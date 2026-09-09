"""Comprehensive tests for ProtocolRunService and function call logging.

This test suite demonstrates advanced service testing patterns including:
- Complex status management with state transitions
- Timestamp and duration calculations
- JSONB field handling (input params, output data, state)
- Relationship management (protocol definition, function calls)
- Advanced filtering and querying
- Helper function testing (function call logging)

These tests serve as examples for testing complex services with:
- Multiple state transitions
- Timing/duration tracking
- Error handling and validation
- Integration with other models
"""
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.filters import SearchFilters
from praxis.backend.models.domain.protocol import (
    FunctionCallLog,
    FunctionProtocolDefinition,
    ProtocolRunCreate,
    ProtocolRunStatusEnum,
)
from praxis.backend.models.enums import FunctionCallStatusEnum
from praxis.backend.services.protocols import (
    log_function_call_end,
    log_function_call_start,
    protocol_run_service,
)


@pytest_asyncio.fixture
async def protocol_definition(db_session: AsyncSession) -> FunctionProtocolDefinition:
    """Create a protocol definition for testing."""
    # Create protocol definition without init=False relationship arguments
    protocol = FunctionProtocolDefinition(
        name="test_protocol",
        fqn="test.protocols.test_protocol",
        version="1.0.0",
        is_top_level=True,
    )
    db_session.add(protocol)
    await db_session.flush()
    return protocol


