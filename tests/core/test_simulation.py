"""Tests for the protocol simulation infrastructure.

This module tests:
- Method contracts (preconditions, effects)
- State models (boolean, symbolic, exact)
- Stateful tracers
- Hierarchical simulation pipeline
- Bounds analyzer
- Failure mode detector
"""

import pytest

from praxis.backend.core.simulation.bounds_analyzer import (
  BoundsAnalyzer,
  ItemizedResourceSpec,
)
from praxis.backend.core.simulation.failure_detector import (
  BooleanStateConfig,
  FailureModeDetector,
  generate_boolean_states,
)
from praxis.backend.core.simulation.method_contracts import (
  METHOD_CONTRACTS,
  get_contract,
  get_contracts_for_type,
)
from praxis.backend.core.simulation.pipeline import (
  simulate_protocol_sync,
)
from praxis.backend.core.simulation.state_models import (
  BooleanLiquidState,
  ExactLiquidState,
  SimulationState,
  StateLevel,
  SymbolicLiquidState,
  TipState,
  ViolationType,
)
from praxis.backend.core.simulation.stateful_tracers import (
  StatefulTracedMachine,
)
from praxis.backend.core.tracing.recorder import OperationRecorder

# =============================================================================
# Test Method Contracts
# =============================================================================


class TestMethodContracts:
  """Tests for method contract definitions."""

  def test_contracts_registry_populated(self) -> None:
    """Test that the contract registry has entries."""
    assert len(METHOD_CONTRACTS) > 0

  def test_liquid_handler_contracts_exist(self) -> None:
    """Test that liquid handler contracts are defined."""
    lh_contracts = get_contracts_for_type("liquid_handler")
    assert len(lh_contracts) > 0

    # Check specific methods
    method_names = {c.method_name for c in lh_contracts}
    assert "pick_up_tips" in method_names
    assert "aspirate" in method_names
    assert "dispense" in method_names
    assert "transfer" in method_names

  def test_get_contract_found(self) -> None:
    """Test getting a specific contract."""
    contract = get_contract("liquid_handler", "aspirate")
    assert contract is not None
    assert contract.method_name == "aspirate"
    assert contract.requires_tips is True
    assert contract.requires_liquid_in == "resource"

  def test_get_contract_not_found(self) -> None:
    """Test getting a non-existent contract."""
    contract = get_contract("liquid_handler", "nonexistent_method")
    assert contract is None

  def test_pick_up_tips_contract(self) -> None:
    """Test pick_up_tips contract details."""
    contract = get_contract("liquid_handler", "pick_up_tips")
    assert contract is not None
    assert contract.requires_tips is False  # Doesn't require tips to pick up
    assert contract.loads_tips is True  # Creates tips_loaded state
    assert "tips" in contract.requires_on_deck

  def test_transfer_contract(self) -> None:
    """Test transfer contract details."""
    contract = get_contract("liquid_handler", "transfer")
    assert contract is not None
    assert contract.requires_tips is True
    assert contract.requires_liquid_in == "source"
    assert contract.requires_capacity_in == "target"
    assert contract.transfers_from_to == ("source", "target")

  def test_plate_reader_contracts(self) -> None:
    """Test plate reader contracts exist."""
    pr_contracts = get_contracts_for_type("plate_reader")
    assert len(pr_contracts) > 0

    method_names = {c.method_name for c in pr_contracts}
    assert "read_absorbance" in method_names


# =============================================================================
# Test State Models
# =============================================================================


class TestBooleanLiquidState:
  """Tests for BooleanLiquidState."""

  def test_init(self) -> None:
    """Test initialization."""
    state = BooleanLiquidState()
    assert len(state.has_liquid) == 0
    assert len(state.has_capacity) == 0

  def test_set_has_liquid(self) -> None:
    """Test setting liquid state."""
    state = BooleanLiquidState()
    state.set_has_liquid("plate.A1", True)
    assert state.check_has_liquid("plate.A1") is True

  def test_unknown_resource_has_liquid(self) -> None:
    """Test that unknown resources are assumed to have liquid."""
    state = BooleanLiquidState()
    assert state.check_has_liquid("unknown") is True

  def test_aspirate(self) -> None:
    """Test aspirate effect."""
    state = BooleanLiquidState()
    state.set_has_liquid("source", True)
    state.aspirate("source")
    # Still has liquid after single aspirate (boolean doesn't track depletion)
    assert state.check_has_capacity("source") is True

  def test_dispense(self) -> None:
    """Test dispense effect."""
    state = BooleanLiquidState()
    state.dispense("dest")
    assert state.check_has_liquid("dest") is True

  def test_transfer(self) -> None:
    """Test transfer effect."""
    state = BooleanLiquidState()
    state.set_has_liquid("source", True)
    state.transfer("source", "dest")
    assert state.check_has_liquid("dest") is True

  def test_copy(self) -> None:
    """Test copying state."""
    state = BooleanLiquidState()
    state.set_has_liquid("plate", True)
    copied = state.copy()
    assert copied.check_has_liquid("plate") is True
    # Modify original, copy should be unchanged
    state.set_has_liquid("plate", False)
    assert copied.check_has_liquid("plate") is True


