---
title: Notebook display epic, round 7 challenger
description: Round 7 check of Revision 6 (98b05e93). C6-1 and C6-2 are closed and the deck panel state machine is sound. 2 MAJOR findings against the user's new preemption-safety rule (browser harnesses, spikes), plus 6 MINOR and 1 SUGGESTION. Verdict REVISE.
status: final
task_id: 260929_notebook-display-design
date: '260929'
---
# Round 7 challenger

Reviewer: praxia:spec-challenger (Opus). Record: `.praxia/audits.jsonl`
`260929_notebook-display-design_spec-challenge_r7`. Verdict: **REVISE**.

**Scope added this round.** The user's global rule of 260929 requires that intensive
calculations be preemption-safe and recoverable by design:
- persist each unit as it completes, with a completion stamp;
- resume by skipping units whose sha256 is verified;
- use a timeout per chunk and a process per chunk, never one whole-run timeout;
- put the design in the spec and in the sidecar.

**Closure.** C6-1 and C6-2 are CLOSED.

**State machine audit.** The table is complete for its 8 events, deterministic, and consistent
with I1–I6 on every row. Every earlier-round requirement is preserved: `late_iframe`/AC-39(e),
C5-2, C4-1, C3-3, B-1, `many_reloads`, re-dock, and the drawer. The AC-38 execution order is
runnable, traced key by key. The lifecycle work has converged.

**Orchestrator check (260929):** the harness is `scripts/repl_smoke.py` at the repo root on
`origin/main`. `run_notebook_check` (`:1463`) builds one `RESULT` and prints it once at the end
(`:1769`). `.github/workflows/repl.yml:43` sets one job-level `timeout-minutes: 45`. Both
premises hold.

## Findings
- **C7-1 [MAJOR]** The `--display-check` and `--dock-check` harnesses violate the preemption rule:
  one process per run, results written only at the end, and a single 45-minute job timeout. The
  scenarios are D1, D1-dark, D2, D3, D4, K1 and K2, and each boots Pyodide. The AC-39
  sensitivity runs re-run whole harnesses. Fix:
  - the scenario is the unit;
  - `--scenario <id>` runs one scenario in its own process with its own timeout;
  - each scenario writes `result.<id>.json` plus a stamp with sha256 of its inputs (dist
    manifest, notebook, harness, chrome path and version) and of its output;
  - a driver resumes by skipping hash-matched units and records what it reused;
  - K1 is atomic;
  - the aggregate rule is unchanged;
  - CI runs one step per scenario, each with its own timeout, uploads results with
    `if: always()`, and states its policy on reuse across reruns;
  - each AC-39 negative runs only its own scenario.
- **C7-2 [MAJOR]** The S1–S4 spikes violate the preemption rule: each is one `bth run` with its
  outcome written at the end, and there is no unit, resume or chunk design. Fix:
  - D17 and each sidecar list the units (probes, trust paths, negative controls);
  - each unit writes `units/<name>.json` plus a stamp with input and artifact sha256;
  - each browser path runs in its own context or subprocess with its own timeout;
  - `--resume` skips verified units;
  - the research note records what was reused;
  - `[outcomes]` are evaluated over the full unit set;
  - S3 and S4 may each declare themselves one bounded unit, with a timeout.
- **C7-3 [MINOR]** A stopped viewer must unsubscribe from `praxis_viz3d`. Otherwise
  `late_iframe`'s reopen can get two announces (a dead v2 and a live v3), and end on the dead
  one. AC-31: after `stop()`, a `query` gets no `announce` and an `open` gets no `accept`.
- **C7-4 [MINOR]** T4 should attach the panel "in the current tier's home (split or drawer)".
  §3.6's opening says "split right", which is wrong in the drawer tier.
- **C7-5 [MINOR]** AC-36 K2 doesn't state its execution order or page count. For example: a fresh
  page at 1152, then `dock()` (T2), then the drawer keys, then `tier_up_rehomes`, then the other
  viewports opened through toggle.
- **C7-6 [MINOR]** A kernel restart or shutdown kills the viewer without a `close`, leaving a
  frozen deck that looks live. Fix: add an event from `sessionContext`, treated like a kernel
  close, or accept the behaviour and say so.
- **C7-7 [MINOR]** Re-applying the preset after a reload is untested, and it may fire before the
  first `scene` arrives. Re-apply after `resources()` is non-empty, and add
  `preset_survives_reload`.
- **C7-8 [MINOR]** The AC-39 exit codes are pass/fail findings cited in the PR with no
  pre-registration. Give them sidecars, or state why they are exempt.
- **C7-9 [SUGGESTION]**
  - Exclude the tier-crossing DOM move from "iframe reload", so T15 and T16 are not both
    triggered.
  - Make a same-id announce in T11 a no-op.
  - Add a `redock_live` key: a live viewer re-docked into an open panel, in the browser.

## Orchestrator rulings for Revision 7
- Apply C7-1 and C7-2 as stated.
- C7-3, C7-4, C7-5 and C7-7 as stated.
- C7-6: add the kernel-restart event.
- C7-8: sidecars for the AC-39 runs.
- C7-9: all three.
