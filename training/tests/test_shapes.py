"""Shape-validation tests for P2.4 (AC-2.4.x): namespace-table legality."""

from __future__ import annotations

from overlay_gen.shapes import validate_call, validate_row


def good_call(name="aspirate", params=None, receiver_type="liquid_handler"):
    return {
        "name": name,
        "receiver_type": receiver_type,
        "params": params
        if params is not None
        else {"source": "plate['A1']", "volume_ul": [10.0]},
    }


def good_row(**overrides):
    row = {
        "id": "ovl-abcdef1234",
        "instruction": "aspirate 10 uL from A1 please",
        "call": good_call(),
        "provenance": {
            "provenance": "naturalness",
            "source_notebook_or_protocol": "x.ipynb",
            "generator": "training/overlay_gen (P2.4)",
            "prompt_version": "p24-naturalness-v1",
            "teacher_model_version": "titanix-vllm-primary",
        },
    }
    row.update(overrides)
    return row


def test_valid_call_passes():
    assert validate_call(good_call()) == []


def test_excluded_verb_rejected():
    errors = validate_call(good_call(name="mix"))
    assert any("phase-2 surface" in e for e in errors)


def test_unknown_param_rejected():
    errors = validate_call(good_call(params={"source": "p['A1']", "volume_ul": [1], "speed": 5}))
    assert any("outside namespace" in e for e in errors)


def test_missing_required_rejected():
    errors = validate_call(good_call(params={"source": "p['A1']"}))
    assert any("missing required" in e for e in errors)


def test_wrong_receiver_type_rejected():
    errors = validate_call(good_call(receiver_type="plate_reader"))
    assert any("receiver_type" in e for e in errors)


def test_symbolic_param_must_be_string():
    errors = validate_call(good_call(params={"source": 12, "volume_ul": [10.0]}))
    assert any("symbolic" in e for e in errors)


def test_cardinality_enforced():
    errs_scalar = validate_call(good_call(params={"source": ["a"], "volume_ul": [10.0]}))
    assert any("cardinality scalar" in e for e in errs_scalar)
    errs_list = validate_call(
        good_call(
            name="pick_up_tips",
            params={"at": "rack['A1']"},
        )
    )
    assert any("cardinality list" in e for e in errs_list)


def test_optional_params_allowed_absent():
    call = good_call(
        name="read_luminescence",
        receiver_type="plate_reader",
        params={"focal_height_mm": 20.0},
    )
    assert validate_call(call) == []  # 'at' optional


def test_row_provenance_required():
    row = good_row()
    del row["provenance"]["prompt_version"]
    errors = validate_row(row)
    assert any("prompt_version" in e for e in errors)


def test_row_provenance_tag_value_pinned():
    row = good_row()
    row["provenance"]["provenance"] = "synthetic"
    errors = validate_row(row)
    assert any("naturalness" in e for e in errors)


def test_row_instruction_blank_rejected():
    errors = validate_row(good_row(instruction="   "))
    assert any("non-empty" in e for e in errors)


def test_row_embedded_call_validated():
    errors = validate_row(good_row(call=good_call(name="shake")))
    assert any("phase-2 surface" in e for e in errors)
