# pylint: disable=too-few-public-methods,missing-class-docstring
"""Unified SQLModel definitions for Resource and ResourceDefinition."""

import uuid
from typing import TYPE_CHECKING, Any, Optional

from pydantic import AliasChoices, ConfigDict
from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

from praxis.backend.models.domain.asset import Asset, AssetBase, AssetRead, AssetUpdate
from praxis.backend.models.domain.sqlmodel_base import PraxisBase
from praxis.backend.models.enums.resource import ResourceStatusEnum
from praxis.backend.utils.db import JsonVariant

if TYPE_CHECKING:
  from praxis.backend.models.domain.deck import Deck, DeckDefinition
  from praxis.backend.models.domain.machine import Machine
  from praxis.backend.models.domain.outputs import FunctionDataOutput
  from praxis.backend.models.domain.protocol import AssetRequirement, ProtocolRun
  from praxis.backend.models.domain.workcell import Workcell

# =============================================================================
# Resource Definition (Catalog)
# =============================================================================


class ResourceDefinitionBase(PraxisBase):
  """Base schema for ResourceDefinition - shared fields for create/update/response."""

  fqn: str = Field(index=True, unique=True, description="Fully qualified name")
  description: str | None = Field(default=None, description="Description of the resource type")
  plr_category: str | None = Field(default=None, description="PyLabRobot category")
  resource_type: str | None = Field(default=None, description="Human-readable type of the resource")
  is_consumable: bool = Field(default=False)
  is_reusable: bool = Field(
    default=True,
    description="Whether the resource can be reused (e.g., plates are reusable, tips are not)",
  )
  nominal_volume_ul: float | None = Field(default=None, description="Nominal volume in microliters")
  material: str | None = Field(default=None, description="Material (polypropylene, glass, etc.)")
  manufacturer: str | None = Field(default=None)
  model: str | None = Field(default=None)
  ordering: str | None = Field(default=None, description="Ordering information")
  size_x_mm: float | None = Field(default=None, description="Size in X dimension (mm)")
  size_y_mm: float | None = Field(default=None, description="Size in Y dimension (mm)")
  size_z_mm: float | None = Field(default=None, description="Size in Z dimension (mm)")
  # Dynamic filtering fields
  num_items: int | None = Field(
    default=None, index=True, description="Number of items (wells, tips)"
  )
  plate_type: str | None = Field(default=None, index=True, description="Plate skirt type")
  well_volume_ul: float | None = Field(
    default=None, index=True, description="Well volume for plates"
  )
  tip_volume_ul: float | None = Field(
    default=None, index=True, description="Tip volume for tip racks"
  )
  vendor: str | None = Field(default=None, index=True, description="Vendor from FQN")
  plr_definition_details_json: dict[str, Any] | None = Field(
    default=None, sa_type=JsonVariant, description="Additional PyLabRobot definition details"
  )
  rotation_json: dict[str, Any] | None = Field(
    default=None, sa_type=JsonVariant, description="PLR rotation object"
  )


class ResourceDefinition(ResourceDefinitionBase, table=True):
  """ResourceDefinition ORM model - catalog of resource types.

  Cascading Deletes:
  - Deleting a ResourceDefinition will delete all associated Resource instances.
  """

  __tablename__ = "resource_definitions"

  # Foreign keys
  deck_definition_accession_id: uuid.UUID | None = Field(
    default=None,
    description="Deck definition accession ID",
    index=True,
    foreign_key="deck_definition_catalog.accession_id",
  )
  asset_requirement_accession_id: uuid.UUID | None = Field(
    default=None,
    description="Asset requirement accession ID",
    index=True,
    foreign_key="protocol_asset_requirements.accession_id",
  )

  # Relationships
  deck_definition: Optional["DeckDefinition"] = Relationship(
    sa_relationship=relationship(
      "DeckDefinition",
      foreign_keys="ResourceDefinition.deck_definition_accession_id",
    )
  )
  asset_requirement: Optional["AssetRequirement"] = Relationship()

  # Relationships
  resources: list["Resource"] = Relationship(
    sa_relationship=relationship(
      "Resource", back_populates="resource_definition", cascade="all, delete-orphan"
    )
  )


class ResourceDefinitionCreate(ResourceDefinitionBase):
  """Schema for creating a ResourceDefinition."""


class ResourceDefinitionRead(ResourceDefinitionBase):
  """Schema for reading a ResourceDefinition (API response)."""

  plr_definition_details_json: dict[str, Any] | None = None
  rotation_json: dict[str, Any] | None = None


