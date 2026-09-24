"""plr_sema.derive.receiver_state: the four build-time passes for per-channel
tip typestate (spec 260902 §10.2, `260902_plr-sema-tip-typestate-increment.md`).

**What this module computes, and why it is a second, independent AST pass
(mirrors `scan_dropped_receiver_calls`'s own independence argument, §7.4).**
Everything `plr_sema.check.tipstate` needs at check time is DERIVED here,
by inspection of PLR source (P1-P3) and of the whole-survey index's own
records (P2's `state_fields`, the bridge scan) -- no PLR class name, method
name, field name or exception name is hand-typed anywhere in this file or
in `plr_sema.check.tipstate` (AC-10.9's AST literal scan enforces the
`check/`-side half of that claim; this module is `derive/`, which is
already permitted to import `ast` and read PLR source, §6.2/§7).

Four passes, matching the spec section numbers:

* **P1** (§10.2.1) -- ``_annotated_attributes``/``_attribute_writers``: a
  stdlib-``ast`` pass over every PLR class body finding ``self.<name>:
  <annotation>`` (unwrapped through ``Dict``/``List``/``Optional`` to a bare
  class name) and every ``self.<name> = ...`` write, keyed by the writing
  method's qualname. Research c-e's rule R3.
* **P2** (§10.2.2) -- ``_typestate_anchor``: the fail-closed single-property
  scan (`return self.<F> is/is not None`) that yields the boolean-view
  attribute name, the state field, and the polarity, all at once. Zero or
  more-than-one such property disables the feature for that class
  (fail-closed, not an error).
* **P3** (§10.2.3) -- ``_channel_default_idiom``: the
  ``<p> = <p> or self.<x> or list(range(len(<q>)))`` idiom match, per
  method of the RECEIVER class (not the tracker class); P3b derives the
  disabler method set from P1b's writer index for the same class.
* **P4** (§10.2.4) -- ``_effects``: classifies each of the tracker class's
  own methods' writes to a field in ``state_fields`` as NO_TIP / HAS_TIP /
  no-effect. A write whose RHS is itself another ``state_fields`` member
  (e.g. ``TipTracker.commit``'s ``self._tip = self._pending_tip``) is
  "ambiguous", which folds into "no effect" under the same both-kinds rule
  as a method that writes both a literal ``None`` and a literal non-``None``
  -- the literal P4 text ("`self.<F> = <expr>` where `<expr>` is not the
  literal `None`") under-specifies this case, and §10.2.4's own worked
  measurement of `commit` ("both-kinds-unknown -> no effect") only holds
  under this reading; see this module's own test for the synthetic
  counterexample that pins it.

**The channel bridge (§10.2.5) is the fifth piece and lives in
``compute_channel_bridge``.** It walks the SAME depth-tracked
``delegates_to`` closure ``derive_contract`` already walks
(``plr_sema.derive._walk_closure``), but keys on each visited record's
``dropped_calls`` (never ``delegates_to`` itself -- a dropped call is by
definition NOT a resolved delegate) matching the channel-receiver shape
``self.<channel_attr>[<name>].<method>``. "Depth 0" in this module's output
means the SAME thing §10.2.2/§10.2.4/§10.2.6 mean by it: the matching
``dropped_calls`` entry belongs to the record visited at closure depth 0
(the entry point's own body), never the guard's own internal depth within
the bridged tracker method (which the payload's illustrative JSON snippet's
``"depth": 1`` for `aspirate` does not actually mean, given `aspirate`'s own
`self.head[channel].get_tip` dropped call sits in its own body -- §10.2.6
states this in prose as depth 0; the JSON snippet is shape-illustrative
only, per this module's own worked-example tests).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from plr_sema.derive.predicate_ast import EnvRef, from_json as predicate_from_json, walk as predicate_walk

from plr_sema.derive import (
    ClassBasesIndex,
    DroppedCall,
    Qualkey,
    SurveyRecord,
    _iter_plr_source_files,
    _module_name_for_plr_file,
    _walk_closure,
    build_class_bases_index,
    default_plr_pkg_root,
    derive_contract,
    resolve,
    resolve_via_base_closure,
)

__all__ = [
    "TIP_STATE_EXCEPTION_MODULE",
    "ReceiverState",
    "compute_tip_state_exceptions",
    "derive_receiver_states",
    "receiver_state_to_json",
    "compute_channel_bridge",
    "TipFamilies",
    "compute_tip_families",
    "reset_rule_candidates",
    "compute_delegate_channel_bindings",
    "lid_typestate_anchor_evidence",
    # 260903 (spec 260903_plr-sema-volume-increment.md §14.0.1/§14.4, T24,
    # backlog #4958): the volume bridge derivation -- B1, B2, P1c, P7, P8
    # and the extended four-segment bridge.
    "compute_volume_state_exceptions",
    "build_plr_class_index",
    "build_plr_class_bases_index",
    "VolumeAnchor",
    "compute_volume_anchors",
    "dataclass_field_annotations",
    "constructor_call_writes",
    "bridge_type_map",
    "operand_pairing_idiom",
    "for_over_comprehension_output",
    "compute_volume_bridge",
    # 260903 (spec 260903_plr-sema-volume-increment.md §14.6, T25, backlog
    # #4958): the generalised conditional-guard rule and R1's
    # position-containment recognition, as a pure function T26/T27 import.
    "volume_guard_is_unconditional",
    # 260909 (spec 260909_plr-sema-observation-increment.md §16.3, T41,
    # backlog #5023): the derived backend surface.
    "BackendSurfaceEntry",
    "backend_surface_entry_to_json",
    "collect_env_ref_method_names",
    "build_backend_surface",
    "probe_method_definitions",
    # 260909 (spec 260909_plr-sema-move-family-increment.md §17.4, T52,
    # D7 unit 12): the singleton typestate anchor (P5) and the
    # intra-operation ordered effect/guard walk (P6).
    "SingletonAnchorCandidate",
    "compute_singleton_typestate_anchors",
    "compute_anchor_guard_states",
]

#: §10.2.5's second conjunct: the taxonomy module path that narrows the
#: 5-member unfiltered `category == "tip_state"` set to exactly
#: {HasTipError, NoTipError}. Named as a constant (not re-typed at each use
#: site) because AC-10.9's AST literal scan treats "the module path is one
#: string literal in plr_sema's source, and that is disclosed, not hidden"
#: (§10.2.5) as the ONE sanctioned literal -- see plr_sema.check.tipstate
#: for the check-side half of that disclosure.
TIP_STATE_EXCEPTION_MODULE = "pylabrobot.resources.errors"

# The channel-receiver bridge shape (§10.2.5, HM-24 pattern 1):
# self.<attr>[<name>].<method>
_BRIDGE_SHAPE_RE = re.compile(r"^self\.(\w+)\[(\w+)\]\.(\w+)$")


def compute_tip_state_exceptions(taxonomy_classes: list[dict[str, Any]]) -> tuple[str, ...]:
    """§10.2.5's two-conjunct filter: `category == "tip_state"` AND
    `module == TIP_STATE_EXCEPTION_MODULE`, both fields already on every
    `plr_exception_taxonomy.json` entry -- nothing hand-typed but the module
    path itself (see this module's docstring and AC-10.9 sub-assertion 2).
    """
    return tuple(
        sorted(
            c["name"]
            for c in taxonomy_classes
            if c.get("category") == "tip_state" and c.get("module") == TIP_STATE_EXCEPTION_MODULE
        )
    )


def compute_volume_state_exceptions(taxonomy_classes: list[dict[str, Any]]) -> tuple[str, ...]:
    """260903 (spec §14.1 fact 2, T24): the SAME two-conjunct filter as
    `compute_tip_state_exceptions`, over `category == "volume_state"`
    instead of `"tip_state"`, against the SAME module path
    (`TIP_STATE_EXCEPTION_MODULE` -- both categories' exception classes live
    in `pylabrobot.resources.errors`, so this reuses the one sanctioned
    literal rather than typing a second copy of it). The unfiltered
    `category == "volume_state"` set has 4 members at the pin
    (`TooLittleLiquidError`, `TooLittleVolumeError`, `BlowOutVolumeError`,
    `LiquidLevelError`); the module conjunct narrows to 2, excluding
    `BlowOutVolumeError` (module `pylabrobot.liquid_handling.liquid_handler`)
    and `LiquidLevelError` (a Hamilton backend class) -- neither name is
    typed here, both are read off the taxonomy JSON.
    """
    return tuple(
        sorted(
            c["name"]
            for c in taxonomy_classes
            if c.get("category") == "volume_state" and c.get("module") == TIP_STATE_EXCEPTION_MODULE
        )
    )


# ---------------------------------------------------------------------------
# P1 (§10.2.1) -- receiver-attribute typing (research c-e's rule R3) and the
# attribute-writer index P3b needs.
# ---------------------------------------------------------------------------


def _unwrap_annotation(node: ast.expr | None) -> str | None:
    """Unwrap `Dict[K,V] -> V`, `List[T] -> T`, `Optional[T] -> T` (both the
    `typing.Optional[T]` subscript form and the PEP 604 `T | None` form) to
    a bare class name.
    """
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Subscript):
        base = node.value
        base_name = (
            base.id
            if isinstance(base, ast.Name)
            else (base.attr if isinstance(base, ast.Attribute) else None)
        )
        sl = node.slice
        if base_name in ("Dict", "dict"):
            if isinstance(sl, ast.Tuple) and len(sl.elts) == 2:
                return _unwrap_annotation(sl.elts[1])
            return None
        if base_name in ("List", "list", "Sequence", "Optional", "Tuple", "tuple"):
            if isinstance(sl, ast.Tuple):
                return _unwrap_annotation(sl.elts[0]) if sl.elts else None
            return _unwrap_annotation(sl)
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left, right = _unwrap_annotation(node.left), _unwrap_annotation(node.right)
        if right == "None":
            return left
        if left == "None":
            return right
        return left
    return None


def _is_self_attr(node: ast.expr, name: str | None = None) -> bool:
    if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self"):
        return False
    return name is None or node.attr == name


def _annotated_attributes(class_node: ast.ClassDef) -> dict[str, str]:
    """P1a: every `self.<name>: <annotation>` `AnnAssign` anywhere in the
    class body (class-level or inside any method, e.g. `__init__`), first
    occurrence wins (deterministic).
    """
    out: dict[str, str] = {}
    for node in ast.walk(class_node):
        if isinstance(node, ast.AnnAssign) and _is_self_attr(node.target):
            unwrapped = _unwrap_annotation(node.annotation)
            if unwrapped is not None:
                out.setdefault(node.target.attr, unwrapped)  # type: ignore[union-attr]
    return out


def _attribute_writers(class_node: ast.ClassDef, class_name: str) -> dict[str, list[str]]:
    """P1b: for every `self.<name> = ...` `Assign` in the class, the
    qualname of the enclosing method. Descends into nested statements
    (`ast.walk` over the whole method body, including `try`/`finally`) so a
    write inside a context-manager `finally` block (`use_channels`'s own
    reset) is found.
    """
    out: dict[str, list[str]] = {}
    for member in ast.iter_child_nodes(class_node):
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        method_qualname = f"{class_name}.{member.name}"
        for node in ast.walk(member):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if _is_self_attr(target):
                        methods = out.setdefault(target.attr, [])  # type: ignore[union-attr]
                        if method_qualname not in methods:
                            methods.append(method_qualname)
    return out


# ---------------------------------------------------------------------------
# P2 (§10.2.2) -- the typestate anchor. Fail-closed: 0 or >1 candidate
# properties disables the feature for this class.
# ---------------------------------------------------------------------------


def _is_docstring_stmt(stmt: ast.stmt) -> bool:
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str)


def _is_property_decorator(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id == "property"


def _typestate_anchor(class_node: ast.ClassDef) -> tuple[str, str, str] | None:
    """Returns `(bool_view_attr, field, true_when)` where `true_when` is
    `"not_none"` (the property is true iff the field is not `None`) or
    `"is_none"` -- or `None` if zero or more than one candidate property
    exists (§10.2.2's fail-closed rule).
    """
    candidates: list[tuple[str, str, str]] = []
    for member in ast.iter_child_nodes(class_node):
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not any(_is_property_decorator(d) for d in member.decorator_list):
            continue
        body = [s for s in member.body if not _is_docstring_stmt(s)]
        if len(body) != 1:
            continue
        stmt = body[0]
        if not (isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Compare)):
            continue
        cmp = stmt.value
        if len(cmp.ops) != 1 or len(cmp.comparators) != 1:
            continue
        op = cmp.ops[0]
        if not isinstance(op, (ast.Is, ast.IsNot)):
            continue
        right = cmp.comparators[0]
        if not (isinstance(right, ast.Constant) and right.value is None):
            continue
        if not _is_self_attr(cmp.left):
            continue
        true_when = "not_none" if isinstance(op, ast.IsNot) else "is_none"
        candidates.append((member.name, cmp.left.attr, true_when))  # type: ignore[union-attr]
    if len(candidates) != 1:
        return None
    return candidates[0]


# ---------------------------------------------------------------------------
# P5 (spec 260909_plr-sema-move-family-increment.md §17.4.1/§17.4.2/§17.4.3,
# T52, D7 unit 12): a SECOND, independent typestate-anchor shape from P2's
# above. P2 requires a bool-view PROPERTY over the field; this anchor
# requires no property at all -- just a plain `self.<F> = ...` assignment
# pair (one constant-`None`, one not) plus a null-check guard reading `F`
# through an `Is`/`IsNot` node, all three found anywhere in the SAME
# class's own body (§17.4.2's conjuncts (a)/(b)/(c)). Both P2 and P5 can
# therefore fire independently for the SAME class -- `LiquidHandler` types
# `self.head` to `TipTracker` (P2's anchor lives on `TipTracker`) and ALSO
# satisfies P5's own three conjuncts directly on `_resource_pickup`
# (P5's anchor lives on `LiquidHandler` ITSELF, no separate tracker class).
# ---------------------------------------------------------------------------


def _self_attr_none_check(node: ast.expr, field: str) -> bool:
    """`self.<field> is None` / `self.<field> is not None` -- the same
    shape `plr_sema.check.tipstate._null_check` matches at CHECK time,
    re-detected here purely syntactically because THIS pass runs before any
    contract table exists (§17.4.2's conjunct (c))."""
    if not (isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1):
        return False
    if not isinstance(node.ops[0], (ast.Is, ast.IsNot)):
        return False
    right = node.comparators[0]
    if not (isinstance(right, ast.Constant) and right.value is None):
        return False
    return _is_self_attr(node.left, field)


def _singleton_anchor_candidate_fields(class_node: ast.ClassDef) -> tuple[str, ...]:
    """§17.4.2's three conjuncts, scanned over `class_node`'s own body: a
    field `F` is a candidate iff at least one `self.F = None` `Assign`
    (conjunct a), at least one `self.F = <non-None>` `Assign` (conjunct b),
    and at least one `if self.F is[/ not] None: raise ...`-shaped guard
    (conjunct c) all occur SOMEWHERE in the class body -- purely syntactic,
    same discipline as P2's `_typestate_anchor` above; no PLR field name is
    hand-typed. Sorted, deterministic.
    """
    none_assigned: set[str] = set()
    nonnone_assigned: set[str] = set()
    guarded: set[str] = set()
    for node in ast.walk(class_node):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute):
            target = node.targets[0]
            if _is_self_attr(target):
                if isinstance(node.value, ast.Constant) and node.value.value is None:
                    none_assigned.add(target.attr)
                else:
                    nonnone_assigned.add(target.attr)
        elif isinstance(node, ast.If) and len(node.body) == 1 and isinstance(node.body[0], ast.Raise):
            test = node.test
            if isinstance(test, ast.Compare) and isinstance(test.left, ast.Attribute) and _self_attr_none_check(test, test.left.attr):
                guarded.add(test.left.attr)
    return tuple(sorted(none_assigned & nonnone_assigned & guarded))


def _property_setter_node(class_node: ast.ClassDef, field: str) -> "ast.FunctionDef | ast.AsyncFunctionDef | None":
    """The `@<field>.setter`-decorated definition of `field` in
    `class_node`, or `None` if it has none."""
    for member in ast.iter_child_nodes(class_node):
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in member.decorator_list:
            if isinstance(dec, ast.Attribute) and dec.attr == "setter" and isinstance(dec.value, ast.Name) and dec.value.id == field:
                return member
    return None


def _is_single_assignment_body(node: "ast.FunctionDef | ast.AsyncFunctionDef") -> bool:
    body = [s for s in node.body if not _is_docstring_stmt(s)]
    return len(body) == 1 and isinstance(body[0], (ast.Assign, ast.AugAssign))


def _singleton_anchor_absent(
    class_node: ast.ClassDef,
    field: str,
    class_name: str,
    module: str,
    class_nodes: dict[str, ast.ClassDef],
    function_index: "FunctionIndex",
) -> int | None:
    """§17.4.2's absence rule, three clauses -- returns the 1-based clause
    number that removed the candidate, or `None` if it survives (present).

    **Clause 3's exception is round 2's R2-C2, conceded.** A `(module,
    qualname)` defined at exactly two linenos does NOT fire clause 3 when
    those two definitions are the getter/setter pair of ONE `@property` --
    one decorated `@property`, the other `@<field>.setter`. Whose qualname
    clause 3 ranges over: the FUNCTION qualname `<class_name>.<field>`,
    meaningful only when `field` is itself a property (has function
    definitions at all) -- a plain attribute has no such definition, so
    `linenos` below is empty and the clause is vacuous for it, exactly as
    §17.4.2 states.
    """
    setter = _property_setter_node(class_node, field)
    if setter is not None and not _is_single_assignment_body(setter):
        return 1  # clause 1.
    # Clause 2: F assigned anywhere OUTSIDE the analyzed class's own body.
    for other_name, other_node in class_nodes.items():
        if other_name == class_name:
            continue
        for node in ast.walk(other_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == field and _is_self_attr(target):
                        return 2  # clause 2.
    # Clause 3: `<class_name>.<field>` defined at more than one lineno,
    # other than as the getter/setter pair of one property.
    qualname = f"{class_name}.{field}"
    matching = [(m, qn, ln) for (m, qn, ln) in function_index if m == module and qn == qualname]
    linenos = sorted({ln for (_m, _qn, ln) in matching})
    if len(linenos) > 1:
        if len(linenos) == 2:
            nodes = [function_index[key] for key in matching]
            is_property = any(
                any(isinstance(d, ast.Name) and d.id == "property" for d in n.decorator_list) for n in nodes
            )
            is_setter_pair = any(
                any(
                    isinstance(d, ast.Attribute) and d.attr == "setter" and isinstance(d.value, ast.Name) and d.value.id == field
                    for d in n.decorator_list
                )
                for n in nodes
            )
            if is_property and is_setter_pair:
                return None  # clause 3's exception: the getter/setter pair.
        return 3  # clause 3.
    return None


@dataclass(frozen=True, slots=True)
class SingletonAnchorCandidate:
    """§17.4.2's published whole-surface selection: one `(class, field)`
    candidate, whether it SURVIVED the absence rule, and if not, which
    clause (1, 2, or 3) removed it."""

    class_name: str
    field: str
    present: bool
    removed_by_clause: int | None = None


def compute_singleton_typestate_anchors(
    class_nodes: dict[str, ast.ClassDef],
    class_modules: dict[str, str],
    function_index: "FunctionIndex",
) -> tuple[dict[str, tuple[str, ...]], tuple[SingletonAnchorCandidate, ...]]:
    """§17.4.2, whole-surface: every `(class, field)` candidate pair
    satisfying conjuncts (a)/(b)/(c) (`_singleton_anchor_candidate_fields`),
    each tested against the absence rule (`_singleton_anchor_absent`).
    Returns `(anchors, candidates)` -- `anchors` is `{class_name: (field,
    ...)}`, sorted, for every candidate that SURVIVES (a class can carry
    MORE than one independent singleton anchor -- unlike P2's single
    bool-view slot, nothing in §17.4.2's own three conjuncts forces
    at-most-one per class, and measured whole-surface `LiquidHandler`
    genuinely has two: `_blow_out_air_volume`
    (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:166,
    973, 1184, 1268`) alongside `_resource_pickup`. Picking an arbitrary
    "winner" by name would either drop a real, independently-trackable
    anchor or require hand-typing the one this increment cares about --
    both refused; every surviving candidate is kept); `candidates` is the
    COMPLETE published selection, in class/field sorted order, for
    AC-17.3's by-clause labelling.
    """
    candidates: list[SingletonAnchorCandidate] = []
    anchors: dict[str, list[str]] = {}
    for class_name, class_node in sorted(class_nodes.items()):
        module = class_modules.get(class_name, "")
        for field in _singleton_anchor_candidate_fields(class_node):
            clause = _singleton_anchor_absent(class_node, field, class_name, module, class_nodes, function_index)
            candidates.append(
                SingletonAnchorCandidate(class_name=class_name, field=field, present=clause is None, removed_by_clause=clause)
            )
            if clause is None:
                anchors.setdefault(class_name, []).append(field)
    return {name: tuple(sorted(fields)) for name, fields in anchors.items()}, tuple(candidates)


# ---------------------------------------------------------------------------
# P6 (spec 260909_plr-sema-move-family-increment.md §17.4.3, T52): the
# intra-operation ordered effect/guard walk. A DERIVE-TIME, purely
# AST-structural computation over ONE entry point's own closure (its own
# body, recursing into resolved bare-`self` delegate calls in SOURCE
# ORDER -- deliberately NOT `_walk_closure`'s own LIFO frontier, which does
# not preserve source order, §17.4.0's own box) -- gives every
# anchor-reading guard reached in that closure a POSITION and folds every
# strictly-earlier effect on the SAME field into its own pre-state.
# ---------------------------------------------------------------------------

_ANCHOR_EMPTY = "EMPTY"
_ANCHOR_HELD = "HELD"
_ANCHOR_TOP = "TOP"
#: Sentinel: "nothing in this closure precedes this position -- read
#: AnchorWalk's own inter-operation carry for this receiver" (§17.4.3
#: condition 4).
_ANCHOR_ENTRY = "ENTRY"


def _anchor_effect(stmt: ast.stmt, field: str) -> str | None:
    """§17.4.3's effect table for one statement against `self.<field>`:
    `"EMPTY"` for a constant-`None` RHS on a plain `self.<field> = <expr>`,
    `"HELD"` for any other plain-assignment RHS, `"TOP"` (widen) for an
    `ast.AugAssign`, a tuple target, or a subscript target naming the SAME
    field -- `tipstate._apply_transfer`'s own third case, same spirit.
    `None` when this statement does not touch `field` at all.
    """
    if isinstance(stmt, ast.AugAssign) and _is_self_attr(stmt.target, field):
        return _ANCHOR_TOP
    if isinstance(stmt, ast.Assign):
        for target in stmt.targets:
            if isinstance(target, ast.Tuple) and any(isinstance(elt, ast.Attribute) and _is_self_attr(elt, field) for elt in target.elts):
                return _ANCHOR_TOP
            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Attribute) and _is_self_attr(target.value, field):
                return _ANCHOR_TOP
        if len(stmt.targets) == 1 and _is_self_attr(stmt.targets[0], field):
            if isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
                return _ANCHOR_EMPTY
            return _ANCHOR_HELD
    return None


def _contains_return_break_continue(stmts: list[ast.stmt]) -> bool:
    for stmt in stmts:
        for node in ast.walk(stmt):
            if isinstance(node, (ast.Return, ast.Break, ast.Continue)):
                return True
    return False


def _self_call_name(stmt: ast.stmt) -> str | None:
    """`self.<name>(...)` at statement level -- a bare expression
    statement, or the RHS of a plain `Assign`/`AnnAssign`, optionally
    `await`-wrapped. Returns `<name>`, or `None` for anything else
    (including `self.<attr>.<name>(...)`, e.g. `self.backend.<m>(...)` --
    a DIFFERENT receiver expression, never a bare-self delegate call).
    """
    value: ast.expr | None = None
    if isinstance(stmt, ast.Expr):
        value = stmt.value
    elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
        value = stmt.value
    if isinstance(value, ast.Await):
        value = value.value
    if not isinstance(value, ast.Call):
        return None
    func = value.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "self":
        return func.attr
    return None


class _AnchorWalkCtx:
    def __init__(
        self,
        field: str,
        class_name: str,
        class_nodes: dict[str, ast.ClassDef],
        class_modules: dict[str, str],
        bases_index: ClassBasesIndex,
    ) -> None:
        self.field = field
        self.class_name = class_name
        self.class_nodes = class_nodes
        self.class_modules = class_modules
        self.bases_index = bases_index
        self.guard_states: dict[int, str] = {}
        #: §17.4.3's FIVE widening conditions -- condition 4 (the initial
        #: state) and condition 5 (the multi-position join, folded silently
        #: into `_record_guard` below rather than counted separately, since
        #: it is a JOIN operator applied uniformly, not a distinct decision
        #: point this walker chooses to take) are not this dict's business;
        #: it counts conditions 1-3, the ones THIS pass can actually detect.
        self.widened_by: dict[str, int] = {"condition_1": 0, "condition_2": 0, "condition_3": 0}

    def _record_guard(self, lineno: int, state: str) -> None:
        # §17.4.3 condition 5: a guard reached at several positions takes
        # the JOIN of the states at all of them -- TOP on disagreement.
        existing = self.guard_states.get(lineno)
        self.guard_states[lineno] = state if existing is None else (existing if existing == state else _ANCHOR_TOP)

    def resolve_self_call(self, class_name: str, method_name: str) -> "tuple[ast.FunctionDef | ast.AsyncFunctionDef, str] | None":
        """`(method_node, owning_class)`, resolved first within
        `class_name`'s own body, falling back to M-INH's own
        `resolve_via_base_closure` (§17.2, already shipped) -- the SAME
        resolution `_state_updated` needs to reach `Resource` (AC-17.1),
        so an inherited delegate that touches no anchor state is correctly
        found and recursed into (contributing nothing), never mistaken for
        an unresolved one (§17.4.3 condition 3)."""
        node = self.class_nodes.get(class_name)
        if node is not None:
            for member in ast.iter_child_nodes(node):
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == method_name:
                    return member, class_name
        ancestor = resolve_via_base_closure(class_name, method_name, self.class_nodes, self.bases_index)
        if ancestor is None:
            return None
        anc_node = self.class_nodes.get(ancestor)
        if anc_node is None:
            return None
        for member in ast.iter_child_nodes(anc_node):
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == method_name:
                return member, ancestor
        return None


def _walk_anchor_stmts(stmts: list[ast.stmt], state: str, ctx: _AnchorWalkCtx, call_stack: frozenset[str]) -> str:
    for stmt in stmts:
        if isinstance(stmt, ast.If) and len(stmt.body) == 1 and isinstance(stmt.body[0], ast.Raise):
            if _self_attr_none_check(stmt.test, ctx.field):
                ctx._record_guard(stmt.body[0].lineno, state)
                continue
        if isinstance(stmt, ast.Try):
            state = _walk_anchor_stmts(stmt.body, state, ctx, call_stack)
            for handler in stmt.handlers:
                # §17.4.3 condition 2 (round 2's R2-C6 fence): a handler
                # whose last statement is an `ast.Raise` AND which contains
                # no `Return`/`Break`/`Continue` at any depth cannot fall
                # through to positions after the `try` -- its own
                # assignment is folded (walked, purely for guard/effect
                # detection inside it) but contributes NO state to what
                # follows. Any other handler widens.
                cannot_fall_through = (
                    bool(handler.body)
                    and isinstance(handler.body[-1], ast.Raise)
                    and not _contains_return_break_continue(handler.body)
                )
                if cannot_fall_through:
                    _walk_anchor_stmts(handler.body, state, ctx, call_stack)
                else:
                    state = _ANCHOR_TOP
                    ctx.widened_by["condition_2"] += 1
            if stmt.orelse:
                state = _walk_anchor_stmts(stmt.orelse, state, ctx, call_stack)
            if stmt.finalbody:
                state = _walk_anchor_stmts(stmt.finalbody, state, ctx, call_stack)
            continue
        if isinstance(stmt, (ast.If, ast.For, ast.AsyncFor, ast.While)):
            # §17.4.3 condition 1: an effect inside a conditionally-reached
            # branch widens from that point on -- detected here as "a
            # branch's own sub-walk produced a DIFFERENT state than it was
            # given", since neither branch is guaranteed to execute.
            branches = [stmt.body, stmt.orelse] if isinstance(stmt, ast.If) else [stmt.body]
            widened = False
            for branch in branches:
                if branch and _walk_anchor_stmts(branch, state, ctx, call_stack) != state:
                    widened = True
            if widened:
                state = _ANCHOR_TOP
                ctx.widened_by["condition_1"] += 1
            continue
        effect = _anchor_effect(stmt, ctx.field)
        if effect is not None:
            state = effect
            continue
        call_name = _self_call_name(stmt)
        if call_name is not None:
            if call_name in call_stack:
                continue  # cycle guard: a repeat visit contributes nothing further.
            resolved = ctx.resolve_self_call(ctx.class_name, call_name)
            if resolved is None:
                # §17.4.3 condition 3: an unresolved delegate may mutate
                # the field invisibly.
                state = _ANCHOR_TOP
                ctx.widened_by["condition_3"] += 1
                continue
            member, _owner_class = resolved
            state = _walk_anchor_stmts(list(member.body), state, ctx, call_stack | {call_name})
            continue
    return state


def compute_anchor_guard_states(
    entry_node: "ast.FunctionDef | ast.AsyncFunctionDef",
    *,
    field: str,
    class_name: str,
    class_nodes: dict[str, ast.ClassDef],
    class_modules: dict[str, str],
    bases_index: ClassBasesIndex,
) -> tuple[dict[int, str], dict[str, int], str | None]:
    """§17.4.3: the intra-operation ordered effect/guard walk over ONE
    entry point's own closure. Returns `(guard_states, widened_by,
    net_effect)`:

    * `guard_states` -- `{raise_lineno: "EMPTY"|"HELD"|"TOP"|"ENTRY"}` for
      every anchor-reading guard (§17.4.2 conjunct (c)'s shape) reached
      anywhere in the closure, keyed by the SAME lineno the survey records
      for that guard (the `raise` statement's own `node.lineno`,
      `scripts/survey_plr_preconditions.py`'s `visit_Raise`) -- so a
      derive-time lookup by `InlinedGuard.site.lineno` finds it directly,
      no re-parsing of `condition` needed at derive_contract's own guard
      loop.
    * `widened_by` -- counts for conditions 1-3 (this pass's own; 4 and 5
      are AnchorWalk's/`_record_guard`'s business respectively, §17.4.3's
      own box).
    * `net_effect` -- `"EMPTY"`/`"HELD"`/`"TOP"`, this entry point's own
      LAST unconditionally-reached effect on `field`, or `None` if the
      closure never touches `field` at all (E3's own no-bridge no-op,
      `tipstate._apply_transfer`'s identical case) -- the value
      `evaluate_anchor_call` applies to `AnchorWalk`'s inter-operation
      carry AFTER evaluating this call's own guards.
    """
    ctx = _AnchorWalkCtx(field, class_name, class_nodes, class_modules, bases_index)
    net = _walk_anchor_stmts(list(entry_node.body), _ANCHOR_ENTRY, ctx, frozenset({entry_node.name}))
    return ctx.guard_states, dict(ctx.widened_by), (None if net == _ANCHOR_ENTRY else net)


# ---------------------------------------------------------------------------
# P3 (§10.2.3) -- the channel-arity idiom (P3a) and its disablers (P3b).
# Both scanned over the RECEIVER class R (not the tracker class C).
# ---------------------------------------------------------------------------


def _is_list_range_len_call(node: ast.expr, param_name: str | None) -> str | None:
    """Matches `list(range(len(<q>)))`; returns `<q>`'s name if it matches
    (and, when `param_name` is given, requires `<q> == param_name` is NOT
    required -- `<q>` is an independent name, e.g. `tip_spots`, distinct
    from `<p>`).
    """
    if not (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "list"
        and len(node.args) == 1
    ):
        return None
    range_call = node.args[0]
    if not (
        isinstance(range_call, ast.Call)
        and isinstance(range_call.func, ast.Name)
        and range_call.func.id == "range"
        and len(range_call.args) == 1
    ):
        return None
    len_call = range_call.args[0]
    if not (
        isinstance(len_call, ast.Call)
        and isinstance(len_call.func, ast.Name)
        and len_call.func.id == "len"
        and len(len_call.args) == 1
        and isinstance(len_call.args[0], ast.Name)
    ):
        return None
    return len_call.args[0].id


def _channel_default_idiom(class_node: ast.ClassDef) -> dict[str, tuple[str, str, str]]:
    """P3a: `method_name -> (q, x, p)` for every method matching
    `<p> = <p> or self.<x> or list(range(len(<q>)))`. `p` -- the KEYWORD
    PLR itself uses to select channels explicitly (empirically
    `"use_channels"` at the current pin, always) -- is read straight off
    the assignment target (`target.id`), never hand-typed: `channels_for_call`
    / P9 (§13.5.2) both need this exact name and AC-10.9/AC-13.15(iii)'s AST
    literal scan forbids spelling it as a string constant anywhere in this
    module or `plr_sema.check.tipstate`.
    """
    out: dict[str, tuple[str, str, str]] = {}
    for member in ast.iter_child_nodes(class_node):
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(member):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            p = target.id
            value = node.value
            if not (isinstance(value, ast.BoolOp) and isinstance(value.op, ast.Or) and len(value.values) == 3):
                continue
            v0, v1, v2 = value.values
            if not (isinstance(v0, ast.Name) and v0.id == p):
                continue
            if not _is_self_attr(v1):
                continue
            q = _is_list_range_len_call(v2, p)
            if q is None:
                continue
            out.setdefault(member.name, (q, v1.attr, p))  # type: ignore[union-attr]
    return out


def _channel_default_disablers(
    idiom_matches: dict[str, tuple[str, str, str]], attribute_writers: dict[str, list[str]]
) -> tuple[str, ...]:
    """P3b: the set of methods writing the `self.<x>` middle term of any P3a
    match, unioned across every distinct `x`. `attribute_writers` (P1b) is
    keyed by QUALIFIED method name (`f"{class_name}.{method}"`, per P1b's
    own definition); this result is the BARE method name (the shape
    `receiver_state["...]["channel_default_disablers"]` uses, matched at
    check time against `ir.Call.method`, which never carries a qualname).
    """
    disablers: set[str] = set()
    for _q, x, _p in idiom_matches.values():
        for qualname in attribute_writers.get(x, ()):
            disablers.add(qualname.rsplit(".", 1)[-1])
    return tuple(sorted(disablers))


def _channel_kwarg_name(idiom_matches: dict[str, tuple[str, str, str]]) -> str | None:
    """The single explicit-channel keyword name every P3a-matched method of
    this receiver agrees on (`p`, §13.5.2 rule 2's `use_channels=`),
    derived rather than hand-typed. `None` (fail-closed, same direction as
    P2's own anchor rule) when no method matched at all, or matched
    methods disagree on `p` -- a receiver whose own idiom is internally
    inconsistent about its channel keyword cannot be trusted to name one
    globally.
    """
    names = {p for _q, _x, p in idiom_matches.values()}
    if len(names) != 1:
        return None
    return next(iter(names))


# ---------------------------------------------------------------------------
# P2's state_fields -- every field named in a NullCheck atom by any guard of
# C that raises a tip_state exception (§10.2.2's last paragraph). Needs the
# survey's own records for C, and the taxonomy filter.
# ---------------------------------------------------------------------------


def _null_check_field(condition: str | None) -> str | None:
    if condition is None:
        return None
    try:
        node = ast.parse(condition, mode="eval").body
    except SyntaxError:
        return None
    if not (isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1):
        return None
    op = node.ops[0]
    if not isinstance(op, (ast.Is, ast.IsNot)):
        return None
    right = node.comparators[0]
    if not (isinstance(right, ast.Constant) and right.value is None):
        return None
    left = node.left
    if _is_self_attr(left):
        return left.attr  # type: ignore[union-attr]
    return None


def _state_fields_for_class(
    records_by_class: dict[str, list[SurveyRecord]],
    class_name: str,
    tip_state_exceptions: frozenset[str],
    bool_view_field: str,
) -> tuple[str, ...]:
    """§10.2.2: every field named in a NullCheck atom by any of C's OWN
    guards that raises a tip_state exception, plus the P2 anchor's own
    `bool_view_field` (always included -- it is load-bearing for BoolView
    atoms even on a class whose guards happen to name only the OTHER
    field, or none at all).
    """
    fields: set[str] = {bool_view_field}
    for rec in records_by_class.get(class_name, ()):
        for finding in rec.findings:
            if finding.raises in tip_state_exceptions:
                f = _null_check_field(finding.condition)
                if f is not None:
                    fields.add(f)
    return tuple(sorted(fields))


# ---------------------------------------------------------------------------
# P4 (§10.2.4) -- effects. Scanned over the TRACKER class C's own methods.
# ---------------------------------------------------------------------------


def _classify_write(value: ast.expr, state_field_set: frozenset[str]) -> str:
    """One write's classification: `"NO_TIP"` (literal `None`),
    `"ambiguous"` (the RHS is itself `self.<G>` for another/the-same state
    field -- its own runtime value is not analyzable as one literal kind,
    e.g. `TipTracker.commit`'s `self._tip = self._pending_tip`), or
    `"HAS_TIP"` (anything else non-`None`).
    """
    if isinstance(value, ast.Constant) and value.value is None:
        return "NO_TIP"
    if _is_self_attr(value) and value.attr in state_field_set:  # type: ignore[union-attr]
        return "ambiguous"
    return "HAS_TIP"


def _effects(class_node: ast.ClassDef, state_fields: tuple[str, ...]) -> dict[str, str]:
    """P4: `method_name -> "HAS_TIP"|"NO_TIP"` for every method of C whose
    writes to `state_fields` unambiguously establish one polarity. A method
    with no such write, or whose writes disagree/are ambiguous, is omitted
    (no effect -- E3).
    """
    state_field_set = frozenset(state_fields)
    out: dict[str, str] = {}
    for member in ast.iter_child_nodes(class_node):
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        kinds: set[str] = set()
        for node in ast.walk(member):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if _is_self_attr(target) and target.attr in state_field_set:  # type: ignore[union-attr]
                        kinds.add(_classify_write(node.value, state_field_set))
        if kinds == {"NO_TIP"}:
            out[member.name] = "NO_TIP"
        elif kinds == {"HAS_TIP"}:
            out[member.name] = "HAS_TIP"
        # {} (untouched), {"ambiguous"}, or any mix -> no effect, omitted.
    return out


# ---------------------------------------------------------------------------
# P5 (spec 260903 §12.1.2) -- the derived setup() head-reset effect. A
# WHOLE-EXPRESSION property over inputs P1/P4 already compute (the class
# index, the attribute-writer index, the constructor's own P4
# classification), not a sixth HM-25 template -- see the module-level
# rationale in §12.1.2 itself. `_attribute_writers` (P1b) already gives the
# per-attribute candidate method set; P5 adds only the three-conjunct test
# below plus the constructor-state read.
# ---------------------------------------------------------------------------


def _is_fresh_only_construction(value: ast.expr, tracker_class: str, class_index: Any) -> bool:
    """Conjunct 1: every `ast.Call` in `value` whose `func` is an
    `ast.Name` that is a key of `class_index` (the whole-PLR class index,
    not just receiver classes) must construct `tracker_class`, and at
    least one such call must exist. A call to a name `class_index` does
    not know (`range`, `len`, `dict`, ...) cannot produce a tracker and is
    ignored -- it is simply not a key of `class_index`.
    """
    found_target = False
    for node in ast.walk(value):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in class_index:
            if node.func.id != tracker_class:
                return False
            found_target = True
    return found_target


def _no_self_attr_load(value: ast.expr, attr_name: str) -> bool:
    """Conjunct 2: `value` contains no load of `self.<attr_name>`
    anywhere. `value` is an assignment's RHS, so every `ast.Attribute`
    found by `ast.walk` here is necessarily a load, never a store target.
    """
    return not any(_is_self_attr(node, attr_name) for node in ast.walk(value))


def reset_rule_candidates(
    receiver_node: ast.ClassDef,
    attr_name: str,
    tracker_class: str,
    class_index: Any,
) -> tuple[frozenset[str], frozenset[str]]:
    """`(conj12, conj123)`: the bare method names of `receiver_node` that
    contain an `ast.Assign` whose single target is `self.<attr_name>` (an
    `ast.Attribute`, never an `ast.Subscript` -- `_is_self_attr` already
    enforces that) and whose value satisfies conjuncts 1-2 (fresh-only
    construction, no carry-over). `conj12` matches such an assignment at
    ANY depth in the method body (mirroring P1b's own `ast.walk`);
    `conj123` matches only when that assignment is additionally a DIRECT
    statement of the method's own body -- not nested inside an `If`,
    `For`, `While`, `Try`, `With` or `match` -- which is conjunct 3 and is
    enforced simply by looking at `member.body` directly instead of
    `ast.walk`-ing into it.

    Exposed (not `_`-prefixed) because AC-12.1(iv) asserts these two sets
    directly against real PLR -- `{"setup", "load_state"}` for `conj12`,
    `{"setup"}` for `conj123` at the pin this module derives against --
    not just P5's final one-or-none selection.
    """
    conj12: set[str] = set()
    conj123: set[str] = set()
    for member in ast.iter_child_nodes(receiver_node):
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(member):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
                continue
            target = node.targets[0]
            if not _is_self_attr(target, attr_name):
                continue
            if _is_fresh_only_construction(node.value, tracker_class, class_index) and _no_self_attr_load(
                node.value, attr_name
            ):
                conj12.add(member.name)
        for stmt in member.body:
            if not (isinstance(stmt, ast.Assign) and len(stmt.targets) == 1):
                continue
            target = stmt.targets[0]
            if not _is_self_attr(target, attr_name):
                continue
            if _is_fresh_only_construction(stmt.value, tracker_class, class_index) and _no_self_attr_load(
                stmt.value, attr_name
            ):
                conj123.add(member.name)
    return frozenset(conj12), frozenset(conj123)


def _constructor_state(tracker_node: ast.ClassDef, state_fields: tuple[str, ...]) -> str | None:
    """`constructor_state(C)` (§12.1.2): P4's OWN three-way classification
    (`_classify_write`) applied to `C.__init__`'s writes to
    `state_fields` -- the same rule `_effects` applies to every other
    method of `C`, but via a DEDICATED pass over `__init__` specifically,
    because `__init__` conventionally writes its state fields via
    `ast.AnnAssign` (e.g. `TipTracker.__init__`'s `self._tip:
    Optional["Tip"] = None`), which `_effects`'s `ast.Assign`-only scan --
    matching how every OTHER tracker method writes them, by plain
    reassignment -- does not match at all. Returns `"NO_TIP"`/`"HAS_TIP"`
    when `__init__` unambiguously establishes one polarity over
    `state_fields`, `None` otherwise (no such write, a polarity mix, or
    `"ambiguous"` -- E3's own "no effect" disposition, reused here per
    §12.1.2's "both-kinds or ambiguous is not a reset").
    """
    state_field_set = frozenset(state_fields)
    init_method: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for member in ast.iter_child_nodes(tracker_node):
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == "__init__":
            init_method = member
            break
    if init_method is None:
        return None
    kinds: set[str] = set()
    for node in ast.walk(init_method):
        if isinstance(node, ast.Assign):
            targets: list[ast.expr] = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        else:
            continue
        for target in targets:
            if _is_self_attr(target) and target.attr in state_field_set:  # type: ignore[union-attr]
                kinds.add(_classify_write(value, state_field_set))
    if kinds == {"NO_TIP"}:
        return "NO_TIP"
    if kinds == {"HAS_TIP"}:
        return "HAS_TIP"
    return None


def _entry_reset(conj123: frozenset[str], constructor_state: str | None) -> tuple[dict[str, str] | None, str]:
    """`(entry_reset, ledger_reason)`. `entry_reset` is
    `{"method": <name>, "post": "no_tip"|"has_tip"}` iff exactly one
    method satisfies all three conjuncts (`conj123`) AND
    `constructor_state` (`_constructor_state(C)`, above) is admissible
    (`"NO_TIP"` or `"HAS_TIP"`, never `None`). `ledger_reason` is
    `"ambiguous"` when more than one method satisfies all three conjuncts
    (§12.1.2's own more-than-one rule, fail-closed), `"absent"` for every
    other nothing-emitted case (zero qualifying methods, or a qualifying
    method whose constructor state is itself inadmissible), and `"ok"`
    when `entry_reset` is populated.
    """
    if len(conj123) > 1:
        return None, "ambiguous"
    if len(conj123) != 1:
        return None, "absent"
    method = next(iter(conj123))
    if constructor_state not in ("NO_TIP", "HAS_TIP"):
        return None, "absent"
    # `.lower()`, not a hand-typed `"has_tip"` literal: that string is
    # ALSO PLR's own bool-view attribute name (`TipTracker.has_tip`),
    # forbidden by AC-10.9/AC-12.1(ii)'s AST literal scan.
    post = constructor_state.lower()
    return {"method": method, "post": post}, "ok"


# ---------------------------------------------------------------------------
# Assembling one ReceiverState per qualifying receiver class.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReceiverState:
    channel_attr: str
    tracker_class: str
    tracker_module: str
    bool_view_attr: str
    bool_view_field: str
    true_when: str
    state_fields: tuple[str, ...]
    effects: dict[str, str]
    channel_default_param: dict[str, str]
    channel_default_disablers: tuple[str, ...]
    tip_state_exceptions: tuple[str, ...]
    entry_reset: dict[str, str] | None = None
    entry_reset_ledger: str = "absent"
    #: 260903 (spec §13.5.3, P9): the keyword PLR itself uses to select
    #: channels explicitly (`p` in P3a's own idiom, §13.5.2 rule 2's
    #: `use_channels=`), or `None` when the receiver's own P3a matches
    #: disagree on it. Additive; a pre-increment `ReceiverState` has no
    #: caller passing this, so it defaults to `None` (fail-closed --
    #: `channels_for_call`'s rule 2 degrades to "never explicit").
    channel_kwarg: str | None = None
    #: 260903 (spec §13.5.2, P9): `method_name -> {delegate_name: binding}`
    #: -- see `compute_delegate_channel_bindings`. Additive; defaults to
    #: `{}` (no binding published, `compute_channel_bridge` attaches no
    #: `bound_channels` key -- every channel_guards entry degrades to
    #: today's `⊤` behaviour exactly).
    delegate_channel_binding: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    #: 260909 (spec 260909_plr-sema-move-family-increment.md §17.4.2, T52,
    #: P5): every singleton typestate anchor field on THIS receiver class
    #: itself (e.g. `("_resource_pickup",)` on `LiquidHandler` -- measured
    #: whole-surface, `LiquidHandler` actually carries TWO, see
    #: `compute_singleton_typestate_anchors`'s own docstring for why both
    #: are kept rather than one being picked as a "winner") -- a SECOND,
    #: independent anchor family from `bool_view_attr`/`state_fields`
    #: above, which describe P2's anchor on the SEPARATE tracker class.
    #: Additive; defaults to `()` (no P5 anchor known for this receiver, or
    #: the caller did not supply a `function_index` --
    #: `compute_channel_bridge`'s same fail-closed-by-omission discipline).
    anchor_fields: tuple[str, ...] = ()


def receiver_state_to_json(rs: ReceiverState) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "channel_attr": rs.channel_attr,
        "tracker_class": rs.tracker_class,
        "bool_view": {"attr": rs.bool_view_attr, "field": rs.bool_view_field, "true_when": rs.true_when},
        "state_fields": list(rs.state_fields),
        "effects": dict(sorted(rs.effects.items())),
        "channel_default_param": dict(sorted(rs.channel_default_param.items())),
        "channel_default_disablers": list(rs.channel_default_disablers),
        "tip_state_exceptions": list(rs.tip_state_exceptions),
    }
    if rs.entry_reset is not None:
        payload["entry_reset"] = dict(rs.entry_reset)
    if rs.channel_kwarg is not None:
        payload["channel_kwarg"] = rs.channel_kwarg
    if rs.delegate_channel_binding:
        # 260903 (spec §13.5.3, P9): published so the "complete set of
        # (K, delegate, rule, channels) tuples P9 binds" (AC-13.15(i)) is
        # visible on the shipped artifact, not just inferable from the
        # per-guard `bound_channels` keys `compute_channel_bridge` attaches.
        payload["delegate_channel_binding"] = {
            method: {delegate: dict(binding) for delegate, binding in sorted(bindings.items())}
            for method, bindings in sorted(rs.delegate_channel_binding.items())
        }
    if rs.anchor_fields:
        payload["anchor_fields"] = list(rs.anchor_fields)
    return payload


def derive_receiver_states(
    plr_pkg_root: Path,
    records: list[SurveyRecord],
    taxonomy_classes: list[dict[str, Any]],
    *,
    function_index: "FunctionIndex | None" = None,
) -> dict[str, ReceiverState]:
    """Runs P1-P4 over the whole PLR source tree and returns one
    `ReceiverState` per qualifying receiver class (measured: `{"LiquidHandler":
    ...}` at the current pin -- `head96` also types to `TipTracker` under
    P1a but loses the deterministic tie-break, §10.9's non-goal).

    ``function_index`` (260909, T52, spec §17.4.2, P5, additive, opt-in):
    when supplied, ALSO computes the whole-surface singleton-anchor
    selection (`compute_singleton_typestate_anchors`) and attaches each
    qualifying receiver's own `anchor_fields`. Omitting it (the default)
    reproduces this function's exact pre-T52 behaviour -- every
    `ReceiverState.anchor_fields` stays `()`, same fail-closed-by-omission
    discipline every other additive keyword in this module already uses.
    """
    root = plr_pkg_root if plr_pkg_root is not None else default_plr_pkg_root()
    tip_state_exceptions = compute_tip_state_exceptions(taxonomy_classes)
    tip_state_exceptions_set = frozenset(tip_state_exceptions)

    class_nodes: dict[str, ast.ClassDef] = {}
    class_modules: dict[str, str] = {}
    for file in _iter_plr_source_files(root):
        try:
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file))
        except (SyntaxError, UnicodeDecodeError):
            continue
        module = _module_name_for_plr_file(file, root)
        for top in ast.iter_child_nodes(tree):
            if isinstance(top, ast.ClassDef):
                class_nodes.setdefault(top.name, top)
                class_modules.setdefault(top.name, module)

    records_by_class: dict[str, list[SurveyRecord]] = {}
    for rec in records:
        if rec.class_name is not None:
            records_by_class.setdefault(rec.class_name, []).append(rec)

    # Cache P2/P4 results per tracker class -- multiple receiver classes
    # could type an attribute to the same tracker class.
    anchor_cache: dict[str, tuple[str, str, str] | None] = {}
    effects_cache: dict[str, dict[str, str]] = {}
    state_fields_cache: dict[str, tuple[str, ...]] = {}
    constructor_state_cache: dict[str, str | None] = {}

    # 260909 (T52, spec §17.4.2, P5, additive, opt-in): the singleton
    # typestate anchor's whole-surface selection, computed ONCE (not per
    # receiver -- P5's anchor lives on the RECEIVER class itself, unlike
    # P2's, so it has no per-tracker-class cache to share). `{}` when
    # `function_index` was not supplied, degrading every `anchor_fields`
    # below to `()` exactly as this function's pre-T52 behaviour did.
    singleton_anchors: dict[str, tuple[str, ...]] = {}
    if function_index is not None:
        singleton_anchors, _candidates = compute_singleton_typestate_anchors(class_nodes, class_modules, function_index)

    out: dict[str, ReceiverState] = {}
    for receiver_name, receiver_node in sorted(class_nodes.items()):
        annotated = _annotated_attributes(receiver_node)
        # Deterministic tie-break (§10.2's own note): among attributes
        # typing to an anchored class, pick alphabetically first
        # ("head" < "head96").
        for attr_name in sorted(annotated):
            tracker_class = annotated[attr_name]
            tracker_node = class_nodes.get(tracker_class)
            if tracker_node is None:
                continue
            if tracker_class not in anchor_cache:
                anchor_cache[tracker_class] = _typestate_anchor(tracker_node)
            anchor = anchor_cache[tracker_class]
            if anchor is None:
                continue  # P2 fail-closed: feature disabled for this class.
            bool_view_attr, bool_view_field, true_when = anchor

            if tracker_class not in state_fields_cache:
                state_fields_cache[tracker_class] = _state_fields_for_class(
                    records_by_class, tracker_class, tip_state_exceptions_set, bool_view_field
                )
            state_fields = state_fields_cache[tracker_class]

            if tracker_class not in effects_cache:
                effects_cache[tracker_class] = _effects(tracker_node, state_fields)
            effects = effects_cache[tracker_class]

            idiom_matches = _channel_default_idiom(receiver_node)
            channel_default_param = {m: q for m, (q, _x, _p) in idiom_matches.items()}
            attribute_writers = _attribute_writers(receiver_node, receiver_name)
            disablers = _channel_default_disablers(idiom_matches, attribute_writers)
            channel_kwarg = _channel_kwarg_name(idiom_matches)
            # P9 (§13.5.2): purely syntactic over `receiver_node`'s own
            # body -- computed once per receiver, independent of any
            # `delegates_to` closure walk (that happens per contract entry,
            # in `compute_channel_bridge`, which looks this table up).
            delegate_channel_binding = compute_delegate_channel_bindings(
                receiver_node, channel_default_param, channel_kwarg
            )

            # P5 (§12.1.2): `class_nodes` IS the "P1 class index" conjunct 1
            # matches `ast.Call` funcs against -- every top-level class
            # across the whole PLR source tree, already built above.
            if tracker_class not in constructor_state_cache:
                constructor_state_cache[tracker_class] = _constructor_state(tracker_node, state_fields)
            constructor_state = constructor_state_cache[tracker_class]
            _conj12, conj123 = reset_rule_candidates(receiver_node, attr_name, tracker_class, class_nodes)
            entry_reset, entry_reset_ledger = _entry_reset(conj123, constructor_state)

            out[receiver_name] = ReceiverState(
                channel_attr=attr_name,
                tracker_class=tracker_class,
                tracker_module=class_modules[tracker_class],
                bool_view_attr=bool_view_attr,
                bool_view_field=bool_view_field,
                true_when=true_when,
                state_fields=state_fields,
                effects=effects,
                channel_default_param=channel_default_param,
                channel_default_disablers=disablers,
                tip_state_exceptions=tip_state_exceptions,
                entry_reset=entry_reset,
                entry_reset_ledger=entry_reset_ledger,
                channel_kwarg=channel_kwarg,
                delegate_channel_binding=delegate_channel_binding,
                anchor_fields=singleton_anchors.get(receiver_name, ()),
            )
            break  # first (alphabetically) qualifying attribute wins.
    return out


