import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

from praxis.backend.models.domain.filters import SearchFilters
from praxis.backend.models.domain.sqlmodel_base import PraxisBase
from praxis.backend.models.enums import DataOutputTypeEnum, SpatialContextEnum
from praxis.backend.utils.db import JsonVariant

if TYPE_CHECKING:
  import uuid

  from praxis.backend.models.domain.deck import Deck
  from praxis.backend.models.domain.machine import Machine
  from praxis.backend.models.domain.protocol import FunctionCallLog, ProtocolRun
  from praxis.backend.models.domain.resource import Resource

# =============================================================================
# Function Data Output
# =============================================================================


class FunctionDataOutputBase(PraxisBase):
  """Base schema for FunctionDataOutput - shared fields for create/update/response."""

  data_type: DataOutputTypeEnum = Field(
    default=DataOutputTypeEnum.UNKNOWN,
    description="Type of data output",
  )
  data_key: str = Field(
    default="", max_length=255, description="Unique key within the function call", index=True
  )
  spatial_context: SpatialContextEnum = Field(
    default=SpatialContextEnum.GLOBAL,
    description="Spatial context of the data",
  )
  spatial_coordinates_json: dict[str, Any] | None = Field(
    default=None, sa_type=JsonVariant, description="Spatial coordinates within resource"
  )
  data_units: str | None = Field(default=None, max_length=50, description="Units of measurement")
  data_quality_score: float | None = Field(
    default=None, ge=0.0, le=1.0, description="Quality score (0.0-1.0)"
  )
  measurement_conditions_json: dict[str, Any] | None = Field(
    default=None, sa_type=JsonVariant, description="Measurement conditions"
  )
  sequence_in_function: int | None = Field(
    default=None, description="Sequence number within the function call"
  )
  file_path: str | None = Field(default=None, description="Path to external file")
  file_size_bytes: int | None = Field(default=None, description="File size in bytes")
  mime_type: str | None = Field(default=None, description="MIME type of the output")
  measurement_timestamp: datetime | None = Field(
    default=None, description="When the measurement was captured"
  )


class FunctionDataOutput(FunctionDataOutputBase, table=True):
  """FunctionDataOutput ORM model - represents data output from a function call."""

  __tablename__ = "function_data_outputs"

  data_type: DataOutputTypeEnum = Field(
    default=DataOutputTypeEnum.UNKNOWN,
    sa_column=Column(
      SAEnum(DataOutputTypeEnum), default=DataOutputTypeEnum.UNKNOWN, nullable=False
    ),
  )
  spatial_context: SpatialContextEnum = Field(
    default=SpatialContextEnum.GLOBAL,
    sa_column=Column(SAEnum(SpatialContextEnum), default=SpatialContextEnum.GLOBAL, nullable=False),
  )

  data_value_json: dict[str, Any] | None = Field(
    default=None, sa_type=JsonVariant, description="Data output as JSON"
  )

  # Data content fields (legacy compatibility)
  data_value_numeric: float | None = Field(default=None, description="Numeric data value")
  data_value_text: str | None = Field(default=None, description="Text data")
  data_value_binary: bytes | None = Field(default=None, description="Binary data")

  # Foreign keys
  function_call_log_accession_id: uuid.UUID | None = Field(
    default=None, foreign_key="function_call_logs.accession_id", index=True
  )
  protocol_run_accession_id: uuid.UUID | None = Field(
    default=None, foreign_key="protocol_runs.accession_id", index=True
  )
  machine_accession_id: uuid.UUID | None = Field(
    default=None, foreign_key="machines.accession_id", index=True
  )
  resource_accession_id: uuid.UUID | None = Field(
    default=None, foreign_key="resources.accession_id", index=True
  )
  deck_accession_id: uuid.UUID | None = Field(
    default=None, foreign_key="decks.accession_id", index=True
  )
  derived_from_data_output_accession_id: uuid.UUID | None = Field(
    default=None, foreign_key="function_data_outputs.accession_id", index=True
  )

  # Relationships
  function_call_log: Optional["FunctionCallLog"] = Relationship(back_populates="data_outputs")
  protocol_run: Optional["ProtocolRun"] = Relationship(back_populates="data_outputs")
  machine: Optional["Machine"] = Relationship(back_populates="data_outputs")
  resource: Optional["Resource"] = Relationship(
    sa_relationship=relationship(
      "Resource",
      primaryjoin="FunctionDataOutput.resource_accession_id == Resource.accession_id",
      back_populates="data_outputs",
    )
  )
  deck: Optional["Deck"] = Relationship()
  derived_from: Optional["FunctionDataOutput"] = Relationship(
    sa_relationship=relationship(
      "FunctionDataOutput", remote_side="FunctionDataOutput.accession_id"
    )
  )
  well_outputs: list["WellDataOutput"] = Relationship(
    sa_relationship=relationship(
      "WellDataOutput", back_populates="function_data_output", cascade="all, delete-orphan"
    )
  )


