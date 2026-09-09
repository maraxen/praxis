"""plr_sema.derive.bindings: ``param_defaults`` (D1) and the alpha/beta
local-binding idioms (increment 6, spec 260904 §15.3/§15.4, T30b).

**Scope.** This module is pure derive-time logic over ONE PLR function's own
``ast.FunctionDef``/``ast.AsyncFunctionDef`` node -- it does no file-system
scanning of its own (that is ``receiver_state.build_plr_function_index``'s
job, kept there so this module never imports ``plr_sema.derive`` and cannot
create an import cycle with it) and no evaluation (turning a binding into a
truth value against a concrete IR call is T31's job, not built yet).

**``param_defaults`` (D1, §15.4's E-CALL(2)).** Per PLR function, ``{param:
<JSON literal>}`` read straight off ``ast.arguments.defaults``/
``kw_defaults``, restricted to ``ast.Constant`` values (``None``/``bool``/
``int``/``float``/``str``) -- anything else (a call, a name, a display) is
OMITTED, fail-closed, never guessed.

**The alpha/beta idioms (§15.3).** Spec's own wording for what counts as a
candidate: "a free local ``x`` of a guard (a ``Var`` in its ``predicate``
that is not a parameter of the defining function ``K``)". Read literally
that would EXCLUDE ``pick_up_tips``'s own ``offsets`` -- which spec's own
worked example requires to be beta-bound at ``:517`` -- because ``offsets``
IS a parameter name of ``pick_up_tips``. The resolution (confirmed against
§15.4's E-CALL step ordering, which tries ``call.kwargs`` FIRST and falls
back to a binding only when the call-side value is absent/falsy): a
parameter name that PLR itself rebinds before a guard reads it (``offsets =
offsets or [...]``) is, AT THE GUARD, a reference to the REBOUND LOCAL, not
to the raw incoming argument -- E-CALL's ordering is what lets the caller's
real value still win when present. **This module therefore attempts a
binding search for EVERY free ``Var`` name in the guard's predicate,
parameter or not**, and lets the "is there a same-body ``Assign`` targeting
this exact name" test do the actual gating: a name with zero ``Assign``
writes in ``K`` (``tip_spots``, ``self``) simply never produces a
candidate, which is the correct outcome for a genuine parameter that is
never rebound -- it is E-CALL step (1)'s job, not this module's.

**Free-var extraction reuses the typed tree, not a second string scan.**
:func:`free_var_names` walks a already-parsed :class:`predicate_ast.Predicate`
(or ``Term``) exactly the way :func:`predicate_ast.contains_opaque` does --
same recursion shape, collecting ``Var.name`` instead of testing for
``Opaque``.

**The published wire shape** for one binding is a plain JSON-safe dict, not
a `predicate_ast` node -- T31 (the evaluator) does not exist yet and this
module does not know its consumption shape, so the encoding here is a
provisional, clearly-documented contract:

* alpha: ``{"idiom": "alpha", "x": <name>, "iter": <param-name>, "pred":
  <predicate_ast.to_json of the parsed `if` clause>}`` -- the bound TERM is
  ``Filtered(seq=Var(iter), predicate=pred)`` in `predicate_ast`'s own
  grammar, decomposed into its two parts rather than nested, so a consumer
  that only wants ``iter`` never has to unwrap a ``Filtered`` JSON node.
* beta: ``{"idiom": "beta", "x": <name>, "param": <p>, "default_shape":
  "range" | "repeat"}`` -- the bound FACT is ``Len(x) == Len(param)``;
  ``default_shape`` records which of the two syntactic defaults produced it
  (``list(range(len(<p>)))`` vs ``[<expr>] * len(<p>)``), published because
  it is free and because a later increment's evaluator may care which one
  it is dealing with even though both bind the identical length fact.
"""

from __future__ import annotations

import ast
from typing import Any

from plr_sema.derive.predicate_ast import (
    AllOf,
    And,
    AnyOf,
    Attr,
    Cmp,
    EnvRef,
    Filtered,
    Is,
    IsInstance,
    Len,
    Lit,
    Not,
    Opaque,
    Or,
    Predicate,
    SetOf,
    TRUE,
    Term,
    Var,
    Zip,
    from_json as predicate_from_json,
    parse as parse_predicate,
    to_json as predicate_to_json,
)

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef

__all__ = [
    "param_defaults_from_function",
    "free_var_names",
    "compute_local_bindings_for_guard",
    "compute_all_local_bindings",
    "compute_reachability_clear",
    "substitute",
    "build_qualname_index",
    "is_plr_layer_method",
    "demote_refused_env_refs",
]


