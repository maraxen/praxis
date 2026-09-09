"""Compare two ``baseline_eval`` reports row-by-row and check a re-score
against its pre-registered prediction (task 260902_p26_rescore).

Two jobs, both pure functions over report JSON:

``compare_reports(a, b)``
    Which rows fail in one report but not the other, whether the clarify
    metrics (recall / precision / confusion / tripwire) are identical, and
    the exact-match successes on each side. Used twice: as the REPRODUCTION
    CONTROL (committed report vs the OLD scorer over a fresh generations
    dump -- expected identical on matching hardware) and as the FLIP TABLE
    (old scorer vs new scorer over the SAME dump).

``check_prediction(old, new, prediction)``
    The pre-registered row-level prediction for a scorer fix: (i) no row
    flips hit->miss, (ii) every miss->hit row is in the breakdown's artifact
    set, (iii) clarify metrics are identical (they depend on neither params
    nor slots; the baseline v2 report predates the tripwire field, so a
    field that APPEARS with the value the breakdown reconstructs is allowed),
    (iv) n_examples unchanged. Rows the breakdown predicted would flip but did
    not are reported separately as ``predicted_but_still_missed``: a
    classifier shortfall, not a scorer deviation.

Reports carry only FAILED rows (``exact_match_failures``); success sets are
therefore derived as complement over the record_ids the caller supplies (the
prediction JSON) or, for compare_reports, as "failed on the other side only".
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

__all__ = ["compare_reports", "check_prediction", "prediction_from_breakdown", "main"]

_CLARIFY_KEYS = ("clarify_recall", "clarify_precision")


def _failed_ids(report: Mapping[str, Any]) -> set[str]:
    return {row["record_id"] for row in report.get("exact_match_failures", [])}


def _stat_triplet(report: Mapping[str, Any], key: str) -> tuple[Any, Any, Any]:
    s = report[key]
    return (s.get("value"), s.get("successes"), s.get("n"))


def compare_reports(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    """Row-level diff of two reports scored on the same split."""
    if a["n_examples"] != b["n_examples"]:
        raise ValueError(f"n_examples differ: {a['n_examples']} vs {b['n_examples']} -- not the same split")
    fa, fb = _failed_ids(a), _failed_ids(b)
    trip_a = a.get("tripwire_out_of_surface_tool_calls")
    trip_b = b.get("tripwire_out_of_surface_tool_calls")
    clarify_identical = all(_stat_triplet(a, k) == _stat_triplet(b, k) for k in _CLARIFY_KEYS) and (
        a.get("clarify_confusion") == b.get("clarify_confusion")
    )
    tripwire_identical = trip_a == trip_b
    return {
        "n_examples": a["n_examples"],
        "successes_a": a["exact_match_accuracy"]["successes"],
        "successes_b": b["exact_match_accuracy"]["successes"],
        "accuracy_a": a["exact_match_accuracy"]["value"],
        "accuracy_b": b["exact_match_accuracy"]["value"],
        "failed_only_in_a": sorted(fa - fb),   # hit in b, miss in a
        "failed_only_in_b": sorted(fb - fa),   # hit in a, miss in b
        "failed_in_both": len(fa & fb),
        "clarify_identical": clarify_identical,
        "tripwire_a": trip_a,
        "tripwire_b": trip_b,
        "tripwire_identical": tripwire_identical,
        "identical": not (fa ^ fb) and clarify_identical and tripwire_identical,
    }


def check_prediction(
    old: Mapping[str, Any],
    new: Mapping[str, Any],
    prediction: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply the pre-registered prediction to an (old scorer, new scorer) pair.

    ``prediction`` is one entry of the prediction JSON written before the
    scorer changed: ``{"artifact_record_ids": [...], "expected_tripwire": int|None}``.
    """
    diff = compare_reports(old, new)
    artifact_ids = set(prediction.get("artifact_record_ids", ()))
    hit_to_miss = diff["failed_only_in_b"]
    miss_to_hit = diff["failed_only_in_a"]
    unpredicted = sorted(set(miss_to_hit) - artifact_ids)
    still_missed = sorted(artifact_ids - set(miss_to_hit))
    expected_trip = prediction.get("expected_tripwire")
    if diff["tripwire_a"] is None:
        # Legacy report without the field: the new one must carry the value
        # the breakdown reconstructs (baseline v2: 44 - 31 = 13).
        tripwire_ok = expected_trip is None or diff["tripwire_b"] == expected_trip
    else:
        tripwire_ok = diff["tripwire_identical"]
    holds = (
        not hit_to_miss
        and not unpredicted
        and diff["clarify_identical"]
        and tripwire_ok
    )
    return {
        "prediction_holds": holds,
        "n_examples": diff["n_examples"],
        "successes_old": diff["successes_a"],
        "successes_new": diff["successes_b"],
        "accuracy_old": diff["accuracy_a"],
        "accuracy_new": diff["accuracy_b"],
        "artifact_rows_predicted": len(artifact_ids),
        "flips_miss_to_hit": len(miss_to_hit),
        "flips_hit_to_miss": hit_to_miss,
        "flips_miss_to_hit_unpredicted": unpredicted,
        "predicted_but_still_missed": still_missed,
        "clarify_identical": diff["clarify_identical"],
        "tripwire_old": diff["tripwire_a"],
        "tripwire_new": diff["tripwire_b"],
        "tripwire_ok": tripwire_ok,
    }


