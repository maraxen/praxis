"""The kernel-side execute entrypoint (W3, spec §3.1 layer 3 + AC-13's kernel
half + §4.5 flag ownership).

This module is the LAST line of defense between a card and the hardware. It
enforces, in Python, in ``coxswain/``, independent of anything the UI does:

1. **Revision guard (§3.1 layer 3)** -- any execute request whose
   ``card_revision`` differs from the ``validated_revision`` stamped by the
   last completed validation pass is rejected with ``blocked:stale_card``
   before the executor is touched. Layer 3 is the authoritative one of the
   three confirm-block layers; the presentation and handler layers exist to
   keep users from REACHING this rejection, not to replace it.
2. **Phrase guard (AC-13 kernel half)** -- for an ``irreversible`` call the
   required FR-3 phrase is derived HERE from the resolved call via
   ``coxswain.phrase.derive_phrase`` and matched under FR-3 normalization. A
   UI that forgets its half of AC-13 cannot reach hardware.
3. **Flag ownership (§4.5)** -- ``EXECUTION_FLAG`` is incremented before the
   PLR dispatch and decremented in a ``finally``, so cue 0's in-process probe
   sees every Coxswain-initiated execution and never sees a stale depth after
   a crash mid-dispatch.
4. **Outcome emission** -- every dispatch terminates in exactly one
   ``ExecutionOutcome`` (``ok`` | ``failed`` | ``aborted_stale``). A failed
   executor raises are captured into a ``failed`` outcome, never allowed to
   escape as an exception with no record.

When the caller supplies the W2 gate, context, and propose-time fingerprint,
the dispatch is routed through ``FftGate.confirm_recheck`` so the FR-6 drift
abort runs immediately before execution; on drift the outcome is
``aborted_stale`` and zero executor calls happen (AC-9's execution side).

Rejections vs outcomes: a guard rejection is NOT an ExecutionOutcome -- no
PLR call was attempted, so no execution status exists to record; the closed
``EXECUTION_STATUSES`` vocabulary stays honest. Rejection codes reuse the
closed disposition strings where one exists (``blocked:stale_card``,
``blocked:audit_unavailable``) and add two phrase codes that live only here.

NFR-1/NFR-2: pure stdlib, CPython-importable, no ``js``, no ``praxis.*``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Final

from coxswain.fft.context import GatePassContext, ParsedCall
from coxswain.fft.gate import FftGate
from coxswain.phrase import derive_phrase, phrase_matches
from coxswain.plr.tool_schema import tier_of
from coxswain.records import EXECUTION_STATUSES, ExecutionOutcome
from coxswain.runtime.execution_flag import EXECUTION_FLAG, ExecutionFlag
from coxswain.schema.types import RiskTier

__all__ = [
    "ExecuteRequest",
    "Rejection",
    "execute",
    "REJECTION_STALE_CARD",
    "REJECTION_PHRASE_REQUIRED",
    "REJECTION_PHRASE_MISMATCH",
]

#: §3.1 layer 3's named disposition, reused verbatim as the rejection code.
REJECTION_STALE_CARD: Final[str] = "blocked:stale_card"

#: Phrase-guard codes. No FftDecision ever carries these -- they are not in
#: the closed §2.4 disposition vocabulary -- because a phrase rejection happens
#: at the execute entrypoint, outside any gate pass.
REJECTION_PHRASE_REQUIRED: Final[str] = "confirmation_phrase_required"
REJECTION_PHRASE_MISMATCH: Final[str] = "confirmation_phrase_mismatch"


@dataclass(frozen=True)
class ExecuteRequest:
    """Everything the entrypoint needs. ``typed_phrase`` arrives from the UI;
    the REQUIRED phrase never does -- it is derived kernel-side."""

    turn_id: str
    session_id: str
    gate_seq: int
    card_revision: int
    validated_revision: int
    parsed_call: ParsedCall
    typed_phrase: str | None = None
    ts: float | None = None


@dataclass(frozen=True)
class Rejection:
    """A guard refusal. Carries turn identity so the shell can surface it as
    a system line joined to the right conversation turn."""

    code: str
    detail: str
    turn_id: str
    gate_seq: int


def revision_guard(request: ExecuteRequest) -> Rejection | None:
    """§3.1 layer 3: equality, not direction. Any difference denies."""
    if request.card_revision != request.validated_revision:
        return Rejection(
            code=REJECTION_STALE_CARD,
            detail=(
                f"card_revision {request.card_revision} != validated_revision "
                f"{request.validated_revision} -- the card was edited after its "
                "last completed validation pass"
            ),
            turn_id=request.turn_id,
            gate_seq=request.gate_seq,
        )
    return None


def phrase_guard(request: ExecuteRequest) -> Rejection | None:
    """AC-13's kernel half. Only ``irreversible`` calls pay this toll."""
    if tier_of(request.parsed_call.name) is not RiskTier.IRREVERSIBLE:
        return None
    verb = _schema_verb(request.parsed_call)
    required = derive_phrase({"verb": verb, "params": request.parsed_call.params})
    typed = request.typed_phrase
    if typed is None:
        return Rejection(
            code=REJECTION_PHRASE_REQUIRED,
            detail=f"an irreversible call requires typing {required!r} to confirm",
            turn_id=request.turn_id,
            gate_seq=request.gate_seq,
        )
    if not phrase_matches(typed, required):
        return Rejection(
            code=REJECTION_PHRASE_MISMATCH,
            detail="the typed confirmation phrase does not match the required phrase",
            turn_id=request.turn_id,
            gate_seq=request.gate_seq,
        )
    return None


