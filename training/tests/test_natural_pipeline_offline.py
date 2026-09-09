"""Natural lane end-to-end with a scripted FakeTeacher: ids, lineage,
provenance, out-of-surface rows with the base clarification copied, filter
applied, teacher version stamped from the cache record, base tampering loud
(tasks 260902_p26b_surface_data, 260903_p26c_oos_natural).
"""

import json
from pathlib import Path

import pytest
from floor_gen.cache import TeacherCache
from floor_gen.corpus import CorpusError
from floor_gen.matrix import committed_matrix_path, load_matrix
from floor_gen.natural import build_natural_manifest, generate_natural_corpus
from floor_gen.teachers import FakeTeacher
from floor_gen.versions import PROMPT_VERSION_NATURAL, PROMPT_VERSION_NATURAL_OOS

ROOT = Path(__file__).resolve().parents[1]
OOS_TEXT = "Could you give well A1 a quick stir by pipetting up and down before you transfer it?"
IN_TEXT = "Pull 25 microliters out of well C7 on plate 1, please."


def _base_rows(cells, n=2):
    rows = [json.loads(line) for line in (ROOT / "out" / "corpus_p23_floor.jsonl").read_text().splitlines() if line.strip()]
    out = []
    for cid in cells:
        out += [r for r in rows if r["matrix_cell"]["cell_id"] == cid][:n]
    return out


def _natural_teacher(model_version="fake-teacher@test"):
    def respond(system, user):
        # mimic a compliant teacher: everyday verb, natural location, no ids;
        # the oos lane asks for the utterance only (clarification null)
        if "class=out-of-surface" in user:
            return json.dumps({"utterance": OOS_TEXT, "clarification": None})
        return json.dumps({"utterance": IN_TEXT, "clarification": None})
    return FakeTeacher(responder=respond, model_version=model_version)


def test_offline_lane_rows_lineage_both_lanes(tmp_path):
    matrix = load_matrix(committed_matrix_path())
    base = _base_rows(["aspirate__none", "pick_up_tips__ambiguous-referent", "mix__out-of-surface"])
    assert sum(r["matrix_cell"]["ambiguity_class"] == "out-of-surface" for r in base) == 2
    rows, stats = generate_natural_corpus(base, matrix, _natural_teacher(), TeacherCache(tmp_path), batch_size=1)
    assert stats.base_rows == 6 and stats.accepted == 6 and stats.rejected_filter == 0
    assert stats.per_class == {"none": 2, "ambiguous-referent": 2, "out-of-surface": 2}
    for row, b in zip(rows, base, strict=True):
        assert row["record_id"] == "nat-" + b["record_id"][4:]
        assert row["lineage"]["base_record_id"] == b["record_id"]
        assert row["provenance"]["provenance"] == "coverage_natural"
        assert row["structured_calls"] == b["structured_calls"] and row["intent"] == b["intent"]
        assert row["supervision"] == b["supervision"]
        assert "execution_verify" not in row
        if b["matrix_cell"]["ambiguity_class"] == "out-of-surface":
            assert row["provenance"]["prompt_version"] == PROMPT_VERSION_NATURAL_OOS
            assert row["utterance"] == OOS_TEXT
            assert row["clarification"] == b["clarification"] and row["clarification"]
            assert row["structured_calls"] == [] and row["supervision"]["kind"] == "nl_clarification"
        else:
            assert row["provenance"]["prompt_version"] == PROMPT_VERSION_NATURAL
            assert row["utterance"] == IN_TEXT and row["clarification"] is None
    m = build_natural_manifest(stats, base_corpus="x", base_manifest={"generator_version": "0.2.1", "prompt_version": "p"})
    assert m["accepted"] == 6 and m["prompt_version"] == PROMPT_VERSION_NATURAL
    assert m["prompt_version_oos"] == PROMPT_VERSION_NATURAL_OOS
    assert m["teacher_model_versions"] == {"fake-teacher@test": 6}
    assert "canonical_verb" not in m["filter_rules"]["out_of_surface"]


