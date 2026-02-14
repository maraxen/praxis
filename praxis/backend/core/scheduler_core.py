# pylint: disable=too-many-arguments,fixme
"""Protocol Scheduler - Manages protocol execution scheduling and asset allocation."""
import uuid
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from praxis.backend.core.scheduler_resources import AssetReservationManager
from praxis.backend.core.scheduler_state import ScheduleEntry
from praxis.backend.models.domain.filters import SearchFilters
from praxis.backend.models.domain.protocol import (
  AssetConstraintsModel,
  FunctionProtocolDefinition,
  LocationConstraintsModel,
  ProtocolRunUpdate,
)
from praxis.backend.models.domain.protocol import (
  AssetRequirement as AssetRequirementModel,
)
from praxis.backend.models.enums import ProtocolRunStatusEnum
from praxis.backend.models.pydantic_internals.runtime import RuntimeAssetRequirement
from praxis.backend.services.protocol_definition import ProtocolDefinitionCRUDService
from praxis.backend.services.protocols import ProtocolRunService
from praxis.backend.utils.errors import AssetAcquisitionError, OrchestratorError
from praxis.backend.utils.logging import get_logger
from praxis.backend.utils.uuid import uuid7, generate_accession_id

logger = get_logger(__name__)


class TaskResult(Protocol):
  """A protocol for a task result."""

  id: str | None


class TaskQueue(Protocol):
  """A protocol for a task queue."""

  def send_task(self, name: str, args: list[Any]) -> TaskResult:
    """Send a task to the queue."""
    ...


