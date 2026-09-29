"""Tests for core/workcell_runtime."""

from unittest.mock import AsyncMock, Mock

import pytest
from pylabrobot.resources import Coordinate, Deck, Resource

from praxis.backend.core.workcell_runtime import WorkcellRuntime
from praxis.backend.core.workcell_runtime.utils import get_class_from_fqn
from praxis.backend.utils.errors import WorkcellRuntimeError
from praxis.backend.utils.uuid import uuid7


class TestGetClassFromFqn:

    """Tests for get_class_from_fqn helper function."""

    def test_get_class_from_fqn_success(self) -> None:
        """Test successful class loading from FQN."""
        # Test with a known standard library class
        result = get_class_from_fqn("collections.OrderedDict")
        from collections import OrderedDict
        assert result == OrderedDict

    def test_get_class_from_fqn_invalid_no_dot(self) -> None:
        """Test with invalid FQN (no dot)."""
        with pytest.raises(ValueError):
            get_class_from_fqn("InvalidClass")

    def test_get_class_from_fqn_empty_string(self) -> None:
        """Test with empty string."""
        with pytest.raises(ValueError):
            get_class_from_fqn("")

    def test_get_class_from_fqn_nonexistent_module(self) -> None:
        """Test with non-existent module."""
        with pytest.raises((ImportError, ModuleNotFoundError)):
            get_class_from_fqn("nonexistent.module.ClassName")

    @pytest.mark.parametrize(
        "stored_fqn",
        [
            # Pre-1.0 FQNs as persisted in DB rows / manifests. The top-level shim packages
            # have no `.liquid_handler` / `.chatterbox` submodules, so these only resolve
            # through the explicit pylabrobot.legacy home.
            "pylabrobot.liquid_handling.liquid_handler.LiquidHandler",
            "pylabrobot.liquid_handling.LiquidHandler",
            "pylabrobot.plate_reading.chatterbox.PlateReaderChatterboxBackend",
            "pylabrobot.heating_shaking.heater_shaker.HeaterShaker",
        ],
    )
    def test_get_class_from_fqn_resolves_pre_1_0_plr_paths_via_legacy(self, stored_fqn: str) -> None:
        """Old PLR machine paths resolve to their pylabrobot.legacy home, without a shim warning."""
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            cls = get_class_from_fqn(stored_fqn)
        assert cls.__module__.startswith("pylabrobot.legacy.")
        assert cls.__name__ == stored_fqn.rsplit(".", 1)[1]

    def test_get_class_from_fqn_explicit_legacy_and_top_level_resources_unchanged(self) -> None:
        """Explicit legacy FQNs and still-top-level modules are not rewritten."""
        from pylabrobot.resources import Plate

        legacy = get_class_from_fqn("pylabrobot.legacy.liquid_handling.liquid_handler.LiquidHandler")
        assert legacy.__module__ == "pylabrobot.legacy.liquid_handling.liquid_handler"
        assert get_class_from_fqn("pylabrobot.resources.plate.Plate") is Plate

    def test_get_class_from_fqn_legacy_fallback_does_not_mask_missing_class(self) -> None:
        """A shimmed package name with a class that exists nowhere still raises."""
        with pytest.raises((ImportError, AttributeError)):
            get_class_from_fqn("pylabrobot.liquid_handling.NoSuchClassAnywhere")


class TestWorkcellRuntimeInit:

    """Tests for WorkcellRuntime initialization."""

    def test_workcell_runtime_initialization(self) -> None:
        """Test WorkcellRuntime initialization."""
        mock_db_session_factory = Mock()
        mock_workcell = Mock()
        mock_workcell.name = "test_workcell"
        mock_deck_service = Mock()
        mock_machine_service = Mock()
        mock_resource_service = Mock()
        mock_deck_type_def_service = Mock()
        mock_workcell_service = Mock()

        runtime = WorkcellRuntime(
            db_session_factory=mock_db_session_factory,
            workcell=mock_workcell,
            deck_service=mock_deck_service,
            machine_service=mock_machine_service,
            resource_service=mock_resource_service,
            deck_type_definition_service=mock_deck_type_def_service,
            workcell_service=mock_workcell_service,
        )

        assert runtime.db_session_factory == mock_db_session_factory
        assert runtime._main_workcell == mock_workcell
        assert runtime.deck_svc == mock_deck_service
        assert runtime.machine_svc == mock_machine_service
        assert runtime.resource_svc == mock_resource_service
        assert runtime.deck_type_definition_svc == mock_deck_type_def_service
        assert runtime.workcell_svc == mock_workcell_service
        assert isinstance(runtime._active_machines, dict)
        assert isinstance(runtime._active_resources, dict)
        assert isinstance(runtime._active_decks, dict)