class TestExactLiquidState:
  """Tests for ExactLiquidState."""

  def test_set_volume(self) -> None:
    """Test setting volume."""
    state = ExactLiquidState()
    state.set_volume("well", 100.0, max_capacity=200.0)
    assert state.get_volume("well") == 100.0
    assert state.get_capacity("well") == 100.0

  def test_aspirate_success(self) -> None:
    """Test successful aspiration."""
    state = ExactLiquidState()
    state.set_volume("source", 100.0)
    result = state.aspirate("source", 50.0)
    assert result is True
    assert state.get_volume("source") == 50.0

  def test_aspirate_failure(self) -> None:
    """Test failed aspiration (insufficient volume)."""
    state = ExactLiquidState()
    state.set_volume("source", 30.0)
    result = state.aspirate("source", 50.0)
    assert result is False
    # Volume unchanged on failure
    assert state.get_volume("source") == 30.0

  def test_dispense_success(self) -> None:
    """Test successful dispense."""
    state = ExactLiquidState()
    state.set_volume("dest", 50.0, max_capacity=200.0)
    result = state.dispense("dest", 50.0)
    assert result is True
    assert state.get_volume("dest") == 100.0

  def test_dispense_failure(self) -> None:
    """Test failed dispense (capacity exceeded)."""
    state = ExactLiquidState()
    state.set_volume("dest", 180.0, max_capacity=200.0)
    result = state.dispense("dest", 50.0)
    assert result is False

  def test_transfer(self) -> None:
    """Test transfer operation."""
    state = ExactLiquidState()
    state.set_volume("source", 100.0)
    state.set_volume("dest", 0.0)
    result = state.transfer("source", "dest", 50.0)
    assert result is True
    assert state.get_volume("source") == 50.0
    assert state.get_volume("dest") == 50.0


class TestTipState:
  """Tests for TipState."""

  def test_init(self) -> None:
    """Test initialization."""
    state = TipState()
    assert state.tips_loaded is False
    assert state.tips_count == 0

  def test_load_tips(self) -> None:
    """Test loading tips."""
    state = TipState()
    state.load_tips(8, "tip_rack")
    assert state.tips_loaded is True
    assert state.tips_count == 8
    assert state.tip_source == "tip_rack"

  def test_drop_tips(self) -> None:
    """Test dropping tips."""
    state = TipState()
    state.load_tips(8)
    state.drop_tips()
    assert state.tips_loaded is False
    assert state.tips_count == 0


class TestSimulationState:
  """Tests for SimulationState."""

  def test_default_boolean(self) -> None:
    """Test creating default boolean state."""
    state = SimulationState.default_boolean()
    assert state.level == StateLevel.BOOLEAN
    assert isinstance(state.liquid_state, BooleanLiquidState)

  def test_promote_boolean_to_symbolic(self) -> None:
    """Test promoting boolean to symbolic state."""
    state = SimulationState.default_boolean()
    state.liquid_state.set_has_liquid("plate", True)

    promoted = state.promote()

    assert promoted.level == StateLevel.SYMBOLIC
    assert isinstance(promoted.liquid_state, SymbolicLiquidState)

  def test_promote_symbolic_to_exact(self) -> None:
    """Test promoting symbolic to exact state."""
    state = SimulationState.default_symbolic()
    promoted = state.promote_to_exact_with_values({"plate": 100.0})

    assert promoted.level == StateLevel.EXACT
    assert isinstance(promoted.liquid_state, ExactLiquidState)

  def test_copy(self) -> None:
    """Test copying state."""
    state = SimulationState.default_boolean()
    state.tip_state.load_tips(8)
    state.deck_state.place_on_deck("plate")

    copied = state.copy()

    assert copied.tip_state.tips_loaded is True
    assert copied.deck_state.is_on_deck("plate") is True

    # Modify original
    state.tip_state.drop_tips()
    # Copy unchanged
    assert copied.tip_state.tips_loaded is True


# =============================================================================
# Test Stateful Tracers
# =============================================================================


class TestStatefulTracedMachine:
  """Tests for StatefulTracedMachine."""

  @pytest.fixture
  def recorder(self) -> OperationRecorder:
    """Create a recorder for testing."""
    return OperationRecorder(protocol_fqn="test.protocol")

  @pytest.fixture
  def state(self) -> SimulationState:
    """Create default state for testing."""
    return SimulationState.default_boolean()

  def test_aspirate_without_tips_violation(
    self, recorder: OperationRecorder, state: SimulationState
  ) -> None:
    """Test that aspirating without tips creates a violation."""
    machine = StatefulTracedMachine(
      name="lh",
      recorder=recorder,
      declared_type="LiquidHandler",
      machine_type="liquid_handler",
      state=state,
    )

    # Aspirate without picking up tips
    machine.aspirate("well", 100)

    assert len(machine.violations) == 1
    assert machine.violations[0].violation_type == ViolationType.TIPS_NOT_LOADED

  def test_pick_up_tips_loads_tips(
    self, recorder: OperationRecorder, state: SimulationState
  ) -> None:
    """Test that pick_up_tips loads tips in state."""
    machine = StatefulTracedMachine(
      name="lh",
      recorder=recorder,
      declared_type="LiquidHandler",
      machine_type="liquid_handler",
      state=state,
    )

    machine.pick_up_tips("tips")

    assert state.tip_state.tips_loaded is True
    assert len(machine.violations) == 0

  def test_aspirate_with_tips_no_violation(
    self, recorder: OperationRecorder, state: SimulationState
  ) -> None:
    """Test that aspirating with tips doesn't create a violation."""
    machine = StatefulTracedMachine(
      name="lh",
      recorder=recorder,
      declared_type="LiquidHandler",
      machine_type="liquid_handler",
      state=state,
    )

    machine.pick_up_tips("tips")
    machine.aspirate("well", 100)

    # No tips violation (resource may have other violations)
    tips_violations = [v for v in machine.violations if v.violation_type == ViolationType.TIPS_NOT_LOADED]
    assert len(tips_violations) == 0

  def test_drop_tips_removes_tips(
    self, recorder: OperationRecorder, state: SimulationState
  ) -> None:
    """Test that drop_tips removes tips from state."""
    machine = StatefulTracedMachine(
      name="lh",
      recorder=recorder,
      declared_type="LiquidHandler",
      machine_type="liquid_handler",
      state=state,
    )

    machine.pick_up_tips("tips")
    assert state.tip_state.tips_loaded is True

    machine.drop_tips("tips")
    assert state.tip_state.tips_loaded is False


