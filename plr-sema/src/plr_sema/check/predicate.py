"""plr_sema.check.predicate: the Kleene three-valued guard evaluator
(increment 6, spec 260904 §15.4/§15.5/§15.7, T31-1).

**Scope.** This module turns a `predicate_ast.Predicate` (already parsed at
derive time, §15.2/§15.3's grammar and local-binding idioms) into a
verdict against ONE concrete `ir.Call`: E-CALL (operand resolution),
E-TYPE (`IsInstance` against a `RESOURCE`'s declared type), E-SCOPE (an
unsatisfied enclosing scope makes `SAFE` true regardless of the guard's own
predicate), E-VERDICT (predicate truth -> `Finding`), E-UNCOND (the six
clauses gating `WILL_FAIL`), E-ENV (`EnvRef`/`Zip`/membership all decide
nothing this increment), and §15.7's reason-assignment procedure. Wiring
the result into a `Finding` and into `check_ir`'s walk is T31-2
(`plr_sema.check.__init__`), not this module's job.

**Import boundary.** Same as the rest of `check/` (module docstring of
`plr_sema.check`): no `pylabrobot`, no `libcst`, no `pydantic`, no
filesystem access, no shelling out. This module DOES import
`plr_sema.derive.predicate_ast` and `plr_sema.derive.bindings` --
`check/volumestate.py` already crosses this exact boundary (importing
`plr_sema.derive.receiver_state.volume_guard_is_unconditional`), so this is
not a new precedent; both modules are pure, stdlib-only Python with no
transitive `pylabrobot`/`libcst` import.

**What this module does NOT have data for (documented, not silently
guessed).**

1. **E-CALL(5), the parameter-rebinding clause, for a NON-beta-bound
   parameter.** The wire carries `InlinedGuard.bindings` -- the alpha/beta
   idiom MATCHES only (§15.3) -- and nothing else about whether an
   arbitrary parameter is rewritten before a guard reads it. For a
   parameter with a recorded BETA binding, E-CALL(5)'s "resolves to ⊤
   unless the write is beta-preserving and the term is a `Len`" is exactly
   what E-CALL(β) (below) implements. For a parameter with NO recorded
   binding at all (the deferred gamma idiom's own territory, §15.13 --
   `resources` at `:999`/`:1172`, `ratios` at `:1343`, the `zip(...)`-based
   rebinding of `offsets` at `:1004`/`:1177`), this module has no positive
   signal of rebinding and resolves the name via the ordinary E-CALL steps
   (1)-(4) -- exactly as if it had never been rebound. This is a
   DELIBERATE, DOCUMENTED scoping decision (not an oversight): building the
   general "is this parameter written anywhere in K" fact requires either a
   new derived field (T31's own file list excludes every `plr_sema.derive`
   module) or reusing gamma's own machinery, which §15.13/§15.16 record as
   NOT adopted this increment. None of `pick_up_tips`'s three gate-relevant
   guards (`:498`, `:502`, `:522`) is affected: `:498`'s free name resolves
   via an ALPHA binding, and `:502`/`:522`'s `use_channels`/`offsets` are
   both in the measured BETA population.
2. **E-UNCOND(5)'s K-body fact** -- REFINED and WIRED, 260907, T36 (spec
   §15.4/§15.10): `True` iff `K`'s body has no earlier `ast.Return`, is not
   lexically inside an `ast.Try`/`ast.With`/`ast.AsyncWith`, and has no
   earlier `ast.Break`/`ast.Continue` (an earlier `ast.Raise` does NOT
   block -- clause (5) is a claim about the operation, scored at the
   failing call's own index, not about the raise site). This module still
   cannot compute the fact itself (no PLR source access, ever -- module
   docstring of `plr_sema.check`); `plr_sema.derive.bindings
   .compute_reachability_clear` computes it at DERIVE time against the SAME
   `K` `bindings` already uses, and `derive/__main__.py::_guard_to_json`
   publishes it as the additive `guard["reachability_clear"]` wire field.
   `evaluate_guard`'s `k_reachability_clear: bool | None` parameter is now
   fed from that field (`check/__init__.py`'s call site); an
   un-regenerated pre-T36 artifact or a hand-built fixture with no such key
   still degrades to `None` -- "not established", fail-closed, per
   E-UNCOND(5)'s own text ("Otherwise ½ and `guard_env_dependent`") --
   UNCHANGED from before this field existed. `_check_no_lid`'s `:117` --
   the fixture AC-15.6 names by site -- resolves `reachability_clear=False`
   on the real corpus (an earlier `return` at `:114` blocks it) when
   inlined at depth >= 1 it is already disposed of at DEPTH (E-UNCOND(4))
   before clause (5) is even reached, so this is observable only via its
   own standalone (depth-0) contract entry, never via `aspirate`/
   `dispense`'s inlined view of it. `tests/test_predicate.py` exercises
   clause (5) directly, at depth 0, with the fact supplied explicitly, to
   prove the positive branch is implemented and not merely defaulted away;
   `tests/test_derive.py` exercises `compute_reachability_clear` itself
   against synthetic `K` bodies and the real `pick_up_tips`/`_check_no_lid`
   sites.
3. **E-TYPE's subclass relation.** `RESOURCE.type`/`element_type` are
   PLR class-name strings; deciding `IsInstance` beyond bare string equality
   needs the PLR class hierarchy, which `plr_sema.derive.receiver_state
   .build_plr_class_index` derives from PLR source at DERIVE time (never at
   check time -- this module cannot read PLR source, by the same import
   boundary as point 2). `evaluate_guard` accepts an optional
   `class_hierarchy: Mapping[str, frozenset[str]]` (name -> its own
   reflexive-transitive ancestor set); `None` (every real production caller
   today, since no such artifact is shipped in `derived_contracts.json` at
   this pin) degrades to EXACT-NAME EQUALITY ONLY -- sound, just less
   precise: `IsInstance(term, (Ti, ...))` still decides `T` whenever the
   declared name IS one of the `Ti`s (exactly `:498`'s own case --
   `element_type == "TipSpot"` against `(TipSpot,)`), and stays ½ rather
   than fabricating a subclass relation it was never handed. This module
   supplies :func:`subclass_closure_from_bases`, a small, generic (no PLR
   knowledge) graph-closure helper over a caller-supplied `{name: direct
   bases}` map, so a caller WITH PLR source access (or a test) can build one
   cheaply without a hand-typed hierarchy living inside this file -- exactly
   the "derived, never hand-typed" property §15.8 requires, satisfied by
   keeping the derivation outside this module rather than inlining a
   PLR-specific table here (`live_rows()`/`BUDGET_CAP` have zero headroom
   this increment; a new hand-typed hierarchy table would also be an
   unregistered HM surface).
4. **E-UNCOND way (3), the structural `for`-loop recognition (R1).**
   Increment 5's R1 recognises a scope entry by POSITION against a
   `for_span` field -- but that field lives on the volume bridge's own
   per-guard JSON (`derive/receiver_state.py`'s `caller_scope`/`for_span`,
   attached by P10), NOT on `InlinedGuard` (nine fields, none of them
   `for_span` -- §15.4's own citation). A guard this module evaluates
   (i.e. one the tip/volume families did not already claim) therefore never
   carries `for_span` data, so way (3) is implemented as a total function
   that is ALWAYS unsatisfied for this guard family at this pin -- not
   silently skipped, just never able to fire for lack of the one field it
   needs. `evaluate_guard` accepts no `for_span` parameter because there is
   nowhere on the wire to have gotten one from.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from plr_sema.check import ir
from plr_sema.derive import bindings as bindings_mod
from plr_sema.derive import predicate_ast as pa

__all__ = [
    "GuardResult",
    "evaluate_guard",
    "evaluate_predicate",
    "evaluate_term",
    "subclass_closure_from_bases",
    "is_dynamic_raise",
]


# ---------------------------------------------------------------------------
# Kleene three-valued truth: True (T), False (F), None (½). No new type --
# Python's own three states are exactly G1's three values, and every
# consumer of this module already speaks `bool | None` fluently.
# ---------------------------------------------------------------------------

_Tri = "bool | None"


def _kleene_not(v: "bool | None") -> "bool | None":
    return v if v is None else (not v)


# ---------------------------------------------------------------------------
# The evaluation context. One instance per guard; `var_override` is the
# ONLY field ever rebound mid-evaluation (via `dataclasses.replace`), for
# the alpha-idiom's real per-item substitution and for a genuine
# `AllOf`/`AnyOf`'s comprehension-bound-name-is-always-TOP rule (A-C13).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Ctx:
    call: ir.Call
    resources_by_slot: Mapping[int, ir.Resource]
    param_defaults: Mapping[str, Any]  # already {} when depth >= 1 (E-CALL(depth))
    bindings_by_name: Mapping[str, Mapping[str, Any]]
    depth: int
    channel_kwarg: "str | None"
    channels: "tuple[int, ...] | None"
    env: "frozenset[str]"
    class_hierarchy: "Mapping[str, frozenset[str]] | None"
    var_override: Mapping[str, ir.Value] = field(default_factory=dict)
    override_all_to_top: bool = False  # A-C13: a genuine AllOf/AnyOf's bound name(s)


def _with_override(ctx: _Ctx, override: Mapping[str, ir.Value]) -> _Ctx:
    merged = dict(ctx.var_override)
    merged.update(override)
    return replace(ctx, var_override=merged, override_all_to_top=False)


def _with_all_to_top(ctx: _Ctx) -> _Ctx:
    return replace(ctx, var_override={}, override_all_to_top=True)


# ---------------------------------------------------------------------------
# E-CALL: Var(name) -> (ir.Value, origin). origin is "operand" (found a home
# via call.kwargs / param_defaults / the channel special-case / an alpha-beta
# binding -- whatever the resulting VALUE is) or "env" (case 4 -- nothing
# found at all, or E-CALL(depth)'s forbiddance fired).
# ---------------------------------------------------------------------------

_JSON_SCALAR = (bool, int, float, str, type(None))


def _lit_of(value: Any) -> ir.Lit:
    return ir.Lit(value if isinstance(value, _JSON_SCALAR) else None)


def _is_known_falsy(value: ir.Value) -> bool:
    if isinstance(value, ir.Lit):
        v = value.v
        return v is None or v is False or v == 0
    if isinstance(value, ir.Seq):
        return len(value.items) == 0
    return False


def _is_known_truthy(value: ir.Value) -> bool:
    if isinstance(value, ir.Lit):
        v = value.v
        if isinstance(v, bool):
            return v is True
        if v is None:
            return False
        try:
            return bool(v)
        except Exception:  # noqa: BLE001 -- conservatively not-truthy on anything odd.
            return False
    if isinstance(value, ir.Ref):
        return True  # a resolved resource reference is always truthy in PLR.
    if isinstance(value, ir.Seq):
        return len(value.items) > 0
    return False


def _resolve_var(name: str, ctx: _Ctx) -> "tuple[ir.Value, str]":
    """Returns `(value, origin)`. `origin == "operand"` iff resolution found
    a home via `call.kwargs` / `param_defaults` / the channel special-case /
    an alpha-beta binding -- REGARDLESS of whether the resulting value is
    concrete or `ir.Top()`; `origin == "env"` iff nothing was found at all
    (E-CALL case 4) or E-CALL(depth) forbade the lookup outright. §15.7's
    `guard_operand_unknown` clause fires on an "operand"-origin `Top`;
    `guard_env_dependent`'s catch-all fires on an "env"-origin `Top`.
    """
    if ctx.override_all_to_top:
        # A-C13: a genuine AllOf/AnyOf comprehension-bound name is ALWAYS
        # ⊤ and NEVER resolved against call.kwargs, even on a name
        # collision with a real parameter -- checked FIRST, before even
        # the channel special-case, because A-C13 is unconditional.
        return ir.Top(), "operand"
    if name in ctx.var_override:
        return ctx.var_override[name], "operand"
    if ctx.channel_kwarg is not None and name == ctx.channel_kwarg:
        if ctx.channels is not None:
            return ir.Seq(tuple(ir.Lit(c) for c in ctx.channels)), "operand"
        return ir.Top(), "operand"
    if ctx.depth == 0:
        if name in ctx.call.kwargs:
            return ctx.call.kwargs[name], "operand"
        if name in ctx.param_defaults:
            return _lit_of(ctx.param_defaults[name]), "operand"
    binding = ctx.bindings_by_name.get(name)
    if binding is not None:
        # Both idioms: a BARE (non-Len) reference has no term substitute
        # (alpha binds elements via Filtered, evaluated only through the
        # G3 emptiness idiom below; beta binds only a length). The binding
        # itself IS the "home found" -- origin is "operand" even though the
        # bare value is Top, matching E-CALL(depth)'s own carve-out ("an
        # alpha/beta binding in the delegate's own body" is one of the two
        # things depth->=1 STILL permits).
        return ir.Top(), "operand"
    return ir.Top(), "env"


def _resolve_term(term: "pa.Term", ctx: _Ctx) -> ir.Value:
    if isinstance(term, pa.Lit):
        return _lit_of(term.value)
    if isinstance(term, pa.Var):
        value, _origin = _resolve_var(term.name, ctx)
        return value
    if isinstance(term, pa.Len):
        n = _resolve_len(term.term, ctx)
        return ir.Top() if n is None else ir.Lit(n)
    if isinstance(term, (pa.SetOf, pa.Attr, pa.Filtered, pa.Zip)):
        # SetOf/Filtered are only ever meaningful through the G3/G4 special
        # cases below (which never call `_resolve_term` on them directly);
        # Attr has no ir.Value shape to resolve to (E-CALL: "resolved or ⊤
        # by E-CALL" -- always ⊤ here, no attribute-value modelling
        # exists); Zip is only meaningful through the quantifier-length
        # special case. Reached here only for a shape used OUTSIDE its one
        # meaningful context -- fail-closed to ⊤.
        return ir.Top()
    if isinstance(term, pa.EnvRef):
        return ir.Top()  # E-ENV: ⊤ in term position, unconditionally.
    raise TypeError(f"_resolve_term: unrecognized term {type(term)!r}")


def _resolve_len(term: "pa.Term", ctx: _Ctx) -> "int | None":
    if isinstance(term, pa.Var):
        binding = ctx.bindings_by_name.get(term.name)
        if binding is not None and binding.get("idiom") == "beta":
            return _resolve_beta_len(binding, ctx)
        if binding is not None and binding.get("idiom") == "alpha":
            # A generic (non-G3-idiom) Len of an alpha-bound name -- not
            # exercised at this pin (every real alpha-bound name's only
            # Len use IS the G3 idiom, handled at the Cmp level before
            # `_resolve_len` is ever called on it) -- fail-closed to ⊤.
            return None
    value = _resolve_term(term, ctx)
    if isinstance(value, ir.Seq):
        return len(value.items)
    return None


def _resolve_beta_len(binding: Mapping[str, Any], ctx: _Ctx) -> "int | None":
    """E-CALL(β), the truthiness interaction. `binding["x"]` is the
    rebound parameter name (`use_channels`); `binding["param"]` is the
    arity source (`tip_spots`)."""
    x = binding["x"]
    param = binding["param"]
    if x in ctx.call.kwargs:
        kwarg_val = ctx.call.kwargs[x]
        if _is_known_falsy(kwarg_val):
            return _resolve_len(pa.Var(param), ctx)  # rule 1
        if _is_known_truthy(kwarg_val):
            return _len_of_value(kwarg_val)  # rule 2
        return None  # present but neither provably falsy nor truthy -> rule 4
    # x absent from call.kwargs -- rule 3, else rule 4.
    has_default = ctx.depth == 0 and x in ctx.param_defaults
    if has_default and _is_known_falsy(_lit_of(ctx.param_defaults[x])):
        return _resolve_len(pa.Var(param), ctx)  # rule 3
    return None  # rule 4


def _len_of_value(value: ir.Value) -> "int | None":
    if isinstance(value, ir.Seq):
        return len(value.items)
    return None


# ---------------------------------------------------------------------------
# E-TYPE.
# ---------------------------------------------------------------------------


def subclass_closure_from_bases(bases: Mapping[str, "tuple[str, ...]"]) -> "dict[str, frozenset[str]]":
    """A small, GENERIC (no PLR knowledge) reflexive-transitive closure over
    a caller-supplied `{name: direct base names}` map -- e.g. `{"Well":
    ("Container",), "Container": ("Resource",)}` -> `{"Well": {"Well",
    "Container", "Resource"}, ...}`. A base name absent from `bases` simply
    contributes nothing further (fail-closed: an unresolvable base is never
    guessed at). This is the "derived, never hand-typed" mechanism §15.8
    requires -- the PLR-specific data (which classes have which bases)
    lives in whatever calls this (a test fixture, or a caller with real PLR
    source access via `plr_sema.derive.receiver_state
    .build_plr_class_index`), never inside this module.
    """
    out: dict[str, frozenset[str]] = {}

    def closure(name: str, seen: "frozenset[str]") -> "frozenset[str]":
        if name in seen:
            return frozenset()
        seen = seen | {name}
        result = {name}
        for base in bases.get(name, ()):
            result |= closure(base, seen)
        return frozenset(result)

    for name in bases:
        out[name] = closure(name, frozenset())
    return out


def _ancestors(name: str, class_hierarchy: "Mapping[str, frozenset[str]] | None") -> "frozenset[str]":
    if class_hierarchy is None:
        return frozenset({name})
    return class_hierarchy.get(name, frozenset({name}))


def _eval_is_instance(node: "pa.IsInstance", ctx: _Ctx) -> "bool | None":
    """E-TYPE, restated (round 1, C4). `T` iff the declared name is-or-is-
    a-subclass-of some `Ti`. `F` requires the declared name to be *known
    exact* -- a fact `ir.Resource` carries no field for at this pin (only
    the graph lane's own payload could mark one, §15.4's O1 box), so `F` is
    structurally unreachable through this module and every non-`T` case is
    ½ rather than a fabricated `F`."""
    value = _resolve_term(node.term, ctx)
    if not isinstance(value, ir.Ref):
        return None
    resource = ctx.resources_by_slot.get(value.slot)
    if resource is None:
        return None
    declared = resource.element_type if value.cell is not None else resource.type
    if declared is None:
        return None
    ancestors = _ancestors(declared, ctx.class_hierarchy)
    if any(t == declared or t in ancestors for t in node.types):
        return True
    return None


def _is_type_ambiguous(node: "pa.IsInstance", ctx: _Ctx) -> bool:
    """§15.7's `guard_operand_unknown` clause: "a RESOURCE whose declared
    type/element_type cannot decide an IsInstance" -- true iff the term
    resolves to a real `Ref` into a known `Resource` slot but the declared
    name is `None` (O1 did not populate it, or the parent's element
    classes were heterogeneous, §15.4's fail-closed singleton rule)."""
    value = _resolve_term(node.term, ctx)
    if not isinstance(value, ir.Ref):
        return False
    resource = ctx.resources_by_slot.get(value.slot)
    if resource is None:
        return False
    declared = resource.element_type if value.cell is not None else resource.type
    return declared is None


# ---------------------------------------------------------------------------
# G3 -- the alpha-idiom emptiness test, evaluated (not merely parsed): a
# `Cmp(Len(Var(x)), op, Lit(n))` where `x` is ALPHA-bound is the existential
# "does some element of the iterand fail/satisfy the filter", decided by
# looping over the iterand's REAL resolved items (each a genuine, possibly
# cell-carrying `ir.Ref`) -- NOT the A-C13 always-⊤ rule, which is about a
# GENUINE `all(...)`/`any(...)` grammar production's own bound name, a
# different thing recorded nowhere as such but distinguished here by WHICH
# evaluation path constructs the quantification (this one, vs. `_eval_allof_anyof`
# below for a literal `AllOf`/`AnyOf` node in the guard's own `predicate`).
# ---------------------------------------------------------------------------

_ANY_OF_COMBOS = frozenset({(">", 0), (">=", 1)})
_NOT_ANY_OF_COMBOS = frozenset({("==", 0), ("!=", 0)})
_FLIP_OP = {"==": "==", "!=": "!=", "<": ">", "<=": ">=", ">": "<", ">=": "<="}


def _is_int_lit(term: "pa.Term") -> "int | None":
    if isinstance(term, pa.Lit) and isinstance(term.value, int) and not isinstance(term.value, bool):
        return term.value
    return None


def _alpha_binding_for(term: "pa.Term", ctx: _Ctx) -> "Mapping[str, Any] | None":
    if not isinstance(term, pa.Var):
        return None
    binding = ctx.bindings_by_name.get(term.name)
    if binding is not None and binding.get("idiom") == "alpha":
        return binding
    return None


def _eval_alpha_existential(binding: Mapping[str, Any], ctx: _Ctx) -> "bool | None":
    """The existential this binding's `pred` represents, over the REAL
    resolved elements of `binding["iter"]`. Returns `False` on a resolved
    (concrete), genuinely empty iterand (the vacuous existential is
    False); `None` (½) when the iterand itself does not resolve to a
    concrete `Seq`; otherwise Kleene-combines one evaluation of `pred` per
    real item (T if any item's evaluation is T, F if every item's is F,
    else ½)."""
    iterand = _resolve_term(pa.Var(binding["iter"]), ctx)
    if not isinstance(iterand, ir.Seq):
        return None
    if len(iterand.items) == 0:
        return False
    pred = pa.from_json(binding["pred"])
    bound_names = sorted(bindings_mod.free_var_names(pred))
    results: list["bool | None"] = []
    for item in iterand.items:
        override = {name: item for name in bound_names}
        results.append(evaluate_predicate(pred, _with_override(ctx, override)))
    if any(r is True for r in results):
        return True
    if all(r is False for r in results):
        return False
    return None


def _maybe_alpha_emptiness(node: "pa.Cmp", ctx: _Ctx) -> "tuple[bool | None, bool] | None":
    """Returns `(value, handled)` sentinel via `None` when this Cmp is not
    the alpha-idiom shape at all (fall through to ordinary Cmp handling);
    otherwise returns `(value, True)`. The idiom is `Len(Var(x)) op n`, so
    the alpha binding lives on `Len`'s own inner `Var`, not on `node.left`/
    `node.right` directly."""
    left_var = node.left.term if isinstance(node.left, pa.Len) else None
    right_var = node.right.term if isinstance(node.right, pa.Len) else None
    left_binding = _alpha_binding_for(left_var, ctx) if left_var is not None else None
    right_binding = _alpha_binding_for(right_var, ctx) if right_var is not None else None
    if left_binding is not None and _is_int_lit(node.right) is not None:
        binding, n, op = left_binding, _is_int_lit(node.right), node.op
    elif right_binding is not None and _is_int_lit(node.left) is not None:
        binding, n, op = right_binding, _is_int_lit(node.left), _FLIP_OP.get(node.op, node.op)
    else:
        return None
    combo = (op, n)
    if combo in _ANY_OF_COMBOS:
        return _eval_alpha_existential(binding, ctx), True
    if combo in _NOT_ANY_OF_COMBOS:
        return _kleene_not(_eval_alpha_existential(binding, ctx)), True
    return None  # an unrecognised numeric relation over an alpha-bound name -- not this idiom's business either; falls through (stays ½ via G5).


# ---------------------------------------------------------------------------
# G4 -- set(x) uniqueness: Cmp(Len(SetOf(a)), "==", Len(b)) with a == b
# structurally.
# ---------------------------------------------------------------------------


def _maybe_setof_uniqueness(node: "pa.Cmp", ctx: _Ctx) -> "tuple[bool | None, bool] | None":
    """`Cmp(Len(SetOf(a)), "==", Len(b))` with `a == b` structurally --
    BOTH sides are `Len`-wrapped (`len(set(x)) == len(x)`), one of them
    additionally `SetOf`-wrapped."""
    if node.op != "==":
        return None
    left, right = node.left, node.right
    if not (isinstance(left, pa.Len) and isinstance(right, pa.Len)):
        return None
    if isinstance(left.term, pa.SetOf) and left.term.term == right.term:
        inner = left.term.term
    elif isinstance(right.term, pa.SetOf) and right.term.term == left.term:
        inner = right.term.term
    else:
        return None
    value = _resolve_term(inner, ctx)
    if not isinstance(value, ir.Seq):
        return None, True
    items: list[Any] = []
    for item in value.items:
        if not isinstance(item, ir.Lit):
            return None, True  # not a Seq of hashable Lits -- ½.
        try:
            items.append(item.v)
            hash(item.v)
        except TypeError:
            return None, True
    return (len(set(items)) == len(items)), True


# ---------------------------------------------------------------------------
# Cmp -- the full dispatch, in order: G3, G4, membership (always ½), the
# Len-vs-Len integer comparison (excluded from G5's fold), then G5's
# unconditional ½ for everything else.
# ---------------------------------------------------------------------------

_NUMERIC_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


def _eval_cmp(node: "pa.Cmp", ctx: _Ctx) -> "bool | None":
    special = _maybe_alpha_emptiness(node, ctx)
    if special is not None:
        return special[0]
    special = _maybe_setof_uniqueness(node, ctx)
    if special is not None:
        return special[0]
    if node.op in pa.MEMBERSHIP_OPS:
        return None  # G8(2): every membership Cmp is ½, unconditionally.
    # G5's own carve-out: "operands are numeric and are NOT Len/SetOf
    # terms folds to ½" -- read the other way, an operand that IS a `Len`
    # escapes the fold. At least one side being `Len` is enough; the other
    # side may be another `Len` (`:522`'s `len(a) == len(b)`) or a bare
    # int literal -- both are "count-shaped" and decidable when they
    # resolve. Two bare literals (neither side `Len`) still fall through
    # to G5's unconditional ½ below -- deliberately: this module does no
    # general numeric reasoning, only length-based reasoning.
    if isinstance(node.left, pa.Len) or isinstance(node.right, pa.Len):
        ln = _resolve_len(node.left.term, ctx) if isinstance(node.left, pa.Len) else _is_int_lit(node.left)
        rn = _resolve_len(node.right.term, ctx) if isinstance(node.right, pa.Len) else _is_int_lit(node.right)
        if ln is None or rn is None:
            return None
        return _NUMERIC_OPS[node.op](ln, rn)
    return None  # G5: numeric atoms that are not a Len-vs-Len pair stay ½.


# ---------------------------------------------------------------------------
# Is (x is None / x is not None).
# ---------------------------------------------------------------------------


def _eval_is(node: "pa.Is", ctx: _Ctx) -> "bool | None":
    value = _resolve_term(node.term, ctx)
    if isinstance(value, ir.Lit):
        is_none = value.v is None
        return (not is_none) if node.negated else is_none
    return None


# ---------------------------------------------------------------------------
# Quantifiers -- AllOf/AnyOf. `Zip` resolution (⊤ unless every item is a
# concrete Seq; length = min over items when it is); the comprehension-
# bound-name-is-always-⊤ rule (A-C13); the vacuous-quantification-over-⊤-
# is-½-never-vacuously-T rule (A-C3).
# ---------------------------------------------------------------------------


def _resolve_seq_length(term: "pa.Term", ctx: _Ctx) -> "int | None":
    if isinstance(term, pa.Zip):
        lengths: list[int] = []
        for item in term.items:
            value = _resolve_term(item, ctx)
            if not isinstance(value, ir.Seq):
                return None  # ⊤ unless EVERY item is a concrete Seq.
            lengths.append(len(value.items))
        return min(lengths) if lengths else None
    value = _resolve_term(term, ctx)
    if isinstance(value, ir.Seq):
        return len(value.items)
    return None


def _eval_allof_anyof(node: "pa.AllOf | pa.AnyOf", ctx: _Ctx, *, kind: str) -> "bool | None":
    n = _resolve_seq_length(node.seq, ctx)
    if n is None:
        return None  # ⊤ seq -> ½, never vacuously T (A-C3).
    if n == 0:
        return kind == "all"  # a genuinely resolved, empty concrete seq: ordinary vacuous truth.
    # A-C13: every comprehension-bound name is ⊤, unconditionally, and
    # NEVER resolved against call.kwargs -- so every one of the n real
    # elements evaluates `predicate` identically; one evaluation suffices.
    return evaluate_predicate(node.predicate, _with_all_to_top(ctx))


# ---------------------------------------------------------------------------
# The general Predicate/Term evaluators.
# ---------------------------------------------------------------------------


def evaluate_term(term: "pa.Term", ctx: Any) -> ir.Value:
    """Public entry point mirroring `evaluate_predicate` -- resolves a
    `Term` to its `ir.Value` (Lit/Ref/Seq/Top) against `ctx` (an opaque
    object built by :func:`evaluate_guard`'s caller-facing helpers; tests
    build one via `_Ctx` directly, see `tests/test_predicate.py`)."""
    return _resolve_term(term, ctx)


def evaluate_predicate(node: "pa.Predicate", ctx: Any) -> "bool | None":
    """The Kleene evaluator over G1-G8. `ctx` is a `_Ctx` (private, but
    tests construct one directly -- see this module's own test suite for
    the supported construction shape)."""
    if isinstance(node, pa.TRUE):
        return True
    if isinstance(node, pa.Opaque):
        return None
    if isinstance(node, pa.Not):
        return _kleene_not(evaluate_predicate(node.predicate, ctx))
    if isinstance(node, pa.And):
        values = [evaluate_predicate(p, ctx) for p in node.predicates]
        if any(v is False for v in values):
            return False
        if all(v is True for v in values):
            return True
        return None
    if isinstance(node, pa.Or):
        values = [evaluate_predicate(p, ctx) for p in node.predicates]
        if any(v is True for v in values):
            return True
        if all(v is False for v in values):
            return False
        return None
    if isinstance(node, pa.Cmp):
        return _eval_cmp(node, ctx)
    if isinstance(node, pa.Is):
        return _eval_is(node, ctx)
    if isinstance(node, pa.IsInstance):
        return _eval_is_instance(node, ctx)
    if isinstance(node, pa.AllOf):
        return _eval_allof_anyof(node, ctx, kind="all")
    if isinstance(node, pa.AnyOf):
        return _eval_allof_anyof(node, ctx, kind="any")
    if isinstance(node, pa.EnvRef):
        return None  # E-ENV: ½ in predicate position, unconditionally.
    raise TypeError(f"evaluate_predicate: unrecognized node {type(node)!r}")


# ---------------------------------------------------------------------------
# §15.7 -- reason assignment, over the alpha/beta-SUBSTITUTED tree.
# ---------------------------------------------------------------------------


def _operand_unknown(node: "pa.Predicate | pa.Term", ctx: _Ctx) -> bool:
    """Clause 2 of §15.7's ordered procedure: true iff some operand of
    THIS call resolves to ⊤. `Filtered`/`AllOf`/`AnyOf`'s own `predicate`
    field is deliberately NOT descended into -- its free names are
    comprehension-bound (A-C13 / the alpha idiom's own synthetic loop
    variable), never a real operand of this call, whichever evaluation
    path (the alpha existential above, or a genuine A-C13 always-⊤
    quantifier) ultimately handles it."""
    if isinstance(node, pa.Var):
        value, origin = _resolve_var(node.name, ctx)
        return origin == "operand" and isinstance(value, ir.Top)
    if isinstance(node, (pa.TRUE, pa.Opaque, pa.Lit)):
        return False
    if isinstance(node, pa.Not):
        return _operand_unknown(node.predicate, ctx)
    if isinstance(node, (pa.And, pa.Or)):
        return any(_operand_unknown(p, ctx) for p in node.predicates)
    if isinstance(node, pa.Cmp):
        return _operand_unknown(node.left, ctx) or _operand_unknown(node.right, ctx)
    if isinstance(node, pa.Is):
        return _operand_unknown(node.term, ctx)
    if isinstance(node, pa.IsInstance):
        return _operand_unknown(node.term, ctx) or _is_type_ambiguous(node, ctx)
    if isinstance(node, (pa.AllOf, pa.AnyOf)):
        return _operand_unknown(node.seq, ctx)  # NOT node.predicate -- see docstring.
    if isinstance(node, (pa.Len, pa.SetOf, pa.Attr)):
        return _operand_unknown(node.term, ctx)
    if isinstance(node, pa.Filtered):
        return _operand_unknown(node.seq, ctx)  # NOT node.predicate -- see docstring.
    if isinstance(node, pa.Zip):
        return any(_operand_unknown(i, ctx) for i in node.items)
    if isinstance(node, pa.EnvRef):
        if node.args is None:
            return False
        return any(_operand_unknown(a, ctx) for a in node.args)
    raise TypeError(f"_operand_unknown: unrecognized node {type(node)!r}")


def guard_reason(predicate: "pa.Predicate", ctx: _Ctx) -> str:
    """§15.7's ordered, four-clause reason-assignment procedure, over the
    alpha/beta-SUBSTITUTED tree (round 2, A-C4) -- called only when the
    guard's overall Kleene value is ½ (this function is meaningless, and
    never called, when the value decided)."""
    substituted = bindings_mod.substitute(predicate, ctx.bindings_by_name)
    if pa.contains_opaque(substituted):
        return "guard_predicate_unparsed"
    if _operand_unknown(substituted, ctx):
        return "guard_operand_unknown"
    return "guard_env_dependent"  # contains_env_ref, or the clause-4 catch-all -- same reason either way.


# ---------------------------------------------------------------------------
# E-SCOPE / E-UNCOND.
# ---------------------------------------------------------------------------

_HYPOTHESIS_ENTRY_RE = re.compile(r"^if (\w+)\(\)$")


def _scope_entry_value(entry: str, ctx: _Ctx) -> "bool | None":
    """One `scope_trail` entry's own Kleene value, for E-SCOPE. An `"else
    of: if "` entry is the negation of its test; an ordinary `"if "` entry
    is its test as-is; a `"for "`/`"while "` header (or anything else
    unrecognised) contributes ½ and never `F` (`ast.parse(..., mode="eval")`
    on a bare `for`/`while` header text is a `SyntaxError` -> `Opaque` ->
    ½ anyway, so no special-case is even needed for those two shapes -- the
    total `parse` already gets this right)."""
    if entry.startswith("else of: if "):
        test_text = entry[len("else of: if ") :]
        return _kleene_not(evaluate_predicate(pa.parse(test_text), ctx))
    if entry.startswith("if "):
        test_text = entry[3:]
        return evaluate_predicate(pa.parse(test_text), ctx)
    return evaluate_predicate(pa.parse(entry), ctx)  # for/while/anything else -> Opaque -> ½.


def _exclude_self_entry(guard: Mapping[str, Any]) -> "list[str]":
    """E-UNCOND(6): a `raise_guard` whose `scope_trail[0]` IS its own
    condition (`visit_Raise` reads it in without popping it) is excluded
    from both E-SCOPE and E-UNCOND, which range over `scope_trail[1:]`."""
    trail = list(guard.get("scope_trail", ()))
    condition = guard.get("condition")
    kind = guard.get("kind", "raise_guard")
    if kind == "raise_guard" and condition is not None and trail and trail[0] == f"if {condition}":
        return trail[1:]
    return trail


def scope_excludes(scope_entries: "list[str]", ctx: _Ctx) -> bool:
    """E-SCOPE: true iff SOME entry evaluates `F` -- the guard is then
    unreachable and its own predicate is irrelevant; the emitted Finding is
    `SAFE` regardless."""
    return any(_scope_entry_value(entry, ctx) is False for entry in scope_entries)


def _entry_satisfies_uncond(entry: str, ctx: _Ctx) -> bool:
    val = _scope_entry_value(entry, ctx)
    if val is True:
        return True  # way (1): evaluation.
    if entry.startswith("if "):
        m = _HYPOTHESIS_ENTRY_RE.match(entry)
        if m is not None and m.group(1) in ctx.env:
            return True  # way (2): hypothesis.
    # way (3): structural R1 -- no for_span data reaches this guard family
    # at this pin (module docstring, point 4); never satisfied here.
    return False


def guard_is_unconditional(
    scope_entries: "list[str]",
    ctx: _Ctx,
    *,
    depth: int,
    k_reachability_clear: "bool | None",
) -> bool:
    """E-UNCOND: may this guard emit `WILL_FAIL`? Clauses (4) and (5) are
    checked first (either can block regardless of the trail's own
    content); otherwise every entry must be satisfied by one of ways
    (1)-(3)."""
    if depth >= 1:
        return False  # clause (4).
    if not scope_entries:
        return bool(k_reachability_clear)  # clause (5), fail-closed on None/False.
    return all(_entry_satisfies_uncond(entry, ctx) for entry in scope_entries)


# ---------------------------------------------------------------------------
# Tier (iii) -- derived, at zero registry cost.
# ---------------------------------------------------------------------------


def is_dynamic_raise(guard: Mapping[str, Any]) -> bool:
    """§15.1's normative box: tier (iii) iff `raises` starts with
    `"<dynamic:"` -- never a site list, never a `condition` text match."""
    raises = guard.get("raises")
    return raises is not None and str(raises).startswith("<dynamic:")


# ---------------------------------------------------------------------------
# The top-level per-guard decision.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GuardResult:
    """`verdict` in `{"safe", "will_fail", "unknown"}`; `reason` is `""`
    for `"safe"`/`"will_fail"` and a `REASON_VOCABULARY` member for
    `"unknown"`; `tier_iii` tells the caller to fold this guard's `site`
    into `AnalysisReport.scope.excludes_sites` (§15.5)."""

    verdict: str
    reason: str = ""
    tier_iii: bool = False


_SAFE = GuardResult(verdict="safe")
_WILL_FAIL = GuardResult(verdict="will_fail")


def evaluate_guard(
    guard: Mapping[str, Any],
    call: ir.Call,
    contract: Mapping[str, Any],
    resources_by_slot: Mapping[int, ir.Resource],
    *,
    env: "frozenset[str]" = frozenset(),
    channel_kwarg: "str | None" = None,
    channels: "tuple[int, ...] | None" = None,
    class_hierarchy: "Mapping[str, frozenset[str]] | None" = None,
    k_reachability_clear: "bool | None" = None,
) -> GuardResult:
    """The full per-guard decision: tier (iii) short-circuit, E-SCOPE,
    E-CALL/E-TYPE/E-ENV (via :func:`evaluate_predicate`), G6's polarity,
    E-UNCOND, E-VERDICT, and (for a ½ outcome) §15.7's reason.

    `guard` is one entry of `contract["guards"]` (the wire shape
    `derive/__main__.py::_guard_to_json` emits). `channel_kwarg`/`channels`
    are the receiver's derived `channel_kwarg` and the ALREADY-COMPUTED
    `tipstate.channels_for_call` result for this call -- computed once by
    the caller (who already has `receiver_state` in hand) and threaded
    through rather than re-derived here, per §15.3's own P3a hook
    ("consults `channels_for_call`... never re-derives it").
    """
    if is_dynamic_raise(guard):
        return GuardResult(verdict="unknown", reason="guard_env_dependent", tier_iii=True)

    if "predicate" not in guard:
        # T30a's own additive-field contract: a pre-T30a contract table (or
        # a hand-built test fixture that never carried the key) has NO
        # `predicate` at all. Degrading to the pre-increment-6 blanket
        # behaviour -- unconditionally `guard_predicate_unparsed` -- is the
        # ONLY sound choice: this module has nothing to evaluate.
        return GuardResult(verdict="unknown", reason="guard_predicate_unparsed")

    depth = int(guard.get("depth", 0))
    predicate = pa.from_json(guard["predicate"])
    bindings_by_name = {b["x"]: b for b in guard.get("bindings", ())}
    ctx = _Ctx(
        call=call,
        resources_by_slot=resources_by_slot,
        param_defaults=contract.get("param_defaults", {}) if depth == 0 else {},
        bindings_by_name=bindings_by_name,
        depth=depth,
        channel_kwarg=channel_kwarg,
        channels=channels,
        env=env,
        class_hierarchy=class_hierarchy,
    )

    scope_entries = _exclude_self_entry(guard)
    if scope_excludes(scope_entries, ctx):
        return _SAFE

    value = evaluate_predicate(predicate, ctx)
    kind = guard.get("kind", "raise_guard")
    fires = value if kind == "raise_guard" else _kleene_not(value)

    if fires is False:
        return _SAFE
    if fires is True:
        if guard_is_unconditional(scope_entries, ctx, depth=depth, k_reachability_clear=k_reachability_clear):
            return _WILL_FAIL
        return GuardResult(verdict="unknown", reason="guard_env_dependent")
    return GuardResult(verdict="unknown", reason=guard_reason(predicate, ctx))
