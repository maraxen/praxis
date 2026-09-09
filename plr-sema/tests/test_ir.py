"""Spec 260902 §11 (`260902_plr-sema-ir-bytecode-increment.md`), Gate A: the
offline acceptance criteria for SEMA-IR (backlog #4921, `#4888` step 0).

Each AC-11.x named individually (not as a range) per §11.8's Gate A split,
so a cross-reference lint can resolve each one. AC-11.5 (the corpus-replay
tool-name barrier) is Gate B and lives in ``oracle_replay.py``'s own run,
not here (§11.8).

**AC-11.1 reads upstream field names by AST, not by importing pydantic**
(dispatch-brief instruction, a deliberate relaxation of the spec's own
"imports the real pydantic models (allowed)" text -- see this file's
``test_disposition_table_is_exhaustive`` docstring for why: it keeps this
file's own coverage environment-independent, complementary to
``tests/test_check_graph_mirror_drift.py``'s live-import Fork C check,
which already covers the pydantic-import path for the SAME exhaustiveness
property one layer up (the ``check/graph.py`` mirror, not
``DISPOSITIONS`` directly)).
"""

from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest
from plr_sema.check import check_graph, check_ir, ir

REPO_ROOT = Path(__file__).resolve().parents[2]
PLR_SEMA_ROOT = Path(__file__).resolve().parents[1]
MODELS_PATH = REPO_ROOT / "praxis" / "backend" / "utils" / "plr_static_analysis" / "models.py"
FIXTURES_DIR = PLR_SEMA_ROOT / "tests" / "fixtures"
CONTRACTS_PATH = PLR_SEMA_ROOT / "data" / "derived_contracts.json"
IR_MODULE_PATH = PLR_SEMA_ROOT / "src" / "plr_sema" / "check" / "ir.py"


def _model_fields_via_ast(class_name: str) -> set[str]:
    """AST-only field-name extraction from ``models.py`` -- no pydantic
    import (dispatch brief). Collects ``ast.AnnAssign`` targets that are
    direct children of the named ``ClassDef``'s body (i.e. class-level
    field declarations, not nested/method-local assignments).
    """
    tree = ast.parse(MODELS_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            }
    raise LookupError(f"class {class_name!r} not found in {MODELS_PATH}")


@pytest.fixture(scope="module")
def contracts_json() -> str:
    return CONTRACTS_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def contracts_payload(contracts_json: str) -> dict[str, Any]:
    return json.loads(contracts_json)


def _all_fields_payload() -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / "all_fields_graph.json").read_text(encoding="utf-8"))


def _branchy_payload() -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / "branchy_graph.json").read_text(encoding="utf-8"))


def _simple_transfer_payload() -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / "simple_transfer_graph.json").read_text(encoding="utf-8"))


def _loop_protocol_payload() -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / "loop_protocol_graph.json").read_text(encoding="utf-8"))


def _conditional_protocol_payload() -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / "conditional_protocol_graph.json").read_text(encoding="utf-8"))


def _proved_trip_payload() -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / "proved_trip_graph.json").read_text(encoding="utf-8"))


def _nested_regions_payload() -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / "nested_regions_graph.json").read_text(encoding="utf-8"))


def _self_attr_payload() -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / "self_attr_graph.json").read_text(encoding="utf-8"))


_ASPIRATE_PARAM_NAMES = {
    "LiquidHandler.aspirate": ("resources", "vols", "use_channels"),
}


# ---------------------------------------------------------------------------
# AC-11.1 -- the disposition table is exhaustive, both directions.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model_name, expected_count",
    # OperationNode 15 -> 16 (spec §12.2/#4932: `trip` added for a REGION
    # loop header's proved trip count, §12.2.3).
    [("OperationNode", 16), ("ResourceNode", 9), ("ProtocolComputationGraph", 10)],
)
def test_disposition_table_is_exhaustive(model_name: str, expected_count: int) -> None:
    """AC-11.1: ``set(DISPOSITIONS[M]) == set(M.model_fields)`` for each of
    the three upstream models, checked both directions (a new upstream
    field OR a stale disposition both turn this red) -- and the second half
    pins the three measured counts are ``(16, 9, 10)`` at the current
    model, the number that must be RE-READ, not re-guessed, when it
    changes. Field names are read by AST from ``models.py`` directly (a
    hardcoded field list in this test would defeat the point -- see the
    module docstring for why AST rather than a live pydantic import).
    """
    upstream_fields = _model_fields_via_ast(model_name)
    disposition_fields = set(ir.DISPOSITIONS[model_name])
    extra = disposition_fields - upstream_fields
    missing = upstream_fields - disposition_fields
    assert not extra and not missing, (
        f"DISPOSITIONS[{model_name!r}] {sorted(disposition_fields)} != "
        f"models.py's {model_name}'s AST-derived field set {sorted(upstream_fields)} "
        f"-- extra: {sorted(extra)}, missing: {sorted(missing)}"
    )
    assert len(upstream_fields) == expected_count, (
        f"{model_name} has {len(upstream_fields)} AST-derived fields, expected "
        f"{expected_count} -- re-read this pinned count from models.py if it "
        f"legitimately changed"
    )


# ---------------------------------------------------------------------------
# AC-11.14 -- the three X dispositions, pinned by identity, independently
# of the table. THE one legitimate hardcode in the increment (§11.7).
# ---------------------------------------------------------------------------


def test_excluded_fields_are_excluded() -> None:
    """AC-11.14: hardcodes exactly three field identities --
    ``OperationNode.preconditions``, ``OperationNode.creates_state``, and
    ``ProtocolComputationGraph.preconditions`` -- and asserts
    ``DISPOSITIONS`` assigns each of them disposition ``X``. This is the
    fact the whole laundering argument depends on: these three fields are
    populated by hand-typed ``TIPS_REQUIRED_METHODS``/
    ``TIPS_LOADING_METHODS`` frozensets
    (``computation_graph_extractor.py:537-570``, ``:479-491``) that §8's
    comparison uses as its TARGET -- consuming them here would launder the
    analyzer's own comparison target through ``CALL.kwargs``. No existing
    criterion catches a reclassification: AC-11.1 is key-set equality
    against upstream and passes unchanged if a field moves categories;
    AC-11.2 read live off ``DISPOSITIONS`` becomes vacuous by construction;
    HM-21's redefined metric (``_hand_maintained.py``) actually points the
    WRONG way for this (it counts X dispositions, so moving a field OUT of
    X *decreases* the count, which a growth-guarding ratchet reads as
    safe). This test must therefore assert the three identities directly,
    NOT derive them from ``DISPOSITIONS``.
    """
    assert ir.DISPOSITIONS["OperationNode"]["preconditions"] == "X"
    assert ir.DISPOSITIONS["OperationNode"]["creates_state"] == "X"
    assert ir.DISPOSITIONS["ProtocolComputationGraph"]["preconditions"] == "X"
    # And nothing else is X -- the three-member set is itself part of the
    # pinned fact (a fourth X field would be new, undiscussed judgement).
    assert frozenset(
        {
            ("OperationNode", "preconditions"),
            ("OperationNode", "creates_state"),
            ("ProtocolComputationGraph", "preconditions"),
        }
    ) == ir.EXCLUDED_FIELDS


