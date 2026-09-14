"""SHAPE: range(0). A proved-trip-0 for-loop (§12.2.3's ``range(0)`` proof
rule).

The body never executes at runtime -- real Python semantics never enters
a ``range(0)`` loop -- so the recorder records ZERO visits of
``pick_up_tips``. Statically, ``check_ir``'s L1 unroll visits
``min(0, K) = 0`` times, so this operation is excluded from
``OBLIGED(graph)`` (spec §12.3.4 exclusion (2)) and never receives a
Finding at all.

EXPECTED: no static finding and no executed record for ``pick_up_tips``
-- nothing to compare, which is exactly the point: the exclusion must not
be silently "compared as passing", it must genuinely produce no key on
either side.
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tip = tip_rack["A1"][0]
    for _i in range(0):
        await lh.pick_up_tips(tip_spots=[tip])
