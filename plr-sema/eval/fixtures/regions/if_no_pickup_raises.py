"""SHAPE: if/else. One arm picks up a tip; the other does not.

B1 (spec §12.3.6) walks BOTH arms from the same entry state regardless of
which one the interpreter actually takes -- the entry state here is
NO_TIP (from the derived setup() reset, #4938), so the ``aspirate``-
without-a-pickup arm gets a definite WILL_FAIL (NoTipError) from the
static walk whether or not that arm is ever reached at runtime. This
fixture reaches it: ``if False`` picks the ``else`` arm for real, so the
static WILL_FAIL and the actual raise land at the exact same key.

EXPECTED: ``aspirate`` WILL_FAIL (NoTipError) in the static report;
executed raises NoTipError on its one and only visit. Exercises AC-12.17's
if-shape WILL_FAIL-at-raised-key requirement.
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}, "seed_volumes": {"plate.A1": 1000.0}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tip = tip_rack["A1"][0]
    well = plate["A1"][0]
    if False:
        await lh.pick_up_tips(tip_spots=[tip])
    else:
        await lh.aspirate(resources=[well], vols=[10.0])
