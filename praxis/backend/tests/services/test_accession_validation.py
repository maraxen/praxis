
import pytest
import uuid
from unittest.mock import AsyncMock
from praxis.backend.services.resource import resource_service
from praxis.backend.services.resource_type_crud import ResourceTypeDefinitionCRUDService
from praxis.backend.models.domain.resource import ResourceDefinition

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.mark.asyncio
async def test_resource_service_accession_validation(mock_db):
    # Test with invalid accession_id in get
    with pytest.raises(ValueError, match="Invalid accession ID format"):
        await resource_service.get(mock_db, "not-a-uuid")

    # Test with invalid parent_accession_id in create
    with pytest.raises(ValueError, match="Invalid accession ID format"):
        await resource_service.create(mock_db, obj_in={"name": "Test", "parent_accession_id": "invalid"})

@pytest.mark.asyncio
async def test_resource_definition_service_accession_validation(mock_db):
    service = ResourceTypeDefinitionCRUDService(ResourceDefinition)
    
    with pytest.raises(ValueError, match="Invalid accession ID format"):
        await service.get(mock_db, "not-a-uuid")
        
    with pytest.raises(ValueError, match="Invalid accession ID format"):
        await service.remove(mock_db, accession_id="not-a-uuid")
