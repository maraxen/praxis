"""Tests for core/workcell.py."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pylabrobot.legacy.machines.machine import Machine
from pylabrobot.resources import Deck, Resource

from praxis.backend.core.filesystem import FileSystem
from praxis.backend.core.workcell import Workcell, WorkcellView
from praxis.backend.models import AssetRequirementModel
from praxis.backend.utils.uuid import uuid7


class TestWorkcellInit:

    """Tests for Workcell initialization."""

    def test_workcell_init_with_valid_json_file(self, tmp_path: Path) -> None:
        """Test that Workcell initializes with valid JSON file."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()

        workcell = Workcell(
            name="test_workcell",
            save_file=save_file,
            file_system=fs,
        )

        assert workcell.name == "test_workcell"
        assert workcell.save_file == save_file
        assert workcell.fs is fs

    def test_workcell_init_with_invalid_file_extension_raises(self) -> None:
        """Test that Workcell raises ValueError for non-JSON save_file."""
        fs = FileSystem()

        with pytest.raises(ValueError, match="save_file must be a JSON file ending in .json"):
            Workcell(
                name="test_workcell",
                save_file="/path/to/state.txt",
                file_system=fs,
            )

    def test_workcell_init_sets_default_parameters(self, tmp_path: Path) -> None:
        """Test that Workcell sets default backup parameters."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()

        workcell = Workcell(
            name="test_workcell",
            save_file=save_file,
            file_system=fs,
        )

        assert workcell.backup_interval == 60
        assert workcell.num_backups == 3
        assert workcell.backup_num == 0

    def test_workcell_init_with_custom_backup_parameters(self, tmp_path: Path) -> None:
        """Test that Workcell accepts custom backup parameters."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()

        workcell = Workcell(
            name="test_workcell",
            save_file=save_file,
            file_system=fs,
            backup_interval=120,
            num_backups=5,
        )

        assert workcell.backup_interval == 120
        assert workcell.num_backups == 5

    def test_workcell_init_creates_empty_refs_and_children(self, tmp_path: Path) -> None:
        """Test that Workcell initializes empty refs and children."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()

        workcell = Workcell(
            name="test_workcell",
            save_file=save_file,
            file_system=fs,
        )

        assert isinstance(workcell.refs, dict)
        assert isinstance(workcell.children, list)
        assert len(workcell.children) == 0


class TestWorkcellDynamicAttributes:

    """Tests for Workcell dynamic attribute creation."""

    def test_workcell_creates_machine_category_attributes(self, tmp_path: Path) -> None:
        """Test that Workcell creates attributes for machine categories."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()

        workcell = Workcell(
            name="test_workcell",
            save_file=save_file,
            file_system=fs,
        )

        # Check that liquid_handlers exists (MachineCategoryEnum.LIQUID_HANDLER)
        assert hasattr(workcell, "liquid_handlers")
        assert isinstance(workcell.liquid_handlers, dict)
        assert "liquid_handlers" in workcell.refs

    def test_workcell_creates_resource_category_attributes(self, tmp_path: Path) -> None:
        """Test that Workcell creates attributes for resource categories."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()

        workcell = Workcell(
            name="test_workcell",
            save_file=save_file,
            file_system=fs,
        )

        # Check that plates exists (ResourceCategoryEnum.PLATE)
        assert hasattr(workcell, "plates")
        assert isinstance(workcell.plates, dict)
        assert "plates" in workcell.refs

    def test_workcell_creates_other_machines_attribute(self, tmp_path: Path) -> None:
        """Test that Workcell always has other_machines attribute."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()

        workcell = Workcell(
            name="test_workcell",
            save_file=save_file,
            file_system=fs,
        )

        assert hasattr(workcell, "other_machines")
        assert isinstance(workcell.other_machines, dict)
        assert "other_machines" in workcell.refs


class TestWorkcellAllMachines:

    """Tests for Workcell.all_machines property."""

    def test_all_machines_returns_empty_dict_initially(self, tmp_path: Path) -> None:
        """Test that all_machines returns empty dict when no machines added."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        result = workcell.all_machines
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_all_machines_includes_machines_from_all_categories(self, tmp_path: Path) -> None:
        """Test that all_machines aggregates machines from all categories."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        # Add mock machines to different categories
        mock_machine1 = Mock(spec=Machine)
        mock_machine1.name = "machine1"
        mock_machine2 = Mock(spec=Machine)
        mock_machine2.name = "machine2"

        workcell.refs["liquid_handlers"]["lh1"] = mock_machine1
        workcell.refs["other_machines"]["other1"] = mock_machine2

        result = workcell.all_machines
        assert len(result) == 2
        assert "lh1" in result
        assert "other1" in result


