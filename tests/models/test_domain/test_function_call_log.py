"""Unit tests for FunctionCallLogmodel."""
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.protocol import (
    FunctionCallLog,
    FunctionProtocolDefinition,
    ProtocolRun,
)
from praxis.backend.models.enums import FunctionCallStatusEnum


@pytest_asyncio.fixture
async def protocol_definition(db_session: AsyncSession) -> FunctionProtocolDefinition:
    """Create a FunctionProtocolDefinitionfor testing."""
    protocol = FunctionProtocolDefinition(
        name="test_protocol",
        fqn="test.protocols.test_protocol",
        version="1.0.0",
        is_top_level=True,
    )
    db_session.add(protocol)
    await db_session.flush()
    return protocol


@pytest_asyncio.fixture
async def protocol_run(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> ProtocolRun:
    """Create a ProtocolRunfor testing."""
    run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
    )
    db_session.add(run)
    await db_session.flush()
    return run


@pytest.mark.asyncio
async def test_function_call_log_orm_creation_minimal(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test creating FunctionCallLogwith minimal required fields."""
    now = datetime.now(timezone.utc)

    call_log = FunctionCallLog(
        name="test_call",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=0,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
    )
    call_log.start_time = now
    call_log.protocol_run = protocol_run
    call_log.executed_function_definition = protocol_definition
    db_session.add(call_log)
    await db_session.flush()

    # Verify creation with defaults
    assert call_log.accession_id is not None
    assert call_log.protocol_run_accession_id == protocol_run.accession_id
    assert call_log.sequence_in_run == 0
    assert call_log.function_protocol_definition_accession_id == protocol_definition.accession_id
    assert call_log.start_time is not None
    assert call_log.end_time is None
    assert call_log.parent_function_call_log_accession_id is None
    assert call_log.input_args_json is None
    assert call_log.return_value_json is None
    assert call_log.status == FunctionCallStatusEnum.UNKNOWN  # Default
    assert call_log.error_message_text is None
    assert call_log.error_traceback_text is None


@pytest.mark.asyncio
async def test_function_call_log_orm_creation_with_all_fields(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test creating FunctionCallLogwith all fields populated."""
    from datetime import timedelta
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(seconds=5)
    input_args = {"volume": 100, "source": "A1", "dest": "B1"}
    return_value = {"success": True, "transferred_volume": 98.5}

    call_log = FunctionCallLog(
        name="test_call",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=0,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
        input_args_json=input_args,
        return_value_json=return_value,
        status=FunctionCallStatusEnum.SUCCESS,
    )
    call_log.start_time = start_time
    call_log.end_time = end_time
    call_log.protocol_run = protocol_run
    call_log.executed_function_definition = protocol_definition
    db_session.add(call_log)
    await db_session.flush()

    # Verify all fields
    assert call_log.accession_id is not None
    assert call_log.start_time == start_time
    assert call_log.end_time == end_time
    assert call_log.input_args_json == input_args
    assert call_log.return_value_json == return_value
    assert call_log.status == FunctionCallStatusEnum.SUCCESS


@pytest.mark.asyncio
async def test_function_call_log_orm_persist_to_database(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test full persistence cycle for FunctionCallLog."""
    now = datetime.now(timezone.utc)

    call_log = FunctionCallLog(
        name="test_call",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=5,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
        status=FunctionCallStatusEnum.IN_PROGRESS,
    )
    call_log.start_time = now
    call_log.protocol_run = protocol_run
    call_log.executed_function_definition = protocol_definition
    db_session.add(call_log)
    await db_session.flush()

    # Query back
    result = await db_session.execute(
        select(FunctionCallLog).where(FunctionCallLog.accession_id == call_log.accession_id),
    )
    retrieved = result.scalars().first()

    # Verify persistence
    assert retrieved is not None
    assert retrieved.accession_id == call_log.accession_id
    assert retrieved.sequence_in_run == 5
    assert retrieved.status == FunctionCallStatusEnum.IN_PROGRESS


@pytest.mark.asyncio
async def test_function_call_log_orm_sequence_ordering(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test sequence_in_run for ordering function calls."""
    now = datetime.now(timezone.utc)

    # Create multiple calls with different sequences
    for seq in [0, 1, 2, 3, 4]:
        call_log = FunctionCallLog(
            name="test_call",
            protocol_run_accession_id=protocol_run.accession_id,
            sequence_in_run=seq,
            function_protocol_definition_accession_id=protocol_definition.accession_id,
        )
        call_log.start_time = now
        call_log.protocol_run = protocol_run
        call_log.executed_function_definition = protocol_definition
        db_session.add(call_log)

    await db_session.flush()

    # Query all calls for this run, ordered by sequence
    result = await db_session.execute(
        select(FunctionCallLog)
        .where(FunctionCallLog.protocol_run_accession_id == protocol_run.accession_id)
        .order_by(FunctionCallLog.sequence_in_run),
    )
    calls = result.scalars().all()

    # Verify ordering
    assert len(calls) >= 5
    sequences = [c.sequence_in_run for c in calls[:5]]
    assert sequences == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_function_call_log_orm_status_values(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test different status values for function calls."""
    now = datetime.now(timezone.utc)
    statuses = [
        FunctionCallStatusEnum.UNKNOWN,
        FunctionCallStatusEnum.PENDING,
        FunctionCallStatusEnum.IN_PROGRESS,
        FunctionCallStatusEnum.SUCCESS,
        FunctionCallStatusEnum.ERROR,
        FunctionCallStatusEnum.SKIPPED,
        FunctionCallStatusEnum.CANCELED,
    ]

    for idx, status in enumerate(statuses):
        call_log = FunctionCallLog(
            name="test_call",
            protocol_run_accession_id=protocol_run.accession_id,
            sequence_in_run=idx,
            function_protocol_definition_accession_id=protocol_definition.accession_id,
            status=status,
        )
        call_log.start_time = now
        call_log.protocol_run = protocol_run
        call_log.executed_function_definition = protocol_definition
        db_session.add(call_log)

    await db_session.flush()

    # Verify statuses
    result = await db_session.execute(
        select(FunctionCallLog)
        .where(FunctionCallLog.protocol_run_accession_id == protocol_run.accession_id)
        .order_by(FunctionCallLog.sequence_in_run),
    )
    calls = result.scalars().all()

    for idx, status in enumerate(statuses):
        assert calls[idx].status == status


@pytest.mark.asyncio
async def test_function_call_log_orm_input_args_jsonb(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test JSONB input_args_json field."""
    now = datetime.now(timezone.utc)
    input_args = {
        "volume_ul": 50,
        "source_well": "A1",
        "dest_well": "B1",
        "aspirate_speed": 100,
        "dispense_speed": 150,
        "mix_cycles": 3,
        "tip_type": "standard",
        "nested": {"key": "value", "items": [1, 2, 3]},
    }

    call_log = FunctionCallLog(
        name="test_call",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=0,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
        input_args_json=input_args,
    )
    call_log.start_time = now
    call_log.protocol_run = protocol_run
    call_log.executed_function_definition = protocol_definition
    db_session.add(call_log)
    await db_session.flush()

    # Verify JSONB storage and retrieval
    assert call_log.input_args_json == input_args
    assert call_log.input_args_json["volume_ul"] == 50
    assert call_log.input_args_json["nested"]["items"] == [1, 2, 3]


@pytest.mark.asyncio
async def test_function_call_log_orm_return_value_jsonb(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test JSONB return_value_json field."""
    now = datetime.now(timezone.utc)
    return_value = {
        "success": True,
        "actual_volume": 49.8,
        "errors": [],
        "warnings": ["Tip slightly bent"],
        "measurements": [1.2, 3.4, 5.6],
    }

    call_log = FunctionCallLog(
        name="test_call",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=0,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
        return_value_json=return_value,
    )
    call_log.start_time = now
    call_log.protocol_run = protocol_run
    call_log.executed_function_definition = protocol_definition
    db_session.add(call_log)
    await db_session.flush()

    # Verify JSONB storage
    assert call_log.return_value_json == return_value
    assert call_log.return_value_json["actual_volume"] == 49.8
    assert call_log.return_value_json["measurements"] == [1.2, 3.4, 5.6]


@pytest.mark.asyncio
async def test_function_call_log_orm_error_fields(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test error_message_text and error_traceback_text fields."""
    now = datetime.now(timezone.utc)
    error_message = "ValueError: Invalid volume specified"
    error_traceback = """Traceback (most recent call last):
  File "protocol.py", line 42, in transfer
    validate_volume(volume)
ValueError: Invalid volume specified"""

    call_log = FunctionCallLog(
        name="test_call",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=0,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
        status=FunctionCallStatusEnum.ERROR,
        error_message_text=error_message,
        error_traceback_text=error_traceback,
    )
    call_log.start_time = now
    call_log.protocol_run = protocol_run
    call_log.executed_function_definition = protocol_definition
    db_session.add(call_log)
    await db_session.flush()

    # Verify error storage
    assert call_log.error_message_text == error_message
    assert call_log.error_traceback_text == error_traceback
    assert "ValueError" in call_log.error_message_text
    assert "protocol.py" in call_log.error_traceback_text


@pytest.mark.asyncio
async def test_function_call_log_orm_nested_calls(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test parent-child relationship for nested function calls."""
    now = datetime.now(timezone.utc)

    # Create parent call
    parent_call = FunctionCallLog(
        name="parent_call",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=0,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
    )
    parent_call.start_time = now
    parent_call.protocol_run = protocol_run
    parent_call.executed_function_definition = protocol_definition
    db_session.add(parent_call)
    await db_session.flush()

    # Create child call
    child_call = FunctionCallLog(
        name="child_call",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=1,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
        parent_function_call_log_accession_id=parent_call.accession_id,
    )
    child_call.start_time = now
    child_call.protocol_run = protocol_run
    child_call.executed_function_definition = protocol_definition
    db_session.add(child_call)
    await db_session.flush()

    # Verify parent-child relationship
    assert child_call.parent_function_call_log_accession_id == parent_call.accession_id
    assert parent_call.parent_function_call_log_accession_id is None


@pytest.mark.asyncio
async def test_function_call_log_orm_timing(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test start_time and end_time fields."""
    from datetime import timedelta
    start_time = datetime.now(timezone.utc)
    end_time = start_time + timedelta(seconds=10)

    call_log = FunctionCallLog(
        name="test_call",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=0,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
        status=FunctionCallStatusEnum.SUCCESS,
    )
    call_log.start_time = start_time
    call_log.end_time = end_time
    call_log.protocol_run = protocol_run
    call_log.executed_function_definition = protocol_definition
    db_session.add(call_log)
    await db_session.flush()

    assert call_log.start_time == start_time
    assert call_log.end_time == end_time
    # Duration should be 10 seconds
    duration = (call_log.end_time - call_log.start_time).total_seconds()
    assert duration == 10


@pytest.mark.asyncio
async def test_function_call_log_orm_query_by_protocol_run(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test querying all function calls for a protocol run."""
    now = datetime.now(timezone.utc)

    # Create multiple calls for the same run
    for i in range(5):
        call_log = FunctionCallLog(
            name="test_call",
            protocol_run_accession_id=protocol_run.accession_id,
            sequence_in_run=i,
            function_protocol_definition_accession_id=protocol_definition.accession_id,
        )
        call_log.start_time = now
        call_log.protocol_run = protocol_run
        call_log.executed_function_definition = protocol_definition
        db_session.add(call_log)

    await db_session.flush()

    # Query all calls for this run
    result = await db_session.execute(
        select(FunctionCallLog).where(
            FunctionCallLog.protocol_run_accession_id == protocol_run.accession_id,
        ),
    )
    calls = result.scalars().all()

    # Should find at least 5 calls
    assert len(calls) >= 5


@pytest.mark.asyncio
async def test_function_call_log_orm_query_by_status(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test querying function calls by status."""
    now = datetime.now(timezone.utc)

    # Create calls with different statuses
    success_call = FunctionCallLog(
        name="success_call",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=0,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
        status=FunctionCallStatusEnum.SUCCESS,
    )
    success_call.start_time = now
    success_call.protocol_run = protocol_run
    success_call.executed_function_definition = protocol_definition

    failed_call = FunctionCallLog(
        name="failed_call",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=1,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
        status=FunctionCallStatusEnum.ERROR,
    )
    failed_call.start_time = now
    failed_call.protocol_run = protocol_run
    failed_call.executed_function_definition = protocol_definition

    db_session.add(success_call)
    db_session.add(failed_call)
    await db_session.flush()

    # Query only failed calls
    result = await db_session.execute(
        select(FunctionCallLog).where(
            FunctionCallLog.status == FunctionCallStatusEnum.ERROR,
        ),
    )
    failed_calls = result.scalars().all()

    # Should find at least our failed call
    assert len(failed_calls) >= 1
    assert any(c.sequence_in_run == 1 for c in failed_calls)


@pytest.mark.asyncio
async def test_function_call_log_orm_repr(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test string representation of FunctionCallLog."""
    now = datetime.now(timezone.utc)

    call_log = FunctionCallLog(
        name="test_call",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=42,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
        status=FunctionCallStatusEnum.SUCCESS,
    )
    call_log.start_time = now

    repr_str = repr(call_log)
    assert "FunctionCallLog" in repr_str
    assert str(call_log.accession_id) in repr_str
    assert str(protocol_run.accession_id) in repr_str
    assert "42" in repr_str
    assert "success" in repr_str
