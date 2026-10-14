---
title: Notebook display epic, round 9 challenger
description: Round 9 check of Revision 8 (05cbff41). C8-1..C8-7 are closed and the runner design is structurally sound. 1 MAJOR (the watchdog disarms at the stamp, so teardown is unbounded) and 5 MINOR hardening items. Verdict REVISE.
status: final
task_id: 260929_notebook-display-design
date: '260929'
---
# Round 9 challenger

Reviewer: praxia:spec-challenger (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-challenge_r9`. Verdict: **REVISE**.

**Closure.** C8-1 through C8-7 are CLOSED.

**Runner design attack.**
- **Process coverage.** The tree walk plus per-pgid kill reaches the Chromium browser, zygote,
  renderer, GPU and node driver. The environ sweep catches double-forked or setsid orphans
  (Python Playwright passes a copy of `os.environ`, and node launches Chromium with
  `process.env`).
- **Sweep scope.** The exact uuid4 token cannot hit another unit or the user's browser, and the
  caller's own pgid is excluded.
- **Freeze window.** Frozen processes are released in step 4. A Ctrl-C or SIGKILL of the caller
  mid-walk could leave them stopped (C9-2).
- **Bound ordering.** Budget < driver kill < CI step: the outer two are tested, the inner one is
  not (C9-4).
- **Watchdog/stamp lock.** Race-free for the rename itself.
- **Sprint A reorder.** Sound: the runner lands first, then A2 and A3 run in parallel. The spikes
  still come first and the sprints still merge independently.

## Findings
- **C9-1 [MAJOR]** The watchdog disarms once the stamp is written, so `browser.close()`,
  `sync_playwright().__exit__` and driver shutdown run unbounded.
  - Locally, the self-bounded form can hang forever, which reopens C8-2.
  - In CI, the step goes red while the aggregate passes.
  - In the driver, `timed_out` conflicts with `stamp.exit 0`.
  - Fix:
    - Close the browser and Playwright inside the bounded region before the stamp, so only
      `os._exit(stamp.exit)` follows it. Alternatively, keep the watchdog armed after the stamp.
    - State that the stamp governs when the driver times out over a valid stamp.
    - Add an AC-42 case: a runner that hangs after its stamp still exits.
- **C9-2 [MINOR]** Harden `kill_tree` and `--reap`:
  - iterate walk and sweep to a fixpoint, freezing everything found;
  - skip `PermissionError`, `ProcessLookupError` or an empty environ, and match the exact
    NUL-delimited entry;
  - send SIGCONT in a `finally`;
  - `--reap` equals `kill_tree` over every token, and refuses to run unless `CI` or `--force` is
    set.
- **C9-3 [MINOR]** Guard against pid reuse before SIGKILL: use `pidfd_open` /
  `pidfd_send_signal`, or verify `/proc/<pid>/stat` starttime. Send group kills only while a
  verified member is still alive.
- **C9-4 [MINOR]**
  - A token set in `os.environ` after exec is invisible in `/proc/self/environ`, so re-exec with
    it set.
  - Arm the watchdog as the unit's first act.
  - An AC-42 case asserts that `run_scenario(<id>)` arms it with that unit's table budget.
- **C9-5 [MINOR]** No gate runs a real Chromium. Add one `test_unit_runner.py` case with headless
  Chromium under `run_unit` that asserts no process carrying the token survives, or a CI reap log
  of survivors.
- **C9-6 [MINOR]**
  - Hash `unit_runner.py` into the D16 harness stamps (add a `runner` input).
  - AC-42 "no result" isn't guaranteed: reword it to "no stamp", or have the watchdog delete the
    result under the lock.

## Rulings for Revision 9
- C9-1: take the first fix. The browser and Playwright close inside the watchdog-bounded region
  before the stamp, and only `os._exit(stamp.exit)` follows it. If a driver timeout happens over a
  valid stamp, the stamp governs and the timeout is logged.
- C9-2..C9-6: apply as stated.
  - C9-3: use `pidfd` where available, with a starttime check as the fallback.
  - C9-5: the real-Chromium `test_unit_runner.py` case, run in CI, never locally (local compute
    rule).
  - C9-6: reword to "no stamp" *and* delete the result under the lock.
- Convergence policy from round 10: decided on BLOCKER/MAJOR only. Any remaining MINOR
  implementation-hardening findings are recorded for the implementing sprint.
