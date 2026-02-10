"""Class discovery visitor for PLR static analysis."""

import libcst as cst

from praxis.backend.utils.plr_static_analysis.models import (
  DiscoveredCapabilities,
  DiscoveredClass,
  PLRClassType,
)
from praxis.backend.utils.plr_static_analysis.visitors.base import BasePLRVisitor

# =============================================================================
# Known PLR base classes for classification
# These are used to identify the type of class being discovered
# =============================================================================

# -----------------------------------------------------------------------------
# MACHINE FRONTEND BASE CLASSES
# Classes that users interact with (API layer)
# Many of these also inherit from Resource/ResourceHolder, so we must
# check machine bases BEFORE resource bases in classification.
# -----------------------------------------------------------------------------

LIQUID_HANDLER_BASES: frozenset[str] = frozenset(
  {
    "LiquidHandler",
  }
)

PLATE_READER_BASES: frozenset[str] = frozenset(
  {
    "PlateReader",
  }
)

IMAGER_BASES: frozenset[str] = frozenset(
  {
    "Imager",
    "ImageReader",
  }
)

HEATER_SHAKER_BASES: frozenset[str] = frozenset(
  {
    "HeaterShaker",
  }
)

SHAKER_BASES: frozenset[str] = frozenset(
  {
    "Shaker",
  }
)

TEMPERATURE_CONTROLLER_BASES: frozenset[str] = frozenset(
  {
    "TemperatureController",
  }
)

CENTRIFUGE_BASES: frozenset[str] = frozenset(
  {
    "Centrifuge",
  }
)

THERMOCYCLER_BASES: frozenset[str] = frozenset(
  {
    "Thermocycler",
  }
)

PUMP_BASES: frozenset[str] = frozenset(
  {
    "Pump",
  }
)

PUMP_ARRAY_BASES: frozenset[str] = frozenset(
  {
    "PumpArray",
  }
)

FAN_BASES: frozenset[str] = frozenset(
  {
    "Fan",
  }
)

SEALER_BASES: frozenset[str] = frozenset(
  {
    "Sealer",
  }
)

PEELER_BASES: frozenset[str] = frozenset(
  {
    "Peeler",
  }
)

POWDER_DISPENSER_BASES: frozenset[str] = frozenset(
  {
    "PowderDispenser",
  }
)

INCUBATOR_BASES: frozenset[str] = frozenset(
  {
    "Incubator",
  }
)

SCARA_BASES: frozenset[str] = frozenset(
  {
    "ExperimentalSCARA",
    "SCARA",
  }
)

# Combined set of all machine frontend bases
# Used for priority classification - if a class inherits from any of these,
# it's a machine, not a resource, even if it also inherits from Resource.
ALL_MACHINE_FRONTEND_BASES: frozenset[str] = (
  LIQUID_HANDLER_BASES
  | PLATE_READER_BASES
  | IMAGER_BASES
  | HEATER_SHAKER_BASES
  | SHAKER_BASES
  | TEMPERATURE_CONTROLLER_BASES
  | CENTRIFUGE_BASES
  | THERMOCYCLER_BASES
  | PUMP_BASES
  | PUMP_ARRAY_BASES
  | FAN_BASES
  | SEALER_BASES
  | PEELER_BASES
  | POWDER_DISPENSER_BASES
  | INCUBATOR_BASES
  | SCARA_BASES
  | frozenset({"Machine"})  # Include base Machine class
)

# -----------------------------------------------------------------------------
# MACHINE BACKEND BASE CLASSES
# Hardware driver implementations
# -----------------------------------------------------------------------------

LH_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "LiquidHandlerBackend",
    "HamiltonLiquidHandler",  # Hamilton-specific abstract base
    "STARBackend",
    "STARletBackend",
    "VantageBackend",
    "OpentronsBackend",
    "ChatterboxBackend",
    "LiquidHandlerChatterboxBackend",
  }
)

PR_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "PlateReaderBackend",
  }
)

IMAGER_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "ImagerBackend",
    "ImageReaderBackend",
  }
)

HS_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "HeaterShakerBackend",
  }
)

SHAKER_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "ShakerBackend",
  }
)

TEMP_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "TemperatureControllerBackend",
  }
)

CENTRIFUGE_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "CentrifugeBackend",
    "LoaderBackend",  # Centrifuge loader
  }
)

THERMOCYCLER_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "ThermocyclerBackend",
  }
)

