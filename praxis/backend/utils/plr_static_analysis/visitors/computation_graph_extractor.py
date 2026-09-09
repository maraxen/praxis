"""Computation graph extractor for protocol functions.

This module provides a LibCST visitor that analyzes protocol function bodies
to extract a computational graph representation, including:
- Operation nodes (method calls on machines)
- Resource nodes (PLR resources used)
- State preconditions (requirements for each operation)
- Execution order

The extractor tracks variable types and infers preconditions from known
method patterns (e.g., `lh.transfer()` requires tips loaded).
"""

from typing import Any

import libcst as cst
from libcst.metadata import CodeRange, MetadataWrapper, PositionProvider

from praxis.backend.utils.plr_static_analysis.models import (
  GraphNodeType,
  OperationNode,
  PreconditionType,
  ProtocolComputationGraph,
  ResourceNode,
  StatePrecondition,
)
from praxis.backend.utils.plr_static_analysis.resource_hierarchy import (
  DeckLayoutType,
  get_parental_chain,
)
from praxis.common.type_inspection import (
  PLR_MACHINE_FRONTEND_TYPES,
  extract_resource_types,
  get_element_type,
  is_container_type,
)

# =============================================================================
# Method Patterns and Preconditions
# =============================================================================

# =============================================================================
# NOTE on provenance and derivation (backlog #4846, 260901)
# =============================================================================
# These five frozensets are hand-typed and audited against an AST-derived
# survey of the real PLR method surface (`training/verify/data/plr_preconditions.json`,
# PLR pin dd79c4c89 / 0.2.2) via `tests/utils/test_computation_graph.py::
# TestFrozensetsMatchPlrSurface`. That test is the durable guard: it asserts
# every member exists as a method on its declared receiver class(es) at the
# current pin, so a future PLR bump that renames/removes a method fails loudly
# here instead of silently dropping a precondition/creates_state edge.
#
# An adversarial round (260901) proposed *deriving* these sets automatically
# from PLR annotations instead of hand-typing them. That was measured and
# rejected: the derivation placed `pick_up_tips96` (a TIPS_LOADING_METHODS
# member, i.e. it CREATES tip state) into the derived TIPS_REQUIRED set — a
# typestate-inversion false positive that a naive "100% recall" metric does
# not catch, because recall says nothing about false positives. Do not retry
# derivation without first validating create/require *polarity*, not just
# coverage. Hand-typing + the regression test above is the current design.
# =============================================================================

# Methods that require tips to be loaded
# Receiver: LiquidHandler
TIPS_REQUIRED_METHODS: frozenset[str] = frozenset({
  "aspirate",
  "dispense",
  "transfer",
  "drop_tips",
  "return_tips",
})

# Methods that create "tips loaded" state
# Receiver: LiquidHandler
TIPS_LOADING_METHODS: frozenset[str] = frozenset({
  "pick_up_tips",
  "pick_up_tips96",
})

# Methods that remove "tips loaded" state
# Receiver: LiquidHandler
TIPS_DROPPING_METHODS: frozenset[str] = frozenset({
  "drop_tips",
  "drop_tips96",
  "return_tips",
})

# Methods that require plate access (not covered by lid)
# Receiver: LiquidHandler (aspirate/dispense/transfer) or PlateReader
# (read_absorbance/read_fluorescence/read_luminescence) — this set is
# intentionally receiver-polymorphic; see _determine_preconditions, which
# keys the PLATE_ACCESSIBLE precondition off the resource argument, not the
# receiver type.
PLATE_ACCESS_METHODS: frozenset[str] = frozenset({
  "aspirate",
  "dispense",
  "transfer",
  "read_absorbance",
  "read_fluorescence",
  "read_luminescence",
})

# Methods that move plates (require iSWAP or similar)
# Receiver: LiquidHandler
PLATE_MOVE_METHODS: frozenset[str] = frozenset({
  "move_plate",
  "move_lid",
})

# Variable name patterns that indicate machine type
MACHINE_VAR_PATTERNS: dict[str, str] = {
  "lh": "liquid_handler",
  "liquid_handler": "liquid_handler",
  "pr": "plate_reader",
  "plate_reader": "plate_reader",
  "reader": "plate_reader",
  "hs": "heater_shaker",
  "heater_shaker": "heater_shaker",
  "shaker": "shaker",
  "centrifuge": "centrifuge",
  "cf": "centrifuge",
  "tc": "thermocycler",
  "thermocycler": "thermocycler",
  "incubator": "incubator",
}


