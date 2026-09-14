"""W1 tests for the §2.4 record shapes, the closed disposition vocabulary,
and NFR-7's kernel-side string caps.

Field names below are normative (spec §2: "an implementer must not choose their
own"), so these tests pin the exact field sets.
"""

from dataclasses import fields, is_dataclass
from dataclasses import FrozenInstanceError

import pytest

from coxswain.records import (
    DISPOSITIONS,
    SCHEMA_VERSION,
    STRING_CAPS,
    CoxswainTurnRecord,
    ExecutionOutcome,
    FftDecision,
    OverrideRecord,
    PendingIntent,
    StalenessFingerprint,
    truncate_to_cap,
)


def make_decision(**overrides) -> FftDecision:
    base = dict(
        turn_id="cx-1-abc123",
        session_id="sess-1",
        gate_seq=0,
        cue=0,
        category="initial",
        disposition="continue",
        payload_kind="concurrency",
        card_revision=0,
        ts=1000.0,
        fingerprint_id=None,
        override_id=None,
    )
    base.update(overrides)
    return FftDecision(**base)


def make_turn(**overrides) -> CoxswainTurnRecord:
    base = dict(
        schema_version=SCHEMA_VERSION,
        turn_id="cx-1-abc123",
        session_id="sess-1",
        state="open",
        opened_at=1000.0,
        closed_at=None,
        transcript=(),
        pending_intents=(),
        decisions=(),
        fingerprints=(),
        outcome=None,
    )
    base.update(overrides)
    return CoxswainTurnRecord(**base)


EXPECTED_FIELDS = {
    CoxswainTurnRecord: (
        "schema_version",
        "turn_id",
        "session_id",
        "state",
        "opened_at",
        "closed_at",
        "transcript",
        "pending_intents",
        "decisions",
        "fingerprints",
        "outcome",
    ),
    FftDecision: (
        "turn_id",
        "session_id",
        "gate_seq",
        "cue",
        "category",
        "disposition",
        "payload_kind",
        "card_revision",
        "ts",
        "fingerprint_id",
        "override_id",
    ),
    StalenessFingerprint: (
        "fingerprint_id",
        "turn_id",
        "gate_seq",
        "card_revision",
        "taken_at",
        "concurrency_active",
        "precondition_digest",
    ),
    OverrideRecord: (
        "schema_version",
        "override_id",
        "turn_id",
        "gate_seq",
        "cue",
        "justification",
        "ts",
    ),
    PendingIntent: (
        "turn_id",
        "parsed_call",
        "resolved_slots",
        "exited_cue",
        "unresolved_slots",
        "candidates",
        "card_revision",
    ),
    ExecutionOutcome: (
        "turn_id",
        "gate_seq",
        "status",
        "detail",
        "ts",
    ),
}


@pytest.mark.parametrize("record_cls", EXPECTED_FIELDS.keys())
def test_record_is_frozen_dataclass_with_spec_fields(record_cls) -> None:
    assert is_dataclass(record_cls)
    assert tuple(f.name for f in fields(record_cls)) == EXPECTED_FIELDS[record_cls]


@pytest.mark.parametrize(
    "record_cls",
    [
        CoxswainTurnRecord,
        FftDecision,
        StalenessFingerprint,
        OverrideRecord,
        PendingIntent,
        ExecutionOutcome,
    ],
)
def test_records_are_frozen(record_cls) -> None:
    """§2.4: 'frozen dataclasses'. Mutation must fail."""
    kwargs = {
        name: _default_value(name) for name in EXPECTED_FIELDS[record_cls]
    }
    record = record_cls(**kwargs)
    with pytest.raises(FrozenInstanceError):
        record.turn_id = "mutated"


def _default_value(field_name: str):
    defaults = {
        "schema_version": SCHEMA_VERSION,
        "turn_id": "cx-1-abc123",
        "session_id": "sess-1",
        "override_id": "cx-1-abc123:0:ovr",
        "fingerprint_id": "cx-1-abc123:0:fp",
        "state": "open",
        "opened_at": 1000.0,
        "closed_at": None,
        "gate_seq": 0,
        "cue": 3,
        "category": "initial",
        "disposition": "continue",
        "payload_kind": "precondition",
        "card_revision": 0,
        "ts": 1000.0,
        "taken_at": 1000.0,
        "concurrency_active": False,
        "precondition_digest": "sha256:deadbeef",
        "justification": "operator accepted the risk",
        "parsed_call": {"call": "transfer"},
        "resolved_slots": (),
        "exited_cue": 2,
        "unresolved_slots": (),
        "candidates": (),
        "status": "ok",
        "detail": None,
        "transcript": (),
        "pending_intents": (),
        "decisions": (),
        "fingerprints": (),
        "outcome": None,
    }
    return defaults[field_name]


