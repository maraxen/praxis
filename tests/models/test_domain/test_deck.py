"""Unit tests for Deck-related ORM models."""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from praxis.backend.models.domain.deck import (
    Deck,
    DeckBase,
    DeckCreate,
    DeckDefinition,
    DeckPositionDefinition,
    DeckPositionDefinitionCreate,
    DeckUpdate,
    PositioningConfig,
)
from praxis.backend.models.domain.deck import (
    DeckPositionDefinitionRead as DeckPositionDefinitionResponse,
)
from praxis.backend.models.domain.deck import (
    DeckRead as DeckResponse,
)
from praxis.backend.models.domain.machine import Machine
from praxis.backend.models.domain.resource import Resource, ResourceDefinition
from praxis.backend.models.enums import AssetType, ResourceStatusEnum
from praxis.backend.utils.uuid import uuid7


@pytest_asyncio.fixture
async def deck_definition(db_session: AsyncSession) -> DeckDefinition:
    """Create a DeckDefinitionfor testing."""
    deck_def = DeckDefinition(
        name="test_deck_definition_fixture",
        fqn="test.deck.DefinitionFixture",
    )
    db_session.add(deck_def)
    await db_session.flush()
    return deck_def


@pytest_asyncio.fixture
async def resource_definition(db_session: AsyncSession) -> ResourceDefinition:
    """Create a ResourceDefinition for testing."""
    res_def = ResourceDefinition(
        name="test_resource_definition_fixture",
        fqn="test.resource.DefinitionFixture",
    )
    db_session.add(res_def)
    await db_session.flush()
    return res_def


@pytest_asyncio.fixture
async def deck(
    db_session: AsyncSession,
    deck_definition: DeckDefinition,
    resource_definition: ResourceDefinition,
) -> Deck:
    """Create a complete Deckinstance for testing."""
    deck_id = uuid7()
    deck = Deck(
        name="test_deck_fixture",
        fqn="test.deck.Fixture",
        asset_type=AssetType.DECK,
        deck_type_id=deck_definition.accession_id,
        resource_definition_accession_id=resource_definition.accession_id,
    )
    deck.accession_id = deck_id
    deck.deck_type = deck_definition
    deck.resource_definition = resource_definition
    db_session.add(deck)
    await db_session.flush()
    return deck


@pytest.mark.asyncio
async def test_deck_definition_orm_creation(db_session: AsyncSession) -> None:
    """Test creating a DeckDefinitionwith minimal fields."""
    # Create deck definition
    deck_def = DeckDefinition(
        name="test_deck_definition",
        fqn="test.deck.Definition",
    )
    db_session.add(deck_def)
    await db_session.flush()

    # Verify defaults
    assert deck_def.accession_id is not None
    assert deck_def.name == "test_deck_definition"
    assert deck_def.fqn == "test.deck.Definition"
    assert deck_def.default_size_x_mm is None
    assert deck_def.default_size_y_mm is None
    assert deck_def.default_size_z_mm is None


@pytest.mark.asyncio
async def test_deck_definition_orm_with_jsonb_fields(db_session: AsyncSession) -> None:
    """Test DeckDefinitionwith JSONB fields."""
    positioning_config = {
        "method_name": "slot_to_location",
        "arg_name": "slot",
        "arg_type": "str",
    }

    constructor_args = {
        "rails": 54,
        "size_x": 1360.0,
        "size_y": 653.0,
    }

    deck_def = DeckDefinition(
        name="hamilton_star_deck",
        fqn="pylabrobot.liquid_handling.backends.hamilton.STARDeck",
        positioning_config_json=positioning_config,
        serialized_constructor_args_json=constructor_args,
        default_size_x_mm=1360.0,
        default_size_y_mm=653.0,
        default_size_z_mm=100.0,
    )
    db_session.add(deck_def)
    await db_session.flush()

    # Verify JSONB fields stored correctly
    assert deck_def.positioning_config_json == positioning_config
    assert deck_def.serialized_constructor_args_json == constructor_args
    assert deck_def.positioning_config_json["method_name"] == "slot_to_location"
    assert deck_def.serialized_constructor_args_json["rails"] == 54


