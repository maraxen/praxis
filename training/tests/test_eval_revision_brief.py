"""eval_revision_brief on committed reports + hand-built synthetic rows
(BATHOS rule: verify the measurement pipeline on synthetic ground truth
before trusting it against the real dumps).

Task 260903_p26d_eval_revision_brief. Three groups, matching the deliverable:

(i)   policies-OFF reproduces the committed reports exactly (successes/n,
      tripwire) for all three checkpoints -- proves ``score_example_cf``
      truly delegates to the frozen ``metrics.score_example`` rather than
      duplicating it.
(ii)  one synthetic hand-built row per policy (J1 abstention, J2 normalized,
      J2 any_span, J3 pure transform), with an OBVIOUS non-transform
      negative control for J3 so the regex stays conservative.
(iii) the frozen TRIPWIRE3 row list (p26c_predictions) matches the committed
      A2/A3 reports' own exact_match_failures.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from coxswain.plr.slot_derivation import derive_call_gaps
from praxis_training.baseline_eval import metrics
from praxis_training.finetune.eval_revision_brief import (
    CHECKPOINTS,
    COMBINED,
    J1_ONLY,
    J2_ANY_SPAN,
    J2_NORMALIZED,
    J3_ONLY,
    OFF,
    Policy,
    _dotted_form,
    _is_pure_transform_pair,
    _normalize_vague,
    diagnose_ref_only_row,
    load_dump_outputs,
    load_gold_eval,
    report_for_policy,
    score_example_cf,
    tripwire3_sanity,
)
from praxis_training.finetune.p26c_predictions import TRIPWIRE3

REPO_ROOT = Path(__file__).resolve().parents[2]


def _call(name: str, params: dict) -> dict:
    """One intended call with self-consistent gap fields (mirrors the real
    corpus's invariant: missing_required/unresolved_slots equal what
    ``derive_call_gaps`` yields from these exact params)."""
    gaps = derive_call_gaps(name, params)
    return {
        "name": name,
        "params": params,
        "missing_required": list(gaps.missing_required),
        "unresolved_slots": [
            {"arg_name": s.arg_name, "reference": s.reference, "resource_type": s.resource_type}
            for s in gaps.unresolved_slots
        ],
    }


def _intent(record_id: str, ambiguity_class: str, calls: list[dict]) -> dict:
    return {
        "record_id": record_id,
        "utterance": "synthetic row for eval_revision_brief tests",
        "ambiguity_class": ambiguity_class,
        "calls": calls,
    }


# --------------------------------------------------------------------------
# (i) policies-OFF reproduces the committed reports exactly
# --------------------------------------------------------------------------


@pytest.mark.parametrize("ckpt", sorted(CHECKPOINTS))
def test_off_policy_reproduces_committed_report(ckpt):
    paths = CHECKPOINTS[ckpt]
    dump_path = REPO_ROOT / paths["dump"]
    report_path = REPO_ROOT / paths["report"]
    if not dump_path.exists() or not report_path.exists():
        pytest.skip(f"{ckpt}: recorded artefacts not present in this checkout")

    committed = json.loads(report_path.read_text(encoding="utf-8"))
    intents = load_gold_eval(REPO_ROOT / "training/assemble/out/corpus_p25_sidecar.jsonl")
    outputs = load_dump_outputs(dump_path)

    cf_report = report_for_policy(outputs, intents, OFF)

    assert cf_report["exact_match_accuracy"]["successes"] == committed["exact_match_accuracy"]["successes"]
    assert cf_report["exact_match_accuracy"]["n"] == committed["exact_match_accuracy"]["n"]
    assert cf_report["tripwire_out_of_surface_tool_calls"] == committed["tripwire_out_of_surface_tool_calls"]
    assert cf_report["clarify_recall"]["successes"] == committed["clarify_recall"]["successes"]
    assert cf_report["clarify_precision"]["successes"] == committed["clarify_precision"]["successes"]
    # Row-level identity too, not just the aggregate counts.
    committed_failed = {row["record_id"] for row in committed["exact_match_failures"]}
    cf_failed = {row["record_id"] for row in cf_report["exact_match_failures"]}
    assert cf_failed == committed_failed


def test_off_policy_delegates_to_real_score_example():
    """score_example_cf(..., OFF) must literally be metrics.score_example
    (same object identity of result semantics), not a parallel reimplementation
    that happens to agree today."""
    intent = _intent("row-1", "clean_parse", [_call("aspirate", {"source": "plate_1.C7", "volume_ul": 25.0})])
    raw = "<start_function_call>call:aspirate{source:<escape>plate_1.C7<escape>,volume_ul:25.0}<end_function_call>"
    direct = metrics.score_example(raw, intent)
    via_cf = score_example_cf(raw, intent, OFF)
    assert via_cf == direct


# --------------------------------------------------------------------------
# (ii) synthetic-row unit tests, one per policy
# --------------------------------------------------------------------------


def test_j1_abstains_all_unknown_verb_out_of_surface():
    intent = _intent("oos-1", "out_of_surface", [])  # D7: out-of-surface -> empty calls
    raw = "<start_function_call>call:read_sample{at:[<escape>sample_4<escape>]}<end_function_call>"

    today = score_example_cf(raw, intent, OFF)
    assert today.exact_match is False  # wrong-call failure, not abstention
    assert today.n_calls_emitted == 1  # counts toward tripwire today

    under_j1 = score_example_cf(raw, intent, J1_ONLY)
    assert under_j1.exact_match is True  # now treated as abstention == expected clarify
    assert under_j1.n_calls_emitted == 0  # tripwire no longer counts it
    assert under_j1.clarify_predicted is True
    assert under_j1.clarify_expected is True


def test_j1_leaves_mixed_valid_invalid_calls_alone():
    """J1 only fires when ALL emitted calls are unknown-verb; a row with at
    least one valid call is untouched."""
    intent = _intent("clean-1", "clean_parse", [_call("aspirate", {"source": "plate_1.C7", "volume_ul": 25.0})])
    raw = (
        "<start_function_call>call:aspirate{source:<escape>plate_1.C7<escape>,volume_ul:25.0}<end_function_call>"
        "<start_function_call>call:read_sample{at:[<escape>sample_4<escape>]}<end_function_call>"
    )
    today = score_example_cf(raw, intent, OFF)
    under_j1 = score_example_cf(raw, intent, J1_ONLY)
    assert today == under_j1  # unaffected: not "all" unknown-verb


def test_j1_can_create_a_new_clarify_false_positive():
    """The documented side effect: an all-unknown-verb emission on a row that
    is NOT clarify-expected today scores clarify_predicted=False (emitted-
    but-invalid is excluded from the abstention clause); under J1 it becomes
    a genuine (if spurious) clarify false positive."""
    intent = _intent("clean-2", "clean_parse", [_call("aspirate", {"source": "plate_1.C7", "volume_ul": 25.0})])
    raw = "<start_function_call>call:read_sample{at:[<escape>sample_4<escape>]}<end_function_call>"

    today = score_example_cf(raw, intent, OFF)
    assert today.clarify_expected is False
    assert today.clarify_predicted is False

    under_j1 = score_example_cf(raw, intent, J1_ONLY)
    assert under_j1.clarify_expected is False
    assert under_j1.clarify_predicted is True  # new false positive


def test_j2_normalized_matches_case_and_article_only():
    gold_ref = "the plate"
    pred_ref = "Plate"  # case-fold + no leading article difference only
    assert _normalize_vague(gold_ref) == _normalize_vague(pred_ref) == "plate"

    intent = _intent("amb-1", "ambiguous_referent", [_call("aspirate", {"source": gold_ref, "volume_ul": 50.0})])
    raw = f"<start_function_call>call:aspirate{{source:<escape>{pred_ref}<escape>,volume_ul:50.0}}<end_function_call>"

    assert score_example_cf(raw, intent, OFF).exact_match is False
    assert score_example_cf(raw, intent, J2_NORMALIZED).exact_match is True


def test_j2_normalized_rejects_genuine_content_difference():
    intent = _intent("amb-2", "ambiguous_referent", [_call("aspirate", {"source": "the plate", "volume_ul": 50.0})])
    raw = "<start_function_call>call:aspirate{source:<escape>the box<escape>,volume_ul:50.0}<end_function_call>"
    assert score_example_cf(raw, intent, J2_NORMALIZED).exact_match is False  # "plate" != "box"


def test_j2_any_span_accepts_any_nonempty_reference():
    intent = _intent("amb-3", "ambiguous_referent", [_call("aspirate", {"source": "the plate", "volume_ul": 50.0})])
    raw = "<start_function_call>call:aspirate{source:<escape>some other place entirely<escape>,volume_ul:50.0}<end_function_call>"
    assert score_example_cf(raw, intent, OFF).exact_match is False
    assert score_example_cf(raw, intent, J2_NORMALIZED).exact_match is False  # not cosmetically equal
    assert score_example_cf(raw, intent, J2_ANY_SPAN).exact_match is True  # any non-empty span accepted


def test_j2_scoped_to_ambiguous_referent_class_only():
    """The relaxation must not leak into non-ambiguous-referent rows even
    when a SYMBOLIC_RESOURCE_REF arg differs in content."""
    intent = _intent("clean-3", "clean_parse", [_call("aspirate", {"source": "plate_1.C7", "volume_ul": 25.0})])
    raw = "<start_function_call>call:aspirate{source:<escape>plate_2.C7<escape>,volume_ul:25.0}<end_function_call>"
    assert score_example_cf(raw, intent, J2_ANY_SPAN).exact_match is False


def test_j3_pure_transform_underscore_to_dotted():
    assert _dotted_form("tube_rack_B3") == "tube_rack.B3"
    assert _dotted_form("tube_rack.B3") == "tube_rack.B3"
    assert _is_pure_transform_pair("tube_rack_B3", "tube_rack.B3") is True

    intent = _intent("golden-clean-1", "clean_parse", [_call("aspirate", {"source": "tube_rack_B3", "volume_ul": 10.0})])
    raw = "<start_function_call>call:aspirate{source:<escape>tube_rack.B3<escape>,volume_ul:10.0}<end_function_call>"

    assert score_example_cf(raw, intent, OFF).exact_match is False
    assert score_example_cf(raw, intent, J3_ONLY).exact_match is True

    diag = diagnose_ref_only_row(raw, intent)
    assert diag == [{"arg_name": "source", "gold_reference": "tube_rack_B3", "predicted_reference": "tube_rack.B3"}]


def test_j3_conservative_no_lookup_no_guess():
    """A content difference that happens to share a well suffix but a
    DIFFERENT prefix is NOT a pure transform -- no lookup table, no guessing."""
    assert _dotted_form("plate_1") is None  # no well suffix at all
    assert _is_pure_transform_pair("source_plate_A1", "source_plate_well_A1") is False  # different prefix

    intent = _intent(
        "golden-clean-2", "clean_parse", [_call("aspirate", {"source": "source_plate_A1", "volume_ul": 10.0})]
    )
    raw = "<start_function_call>call:aspirate{source:<escape>source_plate_well_A1<escape>,volume_ul:10.0}<end_function_call>"
    assert score_example_cf(raw, intent, J3_ONLY).exact_match is False  # stays a miss

    diag = diagnose_ref_only_row(raw, intent)
    # Still flagged as a "reference-string-only" miss (nothing else differs)...
    assert diag == [{"arg_name": "source", "gold_reference": "source_plate_A1", "predicted_reference": "source_plate_well_A1"}]


def test_combined_policy_stacks_all_three():
    """COMBINED = J1 + J2(normalized) + J3(pure transform); a row exercising
    only J3 still flips under COMBINED."""
    intent = _intent("golden-clean-3", "clean_parse", [_call("aspirate", {"source": "tube_rack_B3", "volume_ul": 10.0})])
    raw = "<start_function_call>call:aspirate{source:<escape>tube_rack.B3<escape>,volume_ul:10.0}<end_function_call>"
    assert score_example_cf(raw, intent, COMBINED).exact_match is True
    assert COMBINED.j1_abstain_unknown_verb and COMBINED.j2_mode == "normalized" and COMBINED.j3_pure_transform


def test_policy_off_is_noop_flag():
    assert Policy().is_noop is True
    assert J1_ONLY.is_noop is False
    assert J2_NORMALIZED.is_noop is False
    assert J3_ONLY.is_noop is False


# --------------------------------------------------------------------------
# (iii) TRIPWIRE3 sanity against the committed reports
# --------------------------------------------------------------------------


@pytest.mark.parametrize("ckpt", ["A2", "A3"])
def test_tripwire3_present_in_committed_failures(ckpt):
    report_path = REPO_ROOT / CHECKPOINTS[ckpt]["report"]
    if not report_path.exists():
        pytest.skip(f"{ckpt}: committed report not present in this checkout")
    result = tripwire3_sanity(report_path)
    assert result["tripwire3_ids"] == list(TRIPWIRE3)
    assert result["all_present"] is True
    assert all(result["present_in_failures"].values())


def test_tripwire3_not_claimed_for_checkpoint_a():
    """TRIPWIRE3 is explicitly an A2/A3-discovered row list (p26c_predictions
    docstring: "the three out-of-surface eval rows A2 emitted a call on");
    checkpoint A is not expected to reproduce it."""
    report_path = REPO_ROOT / CHECKPOINTS["A"]["report"]
    if not report_path.exists():
        pytest.skip("A: committed report not present in this checkout")
    result = tripwire3_sanity(report_path)
    assert result["all_present"] is False