# ---------------------------------------------------------------------------
# P9 (spec 260903 §13.5.2, backlog #4946) -- delegate-call literal channel
# binding. Purely syntactic over `receiver_node`'s OWN body -- no closure
# walk, no contract/index lookup. `compute_channel_bridge` (below) is the
# ONLY caller: once its closure walk knows, from the depth-1 step, which
# one-hop delegate D produced a given `channel_guards` entry, it looks up
# `(K, D)` in the table this section builds.
#
# Rule 4 (P3b disabler poisoning) is DELIBERATELY not applied here -- it is
# a CHECK-TIME fact over the whole call graph (whether some disabler method
# was invoked anywhere on the receiver), not a derive-time one over a single
# call site's own syntax. `plr_sema.check.tipstate.evaluate_call` re-applies
# it, via the pre-existing `poisoned` pre-scan, AFTER consulting the record
# this section computes -- §13.5.2's own ordering requirement ("checked
# after 2 and 3, never before").
# ---------------------------------------------------------------------------


def _iter_depth0_calls(member: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    """Every `ast.Call` in `member`'s own body at DEPTH 0: descends into
    `If`/`For`/`While`/`Try`/`With`/`match` bodies (§13.5.2's own "why the
    `for` loop around the `dispense` call does not defeat rule 1" note --
    rule 1 counts SYNTACTIC call sites, not dynamic invocations) but NEVER
    into a nested `FunctionDef`/`AsyncFunctionDef`/`Lambda`'s own body.
    """
    calls: list[ast.Call] = []

    def _walk(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            if isinstance(child, ast.Call):
                calls.append(child)
            _walk(child)

    _walk(member)
    return calls


def _int_list_display(node: ast.expr) -> tuple[int, ...] | None:
    """Rule 2's `<E>`: an `ast.List`/`ast.Tuple` display whose every
    element is an `ast.Constant` of type `int` (`bool` excluded, same guard
    `plr_sema.check.tipstate._int_seq` applies at check time over a lowered
    `ir.Seq` -- mirrored here at derive time over raw syntax).
    """
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    out: list[int] = []
    for elt in node.elts:
        if not (isinstance(elt, ast.Constant) and isinstance(elt.value, int) and not isinstance(elt.value, bool)):
            return None
        out.append(elt.value)
    return tuple(out)


def _display_length(node: ast.expr) -> int | None:
    """Rule 3's `<E>`: an `ast.List`/`ast.Tuple` display -- LENGTH only,
    same "the elements need not be resolvable" property P3a's own
    `list(range(len(<q>)))` production relies on. A `Starred` element
    defeats even the length read (rule 5's "a starred argument" widening
    case) -- the display's true runtime length is not syntactically known.
    """
    if isinstance(node, (ast.List, ast.Tuple)):
        if any(isinstance(elt, ast.Starred) for elt in node.elts):
            return None
        return len(node.elts)
    return None


def _bound_channels_from_call(
    call: ast.Call, delegate: str, channel_default_param: dict[str, str], channel_kwarg: str | None
) -> dict[str, Any] | None:
    """Rules 2/3/5 (§13.5.2), applied to the ONE call site rule 1's
    singleton test (`_delegate_channel_bindings`, below) already narrowed
    to. Returns the bound-channels record (`channels`/`rule`/`delegate`/
    `site_lineno`) or `None` (rule 5, `⊤`).
    """
    kwargs = {kw.arg: kw.value for kw in call.keywords if kw.arg is not None}

    if channel_kwarg is not None:
        explicit = kwargs.get(channel_kwarg)
        if explicit is not None:
            ints = _int_list_display(explicit)
            if ints is None:
                return None  # rule 5: present but not a clean int display.
            return {
                "channels": list(ints),
                "rule": "explicit",
                "delegate": delegate,
                "site_lineno": call.lineno,
            }

    q = channel_default_param.get(delegate)
    if q is not None:
        q_value = kwargs.get(q)
        if q_value is not None:
            n = _display_length(q_value)
            if n is not None and n >= 1:
                return {
                    "channels": list(range(n)),
                    "rule": "arity_default",
                    "delegate": delegate,
                    "site_lineno": call.lineno,
                }
    return None  # rule 5: otherwise Top.


def _delegate_channel_bindings(
    receiver_node: ast.ClassDef, channel_default_param: dict[str, str], channel_kwarg: str | None
) -> dict[str, dict[str, dict[str, Any]]]:
    """P9: `method_name -> {delegate_name: binding}` for every method K of
    `receiver_node`, over every depth-0 `self.<delegate>(...)` call site
    rule 1's singleton test admits (a delegate named zero times never
    enters the dict at all; named more than once is dropped here, both
    collapsing to the same "absent -> Top" outcome the JSON payload uses,
    §13.5.3).
    """
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for member in ast.iter_child_nodes(receiver_node):
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        by_name: dict[str, list[ast.Call]] = {}
        for call in _iter_depth0_calls(member):
            func = call.func
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "self":
                by_name.setdefault(func.attr, []).append(call)
        bindings: dict[str, dict[str, Any]] = {}
        for delegate, sites in by_name.items():
            if len(sites) != 1:
                continue  # rule 1: zero handled by absence above; >1 here.
            binding = _bound_channels_from_call(sites[0], delegate, channel_default_param, channel_kwarg)
            if binding is not None:
                bindings[delegate] = binding
        if bindings:
            out[member.name] = bindings
    return out


def compute_delegate_channel_bindings(
    receiver_node: ast.ClassDef, channel_default_param: dict[str, str], channel_kwarg: str | None
) -> dict[str, dict[str, dict[str, Any]]]:
    """Public alias of `_delegate_channel_bindings` -- exposed (not
    `_`-prefixed) because AC-13.15(i)'s five negative fixtures and the
    rule-2/rule-4 fixtures exercise this function directly against
    synthetic `ast.ClassDef` bodies, not through the whole survey pipeline.
    """
    return _delegate_channel_bindings(receiver_node, channel_default_param, channel_kwarg)


# ---------------------------------------------------------------------------
# §10.2.5 -- the channel bridge, and §10.2.6's tip-loading / tip-requiring /
# tip-dropping family selection (AC-10.10).
# ---------------------------------------------------------------------------


def _one_hop_delegate_name(
    k_rec: SurveyRecord | None,
    index: dict[Qualkey, SurveyRecord],
    channel_attr: str,
    method: str,
) -> str | None:
    """260903 (spec §13.5.2, P9): the FIRST (declaration-order) name in
    `k_rec.delegates_to` that resolves to a record whose OWN
    `dropped_calls` directly contains the bridge-shape match for `method`
    (e.g. `get_tip`) -- i.e. the one-hop delegate D through which THIS
    guard was actually inherited. Declaration order, deliberately NOT
    `_walk_closure`'s own traversal order (its LIFO frontier visits a
    node's `delegates_to` in REVERSE): when two delegates both bridge to
    the same tracker method (e.g. `transfer`'s `aspirate` AND `dispense`
    both reaching `TipTracker.get_tip`), this resolves the tie to
    whichever K's OWN source lists first -- `aspirate`, ahead of
    `dispense`, for `transfer` at the current pin (AC-13.15(i)).
    """
    if k_rec is None:
        return None
    for name in k_rec.delegates_to:
        resolved = resolve(name, k_rec, index)
        if resolved is None:
            continue
        resolved_rec = index.get(resolved)
        if resolved_rec is None:
            continue
        # (260903, T25) `dropped_calls` entries are `DroppedCall` records --
        # match on `.expr`, same regex, same semantics.
        for dropped in resolved_rec.dropped_calls:
            m = _BRIDGE_SHAPE_RE.match(dropped.expr)
            if m is not None and m.group(1) == channel_attr and m.group(3) == method:
                return name
    return None


def compute_channel_bridge(
    entry: Qualkey,
    index: dict[Qualkey, SurveyRecord],
    *,
    receiver_state: ReceiverState,
    stamp: Any,
) -> tuple[list[dict[str, Any]], str | None]:
    """§10.2.5: walk `entry`'s SAME depth-tracked `delegates_to` closure
    `derive_contract` walks, matching every `dropped_calls` entry against
    `self.<channel_attr>[<name>].<method>`. Returns
    `(channel_guards_json, channel_effect)` where `channel_effect` is
    `None` (E3, no bridge at all), `"HAS_TIP"`/`"NO_TIP"` (E2, exactly one
    agreeing depth-0 effect), or `"widen"` (E4.2 deep-only or E4.3
    conflicting-depth-0, per §10.2.4/§10.4 -- both collapse to the SAME
    transfer-function outcome, so the evaluator does not need to
    distinguish them).

    260903 (spec §13.5.2, P9): a guard reached at closure `depth == 1` was
    inherited through exactly ONE `delegates_to` hop -- `key` (the visited
    record's own `(module, qualname)` at that step) IS `entry`'s one-hop
    delegate D, so its bare method name is looked up, together with
    `entry`'s own bare method name K, in `receiver_state
    .delegate_channel_binding` (built once per receiver, purely
    syntactically, by `compute_delegate_channel_bindings`). A hit attaches
    an additive `bound_channels` key to the guard (§13.5.3); a miss leaves
    the guard exactly as today (`⊤`, by omission). `depth != 1` (a direct
    depth-0 bridge, or a chain more than one hop deep) is out of P9's
    stated scope (§13.5.2: "a delegates_to hop", singular) and never gets
    `bound_channels`.
    """
    channel_guards: list[dict[str, Any]] = []
    depth0_effects: set[str] = set()
    any_deep_effect = False
    seen: set[tuple[int, str]] = set()
    k_bare = entry[1].rsplit(".", 1)[-1]
    k_rec = index.get(entry)

    for rec, _key, depth in _walk_closure(entry, index):
        if rec is None:
            continue
        # (260903, T25) `dropped_calls` entries are `DroppedCall` records --
        # match on `.expr`; `expr` itself is unchanged below (still the
        # bare string the rest of this loop, and the `"via"` payload key,
        # use).
        for dropped in rec.dropped_calls:
            expr = dropped.expr
            # HM-24, pattern 1: the ONE canonical bridge-shape regex,
            # checked against THIS receiver's own `channel_attr` (group 1)
            # -- not a fresh per-call `re.compile`.
            m = _BRIDGE_SHAPE_RE.match(expr)
            if m is None or m.group(1) != receiver_state.channel_attr:
                continue
            method = m.group(3)
            c_key: Qualkey = (receiver_state.tracker_module, f"{receiver_state.tracker_class}.{method}")
            if c_key not in index:
                continue
            if (depth, method) in seen:
                continue
            seen.add((depth, method))

            method_contract = derive_contract(
                receiver_state.tracker_module, f"{receiver_state.tracker_class}.{method}", index, stamp=stamp
            )
            for guard in method_contract.guards:
                guard_json: dict[str, Any] = {
                    "condition": guard.condition,
                    "kind": guard.kind,
                    "raises": guard.raises,
                    "free_vars": list(guard.free_vars),
                    "scope_trail": list(guard.scope_trail),
                    "depth": depth,
                    "site": {
                        "file": guard.site.file,
                        "lineno": guard.site.lineno,
                        "qualname": guard.site.qualname,
                    },
                    "via": expr,
                }
                if depth == 1:
                    delegate_name = _one_hop_delegate_name(k_rec, index, receiver_state.channel_attr, method)
                    if delegate_name is not None:
                        binding = receiver_state.delegate_channel_binding.get(k_bare, {}).get(delegate_name)
                        if binding is not None:
                            guard_json["bound_channels"] = dict(binding)
                channel_guards.append(guard_json)

            effect = receiver_state.effects.get(method)
            if effect is not None:
                if depth == 0:
                    depth0_effects.add(effect)
                else:
                    any_deep_effect = True

    if len(depth0_effects) == 1:
        channel_effect: str | None = next(iter(depth0_effects))
    elif len(depth0_effects) >= 2 or any_deep_effect:
        channel_effect = "widen"
    else:
        channel_effect = None
    return channel_guards, channel_effect


@dataclass(frozen=True, slots=True)
class TipFamilies:
    """§10.2.6/AC-10.10: the three derived method-name sets, published (not
    asserted) per anchored receiver class.
    """

    tip_loading: tuple[str, ...] = ()
    tip_requiring: tuple[str, ...] = ()
    tip_dropping: tuple[str, ...] = ()


def _guard_demanded_state(condition: str | None, bool_view_attr: str) -> str | None:
    """§10.2.6's classification of one raise_guard's atom into which state
    it DEMANDS (the state under which the guard does NOT fire, i.e. the
    precondition for the call to be legal): a `BoolView` atom (fires when
    HAS_TIP) demands `"NO_TIP"`; a `NullCheck(is_none=True)` atom (fires
    when NO_TIP) demands `"HAS_TIP"`; a `NullCheck(is_none=False)` atom
    (fires when HAS_TIP) demands `"NO_TIP"`. Returns `None` for anything
    that doesn't parse to one of the three atom productions -- this is a
    REPORTING classifier (AC-10.10), independent of (but structurally
    identical to) `plr_sema.check.tipstate`'s evaluator-side atom parser.
    """
    if condition is None:
        return None
    try:
        node = ast.parse(condition, mode="eval").body
    except SyntaxError:
        return None
    if _is_self_attr(node, bool_view_attr) or (
        isinstance(node, ast.Attribute) and node.attr == bool_view_attr
    ):
        return "NO_TIP"
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
        op = node.ops[0]
        right = node.comparators[0]
        if isinstance(op, (ast.Is, ast.IsNot)) and isinstance(right, ast.Constant) and right.value is None:
            if isinstance(op, ast.Is):
                return "HAS_TIP"  # fires when the field IS None (NO_TIP) -> demands HAS_TIP
            return "NO_TIP"  # fires when the field is NOT None (HAS_TIP) -> demands NO_TIP
    return None


def compute_tip_families(
    contract_entries: dict[str, dict[str, Any]],
    *,
    receiver_class: str,
    receiver_state: ReceiverState,
) -> TipFamilies:
    """§10.2.6: derived directly from the ALREADY-BUILT contract table (own
    `guards` + additive `channel_guards`, and the additive `channel_effect`)
    -- no re-walking of the closure. `f"{receiver_class}.<method>"` keys are
    scanned; a colliding (disambiguated, `@module:lineno`-suffixed) key is
    skipped (§7.2's `build_contract_keys` note: unreachable via
    `receiver_type.method_name` lookup anyway, so it cannot appear as a
    real `CALL.method` either).
    """
    tip_state_exceptions = frozenset(receiver_state.tip_state_exceptions)
    loading: set[str] = set()
    requiring: set[str] = set()
    dropping: set[str] = set()
    prefix = f"{receiver_class}."
    for key, entry in contract_entries.items():
        if not key.startswith(prefix) or "@" in key:
            continue
        method = key[len(prefix) :]
        all_guards = list(entry.get("guards", ())) + list(entry.get("channel_guards", ()))
        for g in all_guards:
            if g.get("kind") != "raise_guard" or g.get("raises") not in tip_state_exceptions:
                continue
            demanded = _guard_demanded_state(g.get("condition"), receiver_state.bool_view_attr)
            if demanded == "NO_TIP":
                loading.add(method)
            elif demanded == "HAS_TIP":
                requiring.add(method)
        channel_effect = entry.get("channel_effect")
        if channel_effect == "HAS_TIP":
            loading.add(method)
        if channel_effect == "NO_TIP":
            dropping.add(method)
    return TipFamilies(
        tip_loading=tuple(sorted(loading)),
        tip_requiring=tuple(sorted(requiring)),
        tip_dropping=tuple(sorted(dropping)),
    )


# ---------------------------------------------------------------------------
# The volume family (spec 260903_plr-sema-volume-increment.md §14.0.1/§14.4,
# T24, backlog #4958). B1, B2 and P1c feed a BRIDGE-ONLY map --
# `derive_receiver_states` above is UNTOUCHED (AC-14.1(iii)): none of the
# functions in this section are called from it, and its own receiver-
# selection input at `derive_receiver_states`'s own `_annotated_attributes`
# call remains that function's result and nothing else.
#
# **What T24 shipped and what T25 adds (§14.0's own gate).** T24 built
# `volume_guards` -- via/cell_param/amount_param/direction/for_span -- but
# attached NO `caller_scope`/`caller_lineno` (P10 was undischarged: the
# survey's `dropped_calls` was still a bare `list[str]`, so there was no
# scope/lineno to attach). T25 (§14.0.2) migrates the survey schema and
# wires P10 as a CONSUMER of it -- see `compute_volume_bridge` below -- and
# adds the generalised conditional-guard rule plus R1 (§14.6) as pure,
# importable functions. Neither T24 nor T25 constructs a `Finding` or wires
# anything into `check/` (no `check/volumestate.py` exists yet, T26's job),
# so §14.0's normative gate -- a landed bridge alone must never let the
# analyzer construct an ungated volume `WILL_FAIL` -- is respected by
# construction, not by restraint.
# ---------------------------------------------------------------------------


def build_plr_class_index(plr_pkg_root: Path) -> tuple[dict[str, ast.ClassDef], dict[str, str]]:
    """The same "P1 class index" (every top-level class across the whole PLR
    source tree, first definition wins) `derive_receiver_states` builds
    internally for itself -- duplicated here, not imported from it, exactly
    as `tests/test_derive.py::_class_index_from_root` already duplicates it
    for its own AC-12.1 tests. Two independent copies of a ~15-line loop
    over already-public helpers is the DELIBERATE choice AC-14.1(iii) forces:
    `derive_receiver_states`'s own body must stay untouched, so the volume
    family's whole-tree scan cannot be threaded through it.

    Returns `(class_nodes, class_modules)`: the class index P1c/P7 need to
    resolve a bridged constructor call's callee and a tracker method's own
    module (for `derive_contract`'s `(module, qualname)` key), respectively.
    """
    class_nodes: dict[str, ast.ClassDef] = {}
    class_modules: dict[str, str] = {}
    for file in _iter_plr_source_files(plr_pkg_root):
        try:
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file))
        except (SyntaxError, UnicodeDecodeError):
            continue
        module = _module_name_for_plr_file(file, plr_pkg_root)
        for top in ast.iter_child_nodes(tree):
            if isinstance(top, ast.ClassDef):
                class_nodes.setdefault(top.name, top)
                class_modules.setdefault(top.name, module)
    return class_nodes, class_modules


