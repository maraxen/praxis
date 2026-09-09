"""Spec 260903 §14.9 (`260903_plr-sema-volume-increment.md`, increment 5,
backlog #4960, T28): tier-3 volume mutants, **one class**.

* **v1 (`v1_overdraw_dispense`).** Multiplies the last `dispense` call's
  `volume_ul` so it exceeds what the mounted tip holds after the row's own
  preceding `aspirate`(s) -- the row's `deck_layout` and every OTHER call is
  carried unchanged from the base example, exactly as `tip_mutants.py`'s own
  m1/m2 depend on (§14.9's normative paragraph on why the state must come
  from the UNMUTATED call, never recomputed from the mutant). Expected
  simulator outcome: `TooLittleLiquidError`, raised at
  `op.tip.tracker.remove_liquid` (`liquid_handler.py:1235`) -- the tip-side
  guard `dispense` bridges, the one guard round-1's R1 (§14.6) makes
  decidable.

`v2_overdraw_transfer` is WITHDRAWN (round-1 O11, §14.9): `transfer` matches
no bridge shape at this pin, so its static side would be `UNKNOWN` by
construction and the class would measure the spec's own scope decision
rather than the implementation. See §14.9's normative box for the full
argument -- it is not reproduced here as code.

This module reuses `tip_mutants.run_one_mutant`'s shape verbatim (the
mutator/expected-exception pair is passed in as arguments, per that
function's own 260903 refactor) rather than re-implementing the
runtime-then-static harness a second time.

Usage::

    uv run python plr-sema/eval/volume_mutants.py \\
        --corpus training/assemble/out/corpus_p25.jsonl \\
        --examples-dir training/examples \\
        --contracts plr-sema/data/derived_contracts.json \\
        --report /tmp/volume_mutants_report.json \\
        --limit 300
"""

from __future__ import annotations

import argparse
import copy
import json
import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "eval"))
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))

import oracle_common as oc  # noqa: E402
from oracle_replay import row_to_verifier_inputs  # noqa: E402
from tip_mutants import MutantResult, run_one_mutant  # noqa: E402

log = logging.getLogger("volume_mutants")

DEFAULT_CONTRACTS = REPO_ROOT / "plr-sema" / "data" / "derived_contracts.json"

_EXPECTED_EXC = {"v1_overdraw_dispense": "TooLittleLiquidError"}

#: The margin added ABOVE the tip's own tracked balance (never a blowout
#: constant): `dispense`'s real PLR code queues the DESTINATION resource's
#: `add_liquid` (increasing, capacity-checked) BEFORE the mounted tip's own
#: `remove_liquid` (decreasing, this class's target), in the SAME `for op in
#: dispenses:` loop (`liquid_handler.py:1226-1233`) -- an astronomically
#: large mutated volume overflows the DESTINATION's own capacity first and
#: raises `TooLittleVolumeError` there, never reaching the tip check this
#: class exists to exercise. Staying within a small margin of the tip's own
#: real, wire-level tracked balance keeps the mutated volume the same order
#: of magnitude as what the base row's own (successful) calls already
#: proved a real resource could accept.
_OVERDRAW_MARGIN_FRACTION = 0.1
_OVERDRAW_MARGIN_FLOOR_UL = 1.0


def _last_dispense_index(call_sequence: list[dict[str, Any]]) -> int | None:
    idx = None
    for i, c in enumerate(call_sequence):
        if c.get("name") == "dispense":
            idx = i
    return idx


