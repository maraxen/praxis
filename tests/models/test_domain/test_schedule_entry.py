"""Unit tests for ScheduleEntrymodel."""
from collections.abc import Callable
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.protocol import (
    FunctionProtocolDefinition,
    ProtocolRun,
)
from praxis.backend.models.domain.protocol_source import (
    FileSystemProtocolSource,
    ProtocolSourceRepository,
)
from praxis.backend.models.domain.schedule import ScheduleEntry
from praxis.backend.models.enums import ScheduleStatusEnum


@pytest_asyncio.fixture
async def source_repository(db_session: AsyncSession) -> ProtocolSourceRepository:
    """Create a ProtocolSourceRepositoryfor testing."""
    repo = ProtocolSourceRepository(
        name="test-repo",
        git_url="https://github.com/test/repo.git",
    )
    db_session.add(repo)
    await db_session.flush()
    return repo


@pytest_asyncio.fixture
async def file_system_source(db_session: AsyncSession) -> FileSystemProtocolSource:
    """Create a FileSystemProtocolSourcefor testing."""
    source = FileSystemProtocolSource(
        name="test-fs-source",
        base_path="/tmp/protocols",
    )
    db_session.add(source)
    await db_session.flush()
    return source


@pytest_asyncio.fixture
async def protocol_definition(
    db_session: AsyncSession,
    source_repository: ProtocolSourceRepository,
    file_system_source: FileSystemProtocolSource,
) -> FunctionProtocolDefinition:
    """Create a FunctionProtocolDefinitionfor testing."""
    protocol = FunctionProtocolDefinition(
        name="test_protocol",
        fqn="test.protocols.test_protocol",
        version="1.0.0",
        is_top_level=True,
        source_repository_accession_id=source_repository.accession_id,
        file_system_source_accession_id=file_system_source.accession_id,
    )
    protocol.source_repository = source_repository
    protocol.file_system_source = file_system_source
    db_session.add(protocol)
    await db_session.flush()
    return protocol


