"""Hardened-parser tests: every hardening rule gets a case (P2.1 deliverable 2)."""

import pytest

from praxis_training.baseline_eval.fgml_parser import parse_function_calls


def test_basic_call_with_escapes():
    raw = '<start_function_call>call:aspirate{source:<escape>reservoir_1<escape>,volume_ul:<escape>50<escape>}<end_function_call>'
    result = parse_function_calls(raw)
    assert result.errors == []
    assert len(result.calls) == 1
    call = result.calls[0]
    assert call.name == "aspirate"
    assert call.params == {"source": "reservoir_1", "volume_ul": 50}  # numeric coercion
    assert isinstance(call.params["volume_ul"], int)


def test_bare_unescaped_values_tolerated():
    raw = "<start_function_call>call:read_absorbance{wavelength_nm:600, at:A1}<end_function_call>"
    result = parse_function_calls(raw)
    assert result.calls[0].params == {"wavelength_nm": 600, "at": "A1"}


def test_float_coercion():
    raw = "<start_function_call>call:read_luminescence{focal_height_mm:<escape>12.5<escape>}<end_function_call>"
    result = parse_function_calls(raw)
    assert result.calls[0].params["focal_height_mm"] == 12.5
    assert isinstance(result.calls[0].params["focal_height_mm"], float)


def test_multiple_spans_parallel_calls():
    raw = (
        "<start_function_call>call:pick_up_tips{at:<escape>rack_A1<escape>}<end_function_call>"
        "junk in between ignored"
        "<start_function_call>call:drop_tips{destination:<escape>trash<escape>}<end_function_call>"
    )
    result = parse_function_calls(raw)
    assert [c.name for c in result.calls] == ["pick_up_tips", "drop_tips"]


def test_truncated_span_recovers_best_effort():
    raw = "<start_function_call>call:transfer{source:<escape>a<escape>,volume_ul:<escape>5<escape>"
    result = parse_function_calls(raw)
    assert result.calls and result.calls[0].name == "transfer"
    assert result.calls[0].params == {"source": "a", "volume_ul": 5}
    assert any("truncated" in note for note in result.notes)


def test_commas_and_braces_inside_escape_values_are_literal():
    raw = (
        "<start_function_call>call:move_resource{resource:<escape>tube{x},1<escape>,"
        "destination:<escape>a:b,c<escape>}<end_function_call>"
    )
    result = parse_function_calls(raw)
    assert result.calls[0].params == {"resource": "tube{x},1", "destination": "a:b,c"}


def test_missing_call_prefix_is_an_error_not_a_crash():
    raw = "<start_function_call>get_weather{city:<escape>Tokyo<escape>}<end_function_call>"
    result = parse_function_calls(raw)
    assert result.calls == []
    assert result.errors and "prefix" in result.errors[0]


def test_empty_param_block():
    raw = "<start_function_call>call:pick_up_tips{}<end_function_call>"
    result = parse_function_calls(raw)
    assert result.calls[0].name == "pick_up_tips"
    assert result.calls[0].params == {}


def test_duplicate_key_last_wins_with_note():
    raw = "<start_function_call>call:aspirate{volume_ul:<escape>1<escape>,volume_ul:<escape>2<escape>}<end_function_call>"
    result = parse_function_calls(raw)
    assert result.calls[0].params["volume_ul"] == 2
    assert any("duplicate key" in n for n in result.notes)


def test_no_spans_yields_empty_result():
    result = parse_function_calls("The weather is nice. <end_of_turn>")
    assert result.calls == []
    assert result.errors == []


def test_whitespace_tolerance_around_name_and_args():
    raw = "<start_function_call>call: dispense { destination : <escape>trash<escape> } <end_function_call>"
    result = parse_function_calls(raw)
    assert result.calls[0].name == "dispense"
    assert result.calls[0].params == {"destination": "trash"}


def test_non_string_inputs_never_mutated_and_garbage_safe():
    for raw in ("", "<start_function_call>", "<start_function_call>call:", None if False else ""):
        parse_function_calls(raw)  # must not raise


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("<escape>hello world<escape>", "hello world"),
        ("<escape><escape>nested<escape><escape>", "nested"),
        ("bare", "bare"),
        ("  padded  ", "padded"),
    ],
)
def test_value_stripping_matrix(value, expected):
    from praxis_training.baseline_eval.fgml_parser import _strip_escapes

    assert _strip_escapes(value) == expected


# ---------------------------------------------------------------------------
# 260902: nested values, mirroring the chat template's format_argument macro
# ---------------------------------------------------------------------------

def _one(raw: str):
    res = parse_function_calls(f"<start_function_call>call:t{{{raw}}}<end_function_call>")
    assert not res.errors, res.errors
    assert len(res.calls) == 1
    return res.calls[0].params


def test_list_of_escaped_strings():
    assert _one("at:[<escape>tip_rack.C5<escape>]") == {"at": ["tip_rack.C5"]}
    assert _one("at:[<escape>a<escape>,<escape>b<escape>],v:5") == {"at": ["a", "b"], "v": 5}


def test_empty_list():
    assert _one("at:[]") == {"at": []}


def test_list_with_comma_and_bracket_inside_escape():
    assert _one("at:[<escape>a,b<escape>,<escape>c]d<escape>]") == {"at": ["a,b", "c]d"]}


def test_list_of_bare_numbers_coerces_elements():
    assert _one("xs:[1,2.5,<escape>3<escape>]") == {"xs": [1, 2.5, 3]}


def test_nested_mapping_value_bare_and_escaped_keys():
    assert _one("dst:{x:1,y:<escape>two<escape>}") == {"dst": {"x": 1, "y": "two"}}
    assert _one("dst:{<escape>x<escape>:1}") == {"dst": {"x": 1}}
    assert _one("dst:{a:[<escape>p<escape>],b:{c:2}}") == {"dst": {"a": ["p"], "b": {"c": 2}}}


def test_escaped_scalar_starting_with_bracket_stays_string():
    assert _one("s:<escape>[not a list]<escape>") == {"s": "[not a list]"}
    assert _one("s:<escape>{k:v}<escape>") == {"s": "{k:v}"}


def test_existing_scalar_behaviour_unchanged():
    # bare numbers, escaped numbers, bare text: exactly as before the fix
    assert _one("volume_ul:50") == {"volume_ul": 50}
    assert _one("volume_ul:<escape>12.5<escape>") == {"volume_ul": 12.5}
    assert _one("well:A1") == {"well": "A1"}
