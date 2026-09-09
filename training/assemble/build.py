"""P2.5 deterministic corpus assembly core (backlog 480).

Pure function of three committed input files + this package's constants:
same inputs => identical output bytes (D9/R4; upstream teacher outputs are
cached content-addressed, so regeneration never re-calls a teacher and never
drifts). No timestamps enter any artifact byte -- see
``developer_scaffold_template.txt`` for the recorded no-date-injection
decision (D6-rev2).

Inputs (all landed + jury-cleared before this item):

- golden   P2.1 ``training/golden/golden_pairs.jsonl`` (+ intent sidecar)
- coverage P2.3 ``training/out/corpus_p23_smoke.jsonl``
- naturalness P2.4 ``training/overlay_gen/out/overlay_smoke.jsonl``

Output contract per deliverable 1/2: ONE FunctionGemma-native JSONL whose
rows carry EXACTLY ``{metadata, tools, messages}``; ``metadata`` is the FINAL
assembled split assigned here (the normalization deliverable), all
golden-provenance rows land in eval, train/eval disjoint by construction.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from coxswain.plr.param_namespace import params_of
from coxswain.plr.slot_derivation import derive_call_gaps
from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES
from floor_gen.matrix import committed_matrix_path, load_matrix
from overlay_gen.normalize import normalize_utterance
from praxis_training.golden_build.corpus import (
    DECLARED_ARRAY_PARAMS,
    DEVELOPER_SCAFFOLD,
)

from assemble.pin import PIN_REL, load_pin, native_digest

from .scaffold import (
    SCAFFOLD_TEMPLATE_NAME,
    SCAFFOLD_VERSION,
    scaffold_template_bytes,
    scaffold_template_text,
)

__all__ = [
    "ASSEMBLY_VERSION",
    "CLASS_MAP",
    "CLARIFY_CLASSES",
    "CORPUS_NAME",
    "EVAL_FRACTION",
    "MANIFEST_NAME",
    "SIDECAR_NAME",
    "PROBE_CORPUS_NAME",
    "PROBE_SIDECAR_NAME",
    "NEAR_PROBE_CORPUS_NAME",
    "NEAR_PROBE_SIDECAR_NAME",
    "NEAR_PROBE_INDEX_MIN",
    "NATURAL_CORPUS_REL",
    "TARGET_EXAMPLES",
    "build_artifacts",
    "main",
]

#: Bump on ANY change to assembly logic / split rule / validation policy.
#: 0.1.3 (260902): gap fields (missing_required / unresolved_slots) are DERIVED
#: for every call from the params as written (sorted keys), never copied; a
#: source annotation that disagrees is a loud AssertionError. Before, golden
#: rows lost their annotation entirely and floor rows kept an authored slot
#: order that disagreed with the sorted-key params (task 260902_p26_rescore).
#: 0.1.4 (260902, task 260902_p26b_surface_data): the eval split is PINNED
#: (training/assemble/data/eval_split_pin.json, record_id + native-row digest)
#: instead of re-cut by the stratum rule; new inputs can only add TRAIN rows.
#: The natural-phrasing floor lane (provenance coverage_natural) joins train
#: when its base row is train, and forms the separate PROBE set when its base
#: row is eval (never the 228). Repaired floor rows (synth 0.2.1) are train-only.
#: 0.1.5 (260903, task 260903_p26c_oos_natural): the natural lane also covers
#: out-of-surface floor rows (supervision nl_clarification, the base row's
#: clarification copied verbatim as the assistant text); same routing (eval
#: base -> probe, so the probe gains an out_of_surface class). Pin unchanged.
#: 0.1.6 (260903, task 260903_p26d_near_surface): matrix v3 appends six
#: near-surface out-of-surface cells (record ordinals >= 685). Their rows are
#: coverage rows outside the pin -> train, EXCEPT example indices >= 16 (the
#: k = floor(0.2*20) = 4 hold-out the pre-freeze rule would have cut), which
#: form the separate NEAR-SURFACE PROBE (corpus_p25_probe_near*.jsonl): never
#: train, never the 228. Pin unchanged.
ASSEMBLY_VERSION = "0.1.6"
GAP_FIELDS_RULE = (
    "missing_required and unresolved_slots derived per call via "
    "coxswain.plr.slot_derivation.derive_call_gaps(name, params with sorted keys); "
    "source annotations checked as sets (missing_required) / multisets (unresolved_slots)"
)

TRAINING_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TRAINING_DIR.parent

GOLDEN_PAIRS_REL = "training/golden/golden_pairs.jsonl"
GOLDEN_SIDECAR_REL = "training/golden/golden_intent_sidecar.jsonl"
FLOOR_CORPUS_REL = "training/out/corpus_p23_floor.jsonl"
NATURAL_CORPUS_REL = "training/out/corpus_p23_floor_natural.jsonl"
OVERLAY_CORPUS_REL = "training/overlay_gen/out/overlay_full.jsonl"

CORPUS_NAME = "corpus_p25.jsonl"
SIDECAR_NAME = "corpus_p25_sidecar.jsonl"
MANIFEST_NAME = "manifest.json"
PROBE_CORPUS_NAME = "corpus_p25_probe.jsonl"
PROBE_SIDECAR_NAME = "corpus_p25_probe_sidecar.jsonl"
NEAR_PROBE_CORPUS_NAME = "corpus_p25_probe_near.jsonl"
NEAR_PROBE_SIDECAR_NAME = "corpus_p25_probe_near_sidecar.jsonl"
#: 0.1.6: example index (last record_id field) from which an APPENDED matrix
#: cell's rows go to the near-surface probe instead of train.
NEAR_PROBE_INDEX_MIN = 16
#: Train rows whose normalized utterance equals an eval row's, as measured at
#: the pin (assembly 0.1.3). Pre-existing (missing-slot cells collapse to
#: "Move to reservoir_1"); 0.1.4 must not grow it.
CROSS_SPLIT_DUPLICATES_AT_PIN = 41

#: Floor-generator class vocabulary -> canonical golden/AmbiguityClass names.
CLASS_MAP: dict[str, str] = {
    "none": "clean_parse",
    "missing-slot": "missing_slot",
    "ambiguous-referent": "ambiguous_referent",
    "out-of-surface": "out_of_surface",
}
CANONICAL_CLASSES: tuple[str, ...] = (
    "clean_parse",
    "missing_slot",
    "ambiguous_referent",
    "out_of_surface",
)
CLARIFY_CLASSES: tuple[str, ...] = ("missing_slot", "ambiguous_referent", "out_of_surface")

#: Held-out fraction per synthetic (provenance x class x verb) stratum.
EVAL_FRACTION = 0.2
#: Strata smaller than this stay ALL-train (D7 negative-mixing priority).
MIN_STRATUM_FOR_EVAL = 4

#: P2.5 target from the task line; shortfall is RECORDED, never padded.
TARGET_EXAMPLES = 1000
SHORTFALL_REASON = (
    "Inputs are the full-scale P2.3 floor sweep (43-cell matrix v2) and the "
    "full P2.4 overlay pass over every mined source; the remaining gap to "
    "1000 is bounded by matrix size x examples_per_cell and by the 37 unique "
    "mined canonicals, not by a pending run. Assembly merges what exists "
    "verbatim and pads nothing."
)

#: Literal params that MUST arrive numeric when present (golden-builder rule).
_NUMERIC_LITERAL_PARAMS = frozenset({
    "volume_ul", "wavelength_nm", "excitation_nm", "emission_nm", "focal_height_mm",
})

THRESHOLDS_DOC_REL = ".praxia/docs/specs/260825_p25_provisional_thresholds.md"


# ---------------------------------------------------------------------------
# small utils
# ---------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json(obj: Any) -> str:
    """Byte-stable serialization (sorted keys, compact, ASCII-escaped)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def plr_source_sha() -> str:
    """Vendored pylabrobot submodule HEAD (D9 corpus key)."""
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "submodule", "status", "external/pylabrobot"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    token = out.split()[0]
    return token[1:] if token[0] in "+-U" else token


