# --- PORT PROVENANCE (verbatim copy of praxis/backend/core/simulation/state_models.py:1-585) ----------------------------------------
"""State models for hierarchical protocol simulation.

This module provides state representations at three precision levels:
1. Boolean: Fast, coarse-grained (has_liquid: bool)
2. Symbolic: Medium, constraint-based (volume: "v1", constraints: ["v1 > 0"])
3. Exact: Precise, numeric (volume: 150.0)

The hierarchical approach enables efficient simulation by starting with
fast boolean checks and only promoting to higher precision when needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StateLevel(str, Enum):
  """Precision level for simulation state."""

  BOOLEAN = "boolean"
  SYMBOLIC = "symbolic"
  EXACT = "exact"


class ViolationType(str, Enum):
  """Types of state violations that can occur during simulation."""

  TIPS_NOT_LOADED = "tips_not_loaded"
  TIPS_ALREADY_LOADED = "tips_already_loaded"
  INSUFFICIENT_TIPS = "insufficient_tips"
  NO_LIQUID = "no_liquid"
  INSUFFICIENT_VOLUME = "insufficient_volume"
  NO_CAPACITY = "no_capacity"
  CAPACITY_EXCEEDED = "capacity_exceeded"
  RESOURCE_NOT_ON_DECK = "resource_not_on_deck"
  MACHINE_NOT_READY = "machine_not_ready"
  TEMPERATURE_OUT_OF_RANGE = "temperature_out_of_range"
  CONSTRAINT_UNSATISFIABLE = "constraint_unsatisfiable"


@dataclass
class StateViolation:
  """A violation of state preconditions during simulation.

  Captures what went wrong, where, and suggests how to fix it.
  """

  violation_type: ViolationType
  """Type of the violation"""

  operation_id: str
  """ID of the operation that caused the violation"""

  method_name: str
  """Name of the method being called"""

  resource_name: str | None = None
  """Name of the resource involved (if applicable)"""

  message: str = ""
  """Human-readable description of the violation"""

  suggested_fix: str | None = None
  """Suggested action to resolve the violation"""

  state_level: StateLevel = StateLevel.BOOLEAN
  """Level at which this violation was detected"""

  details: dict[str, Any] = field(default_factory=dict)
  """Additional violation details (e.g., required volume, available volume)"""

  def __str__(self) -> str:
    base = f"[{self.violation_type.value}] {self.message}"
    if self.suggested_fix:
      base += f" Fix: {self.suggested_fix}"
    return base


# =============================================================================
# Boolean State (Level 1 - Fast)
# =============================================================================


@dataclass
class BooleanLiquidState:
  """Fast boolean state for liquid tracking.

  Tracks only whether liquid is present, not quantities.
  Sufficient for detecting obvious errors like aspirating from empty wells.
  """

  has_liquid: dict[str, bool] = field(default_factory=dict)
  """Resource/well name -> whether it contains liquid"""

  has_capacity: dict[str, bool] = field(default_factory=dict)
  """Resource/well name -> whether it has remaining capacity"""

  def set_has_liquid(self, resource: str, value: bool) -> None:
    """Set whether a resource has liquid."""
    self.has_liquid[resource] = value
    # If it has liquid, it may not have full capacity
    if value:
      self.has_capacity.setdefault(resource, True)

  def set_has_capacity(self, resource: str, value: bool) -> None:
    """Set whether a resource has capacity."""
    self.has_capacity[resource] = value

  def check_has_liquid(self, resource: str) -> bool:
    """Check if resource has liquid. Unknown resources assumed to have liquid."""
    return self.has_liquid.get(resource, True)

  def check_has_capacity(self, resource: str) -> bool:
    """Check if resource has capacity. Unknown resources assumed to have capacity."""
    return self.has_capacity.get(resource, True)

  def aspirate(self, resource: str) -> None:
    """Record aspiration from a resource."""
    # After aspiration, still has liquid (we don't track depletion at boolean level)
    # Capacity increases (we made room)
    self.has_capacity[resource] = True

  def dispense(self, resource: str) -> None:
    """Record dispense to a resource."""
    # After dispense, definitely has liquid
    self.has_liquid[resource] = True
    # Still has capacity at boolean level (we don't track filling)

  def transfer(self, source: str, dest: str) -> None:
    """Record transfer from source to dest."""
    self.aspirate(source)
    self.dispense(dest)

  def copy(self) -> BooleanLiquidState:
    """Create a copy of this state."""
    return BooleanLiquidState(
      has_liquid=self.has_liquid.copy(),
      has_capacity=self.has_capacity.copy(),
    )


# =============================================================================
# Symbolic State (Level 2 - Medium)
# =============================================================================


@dataclass
class SymbolicVolume:
  """A symbolic volume with constraints.

  Represents a volume as a symbol (e.g., "v1") with constraints
  that must be satisfied (e.g., "v1 > 0", "v1 <= 200").
  """

  symbol: str
  """Symbolic name for this volume"""

  constraints: list[str] = field(default_factory=list)
  """Constraints on this symbol"""

  derived_from: str | None = None
  """Expression this was derived from (e.g., 'v1 - 50')"""


@dataclass
class SymbolicLiquidState:
  """Medium-precision symbolic state for liquid tracking.

  Uses symbolic variables with constraints to track volumes.
  Enables detection of issues like "aspiration volume exceeds available".
  """

  volumes: dict[str, SymbolicVolume] = field(default_factory=dict)
  """Resource/well name -> symbolic volume"""

  capacities: dict[str, SymbolicVolume] = field(default_factory=dict)
  """Resource/well name -> symbolic remaining capacity"""

  constraints: list[str] = field(default_factory=list)
  """Global constraints across all symbols"""

  _symbol_counter: int = field(default=0, init=False)
  """Counter for generating unique symbols"""

  def _next_symbol(self, prefix: str = "v") -> str:
    """Generate a unique symbol."""
    self._symbol_counter += 1
    return f"{prefix}{self._symbol_counter}"

  def get_or_create_volume(self, resource: str, max_capacity: float = 200.0) -> SymbolicVolume:
    """Get existing volume or create new symbolic volume."""
    if resource not in self.volumes:
      sym = self._next_symbol()
      self.volumes[resource] = SymbolicVolume(
        symbol=sym,
        constraints=[f"{sym} >= 0", f"{sym} <= {max_capacity}"],
      )
    return self.volumes[resource]

  def get_or_create_capacity(self, resource: str, max_capacity: float = 200.0) -> SymbolicVolume:
    """Get existing capacity or create new symbolic capacity."""
    if resource not in self.capacities:
      sym = self._next_symbol("cap")
      self.capacities[resource] = SymbolicVolume(
        symbol=sym,
        constraints=[f"{sym} >= 0", f"{sym} <= {max_capacity}"],
      )
    return self.capacities[resource]

  def aspirate(self, resource: str, volume_symbol: str) -> None:
    """Record aspiration with symbolic volume."""
    vol = self.get_or_create_volume(resource)
    # Add constraint: current volume >= aspiration volume
    self.constraints.append(f"{vol.symbol} >= {volume_symbol}")
    # Update volume symbol to represent remaining
    new_sym = self._next_symbol()
    self.constraints.append(f"{new_sym} = {vol.symbol} - {volume_symbol}")
    self.constraints.append(f"{new_sym} >= 0")
    self.volumes[resource] = SymbolicVolume(
      symbol=new_sym,
      constraints=[f"{new_sym} >= 0"],
      derived_from=f"{vol.symbol} - {volume_symbol}",
    )

  def dispense(self, resource: str, volume_symbol: str, max_capacity: float = 200.0) -> None:
    """Record dispense with symbolic volume."""
    vol = self.get_or_create_volume(resource)
    cap = self.get_or_create_capacity(resource, max_capacity)
    # Add constraint: capacity >= dispense volume
    self.constraints.append(f"{cap.symbol} >= {volume_symbol}")
    # Update volume and capacity
    new_vol_sym = self._next_symbol()
    new_cap_sym = self._next_symbol("cap")
    self.constraints.append(f"{new_vol_sym} = {vol.symbol} + {volume_symbol}")
    self.constraints.append(f"{new_cap_sym} = {cap.symbol} - {volume_symbol}")
    self.volumes[resource] = SymbolicVolume(
      symbol=new_vol_sym,
      derived_from=f"{vol.symbol} + {volume_symbol}",
    )
    self.capacities[resource] = SymbolicVolume(
      symbol=new_cap_sym,
      derived_from=f"{cap.symbol} - {volume_symbol}",
    )

  def check_constraints_satisfiable(self) -> tuple[bool, list[str]]:
    """Check if all constraints can be satisfied.

    Returns:
        (is_satisfiable, list of conflicting constraints if not)

    Note: This is a simplified check. A full implementation would use
    an SMT solver like Z3.

    """
    # Simplified: just return True for now
    # Real implementation would use constraint solving
    return True, []

  def copy(self) -> SymbolicLiquidState:
    """Create a copy of this state."""
    new_state = SymbolicLiquidState(
      volumes={k: SymbolicVolume(v.symbol, v.constraints.copy(), v.derived_from) for k, v in self.volumes.items()},
      capacities={k: SymbolicVolume(v.symbol, v.constraints.copy(), v.derived_from) for k, v in self.capacities.items()},
      constraints=self.constraints.copy(),
    )
    new_state._symbol_counter = self._symbol_counter
    return new_state


# =============================================================================
# Exact State (Level 3 - Precise)
# =============================================================================


@dataclass
class ExactLiquidState:
  """Precise numeric state for liquid tracking.

  Uses exact floating-point volumes for precise validation.
  Used for edge case detection after symbolic analysis identifies potential issues.
  """

  volumes: dict[str, float] = field(default_factory=dict)
  """Resource/well name -> exact volume in µL"""

  capacities: dict[str, float] = field(default_factory=dict)
  """Resource/well name -> remaining capacity in µL"""

  max_capacities: dict[str, float] = field(default_factory=dict)
  """Resource/well name -> maximum capacity in µL"""

  def get_volume(self, resource: str, default: float = 0.0) -> float:
    """Get volume for a resource."""
    return self.volumes.get(resource, default)

  def get_capacity(self, resource: str, default: float = 200.0) -> float:
    """Get remaining capacity for a resource."""
    return self.capacities.get(resource, default)

  def set_volume(self, resource: str, volume: float, max_capacity: float = 200.0) -> None:
    """Set volume for a resource."""
    self.volumes[resource] = volume
    self.max_capacities.setdefault(resource, max_capacity)
    self.capacities[resource] = max_capacity - volume

  def aspirate(self, resource: str, volume: float) -> bool:
    """Aspirate volume from resource. Returns True if successful."""
    current = self.get_volume(resource)
    if current < volume:
      return False
    self.volumes[resource] = current - volume
    max_cap = self.max_capacities.get(resource, 200.0)
    self.capacities[resource] = max_cap - (current - volume)
    return True

  def dispense(self, resource: str, volume: float) -> bool:
    """Dispense volume to resource. Returns True if successful."""
    current = self.get_volume(resource)
    capacity = self.get_capacity(resource)
    if capacity < volume:
      return False
    self.volumes[resource] = current + volume
    self.capacities[resource] = capacity - volume
    return True

  def transfer(self, source: str, dest: str, volume: float) -> bool:
    """Transfer volume from source to dest. Returns True if successful."""
    if not self.aspirate(source, volume):
      return False
    if not self.dispense(dest, volume):
      # Rollback aspiration
      self.volumes[source] = self.get_volume(source) + volume
      return False
    return True

  def copy(self) -> ExactLiquidState:
    """Create a copy of this state."""
    return ExactLiquidState(
      volumes=self.volumes.copy(),
      capacities=self.capacities.copy(),
      max_capacities=self.max_capacities.copy(),
    )


# =============================================================================
# Unified Simulation State
# =============================================================================


@dataclass
class TipState:
  """State of tips on a machine."""

  tips_loaded: bool = False
  """Whether tips are currently loaded"""

  tips_count: int = 0
  """Number of tips loaded (0 if none)"""

  tip_source: str | None = None
  """Resource from which tips were picked up"""

  def load_tips(self, count: int = 1, source: str | None = None) -> None:
    """Load tips."""
    self.tips_loaded = True
    self.tips_count = count
    self.tip_source = source

  def drop_tips(self) -> None:
    """Drop tips."""
    self.tips_loaded = False
    self.tips_count = 0
    self.tip_source = None

  def copy(self) -> TipState:
    """Create a copy of this state."""
    return TipState(
      tips_loaded=self.tips_loaded,
      tips_count=self.tips_count,
      tip_source=self.tip_source,
    )


@dataclass
class DeckState:
  """State of the deck (resource placement)."""

  on_deck: dict[str, bool] = field(default_factory=dict)
  """Resource name -> whether it's on deck"""

  positions: dict[str, str] = field(default_factory=dict)
  """Resource name -> position/slot on deck"""

  def place_on_deck(self, resource: str, position: str | None = None) -> None:
    """Place a resource on deck."""
    self.on_deck[resource] = True
    if position:
      self.positions[resource] = position

  def remove_from_deck(self, resource: str) -> None:
    """Remove a resource from deck."""
    self.on_deck[resource] = False
    self.positions.pop(resource, None)

  def is_on_deck(self, resource: str) -> bool:
    """Check if resource is on deck. Unknown resources assumed to be on deck."""
    return self.on_deck.get(resource, True)

  def copy(self) -> DeckState:
    """Create a copy of this state."""
    return DeckState(
      on_deck=self.on_deck.copy(),
      positions=self.positions.copy(),
    )


