"""Tests for plr-sema/eval/t30_measure.py (spec 260904 sec15.9, T30b).

Synthetic guard/call fixtures, one per sec15.7 reason (plus `decidable`),
and the GO/NO-GO gate function over a synthetic per-op set. These do not
touch the frozen benchmark or the real contract table -- that is what
running the script itself (recorded in the T30b commit) exercises.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "eval"))
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))

import oracle_common as oc  # noqa: E402
import oracle_replay  # noqa: E402
from plr_sema.check import ir as _ir  # noqa: E402
from t30_measure import (  # noqa: E402
    REASON_DECIDABLE,
    REASON_ENV,
    REASON_OPERAND,
    REASON_UNPARSED,
    _real_calls_by_index,
    build_volume_guard_sites,
    classify_guard_for_call,
    classify_guard_structural,
    collect_executed_population,
    compute_gate,
    is_tip_family_owned,
    is_volume_family_owned,
    measure_env_ref_surface,
)

CONTRACTS_PATH = REPO_ROOT / "plr-sema" / "data" / "derived_contracts.json"


def _var(name: str) -> dict:
    return {"node": "Var", "name": name}


def _lit(value) -> dict:
    return {"node": "Lit", "value": value}


def _cmp(left: dict, op: str, right: dict) -> dict:
    return {"node": "Cmp", "left": left, "op": op, "right": right}


def _len(term: dict) -> dict:
    return {"node": "Len", "term": term}


def _env_ref(path: tuple[str, ...], args: list[dict] | None) -> dict:
    return {"node": "EnvRef", "path": list(path), "args": args}


def _not(pred: dict) -> dict:
    return {"node": "Not", "predicate": pred}


def _guard(
    predicate: dict,
    *,
    depth: int = 0,
    bindings: tuple[dict, ...] = (),
    raises: str | None = "ValueError",
    lineno: int = 100,
    qualname: str = "Widget.frobnicate",
    condition: str = "x",
) -> dict:
    return {
        "condition": condition,
        "predicate": predicate,
        "scope_trail": [],
        "raises": raises,
        "kind": "raise_guard",
        "free_vars": [],
        "site": {"file": "synthetic/module.py", "lineno": lineno, "qualname": qualname},
        "depth": depth,
        "bindings": list(bindings),
    }


def _call(kwargs: dict[str, _ir.Value], *, method: str = "frobnicate") -> _ir.Call:
    return _ir.Call(receiver=0, receiver_type="Widget", method=method, kwargs=kwargs)


# ---------------------------------------------------------------------------
# classify_guard_for_call -- one fixture per reason.
# ---------------------------------------------------------------------------


def test_classify_top_level_opaque_is_unparsed() -> None:
    g = _guard({"node": "Opaque", "text": "c not in self.head"})
    call = _call({})
    assert classify_guard_for_call(g, call, {}, {}, set()) == REASON_UNPARSED


def test_classify_nested_opaque_via_alpha_binding_is_unparsed() -> None:
    """sec15.7's own worked example: the top node parses (a plain Cmp over
    a bound name), but the alpha binding's OWN inner predicate is Opaque
    -- the guard stays `guard_predicate_unparsed` under the nested rule.
    """
    pred = _cmp(_len(_var("invalid_channels")), ">", _lit(0))
    binding = {
        "idiom": "alpha",
        "x": "invalid_channels",
        "iter": "channels",
        "pred": {"node": "Opaque", "text": "c not in self.head"},
    }
    g = _guard(pred, depth=1, bindings=(binding,))
    call = _call({"channels": _ir.Top()})
    assert classify_guard_for_call(g, call, {}, {}, set()) == REASON_UNPARSED


def test_classify_dynamic_raise_is_env_dependent() -> None:
    g = _guard({"node": "TRUE"}, raises="<dynamic:e>")
    call = _call({})
    assert classify_guard_for_call(g, call, {}, {}, set()) == REASON_ENV


def test_classify_depth1_unbound_free_name_is_env_dependent() -> None:
    """E-CALL(depth): a depth>=1 guard's free name never resolves against
    the entry point's kwargs, even if the call happens to carry a
    same-named kwarg.
    """
    g = _guard({"node": "Is", "term": _var("resources"), "negated": False}, depth=1)
    call = _call({"resources": _ir.Lit(v=None)})
    assert classify_guard_for_call(g, call, {}, {}, set()) == REASON_ENV


def test_classify_depth0_missing_kwarg_and_no_default_is_env_dependent() -> None:
    pred = _cmp(_var("strictness"), "==", _lit("STRICT"))
    g = _guard(pred, depth=0)
    call = _call({})  # "strictness" is not a kwarg at all.
    assert classify_guard_for_call(g, call, {}, {}, set()) == REASON_ENV


def test_classify_operand_unknown_top_kwarg() -> None:
    """Every free name resolves (it IS a real kwarg), but its VALUE is
    Top (renamed/unresolvable) -- guard_operand_unknown, not env-dependent.
    """
    pred = _cmp(_len(_var("use_channels")), "==", _len(_var("use_channels")))
    g = _guard(pred, depth=0)
    call = _call({"use_channels": _ir.Top()})
    assert classify_guard_for_call(g, call, {}, {}, set()) == REASON_OPERAND


def test_classify_operand_unknown_alpha_element_type_missing() -> None:
    """The alpha-bound Filtered term's element type cannot be decided
    (no RESOURCE declaration for the ref's slot) -- guard_operand_unknown.
    """
    pred = _cmp(_len(_var("not_tip_spots")), ">", _lit(0))
    binding = {
        "idiom": "alpha",
        "x": "not_tip_spots",
        "iter": "tip_spots",
        "pred": {"node": "Not", "predicate": {"node": "IsInstance", "term": _var("ts"), "types": ["TipSpot"]}},
    }
    g = _guard(pred, depth=0, bindings=(binding,))
    call = _call({"tip_spots": _ir.Seq(items=(_ir.Ref(slot=0, cell="A1"),))})
    # No slot_to_resource entry at all for slot 0 -> element type unresolvable.
    assert classify_guard_for_call(g, call, {}, {}, set()) == REASON_OPERAND


def test_classify_decidable_alpha_element_type_known() -> None:
    pred = _cmp(_len(_var("not_tip_spots")), ">", _lit(0))
    binding = {
        "idiom": "alpha",
        "x": "not_tip_spots",
        "iter": "tip_spots",
        "pred": {"node": "Not", "predicate": {"node": "IsInstance", "term": _var("ts"), "types": ["TipSpot"]}},
    }
    g = _guard(pred, depth=0, bindings=(binding,))
    call = _call({"tip_spots": _ir.Seq(items=(_ir.Ref(slot=0, cell="A1"),))})
    slot_to_resource = {
        0: _ir.Resource(
            slot=0, type="TipRack", element_type="TipSpot", is_container=False, is_parameter=True,
            parents=("Deck",), grid=None,
        )
    }
    assert classify_guard_for_call(g, call, slot_to_resource, {}, set()) == REASON_DECIDABLE


def test_classify_decidable_via_param_default() -> None:
    pred = {"node": "Is", "term": _var("target_vols"), "negated": True}  # target_vols is not None
    g = _guard(pred, depth=0)
    call = _call({})
    assert classify_guard_for_call(g, call, {}, {"target_vols": None}, set()) == REASON_DECIDABLE


def test_classify_decidable_via_channel_kwarg() -> None:
    """A depth->=1 guard whose free name IS the receiver's own
    `channel_kwarg` resolves via the channel term, not via call.kwargs.
    """
    pred = {"node": "Is", "term": _var("use_channels"), "negated": True}
    g = _guard(pred, depth=1)
    call = _call({})
    assert (
        classify_guard_for_call(g, call, {}, {}, {"use_channels"}, channel_kwarg="use_channels")
        == REASON_DECIDABLE
    )


def test_classify_env_dependent_depth1_binding_iterand_not_channel() -> None:
    """A depth>=1 alpha binding whose iterand is NOT the receiver's own
    channel_kwarg can never resolve at all (E-CALL(depth)) -- this is the
    `:875` case (`not_containers` bound over `resources`, not
    `use_channels`) -- `guard_env_dependent`, never `guard_operand_unknown`
    on no evidence.
    """
    pred = _cmp(_len(_var("not_containers")), ">", _lit(0))
    binding = {
        "idiom": "alpha",
        "x": "not_containers",
        "iter": "resources",
        "pred": {"node": "Not", "predicate": {"node": "IsInstance", "term": _var("r"), "types": ["Container"]}},
    }
    g = _guard(pred, depth=1, bindings=(binding,))
    call = _call({"resources": _ir.Seq(items=())})
    assert (
        classify_guard_for_call(g, call, {}, {}, {"resources"}, channel_kwarg="use_channels") == REASON_ENV
    )


# ---------------------------------------------------------------------------
# T35 (260907 amendment, spec 260904 S15.7's REORDERED reason rule, round 2
# A-C5/A-C4): the operand-unknown test precedes contains_env_ref, and both
# range over the alpha/beta-SUBSTITUTED tree.
# ---------------------------------------------------------------------------


def test_classify_env_ref_call_with_top_operand_is_operand_unknown_not_env() -> None:
    """S15.7's reordered clause 2 wins over clause 3: an `EnvRef` call whose
    OWN argument is a real kwarg of this call but its VALUE is Top is
    `guard_operand_unknown`, never `guard_env_dependent` -- the amendment
    must not relax the gate's OTHER zero-condition (A-C5)."""
    pred = _env_ref(("self", "backend", "f"), [_var("x")])
    g = _guard(pred, depth=0)
    call = _call({"x": _ir.Top()})
    assert classify_guard_for_call(g, call, {}, {}, set()) == REASON_OPERAND


def test_classify_env_ref_bare_is_env_dependent() -> None:
    """A bare `EnvRef` used directly as the predicate (e.g.
    `self.setup_finished`) has no free names to resolve at all -- no
    operand-unknown path fires, and `contains_env_ref` alone decides
    `guard_env_dependent`."""
    pred = _env_ref(("self", "setup_finished"), None)
    g = _guard(pred, depth=0)
    call = _call({})
    assert classify_guard_for_call(g, call, {}, {}, set()) == REASON_ENV


def test_classify_substituted_409_shaped_guard_is_env_dependent() -> None:
    """The amendment's own worked example, in classifier form: the RAW
    predicate mentions only `invalid_channels` (no EnvRef at all); its
    alpha binding's inner filter is `Cmp(Var("c"), "not in",
    EnvRef(("self","head"), None))`. `:409`'s own iterand ("channels") is a
    depth-1 free name that can never resolve (E-CALL(depth)) -- so this
    clears clause 1 (substituted tree is not Opaque), clears clause 2
    (nothing resolves to an operand at all, so nothing can be Top), and
    clause 3 (`contains_env_ref` over the SUBSTITUTED tree) decides
    `guard_env_dependent`."""
    pred = _cmp(_len(_var("invalid_channels")), "==", _lit(0))
    binding = {
        "idiom": "alpha",
        "x": "invalid_channels",
        "iter": "channels",
        "pred": {"node": "Cmp", "left": _var("c"), "op": "not in", "right": _env_ref(("self", "head"), None)},
    }
    g = _guard(pred, depth=1, bindings=(binding,))
    call = _call({})
    assert classify_guard_for_call(g, call, {}, {}, set()) == REASON_ENV


def test_classify_structural_substituted_env_ref_is_env_dependent() -> None:
    """The no-call block (3) classifier reaches the identical conclusion
    from the substituted tree, as its own (last-resort) reason."""
    pred = _cmp(_len(_var("invalid_channels")), "==", _lit(0))
    binding = {
        "idiom": "alpha",
        "x": "invalid_channels",
        "iter": "channels",
        "pred": {"node": "Cmp", "left": _var("c"), "op": "not in", "right": _env_ref(("self", "head"), None)},
    }
    g = _guard(pred, depth=1, bindings=(binding,))
    parsed, bound, reason = classify_guard_structural(g, frozenset(), set())
    assert parsed  # the RAW top-level predicate has no Opaque node
    assert reason == REASON_ENV


# ---------------------------------------------------------------------------
# classify_guard_structural -- the no-specific-call block(3) classifier.
# ---------------------------------------------------------------------------


def test_structural_unparsed() -> None:
    g = _guard({"node": "Opaque", "text": "whatever"})
    parsed, bound, reason = classify_guard_structural(g, frozenset(), set())
    assert not parsed
    assert reason == REASON_UNPARSED


def test_structural_bound_and_decidable_or_operand_dependent() -> None:
    pred = _cmp(_len(_var("not_tip_spots")), ">", _lit(0))
    binding = {
        "idiom": "alpha",
        "x": "not_tip_spots",
        "iter": "tip_spots",
        "pred": {"node": "Not", "predicate": {"node": "IsInstance", "term": _var("ts"), "types": ["TipSpot"]}},
    }
    g = _guard(pred, depth=0, bindings=(binding,))
    parsed, bound, reason = classify_guard_structural(g, frozenset({"tip_spots"}), set())
    assert parsed
    assert bound
    assert reason == "decidable_or_operand_dependent"


def test_structural_env_dependent_depth1_non_channel_binding() -> None:
    pred = _cmp(_len(_var("not_containers")), ">", _lit(0))
    binding = {
        "idiom": "alpha",
        "x": "not_containers",
        "iter": "resources",
        "pred": {"node": "Not", "predicate": {"node": "IsInstance", "term": _var("r"), "types": ["Container"]}},
    }
    g = _guard(pred, depth=1, bindings=(binding,))
    parsed, bound, reason = classify_guard_structural(g, frozenset(), {"resources"}, channel_kwarg="use_channels")
    assert parsed
    assert bound
    assert reason == REASON_ENV


def test_structural_unbound_free_local() -> None:
    pred = _cmp(_var("missing"), ">", _lit(0))
    g = _guard(pred, depth=1)
    parsed, bound, reason = classify_guard_structural(g, frozenset(), set())
    assert parsed
    assert not bound
    assert reason == REASON_ENV


# ---------------------------------------------------------------------------
# is_tip_family_owned
# ---------------------------------------------------------------------------


def test_is_tip_family_owned_bool_view_atom() -> None:
    g = _guard({"node": "Opaque", "text": "self.head[channel].has_tip"}, qualname="LiquidHandler.pick_up_tips")
    g["condition"] = "self.head[channel].has_tip"
    receiver_state = {
        "LiquidHandler": {
            "channel_attr": "head",
            "bool_view": {"attr": "has_tip"},
            "state_fields": [],
        }
    }
    assert is_tip_family_owned(g, receiver_state) is True


def test_is_tip_family_owned_false_for_unrelated_condition() -> None:
    g = _guard({"node": "TRUE"}, qualname="LiquidHandler.pick_up_tips")
    g["condition"] = "len(not_tip_spots) > 0"
    receiver_state = {
        "LiquidHandler": {"channel_attr": "head", "bool_view": {"attr": "has_tip"}, "state_fields": []}
    }
    assert is_tip_family_owned(g, receiver_state) is False


def test_is_tip_family_owned_false_when_no_receiver_state() -> None:
    g = _guard({"node": "TRUE"}, qualname="Unrelated.method")
    g["condition"] = "self.head[channel].has_tip"
    assert is_tip_family_owned(g, {}) is False


# ---------------------------------------------------------------------------
# T35 fix-up (2), S15.9: the volume family's own dispatch exclusion, the
# volume half of S15.2's family-dispatch rule.
# ---------------------------------------------------------------------------


def test_build_volume_guard_sites_and_is_volume_family_owned() -> None:
    contracts = {
        "LiquidHandler.aspirate": {
            "guards": [],
            "volume_guards": [
                {
                    "condition": "volume - self.get_used_volume() > 1e-06",
                    "site": {
                        "file": "external/pylabrobot/pylabrobot/resources/volume_tracker.py",
                        "lineno": 92,
                        "qualname": "VolumeTracker.remove_liquid",
                    },
                }
            ],
        },
    }
    sites = build_volume_guard_sites(contracts)
    assert sites == frozenset(
        {("external/pylabrobot/pylabrobot/resources/volume_tracker.py", 92, "VolumeTracker.remove_liquid")}
    )
    g = _guard(
        {"node": "TRUE"},
        lineno=92,
        qualname="VolumeTracker.remove_liquid",
        condition="volume - self.get_used_volume() > 1e-06",
    )
    g["site"]["file"] = "external/pylabrobot/pylabrobot/resources/volume_tracker.py"
    assert is_volume_family_owned(g, sites) is True
    assert is_volume_family_owned(g, frozenset()) is False


# ---------------------------------------------------------------------------
# T35 block (6): measure_env_ref_surface -- the amendment's own whole-table
# surface (n_env_ref_guards/nodes, n_zip, n_membership_cmp, n_var_self,
# n_env_ref_refused_plr_layer, top-10 paths).
# ---------------------------------------------------------------------------


def test_measure_env_ref_surface_counts_and_refusal() -> None:
    """A synthetic two-guard table: one `self.backend.f(...)` EnvRef (never
    refused, length-3 path) and one `self._helper()` call (length-2,
    refused because `_helper` IS in the qualname index for `Widget`)."""
    contracts = {
        "Widget.frobnicate": {
            "guards": [
                _guard(
                    _env_ref(("self", "backend", "f"), [_var("x")]),
                    lineno=10,
                    qualname="Widget.frobnicate",
                    condition="self.backend.f(x)",
                ),
                _guard(
                    {"node": "Opaque", "text": "self._helper()"},
                    lineno=20,
                    qualname="Widget.other",
                    condition="self._helper()",
                ),
            ],
        },
    }
    for g in contracts["Widget.frobnicate"]["guards"]:
        g["site"]["file"] = "external/pylabrobot/pylabrobot/synthetic_widget.py"
    qualname_index = frozenset({("pylabrobot.synthetic_widget", "Widget._helper")})
    result = measure_env_ref_surface(contracts, {}, qualname_index, frozenset())
    assert result["n_env_ref_guards"] == 1  # only the length-3 EnvRef survives as shipped
    assert result["n_env_ref_nodes"] == 1
    assert result["top10_env_ref_paths"] == [{"path": "self.backend.f", "n": 1}]
    assert result["n_env_ref_refused_plr_layer"] == 1  # self._helper() was refused
    assert result["n_var_self"] == 0


def test_measure_env_ref_surface_no_index_refuses_every_k1_candidate() -> None:
    contracts = {
        "Widget.frobnicate": {
            "guards": [
                _guard(
                    {"node": "Opaque", "text": "self._unindexed_helper()"},
                    lineno=30,
                    qualname="Widget.frobnicate",
                    condition="self._unindexed_helper()",
                ),
            ],
        },
    }
    contracts["Widget.frobnicate"]["guards"][0]["site"]["file"] = "external/pylabrobot/pylabrobot/synthetic_widget.py"
    result = measure_env_ref_surface(contracts, {}, None, frozenset())
    assert result["n_env_ref_refused_plr_layer"] == 1


# ---------------------------------------------------------------------------
# compute_gate -- the GO/NO-GO decision over a synthetic per-op set.
# ---------------------------------------------------------------------------


def test_compute_gate_go_when_one_op_clears() -> None:
    per_op = [
        {"op_id": "op_0", "record_id": "r0", "method": "pick_up_tips", "reasons": [REASON_ENV]},
        {"op_id": "op_1", "record_id": "r1", "method": "pick_up_tips", "reasons": [REASON_UNPARSED]},
    ]
    gate = compute_gate(per_op)
    assert gate["go"] is True
    assert gate["n_ops_clearing"] == 1
    assert gate["methods_clearing"] == ["pick_up_tips"]


def test_compute_gate_no_go_when_every_op_carries_unparsed_or_operand_unknown() -> None:
    per_op = [
        {"op_id": "op_0", "record_id": "r0", "method": "pick_up_tips", "reasons": [REASON_UNPARSED, REASON_ENV]},
        {"op_id": "op_1", "record_id": "r1", "method": "aspirate", "reasons": [REASON_OPERAND]},
    ]
    gate = compute_gate(per_op)
    assert gate["go"] is False
    assert gate["n_ops_clearing"] == 0
    assert gate["methods_clearing"] == []


def test_compute_gate_decidable_alone_clears() -> None:
    per_op = [{"op_id": "op_0", "record_id": "r0", "method": "pick_up_tips", "reasons": [REASON_DECIDABLE]}]
    gate = compute_gate(per_op)
    assert gate["go"] is True
    assert gate["n_ops_clearing"] == 1


# ---------------------------------------------------------------------------
# The executed-op population (#4978, T32 fix-up): proves the population
# `collect_executed_population` derives (via FINDINGS_SINK + LOWERED_SINK
# around an unmodified `oracle_replay.main()` call) is exactly the set of
# ops `oracle_replay.run_row` itself executes -- never a locally
# re-implemented gating decision. This is a REGRESSION test for the defect
# fixed by #4978: the pre-fix version of this script re-implemented
# row_to_verifier_inputs/run_runtime/lower_row_calls directly and never
# threaded the sidecar's ambiguity_class through, so it silently admitted
# rows run_row would have skipped (923 vs the correct 544 measured ops on
# the real frozen benchmark).
# ---------------------------------------------------------------------------


def _chat_row(name: str, arguments: dict, utterance: str = "test utterance") -> dict:
    """Minimal chat-format corpus row (corpus_p25.jsonl shape), mirroring
    test_oracle_replay.py's own helper of the same name.
    """
    return {
        "messages": [
            {"role": "developer", "content": "sys"},
            {"role": "user", "content": utterance},
            {"role": "assistant", "tool_calls": [{"function": {"name": name, "arguments": arguments}, "type": "function"}]},
        ],
        "tools": [],
        "metadata": "train",
    }


def _no_call_row(utterance: str = "What's the tip height?") -> dict:
    return {
        "messages": [
            {"role": "user", "content": utterance},
            {"role": "assistant", "content": "The tip height is 10mm."},
        ],
        "tools": [],
        "metadata": "train",
    }


class TestLoweredSinkNotPlannedIndex:
    """Direct level (mirrors test_unknown_ledger.py's TestFindingsSinkSeam
    and test_oracle_replay.py's TestPLRNamedArguments,
    test_run_static_calls_not_planned_index_gets_empty_entry) -- a
    not-planned index (call_sequence[1], deliberately missing from
    plr_kwargs) never carries a real Finding, so FINDINGS_SINK/LOWERED_SINK
    together must exclude it from the executed-op population even though
    `run_static_calls`'s own returned `st` dict still carries a placeholder
    entry for it (`{"verdict": "unknown", "n_findings": 0, "reasons": []}`,
    §11.10) -- exactly the distinction `collect_executed_population` must
    get right.
    """

    def setup_method(self):
        assert oc.FINDINGS_SINK is None, "a prior test left FINDINGS_SINK installed"
        assert oc.LOWERED_SINK is None, "a prior test left LOWERED_SINK installed"

    def teardown_method(self):
        oc.FINDINGS_SINK = None
        oc.LOWERED_SINK = None

    def test_not_planned_op_excluded_from_findings_and_lowered_population(self):
        example = {
            "call_sequence": [
                {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}},
                {"name": "transfer", "params": {"source": "src.A1", "destination": "dst.B1", "volume_ul": 50}},
            ],
            "deck_layout": {"resources": {"tip_rack": "TipRack"}},
            "intent_record": {"record_id": "test:not-planned-00"},
        }
        # index 1 ("transfer") is deliberately absent -> not planned.
        plr_kwargs = {
            0: {
                "tip_spots": {"k": "seq", "items": [{"k": "ref", "name": "tip_rack", "cell": "A1"}]},
                "use_channels": {"k": "seq", "items": [{"k": "lit", "v": 0}]},
            },
        }
        contracts_json = json.dumps({
            "contracts": {
                "LiquidHandler.pick_up_tips": {
                    "guards": [
                        {
                            "condition": "len(not_tip_spots) > 0",
                            "depth": 0, "free_vars": [], "kind": "raise_guard",
                            "raises": "TypeError", "scope_trail": [],
                            "site": {
                                "file": "external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
                                "lineno": 498, "qualname": "LiquidHandler.pick_up_tips",
                            },
                        },
                    ],
                    "gaps": [],
                    "params": ["tip_spots", "use_channels"],
                },
            },
        })

        collected_findings: list[tuple[str, tuple]] = []
        collected_lowered: list[tuple] = []
        oc.FINDINGS_SINK = lambda row_id, findings: collected_findings.append((row_id, findings))
        oc.LOWERED_SINK = lambda row_id, bc, bc_with_o1, not_planned, element_types: collected_lowered.append(
            (row_id, bc, bc_with_o1, not_planned, element_types)
        )

        param_names = oc.param_names_from_contracts(contracts_json)
        st, not_planned = oc.run_static_calls(example, plr_kwargs, contracts_json, param_names=param_names)

        assert not_planned == [1]
        assert set(st) == {"op_0", "op_1"}
        assert st["op_1"] == {"verdict": "unknown", "n_findings": 0, "reasons": []}

        assert len(collected_findings) == 1
        _row_id, findings = collected_findings[0]
        assert findings, "op_0 has a real guard and must carry >=1 real Finding"
        assert {f.operation_id for f in findings} == {"op_0"}  # op_1 (not planned) never appears

        assert len(collected_lowered) == 1
        _row_id2, bc, bc_with_o1, sink_not_planned, _element_types = collected_lowered[0]
        assert sink_not_planned == [1]

        planned_indices = [i for i in range(2) if i not in set(sink_not_planned)]
        real_calls = _real_calls_by_index(bc, planned_indices)
        real_calls_with_o1 = _real_calls_by_index(bc_with_o1, planned_indices)
        assert set(real_calls) == {0}
        assert set(real_calls_with_o1) == {0}
        assert real_calls[0].method == "pick_up_tips"


