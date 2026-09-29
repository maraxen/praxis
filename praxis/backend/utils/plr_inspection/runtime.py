"""Utilities for inspecting PyLabRobot resources and machines.

.. deprecated::
  This module uses runtime inspection which has side effects (imports PLR modules).
  For machine/backend discovery, use :mod:`praxis.backend.utils.plr_static_analysis`
  instead, which provides LibCST-based static analysis without imports.

"""

# Standard Library Imports
import importlib
import inspect
import logging
from inspect import isabstract
import pkgutil
import warnings
from typing import (
  Any,
)

from pylabrobot.legacy.machines.machine import Machine

# PyLabRobot Imports
from pylabrobot.resources import (
  Deck,
  Resource,
  ResourceHolder,
)
from pylabrobot.resources.carrier import (
  Carrier,
  PlateCarrier,
  TipCarrier,
  TroughCarrier,
)
from pylabrobot.resources.trough import Trough

logger = logging.getLogger(__name__)


def get_class_fqn(klass: type[Any]) -> str:
  """Get the fully qualified name of a class."""
  return f"{klass.__module__}.{klass.__name__}"


def get_module_classes(
  module: Any,
  parent_class: type[Any] | None = None,
  concrete_only: bool = False,
) -> dict[str, type[Any]]:
  """Get all classes from a module that are subclasses of parent_class.

  Args:
      module: The module to inspect.
      parent_class: The parent class to filter by. If None, all classes are returned.
      concrete_only: If True, only return non-abstract classes.

  Returns:
      A dictionary of class names to class objects.

  """
  classes = {}
  for name, obj in inspect.getmembers(module, inspect.isclass):
    if parent_class and not issubclass(obj, parent_class):
      continue
    # Ensure the class is defined in the module itself, not just imported.
    if obj.__module__ != module.__name__ and not obj.__module__.startswith(
      module.__name__ + ".",
    ):
      # Allow classes from submodules of the given module if module is a package root
      is_submodule_class = False
      if hasattr(module, "__path__"):  # Check if module is a package
        for _importer, modname, _ispkg in pkgutil.iter_modules(
          module.__path__,
          module.__name__ + ".",
        ):
          if obj.__module__.startswith(modname):
            is_submodule_class = True
            break
      if not is_submodule_class:
        continue

    if concrete_only and isabstract(obj):
      continue
    classes[name] = obj
  return classes


def get_constructor_params_with_defaults(
  klass: type[Any],
  required_only: bool = False,
) -> dict[str, Any]:
  """Get the constructor parameters and their default values for a class.

  Args:
      klass: The class to inspect.
      required_only: If True, only return parameters without default values.

  Returns:
      A dictionary of parameter names to their default values
      (or inspect.Parameter.empty if no default).

  """
  params = {}
  try:
    signature = inspect.signature(klass.__init__)
    for name, param in signature.parameters.items():
      if name in {"self", "args", "kwargs"}:
        continue
      if required_only and param.default is not inspect.Parameter.empty:
        continue
      params[name] = param.default
  except Exception as e:
    logger.exception("Error inspecting constructor for %s: %s", get_class_fqn(klass), e)
  return params


def _discover_classes_in_module_recursive(
  module_name: str,
  parent_class: type[Any] | None,
  concrete_only: bool,
  visited_modules: set[str],
) -> dict[str, type[Any]]:
  """Discover classes in a module and its submodules recursively.

  Args:
    module_name: The name of the module to inspect.
    parent_class: The parent class to filter by. If None, all classes are returned.
    concrete_only: If True, only return non-abstract classes.
    visited_modules: A set to track visited modules to avoid circular imports.

  Returns:
    A dictionary of fully qualified class names to class objects.

  """
  if module_name in visited_modules:
    return {}
  visited_modules.add(module_name)

  found_classes: dict[str, type[Any]] = {}
  try:
    module = importlib.import_module(module_name)
    classes_in_module = get_module_classes(module, parent_class, concrete_only)
    for klass in classes_in_module.values():
      if klass.__module__.startswith(
        module_name,
      ):  # Check it's defined in or under this module path
        found_classes[get_class_fqn(klass)] = klass

    if hasattr(module, "__path__"):
      for _, sub_module_name, _ in pkgutil.walk_packages(
        module.__path__,
        module_name + ".",
      ):
        if sub_module_name not in visited_modules:
          found_classes.update(
            _discover_classes_in_module_recursive(
              sub_module_name,
              parent_class,
              concrete_only,
              visited_modules,
            ),
          )
  except ImportError as e:
    logger.warning("Could not import module %s: %s", module_name, e)
  except Exception as e:
    logger.exception("Error processing module %s: %s", module_name, e)
  return found_classes