@dataclass
class MachineState:
  """State of a machine."""

  is_ready: bool = True
  """Whether machine is initialized and ready"""

  temperature: float | None = None
  """Current temperature (if applicable)"""

  is_shaking: bool = False
  """Whether currently shaking (for shakers)"""

  def copy(self) -> MachineState:
    """Create a copy of this state."""
    return MachineState(
      is_ready=self.is_ready,
      temperature=self.temperature,
      is_shaking=self.is_shaking,
    )


LiquidStateType = BooleanLiquidState | SymbolicLiquidState | ExactLiquidState


@dataclass
class SimulationState:
  """Complete simulation state at a given point in execution.

  Combines tip state, deck state, machine state, and liquid state
  at the appropriate precision level.
  """

  level: StateLevel = StateLevel.BOOLEAN
  """Current precision level"""

  tip_state: TipState = field(default_factory=TipState)
  """Tip loading state"""

  deck_state: DeckState = field(default_factory=DeckState)
  """Resource placement state"""

  machine_states: dict[str, MachineState] = field(default_factory=dict)
  """Machine name -> machine state"""

  liquid_state: LiquidStateType = field(default_factory=BooleanLiquidState)
  """Liquid state at current precision level"""

  def get_machine_state(self, machine: str) -> MachineState:
    """Get state for a machine, creating if needed."""
    if machine not in self.machine_states:
      self.machine_states[machine] = MachineState()
    return self.machine_states[machine]

  def promote(self) -> SimulationState:
    """Promote to the next precision level.

    Returns a new SimulationState at the higher level.
    """
    if self.level == StateLevel.BOOLEAN:
      return self._promote_to_symbolic()
    if self.level == StateLevel.SYMBOLIC:
      return self._promote_to_exact()
    return self  # Already at highest level

  def _promote_to_symbolic(self) -> SimulationState:
    """Promote from boolean to symbolic state."""
    bool_state = self.liquid_state
    if not isinstance(bool_state, BooleanLiquidState):
      msg = "Expected BooleanLiquidState for promotion"
      raise ValueError(msg)

    sym_state = SymbolicLiquidState()

    # Convert boolean has_liquid to symbolic volumes
    for resource, has_liquid in bool_state.has_liquid.items():
      if has_liquid:
        sym = sym_state._next_symbol()
        sym_state.volumes[resource] = SymbolicVolume(
          symbol=sym,
          constraints=[f"{sym} > 0"],  # Has some liquid
        )
      else:
        sym_state.volumes[resource] = SymbolicVolume(
          symbol="0",
          constraints=[],
        )

    return SimulationState(
      level=StateLevel.SYMBOLIC,
      tip_state=self.tip_state.copy(),
      deck_state=self.deck_state.copy(),
      machine_states={k: v.copy() for k, v in self.machine_states.items()},
      liquid_state=sym_state,
    )

  def _promote_to_exact(self) -> SimulationState:
    """Promote from symbolic to exact state with default values."""
    return self.promote_to_exact_with_values({})

  def promote_to_exact_with_values(self, values: dict[str, float]) -> SimulationState:
    """Promote to exact state with specific volume values.

    Args:
        values: Mapping of resource -> initial volume

    """
    exact_state = ExactLiquidState()

    # Set provided values
    for resource, volume in values.items():
      exact_state.set_volume(resource, volume)

    # If we have symbolic state, use constraint info
    if isinstance(self.liquid_state, SymbolicLiquidState):
      for resource in self.liquid_state.volumes:
        if resource not in values:
          # Default to middle of range
          exact_state.set_volume(resource, 100.0)

    return SimulationState(
      level=StateLevel.EXACT,
      tip_state=self.tip_state.copy(),
      deck_state=self.deck_state.copy(),
      machine_states={k: v.copy() for k, v in self.machine_states.items()},
      liquid_state=exact_state,
    )

  def copy(self) -> SimulationState:
    """Create a copy of this state."""
    liquid_copy: LiquidStateType
    if isinstance(self.liquid_state, BooleanLiquidState | SymbolicLiquidState):
      liquid_copy = self.liquid_state.copy()
    else:
      liquid_copy = self.liquid_state.copy()

    return SimulationState(
      level=self.level,
      tip_state=self.tip_state.copy(),
      deck_state=self.deck_state.copy(),
      machine_states={k: v.copy() for k, v in self.machine_states.items()},
      liquid_state=liquid_copy,
    )

  @classmethod
  def default_boolean(cls) -> SimulationState:
    """Create a default boolean-level state."""
    return cls(
      level=StateLevel.BOOLEAN,
      liquid_state=BooleanLiquidState(),
    )

  @classmethod
  def default_symbolic(cls) -> SimulationState:
    """Create a default symbolic-level state."""
    return cls(
      level=StateLevel.SYMBOLIC,
      liquid_state=SymbolicLiquidState(),
    )

  @classmethod
  def default_exact(cls) -> SimulationState:
    """Create a default exact-level state."""
    return cls(
      level=StateLevel.EXACT,
      liquid_state=ExactLiquidState(),
    )
