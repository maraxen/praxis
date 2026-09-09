r"""Content digests for freezing a committed corpus before a generator change.

Precedent: ``training/floor_gen/data/floor_0.2.0_accepted_digests.json`` (task
260902_p26b_surface_data) froze the 625 assembly-accepted floor rows modulo
``provenance.generator_version``. This module makes the rule reusable:

    uv run --package training python -m floor_gen.digests \\
        --corpus training/out/corpus_p23_floor_natural.jsonl \\
        --out training/floor_gen/data/natural_v2_accepted_digests.json \\
        --drop-provenance-key teacher_model_version --artifact praxis-natural-accepted-digests

A digest is sha256 over the canonical JSON of the row with the named
``provenance`` keys removed, so a regeneration may restamp those keys and
nothing else.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def canonical_json(obj: Any) -> str:
  return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def row_digest(row: dict[str, Any], *, drop_provenance_keys: Iterable[str]) -> str:
  drop = set(drop_provenance_keys)
  r = json.loads(canonical_json(row))
  r["provenance"] = {k: v for k, v in r.get("provenance", {}).items() if k not in drop}
  return hashlib.sha256(canonical_json(r).encode("utf-8")).hexdigest()


def build_digest_file(
  rows: list[dict[str, Any]],
  *,
  artifact: str,
  drop_provenance_keys: tuple[str, ...],
  extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
  digests = {r["record_id"]: row_digest(r, drop_provenance_keys=drop_provenance_keys) for r in rows}
  if len(digests) != len(rows):
    raise ValueError("duplicate record_id in corpus")
  out: dict[str, Any] = {
    "artifact": artifact,
    "digest_rule": (
      "sha256(canonical JSON of the row with provenance."
      + "/provenance.".join(drop_provenance_keys)
      + " removed)"
    ),
    "drop_provenance_keys": list(drop_provenance_keys),
    "n_rows": len(rows),
    "rows": dict(sorted(digests.items())),
  }
  out.update(extra or {})
  return out


def read_jsonl(path: Path) -> list[dict[str, Any]]:
  return [
    json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
  ]


def main(argv: list[str] | None = None) -> int:
  p = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
  )
  p.add_argument("--corpus", required=True, type=Path)
  p.add_argument("--out", required=True, type=Path)
  p.add_argument("--artifact", required=True)
  p.add_argument("--drop-provenance-key", action="append", default=[], dest="drop")
  p.add_argument("--meta", action="append", default=[], help="extra key=value recorded in the file")
  a = p.parse_args(argv)
  rows = read_jsonl(a.corpus)
  extra = dict(kv.split("=", 1) for kv in a.meta)
  doc = build_digest_file(
    rows, artifact=a.artifact, drop_provenance_keys=tuple(a.drop), extra=extra
  )
  a.out.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
  print(f"{a.out}: n_rows={doc['n_rows']} drop={doc['drop_provenance_keys']}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
