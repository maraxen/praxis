"""Unit tests for the WellDataOutputmodel."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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
from praxis.backend.models.enums import AssetType
from praxis.backend.utils.uuid import uuid7


@pytest_asyncio.fixture
async def source_repository(db_session: AsyncSession) -> ProtocolSourceRepository:
    """Fixture for a protocol source repository."""
    repo = ProtocolSourceRepository(
        name="test-repo", git_url="https://github.com/test/repo.git",
    )
    db_session.add(repo)
    await db_session.commit()
    return repo


@pytest_asyncio.fixture
async def file_system_source(db_session: AsyncSession) -> FileSystemProtocolSource:
    """Fixture for a file system protocol source."""
    source = FileSystemProtocolSource(name="test-fs", base_path="/tmp")
    db_session.add(source)
    await db_session.commit()
    return source


@pytest_asyncio.fixture
async def protocol_definition(
    db_session: AsyncSession,
    source_repository: ProtocolSourceRepository,
    file_system_source: FileSystemProtocolSource,
) -> FunctionProtocolDefinition:
    """Fixture for a function protocol definition."""
    protocol_definition = FunctionProtocolDefinition(
        name="test_protocol",
        fqn="test.protocol",
        source_repository_accession_id=source_repository.accession_id,
        file_system_source_accession_id=file_system_source.accession_id,
    )
    protocol_definition.source_repository = source_repository
    protocol_definition.file_system_source = file_system_source
    db_session.add(protocol_definition)
    await db_session.commit()
    return protocol_definition


@pytest_asyncio.fixture
async def protocol_run(
    db_session: AsyncSession, protocol_definition: FunctionProtocolDefinition,
) -> ProtocolRun:
    """Fixture for a protocol run."""
    protocol_run = ProtocolRun(
        name="test_run",
        top_level_protocol_definition_accession_id=protocol_definition.accession_id,
    )
    db_session.add(protocol_run)
    await db_session.commit()
    return protocol_run


@pytest_asyncio.fixture
async def function_call_log(
    db_session: AsyncSession,
    protocol_run: ProtocolRun,
    protocol_definition: FunctionProtocolDefinition,
) -> FunctionCallLog:
    """Fixture for a function call log."""
    function_call_log = FunctionCallLog(
        name="test_function_call",
        protocol_run_accession_id=protocol_run.accession_id,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
        sequence_in_run=0,
    )
    function_call_log.protocol_run = protocol_run
    function_call_log.executed_function_definition = protocol_definition
    db_session.add(function_call_log)
    await db_session.commit()
    return function_call_log


@pytest_asyncio.fixture
async def plate_resource(db_session: AsyncSession) -> Resource:
    """Fixture for a plate resource."""
    resource_def = ResourceDefinition(
        name="96-well-plate",
        fqn="pylabrobot.resources.corning_costar_96_wellplate_360ul",
    )
    db_session.add(resource_def)
    await db_session.commit()

    plate_resource = Resource(
        name="plate_1",
        fqn="pylabrobot.resources.corning_costar_96_wellplate_360ul",
        asset_type=AssetType.RESOURCE,
        resource_definition_accession_id=resource_def.accession_id,
    )
    plate_resource.accession_id = uuid7()
    plate_resource.resource_definition = resource_def
    db_session.add(plate_resource)
    await db_session.commit()
    return plate_resource


@pytest_asyncio.fixture
async def function_data_output(
    db_session: AsyncSession, function_call_log: FunctionCallLog, protocol_run: ProtocolRun,
) -> FunctionDataOutput:
    """Fixture for a function data output."""
    data_output = FunctionDataOutput(
        name="test_output",
        protocol_run_accession_id=protocol_run.accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
    )
    data_output.protocol_run = protocol_run
    data_output.function_call_log = function_call_log
    db_session.add(data_output)
    await db_session.commit()
    return data_output


@pytest.mark.asyncio
async def test_well_data_output_orm_creation_minimal(
    db_session: AsyncSession,
    function_data_output: FunctionDataOutput,
    plate_resource: Resource,
):
    """Test creating a WellDataOutputwith minimal fields."""
    well_data = WellDataOutput(
        name="test_well_data",
        function_data_output_accession_id=function_data_output.accession_id,
        plate_resource_accession_id=plate_resource.accession_id,
    )
    well_data.function_data_output = function_data_output
    well_data.plate_resource = plate_resource
    db_session.add(well_data)
    await db_session.commit()

    assert well_data.accession_id is not None
    assert well_data.function_data_output_accession_id == function_data_output.accession_id
    assert well_data.plate_resource_accession_id == plate_resource.accession_id
    assert well_data.well_name == ""
    assert well_data.well_row == 0
    assert well_data.well_column == 0
    assert well_data.data_value is None


@pytest.mark.asyncio
async def test_well_data_output_orm_creation_all_fields(
    db_session: AsyncSession,
    function_data_output: FunctionDataOutput,
    plate_resource: Resource,
):
    """Test creating a WellDataOutputwith all fields populated."""
    well_data = WellDataOutput(
        name="test_well_data_all",
        function_data_output_accession_id=function_data_output.accession_id,
        plate_resource_accession_id=plate_resource.accession_id,
        well_name="A1",
        well_row=0,
        well_column=0,
        well_index=0,
        data_value=0.123,
    )
    well_data.function_data_output = function_data_output
    well_data.plate_resource = plate_resource
    db_session.add(well_data)
    await db_session.commit()

    assert well_data.well_name == "A1"
    assert well_data.well_row == 0
    assert well_data.well_column == 0
    assert well_data.well_index == 0
    assert well_data.data_value == 0.123


@pytest.mark.asyncio
async def test_well_data_output_orm_persistence(
    db_session: AsyncSession,
    function_data_output: FunctionDataOutput,
    plate_resource: Resource,
):
    """Test that a WellDataOutputcan be persisted to the database."""
    well_data = WellDataOutput(
        name="test_well_data_persistence",
        function_data_output_accession_id=function_data_output.accession_id,
        plate_resource_accession_id=plate_resource.accession_id,
        well_name="B2",
        data_value=0.456,
    )
    well_data.function_data_output = function_data_output
    well_data.plate_resource = plate_resource
    db_session.add(well_data)
    await db_session.commit()

    result = await db_session.execute(
        select(WellDataOutput).where(
            WellDataOutput.accession_id == well_data.accession_id,
        ),
    )
    retrieved_well_data = result.scalar_one()

    assert retrieved_well_data is not None
    assert retrieved_well_data.well_name == "B2"
    assert retrieved_well_data.data_value == 0.456


@pytest.mark.asyncio
async def test_well_data_output_orm_relationships(
    db_session: AsyncSession,
    function_data_output: FunctionDataOutput,
    plate_resource: Resource,
):
    """Test the relationships to FunctionDataOutputand Resource."""
    well_data = WellDataOutput(
        name="test_well_data_relationships",
        function_data_output_accession_id=function_data_output.accession_id,
        plate_resource_accession_id=plate_resource.accession_id,
    )
    well_data.function_data_output = function_data_output
    well_data.plate_resource = plate_resource
    db_session.add(well_data)
    await db_session.commit()
    await db_session.refresh(well_data, ["function_data_output", "plate_resource"])

    assert well_data.function_data_output.accession_id == function_data_output.accession_id
    assert well_data.plate_resource.accession_id == plate_resource.accession_id
