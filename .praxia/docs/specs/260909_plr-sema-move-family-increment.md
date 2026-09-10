---
title: "plr-sema increment 8 — the move_* family: inherited-delegate resolution, the resource-pickup typestate, and closing increment 7's own `_check_args` divergence"
description: "Eighth post-corpus increment, spec_version 3 after adversarial rounds 1 AND 2. Target: increment 7 §16.14's deferred row (e), the move_* family's 93 operations, 17.1% of the frozen benchmark. Round 1 (challenger C1-C21, `not_ready`; defender 11 conceded, 9 partial, 1 rebutted) established that spec_version 1's gate was predicted to fail on all 93 operations for two independent reasons, and spec_version 2 re-derived the mechanism rather than polishing the prose. ROUND 2 (challenger R2-C1..R2-C14, `not_ready`; defender `needs_revision`, which ruled the cycle CONVERGING and warranted NO third adversarial round) re-established the same outcome on ONE route and this version repairs it: M-SURF fixed the surface ATTACHMENT half only, while row CANDIDACY runs through `collect_env_ref_method_names`, which scans `predicate` and `caller_args` and neither of which ever carries `self.backend.drop_resource` -- there is no `*.drop_resource` row in the shipped table at all (TEN `*.pick_up_resource` rows -- nine backend classes plus `LiquidHandler` itself -- and zero `*.drop_resource`). §17.1.4 now takes BOTH halves, the selection half is T54's and D8-dependent, and the `321 -> 0` prediction is KEPT rather than retreated from, because `LiquidHandlerChatterboxBackend.drop_resource(self, drop)` is undecorated and singly-defined so the row appears with `params ['drop'] ⊆ default {'drop'}` and the site rule returns F. §17.17 records all fourteen round-2 dispositions. THE CENTRAL CHANGE: increment 7's own `:375`/`:383` divergence -- 321 operations, the largest cluster pair in the instrument -- is now DIAGNOSED, from source, to a single shared cause spec_version 1 named as open. `derive/__main__.py` attaches the derived backend surface to a contract entry only when that entry's own guards' `predicate` JSON carries a `self.backend.<method>(...)` EnvRef CALL; the only guard in `LiquidHandler` with that shape is `pick_up_tips`'s `can_pick_up_tip` check, so `pick_up_tips` is the only entry point whose `_check_args` guards can read a surface row at all -- which is exactly the 223 that flipped and exactly why `:375` and `:383` carry byte-identical 321-operation populations. T49 extended the surface SELECTION half to scan `caller_args` and did not extend the ATTACHMENT half in the same commit. M-SURF is that missing half: ~30 LOC, no registry cost, no decision hook, and it alone clears `:375` and `:383` on the 148 `aspirate`/`dispense`/`drop_tips` operations that spec_version 1 could not explain. SECOND: M3's argument map is re-specified. `derive_contract` computes `compute_caller_args(entry_K, K)` with `entry_K` always the entry point and `_find_delegate_call` scanning only the entry point's own body, so lifting the depth restriction alone binds NOTHING for `move_lid`/`move_plate` (whose bodies contain no `_check_args` call) -- the defender's C2. This version takes the honest path: the admitted call-site set is collected across the WHOLE closure, in a second pass over `_walk_closure`'s already-visited node set, with the conjunctive fold ranging over every site and declining when any visited record carries an unresolved self-call. That is sound (a superset of the executed sites; conjunction over a superset is strictly more conservative), it restores uniformity across all 93, and it is priced honestly at ~300 LOC rather than the ~200 spec_version 1 claimed. THIRD: `:383` is REFUSED, and the refusal is derived rather than discovered at a gate. The move family's third `_check_args` call site sits inside `pick_up_resource` at `:2079`, reached through a `**pickup_kwargs` unpacking that M1 clause 4 refuses; the conjunctive fold therefore declines there whatever the residual-kwargs Term does, so D5a production (5) would buy ZERO operations on this family -- exactly the trade §9.4 forbids. D10 is recommended NO and T54's residual-kwargs row leaves the increment. THE RESIDUAL IS SEVEN, NOT SIX, and the gate is restated over it. FOURTH: §17.4.3's widening condition 2 -- the internal contradiction round 1 found on the pin -- is replaced by a derived handler-terminator shape test (`isinstance(handler.body[-1], ast.Raise)`); no new named assumption, and the assumption table stays at five rows. FIFTH: the typestate's route to a verdict is stated normatively for the first time: it is `tipstate.py`'s own `_null_check`/`atom_truth`/`_finding_for_atom` path with `consumed`-index replacement, NOT `_resolve_env_ref`/`_eval_is` -- which retires the fifth-EnvRef-path claim and the new-Is-rule claim entirely, and puts `p3a`'s mutable population at the full 93 because `_finding_for_atom` has no depth gate. What ships: M-INH (inherited self-call resolution, with a fourth fail-closed condition for the override case round 1 found and a specified base-name extractor); R-ARM plus the complete-`Seq` truthiness clause; the `_resource_pickup` typestate; M-SURF; M3. What is refused, named and priced: E-TYPE's negative direction (D11, NO) and the residual-`**kwargs` Term (D10, NO). Registry: `live_rows()` stays 25 against `BUDGET_CAP` 25, ZERO new rows; the one ask is D7, HM-25 `declared` 10 -> 12 (two units, not one -- the amended predicate-position clause does not ride HM-25's shipped probe, which round 1 established). REASON_VOCABULARY stays 12 of 12. GATE: GO iff every one of the 93 move_* operations' non-excluded residual is EXACTLY the seven sites `{:383, :2204, :2211, :2226, :2233, :2284, :2290}`, down from thirteen, AND `unresolved_delegate` is 0 benchmark-wide, AND tier-1 `unsound` and `unsound_scoped` are both 0, AND increment 7's 216 are preserved, AND `guard_predicate_unparsed` and `guard_operand_unknown` are unchanged. No joined SAFE is claimed on any move_* operation and the obstruction is named in advance."
status: reviewed-round-2
spec_version: 3
amends: 260901_plr-sema-pre-corpus-spec.md
task_id: 260909_sema-move-family
date: '260909'
confidence: medium
sources: "Round 1, read in FULL and dispositioned in §17.16: .praxia/docs/audits/260909_plr-sema-move-family-round1-challenger.md (C1-C21, verdict `not_ready`), .praxia/docs/audits/260909_plr-sema-move-family-round1-defender.md (11 conceded, 9 partial, 1 rebutted, plus its own 'What must change in remediation' list). Increment 7 read as the structural model and as the text this document extends: .praxia/docs/specs/260909_plr-sema-observation-increment.md (§16.1 144-453; §16.2 456-555; §16.3's surface; §16.5's E-ENV rules and §16.5.6's lane-asymmetry disclosure 1127-1140; §16.9's registry arithmetic and D4; §16.10; §16.14 1977-2039; §16.15 2042-2181; §16.17's round-1 disposition table 2205-2264). Increment 1 read as the typestate precedent §17.4 is built on: .praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md (§10.2.2 203-268, §10.2.4 293-334, §10.3 505-616, §10.4 617-649, §10.5 650-703, §10.6.3's named assumptions 744-769, §10.8 989-1136). The instrument: outputs/plr-sema/unknown_ledger_260909_final.json:2-19 (header, git_head 52178d80), :29-38 (totals), :42-58 and :88-104 (the `:375`/`:383` clusters at 321 each), :372-382, :412-422, :452-462, :492-502, :532-542, :572-582, :612-622, :652-662, :692-702 (the nine move-family `guard_env_dependent` clusters at 93), :732-742 and :772-782 (the two `guard_predicate_unparsed` move clusters), :812-822 (the `unresolved_delegate` cluster), :2113-2137 (the scope-verdict histogram), :2172-2185 (`n_row_id_collisions` 12 and the `collision_ops` block §17.0.1's per-operation list is read from -- named as such at round 1's C19), :2174-2264 (one move_resource operation's complete finding list); outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json:79-90, :241-261 (the three per-method residual site sets, identical), :263-265 (gate.go true). PLR at submodule pin dd79c4c89, every line below re-read THIS pass: external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:148-176, :178-185, :187-212, :214-237, :323-329, :346-389, :506-512, :541-546, :687-692, :1037-1042, :1238-1243, :1481-1483, :1559-1561, :1745-1747, :1895-1897, :2038-2094, :2096-2130, :2132-2148, :2200-2295, :2301-2377, :2379-2437, :2439-2505; external/pylabrobot/pylabrobot/resources/resource.py:838-849, :924-934; external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:63, :93, :123-128, :162-167, :201-209, :216-221, :223-231. Analyzer source, every citation verified against the file this pass: scripts/survey_plr_preconditions.py:111-146, :149-151, :259-300, :313-359; plr-sema/src/plr_sema/derive/__init__.py:397-421, :424-459, :610-651, :652-687; plr-sema/src/plr_sema/derive/__main__.py:205-217, :310-325, :326-356; plr-sema/src/plr_sema/derive/bindings.py:862-886, :889-911, :914-928, :931-997, :694-700, :782-790, :1068-1075; plr-sema/src/plr_sema/derive/receiver_state.py:1241-1268, :1284-1293, :1424-1454, :1457-1501, :1504-1563; plr-sema/src/plr_sema/check/predicate.py:309-356, :541-566, :575-594, :817-822, :900-945, :991-1001, :1011-1025, :1040-1044, :1047-1057, :1060-1113, :1121-1125, :1190-1208, :1211-1231, :1234-1249, :1252-1288, :1291-1326, :1333-1337, :1340-1352, :1376-1464; plr-sema/src/plr_sema/check/tipstate.py:128-190, :366-401, :404-439, :442-452, :455-472, :490-518, :521-543; plr-sema/src/plr_sema/check/ir.py:178-191, :385-391, :577-590, :592-601, :793-806; plr-sema/src/plr_sema/check/__init__.py:227-235, :925-959; plr-sema/src/plr_sema/verdict.py:140-199, :313-323; plr-sema/src/plr_sema/_hand_maintained.py:49, :306-434, :437-454, :1000-1054, :1152-1156. Lint, read in full so every citation and task row here is written against the checker: plr-sema/scripts/check_spec_citations.py:1-248, plr-sema/scripts/check_spec_crossrefs.py:40-204, plr-sema/tests/test_spec_lint.py:18-53 (this file is ALREADY registered as SPEC_INCREMENT_8, which is why T56 shrinks). READ AT spec_version 3 and no longer cited by symbol alone -- round 2 established that this artifact is load-bearing for §17.1.4's repair and that declining it is what hid the surface-selection half: plr-sema/data/derived_contracts.json:2-6 (the four `backend_surface` counters), the TEN `*.pick_up_resource` rows and the ZERO `*.drop_resource` rows in the top-level `rows` block, and the five entries carrying an attached `backend_surface` (:103527, :109798, :111527, :113039, :117032); plr-sema/eval/predicate_mutants.py:89, :106-142, :164-207; plr-sema/eval/tip_mutants.py:151-167. NOT read this pass and therefore cited BY SYMBOL rather than by line: plr-sema/eval/unknown_ledger.py, plr-sema/eval/oracle_replay.py, plr-sema/eval/region_oracle.py, plr-sema/eval/t30_measure.py, plr-sema/src/plr_sema/derive/predicate_ast.py."
---

# Increment 8: the move_* family

> **This document amends `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` by reference** and
> adds §17 to that document's numbering, exactly as increment 7 adds §16. It takes the single row
> increment 7's §16.14 named as out of scope by construction — *"deferred row (e), the `move_*`
> family's `unresolved_delegate` gap … 93 operations, 17% of the benchmark, outside every mechanism
> here"* (`.praxia/docs/specs/260909_plr-sema-observation-increment.md:2025-2027`) — and it takes one
> row increment 7 did not know it was leaving: its own `:375`/`:383` prediction, which the final ledger
> falsifies on 321 operations and which **this version diagnoses to a single named cause** (§17.1.4).
>
> **This is `spec_version 3`, after adversarial rounds 1 AND 2.** §17.16 records what each of round 1's
> twenty-one objections did to the text; §17.17 records what each of round 2's fourteen did. Round 1's
> central finding — that spec_version 1's gate was predicted to fail on **all 93** operations — was
> correct, was independently reconfirmed by the defender, and is the reason four sections were
> re-derived rather than edited at spec_version 2. **Round 2 re-established that same outcome on ONE
> route**, R2-C1: spec_version 2's M-SURF repaired the surface **attachment** half and left the surface
> **selection** half unrepaired, so no `drop_resource` row exists to be looked up and `:375` would have
> stayed ½ on all 93 with every hook taken. §17.1.4 now takes both halves. Round 2's defender ruled the
> cycle **converging** — round 1's routes were mechanism failures, round 2's is a plumbing failure of an
> already-correct mechanism, with the favourable outcome provable at the pin before any run — and
> ruled that **no third adversarial round is warranted**; the next gate is a targeted verification of
> §17.17's rows against their cited lines.
>
> **What this increment ships.** Inherited self-call resolution (**M-INH**), which removes an entire
> `REASON_VOCABULARY` member's population from the benchmark and costs no registry row; a fourth
> `EnvRef` path shape (**R-ARM**) and the one evaluator clause it needs; the `_resource_pickup`
> **typestate**, derived by shape and ordered within one operation; the **backend-surface fix in BOTH
> its halves** — the attachment filter (**M-SURF**, T53, no hook) and the row-selection extension
> (T54, behind D8) — which together are what actually close increment 7's `:375`/`:383` divergence;
> and the **constant-argument map at any depth over the whole closure** (**M3**) with a per-call-site
> conjunctive fold.
>
> **THE HEADLINE IS NOT A JOINED `SAFE`, AND THIS DOCUMENT SAYS SO BEFORE ITS GATE RATHER THAN AT IT.**
> `move_*` cannot reach `scope_verdict == SAFE` in increment 8, and the obstruction is named, sized and
> site-identified in advance: **seven** sites remain, six of them behind E-TYPE's **negative** direction,
> which `_eval_is_instance` cannot express by construction
> (`plr-sema/src/plr_sema/check/predicate.py:575-594`), and the seventh — `:383` — behind a
> `**`-unpacking hop M1 clause 4 refuses (`plr-sema/src/plr_sema/derive/bindings.py:966-975`). Both are
> refused here and priced as increment 9's. **The gate is therefore a structural claim over the residual
> set, not a verdict** — §17.8.2 states it both ways and lists the seven distinct ways it can fail.
>
> **Registry arithmetic, with the one spend it proposes and never takes.** `REASON_VOCABULARY` stays at
> **12 of 12** (§17.6). `live_rows()` stays **25** against `BUDGET_CAP = 25`
> (`plr-sema/src/plr_sema/_hand_maintained.py:49`): **zero new rows, no cap conversation.** The only ask
> is **D7** — HM-25 `declared` **10 → 12** — and §17.7 argues why it is two units rather than the one
> spec_version 1 asked for, which is a round-1 concession running against this document's convenience.

---

## 17.0 The instrument and the claim

**The instrument is a fresh `unknown_ledger.py` run at increment 7's final HEAD**,
`outputs/plr-sema/unknown_ledger_260909_final.json`, against the frozen benchmark
`tier1-sidecar-gated-dd79c4c89` at PLR pin `dd79c4c89` and analyzer HEAD `52178d80`
(`outputs/plr-sema/unknown_ledger_260909_final.json:2-19`). Its numbers, verbatim: **544 executed
operations**, **3,903 findings**, **52 clusters**
(`outputs/plr-sema/unknown_ledger_260909_final.json:29-38`). By reason: `guard_env_dependent` 2,884,
`guard_predicate_unparsed` 495, `volume_state_unknown` 194, `unresolved_delegate` 186,
`guard_operand_unknown` 144. The companion replay reports `gate.go` **true** with **216** operations
at `scope_verdict == SAFE` (`outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json:263-265`),
which is increment 7's headline holding at final HEAD and is the number §17.8.2 forbids this increment
to regress.

### 17.0.1 The residual is not merely shared — it is IDENTICAL

**The single most useful fact in the instrument is one the dispatch brief did not contain, and it is
measured rather than argued.** The replay's per-method block gives each of `move_lid`, `move_plate` and
`move_resource` **31 operations**, `n_scope_verdict_safe` **0**, and — for each — a `residual_site_sets`
map with **exactly one key**, and that one key is **byte-identical across all three methods**
(`outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json:241-261`). There is no per-method
variance and no per-operation variance to hedge against: **93 operations, one residual, thirteen
entries.**

> **Normative (the provenance of the per-operation list below, named rather than implied — round 1's
> C19).** The fifteen-finding list is read from the ledger's **`collision_ops`** block, whose selection
> criterion is the neighbouring `n_row_id_collisions: 12`
> (`outputs/plr-sema/unknown_ledger_260909_final.json:2172-2185`). It is a **diagnostic** block, not a
> canonical per-operation dump. Its content agrees finding-for-finding with the replay's
> `residual_site_sets`, which is why the substance stands; but the document that leans on it owes the
> reader the label, and §17.8.1 block (9) owes the round `n_row_id_collisions` before and after, with a
> sentence on whether a collision can double-count an operation in the gate's denominator of 93.

The per-operation finding list for one `move_resource` operation confirms it finding by finding —
**fifteen** findings, of which two are the same `<none>`-sited gap
(`outputs/plr-sema/unknown_ledger_260909_final.json:2174-2264`):

| # | site | reason | what it is |
|---|---|---|---|
| 1–2 | `<none>`, detail `_state_updated` | `unresolved_delegate` | the closure hit an unresolvable call, twice |
| 3 | `:2055` `LiquidHandler.pick_up_resource` | `guard_env_dependent` | `self.setup_finished and (not self._resource_pickups)` |
| 4 | `:2070` `LiquidHandler.pick_up_resource` | `guard_env_dependent` | `self._resource_pickup is not None` |
| 5 | `:2092` `LiquidHandler.pick_up_resource` | `guard_env_dependent` | `<unconditional>` — **tier (iii)**, see below |
| 6 | `:375` `LiquidHandler._check_args` | `guard_env_dependent` | `len(missing) > 0` |
| 7 | `:383` `LiquidHandler._check_args` | `guard_env_dependent` | `strictness == Strictness.STRICT` |
| 8 | `:2120` `LiquidHandler.move_picked_up_resource` | `guard_env_dependent` | `self._resource_pickup is None` |
| 9 | `:2147` `LiquidHandler.drop_resource` | `guard_env_dependent` | `self._resource_pickup is None` |
| 10 | `:2204` `LiquidHandler.drop_resource` | `guard_env_dependent` | `destination.direction == 'z'` |
| 11 | `:2211` `LiquidHandler.drop_resource` | `guard_predicate_unparsed` | `resource_rotation_wrt_destination % 180 != 0` |
| 12 | `:2226` `LiquidHandler.drop_resource` | `guard_predicate_unparsed` | `destination.resource is not None and destination.resource is not resource` |
| 13 | `:2233` `LiquidHandler.drop_resource` | `guard_env_dependent` | `not isinstance(resource, Plate)` |
| 14 | `:2284` `LiquidHandler.drop_resource` | `guard_env_dependent` | `isinstance(destination, ResourceStack) and destination.direction != 'z'` |
| 15 | `:2290` `LiquidHandler.drop_resource` | `guard_env_dependent` | `not isinstance(resource, Plate)` |

> **Normative (`:2092` is tier (iii) and is ALREADY excluded — it is `:576`'s exact analogue and it is
> not this increment's burden).** Its shipped guard record carries `"raises": "<dynamic:e>"`, predicate
> `TRUE`, an empty `scope_trail` and `"reachability_clear": false`, from the `raise e` inside
> `pick_up_resource`'s own `except` block
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2085-2092`). `is_dynamic_raise`
> returns true on the `<dynamic:` prefix and nothing else
> (`plr-sema/src/plr_sema/check/predicate.py:1121-1125`), `evaluate_guard` short-circuits it to
> `tier_iii` (`plr-sema/src/plr_sema/check/predicate.py:1441-1442`), and the site is folded into
> `excludes_sites` (`plr-sema/src/plr_sema/check/__init__.py:967-975`). **This is why `:2092` appears
> in the ledger's fifteen-finding list and NOT in the replay's thirteen-entry residual site set**, and
> the two documents agree exactly. The consequence is normative for §17.8: the unscoped `verdict` on a
> `move_*` operation can never be `SAFE` while `:2092` stands, so `scope_verdict` is the only field
> this increment could ever move — the same asymmetry increment 7 lived under, arrived at by the same
> derived rule.

### 17.0.2 Why the move family, and why not something else

**Confirmed on population, on uniformity and on reason-coverage — and the confirmation is arithmetic,
not deference to the brief.**

1. **Population.** 93 of 544 executed operations, **17.1%**, and the largest homogeneous block left
   after increment 7 took `pick_up_tips`. The next-largest is the volume family's 117
   (`aspirate` 77 + `dispense` 40), which is **not** homogeneous: it carries `:116`'s object-identity
   relation and the unseeded-volume cell, both refused by increment 7 §16.14 for reasons this increment
   does not reopen.
2. **Uniformity.** One residual, thirteen entries, three methods, zero variance
   (`outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json:241-261`). Every other family's
   per-method residual differs between its members. A uniform residual makes a *structural* gate
   possible — §17.8.2 gates on the exact set, which no other family could support. **Round 1 attacked
   exactly this and was right to**: spec_version 1's mechanism would have produced a NON-uniform
   residual (six sites on 31 operations, eight on 62), which is not a set condition (1) can be written
   over. §17.5.1's whole-closure fold is what restores uniformity, and it is the reason that section
   was re-derived rather than patched.
3. **Reason coverage.** The move family is the **sole** carrier of `unresolved_delegate` in the whole
   benchmark: the cluster's `per_method` is exactly `move_lid` 31, `move_plate` 31, `move_resource` 31
   (`outputs/plr-sema/unknown_ledger_260909_final.json:812-822`). Closing it takes one of five reasons
   to zero population, and no other target can do that.
4. **Spillover.** §17.1.4's diagnosis of `:375`/`:383` is not move-specific: the same two sites block
   `aspirate` 77, `dispense` 40, `discard_tips` 34, `drop_tips` 31, `stamp` 27 and `transfer` 19
   (`outputs/plr-sema/unknown_ledger_260909_final.json:42-58`). **The move family is the cheapest place
   to find the bug and the whole benchmark is where the fix lands** — 321 operations, 59% of the
   executed population, the largest cluster pair in the instrument. In spec_version 1 that spillover
   was a hope resting on an open diagnosis; in spec_version 2 the diagnosis is closed and the fix is
   thirty lines (§17.1.4, M-SURF).

**What would have been a better target, and was checked.** A target whose residual could reach a
verdict this increment. There is none: every family's residual contains at least one site behind a
mechanism §17.12 refuses, and the move family's is the *smallest* such remainder.

### 17.0.3 The claim

**Increment 8 removes SIX of the move family's thirteen residual entries and leaves SEVEN.** Six of the
seven are one mechanism in one PLR function; the seventh is `:383`, refused in §17.5.2 for a reason
derived at the pin rather than discovered at a measurement. It does **not** produce a joined `SAFE` on
any `move_*` operation. Whole-benchmark it takes `unresolved_delegate` from 186 findings to **0**,
`:375` from 321 blocked operations to **0**, and `:383` from 321 to **120** — which is increment 7's
own prediction, finally met on the operations its §16.10.3 claimed, and honestly short on the 120 it
cannot reach.

> **Normative (the `:375` claim is now split across TWO halves of the surface machinery, and the second
> half is D8-dependent — round 2's R2-C1).** spec_version 2 stated `:375 → 0` as resting on M-SURF (the
> **attachment** filter) plus M3. That was short by one half: a site rule needs a surface **row**, and
> row candidacy is a *selection* question decided by `collect_env_ref_method_names`
> (`plr-sema/src/plr_sema/derive/receiver_state.py:1486-1501`), which at this pin selects no
> `drop_resource` at all. **So `:375` on the move family (and on `transfer`/`discard_tips`/`stamp`) is
> D8-dependent in BOTH halves** — the selection extension and the argument map are both T54's — while
> the 148 `aspirate`/`dispense`/`drop_tips` operations still clear on M-SURF alone, because their
> method names are already selected and their `caller_args` is already populated at depth 1. **The
> residual is still SEVEN and `:375 → 0` still stands**, for a reason derived at the pin in §17.1.4 and
> not deferred to a measurement.

> **Normative (what this increment must NOT be read as claiming).** A published movement in
> `n_findings_decided`, in `n_clusters` or in `guard_env_dependent` is **not** the gate and cannot
> become it. `join` is unchanged (`plr-sema/src/plr_sema/verdict.py:313-323`) and one `UNKNOWN` finding
> still makes an operation `UNKNOWN`; every move cluster reports `n_ops_sole_blocker` **0**
> (`outputs/plr-sema/unknown_ledger_260909_final.json:812-822`). §17.8.2's gate is stated over the
> **residual site set per operation** for exactly the reason increment 7's §16.0.1 stated its own over
> `scope_verdict`: a count can move by 1,200 while nothing decides.

---

## 17.1 The thirteen entries, and what each one needs

> **Normative (how to read this table).** "This increment" is a **prediction** in increment 6 §15.1's
> and increment 7 §16.1's sense: §17.8.3 is the measured column, produced by T55, and where the two
> disagree the measurement wins and the divergence is recorded rather than absorbed. Every cell is
> **tier 1** — the graph lane's value is §17.8.3's own second table, per increment 7 §16.5.6's
> lane-asymmetry disclosure (`.praxia/docs/specs/260909_plr-sema-observation-increment.md:1127-1140`).

| entry | what it needs | from where | this increment? | resolves to |
|---|---|---|---|---|
| `_state_updated` ×2 | the inherited definition on `Resource` | §17.2's M-INH | **Y iff D9** | the gap disappears; no finding at all |
| `:2055` | the key set of `self._resource_pickups`, non-empty | §17.3's R-ARM plus the complete-`Seq` truthiness clause | **Y** | `SAFE` on 93 |
| `:2070` | `self._resource_pickup` is empty at entry | §17.4's typestate | **Y iff D7** | `SAFE` on 93 |
| `:2120` | `self._resource_pickup` is held after `pick_up_resource` | §17.4's typestate | **Y iff D7** | `SAFE` on 93 |
| `:2147` | same | §17.4's typestate | **Y iff D7** | `SAFE` on 93 |
| `:375` | the method name SELECTED into a surface row, the surface ATTACHED to the entry, plus `m`/`default` at depth ≥ 2 across every closure call site | §17.1.4's M-SURF (attachment) plus §17.1.4's selection extension and §17.5.1's M3 (both T54) | **Y** (M-SURF alone, the 148) **and Y iff D8** (the 93 — **both** halves) | `SAFE` on 321 |
| `:383` | the same, plus an empty `**kwargs` key set at a call site behind a `**` unpacking | M-SURF reaches 201; the move family needs D5a production (5) **and** an M1 clause-4 relaxation | **N** — §17.5.2 | stays ½ on 93 |
| `:2204` | `isinstance(destination, ResourceStack)` decided **F** | E-TYPE's negative direction | **N** — §17.1.5 | stays ½ |
| `:2211` | the same scope entry, decided **F** | E-TYPE's negative direction | **N** — §17.1.5 | stays ½ |
| `:2226` | an earlier arm decided **T**, so this arm's `else of:` is **F** | E-TYPE plus a bound `destination` | **N** — §17.1.5 | stays ½ |
| `:2233` | the same, or `resource` declared exactly `Plate` | E-TYPE plus a bound `destination` | **N** — §17.1.5 | stays ½ |
| `:2284` | the same | E-TYPE plus a bound `destination` | **N** — §17.1.5 | stays ½ |
| `:2290` | the same | E-TYPE plus a bound `destination` | **N** — §17.1.5 | stays ½ |

### 17.1.1 `_state_updated` — the gap is a RESOLUTION failure, not a semantic one

**The whole 186-finding cluster rests on a two-line function that cannot raise.** `Resource`'s own
`_state_updated` is a loop over registered callbacks and nothing else
(`external/pylabrobot/pylabrobot/resources/resource.py:932-934`); it contains no `raise` and no
`assert`. `LiquidHandler` calls it twice per move operation — once at the end of `pick_up_resource`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2094`) and once inside
`drop_resource` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2264`) — which is
exactly the multiplicity the ledger records, 186 findings over 93 operations
(`outputs/plr-sema/unknown_ledger_260909_final.json:812-822`).

> **Normative (spec_version 1's stated ground was WRONG and the correction is recorded rather than
> quietly applied — round 1's C8).** spec_version 1 claimed `_state_updated` contains *"no call the
> survey would record as a precondition"*. **That is false at its own cited lines.** The body's single
> statement is `callback(self.serialize_state())`
> (`external/pylabrobot/pylabrobot/resources/resource.py:934`); `serialize_state` is defined on
> `Resource` itself (`external/pylabrobot/pylabrobot/resources/resource.py:838-849`); and `visit_Call`
> ends in `generic_visit`, so the inner call is visited and recorded as a delegate
> (`scripts/survey_plr_preconditions.py:290-300`). **The correct claim is ZERO GUARDS, which is what
> AC-17.1 actually asserts**: neither `Resource._state_updated`
> (`external/pylabrobot/pylabrobot/resources/resource.py:932-934`), nor `Resource.serialize_state`
> (`external/pylabrobot/pylabrobot/resources/resource.py:838-849`), nor `LiquidHandler`'s override
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:214-237`) contains a `raise` or an
> `assert`. §17.8.3's `0` cell is unchanged; the defect was in the argument, and an argument that
> happens to reach the right cell by luck is exactly what a round exists to find.

**Why it is unresolvable today, in two independent halves, both read at the pin.**

1. **The survey side.** `visit_Call` sets `is_self_call` for a bare `self.<name>(...)` and then admits
   it as a delegate only when `name in self.class_method_names`; every other self-call falls to the
   `unresolved` branch (`scripts/survey_plr_preconditions.py:344-358`). The `class_method_names` set is
   built per `ClassDef` from `ast.iter_child_nodes` over **that class's own body**
   (`scripts/survey_plr_preconditions.py:347-357`), so an inherited method is structurally invisible.
   `_state_updated` is not validation-looking either — `_is_validation_looking` matches only the
   `_check`/`_assert`/`_validate` prefixes (`scripts/survey_plr_preconditions.py:173-175`) — so the
   `is_self_call` clause is the only reason it is recorded at all rather than silently dropped, which
   is the survey behaving correctly.
2. **The derive side.** Even with the survey fixed, `resolve` tries exactly two keys, both in the
   **same module**: `(rec.module, f"{rec.class_name}.{name}")` and `(rec.module, name)`
   (`plr-sema/src/plr_sema/derive/__init__.py:414-421`). `Resource` lives in
   `pylabrobot.resources.resource` and `LiquidHandler` in `pylabrobot.liquid_handling.liquid_handler`,
   so a same-module lookup can never find it, and `derive_contract` appends
   `("no_contract_derived", name)` instead (`plr-sema/src/plr_sema/derive/__init__.py:682-687`) —
   trading one `REASON_VOCABULARY` member for another.

**Both halves must move together, and §17.2 is the only place in this document where that is stated as
a hard ordering constraint within a single task row.**

### 17.1.2 `:2055` — the arm dictionary, and a sentence of increment 7 that is now false

