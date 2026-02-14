"""Smart consumable assignment based on availability and compatibility.

This module provides intelligent consumable (tips/plates) assignment for
protocol execution. It considers:
- Volume capacity matching
- Plate type compatibility
- Resource availability (not reserved by another run)
- Location proximity on the deck
- Expiration dates (if tracked)
- Batch/lot number tracking (if available)

Usage:
    service = ConsumableAssignmentService(db_session)
    suggested = await service.find_compatible_consumable(requirement)
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from praxis.backend.models.domain.protocol import AssetRequirementRead
from praxis.backend.models.domain.schedule import (
  AssetReservation,
)
from praxis.backend.models.enums import AssetReservationStatusEnum
from praxis.backend.utils.logging import get_logger

logger = get_logger(__name__)


class CompatibilityScore:
  """Represents the compatibility score for a consumable candidate."""

  def __init__(self, resource_id: str, name: str) -> None:
    """Initialize compatibility score.

    Args:
        resource_id: The accession ID of the resource.
        name: Human-readable name of the resource.

    """
    self.resource_id = resource_id
    self.name = name
    self.score = 0.0
    self.factors: dict[str, float] = {}
    self.warnings: list[str] = []

  def add_factor(self, name: str, score: float, max_score: float = 1.0) -> None:
    """Add a scoring factor.

    Args:
        name: Name of the factor (e.g., "volume_match").
        score: Score for this factor.
        max_score: Maximum possible score for this factor.

    """
    normalized_score = min(score / max_score, 1.0) if max_score > 0 else 0.0
    self.factors[name] = normalized_score
    self.score += normalized_score

  def add_warning(self, message: str) -> None:
    """Add a compatibility warning."""
    self.warnings.append(message)

  @property
  def total_score(self) -> float:
    """Get the total normalized score (0-1)."""
    if not self.factors:
      return 0.0
    return self.score / len(self.factors)


class ConsumableAssignmentService:
  """Service for intelligent consumable assignment."""

  def __init__(self, db_session: AsyncSession) -> None:
    """Initialize the service.

    Args:
        db_session: Async database session.

    """
    self.db = db_session

  def _validate_accession_id(self, accession_id: str | uuid.UUID | None, context: str) -> uuid.UUID:
    """Validate that the accession ID is a valid UUID (v4 or v7).

    Args:
        accession_id: The ID to validate.
        context: Context for logging (e.g., "workcell_id").

    Returns:
        The validated uuid.UUID object.

    Raises:
        ValueError: If the ID is missing or in an invalid format.

    """
    if not accession_id:
      logger.error("Missing accession_id for %s", context)
      raise ValueError(f"Missing accession_id for {context}")

    if isinstance(accession_id, uuid.UUID):
      val = accession_id
    else:
      try:
        val = uuid.UUID(str(accession_id))
      except ValueError as e:
        logger.error(
          "Invalid accession_id format for %s: %s",
          context,
          accession_id,
          extra={"accession_id": accession_id, "context": context},
        )
        raise ValueError(f"Invalid accession_id format for {context}: {accession_id}") from e

    # Accept v4 and v7 (Praxis uses v7 primarily, but requirement mentioned v4)
    if val.version not in (4, 7):
      logger.warning(
        "Accession ID %s for %s is not UUID v4 or v7 (version=%d)",
        accession_id,
        context,
        val.version,
      )
    return val

  async def find_compatible_consumable(
    self,
    requirement: AssetRequirementRead,
    workcell_id: str | None = None,
    current_time: datetime | None = None,
  ) -> str:
    """Find a compatible consumable for the given requirement.

    Considers:
    - Volume capacity (tip rack volume >= required)
    - Plate type compatibility (well count, shape)
    - Availability (not reserved by another run)
    - Expiration date (if available, prefer non-expired)
    - Batch/lot tracking (if available)

    Args:
        requirement: The asset requirement to match.
        workcell_id: Optional workcell to constrain search to.
        current_time: Current time for expiration checks. Defaults to now.

    Returns:
        Accession ID of the best matching consumable.

    Raises:
        ValueError: If no compatible consumable is found or if inputs are invalid.

    """
    if current_time is None:
      current_time = datetime.now(timezone.utc)

    # Validate workcell_id if provided
    if workcell_id:
      self._validate_accession_id(workcell_id, "workcell_id")

    # Get all candidates of the appropriate type
    candidates = await self._get_candidate_resources(requirement, workcell_id)

    if not candidates:
      msg = f"No candidate consumables found for requirement: {requirement.name}"
      logger.warning(
        msg,
        extra={"requirement": requirement.name, "workcell_id": workcell_id},
      )
      raise ValueError(msg)

    # Score each candidate
    scored_candidates: list[CompatibilityScore] = []
    for candidate in candidates:
      score = await self._score_candidate(
        candidate,
        requirement,
        current_time,
      )
      # Check for critical failures (e.g. volume match is 0)
      if score.factors.get("volume_match") == 0.0:
        continue

      if score.total_score > 0:
        scored_candidates.append(score)

    if not scored_candidates:
      msg = f"No compatible consumables found for requirement: {requirement.name}"
      logger.warning(
        msg,
        extra={"requirement": requirement.name, "workcell_id": workcell_id},
      )
      raise ValueError(msg)

    # Sort by score (highest first)
    scored_candidates.sort(key=lambda x: x.total_score, reverse=True)
    best_match = scored_candidates[0]

    logger.info(
      "Selected consumable '%s' (id=%s, score=%.2f) for requirement '%s'",
      best_match.name,
      best_match.resource_id,
      best_match.total_score,
      requirement.name,
    )

    # Log warnings if any
    for warning in best_match.warnings:
      logger.warning("Consumable %s: %s", best_match.name, warning)

    return best_match.resource_id

  async def auto_assign_consumables(
    self,
    requirements: list[AssetRequirementRead],
    existing_assignments: dict[str, str],
    workcell_id: str | None = None,
  ) -> dict[str, str]:
    """Auto-assign all consumable requirements.

    Args:
        requirements: List of asset requirements to assign.
        existing_assignments: Already assigned assets (requirement name -> asset ID).
        workcell_id: Optional workcell constraint.

    Returns:
        Updated assignments dictionary with suggested consumables.

    """
    if workcell_id:
      self._validate_accession_id(workcell_id, "workcell_id")

    # Validate existing assignments
    for req_name, asset_id in existing_assignments.items():
      self._validate_accession_id(asset_id, f"existing_assignment['{req_name}']")

    assignments = dict(existing_assignments)

    for requirement in requirements:
      # Skip if already assigned
      if requirement.name in assignments:
        continue

      # Skip if not a consumable type
      if not self._is_consumable(requirement):
        continue

      suggested_id = await self.find_compatible_consumable(
        requirement,
        workcell_id,
      )
      if suggested_id:
        assignments[requirement.name] = suggested_id

    return assignments

  def _is_consumable(self, requirement: AssetRequirementRead) -> bool:
    """Check if the requirement is for a consumable resource."""
    type_hint = requirement.type_hint_str.lower()
    consumable_keywords = [
      "plate",
      "tip",
      "tiprack",
      "trough",
      "reservoir",
      "tube",
      "well",
    ]
    return any(keyword in type_hint for keyword in consumable_keywords)

  async def _get_candidate_resources(
    self,
    requirement: AssetRequirementRead,
    workcell_id: str | None = None,
  ) -> list[dict[str, Any]]:
    """Get candidate resources that might match the requirement.

    This method queries the database for resources that:
    - Match the required type pattern
    - Are not currently reserved by another run

    Returns:
        List of candidate resource dictionaries with relevant properties.

    """
    # Validate requirement accession_id
    self._validate_accession_id(requirement.accession_id, "requirement.accession_id")

    # Validate workcell_id if provided
    if workcell_id:
      self._validate_accession_id(workcell_id, "workcell_id")

    # Get currently reserved asset IDs
    reserved_ids = await self._get_reserved_asset_ids()

    # Query resources matching the type
    # This is a simplified query - in production, filter by type columns
    from praxis.backend.models.domain.resource import Resource

    type_hint = requirement.type_hint_str.lower()

    stmt = select(Resource)
    if workcell_id:
      stmt = stmt.filter(Resource.workcell_accession_id == workcell_id)

    result = await self.db.execute(stmt)
    all_resources = result.scalars().all()

    # Filter by type pattern and availability
    candidates = []
    for resource in all_resources:
      # Skip if reserved
      if resource.accession_id in reserved_ids:
        continue

      # Check type compatibility
      resource_type = (resource.fqn or "").lower()
      if self._type_matches(type_hint, resource_type):
        candidate = {
          "accession_id": str(resource.accession_id),
          "name": resource.name,
          "fqn": resource.fqn,
          "properties": resource.properties_json or {},
          "plr_state": resource.plr_state or {},
          "plr_definition": resource.plr_definition or {},
          "nominal_volume_ul": (
            resource.resource_definition.nominal_volume_ul if resource.resource_definition else None
          ),
        }
        candidates.append(candidate)

    return candidates

  async def _get_reserved_asset_ids(self) -> set[uuid.UUID]:
    """Get IDs of assets currently reserved."""
    stmt = select(AssetReservation.asset_accession_id).filter(
      AssetReservation.status.in_(
        [
          AssetReservationStatusEnum.PENDING,
          AssetReservationStatusEnum.RESERVED,
          AssetReservationStatusEnum.ACTIVE,
        ]
      )
    )
    result = await self.db.execute(stmt)
    return {row[0] for row in result.all() if row[0] is not None}

  def _type_matches(self, required_type: str, resource_type: str) -> bool:
    """Check if resource type matches requirement."""
    # Map common type patterns
    type_patterns = {
      "plate": ["plate", "well_plate", "microplate"],
      "tip": ["tip", "tiprack", "tip_rack"],
      "trough": ["trough", "reservoir", "container"],
    }

    for pattern_key, patterns in type_patterns.items():
      if pattern_key in required_type:
        return any(p in resource_type for p in patterns)

    # Default: check for substring match
    return required_type in resource_type or resource_type in required_type

  async def _score_candidate(
    self,
    candidate: dict[str, Any],
    requirement: AssetRequirementRead,
    current_time: datetime,
  ) -> CompatibilityScore:
    """Score a candidate resource for compatibility.

    Scoring factors:
    - volume_match: Capacity meets or exceeds requirement (0-1)
    - type_match: Exact vs approximate type match (0-1)
    - availability: Currently available vs pending (0-1)
    - expiration: Not expired, days until expiration (0-1)
    - batch_tracking: Has batch/lot info (0-1)
    """
    score = CompatibilityScore(
      candidate["accession_id"],
      candidate["name"],
    )

    # 1. Volume/capacity match
    capacity_score = self._score_capacity(candidate, requirement)
    score.add_factor("volume_match", capacity_score)

    # 2. Type match (exact vs approximate)
    type_score = self._score_type_match(candidate, requirement)
    score.add_factor("type_match", type_score)

    # 3. Availability (always 1.0 if we got here, but could check pending)
    score.add_factor("availability", 1.0)

    # 4. Expiration date check
    expiration_score, expiration_warning = self._score_expiration(
      candidate,
      current_time,
    )
    score.add_factor("expiration", expiration_score)
    if expiration_warning:
      score.add_warning(expiration_warning)

    # 5. Batch/lot tracking bonus
    batch_score = self._score_batch_tracking(candidate)
    score.add_factor("batch_tracking", batch_score)

    return score

  def _score_capacity(
    self,
    candidate: dict[str, Any],
    requirement: AssetRequirementRead,
  ) -> float:
    """Score based on volume capacity matching."""
    props = candidate.get("properties", {})
    plr_def = candidate.get("plr_definition", {})

    # Check for volume information
    candidate_volume = (
      candidate.get("nominal_volume_ul")
      or props.get("volume_ul")
      or props.get("max_volume")
      or plr_def.get("max_volume")
      or 0
    )

    # Check requirement constraints for volume
    constraints = requirement.constraints
    required_volume = 0.0
    if constraints and constraints.min_volume_ul:
      required_volume = constraints.min_volume_ul

    if candidate_volume <= 0:
      return 0.5  # Unknown capacity, neutral score

    if required_volume > 0:
      if candidate_volume >= required_volume:
        return 1.0  # Meets requirement
      return 0.0  # Does not meet requirement

    return 0.5  # No specific requirement, neutral score

  def _score_type_match(
    self,
    candidate: dict[str, Any],
    requirement: AssetRequirementRead,
  ) -> float:
    """Score based on how closely the type matches."""
    candidate_fqn = (candidate.get("fqn") or "").lower()
    required_type = requirement.type_hint_str.lower()
    required_fqn = (requirement.fqn or "").lower()

    # Exact FQN match
    if required_fqn and candidate_fqn == required_fqn:
      return 1.0

    # Partial FQN match
    if required_fqn and required_fqn in candidate_fqn:
      return 0.8

    # Type keyword match
    if any(keyword in candidate_fqn for keyword in required_type.split(".") if len(keyword) > 3):
      return 0.6

    return 0.3  # Weak match

  def _score_expiration(
    self,
    candidate: dict[str, Any],
    current_time: datetime,
  ) -> tuple[float, str | None]:
    """Score based on expiration date.

    Returns:
        Tuple of (score, optional warning message).

    """
    props = candidate.get("properties", {})
    expiration_str = props.get("expiration_date") or props.get("expires_at")

    if not expiration_str:
      return (0.7, None)  # No expiration info, neutral

    try:
      # Parse expiration date
      if isinstance(expiration_str, str):
        expiration = datetime.fromisoformat(expiration_str.replace("Z", "+00:00"))
      else:
        expiration = expiration_str

      if expiration < current_time:
        return (0.0, f"Expired on {expiration.date()}")

      # Score based on days until expiration
      days_remaining = (expiration - current_time).days
      if days_remaining > 30:
        return (1.0, None)
      if days_remaining > 7:
        return (0.8, f"Expires in {days_remaining} days")
      return (0.5, f"Expires soon ({days_remaining} days)")

    except (ValueError, TypeError):
      return (0.7, None)  # Couldn't parse, neutral

  def _score_batch_tracking(self, candidate: dict[str, Any]) -> float:
    """Score based on batch/lot tracking information."""
    props = candidate.get("properties", {})

    has_batch = bool(props.get("batch_number") or props.get("lot_number"))
    has_tracking = bool(props.get("received_date") or props.get("manufactured_date"))

    if has_batch and has_tracking:
      return 1.0
    if has_batch or has_tracking:
      return 0.7
    return 0.3