# ---------------------------------------------------------------------------
# D1 -- param_defaults (§15.4's E-CALL(2))
# ---------------------------------------------------------------------------

_JSON_SCALAR = (bool, int, float, str, type(None))


def _constant_json(node: ast.expr) -> tuple[bool, Any]:
    """``(True, value)`` iff ``node`` is an ``ast.Constant`` whose value is
    one of the five JSON-safe scalar types -- ``(False, None)`` for
    anything else (a call, a name, a display, a non-JSON-safe constant like
    a complex number or bytes), which the caller OMITS rather than guesses
    (fail-closed, D1's own normative box)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, _JSON_SCALAR):
        return True, node.value
    return False, None


def param_defaults_from_function(node: FunctionNode) -> dict[str, Any]:
    """D1: ``{param: <JSON literal>}`` for every positional-or-keyword /
    positional-only / keyword-only parameter of ``node`` whose default is
    an ``ast.Constant`` -- read straight off ``ast.arguments.defaults``
    (aligned to the END of ``posonlyargs + args``, standard Python
    semantics: the last ``len(defaults)`` positional params carry one) and
    ``kw_defaults`` (aligned 1:1 with ``kwonlyargs``, with ``None`` entries
    meaning "this keyword-only param has no default" -- NOT the JSON value
    ``null``, a real Python ``None`` sentinel in the AST list itself, tested
    via ``is None`` before ever inspecting the node's own value).
    """
    out: dict[str, Any] = {}
    args = node.args
    positional = list(args.posonlyargs) + list(args.args)
    defaults = list(args.defaults)
    offset = len(positional) - len(defaults)
    for i, default_node in enumerate(defaults):
        ok, value = _constant_json(default_node)
        if ok:
            out[positional[offset + i].arg] = value
    for arg, default_node in zip(args.kwonlyargs, args.kw_defaults):
        if default_node is None:
            continue  # this keyword-only param has no default at all.
        ok, value = _constant_json(default_node)
        if ok:
            out[arg.arg] = value
    return out


# ---------------------------------------------------------------------------
# free_var_names -- every Var reachable in a Predicate/Term tree.
# ---------------------------------------------------------------------------


def free_var_names(node: "Predicate | Term") -> frozenset[str]:
    """All ``Var`` names reachable anywhere in ``node``'s tree, walking
    BOTH ``Predicate``- and ``Term``-typed slots -- the same recursion
    ``predicate_ast.contains_opaque`` uses, collecting names instead of
    testing for ``Opaque``. Spec 260904 §15.3's own wording for what
    alpha/beta search for: "a free local ``x`` of a guard (a ``Var`` in its
    ``predicate``...)"."""
    if isinstance(node, Var):
        return frozenset({node.name})
    if isinstance(node, (TRUE, Opaque, Lit)):
        return frozenset()
    if isinstance(node, Not):
        return free_var_names(node.predicate)
    if isinstance(node, (And, Or)):
        out: set[str] = set()
        for p in node.predicates:
            out |= free_var_names(p)
        return frozenset(out)
    if isinstance(node, Cmp):
        return free_var_names(node.left) | free_var_names(node.right)
    if isinstance(node, Is):
        return free_var_names(node.term)
    if isinstance(node, IsInstance):
        return free_var_names(node.term)
    if isinstance(node, (AllOf, AnyOf)):
        return free_var_names(node.seq) | free_var_names(node.predicate)
    if isinstance(node, (Len, SetOf)):
        return free_var_names(node.term)
    if isinstance(node, Attr):
        return free_var_names(node.term)
    if isinstance(node, Filtered):
        return free_var_names(node.seq) | free_var_names(node.predicate)
    if isinstance(node, Zip):
        out = set()
        for i in node.items:
            out |= free_var_names(i)
        return frozenset(out)
    if isinstance(node, EnvRef):
        # `self` (the path root) is never a free LOCAL -- it is a
        # parameter of every PLR method and, post-amendment, is only ever
        # legitimately spelled as an EnvRef's own path, never as a bare
        # Var; only the CALL's own arguments (shape (2)) can mention a
        # genuine free name (e.g. `channel`, `tip` at `:514`).
        if node.args is None:
            return frozenset()
        out = set()
        for a in node.args:
            out |= free_var_names(a)
        return frozenset(out)
    raise TypeError(f"free_var_names: unrecognized node type {type(node)!r}")


# ---------------------------------------------------------------------------
# substitute -- the alpha/beta-SUBSTITUTED tree (round 2, A-C4).
# ---------------------------------------------------------------------------


