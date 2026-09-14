"""Unit tests for ProtocolRunmodel."""
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.protocol import (
    FunctionProtocolDefinition,
    ProtocolRun,
)
from praxis.backend.models.enums import ProtocolRunStatusEnum


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


@pytest.mark.asyncio
async def test_protocol_run_creation_minimal(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test creating ProtocolRunwith minimal required fields."""
    run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
    )
    db_session.add(run)
    await db_session.flush()

    # Verify creation with defaults
    assert run.accession_id is not None
    assert run.top_level_protocol_definition_accession_id == protocol_definition.accession_id
    assert run.status == ProtocolRunStatusEnum.PENDING  # Default
    assert run.start_time is None
    assert run.end_time is None
    assert run.input_parameters_json is None
    assert run.resolved_assets_json is None
    assert run.output_data_json is None
    assert run.initial_state_json is None
    assert run.final_state_json is None
    assert run.data_directory_path is None
    assert run.created_by_user is None
    assert run.previous_accession_id is None
    assert run.duration_ms is None


@pytest.mark.asyncio
async def test_protocol_run_creation_with_all_fields(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test creating ProtocolRunwith all fields populated."""
    now = datetime.now(timezone.utc)
    input_params = {"volume": 50, "temperature": 37}
    resolved_assets = {"plate": "plate_123", "machine": "star_001"}
    output_data = {"result": "success", "measurements": [1.2, 3.4, 5.6]}
    initial_state = {"deck_layout": "config_a"}
    final_state = {"deck_layout": "config_b", "tips_used": 96}
    user_info = {"user_id": "user123", "username": "testuser"}

    run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        status=ProtocolRunStatusEnum.RUNNING,
        start_time=now,
        input_parameters_json=input_params,
        resolved_assets_json=resolved_assets,
        output_data_json=output_data,
        initial_state_json=initial_state,
        final_state_json=final_state,
        data_directory_path="/data/runs/run_123",
        created_by_user=user_info,
        duration_ms=45000,
    )
    db_session.add(run)
    await db_session.flush()

    # Verify all fields
    assert run.accession_id is not None
    assert run.status == ProtocolRunStatusEnum.RUNNING
    assert run.start_time == now
    assert run.input_parameters_json == input_params
    assert run.resolved_assets_json == resolved_assets
    assert run.output_data_json == output_data
    assert run.initial_state_json == initial_state
    assert run.final_state_json == final_state
    assert run.data_directory_path == "/data/runs/run_123"
    assert run.created_by_user == user_info
    assert run.duration_ms == 45000


