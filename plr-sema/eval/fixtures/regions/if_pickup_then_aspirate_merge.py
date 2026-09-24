"""SHAPE: if/else. True arm picks up a tip; the (empty) else arm does not.
An ``aspirate``/``drop_tips`` pair AFTER the merge exercises the branch
JOIN itself (spec §12.3.6 B1), not just an in-arm guard.

The two arms disagree on tip state at the merge (HAS_TIP vs. NO_TIP), so
the joined state the checker computes for the post-merge calls is
necessarily uncertain -- a real WILL_FAIL or SAFE claim there would be
wrong for one of the two arms, so the join must (and does) fall back to
UNKNOWN, never contradicting the real (``if True`` -- the pickup arm is
the one actually taken) clean execution.

EXPECTED: ``pick_up_tips`` SAFE inside its arm; the post-merge ``aspirate``
and ``drop_tips`` are UNKNOWN (``channel_state_unknown`` -- the branch
join has no definite answer), never WILL_FAIL; executed ran_ok throughout.
This is the fixture spec §12.5's table cites for "a BRANCH join
over-approximates both arms".
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}, "seed_volumes": {"plate.A1": 1000.0}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tip = tip_rack["A1"][0]
    well = plate["A1"][0]
    if True:
        await lh.pick_up_tips(tip_spots=[tip])
    else:
        pass
    await lh.aspirate(resources=[well], vols=[10.0])
    await lh.drop_tips(tip_spots=[tip], allow_nonzero_volume=True)
