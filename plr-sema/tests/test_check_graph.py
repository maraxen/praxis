"""Spec 260901 §6.3/§6.5, T8 (backlog #4834): `plr_sema.check`'s round-1 entry
point, `check_graph(graph_json, contracts_json) -> AnalysisReport`.

Fixture protocol: `simple_transfer` (`tests/fixtures/simple_transfer_graph.
json`), generated out-of-process (spec §6.2/C5 -- `check/` never imports the
extractor; this file doesn't either) by subprocessing into the EXISTING
`praxis.backend.utils.plr_static_analysis.visitors.computation_graph_
extractor.extract_graph_from_source`, over the `SIMPLE_TRANSFER_SOURCE`
fixture already used by `tests/utils/test_computation_graph.py` at repo
root -- chosen because all four of its operations
(`pick_up_tips`/`aspirate`/`dispense`/`drop_tips`) resolve a concrete
`receiver_type` ("LiquidHandler") and a `method_name` that is BOTH in
`SUPPORTED_TOOLS` AND has a populated entry (>=1 guard) in the real,
committed `derived_contracts.json` -- so this fixture genuinely exercises
the contract-table lookup (spec §6.2's D1 flag: `receiver_type_unknown`
alone must not be the only thing satisfying AC-6.3, or the contract table
goes entirely unexercised). See `test_fixture_exercises_contract_table_
lookup` below for the direct confirmation.
"""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from plr_sema.check import SUPPORTED_TOOLS, check_graph, ir
from plr_sema.verdict import AnalysisReport, Finding, PlrSite, SoundnessScope, Verdict

PLR_SEMA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLR_SEMA_ROOT.parent
FIXTURE_GRAPH_JSON = PLR_SEMA_ROOT / "tests" / "fixtures" / "simple_transfer_graph.json"
CONTRACTS_JSON = PLR_SEMA_ROOT / "data" / "derived_contracts.json"

# The full SHA at the pin AC-6.7 targets -- same pin as test_telemetry.py's
# AC-4.3 (external/pylabrobot HEAD, confirmed live this session via
# `git -C external/pylabrobot rev-parse HEAD`).
_PLR_PIN_SHA = "dd79c4c89bc008629a1c598ea614be5e6067d1f9"


@pytest.fixture(scope="module")
def graph_json() -> str:
    return FIXTURE_GRAPH_JSON.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def contracts_json() -> str:
    return CONTRACTS_JSON.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def report(graph_json: str, contracts_json: str) -> AnalysisReport:
    return check_graph(graph_json, contracts_json)


# ---------------------------------------------------------------------------
# AC-6.1 -- import plr_sema.check with BOTH libcst and pylabrobot poisoned.
# ---------------------------------------------------------------------------


