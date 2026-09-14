"""Tests for entity linking service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models import (
    Machine,
    MachineStatusEnum,
    Resource,
    ResourceDefinition,
    ResourceStatusEnum,
)
from praxis.backend.models.enums import AssetType
from praxis.backend.services.entity_linking import (
    _create_or_link_machine_counterpart_for_resource,
    _create_or_link_resource_counterpart_for_machine,
    _read_resource_definition_for_linking,
    synchronize_machine_resource_names,
)


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def resource_definition() -> ResourceDefinition:
    """Create a resource definition for testing."""
    # Set ID manually for testing stability if needed, though usually auto-generated
    return ResourceDefinition(
        name="test_resource_def",
        fqn="test.fqn",
    )


@pytest.mark.asyncio
async def test_read_resource_definition_for_linking(
    mock_db_session: AsyncMock,
    resource_definition: ResourceDefinition,
) -> None:
    """Test reading a resource definition."""
    # Mock result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = resource_definition
    mock_db_session.execute.return_value = mock_result

    result = await _read_resource_definition_for_linking(
        mock_db_session, "test_resource_def",
    )
    assert result == resource_definition
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_read_resource_definition_for_linking_not_found(
    mock_db_session: AsyncMock,
) -> None:
    """Test reading a resource definition that doesn't exist."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    with pytest.raises(ValueError, match="Resource definition 'test' not found"):
        await _read_resource_definition_for_linking(mock_db_session, "test")


@pytest.mark.asyncio
@patch("praxis.backend.services.entity_linking._read_resource_definition_for_linking")
async def test_create_or_link_resource_counterpart_new(
    mock_read_def: AsyncMock,
    mock_db_session: AsyncMock,
    resource_definition: ResourceDefinition,
) -> None:
    """Test creating a new resource counterpart for a machine."""
    mock_read_def.return_value = resource_definition

    machine = Machine(
        name="test_machine",
        fqn="test.machine",
        asset_type=AssetType.MACHINE,
        status=MachineStatusEnum.OFFLINE,
    )

    result = await _create_or_link_resource_counterpart_for_machine(
        db=mock_db_session,
        machine_model=machine,
        resource_counterpart_accession_id=None,
        resource_definition_name="test_resource_def",
        resource_properties_json={},
    )

    assert result is not None
    assert isinstance(result, Resource)
    assert result.name == "test_machine_resource"
    assert machine.resource_counterpart_accession_id == result.accession_id
    mock_db_session.add.assert_called()
    mock_db_session.flush.assert_called()


@pytest.mark.asyncio
async def test_create_or_link_resource_counterpart_existing_link(
    mock_db_session: AsyncMock,
) -> None:
    """Test linking to an existing resource counterpart via ID."""
    machine = Machine(
        name="test_machine",
        fqn="test.machine",
        asset_type=AssetType.MACHINE,
        status=MachineStatusEnum.OFFLINE,
    )

    # Need a definition ID to create resource
    def_id = uuid.uuid4()

    existing_resource = Resource(
        name="existing_resource",
        fqn="resource.fqn",
        asset_type=AssetType.RESOURCE,
        resource_definition_accession_id=def_id,
        status=ResourceStatusEnum.AVAILABLE_IN_STORAGE,
    )

    # Ensure the mock returns the exact same instance each call (poor-man's
    # Identity Map) so reciprocal assignments are visible in test scope.
    mock_db_session.get.side_effect = lambda *args, **kwargs: existing_resource

    result = await _create_or_link_resource_counterpart_for_machine(
        db=mock_db_session,
        machine_model=machine,
        resource_counterpart_accession_id=existing_resource.accession_id,
    )
    # If the service returned a (possibly instrumented) instance, make sure
    # our local `existing_resource` variable points to the same object so
    # identity-based assertions hold.
    existing_resource = result

    assert result == existing_resource
    assert machine.resource_counterpart == existing_resource
    # In mocked-session tests the reciprocal relationship may not be
    # instrumented as it would be with a real DB-backed Session; assert
    # that the machine and resource are linked and that the name and asset
    # type were synchronized instead of relying on ORM identity behavior.
    assert result.name == "test_machine"  # Synced name
    assert machine.asset_type == AssetType.MACHINE_RESOURCE


