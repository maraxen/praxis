# pylint: disable=broad-except, too-many-lines
"""Service layer for Resource  Management."""

import enum
import uuid
from typing import Any, cast

from sqlalchemy import and_, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import SQLModel

from praxis.backend.models.domain.filters import SearchFilters
from praxis.backend.models.domain.resource import (
  Resource as Resource,
)
from praxis.backend.models.domain.resource import (
  ResourceCreate,
  ResourceUpdate,
)
from praxis.backend.models.enums.resource import ResourceStatusEnum
from praxis.backend.services.utils.crud_base import CRUDBase
from praxis.backend.services.utils.query_builder import (
  apply_date_range_filters,
  apply_pagination,
  apply_property_filters,
  apply_specific_id_filters,
)
from praxis.backend.services.utils.validation import validate_accession_ids
from praxis.backend.utils.db import Base
from praxis.backend.utils.db_decorator import handle_db_transaction
from praxis.backend.utils.logging import get_logger

logger = get_logger(__name__)

UUID = uuid.UUID


class ResourceService(CRUDBase[Resource, ResourceCreate, ResourceUpdate]):
  """Service for resource-related operations."""

  @validate_accession_ids
  @handle_db_transaction
  async def create(
    self,
    db: AsyncSession,
    *,
    obj_in: ResourceCreate,
  ) -> Resource:
    """Create a new resource."""
    logger.info(
      "Attempting to create resource '%s' for parent ID %s.",
      obj_in.name,
      obj_in.parent_accession_id,
    )

    resource_model = await super().create(db=db, obj_in=obj_in)

    if obj_in.plr_state:
      resource_model.plr_state = obj_in.plr_state
      flag_modified(resource_model, "plr_state")

    await db.flush()
    # Refresh with relationships loaded for serialization
    await db.refresh(
      resource_model,
      ["children", "parent", "resource_definition"],
    )
    logger.info(
      "Successfully created resource '%s' with ID %s.",
      resource_model.name,
      resource_model.accession_id,
    )
    return resource_model

  @validate_accession_ids
  async def get(
    self,
    db: AsyncSession,
    accession_id: UUID,
  ) -> Resource | None:
    """Retrieve a specific resource by its ID."""
    logger.info("Attempting to retrieve resource with ID: %s.", accession_id)
    stmt = (
      select(self.model)
      .options(
        selectinload(self.model.children),
        joinedload(self.model.parent),
        joinedload(self.model.resource_definition),
      )
      .filter(self.model.accession_id == accession_id)
    )
    result = await db.execute(stmt)
    resource = result.scalar_one_or_none()
    if resource:
      logger.info(
        "Successfully retrieved resource ID %s: '%s'.",
        accession_id,
        resource.name,
      )
    else:
      logger.info("Resource with ID %s not found.", accession_id)
    return resource

  async def get_multi(
    self,
    db: AsyncSession,
    *,
    filters: SearchFilters,
    fqn: str | None = None,
    status: str | None = None,
  ) -> list[Resource]:
    """List all resources, with optional filtering by parent ID."""
    logger.info(
      "Listing resources with filters: %s",
      filters.model_dump_json(),
    )
    stmt = select(self.model).options(
      joinedload(self.model.parent),
      selectinload(self.model.children),
      joinedload(self.model.resource_definition),
    )

    conditions = []

    if filters.parent_accession_id is not None:
      conditions.append(
        self.model.parent_accession_id == filters.parent_accession_id,
      )

    if fqn:
      conditions.append(self.model.fqn == fqn)

    if status:
      conditions.append(self.model.status == status)

    if conditions:
      stmt = stmt.filter(and_(*conditions))

    if not (issubclass(self.model, Base) or issubclass(self.model, SQLModel)):
      msg = f"Model {self.model.__name__} must inherit from Base or SQLModel to use generic filters."
      raise TypeError(msg)
    stmt = apply_specific_id_filters(stmt, filters, self.model)
    stmt = apply_date_range_filters(stmt, filters, self.model.created_at)
    stmt = apply_property_filters(
      stmt,
      filters,
      self.model.properties_json,
    )

    stmt = apply_pagination(stmt, filters)

    stmt = stmt.order_by(self.model.name)
    result = await db.execute(stmt)
    resources = list(result.scalars().all())
    logger.info("Found %s resources.", len(resources))
    return resources

  def _convert_enums(self, update_data: dict) -> dict:
    """Convert enum string values to enum members for SQLAlchemy."""
    for attr_name, column in sa_inspect(self.model).columns.items():
      if attr_name in update_data and hasattr(
        column.type,
        "enum_class",
      ):
        enum_class = getattr(column.type, "enum_class", None)
        if enum_class and issubclass(enum_class, enum.Enum):
          value = update_data[attr_name]
          if isinstance(value, str):
            for member in enum_class:
              if member.value == value:
                update_data[attr_name] = member
                break
    return update_data

  @validate_accession_ids
  @handle_db_transaction
  async def update(
    self,
    db: AsyncSession,
    *,
    db_obj: Resource,
    obj_in: ResourceUpdate | dict,
  ) -> Resource:
    """Update an existing resource."""
    logger.info(
      "Attempting to update resource with ID: %s.",
      db_obj.accession_id,
    )

    obj_in_model = ResourceUpdate(**obj_in) if isinstance(obj_in, dict) else obj_in
    update_data = obj_in_model.model_dump(exclude_unset=True)

    for field in [
      "children",
      "parent",
      "created_at",
      "updated_at",
      "accession_id",
    ]:
      update_data.pop(field, None)

    update_data = self._convert_enums(update_data)

    for field, value in update_data.items():
      if hasattr(db_obj, field):
        setattr(db_obj, field, value)

    if "plr_state" in update_data:
      flag_modified(db_obj, "plr_state")

    db.add(db_obj)
    await db.flush()
    await db.refresh(
      db_obj,
    )
    logger.info(
      "Successfully updated resource ID %s: '%s'.",
      db_obj.accession_id,
      db_obj.name,
    )
    return db_obj

  @validate_accession_ids
  @handle_db_transaction
  async def remove(
    self,
    db: AsyncSession,
    *,
    accession_id: UUID,
  ) -> Resource | None:
    """Delete a specific resource by its ID."""
    logger.info("Attempting to delete resource with ID: %s.", accession_id)
    resource_model = await super().remove(db, accession_id=accession_id)
    if not resource_model:
      logger.warning(
        "Resource with ID %s not found for deletion.",
        accession_id,
      )
      return None

    logger.info(
      "Successfully deleted resource ID %s: '%s'.",
      accession_id,
      resource_model.name,
    )
    return resource_model

  @validate_accession_ids
  @handle_db_transaction
  async def update_resource_location_and_status(
    self,
    db: AsyncSession,
    *,
    resource_accession_id: uuid.UUID,
    new_status: ResourceStatusEnum,
    status_details: str | None = None,
    location_machine_accession_id: uuid.UUID | None = None,
    current_deck_position_name: str | None = None,
  ) -> Resource | None:
    """Update the location and status of a resource."""
    resource = await self.get(db, resource_accession_id)
    if not resource:
      return None

    update_data = {
      "status": new_status,
      "status_details": status_details,
      "machine_location_accession_id": location_machine_accession_id,
      "current_deck_position_name": current_deck_position_name,
    }
    update_data = {k: v for k, v in update_data.items() if v is not None}

    return await self.update(
      db,
      db_obj=resource,
      obj_in=ResourceUpdate(**cast("dict[str, Any]", update_data)),
    )


resource_service = ResourceService(Resource)