def _scalar_volume(value: Any) -> float | None:
    """`volume_ul` at this wire level appears BOTH as a bare number
    (`training/examples/*.json`, `dispense` calls throughout the corpus)
    and as a single-element list (`aspirate` calls throughout the corpus --
    measured: 90/90 corpus `aspirate.volume_ul` values are `list`, 0
    scalar; 90/90 `dispense.volume_ul` values are scalar, 0 `list`).
    Reads either shape; `None` (never a guess) for anything else, including
    a multi-element list -- true multi-channel batching this scalar
    running-balance heuristic cannot follow.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list) and len(value) == 1:
        item = value[0]
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            return float(item)
    return None


def _tip_balance_before(call_sequence: list[dict[str, Any]], target_idx: int) -> float | None:
    """The wire-level running balance of the tip mounted at `target_idx`,
    tracked the same arithmetic PLR's own per-tip `VolumeTracker` performs:
    `+=` on every preceding `aspirate`'s `volume_ul`, `-=` on every
    preceding `dispense`'s -- reset to `0.0` at the most recent
    `pick_up_tips`/`drop_tips` (a fresh or departed tip carries nothing
    forward, §14.5 V5). Single-channel only (:func:`_scalar_volume`).

    `None` -- construction declined, never guessed -- when the running
    balance would go negative (a shape this scalar heuristic cannot
    follow, e.g. multi-channel batching this wire format does not
    represent): the base row ran CLEAN, so a negative running balance means
    this function's arithmetic has diverged from PLR's own, not that the
    row is unsound.
    """
    balance = 0.0
    for c in call_sequence[:target_idx]:
        name = c.get("name")
        if name in ("pick_up_tips", "drop_tips"):
            balance = 0.0
            continue
        vol = _scalar_volume(c.get("params", {}).get("volume_ul"))
        if vol is None:
            continue
        if name == "aspirate":
            balance += vol
        elif name == "dispense":
            balance -= vol
            if balance < 0.0:
                return None
    return balance


def make_v1_overdraw_dispense(example: dict[str, Any]) -> dict[str, Any] | None:
    """Multiplies the LAST `dispense` call's `volume_ul` (§14.9's normative
    box) so it exceeds the tip's own tracked balance at that point
    (:func:`_tip_balance_before`), by a small margin rather than a blowout
    constant -- see that margin's own module-level comment for why.

    `None` (mutation not constructed, the same "skip, don't guess"
    discipline `tip_mutants.make_m1_remove_pickup` follows for a missing
    `pick_up_tips` call) when there is no `dispense` call, its `volume_ul`
    is not a plain number, the running-balance heuristic could not follow
    the sequence, or the tracked balance is non-positive (nothing to
    over-draw against).
    """
    idx = _last_dispense_index(example["call_sequence"])
    if idx is None:
        return None
    held = _tip_balance_before(example["call_sequence"], idx)
    if held is None or held <= 0.0:
        return None
    call = example["call_sequence"][idx]
    volume_ul = _scalar_volume(call.get("params", {}).get("volume_ul"))
    if volume_ul is None:
        return None
    mutant = copy.deepcopy(example)
    margin = max(_OVERDRAW_MARGIN_FLOOR_UL, held * _OVERDRAW_MARGIN_FRACTION)
    mutant["call_sequence"][idx]["params"]["volume_ul"] = held + margin
    return mutant


_MUTATORS = {"v1_overdraw_dispense": make_v1_overdraw_dispense}


def _clean_corpus_examples(corpus_path: Path, limit: int | None) -> list[tuple[str, dict[str, Any]]]:
    """Rows the tier-1 replay executes CLEAN (`RuntimeOutcome.passed`) and
    that contain >=1 `dispense` call -- the `tip_mutants._clean_corpus_
    examples` pattern, keyed on `dispense` rather than `pick_up_tips`.
    """
    out: list[tuple[str, dict[str, Any]]] = []
    with corpus_path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            if limit is not None and i > limit:
                break
            row = json.loads(line)
            try:
                call_sequence, intent_record, deck_layout, skip_reason, no_call_reason = row_to_verifier_inputs(
                    row, source_file=corpus_path.stem, line=i
                )
            except Exception:
                continue
            if no_call_reason or skip_reason:
                continue
            if not any(c.get("name") == "dispense" for c in call_sequence):
                continue
            example = {"call_sequence": call_sequence, "intent_record": intent_record, "deck_layout": deck_layout}
            try:
                rt = oc.run_runtime(example)
            except Exception:
                continue
            if not rt.passed:
                continue
            base_id = intent_record.get("record_id", f"{corpus_path.stem}:{i}")
            out.append((base_id, example))
    return out


def _example_files(examples_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    if not examples_dir.is_dir():
        return out
    for path in sorted(examples_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "call_sequence" not in payload:
            continue
        if not any(c.get("name") == "dispense" for c in payload["call_sequence"]):
            continue
        out.append((path.stem, payload))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--examples-dir", type=Path, default=REPO_ROOT / "training" / "examples")
    ap.add_argument("--contracts", type=Path, default=DEFAULT_CONTRACTS)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=None, help="corpus row limit (base-example discovery)")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    contracts_json = args.contracts.read_text(encoding="utf-8")
    param_names = oc.param_names_from_contracts(contracts_json)

    bases: list[tuple[str, dict[str, Any]]] = []
    bases.extend(_clean_corpus_examples(args.corpus, args.limit))
    n_corpus_bases = len(bases)
    bases.extend(_example_files(args.examples_dir))
    n_example_bases = len(bases) - n_corpus_bases
    log.info(
        "base examples: %d from corpus (clean, has dispense), %d from --examples-dir",
        n_corpus_bases, n_example_bases,
    )

    results: list[MutantResult] = []
    for base_id, example in bases:
        mutant_class = "v1_overdraw_dispense"
        results.append(
            run_one_mutant(
                base_id, mutant_class, example, contracts_json, param_names,
                _MUTATORS[mutant_class], _EXPECTED_EXC[mutant_class],
            )
        )

    by_class: dict[str, list[MutantResult]] = {"v1_overdraw_dispense": results}

    summary: dict[str, Any] = {}
    hard_violations: list[str] = []
    will_fail_fired: dict[str, bool] = {}

    for mclass, rows in by_class.items():
        ran = [r for r in rows if r.ran and r.error is None]
        raised_as_expected = [r for r in ran if r.raised_as_expected]
        verdict_counts = {"will_fail": 0, "unknown": 0, "safe": 0, "none": 0}
        for r in raised_as_expected:
            key = r.static_verdict_at_index or "none"
            verdict_counts[key] = verdict_counts.get(key, 0) + 1

        unsound_safe_rows = [r.base_id for r in ran if r.unsound_safe]
        unsound_will_fail_rows = [r.base_id for r in ran if r.unsound_will_fail_elsewhere]
        will_fail_fired[mclass] = verdict_counts.get("will_fail", 0) > 0

        summary[mclass] = {
            "n_total": len(rows),
            "n_construction_skipped": len(rows) - len(ran) - sum(1 for r in rows if r.ran and r.error),
            "n_error": sum(1 for r in rows if r.error is not None),
            "n_ran": len(ran),
            "n_raised_as_expected": len(raised_as_expected),
            "static_verdict_at_raising_index": verdict_counts,
            "unsound_safe_where_simulator_raised": unsound_safe_rows,
            "unsound_will_fail_where_simulator_ran_clean": unsound_will_fail_rows,
        }

        if unsound_safe_rows:
            hard_violations.append(
                f"{mclass}: criterion (i) VIOLATED -- {len(unsound_safe_rows)} row(s) static SAFE where simulator raised: {unsound_safe_rows[:5]}"
            )
        if unsound_will_fail_rows:
            hard_violations.append(
                f"{mclass}: criterion (ii) VIOLATED -- {len(unsound_will_fail_rows)} row(s) static WILL_FAIL where simulator ran clean: {unsound_will_fail_rows[:5]}"
            )
        if not will_fail_fired[mclass]:
            hard_violations.append(
                f"{mclass}: criterion (iii) FAILED -- WILL_FAIL never fired in the direction the simulator raised "
                f"({len(raised_as_expected)} rows raised as expected; static verdicts there: {verdict_counts})"
            )

    report = {
        "n_corpus_bases": n_corpus_bases,
        "n_example_bases": n_example_bases,
        "by_class": summary,
        "hard_violations": hard_violations,
        "gate_passed": not hard_violations,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    log.info("report written to %s", args.report)
    for mclass, s in summary.items():
        log.info(
            "%s: n=%d raised_as_expected=%d static_at_index=%s",
            mclass, s["n_total"], s["n_raised_as_expected"], s["static_verdict_at_raising_index"],
        )
    if hard_violations:
        log.error("GATE FAILED:\n%s", "\n".join(hard_violations))
        return 1
    log.info("GATE PASSED: criteria (i), (ii), (iii) hold for v1_overdraw_dispense.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
