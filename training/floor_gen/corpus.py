"""Corpus assembly: cache-first teacher pass -> provenance-tagged rows.

Every row carries (deliverable 5):

    provenance: {provenance: "coverage", generator_version, prompt_version,
                 teacher_model_version}

and embeds the FunctionGemma tool declarations rendered from the namespace
table (finding 6a) plus BOTH call views (corpus-B kwargs for execution
verification; schema-side params with D11-derived gaps for the prediction
target). Supervision kind follows D7/D11 exactly:

- none               -> complete tool_call
- missing-slot       -> incomplete tool_call (missing_required derived)
- ambiguous-referent -> complete tool_call w/ unresolved slot (derived)
- out-of-surface     -> NL clarification turn, NO tool_call

Row serialization is canonical JSON (sorted keys, compact separators), so a
cache-complete regeneration is byte-identical.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_THINK_BLOCK: re.Pattern[str] = re.compile(r"<think>.*?</think>", re.DOTALL)

from coxswain.plr.tool_schema import TOOL_SCHEMA

from floor_gen.cache import TeacherCache, compute_cache_key
from floor_gen.declarations import render_declarations
from floor_gen.exec_verify import execution_verify_example
from floor_gen.matrix import AmbiguityMatrix, MatrixCell, cells_round_robin
from floor_gen.prompts import build_prompt, canonical_json
from floor_gen.synth import SynthExample, synthesize_example
from floor_gen.teachers import TeacherBackend
from floor_gen.versions import (
    GENERATOR_VERSION,
    MATRIX_VERSION,
    PLR_SUBMODULE_SHA,
    PROMPT_VERSION,
    SUPERVISION_NL_CLARIFICATION,
    SUPERVISION_TOOL_CALL,
    provenance_tags,
)
from floor_gen.value_formats import VALUE_FORMAT_CONVENTIONS

__all__ = ["CorpusError", "GenerationStats", "generate_corpus", "parse_teacher_raw", "write_outputs"]


class CorpusError(RuntimeError):
    """Loud pipeline failure: bad teacher shapes never enter the corpus."""


@dataclass(frozen=True)
class GenerationStats:
    examples_total: int
    accepted: int
    #: TOTAL rejections, any reason (shape-validation OR execution-verify;
    #: ``execution_rejected`` below is a breakdown SUBSET of this, not an
    #: addition to it -- ``rejected + accepted == examples_total`` keeps
    #: holding exactly as before P2.2 wiring).
    rejected: int
    cache_hits: int
    cache_misses: int
    per_class: dict[str, int]
    teacher_model_version: str
    #: Rows whose ground-truth call failed real execution-verify (P2.2
    #: harness) and were dropped -- a breakdown subset of ``rejected``.
    execution_rejected: int = 0
    #: execution_rejected, broken down by verify.failure_taxonomy category
    #: (260828 finding: a flat count conflates our-own-bugs, precondition
    #: gaps, and real physical-effect mismatches -- see that module's
    #: docstring). Keys sum to execution_rejected exactly.
    execution_rejected_by_category: dict[str, int] = field(default_factory=dict)
    #: Rows KEPT (counted in ``accepted``) whose execution-verify was
    #: intentionally not attempted: D7 classes with no executable ground
    #: truth (missing-slot/ambiguous-referent/out-of-surface), or a
    #: non-liquid-handler receiver (LH_BACKENDS-only limitation). NOT a
    #: rejection -- see floor_gen.exec_verify's module docstring.
    execution_skipped: int = 0

    @property
    def pass_rate(self) -> float:
        return self.accepted / self.examples_total if self.examples_total else 0.0


def parse_teacher_raw(raw: str, cell_id: str) -> dict[str, Any]:
    """Parse + shape-validate one RAW teacher response.

    Defensive fence stripping (teachers occasionally wrap JSON despite the
    contract), then STRICT shape checks. Loud on violation.
    """
    text = raw.strip()
    text = _THINK_BLOCK.sub("", text).strip()  # defensive: thinking models
    if text.startswith("```"):
        stripped = text.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
        text = stripped.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CorpusError(f"{cell_id}: teacher reply is not JSON: {raw[:200]!r}") from exc
    if not isinstance(parsed, dict):
        raise CorpusError(f"{cell_id}: teacher reply is not an object: {raw[:200]!r}")
    utterance = parsed.get("utterance")
    clarification = parsed.get("clarification")
    if not isinstance(utterance, str) or not utterance.strip():
        raise CorpusError(f"{cell_id}: missing non-empty 'utterance': {raw[:200]!r}")
    if clarification is not None and not isinstance(clarification, str):
        raise CorpusError(f"{cell_id}: 'clarification' must be string or null: {raw[:200]!r}")
    extra = set(parsed) - {"utterance", "clarification"}
    if extra:
        raise CorpusError(f"{cell_id}: unexpected keys {sorted(extra)} in teacher reply")
    return {"utterance": utterance.strip(), "clarification": clarification}


def validate_class_shape(parsed: dict[str, Any], cell: MatrixCell) -> None:
    """Class-specific supervision rules (D7/D11)."""
    has_clarification = parsed["clarification"] is not None
    if cell.ambiguity_class == "out-of-surface":
        if not has_clarification:
            raise CorpusError(
                f"{cell.cell_id}: out-of-surface example MUST carry an NL clarification"
            )
    elif has_clarification:
        raise CorpusError(
            f"{cell.cell_id}: in-surface example must have null clarification"
        )


def _expected_effects(example: SynthExample) -> list[dict[str, str]]:
    effects: list[dict[str, str]] = []
    for call in example.schema_calls:
        spec = TOOL_SCHEMA[call["name"]]
        target_ref = ""
        slots = example.derived_slots[0] if example.derived_slots else ()
        if slots:
            target_ref = slots[0][1]
        effects.extend({"effect": effect, "target_ref": target_ref} for effect in sorted(spec.effects))
    return effects


def _supervision_kind(cell: MatrixCell) -> str:
    return (
        SUPERVISION_NL_CLARIFICATION
        if cell.ambiguity_class == "out-of-surface"
        else SUPERVISION_TOOL_CALL
    )


def _record_id(cell: MatrixCell, index: int, ordinal: int) -> str:
    return f"cov-{ordinal:04d}-{cell.cell_id}-{index:02d}"


def _prewarm_cache_batched(
    cells: tuple[MatrixCell, ...],
    backend: TeacherBackend,
    cache: TeacherCache,
    batch_size: int,
) -> None:
    """Fill every cache miss across ``cells`` via grouped ``complete_batch``
    calls (260827 user-directed: group many items into one teacher call
    instead of issuing one call per item). Pure cache pre-warm -- the
    caller's normal per-item loop runs unchanged afterward and will find
    everything already cached. Requires ``backend.complete_batch`` (duck
    -typed, checked by the caller); silently a no-op for backends without it
    (e.g. Titanix, Fake), which keep the original one-call-per-item path.
    """
    misses: dict[str, dict[str, str]] = {}  # key -> prompt dict, de-duplicated
    for cell in cells:
        for index in range(cell.examples_per_cell):
            example = synthesize_example(cell, index)
            prompt = build_prompt(example)
            key = compute_cache_key(PROMPT_VERSION, prompt["input_hash"])
            if key not in misses and cache.get(key) is None:
                misses[key] = prompt
    prewarm_prompts(misses, backend, cache, batch_size, prompt_version=PROMPT_VERSION)


def prewarm_prompts(
    misses: dict[str, dict[str, str]],
    backend: TeacherBackend,
    cache: TeacherCache,
    batch_size: int,
    *,
    prompt_version: str,
) -> None:
    """Batched cache pre-warm over an explicit {cache_key: prompt} map (shared
    by the base lane above and the natural lane, which builds its own map)."""
    if not misses:
        return
    items = list(misses.items())
    for start in range(0, len(items), batch_size):
        chunk = items[start : start + batch_size]
        ids = [key for key, _ in chunk]
        users = [prompt["user"] for _, prompt in chunk]
        system = chunk[0][1]["system"]  # constant across every floor_gen prompt
        raw_by_id = backend.complete_batch(system, users, ids)  # type: ignore[attr-defined]
        for key, raw in raw_by_id.items():
            cache.put(
                key,
                prompt_version=prompt_version,
                input_hash=misses[key]["input_hash"],
                teacher_model_version=backend.teacher_model_version,
                raw_response=raw,
            )


def generate_corpus(
    matrix: AmbiguityMatrix,
    backend: TeacherBackend,
    cache: TeacherCache,
    *,
    limit_cells: int | None = None,
    selected_cell_ids: list[str] | None = None,
    batch_size: int = 1,
    verify_execution: bool = True,
) -> tuple[list[dict[str, Any]], GenerationStats]:
    """Cache-first generation over round-robin cells (or explicit selection).

    ``limit_cells`` bounds the number of CELLS processed (smoke-batch knob);
    every selected cell contributes all of its examples_per_cell.

    ``batch_size`` > 1 pre-warms the cache via grouped ``backend.complete_batch``
    calls (see ``_prewarm_cache_batched``) before the per-item loop below runs
    -- the per-item loop itself is UNCHANGED either way, since after pre-warm
    every lookup is a cache hit. No-op (falls back to one call per item) for
    backends that don't implement ``complete_batch``.

    ``verify_execution`` (default ON, per D9/AC-2.2.x: teacher shape passing
    is NOT proof a call actually executes) gates every accepted "none"-class
    row through the P2.2 execution-verify harness (``floor_gen.exec_verify``)
    before it's committed; ``False`` restores pre-P2.2-wiring behavior
    (shape-validation only) for fast local iteration -- see cli.py's
    ``--skip-execution-verify`` flag docstring for the tradeoff.
    """
    if selected_cell_ids is not None:
        # Accept both cell_id strings and MatrixCell objects; callers (CLI,
        # tests) naturally hold one or the other.
        normalized = [
            item.cell_id if isinstance(item, MatrixCell) else str(item)
            for item in selected_cell_ids
        ]
        by_id = {c.cell_id: c for c in matrix.cells}
        unknown = set(normalized) - set(by_id)
        if unknown:
            raise CorpusError(f"unknown cell ids: {sorted(unknown)}")
        ordered = tuple(by_id[cid] for cid in normalized)
    else:
        ordered = cells_round_robin(matrix.cells)
    if limit_cells is not None:
        ordered = ordered[:limit_cells]

    if batch_size > 1 and hasattr(backend, "complete_batch"):
        _prewarm_cache_batched(ordered, backend, cache, batch_size)

    prov = provenance_tags(backend.teacher_model_version)
    rows: list[dict[str, Any]] = []
    hits = misses = rejected = execution_rejected = execution_skipped = 0
    execution_rejected_by_category: dict[str, int] = {}
    ordinal = 0

    for cell in ordered:
        tools_block = (
            []
            if cell.ambiguity_class == "out-of-surface"
            else render_declarations([cell.verb])  # type: ignore[arg-type]
        )
        for index in range(cell.examples_per_cell):
            example = synthesize_example(cell, index)
            prompt = build_prompt(example)
            key = compute_cache_key(PROMPT_VERSION, prompt["input_hash"])
            record = cache.get(key)
            if record is None:
                raw = backend.complete(prompt["system"], prompt["user"])
                cache.put(
                    key,
                    prompt_version=PROMPT_VERSION,
                    input_hash=prompt["input_hash"],
                    teacher_model_version=backend.teacher_model_version,
                    raw_response=raw,
                )
                record = cache.get(key)
                assert record is not None  # just written atomically
                misses += 1
            else:
                hits += 1

            try:
                parsed = parse_teacher_raw(record["raw_response"], cell.cell_id)
                validate_class_shape(parsed, cell)
            except CorpusError:
                # Format-validation failure (bad JSON shape OR class-rule
                # violation): COUNT it (smoke pass-rate metric), keep the
                # cached raw response, skip the row. Regeneration stays
                # deterministic: same cached raw => same rejection.
                rejected += 1
                ordinal += 1
                continue

            intent_calls: list[dict[str, Any]] = []
            for call_pos, call in enumerate(example.schema_calls):
                entry: dict[str, Any] = {"name": call["name"], "params": call["params"]}
                if example.derived_missing:
                    entry["missing_required"] = list(example.derived_missing[call_pos])
                if example.derived_slots:
                    entry["unresolved_slots"] = [
                        {"arg_name": s[0], "reference": s[1], "resource_type": s[2]}
                        for s in example.derived_slots[call_pos]
                    ]
                intent_calls.append(entry)

            record_id = _record_id(cell, index, ordinal)

            if verify_execution:
                exec_result = execution_verify_example(example, record_id=record_id)
                if exec_result.skipped:
                    execution_skipped += 1
                elif not exec_result.passed:
                    # Ground truth doesn't actually execute correctly against
                    # the P2.2 chatterbox harness (real tip/volume/grounding
                    # defect, not a teacher-shape issue): COUNT it, keep the
                    # cached raw response, skip the row. Deterministic same
                    # as the shape-rejection path above -- verification only
                    # depends on row content, nothing random.
                    rejected += 1
                    execution_rejected += 1
                    category = (exec_result.summary or {}).get("category") or "harness_internal"
                    execution_rejected_by_category[category] = (
                        execution_rejected_by_category.get(category, 0) + 1
                    )
                    ordinal += 1
                    continue
            else:
                exec_result = None

            row = {
                "record_id": record_id,
                "source": "synthetic",
                "provenance": prov,
                "matrix_cell": {
                    "cell_id": cell.cell_id,
                    "verb": cell.verb,
                    "ambiguity_class": cell.ambiguity_class,
                },
                "utterance": parsed["utterance"],
                "clarification": parsed["clarification"],
                "tools": tools_block,
                "structured_calls": [dict(c) for c in example.structured_calls],
                "intent": {
                    "calls": intent_calls,
                    "expected_effects": _expected_effects(example),
                },
                "supervision": {"kind": _supervision_kind(cell)},
            }
            if exec_result is not None and exec_result.summary is not None:
                row["execution_verify"] = exec_result.summary
            if example.repairs:
                # 0.2.1: only on rows the surface coercion changed; absent
                # otherwise so previously accepted rows stay byte-identical.
                row["synth_repairs"] = list(example.repairs)
            rows.append(row)
            ordinal += 1

    per_class: dict[str, int] = {}
    for row in rows:
        cls = row["matrix_cell"]["ambiguity_class"]
        per_class[cls] = per_class.get(cls, 0) + 1

    return rows, GenerationStats(
        examples_total=len(rows) + rejected,
        accepted=len(rows),
        rejected=rejected,
        cache_hits=hits,
        cache_misses=misses,
        per_class=per_class,
        teacher_model_version=backend.teacher_model_version,
        execution_rejected=execution_rejected,
        execution_rejected_by_category=execution_rejected_by_category,
        execution_skipped=execution_skipped,
    )


def build_manifest(matrix: AmbiguityMatrix, stats: GenerationStats, selected_cell_ids: list[str]) -> dict[str, Any]:
    return {
        "pipeline": "p23_coverage_floor",
        "generator_version": GENERATOR_VERSION,
        "prompt_version": PROMPT_VERSION,
        "matrix_version": MATRIX_VERSION,
        "plr_submodule_sha": PLR_SUBMODULE_SHA,
        "teacher_model_version": stats.teacher_model_version,
        "examples_total": stats.examples_total,
        "accepted": stats.accepted,
        "rejected": stats.rejected,
        "execution_rejected": stats.execution_rejected,
        "execution_rejected_by_category": stats.execution_rejected_by_category,
        "execution_skipped": stats.execution_skipped,
        "format_validation_pass_rate": round(stats.pass_rate, 4),
        "cache_hits": stats.cache_hits,
        "cache_misses": stats.cache_misses,
        "per_class": stats.per_class,
        "selected_cell_ids": selected_cell_ids,
        "value_format_conventions": VALUE_FORMAT_CONVENTIONS,
        "supervision_kinds": {"tool_call": SUPERVISION_TOOL_CALL, "nl_clarification": SUPERVISION_NL_CLARIFICATION},
    }


def write_outputs(
    out_dir: Path,
    rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    corpus_name: str = "corpus_p23_floor.jsonl",
    manifest_name: str = "manifest.json",
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = out_dir / corpus_name
    corpus_path.write_text(
        "".join(canonical_json(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest_path = out_dir / manifest_name
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return corpus_path, manifest_path
