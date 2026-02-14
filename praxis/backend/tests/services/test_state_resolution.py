import pytest
import uuid
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from praxis.backend.services.state_resolution_service import StateResolutionService
from praxis.backend.utils.errors import AccessionNotFoundError
from praxis.backend.models.enums.schedule import ScheduleStatusEnum
from praxis.backend.models.domain.schedule import ScheduleEntry
from sqlalchemy.ext.asyncio import AsyncSession
from praxis.backend.core.simulation.state_resolution import StateResolution, ResolutionType

class MockSession(AsyncSession):
    def __init__(self):
        pass

@pytest.fixture
def mock_db_session():
    """Fixture for a mocked SQLAlchemy async session."""
    mock = MagicMock(spec=MockSession)
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock

@pytest.mark.asyncio
async def test_get_uncertain_states_accession_not_found(mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    service = StateResolutionService(mock_db_session)
    random_id = uuid.uuid4()
    
    with pytest.raises(AccessionNotFoundError) as excinfo:
        await service.get_uncertain_states(random_id)
    
    assert excinfo.value.entity_type == "ScheduleEntry"
    assert excinfo.value.accession == random_id

@pytest.mark.asyncio
async def test_resolve_states_accession_not_found(mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    service = StateResolutionService(mock_db_session)
    random_id = uuid.uuid4()
    resolution = MagicMock()
    
    with pytest.raises(AccessionNotFoundError) as excinfo:
        await service.resolve_states(random_id, resolution)
    
    assert excinfo.value.entity_type == "ScheduleEntry"
    assert excinfo.value.accession == random_id

@pytest.mark.asyncio
async def test_resume_run_accession_not_found(mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    service = StateResolutionService(mock_db_session)
    random_id = uuid.uuid4()
    
    with pytest.raises(AccessionNotFoundError) as excinfo:
        # Now we DON'T pass mock_db_session as it should be found in service._session
        await service.resume_run(random_id)
    
    assert excinfo.value.entity_type == "ScheduleEntry"
    assert excinfo.value.accession == random_id

@pytest.mark.asyncio
async def test_abort_run_accession_not_found(mock_db_session):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    service = StateResolutionService(mock_db_session)
    random_id = uuid.uuid4()
    
    with pytest.raises(AccessionNotFoundError) as excinfo:
        # Now we DON'T pass mock_db_session as it should be found in service._session
        await service.abort_run(random_id)
    
    assert excinfo.value.entity_type == "ScheduleEntry"
    assert excinfo.value.accession == random_id

@pytest.mark.asyncio
async def test_resolve_states_missing_snapshot_warning(mock_db_session, caplog):
    # Setup mock schedule entry
    run_id = uuid.uuid4()
    mock_entry = MagicMock(spec=ScheduleEntry)
    mock_entry.accession_id = run_id
    mock_entry.protocol_run_accession_id = uuid.uuid4()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_entry
    mock_db_session.execute.return_value = mock_result
    
    service = StateResolutionService(mock_db_session)
    
    resolution = StateResolution(
        operation_id="test_op",
        resolution_type=ResolutionType.CONFIRMED_SUCCESS,
        resolved_values={"plate.A1.volume": 100}
    )
    
    with caplog.at_level(logging.WARNING):
        await service.resolve_states(run_id, resolution)
    
    assert "No state snapshot found for run" in caplog.text
    assert str(run_id) in caplog.text
