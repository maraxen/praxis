from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.api.dependencies import get_db
from praxis.backend.api.utils.crud_router_factory import create_crud_router
from praxis.backend.models.domain.schedule import (
  AssetReservation,
  ReleaseReservationResponse,
  ResourceReservationStatus,
  ScheduleEntry,
  ScheduleEntryCreate,
  ScheduleEntryRead,
  ScheduleEntryUpdate,
  SchedulePriorityUpdateRequest,
)
from praxis.backend.models.domain.schedule import (
  AssetReservationCreate as AssetReservationListResponse,  # Wait, ListResponse is likely a list container or alias
)
from praxis.backend.models.domain.schedule import (
  AssetReservationRead as AssetReservationResponse,
)
from praxis.backend.models.enums import AssetReservationStatusEnum, ScheduleStatusEnum
from praxis.backend.services.scheduler import schedule_entry_service
from praxis.backend.utils.errors import AccessionNotFoundError, PraxisError

router = APIRouter()

router.include_router(
  create_crud_router(
    service=schedule_entry_service,
    prefix="/entries",
    tags=["Scheduler"],
    create_schema=ScheduleEntryCreate,
    update_schema=ScheduleEntryUpdate,
    read_schema=ScheduleEntryRead,
  ),
)


@router.put(
  "/{schedule_entry_accession_id}/status",
  response_model=ScheduleEntryRead,
  status_code=status.HTTP_200_OK,
  tags=["Scheduler"],
)
async def update_status(
  schedule_entry_accession_id: UUID,
  status_update: ScheduleEntryUpdate,
  db: Annotated[AsyncSession, Depends(get_db)],
) -> ScheduleEntry:
  """Update the status of a schedule entry."""
  if status_update.status is None:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Status must be provided",
    )
  # Handle both enum and string values (Pydantic may pass either)
  if isinstance(status_update.status, str):
    new_status = ScheduleStatusEnum(status_update.status)
  else:
    new_status = status_update.status
  updated_entry = await schedule_entry_service.update_status(
    db=db,
    schedule_entry_accession_id=schedule_entry_accession_id,
    new_status=new_status,
    error_details=status_update.last_error_message,
  )
  if not updated_entry:
    raise HTTPException(status_code=404, detail="Schedule entry not found")
  return updated_entry


@router.put(
  "/{schedule_entry_accession_id}/priority",
  response_model=ScheduleEntryRead,
  status_code=status.HTTP_200_OK,
  tags=["Scheduler"],
)
async def update_priority(
  schedule_entry_accession_id: UUID,
  priority_update: SchedulePriorityUpdateRequest,
  db: Annotated[AsyncSession, Depends(get_db)],
) -> ScheduleEntry:
  """Update the priority of a schedule entry."""
  updated_entry = await schedule_entry_service.update_priority(
    db=db,
    schedule_entry_accession_id=schedule_entry_accession_id,
    new_priority=priority_update.new_priority,
    reason=priority_update.reason,
  )
  if not updated_entry:
    raise HTTPException(status_code=404, detail="Schedule entry not found")
  return updated_entry


def _orm_status_to_api_status(model_status: AssetReservationStatusEnum) -> ResourceReservationStatus:
  """Convert ORM enum to API enum."""
  mapping = {
    AssetReservationStatusEnum.PENDING: ResourceReservationStatus.PENDING,
    AssetReservationStatusEnum.RESERVED: ResourceReservationStatus.RESERVED,
    AssetReservationStatusEnum.ACTIVE: ResourceReservationStatus.ACTIVE,
    AssetReservationStatusEnum.RELEASED: ResourceReservationStatus.RELEASED,
    AssetReservationStatusEnum.EXPIRED: ResourceReservationStatus.EXPIRED,
    AssetReservationStatusEnum.FAILED: ResourceReservationStatus.FAILED,
  }
  return mapping.get(model_status, ResourceReservationStatus.PENDING)