PUMP_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "PumpBackend",
  }
)

PUMP_ARRAY_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "PumpArrayBackend",
  }
)

FAN_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "FanBackend",
  }
)

SEALER_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "SealerBackend",
  }
)

PEELER_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "PeelerBackend",
  }
)

POWDER_DISPENSER_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "PowderDispenserBackend",
  }
)

INCUBATOR_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "IncubatorBackend",
  }
)

SCARA_BACKEND_BASES: frozenset[str] = frozenset(
  {
    "SCARABackend",
  }
)

# Combined set of all machine backend bases
ALL_MACHINE_BACKEND_BASES: frozenset[str] = (
  LH_BACKEND_BASES
  | PR_BACKEND_BASES
  | IMAGER_BACKEND_BASES
  | HS_BACKEND_BASES
  | SHAKER_BACKEND_BASES
  | TEMP_BACKEND_BASES
  | CENTRIFUGE_BACKEND_BASES
  | THERMOCYCLER_BACKEND_BASES
  | PUMP_BACKEND_BASES
  | PUMP_ARRAY_BACKEND_BASES
  | FAN_BACKEND_BASES
  | SEALER_BACKEND_BASES
  | PEELER_BACKEND_BASES
  | POWDER_DISPENSER_BACKEND_BASES
  | INCUBATOR_BACKEND_BASES
  | SCARA_BACKEND_BASES
  | frozenset({"MachineBackend"})  # Include base MachineBackend class
)

# -----------------------------------------------------------------------------
# INFRASTRUCTURE BASE CLASSES
# Decks, carriers, and resources
# -----------------------------------------------------------------------------

DECK_BASES: frozenset[str] = frozenset(
  {
    "Deck",
  }
)

CARRIER_BASES: frozenset[str] = frozenset(
  {
    "Carrier",
    "PlateCarrier",
    "TipCarrier",
    "TroughCarrier",
    "TubeCarrier",
    "MFXCarrier",
  }
)

RESOURCE_BASES: frozenset[str] = frozenset(
  {
    "Resource",
    "ResourceHolder",
    "Plate",
    "TipRack",
    "Trough",
    "Tube",
    "TubeRack",
    "Container",
    "ItemizedResource",
    "Well",
    "TipSpot",
    "Lid",
    "Trash",
    "PetriDish",
    "PlateAdapter",
    "NestedTipRack",
  }
)

# Base classes that should be excluded from cataloging (they're abstract/generic)
EXCLUDED_BASE_CLASS_NAMES: frozenset[str] = frozenset(
  {
    "Resource",
    "ResourceHolder",
    "Carrier",
    "Container",
    "Deck",
    "ItemizedResource",
    "Lid",
    "MFXCarrier",
    "NestedTipRack",
    "PetriDish",
    "PetriDishHolder",
    "Plate",
    "PlateAdapter",
    "PlateCarrier",
    "PlateHolder",
    "ResourceStack",
    "TipCarrier",
    "TipRack",
    "TipSpot",
    "Trash",
    "Trough",
    "TroughCarrier",
    "Tube",
    "TubeCarrier",
    "TubeRack",
    "Well",
  }
)