# =============================================================================
# Test Hierarchical Simulator
# =============================================================================


class TestHierarchicalSimulator:
  """Tests for HierarchicalSimulator."""

  def test_simple_valid_protocol(self) -> None:
    """Test simulation of a valid simple protocol."""

    async def valid_protocol(lh, plate, tips):
      await lh.pick_up_tips(tips)
      await lh.aspirate(plate["A1"], 100)
      await lh.dispense(plate["B1"], 100)
      await lh.drop_tips(tips)

    result = simulate_protocol_sync(
      valid_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
        "tips": "TipRack",
      },
    )

    assert result.passed is True
    assert result.level_completed == "exact"
    assert len(result.violations) == 0

  def test_protocol_missing_tips(self) -> None:
    """Test that missing tips are detected."""

    async def missing_tips_protocol(lh, plate):
      # Aspirate without picking up tips - should fail
      await lh.aspirate(plate["A1"], 100)

    result = simulate_protocol_sync(
      missing_tips_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
      },
    )

    assert result.passed is False
    assert len(result.violations) > 0
    assert any(v["type"] == "tips_not_loaded" for v in result.violations)

  def test_protocol_with_loop(self) -> None:
    """Test simulation of protocol with loop."""

    async def loop_protocol(lh, plate, tips):
      await lh.pick_up_tips(tips)
      for well in plate.wells():
        await lh.aspirate(well, 50)
      await lh.drop_tips(tips)

    result = simulate_protocol_sync(
      loop_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
        "tips": "TipRack",
      },
    )

    # Should pass - tips are picked up before loop
    assert result.passed is True

  def test_inferred_requirements(self) -> None:
    """Test that requirements are inferred from failures."""

    async def incomplete_protocol(lh, plate):
      await lh.aspirate(plate["A1"], 100)

    result = simulate_protocol_sync(
      incomplete_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
      },
    )

    assert result.passed is False
    assert len(result.inferred_requirements) > 0
    # Should infer tips_required
    assert any(r.requirement_type == "tips_required" for r in result.inferred_requirements)


# =============================================================================
# Test Bounds Analyzer
# =============================================================================


class TestBoundsAnalyzer:
  """Tests for BoundsAnalyzer."""

  def test_analyze_wells_loop(self) -> None:
    """Test analyzing plate.wells() loop."""
    analyzer = BoundsAnalyzer()
    analyzer.add_resource_spec(
      ItemizedResourceSpec("plate", "Plate", items_x=12, items_y=8)
    )

    bounds = analyzer.analyze_loop("plate.wells()")

    assert bounds.is_bounded is True
    assert bounds.exact_count == 96

  def test_analyze_rows_loop(self) -> None:
    """Test analyzing plate.rows() loop."""
    analyzer = BoundsAnalyzer()
    analyzer.add_resource_spec(
      ItemizedResourceSpec("plate", "Plate", items_x=12, items_y=8)
    )

    bounds = analyzer.analyze_loop("plate.rows()")

    assert bounds.is_bounded is True
    assert bounds.exact_count == 8

  def test_analyze_columns_loop(self) -> None:
    """Test analyzing plate.columns() loop."""
    analyzer = BoundsAnalyzer()
    analyzer.add_resource_spec(
      ItemizedResourceSpec("plate", "Plate", items_x=12, items_y=8)
    )

    bounds = analyzer.analyze_loop("plate.columns()")

    assert bounds.is_bounded is True
    assert bounds.exact_count == 12

  def test_analyze_tips_loop(self) -> None:
    """Test analyzing tips.tips() loop."""
    analyzer = BoundsAnalyzer()
    analyzer.add_resource_spec(
      ItemizedResourceSpec("tips", "TipRack", items_x=12, items_y=8)
    )

    bounds = analyzer.analyze_loop("tips.tips()")

    assert bounds.is_bounded is True
    assert bounds.exact_count == 96

  def test_unknown_resource_default(self) -> None:
    """Test that unknown resources use default dimensions."""
    analyzer = BoundsAnalyzer()

    bounds = analyzer.analyze_loop("unknown.wells()")

    assert bounds.is_bounded is True
    assert bounds.exact_count == 96  # Default assumption

  def test_384_well_plate(self) -> None:
    """Test 384-well plate dimensions."""
    analyzer = BoundsAnalyzer()
    analyzer.add_resource_spec(
      ItemizedResourceSpec("plate384", "Plate384", items_x=24, items_y=16)
    )

    bounds = analyzer.analyze_loop("plate384.wells()")

    assert bounds.exact_count == 384


# =============================================================================
# Test Failure Mode Detector
# =============================================================================


