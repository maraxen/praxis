"""#5622 T60 (spec 260929_plr-sema-plr1-tip-effect-increment.md §18.5.2, AC-18.10): the sixth observation
field ``tip_racks_available`` and the harness's ability to build a lidded tip rack
(``DeckLayout.lidded_tip_racks``).

Every fixture here is built from REAL PLR objects -- a real ``Lid`` assigned through PLR's own
``Liddable.assign_child_resource`` -- so a positive (lidded -> ``False``) and a negative (clean -> ``True``)
control both read PLR's own ``_available_for_tip_handling`` property, not a stub.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from pylabrobot.resources import Lid, ResourceStack, TipRack

from verify.deck import DeckLayout, build_setup, capture_observation

BACKEND = "LiquidHandlerChatterboxBackend"

#: sha256 of ``{"topology": deck.serialize(), "state": deck.serialize_all_state()}`` (sorted keys) for three
#: LEGACY layouts, computed at HEAD BEFORE T60 touched ``build_setup`` (``plr10_tools/t60/gen_default_layout_pins.py``).
#: A layout that does not name ``lidded_tip_racks`` must still build exactly this deck.
_PRE_T60_DECK_DIGESTS = {
    "empty": ({}, "bfceaa28e5c1f28d00273c7e8f378094a405efb0ac183bf2edda4057e4abed2f"),
    "two_racks_plate_trough_holder": (
        {
            "resources": {"tip_rack": "TipRack", "tips_b": "TipRack", "src": "Plate", "reservoir": "Trough"},
            "holders": ["park1"],
        },
        "f951e1f65bdef7de34dc90cd8b1cf9461314a8251444a67a822a95d8d4250e05",
    ),
    "seeded": (
        {"resources": {"src": "Plate"}, "seed_volumes": {"src.A1": 100.0}},
        "0c8adb217174fcab8aaca1be725f91695ec4ceea1c9d503505a81ff9536d9451",
    ),
}


def _deck_digest(layout: DeckLayout) -> str:
    setup = build_setup(BACKEND, layout)
    blob = json.dumps(
        {"topology": setup.deck.serialize(), "state": setup.deck.serialize_all_state()},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(blob.encode()).hexdigest()


def _walk(node):
    stack = [node]
    while stack:
        cur = stack.pop()
        yield cur
        stack.extend(getattr(cur, "children", []))


def _lids(setup):
    return [n for n in _walk(setup.deck) if isinstance(n, Lid)]


# --- DeckLayout.lidded_tip_racks: the field, merged(), and the default-unchanged pin -----------------------------


def test_lidded_tip_racks_field_defaults_to_an_independent_empty_list():
    a, b = DeckLayout(), DeckLayout()
    assert a.lidded_tip_racks == [] and b.lidded_tip_racks == []
    a.lidded_tip_racks.append("x")
    assert b.lidded_tip_racks == [], "the default must not be a shared mutable list"


def test_merged_concatenates_lidded_tip_racks_like_holders():
    base = DeckLayout(resources={"a": "TipRack"}, lidded_tip_racks=["a"], holders=["h1"])
    other = DeckLayout(resources={"b": "TipRack"}, lidded_tip_racks=["b"], holders=["h2"])
    merged = base.merged(other)
    assert merged.lidded_tip_racks == ["a", "b"]
    assert merged.holders == ["h1", "h2"]
    assert base.merged(None) is base
    # infer_layout's own layouts never carry the field, so an explicit layout's value must survive a merge with one
    assert DeckLayout().merged(DeckLayout(lidded_tip_racks=["tip_rack"])).lidded_tip_racks == ["tip_rack"]
    assert DeckLayout(lidded_tip_racks=["tip_rack"]).merged(DeckLayout()).lidded_tip_racks == ["tip_rack"]


@pytest.mark.parametrize("name", sorted(_PRE_T60_DECK_DIGESTS))
def test_default_layout_builds_exactly_the_pre_t60_deck(name):
    """AC-18.10's default-layout-unchanged test. The digest was taken at HEAD before this change, so this is a
    check against the OLD behaviour and cannot pass by construction."""
    kwargs, expected = _PRE_T60_DECK_DIGESTS[name]
    layout = DeckLayout(**kwargs)
    assert layout.lidded_tip_racks == []
    assert _deck_digest(layout) == expected
    # and an explicit empty list is the same layout
    assert _deck_digest(DeckLayout(**kwargs, lidded_tip_racks=[])) == expected


def test_default_layout_places_no_lid_anywhere():
    setup = build_setup(BACKEND, DeckLayout(resources={"tips_b": "TipRack", "src": "Plate"}))
    assert _lids(setup) == []
    assert all(n.lid is None for n in _walk(setup.deck) if isinstance(n, TipRack))


# --- build_setup: a real Lid on each named rack ------------------------------------------------------------------


def test_lidded_rack_gets_a_real_lid_sized_to_the_rack():
    setup = build_setup(BACKEND, DeckLayout(lidded_tip_racks=["tip_rack"]))
    rack = setup.resources["tip_rack"]
    assert isinstance(rack, TipRack)
    lid = rack.lid
    assert isinstance(lid, Lid), "a real PLR Lid, not a Plate standing in for one"
    assert lid.parent is rack
    assert lid.get_size_x() >= rack.get_size_x() and lid.get_size_y() >= rack.get_size_y()
    assert lid.nesting_z_height != 0, "nonzero nesting: PLR prints a warning for 0 and it is not a physical lid"
    assert rack._available_for_tip_handling is False
    assert _lids(setup) == [lid]


def test_lid_name_is_deck_unique_even_when_the_natural_name_is_taken():
    setup = build_setup(
        BACKEND,
        DeckLayout(resources={"tip_rack": "TipRack", "tips_b": "TipRack"}, lidded_tip_racks=["tip_rack", "tips_b"]),
    )
    names = [n.name for n in _lids(setup)]
    assert len(names) == 2 and len(set(names)) == 2
    all_names = [n.name for n in _walk(setup.deck) if getattr(n, "name", None)]
    assert len(all_names) == len(set(all_names)), "every resource name on the deck is unique"
    # a holder squatting on the natural lid name forces a different one rather than a duplicate-name error
    squatted = build_setup(BACKEND, DeckLayout(holders=["tip_rack_lid"], lidded_tip_racks=["tip_rack"]))
    (lid,) = _lids(squatted)
    assert lid.name != "tip_rack_lid"


def test_only_the_named_rack_is_lidded():
    setup = build_setup(
        BACKEND,
        DeckLayout(resources={"tip_rack": "TipRack", "tips_b": "TipRack"}, lidded_tip_racks=["tips_b"]),
    )
    assert setup.resources["tip_rack"].lid is None
    assert setup.resources["tips_b"].lid is not None


def test_unknown_or_non_rack_name_fails_the_build_closed():
    with pytest.raises(ValueError, match="lidded_tip_racks"):
        build_setup(BACKEND, DeckLayout(lidded_tip_racks=["no_such_rack"]))
    with pytest.raises(ValueError, match="lidded_tip_racks"):
        build_setup(BACKEND, DeckLayout(resources={"src": "Plate"}, lidded_tip_racks=["src"]))


def test_naming_a_rack_twice_fails_closed_instead_of_double_lidding():
    with pytest.raises(ValueError):
        build_setup(BACKEND, DeckLayout(lidded_tip_racks=["tip_rack", "tip_rack"]))


# --- capture_observation: tip_racks_available --------------------------------------------------------------------


def test_clean_layout_observes_tip_racks_available_true():
    setup = build_setup(BACKEND, DeckLayout(resources={"tips_b": "TipRack"}))
    obs = capture_observation(_after_setup(setup))
    assert obs["tip_racks_available"] is True


def test_lidded_layout_observes_tip_racks_available_false():
    setup = build_setup(BACKEND, DeckLayout(lidded_tip_racks=["tip_rack"]))
    assert setup.resources["tip_rack"]._available_for_tip_handling is False
    obs = capture_observation(_after_setup(setup))
    assert obs["tip_racks_available"] is False


def test_one_lidded_rack_anywhere_makes_the_whole_deck_false():
    """§18.5.2 scope: the field quantifies over EVERY rack on the deck, not the operation's racks."""
    setup = build_setup(
        BACKEND,
        DeckLayout(resources={"tip_rack": "TipRack", "tips_b": "TipRack"}, lidded_tip_racks=["tips_b"]),
    )
    assert setup.resources["tip_rack"]._available_for_tip_handling is True
    assert capture_observation(_after_setup(setup))["tip_racks_available"] is False


