---
title: Notebook display epic, round 10 challenger (convergence decision)
description: Round 10 check of Revision 9 (f5c8b4d9). C9-1..C9-6 are closed, with no BLOCKER and no MAJOR. Verdict ACCEPT, so the spec has converged. 4 MINOR hardening items are recorded for the implementing sprint.
status: final
task_id: 260929_notebook-display-design
date: '260929'
---
# Round 10 challenger

Reviewer: praxia:spec-challenger (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-challenge_r10`. Verdict: **ACCEPT (converged)**, decided on
BLOCKER/MAJOR only per the round 9 policy.

**Closure.** C9-1 through C9-6 are CLOSED.

**Revision 9 check.**
- The unit order (token, arm, clear, work, result, teardown, flush, commit, `os._exit`) reads the
  same in every place it is stated.
- "Stamp governs" can't rescue a hung unit. Teardown runs before the commit, so a hung teardown
  exits 124 with no stamp.
- The CI-only real-Chromium case can't pass by being skipped, since Actions sets `CI=true` and a
  missing Chromium fails. It can pass vacuously (C10-1).

**Sprint A skim.**
- File ownership is complete.
- The first steps are consistent: A1, then A2 and A3 in parallel, then A4 and A5, then A6, then
  A7.
- Every gate can be run, and the job backstop sums to 60 minutes.

## MINOR items for the sprint (non-blocking)
- **C10-1:** give the real-Chromium case a positive control. Before the timeout, assert that a live
  process whose `comm`/`exe` is Chromium carries the token and sits in a different pgid. Only then
  assert that none survive.
- **C10-2:** route the result write through the watchdog (`Watchdog.write_result`, which checks
  `fired` under the lock), so "no result" after a timeout is guaranteed.
- **C10-3:** write the timeout line with a non-blocking `os.write`, or emit it after `kill_tree`,
  so a blocked stdout can't stall the watchdog.
- **C10-4:** have `ensure_token` re-exec from `sys.orig_argv` (Python 3.10+) to keep interpreter
  flags.
