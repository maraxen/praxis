"""Render the P2.6c decision tables from the committed reports (task
260903_p26c_oos_natural). Pure formatting over JSON; every number in the
decision doc comes from here::

    python -m praxis_training.finetune.p26c_report \
        --control training/eval/reports/260902_p26b_A.json \
        --new training/eval/reports/260903_p26c_A3.json \
        --baseline training/eval/reports/260902_p26_rescore_baseline.json \
        --prev training/eval/reports/260902_p26_rescore_A.json \
        --probe-control training/eval/reports/260903_p26c_probe_A2.json \
        --probe-new training/eval/reports/260903_p26c_probe_A3.json \
        --out-json training/eval/reports/260903_p26c_predictions.json

Pre-registered checks (prereg §3): P1 tripwire <= 1 AND tripwire3_recovered >= 2;
P2 exact >= control, recall >= 0.705, hit->miss <= 5; P3 surface6 >= 4/6,
in-surface probe >= 0.80, verb22 >= 11/22; P4 oos-probe delta >= +0.10 (secondary);
P5 exploratory (ambig4, golden misses).
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from praxis_training.finetune.failure_breakdown import breakdown_report
from praxis_training.finetune.p26c_predictions import evaluate_predictions, probe_split

__all__ = ["decision_tables", "render_markdown", "main"]

RECALL_FLOOR = 0.705
TRIPWIRE_MAX = 1
TRIPWIRE3_NEEDED = 2
FLIPS_MAX = 5
SURFACE6_NEEDED = 4
VERB22_NEEDED = 11
IN_SURFACE_PROBE_FLOOR = 0.80
OOS_PROBE_DELTA = 0.10


def _stat(report: Mapping[str, Any], key: str) -> str:
    s = report[key]
    if s["value"] is None:
        return "n/a"
    lo, hi = s["wilson95"]
    return f"{s['value']:.3f} [{lo:.3f}, {hi:.3f}] ({s['successes']}/{s['n']})"


def decision_tables(
    control: Mapping[str, Any],
    new: Mapping[str, Any],
    *,
    baseline: Mapping[str, Any] | None = None,
    prev: Mapping[str, Any] | None = None,
    probe_control: Mapping[str, Any] | None = None,
    probe_new: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    pred = evaluate_predictions(control, new)
    acc_new = new["exact_match_accuracy"]["value"]
    acc_ctl = control["exact_match_accuracy"]["value"]
    rec_new = new["clarify_recall"]["value"]
    trip_new = new.get("tripwire_out_of_surface_tool_calls")
    checks: dict[str, Any] = {
        "P1_tripwire": {
            "tripwire": trip_new, "tripwire_max": TRIPWIRE_MAX,
            "tripwire3_recovered": pred["tripwire3_recovered"], "tripwire3_needed": TRIPWIRE3_NEEDED,
            "holds": (trip_new or 0) <= TRIPWIRE_MAX and pred["tripwire3_recovered"] >= TRIPWIRE3_NEEDED,
        },
        "P2_no_regression": {
            "accuracy": acc_new, "accuracy_floor": acc_ctl, "recall": rec_new, "recall_floor": RECALL_FLOOR,
            "hit_to_miss": pred["flips_hit_to_miss"], "hit_to_miss_max": FLIPS_MAX,
            "holds": (acc_new is not None and acc_new >= acc_ctl and rec_new is not None
                      and rec_new >= RECALL_FLOOR and pred["flips_hit_to_miss"] <= FLIPS_MAX),
        },
    }
    p3: dict[str, Any] = {
        "surface6_retained": pred["surface6_retained"], "surface6_needed": SURFACE6_NEEDED,
        "verb22_retained": pred["verb22_retained"], "verb22_needed": VERB22_NEEDED,
    }
    p3_holds = pred["surface6_retained"] >= SURFACE6_NEEDED and pred["verb22_retained"] >= VERB22_NEEDED
    if probe_new is not None:
        sp = probe_split(probe_new)
        p3 |= {"in_surface_probe": sp["in_surface_probe_exact_match_accuracy"],
               "in_surface_probe_n": sp["in_surface_probe_n"], "in_surface_probe_floor": IN_SURFACE_PROBE_FLOOR}
        p3_holds = p3_holds and (sp["in_surface_probe_exact_match_accuracy"] or 0) >= IN_SURFACE_PROBE_FLOOR
    checks["P3_surface_retained"] = p3 | {"holds": p3_holds}
    if probe_control is not None and probe_new is not None:
        so, sn = probe_split(probe_control), probe_split(probe_new)
        delta = (sn["oos_probe_exact_match_accuracy"] or 0) - (so["oos_probe_exact_match_accuracy"] or 0)
        checks["P4_oos_probe"] = {
            "control": so["oos_probe_exact_match_accuracy"], "new": sn["oos_probe_exact_match_accuracy"],
            "n": sn["oos_probe_n"], "delta": delta, "needed_delta": OOS_PROBE_DELTA, "holds": delta >= OOS_PROBE_DELTA,
        }
    keys = ("exact_match_accuracy", "clarify_recall", "clarify_precision")

    def head(r: Mapping[str, Any]) -> dict[str, Any]:
        return {k: _stat(r, k) for k in keys} | {"tripwire": r.get("tripwire_out_of_surface_tool_calls")}

    out: dict[str, Any] = {
        "predictions": pred,
        "checks": checks,
        "headline": {"control": head(control), "new": head(new)},
        "per_class": {
            cls: {"control": control["per_class"][cls]["exact_match"]["successes"],
                  "new": new["per_class"][cls]["exact_match"]["successes"],
                  "n": new["per_class"][cls]["exact_match"]["n"]}
            for cls in sorted(new.get("per_class", {}))
        },
        "breakdown_new": breakdown_report(new)["by_category"],
        "breakdown_control": breakdown_report(control)["by_category"],
        "exploratory": {
            "ambig4_recovered": pred["ambig4_recovered"],
            "ambig4_recovered_ids": pred["ambig4_recovered_ids"],
            "oos44_exact_control": pred["oos44_exact_old"],
            "oos44_exact_new": pred["oos44_exact_new"],
            "golden_misses_control": sum(1 for r in control["exact_match_failures"] if r["record_id"].startswith("golden-")),
            "golden_misses_new": sum(1 for r in new["exact_match_failures"] if r["record_id"].startswith("golden-")),
        },
    }
    if baseline is not None:
        out["headline"]["baseline"] = head(baseline)
    if prev is not None:
        out["headline"]["prev"] = head(prev)
    if probe_control is not None and probe_new is not None:
        out["probe"] = {"control": probe_split(probe_control), "new": probe_split(probe_new)}
    return out


def render_markdown(t: Mapping[str, Any]) -> str:
    lines = ["| model | exact match | clarify recall | clarify precision | tripwire |", "|---|---|---|---|---|"]
    labels = {"baseline": "baseline v2", "prev": "A (P2.6, corpus 0.1.3)",
              "control": "A2 (P2.6b, corpus 0.1.4)", "new": "A3 (P2.6c, corpus 0.1.5)"}
    for name in ("baseline", "prev", "control", "new"):
        if name in t["headline"]:
            h = t["headline"][name]
            lines.append(f"| {labels[name]} | {h['exact_match_accuracy']} | {h['clarify_recall']} | {h['clarify_precision']} | {h['tripwire']} |")
    lines += ["", "| prediction | value | needed | holds |", "|---|---|---|---|"]
    c = t["checks"]
    p1 = c["P1_tripwire"]
    lines.append(f"| P1 tripwire | tripwire {p1['tripwire']}, tripwire3 recovered {p1['tripwire3_recovered']}/3 | <= {p1['tripwire_max']} and >= {p1['tripwire3_needed']}/3 | {p1['holds']} |")
    p2 = c["P2_no_regression"]
    lines.append(f"| P2 no regression vs A2 | acc {p2['accuracy']:.3f} (>= {p2['accuracy_floor']:.3f}), recall {p2['recall']:.3f} (>= {p2['recall_floor']}), hit->miss {p2['hit_to_miss']} (<= {p2['hit_to_miss_max']}) | all | {p2['holds']} |")
    p3 = c["P3_surface_retained"]
    probe_txt = f", in-surface probe {p3['in_surface_probe']:.3f} (>= {p3['in_surface_probe_floor']}, n={p3['in_surface_probe_n']})" if "in_surface_probe" in p3 and p3["in_surface_probe"] is not None else ""
    lines.append(f"| P3 surface gains retained | surface6 {p3['surface6_retained']}/6 (>= {p3['surface6_needed']}), verb22 {p3['verb22_retained']}/22 (>= {p3['verb22_needed']}){probe_txt} | all | {p3['holds']} |")
    if "P4_oos_probe" in c:
        p4 = c["P4_oos_probe"]
        lines.append(f"| P4 oos probe (n={p4['n']}) | A2 {p4['control']:.3f} -> A3 {p4['new']:.3f} (delta {p4['delta']:+.3f}) | >= +{p4['needed_delta']:.2f} | {p4['holds']} |")
    lines += ["", "| class | A2 | A3 | n |", "|---|---|---|---|"]
    for cls, v in t["per_class"].items():
        lines.append(f"| {cls} | {v['control']} | {v['new']} | {v['n']} |")
    lines += ["", f"Residual categories A3: {t['breakdown_new']}", f"Exploratory: {t['exploratory']}",
              f"Flips hit->miss (A2 -> A3): {t['predictions']['flips_hit_to_miss_ids']}",
              f"Flips miss->hit (A2 -> A3): {t['predictions']['flips_miss_to_hit_ids']}"]
    return "\n".join(lines) + "\n"


def _load(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m praxis_training.finetune.p26c_report")
    ap.add_argument("--control", type=Path, required=True)
    ap.add_argument("--new", type=Path, required=True)
    ap.add_argument("--baseline", type=Path, default=None)
    ap.add_argument("--prev", type=Path, default=None)
    ap.add_argument("--probe-control", type=Path, default=None)
    ap.add_argument("--probe-new", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    a = ap.parse_args(argv)
    opt = lambda p: _load(p) if p else None  # noqa: E731
    t = decision_tables(_load(a.control), _load(a.new), baseline=opt(a.baseline), prev=opt(a.prev),
                        probe_control=opt(a.probe_control), probe_new=opt(a.probe_new))
    if a.out_json:
        a.out_json.parent.mkdir(parents=True, exist_ok=True)
        a.out_json.write_text(json.dumps(t, indent=2) + "\n", encoding="utf-8")
    print(render_markdown(t))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
