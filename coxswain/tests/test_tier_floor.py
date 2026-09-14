"""AC-14 (tier floor): the static assignment itself cannot bypass the product.

A schema tagging everything read_only satisfies AC-8 while making every call
execute on propose -- this file floors the assignment: mutators are never
read_only, the waste family is irreversible, and the checks are CLOSED over
the schema so a new mutating-but-read_only entry fails without anyone
remembering to update a hand-listed allowlist.
"""

import pytest

from coxswain.plr import tool_schema
from coxswain.schema.types import RiskTier

#: AC-14 assertion 1 minimum set of state-mutating calls.
MUTATORS = {
    "drop_tips",
    "discard_tips",
    "pick_up_tips",
    "aspirate",
    "dispense",
    "transfer",
    "move_resource",
    "move_plate",
    "move_lid",
}

#: AC-14 assertion 2: the irreversible family.
IRREVERSIBLE_FAMILY = {"drop_tips", "discard_tips", "dispense_to_waste"}


def test_all_named_mutators_exist_in_schema() -> None:
    missing = MUTATORS - set(tool_schema.TOOL_SCHEMA)
    assert missing == set(), f"schema is missing required mutators: {sorted(missing)}"


@pytest.mark.parametrize("name", sorted(MUTATORS))
def test_no_state_mutating_call_is_read_only(name: str) -> None:
    assert tool_schema.TOOL_SCHEMA[name].risk_tier is not RiskTier.READ_ONLY


@pytest.mark.parametrize("name", sorted(IRREVERSIBLE_FAMILY))
def test_irreversible_family_is_irreversible(name: str) -> None:
    assert tool_schema.TOOL_SCHEMA[name].risk_tier is RiskTier.IRREVERSIBLE


# --- structural closure over the schema ---------------------------------------


def test_effect_declaring_entries_are_never_read_only() -> None:
    """Closed check: ANY entry (today's or newly added) declaring a non-empty
    effect set must carry reversible or irreversible."""
    offenders = [
        name
        for name, spec in tool_schema.TOOL_SCHEMA.items()
        if spec.effects and spec.risk_tier is RiskTier.READ_ONLY
    ]
    assert offenders == []


def test_waste_entries_must_be_irreversible() -> None:
    """A new waste-destination entry tagged anything else fails here, not in
    production."""
    offenders = [
        name
        for name, spec in tool_schema.TOOL_SCHEMA.items()
        if spec.to_waste and spec.risk_tier is not RiskTier.IRREVERSIBLE
    ]
    assert offenders == []


def test_drops_effects_must_be_irreversible() -> None:
    offenders = [
        name
        for name, spec in tool_schema.TOOL_SCHEMA.items()
        if "drops_tips" in spec.effects and spec.risk_tier is not RiskTier.IRREVERSIBLE
    ]
    assert offenders == []


def test_read_only_entries_declare_no_effects() -> None:
    """Consistency floor: a reader that declared effects would contradict the
    two structural checks above."""
    readers = [n for n, s in tool_schema.TOOL_SCHEMA.items() if s.risk_tier is RiskTier.READ_ONLY]
    assert readers, "expected at least one read_only entry"
    for name in readers:
        assert not tool_schema.TOOL_SCHEMA[name].effects, name


def test_effects_use_the_ported_contract_vocabulary() -> None:
    """Effect strings stay aligned with the ported method_contracts EffectType
    values so cue-3 evaluation can join the two tables without translation."""
    from coxswain.fft.preconditions.method_contracts import EffectType

    allowed = {e.value for e in EffectType}
    for name, spec in tool_schema.TOOL_SCHEMA.items():
        unknown = spec.effects - allowed
        assert unknown == set(), f"{name}: unknown effects {sorted(unknown)}"
