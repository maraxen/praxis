"""W5 FR-9 ack-before-disposition writer: validation, closed vocabulary,
ack-window policy (KERNEL_RTT_TIMEOUT_MS), and fail-closed conversion of every
store failure into ``False`` -- which FftGate turns into
``blocked:audit_unavailable``. §2.2 point 6: a record whose turn_id is absent
or does not match an open turn is refused."""

import re

import pytest

from coxswain.audit import (
    KERNEL_RTT_TIMEOUT_MS,
    AuditWriter,
    LoopbackTransport,
    ManualAckTransport,
)
from coxswain.persistence.store import CoxswainAuditStore
from coxswain.records import (
    SCHEMA_VERSION,
    ExecutionOutcome,
    FftDecision,
    OverrideRecord,
    PendingIntent,
    StalenessFingerprint,
)

TURN = "cx-1700000000000-k3x9qz"
SESSION = "cx-sess-1700000000000-abcd1234"


def make_store(backend=None) -> tuple[CoxswainAuditStore, object]:
    from test_retention import FakeBackend

    backend = backend if backend is not None else FakeBackend()
    return CoxswainAuditStore.open(backend), backend


def make_decision(turn_id: str = TURN, disposition: str = "continue") -> FftDecision:
    return FftDecision(
        turn_id=turn_id,
        session_id=SESSION,
        gate_seq=0,
        cue=0,
        category="initial",
        disposition=disposition,
        payload_kind="",
        card_revision=0,
        ts=1000.0,
        fingerprint_id=None,
        override_id=None,
    )


def make_writer(store, transport) -> AuditWriter:
    clock = {"now": 0.0}
    return AuditWriter(
        store,
        transport,
        monotonic=lambda: clock["now"],
        sleep=lambda s: clock.__setitem__("now", clock["now"] + s),
    ), clock


# --- turn lifecycle -------------------------------------------------------------


def test_begin_turn_acks_then_applies_locally() -> None:
    store, _ = make_store()
    transport = LoopbackTransport()
    writer, _ = make_writer(store, transport)

    assert writer.begin_turn(TURN, SESSION) is True
    record = store.get_turn(TURN)
    assert record is not None and record.state == "open"
    # The durable write was issued inside begin_turn's own path.
    assert [r["kind"] for r in transport.sent] == ["begin_turn"]


def test_duplicate_begin_turn_refused_loudly() -> None:
    store, _ = make_store()
    writer, _ = make_writer(store, LoopbackTransport())
    assert writer.begin_turn(TURN, SESSION) is True
    with pytest.raises(ValueError, match="already"):
        writer.begin_turn(TURN, SESSION)


def test_appends_require_an_open_turn() -> None:
    store, _ = make_store()
    writer, _ = make_writer(store, LoopbackTransport())

    # Unknown turn: refused before anything is sent or persisted (§2.2.6).
    with pytest.raises(ValueError, match="no open turn"):
        writer.record(make_decision())
    # Closed turn: same refusal.
    writer.begin_turn(TURN, SESSION)
    store.close_turn(TURN)
    with pytest.raises(ValueError, match="no open turn"):
        writer.record(make_decision())


@pytest.mark.parametrize(
    "bad_turn_id", ["", "not-a-turn-id", "cx-abc-def456", "cx-1700000000000-K3X9QZ"]
)
def test_malformed_turn_id_is_a_loud_rejection(bad_turn_id: str) -> None:
    store, _ = make_store()
    transport = LoopbackTransport()
    writer, _ = make_writer(store, transport)
    assert writer.begin_turn(TURN, SESSION) is True
    sent_before = len(transport.sent)

    with pytest.raises(ValueError):
        writer.attach_outcome(
            bad_turn_id,
            ExecutionOutcome(turn_id=bad_turn_id, gate_seq=0, status="ok", detail=None, ts=1.0),
        )
    # The malformed write itself never reached the wire.
    assert len(transport.sent) == sent_before


# --- FR-9: the ack window ---------------------------------------------------------


def test_record_returns_only_after_ack_and_applies_on_ack() -> None:
    store, _ = make_store()
    transport = ManualAckTransport()
    transport.deliver_acks_automatically()
    writer, _ = make_writer(store, transport)
    assert writer.begin_turn(TURN, SESSION) is True

    seen: list[str] = []
    original_pump = transport.pump

    def tracing_pump():
        messages = original_pump()
        for message in messages:
            seen.append(message["type"])
        return messages

    transport.pump = tracing_pump  # type: ignore[method-assign]
    decision = make_decision(disposition="clarify:disambiguate")
    assert writer.record(decision) is True
    # Ack arrived (and was observed by the pump) before record() returned.
    assert "audit.ack" in seen
    joined = store.query_turn(TURN)
    assert len(joined.turn.decisions) == 1
    assert joined.turn.decisions[0].disposition == "clarify:disambiguate"


def test_dropped_ack_times_out_fail_closed_within_kernel_rtt_window() -> None:
    store, _ = make_store()
    transport = ManualAckTransport()
    writer, clock = make_writer(store, transport)
    # The turn opens durably; every write AFTER it is silently dropped.
    transport.deliver_acks_automatically()
    assert writer.begin_turn(TURN, SESSION) is True
    transport.hold_all()
    start = clock["now"]

    assert writer.record(make_decision()) is False
    elapsed_ms = (clock["now"] - start) * 1000
    assert elapsed_ms >= KERNEL_RTT_TIMEOUT_MS - 1e-6
    # The unacked write must not be applied locally either: an unrecorded
    # decision can back a disposition.
    assert store.get_turn(TURN).decisions == ()
    assert writer.last_error is not None


