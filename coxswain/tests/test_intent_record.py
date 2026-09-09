"""P2.0 deliverable 5: intent-record shape + slot-agreement checking.

The intent record is THE per-example supervision contract consumed by the
P2.2 execution-verify harness: intended call sequence, expected effects, and
the slot-agreement axis (C-M3). Defined here (coxswain/plr) rather than in a
future training/ workspace member because coxswain may never import training/
(F2 rev2) while both sides must share ONE shape.
"""

import pytest

from coxswain.plr.intent_record import (
    IntentRecord,
    PredictedCall,
    check_intent_agreement,
)
from coxswain.plr.slot_derivation import DerivedSlot

TRANSFER_INTENT: IntentRecord = {
    "record_id": "golden-transfer-001",
    "utterance": "transfer 50 uL from A1 to B3",
    "source": "golden",
    "calls": [
        {
            "name": "transfer",
            "params": {"source": "A1", "destination": "B3", "volume_ul": 50},
            "missing_required": [],
            "unresolved_slots": [
                {"arg_name": "source", "reference": "A1", "resource_type": "container"},
                {"arg_name": "destination", "reference": "B3", "resource_type": "container"},
            ],
        }
    ],
    "expected_effects": [{"effect": "transfers", "target_ref": "B3"}],
}


# --- shape -----------------------------------------------------------------------


def test_intent_record_holds_sequence_effects_and_slot_axis() -> None:
    assert TRANSFER_INTENT["calls"][0]["name"] == "transfer"
    assert TRANSFER_INTENT["expected_effects"][0]["effect"] == "transfers"
    slots = TRANSFER_INTENT["calls"][0]["unresolved_slots"]
    assert slots[0]["arg_name"] == "source"


def test_clarify_class_record_has_empty_calls_and_gap_annotations() -> None:
    """D7: clarify-expected examples supervise NO tool_call or an incomplete
    one; the record shape carries that without free-text slot naming."""
    record: IntentRecord = {
        "record_id": "synthetic-incomplete-001",
        "utterance": "aspirate 10 uL",
        "source": "synthetic",
        "calls": [
            {
                "name": "aspirate",
                "params": {},
                "missing_required": ["source", "volume_ul"],
                "unresolved_slots": [],
            }
        ],
        "expected_effects": [],
    }
    assert record["calls"][0]["missing_required"] == ["source", "volume_ul"]
    assert record["expected_effects"] == []


# --- agreement checker -----------------------------------------------------------


def test_exact_prediction_agrees() -> None:
    predicted = [PredictedCall(name="transfer", params=TRANSFER_INTENT["calls"][0]["params"])]
    report = check_intent_agreement(predicted, TRANSFER_INTENT)
    assert report.overall
    assert report.sequence_match and report.names_match and report.params_match
    assert report.gaps_match


def test_name_mismatch_flagged_with_reason() -> None:
    predicted = [PredictedCall(name="aspirate", params={"source": "A1"})]
    report = check_intent_agreement(predicted, TRANSFER_INTENT)
    assert not report.names_match
    assert not report.overall
    assert any("name" in r for r in report.reasons)


def test_sequence_length_mismatch_flagged() -> None:
    predicted = [
        PredictedCall(name="transfer", params={}),
        PredictedCall(name="transfer", params={}),
    ]
    report = check_intent_agreement(predicted, TRANSFER_INTENT)
    assert not report.sequence_match
    assert not report.overall


def test_params_mismatch_flagged() -> None:
    predicted = [PredictedCall(name="transfer", params={"source": "A2", "destination": "B3"})]
    report = check_intent_agreement(predicted, TRANSFER_INTENT)
    assert not report.params_match
    assert not report.overall


def test_gaps_derived_deterministically_not_taken_on_faith() -> None:
    """The checker re-derives missing_required/unresolved_slots via D11's pure
    function instead of trusting predicted fields -- the fields are OUT of
    model hands by construction."""
    predicted = [PredictedCall(name="transfer", params={"source": "A1"})]
    report = check_intent_agreement(predicted, TRANSFER_INTENT)
    # volume_ul absent => derived missing_required != intended [] => gap axis fails
    assert not report.gaps_match


def test_clarify_class_incomplete_call_matches_intended_gaps() -> None:
    intent: IntentRecord = {
        "record_id": "s-002",
        "utterance": "aspirate 10 uL",
        "source": "synthetic",
        "calls": [
            {
                "name": "aspirate",
                "params": {},
                "missing_required": ["source", "volume_ul"],
                "unresolved_slots": [],
            }
        ],
        "expected_effects": [],
    }
    predicted = [PredictedCall(name="aspirate", params={})]
    report = check_intent_agreement(predicted, intent)
    assert report.gaps_match
    assert report.overall


def test_unresolved_slot_reference_mismatch_flagged() -> None:
    intent: IntentRecord = {
        **TRANSFER_INTENT,
        "record_id": "s-003",
    }
    predicted = [
        PredictedCall(
            name="transfer",
            params={"source": "A9", "destination": "B3", "volume_ul": 50},
        )
    ]
    report = check_intent_agreement(predicted, intent)
    # params differ (A9 vs A1) so params axis fails too; the gap axis compares
    # derived slots vs intended slots including references.
    assert not report.overall


# ---------------------------------------------------------------------------
# 260902: slot order across args is a parse-layer accident (the FunctionGemma
# template emits keys alphabetically); within one list-valued arg it is data.
# ---------------------------------------------------------------------------

def test_unresolved_slots_order_across_args_is_irrelevant() -> None:
    intent: IntentRecord = {
        **TRANSFER_INTENT,
        "record_id": "s-004",
        "calls": [
            {
                "name": "transfer",
                "params": {"source": "A1", "destination": "B3", "volume_ul": 50},
                "missing_required": [],
                "unresolved_slots": [
                    {"arg_name": "source", "reference": "A1", "resource_type": "container"},
                    {"arg_name": "destination", "reference": "B3", "resource_type": "container"},
                ],
            }
        ],
    }
    # predicted params in ALPHABETICAL key order (destination before source)
    predicted = [PredictedCall(name="transfer", params={"destination": "B3", "source": "A1", "volume_ul": 50})]
    report = check_intent_agreement(predicted, intent)
    assert report.params_match and report.gaps_match and report.overall, report.reasons


def test_unresolved_slots_within_arg_order_is_significant() -> None:
    intent: IntentRecord = {
        "record_id": "s-005",
        "utterance": "pick up tips at A1 then B1",
        "source": "synthetic",
        "calls": [
            {
                "name": "pick_up_tips",
                "params": {"at": ["tip_rack.A1", "tip_rack.B1"]},
                "missing_required": [],
                "unresolved_slots": [
                    {"arg_name": "at", "reference": "tip_rack.B1", "resource_type": "tip_spot"},
                    {"arg_name": "at", "reference": "tip_rack.A1", "resource_type": "tip_spot"},
                ],
            }
        ],
        "expected_effects": [],
    }
    predicted = [PredictedCall(name="pick_up_tips", params={"at": ["tip_rack.A1", "tip_rack.B1"]})]
    report = check_intent_agreement(predicted, intent)
    assert report.params_match
    assert not report.gaps_match  # the annotation lists the tips in the wrong order
