"""Frozen overlay source (owner decision, task 260929_plr-1.0-migration D2).

Rows mined from notebooks upstream PLR deleted at 1.0 live in a tracked,
integrity-pinned archive and are merged into ``overlay_full.jsonl`` so the
assembled train corpus and the pinned eval split do not move. Pins:

- the archive loads, matches its manifest, and covers only deleted sources;
- merge = live U frozen, deduped on the pipeline's content key, LIVE wins;
- a frozen row whose source exists at the current pin is a hard error;
- the committed overlay contains every frozen row verbatim;
- NEGATIVE CONTROL: without the frozen rows the assembly eval-pin guard fails
  (so the merge is load-bearing, not decorative).
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import assemble.build as build
from assemble.pin import PIN_REL, load_pin
from overlay_gen.frozen import (
    FROZEN_MANIFEST_PATH,
    FROZEN_ROWS_PATH,
    FrozenError,
    FrozenSourceStillExistsError,
    load_frozen_rows,
    merge_frozen,
    write_rows_jsonl,
)
from overlay_gen.normalize import normalize_utterance

REPO = Path(__file__).resolve().parents[2]
OVERLAY_FULL = REPO / "training" / "overlay_gen" / "out" / "overlay_full.jsonl"


def _real_frozen():
    rows, manifest = load_frozen_rows()
    return rows, manifest


def _write_archive(tmp_path: Path, rows: list[dict]) -> tuple[Path, Path]:
    """A self-consistent archive (rows + manifest with the right sha/count)."""
    payload = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    rows_path = tmp_path / "rows.jsonl"
    manifest_path = tmp_path / "manifest.json"
    rows_path.write_text(payload, encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "row_count": len(rows),
                "rows_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    return rows_path, manifest_path


def _live_like(row: dict, *, instruction: str | None = None, origin: str | None = None) -> dict:
    """A 'freshly mined' row derived from a real row (valid shape), marked live."""
    live = copy.deepcopy(row)
    live["provenance"]["generator_version"] = "LIVE"
    if instruction is not None:
        live["instruction"] = instruction
    if origin is not None:
        live["provenance"]["origin"] = origin
    return live


# --- the committed archive ------------------------------------------------------


def test_committed_archive_loads_and_matches_manifest():
    rows, manifest = _real_frozen()
    assert len(rows) == manifest["row_count"] == 54
    assert manifest["origin_pin"] == "dd79c4c89bc008629a1c598ea614be5e6067d1f9"
    assert sum(manifest["rows_by_source"].values()) == 54


def test_committed_archive_covers_only_deleted_sources():
    rows, _ = _real_frozen()
    sources = {r["provenance"]["source_notebook_or_protocol"] for r in rows}
    assert len(sources) == 4
    for source in sources:
        assert source.endswith(".ipynb")
        assert not (REPO / source).exists(), f"{source} exists at the current pin"


def test_committed_overlay_contains_every_frozen_row_verbatim():
    frozen_lines = FROZEN_ROWS_PATH.read_text(encoding="utf-8").splitlines()
    overlay_lines = set(OVERLAY_FULL.read_text(encoding="utf-8").splitlines())
    missing = [ln for ln in frozen_lines if ln not in overlay_lines]
    assert not missing, f"{len(missing)} frozen rows absent/altered in overlay_full.jsonl"


def test_committed_overlay_keys_are_unique():
    rows = [json.loads(l) for l in OVERLAY_FULL.read_text(encoding="utf-8").splitlines() if l.strip()]
    keys = [normalize_utterance(r["instruction"]) for r in rows]
    assert len(keys) == len(set(keys))


# --- merge semantics -------------------------------------------------------------


def test_frozen_rows_are_merged_and_counted():
    frozen, _ = _real_frozen()
    donor = frozen[0]
    live = [_live_like(donor, instruction="a brand new live utterance", origin="a/live.py::f@1")]
    merged, stats = merge_frozen(live, frozen)
    assert stats.live_rows == 1
    assert stats.frozen_rows_loaded == stats.frozen_rows_included == 54
    assert stats.frozen_rows_shadowed_by_live == 0
    assert stats.final_rows == len(merged) == 55
    ids = [r["id"] for r in merged]
    assert all(f["id"] in ids for f in frozen)
    # frozen rows pass through untouched (same bytes once serialised)
    by_id = {r["id"]: r for r in merged}
    for f in frozen:
        assert json.dumps(by_id[f["id"]], sort_keys=True) == json.dumps(f, sort_keys=True)


def test_live_wins_on_content_key_collision():
    frozen, _ = _real_frozen()
    victim = frozen[3]
    # same normalized utterance (case + whitespace differ) -> same content key
    live_row = _live_like(victim, instruction="  " + victim["instruction"].upper().replace(" ", "  ") + " ")
    assert normalize_utterance(live_row["instruction"]) == normalize_utterance(victim["instruction"])
    merged, stats = merge_frozen([live_row], frozen)
    assert stats.frozen_rows_shadowed_by_live == 1
    assert stats.frozen_rows_included == 53
    assert stats.final_rows == len(merged) == 54
    kept = [r for r in merged if normalize_utterance(r["instruction"]) == normalize_utterance(victim["instruction"])]
    assert len(kept) == 1
    assert kept[0]["provenance"]["generator_version"] == "LIVE"  # the live row, not the frozen one
    assert kept[0]["instruction"] == live_row["instruction"]


def test_merge_is_deterministic_origin_ordered_live_first_on_ties():
    frozen, _ = _real_frozen()
    tie_origin = frozen[5]["provenance"]["origin"]
    live = [
        _live_like(frozen[0], instruction="zzz live at the tie origin", origin=tie_origin),
        _live_like(frozen[0], instruction="aaa live before everything", origin="."),
    ]
    a, _ = merge_frozen(live, frozen)
    b, _ = merge_frozen(copy.deepcopy(live), copy.deepcopy(frozen))
    assert a == b
    origins = [r["provenance"]["origin"] for r in a]
    assert origins == sorted(origins)
    at_tie = [r for r in a if r["provenance"]["origin"] == tie_origin]
    assert at_tie[0]["provenance"]["generator_version"] == "LIVE"  # live precedes frozen
    assert all(r["provenance"]["generator_version"] != "LIVE" for r in at_tie[1:])


def test_merge_does_not_mutate_inputs():
    frozen, _ = _real_frozen()
    live = [_live_like(frozen[0], instruction="another live row", origin="b/live.py::g@2")]
    frozen_before, live_before = copy.deepcopy(frozen), copy.deepcopy(live)
    merge_frozen(live, frozen)
    assert frozen == frozen_before and live == live_before


def test_write_rows_jsonl_matches_committed_bytes(tmp_path):
    rows = [json.loads(l) for l in OVERLAY_FULL.read_text(encoding="utf-8").splitlines() if l.strip()]
    out = tmp_path / "o.jsonl"
    write_rows_jsonl(rows, out)
    assert out.read_bytes() == OVERLAY_FULL.read_bytes()


# --- the hard errors -------------------------------------------------------------


def test_frozen_row_with_existing_source_is_a_hard_error(tmp_path):
    frozen, _ = _real_frozen()
    rows_path, manifest_path = _write_archive(tmp_path, frozen[:2])
    fake_repo = tmp_path / "repo"
    source = frozen[1]["provenance"]["source_notebook_or_protocol"]
    (fake_repo / source).parent.mkdir(parents=True)
    (fake_repo / source).write_text("{}", encoding="utf-8")  # the notebook 'came back'
    with pytest.raises(FrozenSourceStillExistsError, match="exists at the current pin"):
        load_frozen_rows(rows_path, manifest_path, repo_root=fake_repo)
    # same archive, source genuinely absent -> loads
    rows, _ = load_frozen_rows(rows_path, manifest_path, repo_root=tmp_path / "empty_repo")
    assert len(rows) == 2


def test_tampered_archive_fails_sha_check(tmp_path):
    frozen, _ = _real_frozen()
    rows_path, manifest_path = _write_archive(tmp_path, frozen[:3])
    rows_path.write_text(rows_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(FrozenError, match="sha256"):
        load_frozen_rows(rows_path, manifest_path, repo_root=tmp_path)


def test_missing_archive_is_an_error_not_an_empty_set(tmp_path):
    with pytest.raises(FrozenError, match="missing"):
        load_frozen_rows(tmp_path / "nope.jsonl", tmp_path / "nope.json", repo_root=tmp_path)


def test_duplicate_content_key_in_archive_is_an_error(tmp_path):
    frozen, _ = _real_frozen()
    dup = copy.deepcopy(frozen[0])
    dup["instruction"] = "  " + frozen[0]["instruction"].upper()
    rows_path, manifest_path = _write_archive(tmp_path, [frozen[0], dup])
    with pytest.raises(FrozenError, match="duplicate content key"):
        load_frozen_rows(rows_path, manifest_path, repo_root=tmp_path)


# --- negative control: the frozen rows are load-bearing ---------------------------


def test_frozen_rows_cover_pinned_eval_rows():
    frozen, _ = _real_frozen()
    pin = load_pin(REPO / PIN_REL)
    pinned_frozen = sorted(r["id"] for r in frozen if r["id"] in pin["rows"])
    assert len(pinned_frozen) == 6  # the reason this source exists


def test_negative_control_assembly_pin_guard_fails_without_frozen_rows(monkeypatch):
    """Drop the frozen rows from the overlay the assembler reads: the eval-pin
    guard MUST fire. If this passes vacuously the frozen merge is not needed."""
    frozen, _ = _real_frozen()
    frozen_ids = {r["id"] for r in frozen}
    overlay_path = REPO / build.OVERLAY_CORPUS_REL
    real_read = build._read_jsonl

    def read_without_frozen(path):
        rows = real_read(path)
        if Path(path) == overlay_path:
            rows = [r for r in rows if r["id"] not in frozen_ids]
        return rows

    monkeypatch.setattr(build, "_read_jsonl", read_without_frozen)
    with pytest.raises(AssertionError, match="pinned eval rows missing/excluded"):
        build.build_artifacts()
