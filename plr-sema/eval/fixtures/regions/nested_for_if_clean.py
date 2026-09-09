"""SHAPE: nesting -- a for containing an if.

Proved trip = 2 for the outer loop (``range(2)``); the nested if's true
arm (always taken at runtime -- ``if True``) picks up a tip each
iteration, followed by an aspirate and a drop, so every iteration ends
back at NO_TIP for the next one. Runs clean end to end.

EXPECTED: the nested ``pick_up_tips`` finding carries the OUTER loop's
iteration index (branches never add their own iteration index -- spec
§12.3.4/§12.3.6, ``walk_branch`` threads the enclosing loop's ``iteration``
through unchanged); executed iteration count for ``pick_up_tips`` == the
outer loop's proved trip (2).
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}, "seed_volumes": {"plate.A1": 1000.0}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tips = [tip_rack["A1"][0], tip_rack["A2"][0]]
    well = plate["A1"][0]
    for i in range(2):
        if True:
            await lh.pick_up_tips(tip_spots=[tips[i]])
        await lh.aspirate(resources=[well], vols=[10.0])
        await lh.drop_tips(tip_spots=[tips[i]], allow_nonzero_volume=True)
