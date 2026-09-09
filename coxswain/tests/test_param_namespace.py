"""Canonical param namespace integrity (P2.0 deliverable 2, C-B2 fix).

The namespace table is THE contract between the copilot surface (schema param
names) and vendored PLR kwargs. These tests pin its structural invariants:
totality over the phase-2 surface, symbolic/literal hygiene, fixture
vocabulary coverage, and loader totality.
"""

import json
from pathlib import Path

import pytest

from coxswain.plr.param_namespace import (
    PARAM_NAMESPACE,
    ParamKind,
    params_of,
    required_params,
    symbolic_slots,
)
from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES, TOOL_SCHEMA

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "parsed_calls"


def test_every_phase2_tool_has_a_table_entry() -> None:
    missing = sorted(set(PHASE2_TOOL_NAMES) - set(PARAM_NAMESPACE))
    assert missing == [], f"phase-2 tools without a namespace entry: {missing}"


def test_every_table_entry_is_a_phase2_tool() -> None:
    stray = sorted(set(PARAM_NAMESPACE) - set(PHASE2_TOOL_NAMES))
    assert stray == [], f"namespace entries for non-phase-2 tools: {stray}"


def test_symbolic_specs_carry_resource_type() -> None:
    for tool, specs in sorted(PARAM_NAMESPACE.items()):
        for pspec in specs:
            if pspec.kind is ParamKind.SYMBOLIC_RESOURCE_REF:
                assert pspec.resource_type, (
                    f"{tool}.{pspec.name}: symbolic param needs a resource_type"
                )
            else:
                assert pspec.resource_type is None, (
                    f"{tool}.{pspec.name}: literal params carry no resource_type"
                )


def test_excluded_tools_have_no_table_entry() -> None:
    """Excluded-from-generation tools must not be dispatchable through the
    namespace: no entry means derive_call_gaps fails loudly."""
    excluded = [n for n, s in TOOL_SCHEMA.items() if not s.phase2_included]
    assert excluded, "sanity: expected recorded exclusions"
    for name in excluded:
        with pytest.raises(KeyError):
            params_of(name)


# --- AC-2.0.x: every fixture param name maps to a PLR kwarg or is declared ----


def _fixture_files():
    return sorted(FIXTURES_DIR.glob("*.json"))


def test_all_fixtures_covered_by_namespace() -> None:
    files = _fixture_files()
    assert len(files) == 6, "golden corpus size drifted; update this suite consciously"
    for path in files:
        fixture = json.loads(path.read_text())
        name = fixture["name"]
        assert name in PARAM_NAMESPACE, f"{path.name}: tool {name!r} not in phase-2 surface"
        table_names = {pspec.name for pspec in params_of(name)}
        for key in fixture.get("params", {}):
            assert key in table_names, (
                f"{path.name}: fixture param {key!r} has no mapping in the "
                f"{name} namespace entry"
            )


def test_fixture_tools_are_phase2_included() -> None:
    for path in _fixture_files():
        fixture = json.loads(path.read_text())
        assert TOOL_SCHEMA[fixture["name"]].phase2_included, path.name


def test_fixture_vocabulary_is_normalized() -> None:
    """C-B2: the fixtures' normalized vocabulary (source/destination/volume_ul/
    at/wavelength_nm/what) must stay stable across the corpus."""
    observed = {
        key
        for path in _fixture_files()
        for key in json.loads(path.read_text()).get("params", {})
    }
    assert observed == {"source", "destination", "volume_ul", "what", "at", "wavelength_nm"}


# --- Loader ---------------------------------------------------------------------


def test_required_params_transfer_matches_signature_shape() -> None:
    assert required_params("transfer") == ("source", "destination")
    assert required_params("aspirate") == ("source", "volume_ul")
    assert required_params("stamp") == ("source", "destination", "volume_ul")


def test_symbolic_slots_returns_only_symbolic_specs() -> None:
    slots = symbolic_slots("transfer")
    assert [s.name for s in slots] == ["source", "destination"]
    assert all(s.kind is ParamKind.SYMBOLIC_RESOURCE_REF for s in slots)


def test_params_of_returns_frozen_tuple_of_specs() -> None:
    specs = params_of("aspirate")
    assert isinstance(specs, tuple)
    with pytest.raises((AttributeError, TypeError)):
        specs[0].name = "mutated"  # type: ignore[misc]


def test_read_family_wells_param_is_declared_literal_positional() -> None:
    """Recorded decision: read_*.at holds well POSITIONS relative to the plate
    already inside the reader -- index-like, not deck-object references -- so
    it is literal and never produces an unresolved slot."""
    from coxswain.plr.slot_derivation import derive_call_gaps

    gaps = derive_call_gaps("read_absorbance", {"at": "A1", "wavelength_nm": 600})
    assert gaps.unresolved_slots == ()
    assert gaps.missing_required == ()