def test_offline_lane_filter_rejects_identifier_leak_and_counts(tmp_path):
    matrix = load_matrix(committed_matrix_path())
    base = _base_rows(["aspirate__none"], n=2)
    leaky = FakeTeacher(responder=lambda s, u: json.dumps({"utterance": "Aspirate 25 microliters from plate_1.C7.", "clarification": None}))
    rows, stats = generate_natural_corpus(base, matrix, leaky, TeacherCache(tmp_path))
    assert rows == [] and stats.rejected_filter == 2
    assert stats.rejected_by_reason["underscore_identifier"] == 2
    assert stats.rejected_by_reason["canonical_verb"] == 2


def test_oos_lane_keeps_liquid_verbs_but_rejects_identifiers(tmp_path):
    matrix = load_matrix(committed_matrix_path())
    base = _base_rows(["mix__out-of-surface"], n=2)
    leaky = FakeTeacher(responder=lambda s, u: json.dumps({"utterance": "Stir plate_1 well A1 before the transfer.", "clarification": None}))
    rows, stats = generate_natural_corpus(base, matrix, leaky, TeacherCache(tmp_path))
    assert rows == [] and stats.rejected_by_reason == {"underscore_identifier": 2}
    ok = FakeTeacher(responder=lambda s, u: json.dumps({"utterance": "Stir well A1 up and down before the transfer, would you?", "clarification": None}))
    rows, stats = generate_natural_corpus(base, matrix, ok, TeacherCache(tmp_path / "b"))
    assert stats.accepted == 2 and all(r["clarification"] == b["clarification"] for r, b in zip(rows, base, strict=True))


def test_oos_base_row_without_clarification_is_loud(tmp_path):
    matrix = load_matrix(committed_matrix_path())
    base = _base_rows(["mix__out-of-surface"], n=1)
    base[0]["clarification"] = None
    with pytest.raises(CorpusError, match="without a clarification"):
        generate_natural_corpus(base, matrix, _natural_teacher(), TeacherCache(tmp_path))


def test_second_run_is_cache_hits_only_and_identical(tmp_path):
    matrix = load_matrix(committed_matrix_path())
    base = _base_rows(["dispense__missing-slot"], n=3)
    t = _natural_teacher()
    cache = TeacherCache(tmp_path)
    rows1, s1 = generate_natural_corpus(base, matrix, t, cache)
    rows2, s2 = generate_natural_corpus(base, matrix, t, cache)
    assert s1.cache_misses == 3 and s2.cache_misses == 0 and s2.cache_hits == 3
    assert rows1 == rows2


def test_teacher_version_is_stamped_from_the_cache_record(tmp_path):
    """Regression for the P2.6b provenance bug: a warm-cache pass with a
    different backend must keep the stamp of the teacher that produced the reply."""
    matrix = load_matrix(committed_matrix_path())
    base = _base_rows(["aspirate__none", "shake__out-of-surface"], n=1)
    cache = TeacherCache(tmp_path)
    rows1, s1 = generate_natural_corpus(base, matrix, _natural_teacher("gemini-x"), cache)
    rows2, s2 = generate_natural_corpus(base, matrix, _natural_teacher("fake-teacher@test"), cache)
    assert s2.cache_misses == 0
    assert rows1 == rows2
    assert {r["provenance"]["teacher_model_version"] for r in rows2} == {"gemini-x"}
    assert s2.teacher_model_versions == {"gemini-x": 2} and s2.backend_teacher_model_version == "fake-teacher@test"


def test_tampered_base_row_is_loud(tmp_path):
    matrix = load_matrix(committed_matrix_path())
    base = _base_rows(["aspirate__none"], n=1)
    base[0]["structured_calls"][0]["kwargs"]["vols"] = [999.0]
    with pytest.raises(CorpusError, match="structured_calls differ"):
        generate_natural_corpus(base, matrix, _natural_teacher(), TeacherCache(tmp_path))
