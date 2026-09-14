"""SHAPE: straightline + for -- two DIFFERENT `pick_up_tips` call sites in two DIFFERENT bodies (backlog #4948).

Before #4948, `OperationNode.line_number` was always `0`
(`computation_graph_extractor.py`'s `_current_line` was assigned once in
`__init__` and never again), so `region_oracle.py`'s join keyed on
`(method_name, lineno)` had to normalize every line to `0` (`_join_key`)
and could only ever support "at most one call site per method in the
WHOLE fixture" -- a call to the SAME method from two different bodies
would collide as a `DuplicateCallSiteError`. With real line numbers, the
join can support spec §12.4.2's actual rule ("at most one call site per
method PER BODY"): this fixture deliberately puts `pick_up_tips` in two
different bodies (once at the function's own top level, once inside a
`for`-loop body) to prove the join tells them apart.

The top-level `pick_up_tips` is unconditionally SAFE (entry state
NO_TIP -> HAS_TIP). The `for`-loop's own `pick_up_tips` -- one iteration,
proved trip 1 -- then runs from an entry state that already has a tip (no
`drop_tips` between the two sites), so it is a definite WILL_FAIL
(HasTipError), mirroring `for_pickup_no_drop_raises.py`'s own mechanism
but across TWO SEPARATE bodies rather than two iterations of the same
loop.

EXPECTED: `join_map` has two distinct entries under the SAME method name
(`pick_up_tips`) at two DIFFERENT lines, mapping to two DIFFERENT
operation ids -- no `DuplicateCallSiteError`. Executed: the top-level call
runs ok; the for-loop's call raises HasTipError, and the raise happens at
the for-loop's own key, distinct from the top-level site's key.
"""

from __future__ import annotations

LAYOUT = {"resources": {}}


async def protocol(lh: LiquidHandler, tip_rack: TipRack) -> None:
    tip1 = tip_rack["A1"][0]
    tip2 = tip_rack["A2"][0]
    await lh.pick_up_tips(tip_spots=[tip1])
    for _ in range(1):
        await lh.pick_up_tips(tip_spots=[tip2])