# ---------------------------------------------------------------------------
# loaders -> normalized intermediate records
# ---------------------------------------------------------------------------
# Record shape (dict):
#   record_id, provenance, ambiguity_class, verb, utterance,
#   calls: [{name, params}], assistant_text: str|None, supervision_kind,
#   lineage: {...}   (everything traceability wants, kept out of native rows)

def load_golden() -> list[dict[str, Any]]:
    pairs_path = REPO_ROOT / GOLDEN_PAIRS_REL
    sidecar_path = REPO_ROOT / GOLDEN_SIDECAR_REL
    pairs = _read_jsonl(pairs_path)
    sidecars = _read_jsonl(sidecar_path)
    if len(pairs) != len(sidecars):
        raise AssertionError("golden pairs/sidecar length mismatch")
    records: list[dict[str, Any]] = []
    for n, (row, sc) in enumerate(zip(pairs, sidecars)):
        if sorted(row.keys()) != ["messages", "metadata", "tools"]:
            raise AssertionError(f"golden line {n}: unexpected native keys {sorted(row.keys())}")
        msgs = row["messages"]
        utterance = msgs[1]["content"]
        if utterance != sc["utterance"]:
            raise AssertionError(f"golden line {n}: pair/sidecar utterance linkage broken")
        tool_call_msgs = [m for m in msgs if m["role"] == "assistant" and "tool_calls" in m]
        calls = [
            {"name": tc["function"]["name"], "params": dict(tc["function"]["arguments"])}
            for m in tool_call_msgs
            for tc in m["tool_calls"]
        ]
        # Carry the golden sidecar's own gap annotation onto the call so
        # validate_and_normalize can CHECK it against the derivation (before
        # 0.1.3 it was parked under lineage.gap_fields and the assembled
        # sidecar shipped without it -- the gold_slot_annotation defect).
        for k, sc_call in enumerate(sc.get("calls") or []):
            if k < len(calls):
                for key in ("missing_required", "unresolved_slots"):
                    if key in sc_call:
                        calls[k][key] = sc_call[key]
        assistant_text = next(
            (m["content"] for m in msgs if m["role"] == "assistant" and "tool_calls" not in m),
            None,
        )
        cls = sc["ambiguity_class"]
        records.append({
            "record_id": sc["record_id"],
            "provenance": "golden",
            "ambiguity_class": cls,
            "verb": calls[0]["name"] if calls else "",
            "utterance": utterance,
            "calls": calls,
            "assistant_text": assistant_text,
            "supervision_kind": "nl_clarification" if assistant_text is not None else "tool_call",
            "lineage": {
                "pairs_file": GOLDEN_PAIRS_REL,
                "sidecar_file": GOLDEN_SIDECAR_REL,
                "pair_line": n,
                "golden_internal_split": row["metadata"],
                "sidecar_split_tag": sc.get("split"),
                "authoring_note": sc.get("authoring_note", ""),
                "gap_fields": sc.get("calls"),
            },
        })
    return records


