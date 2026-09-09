"""Unit tests for Machinemodel."""
import json

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.machine import (
    Machine,
    MachineBase,
    MachineCreate,
    MachineUpdate,
)
from praxis.backend.models.domain.machine import (
    MachineRead as MachineResponse,
)
from praxis.backend.models.enums import AssetType, MachineCategoryEnum, MachineStatusEnum


@pytest.mark.asyncio
async def test_machine_orm_creation_with_defaults(db_session: AsyncSession) -> None:
    """Test creating a Machinewith default values."""
    from praxis.backend.utils.uuid import uuid7

    # Create a machine with only required fields
    machine_id = uuid7()
    machine = Machine(
        name="test_machine",
        fqn="test.machine.Fqn",
        asset_type=AssetType.MACHINE,  # Must set explicitly for polymorphic identity
    )
    machine.accession_id = machine_id

    # Verify defaults are set
    assert machine.accession_id == machine_id
    assert machine.name == "test_machine"
    assert machine.fqn == "test.machine.Fqn"
    assert machine.asset_type == AssetType.MACHINE
    assert machine.status == MachineStatusEnum.OFFLINE
    assert machine.machine_category == MachineCategoryEnum.UNKNOWN
    assert machine.description is None
    assert machine.manufacturer is None
    assert machine.model is None
    assert machine.serial_number is None
    assert machine.connection_info is None
    assert machine.workcell_accession_id is None


@pytest.mark.asyncio
async def test_machine_orm_persist_to_database(db_session: AsyncSession) -> None:
    """Test that a Machinecan be persisted to the database."""
    from praxis.backend.utils.uuid import uuid7

    machine_id = uuid7()
    machine = Machine(
        name="test_persistence",
        fqn="test.persistence.Machine",
        asset_type=AssetType.MACHINE,
        description="A test machine",
        manufacturer="Test Manufacturer",
        model="Model X",
        status=MachineStatusEnum.AVAILABLE,  # Changed from ONLINE
        machine_category=MachineCategoryEnum.LIQUID_HANDLER,
    )
    machine.accession_id = machine_id

    # Add to session and flush
    db_session.add(machine)
    await db_session.flush()

    # Query back from database
    result = await db_session.execute(
        select(Machine).where(Machine.accession_id == machine_id),
    )
    retrieved = result.scalars().first()

    # Verify persistence
    assert retrieved is not None
    assert retrieved.accession_id == machine_id
    assert retrieved.name == "test_persistence"
    assert retrieved.fqn == "test.persistence.Machine"
    assert retrieved.description == "A test machine"
    assert retrieved.manufacturer == "Test Manufacturer"
    assert retrieved.model == "Model X"
    assert retrieved.status == MachineStatusEnum.AVAILABLE
    assert retrieved.machine_category == MachineCategoryEnum.LIQUID_HANDLER


