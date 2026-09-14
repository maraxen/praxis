"""W6 propose-time pre-simulation integration (sim/preview.py).

The preview runs boolean-state generation + contract-driven requirement
inference + failure detection at PROPOSE TIME ONLY, returning failures and
warnings shaped to feed the EXISTING surfaces:

- ``unmet_preconditions`` uses exactly cue 3's string vocabulary, so the value
  drops into ``schema.types.PreconditionExitPayload.unmet_preconditions``
  without translation (W2 gate surface);
- ``warnings`` items carry exactly ``{kind, text}``, the shape
  ``web-repl/shell/coxswain/propose_card.js`` renders as advisory badges
  (W3/W4 card surface).

Authority rule under test here: preview_call takes ONLY a parsed call and the
current deck state -- no probe, no audit sink, no gate, no kernel handle. It
advises; it never decides, never exits a pass, never writes a record.
"""

from dataclasses import replace

import pytest

from coxswain.fft.context import ParsedCall
from coxswain.fft.preconditions.method_contracts import get_contract
from coxswain.fft.preconditions.state_models import SimulationState
from coxswain.schema.types import PreconditionExitPayload
from coxswain.sim.preview import PreviewWarning, preview_call


def _state(tips_loaded: bool = False, tips_count: int = 0) -> SimulationState:
    state = SimulationState.default_boolean()
    state.tip_state.tips_loaded = tips_loaded
    state.tip_state.tips_count = tips_count
    return state


def _aspirate(resource: str = "plate_A") -> ParsedCall:
    return ParsedCall(
        name="aspirate",
        receiver_type="liquid_handler",
        params={"resource": resource, "vol": 50.0},
    )


# --- current-state advisory (cue-3 vocabulary) -----------------------------------


def test_unmet_preconditions_use_cue3_vocabulary() -> None:
    result = preview_call(_aspirate(), _state())  # tips not loaded
    assert "tips_not_loaded" in result.unmet_preconditions


def test_liquid_vocabulary_and_capacity_vocabulary() -> None:
    state = _state(tips_loaded=True, tips_count=8)
    state.liquid_state.set_has_liquid("plate_A", False)
    result = preview_call(_aspirate(), state)
    assert "no_liquid_in_resource" in result.unmet_preconditions

    dispense = ParsedCall(
        name="dispense",
        receiver_type="liquid_handler",
        params={"resource": "plate_B", "vol": 30.0},
    )
    state.liquid_state.set_has_capacity("plate_B", False)
    result = preview_call(dispense, state)
    assert "no_capacity_in_resource" in result.unmet_preconditions


def test_unknown_method_fails_closed_like_cue3() -> None:
    call = ParsedCall(name="frobnicate", receiver_type="liquid_handler")
    result = preview_call(call, _state())
    assert result.known_contract is False
    assert result.unmet_preconditions == ("unknown_method:liquid_handler.frobnicate",)


def test_satisfied_state_yields_no_unmet() -> None:
    result = preview_call(_aspirate(), _state(tips_loaded=True, tips_count=8))
    # Unknown resources are assumed on-deck / with liquid by the ported state
    # models' own convention, mirroring cue 3.
    assert result.unmet_preconditions == ()


# --- requirement inference against METHOD_CONTRACTS -------------------------------


def test_requirement_inference_from_contract() -> None:
    result = preview_call(_aspirate(), _state(tips_loaded=True))
    types = {r.requirement_type for r in result.requirements}
    assert {"tips_required", "resource_on_deck", "liquid_present"} <= types

    on_deck = next(r for r in result.requirements if r.requirement_type == "resource_on_deck")
    assert on_deck.resource == "plate_A"


def test_transfer_infers_both_endpoints() -> None:
    call = ParsedCall(
        name="transfer",
        receiver_type="liquid_handler",
        params={"source": "src_plate", "target": "dst_plate", "vol": 20.0},
    )
    result = preview_call(call, _state(tips_loaded=True))
    endpoints = {
        r.requirement_type: r.resource
        for r in result.requirements
        if r.requirement_type in ("resource_on_deck", "liquid_present", "capacity_available")
    }
    assert endpoints["resource_on_deck"] in ("src_plate", "dst_plate")
    liquid_args = [r.resource for r in result.requirements if r.requirement_type == "liquid_present"]
    capacity_args = [r.details.get("arg") for r in result.requirements if r.requirement_type == "capacity_available"]
    assert liquid_args == ["src_plate"]  # transfer requires_liquid_in="source"
    assert capacity_args == ["target"]  # transfer requires_capacity_in="target"


def test_absent_param_still_recorded_but_not_judged() -> None:
    # Mirrors cue 3: absent values are skipped by resource checks (cue 1/2 own
    # presence), but the requirement is still inferred for the card.
    call = replace(_aspirate(), params={})
    result = preview_call(call, _state(tips_loaded=True))
    on_deck = [r for r in result.requirements if r.requirement_type == "resource_on_deck"]
    assert len(on_deck) == 1 and on_deck[0].resource is None
    assert all(not code.endswith("_not_on_deck") for code in result.unmet_preconditions)


