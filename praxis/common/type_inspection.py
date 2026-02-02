# pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements,fixme,logging-fstring-interpolation
"""Utilities for inspecting and serializing Python types."""

import inspect
import re
from collections.abc import Sequence
from typing import Any, Union, get_args, get_origin

# =============================================================================
# PLR Resource Type Constants
# =============================================================================

# All known PLR resource type names for pattern matching
PLR_RESOURCE_TYPES: frozenset[str] = frozenset({
  # Container sub-elements
  "Well",
  "TipSpot",
  "Spot",
  "Tube",
  # Containers
  "Plate",
  "TipRack",
  "Trough",
  "TubeRack",
  "Container",
  # Carriers
  "PlateCarrier",
  "TipCarrier",
  "TroughCarrier",
  "Carrier",
  "CarrierSite",
  # Infrastructure
  "Deck",
  "Slot",
  "Resource",
  # Lids
  "Lid",
  # Machine frontends
  "LiquidHandler",
  "PlateReader",
  "HeaterShaker",
  "Shaker",
  "TemperatureController",
  "Centrifuge",
  "Thermocycler",
  "Pump",
  "PumpArray",
  "Fan",
  "Sealer",
  "Peeler",
  "PowderDispenser",
  "Incubator",
  "SCARA",
  # Base machine class
  "Machine",
})

# Regex pattern for extracting resource types from string type hints
_PLR_RESOURCE_PATTERN = re.compile(
  r"\b(" + "|".join(sorted(PLR_RESOURCE_TYPES, key=len, reverse=True)) + r")\b"
)


def is_pylabrobot_resource(type_or_str: Any) -> bool:
  """Check if the given type or string is a Pylabrobot Resource or Machine.

  This function returns True for:
  - Resources: Plate, TipRack, Trough, Container, Carrier, Deck, etc.
  - Machines: LiquidHandler, PlateReader, Shaker, Centrifuge, etc.

  Both resources and machines are "assets" that need to be acquired at runtime.
  """
  if isinstance(type_or_str, str):
    # Check if any known PLR type name is in the string
    return any(t in type_or_str for t in PLR_RESOURCE_TYPES)

  origin = get_origin(type_or_str)
  if origin is Union:
    args = get_args(type_or_str)
    # Return True if ANY arg is a resource
    return any(is_pylabrobot_resource(arg) for arg in args if arg is not type(None))

  if hasattr(type_or_str, "__module__") and "pylabrobot" in getattr(type_or_str, "__module__", ""):
    return True

  # Also check if the type name is one of the resource types (fallback if module check fails or for some mocks)
  name = getattr(type_or_str, "__name__", str(type_or_str))
  return name in PLR_RESOURCE_TYPES


def extract_resource_types(type_or_str: Any) -> list[str]:
  """Extract all PLR resource types from a type hint, including generics.

  This function handles container types (list, tuple, Sequence) and Union types,
  extracting all PLR resource type names contained within.

  Args:
      type_or_str: A type hint (runtime type or string annotation).

  Returns:
      List of unique PLR resource type names found in the type hint.

  Examples:
      >>> extract_resource_types("list[Well]")
      ['Well']
      >>> extract_resource_types("Sequence[TipSpot]")
      ['TipSpot']
      >>> extract_resource_types("tuple[Plate, TipRack]")
      ['Plate', 'TipRack']
      >>> extract_resource_types("Union[Plate, None]")
      ['Plate']
      >>> extract_resource_types("dict[str, list[Well]]")
      ['Well']

  """
  if isinstance(type_or_str, str):
    return _extract_from_string(type_or_str)

  return _extract_from_runtime_type(type_or_str)


def _extract_from_string(type_str: str) -> list[str]:
  """Extract PLR resource types from a string type hint.

  Uses regex pattern matching to find all known PLR resource type names
  within the string representation of a type hint.

  Args:
      type_str: String representation of a type hint.

  Returns:
      List of unique PLR resource type names found.

  """
  matches = _PLR_RESOURCE_PATTERN.findall(type_str)
  # Return unique matches while preserving order
  seen: set[str] = set()
  result: list[str] = []
  for match in matches:
    if match not in seen:
      seen.add(match)
      result.append(match)
  return result