@router.get(
  "/reservations",
  response_model=AssetReservationListResponse,
  status_code=status.HTTP_200_OK,
  tags=["Scheduler", "Reservations"],
)
async def list_reservations(
  db: Annotated[AsyncSession, Depends(get_db)],
  include_released: bool = Query(
    default=False,
    description="Include released reservations in results",
  ),
  asset_key: str | None = Query(
    default=None,
    description="Filter by specific asset key (e.g., 'asset:my_plate')",
  ),
) -> AssetReservationListResponse:
  """List all asset reservations.

  Admin endpoint for inspecting current reservation state. By default, only
  shows active reservations (PENDING, RESERVED, ACTIVE). Set include_released=true
  to see all reservations including released ones.
  """
  # Build query
  query = select(AssetReservation)

  # Filter by status unless include_released
  if not include_released:
    query = query.where(
      AssetReservation.status.in_(
        [
          AssetReservationStatusEnum.PENDING,
          AssetReservationStatusEnum.RESERVED,
          AssetReservationStatusEnum.ACTIVE,
        ]
      )
    )

  # Filter by asset key if provided
  if asset_key:
    query = query.where(AssetReservation.redis_lock_key == asset_key)

  # Order by most recent first
  query = query.order_by(AssetReservation.created_at.desc())

  result = await db.execute(query)
  reservations = result.scalars().all()

  # Count active reservations
  active_count = sum(
    1
    for r in reservations
    if r.status
    in [
      AssetReservationStatusEnum.PENDING,
      AssetReservationStatusEnum.RESERVED,
      AssetReservationStatusEnum.ACTIVE,
    ]
  )

  # Convert to response models
  reservation_responses = [
    AssetReservationResponse(
      accession_id=r.accession_id,
      created_at=r.created_at,
      protocol_run_accession_id=r.protocol_run_accession_id,
      schedule_entry_accession_id=r.schedule_entry_accession_id,
      asset_type=r.asset_type.value if hasattr(r.asset_type, "value") else str(r.asset_type),
      asset_name=r.asset_name,
      asset_accession_id=r.asset_accession_id,
      status=_orm_status_to_api_status(r.status),
      redis_lock_key=r.redis_lock_key,
      reserved_at=r.reserved_at,
      released_at=r.released_at,
      expires_at=r.expires_at,
      required_capabilities=r.required_capabilities_json,
      estimated_usage_duration_ms=r.estimated_usage_duration_ms,
    )
    for r in reservations
  ]

  return AssetReservationListResponse(
    reservations=reservation_responses,
    total_count=len(reservations),
    active_count=active_count,
  )


@router.delete(
  "/reservations/{asset_key:path}",
  response_model=ReleaseReservationResponse,
  status_code=status.HTTP_200_OK,
  tags=["Scheduler", "Reservations"],
)
async def release_reservation(
  asset_key: str,
  db: Annotated[AsyncSession, Depends(get_db)],
  force: bool = Query(
    default=False,
    description="Force release even for reservations in ACTIVE state",
  ),
) -> ReleaseReservationResponse:
  """Release asset reservations by asset key.

  Admin endpoint for manually clearing stuck reservations. This releases
  all active reservations for the specified asset key.

  The asset_key format is typically "type:name", e.g., "asset:my_plate".

  Use force=true to also release ACTIVE reservations (use with caution as
  this may interrupt running protocols).
  """
  # Find active reservations for this asset key
  statuses_to_release = [
    AssetReservationStatusEnum.PENDING,
    AssetReservationStatusEnum.RESERVED,
  ]
  if force:
    statuses_to_release.append(AssetReservationStatusEnum.ACTIVE)

  query = select(AssetReservation).where(
    AssetReservation.redis_lock_key == asset_key,
    AssetReservation.status.in_(statuses_to_release),
  )

  result = await db.execute(query)
  reservations = result.scalars().all()

  if not reservations:
    return ReleaseReservationResponse(
      asset_key=asset_key,
      released=False,
      message=f"No active reservations found for asset key: {asset_key}",
      released_count=0,
    )

  # Release all matching reservations
  released_count = 0
  for reservation in reservations:
    reservation.status = AssetReservationStatusEnum.RELEASED
    reservation.released_at = datetime.now(timezone.utc)
    released_count += 1

  await db.commit()

  return ReleaseReservationResponse(
    asset_key=asset_key,
    released=True,
    message=f"Successfully released {released_count} reservation(s) for asset key: {asset_key}",
    released_count=released_count,
  )


