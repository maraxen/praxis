"""Spec 260904 §15.10 (`260904_plr-sema-predicate-increment.md`, increment 6,
backlog #4979, T32): the predicate-arity mutant class (p1), tier 3.

Adopted at tier 3 (the spec's own normative box, §15.10): three mutators over
a *planned* `pick_up_tips` call's already-GROUNDED PLR kwargs
(`PlanResult.kwargs`, `training/verify/dispatcher.py`'s own per-call dict --
never the WIRE-level `call.params`, which for `pick_up_tips` exposes only
`at` per `coxswain.plr.param_namespace.PARAM_NAMESPACE`; `use_channels`/
`offsets` have no wire-level schema entry at all, so a wire-level mutation
could never reach them and an unknown wire param would be REJECTED by
`plan_call`'s own STRICT-mode gate before grounding ever ran):

* **(a) `p1a_duplicate_use_channels`.** Injects an explicit `use_channels`
  kwarg with a duplicated entry (`[0, 0]`), violating `:502`'s
  `assert len(set(use_channels)) == len(use_channels)`
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:502`).
  Constructible on every base row -- the guard is a pure self-uniqueness
  test over `use_channels`, independent of `tip_spots`. This is the
  **stub-defeating** mutator (§15.10's own note): it fires against an
  `assert`-kind guard, so an implementation that kept increment 1's
  `raise_guard`-only restriction (G6) would pass (b)/(c) and fail (a).
* **(b) `p1b_short_offsets`.** Injects an explicit `offsets` kwarg one
  element SHORT of `tip_spots` (but non-empty, so E-CALL(β)'s
  known-truthy branch resolves it to the caller's value rather than to the
  β length -- §15.10's own note on why this mutant "survives E-CALL(β)
  explicitly"), violating `:522`'s chained
  `assert len(tip_spots) == len(offsets) == len(use_channels)`. Declines
  (mutation not constructed) when `len(tip_spots) < 2`, since a
  one-shorter-but-non-empty list does not exist below that.
* **(c) `p1c_non_tipspot_element`.** Replaces the first `tip_spots` element
  with a plain non-`TipSpot` object, violating `:496-498`'s `isinstance`
  filter and raising `TypeError` at RUNTIME. Per §15.10's own restated
  E-TYPE (a `_generic_plr_type_name`-derived declaration is never exact),
  the STATIC side cannot decide this to `WILL_FAIL` -- it can only reach
  ½ -- so this mutator's own floor is **0 achieved, 0 unsound**, asserted
  as such below (a `WILL_FAIL` here would be the C4 false-`WILL_FAIL`
  mechanism reappearing, per increment 6 §15.1.2's own history).

Each mutant is run through BOTH the real verifier (`training/verify`,
ground truth -- the mutated kwargs are what the chatterbox actually
executes) and the static analyzer (`lower_calls` -> `check_ir`, via
`oracle_common.run_static_calls`), reusing `tip_mutants.run_one_mutant`'s
own `(base_id, mutant_class, ran, error, ...)` result shape (`MutantResult`)
so this module's report is directly comparable to `tip_mutants_*.json`/
`volume_mutants_*.json` -- imported, not redefined.

Base examples are the SAME two sources `tip_mutants.py`/`volume_mutants.py`
use: corpus rows the tier-1 replay executes CLEAN and that contain a
`pick_up_tips` call, plus `training/examples/*.json` fixtures containing one
(`tip_mutants._clean_corpus_examples`/`_example_files`, imported directly).

Usage::

    uv run python plr-sema/eval/predicate_mutants.py \\
        --corpus training/assemble/out/corpus_p25.jsonl \\
        --examples-dir training/examples \\
        --contracts plr-sema/data/derived_contracts.json \\
        --report /tmp/predicate_mutants_report.json \\
        --limit 300
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "eval"))
sys.path.insert(0, str(REPO_ROOT / "plr-sema" / "src"))

import oracle_common as oc  # noqa: E402
from tip_mutants import (  # noqa: E402
    MutantResult,
    _clean_corpus_examples,
    _example_files,
)

log = logging.getLogger("predicate_mutants")

DEFAULT_CONTRACTS = REPO_ROOT / "plr-sema" / "data" / "derived_contracts.json"

_TARGET_CALL = "pick_up_tips"

_EXPECTED_EXC = {
    "p1a_duplicate_use_channels": "AssertionError",
    "p1b_short_offsets": "AssertionError",
    "p1c_non_tipspot_element": "TypeError",
}

#: §15.10's own normative box: (c) is asserted 0 achieved / 0 unsound under
#: the restated E-TYPE (a `_generic_plr_type_name`-derived declaration is
#: never exact); the floor of >=1 achieved `WILL_FAIL` is carried by (a)/(b)
#: alone. A mutator NOT in this set is held to the usual floor >= 1.
_ZERO_ACHIEVED_EXPECTED = {"p1c_non_tipspot_element"}


def make_p1a_duplicate_use_channels(kwargs: dict[str, Any]) -> bool:
    """Always constructible: `:502`'s guard is a pure self-uniqueness test
    over `use_channels`, independent of `tip_spots`."""
    kwargs["use_channels"] = [0, 0]
    return True


def make_p1b_short_offsets(kwargs: dict[str, Any]) -> bool:
    """Declines (returns False) when `tip_spots` has fewer than 2 elements
    -- a one-shorter-but-non-empty list does not exist below that ("skip,
    don't guess", the same discipline `tip_mutants.make_m1_remove_pickup`
    follows for its own missing-precondition case)."""
    from pylabrobot.resources import Coordinate

    tip_spots = kwargs.get("tip_spots")
    if not isinstance(tip_spots, (list, tuple)) or len(tip_spots) < 2:
        return False
    kwargs["offsets"] = [Coordinate.zero()] * (len(tip_spots) - 1)
    return True


def make_p1c_non_tipspot_element(kwargs: dict[str, Any]) -> bool:
    """Declines when `tip_spots` is empty or not a list/tuple."""
    tip_spots = kwargs.get("tip_spots")
    if not isinstance(tip_spots, (list, tuple)) or len(tip_spots) < 1:
        return False
    mutated = list(tip_spots)
    mutated[0] = object()
    kwargs["tip_spots"] = mutated
    return True


_MUTATORS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "p1a_duplicate_use_channels": make_p1a_duplicate_use_channels,
    "p1b_short_offsets": make_p1b_short_offsets,
    "p1c_non_tipspot_element": make_p1c_non_tipspot_element,
}


def run_one_predicate_mutant(
    base_id: str,
    mutant_class: str,
    example: dict[str, Any],
    contracts_json: str,
    param_names: Any,
    kwargs_mutator: Callable[[dict[str, Any]], bool],
    expected_exc: str,
) -> MutantResult:
    """Mutates the FIRST `_TARGET_CALL` (`pick_up_tips`) call's grounded
    `PlanResult.kwargs` in place, mirroring `oracle_common.run_runtime`'s
    own `recording_plan_call` monkeypatch of `verifier.plan_call` with one
    extra step: right after the REAL `plan_call` grounds the target call
    (past the wire-level STRICT/unknown-param gate, which never sees
    `use_channels`/`offsets` because they are not in `plan_call`'s own
    schema for this tool -- see this module's docstring), `kwargs_mutator`
    mutates `plan_result.kwargs` in place BEFORE `verify()`'s own
    `await plan.method(**plan.kwargs)` runs. The runtime therefore executes
    the mutated kwargs for real, and `rt.plr_kwargs`-equivalent capture
    (`oc.ir_value_of` over the SAME already-mutated `plan_result.kwargs`)
    feeds the identical mutated arguments to the static side, so runtime and
    static reason about exactly the same call.

    Returns a `tip_mutants.MutantResult` -- same shape `tip_mutants.py`/
    `volume_mutants.py` already publish, so all three modules' reports are
    directly comparable field-for-field.
    """
    verifier = oc._import_verifier()
    real_plan_call = verifier.plan_call

    target_idx: int | None = None
    mutation_applied = False
    plr_kwargs: dict[int, dict[str, Any]] = {}

    def recording_plan_call(call, index, setup, *, strict):
        nonlocal target_idx, mutation_applied
        plan_result = real_plan_call(call, index, setup, strict=strict)
        if call.get("name") == _TARGET_CALL and target_idx is None:
            if kwargs_mutator(plan_result.kwargs):
                target_idx = index
                mutation_applied = True
        if hasattr(plan_result, "kwargs"):
            plr_kwargs[index] = {k: oc.ir_value_of(v) for k, v in plan_result.kwargs.items()}
        return plan_result

    verifier.plan_call = recording_plan_call
    sink = io.StringIO()
    try:
        with contextlib.redirect_stdout(sink):
            result = asyncio.run(
                verifier.verify(
                    example["call_sequence"],
                    example["intent_record"],
                    layout=example.get("deck_layout"),
                    backend=example.get("backend", "LiquidHandlerChatterboxBackend"),
                )
            )
    except Exception as e:
        verifier.plan_call = real_plan_call
        return MutantResult(base_id, mutant_class, False, f"runtime_harness:{e}", None, False, None, None, False, False)
    finally:
        verifier.plan_call = real_plan_call

    if not mutation_applied:
        return MutantResult(base_id, mutant_class, False, "mutation could not be constructed", None, False, None, None, False, False)

    error = result.get("error")
    exc_class = error.split(":", 1)[0].strip() if error else None
    raising_index = target_idx if error else None
    raised_as_expected = exc_class == expected_exc

    try:
        st, _not_planned = oc.run_static_calls(
            example, plr_kwargs, contracts_json, param_names=param_names,
            volume_tracking_observed=bool(result.get("volume_tracking_observed")),
        )
    except Exception as e:
        return MutantResult(
            base_id, mutant_class, True, f"static:{e}", exc_class, raised_as_expected, raising_index, None, False, False
        )

    static_verdict_at_index = None
    if raising_index is not None:
        entry = st.get(f"op_{raising_index}")
        static_verdict_at_index = entry["verdict"] if entry is not None else None

    # (i): simulator raised the expected exception at this index, but the
    # static verdict there is SAFE -- unsound.
    unsound_safe = raised_as_expected and static_verdict_at_index == "safe"

    # (ii): simulator ran an op clean but the static verdict there is
    # WILL_FAIL.
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
        "base examples: %d from corpus (clean, has pick_up_tips), %d from --examples-dir",
        n_corpus_bases, n_example_bases,
    )

    results: list[MutantResult] = []
    for base_id, example in bases:
        for mutant_class in ("p1a_duplicate_use_channels", "p1b_short_offsets", "p1c_non_tipspot_element"):
            results.append(
                run_one_predicate_mutant(
                    base_id, mutant_class, example, contracts_json, param_names,
                    _MUTATORS[mutant_class], _EXPECTED_EXC[mutant_class],
                )
            )

    by_class: dict[str, list[MutantResult]] = {
        "p1a_duplicate_use_channels": [], "p1b_short_offsets": [], "p1c_non_tipspot_element": [],
    }
    for r in results:
        by_class[r.mutant_class].append(r)

    summary: dict[str, Any] = {}
    hard_violations: list[str] = []

    for mclass, rows in by_class.items():
        ran = [r for r in rows if r.ran and r.error is None]
        raised_as_expected = [r for r in ran if r.raised_as_expected]
        verdict_counts = {"will_fail": 0, "unknown": 0, "safe": 0, "none": 0}
        for r in raised_as_expected:
            key = r.static_verdict_at_index or "none"
            verdict_counts[key] = verdict_counts.get(key, 0) + 1

        unsound_safe_rows = [r.base_id for r in ran if r.unsound_safe]
        unsound_will_fail_rows = [r.base_id for r in ran if r.unsound_will_fail_elsewhere]
        n_achieved = verdict_counts.get("will_fail", 0)

        summary[mclass] = {
            "n_total": len(rows),
            "n_construction_skipped": len(rows) - len(ran) - sum(1 for r in rows if r.ran and r.error),
            "n_error": sum(1 for r in rows if r.error is not None),
            "n_ran": len(ran),
            "n_raised_as_expected": len(raised_as_expected),
            "static_verdict_at_raising_index": verdict_counts,
            "n_achieved_will_fail_at_raised_index": n_achieved,
            "unsound_safe_where_simulator_raised": unsound_safe_rows,
            "unsound_will_fail_where_simulator_ran_clean": unsound_will_fail_rows,
            "n_unsound": len(unsound_safe_rows) + len(unsound_will_fail_rows),
        }

        if unsound_safe_rows:
            hard_violations.append(
                f"{mclass}: criterion (i) VIOLATED -- {len(unsound_safe_rows)} row(s) static SAFE where simulator raised: {unsound_safe_rows[:5]}"
            )
        if unsound_will_fail_rows:
            hard_violations.append(
                f"{mclass}: criterion (ii) VIOLATED -- {len(unsound_will_fail_rows)} row(s) static WILL_FAIL where simulator ran clean: {unsound_will_fail_rows[:5]}"
            )

        if mclass in _ZERO_ACHIEVED_EXPECTED:
            # §15.10's own restated-E-TYPE prediction: 0 achieved / 0
            # unsound. A WILL_FAIL here is a FAILURE (the C4 false-positive
            # mechanism reappearing), not a bonus.
            if n_achieved > 0:
                hard_violations.append(
                    f"{mclass}: expected 0 achieved WILL_FAIL under the restated E-TYPE (never-exact "
                    f"declarations), got {n_achieved} -- this is the C4 false-WILL_FAIL mechanism "
                    f"reappearing, not a stronger result: {verdict_counts}"
                )
        else:
            if n_achieved < 1:
                hard_violations.append(
                    f"{mclass}: floor FAILED -- 0 achieved WILL_FAIL at the raised index "
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
            "%s: n=%d raised_as_expected=%d achieved=%d unsound=%d static_at_index=%s",
            mclass, s["n_total"], s["n_raised_as_expected"],
            s["n_achieved_will_fail_at_raised_index"], s["n_unsound"],
            s["static_verdict_at_raising_index"],
        )
    if hard_violations:
        log.error("GATE FAILED:\n%s", "\n".join(hard_violations))
        return 1
    log.info(
        "GATE PASSED: (a)/(b) achieve >=1 WILL_FAIL at the raised index with 0 unsound; "
        "(c) achieves 0/0 as predicted by the restated E-TYPE."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
