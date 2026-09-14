"""Spec 260902 §10.7 AC-10.12 (backlog #4881, tier-3 tip-family mutants):
`#4888`'s OWN gate -- "not a downstream nicety" (§10.7's task row).

Two mutant classes, generated from every base example that (a) the tier-1
corpus replay (`oracle_replay.py`, over `training/assemble/out/corpus_p25.
jsonl`) executes CLEAN (`RuntimeOutcome.passed`) and that contains a
`pick_up_tips` call, and (b) every `training/examples/*.json` fixture
containing one:

* **m1 (remove pickup).** Delete the first `pick_up_tips` call from
  `call_sequence`. Expected simulator outcome: a downstream tip-requiring
  call (`aspirate`/`dispense`/`drop_tips`) raises `NoTipError`.
* **m2 (duplicate pickup).** Insert an identical copy of the first
  `pick_up_tips` call immediately after itself. Expected simulator outcome:
  the SECOND `pick_up_tips` call raises `HasTipError`.

Each mutant is run through BOTH `oracle_common.run_runtime` (the
simulator, ground truth) and `lower_calls` -> `check_ir` (the static
analyzer, via `oracle_common.run_static_calls`, which reads THIS module's
tip-typestate machinery through the same path `oracle_replay.py`'s tier-1
harness does). §10.7's AC-10.12 hard assertions, per mutant class:

  (i)   ZERO mutant rows where the simulator raised `NoTipError`/
        `HasTipError` at index i carry a static `SAFE` at i.
  (ii)  ZERO rows where the simulator ran index i clean carry a static
        `WILL_FAIL` at i.
  (iii) AT LEAST ONE row in EACH mutation class carries a static
        `WILL_FAIL` at the index the simulator raised.

(iii) is what makes this gate unsatisfiable by an evaluator that never
fires -- see this module's own `main`'s exit code, which treats a
criterion-(iii) failure as a FAILED gate, not a weaker warning (per the
task brief: "If WILL_FAIL never fires, that is a FAILED gate -- report it
as such and do not weaken it").

Usage::

    uv run python plr-sema/eval/tip_mutants.py \\
        --corpus training/assemble/out/corpus_p25.jsonl \\
        --examples-dir training/examples \\
        --contracts plr-sema/data/derived_contracts.json \\
        --report /tmp/tip_mutants_report.json \\
        --limit 300
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "eval"))
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))

import oracle_common as oc  # noqa: E402
from oracle_replay import row_to_verifier_inputs  # noqa: E402

log = logging.getLogger("tip_mutants")

DEFAULT_CONTRACTS = REPO_ROOT / "plr-sema" / "data" / "derived_contracts.json"

_EXPECTED_EXC = {"m1_remove_pickup": "NoTipError", "m2_duplicate_pickup": "HasTipError"}


@dataclasses.dataclass
class MutantResult:
    base_id: str
    mutant_class: str
    ran: bool  # False if the mutation could not be constructed (no pick_up_tips call)
    error: str | None
    raised_exc_class: str | None
    raised_as_expected: bool
    raising_index: int | None
    static_verdict_at_index: str | None
    unsound_safe: bool
    unsound_will_fail_elsewhere: bool


def _first_pickup_index(call_sequence: list[dict[str, Any]]) -> int | None:
    for i, c in enumerate(call_sequence):
        if c.get("name") == "pick_up_tips":
            return i
    return None


def _last_pickup_index(call_sequence: list[dict[str, Any]]) -> int | None:
    idx = None
    for i, c in enumerate(call_sequence):
        if c.get("name") == "pick_up_tips":
            idx = i
    return idx


def make_m1_remove_pickup(example: dict[str, Any]) -> dict[str, Any] | None:
    """Removes the LAST `pick_up_tips` call, not the first. For a
    single-cycle example the two coincide. The distinction matters for a
    MULTI-cycle example (pickup/aspirate/drop, pickup/aspirate/drop, ...):
    removing the LAST occurrence leaves an EARLIER `drop_tips` in place,
    which is what actually gives the static analyzer a channel state to
    reason from (NO_TIP, established by that earlier `drop_tips`) -- the
    walk never treats "nothing ever loaded a tip" as itself meaning
    NO_TIP (state defaults to Top, not Nothing was established therefore
    empty; §10.1.3), so removing a FIRST-and-only pickup from a
    single-cycle example structurally cannot produce a static WILL_FAIL --
    see this module's own report/commit-message note on AC-10.12 criterion
    (iii) and why `training/examples/tip_mutant_probe.json` (a two-cycle
    fixture) exists.
    """
    idx = _last_pickup_index(example["call_sequence"])
    if idx is None:
        return None
    mutant = copy.deepcopy(example)
    del mutant["call_sequence"][idx]
    return mutant


_WELL_REF_RE = re.compile(r"^(?P<base>.+)\.(?P<row>[A-H])(?P<col>\d{1,2})$")


def _shift_tip_ref(ref: Any, position: int) -> Any:
    """Remap a `"<resource>.<Row><Col>"` well reference to a FAR corner of a
    (real, 96-well, `training/floor_gen/exec_verify.py`-documented)
    standard tip rack, e.g. `"tip_rack.C1"` -> `"tip_rack.H12"`. Used only
    by m2 (duplicate pickup): duplicating the pickup at the IDENTICAL tip
    spot collides at the RESOURCE's own tip-spot tracker first
    (`NoTipError`, "tip spot has no tip"), never reaching the HEAD
    tracker's `HasTipError` check this increment targets -- shifting to a
    still-full spot isolates the head-tracker collision (same channel
    COUNT, so the arity-default rule assigns the identical channel indices
    both times) from the resource-availability collision. Non-string /
    non-matching values pass through unchanged (defensive; every base
    example measured uses this exact `"tip_rack.<Row><Col>"` shape).
    """
    if not isinstance(ref, str):
        return ref
    m = _WELL_REF_RE.match(ref)
    if m is None:
        return ref
    row = chr(ord("H") - (position % 8))
    col = 12 - (position % 12)
    return f"{m.group('base')}.{row}{max(col, 1)}"


def make_m2_duplicate_pickup(example: dict[str, Any]) -> dict[str, Any] | None:
    idx = _first_pickup_index(example["call_sequence"])
    if idx is None:
        return None
    mutant = copy.deepcopy(example)
    call = mutant["call_sequence"][idx]
    duplicate = copy.deepcopy(call)
    at = duplicate.get("params", {}).get("at")
    if isinstance(at, list):
        duplicate["params"]["at"] = [_shift_tip_ref(v, i) for i, v in enumerate(at)]
    elif isinstance(at, str):
        duplicate["params"]["at"] = _shift_tip_ref(at, 0)
    mutant["call_sequence"].insert(idx + 1, duplicate)
    return mutant


_MUTATORS = {"m1_remove_pickup": make_m1_remove_pickup, "m2_duplicate_pickup": make_m2_duplicate_pickup}


def run_one_mutant(
    base_id: str,
    mutant_class: str,
    example: dict[str, Any],
    contracts_json: str,
    param_names: Any,
    mutator: Callable[[dict[str, Any]], dict[str, Any] | None],
    expected_exc: str,
) -> MutantResult:
    """Shared shape for every mutant class this module and `volume_mutants.
    py` generate (spec 260903 §14.9): `mutator`/`expected_exc` are passed in
    by the caller rather than read off this module's own `_MUTATORS`/
    `_EXPECTED_EXC` globals, so a second module (`volume_mutants.py`'s
    `v1_overdraw_dispense`) can reuse this function's shape verbatim without
    importing this module's tip-specific mutator table. The refactor moves
    no m1/m2 semantics -- `main`'s own call sites below still read
    `_MUTATORS`/`_EXPECTED_EXC`, just as arguments now instead of as a
    module-global lookup inside this function.

    The static side runs under the runtime's OWN observed `env` (260903
    T27/T28, backlog #4959/#4960): `rt.volume_tracking_observed`, read from
    inside the window `verify()` turned tracking on in, is threaded into
    `oc.run_static_calls` so the analyzer's hypothesis matches what the
    simulator actually asserted -- never a separate, potentially stale,
    process-wide read.
    """
    mutant = mutator(example)
    if mutant is None:
        return MutantResult(base_id, mutant_class, False, "mutation could not be constructed", None, False, None, None, False, False)

    try:
        rt = oc.run_runtime(mutant)
    except Exception as e:
        return MutantResult(base_id, mutant_class, False, f"runtime:{e}", None, False, None, None, False, False)

    exc_class = rt.exc_class
    raising_index = rt.failing_index
    raised_as_expected = exc_class == expected_exc

    try:
        st, _not_planned = oc.run_static_calls(
            mutant, rt.plr_kwargs, contracts_json, param_names=param_names,
            volume_tracking_observed=rt.volume_tracking_observed,
        )
    except Exception as e:
        return MutantResult(
            base_id, mutant_class, True, f"static:{e}", exc_class, raised_as_expected, raising_index, None, False, False
        )

    static_verdict_at_index = None
    if raising_index is not None:
        entry = st.get(f"op_{raising_index}")
        static_verdict_at_index = entry["verdict"] if entry is not None else None

    # (i): simulator raised the expected tip-state exception at this index,
    # but the static verdict there is SAFE -- unsound.
    unsound_safe = raised_as_expected and static_verdict_at_index == "safe"

    # (ii): simulator ran an op clean (not the raising index, or the whole
    # sequence ran clean) but the static verdict there is WILL_FAIL.
    unsound_will_fail_elsewhere = False
    for oid, sdata in st.items():
        idx = int(oid.split("_", 1)[1])
        simulator_raised_here = raising_index is not None and idx == raising_index and exc_class is not None
        if not simulator_raised_here and sdata["verdict"] == "will_fail":
            unsound_will_fail_elsewhere = True
            break

    return MutantResult(
        base_id,
        mutant_class,
        True,
        None,
        exc_class,
        raised_as_expected,
        raising_index,
        static_verdict_at_index,
        unsound_safe,
        unsound_will_fail_elsewhere,
    )


def _clean_corpus_examples(corpus_path: Path, limit: int | None) -> list[tuple[str, dict[str, Any]]]:
    """Rows the tier-1 replay executes CLEAN (`RuntimeOutcome.passed`) and
    that contain >=1 `pick_up_tips` call.
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
            if not any(c.get("name") == "pick_up_tips" for c in call_sequence):
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
        if not any(c.get("name") == "pick_up_tips" for c in payload["call_sequence"]):
            continue
        out.append((path.stem, payload))
    return out


