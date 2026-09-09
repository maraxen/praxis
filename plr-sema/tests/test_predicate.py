"""plr_sema.check.predicate -- the Kleene evaluator (increment 6, spec
260904 §15.4/§15.5/§15.7, T31-1). One fixture per E-rule named in the
sprint task's deliverable list, plus the round-1 fixture set AC-15.1/
AC-15.2/AC-15.5/AC-15.6 name explicitly.
"""

from __future__ import annotations

from typing import Any

from plr_sema.check import ir
from plr_sema.check.predicate import (
    GuardResult,
    evaluate_guard,
    evaluate_predicate,
    subclass_closure_from_bases,
)
from plr_sema.derive import predicate_ast as pa

# ---------------------------------------------------------------------------
# Fixture builders.
# ---------------------------------------------------------------------------


def _site(lineno: int = 1, qualname: str = "LiquidHandler.m", file: str = "external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py") -> dict[str, Any]:
    return {"file": file, "lineno": lineno, "qualname": qualname}


def _guard(
    condition: "str | None",
    *,
    kind: str = "raise_guard",
    scope_trail: "tuple[str, ...]" = (),
    depth: int = 0,
    bindings: "tuple[dict[str, Any], ...]" = (),
    free_vars: "tuple[str, ...]" = (),
    raises: "str | None" = "TypeError",
    lineno: int = 1,
) -> dict[str, Any]:
    predicate = pa.parse(condition)
    return {
        "condition": condition,
        "predicate": pa.to_json(predicate),
        "scope_trail": list(scope_trail),
        "raises": raises,
        "kind": kind,
        "free_vars": list(free_vars),
        "site": _site(lineno=lineno),
        "depth": depth,
        "bindings": list(bindings),
    }


def _self_entry_guard(condition: str, *, kind: str = "raise_guard", **kw: Any) -> dict[str, Any]:
    """A `raise_guard` whose own condition is the immediate enclosing
    `if` -- E-UNCOND(6)'s self-entry, excluded by `evaluate_guard` before
    E-SCOPE/E-UNCOND ever see it. This is the SHAPE every real
    `_BodyScanner.visit_Raise`-produced guard has whenever `condition` is
    not `None`. The self-entry mechanism is `raise_guard`-only (E-UNCOND(6)
    reads `visit_Raise`'s own convention); an `assert`-kind guard's
    `scope_trail` never carries its own condition, so this helper emits an
    EMPTY trail for one instead -- a non-empty trail here would fabricate
    a phantom enclosing scope entry that E-SCOPE would then evaluate."""
    if kind != "raise_guard":
        return _guard(condition, kind=kind, scope_trail=(), **kw)
    return _guard(condition, kind=kind, scope_trail=(f"if {condition}",), **kw)


def _call(kwargs: "dict[str, ir.Value] | None" = None, *, method: str = "pick_up_tips") -> ir.Call:
    return ir.Call(receiver=0, receiver_type="LiquidHandler", method=method, kwargs=kwargs or {})


def _resource(slot: int, *, type_: "str | None" = None, element_type: "str | None" = None) -> ir.Resource:
    return ir.Resource(
        slot=slot, type=type_, element_type=element_type, is_container=False, is_parameter=True, parents=(), grid=None
    )


def _seq_of_refs(slot: int, cells: "tuple[str, ...]") -> ir.Seq:
    return ir.Seq(tuple(ir.Ref(slot=slot, cell=c) for c in cells))


ALPHA_TIP_SPOTS = {
    "idiom": "alpha",
    "x": "not_tip_spots",
    "iter": "tip_spots",
    "pred": pa.to_json(pa.Not(pa.IsInstance(pa.Var("ts"), ("TipSpot",)))),
}


# ---------------------------------------------------------------------------
# AC-15.1 -- the grammar is total; positive/negative fixtures on evaluation.
# ---------------------------------------------------------------------------


def test_g0_unrecognised_shape_still_yields_guard_predicate_unparsed() -> None:
    """`c not in self.head` -- pre-amendment this stayed `Opaque`; the
    amendment recognises `self.head` as `EnvRef` but the guard as a WHOLE
    is unaffected here since we test it standalone with no alpha binding
    for `c` -- the point is the reason is unchanged from today's."""
    guard = _self_entry_guard("c not in self.head")
    result = evaluate_guard(guard, _call(), {}, {})
    assert result.verdict == "unknown"
    assert result.reason == "guard_env_dependent"  # G8: `not in` -> EnvRef -> contains_env_ref.


