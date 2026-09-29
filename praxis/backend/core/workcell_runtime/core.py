"""Core WorkcellRuntime class definition."""

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from praxis.backend.core.protocols.workcell import IWorkcell
from praxis.backend.core.protocols.workcell_runtime import IWorkcellRuntime
from praxis.backend.core.workcell_runtime.deck_manager import DeckManagerMixin
from praxis.backend.core.workcell_runtime.machine_manager import MachineManagerMixin
from praxis.backend.core.workcell_runtime.resource_manager import ResourceManagerMixin
from praxis.backend.core.workcell_runtime.state_sync import StateSyncMixin
from praxis.backend.services.deck import DeckService
from praxis.backend.services.deck_type_definition import DeckTypeDefinitionService
from praxis.backend.services.machine import MachineService
from praxis.backend.services.resource import ResourceService
from praxis.backend.services.workcell import WorkcellService
from praxis.backend.utils.logging import get_logger

if TYPE_CHECKING:
  import asyncio
  import uuid

  from pylabrobot.legacy.machines import Machine
  from pylabrobot.resources import Deck, Resource

  from praxis.backend.models.domain.deck import Deck

logger = get_logger(__name__)


class WorkcellRuntime(
  MachineManagerMixin,
  ResourceManagerMixin,
  DeckManagerMixin,
  StateSyncMixin,
  IWorkcellRuntime,
):
  """Manages live PyLabRobot objects for an active workcell configuration.

  This class is responsible for initializing, maintaining, and shutting down
  PyLabRobot machine and resource instances based on database definitions.
  It also provides functionality to interact with the live deck state.
  """

  def __init__(
    self,
    db_session_factory: async_sessionmaker[AsyncSession],
    workcell: IWorkcell,
    deck_service: DeckService,
    machine_service: MachineService,
    resource_service: ResourceService,
    deck_type_definition_service: DeckTypeDefinitionService,
    workcell_service: WorkcellService,
  ) -> None:
    """Initialize the WorkcellRuntime."""
    self.db_session_factory = db_session_factory
    self.deck_svc = deck_service
    self.machine_svc = machine_service
    self.resource_svc = resource_service
    self.deck_type_definition_svc = deck_type_definition_service
    self.workcell_svc = workcell_service
    self._active_machines: dict[uuid.UUID, Machine] = {}
    self._active_resources: dict[uuid.UUID, Resource] = {}
    self._active_decks: dict[uuid.UUID, Deck] = {}
    self._last_initialized_deck_object: Deck | None = None
    self._last_initialized_deck_orm_accession_id: uuid.UUID | None = None

    self._main_workcell = workcell
    self._workcell_db_accession_id: uuid.UUID | None = None
    self._state_sync_task: asyncio.Task | None = None
    logger.info("WorkcellRuntime initialized.")
