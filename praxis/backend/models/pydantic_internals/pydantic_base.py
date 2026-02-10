"""Base Pydantic models for reuse across the application.

This module provides common base models, such as a timestamped model,
to ensure consistency in API responses.
"""

import datetime
from enum import Enum
from typing import Any

from pydantic import UUID7, BaseModel, ConfigDict, Field

from praxis.backend.utils.uuid import uuid7


class PraxisBaseModel(BaseModel):
  """A base model that includes timestamp fields for API responses."""

  accession_id: UUID7 = Field(
    description="The unique accession ID of the record.",
    default_factory=uuid7,
    frozen=True,
  )
  created_at: datetime.datetime = Field(
    description="The time the record was created.",
    default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc),
    frozen=True,
  )
  updated_at: datetime.datetime | None = Field(
    default=None,
    alias="last_updated",
    description="The time the record was last updated.",
  )
  name: str = Field(
    default_factory=lambda: uuid7().hex[:8],
    description="An optional name for the record.",
    frozen=True,
  )
  properties_json: dict[str, Any] | None = Field(
    default=None,
    description="Arbitrary metadata associated with the record.",
  )

  def model_post_init(self, __context: Any) -> None:
    """Set the updated_at field on first creation only (when not loaded from DB)."""
    if self.updated_at is None:
      self.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)

  model_config = ConfigDict(
    from_attributes=True,
    use_enum_values=True,
    json_encoders={
      Enum: lambda v: (v.value.lower() if isinstance(v.value, str) else v.value),
    },
    validate_assignment=True,
  )
