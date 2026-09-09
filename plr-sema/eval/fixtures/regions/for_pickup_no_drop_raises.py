"""SHAPE: for. Proved trip = 2 (``range(2)``, an integer literal).

Neither iteration drops its tip before the next iteration's pickup, so
channel 0 already carries a tip when ``pick_up_tips`` is visited a second
time -- HasTipError, definite at that exact (operation, iteration=2) key.

Each call site wraps a single bare ``TipSpot`` in a literal one-element
list (``tip_spots=[tips[i]]``) -- required so the static side can prove
``len(tip_spots) == 1`` (spec §12.1.3's channel-count derivation reads a
``Seq``'s length, not its element values) while staying runtime-correct
(``tip_rack["A1"]`` already returns a one-element list; indexing ``[0]``
recovers the bare ``TipSpot`` before rewrapping).

EXPECTED: ``pick_up_tips`` -- iteration 1 SAFE, iteration 2 WILL_FAIL
(HasTipError). Executed: iteration 1 ran_ok, iteration 2 raises
HasTipError, and execution stops there. Exercises AC-12.17's for-shape
WILL_FAIL-at-raised-key requirement and §12.3.3 L1's per-iteration
soundness claim.
"""

from __future__ import annotations

LAYOUT = {"resources": {"plate": "Plate"}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack, plate: Plate) -> None:
    tips = [tip_rack["A1"][0], tip_rack["A2"][0]]
    for i in range(2):
        await lh.pick_up_tips(tip_spots=[tips[i]])
