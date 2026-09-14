---
title: 'plr-sema sprint 130 plan: the observation record (increment 7, tier (ii)) and the first scoped joined verdict, gated on one registry decision'
description: 'Sprint plan for 260909_sema-observation: Band A the increment 7 spec (tier (ii) observation record, derived backend surface, delegate->caller argument map, scope_verdict, site-keyed fence) drafted and taken through adversarial round 1 to reviewed-round-1 (DONE 260909); Band B foundations T40-T42; Band C E-ENV resolution + scope_verdict T43-T44 (needs D4); Band D fence + oracle + gate T45-T47; Band E CONDITIONAL on D6 -- the :321 and _check_args site rules that are the whole remaining distance to the headline. Six user decision hooks D1-D6 with the round''s recommendations; the headline (first joined SAFE within scope on a real op) is reachable this sprint iff D6 is taken.'
status: active
task_id: 260909_sema-observation
date: '260909'
sprint: '130'
backlog_ids: '5022,5023,5024,5025,5026'
---
# plr-sema sprint 130 plan: the observation record (increment 7, tier (ii)) and the first scoped joined verdict, gated on one registry decision

> Task id `260909_sema-observation`. Spine: `.praxia/docs/specs/260909_plr-sema-observation-increment.md`
> (increment 7, §16, **spec_version 2, `reviewed-round-1`**), authored in band A from sprint 127's
> after-ledger (`outputs/plr-sema/unknown_ledger_260909_after.json`) and increment 6 §15.5/§15.6/§15.13.
> Planned at HEAD `d7d8e348` on `coxswain-p2-pipeline`, PLR pin `dd79c4c89`, sprint 127
> `260904_sema-predicates` closed and pushed (`88141a49`).

## 0. Why this increment

Sprint 127 closed with per-finding `SAFE`/`WILL_FAIL` on real operations and `unknown_rate` still 1.0
on all 544 executed ops: every liquid-handling operation carries tier-(ii) guards that read state
outside the extracted graph, and the user substituted the headline on 260907 — *the first joined `SAFE`
on a real program is increment 7's*. The after-ledger fixes the target: `pick_up_tips` (223 ops) has
a residual of exactly six `guard_env_dependent` sites in `liquid_handler.py` — `:375`/`:383`
(`_check_args`, backend signature), `:409` (head channel membership), `:321` (deck membership), `:514`
(the backend's `can_pick_up_tip` body), `:576` (tier (iii), the backend's own re-raise).

**What the round established about the six** (spec §16.1, §16.17): `:409` and `:514` flip under an
observation record plus a derived backend surface plus the delegate→caller argument map (D4 spends one
HM-25 unit); `:576` is excluded by scope and the joined verdict within that scope is a second additive
report field, `scope_verdict`; **`:375`, `:383` and `:321` are decidable in the `SAFE` direction only
by site rules keyed on a named PLR function** — a *new kind* of hand-maintained fact, one registry row
against a full `BUDGET_CAP` of 24. That is decision **D6**, and neither site rule alone clears the
operation (D-G2). So the headline is reachable this sprint iff D6 is taken.

## 1. Composition

| Band | Item | What | Model | Depends on |
|---|---|---|---|---|
| A — spec | **#5022** (DONE) | Draft (Opus specification-specialist), round 1 (challenger C1–C26 `6729f9bc`, defender `929ad95c`: 13 conceded / 13 partial, six defender gaps), remediation to spec_version 2 (`d7d8e348`), lint registration (`92bc2cc9`, 28 passed). | Opus | — |
| B — foundations | **#5023** | T40 observation record + cache-key partition (~180); T41 derived backend surface (~165); T42 delegate→caller argument map + the D1 depth-1 lift if approved (~170). Each publishes its measured selection before T43 resolves anything. | Sonnet | #5022 |
| C — resolution | **#5024** | T43 E-ENV rules R-HEAD/R-ATTR/R-CONST, the membership deciding case reopened, Q-MONO as an amendment of increment 6 G8(1), **the D4 spend** (~150); T44 `scope_verdict` (~90). **Stop for D4 before T43.** | Sonnet | #5023, D4 |
| D — fence + gate | **#5025** | T45 whole-frame-list fence + `unsound_scoped` (~130); T46 tier-1 re-run, p2a mutants, after-ledger with `scope_verdict`, the gate both ways (~250); T47 INDEX regen at close (lint registration already landed). | Sonnet / Haiku | #5024 |
| E — conditional | **#5026** | **CONDITIONAL on D6.** T48 the `:321` site rule + A-DECK-OBJECT (~120); T49 the two `_check_args` site rules, D5b (~130). Do not start without the user's answer. | Sonnet | #5024, D6 |