class TestGetMainWorkcell:

    """Tests for get_main_workcell method."""

    def test_get_main_workcell_success(self) -> None:
        """Test successful retrieval of main workcell."""
        mock_workcell = Mock()
        mock_workcell.name = "test_workcell"

        runtime = WorkcellRuntime(
            db_session_factory=Mock(),
            workcell=mock_workcell,
            deck_service=Mock(),
            machine_service=Mock(),
            resource_service=Mock(),
            deck_type_definition_service=Mock(),
            workcell_service=Mock(),
        )

        result = runtime.get_main_workcell()
        assert result == mock_workcell

    def test_get_main_workcell_not_initialized(self) -> None:
        """Test error when main workcell is not initialized."""
        runtime = WorkcellRuntime(
            db_session_factory=Mock(),
            workcell=Mock(),
            deck_service=Mock(),
            machine_service=Mock(),
            resource_service=Mock(),
            deck_type_definition_service=Mock(),
            workcell_service=Mock(),
        )

        # Set to None to simulate not initialized
        runtime._main_workcell = None

        with pytest.raises(WorkcellRuntimeError, match="not initialized"):
            runtime.get_main_workcell()


class TestStateManagement:

    """Tests for state snapshot and restoration methods."""

    def test_get_state_snapshot(self) -> None:
        """Test capturing state snapshot."""
        mock_workcell = Mock()
        mock_workcell.name = "test_workcell"
        mock_workcell.serialize_all_state.return_value = {"state": "data"}

        runtime = WorkcellRuntime(
            db_session_factory=Mock(),
            workcell=mock_workcell,
            deck_service=Mock(),
            machine_service=Mock(),
            resource_service=Mock(),
            deck_type_definition_service=Mock(),
            workcell_service=Mock(),
        )

        result = runtime.get_state_snapshot()

        assert result == {"state": "data"}
        mock_workcell.serialize_all_state.assert_called_once()

    def test_apply_state_snapshot(self) -> None:
        """Test applying state snapshot."""
        mock_workcell = Mock()
        mock_workcell.name = "test_workcell"

        runtime = WorkcellRuntime(
            db_session_factory=Mock(),
            workcell=mock_workcell,
            deck_service=Mock(),
            machine_service=Mock(),
            resource_service=Mock(),
            deck_type_definition_service=Mock(),
            workcell_service=Mock(),
        )

        snapshot = {"state": "restored_data"}
        runtime.apply_state_snapshot(snapshot)

        mock_workcell.load_all_state.assert_called_once_with(snapshot)


class TestLinkWorkcellToDb:

    """Tests for _link_workcell_to_db method."""

    @pytest.mark.asyncio
    async def test_link_workcell_to_db_new_workcell(self) -> None:
        """Test linking a new workcell to the database."""
        mock_workcell = Mock()
        mock_workcell.name = "test_workcell"
        mock_workcell.serialize_all_state.return_value = {"state": "data"}

        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        mock_workcell_model = Mock()
        mock_workcell_model.accession_id = uuid7()

        runtime = WorkcellRuntime(
            db_session_factory=mock_db_session_factory,
            workcell=mock_workcell,
            deck_service=Mock(),
            machine_service=Mock(),
            resource_service=Mock(),
            deck_type_definition_service=Mock(),
            workcell_service=Mock(),
        )

        runtime.workcell_svc.create = AsyncMock(return_value=mock_workcell_model)
        runtime.workcell_svc.read_workcell_state = AsyncMock(return_value={"db_state": "data"})

        await runtime._link_workcell_to_db()

        assert runtime._workcell_db_accession_id == mock_workcell_model.accession_id
        runtime.workcell_svc.create.assert_called_once()
        mock_workcell.load_all_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_link_workcell_to_db_already_linked(self) -> None:
        """Test linking when already linked (should skip)."""
        mock_workcell = Mock()
        mock_workcell.name = "test_workcell"

        runtime = WorkcellRuntime(
            db_session_factory=Mock(),
            workcell=mock_workcell,
            deck_service=Mock(),
            machine_service=Mock(),
            resource_service=Mock(),
            deck_type_definition_service=Mock(),
            workcell_service=Mock(),
        )

        # Already linked
        runtime._workcell_db_accession_id = uuid7()
        runtime.workcell_svc.create = AsyncMock()

        await runtime._link_workcell_to_db()

        # Should not create a new entry
        runtime.workcell_svc.create.assert_not_called()


