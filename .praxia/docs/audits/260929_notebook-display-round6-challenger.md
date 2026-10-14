---
title: Notebook display epic, round 6 challenger (convergence confirmation)
description: Round 6 check of Revision 5 (b85dc0b0). C5-1..C5-4 are closed. 1 MAJOR regression from C5-2 (re-dock through an open, iframe-less panel) and 1 MINOR. Fixed by Revision 6, which gives the deck panel an explicit state machine.
status: final
task_id: 260929_notebook-display-design
date: '260929'
---
# Round 6 challenger

Reviewer: praxia:spec-challenger (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-challenge_r6`. Verdict: **REVISE**.

**Closure:**
- C5-1 is CLOSED. The AC-36 `false` clause matches D6, AC-39(d) is unaffected, AC-1 lists each
  key's status, and `iframe_reloads_during_resize = 0` can be met in every branch.
- C5-2 is CLOSED, but it caused C6-1.
- C5-3 and C5-4 are CLOSED.

## Findings
- **C6-1 [MAJOR]** `dock()` awaits the old viewer's `stop()`, which posts a kernel `close`. Under
  Revision 5 that `close` removes the iframe. So every re-dock passes through "panel open, no
  iframe", and no rule covers that state:
  - The announce rules only say "set the iframe `src` while open".
  - B-2 treats a missing iframe as closed-only.
  - §3.6 still says the `announce` "reloads the iframe".
  - AC-38 `redock_reloads` can read a held, stale element.
  - A literal build shows "No deck viewer is running." after every re-dock.

  Fix:
  1. An `announce` into an open panel with no iframe creates one, then sets its `src`.
  2. Reword B-2 to cover that gap.
  3. Add a C5 unit case: `close`, then `announce`, gives exactly one iframe.
  4. AC-38 reads the iframe currently in the panel.
- **C6-2 [MINOR]** AC-38's K1 execution order is unstated. `stop_placeholder`, listed second,
  precedes keys that need a live viewer.

## Disposition
- Revisions 4 and 5 were applied piecemeal by the orchestrator, and each introduced a neighbouring
  inconsistency in the deck panel lifecycle.
- Revision 6 (spec writer) therefore fixes the cause: one authoritative deck panel state machine
  in D11. Every other section references it, and C5 tests one transition per row.