def build_plr_class_bases_index(plr_pkg_root: Path, class_nodes: dict[str, ast.ClassDef]) -> ClassBasesIndex:
    """The whole-tree base-name index M-INH needs (§17.2, T50): a
    DEDICATED second scan over ``plr_pkg_root`` -- independent of
    ``build_plr_class_index``'s own scan above, which keeps only the
    first-definition-wins ``class_nodes``/``class_modules`` and therefore
    cannot answer "does this bare class name collide across modules?" on
    its own. This function's own pass collects EVERY module that defines
    each bare class name (not just the first), then delegates the actual
    extractor rule and closure-refusal bookkeeping to
    ``plr_sema.derive.build_class_bases_index`` -- the ONE shared,
    generic (no PLR knowledge) implementation
    ``scripts/survey_plr_preconditions.py`` also calls, off its own
    already-parsed file dict, so the two halves §17.2 requires to land
    together can never silently apply two different rules.

    Takes the CALLER's own ``class_nodes`` (rather than re-deriving it)
    so a caller that already built it via ``build_plr_class_index`` above
    -- ``derive/__main__.py``'s ``main()`` -- does not pay for a third
    whole-tree AST walk just to get the same first-definition-wins map
    back.
    """
    class_modules_multi: dict[str, set[str]] = {}
    for file in _iter_plr_source_files(plr_pkg_root):
        try:
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file))
        except (SyntaxError, UnicodeDecodeError):
            continue
        module = _module_name_for_plr_file(file, plr_pkg_root)
        for top in ast.iter_child_nodes(tree):
            if isinstance(top, ast.ClassDef):
                class_modules_multi.setdefault(top.name, set()).add(module)
    frozen_multi = {name: frozenset(mods) for name, mods in class_modules_multi.items()}
    return build_class_bases_index(class_nodes, frozen_multi)


