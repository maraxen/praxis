"""Tests for PLR static analysis module."""

import libcst as cst
import pytest

from praxis.backend.utils.plr_static_analysis import (
  MACHINE_BACKEND_TYPES,
  MACHINE_FRONTEND_TYPES,
  DiscoveredClass,
  PLRClassType,
  PLRSourceParser,
  find_plr_source_root,
)
from praxis.backend.utils.plr_static_analysis.manufacturer_inference import (
  infer_manufacturer,
  infer_vendor,
  is_vendor_module,
)


class TestManufacturerInference:
  """Tests for manufacturer inference from module paths."""

  def test_infer_hamilton(self):
    """Test Hamilton manufacturer inference."""
    assert infer_manufacturer("pylabrobot.liquid_handling.backends.hamilton.STAR") == "Hamilton"

  def test_infer_opentrons(self):
    """Test Opentrons manufacturer inference."""
    assert infer_manufacturer("pylabrobot.liquid_handling.backends.opentrons_backend") == "Opentrons"

  def test_infer_tecan(self):
    """Test Tecan manufacturer inference."""
    assert infer_manufacturer("pylabrobot.liquid_handling.backends.tecan.EVO_backend") == "Tecan"

  def test_infer_unknown(self):
    """Test unknown manufacturer returns None."""
    assert infer_manufacturer("pylabrobot.some.unknown.module") is None

  def test_infer_vendor_hamilton(self):
    """Test Hamilton vendor inference."""
    assert infer_vendor("pylabrobot.resources.hamilton.plates") == "Hamilton"

  def test_infer_vendor_corning(self):
    """Test Corning vendor inference."""
    assert infer_vendor("pylabrobot.resources.corning.plates") == "Corning"

  def test_is_vendor_module(self):
    """Test vendor module detection."""
    assert is_vendor_module("pylabrobot.resources.hamilton.plates") is True
    assert is_vendor_module("pylabrobot.resources.base") is False


class TestPLRSourceParser:
  """Tests for the PLR source parser."""

  @pytest.fixture(scope="class")
  def parser(self):
    """Create a parser instance shared across all tests in this class."""
    plr_root = find_plr_source_root()
    return PLRSourceParser(plr_root)

  def test_find_plr_source_root(self):
    """Test that PLR source root can be found."""
    plr_root = find_plr_source_root()
    assert plr_root.exists()
    assert (plr_root / "pylabrobot").is_dir()

  def test_discover_machine_classes(self, parser):
    """Test machine class discovery."""
    machines = parser.discover_machine_classes()

    # Should find some machines
    assert len(machines) > 0

    # All should be non-abstract
    for m in machines:
      assert not m.is_abstract

    # All should be machine types (frontends or backends)
    all_machine_types = MACHINE_FRONTEND_TYPES | MACHINE_BACKEND_TYPES
    for m in machines:
      assert m.class_type in all_machine_types

  def test_discover_star_backend(self, parser):
    """Test that STARBackend is discovered with capabilities."""
    machines = parser.discover_machine_classes()

    star_backends = [m for m in machines if m.name == "STARBackend"]
    assert len(star_backends) == 1

    star = star_backends[0]
    assert star.manufacturer == "Hamilton"
    assert star.class_type == PLRClassType.LH_BACKEND
    # Should detect iswap capability
    assert star.capabilities.has_iswap or "swap" in star.capabilities.modules

  def test_discover_opentrons_backend(self, parser):
    """Test that Opentrons backend is discovered."""
    machines = parser.discover_machine_classes()

    ot_backends = [m for m in machines if "Opentrons" in m.name]
    assert len(ot_backends) >= 1

    ot = ot_backends[0]
    assert ot.manufacturer == "Opentrons"
    assert ot.class_type == PLRClassType.LH_BACKEND

  def test_discover_chatterbox_backend(self, parser):
    """Test that ChatterBox simulation backend is discovered."""
    machines = parser.discover_machine_classes()

    chatterbox = [m for m in machines if "chatterbox" in m.name.lower()]
    assert len(chatterbox) >= 1

  def test_discover_backend_classes(self, parser):
    """Test backend-only discovery."""
    backends = parser.discover_backend_classes()

    assert len(backends) > 0

    # All should be backend types
    for b in backends:
      assert b.class_type in MACHINE_BACKEND_TYPES

  def test_discover_resource_classes(self, parser):
    """Test resource class discovery."""
    resources = parser.discover_resource_classes()

    # Should find some resources
    assert len(resources) > 0

    # All should be non-abstract
    for r in resources:
      assert not r.is_abstract

  def test_discover_deck_classes(self, parser):
    """Test deck class discovery."""
    decks = parser.discover_deck_classes()

    # Should find some decks
    assert len(decks) > 0

    for d in decks:
      assert d.class_type == PLRClassType.DECK
      assert d.name != "Deck"  # Should not include base Deck class

  def test_caching(self, parser):
    """Test that results are cached."""
    # First call
    machines1 = parser.discover_machine_classes()

    # Second call should return same results from cache
    machines2 = parser.discover_machine_classes()

    assert len(machines1) == len(machines2)
    assert machines1 is machines2  # Should be same object

  def test_clear_cache(self, parser):
    """Test cache clearing."""
    # Populate cache
    machines1 = parser.discover_machine_classes()

    # Clear cache
    parser.clear_cache()

    # Should rediscover
    machines2 = parser.discover_machine_classes()

    assert len(machines1) == len(machines2)
    assert machines1 is not machines2  # Should be different objects


