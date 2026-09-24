
import json
from unittest.mock import MagicMock, patch

import pytest

from praxis.backend.core.deck_config import (
    DeckLayoutConfig,
    build_deck_from_config,
    load_deck_layout,
    validate_deck_layout_config,
)

# Test Data
VALID_CONFIG_DICT = {
    "deck_fqn": "pylabrobot.resources.hamilton.HamiltonSTARDeck",
    "deck_kwargs": {"num_channels": 8},
    "placements": [
        {
            "resource_fqn": "pylabrobot.resources.corning.Cor_96_wellplate_360ul_Fb",
            "name": "plate_1",
            "slot": "1"
        },
        {
            "resource_fqn": "pylabrobot.resources.ver.Ver_96_wellplate_360ul_Fb",
            "name": "plate_2",
            "position": {"x": 100, "y": 100, "z": 0},
            "rotation": 90
        }
    ]
}

@pytest.fixture
def valid_config_file(tmp_path):
    config_path = tmp_path / "deck_config.json"
    with open(config_path, "w") as f:
        json.dump(VALID_CONFIG_DICT, f)
    return config_path

def test_load_deck_layout_valid(valid_config_file):
    config = load_deck_layout(valid_config_file)
    assert isinstance(config, DeckLayoutConfig)
    assert config.deck_fqn == VALID_CONFIG_DICT["deck_fqn"]
    assert len(config.placements) == 2
    assert config.placements[0].name == "plate_1"
    assert config.placements[1].position == {"x": 100, "y": 100, "z": 0}

def test_load_deck_layout_not_found():
    with pytest.raises(FileNotFoundError):
        load_deck_layout("non_existent_file.json")

def test_validate_deck_layout_config_valid():
    config = DeckLayoutConfig(**VALID_CONFIG_DICT)
    warnings = validate_deck_layout_config(config)
    assert len(warnings) == 0

def test_validate_deck_layout_config_duplicate_name():
    data = VALID_CONFIG_DICT.copy()
    data["placements"] = [
        {"resource_fqn": "res.A", "name": "plate_1"},
        {"resource_fqn": "res.B", "name": "plate_1"}
    ]
    config = DeckLayoutConfig(**data)
    warnings = validate_deck_layout_config(config)
    assert len(warnings) == 1
    assert "Duplicate resource name" in warnings[0]

def test_validate_deck_layout_config_missing_parent():
    data = VALID_CONFIG_DICT.copy()
    data["placements"] = [
        {"resource_fqn": "res.A", "name": "plate_1", "parent_name": "unknown_carrier"}
    ]
    config = DeckLayoutConfig(**data)
    warnings = validate_deck_layout_config(config)
    assert len(warnings) == 1
    assert "references undefined parent" in warnings[0]

@patch("praxis.backend.core.deck_config._import_class")
def test_build_deck_from_config(mock_import):
    # Setup Mocks
    MockDeckClass = MagicMock()
    MockResourceClass = MagicMock()
    MockDeckInstance = MagicMock()
    MockResourceInstance1 = MagicMock()
    MockResourceInstance2 = MagicMock()

    mock_import.side_effect = [MockDeckClass, MockResourceClass, MockResourceClass]
    MockDeckClass.return_value = MockDeckInstance
    MockResourceClass.side_effect = [MockResourceInstance1, MockResourceInstance2]

    # Run
    config = DeckLayoutConfig(**VALID_CONFIG_DICT)
    deck = build_deck_from_config(config)

    # Verify
    assert deck == MockDeckInstance
    MockDeckClass.assert_called_with(num_channels=8)

    # Check placement 1 (Slot)
    MockResourceInstance1.name = "plate_1" # Mock attribute usually set in init
    MockDeckInstance.assign_child_at_slot.assert_called()

    # Check placement 2 (Position + Rotation)
    MockResourceInstance2.name = "plate_2"
    MockDeckInstance.assign_child_resource.assert_called()
    MockResourceInstance2.rotate.assert_called_with(z=90)
