"""Train-side row selection: dedup + negative-mixing arms (pure, deterministic).

Inputs are the assembled P2.5 corpus and its line-aligned sidecar. Output is
an ordered list of :class:`CorpusRow` plus a summary the manifest records.

Rules (prereg 260901):

- Only ``metadata == "train"`` rows are ever selected; eval is untouched.
- Dedup: exact normalized-utterance duplicates (``overlay_gen.normalize``,
  the same rule the assembler's duplicate counter uses) collapse to the row
  with the lowest ``record_id``.
- Arm ratio ``r``: positives (``clean_parse``) are all kept; negatives total
  ``round(r * n_pos)`` split across the three clarify classes proportionally
  to their post-dedup counts (largest remainder), sampled per class with
  ``random.Random(f"{RECIPE_VERSION}|{arm}|{seed}")`` over rows sorted by
  ``record_id``. ``r is None`` keeps every negative (raw split).
- The returned order is by ``record_id``; the trainer shuffles with its own seed.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from overlay_gen.normalize import normalize_utterance

from .versions import ARMS, NEGATIVE_CLASSES, POSITIVE_CLASS, RECIPE_VERSION

__all__ = [
    "CorpusRow",
    "load_corpus",
    "train_rows",
    "dedup_rows",
    "select_arm",
    "arm_summary",
    "MixingError",
]


class MixingError(ValueError):
    """Corpus/sidecar shape problem that must stop a run loudly."""


@dataclass(frozen=True)
class CorpusRow:
    """One corpus line zipped with its sidecar line."""

    index: int
    record_id: str
    split: str
    ambiguity_class: str
    utterance: str
    supervision_kind: str
    native: dict[str, Any]
    sidecar: dict[str, Any]

    @property
    def is_positive(self) -> bool:
        return self.ambiguity_class == POSITIVE_CLASS


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise MixingError(f"{path}:{lineno}: invalid JSON ({exc})") from exc
    return rows


def load_corpus(corpus_path: Path, sidecar_path: Path) -> list[CorpusRow]:
    """Zip corpus + sidecar line by line, validating alignment."""
    native = _read_jsonl(corpus_path)
    side = _read_jsonl(sidecar_path)
    if len(native) != len(side):
        raise MixingError(
            f"corpus/sidecar length mismatch: {len(native)} vs {len(side)} "
            f"({corpus_path.name} / {sidecar_path.name})"
        )
    rows: list[CorpusRow] = []
    for idx, (n, s) in enumerate(zip(native, side)):
        if n.get("metadata") != s.get("split"):
            raise MixingError(
                f"line {idx + 1}: corpus metadata {n.get('metadata')!r} != sidecar split {s.get('split')!r}"
            )
        cls = s.get("ambiguity_class")
        if cls != POSITIVE_CLASS and cls not in NEGATIVE_CLASSES:
            raise MixingError(f"line {idx + 1}: unknown ambiguity_class {cls!r}")
        rows.append(
            CorpusRow(
                index=idx,
                record_id=str(s["record_id"]),
                split=str(s["split"]),
                ambiguity_class=str(cls),
                utterance=str(s["utterance"]),
                supervision_kind=str(s.get("supervision_kind", "")),
                native=n,
                sidecar=s,
            )
        )
    ids = [r.record_id for r in rows]
    if len(set(ids)) != len(ids):
        raise MixingError("duplicate record_id in sidecar")
    return rows


def train_rows(rows: Sequence[CorpusRow]) -> list[CorpusRow]:
    return sorted((r for r in rows if r.split == "train"), key=lambda r: r.record_id)


def dedup_rows(rows: Sequence[CorpusRow]) -> tuple[list[CorpusRow], list[CorpusRow]]:
    """Collapse exact normalized-utterance duplicates; keep lowest record_id.

    Returns ``(kept, dropped)``, both ordered by ``record_id``.
    """
    seen: dict[str, CorpusRow] = {}
    dropped: list[CorpusRow] = []
    for row in sorted(rows, key=lambda r: r.record_id):
        key = normalize_utterance(row.utterance)
        if key in seen:
            dropped.append(row)
        else:
            seen[key] = row
    return sorted(seen.values(), key=lambda r: r.record_id), dropped


def _largest_remainder(quota: int, counts: dict[str, int]) -> dict[str, int]:
    """Split ``quota`` across classes proportionally to ``counts``."""
    total = sum(counts.values())
    if total == 0 or quota <= 0:
        return {k: 0 for k in counts}
    raw = {k: quota * v / total for k, v in counts.items()}
    floors = {k: int(raw[k]) for k in counts}
    remainder = quota - sum(floors.values())
    # Deterministic tie-break: larger fractional part first, then class name.
    order = sorted(counts, key=lambda k: (-(raw[k] - floors[k]), k))
    for k in order[:remainder]:
        floors[k] += 1
    # Never ask a class for more rows than it has; hand the excess to others.
    excess = 0
    for k in counts:
        if floors[k] > counts[k]:
            excess += floors[k] - counts[k]
            floors[k] = counts[k]
    for k in order:
        while excess and floors[k] < counts[k]:
            floors[k] += 1
            excess -= 1
    return floors


def select_arm(rows: Sequence[CorpusRow], arm: str, seed: int = 0) -> list[CorpusRow]:
    """Apply an ablation arm to (already deduped) train rows."""
    if arm not in ARMS:
        raise MixingError(f"unknown arm {arm!r}; expected one of {sorted(ARMS)}")
    ratio = ARMS[arm]
    positives = [r for r in rows if r.is_positive]
    negatives = {cls: sorted((r for r in rows if r.ambiguity_class == cls), key=lambda r: r.record_id)
                 for cls in NEGATIVE_CLASSES}
    if ratio is None:
        chosen = list(positives) + [r for cls in NEGATIVE_CLASSES for r in negatives[cls]]
        return sorted(chosen, key=lambda r: r.record_id)
    quota = round(ratio * len(positives))
    per_class = _largest_remainder(quota, {cls: len(v) for cls, v in negatives.items()})
    rng = random.Random(f"{RECIPE_VERSION}|{arm}|{seed}")
    chosen = list(positives)
    for cls in NEGATIVE_CLASSES:
        pool = negatives[cls]
        k = per_class[cls]
        chosen.extend(rng.sample(pool, k) if k < len(pool) else pool)
    return sorted(chosen, key=lambda r: r.record_id)


def arm_summary(selected: Sequence[CorpusRow], *, dedup_dropped: Sequence[CorpusRow],
                train_total: int, arm: str, seed: int) -> dict[str, Any]:
    """Counts the manifest records (and the tests pin)."""
    by_class = {cls: 0 for cls in (POSITIVE_CLASS, *NEGATIVE_CLASSES)}
    for r in selected:
        by_class[r.ambiguity_class] += 1
    n_pos = by_class[POSITIVE_CLASS]
    n_neg = len(selected) - n_pos
    return {
        "arm": arm,
        "ratio_negatives_per_positive": ARMS[arm],
        "seed": seed,
        "recipe_version": RECIPE_VERSION,
        "train_rows_assembled": train_total,
        "dedup_dropped": len(dedup_dropped),
        "dedup_dropped_record_ids": [r.record_id for r in dedup_dropped],
        "selected_total": len(selected),
        "selected_by_class": by_class,
        "negative_fraction": (n_neg / len(selected)) if selected else None,
        "selected_record_ids": [r.record_id for r in selected],
    }