class TestDiscoveredClass:
  """Tests for DiscoveredClass model."""

  def test_to_capabilities_dict(self):
    """Test capabilities dict conversion."""
    from praxis.backend.utils.plr_static_analysis.models import DiscoveredCapabilities

    cls = DiscoveredClass(
      fqn="test.module.TestClass",
      name="TestClass",
      module_path="test.module",
      file_path="/test/path.py",
      class_type=PLRClassType.LH_BACKEND,
      capabilities=DiscoveredCapabilities(
        channels=[8, 96],
        modules=["swap", "hepa"],
        has_core96=True,
        has_iswap=True,
      ),
    )

    caps = cls.to_capabilities_dict()
    assert caps["channels"] == [8, 96]
    assert "swap" in caps["modules"]
    assert "hepa" in caps["modules"]
    assert caps["has_core96"] is True
    assert caps["has_iswap"] is True


class TestMachineCapabilitySchemas:
  """Tests for machine-type-specific capability schemas."""

  def test_liquid_handler_capabilities(self):
    """Test LiquidHandlerCapabilities model."""
    from praxis.backend.utils.plr_static_analysis.models import LiquidHandlerCapabilities

    caps = LiquidHandlerCapabilities(
      channels=[8, 96],
      has_iswap=True,
      has_core96=True,
      has_hepa=True,
    )
    assert caps.channels == [8, 96]
    assert caps.has_iswap is True
    assert caps.has_core96 is True
    assert caps.has_hepa is True

  def test_plate_reader_capabilities(self):
    """Test PlateReaderCapabilities model."""
    from praxis.backend.utils.plr_static_analysis.models import PlateReaderCapabilities

    caps = PlateReaderCapabilities(
      absorbance=True,
      fluorescence=True,
      luminescence=False,
      imaging=True,
    )
    assert caps.absorbance is True
    assert caps.fluorescence is True
    assert caps.luminescence is False
    assert caps.imaging is True

  def test_heater_shaker_capabilities(self):
    """Test HeaterShakerCapabilities model."""
    from praxis.backend.utils.plr_static_analysis.models import HeaterShakerCapabilities

    caps = HeaterShakerCapabilities(
      max_temperature_c=95.0,
      min_temperature_c=4.0,
      max_speed_rpm=2000,
      has_cooling=True,
    )
    assert caps.max_temperature_c == 95.0
    assert caps.min_temperature_c == 4.0
    assert caps.max_speed_rpm == 2000
    assert caps.has_cooling is True

  def test_centrifuge_capabilities(self):
    """Test CentrifugeCapabilities model."""
    from praxis.backend.utils.plr_static_analysis.models import CentrifugeCapabilities

    caps = CentrifugeCapabilities(
      max_rpm=15000,
      max_g=20000,
      temperature_controlled=True,
    )
    assert caps.max_rpm == 15000
    assert caps.max_g == 20000
    assert caps.temperature_controlled is True

  def test_pump_capabilities(self):
    """Test PumpCapabilities model."""
    from praxis.backend.utils.plr_static_analysis.models import PumpCapabilities

    caps = PumpCapabilities(
      max_flow_rate_ml_min=50.0,
      min_flow_rate_ml_min=0.1,
      reversible=True,
      num_channels=4,
    )
    assert caps.max_flow_rate_ml_min == 50.0
    assert caps.min_flow_rate_ml_min == 0.1
    assert caps.reversible is True
    assert caps.num_channels == 4

  def test_to_capabilities_dict_with_machine_caps(self):
    """Test that machine_capabilities are merged into to_capabilities_dict."""
    from praxis.backend.utils.plr_static_analysis.models import (
      DiscoveredCapabilities,
      HeaterShakerCapabilities,
    )

    cls = DiscoveredClass(
      fqn="test.module.TestHS",
      name="TestHS",
      module_path="test.module",
      file_path="/test/path.py",
      class_type=PLRClassType.HEATER_SHAKER,
      capabilities=DiscoveredCapabilities(),
      machine_capabilities=HeaterShakerCapabilities(
        max_temperature_c=100.0,
        max_speed_rpm=1500,
        has_cooling=True,
      ),
    )

    caps = cls.to_capabilities_dict()
    assert caps["max_temperature_c"] == 100.0
    assert caps["max_speed_rpm"] == 1500
    assert caps["has_cooling"] is True