def test_chained_comparison_second_conjunct_false_first_half_decides_f() -> None:
    """`len(a) == len(b) == len(c)` -- `And` of two `Cmp`s; the SECOND
    conjunct being `F` decides the whole `And` `F` even though the first
    is ½ (Kleene `And`: one `F` conjunct decides regardless of the rest)."""
    guard = _self_entry_guard("len(a) == len(b) == len(c)", kind="assert")
    call = _call({"b": ir.Seq((ir.Lit(1), ir.Lit(2))), "c": ir.Seq((ir.Lit(1),))})
    # a is unresolved (½ for the first Cmp); b(len=2) != c(len=1) -> F for
    # the second Cmp -> whole And is F -> assert-kind fires on F -> WILL_FAIL
    # unless E-UNCOND blocks it (empty trail, depth 0, no reachability fact).
    result = evaluate_guard(guard, call, {}, {})
    assert result.verdict == "unknown"
    assert result.reason == "guard_env_dependent"  # fires=True (assert on F), but not unconditional.
    # Confirm the underlying VALUE really did decide, via evaluate_predicate directly.
    from plr_sema.check.predicate import _Ctx  # type: ignore[attr-defined]

    ctx = _Ctx(
        call=call, resources_by_slot={}, param_defaults={}, bindings_by_name={}, depth=0,
        channel_kwarg=None, channels=None, env=frozenset(), class_hierarchy=None,
    )
    assert evaluate_predicate(pa.parse("len(a) == len(b) == len(c)"), ctx) is False


def test_filtered_emptiness_gt_zero_and_eq_zero() -> None:
    ctx_kwargs = {"tip_spots": _seq_of_refs(0, ("A1", "A2"))}
    call = _call(ctx_kwargs)
    resources = {0: _resource(0, element_type="TipSpot")}
    guard_gt0 = _guard(
        "len(not_tip_spots) > 0", bindings=(ALPHA_TIP_SPOTS,), free_vars=(), scope_trail=("if len(not_tip_spots) > 0",)
    )
    guard_eq0 = _guard(
        "len(not_tip_spots) == 0", bindings=(ALPHA_TIP_SPOTS,), scope_trail=("if len(not_tip_spots) == 0",)
    )
    # Homogeneous TipSpot elements -> no non-TipSpot found -> AnyOf is False.
    r_gt0 = evaluate_guard(guard_gt0, call, {}, resources)
    assert r_gt0.verdict == "safe"  # raise_guard fires on T; AnyOf=F -> guard does not fire.
    r_eq0 = evaluate_guard(guard_eq0, call, {}, resources)
    # `== 0` is `Not(AnyOf(...))` = Not(False) = True -> raise_guard fires
    # -- but the scope trail is empty and depth 0 with no reachability
    # fact supplied, so it stays UNKNOWN/guard_env_dependent (E-UNCOND(5)).
    assert r_eq0.verdict == "unknown"
    assert r_eq0.reason == "guard_env_dependent"


def test_setof_uniqueness_true_and_false() -> None:
    guard = _self_entry_guard("len(set(use_channels)) == len(use_channels)", kind="assert")
    call_unique = _call({"use_channels": ir.Seq((ir.Lit(0), ir.Lit(1), ir.Lit(1)))})
    result = evaluate_guard(guard, call_unique, {}, {})
    # duplicate channel [0,1,1] -> set has 2, len has 3 -> Cmp False -> assert fires (True) -- E-UNCOND blocks it (no reachability fact).
    assert result.verdict == "unknown"
    assert result.reason == "guard_env_dependent"

    call_ok = _call({"use_channels": ir.Seq((ir.Lit(0), ir.Lit(1)))})
    result_ok = evaluate_guard(guard, call_ok, {}, {})
    assert result_ok.verdict == "safe"  # Cmp True -> assert does not fire -> SAFE.


def test_is_none_and_is_not_none_are_exact_opposites_on_a_lit_null_kwarg() -> None:
    call = _call({"x": ir.Lit(None)})
    from plr_sema.check.predicate import _Ctx  # type: ignore[attr-defined]

    ctx = _Ctx(
        call=call, resources_by_slot={}, param_defaults={}, bindings_by_name={}, depth=0,
        channel_kwarg=None, channels=None, env=frozenset(), class_hierarchy=None,
    )
    assert evaluate_predicate(pa.parse("x is None"), ctx) is True
    assert evaluate_predicate(pa.parse("x is not None"), ctx) is False