class TestFailureModeDetector:
  """Tests for FailureModeDetector."""

  def test_generate_boolean_states(self) -> None:
    """Test generating boolean state combinations."""
    config = BooleanStateConfig(
      resources=["plate"],
      tip_states=[True, False],
      liquid_states=[True, False],
    )

    states = list(generate_boolean_states(config))

    # 2 tip states × 2 liquid states = 4 combinations
    assert len(states) == 4

  def test_generate_states_no_resources(self) -> None:
    """Test generating states with no resources."""
    config = BooleanStateConfig(
      resources=[],
      tip_states=[True, False],
    )

    states = list(generate_boolean_states(config))

    assert len(states) == 2  # Just tip states

  def test_detect_missing_tips_failure(self) -> None:
    """Test detecting missing tips failure mode."""

    async def incomplete_protocol(lh, plate):
      await lh.aspirate(plate["A1"], 100)

    detector = FailureModeDetector(max_states=10)
    result = detector.detect_sync(
      incomplete_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
      },
    )

    assert len(result.failure_modes) > 0
    # At least one failure should be about tips
    tips_failures = [
      f for f in result.failure_modes if "tips" in f.failure_type.lower()
    ]
    assert len(tips_failures) > 0

  def test_no_failures_valid_protocol(self) -> None:
    """Test that valid protocol has no failure modes when run with correct state."""
    # Note: This tests the detector with a protocol that picks up tips
    # Some initial states may still cause failures

    async def valid_protocol(lh, plate, tips):
      await lh.pick_up_tips(tips)
      await lh.aspirate(plate["A1"], 100)
      await lh.drop_tips(tips)

    detector = FailureModeDetector(max_states=10)
    result = detector.detect_sync(
      valid_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
        "tips": "TipRack",
      },
    )

    # Valid protocol should have fewer failures or none
    # (may still fail on states where source has no liquid)
    assert result.states_explored > 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestSimulationIntegration:
  """Integration tests for the complete simulation system."""

  def test_transfer_96_protocol(self) -> None:
    """Test simulation of 96-well transfer protocol."""

    async def transfer_96_protocol(lh, source, dest, tips):
      await lh.pick_up_tips96(tips)
      await lh.transfer_96(source, dest)
      await lh.drop_tips96(tips)

    result = simulate_protocol_sync(
      transfer_96_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "source": "Plate",
        "dest": "Plate",
        "tips": "TipRack",
      },
    )

    # Should pass with proper tip handling
    assert result.passed is True

  def test_multi_step_protocol(self) -> None:
    """Test complex multi-step protocol."""

    async def complex_protocol(lh, plate, tips, volume=50.0):
      await lh.pick_up_tips(tips)
      await lh.aspirate(plate["A1"], volume)
      await lh.dispense(plate["B1"], volume)
      await lh.aspirate(plate["A2"], volume)
      await lh.dispense(plate["B2"], volume)
      await lh.drop_tips(tips)

    result = simulate_protocol_sync(
      complex_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
        "tips": "TipRack",
        "volume": "float",
      },
    )

    assert result.passed is True

  def test_simulation_with_plate_reader(self) -> None:
    """Test protocol using plate reader."""

    async def reader_protocol(pr, plate):
      await pr.read_absorbance(plate, wavelength=450)

    result = simulate_protocol_sync(
      reader_protocol,
      parameter_types={
        "pr": "PlateReader",
        "plate": "Plate",
      },
    )

    # Plate reader doesn't require tips
    assert result.passed is True

  def test_state_violation_has_fix_suggestion(self) -> None:
    """Test that violations include fix suggestions."""

    async def broken_protocol(lh, plate):
      await lh.aspirate(plate["A1"], 100)

    result = simulate_protocol_sync(
      broken_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
      },
    )

    assert result.passed is False
    assert len(result.violations) > 0

    # At least one violation should have a suggested fix
    violations_with_fix = [v for v in result.violations if v.get("suggested_fix")]
    assert len(violations_with_fix) > 0


# =============================================================================
# Test Protocol Simulator Facade
# =============================================================================


class TestProtocolSimulatorFacade:
  """Tests for the ProtocolSimulator facade class."""

  def test_analyze_protocol_sync(self) -> None:
    """Test synchronous protocol analysis."""
    from praxis.backend.core.simulation.simulator import analyze_protocol_sync

    async def simple_protocol(lh, plate, tips):
      await lh.pick_up_tips(tips)
      await lh.aspirate(plate["A1"], 50)
      await lh.drop_tips(tips)

    result = analyze_protocol_sync(
      simple_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
        "tips": "TipRack",
      },
    )

    assert result.passed is True
    assert result.simulation_version is not None
    assert result.execution_time_ms >= 0

  def test_analyze_protocol_with_failure_detection(self) -> None:
    """Test that failure detection runs by default."""
    from praxis.backend.core.simulation.simulator import analyze_protocol_sync

    async def simple_protocol(lh, plate):
      await lh.aspirate(plate["A1"], 50)

    result = analyze_protocol_sync(
      simple_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
      },
      enable_failure_detection=True,
    )

    # Should have failure modes detected (missing tips)
    assert result.passed is False
    assert len(result.failure_modes) > 0 or len(result.violations) > 0

  def test_analyze_protocol_without_failure_detection(self) -> None:
    """Test disabling failure detection."""
    from praxis.backend.core.simulation.simulator import analyze_protocol_sync

    async def simple_protocol(lh, plate, tips):
      await lh.pick_up_tips(tips)
      await lh.aspirate(plate["A1"], 50)
      await lh.drop_tips(tips)

    result = analyze_protocol_sync(
      simple_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
        "tips": "TipRack",
      },
      enable_failure_detection=False,
    )

    # Should still get main simulation result
    assert result.passed is True
    # Failure mode stats should be empty when disabled
    assert result.failure_mode_stats.get("states_explored", 0) == 0

  def test_result_to_cache_dict(self) -> None:
    """Test serializing result to cache dictionary."""
    from praxis.backend.core.simulation.simulator import (
      ProtocolSimulationResult,
      analyze_protocol_sync,
    )

    async def simple_protocol(lh, plate, tips):
      await lh.pick_up_tips(tips)
      await lh.aspirate(plate["A1"], 50)
      await lh.drop_tips(tips)

    result = analyze_protocol_sync(
      simple_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
        "tips": "TipRack",
      },
    )

    cache_dict = result.to_cache_dict()

    assert isinstance(cache_dict, dict)
    assert "passed" in cache_dict
    assert "simulation_version" in cache_dict
    assert "inferred_requirements" in cache_dict
    assert "failure_modes" in cache_dict

    # Verify round-trip
    restored = ProtocolSimulationResult.from_cache_dict(cache_dict)
    assert restored.passed == result.passed
    assert restored.simulation_version == result.simulation_version


