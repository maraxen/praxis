"""#4950: infer_layout() usage-based type inference.

infer_layout() used to decide a resource's PLR type purely by NAME PREFIX
("tip*" -> TipRack, "*trough" -> Trough, else Plate). #4950 makes it infer
from the call sequence's USAGE first (via the canonical
coxswain.plr.param_namespace table dispatcher.py already drives dispatch
from), falling back to the original prefix rule only when there is no usage
evidence -- and keeping the prefix rule verbatim (with a recorded warning)
when a base name is used BOTH as a tip target and a container/well target.
"""

from __future__ import annotations

import warnings

from verify.deck import infer_layout


def test_prefix_rule_preserved_for_tip_rack():
    """A conventional "tip_rack.A1" ref (no other usage evidence needed)
    still collapses onto the single factory-built rack, same as before."""
    calls = [{"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}}]
    layout = infer_layout(calls)
    assert layout.resources == {"tip_rack": "TipRack"}


def test_filter_tip_box_used_as_pickup_target_becomes_tiprack():
    """golden-clean-pick_up_tips-03: a rack NOT prefixed "tip" but used as a
    pick_up_tips.at target must be typed TipRack, not the old default Plate
    (which produced 'Plate' object has no attribute 'tracker')."""
    calls = [
        {
            "name": "pick_up_tips",
            "params": {
                "at": [
                    "filter_tip_box_D1",
                    "filter_tip_box_D2",
                    "filter_tip_box_D3",
                    "filter_tip_box_D4",
                ]
            },
        }
    ]
    layout = infer_layout(calls)
    # #4952: each distinct bare name keeps ITS OWN key -- these are four
    # separately-spelled bare refs (no "." separator, so each is its own
    # base name to ground_ref), and collapsing them onto a single
    # "tip_rack" key used to leave three of the four ungroundable
    # (GroundingError: resource '...' not on deck). build_setup aliases
    # only the FIRST onto the factory-built rack; the rest get their own
    # physically distinct rack (see test_infer_layout's sibling assertions
    # in test_deck_build_setup.py for the build_setup-side behavior).
    assert layout.resources == {
        "filter_tip_box_D1": "TipRack",
        "filter_tip_box_D2": "TipRack",
        "filter_tip_box_D3": "TipRack",
        "filter_tip_box_D4": "TipRack",
    }

    # Same base, but already normalised to dotted "name.well" form (the
    # shape #4939's loader-side rewrite produces) -- usage evidence still
    # wins over the prefix rule (which would've defaulted to Plate here
    # too, since "filter_tip_box" doesn't start with "tip"), and here all
    # four refs share the SAME base name, so infer_layout naturally
    # collapses them onto one key via plain dict setdefault.
    dotted_calls = [
        {
            "name": "pick_up_tips",
            "params": {
                "at": [
                    "filter_tip_box.D1",
                    "filter_tip_box.D2",
                    "filter_tip_box.D3",
                    "filter_tip_box.D4",
                ]
            },
        }
    ]
    assert infer_layout(dotted_calls).resources == {"filter_tip_box": "TipRack"}


def test_bare_aspirate_source_becomes_trough_not_plate():
    """A "source"/"well" container ref with no well address (used bare, as
    the whole aspirate source) must get a resource that carries its OWN
    tracker (PLR Trough) -- a Plate has no top-level .tracker, which is the
    AttributeError('Plate' object has no attribute 'tracker') class this
    fix targets."""
    calls = [{"name": "aspirate", "params": {"source": "reagent_reservoir_1", "volume_ul": 50}}]
    layout = infer_layout(calls)
    assert layout.resources == {"reagent_reservoir_1": "Trough"}


def test_dotted_well_on_plate_stays_plate():
    """The ordinary "<plate>.<well>" shape is unaffected -- still Plate."""
    calls = [{"name": "aspirate", "params": {"source": "plate_1.A1", "volume_ul": 50}}]
    layout = infer_layout(calls)
    assert layout.resources == {"plate_1": "Plate"}

    transfer_calls = [
        {
            "name": "transfer",
            "params": {"source": "plate_A.H12", "destination": "plate_B.A1", "volume_ul": 20},
        }
    ]
    assert infer_layout(transfer_calls).resources == {
        "plate_A": "Plate",
        "plate_B": "Plate",
    }


def test_conflicting_usage_keeps_todays_prefix_behaviour():
    """A base referenced BOTH as a tip-spot target and as a container/well
    target is a conflict: keep today's name-prefix classification (with a
    recorded warning) rather than guessing which usage wins."""
    calls = [
        {"name": "pick_up_tips", "params": {"at": ["rig1.A1"]}},
        {"name": "aspirate", "params": {"source": "rig1", "volume_ul": 10}},
    ]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        layout = infer_layout(calls)

    assert any("both as a tip-spot target" in str(w.message) for w in caught)
    # "rig1" doesn't match the prefix rule's "tip*"/"*trough" special cases,
    # so today's prefix rule types it Plate -- unchanged from pre-#4950
    # behaviour for this name.
    assert layout.resources == {"rig1": "Plate"}

    # A conflicting name that DOES match the "tip*" prefix keeps ITS
    # pre-#4950 behaviour too: collapsed onto the single factory rack.
    tip_prefixed_calls = [
        {"name": "pick_up_tips", "params": {"at": ["tip_reservoir.A1"]}},
        {"name": "aspirate", "params": {"source": "tip_reservoir", "volume_ul": 10}},
    ]
    with warnings.catch_warnings(record=True) as caught2:
        warnings.simplefilter("always")
        layout2 = infer_layout(tip_prefixed_calls)
    assert any("both as a tip-spot target" in str(w.message) for w in caught2)
    assert layout2.resources == {"tip_rack": "TipRack"}


def test_stamp_plate_refs_never_become_trough():
    """stamp needs an actual multi-well Plate (it copies well-by-well); a
    bare stamp source/destination must stay Plate, never earn the
    bare-container Trough treatment aspirate/dispense/transfer get."""
    calls = [
        {
            "name": "stamp",
            "params": {"source": "assay_plate", "destination": "dest_plate", "volume_ul": 10},
        }
    ]
    layout = infer_layout(calls)
    assert layout.resources == {"assay_plate": "Plate", "dest_plate": "Plate"}


def test_unknown_tool_falls_back_to_prefix_rule():
    """A tool absent from the phase-2 canonical namespace carries no usage
    evidence; infer_layout must not raise and must fall back to the
    original prefix rule."""
    calls = [{"name": "read_absorbance", "params": {"wavelength_nm": 405.0, "at": ["A1"]}}]
    layout = infer_layout(calls)
    assert layout.resources == {"A1": "Plate"}


def test_exclude_still_skips_explicit_resources():
    calls = [{"name": "aspirate", "params": {"source": "reagent_reservoir_1", "volume_ul": 50}}]
    layout = infer_layout(calls, exclude={"reagent_reservoir_1"})
    assert layout.resources == {}
