"""State Resolution Service for managing protocol execution error resolution.

This service provides the business logic for handling state resolution during
protocol execution errors. It integrates with:
- The simulation infrastructure to identify uncertain states
- The schedule entry and protocol run tracking
- The resolution audit logging

Usage:
    service = StateResolutionService(session)
    uncertain = await service.get_uncertain_states(run_id)
    await service.resolve_states(run_id, resolution)
    await service.resume_run(run_id)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select

from praxis.backend.core.simulation.state_resolution import (
  OperationRecord,
  ResolutionType,
  StateResolution,
  UncertainStateChange,
  apply_resolution,
  identify_uncertain_states,
)
from praxis.backend.models.domain.resolution import StateResolutionLog as StateResolutionLog
from praxis.backend.models.domain.schedule import ScheduleEntry as ScheduleEntry
from praxis.backend.models.enums.resolution import (
  ResolutionActionEnum,
  ResolutionTypeEnum,
)
from praxis.backend.models.enums.schedule import ScheduleStatusEnum
from praxis.backend.utils.db_decorator import handle_db_transaction
from praxis.backend.utils.errors import AccessionNotFoundError

if TYPE_CHECKING:
  from uuid import UUID

  from sqlalchemy.ext.asyncio import AsyncSession

  from praxis.backend.core.simulation.state_models import SimulationState

logger = logging.getLogger(__name__)


class StateResolutionService:
  """Service for managing state resolution during protocol errors.

  This service provides methods to:
  - Retrieve uncertain states for a paused run
  - Apply user-provided resolutions
  - Log resolutions for audit purposes
  - Resume or abort runs after resolution
  """

  def __init__(self, session: AsyncSession) -> None:
    """Initialize the service.

    Args:
        session: Database session for queries

    """
    self._session = session
    self._pending_resolutions: dict[UUID, list[UncertainStateChange]] = {}
    self._operation_records: dict[UUID, OperationRecord] = {}
    self._state_snapshots: dict[UUID, SimulationState] = {}

  async def get_uncertain_states(
    self,
    run_id: UUID,
  ) -> list[UncertainStateChange]:
    """Get uncertain states for a paused run.

    This retrieves the list of state changes that are uncertain due to
    a failed operation. The run must be in PAUSED or ERROR state.

    Args:
        run_id: Accession ID of the protocol run or schedule entry

    Returns:
        List of uncertain state changes

    Raises:
        ValueError: If run is not found or not in a paused state

    """
    # Get the schedule entry
    schedule_entry = await self._get_schedule_entry(run_id)
    if not schedule_entry:
      logger.warning("Accession lookup failed for run %s: ScheduleEntry not found", run_id)
      raise AccessionNotFoundError("ScheduleEntry", run_id)

    # Check if run is in a state that allows resolution
    # Use FAILED status since there's no explicit PAUSED status
    if schedule_entry.status not in (
      ScheduleStatusEnum.FAILED,
      ScheduleStatusEnum.CONFLICT,
    ):
      msg = (
        f"Run {run_id} is in {schedule_entry.status.value} state, not eligible for state resolution"
      )
      raise ValueError(msg)

    # Check if we have cached uncertain states
    if run_id in self._pending_resolutions:
      return self._pending_resolutions[run_id]

    # Get the operation record for the failed operation
    operation = self._operation_records.get(run_id)
    if not operation:
      # Try to reconstruct from schedule entry error info
      operation = self._reconstruct_operation_from_entry(schedule_entry)
      if operation:
        self._operation_records[run_id] = operation

    if not operation:
      # No operation info available - return empty
      logger.warning(
        "No operation record found for run %s, cannot identify uncertain states",
        run_id,
      )
      return []

    # Get state snapshot
    state_snapshot = self._state_snapshots.get(run_id)

    # Identify uncertain states
    uncertain = identify_uncertain_states(operation, state_snapshot)

    # Cache for later
    self._pending_resolutions[run_id] = uncertain

    return uncertain

  async def resolve_states(
    self,
    run_id: UUID,
    resolution: StateResolution,
    action: ResolutionActionEnum = ResolutionActionEnum.RESUME,
  ) -> StateResolutionLog:
    """Apply resolution and log for audit.

    Args:
        run_id: Accession ID of the protocol run or schedule entry
        resolution: User-provided state resolution
        action: Post-resolution action (resume, abort, retry)

    Returns:
        The created resolution log entry

    Raises:
        ValueError: If run is not found or resolution is invalid

    """
    schedule_entry = await self._get_schedule_entry(run_id)
    if not schedule_entry:
      logger.warning("Accession lookup failed for run %s during state resolution", run_id)
      raise AccessionNotFoundError("ScheduleEntry", run_id)

    # Get the uncertain states that were pending
    uncertain = self._pending_resolutions.get(run_id, [])

    # Get operation record
    operation = self._operation_records.get(run_id)
    operation_id = resolution.operation_id or (operation.operation_id if operation else "unknown")
    operation_desc = (
      f"{operation.method_name}({', '.join(operation.args)})" if operation else "Unknown operation"
    )
    error_msg = operation.error_message if operation else "Unknown error"
    error_type = operation.error_type if operation else None

    # Apply resolution to state if we have a state snapshot
    if run_id in self._state_snapshots:
      state = self._state_snapshots[run_id]
      apply_resolution(resolution, state)
    else:
      logger.warning(
        "No state snapshot found for run %s, skipping state update in diff engine",
        run_id,
      )

    # Create audit log entry
    # Generate a name from operation info
    log_name = f"resolution_{operation_id}"
    log_entry = StateResolutionLog(
      name=log_name,
      schedule_entry_accession_id=schedule_entry.accession_id,
      protocol_run_accession_id=schedule_entry.protocol_run_accession_id,
      operation_id=operation_id,
      operation_description=operation_desc,
      error_message=error_msg,
      error_type=error_type,
      uncertain_states_json={"states": [s.to_dict() for s in uncertain]},
      resolution_json=resolution.to_dict(),
      resolution_type=self._map_resolution_type(resolution.resolution_type),
      resolved_by=resolution.resolved_by,
      notes=resolution.notes,
      action_taken=action,
    )

    self._session.add(log_entry)

    # Clear the pending resolution cache
    if run_id in self._pending_resolutions:
      del self._pending_resolutions[run_id]

    logger.info(
      "State resolution logged for run %s, action: %s",
      run_id,
      action.value,
    )

    return log_entry

  @handle_db_transaction
  async def resume_run(
    self,
    run_id: UUID,
  ) -> None:
    """Resume a paused run after state resolution.

    Args:
        run_id: Accession ID of the protocol run or schedule entry

    Raises:
        ValueError: If run is not found or cannot be resumed

    """
    schedule_entry = await self._get_schedule_entry(run_id)
    if not schedule_entry:
      logger.warning("Accession lookup failed for run %s during resume", run_id)
      raise AccessionNotFoundError("ScheduleEntry", run_id)

    if schedule_entry.status not in (
      ScheduleStatusEnum.FAILED,
      ScheduleStatusEnum.CONFLICT,
    ):
      msg = f"Run {run_id} is in {schedule_entry.status.value} state, cannot resume"
      raise ValueError(msg)

    # Update status to EXECUTING (resume execution)
    schedule_entry.status = ScheduleStatusEnum.EXECUTING

    # Clear caches
    self._cleanup_run_caches(run_id)

    logger.info("Run %s resumed after state resolution", run_id)

  @handle_db_transaction
  async def abort_run(
    self,
    run_id: UUID,
    reason: str | None = None,
  ) -> None:
    """Abort a run after state resolution.

    Args:
        run_id: Accession ID of the protocol run or schedule entry
        reason: Optional reason for aborting

    Raises:
        ValueError: If run is not found

    """
    schedule_entry = await self._get_schedule_entry(run_id)
    if not schedule_entry:
      logger.warning("Accession lookup failed for run %s during abort", run_id)
      raise AccessionNotFoundError("ScheduleEntry", run_id)

    # Update status to CANCELLED
    schedule_entry.status = ScheduleStatusEnum.CANCELLED
    if reason:
      schedule_entry.last_error_message = reason

    # Clear caches
    self._cleanup_run_caches(run_id)

    logger.info("Run %s aborted: %s", run_id, reason or "user requested")

  def register_failed_operation(
    self,
    run_id: UUID,
    operation: OperationRecord,
    state_snapshot: SimulationState | None = None,
  ) -> None:
    """Register a failed operation for later resolution.

    This is called by the execution infrastructure when an operation fails,
    providing the context needed for state resolution.

    Args:
        run_id: Accession ID of the run
        operation: Record of the failed operation
        state_snapshot: Optional state snapshot at time of failure

    """
    self._operation_records[run_id] = operation
    if state_snapshot:
      self._state_snapshots[run_id] = state_snapshot

    logger.debug(
      "Registered failed operation for run %s: %s",
      run_id,
      operation.method_name,
    )

  async def _get_schedule_entry(
    self,
    run_id: UUID,
  ) -> ScheduleEntry | None:
    """Get schedule entry by run ID.

    Args:
        run_id: Either the schedule entry ID or protocol run ID

    Returns:
        Schedule entry if found

    """
    # Try as schedule entry ID
    result = await self._session.execute(
      select(ScheduleEntry).where(ScheduleEntry.accession_id == run_id)
    )
    entry = result.scalar_one_or_none()
    if entry:
      return entry

    # Try as protocol run ID
    result = await self._session.execute(
      select(ScheduleEntry).where(ScheduleEntry.protocol_run_accession_id == run_id)
    )
    return result.scalar_one_or_none()

  def _reconstruct_operation_from_entry(
    self,
    entry: ScheduleEntry,
  ) -> OperationRecord | None:
    """Try to reconstruct operation record from schedule entry.

    Args:
        entry: Schedule entry with error info

    Returns:
        Operation record if reconstruction possible

    """
    if not entry.last_error_message:
      return None

    # Basic reconstruction - just error info
    return OperationRecord(
      operation_id=f"op_{entry.accession_id}",
      method_name="unknown",
      receiver_type="unknown",
      error_message=entry.last_error_message,
      error_type="ExecutionError",
    )

  def _cleanup_run_caches(self, run_id: UUID) -> None:
    """Clean up caches for a run.

    Args:
        run_id: Run to clean up

    """
    self._pending_resolutions.pop(run_id, None)
    self._operation_records.pop(run_id, None)
    self._state_snapshots.pop(run_id, None)

  @staticmethod
  def _map_resolution_type(rt: ResolutionType) -> ResolutionTypeEnum:
    """Map core ResolutionType to ORM enum.

    Args:
        rt: Core resolution type

    Returns:
        ORM resolution type enum

    """
    mapping = {
      ResolutionType.CONFIRMED_SUCCESS: ResolutionTypeEnum.CONFIRMED_SUCCESS,
      ResolutionType.CONFIRMED_FAILURE: ResolutionTypeEnum.CONFIRMED_FAILURE,
      ResolutionType.PARTIAL: ResolutionTypeEnum.PARTIAL,
      ResolutionType.ARBITRARY: ResolutionTypeEnum.ARBITRARY,
      ResolutionType.UNKNOWN: ResolutionTypeEnum.UNKNOWN,
    }
    return mapping.get(rt, ResolutionTypeEnum.UNKNOWN)


# =============================================================================
# Pydantic Models for API
# =============================================================================


from typing import Any

from pydantic import BaseModel, Field


class UncertainStateChangeResponse(BaseModel):
  """API response model for uncertain state change."""

  state_key: str = Field(..., description="Unique key identifying the state property")
  current_value: Any | None = Field(None, description="Value before the operation")
  expected_value: Any | None = Field(None, description="Expected value if succeeded")
  description: str = Field("", description="Human-readable description")
  resolution_type: str = Field("arbitrary", description="Type of input needed")
  resource_name: str | None = Field(None, description="Associated resource name")
  property_name: str | None = Field(None, description="Property that may have changed")
  property_type: str = Field("arbitrary", description="Type of state property")
  suggested_resolutions: list[str] = Field(
    default_factory=list,
    description="Common resolution options",
  )

  @classmethod
  def from_core(cls, uc: UncertainStateChange) -> UncertainStateChangeResponse:
    """Create from core model."""
    return cls(
      state_key=uc.state_key,
      current_value=uc.current_value,
      expected_value=uc.expected_value,
      description=uc.description,
      resolution_type=uc.resolution_type,
      resource_name=uc.resource_name,
      property_name=uc.property_name,
      property_type=uc.property_type.value,
      suggested_resolutions=uc.suggested_resolutions,
    )


class StateResolutionRequest(BaseModel):
  """API request model for state resolution."""

  operation_id: str = Field(..., description="ID of the failed operation")
  resolution_type: str = Field(
    ...,
    description="Type of resolution (confirmed_success, confirmed_failure, partial, arbitrary, unknown)",
  )
  resolved_values: dict[str, Any] = Field(
    default_factory=dict,
    description="Mapping of state_key -> resolved value",
  )
  notes: str | None = Field(None, description="Optional notes about the resolution")
  action: str = Field(
    "resume",
    description="Post-resolution action (resume, abort, retry)",
  )

  def to_core_resolution(self, resolved_by: str = "user") -> StateResolution:
    """Convert to core StateResolution model."""
    return StateResolution(
      operation_id=self.operation_id,
      resolution_type=ResolutionType(self.resolution_type),
      resolved_values=self.resolved_values,
      resolved_by=resolved_by,
      resolved_at=datetime.now(timezone.utc),
      notes=self.notes,
    )

  def get_action(self) -> ResolutionActionEnum:
    """Get the action enum."""
    mapping = {
      "resume": ResolutionActionEnum.RESUME,
      "abort": ResolutionActionEnum.ABORT,
      "retry": ResolutionActionEnum.RETRY,
    }
    return mapping.get(self.action, ResolutionActionEnum.RESUME)


class StateResolutionLogResponse(BaseModel):
  """API response model for resolution log entry."""

  id: UUID = Field(..., description="Resolution log ID")
  run_id: UUID = Field(..., description="Protocol run ID")
  operation_id: str = Field(..., description="Failed operation ID")
  operation_description: str = Field(..., description="Description of the operation")
  resolution_type: str = Field(..., description="Type of resolution applied")
  action_taken: str = Field(..., description="Action taken after resolution")
  resolved_at: datetime = Field(..., description="Timestamp of resolution")
  resolved_by: str = Field(..., description="Who resolved")

  @classmethod
  def from_orm_model(cls, log: StateResolutionLog) -> StateResolutionLogResponse:
    """Create from ORM model."""
    return cls(
      id=log.accession_id,
      run_id=log.protocol_run_accession_id,
      operation_id=log.operation_id,
      operation_description=log.operation_description,
      resolution_type=log.resolution_type.value,
      action_taken=log.action_taken.value,
      resolved_at=log.resolved_at,
      resolved_by=log.resolved_by,
    )