def substitute(node: "Predicate | Term", bindings_by_name: dict[str, dict[str, Any]]) -> "Predicate | Term":
    """Replaces every free ``Var(name)`` whose name has an ALPHA binding in
    ``bindings_by_name`` with the bound term
    (``Filtered(seq=Var(iter), predicate=<the alpha idiom's own parsed `if`
    clause>)``), recursively -- the tree ``contains_opaque``/``contains_env_ref``
    must range over for reason-assignment purposes (S15.2 G7's normative
    box, round 2 A-C4), not the raw ``predicate`` field a guard carries on
    the wire. A BETA binding is left untouched: beta binds only a LENGTH
    fact (``Len(x) == Len(param)``), never a term ``x`` could be replaced
    by, so it can neither introduce nor hide an ``Opaque``/``EnvRef`` node.
    A name with no binding at all is also left untouched -- ordinary,
    unresolved free ``Var``.

    ``bindings_by_name`` is the same ``{x: <binding JSON>}`` map every
    other function in this module keys guard bindings by (``b["idiom"]``,
    ``b["iter"]``/``b["param"]``, ``b["pred"]`` for alpha).
    """
    if isinstance(node, Var):
        b = bindings_by_name.get(node.name)
        if b is not None and b["idiom"] == "alpha":
            inner = predicate_from_json(b["pred"])
            return Filtered(seq=Var(b["iter"]), predicate=substitute(inner, bindings_by_name))
        return node
    if isinstance(node, (TRUE, Opaque, Lit)):
        return node
    if isinstance(node, EnvRef):
        if node.args is None:
            return node
        return EnvRef(node.path, tuple(substitute(a, bindings_by_name) for a in node.args))
    if isinstance(node, Not):
        return Not(substitute(node.predicate, bindings_by_name))
    if isinstance(node, And):
        return And(tuple(substitute(p, bindings_by_name) for p in node.predicates))
    if isinstance(node, Or):
        return Or(tuple(substitute(p, bindings_by_name) for p in node.predicates))
    if isinstance(node, Cmp):
        return Cmp(substitute(node.left, bindings_by_name), node.op, substitute(node.right, bindings_by_name))
    if isinstance(node, Is):
        return Is(substitute(node.term, bindings_by_name), node.negated)
    if isinstance(node, IsInstance):
        return IsInstance(substitute(node.term, bindings_by_name), node.types)
    if isinstance(node, (AllOf, AnyOf)):
        cls = type(node)
        return cls(seq=substitute(node.seq, bindings_by_name), predicate=substitute(node.predicate, bindings_by_name))
    if isinstance(node, Len):
        return Len(substitute(node.term, bindings_by_name))
    if isinstance(node, SetOf):
        return SetOf(substitute(node.term, bindings_by_name))
    if isinstance(node, Attr):
        return Attr(substitute(node.term, bindings_by_name), node.name)
    if isinstance(node, Filtered):
        return Filtered(substitute(node.seq, bindings_by_name), substitute(node.predicate, bindings_by_name))
    if isinstance(node, Zip):
        return Zip(tuple(substitute(i, bindings_by_name) for i in node.items))
    raise TypeError(f"substitute: unrecognized node type {type(node)!r}")


# ---------------------------------------------------------------------------
# G7's PLR-layer test on a shape-(2) EnvRef (round 2, A-C1) -- applied
# POST-parse, here, where `function_index` already lives (S15.2's normative
# box).
# ---------------------------------------------------------------------------


def build_qualname_index(function_index: dict[tuple[str, str, int], Any]) -> frozenset[tuple[str, str]]:
    """Reduces ``receiver_state.build_plr_function_index``'s own
    ``(module, qualname, lineno) -> AST`` map to the ``(module, qualname)``
    pairs alone, dropping ``lineno`` -- G7's PLR-layer test asks "does a key
    ``(module, f'{class_name}.{name}', *)`` exist?", a question about
    qualname alone, over potentially many linenos (overloads, redefinitions)
    that all answer it identically."""
    return frozenset((module, qualname) for module, qualname, _lineno in function_index)


def is_plr_layer_method(
    qualname_index: frozenset[tuple[str, str]], module: str, class_name: str | None, name: str
) -> bool:
    """``True`` iff ``self.<name>(...)`` names an indexed PLR-layer method
    of the receiver class -- the refusal test G7 shape (2) applies to a
    length-2 ``EnvRef`` path (``k == 1``). ``class_name is None`` (a
    module-level guard with no receiver) can never match a
    ``f"{class_name}.{name}"`` qualname, so it is unconditionally NOT an
    indexed method -- fails open toward EnvRef only because there is no
    receiver CLASS for the call to be a coverage gap of."""
    if class_name is None:
        return False
    return (module, f"{class_name}.{name}") in qualname_index


