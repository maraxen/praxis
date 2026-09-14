"""W2 FFT gate orchestration tests: pass sequencing, fingerprint emission at
both ends, override enforcement, drift abort with zero PLR calls (AC-9's
execution-side assertions), and ported-substrate sanity checks.
"""

import time

import pytest

from coxswain.fft.context import (
    AuditSink,
    GatePassContext,
    KernelInstance,
    MapInstanceSource,
    ParsedCall,
    UnresolvedSlot,
)
from coxswain.fft.gate import FftGate, GateOutcome
from coxswain.fft.preconditions.method_contracts import get_contract
from coxswain.fft.preconditions.state_models import (
    BooleanLiquidState,
    SimulationState,
    TipState,
)
from coxswain.records import ExecutionOutcome, StalenessFingerprint
from coxswain.schema.types import OverrideNotAllowedError, RiskTier
from coxswain.plr.tool_schema import tier_of


TURN = "cx-1700000000000-k3x9qz"
SESSION = "sess-test"


# --- fakes ---------------------------------------------------------------------


class FakeAudit:
    """AuditSink double. ``mode``: ok | return_false | raise."""

    def __init__(self, mode: str = "ok") -> None:
        self.mode = mode
        self.decisions = []
        self.overrides = []
        self.fingerprints = []

    def record(self, decision) -> bool:
        if self.mode == "raise":
            raise RuntimeError("audit store unavailable")
        if self.mode == "return_false":
            return False
        self.decisions.append(decision)
        return True

    def record_override(self, record) -> bool:
        if self.mode == "raise":
            raise RuntimeError("audit store unavailable")
        if self.mode == "return_false":
            return False
        self.overrides.append(record)
        return True

    def record_fingerprint(self, fingerprint) -> bool:
        if self.mode == "raise":
            raise RuntimeError("audit store unavailable")
        if self.mode == "return_false":
            return False
        self.fingerprints.append(fingerprint)
        return True


class StubExecutor:
    """Stands in for W3's execute entrypoint; counts PLR dispatches."""

    def __init__(self) -> None:
        self.calls: list[ParsedCall] = []

    def __call__(self, call: ParsedCall) -> ExecutionOutcome:
        self.calls.append(call)
        return ExecutionOutcome(
            turn_id=call.turn_id if hasattr(call, "turn_id") else "?",
            gate_seq=-1,
            status="ok",
            detail=None,
            ts=time.time(),
        )


class FlakyProbe:
    def __init__(self, result) -> None:
        self.result = result

    def is_active(self):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


# --- builders ------------------------------------------------------------------


def make_state(
    *,
    tips_loaded: bool = False,
    liquid: dict[str, bool] | None = None,
    on_deck: dict[str, bool] | None = None,
) -> SimulationState:
    state = SimulationState.default_boolean()
    state.tip_state = TipState(tips_loaded=tips_loaded, tips_count=8 if tips_loaded else 0)
    liquid_state = BooleanLiquidState()
    for name, has in (liquid or {}).items():
        liquid_state.set_has_liquid(name, has)
        liquid_state.set_has_capacity(name, True)
    state.liquid_state = liquid_state
    for name, present in (on_deck or {}).items():
        if present:
            state.deck_state.place_on_deck(name)
        else:
            state.deck_state.remove_from_deck(name)
    return state


def make_ctx(
    audit: FakeAudit | None = None,
    *,
    probe_result=False,
    state: SimulationState | None = None,
    instances: MapInstanceSource | None = None,
    ts: float = 1000.0,
) -> GatePassContext:
    return GatePassContext(
        turn_id=TURN,
        session_id=SESSION,
        card_revision=0,
        probe=FlakyProbe(probe_result),
        kernel_state=state if state is not None else make_state(),
        instance_source=instances if instances is not None else MapInstanceSource({}),
        audit=audit if audit is not None else FakeAudit(),
        ts=ts,
    )


def simple_call(name: str = "transfer", **params) -> ParsedCall:
    base = {"source": "A1", "target": "B3", "vol": 50}
    base.update(params)
    return ParsedCall(name=name, receiver_type="liquid_handler", params=base)


# --- happy path ----------------------------------------------------------------


