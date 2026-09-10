---
title: 'plr-sema sprint 133 plan: the move_* family (increment 8) -- inherited-delegate resolution, the resource-pickup typestate, and closing increment 7''s own _check_args divergence'
description: 'Sprint plan for 260909_sema-move-family: Band A the increment 8 spec drafted and taken through TWO adversarial rounds to spec_version 3 / reviewed-round-2, the second round ruling the cycle converging and warranting no third (DONE 260910); Band B T53 M-SURF the backend-surface ATTACHMENT fix, the one UNCONDITIONAL row, which alone closes 148 operations and increment 7''s :375/:383 divergence; Band C T50 M-INH (D9) + T51 R-ARM and the predicate-position clause (D7 unit 11); Band D T52 the _resource_pickup typestate (D7 unit 12); Band E T54 M3''s closure-wide argument map plus BOTH surface halves (D8); Band F T55 the oracle/mutants/gate and T56 the lint close. Five user decision hooks D7-D11 with the rounds'' recommendations (YES/YES/YES/NO/NO). No joined SAFE is claimed on any move_* operation and the obstruction is named in advance; the gate is a residual of exactly seven sites, down from thirteen.'
status: planning
task_id: 260909_sema-move-family
date: '260910'
sprint: '133'
backlog_ids: '5059,5060,5061,5062,5063,5064'
---
# plr-sema sprint 133 plan: the move_* family (increment 8)