class TestStartStopWorkcellStateSync:

    """Tests for start/stop workcell state sync methods."""

    @pytest.mark.asyncio
    async def test_start_workcell_state_sync(self) -> None:
        """Test starting workcell state synchronization."""
        mock_workcell = Mock()
        mock_workcell.name = "test_workcell"
        mock_workcell.serialize_all_state.return_value = {"state": "data"}

        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        mock_workcell_model = Mock()
        mock_workcell_model.accession_id = uuid7()

        runtime = WorkcellRuntime(
            db_session_factory=mock_db_session_factory,
            workcell=mock_workcell,
            deck_service=Mock(),
            machine_service=Mock(),
            resource_service=Mock(),
            deck_type_definition_service=Mock(),
            workcell_service=Mock(),
        )

        runtime.workcell_svc.create = AsyncMock(return_value=mock_workcell_model)
        runtime.workcell_svc.read_workcell_state = AsyncMock(return_value=None)

        await runtime.start_workcell_state_sync()

        assert runtime._state_sync_task is not None
        assert not runtime._state_sync_task.done()

        # Clean up
        await runtime.stop_workcell_state_sync()

    @pytest.mark.asyncio
    async def test_stop_workcell_state_sync(self) -> None:
        """Test stopping workcell state synchronization."""
        import asyncio

        mock_workcell = Mock()
        mock_workcell.name = "test_workcell"
        mock_workcell.save_file = "/tmp/test.json"
        mock_workcell.save_state_to_file = Mock()
        mock_workcell.serialize_all_state.return_value = {"state": "data"}

        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        runtime = WorkcellRuntime(
            db_session_factory=mock_db_session_factory,
            workcell=mock_workcell,
            deck_service=Mock(),
            machine_service=Mock(),
            resource_service=Mock(),
            deck_type_definition_service=Mock(),
            workcell_service=Mock(),
        )

        runtime._workcell_db_accession_id = uuid7()
        runtime.workcell_svc.update_workcell_state = AsyncMock()

        # Create a proper async task
        async def dummy_task():
            await asyncio.sleep(10)  # Long-running task

        runtime._state_sync_task = asyncio.create_task(dummy_task())

        await runtime.stop_workcell_state_sync()

        # Task should be cancelled and set to None
        assert runtime._state_sync_task is None
        mock_workcell.save_state_to_file.assert_called_once()


