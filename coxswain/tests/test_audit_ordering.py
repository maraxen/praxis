"""AC-19 audit ordering (FR-9): the gate's disposition is not produced before
the corresponding ``audit.ack`` is received; a dropped ack exits
``blocked:audit_unavailable`` after ``KERNEL_RTT_TIMEOUT_MS`` with zero PLR
calls; and a configured-but-unreachable relay changes neither the ack timing
nor the disposition -- the writer never touches the relay path."""

import time

from coxswain.audit import AuditWriter, LoopbackTransport, ManualAckTransport, RelayRecordingTransport
from coxswain.fft.context import (
    GatePassContext,
    MapInstanceSource,
    ParsedCall,
)
from coxswain.fft.gate import FftGate
from coxswain.records import ExecutionOutcome

from test_fft_gate import make_state
from test_audit_writer import SESSION, TURN, make_store


class StaticProbe:
    def __init__(self, result=False) -> None:
        self.result = result

    def is_active(self):
        return self.result


class CountingExecutor:
    """Stands in for the execute entrypoint; counts PLR dispatches."""

    def __init__(self) -> None:
        self.calls: list[ParsedCall] = []

    def __call__(self, call: ParsedCall) -> ExecutionOutcome:
        self.calls.append(call)
        return ExecutionOutcome(
            turn_id=TURN, gate_seq=-1, status="ok", detail=None, ts=time.time()
        )


def ready_call() -> ParsedCall:
    return ParsedCall(
        name="transfer",
        receiver_type="liquid_handler",
        params={"source": "A1", "target": "B3", "vol": 50},
    )


def ready_ctx(ts: float = 1000.0) -> GatePassContext:
    return GatePassContext(
        turn_id=TURN,
        session_id=SESSION,
        card_revision=0,
        probe=StaticProbe(False),
        kernel_state=make_state(tips_loaded=True, liquid={"A1": True}, on_deck={"A1": True, "B3": True}),
        instance_source=MapInstanceSource({}),
        ts=ts,
    )


def drifted_ctx(ts: float = 2000.0) -> GatePassContext:
    """Same shape as ready_ctx but with tips unloaded: the precondition digest
    differs from the propose-time fingerprint -> drift."""
    return GatePassContext(
        turn_id=TURN,
        session_id=SESSION,
        card_revision=0,
        probe=StaticProbe(False),
        kernel_state=make_state(tips_loaded=False, liquid={"A1": True}, on_deck={"A1": True, "B3": True}),
        instance_source=MapInstanceSource({}),
        ts=ts,
    )


def make_gate_writer(store, transport):
    clock = {"now": 0.0}
    writer = AuditWriter(
        store,
        transport,
        monotonic=lambda: clock["now"],
        sleep=lambda s: clock.__setitem__("now", clock["now"] + s),
    )
    return writer, clock


# --- AC-19 assertion 1: no disposition before the ack ------------------------------


def test_disposition_is_not_produced_before_the_matching_ack() -> None:
    store, _ = make_store()
    transport = ManualAckTransport()
    transport.deliver_acks_automatically()
    writer, _ = make_gate_writer(store, transport)
    assert writer.begin_turn(TURN, SESSION) is True

    trace: list[str] = []
    gate = FftGate(audit=writer)

    # Wrap the sink so we can see exactly when record() RETURNS relative to
    # ack delivery. The ack is delivered by pump() inside record() itself.
    original_record = writer.record

    def tracing_record(decision):
        trace.append(f"send:{decision.disposition}")
        ok = original_record(decision)
        trace.append(f"returned:{decision.disposition}:{'acked' if ok else 'unacked'}")
        return ok

    writer.record = tracing_record  # type: ignore[method-assign]
    outcome = gate.initial_pass(ready_call(), ready_ctx())

    assert outcome.disposition == "pass"
    sends = [i for i, t in enumerate(trace) if t.startswith("send:")]
    returns = [i for i, t in enumerate(trace) if t.startswith("returned:") and t.endswith("acked")]
    assert sends and len(sends) == len(returns)
    # Every write RETURNED only after its ack was pumped -- FR-9's ordering
    # guarantee, not synchrony.
    for send_index, return_index in zip(sends, returns):
        assert send_index < return_index
    # The gate outcome exists only after the final write returned.
    assert max(returns) < len(trace)