The guard is `if self.setup_finished and not self._resource_pickups: raise RuntimeError`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2054-2055`), and its shipped
predicate is `And(EnvRef(("self","setup_finished")), Not(EnvRef(("self","_resource_pickups"))))` with
`reachability_clear` true.

`_resource_pickups` is a `Dict[int, Optional[ResourcePickup]]` initialised empty at construction
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:176`) and **rebuilt by `setup` as
`{a: None for a in range(self.backend.num_arms)}`**
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:212`). So after setup its truthiness
is exactly *"this backend declares at least one arm"* — a single, finite, enumerable fact about the
observed receiver, which is precisely R-HEAD's own shape applied to a second dictionary attribute.

**Only the second conjunct is needed, and that matters for cost.** `evaluate_predicate`'s `And` is
Kleene: one `False` makes the conjunction `False` whatever the others are
(`plr-sema/src/plr_sema/check/predicate.py:910-916`). A non-empty `_resource_pickups` makes
`Not(...)` `False`, the `And` `False`, `fires` `False`, and `evaluate_guard` returns `_SAFE`
(`plr-sema/src/plr_sema/check/predicate.py:1451-1452`). **`self.setup_finished` never has to resolve**,
and this increment does not make it resolve.

> **Normative (an EXPLICIT amendment of increment 7 §16.5.1, in increment 7's own manner — the same
> shape its Q-MONO used on increment 6 G8(1)).** The shipped `EnvRef` clause in predicate position
> decides only for an `ir.Lit` and returns ½ for everything else, and it refuses `("self","head")` by
> **shape**, before any resolution, on the stated ground that *"a dict is not a truth value and no
> guard at this pin uses it as one"* (`plr-sema/src/plr_sema/check/predicate.py:934-944`). **The second
> half of that sentence is falsified by `:2055`**, which uses a dict as a truth value directly. The
> amendment is minimal and is stated as a rule rather than an exception:
>
> > **A complete `Seq` decides in predicate position.** An `EnvRef` for which `_resolve_env_ref`
> > returns a **non-`Top`** `ir.Seq` **together with a `rule` whose §16.5 specification declares that
> > `Seq` complete** — today exactly `R-HEAD` and, as of this increment, `R-ARM` — evaluates `T` iff
> > that `Seq` is non-empty and `F` iff it is empty. An `EnvRef` resolving to any other value, to
> > `ir.Top`, or under any other rule, is ½ exactly as today.
>
> **Keying on the RULE and not on the node is deliberate and is the whole of the amendment's
> narrowness.** Completeness is not a field on `ir.Seq`; it is a property the resolution rule declares
> in its own specification, and `_resolve_env_ref` already returns that rule alongside the value
> (`plr-sema/src/plr_sema/check/predicate.py:309-319`). A clause keyed on `isinstance(value, ir.Seq)`
> would silently admit any future rule that returns a lower-bound `Seq`; a clause keyed on the rule
> admits exactly the two that have argued completeness.
>
> **The `("self","head")` shape refusal is KEPT, unchanged and by shape**, because no guard at this pin
> reads `self.head` as a truth value and removing a live fail-closed refusal that nothing needs is the
> surface growth §9.4 exists to prevent. The amendment is written into increment 7's own §16.5.1 text
> and into the code comment that repeats it, in the same commit, which is T51's job.

### 17.1.3 `:2070`, `:2120`, `:2147` — one typestate, three readings, and the ordering problem

The three guards are the two-state protocol PLR writes around a single receiver field:

- `pick_up_resource` raises if `self._resource_pickup is not None`
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2069-2070`) and then **sets** it
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2072-2077`), rolling it back to
  `None` on any backend exception
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2090-2092`).
- `move_picked_up_resource` raises if `self._resource_pickup is None`
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2119-2120`).
- `drop_resource` raises if `self._resource_pickup is None`
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2146-2147`) and **clears** it after
  the backend call (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2261-2264`).

`_resource_pickup` is a `@property` over `self._resource_pickups.get(0)` with a setter that assigns
`self._resource_pickups[0]` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:178-185`),
so an `ast.Assign` to `self._resource_pickup` is what the AST sees at both mutation sites and the
property/setter pair is invisible to a shape test over the assignment. That is convenient and it is
also a hazard, and §17.4.2's absence rule is where it is paid for.

> **Normative (the ordering problem, stated because it is the ONE respect in which this typestate is
> not increment 1's).** `TipWalk` carries **one state per receiver per CALL instruction**, with guards
> evaluated against the pre-state and `_apply_transfer` applied afterwards
> (`plr-sema/src/plr_sema/check/tipstate.py:490-518`, `:521-543`). That is an **inter**-operation
> model. Here all three guards live inside **one** `move_resource` CALL, and the field's value differs
> between them: empty at `:2070`, held at `:2120` and `:2147`. **A single per-call state cannot decide
> all three**, and any implementation that assigns one state to the whole flattened guard list will
> either be wrong at `:2070` or wrong at `:2120`/`:2147`. §17.4 is the intra-operation model that
> answers this, and it is the largest single piece of new machinery in the increment.

### 17.1.4 `:375` and `:383` — increment 7's own divergence, DIAGNOSED

> **This subsection reports a falsified prediction of the immediately preceding increment. It is stated
> as prominently as increment 7 §16.1.1 stated its own withdrawal, and for the same reason: a
> divergence absorbed silently is worse than one that never happened. spec_version 1 left the
> diagnosis OPEN on 148 operations and predicted the other 173 from a reading of which M1 clause
> refuses which entry point. Round 1 falsified that reading (C3), and re-deriving it from the shipped
> traversal turned up the real cause — which explains all 321 at once, and neither of spec_version 1's
> two candidates is it.**

Increment 7 §16.10.3 predicted `:375` and `:383` at `SAFE` on **544** operations under D6, D6 was taken,
T49 shipped, and the final ledger measures each cluster at **321 findings over 321 operations**
(`outputs/plr-sema/unknown_ledger_260909_final.json:42-58`, `:88-104`). The 223 that did flip are
`pick_up_tips`, which is absent from both `per_method` breakdowns; the 321 that did not are
`aspirate` 77, `dispense` 40, `discard_tips` 34, `drop_tips` 31, `move_lid` 31, `move_plate` 31,
`move_resource` 31, `stamp` 27 and `transfer` 19 — a sum that closes exactly.

**The arithmetic is not the problem, and this document reproduces it at the pin for the move family
specifically.** The two `_check_args` calls inside `move_resource` pass
`self.backend.pick_up_resource` with `default={"pickup"}`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2345-2350`) and
`self.backend.drop_resource` with `default={"drop"}`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2364-2369`); the chatterbox backend
declares `pick_up_resource(self, pickup)` and `drop_resource(self, drop)`
(`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:223-231`). So
`params ⊆ default` holds at **both** sites, `missing` is empty at both, and the shipped
`_eval_check_args_missing_site_rule` would return `F` at each of them
(`plr-sema/src/plr_sema/check/predicate.py:1252-1288`).

**The fence table, RE-DERIVED from the traversal rather than from the source text (C3).** Depth is not
a property of the source: it is carried on a LIFO frontier, pushed at expansion time and settled at
pop time, over a `delegates_to` list the survey emits as `sorted(set(...))`
(`plr-sema/src/plr_sema/derive/__init__.py:445-459`, `scripts/survey_plr_preconditions.py:338`). Traced
for entry point `move_resource`: the frontier is pushed
`[_check_args(1), _log_command(1), drop_resource(1), move_picked_up_resource(1), pick_up_resource(1)]`;
`pop()` takes `pick_up_resource(1)`, which pushes `_check_args(2)` for its own call at
`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2079-2081`; that depth-2 entry is
popped before the depth-1 entry buried beneath it, is added to `seen`, and the depth-1 entry is then
skipped. So:

| entry point | where `_check_args`'s guards are inlined | which M1 fence refuses | ops |
|---|---|---|---|
| `move_resource` | **depth 2**, via `pick_up_resource` | clause 6 (`depth == 1` only) — and, independently, clauses 1–2, since `move_resource`'s own body carries TWO call sites and `_find_delegate_call` returns `None` on anything but one (`plr-sema/src/plr_sema/derive/bindings.py:884-886`) | 31 |
| `move_lid`, `move_plate` | **depth 3**, via `move_resource` then `pick_up_resource` | clause 6 | 62 |
| `transfer`, `discard_tips`, `stamp` | depth 2, via `aspirate`/`dispense`, `drop_tips`, `aspirate96`/`dispense96` | clause 6 | 80 |
| `aspirate`, `dispense`, `drop_tips` | **depth 1, one call site — `caller_args` IS populated** | **neither**; the refusal is downstream | 148 |

> **Normative (the third candidate cause round 1 proposed is FALSIFIED and is NOT adopted).** C3
> suggested that the LIFO artifact might also explain the 148 — that a sibling delegate reaching
> `_check_args` would demote them out of depth 1. It does not: `aspirate`, `dispense` and `drop_tips`
> each have exactly one `self._check_args(...)` call and **no sibling delegate that calls it**
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1037-1042`, `:1238-1243`,
> `:687-692`), so each sits at depth 1 with `caller_args` populated. The independent corroboration is
> `pick_up_tips`, which has the identical shape (`:541-546`) and DID flip — meaning depth cannot be
> what separates the 223 from the 148. **A candidate cause that cannot separate the two populations is
> not a cause, and it is recorded here as refused rather than left in the box.**

**The real cause, and it explains all 321 with one mechanism.** `evaluate_guard` reads the derived
backend surface off the guard's own contract entry —
`contract.get("backend_surface", {}).get("rows", {})`
(`plr-sema/src/plr_sema/check/predicate.py:1439`) — and `_check_args_surface_row` declines whenever the
row is absent (`plr-sema/src/plr_sema/check/predicate.py:1234-1249`), which makes **both** site rules
decline (`plr-sema/src/plr_sema/check/predicate.py:1252-1288`, `:1291-1326`). And the attachment is
**filtered**: `derive/__main__.py` attaches `entry["backend_surface"]` only to a contract entry whose
own guards' **`predicate`** JSON carries a `self.backend.<method>(...)` `EnvRef` with `args is not
None` — a CALL — (`plr-sema/src/plr_sema/derive/__main__.py:341-356`).

> **Normative (the prevalence is read from the ARTIFACT, not from the code comment — round 2's R2-C9).**
> spec_version 2 quoted the filter's own comment, *"only 10 of 4,770 entries … at this pin"*
> (`plr-sema/src/plr_sema/derive/__main__.py:336-337`), as a fact about the pin. **The quote is verbatim
> and the comment is stale**, and the shipped table settles it: the artifact carries exactly **five**
> entries with an attached `backend_surface` sub-object, and they are
> `LiquidHandler.consolidate_tip_inventory`
> (`plr-sema/data/derived_contracts.json:103527-103528`), `LiquidHandler.move_tips` (`:109798-109799`),
> `LiquidHandler.pick_up_tips` (`:111527-111528`), `LiquidHandler.probe_tip_presence_via_pickup`
> (`:113039-113040`) and `LiquidHandler.use_tips` (`:117032-117033`). **This corroborates the
> mechanism rather than weakening it**: of the five, only `pick_up_tips` is executed on this benchmark
> (`outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json:79-90` lists the executed methods
> and the other four are absent), so "the 223 that flipped are `pick_up_tips`" closes exactly and
> 223 + 321 = 544. **Reading this artifact is also what surfaces §17.1.4's second half below**, which
> is why spec_version 3 moves it out of the frontmatter's not-read list.

**There is exactly ONE guard predicate in `LiquidHandler` with that shape**: `pick_up_tips`'s
`if not all(self.backend.can_pick_up_tip(channel, tip) for channel, tip in zip(...))`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:506-512`). Every other
`self.backend.<m>(...)` in the file is an awaited backend dispatch or a `self.backend.<attr>` read,
neither of which is a guard condition. **So `pick_up_tips` — and the handful of entry points whose
closures reach its guard — are the only contract entries carrying a surface at all, which is exactly
the 223 that flipped; and every one of the other 321 declines at the surface lookup, which is exactly
why `:375` and `:383` carry byte-identical populations and byte-identical `per_method` breakdowns.**
One shared cause, not two independent ones — and two independent causes were never plausible for two
clusters that agree to the operation.

> **Normative (M-SURF — the fix, and it is T49's own missing half rather than a new mechanism).** T49
> already found and fixed this asymmetry on the SELECTION side:
> `collect_env_ref_method_names` was extended to scan `caller_args` as well as `predicate`, and its own
> docstring states why — without that half, *"`LiquidHandlerChatterboxBackend.pick_up_tips` … would
> never become a `n_surface_candidates` row at all"*
> (`plr-sema/src/plr_sema/derive/receiver_state.py:1457-1501`). The ATTACHMENT filter in
> `derive/__main__.py` was not extended in the same commit
> (`plr-sema/src/plr_sema/derive/__main__.py:341-356`). **M-SURF extends it, by the identical rule:** a
> contract entry receives the surface when any of its guards carries a `self.backend.<m>` `EnvRef`
> either in its own `predicate` (with `args is not None`, unchanged — R-CONST's need) **or** in its
> `caller_args` map (with or without `args` — D5b's need, and the shape `_check_args_method_name`
> actually reads, `plr-sema/src/plr_sema/check/predicate.py:1240-1249`).
>
> **Its blast radius is confined, and the argument is checkable rather than asserted.** The entries
> M-SURF newly attaches are precisely those with a `caller_args`-borne `self.backend.<m>` `EnvRef` and
> **no** call-shaped one in any guard predicate — because an entry with a call-shaped one already had
> the attachment. R-CONST reads the surface only for an `EnvRef` with `args is not None` in a guard
> predicate (`plr-sema/src/plr_sema/check/predicate.py:328-333`), so on every newly-attached entry
> R-CONST has nothing new to decide. **The effect is therefore confined to the two `_check_args` site
> rules, both of which return `F` or `None` and can never return `T`**
> (`plr-sema/src/plr_sema/check/predicate.py:1286-1288`, `:1324-1326`) — so M-SURF is one-directional
> by construction, on D-G6's own argument, and AC-17.4 asserts `n_resolved_by_rule` for R-CONST
> unchanged as the checkable form of that claim.

> **Normative (THE SECOND HALF — the surface SELECTION half is ALSO unrepaired, and it is T54's, not
> T53's. Round 2's R2-C1, conceded as a blocker and found broader than filed).** M-SURF above fixes
> *which entries receive the `rows` dict*. It adds **no rows**, and a site rule needs a **row**:
> `_check_args_surface_row` returns `ctx.backend_surface.get(f"{backend_class}.{method}")`
> (`plr-sema/src/plr_sema/check/predicate.py:1249`) with `method` the last segment of
> `ctx.caller_args["method"]` (`plr-sema/src/plr_sema/check/predicate.py:1240-1249`), and both site
> rules decline on `row is None` (`plr-sema/src/plr_sema/check/predicate.py:1277-1279`, `:1321-1323`).
>
> **The row is missing, and this is measured in the shipped artifact rather than argued.** The
> top-level `rows` block carries **TEN** `*.pick_up_resource` keys and **zero** `*.drop_resource` keys
> (`plr-sema/data/derived_contracts.json:3-6` reports `n_surface_candidates` 160,
> `n_surface_absent_by_c15` 71, `n_surface_rows` 89; the ten `pick_up_resource` keys begin at `:65`
> and the next `drop_resource` occurrence anywhere in the file is a contract-entry key far past the end
> of `rows`). **There is no `*.drop_resource` surface row at this pin.** The ten, sorted, are
> `EVOBackend`, `ExperimentalSCARA`, `LiquidHandler`, `LiquidHandlerChatterboxBackend`,
> `NimbusBackend`, `OpentronsOT2Backend`, `PreciseFlexBackend`, `STARBackend`, `SerializingBackend` and
> `VantageBackend`, each `.pick_up_resource` — **nine backend classes plus `LiquidHandler` itself**,
> which is the distinction both round-2 reports and spec_version 3's first draft collapsed into a
> wrong row count of nine. The count matters only because AC-17.5's exact prediction below is derived
> from it.
>
> **Why, in one chain.** Row candidacy is `qualname.rsplit(".",1)[-1] in selected_method_names`
> (`plr-sema/src/plr_sema/derive/receiver_state.py:1537-1542`), and `selected_method_names` is
> `collect_env_ref_method_names`'s output, which scans exactly two JSON locations per guard — the
> guard's own `predicate` and its `caller_args`
> (`plr-sema/src/plr_sema/derive/receiver_state.py:1486-1501`). `caller_args` is populated **only**
> under `depth == 1` against the entry point
> (`plr-sema/src/plr_sema/derive/__init__.py:640-651`), and `compute_caller_args` refuses a caller
> whose body holds other than exactly one call site
> (`plr-sema/src/plr_sema/derive/bindings.py:966-968`, via `:884-886`).
> `self.backend.drop_resource` is a `_check_args` argument at exactly ONE place in PLR —
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2364-2369`, inside `move_resource`,
> whose body carries **two** `_check_args` calls (`:2345`, `:2364`) and from which `_check_args` is
> popped at depth 2 — and `drop_resource` itself calls no `_check_args` at all
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2200-2295` carries the six
> branch-arm guards and no `_check_args`). **So `drop_resource` never enters any `caller_args`, never
> enters `selected_method_names`, and never becomes a row.** `pick_up_resource` escapes only because
> `LiquidHandler.pick_up_resource` is itself a contract entry with a unique depth-1 `_check_args` call
> at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2079-2081`, which supplies the
> name.
>
> > **The selection extension (T54).** `collect_env_ref_method_names`
> > (`plr-sema/src/plr_sema/derive/receiver_state.py:1486-1501`) scans, per guard, its `predicate`, its
> > `caller_args` **and — additively — every per-site map of §17.5.1's new `caller_args_sites` field**,
> > by the identical `predicate_from_json`/`predicate_walk` pair it already uses on the other two. Every
> > value in every per-site map is a `Term` JSON exactly as `caller_args`' values are, so the walk is
> > total over them by construction and no new parser is needed.
>
> **This half is T54's and D8-dependent, and T53's `caller_args` extension is unchanged.** The 148
> `aspirate`/`dispense`/`drop_tips` operations reach `_check_args` at **depth 1** with `caller_args`
> populated, so their method names are already in `selected_method_names` and already have rows
> (`plr-sema/data/derived_contracts.json:151-190` carries the chatterbox `aspirate`, `aspirate96`,
> `can_pick_up_tip`, `dispense`, `dispense96` and `drop_tips` rows). **T53 alone therefore still clears
> `:375` and `:383` on the 148 through the shipped rules, and §17.11's T53-before-T54 ordering and
> §17.8.2's D8-decline branch are both unchanged.** What moves behind D8 is the depth ≥ 2 populations:
> the 80 `transfer`/`discard_tips`/`stamp` and the 93 `move_*`, which need the selection extension AND
> the attachment filter to read `caller_args_sites` AND M3 to populate it.
>
> **The attachment filter must scan `caller_args_sites` too, and that is also T54's.** For
> `move_lid`/`move_plate`/`move_resource` the `_check_args` guards sit at depth 2/3 and carry no
> `caller_args` at all, so an attachment filter reading only `predicate` and `caller_args` would attach
> nothing to a move-family entry and `evaluate_guard`'s
> `contract.get("backend_surface", {}).get("rows", {})`
> (`plr-sema/src/plr_sema/check/predicate.py:1439`) would still return `{}`. The artifact corroborates
> the mechanism: of the five entries carrying an attached `backend_surface`, none is a move method.
>
> **`:375 → 0` is KEPT rather than retreated from, and the sufficiency is provable at the pin before
> any run.** `LiquidHandlerChatterboxBackend.drop_resource(self, drop)` is **undecorated and
> singly-defined** (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:229-230`;
> `pick_up_resource` is its only same-file neighbour of the pair, at `:223-224`), so it survives C15's
> absence rule — `node.decorator_list` is empty and `n_definitions_at_qualname` is 1
> (`plr-sema/src/plr_sema/derive/receiver_state.py:1450-1454`) — and yields
> `params: ["drop"], has_var_keyword: False`. Against `default={"drop"}` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2364-2369`, `params ⊆ default`
> holds and `_eval_check_args_missing_site_rule` returns `F`
> (`plr-sema/src/plr_sema/check/predicate.py:1286-1287`). **`:383`'s refusal is unaffected**, because
> `has_var_keyword` is `False`. **This is why the residual stays SEVEN and not eight**, and it is a
> derivation at the pin rather than a hope at a gate.
>
> > **Normative (the `F` is scoped to the RESOLVED `m`, and the ten new rows are HETEROGENEOUS).** The
> > site rule looks up `f"{backend_class}.{method}"` with `backend_class` read from the observation, so
> > on this benchmark's `move_*` operations the row actually read is
> > `LiquidHandlerChatterboxBackend.drop_resource` and no other. **The `F` above is asserted for that
> > row only.** The other nine `drop_resource` rows differ in shape and are added to the table without
> > being read by any move-family guard: `SerializingBackend.drop_resource(self, drop, **backend_kwargs)`
> > has `has_var_keyword` **True**
> > (`external/pylabrobot/pylabrobot/liquid_handling/backends/serializing_backend.py:199`),
> > `ExperimentalSCARA.drop_resource(self, position, access=None, **backend_kwargs)` carries
> > `params ["position", "access"]` and `has_var_keyword` **True**
> > (`external/pylabrobot/pylabrobot/arms/scara.py:97-102`), and
> > `PreciseFlexBackend.drop_resource(self, position, access=None)` carries the same params with
> > `has_var_keyword` **False**
> > (`external/pylabrobot/pylabrobot/arms/precise_flex/precise_flex_backend.py:289-293`). **This mirrors
> > the shipped `pick_up_resource` twin exactly** — `ExperimentalSCARA.pick_up_resource` already ships
> > `params ["position", "plate_width"]` with `has_var_keyword` `True` and
> > `SerializingBackend.pick_up_resource` already ships `has_var_keyword` `True`
> > (`plr-sema/data/derived_contracts.json:87-93`, `:555-561`) — so the heterogeneity is **expected and
> > precedented, not alarming**. It is stated because a reader must not infer from "`params ⊆ default`
> > holds" that it holds for every new row; it holds for the one the observed `backend_class` selects.
>
> **The blast radius of the SELECTION half, re-argued because it is wider than M-SURF's — and stated
> as an EXACT prediction rather than an approximation, because a measured twin makes it exact.**
> Admitting `drop_resource` into `selected_method_names` makes every `<Class>.drop_resource` in the
> function index a candidate. **The candidate set is measurable at the pin and it is TWELVE**:
> `def drop_resource` occurs at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2132`,
> `external/pylabrobot/pylabrobot/liquid_handling/backends/backend.py:133`,
> `external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:229`,
> `external/pylabrobot/pylabrobot/liquid_handling/backends/serializing_backend.py:199`,
> `external/pylabrobot/pylabrobot/liquid_handling/backends/opentrons_backend.py:636`,
> `external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/nimbus_backend.py:2287`,
> `external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/STAR_backend.py:5030`,
> `external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/vantage_backend.py:1383`,
> `external/pylabrobot/pylabrobot/liquid_handling/backends/tecan/EVO_backend.py:609`,
> `external/pylabrobot/pylabrobot/arms/backend.py:105`, `external/pylabrobot/pylabrobot/arms/scara.py:97`
> and `external/pylabrobot/pylabrobot/arms/precise_flex/precise_flex_backend.py:289` — each singly
> defined within its own file, and **exactly two of the twelve `@abstractmethod`-decorated**
> (`external/pylabrobot/pylabrobot/liquid_handling/backends/backend.py:132-133` and
> `external/pylabrobot/pylabrobot/arms/backend.py:104-105`), so absent by C15's clause 1.
>
> > **The prediction, DERIVED from the measured twin and falsifiable by the counters T54 publishes.**
> > `def pick_up_resource` has the **identical** shape at this pin — twelve definitions, exactly two
> > `@abstractmethod` — and it ships **ten** rows. By that twin:
> >
> > | counter | today | after T54 | delta |
> > |---|---|---|---|
> > | `n_surface_candidates` | 160 | **172** | +12 |
> > | `n_surface_absent_by_c15` | 71 | **73** | +2 (the two abstract declarations) |
> > | `n_surface_rows` | 89 | **99** | +10 |
> >
> > The rule's own invariant reproduces: 172 − 73 = **99**, exactly as 160 − 71 = 89 holds today
> > (`plr-sema/src/plr_sema/derive/receiver_state.py:1508-1512` states that invariant as holding by
> > construction). **This is a derivation, not a certainty**: if C15 excludes a `drop_resource`
> > declaration for a reason `pick_up_resource` does not share, block (4)'s published before/after
> > counters show it, and **AC-17.5 asserts these three figures by value** precisely so that divergence
> > is a recorded falsification rather than an unnoticed drift.
>
> **§17.8.1 block (4) publishes all four counters before and after** rather than leaving the movement
> to be discovered. **R-CONST is still unaffected**, and for a checkable reason:
> R-CONST reads the surface only for an `EnvRef` with `args is not None` in a guard **predicate**
> (`plr-sema/src/plr_sema/check/predicate.py:328-333`), and no guard predicate anywhere in PLR carries
> a call-shaped `self.backend.drop_resource` — the only occurrence of that path is a `_check_args`
> **argument** (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2364-2369`). So the
> new rows are readable by exactly the two `_check_args` site rules, both of which return `F` or `None`
> and can never return `T`, and AC-17.5 asserts R-CONST's `n_resolved_by_rule` unchanged across T54 as
> the checkable form of that claim.

**What M-SURF alone buys, and what still needs M3.** With the surface attached, `:375` needs `m` and
`default` from `caller_args`, and `:383`'s shipped route needs only `has_var_keyword`:

- **The 148** (`aspirate` 77, `dispense` 40, `drop_tips` 31) already have `caller_args` at depth 1.
  Their `default={"ops", "use_channels"}` and the chatterbox `aspirate`/`dispense`/`drop_tips` declare
  exactly `(self, ops, use_channels, **backend_kwargs)`
  (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:123-128`, `:162-167`, `:93`),
  so `params ⊆ default` and `has_var_keyword` is `True`. **Both sites clear on M-SURF alone, with no
  decision hook and no M3.**
- **The 80** (`transfer`, `discard_tips`, `stamp`) and **the 93** move operations reach `_check_args`
  at depth ≥ 2 and need **all three** of T54's pieces: M3 to populate the per-site maps at all, the
  selection extension so the depth ≥ 2 method names become rows, and the attachment filter's own
  `caller_args_sites` scan so their entries receive the `rows` dict. All three are D8's.
- **`:383` on `stamp` (27) and on the move family (93) is unreachable either way**, because
  `has_var_keyword` is `False` for every backend method those two reach — chatterbox's
  `aspirate96(self, aspiration)`, `dispense96(self, dispense)`
  (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:207-209`, `:216-221`) and
  `pick_up_resource`/`drop_resource`
  (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:223-231`) all take no
  `**backend_kwargs` — and §17.5.2's second route is refused. **120 operations of `:383` survive this
  increment and §17.8.3 states them as such.**

### 17.1.5 The six `drop_resource` sites — refused, and the refusal is about soundness, not cost

All six sit inside the `isinstance(destination, ...)` chains of `drop_resource`: `:2204` and `:2211` in
the `ResourceStack` arm (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2203-2214`),
`:2226` in the `ResourceHolder` arm and `:2233` in the `PlateAdapter` arm
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2224-2233`), and `:2284`/`:2290` in
the second chain's `ResourceStack` and `PlateAdapter` arms
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2282-2290`).

**They would all fall to machinery that is already shipped — if one thing were true, and it is not.**
`scope_excludes` returns `SAFE` as soon as **some** trail entry evaluates `F`, and it does so **before
the predicate is evaluated at all** (`plr-sema/src/plr_sema/check/predicate.py:1040-1044`,
`:1442-1444`). That is why this arm cascade is attractive: it would decide `:2211` and `:2226` —
whose predicates are an arithmetic `BinOp` and an object-identity relation, both refused productions —
**without parsing them**, taking `guard_predicate_unparsed` down by 186 findings on a family whose
grammar this increment does not touch.

**The one thing that is not true is that E-TYPE can say `F`.** `_eval_is_instance` returns `True` when
the declared name is-or-subclasses one of the tested types and `None` otherwise, and its own docstring
states why `F` is structurally unreachable: `F` requires the declared name to be **known exact**, and
`ir.Resource` carries no field for that (`plr-sema/src/plr_sema/check/predicate.py:575-594`). The IR's
`Resource` has seven fields — `slot`, `type`, `element_type`, `is_container`, `is_parameter`, `parents`
and `grid` — and no exactness among them (`plr-sema/src/plr_sema/check/ir.py:178-191`).

> **Normative (why this is REFUSED here, on the argument's TRUE ground — round 1's C12, conceded).**
> spec_version 1 argued that a wrong `F` in a scope entry is *different in kind* from a wrong answer
> anywhere else, because every other mechanism produces `SAFE` through a guard's own `fires is False`.
> **That is architecturally false and the correction is recorded rather than softened.**
> `_scope_entry_value` re-parses each trail entry and evaluates it through the **same**
> `evaluate_predicate` with the **same** `ctx` (`plr-sema/src/plr_sema/check/predicate.py:1011-1025`),
> and `scope_excludes` runs before the site rule
> (`plr-sema/src/plr_sema/check/predicate.py:1442-1446`). So the amended complete-`Seq` truthiness
> clause, R-ARM, and any name M3 newly binds are **all** live inside scope entries and can all produce
> the same silent excision. D11 does not differ in kind.
>
> **The true ground, which survives the correction and is why the recommendation is unchanged.** An
> exactness field is a **derived type claim over the whole corpus**, and this increment cannot audit
> that corpus: nothing anywhere currently publishes the per-operation declared `type`/`element_type` of
> the `destination` and `resource` operands. It differs from every mechanism taken here in three
> measurable ways, not one rhetorical one. **(a) It needs an unauditable input**, where R-ARM's input is
> a single observed dictionary's key set and the typestate's is a shape over one class's own body.
> **(b) It clears SIX sites at once**, through a cascade in which one wrong arm silently excuses every
> later arm, so a single wrong claim is six wrong answers rather than one. **(c) It needs an
> `IR_VERSION` bump that re-keys every cached entry**, which no other mechanism here does. **A wrong
> exactness claim converts six sites on 93 operations to `SAFE` in one step**, which is a false `SAFE`,
> the one failure mode the whole project exists to prevent, and it is not a risk to take in the same
> increment as four other new mechanisms. **It is D11 (§17.13), recommended NO**, with two things owed
> before increment 9 can argue it: §17.8.1 block (11)'s per-operation declared operand types, and
> block (10)'s `n_scope_excluded` per site before and after — the block that makes a silent excision
> **anywhere** in this increment visible, which is C12's own remedy and applies to the four mechanisms
> taken quite as much as to the one refused.

> **Normative (a partial route that exists and is ALSO not taken, recorded so the round can weigh it).**
> `:2233` and `:2290` read `not isinstance(resource, Plate)`, and `resource` is `drop_resource`'s own
> local, assigned `self._resource_pickup.resource`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2146-2148`) — a plain `ast.Assign`
> of an attribute chain, which no binding idiom substitutes, so it is ⊤ today. §17.4's typestate
> carries the held resource as an `ir.Ref` and **could** bind it, after which E-TYPE's **positive**
> direction would decide `isinstance(resource, Plate)` `T` for `move_plate` and the two guards would be
> `SAFE` on 31 operations. **It is not gated and not claimed**, for two reasons: it is `T` only when the
> corpus declares those resources exactly `Plate`, which §17.8.3 cannot derive; and it would break the
> gate's uniformity — 31 of 93, on two of six sites — for no operation gained, since five sites remain
> regardless. **T55 publishes it as a measured extra and §17.8.2 does not gate on it.**

---

## 17.2 M-INH — inherited self-call resolution

> **Normative (the rule, in two halves that must land together).**
>
> **Half 1, the survey.** The per-`ClassDef` method-name set
> (`scripts/survey_plr_preconditions.py:347-357`) is extended with the method names of every class in
> that class's **transitive base closure**, computed over a whole-tree class index. A `self.<name>()`
> call whose `name` is in the extended set is a **delegate**, not an unresolved call
> (`scripts/survey_plr_preconditions.py:290-300`). The record gains one additive field,
> `inherited_delegates`, listing the names admitted only by inheritance, so the selection is
> inspectable and its count publishable.
>
> **Half 2, the derive package.** `resolve` gains a **third** step, tried only after its two existing
> same-module steps fail and never before them, so the class-first-then-module precedence its docstring
> declares normative is untouched (`plr-sema/src/plr_sema/derive/__init__.py:397-421`): walk
> `rec.class_name`'s transitive bases and return `(module_of(B), f"{B}.{name}")` for the **unique** base
> `B` that defines it.