def test_deck_with_no_tip_rack_is_vacuously_true():
    setup = build_setup(BACKEND, DeckLayout())
    for rack in [n for n in _walk(setup.deck) if isinstance(n, TipRack)]:
        rack.parent.unassign_child_resource(rack)
    assert not any(isinstance(n, TipRack) for n in _walk(setup.deck))
    assert capture_observation(_after_setup(setup))["tip_racks_available"] is True


def test_rack_under_another_in_a_z_stack_observes_false():
    """The other half of `_available_for_tip_handling` (a rack that is not the top of a z-stack), so the field is
    not a lid-only check."""
    setup = build_setup(BACKEND, DeckLayout())
    runner = setup.runner_module
    lower, upper = runner.resolve_resource("stack_lo", "TipRack"), runner.resolve_resource("stack_hi", "TipRack")
    stack = ResourceStack("z_stack", "z")
    stack.assign_child_resource(lower)
    stack.assign_child_resource(upper)
    for rails in range(3, 28):
        try:
            setup.deck.assign_child_resource(stack, rails=rails)
            break
        except ValueError:
            continue
    else:  # pragma: no cover
        pytest.skip("no free rails for the stack")
    assert lower._available_for_tip_handling is False and upper._available_for_tip_handling is True
    assert capture_observation(_after_setup(setup))["tip_racks_available"] is False