class FunctionDataOutputCreate(FunctionDataOutputBase):
  """Schema for creating a FunctionDataOutput."""

  function_call_log_accession_id: uuid.UUID
  protocol_run_accession_id: uuid.UUID
  resource_accession_id: uuid.UUID | None = None
  machine_accession_id: uuid.UUID | None = None
  deck_accession_id: uuid.UUID | None = None
  data_value_numeric: float | None = None
  data_value_json: dict[str, Any] | None = None
  data_value_text: str | None = None
  data_value_binary: bytes | None = None
  derived_from_data_output_accession_id: uuid.UUID | None = None


class FunctionDataOutputRead(FunctionDataOutputBase):
  """Schema for reading a FunctionDataOutput (API response)."""

  accession_id: uuid.UUID
  data_value_json: dict[str, Any] | None = None
  data_value_numeric: float | None = None
  data_value_text: str | None = None
  data_value_binary: bytes | None = None

  # Foreign keys included in response
  function_call_log_accession_id: uuid.UUID
  protocol_run_accession_id: uuid.UUID
  resource_accession_id: uuid.UUID | None = None
  machine_accession_id: uuid.UUID | None = None
  deck_accession_id: uuid.UUID | None = None
  derived_from_data_output_accession_id: uuid.UUID | None = None


class FunctionDataOutputUpdate(SQLModel):
  """Schema for updating a FunctionDataOutput (partial update)."""

  data_type: DataOutputTypeEnum | None = None
  file_path: str | None = None
  data_value_json: dict[str, Any] | None = None
  data_quality_score: float | None = None
  data_key: str | None = None
  measurement_conditions_json: dict[str, Any] | None = None
  processing_metadata_json: dict[str, Any] | None = None


# =============================================================================
# Well Data Output
# =============================================================================


class WellDataOutputBase(PraxisBase):
  """Base schema for WellDataOutput - shared fields for create/update/response."""

  well_position: str | None = Field(
    default=None, index=True, description="Well position (e.g., 'A1')"
  )
  measurement_type: str | None = Field(default=None, index=True, description="Type of measurement")
  value: float | None = Field(default=None, description="Measured value")
  unit: str | None = Field(default=None, description="Unit of measurement")
  well_name: str | None = Field(default=None, description="Well name (e.g. A1)")
  well_name: str = Field(default="", description="Well name (e.g. A1)")
  data_value: float | None = None
  well_row: int = Field(default=0, ge=0, description="0-based row index")
  well_column: int = Field(default=0, ge=0, description="0-based column index")
  well_index: int | None = Field(default=None, ge=0, description="Linear well index")


class WellDataOutput(WellDataOutputBase, table=True):
  """WellDataOutput ORM model - represents well-specific data output."""

  __tablename__ = "well_data_outputs"

  metadata_json: dict[str, Any] | None = Field(
    default=None, sa_type=JsonVariant, description="Additional well metadata"
  )

  # Foreign keys
  function_data_output_accession_id: uuid.UUID | None = Field(
    default=None, foreign_key="function_data_outputs.accession_id", index=True
  )
  resource_accession_id: uuid.UUID | None = Field(
    default=None, foreign_key="resources.accession_id", index=True
  )
  plate_resource_accession_id: uuid.UUID | None = Field(
    default=None, foreign_key="resources.accession_id", index=True
  )

  # Relationships
  function_data_output: Optional["FunctionDataOutput"] = Relationship(back_populates="well_outputs")
  resource: Optional["Resource"] = Relationship(
    sa_relationship=relationship(
      "Resource", primaryjoin="WellDataOutput.resource_accession_id == Resource.accession_id"
    )
  )
  plate_resource: Optional["Resource"] = Relationship(
    sa_relationship=relationship(
      "Resource", primaryjoin="WellDataOutput.plate_resource_accession_id == Resource.accession_id"
    )
  )