class ResourceDefinitionUpdate(SQLModel):
  """Schema for updating a ResourceDefinition (partial update)."""

  name: str | None = None
  fqn: str | None = None
  description: str | None = None
  plr_category: str | None = None
  resource_type: str | None = None
  is_consumable: bool | None = None
  is_reusable: bool | None = None
  nominal_volume_ul: float | None = None
  material: str | None = None
  manufacturer: str | None = None
  model: str | None = None
  ordering: str | None = None
  size_x_mm: float | None = None
  size_y_mm: float | None = None
  size_z_mm: float | None = None
  num_items: int | None = None
  plate_type: str | None = None
  well_volume_ul: float | None = None
  tip_volume_ul: float | None = None
  vendor: str | None = None
  plr_definition_details_json: dict[str, Any] | None = None
  rotation_json: dict[str, Any] | None = None


# =============================================================================
# Resource (Physical Instance)
# =============================================================================


class ResourceBase(AssetBase):
  """Base schema for Resource - shared fields for create/update/response."""

  model_config = ConfigDict(extra="allow")

  # Resource-specific override: for minimal ResourceBase we expect `fqn` to be None
  fqn: str | None = Field(default=None, index=True, description="Fully qualified name")

  status: ResourceStatusEnum = Field(
    default=ResourceStatusEnum.UNKNOWN,
  )
  status_details: str | None = Field(default=None, description="Additional status details")
  location_label: str | None = Field(default=None, description="Physical location label")
  current_deck_position_name: str | None = Field(default=None, description="Current deck position")
  resource_definition_accession_id: uuid.UUID | None = Field(
    default=None, description="Reference to resource definition catalog"
  )
  parent_accession_id: uuid.UUID | None = Field(
    default=None, description="Parent resource for hierarchies"
  )
  workcell_accession_id: uuid.UUID | None = Field(
    default=None, description="Workcell this resource belongs to"
  )

  @property
  def deck_accession_id(self) -> uuid.UUID | None:
    """Compatibility property."""
    if "deck_accession_id" in self.__dict__:
      return self.__dict__["deck_accession_id"]
    return getattr(self, "deck_location_accession_id", None)

  @property
  def machine_id(self) -> uuid.UUID | None:
    """Compatibility property."""
    if "machine_id" in self.__dict__:
      return self.__dict__["machine_id"]
    return getattr(
      self, "machine_location_accession_id", getattr(self, "parent_machine_accession_id", None)
    )


class Resource(ResourceBase, Asset, table=True):
  """Resource table - represents a physical resource instance.

  Cascading Deletes:
  - Deleting a Resource will delete all its child resources (e.g., wells in a plate).
  - Deleting a Resource will delete all associated FunctionDataOutput records,
    which in turn deletes associated WellDataOutput records.
  - Deleting a Resource will delete all associated AssetReservation records.
  """

  __tablename__ = "resources"

  status: ResourceStatusEnum = Field(
    sa_column=Column(SAEnum(ResourceStatusEnum), default=ResourceStatusEnum.UNKNOWN),
  )

  # Foreign key references
  resource_definition_accession_id: uuid.UUID | None = Field(
    default=None,
    description="Reference to resource definition catalog",
    foreign_key="resource_definitions.accession_id",
  )
  parent_accession_id: uuid.UUID | None = Field(
    default=None,
    description="Parent resource for hierarchies",
    foreign_key="resources.accession_id",
  )
  current_protocol_run_accession_id: uuid.UUID | None = Field(
    default=None,
    description="Current protocol run if in use",
    foreign_key="protocol_runs.accession_id",
  )
  machine_location_accession_id: uuid.UUID | None = Field(
    default=None,
    description="Machine where resource is located",
    foreign_key="machines.accession_id",
  )
  deck_location_accession_id: uuid.UUID | None = Field(
    default=None, description="Deck where resource is located", foreign_key="decks.accession_id"
  )
  workcell_accession_id: uuid.UUID | None = Field(
    default=None,
    description="Workcell this resource belongs to",
    foreign_key="workcells.accession_id",
  )

  # Relationships
  resource_definition: ResourceDefinition | None = Relationship(back_populates="resources")

  # Self-referential parent/children
  parent: Optional["Resource"] = Relationship(
    sa_relationship=relationship(
      "Resource", back_populates="children", remote_side="Resource.accession_id"
    )
  )
  children: list["Resource"] = Relationship(
    sa_relationship=relationship("Resource", back_populates="parent", cascade="all, delete-orphan")
  )

  machine: Optional["Machine"] = Relationship(
    sa_relationship=relationship(
      "Machine",
      back_populates="resources",
      primaryjoin="Resource.machine_location_accession_id == Machine.accession_id",
      foreign_keys="[Resource.machine_location_accession_id]",
    )
  )
  deck: Optional["Deck"] = Relationship(
    sa_relationship=relationship("Deck", back_populates="resources")
  )
  workcell: Optional["Workcell"] = Relationship(
    sa_relationship=relationship("Workcell", back_populates="resources")
  )
  data_outputs: list["FunctionDataOutput"] = Relationship(
    sa_relationship=relationship(
      "FunctionDataOutput", back_populates="resource", cascade="all, delete-orphan"
    )
  )

  # Asset reservations referencing this resource
  asset_reservations: list["AssetReservation"] = Relationship(
    sa_relationship=relationship(
      "AssetReservation",
      back_populates="resource",
      primaryjoin="foreign(AssetReservation.asset_accession_id) == Resource.accession_id",
      foreign_keys="[AssetReservation.asset_accession_id]",
      cascade="all, delete-orphan",
      overlaps="machine",
    )
  )

  # ProtocolRun Relationship
  current_protocol_run: Optional["ProtocolRun"] = Relationship()

  # Machine counterpart relationship (reciprocal of Machine.resource_counterpart)
  machine_counterpart: Optional["Machine"] = Relationship(
    sa_relationship=relationship(
      "Machine",
      back_populates="resource_counterpart",
      primaryjoin="Machine.resource_counterpart_accession_id == Resource.accession_id",
      foreign_keys="[Machine.resource_counterpart_accession_id]",
    )
  )

  @property
  def deck_accession_id(self) -> uuid.UUID | None:
    """Compatibility property."""
    if "deck_accession_id" in self.__dict__:
      return self.__dict__["deck_accession_id"]
    return self.deck_location_accession_id

  @property
  def machine_id(self) -> uuid.UUID | None:
    """Compatibility property."""
    if "machine_id" in self.__dict__:
      return self.__dict__["machine_id"]
    return self.machine_location_accession_id


