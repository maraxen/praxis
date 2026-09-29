"""Unit tests for AssetRequirementmodel."""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.protocol import (
    AssetRequirement,
    FunctionProtocolDefinition,
)


@pytest_asyncio.fixture
async def protocol_definition(db_session: AsyncSession) -> FunctionProtocolDefinition:
    """Create a FunctionProtocolDefinitionfor testing."""
    protocol = FunctionProtocolDefinition(
        name="test_protocol",
        fqn="test.protocols.test_protocol",
        version="1.0.0",
        source_file_path="protocols/test_protocol.py",
        module_name="test.protocols",
        function_name="test_protocol",
    )
    db_session.add(protocol)
    await db_session.flush()
    return protocol


@pytest.mark.asyncio
async def test_asset_requirement_orm_creation_minimal(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test creating AssetRequirementwith minimal required fields."""
    asset = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
    )
    db_session.add(asset)
    await db_session.flush()

    # Verify creation with defaults
    assert asset.accession_id is not None
    assert asset.protocol_definition_accession_id == protocol_definition.accession_id
    assert asset.name == ""  # Default
    assert asset.type_hint_str == ""  # Default
    assert asset.actual_type_str == ""  # Default
    assert asset.fqn == ""  # Default
    assert asset.optional is False  # Default
    assert asset.default_value_repr is None
    assert asset.description is None
    assert asset.constraints_json is None
    assert asset.location_constraints_json is None


@pytest.mark.asyncio
async def test_asset_requirement_orm_creation_with_all_fields(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test creating AssetRequirementwith all fields populated."""
    constraints = {"capacity_min": 96, "type": "wellplate"}
    location_constraints = {"allowed_positions": ["A1", "A2", "A3"]}

    asset = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="source_plate",
        type_hint_str="Resource",
        actual_type_str="Plate",
        fqn="pylabrobot.resources.Plate",
        optional=True,
        default_value_repr="None",
        description="Source plate for liquid transfers",
        constraints_json=constraints,
        location_constraints_json=location_constraints,
    )
    db_session.add(asset)
    await db_session.flush()

    # Verify all fields
    assert asset.accession_id is not None
    assert asset.protocol_definition_accession_id == protocol_definition.accession_id
    assert asset.name == "source_plate"
    assert asset.type_hint_str == "Resource"
    assert asset.actual_type_str == "Plate"
    assert asset.fqn == "pylabrobot.resources.Plate"
    assert asset.optional is True
    assert asset.default_value_repr == "None"
    assert asset.description == "Source plate for liquid transfers"
    assert asset.constraints_json == constraints
    assert asset.location_constraints_json == location_constraints


@pytest.mark.asyncio
async def test_asset_requirement_orm_persist_to_database(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test full persistence cycle for AssetRequirement."""
    asset = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="liquid_handler",
        type_hint_str="LiquidHandler",
        actual_type_str="STAR",
        fqn="pylabrobot.legacy.liquid_handling.backends.hamilton.STAR",
        optional=False,
        description="Hamilton STAR liquid handler",
    )
    db_session.add(asset)
    await db_session.flush()

    # Query back
    result = await db_session.execute(
        select(AssetRequirement).where(AssetRequirement.accession_id == asset.accession_id),
    )
    retrieved = result.scalars().first()

    # Verify persistence
    assert retrieved is not None
    assert retrieved.accession_id == asset.accession_id
    assert retrieved.name == "liquid_handler"
    assert retrieved.type_hint_str == "LiquidHandler"
    assert retrieved.actual_type_str == "STAR"
    assert retrieved.fqn == "pylabrobot.legacy.liquid_handling.backends.hamilton.STAR"
    assert retrieved.optional is False
    assert retrieved.description == "Hamilton STAR liquid handler"


@pytest.mark.asyncio
async def test_asset_requirement_orm_unique_constraint(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test unique constraint on (protocol_definition_accession_id, name)."""
    # Create first asset
    asset1 = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="unique_asset",
        type_hint_str="Resource",
        actual_type_str="Plate",
        fqn="pylabrobot.resources.Plate",
    )
    db_session.add(asset1)
    await db_session.flush()

    # Try to create another with same protocol and name
    asset2 = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="unique_asset",  # Duplicate name for same protocol
        type_hint_str="Resource",
        actual_type_str="TipRack",
        fqn="pylabrobot.resources.TipRack",
    )
    db_session.add(asset2)

    # Should raise IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_asset_requirement_orm_optional_flag(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test optional flag for asset requirements."""
    # Required asset
    required_asset = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="required_asset",
        type_hint_str="Resource",
        actual_type_str="Plate",
        fqn="pylabrobot.resources.Plate",
        optional=False,
    )
    db_session.add(required_asset)
    await db_session.flush()
    assert required_asset.optional is False

    # Optional asset with default
    optional_asset = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="optional_asset",
        type_hint_str="Resource",
        actual_type_str="TipRack",
        fqn="pylabrobot.resources.TipRack",
        optional=True,
        default_value_repr="None",
    )
    db_session.add(optional_asset)
    await db_session.flush()
    assert optional_asset.optional is True
    assert optional_asset.default_value_repr == "None"