class ProtocolScheduler:
  """Manages protocol scheduling, asset allocation, and execution queueing."""

  def __init__(
    self,
    db_session_factory: async_sessionmaker[AsyncSession],
    task_queue: TaskQueue,
    protocol_run_service: ProtocolRunService,
    protocol_definition_service: ProtocolDefinitionCRUDService,
  ) -> None:
    """Initialize the Protocol Scheduler."""
    self.db_session_factory = db_session_factory
    self.task_queue = task_queue
    self.protocol_run_service = protocol_run_service
    self.protocol_definition_service = protocol_definition_service
    self.asset_reservation_manager = AssetReservationManager(db_session_factory)

    self._active_schedules: dict[uuid.UUID, ScheduleEntry] = {}
    logger.info("ProtocolScheduler initialized with database-backed reservations.")

  async def analyze_protocol_requirements(
    self,
    protocol_def_model: FunctionProtocolDefinition,
    _user_params: dict[str, Any],
    workcell_id: str | None = None,
  ) -> list[RuntimeAssetRequirement]:
    """Analyze a protocol definition to determine asset requirements."""
    from praxis.backend.core.consumable_assignment import ConsumableAssignmentService

    logger.info(
      "Analyzing asset requirements for protocol: %s v%s",
      protocol_def_model.name,
      protocol_def_model.version,
    )

    requirements: list[RuntimeAssetRequirement] = []

    for asset_def in protocol_def_model.assets:
      asset_requirement_model = AssetRequirementModel.model_validate(asset_def)
      requirement = RuntimeAssetRequirement(
        asset_definition=asset_requirement_model,
        asset_type="asset",
        estimated_duration_ms=None,
        priority=1,
      )
      requirements.append(requirement)
      logger.debug(
        "Added asset requirement: %s (%s)",
        asset_def.name,
        asset_def.actual_type_str,
      )

    if protocol_def_model.preconfigure_deck and protocol_def_model.deck_param_name:
      deck_asset_requirement = AssetRequirementModel(
        accession_id=generate_accession_id(),
        name=protocol_def_model.deck_param_name,
        fqn="pylabrobot.resources.Deck",
        type_hint_str="pylabrobot.resources.Deck",
        optional=False,
        constraints=AssetConstraintsModel(),
        location_constraints=LocationConstraintsModel(),
      )
      deck_requirement = RuntimeAssetRequirement(
        asset_definition=deck_asset_requirement,
        asset_type="deck",
        estimated_duration_ms=None,
        priority=1,
      )
      requirements.append(deck_requirement)
      logger.debug("Added deck requirement: %s", protocol_def_model.deck_param_name)

    async with self.db_session_factory() as db_session:
      try:
        assignment_service = ConsumableAssignmentService(db_session)
        for requirement in requirements:
          if requirement.asset_type == "asset" and requirement.suggested_asset_id is None:
            suggested_id = await assignment_service.find_compatible_consumable(
              requirement.asset_definition, # type: ignore
              workcell_id=workcell_id,
            )
            if suggested_id:
              requirement.suggested_asset_id = uuid.UUID(suggested_id)
              logger.debug(
                "Suggested consumable %s for requirement %s",
                suggested_id,
                requirement.asset_name,
              )
      except Exception as e:
        logger.warning("Could not auto-assign consumables: %s", e)

    logger.info(
      "Protocol analysis complete. Found %d asset requirements.",
      len(requirements),
    )
    return requirements

  async def schedule_protocol_execution(
    self,
    protocol_run_id: uuid.UUID,
    user_params: dict[str, Any],
    initial_state: dict[str, Any] | None = None,
  ) -> bool:
    """Schedule a protocol for execution."""
    logger.info(
      "Scheduling protocol execution for run %s",
      protocol_run_id,
    )

    try:
      async with self.db_session_factory() as db_session:
        protocol_run_model = await self.protocol_run_service.get(
          db_session,
          accession_id=protocol_run_id,
        )

        if not protocol_run_model:
          logger.error("Protocol run %s not found", protocol_run_id)
          return False

        protocol_def = await self.protocol_definition_service.get(
          db=db_session,
          accession_id=protocol_run_model.top_level_protocol_definition_accession_id,
        )

        if not protocol_def:
          logger.error(
            "Protocol definition not found for run %s",
            protocol_run_model.accession_id,
          )
          return False

        requirements = await self.analyze_protocol_requirements(
          protocol_def,
          user_params,
        )

        try:
          await self.asset_reservation_manager.reserve_assets(
            requirements, protocol_run_model.accession_id
          )
        except AssetAcquisitionError as e:
          logger.error(
            "Failed to reserve assets for run %s: %s",
            protocol_run_model.accession_id,
            e,
          )
          await self.protocol_run_service.update(
            db=db_session,
            db_obj=protocol_run_model,
            obj_in=ProtocolRunUpdate(
              status=ProtocolRunStatusEnum.FAILED,
              output_data_json={
                "error": "Asset reservation failed",
                "details": str(e),
              },
            ),
          )
          await db_session.commit()
          raise

        schedule_entry = ScheduleEntry(
          protocol_run_id=protocol_run_model.accession_id,
          protocol_name=str(protocol_def.name),
          required_assets=requirements,
          estimated_duration_ms=None,
        )
        self._active_schedules[protocol_run_model.accession_id] = schedule_entry

        await self.protocol_run_service.update(
          db=db_session,
          db_obj=protocol_run_model,
          obj_in=ProtocolRunUpdate(
            status=ProtocolRunStatusEnum.QUEUED,
            output_data_json={
              "scheduled_at": schedule_entry.scheduled_at.isoformat(),
              "asset_count": len(requirements),
            },
          ),
        )
        await db_session.commit()

        success = await self._queue_execution_task(
          protocol_run_model.accession_id,
          user_params,
          initial_state,
        )

        if success:
          logger.info(
            "Successfully scheduled protocol run %s for execution",
            protocol_run_model.accession_id,
          )
          return True
        await self.cancel_scheduled_run(protocol_run_model.accession_id)
        return False

    except Exception as e:
      logger.exception(
        "Error scheduling protocol execution for run %s",
        protocol_run_id,
      )
      if isinstance(e, AssetAcquisitionError | OrchestratorError):
        raise
      msg = f"Failed to schedule protocol execution: {e!s}"
      raise OrchestratorError(msg) from e

  async def _queue_execution_task(
    self,
    protocol_run_id: uuid.UUID,
    user_params: dict[str, Any],
    initial_state: dict[str, Any] | None,
  ) -> bool:
    """Queue a protocol execution task using Celery."""
    logger.info("Queueing execution task for run %s", protocol_run_id)
    user_params = user_params or {}

    try:
      task_result = self.task_queue.send_task(
        "execute_protocol_run",
        args=[
          str(protocol_run_id),
          user_params,
          initial_state,
        ],
      )
      celery_task_id = task_result.id
      logger.info(
        "Successfully queued protocol run %s with Celery task ID: %s",
        protocol_run_id,
        celery_task_id,
      )

      if protocol_run_id in self._active_schedules:
        schedule_entry = self._active_schedules[protocol_run_id]
        schedule_entry.status = "QUEUED"
        schedule_entry.celery_task_id = celery_task_id

    except Exception as e:
      error_str = str(e).lower()
      if "connection" in error_str or "refused" in error_str or "operational" in error_str:
        logger.warning(
          "Celery broker unavailable for run %s - continuing without task queue (simulation mode). Error: %s",
          protocol_run_id,
          e,
        )
        if protocol_run_id in self._active_schedules:
          schedule_entry = self._active_schedules[protocol_run_id]
          schedule_entry.status = "RUNNING_DIRECT"
          schedule_entry.celery_task_id = None
        return True

      logger.exception(
        "Failed to queue execution task for run %s",
        protocol_run_id,
      )
      return False
    else:
      return True

  async def cancel_scheduled_run(self, protocol_run_id: uuid.UUID) -> bool:
    """Cancel a scheduled protocol run and release assets."""
    logger.info("Cancelling scheduled run %s", protocol_run_id)

    try:
      if protocol_run_id not in self._active_schedules:
        logger.warning("Run %s not found in active schedules", protocol_run_id)
        return False

      schedule_entry = self._active_schedules[protocol_run_id]
      asset_keys = [
        f"{r.asset_type}:{r.asset_definition.name}" for r in schedule_entry.required_assets
      ]
      await self.asset_reservation_manager.release_reservations(asset_keys, protocol_run_id)
      del self._active_schedules[protocol_run_id]
      logger.info("Successfully cancelled scheduled run %s", protocol_run_id)

    except Exception:
      logger.exception(
        "Error cancelling scheduled run %s",
        protocol_run_id,
      )
      return False
    else:
      return True

  async def get_schedule_status(
    self,
    protocol_run_id: uuid.UUID,
  ) -> dict[str, Any] | None:
    """Get the current schedule status for a protocol run."""
    if protocol_run_id not in self._active_schedules:
      return None

    schedule_entry = self._active_schedules[protocol_run_id]

    return {
      "protocol_run_id": str(protocol_run_id),
      "protocol_name": schedule_entry.protocol_name,
      "status": schedule_entry.status,
      "scheduled_at": schedule_entry.scheduled_at.isoformat(),
      "asset_count": len(schedule_entry.required_assets),
      "estimated_duration_ms": schedule_entry.estimated_duration_ms,
      "priority": schedule_entry.priority,
    }

  async def list_active_schedules(self) -> list[dict[str, Any]]:
    """List all currently active protocol schedules."""
    schedules = []
    for protocol_run_id in self._active_schedules:
      status = await self.get_schedule_status(protocol_run_id)
      if status:
        schedules.append(status)
    return sorted(schedules, key=lambda x: x["scheduled_at"])

  async def complete_scheduled_run(self, protocol_run_id: uuid.UUID) -> bool:
    """Mark a scheduled run as complete and release reserved assets."""
    logger.info("Completing scheduled run %s", protocol_run_id)
    try:
      if protocol_run_id not in self._active_schedules:
        logger.debug(
          "Run %s not found in active schedules (may have been cancelled or never scheduled)",
          protocol_run_id,
        )
        reserved_assets_to_clear: list[str] = []
        for (
          asset_key,
          reserved_by_set,
        ) in self.asset_reservation_manager._asset_reservations_cache.items():
          if protocol_run_id in reserved_by_set:
            reserved_assets_to_clear.append(asset_key)
        if reserved_assets_to_clear:
          logger.warning(
            "Found stray asset reservations for non-scheduled run %s: %s",
            protocol_run_id,
            reserved_assets_to_clear,
          )
          await self.asset_reservation_manager.release_reservations(
            reserved_assets_to_clear, protocol_run_id
          )
        return False

      schedule_entry = self._active_schedules[protocol_run_id]
      asset_keys_to_release = [
        f"{r.asset_type}:{r.asset_definition.name}" for r in schedule_entry.required_assets
      ]
      await self.asset_reservation_manager.release_reservations(
        asset_keys_to_release, protocol_run_id
      )
      del self._active_schedules[protocol_run_id]
      logger.info(
        "Successfully completed scheduled run %s and released resources",
        protocol_run_id,
      )
      return True

    except Exception:
      logger.exception("Error completing scheduled run %s", protocol_run_id)
      return False

  async def recover_stale_runs(self) -> None:
    """Find and fail stale protocol runs on startup."""
    logger.info("Starting recovery of stale protocol runs...")
    recovered_runs_count = 0
    batch_size = 100
    offset = 0

    try:
      async with self.db_session_factory() as db_session:
        stale_statuses = [ProtocolRunStatusEnum.QUEUED, ProtocolRunStatusEnum.PREPARING]
        while True:
          runs_to_recover = await self.protocol_run_service.get_multi(
            db=db_session,
            filters=SearchFilters(offset=offset, limit=batch_size),
            statuses=stale_statuses,
          )
          if not runs_to_recover:
            break

          for run in runs_to_recover:
            logger.warning(
              "Found stale run %s in %s state. Marking as FAILED.",
              run.accession_id,
              run.status.name,
            )
            await self.protocol_run_service.update(
              db=db_session,
              db_obj=run,
              obj_in=ProtocolRunUpdate(
                status=ProtocolRunStatusEnum.FAILED,
                output_data_json={
                  "error": "Stale run recovered on server startup",
                  "details": (
                    f"The server restarted while this run was in a {run.status.name} state. "
                    "Asset reservations were lost, and the run could not proceed."
                  ),
                },
              ),
            )
            recovered_runs_count += 1

          await db_session.commit()
          offset += len(runs_to_recover)

      if recovered_runs_count > 0:
        logger.info("Successfully recovered %d stale runs.", recovered_runs_count)
      else:
        logger.info("No stale runs found.")
    except Exception:
      logger.exception(
        "Error during stale run recovery. This may indicate a database connection issue."
      )