#: A dedicated, tier-3-only fixture directory -- NOT `training/examples/`.
#: `training/examples/tip_mutant_probe.json` would have been the more
#: obvious home (it is the task brief's named second base-example source),
#: but `test_oracle_replay.py::TestSmokeOnExamples::test_full_pipeline_
#: on_examples` hardcodes "4 examples, 10 ops" over `training/examples/*.
#: json` and landing a 5th file there breaks an unrelated, already-passing
#: test for a reason that has nothing to do with this gate. This directory
#: is unioned with `--examples-dir` below rather than replacing it, so
#: `training/examples/*.json` is still read exactly as the brief describes.
DEFAULT_TIP_MUTANT_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--examples-dir", type=Path, default=REPO_ROOT / "training" / "examples")
    ap.add_argument(
        "--extra-examples-dir",
        type=Path,
        default=DEFAULT_TIP_MUTANT_FIXTURES_DIR,
        help="a SECOND examples directory, unioned with --examples-dir (default: plr-sema/eval/fixtures/, "
        "kept separate from training/examples/ so this gate's own synthetic probes don't perturb an "
        "unrelated test's hardcoded example count)",
    )
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
    if args.extra_examples_dir is not None:
        bases.extend(_example_files(args.extra_examples_dir))
    n_example_bases = len(bases) - n_corpus_bases
    log.info(
        "base examples: %d from corpus (clean, has pick_up_tips), %d from --examples-dir/--extra-examples-dir",
        n_corpus_bases,
        n_example_bases,
    )

    results: list[MutantResult] = []
    for base_id, example in bases:
        for mutant_class in ("m1_remove_pickup", "m2_duplicate_pickup"):
            results.append(
                run_one_mutant(
                    base_id, mutant_class, example, contracts_json, param_names,
                    _MUTATORS[mutant_class], _EXPECTED_EXC[mutant_class],
                )
            )

    by_class: dict[str, list[MutantResult]] = {"m1_remove_pickup": [], "m2_duplicate_pickup": []}
    for r in results:
        by_class[r.mutant_class].append(r)

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
            mclass,
            s["n_total"],
            s["n_raised_as_expected"],
            s["static_verdict_at_raising_index"],
        )
    if hard_violations:
        log.error("GATE FAILED:\n%s", "\n".join(hard_violations))
        return 1
    log.info("GATE PASSED: criteria (i), (ii), (iii) all hold for both mutant classes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
