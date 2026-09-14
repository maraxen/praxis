"""Unit tests for the PraxisBase SQLModel base class."""

import uuid
from datetime import datetime

from praxis.backend.models.domain.sqlmodel_base import PraxisBase, json_field


class MockModel(PraxisBase, table=True):
  """A mock model for testing purposes."""

  description: str | None = None
  extra_metadata: dict = json_field(default_factory=dict)


def test_praxis_base_defaults():
  """Test that PraxisBase provides expected default values."""
  model = MockModel(name="test-model")

  assert isinstance(model.accession_id, uuid.UUID)
  assert isinstance(model.created_at, datetime)
  assert model.updated_at is None
  assert model.name == "test-model"
  assert model.properties_json is None
  assert model.extra_metadata == {}


def test_praxis_base_serialization():
  """Test that PraxisBase can be serialized to and from a dictionary."""
  model = MockModel(name="test-serialization", description="A test model")
  data = model.model_dump()

  assert data["name"] == "test-serialization"
  assert data["description"] == "A test model"
  assert "accession_id" in data
  assert "created_at" in data


def test_json_field_helper():
  """Test the json_field helper function."""
  model = MockModel(name="test-json", extra_metadata={"key": "value"})
  assert model.extra_metadata == {"key": "value"}


def test_sqlmodel_metadata_registration():
  """Test that the model is correctly registered in its metadata."""
  assert "mockmodel" in MockModel.metadata.tables
