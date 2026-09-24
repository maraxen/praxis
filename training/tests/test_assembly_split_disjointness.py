"""P2.5 assembled-corpus split tests: disjointness BY CONSTRUCTION, golden
all-eval, metadata normalization (every row carries the final split), native
key shape, uniform tools block."""

from __future__ import annotations

import json
from pathlib import Path

from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES

TRAINING_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = TRAINING_DIR / "assemble" / "out"


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load():
    rows = _read_jsonl(OUT_DIR / "corpus_p25.jsonl")
    side = _read_jsonl(OUT_DIR / "corpus_p25_sidecar.jsonl")
    assert len(rows) == len(side)
    return rows, side


def test_native_rows_carry_exactly_the_three_keys():
    rows, _ = _load()
    assert rows, "assembled corpus is empty"
    for row in rows:
        assert sorted(row.keys()) == ["messages", "metadata", "tools"], (
            "FunctionGemma-native rows carry EXACTLY {metadata, tools, messages}"
        )
        assert row["metadata"] in ("train", "eval")


def test_splits_are_disjoint_and_complete():
    rows, side = _load()
    ids = [s["record_id"] for s in side]
    assert len(ids) == len(set(ids)), "record_ids must be unique across branches"

    train = {s["record_id"] for r, s in zip(rows, side) if r["metadata"] == "train"}
    eval_ = {s["record_id"] for r, s in zip(rows, side) if r["metadata"] == "eval"}
    assert not (train & eval_), "train/eval must be disjoint by construction"
    assert train | eval_ == set(ids), "every record lands in exactly one split"


def test_metadata_matches_sidecar_split():
    rows, side = _load()
    for row, s in zip(rows, side):
        assert row["metadata"] == s["split"], f"{s['record_id']}: metadata/sidecar split drift"


def test_golden_provenance_all_lands_in_eval():
    rows, side = _load()
    golden = [(r, s) for r, s in zip(rows, side) if s["provenance"] == "golden"]
    assert golden, "golden branch missing from assembly"
    assert all(r["metadata"] == "eval" for r, _ in golden), (
        "task AC: ALL golden-provenance rows land in eval (leak-proof instruments)"
    )


def test_synthetic_strata_keep_train_mass_and_hold_out_representation():
    """Every synthetic stratum keeps >= 1 train row; strata with n >= 4 hold
    out >= 1 eval row. Eval clarify slice stays >= D8's 30 floor."""
    _, side = _load()
    strata: dict[tuple, list] = {}
    for s in side:
        if s["provenance"] == "golden":
            continue
        key = (s["provenance"], s["ambiguity_class"], str(s["verb"]))
        strata.setdefault(key, []).append(s["split"])
    # 0.1.4: the eval split is pinned, so strata that gained rows after the
    # pin (repaired floor cells, the natural lane) legitimately have no
    # held-out row -- but only the ones the manifest enumerates.
    manifest = json.loads((Path(__file__).resolve().parents[1] / "assemble" / "out" / "manifest.json").read_text())
    allowed = {(s["provenance"], s["ambiguity_class"], s["verb"]) for s in manifest["post_freeze_train_only_strata"]}
    for key, splits in strata.items():
        assert splits.count("train") >= 1, f"{key}: stratum lost all train mass"
        if len(splits) >= 4:
            assert splits.count("eval") >= 1 or key in allowed, f"{key}: large stratum has no held-out row and is not enumerated"
    for key in allowed:
        assert key[0] in ("coverage", "coverage_natural"), key

    from assemble.build import CLARIFY_CLASSES

    eval_classes = [s["ambiguity_class"] for s in side if s["split"] == "eval"]
    for cls in CLARIFY_CLASSES:
        n = eval_classes.count(cls)
        assert n >= 10, f"eval slice for {cls} collapsed ({n})"
    assert len(eval_classes) - sum(eval_classes.count(c) for c in CLARIFY_CLASSES) > 0


def test_uniform_full_tool_block_on_every_row():
    rows, _ = _load()
    first = json.dumps(rows[0]["tools"], sort_keys=True)
    assert all(json.dumps(r["tools"], sort_keys=True) == first for r in rows), (
        "mobile-actions pattern: every row repeats the SAME full tool block"
    )
    names = {d["function"]["name"] for d in rows[0]["tools"]}
    assert names == set(PHASE2_TOOL_NAMES)


def test_assistant_supervision_shapes_follow_d7():
    rows, side = _load()
    for row, s in zip(rows, side):
        assistant = row["messages"][2]
        if s["ambiguity_class"] == "out_of_surface":
            assert "tool_calls" not in assistant and assistant["content"], (
                f"{s['record_id']}: out-of-surface supervises an NL clarification turn"
            )
        else:
            assert "tool_calls" in assistant and assistant["tool_calls"], (
                f"{s['record_id']}: in-surface supervises a tool_call"
            )
