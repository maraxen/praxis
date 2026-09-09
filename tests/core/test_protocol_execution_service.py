"""Tests for core/protocol_execution_service.py."""

from unittest.mock import AsyncMock, Mock

import pytest

from praxis.backend.core.protocol_execution_service import ProtocolExecutionService
from praxis.backend.models import ProtocolRunStatusEnum
from praxis.backend.utils.uuid import uuid7


class TestProtocolExecutionServiceInit:

    """Tests for ProtocolExecutionService initialization."""

    def test_protocol_execution_service_initialization(self) -> None:
        """Test ProtocolExecutionService initialization."""
        mock_db_session_factory = Mock()
        mock_asset_manager = Mock()
        mock_workcell_runtime = Mock()
        mock_scheduler = Mock()
        mock_orchestrator = Mock()
        mock_protocol_run_service = Mock()
        mock_protocol_definition_service = Mock()

        service = ProtocolExecutionService(
            db_session_factory=mock_db_session_factory,
            asset_manager=mock_asset_manager,
            workcell_runtime=mock_workcell_runtime,
            scheduler=mock_scheduler,
            orchestrator=mock_orchestrator,
            protocol_run_service=mock_protocol_run_service,
            protocol_definition_service=mock_protocol_definition_service,
        )

        assert service.db_session_factory == mock_db_session_factory
        assert service.asset_manager == mock_asset_manager
        assert service.workcell_runtime == mock_workcell_runtime
        assert service.scheduler == mock_scheduler
        assert service.orchestrator == mock_orchestrator
        assert service.protocol_run_service == mock_protocol_run_service
        assert service.protocol_definition_service == mock_protocol_definition_service


class TestExecuteProtocolImmediately:

    """Tests for execute_protocol_immediately method."""

    @pytest.mark.asyncio
    async def test_execute_protocol_immediately_success(self) -> None:
        """Test immediate protocol execution."""
        service = ProtocolExecutionService(
            db_session_factory=Mock(),
            asset_manager=Mock(),
            workcell_runtime=Mock(),
            scheduler=Mock(),
            orchestrator=Mock(),
            protocol_run_service=Mock(),
            protocol_definition_service=Mock(),
        )

        mock_protocol_run = Mock()
        mock_protocol_run.accession_id = uuid7()

        service.orchestrator.execute_protocol = AsyncMock(return_value=mock_protocol_run)

        result = await service.execute_protocol_immediately(
            protocol_name="test_protocol",
            user_input_params={"param1": "value1"},
            initial_state_data={"state": "initial"},
        )

        assert result == mock_protocol_run
        service.orchestrator.execute_protocol.assert_called_once_with(
            protocol_name="test_protocol",
            input_parameters={"param1": "value1"},
            initial_state_data={"state": "initial"},
            protocol_version=None,
            commit_hash=None,
            source_name=None,
            is_simulation=False,
        )

    @pytest.mark.asyncio
    async def test_execute_protocol_immediately_with_version(self) -> None:
        """Test immediate execution with protocol version."""
        service = ProtocolExecutionService(
            db_session_factory=Mock(),
            asset_manager=Mock(),
            workcell_runtime=Mock(),
            scheduler=Mock(),
            orchestrator=Mock(),
            protocol_run_service=Mock(),
            protocol_definition_service=Mock(),
        )

        mock_protocol_run = Mock()
        service.orchestrator.execute_protocol = AsyncMock(return_value=mock_protocol_run)

        result = await service.execute_protocol_immediately(
            protocol_name="test_protocol",
            protocol_version="1.0",
            commit_hash="abc123",
            source_name="test_source",
        )

        assert result == mock_protocol_run
        service.orchestrator.execute_protocol.assert_called_once()
        call_kwargs = service.orchestrator.execute_protocol.call_args.kwargs
        assert call_kwargs["protocol_version"] == "1.0"
        assert call_kwargs["commit_hash"] == "abc123"
        assert call_kwargs["source_name"] == "test_source"
        assert call_kwargs["is_simulation"] is False


