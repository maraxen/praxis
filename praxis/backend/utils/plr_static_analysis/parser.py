"""Main parser for PLR static analysis."""

import logging
from pathlib import Path

import libcst as cst
from libcst.metadata import MetadataWrapper

from praxis.backend.utils.plr_static_analysis.cache import ParseCache
from praxis.backend.utils.plr_static_analysis.connection_config_templates import (
  get_connection_config_template,
)
from praxis.backend.utils.plr_static_analysis.manufacturer_inference import (
  infer_manufacturer,
  infer_vendor,
)
from praxis.backend.utils.plr_static_analysis.models import (
  MACHINE_BACKEND_TYPES,
  MACHINE_FRONTEND_TYPES,
  DiscoveredBackend,
  DiscoveredClass,
  PLRClassType,
)
from praxis.backend.utils.plr_static_analysis.visitors.capability_extractor import (
  CapabilityExtractorVisitor,
)
from praxis.backend.utils.plr_static_analysis.visitors.class_discovery import (
  EXCLUDED_BASE_CLASS_NAMES,
  ClassDiscoveryVisitor,
)

logger = logging.getLogger(__name__)


class PLRSourceParser:
  """Main entry point for static analysis of PLR sources.

  This parser discovers PLR classes (machines, backends, resources) by
  statically analyzing Python source files using LibCST.

  """

  # Patterns for discovering PLR source files
  # These cover all machine types in PLR
  MACHINE_PATTERNS = (
    "pylabrobot/liquid_handling/**/*.py",
    "pylabrobot/plate_reading/**/*.py",
    "pylabrobot/machines/**/*.py",
    "pylabrobot/heating_shaking/**/*.py",
    "pylabrobot/shaking/**/*.py",
    "pylabrobot/temperature_controlling/**/*.py",
    "pylabrobot/pumps/**/*.py",
    "pylabrobot/centrifuge/**/*.py",
    "pylabrobot/thermocycling/**/*.py",
    "pylabrobot/storage/**/*.py",
    "pylabrobot/sealing/**/*.py",
    "pylabrobot/peeling/**/*.py",
    "pylabrobot/powder_dispensing/**/*.py",
    "pylabrobot/only_fans/**/*.py",
    "pylabrobot/arms/**/*.py",
  )

  RESOURCE_PATTERNS = ("pylabrobot/resources/**/*.py",)

  def __init__(self, plr_source_root: Path, use_cache: bool = True) -> None:
    """Initialize the parser.

    Args:
      plr_source_root: Root directory of PyLabRobot source (containing 'pylabrobot' dir)
      use_cache: Whether to use caching for parse results

    """
    self.plr_source_root = plr_source_root
    self.cache = ParseCache() if use_cache else None
    self._all_classes: list[DiscoveredClass] | None = None
    self._machine_classes: list[DiscoveredClass] | None = None
    self._backend_classes: list[DiscoveredClass] | None = None
    self._resource_classes: list[DiscoveredClass] | None = None

  def discover_all_classes(self) -> list[DiscoveredClass]:
    """Discover all PLR classes from source files.

    Returns:
      List of all discovered PLR classes.

    """
    if self._all_classes is not None:
      return self._all_classes

    discovered: list[DiscoveredClass] = []
    patterns = self.MACHINE_PATTERNS + self.RESOURCE_PATTERNS

    for pattern in patterns:
      for py_file in self.plr_source_root.glob(pattern):
        if py_file.name.startswith("_") and py_file.name != "__init__.py":
          continue
        # Skip test directories and test files to avoid picking up mock backends
        if "/tests/" in str(py_file) or py_file.parent.name == "tests":
          continue
        if py_file.name.endswith("_tests.py") or py_file.name.endswith("_test.py"):
          continue
        try:
          classes = self._parse_file(py_file)
          discovered.extend(classes)
        except Exception as e:
          logger.warning("Failed to parse %s: %s", py_file, e)

    # Enrich with manufacturer and backend matching
    discovered = self._enrich_classes(discovered)
    self._all_classes = discovered

    return discovered

  def discover_machine_classes(self) -> list[DiscoveredClass]:
    """Discover machine-related classes (frontends and backends).

    Returns:
      List of discovered machine classes (non-abstract).

    """
    if self._machine_classes is not None:
      return self._machine_classes

    all_classes = self.discover_all_classes()
    # Use the comprehensive machine type sets from models
    machine_types = MACHINE_FRONTEND_TYPES | MACHINE_BACKEND_TYPES
    self._machine_classes = [
      c for c in all_classes if c.class_type in machine_types and not c.is_abstract
    ]
    return self._machine_classes

  def discover_resource_classes(self) -> list[DiscoveredClass]:
    """Discover resource classes (plates, tip racks, carriers, etc.).

    Returns:
      List of discovered resource classes (non-abstract, non-base).

    """
    if self._resource_classes is not None:
      return self._resource_classes

    all_classes = self.discover_all_classes()
    resource_types = {
      PLRClassType.RESOURCE,
      PLRClassType.CARRIER,
      PLRClassType.DECK,
    }
    self._resource_classes = [
      c
      for c in all_classes
      if c.class_type in resource_types
      and not c.is_abstract
      and c.name not in EXCLUDED_BASE_CLASS_NAMES
    ]
    return self._resource_classes

  def discover_backend_classes(self) -> list[DiscoveredClass]:
    """Discover backend classes only.

    Returns:
      List of discovered backend classes (non-abstract).

    """
    if self._backend_classes is not None:
      return self._backend_classes

    all_classes = self.discover_all_classes()
    # Use the comprehensive backend type set from models
    # Also filter out Mock backends which are for testing only
    self._backend_classes = [
      c
      for c in all_classes
      if c.class_type in MACHINE_BACKEND_TYPES
      and not c.is_abstract
      and "mock" not in c.name.lower()
    ]
    return self._backend_classes

  def discover_frontend_classes(self) -> list[DiscoveredClass]:
    """Discover frontend classes only.

    Returns:
      List of discovered frontend classes (non-abstract).

    """
    all_classes = self.discover_all_classes()
    return [c for c in all_classes if c.class_type in MACHINE_FRONTEND_TYPES and not c.is_abstract]

  def discover_deck_classes(self) -> list[DiscoveredClass]:
    """Discover deck classes.

    Returns:
      List of discovered deck classes (non-abstract).

    """
    all_classes = self.discover_all_classes()
    return [
      c
      for c in all_classes
      if c.class_type == PLRClassType.DECK and not c.is_abstract and c.name != "Deck"
    ]

  def discover_resource_factories(self) -> list[DiscoveredClass]:
    """Discover factory functions that return PLR resource types.

    This finds functions like:
        def Cor_96_wellplate_360ul_Fb(name: str) -> Plate: ...

    Returns:
      List of discovered resource factory functions.

    """
    from praxis.backend.utils.plr_static_analysis.visitors.resource_factory import (
      ResourceFactoryVisitor,
    )

    discovered: list[DiscoveredClass] = []

    for pattern in self.RESOURCE_PATTERNS:
      for py_file in self.plr_source_root.glob(pattern):
        if py_file.name.startswith("_") and py_file.name != "__init__.py":
          continue
        try:
          source = py_file.read_text(encoding="utf-8")
          module_path = self._path_to_module(py_file)

          tree = cst.parse_module(source)
          visitor = ResourceFactoryVisitor(module_path, str(py_file))
          try:
            wrapper = MetadataWrapper(tree)
            wrapper.visit(visitor)
          except Exception:
            # Fall back to simple visit if metadata fails
            for node in tree.body:
              if isinstance(node, cst.FunctionDef):
                visitor.visit_FunctionDef(node)

          discovered.extend(visitor.discovered_resources)
        except Exception as e:
          logger.debug("Failed to parse factory functions in %s: %s", py_file, e)

    return discovered

  def _parse_file(self, file_path: Path) -> list[DiscoveredClass]:
    """Parse a single Python file.

    Args:
      file_path: Path to the Python source file.

    Returns:
      List of discovered classes in the file.

    """
    # Check cache
    if self.cache:
      cached = self.cache.get(file_path)
      if cached:
        return cached

    try:
      source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
      logger.warning("Could not read %s: %s", file_path, e)
      return []

    module_path = self._path_to_module(file_path)

    try:
      tree = cst.parse_module(source)
    except cst.ParserSyntaxError as e:
      logger.warning("Syntax error in %s: %s", file_path, e)
      return []

    # Run class discovery using MetadataWrapper
    discovery_visitor = ClassDiscoveryVisitor(module_path, str(file_path))
    try:
      wrapper = MetadataWrapper(tree)
      wrapper.visit(discovery_visitor)
    except Exception as e:
      # Fall back to manual iteration if metadata fails
      logger.debug("MetadataWrapper failed for %s, using manual iteration: %s", file_path, e)
      self._visit_tree_manually(tree, discovery_visitor)

    # For each discovered class, extract capabilities
    enriched_classes = []
    for cls in discovery_visitor.discovered_classes:
      enriched = self._extract_class_capabilities(tree, cls)
      enriched_classes.append(enriched)

    # Cache results
    if self.cache and enriched_classes:
      self.cache.set(file_path, enriched_classes)

    return enriched_classes

  def _extract_class_capabilities(
    self,
    tree: cst.Module,
    cls: DiscoveredClass,
  ) -> DiscoveredClass:
    """Extract capabilities from a specific class in the tree.

    Args:
      tree: The parsed CST module.
      cls: The discovered class to extract capabilities for.

    Returns:
      The class with capabilities populated.

    """
    # Pass class_type to extractor for type-specific capability detection
    extractor = CapabilityExtractorVisitor(class_type=cls.class_type)

    # Find the class node in the tree and extract capabilities
    for node in tree.body:
      if isinstance(node, cst.ClassDef) and node.name.value == cls.name:
        self._visit_class_manually(node, extractor)
        break

    # Finalize legacy capabilities
    cls.capabilities = extractor.finalize()

    # Build type-specific machine capabilities
    cls.machine_capabilities = extractor.build_machine_capabilities()

    # Build user-configurable capability schema (for dynamic forms)
    cls.capabilities_config = extractor.build_capabilities_config()

    # Build connection configuration schema
    # Detect manufacturer from class info or default to generic
    cls.connection_config = get_connection_config_template(
      cls.class_type, manufacturer=cls.manufacturer
    )

    # Update abstract status if we found abstract methods
    if extractor.has_abstract_methods:
      cls.is_abstract = True

    # Convert to DiscoveredBackend if it's a backend with channel info
    if cls.class_type in (PLRClassType.LH_BACKEND, PLRClassType.PR_BACKEND, PLRClassType.IMAGER_BACKEND):
      return DiscoveredBackend(
        **cls.model_dump(),
        num_channels_default=extractor.num_channels_default,
        num_channels_property=extractor.has_num_channels_property,
      )

    return cls

  def _visit_tree_manually(self, tree: cst.Module, visitor: ClassDiscoveryVisitor) -> None:
    """Manually visit tree nodes when MetadataWrapper fails.

    Args:
      tree: The parsed CST module.
      visitor: The visitor to apply.

    """
    for node in tree.body:
      if isinstance(node, cst.ClassDef):
        visitor.visit_ClassDef(node)

  def _visit_class_manually(
    self, class_node: cst.ClassDef, visitor: CapabilityExtractorVisitor
  ) -> None:
    """Manually visit class body for capability extraction.

    Args:
      class_node: The class definition node.
      visitor: The capability extractor visitor.

    """
    if not isinstance(class_node.body, cst.IndentedBlock):
      return

    for stmt in class_node.body.body:
      if isinstance(stmt, cst.FunctionDef):
        visitor.visit_FunctionDef(stmt)
        # Visit function body for assignments
        if isinstance(stmt.body, cst.IndentedBlock):
          for body_stmt in stmt.body.body:
            if isinstance(body_stmt, cst.SimpleStatementLine):
              for simple_stmt in body_stmt.body:
                if isinstance(simple_stmt, cst.Assign):
                  visitor.visit_Assign(simple_stmt)
                elif isinstance(simple_stmt, cst.AnnAssign):
                  visitor.visit_AnnAssign(simple_stmt)
        visitor.leave_FunctionDef(stmt)

  def _enrich_classes(self, classes: list[DiscoveredClass]) -> list[DiscoveredClass]:
    """Enrich discovered classes with manufacturer and backend matching.

    Args:
      classes: List of discovered classes.

    Returns:
      Enriched list of classes.

    """
    backends = [c for c in classes if c.class_type in MACHINE_BACKEND_TYPES and not c.is_abstract]

    for cls in classes:
      # Infer manufacturer from module path
      cls.manufacturer = infer_manufacturer(cls.module_path)

      # Infer vendor for resources
      if cls.class_type in (PLRClassType.RESOURCE, PLRClassType.CARRIER, PLRClassType.DECK):
        cls.vendor = infer_vendor(cls.module_path)

      # Match frontends to compatible backends
      if cls.class_type in MACHINE_FRONTEND_TYPES:
        cls.compatible_backends = self._find_compatible_backends(cls, backends)

    return classes

  def _find_compatible_backends(
    self,
    frontend: DiscoveredClass,
    backends: list[DiscoveredClass],
  ) -> list[str]:
    """Find backends compatible with a frontend class.

    Args:
      frontend: The frontend class.
      backends: All discovered backend classes.

    Returns:
      List of compatible backend FQNs.

    """
    compatible = []

    # Get expected backend type for this frontend
    target_backend_type = frontend.class_type.get_compatible_backend_type()
    if not target_backend_type:
      return []

    for backend in backends:
      # Filter by type match
      if backend.class_type != target_backend_type:
        continue

      # Always include ChatterBox/simulation backends
      if "chatterbox" in backend.name.lower() or "simulation" in backend.name.lower():
        compatible.append(backend.fqn)
        continue

      # If frontend is generic (no manufacturer or 'pylabrobot'), allow all backends of correct type
      if not frontend.manufacturer or frontend.manufacturer.lower() == "pylabrobot":
        compatible.append(backend.fqn)
        continue

      # Match by manufacturer
      if frontend.manufacturer and backend.manufacturer:
        if frontend.manufacturer.lower() == backend.manufacturer.lower():
          compatible.append(backend.fqn)
          continue

      # Loose name matching as fallback
      frontend_clean = frontend.name.lower()
      backend_clean = backend.name.lower()

      # Remove common suffixes/prefixes
      for term in ["liquidhandler", "platereader", "heatershaker", "backend", "_"]:
        frontend_clean = frontend_clean.replace(term, "")
        backend_clean = backend_clean.replace(term, "")

      if (
        frontend_clean
        and backend_clean
        and (frontend_clean in backend_clean or backend_clean in frontend_clean)
      ):
        compatible.append(backend.fqn)

    return compatible

  def _path_to_module(self, file_path: Path) -> str:
    """Convert file path to module path.

    Args:
      file_path: Path to the Python source file.

    Returns:
      The module path (e.g., 'pylabrobot.liquid_handling.backends.hamilton.STAR_backend')

    """
    try:
      relative = file_path.relative_to(self.plr_source_root)
    except ValueError:
      # File is not under plr_source_root
      relative = file_path

    module_path = str(relative.with_suffix("")).replace("/", ".").replace("\\", ".")

    # Remove __init__ suffix
    return module_path.removesuffix(".__init__")

  def clear_cache(self) -> None:
    """Clear the parse cache."""
    if self.cache:
      self.cache.clear()
    self._all_classes = None
    self._machine_classes = None
    self._backend_classes = None
    self._resource_classes = None


def find_plr_source_root() -> Path:
  """Find the PLR source root directory.

  Searches common locations for the PyLabRobot source.

  Returns:
    Path to the PLR source root.

  Raises:
    RuntimeError: If PLR source cannot be found.

  """
  # Check relative to this file (praxis project structure)
  praxis_root = Path(__file__).parent.parent.parent.parent.parent

  # Check external/pylabrobot first (current project structure)
  external_plr = praxis_root / "external" / "pylabrobot"
  if (external_plr / "pylabrobot").is_dir():
    return external_plr

  # Then check lib/pylabrobot (legacy)
  lib_plr = praxis_root / "lib" / "pylabrobot"
  if (lib_plr / "pylabrobot").is_dir():
    return lib_plr

  # Check site-packages
  try:
    import pylabrobot

    plr_path = Path(pylabrobot.__file__).parent.parent
    if (plr_path / "pylabrobot").is_dir():
      return plr_path
  except ImportError:
    pass

  msg = "Could not find PyLabRobot source directory"
  raise RuntimeError(msg)
