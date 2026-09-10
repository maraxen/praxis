"""plr_sema.check.predicate: the Kleene three-valued guard evaluator
(increment 6, spec 260904 §15.4/§15.5/§15.7, T31-1).

**Scope.** This module turns a `predicate_ast.Predicate` (already parsed at
derive time, §15.2/§15.3's grammar and local-binding idioms) into a
verdict against ONE concrete `ir.Call`: E-CALL (operand resolution),
E-TYPE (`IsInstance` against a `RESOURCE`'s declared type), E-SCOPE (an
unsatisfied enclosing scope makes `SAFE` true regardless of the guard's own
predicate), E-VERDICT (predicate truth -> `Finding`), E-UNCOND (the six
clauses gating `WILL_FAIL`), E-ENV, and §15.7's reason-assignment procedure.
Wiring the result into a `Finding` and into `check_ir`'s walk is T31-2
(`plr_sema.check.__init__`), not this module's job.

**260909 (spec 260909_plr-sema-observation-increment.md §16.5, T43,
backlog #5024): `E-ENV` resolution.** Increment 6 made every `EnvRef` ½ in
predicate position and ⊤ in term position, unconditionally, with no lookup
table. This increment SUPERSEDES that exactly and only for the three
admitted path shapes `_resolve_env_ref` below implements -- R-HEAD
(`self.head`), R-ATTR (`self.backend.<attr>`) and R-CONST
(`self.backend.<method>(...)`, independent of `args` by construction) --
against the observation record's `obs:<key>=<value>` members of `env`
(§16.2.3) and, for R-CONST, the derived backend surface's `constant_return`
column (§16.3, threaded in as `ctx.backend_surface`, keyed
`f"{backend_class}.{method}"`). **Every path not matching one of the three
stays ½/⊤, which is `E-ENV` unchanged.** The membership case is reopened
ONLY for a `Cmp` whose right operand is SYNTACTICALLY an R-HEAD-shaped
`EnvRef` (§16.5.4) -- a general `ir.Seq` (from `call.kwargs`, a
`param_defaults` entry, or an alpha/beta binding) stays a LOWER BOUND and
never decides a `not in` to `T`; `ir.Seq` itself gains no field. Q-MONO
(§16.5.5) is the one quantifier clause: `AllOf`/`AnyOf` over a ⊤ seq takes
a decided value only when the body is definite in the direction the empty
sequence also satisfies (`AllOf` + `T` body -> `T`; `AnyOf` + `F` body ->
`F`); the other two cells stay ½ BY RULE, which AMENDS increment 6's flat
"never vacuously T" sentence (G8(1)/A-C3 --
`.praxia/docs/specs/260904_plr-sema-predicate-increment.md`, amended in the
same commit as this module). Q-BIND is NOT implemented: `:409` already
binds element-wise through `_eval_alpha_existential` below, and no `target`
field is added to `Filtered`/`AllOf`/`AnyOf`.

**260909 (spec 260909_plr-sema-observation-increment.md §16.1.3/§16.15 D6,
T48, backlog #5026): the `:321` site rule.** A site-keyed semantic model of
`LiquidHandler._assert_resources_exist`'s own body -- `D6_SITE_RULES` maps
`(qualname, lineno)` to a total `_Ctx -> bool | None` function that REPLACES
`evaluate_predicate` outright for the matched guard, dispatched in
`evaluate_guard` before the ordinary predicate path. This is a DIFFERENT
shape from R-HEAD/R-ATTR/R-CONST above: `:321`'s own guard predicate
(`Not(Cmp(Var("resource_from_deck"), "==", Var("resource")))`) has no
`EnvRef` at all (§16.1.3's Q2 -- R-DECK, the shape spec_version 1 proposed,
does not occur in the contract table) and neither free name binds through
any idiom this module implements, so there is nothing for a sub-expression
resolution rule to hook. The site rule reads `resources` (K's own
parameter, generically resolved through `_resolve_var`/M2's `caller_args`)
and `obs:deck_resources_verified` (`plr-sema/eval/oracle_common.py`'s
`observation_env_members`) and NEVER returns `T` (§16.1.3 Fact 1: an absent
name raises at `:318`, not here).

**260909 (spec 260909_plr-sema-observation-increment.md §16.1.1/§16.15 D6,
T49, backlog #5026): the `:375`/`:383` site rules (D5b).** Two more
`D6_SITE_RULES` entries, the SAME dict and the SAME dispatch shape as
`:321` above -- each REPLACES `evaluate_predicate` outright for its own
matched guard. `:375`'s own guard predicate is `Cmp(Len(Var("missing")),
">", Lit(0))`; the rule decides it `F` (never `T`) when the observed
`backend_class`'s `(class, method)` row in §16.3's surface has a `params`
list that is a SUBSET of the caller-side `default` set -- both read off
`ctx.caller_args` (`"method"`, an `EnvRef` whose LAST path segment is the
runtime method name `m`, and `"default"`, a G9 `SetLit` now that one is a
parseable `Term`) rather than through `_resolve_var`'s ordinary E-CALL
steps, because `missing`/`vars_keyword` are LOCALS of `_check_args`, not
its parameters, and are therefore never bound by M1/M2 at all. `:383`'s own
guard predicate (`strictness == Strictness.STRICT`) is never evaluated:
its own scope trail's second entry (`"if len(extra) > 0 and
len(vars_keyword) == 0"`) is unsatisfiable whenever `has_var_keyword` is
`True` (the recorded `vars_keyword` set is then non-empty by construction,
so `len(vars_keyword) == 0` is `F`, the `And` is `F` regardless of
`len(extra)`), which makes the whole nested raise unreachable REGARDLESS OF
`strictness` -- so the site rule returns `F` directly for the SAME reason
E-SCOPE would, without ever resolving `strictness` (§16.1.1's own box:
"`strictness` decides nothing... whatever `env` carries"). Both rules
decline (`None`) when §16.3's absence rule removed the `(backend_class, m)`
row (C15's soundness precondition, shared with `:321`) -- an
AST-derived `params`/`has_var_keyword` for a decorated or multiply-defined
method does not describe the runtime object `inspect.signature` sees.

**260909 (spec 260909_plr-sema-move-family-increment.md §17.1.2/§17.3, T51,
D7 unit 11): R-ARM and the amended predicate-position clause.** A FOURTH
admitted `_resolve_env_ref` path shape, `self._resource_pickups`, resolving
to the observation's `arm_slots` under a new `rule` value `"R-ARM"` -- an
`EnvRef` path admitted against the observation record, the identical
pattern R-HEAD/R-ATTR/R-CONST already are, so it rides D4's registry unit
for free. What does NOT ride free, and is booked as its own unit, is the
predicate-position clause this increment amends: increment 7's `E-ENV`
refused `("self","head")` by shape and otherwise decided only for a
resolved `ir.Lit`, on the stated ground that a dict is not a truth value.
`:2055` falsifies that ground directly. The amended rule: an `EnvRef`
resolving to a non-`Top` `ir.Seq` under a `rule` whose own §16.5/§17.3
specification declares that `Seq` COMPLETE -- today R-HEAD and R-ARM --
decides `T` iff non-empty and `F` iff empty; every other value, `Top`, or
rule is ½ exactly as before. Keyed on the RULE, not on
`isinstance(value, ir.Seq)`, which is what keeps a future lower-bound-Seq
rule from silently deciding here. The `("self","head")` shape refusal is
KEPT, unchanged: no guard at this pin reads `self.head` as a truth value.

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

import json
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
    "D6_SITE_RULES",
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
    # 260909 (spec §16.4, T42): M2's `caller_args` resolution. `caller_args`
    # is the guard's own `{D's param name: <Term JSON>}` map (`None` unless
    # `depth == 1` and M1 admitted the pair -- `_resolve_var` re-checks
    # `ctx.depth == 1` itself rather than trusting an un-regenerated or
    # hand-built fixture's `depth` field to agree with a nonzero
    # `caller_args`, defense in depth for M1 clause 6). `entry_param_defaults`
    # is the SAME `contract["param_defaults"]` value `param_defaults` above
    # already carries at `depth == 0` -- unconditionally available here
    # (never depth-gated), because M2 step (1) evaluates a caller-side Term
    # "in K's own context", which needs K's OWN param_defaults regardless of
    # the CURRENT guard's depth.
    caller_args: "Mapping[str, Any] | None" = None
    entry_param_defaults: Mapping[str, Any] = field(default_factory=dict)
    # 260909 (spec §16.3/§16.5, T41/T43): R-CONST's own lookup table --
    # `{f"{backend_class}.{method}": {"constant_return": ..., ...}}`, the
    # additive `contract["backend_surface"]["rows"]` sub-object
    # `derive/__main__.py` attaches ONLY to a contract entry whose own
    # guards carry a `self.backend.<method>(...)` EnvRef (§16.3's derived
    # surface, keyed exactly as `build_backend_surface` keys it). `{}` on
    # every other contract entry and on any un-regenerated table --
    # R-CONST simply never finds a row and declines to ⊤, the same
    # fail-closed default every other additive field in this module uses.
    backend_surface: Mapping[str, Any] = field(default_factory=dict)


def _with_override(ctx: _Ctx, override: Mapping[str, ir.Value]) -> _Ctx:
    merged = dict(ctx.var_override)
    merged.update(override)
    return replace(ctx, var_override=merged, override_all_to_top=False)


def _with_all_to_top(ctx: _Ctx) -> _Ctx:
    return replace(ctx, var_override={}, override_all_to_top=True)


# ---------------------------------------------------------------------------
# E-ENV (260909, spec §16.5, T43): the observation record's own `obs:`
# members of `env`, and the ONE path-shape table dispatching R-HEAD/
# R-ATTR/R-CONST over them -- `_resolve_env_ref` is the symbol
# `_hand_maintained._measure_hm25` imports for HM-25's tenth unit (D4):
# ONE further ceiling unit for the PATTERN ("an EnvRef path admitted
# against the observation record"), not one per instance (§16.9's own
# argument -- R-DECK's withdrawal does not reduce the ask and neither would
# dropping R-ATTR).
# ---------------------------------------------------------------------------

_OBS_PREFIX = "obs:"


def _observation(env: "frozenset[str]") -> "dict[str, Any]":
    """§16.2.3's `obs:<key>=<value>` members of `env`, JSON-decoded into a
    plain dict. `{}` whenever no observation reached this guard at all --
    every §16.5 rule declines on that, which is `E-ENV`'s fail-closed
    default unchanged (§16.2.3's own normative box, restated for T43: with
    no `obs:` member in `env`, every rule below declines). A member whose
    value fails to parse as JSON is skipped rather than raised on -- this
    module never raises on a malformed `env` string, matching every other
    total function here."""
    obs: dict[str, Any] = {}
    for member in env:
        if not member.startswith(_OBS_PREFIX):
            continue
        key, sep, raw = member[len(_OBS_PREFIX) :].partition("=")
        if not sep:
            continue
        try:
            obs[key] = json.loads(raw)
        except ValueError:
            continue
    return obs


def _resolve_env_ref(node: "pa.EnvRef", ctx: _Ctx) -> "tuple[ir.Value, str | None]":
    """Returns `(value, rule)`. `rule` is `"R-HEAD"` / `"R-ATTR"` /
    `"R-CONST"` when the node's `path`/`args` SHAPE matched one of §16.5's
    three admitted shapes -- whether or not the observation went on to let
    it RESOLVE (`value` is `ir.Top()` on a declined resolution: an absent
    or partial observation, or, for R-CONST, a `(backend_class, method)`
    §16.3's absence rule removed or that never had a `constant_return`).
    `rule` is `None` when no shape matched at all -- `E-ENV` unchanged, the
    caller's own ⊤/½ fallback. A caller publishing `n_resolved_by_rule`/
    `n_declined_by_rule` (§16.10.1 block 1) keys off `rule` plus
    `isinstance(value, ir.Top)`.

    **R-HEAD** (§16.5.1): `EnvRef(("self", "head"), None)` -> the COMPLETE
    `Seq` of the observation's `head_channels`, ascending, iff BOTH
    `head_channels` and `backend_class` are present (a partial observation
    is refused wholesale, same rule §16.2.1's ONE-capture-point box states).
    **R-ATTR** (§16.5.2): `EnvRef(("self", "backend", a), None)` -> `Lit(v)`
    iff `a` is a field of §16.2's record -- at this pin exactly
    `num_channels` -- and the observation carries it; every other `a`
    declines. **R-CONST** (§16.5.3): `EnvRef(("self", "backend", m), args)`
    with `args is not None` -> `Lit(v)` iff `ctx.backend_surface` has a row
    keyed `f"{backend_class}.{m}"` carrying a `constant_return` -- read
    independently of `args`, which is not even inspected here (the whole of
    the argument-independence soundness argument, §16.5.3's own box). The
    MRO is not walked: the lookup is the exact key or nothing.

    **R-ARM** (§17.3, move-family increment, T51): `EnvRef(("self",
    "_resource_pickups"), None)` -> the COMPLETE `Seq` of the observation's
    `arm_slots`, ascending, iff `arm_slots` is present. Declared complete
    subject to §17.3's stability precondition -- the key set of
    `self._resource_pickups` is fixed for the rest of the program after
    the capture point, for every receiver with `num_arms >= 1` -- not by
    the shape alone. No membership case: in term position it behaves
    exactly as R-HEAD's own `Seq` does, and no guard at this pin reads
    membership in it.
    """
    obs = _observation(ctx.env)
    if node.path == ("self", "head") and node.args is None:
        if "head_channels" not in obs or "backend_class" not in obs:
            return ir.Top(), "R-HEAD"
        channels = obs["head_channels"]
        if not isinstance(channels, list) or not all(isinstance(c, int) for c in channels):
            return ir.Top(), "R-HEAD"
        return ir.Seq(tuple(ir.Lit(c) for c in sorted(channels))), "R-HEAD"
    if len(node.path) == 3 and node.path[0] == "self" and node.path[1] == "backend":
        member = node.path[2]
        if node.args is None:
            if member != "num_channels" or "num_channels" not in obs:
                return ir.Top(), "R-ATTR"
            return ir.Lit(obs["num_channels"]), "R-ATTR"
        backend_class = obs.get("backend_class")
        if backend_class is None:
            return ir.Top(), "R-CONST"
        row = ctx.backend_surface.get(f"{backend_class}.{member}")
        if row is None or "constant_return" not in row:
            return ir.Top(), "R-CONST"
        return ir.Lit(row["constant_return"]), "R-CONST"
    if node.path == ("self", "_resource_pickups") and node.args is None:
        slots = obs.get("arm_slots")
        if not isinstance(slots, list) or not all(isinstance(s, int) for s in slots):
            return ir.Top(), "R-ARM"
        return ir.Seq(tuple(ir.Lit(s) for s in sorted(slots))), "R-ARM"
    return ir.Top(), None


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
    if ctx.depth == 1 and ctx.caller_args is not None and name in ctx.caller_args:
        # M2 step (1), §16.4: a depth-1 free name that is a parameter of D
        # with a `caller_args` entry resolves by evaluating the CALLER-side
        # `Term` in K's own context -- E-CALL(5)'s parameter-rebinding
        # clause applies in K, never in D. The substitution is a ONE-SHOT
        # replay of the depth-0 resolution rules (`call.kwargs`/K's own
        # `param_defaults`/the P3a `channel_kwarg` hook, the last of which
        # is already depth-independent above) against the recorded Term,
        # never a second name-keyed lookup into D's own `bindings_by_name`
        # (`bindings_by_name={}` below) -- exactly the name-coincidence
        # hazard §16.4 closes: nothing here is re-matched by name against a
        # namespace it does not belong to. `caller_args=None` on the nested
        # ctx is defensive (K-context resolution never re-enters M2 itself).
        term = pa.from_json(ctx.caller_args[name])
        caller_ctx = replace(
            ctx,
            depth=0,
            param_defaults=ctx.entry_param_defaults,
            bindings_by_name={},
            caller_args=None,
        )
        return _resolve_term(term, caller_ctx), "operand"  # C9: always "operand" origin.
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
    if isinstance(term, pa.SetLit):
        # G9 (T49): a set DISPLAY is a concrete, fully-known value by
        # construction -- every element is an `ast.Constant` (§16.1.1's
        # site rules read it directly off `ctx.caller_args` rather than
        # through this generic path, but this branch keeps `_resolve_term`
        # total and correct for any OTHER caller, e.g. a synthetic fixture
        # that places a `SetLit` as an ordinary Cmp operand).
        return ir.Seq(tuple(ir.Lit(v) for v in term.values))
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
        value, _rule = _resolve_env_ref(term, ctx)  # §16.5: ⊤ on decline/no-match, unchanged.
        return value
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
# 260909 (spec §16.5.4, T43): the membership deciding case, reopened under
# all three of its reopening conditions -- (i) a complete-Seq Term exists
# (R-HEAD produces one; `_parse_term` still has no `ast.List`/`ast.Tuple`
# branch, so an `EnvRef` resolution is the ONLY complete `Seq` reachable by
# a membership `Cmp` anywhere in the contract table); (ii) an `ir.Seq` is a
# LOWER BOUND except where this box says otherwise -- the rule is stated at
# the `Cmp` NODE (checking the right operand's own SYNTAX, an R-HEAD-shaped
# `EnvRef`), never at the resolved VALUE, so a `Var` resolving to a general
# `ir.Seq` (from `call.kwargs`, a `param_defaults` entry, or an alpha/beta
# binding) can never decide a `not in` to `T` -- `ir.Seq` gains no field;
# (iii) the population is measured (§16.10.1 block 2's `n_membership_
# decided`, T46's job, not this function's).
# ---------------------------------------------------------------------------


def _maybe_membership_head(node: "pa.Cmp", ctx: _Ctx) -> "bool | None":
    """`Cmp(t, "in"/"not in", S)` decides ONLY when `S` -- `node.right` --
    is SYNTACTICALLY an R-HEAD-shaped `EnvRef` (`("self", "head")`, `args
    is None`) and `t` resolves to a `Lit`. Returns `None` (falls through to
    G8(2)'s unconditional ½) whenever the shape does not match at all, the
    observation is absent/partial (R-HEAD itself declines, so `S` does not
    resolve to a concrete `Seq`), or `t` is ⊤. No other comparator gains a
    case here and `_CMP_OPS` is unchanged (§16.5.4's own closing sentence)."""
    if not (isinstance(node.right, pa.EnvRef) and node.right.path == ("self", "head") and node.right.args is None):
        return None
    seq = _resolve_term(node.right, ctx)
    if not isinstance(seq, ir.Seq):
        return None  # R-HEAD declined -- ½, exactly increment 6's own G8(2).
    left = _resolve_term(node.left, ctx)
    if not isinstance(left, ir.Lit):
        return None
    is_member = any(isinstance(item, ir.Lit) and item.v == left.v for item in seq.items)
    return (not is_member) if node.op == "not in" else is_member


# ---------------------------------------------------------------------------
# Cmp -- the full dispatch, in order: G3, G4, membership (the R-HEAD
# reopening above, else ½), the Len-vs-Len integer comparison (excluded
# from G5's fold), then G5's unconditional ½ for everything else.
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
        decided = _maybe_membership_head(node, ctx)
        if decided is not None:
            return decided
        return None  # G8(2) unchanged: every other membership Cmp is ½.
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
# bound-name-is-always-⊤ rule (A-C13); the vacuous-quantification-over-⊤ is
# ½ WHEN THE BODY IS NOT DEFINITE, and never vacuously T -- a ⊤ seq with a
# ½ or oppositely-signed body cannot decide (G8(1)/A-C3, AMENDED 260909 by
# Q-MONO, §16.5.5, T43; see the amended text in
# `.praxia/docs/specs/260904_plr-sema-predicate-increment.md`, changed in
# this same commit).
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


def _eval_qmono(node: "pa.AllOf | pa.AnyOf", ctx: _Ctx, *, kind: str) -> "bool | None":
    """Q-MONO (§16.5.5, T43) -- E-INV's second named instance (R-CONST is
    the first): a definite body decides over a ⊤ seq, in exactly the two
    cells the EMPTY sequence also satisfies. `all(...)` over an empty
    sequence is `True` and `any(...)` over an empty sequence is `False`, so
    an unknown length cannot falsify either -- `AllOf` with a `T` body is
    `T`, `AnyOf` with an `F` body is `F`. The other two cells (`AllOf` with
    an `F` body, `AnyOf` with a `T` body) are exactly the ones the empty
    sequence FALSIFIES, so an unknown length must not decide them -- they
    stay ½ BY RULE, not by falling through: `AllOf(⊤, F)` and `AnyOf(⊤, T)`
    are both asserted ½ (AC-16.6), never `F`/`T`. Argument-independence is
    identical to R-CONST's own: `p` is evaluated with every comprehension-
    bound name at ⊤ (A-C13) BEFORE this function ever sees whether `seq`
    itself resolved, so the same one evaluation this module already made
    for the resolved-seq path is reused here without a second call."""
    p = evaluate_predicate(node.predicate, _with_all_to_top(ctx))
    if kind == "all" and p is True:
        return True
    if kind == "any" and p is False:
        return False
    return None  # the two vacuity cells, and any ½ body: stay ½.


def _eval_allof_anyof(node: "pa.AllOf | pa.AnyOf", ctx: _Ctx, *, kind: str) -> "bool | None":
    n = _resolve_seq_length(node.seq, ctx)
    if n is None:
        return _eval_qmono(node, ctx, kind=kind)  # ⊤ seq: Q-MONO, else ½ (A-C3, amended).
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
        # §16.5.1: R-HEAD stays ½ in predicate position UNCONDITIONALLY --
        # a dict is not a truth value and no guard at this pin uses it as
        # one -- checked by SHAPE, before any resolution attempt, so an
        # observed-but-empty head does not accidentally read as falsy here.
        if node.path == ("self", "head") and node.args is None:
            return None
        value, rule = _resolve_env_ref(node, ctx)
        if isinstance(value, ir.Seq) and rule in ("R-HEAD", "R-ARM"):
            # §17.1.2's amendment (move-family increment, T51): a complete
            # `Seq` decides by truthiness -- T iff non-empty, F iff empty --
            # keyed on the RULE's own completeness declaration, never on
            # `isinstance(value, ir.Seq)` alone (a future Seq-returning rule
            # that has not argued completeness stays ½ here, unchanged).
            return len(value.items) > 0
        if isinstance(value, ir.Lit):
            return bool(value.v)  # R-ATTR/R-CONST: the Kleene truth of the resolved Lit.
        return None  # declined, or an unadmitted EnvRef shape -- E-ENV's ½ unchanged.
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
    caller_reachability_clear: "bool | None" = None,
    caller_scope_trail: "list[str] | tuple[str, ...] | None" = None,
) -> bool:
    """E-UNCOND: may this guard emit `WILL_FAIL`? Clauses (4) and (5) are
    checked first (either can block regardless of the trail's own
    content); otherwise every entry must be satisfied by one of ways
    (1)-(3).

    260909 (spec §16.4, D1, T42): clause (4) is LIFTED at `depth == 1`
    under D1's three preconditions, `depth >= 2` untouched. Precondition
    2 (the call site itself is reached: `caller_reachability_clear` is
    `True` AND every `caller_scope_trail` entry satisfies ways (1)-(3),
    the SAME `_entry_satisfies_uncond` test `scope_entries` uses -- both
    fields absent, `None`, is fail-closed and blocks) is checked here,
    additively, for `depth == 1` only. Precondition 1 (the delegate's own
    body is clear, `k_reachability_clear`) and D's own enclosing scope
    (an in-loop guard like `:321` is blocked by the SAME `scope_entries`
    rule depth 0 already uses -- C19's own resolution: no fourth
    precondition, the `for` entry in D's OWN trail is what carries it) are
    NOT special-cased for `depth == 1` at all -- they fall through to the
    IDENTICAL two-line rule below, unchanged from depth 0. Precondition 3
    (a total argument map for the guard's free names) is implied by the
    caller already having observed `fires is True` before this function is
    ever invoked (§16.4's own box: "a guard firing on a ⊤ operand cannot
    fire") -- nothing to check for it here.
    """
    if depth >= 2:
        return False  # clause (4): depth >= 2 stays forbidden, unconditionally.
    if depth == 1:
        if not caller_reachability_clear or caller_scope_trail is None:
            return False  # D1 precondition 2, fail-closed on None/False.
        # `caller_scope_trail`'s entries are K's OWN statements, over K's
        # OWN namespace -- evaluated in K's own context (M2's identical
        # "evaluate in K, not in D" rule), never against `ctx` as-is
        # (whose `bindings_by_name`/depth-gating both belong to D at
        # `depth == 1`).
        caller_ctx = replace(
            ctx,
            depth=0,
            param_defaults=ctx.entry_param_defaults,
            bindings_by_name={},
            caller_args=None,
        )
        if not all(_entry_satisfies_uncond(entry, caller_ctx) for entry in caller_scope_trail):
            return False
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
# D6 site rules (260909, spec §16.1.3/§16.15 D6, T48, backlog #5026):
# hand-maintained semantic models of ONE named PLR function body each, keyed
# on `(qualname, lineno)` -- HM-26's own "site-keyed semantic model" class.
# `:321`'s own guard PREDICATE (`Not(Cmp(Var("resource_from_deck"), "==",
# Var("resource")))`) is unbindable by the generic machinery (§16.1.3's Q2:
# `resource_from_deck` is a plain `ast.Assign` of a call, which no binding
# idiom substitutes, and `resource` is a `for`-loop target nothing binds --
# both resolve to `(Top, "env")` under ordinary `_resolve_var`), so a site
# rule here REPLACES `evaluate_predicate` outright for the matched guard
# rather than resolving one `EnvRef` inside it, unlike R-HEAD/R-ATTR/R-CONST.
# Each entry is a total function `_Ctx -> bool | None`; `evaluate_guard`
# dispatches on `guard["site"]` below. T49's `:375`/`:383` rules land in
# this SAME dict when they ship (§16.15's D6 box: one registry row, D6_
# SITE_RULES is HM-26's own live measure).
# ---------------------------------------------------------------------------


def _eval_assert_resources_site_rule(ctx: _Ctx) -> "bool | None":
    """T48 (spec 260909_plr-sema-observation-increment.md §16.1.3/§16.15 D6,
    backlog #5026): the `:321` site rule, keyed on
    `(LiquidHandler._assert_resources_exist, :321)`. Evaluates the guard's
    predicate value to `F` (never `T` -- §16.1.3 Fact 1: an absent name
    raises at `:318`, not here, so the positive branch is never
    established) iff BOTH:

    1. `resources` (K's own parameter -- resolved generically through
       `_resolve_var`, which for a depth-1 guard replays M2's `caller_args`
       substitution unchanged, §16.4/T42) resolves to a CONCRETE `ir.Seq`
       whose every element is an `ir.Ref` carrying a RESOURCE declaration
       (`ref.slot in ctx.resources_by_slot` -- i.e. its underlying name was
       one `resources_from_example` actually declared, never an "absent
       entry, no RESOURCE instruction" slot the caller silently grounded).
    2. The harness's own aggregate deck-membership fact,
       `obs:deck_resources_verified` (`plr-sema/eval/oracle_common.py`'s
       `observation_env_members`), is `True` -- every one of THIS row's
       declared deck-parented resource names is a member of the observed
       `deck_resource_names`.

    ½ (decline) otherwise: `resources` unresolved (`ir.Top()`), a
    non-`Ref` element, a `Ref` whose slot has no RESOURCE declaration, or a
    missing/false aggregate fact -- the SAME `"guard_env_dependent"` reason
    every other §16.5 decline already carries (`resource`/
    `resource_from_deck` resolve `(Top, "env")`, never `(Top, "operand")`,
    so `guard_reason`'s clause 2 -- `guard_operand_unknown` -- never fires
    for this site; no new `REASON_VOCABULARY` member is needed).
    """
    value, _origin = _resolve_var("resources", ctx)
    if not isinstance(value, ir.Seq):
        return None
    for item in value.items:
        if not isinstance(item, ir.Ref) or item.slot not in ctx.resources_by_slot:
            return None
    obs = _observation(ctx.env)
    if obs.get("deck_resources_verified") is not True:
        return None
    return False


def _check_args_method_name(ctx: _Ctx) -> "str | None":
    """T49: `m`, the runtime backend method name, read from THIS guard's
    own `ctx.caller_args["method"]` entry -- the caller-side expression at
    `self._check_args(self.backend.<m>, ...)`
    (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:541-546`),
    an `EnvRef` whose LAST path segment is `m` (§16.3's own selection rule
    reads the identical "last segment of an EnvRef path" fact, just from a
    different JSON location). Never resolved as a VALUE through
    `_resolve_var`/`_resolve_term` -- `method` denotes a PLR method, not an
    `ir.Value` this analyzer models -- so this reads the raw JSON directly.
    `None` on anything else: no `caller_args`, no `"method"` entry, or an
    entry that is not an `EnvRef`, or an `EnvRef` with an empty path."""
    caller_args = ctx.caller_args
    if not caller_args:
        return None
    method_json = caller_args.get("method")
    if not isinstance(method_json, Mapping) or method_json.get("node") != "EnvRef":
        return None
    path = method_json.get("path")
    if not isinstance(path, (list, tuple)) or not path:
        return None
    return str(path[-1])


def _check_args_default_set(ctx: _Ctx) -> "frozenset[str] | None":
    """T49: the caller-side `default` set, read from THIS guard's own
    `ctx.caller_args["default"]` entry -- G9's `SetLit` production, now
    that `default={"ops", "use_channels"}`
    (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:541-546`)
    parses as a `Term` at all. `None` when the entry is absent (an
    un-regenerated table, or a call-site `default=` expression that is not
    a plain `ast.Set` of constants -- M1 clause 5's ordinary partial-
    admission refusal) or is not a `SetLit`, or carries a non-`str`
    element (defensive; `_parse_set_lit` never emits one, but this
    function does not trust the wire without checking)."""
    caller_args = ctx.caller_args
    if not caller_args:
        return None
    default_json = caller_args.get("default")
    if not isinstance(default_json, Mapping) or default_json.get("node") != "SetLit":
        return None
    values = default_json.get("values")
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        return None
    return frozenset(values)


def _check_args_surface_row(ctx: _Ctx) -> "Mapping[str, Any] | None":
    """T49: the §16.3 backend-surface row for `(observed backend_class, m)`
    -- `None` (decline) whenever `backend_class` is unobserved, `m` cannot
    be read (`_check_args_method_name`), or the row is absent (either the
    pair was never a surface candidate, or §16.3's C15 absence rule removed
    it -- both cases are indistinguishable here BY DESIGN, and both mean
    the same thing to a caller: the surface does not vouch for this
    `(class, method)` pair, so decline rather than guess)."""
    obs = _observation(ctx.env)
    backend_class = obs.get("backend_class")
    if backend_class is None:
        return None
    method = _check_args_method_name(ctx)
    if method is None:
        return None
    return ctx.backend_surface.get(f"{backend_class}.{method}")


def _eval_check_args_missing_site_rule(ctx: _Ctx) -> "bool | None":
    """T49 (spec 260909_plr-sema-observation-increment.md §16.1.1/§16.15
    D6, backlog #5026): the `:375` site rule, keyed on
    `(LiquidHandler._check_args, :375)`. `:375`'s own guard predicate is
    `Cmp(Len(Var("missing")), ">", Lit(0))`; `missing` is a LOCAL of
    `_check_args` (`non_default - backend_kws`, `:373`), never one of its
    parameters, so it is unreachable through M1/M2's caller_args machinery
    at all -- this rule decides the guard's OWN predicate value directly,
    the same replacement shape `:321`'s rule above uses.

    Evaluates `F` (never `T` -- the arithmetic only ever proves the
    MINUEND empty, never the SUBTRAHEND non-empty, §16.1.1's own pin
    derivation) iff the observed `backend_class`'s `(class, method)` row
    in §16.3's surface (`m` read from `ctx.caller_args["method"]`) has a
    `params` list that is a SUBSET of the caller-side `default` set (read
    from `ctx.caller_args["default"]`, G9's `SetLit`) -- `params(backend_
    class, m) ⊆ default` implies `non_default ⊆ default_args`, so
    `missing = non_default - backend_kws ⊆ default - backend_kws = ∅`
    whatever `backend_kws` is (§16.1.1's own step-by-step).

    ½ (decline) otherwise: no surface row (absent candidate or C15's
    absence rule), a row with no `params` list, or no `default` caller-arg
    -- the SAME `"guard_env_dependent"` reason every other §16.5 decline
    carries (`missing` resolves `(Top, "env")` under ordinary
    `_resolve_var`, never `(Top, "operand")`)."""
    row = _check_args_surface_row(ctx)
    if row is None:
        return None
    params = row.get("params")
    if not isinstance(params, list) or not all(isinstance(p, str) for p in params):
        return None
    default_set = _check_args_default_set(ctx)
    if default_set is None:
        return None
    if set(params) <= default_set:
        return False
    return None


def _eval_check_args_strict_site_rule(ctx: _Ctx) -> "bool | None":
    """T49 (spec 260909_plr-sema-observation-increment.md §16.1.1/§16.15
    D6, backlog #5026): the `:383` site rule, keyed on
    `(LiquidHandler._check_args, :383)`. `:383`'s own guard predicate is
    `Cmp(Var("strictness"), "==", Attr(Var("Strictness"), "STRICT"))`, and
    this rule NEVER evaluates it -- `strictness`'s caller-side expression
    is `get_strictness()`, a non-`self`-rooted call that is not a `Term`
    under G1, so it carries no `caller_args` entry and `Strictness.STRICT`
    is a module-level `Attr`, not an `EnvRef` under G7 either (§16.1.1's
    own box: deciding `:383` from the predicate "is impossible whatever
    `env` carries").

    The real discharge route is the recorded `scope_trail`'s second entry
    (after E-UNCOND(6) excludes the self-entry), `"if len(extra) > 0 and
    len(vars_keyword) == 0"`: when `has_var_keyword` is `True`, the
    recorded `vars_keyword` set is non-empty by construction, so
    `len(vars_keyword) == 0` is `F`, the `And` is `F` REGARDLESS of
    `len(extra)`, and the nested raise is unreachable regardless of
    `strictness`'s own value. `vars_keyword` is -- like `missing` above --
    a LOCAL of `_check_args`, never one of its parameters, so E-SCOPE's
    own fresh `pa.parse` + `evaluate_predicate` replay of that trail
    entry (`_scope_entry_value`) cannot resolve it either; this rule
    returns the trail's own conclusion (`F`) directly, at the WHOLE-GUARD
    level, rather than teaching `_resolve_var` a THIRD name-keyed special
    case for one local that only ever appears in one function.

    Evaluates `F` (never `T`) iff the observed `backend_class`'s `(class,
    method)` row in §16.3's surface has `has_var_keyword` exactly `True`.
    ½ (decline) otherwise: no surface row, or `has_var_keyword` absent/
    `False`."""
    row = _check_args_surface_row(ctx)
    if row is None:
        return None
    if row.get("has_var_keyword") is not True:
        return None
    return False


#: HM-26's own live measure (`plr_sema._hand_maintained:_measure_hm26`):
#: `len(D6_SITE_RULES)`. T48's `:321` plus T49's `:375`/`:383` pair --
#: three entries, the SAME registry row (§16.15's D6 box: "whichever lands
#: first adds it, the second asserts it already exists").
D6_SITE_RULES: "dict[tuple[str, int], Any]" = {
    ("LiquidHandler._assert_resources_exist", 321): _eval_assert_resources_site_rule,
    ("LiquidHandler._check_args", 375): _eval_check_args_missing_site_rule,
    ("LiquidHandler._check_args", 383): _eval_check_args_strict_site_rule,
}


def _site_rule_for(guard: Mapping[str, Any]) -> "Any | None":
    """`guard["site"]` -> its `D6_SITE_RULES` entry, or `None` when the
    guard's site is not one of the (qualname, lineno) pairs D6 covers --
    the ordinary `evaluate_predicate` path, unchanged, for every other
    guard in the contract table."""
    site = guard.get("site")
    if not isinstance(site, Mapping):
        return None
    qualname = site.get("qualname")
    lineno = site.get("lineno")
    if qualname is None or lineno is None:
        return None
    return D6_SITE_RULES.get((qualname, int(lineno)))


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
    entry_param_defaults = contract.get("param_defaults", {})
    ctx = _Ctx(
        call=call,
        resources_by_slot=resources_by_slot,
        param_defaults=entry_param_defaults if depth == 0 else {},
        bindings_by_name=bindings_by_name,
        depth=depth,
        channel_kwarg=channel_kwarg,
        channels=channels,
        env=env,
        class_hierarchy=class_hierarchy,
        # 260909 (spec §16.4, T42): `caller_args` -- present only on a
        # depth-1 guard whose `(K, D)` pair M1 admitted (`None` otherwise,
        # the same additive-field default `guard.get(...)` already gives
        # every other T42 field); `entry_param_defaults` unconditionally,
        # since M2 step (1)'s caller-context resolution needs K's own
        # param_defaults regardless of THIS guard's own depth.
        caller_args=guard.get("caller_args"),
        entry_param_defaults=entry_param_defaults,
        # 260909 (spec §16.3/§16.5, T41/T43): R-CONST's own lookup table --
        # additive, present only on a contract entry `derive/__main__.py`
        # attached one to (§16.3's derived surface, filtered to the
        # qualnames that actually carry a `self.backend.<method>(...)`
        # EnvRef); `{}` degrades R-CONST to an unconditional decline, the
        # same fail-closed default `param_defaults` etc. already use.
        backend_surface=contract.get("backend_surface", {}).get("rows", {}),
    )

    scope_entries = _exclude_self_entry(guard)
    if scope_excludes(scope_entries, ctx):
        return _SAFE

    site_rule = _site_rule_for(guard)
    value = site_rule(ctx) if site_rule is not None else evaluate_predicate(predicate, ctx)
    kind = guard.get("kind", "raise_guard")
    fires = value if kind == "raise_guard" else _kleene_not(value)

    if fires is False:
        return _SAFE
    if fires is True:
        if guard_is_unconditional(
            scope_entries,
            ctx,
            depth=depth,
            k_reachability_clear=k_reachability_clear,
            caller_reachability_clear=guard.get("caller_reachability_clear"),
            caller_scope_trail=guard.get("caller_scope_trail"),
        ):
            return _WILL_FAIL
        return GuardResult(verdict="unknown", reason="guard_env_dependent")
    return GuardResult(verdict="unknown", reason=guard_reason(predicate, ctx))
