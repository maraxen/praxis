"""rescore_check on synthetic reports with known answers (BATHOS rule: verify
the measurement before trusting it)."""

import pytest

from praxis_training.baseline_eval.metrics import proportion_stat
from praxis_training.finetune.rescore_check import check_prediction, compare_reports

IDS = [f"r{i:02d}" for i in range(10)]


def _report(failed, *, rec=(7, 8), prec=(7, 9), trip=1, n=10, confusion=None):
    return {
        "n_examples": n,
        "exact_match_accuracy": proportion_stat(n - len(failed), n),
        "clarify_recall": proportion_stat(*rec),
        "clarify_precision": proportion_stat(*prec),
        "clarify_confusion": confusion or {"tp": 7, "fp": 2, "fn": 1, "tn": 0},
        "tripwire_out_of_surface_tool_calls": trip,
        "exact_match_failures": [{"record_id": r, "class": "x", "reasons": ["params mismatch: 0: predicted {} != intended {}"]} for r in failed],
    }


def test_compare_reports_identical():
    a = _report(["r01", "r02"])
    d = compare_reports(a, _report(["r01", "r02"]))
    assert d["identical"] is True
    assert d["failed_only_in_a"] == [] and d["failed_only_in_b"] == []
    assert d["successes_a"] == d["successes_b"] == 8


def test_compare_reports_lists_flips_both_directions():
    d = compare_reports(_report(["r01", "r02", "r03"]), _report(["r02", "r05"]))
    assert d["failed_only_in_a"] == ["r01", "r03"]   # miss -> hit
    assert d["failed_only_in_b"] == ["r05"]          # hit -> miss
    assert d["failed_in_both"] == 1
    assert d["identical"] is False


def test_compare_reports_rejects_different_split():
    with pytest.raises(ValueError):
        compare_reports(_report([]), _report([], n=11))


def test_prediction_holds_when_only_artifacts_flip():
    old = _report(["r01", "r02", "r03"])
    new = _report(["r03"])
    res = check_prediction(old, new, {"artifact_record_ids": ["r01", "r02"], "expected_tripwire": 1})
    assert res["prediction_holds"] is True
    assert res["flips_miss_to_hit"] == 2 and res["predicted_but_still_missed"] == []
    assert res["successes_old"] == 7 and res["successes_new"] == 9


def test_hit_to_miss_is_a_violation():
    old = _report(["r01"])
    new = _report(["r02"])
    res = check_prediction(old, new, {"artifact_record_ids": ["r01"]})
    assert res["prediction_holds"] is False
    assert res["flips_hit_to_miss"] == ["r02"]


def test_unpredicted_flip_is_a_violation_but_shortfall_is_not():
    old = _report(["r01", "r02", "r03"])
    new = _report(["r02"])   # r01 predicted, r03 not predicted
    res = check_prediction(old, new, {"artifact_record_ids": ["r01", "r02"]})
    assert res["prediction_holds"] is False
    assert res["flips_miss_to_hit_unpredicted"] == ["r03"]
    assert res["predicted_but_still_missed"] == ["r02"]
    # shortfall alone (r02 predicted but still missed) does NOT violate
    res2 = check_prediction(old, _report(["r02", "r03"]), {"artifact_record_ids": ["r01", "r02"]})
    assert res2["prediction_holds"] is True and res2["predicted_but_still_missed"] == ["r02"]


def test_clarify_metrics_must_be_identical():
    old = _report(["r01"])
    new = _report([], rec=(6, 8))
    res = check_prediction(old, new, {"artifact_record_ids": ["r01"]})
    assert res["prediction_holds"] is False and res["clarify_identical"] is False
    # tripwire change alone also violates
    res2 = check_prediction(old, _report([], trip=0), {"artifact_record_ids": ["r01"]})
    assert res2["prediction_holds"] is False and res2["tripwire_ok"] is False


def test_legacy_report_without_tripwire_accepts_reconstructed_value():
    old = _report(["r01"])
    old["tripwire_out_of_surface_tool_calls"] = None
    new = _report([], trip=13)
    assert check_prediction(old, new, {"artifact_record_ids": ["r01"], "expected_tripwire": 13})["prediction_holds"]
    assert not check_prediction(old, new, {"artifact_record_ids": ["r01"], "expected_tripwire": 12})["prediction_holds"]


def test_prediction_from_breakdown_reconstructs_legacy_tripwire():
    from praxis_training.finetune.rescore_check import prediction_from_breakdown

    rep = _report(["r01", "r02", "r03"])
    rep["tripwire_out_of_surface_tool_calls"] = None
    rep["per_class"] = {"out_of_surface": {"exact_match": {"n": 4, "successes": 3}}}
    bd = {"artifact_record_ids": {"list_escape_format": ["r02"], "slot_order_only": ["r01"]},
          "by_category": {"list_escape_format": 1, "slot_order_only": 1, "no_call": 1}}
    pred = prediction_from_breakdown(rep, bd)
    assert pred["artifact_record_ids"] == ["r01", "r02"]
    assert pred["expected_successes_max"] == 9 and abs(pred["expected_accuracy_ceiling"] - 0.9) < 1e-9
    assert pred["expected_tripwire"] == 1
