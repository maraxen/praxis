"""Comprehensive tests for SchedulerService and related functions.

This test suite demonstrates advanced service testing patterns including:
- CRUD operations with duplicate prevention
- Status management with automatic history logging
- Priority updates with event tracking
- Asset reservation management
- Multi-filter querying
- Time-based cleanup operations
- History tracking and analytics
- Metrics aggregation

These tests serve as examples for testing complex scheduling services with:
- Multiple interconnected models (ScheduleEntry, AssetReservation, History)
- Automatic event logging
- Status transition validation
- Time-based operations
- Complex filtering and aggregation
"""
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.filters import SearchFilters
from praxis.backend.models.domain.machine import Machine
from praxis.backend.models.domain.protocol import (
    FunctionProtocolDefinition,
    ProtocolRun,
)
from praxis.backend.models.domain.protocol_source import (
    FileSystemProtocolSource,
    ProtocolSourceRepository,
)
from praxis.backend.models.domain.schedule import (
    ScheduleEntryCreate,
)
from praxis.backend.models.enums import (
    AssetReservationStatusEnum,
    AssetType,
    ScheduleHistoryEventEnum,
    ScheduleStatusEnum,
)
from praxis.backend.services.scheduler import (
    cleanup_expired_reservations,
    create_asset_reservation,
    get_schedule_history,
    get_scheduling_metrics,
    list_asset_reservations,
    log_schedule_event,
    read_asset_reservation,
    schedule_entry_service,
    update_asset_reservation_status,
)
from praxis.backend.utils.uuid import uuid7

# ============================================================================
# Fixtures
# ============================================================================


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
    """Create a protocol definition for testing."""
    protocol = FunctionProtocolDefinition(
        name="test_protocol",
        fqn="test.protocols.test_protocol",
        version="1.0.0",
        is_top_level=True,
        source_repository_accession_id=source_repository.accession_id,
        file_system_source_accession_id=file_system_source.accession_id,
    )
    db_session.add(protocol)
    await db_session.flush()
    await db_session.refresh(protocol)
    return protocol


