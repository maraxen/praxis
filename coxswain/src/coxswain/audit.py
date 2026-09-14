"""The FR-9 ack-before-disposition audit writer (W5).

Sits between ``FftGate``'s synchronous ``AuditSink`` seam and the L0 IndexedDB
store across ``praxis_coxswain``. Every write issued here carries a
monotonically increasing ``write_id``; the writer returns ``True`` only once
the matching ``audit.ack`` -- sent by ``audit_store.js`` on the IndexedDB
transaction's ``complete`` event, never on request ``success`` -- has arrived,
and always within ``KERNEL_RTT_TIMEOUT_MS`` (§4.7). Timeout, explicit nack, or
a dead transport all collapse to ``False``, which the gate maps to
``blocked:audit_unavailable``: Coxswain never proceeds on an unrecorded
decision (NFR-5, fail closed).

Ordering, not synchrony (FR-9): the write is issued inside the gate pass's own
path and the sink call does not return until durability was claimed or the
window expired.

Validation policy (loud vs. fail-closed):
- A malformed/absent ``turn_id`` or a record outside the closed vocabularies
  is a caller bug and raises ``ValueError`` BEFORE any wire traffic (§2.2
  point 6: absent turn ids and ids that match no open turn are refused).
- Environmental failure (read-only degrade, quota abort, dropped ack, broken
  transport) returns ``False`` with ``last_error`` populated; the gate owns
  the ``blocked:audit_unavailable`` disposition.

The relay is NOT here, on purpose (AC-19/AC-10): relaying is fire-and-forget
browser-side concern in ``relay.js``, never part of this write path.

Transport contract: ``send_write(request)`` issues a durable-write request and
must NOT block on durability; ``pump()`` returns whatever ack/nack messages
are available NOW. ``LoopbackTransport`` is the in-process reference (acks
immediately); the production bridge over BroadcastChannel/worker messaging
implements the same two methods. NFR-1/NFR-2: plain CPython, no ``js``, no
``praxis.*``.
"""

from __future__ import annotations

import re
import time
from dataclasses import asdict
from typing import Any, Final, Iterable, Protocol

from coxswain.persistence.store import CoxswainAuditStore, StoreMode
from coxswain.records import (
    DECISION_CATEGORIES,
    DISPOSITIONS,
    ExecutionOutcome,
    FftDecision,
    OverrideRecord,
    PendingIntent,
    StalenessFingerprint,
)
from coxswain.timing import KERNEL_RTT_TIMEOUT_MS

__all__ = [
    "KERNEL_RTT_TIMEOUT_MS",
    "AckTransport",
    "AuditWriter",
    "LoopbackTransport",
    "ManualAckTransport",
    "RelayRecordingTransport",
    "TURN_ID_PATTERN",
]

#: §2.1: ``cx-<epoch_ms>-<6 base36 chars>``, minted once per submission.
TURN_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^cx-\d+-[0-9a-z]{6}$")

#: Poll quantum while waiting for an ack. Tests inject clock+sleep so this
#: never actually delays them; the WINDOW is what is normative, not the poll
#: rate.
_POLL_INTERVAL_S: Final[float] = 0.001


class AckTransport(Protocol):
    """The durability seam. See module docstring."""

    def send_write(self, request: dict[str, Any]) -> None: ...

    def pump(self) -> Iterable[dict[str, Any]]: ...


