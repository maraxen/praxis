"""Factory functions for creating test fixtures for Schedule and Output models.

These factories handle the complexity of kw_only fields, init=False relationships,
and proper field initialization to make tests easier to write and maintain.

Usage:
    from tests.factories_schedule import create_schedule_entry, create_asset_reservation

    async def test_something(db_session):
        entry = await create_schedule_entry(db_session)
        reservation = await create_asset_reservation(db_session)
"""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.machine import Machine
from praxis.backend.models.domain.outputs import FunctionDataOutput
from praxis.backend.models.domain.protocol import (
    FunctionCallLog,
    FunctionProtocolDefinition,
    ProtocolRun,
)
from praxis.backend.models.domain.protocol_source import (
    FileSystemProtocolSource,
    ProtocolSourceRepository,
)
from praxis.backend.models.domain.resource import Resource
from praxis.backend.models.domain.schedule import AssetReservation, ScheduleEntry
from praxis.backend.models.enums import (
    AssetReservationStatusEnum,
    AssetType,
    DataOutputTypeEnum,
    ScheduleStatusEnum,
    SpatialContextEnum,
)
from praxis.backend.utils.uuid import uuid7


async def create_protocol_definition(
    db_session: AsyncSession,
    source_repository: ProtocolSourceRepository | None = None,
    file_system_source: FileSystemProtocolSource | None = None,
    **kwargs,
) -> FunctionProtocolDefinition:
    """Factory for creating FunctionProtocolDefinition."""
    # Create source_repository if not provided
    if not source_repository:
        source_repository = ProtocolSourceRepository(
            name=f"test-repo-{uuid7()}",
            git_url="https://github.com/test/repo.git",
        )
        db_session.add(source_repository)
        await db_session.flush()

    # Create file_system_source if not provided
    if not file_system_source:
        file_system_source = FileSystemProtocolSource(
            name=f"test-fs-source-{uuid7()}",
            base_path="/tmp/protocols",
        )
        db_session.add(file_system_source)
        await db_session.flush()

    defaults = {
        "name": f"test_protocol_{uuid7()}",
        "fqn": f"test.protocols.test_protocol_{uuid7()}",
        "version": "1.0.0",
        "is_top_level": True,
        "source_repository_accession_id": source_repository.accession_id if source_repository else None,
        "file_system_source_accession_id": file_system_source.accession_id if file_system_source else None,
    }
    defaults.update(kwargs)

    protocol = FunctionProtocolDefinition(**defaults)
    if source_repository:
        protocol.source_repository = source_repository
    if file_system_source:
        protocol.file_system_source = file_system_source
    db_session.add(protocol)
    await db_session.flush()
    await db_session.refresh(protocol)

    return protocol


async def create_protocol_run(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition | None = None,
    **kwargs,
) -> ProtocolRun:
    """Factory for creating ProtocolRun."""
    if not protocol_definition:
        protocol_definition = await create_protocol_definition(db_session)

    defaults = {
        "name": f"test_protocol_run_{uuid7()}",
        "top_level_protocol_definition_accession_id": protocol_definition.accession_id,
    }
    defaults.update(kwargs)

    run = ProtocolRun(**defaults)
    db_session.add(run)
    await db_session.flush()
    await db_session.refresh(run)

    return run


async def create_schedule_entry(
    db_session: AsyncSession,
    protocol_run: ProtocolRun | None = None,
    **kwargs,
) -> ScheduleEntry:
    """Factory for creating ScheduleEntry.

    Handles kw_only fields and relationship setup automatically.

    Args:
        db_session: AsyncSession for database operations
        protocol_run: Optional ProtocolRun to associate with
        **kwargs: Override default values

    Returns:
        Created and persisted ScheduleEntry

    """
    if not protocol_run:
        protocol_run = await create_protocol_run(db_session)

    # Build entry with all kw_only fields as keyword args
    entry = ScheduleEntry(
        status=kwargs.get("status", ScheduleStatusEnum.QUEUED),
        priority=kwargs.get("priority", 1),
        name=kwargs.get("name", f"test_schedule_entry_{uuid7()}"),
        protocol_run=protocol_run,
        scheduled_at=kwargs.get("scheduled_at", datetime.now(timezone.utc)),
        asset_analysis_completed_at=kwargs.get("asset_analysis_completed_at"),
        assets_reserved_at=kwargs.get("assets_reserved_at"),
        execution_started_at=kwargs.get("execution_started_at"),
        execution_completed_at=kwargs.get("execution_completed_at"),
    )

    # Set optional JSONB fields if provided
    if "asset_requirements_json" in kwargs:
        entry.asset_requirements_json = kwargs["asset_requirements_json"]
    if "user_params_json" in kwargs:
        entry.user_params_json = kwargs["user_params_json"]
    if "initial_state_json" in kwargs:
        entry.initial_state_json = kwargs["initial_state_json"]

    db_session.add(entry)
    await db_session.flush()
    await db_session.refresh(entry)

    return entry