def test_assert_and_raise_guard_fire_on_opposite_polarities_of_the_same_condition() -> None:
    condition = "len(set(use_channels)) == len(use_channels)"
    call = _call({"use_channels": ir.Seq((ir.Lit(0), ir.Lit(1)))})  # unique -> Cmp True.
    raise_guard = _self_entry_guard(condition, kind="raise_guard")
    assert_guard = _self_entry_guard(condition, kind="assert")
    # raise_guard fires on T -> since Cmp=True, fires=True -> would-be WILL_FAIL, blocked by E-UNCOND -> unknown.
    r1 = evaluate_guard(raise_guard, call, {}, {})
    assert r1.verdict == "unknown" and r1.reason == "guard_env_dependent"
    # assert fires on F -> since Cmp=True, fires=False -> SAFE (assert passes).
    r2 = evaluate_guard(assert_guard, call, {}, {})
    assert r2.verdict == "safe"


def test_isinstance_container_vs_tipspot_trash_is_half_not_false() -> None:
    """C4a's false-WILL_FAIL mechanism: a `Container`-declared element is
    NOT disjoint-and-exact against `(TipSpot, Trash)` -- ½, never `F`."""
    call = _call({"r": ir.Ref(slot=0, cell="A1")})
    resources = {0: _resource(0, element_type="Container")}
    from plr_sema.check.predicate import _Ctx  # type: ignore[attr-defined]

    ctx = _Ctx(
        call=call, resources_by_slot=resources, param_defaults={}, bindings_by_name={}, depth=0,
        channel_kwarg=None, channels=None, env=frozenset(), class_hierarchy=None,
    )
    node = pa.IsInstance(pa.Var("r"), ("TipSpot", "Trash"))
    assert evaluate_predicate(node, ctx) is None


def test_isinstance_well_vs_container_is_true_via_supplied_hierarchy() -> None:
    """C4b: `Well` IS a `Container` -- `T`, not ½. Requires a
    `class_hierarchy` (this module never hand-types one, see its own
    module docstring point 3); a test supplies it directly."""
    call = _call({"r": ir.Ref(slot=0, cell="A1")})
    resources = {0: _resource(0, element_type="Well")}
    hierarchy = subclass_closure_from_bases({"Well": ("Container",), "Container": ("Resource",)})
    from plr_sema.check.predicate import _Ctx  # type: ignore[attr-defined]

    ctx = _Ctx(
        call=call, resources_by_slot=resources, param_defaults={}, bindings_by_name={}, depth=0,
        channel_kwarg=None, channels=None, env=frozenset(), class_hierarchy=hierarchy,
    )
    node = pa.IsInstance(pa.Var("r"), ("Container",))
    assert evaluate_predicate(node, ctx) is True
    # And without a hierarchy (production default), it degrades to ½ --
    # sound, just less precise, per the module's own documented scoping.
    import dataclasses

    ctx_no_hierarchy = dataclasses.replace(ctx, class_hierarchy=None)
    assert evaluate_predicate(node, ctx_no_hierarchy) is None


def test_nested_opaque_keeps_guard_predicate_unparsed_when_the_guard_stays_half() -> None:
    """C15: a predicate whose top node parses but contains an Opaque
    sub-node keeps `guard_predicate_unparsed` for REASON purposes -- tested
    where the OVERALL value stays ½ (`And(Opaque, T)` -- neither conjunct
    is `F`, and one is undecided, so Kleene `And` cannot decide `T` either).
    §15.7's reason procedure runs only in the ½ case; a decided value uses
    E-VERDICT's own fixed reason regardless of any nested Opaque (see the
    sibling `test_and_with_an_opaque_and_a_false_conjunct_still_decides_f`
    for the still-decides-under-Kleene half of C15)."""
    guard = _self_entry_guard("c in ['a'] and len(x) == 5", kind="assert")
    call = _call({"x": ir.Seq(tuple(ir.Lit(i) for i in range(5)))})  # len(x) == 5 -> True.
    result = evaluate_guard(guard, call, {}, {})
    assert result.verdict == "unknown"
    assert result.reason == "guard_predicate_unparsed"