def demote_refused_env_refs(
    predicate: Predicate,
    *,
    module: str,
    class_name: str | None,
    qualname_index: frozenset[tuple[str, str]] | None,
) -> Predicate:
    """G7's PLR-layer test, applied post-parse: a shape-(2) ``EnvRef`` with
    ``len(path) == 2`` (``self.<name>(...)``) is REFUSED -- demoted to
    ``Opaque`` at its smallest enclosing predicate construction, the SAME
    propagation ``predicate_ast``'s own totality mechanism already uses for
    an ordinary term-parse failure -- when ``<name>`` IS an indexed
    PLR-layer method of the receiver class (``self._is_error_tail``,
    ``self._check_96_head_fits_in_container``: coverage gaps the closure
    could have inlined, not missing observations).

    **Fail-closed default.** ``qualname_index is None`` (no
    ``function_index`` was supplied to ``derive_contract``) refuses EVERY
    ``k == 1`` candidate unconditionally -- the same fail-closed default
    ``InlinedGuard.bindings`` already takes when no index is available.
    Shape (1) (a bare attribute read, ``args is None``) and shape (2) with
    ``len(path) >= 3`` (a read THROUGH a receiver attribute, e.g.
    ``self.backend.can_pick_up_tip(...)``) are NEVER refused by this
    function -- they are not this test's business at all.
    """

    def is_refused(name: str) -> bool:
        if qualname_index is None:
            return True
        return is_plr_layer_method(qualname_index, module, class_name, name)

    return _demote_predicate(predicate, is_refused)


def _opaque_text(node: "Predicate | Term") -> str:
    """Best-effort diagnostic text for a node this pass demotes -- never
    load-bearing (mirrors ``predicate_ast._unparse``'s own disclaimer):
    there is no original AST text available here (we are rewriting an
    ALREADY-PARSED tree, not re-walking source), so this is the node's own
    JSON encoding rendered as text, not ``ast.unparse`` of anything."""
    try:
        return repr(predicate_to_json(node))
    except Exception:  # noqa: BLE001 -- diagnostic text only, never load-bearing.
        return "<refused-env-ref>"


def _demote_term(term: "Term", is_refused) -> "Term | None":
    if isinstance(term, (Var, Lit)):
        return term
    if isinstance(term, EnvRef):
        if term.args is not None and len(term.path) == 2 and is_refused(term.path[1]):
            return None
        return term
    if isinstance(term, Len):
        inner = _demote_term(term.term, is_refused)
        return None if inner is None else Len(inner)
    if isinstance(term, SetOf):
        inner = _demote_term(term.term, is_refused)
        return None if inner is None else SetOf(inner)
    if isinstance(term, Attr):
        inner = _demote_term(term.term, is_refused)
        return None if inner is None else Attr(inner, term.name)
    if isinstance(term, Filtered):
        seq = _demote_term(term.seq, is_refused)
        if seq is None:
            return None
        return Filtered(seq, _demote_predicate(term.predicate, is_refused))
    if isinstance(term, Zip):
        items: list[Term] = []
        for it in term.items:
            si = _demote_term(it, is_refused)
            if si is None:
                return None
            items.append(si)
        return Zip(tuple(items))
    raise TypeError(f"_demote_term: unrecognized node type {type(term)!r}")


def _demote_predicate(pred: "Predicate", is_refused) -> "Predicate":
    if isinstance(pred, (TRUE, Opaque)):
        return pred
    if isinstance(pred, EnvRef):
        sanitized = _demote_term(pred, is_refused)
        return sanitized if sanitized is not None else Opaque(_opaque_text(pred))
    if isinstance(pred, Not):
        return Not(_demote_predicate(pred.predicate, is_refused))
    if isinstance(pred, And):
        return And(tuple(_demote_predicate(p, is_refused) for p in pred.predicates))
    if isinstance(pred, Or):
        return Or(tuple(_demote_predicate(p, is_refused) for p in pred.predicates))
    if isinstance(pred, Cmp):
        left = _demote_term(pred.left, is_refused)
        right = _demote_term(pred.right, is_refused)
        if left is None or right is None:
            return Opaque(_opaque_text(pred))
        return Cmp(left, pred.op, right)
    if isinstance(pred, Is):
        term = _demote_term(pred.term, is_refused)
        return Opaque(_opaque_text(pred)) if term is None else Is(term, pred.negated)
    if isinstance(pred, IsInstance):
        term = _demote_term(pred.term, is_refused)
        return Opaque(_opaque_text(pred)) if term is None else IsInstance(term, pred.types)
    if isinstance(pred, (AllOf, AnyOf)):
        seq = _demote_term(pred.seq, is_refused)
        if seq is None:
            return Opaque(_opaque_text(pred))
        cls = type(pred)
        return cls(seq=seq, predicate=_demote_predicate(pred.predicate, is_refused))
    raise TypeError(f"_demote_predicate: unrecognized node type {type(pred)!r}")


