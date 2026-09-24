"""SHAPE: for (spec 260903 §14.9's tier-2b set, T28). Proved trip = 2
(``range(2)``, an integer literal).

One tip picks up and aspirates 50 uL once, then a loop dispenses 30 uL each
pass. The first dispense is individually safe (tip has 50, asks for 30,
leaves 20); the SECOND dispense over-draws the same tip cell (asks for 30,
tip has only 20 left) -- decidable only because V2 (§14.5) threads the
tip cell's interval pair-by-pair ACROSS iterations rather than re-checking
each dispense against the tip's ORIGINAL 50 uL.

EXPECTED: iteration 1's `dispense` is `Verdict.SAFE`; iteration 2's
`dispense` is `Verdict.WILL_FAIL` (`TooLittleLiquidError`), sited at
`VolumeTracker.remove_liquid`. Executed: iteration 1 `ran_ok`, iteration 2
raises, and execution stops there.

**Source and destination are DIFFERENT wells** (`A1`/`B1`) -- see
`volume_straightline.py`'s own docstring for why (dispensing into the
seeded source well would overflow ITS capacity first).
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}, "seed_volumes": {"plate.A1": 300.0}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tip = tip_rack["A1"][0]
    source = plate["A1"][0]
    dest = plate["B1"][0]
    await lh.pick_up_tips(tip_spots=[tip])
    await lh.aspirate(resources=[source], vols=[50.0])
    for _ in range(2):
        await lh.dispense(resources=[dest], vols=[30.0])