class LoopbackTransport:
    """In-process reference transport: every write is acked immediately, so
    the writer's local mirror applies right away. Records everything sent."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.acks: list[dict[str, Any]] = []
        self._ready: list[dict[str, Any]] = []

    def send_write(self, request: dict[str, Any]) -> None:
        self.sent.append(request)
        ack = {"type": "audit.ack", "write_id": request["write_id"]}
        self.acks.append(ack)
        self._ready.append(ack)

    def pump(self) -> list[dict[str, Any]]:
        ready, self._ready = self._ready, []
        return ready


class ManualAckTransport:
    """Test double: sends are recorded; durability responses are MANUAL.

    Starts fully silent -- no write ever gets a response, which exercises the
    dropped-ack timeout by default. ``deliver_acks_automatically()`` switches
    to Loopback-like behaviour; ``hold_all()`` returns to silence;
    ``fail_next_with(error)`` is a one-shot override turning the NEXT write
    into an explicit nack (quota-style abort) under any mode.
    """

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self._ready: list[dict[str, Any]] = []
        self._auto_ack = False
        self._fail_next: str | None = None

    def deliver_acks_automatically(self) -> None:
        self._auto_ack = True

    def hold_all(self) -> None:
        """Every subsequent write gets NO response at all."""
        self._auto_ack = False

    def fail_next_with(self, error: str) -> None:
        """The next write is rejected explicitly (e.g. QuotaExceededError)."""
        self._fail_next = error

    def send_write(self, request: dict[str, Any]) -> None:
        self.sent.append(request)
        write_id = request["write_id"]
        if self._fail_next is not None:
            error, self._fail_next = self._fail_next, None
            self._ready.append({"type": "audit.nack", "write_id": write_id, "error": error})
            return
        if self._auto_ack:
            self._ready.append({"type": "audit.ack", "write_id": write_id})

    def pump(self) -> list[dict[str, Any]]:
        ready, self._ready = self._ready, []
        return ready


class RelayRecordingTransport(LoopbackTransport):
    """Loopback plus a relay fan-out surface the WRITER must never touch.

    ``relay_attempts`` counts invocations of :meth:`attempt_relay`; the FR-9
    contract keeps the relay out of the kernel write path entirely, so healthy
    runs leave it at zero. ``attempt_relay`` itself models an unreachable or
    arbitrarily slow receiver so a regression back into the ack path shows up
    as latency or a raised error, never silence.
    """

    def __init__(self, *, relay_hang: bool = False, relay_delay_s: float = 0.0) -> None:
        super().__init__()
        self.relay_hang = relay_hang
        self.relay_delay_s = relay_delay_s
        self.relay_attempts = 0

    def attempt_relay(self, payload: dict[str, Any]) -> None:
        """Fire-and-forget relay simulation. NOT called by AuditWriter."""
        self.relay_attempts += 1
        if self.relay_hang:
            raise RuntimeError("relay endpoint unreachable (simulated hang)")
        if self.relay_delay_s > 0:
            time.sleep(self.relay_delay_s)


class AuditWriter:
    """Validating, ack-gated writer over a :class:`CoxswainAuditStore`.

    Implements the gate-facing ``AuditSink`` trio (``record`` /
    ``record_fingerprint`` / ``record_override``) synchronously: each call
    submits the durable write, then pumps the transport until the matching
    ack arrives or ``timeout_ms`` elapses.
    """

    def __init__(
        self,
        store: CoxswainAuditStore,
        transport: AckTransport,
        *,
        timeout_ms: int = KERNEL_RTT_TIMEOUT_MS,
        monotonic: Any = time.monotonic,
        sleep: Any = time.sleep,
    ) -> None:
        self._store = store
        self._transport = transport
        self._timeout_ms = timeout_ms
        self._monotonic = monotonic
        self._sleep = sleep
        self._next_write_id = 0
        self._last_error: str | None = None

    # -- introspection ---------------------------------------------------------

    @property
    def last_error(self) -> str | None:
        return self._last_error

    # -- validation helpers ------------------------------------------------------

    @staticmethod
    def _validate_turn_id(turn_id: str) -> None:
        if not isinstance(turn_id, str) or not TURN_ID_PATTERN.match(turn_id):
            raise ValueError(
                f"turn_id {turn_id!r} is absent or malformed; expected "
                "'cx-<epoch_ms>-<6 base36 chars>' (§2.1)"
            )

    def _ensure_writable(self) -> bool:
        if self._store.mode is not StoreMode.READ_WRITE:
            self._last_error = (
                "audit store is read-only: "
                f"{self._store.status_message or 'schema-version degraded'}"
            )
            return False
        return True

    def _require_open_turn(self, turn_id: str) -> None:
        record = self._store.get_turn(turn_id)
        if record is None or record.state != "open":
            raise ValueError(
                f"no open turn {turn_id!r} in the audit store; refusing to "
                "persist a record that matches nothing (§2.2 point 6)"
            )

    @staticmethod
    def _validate_decision(decision: Any) -> None:
        if not isinstance(decision, FftDecision):
            raise TypeError(f"record() requires an FftDecision, got {type(decision)!r}")
        if decision.category not in DECISION_CATEGORIES:
            raise ValueError(
                f"category {decision.category!r} is outside the closed vocabulary"
            )
        if decision.disposition not in DISPOSITIONS:
            raise ValueError(
                f"disposition {decision.disposition!r} is outside the closed vocabulary"
            )

    @staticmethod
    def _validate_fingerprint(fingerprint: Any) -> None:
        if not isinstance(fingerprint, StalenessFingerprint):
            raise TypeError(
                f"record_fingerprint() requires a StalenessFingerprint, got {type(fingerprint)!r}"
            )

    @staticmethod
    def _validate_override(record: Any) -> None:
        if not isinstance(record, OverrideRecord):
            raise TypeError(
                f"record_override() requires an OverrideRecord, got {type(record)!r}"
            )

    # -- the FR-9 core -------------------------------------------------------------

    def _await_ack(self, write_id: int) -> bool:
        """Pump until THIS write's ack/nack arrives or the RTT window closes.

        The transport is pumped BEFORE the deadline check on every iteration:
        an ack already in flight is never mistaken for a timeout."""
        deadline = self._monotonic() + self._timeout_ms / 1000.0
        while True:
            for message in self._transport.pump():
                if message.get("write_id") != write_id:
                    continue  # a resolved neighbour write; consume and move on
                mtype = message.get("type")
                if mtype == "audit.ack":
                    return True
                if mtype == "audit.nack":
                    self._last_error = (
                        f"audit store rejected write {write_id}: {message.get('error')}"
                    )
                    return False
            if self._monotonic() >= deadline:
                self._last_error = (
                    f"audit.ack for write {write_id} did not arrive within "
                    f"{self._timeout_ms} ms (KERNEL_RTT_TIMEOUT_MS)"
                )
                return False
            self._sleep(_POLL_INTERVAL_S)

    def _submit(self, kind: str, turn_id: str, payload: dict[str, Any], apply_local: Any) -> bool:
        """Issue the durable write INSIDE the caller's own path, await its ack
        within the window, and only then mirror it into the local aggregate --
        so the kernel-side view never claims a record the store does not hold."""
        self._next_write_id += 1
        request = {
            "type": "audit.write",
            "write_id": self._next_write_id,
            "kind": kind,
            "turn_id": turn_id,
            "payload": payload,
        }
        try:
            self._transport.send_write(request)
        except Exception as exc:
            self._last_error = f"audit transport unavailable: {exc}"
            return False
        if not self._await_ack(self._next_write_id):
            return False
        try:
            apply_local()
        except Exception as exc:
            self._last_error = f"durable write acked but local mirror failed: {exc}"
            return False
        self._last_error = None
        return True

    # -- turn lifecycle (each op is itself ack-gated) ---------------------------------

    def begin_turn(self, turn_id: str, session_id: str) -> bool:
        self._validate_turn_id(turn_id)
        if not self._ensure_writable():
            return False
        if self._store.get_turn(turn_id) is not None:
            raise ValueError(f"turn {turn_id!r} already exists in the audit store")

        from coxswain.persistence.store import OPEN_TURN_HEADROOM

        open_count = sum(
            1
            for existing in (self._store.get_turn(tid) for tid in self._known_turn_ids())
            if existing is not None and existing.state == "open"
        )
        cap = self._store._turn_cap
        if open_count >= cap + OPEN_TURN_HEADROOM:
            self._last_error = (
                f"{open_count} open turns have reached the retention cap ({cap}) "
                f"+ headroom ({OPEN_TURN_HEADROOM}); refusing new turns (§2.3)"
            )
            return False

        return self._submit(
            "begin_turn",
            turn_id,
            {"session_id": session_id},
            lambda: self._store.begin_turn(turn_id, session_id),
        )

    def _known_turn_ids(self) -> Iterable[str]:
        return getattr(self._store, "_turns", {}).keys()

    def close_turn(self, turn_id: str) -> bool:
        self._validate_turn_id(turn_id)
        if not self._ensure_writable():
            return False
        if self._store.get_turn(turn_id) is None:
            raise ValueError(f"no turn {turn_id!r} to close")
        return self._submit(
            "close_turn", turn_id, {}, lambda: self._store.close_turn(turn_id)
        )

    def abandon_turn(self, turn_id: str) -> bool:
        self._validate_turn_id(turn_id)
        if not self._ensure_writable():
            return False
        if self._store.get_turn(turn_id) is None:
            raise ValueError(f"no turn {turn_id!r} to abandon")
        return self._submit(
            "abandon_turn", turn_id, {}, lambda: self._store.abandon_turn(turn_id)
        )

    def attach_pending_intent(self, turn_id: str, intent: PendingIntent) -> bool:
        self._validate_turn_id(turn_id)
        if not isinstance(intent, PendingIntent):
            raise TypeError(f"attach_pending_intent() requires a PendingIntent, got {type(intent)!r}")
        self._require_open_turn(turn_id)
        if not self._ensure_writable():
            return False
        return self._submit(
            "attach_intent",
            turn_id,
            {"intent": asdict(intent)},
            lambda: self._store.attach_pending_intent(turn_id, intent),
        )

    def attach_outcome(self, turn_id: str, outcome: ExecutionOutcome) -> bool:
        self._validate_turn_id(turn_id)
        if not isinstance(outcome, ExecutionOutcome):
            raise TypeError(f"attach_outcome() requires an ExecutionOutcome, got {type(outcome)!r}")
        self._require_open_turn(turn_id)
        if not self._ensure_writable():
            return False
        return self._submit(
            "attach_outcome",
            turn_id,
            {"outcome": asdict(outcome)},
            lambda: self._store.attach_outcome(turn_id, outcome),
        )

    # -- the AuditSink seam consumed by FftGate ----------------------------------------

    def record(self, decision: FftDecision) -> bool:
        self._validate_decision(decision)
        self._validate_turn_id(decision.turn_id)
        self._require_open_turn(decision.turn_id)
        if not self._ensure_writable():
            return False
        return self._submit(
            "decision",
            decision.turn_id,
            {"record": asdict(decision)},
            lambda: self._store.record_decision(decision.turn_id, decision),
        )

    def record_fingerprint(self, fingerprint: StalenessFingerprint) -> bool:
        self._validate_fingerprint(fingerprint)
        self._validate_turn_id(fingerprint.turn_id)
        self._require_open_turn(fingerprint.turn_id)
        if not self._ensure_writable():
            return False
        return self._submit(
            "fingerprint",
            fingerprint.turn_id,
            {"record": asdict(fingerprint)},
            lambda: self._store.attach_fingerprint(fingerprint.turn_id, fingerprint),
        )

    def record_override(self, record: OverrideRecord) -> bool:
        self._validate_override(record)
        self._validate_turn_id(record.turn_id)
        self._require_open_turn(record.turn_id)
        if not self._ensure_writable():
            return False
        return self._submit(
            "override",
            record.turn_id,
            {"record": asdict(record)},
            lambda: self._store.add_override(record),
        )
