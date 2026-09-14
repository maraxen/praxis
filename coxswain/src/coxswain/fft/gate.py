"""FftGate: pass orchestration, gate_seq management, re-entry at the exited
cue, confirm-time recheck restricted to cues {0, 3}, override enforcement,
and fail-closed audit handling (W2; spec §4.x work item "FFT gate
extensions").

Sequencing contract (F4-locked):
- ``initial_pass`` sweeps cues 0-3 in order; every verdict is written to the
  audit sink BEFORE the pass advances, and a failed write (False or raise)
  stops the pass with ``blocked:audit_unavailable`` -- later cues are never
  reached after a broken seam.
- A pass that evaluates cue 3 -- whether cue 3 continues or exits -- emits
  exactly one ``StalenessFingerprint``, recorded via the same fail-closed
  seam (FR-6/C23: the compared fields are literally cue 0's and cue 3's
  outputs on every pass; an override path still needs a propose-time anchor).
  Passes stopped at cues 0-2 emit none. A completing pass's terminal ``pass``
  decision references the capture's id.
- ``re_enter`` restarts the sweep AT the cue that exited (FR-8), under the
  caller's choice of start cue, with category ``re_entry``.
- ``confirm_recheck`` re-runs EXACTLY {0, 3} (FR-6): concurrency is re-read,
  a fresh fingerprint is captured and compared against the propose-time one
  via ``fingerprint.compare`` -- the only sanctioned comparison -- and any
  difference aborts BEFORE dispatch: zero executor calls on every stale path.
- Overrides are scoped by ``schema.types.OVERRIDABLE_CUES`` (exactly {3}) via
  ``request_override``; the gate widens nothing.

The audit ack window (``KERNEL_RTT_TIMEOUT_MS``) is W5's writer policy; this
module's synchronous seam treats an explicit False and a raise identically:
unavailable -> blocked.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Final

from coxswain.fft import cues, fingerprint
from coxswain.fft.context import AuditSink, GatePassContext, ParsedCall
from coxswain.records import (
    ExecutionOutcome,
    FftDecision,
    StalenessFingerprint,
)
from coxswain.schema.types import OVERRIDABLE_CUES, request_override

__all__ = ["CONFIRM_RECHECK_CUES", "FftGate", "GateOutcome"]

#: FR-6's confirm-time re-check is restricted to exactly these cues.
CONFIRM_RECHECK_CUES: Final[frozenset[int]] = frozenset({cues.CUE_CONCURRENCY, cues.CUE_PRECONDITION})


#: F4-locked cue evaluation order for a full sweep.
_PASS_ORDER: Final[tuple[int, ...]] = (
    cues.CUE_CONCURRENCY,
    cues.CUE_COMPLETENESS,
    cues.CUE_GROUNDING,
    cues.CUE_PRECONDITION,
)


@dataclass(frozen=True)
class GateOutcome:
    """One pass's result. ``decisions`` mirrors what reached the audit sink;
    ``fingerprints`` carries the passes' own captures (empty unless the pass
    ran to completion or captured pre-abort); ``outcome`` is set only where
    an ExecutionOutcome exists (drift/concurrency aborts, post-execution)."""

    disposition: str
    gate_seq: int
    decisions: tuple[FftDecision, ...] = ()
    exited_cue: int | None = None
    payload: Any = None
    fingerprints: tuple[StalenessFingerprint, ...] = ()
    resolved_slot_names: tuple[str, ...] = ()
    outcome: ExecutionOutcome | None = None


@dataclass(frozen=True)
class _LastExit:
    """What apply_override() needs to re-stamp the exit as an override."""

    turn_id: str
    session_id: str
    card_revision: int
    gate_seq: int
    cue: int
    category: str


def _audit_ok(fn: Any, *args: Any) -> bool:
    """Call one audit-sink method; any failure is 'unavailable' (NFR-5)."""
    try:
        return bool(fn(*args))
    except Exception:
        return False


class FftGate:
    """Kernel-resident FFT gate. One instance per session; ``gate_seq``
    increments across initial passes, re-entries, and confirm rechecks."""

    def __init__(self, audit: AuditSink | None = None) -> None:
        self._audit = audit
        self._next_seq: int = 0
        self._last_exit: _LastExit | None = None

    # --- seq + plumbing -------------------------------------------------------

    def _take_seq(self) -> int:
        seq = self._next_seq
        self._next_seq += 1
        return seq

    def _sink(self, ctx: GatePassContext) -> AuditSink | None:
        return ctx.audit if ctx.audit is not None else self._audit

    def _stamp(
        self,
        ctx: GatePassContext,
        seq: int,
        category: str,
        *,
        cue: int,
        disposition: str,
        payload_kind: str = "",
        fingerprint_id: str | None = None,
        override_id: str | None = None,
        ts: float | None = None,
    ) -> FftDecision:
        return FftDecision(
            turn_id=ctx.turn_id,
            session_id=ctx.session_id,
            gate_seq=seq,
            cue=cue,
            category=category,
            disposition=disposition,
            payload_kind=payload_kind,
            card_revision=ctx.card_revision,
            ts=ctx.ts if ts is None else ts,
            fingerprint_id=fingerprint_id,
            override_id=override_id,
        )

    def _blocked_outcome(self, seq: int, decisions: tuple[FftDecision, ...]) -> GateOutcome:
        return GateOutcome(disposition="blocked:audit_unavailable", gate_seq=seq, decisions=decisions)

    def _capture(
        self, ctx: GatePassContext, seq: int, *, concurrency_active: bool
    ) -> StalenessFingerprint:
        return fingerprint.capture(
            turn_id=ctx.turn_id,
            gate_seq=seq,
            card_revision=ctx.card_revision,
            concurrency_active=concurrency_active,
            precondition_digest=cues.precondition_digest(ctx.kernel_state),
            taken_at=ctx.ts,
        )

    # --- full passes (initial + re-entry) --------------------------------------

    def initial_pass(self, call: ParsedCall, ctx: GatePassContext) -> GateOutcome:
        return self._run_pass(call, ctx, seq=self._take_seq(), category="initial", start_cue=0)

    def re_enter(
        self, call: ParsedCall, ctx: GatePassContext, *, start_cue: int
    ) -> GateOutcome:
        """FR-8: re-enter at the cue that exited and repeat until that cue's
        unresolved slots are empty -- the caller answers, we resweep from the
        same cue."""
        return self._run_pass(
            call, ctx, seq=self._take_seq(), category="re_entry", start_cue=start_cue
        )

    def _run_pass(
        self,
        call: ParsedCall,
        ctx: GatePassContext,
        *,
        seq: int,
        category: str,
        start_cue: int,
    ) -> GateOutcome:
        sink = self._sink(ctx)
        if sink is None:
            # No seam, no pass: refusing silently would fake an audit trail.
            return self._blocked_outcome(seq, ())

        order = [c for c in _PASS_ORDER if c >= start_cue]
        decisions: list[FftDecision] = []
        resolved: list[str] = []
        effective = call

        for cue in order:
            if cue == cues.CUE_CONCURRENCY:
                verdict: cues.CueVerdict = cues.cue_concurrency(ctx)
            elif cue == cues.CUE_COMPLETENESS:
                verdict = cues.cue_completeness(effective)
            elif cue == cues.CUE_GROUNDING:
                verdict, effective, names = cues.cue_grounding(effective, ctx)
                resolved.extend(names)
            else:
                verdict = cues.cue_precondition(effective, ctx)

            if isinstance(verdict, cues.CueContinue):
                decision = self._stamp(ctx, seq, category, cue=cue, disposition="continue")
                if not _audit_ok(sink.record, decision):
                    return self._blocked_outcome(seq, tuple(decisions))
                decisions.append(decision)
                if cue == cues.CUE_PRECONDITION:
                    break  # full sweep completed
                continue

            decision = self._stamp(
                ctx,
                seq,
                category,
                cue=verdict.cue,
                disposition=verdict.disposition,
                payload_kind=verdict.payload_kind,
            )
            if not _audit_ok(sink.record, decision):
                return self._blocked_outcome(seq, tuple(decisions))
            decisions.append(decision)

            if verdict.cue in OVERRIDABLE_CUES:
                self._last_exit = _LastExit(
                    turn_id=ctx.turn_id,
                    session_id=ctx.session_id,
                    card_revision=ctx.card_revision,
                    gate_seq=seq,
                    cue=verdict.cue,
                    category=category,
                )
            # FR-6/C23: a pass that got cue 3's verdict emits its fingerprint
            # even on that exit -- an override path still needs a propose-time
            # anchor for the confirm-time comparison. Earlier stops have none.
            cap: StalenessFingerprint | None = None
            if verdict.cue == cues.CUE_PRECONDITION:
                cap = self._capture(ctx, seq, concurrency_active=False)
                if not _audit_ok(sink.record_fingerprint, cap):
                    return self._blocked_outcome(seq, tuple(decisions))
            return GateOutcome(
                disposition=verdict.disposition,
                gate_seq=seq,
                decisions=tuple(decisions),
                exited_cue=verdict.cue,
                payload=verdict.payload,
                fingerprints=(cap,) if cap is not None else (),
                resolved_slot_names=tuple(resolved),
            )

        # All cues continued: capture + record the propose-time fingerprint
        # (FR-6), then the terminal decision that references it. The terminal
        # decision lives in the audit trail only -- ``decisions`` on the
        # outcome mirrors the per-cue sweep, cues 0..n.
        cap = self._capture(ctx, seq, concurrency_active=False)
        if not _audit_ok(sink.record_fingerprint, cap):
            return self._blocked_outcome(seq, tuple(decisions))
        terminal = self._stamp(
            ctx,
            seq,
            category,
            cue=cues.CUE_PRECONDITION,
            disposition="pass",
            fingerprint_id=cap.fingerprint_id,
        )
        if not _audit_ok(sink.record, terminal):
            return self._blocked_outcome(seq, tuple(decisions))
        return GateOutcome(
            disposition="pass",
            gate_seq=seq,
            decisions=tuple(decisions),
            fingerprints=(cap,),
            resolved_slot_names=tuple(resolved),
        )

    # --- confirm-time recheck (FR-6 / AC-9 execution side) ----------------------

    def confirm_recheck(
        self,
        call: ParsedCall,
        ctx: GatePassContext,
        *,
        propose_fingerprint: StalenessFingerprint,
        executor: Any,
    ) -> GateOutcome:
        """Re-run exactly {0, 3}; execute only on a clean comparison.

        The fresh fingerprint is captured and recorded first, so even an
        abort carries the kernel state that justified it. Drift (per
        ``fingerprint.compare`` -- the ONLY compared-field enumeration) or a
        flipped/unknown probe aborts before the executor is touched: zero PLR
        calls on every stale path (AC-9)."""
        sink = self._sink(ctx)
        if sink is None:
            return self._blocked_outcome(self._take_seq(), ())
        seq = self._take_seq()

        signal = cues.concurrency_signal(ctx)
        cap = self._capture(ctx, seq, concurrency_active=bool(signal))

        # A flipped OR unreadable probe is staleness (FR-6 compares
        # concurrency_active); False is the clean signal.
        concurrency_flipped = signal is not False
        drifted = concurrency_flipped or not fingerprint.compare(propose_fingerprint, cap)
        if drifted:
            if not _audit_ok(sink.record_fingerprint, cap):
                return self._blocked_outcome(seq, ())
            drift_cue = cues.CUE_CONCURRENCY if concurrency_flipped else cues.CUE_PRECONDITION
            decision = self._stamp(
                ctx,
                seq,
                "confirm_recheck",
                cue=drift_cue,
                disposition="aborted:drift",
                payload_kind="concurrency" if concurrency_flipped else "precondition",
                fingerprint_id=cap.fingerprint_id,
            )
            if not _audit_ok(sink.record, decision):
                return self._blocked_outcome(seq, ())
            outcome = ExecutionOutcome(
                turn_id=ctx.turn_id,
                gate_seq=seq,
                status="aborted_stale",
                detail=(
                    "kernel state changed since proposal"
                    if not concurrency_flipped
                    else "concurrency became active since proposal"
                ),
                ts=ctx.ts,
            )
            return GateOutcome(
                disposition="aborted:drift",
                gate_seq=seq,
                decisions=(decision,),
                fingerprints=(cap,),
                outcome=outcome,
            )

        # Clean: stamp the restricted sweep, then dispatch exactly once.
        decisions: list[FftDecision] = []
        if not _audit_ok(sink.record_fingerprint, cap):
            return self._blocked_outcome(seq, ())
        decision = self._stamp(ctx, seq, "confirm_recheck", cue=cues.CUE_CONCURRENCY, disposition="continue")
        if not _audit_ok(sink.record, decision):
            return self._blocked_outcome(seq, ())
        decisions.append(decision)

        verdict = cues.cue_precondition(call, ctx)
        if isinstance(verdict, cues.CueExit):
            decision = self._stamp(
                ctx,
                seq,
                "confirm_recheck",
                cue=verdict.cue,
                disposition=verdict.disposition,
                payload_kind=verdict.payload_kind,
            )
            if not _audit_ok(sink.record, decision):
                return self._blocked_outcome(seq, ())
            decisions.append(decision)
            return GateOutcome(
                disposition=verdict.disposition,
                gate_seq=seq,
                decisions=tuple(decisions),
                exited_cue=verdict.cue,
                payload=verdict.payload,
                fingerprints=(cap,),
            )

        decision = self._stamp(ctx, seq, "confirm_recheck", cue=cues.CUE_PRECONDITION, disposition="continue")
        if not _audit_ok(sink.record, decision):
            return self._blocked_outcome(seq, ())
        decisions.append(decision)

        terminal = self._stamp(
            ctx,
            seq,
            "confirm_recheck",
            cue=cues.CUE_PRECONDITION,
            disposition="pass",
            fingerprint_id=cap.fingerprint_id,
        )
        if not _audit_ok(sink.record, terminal):
            return self._blocked_outcome(seq, ())
        decisions.append(terminal)

        executed: ExecutionOutcome = executor(call)
        return GateOutcome(
            disposition="pass",
            gate_seq=seq,
            decisions=tuple(decisions),
            fingerprints=(cap,),
            outcome=executed,
        )

    # --- overrides (FR-10 / §3.3) -------------------------------------------------

    def apply_override(self, turn_id: str, justification: str) -> GateOutcome:
        """Re-disposition this gate's most recent overridable (cue-3) exit for
        ``turn_id`` as an override. Requires a non-blank justification."""
        last = self._require_exit(turn_id, justification)
        return self._emit_override(
            turn_id=turn_id,
            gate_seq=last.gate_seq,
            cue=last.cue,
            justification=justification,
            session_id=last.session_id,
            card_revision=last.card_revision,
            category=last.category,
        )

    def apply_override_for_cue(
        self,
        turn_id: str,
        *,
        gate_seq: int,
        cue: int,
        justification: str,
        session_id: str = "",
        card_revision: int = 0,
    ) -> GateOutcome:
        """Explicit-cue form. Eligibility is enforced by
        ``schema.request_override`` against OVERRIDABLE_CUES -- widening it is
        a source change, never a parameter."""
        self._require_justification(justification)
        return self._emit_override(
            turn_id=turn_id,
            gate_seq=gate_seq,
            cue=cue,
            justification=justification,
            session_id=session_id,
            card_revision=card_revision,
            category="re_entry",
        )

    @staticmethod
    def _require_justification(justification: str) -> None:
        if not isinstance(justification, str) or not justification.strip():
            raise ValueError("an override requires a non-empty justification")

    def _require_exit(self, turn_id: str, justification: str) -> _LastExit:
        self._require_justification(justification)
        last = self._last_exit
        if last is None or last.turn_id != turn_id:
            raise ValueError(f"no overridable gate exit recorded for turn {turn_id!r}")
        return last

    def _emit_override(
        self,
        *,
        turn_id: str,
        gate_seq: int,
        cue: int,
        justification: str,
        session_id: str,
        card_revision: int,
        category: str,
    ) -> GateOutcome:
        # request_override raises OverrideNotAllowedError for any cue outside
        # OVERRIDABLE_CUES before any record exists.
        record = request_override(
            turn_id=turn_id,
            gate_seq=gate_seq,
            cue=cue,
            justification=justification,
            ts=time.time(),
        )
        sink = self._audit
        if sink is None:
            return GateOutcome(disposition="blocked:audit_unavailable", gate_seq=gate_seq)
        if not _audit_ok(sink.record_override, record):
            return GateOutcome(disposition="blocked:audit_unavailable", gate_seq=gate_seq)
        decision = FftDecision(
            turn_id=turn_id,
            session_id=session_id,
            gate_seq=gate_seq,
            cue=cue,
            category=category,
            disposition="override:precondition",
            payload_kind="override",
            card_revision=card_revision,
            ts=record.ts,
            fingerprint_id=None,
            override_id=record.override_id,
        )
        if not _audit_ok(sink.record, decision):
            return GateOutcome(disposition="blocked:audit_unavailable", gate_seq=gate_seq)
        return GateOutcome(
            disposition="override:precondition",
            gate_seq=gate_seq,
            decisions=(decision,),
        )
