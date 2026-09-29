---
title: Notebook display epic, round 3 challenger (targeted convergence check)
description: Round 3 check of Revision 2 (4dc4d617). All C2-n are closed. B-1, B-3 and B-7 are sound and B-8 is not. 2 MAJOR and 2 MINOR findings, both MAJORs verified against PLR 0.2.2. Verdict REVISE, fixed as Revision 3 without a defender pass.
status: final
task_id: 260929_notebook-display-design
date: '260929'
---
# Round 3 challenger

Reviewer: praxia:spec-challenger (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-challenge_r3`. Verdict: **REVISE**, with 2 MAJOR findings
(C3-1 and C3-2), both one-line fixes to D8 step 4 plus an AC case.

## Closure
C2-1..C2-12 are all CLOSED. C2-3 was checked against source: `server.py:224` reads the global at
call time, and `_models_on_disk` is an `lru_cache` keyed by root (`:104-105`). C2-4 is closed, but
it has the knock-ons C3-1 and C3-2 below.

## Deep checks
- **B-1: SOUND.** Implementer notes:
  - `_clients` is a set (`server.py:187`), so the viewer needs its own ordered map to find the
    oldest client, and eviction must drop the old client synchronously.
  - A synchronous cell running longer than about 60 s makes the page give up
    (`transport.js:26,72-74`). Closing and reopening the panel recovers it.
- **B-3: SOUND.** Implementer notes:
  - Recompute the ≥1600 inline widths on ResizeObserver in the honoured/unreachable case.
  - S1 may record whether `restoreLayout()` reloads the iframe.
- **B-7: SOUND.** Suggested addition: a negative control in AC-23 checking that a re-run output is
  not marked "Drawn in an earlier session".
- **B-8: NOT SOUND.** The rule "owner not in the committed offending set → `None`" means every owner
  kind needs a committed test. Two lack one (C3-1, C3-2).

## Findings

### C3-1 [MAJOR] TLV with a tip owner has no committed test
- **Where:** D8 step 4 "TLV, tip owner: the tip on channel c."; §3.3; AC-15/16/17.
- **Claim:** A pending tip residue gives a self-contradicting panel instead of `None`.
- **Evidence:** Tip trackers are queued outside the `try` (`liquid_handler.py:1031-1035`) and only
  committed after the backend call (`:1059-1064`). `volume_tracker.py:101-107` checks pending.
- **Required change:** The tip offends only if requested > `max_volume − tracker.volume`
  (committed). Add E15 → `None`, and AC-17: E15 shows the generic panel.
- **Orchestrator verification (PLR 0.2.2, fixture layout, chatterbox):**
  1. `pick_up_tips(A1:D1)`.
  2. `aspirate(A1:D1, [200]*4)` with D1 at 100 µL raises `TooLittleLiquidError: ... 200.0uL >
     100uL.` Tip 0 is then committed 0 / pending 200, `max_volume` 360.
  3. `aspirate(A2, [200], use_channels=[0])` raises `TooLittleVolumeError: Not enough space in
     container: 200.0uL > 160.0uL.`
  4. The committed room is 360, so a committed-state panel would describe no fault. **Confirmed.**

### C3-2 [MAJOR] A NoTip channel conflict is defined only for liquid ops
- **Where:** D8 step 4 "a channel with no tip for any liquid op"; §3.3 "NoTip, channel".
- **Claim:** Drop, Return and Discard tips on an empty channel go to the generic panel, although
  this is one of the four MVP error classes.
- **Evidence:** `liquid_handler.py:655`, `tip_tracker.py:64-65`.
- **Required change:** "any op that uses a mounted tip". Add E16 and a matching AC-16 line.
- **Orchestrator verification:**
  - `discard_tips(use_channels=[0])` and `drop_tips(tips["A1"], use_channels=[0])` with no tip
    both raise `NoTipError: Channel 0 does not have a tip.` **Confirmed.**
  - **Correction to the challenger's proposed case:**
    - bare `discard_tips()` raises `RuntimeError: No tips have been picked up and no channels were
      specified.`;
    - bare `return_tips()` raises `RuntimeError: No tips have been picked up.`
    - So E16 must pass `use_channels`, and the two bare calls become negative cases (`None`, plain
      styled traceback).

### C3-3 [MINOR] Tier re-homing is described two ways
D6 moves the iframe and keeps its `src`, while D11's "Closed panel" recreates it and sends `query`.
Keep D6's version and drop "tier crossing" from D11's reopen list.

### C3-4 [MINOR] Leftover text
- AC-15 E10 still has "(plus the owner if it is outside that set)", which the new rule contradicts.
- AC-39's last bullet disagrees with A7 about which sprint runs (a).
- The AC-40 heading has run onto the end of the previous line (a missing newline).

## Disposition
The orchestrator applied the fixes directly as Revision 3 (R3-1..R3-5, including the implementer
notes) without a defender pass. Both MAJORs were settled empirically, and every fix is local.
A final confirmation check follows Revision 3.
