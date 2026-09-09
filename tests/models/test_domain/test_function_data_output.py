"""Unit tests for FunctionDataOutputmodel."""
from collections.abc import Callable
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
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
from praxis.backend.models.enums import (
    AssetType,
    DataOutputTypeEnum,
    SpatialContextEnum,
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


@pytest_asyncio.fixture
async def function_call_log(
    db_session: AsyncSession,
    protocol_run_factory: Callable[[], ProtocolRun],
    protocol_definition: FunctionProtocolDefinition,
) -> FunctionCallLog:
    """Create a FunctionCallLogfor testing."""
    protocol_run = await protocol_run_factory()
    call_log = FunctionCallLog(
        name="test_function_call_log",
        protocol_run_accession_id=protocol_run.accession_id,
        function_protocol_definition_accession_id=protocol_definition.accession_id,
        sequence_in_run=0,
    )
    call_log.start_time = datetime.now(timezone.utc)
    call_log.protocol_run = protocol_run
    call_log.executed_function_definition = protocol_definition
    db_session.add(call_log)
    await db_session.flush()
    return call_log


@pytest_asyncio.fixture
async def resource_asset(db_session: AsyncSession) -> Resource:
    """Create a Resourcefor data output association."""
    resource = Resource(
        name="test_resource_output",
        fqn="test.resources.TestResource",
        asset_type=AssetType.RESOURCE,
    )
    db_session.add(resource)
    await db_session.flush()
    return resource


@pytest_asyncio.fixture
async def machine_asset(db_session: AsyncSession) -> Machine:
    """Create a Machinefor data output association."""
    machine = Machine(
        name="test_machine_output",
        fqn="test.machines.TestMachine",
        asset_type=AssetType.MACHINE,
    )
    db_session.add(machine)
    await db_session.flush()
    return machine


@pytest.mark.asyncio
async def test_function_data_output_orm_creation_minimal(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test creating FunctionDataOutputwith minimal required fields."""
    output = FunctionDataOutput(
        name="test_output",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    db_session.add(output)
    await db_session.flush()

    assert output.accession_id is not None
    assert (
        output.protocol_run_accession_id
        == function_call_log.protocol_run_accession_id
    )
    assert (
        output.function_call_log_accession_id == function_call_log.accession_id
    )
    assert output.data_type == DataOutputTypeEnum.UNKNOWN
    assert output.data_key == ""
    assert output.spatial_context == SpatialContextEnum.GLOBAL
    assert output.resource_accession_id is None
    assert output.machine_accession_id is None
    assert output.data_value_numeric is None
    assert output.data_value_json is None
    assert output.data_value_text is None
    assert output.data_value_binary is None


@pytest.mark.asyncio
async def test_function_data_output_orm_creation_with_all_fields(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
    resource_asset: Resource,
    machine_asset: Machine,
) -> None:
    """Test creating FunctionDataOutputwith all fields populated."""
    output = FunctionDataOutput(
        name="test_output_all_fields",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
        data_type=DataOutputTypeEnum.GENERIC_MEASUREMENT,
        data_key="absorbance_580nm",
        spatial_context=SpatialContextEnum.WELL_SPECIFIC,
        resource_accession_id=resource_asset.accession_id,
        machine_accession_id=machine_asset.accession_id,
        spatial_coordinates_json={"well": "A1"},
        data_value_numeric=0.456,
        data_value_json={"a": 1},
        data_value_text="test",
        data_value_binary=b"test",
        file_path="/path/to/file",
        measurement_conditions_json={"b": 2},
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    output.resource = resource_asset
    output.machine = machine_asset
    db_session.add(output)
    await db_session.flush()

    assert output.data_type == DataOutputTypeEnum.GENERIC_MEASUREMENT
    assert output.data_key == "absorbance_580nm"
    assert output.spatial_context == SpatialContextEnum.WELL_SPECIFIC
    assert output.resource_accession_id == resource_asset.accession_id
    assert output.machine_accession_id == machine_asset.accession_id
    assert output.spatial_coordinates_json == {"well": "A1"}
    assert output.data_value_numeric == 0.456
    assert output.data_value_json == {"a": 1}
    assert output.data_value_text == "test"
    assert output.data_value_binary == b"test"
    assert output.file_path == "/path/to/file"
    assert output.measurement_conditions_json == {"b": 2}


@pytest.mark.asyncio
async def test_function_data_output_orm_persist_to_database(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test full persistence cycle for FunctionDataOutput."""
    output = FunctionDataOutput(
        name="test_output_persist",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    db_session.add(output)
    await db_session.commit()

    result = await db_session.execute(
        select(FunctionDataOutput).where(
            FunctionDataOutput.accession_id == output.accession_id,
        ),
    )
    retrieved_output = result.scalar_one()

    assert retrieved_output is not None
    assert retrieved_output.accession_id == output.accession_id


@pytest.mark.asyncio
async def test_function_data_output_orm_data_type_values(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test different data_type values."""
    for data_type in DataOutputTypeEnum:
        output = FunctionDataOutput(
            name=f"test_output_{data_type.value}",
            protocol_run_accession_id=function_call_log.protocol_run_accession_id,
            function_call_log_accession_id=function_call_log.accession_id,
            data_type=data_type,
        )
        output.protocol_run = function_call_log.protocol_run
        output.function_call_log = function_call_log
        db_session.add(output)

    await db_session.flush()

    for data_type in DataOutputTypeEnum:
        result = await db_session.execute(
            select(FunctionDataOutput).where(
                FunctionDataOutput.data_type == data_type,
            ),
        )
        output = result.scalars().first()
        assert output is not None
        assert output.data_type == data_type


@pytest.mark.asyncio
async def test_function_data_output_orm_spatial_context_values(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test different spatial_context values."""
    for spatial_context in SpatialContextEnum:
        output = FunctionDataOutput(
            name=f"test_output_{spatial_context.value}",
            protocol_run_accession_id=function_call_log.protocol_run_accession_id,
            function_call_log_accession_id=function_call_log.accession_id,
            spatial_context=spatial_context,
        )
        output.protocol_run = function_call_log.protocol_run
        output.function_call_log = function_call_log
        db_session.add(output)

    await db_session.flush()

    for spatial_context in SpatialContextEnum:
        result = await db_session.execute(
            select(FunctionDataOutput).where(
                FunctionDataOutput.spatial_context == spatial_context,
            ),
        )
        output = result.scalars().first()
        assert output is not None
        assert output.spatial_context == spatial_context


@pytest.mark.asyncio
async def test_function_data_output_orm_numeric_data(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test data_value_numeric field for measurements."""
    output = FunctionDataOutput(
        name="test_output_numeric",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
        data_type=DataOutputTypeEnum.GENERIC_MEASUREMENT,
        data_key="absorbance_580nm",
        data_value_numeric=0.456,
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    db_session.add(output)
    await db_session.flush()

    assert output.data_value_numeric == 0.456


@pytest.mark.asyncio
async def test_function_data_output_orm_json_data(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test data_value_json field for structured data."""
    json_data = {"a": 1, "b": [1, 2, 3]}
    output = FunctionDataOutput(
        name="test_output_json",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
        data_value_json=json_data,
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    db_session.add(output)
    await db_session.flush()

    assert output.data_value_json == json_data


@pytest.mark.asyncio
async def test_function_data_output_orm_text_data(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test data_value_text field for text data."""
    output = FunctionDataOutput(
        name="test_output_text",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
        data_value_text="test_text",
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    db_session.add(output)
    await db_session.flush()

    assert output.data_value_text == "test_text"


@pytest.mark.asyncio
async def test_function_data_output_orm_binary_data(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test data_value_binary field for binary data."""
    output = FunctionDataOutput(
        name="test_output_binary",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
        data_value_binary=b"test_binary",
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    db_session.add(output)
    await db_session.flush()

    assert output.data_value_binary == b"test_binary"


@pytest.mark.asyncio
async def test_function_data_output_orm_spatial_coordinates_jsonb(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test spatial_coordinates_json field."""
    coordinates = {"well": "A1", "row": 0, "col": 0}
    output = FunctionDataOutput(
        name="test_output_spatial",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
        spatial_coordinates_json=coordinates,
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    db_session.add(output)
    await db_session.flush()

    assert output.spatial_coordinates_json == coordinates


@pytest.mark.asyncio
async def test_function_data_output_orm_metadata_jsonb(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test metadata_json field."""
    metadata = {"a": 1, "b": "test"}
    output = FunctionDataOutput(
        name="test_output_metadata",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
        measurement_conditions_json=metadata,
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    db_session.add(output)
    await db_session.flush()

    assert output.measurement_conditions_json == metadata


@pytest.mark.asyncio
async def test_function_data_output_orm_file_path(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test file_path field for external file references."""
    output = FunctionDataOutput(
        name="test_output_file_path",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
        file_path="/path/to/test/file",
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    db_session.add(output)
    await db_session.flush()

    assert output.file_path == "/path/to/test/file"


@pytest.mark.asyncio
async def test_function_data_output_orm_relationship_to_protocol_run(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test relationship to ProtocolRun."""
    output = FunctionDataOutput(
        name="test_output_relationship_run",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    db_session.add(output)
    await db_session.flush()

    assert output.protocol_run.accession_id == function_call_log.protocol_run.accession_id

    # Verify via query to avoid lazy load issues
    result = await db_session.execute(
        select(FunctionDataOutput).where(
            FunctionDataOutput.protocol_run_accession_id
            == function_call_log.protocol_run.accession_id,
        ),
    )
    outputs = result.scalars().all()
    assert output.accession_id in [o.accession_id for o in outputs]


@pytest.mark.asyncio
async def test_function_data_output_orm_relationship_to_function_call_log(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test relationship to FunctionCallLog."""
    output = FunctionDataOutput(
        name="test_output_relationship_log",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    db_session.add(output)
    await db_session.flush()

    assert output.function_call_log.accession_id == function_call_log.accession_id

    # Verify via query to avoid lazy load issues
    result = await db_session.execute(
        select(FunctionDataOutput).where(
            FunctionDataOutput.function_call_log_accession_id
            == function_call_log.accession_id,
        ),
    )
    outputs = result.scalars().all()
    assert output.accession_id in [o.accession_id for o in outputs]


@pytest.mark.asyncio
async def test_function_data_output_orm_relationship_to_resource(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
    resource_asset: Resource,
) -> None:
    """Test relationship to Resource."""
    output = FunctionDataOutput(
        name="test_output_relationship_resource",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
        resource_accession_id=resource_asset.accession_id,
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    output.resource = resource_asset
    db_session.add(output)
    await db_session.flush()

    assert output.resource.accession_id == resource_asset.accession_id

    # Verify via query to avoid lazy load issues
    result = await db_session.execute(
        select(FunctionDataOutput).where(
            FunctionDataOutput.resource_accession_id == resource_asset.accession_id,
        ),
    )
    outputs = result.scalars().all()
    assert output.accession_id in [o.accession_id for o in outputs]


@pytest.mark.asyncio
async def test_function_data_output_orm_relationship_to_machine(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
    machine_asset: Machine,
) -> None:
    """Test relationship to Machine."""
    output = FunctionDataOutput(
        name="test_output_relationship_machine",
        protocol_run_accession_id=function_call_log.protocol_run_accession_id,
        function_call_log_accession_id=function_call_log.accession_id,
        machine_accession_id=machine_asset.accession_id,
    )
    output.protocol_run = function_call_log.protocol_run
    output.function_call_log = function_call_log
    output.machine = machine_asset
    db_session.add(output)
    await db_session.flush()

    assert output.machine.accession_id == machine_asset.accession_id

    # Verify via query to avoid lazy load issues
    result = await db_session.execute(
        select(FunctionDataOutput).where(
            FunctionDataOutput.machine_accession_id == machine_asset.accession_id,
        ),
    )
    outputs = result.scalars().all()
    assert output.accession_id in [o.accession_id for o in outputs]


@pytest.mark.asyncio
async def test_function_data_output_orm_query_by_data_type(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test querying outputs by data_type."""
    for data_type in DataOutputTypeEnum:
        output = FunctionDataOutput(
            name=f"test_output_{data_type.value}",
            protocol_run_accession_id=function_call_log.protocol_run_accession_id,
            function_call_log_accession_id=function_call_log.accession_id,
            data_type=data_type,
        )
        output.protocol_run = function_call_log.protocol_run
        output.function_call_log = function_call_log
        db_session.add(output)
    await db_session.flush()

    result = await db_session.execute(
        select(FunctionDataOutput).where(
            FunctionDataOutput.data_type == DataOutputTypeEnum.GENERIC_MEASUREMENT,
        ),
    )
    outputs = result.scalars().all()
    assert len(outputs) == 1
    assert outputs[0].data_type == DataOutputTypeEnum.GENERIC_MEASUREMENT


@pytest.mark.asyncio
async def test_function_data_output_orm_query_by_protocol_run(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
) -> None:
    """Test querying all outputs for a protocol run."""
    for i in range(3):
        output = FunctionDataOutput(
            name=f"test_output_{i}",
            protocol_run_accession_id=function_call_log.protocol_run_accession_id,
            function_call_log_accession_id=function_call_log.accession_id,
        )
        output.protocol_run = function_call_log.protocol_run
        output.function_call_log = function_call_log
        db_session.add(output)
    await db_session.flush()

    result = await db_session.execute(
        select(FunctionDataOutput).where(
            FunctionDataOutput.protocol_run_accession_id
            == function_call_log.protocol_run_accession_id,
        ),
    )
    outputs = result.scalars().all()
    assert len(outputs) == 3


@pytest.mark.asyncio
async def test_function_data_output_orm_query_by_resource(
    db_session: AsyncSession,
    function_call_log: FunctionCallLog,
    resource_asset: Resource,
) -> None:
    """Test querying outputs associated with a specific resource."""
    for i in range(2):
        output = FunctionDataOutput(
            name=f"test_output_{i}",
            protocol_run_accession_id=function_call_log.protocol_run_accession_id,
            function_call_log_accession_id=function_call_log.accession_id,
            resource_accession_id=resource_asset.accession_id,
        )
        output.protocol_run = function_call_log.protocol_run
        output.function_call_log = function_call_log
        output.resource = resource_asset
        db_session.add(output)
    await db_session.flush()

    result = await db_session.execute(
        select(FunctionDataOutput).where(
            FunctionDataOutput.resource_accession_id
            == resource_asset.accession_id,
        ),
    )
    outputs = result.scalars().all()
    assert len(outputs) == 2
