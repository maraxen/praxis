"""Natural-phrasing lane over the accepted floor corpus (task 260902_p26b_surface_data;
extended to out-of-surface rows in task 260903_p26c_oos_natural).

For every floor row, ask the teacher for a SECOND utterance phrased the way a
scientist speaks, and keep it only if a deterministic filter finds no
identifier leakage:

(a) no underscore identifier token  (plate_1, tip_rack, pick_up_tips, ...)
(b) no dotted well reference        (plate_1.D1)
(c) no square brackets              (the overlay's code grammar, plate["A1"])
(d) no canonical verb lemma for the liquid verbs (aspirat*, dispens*,
    transfer*, stamp*) -- IN-SURFACE rows only: out-of-surface requests are
    legitimately about liquid verbs ("mix by pipetting up and down before
    transferring it")
(e) not the same normalized utterance as the base row
(f) not the same normalized utterance as any pinned eval row (no new
    cross-split leakage)

In-surface rows: same structured call (``prompts.build_prompt_natural``,
natural locations, everyday verbs). Out-of-surface rows: the same off-surface
request rephrased casually (``prompts.build_prompt_natural_oos``); the
assistant ``clarification`` is COPIED VERBATIM from the base row, so the
supervision is identical to the base row and only the utterance surface
varies.

Rows copy everything from the base row except the utterance, the record_id
(``nat-`` + base id without ``cov-``), the provenance (``coverage_natural``,
the lane's prompt version, the teacher version that produced the cached
reply) and lineage (``base_record_id``, ``surface: natural``).
Execution-verify is NOT re-run: the structured call is asserted equal to a
fresh ``synthesize_example`` of the same cell/index, so the base row's
verification carries over by construction.

Rejected replies stay in the cache (deterministic regeneration).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from overlay_gen.normalize import normalize_utterance

from floor_gen.cache import TeacherCache, compute_cache_key
from floor_gen.corpus import (
    CorpusError,
    TeacherBackend,
    parse_teacher_raw,
    prewarm_prompts,
    validate_class_shape,
)
from floor_gen.matrix import AmbiguityMatrix, MatrixCell
from floor_gen.prompts import build_prompt_natural, build_prompt_natural_oos
from floor_gen.synth import synthesize_example
from floor_gen.versions import (
    GENERATOR_VERSION,
    MATRIX_VERSION,
    PLR_SUBMODULE_SHA,
    PROMPT_VERSION_NATURAL,
    PROMPT_VERSION_NATURAL_OOS,
    VERB_PARAPHRASE_LEXICON,
)

__all__ = [
    "NaturalStats",
    "FILTER_RULES",
    "surface_violations",
    "generate_natural_corpus",
    "build_natural_manifest",
    "natural_record_id",
    "eval_utterances_from_sidecar",
]

_UNDERSCORE_ID = re.compile(r"\b[A-Za-z]+_[A-Za-z0-9_]+\b")
_DOTTED_WELL = re.compile(r"\b\w+\.[A-Ha-h](?:1[0-2]|[1-9])\b")
_LIQUID_VERB = re.compile(r"\b(aspirat|dispens|transfer|stamp)\w*", re.IGNORECASE)

OUT_OF_SURFACE = "out-of-surface"

#: Rules applied per lane (manifest documentation; the code is the truth).
FILTER_RULES: dict[str, list[str]] = {
    "in_surface": [
        "underscore_identifier", "dotted_well_ref", "bracket", "canonical_verb",
        "duplicate_of_base", "duplicate_of_eval_row",
    ],
    "out_of_surface": [
        "underscore_identifier", "dotted_well_ref", "bracket",
        "duplicate_of_base", "duplicate_of_eval_row",
    ],
}


def surface_violations(
    utterance: str,
    *,
    base_utterance: str,
    eval_utterances: Iterable[str] = (),
    ambiguity_class: str = "none",
) -> list[str]:
    """Deterministic identifier-leak / duplicate checks; empty list == accept.

    ``ambiguity_class == "out-of-surface"`` skips rule (d): those requests may
    legitimately mention the liquid verbs.
    """
    out: list[str] = []
    if _UNDERSCORE_ID.search(utterance):
        out.append("underscore_identifier")
    if _DOTTED_WELL.search(utterance):
        out.append("dotted_well_ref")
    if "[" in utterance or "]" in utterance:
        out.append("bracket")
    if ambiguity_class != OUT_OF_SURFACE and _LIQUID_VERB.search(utterance):
        out.append("canonical_verb")
    norm = normalize_utterance(utterance)
    if norm == normalize_utterance(base_utterance):
        out.append("duplicate_of_base")
    if norm in set(eval_utterances):
        out.append("duplicate_of_eval_row")
    return out


def natural_record_id(base_record_id: str) -> str:
    if not base_record_id.startswith("cov-"):
        raise ValueError(f"not a floor record id: {base_record_id!r}")
    return "nat-" + base_record_id[4:]


def eval_utterances_from_sidecar(sidecar_path: Path) -> frozenset[str]:
    """Normalized utterances of the pinned eval rows (rule (f))."""
    import json

    out = set()
    for line in sidecar_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("split") == "eval":
            out.add(normalize_utterance(row["utterance"]))
    return frozenset(out)


@dataclass
class NaturalStats:
    base_rows: int = 0
    accepted: int = 0
    rejected_shape: int = 0
    rejected_filter: int = 0
    rejected_by_reason: dict[str, int] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    per_class: dict[str, int] = field(default_factory=dict)
    #: the backend used for THIS run (misses only)
    backend_teacher_model_version: str = ""
    #: teacher versions stamped on accepted rows, read from the cache records
    teacher_model_versions: dict[str, int] = field(default_factory=dict)

    @property
    def acceptance_rate(self) -> float:
        n = self.accepted + self.rejected_shape + self.rejected_filter
        return self.accepted / n if n else 0.0


def _index_of(record_id: str) -> int:
    return int(record_id.rsplit("-", 1)[1])


def _bump(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def generate_natural_corpus(
    base_rows: list[dict[str, Any]],
    matrix: AmbiguityMatrix,
    backend: TeacherBackend,
    cache: TeacherCache,
    *,
    batch_size: int = 1,
    eval_utterances: Iterable[str] = (),
) -> tuple[list[dict[str, Any]], NaturalStats]:
    cells: Mapping[str, MatrixCell] = {c.cell_id: c for c in matrix.cells}
    eval_set = frozenset(eval_utterances)
    stats = NaturalStats(backend_teacher_model_version=backend.teacher_model_version)

    # 1. synthesize + prompt for every base row; assert same call (trivially
    #    empty for out-of-surface rows)
    work: list[tuple[dict[str, Any], Any, dict[str, str], str, str]] = []
    for base in base_rows:
        stats.base_rows += 1
        cell = cells.get(base["matrix_cell"]["cell_id"])
        if cell is None:
            raise CorpusError(f"{base['record_id']}: unknown cell {base['matrix_cell']['cell_id']!r}")
        example = synthesize_example(cell, _index_of(base["record_id"]))
        if [dict(c) for c in example.structured_calls] != base["structured_calls"]:
            raise CorpusError(
                f"{base['record_id']}: re-synthesized structured_calls differ from the base row "
                "(seed or coercion drift) -- refusing to attach a natural variant"
            )
        if cell.ambiguity_class == OUT_OF_SURFACE:
            if not base.get("clarification"):
                raise CorpusError(f"{base['record_id']}: out-of-surface base row without a clarification")
            prompt = build_prompt_natural_oos(example, base["utterance"])
            version = PROMPT_VERSION_NATURAL_OOS
        else:
            prompt = build_prompt_natural(example)
            version = PROMPT_VERSION_NATURAL
        key = compute_cache_key(version, prompt["input_hash"])
        work.append((base, example, prompt, key, version))

    # 2. batched pre-warm per prompt version (no-op for backends without complete_batch)
    if batch_size > 1 and hasattr(backend, "complete_batch"):
        for version in (PROMPT_VERSION_NATURAL, PROMPT_VERSION_NATURAL_OOS):
            misses = {key: prompt for _, _, prompt, key, v in work if v == version and cache.get(key) is None}
            prewarm_prompts(misses, backend, cache, batch_size, prompt_version=version)

    # 3. per-item loop: cache -> parse -> class shape -> surface filter -> row
    rows: list[dict[str, Any]] = []
    for base, example, prompt, key, version in work:
        record = cache.get(key)
        if record is None:
            raw = backend.complete(prompt["system"], prompt["user"])
            cache.put(
                key,
                prompt_version=version,
                input_hash=prompt["input_hash"],
                teacher_model_version=backend.teacher_model_version,
                raw_response=raw,
            )
            record = cache.get(key)
            assert record is not None
            stats.cache_misses += 1
        else:
            stats.cache_hits += 1
        cell = example.cell
        cls = cell.ambiguity_class
        try:
            parsed = parse_teacher_raw(record["raw_response"], cell.cell_id)
            if cls == OUT_OF_SURFACE:
                # supervision identical to the base row: only the utterance varies
                parsed["clarification"] = base["clarification"]
            validate_class_shape(parsed, cell)
        except CorpusError:
            stats.rejected_shape += 1
            _bump(stats.rejected_by_reason, "teacher_shape")
            continue
        violations = surface_violations(
            parsed["utterance"], base_utterance=base["utterance"], eval_utterances=eval_set, ambiguity_class=cls
        )
        if violations:
            stats.rejected_filter += 1
            for v in violations:
                _bump(stats.rejected_by_reason, v)
            continue

        teacher_version = record.get("teacher_model_version") or backend.teacher_model_version
        row = {k: v for k, v in base.items() if k not in ("execution_verify",)}
        row["record_id"] = natural_record_id(base["record_id"])
        row["utterance"] = parsed["utterance"]
        row["clarification"] = parsed["clarification"]
        row["provenance"] = dict(base["provenance"]) | {
            "provenance": "coverage_natural",
            "generator_version": GENERATOR_VERSION,
            "prompt_version": version,
            "teacher_model_version": teacher_version,
            "surface": "natural",
        }
        row["lineage"] = {
            "base_record_id": base["record_id"],
            "surface": "natural",
            "base_prompt_version": base["provenance"].get("prompt_version"),
            "execution_verify_inherited_from": base["record_id"],
        }
        rows.append(row)
        stats.accepted += 1
        _bump(stats.per_class, cls)
        _bump(stats.teacher_model_versions, teacher_version)
    return rows, stats


def build_natural_manifest(stats: NaturalStats, *, base_corpus: str, base_manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "pipeline": "p23_coverage_floor_natural",
        "generator_version": GENERATOR_VERSION,
        "prompt_version": PROMPT_VERSION_NATURAL,
        "prompt_version_oos": PROMPT_VERSION_NATURAL_OOS,
        "base_corpus": base_corpus,
        "base_generator_version": base_manifest.get("generator_version"),
        "base_prompt_version": base_manifest.get("prompt_version"),
        "matrix_version": MATRIX_VERSION,
        "plr_submodule_sha": PLR_SUBMODULE_SHA,
        "backend_teacher_model_version": stats.backend_teacher_model_version,
        "teacher_model_versions": dict(sorted(stats.teacher_model_versions.items())),
        "base_rows": stats.base_rows,
        "accepted": stats.accepted,
        "rejected_shape": stats.rejected_shape,
        "rejected_filter": stats.rejected_filter,
        "rejected_by_reason": dict(sorted(stats.rejected_by_reason.items())),
        "acceptance_rate": round(stats.acceptance_rate, 4),
        "cache_hits": stats.cache_hits,
        "cache_misses": stats.cache_misses,
        "per_class": stats.per_class,
        "filter_rules": FILTER_RULES,
        "verb_paraphrase_lexicon": {k: list(v) for k, v in VERB_PARAPHRASE_LEXICON.items()},
        "execution_verify": "inherited from base rows (identical structured_calls asserted)",
        "out_of_surface_supervision": "clarification copied verbatim from the base row",
    }
