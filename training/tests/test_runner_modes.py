"""Runner-mode tests: recorded artifacts (labeled, validated) + injected
local-inference lane. Synthetic outputs -> KNOWN metric values."""

import json

import pytest

from praxis_training.baseline_eval.runner import (
    PairSet,
    load_pair_set,
    load_recorded_outputs,
    run_local,
    run_recorded,
)

REPO = None


def _fixture_path():
    from pathlib import Path

    return Path(__file__).resolve().parents[1] / "eval" / "fixtures" / "recorded_fixture_mechanics_proof.json"


def _golden_paths():
    from pathlib import Path

    base = Path(__file__).resolve().parents[1] / "golden"
    return base / "golden_pairs.jsonl", base / "golden_intent_sidecar.jsonl"


# ---------------------------------------------------------------------------
# recorded-outputs validation
# ---------------------------------------------------------------------------

def test_load_recorded_rejects_wrong_artifact_kind(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"artifact_kind": "something-else", "outputs": []}))
    with pytest.raises(ValueError, match="artifact_kind"):
        load_recorded_outputs(f)


@pytest.mark.parametrize("bad", ["", "unknown", "todo", None])
def test_load_recorded_rejects_missing_base_revision(tmp_path, bad):
    blob = {"artifact_kind": "praxis-recorded-model-outputs",
            "outputs": [{"record_id": "a", "raw_output": ""}]}
    if bad is not None:
        blob["base_revision"] = bad
    f = tmp_path / "r.json"
    f.write_text(json.dumps(blob))
    with pytest.raises(ValueError, match="base_revision"):
        load_recorded_outputs(f)


def test_load_recorded_rejects_duplicate_ids(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({
        "artifact_kind": "praxis-recorded-model-outputs",
        "base_revision": "m@sha1",
        "outputs": [{"record_id": "a", "raw_output": ""},
                    {"record_id": "a", "raw_output": ""}],
    }))
    with pytest.raises(ValueError, match="duplicate"):
        load_recorded_outputs(f)


def test_fixture_fixture_is_labeled_mechanics_proof():
    blob = json.loads(_fixture_path().read_text())
    assert "NOT model outputs" in blob["recorded_by"]
    assert blob["base_revision"].startswith("google/functiongemma-270m-it@")


# ---------------------------------------------------------------------------
# end-to-end recorded mode over the committed fixture: KNOWN metric values.
# Hand-derived from the 8 fixture entries:
#   exact hits (5): aspirate-03, missing-slot-01, out-surface-01 (zero==zero),
#                   ambig-ref-02 passthrough, transfer-03 truncated-recovered.
#   exact fails (3): dispense-03 wrong volume; missing-slot-03 hallucinated
#                   destination; out-surface-02 excluded verb 'mix'.
#   => exact_match k=5, n=8.
# clarify_expected rows (4): missing-slot-01/03, out-surface-01/02
#   (ambiguous-referent is NOT static-clarify: cue-2 needs live grounding).
# clarify_predicted (2): missing-slot-01 (derived missing source),
#   out-surface-01 (abstention). recall=2/4; precision=2/2.
# ---------------------------------------------------------------------------

EXPECTED = dict(exact=(5, 8), recall=(2, 4), precision=(2, 2))


def test_recorded_mode_known_metrics():
    pairs, sidecar = _golden_paths()
    pair_set = load_pair_set(pairs, sidecar)
    report = run_recorded(pair_set, _fixture_path(), split="eval", allow_partial=True)

    assert report["mode"] == "recorded_artifacts"
    assert "RECORDED ARTIFACTS" in report["labeled_as"]
    assert "PARTIAL" in report["labeled_as"]
    em, cr, cp = (report["exact_match_accuracy"], report["clarify_recall"],
                  report["clarify_precision"])
    assert (em["successes"], em["n"]) == EXPECTED["exact"]
    assert (cr["successes"], cr["n"]) == EXPECTED["recall"]
    assert (cp["successes"], cp["n"]) == EXPECTED["precision"]
    assert em["value"] == 5 / 8 and cr["value"] == 0.5 and cp["value"] == 1.0
    # Wilson intervals present beside EVERY point estimate
    for stat in (em, cr, cp):
        assert stat["wilson95"] is not None and len(stat["wilson95"]) == 2
    lo, hi = em["wilson95"]
    assert abs(lo - 0.305783) < 1e-5 and abs(hi - 0.863133) < 1e-5
    assert report["clarify_confusion"] == {
        "true_positive": 2, "false_negative": 2, "false_positive": 0, "true_negative": 4,
    }
    assert report["inputs"]["coverage"] == {"in_scope": 62, "recorded": 8, "scored": 8}


def test_recorded_mode_requires_full_coverage_by_default():
    pairs, sidecar = _golden_paths()
    pair_set = load_pair_set(pairs, sidecar)
    with pytest.raises(ValueError, match="allow-partial|missing"):
        run_recorded(pair_set, _fixture_path(), split="eval")


def test_truncated_span_scores_exact_match():
    """Hardening payoff: the truncated transfer output still scores a hit."""
    pairs, sidecar = _golden_paths()
    pair_set = load_pair_set(pairs, sidecar)
    report = run_recorded(pair_set, _fixture_path(), split="eval", allow_partial=True)
    fails = [f["record_id"] for f in report["exact_match_failures"]]
    assert "golden-clean-transfer-03" not in fails