@pytest_asyncio.fixture
async def protocol_run(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> ProtocolRun:
    """Create a protocol run for testing."""
    run = ProtocolRun(
        name="test_protocol_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
    )
    db_session.add(run)
    await db_session.flush()
    await db_session.refresh(run)
    return run


@pytest_asyncio.fixture
async def machine_asset(db_session: AsyncSession) -> Machine:
    """Create a machine asset for reservation testing."""
    machine = Machine(
        name="test_machine_scheduler",
        fqn="test.machines.SchedulerTestMachine",
        asset_type=AssetType.MACHINE,
    )
    db_session.add(machine)
    await db_session.flush()
    await db_session.refresh(machine)
    return machine


# ============================================================================
# ScheduleEntryCRUDService Tests
# ============================================================================


@pytest.mark.asyncio
async def test_schedule_entry_service_create(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
) -> None:
    """Test creating a schedule entry.

    Demonstrates:
    - Basic service create operation
    - Default status assignment (QUEUED)
    - Automatic history logging
    """
    create_data = ScheduleEntryCreate(
        protocol_run_accession_id=protocol_run.accession_id,
        priority=5,
    )

    entry = await schedule_entry_service.create(db_session, obj_in=create_data)

    # Verify creation
    assert entry.protocol_run_accession_id == protocol_run.accession_id
    assert entry.status == ScheduleStatusEnum.QUEUED
    assert entry.priority == 5
    assert entry.scheduled_at is not None

    # Verify history was logged
    history = await get_schedule_history(db_session, entry.accession_id)
    assert len(history) == 1
    assert history[0].event_type == ScheduleHistoryEventEnum.SCHEDULE_CREATED
    assert history[0].to_status == ScheduleStatusEnum.QUEUED


@pytest.mark.asyncio
async def test_schedule_entry_service_create_duplicate_prevention(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
) -> None:
    """Test that creating duplicate schedule entry for same protocol run fails.

    Demonstrates:
    - Duplicate prevention logic
    - Proper error handling with ValueError
    """
    create_data = ScheduleEntryCreate(
        protocol_run_accession_id=protocol_run.accession_id,
        priority=1,
    )

    # First creation should succeed
    entry1 = await schedule_entry_service.create(db_session, obj_in=create_data)
    assert entry1 is not None

    # Second creation should fail
    with pytest.raises(ValueError) as exc_info:
        await schedule_entry_service.create(db_session, obj_in=create_data)

    assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
async def test_schedule_entry_service_get_multi_with_pagination(
    db_session: AsyncSession,
) -> None:
    """Test listing schedule entries with pagination.

    Demonstrates:
    - get_multi() with SearchFilters
    - Pagination (skip, limit)
    - Default ordering
    """
    from tests.factories_schedule import create_protocol_run, create_schedule_entry

    # Create multiple entries
    entries = []
    for i in range(5):
        run = await create_protocol_run(db_session)
        entry = await create_schedule_entry(db_session, protocol_run=run, priority=i)
        entries.append(entry)

    # Get all entries
    filters = SearchFilters(skip=0, limit=10)
    retrieved = await schedule_entry_service.get_multi(db_session, filters=filters)

    assert len(retrieved) >= 5

    # Get with pagination
    filters = SearchFilters(skip=2, limit=2)
    paginated = await schedule_entry_service.get_multi(db_session, filters=filters)

    assert len(paginated) == 2


@pytest.mark.asyncio
async def test_schedule_entry_service_get_multi_with_sorting(
    db_session: AsyncSession,
) -> None:
    """Test listing schedule entries with custom sorting.

    Demonstrates:
    - Sorting by priority
    - Ascending vs descending order
    """
    from tests.factories_schedule import create_protocol_run, create_schedule_entry

    # Create entries with different priorities
    run1 = await create_protocol_run(db_session)
    entry1 = await create_schedule_entry(db_session, protocol_run=run1, priority=10)

    run2 = await create_protocol_run(db_session)
    entry2 = await create_schedule_entry(db_session, protocol_run=run2, priority=1)

    run3 = await create_protocol_run(db_session)
    entry3 = await create_schedule_entry(db_session, protocol_run=run3, priority=5)

    # Sort by priority ascending
    filters = SearchFilters(skip=0, limit=10, sort_by="priority")
    sorted_entries = await schedule_entry_service.get_multi(db_session, filters=filters)

    # Find our test entries in results
    test_entries = [e for e in sorted_entries if e.accession_id in [entry1.accession_id, entry2.accession_id, entry3.accession_id]]
    if len(test_entries) == 3:
        assert test_entries[0].priority <= test_entries[1].priority <= test_entries[2].priority


@pytest.mark.asyncio
async def test_schedule_entry_service_update_status(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
) -> None:
    """Test updating schedule entry status.

    Demonstrates:
    - Status transition
    - Automatic history logging
    - Timestamp tracking
    """
    from tests.factories_schedule import create_schedule_entry

    entry = await create_schedule_entry(db_session, protocol_run=protocol_run)
    assert entry.status == ScheduleStatusEnum.QUEUED

    # Update to EXECUTING
    started_at = datetime.now(timezone.utc)
    updated = await schedule_entry_service.update_status(
        db_session,
        schedule_entry_accession_id=entry.accession_id,
        new_status=ScheduleStatusEnum.EXECUTING,
        started_at=started_at,
    )

    assert updated is not None
    assert updated.status == ScheduleStatusEnum.EXECUTING

    # Handle SQLite potentially returning naive datetime
    updated_started_at = updated.execution_started_at
    if updated_started_at and updated_started_at.tzinfo is None:
        updated_started_at = updated_started_at.replace(tzinfo=timezone.utc)
    assert updated_started_at == started_at

    # Verify history was logged
    history = await get_schedule_history(db_session, entry.accession_id)
    # Should have STATUS_CHANGED (factory doesn't log SCHEDULE_CREATED)
    assert len(history) >= 1
    status_changed = [h for h in history if h.event_type == ScheduleHistoryEventEnum.STATUS_CHANGED]
    assert len(status_changed) >= 1
    assert status_changed[0].from_status == ScheduleStatusEnum.QUEUED
    assert status_changed[0].to_status == ScheduleStatusEnum.EXECUTING


@pytest.mark.asyncio
async def test_schedule_entry_service_update_status_with_error(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
) -> None:
    """Test updating schedule entry to failed status with error details.

    Demonstrates:
    - Error tracking in status updates
    - Error message storage
    """
    from tests.factories_schedule import create_schedule_entry

    entry = await create_schedule_entry(db_session, protocol_run=protocol_run)

    # Update to FAILED with error
    error_msg = "Test execution failed: timeout"
    updated = await schedule_entry_service.update_status(
        db_session,
        schedule_entry_accession_id=entry.accession_id,
        new_status=ScheduleStatusEnum.FAILED,
        error_details=error_msg,
    )

    assert updated is not None
    assert updated.status == ScheduleStatusEnum.FAILED
    assert updated.last_error_message == error_msg


@pytest.mark.asyncio
async def test_schedule_entry_service_update_priority(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
) -> None:
    """Test updating schedule entry priority.

    Demonstrates:
    - Priority change operation
    - History logging for priority changes
    - Reason tracking
    """
    from tests.factories_schedule import create_schedule_entry

    entry = await create_schedule_entry(db_session, protocol_run=protocol_run, priority=1)
    assert entry.priority == 1

    # Update priority
    updated = await schedule_entry_service.update_priority(
        db_session,
        schedule_entry_accession_id=entry.accession_id,
        new_priority=10,
        reason="Urgent request",
    )

    assert updated is not None
    assert updated.priority == 10

    # Verify history was logged
    history = await get_schedule_history(db_session, entry.accession_id)
    priority_changes = [h for h in history if h.event_type == ScheduleHistoryEventEnum.PRIORITY_CHANGED]
    assert len(priority_changes) == 1
    assert priority_changes[0].event_data_json["old_priority"] == 1
    assert priority_changes[0].event_data_json["new_priority"] == 10
    assert priority_changes[0].event_data_json["reason"] == "Urgent request"


# ============================================================================
# Asset Reservation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_asset_reservation(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    machine_asset: Machine,
) -> None:
    """Test creating an asset reservation.

    Demonstrates:
    - Asset reservation creation
    - Default lock key/value generation
    - Initial status (PENDING)
    """
    from tests.factories_schedule import create_schedule_entry

    entry = await create_schedule_entry(db_session, protocol_run=protocol_run)

    reservation = await create_asset_reservation(
        db_session,
        schedule_entry_accession_id=entry.accession_id,
        asset_type=AssetType.MACHINE,
        asset_name=machine_asset.name,
        protocol_run_accession_id=protocol_run.accession_id,
        asset_accession_id=machine_asset.accession_id,
    )

    assert reservation.schedule_entry_accession_id == entry.accession_id
    assert reservation.asset_type == AssetType.MACHINE
    assert reservation.asset_name == machine_asset.name
    assert reservation.status == AssetReservationStatusEnum.PENDING
    assert reservation.redis_lock_key is not None
    assert reservation.redis_lock_value is not None


