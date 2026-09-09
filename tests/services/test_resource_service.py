"""Unit tests for ResourceService.

Tests cover all CRUD operations and resource-specific functionality.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.filters import SearchFilters
from praxis.backend.models.domain.resource import (
    Resource,
    ResourceCreate,
    ResourceDefinition,
    ResourceUpdate,
)
from praxis.backend.models.enums import AssetType, ResourceStatusEnum
from praxis.backend.services.resource import resource_service


async def create_resource_definition(
    db: AsyncSession,
    name: str = "Test Definition",
) -> ResourceDefinition:
    """Helper to create a resource definition."""
    definition = ResourceDefinition(
        name=name,
        fqn=f"com.example.{name.replace(' ', '')}",
        resource_type="Generic",
    )
    return await resource_service.create_definition(db, obj_in=definition)


@pytest.mark.asyncio
async def test_resource_service_create_resource(db_session: AsyncSession) -> None:
    """Test creating a new resource with all common fields."""
    resource_data = ResourceCreate(
        name="test_plate_1",
        fqn="resources.plates.test_plate_1",
        asset_type=AssetType.RESOURCE,
        status=ResourceStatusEnum.AVAILABLE_IN_STORAGE,
        location="Shelf A",
    )

    resource = await resource_service.create(db_session, obj_in=resource_data)

    # Verify resource was created
    assert resource.name == "test_plate_1"
    assert resource.fqn == "resources.plates.test_plate_1"
    assert resource.asset_type == AssetType.RESOURCE
    assert resource.status == ResourceStatusEnum.AVAILABLE_IN_STORAGE
    assert resource.location == "Shelf A"
    assert resource.accession_id is not None


@pytest.mark.asyncio
async def test_resource_service_create_resource_minimal(db_session: AsyncSession) -> None:
    """Test creating resource with only required fields."""
    resource_data = ResourceCreate(
        name="minimal_resource",
        fqn="resources.minimal",
        asset_type=AssetType.RESOURCE,
    )

    resource = await resource_service.create(db_session, obj_in=resource_data)

    assert resource.name == "minimal_resource"
    assert resource.fqn == "resources.minimal"
    assert resource.status == ResourceStatusEnum.UNKNOWN  # Default
    assert resource.accession_id is not None


@pytest.mark.asyncio
async def test_resource_service_create_duplicate_name(db_session: AsyncSession) -> None:
    """Test that creating resource with duplicate name fails."""
    resource_data1 = ResourceCreate(
        name="duplicate_resource",
        fqn="resources.duplicate1",
        asset_type=AssetType.RESOURCE,
    )
    await resource_service.create(db_session, obj_in=resource_data1)

    # Try to create another resource with same name
    resource_data2 = ResourceCreate(
        name="duplicate_resource",  # Same name
        fqn="resources.duplicate2",
        asset_type=AssetType.RESOURCE,
    )

    with pytest.raises(ValueError, match="Database integrity error"):
        await resource_service.create(db_session, obj_in=resource_data2)


@pytest.mark.asyncio
async def test_resource_service_get_by_id(db_session: AsyncSession) -> None:
    """Test retrieving resource by ID."""
    resource_data = ResourceCreate(
        name="getbyid_resource",
        fqn="resources.getbyid",
        asset_type=AssetType.RESOURCE,
    )
    created_resource = await resource_service.create(db_session, obj_in=resource_data)

    # Retrieve by ID
    retrieved_resource = await resource_service.get(db_session, created_resource.accession_id)

    assert retrieved_resource is not None
    assert retrieved_resource.accession_id == created_resource.accession_id
    assert retrieved_resource.name == "getbyid_resource"


@pytest.mark.asyncio
async def test_resource_service_get_by_id_not_found(db_session: AsyncSession) -> None:
    """Test retrieving non-existent resource returns None."""
    from praxis.backend.utils.uuid import uuid7

    non_existent_id = uuid7()
    resource = await resource_service.get(db_session, non_existent_id)

    assert resource is None


@pytest.mark.asyncio
async def test_resource_service_get_by_name(db_session: AsyncSession) -> None:
    """Test retrieving resource by name."""
    resource_data = ResourceCreate(
        name="findme_resource",
        fqn="resources.findme",
        asset_type=AssetType.RESOURCE,
    )
    await resource_service.create(db_session, obj_in=resource_data)

    # Retrieve by name
    resource = await resource_service.get_by_name(db_session, "findme_resource")

    assert resource is not None
    assert resource.name == "findme_resource"
    assert resource.fqn == "resources.findme"


@pytest.mark.asyncio
async def test_resource_service_get_multi(db_session: AsyncSession) -> None:
    """Test listing multiple resources with pagination."""
    # Create several resources
    for i in range(5):
        resource_data = ResourceCreate(
            name=f"resource_{i}",
            fqn=f"resources.test.resource_{i}",
            asset_type=AssetType.RESOURCE,
        )
        await resource_service.create(db_session, obj_in=resource_data)

    # Get all resources
    filters = SearchFilters(skip=0, limit=10)
    resources = await resource_service.get_multi(db_session, filters=filters)

    assert len(resources) == 5
    assert resources[0].name == "resource_0"  # Ordered by name


@pytest.mark.asyncio
async def test_resource_service_update_resource(db_session: AsyncSession) -> None:
    """Test updating resource information."""
    # Create resource
    resource_data = ResourceCreate(
        name="update_test",
        fqn="resources.update",
        asset_type=AssetType.RESOURCE,
        status=ResourceStatusEnum.AVAILABLE_IN_STORAGE,
    )
    resource = await resource_service.create(db_session, obj_in=resource_data)

    # Update resource
    update_data = ResourceUpdate(
        name="update_test",  # Keep same name
        fqn="resources.update",  # Keep same fqn
        asset_type=AssetType.RESOURCE,
        status=ResourceStatusEnum.IN_USE,
        location="Machine 1",
    )
    updated_resource = await resource_service.update(
        db_session,
        db_obj=resource,
        obj_in=update_data,
    )

    assert updated_resource.status == ResourceStatusEnum.IN_USE
    assert updated_resource.location == "Machine 1"
    assert updated_resource.accession_id == resource.accession_id


@pytest.mark.asyncio
async def test_resource_service_update_partial(db_session: AsyncSession) -> None:
    """Test partial update (only some fields)."""
    # Create resource
    resource_data = ResourceCreate(
        name="partial_update",
        fqn="resources.partial",
        asset_type=AssetType.RESOURCE,
        location="Shelf A",
    )
    resource = await resource_service.create(db_session, obj_in=resource_data)
    original_location = resource.location

    # Update only status
    update_data = ResourceUpdate(
        name="partial_update",
        fqn="resources.partial",
        asset_type=AssetType.RESOURCE,
        status=ResourceStatusEnum.IN_USE,
    )
    updated_resource = await resource_service.update(
        db_session,
        db_obj=resource,
        obj_in=update_data,
    )

    assert updated_resource.status == ResourceStatusEnum.IN_USE
    assert updated_resource.location == original_location  # Unchanged


@pytest.mark.asyncio
async def test_resource_service_remove_resource(db_session: AsyncSession) -> None:
    """Test deleting a resource."""
    # Create resource
    resource_data = ResourceCreate(
        name="delete_me",
        fqn="resources.delete",
        asset_type=AssetType.RESOURCE,
    )
    resource = await resource_service.create(db_session, obj_in=resource_data)
    resource_id = resource.accession_id

    # Delete resource
    deleted_resource = await resource_service.remove(db_session, accession_id=resource_id)

    assert deleted_resource is not None
    assert deleted_resource.accession_id == resource_id

    # Verify it's deleted
    retrieved = await resource_service.get(db_session, resource_id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_resource_service_remove_nonexistent(db_session: AsyncSession) -> None:
    """Test deleting non-existent resource returns None."""
    from praxis.backend.utils.uuid import uuid7

    non_existent_id = uuid7()
    result = await resource_service.remove(db_session, accession_id=non_existent_id)

    assert result is None


@pytest.mark.asyncio
async def test_resource_service_with_resource_definition(db_session: AsyncSession) -> None:
    """Test creating resource linked to a resource definition.

    Note: This test is simplified since ResourceDefinition creation
    is complex. We'll just test that the field can be set.
    """
    from praxis.backend.models.domain import ResourceDefinition

    # Create a real resource definition
    res_def = ResourceDefinition(
        name="test_def",
        fqn="test.def",
    )
    db_session.add(res_def)
    await db_session.flush()

    resource_data = ResourceCreate(
        name="with_definition",
        fqn="resources.with_def",
        asset_type=AssetType.RESOURCE,
        resource_definition_accession_id=res_def.accession_id,
    )

    resource = await resource_service.create(db_session, obj_in=resource_data)

    assert resource.resource_definition_accession_id == res_def.accession_id


@pytest.mark.asyncio
async def test_resource_service_parent_child_relationship(db_session: AsyncSession) -> None:
    """Test parent-child resource relationships."""
    # Create parent resource
    parent_data = ResourceCreate(
        name="parent_plate",
        fqn="resources.parent",
        asset_type=AssetType.RESOURCE,
    )
    parent = await resource_service.create(db_session, obj_in=parent_data)

    # Create child resource
    child_data = ResourceCreate(
        name="child_well",
        fqn="resources.child",
        asset_type=AssetType.RESOURCE,
        parent_accession_id=parent.accession_id,
    )
    child = await resource_service.create(db_session, obj_in=child_data)

    # Retrieve parent with children loaded
    # Expire session to ensure relationship is re-fetched
    parent_id = parent.accession_id
    db_session.expire_all()
    parent_retrieved = await resource_service.get(db_session, parent_id)

    assert child.parent_accession_id == parent_id
    assert parent_retrieved is not None
    # Children relationship is loaded via selectinload in service.get()
    assert len(parent_retrieved.children) == 1
    assert parent_retrieved.children[0].accession_id == child.accession_id


@pytest.mark.asyncio
async def test_resource_service_plr_state_management(db_session: AsyncSession) -> None:
    """Test managing PLR state for resources."""
    # Create resource with PLR state
    plr_state = {
        "volume_ul": 100.0,
        "concentration_ng_ul": 50.0,
        "positions": [[1, 2], [3, 4]],
    }
    resource_data = ResourceCreate(
        name="stateful_resource",
        fqn="resources.stateful",
        asset_type=AssetType.RESOURCE,
        plr_state=plr_state,
    )

    resource = await resource_service.create(db_session, obj_in=resource_data)

    # Verify state was stored
    assert resource.plr_state is not None
    assert resource.plr_state["volume_ul"] == 100.0
    assert resource.plr_state["concentration_ng_ul"] == 50.0
    assert resource.plr_state["positions"] == [[1, 2], [3, 4]]

    # Update state
    new_state = {
        "volume_ul": 75.0,
        "concentration_ng_ul": 45.0,
    }
    update_data = ResourceUpdate(
        name="stateful_resource",
        fqn="resources.stateful",
        asset_type=AssetType.RESOURCE,
        plr_state=new_state,
    )
    updated = await resource_service.update(db_session, db_obj=resource, obj_in=update_data)

    assert updated.plr_state["volume_ul"] == 75.0
    assert updated.plr_state["concentration_ng_ul"] == 45.0


@pytest.mark.asyncio
async def test_resource_service_singleton_instance(db_session: AsyncSession) -> None:
    """Test that resource_service is a singleton instance."""
    from praxis.backend.services.resource import ResourceService

    assert isinstance(resource_service, ResourceService)
    assert resource_service.model == Resource


@pytest.mark.asyncio
async def test_resource_service_update_resource_location_and_status(db_session: AsyncSession) -> None:
    """Test updating resource location and status."""
    resource_data = ResourceCreate(
        name="loc_status_test",
        fqn="resources.loc_status",
        asset_type=AssetType.RESOURCE,
        status=ResourceStatusEnum.AVAILABLE_IN_STORAGE,
        location="Shelf A",
    )
    resource = await resource_service.create(db_session, obj_in=resource_data)

    # Update location and status
    updated = await resource_service.update_resource_location_and_status(
        db_session,
        resource_accession_id=resource.accession_id,
        new_status=ResourceStatusEnum.IN_USE,
        status_details="In use by robot",
        current_deck_position_name="Slot 1"
    )

    assert updated is not None
    assert updated.status == ResourceStatusEnum.IN_USE
    assert updated.status_details == "In use by robot"
    assert updated.current_deck_position_name == "Slot 1"
    assert updated.accession_id == resource.accession_id

    # Verify persistence
    refetched = await resource_service.get(db_session, resource.accession_id)
    assert refetched.status == ResourceStatusEnum.IN_USE
    assert refetched.status_details == "In use by robot"
    assert refetched.current_deck_position_name == "Slot 1"


@pytest.mark.asyncio
async def test_resource_service_update_location_and_status_not_found(db_session: AsyncSession) -> None:
    """Test updating location/status for non-existent resource."""
    from praxis.backend.utils.uuid import uuid7
    non_existent_id = uuid7()

    result = await resource_service.update_resource_location_and_status(
        db_session,
        resource_accession_id=non_existent_id,
        new_status=ResourceStatusEnum.IN_USE
    )

    assert result is None


@pytest.mark.asyncio
async def test_resource_service_get_multi_filters_extended(db_session: AsyncSession) -> None:
    """Test get_multi with extended filters (parent, fqn, status)."""
    # Create parent
    parent = await resource_service.create(db_session, obj_in=ResourceCreate(
        name="parent_filter", fqn="resources.parent_filter", asset_type=AssetType.RESOURCE
    ))

    # Create child
    child = await resource_service.create(db_session, obj_in=ResourceCreate(
        name="child_filter", fqn="resources.child_filter", asset_type=AssetType.RESOURCE,
        parent_accession_id=parent.accession_id
    ))

    # Create another independent resource
    await resource_service.create(db_session, obj_in=ResourceCreate(
        name="other_filter", fqn="resources.other_filter", asset_type=AssetType.RESOURCE,
        status=ResourceStatusEnum.IN_USE
    ))

    # 1. Filter by parent_accession_id
    filters_parent = SearchFilters(parent_accession_id=parent.accession_id)
    results_parent = await resource_service.get_multi(db_session, filters=filters_parent)
    assert len(results_parent) == 1
    assert results_parent[0].accession_id == child.accession_id

    # 2. Filter by fqn
    results_fqn = await resource_service.get_multi(db_session, filters=SearchFilters(), fqn="resources.other_filter")
    assert len(results_fqn) == 1
    assert results_fqn[0].name == "other_filter"

    # 3. Filter by status
    results_status = await resource_service.get_multi(db_session, filters=SearchFilters(), status=ResourceStatusEnum.IN_USE)
    # Note: test database might have other items, so check if 'other_filter' is in results
    names = [r.name for r in results_status]
    assert "other_filter" in names
