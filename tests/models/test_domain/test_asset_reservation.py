"""Unit tests for AssetReservationmodel."""
from collections.abc import Callable
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.machine import Machine
from praxis.backend.models.domain.protocol import (
    FunctionProtocolDefinition,
    ProtocolRun,
)
from praxis.backend.models.domain.protocol_source import (
    FileSystemProtocolSource,
    ProtocolSourceRepository,
)
from praxis.backend.models.domain.schedule import AssetReservation, ScheduleEntry
from praxis.backend.models.enums import (
    AssetReservationStatusEnum,
    AssetType,
)


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
        source_file_path="/tmp/protocols/test_protocol.py",
        module_name="test.protocols.test_protocol",
        function_name="test_protocol_fn",
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


@pytest_asyncio.fixture
def schedule_entry_factory(
    db_session: AsyncSession,
) -> Callable[[ProtocolRun], ScheduleEntry]:
    """Create a ScheduleEntryfactory for testing."""

    async def _factory(protocol_run: ProtocolRun) -> ScheduleEntry:
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
        return entry

    return _factory


@pytest_asyncio.fixture
async def machine_asset(db_session: AsyncSession) -> Machine:
    """Create a Machineasset for reservation testing."""
    machine = Machine(
        name="test_machine_reservation",
        fqn="test.machines.TestMachine",
        asset_type=AssetType.MACHINE,
    )
    db_session.add(machine)
    await db_session.flush()
    return machine