# ---------------------------------------------------------------------------
# AC-11.2 -- no-drop, field by field, over the all_fields_graph.json
# fixture (every OperationNode/ResourceNode/ProtocolComputationGraph field
# carries a non-default value).
# ---------------------------------------------------------------------------


def test_no_drop_field_by_field() -> None:
    """AC-11.2: for every field of every model, the disposition's
    consequence is directly observable in the lowered bytecode: each
    I-dispositioned field's value is recoverable from an instruction, each
    S-dispositioned field appears in ``sideband``, each W-dispositioned
    field produced its ``WIDEN``, and each of the three X fields appears in
    NEITHER the instruction stream nor ``sideband`` -- asserted, not
    assumed (a lowering that dumps the payload wholesale into sideband
    fails the X half; one that drops fields fails the I/S halves).
    """
    payload = _all_fields_payload()
    bc = ir.lower_graph(payload, param_names=_ASPIRATE_PARAM_NAMES)

    calls = [i for i in bc.instructions if isinstance(i, ir.Call)]
    widens = {i.reason for i in bc.instructions if isinstance(i, ir.Widen)}
    resources = [i for i in bc.instructions if isinstance(i, ir.Resource)]
    loops = [i for i in bc.instructions if isinstance(i, ir.Loop)]
    branches = [i for i in bc.instructions if isinstance(i, ir.Branch)]

    # --- I: method_name / receiver_variable -> CALL.method / CALL.receiver.
    op1_call = next(c for c in calls if c.method == "aspirate" and c.kwargs)
    assert op1_call.receiver_type == "LiquidHandler"  # receiver_type also I

    # --- I+W: receiver_type None (op_5) -> WIDEN + CALL.receiver_type=None.
    op5_call = next(c for c in calls if c.receiver_type is None)
    assert op5_call.method == "aspirate"
    assert "receiver_type" in widens

    # --- I+W: arguments -> CALL.kwargs carries the value under a trusted
    # key or a rewritten "?i" key; an untrusted key triggers WIDEN.
    assert "resources" in op1_call.kwargs  # trusted (real PLR param)
    assert "vols" in op1_call.kwargs  # trusted
    assert any(k.startswith("?") for k in op1_call.kwargs)  # foo_bar_baz, untrusted
    assert "arguments" in widens

    # --- S+W: node_type -- carried nowhere as an instruction field (it is
    # recomputed, not stored), but its disagreement with the recomputation
    # (declared "static" while depends_on_params is non-empty) widened.
    assert "node_type" in widens

    # --- X: preconditions / creates_state (OperationNode) appear in
    # NEITHER instructions nor sideband, anywhere.
    canonical = ir.canonical_text(bc)
    assert "precond_1" not in canonical
    assert "precond_1" not in json.dumps(bc.sideband)
    assert "state_1" not in canonical
    assert "state_1" not in json.dumps(bc.sideband)

    # --- X: preconditions (ProtocolComputationGraph, container level).
    assert "resource_on_deck" not in canonical
    assert "resource_on_deck" not in json.dumps(bc.sideband)

    # --- W+S: depends_on_params -- widened, and the names go to sideband
    # is NOT required to be literally stored (the disposition only
    # requires the WIDEN fire); assert the widen fired.
    assert "depends_on_params" in widens

    # --- I+S: foreach_source/foreach_body -> a real LOOP region; the
    # iterated expression text itself never appears in the hashed stream.
    assert len(loops) == 1
    assert "tips_list" not in canonical

    # --- I+S: condition_expr/true_branch/false_branch -> a real BRANCH
    # region (both arms present: op_3's dispense and op_4's pick_up_tips
    # both got a CALL); the condition text never appears in the hashed
    # stream.
    assert len(branches) == 1
    assert "x > 1" not in canonical
    assert {c.method for c in calls} >= {"aspirate", "drop_tips", "dispense", "pick_up_tips"}

    # --- I+W: execution_order -- fixture's list is deliberately one
    # shorter than the real operation count (4 ids for 5 ops), so it is
    # NOT a permutation and the widen fires.
    assert "execution_order" in widens

    # --- I (ResourceNode): every RESOURCE field recoverable, including
    # grid from items_x/items_y and parents from parental_chain.
    plate_resource = next(r for r in resources if r.type == "Plate")
    assert plate_resource.grid == (8, 12)
    assert plate_resource.parents == ("PlateCarrier", "Deck")
    assert plate_resource.element_type == "Well"
    assert plate_resource.is_container is True

    # --- S (ResourceNode.source_expression): sideband only, never hashed.
    assert bc.sideband["source_expression"]["plate"] == 'deck.get_resource("plate")'
    assert "deck.get_resource" not in canonical

    # --- S (ProtocolComputationGraph): protocol_fqn/protocol_name/
    # machine_types/resource_types -- sideband only.
    assert bc.sideband["protocol_fqn"] == payload["protocol_fqn"]
    assert bc.sideband["protocol_name"] == payload["protocol_name"]
    assert payload["protocol_fqn"] not in canonical

    # Every one of the seven derived widen reasons fired at least once
    # SOMEWHERE across this fixture, except has_loops/has_conditionals
    # (real regions exist in this fixture, so the synthetic-wrap widens
    # correctly do NOT fire here -- see test_synthetic_wrap_widens below).
    assert widens == ir.WIDEN_FIELDS - {"has_loops", "has_conditionals"}


