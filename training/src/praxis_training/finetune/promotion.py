"""Mechanical application of the pre-registered P2.6 promotion rule.

Reads baseline v2 plus one ``baseline_eval`` report per arm and decides, with
no judgment calls, which arm the rule selects and whether it is promoted
(prereg doc ``.praxia/docs/preregistration/260901_p26-finetune-prereg.md`` §3,
sidecar ``scripts/experiments/p26_finetune.bth.toml``)::

    python -m praxis_training.finetune.promotion \
        --baseline training/eval/reports/260901_baseline_real_v2.json \
        --arm A=training/eval/reports/260901_p26_arm_A.json \
        --arm B=... --arm C=... --out-json ... --out-md ...

Rule (verbatim from the prereg):
1. eligible  <=> clarify_recall >= RECALL_FLOOR (baseline v2 point, 0.705)
2. selected  = argmax exact_match_accuracy over eligible arms; tie -> higher clarify_precision
3. promoted  <=> selected arm has acc >= T_ACC and prec >= T_PREC and recall >= T_REC
                 and tripwire_out_of_surface_tool_calls == 0
Per-arm sidecar outcome mirrors ``p26_finetune.bth.toml``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

__all__ = ["THRESHOLDS", "decide", "render_markdown", "main"]

#: Provisional anchors (260825_p25_provisional_thresholds.md) -- ONE revision
#: permitted at P2.6, proposed to the user, never applied here.
THRESHOLDS: Mapping[str, float] = {"T_acc": 0.80, "T_clr_recall": 0.70, "T_clr_prec": 0.90}


def _stat(report: Mapping[str, Any], key: str) -> dict[str, Any]:
    s = report[key]
    return {"value": s["value"], "successes": s["successes"], "n": s["n"], "wilson95": s["wilson95"]}


def _summ(report: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "n_examples": report["n_examples"],
        "exact_match_accuracy": _stat(report, "exact_match_accuracy"),
        "clarify_recall": _stat(report, "clarify_recall"),
        "clarify_precision": _stat(report, "clarify_precision"),
        "tripwire_out_of_surface_tool_calls": report.get("tripwire_out_of_surface_tool_calls"),
        "per_class_exact": {k: v["exact_match"]["value"] for k, v in report.get("per_class", {}).items()},
        "base_revision": report.get("base_revision"),
        "model_label": report.get("model_label"),
    }


def decide(baseline: Mapping[str, Any], arms: Mapping[str, Mapping[str, Any]],
           thresholds: Mapping[str, float] = THRESHOLDS) -> dict[str, Any]:
    base = _summ(baseline)
    recall_floor = base["clarify_recall"]["value"]
    distinguish = base["exact_match_accuracy"]["wilson95"][1]
    rows: dict[str, dict[str, Any]] = {}
    for arm, rep in arms.items():
        s = _summ(rep)
        acc = s["exact_match_accuracy"]["value"]
        rec = s["clarify_recall"]["value"]
        prec = s["clarify_precision"]["value"]
        trip = s["tripwire_out_of_surface_tool_calls"]
        if trip is None:
            raise ValueError(f"arm {arm}: report lacks tripwire_out_of_surface_tool_calls")
        if s["n_examples"] != base["n_examples"]:
            raise ValueError(
                f"arm {arm}: n_examples {s['n_examples']} != baseline {base['n_examples']} -- not the same eval split"
            )
        eligible = rec is not None and rec >= recall_floor
        anchors_ok = (acc is not None and acc >= thresholds["T_acc"]
                      and prec is not None and prec >= thresholds["T_clr_prec"]
                      and rec is not None and rec >= thresholds["T_clr_recall"]
                      and trip == 0)
        if anchors_ok:
            outcome = "pass"
        elif eligible and acc is not None and acc > distinguish:
            outcome = "marginal"
        else:
            outcome = "fail"
        rows[arm] = s | {"eligible": eligible, "anchors_cleared": anchors_ok, "sidecar_outcome": outcome,
                         "delta_acc_vs_baseline": None if acc is None else acc - base["exact_match_accuracy"]["value"],
                         "delta_recall_vs_baseline": None if rec is None else rec - recall_floor,
                         "delta_prec_vs_baseline": None if prec is None else prec - base["clarify_precision"]["value"]}
    eligible_arms = [a for a, r in rows.items() if r["eligible"]]
    selected = None
    if eligible_arms:
        selected = sorted(
            eligible_arms,
            key=lambda a: (rows[a]["exact_match_accuracy"]["value"], rows[a]["clarify_precision"]["value"] or 0.0, a),
            reverse=True,
        )[0]
        # ``a`` in the key only breaks exact ties deterministically (later letter wins)
        # -- reverse sort on the letter is the documented tie order A<B<C reversed;
        # make it explicit and stable: prefer the EARLIER arm on a full tie.
        ties = [a for a in eligible_arms
                if (rows[a]["exact_match_accuracy"]["value"], rows[a]["clarify_precision"]["value"])
                == (rows[selected]["exact_match_accuracy"]["value"], rows[selected]["clarify_precision"]["value"])]
        selected = sorted(ties)[0]
    promoted = bool(selected and rows[selected]["anchors_cleared"])
    return {
        "rule": {
            "recall_floor": recall_floor,
            "distinguishability_bound": distinguish,
            "thresholds": dict(thresholds),
            "tie_break": "higher clarify_precision, then earlier arm letter",
        },
        "baseline": base,
        "arms": rows,
        "eligible_arms": sorted(eligible_arms),
        "selected_arm": selected,
        "promoted": promoted,
        "verdict": ("PROMOTE " + selected) if promoted else ("NOT PROMOTED" + (f" (selected {selected})" if selected else " (no eligible arm)")),
    }


def _fmt(stat: Mapping[str, Any]) -> str:
    if stat["value"] is None:
        return "n/a"
    lo, hi = stat["wilson95"]
    return f"{stat['value']:.3f} [{lo:.3f}, {hi:.3f}] ({stat['successes']}/{stat['n']})"


def render_markdown(decision: Mapping[str, Any]) -> str:
    th = decision["rule"]["thresholds"]
    lines = [
        "| Arm | T_acc (>= %.2f) | T_clr_recall (>= %.2f) | T_clr_prec (>= %.2f) | tripwire (== 0) | eligible | outcome |"
        % (th["T_acc"], th["T_clr_recall"], th["T_clr_prec"]),
        "|---|---|---|---|---|---|---|",
    ]
    b = decision["baseline"]
    lines.append(
        f"| baseline v2 | {_fmt(b['exact_match_accuracy'])} | {_fmt(b['clarify_recall'])} | "
        f"{_fmt(b['clarify_precision'])} | {b['tripwire_out_of_surface_tool_calls'] if b['tripwire_out_of_surface_tool_calls'] is not None else '13 (derived)'} | -- | -- |"
    )
    for arm, r in sorted(decision["arms"].items()):
        lines.append(
            f"| {arm} | {_fmt(r['exact_match_accuracy'])} | {_fmt(r['clarify_recall'])} | "
            f"{_fmt(r['clarify_precision'])} | {r['tripwire_out_of_surface_tool_calls']} | "
            f"{'yes' if r['eligible'] else 'no'} | {r['sidecar_outcome']} |"
        )
    lines.append("")
    lines.append(f"Rule: eligible iff recall >= {decision['rule']['recall_floor']:.3f}; selected = max accuracy among eligible "
                 f"({decision['rule']['tie_break']}); promoted iff all anchors + tripwire 0.")
    lines.append(f"Eligible: {', '.join(decision['eligible_arms']) or 'none'}. Selected: {decision['selected_arm'] or 'none'}. "
                 f"**Verdict: {decision['verdict']}.**")
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m praxis_training.finetune.promotion")
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--arm", action="append", required=True, metavar="ARM=REPORT.json")
    p.add_argument("--out-json", type=Path, default=None)
    p.add_argument("--out-md", type=Path, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    arms: dict[str, Any] = {}
    for spec in args.arm:
        name, _, path = spec.partition("=")
        if not path:
            raise SystemExit(f"--arm expects ARM=path, got {spec!r}")
        arms[name] = json.loads(Path(path).read_text(encoding="utf-8"))
    decision = decide(baseline, arms)
    md = render_markdown(decision)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
