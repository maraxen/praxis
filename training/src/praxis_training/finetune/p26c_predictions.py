"""The pre-registered row lists and checks of P2.6c
(.praxia/docs/preregistration/260903_p26c-oos-natural-prereg.md §3).

Control = arm A2 (P2.6b, corpus 0.1.4); new = arm A3 (corpus 0.1.5 with the
out-of-surface natural lane). Pure functions over baseline_eval reports; a
superset of ``p26b_predictions.evaluate_predictions`` so the trainer's
``--compare-report`` path keeps filling the P2.6b fields (which here read as
"retained"). Row lists are DATA frozen at pre-registration time -- do not edit
after the prereg commit.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from praxis_training.finetune.p26b_predictions import SURFACE6, VERB22
from praxis_training.finetune.p26b_predictions import evaluate_predictions as _p26b

__all__ = ["TRIPWIRE3", "OOS_EVAL44", "AMBIG4", "SURFACE6", "VERB22", "evaluate_predictions", "probe_split"]

#: P1 -- the three out-of-surface eval rows A2 emitted a call on (tripwire 3).
TRIPWIRE3: tuple[str, ...] = ("golden-out-surface-05", "golden-out-surface-10", "golden-out-surface-11")

#: The 44 out-of-surface rows of the pinned eval split (32 floor + 12 golden).
OOS_EVAL44: tuple[str, ...] = tuple(
    f"cov-{n:04d}-{verb}__out-of-surface-{i}"
    for verb, start in (
        ("mix", 61), ("blow_out", 126), ("touch_tip", 191), ("dispense_to_waste", 256),
        ("set_temperature", 321), ("shake", 386), ("stop_shaking", 451), ("generic", 516),
    )
    for n, i in zip(range(start, start + 4), range(16, 20), strict=True)
) + tuple(f"golden-out-surface-{i:02d}" for i in range(1, 13))

#: P5 exploratory -- the A -> A2 hit->miss flips that over-canonicalised a vague
#: span (policy item, not data): three golden ambiguous rows + drop_tips-01.
AMBIG4: tuple[str, ...] = (
    "golden-ambig-ref-02", "golden-ambig-ref-11", "golden-ambig-ref-12", "golden-clean-drop_tips-01",
)


def _failed(report: Mapping[str, Any]) -> set[str]:
    return {row["record_id"] for row in report.get("exact_match_failures", [])}


def evaluate_predictions(control: Mapping[str, Any], new: Mapping[str, Any]) -> dict[str, Any]:
    """P1-P5 numbers for (A2 = control, A3 = new) on the same split; includes every P2.6b key."""
    base = _p26b(control, new)
    new_failed = _failed(new)
    old_failed = _failed(control)

    def hits(ids: tuple[str, ...], failed: set[str]) -> list[str]:
        return [rid for rid in ids if rid not in failed]

    return base | {
        "tripwire3_recovered": len(hits(TRIPWIRE3, new_failed)),
        "tripwire3_recovered_ids": hits(TRIPWIRE3, new_failed),
        "oos44_exact_old": len(hits(OOS_EVAL44, old_failed)),
        "oos44_exact_new": len(hits(OOS_EVAL44, new_failed)),
        "surface6_retained": base["surface6_recovered"],
        "verb22_retained": base["verb_category_migrated"],
        "ambig4_recovered": len(hits(AMBIG4, new_failed)),
        "ambig4_recovered_ids": hits(AMBIG4, new_failed),
    }


def probe_split(probe: Mapping[str, Any]) -> dict[str, Any]:
    """Split a probe report's per_class block into in-surface vs out-of-surface accuracy."""
    per = probe.get("per_class", {})
    oos = per.get("out_of_surface", {}).get("exact_match", {"successes": 0, "n": 0})
    ins_s = sum(v["exact_match"]["successes"] for k, v in per.items() if k != "out_of_surface")
    ins_n = sum(v["exact_match"]["n"] for k, v in per.items() if k != "out_of_surface")
    return {
        "in_surface_probe_n": ins_n,
        "in_surface_probe_exact_match_accuracy": (ins_s / ins_n) if ins_n else None,
        "oos_probe_n": oos["n"],
        "oos_probe_exact_match_accuracy": (oos["successes"] / oos["n"]) if oos["n"] else None,
    }