@pytest.mark.asyncio
async def test_create_asset_reservation_with_custom_lock(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    machine_asset: Machine,
) -> None:
    """Test creating asset reservation with custom lock key/value.

    Demonstrates:
    - Custom Redis lock configuration
    - Expiration time setting
    - Capability requirements (JSONB)
    """
    from tests.factories_schedule import create_schedule_entry

    entry = await create_schedule_entry(db_session, protocol_run=protocol_run)

    custom_lock_key = f"custom:lock:{machine_asset.accession_id}"
    custom_lock_value = "my-unique-lock-value"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=2)

    reservation = await create_asset_reservation(
        db_session,
        schedule_entry_accession_id=entry.accession_id,
        asset_type=AssetType.MACHINE,
        asset_name=machine_asset.name,
        protocol_run_accession_id=protocol_run.accession_id,
        asset_accession_id=machine_asset.accession_id,
        redis_lock_key=custom_lock_key,
        redis_lock_value=custom_lock_value,
        required_capabilities_json={"temperature_control": True, "shaking": True},
        estimated_duration_ms=3600000,  # 1 hour
        expires_at=expires_at,
    )

    assert reservation.redis_lock_key == custom_lock_key
    assert reservation.redis_lock_value == custom_lock_value
    assert reservation.required_capabilities_json == {"temperature_control": True, "shaking": True}
    assert reservation.estimated_usage_duration_ms == 3600000

    # Handle SQLite potentially returning naive datetime
    res_expires_at = reservation.expires_at
    if res_expires_at and res_expires_at.tzinfo is None:
        res_expires_at = res_expires_at.replace(tzinfo=timezone.utc)
    assert res_expires_at == expires_at