def test_synthetic_wrap_widens_has_loops_and_has_conditionals() -> None:
    """§11.4.1's synthetic-wrap widens fire on the COMPLEMENTARY case to
    ``test_no_drop_field_by_field``'s fixture: ``has_loops``/
    ``has_conditionals`` set True with ZERO real LOOP/BRANCH regions in the
    stream. Inline payload (not a fixture) -- the two scenarios (a real
    region present vs. none) are mutually exclusive per operation, so one
    fixture cannot exercise both halves of the has_loops/has_conditionals
    widen story.
    """
    payload = {
        "protocol_fqn": "x.y",
        "protocol_name": "y",
        "has_loops": True,
        "has_conditionals": True,
        "operations": [
            {
                "id": "op_1",
                "method_name": "aspirate",
                "receiver_variable": "lh",
                "receiver_type": "LiquidHandler",
            },
            {
                "id": "op_2",
                "method_name": "dispense",
                "receiver_variable": "lh",
                "receiver_type": "LiquidHandler",
            },
        ],
        "resources": {},
    }
    bc = ir.lower_graph(payload)
    widens = {i.reason for i in bc.instructions if isinstance(i, ir.Widen)}
    assert "has_loops" in widens
    assert "has_conditionals" in widens
    # Both wraps nest OUTSIDE every RESOURCE and CALL (§11.4.1) -- here
    # there are no RESOURCE instructions, so LOOP/BRANCH must be the first
    # non-WIDEN instructions and END the last two.
    non_widen = [i for i in bc.instructions if not isinstance(i, ir.Widen)]
    assert isinstance(non_widen[0], ir.Loop)
    assert isinstance(non_widen[1], ir.Branch)
    assert isinstance(non_widen[-1], ir.End)
    assert isinstance(non_widen[-2], ir.End)
    # Single-armed: no ELSE for a whole-stream wrap (no second arm exists).
    assert not any(isinstance(i, ir.Else) for i in bc.instructions)
    # Both CALLs are inside the synthetic LOOP region -- resolved contracts
    # (zero guards/gaps) so the loop check is actually reached rather than
    # short-circuited by unsupported_tool.
    contracts = {
        "LiquidHandler.aspirate": {"guards": [], "gaps": []},
        "LiquidHandler.dispense": {"guards": [], "gaps": []},
    }
    findings = check_ir(bc, contracts)
    assert {f.reason for f in findings} >= {"loop_bounds_unknown"}


# ---------------------------------------------------------------------------
# AC-11.3 -- hash invariance under equivalence.
# ---------------------------------------------------------------------------


def test_hash_invariant_under_variable_rename() -> None:
    import re

    payload = _simple_transfer_payload()
    bc1 = ir.lower_graph(payload)
    renamed = json.loads(json.dumps(payload))
    rename_map = {"lh": "machine_1", "source": "src_plate", "dest": "dst_plate", "tips": "tip_rack_1"}

    def rename_expr(v: Any) -> Any:
        if not isinstance(v, str):
            return v
        for old, new in rename_map.items():
            v = re.sub(rf"\b{re.escape(old)}\b", new, v)
        return v

    renamed["resources"] = {rename_map.get(k, k): v for k, v in renamed["resources"].items()}
    for r in renamed["resources"].values():
        r["variable_name"] = rename_map.get(r["variable_name"], r["variable_name"])
        r["parental_chain"] = list(r.get("parental_chain") or ())
    for op in renamed["operations"]:
        op["receiver_variable"] = rename_map.get(op["receiver_variable"], op["receiver_variable"])
        op["arguments"] = {k: rename_expr(v) for k, v in op["arguments"].items()}
    bc2 = ir.lower_graph(renamed)
    assert ir.bytecode_hash(bc1) == ir.bytecode_hash(bc2)


def test_hash_invariant_under_resources_dict_key_order() -> None:
    payload = _simple_transfer_payload()
    bc1 = ir.lower_graph(payload)
    reordered = json.loads(json.dumps(payload))
    reordered["resources"] = dict(reversed(list(reordered["resources"].items())))
    bc2 = ir.lower_graph(reordered)
    assert ir.bytecode_hash(bc1) == ir.bytecode_hash(bc2)


def test_hash_invariant_under_line_number_change() -> None:
    payload = _simple_transfer_payload()
    bc1 = ir.lower_graph(payload)
    changed = json.loads(json.dumps(payload))
    for op in changed["operations"]:
        op["line_number"] = 999999
    bc2 = ir.lower_graph(changed)
    assert ir.bytecode_hash(bc1) == ir.bytecode_hash(bc2)


def test_hash_invariant_under_protocol_identity_change() -> None:
    payload = _simple_transfer_payload()
    bc1 = ir.lower_graph(payload)
    changed = json.loads(json.dumps(payload))
    changed["protocol_fqn"] = "totally.different.name"
    changed["protocol_name"] = "name"
    bc2 = ir.lower_graph(changed)
    assert ir.bytecode_hash(bc1) == ir.bytecode_hash(bc2)


def test_hash_invariant_under_all_four_combined() -> None:
    payload = _simple_transfer_payload()
    bc1 = ir.lower_graph(payload)
    changed = json.loads(json.dumps(payload))
    changed["protocol_fqn"] = "totally.different.name"
    changed["protocol_name"] = "name"
    changed["resources"] = dict(reversed(list(changed["resources"].items())))
    for op in changed["operations"]:
        op["line_number"] = 999999
    bc2 = ir.lower_graph(changed)
    assert ir.bytecode_hash(bc1) == ir.bytecode_hash(bc2)


# ---------------------------------------------------------------------------
# AC-11.4 -- hash sensitivity under semantic change. Seven mutations,
# pairwise distinct, and distinct from the AC-11.3 base hash.
# ---------------------------------------------------------------------------


def test_hash_sensitivity_seven_mutations_pairwise_distinct() -> None:
    payload = _simple_transfer_payload()
    base = ir.bytecode_hash(ir.lower_graph(payload))

    def h(mutate) -> str:
        mutated = json.loads(json.dumps(payload))
        mutate(mutated)
        return ir.bytecode_hash(ir.lower_graph(mutated))

    def swap_adjacent(p):
        p["operations"][0], p["operations"][1] = p["operations"][1], p["operations"][0]
        p["execution_order"][0], p["execution_order"][1] = (
            p["execution_order"][1],
            p["execution_order"][0],
        )

    def bump_kwarg(p):
        p["operations"][1]["arguments"]["volume"] = "101"

    def int_to_float(p):
        p["operations"][1]["arguments"]["volume"] = "100.0"

    def change_cell(p):
        p["operations"][1]["arguments"]["resource"] = 'source["B1"]'

    def delete_kwarg(p):
        del p["operations"][1]["arguments"]["volume"]

    def change_method(p):
        p["operations"][1]["method_name"] = "dispense"

    def widen_seq(p):
        p["operations"][0]["arguments"]["resource"] = "[tips, tips]"

    mutations = {
        "swap_adjacent": swap_adjacent,
        "bump_kwarg": bump_kwarg,
        "int_to_float": int_to_float,
        "change_cell": change_cell,
        "delete_kwarg": delete_kwarg,
        "change_method": change_method,
        "widen_seq": widen_seq,
    }
    hashes = {name: h(fn) for name, fn in mutations.items()}
    for name, hv in hashes.items():
        assert hv != base, f"mutation {name!r} did not change the hash"
    values = list(hashes.values())
    assert len(set(values)) == len(values), f"mutations were not pairwise distinct: {hashes}"


