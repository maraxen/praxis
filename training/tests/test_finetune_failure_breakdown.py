"""failure_breakdown classifies scorer reasons on synthetic ground truth
(BATHOS rule: verify the measurement before trusting it)."""

from praxis_training.finetune.failure_breakdown import (
    _decode_escaped_list, breakdown_report, classify_reasons,
)

SLOT_A = "DerivedSlot(arg_name='source', reference='p.D1', resource_type='container')"
SLOT_B = "DerivedSlot(arg_name='destination', reference='p.H5', resource_type='container')"


def test_decode_escaped_list():
    assert _decode_escaped_list("[<escape>a<escape>,<escape>b<escape>]") == ["a", "b"]
    assert _decode_escaped_list("[<escape>tip_rack.C5<escape>]") == ["tip_rack.C5"]
    assert _decode_escaped_list("plain") == "plain"
    assert _decode_escaped_list(3) == 3


def test_categories():
    assert classify_reasons(["sequence length 0 != intended 1"]) == "no_call"
    assert classify_reasons(["sequence length 1 != intended 0"]) == "spurious_call"
    assert classify_reasons(["unknown/excluded tool name 'x' (not clarify-routing)",
                             "emitted call(s) but all to unknown/excluded verbs"]) == "unknown_verb"
    assert classify_reasons(["name mismatch: 0: predicted 'a' != intended 'b'",
                             "params mismatch: 0: predicted {} != intended {}"]) == "name_mismatch"
    list_only = [
        "params mismatch: 0: predicted {'at': '[<escape>A7<escape>]'} != intended {'at': ['A7']}",
        f"0: unresolved_slots derived ({SLOT_A},) != intended ({SLOT_B},)",
    ]
    assert classify_reasons(list_only) == "list_escape_format"
    content = ["params mismatch: 0: predicted {'destination': 'plate[1]'} != intended {'destination': 'plate_1.D1'}"]
    assert classify_reasons(content) == "param_content"
    mixed = ["params mismatch: 0: predicted {'at': '[<escape>A7<escape>]', 'v': 5} != intended {'at': ['A7'], 'v': 6}"]
    assert classify_reasons(mixed) == "param_content"
    order = [f"0: unresolved_slots derived ({SLOT_B}, {SLOT_A}) != intended ({SLOT_A}, {SLOT_B})"]
    assert classify_reasons(order) == "slot_order_only"
    different_slots = [f"0: unresolved_slots derived ({SLOT_B},) != intended ({SLOT_A}, {SLOT_B})"]
    assert classify_reasons(different_slots) == "gold_slot_annotation"
    unannotated = [f"0: unresolved_slots derived ({SLOT_A},) != intended ()"]
    assert classify_reasons(unannotated) == "gold_slot_annotation"
    assert classify_reasons(["gap derivation failed (unknown/excluded tool): 'z'"]) == "other"


def test_breakdown_sums_and_ceiling():
    rep = {
        "n_examples": 10,
        "exact_match_accuracy": {"successes": 4, "n": 10, "value": 0.4, "wilson95": [0, 1]},
        "exact_match_failures": [
            {"record_id": "r1", "class": "clean_parse", "reasons": ["sequence length 0 != intended 1"]},
            {"record_id": "r2", "class": "clean_parse",
             "reasons": [f"0: unresolved_slots derived ({SLOT_B}, {SLOT_A}) != intended ({SLOT_A}, {SLOT_B})"]},
            {"record_id": "r3", "class": "missing_slot",
             "reasons": ["params mismatch: 0: predicted {'at': '[<escape>A7<escape>]'} != intended {'at': ['A7']}"]},
        ],
    }
    b = breakdown_report(rep)
    assert sum(b["by_category"].values()) == 3 == b["n_failures"]
    assert b["artifact_rows"] == 2
    assert abs(b["artifact_adjusted_accuracy_ceiling"] - 0.6) < 1e-9
    assert b["by_class_and_category"]["clean_parse"] == {"no_call": 1, "slot_order_only": 1}


MISSING = "0: missing_required derived ('source',) != intended ()"


def test_gold_missing_required_category():
    # params equal (no params line), only gap lines, at least one missing_required line
    assert classify_reasons([MISSING]) == "gold_missing_required"
    assert classify_reasons([MISSING, f"0: unresolved_slots derived ({SLOT_A},) != intended ()"]) == "gold_missing_required"
    # with a params line the row is a genuine miss, not a gold defect
    assert classify_reasons(["params mismatch: 0: predicted {} != intended {'source': 'x'}", MISSING]) == "param_content"


def test_decode_escaped_list_comma_inside_escape():
    assert _decode_escaped_list("[<escape>a,b<escape>,<escape>c<escape>]") == ["a,b", "c"]
    assert _decode_escaped_list("[]") == []


def test_artifact_record_ids_listed():
    rep = {
        "n_examples": 10,
        "exact_match_accuracy": {"successes": 4, "n": 10, "value": 0.4, "wilson95": [0, 1]},
        "exact_match_failures": [
            {"record_id": "r1", "class": "clean_parse", "reasons": ["sequence length 0 != intended 1"]},
            {"record_id": "r2", "class": "clean_parse",
             "reasons": [f"0: unresolved_slots derived ({SLOT_B}, {SLOT_A}) != intended ({SLOT_A}, {SLOT_B})"]},
            {"record_id": "r3", "class": "missing_slot",
             "reasons": ["params mismatch: 0: predicted {'at': '[<escape>A7<escape>]'} != intended {'at': ['A7']}"]},
            {"record_id": "r4", "class": "missing_slot", "reasons": [MISSING]},
        ],
    }
    b = breakdown_report(rep)
    assert b["artifact_rows"] == 3
    assert b["artifact_record_ids"] == {"list_escape_format": ["r3"], "slot_order_only": ["r2"],
                                        "gold_slot_annotation": [], "gold_missing_required": ["r4"]}
