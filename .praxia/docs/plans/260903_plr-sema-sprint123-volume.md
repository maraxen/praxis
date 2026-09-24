---
title: 'plr-sema sprint 123 plan: the volume family (increment 5) plus two carried rows'
description: 'Sprint plan for 260903_sema-volume: Band A adversarial round on increment 5 (spec_version 13) -> reviewed-round-1; Band B the derivation proof T24/T25 as the go/no-go gate (user decision 260903: build the volume family if it is firable); Band C T26-T29 domain, env gate, registry HM-24 1->2 / HM-25 6->8, mutants v1/v2, tier-2b volume fixtures, lint; Band D the carried #4881a landmine test and #4952 build_setup limits. Baselines to hold, exclusions (#4923/#4924 NO-GO, #4956), dispatch conventions.'
status: active
task_id: 260903_sema-volume
date: '260903'
sprint: '123'
backlog_ids: '4962,4958,4959,4960,4963,4952,4881'
---
# plr-sema sprint 123 plan: the volume family (increment 5) plus two carried rows


> Task id `260903_sema-volume`. Spine: `.praxia/docs/specs/260903_plr-sema-volume-increment.md`
> (increment 5, spec_version 13, status `draft`). Governing decision (user, 260903): **build the volume
> family if it is firable at all** — "the corpus is a set of examples, not the sum of what is valid and
> useful". Fail-closed on unrecognised conjuncts stays (soundness); the "no `WILL_FAIL` on real corpus
> rows at this pin" consequence is a precision note, not a blocker. Planned at HEAD `fe9f4f61` on
> `coxswain-p2-pipeline` (sprints 121 `260903_sema-real-programs` and 122 `260903_sema-followups` closed).

## 1. Composition

| Band | Item | Rows | What | Model | Depends on |
|---|---|---|---|---|---|
| A — spec | **#4962** | — | Adversarial round 1 on increment 5 (it has had none), then remediation to `reviewed-round-1`. Dispose Q2 (HM-25 count 8 vs 10), Q3 (derive-side vs survey-side caller scope), Q5 (v2 threshold). Fix the stale "draft-deferred / NOT SCHEDULED" wording that now contradicts §14.13. | Opus (challenger, defender, author) | — |
| B — gate | **#4958** | T24, T25 | The bridge derivation (B1 for-loop-over-comprehension-output; B2 class-level `AnnAssign`; P1c constructor-call typing) and caller-scope threading (P10), every selection **measured and published**. AC-14.1–14.4. **Go/no-go for the family lives here.** | Sonnet | #4962 |
| C — machinery | **#4959** | T26, T27 | `check/volumestate.py` V0–V4 with V2 threaded pair-by-pair; six fixtures; `env` gate with default = unasserted; registry HM-24 1→2, HM-25 6→8, `REASON_VOCABULARY` 8→10, row-count cap unchanged 24/24. AC-14.5–14.8. | Sonnet | #4958 |
| C — oracle | **#4960** | T28, T29 | `eval/volume_mutants.py` v1/v2; four tier-2b executed volume fixtures incl. two-channel/one-well and collective exhaustion; sidecar fields; `SPEC_INCREMENT_5` in the lint; INDEX regenerated. AC-14.9–14.11. | Sonnet / Haiku (T29) | #4959 |
| D — carried | **#4963** | #4881a | Increment 4's `null`-condition landmine regression test + lid gap-ledger block. Verified 260903 it never landed (no fixture, no assertion, absent from §13.14). Independent. | Sonnet | — |
| D — carried | **#4952** | — | `training/verify/deck.py` `build_setup` limits: one TipRack per tip-typed base, free-rail iterator for Troughs, skip auto trash when declared. Closes the 12 residual tier-1 `rows_setup_error`. Coxswain-side file; #4950 touched it in sprint 122 without collision. | Sonnet | — |
| umbrella | **#4881** | — | Tier-3 container. Closes when #4960 lands or when the gate says no-go and the reason is published. | — | — |

