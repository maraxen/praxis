"""P2.5 deliverable 4: manifest completeness.

The manifest must key the corpus to PLR_SOURCE_SHA, carry generator / prompt /
teacher versions and provenance counts, account for every input row (kept or
excluded), record the shortfall against the ~1000 target with its reason, and
point at the provisional thresholds + slice-gate docs."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

TRAINING_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TRAINING_DIR.parent
OUT_DIR = TRAINING_DIR / "assemble" / "out"


def _manifest() -> dict:
    return json.loads((OUT_DIR / "manifest.json").read_text(encoding="utf-8"))


def _corpus_row_count() -> int:
    return sum(
        1
        for line in (OUT_DIR / "corpus_p25.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def test_required_fields_present():
    m = _manifest()
    for key in (
        "artifact", "task_id", "assembly_version", "plr_source_sha", "scaffold",
        "inputs", "generator_versions", "prompt_versions", "teacher_model_versions",
        "counts", "target", "exclusions", "split_rule",
    ):
        assert key in m, f"manifest missing required field: {key}"
    assert m["scaffold"]["date_timestamp_injection"] is False


def test_plr_source_sha_is_submodule_head():
    m = _manifest()
    assert re.fullmatch(r"[0-9a-f]{40}", m["plr_source_sha"])
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "submodule", "status", "external/pylabrobot"],
        capture_output=True, text=True, check=True,
    ).stdout.split()[0]
    if out[0] in "+-U":
        out = out[1:]
    assert m["plr_source_sha"] == out, "manifest PLR sha != submodule HEAD (D9 keying broken)"
    # Cross-artifact consistency with the golden manifest's recorded pin.
    golden = json.loads((TRAINING_DIR / "golden" / "manifest.json").read_text(encoding="utf-8"))
    assert m["plr_source_sha"] == golden["plr_source_sha"]


def test_versions_and_provenance_counts():
    m = _manifest()
    assert m["prompt_versions"], "prompt versions must be recorded"
    assert any(v.startswith("p23_") for v in m["prompt_versions"])
    assert any(v.startswith("p24") for v in m["prompt_versions"])
    assert m["teacher_model_versions"], "teacher model versions must be recorded"

    counts = m["counts"]
    n = counts["total_rows"]
    assert n == _corpus_row_count()
    assert sum(counts["by_split"].values()) == n
    assert sum(counts["by_provenance"].values()) == n
    assert sum(counts["by_class"].values()) == n
    assert set(counts["by_provenance"]) == {"golden", "coverage", "naturalness", "coverage_natural"}
    # Every golden row is eval by rule; at full scale synthetic train mass
    # legitimately outweighs eval, so the bound is on golden, not on train.
    assert counts["by_split"]["eval"] >= counts["by_provenance"]["golden"], "golden-all-eval lower bound"
    strata_total = sum(s["n"] for s in counts["strata"])
    assert strata_total == n
    for s in counts["strata"]:
        if s["provenance"] == "golden":
            # Golden rows are ALL held out by task AC; n_eval == n is correct.
            assert s["n_eval"] == s["n"]
        else:
            assert 0 <= s["n_eval"] <= s["n"] - 1, f"stratum {s} violates train-first clamp"


def test_inputs_are_hashed_and_account_for_all_rows():
    m = _manifest()
    kept = m["counts"]["total_rows"]
    excluded = m["exclusions"]["total"]
    diverted = m["probe"]["rows"] + m["probe_near"]["rows"]
    input_rows = sum(m["inputs"][k]["rows"] for k in ("golden_pairs", "floor_corpus", "overlay_corpus", "natural_corpus"))
    assert kept + excluded + diverted == input_rows, (
        f"kept({kept}) + excluded({excluded}) + probe({diverted}) != input rows({input_rows})"
    )
    for meta in m["inputs"].values():
        path = REPO_ROOT / meta["path"]
        assert path.exists(), f"missing input {meta['path']}"
        assert meta["bytes"] == path.stat().st_size
        import hashlib

        assert meta["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


def test_shortfall_recorded_not_padded():
    m = _manifest()
    target = m["target"]
    assert target["examples_requested"] == 1000
    # 0.1.4: the natural lane can carry assembly past the target; the
    # shortfall is then 0 and stays honest (never padded, never negative).
    assert target["shortfall"] == max(0, target["examples_requested"] - target["examples_assembled"])
    assert len(target["shortfall_reason"]) > 40


def test_doc_pointers():
    m = _manifest()
    assert (REPO_ROOT / m["thresholds_doc"]).exists()
    assert (REPO_ROOT / m["slice_gate_doc"]).exists()


def test_probe_has_out_of_surface_rows_with_clarification_targets():
    """0.1.5: the natural lane covers out-of-surface rows; their eval-base
    variants form an out_of_surface probe class supervised as NL clarification."""
    import json

    from assemble.build import PROBE_CORPUS_NAME, PROBE_SIDECAR_NAME

    out = REPO_ROOT / "training" / "assemble" / "out"
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert m["probe"]["by_class"]["out_of_surface"] >= 20
    probe = [json.loads(line) for line in (out / PROBE_CORPUS_NAME).read_text(encoding="utf-8").splitlines() if line.strip()]
    side = [json.loads(line) for line in (out / PROBE_SIDECAR_NAME).read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(probe) == len(side) == m["probe"]["rows"]
    n_oos = 0
    for row, s in zip(probe, side, strict=True):
        assistant = row["messages"][-1]
        if s["ambiguity_class"] == "out_of_surface":
            n_oos += 1
            assert assistant.get("content") and not assistant.get("tool_calls")
            assert s["supervision_kind"] == "nl_clarification" and s["calls"] == []
        else:
            assert assistant.get("tool_calls")
    assert n_oos == m["probe"]["by_class"]["out_of_surface"]


def test_near_surface_probe_is_the_appended_cells_hold_out():
    """0.1.6: the last 4 examples of each appended (matrix v3) cell form the
    near-surface probe: 24 clarification-only rows, none of them in train or eval."""
    import json

    from assemble.build import NEAR_PROBE_CORPUS_NAME, NEAR_PROBE_INDEX_MIN, NEAR_PROBE_SIDECAR_NAME, SIDECAR_NAME, appended_matrix_cells

    out = REPO_ROOT / "training" / "assemble" / "out"
    m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    cells = appended_matrix_cells()
    assert len(cells) == 6 and set(cells.values()) == {"3"}
    assert m["probe_near"]["rows"] == 24 and m["probe_near"]["index_min"] == NEAR_PROBE_INDEX_MIN == 16
    assert m["probe_near"]["cells"] == {c: 4 for c in cells} and m["probe_near"]["by_class"] == {"out_of_surface": 24}
    near = [json.loads(line) for line in (out / NEAR_PROBE_CORPUS_NAME).read_text(encoding="utf-8").splitlines() if line.strip()]
    side = [json.loads(line) for line in (out / NEAR_PROBE_SIDECAR_NAME).read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(near) == len(side) == 24
    for row, s in zip(near, side, strict=True):
        assistant = row["messages"][-1]
        assert assistant.get("content") and not assistant.get("tool_calls")
        assert s["split"] == "probe_near" and s["supervision_kind"] == "nl_clarification" and s["calls"] == []
        assert s["lineage"]["cell_id"] in cells and int(s["record_id"].rsplit("-", 1)[1]) >= 16
        assert row["metadata"] == "eval"  # scored by baseline_eval --split eval, like the natural probe
    main_side = [json.loads(line) for line in (out / SIDECAR_NAME).read_text(encoding="utf-8").splitlines() if line.strip()]
    near_ids = {s["record_id"] for s in side}
    assert not near_ids & {s["record_id"] for s in main_side}
    in_train = [s for s in main_side if s["lineage"].get("cell_id") in cells]
    assert len(in_train) == 96 and all(s["split"] == "train" and int(s["record_id"].rsplit("-", 1)[1]) < 16 for s in in_train)