#: (module, qualname, lineno) -> the function/method's own AST node -- the
#: SAME triple `SurveyRecord.module`/`.qualname`/`.lineno` carry, verified
#: against the real survey artifact (260904 T30b): `_record_from_dict`'s
#: `lineno` is `node.lineno` for the exact FunctionDef/AsyncFunctionDef the
#: survey walked (`scripts/survey_plr_preconditions.py`'s own
#: `FunctionPreconditions(..., lineno=node.lineno, ...)`), so this index's
#: key is a direct, collision-safe lookup for "the AST node that produced
#: this SurveyRecord" -- no name-only ambiguity (getter/setter pairs, two
#: same-named module-level functions in different modules) survives keying
#: on the triple.
FunctionIndex = dict[tuple[str, str, int], ast.FunctionDef | ast.AsyncFunctionDef]


def build_plr_function_index(plr_pkg_root: Path) -> FunctionIndex:
    """260904 (spec §15.3/§15.4 D1, T30b): a THIRD independent whole-tree
    AST pass (same deliberate-duplication precedent as
    `build_plr_class_index` alongside `derive_receiver_states`'s own
    internal class-index loop, and `plr_sema.derive.__init__`'s own D3
    pass) -- covers what neither of those two build: MODULE-LEVEL
    functions (`_check_no_lid` has no enclosing class at all) alongside
    every class method, keyed the way `bindings.compute_local_bindings_for_guard`
    and `bindings.param_defaults_from_function` need to look a `SurveyRecord`
    up by its own `(module, qualname, lineno)`.

    First-definition-wins on a KEY collision (should not occur -- the key
    includes `lineno`, so two module-level functions sharing a name in the
    same file, or a getter/setter pair, differ in `lineno` and get distinct
    keys; a real collision would mean two functions literally starting on
    the same line of the same file, which is not writable Python).
    """
    out: FunctionIndex = {}
    for file in _iter_plr_source_files(plr_pkg_root):
        try:
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file))
        except (SyntaxError, UnicodeDecodeError):
            continue
        module = _module_name_for_plr_file(file, plr_pkg_root)
        for top in ast.iter_child_nodes(tree):
            if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.setdefault((module, top.name, top.lineno), top)
            elif isinstance(top, ast.ClassDef):
                for member in ast.iter_child_nodes(top):
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        qualname = f"{top.name}.{member.name}"
                        out.setdefault((module, qualname, member.lineno), member)
    return out