class TestCapabilityExtraction:
  """Tests for type-specific capability extraction from PLR sources."""

  @pytest.fixture(scope="class")
  def parser(self):
    """Create a parser instance shared across all tests in this class."""
    plr_root = find_plr_source_root()
    return PLRSourceParser(plr_root, use_cache=False)

  def test_star_backend_has_machine_capabilities(self, parser):
    """Test that STARBackend gets type-specific machine capabilities."""
    from praxis.backend.utils.plr_static_analysis.models import LiquidHandlerCapabilities

    machines = parser.discover_machine_classes()
    star_backends = [m for m in machines if m.name == "STARBackend"]
    assert len(star_backends) == 1

    star = star_backends[0]
    assert star.machine_capabilities is not None
    assert isinstance(star.machine_capabilities, LiquidHandlerCapabilities)
    # STAR should have iswap capability detected from method names
    assert star.machine_capabilities.has_iswap or star.machine_capabilities.has_core96

  def test_heater_shaker_backend_capabilities(self, parser):
    """Test that HeaterShaker backends get type-specific capabilities."""
    machines = parser.discover_machine_classes()
    hs_backends = [m for m in machines if m.class_type == PLRClassType.HS_BACKEND]

    # Should find at least one heater shaker backend
    if len(hs_backends) > 0:
      hs = hs_backends[0]
      assert hs.machine_capabilities is not None


class TestCapabilityConfigTemplates:
  """Tests for capability configuration templates."""

  def test_get_liquid_handler_template(self):
    """Test getting liquid handler config template."""
    from praxis.backend.utils.plr_static_analysis.capability_config_templates import (
      get_config_template,
    )

    template = get_config_template(PLRClassType.LIQUID_HANDLER)
    assert template is not None
    assert template.machine_type == "liquid_handler"

    # Check expected fields exist
    field_names = [f.field_name for f in template.config_fields]
    assert "num_channels" in field_names
    assert "has_iswap" in field_names
    assert "has_core96" in field_names

  def test_get_plate_reader_template(self):
    """Test getting plate reader config template."""
    from praxis.backend.utils.plr_static_analysis.capability_config_templates import (
      get_config_template,
    )

    template = get_config_template(PLRClassType.PLATE_READER)
    assert template is not None
    assert template.machine_type == "plate_reader"

    field_names = [f.field_name for f in template.config_fields]
    assert "has_absorbance" in field_names
    assert "has_fluorescence" in field_names

  def test_backend_type_maps_to_frontend_template(self):
    """Test that backend types correctly map to frontend templates."""
    from praxis.backend.utils.plr_static_analysis.capability_config_templates import (
      get_config_template,
    )

    # LH_BACKEND should get LIQUID_HANDLER template
    template = get_config_template(PLRClassType.LH_BACKEND)
    assert template is not None
    assert template.machine_type == "liquid_handler"

  def test_no_template_for_resources(self):
    """Test that resources return None (no config template)."""
    from praxis.backend.utils.plr_static_analysis.capability_config_templates import (
      get_config_template,
    )

    template = get_config_template(PLRClassType.RESOURCE)
    assert template is None

  def test_parser_populates_capabilities_config(self):
    """Test that the parser populates capabilities_config on machine classes."""
    plr_root = find_plr_source_root()
    parser = PLRSourceParser(plr_root, use_cache=False)

    machines = parser.discover_machine_classes()
    # Find a liquid handler or backend
    lh_machines = [m for m in machines if m.class_type in (PLRClassType.LIQUID_HANDLER, PLRClassType.LH_BACKEND)]

    if lh_machines:
      lh = lh_machines[0]
      # Should have capabilities_config populated
      assert lh.capabilities_config is not None
      assert lh.capabilities_config.machine_type == "liquid_handler"


