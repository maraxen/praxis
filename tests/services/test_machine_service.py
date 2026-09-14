"""Unit tests for MachineService."""
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.filters import SearchFilters
from praxis.backend.models.domain.machine import (
    MachineCreate,
    MachineUpdate,
)
from praxis.backend.models.domain.resource import (
    ResourceDefinition,
)
from praxis.backend.models.enums.asset import AssetType
from praxis.backend.models.enums.machine import MachineStatusEnum
from praxis.backend.services.machine import machine_service


async def create_resource_definition(db: AsyncSession, name: str) -> ResourceDefinition:
    """Helper to create a resource definition."""
    definition = ResourceDefinition(
        name=name,
        fqn="com.example.Resource",
        resource_type="Generic",
        is_consumable=False,
    )
    db.add(definition)
    await db.flush()
    await db.refresh(definition)
    return definition

@pytest.mark.asyncio
async def test_machine_service_create_machine(db_session: AsyncSession) -> None:
    """Test creating a new machine."""
    machine_in = MachineCreate(
        name="Test Machine",
        fqn="com.example.Machine",
        asset_type=AssetType.MACHINE,
        status=MachineStatusEnum.OFFLINE,
    )
    machine = await machine_service.create(db=db_session, obj_in=machine_in)

    assert machine.name == "Test Machine"
    assert machine.accession_id is not None
    # machine.status is an Enum object because Machine uses SAEnum
    assert machine.status == MachineStatusEnum.OFFLINE
    assert machine.fqn == "com.example.Machine"

@pytest.mark.asyncio
async def test_machine_service_create_machine_minimal(db_session: AsyncSession) -> None:
    """Test creating machine with only required fields."""
    machine_in = MachineCreate(
        name="Minimal Machine",
        asset_type=AssetType.MACHINE,
    )
    machine = await machine_service.create(db=db_session, obj_in=machine_in)

    assert machine.name == "Minimal Machine"
    # Default status is OFFLINE
    assert machine.status == MachineStatusEnum.OFFLINE

@pytest.mark.asyncio
async def test_machine_service_create_duplicate_name(db_session: AsyncSession) -> None:
    """Test that creating machine with duplicate name fails."""
    machine_in = MachineCreate(name="Duplicate Name", asset_type=AssetType.MACHINE)
    await machine_service.create(db=db_session, obj_in=machine_in)

    with pytest.raises(ValueError, match="already exists"):
        await machine_service.create(db=db_session, obj_in=machine_in)

@pytest.mark.asyncio
async def test_machine_service_get_by_id(db_session: AsyncSession) -> None:
    """Test retrieving machine by ID."""
    machine_in = MachineCreate(name="Get Machine", asset_type=AssetType.MACHINE)
    created = await machine_service.create(db=db_session, obj_in=machine_in)

    retrieved = await machine_service.get(db=db_session, accession_id=created.accession_id)
    assert retrieved is not None
    assert retrieved.accession_id == created.accession_id
    assert retrieved.name == "Get Machine"

@pytest.mark.asyncio
async def test_machine_service_get_by_id_not_found(db_session: AsyncSession) -> None:
    """Test retrieving non-existent machine returns None."""
    non_existent_id = uuid.uuid4()
    retrieved = await machine_service.get(db=db_session, accession_id=non_existent_id)
    assert retrieved is None

@pytest.mark.asyncio
async def test_machine_service_get_multi(db_session: AsyncSession) -> None:
    """Test listing multiple machines."""
    await machine_service.create(db=db_session, obj_in=MachineCreate(name="Machine 1", asset_type=AssetType.MACHINE))
    await machine_service.create(db=db_session, obj_in=MachineCreate(name="Machine 2", asset_type=AssetType.MACHINE))

    filters = SearchFilters()
    machines = await machine_service.get_multi(db=db_session, filters=filters)

    # get_multi might return machines from previous tests if not cleaned up,
    # but db_session fixture rolls back, so it should be clean PER TEST function.
    # However, ensure we find the ones we created.
    names = [m.name for m in machines]
    assert "Machine 1" in names
    assert "Machine 2" in names