class ClassDiscoveryVisitor(BasePLRVisitor):
  """Discovers classes and their inheritance hierarchy from PLR source."""

  def __init__(self, module_path: str, file_path: str) -> None:
    """Initialize the visitor.

    Args:
      module_path: The Python module path
      file_path: The absolute file path to the source file

    """
    super().__init__(module_path, file_path)
    self.discovered_classes: list[DiscoveredClass] = []
    self._has_abstractmethod = False

  def visit_ClassDef(self, node: cst.ClassDef) -> bool:  # noqa: N802
    """Visit a class definition and extract information.

    Args:
      node: The class definition node.

    Returns:
      True to continue visiting nested classes.

    """
    class_name = node.name.value
    base_classes = self._extract_base_classes(node)
    class_type = self._classify_class(base_classes, class_name)

    # Skip unknown classes
    if class_type == PLRClassType.UNKNOWN:
      return True

    # Check if abstract (will be refined by capability extractor)
    is_abstract = self._is_abstract_class(node) or self._check_abstract_methods(node)

    fqn = f"{self.module_path}.{class_name}"
    docstring = self._get_docstring(node.body)

    discovered = DiscoveredClass(
      fqn=fqn,
      name=class_name,
      module_path=self.module_path,
      file_path=self.file_path,
      class_type=class_type,
      base_classes=base_classes,
      is_abstract=is_abstract,
      docstring=docstring,
      capabilities=DiscoveredCapabilities(),
    )
    self.discovered_classes.append(discovered)

    return True  # Continue visiting nested classes

  def _extract_base_classes(self, node: cst.ClassDef) -> list[str]:
    """Extract base class names from class definition.

    Args:
      node: The class definition node.

    Returns:
      List of base class names.

    """
    bases = []
    for arg in node.bases:
      name = self._name_to_string(arg.value)
      if name:
        # Only keep the last part of the name (e.g., 'module.ClassName' -> 'ClassName')
        bases.append(name.split(".")[-1])
    return bases

  def _classify_class(self, base_classes: list[str], class_name: str) -> PLRClassType:
    """Classify class based on inheritance.

    Classification priority (most specific to least specific):
    1. Machine backends (most specific - always check first)
    2. Machine frontends (must be checked BEFORE resources!)
    3. Infrastructure types (decks, carriers)
    4. Resources (least specific - many machines inherit from Resource)

    Note: We also check if the class name itself is a known machine type,
    since base classes like HeaterShaker, Shaker, etc. don't inherit from
    a class with that same name.

    Args:
      base_classes: List of base class names.
      class_name: The name of the class.

    Returns:
      The classification of the class.

    """
    base_set = set(base_classes)
    # Also include the class name itself for classification
    # This handles base classes like HeaterShaker, Centrifuge, etc.
    base_set_with_self = base_set | {class_name}

    # -------------------------------------------------------------------------
    # 1. Check machine backends first (most specific)
    # Use base_set_with_self to also match backend base classes themselves
    # -------------------------------------------------------------------------
    if base_set_with_self & LH_BACKEND_BASES:
      return PLRClassType.LH_BACKEND
    if base_set_with_self & IMAGER_BACKEND_BASES:
      return PLRClassType.IMAGER_BACKEND
    if base_set_with_self & PR_BACKEND_BASES:
      return PLRClassType.PR_BACKEND
    if base_set_with_self & HS_BACKEND_BASES:
      return PLRClassType.HS_BACKEND
    if base_set_with_self & SHAKER_BACKEND_BASES:
      return PLRClassType.SHAKER_BACKEND
    if base_set_with_self & TEMP_BACKEND_BASES:
      return PLRClassType.TEMP_BACKEND
    if base_set_with_self & CENTRIFUGE_BACKEND_BASES:
      return PLRClassType.CENTRIFUGE_BACKEND
    if base_set_with_self & THERMOCYCLER_BACKEND_BASES:
      return PLRClassType.THERMOCYCLER_BACKEND
    if base_set_with_self & PUMP_ARRAY_BACKEND_BASES:
      return PLRClassType.PUMP_ARRAY_BACKEND
    if base_set_with_self & PUMP_BACKEND_BASES:
      return PLRClassType.PUMP_BACKEND
    if base_set_with_self & FAN_BACKEND_BASES:
      return PLRClassType.FAN_BACKEND
    if base_set_with_self & SEALER_BACKEND_BASES:
      return PLRClassType.SEALER_BACKEND
    if base_set_with_self & PEELER_BACKEND_BASES:
      return PLRClassType.PEELER_BACKEND
    if base_set_with_self & POWDER_DISPENSER_BACKEND_BASES:
      return PLRClassType.POWDER_DISPENSER_BACKEND
    if base_set_with_self & INCUBATOR_BACKEND_BASES:
      return PLRClassType.INCUBATOR_BACKEND
    if base_set_with_self & SCARA_BACKEND_BASES:
      return PLRClassType.SCARA_BACKEND

    # -------------------------------------------------------------------------
    # 2. Check machine frontends BEFORE resources
    # This is critical because many machines inherit from Resource/ResourceHolder
    # (e.g., LiquidHandler inherits from Resource, Machine)
    # Use base_set_with_self to also match machine base classes themselves
    # -------------------------------------------------------------------------
    if base_set_with_self & LIQUID_HANDLER_BASES:
      return PLRClassType.LIQUID_HANDLER
    if base_set_with_self & IMAGER_BASES:
      return PLRClassType.IMAGER
    if base_set_with_self & PLATE_READER_BASES:
      return PLRClassType.PLATE_READER
    # HeaterShaker inherits from TemperatureController + Shaker, check first
    if base_set_with_self & HEATER_SHAKER_BASES:
      return PLRClassType.HEATER_SHAKER
    if base_set_with_self & SHAKER_BASES:
      return PLRClassType.SHAKER
    if base_set_with_self & TEMPERATURE_CONTROLLER_BASES:
      return PLRClassType.TEMPERATURE_CONTROLLER
    if base_set_with_self & CENTRIFUGE_BASES:
      return PLRClassType.CENTRIFUGE
    if base_set_with_self & THERMOCYCLER_BASES:
      return PLRClassType.THERMOCYCLER
    if base_set_with_self & PUMP_ARRAY_BASES:
      return PLRClassType.PUMP_ARRAY
    if base_set_with_self & PUMP_BASES:
      return PLRClassType.PUMP
    if base_set_with_self & FAN_BASES:
      return PLRClassType.FAN
    if base_set_with_self & SEALER_BASES:
      return PLRClassType.SEALER
    if base_set_with_self & PEELER_BASES:
      return PLRClassType.PEELER
    if base_set_with_self & POWDER_DISPENSER_BASES:
      return PLRClassType.POWDER_DISPENSER
    if base_set_with_self & INCUBATOR_BASES:
      return PLRClassType.INCUBATOR
    if base_set_with_self & SCARA_BASES:
      return PLRClassType.SCARA

    # -------------------------------------------------------------------------
    # 3. Check infrastructure types
    # -------------------------------------------------------------------------
    if base_set & DECK_BASES:
      return PLRClassType.DECK
    if base_set & CARRIER_BASES:
      return PLRClassType.CARRIER

    # -------------------------------------------------------------------------
    # 4. Check resources last (least specific)
    # -------------------------------------------------------------------------
    if base_set & RESOURCE_BASES:
      return PLRClassType.RESOURCE

    # -------------------------------------------------------------------------
    # 5. Fallback: Check by class name patterns
    # -------------------------------------------------------------------------
    name_lower = class_name.lower()
    if "backend" in name_lower:
      if "liquidhandler" in name_lower or "lh" in name_lower:
        return PLRClassType.LH_BACKEND
      if "imager" in name_lower or "imagereader" in name_lower:
        return PLRClassType.IMAGER_BACKEND
      if "platereader" in name_lower or "pr" in name_lower:
        return PLRClassType.PR_BACKEND
      if "heatershaker" in name_lower or "hs" in name_lower:
        return PLRClassType.HS_BACKEND
      if "shaker" in name_lower:
        return PLRClassType.SHAKER_BACKEND
      if "temperature" in name_lower or "temp" in name_lower:
        return PLRClassType.TEMP_BACKEND
      if "centrifuge" in name_lower:
        return PLRClassType.CENTRIFUGE_BACKEND
      if "thermocycler" in name_lower:
        return PLRClassType.THERMOCYCLER_BACKEND
      if "pumparray" in name_lower:
        return PLRClassType.PUMP_ARRAY_BACKEND
      if "pump" in name_lower:
        return PLRClassType.PUMP_BACKEND
      if "fan" in name_lower:
        return PLRClassType.FAN_BACKEND
      if "sealer" in name_lower:
        return PLRClassType.SEALER_BACKEND
      if "peeler" in name_lower:
        return PLRClassType.PEELER_BACKEND
      if "powder" in name_lower:
        return PLRClassType.POWDER_DISPENSER_BACKEND
      if "incubator" in name_lower:
        return PLRClassType.INCUBATOR_BACKEND
      if "scara" in name_lower:
        return PLRClassType.SCARA_BACKEND

    return PLRClassType.UNKNOWN

  def _check_abstract_methods(self, node: cst.ClassDef) -> bool:
    """Check if class has @abstractmethod decorated methods.

    Args:
      node: The class definition node.

    Returns:
      True if the class has abstract methods.

    """
    if not isinstance(node.body, cst.IndentedBlock):
      return False

    for stmt in node.body.body:
      if isinstance(stmt, cst.FunctionDef):
        for decorator in stmt.decorators:
          dec_name = self._name_to_string(decorator.decorator)
          if dec_name in ("abstractmethod", "abc.abstractmethod"):
            return True
    return False

  def is_excluded_base_class(self, class_name: str) -> bool:
    """Check if a class name is an excluded base class.

    Args:
      class_name: The name of the class.

    Returns:
      True if the class should be excluded from cataloging.

    """
    return class_name in EXCLUDED_BASE_CLASS_NAMES
