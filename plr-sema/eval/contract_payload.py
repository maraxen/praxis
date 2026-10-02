#!/usr/bin/env python3
"""Measure the shippable size of plr-sema's derived contract table (261002_sema-web-integration).

Slice 1 of the sema web-integration design (Section 2) proposes shipping the
WHOLE contract table, compact-serialized and gzipped, with no receiver-scoped
slicing. That decision rests on one number -- the compact+gzip size of
``plr-sema/data/derived_contracts.json`` -- so it is measured here under a
pre-registered sidecar (``contract_payload.bth.toml``) rather than quoted from a
transcript.

What is measured, all from one read of the input file:

* raw / compact (``separators=(",", ":")``) / compact+gzip(-9) byte counts;
* a round-trip integrity check: gunzip -> ``json.loads`` must equal the
  originally parsed object, or the shipped form is not the table;
* the ``LiquidHandler.*`` slice size, recorded only because Section 2 rejects
  slicing and the spec cites what was given up;
* a NEGATIVE control: a deterministic pseudo-random byte stream of the same
  length as the compact table (sha256 counter mode, so the run is
  reproducible) gzipped the same way. It is incompressible, so it must land
  far above the pass budget; if it does not, the instrument is not measuring
  compression and no verdict from this run counts.

Pure read: touches no shipped file. Stdlib only.

Usage::

    uv run --no-sync python3 plr-sema/eval/contract_payload.py \\
        --report outputs/sema_s1/contract_payload.json
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACTS = REPO_ROOT / "plr-sema" / "data" / "derived_contracts.json"

#: Section 2's pass budget for the whole compact+gzip table. Emitted into the
#: results so the sidecar's control comparison reads the same constant.
BUDGET_BYTES = 1_000_000

log = logging.getLogger(__name__)


def _compact(obj: object) -> bytes:
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def _gz(data: bytes) -> bytes:
    # mtime=0 so the compressed bytes depend on the input only.
    return gzip.compress(data, compresslevel=9, mtime=0)


def _incompressible(n: int) -> bytes:
    """``n`` deterministic pseudo-random bytes (sha256 in counter mode)."""
    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(counter.to_bytes(8, "big")).digest()
        counter += 1
    return bytes(out[:n])


def measure(contracts_path: Path) -> dict:
    raw = contracts_path.read_bytes()
    table = json.loads(raw)

    compact = _compact(table)
    gz = _gz(compact)
    roundtrip_equal = json.loads(gzip.decompress(gz)) == table

    contracts = table["contracts"]
    lh_keys = sorted(k for k in contracts if k.startswith("LiquidHandler."))
    lh_slice = {
        "contracts": {k: contracts[k] for k in lh_keys},
        "receiver_state": table.get("receiver_state"),
        "schema_version": table.get("schema_version"),
        "stamp": table.get("stamp"),
    }
    lh_gz = _gz(_compact(lh_slice))

    control_gz = _gz(_incompressible(len(compact)))

    stamp = table.get("stamp") or {}
    return {
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "stamp_plr": str(stamp.get("plr", "")),
        "raw_bytes": len(raw),
        "compact_bytes": len(compact),
        "gz_bytes": len(gz),
        "gz_ratio": round(len(gz) / len(compact), 6),
        "roundtrip_equal": int(roundtrip_equal),
        "n_contracts": len(contracts),
        "lh_keys": len(lh_keys),
        "lh_gz_bytes": len(lh_gz),
        "control_gz_bytes": len(control_gz),
        "budget_bytes": BUDGET_BYTES,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    result = measure(args.contracts)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2))
    log.info("Report written to %s", args.report)

    bth_path = os.environ.get("BTH_RESULTS_PATH")
    if bth_path:
        Path(bth_path).write_text(json.dumps(result))
        log.info("Bathos results written to %s", bth_path)

    log.info(
        "compact=%d gz=%d (ratio %.4f) roundtrip=%d lh_gz=%d control_gz=%d budget=%d",
        result["compact_bytes"], result["gz_bytes"], result["gz_ratio"], result["roundtrip_equal"],
        result["lh_gz_bytes"], result["control_gz_bytes"], result["budget_bytes"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
