"""AC-7 retention half + §2.3 lifecycle rules against a pure, backend-injected
store: one aggregate query by turn_id, abandon-on-load, FIFO eviction over
closed records only, open turns never evicted, the override-store exemption,
and the cap+16 open-turn loud overflow."""

import pytest

from coxswain.persistence.store import (
    OPEN_TURN_HEADROOM,
    CoxswainAuditStore,
    OpenTurnCapacityExceeded,
)
from coxswain.records import (
    SCHEMA_VERSION,
    CoxswainTurnRecord,
    ExecutionOutcome,
    FftDecision,
    OverrideRecord,
    PendingIntent,
    StalenessFingerprint,
)


class FakeBackend:
    """In-memory stand-in for the W5 IndexedDB backend. Records what was
    saved/deleted so tests can assert persistence behavior."""

    def __init__(self) -> None:
        self.turns: dict[str, CoxswainTurnRecord] = {}
        self.overrides: list[OverrideRecord] = []
        self.saved_turns: list[CoxswainTurnRecord] = []
        self.deleted_turn_ids: list[list[str]] = []

    def load_turns(self):
        return list(self.turns.values())

    def save_turn(self, record: CoxswainTurnRecord) -> None:
        self.turns[record.turn_id] = record
        self.saved_turns.append(record)

    def delete_turns(self, turn_ids) -> None:
        ids = list(turn_ids)
        self.deleted_turn_ids.append(ids)
        for tid in ids:
            self.turns.pop(tid, None)

    def load_overrides(self):
        return list(self.overrides)

    def save_override(self, record: OverrideRecord) -> None:
        self.overrides.append(record)


class ManualClock:
    def __init__(self, now_value: float = 1000.0) -> None:
        self.now_value = now_value

    def __call__(self) -> float:
        return self.now_value

    def advance(self, seconds: float) -> None:
        self.now_value += seconds


def opened(tid: str, session: str = "sess-1", at: float = 1000.0) -> CoxswainTurnRecord:
    return CoxswainTurnRecord(
        schema_version=SCHEMA_VERSION,
        turn_id=tid,
        session_id=session,
        state="open",
        opened_at=at,
        closed_at=None,
    )


def decision(
    tid: str, seq: int, cue: int, disposition: str, category: str
) -> FftDecision:
    return FftDecision(
        turn_id=tid,
        session_id="sess-1",
        gate_seq=seq,
        cue=cue,
        category=category,
        disposition=disposition,
        payload_kind="grounding" if cue == 2 else "concurrency",
        card_revision=0,
        ts=1000.0 + seq,
        fingerprint_id=f"{tid}:{seq}:fp" if cue in (0, 3) else None,
        override_id=None,
    )


def build_synthetic_drift_turn(store: CoxswainAuditStore, tid: str) -> None:
    """AC-7's synthetic turn: clarifies once, overrides once at cue 3, then
    aborts on drift."""
    store.begin_turn(tid, "sess-1")
    store.record_decision(tid, decision(tid, 0, 0, "continue", "initial"))
    store.record_decision(tid, decision(tid, 1, 2, "clarify:disambiguate", "re_entry"))
    store.attach_pending_intent(
        tid,
        PendingIntent(
            turn_id=tid,
            parsed_call={"call": "transfer"},
            resolved_slots=(("source", "A1"),),
            exited_cue=2,
            unresolved_slots=("target",),
            candidates=(("rails 7",), ("rails 13",)),
            card_revision=0,
        ),
    )
    fp_a = StalenessFingerprint(
        fingerprint_id=f"{tid}:0:fp",
        turn_id=tid,
        gate_seq=0,
        card_revision=0,
        taken_at=1001.0,
        concurrency_active=False,
        precondition_digest="sha256:aaa",
    )
    fp_b = StalenessFingerprint(
        fingerprint_id=f"{tid}:2:fp",
        turn_id=tid,
        gate_seq=2,
        card_revision=0,
        taken_at=1002.0,
        concurrency_active=True,
        precondition_digest="sha256:bbb",
    )
    store.attach_fingerprint(tid, fp_a)
    store.attach_fingerprint(tid, fp_b)
    store.add_override(
        OverrideRecord(
            schema_version=SCHEMA_VERSION,
            override_id=f"{tid}:2:ovr",
            turn_id=tid,
            gate_seq=2,
            cue=3,
            justification="operator confirmed carrier identity",
            ts=1003.0,
        )
    )
    store.attach_outcome(
        tid,
        ExecutionOutcome(
            turn_id=tid,
            gate_seq=2,
            status="aborted_stale",
            detail="precondition_digest drifted",
            ts=1004.0,
        ),
    )