def load_floor() -> list[dict[str, Any]]:
    path = REPO_ROOT / FLOOR_CORPUS_REL
    records: list[dict[str, Any]] = []
    for row in _read_jsonl(path):
        cell = row["matrix_cell"]
        prov = row["provenance"]
        clarification = row.get("clarification")
        kind = row["supervision"]["kind"]
        calls = []
        for c in row["intent"]["calls"]:
            entry: dict[str, Any] = {"name": c["name"], "params": dict(c.get("params", {}))}
            if c.get("missing_required"):
                entry["missing_required"] = list(c["missing_required"])
            if c.get("unresolved_slots"):
                entry["unresolved_slots"] = c["unresolved_slots"]
            calls.append(entry)
        if cell["ambiguity_class"] not in CLASS_MAP:
            raise AssertionError(f"{row['record_id']}: unmapped floor class {cell['ambiguity_class']!r}")
        if (kind == "nl_clarification") != (clarification is not None):
            raise AssertionError(f"{row['record_id']}: supervision kind vs clarification mismatch")
        records.append({
            "record_id": row["record_id"],
            "provenance": prov["provenance"],  # "coverage"
            "ambiguity_class": CLASS_MAP[cell["ambiguity_class"]],
            "verb": cell["verb"],
            "utterance": row["utterance"],
            "calls": calls,
            "assistant_text": clarification,
            "supervision_kind": kind,
            "lineage": {
                "source_file": FLOOR_CORPUS_REL,
                "cell_id": cell["cell_id"],
                "matrix_ambiguity_class": cell["ambiguity_class"],
                "matrix_version": prov.get("matrix_version"),
                "generator_version": prov["generator_version"],
                "prompt_version": prov["prompt_version"],
                "teacher_model_version": prov["teacher_model_version"],
                "gap_fields": calls,
            },
        })
    return records


def load_natural() -> list[dict[str, Any]]:
    """Natural-phrasing floor variants (floor_gen/natural.py). Same intent as
    the base row (out-of-surface rows: no calls, the base clarification as the
    assistant text); provenance coverage_natural; lineage carries
    base_record_id so assign_splits can route the variant by its base's split.
    """
    path = REPO_ROOT / NATURAL_CORPUS_REL
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for row in _read_jsonl(path):
        cell = row["matrix_cell"]
        prov = row["provenance"]
        if prov.get("provenance") != "coverage_natural":
            raise AssertionError(f"{row['record_id']}: natural corpus row with provenance {prov!r}")
        kind = row["supervision"]["kind"]
        clarification = row.get("clarification")
        calls = [{"name": c["name"], "params": dict(c.get("params", {}))} for c in row["intent"]["calls"]]
        oos = cell["ambiguity_class"] == "out-of-surface"
        if oos != (kind == "nl_clarification") or oos != (clarification is not None) or (oos and calls):
            raise AssertionError(
                f"{row['record_id']}: natural row shape mismatch (class {cell['ambiguity_class']!r}, "
                f"kind {kind!r}, clarification {'set' if clarification is not None else 'null'}, {len(calls)} calls)"
            )
        records.append({
            "record_id": row["record_id"],
            "provenance": "coverage_natural",
            "ambiguity_class": CLASS_MAP[cell["ambiguity_class"]],
            "verb": cell["verb"],
            "utterance": row["utterance"],
            "calls": calls,
            "assistant_text": clarification,
            "supervision_kind": kind,
            "lineage": {
                "source_file": NATURAL_CORPUS_REL,
                "base_record_id": row["lineage"]["base_record_id"],
                "surface": "natural",
                "cell_id": cell["cell_id"],
                "matrix_ambiguity_class": cell["ambiguity_class"],
                "generator_version": prov["generator_version"],
                "prompt_version": prov["prompt_version"],
                "teacher_model_version": prov["teacher_model_version"],
                "gap_fields": calls,
            },
        })
    return records