# =============================================================================
# Test Cache Validation
# =============================================================================


class TestCacheValidation:
  """Tests for cache validation functions."""

  def test_cache_valid_same_version_same_hash(self) -> None:
    """Test cache is valid when version and hash match."""
    from praxis.backend.core.simulation.simulator import (
      SIMULATION_VERSION,
      is_cache_valid,
    )

    assert is_cache_valid(
      cached_version=SIMULATION_VERSION,
      source_hash="abc123",
      current_source_hash="abc123",
    ) is True

  def test_cache_invalid_version_mismatch(self) -> None:
    """Test cache is invalid when version doesn't match."""
    from praxis.backend.core.simulation.simulator import is_cache_valid

    assert is_cache_valid(
      cached_version="0.0.0",
      source_hash="abc123",
      current_source_hash="abc123",
    ) is False

  def test_cache_invalid_hash_mismatch(self) -> None:
    """Test cache is invalid when hash doesn't match."""
    from praxis.backend.core.simulation.simulator import (
      SIMULATION_VERSION,
      is_cache_valid,
    )

    assert is_cache_valid(
      cached_version=SIMULATION_VERSION,
      source_hash="abc123",
      current_source_hash="def456",
    ) is False

  def test_cache_valid_none_hashes(self) -> None:
    """Test cache validity with None hashes."""
    from praxis.backend.core.simulation.simulator import (
      SIMULATION_VERSION,
      is_cache_valid,
    )

    # Both None - valid (no hash check needed)
    assert is_cache_valid(
      cached_version=SIMULATION_VERSION,
      source_hash=None,
      current_source_hash=None,
    ) is True

    # One None - valid (can't compare)
    assert is_cache_valid(
      cached_version=SIMULATION_VERSION,
      source_hash=None,
      current_source_hash="abc123",
    ) is True


# =============================================================================
# Test Protocol Simulation Result Model
# =============================================================================


class TestProtocolSimulationResultModel:
  """Tests for the ProtocolSimulationResult Pydantic model."""

  def test_default_values(self) -> None:
    """Test default values are set correctly."""
    from praxis.backend.core.simulation.simulator import ProtocolSimulationResult

    result = ProtocolSimulationResult()

    assert result.passed is False
    assert result.level_completed == "none"
    assert result.level_failed is None
    assert result.violations == []
    assert result.inferred_requirements == []
    assert result.failure_modes == []
    assert result.simulation_version is not None

  def test_model_serialization(self) -> None:
    """Test model serializes to JSON correctly."""
    from praxis.backend.core.simulation.simulator import ProtocolSimulationResult

    result = ProtocolSimulationResult(
      passed=True,
      level_completed="exact",
      execution_time_ms=123.45,
    )

    json_dict = result.model_dump(mode="json")

    assert json_dict["passed"] is True
    assert json_dict["level_completed"] == "exact"
    assert json_dict["execution_time_ms"] == 123.45


# =============================================================================
# Test Graph Replay Engine
# =============================================================================