class TestClosedVocabularies:
    def test_disposition_vocabulary_is_exactly_the_spec_set(self) -> None:
        assert DISPOSITIONS == frozenset(
            {
                "continue",
                "pass",
                "blocked:concurrent",
                "blocked:stale_card",
                "blocked:audit_unavailable",
                "clarify:incomplete",
                "clarify:not_found",
                "clarify:disambiguate",
                "clarify:precondition",
                "override:precondition",
                "aborted:drift",
            }
        )

    def test_fft_decision_rejects_unknown_disposition(self) -> None:
        with pytest.raises(ValueError, match="disposition"):
            make_decision(disposition="continue_but_secretly")

    def test_turn_state_vocabulary(self) -> None:
        for state in ("open", "closed", "abandoned"):
            make_turn(
                state=state,
                closed_at=None if state == "open" else 2000.0,
            )
        with pytest.raises(ValueError, match="state"):
            make_turn(state="half_open")

    def test_execution_outcome_status_vocabulary(self) -> None:
        from coxswain.records import EXECUTION_STATUSES, TURN_STATES

        assert EXECUTION_STATUSES == frozenset({"ok", "failed", "aborted_stale"})
        assert TURN_STATES == frozenset({"open", "closed", "abandoned"})
        with pytest.raises(ValueError, match="status"):
            ExecutionOutcome(
                turn_id="cx-1-abc123",
                gate_seq=0,
                status="sort_of_ok",
                detail=None,
                ts=1000.0,
            )

    def test_decision_category_vocabulary(self) -> None:
        from coxswain.records import DECISION_CATEGORIES

        assert DECISION_CATEGORIES == frozenset(
            {"initial", "re_entry", "confirm_recheck"}
        )
        with pytest.raises(ValueError, match="category"):
            make_decision(category="whenever")

    def test_schema_version_is_a_positive_int(self) -> None:
        assert isinstance(SCHEMA_VERSION, int)
        assert SCHEMA_VERSION >= 1


class TestIds:
    """§2.1 identifier formats. turn_id: cx-<epoch_ms>-<6 base36 chars>;
    fingerprint_id / override_id are turn-scoped composite keys."""

    def test_mint_turn_id_format(self) -> None:
        import re

        from coxswain.ids import mint_turn_id

        tid = mint_turn_id()
        assert re.fullmatch(r"cx-\d{13}-[0-9a-z]{6}", tid), tid

    def test_mint_turn_ids_are_unique(self) -> None:
        from coxswain.ids import mint_turn_id

        assert len({mint_turn_id() for _ in range(200)}) == 200

    def test_fingerprint_and_override_ids_are_turn_scoped_keys(self) -> None:
        from coxswain.ids import fingerprint_id_for, override_id_for

        assert fingerprint_id_for("cx-1-abc123", 2) == "cx-1-abc123:2:fp"
        assert override_id_for("cx-1-abc123", 0) == "cx-1-abc123:0:ovr"


class TestNfr7StringCaps:
    def test_caps_table_matches_spec_values(self) -> None:
        assert STRING_CAPS == {
            "nl_restatement": 400,
            "candidate_label": 120,
            "warning_badge_text": 64,
            "edited_field_value": 200,
            "override_justification": 500,
            "confirmation_phrase": 60,
        }

    def test_truncate_short_string_unchanged(self) -> None:
        assert truncate_to_cap("hello world", 10 + 90) == "hello world"

    def test_truncate_long_string_on_word_boundary_with_ellipsis(self) -> None:
        text = "word " * 40  # 200 chars, spaces throughout
        out = truncate_to_cap(text, 64)
        assert len(out) <= 64
        assert out.endswith("…")
        assert out.endswith("word…")

    def test_truncate_never_exceeds_cap_even_without_spaces(self) -> None:
        out = truncate_to_cap("a" * 300, 64)
        assert len(out) <= 64
        assert out.endswith("…")

    def test_override_record_justification_capped_before_persistence(self) -> None:
        long_justification = "justify " * 200  # 1600 chars
        rec = OverrideRecord(
            schema_version=SCHEMA_VERSION,
            override_id="cx-1-abc123:0:ovr",
            turn_id="cx-1-abc123",
            gate_seq=0,
            cue=3,
            justification=long_justification,
            ts=1000.0,
        )
        assert len(rec.justification) <= STRING_CAPS["override_justification"]
        assert rec.justification.endswith("…")
