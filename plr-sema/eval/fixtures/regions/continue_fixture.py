"""SHAPE: continue. A ``Continue`` anywhere in a for-loop's body withdraws
the trip proof (spec §12.2.3's condition 4 / round-1 O7,
``_body_has_continue``'s recursive-any-nesting-depth scan) -- despite the
iterable being ``range(2)`` (a provable-length literal), this loop's
``trip`` lowers to ``None`` and routes to the L2 fixpoint, not L1's
bounded unroll.

Iteration 1 (``i == 0``) hits the ``continue`` and skips ``pick_up_tips``/
``drop_tips`` entirely; iteration 2 (``i == 1``) runs them. The executed
trace therefore VISITS the loop but SKIPS a listed operation on one pass
-- exactly the case spec §12.5's table cites for this condition
("tier 2b's continue fixture, whose executed trace visits the loop but
skips a listed operation").

EXPECTED: no "iteration N" prefix on ``pick_up_tips``'s finding (fixpoint,
not unroll -- AC-12.6's seventh loop's own claim, "trip is None despite a
provable iterable"); the recorder's only visit of ``pick_up_tips`` is on
the SECOND for-iteration (visit_index 1, since the first iteration's call
site is never reached at all).
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tips = [tip_rack["A1"][0], tip_rack["A2"][0]]
    for i in range(2):
        if i == 0:
            continue
        await lh.pick_up_tips(tip_spots=[tips[i]])
        await lh.drop_tips(tip_spots=[tips[i]])
