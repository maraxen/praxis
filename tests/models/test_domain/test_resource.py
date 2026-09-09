"""Unit tests for Resource model."""
import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from praxis.backend.models.domain.resource import (
    Resource,
    ResourceBase,
    ResourceCreate,
    ResourceDefinition,
    ResourceUpdate,
)
from praxis.backend.models.domain.resource import (
    ResourceRead as ResourceResponse,
)
from praxis.backend.models.enums import AssetType, ResourceStatusEnum


@pytest.mark.asyncio
async def test_resource_orm_creation_with_defaults(db_session: AsyncSession) -> None:
    """Test creating a Resource with default values."""
    # Create a resource definition first
    resource_def = ResourceDefinition(
        name="test_resource_def",
        fqn="test.resource.Definition",
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Create a resource with only required fields
    resource = Resource(
        name="test_resource",
        fqn="test.resource.Fqn",
        asset_type=AssetType.RESOURCE,
    )
    resource.resource_definition = resource_def
    db_session.add(resource)
    await db_session.flush()

    # Verify defaults are set
    assert resource.accession_id is not None
    assert resource.name == "test_resource"
    assert resource.fqn == "test.resource.Fqn"
    assert resource.asset_type == AssetType.RESOURCE
    assert resource.status == ResourceStatusEnum.UNKNOWN
    assert resource.resource_definition == resource_def
    assert resource.parent_accession_id is None


@pytest.mark.asyncio
async def test_resource_orm_persist_to_database(db_session: AsyncSession) -> None:
    """Test that a Resource can be persisted to the database."""
    # Create resource definition
    resource_def = ResourceDefinition(
        name="persist_def",
        fqn="test.resource.PersistDef",
    )
    db_session.add(resource_def)
    await db_session.flush()
    def_id = resource_def.accession_id

    # Create resource
    resource = Resource(
        name="test_persistence",
        fqn="test.persistence.Resource",
        asset_type=AssetType.RESOURCE,
        status=ResourceStatusEnum.AVAILABLE_IN_STORAGE,
    )
    # Set FK via relationship instead of direct FK assignment
    resource.resource_definition = resource_def

    # Add to session and flush
    db_session.add(resource)
    await db_session.flush()

    # Query back from database
    result = await db_session.execute(
        select(Resource).where(Resource.accession_id == resource.accession_id),
    )
    retrieved = result.scalars().first()

    # Verify persistence
    assert retrieved is not None
    assert retrieved.accession_id == resource.accession_id
    assert retrieved.name == "test_persistence"
    assert retrieved.fqn == "test.persistence.Resource"
    assert retrieved.status == ResourceStatusEnum.AVAILABLE_IN_STORAGE
    assert retrieved.resource_definition_accession_id == def_id


@pytest.mark.asyncio
async def test_resource_orm_unique_name_constraint(db_session: AsyncSession) -> None:
    """Test that resource names must be unique."""
    from sqlalchemy.exc import IntegrityError

    # Create resource definition
    resource_def = ResourceDefinition(
        name="unique_def",
        fqn="test.resource.UniqueDef",
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Create first resource
    resource1 = Resource(
        name="unique_resource",
        fqn="test.resource.1",
        asset_type=AssetType.RESOURCE,
    )
    resource1.resource_definition = resource_def
    db_session.add(resource1)
    await db_session.flush()

    # Try to create another with same name
    resource2 = Resource(
        name="unique_resource",  # Duplicate name
        fqn="test.resource.2",
        asset_type=AssetType.RESOURCE,
    )
    resource2.resource_definition = resource_def
    db_session.add(resource2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_resource_orm_status_enum_values(db_session: AsyncSession) -> None:
    """Test that resource status enum values are stored correctly."""
    # Create resource definition
    resource_def = ResourceDefinition(
        name="status_def",
        fqn="test.resource.StatusDef",
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Test a few key statuses
    statuses = [
        ResourceStatusEnum.AVAILABLE_IN_STORAGE,
        ResourceStatusEnum.IN_USE,
        ResourceStatusEnum.EMPTY,
        ResourceStatusEnum.UNKNOWN,
    ]

    for status in statuses:
        resource = Resource(
            name=f"resource_{status.value}",
            fqn=f"test.resource.{status.value}",
            asset_type=AssetType.RESOURCE,
            status=status,
        )
        resource.resource_definition = resource_def
        db_session.add(resource)
        await db_session.flush()

        # Verify status was set correctly
        assert resource.status == status


@pytest.mark.asyncio
async def test_resource_orm_parent_child_relationship(db_session: AsyncSession) -> None:
    """Test self-referential parent-child relationship between resources."""
    # Create resource definition
    resource_def = ResourceDefinition(
        name="hierarchy_def",
        fqn="test.resource.HierarchyDef",
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Create parent resource
    parent = Resource(
        name="parent_resource",
        fqn="test.resource.Parent",
        asset_type=AssetType.RESOURCE,
    )
    parent.resource_definition = resource_def
    db_session.add(parent)
    await db_session.flush()

    # Create child resource referencing parent
    child = Resource(
        name="child_resource",
        fqn="test.resource.Child",
        asset_type=AssetType.RESOURCE,
    )
    child.resource_definition = resource_def
    child.parent = parent
    db_session.add(child)
    await db_session.flush()

    # Query back and verify relationship
    result = await db_session.execute(
        select(Resource).where(Resource.accession_id == child.accession_id),
    )
    retrieved_child = result.scalars().first()

    assert retrieved_child is not None
    assert retrieved_child.parent_accession_id == parent.accession_id


@pytest.mark.asyncio
async def test_resource_orm_with_workcell_relationship(db_session: AsyncSession) -> None:
    """Test creating a resource with a workcell relationship."""
    from praxis.backend.models.domain.workcell import Workcell

    # Create workcell
    workcell = Workcell(
        name="test_workcell_for_resource",
    )
    db_session.add(workcell)
    await db_session.flush()

    # Create resource definition
    resource_def = ResourceDefinition(
        name="workcell_resource_def",
        fqn="test.resource.WorkcellDef",
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Create resource in workcell
    resource = Resource(
        name="resource_in_workcell",
        fqn="test.resource.InWorkcell",
        asset_type=AssetType.RESOURCE,
    )
    resource.resource_definition = resource_def
    resource.workcell = workcell
    db_session.add(resource)
    await db_session.flush()

    # Query back and verify
    result = await db_session.execute(
        select(Resource).where(Resource.accession_id == resource.accession_id),
    )
    retrieved = result.scalars().first()

    assert retrieved is not None
    assert retrieved.workcell_accession_id == workcell.accession_id


@pytest.mark.asyncio
async def test_resource_orm_plr_state_json(db_session: AsyncSession) -> None:
    """Test that resource plr_state JSONB field works correctly."""
    # Create resource definition
    resource_def = ResourceDefinition(
        name="plr_state_def",
        fqn="test.resource.PLRStateDef",
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Create resource with PLR state
    plr_state = {
        "location": {"x": 100.5, "y": 200.3, "z": 50.0},
        "rotation": {"x_deg": 0, "y_deg": 0, "z_deg": 90},
        "metadata": {"type": "plate", "barcode": "ABC123"},
    }

    resource = Resource(
        name="resource_with_plr_state",
        fqn="test.resource.WithPLRState",
        asset_type=AssetType.RESOURCE,
        plr_state=plr_state,
    )
    resource.resource_definition = resource_def

    db_session.add(resource)
    await db_session.flush()

    # Verify JSON was stored correctly
    assert resource.plr_state == plr_state
    assert resource.plr_state["location"]["x"] == 100.5
    assert resource.plr_state["metadata"]["barcode"] == "ABC123"


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestResourceSchemas:
    """Tests for Resource Pydantic schemas."""

    def test_resource_base_minimal(self) -> None:
        """Test creating a ResourceBase with minimal required fields."""
        resource = ResourceBase(
            name="test_resource",
            asset_type=AssetType.RESOURCE,
        )

        assert resource.name == "test_resource"
        assert resource.asset_type == "RESOURCE"  # Enum stored as string
        assert resource.status == ResourceStatusEnum.UNKNOWN
        assert resource.fqn is None
        assert resource.resource_definition_accession_id is None
        assert resource.parent_accession_id is None

    def test_resource_base_with_all_fields(self) -> None:
        """Test creating a ResourceBase with all fields populated."""
        from praxis.backend.utils.uuid import uuid7
        plr_state = {"location": {"x": 100, "y": 200}, "rotation": {"z_deg": 90}}

        resource = ResourceBase(
            name="full_resource",
            fqn="test.full.Resource",
            asset_type=AssetType.RESOURCE,
            status=ResourceStatusEnum.AVAILABLE_IN_STORAGE,
            status_details="Ready to use",
            resource_definition_accession_id=uuid7(),
            parent_accession_id=uuid7(),
            workcell_accession_id=uuid7(),
            plr_state=plr_state,
        )

        assert resource.name == "full_resource"
        assert resource.fqn == "test.full.Resource"
        assert resource.asset_type == "RESOURCE"
        assert resource.status == "available_in_storage"  # use_enum_values=True
        assert resource.status_details == "Ready to use"
        assert resource.resource_definition_accession_id is not None
        assert resource.parent_accession_id is not None
        assert resource.workcell_accession_id is not None
        assert resource.plr_state == plr_state

    def test_resource_create_inherits_from_base(self) -> None:
        """Test that ResourceCreate inherits all properties from ResourceBase."""
        resource = ResourceCreate(
            name="create_test",
            fqn="test.create.Resource",
            asset_type=AssetType.RESOURCE,
            status=ResourceStatusEnum.EMPTY,
        )

        assert resource.name == "create_test"
        assert resource.fqn == "test.create.Resource"
        assert resource.asset_type == "RESOURCE"
        assert resource.status == "empty"

    def test_resource_update_all_fields_optional(self) -> None:
        """Test that ResourceUpdate allows all fields to be optional."""
        # Create with minimal fields
        update = ResourceUpdate(asset_type=AssetType.RESOURCE)
        assert update.asset_type == "RESOURCE"
        assert update.name is None  # Default is None

        # Should be able to create with partial fields
        update_partial = ResourceUpdate(
            asset_type=AssetType.RESOURCE,
            name="new_name",
            status=ResourceStatusEnum.IN_USE,
        )
        assert update_partial.asset_type == "RESOURCE"
        assert update_partial.name == "new_name"
        assert update_partial.status == "in_use"

    def test_resource_response_serialization_to_dict(self) -> None:
        """Test that ResourceResponse can be serialized to a dictionary."""
        resource = ResourceResponse(
            name="serialize_test",
            fqn="test.serialize.Resource",
            asset_type=AssetType.RESOURCE,
            status=ResourceStatusEnum.AVAILABLE_ON_DECK,
        )

        data = resource.model_dump()

        assert isinstance(data, dict)
        assert data["name"] == "serialize_test"
        assert data["fqn"] == "test.serialize.Resource"
        assert data["asset_type"] == "RESOURCE"  # Enum to string
        assert data["status"] == "available_on_deck"  # Enum to string

    def test_resource_response_serialization_to_json(self) -> None:
        """Test that ResourceResponse can be serialized to JSON."""
        resource = ResourceResponse(
            name="json_test",
            fqn="test.json.Resource",
            asset_type=AssetType.RESOURCE,
            status=ResourceStatusEnum.IN_USE,
        )

        json_str = resource.model_dump_json()

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["name"] == "json_test"
        assert data["fqn"] == "test.json.Resource"
        assert data["asset_type"] == "RESOURCE"
        assert data["status"] == "in_use"

    def test_resource_response_deserialization_from_dict(self) -> None:
        """Test that ResourceResponse can be deserialized from a dictionary."""
        from praxis.backend.utils.uuid import uuid7
        data = {
            "name": "deserialize_test",
            "fqn": "test.deserialize.Resource",
            "asset_type": "RESOURCE",
            "status": "available_in_storage",
            "status_details": "From dict",
            "resource_definition_accession_id": uuid7(),
            "parent_accession_id": uuid7(),
            "accession_id": uuid7(),
            "created_at": "2025-11-10T12:00:00Z",
            "properties_json": {},
        }

        resource = ResourceResponse.model_validate(data)

        assert resource.name == "deserialize_test"
        assert resource.fqn == "test.deserialize.Resource"
        assert resource.asset_type == "RESOURCE"
        assert resource.status == "available_in_storage"
        assert resource.status_details == "From dict"
        assert resource.resource_definition_accession_id is not None
        assert resource.parent_accession_id is not None

    def test_resource_response_status_enum_validation(self) -> None:
        """Test that ResourceResponse properly validates status enum values."""
        # Valid enum value as string
        resource1 = ResourceResponse(
            name="enum_test_1",
            fqn="test.enum.1",
            asset_type=AssetType.RESOURCE,
            status="available_in_storage",
        )
        assert resource1.status == "available_in_storage"

        # Valid enum value as enum
        resource2 = ResourceResponse(
            name="enum_test_2",
            fqn="test.enum.2",
            asset_type=AssetType.RESOURCE,
            status=ResourceStatusEnum.IN_USE,
        )
        assert resource2.status == "in_use"

        # Invalid enum value should raise error
        with pytest.raises(ValueError):
            ResourceResponse(
                name="enum_test_3",
                fqn="test.enum.3",
                asset_type=AssetType.RESOURCE,
                status="invalid_status",
            )

    def test_resource_response_roundtrip_serialization(self) -> None:
        """Test that ResourceResponse can be serialized and deserialized without data loss."""
        from praxis.backend.utils.uuid import uuid7
        original = ResourceResponse(
            name="roundtrip_test",
            fqn="test.roundtrip.Resource",
            asset_type=AssetType.RESOURCE,
            status=ResourceStatusEnum.EMPTY,
            status_details="Testing roundtrip",
            resource_definition_accession_id=uuid7(),
            plr_state={"test": "data", "nested": {"value": 123}},
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize back
        restored = ResourceResponse.model_validate(data)

        # Should be equal
        assert restored.name == original.name
        assert restored.fqn == original.fqn
        assert restored.asset_type == original.asset_type
        assert restored.status == original.status
        assert restored.status_details == original.status_details
        assert restored.resource_definition_accession_id == original.resource_definition_accession_id
        assert restored.plr_state == original.plr_state

    @pytest.mark.asyncio
    async def test_resource_response_from_model(self, db_session: AsyncSession) -> None:
        """Test converting a Resource instance to ResourceResponse."""
        from praxis.backend.utils.uuid import uuid7

        # Create resource definition
        resource_def = ResourceDefinition(
            name="model_test_def",
            fqn="test.orm.Definition",
        )
        db_session.add(resource_def)
        await db_session.flush()

        # Create an ORM instance
        resource_id = uuid7()
        model_resource = Resource(
            accession_id=resource_id,
            name="model_test_resource",
            fqn="test.orm.Resource",
            asset_type=AssetType.RESOURCE,
            status=ResourceStatusEnum.AVAILABLE_IN_STORAGE,
        )
        model_resource.resource_definition = resource_def

        db_session.add(model_resource)
        await db_session.flush()

        # Refresh with eager loading for Pydantic
        stmt = (
            select(Resource)
            .where(Resource.accession_id == resource_id)
            .options(selectinload(Resource.parent), selectinload(Resource.children))
        )
        result = await db_session.execute(stmt)
        model_resource = result.scalar_one()

        # Convert ORM to Pydantic
        response = ResourceResponse.model_validate(model_resource)

        # Verify conversion
        assert response.accession_id == resource_id
        assert response.name == "model_test_resource"
        assert response.fqn == "test.orm.Resource"
        assert response.asset_type == "RESOURCE"
        assert response.status == "available_in_storage"
        assert response.resource_definition_accession_id == resource_def.accession_id

    @pytest.mark.asyncio
    async def test_resource_response_from_orm_minimal(self, db_session: AsyncSession) -> None:
        """Test ORM-to-Pydantic conversion with minimal fields."""
        from praxis.backend.utils.uuid import uuid7

        # Create resource definition
        resource_def = ResourceDefinition(
            name="minimal_def",
            fqn="test.minimal.Definition",
        )
        db_session.add(resource_def)
        await db_session.flush()

        # Create minimal ORM instance
        resource_id = uuid7()
        model_resource = Resource(
            accession_id=resource_id,
            name="minimal_resource",
            fqn="test.minimal.Resource",
            asset_type=AssetType.RESOURCE,
        )
        model_resource.resource_definition = resource_def

        db_session.add(model_resource)
        await db_session.flush()

        # Refresh with eager loading for Pydantic
        stmt = (
            select(Resource)
            .where(Resource.accession_id == resource_id)
            .options(selectinload(Resource.parent), selectinload(Resource.children))
        )
        result = await db_session.execute(stmt)
        model_resource = result.scalar_one()

        # Convert to Pydantic
        response = ResourceResponse.model_validate(model_resource)

        # Verify required fields
        assert response.accession_id == resource_id
        assert response.name == "minimal_resource"
        assert response.fqn == "test.minimal.Resource"
        assert response.asset_type == "RESOURCE"
        assert response.status == "unknown"  # Default status

        # Verify optional fields are None or default
        assert response.status_details is None
        assert response.parent_accession_id is None
