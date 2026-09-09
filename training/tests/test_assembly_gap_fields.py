"""The assembled sidecar's gap annotations are the D11 derivation, on every
call, in the params order the file itself carries (assembly 0.1.3; the
gold_slot_annotation / slot_order_only / gold_missing_required defects of
task 260902_p26_rescore)."""

import json
from pathlib import Path

from coxswain.plr.slot_derivation import derive_call_gaps

SIDECAR = Path(__file__).resolve().parents[1] / "assemble" / "out" / "corpus_p25_sidecar.jsonl"


def _rows():
    return [json.loads(l) for l in SIDECAR.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_sidecar_gap_fields_equal_derivation_on_every_call():
    n_calls = 0
    for row in _rows():
        for call in row["calls"]:
            gaps = derive_call_gaps(call["name"], call["params"])
            assert call["missing_required"] == list(gaps.missing_required), row["record_id"]
            assert call["unresolved_slots"] == [
                {"arg_name": s.arg_name, "reference": s.reference, "resource_type": s.resource_type}
                for s in gaps.unresolved_slots
            ], row["record_id"]
            n_calls += 1
    assert n_calls > 600


def test_no_call_lacks_gap_keys():
    for row in _rows():
        for call in row["calls"]:
            assert "missing_required" in call and "unresolved_slots" in call, row["record_id"]


def test_params_keys_are_sorted_as_written():
    # derive_call_gaps orders slots by params iteration order; the file's
    # order is the canonical sorted-key order, so the annotation is stable.
    for row in _rows():
        for call in row["calls"]:
            assert list(call["params"]) == sorted(call["params"]), row["record_id"]