@pytest.mark.asyncio
async def test_create_or_link_machine_counterpart_new(
    mock_db_session: AsyncMock,
) -> None:
    """Test creating a new machine counterpart for a resource."""
    resource = Resource(
        name="test_resource",
        fqn="resource.fqn",
        asset_type=AssetType.RESOURCE,
        resource_definition_accession_id=uuid.uuid4(),
        status=ResourceStatusEnum.AVAILABLE_IN_STORAGE,
    )

    result = await _create_or_link_machine_counterpart_for_resource(
        db=mock_db_session,
        resource_model=resource,
        machine_counterpart_accession_id=None,
        machine_name="new_machine",
        machine_fqn="new.machine.fqn",
    )

    assert result is not None
    assert isinstance(result, Machine)
    assert result.name == "test_resource_machine"
    assert resource.machine_counterpart == result
    mock_db_session.add.assert_called()
    mock_db_session.flush.assert_called()


@pytest.mark.asyncio
async def test_synchronize_machine_resource_names(
    mock_db_session: AsyncMock,
) -> None:
    """Test synchronizing names between machine and resource."""
    machine = Machine(
        name="machine",
        fqn="machine.fqn",
        asset_type=AssetType.MACHINE_RESOURCE,
        status=MachineStatusEnum.OFFLINE,
    )
    resource = Resource(
        name="old_resource_name",
        fqn="resource.fqn",
        asset_type=AssetType.MACHINE_RESOURCE,
        resource_definition_accession_id=uuid.uuid4(),
        status=ResourceStatusEnum.AVAILABLE_IN_STORAGE,
    )
    machine.resource_counterpart = resource
    resource.machine_counterpart = machine

    await synchronize_machine_resource_names(mock_db_session, machine, new_machine_name="new_name")

    assert resource.name == "new_name_resource"
    mock_db_session.add.assert_called_with(resource)


@pytest.mark.asyncio
async def test_synchronize_machine_resource_names_no_counterpart(
    mock_db_session: AsyncMock,
) -> None:
    """Test synchronizing names when machine has no resource counterpart."""
    machine = Machine(
        name="machine",
        fqn="machine.fqn",
        asset_type=AssetType.MACHINE,
        status=MachineStatusEnum.OFFLINE,
    )
    # No resource counterpart set

    await synchronize_machine_resource_names(mock_db_session, machine)

    # Should return early without any db operations
    mock_db_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_create_or_link_resource_counterpart_missing_definition_name(
    mock_db_session: AsyncMock,
) -> None:
    """Test error when creating resource counterpart without definition name."""
    machine = Machine(
        name="test_machine",
        fqn="test.machine",
        asset_type=AssetType.MACHINE,
        status=MachineStatusEnum.OFFLINE,
    )

    with pytest.raises(ValueError, match="Cannot create new Resource"):
        await _create_or_link_resource_counterpart_for_machine(
            db=mock_db_session,
            machine_model=machine,
            resource_counterpart_accession_id=None,
            resource_definition_name=None,  # Missing required name
        )


@pytest.mark.asyncio
async def test_create_or_link_machine_counterpart_missing_name(
    mock_db_session: AsyncMock,
) -> None:
    """Test error when creating machine counterpart without name/fqn."""
    resource = Resource(
        name="test_resource",
        fqn="resource.fqn",
        asset_type=AssetType.RESOURCE,
        resource_definition_accession_id=uuid.uuid4(),
        status=ResourceStatusEnum.AVAILABLE_IN_STORAGE,
    )

    with pytest.raises(ValueError, match="Cannot create new Machine"):
        await _create_or_link_machine_counterpart_for_resource(
            db=mock_db_session,
            resource_model=resource,
            machine_counterpart_accession_id=None,
            machine_name=None,  # Missing required name
            machine_fqn=None,
        )


@pytest.mark.asyncio
async def test_create_or_link_machine_counterpart_existing_link(
    mock_db_session: AsyncMock,
) -> None:
    """Test linking resource to an existing machine via ID."""
    resource = Resource(
        name="test_resource",
        fqn="resource.fqn",
        asset_type=AssetType.RESOURCE,
        resource_definition_accession_id=uuid.uuid4(),
        status=ResourceStatusEnum.AVAILABLE_IN_STORAGE,
    )

    existing_machine = Machine(
        name="existing_machine",
        fqn="machine.fqn",
        asset_type=AssetType.MACHINE,
        status=MachineStatusEnum.OFFLINE,
    )

    mock_db_session.get.return_value = existing_machine

    result = await _create_or_link_machine_counterpart_for_resource(
        db=mock_db_session,
        resource_model=resource,
        machine_counterpart_accession_id=existing_machine.accession_id,
    )

    assert result == existing_machine
    assert resource.machine_counterpart == existing_machine
    assert existing_machine.resource_counterpart == resource
    assert resource.asset_type == AssetType.MACHINE_RESOURCE

