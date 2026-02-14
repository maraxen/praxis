"""UUID utilities for Praxis.

This module provides UUID generation functions that return standard uuid.UUID types.

This is only needed because the built-in uuid module does not support UUID7,
and we need to use the uuid_utils library for generation purposes.

It includes functions to generate UUID7 and UUID4, returning them as standard
Python UUID objects.
"""

import uuid

import uuid_utils


def uuid7() -> uuid.UUID:
  """Generate a UUID7 using uuid_utils but return as standard uuid.UUID type.

  Returns:
      uuid.UUID: A UUID7 instance as a standard Python UUID object.

  """
  return uuid.UUID(str(uuid_utils.uuid7()))


def uuid4() -> uuid.UUID:
  """Generate a UUID4 using the standard library.

  Returns:
      uuid.UUID: A UUID4 instance.

  """
  return uuid.uuid4()


def generate_accession_id() -> uuid.UUID:
  """Generate a centralized accession ID.

  Praxis uses UUID7 for accession IDs to ensure they are both unique and
  lexicographically sortable by creation time.

  Returns:
      uuid.UUID: A new UUID7 instance.

  """
  return uuid7()


def generate_name(prefix: str) -> str:
  """Generate a default name."""
  uuid_ = uuid7().hex[:8]
  return f"{prefix}-{uuid_}"
