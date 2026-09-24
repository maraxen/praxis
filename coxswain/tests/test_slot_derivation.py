"""D11 deterministic derivation: slot classification over the canonical
namespace (P2.0 deliverable 3).

Given a tool name + parse-layer params, classify string-valued args via the
TABLE (never value heuristics) into literal vs symbolic-resource-reference,
and derive ``missing_required`` / ``unresolved_slots`` exactly as D11
promises: deterministically, post-parse, outside model hands.
"""

import pytest

from coxswain.plr.slot_derivation import CallGaps, DerivedSlot, derive_call_gaps


# --- missing_required -----------------------------------------------------------


def test_missing_required_single() -> None:
    gaps = derive_call_gaps("aspirate", {"source": "A1"})  # volume_ul absent
    assert gaps.missing_required == ("volume_ul",)
    # "A1" is symbolic but present; missing-ness does not suppress slots.
    assert [s.arg_name for s in gaps.unresolved_slots] == ["source"]


def test_missing_required_multiple_follows_table_order() -> None:
    gaps = derive_call_gaps("transfer", {})
    assert gaps.missing_required == ("source", "destination")


def test_explicit_none_counts_as_absent() -> None:
    gaps = derive_call_gaps("aspirate", {"source": "A1", "volume_ul": None})
    assert gaps.missing_required == ("volume_ul",)


def test_no_missing_when_all_required_present() -> None:
    gaps = derive_call_gaps("aspirate", {"source": "A1", "volume_ul": 10.0})
    assert gaps.missing_required == ()


def test_optional_params_never_reported_missing() -> None:
    gaps = derive_call_gaps("discard_tips", {})
    assert gaps.missing_required == ()  # vendored discard_tips has zero required kwargs


# --- unresolved_slots -----------------------------------------------------------


def test_symbolic_string_becomes_slot_with_resource_type() -> None:
    gaps = derive_call_gaps("aspirate", {"source": "A1", "volume_ul": 10})
    assert gaps.unresolved_slots == (
        DerivedSlot(arg_name="source", reference="A1", resource_type="container"),
    )


def test_literal_strings_are_never_slots() -> None:
    """The table decides, not stringiness: 'what' is a literal noun key."""
    gaps = derive_call_gaps("discard_tips", {"what": "tips", "at": "C3"})
    assert [s.arg_name for s in gaps.unresolved_slots] == ["at"]


def test_numeric_values_are_never_slots() -> None:
    gaps = derive_call_gaps("read_absorbance", {"wavelength_nm": 600, "at": "A1"})
    assert gaps.unresolved_slots == ()


def test_list_of_strings_yields_one_slot_per_element_in_order() -> None:
    gaps = derive_call_gaps(
        "transfer",
        {"source": "A1", "destination": ["B1", "B2", "B3"]},
    )
    assert gaps.unresolved_slots == (
        DerivedSlot("source", "A1", "container"),
        DerivedSlot("destination", "B1", "container"),
        DerivedSlot("destination", "B2", "container"),
        DerivedSlot("destination", "B3", "container"),
    )
    ordered = [s.reference for s in gaps.unresolved_slots]
    assert ordered == ["A1", "B1", "B2", "B3"]


def test_empty_collection_is_present_but_slotless() -> None:
    """Presence-based rule: an empty list satisfies required-ness (dispatch may
    still reject it; that is not this function's job)."""
    gaps = derive_call_gaps("transfer", {"source": [], "destination": []})
    assert gaps.missing_required == ()
    assert gaps.unresolved_slots == ()


def test_structured_values_of_symbolic_params_are_not_slots() -> None:
    """move_*.destination accepts a Coordinate payload; non-string structured
    values are treated as grounded literals."""
    coord = {"x": 10.0, "y": 20.0, "z": 0.0}
    gaps = derive_call_gaps(
        "move_plate",
        {"plate": "plate_1", "destination": coord},
    )
    assert [s.arg_name for s in gaps.unresolved_slots] == ["plate"]


# --- unknown params -------------------------------------------------------------


def test_unknown_params_reported_advisory_not_fatal() -> None:
    """Worker output is advisory-only (C-M1); the gate must stay total."""
    gaps = derive_call_gaps("aspirate", {"source": "A1", "volume_ul": 5, "speed": "fast"})
    assert gaps.unknown_params == ("speed",)
    assert gaps.missing_required == ()


# --- totality / purity -----------------------------------------------------------


def test_unknown_tool_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        derive_call_gaps("no_such_verb", {})


def test_excluded_tool_raises_keyerror() -> None:
    """Phantom verbs have no namespace entry: generation cannot reach them and
    derivation fails loudly instead of inventing a contract."""
    with pytest.raises(KeyError):
        derive_call_gaps("mix", {"resource": "A1"})


def test_input_mapping_is_not_mutated() -> None:
    params = {"source": "A1", "extra": "x"}
    snapshot = dict(params)
    derive_call_gaps("aspirate", params)
    assert params == snapshot


def test_result_defaults_are_immutable_tuples() -> None:
    gaps = derive_call_gaps("discard_tips", {})
    assert isinstance(gaps, CallGaps)
    assert gaps.missing_required == ()
    assert gaps.unresolved_slots == ()