@pytest.mark.asyncio
async def test_protocol_run_service_create_pending(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test creating a protocol run in PENDING status.

    Demonstrates:
    - Basic service.create() usage
    - Status-dependent behavior (no start_time for PENDING)
    - Verification of all created fields
    """
    from praxis.backend.utils.uuid import uuid7

    run_id = uuid7()
    create_data = ProtocolRunCreate(
        run_accession_id=run_id,
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        status=ProtocolRunStatusEnum.PENDING,
        input_parameters_json={"volume": 100, "temperature": 37},
    )

    run = await protocol_run_service.create(db_session, obj_in=create_data)

    # Verify creation
    assert run.accession_id == run_id
    assert run.top_level_protocol_definition_accession_id == protocol_definition.accession_id
    assert run.status == ProtocolRunStatusEnum.PENDING
    assert run.start_time is None  # PENDING runs don't have start time yet
    assert run.input_parameters_json == {"volume": 100, "temperature": 37}


@pytest.mark.asyncio
async def test_protocol_run_service_create_running(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test creating a protocol run in RUNNING status.

    Demonstrates:
    - Conditional logic in service (sets start_time for non-PENDING)
    - Timestamp verification
    """
    from praxis.backend.utils.uuid import uuid7

    run_id = uuid7()
    create_data = ProtocolRunCreate(
        run_accession_id=run_id,
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        status=ProtocolRunStatusEnum.RUNNING,
    )

    run = await protocol_run_service.create(db_session, obj_in=create_data)

    # Verify start_time was set for RUNNING status
    assert run.status == ProtocolRunStatusEnum.RUNNING
    assert run.start_time is not None
    assert isinstance(run.start_time, datetime)
    # Should be recent (within last minute)
    assert (datetime.now(timezone.utc) - run.start_time).total_seconds() < 60


@pytest.mark.asyncio
async def test_protocol_run_service_create_with_complex_jsonb(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test creating protocol run with complex JSONB fields.

    Demonstrates:
    - JSONB field handling for complex nested data
    - Multiple JSONB fields in one model
    """
    from praxis.backend.utils.uuid import uuid7

    input_params = {
        "volumes": [50, 100, 150],
        "source_wells": ["A1", "A2", "A3"],
        "dest_wells": ["B1", "B2", "B3"],
        "config": {"speed": "normal", "mix_cycles": 3},
    }
    initial_state = {
        "deck_layout": "config_a",
        "tip_count": 96,
        "plates": ["plate_001", "plate_002"],
    }

    create_data = ProtocolRunCreate(
        run_accession_id=uuid7(),
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        input_parameters_json=input_params,
        initial_state_json=initial_state,
    )

    run = await protocol_run_service.create(db_session, obj_in=create_data)

    # Verify JSONB fields stored correctly with nested access
    assert run.input_parameters_json == input_params
    assert run.input_parameters_json["volumes"] == [50, 100, 150]
    assert run.input_parameters_json["config"]["mix_cycles"] == 3
    assert run.initial_state_json == initial_state
    assert run.initial_state_json["plates"] == ["plate_001", "plate_002"]


@pytest.mark.asyncio
async def test_protocol_run_service_get_multi_basic(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test listing protocol runs with basic pagination.

    Demonstrates:
    - get_multi() usage
    - SearchFilters for pagination
    - Ordering verification (most recent first)
    """
    from praxis.backend.utils.uuid import uuid7

    # Create multiple runs
    runs = []
    for i in range(5):
        create_data = ProtocolRunCreate(
            run_accession_id=uuid7(),
            name=f"test_run_{i}",
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
            status=ProtocolRunStatusEnum.RUNNING if i % 2 == 0 else ProtocolRunStatusEnum.COMPLETED,
        )
        run = await protocol_run_service.create(db_session, obj_in=create_data)
        runs.append(run)

    # Get all runs
    filters = SearchFilters(skip=0, limit=10)
    retrieved_runs = await protocol_run_service.get_multi(db_session, filters=filters)

    # Verify
    assert len(retrieved_runs) >= 5
    run_names = [r.name for r in retrieved_runs]
    for i in range(5):
        assert f"test_run_{i}" in run_names


@pytest.mark.asyncio
async def test_protocol_run_service_get_multi_with_definition_filter(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test filtering protocol runs by definition ID.

    Demonstrates:
    - Advanced filtering with protocol_definition_accession_id
    - Ensuring correct runs are returned
    """
    from praxis.backend.utils.uuid import uuid7

    # Create another protocol definition
    other_protocol = FunctionProtocolDefinition(
        name="other_protocol",
        fqn="test.protocols.other_protocol",
        version="1.0.0",
        is_top_level=True,
    )
    db_session.add(other_protocol)
    await db_session.flush()

    # Create runs for both protocols
    run1 = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            name="run_proto1",
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        ),
    )
    run2 = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            name="run_proto2",
            top_level_protocol_definition_accession_id=other_protocol.accession_id,
        ),
    )

    # Filter by first protocol definition
    filters = SearchFilters(skip=0, limit=10)
    filtered_runs = await protocol_run_service.get_multi(
        db_session,
        filters=filters,
        protocol_definition_accession_id=protocol_definition.accession_id,
    )

    # Should only get runs for first protocol
    run_ids = [r.accession_id for r in filtered_runs]
    assert run1.accession_id in run_ids
    assert run2.accession_id not in run_ids


@pytest.mark.asyncio
async def test_protocol_run_service_get_multi_with_status_filter(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test filtering protocol runs by status.

    Demonstrates:
    - Status-based filtering
    - Combining multiple filters
    """
    from praxis.backend.utils.uuid import uuid7

    # Create runs with different statuses
    completed_run = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            name="completed_run",
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
            status=ProtocolRunStatusEnum.COMPLETED,
        ),
    )
    running_run = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            name="running_run",
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
            status=ProtocolRunStatusEnum.RUNNING,
        ),
    )

    # Filter by RUNNING status
    filters = SearchFilters(skip=0, limit=10)
    running_runs = await protocol_run_service.get_multi(
        db_session,
        filters=filters,
        status=ProtocolRunStatusEnum.RUNNING,
    )

    # Should only get RUNNING runs
    run_ids = [r.accession_id for r in running_runs]
    assert running_run.accession_id in run_ids
    assert completed_run.accession_id not in run_ids


@pytest.mark.asyncio
async def test_protocol_run_service_get_by_name(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test retrieving protocol run by protocol name.

    Demonstrates:
    - get_by_name() with join to protocol definition
    - Eager loading of relationships
    """
    from praxis.backend.utils.uuid import uuid7

    # Note: get_by_name searches by the protocol DEFINITION name, not the run name
    run = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            name="my_run_instance",
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        ),
    )

    # Retrieve by protocol definition name
    retrieved = await protocol_run_service.get_by_name(db_session, "test_protocol")

    assert retrieved is not None
    assert retrieved.accession_id == run.accession_id


@pytest.mark.asyncio
async def test_protocol_run_service_update_status_to_running(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test updating protocol run status from PENDING to RUNNING.

    Demonstrates:
    - Status transition logic
    - Automatic start_time setting
    - update_run_status() method
    """
    from praxis.backend.utils.uuid import uuid7

    # Create PENDING run
    run = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
            status=ProtocolRunStatusEnum.PENDING,
        ),
    )
    assert run.start_time is None

    # Update to RUNNING
    updated = await protocol_run_service.update_run_status(
        db_session,
        protocol_run_accession_id=run.accession_id,
        new_status=ProtocolRunStatusEnum.RUNNING,
    )

    # Verify status change and start_time was set
    assert updated is not None
    assert updated.status == ProtocolRunStatusEnum.RUNNING
    assert updated.start_time is not None
    assert isinstance(updated.start_time, datetime)