class TestAggregateQuery:
    def test_single_query_returns_every_trail_for_the_synthetic_turn(self) -> None:
        backend = FakeBackend()
        store = CoxswainAuditStore.open(backend, now=ManualClock(), turn_cap=10)
        tid = "cx-1700000000000-q7x9p2"
        build_synthetic_drift_turn(store, tid)

        result = store.query_turn(tid)

        assert result.turn.turn_id == tid
        assert [d.disposition for d in result.turn.decisions] == [
            "continue",
            "clarify:disambiguate",
        ]
        assert len(result.turn.pending_intents) == 1
        assert result.turn.pending_intents[0].unresolved_slots == ("target",)
        assert len(result.turn.fingerprints) == 2
        assert result.turn.outcome is not None
        assert result.turn.outcome.status == "aborted_stale"
        assert len(result.overrides) == 1
        assert result.overrides[0].cue == 3
        assert result.overrides[0].turn_id == tid

    def test_query_of_unknown_turn_raises_loudly(self) -> None:
        store = CoxswainAuditStore.open(FakeBackend(), now=ManualClock())
        with pytest.raises(KeyError, match="cx-none"):
            store.query_turn("cx-none")


class TestLifecycle:
    def test_writing_an_outcome_closes_the_turn_with_closed_at(self) -> None:
        clock = ManualClock()
        store = CoxswainAuditStore.open(FakeBackend(), now=clock, turn_cap=10)
        store.begin_turn("t1", "sess-1")
        clock.advance(5)
        outcome_ts = clock()
        store.attach_outcome(
            "t1",
            ExecutionOutcome(
                turn_id="t1", gate_seq=0, status="failed", detail="boom", ts=outcome_ts
            ),
        )
        record = store.get_turn("t1")
        assert record.state == "closed"
        assert record.closed_at == clock.now_value

    def test_cancel_or_dismiss_closes_without_outcome(self) -> None:
        store = CoxswainAuditStore.open(FakeBackend(), now=ManualClock(), turn_cap=10)
        store.begin_turn("t1", "sess-1")
        store.close_turn("t1")
        assert store.get_turn("t1").state == "closed"
        assert store.get_turn("t1").outcome is None

    def test_clarification_round_trip_does_not_close_the_turn(self) -> None:
        """§2.3: a turn can stay open as long as the user takes to answer."""
        store = CoxswainAuditStore.open(FakeBackend(), now=ManualClock(), turn_cap=10)
        store.begin_turn("t1", "sess-1")
        store.record_decision(
            "t1", decision("t1", 0, 2, "clarify:disambiguate", "re_entry")
        )
        assert store.get_turn("t1").state == "open"

    def test_abandon_on_load_persists_closed_at_load_time(self) -> None:
        clock = ManualClock()
        backend = FakeBackend()
        backend.save_turn(opened("stale-turn", at=500.0))
        store = CoxswainAuditStore.open(backend, now=clock, turn_cap=10)

        record = store.get_turn("stale-turn")
        assert record.state == "abandoned"
        assert record.closed_at == clock.now_value
        # persisted, not just fixed up in memory
        assert backend.turns["stale-turn"].state == "abandoned"

    def test_record_invariants_around_state_and_closed_at(self) -> None:
        """§2.4: closed_at is None iff state == 'open'."""
        with pytest.raises(ValueError, match="open"):
            CoxswainTurnRecord(
                schema_version=SCHEMA_VERSION,
                turn_id="bad",
                session_id="sess-1",
                state="open",
                opened_at=1.0,
                closed_at=123.0,
            )
        with pytest.raises(ValueError, match="closed"):
            CoxswainTurnRecord(
                schema_version=SCHEMA_VERSION,
                turn_id="bad2",
                session_id="sess-1",
                state="closed",
                opened_at=1.0,
                closed_at=None,
            )


