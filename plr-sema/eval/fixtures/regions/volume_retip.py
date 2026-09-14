"""SHAPE: straight-line (spec 260903 §14.9's tier-2b set, T28) -- the
retip fixture, V5's own stub-defeating half (round-1 O4).

One tip picks up, aspirates 50 uL, and is dropped WITHOUT being emptied
first (`allow_nonzero_volume=True` -- PLR's own `is_disabled`-gated
nonzero-volume precondition is a compound condition this family already
declines to recognise, §14.14 item 1). A SECOND, different tip is then
picked up on the same channel and asked to dispense 50 uL. A `[0, 0]`-
always implementation of `pick_up_tips` (crediting every new tip with the
DEPARTED tip's own contents) would emit `Verdict.SAFE` here and be wrong:
the new tip is a genuinely fresh `Tip` instance (`tip.py:32`'s
`__post_init__`, a NEW `VolumeTracker` starting at 0), so the dispense
raises for real, immediately.

V5's lifecycle (`tips_dirty`) makes this the SOUND-but-imprecise case: the
drop leaves `tips_dirty` true (the departing interval was `[50, 50]`, not
provably empty), so the second `pick_up_tips` widens the tip cell to `TOP`
instead of resetting it to `[0, 0]`, and the dispense's guard can then
only report `Verdict.UNKNOWN` (`volume_state_unknown`) -- never `SAFE`,
and never a `WILL_FAIL` sited anywhere but here (there is nowhere else to
mis-site it: this fixture has exactly one dispense).

EXPECTED: `dispense` raises `TooLittleLiquidError` (fresh tip has 0, asked
for 50); static verdict at that operation is `Verdict.UNKNOWN`
(`volume_state_unknown`) -- sound, not `SAFE`. Every earlier operation
runs/verifies clean.

**Source and destination are DIFFERENT wells** (`A1`/`B1`) -- see
`volume_straightline.py`'s own docstring for why (dispensing into the
seeded source well would overflow ITS capacity first).
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}, "seed_volumes": {"plate.A1": 300.0}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tip = tip_rack["A1"][0]
    tip2 = tip_rack["A2"][0]
    source = plate["A1"][0]
    dest = plate["B1"][0]
    await lh.pick_up_tips(tip_spots=[tip])
    await lh.aspirate(resources=[source], vols=[50.0])
    await lh.drop_tips(tip_spots=[tip], allow_nonzero_volume=True)
    await lh.pick_up_tips(tip_spots=[tip2])
    await lh.dispense(resources=[dest], vols=[50.0])
