"""Batch CLI (P2.2 deliverable 4): verify a directory of example files.

Example file format (JSON):
    {
      "intent_record": {...IntentRecord...},
      "call_sequence": [{"name": "...", "params": {...}}, ...],
      "deck_layout": {"resources": {...}, "seed_volumes": {...},
                      "holders": [...]}          # optional
    }

Usage:
    verify-cli <dir-or-file> [--pattern GLOB] [--json] [--bench N]

* prints one PASS/FAIL line per example + a summary table,
* exit code 0 iff every example passed,
* --bench N runs N verifications round-robin over the loaded examples in a
  single process and reports the measured rate against the AC-2.2.4 gate
  (>=100 verifications in <5 minutes, single-process).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from verify.verifier import verify

__all__ = ["load_examples", "main", "run_directory"]

AC_224_MAX_SECONDS = 300.0
AC_224_MIN_VERIFICATIONS = 100


def load_examples(target: Path, pattern: str = "*.json") -> list[dict]:
    """Load example files: a single file or every match inside a directory."""
    files = [target] if target.is_file() else sorted(target.glob(pattern))
    examples = []
    for path in files:
        data = json.loads(path.read_text())
        if "intent_record" not in data or "call_sequence" not in data:
            print(f"SKIP {path.name}: missing intent_record/call_sequence",
                  file=sys.stderr)
            continue
        data["_source"] = path.name
        examples.append(data)
    return examples


async def _verify_example(example: dict) -> dict:
    return await verify(
        example["call_sequence"],
        example["intent_record"],
        layout=example.get("deck_layout"),
        backend=example.get("backend", "LiquidHandlerChatterboxBackend"),
    )


def run_directory(target: Path, pattern: str = "*.json", as_json: bool = False) -> int:
    """Verify all examples; returns process exit code."""
    examples = load_examples(target, pattern)
    if not examples:
        print(f"no example files found under {target}", file=sys.stderr)
        return 2

    results = []
    for ex in examples:
        result = asyncio.run(_verify_example(ex))
        failed = [c for c in result["checks"] if not c["passed"]]
        results.append((ex["_source"], result))

    if not as_json:
        for name, r in results:
            mark = "PASS" if r["passed"] else "FAIL"
            line = f"{mark} {name} ({r['elapsed_ms']:.0f} ms, {len(r['checks'])} checks)"
            if r["error"]:
                line += f" error={r['error']}"
            print(line)
            if not r["passed"]:
                for c in r["checks"]:
                    if not c["passed"]:
                        print(f"     x {c['name']}: {c['detail']}")

    total = len(results)
    npassed = sum(1 for _, r in results if r["passed"])
    if as_json:
        print(json.dumps({
            "total": total,
            "passed": npassed,
            "failed": total - npassed,
            "results": [
                {
                    "file": name,
                    "record_id": r.get("record_id"),
                    "passed": r["passed"],
                    "error": r["error"],
                    "elapsed_ms": r["elapsed_ms"],
                    "failed_checks": [
                        c for c in r["checks"] if not c["passed"]
                    ],
                }
                for name, r in results
            ],
        }, indent=2))
    else:
        print(f"\nsummary: {npassed}/{total} passed")
    return 0 if npassed == total else 1


def bench(target: Path, n: int, pattern: str = "*.json") -> int:
    """AC-2.2.4 performance gate: N verifications, single process."""
    examples = load_examples(target, pattern)
    if not examples:
        print(f"no example files found under {target}", file=sys.stderr)
        return 2

    t0 = time.monotonic()
    for i in range(n):
        asyncio.run(_verify_example(examples[i % len(examples)]))
    elapsed = time.monotonic() - t0

    per_ms = elapsed / n * 1000
    projected_100 = elapsed / n * AC_224_MIN_VERIFICATIONS
    gate_ok = projected_100 < AC_224_MAX_SECONDS
    rate = n / elapsed
    print(f"bench: {n} verifications in {elapsed:.1f}s "
          f"({rate:.1f}/s, {elapsed / n * 1000:.0f} ms each)")
    print(f"gate AC-2.2.4: {AC_224_MIN_VERIFICATIONS} verifications would take "
          f"{projected_100:.1f}s (<{AC_224_MAX_SECONDS:.0f}s budget): "
          f"{'PASS' if gate_ok else 'FAIL'}")
    return 0 if gate_ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify-cli", description=__doc__.splitlines()[0]
    )
    parser.add_argument("target", type=Path,
                        help="directory of example JSON files, or one file")
    parser.add_argument("--pattern", default="*.json")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="machine-readable summary on stdout")
    parser.add_argument("--bench", type=int, metavar="N", default=0,
                        help="run N verifications and report the rate vs "
                             "the AC-2.2.4 gate instead of the summary")
    args = parser.parse_args(argv)

    if args.bench > 0:
        return bench(args.target, args.bench, args.pattern)
    return run_directory(args.target, args.pattern, args.as_json)


if __name__ == "__main__":
    raise SystemExit(main())
