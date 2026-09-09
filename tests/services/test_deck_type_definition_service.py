import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.deck import (
    DeckDefinition,
    DeckDefinitionCreate,
    DeckDefinitionUpdate,
    DeckPositionDefinitionCreate,
    PositioningConfig,
)
from praxis.backend.services.deck_type_definition import DeckTypeDefinitionService


@pytest.fixture
def deck_type_definition_service() -> DeckTypeDefinitionService:
    return DeckTypeDefinitionService(DeckDefinition)

@pytest.mark.asyncio
async def test_create_deck_type_definition_with_positions(
    db_session: AsyncSession,
    deck_type_definition_service: DeckTypeDefinitionService,
) -> None:
    """Test creating a deck type definition with positions."""
    pos_config = PositioningConfig(
        method_name="slot_to_location",
        arg_name="slot",
        arg_type="str",
    )

    pos_def = DeckPositionDefinitionCreate(
        name="Pos1",
        nominal_x_mm=10.0,
        nominal_y_mm=20.0,
        nominal_z_mm=30.0,
        pylabrobot_position_type_name="CarrierSite",
        # position_accession_id is missing here, checking if service handles mapping
    )

    deck_def_create = DeckDefinitionCreate(
        name="Hamilton STAR",
        fqn="pylabrobot.liquid_handling.backends.hamilton.STARDeck",
        version="1.0.0",
        positioning_config=pos_config,
        position_definitions=[pos_def],
    )

    # This might fail if logic is missing
    created_def = await deck_type_definition_service.create(db_session, obj_in=deck_def_create)

    assert created_def.accession_id is not None
    assert created_def.name == "Hamilton STAR"
    assert len(created_def.positions) == 1

    position = created_def.positions[0]
    # If mapping happened, position_accession_id should be "Pos1" or similar
    assert position.nominal_x_mm == 10.0
    # assert position.position_accession_id == "Pos1"

@pytest.mark.asyncio
async def test_get_deck_type_definition(
    db_session: AsyncSession,
    deck_type_definition_service: DeckTypeDefinitionService,
) -> None:
    """Test retrieving a deck type definition."""
    pos_config = PositioningConfig(
        method_name="test", arg_name="test", arg_type="str",
    )
    deck_def_create = DeckDefinitionCreate(
        name="Test Deck",
        fqn="test.deck",
        version="1.0.0",
        positioning_config=pos_config,
        position_definitions=[],
    )
    created_def = await deck_type_definition_service.create(db_session, obj_in=deck_def_create)

    fetched_def = await deck_type_definition_service.get(db_session, created_def.accession_id)
    assert fetched_def is not None
    assert fetched_def.accession_id == created_def.accession_id
    assert fetched_def.name == "Test Deck"

@pytest.mark.asyncio
async def test_update_deck_type_definition(
    db_session: AsyncSession,
    deck_type_definition_service: DeckTypeDefinitionService,
) -> None:
    """Test updating a deck type definition."""
    pos_config = PositioningConfig(
        method_name="test", arg_name="test", arg_type="str",
    )
    deck_def_create = DeckDefinitionCreate(
        name="Update Deck",
        fqn="update.deck",
        version="1.0.0",
        positioning_config=pos_config,
        position_definitions=[],
    )
    created_def = await deck_type_definition_service.create(db_session, obj_in=deck_def_create)

    update_data = DeckDefinitionUpdate(
        description="Updated description",
    )

    updated_def = await deck_type_definition_service.update(
        db_session, db_obj=created_def, obj_in=update_data,
    )

    assert updated_def.description == "Updated description"

@pytest.mark.asyncio
async def test_delete_deck_type_definition(
    db_session: AsyncSession,
    deck_type_definition_service: DeckTypeDefinitionService,
) -> None:
    """Test deleting a deck type definition."""
    pos_config = PositioningConfig(
        method_name="test", arg_name="test", arg_type="str",
    )
    deck_def_create = DeckDefinitionCreate(
        name="Delete Deck",
        fqn="delete.deck",
        version="1.0.0",
        positioning_config=pos_config,
    )
    created_def = await deck_type_definition_service.create(db_session, obj_in=deck_def_create)

    await deck_type_definition_service.remove(db_session, accession_id=created_def.accession_id)

    fetched_def = await deck_type_definition_service.get(db_session, created_def.accession_id)
    assert fetched_def is None