class ResourceCreate(ResourceBase):
  """Schema for creating a Resource."""

  resource_definition_accession_id: uuid.UUID | None = None
  parent_accession_id: uuid.UUID | None = None
  machine_location_accession_id: uuid.UUID | None = None
  deck_location_accession_id: uuid.UUID | None = None
  workcell_accession_id: uuid.UUID | None = None
  plr_state: dict[str, Any] | None = None


class ResourceRead(AssetRead, ResourceBase):
  """Schema for reading a Resource (API response)."""

  machine_id: uuid.UUID | None = Field(
    default=None, validation_alias=AliasChoices("machine_id", "machine_location_accession_id")
  )
  deck_accession_id: uuid.UUID | None = Field(
    default=None, validation_alias=AliasChoices("deck_accession_id", "deck_location_accession_id")
  )


class ResourceUpdate(AssetUpdate):
  """Schema for updating a Resource (partial update)."""

  status: ResourceStatusEnum | None = None
  status_details: str | None = None
  location_label: str | None = None
  current_deck_position_name: str | None = None
  resource_definition_accession_id: uuid.UUID | None = None


# =============================================================================
# Inventory Models
# =============================================================================


class ResourceInventoryReagentItem(SQLModel):
  """Represents a single reagent item within resource inventory data."""

  reagent_accession_id: uuid.UUID
  reagent_name: str | None = None
  lot_number: str | None = None
  expiry_date: str | None = None
  supplier: str | None = None
  catalog_number: str | None = None
  date_received: str | None = None
  date_opened: str | None = None
  concentration: dict[str, Any] | None = None
  initial_quantity: dict[str, Any]
  current_quantity: dict[str, Any]
  quantity_unit_is_volume: bool | None = True
  custom_fields: dict[str, Any] | None = None


class ResourceInventoryItemCount(SQLModel):
  """Provides counts and usage information for items within a resource inventory."""

  item_type: str | None = None
  initial_max_items: int | None = None
  current_available_items: int | None = None
  positions_used: list[str] | None = None


class ResourceInventoryDataIn(SQLModel):
  """Represents inbound inventory data for a resource instance."""

  praxis_inventory_schema_version: str | None = "1.0"
  reagents: list[ResourceInventoryReagentItem] | None = None
  item_count: ResourceInventoryItemCount | None = None
  consumable_state: str | None = None
  last_updated_by: str | None = None
  inventory_notes: str | None = None


class ResourceInventoryDataOut(ResourceInventoryDataIn):
  """Represents outbound inventory data for a resource instance."""

  last_updated_at: str | None = None


class ResourceTypeInfo(SQLModel):
  """Provides detailed information about a specific resource type."""

  name: str
  parent_class: str
  can_create_directly: bool
  constructor_params: dict[str, dict]
  doc: str
  module: str
  model_config = ConfigDict(use_enum_values=True)


class ResourceCategoriesResponse(SQLModel):
  """Organizes resource types by category for categorization and discovery."""

  categories: dict[str, list[str]]
