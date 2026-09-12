---
title: 260912 autonomous loop decisions (L5)
description: 'Every decision the 260912 L5 loop made without a human gate: the REPL-refocus staleness dispositions, the #5110 selection, and the praxia debt filings.'
status: completed
task_id: 260912_repl-gate-manifest-scope
date: '260912'
---
# 260912 autonomous loop decisions (L5)

Autonomy L5: decisions taken without a human gate, logged here so they can be
backtracked. Sprint record: `.praxia/docs/plans/260912_repl-gate-manifest-scope-sprint136.md`.

| # | decision | rationale | reversible? |
|---|---|---|---|
| 1 | Ran a TRIAGE **staleness pass** before scoring anything | The only P1s on the board were three REPL-refocus items that had sat open for multiple sprints; last cycle six Coxswain items proved fully shipped but open (praxia idea-351). | n/a (read-only) |
| 2 | Audited against `origin/main`, **not** the working tree | This worktree is on a stacked branch three deep off an older base; `repl/`, `praxis-browser/` and `build_browser_wheels.py` are absent here, which would have read as "not built" when the real tree is `web-repl/`. | n/a |
| 3 | Spot-checked three of the audit's load-bearing claims myself | A subagent report is not evidence. Verified the vendored visualizer tree, the three pinned storage names, and the submodule pin. | n/a |
| 4 | **Closed #4294** (wheel pipeline) | Shipped: `build_wheels.py` (561 lines), archive export, `+g<sha8>` stamp, manifest as the single seam. Pin is 0.2.2/`dd79c4c89`, not the 0.1.6 the item assumed. Corroborated independently by plr-sema's benchmark name and by this sprint's own build stamping `0.2.2+gdd79c4c8`. | yes (reopen) |
| 5 | **Closed #4297** (visualizer vendor) | Shipped at `web-repl/overlay/assets/visualizer/`, `receiveFromPython` at `vis.js:255`, GATE G6 records 4 anchors + 5 CDN swaps. | yes |
| 6 | **Rescoped #4293** to S-E only, `extended` -> `standard` | Six of seven spikes closed with adjudicated verdicts (PARTIAL-GO). Flagged explicitly as **not autonomously runnable**: needs a human, real USB/HID/serial hardware, non-headless Chromium. | yes |
| 7 | **Rescoped #4296** to the P5.8 persistence ladder | Its two motivating claims are false -- the lab surface and all three pinned storage names already shipped. Noted it still needs a design call (plan U16/U17) before execution. | yes |
| 8 | **Rescoped #4298** to CLAUDE.md + debt-1293 | `repl.yml` exists and runs the full browser battery; the just-prohibition holds. Root `CLAUDE.md` and the `.agent/` migration genuinely remain. | yes |
| 9 | Did **not** pick up any rescoped REPL item | #4293 needs a human + hardware; #4296 needs a design call; #4298's residue is a `quick` write but lower value than a P1 blocking four PRs. | n/a |
| 10 | Filed **#5110** and selected it as the sprint | Found while checking REPL health: `repl.yml` red on all 8 runs since 260904, on the base of the whole PR stack, skipping ten browser gates. A P1 bug on no list anywhere. | yes |
| 11 | Branched off **`main`**, not off the failing branch | A `pull_request` run builds the merge result, so landing the fix on main reaches PR #156's next run. Branching off #156 would not help #157-#159. | yes |
| 12 | Fixed the **checker**, not the data | The nine flagged files are legitimate tracked artifacts of a sibling subproject. Deleting or gitignoring them to green a gate would have been the wrong repair; the brief forbade it explicitly. | yes |
| 13 | **Narrowed R6's manifest arm** against its own "repo-wide, no per-name exception" wording | A deliberate, logged spec deviation. That wording predates a sibling subproject shipping files with this generic basename; the rule's *intent* is the wheel-loader seam. The `.whl` arm was left repo-wide. | yes |
| 14 | Verified the fixer's work **by hand**, including a red run against the unfixed script | The ACP surface returns `claim_verified: null` (praxia debt #1773), so the agent's own report is an unchecked claim. Tests 2 and 3 pass in both directions by design. | n/a |
| 15 | Built wheels locally to exercise **`check_wheel_contract.py`** | That second command of CI step 12 has never run (the step aborts at the first failure), so "coherence is fixed" would not by itself have proven step 12 green. It now exits 0. | n/a |
| 16 | Filed praxia **debt #1792** and **#1793** | #1792: `envelope.json` outside the materialization allowlist / retry self-refusal. #1793: `code_review_diff`'s `fmt` step reformats the workspace it reviews. | yes |
| 17 | Did **not** file two other findings | Already covered: pm_triage's missing record by **#1750** (P1, names the pm_triage symptom exactly) and **#1699**; the ACP null self-report by **#1773**. Duplicates would have added noise. | n/a |
| 18 | Left the increment 9 / `:2070` question untouched | Spec S17.8.2 directs it to the user; the loop does not presume an answer. | n/a |

## Not done, and why

- **No `pm_triage` microflow run.** It burned its full walltime without a record last
  cycle, and praxia #1750 (P1) identifies the cause as a WaitAll join deadline race that
  drops the synthesis step -- naming the pm_triage zero-record symptom explicitly. The
  orchestrator's own logged backlog scan plus the Sonnet staleness audit stood as TRIAGE.
- **No `code_review_diff` run.** praxia #1793, filed this cycle: its `fmt` verification
  reformats the workspace it reviews. A Sonnet `praxia:reviewer` was the gate of record.
- **Nothing merged, nothing pushed to main.** PRs only.
