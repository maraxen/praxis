"""Spec 260902 §10 (`260902_plr-sema-tip-typestate-increment.md`), backlog
#4888 step 1: per-channel tip typestate. Each `test_ac_10_*` function below
names one acceptance criterion from §10.7 individually (not grouped), per
the task brief's convention.

**Fixtures.** `double_pickup_graph.json`, `pickup_then_aspirate_graph.json`,
`aspirate_after_drop_graph.json` (all three named by the spec, §10.7) use
operation ids `op_1`/`op_2`/`op_3` (1-indexed), matching this repo's
existing `simple_transfer_graph.json` convention -- not the spec's own
illustrative `op_0`/`op_1` (0-indexed) numbering. Substance, not the id
strings, is what every assertion below pins.

**Disclosed deviation from AC-10.1's literal "exactly one" `WILL_FAIL`
count (see `test_ac_10_1...` below).** §10.2.6 itself predicts
`pick_up_tips`'s tip-loading precondition is covered "both ways: its own
:535 guard *and* `self.head[channel].add_tip` at :538" -- and §10.3.1's
evaluator has no dedup rule between an "own guard" and a "channel guard"
that happen to demand the identical real-world precondition. Implemented
literally, a repeated pickup therefore produces TWO independent `WILL_FAIL`
findings (the own :535 guard, and the bridged `TipTracker.add_tip:92`
guard), not one. This is sound (strictly more true evidence, never a
fabricated claim) and is the direction increment 1's own soundness argument
(§10.5) explicitly prefers when a choice must be made under-specified by
the letter of an AC. The test below asserts AC-10.1's literal pins (the
`:535` site, category, per-op join, report verdict) among the findings,
rather than asserting a bare count of exactly 1.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
from plr_sema.check import check_graph
from plr_sema.derive.receiver_state import compute_tip_state_exceptions
from plr_sema.verdict import AnalysisReport, PlrSite, Verdict

PLR_SEMA_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLR_SEMA_ROOT.parent
FIXTURES = PLR_SEMA_ROOT / "tests" / "fixtures"
CONTRACTS_JSON_PATH = PLR_SEMA_ROOT / "data" / "derived_contracts.json"
TAXONOMY_JSON_PATH = REPO_ROOT / "training" / "verify" / "data" / "plr_exception_taxonomy.json"

_PICK_UP_TIPS_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
    lineno=535,
    qualname="LiquidHandler.pick_up_tips",
)
_GET_TIP_SITE = PlrSite(
    file="external/pylabrobot/pylabrobot/resources/tip_tracker.py", lineno=65, qualname="TipTracker.get_tip"
)
# 260904 (increment 6, T31): plr_sema.check.predicate now correctly
# DECIDES a handful of non-tip-family guards whose only operand is a
# literal kwarg -- most commonly the uniqueness assert `len(set(
# use_channels)) == len(use_channels)`, sited at pick_up_tips:502 and
# aspirate:959 -- SAFE whenever the fixture's `use_channels` kwarg is a
# literal list with no duplicates (every fixture in this file that
# supplies one). This is correct, expected T31 behaviour, unrelated to
# tip TYPESTATE (it depends only on the kwarg's own value, never on
# `TipWalk`'s state), so tests below that assert "no SAFE"/"no WILL_FAIL
# anywhere on this operation/report" are scoped past it via
# `_excluding_now_decided_non_tip_guards` rather than by widening the
# claim to include a site this module's own family never touches.
_UNIQUE_CHANNELS_SITES = frozenset(
    {
        PlrSite(
            file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
            lineno=502,
            qualname="LiquidHandler.pick_up_tips",
        ),
        PlrSite(
            file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
            lineno=959,
            qualname="LiquidHandler.aspirate",
        ),
        PlrSite(
            file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
            lineno=1153,
            qualname="LiquidHandler.dispense",
        ),
        PlrSite(
            file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
            lineno=651,
            qualname="LiquidHandler.drop_tips",
        ),
    }
)


def _excluding_now_decided_non_tip_guards(findings: list) -> list:
    return [f for f in findings if f.plr_site not in _UNIQUE_CHANNELS_SITES]


@pytest.fixture(scope="module")
def contracts_json() -> str:
    return CONTRACTS_JSON_PATH.read_text(encoding="utf-8")


def _graph(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _check(name: str, contracts_json: str) -> AnalysisReport:
    return check_graph((FIXTURES / f"{name}.json").read_text(encoding="utf-8"), contracts_json)


def _findings_for(report: AnalysisReport, operation_id: str) -> list:
    return [f for f in report.findings if f.operation_id == operation_id]


def _join(findings: list) -> Verdict:
    verdicts = {f.verdict for f in findings}
    if Verdict.WILL_FAIL in verdicts:
        return Verdict.WILL_FAIL
    if Verdict.UNKNOWN in verdicts:
        return Verdict.UNKNOWN
    return Verdict.SAFE if findings else Verdict.UNKNOWN


# ---------------------------------------------------------------------------
# AC-10.1
# ---------------------------------------------------------------------------


def test_ac_10_1_will_fail_on_repeated_pickup(contracts_json: str) -> None:
    report = _check("double_pickup_graph", contracts_json)
    op1, op2 = _findings_for(report, "op_1"), _findings_for(report, "op_2")

    assert _join(op1) is Verdict.UNKNOWN
    assert _join(op2) is Verdict.WILL_FAIL
    assert report.verdict is Verdict.WILL_FAIL

    will_fail = [f for f in op2 if f.verdict is Verdict.WILL_FAIL]
    assert will_fail, "the second pick_up_tips must produce at least one WILL_FAIL"
    assert all(f.category == "precondition_state" for f in will_fail)
    assert any(f.plr_site == _PICK_UP_TIPS_SITE for f in will_fail), (
        "AC-10.1's literal pin: one WILL_FAIL must be sited at liquid_handler.py:535"
    )
    # See this module's docstring: §10.2.6 predicts a SECOND, additive
    # WILL_FAIL from the bridged TipTracker.add_tip guard -- disclosed, not
    # a defect.
    assert len(will_fail) == 2
    assert not [f for f in _excluding_now_decided_non_tip_guards(op2) if f.verdict is Verdict.SAFE]


# ---------------------------------------------------------------------------
# AC-10.2
# ---------------------------------------------------------------------------


def test_ac_10_2_safe_after_pickup_no_operation_level_safe(contracts_json: str) -> None:
    report = _check("pickup_then_aspirate_graph", contracts_json)
    op2 = _findings_for(report, "op_2")

    safe = [f for f in _excluding_now_decided_non_tip_guards(op2) if f.verdict is Verdict.SAFE]
    assert len(safe) == 1, "exactly one SAFE finding on the aspirate, per AC-10.2"
    assert safe[0].plr_site == _GET_TIP_SITE

    assert _join(op2) is Verdict.UNKNOWN, "the operation-level join stays UNKNOWN (its other guards are 1/2)"
    assert not any(f.verdict is Verdict.WILL_FAIL for f in report.findings), (
        "no Finding in the whole report is WILL_FAIL"
    )
    assert report.verdict is Verdict.UNKNOWN


# ---------------------------------------------------------------------------
# AC-10.3
# ---------------------------------------------------------------------------


def test_ac_10_3_will_fail_sited_in_tip_tracker(contracts_json: str) -> None:
    report = _check("aspirate_after_drop_graph", contracts_json)
    op3 = _findings_for(report, "op_3")  # the aspirate, third op (1-indexed)

    will_fail = [f for f in op3 if f.verdict is Verdict.WILL_FAIL]
    assert len(will_fail) == 1
    assert will_fail[0].category == "precondition_state"
    assert will_fail[0].plr_site == _GET_TIP_SITE
    assert report.verdict is Verdict.WILL_FAIL


# ---------------------------------------------------------------------------
# AC-10.4
# ---------------------------------------------------------------------------


def test_ac_10_4_shipped_fixture_unchanged(contracts_json: str) -> None:
    report = _check("simple_transfer_graph", contracts_json)
    assert report.verdict is Verdict.UNKNOWN
    assert all(f.verdict is Verdict.UNKNOWN for f in report.findings)
    # Pre-increment finding count over this fixture (measured against the
    # pre-increment-shaped contract table, AC-10.7's fixture, below) is the
    # same 38 -- asserted there, cross-checked here, EXCLUDING volume-family
    # findings. 260903 (spec §14, T26): the LIVE `contracts_json` fixture's
    # `LiquidHandler.aspirate`/`dispense` entries have carried `volume_guards`
    # since T24/T25 landed, but nothing consumed them until T26 wired
    # `plr_sema.check.volumestate` into this same walk -- this fixture's own
    # aspirate/dispense calls now ALSO pick up 4 additive
    # `volume_state_unknown`/`volume_tracking_unasserted` findings (2 guards
    # apiece), which `derived_contracts_pre_increment.json` (predating every
    # increment) cannot produce at all. That is the correct, disclosed
    # consequence of T26 landing, not a tip-state regression -- so this test
    # narrows to reasons tip state's OWN AC-10.4 cares about, tip-family
    # findings, by excluding the two volume reasons before comparing counts.
    pre_contracts = (FIXTURES / "derived_contracts_pre_increment.json").read_text(encoding="utf-8")
    pre_report = _check("simple_transfer_graph", pre_contracts)
    _VOLUME_REASONS = {"volume_state_unknown", "volume_tracking_unasserted"}
    non_volume = [f for f in report.findings if f.reason not in _VOLUME_REASONS]
    assert len(non_volume) == len(pre_report.findings)
    assert len(report.findings) - len(non_volume) == 4, (
        "expected exactly 4 additive volume findings (aspirate's 2 guards + "
        "dispense's 2 guards) over this fixture"
    )
    assert not any(f.reason == "channel_state_unknown" for f in report.findings)


# ---------------------------------------------------------------------------
# AC-10.5 -- three variants, each asserting op_2 (the second pick_up_tips)
# has zero WILL_FAIL and zero SAFE findings, and the report stays UNKNOWN.
# ---------------------------------------------------------------------------


def _assert_widened(report: AnalysisReport) -> None:
    op2 = _excluding_now_decided_non_tip_guards(_findings_for(report, "op_2"))
    assert not any(f.verdict is Verdict.WILL_FAIL for f in op2)
    assert not any(f.verdict is Verdict.SAFE for f in op2)
    assert report.verdict is Verdict.UNKNOWN


def test_ac_10_5a_own_foreach_field_no_longer_widens_self(contracts_json: str) -> None:
    """Spec 260903 §12.9 amendment 2 / §12.3.3's L3: increment 2's AC-10.5
    rule 2 ("an operation carrying its own `foreach_source`/`foreach_body`
    widens ITS OWN receiver") is SUPERSEDED, not merely refined -- L3
    retires the stale increment-2 compensation this exact fixture used to
    exercise (`check/__init__.py:462-478`, pre-260903). Under increment 3,
    op_2 carries a stray `foreach_source` but is NOT a real `REGION`
    header (`node_type` is still `"static"`) -- `lower_graph` still emits
    the pre-#4932 fixture/fuzz-only shape (op_2's own `CALL` immediately
    followed by an EMPTY `LOOP null ... END`, ir.py's own documented
    backward-compatible interpretation), and that adjacency no longer
    identifies a region owner (§12.2.2 retired the shape it used to lean
    on). op_2 must therefore be evaluated against its REAL pre-call state
    -- identical to unmodified `double_pickup_graph`'s op_2, i.e.
    `Verdict.WILL_FAIL` (round-1 O3; see AC-12.14(iv)'s dedicated
    `call_before_unowned_region_graph.json` fixture for the REAL-region
    version of this same regression test).
    """
    graph = _graph("double_pickup_graph")
    graph["operations"][1]["foreach_source"] = "wells"
    graph["has_loops"] = True
    report = check_graph(json.dumps(graph), contracts_json)
    baseline = check_graph((FIXTURES / "double_pickup_graph.json").read_text(encoding="utf-8"), contracts_json)

    op2 = _findings_for(report, "op_2")
    baseline_op2 = _findings_for(baseline, "op_2")
    assert _join(op2) is Verdict.WILL_FAIL
    assert sorted((f.verdict.value, f.category, f.reason, str(f.plr_site), f.detail) for f in op2) == sorted(
        (f.verdict.value, f.category, f.reason, str(f.plr_site), f.detail) for f in baseline_op2
    ), "the stray foreach_source must have ZERO effect on op_2's own evaluation"


def test_ac_10_5b_widening_erases_depends_on_params(contracts_json: str) -> None:
    graph = _graph("double_pickup_graph")
    graph["operations"][1]["depends_on_params"] = ["n"]
    report = check_graph(json.dumps(graph), contracts_json)
    _assert_widened(report)


def test_ac_10_5c_widening_erases_bare_name_use_channels(contracts_json: str) -> None:
    graph = _graph("double_pickup_graph")
    graph["operations"][0]["arguments"]["use_channels"] = "channels"  # bare Name, not a literal
    report = check_graph(json.dumps(graph), contracts_json)
    _assert_widened(report)


# ---------------------------------------------------------------------------
# AC-10.6 -- unknown shapes widen: a non-null condition_expr, and a
# use_channels-disabler call anywhere on the receiver.
# ---------------------------------------------------------------------------


def test_ac_10_6_own_condition_expr_no_longer_widens_self(contracts_json: str) -> None:
    """Spec 260903 §12.9 amendment 2 / §12.3.3's L3 -- the `BRANCH`
    analogue of `test_ac_10_5a_own_foreach_field_no_longer_widens_self`
    above; see that test's docstring for the full argument. op_2 carries a
    stray `condition_expr` but is not a real `REGION` header, so
    `lower_graph` emits the pre-#4932 shape (op_2's own `CALL` immediately
    followed by an empty, real, non-synthetic `BRANCH null ... ELSE ...
    END`) -- L3's retirement means this no longer widens op_2's own
    receiver, and B1's arm-wise join over two EMPTY arms is a no-op (each
    arm's post-state equals the entry state unchanged), so op_2 is
    evaluated exactly as in unmodified `double_pickup_graph`.
    """
    graph = _graph("double_pickup_graph")
    graph["operations"][1]["condition_expr"] = "True"
    graph["has_conditionals"] = True
    report = check_graph(json.dumps(graph), contracts_json)
    baseline = check_graph((FIXTURES / "double_pickup_graph.json").read_text(encoding="utf-8"), contracts_json)

    op2 = _findings_for(report, "op_2")
    baseline_op2 = _findings_for(baseline, "op_2")
    assert _join(op2) is Verdict.WILL_FAIL
    assert sorted((f.verdict.value, f.category, f.reason, str(f.plr_site), f.detail) for f in op2) == sorted(
        (f.verdict.value, f.category, f.reason, str(f.plr_site), f.detail) for f in baseline_op2
    ), "the stray condition_expr must have ZERO effect on op_2's own evaluation"


def test_ac_10_6_disabler_call_widens(contracts_json: str) -> None:
    graph = _graph("double_pickup_graph")
    graph["operations"].append(
        {
            "arguments": {},
            "condition_expr": None,
            "creates_state": [],
            "depends_on_params": [],
            "false_branch": [],
            "foreach_body": [],
            "foreach_source": None,
            "id": "op_0",
            "line_number": 0,
            "method_name": "use_channels",
            "node_type": "static",
            "preconditions": [],
            "receiver_type": "LiquidHandler",
            "receiver_variable": "lh",
            "true_branch": [],
        }
    )
    graph["execution_order"] = ["op_0", "op_1", "op_2"]
    report = check_graph(json.dumps(graph), contracts_json)
    _assert_widened(report)


# ---------------------------------------------------------------------------
# AC-10.7
# ---------------------------------------------------------------------------


def test_ac_10_7_stale_contract_table_degrades(contracts_json: str) -> None:
    pre_contracts = (FIXTURES / "derived_contracts_pre_increment.json").read_text(encoding="utf-8")
    graph_json = (FIXTURES / "simple_transfer_graph.json").read_text(encoding="utf-8")
    payload = json.loads(pre_contracts)
    assert "receiver_state" not in payload
    for entry in payload["contracts"].values():
        assert "channel_guards" not in entry

    report = check_graph(graph_json, pre_contracts)  # must not raise
    assert report.verdict is Verdict.UNKNOWN
    assert len(report.findings) == 38
    round_tripped = json.loads(json.dumps({"verdict": report.verdict.value, "n": len(report.findings)}))
    assert round_tripped == {"verdict": "unknown", "n": 38}


# ---------------------------------------------------------------------------
# AC-10.8
# ---------------------------------------------------------------------------


def test_ac_10_8_empty_graph_unchanged(contracts_json: str) -> None:
    report = check_graph('{"protocol_fqn":"p","operations":[],"resources":{}}', contracts_json)
    assert report.verdict is Verdict.UNKNOWN
    assert report.findings == ()


# ---------------------------------------------------------------------------
# AC-10.9 -- derivation reproducibility (three sub-assertions).
# ---------------------------------------------------------------------------


def test_ac_10_9_derivation_reproducibility(contracts_json: str) -> None:
    payload = json.loads(contracts_json)
    lh = payload["receiver_state"]["LiquidHandler"]

    # Sub-assertion 1: block equality.
    assert lh["channel_attr"] == "head"
    assert lh["tracker_class"] == "TipTracker"
    assert lh["bool_view"]["field"] == "_pending_tip"
    assert lh["bool_view"]["attr"] == "has_tip"
    assert lh["bool_view"]["true_when"] == "not_none"
    assert lh["effects"]["add_tip"] == "HAS_TIP"
    assert lh["effects"]["remove_tip"] == "NO_TIP"
    assert sorted(lh["tip_state_exceptions"]) == ["HasTipError", "NoTipError"]


def test_ac_10_9_taxonomy_filter_is_checked() -> None:
    """Sub-assertion 2: the module filter is itself an AC-checked fact, not
    just its output.
    """
    taxonomy = json.loads(TAXONOMY_JSON_PATH.read_text(encoding="utf-8"))
    classes = taxonomy["classes"]
    tip_state_unfiltered = {c["name"] for c in classes if c.get("category") == "tip_state"}
    assert tip_state_unfiltered == {
        "HamiltonNoTipError",
        "HasTipError",
        "NoTipError",
        "TipAlreadyFittedError",
        "TipTooLittleVolumeError",
    }
    filtered = {
        c["name"]
        for c in classes
        if c.get("category") == "tip_state" and c.get("module") == "pylabrobot.resources.errors"
    }
    assert filtered == {"HasTipError", "NoTipError"}
    assert set(compute_tip_state_exceptions(classes)) == filtered


_FORBIDDEN_LITERALS = frozenset(
    {
        "TipTracker",
        "has_tip",
        "_pending_tip",
        "NoTipError",
        "HasTipError",
        "head",
        "setup",
        # 260903 (spec §13.5.3, P9, AC-13.15(iii)): the delegate-call
        # channel binding must read these four names off PLR itself
        # (an ast.Attribute callee, P3a's own measured
        # `channel_default_param` map, and the assignment target `p`
        # `_channel_kwarg_name` derives) -- never spell them as string
        # constants in `check/tipstate.py`/`derive/receiver_state.py`.
        "transfer",
        "aspirate",
        "dispense",
        "use_channels",
    }
)  # "setup" added spec 260903 §12.1/AC-12.1(ii): P5's reset-method name must be read from PLR, not typed.
_TIPSTATE_SRC_FILES = (
    PLR_SEMA_ROOT / "src" / "plr_sema" / "check" / "tipstate.py",
    PLR_SEMA_ROOT / "src" / "plr_sema" / "derive" / "receiver_state.py",
)


def _docstring_constant_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                ids.add(id(first.value))
    return ids


def _scan_hand_typed_literals(source: str, filename: str) -> list[str]:
    tree = ast.parse(source, filename=filename)
    docstring_ids = _docstring_constant_ids(tree)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in _FORBIDDEN_LITERALS:
            if id(node) in docstring_ids:
                continue
            offenders.append(f"{filename}:{node.lineno}: {node.value!r}")
    return offenders


def test_ac_10_9_no_hand_typed_plr_names_ast_scan() -> None:
    """Sub-assertion 3: an AST LITERAL scan (not grep) of the tip-state
    modules under `plr_sema/src/` finds none of the six forbidden names as
    an `ast.Constant` string value -- reusing `test_verdict.py`'s own
    docstring-exclusion mechanism (a bare-``ast.walk`` `grep` cannot skip
    docstrings/comments; this scan can and does). The docstring-exclusion
    itself is demonstrated on a synthetic fixture that DOES put one of the
    forbidden names in a docstring, per §10.7's own note that this is what
    must be tested.
    """
    # -- The exclusion itself: a docstring containing "has_tip" is NOT a
    # violation; the identical string as a real string constant IS.
    docstring_case = (
        'def _f():\n'
        '    """This talks about has_tip in prose."""\n'
        '    return 1\n'
    )
    assert _scan_hand_typed_literals(docstring_case, "<synthetic:docstring>") == []

    literal_case = "X = 'has_tip'\n"
    offenders = _scan_hand_typed_literals(literal_case, "<synthetic:literal>")
    assert len(offenders) == 1

    module_docstring_case = '"""has_tip appears in the MODULE docstring."""\nY = 1\n'
    assert _scan_hand_typed_literals(module_docstring_case, "<synthetic:module-docstring>") == []

    # -- The real scan.
    all_offenders: list[str] = []
    for path in _TIPSTATE_SRC_FILES:
        all_offenders.extend(_scan_hand_typed_literals(path.read_text(encoding="utf-8"), str(path)))
    assert all_offenders == [], f"hand-typed PLR name(s) found: {all_offenders}"


# ---------------------------------------------------------------------------
# AC-10.10
# ---------------------------------------------------------------------------


def test_ac_10_10_family_selection_is_published(contracts_json: str) -> None:
    payload = json.loads(contracts_json)
    lh = payload["receiver_state"]["LiquidHandler"]
    contracts = payload["contracts"]

    from plr_sema.derive.receiver_state import ReceiverState, compute_tip_families

    rs = ReceiverState(
        channel_attr=lh["channel_attr"],
        tracker_class=lh["tracker_class"],
        tracker_module="pylabrobot.resources.tip_tracker",
        bool_view_attr=lh["bool_view"]["attr"],
        bool_view_field=lh["bool_view"]["field"],
        true_when=lh["bool_view"]["true_when"],
        state_fields=tuple(lh["state_fields"]),
        effects=lh["effects"],
        channel_default_param=lh["channel_default_param"],
        channel_default_disablers=tuple(lh["channel_default_disablers"]),
        tip_state_exceptions=tuple(lh["tip_state_exceptions"]),
    )
    families = compute_tip_families(contracts, receiver_class="LiquidHandler", receiver_state=rs)
    assert families.tip_loading and families.tip_requiring and families.tip_dropping
    assert "pick_up_tips" in families.tip_loading
    assert "aspirate" in families.tip_requiring
    assert "drop_tips" in families.tip_requiring and "drop_tips" in families.tip_dropping


# ---------------------------------------------------------------------------
# AC-12.1(i) -- the reset rule is derived and published, not asserted
# (spec 260903 §12.1). Sub-assertions (ii)/(iii)/(iv) are covered by this
# module's extended `_FORBIDDEN_LITERALS` scan (ii) and by test_derive.py
# (iii, iv), which exercise `reset_rule_candidates`/`derive_receiver_states`
# directly rather than through the shipped artifact.
# ---------------------------------------------------------------------------

GAP_LEDGER_JSON_PATH = REPO_ROOT / "plr-sema" / "data" / "gap_ledger.json"


def test_ac_12_1_i_entry_reset_is_derived_and_published(contracts_json: str) -> None:
    payload = json.loads(contracts_json)
    lh = payload["receiver_state"]["LiquidHandler"]
    assert lh["entry_reset"] == {"method": "setup", "post": "no_tip"}

    ledger = json.loads(GAP_LEDGER_JSON_PATH.read_text(encoding="utf-8"))
    assert ledger["tip_state"]["LiquidHandler"]["entry_reset"] == {"method": "setup", "post": "no_tip"}


# ---------------------------------------------------------------------------
# AC-12.2 -- entry state fires only on an OBSERVED reset, both directions
# (spec 260903 §12.1.5).
# ---------------------------------------------------------------------------


def test_ac_12_2_a_will_fail_after_observed_setup(contracts_json: str) -> None:
    """(a): `setup()` then `aspirate(use_channels=[0])` -- exactly one
    `WILL_FAIL` `Finding` in the whole report, sited at the bridged
    `TipTracker.get_tip` `NoTipError` guard. `setup`'s own guard (`if
    self.setup_finished: raise RuntimeError`, A-RESET-ONCE) does not parse
    as a tip-state atom and so still emits its own (`UNKNOWN`,
    `guard_predicate_unparsed`) finding on `op_1` -- filtering to
    `Verdict.WILL_FAIL` (as (b)/(c) below already do for their own
    zero-count assertions) is what "exactly one" is checked over, not a
    bare `len(report.findings) == 1`.
    """
    report = _check("setup_then_aspirate_graph", contracts_json)
    will_fail = [f for f in report.findings if f.verdict is Verdict.WILL_FAIL]
    assert len(will_fail) == 1
    (finding,) = will_fail
    assert finding.operation_id == "op_2"
    assert finding.category == "precondition_state"
    assert finding.plr_site == _GET_TIP_SITE
    assert report.verdict is Verdict.WILL_FAIL


def test_ac_12_2_b_no_setup_stays_unknown(contracts_json: str) -> None:
    """(b), the stub-defeating half: the identical `aspirate` with no
    preceding `setup()` yields zero `WILL_FAIL` and zero `SAFE` findings
    over the whole report -- an implementation that seeds `NO_TIP` at
    graph entry (instead of only on an observed reset `CALL`) would pass
    (a) and fail this.
    """
    report = _check("aspirate_no_setup_graph", contracts_json)
    non_tip = _excluding_now_decided_non_tip_guards(report.findings)
    assert not [f for f in non_tip if f.verdict is Verdict.WILL_FAIL]
    assert not [f for f in non_tip if f.verdict is Verdict.SAFE]
    assert report.verdict is Verdict.UNKNOWN


def test_ac_12_2_c_stale_contract_table_degrades_without_raising(contracts_json: str) -> None:
    """(c): fixture (a) against a contract table with no `entry_reset` key
    must not raise, and must degrade to (b)'s behaviour for the tip-state
    question -- read via `.get()` with an empty default (AC-12.2's own
    "fires only on an observed reset" claim depends on this NOT crashing
    on a pre-increment table). Fixture (a) additionally contains the
    `setup` operation itself (deleted in (b)), so the two reports are not
    byte-identical as a whole; the equality this asserts is scoped to (i)
    the report-level verdict and (ii) the `aspirate` operation's own
    findings, which is the tip-state-relevant surface (b) has no
    counterpart operation to diverge on.
    """
    payload = json.loads(contracts_json)
    del payload["receiver_state"]["LiquidHandler"]["entry_reset"]
    stale_contracts_json = json.dumps(payload)

    report_a_stale = check_graph(
        (FIXTURES / "setup_then_aspirate_graph.json").read_text(encoding="utf-8"), stale_contracts_json
    )  # must not raise
    report_b = _check("aspirate_no_setup_graph", contracts_json)

    assert report_a_stale.verdict is Verdict.UNKNOWN
    assert report_b.verdict is Verdict.UNKNOWN

    def _aspirate_shape(report: AnalysisReport) -> list[tuple[str, str, str, str]]:
        return sorted(
            (f.verdict.value, f.category, f.reason, f.detail) for f in _findings_for(report, "op_2")
        )

    assert _aspirate_shape(report_a_stale) == _aspirate_shape(report_b)


# ---------------------------------------------------------------------------
# Spec 260903 §12.3 (region semantics for a region with a proved trip),
# AC-12.10 through AC-12.14. `CONTRACTS_PAYLOAD` below is the parsed form of
# `contracts_json`, needed to cross-check a SAFE finding's `detail` against
# the real, published guard condition (AC-12.14(iii)).
# ---------------------------------------------------------------------------

_ITERATION_RE = re.compile(r"^iteration (\d+): (.*)$", re.DOTALL)


def _iteration_of(detail: str) -> tuple[int | None, str]:
    """Split `_with_iteration`'s `"iteration N: <original detail>"` prefix
    back out. Returns `(None, detail)` unchanged for a finding with no
    iteration label (fixpoint findings, or any finding outside an unrolled
    loop) -- `check/__init__.py::_with_iteration` is the producer this
    inverts.
    """
    m = _ITERATION_RE.match(detail)
    if m is None:
        return None, detail
    return int(m.group(1)), m.group(2)


@pytest.fixture(scope="module")
def contracts_payload(contracts_json: str) -> dict:
    return json.loads(contracts_json)


def _all_real_guard_conditions(contracts_payload: dict) -> set[str]:
    """The union of every guard/channel_guard `condition` across the WHOLE
    contract table -- a SAFE finding's `detail` need not come from the
    checked operation's OWN contract entry (a bridged `channel_guards`
    condition is sited in a DIFFERENT class, e.g. `TipTracker`, than the
    receiver's own `LiquidHandler.<method>` key), so this checks "is a
    real, non-fabricated condition somewhere in the table", not "is this
    exact operation's own condition".
    """
    conditions: set[str] = set()
    for contract in contracts_payload["contracts"].values():
        for guard in (*contract.get("guards", ()), *contract.get("channel_guards", ())):
            condition = guard.get("condition")
            conditions.add(condition if condition is not None else "<unconditional>")
    return conditions


# ---------------------------------------------------------------------------
# AC-12.10 -- L1 bounded unrolling is precise on the round-1 counterexample.
# ---------------------------------------------------------------------------


def test_ac_12_10_bounded_unroll_precise_on_repeated_pickup(contracts_json: str) -> None:
    report = _check("loop_double_pickup_graph", contracts_json)
    op3 = _findings_for(report, "op_3")  # pick_up_tips, inside the trip=2 LOOP

    own_site_will_fail = [
        f
        for f in op3
        if f.verdict is Verdict.WILL_FAIL and f.category == "precondition_state" and f.plr_site == _PICK_UP_TIPS_SITE
    ]
    assert len(own_site_will_fail) == 1, (
        "exactly one WILL_FAIL sited at pick_up_tips:535 -- AC-12.10's literal pin "
        "(a second, ADDITIVE WILL_FAIL at the bridged TipTracker.add_tip:92 site is "
        "expected too, per this module's docstring's disclosed AC-10.1 deviation, and "
        "does not violate this count, which is scoped to the :535 site specifically)"
    )
    (finding,) = own_site_will_fail
    iteration, _detail = _iteration_of(finding.detail)
    assert iteration == 2, "the detail must name iteration 2"

    # The first iteration's pick_up_tips guard is SAFE.
    iteration_1_safe = [
        f
        for f in op3
        if f.verdict is Verdict.SAFE and f.plr_site == _PICK_UP_TIPS_SITE and _iteration_of(f.detail)[0] == 1
    ]
    assert iteration_1_safe, "iteration 1's own :535 guard must be SAFE"

    assert report.verdict is Verdict.WILL_FAIL


# ---------------------------------------------------------------------------
# AC-12.11 -- the L2 fixpoint emits findings from the final pass only.
# ---------------------------------------------------------------------------


def test_ac_12_11_fixpoint_emits_final_pass_only(contracts_json: str) -> None:
    report = _check("while_alternating_graph", contracts_json)
    op3 = _excluding_now_decided_non_tip_guards(_findings_for(report, "op_3"))  # pick_up_tips, inside a real LOOP(trip=None)

    assert not any(f.verdict is Verdict.WILL_FAIL for f in op3), (
        "a pass-1 finding (evaluated against NO_TIP alone, before the head state "
        "widens to TOP at the fixpoint) would be a definite-failure claim about a "
        "program that may take a different path on a later real iteration -- an "
        "implementation that emits it fails this assertion"
    )
    assert not any(f.verdict is Verdict.SAFE for f in op3)
    assert any(f.reason == "channel_state_unknown" for f in op3), (
        "the STABLE (final) pass sees the joined TOP head state -- own+bridged "
        "guards resolve to channel_state_unknown, not silence"
    )
    assert report.verdict is Verdict.UNKNOWN
    # check_ir must not raise and must converge within K passes -- reaching
    # this assertion at all (rather than a hang or a RecursionError) is the
    # convergence/no-raise half of this AC.


# ---------------------------------------------------------------------------
# AC-12.12 -- the tail widen fires at K.
# ---------------------------------------------------------------------------


def test_ac_12_12_tail_widen_at_k(contracts_json: str) -> None:
    report = _check("trip_20_graph", contracts_json)
    op3 = _findings_for(report, "op_3")  # pick_up_tips, inside the trip=20 LOOP

    own_site = [f for f in op3 if f.plr_site == _PICK_UP_TIPS_SITE]
    iterations_seen = {_iteration_of(f.detail)[0] for f in own_site}
    assert iterations_seen == set(range(1, 9)), (
        f"findings for iterations 1 through 8 only, none for 9 through 20; got {sorted(iterations_seen)}"
    )

    # Every receiver in the region reads TOP immediately after the region's
    # END: the following aspirate on the same receiver yields
    # channel_state_unknown, not a definite verdict.
    op4 = _findings_for(report, "op_4")  # aspirate, AFTER the region
    tip_family_op4 = [f for f in op4 if f.reason in ("channel_state_unknown",) or f.plr_site == _GET_TIP_SITE]
    assert tip_family_op4, "op_4 must carry a tip-family finding to assert against"
    assert all(f.verdict is Verdict.UNKNOWN and f.reason == "channel_state_unknown" for f in tip_family_op4)
    assert not any(f.verdict in (Verdict.SAFE, Verdict.WILL_FAIL) and f.plr_site == _GET_TIP_SITE for f in op4)


# ---------------------------------------------------------------------------
# AC-12.14 -- regions widen-or-join, never construct SAFE without an
# evaluated guard, and never widen a call that owns no region.
# ---------------------------------------------------------------------------


def test_ac_12_14_i_ii_branch_arm_state_and_post_join(contracts_json: str) -> None:
    report = _check("branch_join_graph", contracts_json)

    # (i) the true arm's guard evaluates against the true arm's own state
    # and can be SAFE.
    op3 = _findings_for(report, "op_3")  # pick_up_tips, the BRANCH's true arm
    true_arm_safe = [f for f in op3 if f.verdict is Verdict.SAFE and f.plr_site == _PICK_UP_TIPS_SITE]
    assert true_arm_safe, "the true arm's own pick_up_tips guard must be SAFE (entry state is NO_TIP post-setup)"

    # (ii) an operation after the region reads the join and yields
    # channel_state_unknown, not SAFE.
    op4 = _findings_for(report, "op_4")  # aspirate, AFTER the region
    get_tip = [f for f in op4 if f.plr_site == _GET_TIP_SITE]
    assert get_tip
    assert all(f.verdict is Verdict.UNKNOWN and f.reason == "channel_state_unknown" for f in get_tip), (
        "join(HAS_TIP from the true arm, NO_TIP unchanged from the missing false arm) == TOP"
    )
    assert not any(f.verdict is Verdict.SAFE for f in get_tip)


@pytest.mark.parametrize(
    "fixture_name",
    [
        "loop_double_pickup_graph",
        "trip_20_graph",
        "branch_join_graph",
        "call_before_unowned_region_graph",
        # while_alternating_graph is deliberately excluded: its whole point
        # (AC-12.11) is that the final fixpoint pass sees a widened (TOP)
        # head state and therefore emits NO SAFE finding at all -- there is
        # nothing for this check to exercise there.
    ],
)
def test_ac_12_14_iii_safe_findings_carry_a_real_guard_condition(
    fixture_name: str, contracts_json: str, contracts_payload: dict
) -> None:
    """(iii): every Finding whose verdict is SAFE carries a non-empty
    detail equal to a guard condition present in the contract table -- the
    mechanical form of "no SAFE constructed without an evaluated guard".
    Checked over every §12.3 region fixture that produces a SAFE finding at
    all, per the AC's own "over all region fixtures" scope.
    """
    report = _check(fixture_name, contracts_json)
    safe = [f for f in report.findings if f.verdict is Verdict.SAFE]
    assert safe, f"{fixture_name} must produce at least one SAFE finding to exercise this check"
    real_conditions = _all_real_guard_conditions(contracts_payload)
    for finding in safe:
        assert finding.detail, f"{finding} has empty detail"
        _iteration, condition = _iteration_of(finding.detail)
        assert condition in real_conditions, (
            f"{finding}'s detail {condition!r} is not a real guard condition anywhere in the contract table"
        )


def test_ac_12_14_iv_call_before_unowned_region_uses_real_state(contracts_json: str) -> None:
    report = _check("call_before_unowned_region_graph", contracts_json)
    op2 = _findings_for(report, "op_2")  # pick_up_tips on "lh", immediately before a region it does not own

    safe_at_535 = [f for f in op2 if f.verdict is Verdict.SAFE and f.plr_site == _PICK_UP_TIPS_SITE]
    assert len(safe_at_535) == 1, "exactly one SAFE finding sited at pick_up_tips:535"
    assert not any(f.reason == "channel_state_unknown" for f in op2), (
        "no channel_state_unknown for op_2 -- its real pre-call state (NO_TIP from the "
        "reset at the top of the graph) is exact, not TOP; the retired stale compensation "
        "would have widened it to TOP purely for sitting before a region it does not own"
    )
    assert report.verdict is Verdict.WILL_FAIL, (
        "op_4 (inside the region, a DIFFERENT receiver) still produces its own WILL_FAIL "
        "on iteration 2 -- unrelated to op_2's own correctness, asserted here only to "
        "confirm the fixture's region half behaves as AC-12.10 predicts"
    )


# ---------------------------------------------------------------------------
# AC-13.15 -- delegate-call literal channel binding (spec §13.5, P9,
# backlog #4946). Sub-assertion (iii) is covered above by this module's own
# extended `_FORBIDDEN_LITERALS` (next to AC-10.9, whose scan mechanism it
# reuses). (i)'s derived-binding assertion and its negative-fixture set live
# in test_derive.py, next to `compute_delegate_channel_bindings` itself;
# this section covers (ii) (binding a channel grants no effect) and the
# rule-4 ordering half of (i) (disabler poisoning checked AFTER rules 2/3).
# ---------------------------------------------------------------------------


def test_ac_13_15_ii_transfer_safe_then_following_call_widens(contracts_json: str) -> None:
    """(ii): `setup()`, `pick_up_tips(use_channels=[0])`, `transfer(...)`,
    then `aspirate(use_channels=[0])`. `transfer`'s own bridged guard
    (sited at `TipTracker.get_tip:65`) evaluates via P9's `bound_channels`
    (`[0]`, bound through `aspirate`'s arity-default idiom) against the
    HAS_TIP state `pick_up_tips` just established on channel 0 -> SAFE.
    The FOLLOWING `aspirate` must NOT see that same HAS_TIP state carried
    through unchanged -- E2 is not extended (binding a channel licenses
    reading a precondition, never a post-state), so `transfer`'s own
    `channel_effect` stays `None` (E3) and P9's own widen fires instead
    (this module's docstring's "E4.2 still widens the receiver after a
    delegate-only method"), landing on `channel_state_unknown`.
    """
    report = _check("transfer_after_pickup_graph", contracts_json)
    op3 = _findings_for(report, "op_3")  # transfer
    op4 = _findings_for(report, "op_4")  # aspirate, immediately after

    safe_at_get_tip = [f for f in op3 if f.verdict is Verdict.SAFE and f.plr_site == _GET_TIP_SITE]
    assert len(safe_at_get_tip) == 1, (
        "transfer must carry exactly one SAFE finding for the bridged NoTipError guard, "
        "sited at TipTracker.get_tip:65 -- the P9 bound_channels evaluation"
    )
    # 260904 (increment 6, T31): scoped to the tip-family's own bridged
    # site, not "no WILL_FAIL anywhere on this operation" -- the fixture's
    # `transfer(...)` call passes neither `source_vol` nor `target_vols`,
    # which `plr_sema.check.predicate`'s evaluator now correctly reports as
    # a genuine, decidable WILL_FAIL at `:1340` (`transfer` really would
    # raise `TypeError("Must specify either source_vol or target_vols")`
    # against this exact call) -- a fact about `transfer`'s OWN argument
    # guard this fixture never exercised before T31, unrelated to tip
    # typestate, which this test is scoped to.
    assert not any(f.verdict is Verdict.WILL_FAIL for f in op3 if f.plr_site == _GET_TIP_SITE)

    unknown_at_get_tip = [
        f for f in op4 if f.verdict is Verdict.UNKNOWN and f.reason == "channel_state_unknown" and f.plr_site == _GET_TIP_SITE
    ]
    assert unknown_at_get_tip, (
        "the aspirate immediately after transfer must yield channel_state_unknown at "
        "TipTracker.get_tip:65 -- an implementation that extended E2 would instead see "
        "the HAS_TIP state pick_up_tips left behind and emit SAFE here, which is exactly "
        "the stub this sub-assertion defeats"
    )
    assert not any(f.verdict is Verdict.WILL_FAIL for f in op4 if f.plr_site == _GET_TIP_SITE)


def test_ac_13_15_i_disabler_checked_after_rules_2_and_3(contracts_json: str) -> None:
    """(i)'s ordering half, at check time: inserting a P3b disabler call
    (`use_channels`, the SAME real disabler AC-10.6 already exercises)
    between `pick_up_tips` and `transfer` must poison the receiver and
    suppress the `bound_channels`-driven SAFE finding `transfer` would
    otherwise carry (the companion positive case is
    `test_ac_13_15_ii_transfer_safe_then_following_call_widens`, above) --
    despite `bound_channels` having already been computed (rules 2/3, at
    derive time) with a real, non-Top binding. An implementation that
    checked the disabler FIRST (or skipped it entirely for `channel_guards`)
    would still emit the SAFE finding here; this is the stub it defeats.
    """
    graph = _graph("transfer_after_pickup_graph")
    graph["operations"].insert(
        2,
        {
            "arguments": {},
            "condition_expr": None,
            "creates_state": [],
            "depends_on_params": [],
            "false_branch": [],
            "foreach_body": [],
            "foreach_source": None,
            "id": "op_1b",
            "line_number": 0,
            "method_name": "use_channels",
            "node_type": "static",
            "preconditions": [],
            "receiver_type": "LiquidHandler",
            "receiver_variable": "lh",
            "true_branch": [],
        },
    )
    graph["execution_order"] = ["op_1", "op_2", "op_1b", "op_3", "op_4"]
    report = check_graph(json.dumps(graph), contracts_json)
    op3 = _findings_for(report, "op_3")  # transfer, now poisoned

    assert not any(f.plr_site == _GET_TIP_SITE for f in op3), (
        "a poisoned receiver must yield NO finding at all for the bound-channels bridged "
        "guard (channels_for_call also poisoned -> None, same as a guard with no "
        "bound_channels) -- not a SAFE, and not a WILL_FAIL"
    )
    # 260904 (increment 6, T31): scoped to the tip-family's own bridged
    # site -- see the sibling test above for why a WILL_FAIL elsewhere on
    # this same operation (transfer's own `:1340` argument guard) is a
    # correct, unrelated finding this fixture's call genuinely earns.
    assert not any(f.verdict is Verdict.WILL_FAIL for f in op3 if f.plr_site == _GET_TIP_SITE)