> Task id `260909_sema-move-family`. Spine: `.praxia/docs/specs/260909_plr-sema-move-family-increment.md`
> (increment 8, §17, **spec_version 3, `reviewed-round-2`**, 2,693 lines), authored in band A from
> sprint 130's final ledger (`outputs/plr-sema/unknown_ledger_260909_final.json`) and increment 7 §16.14's
> explicitly deferred row (e). Planned at HEAD `0a9190b7` on `plr-sema-inc8-move-family`, PLR pin
> `dd79c4c89`, sprint 130 `260909_sema-observation` closed (`52178d80`, PR #157).

## 0. Why this increment

Sprint 130 reached the headline — 216 of 223 `pick_up_tips` operations reach `scope_verdict == SAFE`
with `unsound == 0` and `unsound_scoped == 0`. It also left increment 7 §16.14's row (e) open by name:
the **`move_*` family, 93 operations, 17.1% of the frozen benchmark**, blocked by `_state_updated` — an
inherited two-line no-op callback loop on `Resource` — and affecting exactly `move_lid` / `move_plate` /
`move_resource` at 31 operations each.

**Measured at the pin, not assumed** (`unknown_ledger_260909_final.json`, orchestrator-verified this
pass): the `unresolved_delegate` cluster is **186 findings over 93 operations** on the single
`condition` value `_state_updated`, `plr_site` `<none>`, `per_method` 31/31/31 — so 186 = 93 × 2
exactly. Its **`n_ops_sole_blocker` is 0**: `unresolved_delegate` is never the sole blocker on any of
the 93, which is why this increment claims **no joined `SAFE` on any `move_*` operation** and names the
obstruction in advance rather than discovering it at a gate. Each of the three methods carries the
identical residual reason set `{guard_env_dependent, guard_predicate_unparsed, unresolved_delegate}`
on all 31 of its operations, and `n_scope_verdict_safe` is 0 for all three.

**The central discovery of the two adversarial rounds** is not about the move family at all. It is that
increment 7's own **`:375`/`:383` divergence — 321 operations, the largest cluster pair in the
instrument — has a single shared cause. `derive/__main__.py` attaches the derived backend surface to a
contract entry only when that entry's own guards' `predicate` JSON carries a `self.backend.<method>(...)`
`EnvRef` CALL. T49 extended the surface **selection** half to scan `caller_args` and did not extend the
**attachment** half in the same commit. Verified against the shipped artifact this pass: exactly **five**
entries carry an attached `backend_surface`, and all five are tip-path (`consolidate_tip_inventory`,
`move_tips`, `pick_up_tips`, `probe_tip_presence_via_pickup`, `use_tips`) — **no move method among
them**. That is M-SURF, T53: ~35 lines, no registry cost, no decision hook, and it alone clears
`:375`/`:383` on the 148 `aspirate`/`dispense`/`drop_tips` operations that spec_version 1 could not
explain.

## 1. Composition

| Band | Item | What | Model | Depends on |
|---|---|---|---|---|
| A — spec | **#5059** (DONE) | Draft spec_version 1 (`9836a5ee`); round 1 (challenger C1–C21 `not_ready`, defender 11 conceded / 9 partial / 1 rebutted, `dbfa39ca`); spec_version 2 (`4dfade54`); round 2 (challenger R2-C1..R2-C14 `not_ready` `2d9eb2ab`, defender `needs_revision` `2ce81bbe`, which ruled the cycle CONVERGING and warranted **no third round**); spec_version 3 + the targeted verification the defender prescribed in its place (`0a9190b7`). | Opus | — |
| B — the unconditional row | **#5060** | **T53 M-SURF, the backend-surface ATTACHMENT fix, and only the attachment fix** (~35). Publishes `n_entries_with_backend_surface` before/after, R-CONST's `n_resolved_by_rule` before/after, and the four row-level counters asserted **UNCHANGED at 160/71/89** with `drop_resource` **still absent**. Satisfies **AC-17.4**. | Haiku | #5059 |
| C — foundations | **#5061** | **T53 must land first.** T50 M-INH — inherited self-call resolution with a fourth fail-closed condition and a specified base-name extractor (~230). **Stop for D9 before T50.** T51 R-ARM's fourth `EnvRef` path shape + the complete-`Seq` truthiness clause (~140). **Stop for D7 unit 11 before T51.** T51 is independent of every other row. T50 must publish its measured selection before T52 and before T54. | Sonnet | #5059, D9, D7 |
| D — typestate | **#5062** | T52 the `_resource_pickup` typestate (~330). **Stop for D7 unit 12 before T52.** Satisfies **AC-17.3**. | Sonnet | #5061, D7 |
| E — M3 + selection | **#5063** | T54 — three pieces: the surface SELECTION extension, the attachment filter's `caller_args_sites` scan, and M3's closure-wide argument map with the conjunctive fold (~340). **Stop for D8 before T54.** Satisfies **AC-17.5**. | Sonnet | #5060, #5061, D8 |
| F — measurement + gate | **#5064** | T55 tier-1 re-run, the p3a mutant, the after-ledger, the gate both ways, and blocks (10)/(11) so increment 9 argues D11 from data (~280); T56 the lint close and INDEX regen (~4 — the spec-lint registration already landed in band A). Satisfies **AC-17.6**, **AC-17.7**, **AC-17.8**. | Sonnet / Haiku | #5060, #5061, #5062, #5063 |

**Order, forced by §17.11 and by the one shared worktree checkout:** T53 → T50 → T51 → T52 → T54 → T55
→ T56, strictly serially. The ordering constraints are real, not conventional: **T50 must precede T52**
(§17.4.3's third widening condition is defined over the unresolved-delegate population, and a typestate
computed against a stale one is a state nobody has inspected); **T50 must precede T54** (§17.5.1's first
site-set condition makes M3's fold decline whenever any record in the closure carries an unresolved
self-call, and every move-family closure carries two today, so M3 lands dead on this family unless M-INH
went first); **T53 must precede T54** (M-SURF alone moves 148 operations through the shipped rules, and
landing M3 first would make that contribution unattributable). Round 2 did **not** reverse this: the 148
reach `_check_args` at depth 1 with `caller_args` already populated, so their rows already exist.

Unconditional total ~35 LOC (T53) plus ~284 (T55/T56, which run whatever was taken). D9 adds ~230, D7
adds ~470 across its two units, D8 adds ~340. Full-take total **~1,359 LOC**.

## 2. The gate (spec §17.8.2, stated both ways)

- **Full take (D7, D8, D9 all YES):** GO iff **every one of the 93 `move_*` operations' non-excluded
  residual is EXACTLY the seven sites `{:383, :2204, :2211, :2226, :2233, :2284, :2290}`**, down from
  thirteen, AND `unresolved_delegate` is **0 benchmark-wide**, AND tier-1 `unsound` and `unsound_scoped`
  are **both 0**, AND increment 7's **216 are preserved**, AND `guard_predicate_unparsed` (495) and
  `guard_operand_unknown` (144) are **unchanged**.
- **Total decline (D7, D8, D9 all NO):** T53 still lands, so the increment is measured against
  `:375`/`:383` clearing on the **148** `aspirate`/`dispense`/`drop_tips` operations through the shipped
  site rules, with increment 7's `:375`/`:383` divergence **closed by diagnosis** and the four surface
  row-level counters unchanged at 160/71/89. `unresolved_delegate` stays 186/93; the move family's
  residual stays at thirteen. **This is a real result, not a fallback** — it is why M-SURF was
  deliberately built to need no hook.
- **Partial takes are priced individually** in §17.8.2's table. Two cascades matter: declining **D9**
  makes M3 decline on the whole family (residual **nine**, not eight), and declining **D8** leaves
  `:375` at ½ for **two** independent reasons — no row and no argument map — so a partial
  implementation of D8 buys nothing.
- Either way: **no joined `SAFE` is claimed on any `move_*` operation**, every reason count is
  published, and the per-site prediction table is reproduced cell by cell.

## 3. Decision hooks — five (spec §17.13)

| id | decision | what declining costs | recommendation after two rounds |
|---|---|---|---|
| **D7** | HM-25 `declared` **10 → 12** — **two** per-row ceiling units: (11) §17.1.2's amended predicate-position clause, (12) §17.4's singleton-anchor and effect shapes. `live_rows()` and `BUDGET_CAP` both **unchanged at 25** — no cap conversation | both units declined: `:2055`, `:2070`, `:2120`, `:2147` stay ½ on 93, residual **eleven**, p3a withdrawn with its criterion, ~440 LOC leaves | **YES.** Unit 12 is increment 1 P2's own class, already the row's first entry. Unit 11 is spec_version 1's own error corrected against itself — round 1 showed D4's probe imports `_resolve_env_ref` while the clause lands in `evaluate_predicate`. Asking for two is the honest number and it moves the ask **up** |
| **D8** | **M3** — the admitted call-site set collected across the **whole closure**, folded conjunctively, with M1's `depth == 1` lifted for call-site-constant arguments only — **plus both surface halves** (round 2's R2-C1) | `:375` stays ½ on the 80 `transfer`/`discard_tips`/`stamp` and the 93 `move_*`; residual **eight**; and it stays ½ for two independent reasons, so a partial take buys nothing. **M-SURF still lands** | **YES.** The lift is genuinely **narrower** than the depth-1 map D1 already permits (a call-site constant resolves against no namespace). The closure-wide fold is **strictly more conservative** than the single-site rule it replaces — a superset of the executed sites can only decline more often — and it is the only version of M3 both sound and uniform across all 93 |
| **D9** | **M-INH** — resolve inherited `self.<name>()` calls across the whole PLR surface, with virtual dispatch inside inherited bodies | `unresolved_delegate` stays 186/93; §17.4.3 condition (2) unreachable; **and §17.5.1's site-set condition makes M3 decline on the whole family, so `:375` joins the residual too — nine entries.** This is the hook whose decline cascades | **YES.** Derived from a whole-tree index with no PLR name typed, closing a two-line function that cannot raise. **A decision and not a sprint choice** because of the blast radius: it perturbs per-guard DEPTH benchmark-wide with no guard body changing (round 1's C11), so the depth multiset is published before and after and §17.2's doubling bound stops the row rather than landing a closure nobody sized |
| **D10** | The **residual-`**kwargs` Term** — D5a's production (5), a second discharge route for the shipped `:383` site rule | nothing on this benchmark; `:383` stays ½ on the 93 and on `stamp`'s 27 in **both** branches | **NO, this increment** — a reversal of spec_version 1, and derived rather than tactical. §17.5.2 shows the conjunctive fold declines at `pick_up_resource`'s call site whatever the Term does, so production (5) alone buys **zero operations**: the exact trade §9.4 forbids |
| **D11** | **E-TYPE's negative direction** — an exactness fact on `ir.Resource` so `isinstance` can decide `F` and E-SCOPE can clear the six `drop_resource` branch-arm sites | the residual stays at seven and `move_*` cannot reach `scope_verdict == SAFE` in increment 8 or 9 without it | **NO, this increment.** Round 1's C12 falsified the original argument (every mechanism here is live inside `_scope_entry_value`); the surviving one is that the input is a derived type claim over a corpus nothing publishes, one wrong claim is six wrong answers, and it is not a risk to take alongside four other new mechanisms. **T55 publishes blocks (10) and (11) so increment 9 argues it from data**, where the recommendation may well be YES |