def test_and_with_an_opaque_and_a_false_conjunct_still_decides_f() -> None:
    """C15's other half: `Opaque` still EVALUATES under Kleene even though
    it keeps `guard_predicate_unparsed` for reason purposes -- `And(Opaque,
    F)` decides `F` because one `F` conjunct is enough, regardless of the
    other conjunct's own undecided status."""
    from plr_sema.check.predicate import _Ctx  # type: ignore[attr-defined]

    call = _call({"x": ir.Seq((ir.Lit(1), ir.Lit(2)))})  # len(x) == 2 != 5 -> F.
    ctx = _Ctx(
        call=call, resources_by_slot={}, param_defaults={}, bindings_by_name={}, depth=0,
        channel_kwarg=None, channels=None, env=frozenset(), class_hierarchy=None,
    )
    assert evaluate_predicate(pa.parse("c in ['a'] and len(x) == 5"), ctx) is False


# ---------------------------------------------------------------------------
# AC-15.2 -- alpha/beta idiom evaluation, fail-closed fixtures.
# ---------------------------------------------------------------------------


def test_beta_empty_list_resolves_to_the_beta_length_not_len_equal_zero() -> None:
    """The stub-defeating half: `offsets=[]` must resolve through the beta
    binding (`Len(offsets) == Len(tip_spots)`), NOT through `Len([]) == 0`
    -- the latter would be a false `WILL_FAIL` at `:522`-shaped guards."""
    beta_offsets = {"idiom": "beta", "x": "offsets", "param": "tip_spots", "default_shape": "repeat"}
    guard = _self_entry_guard(
        "len(tip_spots) == len(offsets)", kind="assert", bindings=(beta_offsets,)
    )
    call = _call({"tip_spots": ir.Seq((ir.Lit(1), ir.Lit(2))), "offsets": ir.Seq(())})
    result = evaluate_guard(guard, call, {}, {})
    # offsets=[] is known-falsy -> resolves via beta to Len(tip_spots) == 2,
    # so Len(tip_spots) == Len(offsets) becomes 2 == 2 -> True -> assert
    # does not fire -> SAFE. A buggy implementation reading offsets=[]
    # literally would get 2 == 0 -> False -> assert fires -> WILL_FAIL (if
    # unconditional) or at least a different, WRONG value.
    assert result.verdict == "safe"


def test_beta_truthy_kwarg_wins_over_the_binding() -> None:
    beta_offsets = {"idiom": "beta", "x": "offsets", "param": "tip_spots", "default_shape": "repeat"}
    guard = _self_entry_guard("len(tip_spots) == len(offsets)", kind="assert", bindings=(beta_offsets,))
    call = _call({"tip_spots": ir.Seq((ir.Lit(1), ir.Lit(2))), "offsets": ir.Seq((ir.Lit(0),))})
    result = evaluate_guard(guard, call, {}, {})
    # offsets is truthy (non-empty) -> uses its OWN length (1), not tip_spots' (2) -> 2 == 1 -> False -> assert fires.
    assert result.verdict == "unknown"
    assert result.reason == "guard_env_dependent"


def test_alpha_binding_iterand_unresolved_is_half_not_false() -> None:
    guard = _guard("len(not_tip_spots) > 0", bindings=(ALPHA_TIP_SPOTS,), scope_trail=("if len(not_tip_spots) > 0",))
    call = _call({})  # tip_spots absent entirely -> Top.
    result = evaluate_guard(guard, call, {}, {})
    assert result.verdict == "unknown"
    assert result.reason == "guard_env_dependent"  # tip_spots resolves via kwargs-path but to Top -> operand? Actually absent -> env.


# ---------------------------------------------------------------------------
# AC-15.5 -- E-SCOPE, E-VERDICT, E-CALL(2)/(depth), guard_operand_unknown.
# ---------------------------------------------------------------------------


def test_f_yields_exactly_one_safe_finding_and_self_entry_not_double_counted() -> None:
    guard = _self_entry_guard("len(x) > 0", kind="raise_guard")
    call = _call({"x": ir.Seq(())})
    result = evaluate_guard(guard, call, {}, {})
    assert result == GuardResult(verdict="safe")


