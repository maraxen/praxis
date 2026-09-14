"""CUE-3 ported precondition substrate (W2 cue-3 sub-item).

This subpackage is a **ported copy**, not a reimplementation: the W0 recon
check (transduction_log record ``260824_w0_simulation_reuse_verdict``) returned
``verdict=partially_reusable``, and per spec §6.1a/N4-C and §3.2 a
``partially_reusable`` verdict means the named dependency-free subset of
``praxis/backend/core/simulation/`` is PORTED BY COPYING into coxswain --
never imported (NFR-2 bans ``praxis.backend.*`` under ``coxswain/src``, and
AC-2 enforces that with an AST scan over every file in this package).

Ported members (each file carries its own provenance header citing source
paths and lines):

- ``method_contracts``   -- entire module (zero praxis imports upstream).
- ``bounds_analyzer``    -- entire module; only the TYPE_CHECKING-only praxis
  import is replaced by local structural Protocols (adaptation documented
  in-file).
- ``state_models``       -- entire module (stdlib-only upstream, verified by W0).
- ``pipeline_models``        -- pipeline.InferredRequirement,
  pipeline.HierarchicalSimulationResult, pipeline.StatefulSimulationResult.
- ``failure_modes``          -- failure_detector.FailureMode,
  FailureDetectionResult, BooleanStateConfig, generate_boolean_states.
- ``simulation_result``      -- simulator.ProtocolSimulationResult,
  simulator.SIMULATION_VERSION, simulator.is_cache_valid.

Deliberately NOT ported: everything whose closure reaches
``praxis.backend.core.tracing.*`` or ``praxis.backend.utils.async_run``
(HierarchicalSimulator, FailureModeDetector, ProtocolSimulator) -- those are
the "partially" half of the verdict and remain deferred per the W0 record.
"""

from coxswain.fft.preconditions.bounds_analyzer import (
    DEFAULT_DIMENSIONS,
    BoundsAnalyzer,
    ItemizedResourceSpec,
    LoopBounds,
)
from coxswain.fft.preconditions.failure_modes import (
    BooleanStateConfig,
    FailureDetectionResult,
    FailureMode,
    generate_boolean_states,
)
from coxswain.fft.preconditions.method_contracts import (
    METHOD_CONTRACTS,
    EffectType,
    MethodContract,
    get_contract,
    get_contracts_for_type,
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
from coxswain.fft.preconditions.state_models import (
    BooleanLiquidState,
    DeckState,
    ExactLiquidState,
    MachineState,
    SimulationState,
    StateLevel,
    StateViolation,
    SymbolicLiquidState,
    SymbolicVolume,
    TipState,
    ViolationType,
)

__all__ = [
    "DEFAULT_DIMENSIONS",
    "SIMULATION_VERSION",
    "BoundsAnalyzer",
    "BooleanLiquidState",
    "BooleanStateConfig",
    "DeckState",
    "EffectType",
    "ExactLiquidState",
    "FailureDetectionResult",
    "FailureMode",
    "HierarchicalSimulationResult",
    "InferredRequirement",
    "METHOD_CONTRACTS",
    "MachineState",
    "ItemizedResourceSpec",
    "MethodContract",
    "ProtocolSimulationResult",
    "SimulationState",
    "StateLevel",
    "StateViolation",
    "SymbolicLiquidState",
    "SymbolicVolume",
    "TipState",
    "ViolationType",
    "LoopBounds",
    "generate_boolean_states",
    "get_contract",
    "get_contracts_for_type",
    "is_cache_valid",
]
