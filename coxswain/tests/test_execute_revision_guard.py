"""§3.1 layer 3 -- the kernel revision guard (AC-4's authoritative half).

The execute entrypoint must reject any execute request whose ``card_revision``
differs from the ``validated_revision`` stamped by the last completed
validation pass, with disposition ``blocked:stale_card``, BEFORE any PLR call
is dispatched -- catching a fast clicker, an Enter keypress on a stale focus,
and a programmatic dispatch alike, even if every UI layer above it is buggy.
"""

from __future__ import annotations

import time
from dataclasses import replace

import pytest

from coxswain.execute import (
    REJECTION_STALE_CARD,
    ExecuteRequest,
    Rejection,
    execute,
)
from coxswain.fft.context import ParsedCall
from coxswain.runtime.execution_flag import EXECUTION_FLAG

TURN = "cx-1700000000000-k3x9qz"
SESSION = "sess-test"


class CountingExecutor:
    """Stands in for the PLR dispatch; counts calls and observes the flag."""

    def __init__(self) -> None:
        self.calls: list[ParsedCall] = []
        self.flag_depths_at_call: list[int] = []

    def __call__(self, call: ParsedCall) -> dict:
        self.calls.append(call)
        self.flag_depths_at_call.append(EXECUTION_FLAG.depth)
        return {"dispatched": True}


def make_request(**overrides) -> ExecuteRequest:
    base = dict(
        turn_id=TURN,
        session_id=SESSION,
        gate_seq=2,
        card_revision=3,
        validated_revision=3,
        parsed_call=ParsedCall(
            name="transfer",
            receiver_type="liquid_handler",
            params={"source": "A1", "destination": "B3", "volume_ul": 50},
        ),
        typed_phrase=None,
        ts=1000.0,
    )
    base.update(overrides)
    return ExecuteRequest(**base)


@pytest.fixture(autouse=True)
def _isolated_flag():
    # The shared EXECUTION_FLAG instance is process-global; assert a clean
    # slate around each test so a leaky increment cannot hide.
    assert EXECUTION_FLAG.depth == 0, "test precondition: execution flag must start at zero"
    yield
    assert EXECUTION_FLAG.depth == 0, "execute() left the ExecutionFlag unbalanced"


def test_equal_revisions_reach_the_executor_exactly_once() -> None:
    executor = CountingExecutor()
    result = execute(make_request(), executor=executor)
    assert not isinstance(result, Rejection)
    assert len(executor.calls) == 1


def test_stale_revision_is_rejected_with_blocked_stale_card_and_zero_plr_calls() -> None:
    executor = CountingExecutor()
    request = make_request(card_revision=4)  # edited after last validation pass
    result = execute(request, executor=executor)
    assert isinstance(result, Rejection)
    assert result.code == REJECTION_STALE_CARD == "blocked:stale_card"
    assert executor.calls == []


def test_revision_ahead_of_validated_is_also_stale_not_just_behind() -> None:
    # §3.1 names equality, not direction: any difference denies.
    executor = CountingExecutor()
    request = make_request(validated_revision=5)
    result = execute(request, executor=executor)
    assert isinstance(result, Rejection)
    assert result.code == REJECTION_STALE_CARD
    assert executor.calls == []


def test_guard_fires_before_the_flag_increments() -> None:
    # A stale rejection must never even transiently claim "execution in
    # flight" -- cue 0 reads this flag.
    executor = CountingExecutor()
    result = execute(
        make_request(card_revision=9),
        executor=executor,
    )
    assert isinstance(result, Rejection)
    assert EXECUTION_FLAG.depth == 0


def test_guard_applies_to_every_tier_including_read_only() -> None:
    executor = CountingExecutor()
    request = make_request(
        card_revision=1,
        validated_revision=0,
        parsed_call=ParsedCall(
            name="read_absorbance",
            receiver_type="plate_reader",
            params={"at": "A1"},
        ),
    )
    result = execute(request, executor=executor)
    assert isinstance(result, Rejection)
    assert result.code == REJECTION_STALE_CARD
    assert executor.calls == []