def test_check_imports_without_libcst() -> None:
    """Spec AC-6.1/§6.3's `test_check_imports_without_libcst`: poison BOTH
    `libcst` and `pylabrobot` to `None` in `sys.modules` (stronger than
    simply not installing them -- fails even if the import is merely
    reachable, not just unavailable), then `import plr_sema.check`. Assert
    exit 0."""
    src_path = str(PLR_SEMA_ROOT / "src")
    preamble = (
        "import sys; "
        "sys.modules['libcst'] = None; "
        "sys.modules['pylabrobot'] = None; "
        "import plr_sema.check"
    )
    result = subprocess.run(
        [sys.executable, "-c", preamble],
        cwd=str(PLR_SEMA_ROOT),
        env={"PYTHONPATH": src_path, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"import plr_sema.check failed with libcst+pylabrobot poisoned:\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )


# ---------------------------------------------------------------------------
# AC-6.3 / AC-6.4 -- fixture graph -> check_graph -> AnalysisReport.
# ---------------------------------------------------------------------------


def test_fixture_graph_yields_unknown_report_with_findings(report: AnalysisReport) -> None:
    """AC-6.3: the committed fixture graph JSON, passed to `check_graph`,
    yields an `AnalysisReport` with `verdict == UNKNOWN` and >=1 finding."""
    assert report.verdict is Verdict.UNKNOWN
    assert len(report.findings) >= 1


def test_operation_ids_are_a_subset_of_real_graph_ids(report: AnalysisReport) -> None:
    """AC-6.4 (round-4 remediation, B2/fix 6: strengthened from subset to
    surjectivity; spec 260903 §12.3.4/§12.9's main-spec amendment: now
    re-read over `OBLIGED(graph)`, not the raw operation-id set).
    `{f.operation_id for f in report.findings}` must equal --  not just be
    a subset of -- `ir.obliged_operation_ids(graph_payload)`. The shipped
    `simple_transfer_graph.json` fixture carries no `REGION` at all
    (AC-12.9), so `OBLIGED(graph) == {op.id for op in graph.operations}`
    here and this test's own behaviour is UNCHANGED from pre-260903 -- see
    `test_dead_loop_body_...` below for the fixture where the two sets
    actually differ. The subset-only form was the anti-fabrication anchor
    but said nothing about COVERAGE: `len(findings) >= len(operations)`
    (AC-6.3) does not imply every operation actually received >=1 finding,
    and nothing in the pre-round-4 suite asserted the surjective direction.
    `research_a_d.md:339-345`'s finding, independently confirmed: a
    `check_graph` that only ever emits findings for op_1 would still pass a
    subset-only check and a count-only check simultaneously, while silently
    never reporting anything about op_2/op_3/op_4."""
    graph_payload = json.loads(FIXTURE_GRAPH_JSON.read_text(encoding="utf-8"))
    real_ids = ir.obliged_operation_ids(graph_payload)

    finding_ids = {f.operation_id for f in report.findings}
    assert finding_ids == real_ids, (
        f"report.findings' operation_id set {sorted(finding_ids)} != the "
        f"fixture graph's OBLIGED(graph) set {sorted(real_ids)} -- either "
        f"a fabricated id ({finding_ids - real_ids}) or an uncovered "
        f"operation ({real_ids - finding_ids})"
    )


def test_fixture_exercises_contract_table_lookup(report: AnalysisReport) -> None:
    """Spec §6.2's D1 flag, directly confirmed: `check_graph` must not be
    satisfiable using ONLY `receiver_type_unknown` (which needs no
    contract-table lookup at all) -- at least one finding must come from a
    REAL, populated contract-table entry, evidenced by a non-null
    `plr_site` pointing into `external/pylabrobot` (a guard's site is only
    ever populated from a resolved `DerivedContract`, never from
    `receiver_type_unknown`/`unsupported_tool`/`no_contract_derived`,
    which all pass `plr_site=None` -- see `plr_sema.check._unknown`)."""
    reasons = {f.reason for f in report.findings}
    assert reasons != {"receiver_type_unknown"}, (
        "every finding is receiver_type_unknown -- the contract table was "
        "never touched (spec §6.2's D1 flag: this is exactly the degenerate "
        "gate the fix closes)"
    )
    grounded_sites = [f for f in report.findings if f.plr_site is not None]
    assert grounded_sites, "no finding carries a plr_site -- no guard from a real contract fired"
    assert any(
        "external/pylabrobot" in f.plr_site.file for f in grounded_sites
    ), "no finding's plr_site points into external/pylabrobot -- contract table not exercised"


# ---------------------------------------------------------------------------
# 260901 T11 -- whole-surface decoupling from SUPPORTED_TOOLS.
# ---------------------------------------------------------------------------


def _single_op_graph(method_name: str, receiver_type: str) -> str:
    return json.dumps(
        {
            "protocol_fqn": "test.t11_whole_surface",
            "operations": [
                {
                    "id": "op_1",
                    "method_name": method_name,
                    "receiver_variable": "x",
                    "receiver_type": receiver_type,
                }
            ],
            "resources": {},
        }
    )


def test_non_liquid_handler_family_resolves_end_to_end(contracts_json: str) -> None:
    """T11 item 1: `check_graph` resolves an operation OUTSIDE
    `LiquidHandler`/the old `SUPPORTED_TOOLS` 10 end-to-end through a real,
    populated contract-table entry. `PlateReader.read_absorbance` has ZERO
    own findings but delegates to `get_plate`, which has one -- so this also
    directly confirms T11 item 4's zero-findings decision: a zero-own-finding
    entry point still surfaces a real, grounded guard inherited through its
    closure, rather than falling back to `unsupported_tool`."""
    report = check_graph(_single_op_graph("read_absorbance", "PlateReader"), contracts_json)
    assert report.verdict is Verdict.UNKNOWN
    reasons = {f.reason for f in report.findings}
    assert "unsupported_tool" not in reasons
    grounded = [f for f in report.findings if f.plr_site is not None]
    assert grounded, "PlateReader.read_absorbance surfaced no grounded finding via its delegate closure"
    assert any(f.plr_site.qualname == "PlateReader.get_plate" for f in grounded), (
        "expected a finding grounded at PlateReader.get_plate (the delegate "
        "read_absorbance's own zero-finding body inlines a guard from)"
    )


def test_unsupported_tool_fires_only_for_genuinely_unknown_methods(contracts_json: str) -> None:
    """T11 items 3/4: `unsupported_tool` now means "key absent from the
    whole-survey contract table" -- verified against all three cases it must
    distinguish:

    * a method name the whole-survey derivation never saw at all -> fires.
    * a real, finding-bearing method OUTSIDE the old 10-name
      `SUPPORTED_TOOLS` allowlist (`pick_up_tips96`) -> must NOT fire (the
      old gate would have fired here; this is the direct regression test
      for decoupling derivation from `SUPPORTED_TOOLS`).
    * a real method the survey scanned with zero own findings and an empty
      closure (`Centrifuge.spin`) -- "known and unconstrained" -- must NOT
      fire either; it resolves via the existing zero-guards/zero-gaps
      `no_contract_derived` fallback instead (T11 item 4's zero-findings
      decision).
    """
    unknown_report = check_graph(
        _single_op_graph("definitely_fake_method_xyz", "LiquidHandler"), contracts_json
    )
    assert {f.reason for f in unknown_report.findings} == {"unsupported_tool"}

    outside_old_allowlist_report = check_graph(
        _single_op_graph("pick_up_tips96", "LiquidHandler"), contracts_json
    )
    assert "unsupported_tool" not in {f.reason for f in outside_old_allowlist_report.findings}

    zero_finding_report = check_graph(_single_op_graph("spin", "Centrifuge"), contracts_json)
    assert {f.reason for f in zero_finding_report.findings} == {"no_contract_derived"}


# ---------------------------------------------------------------------------
# AC-6.5 (D1) -- the ONE live SUPPORTED_TOOLS drift test post-consolidation.
# ---------------------------------------------------------------------------


def test_supported_tools_match_upstream() -> None:
    """`plr_sema.check.SUPPORTED_TOOLS` (the single in-package definition,
    T8 consolidation -- see `plr_sema/check/_supported_tools.py`) must be the
    SAME set as `training.verify.dispatcher.SUPPORTED_TOOLS` today -- a live
    drift test, not a copied constant re-asserted against itself.
    `src/plr_sema` cannot import `verify` (import-boundary test forbids it);
    this test file can, with both `<repo_root>/training` and
    `<repo_root>/coxswain/src` on `sys.path` first (`verify/__init__.py`
    eagerly imports `verify.checks`, which imports
    `coxswain.plr.intent_record`)."""
    training_path = str(REPO_ROOT / "training")
    coxswain_src_path = str(REPO_ROOT / "coxswain" / "src")
    for path in (coxswain_src_path, training_path):
        if path not in sys.path:
            sys.path.insert(0, path)

    try:
        import verify.dispatcher as upstream_dispatcher
    except ImportError as exc:
        pytest.skip(f"training/verify not importable: {exc}")
        return

    assert SUPPORTED_TOOLS == upstream_dispatcher.SUPPORTED_TOOLS, (
        f"plr_sema.check.SUPPORTED_TOOLS {sorted(SUPPORTED_TOOLS)} != "
        f"verify.dispatcher.SUPPORTED_TOOLS {sorted(upstream_dispatcher.SUPPORTED_TOOLS)}"
    )


# ---------------------------------------------------------------------------
# AC-6.6 (D15, moved from AC-3.4) -- full T8 pipeline round-trips to JSON.
# ---------------------------------------------------------------------------


def _plr_site_from_dict(d: dict | None) -> PlrSite | None:
    return None if d is None else PlrSite(file=d["file"], lineno=d["lineno"], qualname=d["qualname"])


def _git_state_from_dict(d: dict):
    from plr_sema._provenance.git_state import GitState

    return GitState(**d)


def _stamp_from_dict(d: dict):
    from plr_sema._provenance import SurveyStamp

    return SurveyStamp(
        plr=_git_state_from_dict(d["plr"]),
        praxis=_git_state_from_dict(d["praxis"]),
        pylabrobot_version=d["pylabrobot_version"],
        stamped_at=d["stamped_at"],
        schema_version=d["schema_version"],
    )


def _finding_from_dict(d: dict) -> Finding:
    return Finding(
        verdict=Verdict(d["verdict"]),
        operation_id=d["operation_id"],
        category=d["category"],
        plr_site=_plr_site_from_dict(d["plr_site"]),
        reason=d["reason"],
        detail=d["detail"],
        evidence=tuple(_plr_site_from_dict(s) for s in d["evidence"]),
    )


def _scope_from_dict(d: dict | None) -> "SoundnessScope | None":
    if d is None:
        return None
    return SoundnessScope(excludes_sites=tuple(_plr_site_from_dict(s) for s in d["excludes_sites"]))


def _report_from_dict(d: dict) -> AnalysisReport:
    return AnalysisReport(
        protocol_fqn=d["protocol_fqn"],
        verdict=Verdict(d["verdict"]),
        findings=tuple(_finding_from_dict(f) for f in d["findings"]),
        stamp=_stamp_from_dict(d["stamp"]),
        schema_version=d["schema_version"],
        scope=_scope_from_dict(d.get("scope")),
        # 260909 (spec §16.6, increment 7, T44, Q1): additive, `None` unless
        # `scope` produced one too.
        scope_verdict=Verdict(d["scope_verdict"]) if d.get("scope_verdict") is not None else None,
    )


def test_full_pipeline_report_round_trips_json(report: AnalysisReport) -> None:
    """AC-6.6 (D15, moved from AC-3.4): an `AnalysisReport` produced by
    running the FULL T8 pipeline (fixture graph JSON -> `check_graph` ->
    report) over the fixture protocol serializes to JSON and deserializes
    field-identically. AC-3.4 (`test_verdict.py`) already covers the
    narrower direct-construction form; this is the full-pipeline form T3
    alone could not exercise."""
    import dataclasses

    payload = json.loads(json.dumps(dataclasses.asdict(report)))
    rebuilt = _report_from_dict(payload)
    assert rebuilt == report


# ---------------------------------------------------------------------------
# §16.6, T44, Q1 -- the scoped joined verdict (AC-16.7)
# ---------------------------------------------------------------------------


def test_scope_verdict_equals_join_over_the_excluded_subset(report: AnalysisReport) -> None:
    """§16.6: `scope_verdict` is `None` iff `scope` is `None`; otherwise it
    is exactly `join()` -- the SAME function `verdict` itself is built
    from -- over the sub-multiset of `report.findings` whose `plr_site` is
    not in `report.scope.excludes_sites`. Re-derived independently here
    rather than trusting `_check`'s own computation. The fixture protocol
    (`pick_up_tips`/`aspirate`/`dispense`/`drop_tips`) is known (§16.6) to
    carry a tier-(iii) re-raise on every operation, so this also confirms
    `report.scope` is actually populated on this fixture -- the assertion
    is not vacuously true over an empty exclusion set."""
    from plr_sema.verdict import join

    assert report.scope is not None
    assert report.scope.excludes_sites
    expected = join(
        tuple(f for f in report.findings if f.plr_site not in report.scope.excludes_sites)
    )
    assert report.scope_verdict == expected
    # verdict itself (the UNSCOPED join) is untouched by scope_verdict's
    # existence.
    assert report.verdict == join(report.findings)


def test_scope_verdict_none_when_scope_none() -> None:
    """`scope_verdict` is `None` whenever `scope` is `None` -- exercised
    directly (not just via the fixture, which always populates `scope`)
    against `check_ir`'s own no-collector default."""
    # A bytecode with zero CALL instructions visits zero guards, so
    # `check_ir`'s own `excludes_sites` collector (never passed here, the
    # default) never matters -- this exercises the "`_check` never passed a
    # collector" half rather than the "collector came back empty" half,
    # which the fixture-based test above cannot reach (it always threads
    # one).
    bytecode = ir.lower_graph({"operations": []}, param_names={})
    from plr_sema.check import _check

    report = _check(bytecode, "empty.protocol", {"contracts": {}, "receiver_state": {}, "stamp": _minimal_stamp_dict()})
    assert report.scope is None
    assert report.scope_verdict is None


def _minimal_stamp_dict() -> dict:
    return {
        "plr": {"hash": "a" * 40, "branch": "main", "dirty": False},
        "praxis": {"hash": "b" * 40, "branch": "main", "dirty": False},
        "pylabrobot_version": "0.1.0",
        "stamped_at": "2026-09-09T00:00:00+00:00",
        "schema_version": 1,
    }


def test_check_call_site_calls_join_without_a_flag() -> None:
    """§16.6's normative box, AST-scanned: `join` is not modified, not
    overloaded and not called with a flag at the ONE `_check` call site
    that computes `scope_verdict`. Every `join(...)` call inside `_check`'s
    body takes exactly one positional argument and zero keyword arguments
    -- there is no boolean/scope parameter threaded into `join` itself."""
    tree = ast.parse(
        (PLR_SEMA_ROOT / "src" / "plr_sema" / "check" / "__init__.py").read_text(),
        filename="check/__init__.py",
    )
    check_fn = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_check"
    )
    join_calls = [
        node
        for node in ast.walk(check_fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "join"
    ]
    # Two calls: `verdict=join(findings)` and `scope_verdict`'s own
    # `join(tuple(...))` over the filtered sub-multiset.
    assert len(join_calls) == 2
    for call in join_calls:
        assert len(call.args) == 1
        assert not call.keywords


# ---------------------------------------------------------------------------
# AC-6.7 (D15, moved from AC-4.3) -- full pipeline + JsonlSink emission.
# ---------------------------------------------------------------------------


def test_full_pipeline_emits_stamped_jsonl(
    graph_json: str, contracts_json: str, tmp_path: Path
) -> None:
    """AC-6.7 (D15, moved from AC-4.3; round-4 remediation, M2/fix 17): with
    `JsonlSink` attached BEFORE the run, `check_graph` itself now emits
    every finding (§3.3:444's "internal_error ... always paired with a
    telemetry emit" used to be false of the code -- nothing under check/
    ever called plr_sema.telemetry.emit*; check_graph now does, for every
    reason, not just internal_error). This test therefore attaches the sink
    and calls `check_graph` directly -- it does NOT call `emit_finding`
    itself, unlike the pre-round-4 version, which emitted from the test and
    proved nothing about the pipeline's own emission behavior. Uses the
    `graph_json`/`contracts_json` fixtures rather than the module-scoped
    `report` fixture, since `report` may have already been built (and
    already emitted, against whatever sink was active then) by an earlier
    test in this module."""
    from plr_sema.telemetry import JsonlSink, set_sink

    sink_path = tmp_path / "events.jsonl"
    set_sink(JsonlSink(sink_path))
    try:
        check_graph(graph_json, contracts_json)
    finally:
        set_sink(None)

    lines = sink_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 1
    # Round-4 remediation (M8/fix 23): asserted against a FALSIFIABLE
    # identity -- the emitted stamp must equal the stamp
    # `derived_contracts.json` itself carries -- rather than a hardcoded
    # pin string that silently passes against an arbitrarily stale
    # artifact (the checker's own code version is unrecorded; `stamp` is
    # build-time-only provenance, reconstructed verbatim from the
    # contracts payload -- see AnalysisReport's docstring).
    expected_hash = json.loads(contracts_json)["stamp"]["plr"]["hash"]
    for line in lines:
        event = json.loads(line)
        assert event["stamp"]["plr"]["hash"] == expected_hash
    # The pin is still confirmed live for THIS checkout, as a secondary,
    # self-scoping sanity check (not the primary assertion above).
    assert expected_hash == _PLR_PIN_SHA


# ---------------------------------------------------------------------------
# Spec 260903 §12.3.4 -- OBLIGED(graph) at check_graph level: a proved-
# trip-0 region's body must never receive a Finding, and AC-6.4/AC-7.2
# amended must both hold over that exclusion.
# ---------------------------------------------------------------------------

DEAD_LOOP_BODY_FIXTURE = PLR_SEMA_ROOT / "tests" / "fixtures" / "dead_loop_body_graph.json"


def test_dead_loop_body_excluded_from_findings_and_obliged(contracts_json: str) -> None:
    graph_json = DEAD_LOOP_BODY_FIXTURE.read_text(encoding="utf-8")
    graph_payload = json.loads(graph_json)
    report = check_graph(graph_json, contracts_json)

    obliged = ir.obliged_operation_ids(graph_payload)
    finding_ids = {f.operation_id for f in report.findings}

    assert "op_3" not in finding_ids, "op_3 is the trip==0 loop's body -- never visited, never a Finding"
    assert "op_3" not in obliged, "OBLIGED(graph) must exclude the dead loop body"
    assert finding_ids == obliged, "AC-6.4 amended: {f.operation_id} == OBLIGED(graph)"
    assert len(report.findings) >= len(obliged), "AC-7.2 amended: len(findings) >= len(OBLIGED(graph))"
    assert finding_ids == {"op_1", "op_4"}


# ---------------------------------------------------------------------------
# Spec 260903 §13.1/§13.9, backlog #4881a -- AC-13.3/AC-13.4. The lid
# family is specified and NOT adopted: `_check_no_lid`'s two guards are
# already inlined (depth 1) into `LiquidHandler.aspirate`'s contract entry
# (they were there before this task; nothing in `plr_sema.derive`/
# `plr_sema.check` was changed to construct a lid Finding), and the
# checker's existing, guard-agnostic `guard_predicate_unparsed` emission
# (`plr_sema.check._finding_from_guard`) already treats BOTH uniformly as
# UNKNOWN -- this is a REGRESSION test that that stays true, most of all
# for the `:117` guard's `condition: null` (the landmine, §13.1.3's own
# disclosure): a future evaluator that read `null` as "raises
# unconditionally" would manufacture `WILL_FAIL` on every one of the six
# `LiquidHandler` methods `_check_no_lid` reaches, for programs that run
# clean.
# ---------------------------------------------------------------------------

LIDDED_PLATE_ASPIRATE_FIXTURE = PLR_SEMA_ROOT / "tests" / "fixtures" / "lidded_plate_aspirate_graph.json"

# The two `_check_no_lid` guard sites (§13.1.1): `:116` is the self-lidded
# raise (`condition == "lidded is resource"`), `:117` is the
# ancestor-lidded raise -- the `condition: null` landmine.
_LID_GUARD_LINENOS = (116, 117)


def test_lid_family_emits_nothing(contracts_json: str) -> None:
    """AC-13.4, first half: for `setup()` then `aspirate(use_channels=[0])`
    on a (nominally lidded, per the fixture's own name) plate, zero
    findings carry a `plr_site` at `liquid_handler.py:116`/`:117` with a
    verdict other than `Verdict.UNKNOWN` -- i.e. the lid family never
    promotes either guard to `SAFE` or `WILL_FAIL`. Also asserts no
    `Finding.reason` contains "lid" anywhere in `report.findings` --
    `REASON_VOCABULARY` has no lid-related member (§13.1's normative
    disposition; the row spends none), so this can never pass by
    coincidence of vocabulary shape.
    """
    graph_json = LIDDED_PLATE_ASPIRATE_FIXTURE.read_text(encoding="utf-8")
    report = check_graph(graph_json, contracts_json)

    assert len(report.findings) >= 1
    for finding in report.findings:
        assert "lid" not in finding.reason.lower(), (
            f"a lid-related reason was constructed: {finding.reason!r} (op {finding.operation_id})"
        )
        site = finding.plr_site
        if site is not None and site.file.endswith("liquid_handler.py") and site.lineno in _LID_GUARD_LINENOS:
            assert finding.verdict is Verdict.UNKNOWN, (
                f"a lid guard at liquid_handler.py:{site.lineno} was promoted to {finding.verdict!r}"
            )


def test_lid_family_findings_identical_to_graph_without_the_plate(contracts_json: str) -> None:
    """AC-13.4, corroborating: the wire format cannot represent a lid at
    all (§13.1.2/L3 -- `RESOURCE`'s only structural operand is
    `parents: tuple[str, ...]`, an upward, type-only chain with no
    children field). So mentioning the (nominally lidded) plate at all,
    versus not mentioning it, must be INVISIBLE to `check_graph` --
    stripping the plate resource and its `aspirate` argument reference
    from the fixture payload must not change a single emitted `Finding`.
    An implementation that somehow keyed a Finding off the plate's
    presence would fail this, even though nothing in §13.1 authorizes one
    to exist.
    """
    graph_json = LIDDED_PLATE_ASPIRATE_FIXTURE.read_text(encoding="utf-8")
    with_plate = json.loads(graph_json)
    without_plate = copy.deepcopy(with_plate)
    del without_plate["resources"]["plate"]
    del without_plate["operations"][1]["arguments"]["resource"]
    without_plate["resource_types"] = ["LiquidHandler"]

    report_with = check_graph(graph_json, contracts_json)
    report_without = check_graph(json.dumps(without_plate), contracts_json)

    assert report_with.findings == report_without.findings
    assert report_with.verdict == report_without.verdict


def test_lid_family_null_condition_guard_is_unknown_not_will_fail(contracts_json: str) -> None:
    """AC-13.4, second half -- the stub-defeating one: the Finding for the
    `:117` guard (whose derived `condition` is `null`) is
    `Verdict.UNKNOWN`, NOT `Verdict.WILL_FAIL`. `null` reads, on its face,
    as "raises unconditionally"; it is not -- `:117`'s raise is reachable
    only when the early `return` at `liquid_handler.py:113-114` did not
    fire, and the precondition survey's `scope_trail` does not model early
    returns (§13.1.3), so no evaluator today or in this fixture can
    construct that fact. An evaluator that treated a `null` condition as
    "always true" AND treated this inlined (depth-1) guard as reachable
    would emit `WILL_FAIL` here and fail this assertion.

    260904 (increment 6, T31): `reason` is now `"guard_env_dependent"`, not
    the pre-increment-6 blanket `"guard_predicate_unparsed"` -- `:117`'s
    predicate parses cleanly to `TRUE()` (`plr_sema.derive.predicate_ast
    .parse(None) == TRUE()`) and evaluates `T`, so `guard_predicate_unparsed`
    (§15.7 clause 1, "the grammar failed here") would be a FALSE statement
    about this guard. What blocks `WILL_FAIL` is E-UNCOND(4): `_check_no_lid`
    is a delegate, so this guard's `depth == 1`, and no guard at depth >= 1
    may emit `WILL_FAIL` this increment (its reachability from the entry
    point's own call site is not established) -- `guard_env_dependent` is
    exactly the reason §15.7 assigns to that give-up point.
    """
    graph_json = LIDDED_PLATE_ASPIRATE_FIXTURE.read_text(encoding="utf-8")
    report = check_graph(graph_json, contracts_json)

    null_condition_findings = [
        f
        for f in report.findings
        if f.plr_site is not None
        and f.plr_site.file.endswith("liquid_handler.py")
        and f.plr_site.lineno == 117
    ]
    assert len(null_condition_findings) == 1, (
        f"expected exactly one Finding for the :117 null-condition guard, got {null_condition_findings!r}"
    )
    finding = null_condition_findings[0]
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"
    assert finding.verdict is not Verdict.WILL_FAIL


# ---------------------------------------------------------------------------
# Spec 260903 §14 (`260903_plr-sema-volume-increment.md`), T26 (backlog
# #4959): the interval domain and its transfer functions (V0-V5), wired
# into `check_ir`/`check_graph`'s walk. AC-14.5/AC-14.6.
# ---------------------------------------------------------------------------

_REMOVE_LIQUID_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/resources/volume_tracker.py",
    lineno=92,
    qualname="VolumeTracker.remove_liquid",
)
_ADD_LIQUID_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/resources/volume_tracker.py",
    lineno=105,
    qualname="VolumeTracker.add_liquid",
)
_DOES_VOLUME_TRACKING_ENV = frozenset({"does_volume_tracking"})


