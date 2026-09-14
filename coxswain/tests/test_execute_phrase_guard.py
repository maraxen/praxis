"""AC-13's kernel half: the execute entrypoint enforces the FR-3 confirmation
phrase for ``irreversible`` calls INDEPENDENT of the UI.

A UI that forgets the check does not reach hardware: a missing, empty,
strict-prefix, one-character-off, or different-call ``typed_phrase`` is
rejected with ZERO PLR calls, directly at the execute entrypoint. A test that
only asserts a disabled attribute does not satisfy AC-13 -- this file is what
does.
"""

import pytest

from coxswain.execute import (
    REJECTION_PHRASE_MISMATCH,
    REJECTION_PHRASE_REQUIRED,
    ExecuteRequest,
    Rejection,
    execute,
)
from coxswain.fft.context import ParsedCall
from coxswain.phrase import derive_phrase
from coxswain.plr.tool_schema import TOOL_SCHEMA, tier_of
from coxswain.schema.types import RiskTier

TURN = "cx-1700000000000-q7x9p2"
SESSION = "sess-test"

DISCARD = ParsedCall(
    name="discard_tips",
    receiver_type="liquid_handler",
    params={"what": "tips", "at": "C3"},
)

REQUIRED_DISCARD = derive_phrase(
    {"verb": TOOL_SCHEMA["discard_tips"].verb, "params": DISCARD.params}
)


class CountingExecutor:
    def __init__(self) -> None:
        self.calls: list[ParsedCall] = []

    def __call__(self, call: ParsedCall) -> dict:
        self.calls.append(call)
        return {"dispatched": True}


def make_request(**overrides) -> ExecuteRequest:
    base = dict(
        turn_id=TURN,
        session_id=SESSION,
        gate_seq=0,
        card_revision=0,
        validated_revision=0,
        parsed_call=DISCARD,
        typed_phrase=None,
        ts=1000.0,
    )
    base.update(overrides)
    return ExecuteRequest(**base)


@pytest.fixture(autouse=True)
def _preconditions():
    assert tier_of(DISCARD) is RiskTier.IRREVERSIBLE
    assert REQUIRED_DISCARD == "discard tips at C3"


# --- the four AC-13 rejection cases plus missing/empty ---------------------------


@pytest.mark.parametrize(
    "typed",
    [
        None,  # missing entirely
        "",  # empty string
        "   ",  # whitespace only
        "discard tips at",  # strict prefix of the required phrase
        "discard tips at C4",  # exactly one character changed
        "transfer to B1 +2 more",  # the phrase of a DIFFERENT call
        "discard tips at C3!",  # punctuation is NOT normalized away (FR-3: no other normalization)
    ],
)
def test_bad_phrase_is_rejected_with_zero_plr_calls(typed: str | None) -> None:
    executor = CountingExecutor()
    result = execute(make_request(typed_phrase=typed), executor=executor)
    assert isinstance(result, Rejection)
    assert result.code in {REJECTION_PHRASE_REQUIRED, REJECTION_PHRASE_MISMATCH}
    assert executor.calls == []


def test_correct_phrase_executes_exactly_once() -> None:
    executor = CountingExecutor()
    result = execute(make_request(typed_phrase="discard tips at C3"), executor=executor)
    assert not isinstance(result, Rejection)
    assert len(executor.calls) == 1


def test_normalized_match_is_accepted_case_and_whitespace_only() -> None:
    """FR-3 matching: case-insensitive with collapsed internal whitespace and
    trimmed ends -- acceptance must be exactly as broad as the rule, too."""
    executor = CountingExecutor()
    result = execute(
        make_request(typed_phrase="  DISCARD   tips AT c3 "), executor=executor
    )
    assert not isinstance(result, Rejection)
    assert len(executor.calls) == 1


def test_multi_target_irreversible_uses_its_own_derived_phrase() -> None:
    waste_multi = ParsedCall(
        name="dispense_to_waste",
        receiver_type="liquid_handler",
        params={"destination": ["waste_a", "waste_b"]},
    )
    assert tier_of(waste_multi) is RiskTier.IRREVERSIBLE
    executor = CountingExecutor()
    request = make_request(
        parsed_call=waste_multi, typed_phrase="discard waste_a +1 more"
    )
    result = execute(request, executor=executor)
    assert not isinstance(result, Rejection)
    assert len(executor.calls) == 1

    stale_prefix = CountingExecutor()
    result = execute(
        make_request(parsed_call=waste_multi, typed_phrase="discard waste_a +"),
        executor=stale_prefix,
    )
    assert isinstance(result, Rejection)
    assert stale_prefix.calls == []


def test_reversible_and_read_only_tiers_need_no_phrase() -> None:
    executor = CountingExecutor()
    transfer_single = ParsedCall(
        name="transfer",
        receiver_type="liquid_handler",
        params={"source": "A1", "destination": "B3"},
    )
    assert tier_of(transfer_single) is RiskTier.REVERSIBLE
    result = execute(
        make_request(parsed_call=transfer_single, typed_phrase=None), executor=executor
    )
    assert not isinstance(result, Rejection)
    assert len(executor.calls) == 1
