"""p26b_predictions.evaluate_predictions on synthetic reports with known answers."""

from praxis_training.baseline_eval.metrics import proportion_stat
from praxis_training.finetune.p26b_predictions import SURFACE6, VERB22, evaluate_predictions


def _report(failed: dict[str, list[str]], n=228):
    return {
        "n_examples": n,
        "exact_match_accuracy": proportion_stat(n - len(failed), n),
        "clarify_recall": proportion_stat(76, 88),
        "clarify_precision": proportion_stat(76, 91),
        "clarify_confusion": {"tp": 76, "fp": 15, "fn": 12, "tn": 125},
        "tripwire_out_of_surface_tool_calls": 1,
        "exact_match_failures": [{"record_id": r, "class": "x", "reasons": rs} for r, rs in failed.items()],
    }


PARAMS = ["params mismatch: 0: predicted {'a': 1} != intended {'a': 2}"]
NAME = ["name mismatch: 0: predicted 'x' != intended 'y'"]
NOCALL = ["sequence length 0 != intended 1"]


def test_lists_are_frozen_sizes():
    assert len(SURFACE6) == 6 and len(VERB22) == 22 and len(set(VERB22)) == 22


def test_counts_recovered_migrated_and_flips():
    old = _report({**{r: PARAMS for r in SURFACE6}, **{r: NAME for r in VERB22[:11]}, **{r: NOCALL for r in VERB22[11:]}, "other-1": PARAMS})
    # new: 4 surface rows pass; 5 verb rows pass, 7 become param_content, 10 still name/no_call; one new miss
    new_failed = {r: PARAMS for r in SURFACE6[4:]}
    new_failed.update({r: PARAMS for r in VERB22[5:12]})
    new_failed.update({r: NAME for r in VERB22[12:]})
    new_failed["other-1"] = PARAMS
    new_failed["fresh-miss"] = PARAMS
    res = evaluate_predictions(old, _report(new_failed))
    assert res["surface6_recovered"] == 4
    assert res["verb_category_migrated"] == 12   # 5 passing + 7 param_content
    assert res["verb22_now_exact"] == 5
    assert res["flips_hit_to_miss"] == 1 and res["flips_hit_to_miss_ids"] == ["fresh-miss"]
    assert res["flips_miss_to_hit"] == 4 + 5
    assert res["clarify_identical"] is True


def test_decision_tables_render():
    from praxis_training.finetune.p26b_report import decision_tables, render_markdown

    old = _report({**{r: PARAMS for r in SURFACE6}, **{r: NAME for r in VERB22}})
    new = _report({r: PARAMS for r in SURFACE6[5:]})
    for rep in (old, new):
        rep["per_class"] = {"clean_parse": {"exact_match": {"successes": 1, "n": 2}}}
    t = decision_tables(old, new, probe_old=_report({"p1": PARAMS}, n=4), probe_new=_report({}, n=4))
    assert t["checks"]["P1_surface6"]["holds"] and t["checks"]["P2_verb_migration"]["holds"]
    assert t["checks"]["P3_no_regression"]["holds"] and t["checks"]["P4_probe"]["holds"]
    md = render_markdown(t)
    assert "P1_surface6 | 5/6" in md and "P4 probe" in md