Order: B → C → D serially; E after C, in parallel with D, only if D6 is taken. Unconditional total
~1,151 LOC; D6 adds ~250 (spec §16.13).

## 2. The gate (spec §16.10.2, stated both ways)

- **D6 taken:** GO iff ≥ 1 executed real operation reaches `scope_verdict == SAFE` with tier-1
  `unsound == 0` under the unmodified predicate AND `unsound_scoped == 0` under §16.7's narrowing.
  Prediction: `pick_up_tips` on **≥ 167 and ≤ 223** ops (bounded by `TipTracker.get_tip`'s 167 decided);
  `n_findings_decided` 223-certain **3,385**.
- **D6 declined:** the increment is measured against a conjunction it can genuinely fail —
  `n_findings_decided ≥ 2,009` (2,170 published as target) AND `unsound == unsound_scoped == 0` AND
  `scope_verdict` computed and published per operation with the `:375`/`:383`/`:321` residual
  reproduced exactly on all 223 `pick_up_tips` ops. `scope_verdict` stays `UNKNOWN` on all 544.
- Either way every reason count is published, the per-site prediction table (§16.10.3) is reproduced
  cell by cell, and the falsification map (§16.10.4) names which production flips which site.

## 3. Decision hooks — six, each stops for the user before it is spent (spec §16.15)

| id | decision | recommendation after round 1 |
|---|---|---|
| **D1** | Lift `E-UNCOND(4)`'s depth ≥ 1 `WILL_FAIL` forbiddance at depth 1 under three preconditions (T42, ~50 LOC withdrawn on decline) | **YES** — C19's missing-precondition attack rebutted on the evidence (`scope_trail` records `for` headers, unsatisfiable under ways (1)–(3)) |
| **D2** | A-DECK-OBJECT as a fifth named assumption + the deck-membership observation, so `:321` decides | **YES, repriced, CONDITIONAL on D6** — R-DECK as drafted could not fire (C3); the only repair is a site rule of D5b's class; exposure bounded by argument on the corpus, not by adversarial measurement (C18) |
| **D3** | *(non-decision)* the derived backend surface hand-types nothing | **survived** — harness-side reads ride increment 5's `volume_tracking_observed` precedent; the undefined selection clause was deleted for one closed rule (C16) |
| **D4** | HM-25 `declared` 9 → 10 for the `EnvRef` path-shape table (`live_rows`/`BUDGET_CAP` unchanged at 24) | **YES** — the unit buys the pattern regardless of instance count; R-ATTR keep-or-drop is a sub-note |
| **D5** | Model `_check_args`: D5a general (~350, increment 8) / D5b two `SAFE`-direction site rules (~130 + the D6 row) / D5c neither | **D5b if D6 is taken** — C1's arithmetic holds at the pin; one-directional by construction (D-G6: both guards carry `reachability_clear` false) |
| **D6** | Accept site-keyed semantic models of named PLR function bodies as a class of hand-maintained fact — **one new registry row, cap 24 → 25** (a §9.4 cap conversation) | **YES** — the single fact D2's repair and D5b both need; the loud half is a published count, not an import-the-symbol measure; C15's absence rule is its soundness precondition; the only route to the headline this sprint |

Also standing: `REASON_VOCABULARY` stays 12/12 (no 13th proposed); #4923 / #4924 remain decision
hooks only; the E-UNCOND(5) refinement of increment 6 (§15.16.3 R1) has now had its adversarial
review (spec §16.15 Q6: R1-C1..C5, no counterexample at the pin; C19's in-loop attack rebutted).

## 4. Baselines that must hold at close

| Tier | Baseline (sprint 127 close) | Where |
|---|---|---|
| 1 sidecar-gated replay | 343/548, crosscheck 191/191, **0 unsound**, `n_findings_decided` 1,563, `guard_predicate_unparsed` 495, `guard_operand_unknown` 144 | `outputs/plr-sema/oracle_replay_260909_inc6.json` |
| after-ledger | 53 clusters / 5,157 findings / 544 ops, `consistency.ok`, `{guard_env_dependent}` on 223 | `outputs/plr-sema/unknown_ledger_260909_after.json` |
| 2b executed regions | 16 fixtures, 0/7/3 | `outputs/plr-sema/tier2b_260909_inc6.json` |
| 3 mutants | m1 199/199, m2 289/289, v1 67/67, p1 (a) 288/288 (b) 16/16 (c) 0, 0 unsound | `outputs/plr-sema/{tip,volume,predicate}_mutants_260909_inc6.json` |
| registry | rows 24/24, HM-24 3, HM-25 9, `REASON_VOCABULARY` 12/12 | `test_hand_maintained_ratchet.py` |
| spec lint | 28 passed, seven specs 0 failing citations | `plr-sema/tests/test_spec_lint.py` |

The numbers allowed to move: `n_findings_decided` (up), `guard_env_dependent` (down), `unknown_rate`
(down, only under D6) — with `unsound` and `unsound_scoped` both staying 0. A `scope_verdict == SAFE`
on an operation whose raise came from a PLR precondition frame is the failure this increment makes
possible for the first time; the whole-frame-list fence (T45) is what catches it.

## 5. Explicitly out (spec §16.14)

γ (the bounded literal-display loop), the `pred`-aware `BRANCH`, the general `Identity(Term, Term)` and
the lid topology, tuple-display comparison, arithmetic `BinOp`, the loop-append idiom, the
well-seeding observation for `volume_state_unknown`, §8's bridge replacement, deferred row (e)'s move
family, precision targets (row (f)), D5a's general `_check_args` model (increment 8 if D6 is declined),
`strictness` as an observation member (refused by name: it decides nothing, §16.1.1). Coxswain and
REPL tracks untouched.

## 6. Dispatch conventions (unchanged from sprint 127)

Fixer briefs mandate `uv run python`, per-file pytest only (the jax-mem-guard blocks any `/tests`
path; include `test_ir.py` — its golden moved in sprint 127), path-scoped `git add`, no background
Bash or monitors, foreground with timeout, final line `COMMIT: <full sha>`, the two trailers. Full
per-file set before closing a band: `test_derive`, `test_predicate_ast`, `test_predicate`,
`test_check_graph`, `test_ir`, `test_wire_fuzz`, `test_verdict`, `test_hand_maintained_ratchet`,
`test_cache`, `test_tip_typestate`, `test_oracle_replay`, `test_unknown_ledger`, `test_t30_measure`,
`test_predicate_mutants`, `test_spec_lint`. Spec author / challenger / defender have no Bash; the
orchestrator persists their reports and runs the lint. Measurement rows go to Sonnet; demand per-site
root causes. Never stage the other session's dirty entries; `outputs/plr-sema` is gitignored
(force-add reports); `git push` needs the sandbox off.

## 7. Estimate

B ~515 LOC (three rows, one session); C ~240 (one session, after D4); D ~380 (one session; T46 is
the long pole — tier 1 plus every non-regression tier plus the ledger); E ~250 (one session, after
D6). Two to three sessions without E, three to four with it. The round itself took one session
(draft ~30 min, challenger ~11 min, defender ~12 min, remediation ~27 min of agent time).

## 8. Specification log (260909, orchestrator)

**Landed on `coxswain-p2-pipeline`:** draft `7893168a` (spec_version 1: the author reported the
headline NOT reachable — D5 at ~350 LOC, refused); challenger `6729f9bc` (C1–C26: the `SAFE` direction
of `:375`/`:383` follows from the derived signature table; R-DECK matches a shape absent from the
contract table; the fence's innermost-frame match excuses nothing on a re-raise; the gated floor used
the uncertain half of `:409`'s reach); defender `929ad95c` (13 conceded / 13 partial / 0 rebutted;
D-G1 Q-BIND is dead machinery, D-G2 the gate needs both site rules, D-G6 the `_check_args` discharge is
one-directional; NEW D6); lint registration `92bc2cc9`; spec_version 2 `d7d8e348`.

**Orchestrator-verified facts:** the traceback frame order (ephemeral script: outermost-first, the
re-raise at index 1, the backend frame last) — C5 confirmed by measurement, not by reading.

**Lessons:** (1) a spec author pricing a *general* mechanism while the gate needs a *one-sided*
direction produced a false NO-GO; the round's first target on any future "not reachable" claim is
the direction the gate actually needs. (2) The IR's `Resource` value carries no name, which is why deck
membership is a site rule and not an `EnvRef` — recorded so it is not rediscovered. (3) Table cells
must not contain a bare `|` (`str | None` broke the crossref lint's gate-cell column once).

## 9. Outcome

*(filled at close)*
