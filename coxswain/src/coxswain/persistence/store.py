"""The pure persistence layer of W1 (spec §2.3, §2.5).

``CoxswainAuditStore`` owns the turn lifecycle (open/closed/abandoned with
closed_at), abandon-on-load, FIFO eviction over closed records only -- never an
open turn -- the override-store exemption, and the §2.5 schema-version check
with its loud read-only degrade.

This module is deliberately storage-agnostic: the persistence backend is
injected (see ``PersistenceBackend``). There is no IndexedDB code here -- the
browser side lands in W5's ``audit_store.js``. NFR-1/NFR-2 hold: plain CPython,
no praxis imports, no js imports.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, replace
from enum import Enum
from typing import Final, Iterable, Protocol

from coxswain.records import (
    SCHEMA_VERSION,
    CoxswainTurnRecord,
    ExecutionOutcome,
    FftDecision,
    OverrideRecord,
    PendingIntent,
    StalenessFingerprint,
)

__all__ = [
    "DEFAULT_TURN_CAP",
    "OPEN_TURN_HEADROOM",
    "SCHEMA_VERSION",
    "CoxswainAuditStore",
    "OpenTurnCapacityExceeded",
    "PersistenceBackend",
    "ReadOnlyStoreError",
    "StoreMode",
    "TurnQueryResult",
    "UnknownTurnError",
]

#: §2.3: configurable FIFO cap over whole turn records (default 1000 turns).
DEFAULT_TURN_CAP: Final[int] = 1000

#: §2.3: if open turns ALONE reach ``cap + 16``, the store stops accepting new
#: turns and surfaces a loud failure instead of evicting one.
OPEN_TURN_HEADROOM: Final[int] = 16


class StoreMode(str, Enum):
    """§2.5: equal schema versions run read-write; ANY other version degrades
    the whole store to read-only. There is deliberately no migration in MVP
    and no flag that downgrades the refusal to a warning."""

    READ_WRITE = "read_write"
    READ_ONLY = "read_only"


class ReadOnlyStoreError(RuntimeError):
    """Raised on any write attempt against a read-only-degraded store."""


class OpenTurnCapacityExceeded(RuntimeError):
    """Raised when open turns alone reach ``cap + 16`` (§2.3 pathological
    state: turns being minted and never resolved must be visible, not
    absorbed)."""


class UnknownTurnError(KeyError):
    """Raised when querying a turn_id no record carries."""


class PersistenceBackend(Protocol):
    """Storage seam injected into the store. The W5 JS implementation backs
    this with IndexedDB object stores ``coxswain_turns`` and
    ``coxswain_overrides``; tests back it with dicts."""

    def load_turns(self) -> Iterable[CoxswainTurnRecord]: ...

    def save_turn(self, record: CoxswainTurnRecord) -> None: ...

    def delete_turns(self, turn_ids: Iterable[str]) -> None: ...

    def load_overrides(self) -> Iterable[OverrideRecord]: ...

    def save_override(self, record: OverrideRecord) -> None: ...


@dataclass(frozen=True)
class TurnQueryResult:
    """AC-7's single-query result: the whole turn aggregate plus every
    override joined by turn_id -- no manual stitching across trails."""

    turn: CoxswainTurnRecord
    overrides: tuple[OverrideRecord, ...]


def _newer_direction_message(record_version: int) -> str:
    return (
        f"Coxswain's audit store was written by a newer build "
        f"(schema {record_version}, this build understands {SCHEMA_VERSION}). "
        "Existing records are readable; Coxswain will not run until you update."
    )


def _older_direction_message(record_version: int) -> str:
    return (
        f"Coxswain's audit store was written by an older build "
        f"(schema {record_version}, this build understands {SCHEMA_VERSION}). "
        "Existing records are readable; no migration is performed."
    )


class CoxswainAuditStore:
    """In-memory view over the two stores, persisted through the injected
    backend. All mutators refuse to write while read-only."""

    def __init__(
        self,
        backend: PersistenceBackend,
        *,
        now: float = time.time,
        turn_cap: int = DEFAULT_TURN_CAP,
    ) -> None:
        self._backend = backend
        self._now = now
        self._turn_cap = turn_cap
        self._turns: dict[str, CoxswainTurnRecord] = {}
        self._overrides: list[OverrideRecord] = []
        self._mode = StoreMode.READ_WRITE
        self._status_message: str | None = None

    # -- construction ---------------------------------------------------------

    @classmethod
    def open(
        cls,
        backend: PersistenceBackend,
        *,
        now: float = time.time,
        turn_cap: int = DEFAULT_TURN_CAP,
    ) -> CoxswainAuditStore:
        store = cls(backend, now=now, turn_cap=turn_cap)
        store._load()
        return store

    def _load(self) -> None:
        self._turns = {r.turn_id: r for r in self._backend.load_turns()}
        self._overrides = list(self._backend.load_overrides())

        # §2.5 scan: any record body version differing from the running build
        # degrades the entire store to read-only, naming both numbers.
        seen_versions = {r.schema_version for r in self._turns.values()}
        seen_versions.update(r.schema_version for r in self._overrides)
        foreign = sorted(v for v in seen_versions if v != SCHEMA_VERSION)
        if foreign:
            above = [v for v in foreign if v > SCHEMA_VERSION]
            if above:
                self._mode = StoreMode.READ_ONLY
                self._status_message = _newer_direction_message(max(above))
            else:
                self._mode = StoreMode.READ_ONLY
                self._status_message = _older_direction_message(min(foreign))
            # Read-only means NO write is accepted -- including lifecycle
            # bookkeeping. The foreign build owns these records' lifecycle;
            # leave them exactly as found (AC-21: no silent coercion).
            return

        # §2.3 abandon-on-load: a turn still open at session init (tab closed
        # mid-turn) becomes abandoned with closed_at set to the load time.
        for turn_id, record in list(self._turns.items()):
            if record.state == "open":
                abandoned = replace(
                    record, state="abandoned", closed_at=self._now()
                )
                self._turns[turn_id] = abandoned
                self._backend.save_turn(abandoned)

        self._evict_over_cap()

    # -- read-only surface ------------------------------------------------------

    @property
    def mode(self) -> StoreMode:
        return self._mode

    @property
    def status_message(self) -> str | None:
        return self._status_message

    def get_turn(self, turn_id: str) -> CoxswainTurnRecord | None:
        return self._turns.get(turn_id)

    def query_turn(self, turn_id: str) -> TurnQueryResult:
        record = self.get_turn(turn_id)
        if record is None:
            raise UnknownTurnError(turn_id)
        return TurnQueryResult(
            turn=record,
            overrides=tuple(o for o in self._overrides if o.turn_id == turn_id),
        )

    def overrides_for_turn(self, turn_id: str) -> tuple[OverrideRecord, ...]:
        return tuple(o for o in self._overrides if o.turn_id == turn_id)

    def export_bundle(self) -> dict:
        """L3-shaped, self-describing bundle of both stores keyed by turn_id.
        Readable (and therefore exportable) even while read-only (AC-21)."""
        return {
            "exported_by_schema_version": SCHEMA_VERSION,
            "turns": {tid: asdict(r) for tid, r in self._turns.items()},
            "overrides": [asdict(o) for o in self._overrides],
        }

    # -- writes -----------------------------------------------------------------

    def _ensure_writable(self) -> None:
        if self._mode is StoreMode.READ_ONLY:
            raise ReadOnlyStoreError(self._status_message or "store is read-only")

    def _save(self, record: CoxswainTurnRecord) -> None:
        self._turns[record.turn_id] = record
        self._backend.save_turn(record)

    def _updated(self, turn_id: str, **changes) -> CoxswainTurnRecord:
        record = self.get_turn(turn_id)
        if record is None:
            raise UnknownTurnError(turn_id)
        updated = replace(record, **changes)
        self._save(updated)
        return updated

    def begin_turn(self, turn_id: str, session_id: str) -> CoxswainTurnRecord:
        self._ensure_writable()
        open_count = sum(1 for r in self._turns.values() if r.state == "open")
        if open_count >= self._turn_cap + OPEN_TURN_HEADROOM:
            raise OpenTurnCapacityExceeded(
                f"{open_count} open turns have reached the retention cap "
                f"({self._turn_cap}) + headroom ({OPEN_TURN_HEADROOM}); Coxswain "
                "stopped accepting new turns. Turns are being minted and never "
                "resolved -- this is a pathological state and must be visible."
            )
        record = CoxswainTurnRecord(
            schema_version=SCHEMA_VERSION,
            turn_id=turn_id,
            session_id=session_id,
            state="open",
            opened_at=self._now(),
            closed_at=None,
        )
        self._save(record)
        self._evict_over_cap()
        return record

    def close_turn(self, turn_id: str) -> CoxswainTurnRecord:
        """User cancelled/dismissed, or the gate reached a terminal block with
        no re-entry pending (§2.3). Idempotent."""
        self._ensure_writable()
        record = self.get_turn(turn_id)
        if record is not None and record.state == "open":
            record = self._updated(turn_id, state="closed", closed_at=self._now())
            self._evict_over_cap()
        return record  # type: ignore[return-value]

    def abandon_turn(self, turn_id: str) -> CoxswainTurnRecord:
        self._ensure_writable()
        record = self._updated(turn_id, state="abandoned", closed_at=self._now())
        self._evict_over_cap()
        return record

    def attach_pending_intent(self, turn_id: str, intent: PendingIntent) -> None:
        self._ensure_writable()
        record = self.get_turn(turn_id)
        if record is None:
            raise UnknownTurnError(turn_id)
        self._updated(turn_id, pending_intents=record.pending_intents + (intent,))

    def record_decision(self, turn_id: str, decision_record: FftDecision) -> None:
        self._ensure_writable()
        record = self.get_turn(turn_id)
        if record is None:
            raise UnknownTurnError(turn_id)
        self._updated(turn_id, decisions=record.decisions + (decision_record,))

    def attach_fingerprint(
        self, turn_id: str, fingerprint: StalenessFingerprint
    ) -> None:
        self._ensure_writable()
        record = self.get_turn(turn_id)
        if record is None:
            raise UnknownTurnError(turn_id)
        self._updated(turn_id, fingerprints=record.fingerprints + (fingerprint,))

    def attach_outcome(self, turn_id: str, outcome: ExecutionOutcome) -> None:
        """Writing an ExecutionOutcome closes the turn (§2.3) -- any status,
        including failed and aborted_stale."""
        self._ensure_writable()
        record = self.get_turn(turn_id)
        if record is None:
            raise UnknownTurnError(turn_id)
        self._updated(turn_id, outcome=outcome)
        if record.state == "open":
            self._updated(turn_id, state="closed", closed_at=self._now())
            self._evict_over_cap()

    def add_override(self, record: OverrideRecord) -> None:
        """Persist to the override store. Exempt from eviction (§2.3): the
        record keeps its turn_id even after the turn itself is evicted."""
        self._ensure_writable()
        self._overrides.append(record)
        self._backend.save_override(record)

    # -- eviction ---------------------------------------------------------------

    def _evict_over_cap(self) -> None:
        """FIFO over WHOLE turn records, oldest closed_at first, restricted to
        closed and abandoned records. An open turn is never evicted regardless
        of age, so the cap may transiently be exceeded by open turns (§2.3)."""
        excess = len(self._turns) - self._turn_cap
        if excess <= 0:
            return
        evictable = sorted(
            (r.closed_at, r.opened_at, tid)
            for tid, r in self._turns.items()
            if r.state != "open"
        )
        victims = [tid for _, _, tid in evictable[:excess]]
        if not victims:
            return
        self._backend.delete_turns(victims)
        for tid in victims:
            self._turns.pop(tid, None)
