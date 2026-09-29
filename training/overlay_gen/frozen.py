"""Frozen overlay source: rows whose source notebook upstream PLR deleted.

At PLR 1.0 the pylabrobot docs dropped ``hamilton-star/{basic,foil}.ipynb`` and
``opentrons/ot2/{hello-world,ot2-simulator}.ipynb``. The overlay rows mined from
them at the previous pin (``dd79c4c89bc0...``) are kept, verbatim, as an explicit
FROZEN source (``frozen/pre_plr1_notebook_rows.jsonl``) so the assembled train
corpus and the pinned eval split do not shift under a submodule bump.

Contract (all enforced here, none by convention):

- Frozen rows are copied as-is: never re-mined, re-verified or re-paraphrased.
- The archive is integrity-pinned (row count + sha256 in the sibling manifest).
- A frozen row whose source path EXISTS at the current pin is a hard error
  (:class:`FrozenSourceStillExistsError`): the frozen set may only cover
  deleted sources; a resurrected notebook must be re-mined live instead.
- On a content-key collision (``normalize_utterance(instruction)`` -- the same
  key ``build_pairs`` dedups on) the LIVE row wins and the frozen row is dropped.
- The merged order is deterministic: a stable sort by ``provenance.origin``
  (the order ``build_pairs`` walks its calls in), live rows before frozen rows
  on ties.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from overlay_gen.miner import REPO_ROOT
from overlay_gen.normalize import normalize_utterance
from overlay_gen.shapes import validate_row

__all__ = [
    "FROZEN_DIR",
    "FROZEN_ROWS_PATH",
    "FROZEN_MANIFEST_PATH",
    "FrozenError",
    "FrozenSourceStillExistsError",
    "FrozenMergeStats",
    "load_frozen_rows",
    "merge_frozen",
    "write_rows_jsonl",
]

FROZEN_DIR = Path(__file__).resolve().parent / "frozen"
FROZEN_ROWS_PATH = FROZEN_DIR / "pre_plr1_notebook_rows.jsonl"
FROZEN_MANIFEST_PATH = FROZEN_DIR / "pre_plr1_notebook_rows.manifest.json"


class FrozenError(ValueError):
    """The frozen archive is missing, corrupt, or violates its contract."""


class FrozenSourceStillExistsError(FrozenError):
    """A frozen row's source notebook exists at the current pin."""


@dataclass(frozen=True)
class FrozenMergeStats:
    live_rows: int
    frozen_rows_loaded: int
    frozen_rows_included: int
    frozen_rows_shadowed_by_live: int
    final_rows: int

    def as_dict(self) -> dict[str, int]:
        return {
            "live_rows": self.live_rows,
            "frozen_rows_loaded": self.frozen_rows_loaded,
            "frozen_rows_included": self.frozen_rows_included,
            "frozen_rows_shadowed_by_live": self.frozen_rows_shadowed_by_live,
            "final_rows": self.final_rows,
        }


def _row_key(row: dict[str, Any]) -> str:
    return normalize_utterance(row.get("instruction"))


def load_frozen_rows(
    rows_path: Path = FROZEN_ROWS_PATH,
    manifest_path: Path = FROZEN_MANIFEST_PATH,
    *,
    repo_root: Path = REPO_ROOT,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load + validate the frozen archive. Returns ``(rows, manifest)``.

    Raises :class:`FrozenError` on any integrity failure and
    :class:`FrozenSourceStillExistsError` if a row's source path exists under
    ``repo_root``. An absent archive is an error, never an empty set: silently
    dropping it would shrink the corpus and trip the eval-pin guard far
    downstream."""
    for path in (rows_path, manifest_path):
        if not Path(path).is_file():
            raise FrozenError(f"frozen archive file missing: {path}")
    raw = Path(rows_path).read_bytes()
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    digest = hashlib.sha256(raw).hexdigest()
    if digest != manifest.get("rows_sha256"):
        raise FrozenError(
            f"frozen rows sha256 {digest} != manifest {manifest.get('rows_sha256')!r}: "
            "the archive was edited; frozen rows are immutable"
        )

    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if len(rows) != manifest.get("row_count"):
        raise FrozenError(f"frozen row count {len(rows)} != manifest {manifest.get('row_count')!r}")

    seen: set[str] = set()
    for row in rows:
        errors = validate_row(row)
        if errors:
            raise FrozenError(f"frozen row {row.get('id')!r} invalid: {errors}")
        key = _row_key(row)
        if key in seen:
            raise FrozenError(f"duplicate content key in frozen archive: {row.get('id')!r}")
        seen.add(key)
        source = row["provenance"]["source_notebook_or_protocol"]
        if (Path(repo_root) / source).exists():
            raise FrozenSourceStillExistsError(
                f"frozen row {row['id']!r} has source {source!r}, which exists at the "
                "current pin: the frozen set may only cover deleted sources. Drop the "
                "row from the archive (and re-pin the manifest) so it is re-mined live."
            )
    return rows, manifest


def merge_frozen(
    live_rows: list[dict[str, Any]], frozen_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], FrozenMergeStats]:
    """``live ∪ frozen`` deduped on the content key, live winning collisions,
    in deterministic ``provenance.origin`` order. Inputs are not mutated."""
    live_keys = {_row_key(r) for r in live_rows}
    kept = [r for r in frozen_rows if _row_key(r) not in live_keys]
    # Python's sort is stable: live rows precede frozen rows on equal origin,
    # and each list keeps its own internal order.
    merged = sorted(
        [*live_rows, *kept], key=lambda r: r["provenance"]["origin"]
    )
    return merged, FrozenMergeStats(
        live_rows=len(live_rows),
        frozen_rows_loaded=len(frozen_rows),
        frozen_rows_included=len(kept),
        frozen_rows_shadowed_by_live=len(frozen_rows) - len(kept),
        final_rows=len(merged),
    )


def write_rows_jsonl(rows: list[dict[str, Any]], out_path: Path) -> None:
    """Byte-for-byte the writer ``build_pairs`` uses (sorted keys, atomic)."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(out_path)