def test_nack_is_an_immediate_failure_before_the_window_elapses() -> None:
    store, _ = make_store()
    transport = ManualAckTransport()
    transport.deliver_acks_automatically()
    writer, clock = make_writer(store, transport)
    assert writer.begin_turn(TURN, SESSION) is True

    transport.fail_next_with("QuotaExceededError: coxswain_turns full")
    assert writer.record(make_decision()) is False
    assert (clock["now"]) < KERNEL_RTT_TIMEOUT_MS / 1000  # no window burn
    assert "QuotaExceededError" in (writer.last_error or "")


def test_transport_send_failure_is_unavailability() -> None:
    store, _ = make_store()

    class DeadTransport:
        def send_write(self, request):
            raise RuntimeError("channel closed")

        def pump(self):
            return []

    # Seed the open turn through the store so the test targets record()'s
    # conversion of a dead transport into False (not lifecycle validation).
    store.begin_turn(TURN, SESSION)
    writer, _ = make_writer(store, DeadTransport())
    assert writer.record(make_decision()) is False
    assert "unavailable" in (writer.last_error or "")


# --- closed vocabularies + record shapes ------------------------------------------


def test_disposition_vocabulary_is_enforced_before_any_write() -> None:
    store, _ = make_store()
    transport = LoopbackTransport()
    writer, _ = make_writer(store, transport)
    writer.begin_turn(TURN, SESSION)

    with pytest.raises(ValueError, match="closed vocabulary"):
        writer.record(make_decision(disposition="continue_but_louder"))
    # Refusal happens BEFORE any wire traffic: no decision write was sent.
    assert all(r["kind"] != "decision" for r in transport.sent)


def test_override_record_keeps_truncated_justification_and_acks() -> None:
    store, _ = make_store()
    writer, _ = make_writer(store, LoopbackTransport())
    writer.begin_turn(TURN, SESSION)

    override = OverrideRecord(
        schema_version=SCHEMA_VERSION,
        override_id=f"{TURN}:0:ovr",
        turn_id=TURN,
        gate_seq=0,
        cue=3,
        justification="x" * 900,
        ts=1000.0,
    )
    assert writer.record_override(override) is True
    stored = store.overrides_for_turn(TURN)
    assert len(stored) == 1
    # NFR-7 cap enforced by the record itself; the writer never re-widens it.
    assert len(stored[0].justification) <= 500


def test_fingerprint_append_is_ack_gated() -> None:
    store, _ = make_store()
    transport = ManualAckTransport()
    transport.deliver_acks_automatically()
    writer, _ = make_writer(store, transport)
    assert writer.begin_turn(TURN, SESSION) is True

    fingerprint = StalenessFingerprint(
        fingerprint_id=f"{TURN}:0:fp",
        turn_id=TURN,
        gate_seq=0,
        card_revision=0,
        taken_at=1000.0,
        concurrency_active=False,
        precondition_digest="deadbeef",
    )
    transport.fail_next_with("store aborted")
    assert writer.record_fingerprint(fingerprint) is False
    assert store.get_turn(TURN).fingerprints == ()

    fingerprint2 = StalenessFingerprint(**{**fingerprint.__dict__, "gate_seq": 1})
    assert writer.record_fingerprint(fingerprint2) is True
    assert len(store.get_turn(TURN).fingerprints) == 1


# --- outcome closes the turn (§2.3), through the ack path ---------------------------


def test_attach_outcome_closes_turn_and_is_ack_gated() -> None:
    store, _ = make_store()
    transport = ManualAckTransport()
    transport.deliver_acks_automatically()
    writer, _ = make_writer(store, transport)
    assert writer.begin_turn(TURN, SESSION) is True

    outcome = ExecutionOutcome(turn_id=TURN, gate_seq=1, status="aborted_stale", detail=None, ts=2.0)
    transport.fail_next_with("abort")
    assert writer.attach_outcome(TURN, outcome) is False
    assert store.get_turn(TURN).state == "open"  # nothing applied on failure

    assert writer.attach_outcome(TURN, outcome) is True
    record = store.get_turn(TURN)
    assert record.outcome is not None and record.outcome.status == "aborted_stale"
    assert record.state == "closed" and record.closed_at is not None


# --- read-only degrade refuses writes without touching the transport ----------------


def test_readonly_store_refuses_every_write_silently_toward_the_wire() -> None:
    from dataclasses import replace

    store, _ = make_store()
    transport = LoopbackTransport()
    writer, _ = make_writer(store, transport)
    writer.begin_turn(TURN, SESSION)
    store.close_turn(TURN)

    # A record body written by a NEWER build degrades the whole store
    # (§2.5): reopen must be readable but accept no write at all.
    original = store.get_turn(TURN)
    assert original is not None
    store._backend.save_turn(replace(original, schema_version=SCHEMA_VERSION + 1))

    reopened = CoxswainAuditStore.open(store._backend)
    writer2, _ = make_writer(reopened, transport)
    sent_before = len(transport.sent)

    assert writer2.begin_turn("cx-1700000000424-ok2k42", SESSION) is False
    assert writer2.last_error and "read-only" in writer2.last_error.lower()
    assert len(transport.sent) == sent_before  # nothing reached the wire
    # Reads still work while read-only (AC-21).
    assert reopened.get_turn(TURN).turn_id == TURN


def test_turn_id_regex_documents_mint_format() -> None:
    from coxswain.audit import TURN_ID_PATTERN

    assert TURN_ID_PATTERN.match("cx-1700000000000-k3x9qz")
    assert TURN_ID_PATTERN.match("cx-123-q7x9p2")  # epoch width not pinned
    assert not TURN_ID_PATTERN.match("cx-1700000000000-Q7X9P2")
    assert not TURN_ID_PATTERN.match(re.sub("cx", "xx", "cx-1700000000000-k3x9qz"))
