# pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements,fixme,logging-fstring-interpolation
"""Utilities for inspecting and serializing Python types."""

import inspect
from typing import Any, Union, get_args, get_origin

from praxis.common.type_inspection import (
  PLR_MACHINE_FRONTEND_TYPES,
  PLR_RESOURCE_TYPES,
  extract_resource_types,
  get_element_type,
  is_container_type,
  is_pylabrobot_resource,
  serialize_type_hint,
)

__all__ = [
  "PLR_MACHINE_FRONTEND_TYPES",
  "PLR_RESOURCE_TYPES",
  "extract_resource_types",
  "fqn_from_hint",
  "get_element_type",
  "is_container_type",
  "is_pylabrobot_resource",
  "serialize_type_hint",
]


def fqn_from_hint(type_hint: Any) -> str:
  """Get the fully qualified name of a type hint.

  For built-in types, this returns just the type name (e.g., "int"), not "builtins.int".
  For types from the "praxis." namespace, returns the fully qualified name.
  For Union or Optional types, returns the FQN of the non-None type(s).
  For generics, returns the FQN of the generic type.
  """
  if type_hint == inspect.Parameter.empty:
    return "Any"
  actual_type = type_hint
  origin = get_origin(type_hint)
  args = get_args(type_hint)
  if origin is Union and type(None) in args:
    non_none_args = [arg for arg in args if arg is not type(None)]
    # Take the first non-None type for simplicity. This is a reasonable assumption for assets.
    if len(non_none_args) == 1:
      actual_type = non_none_args[0]
    elif len(non_none_args) > 1:
      # Handle Union[ResourceType, OtherType] by prioritizing the resource.
      # This is a heuristic. A more robust solution might require more context.
      resource_types = [t for t in non_none_args if is_pylabrobot_resource(t)]
      actual_type = resource_types[0] if resource_types else non_none_args[0]
    else:  # Only NoneType in Union
      return "None"

  if hasattr(actual_type, "__name__"):
    module = getattr(actual_type, "__module__", "")
    if isinstance(module, str) and (
      module.startswith(("praxis.", "pylabrobot.")) or module == "builtins"
    ):
      return (
        f"{module}.{actual_type.__name__}"
        if module and module != "builtins"
        else actual_type.__name__
      )
    return actual_type.__name__
  return str(actual_type)
