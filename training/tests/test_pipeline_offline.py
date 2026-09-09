"""Offline end-to-end pipeline tests: rows, provenance, D7/D11 supervision.

No network: a scripted FakeTeacher stands in for both sanctioned backends.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from floor_gen.cache import TeacherCache
from floor_gen.corpus import (
    CorpusError,
    generate_corpus,
    parse_teacher_raw,
    validate_class_shape,
)
from floor_gen.declarations import render_declaration
from floor_gen.matrix import cells_round_robin, committed_matrix_path, load_matrix
from floor_gen.teachers import FakeTeacher
from floor_gen.versions import GENERATOR_VERSION, PROMPT_VERSION

_OK = json.dumps(
    {"utterance": "Aspirate 50 microliters from plate_1_A1.", "clarification": None},
    sort_keys=True,
)
_CLARIFY = json.dumps(
    {
        "utterance": "Do the off-list thing please.",
        "clarification": "I can't do that, but I can aspirate, dispense, transfer, move things, or read plates.",
    },
    sort_keys=True,
)


def _teacher_for(cls: str) -> FakeTeacher:
    return FakeTeacher(responder=lambda s, u: _CLARIFY if cls == "out-of-surface" else _OK)


def test_provenance_tags_on_every_row(tmp_path: Path):
    matrix = load_matrix(committed_matrix_path())
    ids = ["aspirate__none", "dispense__missing-slot", "transfer__ambiguous-referent"]
    rows, stats = generate_corpus(matrix, FakeTeacher(), TeacherCache(tmp_path), selected_cell_ids=ids)
    assert stats.examples_total >= 3
    want = {
        "provenance": "coverage",
        "generator_version": GENERATOR_VERSION,
        "prompt_version": PROMPT_VERSION,
        "teacher_model_version": "fake-teacher@test",
    }
    for row in rows:
        assert row["provenance"] == want


def test_supervision_kinds_per_class_d7_d11(tmp_path: Path):
    matrix = load_matrix(committed_matrix_path())
    cache = TeacherCache(tmp_path)
    selections = [
        ("aspirate__none", "tool_call"),
        ("read_absorbance__missing-slot", "tool_call"),
        ("stamp__ambiguous-referent", "tool_call"),
        ("shake__out-of-surface", "nl_clarification"),
    ]
    for cell_id, expected_kind in selections:
        cell = next(c for c in matrix.cells if c.cell_id == cell_id)
        rows, _ = generate_corpus(matrix, _teacher_for(cell.ambiguity_class), cache, selected_cell_ids=(cell,))
        for row in rows:
            assert row["supervision"]["kind"] == expected_kind, cell_id


def test_out_of_surface_rows_have_no_tool_call_and_no_tools_block(tmp_path: Path):
    matrix = load_matrix(committed_matrix_path())
    cell = next(c for c in matrix.cells if c.cell_id == "generic__out-of-surface")
    rows, _ = generate_corpus(matrix, _teacher_for("out-of-surface"), TeacherCache(tmp_path), selected_cell_ids=(cell,))
    for row in rows:
        assert row["tools"] == []
        assert row["structured_calls"] == []
        assert row["intent"]["calls"] == []
        assert row["clarification"]
        assert row["utterance"]


def test_in_surface_rows_embed_declaration_and_derived_gaps(tmp_path: Path):
    matrix = load_matrix(committed_matrix_path())
    cell = next(c for c in matrix.cells if c.cell_id == "read_absorbance__missing-slot")
    rows, _ = generate_corpus(matrix, FakeTeacher(), TeacherCache(tmp_path), selected_cell_ids=(cell,))
    decl = render_declaration("read_absorbance")
    for row in rows:
        assert row["tools"] == [decl]
        (call,) = row["intent"]["calls"]
        assert call["name"] == "read_absorbance"
        assert "wavelength_nm" in call["missing_required"]
        # optional wells may ride along; wavelength must NOT be present
        assert "wavelength_nm" not in call["params"]


def test_parse_teacher_raw_defensive_fences():
    fenced = "```json\n" + _OK + "\n```"
    parsed = parse_teacher_raw(fenced, "cell-x")
    assert parsed["clarification"] is None
    assert parsed["utterance"].startswith("Aspirate")


def test_parse_teacher_raw_rejects_extra_keys():
    bad = json.dumps({"utterance": "x", "clarification": None, "surprise": 1})
    with pytest.raises(CorpusError):
        parse_teacher_raw(bad, "cell-y")


def test_class_shape_rules():
    matrix = load_matrix(committed_matrix_path())
    none_cell = next(c for c in matrix.cells if c.cell_id == "aspirate__none")
    oos_cell = next(c for c in matrix.cells if c.cell_id == "mix__out-of-surface")

    parsed_ok = parse_teacher_raw(_OK, "c")
    validate_class_shape(parsed_ok, none_cell)
    with pytest.raises(CorpusError):
        validate_class_shape(parsed_ok, oos_cell)

    parsed_clar = parse_teacher_raw(_CLARIFY, "c")
    with pytest.raises(CorpusError):
        validate_class_shape(parsed_clar, none_cell)
    validate_class_shape(parsed_clar, oos_cell)


def test_regenerate_subcommand_never_calls_teacher_and_is_byte_identical(tmp_path: Path):
    """The CLI regenerate path: manifest-driven, cache-only, loud on miss."""
    from floor_gen.cli import main

    matrix = load_matrix(committed_matrix_path())
    cells = [c.cell_id for c in cells_round_robin(matrix.cells)[:4]]
    out_a = tmp_path / "a"
    cache_dir = tmp_path / "cache"

    rc = main(
        ["generate", "--backend", "fake", "--cells", ",".join(cells), "--out-dir", str(out_a),
         "--cache-dir", str(cache_dir), "--corpus-name", "smoke.jsonl"]
    )
    assert rc == 0

    out_b = tmp_path / "b"
    rc = main(
        ["regenerate", "--manifest", str(out_a / "manifest.json"), "--out-dir", str(out_b),
         "--cache-dir", str(cache_dir), "--corpus-name", "smoke.jsonl"]
    )
    assert rc == 0
    assert (out_a / "smoke.jsonl").read_bytes() == (out_b / "smoke.jsonl").read_bytes()


def test_regenerate_fails_loud_on_cache_miss(tmp_path: Path):
    from floor_gen.cli import main

    matrix = load_matrix(committed_matrix_path())
    cells = [c.cell_id for c in cells_round_robin(matrix.cells)[:2]]
    out_a = tmp_path / "a"
    cache_dir = tmp_path / "cache"
    rc = main(["generate", "--backend", "fake", "--cells", ",".join(cells), "--out-dir", str(out_a),
               "--cache-dir", str(cache_dir)])
    assert rc == 0
    # Wipe one cache entry -> regenerate must fail loudly, never re-call.
    first_entry = sorted(Path(cache_dir).glob("*.json"))[0]
    first_entry.unlink()
    out_b = tmp_path / "b"
    rc = main(["regenerate", "--manifest", str(out_a / "manifest.json"), "--out-dir", str(out_b),
               "--cache-dir", str(cache_dir)])
    assert rc == 2


def test_oxalpha_batch_writer_output_shape(tmp_path: Path):
    from floor_gen.cli import main

    out_dir = tmp_path / "batches"
    rc = main(["batches", "--limit", "2", "--out-dir", str(out_dir), "--batch-size", "3"])
    assert rc == 0
    files = sorted(out_dir.glob("batch_*.md"))
    assert files
    text = files[0].read_text(encoding="utf-8")
    assert "input_hash=" in text
    assert f"prompt_version={PROMPT_VERSION}" in text
    assert '"utterance"' in text and "responses.jsonl" in text


# --- P2.2 execution-verify wiring (260828_wire_execution_verify) ------------


def test_execution_verify_passes_and_attaches_summary(tmp_path: Path):
    """A genuinely clean "none"-class row's ground truth actually executes
    against the REAL P2.2 harness -- kept, and carries a summary a human can
    audit without re-running verify() themselves."""
    matrix = load_matrix(committed_matrix_path())
    cell = next(c for c in matrix.cells if c.cell_id == "aspirate__none")
    rows, stats = generate_corpus(matrix, FakeTeacher(), TeacherCache(tmp_path), selected_cell_ids=(cell,))
    assert rows and stats.execution_rejected == 0
    for row in rows:
        assert row["execution_verify"]["passed"] is True
        assert row["execution_verify"]["backend"] == "LiquidHandlerChatterboxBackend"
        names = {c["name"] for c in row["execution_verify"]["checks"]}
        assert "execution_ok" in names and "tips_delta" in names
        assert any(n.startswith("volume_delta") for n in names)


def test_execution_verify_rejects_a_genuinely_broken_call(tmp_path: Path, monkeypatch):
    """A call whose volume physically cannot be aspirated (impossible
    tip/volume semantics) is rejected by REAL verify(), counted, and never
    silently dropped or crashed on."""
    from dataclasses import replace

    import floor_gen.corpus as corpus_mod
    from floor_gen.synth import synthesize_example as real_synthesize_example

    matrix = load_matrix(committed_matrix_path())
    cell = next(c for c in matrix.cells if c.cell_id == "aspirate__none")

    def broken_synthesize_example(cell_arg, index):
        example = real_synthesize_example(cell_arg, index)
        if cell_arg.cell_id != cell.cell_id:
            return example
        call = dict(example.schema_calls[0])
        call["params"] = {**call["params"], "volume_ul": [999999.0]}  # impossible: empty well
        return replace(example, schema_calls=(call,))

    monkeypatch.setattr(corpus_mod, "synthesize_example", broken_synthesize_example)
    rows, stats = generate_corpus(matrix, FakeTeacher(), TeacherCache(tmp_path), selected_cell_ids=(cell,))
    assert rows == []
    assert stats.execution_rejected == cell.examples_per_cell
    assert stats.rejected == cell.examples_per_cell
    assert stats.accepted == 0


def test_execution_verify_skips_not_rejects_non_executable_classes(tmp_path: Path):
    """out-of-surface (no call), missing-slot (deliberately incomplete), and
    ambiguous-referent (deliberately ungroundable) rows are NEVER real
    execution-verify ground truth (D7) -- kept, counted as skipped, never
    rejected, and never crash the run."""
    matrix = load_matrix(committed_matrix_path())
    ids = ["generic__out-of-surface", "dispense__missing-slot", "transfer__ambiguous-referent"]
    cache = TeacherCache(tmp_path)
    rows, stats = generate_corpus(
        matrix,
        FakeTeacher(responder=lambda s, u: _CLARIFY if "out-of-surface" in s + u else _OK),
        cache,
        selected_cell_ids=ids,
    )
    by_id = {c.cell_id: c for c in matrix.cells}
    expected_kept = sum(by_id[i].examples_per_cell for i in ids)
    assert len(rows) == expected_kept
    assert stats.execution_rejected == 0
    assert stats.execution_skipped == expected_kept
    for row in rows:
        assert "execution_verify" not in row


def test_skip_execution_verify_flag_disables_the_gate(tmp_path: Path, monkeypatch):
    """--skip-execution-verify (verify_execution=False) restores pre-P2.2
    shape-validation-only behavior: the same broken call from
    test_execution_verify_rejects_a_genuinely_broken_call is now KEPT."""
    from dataclasses import replace

    import floor_gen.corpus as corpus_mod
    from floor_gen.synth import synthesize_example as real_synthesize_example

    matrix = load_matrix(committed_matrix_path())
    cell = next(c for c in matrix.cells if c.cell_id == "aspirate__none")

    def broken_synthesize_example(cell_arg, index):
        example = real_synthesize_example(cell_arg, index)
        if cell_arg.cell_id != cell.cell_id:
            return example
        call = dict(example.schema_calls[0])
        call["params"] = {**call["params"], "volume_ul": [999999.0]}
        return replace(example, schema_calls=(call,))

    monkeypatch.setattr(corpus_mod, "synthesize_example", broken_synthesize_example)
    rows, stats = generate_corpus(
        matrix, FakeTeacher(), TeacherCache(tmp_path), selected_cell_ids=(cell,), verify_execution=False
    )
    assert len(rows) == cell.examples_per_cell
    assert stats.execution_rejected == 0
    assert stats.rejected == 0
    for row in rows:
        assert "execution_verify" not in row