> **Normative (the base-name extractor and its fail-closed shapes — round 1's C9, conceded).**
> spec_version 1 said the base closure was *"DERIVED and already shipped"*. **It is not.**
> `subclass_closure_from_bases` consumes a `{name: tuple[base names]}` map
> (`plr-sema/src/plr_sema/check/predicate.py:541-566`) and **nothing in the repo builds one** — its only
> callers are hand-built test fixtures. T50 builds it, from `build_plr_class_index`'s `class_nodes`
> (`plr-sema/src/plr_sema/derive/receiver_state.py:1241-1268`), by this closed rule over each element of
> a `ClassDef.bases` list:
>
> | base expression | base name | why |
> |---|---|---|
> | `ast.Name` | its `id` | the ordinary case |
> | `ast.Attribute` | its `attr` (`resources.Resource` → `Resource`) | the same last-segment rule §16.3's own selection already applies to an `EnvRef` path |
> | `ast.Subscript` | the base name of its `value`, recursively (`Generic[T]` → `Generic`) | the subscript carries no class identity |
> | anything else | **refuse the WHOLE class** | a call, a starred expression or a metaclass keyword means the base list was not fully read |
>
> **Refusing the class rather than dropping the one base is the whole point.** Condition 1 below claims
> a base defines `name` **uniquely in the closure**, and that claim is only licensed by having seen
> every base. A class whose base list contains one unreadable expression is entered in the map with a
> sentinel that makes every M-INH resolution against it — and against every class deriving from it —
> return `None`.
>
> **Import aliases are NOT resolved, and the consequence is stated rather than hidden.** A base written
> under an alias (`import x as Y; class C(Y)`) yields the alias name, which is simply absent from the
> whole-tree class index and contributes nothing further — `subclass_closure_from_bases`'s own
> documented fail-closed behaviour for an unresolvable base. **That is a silent INCOMPLETENESS, not a
> wrong answer**, and it is the one place M-INH can under-resolve. T50 publishes, per class, the count
> of base names that did not resolve to an indexed class, so the incompleteness is measured rather than
> assumed zero.
>
> **The bare-name collision in the shipped index is a second fail-closed case.**
> `build_plr_class_index` keys by **bare class name**, whole-tree, first definition wins via
> `setdefault`, and returns `class_modules` on the same bare key
> (`plr-sema/src/plr_sema/derive/receiver_state.py:1255-1268`), so two same-named classes in different
> PLR modules collapse and `module_of(B)` can name the wrong module — a resolution to a *different
> class's* method of the same name, invisible to condition 1, which only counts definitions inside the
> computed closure. T50 therefore builds its own `(module, name)`-keyed index alongside, and **any class
> name defined in more than one module makes every M-INH resolution mentioning it return `None`.**

> **Normative (four fail-closed conditions, and each closes a distinct way this could be WRONG).**
>
> 1. **Ambiguity refuses.** If more than one class in the base closure defines `name`, `resolve`
>    returns `None` and the gap stands. AST bases are not a Python MRO linearisation, and inlining the
>    wrong body's guards is the only way this mechanism could produce a **false** answer rather than
>    merely a different one. `LiquidHandler` has more than one base, so this is a live condition and
>    not a hypothetical.
> 2. **A base outside the analyzed surface refuses.** If the unique defining class is not in the index,
>    or was refused by the extractor's fourth row or by the collision rule above, the gap stands —
>    today's behaviour exactly.
> 3. **The closure is bounded and the bound is published.** Newly resolved delegates transitively pull
>    in their own delegates through `_walk_closure`
>    (`plr-sema/src/plr_sema/derive/__init__.py:424-459`). T50 publishes the per-entry-point closure
>    size, guard count **and per-guard depth multiset** before and after, and **stops and surfaces to
>    the user rather than landing** if any entry point's closure more than doubles.
> 4. **An inherited body's own self-calls dispatch on the ANALYZED class, or the call refuses.** Inside
>    a body this rule admitted — and only there — a `self.<n>()` call resolves, in order: **(i)** to the
>    analyzed class `C`'s own definition of `n`, when `C` defines it; **(ii)** otherwise to the unique
>    class in `C`'s transitive base closure that defines `n`; **(iii)** otherwise the gap stands
>    (`unresolved_delegate`, unchanged), and step (ii) refuses on more than one definition exactly as
>    condition 1 does. `derive_contract` already holds the entry point's own record at `depth == 0`
>    (`plr-sema/src/plr_sema/derive/__init__.py:635-636`), so `C` is threaded through `_walk_closure`
>    as an additive parameter; **no traversal semantics change.**
>
>    **At the pin this condition BITES, and it is what makes the mechanism correct rather than merely
>    different — round 1's C8.** `Resource._state_updated`'s own `self.serialize_state()`
>    (`external/pylabrobot/pylabrobot/resources/resource.py:934`) would otherwise resolve to
>    `Resource.serialize_state` (`external/pylabrobot/pylabrobot/resources/resource.py:838-849`) by
>    `resolve`'s existing class-first, same-module step, while the receiver is a `LiquidHandler` that
>    **overrides** it (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:214-237`).
>    Step (i) sends it to the override, which is the body that actually runs. Both carry zero guards, so
>    §17.8.3's cell is unchanged either way: **this condition closes a way the mechanism could be
>    wrong, not a number**, and AC-17.1 asserts it by name against a fixture where the two bodies
>    differ.
>
>    **Scoping matters and is deliberate.** The receiver-class-first step applies **only** inside bodies
>    M-INH newly admitted. A record reached the ordinary way is a method of the analyzed class itself,
>    where `resolve`'s step 1 already gives the right answer; changing resolution there would be a
>    benchmark-wide behavioural change this increment neither needs nor measures.

> **Normative (the direction of the change, said plainly because it cuts both ways — and one channel
> round 1 found that spec_version 1's box did not consider, C11).** Resolving a previously-unresolved
> call **adds** that function's guards to the closure. On `_state_updated` that is zero guards and 186
> findings disappear. Elsewhere on the surface it may be more than zero, in which case the benchmark
> gains `UNKNOWN` findings — the **sound** direction, and an honest one, but a direction that can cost
> decided findings and, in principle, increment 7's 216.
>
> **The second channel is subtler and is not about guards at all.** `_walk_closure` pushes
> `rec.delegates_to`, which the survey emits `sorted` (`scripts/survey_plr_preconditions.py:421`), so
> adding `_state_updated` to `pick_up_resource`'s and `drop_resource`'s lists changes push order, hence
> pop order, hence the **depth** at which unrelated delegates are inlined
> (`plr-sema/src/plr_sema/derive/__init__.py:445-459`). Depth gates `caller_args`,
> `caller_reachability_clear` and `caller_scope_trail`
> (`plr-sema/src/plr_sema/derive/__init__.py:640-651`) and D1's `WILL_FAIL` lift
> (`plr-sema/src/plr_sema/check/predicate.py:1092-1109`). **M-INH can therefore move guards into and out
> of the depth-1 population benchmark-wide with no guard body changing at all** — including on the 216
> `pick_up_tips` operations gate condition (4) protects. Closure size and guard count cannot detect
> that; the **per-guard depth multiset** can, `InlinedGuard.depth` is already on the wire
> (`plr-sema/src/plr_sema/derive/__init__.py:665-681`), and T50 publishes it before and after with
> AC-17.1 asserting it unchanged for every entry point whose newly-resolved set is empty.
>
> **That combined risk is why M-INH is a user decision (D9), why §17.8.2's gate makes the 216 a hard
> condition rather than a hope, and why T50 must precede T52 and T54.**

---

## 17.3 R-ARM — `self._resource_pickups`, and the truthiness clause

> **Normative (O3 — one additive observation field, and the record stays closed).** Increment 7 §16.2.1
> fixes the observation record's four fields and refuses growth by name. This increment adds **exactly
> one**, argued against §16.2.2's two tests and against its own third:
>
> | field | type | what it decides |
> |---|---|---|
> | `arm_slots` | a list of `int` | R-ARM — the key set of `self._resource_pickups`, which `:2055` reads |
>
> - **Against test (i), "is it quantified?"** No. It is the finite, enumerated key set of one dictionary
>   on one receiver, read at the single capture point after `await setup.machine.setup()` that §16.2.1
>   already fixes, and it is `sorted(self._resource_pickups)`. This is verbatim `head_channels`' own
>   argument, which §16.2.2 already calls the field to attack and already answers.
> - **Against test (ii), "does it assume the graph is the world?"** No. It is read *from* the executed
>   object, not inferred from an absence.
> - **Against §16.2.2's third test, "is it a function of the guard being decided?"** No, and this is the
>   one that needs care because the answer is closer than for `head_channels`. The guard evaluates the
>   dict's **truthiness**; the field is its **key set**. The harness could not compute the field only by
>   evaluating the guard — the guard's answer is one bit, the field is a set — but a reader is entitled
>   to note that one bit is derivable from the other. The distinction that makes it an observation
>   rather than the answer is that `arm_slots` is a **receiver-state** fact independent of any call,
>   whereas the refused `assert_resources_exist_passed` is a fact about one call's own outcome.
> - **`num_arms` is refused as an alternative**, by name. It would be R-ATTR's shape rather than
>   R-HEAD's, and it would decide `:2055` only through PLR's `setup` body — a claim about how the dict
>   is *built*, which is the argument §16.2.2 rejects for `head_channels`.
>
> The field enters `env` as an `obs:` member under §16.2.3's JSON encoding with **numeric** int sort,
> unchanged in every other respect, and a `None` observation contributes no member and makes R-ARM
> decline.

> **Normative (the STABILITY precondition, which is what "complete" actually requires — round 1's C16,
> conceded).** spec_version 1 argued `arm_slots` as *"a claim about what the dict contains at one
> instant"* and then used it to decide a guard at a **different** instant. That is not enough, and the
> gap is real at the pin: `_resource_pickups` is initialised empty
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:176`), `_resource_pickup`'s setter
> assigns `self._resource_pickups[0]`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:183-185`) — which **creates** key 0
> in an empty dict — and `setup` rebuilds the dict wholesale
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:212`) at a point the capture sits
> after. So a receiver whose backend declares zero arms would *acquire* a key at its first pickup.
>
> > **The property R-ARM's completeness declaration needs is: the key set of
> > `self._resource_pickups` is FIXED for the whole program after the observation capture point.** It
> > holds at this pin for every receiver with `num_arms >= 1`, because `setup` is the only wholesale
> > rebuild and the setter only ever writes a key the rebuild already created. It does **not** hold for
> > `num_arms == 0`, which is exactly the case an empty `arm_slots` names.
>
> **The rule is therefore stated with the empty case handled explicitly, not by omission.** An empty
> observed `arm_slots` makes the amended clause `F` — which is the *correct* answer for `:2055`'s
> `Not(...)` conjunct at the moment the guard runs, and stays correct for every later guard in the same
> operation because `:2055` raises before any pickup can create a key. AC-17.2 asserts the stability
> property directly: an operation sequence containing a pickup and a drop leaves
> `sorted(self._resource_pickups)` unchanged.

> **Normative (R-ARM, and the amended clause it needs).** `EnvRef(("self","_resource_pickups"), None)`
> resolves, inside `_resolve_env_ref` (`plr-sema/src/plr_sema/check/predicate.py:309-356`), to the `Seq`
> of `arm_slots`, under a new `rule` value `"R-ARM"` whose specification declares that `Seq`
> **complete** in exactly R-HEAD's sense and subject to the stability precondition above. In predicate
> position it decides by §17.1.2's amended clause: `T` iff non-empty, `F` iff empty, ½ when the
> observation is absent, when the record is partial, or when the path is any other shape. In **term**
> position it behaves exactly as R-HEAD's `Seq` does and gains no membership case: no guard at this pin
> tests membership in it, and admitting one that nothing reads is the growth §16.2.1's closed list
> exists to prevent.
>
> **R-ARM lands inside `_resolve_env_ref` and therefore costs nothing on D4's precedent
> (§17.7 item 1). The amended predicate-position clause lands in `evaluate_predicate` and therefore
> does NOT** — that separation is round 1's C14, conceded, and it is why D7 asks 10 → 12 rather than
> 10 → 11.

---

## 17.4 The `_resource_pickup` typestate

> **This section's every design choice is stated against increment 1's own, which is the only typestate
> in the analyzer.** Increment 1's four derived passes, its atom truth table
> (`plr-sema/src/plr_sema/check/tipstate.py:442-452`), its transfer function
> (`plr-sema/src/plr_sema/check/tipstate.py:490-518`) and its named assumptions
> (`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:744-754`) are the template; the one
> place this increment departs from it is §17.1.3's ordering problem, and the departure is argued
> rather than assumed.

### 17.4.0 How the state reaches a verdict

> **Normative (the route, stated for the first time in spec_version 2 — round 1's C6 and C10, and the
> single most consequential thing the round established).** spec_version 1 specified a lattice, an
> anchor shape, an effect table and an order, and never said **how the state reaches the evaluator**.
> The challenger inferred that it must go through `_resolve_env_ref` and `_eval_is`, and priced a fifth
> `EnvRef` path shape and a broadened `Is` rule. **Neither is needed, and the defender's rebuttal is
> adopted here as normative text**: the typestate reaches a verdict through `tipstate.py`'s own
> atom/truth-table/finding path, and `evaluate_predicate` is not touched by it at all.
>
> **What spec_version 2 got WRONG about that, and round 2's R2-C3 is conceded on it.** spec_version 2
> wrote the route as four steps of *already-shipped* machinery. It is not shipped: `consumed` indices
> are recorded in exactly one place, the **own-guards** loop, and that loop sits inside
> `if channels is not None:` with a matcher (`parse_own_atom`) that requires the receiver expression to
> be `self.<channel_attr>[<name>]` (`plr-sema/src/plr_sema/check/tipstate.py:570-582`;
> `_is_channel_subscript` at `:404-411`). The bare-`self` shape spec_version 2 named,
> `parse_bridge_atom` (`plr-sema/src/plr_sema/check/tipstate.py:469-480`), is used only in the
> `channel_guards` loop, which iterates a **different** wire field and records **no** consumed index
> (`plr-sema/src/plr_sema/check/tipstate.py:598-616`). And `move_lid`/`move_plate`/`move_resource`
> declare no `use_channels`, so `channels` is `None` and the own-guards loop does not run for a single
> move operation — the shipped docstring says an inexact channel set means the guard is "not
> tip-state-interpretable AT ALL" (`plr-sema/src/plr_sema/check/tipstate.py:553-566`). **The
> COMPONENTS are shipped and the REPLACEMENT PROTOCOL is shipped; the entry point that combines them
> for a channel-free anchor is not.** It is specified normatively here rather than left for T52 to
> invent.
>
> > **Normative (the new evaluator entry point, in seven closed decisions).**
> >
> > 1. **Name and module.** `evaluate_anchor_call`, a sibling of `evaluate_call` in
> >    `plr-sema/src/plr_sema/check/tipstate.py`, with `evaluate_call`'s own signature and return type —
> >    `(findings, consumed)` (`plr-sema/src/plr_sema/check/tipstate.py:521-543`) — so `plr_sema.check`
> >    consumes it through the protocol it already has: `_evaluate_guards_for_call` skips **any**
> >    consumed index unconditionally and for no stated reason
> >    (`plr-sema/src/plr_sema/check/__init__.py:451-453`), which is what makes the replacement
> >    reason-agnostic and is the part of spec_version 2's step 4 that survives intact.
> > 2. **Position.** It runs **before** `evaluate_call`'s two loops for the same CALL, and the union of
> >    the two `consumed` sets is returned to `plr_sema.check`. Anchor indices and channel indices are
> >    disjoint by construction — a guard whose condition matches
> >    `self.<channel_attr>[<name>]` cannot also match a bare-`self` anchor field — so the union needs
> >    no precedence rule, and AC-17.3 asserts the two sets disjoint on the tip fixtures.
> > 3. **No channel gate.** **The `channels is not None` gate does NOT apply to a channel-free anchor**
> >    (`plr-sema/src/plr_sema/check/tipstate.py:570-582` is the gate that is deliberately not reused).
> >    A singleton anchor has no channel set to be exact or inexact about; gating on one would make the
> >    mechanism unreachable on every `move_*` operation, which is exactly the defect R2-C3 found.
> > 4. **Matcher.** `_parse_atom` is reused unchanged
> >    (`plr-sema/src/plr_sema/check/tipstate.py:387-401`) with `base_ok` the bare-`self` test
> >    `parse_bridge_atom` already passes it
> >    (`plr-sema/src/plr_sema/check/tipstate.py:469-480`) and `state_fields` the singleton anchor's own
> >    field name from §17.4.2's published selection. **`bool_view_attr` has no analogue for this anchor
> >    and is passed the empty string**, which can never equal an `ast.Attribute.attr`, so
> >    `_parse_atom`'s bool-view branch is dead by construction and the only reachable atom is
> >    `_null_check`'s (`plr-sema/src/plr_sema/check/tipstate.py:413-425`). No third matcher function is
> >    added.
> > 5. **State source.** `AnchorWalk`, a per-receiver ordered-position walk in `TipWalk`'s own manner
> >    (`plr-sema/src/plr_sema/check/tipstate.py:128-190`), carrying one `PickupState` per receiver
> >    rather than a per-channel map, with §17.4.3's five widening conditions as its transfer function.
> >    It is a NEW class and it is what T52's ~110 LOC for "the ordered walk and the five widening
> >    conditions" buys.
> > 6. **DECISIVELY — `atom_truth` and `_finding_for_atom` are GENERALISED over both lattices, NOT
> >    duplicated.** Both take their state parameter as the union `TipState | PickupState`
> >    (`plr-sema/src/plr_sema/check/tipstate.py:442-452`, `:455-472`); `atom_truth`'s three existing
> >    productions — `bool_view`, `null_check(True)`, `null_check(False)` — are re-expressed against a
> >    two-states-and-a-top protocol both lattices satisfy, and **no new production is added**. The ½
> >    branch's reason becomes a parameter (§17.6's table), which is the ONE line of `_finding_for_atom`
> >    this increment changes. **A DUPLICATED `atom_truth` would break D7's arithmetic**: `_measure_hm25`
> >    returns `len(shape_matchers) + len(productions)` and `productions` is a tuple of *exercised
> >    `atom_truth` branches* (`plr-sema/src/plr_sema/_hand_maintained.py:529-553`), so a second lattice's
> >    branches would be two or three further productions, the measure would land at 14–15, and T52's own
> >    STOP contingency would fire. **Generalising keeps `productions` at 3, `shape_matchers` at 9 after
> >    T51's and T52's one each, and `measure()` at exactly 12 — which is what D7 asks for.**
> > 7. **Nothing else in `tipstate.py` moves.** `channels_for_call`, `fold_channels`, `_apply_transfer`,
> >    `parse_own_atom` and the `channel_guards` loop are untouched, and AC-17.3 asserts the tip
> >    family's own findings and reasons unchanged operation-for-operation.
>
> **Three consequences are normative.**
>
> - **No fifth `EnvRef` path shape and no new `Is`-position rule.** `EnvRef(("self","_resource_pickup"))`
>   never reaches `_resolve_env_ref` on this path, so §17.7's accounting is not short by one and the
>   benchmark-wide broadening of `_eval_is` (`plr-sema/src/plr_sema/check/predicate.py:851-856`) that
>   C6 feared is neither proposed nor needed.
> - **`_finding_for_atom`'s ½ branch must carry `guard_env_dependent` for this anchor**, not the tip
>   family's `channel_state_unknown` (§17.6's table). That is the ONE line of that function this
>   increment parametrises, and AC-17.3 asserts the tip family's own reason is unchanged.
> - **`_finding_for_atom` takes no `depth` argument and calls no `guard_is_unconditional`; its
>   `truth == "T"` branch returns `WILL_FAIL` directly**
>   (`plr-sema/src/plr_sema/check/tipstate.py:464-467`). That function's
>   `depth >= 2` refusal (`plr-sema/src/plr_sema/check/predicate.py:1092-1093`) governs the path this
>   REPLACES. **So §17.9's `p3a` mutable population is the full 93, not the 31 `move_resource`
>   operations** — C10's remedy would have written a wrong denominator into the floor, and it is
>   recorded as rebutted rather than adopted.
>
> **`n_typestate_decided` is published as a counter of its own** (§17.8.1 block 3), distinct from the
> state assignment, so "the state was computed" and "the state decided a guard" cannot be confused for
> one another in the measured report.

### 17.4.1 The lattice and the payload

Two states and a top, on a new enum **`PickupState`** (§17.4.0 decision 5): **`EMPTY`** (the field is
`None`), **`HELD`** (it is not), **`TOP`**. The join is
`TOP` on any disagreement, exactly `join_tip`'s shape, and the two-states-and-a-top protocol is what
§17.4.0 decision 6's generalised `atom_truth` is expressed against. `HELD` additionally carries an optional
**payload**: the `ir.Value` the pickup was constructed from, when the setting assignment's own argument
resolves to one, and `None` otherwise. **The payload never affects the three guards' truth** — §17.4.0
step 3 is why — it exists only so §17.1.5's refused-partial route has somewhere to live in increment 9,
and a `None` payload is always legal.

### 17.4.2 P5 — the singleton typestate anchor, derived by shape

> **Normative.** A receiver attribute `F` on the analyzed class is a **singleton typestate anchor** iff,
> over that class's own body: (a) at least one `ast.Assign` targets `self.<F>` with an `ast.Constant`
> `None` value; (b) at least one `ast.Assign` targets `self.<F>` with a non-`None` value; and (c) at
> least one guard in the derived contract table reads `self.<F>` through an `Is` node — the same
> `x is None` / `x is not None` shape `_null_check` already matches for the tip family
> (`plr-sema/src/plr_sema/check/tipstate.py:413-425`). **No attribute name is typed**, and the selection
> is published whole-surface with its count.

> **Normative (the absence rule, inherited from §16.3's C15 and extended for the hazard §17.1.3
> names).** An anchor candidate is **absent** — the whole mechanism declines for it — when any of three
> clauses holds:
>
> 1. `F` is also defined as a `property` **whose setter body is not a single assignment statement**;
> 2. `F` is assigned anywhere outside the analyzed class's own body;
> 3. **`<Class>.<F>` is defined at more than one lineno OTHER THAN as the getter/setter pair of one
>    `property`.**
>
> **Clause 3's exception is round 2's R2-C2, conceded, and it is a deliberate narrowing of the shipped
> rule rather than an oversight.** `_backend_surface_row_absent`'s own docstring says a getter/setter
> pair sharing a qualname "is caught by (3)"
> (`plr-sema/src/plr_sema/derive/receiver_state.py:1438-1440`), and read without the exception clause 3
> would make **this increment's only anchor absent** — `_resource_pickup` is exactly such a pair
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:178-185`) — which would leave
> `:2070`/`:2120`/`:2147` at ½ on 93 and fail gate condition (1). Two further things are stated because
> a fixer cannot resolve them from the text alone. **(a) Whose qualname clause 3 ranges over**: the
> **function** qualname `<Class>.<F>`, when `F` is a property (the only case in which `F` has function
> definitions at all); when `F` is a plain attribute the clause is **vacuous**, since an attribute has
> no `lineno`-bearing definition for the function index to count. **(b) Why the exception is safe**:
> clause 1 already adjudicates every property, on a strictly stronger test than a definition count —
> without the exception clause 3 would fire first in every case clause 1 exists to decide, and clause
> 1's narrowing argument could never be reached. A reading that renders a coordinate clause dead is not
> the one an implementer takes, and this makes that explicit instead of relying on it.
>
> At the pin `_resource_pickup` **is** a property, it is a two-definition getter/setter pair so clause
> 3's exception applies, and it survives clause 1 precisely because its setter is the single statement
> `self._resource_pickups[0] = value`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:183-185`) — which is a fact about
> PLR that the rule checks rather than assumes. **AC-17.3 asserts three fixtures, not one: the rule
> biting on a synthetic property whose setter does more (clause 1); the two-definition property pair
> asserted PRESENT (clause 3's exception); and a THREE-definition qualname asserted ABSENT (clause 3
> itself, which the exception must not swallow).**

### 17.4.3 P6 — effects, and the intra-operation order

> **Normative (the effect table).** For each anchor `F`, each `ast.Assign` to `self.<F>` in each
> function of the closure yields an **effect** at that assignment's own `lineno`: `EMPTY` for a
> constant `None`, `HELD` otherwise. An assignment in any other shape — an `ast.AugAssign`, a tuple
> target, a subscript — yields **`widen`**, exactly `_apply_transfer`'s own third case
> (`plr-sema/src/plr_sema/check/tipstate.py:505-518`).

> **Normative (the ordering, which is the whole of what is new here).** Within one operation the
> analyzer walks the entry point's own body in **source order**, and at each `self.<delegate>(...)`
> call statement it enters that delegate's effects and guards in **their** source order, recursively.
> Every guard in the flattened list therefore acquires a **position**, and the state at a guard is the
> fold of every effect at a strictly earlier position. `:2070` sits at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2069-2070`, before
> `pick_up_resource`'s own setting assignment at `:2072-2077`, so it reads `EMPTY`; `:2120` and `:2147`
> sit in delegates called after `pick_up_resource` returns
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2353-2377`), so they read `HELD`.

