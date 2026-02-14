"""Validation utilities for accession IDs."""

import functools
import inspect
import uuid
from typing import Any, Callable, TypeVar, cast

from praxis.backend.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=Callable[..., Any])


def validate_accession_id(val: Any) -> None:
  """Validate that a value is a valid UUID accession ID.

  Args:
      val: The value to validate.

  Raises:
      ValueError: If the value is not a valid UUID.
  """
  if val is None:
    return
  if isinstance(val, uuid.UUID):
    return
  if isinstance(val, str):
    try:
      uuid.UUID(val)
      return
    except ValueError:
      pass
  raise ValueError(f"Invalid accession ID format: {val}")


def validate_accession_ids(func: T) -> T:
  """Decorator to validate accession IDs in method arguments.

  This decorator checks for arguments named 'accession_id', or arguments ending
  in '_accession_id', as well as fields in 'obj_in' that contain 'accession_id'.
  """
  sig = inspect.signature(func)

  @functools.wraps(func)
  async def wrapper(*args: Any, **kwargs: Any) -> Any:
    # Map positional arguments to names
    bound_args = sig.bind_partial(*args, **kwargs)
    all_args = bound_args.arguments

    # Check for arguments ending in 'accession_id' or specifically 'accession_id'
    for name, val in all_args.items():
      if name == "accession_id" or name.endswith("_accession_id"):
        validate_accession_id(val)

    # Also check obj_in if it's present (common in CRUD operations)
    if "obj_in" in all_args:
      obj_in = all_args["obj_in"]
      # If it's a Pydantic model
      if hasattr(obj_in, "model_dump"):
        # We only care about set/passed values in the schema
        data = obj_in.model_dump(exclude_unset=True)
        for key, val in data.items():
          if "accession_id" in key:
            validate_accession_id(val)
      # If it's a dict
      elif isinstance(obj_in, dict):
        for key, val in obj_in.items():
          if "accession_id" in key:
            validate_accession_id(val)

    return await func(*args, **kwargs)

  return cast(T, wrapper)
