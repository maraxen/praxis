"""W6 port-parity tests: every amended-subset symbol exposed by
``coxswain.sim`` behaves per its upstream source of truth
(``praxis/backend/core/simulation/{pipeline,failure_detector,simulator}.py``),
encoded here as concrete expectations WITHOUT importing praxis.backend (the
boundary stays intact even in tests).

Provenance note (W6): the amendment (spec lines ~1185-1190) lists this subset;
commit fdfac2f8 (W2 cue-3 sub-item) had already landed ALL of it under
``coxswain/src/coxswain/fft/preconditions/``. Per the deliverable's "not
already landed by W2" clause there is nothing left to copy, so ``coxswain.sim``
EXPOSES the subset by re-export from that single landed copy -- one definition,
zero divergence (RISK-3's two-implementations failure mode).
"""

from datetime import datetime

import pytest

from coxswain.sim import (
    SIMULATION_VERSION,
    BooleanStateConfig,
    FailureDetectionResult,
    FailureMode,
    HierarchicalSimulationResult,
    InferredRequirement,
    ProtocolSimulationResult,
    StatefulSimulationResult,
    generate_boolean_states,
    is_cache_valid,
)

# --- simulator.py parity -------------------------------------------------------


def test_simulation_version_matches_source() -> None:
    # simulator.py:34 -- SIMULATION_VERSION = "1.0.0"
    assert SIMULATION_VERSION == "1.0.0"


@pytest.mark.parametrize(
    ("cached_version", "source_hash", "current_hash", "expected"),
    [
        ("1.0.0", "abc", "abc", True),  # simulator.py:244-247 both match
        ("0.9.0", "abc", "abc", False),  # :241 version must match
        ("1.0.0", "abc", "def", False),  # :245-247 hash must match
        ("1.0.0", None, None, True),  # hashes unavailable -> version only
        ("1.0.0", "abc", None, True),  # one-sided hash -> not compared
        ("1.0.0", None, "abc", True),
        ("0.9.0", None, None, False),
    ],
)
def test_is_cache_valid_truth_table(
    cached_version: str | None,
    source_hash: str | None,
    current_hash: str | None,
    expected: bool,
) -> None:
    assert is_cache_valid(cached_version, source_hash, current_hash) is expected


def test_protocol_simulation_result_defaults_and_cache_round_trip() -> None:
    # simulator.py:42-88 defaults...
    result = ProtocolSimulationResult()
    assert result.passed is False
    assert result.level_completed == "none"
    assert result.level_failed is None
    assert result.violations == []
    assert result.inferred_requirements == []
    assert result.failure_modes == []
    assert result.simulation_version == SIMULATION_VERSION
    assert isinstance(result.simulated_at, datetime)
    assert result.simulated_at.tzinfo is not None  # timezone.utc stamp

    # ...and the cache round-trip (to_cache_dict / from_cache_dict).
    restored = ProtocolSimulationResult.from_cache_dict(result.to_cache_dict())
    assert restored.passed is False
    assert restored.simulation_version == SIMULATION_VERSION


# --- failure_detector.py parity --------------------------------------------------


def test_failure_mode_defaults() -> None:
    # failure_detector.py:34-47 -- required fields + severity default "error".
    mode = FailureMode(
        initial_state={"tips_loaded": False},
        failure_point="aspirate",
        failure_type="tips_not_loaded",
        message="no tips",
    )
    assert mode.severity == "error"
    assert mode.suggested_fix is None


def test_failure_detection_result_defaults() -> None:
    # failure_detector.py:50-61
    result = FailureDetectionResult()
    assert result.failure_modes == []
    assert result.states_explored == 0
    assert result.states_pruned == 0
    assert result.detection_time_ms == 0.0
    assert result.coverage == 0.0


def test_boolean_state_config_defaults() -> None:
    # failure_detector.py:69-80
    config = BooleanStateConfig()
    assert config.resources == []
    assert config.tip_states == [True, False]
    assert config.liquid_states == [True, False]


def test_generate_boolean_states_no_resources_is_tip_only() -> None:
    # failure_detector.py:100-107 -- no resources -> one state per tip state,
    # tips_count 8 iff loaded (:111).
    states = list(generate_boolean_states(BooleanStateConfig()))
    assert len(states) == 2
    loaded = next(s for s in states if s.tip_state.tips_loaded)
    idle = next(s for s in states if not s.tip_state.tips_loaded)
    assert loaded.tip_state.tips_count == 8
    assert idle.tip_state.tips_count == 0


def test_generate_boolean_states_combinatorial_with_resources() -> None:
    # failure_detector.py:116-130 -- tips x liquid^N states; each resource
    # placed on deck with capacity; liquid flags follow the combo.
    config = BooleanStateConfig(resources=["a", "b"])
    states = list(generate_boolean_states(config))
    assert len(states) == 2 * 2**2

    combo = {
        (s.tip_state.tips_loaded, s.liquid_state.has_liquid["a"], s.liquid_state.has_liquid["b"])
        for s in states
    }
    assert combo == {
        (True, True, True),
        (True, True, False),
        (True, False, True),
        (True, False, False),
        (False, True, True),
        (False, True, False),
        (False, False, True),
        (False, False, False),
    }
    for state in states:
        assert state.deck_state.is_on_deck("a") is True
        assert state.deck_state.is_on_deck("b") is True
        assert state.liquid_state.has_capacity["a"] is True
        assert state.liquid_state.has_capacity["b"] is True


# --- pipeline.py parity ----------------------------------------------------------


def test_inferred_requirement_fields() -> None:
    # pipeline.py:51-57
    req = InferredRequirement(
        requirement_type="tips_required",
        details={"before_operation": "aspirate"},
        inferred_at_level="boolean",
    )
    assert req.resource is None
    assert req.details == {"before_operation": "aspirate"}
    assert req.inferred_at_level == "boolean"


def test_hierarchical_simulation_result_defaults() -> None:
    # pipeline.py:60-83
    result = HierarchicalSimulationResult()
    assert result.passed is False
    assert result.level_completed == "none"
    assert result.level_failed is None
    assert result.violations == []
    assert result.inferred_requirements == []
    assert result.computation_graph is None
    assert result.structural_error is None
    assert result.edge_cases == []
    assert result.execution_time_ms == 0.0


def test_stateful_simulation_result_dataclass_shape() -> None:
    # pipeline.py:91-102 -- stdlib dataclass over ported state models.
    from coxswain.fft.preconditions.state_models import (
        SimulationState,
        StateViolation,
        ViolationType,
    )

    state = SimulationState.default_boolean()
    violation = StateViolation(
        violation_type=ViolationType.NO_LIQUID,
        operation_id="op1",
        method_name="aspirate",
    )
    result = StatefulSimulationResult(final_state=state, violations=[violation])
    assert result.final_state is state
    assert result.exception is None
    bare = StatefulSimulationResult(final_state=state)
    assert bare.violations == []