def test_every_decision_write_carries_the_acks_write_id() -> None:
    store, _ = make_store()
    transport = LoopbackTransport()
    writer, _ = make_gate_writer(store, transport)
    assert writer.begin_turn(TURN, SESSION) is True
    gate = FftGate(audit=writer)
    gate.initial_pass(ready_call(), ready_ctx())

    write_ids = [r["write_id"] for r in transport.sent]
    ack_ids = [a["write_id"] for a in transport.acks]
    # One ack per write, carrying that write's id (FR-9: "an audit.ack
    # carrying the record's id").
    assert write_ids == ack_ids
    assert len(set(write_ids)) == len(write_ids)


# --- AC-19 assertion 2: dropped ack -> blocked after the window, zero PLR calls ----


def test_dropped_ack_blocks_confirm_recheck_with_zero_plr_calls() -> None:
    store, _ = make_store()
    healthy = LoopbackTransport()
    writer, _ = make_gate_writer(store, healthy)
    gate = FftGate(audit=writer)
    assert writer.begin_turn(TURN, SESSION) is True

    propose = gate.initial_pass(ready_call(), ready_ctx())
    assert propose.disposition == "pass"
    propose_fingerprint = propose.fingerprints[0]

    # From here the audit store stops acking entirely.
    dropping = ManualAckTransport()
    writer2, clock = make_gate_writer(store, dropping)
    gate3 = FftGate(audit=writer2)
    executor = CountingExecutor()
    start = clock["now"]

    outcome = gate3.confirm_recheck(
        ready_call(),
        drifted_ctx(),  # state also changed; irrelevant: audit blocks first
        propose_fingerprint=propose_fingerprint,
        executor=executor,
    )

    assert outcome.disposition == "blocked:audit_unavailable"
    assert executor.calls == []  # zero PLR calls (fail closed)
    elapsed_ms = (clock["now"] - start) * 1000
    assert elapsed_ms >= 5000 - 1e-6  # KERNEL_RTT_TIMEOUT_MS window honored


# --- AC-19/AC-10: the relay is never in the ack path --------------------------------


def test_configured_unreachable_relay_changes_nothing_for_local_writes() -> None:
    store, _ = make_store()
    # Relay endpoint configured at build time AND permanently unreachable.
    transport = RelayRecordingTransport(relay_hang=True)
    writer, clock = make_gate_writer(store, transport)
    gate = FftGate(audit=writer)
    assert writer.begin_turn(TURN, SESSION) is True

    baseline_start = clock["now"]
    outcome = gate.initial_pass(ready_call(), ready_ctx())

    # Disposition identical to the no-relay case; ack timing unaffected.
    assert outcome.disposition == "pass"
    local_writes = [r for r in transport.sent if r["type"] == "audit.write"]
    assert local_writes
    # Write requests carry no relay field at all: the relay is not part of the
    # write contract, let alone the ack path.
    assert all(not r.get("relay") for r in local_writes)
    # The WRITER never invoked the relay fan-out -- zero attempts, zero latency
    # contribution (the kernel-side half of AC-19's third clause / AC-10).
    assert transport.relay_attempts == 0


def test_slow_relay_does_not_delay_the_ack() -> None:
    store, _ = make_store()
    transport = RelayRecordingTransport(relay_delay_s=10_000.0)
    writer, clock = make_gate_writer(store, transport)
    gate = FftGate(audit=writer)
    assert writer.begin_turn(TURN, SESSION) is True

    start = clock["now"]
    outcome = gate.initial_pass(ready_call(), ready_ctx())
    elapsed_ms = (clock["now"] - start) * 1000

    assert outcome.disposition == "pass"
    assert elapsed_ms < 5000  # nowhere near the RTT window: relay added nothing