class TestScheduleProtocolExecution:

    """Tests for schedule_protocol_execution method."""

    @pytest.mark.asyncio
    async def test_schedule_protocol_execution_success(self) -> None:
        """Test successful protocol scheduling."""
        # Create mock session context manager
        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        service = ProtocolExecutionService(
            db_session_factory=mock_db_session_factory,
            asset_manager=Mock(),
            workcell_runtime=Mock(),
            scheduler=Mock(),
            orchestrator=Mock(),
            protocol_run_service=Mock(),
            protocol_definition_service=Mock(),
        )

        # Mock protocol definition
        mock_protocol_def = Mock()
        mock_protocol_def.accession_id = uuid7()
        mock_protocol_def.name = "test_protocol"

        # Mock protocol run ORM
        mock_protocol_run = Mock()
        mock_protocol_run.accession_id = uuid7()

        service.protocol_definition_service.get_by_name = AsyncMock(return_value=mock_protocol_def)
        service.protocol_run_service.create = AsyncMock(return_value=mock_protocol_run)
        service.scheduler.schedule_protocol_execution = AsyncMock(return_value=True)

        result = await service.schedule_protocol_execution(
            protocol_name="test_protocol",
            user_input_params={"param1": "value1"},
            initial_state_data={"state": "initial"},
        )

        assert result == mock_protocol_run
        service.scheduler.schedule_protocol_execution.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_protocol_execution_protocol_not_found(self) -> None:
        """Test scheduling when protocol is not found."""
        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        service = ProtocolExecutionService(
            db_session_factory=mock_db_session_factory,
            asset_manager=Mock(),
            workcell_runtime=Mock(),
            scheduler=Mock(),
            orchestrator=Mock(),
            protocol_run_service=Mock(),
            protocol_definition_service=Mock(),
        )

        service.protocol_definition_service.get_by_name = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="not found"):
            await service.schedule_protocol_execution(
                protocol_name="nonexistent_protocol",
            )

    @pytest.mark.asyncio
    async def test_schedule_protocol_execution_scheduler_fails(self) -> None:
        """Test handling when scheduler fails."""
        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        service = ProtocolExecutionService(
            db_session_factory=mock_db_session_factory,
            asset_manager=Mock(),
            workcell_runtime=Mock(),
            scheduler=Mock(),
            orchestrator=Mock(),
            protocol_run_service=Mock(),
            protocol_definition_service=Mock(),
        )

        mock_protocol_def = Mock()
        mock_protocol_def.accession_id = uuid7()

        mock_protocol_run = Mock()
        mock_protocol_run.accession_id = uuid7()

        service.protocol_definition_service.get_by_name = AsyncMock(return_value=mock_protocol_def)
        service.protocol_run_service.create = AsyncMock(return_value=mock_protocol_run)
        service.scheduler.schedule_protocol_execution = AsyncMock(return_value=False)

        with pytest.raises(RuntimeError, match="Failed to schedule"):
            await service.schedule_protocol_execution(
                protocol_name="test_protocol",
            )


