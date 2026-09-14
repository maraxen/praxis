from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.machine import MachineDefinition
from praxis.backend.services.machine_type_definition import MachineTypeDefinitionService


@pytest.fixture
def machine_type_definition_service(db_session: AsyncSession) -> MachineTypeDefinitionService:
    return MachineTypeDefinitionService(db_session)

class MockMachineClass:

    """Mock Machine Class."""


@pytest.mark.asyncio
async def test_discover_and_synchronize_machine_types(
    db_session: AsyncSession,
    machine_type_definition_service: MachineTypeDefinitionService,
) -> None:
    """Test synchronization of machine types."""
    from praxis.backend.utils.plr_static_analysis import DiscoveredClass, PLRClassType

    # Setup mock return values
    mock_discovered = [
        DiscoveredClass(
            name="MockMachineClass",
            fqn="test.machine.MockMachine",
            class_type=PLRClassType.LH_BACKEND,
            docstring="Mock Machine",
            manufacturer="TestMfg",
            compatible_backends=["backend"],
            capabilities={"shaking": True},
            file_path="/tmp/mock.py",
            module_path="test.machine",
        )
    ]

    with patch(
        "praxis.backend.services.machine_type_definition.PLRSourceParser.discover_machine_classes",
        return_value=mock_discovered
    ) as mock_discover:
        # Run sync
        synced = await machine_type_definition_service.discover_and_synchronize_type_definitions()

        assert len(synced) == 1
        assert synced[0].fqn == "test.machine.MockMachine"
        assert synced[0].name == "MockMachineClass"
        assert synced[0].frontend_fqn == "pylabrobot.liquid_handling.LiquidHandler"

        # Verify in DB
        result = await db_session.execute(select(MachineDefinition).filter_by(fqn="test.machine.MockMachine"))
        db_obj = result.scalar_one()
        assert db_obj is not None
        assert db_obj.frontend_fqn == "pylabrobot.liquid_handling.LiquidHandler"

        # Run sync again (update)
        mock_discovered[0].docstring = "Updated doc"
        mock_discover.return_value = mock_discovered

        synced_update = await machine_type_definition_service.discover_and_synchronize_type_definitions()
        assert len(synced_update) == 1
        assert synced_update[0].description == "Updated doc"
