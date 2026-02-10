"""Pydantic models for PLR static analysis results."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

# =============================================================================
# Capability Configuration Schemas (User Input)
# =============================================================================


class CapabilityConfigField(BaseModel):
  """Field definition for user-configurable capability."""

  field_name: str
  display_name: str
  field_type: Literal["boolean", "number", "select", "multiselect", "text"]
  default_value: Any
  options: list[str] | None = None  # For select/multiselect
  help_text: str | None = None
  depends_on: str | None = None  # Conditional visibility
  required: bool = False  # Whether field is required
  min: float | None = None  # Minimum value for number fields
  max: float | None = None  # Maximum value for number fields


class MachineCapabilityConfigSchema(BaseModel):
  """Schema for dynamic capability configuration form."""

  machine_type: str  # e.g., "liquid_handler"
  machine_fqn_pattern: str | None = None  # e.g., "*STAR*" for Hamilton STAR
  config_fields: list[CapabilityConfigField]


# =============================================================================
# Capability Requirements (Protocol → Machine Matching)
# These models define requirements extracted from protocols and matching results.
# =============================================================================


class CapabilityRequirement(BaseModel):
  """A single hardware capability requirement inferred from protocol code.

  Used by ProtocolRequirementExtractor to capture inferred requirements from
  static analysis of protocol function bodies.
  """

  capability_name: str  # e.g., "has_core96", "has_iswap", "channels"
  expected_value: Any  # e.g., True, 8, ["absorbance"]
  operator: Literal["eq", "gt", "gte", "lt", "lte", "in", "contains"] = "eq"
  inferred_from: str | None = None  # e.g., "lh.pick_up_tips96()"
  machine_type: str | None = None  # e.g., "liquid_handler" - helps categorize


class ProtocolRequirements(BaseModel):
  """Collection of hardware requirements for a protocol.

  Extracted during protocol discovery and stored in FunctionProtocolDefinition.
  """

  machine_type: str | None = None  # Primary machine type required (e.g., "liquid_handler")
  requirements: list[CapabilityRequirement] = Field(default_factory=list)
  inferred_at: str | None = None  # Timestamp of when requirements were inferred


class CapabilityMatchResult(BaseModel):
  """Result of matching protocol requirements to machine capabilities.

  Returned by CapabilityMatcherService to indicate compatibility.
  """

  is_compatible: bool
  missing_capabilities: list[CapabilityRequirement] = Field(default_factory=list)
  matched_capabilities: list[str] = Field(default_factory=list)
  warnings: list[str] = Field(default_factory=list)
  machine_id: str | None = None  # UUID of the machine checked
  protocol_id: str | None = None  # UUID of the protocol checked


# =============================================================================
# Protocol Inspection Models
# =============================================================================


class ProtocolParameterInfo(BaseModel):
  """Information about a parameter in a protocol function."""

  name: str
  type_hint: str
  default_value: str | None = None
  is_optional: bool = False
  is_asset: bool = False  # True if type is a PLR Resource
  # Asset specific fields
  asset_type: str | None = None
  fqn: str | None = None
  # UI field type for rendering (e.g., "text", "number", "index_selector")
  field_type: str | None = None
  # True if the type is an itemized resource (Well, TipSpot) or collection thereof
  is_itemized: bool = False
  # Specification for index selector (items_x, items_y for parent resource)
  itemized_spec: dict[str, Any] | None = None
  # Link ID for linked index selectors (e.g., source/dest wells)
  linked_to: str | None = None


class ProtocolFunctionInfo(BaseModel):
  """Information extracted from a @protocol_function decorated function."""

  name: str
  fqn: str
  module_name: str
  source_file_path: str
  docstring: str | None = None
  parameters: list[ProtocolParameterInfo] = Field(default_factory=list)
  # Raw data for backward compatibility with discovery service dicts
  raw_assets: list[dict[str, Any]] = Field(default_factory=list)
  raw_parameters: list[dict[str, Any]] = Field(default_factory=list)
  hardware_requirements: dict[str, Any] | None = None
  # Computation graph extracted from the function body
  computation_graph: dict[str, Any] | None = None
  source_hash: str | None = None
  # Whether this protocol requires deck setup (False for machine-only protocols)
  requires_deck: bool = True


# =============================================================================
# Machine-Type Specific Capability Schemas
# These schemas capture capabilities unique to each machine type.
# =============================================================================


class LiquidHandlerCapabilities(BaseModel):
  """Capabilities specific to liquid handlers."""

  channels: list[int] = Field(default_factory=list)
  has_iswap: bool = False
  has_core96: bool = False
  has_hepa: bool = False
  pipette_type: str | None = None  # "fixed", "disposable"
  volume_range_ul: tuple[float, float] | None = None


class PlateReaderCapabilities(BaseModel):
  """Capabilities specific to plate readers."""

  absorbance: bool = False
  fluorescence: bool = False
  luminescence: bool = False
  imaging: bool = False


class HeaterShakerCapabilities(BaseModel):
  """Capabilities specific to heater shakers."""

  max_temperature_c: float | None = None
  min_temperature_c: float | None = None
  max_speed_rpm: int | None = None
  has_cooling: bool = False


class ShakerCapabilities(BaseModel):
  """Capabilities specific to shakers (no heating)."""

  max_speed_rpm: int | None = None
  orbit_diameter_mm: float | None = None


class TemperatureControllerCapabilities(BaseModel):
  """Capabilities specific to temperature controllers."""

  max_temperature_c: float | None = None
  min_temperature_c: float | None = None
  has_cooling: bool = False


class CentrifugeCapabilities(BaseModel):
  """Capabilities specific to centrifuges."""

  max_rpm: int | None = None
  max_g: int | None = None
  temperature_controlled: bool = False


class ThermocyclerCapabilities(BaseModel):
  """Capabilities specific to thermocyclers."""

  max_temperature_c: float | None = None
  min_temperature_c: float | None = None
  ramp_rate_c_per_s: float | None = None
  lid_heated: bool = False


class PumpCapabilities(BaseModel):
  """Capabilities specific to pumps."""

  max_flow_rate_ml_min: float | None = None
  min_flow_rate_ml_min: float | None = None
  reversible: bool = False
  num_channels: int = 1


class FanCapabilities(BaseModel):
  """Capabilities specific to fans."""

  max_speed_rpm: int | None = None
  variable_speed: bool = False


class SealerCapabilities(BaseModel):
  """Capabilities for plate sealers."""

  max_temperature_c: float | None = None
  seal_time_s: float | None = None


class PeelerCapabilities(BaseModel):
  """Capabilities for plate peelers."""

  # Most peelers have no configurable capabilities


class PowderDispenserCapabilities(BaseModel):
  """Capabilities for powder dispensers."""

  min_dispense_mg: float | None = None
  max_dispense_mg: float | None = None


class IncubatorCapabilities(BaseModel):
  """Capabilities for incubators."""

  max_temperature_c: float | None = None
  min_temperature_c: float | None = None
  has_co2_control: bool = False
  has_humidity_control: bool = False


class ScaraCapabilities(BaseModel):
  """Capabilities for SCARA robotic arms."""

  reach_mm: float | None = None
  payload_kg: float | None = None


class GenericMachineCapabilities(BaseModel):
  """Fallback for machine types without specific schemas."""

  raw_capabilities: dict[str, Any] = Field(default_factory=dict)


# Union type for all machine-specific capabilities
MachineCapabilities = (
  LiquidHandlerCapabilities
  | PlateReaderCapabilities
  | HeaterShakerCapabilities
  | ShakerCapabilities
  | TemperatureControllerCapabilities
  | CentrifugeCapabilities
  | ThermocyclerCapabilities
  | PumpCapabilities
  | FanCapabilities
  | SealerCapabilities
  | PeelerCapabilities
  | PowderDispenserCapabilities
  | IncubatorCapabilities
  | ScaraCapabilities
  | GenericMachineCapabilities
)


# =============================================================================
# PLR Class Types
# =============================================================================


class PLRClassType(str, Enum):
  """Classification of PLR class types."""

  # Machine frontends (user-facing API)
  LIQUID_HANDLER = "liquid_handler"
  PLATE_READER = "plate_reader"
  HEATER_SHAKER = "heater_shaker"
  SHAKER = "shaker"
  TEMPERATURE_CONTROLLER = "temperature_controller"
  CENTRIFUGE = "centrifuge"
  THERMOCYCLER = "thermocycler"
  PUMP = "pump"
  PUMP_ARRAY = "pump_array"
  FAN = "fan"
  SEALER = "sealer"
  PEELER = "peeler"
  POWDER_DISPENSER = "powder_dispenser"
  INCUBATOR = "incubator"
  SCARA = "scara"
  IMAGER = "imager"

  # Machine backends (hardware drivers)
  LH_BACKEND = "liquid_handler_backend"
  PR_BACKEND = "plate_reader_backend"
  HS_BACKEND = "heater_shaker_backend"
  SHAKER_BACKEND = "shaker_backend"
  TEMP_BACKEND = "temperature_controller_backend"
  CENTRIFUGE_BACKEND = "centrifuge_backend"
  THERMOCYCLER_BACKEND = "thermocycler_backend"
  PUMP_BACKEND = "pump_backend"
  PUMP_ARRAY_BACKEND = "pump_array_backend"
  FAN_BACKEND = "fan_backend"
  SEALER_BACKEND = "sealer_backend"
  PEELER_BACKEND = "peeler_backend"
  POWDER_DISPENSER_BACKEND = "powder_dispenser_backend"
  INCUBATOR_BACKEND = "incubator_backend"
  SCARA_BACKEND = "scara_backend"
  IMAGER_BACKEND = "imager_backend"

  # Infrastructure types
  DECK = "deck"
  RESOURCE = "resource"
  CARRIER = "carrier"
  UNKNOWN = "unknown"

  def is_machine_frontend(self) -> bool:
    """Check if this is a machine frontend type."""
    return self in MACHINE_FRONTEND_TYPES

  def is_machine_backend(self) -> bool:
    """Check if this is a machine backend type."""
    return self in MACHINE_BACKEND_TYPES

  def get_compatible_backend_type(self) -> "PLRClassType | None":
    """Get the corresponding backend type for a frontend."""
    return FRONTEND_TO_BACKEND_MAP.get(self)


# Sets for type checking
MACHINE_FRONTEND_TYPES: frozenset[PLRClassType] = frozenset()  # Populated after class def
MACHINE_BACKEND_TYPES: frozenset[PLRClassType] = frozenset()  # Populated after class def
FRONTEND_TO_BACKEND_MAP: dict[PLRClassType, PLRClassType] = {}  # Populated after class def


class DiscoveredCapabilities(BaseModel):
  """Capabilities extracted from a PLR class."""

  channels: list[int] = Field(default_factory=list)
  modules: list[str] = Field(default_factory=list)
  has_core96: bool = False
  has_iswap: bool = False
  num_items_x: int | None = None
  num_items_y: int | None = None


class DiscoveredClass(BaseModel):
  """A PLR class discovered via static analysis."""

  fqn: str
  name: str
  module_path: str
  file_path: str
  class_type: PLRClassType
  base_classes: list[str] = Field(default_factory=list)
  is_abstract: bool = False
  docstring: str | None = None
  manufacturer: str | None = None
  model_name: str | None = None
  capabilities: DiscoveredCapabilities = Field(default_factory=DiscoveredCapabilities)
  machine_capabilities: MachineCapabilities | None = None
  compatible_backends: list[str] = Field(default_factory=list)
  capabilities_config: MachineCapabilityConfigSchema | None = None
  connection_config: MachineCapabilityConfigSchema | None = None
  category: str | None = None
  vendor: str | None = None

  def is_simulated(self) -> bool:
    """Check if this is a simulated machine class."""
    name_lower = self.name.lower()
    return any(s in name_lower for s in ["simulat", "chatterbox", "mock", "virtual"])

  def to_capabilities_dict(self) -> dict[str, Any]:
    """Convert capabilities to the format expected by MachineDefinition.

    Merges legacy DiscoveredCapabilities with typed MachineCapabilities.
    """
    caps = self.capabilities
    result: dict[str, Any] = {
      "channels": caps.channels,
      "modules": list(set(caps.modules)),
    }
    if caps.has_core96:
      result["has_core96"] = True
    if caps.has_iswap:
      result["has_iswap"] = True

    # Merge typed machine capabilities if present
    if self.machine_capabilities is not None:
      typed_caps = self.machine_capabilities.model_dump(exclude_none=True)
      # Avoid overwriting legacy fields with empty defaults
      for key, value in typed_caps.items():
        if key not in result or result[key] in ([], None, False):
          result[key] = value

    return result


class DiscoveredBackend(DiscoveredClass):
  """A PLR backend class with additional channel information."""

  num_channels_default: int | None = None
  num_channels_property: bool = False


# Populate type sets after class definition
# Using object.__setattr__ to work around module-level frozenset reassignment
_frontend_types = frozenset(
  {
    PLRClassType.LIQUID_HANDLER,
    PLRClassType.PLATE_READER,
    PLRClassType.HEATER_SHAKER,
    PLRClassType.SHAKER,
    PLRClassType.TEMPERATURE_CONTROLLER,
    PLRClassType.CENTRIFUGE,
    PLRClassType.THERMOCYCLER,
    PLRClassType.PUMP,
    PLRClassType.PUMP_ARRAY,
    PLRClassType.FAN,
    PLRClassType.SEALER,
    PLRClassType.PEELER,
    PLRClassType.POWDER_DISPENSER,
    PLRClassType.INCUBATOR,
    PLRClassType.SCARA,
    PLRClassType.IMAGER,
  }
)

_backend_types = frozenset(
  {
    PLRClassType.LH_BACKEND,
    PLRClassType.PR_BACKEND,
    PLRClassType.HS_BACKEND,
    PLRClassType.SHAKER_BACKEND,
    PLRClassType.TEMP_BACKEND,
    PLRClassType.CENTRIFUGE_BACKEND,
    PLRClassType.THERMOCYCLER_BACKEND,
    PLRClassType.PUMP_BACKEND,
    PLRClassType.PUMP_ARRAY_BACKEND,
    PLRClassType.FAN_BACKEND,
    PLRClassType.SEALER_BACKEND,
    PLRClassType.PEELER_BACKEND,
    PLRClassType.POWDER_DISPENSER_BACKEND,
    PLRClassType.INCUBATOR_BACKEND,
    PLRClassType.SCARA_BACKEND,
    PLRClassType.IMAGER_BACKEND,
  }
)

_frontend_to_backend = {
  PLRClassType.LIQUID_HANDLER: PLRClassType.LH_BACKEND,
  PLRClassType.PLATE_READER: PLRClassType.PR_BACKEND,
  PLRClassType.HEATER_SHAKER: PLRClassType.HS_BACKEND,
  PLRClassType.SHAKER: PLRClassType.SHAKER_BACKEND,
  PLRClassType.TEMPERATURE_CONTROLLER: PLRClassType.TEMP_BACKEND,
  PLRClassType.CENTRIFUGE: PLRClassType.CENTRIFUGE_BACKEND,
  PLRClassType.THERMOCYCLER: PLRClassType.THERMOCYCLER_BACKEND,
  PLRClassType.PUMP: PLRClassType.PUMP_BACKEND,
  PLRClassType.PUMP_ARRAY: PLRClassType.PUMP_ARRAY_BACKEND,
  PLRClassType.FAN: PLRClassType.FAN_BACKEND,
  PLRClassType.SEALER: PLRClassType.SEALER_BACKEND,
  PLRClassType.PEELER: PLRClassType.PEELER_BACKEND,
  PLRClassType.POWDER_DISPENSER: PLRClassType.POWDER_DISPENSER_BACKEND,
  PLRClassType.INCUBATOR: PLRClassType.INCUBATOR_BACKEND,
  PLRClassType.SCARA: PLRClassType.SCARA_BACKEND,
  PLRClassType.IMAGER: PLRClassType.IMAGER_BACKEND,
}

# Update module-level constants
MACHINE_FRONTEND_TYPES = _frontend_types
MACHINE_BACKEND_TYPES = _backend_types
FRONTEND_TO_BACKEND_MAP = _frontend_to_backend

# Backend type → Frontend FQN mapping for code generation
BACKEND_TYPE_TO_FRONTEND_FQN: dict[PLRClassType, str] = {
  PLRClassType.LH_BACKEND: "pylabrobot.liquid_handling.LiquidHandler",
  PLRClassType.PR_BACKEND: "pylabrobot.plate_reading.PlateReader",
  PLRClassType.HS_BACKEND: "pylabrobot.heating_shaking.HeaterShaker",
  PLRClassType.SHAKER_BACKEND: "pylabrobot.shaking.Shaker",
  PLRClassType.TEMP_BACKEND: "pylabrobot.temperature_controlling.TemperatureController",
  PLRClassType.CENTRIFUGE_BACKEND: "pylabrobot.centrifuging.Centrifuge",
  PLRClassType.THERMOCYCLER_BACKEND: "pylabrobot.thermocycling.Thermocycler",
  PLRClassType.PUMP_BACKEND: "pylabrobot.pumping.Pump",
  PLRClassType.PUMP_ARRAY_BACKEND: "pylabrobot.pumping.PumpArray",
  PLRClassType.FAN_BACKEND: "pylabrobot.fans.Fan",
  PLRClassType.SEALER_BACKEND: "pylabrobot.plate_sealing.Sealer",
  PLRClassType.PEELER_BACKEND: "pylabrobot.plate_peeling.Peeler",
  PLRClassType.POWDER_DISPENSER_BACKEND: "pylabrobot.powder_dispensing.PowderDispenser",
  PLRClassType.INCUBATOR_BACKEND: "pylabrobot.incubating.Incubator",
  PLRClassType.SCARA_BACKEND: "pylabrobot.scara.SCARA",
  PLRClassType.IMAGER_BACKEND: "pylabrobot.plate_reading.Imager",
}

# =============================================================================
# Computation Graph Models
# =============================================================================


class GraphNodeType(str, Enum):
  """Classification of computation graph nodes."""

  STATIC = "static"  # Can be pre-computed/evaluated at analysis time
  DYNAMIC = "dynamic"  # Requires runtime data
  CONDITIONAL = "conditional"  # Branches based on runtime value
  FOREACH = "foreach"  # Loop over collection


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