# ---------------------------------------------------------------------------
# T41 (spec 260909_plr-sema-observation-increment.md §16.3) -- the derived
# backend surface: a per-(class, method) table over `build_plr_function_index`
# recording `params`/`has_var_keyword`/`has_var_positional`/`constant_return`.
# ---------------------------------------------------------------------------

#: JSON-safe scalar types (mirrors `bindings._constant_json`'s own
#: restriction -- NOT imported from there, per this module's established
#: "two independent copies of a small helper" convention, see
#: `build_plr_class_index`'s own docstring above).
_JSON_SCALAR_TYPES = (bool, int, float, str, type(None))


@dataclass(frozen=True, slots=True)
class BackendSurfaceEntry:
    """T41: one row of the derived backend surface. ``constant_return`` is
    only meaningful when ``has_constant_return`` is ``True`` -- the JSON
    writer (``derive/__main__.py``) omits the ``"constant_return"`` key
    entirely otherwise, matching this module's own additive-field/omitted-
    key discipline (``param_defaults`` etc.): "no constant return" and "not
    computed at all" both read back as absent via ``.get()``."""

    params: tuple[str, ...]
    has_var_keyword: bool
    has_var_positional: bool
    has_constant_return: bool
    constant_return: Any = None


def backend_surface_entry_to_json(entry: "BackendSurfaceEntry") -> dict[str, Any]:
    """T41: the wire shape for one row -- see ``BackendSurfaceEntry``'s own
    docstring for the ``constant_return`` omission rule."""
    payload: dict[str, Any] = {
        "params": list(entry.params),
        "has_var_keyword": entry.has_var_keyword,
        "has_var_positional": entry.has_var_positional,
    }
    if entry.has_constant_return:
        payload["constant_return"] = entry.constant_return
    return payload


