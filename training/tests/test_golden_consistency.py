"""Golden-set consistency: counts DERIVE from PHASE2_TOOL_NAMES, gap fields
are derived + non-empty for clarify classes, scaffold is verbatim, committed
artifacts regenerate byte-for-byte (drift alarm), pair/sidecar line linkage."""

import json
from pathlib import Path

from coxswain.plr.slot_derivation import derive_call_gaps
from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES

from praxis_training.golden_build.build import (
    GOLDEN_DIR,
    PAIRS_NAME,
    SIDECAR_NAME,
    build_all,
    render_native_row,
    tool_declarations,
)
from praxis_training.golden_build.corpus import (
    DEVELOPER_SCAFFOLD,
    AmbiguityClass,
    CLARIFY_PER_CLASS,
    POSITIVES_PER_TOOL,
    build_corpus,
)

TRAINING_DIR = Path(__file__).resolve().parents[1]


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_counts_derive_from_phase2_tool_names():
    corpus = build_corpus()
    included = sorted(PHASE2_TOOL_NAMES)
    by_tool = {tool: 0 for tool in included}
    for ex in corpus:
        if ex.ambiguity_class == AmbiguityClass.CLEAN_PARSE:
            by_tool[ex.calls[0].name] += 1
    assert all(n == POSITIVES_PER_TOOL for n in by_tool.values())
    # >= 2 per included verb is the AC floor; we author more.
    assert POSITIVES_PER_TOOL >= 2
    clarify = [ex for ex in corpus if ex.ambiguity_class != AmbiguityClass.CLEAN_PARSE]
    assert len(clarify) >= 30
    eval_clarify = [ex for ex in clarify if ex.split == "eval"]
    assert len(eval_clarify) >= 30, "D8: >=30 HELD-OUT clarify examples"
    classes = {ex.ambiguity_class for ex in eval_clarify}
    assert classes == set(AmbiguityClass.CLARIFY), "all three classes held out"


def test_clarify_sidecar_gaps_nonempty_juror_finding():
    sidecars = _read_jsonl(GOLDEN_DIR / SIDECAR_NAME)
    checked = {"missing_slot": 0, "ambiguous_referent": 0}
    for row in sidecars:
        cls = row["ambiguity_class"]
        if cls not in checked:
            continue
        assert row["provenance"] == "golden"
        assert row["source"] == "golden"
        assert row["calls"], f"{row['record_id']}: clarify call-class needs a call"
        call = row["calls"][0]
        derived = derive_call_gaps(call["name"], call["params"])
        if cls == "missing_slot":
            assert list(derived.missing_required) == call["missing_required"]
            assert call["missing_required"]
        else:
            assert list(derived.missing_required) == []
            assert call["unresolved_slots"]
            assert list(derived.unresolved_slots) and call["unresolved_slots"]
        checked[cls] += 1
    assert all(v > 0 for v in checked.values())


def test_gap_fields_are_derived_not_authored():
    """If someone hand-edits an authored param, regeneration must diverge:
    the sidecar's gap fields come from slot_derivation alone."""
    from praxis_training.golden_build.build import render_sidecar_row

    corpus = build_corpus()
    target = next(ex for ex in corpus if ex.record_id == "golden-missing-slot-01")
    row = render_sidecar_row(target)
    assert row["calls"][0]["missing_required"] == ["source"]
    tampered = target.__class__(
        record_id=target.record_id, split=target.split,
        ambiguity_class=target.ambiguity_class, utterance=target.utterance,
        calls=(target.calls[0].__class__(name="aspirate", params={}),),
    )
    assert render_sidecar_row(tampered)["calls"][0]["missing_required"] == ["source", "volume_ul"]


def test_developer_scaffold_verbatim_no_date_injection():
    corpus = build_corpus()
    tools = tool_declarations()
    for ex in corpus[:5]:
        row = json.loads(json.dumps(render_native_row(ex, tools)))
        assert sorted(row.keys()) == ["messages", "metadata", "tools"]
        dev = row["messages"][0]
        assert dev["role"] == "developer"
        assert dev["content"] == DEVELOPER_SCAFFOLD
        assert "date" not in dev["content"].lower()
    assert DEVELOPER_SCAFFOLD.endswith("functions\n")


def test_tools_list_covers_exactly_phase2_surface():
    decls = tool_declarations()
    names = [d["function"]["name"] for d in decls]
    assert sorted(names) == sorted(PHASE2_TOOL_NAMES)
    for d in decls:
        fn = d["function"]
        assert fn["parameters"]["type"] == "OBJECT"
        assert isinstance(fn["parameters"]["required"], list)


def test_committed_artifacts_regenerate_byte_for_byte():
    """Drift alarm (D9 golden exemption still wants re-derivability)."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        build_all(out_dir=__import__("pathlib").Path(td))
        for name in (PAIRS_NAME, SIDECAR_NAME):
            committed = (GOLDEN_DIR / name).read_bytes()
            fresh = (Path(td) / name).read_bytes()
            assert committed == fresh, f"{name} drifted from generator output"
        manifest = json.loads((Path(td) / "manifest.json").read_text())
        committed_manifest = json.loads((GOLDEN_DIR / "manifest.json").read_text())
        assert manifest["plr_source_sha"] == committed_manifest["plr_source_sha"]


def test_pairs_sidecar_line_alignment_and_shapes():
    pairs = _read_jsonl(GOLDEN_DIR / PAIRS_NAME)
    sidecars = _read_jsonl(GOLDEN_DIR / SIDECAR_NAME)
    assert len(pairs) == len(sidecars)
    for idx, (row, sc) in enumerate(zip(pairs, sidecars)):
        user = next(m for m in row["messages"] if m["role"] == "user")
        assert user["content"] == sc["utterance"], f"line {idx} misaligned"
        assert row["metadata"] == sc["split"]
        assistant = row["messages"][-1]
        if sc["ambiguity_class"] == AmbiguityClass.OUT_OF_SURFACE:
            assert assistant["role"] == "assistant"
            assert "tool_calls" not in assistant  # D7: NL turn only
            assert assistant["content"]
            assert sc["calls"] == []
        else:
            assert "tool_calls" in assistant
            tc = assistant["tool_calls"][0]
            assert tc["type"] == "function"
            assert tc["function"]["name"] == sc["calls"][0]["name"]
            assert tc["function"]["arguments"] == sc["calls"][0]["params"]


def test_out_of_surface_never_references_included_verbs_as_calls():
    corpus = build_corpus()
    for ex in corpus:
        if ex.ambiguity_class == AmbiguityClass.OUT_OF_SURFACE:
            assert ex.calls == ()
            assert ex.assistant_text and "?" in ex.assistant_text or ex.assistant_text


def test_manifest_counts_match_files():
    manifest = json.loads((GOLDEN_DIR / "manifest.json").read_text())
    pairs = _read_jsonl(GOLDEN_DIR / PAIRS_NAME)
    assert manifest["counts"]["total_rows"] == len(pairs)
    assert manifest["phase2_tool_count"] == len(PHASE2_TOOL_NAMES)
    assert manifest["sizing_rule"]["clarify_per_class"] == CLARIFY_PER_CLASS
    assert manifest["counts"]["eval_clarify_total"] >= 30
