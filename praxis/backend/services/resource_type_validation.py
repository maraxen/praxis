"""Validation and parsing logic for PyLabRobot resource type definitions."""

import contextlib
import inspect
import math
import re
from typing import Any

from pylabrobot.resources import (
  Carrier,
  Container,
  Deck,
  ItemizedResource,
  Lid,
  MFXCarrier,
  NestedTipRack,
  PetriDish,
  PetriDishHolder,
  Plate,
  PlateAdapter,
  PlateCarrier,
  PlateHolder,
  Resource,
  ResourceHolder,
  ResourceStack,
  TipCarrier,
  TipRack,
  TipSpot,
  Trash,
  Trough,
  TroughCarrier,
  Tube,
  TubeCarrier,
  TubeRack,
  Well,
)

from praxis.backend.utils.logging import get_logger

logger = get_logger(__name__)

# Generic base classes that should NOT be cataloged as resource definitions.
# These are abstract or intermediate types, not usable resource definitions.
EXCLUDED_BASE_CLASSES: tuple[type[Resource], ...] = (
  Carrier,  # Base carrier type
  Container,  # Base container type
  Deck,  # Base deck type
  ItemizedResource,  # Resources with indexed items
  Lid,  # Base lid type
  MFXCarrier,  # Base MFX carrier type
  NestedTipRack,  # Nested tip rack base
  PetriDish,  # Base petri dish type
  PetriDishHolder,  # Petri dish holder base
  Plate,  # Base plate type - concrete plates are factory functions
  PlateAdapter,  # Plate adapter base
  PlateCarrier,  # Plate carrier base
  PlateHolder,  # Plate holder base
  Resource,  # Root resource type
  ResourceHolder,  # Resource holder base
  ResourceStack,  # Resource stack base
  TipCarrier,  # Tip carrier base
  TipRack,  # Base tip rack - concrete tip racks are factory functions
  TipSpot,  # Individual tip spots
  Trash,  # Base trash type
  Trough,  # Base trough type
  TroughCarrier,  # Trough carrier base
  Tube,  # Base tube type
  TubeCarrier,  # Tube carrier base
  TubeRack,  # Base tube rack type
  Well,  # Individual wells in plates
)


def can_catalog_resource(plr_class: type[Any]) -> bool:
  """Determine if a PyLabRobot class represents a resource definition to catalog.

  Excludes:
  - Non-Resource subclasses
  - Abstract classes
  - Generic base classes (by identity or name)
  - Classes not in pylabrobot.resources namespace
  """
  if not inspect.isclass(plr_class) or not issubclass(plr_class, Resource):
    return False
  if inspect.isabstract(plr_class):
    return False
  # Check by identity (exact class object match)
  if plr_class in EXCLUDED_BASE_CLASSES:
    return False
  # Check by name (handles cases where class is imported via different paths)
  excluded_names = {cls.__name__ for cls in EXCLUDED_BASE_CLASSES}
  if plr_class.__name__ in excluded_names:
    return False
  return plr_class.__module__.startswith("pylabrobot.resources")


def get_category_from_plr_class(plr_class: type[Any]) -> str | None:
  """Extract the category from a PyLabRobot class."""
  if hasattr(plr_class, "category"):
    category = plr_class.category
    # Normalize categories (e.g. tecan_plate -> plate)
    if category:
      if "plate" in category and category != "plate":
        return "plate"
      if "tip_rack" in category and category != "tip_rack":
        return "tip_rack"
      if "carrier" in category and category != "carrier":
        # Keep specific carrier types if needed, but for now normalize if it's just vendor_carrier
        if category.endswith("_carrier") and category not in {
          "plate_carrier",
          "tip_carrier",
          "tube_carrier",
        }:
          return "carrier"
    return category
  return None


def extract_ordering_from_plr_class(plr_class: type[Any]) -> str | None:
  """Extract ordering information from a PyLabRobot class."""
  if hasattr(plr_class, "ordering") and isinstance(plr_class.ordering, list):
    return ",".join(plr_class.ordering)
  return None


def get_short_name_from_plr_class(plr_class: type[Any]) -> str:
  """Extract the short name from a PyLabRobot class."""
  return plr_class.__name__


def get_description_from_plr_class(plr_class: type[Any]) -> str | None:
  """Extract the description from a PyLabRobot class."""
  return inspect.getdoc(plr_class)


def get_size_x_mm_from_plr_class(plr_class: type[Any]) -> float | None:
  """Extract the size_x_mm from a PyLabRobot class."""
  if hasattr(plr_class, "size_x"):
    return plr_class.size_x
  return None


def get_size_y_mm_from_plr_class(plr_class: type[Any]) -> float | None:
  """Extract the size_y_mm from a PyLabRobot class."""
  if hasattr(plr_class, "size_y"):
    return plr_class.size_y
  return None