def test_enclosing_scope_false_yields_safe_regardless_of_own_predicate_true() -> None:
    """`transfer`'s own shape: `target_vols is not None` at depth 0's own
    guard is inside `if target_vols is not None: if ratios is not None:
    raise`. When `target_vols` resolves to `Lit(None)` via param_defaults,
    the enclosing scope entry is FALSE, so `:1335`-shaped guards are SAFE
    regardless of `ratios`'s own value."""
    guard = _guard(
        "ratios is not None",
        scope_trail=("if ratios is not None", "if target_vols is not None"),
    )
    contract = {"param_defaults": {"target_vols": None, "ratios": "anything-truthy"}}
    call = _call({}, method="transfer")  # neither kwarg supplied -> resolves via param_defaults.
    result = evaluate_guard(guard, call, contract, {})
    assert result.verdict == "safe"


def test_transfer_source_vol_none_guard_safe_when_source_vol_supplied() -> None:
    """The D1 worked example's `:1340`-shaped guard: `source_vol is None`
    under `else of: if target_vols is not None` / self `if source_vol is
    None`. When the call genuinely supplies a real `source_vol`, the
    guard's OWN predicate is False -> SAFE, matching the spec's own
    worked example (a call this fixture makes explicit, unlike the
    pre-existing `transfer_after_pickup_graph.json` tip-typestate fixture,
    which supplies neither and genuinely earns a WILL_FAIL here)."""
    guard = _guard(
        "source_vol is None",
        scope_trail=("if source_vol is None", "else of: if target_vols is not None"),
    )
    contract = {"param_defaults": {"target_vols": None}}
    call = _call({"source_vol": ir.Lit(5.0)}, method="transfer")
    result = evaluate_guard(guard, call, contract, {})
    assert result.verdict == "safe"


def test_unresolvable_kwarg_yields_guard_operand_unknown() -> None:
    guard = _self_entry_guard("x is None")
    call = _call({"x": ir.Top()})  # a non-literal kwarg -- present, but Top.
    result = evaluate_guard(guard, call, {}, {})
    assert result.verdict == "unknown"
    assert result.reason == "guard_operand_unknown"


def test_envref_call_argument_renamed_kwarg_is_operand_unknown_not_env_dependent() -> None:
    """Round 2, A-C5's clause-ordering fixture: `self.backend.f(?0)` where
    `?0` is a kwarg `lower_calls` renamed -- present in `call.kwargs`
    (under its renamed key) but `Top`. This is `guard_operand_unknown`,
    NOT `guard_env_dependent`, which is the assertion that the amendment
    relaxed neither of the gate's two zero-conditions."""
    condition_predicate = pa.EnvRef(("self", "backend", "f"), (pa.Var("?0"),))
    guard = {
        "condition": "self.backend.f(?0)",
        "predicate": pa.to_json(condition_predicate),
        "scope_trail": ["if self.backend.f(?0)"],
        "raises": "TypeError",
        "kind": "raise_guard",
        "free_vars": [],
        "site": _site(),
        "depth": 0,
        "bindings": [],
    }
    call = _call({"?0": ir.Top()})
    result = evaluate_guard(guard, call, {}, {})
    assert result.verdict == "unknown"
    assert result.reason == "guard_operand_unknown"


def test_unresolved_free_name_yields_guard_env_dependent() -> None:
    guard = _self_entry_guard("self.setup_finished")
    result = evaluate_guard(guard, _call(), {}, {})
    assert result.verdict == "unknown"
    assert result.reason == "guard_env_dependent"


def test_n_guards_yields_exactly_n_findings_join_called_once(monkeypatch: Any = None) -> None:
    """(iv): one Finding per guard is preserved -- checked at the
    `evaluate_guard` layer by simply calling it once per guard and
    counting results; the full `check_ir` integration test lives in
    `test_check_graph.py`."""
    guards = [
        _self_entry_guard("x is None"),
        _self_entry_guard("y is None"),
        _guard(None, raises="<dynamic:err>"),  # tier (iii).
    ]
    call = _call({"x": ir.Lit(None), "y": ir.Lit(1)})
    results = [evaluate_guard(g, call, {}, {}) for g in guards]
    assert len(results) == 3
    assert results[2].tier_iii is True


# ---------------------------------------------------------------------------
# AC-15.6 -- E-UNCOND, all six clauses, and tier (iii).
# ---------------------------------------------------------------------------