class TestGetCalculatedLocation:

    """Tests for _get_calculated_location method."""

    @pytest.mark.asyncio
    async def test_get_calculated_location_with_positioning_config(self) -> None:
        """Test calculating location with positioning configuration."""
        mock_workcell = Mock()
        mock_workcell.name = "test_workcell"

        runtime = WorkcellRuntime(
            db_session_factory=Mock(),
            workcell=mock_workcell,
            deck_service=Mock(),
            machine_service=Mock(),
            resource_service=Mock(),
            deck_type_definition_service=Mock(),
            workcell_service=Mock(),
        )

        # Create mock deck with position method
        mock_deck = Mock(spec=Deck)

        def mock_get_position(num: int) -> Coordinate:
            return Coordinate(x=100.0 + num, y=200.0 + num, z=0.0)

        mock_deck.get_position = mock_get_position

        # Create positioning config
        mock_positioning_config = Mock()
        mock_positioning_config.method_name = "get_position"
        mock_positioning_config.arg_name = "num"
        mock_positioning_config.arg_type = "int"
        mock_positioning_config.params = {}

        deck_type_id = uuid7()
        position_id = "1"

        result = await runtime._get_calculated_location(
            mock_deck,
            deck_type_id,
            position_id,
            mock_positioning_config,
        )

        assert isinstance(result, Coordinate)
        assert result.x == 101.0
        assert result.y == 201.0

    @pytest.mark.asyncio
    async def test_get_calculated_location_no_config_uses_db(self) -> None:
        """Test calculating location without config (uses database)."""
        mock_workcell = Mock()
        mock_workcell.name = "test_workcell"

        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        runtime = WorkcellRuntime(
            db_session_factory=mock_db_session_factory,
            workcell=mock_workcell,
            deck_service=Mock(),
            machine_service=Mock(),
            resource_service=Mock(),
            deck_type_definition_service=Mock(),
            workcell_service=Mock(),
        )

        mock_deck = Mock(spec=Deck)
        deck_type_id = uuid7()

        # Mock deck type definition with position
        mock_position_def = Mock()
        mock_position_def.position_accession_id = "A1"
        mock_position_def.nominal_x_mm = 10.0
        mock_position_def.nominal_y_mm = 20.0
        mock_position_def.nominal_z_mm = 0.0

        mock_deck_type_def = Mock()
        mock_deck_type_def.positions = [mock_position_def]

        runtime.deck_type_definition_svc.get = AsyncMock(return_value=mock_deck_type_def)

        result = await runtime._get_calculated_location(
            mock_deck,
            deck_type_id,
            "A1",
            None,  # No positioning config
        )

        assert isinstance(result, Coordinate)
        assert result.x == 10.0
        assert result.y == 20.0
        assert result.z == 0.0

    @pytest.mark.asyncio
    async def test_get_calculated_location_position_not_found(self) -> None:
        """Test error when position not found in database."""
        mock_workcell = Mock()
        mock_workcell.name = "test_workcell"

        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        runtime = WorkcellRuntime(
            db_session_factory=mock_db_session_factory,
            workcell=mock_workcell,
            deck_service=Mock(),
            machine_service=Mock(),
            resource_service=Mock(),
            deck_type_definition_service=Mock(),
            workcell_service=Mock(),
        )

        mock_deck = Mock(spec=Deck)
        deck_type_id = uuid7()

        # Mock deck type definition with no matching position
        mock_deck_type_def = Mock()
        mock_deck_type_def.positions = []

        runtime.deck_type_definition_svc.get = AsyncMock(return_value=mock_deck_type_def)

        with pytest.raises(WorkcellRuntimeError, match="Position.*not found"):
            await runtime._get_calculated_location(
                mock_deck,
                deck_type_id,
                "NONEXISTENT",
                None,
            )


class TestModuleStructure:

    """Tests for module structure and exports."""

    def test_module_has_workcell_runtime_class(self) -> None:
        """Test that module exports WorkcellRuntime."""
        from praxis.backend.core import workcell_runtime

        assert hasattr(workcell_runtime, "WorkcellRuntime")


class TestAssignResourceToDeck:

    """Tests for assign_resource_to_deck method."""

    @pytest.mark.asyncio
    async def test_assign_resource_to_occupied_position_raises_error(self) -> None:
        """Test that assigning a resource to an occupied position raises an error."""
        mock_workcell = Mock()
        mock_workcell.name = "test_workcell"

        mock_db_session = AsyncMock()
        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_db_session
        mock_session_ctx.__aexit__.return_value = None
        mock_db_session_factory = Mock(return_value=mock_session_ctx)

        runtime = WorkcellRuntime(
            db_session_factory=mock_db_session_factory,
            workcell=mock_workcell,
            deck_service=Mock(),
            machine_service=Mock(),
            resource_service=Mock(),
            deck_type_definition_service=Mock(),
            workcell_service=Mock(),
        )

        deck_id = uuid7()
        mock_deck = Mock(spec=Deck)
        runtime._active_decks[deck_id] = mock_deck

        resource_id = uuid7()
        mock_resource = Mock(spec=Resource)
        mock_resource.name = "new_resource"
        runtime._active_resources[resource_id] = mock_resource

        # Simulate existing resource in DB at the position
        mock_existing_resource = Mock()
        mock_existing_resource.name = "existing_resource"
        runtime.resource_svc.get_multi = AsyncMock(return_value=[mock_existing_resource])

        mock_deck_model = Mock()
        mock_deck_model.accession_id = deck_id
        mock_deck_model.deck_type_id = uuid7()
        runtime.deck_svc.get = AsyncMock(return_value=mock_deck_model)

        mock_deck_def = Mock()
        mock_deck_def.positioning_config_json = {}
        runtime.deck_type_definition_svc.get = AsyncMock(return_value=mock_deck_def)

        runtime._get_calculated_location = AsyncMock(return_value=Coordinate(0, 0, 0))

        with pytest.raises(WorkcellRuntimeError, match="occupied"):
            await runtime.assign_resource_to_deck(
                resource_orm_accession_id=resource_id,
                target=deck_id,
                position_accession_id="A1",
            )
