"""Unit tests for MachineDefinition."""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.machine import (
    MachineDefinition,
    MachineDefinitionBase,
    MachineDefinitionCreate,
    MachineDefinitionUpdate,
)
from praxis.backend.models.domain.machine import (
    MachineDefinitionRead as MachineDefinitionResponse,
)
from praxis.backend.models.enums import MachineCategoryEnum


@pytest.mark.asyncio
async def test_machine_definition_orm_creation_minimal(db_session: AsyncSession) -> None:
    """Test creating MachineDefinition with minimal required fields."""
    machine_def = MachineDefinition(
        name="test_liquid_handler",
        fqn="test.machine.LiquidHandler",
    )
    db_session.add(machine_def)
    await db_session.flush()

    # Verify creation
    assert machine_def.accession_id is not None
    assert machine_def.name == "test_liquid_handler"
    assert machine_def.fqn == "test.machine.LiquidHandler"
    assert machine_def.machine_category == MachineCategoryEnum.UNKNOWN  # Default
    assert machine_def.material is None


@pytest.mark.asyncio
async def test_machine_definition_orm_with_all_fields(db_session: AsyncSession) -> None:
    """Test MachineDefinition with all fields populated."""
    plr_details = {
        "backend_class": "STAR",
        "module": "pylabrobot.liquid_handling.backends.hamilton",
    }
    rotation = {"x_deg": 0, "y_deg": 0, "z_deg": 0}
    setup_method = {
        "method_name": "setup",
        "params": {"simulate": True},
    }

    machine_def = MachineDefinition(
        name="hamilton_star",
        fqn="pylabrobot.liquid_handling.backends.hamilton.STAR",
        machine_category=MachineCategoryEnum.LIQUID_HANDLER,
        description="Hamilton STAR liquid handler",
        material="stainless_steel",
        manufacturer="Hamilton",
        plr_definition_details_json=plr_details,
        size_x_mm=1600.0,
        size_y_mm=900.0,
        size_z_mm=800.0,
        model="STAR",
        rotation_json=rotation,
        plr_category="liquid_handler",
        has_deck=True,
        setup_method_json=setup_method,
    )
    db_session.add(machine_def)
    await db_session.flush()

    # Verify all fields
    assert machine_def.name == "hamilton_star"
    assert machine_def.machine_category == MachineCategoryEnum.LIQUID_HANDLER
    assert machine_def.description == "Hamilton STAR liquid handler"
    assert machine_def.material == "stainless_steel"
    assert machine_def.manufacturer == "Hamilton"
    assert machine_def.plr_definition_details_json == plr_details
    assert machine_def.size_x_mm == 1600.0
    assert machine_def.size_y_mm == 900.0
    assert machine_def.size_z_mm == 800.0
    assert machine_def.model == "STAR"
    assert machine_def.rotation_json == rotation
    assert machine_def.plr_category == "liquid_handler"
    assert machine_def.has_deck is True
    assert machine_def.setup_method_json == setup_method


@pytest.mark.asyncio
async def test_machine_definition_orm_persist_to_database(db_session: AsyncSession) -> None:
    """Test full persistence cycle for MachineDefinition."""
    from praxis.backend.utils.uuid import uuid7

    machine_def_id = uuid7()
    machine_def = MachineDefinition(
        name="persistence_test_machine",
        fqn="test.persistence.Machine",
        machine_category=MachineCategoryEnum.PLATE_READER,
        manufacturer="Test Corp",
    )
    machine_def.accession_id = machine_def_id
    db_session.add(machine_def)
    await db_session.flush()

    # Query back
    result = await db_session.execute(
        select(MachineDefinition).where(
            MachineDefinition.accession_id == machine_def_id,
        ),
    )
    retrieved = result.scalars().first()

    # Verify persistence
    assert retrieved is not None
    assert retrieved.accession_id == machine_def_id
    assert retrieved.name == "persistence_test_machine"
    assert retrieved.fqn == "test.persistence.Machine"
    assert retrieved.machine_category == MachineCategoryEnum.PLATE_READER
    assert retrieved.manufacturer == "Test Corp"