@pytest.mark.asyncio
async def test_protocol_run_persist_to_database(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test full persistence cycle for ProtocolRun."""
    run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        status=ProtocolRunStatusEnum.COMPLETED,
        input_parameters_json={"test": "value"},
    )
    db_session.add(run)
    await db_session.flush()

    run_id = run.accession_id

    # Query back
    result = await db_session.execute(
        select(ProtocolRun).where(ProtocolRun.accession_id == run_id),
    )
    retrieved = result.scalars().first()

    # Verify persistence
    assert retrieved is not None
    assert retrieved.accession_id == run_id
    assert retrieved.status == ProtocolRunStatusEnum.COMPLETED
    assert retrieved.input_parameters_json == {"test": "value"}


@pytest.mark.asyncio
async def test_protocol_run_status_transitions(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test different status values for protocol runs."""
    statuses = [
        (ProtocolRunStatusEnum.PENDING, "pending_run"),
        (ProtocolRunStatusEnum.QUEUED, "queued_run"),
        (ProtocolRunStatusEnum.RUNNING, "running_run"),
        (ProtocolRunStatusEnum.COMPLETED, "completed_run"),
        (ProtocolRunStatusEnum.FAILED, "failed_run"),
        (ProtocolRunStatusEnum.CANCELLED, "cancelled_run"),
        (ProtocolRunStatusEnum.PAUSED, "paused_run"),
    ]

    for status, name in statuses:
        run = ProtocolRun(
            name=name,
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
            status=status,
        )
        db_session.add(run)
        await db_session.flush()

        # Verify status
        assert run.status == status


@pytest.mark.asyncio
async def test_protocol_run_timing_fields(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test start_time, end_time, and duration_ms fields."""
    from datetime import timedelta
    start = datetime.now(timezone.utc)
    # Simulate 30 second execution
    end = start + timedelta(seconds=30)

    run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        status=ProtocolRunStatusEnum.COMPLETED,
        start_time=start,
        end_time=end,
        duration_ms=30000,  # 30 seconds
    )
    db_session.add(run)
    await db_session.flush()

    assert run.start_time == start
    assert run.end_time == end
    assert run.duration_ms == 30000


@pytest.mark.asyncio
async def test_protocol_run_input_parameters_jsonb(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test JSONB input_parameters_json field."""
    input_params = {
        "volume_ul": 100,
        "temperature_c": 37.5,
        "mix_cycles": 3,
        "aspirate_speed": "normal",
        "plate_ids": ["plate_001", "plate_002"],
        "nested": {"key": "value", "count": 42},
    }

    run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        input_parameters_json=input_params,
    )
    db_session.add(run)
    await db_session.flush()

    # Verify JSONB storage and retrieval
    assert run.input_parameters_json == input_params
    assert run.input_parameters_json["volume_ul"] == 100
    assert run.input_parameters_json["plate_ids"] == ["plate_001", "plate_002"]
    assert run.input_parameters_json["nested"]["count"] == 42


@pytest.mark.asyncio
async def test_protocol_run_resolved_assets_jsonb(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test JSONB resolved_assets_json field."""
    resolved_assets = {
        "liquid_handler": {"id": "star_001", "type": "HAMILTON_STAR"},
        "source_plate": {"id": "plate_123", "type": "96_wellplate"},
        "tip_rack": {"id": "tips_001", "position": "A1"},
    }

    run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        resolved_assets_json=resolved_assets,
    )
    db_session.add(run)
    await db_session.flush()

    # Verify JSONB storage
    assert run.resolved_assets_json == resolved_assets
    assert run.resolved_assets_json["liquid_handler"]["id"] == "star_001"


@pytest.mark.asyncio
async def test_protocol_run_output_data_jsonb(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test JSONB output_data_json field."""
    output_data = {
        "status": "success",
        "measurements": [1.2, 3.4, 5.6, 7.8],
        "metadata": {"run_id": "abc123", "operator": "user123"},
    }

    run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        output_data_json=output_data,
    )
    db_session.add(run)
    await db_session.flush()

    # Verify JSONB storage
    assert run.output_data_json == output_data
    assert run.output_data_json["measurements"] == [1.2, 3.4, 5.6, 7.8]


@pytest.mark.asyncio
async def test_protocol_run_state_jsonb(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test JSONB initial_state_json and final_state_json fields."""
    initial_state = {
        "deck_layout": "config_a",
        "tip_count": 96,
        "plates": ["plate_001"],
    }
    final_state = {
        "deck_layout": "config_b",
        "tip_count": 0,
        "plates": ["plate_001", "plate_002"],
        "waste_volume_ul": 1500,
    }

    run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        initial_state_json=initial_state,
        final_state_json=final_state,
    )
    db_session.add(run)
    await db_session.flush()

    # Verify state storage
    assert run.initial_state_json == initial_state
    assert run.final_state_json == final_state
    assert run.initial_state_json["tip_count"] == 96
    assert run.final_state_json["tip_count"] == 0


@pytest.mark.asyncio
async def test_protocol_run_data_directory_path(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test data_directory_path field for output storage."""
    run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        data_directory_path="/data/protocol_runs/2024/11/run_abc123",
    )
    db_session.add(run)
    await db_session.flush()

    assert run.data_directory_path == "/data/protocol_runs/2024/11/run_abc123"


@pytest.mark.asyncio
async def test_protocol_run_created_by_user_jsonb(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test JSONB created_by_user field."""
    user_info = {
        "user_id": "user_789",
        "username": "scientist_alice",
        "email": "alice@example.com",
        "role": "operator",
    }

    run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        created_by_user=user_info,
    )
    db_session.add(run)
    await db_session.flush()

    # Verify user info storage
    assert run.created_by_user == user_info
    assert run.created_by_user["username"] == "scientist_alice"


@pytest.mark.asyncio
async def test_protocol_run_continuation_chain(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test previous_accession_id for protocol run continuations."""
    # Create first run
    run1 = ProtocolRun(
        name="run1",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        status=ProtocolRunStatusEnum.COMPLETED,
    )
    db_session.add(run1)
    await db_session.flush()
    run1_id = run1.accession_id

    # Create continuation run
    run2 = ProtocolRun(
        name="run2",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        status=ProtocolRunStatusEnum.RUNNING,
        previous_run=run1,
    )
    db_session.add(run2)
    await db_session.flush()

    # Verify continuation link
    assert run2.previous_accession_id == run1_id
    assert run1.previous_accession_id is None


@pytest.mark.asyncio
async def test_protocol_run_query_by_status(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test querying protocol runs by status."""
    # Create runs with different statuses
    running_run = ProtocolRun(
        name="running_query_test",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        status=ProtocolRunStatusEnum.RUNNING,
    )
    completed_run = ProtocolRun(
        name="completed_query_test",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        status=ProtocolRunStatusEnum.COMPLETED,
    )
    db_session.add(running_run)
    db_session.add(completed_run)
    await db_session.flush()

    # Query for running protocols
    result = await db_session.execute(
        select(ProtocolRun).where(
            ProtocolRun.status == ProtocolRunStatusEnum.RUNNING,
        ),
    )
    running_runs = result.scalars().all()

    # Should find at least our running run
    assert len(running_runs) >= 1
    assert any(r.name == "running_query_test" for r in running_runs)


@pytest.mark.asyncio
async def test_protocol_run_query_by_protocol(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test querying all runs for a specific protocol."""
    # Create multiple runs for the same protocol
    run1 = ProtocolRun(
        name="protocol_query_run1",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
    )
    run2 = ProtocolRun(
        name="protocol_query_run2",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
    )
    db_session.add(run1)
    db_session.add(run2)
    await db_session.flush()

    # Query all runs for this protocol
    result = await db_session.execute(
        select(ProtocolRun).where(
            ProtocolRun.top_level_protocol_definition_accession_id
            == protocol_definition.accession_id,
        ),
    )
    protocol_runs = result.scalars().all()

    # Should find at least our 2 runs
    assert len(protocol_runs) >= 2
    names = [r.name for r in protocol_runs]
    assert "protocol_query_run1" in names
    assert "protocol_query_run2" in names


@pytest.mark.asyncio
async def test_protocol_run_repr(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test string representation of ProtocolRun."""
    run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        status=ProtocolRunStatusEnum.RUNNING,
    )
    db_session.add(run)
    await db_session.flush()
    run_id = run.accession_id

    repr_str = repr(run)
    assert "ProtocolRun" in repr_str
    assert str(run_id) in repr_str
    assert "running" in repr_str