**How these are being taken, and how to reverse them.** Following sprint 130's recorded precedent —
*"D6 was taken (YES, per the round's own recommendation)"* — this sprint takes **D7 YES, D8 YES, D9 YES,
D10 NO, D11 NO**, each per the specification's own twice-adversarially-reviewed recommendation, and
records that it did so. Every one is separable and individually reversible: §17.8.2's table prices each
decline, a declined decision **withdraws its acceptance criterion with its row** rather than leaving it
unsatisfied, and T53 is deliberately unconditional so that a total decline still ships a result. A user
who wants a different answer on any hook can say so and the corresponding band stands down without
disturbing the others.

Also standing: `live_rows()` stays **25** against `BUDGET_CAP` **25** — zero new rows, at full cap.
`REASON_VOCABULARY` stays **12 of 12** (no 13th proposed).

## 4. Baselines that must hold at close

| Tier | Baseline (sprint 130 close, measured this pass) | Where |
|---|---|---|
| 1 sidecar-gated replay | `rows_executed` 343, `total_operations_executed` 548, **`unsound_count` 0**, `totality_violations` 0, `check_graph_exceptions` 0, `gate.go` true with `n_operations_scope_verdict_safe` **216** | `outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json` |
| crosscheck | joined 191, agree **191**, disagree **0** | same |
| decided | `n_findings_decided` **2,817**; `n_check_args_decided` 446 (223 at `:375`, 223 at `:383`); `n_membership_decided` 331; `n_quantifier_decided_by_qmono` 223; `n_resolved_by_rule` R-HEAD 331 / R-ATTR 0 / R-CONST 223 | same |
| final ledger | 52 clusters / **3,903** findings / 544 ops, `n_ops_unknown_but_scope_verdict_safe` 216, `n_row_id_collisions` 12; by-reason `guard_env_dependent` 2,884 · `guard_predicate_unparsed` 495 · `volume_state_unknown` 194 · `unresolved_delegate` 186 · `guard_operand_unknown` 144 | `outputs/plr-sema/unknown_ledger_260909_final.json` |
| move family | `move_lid` / `move_plate` / `move_resource` each 31 ops, `n_scope_verdict_safe` **0**, residual reason set `{guard_env_dependent, guard_predicate_unparsed, unresolved_delegate}` on all 31 | same |
| 3 mutants | tip `gate_passed` true (285 corpus bases), volume true (66), predicate true (285) | `outputs/plr-sema/{tip,volume,predicate}_mutants_260909_inc7.json` |
| registry | `live_rows()`/`BUDGET_CAP` **25/25**, HM-24 3, HM-25 **10**, HM-26 1, `REASON_VOCABULARY` 12/12 | `test_hand_maintained_ratchet.py` |
| spec lint | **24 passed / 6 failed** — the 6 are pre-existing increment-1..6 citation drift, confirmed byte-identical | `plr-sema/tests/test_spec_lint.py` |

