"""#4952 (left over from #4950 at 6e34be9b): build_setup()'s deck-level
fixes for a DeckLayout whose resources dict already carries more than one
tip-typed base and/or more than one bare container:

1. every tip-typed base gets its OWN physically distinct TipRack, not just
   the single factory-built one under the "tip_rack" key (which used to
   make every base but the first ungroundable -- GroundingError);
2. Trough entries are placed on a free rail instead of the factory's single
   hardcoded rails=21 (which collided the moment more than one bare
   container was named);
3. a base named "trash" reuses STARLetDeck's own built-in Trash resource
   (with_trash=True by default) instead of trying to place a second,
   duplicate-named resource, which raised
   "Resource with name 'trash' already defined.".

See outputs/plr-sema/oracle_replay_260903_4950.json's setup_error_top for
the failure signatures these fixes target.
"""

from __future__ import annotations

from pylabrobot.resources import TipRack, Trough
from pylabrobot.resources.trash import Trash

from verify.deck import DeckLayout, build_setup, infer_layout

BACKEND = "LiquidHandlerChatterboxBackend"


def test_second_tip_typed_base_gets_its_own_rack():
    """Two distinct tip-typed bases (as infer_layout now produces per
    #4952) must both be groundable -- the second must NOT silently alias
    the first."""
    layout = DeckLayout(resources={"tip_rack": "TipRack", "waste_bin": "TipRack"})
    setup = build_setup(BACKEND, layout)

    assert "tip_rack" in setup.resources
    assert "waste_bin" in setup.resources
    assert setup.resources["tip_rack"] is not setup.resources["waste_bin"]
    assert isinstance(setup.resources["waste_bin"], TipRack)
    # Both racks are actually assigned to the deck (not just registered).
    assert setup.deck.has_resource("tip_rack")
    assert setup.deck.has_resource("waste_bin")


def test_first_tip_typed_base_still_aliases_factory_rack():
    """Existing single-rack callers / frozen P2.x behaviour: the FIRST
    tip-typed base is literally the SAME object DeckFactory built, under
    both its own name and "tip_rack"."""
    layout = DeckLayout(resources={"filter_tip_box": "TipRack"})
    setup = build_setup(BACKEND, layout)

    assert setup.resources["filter_tip_box"] is setup.resources["tip_rack"]


def test_two_troughs_do_not_collide_on_hardcoded_rail():
    """Two bare containers (both Trough-typed) used to both target
    rails=21 and the second raised
    ValueError: Location ... is already occupied."""
    layout = DeckLayout(resources={"reagent_a": "Trough", "reagent_b": "Trough"})
    setup = build_setup(BACKEND, layout)

    assert isinstance(setup.resources["reagent_a"], Trough)
    assert isinstance(setup.resources["reagent_b"], Trough)
    loc_a = setup.resources["reagent_a"].get_absolute_location()
    loc_b = setup.resources["reagent_b"].get_absolute_location()
    assert loc_a != loc_b


def test_trash_base_reuses_builtin_trash_not_a_duplicate():
    """A corpus-declared "trash" base (e.g. drop_tips(destination="trash"),
    classified TipRack by usage) must reuse STARLetDeck's own built-in
    Trash resource instead of colliding with it."""
    layout = DeckLayout(resources={"tip_rack": "TipRack", "trash": "TipRack"})
    setup = build_setup(BACKEND, layout)

    assert isinstance(setup.resources["trash"], Trash)
    # It's the SAME object already on the deck, not a second one.
    assert setup.resources["trash"] is setup.deck.get_resource("trash")


def test_infer_layout_then_build_setup_end_to_end_for_drop_tips_to_trash():
    """The exact corpus shape behind setup_error_top's "resource 'trash'
    not on deck" row: drop_tips(destination="trash") after pick_up_tips
    from the default rack. infer_layout must keep "trash" as its own key,
    and build_setup must make it groundable."""
    calls = [
        {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}},
        {"name": "drop_tips", "params": {"destination": "trash"}},
    ]
    layout = infer_layout(calls)
    assert layout.resources == {"tip_rack": "TipRack", "trash": "TipRack"}

    setup = build_setup(BACKEND, layout)
    assert isinstance(setup.resources["trash"], Trash)


def test_infer_layout_then_build_setup_end_to_end_for_two_bare_containers():
    """The exact corpus shape behind setup_error_top's "Location ... is
    already occupied" rows: a transfer between two bare (un-dotted)
    container names."""
    calls = [
        {
            "name": "transfer",
            "params": {
                "source": "standards_plate_A1",
                "destination": "qpcr_plate",
                "volume_ul": 10,
            },
        }
    ]
    layout = infer_layout(calls)
    assert layout.resources == {
        "standards_plate_A1": "Trough",
        "qpcr_plate": "Trough",
    }

    setup = build_setup(BACKEND, layout)
    assert isinstance(setup.resources["standards_plate_A1"], Trough)
    assert isinstance(setup.resources["qpcr_plate"], Trough)