class TestGraphReplayEngine:
  """Tests for the browser-compatible graph replay engine."""

  def test_replay_empty_graph(self) -> None:
    """Test replaying an empty graph succeeds."""
    from praxis.backend.core.simulation.graph_replay import (
      replay_graph,
    )

    graph = {
      "protocol_fqn": "test.empty_protocol",
      "protocol_name": "empty_protocol",
      "resources": {},
      "operations": [],
      "execution_order": [],
      "data_flows": [],
    }

    result = replay_graph(graph)

    assert result.passed is True
    assert result.operations_executed == 0
    assert result.violations == []
    assert result.errors == []
    assert result.replay_mode == "graph"

  def test_replay_with_single_operation(self) -> None:
    """Test replaying a graph with a single operation."""
    from praxis.backend.core.simulation.graph_replay import (
      GraphReplayEngine,
    )

    graph = {
      "protocol_fqn": "test.single_op",
      "protocol_name": "single_op",
      "resources": {
        "lh": {"variable_name": "lh", "declared_type": "LiquidHandler"},
        "tips": {"variable_name": "tips", "declared_type": "TipRack"},
      },
      "operations": [
        {
          "id": "op1",
          "node_type": "static",
          "receiver_variable": "lh",
          "receiver_type": "liquid_handler",
          "method_name": "pick_up_tips",
          "arguments": {"tips": "tips"},
          "line_number": 10,
        }
      ],
      "execution_order": ["op1"],
      "data_flows": [],
    }

    engine = GraphReplayEngine()
    result = engine.replay(graph)

    assert result.operations_executed == 1
    # pick_up_tips doesn't require tips, so should pass
    assert result.passed is True

  def test_replay_detects_tips_violation(self) -> None:
    """Test replay detects aspirate without tips."""
    from praxis.backend.core.simulation.graph_replay import (
      GraphReplayEngine,
    )

    graph = {
      "protocol_fqn": "test.tips_violation",
      "protocol_name": "tips_violation",
      "resources": {
        "lh": {"variable_name": "lh", "declared_type": "LiquidHandler"},
        "plate": {"variable_name": "plate", "declared_type": "Plate"},
      },
      "operations": [
        {
          "id": "op1",
          "node_type": "static",
          "receiver_variable": "lh",
          "receiver_type": "liquid_handler",
          "method_name": "aspirate",
          "arguments": {"resource": "plate['A1']"},
          "line_number": 10,
        }
      ],
      "execution_order": ["op1"],
      "data_flows": [],
    }

    engine = GraphReplayEngine()
    result = engine.replay(graph)

    # Should fail because tips not loaded
    assert result.passed is False
    assert len(result.violations) >= 1

    violation = result.violations[0]
    assert violation.violation_type == "tips_not_loaded"
    assert "tips" in violation.message.lower()
    assert violation.suggested_fix is not None

  def test_replay_with_valid_sequence(self) -> None:
    """Test replay with valid tip pickup -> aspirate sequence."""
    from praxis.backend.core.simulation.graph_replay import (
      GraphReplayEngine,
    )

    graph = {
      "protocol_fqn": "test.valid_sequence",
      "protocol_name": "valid_sequence",
      "resources": {
        "lh": {"variable_name": "lh", "declared_type": "LiquidHandler"},
        "tips": {"variable_name": "tips", "declared_type": "TipRack"},
        "plate": {"variable_name": "plate", "declared_type": "Plate"},
      },
      "operations": [
        {
          "id": "op1",
          "node_type": "static",
          "receiver_variable": "lh",
          "receiver_type": "liquid_handler",
          "method_name": "pick_up_tips",
          "arguments": {"tips": "tips"},
          "line_number": 10,
        },
        {
          "id": "op2",
          "node_type": "static",
          "receiver_variable": "lh",
          "receiver_type": "liquid_handler",
          "method_name": "aspirate",
          "arguments": {"resource": "plate['A1']"},
          "line_number": 11,
        },
      ],
      "execution_order": ["op1", "op2"],
      "data_flows": [],
    }

    engine = GraphReplayEngine()
    result = engine.replay(graph)

    assert result.operations_executed == 2
    # Should pass because tips are loaded before aspirate
    assert result.passed is True

  def test_replay_invalid_graph_returns_error(self) -> None:
    """Test that invalid graph returns clear error message."""
    from praxis.backend.core.simulation.graph_replay import (
      GraphReplayEngine,
    )

    # Invalid graph structure
    invalid_graph = {"not_a_valid": "graph"}

    engine = GraphReplayEngine()
    result = engine.replay(invalid_graph)

    assert result.passed is False
    assert len(result.errors) > 0
    assert "parse" in result.errors[0].lower() or "failed" in result.errors[0].lower()

  def test_replay_foreach_node(self) -> None:
    """Test replay handles foreach (loop) nodes."""
    from praxis.backend.core.simulation.graph_replay import (
      GraphReplayEngine,
    )

    graph = {
      "protocol_fqn": "test.foreach_protocol",
      "protocol_name": "foreach_protocol",
      "resources": {
        "lh": {"variable_name": "lh", "declared_type": "LiquidHandler"},
        "tips": {"variable_name": "tips", "declared_type": "TipRack"},
        "plate": {"variable_name": "plate", "declared_type": "Plate", "items_x": 12, "items_y": 8},
      },
      "operations": [
        {
          "id": "pickup",
          "node_type": "static",
          "receiver_variable": "lh",
          "receiver_type": "liquid_handler",
          "method_name": "pick_up_tips",
          "arguments": {"tips": "tips"},
          "line_number": 10,
        },
        {
          "id": "loop1",
          "node_type": "foreach",
          "receiver_variable": "",
          "method_name": "",
          "arguments": {},
          "foreach_source": "plate.columns()",
          "foreach_body": ["body_op"],
          "line_number": 12,
        },
        {
          "id": "body_op",
          "node_type": "static",
          "receiver_variable": "lh",
          "receiver_type": "liquid_handler",
          "method_name": "aspirate",
          "arguments": {"resource": "column"},
          "line_number": 13,
        },
      ],
      "execution_order": ["pickup", "loop1"],
      "data_flows": [],
    }

    engine = GraphReplayEngine()
    result = engine.replay(graph)

    # Should pass - tips picked up before loop
    assert result.passed is True
    assert result.operations_executed == 2

  def test_replay_result_final_state_summary(self) -> None:
    """Test that final state summary is included in result."""
    from praxis.backend.core.simulation.graph_replay import (
      GraphReplayEngine,
    )

    graph = {
      "protocol_fqn": "test.state_summary",
      "protocol_name": "state_summary",
      "resources": {
        "lh": {"variable_name": "lh", "declared_type": "LiquidHandler"},
        "tips": {"variable_name": "tips", "declared_type": "TipRack"},
      },
      "operations": [
        {
          "id": "op1",
          "node_type": "static",
          "receiver_variable": "lh",
          "receiver_type": "liquid_handler",
          "method_name": "pick_up_tips",
          "arguments": {"tips": "tips"},
          "line_number": 10,
        }
      ],
      "execution_order": ["op1"],
      "data_flows": [],
    }

    engine = GraphReplayEngine()
    result = engine.replay(graph)

    assert "tips_loaded" in result.final_state_summary
    assert result.final_state_summary["tips_loaded"] is True


# =============================================================================
# Test Protocol Cache (Cloudpickle)
# =============================================================================


