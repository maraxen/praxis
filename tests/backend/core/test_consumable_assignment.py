
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from praxis.backend.core.consumable_assignment import ConsumableAssignmentService
from praxis.backend.utils.uuid import uuid7, uuid4
from praxis.backend.models.domain.protocol import (
    AssetRequirementRead, 
    AssetConstraintsModel, 
    LocationConstraintsModel
)
from praxis.backend.models.domain.resource import Resource
from praxis.backend.models.domain.resource import ResourceDefinition

# Helper to create mock resources
def create_mock_resource(
    accession_id, fqn, name, 
    nominal_volume_ul=None, 
    plate_type=None,
    num_items=96,
    properties=None
):
    resource = MagicMock(spec=Resource)
    # Ensure accession_id is a UUID if it's a string that looks like one, or just use as is
    try:
        if isinstance(accession_id, str):
            resource.accession_id = uuid.UUID(accession_id)
        else:
            resource.accession_id = accession_id
    except ValueError:
        resource.accession_id = accession_id

    resource.name = name
    resource.fqn = fqn
    
    definition = MagicMock(spec=ResourceDefinition)
    definition.fqn = fqn
    definition.nominal_volume_ul = nominal_volume_ul
    definition.plate_type = plate_type
    definition.num_items = num_items
    
    # Setup relationship
    resource.resource_definition = definition
    # Direct properties for easy access in our code
    resource.properties_json = properties or {}
    resource.plr_state = {}
    resource.plr_definition = {}
    
    return resource

@pytest.fixture
def mock_db_session():
    session = AsyncMock()
    return session

@pytest.fixture
def service(mock_db_session):
    return ConsumableAssignmentService(mock_db_session)

@pytest.mark.asyncio
async def test_find_compatible_consumable_match(service, mock_db_session):
    # Requirement: 96-well plate, >100ul
    req = AssetRequirementRead(
        accession_id=uuid7(),
        name="source_plate",
        fqn="pylabrobot.resources.Plate",
        type_hint_str="Plate",
        constraints=AssetConstraintsModel(min_volume_ul=100)
    )
    
    # Candidates
    res_id = uuid7()
    candidate1 = create_mock_resource(
        res_id, "pylabrobot.resources.corning.Cor_96_wellplate_360ul_Fb", "Plate 1",
        nominal_volume_ul=360
    )
    
    # Setup Mocks
    service._get_reserved_asset_ids = AsyncMock(return_value=set())
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [candidate1]
    mock_db_session.execute.return_value = mock_result
    
    result = await service.find_compatible_consumable(req)
    
    assert result == str(res_id)

@pytest.mark.asyncio
async def test_find_compatible_consumable_no_match_volume(service, mock_db_session):
    # Requirement: High volume plate
    req = AssetRequirementRead(
        accession_id=uuid7(),
        name="deep_well",
        fqn="pylabrobot.resources.Plate",
        type_hint_str="Plate",
        constraints=AssetConstraintsModel(min_volume_ul=1000)
    )
    
    # Candidates: Low volume plate
    candidate1 = create_mock_resource(
        uuid7(), "pylabrobot.resources.corning.Cor_96_wellplate_360ul_Fb", "Plate 1",
        nominal_volume_ul=360
    )
    
    service._get_reserved_asset_ids = AsyncMock(return_value=set())
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [candidate1]
    mock_db_session.execute.return_value = mock_result
    
    with pytest.raises(ValueError, match="No compatible consumables found"):
        await service.find_compatible_consumable(req)

@pytest.mark.asyncio
async def test_find_compatible_consumable_invalid_workcell_id(service):
    req = AssetRequirementRead(
        accession_id=uuid7(),
        name="plate",
        fqn="pylabrobot.resources.Plate",
        type_hint_str="Plate"
    )
    
    with pytest.raises(ValueError, match="Invalid accession_id format for workcell_id"):
        await service.find_compatible_consumable(req, workcell_id="not-a-uuid")

@pytest.mark.asyncio
async def test_find_compatible_consumable_expired_warning(service, mock_db_session):
    # Requirement
    req = AssetRequirementRead(
        accession_id=uuid7(),
        name="reagent",
        fqn="pylabrobot.resources.Reservoir",
        type_hint_str="Reservoir"
    )
    
    expired_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    
    res_id = uuid7()
    candidate1 = create_mock_resource(
        res_id, "pylabrobot.resources.Reservoir", "Expired Reservoir",
        properties={"expiration_date": expired_date}
    )
    
    service._get_reserved_asset_ids = AsyncMock(return_value=set())
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [candidate1]
    mock_db_session.execute.return_value = mock_result
    
    result = await service.find_compatible_consumable(req)
    assert result == str(res_id)

@pytest.mark.asyncio
async def test_find_compatible_consumable_reserved_excluded(service, mock_db_session):
    req = AssetRequirementRead(
        accession_id=uuid7(),
        name="plate",
        fqn="pylabrobot.resources.Plate",
        type_hint_str="Plate"
    )
    
    res_id1 = uuid7()
    candidate1 = create_mock_resource(res_id1, "pylabrobot.resources.Plate", "Plate 1")
    
    # res1 is reserved
    service._get_reserved_asset_ids = AsyncMock(return_value={res_id1})
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [candidate1]
    mock_db_session.execute.return_value = mock_result
    
    # Should raise ValueError because no other candidates
    with pytest.raises(ValueError, match="No candidate consumables found"):
        await service.find_compatible_consumable(req)
    
    # Add a second candidate that is free
    res_id2 = uuid7()
    candidate2 = create_mock_resource(res_id2, "pylabrobot.resources.Plate", "Plate 2")
    mock_result.scalars.return_value.all.return_value = [candidate1, candidate2]
    
    result = await service.find_compatible_consumable(req)
    assert result == str(res_id2)