@pytest.mark.asyncio
async def test_asset_requirement_orm_type_hints(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test type_hint_str vs actual_type_str fields."""
    # Asset with abstract type hint and concrete actual type
    asset = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="typed_asset",
        type_hint_str="Resource",  # Abstract type hint from function signature
        actual_type_str="Corning_96_CorningWellPlate",  # Concrete type
        fqn="pylabrobot.resources.corning_costar.Corning_96_CorningWellPlate",
    )
    db_session.add(asset)
    await db_session.flush()

    # Verify both type fields
    assert asset.type_hint_str == "Resource"
    assert asset.actual_type_str == "Corning_96_CorningWellPlate"


@pytest.mark.asyncio
async def test_asset_requirement_orm_jsonb_constraints(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test JSONB constraints field for asset validation rules."""
    constraints = {
        "capacity": 96,
        "well_volume_ul": 360,
        "consumable": True,
        "allowed_types": ["wellplate", "reservoir"],
    }

    asset = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="constrained_asset",
        type_hint_str="Resource",
        actual_type_str="Plate",
        fqn="pylabrobot.resources.Plate",
        constraints_json=constraints,
    )
    db_session.add(asset)
    await db_session.flush()

    # Verify JSONB storage and retrieval
    assert asset.constraints_json == constraints
    assert asset.constraints_json["capacity"] == 96
    assert asset.constraints_json["consumable"] is True
    assert asset.constraints_json["allowed_types"] == ["wellplate", "reservoir"]


@pytest.mark.asyncio
async def test_asset_requirement_orm_jsonb_location_constraints(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test JSONB location_constraints field for asset placement rules."""
    location_constraints = {
        "allowed_positions": ["A1", "B1", "C1"],
        "required_carrier": "PlateCarrier",
        "max_height_mm": 100,
    }

    asset = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="positioned_asset",
        type_hint_str="Resource",
        actual_type_str="Plate",
        fqn="pylabrobot.resources.Plate",
        location_constraints_json=location_constraints,
    )
    db_session.add(asset)
    await db_session.flush()

    # Verify JSONB storage and retrieval
    assert asset.location_constraints_json == location_constraints
    assert asset.location_constraints_json["allowed_positions"] == ["A1", "B1", "C1"]
    assert asset.location_constraints_json["max_height_mm"] == 100


@pytest.mark.asyncio
async def test_asset_requirement_orm_relationship_to_protocol(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test relationship between AssetRequirementand FunctionProtocolDefinition."""
    # Create multiple assets for the same protocol
    asset1 = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="asset1",
        type_hint_str="Resource",
        actual_type_str="Plate",
        fqn="pylabrobot.resources.Plate",
    )

    asset2 = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="asset2",
        type_hint_str="LiquidHandler",
        actual_type_str="STAR",
        fqn="pylabrobot.legacy.liquid_handling.backends.hamilton.STAR",
    )

    db_session.add(asset1)
    db_session.add(asset2)
    await db_session.flush()

    # Query protocol and check assets relationship
    result = await db_session.execute(
        select(FunctionProtocolDefinition).where(
            FunctionProtocolDefinition.accession_id == protocol_definition.accession_id,
        ),
    )
    protocol = result.scalars().first()

    # Verify bidirectional relationship
    assert len(protocol.assets) >= 2
    asset_names = [a.name for a in protocol.assets]
    assert "asset1" in asset_names
    assert "asset2" in asset_names


@pytest.mark.asyncio
async def test_asset_requirement_orm_query_by_protocol(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test querying asset requirements by protocol definition."""
    # Create assets for this protocol
    asset1 = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="query_asset1",
        type_hint_str="Resource",
        actual_type_str="Plate",
        fqn="pylabrobot.resources.Plate",
    )

    asset2 = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="query_asset2",
        type_hint_str="Resource",
        actual_type_str="TipRack",
        fqn="pylabrobot.resources.TipRack",
    )

    db_session.add(asset1)
    db_session.add(asset2)
    await db_session.flush()

    # Query all assets for this protocol
    result = await db_session.execute(
        select(AssetRequirement).where(
            AssetRequirement.protocol_definition_accession_id
            == protocol_definition.accession_id,
        ),
    )
    assets = result.scalars().all()

    # Should find at least our 2 assets
    assert len(assets) >= 2
    asset_names = [a.name for a in assets]
    assert "query_asset1" in asset_names
    assert "query_asset2" in asset_names


@pytest.mark.asyncio
async def test_asset_requirement_orm_repr(
    db_session: AsyncSession,
    protocol_definition: FunctionProtocolDefinition,
) -> None:
    """Test string representation of AssetRequirement."""
    asset = AssetRequirement(
        protocol_definition_accession_id=protocol_definition.accession_id,
        protocol_definition=protocol_definition,
        name="repr_asset",
        type_hint_str="Resource",
        actual_type_str="Plate",
        fqn="pylabrobot.resources.Plate",
    )

    repr_str = repr(asset)
    assert "AssetRequirement" in repr_str
    assert "repr_asset" in repr_str
    assert str(protocol_definition.accession_id) in repr_str