class TestWorkcellAssetKeys:

    """Tests for Workcell.asset_keys property."""

    def test_asset_keys_returns_empty_list_initially(self, tmp_path: Path) -> None:
        """Test that asset_keys returns empty list when no assets added."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        result = workcell.asset_keys
        assert isinstance(result, list)
        assert len(result) == 0

    def test_asset_keys_returns_asset_names(self, tmp_path: Path) -> None:
        """Test that asset_keys returns list of asset names."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_asset1 = Mock()
        mock_asset1.name = "asset1"
        mock_asset2 = Mock()
        mock_asset2.name = "asset2"

        workcell.children = [mock_asset1, mock_asset2]

        result = workcell.asset_keys
        assert "asset1" in result
        assert "asset2" in result
        assert len(result) == 2


class TestWorkcellAddAsset:

    """Tests for Workcell.add_asset() method."""

    def test_add_asset_appends_to_children(self, tmp_path: Path) -> None:
        """Test that add_asset appends asset to children list."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_asset = Mock(spec=Resource)
        mock_asset.name = "test_asset"
        mock_asset.category = "plate"

        workcell.add_asset(mock_asset)

        assert len(workcell.children) == 1
        assert workcell.children[0] is mock_asset

    def test_add_asset_adds_to_correct_category(self, tmp_path: Path) -> None:
        """Test that add_asset adds asset to correct category dict."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_asset = Mock(spec=Resource)
        mock_asset.name = "test_plate"
        mock_asset.category = "plate"

        workcell.add_asset(mock_asset)

        assert "test_plate" in workcell.plates
        assert workcell.plates["test_plate"] is mock_asset

    def test_add_asset_with_no_category_logs_warning(self, tmp_path: Path) -> None:
        """Test that add_asset logs warning for asset without category."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_asset = Mock(spec=Resource)
        mock_asset.name = "test_asset"
        mock_asset.category = None

        with patch("praxis.backend.core.workcell.logger.warning") as mock_logger:
            workcell.add_asset(mock_asset)
            mock_logger.assert_called_once()


class TestWorkcellGetAllChildren:

    """Tests for Workcell.get_all_children() method."""

    def test_get_all_children_returns_empty_list_initially(self, tmp_path: Path) -> None:
        """Test that get_all_children returns empty list when no children."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        result = workcell.get_all_children()
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_all_children_returns_direct_children(self, tmp_path: Path) -> None:
        """Test that get_all_children returns direct children."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_asset = Mock(spec=Machine)
        workcell.children.append(mock_asset)

        result = workcell.get_all_children()
        assert len(result) == 1
        assert mock_asset in result

    def test_get_all_children_recursively_gets_resource_children(
        self, tmp_path: Path,
    ) -> None:
        """Test that get_all_children recursively gets children of Resources."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        # Create mock resource with nested children
        mock_child = Mock(spec=Resource)
        mock_resource = Mock(spec=Resource)
        mock_resource.get_all_children.return_value = [mock_child]

        workcell.children.append(mock_resource)

        result = workcell.get_all_children()
        assert mock_resource in result
        assert mock_child in result
        assert len(result) == 2


class TestWorkcellSpecifyDeck:

    """Tests for Workcell.specify_deck() method."""

    def test_specify_deck_assigns_deck_to_liquid_handler(self, tmp_path: Path) -> None:
        """Test that specify_deck assigns deck to liquid handler."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_lh = Mock()
        mock_deck = Mock(spec=Deck)

        workcell.refs["liquid_handlers"]["lh1"] = mock_lh

        workcell.specify_deck("lh1", mock_deck)

        assert mock_lh.deck is mock_deck

    def test_specify_deck_raises_keyerror_for_nonexistent_lh(self, tmp_path: Path) -> None:
        """Test that specify_deck raises KeyError for nonexistent liquid handler."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_deck = Mock(spec=Deck)

        with pytest.raises(KeyError, match="Liquid handler 'nonexistent' not found"):
            workcell.specify_deck("nonexistent", mock_deck)