@pytest.mark.asyncio
async def test_machine_definition_orm_unique_fqn_constraint(db_session: AsyncSession) -> None:
    """Test that FQN must be unique."""
    # Create first machine definition
    machine_def1 = MachineDefinition(
        name="machine_1",
        fqn="test.unique.Machine",
    )
    db_session.add(machine_def1)
    await db_session.flush()

    # Try to create another with same FQN
    machine_def2 = MachineDefinition(
        name="machine_2",
        fqn="test.unique.Machine",  # Duplicate FQN
    )
    db_session.add(machine_def2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_machine_definition_orm_unique_name_constraint(db_session: AsyncSession) -> None:
    """Test that name must be unique."""
    # Create first machine definition
    machine_def1 = MachineDefinition(
        name="unique_machine",
        fqn="test.unique.Machine1",
    )
    db_session.add(machine_def1)
    await db_session.flush()

    # Try to create another with same name
    machine_def2 = MachineDefinition(
        name="unique_machine",  # Duplicate name
        fqn="test.unique.Machine2",
    )
    db_session.add(machine_def2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_machine_definition_orm_machine_categories(db_session: AsyncSession) -> None:
    """Test different machine category types."""
    categories = [
        (MachineCategoryEnum.LIQUID_HANDLER, "liquid_handler"),
        (MachineCategoryEnum.PLATE_READER, "plate_reader"),
        (MachineCategoryEnum.INCUBATOR, "incubator"),
        (MachineCategoryEnum.SHAKER, "shaker"),
        (MachineCategoryEnum.THERMOCYCLER, "thermocycler"),
    ]

    for category, name_suffix in categories:
        machine_def = MachineDefinition(
            name=f"test_{name_suffix}",
            fqn=f"test.machine.{category.value}",
            machine_category=category,
        )
        db_session.add(machine_def)
        await db_session.flush()

        # Verify category was set correctly
        assert machine_def.machine_category == category


@pytest.mark.asyncio
async def test_machine_definition_orm_jsonb_fields(db_session: AsyncSession) -> None:
    """Test JSONB field handling."""
    plr_details = {
        "backend": "STAR",
        "channels": 8,
        "min_volume_ul": 0.5,
        "max_volume_ul": 1000.0,
    }
    rotation = {"x_deg": 0, "y_deg": 90, "z_deg": 180}
    setup_method = {
        "method": "setup_with_robot_config",
        "config_path": "/path/to/config.yaml",
    }

    machine_def = MachineDefinition(
        name="jsonb_test_machine",
        fqn="test.jsonb.Machine",
        plr_definition_details_json=plr_details,
        rotation_json=rotation,
        setup_method_json=setup_method,
    )
    db_session.add(machine_def)
    await db_session.flush()

    # Query back to verify JSONB storage
    result = await db_session.execute(
        select(MachineDefinition).where(
            MachineDefinition.name == "jsonb_test_machine",
        ),
    )
    retrieved = result.scalars().first()

    assert retrieved is not None
    assert retrieved.plr_definition_details_json == plr_details
    assert retrieved.plr_definition_details_json["channels"] == 8
    assert retrieved.rotation_json == rotation
    assert retrieved.rotation_json["y_deg"] == 90
    assert retrieved.setup_method_json == setup_method
    assert retrieved.setup_method_json["method"] == "setup_with_robot_config"


@pytest.mark.asyncio
async def test_machine_definition_orm_dimensions(db_session: AsyncSession) -> None:
    """Test physical dimension fields."""
    machine_def = MachineDefinition(
        name="dimensioned_machine",
        fqn="test.dimensions.Machine",
        size_x_mm=1600.0,
        size_y_mm=900.0,
        size_z_mm=800.0,
    )
    db_session.add(machine_def)
    await db_session.flush()

    # Query back
    result = await db_session.execute(
        select(MachineDefinition).where(
            MachineDefinition.name == "dimensioned_machine",
        ),
    )
    retrieved = result.scalars().first()

    assert retrieved is not None
    assert retrieved.size_x_mm == 1600.0
    assert retrieved.size_y_mm == 900.0
    assert retrieved.size_z_mm == 800.0


@pytest.mark.asyncio
async def test_machine_definition_orm_with_deck_flag(db_session: AsyncSession) -> None:
    """Test has_deck flag for machines with/without decks."""
    # Machinewith deck (liquid handler)
    with_deck = MachineDefinition(
        name="machine_with_deck",
        fqn="test.deck.MachineWithDeck",
        machine_category=MachineCategoryEnum.LIQUID_HANDLER,
        has_deck=True,
    )
    db_session.add(with_deck)
    await db_session.flush()

    # Machinewithout deck (pump)
    without_deck = MachineDefinition(
        name="machine_without_deck",
        fqn="test.deck.MachineWithoutDeck",
        machine_category=MachineCategoryEnum.PUMP,
        has_deck=False,
    )
    db_session.add(without_deck)
    await db_session.flush()

    # Verify
    assert with_deck.has_deck is True
    assert with_deck.has_deck is True
    assert without_deck.has_deck is False


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestMachineDefinitionSchemas:
    """Tests for MachineDefinition Pydantic schemas."""

    def test_machine_definition_base_minimal(self) -> None:
        """Test MachineDefinitionBase with minimal fields."""
        machine_def = MachineDefinitionBase(
            fqn="test.minimal.Machine",
            name="minimal_machine",
        )

        # Verify defaults
        assert machine_def.fqn == "test.minimal.Machine"
        assert machine_def.machine_category is None
        assert machine_def.material is None
        assert machine_def.manufacturer is None
        assert machine_def.nominal_volume_ul is None
        assert machine_def.has_deck is None

    def test_machine_definition_base_with_all_fields(self) -> None:
        """Test MachineDefinitionBase with all fields populated."""
        from praxis.backend.utils.uuid import uuid7

        plr_details = {
            "backend": "STAR",
            "num_channels": 8,
        }
        rotation = {"x_deg": 0, "y_deg": 0, "z_deg": 90}
        setup_method = {"method": "setup", "params": {"simulate": True}}
        resource_def_id = uuid7()
        deck_def_id = uuid7()

        machine_def = MachineDefinitionBase(
            name="full_machine",
            fqn="test.full.Machine",
            machine_category=MachineCategoryEnum.LIQUID_HANDLER,
            nominal_volume_ul=1000.0,
            material="stainless_steel",
            manufacturer="Hamilton",
            plr_definition_details_json=plr_details,
            size_x_mm=1600.0,
            size_y_mm=900.0,
            size_z_mm=800.0,
            model="STAR",
            rotation_json=rotation,
            resource_definition_accession_id=resource_def_id,
            has_deck=True,
            deck_definition_accession_id=deck_def_id,
            setup_method_json=setup_method,
        )

        assert machine_def.fqn == "test.full.Machine"
        assert machine_def.machine_category == "LiquidHandler"  # Serialized to string
        assert machine_def.nominal_volume_ul == 1000.0
        assert machine_def.material == "stainless_steel"
        assert machine_def.manufacturer == "Hamilton"
        assert machine_def.plr_definition_details_json == plr_details
        assert machine_def.size_x_mm == 1600.0
        assert machine_def.model == "STAR"
        assert machine_def.rotation_json == rotation
        assert machine_def.has_deck is True
        assert machine_def.setup_method_json == setup_method

    def test_machine_definition_create(self) -> None:
        """Test MachineDefinitionCreate model."""
        machine_def = MachineDefinitionCreate(
            name="test_liquid_handler",
            fqn="test.machine.LiquidHandler",
            machine_category=MachineCategoryEnum.LIQUID_HANDLER,
            manufacturer="Test Corp",
            has_deck=True,
        )

        assert machine_def.name == "test_liquid_handler"
        assert machine_def.fqn == "test.machine.LiquidHandler"
        assert machine_def.machine_category == "LiquidHandler"
        assert machine_def.manufacturer == "Test Corp"
        assert machine_def.has_deck is True

    def test_machine_definition_update(self) -> None:
        """Test MachineDefinitionUpdate model."""
        # Update requires fqn but other fields are optional
        update = MachineDefinitionUpdate(fqn="test.update.Machine")

        assert update.fqn == "test.update.Machine"
        assert update.machine_category is None
        assert update.description is None

        # Can update specific fields
        update_partial = MachineDefinitionUpdate(
            fqn="test.update.Machine2",
            description="Updated description",
            manufacturer="Updated Corp",
            size_x_mm=1700.0,
            machine_category=MachineCategoryEnum.PLATE_READER,
        )

        assert update_partial.fqn == "test.update.Machine2"
        assert update_partial.description == "Updated description"
        assert update_partial.manufacturer == "Updated Corp"
        assert update_partial.size_x_mm == 1700.0
        assert update_partial.machine_category == "PlateReader"  # Serialized to string

    def test_machine_definition_response_serialization_to_dict(self) -> None:
        """Test MachineDefinitionResponse serialization to dict."""
        from praxis.backend.utils.uuid import uuid7

        machine_id = uuid7()
        response = MachineDefinitionResponse(
            accession_id=machine_id,
            name="response_machine",
            fqn="test.response.Machine",
            machine_category=MachineCategoryEnum.LIQUID_HANDLER,
            manufacturer="Test Corp",
            has_deck=True,
        )

        machine_dict = response.model_dump()

        assert machine_dict["accession_id"] == machine_id
        assert machine_dict["name"] == "response_machine"
        assert machine_dict["fqn"] == "test.response.Machine"
        assert machine_dict["machine_category"] == "LiquidHandler"
        assert machine_dict["manufacturer"] == "Test Corp"
        assert machine_dict["has_deck"] is True

    def test_machine_definition_response_serialization_to_json(self) -> None:
        """Test MachineDefinitionResponse serialization to JSON."""
        from praxis.backend.utils.uuid import uuid7

        response = MachineDefinitionResponse(
            accession_id=uuid7(),
            name="json_machine",
            fqn="test.json.Machine",
            machine_category=MachineCategoryEnum.INCUBATOR,
        )

        json_str = response.model_dump_json()

        assert isinstance(json_str, str)
        assert "json_machine" in json_str
        assert "test.json.Machine" in json_str

    def test_machine_definition_response_deserialization_from_dict(self) -> None:
        """Test creating MachineDefinitionResponse from dict."""
        from praxis.backend.utils.uuid import uuid7

        machine_id = uuid7()
        machine_data = {
            "accession_id": machine_id,
            "name": "deserialized_machine",
            "fqn": "test.deserialized.Machine",
            "machine_category": MachineCategoryEnum.SHAKER,
            "manufacturer": "Test Corp",
        }

        response = MachineDefinitionResponse(**machine_data)

        assert response.accession_id == machine_id
        assert response.name == "deserialized_machine"
        assert response.fqn == "test.deserialized.Machine"
        assert response.machine_category == "Shaker"
        assert response.manufacturer == "Test Corp"

    def test_machine_definition_response_roundtrip_serialization(self) -> None:
        """Test MachineDefinitionResponse survives serialization round-trip."""
        from praxis.backend.utils.uuid import uuid7

        original = MachineDefinitionResponse(
            accession_id=uuid7(),
            name="roundtrip_machine",
            fqn="test.roundtrip.Machine",
            machine_category=MachineCategoryEnum.THERMOCYCLER,
            manufacturer="Test Corp",
            size_x_mm=500.0,
            size_y_mm=400.0,
            has_deck=False,
        )

        # Serialize to dict and back
        machine_dict = original.model_dump()
        restored = MachineDefinitionResponse(**machine_dict)

        assert restored.accession_id == original.accession_id
        assert restored.name == original.name
        assert restored.fqn == original.fqn
        assert restored.machine_category == original.machine_category
        assert restored.manufacturer == original.manufacturer
        assert restored.size_x_mm == original.size_x_mm
        assert restored.has_deck == original.has_deck

    @pytest.mark.asyncio
    async def test_machine_definition_response_from_model(self, db_session: AsyncSession) -> None:
        """Test converting MachineDefinition to MachineDefinitionResponse."""
        plr_details = {"backend": "STAR", "channels": 8}
        rotation = {"x_deg": 0, "y_deg": 0, "z_deg": 0}
        setup_method = {"method": "setup"}

        # Create ORM instance
        model_machine_def = MachineDefinition(
            name="model_test_machine",
            fqn="test.orm.Machine",
            machine_category=MachineCategoryEnum.LIQUID_HANDLER,
            description="Test machine from ORM",
            material="aluminum",
            manufacturer="Test Corp",
            plr_definition_details_json=plr_details,
            size_x_mm=1600.0,
            size_y_mm=900.0,
            size_z_mm=800.0,
            model="TEST-LH",
            rotation_json=rotation,
            plr_category="liquid_handler",
            setup_method_json=setup_method,
        )

        db_session.add(model_machine_def)
        await db_session.flush()

        # Convert to Pydantic
        response = MachineDefinitionResponse.model_validate(model_machine_def)

        # Verify conversion
        assert response.accession_id == model_machine_def.accession_id
        assert response.name == "model_test_machine"
        assert response.fqn == "test.orm.Machine"
        assert response.machine_category == "LiquidHandler"
        assert response.description == "Test machine from ORM"
        assert response.material == "aluminum"
        assert response.manufacturer == "Test Corp"
        assert response.plr_definition_details_json == plr_details
        assert response.size_x_mm == 1600.0
        assert response.size_y_mm == 900.0
        assert response.size_z_mm == 800.0
        assert response.model == "TEST-LH"
        assert response.rotation_json == rotation
        assert response.plr_category == "liquid_handler"
        assert response.has_deck is False
        assert response.setup_method_json == setup_method

    @pytest.mark.asyncio
    async def test_machine_definition_response_from_orm_minimal(self, db_session: AsyncSession) -> None:
        """Test ORM-to-Pydantic conversion with minimal fields."""
        model_machine_def = MachineDefinition(
            name="minimal_machine",
            fqn="test.minimal.Machine",
        )

        db_session.add(model_machine_def)
        await db_session.flush()

        # Convert to Pydantic
        response = MachineDefinitionResponse.model_validate(model_machine_def)

        # Verify
        assert response.accession_id == model_machine_def.accession_id
        assert response.name == "minimal_machine"
        assert response.fqn == "test.minimal.Machine"
        assert response.machine_category == "Unknown"  # ORM default
        assert response.description is None

    def test_machine_definition_jsonb_validation(self) -> None:
        """Test JSONB field validation in Pydantic models."""
        plr_details = {
            "backend_class": "STAR",
            "num_channels": 8,
            "channel_spacing_mm": 9.0,
        }
        setup_method = {
            "method_name": "setup_with_config",
            "config_file": "robot_config.yaml",
        }

        machine_def = MachineDefinitionCreate(
            name="jsonb_test",
            fqn="test.jsonb.Machine",
            plr_definition_details_json=plr_details,
            setup_method_json=setup_method,
        )

        assert machine_def.plr_definition_details_json == plr_details
        assert machine_def.plr_definition_details_json["num_channels"] == 8
        assert machine_def.setup_method_json == setup_method

    def test_machine_definition_category_types(self) -> None:
        """Test different machine category enum values."""
        categories = [
            MachineCategoryEnum.LIQUID_HANDLER,
            MachineCategoryEnum.PLATE_READER,
            MachineCategoryEnum.INCUBATOR,
            MachineCategoryEnum.SHAKER,
            MachineCategoryEnum.THERMOCYCLER,
        ]

        for category in categories:
            machine_def = MachineDefinitionCreate(
                name=f"test_{category.value}",
                fqn=f"test.category.{category.value}",
                machine_category=category,
            )
            assert machine_def.machine_category == category.value  # Serialized to string

    def test_machine_definition_physical_dimensions(self) -> None:
        """Test physical dimension fields."""
        machine_def = MachineDefinitionCreate(
            name="dimensioned_machine",
            fqn="test.dimensions.Machine",
            size_x_mm=1600.0,
            size_y_mm=900.0,
            size_z_mm=800.0,
        )

        assert machine_def.size_x_mm == 1600.0
        assert machine_def.size_y_mm == 900.0
        assert machine_def.size_z_mm == 800.0

    def test_machine_definition_with_deck_flag(self) -> None:
        """Test has_deck flag."""
        # Liquid handler with deck
        with_deck = MachineDefinitionCreate(
            name="liquid_handler_with_deck",
            fqn="test.deck.WithDeck",
            machine_category=MachineCategoryEnum.LIQUID_HANDLER,
            has_deck=True,
        )
        assert with_deck.has_deck is True

        # Pump without deck
        without_deck = MachineDefinitionCreate(
            name="pump_without_deck",
            fqn="test.deck.WithoutDeck",
            machine_category=MachineCategoryEnum.PUMP,
            has_deck=False,
        )
        assert without_deck.has_deck is False