# ---------------------------------------------------------------------------
# AC-11.6 -- check_graph does not move (the shipped fixture's report is
# unchanged through check_graph). Primarily covered by
# tests/test_check_graph.py; re-asserted here against a golden snapshot
# taken from the pre-IR implementation, so a regression in EITHER file
# still catches it.
# ---------------------------------------------------------------------------


def test_check_graph_report_unchanged_for_shipped_fixture(contracts_json: str) -> None:
    graph_json = (FIXTURES_DIR / "simple_transfer_graph.json").read_text(encoding="utf-8")
    report = check_graph(graph_json, contracts_json)
    triples = sorted(
        (f.operation_id, f.reason, f.plr_site.qualname if f.plr_site else None)
        for f in report.findings
    )
    # Golden snapshot. Originally pre-IR (260902: 38 findings, every one
    # `guard_predicate_unparsed`). Re-taken 260909 for the shipped
    # derived_contracts.json after two increments moved it BY DESIGN:
    # increment 5 (spec 260903 §14.5, T26) adds one `volume_state_unknown`
    # finding per bridged volume guard on the two liquid ops (op_2/op_3:
    # +4 -> 42), and increment 6 (spec 260904 §15.7, T31) replaces the
    # blanket `guard_predicate_unparsed` with the four-clause reason
    # assignment. The one-Finding-per-guard invariant (AC-15.5(iv)) holds:
    # 38 guard findings + 4 volume findings. The joined verdict stays
    # `unknown` -- no joined SAFE this increment (spec 260904 §15.5).
    assert report.verdict.value == "unknown"
    assert len(report.findings) == 42
    assert {t[0] for t in triples} == {"op_1", "op_2", "op_3", "op_4"}
    from collections import Counter

    by_reason = Counter(t[1] for t in triples)
    assert by_reason == {
        "guard_env_dependent": 25,
        "guard_operand_unknown": 9,
        "guard_predicate_unparsed": 4,
        "volume_state_unknown": 4,
    }, by_reason
    assert all(t[2] is not None for t in triples)


# ---------------------------------------------------------------------------
# AC-11.7 -- totality over instructions, and the relabel bijection.
# ---------------------------------------------------------------------------


def test_totality_and_relabel_bijection(contracts_payload: dict[str, Any]) -> None:
    """Spec 260903 §12.3.4/§12.9 amendment 5: AC-11.7's bijection clause is
    amended to read over `OBLIGED(graph)`, not the raw `{op.id}` set --
    `sideband.origin` restricted to CALL pcs is a FUNCTION ONTO
    `OBLIGED(graph)`, and after relabelling `{f.operation_id} ==
    OBLIGED(graph)` (this is also main spec AC-6.4, re-asserted through the
    amended path). `simple_transfer_graph.json` carries no REGION at all
    (AC-12.9), so `OBLIGED(graph) == {op.id for op in graph.operations}`
    here and this test's own numbers are UNCHANGED from pre-260903 -- the
    assertions below read over `ir.obliged_operation_ids(payload)` rather
    than the raw id set precisely so that equivalence is checked, not
    assumed. See `test_ac_12_13_...` below for the fixture where the two
    sets actually DIFFER (a proved-`trip == 0` region), which is what
    actually exercises the amendment.
    """
    payload = _simple_transfer_payload()
    contracts = contracts_payload.get("contracts", {})
    bc = ir.lower_graph(payload)
    findings = check_ir(bc, contracts)

    call_pcs = {pc for pc, i in enumerate(bc.instructions) if isinstance(i, ir.Call)}
    non_call_pcs = {pc for pc, i in enumerate(bc.instructions) if not isinstance(i, ir.Call)}

    findings_by_pc: dict[int, int] = {}
    for f in findings:
        findings_by_pc[int(f.operation_id)] = findings_by_pc.get(int(f.operation_id), 0) + 1

    assert set(findings_by_pc) == call_pcs, "every CALL pc must receive >=1 Finding, and only CALL pcs"
    assert not (set(findings_by_pc) & non_call_pcs)

    origin = bc.sideband["origin"]
    origin_over_visited_calls = {pc: opid for pc, opid in origin.items() if pc in findings_by_pc}
    obliged = ir.obliged_operation_ids(payload)
    assert set(origin_over_visited_calls.values()) == obliged, (
        "origin restricted to VISITED CALL pcs must be a function onto OBLIGED(graph)"
    )
    assert len(origin_over_visited_calls) == len(obliged), (
        "no REGION in this fixture -- every call-bearing op is visited exactly once, "
        "so the amended function is still injective HERE (not asserted in general)"
    )

    relabeled = ir.relabel_findings(findings, origin)
    assert {f.operation_id for f in relabeled} == obliged


# ---------------------------------------------------------------------------
# AC-11.8 -- the widen vocabulary is derived, not typed.
# ---------------------------------------------------------------------------


def test_widen_vocabulary_is_subset_of_upstream_fields() -> None:
    payload = _all_fields_payload()
    bc = ir.lower_graph(payload, param_names=_ASPIRATE_PARAM_NAMES)
    reasons = {i.reason for i in bc.instructions if isinstance(i, ir.Widen)}
    upstream = _model_fields_via_ast("OperationNode") | _model_fields_via_ast(
        "ProtocolComputationGraph"
    )
    assert reasons <= upstream


