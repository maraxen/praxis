---
title: Notebook display epic, round 8 challenger
description: Round 8 check of Revision 7 (5ebd6d3a). C7-1..C7-9 are closed, the state rows T23-T27 and the AC-38 order are sound, and the resume design is mostly sound. 2 MAJOR findings (a per-unit timeout can't reach a hung Chromium, and a direct --scenario run is unbounded) plus 5 MINOR. Verdict REVISE.
status: final
task_id: 260929_notebook-display-design
date: '260929'
---
# Round 8 challenger

Reviewer: praxia:spec-challenger (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-challenge_r8`. Verdict: **REVISE**.

**Closure.** C7-1 through C7-9 are all CLOSED.

**Resume design attack.**
- The input set is complete, because dist covers Pyodide, the wheels, the shell JS and the theme.
  The only gap is the Playwright version and `uv.lock` (C8-6).
- The stamp is written last and verified against the result's sha256.
- The pass rule and the spike outcomes are unchanged by resume.
- Nothing runs under a whole-run timeout. The job-level backstop is 45 minutes plus the sum of
  the steps.
- Holes: C8-1 through C8-5, and C8-7.

**T23–T27 and the AC-38 order.** Consistent with I1–I6 and with the earlier-round rules. The
nine-key order runs as written, and the K1a/K1b split orphans no key.

**Orchestrator check (260929).** C8-1's premise holds:
`praxis/web-client/node_modules/playwright-core/lib/server/utils/processLauncher.js:108-111` sets
`detached: process.platform !== "win32"`, so Chromium leads its own process group.

## Findings
- **C8-1 [MAJOR]** The per-unit process-group kill does not reach a hung Chromium, and a CI step
  timeout orphans it too.
  - Fix: kill every descendant, including the process groups they lead (walk
    `/proc/<pid>/task/*/children`, then SIGTERM, then SIGKILL each pgid). Alternatively, sweep by a
    unique `--user-data-dir` per unit.
  - Apply the same kill to spike and nd units.
  - AC-42 case: a `setsid` grandchild does not survive.
- **C8-2 [MAJOR]** A direct `--scenario` run, which is the local gate form in A7, B10 and C7, has
  no timeout.
  - Fix: either `--scenario` enforces its own budget with an in-process watchdog (tree kill, no
    stamp, exits naming `timeout`), or local single-unit runs go through the driver (`--only`).
  - AC-42 case.
- **C8-3 [MINOR]** A timed-out re-run leaves the previous stamp in place. The skip rule checks
  neither `exit == 0` nor that every key is present.
  - Fix: a unit deletes its own result and stamp first. Skipping requires `exit == 0` plus every
    key present and passing.
- **C8-4 [MINOR]** The CI aggregate step omits `--base-path /praxis/`, which is a hashed
  argument. Every stamp then mismatches and the gate is permanently red. Its deletion on mismatch
  also destroys the diagnosis.
  - Fix: pass every hashed argument; the workflow test asserts the arguments match;
    `--aggregate-only` never deletes.
- **C8-5 [MINOR]** The AC-39 negatives write into the default output directory and overwrite real
  results.
  - Fix: the nd driver passes a per-negative `--out-dir`.
- **C8-6 [MINOR]** The Playwright version and the `uv.lock` sha256 are not hashed.
  - Fix: add a `driver` input to all three unit kinds.
- **C8-7 [MINOR]** It is undefined whether a spike unit whose probe raised counts as complete.
  - Fix: a written artifact plus stamp means complete. The exception is captured as an `error`
    finding that counts toward `[outcomes]` and is never reused. Only a timeout, or a crash with
    no stamp, is incomplete. Pre-registered in the sidecar.

## Rulings for Revision 8
- Apply everything.
- For C8-2, choose the self-enforced watchdog in `--scenario`, so a bounded local form exists
  even without the driver.