def get_size_z_mm_from_plr_class(plr_class: type[Any]) -> float | None:
  """Extract the size_z_mm from a PyLabRobot class."""
  if hasattr(plr_class, "size_z"):
    return plr_class.size_z
  return None


def get_nominal_volume_ul_from_plr_class(plr_class: type[Any]) -> float | None:
  """Extract the nominal_volume_ul from a PyLabRobot class."""
  if hasattr(plr_class, "nominal_volume"):
    return plr_class.nominal_volume
  return None


def is_resource_factory_function(func: Any) -> bool:
  """Check if a function is a resource factory (creates Resource instances).

  Factory functions are the primary way PyLabRobot defines concrete resources.
  They return instances of Plate, TipRack, Trough, etc.
  """
  if not inspect.isfunction(func):
    return False

  # Check if function name starts with common resource prefixes
  name = func.__name__
  # Skip internal/private functions
  if name.startswith("_"):
    return False

  # Skip utility functions with common names
  # Valid return types for resource factory functions
  valid_return_types = {
    "Plate",
    "TipRack",
    "Trough",
    "Tube",
    "TubeRack",
    "Carrier",
    "PlateCarrier",
    "TipCarrier",
    "TroughCarrier",
    "TubeCarrier",
    "Lid",
    "PetriDish",
    "Container",
  }

  # Check return type annotation
  try:
    hints = inspect.signature(func).return_annotation
    if hints != inspect.Signature.empty and inspect.isclass(hints):
      # Reject if return type is exactly Resource (base class)
      if hints.__name__ == "Resource":
        return False
      # Accept if return type is in allowlist
      if hints.__name__ in valid_return_types:
        return True
  except (ValueError, TypeError):
    pass

  return False


def extract_vendor_from_fqn(fqn: str) -> str | None:
  """Extract vendor name from FQN like 'pylabrobot.resources.corning.plates.Cor_96'."""
  # Known vendor module patterns - all 28 PLR vendors
  vendor_patterns = {
    "hamilton": "hamilton",
    "opentrons": "opentrons",
    "tecan": "tecan",
    "corning": "corning",
    "azenta": "azenta",
    "alpaqua": "alpaqua",
    "boekel": "boekel",
    "greiner": "greiner",
    "thermo": "thermo",
    "revvity": "revvity",
    "porvair": "porvair",
    "agenbio": "agenbio",
    "agilent": "agilent",
    "bioer": "bioer",
    "biorad": "biorad",
    "celltreat": "celltreat",
    "cellvis": "cellvis",
    "diy": "diy",
    "eppendorf": "eppendorf",
    "falcon": "falcon",
    "imcs": "imcs",
    "nest": "nest",
    "perkin_elmer": "perkin_elmer",
    "sergi": "sergi",
    "stanley": "stanley",
    "thermo_fisher": "thermo_fisher",
    "vwr": "vwr",
  }
  fqn_lower = fqn.lower()
  for pattern, vendor in vendor_patterns.items():
    if f".{pattern}." in fqn_lower or f".{pattern}" in fqn_lower:
      return vendor
  return None


def parse_volume_from_name(name: str) -> float | None:
  """Parse volume from model name like 'Cor_96_wellplate_360ul_Fb' or '2mL'."""
  vol_match = re.search(r"(\d+(?:\.\d+)?)(ul|ml)", name.lower())
  if vol_match:
    vol = float(vol_match.group(1))
    unit = vol_match.group(2)
    return vol * 1000 if unit == "ml" else vol
  return None


def parse_num_items_from_name(name: str) -> int | None:
  """Parse number of items (wells/tips) from model name like 'Cor_96_wellplate'."""
  for count in [384, 96, 48, 24, 12, 6]:
    if f"_{count}_" in name or f"_{count}" in name or name.startswith(f"{count}_"):
      return count
  return None


def parse_plate_type_from_name(name: str) -> str | None:
  """Parse plate type from model name like 'Cor_96_wellplate_360ul_Fb'."""
  name_lower = name.lower()
  if "_fb" in name_lower or "flatbottom" in name_lower or "flat_bottom" in name_lower:
    return "flat"
  if "_vb" in name_lower or "vbottom" in name_lower or "v_bottom" in name_lower:
    return "v-bottom"
  if "_rb" in name_lower or "roundbottom" in name_lower or "round_bottom" in name_lower:
    return "round"
  if "_cb" in name_lower or "conicalbottom" in name_lower or "conical_bottom" in name_lower:
    return "conical"
  return None


