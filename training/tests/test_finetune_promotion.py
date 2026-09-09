"""The pre-registered promotion rule on synthetic reports with known answers."""

import pytest

from praxis_training.baseline_eval.metrics import proportion_stat
from praxis_training.finetune.promotion import decide, render_markdown


def _report(acc_k, rec_k, prec_k, prec_n, trip, n=228, rec_n=88):
    return {
        "n_examples": n,
        "exact_match_accuracy": proportion_stat(acc_k, n),
        "clarify_recall": proportion_stat(rec_k, rec_n),
        "clarify_precision": proportion_stat(prec_k, prec_n),
        "tripwire_out_of_surface_tool_calls": trip,
        "per_class": {},
        "base_revision": "m@r",
        "model_label": "t",
    }


BASELINE = _report(37, 62, 62, 110, 13)  # = baseline v2 numbers


def test_no_eligible_arm_when_recall_regresses():
    d = decide(BASELINE, {"A": _report(200, 61, 60, 62, 0)})
    assert d["eligible_arms"] == [] and d["selected_arm"] is None and d["promoted"] is False
    assert d["arms"]["A"]["sidecar_outcome"] == "fail"


def test_selection_by_accuracy_then_precision_then_letter():
    arms = {
        "A": _report(150, 70, 70, 80, 0),
        "B": _report(160, 70, 70, 90, 0),   # best acc
        "C": _report(160, 70, 75, 90, 0),   # same acc, better precision
    }
    d = decide(BASELINE, arms)
    assert d["eligible_arms"] == ["A", "B", "C"]
    assert d["selected_arm"] == "C"
    tie = {"A": _report(160, 70, 70, 80, 0), "B": _report(160, 70, 70, 80, 0)}
    assert decide(BASELINE, tie)["selected_arm"] == "A"


def test_promotion_requires_all_anchors_and_tripwire():
    good = _report(190, 70, 90, 95, 0)      # acc .833 rec .795 prec .947 trip 0
    d = decide(BASELINE, {"B": good})
    assert d["promoted"] is True and d["verdict"] == "PROMOTE B"
    assert d["arms"]["B"]["sidecar_outcome"] == "pass"
    tripped = _report(190, 70, 90, 95, 1)
    d2 = decide(BASELINE, {"B": tripped})
    assert d2["promoted"] is False and d2["selected_arm"] == "B"
    assert d2["arms"]["B"]["sidecar_outcome"] == "marginal"


def test_marginal_needs_distinguishability_from_baseline():
    # recall fine, accuracy inside the baseline's Wilson interval -> fail, not marginal
    weak = _report(45, 70, 62, 100, 0)  # acc 0.197 < 0.216 upper bound
    d = decide(BASELINE, {"A": weak})
    assert d["arms"]["A"]["eligible"] is True
    assert d["arms"]["A"]["sidecar_outcome"] == "fail"
    assert d["selected_arm"] == "A" and d["promoted"] is False


def test_rejects_reports_from_a_different_split():
    with pytest.raises(ValueError):
        decide(BASELINE, {"A": _report(50, 70, 62, 100, 0, n=100)})


def test_markdown_has_one_row_per_arm_and_verdict():
    md = render_markdown(decide(BASELINE, {"A": _report(150, 70, 70, 80, 0), "B": _report(160, 70, 70, 80, 0)}))
    assert md.count("\n| ") == 3  # baseline + 2 arms
    assert "Verdict: NOT PROMOTED (selected B)" in md