@pytest.mark.asyncio
async def test_machine_orm_unique_name_constraint(db_session: AsyncSession) -> None:
    """Test that machine names must be unique."""
    from sqlalchemy.exc import IntegrityError

    from praxis.backend.utils.uuid import uuid7

    # Create first machine
    machine1 = Machine(
        name="unique_machine",
        fqn="test.machine.1",
        asset_type=AssetType.MACHINE,
    )
    machine1.accession_id = uuid7()
    db_session.add(machine1)
    await db_session.flush()

    # Try to create another with same name
    machine2 = Machine(
        name="unique_machine",  # Duplicate name
        fqn="test.machine.2",
        asset_type=AssetType.MACHINE,
    )
    machine2.accession_id = uuid7()
    db_session.add(machine2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_machine_orm_unique_serial_number(db_session: AsyncSession) -> None:
    """Test that machine serial numbers must be unique."""
    from sqlalchemy.exc import IntegrityError

    from praxis.backend.utils.uuid import uuid7

    # Create first machine with serial number
    machine1 = Machine(
        name="machine1",
        fqn="test.machine.1",
        asset_type=AssetType.MACHINE,
        serial_number="SN123456",
    )
    machine1.accession_id = uuid7()
    db_session.add(machine1)
    await db_session.flush()

    # Try to create another with same serial number
    machine2 = Machine(
        name="machine2",
        fqn="test.machine.2",
        asset_type=AssetType.MACHINE,
        serial_number="SN123456",  # Duplicate serial
    )
    machine2.accession_id = uuid7()
    db_session.add(machine2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_machine_orm_with_workcell_relationship(db_session: AsyncSession) -> None:
    """Test creating a machine with a workcell relationship."""
    from praxis.backend.models.domain.workcell import Workcell
    from praxis.backend.utils.uuid import uuid7

    # Create a workcell first
    workcell_id = uuid7()
    workcell = Workcell(
        name="test_workcell",
    )
    workcell.accession_id = workcell_id
    db_session.add(workcell)
    await db_session.flush()

    # Create a machine and set workcell via attribute (not constructor)
    machine_id = uuid7()
    machine = Machine(
        name="test_machine_in_workcell",
        fqn="test.machine.InWorkcell",
        asset_type=AssetType.MACHINE,
    )
    machine.accession_id = machine_id
    # Set workcell FK after instantiation
    machine.workcell = workcell

    db_session.add(machine)
    await db_session.flush()

    # Query back and verify relationship
    result = await db_session.execute(
        select(Machine).where(Machine.accession_id == machine_id),
    )
    retrieved_machine = result.scalars().first()

    assert retrieved_machine is not None
    assert retrieved_machine.workcell_accession_id == workcell_id


@pytest.mark.asyncio
async def test_machine_orm_status_enum_values(db_session: AsyncSession) -> None:
    """Test that machine status enum values are stored correctly."""
    from praxis.backend.utils.uuid import uuid7

    # Test each status
    statuses = [
        MachineStatusEnum.AVAILABLE,  # Changed from ONLINE
        MachineStatusEnum.OFFLINE,
        MachineStatusEnum.ERROR,
        MachineStatusEnum.MAINTENANCE,
    ]

    for status in statuses:
        machine = Machine(
            name=f"machine_{status.value}",
            fqn=f"test.machine.{status.value}",
            asset_type=AssetType.MACHINE,
            status=status,
        )
        machine.accession_id = uuid7()
        db_session.add(machine)
        await db_session.flush()

        # Verify status was set correctly
        assert machine.status == status


@pytest.mark.asyncio
async def test_machine_orm_category_enum_values(db_session: AsyncSession) -> None:
    """Test that machine category enum values are stored correctly."""
    from praxis.backend.utils.uuid import uuid7

    # Test a few key categories
    categories = [
        MachineCategoryEnum.LIQUID_HANDLER,
        MachineCategoryEnum.PLATE_READER,
        MachineCategoryEnum.CENTRIFUGE,
        MachineCategoryEnum.UNKNOWN,
    ]

    for category in categories:
        machine = Machine(
            name=f"machine_{category.value}",
            fqn=f"test.machine.{category.value}",
            asset_type=AssetType.MACHINE,
            machine_category=category,
        )
        machine.accession_id = uuid7()
        db_session.add(machine)
        await db_session.flush()

        # Verify category was set correctly
        assert machine.machine_category == category


@pytest.mark.asyncio
async def test_machine_orm_connection_info_json(db_session: AsyncSession) -> None:
    """Test that machine connection_info JSONB field works correctly."""
    from praxis.backend.utils.uuid import uuid7

    connection_data = {
        "backend": "hamilton",
        "address": "192.168.1.100",
        "port": 8080,
        "protocol": "http",
    }

    machine = Machine(
        name="machine_with_connection",
        fqn="test.machine.WithConnection",
        asset_type=AssetType.MACHINE,
        connection_info=connection_data,
    )
    machine.accession_id = uuid7()

    db_session.add(machine)
    await db_session.flush()

    # Verify JSON was stored correctly
    assert machine.connection_info == connection_data
    assert machine.connection_info["backend"] == "hamilton"
    assert machine.connection_info["port"] == 8080


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestMachineSchemas:
    """Tests for Machine Pydantic schemas."""

    def test_machine_base_minimal(self) -> None:
        """Test creating a MachineBase with minimal required fields."""
        machine = MachineBase(
            name="test_machine",
            asset_type=AssetType.MACHINE,
        )

        assert machine.name == "test_machine"
        assert machine.asset_type == "MACHINE"  # Enum stored as string
        # Note: MachineStatusEnum NOT converted to string (different from WorkcellStatusEnum)
        assert machine.status == MachineStatusEnum.OFFLINE
        assert machine.description is None
        assert machine.manufacturer is None
        assert machine.model is None

    def test_machine_base_with_all_fields(self) -> None:
        """Test creating a MachineBase with all fields populated."""
        connection_info = {"backend": "hamilton", "address": "192.168.1.100"}

        machine = MachineBase(
            name="full_machine",
            fqn="test.full.Machine",
            asset_type=AssetType.MACHINE,
            status=MachineStatusEnum.AVAILABLE,
            description="A fully configured machine",
            manufacturer="Test Corp",
            model="Model X",
            serial_number="SN12345",
            connection_info=connection_info,
            is_simulation_override=False,
        )

        assert machine.name == "full_machine"
        assert machine.fqn == "test.full.Machine"
        assert machine.asset_type == "MACHINE"
        # use_enum_values=True means enum is stored as string value
        assert machine.status == MachineStatusEnum.AVAILABLE.value
        assert machine.description == "A fully configured machine"
        assert machine.manufacturer == "Test Corp"
        assert machine.model == "Model X"
        assert machine.serial_number == "SN12345"
        assert machine.connection_info == connection_info
        assert machine.is_simulation_override is False

    def test_machine_create_inherits_from_base(self) -> None:
        """Test that MachineCreate inherits all properties from MachineBase."""
        machine = MachineCreate(
            name="create_test",
            fqn="test.create.Machine",
            asset_type=AssetType.MACHINE,
            description="Testing create model",
        )

        assert machine.name == "create_test"
        assert machine.fqn == "test.create.Machine"
        assert machine.asset_type == "MACHINE"
        assert machine.description == "Testing create model"
        # MachineStatusEnum stored as enum object, not string
        assert machine.status == MachineStatusEnum.OFFLINE

    def test_machine_update_all_fields_optional(self) -> None:
        """Test that MachineUpdate allows all fields to be optional.

        Note: MachineUpdate inherits from AssetBase which requires asset_type.
        For updates, asset_type should typically not change, but must be provided.
        """
        # Create with minimal required field (asset_type)
        # Note: name has default_factory in PraxisBaseModel, so it's auto-generated
        update = MachineUpdate(asset_type=AssetType.MACHINE)
        # assert update.asset_type == "MACHINE"  # MachineUpdate does not strictly define asset_type field
        assert update.name is None  # Default is None
        assert update.description is None
        assert update.status is None

        # Should be able to create with partial fields
        update_partial = MachineUpdate(
            asset_type=AssetType.MACHINE,
            name="new_name",
            status=MachineStatusEnum.MAINTENANCE,
        )
        # assert update_partial.asset_type == "MACHINE"
        assert update_partial.name == "new_name"
        assert update_partial.status == "MAINTENANCE"
        assert update_partial.description is None

    def test_machine_response_serialization_to_dict(self) -> None:
        """Test that MachineResponse can be serialized to a dictionary."""
        machine = MachineResponse(
            name="serialize_test",
            fqn="test.serialize.Machine",
            asset_type=AssetType.MACHINE,
            description="Testing serialization",
            status=MachineStatusEnum.MAINTENANCE,
        )

        data = machine.model_dump()

        assert isinstance(data, dict)
        assert data["name"] == "serialize_test"
        assert data["fqn"] == "test.serialize.Machine"
        assert data["asset_type"] == "MACHINE"  # Enum to string
        assert data["description"] == "Testing serialization"
        assert data["status"] == "MAINTENANCE"  # Enum to string

    def test_machine_response_serialization_to_json(self) -> None:
        """Test that MachineResponse can be serialized to JSON."""
        machine = MachineResponse(
            name="json_test",
            fqn="test.json.Machine",
            asset_type=AssetType.MACHINE,
            status=MachineStatusEnum.ERROR,
        )

        json_str = machine.model_dump_json()

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["name"] == "json_test"
        assert data["fqn"] == "test.json.Machine"
        assert data["asset_type"] == "MACHINE"
        assert data["status"] == "ERROR"

    def test_machine_response_deserialization_from_dict(self) -> None:
        """Test that MachineResponse can be deserialized from a dictionary."""
        data = {
            "name": "deserialize_test",
            "fqn": "test.deserialize.Machine",
            "asset_type": "MACHINE",
            "description": "From dict",
            "status": "AVAILABLE",
            "manufacturer": "Test Manufacturer",
            "model": "Model Y",
            "connection_info": {"backend": "tecan"},
            "accession_id": "019a6ee5-1234-7890-abcd-ef1234567890",
            "created_at": "2025-11-10T12:00:00Z",
            "properties_json": {},
        }

        machine = MachineResponse.model_validate(data)

        assert machine.name == "deserialize_test"
        assert machine.fqn == "test.deserialize.Machine"
        assert machine.asset_type == "MACHINE"
        assert machine.description == "From dict"
        assert machine.status == "AVAILABLE"
        assert machine.manufacturer == "Test Manufacturer"
        assert machine.model == "Model Y"
        assert machine.connection_info == {"backend": "tecan"}

    def test_machine_response_status_enum_validation(self) -> None:
        """Test that MachineResponse properly validates status enum values."""
        # Valid enum value as string
        machine1 = MachineResponse(
            name="enum_test_1",
            fqn="test.enum.1",
            asset_type=AssetType.MACHINE,
            status="AVAILABLE",
        )
        assert machine1.status == "AVAILABLE"

        # Valid enum value as enum
        machine2 = MachineResponse(
            name="enum_test_2",
            fqn="test.enum.2",
            asset_type=AssetType.MACHINE,
            status=MachineStatusEnum.IN_USE,
        )
        assert machine2.status == "IN_USE"

        # Invalid enum value should raise error
        with pytest.raises(ValueError):
            MachineResponse(
                name="enum_test_3",
                fqn="test.enum.3",
                asset_type=AssetType.MACHINE,
                status="invalid_status",
            )

    def test_machine_response_roundtrip_serialization(self) -> None:
        """Test that MachineResponse can be serialized and deserialized without data loss."""
        original = MachineResponse(
            name="roundtrip_test",
            fqn="test.roundtrip.Machine",
            asset_type=AssetType.MACHINE,
            description="Testing roundtrip",
            status=MachineStatusEnum.MAINTENANCE,
            manufacturer="Roundtrip Corp",
            connection_info={"test": "data", "nested": {"value": 123}},
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize back
        restored = MachineResponse.model_validate(data)

        # Should be equal
        assert restored.name == original.name
        assert restored.fqn == original.fqn
        assert restored.asset_type == original.asset_type
        assert restored.description == original.description
        assert restored.status == original.status
        assert restored.manufacturer == original.manufacturer
        assert restored.connection_info == original.connection_info

    @pytest.mark.asyncio
    async def test_machine_response_from_model(self, db_session: AsyncSession) -> None:
        """Test converting a Machine instance to MachineResponse (critical for API layer).

        This validates that models inheriting from Asset (with fqn field)
        can be successfully converted to their Pydantic response models.
        """
        from praxis.backend.utils.uuid import uuid7

        # Create an ORM instance
        machine_id = uuid7()
        model_machine = Machine(
            # accession_id=machine_id,  # init=False in ORM
            name="model_test_machine",
            fqn="test.orm.Machine",
            asset_type=AssetType.MACHINE,
            description="Testing ORM to Pydantic conversion",
            manufacturer="Test Manufacturer",
            model="Model Z",
            status=MachineStatusEnum.AVAILABLE,
            connection_info={"backend": "hamilton", "port": 8080},
        )
        model_machine.accession_id = machine_id

        db_session.add(model_machine)
        await db_session.flush()

        # Convert ORM to Pydantic using model_validate with from_attributes=True
        response = MachineResponse.model_validate(model_machine)

        # Verify all fields are correctly converted
        assert response.accession_id == machine_id
        assert response.name == "model_test_machine"
        assert response.fqn == "test.orm.Machine"  # fqn IS present for Assets
        assert response.asset_type == "MACHINE"  # Enum converted to string
        assert response.description == "Testing ORM to Pydantic conversion"
        assert response.manufacturer == "Test Manufacturer"
        assert response.model == "Model Z"
        assert response.status == "AVAILABLE"  # Enum converted to string value
        assert response.connection_info == {"backend": "hamilton", "port": 8080}

    @pytest.mark.asyncio
    async def test_machine_response_from_orm_minimal(self, db_session: AsyncSession) -> None:
        """Test ORM-to-Pydantic conversion with minimal fields."""
        from praxis.backend.utils.uuid import uuid7

        # Create minimal ORM instance
        machine_id = uuid7()
        model_machine = Machine(
            # accession_id=machine_id,
            name="minimal_machine",
            fqn="test.minimal.Machine",
            asset_type=AssetType.MACHINE,
        )
        model_machine.accession_id = machine_id

        db_session.add(model_machine)
        await db_session.flush()

        # Convert to Pydantic
        response = MachineResponse.model_validate(model_machine)

        # Verify required fields
        assert response.accession_id == machine_id
        assert response.name == "minimal_machine"
        assert response.fqn == "test.minimal.Machine"
        assert response.asset_type == "MACHINE"
        assert response.status == "OFFLINE"  # Default status

        # Verify optional fields are None or default
        assert response.description is None
        assert response.manufacturer is None
        assert response.model is None
        assert response.serial_number is None
        assert response.connection_info is None
