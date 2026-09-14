"""P2.5 deliverable 4/8: idempotent regeneration.

Assembly is a pure function of committed inputs; upstream teacher outputs are
cached content-addressed ((prompt_version, input_hash) keys, R4/D9), so
same-inputs => same-corpus BYTES. This suite proves it three ways: repeated
in-process builds, the file-writing CLI path, and a drift alarm against the
committed artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from assemble.build import (
    CORPUS_NAME, MANIFEST_NAME, NEAR_PROBE_CORPUS_NAME, NEAR_PROBE_SIDECAR_NAME, PROBE_CORPUS_NAME, PROBE_SIDECAR_NAME,
    SIDECAR_NAME, build_artifacts, main,
)

TRAINING_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = TRAINING_DIR / "assemble" / "out"
ARTIFACT_NAMES = (CORPUS_NAME, SIDECAR_NAME, MANIFEST_NAME, PROBE_CORPUS_NAME, PROBE_SIDECAR_NAME,
                  NEAR_PROBE_CORPUS_NAME, NEAR_PROBE_SIDECAR_NAME)


def test_repeated_builds_are_byte_identical():
    first = build_artifacts()
    second = build_artifacts()
    assert set(first) == set(ARTIFACT_NAMES)
    for name in ARTIFACT_NAMES:
        assert first[name] == second[name], f"{name} not deterministic"


def test_cli_writes_identical_bytes_on_rerun(tmp_path: Path):
    run_a = tmp_path / "a"
    run_b = tmp_path / "b"
    main(run_a)
    main(run_b)
    for name in ARTIFACT_NAMES:
        assert (run_a / name).read_bytes() == (run_b / name).read_bytes(), (
            f"{name}: CLI rerun diverged -- idempotency broken (D9/R4)"
        )


def test_committed_artifacts_match_fresh_build_drift_alarm():
    fresh = build_artifacts()
    for name in ARTIFACT_NAMES:
        committed = (OUT_DIR / name).read_bytes()
        assert committed == fresh[name], (
            f"committed training/assemble/out/{name} drifted from a fresh "
            "deterministic build; regenerate and re-commit"
        )