class TestProtocolFunctionVisitor:
  """Tests for ProtocolFunctionVisitor."""

  def test_basic_protocol_function(self):
    """Test extracting a basic protocol function."""
    from praxis.backend.utils.plr_static_analysis.visitors.protocol_discovery import (
      ProtocolFunctionVisitor,
    )

    source = """
@protocol_function
def my_protocol():
    '''Docstring.'''
    pass
"""
    tree = cst.parse_module(source.strip())
    visitor = ProtocolFunctionVisitor("test_module", "/path/to/file.py")
    tree.visit(visitor)

    assert len(visitor.definitions) == 1
    info = visitor.definitions[0]
    assert info.name == "my_protocol"
    assert info.docstring == "Docstring."
    assert len(info.parameters) == 0

  def test_protocol_with_parameters(self):
    """Test extracting parameters with defaults."""
    from praxis.backend.utils.plr_static_analysis.visitors.protocol_discovery import (
      ProtocolFunctionVisitor,
    )

    source = """
@protocol_function
def my_protocol(vol: float, name: str = "test"):
    pass
"""
    tree = cst.parse_module(source.strip())
    visitor = ProtocolFunctionVisitor("test_module", "/path/to/file.py")
    tree.visit(visitor)

    assert len(visitor.definitions) == 1
    info = visitor.definitions[0]
    assert len(info.parameters) == 2

    # Check regular param
    p1 = info.parameters[0]
    assert p1.name == "vol"
    assert p1.type_hint == "float"
    assert not p1.is_optional
    assert not p1.is_asset

    # Check default param
    p2 = info.parameters[1]
    assert p2.name == "name"
    assert p2.type_hint == "str"
    assert p2.is_optional
    # Note: LibCST preserves quotes in source representation
    assert '"test"' in p2.default_value or "'test'" in p2.default_value

  def test_protocol_with_assets(self):
    """Test extracting PLR asset parameters."""
    from praxis.backend.utils.plr_static_analysis.visitors.protocol_discovery import (
      ProtocolFunctionVisitor,
    )

    source = """
@protocol_function
def my_protocol(plate: Plate, tips: TipRack):
    pass
"""
    tree = cst.parse_module(source.strip())
    visitor = ProtocolFunctionVisitor("test_module", "/path/to/file.py")
    tree.visit(visitor)

    assert len(visitor.definitions) == 1
    info = visitor.definitions[0]
    assert len(info.parameters) == 2

    # Check assets
    p1 = info.parameters[0]
    assert p1.name == "plate"
    assert p1.is_asset
    assert p1.asset_type == "Plate"

    p2 = info.parameters[1]
    assert p2.name == "tips"
    assert p2.is_asset
    assert p2.asset_type == "TipRack"

  def test_protocol_with_index_selector(self):
    """Test detecting Well/TipSpot parameters for index selection."""
    from praxis.backend.utils.plr_static_analysis.visitors.protocol_discovery import (
      ProtocolFunctionVisitor,
    )

    source = """
@protocol_function
def my_protocol(
    start_well: Well, 
    dest_wells: list[Well], 
    tips: Sequence[TipSpot],
    other: str
):
    pass
"""
    tree = cst.parse_module(source.strip())
    visitor = ProtocolFunctionVisitor("test_module", "/path/to/file.py")
    tree.visit(visitor)

    assert len(visitor.definitions) == 1
    info = visitor.definitions[0]

    # Check start_well (Single Well)
    p1 = info.parameters[0]
    assert p1.name == "start_well"
    assert p1.field_type == "index_selector"
    assert p1.is_itemized is True
    assert p1.itemized_spec["items_x"] == 12

    # Check dest_wells (list[Well])
    p2 = info.parameters[1]
    assert p2.name == "dest_wells"
    assert p2.field_type == "index_selector"
    assert p2.is_itemized is True

    # Check tips (Sequence[TipSpot])
    p3 = info.parameters[2]
    assert p3.name == "tips"
    assert p3.field_type == "index_selector"
    assert p3.is_itemized is True

    # Check other (str)
    p4 = info.parameters[3]
    assert p4.name == "other"
    assert p4.field_type is None

  def test_protocol_with_tuple_well(self):
    """Test detecting tuple[Well, ...] types."""
    from praxis.backend.utils.plr_static_analysis.visitors.protocol_discovery import (
      ProtocolFunctionVisitor,
    )

    source = """
@protocol_function
def my_protocol(wells: tuple[Well, ...]):
    pass
"""
    tree = cst.parse_module(source.strip())
    visitor = ProtocolFunctionVisitor("test_module", "/path/to/file.py")
    tree.visit(visitor)

    assert len(visitor.definitions) == 1
    info = visitor.definitions[0]

    p1 = info.parameters[0]
    assert p1.name == "wells"
    assert p1.field_type == "index_selector"
    assert p1.is_itemized is True

  def test_protocol_with_optional_well(self):
    """Test detecting Optional[Well] types."""
    from praxis.backend.utils.plr_static_analysis.visitors.protocol_discovery import (
      ProtocolFunctionVisitor,
    )

    source = """
@protocol_function
def my_protocol(well: Optional[Well]):
    pass
"""
    tree = cst.parse_module(source.strip())
    visitor = ProtocolFunctionVisitor("test_module", "/path/to/file.py")
    tree.visit(visitor)

    assert len(visitor.definitions) == 1
    info = visitor.definitions[0]

    p1 = info.parameters[0]
    assert p1.name == "well"
    assert p1.field_type == "index_selector"
    assert p1.is_itemized is True

  def test_protocol_with_union_syntax(self):
    """Test detecting Well | None (Python 3.10+ union syntax)."""
    from praxis.backend.utils.plr_static_analysis.visitors.protocol_discovery import (
      ProtocolFunctionVisitor,
    )

    source = """
@protocol_function
def my_protocol(well: Well | None):
    pass
"""
    tree = cst.parse_module(source.strip())
    visitor = ProtocolFunctionVisitor("test_module", "/path/to/file.py")
    tree.visit(visitor)

    assert len(visitor.definitions) == 1
    info = visitor.definitions[0]

    p1 = info.parameters[0]
    assert p1.name == "well"
    assert p1.field_type == "index_selector"
    assert p1.is_itemized is True