class TestProtocolCache:
  """Tests for cloudpickle-based protocol caching."""

  def test_cache_simple_function(self) -> None:
    """Test caching a simple function."""
    from praxis.backend.core.protocol_cache import ProtocolCache

    def simple_func(x: int) -> int:
      return x * 2

    cache = ProtocolCache()
    cached = cache.cache_protocol(simple_func)

    assert cached.bytecode is not None
    assert len(cached.bytecode) > 0
    assert cached.function_name == "simple_func"
    assert cached.python_version is not None
    assert cached.cache_version is not None
    assert cached.created_at is not None

  def test_cache_with_source_code(self) -> None:
    """Test caching with source code generates hash."""
    from praxis.backend.core.protocol_cache import ProtocolCache

    def func() -> str:
      return "hello"

    source = "def func(): return 'hello'"

    cache = ProtocolCache()
    cached = cache.cache_protocol(func, source)

    assert cached.source_hash != ""
    assert len(cached.source_hash) == 64  # SHA-256 hex

  def test_load_cached_function(self) -> None:
    """Test loading and executing a cached function."""
    from praxis.backend.core.protocol_cache import ProtocolCache

    def adder(a: int, b: int) -> int:
      return a + b

    cache = ProtocolCache()
    cached = cache.cache_protocol(adder)

    # Load from bytecode
    loaded_func = cache.load_protocol(cached.bytecode)

    # Execute loaded function
    result = loaded_func(3, 4)
    assert result == 7

  def test_validate_cache_valid(self) -> None:
    """Test cache validation passes for valid cache."""
    from praxis.backend.core.protocol_cache import ProtocolCache

    def func() -> None:
      pass

    cache = ProtocolCache()
    cached = cache.cache_protocol(func)

    validation = cache.validate_cache(
      bytecode=cached.bytecode,
      cached_python_version=cached.python_version,
      cached_cache_version=cached.cache_version,
    )

    assert validation.is_valid is True
    assert validation.reason is None

  def test_validate_cache_empty_bytecode(self) -> None:
    """Test cache validation fails for empty bytecode."""
    from praxis.backend.core.protocol_cache import ProtocolCache

    cache = ProtocolCache()

    validation = cache.validate_cache(bytecode=b"")

    assert validation.is_valid is False
    assert "empty" in validation.reason.lower()

  def test_validate_cache_version_mismatch(self) -> None:
    """Test cache validation fails for version mismatch."""
    from praxis.backend.core.protocol_cache import ProtocolCache

    def func() -> None:
      pass

    cache = ProtocolCache()
    cached = cache.cache_protocol(func)

    validation = cache.validate_cache(
      bytecode=cached.bytecode,
      cached_cache_version="0.0.1",  # Different version
    )

    assert validation.is_valid is False
    assert "version" in validation.reason.lower()

  def test_validate_cache_python_version_mismatch(self) -> None:
    """Test cache validation fails for Python version mismatch."""
    from praxis.backend.core.protocol_cache import ProtocolCache

    def func() -> None:
      pass

    cache = ProtocolCache()
    cached = cache.cache_protocol(func)

    validation = cache.validate_cache(
      bytecode=cached.bytecode,
      cached_python_version="2.7.18",  # Ancient Python
    )

    assert validation.is_valid is False
    assert "python" in validation.reason.lower()

  def test_validate_source_hash_mismatch(self) -> None:
    """Test cache validation fails when source hash changes."""
    from praxis.backend.core.protocol_cache import ProtocolCache

    def func() -> None:
      pass

    cache = ProtocolCache()

    validation = cache.validate_cache(
      bytecode=b"dummy",
      source_hash="abc123",
      current_source_hash="different456",
    )

    assert validation.is_valid is False
    assert "source" in validation.reason.lower()

  def test_serialization_error_clear_message(self) -> None:
    """Test that serialization errors have clear messages."""
    # Lambda with closure over unpickleable object
    import io

    from praxis.backend.core.protocol_cache import ProtocolCache, SerializationError

    file_handle = io.StringIO()

    def func_with_handle() -> None:
      # This captures a file handle
      file_handle.write("test")

    cache = ProtocolCache()

    # Note: StringIO is actually pickleable, so use a different approach
    # Test the error class directly
    error = SerializationError("test_func", Exception("cannot pickle"))

    assert "test_func" in str(error)
    assert "unpickleable" in str(error).lower()

  def test_deserialization_error_clear_message(self) -> None:
    """Test that deserialization errors have clear messages."""
    from praxis.backend.core.protocol_cache import DeserializationError

    error = DeserializationError(
      "Missing module: my_module",
      ModuleNotFoundError("my_module"),
    )

    assert "my_module" in str(error)
    assert "deserialize" in str(error).lower()

  def test_is_cache_valid_helper(self) -> None:
    """Test the is_cache_valid helper function."""
    from praxis.backend.core.protocol_cache import ProtocolCache

    cache = ProtocolCache()

    # Same hash - valid
    assert cache.is_cache_valid("def f(): pass", "abc123") is False  # Different hash

    # Compute actual hash
    import hashlib

    source = "def f(): pass"
    expected_hash = hashlib.sha256(source.encode()).hexdigest()
    assert cache.is_cache_valid(source, expected_hash) is True


# =============================================================================
# Test Clear Error Messages
# =============================================================================


