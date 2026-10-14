---
title: Notebook display epic, round 5 challenger (convergence confirmation)
description: Round 5 check of Revision 4 (715300f0). C4-1 and C4-3 are closed and C4-2 is closed in part. 1 MAJOR (AC-36 per-case list vs the restore_layout_keeps_iframe=false branch) and 3 MINOR. Fixed by the orchestrator as Revision 5.
status: final
task_id: 260929_notebook-display-design
date: '260929'
---
# Round 5 challenger

Reviewer: praxia:spec-challenger (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-challenge_r5`. Verdict: **REVISE**.

**Closure:**
- C4-1 is CLOSED. Every placeholder site names the right text, and AC-38 is sound because only a
  kernel `close` can meet 5 s.
- C4-2 is partial: the mechanism is consistent everywhere except AC-36's case list.
- C4-3 is CLOSED. `tracker.set_volume` has no capacity check (`volume_tracker.py:66-72`).
- Asserting `iframe_reloads_during_resize = 0` under S1-L is well-defined: nothing clamps, so the
  expected count is 0.

## Findings
- **C5-1 [MAJOR]** AC-36 says both `reachable` cases assert every width key. Under
  `restore_layout_keeps_iframe = false`, the D6 note routes clamps to the `unreachable` row, so
  the gate cannot be satisfied there. AC-1 also lacks the per-key status that D6 says it
  records. Fix: an AC-36 `false`-branch clause, and a per-key status list in AC-1.
- **C5-2 [MINOR]** Nothing enforces "a `close` never shows the lost-connection text". A kept
  iframe would retry and emit `plr:gone` after 60 s. Fix: remove the iframe on `close`, or
  ignore `plr:gone` until the next `announce`, with a unit case.
- **C5-3 [MINOR]** The counting method for `iframe_reloads_during_resize` is unstated. A
  listener on one element misses a replaced element. Fix: a MutationObserver plus a `load`
  listener per iframe, in harness code only.
- **C5-4 [MINOR]** The C5 task text and the §4 `dock.js` row lag Revision 4.

## Disposition
The orchestrator applied R5-1..R5-4 as Revision 5. C5-2 got both mechanisms: the iframe is removed
on `close`, and `plr:gone` is ignored until the next `announce`.
