"""Unit tests for state transformation utilities.

Tests the transformation of PyLabRobot state format to frontend StateSnapshot format.
"""


from praxis.backend.core.state_transform import (
    _infer_parent_name,
    _infer_well_id,
    extract_liquid_volumes,
    extract_tip_state,
    get_on_deck_resources,
    transform_plr_state,
)


class TestExtractTipState:
    """Tests for extract_tip_state function."""

    def test_no_liquid_handler(self):
        """No liquid handler in state returns no tips loaded."""
        plr_state = {
            "tip_rack_1": {"tip": None},
            "source_plate": {"volume": 100.0},
        }
        result = extract_tip_state(plr_state)
        assert result == {"tips_loaded": False, "tips_count": 0}

    def test_liquid_handler_no_tips_loaded(self):
        """Liquid handler with no tips returns tips_loaded=False."""
        plr_state = {
            "liquid_handler": {
                "head_state": {
                    "0": {"tip": None, "tip_state": None, "pending_tip": None},
                    "1": {"tip": None, "tip_state": None, "pending_tip": None},
                }
            }
        }
        result = extract_tip_state(plr_state)
        assert result == {"tips_loaded": False, "tips_count": 0}

    def test_liquid_handler_with_tips_loaded(self):
        """Liquid handler with tips returns correct count."""
        plr_state = {
            "liquid_handler": {
                "head_state": {
                    "0": {"tip": {"name": "tip_0"}, "tip_state": {}, "pending_tip": None},
                    "1": {"tip": {"name": "tip_1"}, "tip_state": {}, "pending_tip": None},
                    "2": {"tip": None, "tip_state": None, "pending_tip": None},
                    "3": {"tip": {"name": "tip_3"}, "tip_state": {}, "pending_tip": None},
                }
            }
        }
        result = extract_tip_state(plr_state)
        assert result == {"tips_loaded": True, "tips_count": 3}

    def test_liquid_handler_all_tips_loaded(self):
        """Liquid handler with all 8 tips loaded."""
        plr_state = {
            "liquid_handler": {
                "head_state": {
                    str(i): {"tip": {"name": f"tip_{i}"}, "tip_state": {}}
                    for i in range(8)
                }
            }
        }
        result = extract_tip_state(plr_state)
        assert result == {"tips_loaded": True, "tips_count": 8}

    def test_empty_state(self):
        """Empty state returns no tips loaded."""
        result = extract_tip_state({})
        assert result == {"tips_loaded": False, "tips_count": 0}

    def test_invalid_head_state_type(self):
        """Non-dict head_state is handled gracefully."""
        plr_state = {
            "liquid_handler": {
                "head_state": "invalid"
            }
        }
        result = extract_tip_state(plr_state)
        assert result == {"tips_loaded": False, "tips_count": 0}


class TestExtractLiquidVolumes:
    """Tests for extract_liquid_volumes function."""

    def test_no_volumes(self):
        """State with no volume data returns empty dict."""
        plr_state = {
            "liquid_handler": {"head_state": {}},
            "tip_rack": {"tip": None},
        }
        result = extract_liquid_volumes(plr_state)
        assert result == {}

    def test_single_well_with_volume(self):
        """Single well with volume is extracted correctly."""
        plr_state = {
            "source_plate_A1": {
                "volume": 250.0,
                "pending_volume": 250.0,
                "thing": "source_plate_A1",
                "max_volume": 350.0,
            }
        }
        result = extract_liquid_volumes(plr_state)
        assert result == {"source_plate": {"A1": 250.0}}

    def test_multiple_wells_same_plate(self):
        """Multiple wells from same plate are grouped."""
        plr_state = {
            "source_plate_A1": {"volume": 250.0, "pending_volume": 250.0, "thing": "source_plate_A1", "max_volume": 350.0},
            "source_plate_A2": {"volume": 100.0, "pending_volume": 100.0, "thing": "source_plate_A2", "max_volume": 350.0},
            "source_plate_B1": {"volume": 50.0, "pending_volume": 50.0, "thing": "source_plate_B1", "max_volume": 350.0},
        }
        result = extract_liquid_volumes(plr_state)
        assert result == {
            "source_plate": {"A1": 250.0, "A2": 100.0, "B1": 50.0}
        }

    def test_multiple_plates(self):
        """Wells from different plates are separated."""
        plr_state = {
            "source_plate_A1": {"volume": 250.0, "pending_volume": 250.0, "thing": "source_plate_A1", "max_volume": 350.0},
            "dest_plate_A1": {"volume": 100.0, "pending_volume": 100.0, "thing": "dest_plate_A1", "max_volume": 350.0},
        }
        result = extract_liquid_volumes(plr_state)
        assert result == {
            "source_plate": {"A1": 250.0},
            "dest_plate": {"A1": 100.0},
        }

    def test_zero_volume_excluded(self):
        """Wells with zero volume are not included."""
        plr_state = {
            "source_plate_A1": {"volume": 0.0, "pending_volume": 0.0, "thing": "source_plate_A1", "max_volume": 350.0},
            "source_plate_A2": {"volume": 100.0, "pending_volume": 100.0, "thing": "source_plate_A2", "max_volume": 350.0},
        }
        result = extract_liquid_volumes(plr_state)
        assert result == {"source_plate": {"A2": 100.0}}

    def test_mixed_resource_types(self):
        """Only volume-containing resources are extracted."""
        plr_state = {
            "liquid_handler": {"head_state": {}},
            "tip_rack_1": {"tip": None},
            "source_plate_A1": {"volume": 250.0, "pending_volume": 250.0, "thing": "source_plate_A1", "max_volume": 350.0},
        }
        result = extract_liquid_volumes(plr_state)
        assert result == {"source_plate": {"A1": 250.0}}


