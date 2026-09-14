# --- PORT PROVENANCE (verbatim copy of praxis/backend/core/simulation/method_contracts.py:1-546) ----------------------------------------
"""PLR method contracts for state simulation.

This module defines contracts for PyLabRobot methods, capturing:
- Preconditions: State that must be true before execution
- Effects: State changes after execution

These contracts enable the simulation to validate protocols and infer requirements
without executing actual hardware operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EffectType(str, Enum):
  """Types of state effects from method execution."""

  LOADS_TIPS = "loads_tips"
  DROPS_TIPS = "drops_tips"
  ASPIRATES = "aspirates"
  DISPENSES = "dispenses"
  TRANSFERS = "transfers"
  MOVES_RESOURCE = "moves_resource"
  SETS_TEMPERATURE = "sets_temperature"
  STARTS_SHAKING = "starts_shaking"
  STOPS_SHAKING = "stops_shaking"


@dataclass(frozen=True)
class MethodContract:
  """Contract for a PLR method defining preconditions and effects.

  This captures the semantic meaning of a method for state simulation:
  - What state must be true before the method can execute (preconditions)
  - What state changes after execution (effects)

  Example:
      The `aspirate` method requires tips to be loaded and the source
      resource to have liquid. After execution, liquid is removed from
      the source.

  """

  method_name: str
  """Name of the method (e.g., 'aspirate', 'transfer')"""

  receiver_type: str
  """Type of the receiver object (e.g., 'liquid_handler', 'plate_reader')"""

  # === Preconditions ===

  requires_tips: bool = False
  """Whether tips must be loaded before this operation"""

  requires_tips_count: int | None = None
  """Specific tip count required (e.g., 96 for transfer_96)"""

  requires_on_deck: tuple[str, ...] = ()
  """Argument names that must refer to resources on deck"""

  requires_liquid_in: str | None = None
  """Argument name whose resource must contain liquid"""

  requires_capacity_in: str | None = None
  """Argument name whose resource must have remaining capacity"""

  requires_volume_min: float | None = None
  """Minimum volume required in source (µL)"""

  requires_machine_ready: bool = True
  """Whether machine must be initialized/ready"""

  requires_temperature_range: tuple[float, float] | None = None
  """Required temperature range (min, max) in Celsius"""

  # === Effects ===

  loads_tips: bool = False
  """Whether this operation loads tips"""

  loads_tips_count: int | None = None
  """Number of tips loaded (None = determined by argument)"""

  drops_tips: bool = False
  """Whether this operation drops/returns tips"""

  aspirates_from: str | None = None
  """Argument name from which liquid is aspirated"""

  aspirate_volume_arg: str | None = None
  """Argument name specifying aspiration volume"""

  dispenses_to: str | None = None
  """Argument name to which liquid is dispensed"""

  dispense_volume_arg: str | None = None
  """Argument name specifying dispense volume"""

  transfers_from_to: tuple[str, str] | None = None
  """(source_arg, dest_arg) for transfer operations"""

  moves_resource: tuple[str, str] | None = None
  """(resource_arg, destination_arg) for move operations"""

  # === Metadata ===

  is_async: bool = True
  """Whether this is an async method"""

  description: str = ""
  """Human-readable description of what this method does"""


# =============================================================================
# LiquidHandler Method Contracts
# =============================================================================

_LIQUID_HANDLER_CONTRACTS: list[MethodContract] = [
  # --- Tip Operations ---
  MethodContract(
    method_name="pick_up_tips",
    receiver_type="liquid_handler",
    requires_on_deck=("tips",),
    loads_tips=True,
    description="Pick up tips from a tip rack",
  ),
  MethodContract(
    method_name="pick_up_tips96",
    receiver_type="liquid_handler",
    requires_on_deck=("tip_rack",),
    loads_tips=True,
    loads_tips_count=96,
    description="Pick up 96 tips simultaneously using CoRe 96 head",
  ),
  MethodContract(
    method_name="drop_tips",
    receiver_type="liquid_handler",
    requires_tips=True,
    requires_on_deck=("tips",),
    drops_tips=True,
    description="Drop tips back to tip rack or waste",
  ),
  MethodContract(
    method_name="drop_tips96",
    receiver_type="liquid_handler",
    requires_tips=True,
    requires_tips_count=96,
    requires_on_deck=("tip_rack",),
    drops_tips=True,
    description="Drop 96 tips simultaneously",
  ),
  MethodContract(
    method_name="return_tips",
    receiver_type="liquid_handler",
    requires_tips=True,
    drops_tips=True,
    description="Return tips to their original positions",
  ),
  MethodContract(
    method_name="discard_tips",
    receiver_type="liquid_handler",
    requires_tips=True,
    drops_tips=True,
    description="Discard tips to waste",
  ),
  # --- Liquid Operations ---
  MethodContract(
    method_name="aspirate",
    receiver_type="liquid_handler",
    requires_tips=True,
    requires_on_deck=("resource",),
    requires_liquid_in="resource",
    aspirates_from="resource",
    aspirate_volume_arg="vol",
    description="Aspirate liquid from wells",
  ),
  MethodContract(
    method_name="dispense",
    receiver_type="liquid_handler",
    requires_tips=True,
    requires_on_deck=("resource",),
    requires_capacity_in="resource",
    dispenses_to="resource",
    dispense_volume_arg="vol",
    description="Dispense liquid to wells",
  ),
  MethodContract(
    method_name="transfer",
    receiver_type="liquid_handler",
    requires_tips=True,
    requires_on_deck=("source", "target"),
    requires_liquid_in="source",
    requires_capacity_in="target",
    transfers_from_to=("source", "target"),
    description="Transfer liquid from source to target",
  ),
  MethodContract(
    method_name="stamp",
    receiver_type="liquid_handler",
    requires_tips=True,
    requires_on_deck=("source", "target"),
    requires_liquid_in="source",
    requires_capacity_in="target",
    transfers_from_to=("source", "target"),
    description="Stamp transfer (parallel multi-channel)",
  ),
  MethodContract(
    method_name="aspirate96",
    receiver_type="liquid_handler",
    requires_tips=True,
    requires_tips_count=96,
    requires_on_deck=("resource",),
    requires_liquid_in="resource",
    aspirates_from="resource",
    aspirate_volume_arg="volume",
    description="Aspirate with 96-channel head",
  ),
  MethodContract(
    method_name="dispense96",
    receiver_type="liquid_handler",
    requires_tips=True,
    requires_tips_count=96,
    requires_on_deck=("resource",),
    requires_capacity_in="resource",
    dispenses_to="resource",
    dispense_volume_arg="volume",
    description="Dispense with 96-channel head",
  ),
  MethodContract(
    method_name="transfer_96",
    receiver_type="liquid_handler",
    requires_tips=True,
    requires_tips_count=96,
    requires_on_deck=("source", "target"),
    requires_liquid_in="source",
    requires_capacity_in="target",
    transfers_from_to=("source", "target"),
    description="96-channel transfer from source to target plate",
  ),
  # --- Mixing ---
  MethodContract(
    method_name="mix",
    receiver_type="liquid_handler",
    requires_tips=True,
    requires_on_deck=("resource",),
    requires_liquid_in="resource",
    description="Mix liquid by repeated aspiration/dispense cycles",
  ),
  # --- Auxiliary ---
  MethodContract(
    method_name="blow_out",
    receiver_type="liquid_handler",
    requires_tips=True,
    description="Blow out remaining liquid from tips",
  ),
  MethodContract(
    method_name="touch_tip",
    receiver_type="liquid_handler",
    requires_tips=True,
    requires_on_deck=("resource",),
    description="Touch tip to well wall to remove droplets",
  ),
  # --- Transport (iSWAP) ---
  MethodContract(
    method_name="move_plate",
    receiver_type="liquid_handler",
    requires_on_deck=("plate",),
    moves_resource=("plate", "target"),
    description="Move plate using integrated plate handler (iSWAP)",
  ),
  MethodContract(
    method_name="move_lid",
    receiver_type="liquid_handler",
    requires_on_deck=("lid",),
    moves_resource=("lid", "target"),
    description="Move plate lid",
  ),
]

# =============================================================================
# PlateReader Method Contracts
# =============================================================================

_PLATE_READER_CONTRACTS: list[MethodContract] = [
  MethodContract(
    method_name="read_absorbance",
    receiver_type="plate_reader",
    requires_on_deck=("plate",),
    description="Read absorbance at specified wavelength",
  ),
  MethodContract(
    method_name="read_fluorescence",
    receiver_type="plate_reader",
    requires_on_deck=("plate",),
    description="Read fluorescence with excitation/emission wavelengths",
  ),
  MethodContract(
    method_name="read_luminescence",
    receiver_type="plate_reader",
    requires_on_deck=("plate",),
    description="Read luminescence",
  ),
]

# =============================================================================
# HeaterShaker Method Contracts
# =============================================================================

_HEATER_SHAKER_CONTRACTS: list[MethodContract] = [
  MethodContract(
    method_name="set_temperature",
    receiver_type="heater_shaker",
    description="Set target temperature",
  ),
  MethodContract(
    method_name="wait_for_temperature",
    receiver_type="heater_shaker",
    description="Wait until temperature is reached",
  ),
  MethodContract(
    method_name="shake",
    receiver_type="heater_shaker",
    requires_on_deck=("plate",),
    description="Start shaking at specified speed",
  ),
  MethodContract(
    method_name="stop_shaking",
    receiver_type="heater_shaker",
    description="Stop shaking",
  ),
  MethodContract(
    method_name="open_lid",
    receiver_type="heater_shaker",
    description="Open the heater-shaker lid",
  ),
  MethodContract(
    method_name="close_lid",
    receiver_type="heater_shaker",
    description="Close the heater-shaker lid",
  ),
]

# =============================================================================
# Shaker Method Contracts (no heating)
# =============================================================================

_SHAKER_CONTRACTS: list[MethodContract] = [
  MethodContract(
    method_name="shake",
    receiver_type="shaker",
    requires_on_deck=("plate",),
    description="Start shaking at specified speed",
  ),
  MethodContract(
    method_name="stop_shaking",
    receiver_type="shaker",
    description="Stop shaking",
  ),
]

# =============================================================================
# Temperature Controller Contracts
# =============================================================================

_TEMPERATURE_CONTROLLER_CONTRACTS: list[MethodContract] = [
  MethodContract(
    method_name="set_temperature",
    receiver_type="temperature_controller",
    description="Set target temperature",
  ),
  MethodContract(
    method_name="wait_for_temperature",
    receiver_type="temperature_controller",
    description="Wait until temperature is reached",
  ),
  MethodContract(
    method_name="deactivate",
    receiver_type="temperature_controller",
    description="Turn off temperature control",
  ),
]

# =============================================================================
# Centrifuge Contracts
# =============================================================================

_CENTRIFUGE_CONTRACTS: list[MethodContract] = [
  MethodContract(
    method_name="spin",
    receiver_type="centrifuge",
    requires_on_deck=("plate",),
    description="Spin at specified g-force/RPM for duration",
  ),
  MethodContract(
    method_name="open_lid",
    receiver_type="centrifuge",
    description="Open centrifuge lid",
  ),
  MethodContract(
    method_name="close_lid",
    receiver_type="centrifuge",
    description="Close centrifuge lid",
  ),
]

# =============================================================================
# Thermocycler Contracts
# =============================================================================

_THERMOCYCLER_CONTRACTS: list[MethodContract] = [
  MethodContract(
    method_name="set_block_temperature",
    receiver_type="thermocycler",
    description="Set PCR block temperature",
  ),
  MethodContract(
    method_name="set_lid_temperature",
    receiver_type="thermocycler",
    description="Set lid temperature",
  ),
  MethodContract(
    method_name="run_profile",
    receiver_type="thermocycler",
    requires_on_deck=("plate",),
    description="Run a temperature cycling profile",
  ),
  MethodContract(
    method_name="open_lid",
    receiver_type="thermocycler",
    description="Open thermocycler lid",
  ),
  MethodContract(
    method_name="close_lid",
    receiver_type="thermocycler",
    description="Close thermocycler lid",
  ),
]

# =============================================================================
# Pump Contracts
# =============================================================================

_PUMP_CONTRACTS: list[MethodContract] = [
  MethodContract(
    method_name="run_for_duration",
    receiver_type="pump",
    description="Run pump for specified duration",
  ),
  MethodContract(
    method_name="run_for_volume",
    receiver_type="pump",
    description="Run pump until specified volume dispensed",
  ),
  MethodContract(
    method_name="halt",
    receiver_type="pump",
    description="Stop pump",
  ),
]

# =============================================================================
# Sealer/Peeler Contracts
# =============================================================================

_SEALER_CONTRACTS: list[MethodContract] = [
  MethodContract(
    method_name="seal",
    receiver_type="sealer",
    requires_on_deck=("plate",),
    description="Seal a plate",
  ),
]

_PEELER_CONTRACTS: list[MethodContract] = [
  MethodContract(
    method_name="peel",
    receiver_type="peeler",
    requires_on_deck=("plate",),
    description="Peel seal from plate",
  ),
]

# =============================================================================
# Contract Registry
# =============================================================================


def _build_contract_registry() -> dict[tuple[str, str], MethodContract]:
  """Build the method contract registry.

  Returns:
      Mapping of (receiver_type, method_name) -> MethodContract

  """
  all_contracts = (
    _LIQUID_HANDLER_CONTRACTS
    + _PLATE_READER_CONTRACTS
    + _HEATER_SHAKER_CONTRACTS
    + _SHAKER_CONTRACTS
    + _TEMPERATURE_CONTROLLER_CONTRACTS
    + _CENTRIFUGE_CONTRACTS
    + _THERMOCYCLER_CONTRACTS
    + _PUMP_CONTRACTS
    + _SEALER_CONTRACTS
    + _PEELER_CONTRACTS
  )

  registry: dict[tuple[str, str], MethodContract] = {}
  for contract in all_contracts:
    key = (contract.receiver_type, contract.method_name)
    registry[key] = contract

  return registry


METHOD_CONTRACTS: dict[tuple[str, str], MethodContract] = _build_contract_registry()
"""Registry of all method contracts, keyed by (receiver_type, method_name)."""


def get_contract(receiver_type: str, method_name: str) -> MethodContract | None:
  """Look up a method contract.

  Args:
      receiver_type: Type of the receiver (e.g., 'liquid_handler').
      method_name: Name of the method (e.g., 'aspirate').

  Returns:
      The MethodContract if found, None otherwise.

  """
  return METHOD_CONTRACTS.get((receiver_type, method_name))


def get_contracts_for_type(receiver_type: str) -> list[MethodContract]:
  """Get all contracts for a receiver type.

  Args:
      receiver_type: Type of the receiver (e.g., 'liquid_handler').

  Returns:
      List of all contracts for that receiver type.

  """
  return [c for (rt, _), c in METHOD_CONTRACTS.items() if rt == receiver_type]