def _volume_graph(name: str) -> str:
    return (PLR_SEMA_ROOT / "tests" / "fixtures" / f"{name}_graph.json").read_text(encoding="utf-8")


def _volume_check(name: str, contracts_json: str, *, env: frozenset[str] = frozenset()) -> AnalysisReport:
    return check_graph(_volume_graph(name), contracts_json, env=env)


def _site_findings(report: AnalysisReport, site: PlrSite, operation_id: str | None = None) -> list[Finding]:
    return [
        f
        for f in report.findings
        if f.plr_site == site and (operation_id is None or f.operation_id == operation_id)
    ]


def _no_volume_will_fail(report: AnalysisReport) -> bool:
    """`True` iff no finding sited in `volume_tracker.py` is `WILL_FAIL` --
    narrower than "no WILL_FAIL in the report", since several of these
    fixtures deliberately omit a `pick_up_tips` (AC-14.5(d)) or vary
    `use_channels` (AC-14.6's D2 sub-assertion), which the PRE-EXISTING tip
    family (not volume) correctly flags as its own, unrelated WILL_FAIL
    (e.g. `TipTracker.get_tip`, "dispense with no tip mounted") -- a real,
    correct finding this module must not suppress or be confused by.
    """
    return not any(
        f.verdict is Verdict.WILL_FAIL and f.plr_site is not None and f.plr_site.file.endswith("volume_tracker.py")
        for f in report.findings
    )


def test_ac_14_5_a_headline_tip_overdraw_will_fail_under_env(contracts_json: str) -> None:
    """AC-14.5(a): pick_up_tips ch0 / seeded well 100 / aspirate(vols=[50])
    / dispense(vols=[60]), under `env={"does_volume_tracking"}` -> exactly
    ONE `WILL_FAIL` finding in the whole report, sited at
    `PlrSite(volume_tracker.py, 92, VolumeTracker.remove_liquid)`. The
    report also carries the seed CALL's own `unresolved_delegate` finding
    (§14.8) and the well-side `volume_state_unknown` (the over-fill half,
    always ½, §14.2)."""
    report = _volume_check("volume_overdraw", contracts_json, env=_DOES_VOLUME_TRACKING_ENV)

    will_fail = [f for f in report.findings if f.verdict is Verdict.WILL_FAIL]
    assert len(will_fail) == 1, f"expected exactly one WILL_FAIL, got {will_fail!r}"
    (finding,) = will_fail
    assert finding.plr_site == _REMOVE_LIQUID_SITE
    assert finding.category == "precondition_state"
    assert report.verdict is Verdict.WILL_FAIL

    seed_findings = [f for f in report.findings if f.operation_id == "op_2"]
    assert any(f.reason == "unresolved_delegate" for f in seed_findings), (
        "the seed CALL's own unresolved_delegate finding (§14.8) is missing"
    )
    well_side = _site_findings(report, _ADD_LIQUID_SITE, operation_id="op_4")
    assert well_side and all(f.verdict is Verdict.UNKNOWN and f.reason == "volume_state_unknown" for f in well_side)


def test_ac_14_7_headline_tip_overdraw_unasserted_by_default(contracts_json: str) -> None:
    """AC-14.7: the SAME headline fixture, under the DEFAULT `env ==
    frozenset()`, yields `UNKNOWN`/`volume_tracking_unasserted` at the same
    site -- never `WILL_FAIL` -- while the well's own aspirate guard's
    `SAFE` (below) is unchanged by `env` in either direction. Also pins
    `check_graph`'s two-positional-argument call form (no `env=`) to the
    identical default-`env` result."""
    report_kwarg = _volume_check("volume_overdraw", contracts_json)
    report_positional = check_graph(_volume_graph("volume_overdraw"), contracts_json)
    assert report_kwarg.findings == report_positional.findings

    dispense_tip_side = _site_findings(report_kwarg, _REMOVE_LIQUID_SITE, operation_id="op_5")
    assert len(dispense_tip_side) == 1
    (finding,) = dispense_tip_side
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "volume_tracking_unasserted"
    assert not any(f.verdict is Verdict.WILL_FAIL for f in report_kwarg.findings)

    aspirate_well_side = _site_findings(report_kwarg, _REMOVE_LIQUID_SITE, operation_id="op_4")
    assert len(aspirate_well_side) == 1
    assert aspirate_well_side[0].verdict is Verdict.SAFE


def test_ac_14_5_b_safe_tip_dispense_under_capacity(contracts_json: str) -> None:
    """AC-14.5(b): the same graph with `dispense(vols=[40])` -> a `SAFE`
    finding at the same tip-side site, and the well's own aspirate guard
    (`op_4`) is `SAFE` too -- the well half this increment does ship."""
    report = _volume_check("volume_safe", contracts_json, env=_DOES_VOLUME_TRACKING_ENV)

    tip_side = _site_findings(report, _REMOVE_LIQUID_SITE, operation_id="op_5")
    assert len(tip_side) == 1 and tip_side[0].verdict is Verdict.SAFE

    well_side = _site_findings(report, _REMOVE_LIQUID_SITE, operation_id="op_4")
    assert len(well_side) == 1 and well_side[0].verdict is Verdict.SAFE

    assert not any(f.verdict is Verdict.WILL_FAIL for f in report.findings)


def test_ac_14_5_c_top_amount_yields_unknown(contracts_json: str) -> None:
    """AC-14.5(c): the same graph with the dispense's own `vols` lowering
    to Top (an unresolvable call expression) -> `UNKNOWN` with reason
    `volume_state_unknown` at the tip-side site -- V0 does not apply
    (amounts unresolved), V3 widens."""
    report = _volume_check("volume_top", contracts_json, env=_DOES_VOLUME_TRACKING_ENV)

    tip_side = _site_findings(report, _REMOVE_LIQUID_SITE, operation_id="op_5")
    assert len(tip_side) == 1
    assert tip_side[0].verdict is Verdict.UNKNOWN
    assert tip_side[0].reason == "volume_state_unknown"
    assert not any(f.verdict is Verdict.WILL_FAIL for f in report.findings)


def test_ac_14_5_d_overfill_and_tip_cell_are_always_unknown(contracts_json: str) -> None:
    """AC-14.5(d), the declining half: `dispense(vols=[10_000])` into a
    seeded well, with NO preceding `pick_up_tips` at all -> `UNKNOWN` with
    reason `volume_state_unknown` at BOTH the well-side (`add_liquid`,
    over-fill -- capacity is Top, §14.2) and the tip-side (`remove_liquid`
    -- the channel's `TipState` is not `HAS_TIP`, A-TIP-CELL) sites, under
    EITHER `env` -- never `WILL_FAIL` for either."""
    for env in (frozenset(), _DOES_VOLUME_TRACKING_ENV):
        report = _volume_check("volume_overfill", contracts_json, env=env)
        well_side = _site_findings(report, _ADD_LIQUID_SITE, operation_id="op_3")
        tip_side = _site_findings(report, _REMOVE_LIQUID_SITE, operation_id="op_3")
        assert len(well_side) == 1 and well_side[0].reason == "volume_state_unknown"
        assert len(tip_side) == 1 and tip_side[0].reason == "volume_state_unknown"
        assert _no_volume_will_fail(report)


