"""SHAPE: while. Trip is always None (spec §12.2.3).

No ``pick_up_tips`` anywhere in this loop -- the body ``aspirate``s
directly. Tip state therefore never changes across a real iteration (E3:
``aspirate``'s ``channel_effect`` is ``None``, no bridge), so the L2
fixpoint (spec §12.3.3) stabilizes after its FIRST pass at the entry state
(NO_TIP, from the derived setup() reset, #4938) and stays there --
unlike a loop whose body DOES change tip state (``while_counter_clean.py``
proved this is possible without ever raising; the earlier draft of THIS
fixture tried to make ``pick_up_tips`` itself the failing call, but a
fixpoint's own loop-HEAD state necessarily joins "first entry" against
"looped back from a prior iteration", which collapses to Top the moment
tip state could differ between those two paths -- correctly conservative,
but exactly why a fixpoint can never assert a cross-iteration-dependent
WILL_FAIL. A call whose failure does NOT depend on iteration count, like
this one, is what a fixpoint CAN assert.)

EXPECTED: ``aspirate`` WILL_FAIL (NoTipError) from the fixpoint's single
converged pass; executed raises NoTipError on iteration 1, before the
loop's own counter ever advances. Exercises AC-12.17's while-shape
WILL_FAIL-at-raised-key requirement.
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}, "seed_volumes": {"plate.A1": 1000.0}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    well = plate["A1"][0]
    count = 0
    while count < 2:
        await lh.aspirate(resources=[well], vols=[10.0])
        count += 1
