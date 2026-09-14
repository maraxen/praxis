"""W6 -- propose-time pre-simulation (spec "Graduated pre-execution
simulation" + scope amendment).

``preview_call(parsed_call, deck_state)`` answers, BEFORE any gate pass: given
this call and the deck as we see it right now, what would simulation say?

It composes exactly the amended subset's moving parts:

1. **Requirement inference against METHOD_CONTRACTS** -- contract-driven
   counterpart of pipeline.py's violation-driven ``_infer_requirements``
   (pipeline.py:441-478): ``requires_tips`` -> ``tips_required``,
   ``requires_on_deck`` -> ``resource_on_deck``, ``requires_liquid_in`` ->
   ``liquid_present``, plus ``capacity_available`` for ``requires_capacity_in``
   (contracts express capacity; upstream's three-type vocabulary comes from
   violation classes that have no capacity member -- deviation documented in
   the daily record). Uses the ported ``InferredRequirement``.
2. **Boolean-state generation** -- the ported ``generate_boolean_states`` /
   ``BooleanStateConfig`` over the call's resource arguments.
3. **Failure detection** -- a pure predicate evaluation of the contract per
   generated state, mirroring cue 3's check order and STRING vocabulary
   exactly, emitting ported ``FailureMode`` records. This is the propose-time,
   no-execution stand-in for what ``FailureModeDetector`` does by re-running
   HierarchicalSimulator (excluded from the subset; its tracing closure stays
   cut). Severity splits graduated: a failing state that MATCHES the current
   deck is imminent (``error``); other enumerated combos are potential
   (``warning``).

Authority boundary (binding): the preview takes ONLY the parsed call and the
current deck state. No probe, no audit sink, no gate, no kernel handle. It
FEEDS existing surfaces and decides nothing:

- ``unmet_preconditions`` strings drop into
  ``schema.types.PreconditionExitPayload.unmet_preconditions`` verbatim;
- ``warnings`` items serialize to exactly ``{kind, text}``, the badge shape
  ``web-repl/shell/coxswain/propose_card.js`` renders.

It never exits a pass, never stamps an ``FftDecision``, never writes a record:
propose-time advisory only, zero new kernel-side authority.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from coxswain.fft.context import ParsedCall
from coxswain.fft.preconditions.failure_modes import (
    BooleanStateConfig,
    FailureMode,
    generate_boolean_states,
)
from coxswain.fft.preconditions.method_contracts import MethodContract, get_contract
from coxswain.fft.preconditions.pipeline_models import InferredRequirement
from coxswain.fft.preconditions.simulation_result import ProtocolSimulationResult
from coxswain.fft.preconditions.state_models import (
    BooleanLiquidState,
    SimulationState,
    StateLevel,
)

__all__ = ["PreviewResult", "PreviewWarning", "preview_call"]

_LEVEL = StateLevel.BOOLEAN.value


@dataclass(frozen=True)
class PreviewWarning:
    """One advisory badge for the W3/W4 card surface ({kind, text})."""

    kind: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "text": self.text}


@dataclass(frozen=True)
class PreviewResult:
    """Propose-time pre-simulation output. Advisory only."""

    receiver_type: str
    method_name: str
    known_contract: bool
    #: Cue-3 vocabulary strings; feeds PreconditionExitPayload untranslated.
    unmet_preconditions: tuple[str, ...]
    #: Contract-inferred requirements (ported InferredRequirement).
    requirements: tuple[InferredRequirement, ...]
    #: Enumerated failure modes across explored boolean states.
    failures: tuple[FailureMode, ...]
    #: {kind, text} badges for the propose card.
    warnings: tuple[PreviewWarning, ...]
    states_explored: int = 0
    states_pruned: int = 0
    coverage: float = 0.0
    detection_time_ms: float = 0.0

    def to_protocol_simulation_result(self) -> ProtocolSimulationResult:
        """Summarize as the ported simulator result model (cacheable shape)."""
        imminent = any(f.severity == "error" for f in self.failures)
        return ProtocolSimulationResult(
            passed=self.known_contract and not self.unmet_preconditions and not imminent,
            level_completed="none" if self.unmet_preconditions or imminent else "boolean",
            level_failed="boolean" if self.unmet_preconditions or imminent else None,
            violations=[
                {"type": code, "method_name": self.method_name}
                for code in self.unmet_preconditions
            ],
            inferred_requirements=list(self.requirements),
            failure_modes=list(self.failures),
            failure_mode_stats={
                "states_explored": self.states_explored,
                "states_pruned": self.states_pruned,
                "coverage": self.coverage,
                "detection_time_ms": self.detection_time_ms,
            },
        )


# --- contract predicate (mirrors cues.cue_precondition's checks/vocabulary) -----


def _violations_for(
    contract: MethodContract, call: ParsedCall, state: SimulationState
) -> list[str]:
    """Unmet precondition codes for one state, in cue 3's check order and
    string vocabulary (cues.py:253-289) so both surfaces share one language."""
    codes: list[str] = []

    if contract.requires_tips and not state.tip_state.tips_loaded:
        codes.append("tips_not_loaded")
    if (
        contract.requires_tips_count is not None
        and state.tip_state.tips_count < contract.requires_tips_count
    ):
        codes.append("insufficient_tips")

    for arg in contract.requires_on_deck:
        resource = call.params.get(arg)
        if resource is not None and not state.deck_state.is_on_deck(resource):
            codes.append(f"{arg}_not_on_deck")

    liquid = state.liquid_state if isinstance(state.liquid_state, BooleanLiquidState) else None
    if liquid is not None:
        if contract.requires_liquid_in is not None:
            resource = call.params.get(contract.requires_liquid_in)
            if resource is not None and not liquid.check_has_liquid(resource):
                codes.append(f"no_liquid_in_{contract.requires_liquid_in}")
        if contract.requires_capacity_in is not None:
            resource = call.params.get(contract.requires_capacity_in)
            if resource is not None and not liquid.check_has_capacity(resource):
                codes.append(f"no_capacity_in_{contract.requires_capacity_in}")

    machine = state.machine_states.get(call.receiver_type)
    if contract.requires_machine_ready and machine is not None and not machine.is_ready:
        codes.append("machine_not_ready")
    if (
        contract.requires_temperature_range is not None
        and machine is not None
        and machine.temperature is not None
    ):
        lo, hi = contract.requires_temperature_range
        if not lo <= machine.temperature <= hi:
            codes.append("temperature_out_of_range")

    return codes


# --- requirement inference (contract-driven _infer_requirements counterpart) ----


def _infer_requirements(
    contract: MethodContract, call: ParsedCall
) -> tuple[InferredRequirement, ...]:
    requirements: list[InferredRequirement] = []

    if contract.requires_tips:
        requirements.append(
            InferredRequirement(
                requirement_type="tips_required", inferred_at_level=_LEVEL
            )
        )
    for arg in contract.requires_on_deck:
        requirements.append(
            InferredRequirement(
                requirement_type="resource_on_deck",
                resource=call.params.get(arg),
                details={"arg": arg},
                inferred_at_level=_LEVEL,
            )
        )
    if contract.requires_liquid_in is not None:
        requirements.append(
            InferredRequirement(
                requirement_type="liquid_present",
                resource=call.params.get(contract.requires_liquid_in),
                details={"arg": contract.requires_liquid_in},
                inferred_at_level=_LEVEL,
            )
        )
    if contract.requires_capacity_in is not None:
        requirements.append(
            InferredRequirement(
                requirement_type="capacity_available",
                resource=call.params.get(contract.requires_capacity_in),
                details={"arg": contract.requires_capacity_in},
                inferred_at_level=_LEVEL,
            )
        )

    return tuple(requirements)


# --- boolean-state exploration helpers -------------------------------------------


def _resource_args(contract: MethodContract) -> tuple[str, ...]:
    args: list[str] = [*contract.requires_on_deck]
    for name in (contract.requires_liquid_in, contract.requires_capacity_in):
        if name is not None and name not in args:
            args.append(name)
    return tuple(args)


def _state_key(state: SimulationState) -> str:
    """Upstream FailureModeDetector._state_key pruning key
    (failure_detector.py:275-290)."""
    parts = [
        f"tips={state.tip_state.tips_loaded}",
        f"count={state.tip_state.tips_count}",
    ]
    if isinstance(state.liquid_state, BooleanLiquidState):
        for resource, has_liquid in sorted(state.liquid_state.has_liquid.items()):
            parts.append(f"{resource}:liq={has_liquid}")
    return "|".join(parts)


def _state_to_dict(state: SimulationState) -> dict[str, Any]:
    """Upstream FailureModeDetector._state_to_dict reporting shape
    (failure_detector.py:292-306)."""
    result: dict[str, Any] = {
        "tips_loaded": state.tip_state.tips_loaded,
        "tips_count": state.tip_state.tips_count,
        "level": state.level.value,
    }
    if isinstance(state.liquid_state, BooleanLiquidState):
        result["liquid"] = dict(state.liquid_state.has_liquid)
        result["capacity"] = dict(state.liquid_state.has_capacity)
    result["on_deck"] = dict(state.deck_state.on_deck)
    return result


def _matches_current(
    state: SimulationState, current: SimulationState, resources: tuple[str, ...]
) -> bool:
    """Whether an explored combo agrees with the actual deck on every axis the
    exploration varies (tips + per-resource boolean liquid)."""
    if bool(state.tip_state.tips_loaded) != bool(current.tip_state.tips_loaded):
        return False
    current_liquid = (
        current.liquid_state if isinstance(current.liquid_state, BooleanLiquidState) else None
    )
    if current_liquid is None:
        return True
    explored_liquid = state.liquid_state
    assert isinstance(explored_liquid, BooleanLiquidState)  # generator invariant
    return all(
        explored_liquid.has_liquid.get(r) == current_liquid.has_liquid.get(r, True)
        for r in resources
    )


_FIX_HINTS: dict[str, str] = {
    "tips_not_loaded": "load tips before running this method",
    "insufficient_tips": "load the required number of tips",
}


def _humanize(code: str, call: ParsedCall) -> str:
    if code == "tips_not_loaded":
        return "Tips are not loaded."
    if code == "insufficient_tips":
        return "Not enough tips are loaded for this method."
    if code.endswith("_not_on_deck"):
        return f"'{code[: -len('_not_on_deck')]}' is not on the deck."
    if code.startswith("no_liquid_in_"):
        arg = code[len("no_liquid_in_"):]
        return f"'{arg}' has no liquid."
    if code.startswith("no_capacity_in_"):
        arg = code[len("no_capacity_in_"):]
        return f"'{arg}' has no remaining capacity."
    if code == "machine_not_ready":
        return f"{call.receiver_type} is not ready."
    if code == "temperature_out_of_range":
        return f"{call.receiver_type} temperature is outside the method's required range."
    if code.startswith("unknown_method:"):
        name = code[len("unknown_method:") :]
        return f"No simulation contract exists for {name}; Coxswain cannot vouch for it."
    return f"Unmet precondition: {code}."


def preview_call(call: ParsedCall, deck_state: SimulationState) -> PreviewResult:
    """Run the propose-time pre-simulation for one parsed call."""
    start = time.perf_counter()

    contract = get_contract(call.receiver_type, call.name)
    if contract is None:
        # Fail closed like cue 3 -- but advisory: the gate still owns the exit.
        code = f"unknown_method:{call.receiver_type}.{call.name}"
        return PreviewResult(
            receiver_type=call.receiver_type,
            method_name=call.name,
            known_contract=False,
            unmet_preconditions=(code,),
            requirements=(),
            failures=(),
            warnings=(PreviewWarning(kind="precondition", text=_humanize(code, call)),),
            detection_time_ms=(time.perf_counter() - start) * 1000,
        )

    requirements = _infer_requirements(contract, call)

    # Current-state advisory: imminent, cue-3-vocabulary results.
    current_unmet = tuple(_violations_for(contract, call, deck_state))

    # Boolean-state exploration over the call's resource arguments.
    resources = tuple(
        value
        for arg in _resource_args(contract)
        if (value := call.params.get(arg)) is not None
    )
    config = BooleanStateConfig(resources=list(resources))

    failures: list[FailureMode] = []
    pruned_states: set[str] = set()
    states_explored = 0
    states_pruned = 0

    for state in generate_boolean_states(config):
            key = _state_key(state)
            if key in pruned_states:
                states_pruned += 1
                continue
            pruned_states.add(key)
            states_explored += 1

            codes = _violations_for(contract, call, state)
            if not codes:
                continue
            primary = codes[0]
            failures.append(
                FailureMode(
                    initial_state=_state_to_dict(state),
                    failure_point=call.name,
                    failure_type=primary,
                    message=(
                        f"{call.receiver_type}.{call.name} fails when: "
                        f"{', '.join(codes)}"
                    ),
                    suggested_fix=_FIX_HINTS.get(primary),
                    severity="error" if _matches_current(state, deck_state, resources) else "warning",
                )
            )

    total_candidates = len(config.tip_states) * (2 ** len(config.resources))
    coverage = (
        (states_explored / total_candidates * 100) if total_candidates > 0 else 100.0
    )

    warnings = [PreviewWarning(kind="precondition", text=_humanize(code, call)) for code in current_unmet]
    potential = [f for f in failures if f.severity == "warning"]
    if potential:
        warnings.append(
            PreviewWarning(
                kind="failure_mode",
                text=(
                    f"{len(potential)} other starting state(s) could also make "
                    f"this fail (e.g. {potential[0].failure_type})."
                ),
            )
        )

    return PreviewResult(
        receiver_type=call.receiver_type,
        method_name=call.name,
        known_contract=True,
        unmet_preconditions=current_unmet,
        requirements=requirements,
        failures=tuple(failures),
        warnings=tuple(warnings),
        states_explored=states_explored,
        states_pruned=states_pruned,
        coverage=coverage,
        detection_time_ms=(time.perf_counter() - start) * 1000,
    )