@pytest.mark.asyncio
async def test_machine_service_update_machine(db_session: AsyncSession) -> None:
    """Test updating machine information."""
    machine_in = MachineCreate(name="Update Machine", asset_type=AssetType.MACHINE)
    created = await machine_service.create(db=db_session, obj_in=machine_in)

    # MachineUpdate requires asset_type because it inherits from MachineBase (via PraxisBaseModel logic flaw?)
    # or AssetBase which has required asset_type field.
    # We must provide it.
    update_data = MachineUpdate(
        name="Updated Name",
        status=MachineStatusEnum.AVAILABLE,
        asset_type=AssetType.MACHINE,
    )
    updated = await machine_service.update(db=db_session, db_obj=created, obj_in=update_data)

    assert updated.name == "Updated Name"
    # Machine uses SAEnum, so it returns the Enum member
    assert updated.status == MachineStatusEnum.AVAILABLE

    refetched = await machine_service.get(db=db_session, accession_id=created.accession_id)
    assert refetched.name == "Updated Name"

@pytest.mark.asyncio
async def test_machine_service_update_machine_duplicate_name(db_session: AsyncSession) -> None:
    """Test updating machine to a name that already exists."""
    await machine_service.create(db=db_session, obj_in=MachineCreate(name="Existing Name", asset_type=AssetType.MACHINE))
    target = await machine_service.create(db=db_session, obj_in=MachineCreate(name="Target Machine", asset_type=AssetType.MACHINE))

    # Provide asset_type
    update_data = MachineUpdate(name="Existing Name", asset_type=AssetType.MACHINE)
    with pytest.raises(ValueError, match="already exists"):
        await machine_service.update(db=db_session, db_obj=target, obj_in=update_data)

@pytest.mark.asyncio
async def test_machine_service_remove_machine(db_session: AsyncSession) -> None:
    """Test deleting a machine."""
    machine_in = MachineCreate(name="Remove Machine", asset_type=AssetType.MACHINE)
    created = await machine_service.create(db=db_session, obj_in=machine_in)

    removed = await machine_service.remove(db=db_session, accession_id=created.accession_id)
    assert removed is not None

    retrieved = await machine_service.get(db=db_session, accession_id=created.accession_id)
    assert retrieved is None

@pytest.mark.asyncio
async def test_machine_service_remove_nonexistent(db_session: AsyncSession) -> None:
    """Test deleting non-existent machine returns None."""
    result = await machine_service.remove(db=db_session, accession_id=uuid.uuid4())
    assert result is None

@pytest.mark.asyncio
async def test_machine_service_update_status(db_session: AsyncSession) -> None:
    """Test updating machine status via update_machine_status."""
    machine_in = MachineCreate(name="Status Machine", asset_type=AssetType.MACHINE)
    created = await machine_service.create(db=db_session, obj_in=machine_in)

    updated = await machine_service.update_machine_status(
        db=db_session,
        machine_accession_id=created.accession_id,
        new_status=MachineStatusEnum.IN_USE,
        status_details="Running protocol",
    )

    assert updated.status == MachineStatusEnum.IN_USE
    assert updated.status_details == "Running protocol"

    # Note: We cannot easily test current_protocol_run_accession_id here without
    # creating a full protocol hierarchy, which is complex.
    # The logic is simple assignment, so we trust it works if constraints allow.

@pytest.mark.asyncio
async def test_machine_service_update_status_not_found(db_session: AsyncSession) -> None:
    """Test updating status for non-existent machine."""
    result = await machine_service.update_machine_status(
        db=db_session,
        machine_accession_id=uuid.uuid4(),
        new_status=MachineStatusEnum.ERROR,
    )
    assert result is None

@pytest.mark.asyncio
async def test_machine_service_create_with_resource_counterpart(db_session: AsyncSession) -> None:
    """Test creating a machine with a resource counterpart."""
    res_def_name = "test_machine_res_def"
    await create_resource_definition(db_session, res_def_name)

    machine_in = MachineCreate(
        name="Resource Machine",
        asset_type=AssetType.MACHINE,
        resource_def_name=res_def_name,
    )

    machine = await machine_service.create(db=db_session, obj_in=machine_in)

    assert machine.resource_counterpart is not None

@pytest.mark.asyncio
async def test_machine_service_update_with_resource_counterpart(db_session: AsyncSession) -> None:
    """Test updating machine with resource counterpart."""
    machine_in = MachineCreate(name="Update Resource Machine", asset_type=AssetType.MACHINE)
    machine = await machine_service.create(db=db_session, obj_in=machine_in)

    res_def_name = "update_machine_res_def"
    await create_resource_definition(db_session, res_def_name)

    update_data = MachineUpdate(
        asset_type=AssetType.MACHINE,
        resource_def_name=res_def_name,
    )

    updated = await machine_service.update(db=db_session, db_obj=machine, obj_in=update_data)

    assert updated.resource_counterpart is not None
