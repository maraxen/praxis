"""W6 -- ``coxswain.sim``: the amended pre-execution-simulation subset.

Scope authority: spec ``260824_coxswain-mvp-ux-spec.md``, section
"W6 -- Graduated pre-execution simulation", subsection "W6 scope amendment
(2026-08-25)". The amendment names EXACTLY this subset:

- from ``pipeline.py``:          ``InferredRequirement``,
                                 ``HierarchicalSimulationResult``,
                                 ``StatefulSimulationResult``
- from ``failure_detector.py``:  ``FailureMode``, ``FailureDetectionResult``,
                                 ``BooleanStateConfig``,
                                 ``generate_boolean_states``
- from ``simulator.py``:         ``ProtocolSimulationResult``,
                                 ``SIMULATION_VERSION``, ``is_cache_valid``

Provenance / why this file RE-EXPORTS instead of copying: commit ``fdfac2f8``
(W2 cue-3 sub-item) had already ported every symbol above into
``coxswain/src/coxswain/fft/preconditions/`` (files ``pipeline_models.py``,
``failure_modes.py``, ``simulation_result.py``, each with its own provenance
header citing recon record ``260824_w0_simulation_reuse_verdict``). The W6
deliverable scopes new work to "exactly the amended subset NOT ALREADY LANDED
by W2" -- which is therefore the empty set. Copying the definitions again here
would create two divergent copies of safety-relevant models inside one package
(the exact long-term failure RISK-3 warns about), so this package exposes the
single landed copy under the amendment's ``coxswain.sim`` home;
``tests/test_sim_boundary.py`` asserts identity, not copies.

Deliberately NOT exposed: ``HierarchicalSimulator``, ``FailureModeDetector``,
``ProtocolSimulator`` and anything reaching ``praxis.backend.core.tracing.*``
-- the amendment excludes them by name; their tracing closure stays cut.

Propose-time entry point: ``coxswain.sim.preview.preview_call``.
"""

from coxswain.fft.preconditions.failure_modes import (
    BooleanStateConfig,
    FailureDetectionResult,
    FailureMode,
    generate_boolean_states,
)
from coxswain.fft.preconditions.pipeline_models import (
    HierarchicalSimulationResult,
    InferredRequirement,
    StatefulSimulationResult,
)
from coxswain.fft.preconditions.simulation_result import (
    SIMULATION_VERSION,
    ProtocolSimulationResult,
    is_cache_valid,
)

__all__ = [
    "SIMULATION_VERSION",
    "BooleanStateConfig",
    "FailureDetectionResult",
    "FailureMode",
    "HierarchicalSimulationResult",
    "InferredRequirement",
    "ProtocolSimulationResult",
    "StatefulSimulationResult",
    "generate_boolean_states",
    "is_cache_valid",
]