@pytest.mark.asyncio
async def test_protocol_run_service_update_status_to_completed(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test updating protocol run status to COMPLETED with output data.

    Demonstrates:
    - Terminal status handling (COMPLETED)
    - Automatic end_time setting
    - Duration calculation
    - Output data and final state storage
    """
    from praxis.backend.utils.uuid import uuid7

    # Create and start run
    run = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
            status=ProtocolRunStatusEnum.RUNNING,
        ),
    )
    start_time = run.start_time

    # Complete the run with output data
    output_data = {"result": "success", "measurements": [1.2, 3.4, 5.6]}
    final_state = {"tip_count": 0, "waste_volume_ul": 1500}

    updated = await protocol_run_service.update_run_status(
        db_session,
        protocol_run_accession_id=run.accession_id,
        new_status=ProtocolRunStatusEnum.COMPLETED,
        output_data_json=json.dumps(output_data),
        final_state_json=json.dumps(final_state),
    )

    # Verify completion
    assert updated is not None
    assert updated.status == ProtocolRunStatusEnum.COMPLETED
    assert updated.end_time is not None
    assert updated.start_time == start_time
    # Duration should be calculated
    assert updated.duration_ms is not None
    assert updated.duration_ms > 0
    # Output data should be stored
    assert updated.output_data_json == output_data
    assert updated.final_state_json == final_state


@pytest.mark.asyncio
async def test_protocol_run_service_update_status_to_failed(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test updating protocol run status to FAILED with error info.

    Demonstrates:
    - Error handling in status updates
    - Error info storage in output_data_json
    """
    from praxis.backend.utils.uuid import uuid7

    run = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
            status=ProtocolRunStatusEnum.RUNNING,
        ),
    )

    # Fail the run with error info
    error_info = {
        "error_type": "ValueError",
        "error_message": "Invalid volume specified",
        "traceback": "...",
    }

    updated = await protocol_run_service.update_run_status(
        db_session,
        protocol_run_accession_id=run.accession_id,
        new_status=ProtocolRunStatusEnum.FAILED,
        error_info=error_info,
    )

    # Verify failure
    assert updated is not None
    assert updated.status == ProtocolRunStatusEnum.FAILED
    assert updated.end_time is not None
    # Error info stored in output_data_json
    assert updated.output_data_json == error_info


@pytest.mark.asyncio
async def test_protocol_run_service_update_status_nonexistent(
    db_session: AsyncSession,
) -> None:
    """Test updating status of non-existent protocol run returns None.

    Demonstrates:
    - Error case handling
    - Returning None for not found
    """
    from praxis.backend.utils.uuid import uuid7

    non_existent_id = uuid7()
    result = await protocol_run_service.update_run_status(
        db_session,
        protocol_run_accession_id=non_existent_id,
        new_status=ProtocolRunStatusEnum.COMPLETED,
    )

    assert result is None


@pytest.mark.asyncio
async def test_log_function_call_start(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test logging the start of a function call.

    Demonstrates:
    - Helper function usage (not a service method)
    - Function call log creation
    - JSONB input args storage
    """
    from praxis.backend.utils.uuid import uuid7

    # Create protocol run first
    run = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        ),
    )

    # Log function call start
    input_args = {"volume": 50, "source": "A1", "dest": "B1"}
    call_log = await log_function_call_start(
        db_session,
        protocol_run_orm_accession_id=run.accession_id,
        function_definition_accession_id=protocol_definition.accession_id,
        sequence_in_run=0,
        input_args_json=json.dumps(input_args),
    )

    # Verify function call log created
    assert call_log is not None
    assert call_log.protocol_run_accession_id == run.accession_id
    assert call_log.function_protocol_definition_accession_id == protocol_definition.accession_id
    assert call_log.sequence_in_run == 0
    assert call_log.input_args_json == input_args
    assert call_log.status == FunctionCallStatusEnum.SUCCESS  # Default status
    assert call_log.start_time is not None


@pytest.mark.asyncio
async def test_log_function_call_with_parent(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test logging nested function calls (parent-child relationship).

    Demonstrates:
    - Parent-child function call relationships
    - Nested call tracking
    """
    from praxis.backend.utils.uuid import uuid7

    run = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        ),
    )

    # Log parent function call
    parent_call = await log_function_call_start(
        db_session,
        protocol_run_orm_accession_id=run.accession_id,
        function_definition_accession_id=protocol_definition.accession_id,
        sequence_in_run=0,
        input_args_json="{}",
    )

    # Log child function call
    child_call = await log_function_call_start(
        db_session,
        protocol_run_orm_accession_id=run.accession_id,
        function_definition_accession_id=protocol_definition.accession_id,
        sequence_in_run=1,
        input_args_json="{}",
        parent_function_call_log_accession_id=parent_call.accession_id,
    )

    # Verify parent-child relationship
    assert child_call.parent_function_call_log_accession_id == parent_call.accession_id