# --- boolean-state failure enumeration ---------------------------------------------


def test_failure_modes_enumerated_with_severity_split() -> None:
    # Current state: tips LOADED, plate_A has NO liquid. Exploration over
    # {tips} x {liquid(plate_A)} must find: the matching failing combo as an
    # imminent ("error") mode, and tip-less combos as potential ("warning").
    state = _state(tips_loaded=True, tips_count=8)
    state.liquid_state.set_has_liquid("plate_A", False)
    result = preview_call(_aspirate(), state)

    errors = [f for f in result.failures if f.severity == "error"]
    warnings_ = [f for f in result.failures if f.severity == "warning"]
    assert errors, "the state-matching failing combo must be imminent"
    assert all(f.failure_type == "no_liquid_in_resource" for f in errors)
    assert warnings_, "tip-less combos must be flagged as potential"
    assert any(f.failure_type == "tips_not_loaded" for f in warnings_)
    assert all(f.failure_point == "aspirate" for f in result.failures)

    # Stats mirror FailureDetectionResult's bookkeeping conventions.
    assert result.states_explored == 4
    assert result.states_explored + result.states_pruned == 4


def test_preview_does_not_mutate_deck_state() -> None:
    state = _state(tips_loaded=True, tips_count=8)
    before = state.tip_state.tips_loaded
    preview_call(_aspirate(), state)
    assert state.tip_state.tips_loaded == before
    assert state.deck_state.on_deck.get("plate_A") is None


def test_deterministic_output() -> None:
    state = _state()
    first = preview_call(_aspirate(), state)
    second = preview_call(_aspirate(), state)
    assert first.unmet_preconditions == second.unmet_preconditions
    assert first.failures == second.failures
    assert first.warnings == second.warnings


# --- feeding existing surfaces ------------------------------------------------------


def test_unmet_drops_into_gate_payload_shape() -> None:
    """Cue-3-shaped feed: the tuple constructs PreconditionExitPayload directly
    (the gate keeps its own authority; this proves shape compatibility only)."""
    result = preview_call(_aspirate(), _state())
    payload = PreconditionExitPayload(
        overridable=True,
        override_prompt="operator asserts otherwise",
        unmet_preconditions=result.unmet_preconditions,
    )
    assert "tips_not_loaded" in payload.unmet_preconditions


def test_warnings_match_card_badge_shape() -> None:
    result = preview_call(_aspirate(), _state())
    assert result.warnings, "unsatisfiable proposal should carry at least one badge"
    for warning in result.warnings:
        assert isinstance(warning, PreviewWarning)
        assert set(warning.to_dict()) == {"kind", "text"}
        assert warning.kind and warning.text


def test_unknown_method_carries_card_warning() -> None:
    call = ParsedCall(name="frobnicate", receiver_type="liquid_handler")
    result = preview_call(call, _state())
    kinds = {w.kind for w in result.warnings}
    assert any("unknown" in k or "precondition" in k for k in kinds)


# --- ProtocolSimulationResult integration (ported simulator model) ------------------


def test_to_protocol_simulation_result_round_trip() -> None:
    from coxswain.sim import SIMULATION_VERSION, ProtocolSimulationResult, is_cache_valid

    state = _state(tips_loaded=True, tips_count=8)
    state.liquid_state.set_has_liquid("plate_A", False)
    preview = preview_call(_aspirate(), state)
    sim_result = preview.to_protocol_simulation_result()

    assert isinstance(sim_result, ProtocolSimulationResult)
    assert sim_result.passed is False
    assert sim_result.inferred_requirements == list(preview.requirements)
    assert sim_result.failure_modes == list(preview.failures)
    assert sim_result.failure_mode_stats["states_explored"] == preview.states_explored
    assert sim_result.simulation_version == SIMULATION_VERSION

    restored = ProtocolSimulationResult.from_cache_dict(sim_result.to_cache_dict())
    assert restored.passed is False
    assert restored.failure_mode_stats["states_explored"] == preview.states_explored

    # Cache guard parity with upstream semantics.
    digest = "deadbeef"
    assert is_cache_valid(restored.simulation_version, digest, digest) is True
    assert is_cache_valid("0.0.0", digest, digest) is False


def test_passing_preview_converts_to_passed_result() -> None:
    preview = preview_call(_aspirate(), _state(tips_loaded=True, tips_count=8))
    sim_result = preview.to_protocol_simulation_result()
    assert sim_result.passed is True
    assert sim_result.violations == []


def test_every_known_contract_gets_explored_states() -> None:
    contract = get_contract("liquid_handler", "aspirate")
    assert contract is not None  # sanity: registry fixture exists for these tests
    preview = preview_call(_aspirate(), _state())
    assert preview.states_explored > 0
    assert pytest.approx(preview.coverage) == 100.0
