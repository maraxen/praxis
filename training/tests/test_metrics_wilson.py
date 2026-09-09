"""Wilson interval math + metric assembly against HAND-COMPUTED constants.

Reference values computed independently (plain formula, z=1.9596398454794924):
    k=5,n=8  -> [0.305783, 0.863133]
    k=0,n=10 -> [0.000000, 0.277466]
    k=10,n=10-> [0.722534, 1.000000]
    k=1,n=20 -> [0.008884, 0.236089]
"""

import math

from praxis_training.baseline_eval.metrics import (
    Z95,
    build_report,
    proportion_stat,
    score_example,
    wilson_interval,
)
from praxis_training.golden_build.corpus import AmbiguityClass


def _ref(k: int, n: int) -> tuple[float, float]:
    z = 1.9596398454794924
    p = k / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return max(0.0, center - half), min(1.0, center + half)


def test_z95_pin():
    assert abs(Z95 - 1.9596398454794924) < 1e-12


def test_wilson_known_values():
    cases = {(5, 8): (0.305783, 0.863133), (0, 10): (0.0, 0.277466),
             (10, 10): (0.722534, 1.0), (1, 20): (0.008884, 0.236089)}
    for (k, n), want in cases.items():
        lo, hi = wilson_interval(k, n)
        rlo, rhi = _ref(k, n)
        assert abs(lo - rlo) < 5e-6 and abs(hi - rhi) < 5e-6
        assert abs(lo - want[0]) < 5e-6 and abs(hi - want[1]) < 5e-6


def test_wilson_interval_is_contained_and_ordered():
    for k in range(0, 21):
        lo, hi = wilson_interval(k, 20)
        assert 0.0 <= lo <= hi <= 1.0


def test_wilson_zero_n_returns_none():
    assert wilson_interval(0, 0) is None
    stat = proportion_stat(3, 0)
    assert stat["value"] is None and stat["wilson95"] is None and stat["n"] == 0


def test_proportion_stat_shape():
    stat = proportion_stat(5, 8)
    assert stat["value"] == pytest_approx(0.625)
    assert stat["successes"] == 5 and stat["n"] == 8
    assert len(stat["wilson95"]) == 2


def pytest_approx(x):
    class _A:
        def __eq__(self, other):
            return abs(other - x) < 1e-12
    return _A()


# ---------------------------------------------------------------------------
# score_example + build_report on SYNTHETIC intents with known metric values.
# Synthetic intents are built through render_sidecar_row so their gap fields
# follow the REAL derivation contract (sidecar rows always carry them).
# ---------------------------------------------------------------------------

from praxis_training.golden_build.build import render_sidecar_row
from praxis_training.golden_build.corpus import GoldenCall, GoldenExample


def _intent(record_id, utterance, cls, calls=(), assistant_text=None):
    ex = GoldenExample(
        record_id=record_id, split="eval", ambiguity_class=cls,
        utterance=utterance, calls=tuple(
            GoldenCall(name=n, params=p) for n, p in calls
        ),
        assistant_text=assistant_text,
    )
    return render_sidecar_row(ex)


def test_score_exact_positive_match():
    intent = _intent("x1", "Take up 50 uL from r1.", AmbiguityClass.CLEAN_PARSE,
                     [("aspirate", {"source": "r1", "volume_ul": 50})])
    raw = "<start_function_call>call:aspirate{source:<escape>r1<escape>,volume_ul:<escape>50<escape>}<end_function_call>"
    scored = score_example(raw, intent)
    assert scored.exact_match is True
    assert scored.clarify_expected is False
    assert scored.clarify_predicted is False


def test_score_numeric_string_normalization():
    # model echoes "600"; scorer normalizes both sides -> match
    intent = _intent("x2", "Read absorbance at 600 nm.", AmbiguityClass.CLEAN_PARSE,
                     [("read_absorbance", {"wavelength_nm": 600})])
    raw = "<start_function_call>call:read_absorbance{wavelength_nm:<escape>600<escape>}<end_function_call>"
    assert score_example(raw, intent).exact_match is True


def test_score_missing_required_is_clarify_expected_and_predicted():
    intent = _intent("x3", "Aspirate 50 microliters.", AmbiguityClass.MISSING_SLOT,
                     [("aspirate", {"volume_ul": 50})])
    raw = "<start_function_call>call:aspirate{volume_ul:<escape>50<escape>}<end_function_call>"
    scored = score_example(raw, intent)
    assert scored.exact_match is True  # incomplete call IS the supervision target
    assert scored.clarify_expected is True
    assert scored.clarify_predicted is True


def test_score_abstention_counts_as_clarify_routing():
    intent = _intent("x4", "Turn on the heater shaker.", AmbiguityClass.OUT_OF_SURFACE)
    scored = score_example("", intent)
    assert scored.exact_match is True
    assert scored.clarify_expected is True and scored.clarify_predicted is True


def test_score_unknown_excluded_verb_not_clarify_routing():
    intent = _intent("x5", "Mix my samples.", AmbiguityClass.OUT_OF_SURFACE)
    raw = "<start_function_call>call:mix{at:<escape>x<escape>}<end_function_call>"
    scored = score_example(raw, intent)
    assert scored.exact_match is False
    assert scored.clarify_predicted is False
    assert any("unknown/excluded" in r for r in scored.reasons)


def test_build_report_confusion_and_wilson():
    def mk(rid, exact, exp, pred):
        from praxis_training.baseline_eval.metrics import ScoredExample

        return ScoredExample(
            record_id=rid, ambiguity_class="t", exact_match=exact,
            clarify_expected=exp, clarify_predicted=pred, reasons=(),
        )

    scored = [
        mk("a", True, True, True),    # TP
        mk("b", False, True, False),  # FN
        mk("c", False, False, True),  # FP
        mk("d", True, False, False),  # TN
        mk("e", True, True, True),    # TP
    ]
    report = build_report(
        scored, mode="recorded_artifacts", base_revision="m@r",
        inputs={}, labeled_as="test",
    )
    assert report["clarify_confusion"] == {"true_positive": 2, "false_negative": 1,
                                           "false_positive": 1, "true_negative": 1}
    assert report["exact_match_accuracy"]["successes"] == 3
    assert report["exact_match_accuracy"]["n"] == 5
    assert report["clarify_recall"]["value"] == 2 / 3
    assert report["clarify_precision"]["value"] == 2 / 3
    lo, hi = report["clarify_recall"]["wilson95"]
    rlo, rhi = _ref(2, 3)
    assert abs(lo - rlo) < 1e-9 and abs(hi - rhi) < 1e-9
