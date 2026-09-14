"""clarify.py -- FR-8's deterministic answer matcher and the re-entry driver.

RED phase: every assertion here fails against a tree without
coxswain/src/coxswain/clarify.py. The contract under test:

- match_candidate matches a typed/clicked answer against the ALREADY-FETCHED
  candidate set only (label, then position, then simple synonym) -- no new
  grounding lookup, no model call (FR-8/§7). Zero or more-than-one matches
  return no candidate: fail closed, never guess.
- select_candidate is the click path's index selection (bounds-checked).
- answer_disambiguation / answer_not_found / answer_incomplete bind a user
  answer into the ParsedCall immutably (replace, never mutation), reading ONLY
  fields carried by the prior exit's payload.
- reenter_after_clarification re-enters the gate AT THE CUE THAT EXITED
  (FR-8), and resolve_clarification_loop repeats until the exited cue completes
  a pass with zero unresolved slots -- AC-20's two-ambiguous-references case.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import replace
from pathlib import Path

import pytest

from coxswain.clarify import (
    ClarificationError,
    answer_disambiguation,
    answer_incomplete,
    answer_not_found,
    match_candidate,
    reenter_after_clarification,
    resolve_clarification_loop,
    select_candidate,
)
from coxswain.fft.context import (
    GatePassContext,
    KernelInstance,
    MapInstanceSource,
    ParsedCall,
    UnresolvedSlot,
)
from coxswain.fft.gate import FftGate
from coxswain.schema.types import GroundingExitPayload

TURN = "cx-1700000000000-k3x9qz"

# Reuse W2's vetted doubles/builders verbatim.
from test_fft_gate import FakeAudit, FlakyProbe, make_ctx, make_state  # noqa: E402


def _candidates() -> tuple[KernelInstance, ...]:
    return (
        KernelInstance(name="PLT_CAR_L5AC_A00", resource_type="plate_carrier", position="rails 7"),
        KernelInstance(name="PLT_CAR_P3AC_A00", resource_type="plate_carrier", position="rails 13"),
    )


def _ctx(source=None):
    ctx = make_ctx(FakeAudit(), probe_result=False, instances=source)
    # make_ctx defaults turn_id to its module constant; identity is irrelevant
    # here beyond being non-empty, but keep the tests self-describing.
    return replace(ctx, turn_id=TURN)


def _transfer_call() -> ParsedCall:
    """A transfer whose source AND target are both ambiguous (AC-20's shape)."""
    return ParsedCall(
        name="transfer",
        receiver_type="liquid_handler",
        params={"vol": 50},
        unresolved_slots=(
            UnresolvedSlot(
                arg_name="source", reference="the plate carrier", resource_type="plate_carrier"
            ),
            UnresolvedSlot(
                arg_name="target", reference="the plate carrier", resource_type="plate_carrier"
            ),
        ),
    )


# --- match_candidate ---------------------------------------------------------------


class TestMatchCandidate:
    def test_label_match_is_case_insensitive_and_trimmed(self):
        hit = match_candidate("  plt_car_p3ac_a00 ", _candidates())
        assert hit.candidate is not None
        assert hit.candidate.name == "PLT_CAR_P3AC_A00"
        assert hit.strategy == "label"

    def test_position_match(self):
        hit = match_candidate("Rails 13", _candidates())
        assert hit.candidate is not None
        assert hit.candidate.position == "rails 13"
        assert hit.strategy == "position"

    def test_simple_synonym_singular_for_plural_position(self):
        # "rail 7" is a simple synonym of position "rails 7" (§4.3's copy).
        hit = match_candidate("rail 7", _candidates())
        assert hit.candidate is not None
        assert hit.candidate.position == "rails 7"
        assert hit.strategy == "synonym"

    def test_simple_synonym_drops_leading_article(self):
        hit = match_candidate("the rails 13", _candidates())
        assert hit.candidate is not None
        assert hit.candidate.position == "rails 13"

    def test_no_match_returns_no_candidate_not_a_guess(self):
        hit = match_candidate("rails 42", _candidates())
        assert hit.candidate is None
        assert hit.strategy is None

    def test_ambiguous_answer_at_a_strategy_returns_none_fail_closed(self):
        twins = (
            KernelInstance(name="PLT_A", resource_type="plate", position="rails 7"),
            KernelInstance(name="PLT_B", resource_type="plate", position="rails 7"),
        )
        assert match_candidate("rails 7", twins).candidate is None

    def test_non_string_answer_returns_no_candidate(self):
        assert match_candidate(None, _candidates()).candidate is None  # type: ignore[arg-type]
        assert match_candidate(17, _candidates()).candidate is None  # type: ignore[arg-type]

    def test_empty_candidate_set_matches_nothing(self):
        assert match_candidate("rails 7", ()).candidate is None


# --- select_candidate (click path) ---------------------------------------------------


class TestSelectCandidate:
    def test_index_selects_from_payload_order_as_given(self):
        assert select_candidate(_candidates(), 1).name == "PLT_CAR_P3AC_A00"

    def test_out_of_range_or_bad_index_raises_loud(self):
        with pytest.raises(ClarificationError):
            select_candidate(_candidates(), 2)
        with pytest.raises(ClarificationError):
            select_candidate(_candidates(), -1)
        with pytest.raises(ClarificationError):
            select_candidate(_candidates(), "0")  # type: ignore[arg-type]


# --- binding answers into the call ----------------------------------------------------


class TestBinding:
    def test_answer_disambiguation_by_index_binds_immutably(self):
        gate_outcome_call = _transfer_call()
        prior_payload_slot = "source"
        bound = answer_disambiguation(
            _disambiguate_prior(prior_payload_slot),
            gate_outcome_call,
            index=0,
        )
        # original untouched (frozen-by-contract: replace, never mutation)
        assert len(gate_outcome_call.unresolved_slots) == 2
        assert bound.params["source"] == "PLT_CAR_L5AC_A00"
        assert [s.arg_name for s in bound.unresolved_slots] == ["target"]

    def test_answer_disambiguation_typed_answer_routes_through_matcher(self):
        bound = answer_disambiguation(
            _disambiguate_prior("source"), _transfer_call(), answer="rail 13"
        )
        assert bound.params["source"] == "PLT_CAR_P3AC_A00"
        assert [s.arg_name for s in bound.unresolved_slots] == ["target"]

    def test_answer_disambiguation_unresolvable_answer_raises_fail_closed(self):
        with pytest.raises(ClarificationError):
            answer_disambiguation(_disambiguate_prior("source"), _transfer_call(), answer="rails 42")

    def test_answer_disambiguation_rejects_wrong_slot(self):
        with pytest.raises(ClarificationError):
            answer_disambiguation(_disambiguate_prior("bogus"), _transfer_call(), index=0)

    def test_answer_not_found_rephrases_the_reference(self):
        call = ParsedCall(
            name="transfer",
            receiver_type="liquid_handler",
            unresolved_slots=(UnresolvedSlot("source", "lane C", "plate"),),
        )
        prior = _not_found_prior()
        bound = answer_not_found(prior, call, new_reference="Plate A")
        assert bound.unresolved_slots[0].reference == "Plate A"
        assert "source" not in bound.params

    def test_answer_incomplete_supplies_missing_required_field(self):
        call = ParsedCall(
            name="dispense",
            receiver_type="liquid_handler",
            params={},
            missing_required=("target", "volume_ul"),
        )
        bound = answer_incomplete(_incomplete_prior(), call, supplies={"target": "A1"})
        assert bound.params["target"] == "A1"
        assert bound.missing_required == ("volume_ul",)

    def test_answer_incomplete_rejects_unrequested_field(self):
        with pytest.raises(ClarificationError):
            answer_incomplete(
                _incomplete_prior(),
                ParsedCall(name="dispense", receiver_type="liquid_handler"),
                supplies={"bogus": "x"},
            )


def _disambiguate_prior(slot: str):
    """A stand-in for the relevant slice of a real GateOutcome payload."""
    from types import SimpleNamespace

    return SimpleNamespace(
        exited_cue=2,
        disposition="clarify:disambiguate",
        payload=GroundingExitPayload(slot=slot, candidates=_candidates()),
    )


def _not_found_prior():
    from types import SimpleNamespace

    return SimpleNamespace(
        exited_cue=2,
        disposition="clarify:not_found",
        payload=GroundingExitPayload(slot="source", message='no plate matching "lane C"'),
    )


def _incomplete_prior():
    from types import SimpleNamespace

    return SimpleNamespace(
        exited_cue=1,
        disposition="clarify:incomplete",
        payload=None,
    )


# --- FR-8 re-entry semantics ------------------------------------------------------------


class TestReentry:
    def test_reenter_restarts_at_the_cue_that_exited(self):
        source = MapInstanceSource(
            {("the plate carrier", "plate_carrier"): list(_candidates())}
        )
        gate = FftGate()
        ctx = _ctx(source)
        first = gate.initial_pass(_transfer_call(), ctx)
        assert first.disposition == "clarify:disambiguate"
        assert first.exited_cue == 2

        bound = answer_disambiguation(first, _transfer_call(), index=0)
        second = reenter_after_clarification(gate, bound, ctx, prior=first)
        # Re-entered at cue 2 (not cue 3), gate_seq incremented.
        assert second.disposition == "clarify:disambiguate"
        assert second.exited_cue == 2
        assert second.gate_seq == first.gate_seq + 1

    def test_resolve_loop_repeats_until_unresolved_slots_empty_ac20_shape(self):
        """Two ambiguous references resolve BEFORE cue 3 is ever reached: each
        clarification re-enters cue 2, never advancing past an unresolved slot."""
        source = MapInstanceSource(
            {("the plate carrier", "plate_carrier"): list(_candidates())}
        )
        gate = FftGate()
        ctx = _ctx(source)
        first = gate.initial_pass(_transfer_call(), ctx)
        outcomes = resolve_clarification_loop(
            gate,
            ctx,
            prior=first,
            call=_transfer_call(),
            answers=[
                {"index": 0},
                {"index": 1},
            ],
        )
        dispositions = [o.disposition for o in outcomes]
        assert dispositions[0] == "clarify:disambiguate"
        assert dispositions[1] == "clarify:disambiguate"
        # The loop's LAST outcome must not be another clarify exit on slots:
        assert dispositions[-1] not in ("clarify:disambiguate", "clarify:not_found")
        # Every slot-driven exit was at cue 2.
        assert all(o.exited_cue == 2 for o in outcomes if o.disposition == "clarify:disambiguate")
        # gate_seq increments across each re-entry (FR-8); strictly increasing.
        seqs = [o.gate_seq for o in outcomes]
        assert seqs == sorted(seqs)
        assert len(set(seqs)) == len(seqs)

    def test_resolve_loop_stops_when_answers_run_out(self):
        source = MapInstanceSource(
            {("the plate carrier", "plate_carrier"): list(_candidates())}
        )
        gate = FftGate()
        ctx = _ctx(source)
        first = gate.initial_pass(_transfer_call(), ctx)
        outcomes = resolve_clarification_loop(
            gate, ctx, prior=first, call=_transfer_call(), answers=[]
        )
        assert len(outcomes) == 1
        assert outcomes[0].disposition == "clarify:disambiguate"


# --- structural: no model call on the click/typed path --------------------------------


class TestNoModelOnAnswerPath:
    def test_clarify_module_never_imports_parse_or_model_sources(self):
        """FR-8/§7: no model round-trip on click or typed path. The matcher
        operates on the fetched candidate set only; structurally, clarify.py
        imports nothing from any parse/model layer."""
        src_file = Path(__file__).resolve().parents[1] / "src" / "coxswain" / "clarify.py"
        tree = ast.parse(src_file.read_text())
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        banned = ("parse_source", "openai", "anthropic", "llm")
        offenders = sorted(n for n in imported if any(b in n.lower() for b in banned))
        assert offenders == [], f"clarify.py must not import {offenders}"

    def test_matcher_takes_only_answer_and_candidates(self):
        sig = inspect.signature(match_candidate)
        assert list(sig.parameters) == ["answer", "candidates"]