@pytest_asyncio.fixture
def protocol_run_factory(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> Callable[[], ProtocolRun]:
    """Create a ProtocolRunfactory for testing."""

    async def _factory() -> ProtocolRun:
        run = ProtocolRun(
            name="test_protocol_run",
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        )
        db_session.add(run)
        await db_session.flush()
        return run

    return _factory


@pytest.mark.asyncio
async def test_schedule_entry_orm_creation_minimal(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test creating ScheduleEntrywith minimal required fields."""
    protocol_run = await protocol_run_factory()
    entry = ScheduleEntry(
        protocol_run=protocol_run,
        name="test_schedule_entry",
        scheduled_at=datetime.now(timezone.utc),
        asset_analysis_completed_at=None,
        assets_reserved_at=None,
        execution_started_at=None,
        execution_completed_at=None,
    )

    db_session.add(entry)
    await db_session.flush()

    assert entry.accession_id is not None
    assert entry.protocol_run_accession_id == protocol_run.accession_id
    assert entry.status == ScheduleStatusEnum.QUEUED
    assert entry.priority == 1
    assert entry.scheduled_at is not None
    assert isinstance(entry.scheduled_at, datetime)
    assert entry.asset_analysis_completed_at is None
    assert entry.assets_reserved_at is None
    assert entry.execution_started_at is None
    assert entry.execution_completed_at is None
    assert entry.required_asset_count == 0
    assert entry.retry_count == 0
    assert entry.max_retries == 3
    assert entry.last_error_message is None


@pytest.mark.asyncio
async def test_schedule_entry_orm_creation_with_all_fields(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test creating ScheduleEntrywith all fields populated."""
    protocol_run = await protocol_run_factory()
    now = datetime.now(timezone.utc)
    asset_reqs = {"pipette": {"type": "p1000", "count": 1}}
    user_params = {"param1": "value1"}
    initial_state = {"state1": "initial"}

    entry = ScheduleEntry(
        protocol_run=protocol_run,
        name="test_schedule_entry_all_fields",
        status=ScheduleStatusEnum.READY_TO_EXECUTE,
        priority=10,
        scheduled_at=now,
        asset_analysis_completed_at=now,
        assets_reserved_at=now,
        execution_started_at=now,
        execution_completed_at=now,
        asset_requirements_json=asset_reqs,
        required_asset_count=1,
        estimated_duration_ms=5000,
        celery_task_id="test-task-id",
        celery_queue_name="test-queue",
        retry_count=1,
        max_retries=5,
        last_error_message="A test error",
        user_params_json=user_params,
        initial_state_json=initial_state,
    )

    db_session.add(entry)
    await db_session.flush()

    assert entry.accession_id is not None
    assert entry.protocol_run_accession_id == protocol_run.accession_id
    assert entry.status == ScheduleStatusEnum.READY_TO_EXECUTE
    assert entry.priority == 10
    assert entry.scheduled_at == now
    assert entry.asset_analysis_completed_at == now
    assert entry.assets_reserved_at == now
    assert entry.execution_started_at == now
    assert entry.execution_completed_at == now
    assert entry.asset_requirements_json == asset_reqs
    assert entry.required_asset_count == 1
    assert entry.estimated_duration_ms == 5000
    assert entry.celery_task_id == "test-task-id"
    assert entry.celery_queue_name == "test-queue"
    assert entry.retry_count == 1
    assert entry.max_retries == 5
    assert entry.last_error_message == "A test error"
    assert entry.user_params_json == user_params
    assert entry.initial_state_json == initial_state


@pytest.mark.asyncio
async def test_schedule_entry_orm_persist_to_database(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test full persistence cycle for ScheduleEntry."""
    protocol_run = await protocol_run_factory()
    entry = ScheduleEntry(
        protocol_run=protocol_run,
        name="test_schedule_entry_persist",
        priority=5,
        scheduled_at=datetime.now(timezone.utc),
        asset_analysis_completed_at=None,
        assets_reserved_at=None,
        execution_started_at=None,
        execution_completed_at=None,
    )
    db_session.add(entry)
    await db_session.commit()

    result = await db_session.execute(
        select(ScheduleEntry).where(ScheduleEntry.accession_id == entry.accession_id),
    )
    retrieved_entry = result.scalar_one()

    assert retrieved_entry is not None
    assert retrieved_entry.accession_id == entry.accession_id
    assert retrieved_entry.priority == 5
    assert retrieved_entry.status == ScheduleStatusEnum.QUEUED


@pytest.mark.asyncio
async def test_schedule_entry_orm_status_transitions(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test different status values for schedule entries."""
    for i, status in enumerate(ScheduleStatusEnum):
        protocol_run = await protocol_run_factory()
        entry = ScheduleEntry(
            protocol_run=protocol_run,
            name=f"test_schedule_entry_{i}",
            status=status,
            scheduled_at=datetime.now(timezone.utc),
            asset_analysis_completed_at=None,
            assets_reserved_at=None,
            execution_started_at=None,
            execution_completed_at=None,
        )
        db_session.add(entry)

    await db_session.flush()

    for status in ScheduleStatusEnum:
        result = await db_session.execute(
            select(ScheduleEntry).where(ScheduleEntry.status == status),
        )
        entry = result.scalar_one_or_none()
        assert entry is not None
        assert entry.status == status


@pytest.mark.asyncio
async def test_schedule_entry_orm_priority_ordering(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test priority field for scheduling order."""
    priorities = [5, 1, 10]
    for i, p in enumerate(priorities):
        protocol_run = await protocol_run_factory()
        entry = ScheduleEntry(
            protocol_run=protocol_run,
            name=f"test_schedule_entry_{i}",
            priority=p,
            scheduled_at=datetime.now(timezone.utc),
            asset_analysis_completed_at=None,
            assets_reserved_at=None,
            execution_started_at=None,
            execution_completed_at=None,
        )
        db_session.add(entry)

    await db_session.flush()

    result = await db_session.execute(
        select(ScheduleEntry).order_by(ScheduleEntry.priority.desc()),
    )
    entries = result.scalars().all()

    assert [e.priority for e in entries] == sorted(priorities, reverse=True)


@pytest.mark.asyncio
async def test_schedule_entry_orm_timestamp_fields(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test timestamp fields for tracking execution stages."""
    protocol_run = await protocol_run_factory()
    now = datetime.now(timezone.utc)
    entry = ScheduleEntry(
        protocol_run=protocol_run,
        name="test_schedule_entry_timestamps",
        scheduled_at=now,
        asset_analysis_completed_at=now,
        assets_reserved_at=now,
        execution_started_at=now,
        execution_completed_at=now,
    )
    db_session.add(entry)
    await db_session.flush()

    assert entry.scheduled_at == now
    assert entry.asset_analysis_completed_at == now
    assert entry.assets_reserved_at == now
    assert entry.execution_started_at == now
    assert entry.execution_completed_at == now


@pytest.mark.asyncio
async def test_schedule_entry_orm_asset_requirements_jsonb(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test JSONB asset_requirements_json field."""
    protocol_run = await protocol_run_factory()
    asset_reqs = {
        "pipettes": [{"name": "p1000", "count": 1}],
        "plates": {"type": "96-well", "count": 2},
    }
    entry = ScheduleEntry(
        protocol_run=protocol_run,
        name="test_schedule_entry_jsonb",
        asset_requirements_json=asset_reqs,
        scheduled_at=datetime.now(timezone.utc),
        asset_analysis_completed_at=None,
        assets_reserved_at=None,
        execution_started_at=None,
        execution_completed_at=None,
    )
    db_session.add(entry)
    await db_session.flush()

    assert entry.asset_requirements_json["pipettes"][0]["name"] == "p1000"
    assert entry.asset_requirements_json["plates"]["count"] == 2


@pytest.mark.asyncio
async def test_schedule_entry_orm_celery_integration(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test Celery task tracking fields."""
    protocol_run = await protocol_run_factory()
    entry = ScheduleEntry(
        protocol_run=protocol_run,
        name="test_schedule_entry_celery",
        celery_task_id="test-task-id",
        celery_queue_name="test-queue",
        scheduled_at=datetime.now(timezone.utc),
        asset_analysis_completed_at=None,
        assets_reserved_at=None,
        execution_started_at=None,
        execution_completed_at=None,
    )
    db_session.add(entry)
    await db_session.flush()

    assert entry.celery_task_id == "test-task-id"
    assert entry.celery_queue_name == "test-queue"


@pytest.mark.asyncio
async def test_schedule_entry_orm_retry_logic(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test retry_count and max_retries fields."""
    protocol_run = await protocol_run_factory()
    entry = ScheduleEntry(
        protocol_run=protocol_run,
        name="test_schedule_entry_retry",
        retry_count=2,
        max_retries=5,
        last_error_message="Initial error",
        scheduled_at=datetime.now(timezone.utc),
        asset_analysis_completed_at=None,
        assets_reserved_at=None,
        execution_started_at=None,
        execution_completed_at=None,
    )
    db_session.add(entry)
    await db_session.flush()

    assert entry.retry_count == 2
    assert entry.max_retries == 5
    assert entry.last_error_message == "Initial error"


@pytest.mark.asyncio
async def test_schedule_entry_orm_user_params_jsonb(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test JSONB user_params_json and initial_state_json fields."""
    protocol_run = await protocol_run_factory()
    user_params = {"param1": "value1", "nested": {"p2": 2}}
    initial_state = {"state1": "initial", "nested": {"s2": "s2_val"}}
    entry = ScheduleEntry(
        protocol_run=protocol_run,
        name="test_schedule_entry_user_params",
        user_params_json=user_params,
        initial_state_json=initial_state,
        scheduled_at=datetime.now(timezone.utc),
        asset_analysis_completed_at=None,
        assets_reserved_at=None,
        execution_started_at=None,
        execution_completed_at=None,
    )
    db_session.add(entry)
    await db_session.flush()

    assert entry.user_params_json["nested"]["p2"] == 2
    assert entry.initial_state_json["nested"]["s2"] == "s2_val"


@pytest.mark.asyncio
async def test_schedule_entry_orm_relationship_to_protocol_run(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test relationship between ScheduleEntryand ProtocolRun."""
    protocol_run = await protocol_run_factory()
    entry = ScheduleEntry(
        protocol_run=protocol_run,
        name="test_schedule_entry_relationship",
        scheduled_at=datetime.now(timezone.utc),
        asset_analysis_completed_at=None,
        assets_reserved_at=None,
        execution_started_at=None,
        execution_completed_at=None,
    )
    db_session.add(entry)
    await db_session.flush()

    assert entry.protocol_run_accession_id == protocol_run.accession_id
    assert entry.protocol_run == protocol_run
    await db_session.refresh(protocol_run, ["schedule_entries"])
    assert entry in protocol_run.schedule_entries


@pytest.mark.asyncio
async def test_schedule_entry_orm_query_by_status(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test querying schedule entries by status."""
    statuses = [ScheduleStatusEnum.QUEUED, ScheduleStatusEnum.READY_TO_EXECUTE, ScheduleStatusEnum.QUEUED]
    for i, status in enumerate(statuses):
        protocol_run = await protocol_run_factory()
        entry = ScheduleEntry(
            protocol_run=protocol_run,
            name=f"test_schedule_entry_{i}",
            status=status,
            scheduled_at=datetime.now(timezone.utc),
            asset_analysis_completed_at=None,
            assets_reserved_at=None,
            execution_started_at=None,
            execution_completed_at=None,
        )
        db_session.add(entry)
    await db_session.flush()

    result = await db_session.execute(
        select(ScheduleEntry).where(ScheduleEntry.status == ScheduleStatusEnum.QUEUED),
    )
    queued_entries = result.scalars().all()
    assert len(queued_entries) == 2

    result = await db_session.execute(
        select(ScheduleEntry).where(ScheduleEntry.status == ScheduleStatusEnum.READY_TO_EXECUTE),
    )
    ready_entries = result.scalars().all()
    assert len(ready_entries) == 1


@pytest.mark.asyncio
async def test_schedule_entry_orm_query_ready_entries(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
) -> None:
    """Test querying ready-to-execute entries."""
    entries_data = [
        {"status": ScheduleStatusEnum.READY_TO_EXECUTE, "priority": 10},
        {"status": ScheduleStatusEnum.QUEUED, "priority": 5},
        {"status": ScheduleStatusEnum.READY_TO_EXECUTE, "priority": 20},
    ]
    for i, data in enumerate(entries_data):
        protocol_run = await protocol_run_factory()
        entry = ScheduleEntry(
            protocol_run=protocol_run,
            name=f"test_schedule_entry_{i}",
            status=data["status"],
            priority=data["priority"],
            scheduled_at=datetime.now(timezone.utc),
            asset_analysis_completed_at=None,
            assets_reserved_at=None,
            execution_started_at=None,
            execution_completed_at=None,
        )
        db_session.add(entry)
    await db_session.flush()

    result = await db_session.execute(
        select(ScheduleEntry)
        .where(ScheduleEntry.status == ScheduleStatusEnum.READY_TO_EXECUTE)
        .order_by(ScheduleEntry.priority.desc()),
    )
    ready_entries = result.scalars().all()

    assert len(ready_entries) == 2
    assert ready_entries[0].priority == 20
    assert ready_entries[1].priority == 10