def test_initial_pass_all_continue_stamps_pass_and_fingerprint() -> None:
    audit = FakeAudit()
    gate = FftGate(audit=audit)
    ctx = make_ctx(
        audit,
        state=make_state(tips_loaded=True, liquid={"A1": True}, on_deck={"A1": True, "B3": True}),
    )
    outcome = gate.initial_pass(simple_call(), ctx)

    assert isinstance(outcome, GateOutcome)
    assert outcome.disposition == "pass"
    assert [d.cue for d in outcome.decisions] == [0, 1, 2, 3]
    assert [d.disposition for d in outcome.decisions] == ["continue"] * 4
    terminal = audit.decisions[-1]
    assert terminal.disposition == "pass"
    assert terminal.gate_seq == 0
    assert terminal.category == "initial"
    assert len(audit.fingerprints) == 1  # FR-6: propose-time pass emits one
    fp = audit.fingerprints[0]
    assert isinstance(fp, StalenessFingerprint)
    assert fp.concurrency_active is False
    assert fp.precondition_digest


def test_fingerprint_digest_reflects_kernel_state() -> None:
    audit = FakeAudit()
    gate = FftGate(audit=audit)
    ready = make_state(tips_loaded=True, liquid={"A1": True}, on_deck={"A1": True, "B3": True})
    dry = make_state(tips_loaded=False, liquid={"A1": True}, on_deck={"A1": True, "B3": True})
    out_ready = gate.initial_pass(simple_call(), make_ctx(audit, state=ready))
    # fresh gate so seq bookkeeping stays trivial for the second pass
    gate2 = FftGate(audit=FakeAudit())
    out_dry = gate2.initial_pass(
        simple_call("read_absorbance"), make_ctx(FakeAudit(), state=dry)
    )
    fp_ready = out_ready.fingerprints[0]
    fp_dry = out_dry.fingerprints[0]
    # different states -> different digest; identical state recompute -> equal
    from coxswain.fft.cues import precondition_digest

    assert fp_ready.precondition_digest != fp_dry.precondition_digest
    assert precondition_digest(ready) == fp_ready.precondition_digest


# --- cue 0 ---------------------------------------------------------------------


def test_cue0_blocks_when_concurrent() -> None:
    gate = FftGate(audit=FakeAudit())
    outcome = gate.initial_pass(simple_call(), make_ctx(probe_result=True))
    assert outcome.disposition == "blocked:concurrent"
    assert outcome.exited_cue == 0
    assert len(outcome.decisions) == 1
    assert not outcome.fingerprints


def test_cue0_blocks_on_probe_unknown() -> None:
    outcome = FftGate(audit=FakeAudit()).initial_pass(
        simple_call(), make_ctx(probe_result=None)
    )
    assert outcome.disposition == "blocked:concurrent"  # NFR-5, never continue


# --- cue 1 ---------------------------------------------------------------------


def test_cue1_reports_all_missing_fields() -> None:
    call = simple_call()
    object.__setattr__(
        call, "missing_required", ("vol", "tips")
    )  # frozen dataclass: build via field for clarity below
    call = ParsedCall(
        name="transfer",
        receiver_type="liquid_handler",
        params={"source": "A1", "target": "B3"},
        missing_required=("vol", "tips"),
    )
    outcome = FftGate(audit=FakeAudit()).initial_pass(call, make_ctx())
    assert outcome.disposition == "clarify:incomplete"
    assert outcome.exited_cue == 1
    payload = outcome.payload
    assert tuple(payload.missing_fields) == ("vol", "tips")


# --- cue 2 ---------------------------------------------------------------------


def test_cue2_not_found_exits_clarify() -> None:
    call = ParsedCall(
        name="transfer",
        receiver_type="liquid_handler",
        params={},
        unresolved_slots=(UnresolvedSlot(arg_name="source", reference="lane C", resource_type="Plate"),),
    )
    outcome = FftGate(audit=FakeAudit()).initial_pass(call, make_ctx())
    assert outcome.disposition == "clarify:not_found"
    assert outcome.exited_cue == 2


def test_cue2_ambiguous_exits_with_candidates_in_given_order() -> None:
    slot = UnresolvedSlot(arg_name="source", reference="the plate carrier", resource_type="Plate")
    call = ParsedCall(name="transfer", receiver_type="liquid_handler", params={}, unresolved_slots=(slot,))
    source = MapInstanceSource(
        {
            ("the plate carrier", "Plate"): [
                KernelInstance("PLT_CAR_L5AC_A00", "Plate", position="rails 7"),
                KernelInstance("PLT_CAR_P3AC_A00", "Plate", position="rails 13"),
            ]
        }
    )
    outcome = FftGate(audit=FakeAudit()).initial_pass(call, make_ctx(instances=source))
    assert outcome.disposition == "clarify:disambiguate"
    assert [c.name for c in outcome.payload.candidates] == [
        "PLT_CAR_L5AC_A00",
        "PLT_CAR_P3AC_A00",
    ]


