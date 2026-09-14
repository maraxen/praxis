# --- PORT PROVENANCE ---------------------------------------------------------
# Partial lift from praxis/backend/core/simulation/pipeline.py per the W0 recon
# record 260824_w0_simulation_reuse_verdict (verdict=partially_reusable; N4-C
# port choice). Ported members and their source lines:
#   - InferredRequirement            pipeline.py:51-57  (pydantic model)
#   - HierarchicalSimulationResult   pipeline.py:60-83  (pydantic model)
#   - StatefulSimulationResult       pipeline.py:91-102 (stdlib dataclass)
#
# NOT ported: HierarchicalSimulator and the module's orchestration functions --
# their closure pulls praxis.backend.core.tracing.{executor,recorder} and
# praxis.backend.utils.async_run (pipeline.py:30-36), which NFR-2 forbids here.
# The three result models are self-contained once ``SimulationState`` /
# ``StateViolation`` resolve to the ported state_models sibling.
# -----------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from coxswain.fft.preconditions.state_models import SimulationState, StateViolation


class InferredRequirement(BaseModel):
  """A requirement inferred from simulation."""

  requirement_type: str = Field(description="Type: tips_required, resource_on_deck, liquid_present")
  resource: str | None = Field(default=None, description="Resource involved")
  details: dict[str, Any] = Field(default_factory=dict)
  inferred_at_level: str = Field(description="Level at which this was inferred")


class HierarchicalSimulationResult(BaseModel):
  """Result of hierarchical protocol simulation."""

  passed: bool = Field(default=False, description="Whether simulation passed all levels")

  level_completed: str = Field(default="none", description="Highest level completed without failure")

  level_failed: str | None = Field(default=None, description="Level at which simulation failed")

  violations: list[dict[str, Any]] = Field(default_factory=list, description="All violations found")

  inferred_requirements: list[InferredRequirement] = Field(
    default_factory=list, description="Requirements inferred from simulation"
  )

  computation_graph: dict[str, Any] | None = Field(default=None, description="Extracted computation graph")

  structural_error: str | None = Field(default=None, description="Structural error if Level 0 failed")

  edge_cases: list[dict[str, Any]] = Field(
    default_factory=list, description="Edge cases detected at exact level"
  )

  execution_time_ms: float = Field(default=0.0, description="Total simulation time in milliseconds")


@dataclass
class StatefulSimulationResult:
  """Result of running protocol with stateful tracers."""

  final_state: SimulationState
  """State after execution"""

  violations: list[StateViolation] = field(default_factory=list)
  """Violations detected during execution"""

  exception: Exception | None = None
  """Exception if execution failed"""