def _schema_verb(call: ParsedCall) -> str:
    from coxswain.plr.tool_schema import TOOL_SCHEMA

    spec = TOOL_SCHEMA.get(call.name)
    if spec is None:
        raise ValueError(
            f"no tool schema entry for {call.name!r} -- refusing to derive a "
            "phrase from an unknown call"
        )
    return spec.verb


def execute(
    request: ExecuteRequest,
    *,
    executor: Callable[[ParsedCall], Any],
    gate: FftGate | None = None,
    ctx: GatePassContext | None = None,
    propose_fingerprint: Any = None,
    execution_flag: ExecutionFlag | None = None,
) -> ExecutionOutcome | Rejection:
    """Run one guarded dispatch. Returns a ``Rejection`` when a guard denies
    (zero executor calls), else the terminal ``ExecutionOutcome``.

    ``gate``/``ctx``/``propose_fingerprint`` are optional ONLY so the guards
    are unit-testable in isolation; production wiring always passes all three
    so the FR-6 confirm-time recheck stands between the guards and hardware.
    """
    ts = time.time() if request.ts is None else request.ts

    rejection = revision_guard(request) or phrase_guard(request)
    if rejection is not None:
        return rejection

    flag = execution_flag if execution_flag is not None else EXECUTION_FLAG
    dispatch = _flagged_dispatcher(request, executor, flag, ts)

    if gate is not None and ctx is not None and propose_fingerprint is not None:
        recheck = gate.confirm_recheck(
            request.parsed_call,
            ctx,
            propose_fingerprint=propose_fingerprint,
            executor=dispatch,
        )
        if recheck.outcome is None:
            # The only outcome-less terminal path in confirm_recheck is a
            # broken audit seam (fail closed, NFR-5/FR-9).
            return Rejection(
                code="blocked:audit_unavailable",
                detail="confirm-time audit write was not acknowledged; nothing executed",
                turn_id=request.turn_id,
                gate_seq=recheck.gate_seq,
            )
        assert recheck.outcome.status in EXECUTION_STATUSES
        return recheck.outcome

    return dispatch(request.parsed_call)


def _flagged_dispatcher(
    request: ExecuteRequest,
    executor: Callable[[ParsedCall], Any],
    flag: ExecutionFlag,
    ts: float,
) -> Callable[[ParsedCall], ExecutionOutcome]:
    """Wrap the raw PLR executor: increment before, decrement in a finally,
    capture failures as ``failed`` outcomes instead of escaping exceptions."""

    def dispatch(call: ParsedCall) -> ExecutionOutcome:
        try:
            with flag.active():
                result = executor(call)
        except Exception as exc:  # noqa: BLE001 -- a raise here must become a RECORD
            return ExecutionOutcome(
                turn_id=request.turn_id,
                gate_seq=request.gate_seq,
                status="failed",
                detail=f"{type(exc).__name__}: {exc}",
                ts=ts,
            )
        if isinstance(result, ExecutionOutcome):
            return result
        return ExecutionOutcome(
            turn_id=request.turn_id,
            gate_seq=request.gate_seq,
            status="ok",
            detail=None,
            ts=ts,
        )

    return dispatch
