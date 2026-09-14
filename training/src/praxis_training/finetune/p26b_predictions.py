"""The pre-registered row lists and checks of P2.6b
(.praxia/docs/preregistration/260902_p26b-floor-surface-prereg.md §3).

Pure functions over baseline_eval reports; used by the trainer (to fill the
sidecar result fields) and by the decision analysis. Row lists are DATA
frozen at pre-registration time -- do not edit after commit cc662026.
"""

from __future__ import annotations

from typing import Any, Mapping

from praxis_training.finetune.failure_breakdown import classify_reasons
from praxis_training.finetune.rescore_check import compare_reports

__all__ = ["SURFACE6", "VAGUE3", "HALLUCINATED4", "VERB22", "VERB_CATEGORIES", "evaluate_predictions"]

#: P1 -- coverage eval rows whose gold reference is a dotted id absent from the utterance.
SURFACE6: tuple[str, ...] = (
    "cov-0092-dispense__missing-slot-12", "cov-0093-dispense__missing-slot-13",
    "cov-0094-dispense__missing-slot-14", "cov-0172-transfer__ambiguous-referent-12",
    "cov-0173-transfer__ambiguous-referent-13", "cov-0174-transfer__ambiguous-referent-14",
)
#: P1b -- exploratory: vague-string mismatch (scorer/gold decision, not data).
VAGUE3: tuple[str, ...] = (
    "cov-0367-drop_tips__ambiguous-referent-12", "cov-0369-drop_tips__ambiguous-referent-14",
    "cov-0609-move_lid__ambiguous-referent-14",
)
#: P1b -- exploratory: hallucinated extra argument on missing-slot rows.
HALLUCINATED4: tuple[str, ...] = (
    "cov-0158-transfer__missing-slot-13", "cov-0547-move_lid__missing-slot-12",
    "cov-0548-move_lid__missing-slot-13", "cov-0549-move_lid__missing-slot-14",
)
#: P2 -- rows A fails as name_mismatch / no_call / unknown_verb (fixed scorer).
VERB22: tuple[str, ...] = (
    "cov-0467-move_resource__none-12", "cov-0482-move_plate__missing-slot-12",
    "cov-0483-move_plate__missing-slot-13", "cov-0484-move_plate__missing-slot-14",
    "cov-0498-move_resource__ambiguous-referent-13", "golden-clean-aspirate-03",
    "golden-clean-discard_tips-02", "golden-clean-discard_tips-04", "golden-clean-dispense-02",
    "golden-clean-dispense-04", "golden-clean-move_lid-03", "golden-clean-move_plate-02",
    "golden-clean-move_plate-03", "golden-clean-move_resource-02", "golden-clean-move_resource-03",
    "golden-clean-read_fluorescence-02", "golden-clean-stamp-02", "golden-clean-stamp-03",
    "golden-clean-transfer-02", "golden-clean-transfer-04", "golden-missing-slot-02", "ovl-f33ef17438",
)
VERB_CATEGORIES = frozenset({"name_mismatch", "no_call", "unknown_verb"})


def _categories(report: Mapping[str, Any]) -> dict[str, str]:
    return {row["record_id"]: classify_reasons(row.get("reasons", ())) for row in report.get("exact_match_failures", [])}


def evaluate_predictions(old: Mapping[str, Any], new: Mapping[str, Any]) -> dict[str, Any]:
    """P1/P1b/P2/P3 numbers for (A = old, A2 = new) on the same split."""
    diff = compare_reports(old, new)
    new_cats = _categories(new)
    old_cats = _categories(old)
    new_failed = set(new_cats)

    def recovered(ids: tuple[str, ...]) -> list[str]:
        return [rid for rid in ids if rid not in new_failed]

    migrated = [rid for rid in VERB22 if new_cats.get(rid) not in VERB_CATEGORIES]  # passing rows count
    return {
        "surface6_recovered": len(recovered(SURFACE6)),
        "surface6_recovered_ids": recovered(SURFACE6),
        "vague3_recovered": len(recovered(VAGUE3)),
        "hallucinated4_recovered": len(recovered(HALLUCINATED4)),
        "verb_category_migrated": len(migrated),
        "verb_category_migrated_ids": migrated,
        "verb22_now_exact": len(recovered(VERB22)),
        "verb22_old_categories": {rid: old_cats.get(rid) for rid in VERB22},
        "verb22_new_categories": {rid: new_cats.get(rid, "PASS") for rid in VERB22},
        "discard_tips_pair_exact": len(recovered(("golden-clean-discard_tips-02", "golden-clean-discard_tips-04"))),
        "flips_hit_to_miss": len(diff["failed_only_in_b"]),
        "flips_hit_to_miss_ids": diff["failed_only_in_b"],
        "flips_miss_to_hit": len(diff["failed_only_in_a"]),
        "flips_miss_to_hit_ids": diff["failed_only_in_a"],
        "successes_old": diff["successes_a"],
        "successes_new": diff["successes_b"],
        "clarify_identical": diff["clarify_identical"],
        "tripwire_old": diff["tripwire_a"],
        "tripwire_new": diff["tripwire_b"],
    }
