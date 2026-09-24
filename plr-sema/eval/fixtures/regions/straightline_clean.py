"""SHAPE: straight-line. No loop, no branch -- the control fixture every
other shape is compared against.

EXPECTED: every operation SAFE, no "iteration N" prefix on any finding
(straight-line findings default to iteration 1, spec 260903 §12.3.4);
executed ran_ok throughout, each call visited exactly once.
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}, "seed_volumes": {"plate.A1": 1000.0}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tip = tip_rack["A1"][0]
    well = plate["A1"][0]
    await lh.pick_up_tips(tip_spots=[tip])
    await lh.aspirate(resources=[well], vols=[10.0])
    await lh.drop_tips(tip_spots=[tip], allow_nonzero_volume=True)
