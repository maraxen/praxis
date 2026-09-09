import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.filters import SearchFilters
from praxis.backend.models.domain.protocol import (
    FunctionProtocolDefinition,
    FunctionProtocolDefinitionCreate,
    FunctionProtocolDefinitionUpdate,
)
from praxis.backend.models.domain.protocol_source import (
    FileSystemProtocolSource,
    ProtocolSourceRepository,
)
from praxis.backend.services.protocol_definition import ProtocolDefinitionCRUDService


@pytest.fixture
def protocol_definition_service() -> ProtocolDefinitionCRUDService:
    return ProtocolDefinitionCRUDService(FunctionProtocolDefinition)

@pytest.mark.asyncio
async def test_create_protocol_definition_defaults(
    db_session: AsyncSession,
    protocol_definition_service: ProtocolDefinitionCRUDService,
) -> None:
    """Test creating protocol definition with default sources."""
    create_data = FunctionProtocolDefinitionCreate(
        name="TestProtocol",
        fqn="test.protocol.run",
        source_file_path="/test/path/run.py",
        module_name="test.protocol",
        function_name="run",
    )

    created_def = await protocol_definition_service.create(db_session, obj_in=create_data)

    assert created_def.accession_id is not None
    assert created_def.name == "TestProtocol"
    assert created_def.source_repository is not None
    assert created_def.source_repository.name == "default_test_repo"
    assert created_def.file_system_source is not None
    assert created_def.file_system_source.name == "default_test_fs"

@pytest.mark.asyncio
async def test_create_protocol_definition_with_existing_sources(
    db_session: AsyncSession,
    protocol_definition_service: ProtocolDefinitionCRUDService,
) -> None:
    """Test creating protocol definition with existing sources."""
    # Create sources first
    repo = ProtocolSourceRepository(
        name="existing_repo",
        git_url="https://github.com/existing.git",
    )
    fs_source = FileSystemProtocolSource(
        name="existing_fs",
        base_path="/existing",
    )
    db_session.add(repo)
    db_session.add(fs_source)
    await db_session.flush()

    create_data = FunctionProtocolDefinitionCreate(
        name="TestProtocolExisting",
        fqn="test.protocol.existing",
        source_file_path="/existing/run.py",
        module_name="test.protocol.existing",
        function_name="run",
        source_repository_name="existing_repo",
        file_system_source_name="existing_fs",
    )

    created_def = await protocol_definition_service.create(db_session, obj_in=create_data)

    assert created_def.source_repository.name == "existing_repo"
    assert created_def.file_system_source.name == "existing_fs"

@pytest.mark.asyncio
async def test_create_protocol_definition_creates_missing_sources(
    db_session: AsyncSession,
    protocol_definition_service: ProtocolDefinitionCRUDService,
) -> None:
    """Test creating protocol definition creates missing sources if named."""
    create_data = FunctionProtocolDefinitionCreate(
        name="TestProtocolMissing",
        fqn="test.protocol.missing",
        source_file_path="/missing/run.py",
        module_name="test.protocol.missing",
        function_name="run",
        source_repository_name="missing_repo",
        file_system_source_name="missing_fs",
    )

    created_def = await protocol_definition_service.create(db_session, obj_in=create_data)

    assert created_def.source_repository.name == "missing_repo"
    assert created_def.file_system_source.name == "missing_fs"

@pytest.mark.asyncio
async def test_get_protocol_definition(
    db_session: AsyncSession,
    protocol_definition_service: ProtocolDefinitionCRUDService,
) -> None:
    """Test retrieving protocol definition."""
    create_data = FunctionProtocolDefinitionCreate(
        name="GetProtocol",
        fqn="test.protocol.get",
        source_file_path="/get/run.py",
        module_name="test.protocol.get",
        function_name="run",
    )
    created_def = await protocol_definition_service.create(db_session, obj_in=create_data)

    fetched_def = await protocol_definition_service.get(db_session, created_def.accession_id)
    assert fetched_def is not None
    assert fetched_def.accession_id == created_def.accession_id

    # Test get_by_fqn
    fqn_def = await protocol_definition_service.get_by_fqn(db_session, "test.protocol.get")
    assert fqn_def is not None
    assert fqn_def.accession_id == created_def.accession_id

    # Test get_by_name
    name_def = await protocol_definition_service.get_by_name(db_session, "GetProtocol")
    assert name_def is not None
    assert name_def.accession_id == created_def.accession_id