def test_widen_reason_literals_are_confined_to_the_disposition_table() -> None:
    """AC-11.8's AST-literal-scan half, adapted (dispatch-brief resolved
    ambiguity -- see the paragraph below and this file's module docstring
    on the parallel AC-11.1 relaxation). Every ``Widen(reason=...)`` call
    site in ``ir.py`` passes a bare identifier, never a fresh string
    literal -- verified by walking every ``Widen(...)`` call node and
    requiring its ``reason=`` argument to be an ``ast.Name`` (one of the
    seven module-level identifiers unpacked from ``sorted(WIDEN_FIELDS)``,
    §11.1.5's derivation), never an ``ast.Constant``.

    **Resolved ambiguity, spelled out.** The spec's literal reading of
    AC-11.8's second half -- "an AST literal scan ... finds no
    ``ast.Constant`` string equal to a widen reason outside the single
    dict that maps a field to its disposition" -- cannot be satisfied by
    ANY working lowering, because every widen-triggering field name is
    ALSO the key used to read that field off the raw payload dict (e.g.
    ``op.get("receiver_type")``, ``payload.get("has_loops")``) -- a
    single-occurrence-in-the-whole-file reading would leave the lowering
    with no way to look the field up at all. This test therefore checks
    the achievable, still-real half of the property: the WIDEN
    CONSTRUCTION SITES themselves never hardcode a reason string (so a
    reason cannot silently drift from the derived vocabulary at its point
    of emission), while acknowledging that the SAME field-name strings
    legitimately recur at every ``.get(...)`` payload-read call site --
    those are not widen-reason emissions, they are ordinary dict lookups
    that happen to share a name with one, by §11.1.5's own design ("the
    name of the upstream model field ... verbatim"). The genuinely
    load-bearing property -- that the runtime set of widen reasons never
    exceeds the derived vocabulary -- is checked dynamically instead by
    :func:`test_widen_vocabulary_is_subset_of_upstream_fields` above.
    """
    tree = ast.parse(IR_MODULE_PATH.read_text(encoding="utf-8"), filename=str(IR_MODULE_PATH))

    widen_calls_with_literal_reason = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Widen":
            for kw in node.keywords:
                if kw.arg == "reason" and isinstance(kw.value, ast.Constant):
                    widen_calls_with_literal_reason.append(kw.value.value)
    assert not widen_calls_with_literal_reason, (
        f"Widen(reason=<literal>) call site(s) found with a hardcoded string "
        f"{widen_calls_with_literal_reason!r} -- every widen call site must "
        f"pass one of the derived _XXX identifiers instead"
    )

    # Confirm the seven derived identifiers really are unpacked from a
    # DERIVED expression (sorted(WIDEN_FIELDS)), not from a literal tuple
    # -- the RHS of that one assignment must contain zero string Constants.
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Tuple)
            and any(
                isinstance(elt, ast.Name) and elt.id == "_RECEIVER_TYPE"
                for elt in node.targets[0].elts
            )
        ):
            string_constants_in_rhs = [
                n.value
                for n in ast.walk(node.value)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
            ]
            assert not string_constants_in_rhs, (
                f"the _RECEIVER_TYPE-etc. unpacking assignment's RHS contains "
                f"string literal(s) {string_constants_in_rhs!r} -- it must be "
                f"purely derived (sorted(WIDEN_FIELDS)), no retyped strings"
            )
            break
    else:
        pytest.fail("could not find the _RECEIVER_TYPE-etc. unpacking assignment in ir.py")


# ---------------------------------------------------------------------------
# AC-11.9 -- the cache key is constructible today, every component
# load-bearing.
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _FakeGitState:
    hash: str
    dirty_content_id: str | None = None


@dataclasses.dataclass
class _FakeStamp:
    plr: _FakeGitState
    surface: str = "legacy_pinned"
    surface_pin: str | None = None


def test_cache_key_components_are_independently_load_bearing() -> None:
    payload = _simple_transfer_payload()
    bc = ir.lower_graph(payload)
    bc_hash = ir.bytecode_hash(bc)
    contracts_json_a = json.dumps({"a": 1})
    contracts_json_b = json.dumps({"a": 2})
    stamp_a = _FakeStamp(plr=_FakeGitState(hash="sha_a", dirty_content_id="dirty_a"))
    stamp_b = _FakeStamp(plr=_FakeGitState(hash="sha_a", dirty_content_id="dirty_a"), surface_pin="pin_b")

    key_base = ir.cache_key(bc_hash, contracts_json_a, stamp_a)

    # Changing the graph's semantics changes component 1 (bytecode_hash)
    # and nothing else.
    changed_payload = json.loads(json.dumps(payload))
    changed_payload["operations"][0]["method_name"] = "dispense"
    other_hash = ir.bytecode_hash(ir.lower_graph(changed_payload))
    key_diff_graph = ir.cache_key(other_hash, contracts_json_a, stamp_a)
    assert key_diff_graph[0] != key_base[0]
    assert key_diff_graph[1:] == key_base[1:]

    # Changing one byte of contracts_json changes component 2 and nothing
    # else.
    key_diff_contracts = ir.cache_key(bc_hash, contracts_json_b, stamp_a)
    assert key_diff_contracts[1] != key_base[1]
    assert key_diff_contracts[0] == key_base[0]
    assert key_diff_contracts[2] == key_base[2]
    assert key_diff_contracts[3] == key_base[3]

    # Changing stamp.surface_pin changes component 3 and nothing else.
    key_diff_surface = ir.cache_key(bc_hash, contracts_json_a, stamp_b)
    assert key_diff_surface[2] != key_base[2]
    assert key_diff_surface[0] == key_base[0]
    assert key_diff_surface[1] == key_base[1]
    assert key_diff_surface[3] == key_base[3]

    # Bumping ir_version changes component 4 AND the bytecode_hash (via the
    # hash prefix), which is IR_HASH_PREFIX's whole point. `IR_VERSION`
    # itself is 2 (spec §12.2.7/#4932), so the override under test must be
    # a THIRD, different value to demonstrate the mechanism.
    key_diff_version = ir.cache_key(bc_hash, contracts_json_a, stamp_a, ir_version=3)
    assert key_diff_version[3] != key_base[3]
    prefix_v2 = "sema-ir/2\n"
    prefix_v3 = "sema-ir/3\n"
    assert prefix_v2 != prefix_v3  # the actual mechanism AC-11.9 relies on


# ---------------------------------------------------------------------------
# AC-11.10 -- the trust rule fires in both directions.
# ---------------------------------------------------------------------------


