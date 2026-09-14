"""Batch CLI + AC-2.2.4 performance gate tests."""

import json
import shutil
from pathlib import Path

from verify.cli import bench, load_examples, run_directory

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_load_examples_skips_invalid(tmp_path):
    (tmp_path / "good.json").write_text((EXAMPLES / "clean_transfer.json").read_text())
    (tmp_path / "bad.json").write_text(json.dumps({"foo": 1}))
    examples = load_examples(tmp_path)
    assert [e["_source"] for e in examples] == ["good.json"]


def test_run_directory_exit_code_reflects_failures():
    # full examples dir includes the known-failure file -> exit 1
    assert run_directory(EXAMPLES, as_json=True) == 1


def test_run_directory_all_clean_exits_zero(tmp_path):
    shutil.copy(EXAMPLES / "clean_transfer.json", tmp_path / "clean_transfer.json")
    shutil.copy(EXAMPLES / "aspirate_dispense_drop.json", tmp_path / "a.json")
    shutil.copy(EXAMPLES / "move_plate.json", tmp_path / "m.json")
    assert run_directory(tmp_path, as_json=True) == 0


def test_perf_gate_measured():
    """AC-2.2.4: >=100 verifications must complete in <5 min single-process.

    Default lane: measure a SAMPLE (N=12) and assert its rate against the
    AC-2.2.4 budget (>=100 verifications / 300s => >= 1/3 per second).  The
    FULL 100-verification measurement lives in the CLI (`verify-cli <dir>
    --bench 100`) and is re-run here only when P22_FULL_BENCH=1 -- 100 deck
    builds are seconds of pure CPU and starve under parallel CI/dev loads
    (observed: three agents' suites sharing one box turned 7s into minutes).
    """
    import os
    import time

    n = int(os.environ.get("P22_FULL_BENCH", "0")) and 100 or 12

    t0 = time.monotonic()
    rc = bench(EXAMPLES, n)
    elapsed = time.monotonic() - t0

    assert rc == 0, "bench gate verdict FAIL"
    if n == 100:
        assert elapsed < 300.0, f"100 verifications took {elapsed:.1f}s (>300s)"
    else:
        # sample-rate projection must clear the same budget with headroom
        projected_100 = elapsed / n * 100
        assert projected_100 < 300.0, (
            f"rate too slow: {n} verifications in {elapsed:.1f}s projects "
            f"{projected_100:.1f}s for 100"
        )
