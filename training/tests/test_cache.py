"""Content-hash cache + backend driver behavior tests (deliverables 3/4/7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from floor_gen.cache import TeacherCache, TeacherCacheError, compute_cache_key
from floor_gen.matrix import cells_round_robin, committed_matrix_path, load_matrix
from floor_gen.teachers import FakeTeacher


def test_cache_key_composes_prompt_version_and_input_hash():
    k1 = compute_cache_key("v1", "abc")
    k2 = compute_cache_key("v2", "abc")
    k3 = compute_cache_key("v1", "abd")
    assert len(k1) == 64  # sha256 hex
    assert len({k1, k2, k3}) == 3


def test_cache_roundtrip_and_atomicity(tmp_path: Path):
    cache = TeacherCache(tmp_path / "cache")
    key = compute_cache_key("p23_nlify_v1", "hash-1")
    assert cache.get(key) is None
    cache.put(
        key,
        prompt_version="p23_nlify_v1",
        input_hash="hash-1",
        teacher_model_version="fake@x",
        raw_response='{"utterance":"hi","clarification":null}',
    )
    record = cache.get(key)
    assert record is not None
    assert record["raw_response"] == '{"utterance":"hi","clarification":null}'
    assert record["teacher_model_version"] == "fake@x"
    # no temp litter left behind
    assert [p.suffix for p in (tmp_path / "cache").iterdir()] == [".json"]


def test_corrupt_cache_entry_is_loud(tmp_path: Path):
    cache = TeacherCache(tmp_path)
    key = compute_cache_key("pv", "ih")
    cache.path_for(key).write_text("{not json", encoding="utf-8")
    with pytest.raises(TeacherCacheError):
        cache.get(key)


def test_identity_mismatch_is_loud(tmp_path: Path):
    cache = TeacherCache(tmp_path)
    key = compute_cache_key("pv", "ih")
    path = cache.path_for(key)
    path.write_text(json.dumps({"cache_key": "other-key", "raw_response": "x"}), encoding="utf-8")
    with pytest.raises(TeacherCacheError):
        cache.get(key)


def test_prompt_version_change_invalidates_keys():
    from floor_gen.prompts import compute_input_hash

    payload = {"prompt_version": "does-not-matter-here", "x": 1}
    h = compute_input_hash(payload)
    assert h == compute_input_hash({"prompt_version": "does-not-matter-here", "x": 1})
    assert h != compute_input_hash({"prompt_version": "other", "x": 1})


def _counting_teacher(counter: list[int]) -> FakeTeacher:
    def respond(system: str, user: str) -> str:
        counter.append(1)
        if "OUTSIDE" in user:  # out-of-surface contract: clarification required
            return json.dumps(
                {"utterance": f"off-list request {len(counter)}", "clarification": "Not supported; try pipetting instead."},
                sort_keys=True,
            )
        return json.dumps({"utterance": f"call number {len(counter)}", "clarification": None}, sort_keys=True)

    return FakeTeacher(responder=respond)


def test_second_generation_zero_backend_calls_byte_identical(tmp_path: Path):
    """THE R4 acceptance behavior: same inputs => byte-identical corpus,
    zero re-calls."""
    from floor_gen.corpus import build_manifest, generate_corpus, write_outputs

    matrix = load_matrix(committed_matrix_path())
    cells = tuple(cells_round_robin(matrix.cells)[:6])

    cache_dir = tmp_path / "cache"
    counter_first: list[int] = []
    out_a = tmp_path / "a"
    rows_a, stats_a = generate_corpus(matrix, _counting_teacher(counter_first), TeacherCache(cache_dir), selected_cell_ids=cells)
    write_outputs(out_a, rows_a, build_manifest(matrix, stats_a, [c.cell_id for c in cells]))
    assert stats_a.examples_total > 0
    assert len(counter_first) == stats_a.examples_total

    counter_second: list[int] = []
    out_b = tmp_path / "b"
    rows_b, stats_b = generate_corpus(matrix, _counting_teacher(counter_second), TeacherCache(cache_dir), selected_cell_ids=cells)
    write_outputs(out_b, rows_b, build_manifest(matrix, stats_b, [c.cell_id for c in cells]))
    assert len(counter_second) == 0
    assert (out_a / "corpus_p23_floor.jsonl").read_bytes() == (out_b / "corpus_p23_floor.jsonl").read_bytes()


def test_out_of_surface_teacher_shape_flows_to_nl_clarification(tmp_path: Path):
    from floor_gen.corpus import generate_corpus
    from floor_gen.synth import synthesize_example
    from floor_gen.prompts import build_prompt

    matrix = load_matrix(committed_matrix_path())
    cell = next(c for c in matrix.cells if c.cell_id == "mix__out-of-surface")

    def respond(system: str, user: str) -> str:
        return json.dumps(
            {
                "utterance": "Mix the liquid in well A1 up and down a few times.",
                "clarification": "I can't mix directly, but I can aspirate and dispense repeatedly to achieve mixing.",
            },
            sort_keys=True,
        )

    cache = TeacherCache(tmp_path / "cache")
    rows, stats = generate_corpus(matrix, FakeTeacher(responder=respond), cache, selected_cell_ids=(cell,))
    assert stats.examples_total == cell.examples_per_cell
    for row in rows:
        assert row["supervision"]["kind"] == "nl_clarification"
        assert row["structured_calls"] == []
        assert row["tools"] == []
        assert row["clarification"]
        example = synthesize_example(cell, int(row["record_id"].split("-")[-1][:2]))
        prompt = build_prompt(example)
        # the cached raw response round-trips through the SAME input_hash key
        key = compute_cache_key("p23_nlify_v1", prompt["input_hash"])
        assert cache.get(key) is not None


def test_bad_teacher_shapes_are_counted_not_fatal(tmp_path):
    """Format-validation failures are COUNTED (pass-rate metric) and skipped;
    they never abort the batch nor enter the corpus."""
    from floor_gen.corpus import generate_corpus
    from floor_gen.matrix import load_matrix

    matrix = load_matrix(committed_matrix_path())
    cell = next(c for c in matrix.cells if c.cell_id == "aspirate__none")

    def respond(system: str, user: str) -> str:
        return "utterance only, no json"

    rows, stats = generate_corpus(
        matrix, FakeTeacher(responder=respond), TeacherCache(tmp_path), selected_cell_ids=(cell,)
    )
    assert rows == []
    assert stats.examples_total == cell.examples_per_cell
    assert stats.rejected == stats.examples_total
    assert stats.accepted == 0


def test_mixed_good_bad_replies_yield_correct_pass_rate(tmp_path):
    from floor_gen.corpus import generate_corpus
    from floor_gen.matrix import load_matrix

    matrix = load_matrix(committed_matrix_path())
    cell = next(c for c in matrix.cells if c.cell_id == "aspirate__none")
    flips = {"n": 0}

    def respond(system: str, user: str) -> str:
        flips["n"] += 1
        if flips["n"] % 2 == 0:
            return "not json at all"
        return json.dumps({"utterance": f"good {flips['n']}", "clarification": None}, sort_keys=True)

    rows, stats = generate_corpus(
        matrix, FakeTeacher(responder=respond), TeacherCache(tmp_path), selected_cell_ids=(cell,)
    )
    assert stats.examples_total == cell.examples_per_cell
    assert stats.rejected + stats.accepted == stats.examples_total
    assert len(rows) == stats.accepted
    assert 0.0 < stats.pass_rate < 1.0