class TestCollectExecutedPopulation:
    """Corpus-level: proves `collect_executed_population` -- driven entirely
    through an unmodified `oracle_replay.main()` -- reproduces exactly what
    `oracle_replay.run_row` itself executes for a tiny synthetic corpus with
    one no_call row, one row the SIDECAR's own ambiguity_class skips (the
    exact defect #4978 fixed: a `"transfer"` row with every required param
    present, which `_precondition_plan` would happily execute on its own,
    but which the sidecar marks `"ambiguous_referent"`), and one row that
    executes cleanly (a real `pick_up_tips` row copied verbatim from
    `corpus_p25.jsonl` line 261 / its sidecar counterpart, record_id
    `cov-0260-pick_up_tips__none-00`, so it is known-good production data,
    not a hand-authored guess at what `_precondition_plan`/`run_runtime`
    will accept).
    """

    def test_population_matches_run_row_over_a_tiny_corpus(self, tmp_path: Path) -> None:
        if not CONTRACTS_PATH.exists():
            pytest.skip(f"{CONTRACTS_PATH} not found")

        rows = [
            _no_call_row(),
            _chat_row(
                "transfer",
                {"source": "src.A1", "destination": "dst.B1", "volume_ul": 50},
                utterance="Transfer from A1 to B1",
            ),
            _chat_row(
                "pick_up_tips",
                {"at": ["tip_rack.D8", "tip_rack.F12"]},
                utterance="Pick up tips from tip_rack.D8 and tip_rack.F12.",
            ),
        ]
        sidecar_rows = [
            {"ambiguity_class": "clean_parse", "record_id": "test-no-call-00", "provenance": "coverage", "calls": []},
            {
                "ambiguity_class": "ambiguous_referent", "record_id": "test-transfer-ambiguous-00",
                "provenance": "coverage", "calls": [],
            },
            {
                "ambiguity_class": "clean_parse", "record_id": "cov-0260-pick_up_tips__none-00",
                "provenance": "coverage", "calls": [],
            },
        ]

        corpus_path = tmp_path / "tiny_corpus.jsonl"
        corpus_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        sidecar_path = tmp_path / "tiny_sidecar.jsonl"
        sidecar_path.write_text("\n".join(json.dumps(r) for r in sidecar_rows) + "\n", encoding="utf-8")
        contracts_json = CONTRACTS_PATH.read_text(encoding="utf-8")

        # Independently reproduce what oracle_replay.run_row does for the
        # SAME three rows, with the SAME sidecar-derived arguments -- the
        # ground truth `collect_executed_population`'s own population must
        # match, established WITHOUT going through that function at all.
        expected_op_ids_by_row: list[set[str]] = []
        expected_record_ids: list[str] = []
        for i, (row, srow) in enumerate(zip(rows, sidecar_rows)):
            result = oracle_replay.run_row(
                row, str(corpus_path), i + 1, contracts_json,
                ambiguity_class=srow["ambiguity_class"], sidecar_record_id=srow["record_id"],
                provenance=srow["provenance"],
            )
            expected_op_ids_by_row.append(set(result.static_verdicts))
            expected_record_ids.append(result.record_id)
        assert expected_op_ids_by_row[0] == set()  # no_call row: nothing executed
        assert expected_op_ids_by_row[1] == set()  # sidecar-skipped row: nothing executed
        assert expected_op_ids_by_row[2] == {"op_0"}  # the one real pick_up_tips op

        replay_report_path = tmp_path / "replay_report.json"
        ops, diagnostics = collect_executed_population(
            corpus=[str(corpus_path)],
            sidecar=str(sidecar_path),
            crosscheck=[],
            contracts=CONTRACTS_PATH,
            limit=None,
            replay_report_path=replay_report_path,
        )

        assert diagnostics["n_rows_static_eligible"] == 1  # only the pick_up_tips row reaches Static
        assert diagnostics["n_ops_executed"] == 1
        assert len(ops) == 1
        assert ops[0].method == "pick_up_tips"
        assert ops[0].op_id == "op_0"
        # record_id is a content digest (row_to_verifier_inputs's own docstring:
        # sidecar_record_id is accepted for signature compatibility only, never
        # used for identity) -- compare against run_row's OWN record_id for the
        # SAME row, not the sidecar's record_id.
        assert ops[0].record_id == expected_record_ids[2]