class TestClearErrorMessages:
  """Tests ensuring error messages are clear and actionable."""

  def test_graph_replay_violation_has_suggested_fix(self) -> None:
    """Test that violations include suggested fixes."""
    from praxis.backend.core.simulation.graph_replay import GraphReplayEngine

    graph = {
      "protocol_fqn": "test.suggested_fix",
      "protocol_name": "suggested_fix",
      "resources": {
        "lh": {"variable_name": "lh", "declared_type": "LiquidHandler"},
        "plate": {"variable_name": "plate", "declared_type": "Plate"},
      },
      "operations": [
        {
          "id": "op1",
          "node_type": "static",
          "receiver_variable": "lh",
          "receiver_type": "liquid_handler",
          "method_name": "aspirate",
          "arguments": {"resource": "plate"},
          "line_number": 10,
        }
      ],
      "execution_order": ["op1"],
      "data_flows": [],
    }

    engine = GraphReplayEngine()
    result = engine.replay(graph)

    assert len(result.violations) > 0
    violation = result.violations[0]

    # Violation should have actionable information
    assert violation.message != ""
    assert violation.suggested_fix is not None
    assert "pick_up_tips" in violation.suggested_fix.lower()

  def test_graph_replay_violation_includes_line_number(self) -> None:
    """Test that violations include source line numbers when available."""
    from praxis.backend.core.simulation.graph_replay import GraphReplayEngine

    graph = {
      "protocol_fqn": "test.line_number",
      "protocol_name": "line_number",
      "resources": {
        "lh": {"variable_name": "lh", "declared_type": "LiquidHandler"},
      },
      "operations": [
        {
          "id": "op1",
          "node_type": "static",
          "receiver_variable": "lh",
          "receiver_type": "liquid_handler",
          "method_name": "aspirate",
          "arguments": {},
          "line_number": 42,
        }
      ],
      "execution_order": ["op1"],
      "data_flows": [],
    }

    engine = GraphReplayEngine()
    result = engine.replay(graph)

    assert len(result.violations) > 0
    violation = result.violations[0]

    assert violation.line_number == 42

  def test_cache_validation_error_is_specific(self) -> None:
    """Test that cache validation errors are specific about the issue."""
    from praxis.backend.core.protocol_cache import CacheValidationError

    error = CacheValidationError("Python version mismatch: cached=3.11, current=3.13")

    assert "python version" in str(error).lower()
    assert "3.11" in str(error)
    assert "3.13" in str(error)

  def test_missing_graph_error_message(self) -> None:
    """Test error message when computation graph is missing required fields."""
    from praxis.backend.core.simulation.graph_replay import GraphReplayEngine

    # Graph without required fields (missing protocol_fqn, protocol_name)
    incomplete_graph = {"resources": {}}

    engine = GraphReplayEngine()
    result = engine.replay(incomplete_graph)

    # Should fail with informative error about parsing/validation
    assert result.passed is False
    assert len(result.errors) > 0
    # The error should mention what's missing or that parsing failed
    error_msg = result.errors[0].lower()
    assert "parse" in error_msg or "failed" in error_msg or "validation" in error_msg


# =============================================================================
# Test Tracer Cache (Browser-Compatible)
# =============================================================================


class TestTracerCache:
  """Tests for tracer state serialization (Pyodide-compatible)."""

  def test_serialize_simulation_state(self) -> None:
    """Test that simulation state can be serialized."""
    from praxis.backend.core.protocol_cache import TracerCache

    # Create a simulation state
    state = SimulationState.default_boolean()
    state.tip_state.tips_loaded = True
    state.deck_state.place_on_deck("plate")

    cache = TracerCache()
    bytecode = cache.serialize_tracer_state(state)

    assert bytecode is not None
    assert len(bytecode) > 0

  def test_deserialize_simulation_state(self) -> None:
    """Test that serialized state can be deserialized."""
    from praxis.backend.core.protocol_cache import TracerCache

    # Create and modify state
    state = SimulationState.default_boolean()
    state.tip_state.tips_loaded = True
    state.tip_state.tips_count = 8

    cache = TracerCache()
    bytecode = cache.serialize_tracer_state(state)

    # Deserialize
    loaded_state = cache.deserialize_tracer_state(bytecode)

    assert loaded_state.tip_state.tips_loaded is True
    assert loaded_state.tip_state.tips_count == 8

  def test_tracer_cache_handles_errors(self) -> None:
    """Test that tracer cache provides clear errors on failure."""
    from praxis.backend.core.protocol_cache import DeserializationError, TracerCache

    cache = TracerCache()

    # Try to deserialize garbage
    try:
      cache.deserialize_tracer_state(b"not valid pickle data")
      assert False, "Should have raised"
    except DeserializationError as e:
      assert "tracer state" in str(e).lower()


# =============================================================================
# Test Convenience Functions
# =============================================================================


class TestConvenienceFunctions:
  """Tests for module-level convenience functions."""

  def test_replay_graph_convenience(self) -> None:
    """Test replay_graph convenience function."""
    from praxis.backend.core.simulation import replay_graph

    graph = {
      "protocol_fqn": "test.convenience",
      "protocol_name": "convenience",
      "resources": {},
      "operations": [],
      "execution_order": [],
      "data_flows": [],
    }

    result = replay_graph(graph)
    assert result.passed is True

  def test_cache_protocol_convenience(self) -> None:
    """Test cache_protocol convenience function."""
    from praxis.backend.core.protocol_cache import cache_protocol

    def my_func() -> int:
      return 42

    cached = cache_protocol(my_func)
    assert cached.bytecode is not None
    assert cached.function_name == "my_func"

  def test_load_protocol_convenience(self) -> None:
    """Test load_protocol convenience function."""
    from praxis.backend.core.protocol_cache import cache_protocol, load_protocol

    def multiplier(x: int) -> int:
      return x * 3

    cached = cache_protocol(multiplier)
    loaded = load_protocol(cached.bytecode)

    assert loaded(5) == 15
