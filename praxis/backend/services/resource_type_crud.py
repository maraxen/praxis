"""CRUD service for resource type definitions."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.resource import (
  ResourceDefinition,
  ResourceDefinitionCreate,
  ResourceDefinitionUpdate,
)
from praxis.backend.services.utils.crud_base import CRUDBase
from praxis.backend.services.utils.validation import validate_accession_ids


class ResourceTypeDefinitionCRUDService(
  CRUDBase[
    ResourceDefinition,
    ResourceDefinitionCreate,
    ResourceDefinitionUpdate,
  ],
):
  """CRUD service for resource type definitions."""

  @validate_accession_ids
  async def create(
    self, db: AsyncSession, *, obj_in: ResourceDefinitionCreate
  ) -> ResourceDefinition:
    """Create a new resource definition."""
    return await super().create(db=db, obj_in=obj_in)

  @validate_accession_ids
  async def get(self, db: AsyncSession, accession_id: Any) -> ResourceDefinition | None:
    """Get a resource definition by accession ID."""
    return await super().get(db=db, accession_id=accession_id)

  @validate_accession_ids
  async def update(
    self,
    db: AsyncSession,
    *,
    db_obj: ResourceDefinition,
    obj_in: ResourceDefinitionUpdate | dict[str, Any],
  ) -> ResourceDefinition:
    """Update an existing resource definition."""
    obj_in_model = ResourceDefinitionUpdate(**obj_in) if isinstance(obj_in, dict) else obj_in
    return await super().update(db=db, db_obj=db_obj, obj_in=obj_in_model)

  @validate_accession_ids
  async def remove(self, db: AsyncSession, *, accession_id: Any) -> ResourceDefinition | None:
    """Remove a resource definition."""
    return await super().remove(db=db, accession_id=accession_id)