# ---------------------------------------------------------------------------
# Statement-position walking, chain-tracked (the scope condition's own
# mechanism: "not nested inside an If/For/While/Try/With that does not
# ALSO contain the guard").
# ---------------------------------------------------------------------------

_StmtChain = list[ast.stmt]


def _walk_statements(stmts: list[ast.stmt], chain: _StmtChain) -> list[tuple[ast.stmt, _StmtChain]]:
    """Every statement reachable from ``stmts`` at ANY nesting depth within
    the SAME function scope -- descends into ``If``/``For``/``AsyncFor``/
    ``While``/``Try``/``With``/``AsyncWith`` bodies (``body``/``orelse``/
    ``finalbody``/each ``handler.body``) but NEVER into a nested
    ``FunctionDef``/``AsyncFunctionDef``/``Lambda``/``ClassDef``'s own body
    -- that is a different scope's statements, out of reach for K's own
    single-write and scope-position tests.

    Returns ``(stmt, chain)`` pairs where ``chain`` is every enclosing
    compound statement from the function's own top level down to and
    INCLUDING ``stmt`` itself -- e.g. a statement inside an ``if``'s body
    has chain ``[the_if_stmt, stmt]``. An ``elif`` self-nests as another
    ``If`` in ``orelse`` (mirrors ``ast``'s own shape and the survey's own
    ``visit_If`` compounding), so a three-way ``if``/``elif``/``elif``
    chain naturally shows up as three nested chains, deepest last.
    """
    out: list[tuple[ast.stmt, _StmtChain]] = []
    for stmt in stmts:
        this_chain = [*chain, stmt]
        out.append((stmt, this_chain))
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue  # a different scope -- never descend into it.
        for field_name in ("body", "orelse", "finalbody"):
            sub = getattr(stmt, field_name, None)
            if sub:
                out.extend(_walk_statements(sub, this_chain))
        for handler in getattr(stmt, "handlers", ()):
            out.extend(_walk_statements(handler.body, this_chain))
    return out


def _bare_assign_target(stmt: ast.stmt) -> str | None:
    """The bare ``ast.Name`` target's id iff ``stmt`` is a single-target
    ``ast.Assign`` to one, else ``None`` -- never a tuple/starred/attribute
    target (those are not "a bare ``ast.Name`` ``x``" per §15.3's own
    shape, and are exactly the shapes AC-15.2 fails closed on)."""
    if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
        return None
    target = stmt.targets[0]
    return target.id if isinstance(target, ast.Name) else None


def _count_assigns_to_name(stmts: list[tuple[ast.stmt, _StmtChain]], name: str) -> int:
    return sum(1 for stmt, _ in stmts if _bare_assign_target(stmt) == name)


# ---------------------------------------------------------------------------
# alpha/beta shape matchers -- pure AST-shape tests, no evaluation.
# ---------------------------------------------------------------------------


def _param_names(node: FunctionNode) -> frozenset[str]:
    args = node.args
    names = {a.arg for a in args.posonlyargs} | {a.arg for a in args.args} | {a.arg for a in args.kwonlyargs}
    if args.vararg is not None:
        names.add(args.vararg.arg)
    if args.kwarg is not None:
        names.add(args.kwarg.arg)
    return frozenset(names)


def _match_alpha(value: ast.expr, param_names: frozenset[str]) -> tuple[str, Predicate] | None:
    """§15.3(alpha): ``[<e> for <e> in <param> if <pred>]`` -- single
    generator, sync, exactly one ``if``, the elt IS the loop target (the
    identity map, PLR's "reject the wrongly-typed elements" shape -- never
    a projection), and the ``iter`` is a bare ``ast.Name`` naming a
    PARAMETER of ``K``. Returns ``(iter_name, parsed_if_predicate)`` or
    ``None`` -- the ``if`` clause is re-parsed through the PUBLIC
    ``predicate_ast.parse`` (via ``ast.unparse``) rather than a private
    entry point, so this module never depends on `predicate_ast`
    internals beyond its documented API.
    """
    if not isinstance(value, ast.ListComp) or len(value.generators) != 1:
        return None
    comp = value.generators[0]
    if comp.is_async or len(comp.ifs) != 1:
        return None
    if not (isinstance(value.elt, ast.Name) and isinstance(comp.target, ast.Name) and value.elt.id == comp.target.id):
        return None
    if not (isinstance(comp.iter, ast.Name) and comp.iter.id in param_names):
        return None
    try:
        if_text = ast.unparse(comp.ifs[0])
    except Exception:  # noqa: BLE001 -- best-effort text; parse() itself is total anyway.
        return comp.iter.id, Opaque("<unparseable>")
    return comp.iter.id, parse_predicate(if_text)


