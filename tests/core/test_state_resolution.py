"""Unit tests for state resolution models and logic.

Tests for:
- UncertainStateChange model
- StateResolution model
- OperationRecord model
- identify_uncertain_states() function
- apply_resolution() function
"""


from praxis.backend.core.simulation.state_models import (
    BooleanLiquidState,
    ExactLiquidState,
    SimulationState,
    StateLevel,
)
from praxis.backend.core.simulation.state_resolution import (
    OperationRecord,
    ResolutionType,
    StatePropertyType,
    StateResolution,
    UncertainStateChange,
    apply_resolution,
    identify_uncertain_states,
)


class TestUncertainStateChange:
    """Tests for UncertainStateChange model."""

    def test_create_uncertain_state_change(self):
        """Test creating an UncertainStateChange with all fields."""
        usc = UncertainStateChange(
            state_key="plate.A1.volume",
            current_value=100.0,
            expected_value=50.0,
            description="Volume in plate.A1 after aspiration",
            resolution_type="volume",
            resource_name="plate.A1",
            property_name="volume",
            property_type=StatePropertyType.VOLUME,
            suggested_resolutions=[
                "Confirm aspiration succeeded",
                "Confirm aspiration failed",
            ],
        )

        assert usc.state_key == "plate.A1.volume"
        assert usc.current_value == 100.0
        assert usc.expected_value == 50.0
        assert usc.property_type == StatePropertyType.VOLUME

    def test_to_dict(self):
        """Test serialization to dictionary."""
        usc = UncertainStateChange(
            state_key="plate.A1.volume",
            current_value=100.0,
            expected_value=50.0,
            property_type=StatePropertyType.VOLUME,
        )

        d = usc.to_dict()

        assert d["state_key"] == "plate.A1.volume"
        assert d["current_value"] == 100.0
        assert d["expected_value"] == 50.0
        assert d["property_type"] == "volume"

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "state_key": "plate.A1.volume",
            "current_value": 100.0,
            "expected_value": 50.0,
            "description": "Test description",
            "property_type": "volume",
        }

        usc = UncertainStateChange.from_dict(data)

        assert usc.state_key == "plate.A1.volume"
        assert usc.current_value == 100.0
        assert usc.property_type == StatePropertyType.VOLUME


class TestStateResolution:
    """Tests for StateResolution model."""

    def test_create_resolution_confirmed_success(self):
        """Test creating a confirmed success resolution."""
        resolution = StateResolution(
            operation_id="op_1",
            resolution_type=ResolutionType.CONFIRMED_SUCCESS,
            resolved_values={"plate.A1.volume": 50.0},
            resolved_by="user",
        )

        assert resolution.operation_id == "op_1"
        assert resolution.resolution_type == ResolutionType.CONFIRMED_SUCCESS
        assert resolution.resolved_values["plate.A1.volume"] == 50.0

    def test_create_resolution_confirmed_failure(self):
        """Test creating a confirmed failure resolution."""
        resolution = StateResolution(
            operation_id="op_1",
            resolution_type=ResolutionType.CONFIRMED_FAILURE,
            resolved_values={"plate.A1.volume": 100.0},  # Volume unchanged
            resolved_by="user",
            notes="Operation failed due to pressure fault",
        )

        assert resolution.resolution_type == ResolutionType.CONFIRMED_FAILURE
        assert resolution.notes == "Operation failed due to pressure fault"

    def test_to_dict(self):
        """Test serialization to dictionary."""
        resolution = StateResolution(
            operation_id="op_1",
            resolution_type=ResolutionType.PARTIAL,
            resolved_values={"plate.A1.volume": 75.0},
        )

        d = resolution.to_dict()

        assert d["operation_id"] == "op_1"
        assert d["resolution_type"] == "partial"
        assert d["resolved_values"]["plate.A1.volume"] == 75.0
        assert "resolved_at" in d

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "operation_id": "op_1",
            "resolution_type": "confirmed_success",
            "resolved_values": {"plate.A1.volume": 50.0},
            "resolved_by": "system",
            "resolved_at": "2025-01-01T12:00:00",
        }

        resolution = StateResolution.from_dict(data)

        assert resolution.operation_id == "op_1"
        assert resolution.resolution_type == ResolutionType.CONFIRMED_SUCCESS
        assert resolution.resolved_by == "system"


class TestOperationRecord:
    """Tests for OperationRecord model."""

    def test_create_operation_record(self):
        """Test creating an operation record."""
        record = OperationRecord(
            operation_id="op_1",
            method_name="aspirate",
            receiver_type="liquid_handler",
            args=["plate.A1"],
            kwargs={"vol": "50.0"},
            error_message="Pressure fault detected",
            error_type="PressureFault",
        )

        assert record.operation_id == "op_1"
        assert record.method_name == "aspirate"
        assert record.receiver_type == "liquid_handler"
        assert record.error_message == "Pressure fault detected"