def prediction_from_breakdown(report: Mapping[str, Any], breakdown: Mapping[str, Any]) -> dict[str, Any]:
    """The pre-registered prediction for one model, from its OLD-scorer report
    and that report's ``failure_breakdown`` result: the artifact rows are the
    only rows allowed to flip miss->hit; the tripwire must stay (or, for a
    legacy report without the field, appear as the per_class reconstruction
    out_of_surface n - exact successes)."""
    ids = sorted({rid for rids in breakdown["artifact_record_ids"].values() for rid in rids})
    trip = report.get("tripwire_out_of_surface_tool_calls")
    if trip is None:
        oos = report.get("per_class", {}).get("out_of_surface")
        if oos is not None:
            trip = oos["exact_match"]["n"] - oos["exact_match"]["successes"]
    successes = int(report["exact_match_accuracy"]["successes"])
    n = int(report["n_examples"])
    return {
        "n_examples": n,
        "successes_old": successes,
        "artifact_record_ids": ids,
        "artifact_rows": len(ids),
        "expected_successes_max": successes + len(ids),
        "expected_accuracy_ceiling": (successes + len(ids)) / n if n else None,
        "expected_tripwire": trip,
        "by_category": dict(breakdown["by_category"]),
    }


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m praxis_training.finetune.rescore_check")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare", help="row-level diff of two reports")
    c.add_argument("--a", type=Path, required=True)
    c.add_argument("--b", type=Path, required=True)
    c.add_argument("--out-json", type=Path, default=None)
    k = sub.add_parser("check", help="apply a pre-registered prediction to (old, new)")
    k.add_argument("--old", type=Path, required=True)
    k.add_argument("--new", type=Path, required=True)
    k.add_argument("--prediction", type=Path, required=True, help="prediction JSON")
    k.add_argument("--model", required=True, help="key into the prediction JSON's 'models'")
    k.add_argument("--out-json", type=Path, default=None)
    pr = sub.add_parser("predict", help="build the prediction JSON from old-scorer reports")
    pr.add_argument("--report", action="append", required=True, metavar="NAME=REPORT.json")
    pr.add_argument("--out-json", type=Path, required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.cmd == "compare":
        result = compare_reports(_load(args.a), _load(args.b))
    elif args.cmd == "predict":
        from praxis_training.finetune.failure_breakdown import ARTIFACT_CATEGORIES, breakdown_report

        models: dict[str, Any] = {}
        for spec in args.report:
            name, _, path = spec.partition("=")
            if not path:
                raise SystemExit(f"--report expects NAME=path, got {spec!r}")
            rep = _load(Path(path))
            models[name] = prediction_from_breakdown(rep, breakdown_report(rep)) | {"source": path}
        result = {"artifact_categories": list(ARTIFACT_CATEGORIES), "models": models}
    else:
        pred = _load(args.prediction)["models"][args.model]
        result = check_prediction(_load(args.old), _load(args.new), pred)
    text = json.dumps(result, indent=2)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