def test_rejection_carries_turn_and_gate_identity_for_the_audit_surface() -> None:
    result = execute(make_request(card_revision=7), executor=CountingExecutor())
    assert isinstance(result, Rejection)
    assert result.turn_id == TURN
    assert result.gate_seq == 2


def test_dispatch_runs_under_an_incremented_execution_flag() -> None:
    """§4.5 source 1: execute.py owns the flag's increment/decrement around
    dispatch -- a concurrent cue-0 read DURING the PLR call must see active."""
    executor = CountingExecutor()
    result = execute(make_request(), executor=executor)
    assert not isinstance(result, Rejection)
    assert executor.flag_depths_at_call == [1]


# --- composition: confirm-time drift recheck stands between guards and hardware --


class OkAudit:
    def record(self, decision) -> bool:
        return True

    def record_override(self, record) -> bool:
        return True

    def record_fingerprint(self, fingerprint) -> bool:
        return True


class StaticProbe:
    def __init__(self, result) -> None:
        self.result = result

    def is_active(self):
        return self.result


def _state(liquid_a1: bool):
    from coxswain.fft.preconditions.state_models import (
        BooleanLiquidState,
        SimulationState,
        TipState,
    )

    state = SimulationState.default_boolean()
    state.tip_state = TipState(tips_loaded=True, tips_count=8)
    liquid = BooleanLiquidState()
    liquid.set_has_liquid("A1", liquid_a1)
    liquid.set_has_capacity("A1", True)
    state.liquid_state = liquid
    state.deck_state.place_on_deck("A1")
    state.deck_state.place_on_deck("B3")
    return state


def _ctx(ts: float, *, liquid_a1: bool, probe_result: bool = False):
    from coxswain.fft.context import GatePassContext, MapInstanceSource

    return GatePassContext(
        turn_id=TURN,
        session_id=SESSION,
        card_revision=3,
        probe=StaticProbe(probe_result),
        kernel_state=_state(liquid_a1),
        instance_source=MapInstanceSource({}),
        audit=OkAudit(),
        ts=ts,
    )


def test_confirm_time_drift_yields_aborted_stale_with_zero_plr_calls() -> None:
    """execute() routes through FftGate.confirm_recheck when given the propose
    fingerprint: kernel-state drift between proposal and confirm aborts to
    ``aborted_stale`` before the executor runs (FR-6 / AC-9 execution side)."""
    from coxswain.fft.gate import FftGate

    call = make_request().parsed_call  # transfer: reversible, no phrase toll
    gate = FftGate(audit=OkAudit())
    propose = gate.initial_pass(call, _ctx(ts=1000.0, liquid_a1=True))
    assert propose.disposition == "pass"
    assert propose.fingerprints, "propose pass must anchor a fingerprint"

    executor = CountingExecutor()
    request = make_request()  # revisions equal: revision guard passes
    result = execute(
        request,
        executor=executor,
        gate=gate,
        ctx=_ctx(ts=2000.0, liquid_a1=False),  # tip liquid changed meanwhile
        propose_fingerprint=propose.fingerprints[0],
    )
    assert not isinstance(result, Rejection)
    assert result.status == "aborted_stale"
    assert executor.calls == []


def test_clean_confirm_time_recheck_executes_once_through_the_gate() -> None:
    from coxswain.fft.gate import FftGate

    call = make_request().parsed_call
    gate = FftGate(audit=OkAudit())
    propose = gate.initial_pass(call, _ctx(ts=1000.0, liquid_a1=True))

    executor = CountingExecutor()
    result = execute(
        make_request(),
        executor=executor,
        gate=gate,
        ctx=_ctx(ts=2000.0, liquid_a1=True),
        propose_fingerprint=propose.fingerprints[0],
    )
    assert not isinstance(result, Rejection)
    assert result.status == "ok"
    assert len(executor.calls) == 1