def test_ac_14_5_e_retip_dirty_tip_never_safe(contracts_json: str) -> None:
    """AC-14.5(e), the round-1 O4 counterexample: `pick_up_tips` /
    `aspirate(50)` / `drop_tips(allow_nonzero_volume=True)` (at a tip whose
    interval is NOT provably `[0, 0]`) / `pick_up_tips` / `dispense(50)` ->
    `UNKNOWN` with reason `volume_state_unknown` at the final dispense's
    tip-side site -- NEVER `SAFE`. A `[0, 0]`-always implementation (the
    unsound simple rule V5 replaces) would get this wrong."""
    report = _volume_check("volume_retip", contracts_json, env=_DOES_VOLUME_TRACKING_ENV)

    final_dispense = _site_findings(report, _REMOVE_LIQUID_SITE, operation_id="op_7")
    assert len(final_dispense) == 1
    assert final_dispense[0].verdict is Verdict.UNKNOWN
    assert final_dispense[0].reason == "volume_state_unknown"
    assert final_dispense[0].verdict is not Verdict.SAFE


def test_ac_14_5_e_retip_provably_empty_drop_keeps_precision(contracts_json: str) -> None:
    """AC-14.5(e), the OTHER half: "the same sequence with the drop taken
    at a provably empty tip leaves `tips_dirty` false" -- constructed here
    by inserting a `dispense(50)` immediately before the drop (emptying the
    tip exactly, `[0, 0]`) and replacing the tail with an
    `aspirate(30)`/`dispense(20)` pair. If `tips_dirty` had (incorrectly)
    been set anyway, the second `pick_up_tips` would yield Top and this
    tail's final `dispense(20)` would be `UNKNOWN`, not the `SAFE` a
    provably-empty retip is entitled to.
    """
    graph = json.loads(_volume_graph("volume_retip"))
    ops = graph["operations"]
    by_id = {o["id"]: o for o in ops}

    empty_out = copy.deepcopy(by_id["op_7"])
    empty_out["id"] = "op_4b"
    ops.insert(ops.index(by_id["op_5"]), empty_out)
    graph["execution_order"].insert(graph["execution_order"].index("op_5"), "op_4b")

    by_id["op_7"]["method_name"] = "aspirate"
    by_id["op_7"]["arguments"] = {"resources": "[well]", "vols": "[30]", "use_channels": "[0]"}
    tail = copy.deepcopy(by_id["op_7"])
    tail["id"] = "op_8"
    tail["method_name"] = "dispense"
    tail["arguments"] = {"resources": "[well]", "vols": "[20]", "use_channels": "[0]"}
    ops.append(tail)
    graph["execution_order"].append("op_8")

    report = check_graph(json.dumps(graph), contracts_json, env=_DOES_VOLUME_TRACKING_ENV)

    final_dispense = _site_findings(report, _REMOVE_LIQUID_SITE, operation_id="op_8")
    assert len(final_dispense) == 1
    assert final_dispense[0].verdict is Verdict.SAFE, (
        f"expected SAFE (tips_dirty must stay false after a provably-empty drop), got {final_dispense[0]!r}"
    )


VOLUME_WHILE_FIXTURE = PLR_SEMA_ROOT / "tests" / "fixtures" / "volume_while_graph.json"


def test_ac_14_5_while_loop_converges_and_widens_to_top(contracts_json: str) -> None:
    """AC-14.5's sixth fixture (V4): a `while`-shaped (`trip == null`)
    region whose body dispenses a literal volume repeatedly. `check_ir`
    (via `check_graph`) must converge within the shared `K`-pass cap
    without raising -- a plain, unguarded fixpoint join over the interval
    domain (infinite height) would not be guaranteed to stabilize in any
    fixed number of passes, which is exactly why V4 widens on entry instead
    of iterating to a real fixpoint for volume cells. The probe call AFTER
    the region's `END` requests an enormous amount (999,999); if the tip
    cell had kept ANY finite upper bound from inside the loop, so large a
    request would be decidable (and, under the hypothesis env, WILL_FAIL);
    observing `UNKNOWN`/`volume_state_unknown` instead is the direct,
    externally-observable proof that every cell mentioned in the region is
    Top after the region's END.
    """
    report = check_graph(VOLUME_WHILE_FIXTURE.read_text(encoding="utf-8"), contracts_json, env=_DOES_VOLUME_TRACKING_ENV)

    post_loop_probe = _site_findings(report, _REMOVE_LIQUID_SITE, operation_id="op_6")
    assert len(post_loop_probe) == 1
    assert post_loop_probe[0].verdict is Verdict.UNKNOWN
    assert post_loop_probe[0].reason == "volume_state_unknown"
    assert not any(f.verdict is Verdict.WILL_FAIL for f in report.findings)


# ---------------------------------------------------------------------------
# AC-14.6: V2 threads pair-by-pair, not against one shared snapshot --
# static only, against a SYNTHETIC contract table whose bridged guard has
# no `is_disabled` conjunct (round-1 O14; no real `aspirate` guard is
# unconditional, since the well-side guard always carries the `is_disabled`
# entry -- §14.0.2's disposition table).
# ---------------------------------------------------------------------------

VOLUME_TWO_CHANNEL_FIXTURE = PLR_SEMA_ROOT / "tests" / "fixtures" / "volume_two_channel_one_well_graph.json"


def _synthetic_two_channel_contracts_json(contracts_json: str) -> str:
    payload = json.loads(contracts_json)
    (guard,) = [
        dict(g) for g in payload["contracts"]["LiquidHandler.aspirate"]["volume_guards"] if g["cell_param"] == "resources"
    ]
    guard["caller_scope"] = ["if does_volume_tracking()", "for op in aspirations"]
    payload["contracts"]["LiquidHandler.aspirate"] = dict(payload["contracts"]["LiquidHandler.aspirate"])
    payload["contracts"]["LiquidHandler.aspirate"]["volume_guards"] = [guard]
    return json.dumps(payload)


def test_ac_14_6_two_channel_one_well_threads_sequentially(contracts_json: str) -> None:
    """AC-14.6, first half: a well seeded to 100, `aspirate(resources=[well,
    well], vols=[60, 60], use_channels=[0, 1])` -> `SAFE` for the FIRST
    pair and `WILL_FAIL` for the SECOND, both sited at
    `VolumeTracker.remove_liquid`, and no `SAFE` for the second. An
    implementation that evaluated both guards against one shared
    pre-operation snapshot would emit two `SAFE`s instead."""
    synthetic_contracts_json = _synthetic_two_channel_contracts_json(contracts_json)
    report = check_graph(
        VOLUME_TWO_CHANNEL_FIXTURE.read_text(encoding="utf-8"), synthetic_contracts_json, env=_DOES_VOLUME_TRACKING_ENV
    )

    pair_findings = _site_findings(report, _REMOVE_LIQUID_SITE, operation_id="op_3")
    assert [f.verdict for f in pair_findings] == [Verdict.SAFE, Verdict.WILL_FAIL], (
        f"expected [SAFE, WILL_FAIL] in pair order, got {[f.verdict for f in pair_findings]!r}"
    )


def test_ac_14_6_use_channels_length_mismatch_widens(contracts_json: str) -> None:
    """AC-14.6, second sub-assertion (round-1 D2): the SAME fixture with
    `use_channels=[0, 1, 2]` (disagreeing with the two-element pair list)
    widens to Top and emits no definite verdict for either pair -- V0's
    clause (c)."""
    synthetic_contracts_json = _synthetic_two_channel_contracts_json(contracts_json)
    graph = json.loads(VOLUME_TWO_CHANNEL_FIXTURE.read_text(encoding="utf-8"))
    for operation in graph["operations"]:
        if operation["method_name"] == "aspirate":
            operation["arguments"]["use_channels"] = "[0, 1, 2]"

    report = check_graph(json.dumps(graph), synthetic_contracts_json, env=_DOES_VOLUME_TRACKING_ENV)

    pair_findings = _site_findings(report, _REMOVE_LIQUID_SITE, operation_id="op_3")
    assert len(pair_findings) == 1
    assert pair_findings[0].verdict is Verdict.UNKNOWN
    assert pair_findings[0].reason == "volume_state_unknown"
    assert _no_volume_will_fail(report)


# ---------------------------------------------------------------------------
# AC-16.4 (spec 260909 §16.4, D1, T42): the depth-1 `WILL_FAIL` lift, tested
# against a SYNTHETIC guard swapped into the real `pick_up_tips` contract's
# `:409` slot -- the SAME `_synthetic_*_contracts_json` pattern
# `test_ac_14_6_*` already uses above. A synthetic predicate is necessary
# rather than the real `_make_sure_channels_exist` guard: its own emptiness
# test bottoms out in `c not in self.head`, a MEMBERSHIP `Cmp` that G8(2)
# evaluates 1/2 UNCONDITIONALLY until T43 lands `E-ENV`'s R-HEAD rule, so
# the real site cannot reach `fires is True` at this pin -- exactly why
# spec's own §16.4 box states this increment adds no WILL_FAIL population
# at all without a synthetic exerciser. The synthetic predicate references
# TWO of D's own parameters -- `channels` (mapped, via the REAL
# `caller_args` this contract's own `pick_up_tips`/`_make_sure_channels_
# exist` pair derives, to `Var("use_channels")`) and `flag` (mapped to a
# bare `Lit(True)`, so it resolves with no dependency on `K`'s own state at
# all) -- so perturbation 5 ("one free name resolving to Top") has a second
# name to unmap without collapsing the whole guard to Opaque.
# ---------------------------------------------------------------------------

_T42_GUARD_PREDICATE = {
    "node": "And",
    "predicates": [
        {
            "node": "Cmp",
            "left": {"node": "Len", "term": {"node": "Var", "name": "channels"}},
            "op": ">",
            "right": {"node": "Lit", "value": 0},
        },
        {"node": "Is", "term": {"node": "Var", "name": "flag"}, "negated": True},
    ],
}


def _pick_up_tips_use_channels_graph(use_channels_literal: str) -> str:
    return json.dumps(
        {
            "protocol_fqn": "test.t42_depth1_lift",
            "operations": [
                {
                    "id": "op_1",
                    "method_name": "pick_up_tips",
                    "receiver_variable": "lh",
                    "receiver_type": "LiquidHandler",
                    "arguments": {"use_channels": use_channels_literal},
                }
            ],
            "resources": {},
        }
    )


def _t42_synthetic_contracts_json(contracts_json: str, guard_overrides: dict) -> str:
    """Real `contracts_json`, with `LiquidHandler.pick_up_tips`'s own
    `guards` list replaced by ONE synthetic guard -- the real `:409` site
    (file/lineno/qualname) so the finding is still `plr_site`-addressable,
    but a hand-built `predicate`/`caller_args` triple so the fixture is
    deterministic and self-contained (never depends on `self.head`)."""
    payload = json.loads(contracts_json)
    real_contract = payload["contracts"]["LiquidHandler.pick_up_tips"]
    (real_409,) = [g for g in real_contract["guards"] if g["site"]["lineno"] == 409]
    guard = {
        "condition": "len(channels) > 0 and flag is not None",
        "predicate": _T42_GUARD_PREDICATE,
        "scope_trail": [],
        "raises": "ValueError",
        "kind": "raise_guard",
        "free_vars": ["channels", "flag"],
        "site": real_409["site"],
        "depth": 1,
        "bindings": [],
        "reachability_clear": True,
        "caller_args": {"channels": {"node": "Var", "name": "use_channels"}, "flag": {"node": "Lit", "value": True}},
        "caller_reachability_clear": True,
        "caller_scope_trail": [],
    }
    guard.update(guard_overrides)
    new_contract = dict(real_contract)
    new_contract["guards"] = [guard]
    payload["contracts"] = dict(payload["contracts"])
    payload["contracts"]["LiquidHandler.pick_up_tips"] = new_contract
    return json.dumps(payload)