async def create_machine(
    db_session: AsyncSession,
    **kwargs,
) -> Machine:
    """Factory for creating Machine."""
    defaults = {
        "name": f"test_machine_{uuid7()}",
        "fqn": f"test.machines.TestMachine_{uuid7()}",
        "asset_type": AssetType.MACHINE,
    }
    defaults.update(kwargs)

    machine = Machine(**defaults)
    db_session.add(machine)
    await db_session.flush()
    await db_session.refresh(machine)

    return machine


async def create_resource(
    db_session: AsyncSession,
    **kwargs,
) -> Resource:
    """Factory for creating Resource."""
    defaults = {
        "name": f"test_resource_{uuid7()}",
        "fqn": f"test.resources.TestResource_{uuid7()}",
        "asset_type": AssetType.RESOURCE,
    }
    defaults.update(kwargs)

    resource = Resource(**defaults)
    db_session.add(resource)
    await db_session.flush()
    await db_session.refresh(resource)

    return resource


async def create_asset_reservation(
    db_session: AsyncSession,
    protocol_run: ProtocolRun | None = None,
    schedule_entry: ScheduleEntry | None = None,
    asset: Machine | None = None,
    **kwargs,
) -> AssetReservation:
    """Factory for creating AssetReservation.

    NOTE: Due to unique constraint on protocol_run_accession_id, each protocol
    run can only have ONE reservation. This appears to be a schema limitation.

    Handles all kw_only fields and relationships automatically.

    Args:
        db_session: AsyncSession for database operations
        protocol_run: Optional ProtocolRun to associate with
        schedule_entry: Optional ScheduleEntry to associate with
        asset: Optional asset (Machine/Resource) to reserve
        **kwargs: Override default values

    Returns:
        Created and persisted AssetReservation

    """
    # Create dependencies if not provided
    if not protocol_run:
        protocol_run = await create_protocol_run(db_session)
    if not schedule_entry:
        schedule_entry = await create_schedule_entry(db_session, protocol_run)
    if not asset:
        asset = await create_machine(db_session)

    # Build reservation with all kw_only fields as keyword args
    reservation = AssetReservation(
        protocol_run_accession_id=protocol_run.accession_id,
        schedule_entry_accession_id=schedule_entry.accession_id,
        asset_accession_id=asset.accession_id,
        asset_name=asset.name,
        redis_lock_key=kwargs.get("redis_lock_key", f"lock:asset:{asset.accession_id}"),
        lock_timeout_seconds=kwargs.get("lock_timeout_seconds", 3600),
        status=kwargs.get("status", AssetReservationStatusEnum.PENDING),
        asset_type=kwargs.get("asset_type", AssetType.ASSET),
    )

    # Set optional fields if provided
    if "redis_lock_value" in kwargs:
        reservation.redis_lock_value = kwargs["redis_lock_value"]
    if "released_at" in kwargs:
        reservation.released_at = kwargs["released_at"]
    if "expires_at" in kwargs:
        reservation.expires_at = kwargs["expires_at"]
    if "required_capabilities_json" in kwargs:
        reservation.required_capabilities_json = kwargs["required_capabilities_json"]

    # Set relationships (have init=False)
    reservation.protocol_run = protocol_run
    reservation.schedule_entry = schedule_entry
    reservation.asset = asset

    db_session.add(reservation)
    await db_session.flush()
    await db_session.refresh(reservation)

    return reservation


