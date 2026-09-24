"""Unit tests for ScheduleHistory model.

Tests for the audit trail model tracking schedule status changes and events.
"""
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

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
from praxis.backend.models.domain.schedule import (
    ScheduleEntry,
    ScheduleHistory,
)
from praxis.backend.models.enums import (
    ScheduleHistoryEventEnum,
    ScheduleHistoryEventTriggerEnum,
    ScheduleStatusEnum,
)
from praxis.backend.utils.uuid import uuid7


@pytest_asyncio.fixture
async def source_repository(db_session: AsyncSession) -> ProtocolSourceRepository:
    """Create a ProtocolSourceRepository for testing."""
    repo = ProtocolSourceRepository(
        name="test-repo",
        git_url="https://github.com/test/repo.git",
    )
    db_session.add(repo)
    await db_session.flush()
    return repo


@pytest_asyncio.fixture
async def file_system_source(db_session: AsyncSession) -> FileSystemProtocolSource:
    """Create a FileSystemProtocolSource for testing."""
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
    """Create a FunctionProtocolDefinition for testing."""
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
def schedule_entry_factory(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> Callable[[], ScheduleEntry]:
    """Create a ScheduleEntry factory for testing."""

    async def _factory() -> ScheduleEntry:
        # Create protocol run first
        run = ProtocolRun(
            name="test_protocol_run",
            top_level_protocol_definition_accession_id=protocol_definition.accession_id,
        )
        db_session.add(run)
        await db_session.flush()

        # Create schedule entry
        entry = ScheduleEntry(
            protocol_run=run,
            name="test_schedule_entry",
            scheduled_at=datetime.now(timezone.utc),
            asset_analysis_completed_at=None,
            assets_reserved_at=None,
            execution_started_at=None,
            execution_completed_at=None,
        )
        db_session.add(entry)
        await db_session.flush()
        return entry

    return _factory


@pytest.mark.asyncio
async def test_schedule_history_orm_creation_minimal(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test creating ScheduleHistory with minimal required fields.

    The model should:
    - Require schedule_entry_accession_id and event_type (kw_only)
    - Auto-generate accession_id
    - Set event_start with server_default=func.now()
    - Default triggered_by to SYSTEM
    - Allow nullable from_status, to_status, event_data_json, message, error_details
    """
    schedule_entry = await schedule_entry_factory()

    history = ScheduleHistory(
        name="test_history_minimal",
        schedule_entry_accession_id=schedule_entry.accession_id,
        event_type=ScheduleHistoryEventEnum.STATUS_CHANGED.value,
        event_start=datetime.now(timezone.utc),
    )
    history.schedule_entry = schedule_entry

    db_session.add(history)
    await db_session.flush()
    await db_session.refresh(history)

    # Verify minimal creation
    assert history.accession_id is not None
    assert history.schedule_entry_accession_id == schedule_entry.accession_id
    assert history.event_type == ScheduleHistoryEventEnum.STATUS_CHANGED.value
    assert history.event_start is not None, f"event_start is None. Data: {history.model_dump()}"
    assert isinstance(history.event_start, datetime)
    assert history.triggered_by == ScheduleHistoryEventTriggerEnum.SYSTEM

    # Verify optional fields are None
    assert history.from_status is None
    assert history.to_status is None
    assert history.event_data_json is None
    assert history.message is None
    assert history.error_details is None
    assert history.event_end is None
    assert history.asset_count is None


@pytest.mark.asyncio
async def test_schedule_history_orm_creation_with_all_fields(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test creating ScheduleHistory with all fields populated.

    Should handle:
    - Status transition (from_status → to_status)
    - Event data JSON
    - Message and error details
    - Event timing (event_start, event_end)
    - Asset count
    - Custom trigger (USER, CELERY, etc.)
    """
    schedule_entry = await schedule_entry_factory()
    event_data = {"retry_count": 1, "reason": "Network timeout"}

    history = ScheduleHistory(
        name="test_history_all_fields",
        schedule_entry_accession_id=schedule_entry.accession_id,
        event_type=ScheduleHistoryEventEnum.STATUS_CHANGED.value,
        from_status=ScheduleStatusEnum.QUEUED.value,
        to_status=ScheduleStatusEnum.READY_TO_EXECUTE.value,
        event_data_json=event_data,
        message="Status changed to ready",
        error_details="Previous error: timeout",
        asset_count=3,
        triggered_by=ScheduleHistoryEventTriggerEnum.USER.value,
    )
    history.schedule_entry = schedule_entry

    db_session.add(history)
    await db_session.flush()

    # Verify all fields
    assert history.from_status == ScheduleStatusEnum.QUEUED
    assert history.to_status == ScheduleStatusEnum.READY_TO_EXECUTE
    assert history.event_data_json == event_data
    assert history.message == "Status changed to ready"
    assert history.error_details == "Previous error: timeout"
    assert history.asset_count == 3
    assert history.triggered_by == ScheduleHistoryEventTriggerEnum.USER


@pytest.mark.asyncio
async def test_schedule_history_orm_persist_to_database(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test full persistence cycle for ScheduleHistory."""
    schedule_entry = await schedule_entry_factory()

    history = ScheduleHistory(
        name="test_history_persist",
        schedule_entry_accession_id=schedule_entry.accession_id,
        event_type=ScheduleHistoryEventEnum.SCHEDULED.value,
        message="Assets reserved successfully",
        asset_count=2,
    )
    history.schedule_entry = schedule_entry

    db_session.add(history)
    await db_session.commit()

    # Query back from database
    result = await db_session.execute(
        select(ScheduleHistory).where(
            ScheduleHistory.accession_id == history.accession_id,
        ),
    )
    retrieved_history = result.scalar_one()

    assert retrieved_history is not None
    assert retrieved_history.accession_id == history.accession_id
    assert retrieved_history.event_type == ScheduleHistoryEventEnum.SCHEDULED
    assert retrieved_history.message == "Assets reserved successfully"
    assert retrieved_history.asset_count == 2


@pytest.mark.asyncio
async def test_schedule_history_orm_all_event_types(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test creating history entries for all event types.

    Should support:
    - STATUS_CHANGE
    - ASSET_RESERVED
    - ASSET_RELEASED
    - EXECUTION_STARTED
    - EXECUTION_COMPLETED
    - EXECUTION_FAILED
    - PRIORITY_CHANGED
    - RETRY_ATTEMPTED
    """
    schedule_entry = await schedule_entry_factory()

    for event_type in ScheduleHistoryEventEnum:
        history = ScheduleHistory(
            name=f"test_history_{uuid7()}",
            schedule_entry_accession_id=schedule_entry.accession_id,
            event_type=event_type.value,
            message=f"Test event: {event_type.value}",
        )
        history.schedule_entry = schedule_entry
        db_session.add(history)

    await db_session.flush()

    # Verify all event types were created
    for event_type in ScheduleHistoryEventEnum:
        result = await db_session.execute(
            select(ScheduleHistory).where(
                ScheduleHistory.event_type == event_type.value,
            ),
        )
        history = result.scalar_one_or_none()
        assert history is not None
        assert history.event_type == event_type.value


@pytest.mark.asyncio
async def test_schedule_history_orm_status_transitions(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test tracking status transitions through history.

    Should properly record:
    - QUEUED → READY_TO_EXECUTE
    - READY_TO_EXECUTE → EXECUTING
    - EXECUTING → COMPLETED
    """
    schedule_entry = await schedule_entry_factory()

    transitions = [
        (None, ScheduleStatusEnum.QUEUED),
        (ScheduleStatusEnum.QUEUED, ScheduleStatusEnum.READY_TO_EXECUTE),
        (ScheduleStatusEnum.READY_TO_EXECUTE, ScheduleStatusEnum.EXECUTING),
        (ScheduleStatusEnum.EXECUTING, ScheduleStatusEnum.COMPLETED),
    ]

    for from_status, to_status in transitions:
        history = ScheduleHistory(
            name=f"test_history_{uuid7()}",
            schedule_entry_accession_id=schedule_entry.accession_id,
            event_type=ScheduleHistoryEventEnum.STATUS_CHANGED.value,
            from_status=from_status,
            to_status=to_status,
            message=f"Transition: {from_status} → {to_status}",
        )
        history.schedule_entry = schedule_entry
        db_session.add(history)

    await db_session.flush()

    # Query history in order
    result = await db_session.execute(
        select(ScheduleHistory)
        .where(ScheduleHistory.schedule_entry_accession_id == schedule_entry.accession_id)
        .order_by(ScheduleHistory.event_start),
    )
    history_entries = result.scalars().all()

    assert len(history_entries) == 4
    assert history_entries[0].from_status is None
    assert history_entries[0].to_status == ScheduleStatusEnum.QUEUED
    assert history_entries[3].to_status == ScheduleStatusEnum.COMPLETED


@pytest.mark.asyncio
async def test_schedule_history_orm_event_timing(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test event_start, event_end, and computed duration.

    Should:
    - Auto-set event_start with server_default
    - Allow manual event_end
    - Compute completed_duration_ms from event_end - event_start
    - Support override_duration_ms for manual duration
    """
    schedule_entry = await schedule_entry_factory()

    history = ScheduleHistory(
        name="test_history_timing",
        schedule_entry_accession_id=schedule_entry.accession_id,
        event_type=ScheduleHistoryEventEnum.COMPLETED.value,
        override_duration_ms=5000,
        event_start=datetime.now(timezone.utc),
    )
    history.schedule_entry = schedule_entry

    db_session.add(history)
    await db_session.flush()
    await db_session.refresh(history)

    # Verify timing fields
    # If this fails, it means event_start was not persisted or retrieved correctly
    if history.event_start is None:
        raise AssertionError(f"event_start is None! {history.model_dump()}")

    assert history.event_start is not None
    assert history.event_end is None  # Not set yet
    assert history.override_duration_ms == 5000

    # Set event_end
    history.event_end = history.event_start + timedelta(seconds=3)
    await db_session.flush()
    await db_session.refresh(history)

    # computed_duration_ms should be calculated by database
    assert history.completed_duration_ms is not None
    assert history.completed_duration_ms > 0


@pytest.mark.asyncio
async def test_schedule_history_orm_event_data_jsonb(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test JSONB event_data_json field for storing arbitrary event data."""
    schedule_entry = await schedule_entry_factory()

    event_data = {
        "assets_reserved": ["pipette_1", "plate_reader"],
        "queue_position": 3,
        "estimated_wait_ms": 120000,
        "metadata": {
            "user": "test_user",
            "reason": "scheduled execution",
        },
    }

    history = ScheduleHistory(
        name="test_history_jsonb",
        schedule_entry_accession_id=schedule_entry.accession_id,
        event_type=ScheduleHistoryEventEnum.SCHEDULED.value,
        event_data_json=event_data,
    )
    history.schedule_entry = schedule_entry

    db_session.add(history)
    await db_session.flush()

    # Verify JSONB structure
    assert history.event_data_json["assets_reserved"] == ["pipette_1", "plate_reader"]
    assert history.event_data_json["queue_position"] == 3
    assert history.event_data_json["metadata"]["user"] == "test_user"


@pytest.mark.asyncio
async def test_schedule_history_orm_error_tracking(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test error_details field for tracking failures."""
    schedule_entry = await schedule_entry_factory()

    error_message = """
    Exception: Asset reservation failed
    Traceback:
      File "scheduler.py", line 123
        reserve_asset(asset_id)
    AssetUnavailableError: Pipette p1000 is currently in use
    """

    history = ScheduleHistory(
        name="test_history_error",
        schedule_entry_accession_id=schedule_entry.accession_id,
        event_type=ScheduleHistoryEventEnum.FAILED.value,
        error_details=error_message,
        message="Execution failed due to asset conflict",
    )
    history.schedule_entry = schedule_entry

    db_session.add(history)
    await db_session.flush()

    assert "AssetUnavailableError" in history.error_details
    assert "Pipette p1000" in history.error_details


@pytest.mark.asyncio
async def test_schedule_history_orm_all_trigger_types(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test all trigger types (SYSTEM, USER, CELERY, SCHEDULER).

    Should support:
    - SYSTEM (default)
    - USER
    - CELERY
    - SCHEDULER
    """
    schedule_entry = await schedule_entry_factory()

    for trigger in ScheduleHistoryEventTriggerEnum:
        history = ScheduleHistory(
            name=f"test_history_{uuid7()}",
            schedule_entry_accession_id=schedule_entry.accession_id,
            event_type=ScheduleHistoryEventEnum.STATUS_CHANGED.value,
            triggered_by=trigger,
            message=f"Triggered by: {trigger.value}",
        )
        history.schedule_entry = schedule_entry
        db_session.add(history)

    await db_session.flush()

    # Verify all trigger types
    for trigger in ScheduleHistoryEventTriggerEnum:
        result = await db_session.execute(
            select(ScheduleHistory).where(
                ScheduleHistory.triggered_by == trigger,
            ),
        )
        history = result.scalar_one_or_none()
        assert history is not None
        assert history.triggered_by == trigger


@pytest.mark.asyncio
async def test_schedule_history_orm_asset_count_tracking(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test asset_count field for tracking number of assets involved."""
    schedule_entry = await schedule_entry_factory()

    asset_counts = [0, 1, 5, 10]
    for count in asset_counts:
        history = ScheduleHistory(
            name=f"test_history_{uuid7()}",
            schedule_entry_accession_id=schedule_entry.accession_id,
            event_type=ScheduleHistoryEventEnum.SCHEDULED.value,
            asset_count=count,
            message=f"Reserved {count} assets",
        )
        history.schedule_entry = schedule_entry
        db_session.add(history)

    await db_session.flush()

    # Query by asset count
    result = await db_session.execute(
        select(ScheduleHistory).where(ScheduleHistory.asset_count >= 5),
    )
    high_count_entries = result.scalars().all()

    assert len(high_count_entries) == 2
    assert all(h.asset_count >= 5 for h in high_count_entries)


@pytest.mark.asyncio
async def test_schedule_history_orm_relationship_to_schedule_entry(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test relationship between ScheduleHistory and ScheduleEntry."""
    schedule_entry = await schedule_entry_factory()

    # Create multiple history entries for same schedule entry
    for i in range(3):
        history = ScheduleHistory(
            name=f"test_history_{uuid7()}",
            schedule_entry_accession_id=schedule_entry.accession_id,
            event_type=ScheduleHistoryEventEnum.STATUS_CHANGED.value,
            message=f"Event {i}",
        )
        history.schedule_entry = schedule_entry
        db_session.add(history)

    await db_session.flush()

    # Refresh schedule_entry to load relationship
    await db_session.refresh(schedule_entry, ["history"])

    assert len(schedule_entry.history) == 3
    for history in schedule_entry.history:
        assert history.schedule_entry == schedule_entry
        assert history.schedule_entry_accession_id == schedule_entry.accession_id


@pytest.mark.asyncio
async def test_schedule_history_orm_query_by_event_type(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test querying history entries by event type."""
    schedule_entry = await schedule_entry_factory()

    # Create mix of event types
    event_types = [
        ScheduleHistoryEventEnum.STATUS_CHANGED,
        ScheduleHistoryEventEnum.SCHEDULED,
        ScheduleHistoryEventEnum.STATUS_CHANGED,
        ScheduleHistoryEventEnum.EXECUTED,
    ]

    for event_type in event_types:
        history = ScheduleHistory(
            name=f"test_history_{uuid7()}",
            schedule_entry_accession_id=schedule_entry.accession_id,
            event_type=event_type.value,
        )
        history.schedule_entry = schedule_entry
        db_session.add(history)

    await db_session.flush()

    # Query STATUS_CHANGED events
    result = await db_session.execute(
        select(ScheduleHistory).where(
            ScheduleHistory.event_type == ScheduleHistoryEventEnum.STATUS_CHANGED.value,
        ),
    )
    status_changes = result.scalars().all()

    assert len(status_changes) == 2


@pytest.mark.asyncio
async def test_schedule_history_orm_query_by_time_range(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test querying history entries within a time range."""
    schedule_entry = await schedule_entry_factory()

    # Create entries (event_start will be set automatically)
    for i in range(5):
        history = ScheduleHistory(
            name=f"test_history_{uuid7()}",
            schedule_entry_accession_id=schedule_entry.accession_id,
            event_type=ScheduleHistoryEventEnum.STATUS_CHANGED.value,
            message=f"Event {i}",
        )
        history.schedule_entry = schedule_entry
        db_session.add(history)

    await db_session.flush()

    # Query all events after a timestamp
    now = datetime.now(timezone.utc)
    result = await db_session.execute(
        select(ScheduleHistory)
        .where(ScheduleHistory.schedule_entry_accession_id == schedule_entry.accession_id)
        .where(ScheduleHistory.event_start <= now)
        .order_by(ScheduleHistory.event_start),
    )
    recent_events = result.scalars().all()

    assert len(recent_events) == 5


@pytest.mark.asyncio
async def test_schedule_history_orm_cascade_delete(
    db_session: AsyncSession,
    schedule_entry_factory: Callable[[], ScheduleEntry],
) -> None:
    """Test that deleting schedule entry cascades to delete history entries.

    The relationship should have cascade='all, delete-orphan'.
    """
    schedule_entry = await schedule_entry_factory()
    entry_id = schedule_entry.accession_id

    # Create history entries
    for _i in range(3):
        history = ScheduleHistory(
            name=f"test_history_{uuid7()}",
            schedule_entry_accession_id=schedule_entry.accession_id,
            event_type=ScheduleHistoryEventEnum.STATUS_CHANGED.value,
            event_start=datetime.now(timezone.utc),
        )
        history.schedule_entry = schedule_entry
        db_session.add(history)

    await db_session.flush()

    # Delete schedule entry
    await db_session.delete(schedule_entry)
    await db_session.commit()

    # Verify history entries were cascade deleted
    result = await db_session.execute(
        select(ScheduleHistory).where(
            ScheduleHistory.schedule_entry_accession_id == entry_id,
        ),
    )
    remaining_history = result.scalars().all()

    assert len(remaining_history) == 0
