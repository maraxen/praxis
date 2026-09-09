"""P2.5 deliverable 3: the committed scaffold template is byte-authoritative.

The template file's post-marker body must equal the golden builder's recorded
constant, EVERY assembled row's developer turn must byte-match it, and the
no-date-injection decision (D6-rev2) must be stated in the template header and
true of the body."""

from __future__ import annotations

import json
import re
from pathlib import Path

from praxis_training.golden_build.corpus import DEVELOPER_SCAFFOLD

from assemble.scaffold import (
    BEGIN_MARKER,
    SCAFFOLD_TEMPLATE_NAME,
    scaffold_template_bytes,
    scaffold_template_path,
    scaffold_template_text,
)

TRAINING_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = TRAINING_DIR / "assemble" / "out"


def test_template_body_byte_matches_golden_constant():
    raw = scaffold_template_path().read_bytes()
    marker_line = (BEGIN_MARKER + "\n").encode("utf-8")
    assert marker_line in raw, "template lacks its BEGIN marker"
    assert raw.endswith(b"\n"), "template must end inside the scaffold body (trailing newline)"
    assert scaffold_template_bytes() == DEVELOPER_SCAFFOLD.encode("utf-8"), (
        "committed scaffold bytes drifted from "
        "praxis_training.golden_build.corpus.DEVELOPER_SCAFFOLD"
    )


def test_header_states_date_omission_explicitly():
    raw_text = scaffold_template_path().read_text(encoding="utf-8")
    header = raw_text.partition(BEGIN_MARKER + "\n")[0]
    assert "OMITTED" in header, "D6-rev2 requires the omission be stated explicitly"
    assert "date" in header.lower() and "timestamp" in header.lower()


def test_body_contains_no_timestamp_shape():
    body = scaffold_template_text()  # loader returns the post-marker body ONLY
    assert not re.search(r"\d{4}-\d{2}-\d{2}", body), "date leaked into scaffold body"
    assert not re.search(r"\d{2}:\d{2}:\d{2}", body), "time leaked into scaffold body"


def test_every_assembled_row_developer_turn_byte_matches():
    rows = [
        json.loads(line)
        for line in (OUT_DIR / "corpus_p25.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    expected = {"role": "developer", "content": scaffold_template_text()}
    assert rows
    for i, row in enumerate(rows):
        assert row["messages"][0] == expected, f"corpus line {i}: developer turn off-template"

    # And the manifest records the same fact with a checksum.
    import hashlib

    manifest = json.loads((OUT_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["scaffold"]["date_timestamp_injection"] is False
    assert manifest["scaffold"]["template_sha256"] == hashlib.sha256(
        scaffold_template_bytes()
    ).hexdigest()