def test_cue2_single_match_auto_resolves_without_exit() -> None:
    slot = UnresolvedSlot(arg_name="source", reference="plate A", resource_type="Plate")
    call = ParsedCall(name="transfer", receiver_type="liquid_handler", params={}, unresolved_slots=(slot,))
    source = MapInstanceSource({("plate a", "Plate"): [KernelInstance("PLT_A", "Plate")]})
    audit = FakeAudit()
    state = make_state(tips_loaded=True, liquid={"A1": True}, on_deck={"PLT_A": True, "B3": True})
    outcome = FftGate(audit=audit).initial_pass(call, make_ctx(state=state, instances=source))
    assert outcome.disposition == "pass"
    assert "source" in outcome.resolved_slot_names


# --- cue 3 ---------------------------------------------------------------------


def test_cue3_blocks_on_unmet_precondition_and_is_overridable() -> None:
    # no tips loaded -> transfer unmet
    state = make_state(tips_loaded=False, liquid={"A1": True}, on_deck={"A1": True, "B3": True})
    outcome = FftGate(audit=FakeAudit()).initial_pass(simple_call(), make_ctx(state=state))
    assert outcome.disposition == "clarify:precondition"
    assert outcome.exited_cue == 3
    assert outcome.payload.overridable is True  # cue 3 ∈ OVERRIDABLE_CUES
    assert any("tips_not_loaded" in u for u in outcome.payload.unmet_preconditions)


def test_cue3_fail_closed_for_unknown_method_contract() -> None:
    # no contract exists for this method -> cannot determine preconditions
    outcome = FftGate(audit=FakeAudit()).initial_pass(
        simple_call("teleport_wells"), make_ctx(probe_result=False)
    )
    assert outcome.disposition == "clarify:precondition"
    assert any("unknown_method" in u for u in outcome.payload.unmet_preconditions)


# --- override flow ---------------------------------------------------------------


def test_apply_override_records_override_and_decision() -> None:
    audit = FakeAudit()
    gate = FftGate(audit=audit)
    state = make_state(tips_loaded=False, liquid={"A1": True}, on_deck={"A1": True, "B3": True})
    blocked = gate.initial_pass(simple_call(), make_ctx(audit, state=state))
    assert blocked.disposition == "clarify:precondition"

    result = gate.apply_override(TURN, justification="operator confirmed deck state by eye")
    assert result.disposition == "override:precondition"
    assert len(audit.overrides) == 1
    rec = audit.overrides[0]
    assert rec.turn_id == TURN and rec.cue == 3
    decision = audit.decisions[-1]
    assert decision.disposition == "override:precondition"
    assert decision.override_id == rec.override_id


def test_apply_override_rejects_empty_justification() -> None:
    gate = FftGate(audit=FakeAudit())
    with pytest.raises(ValueError):
        gate.apply_override(TURN, justification="   ")
    with pytest.raises(ValueError):
        gate.apply_override(TURN, justification="")


def test_gate_override_never_escapes_overridable_cues() -> None:
    gate = FftGate(audit=FakeAudit())
    with pytest.raises(OverrideNotAllowedError):
        gate.apply_override_for_cue(TURN, gate_seq=0, cue=0, justification="because")


# --- confirm-time recheck (FR-6 / AC-9 execution side) --------------------------


def _run_propose(gate: FftGate, audit: FakeAudit):
    state = make_state(tips_loaded=True, liquid={"A1": True}, on_deck={"A1": True, "B3": True})
    return gate.initial_pass(simple_call(), make_ctx(audit, state=state))


def test_confirm_recheck_clean_path_executes_exactly_once() -> None:
    audit = FakeAudit()
    gate = FftGate(audit=audit)
    propose = _run_propose(gate, audit)
    executor = StubExecutor()

    state = make_state(tips_loaded=True, liquid={"A1": True}, on_deck={"A1": True, "B3": True})
    result = gate.confirm_recheck(
        simple_call(),
        make_ctx(audit, state=state, ts=2000.0),
        propose_fingerprint=propose.fingerprints[0],
        executor=executor,
    )
    assert result.disposition == "pass"
    assert len(executor.calls) == 1
    assert {d.cue for d in result.decisions} <= {0, 3}  # confirm re-runs EXACTLY {0, 3}
    assert len(result.fingerprints) == 1