def get_all_classes(
  base_module_names: str | list[str] = "pylabrobot",
  parent_class: type[Any] | None = None,
  concrete_only: bool = False,
) -> dict[str, type[Any]]:
  """Get all PyLabRobot classes from base module(s) and their submodules.

  Args:
    base_module_names: A single module name or a list of names to start discovery.
    parent_class: The parent class to filter by. If None, all classes are returned.
    concrete_only: If True, only return non-abstract classes.

  Returns:
    A dictionary of fully qualified class names to class objects.

  """
  all_classes: dict[str, type[Any]] = {}
  visited_modules: set[str] = set()
  module_list = [base_module_names] if isinstance(base_module_names, str) else base_module_names
  for base_module_name in module_list:
    all_classes.update(
      _discover_classes_in_module_recursive(
        base_module_name,
        parent_class,
        concrete_only,
        visited_modules,
      ),
    )
  return all_classes


def get_resource_classes(
  concrete_only: bool = True,
) -> dict[str, type[Resource]]:
  """Return all resource classes from PyLabRobot modules."""
  return get_all_classes(
    base_module_names=[
      "pylabrobot.resources",
      "pylabrobot.liquid_handling.resources",
    ],
    parent_class=Resource,
    concrete_only=concrete_only,
  )


def get_machine_classes(
  concrete_only: bool = True,
) -> dict[str, type[Machine]]:
  """Return all machine classes from PyLabRobot modules.

  .. deprecated::
    Use :class:`praxis.backend.utils.plr_static_analysis.PLRSourceParser` instead.
    Static analysis avoids import side effects.

  """
  warnings.warn(
    "get_machine_classes() is deprecated. Use PLRSourceParser.discover_machine_classes() instead.",
    DeprecationWarning,
    stacklevel=2,
  )
  return get_all_classes(
    base_module_names="pylabrobot.machines",
    parent_class=Machine,
    concrete_only=concrete_only,
  )


def get_deck_classes(concrete_only: bool = True) -> dict[str, type[Deck]]:
  """Return all deck classes from PyLabRobot modules."""
  all_decks = get_all_classes(
    base_module_names=[
      "pylabrobot.resources",
      "pylabrobot.liquid_handling.resources",
    ],
    parent_class=Deck,
    concrete_only=concrete_only,
  )
  return {fqn: deck_class for fqn, deck_class in all_decks.items() if deck_class is not Deck}


def get_liquid_handler_classes(
  concrete_only: bool = True,
) -> dict[str, type[Any]]:
  """Return all LiquidHandler classes from PyLabRobot modules.

  .. deprecated::
    Use :class:`praxis.backend.utils.plr_static_analysis.PLRSourceParser` instead.
    Static analysis avoids import side effects.

  """
  warnings.warn(
    "get_liquid_handler_classes() is deprecated. Use PLRSourceParser.discover_machine_classes() instead.",
    DeprecationWarning,
    stacklevel=2,
  )
  # Import locally to avoid circular imports or import errors if PLR is broken
  try:
    from pylabrobot.legacy.liquid_handling import LiquidHandler

    return get_all_classes(
      base_module_names=[
        "pylabrobot.liquid_handling",
        "pylabrobot.resources",  # some definitions might be here
      ],
      parent_class=LiquidHandler,
      concrete_only=concrete_only,
    )
  except ImportError:
    return {}


def get_backend_classes(
  concrete_only: bool = True,
) -> dict[str, type[Any]]:
  """Return all Backend classes from PyLabRobot modules.

  .. deprecated::
    Use :class:`praxis.backend.utils.plr_static_analysis.PLRSourceParser` instead.
    Static analysis avoids import side effects.

  """
  warnings.warn(
    "get_backend_classes() is deprecated. Use PLRSourceParser.discover_backend_classes() instead.",
    DeprecationWarning,
    stacklevel=2,
  )
  try:
    from pylabrobot.legacy.liquid_handling.backends import LiquidHandlerBackend

    return get_all_classes(
      base_module_names=[
        "pylabrobot.liquid_handling.backends",
      ],
      parent_class=LiquidHandlerBackend,
      concrete_only=concrete_only,
    )
  except ImportError:
    return {}


