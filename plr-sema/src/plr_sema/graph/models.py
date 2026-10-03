"""plr_sema.graph.models: the protocol computation-graph models.

Moved verbatim from ``praxis/backend/utils/plr_static_analysis/models.py``
lines 504-671 (at e06ab3b1) by spec 261002 Slice 1; praxis re-exports them.
``plr_sema.check.graph`` is the stdlib mirror of these classes and
``tests/test_check_graph_mirror_drift.py`` keeps the two in step.
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

# =============================================================================
# Computation Graph Models
# =============================================================================


class GraphNodeType(str, Enum):
  """Classification of computation graph nodes."""

  STATIC = "static"  # Can be pre-computed/evaluated at analysis time
  DYNAMIC = "dynamic"  # Requires runtime data
  CONDITIONAL = "conditional"  # Branches based on runtime value
  FOREACH = "foreach"  # Loop over collection
  REGION = "region"  # A for/while/if region-header node; emits no CALL (spec §12.2.2)


class PreconditionType(str, Enum):
  """Types of state preconditions for operations."""

  RESOURCE_ON_DECK = "resource_on_deck"  # Resource must be placed on deck
  TIPS_LOADED = "tips_loaded"  # Tips must be picked up
  LIQUID_PRESENT = "liquid_present"  # Liquid must be present in container
  PLATE_ACCESSIBLE = "plate_accessible"  # Plate must be accessible (not covered)
  TEMPERATURE_STABLE = "temperature_stable"  # Temperature must be stable
  MACHINE_READY = "machine_ready"  # Machine must be initialized/ready


class OperationNode(BaseModel):
  """A single operation in the protocol execution graph.

  Represents a method call like `lh.aspirate(source, 100)` with its
  arguments, preconditions, and metadata.
  """

  id: str = Field(description="Unique identifier for this operation")
  line_number: int = Field(description="Source line number")
  method_name: str = Field(description="Method being called (e.g., 'transfer')")
  receiver_variable: str = Field(description="Variable receiving the call (e.g., 'lh')")
  receiver_type: str | None = Field(default=None, description="Inferred type of receiver")
  arguments: dict[str, str] = Field(
    default_factory=dict, description="Arg name -> variable/expression"
  )
  node_type: GraphNodeType = Field(
    default=GraphNodeType.STATIC, description="Classification of this node"
  )
  preconditions: list[str] = Field(default_factory=list, description="Required precondition IDs")
  creates_state: list[str] = Field(
    default_factory=list, description="State IDs this operation creates"
  )
  depends_on_params: list[str] = Field(
    default_factory=list, description="Parameter names this operation depends on"
  )

  # For foreach nodes
  foreach_source: str | None = Field(
    default=None, description="Variable being iterated (for foreach nodes)"
  )
  foreach_body: list[str] = Field(default_factory=list, description="Child node IDs in loop body")
  trip: int | None = Field(
    default=None,
    description=(
      "Proved trip count for a REGION loop header, or null when unprovable "
      "(spec §12.2.3: range()/list-display/items_x-or-items_y literals only, "
      "withdrawn by a Continue anywhere in the body; a while region is always "
      "null). Meaningless outside a REGION node whose foreach_body is set."
    ),
  )

  # For conditional nodes
  condition_expr: str | None = Field(default=None, description="Condition expression")
  true_branch: list[str] = Field(default_factory=list, description="True branch node IDs")
  false_branch: list[str] = Field(default_factory=list, description="False branch node IDs")


class ResourceNode(BaseModel):
  """A resource referenced in the protocol.

  Represents a protocol parameter or variable that holds a PLR resource.
  """

  variable_name: str = Field(description="Variable name in protocol")
  declared_type: str = Field(description="Type as declared in signature/assignment")
  element_type: str | None = Field(
    default=None, description="For containers like list[Well], the element type"
  )
  is_container: bool = Field(
    default=False, description="Whether this is a container type (list, Sequence)"
  )
  is_parameter: bool = Field(default=True, description="Whether this is a function parameter")
  parental_chain: list[str] = Field(
    default_factory=list, description="Parent types from resource to deck"
  )
  source_expression: str | None = Field(
    default=None, description="Expression this was derived from (e.g., 'plate[\"A1:A8\"]')"
  )
  items_x: int | None = Field(
    default=None,
    description="Number of columns in the resource grid (for index selector inference)",
  )
  items_y: int | None = Field(
    default=None, description="Number of rows in the resource grid (for index selector inference)"
  )


class StatePrecondition(BaseModel):
  """A condition that must be true for an operation to succeed.

  Represents requirements like "tips must be loaded" or "plate must be on deck".
  """

  id: str = Field(description="Unique identifier for this precondition")
  precondition_type: PreconditionType = Field(description="Type of precondition")
  resource_variable: str = Field(description="Variable name of affected resource")
  resource_type: str | None = Field(default=None, description="Type of the resource")
  required_state: dict[str, Any] = Field(
    default_factory=dict, description="Required state attributes"
  )
  can_be_auto_satisfied: bool = Field(
    default=True, description="Whether system can auto-satisfy this"
  )
  satisfied_by: str | None = Field(
    default=None, description="Operation ID that satisfies this precondition"
  )


class ProtocolComputationGraph(BaseModel):
  """Complete computational graph for a protocol.

  This is the main output of the graph extraction process, containing
  all operations, resources, preconditions, and execution order.
  """

  protocol_fqn: str = Field(description="Fully qualified name of the protocol function")
  protocol_name: str = Field(description="Simple name of the protocol function")

  operations: list[OperationNode] = Field(
    default_factory=list, description="All operation nodes in execution order"
  )
  resources: dict[str, ResourceNode] = Field(
    default_factory=dict, description="Variable name -> ResourceNode mapping"
  )
  preconditions: list[StatePrecondition] = Field(
    default_factory=list, description="All state preconditions"
  )
  execution_order: list[str] = Field(
    default_factory=list, description="Operation IDs in execution order"
  )

  # Summary fields
  machine_types: list[str] = Field(
    default_factory=list, description="Machine types used (liquid_handler, plate_reader, etc.)"
  )
  resource_types: list[str] = Field(
    default_factory=list, description="All PLR resource types referenced"
  )
  has_loops: bool = Field(default=False, description="Whether protocol contains loops")
  has_conditionals: bool = Field(
    default=False, description="Whether protocol contains conditionals"
  )

  def get_unsatisfied_preconditions(self) -> list[StatePrecondition]:
    """Get preconditions not satisfied by any operation in the graph."""
    return [p for p in self.preconditions if p.satisfied_by is None]

  def get_operation(self, op_id: str) -> OperationNode | None:
    """Get an operation by its ID."""
    for op in self.operations:
      if op.id == op_id:
        return op
    return None

  def get_resource(self, var_name: str) -> ResourceNode | None:
    """Get a resource by its variable name."""
    return self.resources.get(var_name)
