"""Unit tests for ResourceDefinition."""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.resource import (
    ResourceDefinition,
    ResourceDefinitionBase,
    ResourceDefinitionCreate,
    ResourceDefinitionUpdate,
)
from praxis.backend.models.domain.resource import (
    ResourceDefinitionRead as ResourceDefinitionResponse,
)


@pytest.mark.asyncio
async def test_resource_definition_orm_creation_minimal(db_session: AsyncSession) -> None:
    """Test creating ResourceDefinition with minimal required fields."""
    resource_def = ResourceDefinition(
        name="test_plate",
        fqn="test.plate.CorningPlate96",
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Verify creation
    assert resource_def.accession_id is not None
    assert resource_def.name == "test_plate"
    assert resource_def.fqn == "test.plate.CorningPlate96"
    assert resource_def.is_consumable is False  # Default
    assert resource_def.resource_type is None


@pytest.mark.asyncio
async def test_resource_definition_orm_with_all_fields(db_session: AsyncSession) -> None:
    """Test ResourceDefinition with all fields populated."""
    plr_details = {
        "class": "Plate_96_Well",
        "module": "pylabrobot.resources.corning_costar",
    }
    rotation = {"x_deg": 0, "y_deg": 0, "z_deg": 90}

    resource_def = ResourceDefinition(
        name="corning_96_wellplate",
        fqn="pylabrobot.resources.corning_costar.Costar_96_CorningWellPlate_360uL_Vb",
        resource_type="plate",
        description="96-well plate from Corning",
        is_consumable=True,
        nominal_volume_ul=360.0,
        material="polypropylene",
        manufacturer="Corning",
        plr_definition_details_json=plr_details,
        size_x_mm=127.76,
        size_y_mm=85.48,
        size_z_mm=14.35,
        model="3650",
        rotation_json=rotation,
        ordering="Corning Cat #3650",
        plr_category="plate",
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Verify all fields
    assert resource_def.name == "corning_96_wellplate"
    assert resource_def.resource_type == "plate"
    assert resource_def.is_consumable is True
    assert resource_def.nominal_volume_ul == 360.0
    assert resource_def.material == "polypropylene"
    assert resource_def.manufacturer == "Corning"
    assert resource_def.plr_definition_details_json == plr_details
    assert resource_def.size_x_mm == 127.76
    assert resource_def.size_y_mm == 85.48
    assert resource_def.size_z_mm == 14.35
    assert resource_def.model == "3650"
    assert resource_def.rotation_json == rotation
    assert resource_def.ordering == "Corning Cat #3650"
    assert resource_def.plr_category == "plate"


@pytest.mark.asyncio
async def test_resource_definition_orm_persist_to_database(db_session: AsyncSession) -> None:
    """Test full persistence cycle for ResourceDefinition."""
    from praxis.backend.utils.uuid import uuid7

    resource_def_id = uuid7()
    resource_def = ResourceDefinition(
        accession_id=resource_def_id,
        name="persistence_test_plate",
        fqn="test.persistence.Plate",
        resource_type="plate",
        is_consumable=True,
        nominal_volume_ul=200.0,
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Query back
    result = await db_session.execute(
        select(ResourceDefinition).where(
            ResourceDefinition.accession_id == resource_def_id,
        ),
    )
    retrieved = result.scalars().first()

    # Verify persistence
    assert retrieved is not None
    assert retrieved.accession_id == resource_def_id
    assert retrieved.name == "persistence_test_plate"
    assert retrieved.fqn == "test.persistence.Plate"
    assert retrieved.resource_type == "plate"
    assert retrieved.is_consumable is True
    assert retrieved.nominal_volume_ul == 200.0


@pytest.mark.asyncio
async def test_resource_definition_orm_unique_fqn_constraint(db_session: AsyncSession) -> None:
    """Test that FQN must be unique."""
    # Create first resource definition
    resource_def1 = ResourceDefinition(
        name="plate_1",
        fqn="test.unique.Plate",
    )
    db_session.add(resource_def1)
    await db_session.flush()

    # Try to create another with same FQN
    resource_def2 = ResourceDefinition(
        name="plate_2",
        fqn="test.unique.Plate",  # Duplicate FQN
    )
    db_session.add(resource_def2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_resource_definition_orm_non_unique_name(db_session: AsyncSession) -> None:
    """Test that name does NOT have to be unique."""
    # Create first resource definition
    resource_def1 = ResourceDefinition(
        name="duplicate_plate",
        fqn="test.unique.Plate1",
    )
    db_session.add(resource_def1)
    await db_session.flush()

    # Create another with same name but different FQN
    resource_def2 = ResourceDefinition(
        name="duplicate_plate",  # Duplicate name
        fqn="test.unique.Plate2",
    )
    db_session.add(resource_def2)

    # Should NOT raise IntegrityError
    await db_session.flush()

    # Verify both exist
    result = await db_session.execute(
        select(ResourceDefinition).where(ResourceDefinition.name == "duplicate_plate")
    )
    assert len(result.scalars().all()) == 2


@pytest.mark.asyncio
async def test_resource_definition_orm_jsonb_fields(db_session: AsyncSession) -> None:
    """Test JSONB field handling."""
    plr_details = {
        "num_items_x": 12,
        "num_items_y": 8,
        "well_size_x": 9.0,
        "well_size_y": 9.0,
    }
    rotation = {"x_deg": 0, "y_deg": 0, "z_deg": 180}

    resource_def = ResourceDefinition(
        name="jsonb_test_plate",
        fqn="test.jsonb.Plate",
        plr_definition_details_json=plr_details,
        rotation_json=rotation,
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Query back to verify JSONB storage
    result = await db_session.execute(
        select(ResourceDefinition).where(
            ResourceDefinition.name == "jsonb_test_plate",
        ),
    )
    retrieved = result.scalars().first()

    assert retrieved is not None
    assert retrieved.plr_definition_details_json == plr_details
    assert retrieved.plr_definition_details_json["num_items_x"] == 12
    assert retrieved.rotation_json == rotation
    assert retrieved.rotation_json["z_deg"] == 180


@pytest.mark.asyncio
async def test_resource_definition_orm_consumable_flag(db_session: AsyncSession) -> None:
    """Test is_consumable flag for different resource types."""
    # Consumable resource (tips, tubes)
    consumable = ResourceDefinition(
        name="tips_200ul",
        fqn="test.tips.Tips200uL",
        resource_type="tips",
        is_consumable=True,
    )
    db_session.add(consumable)
    await db_session.flush()

    # Non-consumable resource (plate carrier)
    non_consumable = ResourceDefinition(
        name="plate_carrier",
        fqn="test.carrier.PlateCarrier",
        resource_type="carrier",
        is_consumable=False,
    )
    db_session.add(non_consumable)
    await db_session.flush()

    # Verify
    assert consumable.is_consumable is True
    assert non_consumable.is_consumable is False


@pytest.mark.asyncio
async def test_resource_definition_orm_dimensions(db_session: AsyncSession) -> None:
    """Test physical dimension fields."""
    resource_def = ResourceDefinition(
        name="dimensioned_plate",
        fqn="test.dimensions.Plate",
        size_x_mm=127.76,
        size_y_mm=85.48,
        size_z_mm=14.35,
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Query back
    result = await db_session.execute(
        select(ResourceDefinition).where(
            ResourceDefinition.name == "dimensioned_plate",
        ),
    )
    retrieved = result.scalars().first()

    assert retrieved is not None
    assert retrieved.size_x_mm == 127.76
    assert retrieved.size_y_mm == 85.48
    assert retrieved.size_z_mm == 14.35


@pytest.mark.asyncio
async def test_resource_definition_orm_with_volume(db_session: AsyncSession) -> None:
    """Test nominal_volume_ul field for volumetric resources."""
    resource_def = ResourceDefinition(
        name="tube_1_5ml",
        fqn="test.tube.Tube1500uL",
        resource_type="tube",
        nominal_volume_ul=1500.0,
        is_consumable=True,
    )
    db_session.add(resource_def)
    await db_session.flush()

    assert resource_def.nominal_volume_ul == 1500.0
    assert resource_def.resource_type == "tube"


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestResourceDefinitionSchemas:
    """Tests for ResourceDefinition Pydantic schemas."""

    def test_resource_definition_base_minimal(self) -> None:
        """Test ResourceDefinitionBase with minimal fields."""
        resource_def = ResourceDefinitionBase(fqn="test.fqn", name="test_name")

        # Verify defaults
        assert resource_def.resource_type is None
        assert resource_def.description is None
        assert resource_def.is_consumable is False  # Default
        assert resource_def.nominal_volume_ul is None
        assert resource_def.material is None
        assert resource_def.manufacturer is None

    def test_resource_definition_base_with_all_fields(self) -> None:
        """Test ResourceDefinitionBase with all fields populated."""
        plr_details = {
            "num_items_x": 12,
            "num_items_y": 8,
        }
        rotation = {"x_deg": 0, "y_deg": 0, "z_deg": 90}

        resource_def = ResourceDefinitionBase(
            name="test_name",
            fqn="test.fqn",
            resource_type="plate",
            description="96-well microplate",
            is_consumable=True,
            nominal_volume_ul=200.0,
            material="polystyrene",
            manufacturer="Corning",
            plr_definition_details_json=plr_details,
            size_x_mm=127.76,
            size_y_mm=85.48,
            size_z_mm=14.35,
            model="3650",
            plr_category="plate",
            rotation_json=rotation,
            ordering="Cat #3650",
        )

        assert resource_def.resource_type == "plate"
        assert resource_def.description == "96-well microplate"
        assert resource_def.is_consumable is True
        assert resource_def.nominal_volume_ul == 200.0
        assert resource_def.material == "polystyrene"
        assert resource_def.manufacturer == "Corning"
        assert resource_def.plr_definition_details_json == plr_details
        assert resource_def.size_x_mm == 127.76
        assert resource_def.model == "3650"
        assert resource_def.rotation_json == rotation

    def test_resource_definition_create(self) -> None:
        """Test ResourceDefinitionCreate model."""
        resource_def = ResourceDefinitionCreate(
            name="test_plate",
            fqn="test.plate.TestPlate",
            resource_type="plate",
            is_consumable=True,
            nominal_volume_ul=300.0,
        )

        assert resource_def.name == "test_plate"
        assert resource_def.fqn == "test.plate.TestPlate"
        assert resource_def.resource_type == "plate"
        assert resource_def.is_consumable is True
        assert resource_def.nominal_volume_ul == 300.0

    def test_resource_definition_update(self) -> None:
        """Test ResourceDefinitionUpdate model."""
        # Update requires fqn but other fields are optional
        update = ResourceDefinitionUpdate(fqn="test.update.Plate")

        assert update.fqn == "test.update.Plate"
        assert update.resource_type is None
        assert update.description is None

        # Can update specific fields
        update_partial = ResourceDefinitionUpdate(
            fqn="test.update.Plate2",
            description="Updated description",
            material="polypropylene",
            size_x_mm=130.0,
        )

        assert update_partial.fqn == "test.update.Plate2"
        assert update_partial.description == "Updated description"
        assert update_partial.material == "polypropylene"
        assert update_partial.size_x_mm == 130.0

    def test_resource_definition_response_serialization_to_dict(self) -> None:
        """Test ResourceDefinitionResponse serialization to dict."""
        from praxis.backend.utils.uuid import uuid7

        resource_id = uuid7()
        response = ResourceDefinitionResponse(
            accession_id=resource_id,
            name="response_plate",
            fqn="test.response.Plate",
            resource_type="plate",
            is_consumable=True,
            nominal_volume_ul=200.0,
            material="polystyrene",
        )

        resource_dict = response.model_dump()

        assert resource_dict["accession_id"] == resource_id
        assert resource_dict["name"] == "response_plate"
        assert resource_dict["fqn"] == "test.response.Plate"
        assert resource_dict["resource_type"] == "plate"
        assert resource_dict["is_consumable"] is True
        assert resource_dict["nominal_volume_ul"] == 200.0
        assert resource_dict["material"] == "polystyrene"

    def test_resource_definition_response_serialization_to_json(self) -> None:
        """Test ResourceDefinitionResponse serialization to JSON."""
        from praxis.backend.utils.uuid import uuid7

        response = ResourceDefinitionResponse(
            accession_id=uuid7(),
            name="json_plate",
            fqn="test.json.Plate",
            resource_type="plate",
        )

        json_str = response.model_dump_json()

        assert isinstance(json_str, str)
        assert "json_plate" in json_str
        assert "test.json.Plate" in json_str

    def test_resource_definition_response_deserialization_from_dict(self) -> None:
        """Test creating ResourceDefinitionResponse from dict."""
        from praxis.backend.utils.uuid import uuid7

        resource_id = uuid7()
        resource_data = {
            "accession_id": resource_id,
            "name": "deserialized_plate",
            "fqn": "test.deserialized.Plate",
            "resource_type": "plate",
            "is_consumable": True,
            "nominal_volume_ul": 250.0,
        }

        response = ResourceDefinitionResponse(**resource_data)

        assert response.accession_id == resource_id
        assert response.name == "deserialized_plate"
        assert response.fqn == "test.deserialized.Plate"
        assert response.resource_type == "plate"
        assert response.nominal_volume_ul == 250.0

    def test_resource_definition_response_roundtrip_serialization(self) -> None:
        """Test ResourceDefinitionResponse survives serialization round-trip."""
        from praxis.backend.utils.uuid import uuid7

        original = ResourceDefinitionResponse(
            accession_id=uuid7(),
            name="roundtrip_plate",
            fqn="test.roundtrip.Plate",
            resource_type="plate",
            is_consumable=True,
            nominal_volume_ul=300.0,
            size_x_mm=127.76,
            size_y_mm=85.48,
        )

        # Serialize to dict and back
        resource_dict = original.model_dump()
        restored = ResourceDefinitionResponse(**resource_dict)

        assert restored.accession_id == original.accession_id
        assert restored.name == original.name
        assert restored.fqn == original.fqn
        assert restored.resource_type == original.resource_type
        assert restored.nominal_volume_ul == original.nominal_volume_ul
        assert restored.size_x_mm == original.size_x_mm

    @pytest.mark.asyncio
    async def test_resource_definition_response_from_model(self, db_session: AsyncSession) -> None:
        """Test converting ResourceDefinition to ResourceDefinitionResponse."""
        plr_details = {"num_items": 96}
        rotation = {"x_deg": 0, "y_deg": 0, "z_deg": 0}

        # Create ORM instance
        model_resource_def = ResourceDefinition(
            name="model_test_plate",
            fqn="test.orm.Plate",
            resource_type="plate",
            description="Test plate from ORM",
            is_consumable=True,
            nominal_volume_ul=200.0,
            material="polystyrene",
            manufacturer="Test Corp",
            plr_definition_details_json=plr_details,
            size_x_mm=127.76,
            size_y_mm=85.48,
            size_z_mm=14.35,
            model="TEST-96",
            rotation_json=rotation,
            plr_category="plate",
        )

        db_session.add(model_resource_def)
        await db_session.flush()

        # Convert to Pydantic
        response = ResourceDefinitionResponse.model_validate(model_resource_def)

        # Verify conversion
        assert response.accession_id == model_resource_def.accession_id
        assert response.name == "model_test_plate"
        assert response.fqn == "test.orm.Plate"
        assert response.resource_type == "plate"
        assert response.description == "Test plate from ORM"
        assert response.is_consumable is True
        assert response.nominal_volume_ul == 200.0
        assert response.material == "polystyrene"
        assert response.manufacturer == "Test Corp"
        assert response.plr_definition_details_json == plr_details
        assert response.size_x_mm == 127.76
        assert response.size_y_mm == 85.48
        assert response.size_z_mm == 14.35
        assert response.model == "TEST-96"
        assert response.rotation_json == rotation
        assert response.plr_category == "plate"

    @pytest.mark.asyncio
    async def test_resource_definition_response_from_orm_minimal(self, db_session: AsyncSession) -> None:
        """Test ORM-to-Pydantic conversion with minimal fields."""
        model_resource_def = ResourceDefinition(
            name="minimal_plate",
            fqn="test.minimal.Plate",
        )

        db_session.add(model_resource_def)
        await db_session.flush()

        # Convert to Pydantic
        response = ResourceDefinitionResponse.model_validate(model_resource_def)

        # Verify
        assert response.accession_id == model_resource_def.accession_id
        assert response.name == "minimal_plate"
        assert response.fqn == "test.minimal.Plate"
        assert response.resource_type is None
        assert response.description is None
        assert response.is_consumable is False  # ORM default

    def test_resource_definition_jsonb_validation(self) -> None:
        """Test JSONB field validation in Pydantic models."""
        plr_details = {
            "num_items_x": 12,
            "num_items_y": 8,
            "well_spacing_x": 9.0,
            "well_spacing_y": 9.0,
        }

        resource_def = ResourceDefinitionCreate(
            name="jsonb_test",
            fqn="test.jsonb.Plate",
            plr_definition_details_json=plr_details,
        )

        assert resource_def.plr_definition_details_json == plr_details
        assert resource_def.plr_definition_details_json["num_items_x"] == 12

    def test_resource_definition_consumable_types(self) -> None:
        """Test is_consumable flag for different resource types."""
        # Tips - consumable
        tips = ResourceDefinitionCreate(
            name="tips_200ul",
            fqn="test.tips.200uL",
            resource_type="tips",
            is_consumable=True,
        )
        assert tips.is_consumable is True

        # Plate carrier - not consumable
        carrier = ResourceDefinitionCreate(
            name="plate_carrier",
            fqn="test.carrier.PlateCarrier",
            resource_type="carrier",
            is_consumable=False,
        )
        assert carrier.is_consumable is False

    def test_resource_definition_physical_dimensions(self) -> None:
        """Test physical dimension fields."""
        resource_def = ResourceDefinitionCreate(
            name="dimensioned_plate",
            fqn="test.dimensions.Plate",
            size_x_mm=127.76,
            size_y_mm=85.48,
            size_z_mm=14.35,
        )

        assert resource_def.size_x_mm == 127.76
        assert resource_def.size_y_mm == 85.48
        assert resource_def.size_z_mm == 14.35