def _extract_from_runtime_type(type_hint: Any) -> list[str]:
  """Extract PLR resource types from a runtime type object.

  Recursively processes generic types (list, tuple, Union, Sequence, etc.)
  to find all contained PLR resource types.

  Args:
      type_hint: A runtime type hint object.

  Returns:
      List of unique PLR resource type names found.

  """
  results: list[str] = []
  seen: set[str] = set()

  def add_if_resource(name: str) -> None:
    if name in PLR_RESOURCE_TYPES and name not in seen:
      seen.add(name)
      results.append(name)

  def process_type(t: Any) -> None:
    if t is None or t is type(None):
      return

    origin = get_origin(t)
    args = get_args(t)

    # Handle generic containers: list, tuple, set, frozenset, Sequence
    if origin in (list, tuple, set, frozenset) or origin is Sequence:
      for arg in args:
        process_type(arg)
      return

    # Handle dict - only check values (keys are typically str)
    if origin is dict and len(args) >= 2:
      process_type(args[1])  # Process value type
      return

    # Handle Union (including Optional)
    if origin is Union:
      for arg in args:
        if arg is not type(None):
          process_type(arg)
      return

    # Handle typing.Sequence (not from collections.abc)
    try:
      from collections.abc import Sequence as TypingSequence

      if origin is TypingSequence:
        for arg in args:
          process_type(arg)
        return
    except ImportError:
      pass

    # Base case: check if this type is a PLR resource
    name = getattr(t, "__name__", None)
    if name:
      add_if_resource(name)
    elif isinstance(t, str):
      # Sometimes types are stored as forward references (strings)
      for found in _extract_from_string(t):
        add_if_resource(found)

  process_type(type_hint)
  return results


def get_element_type(type_or_str: Any) -> str | None:
  """Get the element type from a container type hint.

  For container types like list[Well] or Sequence[TipSpot], returns
  the element type name. Returns None for non-container types.

  Args:
      type_or_str: A type hint (runtime type or string annotation).

  Returns:
      The element type name as a string, or None if not a container.

  Examples:
      >>> get_element_type("list[Well]")
      'Well'
      >>> get_element_type("Sequence[TipSpot]")
      'TipSpot'
      >>> get_element_type("Plate")
      None

  """
  if isinstance(type_or_str, str):
    return _get_element_type_from_string(type_or_str)
  return _get_element_type_from_runtime(type_or_str)


def _get_element_type_from_string(type_str: str) -> str | None:
  """Extract element type from a string container type hint."""
  # Match patterns like list[X], Sequence[X], tuple[X, ...]
  container_pattern = r"^(?:list|Sequence|tuple|set|frozenset)\[([^\[\],]+)"
  match = re.match(container_pattern, type_str.strip())
  if match:
    inner = match.group(1).strip()
    # Check if the inner type is a PLR resource
    if inner in PLR_RESOURCE_TYPES:
      return inner
    # Try to extract from more complex inner types
    extracted = _extract_from_string(inner)
    if extracted:
      return extracted[0]
  return None


def _get_element_type_from_runtime(type_hint: Any) -> str | None:
  """Extract element type from a runtime container type hint."""
  origin = get_origin(type_hint)
  args = get_args(type_hint)

  if origin in (list, tuple, set, frozenset) or origin is Sequence:
    if args:
      # For tuple with multiple types, return the first PLR type
      for arg in args:
        name = getattr(arg, "__name__", None)
        if name and name in PLR_RESOURCE_TYPES:
          return name
        # Recursively check for nested types
        nested = _get_element_type_from_runtime(arg)
        if nested:
          return nested
  return None


def is_container_type(type_or_str: Any) -> bool:
  """Check if the type hint represents a container of resources.

  Args:
      type_or_str: A type hint (runtime type or string annotation).

  Returns:
      True if the type is a container (list, tuple, Sequence, etc.).

  Examples:
      >>> is_container_type("list[Well]")
      True
      >>> is_container_type("Plate")
      False
      >>> is_container_type("tuple[Plate, TipRack]")
      True

  """
  if isinstance(type_or_str, str):
    return bool(
      re.match(r"^(?:list|Sequence|tuple|set|frozenset)\[", type_or_str.strip())
    )

  origin = get_origin(type_or_str)
  return origin in (list, tuple, set, frozenset) or origin is Sequence


def serialize_type_hint(type_hint: Any) -> str:
  """Serialize a type hint to a string representation."""
  if type_hint == inspect.Parameter.empty:
    return "Any"
  origin = get_origin(type_hint)
  args = get_args(type_hint)

  if origin is None:
    return getattr(type_hint, "__name__", str(type_hint))

  # Handle Union types, especially for Optional[T] which is Union[T, None]
  if origin is Union:
    non_none_args = [arg for arg in args if arg is not type(None)]
    if len(non_none_args) == 1:
      return f"typing.Optional[{serialize_type_hint(non_none_args[0])}]"
    return f"typing.Union[{', '.join(serialize_type_hint(arg) for arg in args)}]"

  # Handle generic collections like list, dict, etc.
  if hasattr(origin, "__name__"):
    origin_name = origin.__name__
    if args:
      args_repr = ", ".join(serialize_type_hint(arg) for arg in args)
      return f"{origin_name}[{args_repr}]"
    return origin_name

  # Fallback for other complex types
  if hasattr(type_hint, "__module__") and hasattr(type_hint, "__name__"):
    return f"{type_hint.__module__}.{type_hint.__name__}"

  return str(type_hint)
