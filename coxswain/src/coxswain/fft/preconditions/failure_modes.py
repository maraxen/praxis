# --- PORT PROVENANCE ---------------------------------------------------------
# Partial lift from praxis/backend/core/simulation/failure_detector.py per the
# W0 recon record 260824_w0_simulation_reuse_verdict (verdict=
# partially_reusable; N4-C port choice). Ported members and source lines:
#   - FailureMode              failure_detector.py:34-47   (pydantic model)
#   - FailureDetectionResult   failure_detector.py:50-61   (pydantic model)
#   - BooleanStateConfig       failure_detector.py:69-80   (stdlib dataclass)
#   - generate_boolean_states  failure_detector.py:83-130  (pure generator)
#
# NOT ported: FailureModeDetector + summarize_failure_modes -- the detector's
# constructor and detect() pull HierarchicalSimulator (failure_detector.py:15)
# whose closure carries praxis.backend.core.tracing / utils.async_run.
# generate_boolean_states depends only on the ported state_models siblings.
# -----------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from coxswain.fft.preconditions.state_models import (
  BooleanLiquidState,
  SimulationState,
)

if TYPE_CHECKING:
  from collections.abc import Iterator


class FailureMode(BaseModel):
  """A detected failure mode for a protocol."""

  initial_state: dict = Field(description="State configuration that causes failure")

  failure_point: str = Field(description="Operation ID where failure occurs")

  failure_type: str = Field(description="Type of failure (tips_not_loaded, no_liquid, etc.)")

  message: str = Field(description="Human-readable failure description")

  suggested_fix: str | None = Field(default=None, description="How to prevent this failure")

  severity: str = Field(default="error", description="Severity: error, warning, info")


class FailureDetectionResult(BaseModel):
  """Result of failure mode detection."""

  failure_modes: list[FailureMode] = Field(default_factory=list)

  states_explored: int = Field(default=0, description="Number of states tested")

  states_pruned: int = Field(default=0, description="Number of states skipped via pruning")

  detection_time_ms: float = Field(default=0.0)

  coverage: float = Field(default=0.0, description="Percentage of state space explored")


@dataclass
class BooleanStateConfig:
  """Configuration for generating boolean states."""

  resources: list[str] = field(default_factory=list)
  """Resource names to consider for deck placement"""

  tip_states: list[bool] = field(default_factory=lambda: [True, False])
  """Possible tip states to test"""

  liquid_states: list[bool] = field(default_factory=lambda: [True, False])
  """Possible liquid states to test"""


def generate_boolean_states(
  config: BooleanStateConfig,
) -> Iterator[SimulationState]:
  """Generate candidate boolean states for testing.

  Uses combinatorial generation but with smart defaults to
  reduce the state space.

  Args:
      config: Configuration for state generation.

  Yields:
      SimulationState objects to test.

  """
  # Generate deck placement combinations
  # For N resources, we have 2^N combinations, but we can prune:
  # - At least one machine must be present (implied by protocol)
  # - Resources mentioned in protocol should be on deck

  # Generate tip state combinations
  for tips_loaded in config.tip_states:
    # Generate liquid state combinations for each resource
    if not config.resources:
      # No resources - just tip state
      state = SimulationState.default_boolean()
      state.tip_state.tips_loaded = tips_loaded
      if tips_loaded:
        state.tip_state.tips_count = 8  # Default single-channel
      yield state
      continue

    # For each combination of liquid presence
    for liquid_combo in product(config.liquid_states, repeat=len(config.resources)):
      state = SimulationState.default_boolean()
      state.tip_state.tips_loaded = tips_loaded
      if tips_loaded:
        state.tip_state.tips_count = 8

      # Set liquid state for each resource
      liquid_state = BooleanLiquidState()
      for resource, has_liquid in zip(config.resources, liquid_combo, strict=False):
        liquid_state.set_has_liquid(resource, has_liquid)
        liquid_state.set_has_capacity(resource, True)  # Always have some capacity
        state.deck_state.place_on_deck(resource)

      state.liquid_state = liquid_state
      yield state