# =============================================================================
# Variable Type Tracker
# =============================================================================


class VariableTypeTracker:
  """Tracks variable types throughout a protocol function body.

  This class maintains a mapping of variable names to their inferred types,
  handling assignments, subscript operations, and attribute access.
  """

  def __init__(self, parameter_types: dict[str, str]) -> None:
    """Initialize with known parameter types.

    Args:
        parameter_types: Mapping of parameter names to their type hints.

    """
    self._types: dict[str, str] = parameter_types.copy()
    self._sources: dict[str, str] = {}  # Variable -> source expression

  def get_type(self, var_name: str) -> str | None:
    """Get the type for a variable."""
    return self._types.get(var_name)

  def set_type(self, var_name: str, type_hint: str, source: str | None = None) -> None:
    """Set the type for a variable."""
    self._types[var_name] = type_hint
    if source:
      self._sources[var_name] = source

  def get_source(self, var_name: str) -> str | None:
    """Get the source expression for a variable."""
    return self._sources.get(var_name)

  def infer_subscript_type(self, base_type: str, key: str) -> str:
    """Infer the type of a subscript operation.

    Args:
        base_type: Type of the base expression.
        key: The subscript key (e.g., "A1:A8").

    Returns:
        Inferred type of the subscript result.

    """
    # Plate["A1:A8"] -> list[Well]
    if "Plate" in base_type:
      if ":" in key:
        return "list[Well]"
      return "Well"

    # TipRack["A1:A8"] -> list[TipSpot]
    if "TipRack" in base_type:
      if ":" in key:
        return "list[TipSpot]"
      return "TipSpot"

    # list[X][0] -> X
    if base_type.startswith("list["):
      elem = get_element_type(base_type)
      if elem:
        return elem

    return base_type

  def infer_attribute_type(self, base_type: str, attr: str) -> str:
    """Infer the type of an attribute access.

    Args:
        base_type: Type of the base expression.
        attr: The attribute name.

    Returns:
        Inferred type of the attribute access.

    """
    # plate.wells() -> list[Well]
    if attr == "wells" and "Plate" in base_type:
      return "list[Well]"

    # tiprack.tips() -> list[TipSpot]
    if attr in ("tips", "tip_spots") and "TipRack" in base_type:
      return "list[TipSpot]"

    return "Any"


# =============================================================================
# Computation Graph Extractor
# =============================================================================


