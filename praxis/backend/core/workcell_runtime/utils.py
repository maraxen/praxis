"""Utility functions for WorkcellRuntime."""

import importlib
from functools import partial

from praxis.backend.utils.errors import WorkcellRuntimeError
from praxis.backend.utils.logging import get_logger, log_async_runtime_errors

logger = get_logger(__name__)

log_workcell_runtime_errors = partial(
  log_async_runtime_errors,
  logger_instance=logger,
  raises=True,
  raises_exception=WorkcellRuntimeError,
)


# PLR 1.0 moved the machine-agnostic LiquidHandler stack (and the other legacy machine
# frontends/backends) under ``pylabrobot.legacy``; the old top-level packages are
# DeprecationWarning shims and several of their submodules have no shim at all.
# FQNs persisted before the bump (DB rows, saved manifests) still use the old paths.
_PLR_LEGACY_PACKAGES: frozenset[str] = frozenset({
  "liquid_handling",
  "machines",
  "plate_reading",
  "heating_shaking",
  "shaking",
  "temperature_controlling",
  "thermocycling",
  "powder_dispensing",
  "pumps",
  "centrifuge",
  "storage",
  "scales",
  "tilting",
  "only_fans",
  "sealing",
  "peeling",
  "arms",
})


def _legacy_module_name(module_name: str) -> str | None:
  """Return the ``pylabrobot.legacy.*`` twin of a pre-1.0 PLR module path, if it has one."""
  parts = module_name.split(".")
  if len(parts) >= 2 and parts[0] == "pylabrobot" and parts[1] in _PLR_LEGACY_PACKAGES:
    return ".".join(["pylabrobot", "legacy", *parts[1:]])
  return None


def get_class_from_fqn(class_fqn: str) -> type:
  """Import and return a class dynamically from its fully qualified name.

  Pre-1.0 ``pylabrobot.<machine package>`` paths are resolved through their explicit
  ``pylabrobot.legacy`` home first (no deprecation warning, and it also covers submodules
  the upstream shims dropped); the path as given is the fallback.
  """
  if not class_fqn or "." not in class_fqn:
    msg = "Invalid fully qualified class name: %s"
    raise ValueError(msg, class_fqn)
  module_name, class_name = class_fqn.rsplit(".", 1)
  legacy_module_name = _legacy_module_name(module_name)
  if legacy_module_name is not None:
    try:
      return getattr(importlib.import_module(legacy_module_name), class_name)
    except (ImportError, AttributeError):
      pass
  imported_module = importlib.import_module(module_name)
  return getattr(imported_module, class_name)
