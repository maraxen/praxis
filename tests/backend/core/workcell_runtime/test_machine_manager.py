from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from praxis.backend.core.workcell_runtime.machine_manager import MachineManagerMixin
from praxis.backend.models import DeckDefinition, Machine, MachineDefinition


class MockSetup(MagicMock):
  def __call__(self, *args, **kwargs):
    return super().__call__(*args, **kwargs)

  def __await__(self):
    async def _async_call():
      pass

    return _async_call().__await__()


class MockLH:
  def __init__(self, name, deck=None, **kwargs):
    self.name = name
    self.deck = deck
    self.setup = MockSetup()


class MockDeck:
  def __init__(self, name, **kwargs):
    self.name = name


class MockRuntime(MachineManagerMixin):
  def __init__(self):
    self._active_machines = {}
    self._active_resources = {}
    self._active_decks = {}
    self._main_workcell = MagicMock()
    self.db_session_factory = MagicMock()
    self.machine_svc = MagicMock()
    self.machine_svc.update_machine_status = AsyncMock()
    self.deck_svc = MagicMock()
    self._last_initialized_deck_object = None
    self._last_initialized_deck_orm_accession_id = None


@pytest.mark.asyncio
async def test_initialize_machine_auto_assigns_deck():
  runtime = MockRuntime()

  # Mocking DB session context manager
  mock_db_session = AsyncMock()
  runtime.db_session_factory.return_value.__aenter__.return_value = mock_db_session

  # Mock Deck Definition
  deck_def = MagicMock(spec=DeckDefinition)
  deck_def.accession_id = uuid4()
  deck_def.fqn = "pylabrobot.resources.Deck"
  deck_def.name = "Test Deck"

  # Mock Machine Definition
  machine_def = MagicMock(spec=MachineDefinition)
  machine_def.accession_id = uuid4()
  machine_def.fqn = "pylabrobot.liquid_handling.LiquidHandler"
  machine_def.deck_definition = deck_def

  # Machine Model Mock
  machine_model = MagicMock(spec=Machine)
  machine_model.id = 1
  machine_model.accession_id = uuid4()
  machine_model.name = "STAR1"
  machine_model.fqn = "pylabrobot.liquid_handling.LiquidHandler"
  machine_model.properties_json = {}
  machine_model.machine_definition = machine_def
  machine_model.is_resource = False
  machine_model.frontend_definition_accession_id = None
  machine_model.backend_definition_accession_id = None
  machine_model.frontend_definition = None
  machine_model.backend_definition = None

  # Mock get_class_from_fqn
  with patch(
    "praxis.backend.core.workcell_runtime.machine_manager.get_class_from_fqn"
  ) as mock_get_class:

    def side_effect(fqn):
      if fqn == "pylabrobot.liquid_handling.LiquidHandler":
        return MockLH
      if fqn == "pylabrobot.resources.Deck":
        return MockDeck
      return MagicMock()

    mock_get_class.side_effect = side_effect

    # Mock deck_svc response for deck registration
    deck_orm_entry = MagicMock()
    deck_orm_entry.accession_id = uuid4()
    runtime.deck_svc.read_decks_by_machine_id = AsyncMock(return_value=deck_orm_entry)

    with patch("praxis.backend.core.workcell_runtime.machine_manager.Machine", new=MockLH):
      with patch("praxis.backend.core.workcell_runtime.machine_manager.Deck", new=MockDeck):
        # EXECUTE
        result = await runtime.initialize_machine(machine_model)

        # VERIFY
        assert isinstance(result, MockLH)
        # Check if deck was assigned
        assert result.deck is not None
        assert isinstance(result.deck, MockDeck)


@pytest.mark.asyncio
async def test_initialize_machine_does_not_overwrite_existing_deck():
  runtime = MockRuntime()

  # Mocking DB session context manager
  mock_db_session = AsyncMock()
  runtime.db_session_factory.return_value.__aenter__.return_value = mock_db_session

  # Mock Deck Definition (should NOT be used)
  deck_def = MagicMock(spec=DeckDefinition)
  deck_def.fqn = "pylabrobot.resources.Deck"

  # Mock Machine Definition
  machine_def = MagicMock(spec=MachineDefinition)
  machine_def.deck_definition = deck_def

  # Existing deck in properties
  existing_deck = MockDeck(name="Existing Deck")

  # Machine Model Mock
  machine_model = MagicMock(spec=Machine)
  machine_model.id = 1
  machine_model.accession_id = uuid4()
  machine_model.name = "STAR1"
  machine_model.fqn = "pylabrobot.liquid_handling.LiquidHandler"
  machine_model.properties_json = {"deck": existing_deck}
  machine_model.machine_definition = machine_def
  machine_model.is_resource = False
  machine_model.frontend_definition_accession_id = None
  machine_model.backend_definition_accession_id = None
  machine_model.frontend_definition = None
  machine_model.backend_definition = None

  # Mock get_class_from_fqn
  with patch(
    "praxis.backend.core.workcell_runtime.machine_manager.get_class_from_fqn"
  ) as mock_get_class:
    mock_get_class.return_value = MockLH

    # Mock deck_svc
    runtime.deck_svc.read_decks_by_machine_id = AsyncMock(return_value=MagicMock())

    with patch("praxis.backend.core.workcell_runtime.machine_manager.Machine", new=MockLH):
      with patch("praxis.backend.core.workcell_runtime.machine_manager.Deck", new=MockDeck):
        # EXECUTE
        result = await runtime.initialize_machine(machine_model)

        # VERIFY
        assert isinstance(result, MockLH)
        assert result.deck == existing_deck