class ComputationGraphExtractor(cst.CSTVisitor):
  """Extracts a computation graph from a protocol function body.

  This visitor analyzes LibCST nodes to build a ProtocolComputationGraph
  containing operations, resources, preconditions, and execution order.

  Usage:
      extractor = ComputationGraphExtractor(
          protocol_fqn="my_module.my_protocol",
          parameter_types={"lh": "LiquidHandler", "plate": "Plate"},
      )
      function_node.body.walk(extractor)
      graph = extractor.build_graph()

  """

  # backlog #4948: PositionProvider gives every visited node's real
  # (line, column) span via `self.get_metadata(PositionProvider, node)`,
  # PROVIDED `self.metadata` was populated first -- see `_line_of` and the
  # `extract_graph_from_function`/`extract_graph_from_source` entry points
  # at the bottom of this file, which resolve it via `MetadataWrapper`
  # before any traversal starts.
  METADATA_DEPENDENCIES = (PositionProvider,)

  def __init__(
    self,
    protocol_fqn: str,
    parameter_types: dict[str, str],
    deck_layout_type: DeckLayoutType = DeckLayoutType.CARRIER_BASED,
  ) -> None:
    """Initialize the extractor.

    Args:
        protocol_fqn: Fully qualified name of the protocol function.
        parameter_types: Mapping of parameter names to their type hints.
        deck_layout_type: Type of deck layout for parental chain inference.

    """
    super().__init__()
    self._protocol_fqn = protocol_fqn
    self._protocol_name = protocol_fqn.rsplit(".", maxsplit=1)[-1] if "." in protocol_fqn else protocol_fqn
    self._deck_layout_type = deck_layout_type

    # Type tracking
    self._type_tracker = VariableTypeTracker(parameter_types)
    self._parameter_names = set(parameter_types.keys())

    # Graph components
    self._operations: list[OperationNode] = []
    self._resources: dict[str, ResourceNode] = {}
    self._preconditions: list[StatePrecondition] = []
    self._execution_order: list[str] = []

    # Body-accumulator stack (§12.2.2's restructure): the top of this stack
    # is where a newly emitted operation/region-header id is appended.
    # `self._execution_order` IS the bottom frame (same list object), so
    # top-level statements still land there unchanged; a region body pushes
    # a fresh frame, walks its statements into it, then pops it back out as
    # that region header's `foreach_body`/`true_branch`/`false_branch`.
    self._exec_stack: list[list[str]] = [self._execution_order]

    # State tracking
    self._active_states: set[str] = set()  # Currently active states (e.g., "tips_loaded")
    self._machine_types: set[str] = set()
    self._op_counter = 0
    self._precond_counter = 0
    self._has_loops = False
    self._has_conditionals = False

    # Initialize resources from parameters
    self._initialize_resources_from_params(parameter_types)

  def _line_of(self, node: cst.CSTNode) -> int:
    """Real source line for `node`, via the resolved `PositionProvider`.

    Falls back to `0` (the pre-#4948 constant) if metadata was never
    resolved for this node -- e.g. a caller that walks the extractor
    outside a `self.resolve(wrapper)` context, or a node that is not part
    of the wrapped tree (shouldn't happen via the public entry points, but
    fail soft rather than raise from deep inside a visit_* callback).
    """
    try:
      position: CodeRange = self.get_metadata(PositionProvider, node)
    except KeyError:
      return 0
    return position.start.line

  def _initialize_resources_from_params(self, parameter_types: dict[str, str]) -> None:
    """Create ResourceNode entries for all PLR resource parameters.

    backlog #4951: a parameter whose resolved primary type is a machine
    frontend (`lh: LiquidHandler`, `pr: PlateReader`, ...) is the receiver
    driving operations, never itself something placed on a deck -- it must
    not get a `ResourceNode`/`RESOURCE_ON_DECK` precondition. This was a
    live false-positive from `PLR_RESOURCE_TYPES` widening (b5635334) to
    include machine frontends for a DIFFERENT consumer's benefit
    (`is_pylabrobot_resource`'s "assets that need to be acquired at
    runtime" sense); `get_parental_chain("LiquidHandler", ...)` itself
    returns an empty chain -- corroborating that a machine simply doesn't
    fit this method's "resource -> deck" model at all.
    """
    for param_name, type_hint in parameter_types.items():
      resource_types = extract_resource_types(type_hint)
      if resource_types and resource_types[0] not in PLR_MACHINE_FRONTEND_TYPES:
        # This parameter is a PLR resource
        elem_type = get_element_type(type_hint)
        is_container = is_container_type(type_hint)

        # Get primary resource type for parental chain
        primary_type = elem_type or resource_types[0]
        chain = get_parental_chain(primary_type, self._deck_layout_type)

        self._resources[param_name] = ResourceNode(
          variable_name=param_name,
          declared_type=type_hint,
          element_type=elem_type,
          is_container=is_container,
          is_parameter=True,
          parental_chain=chain.chain,
        )

        # Add resource_on_deck precondition
        precond_id = self._create_precondition(
          PreconditionType.RESOURCE_ON_DECK,
          param_name,
          resource_type=primary_type,
        )
        # Mark as auto-satisfiable
        for p in self._preconditions:
          if p.id == precond_id:
            p.can_be_auto_satisfied = True

  def _generate_op_id(self) -> str:
    """Generate a unique operation ID."""
    self._op_counter += 1
    return f"op_{self._op_counter}"

  def _generate_precond_id(self) -> str:
    """Generate a unique precondition ID."""
    self._precond_counter += 1
    return f"precond_{self._precond_counter}"

  def _create_precondition(
    self,
    precond_type: PreconditionType,
    resource_var: str,
    resource_type: str | None = None,
    required_state: dict[str, Any] | None = None,
    satisfied_by: str | None = None,
  ) -> str:
    """Create a precondition and return its ID."""
    precond_id = self._generate_precond_id()
    self._preconditions.append(
      StatePrecondition(
        id=precond_id,
        precondition_type=precond_type,
        resource_variable=resource_var,
        resource_type=resource_type,
        required_state=required_state or {},
        satisfied_by=satisfied_by,
      )
    )
    return precond_id

  def _infer_machine_type(self, var_name: str) -> str | None:
    """Infer machine type from variable name."""
    lower_name = var_name.lower()
    for pattern, machine_type in MACHINE_VAR_PATTERNS.items():
      if pattern in lower_name:
        return machine_type
    return None

  def _get_expr_source(self, node: cst.BaseExpression) -> str:
    """Get source code string for an expression."""
    return cst.Module([]).code_for_node(node)

  def _get_receiver_info(
    self, func: cst.Attribute
  ) -> tuple[str, str | None]:
    """Extract receiver variable name and inferred type from attribute access.

    Returns:
        Tuple of (receiver_name, receiver_type).

    """
    receiver = func.value
    receiver_name = "?"

    if isinstance(receiver, cst.Name):
      receiver_name = receiver.value
    elif isinstance(receiver, cst.Attribute):
      # Handle chained access like self.lh.method()
      receiver_name = func.attr.value

    receiver_type = self._type_tracker.get_type(receiver_name)
    return receiver_name, receiver_type

  # ===========================================================================
  # Region emission (spec §12.2): visit_For/visit_While/visit_If restructure
  # the traversal from a flat single pass into a body-accumulator,
  # stack-scoped one. Each pushes a fresh accumulator frame, walks its own
  # body/branches into it via `_walk_body`, then either discards the frame
  # (body carried no operation the extractor would otherwise emit -- no
  # header, nothing enters the parent's execution order) or emits a single
  # `GraphNodeType.REGION` header `OperationNode` whose id is appended to the
  # PARENT frame (so it lands at the statement's own position) and whose
  # region field(s) list the frame's collected child ids -- never repeated at
  # top level (§12.2.2).
  # ===========================================================================

  def _push_body(self) -> None:
    """Push a fresh accumulator frame for a region body."""
    self._exec_stack.append([])

  def _pop_body(self) -> list[str]:
    """Pop and return the current accumulator frame's collected ids."""
    return self._exec_stack.pop()

  def _walk_body(self, node: cst.CSTNode) -> list[str]:
    """Walk `node` (a suite/body) into a fresh accumulator frame."""
    self._push_body()
    _walk_cst_node(node, self)
    return self._pop_body()

  def visit_For(self, node: cst.For) -> bool:  # noqa: N802
    """Emit a REGION header for a for-loop with >=1 body operation.

    A `for ... else` is explicitly out of scope (§12.2.4): its body and
    orelse are emitted as ordinary top-level operations exactly as before
    this restructure (`has_loops` still fires, so the retained synthetic
    wrap still catches it) -- returning True lets the generic walker
    descend without pushing a body frame at all.
    """
    self._has_loops = True
    if node.orelse is not None:
      return True

    foreach_source = self._get_expr_source(node.iter)
    body_ids = self._walk_body(node.body)
    if not body_ids:
      return False

    trip = self._proved_trip_count(node.iter, node.body)
    op_id = self._generate_op_id()
    self._operations.append(
      OperationNode(
        id=op_id,
        line_number=self._line_of(node),
        method_name="",
        receiver_variable="",
        receiver_type=None,
        arguments={},
        node_type=GraphNodeType.REGION,
        preconditions=[],
        creates_state=[],
        depends_on_params=[],
        foreach_source=foreach_source,
        foreach_body=body_ids,
        trip=trip,
      )
    )
    self._exec_stack[-1].append(op_id)
    return False

  def visit_While(self, node: cst.While) -> bool:  # noqa: N802
    """Emit a REGION header for a while-loop with >=1 body operation.

    `trip` is always `None` for a while (§12.2.3 -- no proof rule for a
    runtime condition). A `while ... else` is treated the same as a
    `for ... else` (§12.2.4's retained fallback, extended here for the same
    reason: there is no region shape for a second arm to live in without
    silently dropping its operations).
    """
    self._has_loops = True
    if node.orelse is not None:
      return True

    body_ids = self._walk_body(node.body)
    if not body_ids:
      return False

    op_id = self._generate_op_id()
    self._operations.append(
      OperationNode(
        id=op_id,
        line_number=self._line_of(node),
        method_name="",
        receiver_variable="",
        receiver_type=None,
        arguments={},
        node_type=GraphNodeType.REGION,
        preconditions=[],
        creates_state=[],
        depends_on_params=[],
        foreach_source=None,
        foreach_body=body_ids,
        trip=None,
      )
    )
    self._exec_stack[-1].append(op_id)
    return False

  def visit_If(self, node: cst.If) -> bool:  # noqa: N802
    """Emit a REGION header for an if/elif/else with >=1 body operation.

    An `elif` is a nested `If` directly in `node.orelse` (libcst's own
    shape), so it lowers as a nested header inside this header's own
    `false_branch` -- no flattening, no chain node (§12.2.4).
    """
    self._has_conditionals = True
    self._emit_if_region(node)
    return False

  def _emit_if_region(self, node: cst.If) -> None:
    condition_expr = self._get_expr_source(node.test)
    true_ids = self._walk_body(node.body)
    false_ids = self._walk_orelse(node.orelse)
    if not true_ids and not false_ids:
      return

    op_id = self._generate_op_id()
    self._operations.append(
      OperationNode(
        id=op_id,
        line_number=self._line_of(node),
        method_name="",
        receiver_variable="",
        receiver_type=None,
        arguments={},
        node_type=GraphNodeType.REGION,
        preconditions=[],
        creates_state=[],
        depends_on_params=[],
        condition_expr=condition_expr,
        true_branch=true_ids,
        false_branch=false_ids,
      )
    )
    self._exec_stack[-1].append(op_id)

  def _walk_orelse(self, orelse: cst.Else | cst.If | None) -> list[str]:
    """Walk an `If.orelse`.

    `None` (no else), an `Else` (plain else body), or a nested `If` (an
    elif -- recurse through `_emit_if_region` inside a fresh frame so the
    nested header's own id, if any, becomes this region's sole
    `false_branch` entry).
    """
    if orelse is None:
      return []
    if isinstance(orelse, cst.If):
      self._push_body()
      self._emit_if_region(orelse)
      return self._pop_body()
    return self._walk_body(orelse.body)

  # ===========================================================================
  # Proved trip counts (§12.2.3): language semantics only, from `range()`
  # int-literal forms, a literal list/tuple/set display, or
  # `range(<resource>.items_x | items_y)` against an already-known resource
  # grid -- withdrawn to `None` by a `Continue` anywhere in the body (any
  # nesting depth, excluding nested function/lambda defs, round-1 O7).
  # ===========================================================================

  def _proved_trip_count(
    self, iter_expr: cst.BaseExpression, body: cst.BaseSuite
  ) -> int | None:
    if self._body_has_continue(body):
      return None
    return self._proved_iterable_length(iter_expr)

  def _proved_iterable_length(self, expr: cst.BaseExpression) -> int | None:
    if isinstance(expr, cst.Call) and isinstance(expr.func, cst.Name) and expr.func.value == "range":
      return self._proved_range_length(expr)
    if isinstance(expr, (cst.List, cst.Tuple, cst.Set)):
      return len(expr.elements)
    return None

  def _proved_range_length(self, call: cst.Call) -> int | None:
    args = call.args
    if not args or any(a.star for a in args) or any(a.keyword is not None for a in args):
      return None

    if len(args) == 1:
      literal = self._int_literal(args[0].value)
      if literal is not None:
        return len(range(literal))
      item_count = self._resource_item_count(args[0].value)
      if item_count is not None:
        return len(range(item_count))
      return None

    if len(args) in (2, 3):
      values = [self._int_literal(a.value) for a in args]
      if any(v is None for v in values):
        return None
      # backlog #4951: `range(*values)` (star-unpacking a `list[int]`) has
      # no matching overload for `ty` -- `range.__new__`'s overloads are
      # keyed on ARITY (2 vs 3 positional ints), which a starred list
      # can't express statically. Narrow to an explicit `int` tuple (the
      # `is not None` filter above already proved every element is an
      # `int` at runtime; this re-states that for the type checker) and
      # branch on length instead, matching `range`'s own two real
      # constructor shapes.
      ints = tuple(v for v in values if v is not None)
      if len(ints) == 2:
        start, stop = ints
        return len(range(start, stop))
      start, stop, step = ints
      return len(range(start, stop, step))

    return None

  def _int_literal(self, node: cst.BaseExpression) -> int | None:
    if isinstance(node, cst.Integer):
      return int(node.value)
    if (
      isinstance(node, cst.UnaryOperation)
      and isinstance(node.operator, cst.Minus)
      and isinstance(node.expression, cst.Integer)
    ):
      return -int(node.expression.value)
    return None

  def _resource_item_count(self, node: cst.BaseExpression) -> int | None:
    """Resolve `<name>.items_x` / `<name>.items_y` against a known resource.

    `<name>` must be a declared resource whose `ResourceNode` already
    carries that grid dimension (§12.2.3 condition 3).
    """
    if not (isinstance(node, cst.Attribute) and isinstance(node.value, cst.Name)):
      return None
    if node.attr.value not in ("items_x", "items_y"):
      return None
    resource = self._resources.get(node.value.value)
    if resource is None:
      return None
    return resource.items_x if node.attr.value == "items_x" else resource.items_y

  def _body_has_continue(self, node: cst.CSTNode) -> bool:
    """Check for a `Continue` anywhere within `node`.

    Any nesting depth, EXCLUDING the body of a nested function/lambda
    definition (whose own `continue` would be a syntax error against this
    loop anyway).
    """
    if isinstance(node, (cst.FunctionDef, cst.Lambda)):
      return False
    if isinstance(node, cst.Continue):
      return True
    for child in node.children:
      if isinstance(child, cst.CSTNode) and self._body_has_continue(child):
        return True
    return False

  def visit_Assign(self, node: cst.Assign) -> bool:  # noqa: N802
    """Track variable assignments for type inference.

    Registers a `ResourceNode` for a bare-`Name` target, and (§12.2.5,
    round-1 O4) for a `self.<attr>` target too -- under
    `variable_name == f"self.{attr}"`, `is_parameter=False` -- so
    `self.plate_1["A1"]` has a resource slot for `lower_graph`'s value
    grammar to resolve a `Ref` against, closing the tier-1/tier-2 grammar
    residual §11.10 named.
    """
    for target in node.targets:
      t = target.target
      if isinstance(t, cst.Name):
        self._register_resource_assignment(t.value, node.value)
      elif (
        isinstance(t, cst.Attribute)
        and isinstance(t.value, cst.Name)
        and t.value.value == "self"
      ):
        self._register_resource_assignment(f"self.{t.attr.value}", node.value)

    return True

  def _register_resource_assignment(self, var_name: str, value: cst.BaseExpression) -> None:
    """Infer `value`'s type and register a `ResourceNode` if it is a PLR resource.

    Under `var_name` -- shared by both the bare-`Name` and `self.<attr>`
    assignment-target shapes.
    """
    source_expr = self._get_expr_source(value)
    inferred_type = self._infer_assignment_type(value)
    if not inferred_type:
      return

    self._type_tracker.set_type(var_name, inferred_type, source_expr)

    resource_types = extract_resource_types(inferred_type)
    # backlog #4951: same machine-frontend exclusion as
    # `_initialize_resources_from_params` -- see that method's docstring.
    if resource_types and resource_types[0] not in PLR_MACHINE_FRONTEND_TYPES:
      elem_type = get_element_type(inferred_type)
      primary_type = elem_type or resource_types[0]
      chain = get_parental_chain(primary_type, self._deck_layout_type)

      self._resources[var_name] = ResourceNode(
        variable_name=var_name,
        declared_type=inferred_type,
        element_type=elem_type,
        is_container=is_container_type(inferred_type),
        is_parameter=False,
        parental_chain=chain.chain,
        source_expression=source_expr,
      )

  def _infer_assignment_type(self, value: cst.BaseExpression) -> str | None:
    """Infer the type of an assignment value."""
    # Handle subscript: plate["A1:A8"]
    if isinstance(value, cst.Subscript):
      base_name = self._get_expr_source(value.value)
      base_type = self._type_tracker.get_type(base_name)
      if base_type:
        # Get the subscript key
        if value.slice and isinstance(value.slice[0].slice, cst.Index):
          key_node = value.slice[0].slice.value
          if isinstance(key_node, cst.SimpleString | cst.ConcatenatedString):
            key = self._get_expr_source(key_node).strip("\"'")
            return self._type_tracker.infer_subscript_type(base_type, key)
        # Default to list of element type
        elem = get_element_type(base_type)
        if elem:
          return f"list[{elem}]"
      return None

    # Handle attribute access: plate.wells()
    if isinstance(value, cst.Call) and isinstance(value.func, cst.Attribute):
      base_name = self._get_expr_source(value.func.value)
      base_type = self._type_tracker.get_type(base_name)
      attr_name = value.func.attr.value
      if base_type:
        return self._type_tracker.infer_attribute_type(base_type, attr_name)

    # Handle simple name reference
    if isinstance(value, cst.Name):
      return self._type_tracker.get_type(value.value)

    return None

  def visit_Call(self, node: cst.Call) -> bool:  # noqa: N802
    """Process method calls to extract operations."""
    # Only process attribute method calls (e.g., lh.aspirate())
    if not isinstance(node.func, cst.Attribute):
      return True

    method_name = node.func.attr.value
    receiver_name, receiver_type = self._get_receiver_info(node.func)

    # Check if this is a machine method call
    machine_type = self._infer_machine_type(receiver_name)
    if machine_type:
      self._machine_types.add(machine_type)

      # Create operation node
      op_id = self._generate_op_id()
      args = self._extract_arguments(node)

      # Determine preconditions for this operation
      precondition_ids = self._determine_preconditions(method_name, args, receiver_name)

      # Check if this operation creates state
      creates = []
      if method_name in TIPS_LOADING_METHODS:
        creates.append("tips_loaded")
        self._active_states.add("tips_loaded")
        # Satisfy any tips_loaded preconditions from this operation
        for p in self._preconditions:
          if (
            p.precondition_type == PreconditionType.TIPS_LOADED
            and p.satisfied_by is None
          ):
            p.satisfied_by = op_id

      if method_name in TIPS_DROPPING_METHODS:
        self._active_states.discard("tips_loaded")

      # Determine node type
      node_type = GraphNodeType.STATIC
      depends_on = []
      for arg_expr in args.values():
        if arg_expr in self._parameter_names:
          depends_on.append(arg_expr)
          node_type = GraphNodeType.DYNAMIC

      operation = OperationNode(
        id=op_id,
        line_number=self._line_of(node),
        method_name=method_name,
        receiver_variable=receiver_name,
        receiver_type=receiver_type,
        arguments=args,
        node_type=node_type,
        preconditions=precondition_ids,
        creates_state=creates,
        depends_on_params=depends_on,
      )

      self._operations.append(operation)
      self._exec_stack[-1].append(op_id)

    return True

  def _extract_arguments(self, node: cst.Call) -> dict[str, str]:
    """Extract arguments from a Call node."""
    args: dict[str, str] = {}

    # Positional arguments (try to use common names)
    common_arg_names = ["resource", "volume", "source", "destination", "tips"]
    for i, arg in enumerate(node.args):
      if arg.keyword:
        arg_name = arg.keyword.value
      elif i < len(common_arg_names):
        arg_name = common_arg_names[i]
      else:
        arg_name = f"arg{i}"

      args[arg_name] = self._get_expr_source(arg.value)

    return args

  def _determine_preconditions(
    self,
    method_name: str,
    args: dict[str, str],
    receiver_name: str,
  ) -> list[str]:
    """Determine preconditions required for an operation."""
    precondition_ids: list[str] = []

    # Tips required?
    if method_name in TIPS_REQUIRED_METHODS and "tips_loaded" not in self._active_states:
      precond_id = self._create_precondition(
        PreconditionType.TIPS_LOADED,
        receiver_name,
        resource_type="TipRack",
      )
      precondition_ids.append(precond_id)

    # Plate access required?
    if method_name in PLATE_ACCESS_METHODS:
      # Check first argument for resource variable
      resource_arg = args.get("resource") or args.get("source")
      if resource_arg:
        # Extract base variable name
        base_var = resource_arg.split("[")[0].split(".")[0].strip()
        if base_var in self._resources:
          precond_id = self._create_precondition(
            PreconditionType.PLATE_ACCESSIBLE,
            base_var,
            resource_type=self._resources[base_var].declared_type,
          )
          precondition_ids.append(precond_id)

    return precondition_ids

  def build_graph(self) -> ProtocolComputationGraph:
    """Build the final ProtocolComputationGraph."""
    # Collect all resource types
    resource_types: set[str] = set()
    for res in self._resources.values():
      for rt in extract_resource_types(res.declared_type):
        resource_types.add(rt)

    return ProtocolComputationGraph(
      protocol_fqn=self._protocol_fqn,
      protocol_name=self._protocol_name,
      operations=self._operations,
      resources=self._resources,
      preconditions=self._preconditions,
      execution_order=self._execution_order,
      machine_types=sorted(self._machine_types),
      resource_types=sorted(resource_types),
      has_loops=self._has_loops,
      has_conditionals=self._has_conditionals,
    )


