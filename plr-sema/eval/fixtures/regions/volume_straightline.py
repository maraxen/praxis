"""SHAPE: straight-line (spec 260903 §14.9's tier-2b set, T28). No loop, no
branch -- the tip over-draw's own control fixture, mirroring
`straightline_clean.py`'s role for the tip-typestate family.

A single tip picks up, aspirates 50 uL, then dispenses 60 uL -- more than
the tip holds. `dispense`'s tip-side guard (`op.tip.tracker.remove_liquid`,
`liquid_handler.py:1235`) is the one guard round-1's R1 (§14.6) makes
decidable; `aspirate`'s well-side guard stays gated by `is_disabled`
(fail-closed) and never claims a definite verdict here.

EXPECTED: `dispense` raises `TooLittleLiquidError` (tip has 50, asked for
60); static verdict at that operation is `Verdict.WILL_FAIL`, sited at
`VolumeTracker.remove_liquid`. `pick_up_tips` and `aspirate` run/verify
clean.

**Source and destination are DIFFERENT wells** (`A1`/`B1`), both real
labware-capacity-bounded wells -- dispensing back into the SAME well the
seed already loaded to 1000 uL would overflow the WELL's own capacity
first (a real well's physical `max_volume` is far below the seed used to
give `aspirate` plenty of headroom), raising `TooLittleVolumeError` at the
destination-side guard instead of the tip-side guard this fixture exists
to exercise.
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}, "seed_volumes": {"plate.A1": 300.0}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tip = tip_rack["A1"][0]
    source = plate["A1"][0]
    dest = plate["B1"][0]
    await lh.pick_up_tips(tip_spots=[tip])
    await lh.aspirate(resources=[source], vols=[50.0])
    await lh.dispense(resources=[dest], vols=[60.0])