@pytest.mark.asyncio
async def test_asset_reservation_orm_creation_minimal(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test creating AssetReservationwith minimal required fields."""
    protocol_run = await protocol_run_factory()
    schedule_entry = await schedule_entry_factory(protocol_run)
    reservation = AssetReservation(
        name="test_reservation",
        protocol_run_accession_id=protocol_run.accession_id,
        schedule_entry_accession_id=schedule_entry.accession_id,
        asset_accession_id=machine_asset.accession_id,
        asset_name=machine_asset.name,
        redis_lock_key=f"lock:{machine_asset.accession_id}",
        released_at=None,
    )

    db_session.add(reservation)
    await db_session.flush()

    assert reservation.accession_id is not None
    assert reservation.protocol_run_accession_id == protocol_run.accession_id
    assert reservation.schedule_entry_accession_id == schedule_entry.accession_id
    assert reservation.asset_accession_id == machine_asset.accession_id
    assert reservation.asset_name == machine_asset.name
    assert reservation.redis_lock_key == f"lock:{machine_asset.accession_id}"
    assert reservation.asset_type == AssetType.ASSET
    assert reservation.status == AssetReservationStatusEnum.PENDING
    assert reservation.lock_timeout_seconds == 3600
    assert reservation.redis_lock_value is None
    assert reservation.reserved_at is not None
    assert reservation.released_at is None


@pytest.mark.asyncio
async def test_asset_reservation_orm_creation_with_all_fields(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test creating AssetReservationwith all fields populated."""
    protocol_run = await protocol_run_factory()
    schedule_entry = await schedule_entry_factory(protocol_run)
    now = datetime.now(timezone.utc)
    reservation = AssetReservation(
        name="test_reservation_all_fields",
        protocol_run_accession_id=protocol_run.accession_id,
        schedule_entry_accession_id=schedule_entry.accession_id,
        asset_accession_id=machine_asset.accession_id,
        asset_name=machine_asset.name,
        redis_lock_key=f"lock:{machine_asset.accession_id}",
        status=AssetReservationStatusEnum.RESERVED,
        redis_lock_value="test_lock_value",
        lock_timeout_seconds=60,
        released_at=now,
    )
    db_session.add(reservation)
    await db_session.flush()

    assert reservation.status == AssetReservationStatusEnum.RESERVED
    assert reservation.redis_lock_value == "test_lock_value"
    assert reservation.lock_timeout_seconds == 60
    assert reservation.released_at == now


@pytest.mark.asyncio
async def test_asset_reservation_orm_persist_to_database(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test full persistence cycle for AssetReservation."""
    protocol_run = await protocol_run_factory()
    schedule_entry = await schedule_entry_factory(protocol_run)
    reservation = AssetReservation(
        name="test_reservation_persist",
        protocol_run_accession_id=protocol_run.accession_id,
        schedule_entry_accession_id=schedule_entry.accession_id,
        asset_accession_id=machine_asset.accession_id,
        asset_name=machine_asset.name,
        redis_lock_key=f"lock:{machine_asset.accession_id}",
        released_at=None,
    )
    db_session.add(reservation)
    await db_session.commit()

    result = await db_session.execute(
        select(AssetReservation).where(
            AssetReservation.accession_id == reservation.accession_id,
        ),
    )
    retrieved_reservation = result.scalar_one()

    assert retrieved_reservation is not None
    assert retrieved_reservation.accession_id == reservation.accession_id
    assert retrieved_reservation.asset_name == machine_asset.name


@pytest.mark.asyncio
async def test_asset_reservation_orm_status_transitions(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test different status values for asset reservations."""
    for status in AssetReservationStatusEnum:
        protocol_run = await protocol_run_factory()
        schedule_entry = await schedule_entry_factory(protocol_run)
        reservation = AssetReservation(
            name=f"test_reservation_{status.value}",
            protocol_run_accession_id=protocol_run.accession_id,
            schedule_entry_accession_id=schedule_entry.accession_id,
            asset_accession_id=machine_asset.accession_id,
            asset_name=machine_asset.name,
            redis_lock_key=f"lock:{machine_asset.accession_id}:{status.value}",
            status=status,
            released_at=None,
        )
        db_session.add(reservation)

    await db_session.flush()

    for status in AssetReservationStatusEnum:
        result = await db_session.execute(
            select(AssetReservation).where(AssetReservation.status == status),
        )
        reservation = result.scalar_one_or_none()
        assert reservation is not None
        assert reservation.status == status


@pytest.mark.asyncio
async def test_asset_reservation_orm_redis_lock_fields(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test Redis lock tracking fields."""
    protocol_run = await protocol_run_factory()
    schedule_entry = await schedule_entry_factory(protocol_run)
    reservation = AssetReservation(
        name="test_reservation_redis",
        protocol_run_accession_id=protocol_run.accession_id,
        schedule_entry_accession_id=schedule_entry.accession_id,
        asset_accession_id=machine_asset.accession_id,
        asset_name=machine_asset.name,
        redis_lock_key="test_lock_key",
        redis_lock_value="test_lock_value",
        lock_timeout_seconds=120,
        released_at=None,
    )
    db_session.add(reservation)
    await db_session.flush()

    assert reservation.redis_lock_key == "test_lock_key"
    assert reservation.redis_lock_value == "test_lock_value"
    assert reservation.lock_timeout_seconds == 120


@pytest.mark.asyncio
async def test_asset_reservation_orm_timing_fields(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test reservation timing fields."""
    protocol_run = await protocol_run_factory()
    schedule_entry = await schedule_entry_factory(protocol_run)
    now = datetime.now(timezone.utc)
    reservation = AssetReservation(
        name="test_reservation_timing",
        protocol_run_accession_id=protocol_run.accession_id,
        schedule_entry_accession_id=schedule_entry.accession_id,
        asset_accession_id=machine_asset.accession_id,
        asset_name=machine_asset.name,
        redis_lock_key=f"lock:{machine_asset.accession_id}",
        released_at=now,
    )
    db_session.add(reservation)
    await db_session.flush()

    assert reservation.reserved_at is not None
    assert reservation.released_at == now


@pytest.mark.asyncio
async def test_asset_reservation_orm_asset_type_field(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test asset_type field for different asset types."""
    for asset_type in list(AssetType):
        protocol_run = await protocol_run_factory()
        schedule_entry = await schedule_entry_factory(protocol_run)
        reservation = AssetReservation(
            name=f"test_reservation_{asset_type.value}",
            protocol_run_accession_id=protocol_run.accession_id,
            schedule_entry_accession_id=schedule_entry.accession_id,
            asset_accession_id=machine_asset.accession_id,
            asset_name=machine_asset.name,
            redis_lock_key=f"lock:{machine_asset.accession_id}:{asset_type.value}",
            asset_type=asset_type,
            released_at=None,
        )
        db_session.add(reservation)

    await db_session.flush()

    for asset_type in list(AssetType):
        result = await db_session.execute(
            select(AssetReservation).where(
                AssetReservation.asset_type == asset_type,
            ),
        )
        reservation = result.scalars().first()
        assert reservation is not None
        assert reservation.asset_type == asset_type


@pytest.mark.asyncio
async def test_asset_reservation_orm_relationship_to_protocol_run(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test relationship between AssetReservationand ProtocolRun."""
    protocol_run = await protocol_run_factory()
    schedule_entry = await schedule_entry_factory(protocol_run)
    reservation = AssetReservation(
        name="test_reservation_relationship_run",
        protocol_run_accession_id=protocol_run.accession_id,
        schedule_entry_accession_id=schedule_entry.accession_id,
        asset_accession_id=machine_asset.accession_id,
        asset_name=machine_asset.name,
        redis_lock_key=f"lock:{machine_asset.accession_id}",
        released_at=None,
    )
    reservation.protocol_run = protocol_run
    db_session.add(reservation)
    await db_session.flush()

    assert reservation.protocol_run_accession_id == protocol_run.accession_id
    assert reservation.protocol_run == protocol_run
    await db_session.refresh(protocol_run, ["asset_reservations"])
    assert reservation in protocol_run.asset_reservations


@pytest.mark.asyncio
async def test_asset_reservation_orm_relationship_to_schedule_entry(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test relationship between AssetReservationand ScheduleEntry."""
    protocol_run = await protocol_run_factory()
    schedule_entry = await schedule_entry_factory(protocol_run)
    reservation = AssetReservation(
        name="test_reservation_relationship_schedule",
        protocol_run_accession_id=protocol_run.accession_id,
        schedule_entry_accession_id=schedule_entry.accession_id,
        asset_accession_id=machine_asset.accession_id,
        asset_name=machine_asset.name,
        redis_lock_key=f"lock:{machine_asset.accession_id}",
        released_at=None,
    )
    reservation.schedule_entry = schedule_entry
    db_session.add(reservation)
    await db_session.flush()

    assert reservation.schedule_entry_accession_id == schedule_entry.accession_id
    assert reservation.schedule_entry == schedule_entry
    await db_session.refresh(schedule_entry, ["asset_reservations"])
    assert reservation in schedule_entry.asset_reservations


@pytest.mark.asyncio
async def test_asset_reservation_orm_relationship_to_asset(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test relationship between AssetReservationand Asset."""
    protocol_run = await protocol_run_factory()
    schedule_entry = await schedule_entry_factory(protocol_run)
    reservation = AssetReservation(
        name="test_reservation_relationship_asset",
        protocol_run_accession_id=protocol_run.accession_id,
        schedule_entry_accession_id=schedule_entry.accession_id,
        asset_accession_id=machine_asset.accession_id,
        asset_name=machine_asset.name,
        redis_lock_key=f"lock:{machine_asset.accession_id}",
        released_at=None,
    )
    reservation.asset = machine_asset
    db_session.add(reservation)
    await db_session.flush()

    assert reservation.asset_accession_id == machine_asset.accession_id
    assert reservation.asset == machine_asset
    await db_session.refresh(machine_asset, ["asset_reservations"])
    assert reservation in machine_asset.asset_reservations


@pytest.mark.asyncio
async def test_asset_reservation_orm_query_by_status(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test querying asset reservations by status."""
    statuses = [
        AssetReservationStatusEnum.PENDING,
        AssetReservationStatusEnum.RESERVED,
        AssetReservationStatusEnum.PENDING,
    ]
    for i, status in enumerate(statuses):
        run = await protocol_run_factory()
        entry = await schedule_entry_factory(run)
        reservation = AssetReservation(
            name=f"test_reservation_{i}",
            protocol_run_accession_id=run.accession_id,
            schedule_entry_accession_id=entry.accession_id,
            asset_accession_id=machine_asset.accession_id,
            asset_name=machine_asset.name,
            redis_lock_key=f"lock:{machine_asset.accession_id}:{i}",
            status=status,
            released_at=None,
        )
        db_session.add(reservation)
    await db_session.flush()

    result = await db_session.execute(
        select(AssetReservation).where(
            AssetReservation.status == AssetReservationStatusEnum.PENDING,
        ),
    )
    pending_reservations = result.scalars().all()
    assert len(pending_reservations) == 2

    result = await db_session.execute(
        select(AssetReservation).where(
            AssetReservation.status == AssetReservationStatusEnum.RESERVED,
        ),
    )
    reserved_reservations = result.scalars().all()
    assert len(reserved_reservations) == 1


@pytest.mark.asyncio
async def test_asset_reservation_orm_query_active_reservations(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test querying currently active asset reservations."""
    statuses = [
        AssetReservationStatusEnum.ACTIVE,
        AssetReservationStatusEnum.RESERVED,
        AssetReservationStatusEnum.PENDING,
    ]
    for i, status in enumerate(statuses):
        run = await protocol_run_factory()
        entry = await schedule_entry_factory(run)
        reservation = AssetReservation(
            name=f"test_reservation_{i}",
            protocol_run_accession_id=run.accession_id,
            schedule_entry_accession_id=entry.accession_id,
            asset_accession_id=machine_asset.accession_id,
            asset_name=machine_asset.name,
            redis_lock_key=f"lock:{machine_asset.accession_id}:{i}",
            status=status,
            released_at=None,
        )
        db_session.add(reservation)
    await db_session.flush()

    result = await db_session.execute(
        select(AssetReservation).where(
            AssetReservation.status.in_(
                [
                    AssetReservationStatusEnum.ACTIVE,
                    AssetReservationStatusEnum.RESERVED,
                ],
            ),
        ),
    )
    active_reservations = result.scalars().all()
    assert len(active_reservations) == 2


@pytest.mark.asyncio
async def test_asset_reservation_orm_query_by_asset(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test querying reservations for a specific asset."""
    for i in range(3):
        run = await protocol_run_factory()
        entry = await schedule_entry_factory(run)
        reservation = AssetReservation(
            name=f"test_reservation_{i}",
            protocol_run_accession_id=run.accession_id,
            schedule_entry_accession_id=entry.accession_id,
            asset_accession_id=machine_asset.accession_id,
            asset_name=machine_asset.name,
            redis_lock_key=f"lock:{machine_asset.accession_id}:{i}",
            released_at=None,
        )
        db_session.add(reservation)
    await db_session.flush()

    result = await db_session.execute(
        select(AssetReservation).where(
            AssetReservation.asset_accession_id == machine_asset.accession_id,
        ),
    )
    reservations = result.scalars().all()
    assert len(reservations) == 3


@pytest.mark.asyncio
async def test_multiple_reservations_for_same_run(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    schedule_entry_factory: Callable[[ProtocolRun], ScheduleEntry],
    machine_asset: Machine,
) -> None:
    """Test that multiple asset reservations can be created for the same protocol run."""
    protocol_run = await protocol_run_factory()
    schedule_entry = await schedule_entry_factory(protocol_run)

    reservation1 = AssetReservation(
        name="test_reservation_1",
        protocol_run_accession_id=protocol_run.accession_id,
        schedule_entry_accession_id=schedule_entry.accession_id,
        asset_accession_id=machine_asset.accession_id,
        asset_name=machine_asset.name,
        redis_lock_key=f"lock:{machine_asset.accession_id}:1",
        released_at=None,
    )
    db_session.add(reservation1)

    # Create another asset to reserve
    machine2 = Machine(
        name="test_machine_reservation_2",
        fqn="test.machines.TestMachine2",
        asset_type=AssetType.MACHINE,
    )
    db_session.add(machine2)
    await db_session.flush()

    reservation2 = AssetReservation(
        name="test_reservation_2",
        protocol_run_accession_id=protocol_run.accession_id,
        schedule_entry_accession_id=schedule_entry.accession_id,
        asset_accession_id=machine2.accession_id,
        asset_name=machine2.name,
        redis_lock_key=f"lock:{machine2.accession_id}:2",
        released_at=None,
    )
    db_session.add(reservation2)
    await db_session.flush()

    result = await db_session.execute(
        select(AssetReservation).where(
            AssetReservation.protocol_run_accession_id == protocol_run.accession_id,
        ),
    )
    reservations = result.scalars().all()
    assert len(reservations) == 2
