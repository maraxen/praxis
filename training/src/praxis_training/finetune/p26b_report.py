"""Render the P2.6b decision tables from the committed reports (task
260902_p26b_surface_data). Pure formatting over JSON; every number in the
decision doc comes from here::

    python -m praxis_training.finetune.p26b_report \
        --old training/eval/reports/260902_p26_rescore_A.json \
        --new training/eval/reports/260902_p26b_A.json \
        --baseline training/eval/reports/260902_p26_rescore_baseline.json \
        --probe-old training/eval/reports/260902_p26b_probe_A.json \
        --probe-new training/eval/reports/260902_p26b_probe_A2.json \
        --out-json training/eval/reports/260902_p26b_predictions.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from praxis_training.finetune.failure_breakdown import breakdown_report
from praxis_training.finetune.p26b_predictions import evaluate_predictions

__all__ = ["decision_tables", "render_markdown", "main"]

PREDICTIONS = {
    "P1_surface6": ("surface6_recovered", 4, 6),
    "P2_verb_migration": ("verb_category_migrated", 11, 22),
    "P2b_discard_tips_pair": ("discard_tips_pair_exact", 1, 2),
}


def _stat(report: Mapping[str, Any], key: str) -> str:
    s = report[key]
    if s["value"] is None:
        return "n/a"
    lo, hi = s["wilson95"]
    return f"{s['value']:.3f} [{lo:.3f}, {hi:.3f}] ({s['successes']}/{s['n']})"


def decision_tables(old: Mapping[str, Any], new: Mapping[str, Any], *, baseline: Mapping[str, Any] | None = None,
                    probe_old: Mapping[str, Any] | None = None, probe_new: Mapping[str, Any] | None = None) -> dict[str, Any]:
    pred = evaluate_predictions(old, new)
    checks: dict[str, Any] = {}
    for name, (field, need, of) in PREDICTIONS.items():
        checks[name] = {"value": pred[field], "needed": need, "of": of, "holds": pred[field] >= need}
    acc_new = new["exact_match_accuracy"]["value"]
    rec_new = new["clarify_recall"]["value"]
    trip_new = new.get("tripwire_out_of_surface_tool_calls")
    checks["P3_no_regression"] = {
        "accuracy": acc_new, "accuracy_floor": old["exact_match_accuracy"]["value"],
        "recall": rec_new, "recall_floor": 0.705, "tripwire": trip_new, "tripwire_max": 1,
        "hit_to_miss": pred["flips_hit_to_miss"], "hit_to_miss_max": 5,
        "holds": (acc_new is not None and acc_new >= old["exact_match_accuracy"]["value"]
                  and rec_new is not None and rec_new >= 0.705 and (trip_new or 0) <= 1
                  and pred["flips_hit_to_miss"] <= 5),
    }
    if probe_old is not None and probe_new is not None:
        po, pn = probe_old["exact_match_accuracy"]["value"], probe_new["exact_match_accuracy"]["value"]
        checks["P4_probe"] = {"old": po, "new": pn, "delta": (pn or 0) - (po or 0), "needed_delta": 0.10,
                              "n": probe_new["n_examples"], "holds": (pn or 0) - (po or 0) >= 0.10}
    keys = ("exact_match_accuracy", "clarify_recall", "clarify_precision")
    out: dict[str, Any] = {
        "predictions": pred,
        "checks": checks,
        "headline": {
            "old": {k: _stat(old, k) for k in keys} | {"tripwire": old.get("tripwire_out_of_surface_tool_calls")},
            "new": {k: _stat(new, k) for k in keys} | {"tripwire": trip_new},
        },
        "per_class": {
            cls: {"old": old["per_class"][cls]["exact_match"]["successes"],
                  "new": new["per_class"][cls]["exact_match"]["successes"],
                  "n": new["per_class"][cls]["exact_match"]["n"]}
            for cls in sorted(new.get("per_class", {}))
        },
        "breakdown_new": breakdown_report(new)["by_category"],
        "breakdown_old": breakdown_report(old)["by_category"],
        "exploratory": {
            "vague3_recovered": pred["vague3_recovered"],
            "hallucinated4_recovered": pred["hallucinated4_recovered"],
            "golden_misses_old": sum(1 for r in old["exact_match_failures"] if r["record_id"].startswith("golden-")),
            "golden_misses_new": sum(1 for r in new["exact_match_failures"] if r["record_id"].startswith("golden-")),
        },
    }
    if baseline is not None:
        out["headline"]["baseline"] = {k: _stat(baseline, k) for k in keys} | {"tripwire": baseline.get("tripwire_out_of_surface_tool_calls")}
    return out


def render_markdown(t: Mapping[str, Any]) -> str:
    lines = ["| model | exact match | clarify recall | clarify precision | tripwire |", "|---|---|---|---|---|"]
    labels = {"baseline": "baseline v2", "old": "A (P2.6, corpus 0.1.3)", "new": "A2 (P2.6b, corpus 0.1.4)"}
    for name in ("baseline", "old", "new"):
        if name in t["headline"]:
            h = t["headline"][name]
            lines.append(f"| {labels[name]} | {h['exact_match_accuracy']} | {h['clarify_recall']} | {h['clarify_precision']} | {h['tripwire']} |")
    lines += ["", "| prediction | value | needed | holds |", "|---|---|---|---|"]
    for name, c in t["checks"].items():
        if name.startswith("P3"):
            lines.append(f"| P3 no regression | acc {c['accuracy']:.3f} (>= {c['accuracy_floor']:.3f}), recall {c['recall']:.3f} (>= 0.705), "
                         f"tripwire {c['tripwire']} (<= 1), hit->miss {c['hit_to_miss']} (<= 5) | all | {c['holds']} |")
        elif name.startswith("P4"):
            lines.append(f"| P4 probe (n={c['n']}) | A {c['old']:.3f} -> A2 {c['new']:.3f} (delta {c['delta']:+.3f}) | >= +0.10 | {c['holds']} |")
        else:
            lines.append(f"| {name} | {c['value']}/{c['of']} | >= {c['needed']} | {c['holds']} |")
    lines += ["", "| class | A | A2 | n |", "|---|---|---|---|"]
    for cls, v in t["per_class"].items():
        lines.append(f"| {cls} | {v['old']} | {v['new']} | {v['n']} |")
    lines += ["", f"Residual categories A2: {t['breakdown_new']}", f"Exploratory: {t['exploratory']}",
              f"Flips hit->miss: {t['predictions']['flips_hit_to_miss_ids']}",
              f"Verb rows migrated: {t['predictions']['verb_category_migrated_ids']}"]
    return "\n".join(lines) + "\n"


def _load(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m praxis_training.finetune.p26b_report")
    ap.add_argument("--old", type=Path, required=True)
    ap.add_argument("--new", type=Path, required=True)
    ap.add_argument("--baseline", type=Path, default=None)
    ap.add_argument("--probe-old", type=Path, default=None)
    ap.add_argument("--probe-new", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    a = ap.parse_args(argv)
    t = decision_tables(_load(a.old), _load(a.new), baseline=_load(a.baseline) if a.baseline else None,
                        probe_old=_load(a.probe_old) if a.probe_old else None,
                        probe_new=_load(a.probe_new) if a.probe_new else None)
    if a.out_json:
        a.out_json.parent.mkdir(parents=True, exist_ok=True)
        a.out_json.write_text(json.dumps(t, indent=2) + "\n", encoding="utf-8")
    print(render_markdown(t))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