async def create_function_call_log(
    db_session: AsyncSession,
    protocol_run: ProtocolRun | None = None,
    protocol_definition: FunctionProtocolDefinition | None = None,
    **kwargs,
) -> FunctionCallLog:
    """Factory for creating FunctionCallLog."""
    if not protocol_run:
        protocol_run = await create_protocol_run(db_session)
    if not protocol_definition:
        # Use the protocol run's definition
        await db_session.refresh(protocol_run, ["top_level_protocol_definition"])
        protocol_definition = protocol_run.top_level_protocol_definition

    defaults = {
        "protocol_run_accession_id": protocol_run.accession_id,
        "function_protocol_definition_accession_id": protocol_definition.accession_id,
        "sequence_in_run": kwargs.get("sequence_in_run", 0),
        "start_time": kwargs.get("start_time", datetime.now(timezone.utc)),
    }
    # Don't let kwargs override the required fields
    for key in ["protocol_run_accession_id", "function_protocol_definition_accession_id"]:
        kwargs.pop(key, None)
    defaults.update(kwargs)

    call_log = FunctionCallLog(**defaults)

    # Set relationships
    call_log.protocol_run = protocol_run
    call_log.executed_function_definition = protocol_definition

    db_session.add(call_log)
    await db_session.flush()
    await db_session.refresh(call_log)

    return call_log


async def create_function_data_output(
    db_session: AsyncSession,
    protocol_run: ProtocolRun | None = None,
    function_call_log: FunctionCallLog | None = None,
    **kwargs,
) -> FunctionDataOutput:
    """Factory for creating FunctionDataOutput.

    Handles kw_only fields and optional relationships.

    Args:
        db_session: AsyncSession for database operations
        protocol_run: Optional ProtocolRun to associate with
        function_call_log: Optional FunctionCallLog to associate with
        **kwargs: Override default values including:
            - data_type: DataOutputTypeEnum
            - data_key: str
            - spatial_context: SpatialContextEnum
            - data_value_numeric: float
            - data_value_json: dict
            - data_value_text: str
            - data_value_binary: bytes
            - resource_accession_id: UUID (for resource association)
            - machine_accession_id: UUID (for machine association)
            - deck_accession_id: UUID (for deck association)
            - spatial_coordinates_json: dict
            - measurement_conditions_json: dict

    Returns:
        Created and persisted FunctionDataOutput

    """
    # Create dependencies if not provided
    if not function_call_log:
        function_call_log = await create_function_call_log(db_session, protocol_run)
    if not protocol_run:
        protocol_run = function_call_log.protocol_run

    # Build output with kw_only fields
    output = FunctionDataOutput(
        protocol_run_accession_id=protocol_run.accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
        data_type=kwargs.get("data_type", DataOutputTypeEnum.UNKNOWN),
        data_key=kwargs.get("data_key", ""),
        spatial_context=kwargs.get("spatial_context", SpatialContextEnum.GLOBAL),
    )

    # Set optional numeric data
    if "data_value_numeric" in kwargs:
        output.data_value_numeric = kwargs["data_value_numeric"]

    # Set optional JSONB data
    if "data_value_json" in kwargs:
        output.data_value_json = kwargs["data_value_json"]
    if "spatial_coordinates_json" in kwargs:
        output.spatial_coordinates_json = kwargs["spatial_coordinates_json"]
    if "measurement_conditions_json" in kwargs:
        output.measurement_conditions_json = kwargs["measurement_conditions_json"]

    # Set optional text/binary data
    if "data_value_text" in kwargs:
        output.data_value_text = kwargs["data_value_text"]
    if "data_value_binary" in kwargs:
        output.data_value_binary = kwargs["data_value_binary"]

    # Set optional file info
    if "file_path" in kwargs:
        output.file_path = kwargs["file_path"]
    if "file_size_bytes" in kwargs:
        output.file_size_bytes = kwargs["file_size_bytes"]

    # Set optional FK relationships
    if "resource_accession_id" in kwargs:
        output.resource_accession_id = kwargs["resource_accession_id"]
    if "machine_accession_id" in kwargs:
        output.machine_accession_id = kwargs["machine_accession_id"]
    if "deck_accession_id" in kwargs:
        output.deck_accession_id = kwargs["deck_accession_id"]

    # Set relationships
    output.protocol_run = protocol_run
    output.function_call_log = function_call_log

    db_session.add(output)
    await db_session.flush()
    await db_session.refresh(output)

    return output