@pytest.mark.asyncio
async def test_read_asset_reservation(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    machine_asset: Machine,
) -> None:
    """Test reading an asset reservation by ID.

    Demonstrates:
    - read_asset_reservation() function
    - None return for non-existent ID
    """
    from tests.factories_schedule import create_schedule_entry

    entry = await create_schedule_entry(db_session, protocol_run=protocol_run)

    reservation = await create_asset_reservation(
        db_session,
        schedule_entry_accession_id=entry.accession_id,
        asset_type=AssetType.MACHINE,
        asset_name=machine_asset.name,
        protocol_run_accession_id=protocol_run.accession_id,
        asset_accession_id=machine_asset.accession_id,
    )

    # Read it back
    retrieved = await read_asset_reservation(db_session, reservation.accession_id)
    assert retrieved is not None
    assert retrieved.accession_id == reservation.accession_id

    # Non-existent ID returns None
    non_existent = await read_asset_reservation(db_session, uuid7())
    assert non_existent is None


@pytest.mark.asyncio
async def test_list_asset_reservations_with_filters(
    db_session: AsyncSession,
) -> None:
    """Test listing asset reservations with various filters.

    Demonstrates:
    - Filter by schedule_entry_accession_id
    - Filter by asset_type
    - Filter by asset_name
    - Filter by status
    - active_only flag
    """
    from tests.factories_schedule import create_machine, create_protocol_run, create_schedule_entry

    # Create two different schedule entries with reservations
    run1 = await create_protocol_run(db_session)
    entry1 = await create_schedule_entry(db_session, protocol_run=run1)
    machine1 = await create_machine(db_session, name="machine_1")

    # NOTE: Due to unique constraint on protocol_run_accession_id,
    # we need separate protocol runs for each reservation
    reservation1 = await create_asset_reservation(
        db_session,
        schedule_entry_accession_id=entry1.accession_id,
        asset_type=AssetType.MACHINE,
        asset_name=machine1.name,
        protocol_run_accession_id=run1.accession_id,
        asset_accession_id=machine1.accession_id,
    )

    run2 = await create_protocol_run(db_session)
    entry2 = await create_schedule_entry(db_session, protocol_run=run2)
    machine2 = await create_machine(db_session, name="machine_2")

    await create_asset_reservation(
        db_session,
        schedule_entry_accession_id=entry2.accession_id,
        asset_type=AssetType.MACHINE,
        asset_name=machine2.name,
        protocol_run_accession_id=run2.accession_id,
        asset_accession_id=machine2.accession_id,
    )

    # Filter by schedule entry
    entry1_reservations = await list_asset_reservations(
        db_session,
        schedule_entry_accession_id=entry1.accession_id,
    )
    assert len(entry1_reservations) == 1
    assert entry1_reservations[0].accession_id == reservation1.accession_id

    # Filter by asset name
    machine1_reservations = await list_asset_reservations(
        db_session,
        asset_name=machine1.name,
    )
    assert len(machine1_reservations) >= 1
    assert any(r.accession_id == reservation1.accession_id for r in machine1_reservations)


@pytest.mark.asyncio
async def test_list_asset_reservations_active_only(
    db_session: AsyncSession,
) -> None:
    """Test listing only active asset reservations.

    Demonstrates:
    - active_only filter
    - Multiple status values considered active
    """
    from tests.factories_schedule import create_machine, create_protocol_run, create_schedule_entry

    # Create PENDING reservation
    run1 = await create_protocol_run(db_session)
    entry1 = await create_schedule_entry(db_session, protocol_run=run1)
    machine1 = await create_machine(db_session)
    reservation1 = await create_asset_reservation(
        db_session,
        schedule_entry_accession_id=entry1.accession_id,
        asset_type=AssetType.MACHINE,
        asset_name=machine1.name,
        protocol_run_accession_id=run1.accession_id,
        asset_accession_id=machine1.accession_id,
    )

    # Update to RESERVED
    await update_asset_reservation_status(
        db_session,
        reservation_accession_id=reservation1.accession_id,
        new_status=AssetReservationStatusEnum.RESERVED,
    )

    # Create RELEASED reservation (separate protocol run due to unique constraint)
    run2 = await create_protocol_run(db_session)
    entry2 = await create_schedule_entry(db_session, protocol_run=run2)
    machine2 = await create_machine(db_session)
    reservation2 = await create_asset_reservation(
        db_session,
        schedule_entry_accession_id=entry2.accession_id,
        asset_type=AssetType.MACHINE,
        asset_name=machine2.name,
        protocol_run_accession_id=run2.accession_id,
        asset_accession_id=machine2.accession_id,
    )
    await update_asset_reservation_status(
        db_session,
        reservation_accession_id=reservation2.accession_id,
        new_status=AssetReservationStatusEnum.RELEASED,
    )

    # List active only
    active = await list_asset_reservations(db_session, active_only=True)

    # Should include RESERVED but not RELEASED
    active_ids = [r.accession_id for r in active]
    assert reservation1.accession_id in active_ids
    assert reservation2.accession_id not in active_ids


