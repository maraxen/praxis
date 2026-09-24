"""SHAPE: break (spec 260903 §12.1.5's A-EARLY-EXIT, round-1 O7).

``range(3)`` gives a proved trip of 3, but the loop body ``break``s after
its first (clean) iteration -- real Python semantics never enters
iterations 2 or 3. A-EARLY-EXIT's claim (spec §12.5 table) is that an
unvisited call site is not-reached BY CONSTRUCTION under the
(operation, iteration) comparison: iterations 2 and 3's ``pick_up_tips``/
``drop_tips`` findings (L1 still unrolls them -- unlike ``continue``,
``break`` does not withdraw the trip proof) simply have no executed
record to compare against, and are silently exempt rather than counted.

EXPECTED: only visit_index 1 is ever recorded for ``pick_up_tips``/
``drop_tips`` (a proved trip of 3 with only 1 real execution -- this
fixture is DELIBERATELY exempt from the "executed count == proved trip"
check the other proved-trip fixtures satisfy, precisely because of the
early exit).
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tips = [tip_rack["A1"][0], tip_rack["A2"][0], tip_rack["A3"][0]]
    for i in range(3):
        await lh.pick_up_tips(tip_spots=[tips[i]])
        await lh.drop_tips(tip_spots=[tips[i]])
        break