@pytest.mark.asyncio
async def test_deck_position_definition_orm_creation(db_session: AsyncSession) -> None:
    """Test creating a DeckPositionDefinition."""
    # Create deck definition first
    deck_def = DeckDefinition(
        name="test_deck_for_positions",
        fqn="test.deck.ForPositions",
    )
    db_session.add(deck_def)
    await db_session.flush()

    # Create position definition
    position = DeckPositionDefinition(
        name="position_a1",
        deck_type_id=deck_def.accession_id,
        position_accession_id="A1",
        nominal_x_mm=100.0,
        nominal_y_mm=200.0,
        nominal_z_mm=10.0,
        accepts_plates=True,
        accepts_tips=False,
        deck_type=deck_def,  # Also set relationship
    )
    db_session.add(position)
    await db_session.flush()

    # Verify
    assert position.accession_id is not None
    assert position.position_accession_id == "A1"
    assert position.nominal_x_mm == 100.0
    assert position.nominal_y_mm == 200.0
    assert position.nominal_z_mm == 10.0
    assert position.accepts_plates is True
    assert position.accepts_tips is False


@pytest.mark.asyncio
async def test_deck_position_definition_orm_unique_constraint(db_session: AsyncSession) -> None:
    """Test unique constraint on (deck_type_id, position_accession_id)."""
    # Create deck definition
    deck_def = DeckDefinition(
        name="unique_constraint_deck",
        fqn="test.deck.UniqueConstraint",
    )
    db_session.add(deck_def)
    await db_session.flush()

    # Create first position
    position1 = DeckPositionDefinition(
        name="unique_position_a1",
        deck_type_id=deck_def.accession_id,
        position_accession_id="A1",
        nominal_x_mm=100.0,
        nominal_y_mm=200.0,
        nominal_z_mm=10.0,
        deck_type=deck_def,
    )
    db_session.add(position1)
    await db_session.flush()

    # Try to create duplicate position on same deck
    position2 = DeckPositionDefinition(
        name="unique_position_a1_duplicate",
        deck_type_id=deck_def.accession_id,
        position_accession_id="A1",  # Duplicate
        nominal_x_mm=150.0,
        nominal_y_mm=250.0,
        nominal_z_mm=10.0,
        deck_type=deck_def,
    )
    db_session.add(position2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_deck_orm_creation_with_defaults(db_session: AsyncSession) -> None:
    """Test creating a Deckwith minimal required fields."""
    # Create resource definition for deck
    resource_def = ResourceDefinition(
        name="deck_resource_def",
        fqn="test.deck.ResourceDef",
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Create deck definition
    deck_def = DeckDefinition(
        name="test_deck_def",
        fqn="test.deck.TypeDef",
    )
    db_session.add(deck_def)
    await db_session.flush()

    # Create deck with required fields
    deck_id = uuid7()
    deck = Deck(
        name="test_deck",
        fqn="test.deck.Instance",
        asset_type=AssetType.DECK,
        deck_type_id=deck_def.accession_id,  # Required kw_only FK
    )
    deck.accession_id = deck_id
    # Set FKs via relationships (workaround for MappedAsDataclass FK issue)
    deck.resource_definition = resource_def
    deck.deck_type = deck_def

    db_session.add(deck)
    await db_session.flush()

    # Verify defaults
    assert deck.accession_id == deck_id
    assert deck.name == "test_deck"
    assert deck.fqn == "test.deck.Instance"
    assert deck.asset_type == AssetType.DECK
    assert deck.status == ResourceStatusEnum.UNKNOWN
    assert deck.resource_definition == resource_def
    assert deck.deck_type == deck_def
    assert deck.parent_machine_accession_id is None


@pytest.mark.asyncio
async def test_deck_orm_persist_to_database(db_session: AsyncSession) -> None:
    """Test full persistence cycle for Deck."""
    # Create resource definition
    resource_def = ResourceDefinition(
        name="persist_deck_resource_def",
        fqn="test.deck.PersistResourceDef",
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Create deck definition
    deck_def = DeckDefinition(
        name="persist_deck_def",
        fqn="test.deck.PersistDef",
        default_size_x_mm=1360.0,
        default_size_y_mm=653.0,
    )
    db_session.add(deck_def)
    await db_session.flush()

    # Create deck
    deck_id = uuid7()
    deck = Deck(
        name="test_persistence_deck",
        fqn="test.deck.Persistence",
        asset_type=AssetType.DECK,
        status=ResourceStatusEnum.AVAILABLE_ON_DECK,
        deck_type_id=deck_def.accession_id,
    )
    deck.accession_id = deck_id
    deck.resource_definition = resource_def
    deck.deck_type = deck_def

    db_session.add(deck)
    await db_session.flush()

    # Query back
    result = await db_session.execute(
        select(Deck).where(Deck.accession_id == deck_id),
    )
    retrieved = result.scalars().first()

    # Verify persistence
    assert retrieved is not None
    assert retrieved.accession_id == deck_id
    assert retrieved.name == "test_persistence_deck"
    assert retrieved.status == ResourceStatusEnum.AVAILABLE_ON_DECK
    assert retrieved.resource_definition_accession_id == resource_def.accession_id
    assert retrieved.deck_type_id == deck_def.accession_id


@pytest.mark.asyncio
async def test_deck_orm_unique_name_constraint(db_session: AsyncSession) -> None:
    """Test that deck names must be unique (inherited from Asset)."""
    # Create resource definition
    resource_def = ResourceDefinition(
        name="unique_deck_resource_def",
        fqn="test.deck.UniqueResourceDef",
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Create deck definition
    deck_def = DeckDefinition(
        name="unique_deck_def",
        fqn="test.deck.UniqueDef",
    )
    db_session.add(deck_def)
    await db_session.flush()

    # Create first deck
    deck1_id = uuid7()
    deck1 = Deck(
        name="unique_deck",
        fqn="test.deck.1",
        asset_type=AssetType.DECK,
        deck_type_id=deck_def.accession_id,
    )
    deck1.accession_id = deck1_id
    deck1.resource_definition = resource_def
    deck1.deck_type = deck_def
    db_session.add(deck1)
    await db_session.flush()

    # Try to create another with same name
    deck2_id = uuid7()
    deck2 = Deck(
        name="unique_deck",  # Duplicate
        fqn="test.deck.2",
        asset_type=AssetType.DECK,
        deck_type_id=deck_def.accession_id,
    )
    deck2.accession_id = deck2_id
    deck2.resource_definition = resource_def
    deck2.deck_type = deck_def
    db_session.add(deck2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_deck_orm_with_parent_machine(db_session: AsyncSession) -> None:
    """Test Deckwith parent machine relationship."""
    # Create machine
    machine_id = uuid7()
    machine = Machine(
        name="test_machine_for_deck",
        fqn="test.machine.ForDeck",
        asset_type=AssetType.MACHINE,
    )
    machine.accession_id = machine_id
    db_session.add(machine)
    await db_session.flush()

    # Create resource definition
    resource_def = ResourceDefinition(
        name="machine_deck_resource_def",
        fqn="test.deck.MachineDeckResourceDef",
    )
    db_session.add(resource_def)
    await db_session.flush()

    # Create deck definition
    deck_def = DeckDefinition(
        name="machine_deck_def",
        fqn="test.deck.MachineDeckDef",
    )
    db_session.add(deck_def)
    await db_session.flush()

    # Create deck with parent machine
    deck_id = uuid7()
    deck = Deck(
        name="deck_on_machine",
        fqn="test.deck.OnMachine",
        asset_type=AssetType.DECK,
        deck_type_id=deck_def.accession_id,
    )
    deck.accession_id = deck_id
    deck.resource_definition = resource_def
    deck.deck_type = deck_def
    deck.parent_machine = machine

    db_session.add(deck)
    await db_session.flush()

    # Query back and verify
    result = await db_session.execute(
        select(Deck).where(Deck.accession_id == deck_id),
    )
    retrieved = result.scalars().first()

    assert retrieved is not None
    assert retrieved.parent_machine_accession_id == machine_id


@pytest.mark.asyncio
async def test_deck_orm_with_resources(db_session: AsyncSession) -> None:
    """Test Deckwith resources placed on it."""
    # Create deck resource definition
    deck_resource_def = ResourceDefinition(
        name="deck_with_resources_def",
        fqn="test.deck.WithResourcesDef",
    )
    db_session.add(deck_resource_def)
    await db_session.flush()

    # Create deck definition
    deck_def = DeckDefinition(
        name="deck_for_resources",
        fqn="test.deck.ForResources",
    )
    db_session.add(deck_def)
    await db_session.flush()

    # Create deck
    deck_id = uuid7()
    deck = Deck(
        name="deck_with_resources",
        fqn="test.deck.WithResources",
        asset_type=AssetType.DECK,
        deck_type_id=deck_def.accession_id,
    )
    deck.accession_id = deck_id
    deck.resource_definition = deck_resource_def
    deck.deck_type = deck_def
    db_session.add(deck)
    await db_session.flush()

    # Create resource definition for plate
    plate_def = ResourceDefinition(
        name="plate_def",
        fqn="test.resource.PlateDef",
    )
    db_session.add(plate_def)
    await db_session.flush()

    # Create resource on deck
    resource_id = uuid7()
    resource = Resource(
        name="plate_on_deck",
        fqn="test.resource.PlateOnDeck",
        asset_type=AssetType.DECK,
        current_deck_position_name="A1",
    )
    resource.accession_id = resource_id
    resource.resource_definition = plate_def
    resource.deck = deck
    db_session.add(resource)
    await db_session.flush()

    # Query back and verify relationship
    result = await db_session.execute(
        select(Deck).where(Deck.accession_id == deck_id),
    )
    retrieved_deck = result.scalars().first()

    assert retrieved_deck is not None
    # Note: May need to explicitly load relationships
    assert retrieved_deck.accession_id == deck_id

    # Query the resource to verify deck relationship
    resource_result = await db_session.execute(
        select(Resource).where(Resource.accession_id == resource_id),
    )
    retrieved_resource = resource_result.scalars().first()

    assert retrieved_resource is not None
    assert retrieved_resource.deck_accession_id == deck_id
    assert retrieved_resource.current_deck_position_name == "A1"


@pytest.mark.asyncio
async def test_deck_orm_is_resource_and_asset(
    db_session: AsyncSession, deck: Deck,
) -> None:
    """Verify that a Deckis also a Resourceand Asset."""
    # Query as Asset (using Deck since Asset is not a table)
    asset_result = await db_session.execute(
        select(Deck).where(Deck.accession_id == deck.accession_id),
    )
    asset = asset_result.scalars().first()
    assert asset is not None
    assert asset.accession_id == deck.accession_id
    assert asset.name == "test_deck_fixture"
    assert asset.asset_type == AssetType.DECK

    # Query as Resource (using Deck table in Table-Per-Class pattern)
    resource_result = await db_session.execute(
        select(Deck).where(Deck.accession_id == deck.accession_id),
    )
    resource = resource_result.scalars().first()
    assert resource is not None
    assert resource.accession_id == deck.accession_id
    assert resource.name == "test_deck_fixture"
    assert resource.status == ResourceStatusEnum.UNKNOWN


@pytest.mark.asyncio
async def test_deck_orm_relationships(
    db_session: AsyncSession,
    deck: Deck,
    deck_definition: DeckDefinition,
    resource_definition: ResourceDefinition,
) -> None:
    """Test the relationships of the Deckmodel."""
    result = await db_session.execute(
        select(Deck)
        .where(Deck.accession_id == deck.accession_id)
        .options(
            selectinload(Deck.deck_type),
            selectinload(Deck.resource_definition),
            selectinload(Deck.resources),
        ),
    )
    retrieved_deck = result.scalars().first()

    assert retrieved_deck is not None
    assert retrieved_deck.deck_type is not None
    assert retrieved_deck.deck_type.accession_id == deck_definition.accession_id
    assert retrieved_deck.resource_definition is not None
    assert (
        retrieved_deck.resource_definition.accession_id
        == resource_definition.accession_id
    )
    assert retrieved_deck.resources == []

    # Test bidirectional relationship from DeckDefinition
    result_def = await db_session.execute(
        select(DeckDefinition)
        .where(DeckDefinition.accession_id == deck_definition.accession_id)
        .options(selectinload(DeckDefinition.deck)),
    )
    retrieved_def = result_def.scalars().first()
    assert retrieved_def is not None
    assert len(retrieved_def.deck) == 1
    assert retrieved_def.deck[0].accession_id == deck.accession_id


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestDeckSchemas:
    """Tests for Deck Pydantic schemas."""

    def test_deck_base_minimal(self) -> None:
        """Test creating a DeckBase with minimal required fields."""
        deck = DeckBase(
            name="test_deck",
            asset_type=AssetType.DECK,
        )

        assert deck.name == "test_deck"
        assert deck.asset_type == "DECK"
        assert deck.status == ResourceStatusEnum.UNKNOWN
        assert deck.machine_id is None
        assert deck.deck_type_id is None

    def test_deck_base_with_all_fields(self) -> None:
        """Test creating a DeckBase with all fields populated."""
        from praxis.backend.utils.uuid import uuid7

        machine_id = uuid7()
        deck_type_id = uuid7()
        uuid7()

        deck = DeckBase(
            name="full_deck",
            fqn="test.full.Deck",
            asset_type=AssetType.DECK,
            status=ResourceStatusEnum.AVAILABLE_ON_DECK,
            machine_id=machine_id,
            deck_type_id=deck_type_id,
        )

        assert deck.name == "full_deck"
        assert deck.fqn == "test.full.Deck"
        assert deck.asset_type == "DECK"
        assert deck.status == "available_on_deck"
        assert deck.machine_id == machine_id
        assert deck.deck_type_id == deck_type_id

    def test_deck_create_inherits_from_base(self) -> None:
        """Test that DeckCreate inherits from DeckBase and ResourceCreate."""
        from praxis.backend.utils.uuid import uuid7

        resource_def_id = uuid7()

        deck = DeckCreate(
            name="create_deck",
            fqn="test.create.Deck",
            asset_type=AssetType.DECK,
            resource_definition_accession_id=resource_def_id,
        )

        assert deck.name == "create_deck"
        assert deck.fqn == "test.create.Deck"
        assert deck.asset_type == "DECK"
        assert deck.resource_definition_accession_id == resource_def_id
        assert deck.status == ResourceStatusEnum.UNKNOWN

    def test_deck_update_all_fields_optional(self) -> None:
        """Test that DeckUpdate allows all fields to be optional."""
        # DeckUpdate inherits from ResourceUpdate which requires asset_type
        update = DeckUpdate(asset_type=AssetType.DECK)

        assert update.asset_type == "DECK"
        assert update.name is None
        assert update.status is None  # Default status for update is None

        # Can update specific fields
        update_partial = DeckUpdate(
            asset_type=AssetType.DECK,
            name="updated_deck",
            status=ResourceStatusEnum.AVAILABLE_ON_DECK,
        )
        assert update_partial.name == "updated_deck"
        assert update_partial.status == "available_on_deck"

    def test_deck_response_serialization_to_dict(self) -> None:
        """Test that DeckResponse can be serialized to a dictionary."""
        from praxis.backend.utils.uuid import uuid7

        deck_id = uuid7()
        machine_id = uuid7()
        deck_type_id = uuid7()

        deck = DeckResponse(
            accession_id=deck_id,
            name="response_deck",
            fqn="test.response.Deck",
            asset_type=AssetType.DECK,
            status=ResourceStatusEnum.AVAILABLE_ON_DECK,
            machine_id=machine_id,
            deck_type_id=deck_type_id,
        )

        deck_dict = deck.model_dump()

        assert deck_dict["accession_id"] == deck_id
        assert deck_dict["name"] == "response_deck"
        assert deck_dict["fqn"] == "test.response.Deck"
        assert deck_dict["asset_type"] == "DECK"
        assert deck_dict["status"] == "available_on_deck"
        assert deck_dict["machine_id"] == machine_id
        assert deck_dict["deck_type_id"] == deck_type_id

    def test_deck_response_serialization_to_json(self) -> None:
        """Test that DeckResponse can be serialized to JSON."""
        from praxis.backend.utils.uuid import uuid7

        deck_id = uuid7()

        deck = DeckResponse(
            accession_id=deck_id,
            name="json_deck",
            fqn="test.json.Deck",
            asset_type=AssetType.DECK,
        )

        json_str = deck.model_dump_json()

        assert isinstance(json_str, str)
        assert "json_deck" in json_str
        assert str(deck_id) in json_str

    def test_deck_response_deserialization_from_dict(self) -> None:
        """Test creating DeckResponse from a dictionary."""
        from praxis.backend.utils.uuid import uuid7

        deck_id = uuid7()
        machine_id = uuid7()

        deck_data = {
            "accession_id": deck_id,
            "name": "deserialized_deck",
            "fqn": "test.deserialized.Deck",
            "asset_type": "RESOURCE",
            "status": "available_on_deck",
            "machine_id": machine_id,
        }

        deck = DeckResponse(**deck_data)

        assert deck.accession_id == deck_id
        assert deck.name == "deserialized_deck"
        assert deck.status == "available_on_deck"
        assert deck.machine_id == machine_id

    def test_deck_response_roundtrip_serialization(self) -> None:
        """Test that DeckResponse survives serialization round-trip."""
        from praxis.backend.utils.uuid import uuid7

        original = DeckResponse(
            accession_id=uuid7(),
            name="roundtrip_deck",
            fqn="test.roundtrip.Deck",
            asset_type=AssetType.DECK,
            status=ResourceStatusEnum.AVAILABLE_ON_DECK,
            deck_type_id=uuid7(),
        )

        # Serialize to dict and back
        deck_dict = original.model_dump()
        restored = DeckResponse(**deck_dict)

        assert restored.accession_id == original.accession_id
        assert restored.name == original.name
        assert restored.fqn == original.fqn
        assert restored.asset_type == original.asset_type
        assert restored.status == original.status
        assert restored.deck_type_id == original.deck_type_id

    @pytest.mark.asyncio
    async def test_deck_response_from_model(self, db_session: AsyncSession) -> None:
        """Test converting Deck to DeckResponse."""
        from praxis.backend.utils.uuid import uuid7

        # Create resource definition
        resource_def = ResourceDefinition(
            name="model_deck_resource_def",
            fqn="test.orm.DeckResourceDef",
        )
        db_session.add(resource_def)
        await db_session.flush()

        # Create deck definition
        deck_def = DeckDefinition(
            name="model_deck_def",
            fqn="test.orm.DeckDef",
        )
        db_session.add(deck_def)
        await db_session.flush()

        # Create ORM deck
        deck_id = uuid7()
        model_deck = Deck(
            # accession_id=deck_id,
            name="model_test_deck",
            fqn="test.orm.Deck",
            asset_type=AssetType.DECK,
            status=ResourceStatusEnum.AVAILABLE_ON_DECK,
            deck_type_id=deck_def.accession_id,
        )
        model_deck.accession_id = deck_id
        model_deck.resource_definition = resource_def
        model_deck.deck_type = deck_def

        db_session.add(model_deck)
        await db_session.flush()

        # Refresh with eager loading for Pydantic
        stmt = (
            select(Deck)
            .where(Deck.accession_id == deck_id)
            .options(selectinload(Deck.parent), selectinload(Deck.children))
        )
        result = await db_session.execute(stmt)
        model_deck = result.scalar_one()

        # Convert to Pydantic
        response = DeckResponse.model_validate(model_deck)

        # Verify conversion
        assert response.accession_id == deck_id
        assert response.name == "model_test_deck"
        assert response.fqn == "test.orm.Deck"
        assert response.asset_type == "DECK"
        assert response.status == "available_on_deck"
        assert response.deck_type_id == deck_def.accession_id
        assert response.resource_definition_accession_id == resource_def.accession_id

    @pytest.mark.asyncio
    async def test_deck_response_from_orm_minimal(self, db_session: AsyncSession) -> None:
        """Test ORM-to-Pydantic conversion with minimal fields."""
        from praxis.backend.utils.uuid import uuid7

        # Create resource definition
        resource_def = ResourceDefinition(
            name="minimal_deck_resource_def",
            fqn="test.minimal.DeckResourceDef",
        )
        db_session.add(resource_def)
        await db_session.flush()

        # Create deck definition
        deck_def = DeckDefinition(
            name="minimal_deck_def",
            fqn="test.minimal.DeckDef",
        )
        db_session.add(deck_def)
        await db_session.flush()

        # Create minimal deck
        deck_id = uuid7()
        model_deck = Deck(
            # accession_id=deck_id,
            name="minimal_deck",
            fqn="test.minimal.Deck",
            asset_type=AssetType.DECK,
            deck_type_id=deck_def.accession_id,
        )
        model_deck.accession_id = deck_id
        model_deck.resource_definition = resource_def
        model_deck.deck_type = deck_def

        db_session.add(model_deck)
        await db_session.flush()

        # Refresh with eager loading for Pydantic
        stmt = (
            select(Deck)
            .where(Deck.accession_id == deck_id)
            .options(selectinload(Deck.parent), selectinload(Deck.children))
        )
        result = await db_session.execute(stmt)
        model_deck = result.scalar_one()

        # Convert to Pydantic
        response = DeckResponse.model_validate(model_deck)

        # Verify
        assert response.accession_id == deck_id
        assert response.name == "minimal_deck"
        assert response.status == "unknown"  # Default
        assert response.machine_id is None  # Optional

    def test_positioning_config_model(self) -> None:
        """Test PositioningConfig Pydantic model."""
        config = PositioningConfig(
            method_name="slot_to_location",
            arg_name="slot",
            arg_type="str",
            params={"offset_x": 10.0, "offset_y": 5.0},
        )

        assert config.method_name == "slot_to_location"
        assert config.arg_name == "slot"
        assert config.arg_type == "str"
        assert config.params["offset_x"] == 10.0

    def test_deck_position_definition_create(self) -> None:
        """Test DeckPositionDefinitionCreate model."""
        position = DeckPositionDefinitionCreate(
            name="test_position",
            nominal_x_mm=100.0,
            nominal_y_mm=200.0,
            nominal_z_mm=10.0,
            pylabrobot_position_type_name="Slot",
            accepts_plates=True,
            accepts_tips=False,
            notes="Position A1 for 96-well plates",
        )

        assert position.nominal_x_mm == 100.0
        assert position.nominal_y_mm == 200.0
        assert position.nominal_z_mm == 10.0
        assert position.pylabrobot_position_type_name == "Slot"
        assert position.accepts_plates is True
        assert position.accepts_tips is False
        assert position.notes == "Position A1 for 96-well plates"

    def test_deck_position_definition_response(self) -> None:
        """Test DeckPositionDefinitionResponse model."""
        from praxis.backend.utils.uuid import uuid7

        deck_type_id = uuid7()

        position = DeckPositionDefinitionResponse(
            nominal_x_mm=100.0,
            nominal_y_mm=200.0,
            nominal_z_mm=10.0,
            deck_type_accession_id=deck_type_id,
        )

        assert position.nominal_x_mm == 100.0
        assert position.nominal_y_mm == 200.0
        assert position.nominal_z_mm == 10.0
        assert position.deck_type_accession_id == deck_type_id

    def test_deck_position_definition_with_compatible_resources(self) -> None:
        """Test DeckPositionDefinitionCreate with compatible_resource_fqns."""
        compatible_resources = {
            "plates": ["corning_96_wellplate", "greiner_96_wellplate"],
            "tips": [],
        }

        position = DeckPositionDefinitionCreate(
            name="compatible_position",
            nominal_x_mm=100.0,
            nominal_y_mm=200.0,
            nominal_z_mm=10.0,
            compatible_resource_fqns=compatible_resources,
            accepts_plates=True,
        )

        assert position.compatible_resource_fqns == compatible_resources
        assert "plates" in position.compatible_resource_fqns
        assert len(position.compatible_resource_fqns["plates"]) == 2