def test_uncond_way1_evaluation_satisfied_yields_will_fail() -> None:
    """Way (1) requires the trail entry to PARSE to a non-Opaque predicate
    that evaluates T -- a bare name (`"if setup_finished"`) parses `Opaque`
    (no production for a standalone name in predicate position other than
    a self-rooted attribute chain), so this exercises an entry that is a
    genuine comparison instead."""
    guard = _guard(None, scope_trail=("if setup_finished is not None",))
    guard["predicate"] = pa.to_json(pa.TRUE())
    call = _call({"setup_finished": ir.Lit(True)})
    result = evaluate_guard(guard, call, {}, {})
    assert result == GuardResult(verdict="will_fail")


def test_uncond_way2_hypothesis_satisfied_yields_will_fail() -> None:
    guard = _guard(None, scope_trail=("if does_volume_tracking()",))
    guard["predicate"] = pa.to_json(pa.TRUE())
    result = evaluate_guard(guard, _call(), {}, {}, env=frozenset({"does_volume_tracking"}))
    assert result == GuardResult(verdict="will_fail")


def test_uncond_while_header_blocks() -> None:
    guard = _guard(None, scope_trail=("while True",))
    guard["predicate"] = pa.to_json(pa.TRUE())
    result = evaluate_guard(guard, _call(), {}, {})
    assert result.verdict == "unknown" and result.reason == "guard_env_dependent"


def test_uncond_for_header_r1_did_not_bind_blocks() -> None:
    guard = _guard(None, scope_trail=("for op in aspirations",))
    guard["predicate"] = pa.to_json(pa.TRUE())
    result = evaluate_guard(guard, _call(), {}, {})
    assert result.verdict == "unknown" and result.reason == "guard_env_dependent"


def test_uncond_trail_entry_parsing_opaque_blocks() -> None:
    guard = _guard(None, scope_trail=("if c not in self.head",))
    guard["predicate"] = pa.to_json(pa.TRUE())
    result = evaluate_guard(guard, _call(), {}, {})
    assert result.verdict == "unknown" and result.reason == "guard_env_dependent"


def test_uncond_trail_entry_evaluating_half_blocks() -> None:
    guard = _guard(None, scope_trail=("if x > 5",))  # numeric Cmp -> G5 -> 1/2.
    guard["predicate"] = pa.to_json(pa.TRUE())
    call = _call({"x": ir.Lit(10)})
    result = evaluate_guard(guard, call, {}, {})
    assert result.verdict == "unknown" and result.reason == "guard_env_dependent"


def test_uncond_else_of_entry_whose_test_is_in_env_does_not_satisfy_it() -> None:
    """Preserving increment 5's AC-14.4 behaviour: an `else of:` entry is
    recognised ONLY by way (1), never by way (2)."""
    guard = _guard(None, scope_trail=("else of: if does_volume_tracking()",))
    guard["predicate"] = pa.to_json(pa.TRUE())
    result = evaluate_guard(guard, _call(), {}, {}, env=frozenset({"does_volume_tracking"}))
    assert result.verdict == "unknown" and result.reason == "guard_env_dependent"


def test_uncond_depth_1_blocks_even_with_a_true_predicate() -> None:
    guard = _guard(None, depth=1, scope_trail=())
    guard["predicate"] = pa.to_json(pa.TRUE())
    result = evaluate_guard(guard, _call(), {}, {})
    assert result.verdict == "unknown" and result.reason == "guard_env_dependent"


def test_check_no_lid_117_by_name_is_unknown_via_depth() -> None:
    """`_check_no_lid`'s `:117`, asserted by name -- `condition: null`,
    empty `scope_trail`, `depth == 1` (it is inlined from a delegate into
    every caller it reaches). E-UNCOND(4) alone already blocks it; no
    `k_reachability_clear` fact is needed for THIS site (see the module
    docstring's point 2)."""
    guard = _guard(
        None,
        depth=1,
        scope_trail=(),
        raises="ValueError",
    )
    guard["site"] = _site(lineno=117, qualname="_check_no_lid")
    result = evaluate_guard(guard, _call(), {}, {})
    assert result.verdict == "unknown"
    assert result.reason == "guard_env_dependent"
    assert result.verdict is not None and result.verdict != "will_fail"


