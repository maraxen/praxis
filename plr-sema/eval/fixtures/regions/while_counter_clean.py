"""SHAPE: while. Trip is always None (no proof rule for a runtime
condition, spec §12.2.3) -- this loop's own bound (``count < len(tips)``)
is counter-driven, not something the extractor could prove regardless.

Each of the three iterations picks up, aspirates, and drops its own tip
before the next iteration's pickup -- runs clean end to end.

EXPECTED: every operation's static verdict comes from the L2 fixpoint's
FINAL pass only (no "iteration N" prefix in ``Finding.detail`` -- spec
§12.3.3 L2), and must stay sound against every one of the three real
executed iterations, not just the first.
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}, "seed_volumes": {"plate.A1": 1000.0}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tips = [tip_rack["A1"][0], tip_rack["A2"][0], tip_rack["A3"][0]]
    well = plate["A1"][0]
    count = 0
    while count < len(tips):
        await lh.pick_up_tips(tip_spots=[tips[count]])
        await lh.aspirate(resources=[well], vols=[10.0])
        await lh.drop_tips(tip_spots=[tips[count]], allow_nonzero_volume=True)
        count += 1
