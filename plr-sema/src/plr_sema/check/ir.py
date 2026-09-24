"""plr_sema.check.ir: SEMA-IR, a versioned linear bytecode (spec 260901 §11,
`260902_plr-sema-ir-bytecode-increment.md`).

**Stdlib only.** No ``libcst``, no ``pylabrobot``, no ``pydantic`` (§6.2's
import boundary, unchanged -- see ``plr_sema.check``'s module docstring).
``ast`` is stdlib and permitted (§6.2 bans ``libcst``/``pylabrobot``, not
``ast``; ``plr_sema.derive`` already relies on that same distinction).

**What this module is.** The missing middle between the front end
(``praxis``'s libcst extractor -> ``ProtocolComputationGraph``, out of
process) and the back end (``check_ir`` in ``plr_sema.check``, a pass over
this bytecode). Two lowerings target it: :func:`lower_graph` (from an
extracted-graph JSON payload) and :func:`lower_calls` (from a corpus row's
or a verifier run's PLR-named, already-grounded kwargs -- see
``plr-sema/eval/oracle_common.py``'s ``ir_value_of``). Both produce a
:class:`Bytecode`: a linear instruction stream plus a ``sideband`` dict of
everything not hashed (spans, names, the origin map).

**The no-drop invariant (§11.1.4).** Every field of every upstream model
(``OperationNode``, ``ResourceNode``, ``ProtocolComputationGraph``,
``praxis/backend/utils/plr_static_analysis/models.py:524-661``) is assigned
exactly one disposition in :data:`DISPOSITIONS`: **I** (an instruction
field), **W** (a widen trigger), **S** (sideband, never hashed, never read
by ``check_ir``), or **X** (excluded with a written reason -- the three
hand-typed precondition/creates_state fields, §11.1.4's laundering
argument). There is no fifth disposition and no unlisted field --
``tests/test_ir.py::test_disposition_table_is_exhaustive`` (AC-11.1) checks
this against the live upstream field names.

**The WIDEN vocabulary is derived, never typed a second time (§11.1.5,
AC-11.8).** :data:`WIDEN_FIELDS` is computed from :data:`DISPOSITIONS`
itself, and the seven field-name identifiers used at every widen call site
below (``_RECEIVER_TYPE`` etc.) are unpacked FROM ``sorted(WIDEN_FIELDS)`` --
not retyped as string literals -- so the only ``ast.Constant`` occurrence of
each widen-reason string in this file is the one inside ``DISPOSITIONS``
itself. See ``tests/test_ir.py``'s AC-11.8 test for the exact scan and the
resolved-ambiguity note on what "outside the single dict" was relaxed to
mean for call sites that must also *read* the same field name from a
payload dict (unavoidable -- a lookup key and a widen reason are the same
string by construction, per §11.1.5).
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar, Union

__all__ = [
    "IR_VERSION",
    "IR_HASH_PREFIX",
    "Lit",
    "Ref",
    "Seq",
    "Top",
    "Value",
    "value_to_json",
    "value_from_json",
    "Resource",
    "Call",
    "Loop",
    "Branch",
    "Else",
    "End",
    "Widen",
    "Instruction",
    "Bytecode",
    "DISPOSITIONS",
    "EXCLUDED_FIELDS",
    "WIDEN_FIELDS",
    "lower_graph",
    "lower_calls",
    "canonical_text",
    "bytecode_hash",
    "cache_key",
    "relabel_findings",
    "obliged_operation_ids",
]

#: Normative bump rule (§11.1.1): any change to the opcode set, the value
#: grammar, the canonicalisation rules (§11.3) or the disposition table
#: (§11.1.3) bumps this. It is a cache-key component (§11.3.3) so a bump
#: invalidates every stored result rather than silently reusing one
#: computed under different rules.
#:
#: 1 -> 2 (spec §12.2.7, backlog #4932): the extractor now emits real
#: LOOP/BRANCH regions, which changes `bytecode_hash` for every protocol
#: that previously got the synthetic whole-stream wrap -- exactly the case
#: §11.4.1 property 3 named as this follow-up's own trigger.
IR_VERSION = 2


# ---------------------------------------------------------------------------
# §11.1.2 -- the value grammar. Four forms, no fifth, no escape hatch to a
# raw source string in the hashed stream.
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class Lit:
    """A static literal: number, string, bool, or ``None``."""

    v: Any


@dataclasses.dataclass(frozen=True, slots=True)
class Ref:
    """A resource, or a cell within one (``"A1"``). ``slot`` is a
    positional slot id assigned by the lowering (§11.3.1) -- never a raw
    variable name.
    """

    slot: int
    cell: str | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class Seq:
    """An ordered sequence of KNOWN LENGTH. The load-bearing form: a
    sequence whose *elements* are unresolvable still has a resolvable
    *length* (§11.1.2).
    """

    items: tuple[Value, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class Top:
    """The analyzer cannot resolve this value."""


Value = Union[Lit, Ref, Seq, Top]


def value_to_json(v: Value) -> dict[str, Any]:
    """Canonical JSON encoding (§11.1.2): ``{"k":"lit","v":...}`` /
    ``{"k":"ref","slot":...,"cell":...}`` / ``{"k":"seq","items":[...]}`` /
    ``{"k":"top"}``.
    """
    if isinstance(v, Lit):
        return {"k": "lit", "v": v.v}
    if isinstance(v, Ref):
        return {"k": "ref", "slot": v.slot, "cell": v.cell}
    if isinstance(v, Seq):
        return {"k": "seq", "items": [value_to_json(item) for item in v.items]}
    if isinstance(v, Top):
        return {"k": "top"}
    raise TypeError(f"not a Value: {v!r}")


def value_from_json(d: Mapping[str, Any]) -> Value:
    """Inverse of :func:`value_to_json`. Round-trips a canonical Value
    encoding, e.g. one already carrying a resolved integer ``slot`` (as
    opposed to the pre-resolution name-keyed ref wire shape :func:`lower_calls`
    reads -- see that function's docstring).
    """
    k = d.get("k")
    if k == "lit":
        return Lit(d.get("v"))
    if k == "ref":
        return Ref(slot=int(d["slot"]), cell=d.get("cell"))
    if k == "seq":
        return Seq(tuple(value_from_json(item) for item in d.get("items", ())))
    if k == "top":
        return Top()
    raise ValueError(f"unrecognized Value JSON {d!r}")


# ---------------------------------------------------------------------------
# §11.1.3 -- the six opcodes. `op` is a ClassVar tag, not a dataclass field
# (excluded from __init__/fields/slots by the ClassVar annotation).
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True, slots=True)
class Resource:
    """Declares resource slot ``slot``. ``grid`` is ``(items_x, items_y)``
    when both are non-null, else ``None`` (= Top, "grid unknown").
    """

    op: ClassVar[str] = "RESOURCE"
    slot: int
    type: str | None
    element_type: str | None
    is_container: bool
    is_parameter: bool
    parents: tuple[str, ...]
    grid: tuple[int, int] | None


@dataclasses.dataclass(frozen=True, slots=True)
class Call:
    """One operation. Every ``kwargs`` value is a :data:`Value`
    (§11.1.2), never a source string.
    """

    op: ClassVar[str] = "CALL"
    receiver: int
    receiver_type: str | None
    method: str
    kwargs: Mapping[str, Value]


@dataclasses.dataclass(frozen=True, slots=True)
class Loop:
    """Opens a loop region. ``trip=None`` = Top. v1 always emits ``None``
    (§11.1.3 -- the operand exists now so a later trip-count increment is
    additive with an ``IR_VERSION`` bump, not a re-encoding).
    """

    op: ClassVar[str] = "LOOP"
    trip: int | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class Branch:
    """Opens a two-armed region. ``pred=None`` = Top. v1 always emits
    ``None`` (no predicate language over protocol-level expressions yet).
    """

    op: ClassVar[str] = "BRANCH"
    pred: None = None


@dataclasses.dataclass(frozen=True, slots=True)
class Else:
    """Separates the arms of the innermost open ``Branch``."""

    op: ClassVar[str] = "ELSE"


@dataclasses.dataclass(frozen=True, slots=True)
class End:
    """Closes the innermost open ``Loop`` or ``Branch``."""

    op: ClassVar[str] = "END"


@dataclasses.dataclass(frozen=True, slots=True)
class Widen:
    """An explicit, hashed record that the lowering could not preserve
    something. ``reason`` is the verbatim name of the upstream model field
    whose disposition forced the widening (§11.1.5) -- never a new,
    hand-typed vocabulary.
    """

    op: ClassVar[str] = "WIDEN"
    reason: str


Instruction = Union[Resource, Call, Loop, Branch, Else, End, Widen]


@dataclasses.dataclass(frozen=True, slots=True)
class Bytecode:
    """``{"ir_version": ..., "instructions": [...], "sideband": {...}}``
    (§11.1.1). ``sideband`` is never hashed and never read by ``check_ir``.
    """

    ir_version: int
    instructions: tuple[Instruction, ...]
    sideband: Mapping[str, Any] = dataclasses.field(default_factory=dict)


# ---------------------------------------------------------------------------
# §11.1.4 -- the disposition table. The no-drop invariant: every field of
# every upstream model gets exactly one of I / W / S / X (dispositions may
# combine, e.g. "I+W"). Keyed by model NAME (not the pydantic class itself --
# this module never imports pydantic); tests/test_ir.py compares this
# against the live/AST-derived upstream field names (AC-11.1).
# ---------------------------------------------------------------------------

DISPOSITIONS: dict[str, dict[str, str]] = {
    # OperationNode (models.py:524-559 pre-#4932, now 16 fields with `trip`).
    "OperationNode": {
        "id": "S",
        "line_number": "S",
        "method_name": "I",
        "receiver_variable": "I",
        "receiver_type": "I+W",
        "arguments": "I+W",
        # §12.2.2/§12.9: moved S+W -> I+S+W -- node_type is now READ to
        # decide whether a CALL is emitted at all (GraphNodeType.REGION
        # skips lower_one_call and its recomputed_node_type cross-check
        # entirely), in addition to the pre-existing widen-on-mismatch
        # behaviour for every non-REGION node.
        "node_type": "I+S+W",
        "preconditions": "X",
        "creates_state": "X",
        "depends_on_params": "W+S",
        "foreach_source": "I+S",
        "foreach_body": "I",
        "condition_expr": "I+S",
        "true_branch": "I",
        "false_branch": "I",
        # §12.2.3/§12.2.7 (#4932): a REGION loop header's proved trip count
        # (or null), read straight into Loop.trip.
        "trip": "I",
    },
    # ResourceNode (models.py:562-587, 9 fields).
    "ResourceNode": {
        "variable_name": "I",
        "declared_type": "I",
        "element_type": "I",
        "is_container": "I",
        "is_parameter": "I",
        "parental_chain": "I",
        "source_expression": "S",
        "items_x": "I",
        "items_y": "I",
    },
    # ProtocolComputationGraph (models.py:613-634, 10 fields).
    "ProtocolComputationGraph": {
        "protocol_fqn": "S",
        "protocol_name": "S",
        "operations": "I",
        "resources": "I",
        "preconditions": "X",
        "execution_order": "I+W",
        "machine_types": "S",
        "resource_types": "S",
        "has_loops": "I+W",
        "has_conditionals": "I+W",
    },
}

#: The three excluded-with-reason fields (§11.1.4), pinned INDEPENDENTLY of
#: this table by AC-11.14 (``tests/test_ir.py::test_excluded_fields_are_excluded``)
#: -- see that test's docstring for why a table-derived check cannot
#: substitute for the hardcoded identity check.
EXCLUDED_FIELDS: frozenset[tuple[str, str]] = frozenset(
    (model, field)
    for model, fields in DISPOSITIONS.items()
    for field, disposition in fields.items()
    if disposition == "X"
)

#: §11.1.5: the WIDEN vocabulary is DERIVED from DISPOSITIONS, never a
#: second, hand-typed set. Every field whose disposition contains "W".
WIDEN_FIELDS: frozenset[str] = frozenset(
    field
    for fields in DISPOSITIONS.values()
    for field, disposition in fields.items()
    if "W" in disposition
)

#: Unpacked from a DERIVED, sorted sequence -- not retyped as string
#: literals -- so every widen call site below reads/writes a field name via
#: one of these identifiers rather than a fresh ``ast.Constant`` (see this
#: module's docstring and AC-11.8). Order is alphabetical
#: (``sorted(WIDEN_FIELDS)``); if a new widen field is ever added, this line
#: fails loudly (wrong tuple arity) rather than silently mis-assigning.
(
    _ARGUMENTS,
    _DEPENDS_ON_PARAMS,
    _EXECUTION_ORDER,
    _HAS_CONDITIONALS,
    _HAS_LOOPS,
    _NODE_TYPE,
    _RECEIVER_TYPE,
) = sorted(WIDEN_FIELDS)


# ---------------------------------------------------------------------------
# §11.2.1 -- lower_graph: from the extractor's JSON payload.
# ---------------------------------------------------------------------------


def _value_from_pyobj(x: Any) -> Value:
    if isinstance(x, (list, tuple)):
        return Seq(tuple(_value_from_pyobj(i) for i in x))
    if x is None or isinstance(x, (bool, int, float, str)):
        return Lit(x)
    return Top()


def lower_graph(
    payload: Mapping[str, Any],
    *,
    param_names: Mapping[str, tuple[str, ...]] | None = None,
) -> Bytecode:
    """Lower a §6.2 graph wire payload (the raw ``model_dump(mode="json")``
    of a real ``ProtocolComputationGraph`` -- the same JSON
    ``plr_sema.check.graph.parse_graph`` reads) into :class:`Bytecode`.

    ``param_names`` maps a contract key (``f"{receiver_type}.{method_name}"``)
    to that method's PLR parameter names (§11.2.4's trust rule). ``None``
    means "trust nothing" -- fail-closed default.

    **Real regions (§12.2, #4932).** The extractor now populates a
    ``GraphNodeType.REGION`` header -- ``method_name == ""``,
    ``receiver_variable == ""``, ``receiver_type is None`` -- for every
    ``for``/``while``/``if`` whose body carries >=1 operation. Such a
    header emits **no** ``CALL`` at all (§12.2.2: it is not an operation
    and carries no obligation) -- just the region alone, ``LOOP``
    (respectively ``BRANCH ... ELSE ... END``), with ``Loop.trip`` read
    straight from the header's own ``trip`` field (§12.2.3's proved value,
    or ``None``).

    **Resolved ambiguity (fixture/fuzz-only region semantics, PRE-#4932
    shape, still supported).** Before real regions existed, the extractor
    never populated ``foreach_source``/``foreach_body``/``condition_expr``/
    ``true_branch``/``false_branch`` on real graphs (§11.1.4's live-data
    caveat) -- this lowering's handling of them was therefore exercised by
    fixtures and the tier-4 hypothesis fuzzer only, and that fixture/fuzz
    shape (a call-bearing, non-``REGION`` operation that ALSO carries its
    own region fields) is still supported unchanged, for backward
    compatibility: (1) such an operation gets its own ``CALL`` (so
    per-operation totality, AC-6.4/AC-11.7, holds even for a loop-carrying
    operation) immediately followed by a ``LOOP null`` region wrapping
    whichever ``foreach_body`` ids resolve to real, not-yet-emitted
    operations (dangling/unresolvable ids -- the common case from the
    tier-4 fuzzer, which never emits a matching id -- are silently
    skipped, not an error: the region still opens and closes validly
    around whatever real content exists, which is what keeps AC-11.13's
    well-formedness total even under fuzzed input). Same shape for
    ``condition_expr``/``true_branch``/``false_branch`` -> ``BRANCH null
    ... ELSE ... END``. This is one reasonable, explicit, total
    interpretation of an underspecified (self-admittedly
    unreachable-from-real-data, at the time) corner; see the task report
    for the alternative considered and rejected (a separate, CALL-less
    "loop header" node) and why it would violate AC-6.4/AC-11.7's totality
    guarantee -- the same argument #4932 later adopted FOR the real
    ``REGION`` shape once headers stopped needing to double as an
    operation's own totality-bearing ``CALL``.

    **Resolved ambiguity (duplicate operation ids, tier-4 fuzz-discovered).**
    A real extractor's ``id`` is documented "Unique identifier for this
    operation", but the wire schema does not structurally forbid a
    duplicate, and the tier-4 hypothesis strategy
    (``tests/test_wire_fuzz.py::operation_id_strategy``) can and does
    generate one. An id-keyed dict (last-write-wins) would silently drop
    every operation but the last with a given id, violating AC-6.4/AC-11.7's
    totality over the REAL operation count, not the unique-id count. This
    lowering therefore tracks CONSUMPTION BY POSITION (a per-id FIFO queue
    of list indices, ``positions_by_id``), never by id membership in a
    ``set`` -- every element of ``operations`` gets exactly one ``CALL``
    regardless of id collisions, and a self-referencing or cyclic
    ``foreach_body``/``true_branch``/``false_branch`` id still terminates
    (each position is poppable at most once).
    """
    operations_raw = list(payload.get("operations") or ())
    resources_payload: dict[str, Mapping[str, Any]] = dict(payload.get("resources") or {})
    execution_order = list(payload.get("execution_order") or ())
    has_loops = bool(payload.get("has_loops", False))
    has_conditionals = bool(payload.get("has_conditionals", False))

    positions_by_id: dict[str, list[int]] = {}
    op_ids_in_payload_order: list[str] = []
    by_id_first: dict[str, Mapping[str, Any]] = {}
    for idx, op in enumerate(operations_raw):
        oid = op["id"]
        positions_by_id.setdefault(oid, []).append(idx)
        op_ids_in_payload_order.append(oid)
        by_id_first.setdefault(oid, op)
    # FIFO per id: pop the earliest not-yet-consumed position for `oid`.
    _next_pos_cursor: dict[str, int] = {}

    def next_position(oid: str) -> int | None:
        positions = positions_by_id.get(oid)
        if not positions:
            return None
        cursor = _next_pos_cursor.get(oid, 0)
        if cursor >= len(positions):
            return None
        _next_pos_cursor[oid] = cursor + 1
        return positions[cursor]

    def _region_children(op: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            *(op.get("foreach_body") or ()),
            *(op.get("true_branch") or ()),
            *(op.get("false_branch") or ()),
        )

    def _reachable_from(top_ids: list[str]) -> set[str]:
        # §12.2.2 (#4932): a REGION header's body ids are NOT repeated at
        # top level in `execution_order` -- they are only reachable by
        # recursing through the header's own region field(s). A flat
        # `set(execution_order) == set(op_ids_in_payload_order)` check
        # would therefore treat every real region-bearing payload as an
        # invalid permutation and always fall back to the (mis-ordered,
        # since body ops are appended to `operations` before their owning
        # header -- see the extractor's own body-accumulator ordering)
        # flat walk. This closure is the region-aware replacement.
        seen: set[str] = set()
        stack = list(top_ids)
        while stack:
            oid = stack.pop()
            if oid in seen:
                continue
            seen.add(oid)
            op = by_id_first.get(oid)
            if op is not None:
                stack.extend(_region_children(op))
        return seen

    front_widens: list[Widen] = []
    if (
        execution_order
        and len(execution_order) == len(set(execution_order))
        and _reachable_from(execution_order) == set(op_ids_in_payload_order)
    ):
        ordered_ids = list(execution_order)
    else:
        ordered_ids = list(op_ids_in_payload_order)
        if execution_order:
            front_widens.append(Widen(reason=_EXECUTION_ORDER))

    slot_of: dict[str, int] = {}

    def get_slot(name: str) -> int:
        if name not in slot_of:
            slot_of[name] = len(slot_of)
        return slot_of[name]

    def lower_arg_value(raw: Any) -> Value:
        if not isinstance(raw, str):
            return _value_from_pyobj(raw)
        try:
            node = ast.parse(raw, mode="eval").body
        except SyntaxError:
            return Top()
        return _lower_ast_node(node)

    def _self_attr_name(node: ast.AST) -> str | None:
        # §12.2.5 (#4932, round-1 O4): `self.<attr>` resolves against the
        # declared resource set by its dotted name, matching the
        # extractor's own `visit_Assign` registration
        # (`variable_name == f"self.{attr}"`).
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
        ):
            return f"self.{node.attr}"
        return None

    def _lower_ast_node(node: ast.AST) -> Value:
        if isinstance(node, ast.Name) and node.id in resources_payload:
            return Ref(get_slot(node.id), None)
        self_attr = _self_attr_name(node)
        if self_attr is not None and self_attr in resources_payload:
            return Ref(get_slot(self_attr), None)
        if isinstance(node, ast.Subscript):
            base = node.value
            idx = node.slice
            base_name: str | None = None
            if isinstance(base, ast.Name) and base.id in resources_payload:
                base_name = base.id
            else:
                base_self_attr = _self_attr_name(base)
                if base_self_attr is not None and base_self_attr in resources_payload:
                    base_name = base_self_attr
            if (
                base_name is not None
                and isinstance(idx, ast.Constant)
                and isinstance(idx.value, str)
            ):
                return Ref(get_slot(base_name), idx.value)
            return Top()
        if isinstance(node, (ast.List, ast.Tuple)):
            return Seq(tuple(_lower_ast_node(elt) for elt in node.elts))
        try:
            literal = ast.literal_eval(node)
        except Exception:
            return Top()
        return _value_from_pyobj(literal)

    body_instrs: list[Instruction] = []
    body_origin: dict[int, str] = {}
    body_span: dict[int, int] = {}

    def lower_kwargs(op: Mapping[str, Any]) -> tuple[dict[str, Value], bool]:
        args = op.get("arguments") or {}
        contract_key = f"{op.get('receiver_type')}.{op.get('method_name')}"
        trusted = None if param_names is None else param_names.get(contract_key)
        out: dict[str, Value] = {}
        any_untrusted = False
        for i, (k, raw) in enumerate(args.items()):
            value = lower_arg_value(raw)
            if trusted is not None and k in trusted:
                out[k] = value
            else:
                any_untrusted = True
                out[f"?{i}"] = value
        return out, any_untrusted

    def lower_one_call(op: Mapping[str, Any]) -> None:
        widens: list[Widen] = []
        if op.get("receiver_type") is None:
            widens.append(Widen(reason=_RECEIVER_TYPE))
        depends = op.get("depends_on_params") or ()
        if depends:
            widens.append(Widen(reason=_DEPENDS_ON_PARAMS))
        kwargs, any_untrusted = lower_kwargs(op)
        if any_untrusted:
            widens.append(Widen(reason=_ARGUMENTS))
        recomputed_dynamic = bool(depends) or any(isinstance(v, Top) for v in kwargs.values())
        recomputed_node_type = "dynamic" if recomputed_dynamic else "static"
        node_type = op.get("node_type")
        if node_type is not None and node_type != recomputed_node_type:
            widens.append(Widen(reason=_NODE_TYPE))

        body_instrs.extend(widens)
        receiver_var = op.get("receiver_variable")
        pc = len(body_instrs)
        body_instrs.append(
            Call(
                receiver=get_slot(receiver_var) if receiver_var is not None else get_slot(""),
                receiver_type=op.get("receiver_type"),
                method=op.get("method_name"),
                kwargs=kwargs,
            )
        )
        body_origin[pc] = op["id"]
        body_span[pc] = op.get("line_number", 0)

    def lower_op_and_regions(oid: str) -> None:
        idx = next_position(oid)
        if idx is None:
            return
        op = operations_raw[idx]
        # §12.2.2 (#4932): a REGION header emits no CALL at all -- it is
        # not an operation, carries no obligation, and would otherwise
        # spuriously WIDEN on `receiver_type`/`node_type` (a header's
        # `receiver_type` is always None and its `node_type` disagrees
        # with both "static" and "dynamic" by construction).
        is_region_header = op.get("node_type") == "region"
        if not is_region_header:
            lower_one_call(op)

        foreach_source = op.get("foreach_source")
        foreach_body = op.get("foreach_body") or ()
        if foreach_source is not None or foreach_body:
            # §12.2.3/§12.2.7 (#4932): a REGION header's proved trip count
            # (or `None`) is read straight through. A pre-#4932 fixture
            # carrying `foreach_source`/`foreach_body` on a call-bearing,
            # non-REGION node (the increment-2 fixture/fuzz-only shape
            # this lowering also still supports, per this function's own
            # docstring) has no `trip` field at all and keeps the old
            # always-`None` behaviour.
            trip = op.get("trip") if is_region_header else None
            body_instrs.append(Loop(trip=trip))
            for cid in foreach_body:
                lower_op_and_regions(cid)
            body_instrs.append(End())

        condition_expr = op.get("condition_expr")
        true_branch = op.get("true_branch") or ()
        false_branch = op.get("false_branch") or ()
        if condition_expr is not None or true_branch or false_branch:
            body_instrs.append(Branch(pred=None))
            for cid in true_branch:
                lower_op_and_regions(cid)
            body_instrs.append(Else())
            for cid in false_branch:
                lower_op_and_regions(cid)
            body_instrs.append(End())

    for oid in ordered_ids:
        lower_op_and_regions(oid)

    # §11.4.1 -- the synthetic whole-stream wrap.
    has_real_loop = any(isinstance(i, Loop) for i in body_instrs)
    has_real_branch = any(isinstance(i, Branch) for i in body_instrs)
    extra_front = 0
    if has_conditionals and not has_real_branch:
        body_instrs = [Widen(reason=_HAS_CONDITIONALS), Branch(pred=None), *body_instrs, End()]
        extra_front += 2
    if has_loops and not has_real_loop:
        body_instrs = [Widen(reason=_HAS_LOOPS), Loop(trip=None), *body_instrs, End()]
        extra_front += 2

    body_instrs = [*front_widens, *body_instrs]
    extra_front += len(front_widens)
    body_origin = {pc + extra_front: opid for pc, opid in body_origin.items()}
    body_span = {pc + extra_front: ln for pc, ln in body_span.items()}

    resource_instrs: list[Resource] = []
    for name, slot in sorted(slot_of.items(), key=lambda kv: kv[1]):
        decl = resources_payload.get(name)
        if decl is None:
            continue
        items_x = decl.get("items_x")
        items_y = decl.get("items_y")
        grid = (items_x, items_y) if items_x is not None and items_y is not None else None
        resource_instrs.append(
            Resource(
                slot=slot,
                type=decl.get("declared_type"),
                element_type=decl.get("element_type"),
                is_container=bool(decl.get("is_container", False)),
                is_parameter=bool(decl.get("is_parameter", True)),
                parents=tuple(decl.get("parental_chain") or ()),
                grid=grid,
            )
        )

    offset = len(resource_instrs)
    instructions = tuple(resource_instrs) + tuple(body_instrs)
    origin = {pc + offset: opid for pc, opid in body_origin.items()}
    span = {pc + offset: ln for pc, ln in body_span.items()}

    source_expression = {
        name: decl.get("source_expression")
        for name, decl in resources_payload.items()
        if decl.get("source_expression") is not None
    }

    sideband: dict[str, Any] = {
        "protocol_fqn": payload.get("protocol_fqn"),
        "protocol_name": payload.get("protocol_name"),
        "machine_types": list(payload.get("machine_types") or ()),
        "resource_types": list(payload.get("resource_types") or ()),
        "origin": origin,
        "span": span,
        "source_expression": source_expression,
    }
    return Bytecode(ir_version=IR_VERSION, instructions=instructions, sideband=sideband)


# ---------------------------------------------------------------------------
# §11.2.2 -- lower_calls: from a corpus row's / verifier run's PLR-named
# kwargs, already reduced to IR-value JSON by eval/oracle_common.py's
# ir_value_of. See ir_value_of's own docstring for the exact pre-resolution
# wire shape (name-keyed refs, resolved to slots HERE).
# ---------------------------------------------------------------------------


def _value_from_wire(d: Any, get_slot: Any) -> Value:
    if not isinstance(d, Mapping):
        return Top()
    k = d.get("k")
    if k == "lit":
        return Lit(d.get("v"))
    if k == "ref":
        name = d.get("name")
        if name is not None:
            return Ref(slot=get_slot(name), cell=d.get("cell"))
        return Ref(slot=int(d["slot"]), cell=d.get("cell"))
    if k == "seq":
        return Seq(tuple(_value_from_wire(item, get_slot) for item in d.get("items", ())))
    return Top()


def lower_calls(
    calls: Sequence[Mapping[str, Any]],
    *,
    resources: Mapping[str, Mapping[str, Any]],
    param_names: Mapping[str, tuple[str, ...]] | None = None,
) -> Bytecode:
    """Lower a sequence of ``{"method": <PLR method name>, "kwargs": {<PLR
    param>: <IR value JSON>}, "receiver"?: <name>, "receiver_type"?: <str>}``
    (§11.2.2) into :class:`Bytecode`.

    **Resolved ambiguity (the receiver, and the pre-resolution ref wire
    shape).** §11.2.2's pseudocode gives ``calls`` as ``{"method", "kwargs"}``
    only -- no explicit receiver, matching today's single-receiver
    ``adapt_graph`` convention (every op against ``lh``/``"LiquidHandler"``).
    This implementation keeps that default (``receiver="lh"``,
    ``receiver_type="LiquidHandler"``) but accepts optional per-call
    overrides, a strict superset. Each ``kwargs`` value is the wire dict
    :func:`value_to_json` would emit, EXCEPT a ``Ref`` is keyed by
    ``"name"`` (a resource variable name) rather than an already-resolved
    ``"slot"`` int -- slot assignment is this function's job (mirroring
    :func:`lower_graph`'s own first-appearance-order assignment), and at
    harvest time (inside ``run_runtime``, one call at a time) there is no
    cross-call slot registry to assign ints against yet. A ``"slot"`` key is
    still accepted for forward compatibility with an already-resolved Value.

    ``resources`` mirrors :func:`lower_graph`'s per-name resource
    declaration dict (``type``/``declared_type``, ``element_type``,
    ``is_container``, ``is_parameter``, ``parents``/``parental_chain``,
    ``items_x``/``items_y``); an entry absent from it still gets a slot
    (grounded implicitly by its first ``Ref``/receiver use) but no
    ``RESOURCE`` instruction.
    """
    slot_of: dict[str, int] = {}

    def get_slot(name: str) -> int:
        if name not in slot_of:
            slot_of[name] = len(slot_of)
        return slot_of[name]

    body_instrs: list[Instruction] = []
    origin: dict[int, str] = {}

    for i, call in enumerate(calls):
        method = call.get("method", "")
        receiver_name = call.get("receiver", "lh")
        receiver_type = call.get("receiver_type", "LiquidHandler")
        kwargs_raw = call.get("kwargs") or {}
        contract_key = f"{receiver_type}.{method}"
        trusted = None if param_names is None else param_names.get(contract_key)

        kwargs: dict[str, Value] = {}
        any_untrusted = False
        for j, (k, raw) in enumerate(kwargs_raw.items()):
            value = _value_from_wire(raw, get_slot)
            if trusted is not None and k in trusted:
                kwargs[k] = value
            else:
                any_untrusted = True
                kwargs[f"?{j}"] = value

        widens: list[Widen] = []
        if any_untrusted:
            widens.append(Widen(reason=_ARGUMENTS))
        body_instrs.extend(widens)

        pc = len(body_instrs)
        body_instrs.append(
            Call(
                receiver=get_slot(receiver_name),
                receiver_type=receiver_type,
                method=method,
                kwargs=kwargs,
            )
        )
        origin[pc] = str(i)

    resource_instrs: list[Resource] = []
    for name, slot in sorted(slot_of.items(), key=lambda kv: kv[1]):
        decl = resources.get(name)
        if decl is None:
            continue
        items_x = decl.get("items_x")
        items_y = decl.get("items_y")
        grid = (items_x, items_y) if items_x is not None and items_y is not None else None
        resource_instrs.append(
            Resource(
                slot=slot,
                type=decl.get("type", decl.get("declared_type")),
                element_type=decl.get("element_type"),
                is_container=bool(decl.get("is_container", False)),
                is_parameter=bool(decl.get("is_parameter", True)),
                parents=tuple(decl.get("parents", decl.get("parental_chain")) or ()),
                grid=grid,
            )
        )

    offset = len(resource_instrs)
    instructions = tuple(resource_instrs) + tuple(body_instrs)
    origin = {pc + offset: opid for pc, opid in origin.items()}
    return Bytecode(ir_version=IR_VERSION, instructions=instructions, sideband={"origin": origin})


# ---------------------------------------------------------------------------
# §11.3 -- canonical form, content hash, cache key.
# ---------------------------------------------------------------------------


def _instr_canonical_obj(instr: Instruction) -> dict[str, Any]:
    if isinstance(instr, Resource):
        return {
            "op": Resource.op,
            "slot": instr.slot,
            "type": instr.type,
            "element_type": instr.element_type,
            "is_container": instr.is_container,
            "is_parameter": instr.is_parameter,
            "parents": list(instr.parents),
            "grid": list(instr.grid) if instr.grid is not None else None,
        }
    if isinstance(instr, Call):
        kwargs_sorted = {k: value_to_json(v) for k, v in sorted(instr.kwargs.items(), key=lambda kv: kv[0])}
        return {
            "op": Call.op,
            "receiver": instr.receiver,
            "receiver_type": instr.receiver_type,
            "method": instr.method,
            "kwargs": kwargs_sorted,
        }
    if isinstance(instr, Loop):
        return {"op": Loop.op, "trip": instr.trip}
    if isinstance(instr, Branch):
        return {"op": Branch.op, "pred": instr.pred}
    if isinstance(instr, Else):
        return {"op": Else.op}
    if isinstance(instr, End):
        return {"op": End.op}
    if isinstance(instr, Widen):
        return {"op": Widen.op, "reason": instr.reason}
    raise TypeError(f"unrecognized instruction {instr!r}")


def canonical_text(bytecode: Bytecode) -> str:
    """§11.3.1: one canonical JSON object per instruction
    (``sort_keys=True, separators=(",", ":"), ensure_ascii=False``), joined
    by ``"\\n"``. ``pc`` is not written -- it is the line index. Only
    instruction fields participate; ``sideband`` (line numbers, names,
    ``protocol_fqn``/``protocol_name``, the origin map) never does.
    """
    lines = [
        json.dumps(_instr_canonical_obj(instr), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        for instr in bytecode.instructions
    ]
    return "\n".join(lines)


#: §11.3.2.
IR_HASH_PREFIX = f"sema-ir/{IR_VERSION}\n"


def bytecode_hash(bytecode: Bytecode) -> str:
    """§11.3.2: ``sha256(IR_HASH_PREFIX + canonical_text)``. Chosen because
    the provenance layer this plugs into already speaks sha256/sha1
    (``GitState.dirty_content_id``).
    """
    text = canonical_text(bytecode)
    return hashlib.sha256((IR_HASH_PREFIX + text).encode("utf-8")).hexdigest()


def cache_key(
    bc_hash: str,
    contracts_json: str,
    stamp: Any,
    *,
    ir_version: int = IR_VERSION,
    env: frozenset[str] = frozenset(),
) -> tuple[str, str, tuple[Any, Any, Any], int, tuple[str, ...]]:
    """§11.3.3/§13.3.2: ``(bytecode_hash, contracts_sha, surface_identity,
    ir_version, env)``. Defines the key; stores nothing (#4922 -- the store
    is :class:`plr_sema.check.cache.CacheStore`).

    ``stamp`` is a ``plr_sema._provenance.SurveyStamp`` (duck-typed via
    ``getattr`` here rather than imported, to keep this module's own import
    list minimal and independent of that module's own import graph).

    ``env`` (spec 260903 §13.3.2/§13.2.6) is the fifth key component --
    added because the volume family's ``does_volume_tracking()`` hypothesis
    makes ``check_ir`` a function of a runtime-observed environment set, not
    just of ``bytecode``/``contracts``/``receiver_states``. It defaults to
    the empty ``frozenset`` because the volume family (its only producer)
    is deferred out of this increment (#4922) -- every caller today gets
    the same fifth component, ``()``, until a later increment threads a
    real ``env`` through ``check_ir``/``check_graph``. Encoded as
    ``tuple(sorted(env))`` so the key stays JSON-round-trippable and
    order-independent (two callers passing the same set in different
    iteration order must produce the same key).
    """
    contracts_sha = hashlib.sha256(contracts_json.encode("utf-8")).hexdigest()
    plr = getattr(stamp, "plr", None)
    surface_identity = (
        getattr(stamp, "surface", None),
        getattr(stamp, "surface_pin", None) or getattr(plr, "hash", None),
        getattr(plr, "dirty_content_id", None),
    )
    return (bc_hash, contracts_sha, surface_identity, ir_version, tuple(sorted(env)))


def obliged_operation_ids(payload: Mapping[str, Any]) -> frozenset[str]:
    """Spec 260903 §12.3.4: `OBLIGED(graph)` -- call-bearing operations
    (§12.2.2's `node_type is not REGION` exclusion) minus every operation
    that lies, at any nesting depth, within the `foreach_body`/
    `true_branch`/`false_branch` of a `REGION` header whose own `trip` is
    the PROVED integer `0` (§12.2.3). Only a `LOOP`-shaped header (one with
    a `trip` field at all) can be "dead" this way -- a `BRANCH` never
    excuses its arms, since either arm may run depending on a predicate
    this analyzer does not evaluate (§12.3.6 B2).

    This is main spec AC-6.4 (amended) and AC-7.2 (amended)'s right-hand
    side, and AC-11.7 (amended)'s target set for `sideband.origin` restricted
    to visited `CALL` pcs -- implemented once here so all three (and the
    tests that pin them) read the same definition rather than three
    independently hand-rolled set comprehensions. Operates on the RAW wire
    payload (`lower_graph`'s own input shape), not on `Bytecode`, because
    `OBLIGED` is a property of the GRAPH, not of how many times `check_ir`
    chooses to walk a region (§12.3.4 point 1: unrolling is a property of
    the walk, not the stream).
    """
    operations = list(payload.get("operations") or ())
    by_id: dict[str, Mapping[str, Any]] = {}
    for op in operations:
        by_id.setdefault(op["id"], op)

    def region_children(op: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            *(op.get("foreach_body") or ()),
            *(op.get("true_branch") or ()),
            *(op.get("false_branch") or ()),
        )

    dead: set[str] = set()

    def mark_dead(ids: Sequence[str]) -> None:
        stack = list(ids)
        while stack:
            oid = stack.pop()
            if oid in dead:
                continue
            dead.add(oid)
            op = by_id.get(oid)
            if op is not None:
                stack.extend(region_children(op))

    for op in operations:
        if op.get("node_type") == "region" and op.get("trip") == 0:
            mark_dead(region_children(op))

    return frozenset(
        op["id"]
        for op in operations
        if op.get("node_type") != "region" and op["id"] not in dead
    )


def relabel_findings(findings: Sequence[Any], origin: Mapping[int, str]) -> tuple[Any, ...]:
    """§11.4.3: relabel each finding's ``operation_id`` (a ``str(pc)``,
    ``check_ir``'s only available identity) through ``sideband["origin"]``
    to the real graph/call-index id. Generic over any dataclass carrying an
    ``operation_id`` field (duck-typed via ``dataclasses.replace`` so this
    module need not import ``plr_sema.verdict.Finding``).
    """
    out = []
    for f in findings:
        pc = int(f.operation_id)
        real_id = origin.get(pc, f.operation_id)
        out.append(dataclasses.replace(f, operation_id=real_id))
    return tuple(out)