def _constant_return_shape(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[bool, Any]:
    """T41 (§16.3's S1 table, `constant_return`'s own normative box):
    ``(True, value)`` iff ``node.body`` is EXACTLY one statement, that
    statement an ``ast.Return``, and its ``value`` an ``ast.Constant`` whose
    Python value is one of the five JSON-safe scalar types. A docstring
    counts as a statement -- a docstring-plus-return body has ``len(body)
    == 2`` and fails here, deliberately (the spec's own point: this is the
    NARROWEST shape test that decides `:514`, not "the first return wins").
    ``(False, None)`` for anything else, INCLUDING a syntactically-single
    ``ast.Constant`` return whose value is not JSON-safe (bytes, complex,
    ``...``) -- fail-closed, same spirit as ``bindings._constant_json``."""
    body = node.body
    if len(body) != 1:
        return False, None
    (stmt,) = body
    if not isinstance(stmt, ast.Return) or stmt.value is None:
        return False, None
    if not isinstance(stmt.value, ast.Constant):
        return False, None
    value = stmt.value.value
    if not isinstance(value, _JSON_SCALAR_TYPES):
        return False, None
    return True, value


def _has_var_keyword(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return node.args.kwarg is not None


def _has_var_positional(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return node.args.vararg is not None


def _non_default_params_after_self(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    """T41 `params` column: parameter names after ``self``, excluding
    ``*args``/``**kwargs``, that carry no default -- positional-or-keyword
    (posonly + ordinary) params via the same ``defaults``-aligned-to-the-
    end convention ``bindings.param_defaults_from_function`` already uses,
    plus keyword-only params whose own ``kw_defaults`` entry is ``None``
    (a real "no default at all" AST sentinel, not the JSON value ``null``
    -- same distinction that function's own docstring makes).

    Every caller of this function has already survived the C15 absence
    rule (``_backend_surface_row_absent``), so it is never handed a
    decorated definition -- meaning its first positional parameter is
    ``self`` by PLR's own convention. Asserted, not assumed: a candidate
    that is not truly an instance method here would silently miscount
    every rule reading ``params``, and that failure must be loud."""
    args = node.args
    positional = list(args.posonlyargs) + list(args.args)
    assert positional and positional[0].arg == "self", (
        f"{node.name}: expected the first parameter to be 'self', got "
        f"{positional[0].arg if positional else '<none>'} -- backend surface "
        f"candidates are always instance methods that survived the absence rule"
    )
    n_defaults = len(args.defaults)
    offset = len(positional) - n_defaults
    non_default_positional = [a.arg for a in positional[1:offset]]  # [1:] drops self
    non_default_kwonly = [a.arg for a, default in zip(args.kwonlyargs, args.kw_defaults) if default is None]
    return tuple(non_default_positional + non_default_kwonly)


def _backend_surface_row_absent(node: ast.FunctionDef | ast.AsyncFunctionDef, *, n_definitions_at_qualname: int) -> bool:
    """T41's ABSENCE rule (C15, §16.3's normative box, D5b's shared
    soundness gate): a row is absent when ANY of:

    1. ``node.decorator_list`` is non-empty -- ``@property``, ``@x.setter``,
       ``@staticmethod``, ``@classmethod``, ``@abstractmethod``, or any
       other decorator all fall here;
    2. the definition IS a property -- structurally the SAME test as (1)
       for every shape reachable from ``build_plr_function_index`` (a bare
       ``property(...)`` assignment is not itself a ``FunctionDef``, so it
       never becomes a row candidate at all; a getter/setter PAIR sharing a
       qualname is caught by (3)). Kept as its own named clause because the
       spec's own normative box enumerates it separately and says exactly
       this -- not because a second, independent AST test exists for it;
    3. the same ``(module, qualname)`` is defined at more than one lineno
       (``n_definitions_at_qualname > 1``, the caller's own count over
       ``build_plr_function_index``).

    Why this matters (not conservatism for its own sake): ``constant_return``
    is read off the AST and R-CONST claims the value the RUNTIME call
    returns; a non-``functools.wraps`` decorator makes those two different.
    The abstract base's ``can_pick_up_tip`` is ``@abstractmethod``-decorated
    (`external/pylabrobot/pylabrobot/liquid_handling/backends/backend.py:183-187`),
    so it is absent by clause (1) -- the right answer, and asserted by name
    in ``tests/test_derive.py``.
    """
    if node.decorator_list:
        return True
    if n_definitions_at_qualname > 1:
        return True
    return False


def collect_env_ref_method_names(contracts: dict[str, Any]) -> frozenset[str]:
    """T41's ONE closed selection rule, first half (§16.3, C16 -- second
    half deleted at spec_version 2): every DISTINCT last path segment of an
    ``EnvRef`` node reachable in ANY guard's regenerated ``"predicate"``
    JSON, across the WHOLE ``contracts`` table (``derive/__main__.py``'s
    ``build_derived_contracts_payload`` output, i.e. what
    ``derive_contract``/``_guard_to_json`` actually shipped -- not a second,
    independent notion of the predicate shape). Reads the table the same
    way a downstream consumer would: ``predicate_ast.from_json`` on each
    guard's own ``"predicate"`` key, then ``predicate_ast.walk``. This
    function introduces no hand-typed method name and no base-class name --
    ``contracts`` is itself derived.

    **260909 (T49, spec 260909_plr-sema-observation-increment.md §16.1.1/
    §16.3): ALSO scans ``"caller_args"``.** D5b's two site rules read the
    delegate's own runtime "method" identity (`m`) from an `EnvRef` stored
    in a guard's `caller_args` map (T42, an additive field on the SAME
    guard record), never from the guard's own `predicate` -- `_check_args`'s
    `:375`/`:383` predicates reference `missing`/`vars_keyword`/`strictness`,
    never the method itself. Without this half, `LiquidHandlerChatterboxBackend
    .pick_up_tips` (and every other backend's `pick_up_tips`) would never
    become a `n_surface_candidates` row at all -- `pick_up_tips` occurs
    NOWHERE as an `EnvRef` path segment in any guard's own `"predicate"` JSON
    at this pin (measured 0 before this half existed), so D5b's own
    arithmetic (§16.1.1) would be permanently unreachable without it. Every
    `caller_args` VALUE is a `Term` JSON (never a `Predicate`), so this reuses
    the SAME `predicate_ast.from_json`/`predicate_ast.walk` pair -- both are
    total over the whole `Predicate | Term` union, `SetLit` included (G9).

    **260909 (T54, spec 260909_plr-sema-move-family-increment.md S17.1.4,
    round 2's R2-C1): ALSO scans EVERY per-site `args` map of M3's new
    `"caller_args_sites"` field.** A move-family guard sits at depth >= 2
    and never carries a populated `"caller_args"` (M1 clause 6, unrelaxed
    for the single-entry-point-relative field), so without this THIRD scan
    a method name that only ever appears at depth >= 2 -- `drop_resource`,
    reached only through `move_resource`'s own two `_check_args` calls --
    never becomes a `n_surface_candidates` row at all, and the selection
    half of round 2's R2-C1 stays unrepaired regardless of what the
    attachment filter does. Every value in every per-site `args` map is a
    `Term` JSON exactly as `caller_args`'s values are (M3's own
    `compute_caller_args_for_call`), so the walk below is total over them
    by construction and needs no new parser."""
    names: set[str] = set()
    for entry in contracts.values():
        for guard in entry.get("guards", ()):
            predicate_json = guard.get("predicate")
            if predicate_json is not None:
                node = predicate_from_json(predicate_json)
                for sub in predicate_walk(node):
                    if isinstance(sub, EnvRef) and sub.path:
                        names.add(sub.path[-1])
            caller_args_json = guard.get("caller_args")
            if caller_args_json:
                for term_json in caller_args_json.values():
                    term = predicate_from_json(term_json)
                    for sub in predicate_walk(term):
                        if isinstance(sub, EnvRef) and sub.path:
                            names.add(sub.path[-1])
            caller_args_sites = guard.get("caller_args_sites")
            if caller_args_sites:
                for site in caller_args_sites:
                    site_args = site.get("args") if isinstance(site, dict) else None
                    if not site_args:
                        continue
                    for term_json in site_args.values():
                        term = predicate_from_json(term_json)
                        for sub in predicate_walk(term):
                            if isinstance(sub, EnvRef) and sub.path:
                                names.add(sub.path[-1])
    return frozenset(names)


def build_backend_surface(
    function_index: "FunctionIndex",
    selected_method_names: frozenset[str],
) -> tuple[dict[str, "BackendSurfaceEntry"], int, int]:
    """T41 (§16.3): the derived backend surface. Returns ``(rows,
    n_surface_candidates, n_surface_absent_by_c15)`` -- ``n_surface_rows``
    is the caller's ``len(rows)``, and ``candidates - absent == rows`` holds
    by construction (every candidate becomes exactly one row or is counted
    absent; no third outcome).

    **Candidate selection (the ONE closed rule, spec_version 2).** A
    ``(module, qualname, lineno)`` entry of ``function_index`` is a
    candidate iff ``qualname`` names a CLASS method (contains a ``.`` --
    module-level functions are never surface rows) and its last segment is
    a member of ``selected_method_names`` (``collect_env_ref_method_names``'s
    output). **No base-class name, no method list**: ``selected_method_names``
    is derived from the contract table by the caller and never hand-typed
    here; this function does not know or care what ``LiquidHandlerBackend``
    is.

    **Keying.** The bare key is ``qualname`` (already ``"ClassName.method"``,
    exactly the "(class, method)" pair the spec names) when it is unique
    among surviving rows; disambiguated as ``f"{qualname}@{module}:{lineno}"``
    otherwise -- same single, uniform disambiguator ``build_contract_keys``
    already uses for the analogous same-qualname-different-module collision,
    chosen for the identical reason (one rule, not a two-tier one, keeps
    this testable).
    """
    linenos_by_qualkey: dict[tuple[str, str], set[int]] = {}
    for module, qualname, lineno in function_index:
        linenos_by_qualkey.setdefault((module, qualname), set()).add(lineno)

    candidates: list[tuple[str, str, int]] = []
    for module, qualname, lineno in function_index:
        if "." not in qualname:
            continue
        method_name = qualname.rsplit(".", 1)[-1]
        if method_name in selected_method_names:
            candidates.append((module, qualname, lineno))
    candidates.sort()
    n_candidates = len(candidates)

    survivors: list[tuple[str, str, int, BackendSurfaceEntry]] = []
    n_absent = 0
    for module, qualname, lineno in candidates:
        node = function_index[(module, qualname, lineno)]
        n_defs = len(linenos_by_qualkey[(module, qualname)])
        if _backend_surface_row_absent(node, n_definitions_at_qualname=n_defs):
            n_absent += 1
            continue
        has_const, const_value = _constant_return_shape(node)
        entry = BackendSurfaceEntry(
            params=_non_default_params_after_self(node),
            has_var_keyword=_has_var_keyword(node),
            has_var_positional=_has_var_positional(node),
            has_constant_return=has_const,
            constant_return=const_value,
        )
        survivors.append((module, qualname, lineno, entry))

    bare_key_counts: dict[str, int] = {}
    for _module, qualname, _lineno, _entry in survivors:
        bare_key_counts[qualname] = bare_key_counts.get(qualname, 0) + 1

    rows: dict[str, BackendSurfaceEntry] = {}
    for module, qualname, lineno, entry in survivors:
        key = qualname if bare_key_counts[qualname] == 1 else f"{qualname}@{module}:{lineno}"
        assert key not in rows, f"backend surface key collision building rows: {key!r}"
        rows[key] = entry

    assert n_candidates - n_absent == len(rows), (
        f"backend surface candidate/absent/row counts do not reconcile: "
        f"{n_candidates} - {n_absent} != {len(rows)}"
    )
    return rows, n_candidates, n_absent


def probe_method_definitions(function_index: "FunctionIndex", method_name: str) -> tuple[int, int]:
    """T41 (AC-16.2): a generic whole-tree probe -- ``(n_definitions,
    n_constant_return)`` for every ``(module, qualname, lineno)`` entry of
    ``function_index`` whose qualname's last segment equals ``method_name``,
    counted BEFORE the C15 absence rule (a whole-tree fact, independent of
    ``build_backend_surface``'s EnvRef-driven selection) and using the SAME
    shape test (``_constant_return_shape``). ``method_name`` is a
    caller-supplied parameter, never a literal inside this function -- the
    ``can_pick_up_tip`` probe AC-16.2 requires is the CALLER's business
    (``derive/__main__.py``'s regeneration diagnostic, ``tests/test_derive.py``),
    keeping this function itself free of any hand-typed PLR method name."""
    n_definitions = 0
    n_constant_return = 0
    for (module, qualname, lineno), node in function_index.items():
        if "." not in qualname:
            continue
        if qualname.rsplit(".", 1)[-1] != method_name:
            continue
        n_definitions += 1
        has_const, _value = _constant_return_shape(node)
        if has_const:
            n_constant_return += 1
    return n_definitions, n_constant_return


# ---------------------------------------------------------------------------
# B2 (§14.0.1, round-1 O9) -- dataclass class-level field annotations, into
# the bridge-only map. NOT a branch of `_annotated_attributes` (§10.2.1's P1a
# stays self-attr-only, unmodified) -- see the normative box's own
# "first-writer-wins would displace an existing P1a selection" argument.
# ---------------------------------------------------------------------------


def dataclass_field_annotations(class_node: ast.ClassDef) -> dict[str, str]:
    """B2: every `<name>: <annotation>` `AnnAssign` that is a DIRECT
    statement of `class_node.body` (never `ast.walk` -- a method-body
    `self.x: T` must not enter this map, that is P1a's job) whose target is
    a bare `ast.Name` (never `self.<name>` -- that shape is P1a's,
    `_is_self_attr` rejects it here by construction since we never call it).
    First occurrence wins (deterministic), same convention as P1a.
    """
    out: dict[str, str] = {}
    for stmt in class_node.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            unwrapped = _unwrap_annotation(stmt.annotation)
            if unwrapped is not None:
                out.setdefault(stmt.target.id, unwrapped)
    return out


# ---------------------------------------------------------------------------
# P1c (§14.0.1, round-1 O2) -- constructor-call typing through an
# unannotated write, over EVERY method of the class (not just `__init__` --
# `Tip.tracker` is written in `__post_init__`). Fail-closed over the UNION
# of writes to a name anywhere in the class.
# ---------------------------------------------------------------------------


def constructor_call_writes(class_node: ast.ClassDef, class_index: dict[str, ast.ClassDef]) -> dict[str, str]:
    """P1c: for class `class_node`, walks EVERY `ast.FunctionDef`/
    `ast.AsyncFunctionDef` child (never singled out to `__init__`) and
    every `self.<name> = <value>` write anywhere in each (mirrors P1b's own
    `ast.walk`, `_attribute_writers`). A write's `value` is classified as
    `("ctor", <Callee>)` when it is a bare `ast.Call` to an `ast.Name` that
    is a key of `class_index` (the WHOLE-PLR class index P1 builds, not
    just receiver classes -- the same conjunct-1 test §12.1.2's
    `_is_fresh_only_construction` already uses), else `("other", None)`.

    Fail-closed over the UNION of writes (round-1 O2): a name whose distinct
    write-descriptor set has size != 1 anywhere in the class records
    nothing -- this covers "two different constructors", "written both by a
    constructor call and by something else", and "never written by a
    constructor call at all" in one rule, deliberately not just the first
    of those (a name written twice by the identical constructor call is NOT
    penalised: two methods that agree are not "two different constructors").
    """
    per_name: dict[str, set[tuple[str, str | None]]] = {}
    for member in ast.iter_child_nodes(class_node):
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for node in ast.walk(member):
            if not (isinstance(node, ast.Assign) and len(node.targets) == 1):
                continue
            target = node.targets[0]
            if not _is_self_attr(target):
                continue
            value = node.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in class_index:
                descriptor: tuple[str, str | None] = ("ctor", value.func.id)
            else:
                descriptor = ("other", None)
            per_name.setdefault(target.attr, set()).add(descriptor)  # type: ignore[union-attr]
    out: dict[str, str] = {}
    for name, descriptors in per_name.items():
        if len(descriptors) != 1:
            continue  # fail-closed: conflicting writes anywhere in the class.
        (kind, callee) = next(iter(descriptors))
        if kind == "ctor":
            out[name] = callee  # type: ignore[assignment]
    return out


def bridge_type_map(class_node: ast.ClassDef, class_index: dict[str, ast.ClassDef]) -> dict[str, str]:
    """The bridge-only map B2 and P1c both feed (§14.0.1): B2's dataclass
    field annotations, overlaid by P1c's constructor-call writes. "P1c is
    consulted only after B2: an annotated field always wins" -- P1c's
    result is the base, B2's overlays it, so a name B2 admits always wins a
    collision (none is expected at this pin: B2 types dataclass fields on
    the operation classes, P1c types constructor-written attributes on the
    resource classes, and the two populations do not overlap).
    """
    p1c = constructor_call_writes(class_node, class_index)
    b2 = dataclass_field_annotations(class_node)
    return {**p1c, **b2}


# ---------------------------------------------------------------------------
# P8 (§14.4) -- the operand-pairing idiom, extended to also record the
# comprehension's own assignment target (what B1 binds a `for` loop
# against).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _ComprehensionBinding:
    """One P8 match: `assign_target = [O(k=a_i, ...) for ..., a_i, ... in
    zip(..., param_i, ...)]`. `pairings` maps a keyword `k` of `O` to
    `(zip_name, is_local)` -- `zip_name` is the `ai` name at the matching
    zip position, and `is_local` is true when `ai` is NOT a parameter of
    the enclosing method (P8's "local pairing", round-1 D1)."""

    element_class: str
    pairings: dict[str, tuple[str, bool]]
    lineno: int


def operand_pairing_idiom(method: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, _ComprehensionBinding]:
    """P8: every `<target> = [O(k1=a1, ...) for a1, ... in zip(p1, ...)]` (or
    `GeneratorExp`) assignment in `method`'s body, keyed by `<target>`'s own
    name (`assign_target`, e.g. `"aspirations"`) -- what B1 binds a `for`
    loop's `iter` against. Matches a single-target `ast.Assign` to a bare
    `ast.Name` whose value is a `ListComp`/`GeneratorExp` with exactly one,
    non-async, filter-free generator over `zip(p1, ..., pn)`, whose element
    is an `ast.Call` to a bare `ast.Name` class `O` with keyword arguments.
    Each keyword `k` whose value is one of the comprehension's own bound
    names is recorded, paired to the zip position's own argument `pi` --
    ONLY when `pi` is itself an `ast.Name`.

    **Measured deviation from the spec's literal text (§14.4's own P8 box:
    "zip(a1, …, an) where each ai is an ast.Name").** At the pin,
    `LiquidHandler.aspirate`/`dispense`'s own `zip(...)` call's LAST
    argument is `mix or [None] * len(use_channels)` (`liquid_handler.py
    :1026`/`:1226`) -- an `ast.BoolOp`, not a bare `ast.Name`. A whole-zip-
    call precondition ("every ai is a Name") would make P8 never match
    either method's real comprehension at all, which would silently empty
    the ENTIRE volume family (the exact G1 gap §14.0 exists to close).
    Reading "each ai is an ast.Name" as a PER-KEYWORD precondition instead
    -- record `(O.k -> ai)` only for the keywords whose own zip position IS
    a bare Name, and simply do not pair a keyword whose position is some
    other expression (here, `mix`) -- is measured to be the only reading
    under which the bridge fires at all, and is what this function
    implements; the `mix` keyword's pairing is one the AC never needs
    (neither guard's `cell_param`/`amount_param` is `mix`), so nothing this
    increment ships depends on the relaxed case being wrong.
    """
    param_names = {a.arg for a in method.args.args} | {a.arg for a in method.args.kwonlyargs}
    out: dict[str, _ComprehensionBinding] = {}
    for node in ast.walk(method):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
            continue
        comp = node.value
        if not isinstance(comp, (ast.ListComp, ast.GeneratorExp)):
            continue
        if len(comp.generators) != 1:
            continue
        gen = comp.generators[0]
        if gen.ifs or gen.is_async:
            continue
        iter_call = gen.iter
        if not (
            isinstance(iter_call, ast.Call) and isinstance(iter_call.func, ast.Name) and iter_call.func.id == "zip"
        ):
            continue
        if not iter_call.args:
            continue
        zip_args = iter_call.args

        target = gen.target
        if isinstance(target, ast.Tuple):
            if len(target.elts) != len(zip_args) or not all(isinstance(e, ast.Name) for e in target.elts):
                continue
            target_names = [e.id for e in target.elts]  # type: ignore[union-attr]
        elif isinstance(target, ast.Name):
            if len(zip_args) != 1:
                continue
            target_names = [target.id]
        else:
            continue

        elt = comp.elt
        if not (isinstance(elt, ast.Call) and isinstance(elt.func, ast.Name)):
            continue
        element_class = elt.func.id

        pairings: dict[str, tuple[str, bool]] = {}
        for kw in elt.keywords:
            if kw.arg is None or not isinstance(kw.value, ast.Name):
                continue
            if kw.value.id not in target_names:
                continue
            zip_arg = zip_args[target_names.index(kw.value.id)]
            if not isinstance(zip_arg, ast.Name):
                continue  # this zip position is not a bare Name -- skip this keyword only.
            pairings[kw.arg] = (zip_arg.id, zip_arg.id not in param_names)

        out.setdefault(node.targets[0].id, _ComprehensionBinding(  # type: ignore[union-attr]
            element_class=element_class, pairings=pairings, lineno=node.lineno
        ))
    return out


# ---------------------------------------------------------------------------
# B1 (§14.0.1) -- for-loop-over-comprehension-output binding, at depth 0 in
# the method body (excluding nested function/lambda defs), with the two
# fail-closed cases: a tuple `for` target, and more than one `ast.For` over
# the same P8-produced name.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class B1Binding:
    """One B1 binding: `<name> : <element_class>`, plus the binding
    `ast.For` node's own `for_span` (`[lineno, end_lineno]`, §14.6's R1
    position-containment key) and the P8 assignment target it was bound
    against (`source_name`, e.g. `"aspirations"` -- what `operand_pairing_
    idiom`'s own map is keyed on, so a bridge match can look its pairings
    back up)."""

    element_class: str
    for_span: tuple[int, int]
    source_name: str


def for_over_comprehension_output(
    method: ast.FunctionDef | ast.AsyncFunctionDef, p8_matches: dict[str, _ComprehensionBinding]
) -> dict[str, B1Binding]:
    """B1: every `for <name> in <p8_target>:` at depth 0 in `method`'s body
    (recurses through `If`/`For`/`While`/`Try`/`With` bodies -- depth 0
    means "not inside a nested function/lambda def", not "top-level
    statement only" -- but never descends into an `ast.FunctionDef`/
    `ast.AsyncFunctionDef`/`ast.Lambda`, which this walker simply never
    visits). Binds `<name> : p8_matches[<p8_target>].element_class`.

    Fail-closed (two cases, §14.0.1's own box): if more than one depth-0
    `ast.For` iterates the SAME `<p8_target>` name, or the (single) such
    `ast.For`'s target is a tuple rather than a bare `ast.Name`, B1 binds
    nothing for that name. An `ast.AsyncFor` is never recognised (B1 is
    stated over `ast.For` only) and is simply never collected as a
    candidate -- so it neither binds nor poisons another name's count.
    """
    candidates: dict[str, list[ast.For]] = {}

    def _walk(stmts: list[ast.stmt]) -> None:
        for stmt in stmts:
            if isinstance(stmt, ast.For):
                if isinstance(stmt.iter, ast.Name) and stmt.iter.id in p8_matches:
                    candidates.setdefault(stmt.iter.id, []).append(stmt)
                _walk(stmt.body)
                _walk(stmt.orelse)
            elif isinstance(stmt, ast.If):
                _walk(stmt.body)
                _walk(stmt.orelse)
            elif isinstance(stmt, ast.Try):
                _walk(stmt.body)
                _walk(stmt.orelse)
                _walk(stmt.finalbody)
                for handler in stmt.handlers:
                    _walk(handler.body)
            elif isinstance(stmt, (ast.With, ast.AsyncWith)):
                _walk(stmt.body)
            elif isinstance(stmt, ast.While):
                _walk(stmt.body)
                _walk(stmt.orelse)
            # ast.AsyncFor, ast.FunctionDef, ast.AsyncFunctionDef and every
            # other statement kind: not descended into (AsyncFor is not an
            # ast.For B1 recognises; the two def kinds are the "excluding
            # nested function definitions" clause; everything else has no
            # nested statement list worth walking for this idiom).

    _walk(method.body)

    out: dict[str, B1Binding] = {}
    for source_name, fors in candidates.items():
        if len(fors) != 1:
            continue  # fail-closed: more than one ast.For over this name.
        for_node = fors[0]
        if not isinstance(for_node.target, ast.Name):
            continue  # fail-closed: tuple target.
        binding = p8_matches[source_name]
        assert for_node.end_lineno is not None
        out[for_node.target.id] = B1Binding(
            element_class=binding.element_class,
            for_span=(for_node.lineno, for_node.end_lineno),
            source_name=source_name,
        )
    return out


# ---------------------------------------------------------------------------
# P7 (§14.4) -- the volume anchor: a class `C`'s used-volume/free-volume
# accessor pair and the P7-anchored field the AugAssign direction rule
# (below) reads. Fail-closed: zero or ambiguous candidates emit nothing.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VolumeAnchor:
    used_volume_accessor: str
    free_volume_accessor: str
    anchored_field: str
    #: 260903 T27 (spec §14.6/§14.8, round-1 defender's `_apply_seed`
    #: residue): the unique method that unconditionally writes
    #: `anchored_field` from a bare parameter at statement position --
    #: `None` when zero or more than one candidate exists (fail-closed,
    #: same discipline as the accessor pair above). Published so
    #: `check/volumestate.py`'s seed recognition can read "is this call the
    #: class's own setter" off the derived table instead of hard-typing
    #: `"VolumeTracker"`/`"set_volume"`.
    setter: str | None


def _init_written_fields(class_node: ast.ClassDef) -> frozenset[str]:
    """Every `self.<name>` written in `class_node.__init__`, by either
    `ast.Assign` or `ast.AnnAssign` (`VolumeTracker.__init__`'s own
    `self._callback: Optional[...] = None` is the `AnnAssign` case; P1b's
    `_attribute_writers` is `ast.Assign`-only and is not reused here for
    that reason -- same "P1c does not inherit P1b's narrower shape"
    argument the module docstring already makes for the writer-index
    precedent, applied one level up)."""
    for member in ast.iter_child_nodes(class_node):
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == "__init__":
            names: set[str] = set()
            for node in ast.walk(member):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if _is_self_attr(target):
                            names.add(target.attr)  # type: ignore[union-attr]
                elif isinstance(node, ast.AnnAssign) and node.value is not None and _is_self_attr(node.target):
                    names.add(node.target.attr)  # type: ignore[union-attr]
            return frozenset(names)
    return frozenset()


def _raise_exception_name(raise_node: ast.Raise) -> str | None:
    exc = raise_node.exc
    if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
        return exc.func.id
    if isinstance(exc, ast.Name):
        return exc.id
    return None


def _volume_anchor(class_node: ast.ClassDef, volume_state_exceptions: frozenset[str]) -> VolumeAnchor | None:
    """P7's fail-closed anchor test for one class.

    **Candidate accessors** (conjunct 1): a zero-argument (`self` only)
    method whose body is a single `ast.Return` of a non-`None` expression
    that mentions >=1 `self.<F>` for `<F>` in `class_node.__init__`'s own
    written fields (`_init_written_fields`). `bare_field` is recorded when
    the WHOLE return expression is exactly `self.<F>` (nothing else) --
    `get_used_volume`'s `return self.pending_volume` qualifies;
    `get_free_volume`'s `return self.max_volume - self.get_used_volume()`
    is a candidate accessor (it mentions `self.max_volume`) but is NOT a
    bare-field one.

    **Raise guards** (conjunct 2): for every method (own params excluding
    `self`), every `ast.If` with an `ast.Compare` test whose (possibly
    nested) body contains an `ast.Raise` of a class in
    `volume_state_exceptions`, AND whose test mentions >=1 candidate
    accessor call (`self.<accessor>()`) AND >=1 of the method's own
    parameter names. Each such accessor is recorded as "referenced".

    **The used/free split, derived without naming either exception class**
    (AC-14.2(iii) forbids `"TooLittleLiquidError"`/`"TooLittleVolumeError"`
    as literals here): the used-volume accessor is the UNIQUE referenced
    accessor with a `bare_field` (the "direct" accessor); the free-volume
    accessor is the unique OTHER referenced accessor. Ambiguity (not
    exactly one of either) or zero referenced accessors at all fails
    closed, returning `None` -- the same "zero or >=1 ambiguous candidate"
    discipline §14.4's own box states for the used-volume half, extended
    symmetrically to the free-volume half (undisclosed by the letter of the
    box, but the same soundness argument: an ambiguous free-volume accessor
    is exactly as dangerous to the direction rule as an ambiguous
    used-volume one, and this class does not trip it at the pin either way,
    §14.4's own measured expectation).
    """
    init_fields = _init_written_fields(class_node)
    accessor_bare_field: dict[str, str | None] = {}
    for member in ast.iter_child_nodes(class_node):
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = member.args
        if args.vararg or args.kwarg or args.kwonlyargs or args.posonlyargs or args.defaults:
            continue
        if len(args.args) != 1 or args.args[0].arg != "self":
            continue
        body = [s for s in member.body if not _is_docstring_stmt(s)]
        if len(body) != 1 or not isinstance(body[0], ast.Return) or body[0].value is None:
            continue
        value = body[0].value
        referenced_fields = {
            node.attr  # type: ignore[union-attr]
            for node in ast.walk(value)
            if _is_self_attr(node) and node.attr in init_fields  # type: ignore[union-attr]
        }
        if not referenced_fields:
            continue
        bare_field = value.attr if (_is_self_attr(value) and value.attr in init_fields) else None  # type: ignore[union-attr]
        accessor_bare_field[member.name] = bare_field

    referenced: dict[str, set[str]] = {}
    for member in ast.iter_child_nodes(class_node):
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        own_params = {a.arg for a in member.args.args if a.arg != "self"}
        for node in ast.walk(member):
            if not (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)):
                continue
            raise_names = {_raise_exception_name(s) for s in ast.walk(node) if isinstance(s, ast.Raise)}
            raise_names.discard(None)
            if not (raise_names & volume_state_exceptions):
                continue
            accessor_calls = {
                n.func.attr  # type: ignore[union-attr]
                for n in ast.walk(node.test)
                if isinstance(n, ast.Call)
                and _is_self_attr(n.func)  # type: ignore[arg-type]
                and n.func.attr in accessor_bare_field  # type: ignore[union-attr]
            }
            param_refs = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name) and n.id in own_params}
            if not accessor_calls or not param_refs:
                continue
            for accessor in accessor_calls:
                referenced.setdefault(accessor, set()).update(raise_names & volume_state_exceptions)

    direct = {a for a in referenced if accessor_bare_field.get(a) is not None}
    if len(direct) != 1:
        return None
    used_volume_accessor = next(iter(direct))
    anchored_field = accessor_bare_field[used_volume_accessor]
    if anchored_field is None:
        return None
    other = {a for a in referenced if a != used_volume_accessor}
    if len(other) != 1:
        return None
    free_volume_accessor = next(iter(other))
    setter = _volume_setter(class_node, anchored_field)
    return VolumeAnchor(
        used_volume_accessor=used_volume_accessor,
        free_volume_accessor=free_volume_accessor,
        anchored_field=anchored_field,
        setter=setter,
    )


def _volume_setter(class_node: ast.ClassDef, anchored_field: str) -> str | None:
    """260903 T27 (spec §14.8, round-1 defender's `_apply_seed` residue):
    the unique method of `class_node`, over exactly one non-`self`
    parameter `<p>`, whose body contains -- as a DIRECT (depth-0, i.e.
    unconditional: not nested inside any `If`/`For`/`While`/`Try`)
    statement -- an `ast.Assign` whose sole target is `self.<anchored_field>`
    and whose value is the bare `ast.Name(<p>)`. Two or more `Assign`
    targets on one statement (`self.a = self.b = p`) do not qualify --
    "sole target" is part of the shape, not a simplification.

    **Measured expectation:** `VolumeTracker.set_volume` (`volume_tracker
    .py:66-72`) -- `def set_volume(self, volume): self.volume = volume;
    self.pending_volume = volume; ...` -- has exactly one parameter
    (`volume`) and a depth-0 `self.pending_volume = volume` (the anchored
    field is `pending_volume`, §14.4's measured expectation). No other
    method of `VolumeTracker` has both a single parameter and a depth-0
    assignment of `pending_volume` from it: `remove_liquid`/`add_liquid`
    write it via `ast.AugAssign` (`-=`/`+=`, not `Assign`, and not from a
    bare copy of their own parameter), `__init__` takes three parameters,
    and `set_liquids` never assigns `pending_volume` directly at all (it
    delegates to `set_volume`). Fail-closed: zero or >=2 candidates return
    `None`, same discipline as the accessor pair above.
    """
    candidates: set[str] = set()
    for member in ast.iter_child_nodes(class_node):
        if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        args = member.args
        if args.vararg or args.kwarg or args.kwonlyargs or args.posonlyargs:
            continue
        params = [a.arg for a in args.args if a.arg != "self"]
        if len(params) != 1:
            continue
        (param,) = params
        body = [s for s in member.body if not _is_docstring_stmt(s)]
        writes_from_param = any(
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and _is_self_attr(stmt.targets[0], anchored_field)
            and isinstance(stmt.value, ast.Name)
            and stmt.value.id == param
            for stmt in body
        )
        if writes_from_param:
            candidates.add(member.name)
    if len(candidates) != 1:
        return None
    return next(iter(candidates))


def compute_volume_anchors(
    class_nodes: dict[str, ast.ClassDef], volume_state_exceptions: frozenset[str]
) -> dict[str, VolumeAnchor]:
    """P7 run over every class in the whole-tree index: `{class_name:
    VolumeAnchor}` for every class that is not fail-closed. Measured at the
    pin: `{"VolumeTracker": VolumeAnchor(used_volume_accessor=
    "get_used_volume", free_volume_accessor="get_free_volume",
    anchored_field="pending_volume", setter="set_volume")}` -- published by
    the T24/T27 fixers, not assumed here.
    """
    out: dict[str, VolumeAnchor] = {}
    for name, node in class_nodes.items():
        anchor = _volume_anchor(node, volume_state_exceptions)
        if anchor is not None:
            out[name] = anchor
    return out


def _volume_direction(method: ast.FunctionDef | ast.AsyncFunctionDef, anchored_field: str) -> str | None:
    """The `ast.AugAssign` direction rule (§14.4, round-1 O10): the sign of
    `method`'s `ast.AugAssign` on `self.<anchored_field>` -- `ast.Sub` is
    `"decreasing"`, `ast.Add` is `"increasing"`. No such write, writes of
    both signs, or a write with any other operator: `None` (carries the
    guard, no transfer -- V2, T26's job, applies no update)."""
    signs: set[str] = set()
    for node in ast.walk(method):
        if isinstance(node, ast.AugAssign) and _is_self_attr(node.target, anchored_field):
            if isinstance(node.op, ast.Sub):
                signs.add("decreasing")
            elif isinstance(node.op, ast.Add):
                signs.add("increasing")
            else:
                signs.add("other")
    if len(signs) == 1:
        (only,) = signs
        return only if only in ("decreasing", "increasing") else None
    return None


# ---------------------------------------------------------------------------
# The extended four-segment volume bridge (§14.4, a second HM-24 pattern):
# `<name>.<field>.<attr>.<method>`, `<name>` bound by B1 (the only source
# exercised at this pin -- see the module note below), `<field>` typed by
# the bridge-only map to a class `C1`, `<attr>` typed by `C1`'s OWN
# bridge-only map to a P7-anchored class `C`, `f"{C}.{method}"` a real
# contract entry. Attaches every guard of `C.<method>` to `K` as a volume
# guard.
#
# **Scope note.** §14.4's own box says `<name>` may be bound "either by a
# P8 comprehension target or by §14.0.1's B1" -- the first alternative
# (`<name>` itself one of P8's own zip-bound names, e.g. `r`/`v`/`o`) is
# NOT exercised anywhere at this pin (`op`, the only `<name>` any real
# `dropped_calls` entry uses, is B1-bound, never a bare zip target -- G1's
# own finding). This module implements the B1 path only; a direct
# P8-comprehension-target `<name>` resolver is not built, since there is no
# real match to measure it against and no AC exercises it. Documented here
# rather than silently narrowed, per T24's own "publish what you measured,
# do not reconcile to the document" instruction.
# ---------------------------------------------------------------------------

_VOLUME_BRIDGE_SHAPE_RE = re.compile(r"^(\w+)\.(\w+)\.(\w+)\.(\w+)$")


def _caller_scope_for_expr(
    expr: str, dropped_calls: tuple[DroppedCall, ...]
) -> tuple[list[str] | None, int | None]:
    """P10 (§14.0.2, T25): `(caller_scope, caller_lineno)` for the ONE
    `DroppedCall` record in `dropped_calls` whose `expr` equals `expr`,
    read verbatim (nearest-first, polarity preserved) off that record's own
    `scope_trail`/`lineno`.

    **Fail-closed** to `(None, None)` -- normative box's own words -- when
    zero or more than one record share this `expr` in the same method (an
    ambiguous attachment is not a safer-but-wrong one; it is `null`), or
    when the single matching record predates the schema migration
    (`lineno is None`, produced by `_dropped_call_from_any`'s bare-`str`
    degrade path). Disjoint from the guard's own callee-sourced
    `scope_trail`, which this function never reads or writes.
    """
    matches = [dropped for dropped in dropped_calls if dropped.expr == expr]
    if len(matches) != 1:
        return None, None
    (only,) = matches
    if only.lineno is None:
        return None, None
    return list(only.scope_trail), only.lineno


def compute_volume_bridge(
    entry: Qualkey,
    index: dict[Qualkey, SurveyRecord],
    *,
    receiver_node: ast.ClassDef,
    class_index: dict[str, ast.ClassDef],
    class_modules: dict[str, str],
    volume_anchors: dict[str, VolumeAnchor],
    stamp: Any,
) -> list[dict[str, Any]]:
    """§14.4's extended bridge, for one contract entry `K = entry`.

    Looks up `K`'s own method node in `receiver_node` (K's receiver class),
    runs P8 (`operand_pairing_idiom`) and B1 (`for_over_comprehension_
    output`) over it, then matches `K`'s own SurveyRecord's `dropped_calls`
    (depth 0 -- K's own body, no `delegates_to` closure walk; §14.4's box:
    "reached at depth 0 in K's own body") against the four-segment shape.

    For each match: `<field>` is looked up in the B1-bound element class's
    `bridge_type_map` (B2/P1c); `<attr>` is looked up in THAT class's own
    `bridge_type_map`; the resolved tracker class must be a P7 anchor and
    `f"{tracker_class}.{method}"` a real index entry. `cell_param` is P8's
    pairing for `<field>` (a bare kwarg-name string for a parameter
    pairing, or `{"local": True, "name": <zip_name>}` for a local one --
    round-1 D1); `amount_param` is P8's pairing for the tracker method's
    own non-`self` parameter name (the guard's own free variable), read off
    `<name>`'s SAME comprehension (`operand_pairing_idiom`'s `source_name`
    keys both lookups, so the two pairings can never come from different
    comprehensions). `direction` is `_volume_direction` on the tracker
    method against `VolumeAnchor.anchored_field`. `for_span` is attached
    when the `<name>` binding came through B1 (always, at this pin -- see
    the module note above).
    """
    k_rec = index.get(entry)
    if k_rec is None:
        return []
    method_name = entry[1].rsplit(".", 1)[-1]
    method_node: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    for member in ast.iter_child_nodes(receiver_node):
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) and member.name == method_name:
            method_node = member
            break
    if method_node is None:
        return []

    p8_matches = operand_pairing_idiom(method_node)
    b1_bindings = for_over_comprehension_output(method_node, p8_matches)

    volume_guards: list[dict[str, Any]] = []
    # (260903, T25) `dropped_calls` entries are `DroppedCall` records, and
    # the survey now preserves multiplicity (the same `expr` can appear
    # more than once, at different scopes) -- match on the DISTINCT `expr`s,
    # first-seen order, so a duplicate does not manufacture a second
    # `volume_guards` entry for the same bridge match (that duplication
    # would itself be exactly the ambiguity `_caller_scope_for_expr` fails
    # closed on, attached to a guard nothing else distinguishes).
    seen_exprs: list[str] = []
    seen_exprs_set: set[str] = set()
    for dropped in k_rec.dropped_calls:
        if dropped.expr not in seen_exprs_set:
            seen_exprs_set.add(dropped.expr)
            seen_exprs.append(dropped.expr)

    for expr in seen_exprs:
        m = _VOLUME_BRIDGE_SHAPE_RE.match(expr)
        if m is None:
            continue
        name, field, attr, method = m.groups()

        binding = b1_bindings.get(name)
        if binding is None:
            continue  # <name> not B1-bound (the direct-P8-target path is not implemented -- see module note).

        element_node = class_index.get(binding.element_class)
        if element_node is None:
            continue
        field_type = bridge_type_map(element_node, class_index).get(field)
        if field_type is None:
            continue
        field_class_node = class_index.get(field_type)
        if field_class_node is None:
            continue
        tracker_class = bridge_type_map(field_class_node, class_index).get(attr)
        if tracker_class is None:
            continue

        anchor = volume_anchors.get(tracker_class)
        if anchor is None:
            continue
        tracker_module = class_modules.get(tracker_class)
        if tracker_module is None:
            continue
        c_key: Qualkey = (tracker_module, f"{tracker_class}.{method}")
        if c_key not in index:
            continue

        tracker_class_node = class_index.get(tracker_class)
        tracker_method_node = None
        if tracker_class_node is not None:
            for tmember in ast.iter_child_nodes(tracker_class_node):
                if isinstance(tmember, (ast.FunctionDef, ast.AsyncFunctionDef)) and tmember.name == method:
                    tracker_method_node = tmember
                    break

        direction = (
            _volume_direction(tracker_method_node, anchor.anchored_field) if tracker_method_node is not None else None
        )

        pairing = p8_matches.get(binding.source_name)
        cell_param: Any = None
        if pairing is not None and field in pairing.pairings:
            zip_name, is_local = pairing.pairings[field]
            cell_param = {"local": True, "name": zip_name} if is_local else zip_name

        amount_param: str | None = None
        if pairing is not None and tracker_method_node is not None:
            guard_params = [a.arg for a in tracker_method_node.args.args if a.arg != "self"]
            if len(guard_params) == 1 and guard_params[0] in pairing.pairings:
                zip_name, is_local = pairing.pairings[guard_params[0]]
                if not is_local:
                    amount_param = zip_name

        caller_scope, caller_lineno = _caller_scope_for_expr(expr, k_rec.dropped_calls)

        method_contract = derive_contract(tracker_module, f"{tracker_class}.{method}", index, stamp=stamp)
        for guard in method_contract.guards:
            guard_json: dict[str, Any] = {
                "condition": guard.condition,
                "kind": guard.kind,
                "raises": guard.raises,
                "free_vars": list(guard.free_vars),
                "scope_trail": list(guard.scope_trail),
                "site": {
                    "file": guard.site.file,
                    "lineno": guard.site.lineno,
                    "qualname": guard.site.qualname,
                },
                "via": expr,
                "cell_param": cell_param,
                "amount_param": amount_param,
                "direction": direction,
                # P10 (§14.0.2, T25): attached from K's own dropped_calls
                # record for this `expr`, additively alongside the guard's
                # own callee-sourced `scope_trail` above (never modified --
                # the two facts are kept apart, per the normative box).
                "caller_scope": caller_scope,
                "caller_lineno": caller_lineno,
            }
            if binding.for_span is not None:
                guard_json["for_span"] = list(binding.for_span)
            volume_guards.append(guard_json)
    return volume_guards


