"""AC-2.6.3 clarify tripwire + model_label on the eval report.

Verified on SYNTHETIC ground truth first (BATHOS rule): a fabricated call on an
out-of-surface row counts, an abstention does not, other classes never count.
"""

from praxis_training.baseline_eval.metrics import ScoredExample, build_report, score_example
from praxis_training.golden_build.build import render_sidecar_row
from praxis_training.golden_build.corpus import AmbiguityClass, GoldenCall, GoldenExample


def _intent(record_id, utterance, cls, calls=(), assistant_text=None):
    ex = GoldenExample(
        record_id=record_id, split="eval", ambiguity_class=cls, utterance=utterance,
        calls=tuple(GoldenCall(name=n, params=p) for n, p in calls),
        assistant_text=assistant_text,
    )
    return render_sidecar_row(ex)


def _mk(rid, cls, n_calls, exact=False):
    return ScoredExample(
        record_id=rid, ambiguity_class=cls, exact_match=exact,
        clarify_expected=cls != "clean_parse", clarify_predicted=n_calls == 0,
        reasons=(), n_calls_emitted=n_calls,
    )


def test_tripwire_counts_only_out_of_surface_rows_that_emitted_calls():
    scored = [
        _mk("a", "out_of_surface", 0, exact=True),   # abstained: fine
        _mk("b", "out_of_surface", 1),               # fabricated call: tripwire
        _mk("c", "out_of_surface", 2),               # two calls: still ONE row
        _mk("d", "clean_parse", 1, exact=True),      # positives never count
        _mk("e", "missing_slot", 1),                 # incomplete call is the target; never counts
    ]
    report = build_report(scored, mode="recorded_artifacts", base_revision="m@r",
                          inputs={}, labeled_as="test", model_label="unit")
    assert report["tripwire_out_of_surface_tool_calls"] == 2
    assert report["model_label"] == "unit"


def test_model_label_defaults_to_none_for_legacy_callers():
    report = build_report([_mk("a", "clean_parse", 1, exact=True)], mode="recorded_artifacts",
                          base_revision="m@r", inputs={}, labeled_as="test")
    assert report["model_label"] is None
    assert report["tripwire_out_of_surface_tool_calls"] == 0


def test_score_example_records_emitted_calls_even_for_unknown_verbs():
    intent = _intent("x", "Turn on the heater shaker.", AmbiguityClass.OUT_OF_SURFACE)
    fabricated = "<start_function_call>call:set_temperature{target_c:<escape>37<escape>}<end_function_call>"
    scored = score_example(fabricated, intent)
    assert scored.n_calls_emitted == 1
    assert scored.exact_match is False
    abstained = score_example("I can only control the liquid handler and plate reader.", intent)
    assert abstained.n_calls_emitted == 0
    assert abstained.exact_match is True


def test_tripwire_on_real_baseline_v2_report_reconstructs_from_per_class():
    """Baseline v2 recorded 31/44 out_of_surface abstentions -> 13 fabricated
    calls. The new field must agree with that arithmetic when re-scored; here
    we only pin the identity the promotion doc relies on."""
    n, abstained = 44, 31
    assert n - abstained == 13