_T42_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
    lineno=409,
    qualname="LiquidHandler._make_sure_channels_exist",
)


def _t42_report(contracts_json: str, guard_overrides: dict, *, use_channels: str = "[0, 1]") -> AnalysisReport:
    synthetic = _t42_synthetic_contracts_json(contracts_json, guard_overrides)
    return check_graph(_pick_up_tips_use_channels_graph(use_channels), synthetic)


def test_ac_16_4_depth1_will_fail_under_all_three_preconditions(contracts_json: str) -> None:
    """All three D1 preconditions hold (`reachability_clear`,
    `caller_reachability_clear` + a satisfied `caller_scope_trail`, and a
    total map -- implied here by `fires is True`) -> `WILL_FAIL` with
    `category == "precondition_state"`."""
    report = _t42_report(contracts_json, {})
    findings = _site_findings(report, _T42_SITE, operation_id="op_1")
    assert len(findings) == 1
    (finding,) = findings
    assert finding.verdict is Verdict.WILL_FAIL
    assert finding.category == "precondition_state"


def test_ac_16_4_reachability_clear_false_blocks(contracts_json: str) -> None:
    """Perturbation 1: the delegate's own body is not clear ->
    `UNKNOWN`/`guard_env_dependent`, never `WILL_FAIL`."""
    report = _t42_report(contracts_json, {"reachability_clear": False})
    (finding,) = _site_findings(report, _T42_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"


def test_ac_16_4_caller_reachability_clear_false_blocks(contracts_json: str) -> None:
    """Perturbation 2: the call site is not reached (`caller_reachability_
    clear is False`) -> blocked."""
    report = _t42_report(contracts_json, {"caller_reachability_clear": False})
    (finding,) = _site_findings(report, _T42_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"


def test_ac_16_4_caller_reachability_clear_absent_blocks(contracts_json: str) -> None:
    """Perturbation 3: `caller_reachability_clear` is ABSENT (=> `None` =>
    blocked), the stub-defeating half distinguishing `is False` from
    `is None` -- an implementation checking only the former would pass
    perturbation 2 and fail this one."""
    report = _t42_report(contracts_json, {"caller_reachability_clear": None})
    (finding,) = _site_findings(report, _T42_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"


def test_ac_16_4_unsatisfied_caller_scope_trail_entry_blocks(contracts_json: str) -> None:
    """Perturbation 4: an unsatisfied `caller_scope_trail` entry (an `if
    <unhypothesised-name>()` with the default empty `env`) -> blocked."""
    report = _t42_report(contracts_json, {"caller_scope_trail": ["if some_undeclared_flag()"]})
    (finding,) = _site_findings(report, _T42_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"


def test_ac_16_4_one_free_name_resolving_to_top_blocks(contracts_json: str) -> None:
    """Perturbation 5: `flag` loses its `caller_args` entry -> resolves to
    Top with `origin == "env"` -> the predicate can no longer decide `T`,
    landing at the `guard_env_dependent` catch-all (not `guard_operand_
    unknown`, since an "env"-origin Top is precisely what AC-16.3(b) names
    as the OTHER class)."""
    report = _t42_report(
        contracts_json, {"caller_args": {"channels": {"node": "Var", "name": "use_channels"}}}
    )
    (finding,) = _site_findings(report, _T42_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"


def test_ac_16_4_depth_two_still_forbidden_unconditionally(contracts_json: str) -> None:
    """The sixth fixture: `depth == 2` stays forbidden UNCONDITIONALLY,
    even with every other field left at its all-preconditions-satisfied
    value and an unconditionally-true predicate (`TRUE()`, so `fires is
    True` regardless of any resolution -- depth >= 1 already blocks every
    name from resolving via `caller_args` except at depth == 1
    specifically, so a depth-2 guard needs a vacuous predicate to even
    reach `guard_is_unconditional` at all)."""
    report = _t42_report(
        contracts_json,
        {"predicate": {"node": "TRUE"}, "depth": 2},
    )
    (finding,) = _site_findings(report, _T42_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"


def test_ac_16_3_b_caller_args_top_yields_operand_unknown_not_env_dependent(contracts_json: str) -> None:
    """AC-16.3(b) / C9's origin clause, the FIRST half: a `caller_args`-
    resolved name whose caller-side `Term` itself resolves to Top yields
    `guard_operand_unknown` -- NOT `guard_env_dependent` (that catch-all is
    for a name with NO `caller_args` entry at all, AC-16.3(b)'s second
    half / `test_ac_16_4_one_free_name_resolving_to_top_blocks` above). A
    single-free-var predicate over `channels`, mapped to `Var("use_channels")`,
    with NEITHER `use_channels` NOR `tip_spots` (the P3a default-arity
    fallback) supplied by the operation -- `channels_for_call` returns
    `None`, so the recursive K-context resolution itself lands on Top, but
    `origin` stays `"operand"` (C9: unconditional, regardless of whether
    the resolved value is concrete or Top)."""
    report = _t42_report(
        contracts_json,
        {
            "predicate": {
                "node": "Cmp",
                "left": {"node": "Len", "term": {"node": "Var", "name": "channels"}},
                "op": ">",
                "right": {"node": "Lit", "value": 0},
            },
            "free_vars": ["channels"],
            "caller_args": {"channels": {"node": "Var", "name": "use_channels"}},
        },
        use_channels="None",
    )
    (finding,) = _site_findings(report, _T42_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_operand_unknown"


# ---------------------------------------------------------------------------
# AC-16.5/AC-16.6 (spec 260909 §16.5, T43): `E-ENV` resolution -- R-HEAD,
# R-ATTR, R-CONST, the reopened membership case, and Q-MONO. The `:409`/
# `:514` tests below exercise the REAL, un-modified `pick_up_tips` contract
# end to end -- exactly the site the T42 comment above (`_T42_GUARD_PREDICATE`'s
# own docstring) names as unreachable until this row lands.
# ---------------------------------------------------------------------------

_T43_HEAD_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
    lineno=409,
    qualname="LiquidHandler._make_sure_channels_exist",
)
_T43_CONST_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
    lineno=514,
    qualname="LiquidHandler.pick_up_tips",
)


def _t43_obs_env(*, backend_class: str = "LiquidHandlerChatterboxBackend", num_channels: int = 8, head_channels=(0, 1, 2, 3, 4, 5, 6, 7)) -> "frozenset[str]":
    return frozenset(
        {
            f'obs:backend_class="{backend_class}"',
            f"obs:num_channels={num_channels}",
            f"obs:head_channels={list(head_channels)}".replace(" ", ""),
        }
    )


def test_ac_16_5_16_6_head_and_const_sites_flip_safe_under_observation(contracts_json: str) -> None:
    """The real `:409`/`:514` guards, unmodified -- both `UNKNOWN` before
    T43 (the T42 comment's own claim), both `SAFE` once R-HEAD/§16.5.4's
    membership reopening (`:409`) and R-CONST/Q-MONO (`:514`) resolve the
    observation. `:409` is reached through the shipped `len(Filtered) == 0`
    alpha idiom end to end -- no hand-built quantifier node (AC-16.6's
    stub-defeating half)."""
    report = check_graph(_pick_up_tips_use_channels_graph("[0, 1]"), contracts_json, env=_t43_obs_env())
    (head_finding,) = _site_findings(report, _T43_HEAD_SITE, operation_id="op_1")
    assert head_finding.verdict is Verdict.SAFE
    (const_finding,) = _site_findings(report, _T43_CONST_SITE, operation_id="op_1")
    assert const_finding.verdict is Verdict.SAFE


def test_ac_16_5_no_observation_stays_env_dependent(contracts_json: str) -> None:
    """§16.2.3's fail-closed default, restated for T43: with no `obs:`
    member in `env`, both sites stay exactly where increment 6 left them."""
    report = check_graph(_pick_up_tips_use_channels_graph("[0, 1]"), contracts_json)
    (head_finding,) = _site_findings(report, _T43_HEAD_SITE, operation_id="op_1")
    assert head_finding.verdict is Verdict.UNKNOWN
    assert head_finding.reason == "guard_env_dependent"
    (const_finding,) = _site_findings(report, _T43_CONST_SITE, operation_id="op_1")
    assert const_finding.verdict is Verdict.UNKNOWN


def test_ac_16_5_partial_observation_declines(contracts_json: str) -> None:
    """R-HEAD's own decline clause (§16.5.1): `backend_class` present but
    `head_channels` absent still declines to ⊤ -- a partial observation is
    refused wholesale, not read as \"no information about this one field\"."""
    partial_env = frozenset({'obs:backend_class="LiquidHandlerChatterboxBackend"'})
    report = check_graph(_pick_up_tips_use_channels_graph("[0, 1]"), contracts_json, env=partial_env)
    (head_finding,) = _site_findings(report, _T43_HEAD_SITE, operation_id="op_1")
    assert head_finding.verdict is Verdict.UNKNOWN
    assert head_finding.reason == "guard_env_dependent"


def test_ac_16_5_16_6_channel_outside_head_will_fail_at_head_site_const_site_unaffected(contracts_json: str) -> None:
    """The false-positive direction, checked positively: a requested
    channel NOT in `head_channels` makes `:409`'s membership existential
    find a genuine invalid channel -> `WILL_FAIL`, never a silently-passing
    `SAFE` (the `ir.Seq`-is-a-lower-bound rule made checkable the OTHER
    way). `:514` is unaffected -- R-CONST's argument-independence means the
    channel choice never enters its own resolution at all."""
    env = _t43_obs_env(head_channels=(0, 1, 2, 3))
    report = check_graph(_pick_up_tips_use_channels_graph("[5]"), contracts_json, env=env)
    (head_finding,) = _site_findings(report, _T43_HEAD_SITE, operation_id="op_1")
    assert head_finding.verdict is Verdict.WILL_FAIL
    (const_finding,) = _site_findings(report, _T43_CONST_SITE, operation_id="op_1")
    assert const_finding.verdict is Verdict.SAFE


def test_ac_16_5_const_declines_for_unobserved_backend_class(contracts_json: str) -> None:
    """R-CONST's own decline clause (§16.5.3): a `backend_class` with no
    row in the derived surface (or no `constant_return` on its row) means
    the lookup `f\"{backend_class}.{method}\"` misses and R-CONST declines
    to ⊤ -- never fabricates a value for an unobserved/unknown backend."""
    env = _t43_obs_env(backend_class="SomeUnknownBackend")
    report = check_graph(_pick_up_tips_use_channels_graph("[0, 1]"), contracts_json, env=env)
    (const_finding,) = _site_findings(report, _T43_CONST_SITE, operation_id="op_1")
    assert const_finding.verdict is Verdict.UNKNOWN


# ---------------------------------------------------------------------------
# R-ATTR and Q-MONO, exercised via a SYNTHETIC guard swapped into the real
# `:514` site slot (same `_t42_synthetic_contracts_json` pattern) -- R-ATTR
# decides nothing on the real corpus (§16.5.2's own box; `n_resolved_by_rule`
# for it is asserted 0 there) and Q-MONO's two VACUITY cells need a body
# that never depends on any real operand to isolate them from R-CONST.
# ---------------------------------------------------------------------------


def _t43_synthetic_predicate_report(contracts_json: str, predicate: dict, *, env: "frozenset[str]" = frozenset()) -> AnalysisReport:
    payload = json.loads(contracts_json)
    real_contract = payload["contracts"]["LiquidHandler.pick_up_tips"]
    (real_514,) = [g for g in real_contract["guards"] if g["site"]["lineno"] == 514]
    guard = {
        "condition": "synthetic T43 probe",
        "predicate": predicate,
        "scope_trail": [],
        "raises": "RuntimeError",
        "kind": "raise_guard",
        "free_vars": [],
        "site": real_514["site"],
        "depth": 0,
        "bindings": [],
        "reachability_clear": True,
    }
    new_contract = dict(real_contract)
    new_contract["guards"] = [guard]
    payload["contracts"] = dict(payload["contracts"])
    payload["contracts"]["LiquidHandler.pick_up_tips"] = new_contract
    synthetic = json.dumps(payload)
    return check_graph(_pick_up_tips_use_channels_graph("[0, 1]"), synthetic, env=env)


def test_ac_16_5_r_attr_resolves_num_channels_positive_and_negative(contracts_json: str) -> None:
    """R-ATTR (§16.5.2): `self.backend.num_channels` resolves to the
    observation's `Lit`, whose Kleene truth decides the guard; any OTHER
    attribute name stays ⊤ regardless of the observation (\"every other `a`
    resolves ⊤\")."""
    num_channels_predicate = {"node": "EnvRef", "path": ["self", "backend", "num_channels"], "args": None}
    report_truthy = _t43_synthetic_predicate_report(contracts_json, num_channels_predicate, env=_t43_obs_env(num_channels=8))
    (finding,) = _site_findings(report_truthy, _T43_CONST_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.WILL_FAIL  # 8 is truthy -> the guard fires.

    report_falsy = _t43_synthetic_predicate_report(contracts_json, num_channels_predicate, env=_t43_obs_env(num_channels=0))
    (finding,) = _site_findings(report_falsy, _T43_CONST_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.SAFE  # 0 is falsy -> the guard does not fire.

    other_attr_predicate = {"node": "EnvRef", "path": ["self", "backend", "some_other_attr"], "args": None}
    report_other = _t43_synthetic_predicate_report(contracts_json, other_attr_predicate, env=_t43_obs_env())
    (finding,) = _site_findings(report_other, _T43_CONST_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN


_UNRESOLVED_SEQ = {"node": "Var", "name": "some_unresolved_local"}
_DEFINITE_FALSE_BODY = {"node": "Is", "term": {"node": "Lit", "value": None}, "negated": True}
_DEFINITE_TRUE_BODY = {"node": "Is", "term": {"node": "Lit", "value": None}, "negated": False}


def test_ac_16_6_qmono_vacuity_cells_stay_half(contracts_json: str) -> None:
    """Q-MONO's two VACUITY cells (§16.5.5): `AllOf(⊤, F)` and `AnyOf(⊤,
    T)` are the two cells the empty sequence FALSIFIES, so an unknown
    length must not decide them -- asserted ½ (`UNKNOWN`/`guard_env_
    dependent`), never `F`/`T`, the stub-defeating half distinguishing Q-
    MONO from a blanket \"a ⊤ seq with a definite body always decides\" bug."""
    allof_f = {"node": "AllOf", "seq": _UNRESOLVED_SEQ, "predicate": _DEFINITE_FALSE_BODY}
    report = _t43_synthetic_predicate_report(contracts_json, allof_f)
    (finding,) = _site_findings(report, _T43_CONST_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"

    anyof_t = {"node": "AnyOf", "seq": _UNRESOLVED_SEQ, "predicate": _DEFINITE_TRUE_BODY}
    report = _t43_synthetic_predicate_report(contracts_json, anyof_t)
    (finding,) = _site_findings(report, _T43_CONST_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"


def test_ac_16_6_qmono_decided_cells(contracts_json: str) -> None:
    """Q-MONO's two DECIDED cells, both directions: `AllOf(⊤, T)` (the real
    `:514` shape, covered end to end above) and, here, `AnyOf(⊤, F)` --
    both are the cells the empty sequence ALSO satisfies, so an unknown
    length cannot falsify them."""
    anyof_f = {"node": "AnyOf", "seq": _UNRESOLVED_SEQ, "predicate": _DEFINITE_FALSE_BODY}
    report = _t43_synthetic_predicate_report(contracts_json, anyof_f)
    (finding,) = _site_findings(report, _T43_CONST_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.SAFE  # AnyOf + F body decides False -> guard never fires.

    allof_t = {"node": "AllOf", "seq": _UNRESOLVED_SEQ, "predicate": _DEFINITE_TRUE_BODY}
    report = _t43_synthetic_predicate_report(contracts_json, allof_t)
    (finding,) = _site_findings(report, _T43_CONST_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.WILL_FAIL  # AllOf + T body decides True -> the guard fires.


def test_ac_16_6_membership_against_general_seq_stays_half_not_true(contracts_json: str) -> None:
    """The `ir.Seq`-is-a-lower-bound rule (§16.5.4(ii)), made checkable the
    OTHER way: a `not in` against a `Var` resolving to an ORDINARY `ir.Seq`
    (not an R-HEAD-shaped `EnvRef`) is ½, asserted NOT `T` -- a general
    `Seq` never decides a membership `Cmp` to `T`, even when the value is
    concretely absent from it."""
    predicate = {
        "node": "Cmp",
        "left": {"node": "Lit", "value": 99},
        "op": "not in",
        "right": {"node": "Var", "name": "some_kwarg_seq"},
    }
    payload = json.loads(contracts_json)
    real_contract = payload["contracts"]["LiquidHandler.pick_up_tips"]
    (real_514,) = [g for g in real_contract["guards"] if g["site"]["lineno"] == 514]
    guard = {
        "condition": "synthetic T43 membership probe",
        "predicate": predicate,
        "scope_trail": [],
        "raises": "RuntimeError",
        "kind": "raise_guard",
        "free_vars": ["some_kwarg_seq"],
        "site": real_514["site"],
        "depth": 0,
        "bindings": [],
        "reachability_clear": True,
    }
    new_contract = dict(real_contract)
    new_contract["guards"] = [guard]
    payload["contracts"] = dict(payload["contracts"])
    payload["contracts"]["LiquidHandler.pick_up_tips"] = new_contract
    synthetic = json.dumps(payload)
    graph = json.dumps(
        {
            "protocol_fqn": "test.t43_membership_probe",
            "operations": [
                {
                    "id": "op_1",
                    "method_name": "pick_up_tips",
                    "receiver_variable": "lh",
                    "receiver_type": "LiquidHandler",
                    "arguments": {"some_kwarg_seq": "[1, 2, 3]"},
                }
            ],
            "resources": {},
        }
    )
    report = check_graph(graph, synthetic, env=_t43_obs_env())
    (finding,) = _site_findings(report, _T43_CONST_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"


# ---------------------------------------------------------------------------
# AC-16.13 (spec 260909 §16.1.3/§16.15 D6, T48, backlog #5026): the `:321`
# site rule (`LiquidHandler._assert_resources_exist`). This is a DIFFERENT
# dispatch shape from R-HEAD/R-ATTR/R-CONST above -- `:321`'s own guard
# predicate has no `EnvRef` at all (§16.1.3's Q2) and neither of its two
# free names (`resource`/`resource_from_deck`) binds through any idiom this
# module implements, so `plr_sema.check.predicate.D6_SITE_RULES` REPLACES
# `evaluate_predicate` outright for the matched `(qualname, lineno)` rather
# than resolving one sub-expression inside it.
# ---------------------------------------------------------------------------

_T48_ASSERT_RESOURCES_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
    lineno=321,
    qualname="LiquidHandler._assert_resources_exist",
)


def _t48_env(*, verified: bool) -> "frozenset[str]":
    return frozenset({f"obs:deck_resources_verified={'true' if verified else 'false'}"})


def _pick_up_tips_resources_graph(
    tip_spots_literal: str = "[tip_rack_1]",
    *,
    resources: "dict[str, Any] | None" = None,
) -> str:
    return json.dumps(
        {
            "protocol_fqn": "test.t48_assert_resources",
            "operations": [
                {
                    "id": "op_1",
                    "method_name": "pick_up_tips",
                    "receiver_variable": "lh",
                    "receiver_type": "LiquidHandler",
                    "arguments": {"tip_spots": tip_spots_literal, "use_channels": "[0]"},
                }
            ],
            "resources": resources if resources is not None else {"tip_rack_1": {}},
        }
    )


def test_ac_16_13_321_site_rule_flips_safe_under_verified_observation(contracts_json: str) -> None:
    """The real `:321` guard, unmodified -- through T43 there is no rule
    matching this site at all, so `evaluate_predicate` runs against
    `resource`/`resource_from_deck` (both unbindable, §16.1.3's Q2) and
    stays `UNKNOWN` regardless of `env` (see the no-observation test right
    below). Once `D6_SITE_RULES` dispatches AND the harness's own aggregate
    deck fact (`obs:deck_resources_verified`) says `True`, the SAME real
    guard -- reached via T42's `caller_args` (`resources` -> `tip_spots`,
    the real derived contract table's own entry) -- flips `SAFE`."""
    report = check_graph(_pick_up_tips_resources_graph(), contracts_json, env=_t48_env(verified=True))
    (finding,) = _site_findings(report, _T48_ASSERT_RESOURCES_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.SAFE


def test_ac_16_13_321_no_observation_stays_env_dependent(contracts_json: str) -> None:
    """§16.2.3's fail-closed default: with no `obs:` member in `env`, the
    site rule declines (no `deck_resources_verified` key in the decoded
    observation) exactly like every other §16.5 rule."""
    report = check_graph(_pick_up_tips_resources_graph(), contracts_json)
    (finding,) = _site_findings(report, _T48_ASSERT_RESOURCES_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"


def test_ac_16_13_321_unverified_deck_declines(contracts_json: str) -> None:
    """`obs:deck_resources_verified=false` (some row-declared deck-parented
    name is NOT a member of the observed `deck_resource_names`) declines,
    never falsifies -- the rule has no `T`-producing branch at all, so a
    `False` aggregate fact and a `True` one both land in the SAME ½
    outcome, distinguished only by which one CAN later decide `F`."""
    report = check_graph(_pick_up_tips_resources_graph(), contracts_json, env=_t48_env(verified=False))
    (finding,) = _site_findings(report, _T48_ASSERT_RESOURCES_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"


def test_ac_16_13_321_site_rule_never_returns_true() -> None:
    """§16.1.3 Fact 1: an absent name raises at `:318`, not `:321`, so the
    positive branch is never established -- asserted directly against
    `_eval_assert_resources_site_rule`'s own Kleene range, exhaustively
    over every branch its own docstring names. The stub-defeating half:
    a rule that always returned `None` would also pass every `check_graph`
    test above (`UNKNOWN` either way), so branch (b) here is what proves
    the `False`-producing path is actually implemented, not merely
    defaulted away."""
    from plr_sema.check.predicate import _Ctx, _eval_assert_resources_site_rule

    def _ctx(*, kwargs: dict, resources_by_slot: dict, env: "frozenset[str]") -> _Ctx:
        return _Ctx(
            call=ir.Call(receiver=0, receiver_type="LiquidHandler", method="_assert_resources_exist", kwargs=kwargs),
            resources_by_slot=resources_by_slot,
            param_defaults={},
            bindings_by_name={},
            depth=0,
            channel_kwarg=None,
            channels=None,
            env=env,
            class_hierarchy=None,
        )

    declared = {
        0: ir.Resource(
            slot=0, type=None, element_type=None, is_container=False, is_parameter=True, parents=("Deck",), grid=None
        )
    }
    verified_true = frozenset({"obs:deck_resources_verified=true"})
    verified_false = frozenset({"obs:deck_resources_verified=false"})

    # (a) `resources` unresolved (`ir.Top()`, no kwarg at all) -> ½, never T.
    assert _eval_assert_resources_site_rule(_ctx(kwargs={}, resources_by_slot=declared, env=verified_true)) is None
    # (b) a concrete Seq of declared Refs, verified True -> F, the ONE decided branch.
    assert (
        _eval_assert_resources_site_rule(
            _ctx(kwargs={"resources": ir.Seq((ir.Ref(0, None),))}, resources_by_slot=declared, env=verified_true)
        )
        is False
    )
    # (c) same Seq, verified False -> ½, never T.
    assert (
        _eval_assert_resources_site_rule(
            _ctx(kwargs={"resources": ir.Seq((ir.Ref(0, None),))}, resources_by_slot=declared, env=verified_false)
        )
        is None
    )
    # (d) a non-Ref element -> ½, never T.
    assert (
        _eval_assert_resources_site_rule(
            _ctx(kwargs={"resources": ir.Seq((ir.Lit(1),))}, resources_by_slot=declared, env=verified_true)
        )
        is None
    )
    # (e) a Ref to an undeclared slot -> ½, never T.
    assert (
        _eval_assert_resources_site_rule(
            _ctx(kwargs={"resources": ir.Seq((ir.Ref(1, None),))}, resources_by_slot=declared, env=verified_true)
        )
        is None
    )


def test_ac_16_13_a_deck_object_adversarial_duplicate_name_mismatched_geometry(contracts_json: str) -> None:
    """AC-16.13's HAND-BUILT adversarial fixture (C18): a second
    `pylabrobot.resources.Resource`, constructed DIRECTLY (never through
    the kwarg-mutator API) with the SAME name as an existing deck resource
    but a MISMATCHED geometry. PLR's own `Resource.__eq__` (name, all three
    absolute sizes, location, category and children, §16.1.3 Fact 2) says
    these are NOT equal despite the name match -- the exact residual
    A-DECK-OBJECT accepts, given a NAME witness alone.

    The STATIC site rule, told only that the name is verified
    (`obs:deck_resources_verified=true` -- exactly what the harness's own
    `deck_map` would say: it is built from `deck_resource_names`, a NAME
    list, with no notion of geometry at all), still predicts `SAFE` -- it
    CANNOT see this gap, by construction (§16.1.3's own normative box: "no
    derivation establishes it at all"). Were this fed through the full
    runtime harness (`training/verify/`, `plr-sema/eval/region_oracle.py`
    -- both outside this row's own file list), PLR's real
    `_assert_resources_exist` would raise on the genuine object at runtime
    while the static side predicts `SAFE`, exactly what the tier-1 fence's
    `unsound` counter (`plr-sema/eval/oracle_common.py`'s `compare`,
    unmodified) exists to catch; this test proves the STATIC half of that
    gap directly and in-process, since re-deriving the runtime harness is
    outside this row's own file scope."""
    from pylabrobot.resources import Resource

    deck_resource = Resource("tip_rack_1", size_x=10, size_y=10, size_z=10, category="resource")
    duplicate_resource = Resource("tip_rack_1", size_x=999, size_y=999, size_z=999, category="resource")
    assert deck_resource.name == duplicate_resource.name
    assert deck_resource != duplicate_resource  # A-DECK-OBJECT's own residual (§16.1.3 Fact 2).

    report = check_graph(_pick_up_tips_resources_graph(), contracts_json, env=_t48_env(verified=True))
    (finding,) = _site_findings(report, _T48_ASSERT_RESOURCES_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.SAFE


def test_ac_16_13_a_deck_object_assumption_table_has_five_rows() -> None:
    """AC-16.13: A-DECK-OBJECT is added to increment 1's §10.6.3
    named-assumption table with its own breakage column, taking the table
    from FOUR rows to FIVE -- asserted directly against the spec file
    rather than trusted from prose."""
    spec_path = REPO_ROOT / ".praxia" / "docs" / "specs" / "260902_plr-sema-tip-typestate-increment.md"
    text = spec_path.read_text(encoding="utf-8")
    start = text.index("### 10.6.3 The assumptions, named")
    header_idx = text.index("| id | assumption", start)
    end = text.index("\n\n", header_idx)
    table = text[start:end]
    rows = [line for line in table.splitlines() if line.startswith("| **A-")]
    assert len(rows) == 5, f"expected 5 named-assumption rows, found {len(rows)}: {rows}"
    assert any(row.startswith("| **A-DECK-OBJECT**") for row in rows), rows


# ---------------------------------------------------------------------------
# AC-16.14 (spec 260909 §16.1.1/§16.15 D6, T49, backlog #5026): the
# `:375`/`:383` site rules (D5b). SAME `D6_SITE_RULES` dict, SAME dispatch
# shape as `:321` above -- each REPLACES `evaluate_predicate` outright for
# its own matched guard. Unlike `:321`, both read `ctx.caller_args`
# directly (`"method"`'s `EnvRef` last path segment, `"default"`'s G9
# `SetLit`) rather than through `_resolve_var`'s ordinary E-CALL steps,
# because `missing`/`vars_keyword` are LOCALS of `_check_args`, never its
# parameters.
# ---------------------------------------------------------------------------

_T49_MISSING_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
    lineno=375,
    qualname="LiquidHandler._check_args",
)
_T49_STRICT_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
    lineno=383,
    qualname="LiquidHandler._check_args",
)


def test_ac_16_14_375_383_site_rules_flip_safe_under_observation(contracts_json: str) -> None:
    """The real `:375`/`:383` guards, unmodified -- through T48 there is no
    rule matching either site at all, so both stay `UNKNOWN` regardless of
    `env` (see the no-observation test right below). Once `D6_SITE_RULES`
    dispatches AND the observed `backend_class` (chatterbox, the pin) has a
    `pick_up_tips` row in §16.3's surface -- reached via T42's `caller_args`
    (`method` -> `self.backend.pick_up_tips`, `default` -> G9's `SetLit`,
    the real derived contract table's own entries) -- both flip `SAFE`."""
    report = check_graph(_pick_up_tips_use_channels_graph("[0, 1]"), contracts_json, env=_t43_obs_env())
    (missing_finding,) = _site_findings(report, _T49_MISSING_SITE, operation_id="op_1")
    assert missing_finding.verdict is Verdict.SAFE
    (strict_finding,) = _site_findings(report, _T49_STRICT_SITE, operation_id="op_1")
    assert strict_finding.verdict is Verdict.SAFE


def test_ac_16_14_no_observation_stays_env_dependent(contracts_json: str) -> None:
    """§16.2.3's fail-closed default: with no `obs:` member in `env`, both
    sites decline (no `backend_class` in the decoded observation, so
    `_check_args_surface_row` cannot even look up a row) exactly like every
    other §16.5/D6 rule."""
    report = check_graph(_pick_up_tips_use_channels_graph("[0, 1]"), contracts_json)
    (missing_finding,) = _site_findings(report, _T49_MISSING_SITE, operation_id="op_1")
    assert missing_finding.verdict is Verdict.UNKNOWN
    assert missing_finding.reason == "guard_env_dependent"
    (strict_finding,) = _site_findings(report, _T49_STRICT_SITE, operation_id="op_1")
    assert strict_finding.verdict is Verdict.UNKNOWN
    assert strict_finding.reason == "guard_env_dependent"


def test_ac_16_14_unobserved_backend_class_declines(contracts_json: str) -> None:
    """A `backend_class` with no row in the derived surface -- the SAME
    decline clause R-CONST's own AC-16.5 test exercises (§16.5.3) --
    declines to ½, never fabricates a value for an unobserved/unknown
    backend/method pair. This is also the observable proxy for C15's
    absence rule: a decorated or multiply-defined `(class, method)` is
    likewise simply ABSENT from the surface, which this function cannot
    distinguish from "never a candidate at all" -- and is not meant to,
    §16.3's own selection box makes both cases the identical decline."""
    env = _t43_obs_env(backend_class="SomeUnknownBackend")
    report = check_graph(_pick_up_tips_use_channels_graph("[0, 1]"), contracts_json, env=env)
    (missing_finding,) = _site_findings(report, _T49_MISSING_SITE, operation_id="op_1")
    assert missing_finding.verdict is Verdict.UNKNOWN
    (strict_finding,) = _site_findings(report, _T49_STRICT_SITE, operation_id="op_1")
    assert strict_finding.verdict is Verdict.UNKNOWN


def _t49_ctx(*, caller_args: "dict[str, Any] | None", env: "frozenset[str]", backend_surface: "dict[str, Any]") -> "Any":
    from plr_sema.check.predicate import _Ctx

    return _Ctx(
        call=ir.Call(receiver=0, receiver_type="LiquidHandler", method="_check_args", kwargs={}),
        resources_by_slot={},
        param_defaults={},
        bindings_by_name={},
        depth=1,
        channel_kwarg=None,
        channels=None,
        env=env,
        class_hierarchy=None,
        caller_args=caller_args,
        backend_surface=backend_surface,
    )


_T49_METHOD_ENVREF = {"node": "EnvRef", "path": ["self", "backend", "pick_up_tips"], "args": None}
_T49_DEFAULT_SETLIT = {"node": "SetLit", "values": ["ops", "use_channels"]}
_T49_SURFACE = {
    "LiquidHandlerChatterboxBackend.pick_up_tips": {
        "params": ["ops", "use_channels"],
        "has_var_keyword": True,
        "has_var_positional": False,
    }
}
_T49_ENV = frozenset({'obs:backend_class="LiquidHandlerChatterboxBackend"'})


def test_ac_16_14_missing_site_rule_never_returns_true() -> None:
    """§16.1.1's own arithmetic: the rule only ever proves the MINUEND
    (`missing`) empty, never the SUBTRAHEND non-empty -- asserted directly
    against `_eval_check_args_missing_site_rule`'s own Kleene range,
    exhaustively over every branch its own docstring names. The
    stub-defeating half: a rule that always returned `None` would also
    pass the `check_graph` no-observation test above, so branch (b) here
    is what proves the `False`-producing path is actually implemented."""
    from plr_sema.check.predicate import _eval_check_args_missing_site_rule

    # (a) no caller_args at all -> decline, never T.
    ctx = _t49_ctx(caller_args=None, env=_T49_ENV, backend_surface=_T49_SURFACE)
    assert _eval_check_args_missing_site_rule(ctx) is None
    # (b) method + default present, params subset of default -> F, the ONE decided branch.
    ctx = _t49_ctx(
        caller_args={"method": _T49_METHOD_ENVREF, "default": _T49_DEFAULT_SETLIT},
        env=_T49_ENV,
        backend_surface=_T49_SURFACE,
    )
    assert _eval_check_args_missing_site_rule(ctx) is False
    # (c) no backend_class observed -> decline, never T.
    ctx = _t49_ctx(
        caller_args={"method": _T49_METHOD_ENVREF, "default": _T49_DEFAULT_SETLIT},
        env=frozenset(),
        backend_surface=_T49_SURFACE,
    )
    assert _eval_check_args_missing_site_rule(ctx) is None
    # (d) no surface row for this (class, method) -> decline, never T.
    ctx = _t49_ctx(
        caller_args={"method": _T49_METHOD_ENVREF, "default": _T49_DEFAULT_SETLIT},
        env=_T49_ENV,
        backend_surface={},
    )
    assert _eval_check_args_missing_site_rule(ctx) is None
    # (e) no "default" caller-arg -> decline, never T.
    ctx = _t49_ctx(caller_args={"method": _T49_METHOD_ENVREF}, env=_T49_ENV, backend_surface=_T49_SURFACE)
    assert _eval_check_args_missing_site_rule(ctx) is None
    # (f) params NOT a subset of default -> decline, never T (the surface
    # row's own params exceed what the caller declared as default).
    surface_superset = {
        "LiquidHandlerChatterboxBackend.pick_up_tips": {
            "params": ["ops", "use_channels", "extra_required_param"],
            "has_var_keyword": True,
            "has_var_positional": False,
        }
    }
    ctx = _t49_ctx(
        caller_args={"method": _T49_METHOD_ENVREF, "default": _T49_DEFAULT_SETLIT},
        env=_T49_ENV,
        backend_surface=surface_superset,
    )
    assert _eval_check_args_missing_site_rule(ctx) is None


def test_ac_16_14_strict_site_rule_never_returns_true() -> None:
    """The SAME Kleene-range proof for `:383`: the rule decides `F` iff
    `has_var_keyword` is exactly `True` on the observed surface row, and
    NEVER resolves `strictness` at all (§16.1.1's own box) -- so a
    `has_var_keyword=False` row declines exactly like a missing one, never
    falsifying to `T` in either case."""
    from plr_sema.check.predicate import _eval_check_args_strict_site_rule

    # (a) no caller_args at all -> decline, never T.
    ctx = _t49_ctx(caller_args=None, env=_T49_ENV, backend_surface=_T49_SURFACE)
    assert _eval_check_args_strict_site_rule(ctx) is None
    # (b) has_var_keyword True -> F, the ONE decided branch.
    ctx = _t49_ctx(caller_args={"method": _T49_METHOD_ENVREF}, env=_T49_ENV, backend_surface=_T49_SURFACE)
    assert _eval_check_args_strict_site_rule(ctx) is False
    # (c) no backend_class observed -> decline, never T.
    ctx = _t49_ctx(caller_args={"method": _T49_METHOD_ENVREF}, env=frozenset(), backend_surface=_T49_SURFACE)
    assert _eval_check_args_strict_site_rule(ctx) is None
    # (d) no surface row -> decline, never T.
    ctx = _t49_ctx(caller_args={"method": _T49_METHOD_ENVREF}, env=_T49_ENV, backend_surface={})
    assert _eval_check_args_strict_site_rule(ctx) is None
    # (e) has_var_keyword False -> decline, never T.
    surface_no_var_keyword = {
        "LiquidHandlerChatterboxBackend.pick_up_tips": {
            "params": ["ops", "use_channels"],
            "has_var_keyword": False,
            "has_var_positional": False,
        }
    }
    ctx = _t49_ctx(
        caller_args={"method": _T49_METHOD_ENVREF}, env=_T49_ENV, backend_surface=surface_no_var_keyword
    )
    assert _eval_check_args_strict_site_rule(ctx) is None


def test_ac_16_14_set_lit_parses_and_round_trips() -> None:
    """G9's own narrow shape test (T49): an `ast.Set` display of
    `ast.Constant`s parses to `SetLit`, round-trips through `to_json`/
    `from_json`, and a display containing ANY non-`Constant` element fails
    the WHOLE display's parse (no partial `SetLit`) -- collapsing the
    enclosing `Cmp` to `Opaque`, the ordinary Term-parse-failure path."""
    from plr_sema.derive.predicate_ast import Cmp, Opaque, SetLit, from_json, parse, to_json

    parsed = parse('x == {"a", "b", "a"}')
    assert isinstance(parsed, Cmp)
    assert isinstance(parsed.right, SetLit)
    assert parsed.right.values == ("a", "b")  # deduplicated, first-occurrence order.
    assert from_json(to_json(parsed)) == parsed

    mixed = parse("x == {1, f()}")
    assert isinstance(mixed, Opaque)  # one non-Constant element -> the WHOLE display fails to parse.


# ---------------------------------------------------------------------------
# AC-17.2 (spec 260909_plr-sema-move-family-increment.md §17.1.2/§17.3,
# T51): `:2055`'s REAL, unmodified `LiquidHandler.pick_up_resource` guard
# record, end to end -- never through a hand-built predicate.
# ---------------------------------------------------------------------------

_PICK_UP_RESOURCE_2055_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
    lineno=2055,
    qualname="LiquidHandler.pick_up_resource",
)


def _pick_up_resource_graph() -> str:
    return json.dumps(
        {
            "protocol_fqn": "test.t51_r_arm",
            "operations": [
                {
                    "id": "op_1",
                    "method_name": "pick_up_resource",
                    "receiver_variable": "lh",
                    "receiver_type": "LiquidHandler",
                    "arguments": {},
                }
            ],
            "resources": {},
        }
    )


def _arm_slots_only_env(arm_slots: "list[int]") -> "frozenset[str]":
    return frozenset({f"obs:arm_slots={list(arm_slots)}".replace(" ", "")})


def test_ac_17_2_2055_safe_end_to_end_through_shipped_guard_record(contracts_json: str) -> None:
    """AC-17.2's positive claim: `:2055` (`self.setup_finished and not
    self._resource_pickups`) decides `SAFE` end to end through the REAL,
    UNMODIFIED `LiquidHandler.pick_up_resource` guard record -- never
    through a hand-built predicate -- once `arm_slots` observes at least
    one arm. Only the SECOND `And` conjunct needs to resolve (Kleene `And`:
    one `False` decides regardless of the other); `self.setup_finished`
    is never observed here and never has to be."""
    report = check_graph(_pick_up_resource_graph(), contracts_json, env=_arm_slots_only_env([0, 1]))
    (finding,) = _site_findings(report, _PICK_UP_RESOURCE_2055_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.SAFE


def test_ac_17_2_2055_no_observation_stays_unknown(contracts_json: str) -> None:
    """§16.2.3's fail-closed default, unaffected by this increment: with no
    `arm_slots` observation in `env`, `:2055` stays exactly where it was
    before T51 -- `UNKNOWN`/`guard_env_dependent`."""
    report = check_graph(_pick_up_resource_graph(), contracts_json)
    (finding,) = _site_findings(report, _PICK_UP_RESOURCE_2055_SITE, operation_id="op_1")
    assert finding.verdict is Verdict.UNKNOWN
    assert finding.reason == "guard_env_dependent"


# ---------------------------------------------------------------------------
# AC-17.3 (spec 260909_plr-sema-move-family-increment.md §17.4, T52): the
# `_resource_pickup` typestate, end to end through the REAL, UNMODIFIED
# `move_resource`/`pick_up_resource`/`move_picked_up_resource`/
# `drop_resource` guard records -- never through a hand-built predicate.
# ---------------------------------------------------------------------------

_PICK_UP_RESOURCE_2070_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
    lineno=2070,
    qualname="LiquidHandler.pick_up_resource",
)
_MOVE_PICKED_UP_RESOURCE_2120_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
    lineno=2120,
    qualname="LiquidHandler.move_picked_up_resource",
)
_DROP_RESOURCE_2147_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
    lineno=2147,
    qualname="LiquidHandler.drop_resource",
)


def _move_resource_graph(n_ops: int) -> str:
    return json.dumps(
        {
            "protocol_fqn": "test.t52_anchor",
            "operations": [
                {
                    "id": f"op_{i + 1}",
                    "method_name": "move_resource",
                    "receiver_variable": "lh",
                    "receiver_type": "LiquidHandler",
                    "arguments": {},
                }
                for i in range(n_ops)
            ],
            "resources": {},
        }
    )


def test_ac_17_3_move_resource_2120_2147_decide_safe_from_held(contracts_json: str) -> None:
    """AC-17.3: `:2120`/`:2147` decide `SAFE` from `HELD` on a SINGLE
    `move_resource` call, through the REAL guard records -- their own
    pre-state is a derive-time CONSTANT (`pick_up_resource`'s own
    `:2072-2077` effect, strictly earlier in the SAME closure), never the
    walk's inter-operation carry, so a single, isolated operation already
    decides both."""
    report = check_graph(_move_resource_graph(1), contracts_json)
    (f2120,) = _site_findings(report, _MOVE_PICKED_UP_RESOURCE_2120_SITE, operation_id="op_1")
    (f2147,) = _site_findings(report, _DROP_RESOURCE_2147_SITE, operation_id="op_1")
    assert f2120.verdict is Verdict.SAFE
    assert f2147.verdict is Verdict.SAFE


def test_ac_17_3_pick_up_resource_2070_decides_safe_from_empty_carried_state(contracts_json: str) -> None:
    """AC-17.3: `:2070` decides `SAFE` from `EMPTY` -- carried in from a
    PRIOR operation's own net effect (`drop_resource`'s `:2263` assignment,
    `AnchorWalk`'s inter-operation carry, §17.4.3 condition 4), through TWO
    sequential `move_resource` calls on the same receiver. The FIRST call's
    own `:2070` starts from a fresh walk (`TOP`, untested here); the
    SECOND's genuinely decides by state."""
    report = check_graph(_move_resource_graph(2), contracts_json)
    (f2070_op2,) = _site_findings(report, _PICK_UP_RESOURCE_2070_SITE, operation_id="op_2")
    assert f2070_op2.verdict is Verdict.SAFE


def test_ac_17_3_no_anchor_widening_on_move_family(contracts_json: str) -> None:
    """AC-17.3: none of the five widening conditions fire on the real
    move-family closure -- every one of the three anchor guards decides by
    state (`SAFE`, never `UNKNOWN`/`guard_env_dependent`) across two
    sequential operations."""
    report = check_graph(_move_resource_graph(2), contracts_json)
    for site, op_id in (
        (_PICK_UP_RESOURCE_2070_SITE, "op_2"),
        (_MOVE_PICKED_UP_RESOURCE_2120_SITE, "op_1"),
        (_DROP_RESOURCE_2147_SITE, "op_1"),
    ):
        (finding,) = _site_findings(report, site, operation_id=op_id)
        assert finding.verdict is Verdict.SAFE, f"{site}: expected SAFE (decided by state, not widened), got {finding.verdict}"


def test_ac_17_3_anchor_and_channel_consumed_sets_disjoint() -> None:
    """AC-17.3(b): the anchor and channel `consumed` index sets are
    asserted DISJOINT on the tip fixtures -- a synthetic receiver carrying
    BOTH a P2 channel anchor and a P5 singleton anchor, and a contract
    whose `guards` mix a channel-scoped own guard (`self.head[i].has_tip`)
    with a bare-`self` anchor guard (`self._resource_pickup is None`). A
    guard matching `self.<channel_attr>[<name>]` cannot also match a
    bare-`self` anchor field, by construction."""
    from plr_sema.check import ir
    from plr_sema.check.tipstate import AnchorWalk, TipWalk, evaluate_anchor_call, evaluate_call

    receiver_state = {
        "channel_attr": "head",
        "bool_view": {"attr": "has_tip", "field": "_tip", "true_when": "not_none"},
        "state_fields": ["_tip"],
        "effects": {},
        "channel_default_param": {"pick_up_tips": "tip_spots"},
        "channel_default_disablers": [],
        "tip_state_exceptions": [],
        "anchor_fields": ["_resource_pickup"],
    }
    contract = {
        "guards": [
            {
                "kind": "raise_guard",
                "condition": "self.head[channel].has_tip",
                "site": {"file": "f", "lineno": 1, "qualname": "q"},
            },
            {
                "kind": "raise_guard",
                "condition": "self._resource_pickup is None",
                "site": {"file": "f", "lineno": 2, "qualname": "q"},
                "anchor_state": "HELD",
                "anchor_field": "_resource_pickup",
            },
        ],
    }
    call = ir.Call(receiver=0, receiver_type="LiquidHandler", method="pick_up_tips", kwargs={"tip_spots": ir.Seq(items=(ir.Lit(v=0),))})
    _anchor_findings, anchor_consumed = evaluate_anchor_call("op_1", call, contract, receiver_state, AnchorWalk())
    _tip_findings, tip_consumed = evaluate_call("op_1", call, contract, receiver_state, TipWalk(), poisoned=False)
    assert anchor_consumed == {1}
    assert tip_consumed == {0}
    assert anchor_consumed & tip_consumed == set()


def test_ac_17_3_finding_for_atom_reason_parametrised(contracts_json: str) -> None:
    """AC-17.3: the ½ branch carries `guard_env_dependent` for the anchor
    (a fresh-walk `TOP` state on the FIRST `move_resource` call's own
    `:2070`, which has no preceding effect in its own closure) and
    `channel_state_unknown` remains the tip family's own reason,
    unchanged -- both asserted on the SAME report."""
    report = check_graph(_move_resource_graph(1), contracts_json)
    (f2070_op1,) = _site_findings(report, _PICK_UP_RESOURCE_2070_SITE, operation_id="op_1")
    assert f2070_op1.verdict is Verdict.UNKNOWN
    assert f2070_op1.reason == "guard_env_dependent"