# =============================================================================
# Convenience Functions
# =============================================================================


def extract_graph_from_function(
  function_node: cst.FunctionDef,
  module_name: str,
  parameter_types: dict[str, str] | None = None,
  deck_layout_type: DeckLayoutType = DeckLayoutType.CARRIER_BASED,
  *,
  _wrapper: MetadataWrapper | None = None,
) -> ProtocolComputationGraph:
  """Extract a computation graph from a function definition.

  Args:
      function_node: The LibCST FunctionDef node to analyze.
      module_name: The module name for FQN generation.
      parameter_types: Optional pre-extracted parameter types.
      deck_layout_type: Type of deck layout.
      _wrapper: Internal-only. A `MetadataWrapper` that already contains
          `function_node` (i.e. `function_node` is (a descendant of) one of
          `_wrapper.module.body`'s statements) -- passed by
          `extract_graph_from_source`, which already has the real, full
          module in hand and wraps it ONCE so `OperationNode.line_number`
          reflects the function's real position within that source, not a
          position relative to a synthetic one-function module. Public
          callers (e.g. `protocol_discovery.py`, which only ever has a bare
          `function_node`) leave this `None`: a synthetic single-function
          module is wrapped instead, which still gives every call/region a
          real, distinct, non-zero line number (backlog #4948) -- just
          relative to that function's own text, since no wider module
          context is available to this call shape.

  Returns:
      The extracted ProtocolComputationGraph.

  """
  func_name = function_node.name.value
  fqn = f"{module_name}.{func_name}"

  # Extract parameter types if not provided
  if parameter_types is None:
    parameter_types = {}
    for param in function_node.params.params:
      param_name = param.name.value
      if param.annotation:
        type_hint = cst.Module([]).code_for_node(param.annotation.annotation)
        parameter_types[param_name] = type_hint
      else:
        parameter_types[param_name] = "Any"

  extractor = ComputationGraphExtractor(
    protocol_fqn=fqn,
    parameter_types=parameter_types,
    deck_layout_type=deck_layout_type,
  )

  # backlog #4948: resolve PositionProvider metadata via MetadataWrapper so
  # `OperationNode.line_number` is real. `MetadataWrapper.__init__` deep-
  # clones its module by default, which means node IDENTITY (what
  # PositionProvider's mapping is keyed on) only matches between
  # `wrapper.module`'s own nodes -- so the walk below must start from
  # `wrapped_function` (a node reachable from `wrapper.module`), never from
  # the caller's original `function_node`.
  if _wrapper is not None:
    wrapper = _wrapper
    wrapped_function = function_node
  else:
    wrapper = MetadataWrapper(cst.Module(body=[function_node]))
    wrapped_function = wrapper.module.body[0]

  # `extractor.resolve(wrapper)` is what `MetadataWrapper.visit()` does
  # under the hood before delegating to `self.module.visit(visitor)`
  # (`libcst/metadata/wrapper.py`); we reuse the same resolve step but keep
  # our own scoped traversal (`_walk_cst_node`, starting at just the target
  # function) rather than `wrapper.visit()`'s whole-module traversal, since
  # `extract_graph_from_source` may hand in a wrapper over a module with
  # OTHER top-level statements (imports, sibling functions) that must not
  # be visited here.
  with extractor.resolve(wrapper):
    _walk_cst_node(wrapped_function, extractor)

  return extractor.build_graph()


