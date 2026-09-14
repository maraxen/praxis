"""The four FFT cue functions (F4-locked semantics) and the FR-6
precondition digest (W2).

Each cue is ``(parsed_call, grounded_context) -> CueContinue | CueExit``;
the gate stamps the ``FftDecision`` each verdict implies, so cue code stays
decision-free and the audit vocabulary lives in exactly one place.

Fail-closed rules encoded here (NFR-5):
- a probe that raises or answers ``None`` maps to ``blocked:concurrent``,
  never continue;
- a grounding lookup that raises maps to ``clarify:not_found`` -- a user
  clarification, never a silent guess;
- an unknown method contract maps to an unmet ``unknown_method:*``
  precondition (cue 3 cannot vouch for what it cannot enumerate);
- absent parameter values are skipped by cue 3's resource checks, mirroring
  the ported state models' own convention ("unknown resources assumed OK"):
  whether a value should have been present is cue 1/cue 2's question.

The precondition digest covers exactly the kernel-state surface cue 3 reads
(tips, deck, boolean liquid, machine readiness) plus nothing else; it must be
stable for identical states and differ for any state cue 3 would judge
differently. FR-6's *compared* field set is enumerated solely in
``fft/fingerprint.py`` -- this module only produces the digest string.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any

from coxswain.fft.context import GatePassContext, ParsedCall, UnresolvedSlot
from coxswain.fft.preconditions.method_contracts import get_contract
from coxswain.fft.preconditions.state_models import (
    BooleanLiquidState,
    SimulationState,
)
from coxswain.plr.grounding import KernelInstance
from coxswain.schema.types import (
    CompletenessExitPayload,
    ConcurrencyExitPayload,
    GroundingExitPayload,
    PreconditionExitPayload,
)

__all__ = [
    "CueContinue",
    "CueExit",
    "CueVerdict",
    "concurrency_signal",
    "cue_completeness",
    "cue_concurrency",
    "cue_grounding",
    "cue_precondition",
    "precondition_digest",
]


# Normative cue indices (mirrors schema.types.CueId as plain ints: records
# carry plain ints, per §2.4).
CUE_CONCURRENCY = 0
CUE_COMPLETENESS = 1
CUE_GROUNDING = 2
CUE_PRECONDITION = 3


# --- Verdict shapes -----------------------------------------------------------


@dataclass(frozen=True)
class CueContinue:
    """The cue found nothing to ask about; the pass advances."""

    cue: int


@dataclass(frozen=True)
class CueExit:
    """The cue stopped the pass with one closed-vocabulary disposition and
    the payload the JS card layer renders (§3.3 payload types)."""

    cue: int
    disposition: str
    payload_kind: str
    payload: Any


CueVerdict = CueContinue | CueExit


# --- FR-6 precondition digest ---------------------------------------------------


def precondition_digest(state: SimulationState) -> str:
    """Stable digest over the state surface cue 3 judges.

    Boolean-level fields only, canonical JSON, sha256: two states the cue
    would evaluate identically MUST collide here, and any state it would
    judge differently MUST not. Provenance-free by construction."""
    liquid = (
        state.liquid_state if isinstance(state.liquid_state, BooleanLiquidState) else None
    )
    payload = {
        "tips_loaded": bool(state.tip_state.tips_loaded),
        "tips_count": int(state.tip_state.tips_count),
        "deck": sorted((str(name), bool(on)) for name, on in state.deck_state.on_deck.items()),
        "positions": sorted((str(k), str(v)) for k, v in state.deck_state.positions.items()),
        "liquid": sorted(map(tuple, liquid.has_liquid.items())) if liquid else [],
        "capacity": sorted(map(tuple, liquid.has_capacity.items())) if liquid else [],
        "machines": sorted(
            (str(name), bool(ms.is_ready)) for name, ms in state.machine_states.items()
        ),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# --- Cue 0: concurrency (§4.5) --------------------------------------------------


def concurrency_signal(ctx: GatePassContext) -> bool | None:
    """Raw §4.5 read: True/False/None(unknown). A raising probe is an unknown,
    not a 'not active' (NFR-5)."""
    try:
        return ctx.probe.is_active()
    except Exception:
        return None


def cue_concurrency(ctx: GatePassContext) -> CueVerdict:
    signal = concurrency_signal(ctx)
    if signal is True:
        return CueExit(
            CUE_CONCURRENCY,
            "blocked:concurrent",
            "concurrency",
            ConcurrencyExitPayload(concurrency_active=True),
        )
    if signal is None:
        # Unknown == block. There is no continue path through an unreadable
        # probe (NFR-5).
        return CueExit(
            CUE_CONCURRENCY,
            "blocked:concurrent",
            "concurrency_unknown",
            ConcurrencyExitPayload(concurrency_active=None),
        )
    return CueContinue(CUE_CONCURRENCY)


# --- Cue 1: completeness --------------------------------------------------------


def cue_completeness(call: ParsedCall) -> CueVerdict:
    missing = tuple(call.missing_required)
    if missing:
        return CueExit(
            CUE_COMPLETENESS,
            "clarify:incomplete",
            "missing_fields",
            CompletenessExitPayload(missing_fields=missing),
        )
    return CueContinue(CUE_COMPLETENESS)


# --- Cue 2: grounding (FR-7) ------------------------------------------------------


def _safe_resolve(ctx: GatePassContext, slot: UnresolvedSlot) -> tuple[KernelInstance, ...]:
    try:
        return tuple(ctx.instance_source.resolve_slot(slot.reference, slot.resource_type))
    except Exception:
        # A misbehaving source is "no answer", which exits to a user
        # clarification rather than guessing (NFR-5).
        return ()


def cue_grounding(
    call: ParsedCall, ctx: GatePassContext
) -> tuple[CueVerdict, ParsedCall, tuple[str, ...]]:
    """Resolve symbolic slots against live instances.

    Returns ``(verdict, effective_call, resolved_arg_names)``. Cardinality
    decides: 0 exits ``clarify:not_found``, N>1 exits
    ``clarify:disambiguate`` with ALL candidates in as-given order (FR-3),
    and exactly one auto-resolves without exiting -- the binding is applied
    via a fresh ``ParsedCall``, never mutation."""
    params = dict(call.params)
    resolved_names: list[str] = []
    for slot in call.unresolved_slots:
        candidates = _safe_resolve(ctx, slot)
        if len(candidates) == 0:
            return (
                CueExit(
                    CUE_GROUNDING,
                    "clarify:not_found",
                    "not_found",
                    GroundingExitPayload(
                        slot=slot.arg_name,
                        message=f'no {slot.resource_type} matching "{slot.reference}"',
                    ),
                ),
                call,
                tuple(resolved_names),
            )
        if len(candidates) > 1:
            return (
                CueExit(
                    CUE_GROUNDING,
                    "clarify:disambiguate",
                    "candidates",
                    GroundingExitPayload(slot=slot.arg_name, candidates=candidates),
                ),
                call,
                tuple(resolved_names),
            )
        # Exactly one match: auto-resolve, no exit (FR-7's single-match rule).
        params[slot.arg_name] = candidates[0].name
        resolved_names.append(slot.arg_name)

    if not resolved_names:
        return CueContinue(CUE_GROUNDING), call, ()
    effective = replace(call, params=params, unresolved_slots=())
    return CueContinue(CUE_GROUNDING), effective, tuple(resolved_names)


# --- Cue 3: preconditions (W0/N4-C ported contracts) -----------------------------


def cue_precondition(call: ParsedCall, ctx: GatePassContext) -> CueVerdict:
    contract = get_contract(call.receiver_type, call.name)
    if contract is None:
        # Fail closed: an unenumerable method cannot be vouched for. The exit
        # is overridable like any cue-3 exit (OVERRIDABLE_CUES is exactly {3}).
        return CueExit(
            CUE_PRECONDITION,
            "clarify:precondition",
            "precondition",
            PreconditionExitPayload(
                overridable=True,
                override_prompt=(
                    f"no simulation contract exists for "
                    f"{call.receiver_type}.{call.name}; operator may override"
                ),
                unmet_preconditions=(f"unknown_method:{call.receiver_type}.{call.name}",),
            ),
        )

    state = ctx.kernel_state
    unmet: list[str] = []

    if contract.requires_tips and not state.tip_state.tips_loaded:
        unmet.append("tips_not_loaded")
    if (
        contract.requires_tips_count is not None
        and state.tip_state.tips_count < contract.requires_tips_count
    ):
        unmet.append("insufficient_tips")

    for arg in contract.requires_on_deck:
        resource = call.params.get(arg)
        if resource is not None and not state.deck_state.is_on_deck(resource):
            unmet.append(f"{arg}_not_on_deck")

    liquid = (
        state.liquid_state if isinstance(state.liquid_state, BooleanLiquidState) else None
    )
    if liquid is not None:
        if contract.requires_liquid_in is not None:
            resource = call.params.get(contract.requires_liquid_in)
            if resource is not None and not liquid.check_has_liquid(resource):
                unmet.append(f"no_liquid_in_{contract.requires_liquid_in}")
        if contract.requires_capacity_in is not None:
            resource = call.params.get(contract.requires_capacity_in)
            if resource is not None and not liquid.check_has_capacity(resource):
                unmet.append(f"no_capacity_in_{contract.requires_capacity_in}")

    machine = state.machine_states.get(call.receiver_type)
    if contract.requires_machine_ready and machine is not None and not machine.is_ready:
        unmet.append("machine_not_ready")
    if (
        contract.requires_temperature_range is not None
        and machine is not None
        and machine.temperature is not None
    ):
        lo, hi = contract.requires_temperature_range
        if not lo <= machine.temperature <= hi:
            unmet.append("temperature_out_of_range")

    if unmet:
        return CueExit(
            CUE_PRECONDITION,
            "clarify:precondition",
            "precondition",
            PreconditionExitPayload(
                overridable=True,
                override_prompt=(
                    "operator asserts the listed preconditions are met by other means"
                ),
                unmet_preconditions=tuple(unmet),
            ),
        )
    return CueContinue(CUE_PRECONDITION)