def extract_properties_from_instance(instance: Any) -> dict[str, Any]:
  """Extract properties from a PLR instance based on class inheritance."""
  props: dict[str, Any] = {}

  # All Resources - basic dimensions
  props["size_x_mm"] = getattr(instance, "_size_x", None)
  props["size_y_mm"] = getattr(instance, "_size_y", None)
  props["size_z_mm"] = getattr(instance, "_size_z", None)
  props["category"] = getattr(instance, "category", None)
  props["model"] = getattr(instance, "model", None)

  # ItemizedResource (Plate, TipRack) - item count
  if hasattr(instance, "num_items"):
    with contextlib.suppress(Exception):
      props["num_items"] = instance.num_items
    if hasattr(instance, "num_items_x"):
      try:
        props["num_items_x"] = instance.num_items_x
        props["num_items_y"] = instance.num_items_y
      except Exception:
        pass

  # Plate-specific - plate_type and well properties
  if hasattr(instance, "plate_type"):
    props["plate_type"] = getattr(instance, "plate_type", None)
    try:
      wells = instance.get_all_items()
      if wells:
        first_well = wells[0]
        props["well_volume_ul"] = getattr(first_well, "max_volume", None)
        bottom_type = getattr(first_well, "bottom_type", None)
        if bottom_type is not None:
          props["well_bottom_type"] = (
            bottom_type.value if hasattr(bottom_type, "value") else str(bottom_type)
          )
        cross_section = getattr(first_well, "cross_section_type", None)
        if cross_section is not None:
          props["well_cross_section"] = (
            cross_section.value if hasattr(cross_section, "value") else str(cross_section)
          )
    except Exception:
      pass

  # TipRack-specific - tip properties from prototype
  if hasattr(instance, "get_all_items") and props.get("category") == "tip_rack":
    try:
      spots = instance.get_all_items()
      if spots and hasattr(spots[0], "make_tip"):
        tip = spots[0].make_tip()
        props["tip_volume_ul"] = getattr(tip, "maximal_volume", None)
        props["tip_has_filter"] = getattr(tip, "has_filter", None)
        # PLR 1.0: Tip is a Resource; total_tip_length was removed, size_z is the tip length.
        props["tip_length_mm"] = getattr(tip, "size_z", None)
        props["tip_fitting_depth_mm"] = getattr(tip, "fitting_depth", None)
    except Exception:
      pass

  # Container - max_volume (for troughs, tubes, etc.)
  if hasattr(instance, "max_volume") and "well_volume_ul" not in props:
    props["max_volume_ul"] = getattr(instance, "max_volume", None)

  def is_json_serializable(v: Any) -> bool:
    if v is None:
      return False
    return not (isinstance(v, float) and (math.isinf(v) or math.isnan(v)))

  return {k: v for k, v in props.items() if is_json_serializable(v)}


def get_metadata_from_factory_function(func: Any, fqn: str) -> dict[str, Any]:
  """Extract metadata from a resource factory function by instantiating it."""
  name = func.__name__
  metadata: dict[str, Any] = {
    "name": name,
    "description": inspect.getdoc(func),
    "category": None,
    "ordering": None,
    "size_x_mm": None,
    "size_y_mm": None,
    "size_z_mm": None,
    "nominal_volume_ul": None,
    # Dynamic filter fields - will be populated from instance
    "num_items": parse_num_items_from_name(name),
    "plate_type": parse_plate_type_from_name(name),
    "well_volume_ul": None,
    "tip_volume_ul": None,
    "vendor": extract_vendor_from_fqn(fqn),
    "properties_json": None,
  }

  # Try to infer category from function name (fallback)
  name_lower = name.lower()
  if "plate" in name_lower or "_vb" in name_lower or "_fb" in name_lower:
    metadata["category"] = "plate"
    metadata["well_volume_ul"] = parse_volume_from_name(name)
  elif "tip" in name_lower:
    metadata["category"] = "tip_rack"
    metadata["tip_volume_ul"] = parse_volume_from_name(name)
  elif "trough" in name_lower:
    metadata["category"] = "trough"
  elif "tube" in name_lower:
    metadata["category"] = "tube"
  elif "lid" in name_lower:
    metadata["category"] = "lid"
  elif "carrier" in name_lower:
    metadata["category"] = "carrier"

  # Try to instantiate the factory function and extract properties
  try:
    # Most PLR factory functions take a name argument
    instance = func(name=f"_temp_{name}")
    props = extract_properties_from_instance(instance)
    metadata["properties_json"] = props

    # Override metadata with actual values from instance
    if props.get("size_x_mm"):
      metadata["size_x_mm"] = props["size_x_mm"]
    if props.get("size_y_mm"):
      metadata["size_y_mm"] = props["size_y_mm"]
    if props.get("size_z_mm"):
      metadata["size_z_mm"] = props["size_z_mm"]
    if props.get("category"):
      metadata["category"] = props["category"]
    if props.get("num_items"):
      metadata["num_items"] = props["num_items"]
    if props.get("plate_type"):
      metadata["plate_type"] = props["plate_type"]
    if props.get("well_volume_ul"):
      metadata["well_volume_ul"] = props["well_volume_ul"]
    if props.get("tip_volume_ul"):
      metadata["tip_volume_ul"] = props["tip_volume_ul"]

    logger.debug("Extracted properties from instance: %s", fqn)
  except Exception as e:
    logger.debug("Could not instantiate factory function %s: %s", fqn, e)

  return metadata