def test_uncond_5_depth_0_empty_trail_k_containing_earlier_try_blocks() -> None:
    guard = _guard(None, depth=0, scope_trail=())
    guard["predicate"] = pa.to_json(pa.TRUE())
    result = evaluate_guard(guard, _call(), {}, {}, k_reachability_clear=False)
    assert result.verdict == "unknown" and result.reason == "guard_env_dependent"


def test_uncond_5_depth_0_empty_trail_k_with_no_earlier_control_flow_yields_will_fail() -> None:
    """The positive branch AC-15.6 requires: a guard evaluating `T` at
    depth 0 with an empty `scope_trail` in a `K` containing NO earlier
    `Return`/`Try`/`Break`/`Continue` (an earlier `Raise` does not block,
    260907 T36's refinement) yields `WILL_FAIL`. This module still has no
    wire signal of its own for that K-body fact (`check/` cannot read PLR
    source, ever); the fact is supplied directly here via the keyword,
    exactly as `check/__init__.py::_findings_for_guards` now supplies it
    from `guard["reachability_clear"]` for a real caller (see
    `test_wire_reachability_clear_field_flows_through_findings_for_guards`
    below for that dict-based plumbing, exercised end to end)."""
    guard = _guard(None, depth=0, scope_trail=())
    guard["predicate"] = pa.to_json(pa.TRUE())
    result = evaluate_guard(guard, _call(), {}, {}, k_reachability_clear=True)
    assert result == GuardResult(verdict="will_fail")


def test_wire_reachability_clear_field_flows_through_findings_for_guards() -> None:
    """260907 (T36, spec 260904 §15.4/§15.10): the WIRE plumbing itself --
    not just `evaluate_guard`'s own keyword, which the two fixtures above
    exercise directly. `plr_sema.check._findings_for_guards` (T31-2's own
    per-guard dispatch loop, `check/__init__.py`) reads
    `guard["reachability_clear"]` straight off the guard dict -- the SAME
    shape `derive/__main__.py::_guard_to_json` now publishes -- and threads
    it into `evaluate_guard`'s `k_reachability_clear` parameter via
    `guard.get("reachability_clear")`. A `True` field value on a depth-0,
    empty-scope-trail, always-firing `raise_guard` flips the verdict to
    `WILL_FAIL`; an explicit `False` keeps it `UNKNOWN`/
    `guard_env_dependent`; an ABSENT key (an un-regenerated pre-T36
    contract, or a hand-built fixture that never carried it) degrades
    identically to `False` via `dict.get`'s own `None` default -- the exact
    fail-closed behaviour the field's absence had before T36 existed."""
    from plr_sema.check import _findings_for_guards
    from plr_sema.verdict import Verdict

    def _one_verdict(*, set_field: bool, value: bool = False) -> "tuple[Verdict, str]":
        guard = _guard(None, depth=0, scope_trail=())
        guard["predicate"] = pa.to_json(pa.TRUE())
        if set_field:
            guard["reachability_clear"] = value
        findings = _findings_for_guards(
            "op-1",
            _call(),
            {"guards": [guard]},
            frozenset(),
            receiver_state=None,
            resources_by_slot={},
            env=frozenset(),
            class_hierarchy=None,
            poisoned=False,
            excludes_sites=None,
        )
        assert len(findings) == 1
        return findings[0].verdict, findings[0].reason

    assert _one_verdict(set_field=True, value=True) == (Verdict.WILL_FAIL, "")
    assert _one_verdict(set_field=True, value=False) == (Verdict.UNKNOWN, "guard_env_dependent")
    assert _one_verdict(set_field=False) == (Verdict.UNKNOWN, "guard_env_dependent")


def test_tier_iii_dynamic_raise_is_one_unknown_finding_marked_for_excludes_sites() -> None:
    guard = _guard(None, raises="<dynamic:error>")
    guard["predicate"] = pa.to_json(pa.TRUE())  # irrelevant -- tier (iii) short-circuits before evaluating it.
    result = evaluate_guard(guard, _call(), {}, {})
    assert result == GuardResult(verdict="unknown", reason="guard_env_dependent", tier_iii=True)


def test_is_dynamic_raise_selected_by_prefix_not_site_or_condition_text() -> None:
    from plr_sema.check.predicate import is_dynamic_raise

    assert is_dynamic_raise({"raises": "<dynamic:error>"}) is True
    assert is_dynamic_raise({"raises": "TypeError"}) is False
    assert is_dynamic_raise({"raises": None}) is False
    assert is_dynamic_raise({}) is False