@pytest.mark.asyncio
async def test_log_function_call_end_success(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test logging successful function call completion.

    Demonstrates:
    - Function call completion logging
    - Return value storage
    - Status update
    """
    from praxis.backend.utils.uuid import uuid7

    run = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        ),
    )

    # Start function call
    call_log = await log_function_call_start(
        db_session,
        protocol_run_orm_accession_id=run.accession_id,
        function_definition_accession_id=protocol_definition.accession_id,
        sequence_in_run=0,
        input_args_json="{}",
    )

    # End function call successfully
    return_value = {"status": "success", "transferred_volume": 48.5}
    completed_call = await log_function_call_end(
        db_session,
        function_call_log_accession_id=call_log.accession_id,
        status=FunctionCallStatusEnum.SUCCESS,
        return_value_json=json.dumps(return_value),
        duration_ms=150.5,
    )

    # Verify completion
    assert completed_call is not None
    assert completed_call.status == FunctionCallStatusEnum.SUCCESS
    assert completed_call.end_time is not None
    assert completed_call.return_value_json == return_value
    assert completed_call.duration_ms == 150


@pytest.mark.asyncio
async def test_log_function_call_end_failure(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test logging failed function call.

    Demonstrates:
    - Error case handling in function call logging
    - Error message and traceback storage
    """
    from praxis.backend.utils.uuid import uuid7

    run = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        ),
    )

    # Start function call
    call_log = await log_function_call_start(
        db_session,
        protocol_run_orm_accession_id=run.accession_id,
        function_definition_accession_id=protocol_definition.accession_id,
        sequence_in_run=0,
        input_args_json="{}",
    )

    # End function call with failure
    error_message = "ValueError: Invalid volume"
    error_traceback = "Traceback...\n  File protocol.py, line 42..."
    failed_call = await log_function_call_end(
        db_session,
        function_call_log_accession_id=call_log.accession_id,
        status=FunctionCallStatusEnum.ERROR,
        error_message=error_message,
        error_traceback=error_traceback,
    )

    # Verify failure logged
    assert failed_call is not None
    assert failed_call.status == FunctionCallStatusEnum.ERROR
    assert failed_call.error_message_text == error_message
    assert failed_call.error_traceback_text == error_traceback


@pytest.mark.asyncio
async def test_log_function_call_end_nonexistent(
    db_session: AsyncSession,
) -> None:
    """Test logging end of non-existent function call returns None."""
    from praxis.backend.utils.uuid import uuid7

    non_existent_id = uuid7()
    result = await log_function_call_end(
        db_session,
        function_call_log_accession_id=non_existent_id,
        status=FunctionCallStatusEnum.SUCCESS,
    )

    assert result is None