class WellDataOutputCreate(WellDataOutputBase):
  """Schema for creating a WellDataOutput."""

  function_data_output_accession_id: uuid.UUID
  plate_resource_accession_id: uuid.UUID


class WellDataOutputRead(WellDataOutputBase):
  """Schema for reading a WellDataOutput (API response)."""

  accession_id: uuid.UUID
  metadata_json: dict[str, Any] | None = None
  function_data_output_accession_id: uuid.UUID
  plate_resource_accession_id: uuid.UUID


class WellDataOutputUpdate(SQLModel):
  """Schema for updating a WellDataOutput (partial update)."""

  well_position: str | None = None
  measurement_type: str | None = None
  value: float | None = None
  unit: str | None = None
  well_name: str | None = None
  data_value: float | None = None
  metadata_json: dict[str, Any] | None = None


# =============================================================================
# Auxiliary Models (Visualizations, Summaries, Filters)
# =============================================================================


class PlateDataVisualization(PraxisBase):
  """Model for plate-based data visualization."""

  plate_resource_accession_id: uuid.UUID = Field(..., description="ID of the plate resource")
  plate_name: str = Field(..., description="Name of the plate")
  data_type: DataOutputTypeEnum = Field(..., description="Type of data being visualized")
  measurement_timestamp: datetime = Field(..., description="When the data was captured")
  well_data: list[WellDataOutputRead] = Field(..., description="Data for each well")
  plate_layout: dict[str, Any] = Field(
    ..., sa_type=JsonVariant, description="Plate layout information"
  )
  data_range: dict[str, float] = Field(..., sa_type=JsonVariant, description="Min/max values")
  units: str | None = Field(None, description="Data units")


class ProtocolRunDataSummary(PraxisBase):
  """Model for summarizing all data from a protocol run."""

  protocol_run_accession_id: uuid.UUID = Field(..., description="ID of the protocol run")
  total_data_outputs: int = Field(..., description="Total number of data outputs")
  data_types: list[str] = Field(..., description="List of data types captured")
  machines_used: Sequence[uuid.UUID] = Field(..., description="List of machine IDs")
  resource_with_data: Sequence[uuid.UUID] = Field(..., description="List of resource IDs")
  data_timeline: list[dict[str, Any]] = Field(..., description="Timeline of data capture events")
  file_attachments: list[dict[str, Any]] = Field(..., description="List of file attachments")


class DataExportRequest(SQLModel):
  """Model for requesting data export."""

  filters: SearchFilters = Field(..., description="Filters for data selection")
  export_format: str = Field(..., description="Export format (csv, json, xlsx, etc.)")
  include_metadata: bool = Field(True, description="Whether to include metadata")
  include_spatial_info: bool = Field(True, description="Whether to include spatial information")
  flatten_structure: bool = Field(False, description="Whether to flatten hierarchical data")


class FunctionDataOutputFilters(SQLModel):
  """Model for filtering function data outputs."""

  search_filters: SearchFilters = Field(..., description="Search filters for data selection")
  data_types: list[DataOutputTypeEnum] | None = Field(None, description="Filter by data types.")
  spatial_contexts: list[SpatialContextEnum] | None = Field(
    None, description="Filter by spatial context."
  )
  has_numeric_data: bool | None = Field(None, description="Filter for entries with numeric data.")
  has_file_data: bool | None = Field(None, description="Filter for entries with file attachments.")
  min_quality_score: float | None = Field(
    None, ge=0.0, le=1.0, description="Minimum quality score."
  )


class WellDataOutputFilters(SQLModel):
  """Model for filtering well data outputs."""

  plate_resource_id: UUID | None = Field(None)
  function_call_id: UUID | None = Field(None)
  protocol_run_id: UUID | None = Field(None)
  data_type: DataOutputTypeEnum | None = Field(None)
  well_row: int | None = Field(None, ge=0)
  well_column: int | None = Field(None, ge=0)
  skip: int = Field(0, ge=0)
  limit: int = Field(100, ge=1, le=1000)