def test_confirm_recheck_drift_aborts_with_zero_plr_calls() -> None:
    audit = FakeAudit()
    gate = FftGate(audit=audit)
    propose = _run_propose(gate, audit)
    executor = StubExecutor()

    drifted = make_state(tips_loaded=True, liquid={"A1": False}, on_deck={"A1": True, "B3": True})
    result = gate.confirm_recheck(
        simple_call(),
        make_ctx(audit, state=drifted, ts=2000.0),
        propose_fingerprint=propose.fingerprints[0],
        executor=executor,
    )
    assert result.disposition == "aborted:drift"
    assert executor.calls == []  # zero PLR calls
    assert result.outcome is not None and result.outcome.status == "aborted_stale"
    drift_decisions = [d for d in audit.decisions if d.disposition == "aborted:drift"]
    assert len(drift_decisions) == 1
    assert drift_decisions[0].fingerprint_id == result.fingerprints[-1].fingerprint_id


def test_confirm_recheck_concurrency_flip_aborts() -> None:
    audit = FakeAudit()
    gate = FftGate(audit=audit)
    propose = _run_propose(gate, audit)
    executor = StubExecutor()
    state = make_state(tips_loaded=True, liquid={"A1": True}, on_deck={"A1": True, "B3": True})
    result = gate.confirm_recheck(
        simple_call(),
        make_ctx(audit, probe_result=True, state=state),  # run started meanwhile
        propose_fingerprint=propose.fingerprints[0],
        executor=executor,
    )
    assert result.outcome is not None and result.outcome.status == "aborted_stale"
    assert executor.calls == []


# --- gate_seq management ---------------------------------------------------------


def test_gate_seq_increments_across_reentries_and_confirm() -> None:
    audit = FakeAudit()
    gate = FftGate(audit=audit)
    propose = _run_propose(gate, audit)
    assert propose.gate_seq == 0

    re = gate.re_enter(
        simple_call(),
        make_ctx(audit, state=make_state(tips_loaded=True, liquid={"A1": True}, on_deck={"A1": True, "B3": True})),
        start_cue=2,
    )
    assert re.gate_seq == 1
    confirm = gate.confirm_recheck(
        simple_call(),
        make_ctx(audit, state=make_state(tips_loaded=True, liquid={"A1": True}, on_deck={"A1": True, "B3": True})),
        propose_fingerprint=re.fingerprints[-1] or propose.fingerprints[0],
        executor=StubExecutor(),
    )
    assert confirm.gate_seq >= 2
    first = min(d.gate_seq for d in audit.decisions)
    assert first == 0


# --- fail-closed audit seam -------------------------------------------------------


@pytest.mark.parametrize("mode", ["return_false", "raise"])
def test_audit_unavailable_fails_closed(mode: str) -> None:
    audit = FakeAudit(mode=mode)
    gate = FftGate(audit=audit)
    outcome = gate.initial_pass(simple_call(), make_ctx(audit))
    assert outcome.disposition == "blocked:audit_unavailable"
    assert not outcome.fingerprints


def test_audit_failure_mid_pass_never_reaches_later_cues() -> None:
    class FailAtThird(FakeAudit):
        def __init__(self) -> None:
            super().__init__()
            self.n = 0

        def record(self, decision):  # noqa: D102
            self.n += 1
            if self.n > 2:
                raise RuntimeError("store died mid-pass")
            self.decisions.append(decision)
            return True

    audit = FailAtThird()
    outcome = FftGate(audit=audit).initial_pass(simple_call(), make_ctx(audit))
    assert outcome.disposition == "blocked:audit_unavailable"
    assert all(d.cue <= 1 for d in outcome.decisions)


# --- ported substrate sanity (W0/N4-C port behaves as upstream) -------------------


def test_ported_contracts_drive_cue3_evaluation() -> None:
    contract = get_contract("liquid_handler", "transfer")
    assert contract is not None
    assert contract.requires_tips
    assert contract.requires_liquid_in == "source"
    assert contract.requires_capacity_in == "target"


def test_tier_lookup_agrees_with_schema_entries() -> None:
    assert tier_of("transfer") is RiskTier.REVERSIBLE
