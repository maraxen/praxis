"""p26c_predictions on synthetic reports with known answers (frozen lists checked against the sidecar)."""

import json
from pathlib import Path

from praxis_training.baseline_eval.metrics import proportion_stat
from praxis_training.finetune.p26c_predictions import (
    AMBIG4,
    OOS_EVAL44,
    TRIPWIRE3,
    evaluate_predictions,
    probe_split,
)

REPO = Path(__file__).resolve().parents[2]
SIDECAR = REPO / "training" / "assemble" / "out" / "corpus_p25_sidecar.jsonl"


def _report(failed: dict[str, list[str]], n=228, tripwire=0):
    return {
        "n_examples": n,
        "exact_match_accuracy": proportion_stat(n - len(failed), n),
        "clarify_recall": proportion_stat(81, 88),
        "clarify_precision": proportion_stat(81, 95),
        "clarify_confusion": {"tp": 81, "fp": 14, "fn": 7, "tn": 126},
        "tripwire_out_of_surface_tool_calls": tripwire,
        "exact_match_failures": [{"record_id": r, "class": "x", "reasons": rs} for r, rs in failed.items()],
    }


SPURIOUS = ["sequence length 1 != intended 0"]
PARAMS = ["params mismatch: 0: predicted {'a': 1} != intended {'a': 2}"]


def test_frozen_lists_match_the_pinned_eval_split():
    rows = [json.loads(line) for line in SIDECAR.read_text(encoding="utf-8").splitlines() if line.strip()]
    oos = {r["record_id"] for r in rows if r["split"] == "eval" and r["ambiguity_class"] == "out_of_surface"}
    assert set(OOS_EVAL44) == oos and len(OOS_EVAL44) == 44
    assert set(TRIPWIRE3) <= oos
    eval_ids = {r["record_id"] for r in rows if r["split"] == "eval"}
    assert set(AMBIG4) <= eval_ids


def test_tripwire_recovery_and_oos_counts():
    control = _report(dict.fromkeys(TRIPWIRE3, SPURIOUS) | {"other-1": PARAMS}, tripwire=3)
    new = _report({TRIPWIRE3[0]: SPURIOUS, "other-1": PARAMS, "fresh-miss": PARAMS}, tripwire=1)
    res = evaluate_predictions(control, new)
    assert res["tripwire3_recovered"] == 2 and res["tripwire3_recovered_ids"] == list(TRIPWIRE3[1:])
    assert res["oos44_exact_old"] == 41 and res["oos44_exact_new"] == 43
    assert res["flips_hit_to_miss"] == 1 and res["flips_hit_to_miss_ids"] == ["fresh-miss"]
    assert res["tripwire_old"] == 3 and res["tripwire_new"] == 1
    assert res["surface6_retained"] == 6 and res["verb22_retained"] == 22  # nothing listed failed
    assert res["ambig4_recovered"] == 4


def test_probe_split():
    probe = {"per_class": {
        "clean_parse": {"exact_match": {"successes": 30, "n": 37}},
        "missing_slot": {"exact_match": {"successes": 25, "n": 32}},
        "out_of_surface": {"exact_match": {"successes": 8, "n": 32}},
    }}
    s = probe_split(probe)
    assert s["in_surface_probe_n"] == 69 and abs(s["in_surface_probe_exact_match_accuracy"] - 55 / 69) < 1e-9
    assert s["oos_probe_n"] == 32 and s["oos_probe_exact_match_accuracy"] == 0.25
    assert probe_split({"per_class": {"clean_parse": {"exact_match": {"successes": 1, "n": 2}}}})["oos_probe_n"] == 0


def test_decision_tables_render():
    from praxis_training.finetune.p26c_predictions import SURFACE6, VERB22
    from praxis_training.finetune.p26c_report import decision_tables, render_markdown

    control = _report(dict.fromkeys(TRIPWIRE3, SPURIOUS) | dict.fromkeys(SURFACE6[4:], PARAMS) | dict.fromkeys(VERB22[:11], PARAMS), tripwire=3)
    new = _report(dict.fromkeys(SURFACE6[4:], PARAMS) | dict.fromkeys(VERB22[:11], PARAMS), tripwire=0)
    for rep in (control, new):
        rep["per_class"] = {"clean_parse": {"exact_match": {"successes": 1, "n": 2}}}
    probe_c = {"n_examples": 122, "exact_match_accuracy": proportion_stat(80, 122), "per_class": {
        "clean_parse": {"exact_match": {"successes": 30, "n": 37}}, "missing_slot": {"exact_match": {"successes": 26, "n": 32}},
        "ambiguous_referent": {"exact_match": {"successes": 19, "n": 21}}, "out_of_surface": {"exact_match": {"successes": 5, "n": 32}}}}
    probe_n = {"n_examples": 122, "exact_match_accuracy": proportion_stat(100, 122), "per_class": {
        "clean_parse": {"exact_match": {"successes": 31, "n": 37}}, "missing_slot": {"exact_match": {"successes": 26, "n": 32}},
        "ambiguous_referent": {"exact_match": {"successes": 19, "n": 21}}, "out_of_surface": {"exact_match": {"successes": 24, "n": 32}}}}
    t = decision_tables(control, new, probe_control=probe_c, probe_new=probe_n)
    assert t["checks"]["P1_tripwire"]["holds"] and t["checks"]["P2_no_regression"]["holds"]
    assert t["checks"]["P3_surface_retained"]["holds"] and t["checks"]["P4_oos_probe"]["holds"]
    md = render_markdown(t)
    assert "tripwire3 recovered 3/3" in md and "P4 oos probe (n=32)" in md
    # regression: a fabricated call on a new row and a lost surface row
    worse = _report(dict.fromkeys(SURFACE6[3:], PARAMS) | {"golden-out-surface-01": SPURIOUS}, tripwire=1)
    worse["per_class"] = new["per_class"]
    t2 = decision_tables(control, worse)
    assert t2["checks"]["P1_tripwire"]["holds"] and not t2["checks"]["P3_surface_retained"]["holds"]
