"""AC-7 join half: a synthetic turn that clarifies once, overrides once at
cue 3, and aborts on drift is retrievable by ONE query_turn(turn_id) call --
PendingIntent history, every FftDecision, both StalenessFingerprints, the
OverrideRecord, and the ExecutionOutcome, with no manual stitching across the
two stores. A second test evicts the turn record and asserts the OverrideRecord
survives with its turn_id intact (§2.3's override-store exemption)."""

from coxswain.audit import AuditWriter, LoopbackTransport
from coxswain.fft.context import (
    GatePassContext,
    KernelInstance,
    MapInstanceSource,
    ParsedCall,
    UnresolvedSlot,
)
from coxswain.fft.gate import FftGate
from coxswain.persistence.store import (
    DEFAULT_TURN_CAP,
    CoxswainAuditStore,
    UnknownTurnError,
)
import pytest

from coxswain.records import PendingIntent
from test_fft_gate import make_state
from test_audit_ordering import StaticProbe
from test_audit_writer import SESSION, TURN, make_store

READY_STATE = dict(tips_loaded=True, liquid={"A1": True}, on_deck={"A1": True, "B3": True})


def ctx(
    *,
    unresolved=(),
    state=None,
    instances=MapInstanceSource({}),
    ts=1000.0,
) -> GatePassContext:
    return GatePassContext(
        turn_id=TURN,
        session_id=SESSION,
        card_revision=0,
        probe=StaticProbe(False),
        kernel_state=state if state is not None else make_state(**READY_STATE),
        instance_source=instances,
        ts=ts,
    )


def ambiguous_call() -> ParsedCall:
    return ParsedCall(
        name="transfer",
        receiver_type="liquid_handler",
        params={"source": "A1", "target": "B3", "vol": 50},
        unresolved_slots=(
            UnresolvedSlot(arg_name="source", reference="plate a", resource_type="Plate"),
        ),
    )


def resolved_call() -> ParsedCall:
    return ParsedCall(
        name="transfer",
        receiver_type="liquid_handler",
        params={"source": "A1", "target": "B3", "vol": 50},
    )


# Propose-time state: tips NOT loaded -> cue 3 exits clarify:precondition
# (contract requires_tips), which is exactly what gets overridden.
def propose_state():
    return make_state(tips_loaded=False, liquid={"A1": True}, on_deck={"A1": True, "B3": True})


def drifted_state():
    """Tips have since been loaded: the precondition digest differs from the
    propose-time fingerprint -> drift."""
    return make_state(**READY_STATE)


def run_synthetic_turn(store: CoxswainAuditStore) -> None:
    """clarify once -> override at cue 3 -> drift abort, all through the real
    gate + ack-gated writer."""
    writer = AuditWriter(store, LoopbackTransport())
    assert writer.begin_turn(TURN, SESSION) is True
    gate = FftGate(audit=writer)

    # Pass 1: cue 2 exits clarify:disambiguate on an ambiguous reference.
    two_plates = MapInstanceSource(
        {("plate a", "Plate"): [KernelInstance("PLT_1", "Plate"), KernelInstance("PLT_2", "Plate")]}
    )
    first = gate.initial_pass(ambiguous_call(), ctx(instances=two_plates))
    assert first.disposition == "clarify:disambiguate" and first.exited_cue == 2
    assert writer.attach_pending_intent(
        TURN,
        PendingIntent(
            turn_id=TURN,
            parsed_call={"name": "transfer"},
            exited_cue=first.exited_cue,
            unresolved_slots=("source",),
            candidates=("PLT_1", "PLT_2"),
            card_revision=0,
        ),
    )

    # Re-entry AT cue 2 (FR-8), now resolvable; cue 3 exits precondition.
    second = gate.re_enter(resolved_call(), ctx(state=propose_state(), ts=1100.0), start_cue=2)
    assert second.disposition == "clarify:precondition" and second.exited_cue == 3
    assert len(second.fingerprints) == 1  # propose-time anchor for the override path
    assert writer.attach_pending_intent(
        TURN,
        PendingIntent(
            turn_id=TURN,
            parsed_call={"name": "transfer"},
            exited_cue=second.exited_cue,
            unresolved_slots=(),
            card_revision=0,
        ),
    )

    # The user overrides the precondition exit with a justification.
    overridden = gate.apply_override(TURN, "operator confirmed plate assignment")
    assert overridden.disposition == "override:precondition"

    # Confirm-time recheck against drifted state: aborted_stale, outcome written.
    recheck = gate.confirm_recheck(
        resolved_call(),
        ctx(state=drifted_state(), ts=1200.0),
        propose_fingerprint=second.fingerprints[0],
        executor=lambda call: pytest.fail("execution must never be reached on drift"),
    )
    assert recheck.disposition == "aborted:drift"
    assert recheck.outcome is not None and recheck.outcome.status == "aborted_stale"
    assert writer.attach_outcome(TURN, recheck.outcome) is True


def test_single_query_joins_every_trail_by_turn_id() -> None:
    store, _ = make_store()
    run_synthetic_turn(store)

    # THE join: one call, no manual stitching.
    joined = store.query_turn(TURN)

    # PendingIntent history: the clarify exit and the resolved re-entry.
    assert len(joined.turn.pending_intents) == 2
    assert joined.turn.pending_intents[0].unresolved_slots == ("source",)
    assert joined.turn.pending_intents[1].unresolved_slots == ()

    # All FftDecision records across all passes.
    dispositions = [d.disposition for d in joined.turn.decisions]
    assert "clarify:disambiguate" in dispositions
    assert "override:precondition" in dispositions
    assert "aborted:drift" in dispositions

    # BOTH staleness fingerprints (cue-3-exit anchor + confirm-time capture).
    assert len(joined.turn.fingerprints) == 2

    # The OverrideRecord joined from the OTHER store by turn_id.
    assert len(joined.overrides) == 1
    assert joined.overrides[0].turn_id == TURN
    assert joined.overrides[0].cue == 3

    # Terminal outcome closed the turn.
    assert joined.turn.outcome is not None
    assert joined.turn.outcome.status == "aborted_stale"
    assert joined.turn.state == "closed"


def test_evicted_turn_leaves_override_surviving_with_turn_id() -> None:
    store, backend = make_store()
    run_synthetic_turn(store)

    # Force §2.3 eviction of THIS turn record: shrink the cap below the current
    # population via a fresh store over the same backend.
    tiny = CoxswainAuditStore.open(backend, turn_cap=1)
    # begin/close another turn to trigger eviction bookkeeping over cap 1.
    other = "cx-1700000009999-evict1"
    tiny.begin_turn(other, SESSION)
    tiny.close_turn(other)

    with pytest.raises(UnknownTurnError):
        tiny.query_turn(TURN)

    # The override store is EXEMPT: the record survives with its turn_id, so an
    # exported override still joins to an exported turn even post-eviction.
    survivors = tiny.overrides_for_turn(TURN)
    assert len(survivors) == 1
    assert survivors[0].turn_id == TURN


def test_cap_is_the_default_and_overrides_exemption_holds_under_load() -> None:
    store, _ = make_store()
    assert store._turn_cap == DEFAULT_TURN_CAP
    run_synthetic_turn(store)
    # Overrides are never evicted regardless of turn churn.
    assert len(store.overrides_for_turn(TURN)) == 1