class TestGetProtocolRunStatus:

    """Tests for get_protocol_run_status method."""

    @pytest.mark.asyncio
    async def test_get_protocol_run_status_success(self) -> None:
        """Test successful status retrieval."""
        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        service = ProtocolExecutionService(
            db_session_factory=mock_db_session_factory,
            asset_manager=Mock(),
            workcell_runtime=Mock(),
            scheduler=Mock(),
            orchestrator=Mock(),
            protocol_run_service=Mock(),
            protocol_definition_service=Mock(),
        )

        run_id = uuid7()

        # Mock protocol run ORM
        mock_protocol_run = Mock()
        mock_protocol_run.status = ProtocolRunStatusEnum.COMPLETED
        mock_protocol_run.created_at = Mock()
        mock_protocol_run.created_at.isoformat.return_value = "2025-01-01T00:00:00"
        mock_protocol_run.start_time = None
        mock_protocol_run.end_time = None
        mock_protocol_run.duration_ms = None
        mock_protocol_run.output_data_json = None
        mock_protocol_run.top_level_protocol_definition = Mock()
        mock_protocol_run.top_level_protocol_definition.name = "test_protocol"

        service.scheduler.get_schedule_status = AsyncMock(return_value={"status": "scheduled"})
        service.protocol_run_service.get = AsyncMock(return_value=mock_protocol_run)

        result = await service.get_protocol_run_status(run_id)

        assert result is not None
        assert result["protocol_run_id"] == str(run_id)
        assert result["status"] == "completed"  # .value returns lowercase
        assert result["protocol_name"] == "test_protocol"
        assert result["schedule_info"] == {"status": "scheduled"}

    @pytest.mark.asyncio
    async def test_get_protocol_run_status_not_found(self) -> None:
        """Test status retrieval when run is not found."""
        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        service = ProtocolExecutionService(
            db_session_factory=mock_db_session_factory,
            asset_manager=Mock(),
            workcell_runtime=Mock(),
            scheduler=Mock(),
            orchestrator=Mock(),
            protocol_run_service=Mock(),
            protocol_definition_service=Mock(),
        )

        run_id = uuid7()

        service.scheduler.get_schedule_status = AsyncMock(return_value=None)
        service.protocol_run_service.get = AsyncMock(return_value=None)

        result = await service.get_protocol_run_status(run_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_protocol_run_status_with_output_data(self) -> None:
        """Test status retrieval with output data."""
        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        service = ProtocolExecutionService(
            db_session_factory=mock_db_session_factory,
            asset_manager=Mock(),
            workcell_runtime=Mock(),
            scheduler=Mock(),
            orchestrator=Mock(),
            protocol_run_service=Mock(),
            protocol_definition_service=Mock(),
        )

        run_id = uuid7()

        mock_protocol_run = Mock()
        mock_protocol_run.status = ProtocolRunStatusEnum.COMPLETED
        mock_protocol_run.created_at = Mock()
        mock_protocol_run.created_at.isoformat.return_value = "2025-01-01T00:00:00"
        mock_protocol_run.start_time = None
        mock_protocol_run.end_time = None
        mock_protocol_run.duration_ms = 1000
        mock_protocol_run.output_data_json = '{"result": "success"}'
        mock_protocol_run.top_level_protocol_definition = Mock()
        mock_protocol_run.top_level_protocol_definition.name = "test_protocol"

        service.scheduler.get_schedule_status = AsyncMock(return_value=None)
        service.protocol_run_service.get = AsyncMock(return_value=mock_protocol_run)

        result = await service.get_protocol_run_status(run_id)

        # Verify output data was parsed correctly
        assert result is not None
        assert result["output_data"] == {"result": "success"}
        assert result["status"] == "completed"


class TestCancelProtocolRun:

    """Tests for cancel_protocol_run method."""

    @pytest.mark.asyncio
    async def test_cancel_protocol_run_success(self) -> None:
        """Test successful protocol run cancellation."""
        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        service = ProtocolExecutionService(
            db_session_factory=mock_db_session_factory,
            asset_manager=Mock(),
            workcell_runtime=Mock(),
            scheduler=Mock(),
            orchestrator=Mock(),
            protocol_run_service=Mock(),
            protocol_definition_service=Mock(),
        )

        run_id = uuid7()

        service.scheduler.cancel_scheduled_run = AsyncMock(return_value=True)
        service.protocol_run_service.update_run_status = AsyncMock()
        service.protocol_run_service.get = AsyncMock(return_value=Mock(status=ProtocolRunStatusEnum.RUNNING))

        # Mock the locally imported send_control_command
        with pytest.MonkeyPatch.context() as m:
            mock_send_cmd = AsyncMock(return_value=True)
            m.setattr("praxis.backend.utils.run_control.send_control_command", mock_send_cmd)

            result = await service.cancel_protocol_run(run_id)

            assert result is True
            service.scheduler.cancel_scheduled_run.assert_called_once_with(run_id)
            service.protocol_run_service.update_run_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_protocol_run_scheduler_fails(self) -> None:
        """Test cancellation when scheduler fails."""
        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        service = ProtocolExecutionService(
            db_session_factory=mock_db_session_factory,
            asset_manager=Mock(),
            workcell_runtime=Mock(),
            scheduler=Mock(),
            orchestrator=Mock(),
            protocol_run_service=Mock(),
            protocol_definition_service=Mock(),
        )

        run_id = uuid7()

        service.scheduler.cancel_scheduled_run = AsyncMock(return_value=False)
        service.protocol_run_service.update_run_status = AsyncMock()

        # Mock the locally imported send_control_command
        with pytest.MonkeyPatch.context() as m:
            mock_send_cmd = AsyncMock(return_value=False)
            m.setattr("praxis.backend.utils.run_control.send_control_command", mock_send_cmd)

            result = await service.cancel_protocol_run(run_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_cancel_protocol_run_database_fails(self) -> None:
        """Test cancellation when database update fails."""
        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        service = ProtocolExecutionService(
            db_session_factory=mock_db_session_factory,
            asset_manager=Mock(),
            workcell_runtime=Mock(),
            scheduler=Mock(),
            orchestrator=Mock(),
            protocol_run_service=Mock(),
            protocol_definition_service=Mock(),
        )

        run_id = uuid7()

        service.scheduler.cancel_scheduled_run = AsyncMock(return_value=True)
        service.protocol_run_service.update_run_status = AsyncMock(side_effect=Exception("DB error"))

        # Mock the locally imported send_control_command
        with pytest.MonkeyPatch.context() as m:
            mock_send_cmd = AsyncMock(return_value=True)
            m.setattr("praxis.backend.utils.run_control.send_control_command", mock_send_cmd)

            result = await service.cancel_protocol_run(run_id)

            assert result is False


class TestModuleStructure:

    """Tests for module structure and exports."""

    def test_module_has_protocol_execution_service_class(self) -> None:
        """Test that module exports ProtocolExecutionService."""
        from praxis.backend.core import protocol_execution_service

        assert hasattr(protocol_execution_service, "ProtocolExecutionService")

    def test_module_has_logger(self) -> None:
        """Test that module defines logger."""
        from praxis.backend.core import protocol_execution_service

        assert hasattr(protocol_execution_service, "logger")