def load_overlay() -> list[dict[str, Any]]:
    path = REPO_ROOT / OVERLAY_CORPUS_REL
    records: list[dict[str, Any]] = []
    for row in _read_jsonl(path):
        prov = row["provenance"]
        call = row["call"]
        records.append({
            "record_id": row["id"],
            "provenance": prov["provenance"],  # "naturalness"
            "ambiguity_class": "clean_parse",
            "verb": call["name"],
            "utterance": row["instruction"],
            "calls": [{"name": call["name"], "params": dict(call.get("params", {}))}],
            "assistant_text": None,
            "supervision_kind": "tool_call",
            "lineage": {
                "source_file": OVERLAY_CORPUS_REL,
                "origin": prov.get("origin"),
                "source_notebook_or_protocol": prov.get("source_notebook_or_protocol"),
                "receiver_type": call.get("receiver_type"),
                "generator_version": prov["generator_version"],
                "prompt_version": prov["prompt_version"],
                "teacher_model_version": prov["teacher_model_version"],
                "gap_fields": [],
            },
        })
    return records


# ---------------------------------------------------------------------------
# validation + normalization (uniform gate over EVERY provenance)
# ---------------------------------------------------------------------------

def validate_and_normalize(record: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Returns (normalized_calls, exclusion_reasons). Non-empty reasons => the
    RECORD is excluded whole: a half-supervised utterance would be junk, and
    this corpus pads with nothing.
    """
    rid = record["record_id"]
    reasons: list[str] = []
    normalized: list[dict[str, Any]] = []
    for call in record["calls"]:
        name = call["name"]
        if name not in PHASE2_TOOL_NAMES:
            reasons.append(f"{rid}: call {name!r} outside PHASE2_TOOL_NAMES surface")
            continue
        known = {spec.name for spec in params_of(name)}
        params: dict[str, Any] = {}
        bad_call = False
        for pname, value in call["params"].items():
            if pname not in known:
                reasons.append(f"{rid}: {name}.{pname} outside canonical namespace")
                bad_call = True
                continue
            spec = next(s for s in params_of(name) if s.name == pname)
            is_array_param = (name, pname) in DECLARED_ARRAY_PARAMS
            if is_array_param:
                if not (isinstance(value, list) and value):
                    reasons.append(f"{rid}: {name}.{pname} declared ARRAY got non-list/empty")
                    bad_call = True
                    continue
                params[pname] = value
            elif isinstance(value, list):
                if len(value) == 1:
                    params[pname] = value[0]  # lossless unwrap to declared scalar
                else:
                    reasons.append(
                        f"{rid}: {name}.{pname} multi-value {value!r} inexpressible in "
                        f"declared scalar surface (dispatcher wraps scalar->[v])"
                    )
                    bad_call = True
                    continue
            else:
                if pname in _NUMERIC_LITERAL_PARAMS and (
                    isinstance(value, bool) or not isinstance(value, (int, float))
                ):
                    reasons.append(f"{rid}: {name}.{pname} must be numeric, got {value!r}")
                    bad_call = True
                    continue
                params[pname] = value
        if not bad_call:
            entry: dict[str, Any] = {"name": name, "params": params}
            gaps = derive_call_gaps(name, dict(sorted(params.items())))
            derived_missing = list(gaps.missing_required)
            derived_slots = [
                {"arg_name": s.arg_name, "reference": s.reference, "resource_type": s.resource_type}
                for s in gaps.unresolved_slots
            ]
            # Loud gate: a source annotation may only differ from the
            # derivation in order (slots) -- never in content.
            if "missing_required" in call and set(call["missing_required"]) != set(derived_missing):
                raise AssertionError(
                    f"{rid}: {name} missing_required annotation {call['missing_required']!r} "
                    f"!= derived {derived_missing!r}"
                )
            if "unresolved_slots" in call:
                src = Counter(_canonical_json(x) for x in call["unresolved_slots"])
                if src != Counter(_canonical_json(x) for x in derived_slots):
                    raise AssertionError(
                        f"{rid}: {name} unresolved_slots annotation {call['unresolved_slots']!r} "
                        f"!= derived {derived_slots!r}"
                    )
            entry["missing_required"] = derived_missing
            entry["unresolved_slots"] = derived_slots
            normalized.append(entry)
    return normalized, reasons


# ---------------------------------------------------------------------------
# split assignment (disjoint BY CONSTRUCTION)
# ---------------------------------------------------------------------------

def appended_matrix_cells() -> dict[str, str]:
    """cell_id -> matrix revision for every cell APPENDED after the pin (0.1.6)."""
    return {c.cell_id: c.appended_in_matrix_version for c in load_matrix(committed_matrix_path()).cells if c.appended_in_matrix_version}


def _floor_example_index(record_id: str) -> int:
    return int(record_id.rsplit("-", 1)[1])


def assign_splits_pinned(records: list[dict[str, Any]], pin: dict[str, Any]) -> dict[str, set[str]]:
    """0.1.4: eval == the pinned record_ids EXACTLY (loud if one is missing or
    excluded); golden must all be pinned; natural variants follow their base
    row (eval base -> probe, never eval); 0.1.6: rows of APPENDED matrix cells
    with example index >= NEAR_PROBE_INDEX_MIN -> probe_near; everything else
    -> train.
    """
    pinned = set(pin["rows"])
    appended = appended_matrix_cells()
    present = {r["record_id"] for r in records}
    missing = sorted(pinned - present)
    if missing:
        raise AssertionError(f"pinned eval rows missing/excluded from assembly: {missing[:5]} (+{max(0, len(missing) - 5)})")
    by_split: dict[str, set[str]] = {"train": set(), "eval": set(), "probe": set(), "probe_near": set()}
    for r in records:
        rid = r["record_id"]
        if r["provenance"] == "coverage" and r["lineage"]["cell_id"] in appended:
            if rid in pinned:
                raise AssertionError(f"{rid}: appended-cell row cannot be in the eval pin")
            by_split["probe_near" if _floor_example_index(rid) >= NEAR_PROBE_INDEX_MIN else "train"].add(rid)
        elif r["provenance"] == "golden":
            if rid not in pinned:
                raise AssertionError(f"golden row {rid} is not in the eval pin")
            by_split["eval"].add(rid)
        elif rid in pinned:
            by_split["eval"].add(rid)
        elif r["provenance"] == "coverage_natural":
            base = r["lineage"]["base_record_id"]
            by_split["probe" if base in pinned else "train"].add(rid)
        else:
            by_split["train"].add(rid)
    if by_split["eval"] != pinned:
        raise AssertionError("eval split != pin")
    total = sum(len(v) for v in by_split.values())
    if total != len(present):
        raise AssertionError("split assignment lost/duplicated records")
    return by_split


def assign_splits(records: list[dict[str, Any]]) -> dict[str, set[str]]:
    """PRE-0.1.4 rule (kept for reference / the pin's provenance): golden ->
    eval unconditionally; synthetic strata keyed (provenance, class, verb),
    sorted by record_id; LAST k go eval where k = min(n-1, floor(n*EVAL_FRACTION)),
    bumped to >=1 once n >= MIN_STRATUM_FOR_EVAL.
    """
    by_split: dict[str, set[str]] = {"train": set(), "eval": set()}
    strata: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for r in records:
        if r["provenance"] == "golden":
            by_split["eval"].add(r["record_id"])  # task AC: golden ALWAYS held out
        else:
            strata[(r["provenance"], r["ambiguity_class"], str(r["verb"]))].append(r["record_id"])
    for (_prov, _cls, _verb), ids in sorted(strata.items()):
        ids = sorted(ids)
        n = len(ids)
        k = math.floor(n * EVAL_FRACTION)
        if n >= MIN_STRATUM_FOR_EVAL:
            k = max(k, 1)
        k = min(k, n - 1)  # every stratum keeps >= 1 train row
        by_split["train"].update(ids[: n - k])
        by_split["eval"].update(ids[n - k:])
    total = sum(len(v) for v in by_split.values())
    if total != len({r["record_id"] for r in records}):
        raise AssertionError("split assignment lost/duplicated records")
    return by_split


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def render_native_row(record: dict[str, Any], split: str, tools: list[dict]) -> dict:
    """FunctionGemma-native row: keys EXACTLY {metadata, tools, messages};
    developer turn byte-matches the committed scaffold template.
    """
    messages: list[dict] = [
        {"role": "developer", "content": scaffold_template_text()},
        {"role": "user", "content": record["utterance"]},
    ]
    if record["assistant_text"] is not None:
        messages.append({"role": "assistant", "content": record["assistant_text"]})
    else:
        messages.append({
            "role": "assistant",
            "tool_calls": [
                {"type": "function", "function": {"name": c["name"], "arguments": c["params"]}}
                for c in record["normalized_calls"]
            ],
        })
    return {"metadata": split, "tools": tools, "messages": messages}


def render_sidecar_row(record: dict[str, Any], split: str) -> dict:
    return {
        "record_id": record["record_id"],
        # Line-alignment contract shared with the golden sidecar: consumers
        # (praxis_training.baseline_eval.runner.load_pair_set) verify the
        # sidecar utterance equals the pair's user turn on every line.
        "utterance": record["utterance"],
        "split": split,
        "provenance": record["provenance"],
        "ambiguity_class": record["ambiguity_class"],
        "verb": record["verb"],
        "supervision_kind": record["supervision_kind"],
        "calls": record["normalized_calls"],
        "lineage": record["lineage"],
    }


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------

def _input_meta(rel: str) -> dict:
    path = REPO_ROOT / rel
    if not path.exists():
        # only the natural corpus may be absent (lane not generated yet)
        assert rel == NATURAL_CORPUS_REL, rel
        return {"path": rel, "sha256": None, "bytes": 0, "rows": 0}
    return {
        "path": rel,
        "sha256": _sha256_file(path),
        "bytes": path.stat().st_size,
        "rows": len(_read_jsonl(path)),
    }


def _count_strata(records: list[dict], by_split: dict[str, set[str]]) -> list[dict]:
    agg: dict[tuple[str, str, str], dict[str, int]] = {}
    for r in records:
        key = (r["provenance"], r["ambiguity_class"], str(r["verb"]))
        slot = agg.setdefault(key, {"n": 0, "n_eval": 0})
        slot["n"] += 1
        if r["record_id"] in by_split["eval"]:
            slot["n_eval"] += 1
    return [
        {"provenance": p, "ambiguity_class": c, "verb": v, **counts}
        for (p, c, v), counts in sorted(agg.items())
    ]


def build_manifest(
    records: list[dict],
    by_split: dict[str, set[str]],
    exclusion_map: dict[str, list[str]],
    scaffold_sha256: str,
    *,
    probe_records: list[dict] | None = None,
    near_probe_records: list[dict] | None = None,
    pin: dict[str, Any] | None = None,
) -> dict:
    probe_records = probe_records or []
    near_probe_records = near_probe_records or []
    n_total = len(records)
    n_eval = len(by_split["eval"])
    eval_norm = {normalize_utterance(r["utterance"]) for r in records if r["record_id"] in by_split["eval"]}
    cross_split_dups = sum(
        1 for r in records if r["record_id"] in by_split["train"] and normalize_utterance(r["utterance"]) in eval_norm
    )
    if cross_split_dups > CROSS_SPLIT_DUPLICATES_AT_PIN:
        raise AssertionError(
            f"cross-split duplicate utterances grew: {cross_split_dups} > {CROSS_SPLIT_DUPLICATES_AT_PIN} at the pin"
        )
    strata = _count_strata(records, by_split)
    train_only = [
        {"provenance": s["provenance"], "ambiguity_class": s["ambiguity_class"], "verb": s["verb"], "n": s["n"]}
        for s in strata
        if s["provenance"] != "golden" and s["n_eval"] == 0 and s["n"] >= MIN_STRATUM_FOR_EVAL
    ]
    per_split_class = {
        split: dict(Counter(r["ambiguity_class"] for r in records if r["record_id"] in ids))
        for split, ids in by_split.items()
    }
    eval_clarify = sum(per_split_class["eval"].get(c, 0) for c in CLARIFY_CLASSES)
    # Measured, never dropped: floor_gen has no utterance-level dedup (only
    # cache-key dedup) and overlay_gen dedups only against floor + itself, so
    # cross-provenance paraphrase collapse is only visible here. Same
    # normalization rule as P2.4's dedup (trim/collapse/casefold).
    normalized = [normalize_utterance(r["utterance"]) for r in records]
    duplicate_utterances = len(normalized) - len(set(normalized))

    def _lineage_versions(field: str) -> list[str]:
        return sorted({r["lineage"][field] for r in records if field in r["lineage"]})

    def _provenance_versions(prov: str) -> list[str]:
        return sorted({r["lineage"]["generator_version"] for r in records if r["provenance"] == prov})

    return {
        "artifact": "praxis-copilot-p25-assembled-corpus",
        "task_id": "260825_copilot_pipeline_spec",
        "backlog_item": 480,
        "spec_ref": ".praxia/docs/specs/260825_coxswain-phase-2-functiongemma-copilot-p.md rev2 §5 P2.5 / §7 AC-2.5.x",
        "assembly_version": ASSEMBLY_VERSION,
        "gap_fields_rule": GAP_FIELDS_RULE,
        "plr_source_sha": plr_source_sha(),
        "scaffold": {
            "template_file": f"training/assemble/{SCAFFOLD_TEMPLATE_NAME}",
            "template_sha256": scaffold_sha256,
            "version": SCAFFOLD_VERSION,
            "date_timestamp_injection": False,
        },
        "dataset_format": "FunctionGemma-native JSONL {metadata, tools[], messages[]} (research §2a / mobile-actions)",
        "inputs": {
            "golden_pairs": _input_meta(GOLDEN_PAIRS_REL),
            "golden_sidecar": _input_meta(GOLDEN_SIDECAR_REL),
            "floor_corpus": _input_meta(FLOOR_CORPUS_REL),
            "overlay_corpus": _input_meta(OVERLAY_CORPUS_REL),
            "natural_corpus": _input_meta(NATURAL_CORPUS_REL),
        },
        "generator_versions": {
            "assemble": ASSEMBLY_VERSION,
            "floor_gen": _provenance_versions("coverage"),
            "floor_gen_natural": _provenance_versions("coverage_natural"),
            "overlay_gen": _provenance_versions("naturalness"),
        },
        "eval_split_pin": {
            "path": PIN_REL,
            "pinned_at_assembly_version": pin["pinned_at_assembly_version"] if pin else None,
            "n": pin["n"] if pin else None,
            "rows_sha256": pin["rows_sha256"] if pin else None,
        },
        "post_freeze_train_only_strata": train_only,
        "probe": {
            "corpus": PROBE_CORPUS_NAME,
            "sidecar": PROBE_SIDECAR_NAME,
            "rows": len(probe_records),
            "by_class": dict(sorted(Counter(r["ambiguity_class"] for r in probe_records).items())),
            "rule": "natural-phrasing variants whose base row is a pinned eval row; scored separately, never part of the 228",
        },
        "probe_near": {
            "corpus": NEAR_PROBE_CORPUS_NAME,
            "sidecar": NEAR_PROBE_SIDECAR_NAME,
            "rows": len(near_probe_records),
            "index_min": NEAR_PROBE_INDEX_MIN,
            "cells": dict(sorted(Counter(r["lineage"]["cell_id"] for r in near_probe_records).items())),
            "by_class": dict(sorted(Counter(r["ambiguity_class"] for r in near_probe_records).items())),
            "rule": "0.1.6: rows of matrix cells APPENDED after the pin (matrix v3 near-surface out-of-surface cells) with example index >= index_min; scored separately, never train, never the 228",
        },
        "prompt_versions": _lineage_versions("prompt_version"),
        "teacher_model_versions": _lineage_versions("teacher_model_version"),
        "split_rule": (
            "0.1.4 PINNED: eval == the record_ids in the eval split pin (cut at "
            "assembly 0.1.3 by: golden -> eval unconditionally; synthetic strata "
            "(provenance x ambiguity-class x verb) sorted by record_id, LAST k -> "
            "eval, k = min(n-1, floor(n*0.2)) bumped to >=1 when n>=4), content "
            "digests asserted; coverage_natural rows follow their base row (eval "
            "base -> probe set); 0.1.6: rows of appended matrix cells with example "
            "index >= 16 -> near-surface probe; every other row -> train"
        ),
        "counts": {
            "total_rows": n_total,
            "by_split": {s: len(ids) for s, ids in sorted(by_split.items())},
            "by_provenance": dict(sorted(Counter(r["provenance"] for r in records).items())),
            "by_class": dict(sorted(Counter(r["ambiguity_class"] for r in records).items())),
            "by_split_and_class": {s: dict(sorted(m.items())) for s, m in sorted(per_split_class.items())},
            "eval_clarify_total": eval_clarify,
            "duplicate_utterances_normalized": duplicate_utterances,
            "cross_split_duplicate_utterances": cross_split_dups,
            "cross_split_duplicate_utterances_at_pin": CROSS_SPLIT_DUPLICATES_AT_PIN,
            "distinct_verbs": sorted({str(r["verb"]) for r in records if r["verb"]}),
            "strata": strata,
        },
        "target": {
            "examples_requested": TARGET_EXAMPLES,
            "examples_assembled": n_total,
            "shortfall": max(0, TARGET_EXAMPLES - n_total),
            "shortfall_reason": SHORTFALL_REASON,
        },
        "exclusions": {
            # RECORDS excluded (a record with two bad calls is one exclusion);
            # reason_entries counts (reason, record) pairs and can exceed it.
            "total": len({rid for rids in exclusion_map.values() for rid in rids}),
            "reason_entries": sum(len(v) for v in exclusion_map.values()),
            "reasons": dict(sorted(exclusion_map.items())),
        },
        "thresholds_doc": THRESHOLDS_DOC_REL,
        "slice_gate_doc": ".praxia/docs/specs/260825_p25_slice_gate.md",
    }


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def build_artifacts() -> dict[str, bytes]:
    """Pure assembly: returns the THREE artifact byte payloads.

    Deterministic: no clock, no RNG, no dict-order dependence (sorted JSON +
    record_id-sorted rows). Same committed inputs => same bytes, always.
    """
    records = load_golden() + load_floor() + load_overlay() + load_natural()
    pin = load_pin(REPO_ROOT / PIN_REL)

    ids = [r["record_id"] for r in records]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise AssertionError(f"duplicate record_ids across branches: {dupes}")

    # Uniform validation gate; excluded records leave loudly + counted.
    kept: list[dict] = []
    exclusion_map: dict[str, list[str]] = defaultdict(list)
    for r in records:
        normalized, reasons = validate_and_normalize(r)
        if reasons:
            for reason in reasons:
                exclusion_map[reason].append(r["record_id"])
            continue
        r["normalized_calls"] = normalized
        kept.append(r)
    if not kept:
        raise AssertionError("assembly kept zero records")

    kept.sort(key=lambda r: r["record_id"])  # global deterministic order

    by_split = assign_splits_pinned(kept, pin)
    from praxis_training.golden_build.corpus import tool_declarations

    tools = tool_declarations()
    corpus_lines: list[str] = []
    sidecar_lines: list[str] = []
    probe_lines: list[str] = []
    probe_sidecar_lines: list[str] = []
    near_lines: list[str] = []
    near_sidecar_lines: list[str] = []
    main_records: list[dict] = []
    probe_records: list[dict] = []
    near_probe_records: list[dict] = []
    for r in kept:
        rid = r["record_id"]
        if rid in by_split["probe_near"]:
            near_lines.append(_canonical_json(render_native_row(r, "eval", tools)))
            near_sidecar_lines.append(_canonical_json(render_sidecar_row(r, "probe_near")))
            near_probe_records.append(r)
            continue
        if rid in by_split["probe"]:
            # probe rows carry metadata "eval" so baseline_eval --split eval
            # scores them unchanged; they live in their own files.
            probe_lines.append(_canonical_json(render_native_row(r, "eval", tools)))
            probe_sidecar_lines.append(_canonical_json(render_sidecar_row(r, "probe")))
            probe_records.append(r)
            continue
        split = "eval" if rid in by_split["eval"] else "train"
        native = render_native_row(r, split, tools)
        if split == "eval" and native_digest(native) != pin["rows"][rid]:
            raise AssertionError(f"pinned eval row {rid} renders differently from the pin (content drift)")
        corpus_lines.append(_canonical_json(native))
        sidecar_lines.append(_canonical_json(render_sidecar_row(r, split)))
        main_records.append(r)

    scaffold_bytes = scaffold_template_bytes()
    if scaffold_bytes != DEVELOPER_SCAFFOLD.encode("utf-8"):
        raise AssertionError(
            "committed scaffold template drifted from golden builder constant "
            "(praxis_training.golden_build.corpus.DEVELOPER_SCAFFOLD)"
        )

    manifest = build_manifest(
        main_records, {"train": by_split["train"], "eval": by_split["eval"]}, exclusion_map,
        hashlib.sha256(scaffold_bytes).hexdigest(), probe_records=probe_records,
        near_probe_records=near_probe_records, pin=pin,
    )
    manifest_bytes = (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode("utf-8")
    return {
        CORPUS_NAME: ("\n".join(corpus_lines) + "\n").encode("utf-8"),
        SIDECAR_NAME: ("\n".join(sidecar_lines) + "\n").encode("utf-8"),
        MANIFEST_NAME: manifest_bytes,
        PROBE_CORPUS_NAME: ("\n".join(probe_lines) + "\n").encode("utf-8"),
        PROBE_SIDECAR_NAME: ("\n".join(probe_sidecar_lines) + "\n").encode("utf-8"),
        NEAR_PROBE_CORPUS_NAME: ("\n".join(near_lines) + "\n").encode("utf-8"),
        NEAR_PROBE_SIDECAR_NAME: ("\n".join(near_sidecar_lines) + "\n").encode("utf-8"),
    }


def main(out_dir: Path | None = None) -> dict:
    """Write artifacts (default training/assemble/out/) + print summary."""
    out_dir = out_dir or (Path(__file__).resolve().parent / "out")
    artifacts = build_artifacts()
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in artifacts.items():
        (out_dir / name).write_bytes(payload)
    manifest = json.loads(artifacts[MANIFEST_NAME])
    summary = {
        "written_to": str(out_dir),
        "total_rows": manifest["counts"]["total_rows"],
        "by_split": manifest["counts"]["by_split"],
        "by_provenance": manifest["counts"]["by_provenance"],
        "by_class": manifest["counts"]["by_class"],
        "shortfall_vs_target": manifest["target"]["shortfall"],
        "exclusions": manifest["exclusions"]["total"],
    }
    print(json.dumps(summary, indent=1, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()