# ---------------------------------------------------------------------------
# local mode with an INJECTED generate fn (no torch/transformers involved)
# ---------------------------------------------------------------------------

def test_local_mode_with_injected_generate_fn():
    pairs, sidecar = _golden_paths()
    pair_set = load_pair_set(pairs, sidecar).filter_split("eval")

    def generate(native_row: dict) -> str:
        user = next(m["content"] for m in native_row["messages"] if m["role"] == "user")
        if "heater shaker" in user:
            return ""  # correct abstention
        if "lysis buffer reservoir" in user:
            return ("<start_function_call>call:aspirate{source:<escape>lysis_buffer_reservoir"
                    "<escape>,volume_ul:<escape>100<escape>}<end_function_call>")
        return "<start_function_call>call:aspirate{}<end_function_call>"

    report = run_local(pair_set, "fake/model", revision="deadbeef",
                       generate_fn=generate)
    assert report["mode"] == "local_inference"
    assert report["base_revision"] == "fake/model@deadbeef"
    assert report["n_examples"] == len(pair_set.intents)
    failed = {f["record_id"] for f in report["exact_match_failures"]}
    assert "golden-clean-aspirate-03" not in failed
    assert "golden-out-surface-01" not in failed


def test_pairset_filter_split_line_alignment():
    pairs, sidecar = _golden_paths()
    ps = load_pair_set(pairs, sidecar)
    ev = ps.filter_split("eval")
    assert len(ev.pairs) == len(ev.intents) == 62
    assert all(row["metadata"] == "eval" for row in ev.pairs)
    # misaligned sidecar must raise
    bad = tmp_sidecar_with_swapped_utterance(sidecar)
    with pytest.raises(ValueError, match="sidecar utterance"):
        load_pair_set(pairs, bad)


def tmp_sidecar_with_swapped_utterance(sidecar_path):
    import tempfile
    from pathlib import Path

    lines = sidecar_path.read_text().splitlines()
    rows = [json.loads(l) for l in lines]
    rows[0]["utterance"] = rows[0]["utterance"] + " TAMPERED"
    tmp = Path(tempfile.mkdtemp()) / "bad_sidecar.jsonl"
    tmp.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return tmp


# ---------------------------------------------------------------------------
# generations dump: the live lane writes a recorded artifact that re-scores
# to the identical report (260902 enabler for scorer-fix re-scores)
# ---------------------------------------------------------------------------

def _synthetic_generate(native_row: dict) -> str:
    user = next(m["content"] for m in native_row["messages"] if m["role"] == "user")
    if "heater shaker" in user:
        return ""
    if "lysis buffer reservoir" in user:
        return ("<start_function_call>call:aspirate{source:<escape>lysis_buffer_reservoir"
                "<escape>,volume_ul:<escape>100<escape>}<end_function_call>")
    return "<start_function_call>call:aspirate{}<end_function_call>"


def test_local_mode_dumps_recorded_artifact_that_rescores_identically(tmp_path):
    from praxis_training.baseline_eval.runner import read_recorded_artifact

    pairs, sidecar = _golden_paths()
    pair_set = load_pair_set(pairs, sidecar).filter_split("eval")
    dump = tmp_path / "dump.json"
    live = run_local(pair_set, "fake/model", revision="deadbeef", generate_fn=_synthetic_generate,
                     model_label="fake label sha256:abc", dump_outputs=dump)
    assert live["inputs"]["dump_outputs"] == str(dump)

    art = read_recorded_artifact(dump)
    assert art.base_revision == "fake/model@deadbeef"
    assert art.model_label == "fake label sha256:abc"
    assert art.recorded_by.endswith("run_local")
    assert set(art.outputs) == {i["record_id"] for i in pair_set.intents}
    assert art.inputs["max_new_tokens"] == 128 and art.inputs["split"] == "all"

    rescored = run_recorded(pair_set, dump)
    assert rescored["mode"] == "recorded_artifacts"
    for key in ("n_examples", "exact_match_accuracy", "clarify_recall", "clarify_precision",
                "clarify_confusion", "tripwire_out_of_surface_tool_calls", "per_class",
                "exact_match_failures"):
        assert rescored[key] == live[key], key
    assert rescored["inputs"]["coverage"] == {"in_scope": 62, "recorded": 62, "scored": 62}
    assert rescored["inputs"]["recorded_inputs"]["max_new_tokens"] == 128


def test_recorded_mode_carries_model_label_from_dump(tmp_path):
    pairs, sidecar = _golden_paths()
    pair_set = load_pair_set(pairs, sidecar).filter_split("eval")
    dump = tmp_path / "dump.json"
    run_local(pair_set, "fake/model", revision="deadbeef", generate_fn=_synthetic_generate,
              model_label="from-dump", dump_outputs=dump)
    assert run_recorded(pair_set, dump)["model_label"] == "from-dump"
    assert run_recorded(pair_set, dump, model_label="override")["model_label"] == "override"
    assert "pairs" not in run_recorded(pair_set, dump)["inputs"]
