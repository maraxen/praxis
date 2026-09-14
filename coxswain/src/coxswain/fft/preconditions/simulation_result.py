# --- PORT PROVENANCE ---------------------------------------------------------
# Partial lift from praxis/backend/core/simulation/simulator.py per the W0 recon
# record 260824_w0_simulation_reuse_verdict (verdict=partially_reusable; N4-C
# port choice). Ported members and their source lines:
#   - SIMULATION_VERSION           simulator.py:32-34
#   - ProtocolSimulationResult     simulator.py:42-88 (pydantic model incl.
#                                  to_cache_dict / from_cache_dict)
#   - is_cache_valid               simulator.py:224-249 (pure function)
#
# NOT ported: ProtocolSimulator + the analyze_protocol* conveniences -- they
# construct HierarchicalSimulator / FailureModeDetector (simulator.py:139-140),
# whose closures carry praxis.backend.core.tracing / utils.async_run, banned by
# NFR-2. The result model resolves InferredRequirement / FailureMode against the
# ported siblings. ``initial_state`` field typed dict[str, Any] matches the
# source's loose dict usage in this subset's consumers.
# -----------------------------------------------------------------------------

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from coxswain.fft.preconditions.failure_modes import FailureMode
from coxswain.fft.preconditions.pipeline_models import InferredRequirement

# Version string for cache invalidation
# Bump this when simulation logic changes
SIMULATION_VERSION = "1.0.0"


class ProtocolSimulationResult(BaseModel):
  """Complete simulation result for a protocol.

  This model is designed to be cached with the protocol definition.
  """

  # Simulation outcome
  passed: bool = Field(default=False, description="Whether protocol passed all validation")

  # Hierarchical simulation results
  level_completed: str = Field(default="none", description="Highest level completed")
  level_failed: str | None = Field(default=None, description="Level where failure occurred")
  structural_error: str | None = Field(default=None, description="Structural error if any")

  # Violations found
  violations: list[dict[str, Any]] = Field(
    default_factory=list, description="All violations from simulation"
  )

  # Inferred requirements
  inferred_requirements: list[InferredRequirement] = Field(
    default_factory=list, description="Requirements inferred from simulation"
  )

  # Failure modes
  failure_modes: list[FailureMode] = Field(
    default_factory=list, description="Enumerated failure modes"
  )

  # Detection statistics
  failure_mode_stats: dict[str, Any] = Field(
    default_factory=dict, description="Failure detection statistics"
  )

  # Metadata
  simulation_version: str = Field(default=SIMULATION_VERSION)
  simulated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
  execution_time_ms: float = Field(default=0.0)

  def to_cache_dict(self) -> dict[str, Any]:
    """Convert to dictionary for caching (source docstring said 'database
    caching'; the coxswain consumer caches outside any DB)."""
    return self.model_dump(mode="json")

  @classmethod
  def from_cache_dict(cls, data: dict[str, Any]) -> ProtocolSimulationResult:
    """Reconstruct from cached dictionary."""
    return cls.model_validate(data)


def is_cache_valid(
  cached_version: str | None,
  source_hash: str | None,
  current_source_hash: str | None,
) -> bool:
  """Check if cached simulation result is still valid.

  Args:
      cached_version: Version string from cache.
      source_hash: Source hash from cache.
      current_source_hash: Current source hash.

  Returns:
      True if cache is valid and can be used.

  """
  # Version must match
  if cached_version != SIMULATION_VERSION:
    return False

  # Source hash must match (if available)
  if source_hash is not None and current_source_hash is not None:
    if source_hash != current_source_hash:
      return False

  return True