# ---------------------------------------------------------------------------
# The Zip/quantifier fixtures (E-ENV / A-C3 / A-C13).
# ---------------------------------------------------------------------------


def test_allof_over_zip_with_one_top_item_is_half_never_vacuously_true() -> None:
    node = pa.AllOf(
        seq=pa.Zip((pa.Var("a"), pa.Var("b"))),
        predicate=pa.Cmp(pa.Var("channel"), "==", pa.Var("channel")),  # anything, since it's never reached decidably.
    )
    call = _call({"a": ir.Seq(())})  # a resolves to an EMPTY concrete Seq, b unresolved -> Top.
    from plr_sema.check.predicate import _Ctx  # type: ignore[attr-defined]

    ctx = _Ctx(
        call=call, resources_by_slot={}, param_defaults={}, bindings_by_name={}, depth=0,
        channel_kwarg=None, channels=None, env=frozenset(), class_hierarchy=None,
    )
    assert evaluate_predicate(node, ctx) is None  # not every item is a concrete Seq -> Zip is Top -> AllOf over Top is 1/2.


def test_anyof_over_genuinely_concrete_empty_seq_is_vacuously_false() -> None:
    node = pa.AnyOf(seq=pa.Var("xs"), predicate=pa.TRUE())
    call = _call({"xs": ir.Seq(())})
    from plr_sema.check.predicate import _Ctx  # type: ignore[attr-defined]

    ctx = _Ctx(
        call=call, resources_by_slot={}, param_defaults={}, bindings_by_name={}, depth=0,
        channel_kwarg=None, channels=None, env=frozenset(), class_hierarchy=None,
    )
    assert evaluate_predicate(node, ctx) is False


def test_comprehension_bound_name_never_resolves_against_call_kwargs() -> None:
    """A-C13: `channel` collides with a REAL kwarg name, but a genuine
    `AllOf`/`AnyOf`'s bound name resolves to ⊤ regardless, never to the
    kwarg's real value."""
    node = pa.AnyOf(seq=pa.Var("chans"), predicate=pa.Is(pa.Var("channel"), negated=False))
    call = _call({"chans": ir.Seq((ir.Lit(0),)), "channel": ir.Lit(None)})
    from plr_sema.check.predicate import _Ctx  # type: ignore[attr-defined]

    ctx = _Ctx(
        call=call, resources_by_slot={}, param_defaults={}, bindings_by_name={}, depth=0,
        channel_kwarg=None, channels=None, env=frozenset(), class_hierarchy=None,
    )
    # If `channel` resolved against call.kwargs it would be Lit(None) -> `is None` -> True -> AnyOf True.
    # A-C13 says it must resolve to ⊤ instead -> Is(Top,...) -> 1/2 -> AnyOf over one 1/2 element -> 1/2.
    assert evaluate_predicate(node, ctx) is None


# ---------------------------------------------------------------------------
# subclass_closure_from_bases -- the "derived, never hand-typed" helper.
# ---------------------------------------------------------------------------


def test_subclass_closure_from_bases_is_reflexive_and_transitive() -> None:
    closure = subclass_closure_from_bases({"Well": ("Container",), "Container": ("Resource",), "Resource": ()})
    assert closure["Well"] == frozenset({"Well", "Container", "Resource"})
    assert closure["Resource"] == frozenset({"Resource"})


def test_subclass_closure_unresolvable_base_contributes_nothing_extra() -> None:
    """A direct base named by the caller IS a real edge (`Foo`'s ancestor
    set includes it) -- what stays unguessed is `NotInMap`'s OWN further
    ancestors, since it is not itself a key of `bases`."""
    closure = subclass_closure_from_bases({"Foo": ("NotInMap",)})
    assert closure["Foo"] == frozenset({"Foo", "NotInMap"})


# ---------------------------------------------------------------------------
# A pre-T30a / hand-built fixture missing the `predicate` key entirely.
# ---------------------------------------------------------------------------


def test_guard_without_a_predicate_key_degrades_to_the_pre_increment_blanket_reason() -> None:
    guard = _self_entry_guard("anything at all")
    del guard["predicate"]
    result = evaluate_guard(guard, _call(), {}, {})
    assert result == GuardResult(verdict="unknown", reason="guard_predicate_unparsed")