Order of execution: A → B → C serially (each band is the next one's premise); D runs in parallel with A
from the first dispatch, in worktrees, because neither D item touches a file the spine writes.

## 2. The go/no-go gate (band B)

The user's condition is *firable*, not *fires on the corpus*. After T24 and T25 have published their
four measured sets and `aspirate`'s `caller_scope`:

- **GO** if the extended bridge binds `remove_liquid`/`add_liquid` guards for at least one real PLR
  method at the pin (`liquid_handler.py:1031-1035` is the expected site) so that a harness fixture can
  drive the `WILL_FAIL` path under the asserted `env`. Proceed to #4959.
- **NO-GO** if, with B1/B2/P1c all landed, the bridge still cannot bind on the pin. Stop the family,
  publish the measured sets and the structural reason in the spec's implementation record, close #4881
  with that finding, do **not** start T26. The decision comes back to the user with the evidence.

Either way the T24/T25 code stays: the three sub-boxes widen P1a/P8 honestly and are useful to every
later family.

## 3. Decision hooks that stop for the user

1. **Q2 re-count.** If round 1 counts B2/P1c/B1/P10 as four HM-25 patterns (ceiling 10, not 8), stop
   before T27. A row split vs a ceiling bump is the user's ratchet call (§9.4 anti-gaming clause).
2. **NO-GO at band B** (above).
3. **Q5 threshold.** If the round holds that an ungated v2 class must not ship, T28 lands v1 only and
   v2 is measured and reported without a gate; the user decides whether a gate is set afterwards.

## 4. Baselines that must hold at close

| Tier | Baseline (sprint 122 close) | Where |
|---|---|---|
| 1 sidecar-gated replay | 331 executed / 528 ops, `rows_setup_error` 12, crosscheck 191/191 agreement 1.0, 0 unsound | `outputs/plr-sema/oracle_replay_260903_4950.json` |
| 2a bytecode differential | 330/330 agreeing, extractor divergences 0 | `outputs/plr-sema/tier2a_*.json` |
| 2b executed regions | 4 findings, 0 unsound, join by `(method, line_number)` | `outputs/plr-sema/tier2b_260903.json` |
| 3 tip mutants | m1 193/193, m2 254/254, 0 unsound | `outputs/plr-sema/tip_mutants_*.json` |
| registry | rows 24/24 (cap 24), HM-25 declared 6/6, HM-24 1, `REASON_VOCABULARY` 8/12 | `test_hand_maintained_ratchet.py` |

Tier-1 replay is always run with `--sidecar training/assemble/out/corpus_p25_sidecar.jsonl
--crosscheck training/out/corpus_p23_floor.jsonl --crosscheck training/overlay_gen/out/overlay_full.jsonl`.
#4952 is the one item allowed to move tier 1 (`rows_setup_error` 12 → published residual, executed
rows up, crosscheck unchanged).

## 5. Explicitly out

- **#4923** incremental re-check and **#4924** recovery interpreter — NO-GO criteria in increment 4
  §13.12 stand (workload unmeasured; over-fill verdict undecidable until `max_volume` reaches the wire).
  Increment 5 puts `max_volume` on the wire, so #4924's criterion may reopen *after* this sprint.
- **#4956** P2.6e label-conflict audit — Coxswain track, needs its own prereg, user's call.
- REPL refocus P0–P7 and Coxswain W0–W6 — other track.
- Any new registry row. Increment 5 spends per-row ceilings only.

## 6. Dispatch conventions (unchanged from sprints 121/122)

- Fixer briefs mandate: `uv run python` never bare python; per-file pytest only (the jax-mem-guard
  blocks any path ending in `/tests`); path-scoped `git add`; **no background Bash, no monitors**;
  foreground with timeout; final line `COMMIT: <full sha>`; trailers `Co-Authored-By: Claude Fable 5.1
  <noreply@anthropic.com>` + `Claude-Session: https://claude.ai/code/session_01QgK1DBdBsTFJou6ML91sNT`.
- Run the **full** per-file set before closing a band: `test_derive`, `test_check_graph`,
  `test_wire_fuzz`, `test_verdict` (the §3.3 reason scan — no fixer gate ran it in sprint 122),
  `test_hand_maintained_ratchet`, `test_cache`, `test_oracle_replay`, `test_spec_lint`.
