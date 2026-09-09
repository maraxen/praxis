"""Render the P2.6d decision tables from the committed reports (task
260903_p26d_near_surface, backlog 4940). Pure formatting over JSON; every
number in the decision doc comes from here::

    python -m praxis_training.finetune.p26d_report \
        --control training/eval/reports/260903_p26c_A3.json \
        --new training/eval/reports/260903_p26d_A4.json \
        --baseline training/eval/reports/260902_p26_rescore_baseline.json \
        --prev training/eval/reports/260902_p26b_A.json \
        --probe-control training/eval/reports/260903_p26c_probe_A3.json \
        --probe-new training/eval/reports/260903_p26d_probe_A4.json \
        --near-control training/eval/reports/260903_p26d_near_A3.json \
        --near-new training/eval/reports/260903_p26d_near_A4.json \
        --out-json training/eval/reports/260903_p26d_predictions.json

Pre-registered checks (prereg §3) are the P2.6c checks with A3 as control and
A4 as new (``p26c_report.decision_tables`` is reused unchanged: P1 tripwire
<= 1 AND tripwire3_recovered >= 2; P2 exact >= control, recall >= 0.705,
hit->miss <= 5; P3 surface6 >= 4/6, in-surface probe >= 0.80, verb22 >= 11/22).
P4 here is the NEAR-SURFACE probe (24 held-out rows of the six new cells,
scored by the baseline_eval CLI): abstention exact-match rises by >= 0.10 over
A3 unless A3 is already at or above the ceiling 0.90, in which case P4 is void
(recorded, not gated). The natural oos probe of P2.6c is reported as
exploratory only.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from praxis_training.finetune.p26c_report import decision_tables as _p26c_tables

__all__ = ["NEAR_PROBE_DELTA", "NEAR_PROBE_CEILING", "decision_tables", "render_markdown", "main"]

NEAR_PROBE_DELTA = 0.10
NEAR_PROBE_CEILING = 0.90

LABELS = {"baseline": "baseline v2", "prev": "A2 (P2.6b, corpus 0.1.4)",
          "control": "A3 (P2.6c, corpus 0.1.5)", "new": "A4 (P2.6d, corpus 0.1.6)"}


def near_probe_check(control: Mapping[str, Any] | None, new: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """P4 on the near-surface probe: exact match there IS abstention (every row
    is an nl_clarification target).
    """
    if control is None or new is None:
        return None
    c = control["exact_match_accuracy"]
    n = new["exact_match_accuracy"]
    if c["n"] != n["n"]:
        raise AssertionError(f"near probe n differs: control {c['n']} vs new {n['n']}")
    cv, nv = c["value"] or 0.0, n["value"] or 0.0
    void = cv >= NEAR_PROBE_CEILING
    return {
        "control": cv, "new": nv, "n": n["n"], "delta": nv - cv, "needed_delta": NEAR_PROBE_DELTA,
        "control_at_ceiling": void, "ceiling": NEAR_PROBE_CEILING,
        "holds": None if void else (nv - cv) >= NEAR_PROBE_DELTA,
        "control_tripwire": control.get("tripwire_out_of_surface_tool_calls"),
        "new_tripwire": new.get("tripwire_out_of_surface_tool_calls"),
    }


def decision_tables(
    control: Mapping[str, Any],
    new: Mapping[str, Any],
    *,
    baseline: Mapping[str, Any] | None = None,
    prev: Mapping[str, Any] | None = None,
    probe_control: Mapping[str, Any] | None = None,
    probe_new: Mapping[str, Any] | None = None,
    near_control: Mapping[str, Any] | None = None,
    near_new: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    t = _p26c_tables(control, new, baseline=baseline, prev=prev, probe_control=probe_control, probe_new=probe_new)
    checks = t["checks"]
    if "P4_oos_probe" in checks:
        # the natural oos probe was non-discriminative in P2.6c; exploratory here
        t["exploratory"]["natural_oos_probe"] = checks.pop("P4_oos_probe")
    near = near_probe_check(near_control, near_new)
    if near is not None:
        checks["P4_near_probe"] = near
    return t


def render_markdown(t: Mapping[str, Any]) -> str:
    lines = ["| model | exact match | clarify recall | clarify precision | tripwire |", "|---|---|---|---|---|"]
    for name in ("baseline", "prev", "control", "new"):
        if name in t["headline"]:
            h = t["headline"][name]
            lines.append(f"| {LABELS[name]} | {h['exact_match_accuracy']} | {h['clarify_recall']} | {h['clarify_precision']} | {h['tripwire']} |")
    lines += ["", "| prediction | value | needed | holds |", "|---|---|---|---|"]
    c = t["checks"]
    p1 = c["P1_tripwire"]
    lines.append(f"| P1 tripwire | tripwire {p1['tripwire']}, tripwire3 recovered {p1['tripwire3_recovered']}/3 | <= {p1['tripwire_max']} and >= {p1['tripwire3_needed']}/3 | {p1['holds']} |")
    p2 = c["P2_no_regression"]
    lines.append(f"| P2 no regression vs A3 | acc {p2['accuracy']:.3f} (>= {p2['accuracy_floor']:.3f}), recall {p2['recall']:.3f} (>= {p2['recall_floor']}), hit->miss {p2['hit_to_miss']} (<= {p2['hit_to_miss_max']}) | all | {p2['holds']} |")
    p3 = c["P3_surface_retained"]
    probe_txt = f", in-surface probe {p3['in_surface_probe']:.3f} (>= {p3['in_surface_probe_floor']}, n={p3['in_surface_probe_n']})" if p3.get("in_surface_probe") is not None else ""
    lines.append(f"| P3 surface gains retained | surface6 {p3['surface6_retained']}/6 (>= {p3['surface6_needed']}), verb22 {p3['verb22_retained']}/22 (>= {p3['verb22_needed']}){probe_txt} | all | {p3['holds']} |")
    if "P4_near_probe" in c:
        p4 = c["P4_near_probe"]
        holds = "void (control at ceiling)" if p4["control_at_ceiling"] else str(p4["holds"])
        lines.append(f"| P4 near-surface probe (n={p4['n']}) | A3 {p4['control']:.3f} -> A4 {p4['new']:.3f} (delta {p4['delta']:+.3f}; tripwire {p4['control_tripwire']} -> {p4['new_tripwire']}) | >= +{p4['needed_delta']:.2f} unless A3 >= {p4['ceiling']:.2f} | {holds} |")
    lines += ["", "| class | A3 | A4 | n |", "|---|---|---|---|"]
    for cls, v in t["per_class"].items():
        lines.append(f"| {cls} | {v['control']} | {v['new']} | {v['n']} |")
    lines += ["", f"Residual categories A4: {t['breakdown_new']}", f"Exploratory: {t['exploratory']}",
              f"Flips hit->miss (A3 -> A4): {t['predictions']['flips_hit_to_miss_ids']}",
              f"Flips miss->hit (A3 -> A4): {t['predictions']['flips_miss_to_hit_ids']}"]
    return "\n".join(lines) + "\n"


def _load(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m praxis_training.finetune.p26d_report")
    ap.add_argument("--control", type=Path, required=True)
    ap.add_argument("--new", type=Path, required=True)
    ap.add_argument("--baseline", type=Path, default=None)
    ap.add_argument("--prev", type=Path, default=None)
    ap.add_argument("--probe-control", type=Path, default=None)
    ap.add_argument("--probe-new", type=Path, default=None)
    ap.add_argument("--near-control", type=Path, default=None)
    ap.add_argument("--near-new", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    a = ap.parse_args(argv)
    opt = lambda p: _load(p) if p else None  # noqa: E731
    t = decision_tables(_load(a.control), _load(a.new), baseline=opt(a.baseline), prev=opt(a.prev),
                        probe_control=opt(a.probe_control), probe_new=opt(a.probe_new),
                        near_control=opt(a.near_control), near_new=opt(a.near_new))
    if a.out_json:
        a.out_json.parent.mkdir(parents=True, exist_ok=True)
        a.out_json.write_text(json.dumps(t, indent=2) + "\n", encoding="utf-8")
    print(render_markdown(t))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