def discover_deck_classes(
  packages: str | list[str] = "pylabrobot.resources",
) -> dict[str, type[Deck]]:
  """Discover all non-abstract PLR Deck subclasses in the given Python package(s)."""
  package_list = [packages] if isinstance(packages, str) else list(packages)
  discovered_deck_classes: dict[str, type[Deck]] = {}
  visited_modules: set[str] = set()
  for package_name in package_list:
    try:
      deck_classes_in_pkg = _discover_classes_in_module_recursive(
        package_name,
        Deck,
        concrete_only=True,
        visited_modules=visited_modules,
      )
      for fqn, deck_class in deck_classes_in_pkg.items():
        if issubclass(deck_class, Deck) and deck_class is not Deck:
          discovered_deck_classes[fqn] = deck_class
    except ImportError:
      logger.warning("Package %s not found during deck discovery.", package_name)
    except Exception as e:
      logger.exception("Error discovering deck classes in package %s: %s", package_name, e)
  return discovered_deck_classes


def _get_accepted_categories_for_resource_holder(
  holder: ResourceHolder,
  parent_carrier: Carrier | None = None,
) -> list[str]:
  """Determine accepted resource categories for a ResourceHolder.

  Infer based on the type of the holder or its parent carrier.
  """
  accepted_categories: list[str] = []

  # Check the parent carrier first, as it's often more specific
  if parent_carrier:
    if isinstance(parent_carrier, PlateCarrier):
      accepted_categories.append("Plate")
    elif isinstance(parent_carrier, TipCarrier):
      accepted_categories.append("TipRack")
    elif isinstance(parent_carrier, TroughCarrier):  # Added TroughCarrier check
      accepted_categories.append("Trough")
    # Add other specific carrier types here if needed

  # If no specific parent carrier type, or if it's a direct holder, check holder type
  if not accepted_categories:
    if isinstance(holder, PlateCarrier):
      accepted_categories.append("Plate")
    elif isinstance(holder, TipCarrier):
      accepted_categories.append("TipRack")
    elif "Plate" in holder.__class__.__name__ and "Plate" not in accepted_categories:
      accepted_categories.append("Plate")
    elif "Tip" in holder.__class__.__name__ and "TipRack" not in accepted_categories:
      accepted_categories.append("TipRack")
    elif isinstance(holder, Trough):
      accepted_categories.append("Trough")
    # Add other holder type checks here if needed

  return accepted_categories


def get_resource_holder_classes(
  concrete_only: bool = True,
) -> dict[str, type[ResourceHolder]]:
  """Return all resource holder and specific carrier classes.

  Includes holders and specific carriers from PyLabRobot modules.
  """
  return get_all_classes(
    base_module_names=[
      "pylabrobot.resources",
      "pylabrobot.liquid_handling.resources",
    ],
    parent_class=ResourceHolder,
    concrete_only=concrete_only,
  )


def get_carrier_classes(
  concrete_only: bool = True,
) -> dict[str, type[Carrier]]:
  """Return all carrier classes (including plate, tip, and trough carriers).

  Includes all carrier types from PyLabRobot modules.
  """
  return get_all_classes(
    base_module_names=[
      "pylabrobot.resources",
      "pylabrobot.liquid_handling.resources",
    ],
    parent_class=Carrier,
    concrete_only=concrete_only,
  )


def get_plate_carrier_classes(
  concrete_only: bool = True,
) -> dict[str, type[PlateCarrier]]:
  """Return all plate carrier classes from PyLabRobot modules."""
  return get_all_classes(
    base_module_names=[
      "pylabrobot.resources",
      "pylabrobot.liquid_handling.resources",
    ],
    parent_class=PlateCarrier,
    concrete_only=concrete_only,
  )


def get_tip_carrier_classes(
  concrete_only: bool = True,
) -> dict[str, type[TipCarrier]]:
  """Return all tip carrier classes from PyLabRobot modules."""
  return get_all_classes(
    base_module_names=[
      "pylabrobot.resources",
      "pylabrobot.liquid_handling.resources",
    ],
    parent_class=TipCarrier,
    concrete_only=concrete_only,
  )


def get_trough_carrier_classes(
  concrete_only: bool = True,
) -> dict[str, type[TroughCarrier]]:
  """Return all trough carrier classes from PyLabRobot modules."""
  return get_all_classes(
    base_module_names=[
      "pylabrobot.resources",
      "pylabrobot.liquid_handling.resources",
    ],
    parent_class=TroughCarrier,
    concrete_only=concrete_only,
  )