**The numbers allowed to move:** `n_findings_decided` (up, 2,817 → **3,711** on a full take),
`guard_env_dependent` (down, 2,884 → **1,990**), `unresolved_delegate` (down, 186 → **0** under D9),
`n_surface_candidates`/`n_surface_absent_by_c15`/`n_surface_rows` (only under D8, 160/71/89 →
**172/73/99**), and HM-25 `declared` (10 → **12** under D7). Everything else in §4 must hold.
`n_findings` is published against **2,823**, which closes against the measured baseline:
2,817 + 894 = 3,711 decided, 3,903 − 894 − 186 = 2,823 unknown, and 3,711 + 2,823 = 6,534 = 6,720 − 186.

The failure this increment makes possible for the first time is a **`scope_verdict == SAFE` reached
through a stale unresolved-delegate population**, and T50's published depth multiset plus §17.2's
doubling bound are what catch it.

## 5. Explicitly out (spec §17.12)

D10's residual-`**kwargs` Term and D11's E-TYPE negative direction (both priced as increment 9's, both
with their reasons recorded). The `:2055` mutator (non-constructible on the backend-class ground alone).
Precision targets (increment 7 row (f)). Any joined `SAFE` on a `move_*` operation. `strictness` as an
observation member (refused by name — it decides nothing). Coxswain and REPL tracks untouched.

## 6. Dispatch conventions (unchanged from sprint 130)

Fixer briefs mandate `uv run python`, **per-file pytest only** (the jax-mem-guard blocks any `/tests`
path; include `test_ir.py`), path-scoped `git add`, no background Bash or monitors, foreground with
timeout, final line `COMMIT: <full sha>`, the two trailers. Full per-file set before closing a band:
`test_derive`, `test_predicate_ast`, `test_predicate`, `test_check_graph`, `test_ir`, `test_wire_fuzz`,
`test_verdict`, `test_hand_maintained_ratchet`, `test_cache`, `test_tip_typestate`, `test_oracle_replay`,
`test_unknown_ledger`, `test_t30_measure`, `test_predicate_mutants`, `test_spec_lint`. Spec author /
challenger / defender have **no Bash and no Write** — the orchestrator persists their reports and runs
the lints. Measurement rows go to Sonnet; demand per-site root causes. Never stage another session's
dirty entries; `outputs/plr-sema` is gitignored (force-add reports); `git push` needs the sandbox off.
All work happens in worktree `wt-20260909-172820` on `plr-sema-inc8-move-family` — Agent dispatch from
the primary checkout is blocked by a discipline hook.