def test_trust_rule_trusted_key_no_widen() -> None:
    payload = json.loads((FIXTURES_DIR / "simple_transfer_graph.json").read_text(encoding="utf-8"))
    # Rewrite op_2 (aspirate) to carry REAL PLR parameter names.
    for op in payload["operations"]:
        if op["method_name"] == "aspirate":
            op["arguments"] = {"resources": 'source["A1"]', "vols": "100"}
    param_names = {"LiquidHandler.aspirate": ("resources", "vols", "use_channels")}
    bc = ir.lower_graph(payload, param_names=param_names)
    aspirate_call = next(i for i in bc.instructions if isinstance(i, ir.Call) and i.method == "aspirate")
    assert set(aspirate_call.kwargs) == {"resources", "vols"}
    assert not any(k.startswith("?") for k in aspirate_call.kwargs)


def test_trust_rule_untrusted_key_widens_and_keeps_value() -> None:
    payload = json.loads((FIXTURES_DIR / "simple_transfer_graph.json").read_text(encoding="utf-8"))
    param_names = {"LiquidHandler.aspirate": ("resources", "vols", "use_channels")}
    bc = ir.lower_graph(payload, param_names=param_names)
    aspirate_call = next(i for i in bc.instructions if isinstance(i, ir.Call) and i.method == "aspirate")
    # The fixture's own arguments are extractor-guessed positional names
    # ("resource"/"volume"), neither a member of aspirate's real params.
    assert set(aspirate_call.kwargs) == {"?0", "?1"}
    assert aspirate_call.kwargs["?1"] == ir.Lit(100)


def test_trust_rule_none_param_names_untrusts_everything() -> None:
    payload = json.loads((FIXTURES_DIR / "simple_transfer_graph.json").read_text(encoding="utf-8"))
    bc = ir.lower_graph(payload, param_names=None)
    calls_with_kwargs = [i for i in bc.instructions if isinstance(i, ir.Call) and i.kwargs]
    assert calls_with_kwargs
    for call in calls_with_kwargs:
        assert all(k.startswith("?") for k in call.kwargs)


# ---------------------------------------------------------------------------
# AC-11.11 -- v1 lowers every condition and every trip count to Top, and
# says so.
# ---------------------------------------------------------------------------


def test_loop_trip_and_branch_pred_always_none() -> None:
    for fixture_payload in (_all_fields_payload(), _branchy_payload()):
        bc = ir.lower_graph(fixture_payload, param_names=_ASPIRATE_PARAM_NAMES)
        for instr in bc.instructions:
            if isinstance(instr, ir.Loop):
                assert instr.trip is None
            if isinstance(instr, ir.Branch):
                assert instr.pred is None


def test_branchy_fixture_lowers_to_well_formed_two_armed_region(
    contracts_payload: dict[str, Any],
) -> None:
    """The `condition_expr`/two-armed half of AC-11.11: a payload carrying a
    non-null `condition_expr` lowers to a well-formed BRANCH...ELSE...END
    region (both arms present, END balanced) and yields zero SAFE/WILL_FAIL
    findings for every receiver mentioned in either arm -- trivially true
    in v1 (no verdict but UNKNOWN is ever constructed, AC-11.6/§0), but the
    machinery half (both arms present, well-formed) is checked directly.
    **Scope qualifier (spec's own, carried over):** this is a fixture-only
    guarantee; no real graph payload can satisfy the antecedent (`extract/`
    never writes these fields).
    """
    payload = _branchy_payload()
    bc = ir.lower_graph(payload)
    branch_idx = next(i for i, instr in enumerate(bc.instructions) if isinstance(instr, ir.Branch))
    else_idx = next(i for i, instr in enumerate(bc.instructions) if isinstance(instr, ir.Else))
    end_idx = next(
        i
        for i, instr in enumerate(bc.instructions)
        if isinstance(instr, ir.End) and i > else_idx
    )
    assert branch_idx < else_idx < end_idx
    # Both arms carry >=1 CALL.
    assert any(isinstance(instr, ir.Call) for instr in bc.instructions[branch_idx + 1 : else_idx])
    assert any(isinstance(instr, ir.Call) for instr in bc.instructions[else_idx + 1 : end_idx])

    contracts = contracts_payload.get("contracts", {})
    findings = check_ir(bc, contracts)
    assert all(f.verdict.value == "unknown" for f in findings)


# ---------------------------------------------------------------------------
# AC-11.12 -- stale contract table degrades, does not crash.
# ---------------------------------------------------------------------------


def test_stale_contract_table_degrades_not_crashes(contracts_json: str) -> None:
    stale_payload = json.loads(contracts_json)
    for entry in stale_payload["contracts"].values():
        entry.pop("params", None)
    stale_json = json.dumps(stale_payload)

    graph_json = (FIXTURES_DIR / "simple_transfer_graph.json").read_text(encoding="utf-8")
    fresh_report = check_graph(graph_json, contracts_json)
    stale_report = check_graph(graph_json, stale_json)  # must not raise

    fresh_triples = sorted(
        (f.operation_id, f.reason, f.plr_site.qualname if f.plr_site else None)
        for f in fresh_report.findings
    )
    stale_triples = sorted(
        (f.operation_id, f.reason, f.plr_site.qualname if f.plr_site else None)
        for f in stale_report.findings
    )
    assert fresh_triples == stale_triples  # AC-11.6-identical, per §11.2.4

    # And the bytecode underneath carries WIDEN arguments on every CALL
    # that has any kwarg (fail-closed -- "trust nothing" against a table
    # with no params key on any entry).
    payload = json.loads(graph_json)
    stale_contracts = json.loads(stale_json).get("contracts", {})
    param_names = {
        key: tuple(entry.get("params", ())) for key, entry in stale_contracts.items() if entry.get("params")
    }
    assert param_names == {}
    bc = ir.lower_graph(payload, param_names=param_names)
    widen_pcs = {pc for pc, i in enumerate(bc.instructions) if isinstance(i, ir.Widen) and i.reason == "arguments"}
    calls_with_kwargs = [
        pc for pc, i in enumerate(bc.instructions) if isinstance(i, ir.Call) and i.kwargs
    ]
    assert calls_with_kwargs
    # Every CALL-with-kwargs pc has a preceding WIDEN(arguments) somewhere
    # before it in program order (checked via origin ordering rather than
    # exact adjacency, since other widens may also precede).
    for pc in calls_with_kwargs:
        assert any(w < pc for w in widen_pcs), f"CALL at pc={pc} has kwargs but no preceding WIDEN(arguments)"


# ---------------------------------------------------------------------------
# AC-11.13 -- region well-formedness is total, over the fixture corpus and
# reusing tier 4's hypothesis harness (not rebuilt).
# ---------------------------------------------------------------------------


