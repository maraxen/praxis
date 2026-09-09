"""Oracle spike: does PLR's simulator agree with plr-sema's static verdict?

Feasibility probe for the oracle harness (plan
``.praxia/docs/plans/260902_plr-sema-oracle-harness.md``). For each
verifier example (``training/examples/*.json``: ``call_sequence`` +
``intent_record`` + ``deck_layout``) it produces two independent readings
of the same protocol and lines them up per operation:

* **runtime** -- ``training/verify``'s ``verify()`` runs the call sequence on
  the chatterbox backend with STRICT mode and tip + volume tracking on, so
  PLR itself raises ``NoTipError`` / ``HasTipError`` / ``TooLittleLiquidError``
  / ... at the offending step. ``verify()`` collapses that to one error
  string, so this script wraps ``plan_call`` to learn *which* operation
  index was being executed when it raised.
* **static** -- 260902 (spec §11, SEMA-IR): the runtime's own PLR-named,
  already-grounded kwargs (``run_runtime``'s ``recording_plan_call``
  harvest, reduced to IR value JSON by ``ir_value_of``) are lowered
  through ``plr_sema.check.ir.lower_calls`` and checked by
  ``plr_sema.check.check_ir`` against the shipped derived-contract table
  -- no adapted graph, no tool-named argument guessing. Per-operation
  verdict = ``join`` of that operation's findings.

The soundness contract this checks, per operation ``i``:

* static ``SAFE`` and the simulator raised at ``i``       -> UNSOUND (bug)
* static ``WILL_FAIL`` and the simulator ran ``i`` cleanly -> UNSOUND (bug)
* static ``UNKNOWN``                                          -> no constraint

Everything else is an agreement row. Tier 1 of the plan (corpus replay)
is this script generalised to the 812-row corpus and made bathos-tracked;
this spike is deliberately unscored and untracked -- it exists to prove
the glue closes, not to publish a number.

Usage::

    uv run python plr-sema/scripts/oracle_spike.py \
        --examples training/examples --json-out $TMPDIR/oracle_spike.json
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))

from oracle_common import (
    DEFAULT_CONTRACTS,
    compare,
    param_names_from_contracts,
    run_runtime,
    run_static_calls,
)

log = logging.getLogger("oracle_spike")

REPO_ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--examples", type=Path, required=True, help="a JSON file or a directory of them")
    ap.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    files = [args.examples] if args.examples.is_file() else sorted(args.examples.glob("*.json"))
    contracts_json = args.contracts.read_text(encoding="utf-8")
    param_names = param_names_from_contracts(contracts_json)
    out: list[dict[str, Any]] = []
    n_unsound = 0
    for f in files:
        ex = json.loads(f.read_text(encoding="utf-8"))
        if "call_sequence" not in ex or "intent_record" not in ex:
            log.info("skip %s (no call_sequence/intent_record)", f.name)
            continue
        rt = run_runtime(ex)
        st, not_planned = run_static_calls(ex, rt.plr_kwargs, contracts_json, param_names=param_names)
        if not_planned:
            log.warning("%s: %d call(s) never planned (no CALL emitted): indices=%s",
                        f.name, len(not_planned), not_planned)
        rows = compare(ex, rt, st)
        n_unsound += sum(r["unsound"] for r in rows)
        log.info("%s  runtime=%s  planned=%s", f.name, rt.error or "clean", rt.planned_indices)
        for r in rows:
            log.info("  op_%d %-14s static=%-9s (%2d findings)  runtime=%s%s",
                     r["index"], r["method"], r["static"], r["static_findings"], r["runtime"],
                     "  <-- UNSOUND" if r["unsound"] else "")
        out.append({"example": f.name, "runtime": dataclasses.asdict(rt), "rows": rows, "not_planned": not_planned})
    log.info("examples=%d operations=%d unsound=%d", len(out), sum(len(o["rows"]) for o in out), n_unsound)
    if args.json_out:
        args.json_out.write_text(json.dumps(out, indent=2))
    return 1 if n_unsound else 0


if __name__ == "__main__":
    sys.exit(main())