## 7. Estimate

B ~35 LOC (one Haiku row, minutes — but its published counters are what confirm or falsify §17.1.4);
C ~370 (one session, after D9 and D7); D ~330 (one session, after T50 publishes); E ~340 (one session,
the largest single row and the one that relaxes two soundness fences); F ~284 (one session; T55 is the
long pole — tier 1 plus every non-regression tier plus the ledger). Three to four sessions on a full
take, strictly serial. Band A took one session across two adversarial rounds.

## 8. Specification log (260909–260910, orchestrator)

**Landed on `plr-sema-inc8-move-family`:** draft `9836a5ee` (spec_version 1); round-1 reports
`dbfa39ca`; spec_version 2 `4dfade54`; INDEX regen `04c4a834`; round-2 challenger `2d9eb2ab`; round-2
defender `2ce81bbe`; spec_version 3 + targeted verification `0a9190b7`.

**What the second round bought, and why there is no third.** Round 1's two routes were *mechanism*
failures requiring re-derivation from scratch; round 2's single route (R2-C1) was a *plumbing* failure
of an already-correct mechanism — two scan sites must read a new field beside `caller_args` — with the
favourable outcome provable at the pin before any run. The round-2 defender ruled the cycle
**converging**, warranted **no third adversarial round**, and prescribed in its place a targeted
verification of its ten remediation items against the cited lines. That verification found **two
defects both adversaries had missed**:

1. The shipped `rows` object carries **ten** `*.pick_up_resource` rows, not the nine that the round-2
   challenger, the round-2 defender and spec_version 3's first pass all asserted. Root cause: all three
   passes used a **digit-free class-segment regex**, which silently drops
   `OpentronsOT2Backend.pick_up_resource`. Nine of the ten are backend classes; the tenth is
   `LiquidHandler.pick_up_resource` itself. *A count taken from a regex is a count of what the regex
   admits* — recorded in §17.15 so it is not rediscovered.
2. The blast radius was **approximate where it could be exact**. `def drop_resource` has exactly 12
   definitions at the pin with exactly 2 `@abstractmethod`, structurally identical to
   `pick_up_resource`'s 12/2 which ships 10 rows — so AC-17.5 now asserts `n_surface_candidates` **172**
   / `n_surface_absent_by_c15` **73** / `n_surface_rows` **99** *by value*, with 172 − 73 = 99
   reproducing the by-construction invariant at `receiver_state.py:1508-1512`. This is now the cheapest
   falsifier of §17.1.4 and it fires at T54 rather than at T55.

A third correction scoped an overclaim: the ten new `drop_resource` rows are **heterogeneous** (the arms
classes take `position`/`access`; `SerializingBackend` carries `**backend_kwargs`), so the site rule's
`F` is asserted for the **resolved `m`** — `LiquidHandlerChatterboxBackend` — and no other.

**Orchestrator-verified facts** (source and instrument, not report): the selection half scans exactly
`predicate` and `caller_args` (`receiver_state.py:1488-1500`); the attachment filter `continue`s on a
null `predicate` and never reads `caller_args` at all (`derive/__main__.py:343-345`), so R2-C1 is
**broader than the challenger filed**; `chatterbox.py:229-230`'s `drop_resource` is undecorated and
singly-defined, so `321 → 0` is **kept** rather than retreating to the challenger's residual of eight;
`_measure_hm25` is `len(shape_matchers)` (7) + `len(productions)` (3) = 10, so D7's 12 requires
`shape_matchers` 7→9 with `productions` **pinned at 3**; `_resource_pickup` is a `@property` pair at
`:179`/`:184` and `receiver_state.py:1435` explicitly documents that clause 3 catches such a pair, which
is why §17.4.2 needs the exemption; `no_contract_derived` is **absent from the by-reason map entirely**
(0 benchmark-wide); and the `unresolved_delegate` cluster's **`n_ops_sole_blocker` is 0**.

**Lessons.** (1) A shipped artifact the frontmatter declares "NOT read this pass" is exactly where the
next blocker hides — round 2's blocker was found by reading `derived_contracts.json`, and the §17.13 Q9
overstatement ("DISPOSED IN FULL") is what licensed declining to read it. (2) A challenger and a
defender agreeing on a number is **not** verification; both inherited "nine" from the same bad regex.
Parse the artifact. (3) An absence claim naturally trips the citation lint's nearest-backtick anchor
rule — re-anchor on an identifier that IS in range rather than weakening the claim.

## 9. Outcome

*To be written at close.*