class TestWorkcellStateSerialization:

    """Tests for Workcell state serialization methods."""

    def test_serialize_all_state_returns_empty_dict_initially(self, tmp_path: Path) -> None:
        """Test that serialize_all_state returns empty dict with no resources."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        result = workcell.serialize_all_state()
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_serialize_all_state_serializes_resources(self, tmp_path: Path) -> None:
        """Test that serialize_all_state serializes Resource states."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_resource = Mock(spec=Resource)
        mock_resource.name = "resource1"
        mock_resource.get_all_children.return_value = []
        mock_resource.serialize_state.return_value = {"state": "data"}

        workcell.children.append(mock_resource)

        result = workcell.serialize_all_state()
        assert "resource1" in result
        assert result["resource1"] == {"state": "data"}
        mock_resource.serialize_state.assert_called_once()

    def test_load_all_state_loads_resource_states(self, tmp_path: Path) -> None:
        """Test that load_all_state loads states for Resources."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_resource = Mock(spec=Resource)
        mock_resource.name = "resource1"
        mock_resource.get_all_children.return_value = []

        workcell.children.append(mock_resource)

        state_data = {"resource1": {"state": "data"}}
        workcell.load_all_state(state_data)

        mock_resource.load_state.assert_called_once_with({"state": "data"})

    def test_load_all_state_skips_missing_resources(self, tmp_path: Path) -> None:
        """Test that load_all_state skips resources not in state dict."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_resource = Mock(spec=Resource)
        mock_resource.name = "resource1"
        mock_resource.get_all_children.return_value = []

        workcell.children.append(mock_resource)

        state_data = {"other_resource": {"state": "data"}}
        workcell.load_all_state(state_data)

        # Should not call load_state since resource1 not in state_data
        mock_resource.load_state.assert_not_called()


class TestWorkcellStateFiles:

    """Tests for Workcell file save/load methods."""

    def test_save_state_to_file_writes_json(self, tmp_path: Path) -> None:
        """Test that save_state_to_file writes serialized state to file."""
        save_file = str(tmp_path / "state.json")
        output_file = str(tmp_path / "output.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_resource = Mock(spec=Resource)
        mock_resource.name = "resource1"
        mock_resource.get_all_children.return_value = []
        mock_resource.serialize_state.return_value = {"key": "value"}

        workcell.children.append(mock_resource)

        workcell.save_state_to_file(output_file)

        # Verify file was written
        assert Path(output_file).exists()

        # Verify content
        with open(output_file) as f:
            data = json.load(f)
        assert data == {"resource1": {"key": "value"}}

    def test_load_state_from_file_reads_json(self, tmp_path: Path) -> None:
        """Test that load_state_from_file reads and loads state from file."""
        save_file = str(tmp_path / "state.json")
        input_file = str(tmp_path / "input.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        # Create input file
        state_data = {"resource1": {"key": "value"}}
        with open(input_file, "w") as f:
            json.dump(state_data, f)

        mock_resource = Mock(spec=Resource)
        mock_resource.name = "resource1"
        mock_resource.get_all_children.return_value = []

        workcell.children.append(mock_resource)

        workcell.load_state_from_file(input_file)

        mock_resource.load_state.assert_called_once_with({"key": "value"})


class TestWorkcellSpecialMethods:

    """Tests for Workcell special methods."""

    def test_contains_returns_true_for_existing_asset(self, tmp_path: Path) -> None:
        """Test that __contains__ returns True for existing asset."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_asset = Mock()
        mock_asset.name = "test_asset"
        workcell.children.append(mock_asset)

        assert "test_asset" in workcell

    def test_contains_returns_false_for_nonexistent_asset(self, tmp_path: Path) -> None:
        """Test that __contains__ returns False for nonexistent asset."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        assert "nonexistent" not in workcell

    def test_getitem_returns_category_dict(self, tmp_path: Path) -> None:
        """Test that __getitem__ returns the refs dict for valid category."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        result = workcell["plates"]
        assert result is workcell.refs["plates"]

    def test_getitem_raises_keyerror_for_invalid_category(self, tmp_path: Path) -> None:
        """Test that __getitem__ raises KeyError for invalid category."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        with pytest.raises(KeyError, match="'invalid' is not a valid asset category"):
            _ = workcell["invalid"]


class TestWorkcellViewInit:

    """Tests for WorkcellView initialization."""

    def test_workcell_view_init(self, tmp_path: Path) -> None:
        """Test that WorkcellView initializes correctly."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        required_assets = [
            AssetRequirementModel(
                accession_id=uuid7(),
                name="asset1",
                fqn="test.asset1",
                type_hint_str="Plate",
            ),
            AssetRequirementModel(
                accession_id=uuid7(),
                name="asset2",
                fqn="test.asset2",
                type_hint_str="Plate",
            ),
        ]

        view = WorkcellView(workcell, "test_protocol", required_assets)

        assert view.parent is workcell
        assert view.protocol_name == "test_protocol"
        assert "asset1" in view._required_asset_names
        assert "asset2" in view._required_asset_names

    def test_workcell_view_extracts_asset_names(self, tmp_path: Path) -> None:
        """Test that WorkcellView extracts asset names from requirements."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        required_assets = [
            AssetRequirementModel(
                accession_id=uuid7(),
                name="test_asset",
                fqn="test.test_asset",
                type_hint_str="Plate",
            ),
        ]

        view = WorkcellView(workcell, "protocol", required_assets)

        assert len(view._required_asset_names) == 1
        assert "test_asset" in view._required_asset_names


class TestWorkcellViewContains:

    """Tests for WorkcellView.__contains__() method."""

    def test_contains_returns_true_for_required_asset(self, tmp_path: Path) -> None:
        """Test that __contains__ returns True for required asset."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        required_assets = [
            AssetRequirementModel(
                accession_id=uuid7(),
                name="asset1",
                fqn="test.asset1",
                type_hint_str="Plate",
            ),
        ]
        view = WorkcellView(workcell, "protocol", required_assets)

        assert "asset1" in view

    def test_contains_returns_false_for_non_required_asset(self, tmp_path: Path) -> None:
        """Test that __contains__ returns False for non-required asset."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        required_assets = [
            AssetRequirementModel(
                accession_id=uuid7(),
                name="asset1",
                fqn="test.asset1",
                type_hint_str="Plate",
            ),
        ]
        view = WorkcellView(workcell, "protocol", required_assets)

        assert "other_asset" not in view


