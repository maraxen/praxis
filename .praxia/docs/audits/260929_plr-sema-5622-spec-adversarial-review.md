---
title: Adversarial review of the plr-sema PLR 1.0 tip-effect spec (#5622)
description: 'Four-round challenger/defender review of spec 260929_plr-sema-plr1-tip-effect-increment: per-round verdicts, blockers, orchestrator rulings on disputed points, convergence (round 4 ACCEPT)'
status: draft
task_id: 260929_plr-1.0-migration
date: '260929'
verdict: 'ACCEPT (round 4)'
base_sha: 'a176bac7'
---
# Adversarial review of the plr-sema PLR 1.0 tip-effect spec (#5622)

Spec: `.praxia/docs/specs/260929_plr-sema-plr1-tip-effect-increment.md` (§18), on branch
`plr-sema-5622-spec`. Each round's challenger and defender read the cited code themselves; agent
records are in the worktree's `.praxia/audits.jsonl` under the ids
`260929_plr-1.0-migration_spec18_challenge_r{1..4}` and `..._spec5622_defense_r{1,2}`. The author
revised in place; the per-objection change log is the spec's §18.17. The citation lint
(`plr-sema/scripts/check_spec_citations.py`) was run on every revision with 0 failing citations.
The owner's locked decisions L0–L7 were never reopened.

## Rounds

| Round | Spec | Challenger | Defender | Outcome |
|---|---|---|---|---|
| 1 | r0 | REVISE: 2 BLOCKER, 11 MAJOR, 16 MINOR | REVISE: 20 concede, 10 partial, 0 rebut | r1 |
| 2 | r1 | REVISE: 4 BLOCKER, 6 MAJOR, 7 MINOR (M7/M8 applied incorrectly) | REVISE: all blockers conceded, fixes corrected | r2 |
| 3 | r2 | REVISE: 1 BLOCKER, 1 MAJOR, 5 MINOR | none (the orchestrator verified the facts directly) | r3 |
| 4 | r3 | **ACCEPT**, no BLOCKER or MAJOR | — | converged |

## Blockers and how they closed

- **r1-B1:** a `Call`/`Subscript`/other possibly-None write was classed HAS_TIP, which reproduces the old pin's
  unsound `load_state`. **Fix:** classify it UNRESOLVED, with an inline old-pin fixture.
- **r1-B2:** a parameter rebound in the helper body was ignored. **Fix:** join the parameter with every one of
  its bindings.
- **r2-C1:** the pre-registered PASS was unreachable. m1 was scored over runs rather than raised runs, and the
  p3a floor already failed at inc8, the NO-GO this increment excludes. **Fix:** use the raised-run
  denominator, exclude the p3a floor from the gate, and make p3a reported-only.
- **r2-C2:** HAS_TIP could come from an unannotated or `Optional`-shaped parameter. **Fix:** a node-shape
  allowlist over a tip type derived from W that must be a singleton (fail closed).
- **r2-C3:** the write table had no catch-all (`setattr`, `for self.x in`, `__dict__`, …). **Fix:** those
  forms become UNRESOLVED.
- **r2-C4:** the `:338` decline counters had no producer and mismatched units. **Fix:** a pure
  first-failing-conjunct function, scoped to planned pickups, with consistency hard terms.
- **r3-X1:** a bare `self` could escape by aliasing or by being passed to a followed call. **Fix:** any bare
  `self` Load outside an Attribute base makes the method UNRESOLVED.

Every blocker fix was traced by a reviewer to cost zero recovered effects at the 1.0 pin
(786ac2c4e) and at the old pin (dd79c4c89).

## Orchestrator rulings on disputed points

- **r1 M6:** rewrite the text around the harness-grounding premise. A tip-spot ref conjunct would need a
  hand-typed parameter name (L0), and no derived table supplies one (all 13 inlined `:338` records have
  `caller_args: null`).
- **r1 M5:** defer the whole-surface rack-topology closure check to OI-2 as a follow-up. Pin the derived
  move family instead, and name TOP as fail-open.
- **r1 M7:** the lidded-rack mutant m3 is **in scope**. It is the only in-run falsifier of a wrong
  `:338` SAFE (for the observation conjunct).
- **r1 M2:** widen when depth-0 and deep bridge effects coexist. This amends increment 1's E2.
- **r2 D-1:** p3a's floor is reported-only, because its 1.0 baseline was never measured.
- **r2 D-2:** the analyzer-side decline reason is computed in the measurement script through the existing
  sinks. Nothing is threaded through `check/`.
- **r2 D-3:** `self` passed to an unfollowed call is UNRESOLVED. This was generalised by r3-X1.
- **r2 D-4:** m3b is dropped. The harness has no Lid source, and AC-18.11(d)(e)(f) cover the topology
  conjunct.

## Facts verified by the orchestrator

- inc7 m1: 289 ran, 199 raised, 199 will_fail (`outputs/plr-sema/tip_mutants_260909_inc7.json`).
- inc8 p3a: `floor_met: false`, `gate_passed: false` (`outputs/plr-sema/tip_mutants_260910_inc8.json`).
- PLR 1.0 `Liddable.assign_child_resource` raises only on an existing lid or an undersize beyond
  `LID_UNDERSIZE_TOLERANCE` (`resources/lid.py`).
- Bare `self` in either tracker occurs only as a method parameter.
- `observation_env_members` is called as a module global inside `run_static_calls`.

## Owner rulings (260929, after convergence)

- **OI-21:** A-CALLBACK-INERT is **accepted** as a named assumption. T61 adds its row to increment 1's
  §10.6.3 table. The fail-closed callback guard that would turn it into a check is backlog #5661.
- **OI-4:** HM-25 12 → 13 is **booked**. The zero-cost alternative was declined.
- **New global rule applied:** the T63 measurement is preemption-safe and resumable. It has seven
  units, each hash-stamped and reused only on a full match, with a timeout per unit. Outcome criteria
  are unchanged.
- **OI-22:** churn of the `_before` writer snapshot is accepted as a deliberately loud trade.
- **Deferred follow-ups filed:** #5662 (rack-topology closure, OI-2) and #5663 (tip-spot argument
  conjunct, OI-3).

