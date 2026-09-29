---
title: Notebook display epic, round 4 challenger (final convergence check)
description: Round 4 check of Revision 3 (3bf10d63). All C3-n are closed. 2 MAJOR (one introduced by the orchestrator's plr:gone edit) and 2 MINOR findings. Verdict REVISE, fixed by the orchestrator as Revision 4.
status: final
task_id: 260929_notebook-display-design
date: '260929'
---
# Round 4 challenger

Reviewer: praxia:spec-challenger (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-challenge_r4`. Verdict: **REVISE**.

**Closure:**
- C3-1, C3-2, C3-3 and C3-4 are CLOSED.
- R3-5 (a), (b), (c) and (e) are CLOSED. (d) is OPEN, and becomes C4-2.
- No dangling references remain: `praxis:display-session`, `head96`, the comprehension case,
  "set once at open", `setRelativeSizes` and a page-side `close` appear only in the revision logs
  or as explicit negations.
- Every AC-1..AC-41 is closed by at least one task.

## Findings
- **C4-1 [MAJOR] The stop placeholder is ambiguous after the `plr:gone` edit.**
  - §3.6 gained a second placeholder text. The line "`await viewer.stop()` gives the same
    placeholder within 5 s" then pointed at the lost-connection text.
  - AC-38 `stop_placeholder` matched either string.
  - Only a kernel `close` can trigger the placeholder within 5 s, because `plr:gone` needs 60 s
    (`static/transport.js:26,73-74`).
  - Fix: a kernel `close` shows "No deck viewer is running."; only `plr:gone` shows the
    lost-connection text; AC-38 asserts the exact string; each placeholder reference names its
    text.
- **C4-2 [MAJOR] `restore_layout_keeps_iframe` has no `false` branch.**
  - If `false`, every `ResizeObserver` or drag clamp through `restoreLayout()` would reload the
    deck iframe. That costs a re-greeting and a client of the cap, and no gate would catch it.
  - Fix: layout sizing only at open and on tier changes when `false`, or a stated deviation with
    a recorded key. Also add the key to the §4 S1 row.
- **C4-3 [MINOR] E3's threshold is ambiguous.** The fixture tip's `max_volume` is 360, not its
  300 nominal.
- **C4-4 [MINOR, parser note]** The ACs are `- **AC-n …**` bullets (41 of them, each at line
  start), not `### AC-n` headings. No content change is needed.

## Disposition
The orchestrator applied R4-1..R4-4 directly as Revision 4 (715300f0):
- For C4-2 it chose option (i): layout sizing only at open and on tier changes.
- It added an asserted `iframe_reloads_during_resize = 0` key as the gate, so a clamp that
  reloads the iframe fails rather than being merely recorded.