> **Normative (FIVE fail-closed widening conditions, and every one of them is a way a source-order walk
> could be WRONG). spec_version 1 had four; round 1 replaced condition 2 outright and added condition 5.**
>
> 1. **A conditionally-reached effect site widens.** If the call statement carrying an effect is not
>    unconditionally reached, the state becomes `TOP` from that position onward. **Where the
>    conditionality comes from is stated, because round 1 showed spec_version 1's answer did not exist
>    (C20).** A call statement has no `scope_trail`: `scope_trail` is a field of a
>    `PreconditionFinding` (`scripts/survey_plr_preconditions.py:100-108`), and the only per-call-site
>    scope data on the wire, `caller_scope_trail`, exists at `depth == 1` only. The trail is instead
>    computed from the AST by the **already-shipped** `compute_caller_scope_trail`, which takes a
>    function node and a call statement's own `lineno`
>    (`plr-sema/src/plr_sema/derive/bindings.py:1068-1075`), alongside `compute_reachability_clear`
>    (`plr-sema/src/plr_sema/derive/bindings.py:782-790`); each resulting entry is then tested by
>    `_entry_satisfies_uncond`'s ways (1)–(3)
>    (`plr-sema/src/plr_sema/check/predicate.py:1047-1057` — which is that function, not
>    `guard_is_unconditional`, whose own body begins at `:1060`; spec_version 1 mislabelled the
>    citation and the label is corrected here). This is what makes `move_picked_up_resource`'s in-loop
>    call site (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2361-2362`) safe: the
>    loop carries **no** effect, so nothing widens, and had it carried one it would have.
> 2. **A handler that can fall through widens; a handler that cannot, contributes nothing.** An
>    assignment to `self.<F>` lexically inside an `ast.Try` handler is folded into the ordered state
>    **iff** that handler cannot reach any position after the enclosing `try` — decided by the pure AST
>    shape test `isinstance(handler.body[-1], ast.Raise)` **and** the handler body containing no
>    `ast.Return`, `ast.Break` or `ast.Continue` at any depth; **otherwise it widens.** The same class
>    of shape test §17.4.2's absence rule already uses. A handler satisfying both halves contributes
>    **no** state to positions after the `try`, and its own assignment is therefore ignored rather than
>    folded. **Any other handler widens**: the state becomes `TOP` at every position after the
>    enclosing `try`.
>
>    > **The second half is round 2's R2-C6, conceded, and it closes the rule's ONE unsound
>    > direction.** A handler whose last statement is an `ast.Raise` but which contains an earlier
>    > `ast.Return` — or a `Break`/`Continue` inside an enclosing loop — can leave the handler
>    > **normally**, carrying the rolled-back state, so positions after the `try` would read `HELD`
>    > while the field is `None`. For this anchor that is a false `SAFE` on `drop_resource`'s
>    > `self._resource_pickup is None`
>    > (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2146-2147`) — the one failure
>    > mode §17.1.5 says the project exists to prevent. **At the pin the unfenced test was correct**:
>    > `pick_up_resource`'s handler is exactly the two statements `self._resource_pickup = None` and
>    > `raise e` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2090-2092`), with no
>    > earlier `Return`. But §17.8.1 block (3) publishes P5/P6's selection **whole-surface**, so the
>    > rule ships against handlers nobody has enumerated and the fence is owed. **The added clause errs
>    > safe in every case it changes** (it can only widen more often), so it cannot create a `SAFE` that
>    > the unfenced rule refused. ~2 LOC on top of condition 2's ~5.
>
>    > **This replaces spec_version 1's condition 2 outright, and the replacement is round 1's central
>    > pin-level finding (C4).** spec_version 1 made an in-handler assignment widen *unconditionally*,
>    > which at the pin puts `:2120` and `:2147` at `TOP` — because `pick_up_resource`'s rollback sits
>    > inside the `try/except` at
>    > `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2085-2092` and all three later
>    > positions are after it — while §17.8.3 predicted `SAFE` on 93 for both. **Both statements cannot
>    > hold, and that contradiction alone made spec_version 1's gate fail on all 93 operations.** The
>    > rescue the challenger identified — the handler's terminator is `raise e` at
>    > `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2092` — is a **control-flow**
>    > fact only if it is *asserted*; as a **shape test over `handler.body[-1]`** it is derived, in the
>    > same sense P5's property-setter test is derived. **So no new named assumption is added and the
>    > table stays at five rows.** ~5 LOC.
> 3. **An unresolved delegate widens.** A call the closure could not resolve may mutate `F`
>    invisibly. Note the interaction with §17.2, and it runs the **right** way: M-INH resolves calls
>    that today are gaps, so it strictly reduces the population that widens here.
> 4. **The initial state is `TOP` unless the graph supplies it.** Across operations the state is carried
>    by **`AnchorWalk`** (§17.4.0 decision 5) in `TipWalk`'s own manner
>    (`plr-sema/src/plr_sema/check/tipstate.py:128-190`),
>    resetting to `EMPTY` only where increment 1's own **A-COMPLETES** already licenses it
>    (`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:744-754`) and widening on any
>    receiver whose prior operations are not all decided.
> 5. **A guard reached at several positions takes the JOIN of the states at all of them**, which is
>    `TOP` on any disagreement. **This is round 1's C5, conceded as a soundness hardening.** The
>    contract table carries one guard entry per key — `derive_contract` emits `rec.findings` once per
>    popped key and `_walk_closure` visits each key once
>    (`plr-sema/src/plr_sema/derive/__init__.py:445-459`, `:652-681`) — while the walk above assigns
>    positions to **call statements**, and a delegate called twice executes at two positions. At the pin
>    this does not bite: each of `:2070`, `:2120` and `:2147` sits in a function with exactly one call
>    site in the move closure. It bites for `_check_args` (three positions) and, after M-INH, for
>    `_state_updated` (two, at `HELD` and at `EMPTY`), neither of which reads an anchor — so the
>    condition costs nothing at this pin and closes the case where a future anchor-reading guard would
>    otherwise get one entry for two disagreeing pre-states.

> **Normative (NO new named assumption is added, and this is the strongest property this increment
> has).** The assumption table stays at **five** rows. Every claim §17.4 makes is either derived (P5's
> and P6's shapes, the source-order walk, the five widening conditions, the handler-terminator test) or
> already licensed by an existing assumption: **A-SINGLE** for one receiver variable denoting one
> instance, **A-COMPLETES** for the inter-operation initial state
> (`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:744-754`). **Round 1 attacked this
> claim first, as spec_version 1 invited it to, and found a real falsification in condition 2 —
> which is why condition 2 now tests a shape instead of asserting a fact.** AC-17.3 requires the next
> round to try again, and if it succeeds the assumption must be named before the row lands.

---

## 17.5 M3 — the constant-argument map at any depth, and the `:383` refusal

### 17.5.1 M3

> **Normative (the clause accounting, corrected — round 2's R2-C11, conceded on citation precision).**
> `compute_caller_args` refuses a `(K, D)` pair outright on **clauses 1/2** — no single self-rooted
> call site, `_find_delegate_call`'s `return calls[0] if len(calls) == 1 else None`
> (`plr-sema/src/plr_sema/derive/bindings.py:966-968`, via `:884-886`) — and on **clause 4**, which is
> **three** separate refusals, of which §17.5.2's derivation uses one
> (`plr-sema/src/plr_sema/derive/bindings.py:969-975`: call-side `ast.Starred`, call-side `**`
> unpacking, and `D` itself declaring `*args`/`**kwargs`). Clauses 3 and 5 are enforced per-argument
> inside the loop and never reach the whole-pair `None`. **Clause 6 (`depth == 1`) is not in that
> function at all** — its own docstring says so, "it has no `depth` parameter at all"
> (`plr-sema/src/plr_sema/derive/bindings.py:944-948`) — and the gate lives in `derive_contract`
> (`plr-sema/src/plr_sema/derive/__init__.py:640-651`). spec_version 2 cited `:931-941`, which is the
> docstring rather than the refusals, and said "two grounds relaxed, four untouched"; **this increment
> relaxes clauses 1/2 (into a site LIST) and clause 6 (for constant arguments only), and touches
> clause 4 not at all.**
>
> **(a) The single-call-site refusal becomes a per-site LIST over the WHOLE CLOSURE.** This is the
> half round 1 broke (C2, conceded by the defender as *"the true blocker"*), and it is re-derived
> rather than patched.
>
> > **What was wrong.** `derive_contract` computes `compute_caller_args(entry_K, K)` where `entry_K` is
> > the **entry point**, captured once at `depth == 0`
> > (`plr-sema/src/plr_sema/derive/__init__.py:635-651`), and `_find_delegate_call` scans **`K.body`
> > only** (`plr-sema/src/plr_sema/derive/bindings.py:884-886`). `move_lid`'s body contains exactly two
> > self-calls — `_log_command` and `move_resource`
> > (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2415-2437`) — and no
> > `_check_args` call at all. **So lifting the depth restriction alone binds NOTHING for `move_lid`,
> > `move_plate`, `transfer`, `discard_tips` or `stamp`: 142 of the 173 spec_version 1 called
> > "certain".** §17.5.1(b) said *"the argument at the call site"* without ever saying whose body the
> > call site is in, and the shipped signature answers: the entry point's.
>
> **The rule.** For a delegate `D` reached anywhere in entry point `E`'s closure, the **admitted
> call-site set** is every `self.<D.name>(...)` call statement in the body of **every** record the
> closure walk visited whose own `delegates_to` resolves to `D`'s key. It is computed in a **second
> pass over `_walk_closure`'s already-visited node set**, with each caller record's own `K` taken from
> the SAME `function_index` `derive_contract` already holds
> (`plr-sema/src/plr_sema/derive/__init__.py:630-651`). **`_walk_closure`'s traversal semantics — LIFO,
> depth-carrying, `seen`-deduplicating — are NOT changed** (`plr-sema/src/plr_sema/derive/__init__.py:444-459`);
> the parentage C2 asked for is recovered afterwards, from data the walk already produced, rather than
> by re-specifying the walk.
>
> > **Normative (the second pass's exact SHAPE, because the visited set is not exposed — round 2's
> > R2-C12, conceded).** `seen` is a generator-local set inside `_walk_closure` and is neither returned
> > nor exposed (`plr-sema/src/plr_sema/derive/__init__.py:445-451`), and `derive_contract` constructs
> > and appends each `InlinedGuard` **inside** the walk loop
> > (`plr-sema/src/plr_sema/derive/__init__.py:665-681`) on a frozen, slotted dataclass
> > (`plr-sema/src/plr_sema/derive/__init__.py:462-463`), so there is no already-visited node set to
> > make a second pass over and no mutable guard to revise. **The shape is therefore: (i)** during the
> > existing single pass, buffer each `(rec, key, depth)` triple into a list, together with that
> > record's findings, and construct **no** `InlinedGuard` yet; **(ii)** after the walk returns,
> > resolve the per-`(entry point, delegate)` admitted call-site sets from that buffered list;
> > **(iii)** emit every `InlinedGuard` in a second loop over the buffer, with `caller_args_sites`
> > populated. **No `dataclasses.replace` and no mutable guard** — the frozen dataclass stays frozen,
> > and `derive_contract`'s output order is preserved because the buffer preserves the walk's own
> > order. The restructure is T54's and is inside its ~300 LOC; T50 and T52 also modify
> > `derive_contract`, which is a second reason §17.11 orders T50 before T54.
>
> `caller_args` becomes, additively, a **list** of per-call-site maps — one entry per admitted call
> site, each carrying its own `lineno`, its own caller qualname, and its own parameter map, computed
> against **that site's own caller** `K_i` (never against `entry_K`) with the alpha substitution
> position-gated at that site's own lineno, exactly as `compute_caller_args` already does for the
> depth-1 case (`plr-sema/src/plr_sema/derive/bindings.py:981-996`). A **site rule** reading the list
> evaluates **once per entry** and folds **conjunctively**: `F` iff every entry yields `F`, ½ if any
> entry declines.
>
> **Why the conjunctive fold over the CLOSURE's sites is sound, stated as the whole argument.** The
> collected set is a **superset** of the call sites actually executed during one operation — some lie
> on paths the operation does not take. A conjunctive fold over a superset is strictly more
> conservative than the same fold over the executed subset: requiring `F` everywhere is a stronger
> demand than requiring `F` where it runs. The guard genuinely executes once per executed call site, so
> `SAFE` requires `SAFE` at all of them; ranging over more of them can only decline more often, never
> decide more often. **This is what makes the residual uniform across all 93** — the three sites
> `move_resource` reaches (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2345-2350`,
> `:2364-2369`, `:2079-2081`) are exactly the three `move_lid` and `move_plate` reach, one hop further
> out.
>
> **Two fail-closed conditions on the site set, because an INCOMPLETE site set is the one way this
> could be unsound.**
>
> 1. **An unresolved self-call anywhere in the closure makes the fold decline.** A record with a
>    non-empty `unresolved_calls` (`scripts/survey_plr_preconditions.py:140`) may reach `D` by a
>    path the closure never walked. **This is a hard ordering dependency on M-INH**: every move-family
>    closure carries two such calls today, so **T50 must land before T54** or M3 decides nothing on the
>    family it was written for. §17.8.1 block (5) publishes the decline count under this condition.
> 2. **A visited record with no `K` makes the fold decline.** A body the function index cannot supply
>    is a body that could call `D` unseen.
>
> **One residual soundness gap is named rather than closed, because it is not this increment's and is
> not made worse by it.** A call to `D` through a receiver expression that is not bare `self` — which
> the survey records in `dropped_calls` and neither M1 nor M3 models
> (`scripts/survey_plr_preconditions.py:268-288`) — is invisible to the site set, exactly as it is
> invisible to the shipped single-site rule and to the entire `delegates_to` closure the contract table
> already rests on. **M3 inherits that gap unchanged; it does not widen it.**
>
> **(b) The `depth == 1` restriction is lifted for CALL-SITE-CONSTANT arguments only.** A `(K_i, D)`
> pair at any depth `d ≥ 1` binds a parameter iff the argument at that call site parses as a `Term`
> whose free names are **empty** — a constant, a `SetLit` of constants, or a `self`-rooted `EnvRef`.
> Every other argument binds nothing at `d ≥ 2`, exactly as today.
>
> **Why the lift is NARROWER than the depth-1 map D1 already permitted, and not wider.** M1's clause 6
> exists because resolving a caller-side **name** requires the caller's namespace, and only the entry
> point's namespace is available (`plr-sema/src/plr_sema/derive/__init__.py:610-621`). A call-site
> constant is resolved against **no namespace at all**: it is a literal in that call site's own source
> text, and the chain of intermediate frames it passes through cannot change it. **The restriction
> genuinely does not apply**, and this document states that as the whole of the argument rather than
> appealing to measurement.
>
> **The pin makes this exact, and there are ELEVEN call sites, not ten (round 1's C18, conceded).**
> `self._check_args(` occurs at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:541-546`,
> `:687-692`, `:1037-1042`, `:1238-1243`, `:1481-1483`, `:1559-1561`, `:1745-1747`, `:1895-1897`,
> `:2079-2081`, `:2345-2350` **and `:2364-2369`** — the last being `move_resource`'s second site, whose
> distinct `default={"drop"}` the per-call-site fold argument depends on and which AC-17.5 asserts by
> name. spec_version 1's "all ten" omitted it, and the frontmatter's "eight of the ten" inherited the
> undercount. At every one of the eleven: `method` is a `self`-rooted `EnvRef`, `default` is a `SetLit`
> of string constants, and `strictness` is either a module-level `Attr` or a bare call — neither a
> `Term`, so neither binds, at any depth. **`backend_kwargs` is a bare caller-side name and is
> deliberately NOT bound by M3** at `d ≥ 2`; §17.5.2 is why that matters and why `:383` is refused.
>
> **The wire-shape change, named on the PRODUCER side (round 1's C13, conceded).** spec_version 1
> specified only the consumer's tolerance. All three shipped consumers call `.get(...)` on a `Mapping`
> — `caller_args.get("method")` (`plr-sema/src/plr_sema/check/predicate.py:1240-1249`),
> `caller_args.get("default")` (`plr-sema/src/plr_sema/check/predicate.py:1222-1231`), and
> `_Ctx.caller_args = guard.get("caller_args")`
> (`plr-sema/src/plr_sema/check/predicate.py:1425-1432`) — and a list has no `.get`, so **re-typing the
> existing key breaks all three**. The list is therefore a **NEW wire field, `caller_args_sites`**,
> beside the existing `caller_args`, which keeps its shape and its `depth == 1`-only population
> unchanged. Both site rules read `caller_args_sites` when present and fall back to `caller_args`
> otherwise, so a pre-T54 contract table behaves exactly as today. The additive field participates in
> `contracts_sha` automatically and therefore cools the cache by design; `test_cache.py` must assert
> the round trip preserves per-site linenos and that a table carrying only `caller_args` still decides
> `:375` for `pick_up_tips`.
>
> **What M3 does NOT touch.** `caller_reachability_clear` and `caller_scope_trail` stay strictly
> `depth == 1` and strictly entry-point-relative, and so does D1's `WILL_FAIL` lift.
> **M3 binds names; it licenses no new `WILL_FAIL` anywhere.** That separation is what keeps this
> increment out of increment 5 §14.6 R1's risk direction entirely.

### 17.5.2 `:383` on the move family — REFUSED, and the refusal is derived at the pin

> **Normative (D5a production (5) is NOT taken, and D10 is recommended NO — a reversal of
> spec_version 1).** Increment 7 §16.1.1 priced D5a as five productions and made it increment 8's.
> spec_version 1 took production (5) — a representation of the residual `**kwargs` key set — on the
> ground that it was the only route to `:383` on this family. **Re-deriving §17.5.1's fold showed that
> it does not reach, and a production that buys zero operations is exactly the trade §9.4 forbids —
> the same argument spec_version 1 itself used to refuse the enum-constant `Term`.**
>
> **The derivation, in three steps.** `:383`'s shipped rule discharges only on `has_var_keyword`
> (`plr-sema/src/plr_sema/check/predicate.py:1291-1326`), which is `False` for every backend method the
> move family reaches (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:223-231`).
> The proposed second route would return `F` when the call site's `backend_kwargs` argument resolves to
> an **empty complete `Seq`**.
>
> 1. At `move_resource`'s own two sites the argument is literally the entry point's `**kwargs`
>    parameter (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2345-2350`,
>    `:2364-2369`), so the route would fire — `F` at both.
> 2. At the **third** site, inside `pick_up_resource`
>    (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2079-2081`), the argument is
>    `pick_up_resource`'s **own** `**backend_kwargs` parameter, which is a different name binding that
>    happens to share a spelling. It is bound from the caller only through
>    `await self.pick_up_resource(..., **pickup_kwargs)`
>    (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2353-2359`) — a call-side `**`
>    unpacking of a local assigned from a dict comprehension
>    (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2351`). **M1 clause 4 refuses
>    call-side `**` unpacking outright** (`plr-sema/src/plr_sema/derive/bindings.py:966-975`), and M3
>    does not relax clause 4.
> 3. §17.5.1's fold is conjunctive over **every** admitted site, so one declining site makes the whole
>    fold ½. **`:383` stays ½ on all 93 move operations however production (5) is written.**
>
> **What it would actually cost to reach `:383` here, priced so increment 9 can decide.** Three further
> productions on top of production (5): a relaxation of M1 clause 4 propagating a `**<name>` unpacking
> into the callee's VAR_KEYWORD parameter with its own soundness argument; a local-binding idiom
> admitting a `DictComp` assignment, which §15.3's alpha/beta idioms do not cover; and the
> comprehension-emptiness rule production (5) already needed. For `move_lid`/`move_plate` there is a
> fourth hop, since they reach `move_resource` through the same `**backend_kwargs` unpacking
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2427-2437`, `:2495-2505`). **Four
> productions, four hops, one site, on a family where five other sites remain regardless.** That is
> increment 9's, behind D10, recommended **NO**.
>
> **The route round 1 was right about, recorded because it was not spec_version 1's argument.**
> C1 attributed the failure to M1 clause 4 sitting on `move_lid`'s own `**backend_kwargs` hop. The
> defender's correction is adopted: the spec never proposed propagating kwargs through that hop, and
> `_eval_check_args_strict_site_rule` reads only the argument map, which is unavailable at the guard for
> the reason C2 names. **The conclusion — `:383` does not reach 62 of 93 — was right; here it is right
> on all 93, and for a third reason neither report named.**

> **Normative (the completeness claim production (5) rests on is a PRECONDITION and is currently
> UNSUPPORTABLE IN BOTH LANES — round 1's C7, conceded, and an independent reason for the refusal).**
> spec_version 1 asserted, uncited, that an operation's keyword set is *"total in the IR, not a lower
> bound"*. It is not. In the graph lane, `lower_kwargs` keeps a keyword's real name only when it is in
> the per-contract `trusted` list and otherwise stores it under the synthetic key `f"?{i}"`
> (`plr-sema/src/plr_sema/check/ir.py:577-590`); the tier-1 lane does the identical rename
> (`plr-sema/src/plr_sema/check/ir.py:793-806`); and `param_names is None` — documented as *"trust
> nothing — fail-closed default"* (`plr-sema/src/plr_sema/check/ir.py:385-391`) — renames **every**
> key. The rename half fails **SAFE**, since a synthetic key is never a declared parameter and the
> residual `Seq` becomes spuriously non-empty; the dangerous half is a keyword the extractor never
> modelled, which is absent from `arguments` entirely and makes the residual `Seq` falsely **empty**.
> **Were D10 ever taken, the Term must DECLINE — not assert emptiness — whenever any `?<i>` key is
> present or `param_names` is absent**, and `lower_kwargs`'s existing `Widen(reason=_ARGUMENTS)`
> (`plr-sema/src/plr_sema/check/ir.py:592-601`) is the shipped signal that precondition hangs on.
> Increment 9 owes a graph-lane negative fixture, not only a tier-1 one, per §16.5.6.

> **Normative (a route considered and REFUSED, recorded so the round does not have to find it).**
> `move_resource` passes `strictness=Strictness.IGNORE` literally
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2345-2350`), and an enum-constant
> `Term` plus an equality rule would make `:383`'s own predicate `F` at those two sites without any
> scope reasoning. **It does not close the site**, for the identical reason production (5) does not:
> the same closure reaches `_check_args` from `pick_up_resource` with `get_strictness()`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2079-2081`) — a non-`self`-rooted
> call that is not a `Term` under G1 — so §17.5.1's fold declines there. **One production, bought for
> nothing**, and the enum-constant `Term` is refused by name in §17.12.

---

## 17.6 Reasons

> **Normative: `REASON_VOCABULARY` does NOT change. It stays at 12 of 12, HM-14's `declared` stays 12,
> and no thirteenth member is proposed.** The vocabulary is
> `plr-sema/src/plr_sema/verdict.py:147-199`. Every give-up point this increment adds folds into an
> existing member, mechanically:
>
> | new give-up point | member | why it is that member and not a new one |
> |---|---|---|
> | R-ARM declines (no observation, or a partial record) | `guard_env_dependent` | ≥ 1 free name resolves to state outside the call — the member's first clause, verbatim |
> | the typestate is `TOP` at a guard's position | `guard_env_dependent` | the guard reads instance state the analyzer did not establish; the tip family's own `channel_state_unknown` is **per-channel** and this anchor has no channels — which is the one line of `_finding_for_atom` §17.4.0 parametrises |
> | a per-call-site fold in which one site declines | `guard_env_dependent` | unchanged from the single-site decline it generalises |
> | the fold's site set is incomplete (§17.5.1's two conditions) | `guard_env_dependent` | the same clause; the guard's own `missing` still resolves `(Top, "env")` |
> | M-SURF attaches no surface to an entry, **or the surface carries no row for the looked-up `(class, method)` pair** (§17.1.4's selection half, round 2's R2-C1) | `guard_env_dependent` | unchanged — this is today's behaviour for all 321, and `_check_args_surface_row` already returns `None` in both cases, so neither give-up point is new |
> | an inherited call whose base chain is ambiguous, whose base name is unreadable, or whose name collides across modules | `unresolved_delegate` | **unchanged** — this is the member's existing meaning and the reason it is not retired |

> **Normative (`unresolved_delegate` goes to ZERO POPULATION and is explicitly NOT retired).** After
> §17.2 no operation on this benchmark carries the reason, and a retirement would look like tidiness.
> It is refused: the member is the sound fallback for a call that genuinely cannot be resolved, §17.2's
> four fail-closed conditions each produce exactly that case, and a benchmark on which a fallback never
> fires is not evidence the fallback is dead. **T55 publishes `unresolved_delegate == 0` as a
> measurement and AC-17.6 asserts the member is still present in the vocabulary.**

---

## 17.7 Registry

**New rows: ZERO, in every branch of every decision hook. `live_rows()` stays 25
(`plr-sema/src/plr_sema/_hand_maintained.py:1152-1156`) against `BUDGET_CAP = 25`
(`plr-sema/src/plr_sema/_hand_maintained.py:49`); headroom 0, unchanged; no cap conversation.** That
constraint shaped the increment rather than being satisfied after the fact, and §17.12 records the
mechanisms it excluded for costing a row.

> **Normative (the ONE proposed spend, and it is TWO units rather than spec_version 1's one — D7,
> HM-25 `declared` 10 → 12).** Round 1's C14 and C15 are both conceded, and together they move the ask
> up rather than down, which is why this box states them as the argument rather than burying them in
> §17.16.
>
> **Unit 11 — the amended predicate-position clause (§17.1.2).** spec_version 1 argued this rode D4's
> tenth unit for free. It does not. HM-25's tenth unit is booked for *"an `EnvRef` path admitted
> against the observation record"* and its probe imports and exercises `_resolve_env_ref`, *"the ONE
> symbol implementing all three rules"* (`plr-sema/src/plr_sema/_hand_maintained.py:350-362`,
> `:391-412`). **R-ARM lands inside `_resolve_env_ref` and genuinely rides that unit — but the amended
> clause lands in `evaluate_predicate` (`plr-sema/src/plr_sema/check/predicate.py:934-944`), which no
> HM-25 probe imports or exercises.** D7 is recommended YES on HM-25's LOUD-failure property, and that
> property does not extend to a rule no probe touches. **Booking it as its own unit, with its own probe
> importing `evaluate_predicate` and asserting a complete-`Seq` `EnvRef` decides while a `("self","head")`
> one still does not, is what keeps the row from becoming HM-24's silent-collapse mode in disguise.**
> spec_version 1 also treated two structurally identical cases in opposite directions — the truthiness
> clause free, the residual-kwargs Term riding D7 — and the asymmetry ran in the direction that lowered
> the ask. It is removed here in both places: the clause is charged, and the Term is refused outright
> (§17.5.2).
>
> **Unit 12 — §17.4's P5 anchor shape and P6 effect shapes.** Hand-written syntactic patterns over how
> PLR is written — an assignment-pair shape, an `Is`-read requirement, a property-setter absence rule
> with clause 3's getter/setter exception, and a handler-terminator test with its
> `Return`/`Break`/`Continue` fence — in exactly the sense HM-25's own `why_not_derived` uses, and in
> exactly increment 1 P2's class, which is already the row's first entry
> (`plr-sema/src/plr_sema/_hand_maintained.py:1000-1054`). One further collective unit for the
> **pattern**, not one per shape.
>
> > **Normative (unit 12's scope over §17.4.0's named symbols, re-stated at spec_version 3 — round 2's
> > R2-C3, and the arithmetic re-check the round-2 defender asked for).** §17.4.0 now names five new
> > symbols: `evaluate_anchor_call`, `AnchorWalk`, the `PickupState` lattice, the singleton
> > anchor/effect matcher, and the generalised state parameter on `atom_truth`/`_finding_for_atom`.
> > **Exactly ONE of them is a hand-maintained pattern and therefore inside unit 12**: the singleton
> > anchor/effect matcher, which is the distinct symbol C15 requires T52 to add and import. The other
> > four are **code** — an evaluator entry point, a walk class, an enum, and a widened type annotation
> > — in the same sense M3's traversal and the base-name extractor are code, so they cost no unit.
> > **The measure lands at 12, and here is the arithmetic in full.** `_measure_hm25` returns
> > `len(shape_matchers) + len(productions)`, today 7 + 3 = 10
> > (`plr-sema/src/plr_sema/_hand_maintained.py:529-553`). T51 adds **one** matcher (unit 11's
> > `evaluate_predicate` probe) → 8. T52 adds **one** matcher (unit 12's singleton anchor/effect
> > matcher, distinct from `_typestate_anchor`) → 9. **`productions` stays at 3** because §17.4.0
> > decision 6 GENERALISES `atom_truth` over both lattices instead of duplicating it — its three
> > branches (`bool_view`, `null_check(True)`, `null_check(False)`) are re-expressed, not re-added.
> > 9 + 3 = **12**, exactly D7's `declared`, and the `measure() <= declared` ratchet passes
> > non-vacuously. **Had T52 duplicated `atom_truth` for the EMPTY/HELD lattice** its branches would be
> > two or three further productions, the measure would land at **14–15**, and T52's STOP contingency
> > below would fire — which is why decision 6 is stated normatively rather than left to the
> > implementer.
>
> **The measure is mechanical, and that is why unit 12 must name a NEW symbol.** C15's premise that
> `_measure_hm25` returns a hand-written integer is **false** — it returns
> `len(shape_matchers) + len(productions)` (`plr-sema/src/plr_sema/_hand_maintained.py:529-553`), so the
> `measure() <= declared` ratchet genuinely checks the STOP contingency. **C15's surviving half is
> right and is binding**: `_typestate_anchor` is *already* in `shape_matchers`
> (`plr-sema/src/plr_sema/_hand_maintained.py:414-422`), so a P5 implemented as a variant of it adds no
> new symbol and the twelfth unit would pass the ratchet **vacuously**. T52 must therefore add a
> **distinct** symbol — the singleton-anchor/effect matcher — and import it. **If the measured count
> would exceed 12, T52 STOPS and surfaces a further spend to the user rather than raising `declared` on
> its own authority**, which is the contingency increments 6 and 7 both wrote and this one inherits
> verbatim.

> **Normative (four things that cost NOTHING, each argued rather than asserted, and each stated so a
> reviewer can break it).**
>
> 1. **R-ARM costs nothing**, on **D4's own precedent**, and now for a verified reason rather than an
>    assumed one. §16.9's D4 box states that the unit buys *"an `EnvRef` path admitted against the
>    observation record"* as a **pattern**, explicitly *"not one per instance"*, and its probe exercises
>    `_resolve_env_ref` — the exact function R-ARM's new path shape lands inside
>    (`plr-sema/src/plr_sema/check/predicate.py:336-356`). It is a fourth instance of an identical
>    pattern inside the identical symbol. **The objection spec_version 1 named against itself — that the
>    amended predicate-position clause is an evaluator rule rather than a path shape — was RIGHT, and
>    the clause is now charged separately as unit 11.**
> 2. **M-INH costs nothing.** A transitive base closure over PLR's own recorded class bases, keyed on a
>    shipped whole-tree index, introducing no literal. Same class as `is_dynamic_raise`,
>    `reachability_clear` and §16.3's derived backend surface. **The base-name extractor §17.2 specifies
>    is derived too** — three AST shapes and a refusal, no PLR name.
> 3. **M3 costs nothing.** A shape test over `ast.Call` and `ast.arguments`, fail-closed on every
>    unrecognised shape, adopting the restrictions M1 already states rather than inventing any — which
>    is verbatim §16.9's own item (2) for the depth-1 map. The whole-closure site collection adds
>    traversal *code*, not a hand-maintained *pattern*.
> 4. **M-SURF costs nothing, and it is the clearest case on this list.** It changes one boolean filter
>    in `derive/__main__.py` to scan the same `caller_args` structure `collect_env_ref_method_names`
>    already scans (`plr-sema/src/plr_sema/derive/receiver_state.py:1470-1500`). It introduces no
>    pattern, no literal, no row and no unit; it removes an asymmetry between two halves of one shipped
>    rule. **AC-17.4 asserts a grep finds no method name typed anywhere in the change.**
>    **§17.1.4's SELECTION extension costs nothing on the identical argument**, and it is stated
>    separately because it is a different function in a different module: it adds one more JSON
>    location — `caller_args_sites` — to the two `collect_env_ref_method_names` already walks with the
>    same `predicate_from_json`/`predicate_walk` pair
>    (`plr-sema/src/plr_sema/derive/receiver_state.py:1486-1501`). No pattern, no literal, no method
>    name; the names it admits come from the derived contract table exactly as today's do, and
>    **AC-17.5 asserts the same no-literal grep over T54's change.**

> **Normative (HM-26 is untouched, in every branch).** `_measure_hm26` counts `len(D6_SITE_RULES)`
> (`plr-sema/src/plr_sema/_hand_maintained.py:437-454`), and the dict's three keyed `(qualname, lineno)`
> pairs are unchanged (`plr-sema/src/plr_sema/check/predicate.py:1333-1337`). M-SURF changes what the
> `:375`/`:383` rules can READ, not how many rules there are, and M3 changes the shape of one field they
> read. No fourth keyed site is added. **HM-26 stays at `declared` 3**, and AC-17.5 asserts it.

---

## 17.8 Measured sets and the gate

### 17.8.1 What T55 publishes

> **Normative.** The measured report publishes, over the frozen benchmark and the regenerated contract
> table, **eleven** blocks. Blocks (4) and (10) are new in spec_version 2; block (1) gains the depth
> multiset and a fourth refusal count; block (9) gains the collision count. **At spec_version 3 block
> (4) gains the surface's four ROW-level counters** (round 2's R2-C8) — the block count stays at
> eleven and no block is added.
>
> 1. **M-INH's complete measured selection**: every `(class, name)` pair newly resolved by
>    inheritance, its unique defining base, and — separately — the count **refused** by each of §17.2's
>    four fail-closed conditions plus the two extractor refusals (unreadable base expression, bare-name
>    collision). Plus, per entry point, the closure size, the guard count **and the per-guard `depth`
>    multiset**, before and after, so §17.2's doubling bound is checkable and C11's silent depth
>    perturbation is visible rather than inferred.
> 2. **`n_resolved_by_rule` and `n_declined_by_rule` for R-ARM**, per lane (tier 1, tier 2b),
>    alongside the existing R-HEAD/R-ATTR/R-CONST block, and `n_seq_truthiness_decided` for
>    §17.1.2's amended clause — the one evaluator rule this increment adds, which must have a counter
>    of its own rather than hiding inside R-ARM's.
> 3. **The typestate's complete measured selection**: every anchor candidate, every one removed by
>    §17.4.2's absence rule with which clause removed it, the per-guard state assignment for all three
>    move sites, `n_typestate_decided` (guards the state actually decided, distinct from guards it was
>    computed for), and `n_typestate_widened` broken down by which of §17.4.3's **five** conditions
>    widened it.
> 4. **M-SURF's measured selection, AND the surface's ROW-LEVEL counters**: `n_entries_with_backend_surface`
>    before and after, the complete list of newly-attached contract keys, and `n_resolved_by_rule` for
>    **R-CONST** before and after — which §17.1.4's blast-radius argument predicts **unchanged**, and
>    which is the cheapest falsification of that argument. **Plus, new at spec_version 3 and the
>    cheapest falsifier of §17.1.4's SELECTION half (round 2's R2-C8): `n_surface_candidates`,
>    `n_surface_absent_by_c15`, `n_surface_rows` and the sorted `rows` key list, each before and
>    after** — all four are already shipped fields of the payload
>    (`plr-sema/src/plr_sema/derive/__main__.py:320-325`), and their pin values are 160 / 71 / 89
>    (`plr-sema/data/derived_contracts.json:3-6`). **None of the attachment-level counters moves when a
>    ROW is missing**, which is exactly how spec_version 2 could publish a healthy block (4) while
>    `:375` stayed ½ on 93; these four move, and they move at T54 rather than T53. Published per row so
>    the two halves are separately attributable: **T53 must leave all four unchanged at 160 / 71 / 89**
>    (it touches attachment only), and **T54 must move them to exactly 172 / 73 / 99** with
>    `drop_resource` newly present in the key list — §17.1.4's blast-radius box derives those three
>    figures from `pick_up_resource`'s measured twin (twelve definitions, two `@abstractmethod`, ten
>    rows) and this block is where the derivation is confirmed or falsified.
> 5. **M3's measured selection**: every `(K_i, D)` pair now admitted at `depth ≥ 2`; for every
>    `(entry point, delegate)` pair, the complete admitted call-site set with each site's lineno and
>    caller qualname; the conjunctive fold's outcome per site rule; the count declined by each of
>    §17.5.1's two site-set conditions; and the count still refused by each surviving M1 clause.
> 6. **`n_check_args_decided`**, split by which discharge route decided it — `has_var_keyword`, the
>    argument map, or neither — per site and per method. **This is the block that CONFIRMS or falsifies
>    §17.1.4's now-closed diagnosis**, and it must name the decline reason per operation for any of the
>    321 that do not clear.
> 7. **Per executed operation**: `verdict`, `scope_verdict`, the residual reason set, and the list of
>    non-excluded sites carrying an `UNKNOWN`. **The gate is computable from this block alone, without
>    reading this document.**
> 8. **The fence**: `unsound` and `unsound_scoped`, both unmodified in definition, with
>    `rows_excused_by_scope` and `rows_excused_by_frame` and every excused row's captured frame list.
> 9. **The after-ledger delta** against `outputs/plr-sema/unknown_ledger_260909_final.json`, on
>    `n_findings_by_reason`, `n_clusters`, `per_op_reason_set_histogram` and the per-method
>    `residual_site_sets`, with `consistency.ok` true — **plus `n_row_id_collisions` before and after,
>    with a sentence on whether a collision can double-count an operation in the gate's denominator of
>    93** (§17.0.1's provenance box, round 1's C19).
> 10. **`n_scope_excluded` per site, before and after, with every newly-excluded site named.** E-SCOPE
>     exclusions are invisible today: `excludes_sites` collects tier-(iii) sites only
>     (`plr-sema/src/plr_sema/check/__init__.py:932-949`), while `scope_excludes` returns `_SAFE`
>     directly (`plr-sema/src/plr_sema/check/predicate.py:1442-1444`) and leaves no trace. The counter
>     needs one additive boolean on `GuardResult` (`plr-sema/src/plr_sema/check/predicate.py:1401-1407`)
>     and a per-site tally in the ledger. **This is round 1's C12 remedy and it applies to the four
>     mechanisms TAKEN, not only to the one refused**: the amended truthiness clause, R-ARM and any name
>     M3 newly binds are all live inside `_scope_entry_value`
>     (`plr-sema/src/plr_sema/check/predicate.py:1011-1025`), and this block is the only thing that
>     would make a new silent excision attributable rather than merely detectable through
>     `unsound_scoped`.
> 11. **§17.1.5's precondition for increment 9**: the per-operation declared `type`/`element_type` of
>     the `destination` and `resource` operands of every `move_*` operation, published so D11 can be
>     argued from data next increment instead of from prose.

### 17.8.2 The gate

> **Normative (the GO condition, stated over structure because this increment cannot reach a verdict
> and says so in advance). The residual is SEVEN, not spec_version 1's six** — `:383` moved into it
> under §17.5.2's derivation, and moving it there rather than discovering it at a measurement is the
> whole point of the round.
>
> **The residual is STILL seven at spec_version 3, and this is where round 2's blocker either does or
> does not move it.** R2-C1 argued for **eight**, keeping `:375` in the residual because no
> `drop_resource` surface row exists. §17.1.4 takes the defect and rejects the retreat: the missing row
> is a *selection* defect with a specified fix, and the fixed selection provably yields a row whose
> `params ["drop"] ⊆ default {"drop"}`, so `_eval_check_args_missing_site_rule` returns `F` and `:375`
> leaves the residual. **Condition (1) is therefore unchanged at seven — but it now depends on THREE
> T54 pieces rather than one**, and §17.8.2's hook table below prices the D8 decline accordingly.
>
> > **GO iff ALL FIVE hold.** (1) On **every one** of the 93 `move_*` operations, the non-excluded
> > residual site set is **exactly** `{:383, :2204, :2211, :2226, :2233, :2284, :2290}` — seven entries,
> > down from thirteen. (2) `unresolved_delegate` is **0 findings** benchmark-wide. (3) Tier-1 `unsound`
> > is **0** under the unmodified predicate **and** `unsound_scoped` is **0** under §16.7's narrowing.
> > (4) `pick_up_tips` reaches `scope_verdict == SAFE` on **≥ 216** operations — increment 7's headline
> > preserved or improved — **and any increase is attributed to a named mechanism from §17.8.4's map
> > before the run is accepted.** (5) `guard_predicate_unparsed` is **unchanged at 495** and
> > `guard_operand_unknown` **unchanged at 144**.
>
> **NO-GO otherwise**: publish every count and the structural reason in §17.14, keep whatever landed
> (each mechanism is a strict information gain on the contract table and on the ledger either way), and
> bring the decision to the user.

> **Normative (the SEVEN distinct ways this gate can fail, named so it is not a coin already called;
> the seventh is new at spec_version 3).**
>
> 1. **The residual is larger than seven** — some mechanism does not reach some operation, which
>    falsifies §17.1's site analysis.
> 2. **The residual is SMALLER than seven, or contains a site not on the list** — equally a failure, and
>    the more interesting one: it means a mechanism decided something this document did not predict,
>    and an undiagnosed `SAFE` is exactly what §17.1.5 refuses to ship. **Block (10) is what makes this
>    attributable**, because the likeliest undiagnosed `SAFE` is a scope exclusion.
> 3. **M-INH regresses the benchmark** — condition (4) or (5) breaks because newly resolved base
>    methods carry guards this document did not anticipate, **or because the depth perturbation §17.2's
>    box names moves a guard out of the depth-1 population**. Block (1)'s depth multiset is what tells
>    the two apart.
> 4. **Either fence counter moves off zero** — the one outcome that stops the increment outright.
> 5. **M-SURF's blast radius is wider than §17.1.4 argues** — block (4) shows R-CONST's
>    `n_resolved_by_rule` moving, which would mean a newly-attached entry does carry a call-shaped
>    `self.backend.<m>(...)` `EnvRef` after all and the confinement argument is wrong.
> 6. **§17.1.4's diagnosis is wrong** — the surface attaches, `caller_args` populates, and `:375` still
>    declines on some part of the 321. Block (6) publishes the decline reason per operation, and this
>    document's `:375 → 0` prediction is falsified in public rather than absorbed.
> 7. **The SELECTION half does not produce the `drop_resource` row, or produces it absent by C15** —
>    new at spec_version 3, and it is round 2's R2-C1 restated as a falsifiable outcome rather than as
>    a prediction this document is confident about. Block (4)'s `n_surface_rows` and sorted `rows` key
>    list are what surface it, **at T54 rather than at T55**, and if the row appears but is counted in
>    `n_surface_absent_by_c15` instead then §17.1.4's undecorated/singly-defined argument is wrong at
>    the pin and `:375` returns to the residual as R2-C1 argued. This is the cheapest single check in
>    the whole increment and it is owed before T55 runs.