@pytest.mark.asyncio
async def test_get_by_name_with_filters(
    db_session: AsyncSession,
    protocol_definition_service: ProtocolDefinitionCRUDService,
) -> None:
    """Test retrieving protocol definition by name with version and commit hash."""
    create_data = FunctionProtocolDefinitionCreate(
        name="FilterProtocol",
        fqn="test.protocol.filter",
        source_file_path="/filter/run.py",
        module_name="test.protocol.filter",
        function_name="run",
        version="1.0.0",
        commit_hash="abc1234"
    )
    created_def = await protocol_definition_service.create(db_session, obj_in=create_data)

    # Test with version
    version_def = await protocol_definition_service.get_by_name(
        db_session, "FilterProtocol", version="1.0.0"
    )
    assert version_def is not None
    assert version_def.accession_id == created_def.accession_id

    # Test with wrong version
    wrong_version_def = await protocol_definition_service.get_by_name(
        db_session, "FilterProtocol", version="2.0.0"
    )
    assert wrong_version_def is None

    # Test with commit hash
    commit_def = await protocol_definition_service.get_by_name(
        db_session, "FilterProtocol", commit_hash="abc1234"
    )
    assert commit_def is not None
    assert commit_def.accession_id == created_def.accession_id

    # Test with wrong commit hash
    wrong_commit_def = await protocol_definition_service.get_by_name(
        db_session, "FilterProtocol", commit_hash="xyz9876"
    )
    assert wrong_commit_def is None

    # Test with both
    both_def = await protocol_definition_service.get_by_name(
        db_session, "FilterProtocol", version="1.0.0", commit_hash="abc1234"
    )
    assert both_def is not None

@pytest.mark.asyncio
async def test_get_multi_protocol_definitions(
    db_session: AsyncSession,
    protocol_definition_service: ProtocolDefinitionCRUDService,
) -> None:
    """Test retrieving multiple protocol definitions."""
    # Create a few definitions
    for i in range(3):
        create_data = FunctionProtocolDefinitionCreate(
            name=f"MultiProtocol{i}",
            fqn=f"test.protocol.multi{i}",
            source_file_path=f"/multi{i}/run.py",
            module_name=f"test.protocol.multi{i}",
            function_name="run",
        )
        await protocol_definition_service.create(db_session, obj_in=create_data)

    # Test get_multi without filters
    all_defs = await protocol_definition_service.get_multi(db_session, filters=SearchFilters())
    # We might have other tests running, so just check if we have at least 3
    assert len(all_defs) >= 3

    # Test get_multi with filters
    filters = SearchFilters(limit=2, offset=0)
    paged_defs = await protocol_definition_service.get_multi(db_session, filters=filters)
    assert len(paged_defs) == 2

    # Test get_multi with offset
    filters_offset = SearchFilters(limit=2, offset=2)
    offset_defs = await protocol_definition_service.get_multi(db_session, filters=filters_offset)
    assert len(offset_defs) >= 1

@pytest.mark.asyncio
async def test_update_protocol_definition(
    db_session: AsyncSession,
    protocol_definition_service: ProtocolDefinitionCRUDService,
) -> None:
    """Test updating protocol definition."""
    create_data = FunctionProtocolDefinitionCreate(
        name="UpdateProtocol",
        fqn="test.protocol.update",
        source_file_path="/update/run.py",
        module_name="test.protocol.update",
        function_name="run",
    )
    created_def = await protocol_definition_service.create(db_session, obj_in=create_data)

    update_data = FunctionProtocolDefinitionUpdate(
        description="Updated description",
    )

    updated_def = await protocol_definition_service.update(
        db_session, db_obj=created_def, obj_in=update_data,
    )

    assert updated_def.description == "Updated description"
    # Ensure relationships are loaded
    assert "parameters" in updated_def.__dict__
    assert "assets" in updated_def.__dict__
    assert "source_repository" in updated_def.__dict__
    assert "file_system_source" in updated_def.__dict__