# ---------------------------------------------------------------------------
# §14.6 -- the hypothesis gate: the generalised conditional-guard rule and
# R1, its one structural admission (T25). Pure, importable functions with
# no dependency on `check/` -- T26/T27 import `volume_guard_is_unconditional`
# directly rather than re-implementing the recognition test a second time;
# placed here (not a new `check/volumescope.py`) because T25's own file
# scope only touches `derive/`, and this rule is a property of the data
# `compute_volume_bridge` above already produces, not of the interval
# domain T26 builds.
# ---------------------------------------------------------------------------

#: A bare zero-argument call entry, e.g. `"if does_volume_tracking()"` --
#: never matches `"else of: if does_volume_tracking()"` (the `"else of: "`
#: prefix means the whole string does not start with `"if "` at position 0)
#: and never matches an entry with an argument, an attribute test, or a
#: comparison (the `\(\)` anchors on ZERO arguments).
_HYPOTHESIS_ENTRY_RE = re.compile(r"^if (\w+)\(\)$")


def _caller_scope_entry_recognized(
    entry: str,
    *,
    is_outermost_for: bool,
    for_span: tuple[int, int] | None,
    caller_lineno: int | None,
    env: frozenset[str],
) -> bool:
    """One `caller_scope` entry is recognised as satisfied in exactly two
    ways (§14.6's normative box), and no others:

    1. **By hypothesis.** `entry` is a bare zero-argument call `f()` --
       `"if f()"` -- whose callee name `f` is a member of `env`. An
       `"else of: if f()"` entry (a negated enclosure) never matches this
       regex (it does not start with `"if "`) and is therefore never
       recognised this way, under any `env`, per the normative box.
    2. **By structure -- R1.** `entry` is the B1-bound `ast.For` statement
       for this guard, identified by POSITION, never by text: the caller
       has already established `is_outermost_for` (this is the outermost
       `"for "`-prefixed entry in the guard's own nearest-first
       `caller_scope`), and `for_span`/`caller_lineno` are both present and
       `for_span[0] <= caller_lineno <= for_span[1]`.

    Everything else -- a second `for` header (not the outermost one, or
    outside `for_span`), any `while`, any `async for`, an attribute test, a
    comparison, a `UnaryOp`, a call with arguments, an `"else of: if …"`
    entry, `for_span` absent, `caller_lineno` absent, an unparseable
    string -- returns False.
    """
    hypothesis_match = _HYPOTHESIS_ENTRY_RE.match(entry)
    if hypothesis_match is not None and hypothesis_match.group(1) in env:
        return True
    if (
        is_outermost_for
        and entry.startswith("for ")
        and for_span is not None
        and caller_lineno is not None
        and for_span[0] <= caller_lineno <= for_span[1]
    ):
        return True
    return False