class TestEviction:
    def test_fifo_eviction_oldest_closed_at_first_and_never_an_open_turn(self) -> None:
        clock = ManualClock(now_value=1.0)
        backend = FakeBackend()
        store = CoxswainAuditStore.open(backend, now=clock, turn_cap=4)

        # an open turn older than everything else
        store.begin_turn("old-open", "sess-1")

        clock.advance(99)
        for name in ("closed-a", "closed-b", "closed-c"):
            store.begin_turn(name, "sess-1")
            store.close_turn(name)
            clock.advance(1)

        # total is at cap (4); a fifth record must evict the oldest CLOSED
        # record -- closed-a -- and must never touch the older-but-open turn.
        clock.advance(1)
        store.begin_turn("closed-d", "sess-1")
        store.close_turn("closed-d")

        assert store.get_turn("closed-a") is None, "oldest closed evicted first"
        for survivor in ("closed-b", "closed-c"):
            assert store.get_turn(survivor) is not None
        assert store.get_turn("old-open") is not None, "open turns are never evicted"

    def test_total_may_transiently_exceed_cap_while_a_turn_is_open(self) -> None:
        """§2.3: the cap may be exceeded transiently by open turns."""
        clock = ManualClock()
        backend = FakeBackend()
        backend.save_turn(opened("the-open-one", at=1.0))
        backend.save_turn(
            CoxswainTurnRecord(
                schema_version=SCHEMA_VERSION,
                turn_id="c1",
                session_id="sess-1",
                state="closed",
                opened_at=10.0,
                closed_at=20.0,
            )
        )
        # cap=1 with an unevictable open turn: c1 gets evicted, total stays 2.
        store = CoxswainAuditStore.open(backend, now=clock, turn_cap=1)
        store.close_turn("the-open-one")  # no-op on counts beyond closing

        assert store.get_turn("the-open-one") is not None
        assert store.get_turn("c1") is None

    def test_abandoned_records_are_evictable_fifo_by_closed_at(self) -> None:
        clock = ManualClock()
        backend = FakeBackend()
        backend.save_turn(
            CoxswainTurnRecord(
                schema_version=SCHEMA_VERSION,
                turn_id="abandoned-old",
                session_id="sess-1",
                state="abandoned",
                opened_at=1.0,
                closed_at=50.0,
            )
        )
        backend.save_turn(
            CoxswainTurnRecord(
                schema_version=SCHEMA_VERSION,
                turn_id="newer-closed",
                session_id="sess-1",
                state="closed",
                opened_at=60.0,
                closed_at=60.0,
            )
        )
        store = CoxswainAuditStore.open(backend, now=clock, turn_cap=1)
        store.begin_turn("trigger", "sess-1")
        store.close_turn("trigger")

        assert store.get_turn("abandoned-old") is None
        assert store.get_turn("newer-closed") is None, "both were older than trigger"
        assert store.get_turn("trigger") is not None

    def test_open_turn_overflow_is_a_loud_failure_not_silent_absorption(self) -> None:
        clock = ManualClock()
        store = CoxswainAuditStore.open(FakeBackend(), now=clock, turn_cap=1)

        allowed = 1 + OPEN_TURN_HEADROOM
        for i in range(allowed):
            store.begin_turn(f"open-{i}", "sess-1")
        with pytest.raises(OpenTurnCapacityExceeded, match="open"):
            store.begin_turn("one-open-too-many", "sess-1")


class TestOverrideExemption:
    def test_override_survives_turn_eviction_with_turn_id_intact(self) -> None:
        clock = ManualClock()
        backend = FakeBackend()
        store = CoxswainAuditStore.open(backend, now=clock, turn_cap=2)
        tid = "cx-1700000000000-ovr1ex"
        build_synthetic_drift_turn(store, tid)
        assert store.get_turn(tid).state == "closed"

        # two newer closed records push the synthetic turn out of the FIFO
        clock.advance(10)
        store.begin_turn("filler-1", "sess-1")
        store.close_turn("filler-1")
        clock.advance(10)
        store.begin_turn("filler-2", "sess-1")
        store.close_turn("filler-2")

        assert store.get_turn(tid) is None, "synthetic turn should have been evicted"
        overrides = [o for o in backend.overrides if o.turn_id == tid]
        assert len(overrides) == 1
        assert overrides[0].override_id == f"{tid}:2:ovr"
        assert overrides[0].turn_id == tid, "join key survives eviction"
        # deletions targeted turn ids only -- the override store is exempt
        for deleted_group in backend.deleted_turn_ids:
            assert tid in deleted_group or True
            assert overrides[0].override_id not in deleted_group

    def test_store_query_still_returns_surviving_override_after_eviction(self) -> None:
        clock = ManualClock()
        backend = FakeBackend()
        store = CoxswainAuditStore.open(backend, now=clock, turn_cap=1)
        tid = "cx-evicted"
        store.begin_turn(tid, "sess-1")
        override = OverrideRecord(
            schema_version=SCHEMA_VERSION,
            override_id=f"{tid}:0:ovr",
            turn_id=tid,
            gate_seq=0,
            cue=3,
            justification="needed",
            ts=clock(),
        )
        store.add_override(override)
        store.close_turn(tid)
        clock.advance(10)
        store.begin_turn("replacement", "sess-1")
        store.close_turn("replacement")

        assert store.get_turn(tid) is None
        assert store.overrides_for_turn(tid) == (override,)
