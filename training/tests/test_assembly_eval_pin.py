"""The committed eval-split pin matches the committed assembled corpus
(membership + native-row content). Task 260902_p26b_surface_data."""

import json
from pathlib import Path

from assemble.pin import PIN_REL, load_pin, native_digest

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "training" / "assemble" / "out"


def _rows(name):
    return [json.loads(l) for l in (OUT / name).read_text(encoding="utf-8").splitlines() if l.strip()]


def test_pin_loads_and_has_228_rows():
    pin = load_pin(REPO / PIN_REL)
    assert pin["n"] == 228
    assert pin["pinned_at_assembly_version"] == "0.1.3"


def test_pinned_ids_are_exactly_the_eval_split_and_content_matches():
    pin = load_pin(REPO / PIN_REL)
    pairs, side = _rows("corpus_p25.jsonl"), _rows("corpus_p25_sidecar.jsonl")
    eval_ids = {s["record_id"]: p for p, s in zip(pairs, side) if p["metadata"] == "eval"}
    assert set(eval_ids) == set(pin["rows"])
    for rid, digest in pin["rows"].items():
        assert native_digest(eval_ids[rid]) == digest, rid


def test_golden_rows_all_pinned():
    pin = load_pin(REPO / PIN_REL)
    side = _rows("corpus_p25_sidecar.jsonl")
    golden = {s["record_id"] for s in side if s["provenance"] == "golden"}
    assert golden <= set(pin["rows"]) and len(golden) == 88