# =============================================================================
# State Resolution Endpoints
# =============================================================================


@router.get(
  "/{schedule_entry_accession_id}/uncertain-state",
  response_model=list,
  status_code=status.HTTP_200_OK,
  tags=["Scheduler", "State Resolution"],
)
async def get_uncertain_states(
  schedule_entry_accession_id: UUID,
  db: Annotated[AsyncSession, Depends(get_db)],
) -> list:
  """Get uncertain states for a failed/paused run.

  Returns the list of state changes that are uncertain due to a failed
  operation. This is used to build a state resolution UI.
  """
  from praxis.backend.services.state_resolution_service import (
    StateResolutionService,
    UncertainStateChangeResponse,
  )

  service = StateResolutionService(db)
  try:
    uncertain = await service.get_uncertain_states(schedule_entry_accession_id)
    return [UncertainStateChangeResponse.from_core(u).model_dump() for u in uncertain]
  except AccessionNotFoundError as e:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
  except (ValueError, PraxisError) as e:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
  "/{schedule_entry_accession_id}/resolve-state",
  status_code=status.HTTP_200_OK,
  tags=["Scheduler", "State Resolution"],
)
async def resolve_state(
  schedule_entry_accession_id: UUID,
  db: Annotated[AsyncSession, Depends(get_db)],
  resolution_request: dict,
) -> dict:
  """Submit a state resolution for a failed operation.

  The user provides their determination of what actually happened during the
  failed operation. This is logged for audit purposes and the simulation
  state is updated accordingly.
  """
  from praxis.backend.services.state_resolution_service import (
    StateResolutionLogResponse,
    StateResolutionRequest,
    StateResolutionService,
  )

  service = StateResolutionService(db)
  try:
    # Parse request
    request = StateResolutionRequest(**resolution_request)
    resolution = request.to_core_resolution()
    action = request.get_action()

    # Apply resolution
    log_entry = await service.resolve_states(
      schedule_entry_accession_id,
      resolution,
      action,
    )
    await db.commit()

    return StateResolutionLogResponse.from_orm_model(log_entry).model_dump()
  except AccessionNotFoundError as e:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
  except (ValueError, PraxisError) as e:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
  "/{schedule_entry_accession_id}/resume",
  status_code=status.HTTP_200_OK,
  tags=["Scheduler", "State Resolution"],
)
async def resume_run(
  schedule_entry_accession_id: UUID,
  db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
  """Resume a paused/failed run after state resolution.

  This transitions the run back to EXECUTING status so that it can continue.
  Must be called after resolve_state to ensure state is correct.
  """
  from praxis.backend.services.state_resolution_service import StateResolutionService

  service = StateResolutionService(db)
  try:
    await service.resume_run(schedule_entry_accession_id)
    return {"status": "resumed", "schedule_entry_id": str(schedule_entry_accession_id)}
  except AccessionNotFoundError as e:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
  except (ValueError, PraxisError) as e:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
  "/{schedule_entry_accession_id}/abort",
  status_code=status.HTTP_200_OK,
  tags=["Scheduler", "State Resolution"],
)
async def abort_run(
  schedule_entry_accession_id: UUID,
  db: Annotated[AsyncSession, Depends(get_db)],
  reason: str | None = Query(default=None, description="Reason for aborting the run"),
) -> dict:
  """Abort a run after state resolution.

  This cancels the run entirely. Use when the user determines the run
  cannot be safely continued.
  """
  from praxis.backend.services.state_resolution_service import StateResolutionService

  service = StateResolutionService(db)
  try:
    await service.abort_run(schedule_entry_accession_id, reason)
    return {"status": "aborted", "schedule_entry_id": str(schedule_entry_accession_id)}
  except AccessionNotFoundError as e:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
  except (ValueError, PraxisError) as e:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