class TestTypeAnnotationAnalyzer:
  """Tests for the TypeAnnotationAnalyzer utility."""

  def test_analyze_simple_well(self):
    """Test detecting simple Well type."""
    from praxis.backend.utils.plr_static_analysis.type_annotation_analyzer import (
      analyze_type_hint_string,
    )

    result = analyze_type_hint_string("Well")
    assert result is not None
    assert result.element_type == "Well"
    assert result.is_container is False

  def test_analyze_list_well(self):
    """Test detecting list[Well] type."""
    from praxis.backend.utils.plr_static_analysis.type_annotation_analyzer import (
      analyze_type_hint_string,
    )

    result = analyze_type_hint_string("list[Well]")
    assert result is not None
    assert result.element_type == "Well"
    assert result.is_container is True

  def test_analyze_sequence_tipspot(self):
    """Test detecting Sequence[TipSpot] type."""
    from praxis.backend.utils.plr_static_analysis.type_annotation_analyzer import (
      analyze_type_hint_string,
    )

    result = analyze_type_hint_string("Sequence[TipSpot]")
    assert result is not None
    assert result.element_type == "TipSpot"
    assert result.is_container is True

  def test_analyze_non_itemized_type(self):
    """Test that non-itemized types return None."""
    from praxis.backend.utils.plr_static_analysis.type_annotation_analyzer import (
      analyze_type_hint_string,
    )

    result = analyze_type_hint_string("str")
    assert result is None

    result = analyze_type_hint_string("int")
    assert result is None

    result = analyze_type_hint_string("Plate")
    assert result is None

  def test_ansi_sbs_dimensions(self):
    """Test ANSI/SBS plate dimension constants."""
    from praxis.backend.utils.plr_static_analysis.type_annotation_analyzer import (
      get_standard_dimensions,
    )

    # 96-well plate
    x, y = get_standard_dimensions(96)
    assert x == 12
    assert y == 8

    # 384-well plate
    x, y = get_standard_dimensions(384)
    assert x == 24
    assert y == 16

    # Default (None)
    x, y = get_standard_dimensions()
    assert x == 12
    assert y == 8

    # Unknown returns default
    x, y = get_standard_dimensions(999)
    assert x == 12
    assert y == 8

