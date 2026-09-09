"""AC-2.2.3 slot-agreement tests: THE axis of this deliverable.

A wrong-slot call EXECUTES CLEANLY and passes its own volume
post-conditions; it must still FAIL verification through the agreement
axis.  Execution success alone cannot catch a wrong reading.
"""

import asyncio
import json
from pathlib import Path

from verify import verify

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _load(name):
    data = json.loads((EXAMPLES / name).read_text())
    return data["call_sequence"], data["intent_record"], data.get("deck_layout")


def test_wrong_slot_executes_cleanly_but_fails_agreement():
    seq, intent, layout = _load("wrong_slot_known_failure.json")
    r = asyncio.run(verify(seq, intent, layout=layout))
    checks = {c["name"]: c for c in r["checks"]}

    # execution itself was clean
    assert r["error"] is None
    assert checks["execution_ok"]["passed"]
    # ...and the executed call's OWN post-conditions hold (moved exactly the
    # volumes it named -- just at the wrong slot)
    assert checks["volume_delta:dest_plate_well_C3"]["passed"]
    assert checks["volume_delta:source_plate_well_A1"]["passed"]

    # the intent-level axes catch it
    assert not checks["slot_agreement"]["passed"]
    assert "dest_plate.C3" in checks["slot_agreement"]["detail"]
    assert "dest_plate.B1" in checks["slot_agreement"]["detail"]
    assert not checks["effects_match"]["passed"]
    assert not checks["intent_agreement_parse_layer"]["passed"]
    assert not r["passed"]


def test_wrong_literal_volume_flagged():
    seq, intent, layout = _load("clean_transfer.json")
    seq = list(seq)
    seq[1] = {"name": "transfer", "params": {
        "source": "source_plate.A1",
        "destination": "dest_plate.B1",
        "volume_ul": 40,  # intent says 50
    }}
    r = asyncio.run(verify(seq, intent, layout=layout))
    checks = {c["name"]: c for c in r["checks"]}
    assert not checks["slot_agreement"]["passed"]
    assert "literal" in checks["slot_agreement"]["detail"]
    assert not r["passed"]


def test_sequence_length_mismatch_flagged():
    seq, intent, layout = _load("clean_transfer.json")
    r = asyncio.run(verify(seq[:2], intent, layout=layout))  # drop discard_tips
    checks = {c["name"]: c for c in r["checks"]}
    assert not checks["slot_agreement"]["passed"]
    assert "sequence length 2 != intended 3" in checks["slot_agreement"]["detail"]


def test_matching_bindings_pass():
    seq, intent, layout = _load("clean_transfer.json")
    r = asyncio.run(verify(seq, intent, layout=layout))
    checks = {c["name"]: c for c in r["checks"]}
    assert checks["slot_agreement"]["passed"]
    assert checks["intent_agreement_parse_layer"]["passed"]