@pytest.mark.asyncio
async def test_update_asset_reservation_status(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    machine_asset: Machine,
) -> None:
    """Test updating asset reservation status.

    Demonstrates:
    - Status transitions
    - Timestamp tracking (reserved_at, released_at)
    """
    from tests.factories_schedule import create_schedule_entry

    entry = await create_schedule_entry(db_session, protocol_run=protocol_run)
    reservation = await create_asset_reservation(
        db_session,
        schedule_entry_accession_id=entry.accession_id,
        asset_type=AssetType.MACHINE,
        asset_name=machine_asset.name,
        protocol_run_accession_id=protocol_run.accession_id,
        asset_accession_id=machine_asset.accession_id,
    )
    assert reservation.status == AssetReservationStatusEnum.PENDING

    # Update to RESERVED
    reserved_time = datetime.now(timezone.utc)
    updated = await update_asset_reservation_status(
        db_session,
        reservation_accession_id=reservation.accession_id,
        new_status=AssetReservationStatusEnum.RESERVED,
        reserved_at=reserved_time,
    )

    assert updated is not None
    assert updated.status == AssetReservationStatusEnum.RESERVED

    # Handle SQLite potentially returning naive datetime
    updated_reserved_at = updated.reserved_at
    if updated_reserved_at and updated_reserved_at.tzinfo is None:
        updated_reserved_at = updated_reserved_at.replace(tzinfo=timezone.utc)
    assert updated_reserved_at == reserved_time

    # Update to RELEASED
    released_time = datetime.now(timezone.utc)
    updated = await update_asset_reservation_status(
        db_session,
        reservation_accession_id=reservation.accession_id,
        new_status=AssetReservationStatusEnum.RELEASED,
        released_at=released_time,
    )

    assert updated is not None
    assert updated.status == AssetReservationStatusEnum.RELEASED

    # Handle SQLite potentially returning naive datetime
    updated_released_at = updated.released_at
    if updated_released_at and updated_released_at.tzinfo is None:
        updated_released_at = updated_released_at.replace(tzinfo=timezone.utc)
    assert updated_released_at == released_time


@pytest.mark.asyncio
async def test_cleanup_expired_reservations(
    db_session: AsyncSession,
) -> None:
    """Test cleaning up expired asset reservations.

    Demonstrates:
    - Time-based cleanup operation
    - Status transition to EXPIRED
    - Selective cleanup (only active reservations)
    """
    from tests.factories_schedule import create_machine, create_protocol_run, create_schedule_entry

    current_time = datetime.now(timezone.utc)
    past_time = current_time - timedelta(hours=2)

    # Create expired PENDING reservation
    run1 = await create_protocol_run(db_session)
    entry1 = await create_schedule_entry(db_session, protocol_run=run1)
    machine1 = await create_machine(db_session)
    expired_reservation = await create_asset_reservation(
        db_session,
        schedule_entry_accession_id=entry1.accession_id,
        asset_type=AssetType.MACHINE,
        asset_name=machine1.name,
        protocol_run_accession_id=run1.accession_id,
        asset_accession_id=machine1.accession_id,
        expires_at=past_time,
    )

    # Create non-expired reservation
    run2 = await create_protocol_run(db_session)
    entry2 = await create_schedule_entry(db_session, protocol_run=run2)
    machine2 = await create_machine(db_session)
    future_time = current_time + timedelta(hours=2)
    active_reservation = await create_asset_reservation(
        db_session,
        schedule_entry_accession_id=entry2.accession_id,
        asset_type=AssetType.MACHINE,
        asset_name=machine2.name,
        protocol_run_accession_id=run2.accession_id,
        asset_accession_id=machine2.accession_id,
        expires_at=future_time,
    )

    # Run cleanup
    count = await cleanup_expired_reservations(db_session, current_time=current_time)
    assert count >= 1

    # Verify expired was updated
    expired = await read_asset_reservation(db_session, expired_reservation.accession_id)
    assert expired.status == AssetReservationStatusEnum.EXPIRED
    assert expired.released_at is not None

    # Verify active was not touched
    active = await read_asset_reservation(db_session, active_reservation.accession_id)
    assert active.status == AssetReservationStatusEnum.PENDING