class TestIsConsumable:
    """Tests for _is_consumable type detection."""

    @pytest.fixture
    def service(self, mock_db_session):
        return ConsumableAssignmentService(mock_db_session)

    @pytest.mark.parametrize("type_hint,expected", [
        ("pylabrobot.resources.Plate", True),
        ("pylabrobot.resources.TipRack", True),
        ("pylabrobot.resources.Trough", True),
        ("pylabrobot.resources.Reservoir", True),
        ("pylabrobot.resources.Tube", True),
        ("pylabrobot.resources.Well", True),
        ("pylabrobot.machines.LiquidHandler", False),
        ("pylabrobot.resources.Deck", False),
        ("str", False),
    ])
    def test_is_consumable_type_detection(self, service, type_hint, expected):
        """Verify type hint detection for consumables."""
        req = AssetRequirementRead(
            accession_id=uuid7(),
            name="test",
            fqn=type_hint,
            type_hint_str=type_hint.split(".")[-1]  # Just the class name
        )
        assert service._is_consumable(req) == expected

class TestTypeMatches:
    """Tests for _type_matches FQN pattern matching."""

    @pytest.fixture
    def service(self, mock_db_session):
        return ConsumableAssignmentService(mock_db_session)

    @pytest.mark.parametrize("required,resource_fqn,expected", [
        ("plate", "pylabrobot.resources.corning.Cor_96_wellplate", True),
        ("plate", "pylabrobot.resources.microplate", True),
        ("tip", "pylabrobot.resources.tip_rack", True),
        ("tip", "pylabrobot.resources.tiprack", True),
        ("trough", "pylabrobot.resources.reservoir", True),
        ("plate", "pylabrobot.machines.LiquidHandler", False),
    ])
    def test_type_matching_patterns(self, service, required, resource_fqn, expected):
        """Verify FQN pattern matching logic."""
        assert service._type_matches(required, resource_fqn) == expected

class TestCandidateScoring:
    """Tests for multi-factor candidate scoring."""

    @pytest.mark.asyncio
    async def test_multiple_candidates_best_score_wins(self, service, mock_db_session):
        """Verify highest scoring candidate is selected."""
        res_id1 = uuid7()
        candidate_good = create_mock_resource(
            res_id1, "pylabrobot.resources.Plate", "Good Plate",
            nominal_volume_ul=500
        )
        res_id2 = uuid7()
        candidate_ok = create_mock_resource(
            res_id2, "pylabrobot.resources.Plate", "OK Plate",
            nominal_volume_ul=200
        )
        
        req = AssetRequirementRead(
            accession_id=uuid7(),
            name="plate",
            fqn="pylabrobot.resources.Plate",
            type_hint_str="Plate",
            constraints=AssetConstraintsModel(min_volume_ul=400)
        )
        
        service._get_reserved_asset_ids = AsyncMock(return_value=set())
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [candidate_ok, candidate_good]
        mock_db_session.execute.return_value = mock_result
        
        result = await service.find_compatible_consumable(req)
        assert result == str(res_id1)

@pytest.mark.asyncio
async def test_auto_assign_consumables_success(service, mock_db_session):
    req1 = AssetRequirementRead(
        accession_id=uuid7(),
        name="plate1",
        type_hint_str="Plate"
    )
    req2 = AssetRequirementRead(
        accession_id=uuid7(),
        name="tiprack1",
        type_hint_str="TipRack"
    )
    
    res_id1 = uuid7()
    res_id2 = uuid7()
    
    cand1 = create_mock_resource(res_id1, "pylabrobot.resources.Plate", "Plate 1")
    cand2 = create_mock_resource(res_id2, "pylabrobot.resources.TipRack", "Tips 1")
    
    service._get_reserved_asset_ids = AsyncMock(return_value=set())
    
    # Mocking _get_candidate_resources to return different things for different calls
    # or just mock find_compatible_consumable
    service.find_compatible_consumable = AsyncMock()
    service.find_compatible_consumable.side_effect = [str(res_id1), str(res_id2)]
    
    results = await service.auto_assign_consumables([req1, req2], {})
    
    assert results["plate1"] == str(res_id1)
    assert results["tiprack1"] == str(res_id2)

@pytest.mark.asyncio
async def test_auto_assign_consumables_invalid_existing(service):
    req = AssetRequirementRead(
        accession_id=uuid7(),
        name="plate1",
        type_hint_str="Plate"
    )
    
    with pytest.raises(ValueError, match="Invalid accession_id format for existing_assignment"):
        await service.auto_assign_consumables([req], {"some_req": "not-a-uuid"})

@pytest.mark.asyncio
async def test_validate_accession_id_versions(service):
    # UUID v4 should pass
    v4 = uuid4()
    assert service._validate_accession_id(v4, "test") == v4
    assert service._validate_accession_id(str(v4), "test") == v4
    
    # UUID v7 should pass
    v7 = uuid7()
    assert service._validate_accession_id(v7, "test") == v7
    assert service._validate_accession_id(str(v7), "test") == v7
    
    # UUID v1 should pass but log a warning (which we don't easily check here)
    v1 = uuid.uuid1()
    assert service._validate_accession_id(v1, "test") == v1
    
    # Missing should raise
    with pytest.raises(ValueError, match="Missing accession_id"):
        service._validate_accession_id(None, "test")
    
    # Invalid format should raise
    with pytest.raises(ValueError, match="Invalid accession_id format"):
        service._validate_accession_id("invalid-uuid", "test")