def volume_guard_is_unconditional(
    caller_scope: list[str] | None,
    caller_lineno: int | None,
    for_span: tuple[int, int] | list[int] | None,
    env: frozenset[str],
) -> bool:
    """§14.6's normative conditional-guard rule. A volume guard is
    UNCONDITIONAL -- i.e. may emit `WILL_FAIL` -- iff EVERY entry of its
    `caller_scope` (nearest-first, as P10 attaches it) is recognised as
    satisfied by `_caller_scope_entry_recognized`.

    **Fail-closed on `caller_scope is None`** (P10's own attachment
    failure, §14.0.2) -- a `null` caller scope is treated as containing an
    unrecognised conjunct, never as an empty (vacuously satisfied) one.

    The "outermost `for` entry" that R1 may recognise is computed ONCE
    here, over the whole nearest-first list (the LAST `"for "`-prefixed
    entry, since nearest-first means index 0 is innermost) -- a second,
    non-outermost `for` entry is never recognised by R1 even when
    `for_span` happens to contain `caller_lineno`, because R1 identifies a
    NODE (the specific `ast.For` B1 bound `<name>` over), not a shape, and
    this guard's `for_span` names only that one node.
    """
    if caller_scope is None:
        return False
    span = (for_span[0], for_span[1]) if for_span is not None else None
    for_indices = [i for i, entry in enumerate(caller_scope) if entry.startswith("for ")]
    outermost_for_index = max(for_indices) if for_indices else None
    for i, entry in enumerate(caller_scope):
        recognized = _caller_scope_entry_recognized(
            entry,
            is_outermost_for=(outermost_for_index is not None and i == outermost_for_index),
            for_span=span,
            caller_lineno=caller_lineno,
            env=env,
        )
        if not recognized:
            return False
    return True


# ---------------------------------------------------------------------------
# The lid family (spec 260903 §13.1, backlog #4881a) -- NOT a fifth pass,
# and NOT a receiver-state producer. §13.1's normative disposition is that
# the lid family is "specified and not adopted": no `LidState`, no
# `ReceiverState` entry for a lid-carrying class, no `Finding` of any
# verdict. `lid_typestate_anchor_evidence` below exists ONLY to publish,
# in the gap ledger, WHY P2's real anchor rule (`_typestate_anchor`) does
# not fire for `Liddable` (AC-13.3) -- it re-runs that same rule, plus
# P1b's own writer scan (`_attribute_writers`), against the class the
# caller names; it invents no rule of its own and is called from nowhere
# in `derive_receiver_states`'s own path.
# ---------------------------------------------------------------------------


def _none_check_body_shape(member: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, str] | None:
    """The body-shape half of `_typestate_anchor`'s test (`return self.<F>
    is/is not None`), WITHOUT its `@property` decorator gate. Used only to
    publish which methods match the shape regardless of decoration, so an
    "absent" P2 anchor is diagnosable (a same-shaped candidate existed but
    was not a `@property`) rather than a bare negative.
    """
    body = [s for s in member.body if not _is_docstring_stmt(s)]
    if len(body) != 1:
        return None
    stmt = body[0]
    if not (isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Compare)):
        return None
    cmp = stmt.value
    if len(cmp.ops) != 1 or len(cmp.comparators) != 1:
        return None
    op = cmp.ops[0]
    if not isinstance(op, (ast.Is, ast.IsNot)):
        return None
    right = cmp.comparators[0]
    if not (isinstance(right, ast.Constant) and right.value is None):
        return None
    if not _is_self_attr(cmp.left):
        return None
    true_when = "not_none" if isinstance(op, ast.IsNot) else "is_none"
    return (cmp.left.attr, true_when)  # type: ignore[union-attr]


def lid_typestate_anchor_evidence(plr_pkg_root: Path, class_name: str = "Liddable") -> dict[str, Any] | None:
    """§13.1's diagnostic-only evidence for the gap ledger's `lid_state`
    block (AC-13.3). Walks `plr_pkg_root` once (the same whole-tree scan
    `derive_receiver_states` uses) looking for the first top-level class
    named `class_name`, then reports:

    * ``anchor`` -- the field P2's real `_typestate_anchor` rule finds, or
      the literal string ``"absent"`` when it finds zero or more than one
      candidate `@property` (§10.2.2's fail-closed rule, unmodified here).
    * ``anchor_candidates`` -- every method (decorated `@property` or not)
      whose BODY matches the anchor shape, so an "absent" verdict is
      diagnosable rather than a bare negative.
    * ``state_fields`` -- P1b's own `_attribute_writers` scan of the class,
      i.e. every `self.<name> = ...` write found anywhere in its body.

    Returns ``None`` if `class_name` is not found anywhere under
    `plr_pkg_root` -- fail closed, the same discipline P2 itself uses,
    rather than publishing evidence about a class that does not exist at
    this pin.
    """
    class_node: ast.ClassDef | None = None
    for file in _iter_plr_source_files(plr_pkg_root):
        try:
            source = file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for top in ast.iter_child_nodes(tree):
            if isinstance(top, ast.ClassDef) and top.name == class_name:
                class_node = top
                break
        if class_node is not None:
            break
    if class_node is None:
        return None

    anchor = _typestate_anchor(class_node)
    body_shape_candidates = sorted(
        member.name
        for member in ast.iter_child_nodes(class_node)
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        and _none_check_body_shape(member) is not None
    )
    state_fields = sorted(_attribute_writers(class_node, class_name).keys())
    return {
        "anchor": "absent" if anchor is None else anchor[0],
        "anchor_candidates": body_shape_candidates,
        "state_fields": state_fields,
    }