def test_observation_record_has_exactly_six_keys():
    obs = capture_observation(_after_setup(build_setup(BACKEND, DeckLayout())))
    assert set(obs) == {
        "backend_class", "num_channels", "head_channels", "deck_resource_names", "arm_slots", "tip_racks_available",
    }
    assert isinstance(obs["tip_racks_available"], bool)


@pytest.mark.parametrize("raising_rack", ["tip_rack", "tips_b"])
def test_every_rack_is_read_so_a_raising_read_beyond_a_false_still_raises(monkeypatch, raising_rack):
    """The aggregate reads EVERY rack (no short-circuit at the first unavailable one): with one rack reading
    `False` and another raising, the raise must reach the caller whichever rack the walk visits first -- otherwise
    the record would silently be `False` on some decks and `None` on others. Both orders are covered."""
    setup = _after_setup(build_setup(BACKEND, DeckLayout(resources={"tip_rack": "TipRack", "tips_b": "TipRack"})))

    def _flaky(self):
        if self.name == raising_rack:
            raise RuntimeError("synthetic private-property failure")
        return False

    monkeypatch.setattr(TipRack, "_available_for_tip_handling", property(_flaky))
    with pytest.raises(RuntimeError, match="synthetic private-property failure"):
        capture_observation(setup)


def test_a_raising_read_raises_out_of_capture_observation(monkeypatch):
    """`capture_observation` does no fail-closed handling of its own (§16.2.1): the raise reaches the caller's ONE
    guard, which nulls the whole record (asserted end to end in test_verify_postconditions.py)."""
    setup = _after_setup(build_setup(BACKEND, DeckLayout()))

    def _boom(self):
        raise RuntimeError("synthetic private-property failure")

    monkeypatch.setattr(TipRack, "_available_for_tip_handling", property(_boom))
    with pytest.raises(RuntimeError, match="synthetic private-property failure"):
        capture_observation(setup)


def _after_setup(setup):
    """`capture_observation` reads `machine.head`, which PLR fills only in `machine.setup()`."""
    import asyncio
    import contextlib
    import io

    with contextlib.redirect_stdout(io.StringIO()):
        asyncio.run(setup.machine.setup())
    return setup