class TestWorkcellViewGetAttr:

    """Tests for WorkcellView.__getattr__() method."""

    def test_getattr_allows_access_to_required_asset(self, tmp_path: Path) -> None:
        """Test that __getattr__ allows access to required assets."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        mock_asset = Mock()
        workcell.test_asset = mock_asset

        required_assets = [
            AssetRequirementModel(
                accession_id=uuid7(),
                name="test_asset",
                fqn="test.test_asset",
                type_hint_str="Plate",
            ),
        ]
        view = WorkcellView(workcell, "protocol", required_assets)

        result = view.test_asset
        assert result is mock_asset

    def test_getattr_raises_attributeerror_for_non_required_asset(
        self, tmp_path: Path,
    ) -> None:
        """Test that __getattr__ raises AttributeError for non-required assets."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        required_assets = [
            AssetRequirementModel(
                accession_id=uuid7(),
                name="asset1",
                fqn="test.asset1",
                type_hint_str="Plate",
            ),
        ]
        view = WorkcellView(workcell, "protocol", required_assets)

        with pytest.raises(
            AttributeError,
            match="Protocol 'protocol' attempted to access asset 'other_asset'",
        ):
            _ = view.other_asset

    def test_getattr_allows_access_to_private_attributes(self, tmp_path: Path) -> None:
        """Test that __getattr__ allows access to private view attributes."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        required_assets = []
        view = WorkcellView(workcell, "protocol", required_assets)

        # Access private attribute directly
        result = view._required_asset_names
        assert isinstance(result, set)


class TestWorkcellIntegration:

    """Integration tests for Workcell and WorkcellView."""

    def test_complete_workcell_workflow(self, tmp_path: Path) -> None:
        """Test complete workflow: add assets, serialize, save, load."""
        save_file = str(tmp_path / "state.json")
        output_file = str(tmp_path / "output.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        # Add mock resource
        mock_resource = Mock(spec=Resource)
        mock_resource.name = "test_resource"
        mock_resource.category = "plate"
        mock_resource.get_all_children.return_value = []
        mock_resource.serialize_state.return_value = {"test": "data"}

        workcell.add_asset(mock_resource)

        # Verify asset was added
        assert "test_resource" in workcell
        assert "test_resource" in workcell.plates

        # Save state
        workcell.save_state_to_file(output_file)

        # Create new workcell and load state
        workcell2 = Workcell(name="test_workcell2", save_file=save_file, file_system=fs)
        mock_resource2 = Mock(spec=Resource)
        mock_resource2.name = "test_resource"
        mock_resource2.get_all_children.return_value = []
        workcell2.children.append(mock_resource2)

        workcell2.load_state_from_file(output_file)

        # Verify state was loaded
        mock_resource2.load_state.assert_called_once_with({"test": "data"})

    def test_workcell_view_security(self, tmp_path: Path) -> None:
        """Test that WorkcellView enforces asset access restrictions."""
        save_file = str(tmp_path / "state.json")
        fs = FileSystem()
        workcell = Workcell(name="test_workcell", save_file=save_file, file_system=fs)

        # Add assets to workcell
        workcell.allowed_asset = Mock()
        workcell.forbidden_asset = Mock()

        # Create view with limited access
        required_assets = [
            AssetRequirementModel(
                accession_id=uuid7(),
                name="allowed_asset",
                fqn="test.allowed_asset",
                type_hint_str="Plate",
            ),
        ]
        view = WorkcellView(workcell, "secure_protocol", required_assets)

        # Should allow access to declared asset
        result = view.allowed_asset
        assert result is workcell.allowed_asset

        # Should deny access to undeclared asset
        with pytest.raises(AttributeError, match="did not declare it as a requirement"):
            _ = view.forbidden_asset
