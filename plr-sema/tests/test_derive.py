"""Spec 260901 §7.5 / T6 (backlog #4829): the seven `plr_sema.derive` tests
named in §7.5.

T8 consolidation note: this file previously carried an extra
`test_supported_tools_matches_upstream_dispatcher` live cross-package drift
test. `SUPPORTED_TOOLS` now has a single in-package definition at
`plr_sema.check._supported_tools` (T8, spec §6.2's D1 note); `plr_sema.derive`
imports and re-exports the exact same frozenset object rather than defining
its own copy. The one live drift test against `training.verify.dispatcher`
moved to `tests/test_check_graph.py::test_supported_tools_match_upstream`
(spec AC-6.5's named test) so there is exactly ONE such test, not two testing
the same fact from two module paths.

AC-7.1: all seven §7.5 tests pass. Uses the real survey JSON already on disk
(`training/verify/data/plr_preconditions.json`, §7.1) and the real vendored
PLR source under `external/pylabrobot` for the tests that need real data
(the aspirate/_check_containers regression, the guard-site test); synthetic
in-memory indexes for the tests that are about the closure MECHANIC itself
(cycle safety, unresolved-call gaps) rather than about PLR's actual content.
"""

from __future__ import annotations

import ast
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from plr_sema._hand_maintained import BUDGET_CAP, live_rows
from plr_sema._provenance import SurveyStamp, survey_stamp
from plr_sema.derive import (
    DroppedCall,
    SurveyFinding,
    SurveyRecord,
    _is_inert_dropped_receiver_call,
    _iter_plr_source_files,
    build_contract_keys,
    build_gap_ledger,
    build_index,
    default_plr_pkg_root,
    derive_contract,
    load_survey,
    scan_dropped_receiver_calls,
    scan_dropped_receiver_calls_in_source,
)
from plr_sema.derive.__main__ import build_derived_contracts_payload, _guard_to_json
from plr_sema.derive.bindings import (
    build_qualname_index,
    compute_all_local_bindings,
    compute_local_bindings_for_guard,
    compute_reachability_clear,
    demote_refused_env_refs,
    free_var_names,
    is_plr_layer_method,
    param_defaults_from_function,
    substitute,
)
from plr_sema.derive.predicate_ast import (
    Cmp,
    EnvRef,
    Filtered,
    Len,
    Lit,
    Not,
    Opaque,
    TRUE,
    Var,
    contains_env_ref,
    contains_opaque,
    count_var_self,
    parse as parse_predicate,
)
from plr_sema.derive.receiver_state import (
    build_plr_class_index,
    build_plr_function_index,
    compute_delegate_channel_bindings,
    compute_volume_anchors,
    compute_volume_bridge,
    compute_volume_state_exceptions,
    constructor_call_writes,
    dataclass_field_annotations,
    derive_receiver_states,
    for_over_comprehension_output,
    operand_pairing_idiom,
    reset_rule_candidates,
    volume_guard_is_unconditional,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SURVEY_JSON = REPO_ROOT / "training" / "verify" / "data" / "plr_preconditions.json"
TAXONOMY_JSON = REPO_ROOT / "training" / "verify" / "data" / "plr_exception_taxonomy.json"


# ---------------------------------------------------------------------------
# Shared fixtures: real survey data, loaded once per module.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def survey_records() -> list[SurveyRecord]:
    return load_survey(SURVEY_JSON)


@pytest.fixture(scope="module")
def survey_index(survey_records: list[SurveyRecord]) -> dict[tuple[str, str], SurveyRecord]:
    return build_index(survey_records)


@pytest.fixture(scope="module")
def plr_function_index():
    """260904 (T30b): the real whole-tree `(module, qualname, lineno) -> AST
    node` index, module-scoped -- built once per test-module run rather
    than once per test (`build_plr_function_index` walks all 4770-plus
    functions across the whole vendored PLR tree)."""
    return build_plr_function_index(default_plr_pkg_root())


# ---------------------------------------------------------------------------
# test_aspirate_closure_reaches_check_containers -- the load-bearing
# regression (§7.5). Must fail against an own-body-only derivation.
# ---------------------------------------------------------------------------


def test_aspirate_closure_reaches_check_containers(
    survey_index: dict[tuple[str, str], SurveyRecord],
) -> None:
    entry = survey_index[("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler.aspirate")]

    # First, prove the regression is genuinely load-bearing: aspirate's OWN
    # body (depth 0 only, i.e. no closure expansion at all) has zero guards
    # whose site is _check_containers -- own-body findings don't mention it.
    own_body_sites = {f.lineno for f in entry.findings}
    check_containers = survey_index[
        ("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler._check_containers")
    ]
    check_containers_linenos = {f.lineno for f in check_containers.findings}
    assert not (own_body_sites & check_containers_linenos), (
        "fixture assumption violated: aspirate's own body already contains "
        "a finding at one of _check_containers's line numbers, which would "
        "make this regression vacuous"
    )
    assert "_check_containers" in entry.delegates_to  # sanity: it IS a delegate

    # Now derive the full closure and assert it DOES reach _check_containers
    # at depth > 0 -- this is the property that fails if delegate expansion
    # is disabled (own-body-only derivation), which is the whole point.
    contract = derive_contract(entry.module, entry.qualname, survey_index)
    matching = [
        g
        for g in contract.guards
        if g.site.qualname == "LiquidHandler._check_containers" and g.depth > 0
    ]
    assert matching, (
        "derive_contract(LiquidHandler.aspirate) closure did not reach "
        "LiquidHandler._check_containers at depth > 0 -- this is exactly "
        "the own-body-only failure mode §7.2 exists to prevent"
    )
    # And the guard's site really is _check_containers's own recorded line,
    # not aspirate's.
    assert matching[0].site.lineno in check_containers_linenos


# ---------------------------------------------------------------------------
# test_closure_terminates_on_cycle
# ---------------------------------------------------------------------------


def _synthetic_record(
    qualname: str,
    *,
    class_name: str | None,
    module: str = "synthetic.module",
    delegates_to: tuple[str, ...] = (),
    unresolved_calls: tuple[str, ...] = (),
    findings: tuple[SurveyFinding, ...] = (),
) -> SurveyRecord:
    return SurveyRecord(
        qualname=qualname,
        class_name=class_name,
        module=module,
        file="synthetic/module.py",
        lineno=1,
        params=(),
        findings=findings,
        delegates_to=delegates_to,
        unresolved_calls=unresolved_calls,
    )


def _synthetic_finding(lineno: int, kind: str = "raise_guard") -> SurveyFinding:
    return SurveyFinding(
        kind=kind,
        condition="x > 0",
        raises="ValueError" if kind == "raise_guard" else None,
        scope_trail=(),
        mentions_params=("x",),
        lineno=lineno,
    )


@pytest.mark.timeout(5)
def test_closure_terminates_on_cycle() -> None:
    """Synthetic A -> B -> A index (§7.5). Cycle-safety is checked via
    `seen` before expansion (trap 2); a naive recursion would hang. Run
    under pytest-timeout so a regression fails loudly instead of hanging
    the suite.
    """
    rec_a = _synthetic_record(
        "A", class_name=None, delegates_to=("B",), findings=(_synthetic_finding(10),)
    )
    rec_b = _synthetic_record(
        "B", class_name=None, delegates_to=("A",), findings=(_synthetic_finding(20),)
    )
    index = build_index([rec_a, rec_b])

    contract = derive_contract("synthetic.module", "A", index)

    # Terminates (the @pytest.mark.timeout above is the primary guard) and
    # visits each node's findings exactly once -- one guard from A (depth 0)
    # and one from B (depth 1), not an unbounded/duplicated set.
    assert len(contract.guards) == 2
    depths = sorted(g.depth for g in contract.guards)
    assert depths == [0, 1]
    linenos = sorted(g.site.lineno for g in contract.guards)
    assert linenos == [10, 20]


# ---------------------------------------------------------------------------
# test_unresolved_calls_become_gaps
# ---------------------------------------------------------------------------


def test_unresolved_calls_become_gaps() -> None:
    rec = _synthetic_record(
        "Widget.frobnicate",
        class_name="Widget",
        unresolved_calls=("send_command",),
    )
    index = build_index([rec])

    contract = derive_contract("synthetic.module", "Widget.frobnicate", index)

    assert contract.gaps == (("unresolved_delegate", "send_command"),)


# ---------------------------------------------------------------------------
# test_guard_sites_point_at_defining_file -- respecified per D5: a universal
# over the closure, not gated on cross-file (which is structurally
# unsatisfiable under round-1 resolve()).
# ---------------------------------------------------------------------------


def test_guard_sites_point_at_defining_file(
    survey_index: dict[tuple[str, str], SurveyRecord],
) -> None:
    entry_module = "pylabrobot.liquid_handling.liquid_handler"
    entry_qualname = "LiquidHandler.aspirate"
    contract = derive_contract(entry_module, entry_qualname, survey_index)

    depth_gt_0 = [g for g in contract.guards if g.depth > 0]
    assert depth_gt_0, "fixture assumption violated: expected >=1 depth>0 guard"

    for guard in depth_gt_0:
        assert guard.site.qualname != entry_qualname, (
            f"guard at depth {guard.depth} claims site.qualname == the entry "
            f"point's own qualname -- provenance is not preserved"
        )
        defining_rec = survey_index[(entry_module, guard.site.qualname)]
        defining_linenos = {f.lineno for f in defining_rec.findings}
        assert guard.site.lineno in defining_linenos, (
            f"guard's site.lineno={guard.site.lineno} does not match any "
            f"finding recorded on {guard.site.qualname} -- site does not "
            f"point at the DEFINING site"
        )


# ---------------------------------------------------------------------------
# test_ledger_totals_are_internally_consistent
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_stamp() -> SurveyStamp:
    return survey_stamp()


@pytest.fixture(scope="module")
def dropped_receiver_counts():
    return scan_dropped_receiver_calls(default_plr_pkg_root())


@pytest.fixture(scope="module")
def gap_ledger(
    survey_index: dict[tuple[str, str], SurveyRecord],
    survey_records: list[SurveyRecord],
    dropped_receiver_counts,
    real_stamp: SurveyStamp,
) -> dict:
    return build_gap_ledger(
        survey_index,
        survey_records,
        dropped_receiver_counts=dropped_receiver_counts,
        stamp=real_stamp,
    )


def test_ledger_totals_are_internally_consistent(
    gap_ledger: dict,
    survey_index: dict[tuple[str, str], SurveyRecord],
    survey_records: list[SurveyRecord],
    real_stamp: SurveyStamp,
) -> None:
    totals = gap_ledger["totals"]
    assert (
        totals["methods_with_no_recorded_gap"] + totals["methods_with_gaps"]
        == totals["methods_attempted"]
    )

    # sum(by_reason.values()) == total gap count -- recomputed independently
    # (re-running the closures here, not trusting the ledger's own running
    # total) so this is a real cross-check, not a tautology.
    finding_bearing = [rec for rec in survey_records if rec.findings]
    recomputed_gap_count = 0
    for rec in finding_bearing:
        contract = derive_contract(rec.module, rec.qualname, survey_index, stamp=real_stamp)
        recomputed_gap_count += len(contract.gaps)

    assert sum(gap_ledger["by_reason"].values()) == recomputed_gap_count
    assert totals["methods_attempted"] == len(finding_bearing)

    # Round-4 remediation (M11): a subset count must never exceed its own
    # population's denominator. Before this fix,
    # `methods_with_dropped_receiver_call` was computed over ALL 4,758
    # indexed records while `methods_attempted` counted only the 1,314
    # finding-bearing ones -- 1976 > 1314, a structurally impossible
    # "subset". Both figures are now computed over the same population
    # (`finding_bearing`), so this assertion is a real, not vacuous, check.
    assert totals["methods_with_dropped_receiver_call"] <= totals["methods_attempted"]

    supported_tools_totals = gap_ledger["supported_tools"]
    assert (
        supported_tools_totals["methods_with_dropped_receiver_call"]
        <= supported_tools_totals["methods_attempted"]
    )


# ---------------------------------------------------------------------------
# test_ledger_is_stamped
# ---------------------------------------------------------------------------


def test_ledger_is_stamped(gap_ledger: dict) -> None:
    plr_hash = gap_ledger["stamp"]["plr"]["hash"]
    assert len(plr_hash) == 40
    assert all(c in "0123456789abcdef" for c in plr_hash)


# ---------------------------------------------------------------------------
# test_ledger_regenerates_deterministically -- round-4 remediation (m2).
# AC-7.3 claims byte-identical regeneration modulo `stamped_at`; nothing
# mechanized that claim before this test.
# ---------------------------------------------------------------------------


def test_ledger_regenerates_deterministically(
    survey_index: dict[tuple[str, str], SurveyRecord],
    survey_records: list[SurveyRecord],
    dropped_receiver_counts,
    real_stamp: SurveyStamp,
) -> None:
    """AC-7.3 (round-4 remediation, m2): two consecutive `build_gap_ledger`
    runs against the SAME fixed stamp and unchanged survey data must
    serialize to byte-identical JSON. Uses a shared, fixed `real_stamp`
    (rather than letting each call recompute its own) so this test isolates
    determinism of the LEDGER-BUILDING logic itself from `stamped_at`'s
    inherent per-call variation, which AC-7.3's own "modulo `stamped_at`"
    clause already carves out.
    """
    import json

    first = build_gap_ledger(
        survey_index,
        survey_records,
        dropped_receiver_counts=dropped_receiver_counts,
        stamp=real_stamp,
    )
    second = build_gap_ledger(
        survey_index,
        survey_records,
        dropped_receiver_counts=dropped_receiver_counts,
        stamp=real_stamp,
    )
    first_json = json.dumps(first, sort_keys=True)
    second_json = json.dumps(second, sort_keys=True)
    assert first_json == second_json


# ---------------------------------------------------------------------------
# test_dropped_receiver_calls_are_counted -- new, T6, corrected predicate D3.
# ---------------------------------------------------------------------------


def test_dropped_receiver_calls_are_counted() -> None:
    subscript_receiver_source = """
def pick_up_tips(self, channel):
    tip = self.head[channel].get_tip()
    return tip
"""
    bare_name_receiver_source = """
def use_resource(self, resource):
    item = resource.get_item()
    return item
"""
    only_self_and_bare_source = """
def clean(self):
    self.foo()
    bare_call()
    return None
"""

    subscript_counts = scan_dropped_receiver_calls_in_source(subscript_receiver_source)
    assert subscript_counts.total >= 1

    bare_name_counts = scan_dropped_receiver_calls_in_source(bare_name_receiver_source)
    assert bare_name_counts.total >= 1

    clean_counts = scan_dropped_receiver_calls_in_source(only_self_and_bare_source)
    assert clean_counts.total == 0
    assert clean_counts.validation_looking == 0

    for counts in (subscript_counts, bare_name_counts, clean_counts):
        assert counts.validation_looking <= counts.total


# ---------------------------------------------------------------------------
# 260901 T11 -- decoupling derivation from SUPPORTED_TOOLS: whole-surface
# contract count, and the contract-table key disambiguator.
# ---------------------------------------------------------------------------


def test_contract_keys_are_collision_free(survey_records: list[SurveyRecord]) -> None:
    """T11 item 2 (F6 resurfacing at whole-survey scale): every record gets
    a DISTINCT contract-table key. `build_contract_keys` itself asserts this
    internally on every call -- this test additionally pins the two known
    collision populations against the real survey data, so a future survey
    regeneration that silently changes the collision shape is caught here
    rather than only inside the function's own defensive assert.
    """
    keys = build_contract_keys(survey_records)
    assert len(keys) == len(survey_records)
    assert len(set(keys.values())) == len(survey_records)

    # Source 1 (already known, F6): a property/setter pair -- same (module,
    # qualname), different lineno -- gets two DISAMBIGUATED keys, neither
    # bare.
    serial_dtr = [
        (rec.module, rec.qualname, rec.lineno)
        for rec in survey_records
        if rec.module == "pylabrobot.io.serial" and rec.qualname == "Serial.dtr"
    ]
    assert len(serial_dtr) == 2, "fixture assumption violated: expected Serial.dtr getter+setter pair"
    disambiguated = {keys[k] for k in serial_dtr}
    assert len(disambiguated) == 2
    assert all("@" in k for k in disambiguated)
    assert "Serial.dtr" not in disambiguated

    # Source 2 (NEW, found this task -- not in the original brief's "8"
    # figure): a module-level function name repeated in a DIFFERENT module.
    # (module, qualname) does not collide (module differs), but the bare
    # contract-table key would, absent disambiguation.
    height_fn = [
        (rec.module, rec.qualname, rec.lineno)
        for rec in survey_records
        if rec.qualname == "_height_of_volume_in_spherical_cap"
    ]
    assert len(height_fn) == 2, (
        "fixture assumption violated: expected _height_of_volume_in_spherical_cap "
        "defined in two distinct modules"
    )
    modules = {rec_key[0] for rec_key in height_fn}
    assert len(modules) == 2, "fixture assumption violated: expected two DIFFERENT modules"
    disambiguated_fn = {keys[k] for k in height_fn}
    assert len(disambiguated_fn) == 2
    assert all("@" in k for k in disambiguated_fn)

    # A non-colliding record keeps its bare qualname (the overwhelming
    # majority -- 4,744 of 4,770 at the current pin).
    aspirate_key = [
        (rec.module, rec.qualname, rec.lineno)
        for rec in survey_records
        if rec.module == "pylabrobot.liquid_handling.liquid_handler" and rec.qualname == "LiquidHandler.aspirate"
    ][0]
    assert keys[aspirate_key] == "LiquidHandler.aspirate"


def test_whole_surface_contract_count(
    survey_records: list[SurveyRecord],
    survey_index: dict[tuple[str, str], SurveyRecord],
    real_stamp: SurveyStamp,
) -> None:
    """T11 items 1+4: `build_derived_contracts_payload` derives a contract
    for EVERY record the survey indexed -- the whole PLR surface, not just
    the 10 `SUPPORTED_TOOLS` methods (spec pre-T11) and not just the 1,314
    finding-bearing methods (T11 item 4's zero-findings decision: a
    zero-own-finding method still gets a real entry, since it may inherit
    guards through its own delegates -- see `PlateReader.read_absorbance`
    covered end-to-end in `test_check_graph.py`).
    """
    payload = build_derived_contracts_payload(survey_records, survey_index, real_stamp)
    contracts = payload["contracts"]

    assert len(contracts) == len(survey_records)
    assert len(contracts) > 10, "whole-surface derivation must exceed the old 10-tool scope"

    # A finding-bearing SUPPORTED_TOOLS method still resolves with guards.
    assert contracts["LiquidHandler.aspirate"]["guards"]

    # A non-LiquidHandler, zero-own-finding method that inherits a guard
    # through delegation is present with a non-empty contract.
    assert contracts["PlateReader.read_absorbance"]["guards"]

    # A zero-own-finding method with an empty closure is present with an
    # EMPTY (not absent) guards/gaps contract -- "known and unconstrained",
    # T11 item 4. 260902 (spec §11.2.4): every entry additionally carries a
    # `params` key (this method's PLR parameter names, straight off
    # `SurveyRecord.params`) -- checked separately below rather than folded
    # into this equality, since its content isn't this test's concern.
    assert contracts["Centrifuge.spin"]["guards"] == []
    assert contracts["Centrifuge.spin"]["gaps"] == []

    # 260902 (spec §11.2.4, SEMA-IR): every contract entry carries an
    # additive `params` key -- the method's PLR parameter names, verbatim
    # off `SurveyRecord.params` (not re-derived here).
    assert "params" in contracts["LiquidHandler.aspirate"]
    assert "resources" in contracts["LiquidHandler.aspirate"]["params"]
    assert "vols" in contracts["LiquidHandler.aspirate"]["params"]

    # Every emitted key really is one of build_contract_keys' outputs (no
    # ad hoc key construction inside build_derived_contracts_payload itself).
    assert set(contracts.keys()) == set(build_contract_keys(survey_records).values())


# ---------------------------------------------------------------------------
# 260901 T14 (backlog #4862) -- the surface-agnostic dropped-receiver
# worklist (top_unresolved.dropped_receiver_whole_surface), and its direct
# motivation: the CLOSURE-based dropped_receiver views are structurally
# empty on a surface with no LiquidHandler/SUPPORTED_TOOLS entry points.
#
# Deliberately does NOT depend on a live PLR source tree: unlike
# scan_dropped_receiver_calls (the independent AST pass, D3), the function
# under test here (_dropped_receiver_worklist_whole_surface) reads only
# each SurveyRecord's own `dropped_calls` field -- already captured in the
# COMMITTED training/verify/data/plr_preconditions.upstream_nonlegacy.json
# -- so `dropped_receiver_counts={}` is passed to build_gap_ledger below on
# purpose: it is irrelevant to the fields these tests inspect, and passing
# an empty dict avoids re-extracting the upstream_nonlegacy pin (T13 used an
# ephemeral git-archive tmpdir; see test_check_graph_nonlegacy.py's module
# docstring) just to run this test.
# ---------------------------------------------------------------------------

NONLEGACY_SURVEY_JSON = (
    REPO_ROOT / "training" / "verify" / "data" / "plr_preconditions.upstream_nonlegacy.json"
)


@pytest.fixture(scope="module")
def nonlegacy_survey_records() -> list[SurveyRecord]:
    return load_survey(NONLEGACY_SURVEY_JSON)


@pytest.fixture(scope="module")
def nonlegacy_survey_index(
    nonlegacy_survey_records: list[SurveyRecord],
) -> dict[tuple[str, str], SurveyRecord]:
    return build_index(nonlegacy_survey_records)


@pytest.fixture(scope="module")
def nonlegacy_gap_ledger(
    nonlegacy_survey_index: dict[tuple[str, str], SurveyRecord],
    nonlegacy_survey_records: list[SurveyRecord],
) -> dict:
    return build_gap_ledger(
        nonlegacy_survey_index,
        nonlegacy_survey_records,
        dropped_receiver_counts={},
    )


def test_closure_based_dropped_receiver_views_are_vacuous_on_nonlegacy(
    nonlegacy_gap_ledger: dict,
) -> None:
    """Pins the T14 motivation directly: on `upstream_nonlegacy`,
    `liquid_handler_present` is False (no orchestration layer, T13), so
    `top_unresolved.dropped_receiver`/`dropped_receiver_unfiltered` (both
    built by walking closures from a `SUPPORTED_TOOLS`/`LiquidHandler`
    entry-point set that is empty here) are structurally EMPTY -- not
    small, not "nothing interesting found", genuinely never populated. If
    this test ever starts failing because these lists are non-empty, either
    upstream reintroduced `LiquidHandler` outside `legacy/`, or a future
    survey regeneration changed which surface this fixture reads.
    """
    assert nonlegacy_gap_ledger["supported_tools"]["liquid_handler_present"] is False
    assert nonlegacy_gap_ledger["top_unresolved"]["dropped_receiver"] == []
    assert nonlegacy_gap_ledger["top_unresolved"]["dropped_receiver_unfiltered"] == []


def test_whole_surface_dropped_receiver_worklist_is_populated_on_nonlegacy(
    nonlegacy_gap_ledger: dict,
) -> None:
    """The new, surface-agnostic view fills exactly the gap the previous
    test pins: it is NOT gated on `tool_keys`, so it is non-empty even
    though the closure-based views above are structurally empty. Checked
    against the real, committed nonlegacy survey data -- not a synthetic
    fixture -- so this is a real measurement, not just a shape check.
    """
    whole_surface = nonlegacy_gap_ledger["top_unresolved"]["dropped_receiver_whole_surface"]
    whole_surface_unfiltered = nonlegacy_gap_ledger["top_unresolved"][
        "dropped_receiver_whole_surface_unfiltered"
    ]
    assert whole_surface, "expected a non-empty ranked worklist on the driver-layer surface"
    assert whole_surface_unfiltered
    assert len(whole_surface) <= len(whole_surface_unfiltered), (
        "filtering must never ADD rows relative to the unfiltered ranking"
    )

    # Every row is well-formed: {"call": str, "blocks_methods": int}, sorted
    # descending by blocks_methods (same shape/order contract as the other
    # three top_unresolved views).
    for row in whole_surface:
        assert set(row.keys()) == {"call", "blocks_methods"}
        assert row["blocks_methods"] >= 1
    counts = [row["blocks_methods"] for row in whole_surface]
    assert counts == sorted(counts, reverse=True)

    # blocks_methods can never exceed the population it was ranked over
    # (methods_attempted, the finding-bearing count).
    methods_attempted = nonlegacy_gap_ledger["totals"]["methods_attempted"]
    assert whole_surface[0]["blocks_methods"] <= methods_attempted

    # 260903 §13.4.2 (backlog #4883): the filter is now DERIVED
    # (`sys.stdlib_module_names` + per-file import-alias resolution,
    # builtin-container-attribute membership) rather than the round-5
    # hand-typed prefix/suffix lists. `logger` is a plain
    # `logging.Logger`-typed local variable on this surface too, not an
    # import alias of the stdlib `logging` module -- so `logger.*` calls
    # are NO LONGER filtered here, and correctly so (§13.4.2's own "six
    # uncovered locals" point: a filter that hides `logger.debug` by
    # naming it hides the fact that the derivation cannot see it). This
    # reverses the round-5 assertion below on purpose; the "filter is
    # actually doing something" property is now demonstrated by `'.join`
    # / other builtin-container-attribute calls instead, still present in
    # the unfiltered ranking and absent from the filtered one.
    filtered_calls = {row["call"] for row in whole_surface}
    unfiltered_calls = {row["call"] for row in whole_surface_unfiltered}
    assert any(call.startswith("logger.") for call in filtered_calls), (
        "fixture assumption violated: expected >=1 logger.* call to survive "
        "the derived filter -- logger is a local variable, not a stdlib "
        "import alias, on this surface"
    )
    assert "', '.join" in unfiltered_calls and "', '.join" not in filtered_calls, (
        "fixture assumption violated: expected the derived filter to still "
        "remove >=1 builtin-container-attribute call (proves the filter is "
        "actually doing something, not vacuously passing because there was "
        "nothing to filter)"
    )


def test_whole_surface_dropped_receiver_worklist_matches_direct_recount(
    nonlegacy_survey_records: list[SurveyRecord],
    nonlegacy_gap_ledger: dict,
) -> None:
    """Cross-check against an independent recomputation straight from
    `SurveyRecord.dropped_calls` -- not trusting the ledger's own output as
    its own proof, the same discipline `test_ledger_totals_are_internally_
    consistent` already applies to `by_reason`.
    """
    finding_bearing = [rec for rec in nonlegacy_survey_records if rec.findings]
    expected: dict[str, int] = {}
    for rec in finding_bearing:
        # (260903, T25) `dropped_calls` entries are `DroppedCall` records --
        # dedupe on `.expr`, mirroring `_dropped_receiver_worklist_whole_
        # surface`'s own `{dropped.expr for dropped in rec.dropped_calls}`.
        for call_expr in {dropped.expr for dropped in rec.dropped_calls}:
            expected[call_expr] = expected.get(call_expr, 0) + 1

    whole_surface_unfiltered = nonlegacy_gap_ledger["top_unresolved"][
        "dropped_receiver_whole_surface_unfiltered"
    ]
    actual = {row["call"]: row["blocks_methods"] for row in whole_surface_unfiltered}
    assert actual == expected


def test_whole_surface_dropped_receiver_worklist_populated_on_legacy(
    survey_records: list[SurveyRecord],
    survey_index: dict[tuple[str, str], SurveyRecord],
) -> None:
    """The new view is published for EVERY surface, not just the one that
    motivated it -- on `legacy_pinned` (which DOES have a `LiquidHandler`
    closure), it ranks a population that is a superset of, not identical
    to, the closure-based `dropped_receiver` view (see the T14 docstring's
    "neither is a strict superset" note for why the reverse containment
    does not hold either) -- checked here only for non-emptiness and shape,
    not byte-for-byte equality with the closure view.
    """
    ledger = build_gap_ledger(survey_index, survey_records, dropped_receiver_counts={})
    whole_surface = ledger["top_unresolved"]["dropped_receiver_whole_surface"]
    assert whole_surface
    for row in whole_surface:
        assert set(row.keys()) == {"call", "blocks_methods"}


# ---------------------------------------------------------------------------
# AC-13.1 / AC-13.2 (spec 260903 §13.4, backlog #4883) -- the derived
# dropped-receiver inert-name filter replaces the two hand-typed frozensets
# (`_INERT_RECEIVER_PREFIXES`, `_INERT_CALL_SUFFIXES`), and the deletion
# leaves the hand-maintained registry unchanged.
# ---------------------------------------------------------------------------

_LIQUID_HANDLER_FILE = "external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py"


@pytest.fixture
def stdlib_importing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """A synthetic module-level source file that actually imports
    `asyncio`/`time`/`struct`/`contextlib` -- used instead of a real PLR
    file so this test's classification claims do not depend on which PLR
    file happens to import which stdlib module at the current pin (a fact
    that can drift independently of this filter). Patches
    `plr_sema.derive._REPO_ROOT` for the duration of the test so a bare,
    repo-root-relative `file=...` string resolves into `tmp_path`, and
    clears `_module_level_import_aliases`'s cache so an earlier test's
    entry for the same bare filename can never leak in."""
    import plr_sema.derive as derive_mod

    (tmp_path / "stdlib_caller.py").write_text(
        "import asyncio\nimport time\nimport struct\nimport contextlib\n"
    )
    monkeypatch.setattr(derive_mod, "_REPO_ROOT", tmp_path)
    derive_mod._module_level_import_aliases.cache_clear()
    yield "stdlib_caller.py"
    derive_mod._module_level_import_aliases.cache_clear()


@pytest.mark.parametrize(
    "call_expr",
    ["asyncio.sleep", "time.time", "struct.pack", "contextlib.suppress"],
)
def test_derived_inert_filter_classifies_stdlib_calls_as_inert(
    call_expr: str, stdlib_importing_file: str
) -> None:
    """AC-13.1's positive half: none of these four heads were in the
    deleted `_INERT_RECEIVER_PREFIXES` (nine locals/logging/inspect names),
    so a pre-260903 run ranked them as real unresolved-receiver signal
    (T14's finding, §13.4.1). The derived clause-1 replacement catches all
    four -- but only because `stdlib_importing_file` actually IMPORTS each
    module at module level (backlog #4883 follow-up: bare
    `sys.stdlib_module_names` string-membership on the head, with no
    verification the file imported anything, was the bug this tightening
    fixes -- see `test_derived_inert_filter_requires_actual_import`)."""
    assert _is_inert_dropped_receiver_call(call_expr, file=stdlib_importing_file) is True


def test_derived_inert_filter_requires_actual_import(
    stdlib_importing_file: str,
) -> None:
    """Backlog #4883 follow-up (the `resource` false-positive fix): a head
    that merely COINCIDES with a stdlib module name -- `resource` is a
    real, Unix-only stdlib module, and PLR uses `resource` constantly as
    an ordinary local variable name for a `Resource` instance -- must NOT
    be classified inert unless the file's own module-level imports
    actually bind that name to a stdlib module. `stdlib_importing_file`
    imports `asyncio` (so `asyncio.sleep` IS inert) but never imports
    `resource` (so `resource.get_item`, an ordinary PLR receiver call, is
    NOT inert) -- the exact pairing the follow-up requires."""
    assert _is_inert_dropped_receiver_call("asyncio.sleep", file=stdlib_importing_file) is True
    assert (
        _is_inert_dropped_receiver_call("resource.get_item", file=stdlib_importing_file) is False
    )


@pytest.mark.parametrize(
    "call_expr",
    [
        "self.head[channel].get_tip",
        "op.resource.tracker.remove_liquid",
        "op.tip.tracker.add_liquid",
    ],
)
def test_derived_inert_filter_keeps_real_receiver_signal(call_expr: str) -> None:
    """AC-13.1's negative half: real tip/volume-typestate receivers must
    NOT be classified inert by either replaced clause -- `self`/`op` are
    not stdlib module names or aliases of one, `self`/`op` are lowercase
    (clause 2 unaffected), and `get_tip`/`remove_liquid`/`add_liquid` are
    not builtin container/str/bytes attributes (clause 3's replacement)."""
    assert _is_inert_dropped_receiver_call(call_expr, file=_LIQUID_HANDLER_FILE) is False


def test_derived_inert_filter_stub_defeating_half_admits_logger_debug() -> None:
    """AC-13.1's stub-defeating assertion, named explicitly in the spec: an
    implementation that quietly kept `_INERT_RECEIVER_PREFIXES` as a
    fallback would report `logger.debug` as still inert (0 newly admitted).
    `logger` is a local `logging.Logger` instance, not an import alias of
    the stdlib `logging` module in this file, so clause 1's replacement
    (stdlib membership / per-file import-alias resolution) does not catch
    it, and it is genuinely admitted back into the ranking."""
    assert (
        _is_inert_dropped_receiver_call("logger.debug", file=_LIQUID_HANDLER_FILE) is False
    ), "logger.debug must be admitted (not inert) -- see §13.4.2's 'six uncovered locals'"


def _old_inert_predicate(call_expr: str) -> bool:
    """The round-5 rule this task DELETES from the source
    (`_INERT_RECEIVER_PREFIXES`/`_INERT_CALL_SUFFIXES`), reconstructed HERE
    ONLY so this test module can compute the before/after ranking movement
    AC-13.1 requires published -- not reintroduced as a fallback in
    `plr_sema.derive` itself (§13.4.2's design point 8 forbids that)."""
    old_prefixes = {
        "logger", "logging", "warnings", "inspect", "args", "kwargs", "sig",
        "backend_kwargs", "default",
    }
    old_suffixes = {
        "keys", "items", "values", "union", "join", "append", "get", "update",
        "format", "strip", "split",
    }
    head = call_expr.split(".", 1)[0]
    if head in old_prefixes:
        return True
    if head[:1].isupper():
        return True
    tail = call_expr.rsplit(".", 1)[-1]
    return tail in old_suffixes


def test_dropped_receiver_worklist_ranking_movement_both_directions(
    gap_ledger: dict,
) -> None:
    """AC-13.1: publish the ranking movement in both directions over the
    real, shipped `top_unresolved.dropped_receiver` view, relative to the
    ORIGINAL pre-#4883 rule (`_INERT_RECEIVER_PREFIXES`/
    `_INERT_CALL_SUFFIXES`, reconstructed as `_old_inert_predicate`) --
    newly filtered (was ranked under the old rule, now inert under the
    derived rule) and newly admitted (was inert under the old rule, now
    ranked). The newly-admitted count must be > 0 and must include
    `logger.debug` (the stub-defeating half named in the spec) -- `resource`
    was never in the old rule's typed lists, so `resource.*` calls were
    already visible under the OLD rule too and are not part of THIS
    comparison's movement; the follow-up's own regression guard (a
    NARROWER rule than #4883's first cut, not something the pre-#4883 rule
    ever caught) is `test_dropped_receiver_worklist_admits_resource_calls`
    below.

    Compares against the SHIPPED `dropped_receiver` view (not a local
    recomputation) for the "new" side deliberately: the derived rule is
    now per-file (`_is_inert_dropped_receiver_call` requires the
    originating record's own `file`), and the unfiltered call-text list
    alone does not carry which file(s) each call text came from, so
    recomputing "new" with one hardcoded file would silently misclassify
    any call text that appears in more than one file. The old rule had no
    such dependency (`_old_inert_predicate` takes no `file` argument), so
    reconstructing IT locally is safe.
    """
    unfiltered = gap_ledger["top_unresolved"]["dropped_receiver_unfiltered"]
    all_calls = {row["call"] for row in unfiltered}
    new_filtered = {row["call"] for row in gap_ledger["top_unresolved"]["dropped_receiver"]}

    old_filtered = {c for c in all_calls if not _old_inert_predicate(c)}

    newly_filtered = old_filtered - new_filtered
    newly_admitted = new_filtered - old_filtered

    assert len(newly_admitted) > 0
    assert "logger.debug" in newly_admitted
    # Sanity: the derived rule strictly extends stdlib-noise coverage
    # (asyncio/time/struct were real unresolved-receiver noise under the
    # old rule per T14, §13.4.1), so some entries move the other way too.
    assert len(newly_filtered) >= 0  # published even when zero


def test_dropped_receiver_worklist_admits_resource_calls(gap_ledger: dict) -> None:
    """Backlog #4883 follow-up: `resource` is a real, Unix-only stdlib
    module name that also happens to be an extremely common PLR local
    variable name (a `Resource` instance) -- a bare
    `head in sys.stdlib_module_names` membership check (the first cut of
    this item, before the follow-up tightened clause 1 to require an
    ACTUAL per-file import binding) wrongly classified every
    `resource.<attr>` dropped call as inert, with no evidence any file
    ever imported the stdlib `resource` module. None of PLR's files that
    contribute `resource.*` dropped-receiver calls in the SUPPORTED_TOOLS
    closure import the stdlib `resource` module, so all of them must
    survive the (tightened) filter -- this is the stub-defeating half for
    the follow-up specifically: an implementation that reverted to bare
    membership passes every other AC-13.1 assertion and fails only this
    one."""
    filtered_calls = {row["call"] for row in gap_ledger["top_unresolved"]["dropped_receiver"]}
    resource_calls = {c for c in filtered_calls if c.startswith("resource.")}
    assert resource_calls, (
        "expected >=1 resource.* call to survive the derived filter -- if "
        "this is empty, clause 1 has regressed to bare stdlib-name "
        "membership and is wrongly treating `resource` as an import"
    )
    assert "resource.get_item" in filtered_calls


def test_dropped_receiver_worklist_publishes_get_tip_rank(gap_ledger: dict) -> None:
    """AC-13.1's third published number: the resulting rank of
    `self.head[channel].get_tip` in the (derived-rule) filtered ranking --
    it must still be present (real signal, never inert) and its rank is a
    concrete, reportable position."""
    view = gap_ledger["top_unresolved"]["dropped_receiver"]
    calls = [row["call"] for row in view]
    assert "self.head[channel].get_tip" in calls, (
        "self.head[channel].get_tip must survive the derived filter -- it "
        "is real tip-typestate receiver signal, not stdlib/container noise"
    )
    rank = calls.index("self.head[channel].get_tip") + 1
    assert rank >= 1


def test_import_alias_resolution_is_per_file_not_global() -> None:
    """Round-1 challenger O6: alias resolution must be scoped to the file
    the `dropped_calls` entry came from, not a single global table. Two
    synthetic files that bind the SAME local name to DIFFERENT targets --
    one a real stdlib alias, one an ordinary local variable -- must resolve
    independently. A fixer who built one global alias table would have
    `aio` resolve identically in both files; per-file resolution must not.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        file_a = tmp_path / "a.py"
        file_b = tmp_path / "b.py"
        file_a.write_text("import asyncio as aio\n")
        file_b.write_text("aio = SomeOtherThing()\n")  # NOT an import -- ordinary local

        # Resolve relative to the real repo root the module derives paths
        # from (`_REPO_ROOT`), so use paths that are actually reachable --
        # patch the module's repo-root-relative lookup by using a path
        # string relative to the real repo root.
        import plr_sema.derive as derive_mod

        original_root = derive_mod._REPO_ROOT
        try:
            derive_mod._REPO_ROOT = tmp_path
            # `_module_level_import_aliases` is `lru_cache`d on the bare
            # `file` string alone -- clear it so no other test's "a.py"/
            # "b.py" entry (resolved against a DIFFERENT tmp_path) can leak
            # in, and clear again on the way out so this test's entries
            # don't leak to a later one either.
            derive_mod._module_level_import_aliases.cache_clear()
            assert _is_inert_dropped_receiver_call("aio.sleep", file="a.py") is True
            assert _is_inert_dropped_receiver_call("aio.sleep", file="b.py") is False
        finally:
            derive_mod._REPO_ROOT = original_root
            derive_mod._module_level_import_aliases.cache_clear()


def test_ac_13_2_frozensets_are_deleted_from_source() -> None:
    """AC-13.2, first half: an AST scan of `derive/__init__.py` finds no
    module-level assignment named `_INERT_RECEIVER_PREFIXES` or
    `_INERT_CALL_SUFFIXES`, and no `ast.Constant` string equal to any of
    their twenty former members -- so the item cannot be satisfied by
    quietly keeping the list under a different name or inlining its
    members as string literals elsewhere."""
    import plr_sema.derive as derive_mod

    source_path = Path(derive_mod.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))

    forbidden_names = {"_INERT_RECEIVER_PREFIXES", "_INERT_CALL_SUFFIXES"}
    forbidden_string_constants = {
        "logger", "logging", "warnings", "inspect", "args", "kwargs", "sig",
        "backend_kwargs", "default",
        "keys", "items", "values", "union", "join", "append", "get", "update",
        "format", "strip", "split",
    }
    assert len(forbidden_string_constants) == 20

    assigned_names: set[str] = set()
    string_constants: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned_names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            assigned_names.add(node.target.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            string_constants.add(node.value)

    assert not (assigned_names & forbidden_names), (
        f"forbidden module-level names still assigned: {assigned_names & forbidden_names}"
    )
    hits = string_constants & forbidden_string_constants
    assert not hits, f"forbidden former frozenset members still present as string constants: {hits}"


def test_ac_13_2_registry_unchanged_at_24_live() -> None:
    """AC-13.2, second half: the hand-maintained registry does not grow --
    #4883 adds no row, retires no row (§13.4.3: the frozensets were never
    registered in the first place, so there is no row to retire either).
    `live_rows()` stays 24 against `BUDGET_CAP == 24`, asserted AFTER this
    change, so the item cannot be satisfied by registering the deleted
    surface instead of deriving it."""
    assert BUDGET_CAP == 24
    assert len(live_rows()) == 24


# ---------------------------------------------------------------------------
# AC-12.1 -- the derived setup() head-reset effect (spec 260903 §12.1),
# sub-assertions (iii) and (iv). (i) and (ii) live in test_tip_typestate.py,
# next to AC-10.9, whose shipped-artifact fixture and forbidden-literal scan
# they reuse.
# ---------------------------------------------------------------------------


def _class_index_from_root(root: Path) -> dict[str, ast.ClassDef]:
    """The same "P1 class index" build `derive_receiver_states` does
    internally (every top-level class across a source tree, first
    definition wins) -- duplicated here, not imported, because it is a
    ~10-line loop over already-public helpers and the point of this
    section's own tests is to exercise `reset_rule_candidates` directly,
    at a level BELOW `derive_receiver_states`'s own one-ReceiverState-per-
    class assembly.
    """
    class_nodes: dict[str, ast.ClassDef] = {}
    for file in _iter_plr_source_files(root):
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for top in ast.iter_child_nodes(tree):
            if isinstance(top, ast.ClassDef):
                class_nodes.setdefault(top.name, top)
    return class_nodes


def test_ac_12_1_iv_conjunct_sets_against_real_plr() -> None:
    """AC-12.1(iv): conjuncts 1-2 alone select `{"setup", "load_state"}` at
    the current pin (`LiquidHandler.load_state` also constructs only fresh
    `TipTracker`s with no carry-over, §12.1.2's own worked example) --
    conjunct 3 (direct statement of the method body, not nested in the
    `if head_state and self.head == {}:` `load_state` sits inside) narrows
    that to exactly `{"setup"}`. This is the sub-assertion that fails
    loudly if conjunct 3 is dropped or weakened, per §12.1.2/AC-12.1(iv)'s
    own framing -- without it P5's more-than-one rule would fire and the
    whole feature would silently disable itself at this pin.
    """
    root = default_plr_pkg_root()
    class_nodes = _class_index_from_root(root)
    liquid_handler = class_nodes["LiquidHandler"]

    conj12, conj123 = reset_rule_candidates(liquid_handler, "head", "TipTracker", class_nodes)
    assert conj12 == frozenset({"setup", "load_state"})
    assert conj123 == frozenset({"setup"})


_SYNTH_TRACKER_AND_ANCHOR = '''
class Tracker:
    def __init__(self):
        self._pending_tip = None

    @property
    def has_tip(self):
        return self._pending_tip is not None
'''


def test_ac_12_1_iii_two_qualifying_methods_is_ambiguous(tmp_path: Path) -> None:
    """AC-12.1(iii), first half: a synthetic class with TWO methods that
    each satisfy all three conjuncts produces NO `entry_reset` -- P5's
    more-than-one rule, §12.1.2 -- and the ledger reason is `"ambiguous"`.
    """
    synth = tmp_path / "synth.py"
    synth.write_text(
        _SYNTH_TRACKER_AND_ANCHOR
        + '''

class Receiver:
    def __init__(self):
        self.head: "Tracker" = {}

    def setup(self):
        self.head = {c: Tracker() for c in range(3)}

    def reboot(self):
        self.head = {c: Tracker() for c in range(3)}
''',
        encoding="utf-8",
    )
    receiver_states = derive_receiver_states(tmp_path, records=[], taxonomy_classes=[])
    rs = receiver_states["Receiver"]
    assert rs.entry_reset is None
    assert rs.entry_reset_ledger == "ambiguous"


def test_ac_12_1_iii_carry_over_comprehension_is_absent(tmp_path: Path) -> None:
    """AC-12.1(iii), second half: a method whose value expression is a
    carry-over comprehension (`{k: v for k, v in self.head.items()}`) --
    conjunct 2's own load-bearing counterexample, §12.1.2 -- qualifies for
    NEITHER `conj12` nor `conj123` (it constructs no tracker at all and
    loads `self.head`), so `entry_reset` is `None` and the ledger reason is
    `"absent"`, not `"ambiguous"` -- there is only one candidate method and
    it does not qualify, which is a different fail-closed disposition than
    "more than one qualified".
    """
    synth = tmp_path / "synth.py"
    synth.write_text(
        _SYNTH_TRACKER_AND_ANCHOR
        + '''

class Receiver:
    def __init__(self):
        self.head: "Tracker" = {}

    def reload(self):
        self.head = {k: v for k, v in self.head.items()}
''',
        encoding="utf-8",
    )
    receiver_states = derive_receiver_states(tmp_path, records=[], taxonomy_classes=[])
    rs = receiver_states["Receiver"]
    assert rs.entry_reset is None
    assert rs.entry_reset_ledger == "absent"


# ---------------------------------------------------------------------------
# AC-13.15(i) -- delegate-call literal channel binding (spec §13.5.2, P9,
# backlog #4946): the real-PLR derived binding, and the five-shape negative
# fixture set plus the rule-2 fixture (tested directly against
# `compute_delegate_channel_bindings`, at a level BELOW the whole survey
# pipeline -- the same "exercise the mechanic itself" pattern this file's
# own module docstring names). The rule-4 (disabler ordering) half and
# AC-13.15(ii) (binding grants no effect) live in test_tip_typestate.py,
# next to the check-time fixtures/`_check` helper they need.
# ---------------------------------------------------------------------------


def test_ac_13_15_i_transfer_binds_via_aspirate_arity_default(
    survey_records: list[SurveyRecord],
    survey_index: dict[tuple[str, str], SurveyRecord],
    real_stamp: SurveyStamp,
) -> None:
    """Re-running `plr_sema.derive` over real PLR at the current pin emits,
    on `contracts["LiquidHandler.transfer"]["channel_guards"][0]`, a
    `bound_channels` record with `channels == [0]`, `delegate == "aspirate"`
    and `rule == "arity_default"` -- the rule-3 path, since the `aspirate`
    call site (`liquid_handler.py:1347-1352`) passes no explicit channel
    keyword. `dispense`'s call site at `:1355-1361` binds EXPLICITLY to the
    same numeric channel set through the SAME tracker guard (`get_tip`),
    which is what makes this a real tie the fixer's own one-hop-delegate
    tie-break (K's OWN `delegates_to` declaration order) has to resolve,
    not a vacuous "some [0] shows up somewhere" assertion. And: exactly ONE
    `bound_channels` record exists anywhere in the whole contract table at
    this pin (§13.5.4's own "transfer is the only method this reaches, and
    that must be measured rather than assumed").
    """
    taxonomy = json.loads(TAXONOMY_JSON.read_text(encoding="utf-8"))
    receiver_states = derive_receiver_states(None, survey_records, taxonomy["classes"])
    payload = build_derived_contracts_payload(
        survey_records, survey_index, real_stamp, receiver_states=receiver_states
    )
    contracts = payload["contracts"]

    channel_guards = contracts["LiquidHandler.transfer"]["channel_guards"]
    assert len(channel_guards) == 1
    bound = channel_guards[0]["bound_channels"]
    assert bound["channels"] == [0]
    assert bound["delegate"] == "aspirate"
    assert bound["rule"] == "arity_default"
    assert bound["site_lineno"] == 1347

    found = [
        (key, g["bound_channels"])
        for key, entry in contracts.items()
        for g in entry.get("channel_guards", ())
        if "bound_channels" in g
    ]
    assert found == [("LiquidHandler.transfer", bound)]


_P9_SYNTHETIC_SOURCE = '''
class R:
    async def caller_double_call(self):
        await self.helper(use_channels=[0])
        await self.helper(use_channels=[1])

    async def caller_kwargs_forward(self, **kw):
        await self.helper(**kw)

    async def caller_bare_name(self, chans):
        await self.helper(use_channels=chans)

    async def caller_starred(self, chans):
        await self.helper(use_channels=[*chans])

    async def caller_empty_display(self):
        await self.helper(resources=[])

    async def caller_explicit(self):
        await self.helper(use_channels=[1, 3])

    async def caller_arity_default(self):
        await self.helper(resources=[1, 2, 3])

    async def helper(self, resources=None, use_channels=None):
        pass
'''


def _p9_synthetic_receiver() -> ast.ClassDef:
    tree = ast.parse(_P9_SYNTHETIC_SOURCE)
    (class_node,) = [n for n in ast.iter_child_nodes(tree) if isinstance(n, ast.ClassDef)]
    return class_node


def test_ac_13_15_i_five_negative_fixtures_all_widen() -> None:
    """AC-13.15(i)'s five-shape negative fixture set: two depth-0 awaits of
    the same delegate (rule 1); a `**kwargs` forward; a bare `ast.Name` in
    `use_channels`; a starred argument; and a delegate-parameter display of
    length 0 -- P9 yields `Top` (no entry in the returned table at all,
    §13.5.3's "absent when P9 yields Top") in all five.
    """
    receiver = _p9_synthetic_receiver()
    bindings = compute_delegate_channel_bindings(receiver, {"helper": "resources"}, "use_channels")

    for widened_caller in (
        "caller_double_call",
        "caller_kwargs_forward",
        "caller_bare_name",
        "caller_starred",
        "caller_empty_display",
    ):
        assert widened_caller not in bindings, f"{widened_caller} must widen (Top), found {bindings.get(widened_caller)!r}"


def test_ac_13_15_i_rule_2_explicit_binds_exact_channels() -> None:
    """The rule-2 fixture: `use_channels=[1, 3]` at the call site binds
    EXACTLY `[1, 3]`, `rule == "explicit"` -- not narrowed, not widened,
    and not confused with rule 3's arity-default path (a DIFFERENT caller
    in the same synthetic class, `caller_arity_default`, binds via
    `resources=[1, 2, 3]` to `[0, 1, 2]`, `rule == "arity_default"` --
    both assert here so the two rules are pinned as genuinely distinct,
    not just "some rule matched").
    """
    receiver = _p9_synthetic_receiver()
    bindings = compute_delegate_channel_bindings(receiver, {"helper": "resources"}, "use_channels")

    explicit = bindings["caller_explicit"]["helper"]
    assert explicit["channels"] == [1, 3]
    assert explicit["rule"] == "explicit"
    assert explicit["delegate"] == "helper"

    arity = bindings["caller_arity_default"]["helper"]
    assert arity["channels"] == [0, 1, 2]
    assert arity["rule"] == "arity_default"
    assert arity["delegate"] == "helper"


# ---------------------------------------------------------------------------
# AC-13.3 (spec 260903 §13.1, backlog #4881a) -- the lid facts are DERIVED
# and published, and nothing is claimed from them. Asserted against the
# SHIPPED `plr-sema/data/gap_ledger.json` (not a fixture), because §13.1's
# whole argument is about real PLR at this pin (AC-13.3's own text).
# ---------------------------------------------------------------------------

GAP_LEDGER_JSON_PATH = REPO_ROOT / "plr-sema" / "data" / "gap_ledger.json"


def test_ac_13_3_lid_state_block_is_published_in_shipped_ledger() -> None:
    """The shipped gap ledger carries a `lid_state` block naming, for
    `Liddable`: the P2 anchor as `"absent"` (`has_lid` is a plain method,
    `lid.py:71-72` -- no decorator; the `@property` at `:74` belongs to
    `lid`, not `has_lid`), `has_lid` itself as the one body-shape candidate
    P2's decorator gate rejected, zero state fields (`lid` is computed from
    `self.children` on every read, `lid.py:74-77` -- nothing for
    `_attribute_writers` to see), and the two `_check_no_lid`-derived guard
    conditions with their `raises` -- `"lidded is resource"`/`ValueError`
    at `:116` and `null`/`ValueError` at `:117`.
    """
    ledger = json.loads(GAP_LEDGER_JSON_PATH.read_text(encoding="utf-8"))
    lid_state = ledger["lid_state"]["Liddable"]

    assert lid_state["anchor"] == "absent"
    assert lid_state["anchor_candidates"] == ["has_lid"]
    assert lid_state["state_fields"] == []

    guards = lid_state["check_no_lid_guards"]
    assert len(guards) == 2
    by_lineno = {g["site"]["lineno"]: g for g in guards}
    assert set(by_lineno) == {116, 117}
    assert by_lineno[116]["condition"] == "lidded is resource"
    assert by_lineno[116]["raises"] == "ValueError"
    assert by_lineno[116]["site"]["qualname"] == "_check_no_lid"
    assert by_lineno[116]["site"]["file"].endswith("liquid_handling/liquid_handler.py")
    assert by_lineno[117]["condition"] is None
    assert by_lineno[117]["raises"] == "ValueError"
    assert by_lineno[117]["site"]["qualname"] == "_check_no_lid"


def test_ac_13_3_lid_state_evidence_is_derived_not_hand_typed() -> None:
    """Stub-defeating half: `lid_typestate_anchor_evidence`, called fresh
    against `default_plr_pkg_root()`, reproduces EXACTLY what the shipped
    ledger's `lid_state` block records (short of the `check_no_lid_guards`
    key, which that function does not compute) -- so a hand-typed ledger
    block that happened to match today's PLR pin, rather than a genuinely
    re-run P2 anchor rule, would be caught the moment `Liddable` changes
    shape. Also confirms `Liddable.has_lid` is found via the REAL
    `_typestate_anchor` fail-closed rule (no `@property` decorator ->
    `None`), not a bespoke lid-specific check.
    """
    from plr_sema.derive.receiver_state import lid_typestate_anchor_evidence

    fresh = lid_typestate_anchor_evidence(default_plr_pkg_root())
    assert fresh is not None

    ledger = json.loads(GAP_LEDGER_JSON_PATH.read_text(encoding="utf-8"))
    shipped = ledger["lid_state"]["Liddable"]

    assert fresh["anchor"] == shipped["anchor"] == "absent"
    assert fresh["anchor_candidates"] == shipped["anchor_candidates"] == ["has_lid"]
    assert fresh["state_fields"] == shipped["state_fields"] == []


def test_ac_13_3_no_lidstate_no_receiver_state_entry_no_reason_vocabulary_member() -> None:
    """§13.1's normative disposition, machine-checked: no `LidState` class
    exists anywhere in `plr_sema`; the shipped `receiver_state` block
    (keyed by receiver CLASS, e.g. `LiquidHandler`) carries no `Liddable`
    entry -- the lid ledger block lives ONLY under the separate top-level
    `lid_state` key, never inside `receiver_state`; and `REASON_VOCABULARY`
    gains no lid-related member. Was "still exactly 8" (§13.7/§13.13 item
    6) through increment 4; 260903 (spec §14.6/§14.16 Q4, T26) bumped it
    8 -> 10 for the volume family's `volume_tracking_unasserted`/
    `volume_state_unknown`; 260904 (spec §15.7, increment 6, T31,
    user-approved 260907) bumped it 10 -> 12 for `guard_operand_unknown`/
    `guard_env_dependent` -- both unrelated to lid, which is what the
    no-"lid"-substring assertion below re-confirms independently of the
    exact count.
    """
    import plr_sema

    src_root = Path(plr_sema.__file__).resolve().parent
    for py_file in src_root.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                assert node.name != "LidState", f"a LidState class was constructed at {py_file}:{node.lineno}"

    ledger = json.loads(GAP_LEDGER_JSON_PATH.read_text(encoding="utf-8"))
    assert "Liddable" not in ledger.get("receiver_state", {})

    contracts = json.loads((REPO_ROOT / "plr-sema" / "data" / "derived_contracts.json").read_text(encoding="utf-8"))
    assert "Liddable" not in contracts.get("receiver_state", {})

    from plr_sema.verdict import REASON_VOCABULARY

    assert len(REASON_VOCABULARY) == 12
    assert not any("lid" in reason.lower() for reason in REASON_VOCABULARY)


# ---------------------------------------------------------------------------
# T24 (spec 260903_plr-sema-volume-increment.md §14.0.1/§14.4, backlog
# #4958) -- the volume bridge derivation: B1, B2, P1c, P7, P8, and the
# extended four-segment bridge. AC-14.1, AC-14.2. Every selection below is
# MEASURED against real PLR at the pin, not asserted from the spec's own
# worked example -- see `outputs/plr-sema/t24_measured_260904.json` for the
# full published sets.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def volume_class_index() -> tuple[dict[str, ast.ClassDef], dict[str, str]]:
    return build_plr_class_index(default_plr_pkg_root())


@pytest.fixture(scope="module")
def volume_taxonomy_classes() -> list[dict]:
    return json.loads(TAXONOMY_JSON.read_text(encoding="utf-8"))["classes"]


def test_ac_14_1_i_b1_binds_op_over_whole_surface(
    volume_class_index: tuple[dict[str, ast.ClassDef], dict[str, str]],
) -> None:
    """AC-14.1(i): the complete set of `(K, name, element_class, for_span)`
    B1 binds over `LiquidHandler` has >= 2 entries and includes `aspirate`
    (`op : SingleChannelAspiration`, `for_span == (1031, 1035)`) and
    `dispense` (`op : SingleChannelDispense`, `for_span == (1231, 1235)`) --
    the two the spec's own worked example names. Published over the whole
    class, not just those two methods, per T24's "publish the complete set"
    instruction.
    """
    class_nodes, _modules = volume_class_index
    lh = class_nodes["LiquidHandler"]

    tuples: list[tuple[str, str, str, tuple[int, int]]] = []
    for member in ast.iter_child_nodes(lh):
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        p8 = operand_pairing_idiom(member)
        if not p8:
            continue
        for bound_name, binding in for_over_comprehension_output(member, p8).items():
            tuples.append((member.name, bound_name, binding.element_class, binding.for_span))

    assert len(tuples) >= 2
    by_method = {t[0]: t for t in tuples}
    assert by_method["aspirate"] == ("aspirate", "op", "SingleChannelAspiration", (1031, 1035))
    assert by_method["dispense"] == ("dispense", "op", "SingleChannelDispense", (1231, 1235))


_B1_TUPLE_TARGET_SOURCE = '''
class R:
    def method(self, resources, vols):
        aspirations = [O(resource=r, volume=v) for r, v in zip(resources, vols)]
        for op, extra in aspirations:
            pass
'''


def test_ac_14_1_i_b1_tuple_target_fails_closed() -> None:
    """AC-14.1(i)'s first fail-closed case: the `ast.For` target is a tuple
    (`for op, extra in aspirations:`) rather than a single `ast.Name` -- B1
    binds nothing, even though P8 itself matched `aspirations` cleanly."""
    tree = ast.parse(_B1_TUPLE_TARGET_SOURCE)
    (cls,) = [n for n in ast.iter_child_nodes(tree) if isinstance(n, ast.ClassDef)]
    method = next(m for m in ast.iter_child_nodes(cls) if isinstance(m, ast.FunctionDef))
    p8 = operand_pairing_idiom(method)
    assert "aspirations" in p8
    assert for_over_comprehension_output(method, p8) == {}


_B1_TWO_LOOPS_SOURCE = '''
class R:
    def method(self, resources, vols):
        aspirations = [O(resource=r, volume=v) for r, v in zip(resources, vols)]
        for op in aspirations:
            pass
        for op2 in aspirations:
            pass
'''


def test_ac_14_1_i_b1_two_loops_over_one_list_fails_closed() -> None:
    """AC-14.1(i)'s second fail-closed case (spec §14.0.1's own text): two
    depth-0 `ast.For` statements iterate the SAME P8-produced name -- B1
    binds nothing for either, since picking one would be §10.5 rule 1's
    "two views of one fact" case."""
    tree = ast.parse(_B1_TWO_LOOPS_SOURCE)
    (cls,) = [n for n in ast.iter_child_nodes(tree) if isinstance(n, ast.ClassDef)]
    method = next(m for m in ast.iter_child_nodes(cls) if isinstance(m, ast.FunctionDef))
    p8 = operand_pairing_idiom(method)
    assert "aspirations" in p8
    assert for_over_comprehension_output(method, p8) == {}


def test_ac_14_1_ii_b2_dataclass_field_annotations(
    volume_class_index: tuple[dict[str, ast.ClassDef], dict[str, str]],
) -> None:
    """AC-14.1(ii): B2's selection over `SingleChannelAspiration` and
    `SingleChannelDispense` (`standard.py:53-56`/`:63-72`) -- >= 8
    attributes over >= 2 classes, with `.resource -> Container`,
    `.tip -> Tip`, `.volume -> float` on both."""
    class_nodes, _modules = volume_class_index
    aspiration = dataclass_field_annotations(class_nodes["SingleChannelAspiration"])
    dispense = dataclass_field_annotations(class_nodes["SingleChannelDispense"])

    for fields in (aspiration, dispense):
        assert fields["resource"] == "Container"
        assert fields["tip"] == "Tip"
        assert fields["volume"] == "float"

    assert len(aspiration) + len(dispense) >= 8


def test_ac_14_1_iii_volume_passes_do_not_disturb_receiver_state(
    survey_records: list[SurveyRecord],
    survey_index: dict[tuple[str, str], SurveyRecord],
    real_stamp: SurveyStamp,
    volume_taxonomy_classes: list[dict],
    volume_class_index: tuple[dict[str, ast.ClassDef], dict[str, str]],
) -> None:
    """AC-14.1(iii): B2/P1c disturb no existing selection. `derive_receiver_
    states`'s own body is never called by anything in this section (a
    static fact, not tested here); what IS tested is the OBSERVABLE
    consequence -- the SAME `receiver_states` run through
    `build_derived_contracts_payload` with and without the volume-bridge
    keyword arguments produces a byte-identical `receiver_state` block, and
    every contract entry's `guards`/`gaps`/`params`/`channel_guards`/
    `channel_effect` keys are unaffected too (only the additive
    `volume_guards` key, and 260903 T27's additive `is_volume_setter` key on
    the setter method's own entry, differ). `LiquidHandler`'s own
    `channel_attr`/`tracker_class` stay `"head"`/`"TipTracker"`.
    """
    class_nodes, class_modules = volume_class_index
    receiver_states = derive_receiver_states(None, survey_records, volume_taxonomy_classes)
    volume_state_exceptions = frozenset(compute_volume_state_exceptions(volume_taxonomy_classes))
    anchors = compute_volume_anchors(class_nodes, volume_state_exceptions)

    without_volume = build_derived_contracts_payload(
        survey_records, survey_index, real_stamp, receiver_states=receiver_states
    )
    with_volume = build_derived_contracts_payload(
        survey_records,
        survey_index,
        real_stamp,
        receiver_states=receiver_states,
        volume_class_index=class_nodes,
        volume_class_modules=class_modules,
        volume_anchors=anchors,
    )

    assert without_volume["receiver_state"] == with_volume["receiver_state"]
    assert with_volume["receiver_state"]["LiquidHandler"]["channel_attr"] == "head"
    assert with_volume["receiver_state"]["LiquidHandler"]["tracker_class"] == "TipTracker"

    for key, entry in with_volume["contracts"].items():
        without_volume_guards = {
            k: v for k, v in entry.items() if k not in ("volume_guards", "is_volume_setter")
        }
        assert without_volume_guards == without_volume["contracts"][key], (
            f"{key}: a non-volume_guards/is_volume_setter key changed when volume-bridge args were passed"
        )


def test_ac_14_1_iv_p1c_matches_real_plr(
    volume_class_index: tuple[dict[str, ast.ClassDef], dict[str, str]],
) -> None:
    """AC-14.1(iv): P1c yields `Container.tracker -> VolumeTracker`
    (`container.py:85`) and `Tip.tracker -> VolumeTracker` (`tip.py:45`,
    written in `__post_init__`, `tip.py:32`) -- the stub-defeating half,
    since an `__init__`-only pass would find the `Container` half and miss
    `Tip` entirely. The whole-surface selection (every class's own P1c map,
    unioned) has >= 3 entries."""
    class_nodes, _modules = volume_class_index
    assert constructor_call_writes(class_nodes["Container"], class_nodes) == {"tracker": "VolumeTracker"}
    assert constructor_call_writes(class_nodes["Tip"], class_nodes) == {"tracker": "VolumeTracker"}

    whole_surface: list[tuple[str, str, str]] = []
    for name, node in class_nodes.items():
        for attr, callee in constructor_call_writes(node, class_nodes).items():
            whole_surface.append((name, attr, callee))
    assert len(whole_surface) >= 3
    assert ("Container", "tracker", "VolumeTracker") in whole_surface
    assert ("Tip", "tracker", "VolumeTracker") in whole_surface


_P1C_CONFLICT_SOURCE = '''
class Other:
    pass

class Another:
    pass

class R:
    def a(self):
        self.tracker = Other()

    def b(self):
        self.tracker = Another()
'''


def test_ac_14_1_iv_p1c_two_different_constructors_fails_closed() -> None:
    """AC-14.1(iv)'s stub-defeating half: two DIFFERENT methods of the same
    class write `self.tracker` to two DIFFERENT constructor calls -- P1c
    records nothing for `tracker`, over the union of writes (round-1 O2),
    not just within one method."""
    tree = ast.parse(_P1C_CONFLICT_SOURCE)
    classes = {n.name: n for n in ast.iter_child_nodes(tree) if isinstance(n, ast.ClassDef)}
    assert constructor_call_writes(classes["R"], classes) == {}


def test_ac_14_2_i_volume_bridge_matches_aspirate_and_dispense(
    survey_records: list[SurveyRecord],
    survey_index: dict[tuple[str, str], SurveyRecord],
    real_stamp: SurveyStamp,
    volume_taxonomy_classes: list[dict],
    volume_class_index: tuple[dict[str, ast.ClassDef], dict[str, str]],
) -> None:
    """AC-14.2(i): `contracts["LiquidHandler.aspirate"]["volume_guards"]`
    has exactly two entries -- `TooLittleLiquidError` via
    `op.resource.tracker.remove_liquid`, `cell_param == "resources"`,
    `amount_param == "vols"`, direction *decreasing*; `TooLittleVolumeError`
    via `op.tip.tracker.add_liquid`, a LOCAL `cell_param`, direction
    *increasing*. `dispense` carries the mirror pair, including
    `via == "op.tip.tracker.remove_liquid"` with direction *decreasing* --
    the guard this increment exists to decide (§14.0.2's disposition table
    row 4) -- sited at `VolumeTracker.remove_liquid:92`, with a `for_span`
    covering the B1-bound `for op in dispenses:` loop.
    """
    class_nodes, class_modules = volume_class_index
    volume_state_exceptions = frozenset(compute_volume_state_exceptions(volume_taxonomy_classes))
    anchors = compute_volume_anchors(class_nodes, volume_state_exceptions)

    payload = build_derived_contracts_payload(
        survey_records,
        survey_index,
        real_stamp,
        volume_class_index=class_nodes,
        volume_class_modules=class_modules,
        volume_anchors=anchors,
    )
    contracts = payload["contracts"]

    aspirate_guards = contracts["LiquidHandler.aspirate"]["volume_guards"]
    assert len(aspirate_guards) == 2
    by_raises = {g["raises"]: g for g in aspirate_guards}

    liquid = by_raises["TooLittleLiquidError"]
    assert liquid["via"] == "op.resource.tracker.remove_liquid"
    assert liquid["cell_param"] == "resources"
    assert liquid["amount_param"] == "vols"
    assert liquid["direction"] == "decreasing"
    assert liquid["for_span"] == [1031, 1035]

    volume = by_raises["TooLittleVolumeError"]
    assert volume["via"] == "op.tip.tracker.add_liquid"
    assert isinstance(volume["cell_param"], dict) and volume["cell_param"]["local"] is True
    assert volume["direction"] == "increasing"

    dispense_guards = contracts["LiquidHandler.dispense"]["volume_guards"]
    assert len(dispense_guards) == 2
    by_raises_d = {g["raises"]: g for g in dispense_guards}

    tip_side = by_raises_d["TooLittleLiquidError"]
    assert tip_side["via"] == "op.tip.tracker.remove_liquid"
    assert tip_side["direction"] == "decreasing"
    assert tip_side["for_span"] == [1231, 1235]
    assert tip_side["site"]["qualname"] == "VolumeTracker.remove_liquid"
    assert tip_side["site"]["lineno"] == 92
    assert isinstance(tip_side["cell_param"], dict) and tip_side["cell_param"]["local"] is True

    well_side = by_raises_d["TooLittleVolumeError"]
    assert well_side["via"] == "op.resource.tracker.add_liquid"
    assert well_side["cell_param"] == "resources"
    assert well_side["direction"] == "increasing"

    # Only aspirate/dispense have a real four-segment match at this pin --
    # transfer/aspirate96/dispense96 do not (§14.9's own withdrawal of v2).
    with_guards = {k for k, e in contracts.items() if e.get("volume_guards")}
    assert with_guards == {"LiquidHandler.aspirate", "LiquidHandler.dispense"}


def test_ac_14_2_ii_volume_state_taxonomy_filter(volume_taxonomy_classes: list[dict]) -> None:
    """AC-14.2(ii): the unfiltered `category == "volume_state"` set has 4
    members; the module conjunct narrows it to exactly
    `{TooLittleLiquidError, TooLittleVolumeError}`."""
    unfiltered = {c["name"] for c in volume_taxonomy_classes if c.get("category") == "volume_state"}
    assert len(unfiltered) == 4
    assert set(compute_volume_state_exceptions(volume_taxonomy_classes)) == {
        "TooLittleLiquidError",
        "TooLittleVolumeError",
    }


_VOLUME_FORBIDDEN_LITERALS = frozenset(
    {
        "get_used_volume",
        "get_free_volume",
        "pending_volume",
        "tracker",
        "op",
        "TooLittleLiquidError",
        "TooLittleVolumeError",
        "resources",
        "vols",
        # 260903 T27 (spec §14.8, backlog #4959): the `_apply_seed` residue
        # -- the receiver_type/method PAIR that used to be typed as a
        # literal string in `check/volumestate.py`, before P7's published
        # `setter` field replaced it (AC-14.8's item 5). Extended here so
        # the residue cannot return unnoticed.
        "VolumeTracker",
        "set_volume",
    }
)
#: AC-14.2(iv)'s narrowed re-check: the three names the draft's whole-`src/`
#: scope would have been red on unmodified (§14.2(iii)'s own note -- `"op"`
#: is the IR's opcode tag, `"resources"` is the graph payload's own key).
_VOLUME_NARROWED_LITERALS = frozenset({"tracker", "op", "resources"})

_VOLUME_SCAN_MODULES = (
    REPO_ROOT / "plr-sema" / "src" / "plr_sema" / "derive" / "receiver_state.py",
    # 260903 T24: check/volumestate.py is T26's deliverable and does not
    # exist yet -- the scan must tolerate an absent file (see below).
    REPO_ROOT / "plr-sema" / "src" / "plr_sema" / "check" / "volumestate.py",
)


def _volume_docstring_constant_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(
                first.value.value, str
            ):
                ids.add(id(first.value))
    return ids


def _scan_volume_forbidden_literals(source: str, filename: str, forbidden: frozenset[str]) -> list[str]:
    tree = ast.parse(source, filename=filename)
    docstring_ids = _volume_docstring_constant_ids(tree)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in forbidden:
            if id(node) in docstring_ids:
                continue
            offenders.append(f"{filename}:{node.lineno}: {node.value!r}")
    return offenders


def test_ac_14_2_iii_iv_no_hand_typed_volume_names_ast_scan() -> None:
    """AC-14.2(iii): an AST literal scan (not grep, so docstrings are
    excluded -- same mechanism as `test_ac_10_9_no_hand_typed_plr_names_ast_
    scan`) of `plr_sema/derive/receiver_state.py` and the not-yet-existing
    `plr_sema/check/volumestate.py` finds none of the eleven forbidden names
    as a real `ast.Constant` string. AC-14.2(iv): the narrowed three-name
    re-check over the SAME two-file scope still forbids all three -- the
    gate keeps its content, it is not vacuous just because it tolerates a
    missing file.
    """
    all_offenders: list[str] = []
    narrowed_offenders: list[str] = []
    for path in _VOLUME_SCAN_MODULES:
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        all_offenders.extend(_scan_volume_forbidden_literals(source, str(path), _VOLUME_FORBIDDEN_LITERALS))
        narrowed_offenders.extend(_scan_volume_forbidden_literals(source, str(path), _VOLUME_NARROWED_LITERALS))

    assert all_offenders == [], f"hand-typed volume-family name(s) found: {all_offenders}"
    assert narrowed_offenders == [], f"narrowed scan found: {narrowed_offenders}"


def test_ac_14_2_bridge_absent_when_volume_args_omitted(
    survey_records: list[SurveyRecord],
    survey_index: dict[tuple[str, str], SurveyRecord],
    real_stamp: SurveyStamp,
) -> None:
    """Degrade discipline (§14.11's wire-format note): a caller that does
    not pass the volume-bridge keyword arguments (the pre-T24 call shape)
    gets a table with no `volume_guards` key anywhere -- `.get()` with an
    empty default degrades to today's behaviour exactly."""
    payload = build_derived_contracts_payload(survey_records, survey_index, real_stamp)
    assert not any("volume_guards" in entry for entry in payload["contracts"].values())


# ---------------------------------------------------------------------------
# AC-14.3 (T25, §14.0.2, §14.6): caller scope reaches the bridged guard,
# with polarity and position.
# ---------------------------------------------------------------------------


def test_ac_14_3_caller_scope_reaches_bridged_guards_with_polarity_and_position(
    survey_records: list[SurveyRecord],
    survey_index: dict[tuple[str, str], SurveyRecord],
    real_stamp: SurveyStamp,
    volume_taxonomy_classes: list[dict],
    volume_class_index: tuple[dict[str, ast.ClassDef], dict[str, str]],
) -> None:
    """AC-14.3: all four bridged guards of `aspirate`/`dispense` carry a
    non-null `caller_scope`, published verbatim, each of length >= 2, and
    the two guards under the `is_disabled` test (`:1034`/`:1234`) carry an
    entry the other two do not (a set difference, not eyeballed). (ii):
    each guard's own `scope_trail` is unchanged from the callee's contract,
    disjoint from `caller_scope`, and both use the nearest-first
    convention. Verbatim values match §14.0.2's own disposition table.
    """
    class_nodes, class_modules = volume_class_index
    volume_state_exceptions = frozenset(compute_volume_state_exceptions(volume_taxonomy_classes))
    anchors = compute_volume_anchors(class_nodes, volume_state_exceptions)

    payload = build_derived_contracts_payload(
        survey_records,
        survey_index,
        real_stamp,
        volume_class_index=class_nodes,
        volume_class_modules=class_modules,
        volume_anchors=anchors,
    )
    contracts = payload["contracts"]
    aspirate_guards = {g["via"]: g for g in contracts["LiquidHandler.aspirate"]["volume_guards"]}
    dispense_guards = {g["via"]: g for g in contracts["LiquidHandler.dispense"]["volume_guards"]}

    well_aspirate = aspirate_guards["op.resource.tracker.remove_liquid"]
    tip_aspirate = aspirate_guards["op.tip.tracker.add_liquid"]
    well_dispense = dispense_guards["op.resource.tracker.add_liquid"]
    tip_dispense = dispense_guards["op.tip.tracker.remove_liquid"]

    for guard in (well_aspirate, tip_aspirate, well_dispense, tip_dispense):
        assert guard["caller_scope"] is not None
        assert len(guard["caller_scope"]) >= 2

    is_disabled_entry = "if not op.resource.tracker.is_disabled"
    with_is_disabled = {
        via for via, guard in {**aspirate_guards, **dispense_guards}.items()
        if is_disabled_entry in guard["caller_scope"]
    }
    assert with_is_disabled == {"op.resource.tracker.remove_liquid", "op.resource.tracker.add_liquid"}

    # Verbatim, per §14.0.2's own disposition table (nearest-first).
    assert well_aspirate["caller_scope"] == [
        "if not op.resource.tracker.is_disabled",
        "if does_volume_tracking()",
        "for op in aspirations",
    ]
    assert tip_aspirate["caller_scope"] == ["if does_volume_tracking()", "for op in aspirations"]
    assert well_dispense["caller_scope"] == [
        "if not op.resource.tracker.is_disabled",
        "if does_volume_tracking()",
        "for op in dispenses",
    ]
    assert tip_dispense["caller_scope"] == ["if does_volume_tracking()", "for op in dispenses"]

    assert well_aspirate["caller_lineno"] == 1034
    assert tip_aspirate["caller_lineno"] == 1035
    assert well_dispense["caller_lineno"] == 1234
    assert tip_dispense["caller_lineno"] == 1235

    # (ii): the guard's OWN scope_trail (callee-sourced) is unchanged from
    # the callee's own contract and disjoint from caller_scope.
    assert well_aspirate["scope_trail"] == ["if volume - self.get_used_volume() > 1e-06"]
    assert tip_aspirate["scope_trail"] == ["if volume - self.get_free_volume() > 1e-06"]
    assert well_dispense["scope_trail"] == ["if volume - self.get_free_volume() > 1e-06"]
    assert tip_dispense["scope_trail"] == ["if volume - self.get_used_volume() > 1e-06"]


def _scan_dropped_calls_in_function(source: str) -> list:
    """Run the survey's OWN `_BodyScanner` (`scripts/survey_plr_
    preconditions.py`) over one synthetic function's body, for AC-14.3(iii)/
    (iv)'s survey-side fixtures -- exercised at the same level `scripts/
    survey_plr_preconditions.py`'s own `_survey_function` runs it at, not
    reimplemented."""
    import sys as _sys

    scripts_dir = str(REPO_ROOT / "scripts")
    if scripts_dir not in _sys.path:
        _sys.path.insert(0, scripts_dir)
    from survey_plr_preconditions import _BodyScanner  # noqa: PLC0415

    tree = ast.parse(source)
    (func,) = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    scanner = _BodyScanner({a.arg for a in func.args.args}, set(), set())
    for stmt in func.body:
        scanner.visit(stmt)
    return scanner.dropped


_AC_14_3_III_SOURCE = '''
def method(self, a, b):
    if a:
        widget.tracker.spend()
    if b:
        widget.tracker.spend()
'''

_AC_14_3_IV_SOURCE = '''
def method(self):
    if flag_check():
        pass
    else:
        widget.tracker.spend()
'''


def test_ac_14_3_iii_duplicate_expr_under_different_scopes_not_collapsed() -> None:
    """AC-14.3(iii): a fixture whose method body contains the same dotted
    call expression twice under different `if` scopes yields TWO
    `dropped_calls` records with different `lineno`s and different
    `scope_trail`s -- multiplicity preserved, not collapsed (the old
    `set[str]` schema WOULD have collapsed these into one)."""
    dropped = _scan_dropped_calls_in_function(_AC_14_3_III_SOURCE)
    assert len(dropped) == 2
    assert {d.expr for d in dropped} == {"widget.tracker.spend"}
    assert dropped[0].lineno != dropped[1].lineno
    assert dropped[0].scope_trail != dropped[1].scope_trail
    assert dropped[0].scope_trail == ["if a"]
    assert dropped[1].scope_trail == ["if b"]


def test_ac_14_3_iv_orelse_call_records_negated_polarity_and_is_never_recognized() -> None:
    """AC-14.3(iv), the stub-defeating half: a fixture whose call sits in
    an `orelse` records an entry beginning `"else of: if "`, and that entry
    is NOT recognised as satisfied by §14.6's rule even when its test text
    is a member of `env`."""
    (dropped,) = _scan_dropped_calls_in_function(_AC_14_3_IV_SOURCE)
    assert dropped.expr == "widget.tracker.spend"
    assert dropped.scope_trail == ["else of: if flag_check()"]

    # Even with "flag_check" IN env, the negated enclosure is unrecognised.
    recognized = volume_guard_is_unconditional(
        dropped.scope_trail, dropped.lineno, None, frozenset({"flag_check"})
    )
    assert recognized is False


# ---------------------------------------------------------------------------
# AC-14.4 (T25, §14.6): fail-closed on anything unrecognised; R1 recognises
# exactly one node.
# ---------------------------------------------------------------------------


def test_ac_14_4_fail_closed_env_gate_and_r1_position_recognition() -> None:
    """AC-14.4: with `env == {"does_volume_tracking"}`, a guard whose
    `caller_scope == ["if does_volume_tracking()", "for op in dispenses"]`
    WITH a `for_span` containing its `caller_lineno` is unconditional
    (`WILL_FAIL`-eligible); the same guard is CONDITIONAL (blocks
    `WILL_FAIL`) under each of six perturbations, one fixture apiece. The
    `null`/span-absent cases are the stub-defeating halves: an
    implementation that treats a missing scope as an empty one, or that
    recognises `for` headers by TEXT rather than position, passes the
    others and fails these.
    """
    env = frozenset({"does_volume_tracking"})
    base_scope = ["if does_volume_tracking()", "for op in dispenses"]
    base_lineno = 1235
    base_span = (1231, 1235)

    # The base case itself: fully recognised, may emit WILL_FAIL.
    assert volume_guard_is_unconditional(base_scope, base_lineno, base_span, env) is True

    # 1. An added is_disabled attribute test -- unrecognised (UnaryOp, no call).
    with_is_disabled = [
        "if not op.resource.tracker.is_disabled",
        "if does_volume_tracking()",
        "for op in dispenses",
    ]
    assert volume_guard_is_unconditional(with_is_disabled, base_lineno, base_span, env) is False

    # 2. A second `for` header whose span does NOT contain caller_lineno --
    # R1 identifies a NODE (this guard's own for_span), never a shape;
    # a second, non-B1 for entry never rescues a guard whose OWN for_span
    # fails position containment.
    second_for_header = ["if does_volume_tracking()", "for inner_op in something", "for op in dispenses"]
    mismatched_span = (1300, 1310)
    assert volume_guard_is_unconditional(second_for_header, base_lineno, mismatched_span, env) is False

    # 3. The same for entry with for_span absent -- the stub-defeating half
    # against a text-matching implementation.
    assert volume_guard_is_unconditional(base_scope, base_lineno, None, env) is False

    # 4. A while header -- never recognised, independently of env.
    while_header = ["if does_volume_tracking()", "while some_cond"]
    assert volume_guard_is_unconditional(while_header, base_lineno, base_span, env) is False

    # 5. An "else of: if does_volume_tracking()" entry -- negated enclosure,
    # never recognised under any env.
    else_of_entry = ["else of: if does_volume_tracking()", "for op in dispenses"]
    assert volume_guard_is_unconditional(else_of_entry, base_lineno, base_span, env) is False

    # 6. caller_scope: null -- the other stub-defeating half.
    assert volume_guard_is_unconditional(None, None, base_span, env) is False


def test_compute_volume_bridge_direct_on_synthetic_receiver() -> None:
    """`compute_volume_bridge` itself, exercised directly against a
    synthetic receiver + tracker pair -- at a level BELOW the whole survey
    pipeline, mirroring this file's own module-docstring convention (`test_
    ac_13_15_i_five_negative_fixtures_all_widen` does the same for the
    channel bridge). Confirms the mechanic end-to-end: B1 binds `op`, P8
    pairs `resource -> resources`/`volume -> vols`, P1c types
    `Widget.tracker -> Tracker`, P7 anchors `Tracker`, and the bridge
    attaches `Tracker.spend`'s one guard with `direction == "decreasing"`.
    """
    source = '''
class Op:
    resource: "Widget"
    volume: float

class Widget:
    def __init__(self):
        self.tracker = Tracker(cap=1.0)

class Tracker:
    def __init__(self, cap):
        self.cap = cap
        self.used = 0.0

    def get_used(self):
        return self.used

    def get_free(self):
        return self.cap - self.get_used()

    def spend(self, volume):
        if volume - self.get_used() > 1e-6:
            raise TooLittleError("nope")
        self.used -= volume

    def fill(self, volume):
        if volume - self.get_free() > 1e-6:
            raise TooMuchError("nope")
        self.used += volume

class R:
    def method(self, resources, vols):
        ops = [Op(resource=r, volume=v) for r, v in zip(resources, vols)]
        for op in ops:
            op.resource.tracker.spend(op.volume)
'''
    tree = ast.parse(source)
    class_nodes = {n.name: n for n in ast.iter_child_nodes(tree) if isinstance(n, ast.ClassDef)}
    class_modules = {name: "synthetic" for name in class_nodes}
    volume_state_exceptions = frozenset({"TooLittleError", "TooMuchError"})
    anchors = compute_volume_anchors(class_nodes, volume_state_exceptions)
    assert "Tracker" in anchors
    assert anchors["Tracker"].used_volume_accessor == "get_used"
    assert anchors["Tracker"].free_volume_accessor == "get_free"
    assert anchors["Tracker"].anchored_field == "used"

    survey_records = [
        SurveyRecord(
            qualname="R.method",
            class_name="R",
            module="synthetic",
            file="<synthetic>",
            lineno=1,
            params=("self", "resources", "vols"),
            findings=(),
            delegates_to=(),
            unresolved_calls=(),
            dropped_calls=(
                DroppedCall(expr="op.resource.tracker.spend", lineno=35, scope_trail=["for op in ops"]),
            ),
        ),
        SurveyRecord(
            qualname="Tracker.spend",
            class_name="Tracker",
            module="synthetic",
            file="<synthetic>",
            lineno=1,
            params=("self", "volume"),
            findings=(
                SurveyFinding(
                    kind="raise_guard",
                    condition="volume - self.get_used() > 1e-06",
                    raises="TooLittleError",
                    scope_trail=("if volume - self.get_used() > 1e-06",),
                    mentions_params=("self", "volume"),
                    lineno=1,
                ),
            ),
            delegates_to=(),
            unresolved_calls=(),
            dropped_calls=(),
        ),
    ]
    index = build_index(survey_records)
    stamp = survey_stamp()
    guards = compute_volume_bridge(
        ("synthetic", "R.method"),
        index,
        receiver_node=class_nodes["R"],
        class_index=class_nodes,
        class_modules=class_modules,
        volume_anchors=anchors,
        stamp=stamp,
    )
    assert len(guards) == 1
    (guard,) = guards
    assert guard["via"] == "op.resource.tracker.spend"
    assert guard["raises"] == "TooLittleError"
    assert guard["cell_param"] == "resources"
    assert guard["amount_param"] == "vols"
    assert guard["direction"] == "decreasing"
    assert guard["for_span"][0] <= guard["for_span"][1]
    # (260903, T25) P10: attached verbatim from the one matching
    # dropped_calls record -- disjoint from `guard["scope_trail"]`, which
    # stays the callee's own (`Tracker.spend`'s `if volume - ...`).
    assert guard["caller_scope"] == ["for op in ops"]
    assert guard["caller_lineno"] == 35
    assert guard["scope_trail"] == ["if volume - self.get_used() > 1e-06"]


# ---------------------------------------------------------------------------
# T30a (spec 260904 §15.2, increment 6): InlinedGuard.predicate -- additive,
# populated at construction from predicate_ast.parse(finding.condition),
# `condition` retained as the source of truth (main spec boundary row,
# 260901_plr-sema-pre-corpus-spec.md:2532).
# ---------------------------------------------------------------------------


def test_inlined_guard_predicate_is_populated_and_condition_retained() -> None:
    rec = _synthetic_record(
        "Widget.frobnicate", class_name="Widget", findings=(_synthetic_finding(42),)
    )
    index = build_index([rec])

    contract = derive_contract("synthetic.module", "Widget.frobnicate", index)

    assert len(contract.guards) == 1
    (guard,) = contract.guards
    # `_synthetic_finding` always carries condition "x > 0" (see above).
    assert guard.condition == "x > 0"
    assert guard.predicate == parse_predicate("x > 0")
    assert guard.predicate != Opaque("x > 0")


def test_inlined_guard_predicate_is_true_for_unconditional_guard() -> None:
    rec = SurveyRecord(
        qualname="Widget.frobnicate",
        class_name="Widget",
        module="synthetic.module",
        file="<synthetic>",
        lineno=1,
        params=("self",),
        findings=(
            SurveyFinding(
                kind="raise_guard",
                condition=None,
                raises="ValueError",
                scope_trail=(),
                mentions_params=(),
                lineno=7,
            ),
        ),
        delegates_to=(),
        unresolved_calls=(),
    )
    index = build_index([rec])

    contract = derive_contract("synthetic.module", "Widget.frobnicate", index)

    assert len(contract.guards) == 1
    (guard,) = contract.guards
    assert guard.condition is None
    assert guard.predicate == TRUE()


def test_guard_to_json_emits_predicate_alongside_condition() -> None:
    rec = _synthetic_record(
        "Widget.frobnicate", class_name="Widget", findings=(_synthetic_finding(42),)
    )
    index = build_index([rec])
    contract = derive_contract("synthetic.module", "Widget.frobnicate", index)
    (guard,) = contract.guards

    guard_json = _guard_to_json(guard)

    assert guard_json["condition"] == "x > 0"
    assert "predicate" in guard_json
    assert guard_json["predicate"]["node"] != "" and isinstance(guard_json["predicate"], dict)


def test_guard_predicate_unparsed_reason_tolerates_a_record_missing_predicate() -> None:
    """The 'reader accepts records without it' half of T30a's additive-field
    contract: `plr_sema.check`'s existing guard-to-Finding path never reads
    `guard["predicate"]` at all (only `condition`/`site`), so a guard dict
    from an un-regenerated (pre-T30a) artifact -- one with no `predicate`
    key whatsoever -- produces the IDENTICAL Finding as one that carries it.
    """
    from plr_sema.check import _finding_from_guard

    rec = _synthetic_record(
        "Widget.frobnicate", class_name="Widget", findings=(_synthetic_finding(42),)
    )
    index = build_index([rec])
    contract = derive_contract("synthetic.module", "Widget.frobnicate", index)
    (guard,) = contract.guards

    with_predicate = _guard_to_json(guard)
    without_predicate = dict(with_predicate)
    del without_predicate["predicate"]
    assert "predicate" not in without_predicate

    finding_with = _finding_from_guard("op-1", with_predicate)
    finding_without = _finding_from_guard("op-1", without_predicate)

    assert finding_with == finding_without


# ---------------------------------------------------------------------------
# T30b (spec 260904 §15.3/§15.4 D1, T30b, increment 6): param_defaults and
# the alpha/beta local-binding idioms.
# ---------------------------------------------------------------------------


def _func_node(source: str) -> ast.FunctionDef:
    """Parse ONE synthetic function/method definition and return its own
    AST node -- the same shape `build_plr_function_index` would hand
    `compute_local_bindings_for_guard`/`param_defaults_from_function`, but
    without touching the filesystem (mirrors
    `scan_dropped_receiver_calls_in_source`'s own convention above)."""
    tree = ast.parse(source)
    (node,) = tree.body
    assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    return node


# ---- param_defaults (D1) --------------------------------------------------


def test_param_defaults_restricted_to_constants() -> None:
    node = _func_node(
        "def f(self, a, b=None, c=3, d='x', e=1.5, f=True, g=[], h=SOME_CALL(), i=OTHER, *, j=None, k=NAME_DEFAULT):\n"
        "    pass\n"
    )
    defaults = param_defaults_from_function(node)
    assert defaults == {"b": None, "c": 3, "d": "x", "e": 1.5, "f": True, "j": None}
    # g/h/i/k are non-Constant (list display, call, bare name) -- OMITTED,
    # never guessed (fail-closed), and `a`/`self` have no default at all.
    assert "g" not in defaults and "h" not in defaults and "i" not in defaults and "k" not in defaults
    assert "a" not in defaults and "self" not in defaults


def test_param_defaults_real_transfer_and_pick_up_tips(plr_function_index) -> None:
    """Task brief's own named assertion: `LiquidHandler.transfer` gets
    `target_vols`/`ratios`/`source_vol` -> `None`, and `pick_up_tips` gets
    `offsets`/`use_channels` -> `None` -- read from the REAL vendored PLR
    source at the pinned submodule commit."""
    key = ("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler.transfer")
    lineno = next(ln for (mod, qn, ln) in plr_function_index if (mod, qn) == key)
    node = plr_function_index[(*key, lineno)]
    defaults = param_defaults_from_function(node)
    assert defaults["target_vols"] is None
    assert defaults["ratios"] is None
    assert defaults["source_vol"] is None

    key2 = ("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler.pick_up_tips")
    lineno2 = next(ln for (mod, qn, ln) in plr_function_index if (mod, qn) == key2)
    node2 = plr_function_index[(*key2, lineno2)]
    defaults2 = param_defaults_from_function(node2)
    assert defaults2["offsets"] is None
    assert defaults2["use_channels"] is None


# ---- free_var_names --------------------------------------------------------


def test_free_var_names_walks_predicate_and_term_positions() -> None:
    # 260907 amendment (G7, T35): `self.head.has_tip` is now ONE `EnvRef`
    # leaf (`EnvRef(("self", "head", "has_tip"), None)`, shape (1) subsuming
    # the whole chain) rather than `Attr(Attr(Var("self"), "head"),
    # "has_tip")` -- so "self" is no longer a free var at all (it is the
    # EnvRef's own path root, never exposed as a bare `Var`). This exercises
    # `free_var_names`'s EnvRef branch (args is None -> no free names).
    pred = parse_predicate("len(not_tip_spots) > 0 and self.head.has_tip == other")
    assert free_var_names(pred) == {"not_tip_spots", "other"}


# ---- alpha/beta AC-15.2 fixtures (synthetic, one per named shape) --------


def test_alpha_binds_filtered_comprehension() -> None:
    node = _func_node(
        "def m(self, tip_spots):\n"
        "    not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, TipSpot)]\n"
        "    if len(not_tip_spots) > 0:\n"
        "        raise TypeError('x')\n"
    )
    pred = parse_predicate("len(not_tip_spots) > 0")
    bindings = compute_local_bindings_for_guard(node, pred, guard_lineno=4)
    assert bindings == (
        {
            "idiom": "alpha",
            "x": "not_tip_spots",
            "iter": "tip_spots",
            "pred": {
                "node": "Not",
                "predicate": {"node": "IsInstance", "term": {"node": "Var", "name": "ts"}, "types": ["TipSpot"]},
            },
        },
    )


def test_alpha_admits_tuple_type_form() -> None:
    node = _func_node(
        "def m(self, tip_spots):\n"
        "    not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, (TipSpot, Trash))]\n"
        "    if len(not_tip_spots) > 0:\n"
        "        raise TypeError('x')\n"
    )
    pred = parse_predicate("len(not_tip_spots) > 0")
    (binding,) = compute_local_bindings_for_guard(node, pred, guard_lineno=4)
    assert binding["pred"]["predicate"]["types"] == ["TipSpot", "Trash"]


def test_beta_binds_length_range_shape() -> None:
    node = _func_node(
        "def m(self, tip_spots, use_channels=None):\n"
        "    use_channels = use_channels or list(range(len(tip_spots)))\n"
        "    assert len(use_channels) == len(tip_spots)\n"
    )
    pred = parse_predicate("len(use_channels) == len(tip_spots)")
    bindings = compute_local_bindings_for_guard(node, pred, guard_lineno=3)
    assert bindings == (
        {"idiom": "beta", "x": "use_channels", "param": "tip_spots", "default_shape": "range"},
    )


def test_beta_binds_length_repeat_shape() -> None:
    node = _func_node(
        "def m(self, tip_spots, offsets=None):\n"
        "    offsets = offsets or [Coordinate.zero()] * len(tip_spots)\n"
        "    assert len(tip_spots) == len(offsets)\n"
    )
    pred = parse_predicate("len(tip_spots) == len(offsets)")
    (binding,) = compute_local_bindings_for_guard(node, pred, guard_lineno=3)
    assert binding == {"idiom": "beta", "x": "offsets", "param": "tip_spots", "default_shape": "repeat"}


# -- five AC-15.2 fail-closed fixtures, one apiece --------------------------


def test_fail_closed_second_write_to_x_binds_nothing() -> None:
    node = _func_node(
        "def m(self, tip_spots):\n"
        "    not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, TipSpot)]\n"
        "    not_tip_spots = list(not_tip_spots)\n"
        "    if len(not_tip_spots) > 0:\n"
        "        raise TypeError('x')\n"
    )
    pred = parse_predicate("len(not_tip_spots) > 0")
    assert compute_local_bindings_for_guard(node, pred, guard_lineno=5) == ()


def test_fail_closed_assignment_in_sibling_branch_binds_nothing() -> None:
    node = _func_node(
        "def m(self, tip_spots, flag):\n"
        "    if flag:\n"
        "        not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, TipSpot)]\n"
        "    if len(not_tip_spots) > 0:\n"
        "        raise TypeError('x')\n"
    )
    pred = parse_predicate("len(not_tip_spots) > 0")
    assert compute_local_bindings_for_guard(node, pred, guard_lineno=4) == ()


def test_fail_closed_three_operand_or_chain_declines_beta() -> None:
    node = _func_node(
        "def m(self, tip_spots, use_channels=None):\n"
        "    use_channels = use_channels or self._default_use_channels or list(range(len(tip_spots)))\n"
        "    assert len(use_channels) == len(tip_spots)\n"
    )
    pred = parse_predicate("len(use_channels) == len(tip_spots)")
    assert compute_local_bindings_for_guard(node, pred, guard_lineno=3) == ()


def test_fail_closed_assignment_after_guard_binds_nothing() -> None:
    node = _func_node(
        "def m(self, tip_spots):\n"
        "    if len(not_tip_spots) > 0:\n"
        "        raise TypeError('x')\n"
        "    not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, TipSpot)]\n"
    )
    pred = parse_predicate("len(not_tip_spots) > 0")
    assert compute_local_bindings_for_guard(node, pred, guard_lineno=2) == ()


def test_fail_closed_for_header_targeting_x_binds_nothing() -> None:
    node = _func_node(
        "def m(self, tip_spots, items):\n"
        "    not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, TipSpot)]\n"
        "    for not_tip_spots in items:\n"
        "        if len(not_tip_spots) > 0:\n"
        "            raise TypeError('x')\n"
    )
    pred = parse_predicate("len(not_tip_spots) > 0")
    assert compute_local_bindings_for_guard(node, pred, guard_lineno=4) == ()


# -- round-1 fixtures: beta-preserving rebinding, iterand single-write ------


def test_beta_preserving_rebinding_survives() -> None:
    node = _func_node(
        "def m(self, tip_spots, x=None):\n"
        "    x = x or list(range(len(tip_spots)))\n"
        "    x = [f(e) for e in x]\n"
        "    assert len(x) == len(tip_spots)\n"
    )
    pred = parse_predicate("len(x) == len(tip_spots)")
    (binding,) = compute_local_bindings_for_guard(node, pred, guard_lineno=4)
    assert binding == {"idiom": "beta", "x": "x", "param": "tip_spots", "default_shape": "range"}


def test_zip_rebinding_does_not_preserve_beta() -> None:
    node = _func_node(
        "def m(self, tip_spots, y, x=None):\n"
        "    x = x or list(range(len(tip_spots)))\n"
        "    x = [f(a, b) for a, b in zip(y, x)]\n"
        "    assert len(x) == len(tip_spots)\n"
    )
    pred = parse_predicate("len(x) == len(tip_spots)")
    assert compute_local_bindings_for_guard(node, pred, guard_lineno=4) == ()


def test_second_write_to_alpha_iterand_binds_nothing() -> None:
    """TWO explicit writes to the iterand (not one -- see
    `test_one_write_to_beta_iterand_before_binding_is_tolerated`'s own
    docstring for why exactly one is tolerated) is what round-1's own "a
    second write to alpha's iter name binds nothing" fixture means."""
    node = _func_node(
        "def m(self, tip_spots):\n"
        "    not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, TipSpot)]\n"
        "    tip_spots = list(tip_spots)\n"
        "    tip_spots = list(tip_spots)\n"
        "    if len(not_tip_spots) > 0:\n"
        "        raise TypeError('x')\n"
    )
    pred = parse_predicate("len(not_tip_spots) > 0")
    assert compute_local_bindings_for_guard(node, pred, guard_lineno=5) == ()


def test_one_write_to_beta_iterand_before_binding_is_tolerated() -> None:
    """Empirical grounding for the ">1" iterand threshold (see
    `bindings._shape_and_single_write_ok`'s own comment): `aspirate`'s real
    beta population rebinds its OWN iterand (`use_channels`) exactly once,
    BEFORE the beta assignment -- this must still bind."""
    node = _func_node(
        "def m(self, resources, use_channels=None, flow_rates=None):\n"
        "    use_channels = use_channels or list(range(len(resources)))\n"
        "    flow_rates = flow_rates or [None] * len(use_channels)\n"
        "    assert len(flow_rates) == 5\n"
    )
    # Predicate mentions ONLY `flow_rates` -- `use_channels` is a
    # perfectly valid SEPARATE beta binding of its own (over `resources`),
    # which would be a distinct assertion; keeping this fixture to one
    # free name isolates the property under test (the iterand's own
    # single-explicit-write tolerance).
    pred = parse_predicate("len(flow_rates) == 5")
    (binding,) = compute_local_bindings_for_guard(node, pred, guard_lineno=4)
    assert binding == {"idiom": "beta", "x": "flow_rates", "param": "use_channels", "default_shape": "repeat"}


def test_two_writes_to_beta_iterand_binds_nothing() -> None:
    node = _func_node(
        "def m(self, resources, use_channels=None, flow_rates=None):\n"
        "    use_channels = use_channels or list(range(len(resources)))\n"
        "    flow_rates = flow_rates or [None] * len(use_channels)\n"
        "    use_channels = list(use_channels)\n"
        "    assert len(flow_rates) == len(use_channels)\n"
    )
    pred = parse_predicate("len(flow_rates) == len(use_channels)")
    assert compute_local_bindings_for_guard(node, pred, guard_lineno=5) == ()


# -- nested-Opaque binding (invalid_channels) -------------------------------


def test_alpha_binds_the_now_g7_g8_readable_filter() -> None:
    """The `if` clause `c not in self.head` used to parse to `Opaque`;
    after the 260907 amendment (G7 `EnvRef`, G8 `in`/`not in`, T35) it
    parses to `Cmp(Var("c"), "not in", EnvRef(("self", "head"), None))` --
    alpha still binds the TERM regardless (a binding rule, not a decision
    rule, §15.3's own 'that asymmetry is the point'), but the bound term's
    OWN inner predicate is no longer `Opaque`. §15.7's worked example
    (`:409`) turns on exactly this: the guard moves from
    `guard_predicate_unparsed` to `guard_env_dependent` because this
    filter is now readable, not because its truth value changed."""
    node = _func_node(
        "def m(self, channels):\n"
        "    invalid_channels = [c for c in channels if c not in self.head]\n"
        "    if not len(invalid_channels) == 0:\n"
        "        raise ValueError('x')\n"
    )
    pred = parse_predicate("not len(invalid_channels) == 0")
    (binding,) = compute_local_bindings_for_guard(node, pred, guard_lineno=3)
    assert binding["idiom"] == "alpha"
    assert binding["pred"] == {
        "node": "Cmp",
        "left": {"node": "Var", "name": "c"},
        "op": "not in",
        "right": {"node": "EnvRef", "path": ["self", "head"], "args": None},
    }


# ---- the measured population against the real, pinned PLR surface --------


def test_real_alpha_population_meets_ac_15_2_floor(plr_function_index) -> None:
    """AC-15.2's floor: >= 3 alpha entries, naming pick_up_tips (:496 in
    the guard-independent catalog's own function-start-relative numbering
    -- checked here by CONDITION shape, not by a hardcoded lineno, since
    `compute_all_local_bindings` is keyed by function, not by guard site),
    drop_tips, and `_check_containers` by name."""
    seen: dict[str, list[dict]] = {}
    for (module, qualname, _lineno), node in plr_function_index.items():
        if module != "pylabrobot.liquid_handling.liquid_handler":
            continue
        for b in compute_all_local_bindings(node):
            if b["idiom"] == "alpha":
                seen.setdefault(qualname, []).append(b)

    assert len(sum(seen.values(), [])) >= 3
    assert seen["LiquidHandler.pick_up_tips"][0]["x"] == "not_tip_spots"
    assert seen["LiquidHandler.drop_tips"][0]["x"] == "not_tip_spots"
    assert seen["LiquidHandler._check_containers"][0]["x"] == "not_containers"
    # :407's invalid_channels -- alpha binds it; after the 260907 amendment
    # (G7 EnvRef, G8 in/not in, T35) its inner filter `c not in self.head`
    # is a `Cmp` containing an `EnvRef`, no longer `Opaque`.
    inner = seen["LiquidHandler._make_sure_channels_exist"][0]["pred"]
    assert inner["node"] == "Cmp"
    assert inner["op"] == "not in"
    assert inner["right"] == {"node": "EnvRef", "path": ["self", "head"], "args": None}


def test_real_beta_population_meets_ac_15_2_floor(plr_function_index) -> None:
    """AC-15.2's floor: >= 6 beta entries; this pin's measured population is
    published in the T30b commit report (>= 8, incl. all named sites --
    see the module docstring's own reasoning for why the catalog is wider
    than any one guard's `bindings`)."""
    beta: list[tuple[str, dict]] = []
    for (module, qualname, _lineno), node in plr_function_index.items():
        if module != "pylabrobot.liquid_handling.liquid_handler":
            continue
        for b in compute_all_local_bindings(node):
            if b["idiom"] == "beta":
                beta.append((qualname, b))

    assert len(beta) >= 6
    by_qual = {}
    for qualname, b in beta:
        by_qual.setdefault(qualname, []).append(b["x"])
    assert "offsets" in by_qual["LiquidHandler.pick_up_tips"]
    assert "offsets" in by_qual["LiquidHandler.drop_tips"]
    assert {"flow_rates", "liquid_height", "blow_out_air_volume"} <= set(by_qual["LiquidHandler.aspirate"])
    assert {"flow_rates", "liquid_height", "blow_out_air_volume"} <= set(by_qual["LiquidHandler.dispense"])
    # offsets at aspirate/dispense's own beta-shaped :962/:1156 is EXCLUDED
    # -- its second write is a `zip(...)` rebind, which does not preserve.
    assert "offsets" not in by_qual.get("LiquidHandler.aspirate", ())
    assert "offsets" not in by_qual.get("LiquidHandler.dispense", ())


def test_derive_contract_populates_bindings_from_function_index(
    survey_index: dict[tuple[str, str], SurveyRecord], plr_function_index
) -> None:
    contract = derive_contract(
        "pylabrobot.liquid_handling.liquid_handler",
        "LiquidHandler.pick_up_tips",
        survey_index,
        function_index=plr_function_index,
    )
    by_lineno = {g.site.lineno: g for g in contract.guards}
    assert by_lineno[498].bindings[0]["idiom"] == "alpha"
    assert by_lineno[498].bindings[0]["x"] == "not_tip_spots"
    assert by_lineno[522].bindings[0]["idiom"] == "beta"
    assert by_lineno[522].bindings[0]["x"] == "offsets"
    assert by_lineno[409].bindings[0]["idiom"] == "alpha"  # depth-1 guard, own delegate body
    # a guard with no binding-eligible free names (e.g. the backend-can-
    # pick-up-tip guard) still has an explicit empty tuple, never a crash.
    assert by_lineno[514].bindings == ()


def test_derive_contract_without_function_index_leaves_bindings_empty(
    survey_index: dict[tuple[str, str], SurveyRecord],
) -> None:
    """Backward compatibility: every pre-T30b caller of `derive_contract`
    (no `function_index=`) gets `bindings == ()` on every guard -- the
    default-off half of the additive contract."""
    contract = derive_contract(
        "pylabrobot.liquid_handling.liquid_handler", "LiquidHandler.pick_up_tips", survey_index
    )
    assert all(g.bindings == () for g in contract.guards)


def test_guard_to_json_emits_bindings_key(
    survey_index: dict[tuple[str, str], SurveyRecord], plr_function_index
) -> None:
    contract = derive_contract(
        "pylabrobot.liquid_handling.liquid_handler",
        "LiquidHandler.pick_up_tips",
        survey_index,
        function_index=plr_function_index,
    )
    (guard_498,) = [g for g in contract.guards if g.site.lineno == 498]
    payload = _guard_to_json(guard_498)
    assert payload["bindings"] == [
        {
            "idiom": "alpha",
            "x": "not_tip_spots",
            "iter": "tip_spots",
            "pred": {
                "node": "Not",
                "predicate": {"node": "IsInstance", "term": {"node": "Var", "name": "ts"}, "types": ["TipSpot"]},
            },
        }
    ]


# ---------------------------------------------------------------------------
# T36 (260907, spec 260904 §15.4/§15.10 refined): E-UNCOND(5)'s K-body fact,
# `compute_reachability_clear` + its wiring into `InlinedGuard`/the JSON
# writer. Synthetic fixtures, one per named shape, then the real corpus.
# ---------------------------------------------------------------------------


def test_reachability_clear_true_after_a_conditional_raise() -> None:
    """An earlier RAISE does not block (the refined clause's own point) --
    only Return/Try/With/Break/Continue do."""
    node = _func_node(
        "def m(self, x):\n"
        "    if x < 0:\n"
        "        raise ValueError('neg')\n"
        "    assert x < 100\n"
    )
    assert compute_reachability_clear(node, guard_lineno=4) is True


def test_reachability_clear_false_after_a_conditional_return() -> None:
    node = _func_node(
        "def m(self, x):\n"
        "    if x < 0:\n"
        "        return\n"
        "    assert x < 100\n"
    )
    assert compute_reachability_clear(node, guard_lineno=4) is False


def test_reachability_clear_false_inside_try() -> None:
    node = _func_node(
        "def m(self, x):\n"
        "    try:\n"
        "        assert x < 100\n"
        "    except Exception:\n"
        "        pass\n"
    )
    assert compute_reachability_clear(node, guard_lineno=3) is False


def test_reachability_clear_false_inside_with() -> None:
    node = _func_node(
        "def m(self, x):\n"
        "    with open('f') as fh:\n"
        "        assert x < 100\n"
    )
    assert compute_reachability_clear(node, guard_lineno=3) is False


def test_reachability_clear_false_after_break_inside_a_loop() -> None:
    """Conservative, per spec text: the guard need not be lexically inside
    the loop the `break` belongs to -- ANY earlier `Break`/`Continue`
    anywhere in `K` blocks it."""
    node = _func_node(
        "def m(self, xs):\n"
        "    for x in xs:\n"
        "        if x < 0:\n"
        "            break\n"
        "    assert len(xs) > 0\n"
    )
    assert compute_reachability_clear(node, guard_lineno=5) is False


def test_reachability_clear_false_when_guard_lineno_absent_from_k() -> None:
    """Defensive fail-closed default, mirroring
    `compute_local_bindings_for_guard`'s identical fallback -- should not
    occur for a `finding.lineno` that genuinely came from `K`'s own body."""
    node = _func_node("def m(self, x):\n    assert x < 100\n")
    assert compute_reachability_clear(node, guard_lineno=999) is False


def test_real_reachability_clear_pick_up_tips_502_and_522(plr_function_index) -> None:
    """The task brief's own named assertion: `pick_up_tips`'s duplicate-
    `use_channels` guard (`:502`) and its `tip_spots`/`offsets`/
    `use_channels` length-triple guard (`:522`) both resolve `True` --
    `pick_up_tips` has no Return/Try/With/Break/Continue anywhere in its
    own body before either line (T32's measured defect: these two sites
    produced 0 WILL_FAIL on their own mutants because the pre-T36 default
    fails closed on `None`)."""
    key = ("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler.pick_up_tips")
    lineno = next(ln for (mod, qn, ln) in plr_function_index if (mod, qn) == key)
    node = plr_function_index[(*key, lineno)]
    assert compute_reachability_clear(node, guard_lineno=502) is True
    assert compute_reachability_clear(node, guard_lineno=522) is True


def test_real_reachability_clear_check_no_lid_117_is_false(plr_function_index) -> None:
    """`_check_no_lid`'s own (depth-0) `:117` resolves `False` -- blocked
    by the earlier `return` at `liquid_handler.py:114` (`if lidded is
    None: return`). At depth >= 1 (inlined into `aspirate`/`dispense`)
    E-UNCOND(4) already disposes of this site before clause (5) is ever
    reached (`test_check_no_lid_117_by_name_is_unknown_via_depth`,
    `tests/test_predicate.py`); this is the standalone entry where clause
    (5) is the one doing the work, and it agrees with the depth-1 outcome
    for an unrelated reason."""
    key = ("pylabrobot.liquid_handling.liquid_handler", "_check_no_lid")
    lineno = next(ln for (mod, qn, ln) in plr_function_index if (mod, qn) == key)
    node = plr_function_index[(*key, lineno)]
    assert compute_reachability_clear(node, guard_lineno=117) is False


def test_derive_contract_populates_reachability_clear_from_function_index(
    survey_index: dict[tuple[str, str], SurveyRecord], plr_function_index
) -> None:
    contract = derive_contract(
        "pylabrobot.liquid_handling.liquid_handler",
        "LiquidHandler.pick_up_tips",
        survey_index,
        function_index=plr_function_index,
    )
    by_lineno = {g.site.lineno: g for g in contract.guards}
    assert by_lineno[502].reachability_clear is True
    assert by_lineno[522].reachability_clear is True


def test_derive_contract_without_function_index_leaves_reachability_clear_false(
    survey_index: dict[tuple[str, str], SurveyRecord],
) -> None:
    """Backward compatibility, identical in spirit to `bindings`'s own
    default-off fixture: every pre-T36 caller of `derive_contract` (no
    `function_index=`) gets `reachability_clear is False` on every guard."""
    contract = derive_contract(
        "pylabrobot.liquid_handling.liquid_handler", "LiquidHandler.pick_up_tips", survey_index
    )
    assert all(g.reachability_clear is False for g in contract.guards)


def test_guard_to_json_emits_reachability_clear_key(
    survey_index: dict[tuple[str, str], SurveyRecord], plr_function_index
) -> None:
    contract = derive_contract(
        "pylabrobot.liquid_handling.liquid_handler",
        "LiquidHandler.pick_up_tips",
        survey_index,
        function_index=plr_function_index,
    )
    (guard_502,) = [g for g in contract.guards if g.site.lineno == 502]
    payload = _guard_to_json(guard_502)
    assert payload["reachability_clear"] is True


def test_build_derived_contracts_payload_adds_param_defaults(
    survey_records: list[SurveyRecord],
    survey_index: dict[tuple[str, str], SurveyRecord],
    plr_function_index,
) -> None:
    stamp = survey_stamp()
    payload = build_derived_contracts_payload(survey_records, survey_index, stamp, function_index=plr_function_index)
    contracts = payload["contracts"]
    key = next(k for k in contracts if k.startswith("LiquidHandler.transfer"))
    assert contracts[key]["param_defaults"]["target_vols"] is None
    assert contracts[key]["param_defaults"]["ratios"] is None
    assert contracts[key]["param_defaults"]["source_vol"] is None


def test_build_derived_contracts_payload_omits_param_defaults_without_function_index(
    survey_records: list[SurveyRecord], survey_index: dict[tuple[str, str], SurveyRecord]
) -> None:
    stamp = survey_stamp()
    payload = build_derived_contracts_payload(survey_records, survey_index, stamp)
    contracts = payload["contracts"]
    key = next(k for k in contracts if k.startswith("LiquidHandler.transfer"))
    assert "param_defaults" not in contracts[key]


# ---------------------------------------------------------------------------
# T35 (260907 amendment, spec 260904 S15.2's normative box, round 2 A-C1):
# G7's PLR-layer test on a shape-(2) EnvRef, applied post-parse in
# derive.bindings against `receiver_state.build_plr_function_index`.
# ---------------------------------------------------------------------------


def _synthetic_index_and_function_index(with_helper: bool):
    """A synthetic `Foo.bar` whose guard reads `self._helper()` -- a
    length-2 `self.<name>(...)` EnvRef candidate. `with_helper=True` puts
    `_helper` in the function index (an indexed PLR-layer method of the
    SAME receiver class -- refused); `with_helper=False` omits it (an
    unindexed read -- admitted)."""
    bar_src = "def bar(self):\n    if self._helper():\n        raise ValueError('x')\n"
    bar_node = _func_node(bar_src)
    finding = SurveyFinding(
        kind="raise_guard",
        condition="self._helper()",
        raises="ValueError",
        scope_trail=(),
        mentions_params=(),
        lineno=2,
    )
    rec = SurveyRecord(
        qualname="Foo.bar",
        class_name="Foo",
        module="synthetic_mod",
        file="synthetic_mod.py",
        lineno=1,
        params=("self",),
        findings=(finding,),
        delegates_to=(),
        unresolved_calls=(),
    )
    index = {("synthetic_mod", "Foo.bar"): rec}
    function_index = {("synthetic_mod", "Foo.bar", 1): bar_node}
    if with_helper:
        helper_node = _func_node("def _helper(self):\n    return True\n")
        function_index[("synthetic_mod", "Foo._helper", 5)] = helper_node
    return index, function_index


def test_g7_index_refusal_indexed_method_becomes_opaque() -> None:
    """`self._helper()` where `_helper` IS an indexed method of `Foo` (the
    receiver class) is refused -- a coverage gap the closure could have
    inlined, not a missing observation."""
    index, function_index = _synthetic_index_and_function_index(with_helper=True)
    contract = derive_contract("synthetic_mod", "Foo.bar", index, function_index=function_index)
    (guard,) = contract.guards
    assert isinstance(guard.predicate, Opaque)
    assert count_var_self(guard.predicate) == 0


def test_g7_index_absent_method_stays_env_ref() -> None:
    """The same shape, but `_helper` is ABSENT from the function index --
    admitted as an `EnvRef` (an environment read the grammar recognises)."""
    index, function_index = _synthetic_index_and_function_index(with_helper=False)
    contract = derive_contract("synthetic_mod", "Foo.bar", index, function_index=function_index)
    (guard,) = contract.guards
    assert guard.predicate == EnvRef(("self", "_helper"), ())


def test_g7_no_function_index_refuses_every_k1_candidate() -> None:
    """Fail-closed default: omitting `function_index` entirely (T30a's
    exact calling convention) refuses EVERY k==1 shape-(2) candidate,
    exactly like `InlinedGuard.bindings`'s own no-index default -- even
    though `_helper` is not defined anywhere in this synthetic index."""
    index, _function_index = _synthetic_index_and_function_index(with_helper=False)
    contract = derive_contract("synthetic_mod", "Foo.bar", index)
    (guard,) = contract.guards
    assert isinstance(guard.predicate, Opaque)


def test_g7_shape2_len3_never_refused_regardless_of_index() -> None:
    """A read THROUGH a receiver attribute (`len(path) >= 3`,
    `self.backend.can_pick_up_tip(...)`) is never this test's business --
    it stays an `EnvRef` even when an entry matching its OWN name exists in
    the index (the index test only ever looks at length-2 paths)."""
    bar_src = "def bar(self):\n    if self.backend.can_pick_up_tip(x):\n        raise ValueError('x')\n"
    bar_node = _func_node(bar_src)
    finding = SurveyFinding(
        kind="raise_guard",
        condition="self.backend.can_pick_up_tip(x)",
        raises="ValueError",
        scope_trail=(),
        mentions_params=(),
        lineno=2,
    )
    rec = SurveyRecord(
        qualname="Foo.bar",
        class_name="Foo",
        module="synthetic_mod",
        file="synthetic_mod.py",
        lineno=1,
        params=("self", "x"),
        findings=(finding,),
        delegates_to=(),
        unresolved_calls=(),
    )
    index = {("synthetic_mod", "Foo.bar"): rec}
    # An entry for "Foo.can_pick_up_tip" exists, but the EnvRef's path is
    # ("self", "backend", "can_pick_up_tip") -- length 3, never checked.
    function_index = {
        ("synthetic_mod", "Foo.bar", 1): bar_node,
        ("synthetic_mod", "Foo.can_pick_up_tip", 9): _func_node("def can_pick_up_tip(self, x):\n    pass\n"),
    }
    contract = derive_contract("synthetic_mod", "Foo.bar", index, function_index=function_index)
    (guard,) = contract.guards
    assert guard.predicate == EnvRef(("self", "backend", "can_pick_up_tip"), (Var("x"),))


def test_build_qualname_index_drops_lineno() -> None:
    function_index = {
        ("mod", "Foo.bar", 1): object(),
        ("mod", "Foo.bar", 50): object(),  # a second def at a different line, same qualname
        ("mod", "Foo.baz", 2): object(),
    }
    idx = build_qualname_index(function_index)
    assert idx == frozenset({("mod", "Foo.bar"), ("mod", "Foo.baz")})


def test_is_plr_layer_method_none_class_name_never_matches() -> None:
    idx = frozenset({("mod", "Foo.bar")})
    assert is_plr_layer_method(idx, "mod", None, "bar") is False
    assert is_plr_layer_method(idx, "mod", "Foo", "bar") is True
    assert is_plr_layer_method(idx, "mod", "Foo", "other") is False


def test_n_var_self_is_zero_over_the_real_regenerated_table(
    survey_records: list[SurveyRecord], survey_index: dict[tuple[str, str], SurveyRecord], plr_function_index
) -> None:
    """S15.9 block (6)'s whole-table invariant, published rather than
    assumed: no guard anywhere in the real, regenerated contract table
    contains a bare `Var("self")`."""
    stamp = survey_stamp()
    payload = build_derived_contracts_payload(survey_records, survey_index, stamp, function_index=plr_function_index)
    total = 0
    for entry in payload["contracts"].values():
        for g in entry.get("guards", ()):
            from plr_sema.derive.predicate_ast import from_json

            total += count_var_self(from_json(g["predicate"]))
    assert total == 0


# ---------------------------------------------------------------------------
# T35: `substitute` -- the alpha/beta-SUBSTITUTED tree contains_opaque/
# contains_env_ref must range over (round 2, A-C4).
# ---------------------------------------------------------------------------


def test_substitute_alpha_binding_exposes_nested_env_ref() -> None:
    """The amendment's own worked example: `:409`'s guard predicate itself
    has no `EnvRef`/`Opaque` node at all (`invalid_channels` is a plain
    `Var`) -- only the alpha-SUBSTITUTED tree does."""
    pred = parse_predicate("not len(invalid_channels) == 0")
    assert not contains_env_ref(pred)
    bindings_by_name = {
        "invalid_channels": {
            "idiom": "alpha",
            "x": "invalid_channels",
            "iter": "channels",
            "pred": {
                "node": "Cmp",
                "left": {"node": "Var", "name": "c"},
                "op": "not in",
                "right": {"node": "EnvRef", "path": ["self", "head"], "args": None},
            },
        }
    }
    substituted = substitute(pred, bindings_by_name)
    assert not contains_opaque(substituted)
    assert contains_env_ref(substituted)
    assert substituted == Not(
        Cmp(
            Len(Filtered(Var("channels"), Cmp(Var("c"), "not in", EnvRef(("self", "head"), None)))),
            "==",
            Lit(0),
        )
    )


def test_substitute_leaves_unbound_and_beta_bound_names_alone() -> None:
    """A beta binding (a LENGTH fact, not a term) and a wholly unbound name
    are both left untouched -- substitution can only ever introduce a
    `Filtered` term for an ALPHA-bound name."""
    pred = parse_predicate("len(offsets) == len(unbound)")
    substituted = substitute(pred, {"offsets": {"idiom": "beta", "x": "offsets", "param": "tip_spots", "default_shape": "repeat"}})
    assert substituted == pred


def test_substitute_recurses_into_env_ref_args() -> None:
    """A bound name appearing as an EnvRef CALL argument is substituted
    too -- `substitute` recurses into `EnvRef.args`, not just top-level
    Cmp/Is/IsInstance operands."""
    pred = parse_predicate("self.backend.f(bound_name)")
    bindings_by_name = {
        "bound_name": {
            "idiom": "alpha",
            "x": "bound_name",
            "iter": "items",
            "pred": {"node": "TRUE"},
        }
    }
    substituted = substitute(pred, bindings_by_name)
    assert isinstance(substituted, EnvRef)
    assert substituted.args == (Filtered(Var("items"), TRUE()),)