> **Normative (which decision hooks each condition needs, so a partial decline is predictable rather
> than discovered mid-sprint).**
>
> | hook (D7–D9: **if declined**; D10–D11: **if approved**, per their own rows) | condition (1) becomes | other conditions |
> |---|---|---|
> | **D7** (both units) | **eleven** sites, adding `:2055`, `:2070`, `:2120`, `:2147` | unaffected |
> | **D7 unit 11 only** (the truthiness clause) | ten sites, adding `:2070`, `:2120`, `:2147`; T52 leaves the increment with `p3a` | unaffected |
> | **D7 unit 12 only** (the typestate) | eight sites, adding `:2055`; T51's clause leaves and R-ARM lands as a term-position path shape with no consumer, so **T51 is withdrawn entirely** rather than landing dead machinery | unaffected |
> | **D8** | eight sites, adding `:375` — and at spec_version 3 the decline costs **all three** of T54's pieces (the surface selection extension, the attachment filter's `caller_args_sites` scan, and M3's per-site maps), not just the argument map | unaffected; **M-SURF still lands and still clears `:375`/`:383` on the 148**, whose method names are already selected and whose `caller_args` is already populated at depth 1 |
> | **D9** | eight entries, adding `_state_updated`; condition (2) is **unreachable**; and §17.5.1's first site-set condition makes M3 decline on the whole move family, so `:375` joins the residual — **nine** | (4) and (5) become strictly easier |
> | **D10** — read this row as **"if APPROVED"**, since D10's recommendation is already **NO** and this table's other five rows price a *decline* (round 2's R2-C13) | **if DECLINED (= taken as recommended): no change.** **If APPROVED the increment still cannot deliver it** — §17.5.2 prices it at four productions and four hops — so no row lands here, condition (1) is unchanged at seven, and the approval carries forward into increment 9's scope as a standing user decision | unaffected in both branches |
> | **D11** — read this row as **"if APPROVED"** on the same construction | **if DECLINED (= taken as recommended): no change.** **If APPROVED the increment still cannot deliver it** — an `IR_VERSION` bump re-keying every cached entry plus a corpus-wide exactness claim nothing publishes is not deliverable alongside four new mechanisms — so no row lands here, the six `drop_resource` sites stay in the residual, and the approval carries forward into increment 9, where §17.8.1 blocks (10) and (11) are the data to argue it from | unaffected in both branches |
>
> **D9's decline is the one that cascades**, and spec_version 1 did not say so: without M-INH the move
> closures carry two unresolved self-calls apiece, §17.5.1's fail-closed site-set condition fires, and
> M3 decides nothing on this family even with D8 taken. **With D7, D8 and D9 all declined the gate is
> unwinnable by construction**, and the increment reduces to M-SURF plus §17.8.1's measured blocks —
> which is still 148 operations of `:375` and `:383`, still worth publishing, and still the input
> increment 9 needs. **The user is owed that choice before the work starts and not at a gate**, which
> is the discipline increment 7 §16.15 Q5 established and this document inherits.

### 17.8.3 The prediction, per entry

> **Normative (this table is a PREDICTION for T55 to falsify, cell by cell; a divergence in either
> direction is recorded in §17.14 rather than absorbed.) Every cell is TIER 1.** Counts are the ledger's
> frozen population. The graph lane is the second table below, and the split is increment 7 §16.5.6's
> own normative disclosure applied to this increment's rules
> (`.praxia/docs/specs/260909_plr-sema-observation-increment.md:1127-1140`), which spec_version 1 owed
> and did not make.

**The move family — 93 operations, one uniform residual, TIER 1:**

| entry | today | all hooks taken | by what |
|---|---|---|---|
| `_state_updated` ×2 | 186 findings | **0** | §17.2's M-INH; neither `Resource._state_updated` nor the `serialize_state` it dispatches to contributes a guard |
| `:2055` | ½ on 93 | **`SAFE` on 93** | R-ARM plus §17.1.2's truthiness clause; the Kleene `And` needs only the second conjunct |
| `:2070` | ½ on 93 | **`SAFE` on 93** | the typestate at position; `EMPTY` before `:2072` |
| `:2120` | ½ on 93 | **`SAFE` on 93** | the typestate; `HELD` after the `try`, by §17.4.3 condition 2's terminator test |
| `:2147` | ½ on 93 | **`SAFE` on 93** | the typestate; `HELD` |
| `:375` | ½ on 93 | **`SAFE` on 93** | the selection extension makes `drop_resource` a row; M-SURF and the attachment filter's `caller_args_sites` scan attach the surface; M3 supplies `m`/`default` at all three closure call sites; the fold is `F` at each |
| `:383` | ½ on 93 | **unchanged, ½ on 93** | no route — §17.5.2, D10 **NO** |
| `:2204` `:2211` `:2226` `:2233` `:2284` `:2290` | ½ on 93 | **unchanged, ½ on 93** | E-TYPE's negative direction, refused (§17.1.5, D11) |
| **`scope_verdict`** | `UNKNOWN` on 93 | **`UNKNOWN` on 93** | seven sites remain; **this document claims no verdict here** |

**The graph lane (tier 2b), stated per row rather than left to inference:** R-ARM, the truthiness
clause and the typestate's inter-operation carry are all **observation-dependent**, and the graph lane
has no harness and no observation, so `:2055`, `:2070`, `:2120` and `:2147` **stay ½ there in every
branch**. M-SURF and M3 are **contract-table** facts and are lane-independent, so `:375` clears in both
lanes. M-INH is a contract-table fact and is lane-independent. `:383` and the six `drop_resource` sites
stay ½ in both lanes. **The graph lane therefore sees a residual of eleven, not seven, and §17.8.2's
gate is a tier-1 gate** — which §17.9's tier-2b box already disclosed and this table now states.

**Whole benchmark, tier 1. spec_version 1 split this into a "certain" and a "diagnosis-dependent" half
because §17.1.4's cause was open; the cause is now closed, so the split is gone and the numbers are
stated whole — with the honest consequence that a miss is a plain falsification and not a hedge:**

- **`:375`.** 321 → **0**. The 148 `aspirate`/`dispense`/`drop_tips` clear on **M-SURF alone**; the 80
  `transfer`/`discard_tips`/`stamp` and the 93 `move_*` need **M-SURF plus all three of T54's pieces
  together** — the surface selection extension, the attachment filter's `caller_args_sites` scan, and
  M3 — because their `_check_args` guards sit at depth ≥ 2 and neither their method names nor their
  argument maps exist today (§17.1.4, round 2's R2-C1). **Published, not gated** — the gate reads only
  the 93, because increment 7 C4's lesson is that gating on the part a document cannot re-measure makes
  a prediction-holding run fail its own criterion.
- **`:383`.** 321 → **120**. Clearing: the **148 on M-SURF alone**; `transfer` 19 and `discard_tips` 34
  **additionally require M3 (D8)** — the discharge *route* is the shipped `has_var_keyword` one, but
  `_check_args_surface_row` needs `m` from the argument map
  (`plr-sema/src/plr_sema/check/predicate.py:1246-1248`) and both reach `_check_args` at depth ≥ 2, so
  53 of the 201 are D8-dependent, exactly as §17.8.2's hook table and Q10's "on the 148" already have
  it (round 2's R2-C10; spec_version 2's bullet read as if all 201 were hook-free). Not clearing:
  `stamp` 27 and the move family's 93, because `has_var_keyword` is `False` for
  `aspirate96`/`dispense96`/`pick_up_resource`/`drop_resource`
  (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:207-231`) and §17.5.2's
  second route is refused.
- **`unresolved_delegate`.** 186 → **0**, whole population. This one **is** gated.
- **`n_findings_decided`.** Today **2,817** → **3,711**: **+372** (the four move sites × 93) **+321**
  (`:375`) **+201** (`:383`). **spec_version 1's arithmetic is corrected here and the correction is not
  in this document's favour**: it counted **+186** for `_state_updated`, but a gap that disappears
  removes an *undecided* finding from the denominator rather than deciding one. M-INH contributes
  **0** to `n_findings_decided` and **−186** to `n_findings`. **Published, not gated.**
- **`n_findings`.** 3,903 → **2,823**, and **spec_version 2's `3,717` was arithmetically wrong**
  (round 2's R2-C5, conceded). `n_findings_total` counts **UNKNOWN** findings only, and its by-reason
  cells partition it exactly: 2,884 + 495 + 194 + 186 + 144 = 3,903
  (`outputs/plr-sema/unknown_ledger_260909_final.json:29-38`). So the 894 findings the bullet above
  moves *into* `n_findings_decided` must also *leave* `n_findings`, exactly as the
  `guard_env_dependent` cell below already concedes; spec_version 2 subtracted only M-INH's 186.
  **The correct figure follows from this document's own adjacent cells without any ledger identity:**
  1,990 (`guard_env_dependent`) + 495 (`guard_predicate_unparsed`) + 194 (`volume_state_unknown`)
  + 0 (`unresolved_delegate`) + 144 (`guard_operand_unknown`) = **2,823**. Cross-check: 3,711 decided
  + 2,823 unknown = 6,534 = 6,720 − 186 ✓.
- **`guard_env_dependent`.** 2,884 → **1,990** (−372 −321 −201).
- **`n_clusters`.** 52 → **46**: the `unresolved_delegate` cluster goes, the four
  `:2055`/`:2070`/`:2120`/`:2147` clusters go, and the `:375` cluster goes; **`:383` survives at 120**
  as a partially-cleared cluster, which is the correction increment 7 C4 made to its own arithmetic and
  this document adopts rather than rediscovering.
- **`guard_predicate_unparsed` 495 → 495** and **`guard_operand_unknown` 144 → 144**, unchanged in
  every branch. This increment adds no grammar production that any guard's own predicate reaches, and a
  movement in either means something unintended happened. **Both are gate conditions**, and they are
  the two cheapest falsifications of this document's own claims about its blast radius.
- **`unknown_rate` 1.0 → 1.0**, and `scope_verdict == SAFE` on **216** operations, all `pick_up_tips`,
  unchanged. **No new method reaches a joined `SAFE`**, and §17.8.4 is where that is defended. An
  *increase* is not automatically a failure but is not automatically a win either: gate condition (4)
  requires it attributed.

### 17.8.4 The anti-gaming counter

> **Normative (which mechanism flips which site — the falsification map). The gate is stated over a set
> this increment shrinks, so the burden is on this box.**
>
> | mechanism | flips | does NOT flip | published counter |
> |---|---|---|---|
> | M-INH alone (§17.2) | the `<none>` gap only | every guard site in the benchmark | the newly-resolved pair list, the four refusal counts, and the per-guard depth multiset |
> | R-ARM plus the truthiness clause | `:2055` only | every guard reading any other path | `n_resolved_by_rule` for R-ARM, and `n_seq_truthiness_decided` |
> | the typestate (§17.4) | `:2070`, `:2120`, `:2147` only | every guard not reading a singleton anchor | the per-guard state assignment, `n_typestate_decided`, and `n_typestate_widened` |
> | M-SURF alone (§17.1.4), T53 | `:375` and `:383` on the 148, through the SHIPPED rules | every guard that is not a `_check_args` site rule; R-CONST's population; **the surface's four row-level counters, which T53 must leave unchanged** | `n_entries_with_backend_surface` before/after, R-CONST's `n_resolved_by_rule` before/after, and block (4)'s `n_surface_candidates`/`n_surface_absent_by_c15`/`n_surface_rows`/sorted `rows` key list before/after |
> | the surface SELECTION extension (§17.1.4, new at spec_version 3), T54 | nothing by itself — it adds ROWS; without M3 no move-family guard has an `m` to look one up with | every guard predicate, because no guard predicate carries a call-shaped `self.backend.drop_resource`; R-CONST's population | `n_surface_rows` off 89, `n_surface_candidates` off 160, and `drop_resource` newly present in the sorted `rows` key list |
> | M3 alone (§17.5.1) | nothing by itself | — it binds names; it decides no guard and licenses no `WILL_FAIL` | the newly-admitted pair list and the per-`(entry point, delegate)` site sets |
>
> **The FIVE cheap ways to pass this gate, all named and all REFUSED; the fifth is new at
> spec_version 3.**
>
> 1. **Put the six `drop_resource` sites into `excludes_sites`.** Refused. `excludes_sites` is
>    **derived**, from `is_dynamic_raise` and from nothing else
>    (`plr-sema/src/plr_sema/check/predicate.py:1121-1125`); admitting a site list is the configuration
>    increment 6 §15.1's derived-tier box exists to prevent, and increment 7 §16.10.4 refused the
>    identical move for `:375`/`:383` when it would have bought a headline. **This is the move that
>    would make the gate's condition (1) trivially true, and the reason it is refused is not cost.**
> 2. **Retire `unresolved_delegate` instead of emptying it.** Refused by §17.6's own box. Condition (2)
>    would then be satisfied by a deletion.
> 3. **Widen the typestate to `TOP` whenever it would be wrong.** A `TOP` state emits
>    `guard_env_dependent`, so this cannot manufacture a `SAFE` — but it *can* make §17.4's measured
>    selection look healthier than it is. **`n_typestate_widened`, broken down by condition, and
>    `n_typestate_decided` beside it, are what a reader inspects**, and AC-17.3 asserts the three move
>    guards decide by state and **not** by widening.
> 4. **Attach the backend surface unconditionally to every contract entry.** Refused, and it is the
>    newest of the four because M-SURF is new. Attaching everywhere would make condition (1) easier and
>    would also hand R-CONST a lookup table on entries whose guards were never argued to need one —
>    the exact confinement §17.1.4's blast-radius box rests on. **The filter stays a filter; it is
>    widened by one derived clause and not removed**, and block (4)'s R-CONST counter is what proves it.
> 5. **Make `selected_method_names` the whole function index — i.e. build a surface row for every
>    class method there is.** Refused, and this is the cheap move the SELECTION extension makes
>    available for the first time, so it is named the moment the extension is. It would guarantee the
>    `drop_resource` row without any of T54's other work, would take `n_surface_candidates` from 160 to
>    the whole index, and would hand the two `_check_args` site rules a table nothing derived — which
>    is the same configuration-not-derivation objection refusal 1 makes about `excludes_sites`, and it
>    would additionally break `collect_env_ref_method_names`'s own no-hand-typed-name property
>    (`plr-sema/src/plr_sema/derive/receiver_state.py:1457-1468`). **The selection stays a selection;
>    it gains exactly one more JSON location to walk and no default-open branch**, and block (4)'s
>    `n_surface_candidates` before/after is what proves it — an unbounded selection is visible in that
>    one number.
>
> **The cheapest falsification of this document as a whole**: any `move_*` operation whose residual is
> not exactly the predicted seven. That single number falsifies §17.1's site analysis in either
> direction, and it is the gate.

---

## 17.9 The oracle and the mutants

**Tier 1 re-run is the gate, under the UNMODIFIED unsoundness predicate.** Baseline, from the run this
document is written against: 544 executed operations, `unsound` 0, `unsound_scoped` 0,
`n_findings_decided` 2,817, `gate.go` true with 216 at `scope_verdict == SAFE`
(`outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json:263-265`). Every one of those numbers
is re-measured and any movement is attributed to a named mechanism before the run is accepted.

**Non-regression, exact:** m1, m2, v1 and the tier-2b fixture set at their increment-7 closing values,
with `region_unsound` 0.

> **Normative (which mechanisms can move tier 2b, disclosed once — C24's own discipline).** Tier 2b
> builds every fixture on the chatterbox backend and **can observe**, so **R-ARM** and the truthiness
> clause can move it, and so can the typestate on any fixture whose program picks a resource up.
> **M-INH, M-SURF and M3 move it for a different reason** — they change the contract table, which both
> lanes read — so a tier-2b movement attributable to any of those three is expected and is not itself
> a defect. **Every movement must be attributed to a named mechanism, using §17.8.1's per-lane
> counters, before the run is accepted.**

> **Normative (the mutant class, and it has exactly ONE mutator).** **`p3a_pickup_already_held`**:
> mutate a planned program so a second `pick_up_resource` is issued while a resource is still held.
> PLR raises `RuntimeError` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2069-2070`; the static side must
> emit `WILL_FAIL` at the raised index. **This is the only mutator that exercises the typestate's `T`
> direction, and that is exactly the class's point** — a two-state tracker tested only in the `SAFE`
> direction is half tested, which is increment 7 D1's own argument.
>
> > **Normative (WHICH HARNESS, and it is NOT `predicate_mutants.py` — round 2's R2-C4, conceded).**
> > spec_version 2 said `predicate_mutants.py` is extended. It cannot be, and the reason is a fact
> > about that module's API rather than a cost: every one of its mutators is a **kwargs transform**,
> > `Callable[[dict[str, Any]], bool]` (`plr-sema/eval/predicate_mutants.py:138-142`), applied by a
> > driver that mutates "the FIRST `_TARGET_CALL` … call's grounded `PlanResult.kwargs` in place"
> > (`plr-sema/eval/predicate_mutants.py:173-174`). **Issuing a second call is a program-structure
> > mutation, which no `Callable[[dict], bool]` can express**, and no kwarg of a `move_*` call can
> > leave `self._resource_pickup` non-`None` at entry. A second obstacle the challenger did not name
> > compounds it: `_TARGET_CALL` is a module constant fixed to `pick_up_tips`
> > (`plr-sema/eval/predicate_mutants.py:89`) and is read directly by the driver
> > (`plr-sema/eval/predicate_mutants.py:198-207`), so even a program-level extension of that module
> > would need the target de-hardcoded.
> >
> > **`p3a` therefore lives in `plr-sema/eval/tip_mutants.py`, as a `pick_up_resource` analogue of
> > `make_m2_duplicate_pickup`** (`plr-sema/eval/tip_mutants.py:151-164`), which **is** exactly p3a's
> > shape for tips: find the first pickup index in `example["call_sequence"]`, `copy.deepcopy` the
> > call, shift its operand, and `insert(idx + 1, duplicate)`. Its API is
> > `Callable[[example], example | None]` over the program, registered in that module's own `_MUTATORS`
> > (`plr-sema/eval/tip_mutants.py:167`), and it returns `None` to DECLINE — the "skip, don't guess"
> > discipline p1b already follows — when the base example contains no `pick_up_resource`. **The
> > operand shift is a `resource`/`destination` shift rather than a tip-spot one**, so p3a needs its
> > own shift helper beside `_shift_tip_ref` and nothing else new. **T55's scope cell names
> > `tip_mutants.py`, not `predicate_mutants.py`**, and the row's ~280 LOC absorbs it (the analogue is
> > ~15 lines plus the shift helper) because T55 already runs `tip_mutants.py` in its gate cell.
> >
> > **The `:2055` non-constructibility argument is restated on the ground that survives.** §17.9's
> > refusal box below leaned on two grounds and spec_version 2 stated the weaker one second; the
> > weaker one — "the mutator API mutates kwargs" — is exactly the premise this box has just
> > withdrawn, and a document may not refuse one mutator on a premise it needs false to ask for
> > another. **Only the backend-class ground is kept**, and it is sufficient.
>
> **The mutable population is the FULL 93, and the reason is §17.4.0's route (round 1's C10, rebutted).**
> C10 held that `p3a` could never fire on `move_lid`/`move_plate` because `guard_is_unconditional`
> refuses `depth >= 2` unconditionally (`plr-sema/src/plr_sema/check/predicate.py:1092-1093`). That
> function governs the path the typestate **replaces**: `_finding_for_atom` returns
> `Verdict.WILL_FAIL` on `truth == "T"` with no depth argument and no call to it at all
> (`plr-sema/src/plr_sema/check/tipstate.py:455-472`), and `evaluate_call` records the `consumed` index
> so the ordinary emission is skipped one-for-one
> (`plr-sema/src/plr_sema/check/tipstate.py:521-543`). **Adopting C10's remedy would have written a
> denominator of 31 into this floor when the truth is 93** — which is why it is recorded as rebutted
> and not as conceded.
>
> **Floor, with a denominator, in p1's own published shape:** `n_achieved_will_fail_at_raised_index`
> over `n_ran`, with `n_construction_skipped` and `n_error` beside it, and the floor is
> **`achieved == attempted` with `attempted ≥ 60`** and 0 unsound in both directions. Sixty rather than
> increment 7's two hundred, because the mutable population is the 93 move operations and not the 544.
> **A bare floor of 1 is refused**, for C23's reason: 1/93 satisfies it.
>
> **If D7's unit 12 is declined this class is WITHDRAWN together with the typestate row rather than left
> to report 0** — increment 6 §15.16.3's lesson, that a class which can only ever report 0 is a
> publication and not a gate.

> **Normative (a mutator on `:2055` is NOT constructible, and the reason is a fact about the CORPUS,
> not about the harness's API — round 2's R2-C4, second half).** The dual — a backend that declares no
> arms — is a property of the **backend class**, and every fixture in this corpus is built on
> `LiquidHandlerChatterboxBackend`, whose `num_arms` is fixed by its own class body. **No program-level
> mutation and no kwargs mutation can change a backend class**, so `:2055` can only ever produce
> `SAFE` here and its `T` branch is unreachable by construction. **spec_version 2 additionally said
> "the mutator API mutates kwargs"; that clause is WITHDRAWN**, because the box above needs it false
> in order to ask for `p3a` at all, and a refusal resting on a premise the same section withdraws is
> not a refusal. The backend-class ground stands alone and is sufficient. **Stated as a property of the
> site rather than left as an absence**, and it is the same shape §16.11 recorded for `:321`.

---

## 17.10 Acceptance criteria

- **AC-17.1 (M-INH resolves, is measured whole-surface, and fails closed).** `_state_updated` is
  asserted **by name** to resolve to `Resource._state_updated` and to contribute **zero** guards
  (`external/pylabrobot/pylabrobot/resources/resource.py:932-934`); the whole newly-resolved
  `(class, name)` selection is published with each pair's unique defining base; and the refusal count
  is broken down by which of §17.2's four conditions, or which of the two extractor refusals, refused
  it. **Six fail-closed fixtures, and the first and the fourth are the stub-defeating halves:** a name
  defined on **two** classes in the base closure resolves to **neither** and the gap stands, asserted
  positively — an implementation that takes the first base passes every other fixture and fails this
  one; a base outside the index leaves the gap; a `ClassDef` with an unreadable base expression makes
  the **whole** class refuse rather than contributing a partial closure; a class name defined in two
  modules makes every resolution mentioning it refuse; **an inherited body whose own `self.<n>()` call
  is overridden on the analyzed class resolves to the OVERRIDE, asserted against a fixture where the
  two bodies carry different guards** — which is §17.2 condition 4 made checkable, and an
  implementation that binds the base's body passes every shape fixture and fails this one; and a
  closure that would more than double an entry point's guard count halts with a message naming the
  entry point rather than landing. A grep over the survey and the derive package asserts **no** PLR
  base-class name occurs as a literal, which is §17.2's no-hand-typed-fact claim made checkable. Per
  entry point, closure size, guard count **and the per-guard `depth` multiset** are published before and
  after, and **the multiset is asserted UNCHANGED for every entry point whose newly-resolved set is
  empty** — round 1's C11, and the only assertion that can catch a silent depth perturbation.
- **AC-17.2 (R-ARM, the observation field, its stability precondition, and the amended clause).**
  `verify()` returns `arm_slots` from the **same** single capture point §16.2.1 fixes, `None` with the
  rest of the record on any raising read; a fixture asserts the field is empty **before**
  `await setup.machine.setup()` and non-empty after, which is the placement half
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:212`); and a fixture asserts it
  sorts **numerically**. **The stability precondition is asserted directly** (round 1's C16): an
  operation sequence containing a pickup and a drop leaves `sorted(self._resource_pickups)` unchanged,
  which is what licenses calling the `Seq` complete at a later instant than the capture. Positive:
  `EnvRef(("self","_resource_pickups"))` resolves to the observed complete `Seq` under a `rule` of
  `"R-ARM"`, and `:2055` is asserted `SAFE` end-to-end **through the shipped guard record**, not through
  a hand-built predicate. **Three stub-defeating halves.** (i) A fixture with `self.setup_finished` at
  ⊤ still yields `SAFE`, which is the Kleene-`And` claim made checkable
  (`plr-sema/src/plr_sema/check/predicate.py:910-916`) — an implementation that requires both conjuncts
  fails it. (ii) `self.head` in predicate position is asserted **still ½**, by shape, with an
  **observed and non-empty** head — the kept refusal made checkable. (iii) **An `EnvRef` resolving to a
  non-`Top` `ir.Seq` under a rule that does NOT declare completeness is asserted still ½**, which is
  what makes §17.1.2's rule-keyed clause narrower than an `isinstance(value, ir.Seq)` test — an
  implementation keyed on the node rather than on the rule fails this and nothing else. An **empty**
  `arm_slots` is asserted to make the clause `F`, not ½. Increment 7's §16.5.1 text and the code comment
  that repeats it are asserted to carry the amended wording. **The HM-25 unit-11 probe is asserted to
  import and exercise `evaluate_predicate`** and to go red if the clause is deleted.
- **AC-17.3 (the typestate: the route, the anchor, the effects, the order, and the five widenings).**
  **The route is asserted first, because it is what round 1 established and what round 2 made
  normative:** `:2070`, `:2120` and `:2147` are asserted to be decided through the new
  `evaluate_anchor_call`'s `consumed`-index replacement, consumed by the shipped protocol
  (`plr-sema/src/plr_sema/check/__init__.py:451-453`), and a grep asserts **no new `EnvRef` path shape
  and no change to `_eval_is`** (`plr-sema/src/plr_sema/check/predicate.py:851-856`) — an
  implementation that routes the typestate through the predicate evaluator fails this. **Four further
  route assertions, each one of §17.4.0's closed decisions made checkable (round 2's R2-C3).** (a) A
  `move_*` fixture whose `channels` is `None` still decides all three guards, which is the
  no-channel-gate decision — an implementation that reuses `evaluate_call`'s
  `if channels is not None:` gate (`plr-sema/src/plr_sema/check/tipstate.py:570-582`) decides **zero**
  move guards and fails this and nothing else. (b) The anchor and channel `consumed` sets are asserted
  **disjoint** on the tip fixtures. (c) `atom_truth` is asserted to be **one** function serving both
  lattices, by a fixture that calls it with a `PickupState` and with a `TipState` and by
  `_measure_hm25` being asserted **exactly 12** with `productions` still **3**
  (`plr-sema/src/plr_sema/_hand_maintained.py:529-553`) — an implementation that duplicates
  `atom_truth` measures 14–15 and trips the ratchet, which is the mechanical form of §17.7 unit 12's
  arithmetic. (d) `_parse_atom` is asserted called with an empty `bool_view_attr` for this anchor and
  the bool-view atom asserted **never** produced for it. The complete
  anchor selection is published, with `_resource_pickup` asserted present **by name** and every
  candidate removed by §17.4.2's absence rule labelled with the clause that removed it. **Three
  absence fixtures, not one, and together they are this criterion's first stub-defeating half
  (round 2's R2-C2):** a synthetic `property` whose setter does more than one assignment, asserted
  **absent** (clause 1); the two-definition getter/setter pair `_resource_pickup` asserted **present**
  (clause 3's exception); and a synthetic qualname defined at **three** linenos asserted **absent**
  (clause 3 itself) — an implementation that drops clause 3 to save the anchor passes the first two and
  fails the third. The three move guards are asserted to decide **by state**:
  `:2070` from `EMPTY`, `:2120` and `:2147` from `HELD`, each asserted individually, which is the
  second stub-defeating half — a single per-call state cannot satisfy all three (§17.1.3). **Five
  widening fixtures, one per §17.4.3 condition**, each asserting `guard_env_dependent` and **not** a
  verdict: a conditionally-reached effect site; **an assignment inside an `ast.Try` handler that does
  NOT end in a `raise`, asserted to widen, beside one that DOES, asserted to leave `HELD` intact, and
  beside a THIRD whose last statement IS an `ast.Raise` but whose body contains an earlier
  `ast.Return`, asserted to widen** — the three together are the third stub-defeating half, the direct
  test of the rule that replaced spec_version 1's condition 2, and (in the third fixture) round 2's
  R2-C6 fence made checkable: an implementation that tests only `handler.body[-1]` passes the first two
  and produces a false `SAFE` on the third; an unresolved delegate between two guards; an undecided
  prior operation on the same receiver; and a guard reached at two positions whose states disagree,
  asserted `TOP`. The tip
  family's own `channel_state_unknown` is asserted **unchanged** on every tip guard, which is what
  keeps §17.4.0's one parametrised line from leaking. `n_typestate_widened` is published per condition
  and asserted **0** on the move family; `n_typestate_decided` is published beside it. The assumption
  table is asserted to have **five** rows — unchanged —
  which is §17.4.3's no-new-assumption claim made checkable. **`p3a`'s published floor is NOT asserted
  here** — it is AC-17.7's, on T55, which is the row that owns the mutant harness (round 2's R2-C7);
  what this criterion asserts about `p3a` is only what T52 can evaluate, namely that
  `_finding_for_atom`'s `truth == "T"` branch reaches `WILL_FAIL` for an anchor guard at `depth ≥ 2`
  in a unit fixture, which is what fixes the denominator at 93. **If D7's unit 12 is declined this
  criterion is withdrawn together with its task row, and AC-17.7's `p3a` sub-assertion is withdrawn
  with it.**
- **AC-17.4 (M-SURF attaches, its blast radius is exactly what §17.1.4 argues, and the surface's ROW
  counters are pinned).** `n_entries_with_backend_surface` is published before and after with the
  complete list of newly attached contract keys, and `LiquidHandler.aspirate`, `LiquidHandler.dispense`
  and `LiquidHandler.drop_tips` are asserted present in that list **by name**. **`has_var_keyword` is
  asserted `True` for the three chatterbox methods involved**
  (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:93-167`), and the two site
  rules are asserted to reach `F` on a unit fixture built from the regenerated table for each of
  `aspirate`, `dispense` and `drop_tips`, through the SHIPPED rules and not through anything M3 adds —
  which is what makes this row's contribution separable from T54's. **The per-operation benchmark
  count for the 148 is NOT asserted here**: it is AC-17.8's, on T55, which is the only row whose gate
  runs the replay and the ledger (round 2's R2-C7); this row asserts the mechanism, T55 asserts the
  population. **Three stub-defeating halves.** (i) **R-CONST's
  `n_resolved_by_rule` is asserted UNCHANGED**, which is §17.1.4's confinement argument made checkable —
  an implementation that attaches the surface unconditionally passes every positive assertion and fails
  this one. (ii) An entry with **no** `self.backend.<m>` `EnvRef` in either its `predicate` or its
  `caller_args` is asserted to receive **no** `backend_surface` key at all, so the filter is asserted to
  still be a filter. (iii) **New at spec_version 3 and round 2's R2-C1/R2-C8 made checkable:** block
  (4)'s four row-level counters are published before and after and asserted **unchanged at 160 / 71 /
  89** across this row, with `LiquidHandlerChatterboxBackend.pick_up_resource` asserted present in the
  sorted `rows` key list **by name** and `LiquidHandlerChatterboxBackend.drop_resource` asserted
  **ABSENT** from it **by name** — because M-SURF changes attachment only and adds no row, and an
  implementation that "fixes `:375`" by quietly widening the selection here rather than in T54 passes
  every other assertion and fails this one. A grep asserts no backend method name occurs as a literal
  in the change.
- **AC-17.5 (M3, the surface SELECTION extension, the whole-closure site set, the per-site list, the
  conjunctive fold, and the depth
  lift).** The complete newly-admitted `(K_i, D)` selection at `depth ≥ 2` is published, and for
  `_check_args` the admitted call-site set is asserted to contain **exactly three** entries for every
  one of `move_resource`, `move_lid` and `move_plate` — `:2345`, `:2364` and `:2079`
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2345-2350`, `:2364-2369`,
  `:2079-2081`) — each with its own lineno and caller qualname. That single assertion is the whole of
  round 1's C2 made checkable, and it is this criterion's **first stub-defeating half**: an
  implementation that scans only the entry point's own body returns two entries for `move_resource` and
  **zero** for `move_lid`/`move_plate`, passing nothing. **Five further fixtures.** (i) A multi-site
  delegate where one site would yield `F` and the other declines is asserted **½**, not `F` — the
  conjunctive fold made checkable. (ii) A `depth == 2` argument that is a caller-side **name** rather
  than a constant is asserted to bind **nothing**, which is the whole of §17.5.1(b)'s narrowness claim.
  (iii) A `SetLit` at depth 3 binds. (iv) A closure containing one record with a non-empty
  `unresolved_calls` is asserted to make the fold **decline**, and the same closure with that call
  resolved is asserted to decide — which is §17.5.1's first site-set condition and the mechanical form
  of the T50-before-T54 ordering. (v) `caller_reachability_clear` and `caller_scope_trail` are asserted
  **absent** at every `depth ≥ 2` guard, and a grep asserts no new `WILL_FAIL` path was opened. The
  wire round trip is asserted in `test_cache.py`: `caller_args_sites` preserves per-site linenos, and a
  contract table carrying only the old `caller_args` key still decides `:375` for `pick_up_tips`.
  **The SELECTION extension is asserted separately, and it is round 2's R2-C1 made checkable — three
  further assertions.** (vi) `LiquidHandlerChatterboxBackend.drop_resource` is asserted present in the
  surface's sorted `rows` key list **by name** after this row, with `params` asserted exactly
  `["drop"]` and `has_var_keyword` asserted `False` — the shape §17.1.4 derives from
  `external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:229-230`, and an
  implementation that extends the attachment filter without extending
  `collect_env_ref_method_names` passes every fold assertion above and fails this one. **The `params`
  assertion is scoped to THAT row**: the other nine `drop_resource` rows are heterogeneous by design
  (§17.1.4's scoping box) and no move-family guard reads them, so this criterion asserts nothing about
  their shapes. (vii) **The three row-level counters are asserted BY VALUE, not merely as having
  moved**: `n_surface_candidates` **172**, `n_surface_absent_by_c15` **73**, `n_surface_rows` **99**,
  with the invariant 172 − 73 = 99 asserted and the full added-key diff published. These come from
  §17.1.4's derivation off `pick_up_resource`'s measured twin, and asserting them by value is what
  makes this a falsification rather than a drift: an implementation whose selection became
  default-open blows `n_surface_candidates` far past 172 (§17.8.4 refusal 5), and a C15 exclusion
  `pick_up_resource` does not share shows up as 73 moving. **If the measured triple diverges, T54
  records it in §17.14 against this criterion rather than adjusting the criterion.** (viii) **R-CONST's
  `n_resolved_by_rule` is asserted UNCHANGED across this row too**, which is the selection half's own
  blast-radius argument made checkable, and a grep asserts no backend method name occurs as a literal
  in the change. `:383` is asserted **still ½**
  on all 93, which is §17.5.2's refusal made checkable rather than merely stated. **The per-operation
  benchmark count for the 93 is NOT asserted here** — `:375` at `SAFE` on the 93 `move_*` operations
  by name is AC-17.8's, on T55, for the reason round 2's R2-C7 gives: this row's gate cell runs
  `test_derive.py`, `test_check_graph.py` and `test_cache.py` and cannot evaluate a frozen-benchmark
  population. `len(D6_SITE_RULES)`
  is asserted **3** and HM-26's `declared` asserted **3**
  (`plr-sema/src/plr_sema/check/predicate.py:1333-1337`). **If D8 is declined this criterion is
  withdrawn together with its task row, and AC-17.8's two `:375` population sub-assertions for the 93
  and the 80 are withdrawn with it.**
- **AC-17.6 (tier 1 — both fence counters at zero, the reason counts, and increment 7 preserved).** The
  sidecar-gated replay reports `unsound == 0` under the unmodified predicate and `unsound_scoped == 0`;
  `pick_up_tips` reaches `scope_verdict == SAFE` on **≥ 216** operations, with any increase attributed
  to a named mechanism; `guard_predicate_unparsed` is asserted **unchanged at 495** and
  `guard_operand_unknown` **unchanged at 144**; `unresolved_delegate` is asserted **0 findings** and the
  member is asserted **still present** in `REASON_VOCABULARY`
  (`plr-sema/src/plr_sema/verdict.py:147-199`), which is §17.6's not-retired claim made checkable.
  `n_findings_decided` is published against §17.8.3's **3,711** and is **not** gated;
  `n_findings` is published against **2,823** — spec_version 2's **3,717** was wrong and is corrected
  per round 2's R2-C5, because the 894 findings that become decided also leave the UNKNOWN population
  and spec_version 2 subtracted only M-INH's 186 (§17.8.3's own bullet carries the arithmetic and its
  cross-check). **The stub-defeating half: an implementation that lands
  every mechanism but never threads the observation scores at most 3,339 — the 372 observation-dependent
  findings never decide — and fails.**
- **AC-17.7 (non-regression and the mutant class).** m1, m2, v1 and the tier-2b set at their
  increment-7 closing values with `region_unsound == 0`, **with any tier-2b movement attributed to a
  named mechanism from §17.9's disclosure before the run is accepted**. p1's three mutators are
  re-measured **unchanged**, which is what proves this increment disturbed no depth-0 population.
  **`p3a` is asserted HERE and not on AC-17.3, because T55 is the row that owns the mutant harness and
  T52's gate cell never runs it (round 2's R2-C7).** `p3a_pickup_already_held` is published as
  `achieved/attempted` in p1's own shape — `n_achieved_will_fail_at_raised_index` over `n_ran`, with
  `n_construction_skipped` and `n_error` beside it — against §17.9's floor of `achieved == attempted`
  with `attempted ≥ 60`, **its denominator asserted to be 93 and not 31**, and 0 unsound in both
  directions. It is asserted to live in `plr-sema/eval/tip_mutants.py` and to use that module's
  program-level `Callable[[example], example | None]` API rather than
  `predicate_mutants.py`'s kwargs API (round 2's R2-C4), which a grep over the two modules makes
  checkable. **If D7's unit 12 is declined this sub-assertion is withdrawn with AC-17.3 and T52**, and
  the rest of AC-17.7 stands.
- **AC-17.8 (the measured sets are published and the gate is decided by them).** All **eleven** blocks
  of §17.8.1 are present and non-null; §17.8.3's per-entry table is reproduced cell by cell for
  whichever branches of D7–D9 the user took, with every divergence recorded in §17.14 rather than
  absorbed; the GO/NO-GO is recorded against the published per-operation residual site set, and **the
  gate is asserted computable from the JSON alone, without reading this document**. §17.1.4's
  diagnosis is either **confirmed with `:375` at 0 benchmark-wide** or explicitly recorded as
  falsified with block (6)'s per-operation decline reasons published — the report must say which, so
  the `321 → 0` prediction is never read as achieved when it is not. Block (10)'s `n_scope_excluded`
  is asserted to name **zero** newly-excluded sites outside the move family, or to name every one it
  found. Block (11)'s destination-type distribution is published whether or not increment 9 uses it.
  **Three per-operation benchmark sub-assertions are re-homed here from AC-17.4 and AC-17.5, because
  this is the only row whose gate runs the tier-1 replay and the ledger (round 2's R2-C7).** (a)
  `:375` is asserted `SAFE` on the **148** `aspirate`/`dispense`/`drop_tips` operations and `:383`
  likewise, **attributed to T53 alone** through the shipped rules — the assertion that makes M-SURF's
  contribution separable, which AC-17.4 states the mechanism for and this criterion counts. (b) `:375`
  is asserted `SAFE` on the **93** `move_*` operations **by name**, and `:383` **still ½** on all 93.
  (c) `:375` is asserted `SAFE` on the **80** `transfer`/`discard_tips`/`stamp` operations and `:383`
  on the 53 of them that reach it. **(b) and (c) are withdrawn with AC-17.5 and T54 if D8 is
  declined**, and (a) is withdrawn only if T53 itself does not land — which no decision hook permits.
  The withdraw-with-row linkage is prose here rather than a gate cell precisely because the crossref
  lint reads gate cells only (§17.11's box), and a criterion cannot be gated twice.
- **AC-17.9 (this document is machine-checked).** `.praxia/docs/INDEX.md` is regenerated and
  `uv run pytest plr-sema/tests/test_spec_lint.py -q` is **actually run** with its result recorded —
  the citation checker reporting **zero** failing violations over this file and the AC-gating half of
  the cross-reference checker reporting zero, with the other eight specs unchanged at zero. **This file
  is already registered as `SPEC_INCREMENT_8` and already parametrised into both live-spec tests
  (`plr-sema/tests/test_spec_lint.py:39`, `:226`, `:252`), so the registration half of spec_version 1's
  T56 is already done and the row shrinks to the index regeneration and the run.**

---

## 17.11 Task rows

> **Normative (the ordering, forced by the same gate discipline increments 5, 6 and 7 all impose, plus
> one dependency round 1 created).** **T50 must land and publish its measured selection before T52**,
> because §17.4.3's third widening condition is defined over the unresolved-delegate population and a
> typestate computed against a stale one is a state nobody has inspected. **T50 must also precede
> T54**, which is new in spec_version 2: §17.5.1's first site-set condition makes M3's fold decline
> whenever any record in the closure carries an unresolved self-call, and every move-family closure
> carries two today — so M3 lands dead on this family unless M-INH went first. **T53 must precede
> T54**: M-SURF alone moves 148 operations through the shipped rules, and landing M3 first would make
> that contribution unattributable. **T51 is independent of all of them.** T55 is last and is where
> §17.1's analysis is confirmed or falsified.
>
> **Normative (round 2 did NOT reverse this ordering, and that is worth saying because the blocker
> looked as though it might — R2-C1's "why a fixer is blocked" claimed the fix "reverses §17.11's
> stated T53-before-T54 attribution story").** It does not. The 148 `aspirate`/`dispense`/`drop_tips`
> operations reach `_check_args` at **depth 1** with `caller_args` populated, so their method names are
> already selected and their rows already exist; T53's attachment extension alone still clears
> `:375`/`:383` on them, and it is still the only row that does so without a hook. **The selection
> extension and the attachment filter's `caller_args_sites` scan are BOTH T54's**, because
> `caller_args_sites` does not exist until T54 creates it — a selection scan for a field no table
> carries would be dead code, and that is the whole reason the split falls where it does rather than
> being an attribution convenience. **T53 still precedes T54; the D8-decline branch of §17.8.2 is
> unchanged; and T54 now carries three pieces instead of one, which §17.11's sizing note prices.**

> **Normative (why every AC is gated exactly once, and where the conditional rows sit).** The
> cross-reference lint reads the **gate cell only** — column 4 of a row matching its task-row pattern
> (`plr-sema/scripts/check_spec_crossrefs.py:139-156`). An AC named in a scope cell, in a box, or in
> prose is documentation and not a gate. **AC-17.3 and AC-17.5 are gated on T52 and T54, each
> conditional on a user decision** — the same construction increment 7 used for AC-16.13 on T48, and
> the reason a declined decision withdraws the criterion **with** its row rather than leaving it
> unsatisfied. **AC-17.4 is gated on T53, which is conditional on nothing**: M-SURF is the one
> mechanism here that needs no hook, and that is deliberate — it means a total decline of D7, D8 and D9
> still leaves the increment with 148 operations and a closed diagnosis.

| task | scope | files | gate | ~LOC | depends on | model |
|---|---|---|---|---|---|---|
| **T50** | **CONDITIONAL on D9.** **M-INH — inherited self-call resolution (§17.2), both halves in one commit.** The survey's per-`ClassDef` method-name set gains the transitive base closure's method names, with an additive `inherited_delegates` field; `resolve` gains a **third** step after its two existing same-module steps, returning the unique defining base's key and `None` on ambiguity; **the base-name extractor of §17.2 — `ast.Name`/`ast.Attribute`/`ast.Subscript` and a whole-class refusal on anything else — is written here, because nothing in the repo builds the map `subclass_closure_from_bases` consumes**; a `(module, name)`-keyed index refuses bare-name collisions; **the FOURTH fail-closed condition — an inherited body's self-calls dispatch on the analyzed class, threaded through `_walk_closure` as an additive parameter with NO change to traversal semantics**; the complete newly-resolved selection, the six refusal counts, and **per entry point the closure size, guard count and per-guard depth multiset before and after**, with a doubling halt that stops and surfaces to the user rather than landing. **`_state_updated` contributes zero guards and the reason's whole population goes to zero** | modify `scripts/survey_plr_preconditions.py`, `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q`; then re-run the survey and regenerate the contract table — satisfying **AC-17.1** | ~230 | — | Sonnet — the ambiguity refusal and the override condition are the two clauses standing between a resolution and the wrong function body's guards, and this row can move every number in the benchmark |
| **T51** | **CONDITIONAL on D7 unit 11.** **R-ARM and the complete-`Seq` truthiness clause (§17.3, §17.1.2).** `verify()` gains the additive `arm_slots` field at the **existing** single capture point, `None` with the rest of the record on any raising read; the harness builds its `obs:` member under §16.2.3's JSON encoding with numeric int sort; **R-ARM** resolves `self._resource_pickups` inside `_resolve_env_ref` under a new `rule` value, declared complete subject to §17.3's stability precondition; **the amended predicate-position clause, keyed on the RULE and not on `isinstance(value, ir.Seq)`** — `T` iff non-empty, `F` iff empty — with the `self.head` shape refusal **kept unchanged**; the amendment written into increment 7's own §16.5.1 text and the code comment that repeats it, in this commit; **the HM-25 unit-11 probe added to `shape_matchers`, importing and exercising `evaluate_predicate`**; `n_resolved_by_rule` for R-ARM per lane and `n_seq_truthiness_decided` published | modify `training/verify/verifier.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/eval/region_oracle.py`, `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/src/plr_sema/_hand_maintained.py`, `.praxia/docs/specs/260909_plr-sema-observation-increment.md` (the §16.5.1 amendment), `training/tests/test_verify_postconditions.py`, `plr-sema/tests/test_check_graph.py`, `plr-sema/tests/test_hand_maintained_ratchet.py`, `plr-sema/tests/test_cache.py` | `uv sync --all-packages`; `uv run pytest training/tests/test_verify_postconditions.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q`; `uv run pytest plr-sema/tests/test_spec_lint.py -q` (the increment-7 edit must not break its citations) — satisfying **AC-17.2** | ~140 | — | Sonnet — small, but it amends a shipped refusal, and the kept-`self.head` fixture plus the rule-keyed-not-node-keyed fixture are the only things preventing that amendment from quietly becoming general |
| **T52** | **CONDITIONAL on D7 unit 12 — do not start without the user's answer.** **The `_resource_pickup` typestate (§17.4).** P5's anchor shape and its absence rule **with clause 3's getter/setter exception (§17.4.2, round 2's R2-C2)**; P6's effect table with `widen` for every non-plain assignment shape; the **intra-operation source-order walk** over the entry point's own delegate call statements, giving every guard a position and folding every strictly-earlier effect, with each call statement's conditionality taken from the **shipped** `compute_caller_scope_trail`/`compute_reachability_clear` at that statement's own lineno; the **five** fail-closed widening conditions of §17.4.3, **including the handler-terminator shape test that replaces spec_version 1's unconditional `try` widening — with its `Return`/`Break`/`Continue` fence (round 2's R2-C6) — and the multi-position join**; **the decision route of §17.4.0 as SEVEN closed decisions, which spec_version 2 wrongly described as already-shipped machinery (round 2's R2-C3): a NEW `evaluate_anchor_call` entry point returning `(findings, consumed)` and running before `evaluate_call`'s two loops, with NO `channels is not None` gate; `_parse_atom` reused with `parse_bridge_atom`'s bare-`self` `base_ok` and an empty `bool_view_attr`; a NEW `AnchorWalk`; and `atom_truth`/`_finding_for_atom` GENERALISED over both lattices rather than duplicated, so `productions` stays at 3 and `_measure_hm25` lands at exactly 12**; the ½ branch parametrised to `guard_env_dependent`, **and no change to `_resolve_env_ref` or `_eval_is`**; the two-state lattice with its optional held-resource `ir.Ref` payload, which decides nothing this increment; the inter-operation carry in `TipWalk`'s own manner; the complete anchor selection, the per-guard state assignment, `n_typestate_decided` and `n_typestate_widened` per condition published. **The HM-25 unit-12 spend, filed as ONE further unit whose probe imports a NEW symbol distinct from `_typestate_anchor` — stopping and asking the user if the measured count would exceed 12.** **No new named assumption is added and the assumption table stays at five rows** | modify `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/src/plr_sema/check/tipstate.py`, `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/src/plr_sema/_hand_maintained.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_tip_typestate.py`, `plr-sema/tests/test_hand_maintained_ratchet.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_tip_typestate.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q` (`live_rows` 25 and `BUDGET_CAP` 25, both asserted **unchanged**, and `_measure_hm25` asserted exactly **12** with `productions` still **3**) — satisfying **AC-17.3** | ~330 | **T50**, with its measured selection published | Sonnet — **the largest and riskiest row in the increment**: an intra-operation ordered state is machinery the analyzer has never had, the new evaluator entry point and walk have no precedent here, and the five widening conditions are the whole of what stands between it and a state that is confidently wrong |
| **T53** | **UNCONDITIONAL — no decision hook. M-SURF: the backend-surface ATTACHMENT fix, and ONLY the attachment fix (§17.1.4).** `derive/__main__.py`'s attachment filter is extended to attach `entry["backend_surface"]` when any of the entry's guards carries a `self.backend.<m>` `EnvRef` in its `predicate` (with `args is not None`, unchanged) **or** in its `caller_args` map — the asymmetry T49 closed on the SELECTION side for `caller_args` in `collect_env_ref_method_names` and did not close here. `n_entries_with_backend_surface` published before and after with the newly-attached key list; R-CONST's `n_resolved_by_rule` published before and after as the confinement check; **and the surface's four ROW-level counters (`n_surface_candidates`, `n_surface_absent_by_c15`, `n_surface_rows`, the sorted `rows` key list) published before and after and asserted UNCHANGED at 160/71/89 — this row adds no row, and `drop_resource` is asserted STILL ABSENT from the key list here (round 2's R2-C1: the SELECTION half for depth ≥ 2 method names is T54's, not this row's).** **This row alone closes `:375` and `:383` on the 148 `aspirate`/`dispense`/`drop_tips` operations through the SHIPPED site rules, with no registry cost, no new pattern, and no user decision** | modify `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_check_graph.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q` — satisfying **AC-17.4** | ~35 | — | Haiku — thirty-odd lines and one boolean, but its measured selection is what confirms or falsifies §17.1.4's attachment diagnosis, so the published before/after counts matter more than the code |
| **T54** | **CONDITIONAL on D8 — do not start without the user's answer.** **M3 — the constant-argument map at any depth over the whole closure (§17.5.1) — PLUS the surface SELECTION extension and the attachment filter's `caller_args_sites` scan (§17.1.4, new at spec_version 3, round 2's R2-C1).** `collect_env_ref_method_names` gains `caller_args_sites` as a third scanned JSON location beside `predicate` and `caller_args`, by the identical `predicate_from_json`/`predicate_walk` pair, so a method name that only ever appears at depth ≥ 2 becomes a surface-row candidate at all; `derive/__main__.py`'s attachment filter gains the same scan, so a move-family entry receives the `rows` dict; **`n_surface_candidates`/`n_surface_absent_by_c15`/`n_surface_rows` and the sorted `rows` key list published before and after, with `LiquidHandlerChatterboxBackend.drop_resource` asserted newly present with `params ["drop"]` and `has_var_keyword` `False`, and R-CONST's `n_resolved_by_rule` asserted unchanged**. Then M3 itself: a **buffered second pass over the walk's own `(rec, key, depth)` triples** (§17.5.1's shape box — the visited set is not exposed and `InlinedGuard` is frozen) collects, for each `(entry point, delegate)` pair, every `self.<D.name>(...)` call statement in every visited record that resolves to that delegate — **with no change to `_walk_closure`'s own traversal semantics**; each site's argument map is computed against **that site's own caller**, with alpha substitution position-gated at that site's lineno; the result ships as a **NEW** additive wire field `caller_args_sites`, beside the unchanged `caller_args`, because all three shipped consumers call `.get` on a `Mapping`; site rules evaluate once per entry and fold **conjunctively**; M1's `depth == 1` restriction is lifted for arguments that parse as a `Term` with **no free names** and for nothing else; **the two site-set fail-closed conditions — an unresolved self-call anywhere in the closure, or a visited record with no `K`, makes the fold decline**; **`caller_reachability_clear`, `caller_scope_trail` and D1's `WILL_FAIL` lift stay strictly `depth == 1` and are untouched**; the complete newly-admitted selection, the per-pair site sets, the fold outcomes and the surviving-clause refusal breakdown published | modify `plr-sema/src/plr_sema/derive/bindings.py`, `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_check_graph.py`, `plr-sema/tests/test_cache.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q`; then regenerate the contract table and assert the surface's row counters at exactly **`n_surface_candidates` 172 / `n_surface_absent_by_c15` 73 / `n_surface_rows` 99** (from 160/71/89), with `LiquidHandlerChatterboxBackend.drop_resource` present in the `rows` key list — §17.1.4's derivation off `pick_up_resource`'s twin, recorded in §17.14 if it diverges — satisfying **AC-17.5** | ~340 | **T50**, **T53** | Sonnet — it relaxes two deliberate soundness fences, adds a buffered second traversal pass, and carries the surface-selection half whose absence was round 2's one blocker; the three-site assertion for `move_lid`, the unresolved-call decline fixture and the `drop_resource`-row assertion are the three tests that prove the closure-wide and selection halves are real and fenced |
| **T55** | **The oracle, the mutants and the gate (§17.8, §17.9).** Tier-1 re-run under the unmodified predicate with both fence counters published; §17.8.1's **eleven** measured blocks, including the two new ones — M-SURF's attachment counts **plus block (4)'s four row-level surface counters before and after (round 2's R2-C8)** — and **`n_scope_excluded` per site before and after, which needs one additive boolean on `GuardResult` and a per-site tally**; §17.8.3's per-entry prediction table reproduced cell by cell for whichever branches of D7–D9 the user took, with every divergence recorded; the after-ledger with `consistency.ok`, its published delta, `n_row_id_collisions` before and after, and the per-method `residual_site_sets` threaded through so the ledger can audit the gate directly; **`plr-sema/eval/tip_mutants.py` — NOT `predicate_mutants.py`, whose kwargs-only mutator API cannot express a program-structure mutation (round 2's R2-C4) — extended with `p3a_pickup_already_held` as a `pick_up_resource` analogue of `make_m2_duplicate_pickup`, published as `achieved/attempted` over a denominator of 93**; the m1/m2/v1/tier-2b non-regression set re-measured with every movement attributed to a named mechanism; **the three per-operation benchmark counts AC-17.8 re-homes here — `:375`/`:383` on the 148, `:375` on the 93 with `:383` still ½, and `:375` on the 80 — each attributed to the row that bought it**; **§17.1.4's diagnosis either confirmed with `:375` at 0 benchmark-wide or explicitly recorded as falsified with block (6)'s per-operation decline reasons**; block (11)'s destination-type distribution published for increment 9; **the GO/NO-GO recorded against the published per-operation residual site set, computable from the JSON alone** | modify `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/eval/oracle_replay.py`, `plr-sema/eval/tip_mutants.py`, `plr-sema/eval/unknown_ledger.py`, `plr-sema/eval/t30_measure.py`, `plr-sema/tests/test_oracle_replay.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q`; then the tier-1 replay with its three standard flags, `unknown_ledger.py` into `outputs/plr-sema/unknown_ledger_2609XX_inc8.json`, `predicate_mutants.py`, `tip_mutants.py`, `volume_mutants.py` and `region_oracle.py` into `outputs/plr-sema/*_2609XX_inc8.json`, publishing the delta against the `260909_final` set — satisfying **AC-17.6**, **AC-17.7** and **AC-17.8** | ~280 | T50, T51, T52, T53, T54 | Sonnet — every published number is a measurement, and this row is where §17.1's site analysis is either confirmed or falsified by one set |
| **T56** | Index and lint: regenerate `.praxia/docs/INDEX.md` and **actually run the lint, recording the result**. **Registration in `plr-sema/tests/test_spec_lint.py` is already done** — this file is `SPEC_INCREMENT_8` and is already parametrised into both live-spec tests, which is why this row is four lines rather than spec_version 1's six | regenerate `.praxia/docs/INDEX.md` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_spec_lint.py -q` — satisfying **AC-17.9** | ~4 | — | Haiku |

**Sizing note, stated honestly and with the numbers round 1 moved flagged as moved.** T50 rises from
spec_version 1's ~190 to **~230**: the base-name extractor and the `(module, name)` collision index are
new code C9 showed was not shipped, the fourth fail-closed condition threads a parameter through
`_walk_closure`, and the per-guard depth publication is C11's. T51 rises ~120 → **~140** for the
HM-25 unit-11 probe. **T52 rises ~300 → ~330 at spec_version 3, and it is still the only guess**:
~72 for P5 and P6's shape tests and the absence rule (clause 3's getter/setter exception is ~2), ~112
for the ordered walk and the five widening conditions (the handler-terminator test is ~5 plus ~2 for
R2-C6's `Return`/`Break`/`Continue` fence, and C20's re-size is smaller than feared because
`compute_caller_scope_trail` is already shipped), ~50 for the inter-operation carry, ~70 for the
published selections, **and ~30 new at spec_version 3 for §17.4.0's evaluator entry point and the
`atom_truth`/`_finding_for_atom` generalisation, which spec_version 2 wrongly costed at zero by
believing them shipped (round 2's R2-C3)** — and the ordered walk is machinery with no precedent in
this codebase, so it could still be materially larger. **T52 is the row to split first if a session
boundary falls inside it**, at P5/P6 versus the walk-and-evaluator half. **T54 rises from
spec_version 1's ~200 to ~300 for C2's remedy and to ~340 at spec_version 3 for R2-C1's**: a buffered
second traversal pass, per-site caller resolution, a new wire field with its cache round trip, two
site-set fail-closed conditions, **and ~40 for the surface-selection extension, the attachment
filter's `caller_args_sites` scan and the four row-level counters**. T53 at ~35 is the cheapest row in
the increment and the one that buys the most operations per line. **Total for the conditional rows
plus T53, T51 and T55: ~1,360 LOC across seven rows, which is three to four sessions.** **Do not
reorder T50 after T52 or
after T54**, and **do not reorder T53 after T54**: the first would compute a typestate against a stale
unresolved-delegate population, the second would land M3 dead on the move family, and the third would
make 148 operations unattributable.

---

## 17.12 Not in this increment

- **E-TYPE's negative direction, and with it the six `drop_resource` branch-arm sites.** §17.1.5 is the
  argument. It is **not** that a wrong `F` in a scope entry differs in kind from a wrong answer
  elsewhere — round 1's C12 showed that is architecturally false, since `_scope_entry_value` runs the
  same evaluator every rule here extends (`plr-sema/src/plr_sema/check/predicate.py:1011-1025`). It is
  that an exactness field is a **derived type claim over a corpus this increment cannot audit**, that it
  clears **six sites at once** through a cascade, and that it needs an `IR_VERSION` bump re-keying every
  cached entry (`plr-sema/src/plr_sema/check/ir.py:178-191`). **D11, recommended NO**, with §17.8.1
  blocks (10) and (11) as the data increment 9 must argue it from.
- **D5a's production (5), the residual-`**kwargs` Term — REFUSED in spec_version 2, having been taken
  in spec_version 1.** §17.5.2 derives why: the move family's third `_check_args` call site sits behind
  a `**` unpacking M1 clause 4 refuses
  (`plr-sema/src/plr_sema/derive/bindings.py:966-975`), §17.5.1's fold is conjunctive over every
  admitted site, so the production buys **zero operations** at this pin. Reaching `:383` here needs four
  productions and four hops. **D10, recommended NO.** D5a's other four productions — a `keys()` term, a
  set-difference `BinOp`, an `E-SIG` family, and the general both-directions model — stay increment 9's,
  exactly as increment 7 §16.14 left them.
- **A relaxation of M1 clause 4.** Propagating a `**<name>` unpacking into a callee's VAR_KEYWORD
  parameter is the first of `:383`'s four missing hops and is priced in §17.5.2 rather than attempted.
- **An enum-constant `Term` production and an enum equality rule.** Refused by name in §17.5.2: it
  would decide `:383`'s own predicate at `move_resource`'s two literal call sites and still not close
  the site, because the fold declines at the third
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2079-2081`).
- **Binding `destination` in `drop_resource`.** M3 binds call-site **constants**; `to` is the entry
  point's own argument and needs full argument composition across two hops. It buys nothing without
  E-TYPE's negative direction, and taking it alone would be machinery with no consumer.
- **The `resource`-payload route to `:2233`/`:2290` on `move_plate`.** §17.1.5's second box: the
  typestate could bind it, E-TYPE's positive direction could decide it, and it would clear two of six
  sites on 31 of 93 operations. **Published by T55 as a measured extra and never gated**, because it
  breaks the residual's uniformity for no operation gained.
- **Retiring `unresolved_delegate`.** §17.6's box. Zero population is not a dead fallback.
- **A membership case for `self._resource_pickups`.** No guard at this pin tests membership in it
  (§17.3), and admitting one nothing reads is the growth §16.2.1's closed list exists to prevent.
- **Any further observation field.** `arm_slots` is the only addition, and increment 7 §16.2.1's
  refusals — `strictness`, per-well seeded volumes, lid topology, `head96`, `_default_use_channels`,
  anything read from `after`, and the value of any guard's own condition — stand unchanged and are not
  re-litigated here.
- **Virtual dispatch outside inherited bodies.** §17.2 condition 4's receiver-class-first step is
  scoped to bodies M-INH itself admits. Applying it to every record would be a benchmark-wide
  resolution change this increment neither needs nor measures.
- **The γ loop idiom, the `pred`-aware `BRANCH`, tuple-display comparison, arithmetic `BinOp` terms, a
  fourth loop-append binding idiom, the well-seeding observation, and the general `Identity(Term,
  Term)`.** Increment 7 §16.14's dispositions all stand, and this increment adds a further reason for
  the arithmetic `BinOp`: its one move-family consumer is `:2211`, which sits behind the refused
  mechanism anyway.
- **A thirteenth `REASON_VOCABULARY` member.** §17.6's table folds every new give-up point into an
  existing one, mechanically.
- **A new registry row, in every branch.** §17.7. `live_rows()` stays 25 against `BUDGET_CAP` 25 and
  the only ask is two per-row ceiling units.
- **Replacing §8's hand-written-contract bridge**, and **precision targets, deferred row (f)**. Both
  recorded, not discharged, exactly as increments 6 and 7 record them.

---

## 17.13 The questions, their dispositions, and every user decision hook

### Q7 — is the `unresolved_delegate` gap semantic or mechanical?

**DISPOSED by §17.1.1 and §17.2: mechanical, and closing it costs no registry row.** `Resource`'s
`_state_updated` is two lines with no `raise` and no `assert`
(`external/pylabrobot/pylabrobot/resources/resource.py:932-934`); the survey resolves `self.<name>`
against the class's own body alone (`scripts/survey_plr_preconditions.py:347-357`) and `resolve` within
the same module alone (`plr-sema/src/plr_sema/derive/__init__.py:414-421`). **What round 1 changed:**
the *stated ground* was wrong (`_state_updated` does contain a recordable call), the base-name
extractor was **not** shipped, and the override case needed a fourth fail-closed condition. All three
are now in §17.2, and none of them moves §17.8.3's `0`. **The alternative considered and rejected: a
site-keyed exception for this one call.** That is HM-26's class, a fourth keyed rule and a registry
unit, for a defect that is general across the whole PLR surface. **Rejected, and recorded as rejected.**

### Q8 — can the `_resource_pickup` typestate reuse increment 1's model unchanged?

**DISPOSED by §17.1.3 and §17.4: the ORDERING is new, the ROUTE TO A VERDICT is not, and spec_version 1
failed to say the second half.** `TipWalk` carries one state per receiver per CALL
(`plr-sema/src/plr_sema/check/tipstate.py:521-543`); the three move guards live inside one CALL and read
two different states, and the **intra-operation ordered walk** is what closes that. But the state
reaches a verdict through increment 1's own `_null_check`/`atom_truth`/`_finding_for_atom`
**components** and its reason-agnostic `consumed`-index **replacement protocol** (§17.4.0), not
through the predicate evaluator — which retires round 1's
fifth-`EnvRef`-path and broadened-`Is` asks entirely and fixes `p3a`'s denominator at 93.
**Round 2 corrected the second half of that answer and the correction is recorded here rather than
only in §17.17**: the components and the protocol are shipped, the *entry point* that combines them
for a channel-free anchor is **not**, so §17.4.0 specifies a new `evaluate_anchor_call` and a new
`AnchorWalk` and prices them (~30 LOC, T52's re-size to ~330). **The reuse claim is narrower than
spec_version 2 made it and the ask is one unit larger in scope, not in count** — unit 12 still covers
exactly one hand-maintained pattern, and `_measure_hm25` still lands at 12 because `atom_truth` is
generalised rather than duplicated.
**No new named assumption is needed** and §17.4.3 says why, now that condition 2 tests a handler's
terminator shape instead of asserting a control-flow fact.

### Q9 — why did increment 7's `:375`/`:383` prediction miss on 321 operations?

**DISPOSED ON THE ATTACHMENT HALF; THE SELECTION HALF IS ROUND 2's R2-C1 and is disposed by §17.1.4's
second normative box.** spec_version 2 marked this question "DISPOSED IN FULL" and §17.16's C3 row
called M-SURF "the real cause". **That was a completeness overstatement, and it is the single line
round 2's defender identified as most worth weakening** — because it is what licensed the frontmatter's
decision not to read `plr-sema/data/derived_contracts.json`, the artifact in which the second half is
plainly visible (ten `*.pick_up_resource` rows, zero `*.drop_resource`). M-SURF is **a** real cause — the
attachment half — and the surface *selection* half is a second, independent half of the same cause:
no row exists for a method name that only ever appears at depth ≥ 2, so the attachment fix alone has
nothing to look up. **Both halves are now specified, the selection half is T54's, and the frontmatter
reads the artifact.**

spec_version 1 named two candidate causes and left 148 operations undiagnosed; the challenger proposed
a third; the defender falsified the third and re-derived the traversal. Re-deriving it from the shipped
code turned up a fourth that explains **all 321 at once and none of the first three is it**:
`derive/__main__.py` attaches the derived backend surface only to contract entries whose own guards'
`predicate` carries a `self.backend.<method>(...)` `EnvRef` call
(`plr-sema/src/plr_sema/derive/__main__.py:341-356`), the only such guard in `LiquidHandler` is
`pick_up_tips`'s (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:506-512`), and
`_check_args_surface_row` declines without a row
(`plr-sema/src/plr_sema/check/predicate.py:1234-1249`). That is exactly why the two clusters carry
byte-identical populations. **M-SURF is the fix for that half and it is T49's own missing half**; M1's
two fences are real but they explain only which of the 321 additionally need M3. **And the SELECTION
half is the second half of the same cause, added at spec_version 3**: even with the surface attached,
`_check_args_surface_row`'s key `f"{backend_class}.{method}"` has no `rows` entry for
`drop_resource`, because row candidacy is decided by `collect_env_ref_method_names`
(`plr-sema/src/plr_sema/derive/receiver_state.py:1486-1501`), which reads only `predicate` and
`caller_args`, and `caller_args` exists only at depth 1. §17.8.1 blocks (4) and (6) are where T55 —
and, for block (4), T53 and T54 themselves — confirm or falsify both halves.

### Q10 — what may the headline claim?

**DISPOSED: no joined `SAFE`, and the refusal is stated before the gate rather than at it.** `move_*`
stays `UNKNOWN` under both `verdict` and `scope_verdict` on all 93 operations, and §17.1.5 and §17.5.2
name the two obstructions, size them and refuse them. **What the sprint may claim under D7, D8 and D9
all taken:** the move family's residual reduced from thirteen sites to **seven**, six of them in one PLR
function behind one named mechanism and the seventh priced at four productions; `unresolved_delegate` at
**0 findings** benchmark-wide, the first `REASON_VOCABULARY` member to reach zero population; **`:375`
discharged on all 321 operations and `:383` on 201 of them**, which closes increment 7's own divergence
and names the 120 it does not reach; `n_findings_decided` **2,817 → 3,711**; `n_findings`
**3,903 → 2,823**; and increment 7's 216
preserved. **It may NOT report a joined `SAFE` on any operation other than the 216 that already have
one**, and §17.8.2's conditions (2)-through-(5) exist to make that claim checkable rather than trusted.
**Under a total decline of D7, D8 and D9 it may still claim `:375` and `:383` on the 148 and the closed
diagnosis**, because M-SURF needs no hook.

> **Normative (what the headline may NOT claim about the `:375` fix's provenance, new at
> spec_version 3).** The 321 figure is **D8-dependent for 173 of its operations** — the 80
> `transfer`/`discard_tips`/`stamp` and the 93 `move_*` — and D8-dependent in **both** halves of the
> surface machinery, not only in the argument map (§17.1.4, round 2's R2-C1). A sprint report that
> credits "all 321" to M-SURF, or that credits the fix to one row when three T54 pieces bought 173 of
> it, is the same absorbed-divergence failure §17.1.4 exists to prevent, one increment on. **The
> attribution is: T53 buys the 148 with no hook; T54 buys the other 173 behind D8.** §17.8.4's
> falsification map carries it per mechanism and §17.8.1 block (4)'s row counters make it
> mechanically checkable at T53 and T54 rather than only at T55.

### The user decision hooks, together, each with this document's recommendation

| id | the decision | what it costs | what declining costs | recommendation |
|---|---|---|---|---|
| **D7** | HM-25 `declared` **10 → 12** — **two** per-row ceiling units: (11) §17.1.2's amended predicate-position clause, (12) §17.4's singleton-anchor and effect shapes | two ceiling units; `live_rows()` and `BUDGET_CAP` both **unchanged at 25**; no cap conversation | both units declined: `:2055`, `:2070`, `:2120` and `:2147` stay ½ on 93 and the residual is **eleven**; `p3a` is withdrawn with its criterion; ~440 LOC leaves the increment. The units are separable and §17.8.2's table prices each half | **YES.** Unit 12 is increment 1 P2's own class, already the row's first entry (`plr-sema/src/plr_sema/_hand_maintained.py:1000-1054`), and HM-25 is the LOUD-failure row whose `breaks_when` this increment's published selections satisfy. **Unit 11 is spec_version 1's own error corrected against itself**: it argued the clause rode D4's unit, and round 1 showed D4's probe imports `_resolve_env_ref` (`plr-sema/src/plr_sema/_hand_maintained.py:350-362`) while the clause lands in `evaluate_predicate`. Asking for two is the honest number and it moves the ask UP |
| **D8** | **M3** — collect the admitted call-site set across the **whole closure**, fold conjunctively over it, and lift M1's `depth == 1` restriction for **call-site-constant arguments only** — **plus, at spec_version 3, the surface SELECTION extension and the attachment filter's `caller_args_sites` scan** (§17.1.4, round 2's R2-C1), which are what make a depth ≥ 2 method name a surface row at all | zero registry; two deliberate soundness fences relaxed and a buffered second traversal pass added, which is why T54 is ~340 and not spec_version 1's ~200; a new additive wire field with a cache round trip; and `n_surface_rows`/`n_surface_candidates` move off their pin values, which block (4) publishes | `:375` stays ½ on the 80 `transfer`/`discard_tips`/`stamp` and the 93 `move_*` operations, and the gate's residual is **eight** — and it stays ½ for **two** independent reasons now (no row and no argument map), so a partial implementation of this hook buys nothing. **M-SURF still lands**, so the 148 clear either way and increment 7's divergence is still closed on them | **YES.** The lift is genuinely **narrower** than the depth-1 map D1 already permits: a call-site constant is resolved against no namespace at all, so clause 6's reason does not apply to it. The closure-wide fold is **strictly more conservative** than the single-site rule it replaces — it ranges over a superset of the executed sites and can only decline more often — and it is the only version of M3 that is both sound and uniform across all 93, which is what round 1's C2 forced |
| **D9** | **M-INH** — resolve inherited `self.<name>()` calls across the whole PLR surface, with virtual dispatch inside inherited bodies | zero registry; but it changes the closure for **every** entry point and can move every number in the benchmark, including increment 7's 216 — **and it perturbs per-guard DEPTH benchmark-wide with no guard body changing**, which is round 1's C11 and which block (1)'s depth multiset exists to make visible | `unresolved_delegate` stays at 186 findings on 93 operations; condition (2) is unreachable; **and §17.5.1's site-set condition makes M3 decline on the whole move family, so `:375` joins the residual too — nine entries.** This is the hook whose decline cascades | **YES.** The fix is derived from a whole-tree index with no PLR name typed, and the gap it closes is a two-line function that cannot raise. **It is a decision and not a sprint choice** precisely because of the blast radius: §17.8.2 makes the 216 a hard gate condition, §17.2's doubling bound stops the row rather than landing a closure nobody sized, and the depth multiset is published before and after |
| **D10** | The **residual-`**kwargs` Term** — D5a's production (5), giving the shipped `:383` site rule a second discharge route | one grammar production, one comprehension rule, and — to actually reach `:383` on this family — three further productions and a relaxation of M1 clause 4 | nothing on this benchmark. `:383` stays ½ on the move family's 93 and on `stamp`'s 27 in **both** branches | **NO, this increment — a REVERSAL of spec_version 1, and the reversal is derived rather than tactical.** §17.5.2 shows the conjunctive fold declines at `pick_up_resource`'s call site whatever the Term does, so production (5) alone buys **zero operations** — the exact trade §9.4 forbids and the exact argument spec_version 1 used against the enum-constant `Term`. Its completeness claim is also unsupportable in **both** lanes as written (`plr-sema/src/plr_sema/check/ir.py:577-590`, `:793-806`), which round 1's C7 established and which increment 9 must state as a precondition before taking it |
| **D11** | **E-TYPE's negative direction** — an exactness fact on `ir.Resource`, so `isinstance` can decide `F` and E-SCOPE can clear the six `drop_resource` branch-arm sites | an `IR_VERSION` bump that re-keys every cached entry, and a derived `F` in a **scope** entry that clears six sites through one cascade | the move family's residual stays at seven sites and `move_*` cannot reach `scope_verdict == SAFE` in increment 8 or 9 without it | **NO, this increment.** The recommendation is unchanged from spec_version 1; **the argument is not.** It is no longer that a scope-entry `F` differs in kind — round 1's C12 falsified that, since every mechanism here is live inside `_scope_entry_value`. It is that the input is a derived type claim over a corpus nothing currently publishes, that one wrong claim is six wrong answers, and that it is not a risk to take alongside four other new mechanisms. **T55 publishes blocks (10) and (11) so increment 9 argues it from data**, and the recommendation there may well be YES |

---

## 17.14 Implementation record

*(Column shape mirrors increments 5, 6 and 7. No row is started; the whole table is prospective.
First-column ids are deliberately unbolded so the cross-reference lint's task-row pattern does not read
this table's cells as gate cells.)*

| row | commit | what landed | measured vs the spec's expectation | divergences |
|---|---|---|---|---|
| T50 | `266f4c41` | M-INH, both halves. Half 1 extends the survey's per-`ClassDef` method-name set with the transitive base closure and adds the additive `inherited_delegates` field; Half 2 gives `resolve` its third step, tried only after the two same-module steps. The base-name extractor, the `(module, name)` collision index and all four fail-closed conditions are implemented, with condition 4's receiver-class-first dispatch scoped to newly-admitted bodies only. All new threading is additive opt-in kwargs, so omitting them reproduces pre-T50 behaviour exactly. | `_state_updated` resolves to `Resource._state_updated` and contributes **zero guards**; `move_lid`/`move_plate`/`move_resource` now carry an **empty `gaps` list** — the 186-finding / 93-operation `unresolved_delegate` cluster's root cause is closed at the contract level. Closures grew 8→10, 8→10, 7→9 with **guard counts unchanged at 13/13/13**, and the **per-guard depth multiset is unchanged for every one of the ten `SUPPORTED_TOOLS` entry points**. Condition 3's doubling bound never tripped. `half1_admitted` 510; refusals `ambiguous` 0, `base_outside_surface` 0, `class_name_collision` **1**, `no_ancestor_defines` 455 over the residual population. `LiquidHandler` confirmed to have more than one base, so condition 1 is live rather than hypothetical. | **Two divergences, both reported by the row rather than found afterwards.** (1) **`half1_ambiguous_mismatch` = 12**: Half 1's union-of-ancestors admission rule carries no ambiguity check, so it admits a name as a delegate that Half 2's stricter `resolve` then refuses as ambiguous. §17.2's boxes did not anticipate the asymmetry. The consequence is a **reason change, not a wrong answer** — those self-calls move from `unresolved_delegate` to `no_contract_derived`, both `UNKNOWN`-side. (2) Consequently **`no_contract_derived` goes 0 → 19 gap instances at the contract level** (measured by diffing the regenerated table against `bd3e2e56`: 19 added, 0 removed), over ~15 entries — 8 `assign_child_resource`, 6 `get_resource`, 3 `_send_action_command`, 2 `_send_framed_command`. **Every carrier is a deck constructor, a deck method, `Loader.unload`, or `ExperimentalBioTekEL406Backend`; none is a `LiquidHandler` method or reachable by a `self.<n>()` call from one**, so the expectation is **zero benchmark findings** and no movement in `n_findings`. **This is an expectation, not a measurement, and T55 must measure it**: if the benchmark's `no_contract_derived` comes back non-zero, **AC-17.6's `n_findings` 2,823 is wrong by exactly that count** and must be corrected rather than the assertion relaxed. `unresolved_delegate` gaps unrelated to `_state_updated` (498 `send_command` and ~64 others) remain at the contract level and are expected to keep contributing zero findings, as they did before this row. **(3) Citation drift, expected and partly deferred.** T50 edited `survey_plr_preconditions.py`, `derive/__init__.py`, `derive/__main__.py` and `receiver_state.py`, shifting line numbers other specs cite. Six citations in THIS spec and two each in the main pre-corpus spec and increment 7 broke and were **repaired immediately**, because those three specs were passing and the gate requires they stay so. Increments 2, 3 and 5 each gained a newly-drifted citation as well (their first-reported failing citation changed), but those three specs were **already** in the accepted pre-existing increment-1..6 failure set, so `test_spec_lint.py` still reports the baseline **6 failed / 24 passed** with both increment-8 params green. Their drift is **deliberately NOT repaired here**: T51, T52 and T54 edit the same files again, so a sweep now would simply re-drift. **T56 owes a full citation-drift sweep across increments 1-6 once every source-editing row has landed** — that is the row's stated purpose and it is the correct place for it. | 
| T51 | `5a01e2af` | R-ARM and the amended predicate-position clause (§17.3/§17.1.2). `capture_observation` gains the additive `arm_slots` field (`sorted(machine._resource_pickups)`) at the SAME single capture point O3 fixes — no second capture point, `OBSERVATION_KEYS` closed at five. `_resolve_env_ref` gains a new `rule="R-ARM"` branch resolving `EnvRef(("self","_resource_pickups"), None)` to the observation's `arm_slots` `Seq`. `evaluate_predicate`'s `EnvRef` branch is amended: `isinstance(value, ir.Seq) and rule in ("R-HEAD", "R-ARM")` decides by truthiness (`T` iff non-empty, `F` iff empty) BEFORE the `ir.Lit` branch, with the `self.head` shape refusal kept unchanged and checked first, by shape. HM-25's unit-11 probe (`_r_arm_truthiness_clause_probe`) imports and exercises `evaluate_predicate` directly, asserting the complete-`Seq` case decides while the kept `self.head` refusal still returns ½. | `_measure_hm25()` == **11** == `declared`; `live_rows()` == 25 against `BUDGET_CAP` == 25, zero new rows; `productions` unchanged at 3. `:2055` decided `SAFE` end to end through the REAL, unmodified `LiquidHandler.pick_up_resource` guard record (the `derived_contracts.json` entry already carried the `:2055` guard as a self-entry, depth-0, `reachability_clear: true` record from an earlier row — this row supplies the resolution, not the wiring). No observation still yields `UNKNOWN`/`guard_env_dependent`, unchanged. Every number matched this row's own prediction exactly; none diverged. | **None.** The stability precondition (§17.3's own box) was asserted directly (AC-17.2) by monkeypatching `verify.verifier.capture_observation` to retain a reference to the live `machine` object across a real `move_plate` (pick-then-drop) run and comparing `sorted(machine._resource_pickups)` before/after — `pick_up_resource`/`drop_resource` never change the key SET, only the per-key value, exactly as predicted. The placement half (`arm_slots` empty before `await setup.machine.setup()`, non-empty after) was asserted directly against `verify.deck.capture_observation`, mirroring `head_channels`' own placement argument. Citation drift: this row's edits to `predicate.py`/`_hand_maintained.py`/`oracle_common.py` shifted line numbers seven OTHER specs cite; all seven broke citations (six in THIS spec, one each — after the first pass — newly surfaced in the main pre-corpus spec and increment 7) were repaired in the SAME commit, and increment 7's own §16.5.1 text was amended in place (the sentence T51's own box names as now false) together with its code-comment echo in `predicate.py`'s module docstring, both in this commit as required. `test_spec_lint.py` stayed at the accepted baseline **6 failed / 24 passed** throughout, both increment-8 params green. |
| T52 | `9d0f2cc2` | The `_resource_pickup` typestate, all seven §17.4.0 decisions and §17.4.2/§17.4.3. **P5** (`receiver_state.compute_singleton_typestate_anchors`/`_singleton_anchor_candidate_fields`/`_singleton_anchor_absent`): a whole-surface, purely-syntactic scan for `(class, field)` pairs satisfying the three conjuncts, with the three-clause absence rule (clause 3's getter/setter-pair exception implemented as stated). **Measured whole-surface: `LiquidHandler` carries TWO surviving anchors, not one** — `_resource_pickup` and `_blow_out_air_volume` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:166`) — so `ReceiverState.anchor_field` (singular, as first drafted) was widened to `anchor_fields: tuple[str, ...]` before landing; `AnchorWalk` is keyed on `(receiver slot, field)`, never receiver alone, and `InlinedGuard` carries both `anchor_state` and `anchor_field` so a guard's own walk lookup is unambiguous. **P6** (`receiver_state.compute_anchor_guard_states`): a NEW derive-time source-order walk, independent of `_walk_closure`'s own LIFO frontier, recursing into resolved bare-`self` delegate calls (same-class first, `resolve_via_base_closure` fallback for `_state_updated`'s cross-class resolution) and implementing all five widening conditions, including R2-C6's handler-terminator fence. `derive_contract` gains the opt-in `anchor_fields` param, runs P6 once per field at `depth == 0`, and attaches `anchor_state`/`anchor_field` per guard by lineno; `DerivedContract.anchor_net_effects` (`{field: net_effect}`) is the new per-entry additive field `derive/__main__.py` writes into the JSON. **The seven closed decisions**: `evaluate_anchor_call` (new, `check/tipstate.py`) mirrors `evaluate_call`'s `(findings, consumed)` shape, runs before it in `check/__init__.py`'s `_findings_for_call`, has NO `channels is not None` gate, reuses `_parse_atom` unchanged with `bool_view_attr=""`, reads state via a NEW `AnchorWalk` class, and — decisively — `atom_truth`/`_finding_for_atom` are GENERALISED (a `_TOP_MEMBERS`/`_POSITIVE_MEMBERS` protocol both `TipState` and the new `PickupState` satisfy) rather than duplicated; `_finding_for_atom`'s ½-branch reason is parametrised via an if/else dispatch to two literal `Finding(...)` sites (`"channel_state_unknown"` / `"guard_env_dependent"`) rather than a bare dynamic `reason=reason` pass-through, because §3.3's citation-lint requires every vocabulary member to be reached by >=1 STATIC literal `Finding(...)` site (a `vocabulary_reason(reason)` indirection was tried first and satisfies the forward direction only — it broke the reverse closure check, since it hides `"channel_state_unknown"` from every static site). `check_ir` threads a fresh `anchor_walk` through the SAME region-stack pass `TipWalk` uses, including region-entry widening for every known anchor field. HM-25's unit-12 probe (`_singleton_anchor_absence_probe`) imports `_singleton_anchor_absent` (a symbol distinct from `_typestate_anchor`) and exercises all three absence clauses via three synthetic fixtures. | `_measure_hm25()` == **12** == `declared`; `len(productions)` unchanged at **3** (the generalisation, not a duplication); `live_rows()` == 25 against `BUDGET_CAP` == 25, zero new rows. On the regenerated `derived_contracts.json`, `move_resource`'s (and `move_lid`'s/`move_plate`'s) own P6 walk over `_resource_pickup` yields EXACTLY `{2070: "ENTRY", 2120: "HELD", 2147: "HELD"}` with **zero** widening on all four conditions this pass can trip (1/2/3; condition 4 is AnchorWalk's own default, condition 5 the join, neither bites at this pin) and `anchor_net_effects == {"_resource_pickup": "EMPTY"}` — matching §17.4.3's own worked example exactly. End-to-end through `check_graph` against the real, unmodified guard records: `:2120`/`:2147` decide `SAFE` on a single `move_resource` call (their pre-state is a derive-time CONSTANT, independent of the walk); `:2070` decides `SAFE` on a SECOND sequential call (carried `EMPTY` from the first call's own net effect) and `UNKNOWN`/`guard_env_dependent` on an isolated first call (fresh-walk `TOP`) — both asserted individually, per AC-17.3. The anchor/channel `consumed` sets are disjoint by construction (asserted directly: a synthetic receiver mixing a channel-scoped own guard with a bare-`self` anchor guard splits `{0}`/`{1}` exactly). `backend_surface` counters (160/71/89) and M-INH's own printed selection are byte-for-byte unchanged by this row's regeneration — confirmed via diff, purely additive (`anchor_state`/`anchor_field`/`anchor_net_effects` keys, `null`/absent on every non-anchor guard/entry) plus 3 provenance-stamp lines. `n_typestate_decided`/`n_typestate_widened` are NOT wired into a live report by this row — §17.8.1 states that block is "What T55 publishes"; T52 instead exposes `compute_anchor_guard_states`'s own `widened_by` return value as a directly-testable pure function (asserted `{0,0,0}` on the real move-family closures), which is what T55 will aggregate. | **One divergence from the spec's own text, surfaced and resolved rather than hidden.** §17.4.0/§17.4.2 describe "the singleton typestate anchor" in the singular throughout, and `AnchorWalk`'s own decision-5 prose says "carrying one `PickupState` per receiver". Measured whole-surface, `LiquidHandler` satisfies P5's three conjuncts for TWO fields, not one (`_resource_pickup` and `_blow_out_air_volume`, unrelated — the latter belongs to `aspirate`'s own guard, not the move family). Picking an arbitrary "winner" by field name would either (a) hand-type the one PLR fact this increment is built to avoid hand-typing, or (b) silently drop a second, independently-valid, mechanically-derived anchor. Neither is acceptable, so the implementation generalises: `ReceiverState.anchor_fields` is plural, `AnchorWalk` and `InlinedGuard.anchor_field` are keyed per-field, and `evaluate_anchor_call` loops over every field a receiver carries. This is STRICTLY MORE GENERAL than the spec's own singular design, changes nothing about the move family's own three guards (all reading `_resource_pickup` only), and every AC-17.3 assertion the spec actually names still holds; it is recorded here because the spec's own words assumed a cardinality the real surface does not have. **No other divergence** — the pin-level guard-state assignment, the zero-widening claim, and the HM-25 arithmetic all matched the spec's own prediction exactly. |
| T53 | `8adb83f4` | M-SURF (backend-surface attachment filter extends to `caller_args`): extends the filter in `derive/__main__.py:377-410` (line numbers as they stand after T50's edits to the same file) to scan not only a guard's `predicate` JSON but also its `caller_args` map for `self.backend.<m>` EnvRefs. The `caller_args` arm requires **no** `args is not None` check. Adds published `n_entries_with_backend_surface` counter to the `backend_surface` sub-object. | `n_entries_with_backend_surface` 5 → 13. The eight newly attached are `LiquidHandler.aspirate`, `aspirate96`, `dispense`, `dispense96`, `drop_tips`, `drop_tips96`, `pick_up_resource`, and `pick_up_tips96`. R-CONST `n_resolved_by_rule` unchanged at 223 (R-CONST reads only predicate-borne `EnvRef`s with `args is not None`). Row counters unchanged at 160/71/89. No new rows added (T54's responsibility). `has_var_keyword` verified `True` for chatterbox `aspirate`, `dispense`, `drop_tips`. | **Broader attachment than the three named methods.** Spec predicted `aspirate`, `dispense`, `drop_tips` as the required-present subset; implementation attached eight, adding the four `96`-suffixed variants and `LiquidHandler.pick_up_resource`. Mechanism is correct (all eight have `self.backend.<m>` EnvRefs in `caller_args`); the five additional entries are real attachments, not spurious. **`LiquidHandler.pick_up_resource` is relevant to T54** because `:2079` (the move family's third `_check_args` call site) sits inside `pick_up_resource`, so T54 must account for this entry's newly-attached surface when reasoning about the move family's site set. T55 confirms R-CONST `n_resolved_by_rule` by measurement (unchanged, no new predicates to resolve). |
| T54 | — | — | — | — |
| T55 | — | — | — | — |
| T56 | — | — | — | — |

---

## 17.15 Specification log

**spec_version 1 written 260909 by `praxia:specification-specialist` at Opus against final HEAD
`52178d80`; spec_version 2 written the same day by the same role after adversarial round 1; spec_version
3 written 260910 by the same role after adversarial round 2 — all three in worktree
`wt-20260909-172820`, with no shell access — every claim in this document is either read from source at
the cited lines, read from the two instrument files, or read from
`plr-sema/data/derived_contracts.json` (newly read at spec_version 3), and none is measured by this
author.**

**What spec_version 1's investigation found that the dispatch brief did not contain**, retained because
each still shapes the increment:

1. **The brief named SEVEN `guard_env_dependent` clusters at 93 operations. There are NINE.** `:2284`
   and `:2290` are the two it omitted
   (`outputs/plr-sema/unknown_ledger_260909_final.json:652-662`, `:692-702`). The residual is thirteen
   entries, not eleven.
2. **The `unresolved_delegate` gap is not semantic.** The brief's framing presumed a contract that
   could not be derived; the truth is a resolution rule that never looks at base classes.
3. **The three move methods have an IDENTICAL residual, not merely a similar one**
   (`outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json:241-261`). That is what makes a
   structural gate possible at all.
4. **`:375` and `:383` are increment 7's own falsified prediction**, still open at 321 operations.
5. **The chatterbox backend's move methods take no `**backend_kwargs`**
   (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:223-231`), which is why the
   shipped `:383` rule can never fire for this family.
6. **The typestate the brief anticipated is real but is NOT increment 1's shape** — the ordering is
   intra-operation.

**What spec_version 2's re-derivation found, and each of the four changed a number:**

7. **`:375`/`:383`'s cause is the surface ATTACHMENT filter, not either M1 fence** — thirty lines in
   `derive/__main__.py` (`plr-sema/src/plr_sema/derive/__main__.py:341-356`). Q9 goes from partially
   disposed to disposed, the 148 clear with no decision hook, and `:375` is predicted at 0
   benchmark-wide.
8. **`caller_args` is computed against the ENTRY POINT, always** — so a depth lift alone binds nothing
   for `move_lid`/`move_plate`, and the fold has to range over the whole closure to be both sound and
   uniform. T54 rises 100 LOC.
9. **`:383` cannot be reached on this family at any price this increment should pay**, because the
   third call site sits behind a `**` unpacking. The residual is seven, not six, and D10 flips to NO.
10. **The typestate never touches the predicate evaluator**, which deletes two asks round 1 priced and
    triples `p3a`'s denominator.

**What spec_version 3's round-2 remediation found, and what each one moved:**

11. **The surface has TWO halves and spec_version 2 fixed one.** Row *attachment* is
    `derive/__main__.py`'s filter; row *selection* is `collect_env_ref_method_names`, and it selects no
    `drop_resource` at this pin, so **ten** `*.pick_up_resource` rows exist and zero `*.drop_resource`
    rows do. **T54 gains two pieces, rises 300 → 340, and the `:375` claim becomes D8-dependent in both
    halves for 173 of its 321 operations. The `321 → 0` prediction survives** because the repaired
    selection provably produces a row that clears the site rule at the pin. **And the selection half's
    blast radius is exact, not approximate**: 160/71/89 → **172/73/99**, derived from
    `pick_up_resource`'s measured twin and asserted by value in AC-17.5.
12. **`n_findings` was arithmetically wrong.** 3,717 counted only M-INH's 186 leaving the UNKNOWN
    population and not the 894 that become decided. **2,823**, and it follows from this document's own
    adjacent by-reason cells without any ledger identity.
13. **The typestate's route was NOT shipped machinery.** `consumed` indices exist only inside a
    `channels is not None` gate with a channel-subscript matcher, and `move_*` has no channel set —
    so the route needed a new evaluator entry point, and §17.4.0 now states it as seven closed
    decisions. **The load-bearing one is that `atom_truth` is generalised rather than duplicated**:
    duplicating it lands `_measure_hm25` at 14–15 and trips T52's own STOP contingency, so D7's
    `declared` 12 depends on a decision spec_version 2 left open. T52 rises 300 → 330.
14. **`p3a` was specified against the wrong harness.** `predicate_mutants.py` is kwargs-only, and its
    `_TARGET_CALL` is hardcoded besides; `tip_mutants.py`'s `make_m2_duplicate_pickup` **is** p3a's
    shape. The class survives, in the other module, and the `:2055` refusal loses the clause that
    contradicted it.
15. **Condition 2's terminator test had an unfenced unsound direction, and this document's own
    self-assessment of it was wrong in the same place** (see the owed-item (3) correction below).

**The targeted verification pass HAPPENED, within spec_version 3, and it found two things — both
recorded here rather than absorbed.** The orchestrator re-ran both lints (citations 303 checked, zero
failing; crossrefs zero AC-gating violations) and then measured the shipped artifact directly rather
than trusting this document's reading of it. **(a) The row count was off by one.** Three places said
"nine `pick_up_resource` rows"; the shipped `rows` object carries **ten**. The error is a real one and
its shape is instructive: **nine of the ten are backend classes and the tenth is
`LiquidHandler.pick_up_resource` itself**, so "nine backend classes" was a correct gloss that both
round-2 reports and this document then reused as a row count. **The mechanical cause is worth naming
because it will recur**: the grep all three passes used matched the class segment with a
digit-free character class, and `OpentronsOT2Backend.pick_up_resource`
(`plr-sema/data/derived_contracts.json:355`) is the one key of the ten whose class name carries digits,
so it was silently dropped by the pattern rather than by the artifact. A count taken from a regex is a
count of what the regex admits; the orchestrator's pass got ten by parsing the JSON and counting keys.
`drop_resource` rows: **zero**, confirmed
exactly, so R2-C1's substance is untouched — only the numeral moved. `n_surface_candidates` 160,
`n_surface_absent_by_c15` 71, `n_surface_rows` 89, and the five tip-path entries carrying an attached
`backend_surface` with **no move method among them** were all confirmed exactly, which is §17.1.4's
attachment diagnosis measured against the artifact rather than argued from source. **(b) The blast
radius was approximate where it could be exact.** "Moves off 89" and "~9 backend classes" are now the
measured triple **172 / 73 / 99**, derived from `pick_up_resource`'s twelve-definition,
two-`@abstractmethod`, ten-row twin, asserted by value in AC-17.5 and checked in T54's own gate cell.
**That is a strictly better criterion than the one this document wrote for itself**, and it is the
kind of sharpening a measuring pass produces that a reading pass cannot: the author had the source and
inferred a direction; the orchestrator had the artifact and got a number. A third correction guards the
overclaim that direction invited — the ten new rows are **heterogeneous**, so the `params ⊆ default`
`F` is scoped to the resolved `m` (§17.1.4's scoping box).

**No third adversarial round.** Round 2's defender ruled the cycle **converging** rather than
thrashing, on a distinction worth recording: round 1's two routes to gate failure were **mechanism**
failures requiring re-derivation from scratch (`compute_caller_args` binds against the entry point;
condition 2's unconditional widening contradicted §17.8.3 at the pin), while round 2's single route is
a **plumbing** failure of an already-correct mechanism — two scan sites must read one more field
beside the one they already read — with the favourable outcome provable at the pin before any run.
The rest of round 2 is one arithmetic slip provable from adjacent cells, one wrong harness named for
one mutator, one missing clause in one widening condition, one ambiguous absence clause the same
paragraph already disambiguates three times, and seven text-level items. **The gate this document now
owes is a targeted verification of §17.17's fourteen rows against their cited lines — a spec-author or
auditor pass, not a fresh adversarial pair — plus one arithmetic re-check that `_measure_hm25` still
lands at 12 under §17.4.0 decision 6.** After that the document is ready to plan.

**The constraint the brief imposed, and how it was met.** The registry is at full cap: `live_rows()`
25, `BUDGET_CAP` 25, zero headroom. **This increment asks for no row in any branch, and spec_version 3
adds no unit either** — §17.4.0's five newly-named symbols are four pieces of code and one
hand-maintained pattern already inside unit 12 (§17.7), and §17.1.4's selection extension is one more
JSON location for an existing derived scan. Every mechanism is
either derived (M-INH, M-SURF, the selection extension, M3), free under a unit already spent (R-ARM,
inside `_resolve_env_ref`), or a further ceiling unit on the existing loud-failure row (D7's two).
`REASON_VOCABULARY` stays 12 of 12, and `_measure_hm25` lands at exactly 12 against `declared` 12.

**Owed before this document is implemented: a round-2 pass** — and it happened. **spec_version 2's
three self-nominated claims, with round 2's answer to each, replacing the hedges rather than leaving
them.**

**(1) §17.1.4's diagnosis — the self-nomination was RIGHT and it is what made the blocker findable in
one pass, but the wrong method was named.** spec_version 2 worried that
`LiquidHandlerChatterboxBackend.pick_up_resource` might be absent from the surface `rows`.
**`pick_up_resource` IS a row** — one of ten — and `drop_resource` is not, and cannot become one
under M-SURF as spec_version 2 specified it, because row *selection* is a different half of the
machinery from row *attachment* (§17.1.4's second box; round 2's R2-C1). **The remedy is specified and
the `321 → 0` prediction is kept**, because the repaired selection provably yields a row whose
`params ["drop"] ⊆ default {"drop"}`. **This claim is now the seventh way §17.8.2's gate can fail**,
checkable at T54 by one counter rather than at T55 by a whole replay.

**(2) §17.5.1's site-set fail-closed conditions — MEASURED, and the answer is POSITIVE. The hedge
"this document cannot measure either" is withdrawn** and replaced with the measurement (round 2's
R2-C10 favourable finding, confirmed independently by both round-2 adversaries). The
`unresolved_delegate` cluster is `n_findings` **186** over `n_ops_blocked` **93**, `condition`
`_state_updated`, `per_method` 31/31/31
(`outputs/plr-sema/unknown_ledger_260909_final.json:812-822`) — **exactly two unresolved calls per
move operation, both `_state_updated`**, and nothing else. **M-INH's newly-admitted bodies add
none**: inside `LiquidHandler.serialize_state`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:214-237`) there is no bare
`self.<n>()` call at all, so it contributes no delegate and no unresolved call;
`callback(self.serialize_state())` in `Resource._state_updated`
(`external/pylabrobot/pylabrobot/resources/resource.py:932-934`) is an `ast.Name` call recorded
nowhere by `visit_Call` (`scripts/survey_plr_preconditions.py:306-320`), while the inner
`self.serialize_state()` is a resolvable self-call and becomes a delegate. **And the other input to
§17.5.1's first condition is 0 benchmark-wide**: `no_contract_derived` is a `REASON_VOCABULARY` member
(`plr-sema/src/plr_sema/verdict.py:147-199`) and it does **not** appear in the ledger's
`n_findings_by_reason` (`outputs/plr-sema/unknown_ledger_260909_final.json:29-38`) — zero such
findings across all 544 executed operations. **The hedge shrinks to exactly one clause**: whether any
visited record lacks a `K`, which comes from a `function_index` lookup
(`plr-sema/src/plr_sema/derive/__init__.py:630-636`) this document cannot evaluate without running
the derive step. §17.8.1 block (5) publishes the decline count under both conditions.

**(3) §17.4.3 condition 2's terminator test — the self-assessment was WRONG, and the correction is
recorded rather than quietly applied (round 2's R2-C6).** spec_version 2 named two shapes and claimed
the test "gets wrong in opposite directions … only one of them errs safe". **Both of the named shapes
err SAFE**: a handler whose last statement is a nested `ast.Try`, and a handler whose `raise` is last
on every path but not last lexically, both fail the `isinstance` test and therefore **widen**. **The
unsafe shape was not named at all**, and it is a handler whose last statement *is* an `ast.Raise` but
whose body contains an earlier `ast.Return` (or `Break`/`Continue` inside an enclosing loop): control
leaves the handler normally, carrying the rolled-back state, and a later guard reads `HELD` while the
field is `None` — a false `SAFE`. **Condition 2 now fences it** and AC-17.3 fixtures it. **This is the
reason the hole was not found by the document itself**: a mis-stated self-assessment is worse than no
self-assessment, because it tells the next round where not to look.

---

## 17.16 Round-1 disposition

**Round 1 was `praxia:spec-challenger` (C1–C21) against `praxia:spec-defender`, both at Opus, both
against spec_version 1. Challenger verdict `not_ready`: 12 blockers, 8 must-fix, 1 suggestion.
Defender: 11 conceded outright, 9 partial, 1 rebutted outright (C10), with C6 largely rebutted on the
same fact.** The round's central finding — that gate condition (1) was predicted to fail on **all 93**
operations — was reached independently by both sides and is accepted here in full. The defender's
disposition is authoritative for this remediation: it re-verified every citation in both directions,
and it is the reason two objections below are recorded as REBUT rather than CONCEDE despite the
challenger being confident on both.

This table records what each objection did to the text. "CONCEDE" means the remedy is now normative
here; "PARTIAL" means the diagnosis was accepted and the remedy or the costing was replaced; "REBUT"
means the text did not change on the merits.

| id | class | disposition | what changed | § touched |
|---|---|---|---|---|
| **C1** | blocker | **PARTIAL — conclusion right, attribution wrong, and the real answer is worse** | `:383` genuinely does not reach `move_lid`/`move_plate`, but not because of `move_lid`'s own `**backend_kwargs` hop: the rule reads only the argument map, unavailable for C2's reason. Re-deriving the fold showed `:383` does not reach **any** of the 93, at the third call site. **D10 flips YES → NO, T54's residual-kwargs row leaves the increment, and the residual is seven** | §17.5.2 (rewritten as a refusal), §17.12, §17.13 D10 |
| **C2** | blocker | **CONCEDE — the true blocker** | `compute_caller_args(entry_K, K)` binds against the entry point and `_find_delegate_call` scans its body only, so a depth lift alone binds nothing for 142 of the "certain 173". §17.5.1(a) is rewritten: the admitted call-site set is collected **across the whole closure** in a second pass over `_walk_closure`'s visited set, with a stated superset-conservatism soundness argument and two fail-closed site-set conditions. T54 re-sized ~200 → ~300 | §17.5.1(a), §17.8.1 block (5), AC-17.5, T54 |
| **C3** | blocker | **PARTIAL — trace conceded, third cause FALSIFIED** | The LIFO trace is right and is reproduced here: `_check_args` lands at depth 2 for `move_resource`, depth 3 for `move_lid`/`move_plate`, and the refusing clause is 6, not "clauses 1–2". §17.1.4's fence table is re-derived from the traversal. **The proposed third candidate cause for the 148 is NOT adopted**: `aspirate`/`dispense`/`drop_tips` have no sibling delegate calling `_check_args`, so the artifact cannot separate them from `pick_up_tips`. Re-deriving instead found the real cause (M-SURF) | §17.1.4 (rewritten), §17.13 Q9 |
| **C4** | blocker | **CONCEDE — the pin-level falsification spec_version 1 invited** | Condition 2 put `:2120`/`:2147` at `TOP` while §17.8.3 predicted `SAFE`; both could not hold, and that alone failed the gate on 93. Replaced by a derived handler-terminator shape test, `isinstance(handler.body[-1], ast.Raise)`, ~5 LOC. **No new named assumption; the table stays at five rows** | §17.4.3 condition 2, AC-17.3, §17.8.1 block (3) |
| **C5** | blocker → must-fix | **CONCEDE, downgraded** | A guard reached at several positions takes the **join** of the states, `TOP` on disagreement — now §17.4.3's fifth widening condition with its own fixture. Downgraded because at the pin no anchor-reading guard sits in a multiply-called function | §17.4.3 condition 5, AC-17.3 |
| **C6** | blocker | **REBUT on the premise, CONCEDE the remedy's core** | The typestate does **not** route through `_resolve_env_ref`/`_eval_is`: it uses `tipstate.py`'s `_null_check`/`atom_truth`/`_finding_for_atom` path with `consumed`-index replacement (`plr-sema/src/plr_sema/check/tipstate.py:507-550`). **No fifth `EnvRef` path shape, no broadened `Is` rule, §17.7's accounting is not short by one.** What survives: the route is now stated normatively, and `n_typestate_decided` is added | §17.4.0 (new), §17.8.1 block (3) |
| **C7** | blocker | **PARTIAL — precondition conceded, direction corrected** | The completeness claim is uncited and unsupportable in **both** lanes, not only the graph lane. The `?<i>` rename half fails SAFE, not unsafe; the real channel is an unmodelled keyword. The precondition is now stated per lane — and, since D10 is refused, it is stated as what increment 9 owes rather than as a rule this increment ships | §17.5.2's precondition box, §17.13 D10 |
| **C8** | blocker | **CONCEDE, both halves** | §17.1.1's stated ground was false: `_state_updated` **does** contain a recordable call, `callback(self.serialize_state())`. Corrected to "zero GUARDS". A **fourth fail-closed condition** is added — an inherited body's self-calls dispatch on the analyzed class, or the call refuses — which bites at the pin because `LiquidHandler` overrides `serialize_state` | §17.1.1, §17.2 condition 4, AC-17.1 |
| **C9** | blocker | **CONCEDE** | "Already shipped" was overstated: `subclass_closure_from_bases` consumes a map nothing builds. §17.2 now specifies the base-name extractor (three AST shapes, whole-class refusal on anything else), names the import-alias incompleteness and publishes its count, and refuses on `build_plr_class_index`'s bare-name collisions. T50 re-sized ~190 → ~230 | §17.2's extractor box, AC-17.1, T50 |
| **C10** | blocker | **REBUT outright** | `_finding_for_atom` returns `WILL_FAIL` with no depth argument and no call to `guard_is_unconditional`, which governs the path the typestate **replaces**. `p3a`'s mutable population is the full **93**, not 31 — adopting the remedy would have written a wrong denominator into the floor | §17.9, §17.4.0, AC-17.3 |
| **C11** | blocker | **CONCEDE** | M-INH changes `delegates_to`, hence push order, hence pop order, hence **depth**, benchmark-wide with no guard body changing. T50 publishes the **per-guard depth multiset** before and after (`InlinedGuard.depth` is already on the wire), and AC-17.1 asserts it unchanged for every entry point whose newly-resolved set is empty | §17.2's direction box, §17.8.1 block (1), AC-17.1, §17.8.2 failure mode 3 |
| **C12** | blocker | **CONCEDE** | The kind-argument is architecturally false: `_scope_entry_value` runs the same evaluator every rule here extends, so the truthiness clause, R-ARM and M3's bindings are all live inside scope entries. D11's argument is restated on its true ground (an unauditable derived type claim, six sites through one cascade, an `IR_VERSION` bump) and **block (10), `n_scope_excluded` per site before and after, is added** — a counter that fences the four mechanisms TAKEN, not only the one refused. **The recommendation is unchanged: NO** | §17.1.5, §17.8.1 block (10), §17.12, §17.13 D11 |
| **C13** | must-fix | **CONCEDE** | All three consumers call `.get` on a `Mapping`, so re-typing breaks them. The per-site list ships as a **new** field `caller_args_sites` beside the unchanged `caller_args`; both site rules fall back; the cache round trip is asserted | §17.5.1(a), AC-17.5, T54 |
| **C14** | must-fix | **CONCEDE, and it raises the ask** | HM-25's tenth unit's probe imports `_resolve_env_ref`; R-ARM lands there and rides it, the amended clause lands in `evaluate_predicate` and does not. Booked as **unit 11** with its own probe. **D7 becomes 10 → 12** | §17.7, §17.13 D7, T51, AC-17.2 |
| **C15** | must-fix | **PARTIAL — premise false, surviving half binding** | `_measure_hm25` returns `len(shape_matchers) + len(productions)`, a mechanical count, so the STOP contingency **is** checkable via the ratchet. But `_typestate_anchor` is already in `shape_matchers`, so unit 12 must name a **distinct** symbol or it passes vacuously. T52 must add and import one | §17.7, T52 |
| **C16** | must-fix | **CONCEDE** | The key set is not invariant — the setter creates key 0 in an empty dict. The completeness declaration now carries an explicit **stability precondition** (the key set is fixed for the whole program after the capture point, true at this pin for `num_arms >= 1`), and AC-17.2 asserts it with a pickup-and-drop sequence | §17.3, AC-17.2 |
| **C17** | must-fix | **CONCEDE** | §17.8.3's table is headed **tier 1** and gains a paragraph naming the graph lane's value per row: `:2055`/`:2070`/`:2120`/`:2147` stay ½ there in every branch, so the graph-lane residual is eleven and the gate is a tier-1 gate | §17.1's table header, §17.8.3 |
| **C18** | must-fix | **CONCEDE** | **Eleven** `_check_args` call sites, not ten; `:2364-2369` added to the enumeration and to AC-17.5 by name; the frontmatter's inherited undercount removed | §17.5.1(b), frontmatter, AC-17.5 |
| **C19** | must-fix | **CONCEDE** | The fifteen-finding list is the ledger's **`collision_ops`** block, a diagnostic selection keyed on `n_row_id_collisions: 12`. Named as such, and block (9) publishes the collision count before and after with a sentence on the gate's denominator | §17.0.1's provenance box, §17.8.1 block (9) |
| **C20** | must-fix | **PARTIAL — citation label narrower, substance fully conceded** | Ways (1)–(3) do live at the cited lines; the function named was wrong (`_entry_satisfies_uncond`, not `guard_is_unconditional`) and the label is fixed. The substantive half is fully taken: a call statement has no `scope_trail`, and condition 1 now derives it from the **shipped** `compute_caller_scope_trail` at the call statement's own lineno — which is also why T52's re-size is smaller than feared | §17.4.3 condition 1, T52 |
| **C21** | suggestion | **CONCEDE, and acted on rather than acknowledged** | The gate is re-derived after C1–C7. Residual **six → seven**; `:383` moved into it by derivation; the certain/diagnosis-dependent split **removed** because Q9 is now closed; failure modes 5 and 6 added; blocks (4) and (10) added so a divergence is attributable rather than merely visible | §17.0.3, §17.8.2, §17.8.3, §17.8.4 |

**Task rows were RENUMBERED between spec_version 1 and spec_version 2, and two rows in the table above
therefore cite ids round 1 never saw (round 2's R2-C14, conceded).** **M3 moved from spec_version 1's
T53 to T54; T53 is now M-SURF, which spec_version 1 did not have.** Round 1's challenger cites "T53"
for M3 in both its C2 and its C13
(`.praxia/docs/audits/260909_plr-sema-move-family-round1-challenger.md:61`, `:263`), and the C2 and
C13 rows above read "T54" without saying so. T50, T51 and T52 are stable across both versions, which
is exactly what made the two shifted ids read as if round 1 had reviewed them. **No row's content was
renumbered at spec_version 3**: T53 and T54 keep their spec_version 2 identities, and R2-C1's fix
moves work *into* T54 rather than moving a row.

**What round 1 did NOT change.** The instrument and every measured fact in it; §17.0.1's
identical-residual observation, which remains the foundation the structural gate rests on; the
`unresolved_delegate` diagnosis and its cheap closure; the `:375` site-rule arithmetic itself
(`params ⊆ default` at every move call site, re-verified against the chatterbox signatures this pass);
D11's recommendation (**NO**, on a repaired argument); the refusal to retire `unresolved_delegate`
(§17.6); the refusal to admit a site list into `excludes_sites` (§17.8.4 refusal 1); and the decision
to state the headline's impossibility before the gate rather than at it.

**The two numbers that moved most.** `:375` went from *"certain on 173, open on 148"* to **0
benchmark-wide** — because the round's pressure on a fence table this document had read from source
rather than from the traversal is what sent it back to `derive/__main__.py`. And the gate's residual
went from six to **seven**, which is the increment claiming less than spec_version 1 did, on a
derivation spec_version 1 did not have.

---

## 17.17 Round-2 disposition

**Round 2 was `praxia:spec-challenger` (R2-C1–R2-C14) against `praxia:spec-defender`, both at Opus,
both against spec_version 2. Challenger verdict `not_ready`: 3 blockers, 4 major, 7 minor. Defender
verdict `needs_revision`: R2-C1 conceded as a blocker and found BROADER than filed, R2-C2 downgraded
to partial, R2-C3 narrowed to partial, R2-C4–R2-C14 all conceded — and the challenger CORRECTED
twice.** The round's central finding — that gate condition (1) was again predicted to fail on all 93
operations — is accepted, on **one** route (R2-C1), not the challenger's two. **Both round-2 parties
independently verified §17.16's twenty-one round-1 dispositions and found none falsely closed**, and
this table is held to the same standard: no concession is recorded as a rebuttal, and every "what
changed" cell names text this document contains.

**The defender is authoritative where the two disagree, and it re-derived from source in two places
that matter.** (i) The `:375` fix does **NOT** reverse §17.11's T53-before-T54 attribution — the 148
reach `_check_args` at depth 1 with `caller_args` populated, so T53 alone still buys them, and the
D8-decline branch is unchanged. (ii) The **`321 → 0` prediction is KEPT** rather than retreating to
the challenger's "residual eight", because
`LiquidHandlerChatterboxBackend.drop_resource(self, drop)` is undecorated and singly-defined
(`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:229-230`), survives C15's
absence rule, and yields `params ["drop"] ⊆ default {"drop"}` so the site rule returns `F`.

Dispositions use §17.16's vocabulary: "CONCEDE" means the remedy is now normative here; "PARTIAL"
means the diagnosis was accepted and the remedy or the severity was replaced; "REBUT" means the text
did not change on the merits.

| id | class | disposition | what changed | § touched |
|---|---|---|---|---|
| **R2-C1** | blocker | **CONCEDE, and BROADER than filed** | M-SURF fixed row *attachment* and left row *selection* unrepaired, so no `*.drop_resource` row exists (**ten** `*.pick_up_resource` rows — nine backend classes plus `LiquidHandler` itself — and zero `*.drop_resource`) and `:375` would have stayed ½ on all 93 with every hook taken. §17.1.4 gains a second normative box specifying **both** halves as T54's: `collect_env_ref_method_names` scans `caller_args_sites`, and the attachment filter does too — the second being the defender's extension, since move-family guards at depth 2/3 carry no `caller_args` at all, so no move entry would be attached either. The move family's `:375` is restated **D8-dependent in both halves**; a **seventh** gate failure mode is added; T54 rises ~300 → ~340. **The challenger's proposed retreat to a residual of eight is NOT taken**: `321 → 0` is kept on the pin derivation above. **The blast radius is stated as an EXACT prediction, not an approximation** — `def drop_resource` has twelve definitions at the pin, exactly two `@abstractmethod`, and `pick_up_resource`'s identical twin (twelve, two, ten rows) gives `n_surface_candidates` **160 → 172**, `n_surface_absent_by_c15` **71 → 73**, `n_surface_rows` **89 → 99**, with 172 − 73 = 99 reproducing today's 160 − 71 = 89; **AC-17.5 asserts all three by value** and T54's gate cell checks them, so a C15 exclusion the twin does not share is a recorded falsification. The ten new rows are also **heterogeneous** (arms/serializing variants carry `has_var_keyword` `True` and `position`/`access` params), so the `params ⊆ default → F` claim is scoped to the resolved `m` — `LiquidHandlerChatterboxBackend` — and the rest are added unread | §17.0.3, §17.1's table, §17.1.4, §17.5.1 clause accounting, §17.7 item 4, §17.8.1 block (4), §17.8.2 (both the gate box and the hook table's D8 row), §17.8.3, §17.8.4, §17.11's ordering box and sizing note, AC-17.4, AC-17.5, AC-17.8, T53, T54, Q9, Q10, §17.13 D8, frontmatter |
| **R2-C2** | blocker → must-fix | **PARTIAL — remedy taken, blocker severity NOT** | §17.4.2's clause 3 read literally makes `_resource_pickup` absent, which would fail the gate on 93. **The remedy is taken in full**: clause 3 is now "defined at more than one lineno **other than as the getter/setter pair of one `property`**", cited against the rule deliberately narrowed, with whose qualname the clause ranges over stated (the property function's; vacuous for a plain attribute) and a three-definition negative fixture added beside the pair. **The severity does not survive** and this is recorded as the document's own defence rather than hidden: the challenger's reading nullifies clause 1 of the same sentence — every property with a setter has two definitions, so clause 3 would fire in every case clause 1 exists to adjudicate — and the favourable outcome was already stated three times (§17.4.2's own narrowing argument, its pin paragraph, and AC-17.3's by-name assertion). It is a documentation defect, not a second independent route to gate failure | §17.4.2, AC-17.3, T52 |
| **R2-C3** | blocker → must-fix | **PARTIAL — gap conceded, "why a fixer is blocked" narrowed, and the load-bearing item is NOT the one the challenger stressed** | §17.4.0's "the route already exists" **overreaches and is withdrawn**: `consumed` indices are recorded only inside a `channels is not None` gate with a channel-subscript matcher, `parse_bridge_atom` is used only in the reason-agnostic `channel_guards` loop which records no index, and `move_*` has no channel set. §17.4.0's four steps are replaced by **seven closed decisions** naming `evaluate_anchor_call`, its position, the explicit no-channel-gate, the reused `_parse_atom` with an empty `bool_view_attr`, `AnchorWalk`, and — **decisively** — that `atom_truth`/`_finding_for_atom` are **generalised over both lattices, not duplicated**, because `_measure_hm25`'s `productions` counts exercised `atom_truth` branches and a duplicate would land the measure at 14–15 and trip T52's own STOP contingency. §17.7 unit 12's scope is re-stated over the five new symbols (one pattern, four code) with the 7+1+1 matchers / 3 productions = **12** arithmetic in full; T52 rises ~300 → ~330. **What narrows it:** the *replacement protocol* genuinely is shipped and reason-agnostic, and the ½-branch parametrisation and T52's ~300 LOC sizing note were already in the text | §17.4.0 (rewritten), §17.7 unit 12, AC-17.3, T52, §17.11's sizing note |
| **R2-C4** | major | **CONCEDE, with a second obstacle the challenger did not name** | `p3a` cannot live in `predicate_mutants.py`: every mutator there is a `Callable[[dict], bool]` kwargs transform over one grounded call's kwargs, and — the second obstacle — `_TARGET_CALL` is a module constant fixed to `pick_up_tips` and read directly by the driver, so even a program-level extension needs the target de-hardcoded. **`p3a` moves to `tip_mutants.py` as a `pick_up_resource` analogue of `make_m2_duplicate_pickup`**, which is exactly p3a's shape for tips, with a `resource`-shift helper beside `_shift_tip_ref`. The `:2055` refusal's "the mutator API mutates kwargs" clause is **withdrawn** and the backend-class ground kept, since the box may not refuse one mutator on a premise it needs false to ask for another. T55's scope cell and file list name `tip_mutants.py` | §17.9 (both boxes), AC-17.3, AC-17.7, T55 |
| **R2-C5** | major | **CONCEDE** | `n_findings` **3,717 → 2,823**. A decided guard is not a finding, so the 894 that become decided also leave the UNKNOWN population; spec_version 2 subtracted only M-INH's 186. The corrected figure is derived from this document's own by-reason cells (1,990 + 495 + 194 + 0 + 144) with the 3,711 + 2,823 = 6,534 = 6,720 − 186 cross-check | §17.8.3, AC-17.6, Q10 |
| **R2-C6** | major | **CONCEDE, and §17.15's own self-assessment of this rule is corrected too** | Widening condition 2 gains "**and** the handler body contains no `ast.Return`, `ast.Break` or `ast.Continue` at any depth; otherwise it widens", with the false-`SAFE` path named at the pin's own anchor and a third AC-17.3 fixture (last statement IS a `raise`, earlier `Return` present, asserted to widen). **Separately, §17.15's owed item (3) claimed its two named shapes err "in opposite directions"; BOTH err safe**, and the unsafe shape was unnamed — corrected in the same pass, because that mis-assessment is why the document did not find the hole itself | §17.4.3 condition 2, AC-17.3, §17.15 owed item (3), §17.11's sizing note |
| **R2-C7** | major | **CONCEDE (bookkeeping)** | Three ACs asserted frozen-benchmark per-operation counts on rows whose gate cells run only pytest files. **AC-17.4's 148 and AC-17.5's 93/80 clauses are re-homed onto AC-17.8, and AC-17.3's `p3a` floor onto AC-17.7** — both already gated on T55, the only row whose gate runs the replay and the ledger — as named sub-assertions, with the withdraw-with-row linkage kept in prose because the crossref lint reads gate cells only and an AC may be gated once. AC-17.4 and AC-17.5 keep the mechanism-level assertions their own rows can evaluate. **No AC was added, renumbered or re-gated**, so the one-gate-each invariant is untouched | AC-17.3, AC-17.4, AC-17.5, AC-17.7, AC-17.8, T55 |
| **R2-C8** | minor → must-fix (upgraded by R2-C1) | **CONCEDE** | Block (4) gains `n_surface_candidates`, `n_surface_absent_by_c15`, `n_surface_rows` and the sorted `rows` key list, each before and after, all four already shipped payload fields; AC-17.4 asserts them **unchanged at 160/71/89** across T53 with `drop_resource` still absent, and AC-17.5 asserts them **by value at 172/73/99** across T54 with `drop_resource` present by name — the exact triple derived from `pick_up_resource`'s measured twin, not merely "moved off 89". This is now the cheapest falsifier of §17.1.4 and it fires at T54 rather than at T55 | §17.8.1 block (4), §17.8.2 failure mode 7, §17.8.4's map, AC-17.4, AC-17.5, T53, T54, T55 |
| **R2-C9** | minor | **PARTIAL — attribution defended, substance conceded** | The "10 of 4,770" figure was quoted **as** a code comment and the quote is verbatim, so it was not a misrepresentation of the artifact — it was a stale number repeated accurately, and that distinction is recorded rather than dropped. **The substance concedes**: §17.1.4 now reports the artifact's own **five** attached entries by name and line, notes that only `pick_up_tips` among them is executed (which corroborates the mechanism), and **`plr-sema/data/derived_contracts.json` is removed from the frontmatter's not-read list** and cited by line throughout | §17.1.4, frontmatter |
| **R2-C10** | minor | **CONCEDE** | §17.8.3's `:383` bullet read as if all 201 clearing operations were hook-free. Restated: the 148 on M-SURF alone; `transfer` 19 and `discard_tips` 34 **additionally require M3 (D8)**, because the surface-row lookup needs `m` from the argument map and both reach `_check_args` at depth ≥ 2 — 53 of the 201. §17.8.2's hook table and Q10 already had it right | §17.8.3 |
| **R2-C11** | minor | **CONCEDE (citation precision)** | §17.5.1's clause accounting is corrected: clauses 1/2 are `_find_delegate_call`'s single-site refusal, clause 4 is **three** sub-refusals, clause 6 (`depth == 1`) is **not in `compute_caller_args` at all** — its own docstring says so — and the gate lives in `derive_contract`. spec_version 2's cited range was the docstring, not the refusals. "Two relaxed, four untouched" is replaced by "clauses 1/2 and 6 relaxed, clause 4 untouched" | §17.5.1 |
| **R2-C12** | minor | **CONCEDE** | "A second pass over `_walk_closure`'s already-visited node set" is not available as stated: `seen` is generator-local and unexposed, and `InlinedGuard` is constructed inside the walk loop as a frozen dataclass. §17.5.1 gains a normative shape box: buffer `(rec, key, depth)` plus findings during the existing pass, resolve the per-delegate site sets after, emit guards in a second loop — **no `dataclasses.replace`, no mutable guard**, order preserved | §17.5.1, T54 |
| **R2-C13** | minor | **CONCEDE** | §17.8.2's hook table was headed "if declined" with D10/D11 reading "taken as recommended — no change", leaving an approving user with no row, LOC, AC or gate change. Both rows are re-headed **"if APPROVED"** and state that the increment cannot deliver either, that no row lands here, and that the approval carries into increment 9's scope; the column header names the asymmetry | §17.8.2's hook table |
| **R2-C14** | minor | **CONCEDE** | §17.16's C2 and C13 rows cite "T54" for M3, which round 1 knew as T53. A note under §17.16's table records the renumbering — **M3 moved from spec_version 1's T53 to T54; T53 is now M-SURF, which spec_version 1 did not have** — cited to round 1's own two references, and states that no row was renumbered again at spec_version 3 | §17.16 |

**What round 2 did NOT change, and it is more than round 1 left standing.** §17.1.4's *mechanism* — the
attachment filter, one guard predicate, five attached entries — which both adversaries independently
confirmed from the artifact; §17.0.1's identical-residual observation and every measured fact in the
instrument, every range of which the challenger re-verified; the 223/321 split closing to 544; D10's
refusal, which the challenger re-derived **twice over** at the pin (`kw.arg is None` and
`d_args.kwarg is not None`, both refusing `pick_up_resource`'s `backend_kwargs`); D11's repaired
argument and its **NO** recommendation; D7's two units, which the challenger checked mechanically and
found honestly argued, with **nothing in the document requiring a 27th registry row**; §17.16's
twenty-one dispositions, all honest; **both** of round 1's rebuttals (C6 and C10), each re-verified
sound by both round-2 parties; and §17.15's decision to nominate this document's own three weakest
claims, which is what made round 2's blocker findable in one pass and is retained at spec_version 3.

**The two things that moved most.** The `:375` fix went from **one** half of the surface machinery to
**two**, with 173 of its 321 operations moving behind D8 in both halves — the increment's largest
claim, still made, but now attributed correctly and falsifiable by one counter at T54 instead of by a
whole replay at T55. And §17.4.0 went from *"the route already exists"* to **seven closed
decisions**, one of which (generalise `atom_truth`, do not duplicate it) is the difference between
D7's `declared` 12 holding and T52 stopping — a decision spec_version 2 left to the implementer
without knowing it had left anything.

---

## References

- Round 1: `.praxia/docs/audits/260909_plr-sema-move-family-round1-challenger.md` and
  `.praxia/docs/audits/260909_plr-sema-move-family-round1-defender.md` — dispositioned in §17.16.
- Round 2: `.praxia/docs/audits/260909_plr-sema-move-family-round2-challenger.md` (R2-C1–R2-C14,
  verdict `not_ready`) and `.praxia/docs/audits/260909_plr-sema-move-family-round2-defender.md`
  (verdict `needs_revision`, plus its §2 ordered remediation list and its §3 converging/thrashing
  ruling) — both read in full and dispositioned in §17.17. The defender's §2 list is the authoritative
  scope of the spec_version 3 remediation, and its ruling that **no third adversarial round is
  warranted** is why §17.15 names a targeted verification pass as the next gate instead.
- Main specification (amended): `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` — the deferred
  rows, with (e) — the `move_*` family — at `:2520` and (f), precision targets, at `:2524`.
- Increment 1: `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md` — §10.2.2's typestate
  anchor, §10.2.4's effects, §10.3's evaluator (the route §17.4.0 adopts), §10.4's transfer functions,
  §10.5's graph walk, and §10.6.3's named assumption table (`:744-754`), which §17.4.3 leaves at five
  rows and which supplies **A-COMPLETES** (`:752`).
- Increment 5: `.praxia/docs/specs/260903_plr-sema-volume-increment.md` — §14.6's O5 pattern, the
  precedent §17.3's `arm_slots` argument is stated against, and R1's own risk direction, which §17.5.1
  is explicitly designed to stay out of.
- Increment 6: `.praxia/docs/specs/260904_plr-sema-predicate-increment.md` — §15.1's tiers and its
  derived-tier box (§17.8.4's refusal 1), §15.2's grammar, §15.3's local-binding idioms (which do NOT
  cover a `DictComp`, §17.5.2's second missing hop), §15.4's `E-CALL`/`E-TYPE`/`E-SCOPE`/`E-UNCOND`,
  §15.7's ordered reason procedure (unchanged here), and §15.16.3's lesson that a class which can only
  ever report 0 is a publication and not a gate.
- Increment 7: `.praxia/docs/specs/260909_plr-sema-observation-increment.md` — §16.2's observation
  record and its closed refusal list, §16.3's derived backend surface and C15 absence rule, §16.4's
  argument map and M1, §16.5's `E-ENV` rules (§16.5.1's predicate-position sentence is amended by
  §17.1.2) and §16.5.6's lane-asymmetry disclosure (`:1127-1140`), §16.9's registry arithmetic and D4's
  pattern-not-instance box, §16.10.4's anti-gaming discipline, §16.14's deferred row (e) (`:2025-2027`)
  and its D5a deferral (`:1979-1983`), §16.15's D5/D6 boxes with D-G6's one-directionality argument,
  and §16.17's round-1 disposition table (`:2205-2264`), whose shape §17.16 follows.
- The instrument: `outputs/plr-sema/unknown_ledger_260909_final.json` with its companion
  `outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json`, both read directly at every cited
  range and neither produced by this author.
- Sprint 130's plan, read for its §8 log style and its §9 outcome:
  `.praxia/docs/plans/260909_plr-sema-sprint130-observation.md:122-161`.
