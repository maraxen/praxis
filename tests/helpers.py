"""Async helper functions for creating test data.

These helpers work with async SQLAlchemy sessions, unlike Factory Boy which
only supports synchronous sessions. Use these for creating test data in
async tests.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.deck import Deck, DeckDefinition
from praxis.backend.models.domain.machine import Machine
from praxis.backend.models.domain.outputs import FunctionDataOutput, WellDataOutput
from praxis.backend.models.domain.protocol import (
    FunctionCallLog,
    FunctionProtocolDefinition,
    ProtocolRun,
)
from praxis.backend.models.domain.protocol_source import (
    FileSystemProtocolSource,
    ProtocolSourceRepository,
)
from praxis.backend.models.domain.resource import Resource, ResourceDefinition
from praxis.backend.models.domain.workcell import Workcell
from praxis.backend.models.enums import AssetType, ProtocolRunStatusEnum, ResourceStatusEnum
from praxis.backend.utils.uuid import uuid7


async def create_workcell(
    db_session: AsyncSession,
    name: str = "test_workcell",
    **kwargs: Any,
) -> Workcell:
    """Create a workcell for testing.

    Args:
        db_session: Async database session
        name: Workcell name (default: "test_workcell")
        **kwargs: Additional attributes to set on the workcell

    Returns:
        Workcell instance with generated accession_id

    """
    accession_id = kwargs.pop("accession_id", None)
    workcell = Workcell(name=name, **kwargs)
    if accession_id:
        workcell.accession_id = accession_id
    db_session.add(workcell)
    await db_session.flush()
    return workcell


async def create_machine(
    db_session: AsyncSession,
    workcell: Workcell | None = None,
    name: str | None = None,
    fqn: str = "test.machine",
    **kwargs: Any,
) -> Machine:
    """Create a machine for testing.

    Args:
        db_session: Async database session
        workcell: Parent workcell (will create one if not provided)
        name: Machine name (default: unique generated name)
        fqn: Fully qualified name (default: "test.machine")
        **kwargs: Additional attributes to set on the machine

    Returns:
        Machine instance with generated accession_id

    """
    if workcell is None:
        # Generate unique workcell name to avoid constraint violations
        unique_suffix = str(uuid7())
        workcell = await create_workcell(db_session, name=f"test_workcell_{unique_suffix}")

    accession_id = kwargs.pop("accession_id", None)

    # Generate unique machine name if not provided
    if name is None:
        name = f"test_machine_{uuid7()!s}"

    # Set asset_type if not provided
    if "asset_type" not in kwargs:
        kwargs["asset_type"] = AssetType.MACHINE

    machine = Machine(
        name=name,
        fqn=fqn,
        **kwargs,
    )
    machine.workcell_accession_id = workcell.accession_id
    if accession_id:
        machine.accession_id = accession_id
    db_session.add(machine)
    await db_session.flush()
    return machine


async def create_resource_definition(
    db_session: AsyncSession,
    name: str = "test_resource_definition",
    fqn: str = "test.resource.definition",
    **kwargs: Any,
) -> ResourceDefinition:
    """Create a resource definition for testing.

    Args:
        db_session: Async database session
        name: Resource definition name (default: "test_resource_definition")
        fqn: Fully qualified name (default: "test.resource.definition")
        **kwargs: Additional attributes to set on the resource definition

    Returns:
        ResourceDefinition instance

    """
    resource_def = ResourceDefinition(
        name=name,
        fqn=fqn,
        **kwargs,
    )
    db_session.add(resource_def)
    await db_session.flush()
    return resource_def


async def create_resource(
    db_session: AsyncSession,
    name: str | None = None,
    resource_definition: ResourceDefinition | None = None,
    **kwargs: Any,
) -> Resource:
    """Create a resource for testing.

    Args:
        db_session: Async database session
        name: Resource name (generates unique name if not provided)
        resource_definition: Associated resource definition (creates one if not provided)
        **kwargs: Additional attributes to set on the resource

    Returns:
        Resource instance

    """
    # Generate unique name if not provided
    if name is None:
        name = f"test_resource_{uuid7()!s}"

    # Create resource definition if not provided
    if resource_definition is None:
        resource_definition = await create_resource_definition(
            db_session,
            name=f"def_{name}",
            fqn=f"test.resource.def.{uuid7()!s}",
        )

    # Set defaults
    defaults = {
        "name": name,
        "fqn": f"test.resource.{uuid7()!s}",
        "asset_type": AssetType.RESOURCE,
        "status": ResourceStatusEnum.AVAILABLE_IN_STORAGE,
        "resource_definition_accession_id": resource_definition.accession_id,
    }
    defaults.update(kwargs)

    accession_id = defaults.pop("accession_id", None)
    resource = Resource(**defaults)
    if accession_id:
        resource.accession_id = accession_id
    db_session.add(resource)
    await db_session.flush()
    return resource


async def create_deck_definition(
    db_session: AsyncSession,
    resource_definition: ResourceDefinition | None = None,
    name: str = "test_deck_definition",
    fqn: str = "test.deck.definition",
    **kwargs: Any,
) -> DeckDefinition:
    """Create a deck definition for testing.

    Args:
        db_session: Async database session
        resource_definition: Associated resource definition (will create one if not provided)
        name: Deck definition name (default: "test_deck_definition")
        fqn: Fully qualified name (default: "test.deck.definition")
        **kwargs: Additional attributes to set on the deck definition

    Returns:
        DeckDefinition instance with generated accession_id

    """
    if resource_definition is None:
        resource_definition = await create_resource_definition(db_session)

    deck_def = DeckDefinition(
        name=name,
        fqn=fqn,
        # resource_definition=resource_definition, # Relationship deprecated/removed?
        resource_definition_accession_id=resource_definition.accession_id,
        **kwargs,
    )
    db_session.add(deck_def)
    await db_session.flush()
    return deck_def


async def create_deck(
    db_session: AsyncSession,
    machine: Machine | None = None,
    deck_definition: DeckDefinition | None = None,
    name: str = "test_deck",
    **kwargs: Any,
) -> Deck:
    """Create a deck for testing.

    Args:
        db_session: Async database session
        machine: Parent machine (will create one if not provided)
        deck_definition: Deck type definition (will create one if not provided)
        name: Deck name (default: "test_deck")
        **kwargs: Additional attributes to set on the deck

    Returns:
        Deck instance with generated accession_id

    """
    if machine is None:
        machine = await create_machine(db_session)

    if deck_definition is None:
        deck_definition = await create_deck_definition(db_session)

    # Set asset_type if not provided
    if "asset_type" not in kwargs:
        kwargs["asset_type"] = AssetType.DECK

    accession_id = kwargs.pop("accession_id", None)
    deck = Deck(
        name=name,
        deck_type_id=deck_definition.accession_id,
        parent_machine_accession_id=machine.accession_id,
        resource_definition_accession_id=deck_definition.resource_definition_accession_id, # Updated field name logic
        **kwargs,
    )
    if accession_id:
        deck.accession_id = accession_id

    db_session.add(deck)
    await db_session.flush()
    await db_session.refresh(deck)  # Ensure the deck is fully loaded
    return deck


async def create_protocol_definition(
    db_session: AsyncSession,
    name: str | None = None,
    **kwargs: Any,
) -> FunctionProtocolDefinition:
    """Create a protocol definition for testing.

    Args:
        db_session: Async database session
        name: Protocol name (generates unique name if not provided)
        **kwargs: Additional attributes to set on the protocol definition

    Returns:
        FunctionProtocolDefinition instance

    """
    # Generate unique name if not provided
    if name is None:
        name = f"test_protocol_{uuid7()!s}"

    # Create a file system source if not provided
    if "file_system_source" not in kwargs:
        fs_source = FileSystemProtocolSource(
            name=f"test_fs_source_{uuid7()!s}",
            base_path="/test/protocols",
        )
        db_session.add(fs_source)
        await db_session.flush()
        kwargs["file_system_source"] = fs_source

    # Create source repository if not provided (required kw_only arg)
    if "source_repository" not in kwargs:
        repo = ProtocolSourceRepository(
            name=f"test_repo_{uuid7()!s}",
            git_url="https://github.com/test/test.git",
        )
        db_session.add(repo)
        await db_session.flush()
        kwargs["source_repository"] = repo

    # Extract relationships that are init=False
    file_system_source = kwargs.pop("file_system_source", None)
    source_repository = kwargs.pop("source_repository", None)

    # Set required defaults
    defaults = {
        "name": name,
        "fqn": f"test.protocols.{name}",
        "source_file_path": f"/test/protocols/{name}.py",
        "module_name": f"test.protocols.{name}",
        "function_name": name,
        "version": "1.0.0",
    }
    defaults.update(kwargs)

    # Set FK IDs if objects were provided/created
    if file_system_source:
        defaults["file_system_source_accession_id"] = file_system_source.accession_id
    if source_repository:
        defaults["source_repository_accession_id"] = source_repository.accession_id

    protocol_def = FunctionProtocolDefinition(**defaults)

    # Manually assign relationships since init=False
    # if file_system_source:
    #     protocol_def.file_system_source = file_system_source
    # if source_repository:
    #     protocol_def.source_repository = source_repository
    db_session.add(protocol_def)
    await db_session.flush()
    return protocol_def


async def create_protocol_run(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition | None = None,
    **kwargs: Any,
) -> ProtocolRun:
    """Create a protocol run for testing.

    Args:
        db_session: Async database session
        protocol_definition: Associated protocol definition (creates one if not provided)
        **kwargs: Additional attributes to set on the protocol run

    Returns:
        ProtocolRun instance

    """
    # Create protocol definition if not provided
    if protocol_definition is None:
        protocol_definition = await create_protocol_definition(db_session)

    # Generate unique name if not provided
    unique_id = str(uuid7())

    # Set defaults
    defaults = {
        "name": f"test_protocol_run_{unique_id}",
        "top_level_protocol_definition_accession_id": protocol_definition.accession_id,
        "status": ProtocolRunStatusEnum.PENDING,
    }
    defaults.update(kwargs)

    # Extract accession_id before creating ORM (it's init=False)
    accession_id = defaults.pop("accession_id", uuid7())

    protocol_run = ProtocolRun(**defaults)
    # Set accession_id manually
    protocol_run.accession_id = accession_id

    db_session.add(protocol_run)
    await db_session.flush()
    return protocol_run


async def create_function_data_output(
    db_session: AsyncSession,
    protocol_run: ProtocolRun | None = None,
    **kwargs: Any,
) -> FunctionDataOutput:
    """Create a function data output for testing.

    Args:
        db_session: Async database session
        protocol_run: Associated protocol run (creates one if not provided)
        **kwargs: Additional attributes to set on the data output

    Returns:
        FunctionDataOutput instance

    """
    from praxis.backend.models.enums import DataOutputTypeEnum

    # Create protocol run if not provided
    if protocol_run is None:
        protocol_run = await create_protocol_run(db_session)

    # Create a function call log (required FK)
    protocol_def = await create_protocol_definition(
        db_session,
        name=f"test_protocol_for_fcl_{uuid7()!s}",
    )

    function_call_log = FunctionCallLog(
        name=f"test_function_call_log_{uuid7()!s}",
        protocol_run_accession_id=protocol_run.accession_id,
        sequence_in_run=0,
        function_protocol_definition_accession_id=protocol_def.accession_id,
    )
    db_session.add(function_call_log)
    await db_session.flush()

    # Set defaults
    defaults = {
        "name": f"test_data_output_{uuid7()!s}",
        "data_key": f"test_output_{uuid7()!s}",
        "data_type": DataOutputTypeEnum.GENERIC_MEASUREMENT,
        "data_json": {"value": 42}, # Updated field name data_value_json -> data_json in Domain
    }
    defaults.update(kwargs)

    # Create ORM with FK IDs only (MappedAsDataclass pattern)
    data_output = FunctionDataOutput(
        **defaults,
        protocol_run_accession_id=protocol_run.accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
    )
    # Assign relationships after construction (required for init=False fields)
    # data_output.protocol_run = protocol_run
    # data_output.function_call_log = function_call_log

    db_session.add(data_output)
    await db_session.flush()
    return data_output


async def create_well_data_output(
    db_session: AsyncSession,
    plate_resource: Resource | None = None,
    function_data_output: FunctionDataOutput | None = None,
    **kwargs: Any,
) -> WellDataOutput:
    """Create a well data output for testing.

    Args:
        db_session: Async database session
        plate_resource: Associated plate resource (creates one if not provided)
        function_data_output: Associated function data output (creates one if not provided)
        **kwargs: Additional attributes to set on the well data output

    Returns:
        WellDataOutput instance

    """
    # Create plate resource if not provided
    if plate_resource is None:
        plate_resource = await create_resource(db_session, name=f"test_plate_{uuid7()!s}")

    # Create function data output if not provided
    if function_data_output is None:
        function_data_output = await create_function_data_output(db_session)

    # Set defaults
    defaults = {
        "name": f"test_well_output_{uuid7()!s}",
        "well_name": "A1",
        "well_row": 0,
        "well_column": 0,
    }
    defaults.update(kwargs)

    # Create ORM with FK IDs only (MappedAsDataclass pattern)
    well_output = WellDataOutput(
        **defaults,
        function_data_output_accession_id=function_data_output.accession_id,
        plate_resource_accession_id=plate_resource.accession_id,
    )
    # Assign relationships after construction (required for init=False fields)
    # well_output.function_data_output = function_data_output
    # well_output.plate_resource = plate_resource

    db_session.add(well_output)
    await db_session.flush()
    return well_output