def _bare_len_name(node: ast.expr) -> str | None:
    """``len(<p>)`` where ``<p>`` is a bare ``ast.Name`` -- returns ``<p>``'s
    id, else ``None``."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "len"
        and len(node.args) == 1
        and not node.keywords
        and isinstance(node.args[0], ast.Name)
    ):
        return node.args[0].id
    return None


def _match_range_default(node: ast.expr) -> str | None:
    """``list(range(len(<p>)))``."""
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "list"
        and len(node.args) == 1
        and not node.keywords
    ):
        return None
    inner = node.args[0]
    if not (
        isinstance(inner, ast.Call)
        and isinstance(inner.func, ast.Name)
        and inner.func.id == "range"
        and len(inner.args) == 1
        and not inner.keywords
    ):
        return None
    return _bare_len_name(inner.args[0])


def _match_repeat_default(node: ast.expr) -> str | None:
    """``[<expr>] * len(<p>)`` -- the left operand is a list DISPLAY (any
    elements), never a resolved value; only the length matters."""
    if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult)):
        return None
    if not isinstance(node.left, ast.List):
        return None
    return _bare_len_name(node.right)


def _match_beta(value: ast.expr, x_name: str) -> tuple[str, str] | None:
    """§15.3(beta): ``x = x or <default>`` -- an ``ast.BoolOp(Or)`` with
    EXACTLY two operands (a 3+-operand chain is P3a's territory, declined
    here outright per §15.3's own "binds only when every intermediate
    operand resolves F" discussion -- a middle operand is unresolvable at
    derive time regardless of what it is, so beta simply never matches a
    chain longer than two). Returns ``(param_name, "range" | "repeat")`` or
    ``None``.
    """
    if not (isinstance(value, ast.BoolOp) and isinstance(value.op, ast.Or)):
        return None
    if len(value.values) != 2:
        return None
    first, last = value.values
    if not (isinstance(first, ast.Name) and first.id == x_name):
        return None
    param = _match_range_default(last)
    if param is not None:
        return param, "range"
    param = _match_repeat_default(last)
    if param is not None:
        return param, "repeat"
    return None


def _is_beta_preserving_rebinding(stmt: ast.stmt, x_name: str) -> bool:
    """The ONE second-write shape that does not invalidate a beta binding
    (round 1, C6): ``x = [<elt> for <e> in x]`` -- single generator, sync,
    NO ``if`` clause, a bare-``Name`` comprehension target, and an ``iter``
    that is the bare ``ast.Name`` ``x`` itself. ``<elt>`` is unconstrained
    (an ``ast.IfExp`` in element position is exactly PLR's real shape,
    ``[float(fr) if fr is not None else None for fr in flow_rates]``) --
    only the comprehension's OWN shape is constrained, because only that
    shape provably preserves ``Len(x)``.
    """
    target = _bare_assign_target(stmt)
    if target != x_name:
        return False
    value = stmt.value  # type: ignore[union-attr]  -- _bare_assign_target already confirmed ast.Assign
    if not isinstance(value, ast.ListComp) or len(value.generators) != 1:
        return False
    comp = value.generators[0]
    if comp.is_async or comp.ifs:
        return False
    return isinstance(comp.target, ast.Name) and isinstance(comp.iter, ast.Name) and comp.iter.id == x_name


# ---------------------------------------------------------------------------
# The public entry point.
# ---------------------------------------------------------------------------


def _ancestors_are_prefix(candidate_ancestors: _StmtChain, guard_chain: _StmtChain) -> bool:
    """The scope condition's "not nested inside a header that does not
    ALSO contain the guard": every compound statement enclosing the
    candidate assignment must ALSO enclose the guard, at the SAME position
    in both chains (identity comparison -- both chains are built by walking
    the SAME tree, so ``is`` is exact and never a text/structural
    coincidence)."""
    if len(candidate_ancestors) > len(guard_chain):
        return False
    return all(a is b for a, b in zip(candidate_ancestors, guard_chain))


def _shape_and_single_write_ok(
    x: str,
    param_names: frozenset[str],
    all_stmts: list[tuple[ast.stmt, _StmtChain]],
) -> tuple[dict[str, Any], ast.stmt, _StmtChain] | None:
    """The idiom-shape and BOTH single-write clauses (over ``x`` itself,
    with beta's one preserving exception, and over the term's own
    iterand) -- everything §15.3 requires EXCEPT the guard-relative
    position/scope tests, which only apply when there is a specific guard
    to relate ``x`` to (:func:`compute_local_bindings_for_guard`'s own
    extra checks). Returns ``(binding_dict, first_stmt, first_chain)`` or
    ``None``.
    """
    writes = [(stmt, chain) for stmt, chain in all_stmts if _bare_assign_target(stmt) == x]
    if not writes:
        return None
    writes.sort(key=lambda sc: sc[0].lineno)
    first_stmt, first_chain = writes[0]

    alpha = _match_alpha(first_stmt.value, param_names)  # type: ignore[union-attr]
    idiom: str
    iterand: str
    pred: Predicate | None = None
    default_shape: str | None = None
    if alpha is not None:
        idiom = "alpha"
        iterand, pred = alpha
    else:
        beta = _match_beta(first_stmt.value, x)  # type: ignore[union-attr]
        if beta is None:
            return None  # first write to x matches neither idiom -- no binding.
        idiom = "beta"
        iterand, default_shape = beta

    # Single-write clause over x, with beta's one preserving exception.
    extra_writes = [stmt for stmt, _ in writes[1:]]
    if extra_writes:
        if idiom != "beta" or len(extra_writes) != 1 or not _is_beta_preserving_rebinding(extra_writes[0], x):
            return None

    # Single-write clause over the term's own iterand (alpha's iter name /
    # beta's <p> name) -- symmetric with x's own rule: a SECOND explicit
    # Assign anywhere in K invalidates the binding, but ONE is tolerated,
    # exactly as a plain parameter tolerates its own implicit "binding" by
    # the call plus zero explicit rewrites. Measured, not merely asserted
    # (260904 T30b): `aspirate`'s beta population (`:963`-`:965`) rebinds
    # its own iterand `use_channels` exactly ONCE (`:958`,
    # `use_channels = use_channels or self._default_use_channels or
    # list(range(len(resources)))`) BEFORE any of the three beta
    # assignments that key off it, and AC-15.2's own floor names all three
    # as expected population members -- so "written exactly once" cannot
    # mean "zero explicit rewrites tolerated" (that would silently exclude
    # all three and miss the floor); it means what it says for x itself:
    # ONE write is the binding event, a SECOND is what makes it Opaque.
    if _count_assigns_to_name(all_stmts, iterand) > 1:
        return None

    if idiom == "alpha":
        assert pred is not None
        binding = {"idiom": "alpha", "x": x, "iter": iterand, "pred": predicate_to_json(pred)}
    else:
        assert default_shape is not None
        binding = {"idiom": "beta", "x": x, "param": iterand, "default_shape": default_shape}
    return binding, first_stmt, first_chain


def compute_local_bindings_for_guard(
    K: FunctionNode, predicate: Predicate, guard_lineno: int
) -> tuple[dict[str, Any], ...]:
    """The complete set of bindings this ONE guard's free names resolve to
    (§15.3) -- ``()`` when ``K``'s body has no statement at ``guard_lineno``
    at all (a defensive fail-closed default; should not occur for a
    ``finding.lineno`` that genuinely came from ``K``'s own body) or when no
    free name binds. Deterministic order: sorted by free-var name, so two
    runs over the same source produce byte-identical JSON.

    In ADDITION to the shape/single-write tests (:func:`_shape_and_single_write_ok`),
    this applies the two guard-RELATIVE tests: the binding assignment's
    ``lineno`` must precede the guard's, and it must not sit inside a
    header that does not also contain the guard (including the ``for``
    entry targeting ``x`` case).
    """
    free_names = sorted(free_var_names(predicate))
    if not free_names:
        return ()
    all_stmts = _walk_statements(K.body, [])
    guard_entry = next((entry for entry in all_stmts if entry[0].lineno == guard_lineno), None)
    if guard_entry is None:
        return ()
    _, guard_chain = guard_entry
    param_names = _param_names(K)

    bindings: list[dict[str, Any]] = []
    for x in free_names:
        matched = _shape_and_single_write_ok(x, param_names, all_stmts)
        if matched is None:
            continue
        binding, first_stmt, first_chain = matched

        if not (first_stmt.lineno < guard_lineno):
            continue
        if not _ancestors_are_prefix(first_chain[:-1], guard_chain):
            continue
        shadowed = False
        for ancestor in guard_chain[:-1]:
            if isinstance(ancestor, (ast.For, ast.AsyncFor)) and isinstance(ancestor.target, ast.Name):
                if ancestor.target.id == x:
                    shadowed = True
                    break
        if shadowed:
            continue

        bindings.append(binding)
    return tuple(bindings)


def compute_all_local_bindings(K: FunctionNode) -> tuple[dict[str, Any], ...]:
    """The complete, GUARD-INDEPENDENT catalog of alpha/beta bindings
    anywhere in ``K``'s own body (§15.9 block (2)'s "complete set of (K, x,
    idiom, term) tuples") -- every bare-``Name`` assignment target found
    anywhere in ``K``, filtered through the SAME shape and single-write
    tests :func:`compute_local_bindings_for_guard` uses, but with NO
    guard-relative position/scope check at all.

    This is deliberately wider than any one guard's own ``bindings``
    field: PLR rebinds several names via the identical beta shape in one
    method (``aspirate``'s ``offsets``/``flow_rates``/``liquid_height``/
    ``blow_out_air_volume`` at consecutive lines) but only ONE guard
    currently reads any of them directly -- the rest are read through a
    ``for n, p in [...]`` aliasing loop (the deferred gamma idiom, §15.13),
    so they never appear as a free ``Var`` in any guard's own predicate and
    would be invisible to a guard-scoped search. AC-15.2's own floor (beta
    population exactly 8, naming ``aspirate``'s ``:963``/``:964``/``:965``
    and ``dispense``'s ``:1157``/``:1158``/``:1159`` by line) is a claim
    about THIS catalog, not about ``InlinedGuard.bindings``.
    """
    all_stmts = _walk_statements(K.body, [])
    candidate_names = sorted({name for stmt, _ in all_stmts if (name := _bare_assign_target(stmt)) is not None})
    param_names = _param_names(K)

    bindings: list[dict[str, Any]] = []
    for x in candidate_names:
        matched = _shape_and_single_write_ok(x, param_names, all_stmts)
        if matched is not None:
            bindings.append(matched[0])
    return tuple(bindings)


# ---------------------------------------------------------------------------
# E-UNCOND(5)'s K-body fact (increment 6, spec 260904 §15.4/§15.10 refined,
# T36): `reachability_clear`.
# ---------------------------------------------------------------------------


def compute_reachability_clear(K: FunctionNode, guard_lineno: int) -> bool:
    """The refined E-UNCOND(5) fact for ONE guard, derived from ``K``'s own
    AST at guard-construction time (``derive_contract``'s job, never
    ``check/``'s -- module docstring of ``plr_sema.check`` forbids it PLR
    source access). ``True`` iff ALL THREE hold:

    * ``not has_return_before`` -- no ``ast.Return`` anywhere in ``K``'s
      body (any nesting, reusing :func:`_walk_statements`'s own scope
      boundary -- never descending into a nested ``FunctionDef``/
      ``AsyncFunctionDef``/``Lambda``/``ClassDef``) with ``lineno <
      guard_lineno``;
    * ``not enclosed_by_try_or_with`` -- the guard's OWN statement is not
      lexically inside any ``ast.Try`` (``body``/``handlers``/``orelse``/
      ``finalbody``) or ``ast.With``/``ast.AsyncWith`` within ``K``, tested
      against its own ancestor chain (the same ``_walk_statements`` chain
      :func:`compute_local_bindings_for_guard` uses for its scope-position
      tests);
    * ``not has_break_continue_before`` -- no ``ast.Break``/``ast.Continue``
      with ``lineno < guard_lineno`` ANYWHERE in ``K`` (conservative: not
      scoped to whether the break/continue's own loop actually encloses the
      guard).

    An earlier ``ast.Raise`` does NOT block -- the refined clause (5) is a
    claim about the OPERATION failing, scored by ``oracle_common.compare``
    at the failing call's own index, not about the raise site; an earlier,
    unconditional raise elsewhere in ``K`` has no bearing on whether THIS
    guard's own claim is safe to emit as ``WILL_FAIL``.

    ``False`` (fail-closed, never guessed) when ``guard_lineno`` names no
    statement anywhere in ``K``'s body at all -- defensive, mirroring
    :func:`compute_local_bindings_for_guard`'s identical fallback; should
    not occur for a ``finding.lineno`` that genuinely came from ``K``'s own
    body.
    """
    all_stmts = _walk_statements(K.body, [])
    guard_entry = next((entry for entry in all_stmts if entry[0].lineno == guard_lineno), None)
    if guard_entry is None:
        return False

    _, guard_chain = guard_entry
    ancestors = guard_chain[:-1]
    if any(isinstance(ancestor, (ast.Try, ast.With, ast.AsyncWith)) for ancestor in ancestors):
        return False

    for stmt, _ in all_stmts:
        if stmt.lineno >= guard_lineno:
            continue
        if isinstance(stmt, ast.Return):
            return False
        if isinstance(stmt, (ast.Break, ast.Continue)):
            return False
    return True
