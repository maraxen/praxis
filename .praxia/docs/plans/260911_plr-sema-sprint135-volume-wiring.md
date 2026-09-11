---
title: 'plr-sema sprint 135 plan: thread volume_tracking_observed into the corpus-replay path (#5043) -- a bugfix_simple sprint run as the first surface-dispatch pilot'
description: 'Sprint plan and outcome for 260911_sema-volume-wiring: one P2 bug, #5043 -- oracle_replay.py run_row and oracle_spike.py capture RuntimeOutcome.volume_tracking_observed but never passed it to run_static_calls. Fixed (T57, 80dd7103) by a Cursor agent over ACP via praxia surface_dispatch, verified by diff and an independent per-file run (75 passed). Re-measured (T58, b857b301): EVERY benchmark count identical to the inc8 baseline, volume_state_unknown 194 -> 194, unsound 0 -> 0 -- the item''s inflation hypothesis is measured FALSE because the env member is consumed only on a firing volume guard and no benchmark row has one. Published ledgers since increment 5 stand. Records the pilot''s findings: a transient ENOSPC, two praxia-side dispatch bugs (retry self-refusal; envelope.json outside the allowlist), claim_verified null on the ACP surface, and the worktree guard forcing commit-after-copy-out.'
status: completed
task_id: 260911_sema-volume-wiring
date: '260911'
sprint: '135'
backlog_ids: '5043'
---
# plr-sema sprint 135 plan: thread `volume_tracking_observed` into the corpus-replay path (#5043)

