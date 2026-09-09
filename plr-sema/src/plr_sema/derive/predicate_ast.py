"""plr_sema.derive.predicate_ast: the typed predicate mini-AST and its total
parse (increment 6, spec 260904 §15.2, T30a).

**Scope, drawn narrowly on purpose (§15.12's T30/T30a split).** This module
implements ONLY the grammar (G0-G6): a typed sum type over Kleene
three-valued predicates, and ``parse: str | None -> Predicate``, a TOTAL
function with ``Opaque`` as its only escape. It does **no evaluation** --
turning a ``Predicate`` into ``T``/``F``/``½`` against a concrete IR call is
``plr_sema.check.predicate`` (T31, not built yet). It does **no idiom
resolution** -- the local-binding idioms (alpha binds a filtered-comprehension
term to a name at an earlier statement, beta binds a length to an
``or``-chain default, both spec 260904 §15.3) are T30b's job, threading
``scope_trail``/``mentions_params`` context this module never sees. ``parse``
only ever looks at ONE self-contained condition string via
``ast.parse(condition, mode="eval")``.

**G0 -- totality.** ``parse`` never raises. ``parse(None) = TRUE`` (a guard
whose ``condition`` is ``None`` fires unconditionally --
``check/__init__.py``'s pre-existing ``"<unconditional>"`` sentinel encodes
the same fact). A ``SyntaxError`` from ``ast.parse``, or any construction
shape this module's walk does not recognise, yields ``Opaque(text)`` --
never an exception. ``Opaque`` is a constructor of the type, not a failure
mode: an ``Opaque`` predicate still evaluates to ½ under every state (T31's
job) and still carries a `guard_predicate_unparsed` reason -- exactly
today's behaviour for a guard nothing here understands.

**Nested `Opaque` (round 1, C15).** Only ``Predicate``-typed slots can hold
an ``Opaque`` node (there is no ``Term``-side escape -- see the grammar
below); when a ``Term``-typed sub-expression fails to parse, the smallest
ENCLOSING predicate construction collapses to ``Opaque`` instead, so
``Opaque`` never appears where a ``Term`` is expected structurally. This
keeps ``contains_opaque`` (below) a straightforward recursive walk: a
predicate contains an ``Opaque`` iff some reachable ``Predicate``-typed slot
in its tree is one, and it still evaluates under Kleene regardless (T31's
job) -- two independent facts about the same tree.

**The grammar, restated as the node names T31 must agree with**
(spec 260904 §15.2 G1)::

    Predicate ::= TRUE
                | Not(Predicate)
                | And(Predicate, ...)
                | Or(Predicate, ...)
                | Cmp(Term, op, Term)          # op in {==, !=, <, <=, >, >=}
                | Is(Term, negated)            # `x is None` / `x is not None`
                | AllOf(Term, Predicate)       # all(<Predicate> for <v> in <Term>)
                | AnyOf(Term, Predicate)       # any(<Predicate> for <v> in <Term>)
                | IsInstance(Term, (str, ...))
                | Opaque(text)
    Term      ::= Len(Term) | SetOf(Term) | Var(name) | Lit(json) | Attr(Term, name)
                | Filtered(Term, Predicate)    # the comprehension of §15.3(alpha), as a TERM

``AllOf``/``AnyOf``'s first field is typed as a general ``Term`` (not
restricted to a bare ``Var``) because G3 below constructs it by reusing
``Filtered``'s own ``Term``-typed ``seq`` field directly -- the grammar
block's ``Var`` annotation names the common case, not a type constraint.
Neither ``AllOf`` nor ``AnyOf`` records the comprehension's bound name: a
reference to it inside ``predicate`` is parsed as an ordinary free
``Var(name)``, exactly like any other free name -- resolving which names are
loop-bound is downstream (idiom/evaluator) context this module never has.

**G2 -- chained comparisons.** An ``ast.Compare`` with ``n`` operators
becomes ``And`` of ``n`` pairwise ``Cmp``s (or a bare ``Cmp`` when ``n ==
1``); each operand between two ``ast.Compare`` slots is parsed to a
``Term`` exactly once and reused for both adjacent pairs.

**G3 -- the emptiness-of-a-filtered-comprehension idiom.** ``len(<x>) <cmp>
<int>`` where ``<x>`` parses to ``Filtered(seq, pred)`` is rewritten:
``> 0`` / ``>= 1`` become ``AnyOf(seq, pred)``; ``== 0`` / ``!= 0`` become
``Not(AnyOf(seq, pred))``. Every other numeric relation over a ``Filtered``
term is ``Opaque`` -- a count is not an emptiness test. This is symmetric
under operand order (``0 < len(<x>)`` is the same rewrite as ``len(<x>) >
0``).

**G4 -- ``set(P)`` uniqueness -- an EVALUATION rule, not a parse-time one.**
``len(set(x)) == len(x)`` parses as an entirely ordinary
``Cmp(Len(SetOf(Var("x"))), "==", Len(Var("x")))`` -- no special-casing is
needed at parse time, because ``Len``/``SetOf``/``Cmp`` are already ordinary
grammar productions. G4's uniqueness semantics belong to T31's evaluator.

**G5 -- numeric atoms stay representable, folding is the evaluator's
business.** A ``Cmp`` whose operands are plain numeric terms parses exactly
like any other ``Cmp``; whether it folds to ½ (the general rule) or reads
the volume interval domain (increment 5's one exception) is T31's decision,
not this module's.

**G6 -- polarity from ``kind``, never from the text.** ``InlinedGuard.kind``
(``"raise_guard"`` fires on ``T``, ``"assert"`` fires on ``F``) is carried on
the guard, not on the ``Predicate`` -- this module parses the SAME condition
string identically regardless of ``kind``.

**Wire encoding.** ``to_json``/``from_json`` give a stable, JSON-safe
round-trip: every node becomes ``{"node": <class name>, ...fields}``, never a
Python ``repr()`` string. This is independent of ``InlinedGuard``'s own JSON
shape (``derive/__main__.py``'s ``_guard_to_json``), which calls ``to_json``
on the ``predicate`` field it adds.

**G7/G8 -- the 260907 amendment (spec 260904 S15.2, T35).** Three additive
productions, all this module's business except the PLR-layer index test
(below): ``EnvRef(path, args)`` -- a self-rooted attribute chain
(``args is None``) or the call of one (``args`` a tuple, possibly empty),
admissible in BOTH ``Predicate`` and ``Term`` position -- the one node
inhabiting both unions, a deliberate one-element overlap in the otherwise
disjoint partition; ``Zip(items)`` -- ``zip(<e1>, ..., <en>)``, ``n >= 2``,
admissible ONLY as the ``seq`` of ``AllOf``/``AnyOf``; and the membership
comparators ``in``/``not in`` added to ``Cmp``'s op set. All three are
purely SYNTACTIC here -- evaluating them (E-ENV: 1/2 in predicate position,
TOP in term position, unconditionally, this increment) is T31's job.

**The PLR-layer test on a shape-(2) `self.<name>(...)` call with
``len(path) == 2`` is NOT this module's job.** ``parse`` sees one
self-contained condition string and no context (no receiver class, no
function index), so it admits EVERY syntactically-valid self-rooted call as
an ``EnvRef`` candidate. The index-gated refusal -- demoting a `self.<name>`
call to `Opaque` when `<name>` IS an indexed PLR-layer method of the
receiver class -- is applied POST-parse, in `plr_sema.derive.bindings`,
against `receiver_state.build_plr_function_index` (spec 260904 S15.2's
normative box, round 2 A-C1).

**The `Var("self")` invariant IS this module's job**, because it needs no
external context: after the amendment, no parsed predicate may contain a
bare `Var` node named `"self"` -- `self` is meaningful ONLY as the root of
an `EnvRef` path. `_parse_term` therefore refuses a bare `ast.Name("self")`
unconditionally (returns `None`, an ordinary term-parse failure that
propagates via the existing totality machinery to `Opaque` at the smallest
enclosing predicate construction) -- self-rooted attribute/call chains are
intercepted BEFORE reaching that branch, via `_self_rooted_path`, so a
legitimate `self.<x>` never touches it.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Union

__all__ = [
    # Predicate nodes
    "TRUE",
    "Not",
    "And",
    "Or",
    "Cmp",
    "Is",
    "AllOf",
    "AnyOf",
    "IsInstance",
    "Opaque",
    "EnvRef",
    # Term nodes
    "Len",
    "SetOf",
    "Var",
    "Lit",
    "Attr",
    "Filtered",
    "Zip",
    # type aliases
    "Predicate",
    "Term",
    # API
    "parse",
    "walk",
    "contains_opaque",
    "contains_env_ref",
    "count_env_ref_nodes",
    "count_var_self",
    "to_json",
    "from_json",
    "MEMBERSHIP_OPS",
]


# ---------------------------------------------------------------------------
# Term nodes (§15.2 G1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Var:
    """A free name -- a kwarg, a local, an attribute base. Resolving it
    against a call's actual operands is the evaluator's job (T31); this
    module only records the name."""

    name: str


@dataclass(frozen=True, slots=True)
class Lit:
    """A JSON-safe literal: ``None``, ``bool``, ``int``, ``float``, or
    ``str``. Never a Python ``repr()`` string -- see ``to_json``."""

    value: bool | int | float | str | None


@dataclass(frozen=True, slots=True)
class Len:
    """``len(<term>)``."""

    term: "Term"


@dataclass(frozen=True, slots=True)
class SetOf:
    """``set(<term>)`` -- read as an operator on a resolved sequence (G4),
    never as a Python value at parse time."""

    term: "Term"


@dataclass(frozen=True, slots=True)
class Attr:
    """``<term>.<name>``."""

    term: "Term"
    name: str


@dataclass(frozen=True, slots=True)
class Filtered:
    """The term §15.3(alpha) binds, when it appears INLINE in one
    self-contained condition: ``[<v> for <v> in <seq> if <pred>]`` where the
    comprehension's ``elt`` is the identity map of its own loop variable
    (PLR's "reject the wrongly-typed elements" shape,
    ``not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, TipSpot)]``).
    ``predicate`` is the parsed ``if`` clause -- itself free to be ``Opaque``
    (the nested-``Opaque`` rule, C15) while ``seq`` stays a genuine
    ``Term``."""

    seq: "Term"
    predicate: "Predicate"


@dataclass(frozen=True, slots=True)
class Zip:
    """G8 (260907 amendment, T35): ``zip(<e1>, ..., <en>)``, ``n >= 2`` --
    admissible ONLY as the ``seq`` of ``AllOf``/``AnyOf`` (constructed only
    by the quantifier parser, never by the general ``_parse_term``
    dispatch, so a ``zip(...)`` anywhere else -- under ``Len``, as a bare
    ``Cmp`` operand -- is simply unrecognised and collapses its enclosing
    predicate to ``Opaque``, exactly like any other unsupported shape).
    Resolves to TOP unless every item resolves to a concrete ``Seq``
    (S15.4 E-ENV, T31's job). The comprehension target's bound names are
    never recorded as a field here -- same rationale as ``AllOf``/``AnyOf``
    not recording their own bound name."""

    items: tuple["Term", ...]


@dataclass(frozen=True, slots=True)
class EnvRef:
    """G7 (260907 amendment, T35): an expression rooted at the literal name
    ``self`` -- an attribute chain (``args is None``, e.g. ``self.head`` ->
    ``EnvRef(("self", "head"), None)``) or the CALL of such a chain whose
    arguments all parse as ``Term``s (``args`` a tuple, possibly empty --
    that is what distinguishes a zero-argument call from a bare read).
    Admissible in BOTH ``Predicate`` and ``Term`` position -- the one node
    inhabiting both unions (a deliberate one-element overlap; round 2,
    A-C12). This module constructs the SYNTACTIC candidate only: the
    PLR-layer index test on a shape-(2) call with ``len(path) == 2`` (does
    ``<name>`` name an indexed PLR-layer method of the receiver class?) is
    applied post-parse, in ``plr_sema.derive.bindings``, against
    ``receiver_state.build_plr_function_index`` -- this module has no
    access to that context and never guesses it. Evaluates to 1/2 in
    predicate position and TOP in term position, unconditionally, this
    increment (S15.4 E-ENV, T31's job)."""

    path: tuple[str, ...]
    args: tuple["Term", ...] | None


Term = Union[Len, SetOf, Var, Lit, Attr, Filtered, Zip, EnvRef]


# ---------------------------------------------------------------------------
# Predicate nodes (§15.2 G1)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TRUE:
    """The unconditional predicate. ``parse(None) = TRUE()`` -- a statement
    about the PREDICATE only, never a reachability claim (§15.2's normative
    box); E-UNCOND still gates whether a ``TRUE`` guard may emit
    ``WILL_FAIL`` (T31)."""


@dataclass(frozen=True, slots=True)
class Opaque:
    """The only escape from totality. ``text`` is ``ast.unparse`` of the
    smallest sub-expression this module's walk could not classify -- the
    whole condition at the top level, or one operand/clause when the rest of
    an enclosing ``And``/``Or``/``Not``/``Filtered``/``AllOf``/``AnyOf``
    parsed fine (the nested-``Opaque`` rule, C15)."""

    text: str


@dataclass(frozen=True, slots=True)
class Not:
    predicate: "Predicate"


@dataclass(frozen=True, slots=True)
class And:
    """Kleene: ``F`` if any conjunct is ``F``, ``T`` if all are ``T``, else
    ``½`` -- evaluation is T31's job; this node is purely structural."""

    predicates: tuple["Predicate", ...]


@dataclass(frozen=True, slots=True)
class Or:
    """Kleene dual of ``And``."""

    predicates: tuple["Predicate", ...]


@dataclass(frozen=True, slots=True)
class Cmp:
    """``op in {"==", "!=", "<", "<=", ">", ">="}``."""

    left: "Term"
    op: str
    right: "Term"


@dataclass(frozen=True, slots=True)
class Is:
    """``<term> is None`` (``negated=False``) / ``<term> is not None``
    (``negated=True``). The RHS must be the literal constant ``None`` --
    anything else is not this production (§15.2 G1)."""

    term: "Term"
    negated: bool


@dataclass(frozen=True, slots=True)
class IsInstance:
    """``isinstance(<term>, <type>)`` / ``isinstance(<term>, (<type>, ...))``.
    ``types`` are bare (possibly dotted) type names, never resolved classes
    -- E-TYPE's exact-vs-hierarchy decision is T31's job."""

    term: "Term"
    types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AllOf:
    """``all(<predicate> for <v> in <seq>)`` -- universal quantification
    over ``seq``. See the module docstring for why ``seq`` is typed as a
    general ``Term``, and why the bound name ``<v>`` is not itself a
    field."""

    seq: "Term"
    predicate: "Predicate"


@dataclass(frozen=True, slots=True)
class AnyOf:
    """``any(<predicate> for <v> in <seq>)`` -- existential dual of
    ``AllOf``. Also G3's rewrite target for ``len(Filtered(seq, pred)) > 0``."""

    seq: "Term"
    predicate: "Predicate"


Predicate = Union[TRUE, Not, And, Or, Cmp, Is, AllOf, AnyOf, IsInstance, Opaque, EnvRef]


# ---------------------------------------------------------------------------
# parse: str | None -> Predicate (G0, total)
# ---------------------------------------------------------------------------

_CMP_OPS: dict[type[ast.cmpop], str] = {
    ast.Eq: "==",
    ast.NotEq: "!=",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    # G8(2), 260907 amendment: membership comparators. Every membership
    # `Cmp` evaluates 1/2 unconditionally this increment (S15.4 E-ENV) --
    # that is T31's business, not this module's; parsing them is purely
    # representational, exactly like every other Cmp op.
    ast.In: "in",
    ast.NotIn: "not in",
}

#: G8(2)'s op set -- the two ops that are never a decidable Cmp this
#: increment (S15.4 E-ENV: "every membership Cmp evaluates 1/2
#: unconditionally"). Not consulted by this module (parsing is polarity/
#: value agnostic); published for T31/t30_measure's convenience so neither
#: has to hand-type the pair a second time.
MEMBERSHIP_OPS = frozenset({"in", "not in"})

# G3: op/int-literal combos over a Filtered term that ARE an emptiness test.
_ANY_OF_COMBOS = frozenset({(">", 0), (">=", 1)})
_NOT_ANY_OF_COMBOS = frozenset({("==", 0), ("!=", 0)})

_FLIP_OP = {
    "==": "==",
    "!=": "!=",
    "<": ">",
    "<=": ">=",
    ">": "<",
    ">=": "<=",
}


def parse(condition: str | None) -> Predicate:
    """Total: ``parse(None) = TRUE()``; a ``SyntaxError`` or any internal
    surprise degrades to ``Opaque(condition)`` rather than raising (G0)."""
    if condition is None:
        return TRUE()
    try:
        tree = ast.parse(condition, mode="eval")
    except (SyntaxError, ValueError):
        return Opaque(condition)
    try:
        return _parse_predicate(tree.body)
    except Exception:  # noqa: BLE001 -- G0's totality is absolute.
        return Opaque(condition)


def _unparse(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except Exception:  # noqa: BLE001 -- text is best-effort, never load-bearing.
        return "<unparseable>"


def _pair_text(left: ast.expr, op: ast.cmpop, right: ast.expr) -> str:
    return _unparse(ast.Compare(left=left, ops=[op], comparators=[right]))


# ---- Predicate-position dispatch ------------------------------------------


def _parse_predicate(node: ast.expr) -> Predicate:
    if isinstance(node, ast.Compare):
        return _parse_compare(node)
    if isinstance(node, ast.BoolOp):
        parts = tuple(_parse_predicate(v) for v in node.values)
        return And(parts) if isinstance(node.op, ast.And) else Or(parts)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return Not(_parse_predicate(node.operand))
    if isinstance(node, ast.Call):
        result = _parse_call_predicate(node)
        if result is not None:
            return result
    if isinstance(node, ast.Attribute):
        # G7 shape (1) used bare, in predicate position -- e.g.
        # `self.setup_finished` as a standalone truthiness test.
        self_path = _self_rooted_path(node)
        if self_path is not None:
            return EnvRef(self_path, None)
    return Opaque(_unparse(node))


def _self_rooted_path(node: ast.expr) -> tuple[str, ...] | None:
    """G7's shape test: the attribute-chain path if ``node`` is a chain of
    plain ``ast.Attribute``s bottoming out at ``ast.Name("self")`` -- e.g.
    ``self.head`` -> ``("self", "head")``; ``self._resource_pickup.direction``
    -> ``("self", "_resource_pickup", "direction")``. ``None`` for anything
    else: a non-``self`` base, or a ``Subscript``/``Call`` anywhere in the
    chain (the closed negative list: subscripted ``self`` stays ``Opaque``
    because the chain simply never reaches ``ast.Name("self")`` through
    pure ``Attribute`` hops alone)."""
    parts: list[str] = []
    cur: ast.expr = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name) and cur.id == "self":
        parts.reverse()
        return ("self", *parts)
    return None


def _parse_env_ref_call(node: ast.Call) -> "EnvRef | None":
    """G7 shape (2)'s SYNTACTIC half only (no PLR-layer index test here --
    see the module docstring). Admits ``self.<attr>...(...)``: no
    ``keywords``, no ``Starred``, every argument parses as a ``Term``. A
    bare ``self`` as an argument already fails via ``_parse_term``'s own
    refusal of a standalone ``Name("self")`` (the ``Var("self")``
    invariant), so no separate check is needed here."""
    path = _self_rooted_path(node.func)
    if path is None or len(path) < 2:
        return None
    if node.keywords:
        return None
    if any(isinstance(a, ast.Starred) for a in node.args):
        return None
    args: list[Term] = []
    for a in node.args:
        t = _parse_term(a)
        if t is None:
            return None
        args.append(t)
    return EnvRef(path=path, args=tuple(args))


def _parse_call_predicate(node: ast.Call) -> Predicate | None:
    env_ref = _parse_env_ref_call(node)
    if env_ref is not None:
        return env_ref
    if not isinstance(node.func, ast.Name):
        return None
    name = node.func.id
    if name == "isinstance":
        return _parse_isinstance(node)
    if name in ("all", "any"):
        return _parse_quantifier(node, name)
    return None


def _parse_isinstance(node: ast.Call) -> Predicate:
    if len(node.args) != 2 or node.keywords:
        return Opaque(_unparse(node))
    term = _parse_term(node.args[0])
    types = _parse_isinstance_types(node.args[1])
    if term is None or types is None or not types:
        return Opaque(_unparse(node))
    return IsInstance(term=term, types=types)


def _type_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _type_name(node.value)
        return None if base is None else f"{base}.{node.attr}"
    return None


def _parse_isinstance_types(node: ast.expr) -> tuple[str, ...] | None:
    if isinstance(node, ast.Tuple):
        names: list[str] = []
        for elt in node.elts:
            name = _type_name(elt)
            if name is None:
                return None
            names.append(name)
        return tuple(names)
    name = _type_name(node)
    return None if name is None else (name,)


def _parse_zip(node: ast.expr) -> "Zip | None":
    """G8(1): ``zip(<e1>, ..., <en>)``, ``n >= 2``, no ``keywords``, no
    ``Starred``, every item parsing as a ``Term``. Constructed ONLY here --
    never by the general ``_parse_term`` dispatch -- so a ``zip(...)``
    anywhere else in a condition (under ``Len``, as a bare ``Cmp`` operand)
    is simply an unrecognised ``ast.Call`` and collapses its enclosing
    predicate to ``Opaque`` via the ordinary term-parse-failure path."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "zip"):
        return None
    if node.keywords or len(node.args) < 2:
        return None
    if any(isinstance(a, ast.Starred) for a in node.args):
        return None
    items: list[Term] = []
    for a in node.args:
        t = _parse_term(a)
        if t is None:
            return None
        items.append(t)
    return Zip(tuple(items))


def _tuple_target_matches(target: ast.expr, n: int) -> bool:
    """G8(1)'s tuple-target correspondence: every element a bare
    ``ast.Name``, arity exactly ``n`` -- else the whole quantifier is
    ``Opaque`` (no partial admission)."""
    return isinstance(target, ast.Tuple) and len(target.elts) == n and all(isinstance(e, ast.Name) for e in target.elts)


def _parse_quantifier(node: ast.Call, kind: str) -> Predicate:
    if len(node.args) != 1 or node.keywords:
        return Opaque(_unparse(node))
    arg = node.args[0]
    if not isinstance(arg, ast.GeneratorExp) or len(arg.generators) != 1:
        return Opaque(_unparse(node))
    comp = arg.generators[0]
    if comp.ifs or comp.is_async:
        return Opaque(_unparse(node))
    zip_seq = _parse_zip(comp.iter)
    seq: "Term | None"
    if zip_seq is not None:
        # G8(1): a Zip iterand REQUIRES a matching tuple target -- the
        # positional correspondence `target[i] <-> items[i]` is what makes
        # the Zip readable at all; anything else is Opaque, no partial
        # admission (round 2, A-C13's comprehension-bound-name rule is
        # about what the names RESOLVE to, T31's job -- this is only the
        # syntactic gate on whether the Zip is admitted at all).
        seq = zip_seq if _tuple_target_matches(comp.target, len(zip_seq.items)) else None
    else:
        seq = _parse_term(comp.iter)
    if seq is None:
        return Opaque(_unparse(node))
    body = _parse_predicate(arg.elt)
    return AllOf(seq=seq, predicate=body) if kind == "all" else AnyOf(seq=seq, predicate=body)


def _parse_compare(node: ast.Compare) -> Predicate:
    operands_ast = [node.left, *node.comparators]
    # Each operand parsed to a Term exactly once (G2) -- reused across both
    # adjacent pairs a middle operand participates in.
    terms = [_parse_term(o) for o in operands_ast]
    parts: list[Predicate] = []
    for i, op_node in enumerate(node.ops):
        parts.append(
            _parse_one_cmp(
                op_node,
                operands_ast[i],
                terms[i],
                operands_ast[i + 1],
                terms[i + 1],
            )
        )
    return parts[0] if len(parts) == 1 else And(tuple(parts))


def _parse_one_cmp(
    op_node: ast.cmpop,
    left_ast: ast.expr,
    left_term: "Term | None",
    right_ast: ast.expr,
    right_term: "Term | None",
) -> Predicate:
    if isinstance(op_node, (ast.Is, ast.IsNot)):
        if left_term is not None and isinstance(right_term, Lit) and right_term.value is None:
            return Is(term=left_term, negated=isinstance(op_node, ast.IsNot))
        return Opaque(_pair_text(left_ast, op_node, right_ast))

    op_symbol = _CMP_OPS.get(type(op_node))
    if op_symbol is None:
        return Opaque(_pair_text(left_ast, op_node, right_ast))
    if left_term is None or right_term is None:
        return Opaque(_pair_text(left_ast, op_node, right_ast))

    special = _maybe_filtered_emptiness(left_term, op_symbol, right_term)
    if special is not None:
        return special
    return Cmp(left_term, op_symbol, right_term)


def _is_int_count(term: "Term") -> bool:
    return isinstance(term, Lit) and isinstance(term.value, int) and not isinstance(term.value, bool)


def _maybe_filtered_emptiness(left: "Term", op: str, right: "Term") -> Predicate | None:
    """G3. Returns ``None`` when neither operand is ``Len(Filtered(...))``
    (not this idiom at all -- fall through to an ordinary ``Cmp``);
    otherwise ALWAYS returns a ``Predicate`` (``AnyOf``, ``Not(AnyOf(...))``,
    or ``Opaque`` for an unrecognised numeric relation over a ``Filtered``
    term -- a count is not an emptiness test)."""
    if isinstance(left, Len) and isinstance(left.term, Filtered) and _is_int_count(right):
        filtered = left.term
        n = right.value
        eff_op = op
    elif isinstance(right, Len) and isinstance(right.term, Filtered) and _is_int_count(left):
        filtered = right.term
        n = left.value
        eff_op = _FLIP_OP[op]
    else:
        return None

    combo = (eff_op, n)
    if combo in _ANY_OF_COMBOS:
        return AnyOf(seq=filtered.seq, predicate=filtered.predicate)
    if combo in _NOT_ANY_OF_COMBOS:
        return Not(AnyOf(seq=filtered.seq, predicate=filtered.predicate))
    return Opaque(f"len({_unparse_term_text(filtered)}) {op} {n!r}")


def _unparse_term_text(term: "Term") -> str:
    """Best-effort text for a Term that only ever appears inside a
    synthesized ``Opaque`` message (G3's unsupported-relation case) -- never
    fed back through ``from_json``, so approximate is fine."""
    if isinstance(term, Var):
        return term.name
    if isinstance(term, Lit):
        return repr(term.value)
    if isinstance(term, Len):
        return f"len({_unparse_term_text(term.term)})"
    if isinstance(term, SetOf):
        return f"set({_unparse_term_text(term.term)})"
    if isinstance(term, Attr):
        return f"{_unparse_term_text(term.term)}.{term.name}"
    if isinstance(term, Filtered):
        return f"[... for ... in {_unparse_term_text(term.seq)} if ...]"
    return "<term>"


# ---- Term-position dispatch ------------------------------------------------


def _parse_term(node: ast.expr) -> "Term | None":
    if isinstance(node, ast.Constant):
        value = node.value
        if value is None or isinstance(value, (bool, int, float, str)):
            return Lit(value)
        return None
    if isinstance(node, ast.Name):
        if node.id == "self":
            # The Var("self") invariant (S15.2's normative box): bare
            # `self` is meaningful ONLY as the root of an EnvRef path, and
            # every legitimate self-rooted chain/call is intercepted BEFORE
            # reaching this branch (the Attribute/Call cases below try
            # `_self_rooted_path` first). An ordinary term-parse failure --
            # propagates via the existing totality machinery to `Opaque` at
            # the smallest enclosing predicate construction, exactly like
            # any other unrecognised term.
            return None
        return Var(node.id)
    if isinstance(node, ast.Attribute):
        self_path = _self_rooted_path(node)
        if self_path is not None:
            return EnvRef(self_path, None)
        base = _parse_term(node.value)
        return None if base is None else Attr(base, node.attr)
    if isinstance(node, ast.Call):
        env_ref = _parse_env_ref_call(node)
        if env_ref is not None:
            return env_ref
        if isinstance(node.func, ast.Name) and not node.keywords:
            if node.func.id == "len" and len(node.args) == 1:
                inner = _parse_term(node.args[0])
                return None if inner is None else Len(inner)
            if node.func.id == "set" and len(node.args) == 1:
                inner = _parse_term(node.args[0])
                return None if inner is None else SetOf(inner)
        return None
    if isinstance(node, ast.ListComp):
        return _parse_filtered(node)
    return None


def _parse_filtered(node: ast.ListComp) -> "Term | None":
    if len(node.generators) != 1:
        return None
    comp = node.generators[0]
    if comp.is_async or len(comp.ifs) != 1:
        return None
    if not (isinstance(node.elt, ast.Name) and isinstance(comp.target, ast.Name) and node.elt.id == comp.target.id):
        # G3's shape is the identity map -- `[ts for ts in tip_spots if
        # <pred>]`, never a projection. A projecting comprehension does not
        # match this production; it is a Term-parse failure, which the
        # caller turns into Opaque at the nearest enclosing Predicate.
        return None
    seq = _parse_term(comp.iter)
    if seq is None:
        return None
    predicate = _parse_predicate(comp.ifs[0])
    return Filtered(seq=seq, predicate=predicate)


# ---------------------------------------------------------------------------
# contains_opaque -- §15.7's nested-Opaque rule (C15)
# ---------------------------------------------------------------------------


def contains_opaque(node: "Predicate | Term") -> bool:
    """``True`` iff some reachable ``Predicate``-typed slot in ``node`` is an
    ``Opaque`` node. A predicate for which this is ``True`` keeps
    ``guard_predicate_unparsed`` for reason-assignment purposes even though
    it still evaluates under Kleene (T31's job, not this function's)."""
    if isinstance(node, Opaque):
        return True
    if isinstance(node, (TRUE, Var, Lit)):
        return False
    if isinstance(node, Not):
        return contains_opaque(node.predicate)
    if isinstance(node, (And, Or)):
        return any(contains_opaque(p) for p in node.predicates)
    if isinstance(node, Cmp):
        return contains_opaque(node.left) or contains_opaque(node.right)
    if isinstance(node, Is):
        return contains_opaque(node.term)
    if isinstance(node, IsInstance):
        return contains_opaque(node.term)
    if isinstance(node, (AllOf, AnyOf)):
        return contains_opaque(node.seq) or contains_opaque(node.predicate)
    if isinstance(node, (Len, SetOf)):
        return contains_opaque(node.term)
    if isinstance(node, Attr):
        return contains_opaque(node.term)
    if isinstance(node, Filtered):
        return contains_opaque(node.seq) or contains_opaque(node.predicate)
    if isinstance(node, (Zip, EnvRef)):
        # Neither can hold an Opaque sub-node: every Zip item and every
        # EnvRef arg is a Term that, on parse failure, causes the WHOLE
        # Zip/EnvRef construction to be rejected (returning None up to the
        # caller) rather than embedding a partial/Opaque child -- "no
        # partial admission and no fallback" (S15.2 G7/G8).
        return False
    raise TypeError(f"contains_opaque: unrecognized node type {type(node)!r}")


def contains_env_ref(node: "Predicate | Term") -> bool:
    """``True`` iff some reachable ``Predicate``- or ``Term``-typed slot in
    ``node`` is an ``EnvRef`` node -- the total sibling of ``contains_opaque``
    §15.7's reason rule reads (round 2, A-C4: BOTH walks range over the
    alpha/beta-SUBSTITUTED tree, never the raw ``predicate`` field --
    :func:`plr_sema.derive.bindings.substitute` builds that tree)."""
    if isinstance(node, EnvRef):
        return True
    if isinstance(node, (TRUE, Opaque, Var, Lit)):
        return False
    if isinstance(node, Not):
        return contains_env_ref(node.predicate)
    if isinstance(node, (And, Or)):
        return any(contains_env_ref(p) for p in node.predicates)
    if isinstance(node, Cmp):
        return contains_env_ref(node.left) or contains_env_ref(node.right)
    if isinstance(node, Is):
        return contains_env_ref(node.term)
    if isinstance(node, IsInstance):
        return contains_env_ref(node.term)
    if isinstance(node, (AllOf, AnyOf)):
        return contains_env_ref(node.seq) or contains_env_ref(node.predicate)
    if isinstance(node, (Len, SetOf)):
        return contains_env_ref(node.term)
    if isinstance(node, Attr):
        return contains_env_ref(node.term)
    if isinstance(node, Filtered):
        return contains_env_ref(node.seq) or contains_env_ref(node.predicate)
    if isinstance(node, Zip):
        return any(contains_env_ref(i) for i in node.items)
    raise TypeError(f"contains_env_ref: unrecognized node type {type(node)!r}")


def walk(node: "Predicate | Term") -> "list[Predicate | Term]":
    """Every node reachable from ``node``, ``node`` itself included --
    the general-purpose traversal §15.9 block (6)'s whole-table counts
    (``n_zip``, ``n_membership_cmp``, ``n_env_ref_nodes``, ``n_var_self``)
    are built from, so each of those is a one-line filter over ONE
    recursion rather than a fourth hand-written walk."""
    out: list["Predicate | Term"] = [node]
    if isinstance(node, (TRUE, Opaque, Var, Lit)):
        pass
    elif isinstance(node, Not):
        out.extend(walk(node.predicate))
    elif isinstance(node, (And, Or)):
        for p in node.predicates:
            out.extend(walk(p))
    elif isinstance(node, Cmp):
        out.extend(walk(node.left))
        out.extend(walk(node.right))
    elif isinstance(node, Is):
        out.extend(walk(node.term))
    elif isinstance(node, IsInstance):
        out.extend(walk(node.term))
    elif isinstance(node, (AllOf, AnyOf)):
        out.extend(walk(node.seq))
        out.extend(walk(node.predicate))
    elif isinstance(node, (Len, SetOf, Attr)):
        out.extend(walk(node.term))
    elif isinstance(node, Filtered):
        out.extend(walk(node.seq))
        out.extend(walk(node.predicate))
    elif isinstance(node, Zip):
        for i in node.items:
            out.extend(walk(i))
    elif isinstance(node, EnvRef):
        if node.args is not None:
            for a in node.args:
                out.extend(walk(a))
    else:
        raise TypeError(f"walk: unrecognized node type {type(node)!r}")
    return out


def count_env_ref_nodes(node: "Predicate | Term") -> int:
    """The number of ``EnvRef`` NODES reachable from ``node`` -- block (3)'s
    ``n_env_ref_nodes``, a NODE count (e.g. two for one guard containing
    ``self.a and self.b``), never a per-guard boolean (that is
    :func:`contains_env_ref`) nor the per-guard-COUNT block (4) publishes
    under the SAME name in a different unit (round 2, A-C8's own point --
    the two are deliberately different functions with different names)."""
    return sum(1 for n in walk(node) if isinstance(n, EnvRef))


def count_var_self(node: "Predicate | Term") -> int:
    """The number of ``Var("self")`` occurrences reachable from ``node`` --
    always 0 by construction on anything this module's own ``parse``
    produced (the ``Var("self")`` invariant is enforced AT parse time, in
    ``_parse_term``'s refusal of a bare ``ast.Name("self")``); published as
    a measured whole-table count rather than merely asserted true by
    reading the code (S15.9 block (6), ``n_var_self``)."""
    return sum(1 for n in walk(node) if isinstance(n, Var) and n.name == "self")


# ---------------------------------------------------------------------------
# Stable JSON encoding -- round-trippable, no Python repr() strings.
# ---------------------------------------------------------------------------


def to_json(node: "Predicate | Term") -> dict[str, Any]:
    if isinstance(node, TRUE):
        return {"node": "TRUE"}
    if isinstance(node, Opaque):
        return {"node": "Opaque", "text": node.text}
    if isinstance(node, Not):
        return {"node": "Not", "predicate": to_json(node.predicate)}
    if isinstance(node, And):
        return {"node": "And", "predicates": [to_json(p) for p in node.predicates]}
    if isinstance(node, Or):
        return {"node": "Or", "predicates": [to_json(p) for p in node.predicates]}
    if isinstance(node, Cmp):
        return {"node": "Cmp", "left": to_json(node.left), "op": node.op, "right": to_json(node.right)}
    if isinstance(node, Is):
        return {"node": "Is", "term": to_json(node.term), "negated": node.negated}
    if isinstance(node, IsInstance):
        return {"node": "IsInstance", "term": to_json(node.term), "types": list(node.types)}
    if isinstance(node, AllOf):
        return {"node": "AllOf", "seq": to_json(node.seq), "predicate": to_json(node.predicate)}
    if isinstance(node, AnyOf):
        return {"node": "AnyOf", "seq": to_json(node.seq), "predicate": to_json(node.predicate)}
    if isinstance(node, Len):
        return {"node": "Len", "term": to_json(node.term)}
    if isinstance(node, SetOf):
        return {"node": "SetOf", "term": to_json(node.term)}
    if isinstance(node, Var):
        return {"node": "Var", "name": node.name}
    if isinstance(node, Lit):
        return {"node": "Lit", "value": node.value}
    if isinstance(node, Attr):
        return {"node": "Attr", "term": to_json(node.term), "name": node.name}
    if isinstance(node, Filtered):
        return {"node": "Filtered", "seq": to_json(node.seq), "predicate": to_json(node.predicate)}
    if isinstance(node, Zip):
        return {"node": "Zip", "items": [to_json(i) for i in node.items]}
    if isinstance(node, EnvRef):
        return {
            "node": "EnvRef",
            "path": list(node.path),
            "args": None if node.args is None else [to_json(a) for a in node.args],
        }
    raise TypeError(f"to_json: unrecognized predicate/term node type {type(node)!r}")


_TERM_KINDS = {"Len", "SetOf", "Var", "Lit", "Attr", "Filtered", "Zip", "EnvRef"}
#: EnvRef is deliberately in BOTH sets -- the one node inhabiting both
#: `Term` and `Predicate` (round 2, A-C12: a break of the previously
#: disjoint partition, recorded so it is not discovered as a surprise).
_PREDICATE_KINDS = {"TRUE", "Opaque", "Not", "And", "Or", "Cmp", "Is", "AllOf", "AnyOf", "IsInstance", "EnvRef"}


def from_json(data: dict[str, Any]) -> "Predicate | Term":
    """Inverse of ``to_json``. Raises ``ValueError`` on an unrecognized
    ``"node"`` tag -- unlike ``parse``, this is not a totality boundary: the
    input is our own emitted JSON, not untrusted PLR source, so a malformed
    record is a real bug to surface, not a shape to degrade."""
    kind = data.get("node")
    if kind == "TRUE":
        return TRUE()
    if kind == "Opaque":
        return Opaque(data["text"])
    if kind == "Not":
        return Not(from_json(data["predicate"]))
    if kind == "And":
        return And(tuple(from_json(p) for p in data["predicates"]))
    if kind == "Or":
        return Or(tuple(from_json(p) for p in data["predicates"]))
    if kind == "Cmp":
        return Cmp(from_json(data["left"]), data["op"], from_json(data["right"]))
    if kind == "Is":
        return Is(from_json(data["term"]), data["negated"])
    if kind == "IsInstance":
        return IsInstance(from_json(data["term"]), tuple(data["types"]))
    if kind == "AllOf":
        return AllOf(from_json(data["seq"]), from_json(data["predicate"]))
    if kind == "AnyOf":
        return AnyOf(from_json(data["seq"]), from_json(data["predicate"]))
    if kind == "Len":
        return Len(from_json(data["term"]))
    if kind == "SetOf":
        return SetOf(from_json(data["term"]))
    if kind == "Var":
        return Var(data["name"])
    if kind == "Lit":
        return Lit(data["value"])
    if kind == "Attr":
        return Attr(from_json(data["term"]), data["name"])
    if kind == "Filtered":
        return Filtered(from_json(data["seq"]), from_json(data["predicate"]))
    if kind == "Zip":
        return Zip(tuple(from_json(i) for i in data["items"]))
    if kind == "EnvRef":
        args_json = data.get("args")
        args = None if args_json is None else tuple(from_json(a) for a in args_json)
        return EnvRef(tuple(data["path"]), args)
    raise ValueError(f"from_json: unrecognized node kind {kind!r} in {data!r}")