class TestInferParentName:
    """Tests for _infer_parent_name helper."""

    def test_standard_pattern(self):
        """Standard plate_well pattern is parsed correctly."""
        assert _infer_parent_name("source_plate_A1") == "source_plate"
        assert _infer_parent_name("dest_plate_B12") == "dest_plate"

    def test_with_well_suffix(self):
        """Pattern with _well_ is handled."""
        assert _infer_parent_name("source_plate_well_A1") == "source_plate"

    def test_standalone_well_id(self):
        """Standalone well ID returns unknown_plate."""
        assert _infer_parent_name("A1") == "unknown_plate"
        assert _infer_parent_name("H12") == "unknown_plate"

    def test_no_pattern_match(self):
        """No pattern match returns full name."""
        assert _infer_parent_name("liquid_handler") == "liquid_handler"
        assert _infer_parent_name("tip_rack") == "tip_rack"

    def test_384_well_plate(self):
        """384-well plate identifiers are handled."""
        assert _infer_parent_name("plate_384_P24") == "plate_384"


class TestInferWellId:
    """Tests for _infer_well_id helper."""

    def test_extracts_well_id(self):
        """Well ID is extracted from end of name."""
        assert _infer_well_id("source_plate_A1") == "A1"
        assert _infer_well_id("dest_plate_B12") == "B12"

    def test_uppercase_result(self):
        """Result is always uppercase."""
        assert _infer_well_id("plate_a1") == "A1"

    def test_no_well_id(self):
        """No well ID returns full name."""
        assert _infer_well_id("liquid_handler") == "liquid_handler"

    def test_384_well_ids(self):
        """384-well plate identifiers are handled."""
        assert _infer_well_id("plate_P24") == "P24"


class TestGetOnDeckResources:
    """Tests for get_on_deck_resources function."""

    def test_returns_all_keys(self):
        """All resource names are returned."""
        plr_state = {
            "liquid_handler": {},
            "tip_rack_1": {},
            "source_plate": {},
        }
        result = get_on_deck_resources(plr_state)
        assert set(result) == {"liquid_handler", "tip_rack_1", "source_plate"}

    def test_empty_state(self):
        """Empty state returns empty list."""
        assert get_on_deck_resources({}) == []


class TestTransformPlrState:
    """Tests for transform_plr_state main function."""

    def test_none_input(self):
        """None input returns None."""
        assert transform_plr_state(None) is None

    def test_empty_dict(self):
        """Empty dict returns None (falsy)."""
        assert transform_plr_state({}) is None

    def test_full_transformation(self):
        """Full state is transformed correctly."""
        plr_state = {
            "liquid_handler": {
                "head_state": {
                    "0": {"tip": {"name": "tip_0"}, "tip_state": {}},
                    "1": {"tip": None, "tip_state": None},
                }
            },
            "source_plate_A1": {"volume": 250.0, "pending_volume": 250.0, "thing": "source_plate_A1", "max_volume": 350.0},
            "tip_rack_1": {"tip": None},
        }

        result = transform_plr_state(plr_state)

        assert result is not None
        assert result["tips"] == {"tips_loaded": True, "tips_count": 1}
        assert result["liquids"] == {"source_plate": {"A1": 250.0}}
        assert set(result["on_deck"]) == {"liquid_handler", "source_plate_A1", "tip_rack_1"}
        assert result["raw_plr_state"] == plr_state

    def test_preserves_raw_state(self):
        """Original PLR state is preserved in raw_plr_state."""
        plr_state = {"some_resource": {"data": "value"}}
        result = transform_plr_state(plr_state)

        assert result is not None
        assert result["raw_plr_state"] is plr_state
