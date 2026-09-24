"""SHAPE: for (spec 260903 §14.9's tier-2b set, T28). Proved trip = 3
(``range(3)``, an integer literal).

One tip picks up and aspirates 50 uL once, then a loop dispenses 20 uL each
pass -- individually SAFE against the tip's original 50 uL every single
time (20 <= 50), but the tip is exhausted COLLECTIVELY: 50 -> 30 -> 10, and
the third dispense (asks for 20, tip has only 10 left) over-draws. This is
the fixture that falsifies a per-call check that never accumulates state
across iterations -- a per-operation-only static side would emit SAFE at
every one of the three dispenses and never catch this.

EXPECTED: iterations 1 and 2's `dispense` are `Verdict.SAFE`; iteration 3's
`dispense` is `Verdict.WILL_FAIL` (`TooLittleLiquidError`), sited at
`VolumeTracker.remove_liquid`. Executed: iterations 1-2 `ran_ok`,
iteration 3 raises, and execution stops there.

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
    for _ in range(3):
        await lh.dispense(resources=[dest], vols=[20.0])
