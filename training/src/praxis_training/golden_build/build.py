"""Deterministic golden-set generator -> training/golden/ (P2.1 deliverable 1).

Emits THREE artifacts, byte-stable across runs (no timestamps inside the pair
files; the manifest carries environment provenance instead):

- ``golden_pairs.jsonl``         FunctionGemma-native rows
                                 ``{metadata, tools[], messages[]}`` -- the
                                 EXACT trainer/serving surface (research §2a,
                                 D6). Extra keys are deliberately absent so
                                 strict loaders never choke.
- ``golden_intent_sidecar.jsonl`` parallel normalized intent records
                                 (coxswain.plr.intent_record shape) with gap
                                 fields DERIVED via slot_derivation and
                                 ``provenance: "golden"``; line N pairs with
                                 line N of the pairs file.
- ``manifest.json``              counts by tool/class/split, scaffold version,
                                 PLR submodule SHA keying (D9), juror-finding
                                 assertions evidence.

Pair-side linkage test (tests/test_golden_consistency.py) asserts sidecar row
N's utterance equals pairs row N's user message.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from coxswain.plr.slot_derivation import derive_call_gaps

from .corpus import (
    DEVELOPER_SCAFFOLD,
    AmbiguityClass,
    CLARIFY_PER_CLASS,
    GoldenExample,
    POSITIVES_PER_TOOL,
    build_corpus,
    tool_declarations,
)

__all__ = ["GOLDEN_DIR", "build_all", "render_native_row", "render_sidecar_row", "main"]

GOLDEN_DIR = Path(__file__).resolve().parents[3] / "golden"
PAIRS_NAME = "golden_pairs.jsonl"
SIDECAR_NAME = "golden_intent_sidecar.jsonl"
MANIFEST_NAME = "manifest.json"

_SCAFFOLD_VERSION = "functiongemma-native/research-s2a-developer-scaffold/no-date-injection(D6-rev2)"


def render_native_row(ex: GoldenExample, tools: list[dict]) -> dict:
    """One FunctionGemma-native training/eval row. Keys EXACTLY
    {metadata, tools, messages}."""
    messages: list[dict] = [
        {"role": "developer", "content": DEVELOPER_SCAFFOLD},
        {"role": "user", "content": ex.utterance},
    ]
    if ex.ambiguity_class == AmbiguityClass.OUT_OF_SURFACE:
        # D7: NL clarification turn, NO tool_calls key at all.
        messages.append({"role": "assistant", "content": ex.assistant_text})
    else:
        messages.append({
            "role": "assistant",
            "tool_calls": [
                {
                    "type": "function",
                    "function": {"name": c.name, "arguments": c.params},
                }
                for c in ex.calls
            ],
        })
    return {"metadata": ex.split, "tools": tools, "messages": messages}


def render_sidecar_row(ex: GoldenExample) -> dict:
    """Normalized intent record (IntentRecord shape) + routing metadata.

    Gap fields are ALWAYS derived here from the canonical tables (D11) --
    authored annotations would be exactly the 'model-predicted slots' trap
    D11 forbids. Juror finding enforced downstream by _assert_sidecar_gaps.
    """
    calls: list[dict] = []
    for c in ex.calls:
        gaps = derive_call_gaps(c.name, c.params)
        call: dict = {"name": c.name, "params": c.params}
        if gaps.missing_required:
            call["missing_required"] = list(gaps.missing_required)
        if gaps.unresolved_slots:
            call["unresolved_slots"] = [
                {
                    "arg_name": s.arg_name,
                    "reference": s.reference,
                    "resource_type": s.resource_type,
                }
                for s in gaps.unresolved_slots
            ]
        calls.append(call)
    return {
        # IntentRecord fields (coxswain.plr.intent_record):
        "record_id": ex.record_id,
        "utterance": ex.utterance,
        "source": "golden",
        "calls": calls,
        "expected_effects": [],  # P2.2 tracker owns effect verification.
        # Harness-routing metadata (additive, outside the IntentRecord keys):
        "split": ex.split,
        "ambiguity_class": ex.ambiguity_class,
        "provenance": "golden",
        "authoring_note": ex.note,
    }


def _assert_sidecar_gaps(sidecars: list[dict]) -> None:
    """Juror route-in finding: clarify examples must carry NON-EMPTY expected
    gap fields. Empty here meant cue-1/cue-2 had nothing to score against."""
    for row in sidecars:
        cls = row["ambiguity_class"]
        for call in row["calls"]:
            has_gaps = bool(call.get("missing_required") or call.get("unresolved_slots"))
            if cls == AmbiguityClass.MISSING_SLOT and not call.get("missing_required"):
                raise AssertionError(f"{row['record_id']}: missing-slot row lacks missing_required")
            if cls == AmbiguityClass.AMBIGUOUS_REFERENT and not call.get("unresolved_slots"):
                raise AssertionError(f"{row['record_id']}: ambiguous-referent row lacks unresolved_slots")
            if cls in (AmbiguityClass.MISSING_SLOT, AmbiguityClass.AMBIGUOUS_REFERENT) and not has_gaps:
                raise AssertionError(f"{row['record_id']}: clarify row has EMPTY gap fields")
            if cls == AmbiguityClass.CLEAN_PARSE and call.get("missing_required"):
                raise AssertionError(
                    f"{row['record_id']}: clean-parse row unexpectedly missing {call['missing_required']}"
                )
            # Clean-parse rows MAY carry derived unresolved_slots: concrete
            # string references still ground at dispatch (FR-7). Only a
            # missing required param would disqualify 'clean'.


def _plr_source_sha() -> str:
    """D9 keying: record the vendored PLR submodule SHA beside the artifacts
    (golden is human-authored/exempt from regeneration, but the environment
    it was reviewed against is part of provenance)."""
    try:
        out = subprocess.run(
            ["git", "-C", "external/pylabrobot", "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        )
        return out.stdout.strip()
    except Exception as exc:  # pragma: no cover - only when run outside repo
        return f"unavailable ({exc})"


def _counts(corpus: list[GoldenExample]) -> dict:
    by_split: dict[str, int] = {"train": 0, "eval": 0}
    by_class: dict[str, int] = {}
    by_class_split: dict[str, dict[str, int]] = {}
    per_tool_train: dict[str, int] = {}
    per_tool_eval: dict[str, int] = {}
    for ex in corpus:
        by_split[ex.split] += 1
        by_class[ex.ambiguity_class] = by_class.get(ex.ambiguity_class, 0) + 1
        bucket = by_class_split.setdefault(ex.ambiguity_class, {"train": 0, "eval": 0})
        bucket[ex.split] += 1
        for c in ex.calls:
            target = per_tool_train if ex.split == "train" else per_tool_eval
            target[c.name] = target.get(c.name, 0) + 1
    return {
        "total_rows": len(corpus),
        "by_split": by_split,
        "by_ambiguity_class": by_class,
        "by_class_and_split": by_class_split,
        "calls_per_tool_train": per_tool_train,
        "calls_per_tool_eval": per_tool_eval,
        "eval_clarify_total": by_class_split.get(AmbiguityClass.MISSING_SLOT, {}).get("eval", 0)
        + by_class_split.get(AmbiguityClass.AMBIGUOUS_REFERENT, {}).get("eval", 0)
        + by_class_split.get(AmbiguityClass.OUT_OF_SURFACE, {}).get("eval", 0),
    }


def build_all(out_dir: Path | None = None) -> dict:
    """Generate all three golden artifacts. Returns the manifest written."""
    out_dir = out_dir or GOLDEN_DIR
    corpus = build_corpus()
    tools = tool_declarations()
    sidecars = [render_sidecar_row(ex) for ex in corpus]
    _assert_sidecar_gaps(sidecars)

    out_dir.mkdir(parents=True, exist_ok=True)
    pairs_path = out_dir / PAIRS_NAME
    sidecar_path = out_dir / SIDECAR_NAME

    with pairs_path.open("w", encoding="utf-8") as f:
        for ex in corpus:
            f.write(json.dumps(render_native_row(ex, tools), ensure_ascii=False) + "\n")
    with sidecar_path.open("w", encoding="utf-8") as f:
        for row in sidecars:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "artifact": "praxis-copilot-golden-pair-set",
        "version": 1,
        "provenance": "human-authored golden corpus (D9 regeneration-exempt); "
                      "generator re-derives byte-for-byte for drift detection",
        "scaffold": _SCAFFOLD_VERSION,
        "developer_content_verbatim": DEVELOPER_SCAFFOLD,
        "plr_source_sha": _plr_source_sha(),
        "phase2_tool_count": len(tools),
        "sizing_rule": {
            "positives_per_tool": POSITIVES_PER_TOOL,
            "clarify_per_class": CLARIFY_PER_CLASS,
            "clarify_classes": list(AmbiguityClass.CLARIFY),
            "clarify_split_policy": "all eval (held-out) per D8 >=30 held-out sizing; "
                                    "train negative mixing is P2.5 assembly's job",
        },
        "counts": _counts(corpus),
        "gap_fields_policy": "missing_required/unresolved_slots derived deterministically "
                             "via coxswain.plr.slot_derivation (D11); NEVER authored or "
                             "model-predicted",
        "pair_linkage": "sidecar line N <-> pairs line N; utterance equality asserted in tests",
    }
    (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:  # pragma: no cover - CLI convenience
    manifest = build_all()
    print(json.dumps(manifest["counts"], indent=2))
    print(f"wrote {GOLDEN_DIR / PAIRS_NAME}")
    print(f"wrote {GOLDEN_DIR / SIDECAR_NAME}")
    print(f"wrote {GOLDEN_DIR / MANIFEST_NAME}")


if __name__ == "__main__":  # pragma: no cover
    main()