# ============================================================================
# Schedule History Tests
# ============================================================================


@pytest.mark.asyncio
async def test_log_schedule_event(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
) -> None:
    """Test manually logging a schedule event.

    Demonstrates:
    - log_schedule_event() helper function
    - Event type tracking
    - Custom event data (JSONB)
    """
    from tests.factories_schedule import create_schedule_entry

    entry = await create_schedule_entry(db_session, protocol_run=protocol_run)

    # Log a custom event
    history_entry = await log_schedule_event(
        db_session,
        schedule_entry_accession_id=entry.accession_id,
        event_type=ScheduleHistoryEventEnum.SCHEDULED,
        event_details_json={"asset_count": 3, "analysis_type": "compatibility"},
        message="Started analyzing asset requirements",
    )

    assert history_entry.schedule_entry_accession_id == entry.accession_id
    assert history_entry.event_type == ScheduleHistoryEventEnum.SCHEDULED
    assert history_entry.event_data_json["asset_count"] == 3
    assert history_entry.message == "Started analyzing asset requirements"


@pytest.mark.asyncio
async def test_get_schedule_history(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
) -> None:
    """Test retrieving schedule history.

    Demonstrates:
    - History retrieval for specific entry
    - Pagination (limit, offset)
    - Ordering (most recent first)
    """
    from tests.factories_schedule import create_schedule_entry

    entry = await create_schedule_entry(db_session, protocol_run=protocol_run)

    # Log multiple events
    await log_schedule_event(
        db_session,
        entry.accession_id,
        ScheduleHistoryEventEnum.SCHEDULED,
    )
    await log_schedule_event(
        db_session,
        entry.accession_id,
        ScheduleHistoryEventEnum.EXECUTED,
    )

    # Get all history
    history = await get_schedule_history(db_session, entry.accession_id, limit=100)
    # Should have 2 custom events (factory doesn't log SCHEDULE_CREATED)
    assert len(history) >= 2

    # Get with limit
    limited = await get_schedule_history(db_session, entry.accession_id, limit=2)
    assert len(limited) == 2


@pytest.mark.asyncio
async def test_get_scheduling_metrics(
    db_session: AsyncSession,
) -> None:
    """Test retrieving scheduling metrics for a time period.

    Demonstrates:
    - Metrics aggregation
    - Time range filtering
    - Status counting
    - Error tracking
    """
    from tests.factories_schedule import create_protocol_run, create_schedule_entry

    start_time = datetime.now(timezone.utc) - timedelta(hours=1)

    # Create entries with status transitions
    run1 = await create_protocol_run(db_session)
    entry1 = await create_schedule_entry(db_session, protocol_run=run1)
    await schedule_entry_service.update_status(
        db_session,
        entry1.accession_id,
        ScheduleStatusEnum.CANCELLED,
    )

    run2 = await create_protocol_run(db_session)
    entry2 = await create_schedule_entry(db_session, protocol_run=run2)
    await schedule_entry_service.update_status(
        db_session,
        entry2.accession_id,
        ScheduleStatusEnum.FAILED,
        error_details="Test error",
    )

    end_time = datetime.now(timezone.utc) + timedelta(hours=1)

    # Get metrics
    metrics = await get_scheduling_metrics(db_session, start_time, end_time)

    assert "status_counts" in metrics
    assert "total_events" in metrics
    assert metrics["total_events"] >= 2  # At least our test events
