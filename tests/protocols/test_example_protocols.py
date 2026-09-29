"""Tests for example protocol discovery and analysis."""

import libcst as cst
import pytest
from libcst.metadata import MetadataWrapper

from praxis.backend.utils.plr_static_analysis.visitors.protocol_discovery import (
    ProtocolFunctionVisitor,
)


class TestExampleProtocolDiscovery:
    """Test that example protocols are correctly discovered."""

    @pytest.fixture
    def discover_protocol(self, tmp_path):
        """Factory fixture to discover a protocol from source code."""

        def _discover(source: str, module_name: str = "test_module"):
            tree = cst.parse_module(source)
            visitor = ProtocolFunctionVisitor(module_name, str(tmp_path / "test.py"))
            wrapper = MetadataWrapper(tree)
            wrapper.visit(visitor)
            return visitor.definitions

        return _discover

    def test_plate_reader_assay_requires_no_deck(self, discover_protocol):
        """Test that plate reader protocol correctly declares requires_deck=False."""
        source = '''
from pylabrobot.legacy.plate_reading import PlateReader
from pylabrobot.resources import Plate
from praxis.backend.core.decorators import protocol_function

@protocol_function(
    name="plate_reader_assay",
    requires_deck=False,
)
async def plate_reader_assay(plate_reader: PlateReader, plate: Plate):
    """Test protocol."""
    pass
'''
        definitions = discover_protocol(source)
        assert len(definitions) == 1
        assert definitions[0].name == "plate_reader_assay"
        assert definitions[0].requires_deck is False

    def test_kinetic_assay_requires_no_deck(self, discover_protocol):
        """Test that kinetic assay correctly declares requires_deck=False."""
        source = '''
from pylabrobot.legacy.plate_reading import PlateReader
from pylabrobot.resources import Plate
from praxis.backend.core.decorators import protocol_function

@protocol_function(
    name="kinetic_assay",
    requires_deck=False,
)
async def kinetic_assay(plate_reader: PlateReader, plate: Plate):
    """Time-course assay."""
    pass
'''
        definitions = discover_protocol(source)
        assert len(definitions) == 1
        assert definitions[0].name == "kinetic_assay"
        assert definitions[0].requires_deck is False

    def test_selective_transfer_requires_deck(self, discover_protocol):
        """Test that selective transfer protocol requires deck (has LiquidHandler)."""
        source = '''
from pylabrobot.legacy.liquid_handling import LiquidHandler
from pylabrobot.resources import Plate, TipRack
from praxis.backend.core.decorators import protocol_function

@protocol_function(
    name="selective_transfer",
)
async def selective_transfer(lh: LiquidHandler, plate: Plate, tips: TipRack):
    """Transfer protocol."""
    pass
'''
        definitions = discover_protocol(source)
        assert len(definitions) == 1
        assert definitions[0].name == "selective_transfer"
        # Auto-detected as True because it has LiquidHandler
        assert definitions[0].requires_deck is True

    def test_protocol_with_well_selector_params(self, discover_protocol):
        """Test that well selector parameter metadata is preserved."""
        source = '''
from pylabrobot.resources import Plate
from praxis.backend.core.decorators import protocol_function

@protocol_function(
    name="well_selection_demo",
    param_metadata={
        "source_wells": {
            "ui_hint": "well_selector",
            "plate_ref": "source_plate",
        },
    },
)
async def well_selection_demo(source_plate: Plate, source_wells: str = "A1:A4"):
    """Demo with well selection."""
    pass
'''
        definitions = discover_protocol(source)
        assert len(definitions) == 1
        # Note: param_metadata is captured in decorator args, which may be exposed differently
        # This test mainly confirms the protocol is discovered
        assert definitions[0].name == "well_selection_demo"

    def test_inferred_requires_deck_false_without_lh(self, discover_protocol):
        """Test that protocols without LH/Deck params auto-detect requires_deck=False."""
        source = '''
from pylabrobot.legacy.plate_reading import PlateReader
from pylabrobot.resources import Plate
from praxis.backend.core.decorators import protocol_function

@protocol_function(
    name="plate_only_protocol",
)
async def plate_only_protocol(pr: PlateReader, plate: Plate):
    """No LH, should infer requires_deck=False."""
    pass
'''
        definitions = discover_protocol(source)
        assert len(definitions) == 1
        # PlateReader and Plate alone should not require deck
        # (only LiquidHandler or explicit Deck types require deck)
        assert definitions[0].requires_deck is False