def _walk_cst_node(node: cst.CSTNode, visitor: cst.CSTVisitor) -> None:
  """Manually walk a CST node with a visitor.

  LibCST's walk method is only available on Module, so we need to
  manually traverse the tree for other node types.
  """
  # Visit this node
  should_descend = True

  # Check for visitor methods
  node_type = type(node).__name__
  visit_method = getattr(visitor, f"visit_{node_type}", None)
  if visit_method:
    result = visit_method(node)
    if result is False:
      should_descend = False

  # Descend into children if allowed
  if should_descend:
    for child in node.children:
      if isinstance(child, cst.CSTNode):
        _walk_cst_node(child, visitor)


def extract_graph_from_source(
  source: str,
  function_name: str,
  module_name: str = "protocol",
  deck_layout_type: DeckLayoutType = DeckLayoutType.CARRIER_BASED,
) -> ProtocolComputationGraph | None:
  """Extract a computation graph from source code.

  Args:
      source: Python source code containing the function.
      function_name: Name of the function to extract.
      module_name: Module name for FQN generation.
      deck_layout_type: Type of deck layout.

  Returns:
      The extracted ProtocolComputationGraph, or None if function not found.

  """
  try:
    tree = cst.parse_module(source)
  except cst.ParserSyntaxError:
    return None

  # backlog #4948: wrap the REAL, full module once so line numbers are
  # correct relative to `source` as a whole (not just the extracted
  # function's own text) -- `MetadataWrapper` deep-clones `tree`, so the
  # target `FunctionDef` must be looked up in `wrapper.module.body` (the
  # clone), not `tree.body` (node identity is what PositionProvider keys
  # on; the two trees are structurally identical but distinct objects).
  wrapper = MetadataWrapper(tree)

  # Find the function
  for stmt in wrapper.module.body:
    if isinstance(stmt, cst.FunctionDef) and stmt.name.value == function_name:
      return extract_graph_from_function(
        stmt, module_name, deck_layout_type=deck_layout_type, _wrapper=wrapper
      )

  return None
