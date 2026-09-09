"""Unit tests for StateResolutionService.

Tests for:
- Getting uncertain states
- Resolving states
- Resuming and aborting runs
- Audit logging
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.core.simulation.state_models import SimulationState, StateLevel
from praxis.backend.core.simulation.state_resolution import (
    OperationRecord,
    ResolutionType,
    StatePropertyType,
    UncertainStateChange,
)
from praxis.backend.models.enums.resolution import ResolutionActionEnum, ResolutionTypeEnum
from praxis.backend.models.enums.schedule import ScheduleStatusEnum
from praxis.backend.services.state_resolution_service import (
    StateResolutionRequest,
    StateResolutionService,
    UncertainStateChangeResponse,
)


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def service(mock_session):
    """Create a StateResolutionService with mock session."""
    return StateResolutionService(mock_session)


@pytest.fixture
def sample_operation():
    """Create a sample failed operation."""
    return OperationRecord(
        operation_id="op_1",
        method_name="aspirate",
        receiver_type="liquid_handler",
        kwargs={"resource": "plate.A1", "vol": "50"},
        error_message="Pressure fault detected",
        error_type="PressureFault",
    )


@pytest.fixture
def sample_schedule_entry():
    """Create a mock schedule entry."""
    entry = MagicMock()
    entry.accession_id = uuid4()
    entry.protocol_run_accession_id = uuid4()
    entry.status = ScheduleStatusEnum.FAILED
    entry.last_error_message = "Pressure fault detected"
    return entry


class TestStateResolutionService:
    """Tests for StateResolutionService."""

    def test_init(self, mock_session):
        """Test service initialization."""
        service = StateResolutionService(mock_session)
        assert service._session == mock_session
        assert service._pending_resolutions == {}
        assert service._operation_records == {}

    def test_register_failed_operation(self, service, sample_operation):
        """Test registering a failed operation."""
        run_id = uuid4()

        service.register_failed_operation(run_id, sample_operation)

        assert run_id in service._operation_records
        assert service._operation_records[run_id] == sample_operation

    def test_register_failed_operation_with_state(self, service, sample_operation):
        """Test registering a failed operation with state snapshot."""
        run_id = uuid4()
        state = SimulationState(level=StateLevel.BOOLEAN)

        service.register_failed_operation(run_id, sample_operation, state)

        assert run_id in service._operation_records
        assert run_id in service._state_snapshots
        assert service._state_snapshots[run_id] == state

    @pytest.mark.asyncio
    async def test_get_uncertain_states_not_found(self, service, mock_session):
        """Test getting uncertain states when run not found."""
        run_id = uuid4()

        # Mock empty result - execute returns a Result with scalar_one_or_none
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not found"):
            await service.get_uncertain_states(run_id)

    @pytest.mark.asyncio
    async def test_get_uncertain_states_wrong_status(
        self, service, mock_session, sample_schedule_entry
    ):
        """Test getting uncertain states when run is not in failed state."""
        run_id = uuid4()
        sample_schedule_entry.status = ScheduleStatusEnum.COMPLETED

        # Mock result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_schedule_entry
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError, match="not eligible"):
            await service.get_uncertain_states(run_id)

    @pytest.mark.asyncio
    async def test_get_uncertain_states_success(
        self, service, mock_session, sample_schedule_entry, sample_operation
    ):
        """Test successfully getting uncertain states."""
        run_id = sample_schedule_entry.accession_id

        # Register the operation first
        service.register_failed_operation(run_id, sample_operation)

        # Mock result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_schedule_entry
        mock_session.execute = AsyncMock(return_value=mock_result)

        uncertain = await service.get_uncertain_states(run_id)

        # Should return list of uncertain states
        assert isinstance(uncertain, list)
        # States should be cached
        assert run_id in service._pending_resolutions

    @pytest.mark.asyncio
    async def test_get_uncertain_states_cached(
        self, service, mock_session, sample_schedule_entry
    ):
        """Test that cached uncertain states are returned."""
        run_id = sample_schedule_entry.accession_id

        # Pre-populate cache
        cached_states = [
            UncertainStateChange(
                state_key="plate.A1.volume",
                current_value=100.0,
                property_type=StatePropertyType.VOLUME,
            )
        ]
        service._pending_resolutions[run_id] = cached_states

        # Mock result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_schedule_entry
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_uncertain_states(run_id)

        assert result == cached_states

    def test_map_resolution_type(self):
        """Test mapping core ResolutionType to ORM enum."""
        assert (
            StateResolutionService._map_resolution_type(ResolutionType.CONFIRMED_SUCCESS)
            == ResolutionTypeEnum.CONFIRMED_SUCCESS
        )
        assert (
            StateResolutionService._map_resolution_type(ResolutionType.CONFIRMED_FAILURE)
            == ResolutionTypeEnum.CONFIRMED_FAILURE
        )
        assert (
            StateResolutionService._map_resolution_type(ResolutionType.PARTIAL)
            == ResolutionTypeEnum.PARTIAL
        )
        assert (
            StateResolutionService._map_resolution_type(ResolutionType.ARBITRARY)
            == ResolutionTypeEnum.ARBITRARY
        )
        assert (
            StateResolutionService._map_resolution_type(ResolutionType.UNKNOWN)
            == ResolutionTypeEnum.UNKNOWN
        )


class TestPydanticModels:
    """Tests for Pydantic API models."""

    def test_uncertain_state_change_response_from_core(self):
        """Test creating response from core model."""
        core = UncertainStateChange(
            state_key="plate.A1.volume",
            current_value=100.0,
            expected_value=50.0,
            description="Volume after aspiration",
            property_type=StatePropertyType.VOLUME,
            suggested_resolutions=["Confirm success", "Confirm failure"],
        )

        response = UncertainStateChangeResponse.from_core(core)

        assert response.state_key == "plate.A1.volume"
        assert response.current_value == 100.0
        assert response.expected_value == 50.0
        assert response.property_type == "volume"

    def test_state_resolution_request_to_core(self):
        """Test converting request to core resolution."""
        request = StateResolutionRequest(
            operation_id="op_1",
            resolution_type="confirmed_success",
            resolved_values={"plate.A1.volume": 50.0},
            notes="Verified by visual inspection",
            action="resume",
        )

        core = request.to_core_resolution(resolved_by="user_123")

        assert core.operation_id == "op_1"
        assert core.resolution_type == ResolutionType.CONFIRMED_SUCCESS
        assert core.resolved_values["plate.A1.volume"] == 50.0
        assert core.resolved_by == "user_123"
        assert core.notes == "Verified by visual inspection"

    def test_state_resolution_request_get_action(self):
        """Test getting action enum from request."""
        request_resume = StateResolutionRequest(
            operation_id="op_1",
            resolution_type="confirmed_success",
            action="resume",
        )
        assert request_resume.get_action() == ResolutionActionEnum.RESUME

        request_abort = StateResolutionRequest(
            operation_id="op_1",
            resolution_type="confirmed_failure",
            action="abort",
        )
        assert request_abort.get_action() == ResolutionActionEnum.ABORT

        request_retry = StateResolutionRequest(
            operation_id="op_1",
            resolution_type="unknown",
            action="retry",
        )
        assert request_retry.get_action() == ResolutionActionEnum.RETRY

    def test_state_resolution_request_defaults(self):
        """Test default values in request model."""
        request = StateResolutionRequest(
            operation_id="op_1",
            resolution_type="confirmed_success",
        )

        assert request.resolved_values == {}
        assert request.notes is None
        assert request.action == "resume"
