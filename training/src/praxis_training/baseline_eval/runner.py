"""Baseline eval runner: recorded-artifacts mode + local inference lane.

TWO modes, one scoring path (P2.1 deliverable 2):

- **recorded-artifact mode** (`run_recorded`): reads a JSON file of
  pre-recorded raw model outputs keyed by record_id. Every report produced
  from this mode is LABELED as such -- it proves harness mechanics and lets
  recorded checkpoints be re-scored reproducibly; it is NOT live inference.
- **local inference mode** (`local_infer.make_generate` + `run_local`):
  transformers-based CPU/GPU generation for the real baseline
  (AC-2.1.x 'local CPU lane'). Import of transformers/torch is LAZY and
  confined to `local_infer.py` so the rest of the package stays light.

Recorded artifact JSON shape::

    {
      "artifact_kind": "praxis-recorded-model-outputs",
      "base_revision": "<model id>@<revision or sha>",
      "recorded_by": "who/what produced these strings",
      "outputs": [{"record_id": "...", "raw_output": "..."}, ...]
    }

`base_revision` is REQUIRED (R7: pin the base revision beside any recorded
outputs). A missing or placeholder base_revision is a hard error.

Since 260902 (`run_local(dump_outputs=...)`) the live lane WRITES this same
artifact beside its report, carrying `model_label` and the inference
`inputs` (device / dtype requested / dtype resolved / max_new_tokens /
split). A scorer change is then a pure `--recorded` re-score of the SAME
generations -- no inference, no numerics drift, every row auditable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from coxswain.plr.intent_record import IntentRecord

from .metrics import ScoredExample, build_report, score_all

__all__ = [
    "PairSet",
    "RecordedArtifact",
    "load_pair_set",
    "load_recorded_outputs",
    "read_recorded_artifact",
    "write_recorded_artifact",
    "run_recorded",
    "run_local",
    "GenerateFn",
]

GenerateFn = Callable[[Mapping[str, Any]], str]

RECORDED_KIND = "praxis-recorded-model-outputs"
_RECORDED_LABEL = (
    "RECORDED ARTIFACTS - NOT LIVE MODEL INFERENCE "
    "(mechanics proof / checkpoint re-scoring only)"
)
_LOCAL_LABEL = "LIVE LOCAL INFERENCE"


@dataclass(frozen=True)
class PairSet:
    """Native rows zipped with sidecar intent records, line-aligned."""

    pairs: list[dict]
    intents: list[IntentRecord]

    def filter_split(self, split: str) -> "PairSet":
        keep = [(p, i) for p, i in zip(self.pairs, self.intents) if p["metadata"] == split]
        return PairSet(pairs=[p for p, _ in keep], intents=[i for _, i in keep])


def load_pair_set(pairs_path: Path, sidecar_path: Path) -> PairSet:
    pairs = _read_jsonl(pairs_path)
    sidecars = _read_jsonl(sidecar_path)
    if len(pairs) != len(sidecars):
        raise ValueError(
            f"pair/sidecar line count mismatch: {len(pairs)} vs {len(sidecars)}"
        )
    intents: list[IntentRecord] = []
    for idx, (row, sc) in enumerate(zip(pairs, sidecars)):
        # Line-alignment contract: same record identity on both sides.
        utterance = next(
            m["content"] for m in row["messages"] if m["role"] == "user"
        )
        if utterance != sc["utterance"]:
            raise ValueError(
                f"line {idx}: sidecar utterance != pairs user message "
                f"({sc['utterance']!r} vs {utterance!r})"
            )
        intents.append(sc)
    return PairSet(pairs=pairs, intents=intents)


@dataclass(frozen=True)
class RecordedArtifact:
    """A validated recorded-outputs artifact (see module docstring)."""

    outputs: dict[str, str]
    base_revision: str
    recorded_by: str | None = None
    model_label: str | None = None
    inputs: dict[str, Any] = field(default_factory=dict)


def read_recorded_artifact(path: Path) -> RecordedArtifact:
    """Parse + validate a recorded-outputs JSON, metadata included."""
    blob = json.loads(path.read_text(encoding="utf-8"))
    if blob.get("artifact_kind") != RECORDED_KIND:
        raise ValueError(
            f"{path}: expected artifact_kind={RECORDED_KIND!r}, got {blob.get('artifact_kind')!r}"
        )
    base = blob.get("base_revision")
    if not base or not isinstance(base, str) or base.strip().lower() in ("unknown", "todo", ""):
        raise ValueError(
            f"{path}: base_revision missing/placeholder - R7 requires the base "
            "revision pinned beside any recorded outputs"
        )
    outputs: dict[str, str] = {}
    for entry in blob.get("outputs", []):
        rid = entry.get("record_id")
        if not rid:
            raise ValueError(f"{path}: output entry without record_id")
        if rid in outputs:
            raise ValueError(f"{path}: duplicate record_id {rid!r}")
        outputs[rid] = entry.get("raw_output", "")
    inputs = blob.get("inputs") or {}
    return RecordedArtifact(
        outputs=outputs,
        base_revision=base,
        recorded_by=blob.get("recorded_by"),
        model_label=blob.get("model_label"),
        inputs=dict(inputs) if isinstance(inputs, Mapping) else {},
    )


def load_recorded_outputs(path: Path) -> tuple[dict[str, str], str]:
    """Parse + validate a recorded-outputs JSON. Returns ({id: raw}, base_rev)."""
    art = read_recorded_artifact(path)
    return art.outputs, art.base_revision


def write_recorded_artifact(
    path: Path,
    outputs: Mapping[str, str],
    *,
    base_revision: str,
    recorded_by: str,
    model_label: str | None,
    inputs: Mapping[str, Any],
) -> None:
    """Write the recorded-outputs artifact in the shape `read_recorded_artifact`
    accepts (round-trip guaranteed by test_runner_modes)."""
    blob = {
        "artifact_kind": RECORDED_KIND,
        "base_revision": base_revision,
        "recorded_by": recorded_by,
        "model_label": model_label,
        "inputs": dict(inputs),
        "outputs": [{"record_id": rid, "raw_output": raw} for rid, raw in outputs.items()],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(blob, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_recorded(
    pair_set: PairSet,
    recorded_path: Path,
    out_path: Path | None = None,
    split: str | None = None,
    allow_partial: bool = False,
    model_label: str | None = None,
) -> dict[str, Any]:
    """Score pre-recorded outputs; report clearly labeled as recorded.

    Full coverage of the selected split is REQUIRED by default (a real
    checkpoint re-score must see every example). ``allow_partial=True``
    scores the recorded/scope INTERSECTION instead -- for tiny hand-made
    mechanics-proof fixtures -- and the report is labeled PARTIAL.
    ``model_label`` defaults to the label stored in the artifact (the dump
    written by :func:`run_local`), so a re-score still names its weights.
    """
    selected = pair_set.filter_split(split) if split else pair_set
    art = read_recorded_artifact(recorded_path)
    outputs, base = art.outputs, art.base_revision

    ids = [intent["record_id"] for intent in selected.intents]
    missing = [rid for rid in ids if rid not in outputs]
    extra = sorted(set(outputs) - set(ids))
    if missing and not allow_partial:
        raise ValueError(
            f"recorded outputs missing {len(missing)} in-scope record_ids "
            f"(first few: {missing[:5]}); pass --allow-partial "
            "only for hand-made mechanics fixtures"
        )

    intents_by_id = {i["record_id"]: i for i in selected.intents}
    scored_ids = [rid for rid in ids if rid in outputs]
    scored = score_all(
        {rid: outputs[rid] for rid in scored_ids},
        [intents_by_id[rid] for rid in scored_ids],
    )
    label = _RECORDED_LABEL
    if allow_partial:
        label += " - PARTIAL COVERAGE (mechanics-proof subset, NOT split-representative)"
    report = build_report(
        scored,
        mode="recorded_artifacts",
        base_revision=base,
        inputs={
            "recorded_outputs": str(recorded_path),
            "recorded_inputs": art.inputs,
            "split": split or "all",
            "extra_record_ids_ignored": extra,
            "coverage": {
                "in_scope": len(ids),
                "recorded": len(outputs),
                "scored": len(scored_ids),
            },
        },
        labeled_as=label,
        model_label=model_label if model_label is not None else art.model_label,
    )
    return report


def run_local(
    pair_set: PairSet,
    model_id: str,
    *,
    revision: str = "main",
    device: str = "cpu",
    dtype: str | None = None,
    max_new_tokens: int = 128,
    out_path: Path | None = None,
    split: str | None = None,
    generate_fn: GenerateFn | None = None,
    model_label: str | None = None,
    dump_outputs: Path | None = None,
) -> dict[str, Any]:
    """Live local inference over the selected split (AC-2.1.x CPU lane).

    ``generate_fn`` injectable for tests; when omitted, built from
    transformers via :mod:`.local_infer` (lazy heavy imports).
    ``dump_outputs`` persists every raw generation as a recorded-outputs
    artifact so the run can be re-scored without inference.
    """
    if generate_fn is None:
        from .local_infer import make_generate  # lazy: keeps torch off default path

        gen = make_generate(
            model_id=model_id, revision=revision, device=device, dtype=dtype,
            max_new_tokens=max_new_tokens,
        )
    else:
        gen = generate_fn

    selected = pair_set.filter_split(split) if split else pair_set
    outputs: dict[str, str] = {}
    for row, intent in zip(selected.pairs, selected.intents):
        outputs[intent["record_id"]] = gen(row)

    base_revision = f"{model_id}@{revision}"
    inputs: dict[str, Any] = {
        "device": device,
        "dtype": dtype or "model-default",
        "dtype_resolved": getattr(gen, "resolved_dtype", None),
        "split": split or "all",
        "max_new_tokens": max_new_tokens,
    }
    if dump_outputs is not None:
        write_recorded_artifact(
            dump_outputs,
            outputs,
            base_revision=base_revision,
            recorded_by="praxis_training.baseline_eval.runner.run_local",
            model_label=model_label,
            inputs=inputs,
        )
        inputs["dump_outputs"] = str(dump_outputs)

    scored: list[ScoredExample] = score_all(outputs, selected.intents)
    return build_report(
        scored,
        mode="local_inference",
        base_revision=base_revision,
        inputs=inputs,
        labeled_as=_LOCAL_LABEL,
        model_label=model_label,
    )


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{idx + 1}: invalid JSON ({exc})") from exc
    return rows