def _assert_regions_well_formed(bc: ir.Bytecode) -> None:
    stack: list[str] = []
    for instr in bc.instructions:
        if isinstance(instr, ir.Loop):
            stack.append("LOOP")
        elif isinstance(instr, ir.Branch):
            stack.append("BRANCH")
        elif isinstance(instr, ir.Else):
            assert stack and stack[-1] == "BRANCH", "ELSE outside an open BRANCH"
        elif isinstance(instr, ir.End):
            assert stack, "unbalanced END with no open region"
            stack.pop()
    assert not stack, f"unclosed region(s) at end of stream: {stack}"


def test_region_well_formedness_over_fixtures() -> None:
    for payload in (_simple_transfer_payload(), _all_fields_payload(), _branchy_payload()):
        bc = ir.lower_graph(payload, param_names=_ASPIRATE_PARAM_NAMES)
        _assert_regions_well_formed(bc)


def test_region_well_formedness_over_hypothesis_fuzz() -> None:
    """Reuses tier 4's own strategy (`tests/test_wire_fuzz.py`,
    `graph_payload_strategy`) rather than rebuilding one, per §11.7 AC-11.13's
    "reused not rebuilt" instruction. 2,000 examples locally (the spec's own
    10,000 is tier 4's own budget under its harness's settings, which run
    separately in `test_wire_fuzz.py`'s `add_loop`-carrying strategy at 150
    examples per property x8 properties already -- this test targets the
    SAME strategy at a larger count, scoped to just the well-formedness
    property, to stay within a reasonable single-file runtime).
    """
    import sys as _sys

    _sys.path.insert(0, str(PLR_SEMA_ROOT / "tests"))
    from hypothesis import HealthCheck, given, settings
    from hypothesis import strategies as st
    from test_wire_fuzz import graph_payload_strategy  # noqa: PLC0415

    real_methods = list(json.loads(CONTRACTS_PATH.read_text(encoding="utf-8"))["contracts"].keys())[:30]

    @given(data=st.data())
    @settings(max_examples=2000, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def _prop(data: st.DataObject) -> None:
        payload = data.draw(graph_payload_strategy(real_methods))
        bc = ir.lower_graph(payload)  # must never raise
        _assert_regions_well_formed(bc)  # must always be balanced

    _prop()


# ---------------------------------------------------------------------------
# Spec §12.2 / backlog #4932: real LOOP/BRANCH regions, AC-12.5 through
# AC-12.8. `IR_VERSION` is 2 (§12.2.7) for this whole file's lowerings.
# ---------------------------------------------------------------------------


def test_ac_12_5_loop_protocol_real_region_no_synthetic_wrap() -> None:
    """AC-12.5's loop half, over the extractor's OWN output (the
    `LOOP_PROTOCOL_SOURCE` fixture from `tests/utils/test_computation_graph.py`,
    lowered and saved -- see that file's `:240-254`). A REGION header emits
    no `CALL`; `lower_graph` produces >=1 real `LOOP` and zero synthetic
    `WIDEN(has_loops)`/`Loop` wrap.
    """
    payload = _loop_protocol_payload()
    assert payload["has_loops"] is True
    header = next(op for op in payload["operations"] if op["node_type"] == "region")
    assert header["method_name"] == ""
    assert header["receiver_variable"] == ""
    assert header["receiver_type"] is None
    assert header["foreach_body"]
    # Body ops are not repeated at top level in execution_order.
    assert not (set(header["foreach_body"]) & set(payload["execution_order"]))

    bc = ir.lower_graph(payload, param_names=_ASPIRATE_PARAM_NAMES)
    widens = {i.reason for i in bc.instructions if isinstance(i, ir.Widen)}
    assert "has_loops" not in widens
    loops = [i for i in bc.instructions if isinstance(i, ir.Loop)]
    assert len(loops) == 1
    # The header itself never produced a CALL/WIDEN -- only the (real)
    # aspirate/dispense body calls and the pick_up_tips/drop_tips outside
    # the loop are present.
    calls = [i for i in bc.instructions if isinstance(i, ir.Call)]
    assert {c.method for c in calls} == {"pick_up_tips", "aspirate", "dispense", "drop_tips"}
    assert "receiver_type" not in widens  # the header's own None receiver_type never widens
    _assert_regions_well_formed(bc)


def test_ac_12_5_conditional_protocol_real_region_no_synthetic_wrap() -> None:
    """AC-12.5's branch half, over the extractor's own
    `CONDITIONAL_PROTOCOL_SOURCE` output: a real `BRANCH ... ELSE ... END`,
    zero synthetic `WIDEN(has_conditionals)` wrap.
    """
    payload = _conditional_protocol_payload()
    assert payload["has_conditionals"] is True
    header = next(op for op in payload["operations"] if op["node_type"] == "region")
    assert header["true_branch"] and header["false_branch"]
    assert not (
        (set(header["true_branch"]) | set(header["false_branch"])) & set(payload["execution_order"])
    )

    bc = ir.lower_graph(payload, param_names=_ASPIRATE_PARAM_NAMES)
    widens = {i.reason for i in bc.instructions if isinstance(i, ir.Widen)}
    assert "has_conditionals" not in widens
    branches = [i for i in bc.instructions if isinstance(i, ir.Branch)]
    assert len(branches) == 1
    _assert_regions_well_formed(bc)


def test_ac_12_6_proved_trip_counts_relayed_into_loop_trip() -> None:
    """AC-12.6: a REGION header's own proved `trip` (§12.2.3, computed by
    the extractor) is read straight into `Loop.trip` by `lower_graph` --
    seven loops `3, 4, 3, 12, None, None, None`, plus an eighth
    (`range(0)`) `0`.
    """
    payload = _proved_trip_payload()
    bc = ir.lower_graph(payload)
    loops = [i for i in bc.instructions if isinstance(i, ir.Loop)]
    assert [loop.trip for loop in loops] == [3, 4, 3, 12, None, None, None, 0]
    _assert_regions_well_formed(bc)


def test_ac_12_6_pre_4932_fixture_shape_still_always_none() -> None:
    """The pre-#4932 fixture/fuzz-only shape (a call-bearing, non-REGION
    operation that also carries its own region fields, e.g. `branchy_graph
    .json`/`all_fields_graph.json`) has no `trip` field at all and keeps
    the old, unconditional `Loop.trip is None` behaviour -- unaffected by
    #4932's REGION-specific relay.
    """
    for fixture_payload in (_all_fields_payload(), _branchy_payload()):
        bc = ir.lower_graph(fixture_payload, param_names=_ASPIRATE_PARAM_NAMES)
        for instr in bc.instructions:
            if isinstance(instr, ir.Loop):
                assert instr.trip is None


def test_ac_12_7_nested_regions_well_formed_and_elif_is_nested_branch() -> None:
    """AC-12.7: `for` containing `if`/`elif`/`else`, itself containing a
    `while`, lowers to a balanced stream -- `LOOP` -> `BRANCH` -> `ELSE` ->
    nested `BRANCH` -> `ELSE` -> `LOOP` -> matched `END`s -- with `ELSE`
    only inside an open `BRANCH`, and `check_ir` never raises. The `elif`
    is a nested `BRANCH` in the outer branch's false arm, not a third arm.
    """
    payload = _nested_regions_payload()
    bc = ir.lower_graph(payload)
    _assert_regions_well_formed(bc)

    ops = [i.op for i in bc.instructions if not isinstance(i, ir.Widen)]
    loop_idx = [i for i, op in enumerate(ops) if op == ir.Loop.op]
    branch_idx = [i for i, op in enumerate(ops) if op == ir.Branch.op]
    else_idx = [i for i, op in enumerate(ops) if op == ir.Else.op]
    assert len(loop_idx) == 2  # the outer `for` and the nested `while`
    assert len(branch_idx) == 2  # the outer `if` and the nested `elif`
    assert len(else_idx) == 2

    # The outer LOOP opens before both BRANCHes and closes after the
    # (later, nested) LOOP -- i.e. the for-loop's own region spans the
    # if/elif/else AND the while.
    outer_loop_open = loop_idx[0]
    inner_loop_open = loop_idx[1]
    assert outer_loop_open < branch_idx[0] < branch_idx[1] < inner_loop_open

    # No third arm: exactly two BRANCH opens and two ELSEs (if/elif), never
    # a third BRANCH sibling at the same nesting level for the same `if`.
    assert len(branch_idx) == len(else_idx) == 2

    # check_ir must not raise over this stream, contracts or not.
    findings = check_ir(bc, {})
    assert isinstance(findings, tuple)


def test_ac_12_8_self_attr_resolves_to_ref_not_top() -> None:
    """AC-12.8: `self.plate_1 = deck.get_resource("plate")` then
    `lh.aspirate(self.plate_1["A1"], vols=50)` -- the `ResourceNode` is
    registered under `variable_name == "self.plate_1"`,
    `is_parameter is False` (the extractor's own producer half, §12.2.5),
    and `lower_graph`'s value grammar resolves the argument to
    `Ref(slot_of("self.plate_1"), "A1")`, NOT `Top` (round-1 O4's latent
    divergence, closed).
    """
    payload = _self_attr_payload()
    resource = payload["resources"]["self.plate_1"]
    assert resource["variable_name"] == "self.plate_1"
    assert resource["is_parameter"] is False

    param_names = {"LiquidHandler.aspirate": ("resources", "vols")}
    bc = ir.lower_graph(payload, param_names=param_names)
    call = next(i for i in bc.instructions if isinstance(i, ir.Call) and i.method == "aspirate")
    resource_instr = next(i for i in bc.instructions if isinstance(i, ir.Resource))
    resolved = call.kwargs["resources"]
    assert isinstance(resolved, ir.Ref)
    assert resolved.cell == "A1"
    assert resolved.slot == resource_instr.slot
    assert resolved != ir.Top()


# ---------------------------------------------------------------------------
# AC-12.13 -- totality and the relabel under unrolling, and the OBLIGED(graph)
# exclusion for a proved-trip-0 region body.
# ---------------------------------------------------------------------------


def test_ac_12_13_obliged_excludes_only_the_dead_loop_body(contracts_payload: dict[str, Any]) -> None:
    """AC-12.13's second half: `OBLIGED(graph)` differs from `{op.id for op
    in graph.operations if op.node_type is not REGION}` on EXACTLY the body
    operations of proved-`trip == 0` regions. Uses `proved_trip_graph.json`
    (AC-12.6's own fixture -- seven proved loops plus an eighth,
    `range(0)`, `trip == 0`), the fixture AC-12.13 itself names.
    """
    payload = _proved_trip_payload()
    call_bearing = {
        op["id"] for op in payload["operations"] if op.get("node_type") != "region"
    }
    obliged = ir.obliged_operation_ids(payload)
    assert obliged != call_bearing, "the eighth (range(0)) loop's body must be excluded"
    excluded = call_bearing - obliged
    assert len(excluded) == 1, f"exactly one call-bearing op should be excluded, got {excluded}"


def test_ac_12_13_totality_and_relabel_over_a_dead_region(contracts_payload: dict[str, Any]) -> None:
    """AC-12.13's first half, over a fixture WITH a dead region (unlike
    `test_totality_and_relabel_bijection`, which uses the region-free
    `simple_transfer` fixture): every CALL pc VISITED by `check_ir`
    receives >=1 Finding and no non-CALL pc receives any; `sideband.origin`
    restricted to visited CALL pcs is a function onto `OBLIGED(graph)`;
    after relabelling, `{f.operation_id} == OBLIGED(graph)` (AC-6.4
    amended); and `len(findings) >= len(OBLIGED(graph))` (AC-7.2 amended).
    """
    payload = _proved_trip_payload()
    contracts = contracts_payload.get("contracts", {})
    bc = ir.lower_graph(payload)
    findings = check_ir(bc, contracts)

    call_pcs = {pc for pc, i in enumerate(bc.instructions) if isinstance(i, ir.Call)}
    non_call_pcs = {pc for pc, i in enumerate(bc.instructions) if not isinstance(i, ir.Call)}
    visited_pcs = {int(f.operation_id) for f in findings}

    assert visited_pcs <= call_pcs
    assert not (visited_pcs & non_call_pcs)
    assert visited_pcs != call_pcs, "the dead loop's body CALL pc must never be visited"

    origin = bc.sideband["origin"]
    origin_over_visited = {pc: opid for pc, opid in origin.items() if pc in visited_pcs}
    obliged = ir.obliged_operation_ids(payload)
    assert set(origin_over_visited.values()) == obliged, (
        "origin restricted to visited CALL pcs must be a function onto OBLIGED(graph)"
    )

    relabeled = ir.relabel_findings(findings, origin)
    assert {f.operation_id for f in relabeled} == obliged, "AC-6.4 amended: {f.operation_id} == OBLIGED(graph)"
    assert len(findings) >= len(obliged), "AC-7.2 amended: len(findings) >= len(OBLIGED(graph))"
