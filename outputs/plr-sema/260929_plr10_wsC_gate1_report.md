# plr-sema on PLR 1.0.0b1: workstream C, gate 1 report (task 260929_plr-1.0-migration)

**Status: gate 1 FAILED on real PLR semantic changes. Stopped before step 2 (the measurement) and step 3 (spec citations).**

## Which files the analyzer reads (surface mapping)
- `legacy_pinned` at 1.0 means the static import closure of `pylabrobot/legacy/`. It is built in `plr_sema.derive.surface_files`, and both the derive step and the three surveys use it. On 1.0 that is 461 of 760 source files. Trees without a `legacy/` directory (the old pin, the 3a50a567f snapshot) are still read whole, exactly as before.
- Why this choice:
  - It covers exactly what the legacy LiquidHandler can execute, which is what praxis calls after commit 4772f264.
  - Reading the whole tree instead would pick up a 9th `can_pick_up_tip` definition and 109 duplicate class names from the new device API.
  - The closure keeps the new modules that legacy code really delegates to, such as the `hamilton/star/driver` parts that the legacy STAR backend imports.
- `upstream_nonlegacy` is left frozen at 3a50a567f. A mode `nonlegacy` (the tree minus `legacy/`) exists if someone wants to rebuild it from 1.0.
- Recipe check at the old pin: running the survey and derive steps, with `--taxonomy-json`, reproduces the committed `derived_contracts.json` exactly. The committed `gap_ledger.json` was already out of date there, from an older code state (`by_reason` values).

## Blocking semantic changes (root causes)
1. **The analyzer can no longer derive the effects of picking up and dropping tips.** PLR 1.0 rewrote `TipTracker` (`legacy/tip_tracker.py`):
   - `_pending_tip` and `_tip` are now properties, and state changes go through `_hold` / `_put`, which write `_carried` or the resource tree.
   - The step that derives these effects (P4) looks for direct assignments to those fields, so it now finds no effects at all.
   - Consequences: the setup reset is `absent`, `tip_dropping` is empty, and the `channel_effect` recorded for pick_up_tips / drop_tips is None.
   - All tip-state results for those ops become UNKNOWN. This is the cause of the 15 test_tip_typestate failures, the 2 test_tier2 failures, and part of the volume results.
2. **A new PLR check `_check_tip_racks_available`** (liquid_handler.py:338) now runs inside pick_up_tips, drop_tips and the 96-head variants. The analyzer cannot read its condition, so it is always UNKNOWN on those ops.
   - On one clean pick_up_tips row, the ops left undecided are :338, :758 (HasTipError) and tip_tracker.py:153. The expected SAFE verdict is lost (test_oracle_replay gate test).
3. **SOUNDNESS: the analyzer now reports a wrong SAFE.** Two tests catch it: `test_ac_14_5_e_retip_dirty_tip_never_safe` and `test_tips_dirty_cost`.
   - Cause: in the volume rules (`check/volumestate.py` `_apply_v5`), a call with no derived effect only sets `tips_dirty`. It never resets the tip's recorded volume to unknown.
   - So pick up / aspirate 50 / drop / pick up / dispense 50 comes out SAFE, because the tip volume survives the drop.
   - Proposed fix (not applied, because it changes the spec's rule): an unmodelled tip movement should also reset every tip cell to unknown.
4. The golden counts in test_ir (42→44) and ac_10_4 (38→40) move because of the new check in item 2.

## Mechanical re-anchoring done
Pins, the `legacy/` paths and module names, D6 keyed by symbol, oracle_replay site keys by symbol, the t30 PREDICTED_TIER table, test line numbers (mapped by aligning file contents), and backend-surface counts 218/98/120 with the root cause recorded.