def get_all_carrier_classes(
  concrete_only: bool = True,
) -> dict[str, type[Carrier]]:
  """Return all carrier classes.

  Includes all carrier types (including plate, tip, and trough carriers) from PyLabRobot
  modules.

  Args:
    concrete_only: If True, only return non-abstract classes.

  Returns:
    A dictionary of fully qualified class names to carrier class objects.

  """
  all_carriers = get_all_classes(
    base_module_names=[
      "pylabrobot.resources",
      "pylabrobot.liquid_handling.resources",
    ],
    parent_class=Carrier,
    concrete_only=concrete_only,
  )
  return {
    fqn: carrier_class
    for fqn, carrier_class in all_carriers.items()
    if carrier_class is not Carrier
  }


def get_all_deck_and_carrier_classes(
  concrete_only: bool = True,
) -> dict[str, type[Deck | Carrier]]:
  """Return all deck and carrier classes from PyLabRobot modules."""
  all_decks = get_deck_classes(concrete_only=concrete_only)
  all_carriers = get_all_carrier_classes(concrete_only=concrete_only)
  return {**all_decks, **all_carriers}


def get_all_resource_classes(
  concrete_only: bool = True,
) -> dict[str, type[Resource]]:
  """Return all resource classes (including holders and specific carriers) from PyLabRobot modules."""
  all_resources = get_resource_classes(concrete_only=concrete_only)
  all_holders = get_resource_holder_classes(concrete_only=concrete_only)
  return {**all_resources, **all_holders}


def get_all_machine_and_deck_classes(
  concrete_only: bool = True,
) -> dict[str, type[Machine | Deck]]:
  """Return all machine and deck classes from PyLabRobot modules."""
  all_machines = get_machine_classes(concrete_only=concrete_only)
  all_decks = get_deck_classes(concrete_only=concrete_only)
  return {**all_machines, **all_decks}


def get_all_classes_with_inspection(
  base_module_names: str | list[str] = "pylabrobot",
  parent_class: type[Any] | None = None,
  concrete_only: bool = False,
) -> dict[str, type[Any]]:
  """Get all classes with enhanced inspection from base module(s) and their submodules.

  This function extends get_all_classes by applying additional inspection logic
  to discover and filter classes based on custom criteria.

  Args:
    base_module_names: A single module name or a list of names to start discovery.
    parent_class: The parent class to filter by. If None, all classes are returned.
    concrete_only: If True, only return non-abstract classes.

  Returns:
    A dictionary of fully qualified class names to class objects.

  """
  all_classes: dict[str, type[Any]] = {}
  visited_modules: set[str] = set()
  module_list = [base_module_names] if isinstance(base_module_names, str) else base_module_names
  for base_module_name in module_list:
    all_classes.update(
      _discover_classes_in_module_recursive(
        base_module_name,
        parent_class,
        concrete_only,
        visited_modules,
      ),
    )

  # --- Additional Inspection Logic ---

  # Filter out abstract classes and interfaces, keeping only concrete classes
  if concrete_only:
    all_classes = {
      name: klass
      for name, klass in all_classes.items()
      if not isabstract(klass)
    }

  return all_classes


def get_all_resource_and_machine_classes(
  concrete_only: bool = True,
) -> dict[str, type[Any]]:
  """Return all resources and machine classes.

  Includes holders, specific carriers, and machines from PyLabRobot modules.
  """
  all_resources = get_all_resource_classes(concrete_only=concrete_only)
  all_machines = get_machine_classes(concrete_only=concrete_only)
  return {**all_resources, **all_machines}


def get_deck_and_carrier_classes(
  concrete_only: bool = True,
) -> dict[str, type[Any]]:
  """Return all deck and carrier classes with enhanced inspection.

  Includes all deck and carrier classes from PyLabRobot modules.
  """
  all_decks_and_carriers = get_all_classes_with_inspection(
    base_module_names=[
      "pylabrobot.resources",
      "pylabrobot.liquid_handling.resources",
    ],
    parent_class=Carrier,
    concrete_only=concrete_only,
  )
  return {
    fqn: deck_or_carrier_class
    for fqn, deck_or_carrier_class in all_decks_and_carriers.items()
    if deck_or_carrier_class is not Carrier
  }


def get_all_resource_and_machine_classes_enhanced(
  concrete_only: bool = True,
) -> dict[str, type[Any]]:
  """Return all resources and machine classes with enhanced inspection.

  Includes holders, specific carriers, and machines from PyLabRobot modules.
  """
  all_resources_and_machines = get_all_classes_with_inspection(
    base_module_names="pylabrobot",
    parent_class=Machine,
    concrete_only=concrete_only,
  )
  return {
    fqn: resource_or_machine_class
    for fqn, resource_or_machine_class in all_resources_and_machines.items()
    if resource_or_machine_class is not Machine
  }
