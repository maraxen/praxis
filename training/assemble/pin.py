"""Eval-split pin: freezes the 228-row P2.5 eval split by record_id AND content.

Task 260902_p26b_surface_data. Baseline v2, the P2.6 ablation and the 260902
re-score were all measured on the eval split assembly 0.1.3 produced. Later
corpus changes (repaired floor rows, the natural-phrasing lane) may only add
TRAIN rows: the assembler reads this pin, puts exactly these record_ids in
eval, and asserts every pinned native row still renders byte-identically.

Digest = sha256 of the canonical JSON (sorted keys, compact separators,
ASCII) of the NATIVE pairs row ({metadata, tools, messages}) -- the thing
the model is scored on. The sidecar (gap annotations, lineage) is not part
of the digest; those fields may change under the D11 derivation rule.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

__all__ = ["PIN_REL", "native_digest", "write_pin", "load_pin"]

PIN_REL = "training/assemble/data/eval_split_pin.json"


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def native_digest(native_row: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(native_row).encode("utf-8")).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_pin(pairs_path: Path, sidecar_path: Path, out_path: Path, *, assembly_version: str) -> dict[str, Any]:
    """Pin the eval rows of an assembled corpus (record_id -> native digest)."""
    pairs = _read_jsonl(pairs_path)
    sidecar = _read_jsonl(sidecar_path)
    if len(pairs) != len(sidecar):
        raise ValueError("pairs/sidecar line count mismatch")
    rows: dict[str, str] = {}
    for p, s in zip(pairs, sidecar):
        if p["metadata"] != "eval":
            continue
        rows[str(s["record_id"])] = native_digest(p)
    ordered = {rid: rows[rid] for rid in sorted(rows)}
    pin = {
        "artifact": "praxis-eval-split-pin",
        "pinned_at_assembly_version": assembly_version,
        "n": len(ordered),
        "rows_sha256": hashlib.sha256(_canonical(sorted(ordered)).encode("utf-8")).hexdigest(),
        "rows": ordered,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(pin, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return pin


def load_pin(path: Path) -> dict[str, Any]:
    pin = json.loads(path.read_text(encoding="utf-8"))
    if pin.get("artifact") != "praxis-eval-split-pin":
        raise ValueError(f"{path}: not an eval-split pin")
    if pin["n"] != len(pin["rows"]):
        raise ValueError(f"{path}: n {pin['n']} != rows {len(pin['rows'])}")
    return pin