- Challenger/defender agents have no write tool; the orchestrator persists their reports under
  `.praxia/docs/audits/260903_plr-sema-volume-round1-{challenger,defender}.md`.
- Never touch the other session's dirty entries in the tree; `git push` needs the sandbox off.
- Spec citations drift when code lands: re-anchor pass (`check_spec_citations.py`) before close.

## 7. Estimate

Spec rows: T24 ~420, T25 ~230, T26 ~360, T27 ~200, T28 ~430, T29 ~15, #4881a ~120; #4952 ~150.
Sprint 122 delivered a comparable set (5 rows + a spec round) in one day; band B's measurement
discipline and the round make this one closer to a day and a half.

## 8. Outcome (260904)

**Go/no-go result: GO.** Band B (T24/T25) published all four measured sets and `caller_scope`s per
§14.0's gate — the extended bridge binds `remove_liquid`/`add_liquid` guards on real PLR
(`liquid_handler.py:1031-1235`), so `GATE = GO` per T25's own recorded result, and band C proceeded.

| Band | Item | Commit(s) | Numbers |
|---|---|---|---|
| A — spec | #4962 | `5458f24b` + `c5f6068f` (round-1 audits), `7b1913cd` (remediation, `reviewed-round-1`, spec_version 14) | Challenger O1–O14, defender's twelve-item ordered list, all applied; deliverable narrowed to "a definite `WILL_FAIL` on a tip over-draw, `SAFE`/`UNKNOWN` on every well" |
| B — gate | #4958 | T24 `2e50e613`, T25 `5582ae08` | B1 2 tuples; B2 100 classes/467 attrs; P1c 45 classes/67 entries; four `caller_scope`s published matching §14.0.2's disposition table; survey regeneration 4770 records unchanged, dropped entries 4717 → 5769 with multiplicity, 0 non-additive diffs |
| C — machinery | #4959 | T26 `92776b8e`, T27 `96234d90` | First volume `WILL_FAIL` at `PlrSite(volume_tracker.py, 92, VolumeTracker.remove_liquid)`; `REASON_VOCABULARY` 8 → 10; HM-24 `declared` 1 → 3 (user-approved 260904, not the originally planned 1 → 2), HM-25 `declared` 6 → 8; `live_rows() == 24 == BUDGET_CAP` |
| C — oracle | #4960 | T28 `c67fc230`; T29 (this docs-close pass) | v1 67/67 raised, 67/67 `WILL_FAIL` at raised index, 0 unsound; m1 199/199, m2 289/289, 0 unsound (non-regression held); tier-2b 16 fixtures, `region_unsound` 0, `region_will_fail_fired` 7; tier 1 unsound 0, `rows_executed` 343, `setup_error` 0; lint id renamed `increment-5-volume-deferred` → `increment-5-volume`, citations re-anchored, `test_spec_lint.py -q` 24 passed |
| D — carried | #4963 | `7761af22` | `#4881a` null-condition landmine regression test + lid gap-ledger block landed; recorded in increment 4 §13.14 this pass (it was never added when the commit landed in sprint 122) |
| D — carried | #4952 | `717d16af` | `build_setup`: tier 1 343 executed / 548 ops, `setup_error` 0 (was 12) |
| umbrella | #4881 | closed by #4960 landing | volume family shipped; lid family (#4881, first half) stays not-adopted per increment 4 §13.1 |

**Registry arithmetic actually spent** (vs this plan's §1 estimate of HM-24 1 → 2): **HM-24 1 → 3**,
not 1 → 2 — the defender's O12 adjudication (band A, round 1) moved B1 from HM-25 to HM-24 on the
registry's own silent-versus-loud criterion before band B started, so the plan's §1/§4 HM-24 figure
was superseded before it was spent. HM-25 landed exactly as planned, 6 → 8. Both approved by the user
260904 (§14.16 Q2). Tier-1 baseline moved from this plan's §4 table (331/528/12 setup_error) to
343/548/0 setup_error via #4952 (band D), as §4 anticipated.

Full per-row detail, including divergences from each task row's own spec expectation and why each is
acceptable, is in `260903_plr-sema-volume-increment.md` §14.17.