@pytest.mark.asyncio
async def test_protocol_run_service_full_lifecycle(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test complete protocol run lifecycle from creation to completion.

    Demonstrates:
    - Full workflow integration
    - State transitions
    - Function call logging
    - Timing and duration calculations

    This is a comprehensive integration test showing how all pieces work together.
    """
    from praxis.backend.utils.uuid import uuid7

    # 1. Create PENDING run
    run = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            name="lifecycle_test",
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
            status=ProtocolRunStatusEnum.PENDING,
            input_parameters_json={"volume": 100},
            initial_state_json={"tip_count": 96},
        ),
    )
    assert run.status == ProtocolRunStatusEnum.PENDING
    assert run.start_time is None

    # 2. Start execution
    run = await protocol_run_service.update_run_status(
        db_session,
        protocol_run_accession_id=run.accession_id,
        new_status=ProtocolRunStatusEnum.RUNNING,
    )
    assert run.status == ProtocolRunStatusEnum.RUNNING
    assert run.start_time is not None
    start_time = run.start_time

    # 3. Log function calls
    call1 = await log_function_call_start(
        db_session,
        protocol_run_orm_accession_id=run.accession_id,
        function_definition_accession_id=protocol_definition.accession_id,
        sequence_in_run=0,
        input_args_json=json.dumps({"action": "aspirate"}),
    )
    await log_function_call_end(
        db_session,
        function_call_log_accession_id=call1.accession_id,
        status=FunctionCallStatusEnum.SUCCESS,
        return_value_json=json.dumps({"volume_aspirated": 98.5}),
    )

    call2 = await log_function_call_start(
        db_session,
        protocol_run_orm_accession_id=run.accession_id,
        function_definition_accession_id=protocol_definition.accession_id,
        sequence_in_run=1,
        input_args_json=json.dumps({"action": "dispense"}),
    )
    await log_function_call_end(
        db_session,
        function_call_log_accession_id=call2.accession_id,
        status=FunctionCallStatusEnum.SUCCESS,
        return_value_json=json.dumps({"volume_dispensed": 98.5}),
    )

    # 4. Complete execution
    run = await protocol_run_service.update_run_status(
        db_session,
        protocol_run_accession_id=run.accession_id,
        new_status=ProtocolRunStatusEnum.COMPLETED,
        output_data_json=json.dumps({"success": True, "total_transferred": 98.5}),
        final_state_json=json.dumps({"tip_count": 95}),
    )

    # 5. Verify complete lifecycle
    assert run.status == ProtocolRunStatusEnum.COMPLETED
    assert run.start_time == start_time
    assert run.end_time is not None
    assert run.end_time > run.start_time
    assert run.duration_ms is not None
    assert run.duration_ms > 0
    assert run.input_parameters_json == {"volume": 100}
    assert run.output_data_json == {"success": True, "total_transferred": 98.5}
    assert run.initial_state_json == {"tip_count": 96}
    assert run.final_state_json == {"tip_count": 95}

    # 6. Verify function calls were logged
    result = await db_session.execute(
        select(FunctionCallLog).where(
            FunctionCallLog.protocol_run_accession_id == run.accession_id,
        ).order_by(FunctionCallLog.sequence_in_run),
    )
    calls = result.scalars().all()
    assert len(calls) == 2
    assert calls[0].input_args_json == {"action": "aspirate"}
    assert calls[1].input_args_json == {"action": "dispense"}
    assert all(c.status == FunctionCallStatusEnum.SUCCESS for c in calls)


@pytest.mark.asyncio
async def test_protocol_run_service_update_status_handles_core_exception(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test that Core exceptions during status update are caught and handled.

    Demonstrates:
    - Connecting Core exception handling to Service layer
    - Verifying run transitions to FAILED instead of crashing
    """
    from praxis.backend.utils.errors import AssetAcquisitionError
    from praxis.backend.utils.uuid import uuid7

    # Create PENDING run
    run = await protocol_run_service.create(
        db_session,
        obj_in=ProtocolRunCreate(
            run_accession_id=uuid7(),
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
            status=ProtocolRunStatusEnum.PENDING,
        ),
    )

    # Mock scheduler to simulate "Not Enough Tips" error
    mock_scheduler = AsyncMock()
    mock_scheduler.analyze_protocol_requirements.return_value = []
    mock_scheduler.reserve_assets.side_effect = AssetAcquisitionError("Not Enough Tips")

    with patch("praxis.backend.api.global_dependencies.get_scheduler", return_value=mock_scheduler):
        # Update to RUNNING
        updated = await protocol_run_service.update_run_status(
            db_session,
            protocol_run_accession_id=run.accession_id,
            new_status=ProtocolRunStatusEnum.RUNNING,
        )

        # Verify status is FAILED (handled exception)
        assert updated is not None

        # Verify that Core integration was attempted
        if not mock_scheduler.analyze_protocol_requirements.called:
             pytest.fail("Scheduler.analyze_protocol_requirements was not called. Integration skipped.")

        assert updated.status == ProtocolRunStatusEnum.FAILED
        assert updated.output_data_json is not None
        assert updated.output_data_json["error"] == "Protocol execution failed to start"
        assert updated.output_data_json["details"] == "Not Enough Tips"
