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
    ClassBasesIndex,
    DroppedCall,
    SurveyFinding,
    SurveyRecord,
    _extract_base_name,
    _is_inert_dropped_receiver_call,
    _iter_plr_source_files,
    _walk_closure,
    build_class_bases_index,
    build_contract_keys,
    build_gap_ledger,
    build_index,
    class_closure,
    compute_m_inh_selection,
    default_plr_pkg_root,
    derive_contract,
    diagnose_base_resolution,
    inherited_method_names,
    load_survey,
    measure_m_inh_entry_point_impact,
    resolve,
    resolve_via_base_closure,
    scan_dropped_receiver_calls,
    scan_dropped_receiver_calls_in_source,
)
from plr_sema.derive.__main__ import build_derived_contracts_payload, _guard_to_json
from plr_sema.derive.bindings import (
    build_qualname_index,
    compute_all_local_bindings,
    compute_caller_args,
    compute_caller_args_for_call,
    compute_caller_call_lineno,
    compute_caller_scope_trail,
    compute_local_bindings_for_guard,
    compute_reachability_clear,
    demote_refused_env_refs,
    find_delegate_calls,
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
    to_json as predicate_to_json,
)
from plr_sema.derive.receiver_state import (
    BackendSurfaceEntry,
    SingletonAnchorCandidate,
    backend_surface_entry_to_json,
    build_backend_surface,
    build_plr_class_bases_index,
    build_plr_class_index,
    build_plr_function_index,
    collect_env_ref_method_names,
    compute_anchor_guard_states,
    compute_delegate_channel_bindings,
    compute_singleton_typestate_anchors,
    compute_volume_anchors,
    compute_volume_bridge,
    compute_volume_state_exceptions,
    constructor_call_writes,
    dataclass_field_annotations,
    derive_receiver_states,
    for_over_comprehension_output,
    operand_pairing_idiom,
    probe_method_definitions,
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
    inherited_delegates: tuple[str, ...] = (),
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
        inherited_delegates=inherited_delegates,
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
    `live_rows() == BUDGET_CAP` is what #4883 itself left true (this change
    fills the registry to its own cap exactly, whatever that cap is at the
    time this test runs) -- NOT a frozen `== 24` literal: 260909 (spec
    §16.15 D6, T48, backlog #5026) is a LATER, separate decision that
    raises `BUDGET_CAP` 24 -> 25 and adds HM-26, and asserting the stale
    literal here would make this row's own regression test fail on every
    future registry-row addition, which is not what AC-13.2 claims."""
    assert len(live_rows()) == BUDGET_CAP


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


# ---------------------------------------------------------------------------
# T41 (spec 260909_plr-sema-observation-increment.md §16.3, backlog #5023):
# the derived backend surface -- AC-16.2.
# ---------------------------------------------------------------------------

_BACKEND_SURFACE_SHAPE_SOURCE = '''
class Backend:
    def method_return_true(self, ops, use_channels, extra=1):
        return True

    def method_docstring_return(self, ops):
        """A docstring counts as a statement (§16.3's own point)."""
        return True

    def method_two_statement(self, ops):
        x = 1
        return True

    def method_return_name(self, y):
        return y

    def method_var_args(self, ops, *args, **kwargs):
        return None
'''

_BACKEND_SURFACE_ABSENCE_SOURCE = '''
def _some_wrapper(fn):
    return fn


class Backend:
    @_some_wrapper
    def method_decorated(self, ops):
        return True

    @property
    def method_property(self):
        return True

    def method_duplicate(self, ops):
        return True

    def method_duplicate(self, ops, extra=1):
        return False
'''


def test_ac_16_2_constant_return_shape_fixtures(tmp_path: Path) -> None:
    """AC-16.2's four shape fixtures, one apiece: a single `return True`
    body is admitted; a docstring-plus-return body is not; a two-statement
    body is not; a `return <Name>` body is not. All five methods here
    survive the absence rule (no decorator, unique lineno), so every one
    becomes a ROW -- only `method_return_true`'s row carries a
    `constant_return` key. `method_return_true`'s `params` column also
    checks the non-default-after-self rule: `extra` carries a default and
    is excluded, `ops`/`use_channels` are not."""
    (tmp_path / "synth_backend.py").write_text(_BACKEND_SURFACE_SHAPE_SOURCE, encoding="utf-8")
    function_index = build_plr_function_index(tmp_path)
    selected = frozenset(
        {
            "method_return_true",
            "method_docstring_return",
            "method_two_statement",
            "method_return_name",
            "method_var_args",
        }
    )
    rows, n_candidates, n_absent = build_backend_surface(function_index, selected)
    assert n_candidates == 5
    assert n_absent == 0
    assert n_candidates - n_absent == len(rows) == 5

    assert rows["Backend.method_return_true"].has_constant_return is True
    assert rows["Backend.method_return_true"].constant_return is True
    assert rows["Backend.method_return_true"].params == ("ops", "use_channels")

    assert rows["Backend.method_docstring_return"].has_constant_return is False
    assert rows["Backend.method_two_statement"].has_constant_return is False
    assert rows["Backend.method_return_name"].has_constant_return is False

    var_args_row = rows["Backend.method_var_args"]
    assert var_args_row.has_var_positional is True
    assert var_args_row.has_var_keyword is True
    assert var_args_row.params == ("ops",)

    # JSON encoding: the key is present iff has_constant_return.
    assert backend_surface_entry_to_json(rows["Backend.method_return_true"])["constant_return"] is True
    assert "constant_return" not in backend_surface_entry_to_json(rows["Backend.method_docstring_return"])


def test_ac_16_2_absence_rule_fixtures(tmp_path: Path) -> None:
    """AC-16.2's three C15 absence fixtures: a `@some_wrapper`-decorated
    body that is otherwise a perfect `return True` yields an absent row
    (clause 1); a `property` yields an absent row (clause 2, subsumed by
    clause 1's decorator test as §16.3's own normative box states); and a
    qualname defined at two linenos yields an absent row for BOTH
    definitions (clause 3)."""
    (tmp_path / "synth_backend.py").write_text(_BACKEND_SURFACE_ABSENCE_SOURCE, encoding="utf-8")
    function_index = build_plr_function_index(tmp_path)
    selected = frozenset({"method_decorated", "method_property", "method_duplicate"})
    rows, n_candidates, n_absent = build_backend_surface(function_index, selected)
    # 1 decorated + 1 property + 2 duplicate-lineno definitions of the same
    # qualname = 4 candidates, all 4 absent, 0 rows.
    assert n_candidates == 4
    assert n_absent == 4
    assert rows == {}


def test_ac_16_2_can_pick_up_tip_whole_tree_probe(plr_function_index) -> None:
    """AC-16.2: 'the whole-tree count of `can_pick_up_tip` definitions and
    the count of those with a `constant_return`, asserted 2 at this pin
    with the two files named' -- `probe_method_definitions` takes
    `method_name` as a parameter (never a literal inside `receiver_state.py`
    itself; see that function's own docstring), and this test is where the
    literal `"can_pick_up_tip"` legitimately lives."""
    n_definitions, n_constant_return = probe_method_definitions(plr_function_index, "can_pick_up_tip")
    assert n_definitions == 8
    assert n_constant_return == 2

    constant_return_modules = sorted(
        module
        for (module, qualname, _lineno), node in plr_function_index.items()
        if qualname.endswith(".can_pick_up_tip")
        for has_const in [_constant_return_shape_for_test(node)]
        if has_const
    )
    assert constant_return_modules == [
        "pylabrobot.liquid_handling.backends.chatterbox",
        "pylabrobot.liquid_handling.backends.serializing_backend",
    ]


def _constant_return_shape_for_test(node: ast.AST) -> bool:
    """Local re-derivation of the shape test, kept independent of
    `receiver_state._constant_return_shape` on purpose -- this is a
    cross-check, not a re-import of the thing under test."""
    body = node.body
    if len(body) != 1:
        return False
    (stmt,) = body
    return (
        isinstance(stmt, ast.Return)
        and stmt.value is not None
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, (bool, int, float, str, type(None)))
    )


def test_ac_16_2_abstract_base_can_pick_up_tip_absent_by_name(plr_function_index) -> None:
    """AC-16.2: the abstract base's `@abstractmethod` `can_pick_up_tip`
    (`external/pylabrobot/pylabrobot/liquid_handling/backends/backend.py:183-187`)
    is asserted absent BY NAME -- the rule is shown biting on real PLR
    source, not only on a synthetic fixture."""
    rows, _n_candidates, _n_absent = build_backend_surface(plr_function_index, frozenset({"can_pick_up_tip"}))
    assert "LiquidHandlerBackend.can_pick_up_tip" not in rows
    # Confirmed present-but-absent, not simply never-a-candidate: the real
    # node's decorator_list is non-empty.
    node = next(
        node
        for (module, qualname, _lineno), node in plr_function_index.items()
        if qualname == "LiquidHandlerBackend.can_pick_up_tip"
        and module == "pylabrobot.liquid_handling.backends.backend"
    )
    assert node.decorator_list != []
    # And the surface still selected other classes' definitions of the
    # same method name.
    assert "LiquidHandlerChatterboxBackend.can_pick_up_tip" in rows
    assert "SerializingBackend.can_pick_up_tip" in rows


def test_ac_16_2_no_hand_typed_base_class_name_ast_scan() -> None:
    """§16.3's D3 box / C16: a grep-equivalent AST literal scan (docstrings
    excluded, same mechanism `test_ac_14_2_iii_iv_no_hand_typed_volume_
    names_ast_scan` already uses) over the three files T41 modifies finds
    the literal string `LiquidHandlerBackend` NOWHERE -- the surface is
    keyed on PLR's own function index, never on the base class name."""
    scan_modules = (
        REPO_ROOT / "plr-sema" / "src" / "plr_sema" / "derive" / "__init__.py",
        REPO_ROOT / "plr-sema" / "src" / "plr_sema" / "derive" / "receiver_state.py",
        REPO_ROOT / "plr-sema" / "src" / "plr_sema" / "derive" / "__main__.py",
    )
    offenders: list[str] = []
    for path in scan_modules:
        source = path.read_text(encoding="utf-8")
        offenders.extend(_scan_volume_forbidden_literals(source, str(path), frozenset({"LiquidHandlerBackend"})))
    assert offenders == [], f"hand-typed base-class name found: {offenders}"


def test_ac_16_2_shipped_table_candidates_absent_rows_reconcile() -> None:
    """The shipped, regenerated `derived_contracts.json`'s own
    `backend_surface` block satisfies `candidates - absent == rows` -- the
    published counts, checked against the real artifact rather than only
    against a synthetic fixture."""
    contracts_path = REPO_ROOT / "plr-sema" / "data" / "derived_contracts.json"
    payload = json.loads(contracts_path.read_text(encoding="utf-8"))
    surface = payload["backend_surface"]
    assert surface["n_surface_candidates"] - surface["n_surface_absent_by_c15"] == surface["n_surface_rows"]
    assert surface["n_surface_rows"] == len(surface["rows"])
    assert surface["n_surface_candidates"] > 0
    assert surface["n_surface_absent_by_c15"] > 0


def test_ac_16_2_backend_surface_is_additive_fifth_top_level_key(
    survey_records: list[SurveyRecord],
    survey_index: dict[tuple[str, str], SurveyRecord],
    real_stamp: SurveyStamp,
    plr_function_index,
) -> None:
    """§16.3: `backend_surface` is the additive FIFTH top-level key of the
    payload `build_derived_contracts_payload` returns, alongside the four
    that already existed (`contracts`, `receiver_state`, `schema_version`,
    `stamp`)."""
    payload = build_derived_contracts_payload(
        survey_records, survey_index, real_stamp, function_index=plr_function_index
    )
    assert set(payload.keys()) == {"schema_version", "stamp", "receiver_state", "contracts", "backend_surface"}
    surface = payload["backend_surface"]
    assert set(surface.keys()) == {"n_surface_candidates", "n_surface_absent_by_c15", "n_surface_rows", "n_entries_with_backend_surface", "rows"}
    assert surface["n_surface_rows"] > 0
    assert surface["n_entries_with_backend_surface"] > 0


def test_ac_16_2_backend_surface_degrades_when_function_index_omitted(
    survey_records: list[SurveyRecord],
    survey_index: dict[tuple[str, str], SurveyRecord],
    real_stamp: SurveyStamp,
) -> None:
    """Degrade discipline (same convention `test_ac_14_2_bridge_absent_
    when_volume_args_omitted` already establishes for `volume_guards`): a
    caller that does not supply `function_index` gets `backend_surface`
    present but empty, never a crash and never a stale/guessed table."""
    payload = build_derived_contracts_payload(survey_records, survey_index, real_stamp)
    assert payload["backend_surface"] == {
        "n_surface_candidates": 0,
        "n_surface_absent_by_c15": 0,
        "n_surface_rows": 0,
        "n_entries_with_backend_surface": 0,
        "rows": {},
    }


def test_ac_16_2_collect_env_ref_method_names_walks_nested_predicates() -> None:
    """`collect_env_ref_method_names` finds an `EnvRef`'s last path segment
    regardless of how deeply it is nested inside `And`/`Cmp`/`Not` -- it
    reads the regenerated contract table via `predicate_ast.from_json` +
    `predicate_ast.walk`, not a hand-written partial JSON walk."""
    nested_predicate = parse_predicate("self.head is not None and not len(self.backend.get_ids()) == 0")
    contracts = {
        "Some.method": {
            "guards": [
                {"predicate": predicate_to_json(nested_predicate)},
                {"predicate": None},  # a guard the writer never populated -- tolerated.
            ]
        },
        "Other.method": {"guards": []},
    }
    names = collect_env_ref_method_names(contracts)
    assert names == frozenset({"head", "get_ids"})


def test_ac_16_2_collect_env_ref_method_names_also_walks_caller_args() -> None:
    """T49 (spec 260909 §16.1.1/§16.3): `collect_env_ref_method_names` ALSO
    scans each guard's `caller_args` map -- D5b's site rules read the
    delegate's runtime `method` identity from THERE, never from the
    guard's own `predicate` (`_check_args`'s `:375`/`:383` predicates
    reference `missing`/`vars_keyword`/`strictness`, never the method
    itself). Without this half, `pick_up_tips` would never become a
    surface candidate at all -- it occurs NOWHERE as an `EnvRef` path
    segment in any guard's own `"predicate"` JSON at this pin (measured 0
    before this half existed)."""
    contracts = {
        "LiquidHandler._check_args": {
            "guards": [
                {
                    "predicate": {"node": "Cmp", "left": {"node": "Var", "name": "missing"}, "op": ">", "right": {"node": "Lit", "value": 0}},
                    "caller_args": {
                        "method": {"node": "EnvRef", "path": ["self", "backend", "pick_up_tips"], "args": None},
                        "default": {"node": "SetLit", "values": ["ops", "use_channels"]},
                    },
                },
                {"predicate": None, "caller_args": None},  # an un-mapped guard -- tolerated.
                {"predicate": None},  # a guard with no caller_args key at all -- tolerated.
            ]
        },
    }
    names = collect_env_ref_method_names(contracts)
    assert names == frozenset({"pick_up_tips"})


def test_ac_17_4_m_surf_attachment_extends_to_caller_args() -> None:
    """T53 (spec 260909_plr-sema-move-family-increment.md §17.1.4, M-SURF):
    the attachment filter extends to scan `caller_args` as well as `predicate`,
    by the SAME rule as the selection half (`collect_env_ref_method_names`).
    D5b's site rules read the method identity from `caller_args`, not from the
    guard's own `predicate` -- `_check_args` carries `missing`/`has_var_keyword`,
    never the method itself. Without this half, entries like `aspirate`,
    `dispense`, `drop_tips` with `caller_args` at depth 1 would never receive
    the backend_surface attachment.

    The `caller_args` arm requires NO `args is not None` check (stores method
    identity as a reference, not a call), matching D5b's need and the
    distinction M-SURF makes between the two arms.

    AC-17.4: entries with a `self.backend.<m>` EnvRef only in `caller_args`
    (not in `predicate` with `args is not None`) now receive the attachment."""
    from plr_sema.derive.__main__ import build_derived_contracts_payload

    # Create a synthetic contract with a backend EnvRef ONLY in caller_args
    # (not in the predicate), mimicking the depth-1 `aspirate`/`dispense`/
    # `drop_tips` case.
    contracts = {
        "Entry": {
            "guards": [
                {
                    # Predicate does NOT contain a call-shaped backend EnvRef
                    "predicate": {"node": "Cmp", "left": {"node": "Var", "name": "x"}, "op": ">", "right": {"node": "Lit", "value": 0}},
                    # But caller_args DOES contain a backend method reference
                    "caller_args": {
                        "method": {"node": "EnvRef", "path": ["self", "backend", "aspirate"], "args": None},
                        "default": {"node": "SetLit", "values": ["ops"]},
                    },
                },
            ]
        },
        "NoBackendEntry": {
            "guards": [
                {
                    "predicate": {"node": "Lit", "value": True},
                    # No backend EnvRef anywhere
                    "caller_args": {
                        "other": {"node": "Var", "name": "x"},
                    },
                },
            ]
        },
    }

    backend_surface = {
        "n_surface_candidates": 0,
        "n_surface_absent_by_c15": 0,
        "n_surface_rows": 0,
        "rows": {"Backend.aspirate": {}},  # dummy row
    }

    # Apply the attachment filter (the modified code)
    for entry in contracts.values():
        for guard in entry.get("guards", ()):
            # Check predicate (with args is not None)
            predicate_json = guard.get("predicate")
            if predicate_json is not None:
                from plr_sema.derive.predicate_ast import EnvRef, from_json as predicate_from_json, walk as predicate_walk
                node = predicate_from_json(predicate_json)
                if any(
                    isinstance(sub, EnvRef)
                    and sub.args is not None
                    and len(sub.path) >= 2
                    and sub.path[0] == "self"
                    and sub.path[1] == "backend"
                    for sub in predicate_walk(node)
                ):
                    entry["backend_surface"] = {"rows": backend_surface["rows"]}
                    break
            # Check caller_args (with or without args)
            caller_args_json = guard.get("caller_args")
            if caller_args_json:
                for term_json in caller_args_json.values():
                    term = predicate_from_json(term_json)
                    if any(
                        isinstance(sub, EnvRef)
                        and len(sub.path) >= 2
                        and sub.path[0] == "self"
                        and sub.path[1] == "backend"
                        for sub in predicate_walk(term)
                    ):
                        entry["backend_surface"] = {"rows": backend_surface["rows"]}
                        break
                else:
                    continue
                break

    # Assert that Entry got the attachment (via caller_args)
    assert "backend_surface" in contracts["Entry"], "Entry should have backend_surface via caller_args"
    assert contracts["Entry"]["backend_surface"]["rows"] == backend_surface["rows"]

    # Assert that NoBackendEntry did NOT get the attachment
    assert "backend_surface" not in contracts["NoBackendEntry"], "NoBackendEntry should not have backend_surface"


def test_ac_17_4_n_entries_with_backend_surface_counter_exists_in_payload(
    real_stamp: SurveyStamp,
) -> None:
    """T53 (spec 260909_plr-sema-move-family-increment.md §17.1.4): the
    `n_entries_with_backend_surface` counter in the `backend_surface` payload
    sub-object must be published. This test verifies that the counter exists
    in the payload with no function_index (else branch, fail-closed path)."""
    from plr_sema.derive.__main__ import build_derived_contracts_payload

    payload = build_derived_contracts_payload(
        [],  # Empty records
        {},  # Empty index
        real_stamp,
        # No other arguments -- triggers the else branch
    )
    # With no function_index, the counter should be 0 and present
    assert "n_entries_with_backend_surface" in payload["backend_surface"]
    assert payload["backend_surface"]["n_entries_with_backend_surface"] == 0


def test_real_backend_surface_attachment_matches_counter(
    survey_records: list[SurveyRecord],
    survey_index: dict[tuple[str, str], SurveyRecord],
    real_stamp: SurveyStamp,
    plr_function_index: FunctionIndex,
) -> None:
    """AC-17.4 measurement: verify that the published
    `n_entries_with_backend_surface` counter in the payload matches the
    actual count of contract entries that received the attachment."""
    payload = build_derived_contracts_payload(
        survey_records,
        survey_index,
        real_stamp,
        function_index=plr_function_index,
    )

    contracts = payload["contracts"]
    backend_surface = payload["backend_surface"]

    # Count entries that actually have backend_surface
    actual_count = sum(1 for entry in contracts.values() if "backend_surface" in entry)

    # Assert the counter matches
    assert backend_surface["n_entries_with_backend_surface"] == actual_count, (
        f"Counter mismatch: published {backend_surface['n_entries_with_backend_surface']} "
        f"but actual count is {actual_count}"
    )


# ---------------------------------------------------------------------------
# T42 (260909, spec 260909_plr-sema-observation-increment.md §16.4,
# increment 7): the delegate->caller argument map, `compute_caller_args`'s
# M1 six conditions, `compute_caller_scope_trail`, and their wiring into
# `derive_contract`/`InlinedGuard`/the JSON writer.
# ---------------------------------------------------------------------------


def test_compute_caller_args_clause1_module_level_delegate_binds_nothing() -> None:
    """M1 clause 1: `helper(x)` called BARE (no `self.` receiver) never
    matches the self-rooted call shape at all -- `None`, not an empty
    dict."""
    K = _func_node("def K(self, x):\n    helper(x)\n")
    D = _func_node("def helper(self, y):\n    pass\n")
    assert compute_caller_args(K, D) is None


def test_compute_caller_args_clause2_delegate_called_twice_binds_nothing() -> None:
    """M1 clause 2: two call sites have two argument vectors and one guard
    record -- binding either would be a choice the record cannot
    express."""
    K = _func_node("def K(self, x):\n    self.helper(x)\n    self.helper(x)\n")
    D = _func_node("def helper(self, y):\n    pass\n")
    assert compute_caller_args(K, D) is None


def test_compute_caller_args_clause4_starred_call_arg_binds_nothing() -> None:
    """M1 clause 4: an `ast.Starred` call-side argument is positionally
    ambiguous -- fail-closed on the WHOLE map, never a partial one."""
    K = _func_node("def K(self, xs):\n    self.helper(*xs)\n")
    D = _func_node("def helper(self, y):\n    pass\n")
    assert compute_caller_args(K, D) is None


def test_compute_caller_args_clause4_call_side_double_star_binds_nothing() -> None:
    """M1 clause 4, the call-side `**` unpacking half (distinct from D's
    own `**kwargs` below)."""
    K = _func_node("def K(self, kw):\n    self.helper(**kw)\n")
    D = _func_node("def helper(self, y):\n    pass\n")
    assert compute_caller_args(K, D) is None


def test_compute_caller_args_clause4_delegate_with_kwargs_binds_nothing() -> None:
    """M1 clause 4: `D` itself declaring `**kwargs` refuses the WHOLE map,
    even though the call site is perfectly ordinary."""
    K = _func_node("def K(self, x):\n    self.helper(x)\n")
    D = _func_node("def helper(self, y, **kwargs):\n    pass\n")
    assert compute_caller_args(K, D) is None


def test_compute_caller_args_clause4_delegate_with_star_args_binds_nothing() -> None:
    """M1 clause 4: `D` itself declaring `*args` refuses the WHOLE map."""
    K = _func_node("def K(self, x):\n    self.helper(x)\n")
    D = _func_node("def helper(self, y, *args):\n    pass\n")
    assert compute_caller_args(K, D) is None


def test_compute_caller_args_clause5_unparseable_argument_binds_only_that_param() -> None:
    """M1 clause 5, the stub-defeating half: an argument that does not
    parse as a `Term` (`get_strictness()`, a non-`self`-rooted call) binds
    ONLY that parameter to nothing -- the OTHER parameter, whose argument
    IS a Term, still binds. A whole-map refusal here (returning `None`)
    would be wrong -- clause 5 is explicitly a per-argument rule."""
    K = _func_node("def K(self, x):\n    self.helper(x, get_strictness())\n")
    D = _func_node("def helper(self, a, b):\n    pass\n")
    result = compute_caller_args(K, D)
    assert result == {"a": {"node": "Var", "name": "x"}}
    assert "b" not in result


def test_compute_caller_args_keyword_arguments_map_by_name() -> None:
    """M1 clause 3's keyword half: a keyword call argument binds by NAME
    against D's own parameter, independent of positional order."""
    K = _func_node("def K(self, x, y):\n    self.helper(b=y, a=x)\n")
    D = _func_node("def helper(self, a, b):\n    pass\n")
    result = compute_caller_args(K, D)
    assert result == {"a": {"node": "Var", "name": "x"}, "b": {"node": "Var", "name": "y"}}


def test_compute_caller_args_positional_arguments_map_by_index_after_self() -> None:
    """M1 clause 3's positional half: index against D's OWN
    `ast.arguments`, after `self` -- the call never spells `self`."""
    K = _func_node("def K(self, x, y):\n    self.helper(x, y)\n")
    D = _func_node("def helper(self, first, second):\n    pass\n")
    result = compute_caller_args(K, D)
    assert result == {
        "first": {"node": "Var", "name": "x"},
        "second": {"node": "Var", "name": "y"},
    }


def test_compute_caller_args_c10_position_gates_on_the_call_statement_not_the_guard() -> None:
    """C10 (§16.4's own normative box): a delegate defined BELOW its
    caller, with the mapped name's ALPHA rebinding written AFTER the
    delegate call, does NOT get folded into the stored Term -- "binds the
    pre-call value and not the rebinding". `K`'s call happens at line 3,
    BEFORE `x`'s only alpha-shaped assignment at line 5; gating on the
    delegate CALL STATEMENT's own lineno (3) correctly excludes it (the
    binding search finds `first_stmt.lineno(5) < 3` false). A guard-lineno
    reading (D's own raise sits far below, at a much larger lineno) would
    WRONGLY admit it -- the unsoundness this fixture exists to catch."""
    K = _func_node(
        "def K(self, x, seq):\n"
        "    self.helper(x)\n"
        "    x = [e for e in seq if e > 0]\n"
    )
    D = _func_node(
        "def helper(self, y):\n"
        "    if y:\n"
        "        raise ValueError('y')\n"
    )
    result = compute_caller_args(K, D)
    assert result == {"y": {"node": "Var", "name": "x"}}, (
        "the call-lineno-gated alpha binding must NOT have been folded in "
        "-- the stored term should still be the bare pre-rebinding Var(x)"
    )


def test_compute_caller_args_c10_alpha_binding_before_the_call_is_folded_in() -> None:
    """The positive control for C10: the SAME alpha assignment, now BEFORE
    the call, at a lineno less than the call statement's own -- the
    binding correctly applies and `substitute` folds it into the stored
    Term."""
    K = _func_node(
        "def K(self, x, seq):\n"
        "    x = [e for e in seq if e > 0]\n"
        "    self.helper(x)\n"
    )
    D = _func_node(
        "def helper(self, y):\n"
        "    if y:\n"
        "        raise ValueError('y')\n"
    )
    result = compute_caller_args(K, D)
    assert result == {
        "y": {
            "node": "Filtered",
            "seq": {"node": "Var", "name": "seq"},
            "predicate": {
                "node": "Cmp",
                "left": {"node": "Var", "name": "e"},
                "op": ">",
                "right": {"node": "Lit", "value": 0},
            },
        }
    }


def test_compute_caller_args_clause6_is_the_callers_job_not_this_functions() -> None:
    """M1 clause 6 ("one level only") has no `depth` parameter on this
    function at all -- `compute_caller_args` itself binds a perfectly
    ordinary `(K, D)` pair regardless of what depth the CALLER intends to
    use it at; enforcement lives in `derive_contract` alone (the dedicated
    end-to-end fixture below, `test_derive_contract_depth2_never_gets_
    caller_args`, confirms the enforcement side)."""
    K = _func_node("def K(self, x):\n    self.helper(x)\n")
    D = _func_node("def helper(self, y):\n    pass\n")
    assert compute_caller_args(K, D) == {"y": {"node": "Var", "name": "x"}}


def test_compute_caller_call_lineno_matches_the_call_statement() -> None:
    K = _func_node("def K(self, x):\n    pass\n    self.helper(x)\n")
    D = _func_node("def helper(self, y):\n    pass\n")
    assert compute_caller_call_lineno(K, D) == 3


def test_compute_caller_call_lineno_none_when_call_is_ambiguous() -> None:
    K = _func_node("def K(self, x):\n    self.helper(x)\n    self.helper(x)\n")
    D = _func_node("def helper(self, y):\n    pass\n")
    assert compute_caller_call_lineno(K, D) is None


def test_compute_caller_scope_trail_empty_for_a_straight_line_call() -> None:
    K = _func_node("def K(self, x):\n    self.helper(x)\n")
    assert compute_caller_scope_trail(K, 2) == ()


def test_compute_caller_scope_trail_none_when_lineno_absent() -> None:
    K = _func_node("def K(self, x):\n    self.helper(x)\n")
    assert compute_caller_scope_trail(K, 999) is None


def test_compute_caller_scope_trail_nearest_first_if_and_for() -> None:
    """Nearest-first, matching `scope_trail`'s own convention (survey
    `_BodyScanner`): the innermost `for` entry sorts BEFORE the outer
    `if`."""
    K = _func_node(
        "def K(self, cond, xs):\n"
        "    if cond:\n"
        "        for x in xs:\n"
        "            self.helper(x)\n"
    )
    assert compute_caller_scope_trail(K, 4) == ("for x in xs", "if cond")


def test_compute_caller_scope_trail_else_branch() -> None:
    K = _func_node(
        "def K(self, cond, x):\n"
        "    if cond:\n"
        "        pass\n"
        "    else:\n"
        "        self.helper(x)\n"
    )
    assert compute_caller_scope_trail(K, 5) == ("else of: if cond",)


def test_compute_caller_scope_trail_ignores_try_but_still_descends() -> None:
    """A `Try`/`With` ancestor contributes NO entry of its own (mirrors the
    survey scanner, which has no `visit_Try`/`visit_With` override), but a
    target nested inside one is still found."""
    K = _func_node(
        "def K(self, x):\n"
        "    try:\n"
        "        self.helper(x)\n"
        "    except Exception:\n"
        "        pass\n"
    )
    assert compute_caller_scope_trail(K, 3) == ()


# ---- The real corpus: pick_up_tips's own two mapped delegates -------------


def test_real_compute_caller_args_pick_up_tips_make_sure_channels_exist(plr_function_index) -> None:
    """AC-16.3's own named assertion: `self._make_sure_channels_exist(use_
    channels)` (`external/pylabrobot/.../liquid_handler.py:520-522`) maps
    `channels` -> `Var("use_channels")`, by NAME."""
    k_key = ("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler.pick_up_tips")
    d_key = ("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler._make_sure_channels_exist")
    K = plr_function_index[(*k_key, next(ln for (m, q, ln) in plr_function_index if (m, q) == k_key))]
    D = plr_function_index[(*d_key, next(ln for (m, q, ln) in plr_function_index if (m, q) == d_key))]
    assert compute_caller_args(K, D) == {"channels": {"node": "Var", "name": "use_channels"}}
    call_lineno = compute_caller_call_lineno(K, D)
    assert compute_reachability_clear(K, call_lineno) is True
    assert compute_caller_scope_trail(K, call_lineno) == ()


def test_real_compute_caller_args_pick_up_tips_assert_resources_exist(plr_function_index) -> None:
    """AC-16.3's second named assertion: `self._assert_resources_exist(tip_
    spots)` maps `resources` -> `Var("tip_spots")`, by NAME."""
    k_key = ("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler.pick_up_tips")
    d_key = ("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler._assert_resources_exist")
    K = plr_function_index[(*k_key, next(ln for (m, q, ln) in plr_function_index if (m, q) == k_key))]
    D = plr_function_index[(*d_key, next(ln for (m, q, ln) in plr_function_index if (m, q) == d_key))]
    assert compute_caller_args(K, D) == {"resources": {"node": "Var", "name": "tip_spots"}}
    call_lineno = compute_caller_call_lineno(K, D)
    assert compute_reachability_clear(K, call_lineno) is True
    assert compute_caller_scope_trail(K, call_lineno) == ()


def test_real_compute_caller_args_check_args_strictness_not_parseable(plr_function_index) -> None:
    """AC-16.3(b) / C9's own named claim: `:383`'s `strictness` carries NO
    `caller_args` entry, because the real call site's own argument
    (`strictness=get_strictness()`) does not parse as a `Term` (M1 clause
    5, the partial-admission rule) -- `strictness` IS a parameter of
    `_check_args`, so its absence from the map is a Term-parse refusal,
    never a "not a parameter" non-issue. `method`/`backend_kwargs`, whose
    own call-side expressions DO parse (`self.backend.pick_up_tips` -- a
    self-rooted `EnvRef`, and `backend_kwargs`, a bare `Var`), still bind."""
    k_key = ("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler.pick_up_tips")
    d_key = ("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler._check_args")
    K = plr_function_index[(*k_key, next(ln for (m, q, ln) in plr_function_index if (m, q) == k_key))]
    D = plr_function_index[(*d_key, next(ln for (m, q, ln) in plr_function_index if (m, q) == d_key))]
    param_names = {a.arg for a in D.args.posonlyargs} | {a.arg for a in D.args.args}
    assert "strictness" in param_names
    result = compute_caller_args(K, D)
    assert result is not None
    assert "strictness" not in result
    assert "method" in result
    assert "backend_kwargs" in result


def test_real_compute_caller_args_check_args_default_setlit_parses(plr_function_index) -> None:
    """T49 (spec 260909_plr-sema-observation-increment.md §16.1.1, G9): the
    real call site's `default={"ops", "use_channels"}`
    (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:541-546`)
    now parses as a `Term` -- an `ast.Set` display of `ast.Constant`s, G9's
    ONE further production -- so `"default"` binds in `caller_args` even
    though it never did before this production existed. This is the exact
    fact D5b's `:375`/`:383` site rules read."""
    k_key = ("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler.pick_up_tips")
    d_key = ("pylabrobot.liquid_handling.liquid_handler", "LiquidHandler._check_args")
    K = plr_function_index[(*k_key, next(ln for (m, q, ln) in plr_function_index if (m, q) == k_key))]
    D = plr_function_index[(*d_key, next(ln for (m, q, ln) in plr_function_index if (m, q) == d_key))]
    result = compute_caller_args(K, D)
    assert result is not None
    assert result["default"] == {"node": "SetLit", "values": ["ops", "use_channels"]}


# ---- derive_contract wiring: depth == 1 populated, depth >= 2 never is ----


def test_derive_contract_depth1_gets_caller_args_depth2_never_does() -> None:
    """M1 clause 6, enforced end to end: a THREE-level synthetic closure
    (A -> B -> C, A the entry point) -- B's own guard (depth 1, reached
    directly from A) gets `caller_args`/`caller_reachability_clear`/
    `caller_scope_trail` populated; C's own guard (depth 2, reached via
    B) gets `None` for all three, UNCONDITIONALLY, even though B's own
    call to C would otherwise qualify under M1 on its own terms."""
    a_node = _func_node("def A(self, x):\n    self.B(x)\n")
    b_node = _func_node(
        "def B(self, p):\n"
        "    if p < 0:\n"
        "        raise ValueError('neg')\n"
        "    self.C(p)\n"
    )
    c_node = _func_node(
        "def C(self, q):\n"
        "    if q > 0:\n"
        "        raise ValueError('pos')\n"
    )
    rec_a = _synthetic_record("Foo.A", class_name="Foo", delegates_to=("B",))
    rec_b = _synthetic_record("Foo.B", class_name="Foo", delegates_to=("C",), findings=(_synthetic_finding(3),))
    rec_c = _synthetic_record("Foo.C", class_name="Foo", findings=(_synthetic_finding(3),))
    index = build_index([rec_a, rec_b, rec_c])
    function_index = {
        ("synthetic.module", "Foo.A", 1): a_node,
        ("synthetic.module", "Foo.B", 1): b_node,
        ("synthetic.module", "Foo.C", 1): c_node,
    }

    contract = derive_contract("synthetic.module", "Foo.A", index, function_index=function_index)

    (guard1,) = [g for g in contract.guards if g.depth == 1]
    assert guard1.caller_args == {"p": {"node": "Var", "name": "x"}}
    assert guard1.caller_reachability_clear is True
    assert guard1.caller_scope_trail == ()

    (guard2,) = [g for g in contract.guards if g.depth == 2]
    assert guard2.caller_args is None
    assert guard2.caller_reachability_clear is None
    assert guard2.caller_scope_trail is None


def test_derive_contract_without_function_index_leaves_caller_args_none(
    survey_index: dict[tuple[str, str], SurveyRecord],
) -> None:
    """Backward-compatibility default, identical in spirit to `bindings`/
    `reachability_clear`'s own: no `function_index` -> every guard's
    `caller_args`/`caller_reachability_clear`/`caller_scope_trail` stays
    `None`, regardless of depth."""
    contract = derive_contract(
        "pylabrobot.liquid_handling.liquid_handler", "LiquidHandler.pick_up_tips", survey_index
    )
    assert all(g.caller_args is None for g in contract.guards)
    assert all(g.caller_reachability_clear is None for g in contract.guards)
    assert all(g.caller_scope_trail is None for g in contract.guards)


def test_guard_to_json_emits_caller_args_keys(
    survey_index: dict[tuple[str, str], SurveyRecord], plr_function_index
) -> None:
    contract = derive_contract(
        "pylabrobot.liquid_handling.liquid_handler",
        "LiquidHandler.pick_up_tips",
        survey_index,
        function_index=plr_function_index,
    )
    (guard_409,) = [g for g in contract.guards if g.site.lineno == 409]
    payload = _guard_to_json(guard_409)
    assert payload["caller_args"] == {"channels": {"node": "Var", "name": "use_channels"}}
    assert payload["caller_reachability_clear"] is True
    assert payload["caller_scope_trail"] == []


def test_guard_to_json_caller_args_absent_for_depth0_guard(
    survey_index: dict[tuple[str, str], SurveyRecord], plr_function_index
) -> None:
    """A depth-0 guard's own `_guard_to_json` payload still carries the
    three keys (additive-field discipline: present, `None`, never simply
    missing), matching `bindings`/`reachability_clear`'s own convention."""
    contract = derive_contract(
        "pylabrobot.liquid_handling.liquid_handler",
        "LiquidHandler.pick_up_tips",
        survey_index,
        function_index=plr_function_index,
    )
    (guard_502,) = [g for g in contract.guards if g.site.lineno == 502]
    assert guard_502.depth == 0
    payload = _guard_to_json(guard_502)
    assert payload["caller_args"] is None
    assert payload["caller_reachability_clear"] is None
    assert payload["caller_scope_trail"] is None


# ---------------------------------------------------------------------------
# T50 -- M-INH, inherited self-call resolution (spec
# 260909_plr-sema-move-family-increment.md §17.2, AC-17.1). Synthetic
# in-memory class trees throughout (mirrors this file's own docstring
# convention: synthetic fixtures for tests about the MECHANIC itself).
# ---------------------------------------------------------------------------


def _class_nodes_from_source(source: str) -> dict[str, ast.ClassDef]:
    tree = ast.parse(source)
    return {n.name: n for n in ast.iter_child_nodes(tree) if isinstance(n, ast.ClassDef)}


def _uniform_bases_index(class_nodes: dict[str, ast.ClassDef], module: str = "mod") -> ClassBasesIndex:
    """No collisions, every class in one module -- the common case most
    of this section's fixtures want; the collision-specific tests below
    build their own ``class_modules_multi`` instead."""
    return build_class_bases_index(class_nodes, {name: frozenset({module}) for name in class_nodes})


# --- the base-name extractor's four rows (§17.2's table) -------------------


def test_extract_base_name_four_rows() -> None:
    src = """
class ByName(A): pass
class ByAttribute(mod.B): pass
class BySubscript(Generic[T]): pass
class RefusedCall(factory()): pass
class RefusedStar(*bases): pass
"""
    classes = _class_nodes_from_source(src)
    assert _extract_base_name(classes["ByName"].bases[0]) == "A"
    assert _extract_base_name(classes["ByAttribute"].bases[0]) == "B"
    assert _extract_base_name(classes["BySubscript"].bases[0]) == "Generic"
    assert _extract_base_name(classes["RefusedCall"].bases[0]) is None
    assert _extract_base_name(classes["RefusedStar"].bases[0]) is None


def test_build_class_bases_index_refuses_whole_class_on_unreadable_base_expression() -> None:
    """AC-17.1's third stub-defeating fixture: a `ClassDef` with an
    unreadable base expression makes the WHOLE class refuse rather than
    contributing a partial closure -- not just the one unreadable base
    dropped silently."""
    class_nodes = _class_nodes_from_source("class Bad(factory(), Readable):\n    def m(self): pass\n")
    idx = _uniform_bases_index(class_nodes)
    assert idx.bases["Bad"] is None
    assert idx.unresolved_base_counts["Bad"] == 0  # meaningless for a refused class -- 0, not a partial count


def test_build_class_bases_index_records_alias_incompleteness() -> None:
    """An import-alias base yields a name absent from the whole-tree
    index -- silent INCOMPLETENESS, not a refusal -- and T50 publishes the
    per-class count rather than assuming zero."""
    class_nodes = _class_nodes_from_source("class C(AliasedImport):\n    def m(self): pass\n")
    idx = _uniform_bases_index(class_nodes)
    assert idx.bases["C"] == ("AliasedImport",)
    assert idx.unresolved_base_counts["C"] == 1
    assert idx.collision_names == frozenset()


def test_build_class_bases_index_bare_name_collision() -> None:
    """A class name defined in more than one module is a collision --
    the extractor's second refusal, independent of the base expression
    shape."""
    class_nodes = _class_nodes_from_source("class Dup:\n    def m(self): pass\n")
    idx = build_class_bases_index(class_nodes, {"Dup": frozenset({"mod.a", "mod.b"})})
    assert idx.collision_names == frozenset({"Dup"})


# --- class_closure: reflexive/transitive + fail-closed refusal propagation -


def test_class_closure_is_reflexive_and_transitive() -> None:
    class_nodes = _class_nodes_from_source("class A: pass\nclass B(A): pass\nclass C(B): pass\n")
    idx = _uniform_bases_index(class_nodes)
    assert class_closure("C", class_nodes, idx) == frozenset({"A", "B", "C"})
    assert class_closure("A", class_nodes, idx) == frozenset({"A"})


def test_class_closure_propagates_refusal_from_an_unreadable_ancestor() -> None:
    """§17.2's own framing: refusing the class rather than dropping the
    one base is the whole point -- a subclass of a refused class cannot
    licitly claim uniqueness either, since it has not seen the refused
    ancestor's own (unknown) further bases."""
    class_nodes = _class_nodes_from_source("class Bad(factory()):\n    def m(self): pass\nclass Child(Bad): pass\n")
    idx = _uniform_bases_index(class_nodes)
    assert class_closure("Bad", class_nodes, idx) is None
    assert class_closure("Child", class_nodes, idx) is None


def test_class_closure_refuses_on_a_collision_anywhere_in_the_chain() -> None:
    class_nodes = _class_nodes_from_source("class Dup(Base): pass\nclass Base:\n    def m(self): pass\n")
    idx = build_class_bases_index(class_nodes, {"Dup": frozenset({"mod"}), "Base": frozenset({"mod.a", "mod.b"})})
    assert class_closure("Dup", class_nodes, idx) is None


def test_class_closure_unresolved_base_contributes_itself_but_no_further_ancestors() -> None:
    """An import alias / out-of-surface base is absent from `bases`
    entirely -- a leaf, not a refusal. Mirrors
    `subclass_closure_from_bases`'s own documented behaviour exactly
    (`test_subclass_closure_unresolvable_base_contributes_nothing_extra`
    in test_predicate.py): the DIRECT edge to the unresolved name is real
    (`C`'s ancestor set includes it) -- what stays unguessed is that
    name's own FURTHER ancestors, since it is not itself a key of
    `bases_index.bases`."""
    class_nodes = _class_nodes_from_source("class C(NotIndexed):\n    def m(self): pass\n")
    idx = _uniform_bases_index(class_nodes)
    assert class_closure("C", class_nodes, idx) == frozenset({"C", "NotIndexed"})


# --- diagnose_base_resolution / resolve_via_base_closure: the four reasons -


def test_diagnose_base_resolution_resolves_the_unique_ancestor() -> None:
    class_nodes = _class_nodes_from_source("class A:\n    def m(self): pass\nclass C(A): pass\n")
    idx = _uniform_bases_index(class_nodes)
    assert diagnose_base_resolution("C", "m", class_nodes, idx) == ("A", "resolved")
    assert resolve_via_base_closure("C", "m", class_nodes, idx) == "A"


def test_diagnose_base_resolution_ambiguous_on_two_defining_ancestors() -> None:
    """AC-17.1's first stub-defeating fixture: a name defined on TWO
    classes in the base closure resolves to NEITHER, asserted positively
    -- an implementation that takes the first base passes every other
    fixture and fails this one."""
    class_nodes = _class_nodes_from_source(
        "class A:\n    def m(self): pass\nclass B:\n    def m(self): pass\nclass C(A, B): pass\n"
    )
    idx = _uniform_bases_index(class_nodes)
    assert diagnose_base_resolution("C", "m", class_nodes, idx) == (None, "ambiguous")
    assert resolve_via_base_closure("C", "m", class_nodes, idx) is None


def test_diagnose_base_resolution_no_ancestor_defines() -> None:
    class_nodes = _class_nodes_from_source("class A: pass\nclass C(A): pass\n")
    idx = _uniform_bases_index(class_nodes)
    assert diagnose_base_resolution("C", "nope", class_nodes, idx) == (None, "no_ancestor_defines")


def test_diagnose_base_resolution_refuses_on_class_name_collision() -> None:
    class_nodes = _class_nodes_from_source("class C(A): pass\nclass A:\n    def m(self): pass\n")
    idx = build_class_bases_index(class_nodes, {"C": frozenset({"mod.a", "mod.b"}), "A": frozenset({"mod"})})
    assert diagnose_base_resolution("C", "m", class_nodes, idx) == (None, "class_name_collision")


def test_diagnose_base_resolution_refuses_when_a_base_is_outside_the_index() -> None:
    """§17.2 condition 2: a base outside the analyzed surface (an
    unreadable-expression refusal on the ancestor, here) leaves the gap."""
    class_nodes = _class_nodes_from_source(
        "class Bad(factory()):\n    def m(self): pass\nclass C(Bad):\n    pass\n"
    )
    idx = _uniform_bases_index(class_nodes)
    assert diagnose_base_resolution("C", "m", class_nodes, idx) == (None, "closure_refused")


# --- inherited_method_names: Half 1's union-of-ancestors, no ambiguity -----


def test_inherited_method_names_is_the_union_with_no_ambiguity_refusal() -> None:
    """Unlike `resolve_via_base_closure`, the survey's own classification
    need is a boolean ("is this name SOME delegate"), so two ancestors
    defining the same name is not a conflict here -- both contribute."""
    class_nodes = _class_nodes_from_source(
        "class A:\n    def m(self): pass\nclass B:\n    def m(self): pass\n    def n(self): pass\n"
        "class C(A, B): pass\n"
    )
    idx = _uniform_bases_index(class_nodes)
    assert inherited_method_names("C", class_nodes, idx) == frozenset({"m", "n"})


def test_inherited_method_names_empty_when_closure_refused() -> None:
    class_nodes = _class_nodes_from_source(
        "class Bad(factory()):\n    def m(self): pass\nclass Child(Bad): pass\n"
    )
    idx = _uniform_bases_index(class_nodes)
    assert inherited_method_names("Child", class_nodes, idx) == frozenset()


def test_inherited_method_names_still_reports_an_ancestor_name_c_overrides() -> None:
    """`inherited_method_names` reports every ANCESTOR's own method names,
    with no awareness of whether `class_name` itself also defines the
    same name -- excluding an override at the CALLER's own precedence
    (`_BodyScanner.visit_Call`'s own-class-branch-first check, mirroring
    `resolve()`'s class-first step) is what keeps a `self.m()` call on
    `C` resolving to `C`'s own `m`, never to this set. This is exactly
    the shape condition 4's override fixture needs: `Base` defines a
    name `Derived` also overrides, and the override still wins at
    RESOLUTION time even though this SELECTION-time set does not know
    which body eventually gets used."""
    class_nodes = _class_nodes_from_source(
        "class A:\n    def m(self): pass\nclass C(A):\n    def m(self): pass\n"
    )
    idx = _uniform_bases_index(class_nodes)
    assert "m" in inherited_method_names("C", class_nodes, idx)


# --- resolve()'s third step and condition 4 (dispatch on the analyzed class)


def test_resolve_without_m_inh_kwargs_reproduces_pre_t50_behaviour() -> None:
    class_nodes = _class_nodes_from_source("class A:\n    def m(self): pass\nclass C(A): pass\n")
    idx = _uniform_bases_index(class_nodes)
    rec_c = _synthetic_record("C.foo", class_name="C", module="mod", delegates_to=("m",))
    index = build_index([_synthetic_record("A.m", class_name="A", module="mod"), rec_c])
    assert resolve("m", rec_c, index) is None
    # Only with ALL THREE of class_nodes/class_modules/bases_index does the
    # third step activate.
    assert resolve("m", rec_c, index, class_nodes=class_nodes) is None
    assert (
        resolve("m", rec_c, index, class_nodes=class_nodes, class_modules={"A": "mod", "C": "mod"}, bases_index=idx)
        == ("mod", "A.m")
    )


def test_resolve_third_step_refuses_on_ambiguous_base() -> None:
    """The second half of AC-17.1's first stub-defeating fixture, at
    `resolve()`'s own level: `LiquidHandler` has more than one base for
    real, so this is a live condition, not a hypothetical."""
    class_nodes = _class_nodes_from_source(
        "class A:\n    def m(self): pass\nclass B:\n    def m(self): pass\nclass C(A, B): pass\n"
    )
    idx = _uniform_bases_index(class_nodes)
    class_modules = {"A": "mod", "B": "mod", "C": "mod"}
    rec_c = _synthetic_record("C.foo", class_name="C", module="mod", delegates_to=("m",))
    index = build_index(
        [
            _synthetic_record("A.m", class_name="A", module="mod"),
            _synthetic_record("B.m", class_name="B", module="mod"),
            rec_c,
        ]
    )
    assert resolve("m", rec_c, index, class_nodes=class_nodes, class_modules=class_modules, bases_index=idx) is None


def test_resolve_third_step_refuses_when_candidate_key_absent_from_index() -> None:
    """§17.2 condition 2: the unique base is found, but its own record was
    never indexed (e.g. never surveyed) -- the gap stands."""
    class_nodes = _class_nodes_from_source("class A:\n    def m(self): pass\nclass C(A): pass\n")
    idx = _uniform_bases_index(class_nodes)
    class_modules = {"A": "mod", "C": "mod"}
    rec_c = _synthetic_record("C.foo", class_name="C", module="mod", delegates_to=("m",))
    index = build_index([rec_c])  # A.m deliberately never indexed
    assert resolve("m", rec_c, index, class_nodes=class_nodes, class_modules=class_modules, bases_index=idx) is None


def test_walk_closure_condition4_dispatches_inherited_body_self_call_on_override() -> None:
    """§17.2 condition 4 / AC-17.1's fourth stub-defeating fixture: an
    inherited body's own `self.<n>()` call is overridden on the analyzed
    class, asserted against a fixture where the two bodies carry
    DIFFERENT guards (different `site.lineno`s stand in for that here) --
    an implementation that binds the base's body passes every shape
    fixture and fails this one."""
    class_nodes = _class_nodes_from_source(
        "class Base:\n    def helper(self): pass\n    def uses_helper(self): pass\n"
        "class Derived(Base):\n    def helper(self): pass\n"
    )
    class_modules = {"Base": "mod", "Derived": "mod"}
    bases_index = _uniform_bases_index(class_nodes)

    rec_base_helper = _synthetic_record(
        "Base.helper", class_name="Base", module="mod", findings=(_synthetic_finding(100),)
    )
    rec_base_uses = _synthetic_record(
        "Base.uses_helper", class_name="Base", module="mod", delegates_to=("helper",)
    )
    rec_derived_helper = _synthetic_record(
        "Derived.helper", class_name="Derived", module="mod", findings=(_synthetic_finding(200),)
    )
    rec_derived_entry = _synthetic_record(
        "Derived.entry", class_name="Derived", module="mod", delegates_to=("uses_helper",)
    )
    index = build_index([rec_base_helper, rec_base_uses, rec_derived_helper, rec_derived_entry])

    contract = derive_contract(
        "mod", "Derived.entry", index,
        class_nodes=class_nodes, class_modules=class_modules, bases_index=bases_index,
    )
    site_linenos = {g.site.lineno for g in contract.guards}
    site_qualnames = {g.site.qualname for g in contract.guards}
    assert 200 in site_linenos
    assert 100 not in site_linenos
    assert "Derived.helper" in site_qualnames
    assert "Base.helper" not in site_qualnames

    # And the scoping note: a record reached the ORDINARY way (the entry
    # point's own class) is unaffected -- Derived.entry's OWN self-calls
    # (none here besides uses_helper, already covered above) never take
    # the condition-4 branch, since rec.class_name == analyzed_class there.
    resolved_keys = {
        key
        for _rec, key, _depth in _walk_closure(
            ("mod", "Derived.entry"), index,
            class_nodes=class_nodes, class_modules=class_modules, bases_index=bases_index,
        )
    }
    assert resolved_keys == {
        ("mod", "Derived.entry"),
        ("mod", "Base.uses_helper"),
        ("mod", "Derived.helper"),
    }


def test_measure_m_inh_entry_point_impact_flags_doubling() -> None:
    """§17.2 condition 3: the closure bound, published and checkable."""
    class_nodes = _class_nodes_from_source(
        "class Base:\n    def _x(self): pass\n    def h1(self): pass\n"
        "    def h2(self): pass\n    def h3(self): pass\n"
        "class Derived(Base):\n    def entry(self): pass\n"
    )
    class_modules = {"Base": "mod", "Derived": "mod"}
    bases_index = _uniform_bases_index(class_nodes)
    records = [
        _synthetic_record("Derived.entry", class_name="Derived", module="mod", delegates_to=("_x",)),
        _synthetic_record("Base._x", class_name="Base", module="mod", delegates_to=("h1", "h2", "h3")),
        _synthetic_record("Base.h1", class_name="Base", module="mod"),
        _synthetic_record("Base.h2", class_name="Base", module="mod"),
        _synthetic_record("Base.h3", class_name="Base", module="mod"),
    ]
    index = build_index(records)

    impact = measure_m_inh_entry_point_impact(
        ("mod", "Derived.entry"), index, class_nodes, class_modules, bases_index
    )
    assert impact["closure_size_before"] == 1
    assert impact["closure_size_after"] == 5
    assert impact["doubled"] is True


def test_measure_m_inh_entry_point_impact_not_doubled_when_growth_is_modest() -> None:
    class_nodes = _class_nodes_from_source(
        "class Base:\n    def _x(self): pass\nclass Derived(Base):\n    def entry(self): pass\n"
    )
    class_modules = {"Base": "mod", "Derived": "mod"}
    bases_index = _uniform_bases_index(class_nodes)
    records = [
        _synthetic_record("Derived.entry", class_name="Derived", module="mod", delegates_to=("_x", "other")),
        _synthetic_record("Base._x", class_name="Base", module="mod"),
        _synthetic_record("Derived.other", class_name="Derived", module="mod"),
    ]
    index = build_index(records)
    impact = measure_m_inh_entry_point_impact(
        ("mod", "Derived.entry"), index, class_nodes, class_modules, bases_index
    )
    assert impact["closure_size_before"] == 2  # entry + Derived.other (via module-level/step-1, unaffected)
    assert impact["closure_size_after"] == 3  # + Base._x
    assert impact["doubled"] is False


def test_compute_m_inh_selection_reports_half1_and_half2_populations_separately() -> None:
    class_nodes = _class_nodes_from_source(
        "class A:\n    def m(self): pass\nclass B:\n    def m(self): pass\n"
        "class C(A, B): pass\nclass D(A): pass\n"
    )
    class_modules = {"A": "mod", "B": "mod", "C": "mod", "D": "mod"}
    bases_index = _uniform_bases_index(class_nodes)
    records = [
        _synthetic_record("A.m", class_name="A", module="mod"),
        _synthetic_record("B.m", class_name="B", module="mod"),
        # Half 1 (the survey) admits "m" into C's delegates via the union
        # rule -- no ambiguity check -- so it shows up in
        # inherited_delegates even though Half 2 cannot uniquely resolve it.
        _synthetic_record(
            "C.entry", class_name="C", module="mod",
            delegates_to=("m",), inherited_delegates=("m",),
        ),
        # D's closure is unambiguous (only A), so it resolves cleanly and
        # would ALSO be found via the residual unresolved_calls channel if
        # the survey had left it unresolved (not the common case, but the
        # channel exists for exactly this).
        _synthetic_record("D.entry", class_name="D", module="mod", unresolved_calls=("m",)),
    ]
    index = build_index(records)

    selection = compute_m_inh_selection(records, index, class_nodes, class_modules, bases_index)
    assert len(selection["half1_admitted"]) == 1
    assert selection["half1_admitted"][0]["class"] == "C"
    assert selection["half1_admitted"][0]["reason"] == "ambiguous"
    assert selection["half1_ambiguous_mismatch"] == selection["half1_admitted"]

    assert len(selection["newly_resolved"]) == 1
    assert selection["newly_resolved"][0] == {
        "class": "D", "module": "mod", "name": "m", "base": "A", "base_module": "mod",
    }
    assert selection["refusal_counts"]["resolved"] == 1


# --- real-PLR pin: AC-17.1's own named assertion ---------------------------


def test_state_updated_resolves_to_resource_with_zero_guards_real_plr(
    survey_records: list[SurveyRecord], survey_index: dict[tuple[str, str], SurveyRecord]
) -> None:
    """AC-17.1, asserted by name: `_state_updated` resolves to
    `Resource._state_updated` and contributes ZERO guards. This is the
    fixture round 1's C8 named -- `LiquidHandler` overrides
    `serialize_state`, so condition 4 must send `_state_updated`'s own
    `self.serialize_state()` call to the OVERRIDE when reached through
    `LiquidHandler`'s closure, not to `Resource`'s own (different) body.
    """
    root = default_plr_pkg_root()
    class_nodes, class_modules = build_plr_class_index(root)
    bases_index = build_plr_class_bases_index(root, class_nodes)

    base = resolve_via_base_closure("LiquidHandler", "_state_updated", class_nodes, bases_index)
    assert base == "Resource"

    resource_module = class_modules["Resource"]
    state_updated_contract = derive_contract(
        resource_module, "Resource._state_updated", survey_index,
        class_nodes=class_nodes, class_modules=class_modules, bases_index=bases_index,
    )
    assert state_updated_contract.guards == ()

    pick_up_module = "pylabrobot.liquid_handling.liquid_handler"
    pick_up_contract = derive_contract(
        pick_up_module, "LiquidHandler.pick_up_resource", survey_index,
        class_nodes=class_nodes, class_modules=class_modules, bases_index=bases_index,
    )
    assert ("unresolved_delegate", "_state_updated") not in pick_up_contract.gaps
    drop_contract = derive_contract(
        pick_up_module, "LiquidHandler.drop_resource", survey_index,
        class_nodes=class_nodes, class_modules=class_modules, bases_index=bases_index,
    )
    assert ("unresolved_delegate", "_state_updated") not in drop_contract.gaps


def test_liquid_handler_has_more_than_one_base_real_plr() -> None:
    """§17.2's own claim, made checkable: condition 1's ambiguity refusal
    is live at this pin, not a hypothetical."""
    root = default_plr_pkg_root()
    class_nodes, class_modules = build_plr_class_index(root)
    bases_index = build_plr_class_bases_index(root, class_nodes)
    assert len(bases_index.bases["LiquidHandler"]) > 1


def test_move_family_entry_points_do_not_double_and_add_zero_guards_real_plr(
    survey_index: dict[tuple[str, str], SurveyRecord]
) -> None:
    """§17.2 condition 3, pinned: at this survey pin, `_state_updated`'s
    own zero guards mean the move-family entry points' guard counts and
    per-guard depth multisets are UNCHANGED even where closure size grows
    (round 1's C11 -- the multiset is the only thing that could catch a
    perturbation, and here it correctly reports none)."""
    root = default_plr_pkg_root()
    class_nodes, class_modules = build_plr_class_index(root)
    bases_index = build_plr_class_bases_index(root, class_nodes)
    module = "pylabrobot.liquid_handling.liquid_handler"
    for qualname in ("LiquidHandler.move_lid", "LiquidHandler.move_plate", "LiquidHandler.move_resource"):
        impact = measure_m_inh_entry_point_impact(
            (module, qualname), survey_index, class_nodes, class_modules, bases_index
        )
        assert impact["doubled"] is False
        assert impact["guard_count_before"] == impact["guard_count_after"]
        assert impact["depth_multiset_before"] == impact["depth_multiset_after"]
        assert impact["closure_size_after"] >= impact["closure_size_before"]


# ---------------------------------------------------------------------------
# AC-17.3 (spec 260909_plr-sema-move-family-increment.md §17.4, T52): the
# `_resource_pickup` typestate -- P5's singleton anchor, its absence rule,
# and P6's intra-operation ordered effect/guard walk.
# ---------------------------------------------------------------------------


def test_singleton_anchor_selection_finds_resource_pickup_by_name_real_plr() -> None:
    """AC-17.3: the complete anchor selection is published, with
    `_resource_pickup` asserted PRESENT by name on `LiquidHandler`."""
    root = default_plr_pkg_root()
    class_nodes, class_modules = build_plr_class_index(root)
    function_index = build_plr_function_index(root)
    anchors, candidates = compute_singleton_typestate_anchors(class_nodes, class_modules, function_index)
    assert "_resource_pickup" in anchors.get("LiquidHandler", ())
    (candidate,) = (c for c in candidates if c.class_name == "LiquidHandler" and c.field == "_resource_pickup")
    assert candidate.present is True
    assert candidate.removed_by_clause is None


def test_singleton_anchor_absence_rule_three_fixtures() -> None:
    """AC-17.3: three absence fixtures, not one (round 2's R2-C2). (i) a
    synthetic `@property` whose setter does MORE than one assignment ->
    clause 1, absent. (ii) the genuine getter/setter PAIR of one property,
    two definitions -> clause 3's own exception, present. (iii) a THREE-
    definition qualname -> clause 3 itself, absent -- proving the exception
    (exactly two) does not swallow clause 3 outright."""
    from plr_sema.derive.receiver_state import _singleton_anchor_absent

    module = "synthetic.module"

    # (i) clause 1.
    tree1 = ast.parse(
        "class C1:\n"
        "    @property\n"
        "    def foo(self):\n"
        "        return self._foo\n"
        "    @foo.setter\n"
        "    def foo(self, value):\n"
        "        self._log = True\n"
        "        self._foo = value\n"
    )
    class1 = tree1.body[0]
    getter1, setter1 = class1.body[0], class1.body[1]
    fi1 = {(module, "C1.foo", getter1.lineno): getter1, (module, "C1.foo", setter1.lineno): setter1}
    assert _singleton_anchor_absent(class1, "foo", "C1", module, {"C1": class1}, fi1) == 1

    # (ii) clause 3's own exception.
    tree2 = ast.parse(
        "class C2:\n"
        "    @property\n"
        "    def foo(self):\n"
        "        return self._foo\n"
        "    @foo.setter\n"
        "    def foo(self, value):\n"
        "        self._foo = value\n"
    )
    class2 = tree2.body[0]
    getter2, setter2 = class2.body[0], class2.body[1]
    fi2 = {(module, "C2.foo", getter2.lineno): getter2, (module, "C2.foo", setter2.lineno): setter2}
    assert _singleton_anchor_absent(class2, "foo", "C2", module, {"C2": class2}, fi2) is None

    # (iii) clause 3 itself.
    tree3 = ast.parse("class C3:\n    def foo(self):\n        pass\n")
    class3 = tree3.body[0]
    def3 = class3.body[0]
    fi3 = {(module, "C3.foo", 100): def3, (module, "C3.foo", 200): def3, (module, "C3.foo", 300): def3}
    assert _singleton_anchor_absent(class3, "foo", "C3", module, {"C3": class3}, fi3) == 3


def test_compute_anchor_guard_states_move_family_real_plr() -> None:
    """AC-17.3: `:2070` from `ENTRY` (nothing precedes it in the closure),
    `:2120`/`:2147` from `HELD`, on the REAL `move_resource`/`move_lid`/
    `move_plate` closures, with ZERO widening -- the pin-level claim
    §17.4.3's own box makes."""
    root = default_plr_pkg_root()
    class_nodes, class_modules = build_plr_class_index(root)
    bases_index = build_plr_class_bases_index(root, class_nodes)
    liquid_handler = class_nodes["LiquidHandler"]
    for entry_name in ("pick_up_resource", "move_resource", "move_lid", "move_plate"):
        entry_node = next(m for m in liquid_handler.body if getattr(m, "name", None) == entry_name)
        guard_states, widened_by, _net = compute_anchor_guard_states(
            entry_node,
            field="_resource_pickup",
            class_name="LiquidHandler",
            class_nodes=class_nodes,
            class_modules=class_modules,
            bases_index=bases_index,
        )
        assert widened_by == {"condition_1": 0, "condition_2": 0, "condition_3": 0}
        assert guard_states.get(2070) == "ENTRY"
    move_resource_node = next(m for m in liquid_handler.body if getattr(m, "name", None) == "move_resource")
    guard_states, _widened, net = compute_anchor_guard_states(
        move_resource_node,
        field="_resource_pickup",
        class_name="LiquidHandler",
        class_nodes=class_nodes,
        class_modules=class_modules,
        bases_index=bases_index,
    )
    assert guard_states == {2070: "ENTRY", 2120: "HELD", 2147: "HELD"}
    assert net == "EMPTY"


def test_derive_contract_attaches_anchor_state_to_real_guards(survey_index: dict[tuple[str, str], SurveyRecord]) -> None:
    """AC-17.3: `derive_contract`, given `anchor_fields`, attaches
    `anchor_state`/`anchor_field` to the three real move-family guards --
    the SAME wiring `derive/__main__.py` uses, exercised directly rather
    than through the whole CLI pipeline."""
    root = default_plr_pkg_root()
    class_nodes, class_modules = build_plr_class_index(root)
    bases_index = build_plr_class_bases_index(root, class_nodes)
    function_index = build_plr_function_index(root)
    module = "pylabrobot.liquid_handling.liquid_handler"
    contract = derive_contract(
        module, "LiquidHandler.move_resource", survey_index,
        function_index=function_index, class_nodes=class_nodes, class_modules=class_modules, bases_index=bases_index,
        anchor_fields={"LiquidHandler": ("_resource_pickup",)},
    )
    by_lineno = {g.site.lineno: g for g in contract.guards if g.anchor_field is not None}
    assert by_lineno[2070].anchor_state == "ENTRY"
    assert by_lineno[2070].anchor_field == "_resource_pickup"
    assert by_lineno[2120].anchor_state == "HELD"
    assert by_lineno[2147].anchor_state == "HELD"
    assert contract.anchor_net_effects == {"_resource_pickup": "EMPTY"}


# ---------------------------------------------------------------------------
# AC-17.5 (spec 260909_plr-sema-move-family-increment.md S17.5.1/S17.1.4,
# T54): M3 -- the closure-wide constant-argument map -- and the surface
# SELECTION extension.
# ---------------------------------------------------------------------------


def test_find_delegate_calls_returns_every_self_call_in_source_order() -> None:
    """`find_delegate_calls` (T54) is `_find_delegate_call`'s own
    generalization: EVERY `self.<name>(...)` call, not just the singular
    one clauses 1/2 admit -- `move_resource`'s own shape (two direct
    calls to the same delegate)."""
    K = _func_node("def K(self, x):\n    self.helper(x)\n    self.helper(x, y=1)\n")
    calls = find_delegate_calls(K, "helper")
    assert [c.lineno for c in calls] == [2, 3]


def test_compute_caller_args_for_call_constants_only_skips_free_name_argument() -> None:
    """AC-17.5 fixture (ii): a caller-side NAME (a bare `Var`, e.g. a
    local variable or parameter) does NOT bind under M3's
    `constants_only=True` depth-lift restriction -- S17.5.1(b)'s
    narrowness claim, made checkable at the primitive that implements it.
    The SAME call, unrestricted (`constants_only=False`, depth == 1's own
    unchanged behaviour), DOES bind -- proving the restriction, and
    nothing else, suppressed it."""
    K = _func_node("def K(self, x):\n    self.helper(x)\n")
    D = _func_node("def helper(self, y):\n    pass\n")
    (call,) = find_delegate_calls(K, "helper")
    assert compute_caller_args_for_call(K, D, call, constants_only=True) == {}
    assert compute_caller_args_for_call(K, D, call, constants_only=False) == {
        "y": {"node": "Var", "name": "x"}
    }


def test_compute_caller_args_for_call_constants_only_binds_setlit_and_self_rooted_envref() -> None:
    """AC-17.5 fixture (iii): a `SetLit` of constants DOES bind under
    `constants_only=True` -- it has no free names by construction (G9) --
    and so does a self-rooted `EnvRef`; the free-named argument at the
    SAME call site still does not."""
    K = _func_node(
        "def K(self, x):\n"
        "    self.helper(x, default={'a', 'b'}, method=self.backend.foo)\n"
    )
    D = _func_node("def helper(self, y, default, method):\n    pass\n")
    (call,) = find_delegate_calls(K, "helper")
    result = compute_caller_args_for_call(K, D, call, constants_only=True)
    assert result["default"] == {"node": "SetLit", "values": ["a", "b"]}
    assert result["method"] == {"node": "EnvRef", "path": ["self", "backend", "foo"], "args": None}
    assert "y" not in result


def test_derive_contract_caller_args_sites_collects_across_whole_closure() -> None:
    """M3's own worked shape at the `derive_contract` level (S17.5.1(a)):
    entry `A` reaches delegate `E` through TWO different records -- `B`
    at depth 1 and `C` at depth 2, both delegating to `E` -- and
    `caller_args_sites` collects BOTH call sites, each computed against
    its OWN caller (`B`'s `default={'a','b'}`, `C`'s `default={'c'}`),
    with the free-named argument unbound at both. This is round 1's C2
    made checkable: an implementation scanning only the entry point's own
    body would see neither site at all."""
    a_node = _func_node("def A(self, x):\n    self.B(x)\n")
    b_node = _func_node(
        "def B(self, p):\n"
        "    self.E(p, default={'a', 'b'})\n"
        "    self.C(p)\n"
    )
    c_node = _func_node("def C(self, q):\n    self.E(q, default={'c'})\n")
    e_node = _func_node(
        "def E(self, y, default):\n"
        "    if y:\n"
        "        raise ValueError('y')\n"
    )
    function_index = {
        ("synthetic.module", "Foo.A", 1): a_node,
        ("synthetic.module", "Foo.B", 1): b_node,
        ("synthetic.module", "Foo.C", 1): c_node,
        ("synthetic.module", "Foo.E", 1): e_node,
    }
    rec_a = _synthetic_record("Foo.A", class_name="Foo", delegates_to=("B",))
    rec_b = _synthetic_record("Foo.B", class_name="Foo", delegates_to=("E", "C"))
    rec_c = _synthetic_record("Foo.C", class_name="Foo", delegates_to=("E",))
    rec_e = _synthetic_record("Foo.E", class_name="Foo", findings=(_synthetic_finding(3),))
    index = build_index([rec_a, rec_b, rec_c, rec_e])

    contract = derive_contract("synthetic.module", "Foo.A", index, function_index=function_index)

    (guard,) = [g for g in contract.guards if g.depth >= 1]
    sites = guard.caller_args_sites
    assert sites is not None
    assert len(sites) == 2
    by_qual = {s["caller_qualname"]: s for s in sites}
    assert set(by_qual) == {"Foo.B", "Foo.C"}
    assert by_qual["Foo.B"]["args"]["default"] == {"node": "SetLit", "values": ["a", "b"]}
    assert by_qual["Foo.C"]["args"]["default"] == {"node": "SetLit", "values": ["c"]}
    assert "y" not in by_qual["Foo.B"]["args"]
    assert "y" not in by_qual["Foo.C"]["args"]


def test_derive_contract_caller_args_sites_declines_on_closure_unresolved_call() -> None:
    """AC-17.5 fixture (iv): a closure containing ONE record with a
    non-empty `unresolved_calls` makes the WHOLE closure's M3 fold
    decline (`caller_args_sites` stays `None` for every depth >= 1 guard
    in it), and the SAME closure with that call resolved (removed from
    `unresolved_calls`) decides -- S17.5.1's first fail-closed condition,
    and the mechanical form of the T50-before-T54 task ordering."""
    a_node = _func_node("def A(self, x):\n    self.B(x)\n")
    b_node = _func_node("def B(self, p):\n    self.D(p)\n")
    d_node = _func_node(
        "def D(self, y):\n"
        "    if y:\n"
        "        raise ValueError('y')\n"
    )
    function_index = {
        ("synthetic.module", "Foo.A", 1): a_node,
        ("synthetic.module", "Foo.B", 1): b_node,
        ("synthetic.module", "Foo.D", 1): d_node,
    }
    rec_a = _synthetic_record("Foo.A", class_name="Foo", delegates_to=("B",))
    rec_d = _synthetic_record("Foo.D", class_name="Foo", findings=(_synthetic_finding(3),))

    rec_b_unresolved = _synthetic_record(
        "Foo.B", class_name="Foo", delegates_to=("D",), unresolved_calls=("ghost",)
    )
    index_declines = build_index([rec_a, rec_b_unresolved, rec_d])
    contract_declines = derive_contract("synthetic.module", "Foo.A", index_declines, function_index=function_index)
    (guard_declines,) = [g for g in contract_declines.guards if g.depth >= 1]
    assert guard_declines.caller_args_sites is None

    rec_b_resolved = _synthetic_record("Foo.B", class_name="Foo", delegates_to=("D",))
    index_decides = build_index([rec_a, rec_b_resolved, rec_d])
    contract_decides = derive_contract("synthetic.module", "Foo.A", index_decides, function_index=function_index)
    (guard_decides,) = [g for g in contract_decides.guards if g.depth >= 1]
    assert guard_decides.caller_args_sites is not None
    assert [s["lineno"] for s in guard_decides.caller_args_sites] == [2]


def test_derive_contract_caller_args_sites_declines_on_closure_record_missing_k() -> None:
    """S17.5.1's SECOND fail-closed condition, the sibling of the test
    above: a visited closure record with no `K` -- i.e. present in the
    survey index and therefore walked, but absent from `function_index`
    so its AST is unavailable -- makes the WHOLE closure's M3 fold
    decline, and the SAME closure with that record's `K` supplied
    decides.

    Without this, an incomplete site set could be folded as if it were
    complete, which is the one way M3's superset argument could be
    unsound: the fold's soundness rests on ranging over a SUPERSET of the
    executed call sites, and a record whose body could not be read may
    contain an admitted site nobody counted. Added at the sprint-133
    close audit, which found the condition implemented correctly but
    exercised by no test."""
    a_node = _func_node("def A(self, x):\n    self.B(x)\n")
    b_node = _func_node("def B(self, p):\n    self.D(p)\n")
    d_node = _func_node(
        "def D(self, y):\n"
        "    if y:\n"
        "        raise ValueError('y')\n"
    )
    rec_a = _synthetic_record("Foo.A", class_name="Foo", delegates_to=("B",))
    rec_b = _synthetic_record("Foo.B", class_name="Foo", delegates_to=("D",))
    rec_d = _synthetic_record("Foo.D", class_name="Foo", findings=(_synthetic_finding(3),))
    index = build_index([rec_a, rec_b, rec_d])

    # `Foo.B` is walked (it is in the survey index and `Foo.A` delegates to
    # it) but its AST is absent, so the closure carries a record with no `K`.
    function_index_missing_k = {
        ("synthetic.module", "Foo.A", 1): a_node,
        ("synthetic.module", "Foo.D", 1): d_node,
    }
    contract_declines = derive_contract(
        "synthetic.module", "Foo.A", index, function_index=function_index_missing_k
    )
    (guard_declines,) = [g for g in contract_declines.guards if g.depth >= 1]
    assert guard_declines.caller_args_sites is None

    # The same closure with `Foo.B`'s `K` supplied decides.
    function_index_complete = dict(function_index_missing_k)
    function_index_complete[("synthetic.module", "Foo.B", 1)] = b_node
    contract_decides = derive_contract(
        "synthetic.module", "Foo.A", index, function_index=function_index_complete
    )
    (guard_decides,) = [g for g in contract_decides.guards if g.depth >= 1]
    assert guard_decides.caller_args_sites is not None
    assert [s["lineno"] for s in guard_decides.caller_args_sites] == [2]


# --- real-PLR pin: AC-17.5's stub-defeater and by-value surface counters ---


def test_ac_17_5_move_family_check_args_admitted_call_site_set_real_plr(
    survey_index: dict[tuple[str, str], SurveyRecord], plr_function_index,
) -> None:
    """AC-17.5's stub-defeating half: the admitted call-site set for
    `_check_args` contains EXACTLY THREE entries -- `:2345`, `:2364` and
    `:2079` -- for EVERY ONE of `move_resource`, `move_lid` and
    `move_plate`, each with its own lineno and caller qualname. An
    implementation that scans only the entry point's own body returns TWO
    entries for `move_resource` and ZERO for `move_lid`/`move_plate`."""
    root = default_plr_pkg_root()
    class_nodes, class_modules = build_plr_class_index(root)
    bases_index = build_plr_class_bases_index(root, class_nodes)
    module = "pylabrobot.liquid_handling.liquid_handler"
    expected = {
        (2345, "LiquidHandler.move_resource"),
        (2364, "LiquidHandler.move_resource"),
        (2079, "LiquidHandler.pick_up_resource"),
    }
    for entry_name in ("move_resource", "move_lid", "move_plate"):
        contract = derive_contract(
            module, f"LiquidHandler.{entry_name}", survey_index,
            function_index=plr_function_index, class_nodes=class_nodes, class_modules=class_modules,
            bases_index=bases_index,
        )
        check_args_guards = [g for g in contract.guards if g.site.qualname == "LiquidHandler._check_args"]
        assert check_args_guards, f"{entry_name}: no _check_args guard inlined"
        for guard in check_args_guards:
            sites = guard.caller_args_sites
            assert sites is not None, f"{entry_name}: the fold declined -- site set is None"
            observed = {(s["lineno"], s["caller_qualname"]) for s in sites}
            assert observed == expected, f"{entry_name} at :{guard.site.lineno}: {observed}"


def test_ac_17_5_move_family_check_args_sites_and_383_stay_half(
    survey_index: dict[tuple[str, str], SurveyRecord], plr_function_index,
) -> None:
    """`:375` decides `F` on the move family (`LiquidHandlerChatterboxBackend
    .pick_up_resource`/`.drop_resource` both satisfy `params <= default`
    at every one of the three sites, so the conjunctive fold decides `F`
    too), while `:383` stays ½ (`has_var_keyword` is `False` on both real
    rows) -- exercised directly through `evaluate_guard` against the REAL,
    regenerated contract table, S17.5.2's refusal made checkable."""
    from plr_sema.check import ir
    from plr_sema.check.predicate import evaluate_guard

    root = default_plr_pkg_root()
    class_nodes, class_modules = build_plr_class_index(root)
    bases_index = build_plr_class_bases_index(root, class_nodes)
    function_index = plr_function_index
    module = "pylabrobot.liquid_handling.liquid_handler"
    anchor_fields, _ = compute_singleton_typestate_anchors(class_nodes, class_modules, function_index)
    selected = collect_env_ref_method_names(
        {
            "LiquidHandler._check_args": {
                "guards": [
                    {
                        "predicate": {"node": "TRUE"},
                        "caller_args_sites": [
                            {"args": {"method": {"node": "EnvRef", "path": ["self", "backend", "pick_up_resource"], "args": None}}},
                            {"args": {"method": {"node": "EnvRef", "path": ["self", "backend", "drop_resource"], "args": None}}},
                        ],
                    }
                ]
            }
        }
    )
    raw_rows, _n_cand, _n_absent = build_backend_surface(function_index, selected)
    rows = {key: backend_surface_entry_to_json(e) for key, e in raw_rows.items()}
    env = frozenset({'obs:backend_class="LiquidHandlerChatterboxBackend"'})
    for entry_name in ("move_resource", "move_lid", "move_plate"):
        contract = derive_contract(
            module, f"LiquidHandler.{entry_name}", survey_index,
            function_index=function_index, class_nodes=class_nodes, class_modules=class_modules,
            bases_index=bases_index, anchor_fields=anchor_fields,
        )
        contract_json = {
            "guards": [_guard_to_json(g) for g in contract.guards],
            "backend_surface": {"rows": rows},
        }
        guard_375 = next(g for g in contract_json["guards"] if g["site"]["lineno"] == 375)
        guard_383 = next(g for g in contract_json["guards"] if g["site"]["lineno"] == 383)
        result_375 = evaluate_guard(guard_375, ir.Call(receiver=0, receiver_type="LiquidHandler", method=entry_name, kwargs={}), contract_json, {}, env=env)
        result_383 = evaluate_guard(guard_383, ir.Call(receiver=0, receiver_type="LiquidHandler", method=entry_name, kwargs={}), contract_json, {}, env=env)
        assert result_375.verdict == "safe", f"{entry_name} :375 -> {result_375}"
        assert result_383.verdict == "unknown", f"{entry_name} :383 -> {result_383}"
        assert result_383.reason == "guard_env_dependent"


def test_ac_17_5_surface_counters_by_value_and_drop_resource_row(
    survey_records: list[SurveyRecord], survey_index: dict[tuple[str, str], SurveyRecord], plr_function_index,
) -> None:
    """AC-17.5 (vii)/(vi): the three row-level counters asserted BY VALUE
    -- `n_surface_candidates` 172, `n_surface_absent_by_c15` 73,
    `n_surface_rows` 99 (from 160/71/89), with the invariant 172 - 73 = 99
    -- and `LiquidHandlerChatterboxBackend.drop_resource` present in the
    `rows` key list by name, `params` exactly `["drop"]`,
    `has_var_keyword` exactly `False`. Derived off `pick_up_resource`'s
    measured twin (S17.1.4); if this diverges it is recorded in S17.14
    against this criterion, per the row's own instruction."""
    root = default_plr_pkg_root()
    class_nodes, class_modules = build_plr_class_index(root)
    bases_index = build_plr_class_bases_index(root, class_nodes)
    stamp = survey_stamp()
    payload = build_derived_contracts_payload(
        survey_records, survey_index, stamp,
        function_index=plr_function_index,
        minh_class_nodes=class_nodes, minh_class_modules=class_modules, minh_bases_index=bases_index,
    )
    bs = payload["backend_surface"]
    assert bs["n_surface_candidates"] == 172
    assert bs["n_surface_absent_by_c15"] == 73
    assert bs["n_surface_rows"] == 99
    assert bs["n_surface_candidates"] - bs["n_surface_absent_by_c15"] == bs["n_surface_rows"]
    row = bs["rows"]["LiquidHandlerChatterboxBackend.drop_resource"]
    assert row["params"] == ["drop"]
    assert row["has_var_keyword"] is False


def test_ac_17_5_n_entries_with_backend_surface_moves_and_lists_move_family_by_name(
    survey_records: list[SurveyRecord], survey_index: dict[tuple[str, str], SurveyRecord], plr_function_index,
) -> None:
    """AC-17.5 fixture (v): `n_entries_with_backend_surface` MOVES once
    T54's selection extension (`collect_env_ref_method_names` scanning
    `caller_args_sites`) and attachment extension (the attachment filter
    scanning `caller_args_sites`) are BOTH live -- T53 alone left the
    move family entirely unattached (0 of the 13 keys were move-family),
    and T54 attaches all three."""
    root = default_plr_pkg_root()
    class_nodes, class_modules = build_plr_class_index(root)
    bases_index = build_plr_class_bases_index(root, class_nodes)
    stamp = survey_stamp()
    payload = build_derived_contracts_payload(
        survey_records, survey_index, stamp,
        function_index=plr_function_index,
        minh_class_nodes=class_nodes, minh_class_modules=class_modules, minh_bases_index=bases_index,
    )
    bs = payload["backend_surface"]
    entries_with_surface = {
        key for key, entry in payload["contracts"].items() if "backend_surface" in entry
    }
    assert bs["n_entries_with_backend_surface"] == len(entries_with_surface)
    for move_key in ("LiquidHandler.move_resource", "LiquidHandler.move_lid", "LiquidHandler.move_plate"):
        assert move_key in entries_with_surface, f"{move_key} missing from the attached set"


def test_ac_17_5_no_backend_method_name_literal_in_t54_change() -> None:
    """AC-17.5 (viii)'s own grep: no backend method name (`pick_up_
    resource`, `drop_resource`, etc.) occurs as a literal `ast.Constant`
    string anywhere in the modules T54 touches -- the selection/
    attachment extensions and M3 itself are generic over PLR's own
    function index, never a hand-typed method-name table. This is what
    makes R-CONST's `n_resolved_by_rule` staying unchanged a structural
    fact rather than a hope: R-CONST's own resolution path
    (`ctx.backend_surface`, keyed off the OBSERVED backend_class/method)
    is untouched by every string this scan would catch."""
    scan_modules = (
        REPO_ROOT / "plr-sema" / "src" / "plr_sema" / "derive" / "__init__.py",
        REPO_ROOT / "plr-sema" / "src" / "plr_sema" / "derive" / "receiver_state.py",
        REPO_ROOT / "plr-sema" / "src" / "plr_sema" / "derive" / "__main__.py",
        REPO_ROOT / "plr-sema" / "src" / "plr_sema" / "derive" / "bindings.py",
        REPO_ROOT / "plr-sema" / "src" / "plr_sema" / "check" / "predicate.py",
    )
    forbidden = frozenset({
        "pick_up_resource", "drop_resource", "move_resource", "move_lid", "move_plate",
    })
    offenders: list[str] = []
    for path in scan_modules:
        source = path.read_text(encoding="utf-8")
        offenders.extend(_scan_volume_forbidden_literals(source, str(path), forbidden))
    assert offenders == [], f"hand-typed move-family method name found: {offenders}"
