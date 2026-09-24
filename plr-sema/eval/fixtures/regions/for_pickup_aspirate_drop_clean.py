"""SHAPE: for. Proved trip = 2 (``range(2)``, an integer literal).

Each iteration picks up, aspirates, and drops its own tip before the next
iteration's pickup -- runs clean end to end. The tip-outcome sibling of
``for_pickup_no_drop_raises.py``: same shape, both tip outcomes
represented (spec 260903 §12.4.2's "both tip outcomes represented").
``drop_tips(..., allow_nonzero_volume=True)`` -- the tip still carries the
aspirated volume; this fixture is about tip-presence typestate, not
volume bookkeeping, so it opts out of PLR's separate nonzero-volume guard
rather than adding an unrelated dispense-back step.

EXPECTED: every operation SAFE at both iterations; executed side ran_ok
throughout; executed iteration count for every operation == the proved
trip (2).
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}, "seed_volumes": {"plate.A1": 1000.0}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tips = [tip_rack["A1"][0], tip_rack["A2"][0]]
    well = plate["A1"][0]
    for i in range(2):
        await lh.pick_up_tips(tip_spots=[tips[i]])
        await lh.aspirate(resources=[well], vols=[10.0])
        await lh.drop_tips(tip_spots=[tips[i]], allow_nonzero_volume=True)