> Task id `260911_sema-volume-wiring`. Praxia sprint id **135** (the DB assigned 135, not the 134 the
> loop's triage text guessed -- same lesson as sprint 130/"128"). Planned at HEAD `12003b06` on
> `plr-sema-inc8-move-family` (PR #158's tip, stacked on #157 → #156); executed on the new branch
> `plr-sema-volume-observation-wiring`, based at that same commit. PLR pin `dd79c4c89`, frozen
> benchmark `tier1-sidecar-gated-dd79c4c89`. Decision log: `.praxia/docs/daily/260911_overnight-decisions.md`.

## 0. How this sprint was selected (TRIAGE, autonomous, L5)

The loop was re-fired 260911 with `/praxia:orchestration /praxia:autonomous-praxia-dev-loop and use
surface dispatch` after sprint 133 closed **NO-GO on §17.8.2 condition (1)** and escalated the
`:2070` question to the user. That question is **still the user's** -- this sprint does not presume an
answer to it and does not start increment 9. It picks the highest-value executable item that is
*independent* of that decision.

**Staleness closure first (idea-351 gap).** The backlog's top P1 candidates were the six Coxswain items
#4389-#4394 (W1.0 CI wiring through W5 audit trail). Every one is already shipped on this branch:
`71717536` (W1.0, the `coxswain` job and `coxswain/**` path filters in `repl.yml`), `e22e9968` (W1),
`e84f8010` (W2), `c42adc1f` (W3), `9d7b24d9`/`b4bffc5e` (W4), `4827f3f0`/`2e1a2373`/`2dc8c3a7` (W5).
All six were marked `completed` with those citations. W6 (#4395) stays open: it is explicitly
conditional on W0's verdict.

**Remaining executable P1s** are the three REPL-refocus phases (#4293/#4294/#4296). All are
`extended`, all need a headless-Chromium + Pyodide run under a disabled sandbox, and #4293's S-E
sub-spike needs a human with a device. Under the L5 heuristic (prefer `standard` over `extended`;
break ties toward items that unblock others) they lose to:

**#5043 (P2, `bug`)** -- small, real, in the thread the last six sprints built, and bearing on the
published counts every later increment cites. Verified this pass rather than trusted:

| what | where | state at `12003b06` |
|---|---|---|
| `run_static_calls` accepts the keyword | `plr-sema/eval/oracle_common.py:855-861` | `volume_tracking_observed: bool = False` (T27, #4959) |
| `RuntimeOutcome` carries the observation | `plr-sema/eval/oracle_common.py:488`, populated at `:547` | present |
| corpus-replay call site 1 | `plr-sema/eval/oracle_replay.py:417-431` (`run_row`) | passes `plr_observation`, `excludes_sites`, `scope_excluded_sites`, ... -- **not** `volume_tracking_observed` |
| corpus-replay call site 2 | `plr-sema/scripts/oracle_spike.py:84` | passes `param_names` only |
| the correctly wired sibling | `plr-sema/eval/predicate_mutants.py:236-239` | `volume_tracking_observed=bool(result.get("volume_tracking_observed"))` |
| the precedent test | `plr-sema/tests/test_oracle_replay.py:1434` `TestT46ObservationThreading` | drives `oracle_replay.main` end-to-end on a synthetic row |
| the suspected-inflated baseline | `outputs/plr-sema/unknown_ledger_260910_inc8.json` | `n_findings_by_reason.volume_state_unknown` = **194** over 544 ops; `unsound` 0 |

Decision rubric (parts/01_triage.md): `category=bug` → `brainstorm_needed=false`; adversarial
**TIER1** (skip challenger, INVEST gate only); PCW template **`bugfix_simple`** (recon → fixer →
auditor). No spec document was authored; this plan is the spine.

## 1. Composition (as executed)

| Step | What | Surface / model | Result |
|---|---|---|---|
| recon | Orchestrator's own source reading, logged as `260911_loop_backlog_scan_and_recon` in `.praxia/recon.jsonl` (the table above). The recon microflow was not dispatched: the item names its own lines and every one was verified directly. | in-session | done |
| **T57 fixer** | Add `volume_tracking_observed=rt.volume_tracking_observed` at both call sites with `#5043` comments in the T46 style; add `TestT57VolumeObservationThreading`, differential by construction; per-file pytest; **do not commit** (admission reads `git status`). | **`surface_dispatch` → Cursor, ACP, `standard` = `cursor-grok-4.6-medium`**, dispatch `e8e410a9` | `terminal_state: completed`; three files modified exactly as briefed; **75 passed** in the dispatch worktree and again here → **`80dd7103`** |
| admission | §2.3 checks + orchestrator verification. | child + orchestrator | `claim_verified: null` (ACP returns no structured self-report) → verified by hand: `diff -u` against the identical base, independent test run |
| **T58 measure** | Ledger re-run, identical recipe to the inc8 header (§2), into `outputs/plr-sema/unknown_ledger_260911_volwire{,.oracle_replay}.json`; compare with `scripts/compare_unknown_ledgers.py`; probe the wire with `scripts/probe_volume_observation.py`. | in-session Bash (measurement, not an edit) | **`b857b301`**; see §5 |
| audit | `code_review_diff` (rig, titanix vLLM) over `12003b06..80dd7103`; `praxia:reviewer` (Sonnet) over `12003b06..b857b301` against §3. | rig + in-session | see §5 |
| close | this §5, backlog #5043 + sprint 135 completed, `docs index`, PR against `plr-sema-inc8-move-family`. | in-session | see §5 |

## 2. The measurement recipe (from the inc8 artifact's own header)

Run from `plr-sema/` (the header's paths are relative to it):

```
uv run python eval/unknown_ledger.py \
  --corpus    ../training/assemble/out/corpus_p25.jsonl \
  --sidecar   ../training/assemble/out/corpus_p25_sidecar.jsonl \
  --crosscheck ../training/out/corpus_p23_floor.jsonl \
  --crosscheck ../training/overlay_gen/out/overlay_full.jsonl \
  --report         ../outputs/plr-sema/unknown_ledger_260911_volwire.json \
  --replay-report  ../outputs/plr-sema/unknown_ledger_260911_volwire.oracle_replay.json
```

`contracts_path` is the default `data/derived_contracts.json`; its sha256 `98e23fe5…b70d2a` is
identical in both headers (this sprint touches no derive code). Wall time ≈ 90 s.

## 3. Gates

1. **Soundness (hard):** `unsound == 0` and `unsound_scoped == 0` and `totality_violations == 0`.
2. **The wire is live:** `volume_state_unknown` strictly decreases from 194 -- or, if it does not, the
   reason is published; both are findings, neither is a pass by default.
3. **Nothing else moves:** `guard_env_dependent` 2083, `guard_predicate_unparsed` 495,
   `guard_operand_unknown` 144, `pick_up_tips` SAFE 216, `contracts_sha256` identical.
4. **Test:** `cd plr-sema && uv run pytest tests/test_oracle_replay.py -q` green.
5. **Admission:** `claim_verified: true`, or -- when the surface cannot report -- orchestrator
   verification by diff and independent test run, recorded as such.

## 4. Surface-dispatch pilot record (the user asked for this; these are the findings)

- **Transport `acp`, requested explicitly.** `auto` resolves straight to headless (debt #1762). ACP is
  the transport the crate live-tested against exactly this `cursor-agent` build (`2026.09.10-fd3934a`).
  Consequence accepted and recorded: `containment: "none"`; the permission engine was never consulted.
  Admission's git checks plus the orchestrator's own diff and test run were the real gate.
- **Three launches to one completion.** `cfc81e4e` attempt 0 died of a **transient ENOSPC** on the root
  volume during admission (git could not write the submodule `index.lock`; the terminal record's append
  failed) -- a minute later `df` showed 92–96 GB free and the host drive 695 GB free; the spike's source
  was not identified. `cfc81e4e` attempt 1 was **refused by the retry precondition** because the MCP
  `run` handler writes `envelope.json` into `.praxia/dispatch/<id>/` *before* spawning and the child
  then counts that very file (and `.praxia/dispatch/.lock`) as unclaimed untracked paths → **the retry
  contract cannot succeed through the MCP surface as shipped.** `e8e410a9` attempt 0 (fresh id, same
  base, stale dispatch dir deleted) completed.
- **`envelope.json` is outside the materialization allowlist** on the completed record too
  (`git_status_unscoped` lists it next to the three real edits). Same root cause as the retry refusal.
- **The ACP surface returns no structured self-report**, so `files_changed_claimed: []`, `tests: []`,
  `claim_verified: null`. The record is, by the tool's own definition, an unchecked model claim; the
  orchestrator verified by hand.
- **Environment setup belongs in the brief.** A fresh worktree has no `external/pylabrobot` submodule
  (`uv sync` fails: "does not appear to be a Python project"); the fixer's step 0 was the submodule init
  and `uv sync --all-packages`. The agent's tooling also created an unignored `.serena/` cache at the
  worktree root; the brief was amended to make it delete tooling caches before finishing, and it did.
- **The worktree guard forces commit-after-copy-out.** The session's isolation hook refuses git in a
  sibling worktree, and admission requires the edits to stay uncommitted, so the flow was: copy the three
  files out → `git worktree remove --force` → check the sprint branch out here → copy in → commit.
- **What worked exactly as designed:** the one-dispatch-per-worktree lock, the marker/lock/record
  crash classification, `git reset --hard <base>` leaving untracked files alone, detached execution
  surviving the orchestrator's turn boundaries, and the agent following a dense brief precisely (test
  first and observed red, then the fix, then green, then cleanup, no commit).

**To file in the praxia repo (not here):** (1) `praxia_dispatch::materialized_paths` must include the
MCP-written `envelope.json` (and the retry precondition must exclude `.praxia/dispatch/.lock`), or the
MCP `run` handler must write the envelope somewhere allowlisted; (2) the ACP executor should map the
agent's final message into `structured_output` / `files_changed_claimed` so `check_scoped` has
something to verify; (3) `pm_triage` on `vllm/titanix-vllm-primary` (Qwen3.8-27B) exhausted its 900 s
fork/join with the `backlog_triage` branch unable to emit a parseable `write_backlog_triage_result`
(three retries; one attempt put an entire JSON payload in `debt_id`).

## 5. Outcome

**All seven task steps landed. Gates 1, 3, 4 and 5 hold. Gate 2 fails in the informative direction.**

| quantity | inc8 baseline (`92dc7df6`) | volwire (`80dd7103`) |
|---|---|---|
| `n_findings_total` | 2916 | **2916** |
| `guard_env_dependent` | 2083 | 2083 |
| `guard_predicate_unparsed` | 495 | 495 |
| `guard_operand_unknown` | 144 | 144 |
| **`volume_state_unknown`** | **194** (117 `add_liquid`, 77 `remove_liquid`) | **194** (identical clusters) |
| `volume_tracking_unasserted` | 0 | 0 |
| `n_findings_decided` | 3618 | 3618 |
| `unsound` / `unsound_scoped` / `totality_violations` | 0 / 0 / 0 | 0 / 0 / 0 |
| `pick_up_tips` `n_scope_verdict_safe` | 216 | 216 |
| decided-by-site / resolved-by-rule changes | -- | **0 / 0** |
| `contracts_sha256` | `98e23fe5…` | identical |

**Why nothing moved, and why that is the finding.** `scripts/probe_volume_observation.py` shows the
wire is live: `run_static_calls` now receives `volume_tracking_observed=True` on **30 of 30** executed
rows in a 120-row prefix (pre-fix the keyword was absent, so `env` was always empty). But the env member
`does_volume_tracking` is consumed in **exactly one place** -- `check/volumestate.py` `_pair_finding` →
`volume_guard_is_unconditional(..., env)` -- and only on the branch where the interval arithmetic
*proves* a volume guard fires, where it chooses `will_fail` over `volume_tracking_unasserted`. The
`safe` and `volume_state_unknown` branches are env-independent. No benchmark row has a firing volume
guard (`volume_tracking_unasserted` is 0 before and after), so the env is never read there, and the 194
are unknown well-volume **state** by design (interval too wide, or `add_liquid`'s non-decreasing
direction), not a tracking-mode gap.

**So #5043's hypothesis -- "likely inflates the published `volume_state_unknown` /
`guard_predicate_unparsed` baseline counts across every increment since 5" -- is measured FALSE.**
Every published ledger since increment 5 stands as published. The fix is still correct and still
wanted: it removes a latent divergence between the corpus-replay path and the mutant harnesses (whose
`v1_overdraw_dispense` class reaches `will_fail` 67/67 precisely because they threaded the flag), and
any future corpus row that does overdraw will now be `will_fail` rather than `volume_tracking_unasserted`.

**Audit.** `praxia:reviewer` (Sonnet) over `12003b06..b857b301`: **PASS**, high confidence, no
required fixes -- scores 5/5/4/4/5/5; the one-line soundness answer is "No": `env`'s only consumer is
`volumestate._pair_finding`'s `fires` branch, the `safe` branch is env-independent, so no SAFE is
reachable that the pre-change code would not have produced. Two cosmetic suggestions, dispositioned in
`.praxia/docs/audits/260911_plr-sema-sprint135-audit.md` (the 2-space indentation is what the repo's
configured `ruff format` emits under `indent-width = 2`; the `oracle_spike.py` comment was expanded to
parity in the close commit). `code_review_diff` (rig): see §6.

## 6. pm_triage reconciliation and audit addendum

`pm_triage` (rig-run, `vllm/titanix-vllm-primary`) was launched at TRIAGE as the skill mandates and
**wrote no record**: fork/join timed out at the 900 s walltime with 2 of 4 branches finished; the
`backlog_triage` branch exhausted its retries failing to emit a parseable `{reasoning, action}` for
`write_backlog_triage_result`. The orchestrator's backlog scan (logged) stood as the triage; the route
was rubric-determined regardless.

_Audit addendum: written when both reviews land._