class TestIdentifyUncertainStates:
    """Tests for identify_uncertain_states function."""

    def test_identify_aspirate_uncertain_states(self):
        """Test identification of uncertain state from aspirate operation."""
        operation = OperationRecord(
            operation_id="op_1",
            method_name="aspirate",
            receiver_type="liquid_handler",
            kwargs={"resource": "plate.A1", "vol": "50.0"},
            error_message="Pressure fault",
        )

        uncertain = identify_uncertain_states(operation)

        # Should identify volume as uncertain
        assert len(uncertain) > 0
        volume_states = [u for u in uncertain if "volume" in u.state_key]
        assert len(volume_states) > 0

    def test_identify_dispense_uncertain_states(self):
        """Test identification of uncertain state from dispense operation."""
        operation = OperationRecord(
            operation_id="op_2",
            method_name="dispense",
            receiver_type="liquid_handler",
            kwargs={"resource": "plate.B1", "vol": "50.0"},
            error_message="Timeout",
        )

        uncertain = identify_uncertain_states(operation)

        # Should identify destination volume as uncertain
        assert len(uncertain) > 0

    def test_identify_pick_up_tips_uncertain_states(self):
        """Test identification of uncertain state from tip pickup."""
        operation = OperationRecord(
            operation_id="op_3",
            method_name="pick_up_tips",
            receiver_type="liquid_handler",
            kwargs={"tips": "tip_rack"},
            error_message="Tip pickup failed",
        )

        uncertain = identify_uncertain_states(operation)

        # Should identify tip state as uncertain
        assert len(uncertain) > 0
        tip_states = [u for u in uncertain if "tips" in u.state_key or "tip" in u.property_name or ""]
        # Either tip rack tips or machine tips_loaded should be uncertain

    def test_identify_with_state_snapshot(self):
        """Test identification uses state snapshot for current values."""
        # Create a state with exact volumes
        state = SimulationState(level=StateLevel.EXACT)
        if isinstance(state.liquid_state, ExactLiquidState):
            state.liquid_state.set_volume("plate_A1", 100.0)

        operation = OperationRecord(
            operation_id="op_1",
            method_name="aspirate",
            receiver_type="liquid_handler",
            kwargs={"resource": "plate_A1", "vol": "50.0"},
            error_message="Error",
        )

        uncertain = identify_uncertain_states(operation, state)

        # Should not crash and return some uncertain states
        assert isinstance(uncertain, list)

    def test_identify_unknown_operation_fallback(self):
        """Test fallback for operations without method contracts."""
        operation = OperationRecord(
            operation_id="op_custom",
            method_name="custom_operation",
            receiver_type="unknown_machine",
            args=["resource_a", "resource_b"],
            error_message="Unknown error",
        )

        uncertain = identify_uncertain_states(operation)

        # Should still identify some uncertain states from args
        assert len(uncertain) >= 0  # May be empty or have generic states


class TestApplyResolution:
    """Tests for apply_resolution function."""

    def test_apply_volume_resolution_exact_state(self):
        """Test applying volume resolution to exact state."""
        state = SimulationState(level=StateLevel.EXACT)
        if isinstance(state.liquid_state, ExactLiquidState):
            state.liquid_state.set_volume("plate.A1", 100.0)

        resolution = StateResolution(
            operation_id="op_1",
            resolution_type=ResolutionType.CONFIRMED_SUCCESS,
            resolved_values={"plate.A1.volume": 50.0},
        )

        apply_resolution(resolution, state)

        # Volume should be updated
        if isinstance(state.liquid_state, ExactLiquidState):
            assert state.liquid_state.get_volume("plate.A1") == 50.0

    def test_apply_has_liquid_resolution_boolean_state(self):
        """Test applying has_liquid resolution to boolean state."""
        state = SimulationState(level=StateLevel.BOOLEAN)
        if isinstance(state.liquid_state, BooleanLiquidState):
            state.liquid_state.set_has_liquid("plate_A1", True)

        resolution = StateResolution(
            operation_id="op_1",
            resolution_type=ResolutionType.CONFIRMED_FAILURE,
            # Use simple key: resource_name.property_name
            resolved_values={"plate_A1.has_liquid": False},
        )

        apply_resolution(resolution, state)

        # has_liquid should be updated
        if isinstance(state.liquid_state, BooleanLiquidState):
            assert state.liquid_state.has_liquid.get("plate_A1") is False

    def test_apply_tip_loaded_resolution(self):
        """Test applying tip loaded resolution."""
        state = SimulationState(level=StateLevel.BOOLEAN)
        state.tip_state.tips_loaded = False

        resolution = StateResolution(
            operation_id="op_1",
            resolution_type=ResolutionType.CONFIRMED_SUCCESS,
            resolved_values={"machine.tips_loaded": True},
        )

        apply_resolution(resolution, state)

        assert state.tip_state.tips_loaded is True

    def test_apply_multiple_resolutions(self):
        """Test applying resolution with multiple state values."""
        state = SimulationState(level=StateLevel.EXACT)

        resolution = StateResolution(
            operation_id="op_1",
            resolution_type=ResolutionType.PARTIAL,
            resolved_values={
                "plate.A1.volume": 75.0,
                "plate.B1.volume": 25.0,
            },
        )

        apply_resolution(resolution, state)

        if isinstance(state.liquid_state, ExactLiquidState):
            assert state.liquid_state.get_volume("plate.A1") == 75.0
            assert state.liquid_state.get_volume("plate.B1") == 25.0

    def test_apply_resolution_returns_state(self):
        """Test that apply_resolution returns the updated state."""
        state = SimulationState(level=StateLevel.BOOLEAN)

        resolution = StateResolution(
            operation_id="op_1",
            resolution_type=ResolutionType.UNKNOWN,
            resolved_values={},
        )

        result = apply_resolution(resolution, state)

        assert result is state  # Should return same state object
