---
title: "plr-sema increment 8 — the move_* family: inherited-delegate resolution, the resource-pickup typestate, and closing increment 7's own `_check_args` divergence"
description: "Eighth post-corpus increment to the plr-sema pre-corpus specification, taking increment 7 section 16.14's deferred row (e) -- the move_* family's `unresolved_delegate` gap, 93 operations, 17.1% of the frozen benchmark. The instrument is a fresh unknown_ledger run at final HEAD 52178d80, and its central measured fact is one this document did not expect and states first: the three move methods do not merely SHARE a residual, they have the IDENTICAL residual -- one 13-site set, on all 31 operations of each of move_lid, move_plate and move_resource, with zero variance and zero `n_ops_sole_blocker`. Second, the `unresolved_delegate` gap is NOT a semantic gap at all. `self._state_updated()` is an INHERITED method: it is defined on `Resource`, two lines, a loop over registered callbacks, with no raise, no assert and no precondition of any kind; the survey resolves a `self.<name>` call only against the class's OWN body, and the derive package's `resolve` only within the SAME module, so every inherited self-call in PLR becomes an `unresolved_calls` entry and then a fail-closed `unresolved_delegate` finding. Closing it costs no registry row, reuses two shipped whole-tree helpers, and removes 100% of that reason's population from the benchmark -- and it buys NO verdict on its own, which this document says in the same breath, because twelve further sites remain on every one of the 93 operations. Third, `:375` and `:383` are increment 7's own UNRECONCILED divergence: section 16.10.3 predicted `SAFE` on 544 operations and the final ledger measures 223, leaving 321 operations -- 59% of the benchmark and the largest cluster pair in the instrument -- blocked at two lines whose SAFE arithmetic increment 7 already worked out. The cause is not the arithmetic: it is that `caller_args` is computed only at `depth == 1` and only for a delegate with ONE call site, and `_check_args` is reached at depth 2 from transfer, discard_tips, stamp, move_lid and move_plate, and TWICE from move_resource. What increment 8 ships: M-INH, inherited self-call resolution across the whole PLR surface, fail-closed on any ambiguous base chain; R-ARM, a fourth `EnvRef` path shape resolving `self._resource_pickups` against a new observation field, plus the one evaluator clause that lets a COMPLETE `Seq` decide in predicate position -- which is an explicit amendment of increment 7 section 16.5.1's own sentence that no guard at this pin uses a dict as a truth value, falsified by `:2055`; the `_resource_pickup` typestate, a singleton two-state tracker with a held-resource payload, derived by shape in increment 1 P2/P4's manner and ordered WITHIN one operation by the entry point's own delegate-call linenos, fail-closed to Top at any effect site that is not unconditionally reached; M3, the constant-argument map at any depth together with a per-call-site conjunctive fold, which is what actually closes the `:375` divergence; and the residual-`**kwargs` Term -- ONE production of increment 7's refused D5a, and only one -- which gives the shipped `:383` site rule its second discharge route and is the only thing that reaches the move family, because the chatterbox backend's `pick_up_resource` and `drop_resource` take no `**backend_kwargs` at all and `has_var_keyword` is therefore False for the entire family. What increment 8 REFUSES, named and priced rather than omitted: E-TYPE's negative direction, and with it the six `drop_resource` isinstance-branch-arm sites `:2204`, `:2211`, `:2226`, `:2233`, `:2284` and `:2290`. `_eval_is_instance` cannot return F by construction, `scope_excludes` returns SAFE before a predicate is evaluated at all, and a false F in a scope entry is therefore a false SAFE with no fence between it and the verdict -- the one failure mode this project exists to prevent. It needs an exactness field on `ir.Resource` and an IR_VERSION bump; it is increment 9's, behind a decision hook recommended NO. THE GATE IS NOT A JOINED SAFE AND THIS DOCUMENT DOES NOT CLAIM ONE. move_* cannot reach `scope_verdict == SAFE` this increment and the reason is named in advance rather than discovered at a measurement: six of its thirteen sites are behind the refused mechanism. The gate is instead a structural claim over the residual set, which cannot be met by a relabelling and can genuinely fail in five stated ways: GO iff every one of the 93 move_* operations' non-excluded residual is EXACTLY those six drop_resource sites, down from thirteen, AND `unresolved_delegate` is 0 findings benchmark-wide, AND tier-1 `unsound` and `unsound_scoped` are both 0, AND increment 7's 216 `pick_up_tips` operations at `scope_verdict == SAFE` are preserved or improved. Registry arithmetic, with the one spend it proposes and never takes: `live_rows()` stays 25 against BUDGET_CAP 25 -- ZERO new rows, no cap conversation, which is the constraint this increment was written under -- and the only ask is ONE further per-row ceiling unit on HM-25, declared 10 to 11, for the singleton-typestate anchor and effect shapes. R-ARM is argued to cost NOTHING on D4's own precedent that a unit buys the pattern and not the instance count, and the `:383` extension changes no HM-26 count because it adds no fourth keyed site. REASON_VOCABULARY stays 12 of 12; `unresolved_delegate` goes to zero POPULATION and is explicitly NOT retired, because it remains the sound fallback for a genuinely unresolvable call. Five user decision hooks are surfaced with recommendations and never spent in the text: D7 (the HM-25 unit, YES), D8 (M3's lift of M1 clause 6 for call-site-constant arguments only, YES), D9 (inherited resolution, YES, and it is a decision because it can move every number in the benchmark including increment 7's 216), D10 (the residual-kwargs production, YES), D11 (E-TYPE's negative direction, NO). No new named assumption is added -- the assumption table stays at five rows -- and section 17.4 argues why the typestate needs none, which is the strongest single property this increment has."
status: draft
spec_version: 1
amends: 260901_plr-sema-pre-corpus-spec.md
task_id: 260909_sema-move-family
date: '260909'
confidence: medium
sources: "Increment 7 read in FULL as the structural model and as the text this document extends: .praxia/docs/specs/260909_plr-sema-observation-increment.md (frontmatter 1-11; preamble 13-59; §16.0 62-141; §16.1 144-453; §16.2 456-555; §16.8 1319-1350; §16.9 1353-1436; §16.10 1439-1660; §16.11 1663-1724; §16.12 1727-1910; §16.13 1913-1974; §16.14 1977-2039; §16.15 2042-2181; §16.16 2184-2202; §16.17 2205-2264; References 2267-2305). Increment 1 read as the typestate precedent §17.4 is built on: .praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md (§10.2.2 the typestate anchor 203-268, §10.2.4 P4 effects 293-334, §10.3 the evaluator 505-616, §10.4 transfer functions 617-649, §10.5 the graph walk 650-703, §10.6.3 the named assumptions 744-769, §10.8 the registry 989-1136, §10.9 explicitly-not 1137-1168). The instrument, read directly and in full at every cited range: outputs/plr-sema/unknown_ledger_260909_final.json:2-19 (the header, git_head 52178d80), :29-38 (the totals -- 544 executed, 3,903 findings, 52 clusters, the five reasons), :42-58 and :88-104 (the `:375`/`:383` clusters at 321 each), :372-382, :412-422, :452-462, :492-502, :532-542, :572-582, :612-622, :652-662, :692-702 (the NINE move-family `guard_env_dependent` clusters at 93 each -- the dispatch brief named seven; :2284 and :2290 are the two it omitted), :732-742 and :772-782 (the two `guard_predicate_unparsed` move clusters), :812-822 (the `unresolved_delegate` cluster, 186 findings over 93 operations), :2113-2137 (the scope-verdict histogram), :2172 (n_ops_unknown_but_scope_verdict_safe 216), :2174-2264 (one move_resource operation's COMPLETE finding list, 15 findings, which is the per-operation ground truth §17.0.1 is built on). outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json:79-90 (unknown_rate_by_method), :241-261 (the three per-method residual site sets -- IDENTICAL, 31 operations each, n_scope_verdict_safe 0), :263-265 (gate.go true). PLR at submodule pin dd79c4c89, every line below read THIS pass: external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:150-176 (the receiver fields), :178-185 (the `_resource_pickup` property and its setter), :187-212 (`setup` and the arm-dict rebuild), :323-329 (`_check_args`'s own signature), :541-546, :687-692, :1037-1042, :1238-1243, :1481-1483, :1559-1561, :1745-1747, :1895-1897 (eight of the ten `_check_args` call sites), :2038-2094 (`pick_up_resource` in full), :2096-2130 (`move_picked_up_resource` in full), :2132-2148 (`drop_resource`'s head), :2203-2214 (the ResourceStack arm), :2219-2233 (the Coordinate/Trash/ResourceHolder/PlateAdapter arms), :2246-2264 (the drop and the second `_state_updated`), :2272-2297 (the second isinstance chain), :2301-2377 (`move_resource` in full, including its TWO `_check_args` calls at :2345-2350 and :2364-2369), :2379-2437 (`move_lid`), :2439-2498 (`move_plate`); external/pylabrobot/pylabrobot/resources/resource.py:924-934 (`_state_updated` and its two callback registrars); external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:223-231 (`pick_up_resource`, `move_picked_up_resource`, `drop_resource` -- NONE takes `**backend_kwargs`, which is §17.1.4's load-bearing fact). Analyzer source, each citation verified against the file this pass: scripts/survey_plr_preconditions.py:112-128 (the record's `delegates_to`/`unresolved_calls` fields), :149-151 (`_is_validation_looking`), :259-300 (`visit_Call` in full -- the resolution branch at :290-299), :313-345 (`survey` and `_survey_function`), :347-354 (the per-ClassDef `method_names` set); plr-sema/src/plr_sema/derive/__init__.py:397-421 (`resolve`), :424-459 (`_walk_closure`), :630-651 (`derive_contract`'s depth-1 `caller_args` branch), :682-687 (the two gap appends); plr-sema/src/plr_sema/derive/bindings.py:914-924 (`compute_caller_call_lineno`), :931-941 (`compute_caller_args` and M1's clauses); plr-sema/src/plr_sema/derive/receiver_state.py:1241-1251 (`build_plr_class_index`), :1284-1293 (`build_plr_function_index`); plr-sema/src/plr_sema/check/predicate.py:541-566 (`subclass_closure_from_bases`), :575-594 (`_eval_is_instance` -- F structurally unreachable), :597-610 (`_is_type_ambiguous`), :783-809 (`_eval_cmp`), :817-822 (`_eval_is`), :900-945 (`evaluate_predicate`, the Kleene `And` at :910-916 and the `EnvRef` predicate-position clause at :934-944), :1011-1025 (`_scope_entry_value`), :1040-1044 (`scope_excludes`), :1121-1125 (`is_dynamic_raise`), :1200-1208 (`caller_args`'s method-name read), :1211-1231 (`_check_args_default_set`), :1234-1249 (`_check_args_surface_row`), :1252-1288 (`_eval_check_args_missing_site_rule`), :1291-1326 (`_eval_check_args_strict_site_rule`), :1333-1337 (`D6_SITE_RULES`), :1340-1352 (`_site_rule_for`), :1376-1464 (`evaluate_guard`); plr-sema/src/plr_sema/check/tipstate.py:128-190 (`TipWalk`), :372-384 (`_null_check`), :442-452 (`atom_truth`), :490-518 (`_apply_transfer`), :521-543 (`evaluate_call`); plr-sema/src/plr_sema/check/ir.py:178-191 (`Resource` and its seven fields, no name and no exactness); plr-sema/src/plr_sema/check/__init__.py:227-233 (`_unresolved_delegate`), :400-401 (the gap dispatch), :932-956 (the `excludes_sites` collector and the scoped join); plr-sema/src/plr_sema/verdict.py:140-199 (`REASON_VOCABULARY`, 12 members, `unresolved_delegate` at :152), :313-323 (`join`, unchanged); plr-sema/src/plr_sema/_hand_maintained.py:49 (`BUDGET_CAP` 25), :306-336 (`_measure_hm25`), :437-454 (`_measure_hm26`), :1000-1054 (HM-25, declared 10), :1097-1118 (HM-26, declared 3), :1152-1156 (`live_rows`). Lint, read in full so every citation and every task row here is written against the checker rather than a memory of it: plr-sema/scripts/check_spec_citations.py:1-248, plr-sema/scripts/check_spec_crossrefs.py:40-204, plr-sema/tests/test_spec_lint.py:18-53. Sprint 130's plan read for its §8 log style: .praxia/docs/plans/260909_plr-sema-sprint130-observation.md:122-161. NOT read this pass and therefore cited BY SYMBOL rather than by line: plr-sema/eval/unknown_ledger.py, plr-sema/eval/oracle_replay.py, plr-sema/eval/predicate_mutants.py, plr-sema/eval/region_oracle.py, plr-sema/eval/t30_measure.py, plr-sema/src/plr_sema/derive/predicate_ast.py, plr-sema/data/derived_contracts.json apart from the four guard records quoted in §17.1."
---

# Increment 8: the move_* family

> **This document amends `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` by reference** and
> adds §17 to that document's numbering, exactly as increment 7 adds §16. It takes the single row
> increment 7's §16.14 named as out of scope by construction — *"deferred row (e), the `move_*`
> family's `unresolved_delegate` gap … 93 operations, 17% of the benchmark, outside every mechanism
> here"* (`.praxia/docs/specs/260909_plr-sema-observation-increment.md:2025-2027`) — and it takes one
> row increment 7 did not know it was leaving: its own `:375`/`:383` prediction, which the final ledger
> falsifies on 321 operations.
>
> **What this increment ships.** Inherited self-call resolution (**M-INH**), which removes an entire
> `REASON_VOCABULARY` member's population from the benchmark and costs no registry row; a fourth
> `EnvRef` path shape (**R-ARM**) and the one evaluator clause it needs; the `_resource_pickup`
> **typestate**, derived by shape and ordered within one operation; the **constant-argument map at any
> depth** (**M3**) with a per-call-site conjunctive fold; and **one** production of increment 7's
> refused D5a — the residual-`**kwargs` Term — which is the only thing that reaches `:383` on this
> family.
>
> **THE HEADLINE IS NOT A JOINED `SAFE`, AND THIS DOCUMENT SAYS SO BEFORE ITS GATE RATHER THAN AT IT.**
> `move_*` cannot reach `scope_verdict == SAFE` in increment 8, and the obstruction is named, sized and
> site-identified in §17.1.5: six of its thirteen residual sites sit behind E-TYPE's **negative**
> direction, which `_eval_is_instance` cannot express by construction
> (`plr-sema/src/plr_sema/check/predicate.py:575-594`) and which would make a false `F` in a scope
> entry into a false `SAFE` with nothing between it and the verdict
> (`plr-sema/src/plr_sema/check/predicate.py:1040-1044`). It is refused here and priced as increment
> 9's. **The gate is therefore a structural claim over the residual set, not a verdict** — §17.8.2
> states it both ways and lists the five distinct ways it can fail.
>
> **Registry arithmetic, with the one spend it proposes and never takes.** `REASON_VOCABULARY` stays at
> **12 of 12** (§17.6). `live_rows()` stays **25** against `BUDGET_CAP = 25`
> (`plr-sema/src/plr_sema/_hand_maintained.py:49`): **zero new rows, no cap conversation.** The only ask
> is **D7** — one further per-row ceiling unit on HM-25, `declared` **10 → 11** — and §17.7 argues that
> R-ARM and the `:383` extension cost nothing at all, on increment 7's own D4 and D6 precedents rather
> than on this document's convenience.

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
> `tier_iii` (`plr-sema/src/plr_sema/check/predicate.py:1400-1401`), and the site is folded into
> `excludes_sites` (`plr-sema/src/plr_sema/check/__init__.py:932-956`). **This is why `:2092` appears
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
   possible — §17.8.2 gates on the exact set, which no other family could support.
3. **Reason coverage.** The move family is the **sole** carrier of `unresolved_delegate` in the whole
   benchmark: the cluster's `per_method` is exactly `move_lid` 31, `move_plate` 31, `move_resource` 31
   (`outputs/plr-sema/unknown_ledger_260909_final.json:812-822`). Closing it takes one of five reasons
   to zero population, and no other target can do that.
4. **Spillover.** §17.1.4's diagnosis of `:375`/`:383` is not move-specific: the same two sites block
   `aspirate` 77, `dispense` 40, `discard_tips` 34, `drop_tips` 31, `stamp` 27 and `transfer` 19
   (`outputs/plr-sema/unknown_ledger_260909_final.json:42-58`). **The move family is the cheapest place
   to find the bug and the whole benchmark is where the fix lands** — 321 operations, 59% of the
   executed population, the largest cluster pair in the instrument.

**What would have been a better target, and was checked.** A target whose residual could reach a
verdict this increment. There is none: every family's residual contains at least one site behind a
mechanism §17.12 refuses, and the move family's is the *smallest* such remainder (six sites, all in one
function, all one mechanism) rather than the largest.

### 17.0.3 The claim

**Increment 8 removes SEVEN of the move family's thirteen residual entries and leaves SIX**, and the
six are one mechanism in one PLR function. It does **not** produce a joined `SAFE` on any `move_*`
operation, and §17.1.5 names the obstruction in advance rather than discovering it at §17.8's
measurement. Whole-benchmark it takes `unresolved_delegate` from 186 findings to **0**, and `:375` and
`:383` from 321 blocked operations each to **0** — which is increment 7's own prediction, finally met,
on the 321 operations its §16.10.3 claimed and its measurement missed.

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
> disagree the measurement wins and the divergence is recorded rather than absorbed.

| entry | what it needs | from where | this increment? | resolves to |
|---|---|---|---|---|
| `_state_updated` ×2 | the inherited definition on `Resource` | §17.2's M-INH | **Y iff D9** | the gap disappears; no finding at all |
| `:2055` | the key set of `self._resource_pickups`, non-empty | §17.3's R-ARM plus the `Seq` truthiness clause | **Y** | `SAFE` on 93 |
| `:2070` | `self._resource_pickup` is empty at entry | §17.4's typestate | **Y iff D7** | `SAFE` on 93 |
| `:2120` | `self._resource_pickup` is held after `pick_up_resource` | §17.4's typestate | **Y iff D7** | `SAFE` on 93 |
| `:2147` | same | §17.4's typestate | **Y iff D7** | `SAFE` on 93 |
| `:375` | `caller_args` at depth 2 and across two call sites | §17.5's M3 | **Y iff D8** | `SAFE` on 321 |
| `:383` | the residual `**kwargs` key set is empty | §17.5's residual-kwargs Term | **Y iff D8 and D10** | `SAFE` on 321 |
| `:2204` | `isinstance(destination, ResourceStack)` decided **F** | E-TYPE's negative direction | **N** — §17.1.5 | stays ½ |
| `:2211` | the same scope entry, decided **F** | E-TYPE's negative direction | **N** — §17.1.5 | stays ½ |
| `:2226` | an earlier arm decided **T**, so this arm's `else of:` is **F** | E-TYPE plus a bound `destination` | **N** — §17.1.5 | stays ½ |
| `:2233` | the same, or `resource` declared exactly `Plate` | E-TYPE plus a bound `destination` | **N** — §17.1.5 | stays ½ |
| `:2284` | the same | E-TYPE plus a bound `destination` | **N** — §17.1.5 | stays ½ |
| `:2290` | the same | E-TYPE plus a bound `destination` | **N** — §17.1.5 | stays ½ |

### 17.1.1 `_state_updated` — the gap is a RESOLUTION failure, not a semantic one

**The whole 186-finding cluster rests on a two-line function that cannot raise.** `Resource`'s own
`_state_updated` is a loop over registered callbacks and nothing else
(`external/pylabrobot/pylabrobot/resources/resource.py:932-934`); it contains no `raise`, no `assert`,
and no call the survey would record as a precondition. `LiquidHandler` calls it twice per move
operation — once at the end of `pick_up_resource`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2094`) and once inside
`drop_resource` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2264`) — which is
exactly the multiplicity the ledger records, 186 findings over 93 operations
(`outputs/plr-sema/unknown_ledger_260909_final.json:812-822`).

**Why it is unresolvable today, in two independent halves, both read at the pin.**

1. **The survey side.** `visit_Call` sets `is_self_call` for a bare `self.<name>(...)` and then admits
   it as a delegate only when `name in self.class_method_names`; every other self-call falls to the
   `unresolved` branch (`scripts/survey_plr_preconditions.py:290-299`). The `class_method_names` set is
   built per `ClassDef` from `ast.iter_child_nodes` over **that class's own body**
   (`scripts/survey_plr_preconditions.py:347-354`), so an inherited method is structurally invisible.
   `_state_updated` is not validation-looking either — `_is_validation_looking` matches only the
   `_check`/`_assert`/`_validate` prefixes (`scripts/survey_plr_preconditions.py:149-151`) — so the
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
(`plr-sema/src/plr_sema/check/predicate.py:1449-1452`). **`self.setup_finished` never has to resolve**,
and this increment does not make it resolve.

> **Normative (an EXPLICIT amendment of increment 7 §16.5.1, in increment 7's own manner — the same
> shape its Q-MONO used on increment 6 G8(1)).** The shipped `EnvRef` clause in predicate position
> decides only for an `ir.Lit` and returns ½ for everything else, and it refuses `("self","head")` by
> **shape**, before any resolution, on the stated ground that *"a dict is not a truth value and no
> guard at this pin uses it as one"* (`plr-sema/src/plr_sema/check/predicate.py:934-944`). **The second
> half of that sentence is falsified by `:2055`**, which uses a dict as a truth value directly. The
> amendment is minimal and is stated as a rule rather than an exception:
>
> > **A complete `Seq` decides in predicate position.** An `EnvRef` whose resolution rule declares its
> > result a **complete** `Seq` — R-HEAD's own completeness claim, and now R-ARM's — evaluates `T` iff
> > that `Seq` is non-empty and `F` iff it is empty. An `EnvRef` resolving to any other value, or to a
> > `Seq` not declared complete, is ½ exactly as today.
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

`_resource_pickup` is a `@property` over `self._resource_pickups[0]` with a matching setter
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:178-185`), so an
`ast.Assign` to `self._resource_pickup` is what the AST sees at both mutation sites and the
property/setter pair is invisible to a shape test over the assignment. That is convenient and it is
also a hazard, and §17.4's absence rule is where it is paid for.

> **Normative (the ordering problem, stated because it is the ONE respect in which this typestate is
> not increment 1's).** `TipWalk` carries **one state per receiver per CALL instruction**, with guards
> evaluated against the pre-state and `_apply_transfer` applied afterwards
> (`plr-sema/src/plr_sema/check/tipstate.py:490-518`, `:521-543`). That is an **inter**-operation
> model. Here all three guards live inside **one** `move_resource` CALL, and the field's value differs
> between them: empty at `:2070`, held at `:2120` and `:2147`. **A single per-call state cannot decide
> all three**, and any implementation that assigns one state to the whole flattened guard list will
> either be wrong at `:2070` or wrong at `:2120`/`:2147`. §17.4 is the intra-operation model that
> answers this, and it is the largest single piece of new machinery in the increment.

### 17.1.4 `:375` and `:383` — increment 7's own divergence, diagnosed

> **This subsection reports a falsified prediction of the immediately preceding increment. It is stated
> as prominently as increment 7 §16.1.1 stated its own withdrawal, and for the same reason: a
> divergence absorbed silently is worse than one that never happened.**

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

**What actually blocks it is the argument map's own two fences, and both are in `compute_caller_args`'s
own docstring rather than hidden.** The rule reads `m` and `default` out of `ctx.caller_args`
(`plr-sema/src/plr_sema/check/predicate.py:1200-1208`, `:1211-1231`), and `caller_args` is populated
**only** in `derive_contract`'s `depth == 1` branch
(`plr-sema/src/plr_sema/derive/__init__.py:630-651`) and **only** for a delegate with a single
self-rooted call site — clauses 1 and 2, which refuse the whole pair
(`plr-sema/src/plr_sema/derive/bindings.py:931-941`, `:914-924`). Both fences bite here:

| entry point | how `_check_args` is reached | which fence refuses | ops |
|---|---|---|---|
| `move_resource` | twice at depth 1, `:2345` and `:2364`, plus once at depth 2 via `pick_up_resource` `:2079` | clauses 1–2, the single-call-site rule | 31 |
| `move_lid`, `move_plate` | depth 2 via `move_resource` | clause 6, the `depth == 1` restriction | 62 |
| `transfer`, `discard_tips`, `stamp` | depth 2 via `aspirate`/`dispense`, `drop_tips`, `aspirate96`/`dispense96` | clause 6 | 80 |
| `aspirate`, `dispense`, `drop_tips` | depth 1, one call site each at `:1037-1042`, `:1238-1243`, `:687-692` | neither — **T55 must diagnose these 148 and publish which** | 148 |

> **Normative (the last row is an OPEN diagnosis this document refuses to guess at, and it is a task and
> not a prose claim).** `aspirate`, `dispense` and `drop_tips` each call `_check_args` exactly once and
> at depth 1, so neither M1 fence explains them. The two candidate causes this document can name from
> source, without preferring one, are (a) §16.3's **surface selection rule** — the row
> `(backend_class, m)` is looked up in `ctx.backend_surface` and is absent whenever the pair was never
> a surface candidate, a case `_check_args_surface_row` deliberately makes indistinguishable from a
> C15 removal (`plr-sema/src/plr_sema/check/predicate.py:1234-1249`) — and (b) a `default=` expression
> that does not parse as a `SetLit` (`plr-sema/src/plr_sema/check/predicate.py:1211-1231`), which the
> pin's own call sites make unlikely but which only measurement settles. **T55 publishes the decline
> reason per operation, and §17.8.3's `:375` cell is stated as 321 only if that diagnosis is closed;
> otherwise it is stated as 173 and the residual is published.** A cell this document cannot derive is
> not written as if it could.

**`:383` is a separate and harder case, and the reason is a fact about the chatterbox backend.** The
shipped `_eval_check_args_strict_site_rule` has exactly one discharge route: `F` iff the surface row's
`has_var_keyword` is `True` (`plr-sema/src/plr_sema/check/predicate.py:1291-1326`). The chatterbox
`pick_up_resource`, `move_picked_up_resource` and `drop_resource` take **no** `**backend_kwargs` at all
(`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:223-231`), so
`has_var_keyword` is `False` for every backend method the move family reaches and **the rule declines
for the whole family however the argument map is fixed.** §17.5's residual-kwargs Term is the second
route, and it is the only one.

> **Normative (a route considered and REFUSED, recorded so the round does not have to find it).**
> `move_resource` passes `strictness=Strictness.IGNORE` literally
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2345-2350`), and an enum-constant
> `Term` plus an equality rule would make `:383`'s own predicate `F` at those two sites without any
> scope reasoning. **It does not close the site**, because the same closure also reaches `_check_args`
> from `pick_up_resource`, which passes `get_strictness()`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2079-2081`) — a non-`self`-rooted
> call that is not a `Term` under G1. §17.5's fold is conjunctive over admitted call sites and would
> therefore decline, correctly. **One production, bought for nothing, is exactly the trade §9.4
> forbids**, and the enum-constant `Term` is refused by name in §17.12.

### 17.1.5 The six `drop_resource` sites — refused, and the refusal is about soundness, not cost

All six sit inside the `isinstance(destination, ...)` chains of `drop_resource`: `:2204` and `:2211` in
the `ResourceStack` arm (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2203-2214`),
`:2226` in the `ResourceHolder` arm and `:2233` in the `PlateAdapter` arm
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2219-2233`), and `:2284`/`:2290` in
the second chain's `ResourceStack` and `PlateAdapter` arms
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2272-2297`).

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

> **Normative (why this is REFUSED here rather than merely deferred, and the argument is the project's
> own).** Supplying the missing exactness fact means a new field on the `Resource` wire node and an
> `IR_VERSION` bump, which re-keys every cached entry — and, far more seriously, it puts a **derived
> `F`** into a scope entry. Every other mechanism in increments 6, 7 and 8 that can produce a `SAFE`
> does so through a guard's own `fires is False` return, where a wrong answer is at least visible as a
> guard the analyzer claims not to fire. A wrong `F` in a **scope** entry is different in kind: it
> excises the guard before evaluation, produces `_SAFE` with no predicate reasoning recorded, and does
> so for **every** guard in every later arm at once. **A single wrong exactness claim would silently
> convert six sites on 93 operations to `SAFE`.** That is a false `SAFE`, which is the one failure mode
> the whole project exists to prevent, and it is not a risk to take in the same increment as four other
> new mechanisms. **It is D11 (§17.13), recommended NO**, with the precondition T55 must publish before
> increment 9 can argue it: the per-operation declared type of the `destination` and `resource`
> operands, which no number anywhere currently covers.

> **Normative (a partial route that exists and is ALSO not taken, recorded so the round can weigh it).**
> `:2233` and `:2290` read `not isinstance(resource, Plate)`, and `resource` is `drop_resource`'s own
> local, assigned `self._resource_pickup.resource`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2146-2148`) — a plain `ast.Assign`
> of an attribute chain, which no binding idiom substitutes, so it is ⊤ today. §17.4's typestate
> carries the held resource as an `ir.Ref` and **could** bind it, after which E-TYPE's **positive**
> direction would decide `isinstance(resource, Plate)` `T` for `move_plate` and the two guards would be
> `SAFE` on 31 operations. **It is not gated and not claimed**, for two reasons: it is `T` only when the
> corpus declares those resources exactly `Plate`, which §17.8.3 cannot derive; and it would break the
> gate's uniformity — 31 of 93, on two of six sites — for no operation gained, since four sites remain
> regardless. **T55 publishes it as a measured extra and §17.8.2 does not gate on it.**

---

## 17.2 M-INH — inherited self-call resolution

> **Normative (the rule, in two halves that must land together).**
>
> **Half 1, the survey.** The per-`ClassDef` method-name set
> (`scripts/survey_plr_preconditions.py:347-354`) is extended with the method names of every class in
> that class's **transitive base closure**, computed over a whole-tree class index. A `self.<name>()`
> call whose `name` is in the extended set is a **delegate**, not an unresolved call
> (`scripts/survey_plr_preconditions.py:290-299`). The record gains one additive field,
> `inherited_delegates`, listing the names admitted only by inheritance, so the selection is
> inspectable and its count publishable.
>
> **Half 2, the derive package.** `resolve` gains a **third** step, tried only after its two existing
> same-module steps fail and never before them, so the class-first-then-module precedence its docstring
> declares normative is untouched (`plr-sema/src/plr_sema/derive/__init__.py:397-421`): walk
> `rec.class_name`'s transitive bases and return `(module_of(B), f"{B}.{name}")` for the **unique** base
> `B` that defines it.
>
> **The base closure and the module map are DERIVED and already shipped.** `build_plr_class_index`
> returns `(class_nodes, class_modules)` — every top-level class across the whole PLR tree, plus the
> module each lives in (`plr-sema/src/plr_sema/derive/receiver_state.py:1241-1251`), the same whole-tree
> pass `build_plr_function_index` sits beside
> (`plr-sema/src/plr_sema/derive/receiver_state.py:1284-1293`) — and
> `subclass_closure_from_bases` is the generic, PLR-free reflexive-transitive closure already shipped
> for E-TYPE (`plr-sema/src/plr_sema/check/predicate.py:541-566`). **No base-class name is typed
> anywhere**, which is §16.3's D3 argument reused rather than re-derived.

> **Normative (three fail-closed conditions, and each closes a distinct way this could be WRONG).**
>
> 1. **Ambiguity refuses.** If more than one class in the base closure defines `name`, `resolve`
>    returns `None` and the gap stands. AST bases are not a Python MRO linearisation, and inlining the
>    wrong body's guards is the only way this mechanism could produce a **false** answer rather than
>    merely a different one. `LiquidHandler` has more than one base, so this is a live condition and
>    not a hypothetical.
> 2. **A base outside the analyzed surface refuses.** If the unique defining class is not in the index,
>    the gap stands — today's behaviour exactly.
> 3. **The closure is bounded and the bound is published.** Newly resolved delegates transitively pull
>    in their own delegates through `_walk_closure`
>    (`plr-sema/src/plr_sema/derive/__init__.py:424-459`). T50 publishes the per-entry-point closure
>    size and guard count before and after, and **stops and surfaces to the user rather than landing**
>    if any entry point's closure more than doubles.

> **Normative (the direction of the change, said plainly because it cuts both ways).** Resolving a
> previously-unresolved call **adds** that function's guards to the closure. On `_state_updated` that
> is zero guards and 186 findings disappear. Elsewhere on the surface it may be more than zero, in
> which case the benchmark gains `UNKNOWN` findings — the **sound** direction, and an honest one, but a
> direction that can cost decided findings and, in principle, increment 7's 216. **That risk is why
> M-INH is a user decision (D9) and why §17.8.2's gate makes the 216 a hard condition rather than a
> hope.**

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
>   already fixes, and it is `sorted(self._resource_pickups)` — a claim about what the dict *contains*
>   at one instant, never about how `setup` builds it
>   (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:212`). This is verbatim
>   `head_channels`' own argument, which §16.2.2 already calls the field to attack and already answers.
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

> **Normative (R-ARM, and the amended clause it needs).** `EnvRef(("self","_resource_pickups"), None)`
> resolves to the `Seq` of `arm_slots`, declared **complete** in exactly R-HEAD's sense. In predicate
> position it decides by §17.1.2's amended clause: `T` iff non-empty, `F` iff empty, ½ when the
> observation is absent, when the record is partial, or when the path is any other shape
> (`plr-sema/src/plr_sema/check/predicate.py:934-944`). In **term** position it behaves exactly as
> R-HEAD's `Seq` does and gains no membership case: no guard at this pin tests membership in it, and
> admitting one that nothing reads is the growth §16.2.1's closed list exists to prevent.

---

## 17.4 The `_resource_pickup` typestate

> **This section's every design choice is stated against increment 1's own, which is the only typestate
> in the analyzer.** Increment 1's four derived passes, its atom truth table
> (`plr-sema/src/plr_sema/check/tipstate.py:442-452`), its transfer function
> (`plr-sema/src/plr_sema/check/tipstate.py:490-518`) and its named assumptions
> (`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:744-754`) are the template; the one
> place this increment departs from it is §17.1.3's ordering problem, and the departure is argued
> rather than assumed.

### 17.4.1 The lattice and the payload

Two states and a top: **`EMPTY`** (the field is `None`), **`HELD`** (it is not), **`TOP`**. The join is
`TOP` on any disagreement, exactly `join_tip`'s shape. `HELD` additionally carries an optional
**payload**: the `ir.Value` the pickup was constructed from, when the setting assignment's own argument
resolves to one, and `None` otherwise. **The payload never affects the three guards' truth** — it exists
only so §17.1.5's refused-partial route has somewhere to live in increment 9, and a `None` payload is
always legal.

### 17.4.2 P5 — the singleton typestate anchor, derived by shape

> **Normative.** A receiver attribute `F` on the analyzed class is a **singleton typestate anchor** iff,
> over that class's own body: (a) at least one `ast.Assign` targets `self.<F>` with an `ast.Constant`
> `None` value; (b) at least one `ast.Assign` targets `self.<F>` with a non-`None` value; and (c) at
> least one guard in the derived contract table reads `self.<F>` through an `Is` node — the same
> `x is None` / `x is not None` shape `_null_check` already matches for the tip family
> (`plr-sema/src/plr_sema/check/tipstate.py:372-384`). **No attribute name is typed**, and the selection
> is published whole-surface with its count.

> **Normative (the absence rule, inherited from §16.3's C15 and extended for the hazard §17.1.3
> names).** An anchor candidate is **absent** — the whole mechanism declines for it — when: `F` is also
> defined as a `property` **whose setter body is not a single assignment to another attribute**; when
> `F` is assigned anywhere outside the analyzed class's own body; or when the qualname is defined at
> more than one lineno. At the pin `_resource_pickup` **is** a property, and it survives precisely
> because its setter is the single statement `self._resource_pickups[0] = value`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:178-185`) — which is a fact about
> PLR that the rule checks rather than assumes. **AC-17.3 asserts the rule biting on a synthetic
> property whose setter does more.**

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
> `pick_up_resource`'s own setting assignment at `:2072`, so it reads `EMPTY`; `:2120` and `:2147` sit
> in delegates called after `pick_up_resource` returns
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2353-2377`), so they read `HELD`.

> **Normative (four fail-closed conditions, and every one of them is a way a source-order walk could be
> WRONG).**
>
> 1. **A conditionally-reached effect site widens.** If a call statement carrying an effect does not
>    satisfy `guard_is_unconditional`'s own ways (1)–(3) on its `scope_trail`
>    (`plr-sema/src/plr_sema/check/predicate.py:1047-1057`), the state becomes `TOP` from that position
>    onward. This is what makes `move_picked_up_resource`'s in-loop call site
>    (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2361-2362`) safe: the loop
>    carries **no** effect, so nothing widens, and had it carried one it would have.
> 2. **A rollback path widens.** An assignment to `self.<F>` lexically inside an `ast.Try` handler —
>    `pick_up_resource`'s own `except` at
>    `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2090-2092` — is **not** folded
>    into the ordered state; instead the state becomes `TOP` at every position after the enclosing
>    `try`. On the pin this costs nothing, because both `:2120` and `:2147` are reached only when
>    `pick_up_resource` returned normally, and the analyzer cannot know that; taking the loss is the
>    point.
> 3. **An unresolved delegate widens.** A call the closure could not resolve may mutate `F`
>    invisibly. Note the interaction with §17.2, and it runs the **right** way: M-INH resolves calls
>    that today are gaps, so it strictly reduces the population that widens here.
> 4. **The initial state is `TOP` unless the graph supplies it.** Across operations the state is carried
>    by the graph walk in `TipWalk`'s own manner (`plr-sema/src/plr_sema/check/tipstate.py:128-190`),
>    resetting to `EMPTY` only where increment 1's own **A-COMPLETES** already licenses it
>    (`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:744-754`) and widening on any
>    receiver whose prior operations are not all decided.

> **Normative (NO new named assumption is added, and this is the strongest property this increment
> has).** The assumption table stays at **five** rows. Every claim §17.4 makes is either derived (P5's
> and P6's shapes, the source-order walk, the four widening conditions) or already licensed by an
> existing assumption: **A-SINGLE** for one receiver variable denoting one instance, **A-COMPLETES** for
> the inter-operation initial state
> (`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:744-754`). **The cheapest
> falsification of that claim** is a fixture in which the state at a guard depends on a fact no listed
> assumption supplies; AC-17.3 requires the round to try to build one, and if it succeeds the
> assumption must be named before the row lands.

---

## 17.5 M3 — the constant-argument map at any depth, and the residual-`**kwargs` Term

### 17.5.1 M3

> **Normative.** `compute_caller_args` today refuses a `(K, D)` pair outright on two grounds this
> increment relaxes, and on four it does not touch
> (`plr-sema/src/plr_sema/derive/bindings.py:931-941`).
>
> **(a) The single-call-site refusal becomes a per-site LIST.** `caller_args` becomes, additively, a
> list of per-call-site maps — one entry per `self.<D.name>(...)` statement in `K`, each carrying its
> own `lineno` alongside its parameter map. A wire consumer seeing the old single-map shape, or `None`,
> behaves exactly as today. A **site rule** reading the list evaluates **once per entry** and folds
> **conjunctively**: `F` iff every entry yields `F`, ½ if any entry declines. This is the only sound
> fold — the guard genuinely executes once per call site, so `SAFE` requires `SAFE` at all of them —
> and it is what decides `:375` for `move_resource`, whose two sites disagree on `m` and `default` but
> agree on `params ⊆ default`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2345-2350`, `:2364-2369`).
>
> **(b) The `depth == 1` restriction is lifted for CALL-SITE-CONSTANT arguments only.** A `(K, D)` pair
> at any depth `d ≥ 1` binds a parameter iff the argument at the call site parses as a `Term` whose
> free names are **empty** — a constant, a `SetLit` of constants, or a `self`-rooted `EnvRef`. Every
> other argument binds nothing at `d ≥ 2`, exactly as today.
>
> **Why the lift is NARROWER than the depth-1 map D1 already permitted, and not wider.** M1's clause 6
> exists because resolving a caller-side **name** requires the caller's namespace, and only the entry
> point's namespace is available (`plr-sema/src/plr_sema/derive/__init__.py:630-651`). A call-site
> constant is resolved against **no namespace at all**: it is a literal in the delegate's caller's own
> source text, and the chain of intermediate frames it passes through cannot change it. **The
> restriction genuinely does not apply**, and this document states that as the whole of the argument
> rather than appealing to measurement.
>
> **The pin makes this exact.** All ten `_check_args` call sites pass, for `method`, a `self`-rooted
> `EnvRef`; for `default`, a `SetLit` of string constants; for `strictness`, either a module-level
> `Attr` or a bare call — neither a `Term`, so neither binds, at any depth
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:541-546`, `:687-692`,
> `:1037-1042`, `:1238-1243`, `:1481-1483`, `:1559-1561`, `:1745-1747`, `:1895-1897`, `:2079-2081`,
> `:2345-2350`). **`backend_kwargs` is the entry point's own name and is deliberately NOT bound by
> M3** — §17.5.2 is what reads it, and by a different route.
>
> **What M3 does NOT touch.** `caller_reachability_clear` and `caller_scope_trail` stay strictly
> `depth == 1`, and so does D1's `WILL_FAIL` lift. **M3 binds names; it licenses no new `WILL_FAIL`
> anywhere.** That separation is what keeps this increment out of increment 5 §14.6 R1's risk
> direction entirely.

### 17.5.2 The residual-`**kwargs` Term, and `:383`'s second route

> **Normative (ONE production of D5a, and only one).** Increment 7 §16.1.1 priced D5a as five
> productions and made it increment 8's. This increment takes **production (5) alone** — a
> representation of the residual `**kwargs` key set — and refuses the other four by name in §17.12.
>
> **The Term.** Inside a contract whose entry point declares a `**kwargs` parameter `W`, `Var(W)`
> resolves to the **complete** `Seq` of `call.kwargs` keys that are **not** declared parameters of the
> entry point. Both halves are already on hand: the operation's own keyword set is `ir.Call.kwargs`, and
> the entry point's declared parameters come from its `ast.arguments` through the same function index
> `build_plr_function_index` supplies (`plr-sema/src/plr_sema/derive/receiver_state.py:1284-1293`). It
> is **complete** in R-HEAD's sense — an operation's keyword set is total in the IR, not a lower bound —
> and that completeness is what lets it decide an emptiness test.
>
> **`:383`'s second discharge route.** The shipped rule returns `F` iff `has_var_keyword` is `True`
> (`plr-sema/src/plr_sema/check/predicate.py:1291-1326`). It gains a second, disjunctive route: `F`
> **also** when the call site's `backend_kwargs` argument resolves to an **empty** complete `Seq`. The
> arithmetic is `:375`'s own, one term over: the recorded scope entry is
> `if len(extra) > 0 and len(vars_keyword) == 0`, `extra` is `backend_kws - args`, and an empty minuend
> makes `extra` empty whatever `args` is — so `len(extra) > 0` is `F`, the `And` is `F`, and E-SCOPE's
> conclusion holds regardless of `vars_keyword`, of `strictness`, and of the backend method's
> signature.
>
> **One further hop is needed and it is bounded.** `move_resource` passes its own `backend_kwargs`
> directly at both of its call sites, but `pick_up_resource` receives `**pickup_kwargs`, a dict
> comprehension over `backend_kwargs`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2345-2351`). The rule needed is
> one line of reasoning and is stated as a rule, not a special case: **a dict or set comprehension whose
> single `iter` resolves to an empty complete `Seq` resolves to an empty complete `Seq`**, whatever its
> filter. Nothing else about comprehensions is admitted.
>
> **It is one-directional by construction**, on D-G6's own argument: both `_check_args` guards carry
> `reachability_clear` false, and `evaluate_guard` returns `_SAFE` on `fires is False` unguarded by
> depth (`plr-sema/src/plr_sema/check/predicate.py:1449-1452`). This route can add `SAFE` and can never
> emit a `WILL_FAIL`, false or otherwise.

> **Normative (the registry consequence, and it is ZERO).** `_measure_hm26` counts
> `len(D6_SITE_RULES)` (`plr-sema/src/plr_sema/_hand_maintained.py:437-454`), and the dict's three
> keyed `(qualname, lineno)` pairs are unchanged
> (`plr-sema/src/plr_sema/check/predicate.py:1333-1337`). Broadening one existing rule's condition adds
> no fourth site and moves no count. **HM-26 stays at `declared` 3.** The Term itself is a grammar
> production of exactly the class §16.9 books on HM-25, and §17.7 argues it onto D7's unit rather than
> asking twice.

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
> | the typestate is `TOP` at a guard's position | `guard_env_dependent` | the guard reads instance state the analyzer did not establish; the tip family's own `channel_state_unknown` is **per-channel** and this anchor has no channels |
> | a per-call-site fold in which one site declines | `guard_env_dependent` | unchanged from the single-site decline it generalises |
> | the residual-`**kwargs` `Seq` does not resolve | `guard_env_dependent` | same clause |
> | an inherited call whose base chain is ambiguous | `unresolved_delegate` | **unchanged** — this is the member's existing meaning and the reason it is not retired |

> **Normative (`unresolved_delegate` goes to ZERO POPULATION and is explicitly NOT retired).** After
> §17.2 no operation on this benchmark carries the reason, and a retirement would look like tidiness.
> It is refused: the member is the sound fallback for a call that genuinely cannot be resolved, §17.2's
> three fail-closed conditions each produce exactly that case, and a benchmark on which a fallback never
> fires is not evidence the fallback is dead. **T55 publishes `unresolved_delegate == 0` as a
> measurement and AC-17.6 asserts the member is still present in the vocabulary.**

---

## 17.7 Registry

**New rows: ZERO, in every branch of every decision hook. `live_rows()` stays 25
(`plr-sema/src/plr_sema/_hand_maintained.py:1152-1156`) against `BUDGET_CAP = 25`
(`plr-sema/src/plr_sema/_hand_maintained.py:49`); headroom 0, unchanged; no cap conversation.** That
constraint shaped the increment rather than being satisfied after the fact, and §17.12 records the two
mechanisms it excluded for costing a row.

> **Normative (the ONE proposed spend, and it is the user's: HM-25 `declared` 10 → 11 — `D7`).**
> §17.4's P5 anchor shape and P6 effect shape are hand-written **syntactic patterns over how PLR is
> written** — an assignment-pair shape plus an `Is`-read requirement, in exactly the sense HM-25's own
> `why_not_derived` uses, and in exactly increment 1 P2's class, which is already the row's first
> entry (`plr-sema/src/plr_sema/_hand_maintained.py:1000-1054`). One further collective unit for the
> **pattern** — *"a singleton typestate anchor and its assignment effects"* — not one per shape.
> `_measure_hm25` measures the row by importing the symbols that implement its patterns
> (`plr-sema/src/plr_sema/_hand_maintained.py:306-336`), so **T52 must additionally import the
> anchor/effect symbol**, and the same contingency increment 6 and increment 7 both wrote applies
> verbatim: **if the measured count would exceed 11, T52 STOPS and surfaces a further spend to the user
> rather than raising `declared` on its own authority.**

> **Normative (three things that cost NOTHING, each argued rather than asserted, and each stated so a
> reviewer can break it).**
>
> 1. **R-ARM and its truthiness clause cost nothing**, on **D4's own precedent**. §16.9's D4 box states
>    that the unit buys *"an `EnvRef` path admitted against the observation record"* as a **pattern**,
>    explicitly *"not one per instance"*, and uses that same argument to refuse reducing the ask when
>    R-DECK was withdrawn. R-ARM is a fourth instance of that identical pattern. Charging for it would
>    be inconsistent with the argument that was already accepted, in the direction that flatters this
>    document — which is the mirror image of the gaming §9.4 forbids. **The strongest objection is that
>    the amended predicate-position clause is a new *evaluator rule* rather than a new path shape; the
>    reply is that R-HEAD's own predicate-position behaviour was already specified in §16.5.1 as part of
>    the same unit, and this amends that specification rather than adding a second.**
> 2. **M-INH costs nothing.** A transitive base closure over PLR's own recorded class bases, keyed on
>    two shipped whole-tree indices, introducing no literal. Same class as `is_dynamic_raise`,
>    `reachability_clear` and §16.3's derived backend surface.
> 3. **M3 costs nothing.** A shape test over `ast.Call` and `ast.arguments`, fail-closed on every
>    unrecognised shape, adopting the restrictions M1 already states rather than inventing any — which
>    is verbatim §16.9's own item (2) for the depth-1 map, an argument round 1 examined and did not
>    reject.
>
> **The residual-`**kwargs` Term is the borderline case and is disclosed as one.** It is a grammar
> production, and §16.9 booked `EnvRef`, `Zip` and the membership comparators onto HM-25 as exactly
> that. This document's position is that it rides **D7's** unit rather than asking for a second, on the
> ground that it is a *resolution* of an existing `Var` against already-modelled data and adds no node
> to the grammar. **If the round rejects that, the disposition is a second unit on the same row and D7
> becomes 10 → 12; it is not a new row either way**, and it is not a cap conversation in either case.

---

## 17.8 Measured sets and the gate

### 17.8.1 What T55 publishes

> **Normative.** The measured report publishes, over the frozen benchmark and the regenerated contract
> table:
>
> 1. **M-INH's complete measured selection**: every `(class, name)` pair newly resolved by
>    inheritance, its unique defining base, and — separately — the count **refused** by each of §17.2's
>    three fail-closed conditions. Plus, per entry point, the closure size and guard count **before and
>    after**, so §17.2's doubling bound is checkable rather than asserted.
> 2. **`n_resolved_by_rule` and `n_declined_by_rule` for R-ARM**, per lane (tier 1, tier 2b),
>    alongside the existing R-HEAD/R-ATTR/R-CONST block, and `n_seq_truthiness_decided` for
>    §17.1.2's amended clause — the one evaluator rule this increment adds, which must have a counter
>    of its own rather than hiding inside R-ARM's.
> 3. **The typestate's complete measured selection**: every anchor candidate, every one removed by
>    §17.4.2's absence rule with which clause removed it, the per-guard state assignment for all three
>    move sites, and `n_typestate_widened` broken down by which of §17.4.3's four conditions widened it.
> 4. **M3's measured selection**: every `(K, D)` pair now admitted at `depth ≥ 2`, every multi-site
>    delegate now admitted as a list with its per-site linenos, the conjunctive fold's outcome per site
>    rule, and the count still refused by each surviving M1 clause.
> 5. **`n_check_args_decided`**, split by which discharge route decided it — `has_var_keyword`, the new
>    residual-kwargs route, or neither — per site and per method. **This is the block that closes
>    §17.1.4's open diagnosis**, and it must name the decline reason per operation for the 148
>    `aspirate`/`dispense`/`drop_tips` operations this document could not explain.
> 6. **Per executed operation**: `verdict`, `scope_verdict`, the residual reason set, and the list of
>    non-excluded sites carrying an `UNKNOWN`. **The gate is computable from this block alone, without
>    reading this document.**
> 7. **The fence**: `unsound` and `unsound_scoped`, both unmodified in definition, with
>    `rows_excused_by_scope` and `rows_excused_by_frame` and every excused row's captured frame list.
> 8. **The after-ledger delta** against `outputs/plr-sema/unknown_ledger_260909_final.json`, on
>    `n_findings_by_reason`, `n_clusters`, `per_op_reason_set_histogram` and the per-method
>    `residual_site_sets`, with `consistency.ok` true.
> 9. **§17.1.5's precondition for increment 9**: the per-operation declared `type`/`element_type` of the
>    `destination` and `resource` operands of every `move_*` operation, published so D11 can be argued
>    from data next increment instead of from prose.

### 17.8.2 The gate

> **Normative (the GO condition, stated over structure because this increment cannot reach a verdict
> and says so in advance).**
>
> > **GO iff ALL FIVE hold.** (1) On **every one** of the 93 `move_*` operations, the non-excluded
> > residual site set is **exactly** `{:2204, :2211, :2226, :2233, :2284, :2290}` — six entries, down
> > from thirteen. (2) `unresolved_delegate` is **0 findings** benchmark-wide. (3) Tier-1 `unsound` is
> > **0** under the unmodified predicate **and** `unsound_scoped` is **0** under §16.7's narrowing.
> > (4) `pick_up_tips` reaches `scope_verdict == SAFE` on **≥ 216** operations — increment 7's headline
> > preserved or improved. (5) `guard_predicate_unparsed` is **unchanged at 495** and
> > `guard_operand_unknown` **unchanged at 144**.
>
> **NO-GO otherwise**: publish every count and the structural reason in §17.14, keep whatever landed
> (each mechanism is a strict information gain on the contract table and on the ledger either way), and
> bring the decision to the user.

> **Normative (the five distinct ways this gate can fail, named so it is not a coin already called).**
>
> 1. **The residual is larger than six** — some mechanism does not reach some operation, which
>    falsifies §17.1's site analysis.
> 2. **The residual is SMALLER than six, or contains a site not on the list** — equally a failure, and
>    the more interesting one: it means a mechanism decided something this document did not predict,
>    and an undiagnosed `SAFE` is exactly what §17.1.5 refuses to ship.
> 3. **M-INH regresses the benchmark** — condition (4) or (5) breaks because newly resolved base
>    methods carry guards this document did not anticipate. §17.2's own box says this is possible.
> 4. **Either fence counter moves off zero** — the one outcome that stops the increment outright.
> 5. **The `:375` diagnosis is wrong** — §17.1.4's open row resolves to neither named cause, and the
>    148 stay blocked.

> **Normative (which decision hooks each condition needs, so a partial decline is predictable rather
> than discovered mid-sprint).**
>
> | if declined | condition (1) becomes | other conditions |
> |---|---|---|
> | **D7** | eight sites, adding `:2070`, `:2120`, `:2147` | unaffected |
> | **D8** | seven sites, adding `:375`; `:383` is unreachable regardless | unaffected |
> | **D9** | seven entries, adding `_state_updated`; condition (2) is **unreachable** | (4) and (5) become strictly easier |
> | **D10** | seven sites, adding `:383` | unaffected |
> | **D11** | *taken as recommended* — no change; D11 is **NO** in this document's own text | — |
>
> **With D7, D8, D9 and D10 all declined the gate is unwinnable by construction**, and the increment
> reduces to §17.8.1's measured blocks, which are still worth publishing and are still the input
> increment 9 needs. **The user is owed that choice before the work starts and not at a gate**, which
> is the discipline increment 7 §16.15 Q5 established and this document inherits.

### 17.8.3 The prediction, per entry

> **Normative (this table is a PREDICTION for T55 to falsify, cell by cell; a divergence in either
> direction is recorded in §17.14 rather than absorbed.)** Counts are the ledger's frozen population.

**The move family — 93 operations, one uniform residual:**

| entry | today | all hooks taken | by what |
|---|---|---|---|
| `_state_updated` ×2 | 186 findings | **0** | §17.2's M-INH; `Resource._state_updated` contributes no guard |
| `:2055` | ½ on 93 | **`SAFE` on 93** | R-ARM plus §17.1.2's truthiness clause; the Kleene `And` needs only the second conjunct |
| `:2070` | ½ on 93 | **`SAFE` on 93** | the typestate at position; `EMPTY` before `:2072` |
| `:2120` | ½ on 93 | **`SAFE` on 93** | the typestate; `HELD` after `pick_up_resource` returns |
| `:2147` | ½ on 93 | **`SAFE` on 93** | the typestate; `HELD` |
| `:375` | ½ on 93 | **`SAFE` on 93** | M3's depth lift plus the per-site conjunctive fold |
| `:383` | ½ on 93 | **`SAFE` on 93** | the residual-kwargs route; `has_var_keyword` is False here and cannot help |
| `:2204` `:2211` `:2226` `:2233` `:2284` `:2290` | ½ on 93 | **unchanged, ½ on 93** | E-TYPE's negative direction, refused (§17.1.5, D11) |
| **`scope_verdict`** | `UNKNOWN` on 93 | **`UNKNOWN` on 93** | six sites remain; **this document claims no verdict here** |

**Whole benchmark, split into a CERTAIN half and a DIAGNOSIS-DEPENDENT half, because §17.1.4's open row
is exactly the number this document declines to claim:**

- **`:375`.** Certain: **173** operations — 93 `move_*` plus 80 `transfer`/`discard_tips`/`stamp`, all
  of which M3's depth lift and per-site fold reach by the argument above. Diagnosis-dependent: the
  further **148** `aspirate`/`dispense`/`drop_tips`, which need §17.1.4's open cause found and fixed.
  **Target 321; the gate reads only the 93.**
- **`:383`.** Identical split, identical numbers, for the identical reason.
- **`n_findings_decided`.** Today **2,817**. Certain: **+186** (`_state_updated`) **+372** (four sites ×
  93) **+346** (`:375` and `:383` on 173) = **3,721**. Target with the diagnosis closed: **4,017**.
  **Published, not gated** — increment 7 C4's lesson is that gating on the uncertain half makes a
  prediction-holding run fail its own criterion.
- **`guard_env_dependent`.** 2,884 → certain **≈ 2,140**, target **≈ 1,844**.
- **`unresolved_delegate`.** 186 → **0**, whole population. This one **is** gated.
- **`n_clusters`.** 52 → **51** in the certain half: the `unresolved_delegate` cluster disappears and
  the four `:2055`/`:2070`/`:2120`/`:2147` clusters disappear with it — call it **47** — while `:375`
  and `:383` survive as partially-cleared clusters until the diagnosis closes, at which point they go
  too, for **45**. A partially cleared site is still a cluster, which is the correction increment 7 C4
  made to its own arithmetic and this document adopts rather than rediscovering.
- **`guard_predicate_unparsed` 495 → 495** and **`guard_operand_unknown` 144 → 144**, unchanged in
  every branch. This increment adds no grammar production that any guard's own predicate reaches, and a
  movement in either means something unintended happened. **Both are gate conditions**, and they are
  the two cheapest falsifications of this document's own claims about its blast radius.
- **`unknown_rate` 1.0 → 1.0**, and `scope_verdict == SAFE` on **216** operations, all `pick_up_tips`,
  unchanged. **No new method reaches a joined `SAFE`**, and §17.8.4 is where that is defended.

### 17.8.4 The anti-gaming counter

> **Normative (which mechanism flips which site — the falsification map). The gate is stated over a set
> this increment shrinks, so the burden is on this box.**
>
> | mechanism | flips | does NOT flip | published counter |
> |---|---|---|---|
> | M-INH alone (§17.2) | the `<none>` gap only | every guard site in the benchmark | the newly-resolved pair list, and the refusal counts |
> | R-ARM plus the truthiness clause | `:2055` only | every guard reading any other path | `n_resolved_by_rule` for R-ARM, and `n_seq_truthiness_decided` |
> | the typestate (§17.4) | `:2070`, `:2120`, `:2147` only | every guard not reading a singleton anchor | the per-guard state assignment, plus `n_typestate_widened` |
> | M3 alone (§17.5.1) | nothing by itself | — it binds names; it decides no guard and licenses no `WILL_FAIL` | the newly-admitted pair list |
> | the residual-kwargs Term | `:383` only, and only through the existing site rule | every other guard in every other PLR function | `n_check_args_decided` split by route |
>
> **The three cheap ways to pass this gate, all named and all REFUSED.**
>
> 1. **Put the six `drop_resource` sites into `excludes_sites`.** Refused. `excludes_sites` is
>    **derived**, from `guard.is_dynamic_raise` and from nothing else
>    (`plr-sema/src/plr_sema/check/predicate.py:1121-1125`); admitting a site list is the configuration
>    increment 6 §15.1's derived-tier box exists to prevent, and increment 7 §16.10.4 refused the
>    identical move for `:375`/`:383` when it would have bought a headline. **This is the move that
>    would make the gate's condition (1) trivially true, and the reason it is refused is not cost.**
> 2. **Retire `unresolved_delegate` instead of emptying it.** Refused by §17.6's own box. Condition (2)
>    would then be satisfied by a deletion.
> 3. **Widen the typestate to `TOP` whenever it would be wrong.** A `TOP` state emits
>    `guard_env_dependent`, so this cannot manufacture a `SAFE` — but it *can* make §17.4's measured
>    selection look healthier than it is. **`n_typestate_widened`, broken down by condition, is what a
>    reader inspects**, and AC-17.3 asserts the three move guards decide by state and **not** by
>    widening.
>
> **The cheapest falsification of this document as a whole**: any `move_*` operation whose residual is
> not exactly the predicted six. That single number falsifies §17.1's site analysis in either
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
> builds every fixture on the chatterbox backend and **can observe**, so **R-ARM** and the residual-kwargs
> route can both move it, and so can the typestate on any fixture whose program picks a resource up.
> M-INH can move it on any fixture whose closure contains an inherited self-call, which is most of them.
> **Every movement must be attributed to a named mechanism, using §17.8.1's per-lane counters, before
> the run is accepted.**

> **Normative (the mutant class, and it has exactly ONE mutator).** `plr-sema/eval/predicate_mutants.py`
> is extended by **`p3a_pickup_already_held`**: mutate a planned program so a second `pick_up_resource`
> is issued while a resource is still held. PLR raises `RuntimeError` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2069-2070`; the static side must
> emit `WILL_FAIL` at the raised index. **This is the only mutator that exercises the typestate's `T`
> direction, and that is exactly the class's point** — a two-state tracker tested only in the `SAFE`
> direction is half tested, which is increment 7 D1's own argument.
>
> **Floor, with a denominator, in p1's own published shape:** `n_achieved_will_fail_at_raised_index`
> over `n_ran`, with `n_construction_skipped` and `n_error` beside it, and the floor is
> **`achieved == attempted` with `attempted ≥ 60`** and 0 unsound in both directions. Sixty rather than
> increment 7's two hundred, because the mutable population is the 93 move operations and not the 544.
> **A bare floor of 1 is refused**, for C23's reason: 1/93 satisfies it.
>
> **If D7 is declined this class is WITHDRAWN together with the typestate row rather than left to report
> 0** — increment 6 §15.16.3's lesson, that a class which can only ever report 0 is a publication and
> not a gate.

> **Normative (a mutator on `:2055` is NOT constructible, and the reason is a fact about the harness).**
> The dual — a backend with no arms — is a property of the **backend class**, not of a planned call's
> kwargs, and the mutator API mutates kwargs. `:2055` can therefore only ever produce `SAFE` on this
> corpus, and its `T` branch is unreachable by construction. **Stated as a property of the site rather
> than left as an absence**, and it is the same shape §16.11 recorded for `:321`.

---

## 17.10 Acceptance criteria

- **AC-17.1 (M-INH resolves, is measured whole-surface, and fails closed).** `_state_updated` is
  asserted **by name** to resolve to `Resource._state_updated` and to contribute **zero** guards
  (`external/pylabrobot/pylabrobot/resources/resource.py:932-934`); the whole newly-resolved
  `(class, name)` selection is published with each pair's unique defining base; and the refusal count
  is broken down by which of §17.2's three conditions refused it. **Three fail-closed fixtures, one per
  condition, and the first is the stub-defeating half:** a name defined on **two** classes in the base
  closure resolves to **neither** and the gap stands, asserted positively — an implementation that
  takes the first base passes every other fixture and fails this one; a base outside the index leaves
  the gap; and a closure that would more than double an entry point's guard count halts with a message
  naming the entry point rather than landing. A grep over the survey and the derive package asserts
  **no** PLR base-class name occurs as a literal, which is §17.2's no-hand-typed-fact claim made
  checkable. Per entry point, closure size and guard count are published **before and after**.
- **AC-17.2 (R-ARM, the observation field, and the amended truthiness clause).** `verify()` returns
  `arm_slots` from the **same** single capture point §16.2.1 fixes, `None` with the rest of the record
  on any raising read; a fixture asserts the field is empty **before** `await setup.machine.setup()`
  and non-empty after, which is the placement half
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:212`); and a fixture asserts it
  sorts **numerically**. Positive: `EnvRef(("self","_resource_pickups"))` resolves to the observed
  complete `Seq`, and `:2055` is asserted `SAFE` end-to-end **through the shipped guard record**, not
  through a hand-built predicate. **Two stub-defeating halves.** (i) A fixture with
  `self.setup_finished` at ⊤ still yields `SAFE`, which is the Kleene-`And` claim made checkable
  (`plr-sema/src/plr_sema/check/predicate.py:910-916`) — an implementation that requires both conjuncts
  fails it. (ii) `self.head` in predicate position is asserted **still ½**, by shape, with an
  **observed and non-empty** head — the kept refusal made checkable, which an implementation that
  simply deletes the shape test fails. An **empty** `arm_slots` is asserted to make the clause `F`, not
  ½. Increment 7's §16.5.1 text and the code comment that repeats it are asserted to carry the amended
  wording.
- **AC-17.3 (the typestate: the anchor, the effects, the order, and the four widenings).** The complete
  anchor selection is published, with `_resource_pickup` asserted present **by name** and every
  candidate removed by §17.4.2's absence rule labelled with the clause that removed it — including a
  synthetic `property` whose setter does more than one assignment, asserted **absent**, which is this
  criterion's first stub-defeating half because an implementation that skips the setter test passes
  every shape fixture and fails this one. The three move guards are asserted to decide **by state**:
  `:2070` from `EMPTY`, `:2120` and `:2147` from `HELD`, each asserted individually, which is the
  second stub-defeating half — a single per-call state cannot satisfy all three (§17.1.3). **Four
  widening fixtures, one per §17.4.3 condition**, each asserting `guard_env_dependent` and **not** a
  verdict: an effect site inside an unsatisfied scope; an assignment inside an `ast.Try` handler; an
  unresolved delegate between two guards; and an undecided prior operation on the same receiver.
  `n_typestate_widened` is published per condition and asserted **0** on the move family. `p3a` is
  published as `achieved/attempted` in p1's shape with the floor of §17.9. The assumption table is
  asserted to have **five** rows — unchanged — which is §17.4.3's no-new-assumption claim made
  checkable. **If D7 is declined this criterion is withdrawn together with its task row.**
- **AC-17.4 (M3: the depth lift, the per-site list, and the conjunctive fold).** The complete
  newly-admitted `(K, D)` selection at `depth ≥ 2` is published, with `_check_args` asserted present
  **by name** from `move_lid`, `move_plate`, `transfer`, `discard_tips` and `stamp`; `move_resource`'s
  **two** call sites are asserted present as **two** list entries with their own linenos
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2345-2350`, `:2364-2369`).
  **Four fixtures, and the first two are the stub-defeating halves.** (i) A multi-site delegate where
  one site would yield `F` and the other declines is asserted **½**, not `F` — the conjunctive fold
  made checkable. (ii) A `depth == 2` argument that is a caller-side **name** rather than a constant is
  asserted to bind **nothing**, which is the whole of §17.5.1's narrowness claim. (iii) A `SetLit` at
  depth 3 binds. (iv) `caller_reachability_clear` and `caller_scope_trail` are asserted **absent** at
  every `depth ≥ 2` guard, and a grep asserts no new `WILL_FAIL` path was opened. `:375` is asserted
  `SAFE` on the 93 `move_*` operations **by name**. **If D8 is declined this criterion is withdrawn
  together with its task row.**
- **AC-17.5 (the residual-kwargs Term and `:383`'s second route).** `Var(W)` for an entry point's
  `**kwargs` parameter resolves to the complete `Seq` of `call.kwargs` keys not among the entry point's
  declared parameters; a fixture with one genuinely-extra keyword asserts a **non**-empty `Seq` and a
  `:383` decline, which is the stub-defeating half — an implementation returning an empty `Seq`
  unconditionally passes the happy path and fails this. The comprehension rule is asserted on both
  sides: an empty source yields an empty complete `Seq`; a non-empty source yields ⊤ whatever the
  filter. `:383` is asserted `SAFE` on the 93 `move_*` operations with `has_var_keyword` asserted
  **False** for the backend methods involved
  (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:223-231`), so the assertion
  is provably reached through the **new** route and not the old one. `n_check_args_decided` is published
  split by route. `len(D6_SITE_RULES)` is asserted **3** and HM-26's `declared` asserted **3**
  (`plr-sema/src/plr_sema/check/predicate.py:1333-1337`), so an implementation that adds a fourth keyed
  site fails. **If D10 is declined this criterion is withdrawn together with its task row.**
- **AC-17.6 (tier 1 — both fence counters at zero, the reason counts, and increment 7 preserved).** The
  sidecar-gated replay reports `unsound == 0` under the unmodified predicate and `unsound_scoped == 0`;
  `pick_up_tips` reaches `scope_verdict == SAFE` on **≥ 216** operations;
  `guard_predicate_unparsed` is asserted **unchanged at 495** and `guard_operand_unknown` **unchanged at
  144**; `unresolved_delegate` is asserted **0 findings** and the member is asserted **still present**
  in `REASON_VOCABULARY` (`plr-sema/src/plr_sema/verdict.py:147-199`), which is §17.6's
  not-retired claim made checkable. `n_findings_decided` is published against §17.8.3's certain **3,721**
  and target **4,017**, and is **not** gated. **The stub-defeating half: an implementation that lands
  every mechanism but never threads the observation scores 2,817 and fails.**
- **AC-17.7 (non-regression and the mutant class).** m1, m2, v1 and the tier-2b set at their
  increment-7 closing values with `region_unsound == 0`, **with any tier-2b movement attributed to a
  named mechanism from §17.9's disclosure before the run is accepted**. p1's three mutators are
  re-measured **unchanged**, which is what proves this increment disturbed no depth-0 population.
- **AC-17.8 (the measured sets are published and the gate is decided by them).** All **nine** blocks of
  §17.8.1 are present and non-null; §17.8.3's per-entry table is reproduced cell by cell for whichever
  branches of D7–D10 the user took, with every divergence recorded in §17.14 rather than absorbed; the
  GO/NO-GO is recorded against the published per-operation residual site set, and **the gate is asserted
  computable from the JSON alone, without reading this document**. §17.1.4's open diagnosis is either
  **closed with its cause named** or explicitly recorded as still open with the 148 published — the
  report must say which, so §17.8.3's 321 target is never read as achieved when it is not. Block (9)'s
  destination-type distribution is published whether or not increment 9 uses it.
- **AC-17.9 (this document is machine-checked).** `plr-sema/tests/test_spec_lint.py` gains a constant
  for this file and parametrises it into both live-spec tests; `.praxia/docs/INDEX.md` is regenerated;
  and `uv run pytest plr-sema/tests/test_spec_lint.py -q` is **actually run** with its result recorded
  — the citation checker reporting **zero** failing violations over this file and the AC-gating half of
  the cross-reference checker reporting zero, with the other eight specs unchanged at zero.

---

## 17.11 Task rows

> **Normative (the ordering, forced by the same gate discipline increments 5, 6 and 7 all impose).**
> **T50 must land and publish its measured selection before T52 assigns a single typestate**, because
> §17.4.3's third widening condition is defined over the unresolved-delegate population and a typestate
> computed against a stale one is a state nobody has inspected. **T53 must precede T54**: the
> residual-kwargs route reads a call-site argument through the same map T53 generalises, and landing
> the route first would make its measured selection unattributable. **T51 is independent of all of
> them.** T55 is last and is where §17.1's analysis is confirmed or falsified.

> **Normative (why every AC is gated exactly once, and where the conditional rows sit).** The
> cross-reference lint reads the **gate cell only** — column 4 of a row matching its task-row pattern
> (`plr-sema/scripts/check_spec_crossrefs.py:139-156`). An AC named in a scope cell, in a box, or in
> prose is documentation and not a gate. **AC-17.3, AC-17.4 and AC-17.5 are gated on T52, T53 and T54,
> each conditional on a user decision** — the same construction increment 7 used for AC-16.13 on T48,
> and the reason a declined decision withdraws the criterion **with** its row rather than leaving it
> unsatisfied.

| task | scope | files | gate | ~LOC | depends on | model |
|---|---|---|---|---|---|---|
| **T50** | **CONDITIONAL on D9.** **M-INH — inherited self-call resolution (§17.2), both halves in one commit.** The survey's per-`ClassDef` method-name set gains the transitive base closure's method names, computed over a whole-tree class index, with an additive `inherited_delegates` field naming what inheritance alone admitted; `resolve` gains a **third** step after its two existing same-module steps, returning the unique defining base's key and `None` on ambiguity; the base closure is built from `build_plr_class_index` and `subclass_closure_from_bases`, both shipped, with **no** PLR base-class name typed anywhere; three fail-closed conditions — ambiguity, a base outside the index, and a closure-doubling halt that stops and surfaces to the user rather than landing; the complete newly-resolved selection and the per-condition refusal counts published; per entry point, closure size and guard count published before and after. **`_state_updated` contributes zero guards and the reason's whole population goes to zero** | modify `scripts/survey_plr_preconditions.py`, `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q`; then re-run the survey and regenerate the contract table — satisfying **AC-17.1** | ~190 | — | Sonnet — the ambiguity refusal is the one clause here that stands between a resolution and the wrong function body's guards, and this row can move every number in the benchmark |
| **T51** | **R-ARM and the truthiness clause (§17.3, §17.1.2).** `verify()` gains the additive `arm_slots` field at the **existing** single capture point after `await setup.machine.setup()`, inside the existing fail-closed guard, `None` with the rest of the record on any raising read; the harness builds its `obs:` member under §16.2.3's JSON encoding with numeric int sort; **R-ARM** resolves `self._resource_pickups` to that complete `Seq`; **the amended predicate-position clause** — a complete `Seq` is `T` iff non-empty and `F` iff empty — with the `self.head` shape refusal **kept unchanged**; the amendment written into increment 7's own §16.5.1 text and the code comment that repeats it, in this commit; `n_resolved_by_rule` for R-ARM per lane and `n_seq_truthiness_decided` published. **No new registry unit is claimed for this row** (§17.7's item 1) | modify `training/verify/verifier.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/eval/region_oracle.py`, `plr-sema/src/plr_sema/check/predicate.py`, `.praxia/docs/specs/260909_plr-sema-observation-increment.md` (the §16.5.1 amendment), `training/tests/test_verify_postconditions.py`, `plr-sema/tests/test_check_graph.py`, `plr-sema/tests/test_cache.py` | `uv sync --all-packages`; `uv run pytest training/tests/test_verify_postconditions.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q`; `uv run pytest plr-sema/tests/test_spec_lint.py -q` (the increment-7 edit must not break its citations) — satisfying **AC-17.2** | ~120 | — | Sonnet — small, but it amends a shipped refusal, and the kept-`self.head` fixture is the only thing preventing that amendment from quietly becoming general |
| **T52** | **CONDITIONAL on D7 — do not start without the user's answer.** **The `_resource_pickup` typestate (§17.4).** P5's anchor shape and its absence rule (a `property` whose setter is not a single assignment; an assignment outside the class body; a qualname at more than one lineno); P6's effect table with `widen` for every non-plain assignment shape; the **intra-operation source-order walk** over the entry point's own delegate call statements, giving every guard a position and folding every strictly-earlier effect; the **four** fail-closed widening conditions of §17.4.3; the two-state lattice with its optional held-resource `ir.Ref` payload, which decides nothing this increment; the inter-operation carry in `TipWalk`'s own manner, resetting only where **A-COMPLETES** already licenses it; the complete anchor selection, the per-guard state assignment and `n_typestate_widened` per condition published. **The approved HM-25 `declared` 10 → 11 spend (D7), filed as ONE further unit inside the existing entry whose `what` now also names the singleton-anchor pattern, with `_measure_hm25` importing the anchor/effect symbol — stopping and asking the user if the measured count would exceed 11.** **No new named assumption is added and the assumption table stays at five rows** | modify `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/src/plr_sema/check/tipstate.py`, `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/src/plr_sema/_hand_maintained.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_tip_typestate.py`, `plr-sema/tests/test_hand_maintained_ratchet.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_tip_typestate.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q` (`live_rows` 25 and `BUDGET_CAP` 25, both asserted **unchanged**) — satisfying **AC-17.3** | ~290 | **T50**, with its measured selection published | Sonnet — **the largest and riskiest row in the increment**: an intra-operation ordered state is machinery the analyzer has never had, and the four widening conditions are the whole of what stands between it and a state that is confidently wrong |
| **T53** | **CONDITIONAL on D8 — do not start without the user's answer.** **M3 — the constant-argument map at any depth (§17.5.1).** `caller_args` becomes, additively, a per-call-site **list** with each entry's own `lineno`, the old single-map and `None` shapes both still accepted; site rules evaluate once per entry and fold **conjunctively**, `F` only if every entry yields `F`; M1's `depth == 1` restriction is lifted for arguments that parse as a `Term` with **no free names** — a constant, a `SetLit`, or a `self`-rooted `EnvRef` — and for nothing else; **`caller_reachability_clear`, `caller_scope_trail` and D1's `WILL_FAIL` lift stay strictly `depth == 1` and are untouched**; the complete newly-admitted selection and the surviving-clause refusal breakdown published. **This row is where §17.1.4's `:375` divergence is diagnosed: if the 148 `aspirate`/`dispense`/`drop_tips` operations do not clear, the row publishes the decline reason per operation rather than absorbing it** | modify `plr-sema/src/plr_sema/derive/bindings.py`, `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_check_graph.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q` — satisfying **AC-17.4** | ~200 | — | Sonnet — it relaxes two deliberate soundness fences at once, and the depth-2-name fixture is the one test that proves only the intended one moved |
| **T54** | **CONDITIONAL on D10 — do not start without the user's answer. This is D5a's production (5), NOT D5a.** **The residual-`**kwargs` Term and `:383`'s second discharge route (§17.5.2).** `Var(W)` for an entry point's `**kwargs` parameter resolves to the complete `Seq` of `ir.Call.kwargs` keys not among the entry point's declared parameters, read through the shipped function index; the one comprehension rule — an empty complete `Seq` source yields an empty complete `Seq`, any other source yields ⊤; `_eval_check_args_strict_site_rule` gains a second, **disjunctive** route returning `F` when the call site's `backend_kwargs` argument resolves to an empty complete `Seq`, keeping the existing `has_var_keyword` route unchanged; `n_check_args_decided` published split by route. **No fourth keyed site is added: `len(D6_SITE_RULES)` stays 3 and HM-26 stays at `declared` 3.** **D5a's other four productions — a `keys()` term, a set-difference `BinOp`, an `E-SIG` comprehension family, and the general both-directions model — are NOT this row and remain increment 9's** | modify `plr-sema/src/plr_sema/derive/predicate_ast.py`, `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_check_graph.py`, `plr-sema/tests/test_hand_maintained_ratchet.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q` — satisfying **AC-17.5** | ~150 | **T53** | Sonnet — one-directional by construction (both `_check_args` guards carry `reachability_clear` false), so the whole risk is whether the residual key set is genuinely complete rather than a lower bound |
| **T55** | **The oracle, the mutants and the gate (§17.8, §17.9).** Tier-1 re-run under the unmodified predicate with both fence counters published; §17.8.1's **nine** measured blocks; §17.8.3's per-entry prediction table reproduced cell by cell for whichever branches of D7–D10 the user took, with every divergence recorded; the after-ledger with `consistency.ok`, its published delta and the per-method `residual_site_sets` threaded through so the ledger can audit the gate directly; `plr-sema/eval/predicate_mutants.py` extended with `p3a_pickup_already_held` published as `achieved/attempted`; the m1/m2/v1/tier-2b non-regression set re-measured with every movement attributed to a named mechanism; **§17.1.4's open diagnosis either closed with its cause named or explicitly recorded as open with the 148 published**; block (9)'s destination-type distribution published for increment 9; **the GO/NO-GO recorded against the published per-operation residual site set, computable from the JSON alone** | modify `plr-sema/eval/oracle_replay.py`, `plr-sema/eval/predicate_mutants.py`, `plr-sema/eval/unknown_ledger.py`, `plr-sema/eval/t30_measure.py`, `plr-sema/tests/test_oracle_replay.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q`; then the tier-1 replay with its three standard flags, `unknown_ledger.py` into `outputs/plr-sema/unknown_ledger_2609XX_inc8.json`, `predicate_mutants.py`, `tip_mutants.py`, `volume_mutants.py` and `region_oracle.py` into `outputs/plr-sema/*_2609XX_inc8.json`, publishing the delta against the `260909_final` set — satisfying **AC-17.6**, **AC-17.7** and **AC-17.8** | ~260 | T50, T51, T52, T53, T54 | Sonnet — every published number is a measurement, and this row is where §17.1's site analysis is either confirmed or falsified by one set |
| **T56** | Lint and index: register this file in `plr-sema/tests/test_spec_lint.py` and parametrise it into both live-spec tests; regenerate `.praxia/docs/INDEX.md`; **actually run the lint and record the result** | modify `plr-sema/tests/test_spec_lint.py`; regenerate `.praxia/docs/INDEX.md` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_spec_lint.py -q` — satisfying **AC-17.9** | ~6 | — | Haiku |

**Sizing note, stated honestly and with the one number that is a guess flagged as one.** T50 at ~190 is
two small AST changes plus their published selections and the doubling bound; its risk is measurement
breadth, not code volume. T51 at ~120 is one observation field, one path rule, one evaluator clause and
the increment-7 text edit. **T52 at ~290 is the guess**, and it is the only one: ~70 for P5 and P6's
shape tests and the absence rule, ~110 for the ordered walk and the four widening conditions, ~50 for
the inter-operation carry, ~60 for the published selections — and the ordered walk is machinery with no
precedent in this codebase, so it could be materially larger. **T52 is the row to split first if a
session boundary falls inside it**, at P5/P6 versus the walk. T53 at ~200 is the per-site list, its
round-trip and the depth lift. T54 at ~150 is one Term, one comprehension rule and one disjunct.
**Total for the four conditional rows plus T51 and T55: ~1,010 LOC across six rows, which is three
sessions.** **Do not reorder T50 after T52**: a typestate computed against a stale unresolved-delegate
population is the configuration the ordering box exists to prevent.

---

## 17.12 Not in this increment

- **E-TYPE's negative direction, and with it the six `drop_resource` branch-arm sites.** §17.1.5 is the
  argument and it is about soundness rather than cost: a wrong `F` in a scope entry becomes a `SAFE`
  with no predicate reasoning between it and the verdict
  (`plr-sema/src/plr_sema/check/predicate.py:1040-1044`). It needs an exactness field on `ir.Resource`
  (`plr-sema/src/plr_sema/check/ir.py:178-191`) and an `IR_VERSION` bump (`plr-sema/src/plr_sema/check/ir.py:90-93`). **D11, recommended NO**, with
  §17.8.1 block (9) as the data increment 9 must argue it from.
- **`D5a`'s other four productions** — a `set(<x>.keys())` term, a set-difference `BinOp`, an `E-SIG`
  family over the `inspect.signature` comprehensions, and the general both-directions model.
  **Production (5) alone is taken** (§17.5.2), because it is the only one the `SAFE` direction forms.
  The remaining four stay increment 9's, exactly as increment 7 §16.14 left them.
- **An enum-constant `Term` production and an enum equality rule.** Refused by name in §17.1.4: it
  would decide `:383`'s own predicate at `move_resource`'s two literal call sites and still not close
  the site, because the same closure reaches `_check_args` from `pick_up_resource` with
  `get_strictness()` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2079-2081`).
  One production bought for zero operations.
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
- **The γ loop idiom, the `pred`-aware `BRANCH`, tuple-display comparison, arithmetic `BinOp` terms, a
  fourth loop-append binding idiom, the well-seeding observation, and the general `Identity(Term,
  Term)`.** Increment 7 §16.14's dispositions all stand, and this increment adds a further reason for
  the arithmetic `BinOp`: its one move-family consumer is `:2211`, which sits behind the refused
  mechanism anyway, so admitting it would buy nothing here either.
- **A thirteenth `REASON_VOCABULARY` member.** §17.6's table folds every new give-up point into an
  existing one, mechanically.
- **A new registry row, in every branch.** §17.7. `live_rows()` stays 25 against `BUDGET_CAP` 25 and
  the only ask is one per-row ceiling unit.
- **Replacing §8's hand-written-contract bridge**, and **precision targets, deferred row (f)**. Both
  recorded, not discharged, exactly as increments 6 and 7 record them.

---

## 17.13 The questions, their dispositions, and every user decision hook

### Q7 — is the `unresolved_delegate` gap semantic or mechanical?

**DISPOSED by §17.1.1 and §17.2: mechanical, and closing it costs no registry row.** `Resource`'s
`_state_updated` is two lines with no precondition
(`external/pylabrobot/pylabrobot/resources/resource.py:932-934`); the survey resolves `self.<name>`
against the class's own body alone (`scripts/survey_plr_preconditions.py:347-354`) and `resolve` within
the same module alone (`plr-sema/src/plr_sema/derive/__init__.py:414-421`). **The alternative
considered and rejected: a site-keyed exception for this one call.** That is HM-26's class, a fourth
keyed rule and a registry unit, for a defect that is general across the whole PLR surface and derivable
from indices already shipped. **Rejected, and recorded as rejected.**

### Q8 — can the `_resource_pickup` typestate reuse increment 1's model unchanged?

**DISPOSED by §17.1.3 and §17.4: no, and the one difference is the whole of the work.** `TipWalk`
carries one state per receiver per CALL (`plr-sema/src/plr_sema/check/tipstate.py:521-543`); the three
move guards live inside one CALL and read two different states. The **intra-operation ordered walk** is
what closes it, and its four fail-closed widening conditions are what keep an ordering claim from
becoming a control-flow claim the analyzer cannot make. **No new named assumption is needed** and
§17.4.3 says why, which is this increment's strongest single property and the first thing a round
should attack.

### Q9 — why did increment 7's `:375`/`:383` prediction miss on 321 operations?

**DISPOSED by §17.1.4, PARTIALLY: two of the three causes are named from source and the third is an
open diagnosis this document refuses to guess at.** The arithmetic is sound and is re-derived at the pin
for the move family; what refuses is `compute_caller_args`' single-call-site clause and its
`depth == 1` restriction (`plr-sema/src/plr_sema/derive/bindings.py:931-941`), which between them
account for 173 of the 321. The remaining 148 — `aspirate`, `dispense`, `drop_tips`, each at depth 1
with one call site — are **not** explained by either, and §17.8.1 block (5) is where T53 and T55 must
say why. **A spec that guessed here would repeat increment 7's own error**, which was to state a
per-site prediction the document could not derive.

### Q10 — what may the headline claim?

**DISPOSED: no joined `SAFE`, and the refusal is stated before the gate rather than at it.** `move_*`
stays `UNKNOWN` under both `verdict` and `scope_verdict` on all 93 operations, and §17.1.5 names the
obstruction, sizes it and refuses it on soundness grounds. **What the sprint may claim under all four
hooks taken:** the move family's residual reduced from thirteen sites to **six**, all in one PLR
function and all behind one named mechanism; `unresolved_delegate` at **0 findings** benchmark-wide,
the first `REASON_VOCABULARY` member to reach zero population; `:375` and `:383` discharged on the 93,
with a route to 321; `n_findings_decided` **2,817 → ≥ 3,721**; and increment 7's 216 preserved. **It may
NOT report a joined `SAFE` on any operation other than the 216 that already have one**, and §17.8.2's
condition (2)-through-(5) exist to make that claim checkable rather than trusted.

### The user decision hooks, together, each with this document's recommendation

| id | the decision | what it costs | what declining costs | recommendation |
|---|---|---|---|---|
| **D7** | HM-25 `declared` **10 → 11**, one further per-row ceiling unit, for §17.4's singleton-typestate anchor and effect shapes | one ceiling unit; `live_rows()` and `BUDGET_CAP` both **unchanged at 25**; no cap conversation | `:2070`, `:2120` and `:2147` stay ½ on 93 operations; the gate's residual is eight sites, not six; `p3a` is withdrawn with its criterion; ~290 LOC leaves the increment | **YES.** It is increment 1 P2's own class — a typestate-anchor property shape — already the first entry on this row (`plr-sema/src/plr_sema/_hand_maintained.py:1000-1054`), and HM-25 is the LOUD-failure row whose `breaks_when` this increment's published selections satisfy. Increment 6 spent 8 → 9 and increment 7 spent 9 → 10 on this row for the same reason |
| **D8** | **M3** — relax M1's single-call-site clause to a per-call-site list with a conjunctive fold, and lift its `depth == 1` restriction for **call-site-constant arguments only** | zero registry; two deliberate soundness fences relaxed in one row, which is why the depth-2-**name** fixture is AC-17.4's stub-defeating half | `:375` stays ½ on 321 operations and `:383` is unreachable regardless, since §17.5.2's route reads a call-site argument through this same map; increment 7's divergence stays open | **YES.** The lift is genuinely **narrower** than the depth-1 map D1 already permits: a call-site constant is resolved against no namespace at all, so clause 6's reason does not apply to it (§17.5.1). The conjunctive fold is the only sound fold, and it is strictly more conservative than the single-site rule it replaces |
| **D9** | **M-INH** — resolve inherited `self.<name>()` calls across the whole PLR surface | zero registry; but it changes the closure for **every** entry point and can therefore move every number in the benchmark, including increment 7's 216 | `unresolved_delegate` stays at 186 findings on 93 operations; the gate's condition (2) is unreachable and its residual has seven entries | **YES.** The fix is derived from two shipped whole-tree indices with no PLR name typed, and the gap it closes is a two-line function that cannot raise. **It is a decision and not a sprint choice** precisely because of the blast radius: §17.8.2 makes the 216 a hard gate condition rather than a hope, and §17.2's doubling bound stops the row rather than landing a closure nobody sized |
| **D10** | The **residual-`**kwargs` Term** — D5a's production (5), and only that one — giving the shipped `:383` site rule a second discharge route | rides D7's unit under §17.7's argument, or one further unit if the round rejects that; **no** new registry row and **no** fourth keyed site, so HM-26 stays at `declared` 3 | `:383` stays ½ on 321 operations; the gate's residual is seven sites. **Nothing else can reach it**: `has_var_keyword` is `False` for every backend method the move family calls -- `pick_up_resource`, `move_picked_up_resource` and `drop_resource` (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:223-231`) take no `**kwargs` at all | **YES.** It is one-directional by construction on D-G6's own argument, it is the single production the `SAFE` direction actually forms, and increment 7 §16.14 already made D5a increment 8's — this takes the fifth of its five productions and refuses the other four by name |
| **D11** | **E-TYPE's negative direction** — an exactness fact on `ir.Resource`, so `isinstance` can decide `F` and E-SCOPE can clear the six `drop_resource` branch-arm sites | an `IR_VERSION` bump that re-keys every cached entry, and a derived `F` in a **scope** entry, where one wrong answer becomes a false `SAFE` on six sites at once with no fence between it and the verdict | the move family's residual stays at six sites and `move_*` cannot reach `scope_verdict == SAFE` in increment 8 or 9 without it. **This is the whole of what stands between this increment and a headline** | **NO, this increment.** Not on cost — it is the cheapest remaining mechanism by LOC — but because it is the only one whose failure mode is the one the project exists to prevent, and taking it alongside four other new mechanisms would make a regression unattributable. **T55 publishes the destination-type distribution so increment 9 can argue it from data**, and the recommendation there may well be YES |

---

## 17.14 Implementation record

*(Column shape mirrors increments 5, 6 and 7. No row is started; the whole table is prospective.
First-column ids are deliberately unbolded so the cross-reference lint's task-row pattern does not read
this table's cells as gate cells.)*

| row | commit | what landed | measured vs the spec's expectation | divergences |
|---|---|---|---|---|
| T50 | — | — | — | — |
| T51 | — | — | — | — |
| T52 | — | — | — | — |
| T53 | — | — | — | — |
| T54 | — | — | — | — |
| T55 | — | — | — | — |
| T56 | — | — | — | — |

---

## 17.15 Specification log

**Written 260909 by `praxia:specification-specialist` at Opus, against final HEAD `52178d80`, in
worktree `wt-20260909-172820`, with no shell access — every claim in this document is either read from
source at the cited lines or read from the two instrument files, and none is measured by this author.**

**What the investigation found that the dispatch brief did not contain**, recorded because each changed
the shape of the increment:

1. **The brief named SEVEN `guard_env_dependent` clusters at 93 operations. There are NINE.** `:2284`
   and `:2290` are the two it omitted
   (`outputs/plr-sema/unknown_ledger_260909_final.json:652-662`, `:692-702`). The residual is thirteen
   entries, not eleven.
2. **The `unresolved_delegate` gap is not semantic.** `Resource._state_updated` is two lines and cannot
   raise (`external/pylabrobot/pylabrobot/resources/resource.py:932-934`). The brief's framing —
   "whatever they delegate to that produces the `_state_updated` unresolved-delegate gap" — presumed a
   contract that could not be derived; the truth is a resolution rule that never looks at base classes.
3. **The three move methods have an IDENTICAL residual, not merely a similar one**
   (`outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json:241-261`). That is what makes a
   structural gate possible at all, and it is the single most useful fact in the instrument.
4. **`:375` and `:383` are increment 7's own falsified prediction**, still open at 321 operations. The
   brief did not mention them; they are the largest cluster pair in the ledger and the increment's
   biggest whole-benchmark opportunity.
5. **The chatterbox backend's move methods take no `**backend_kwargs`**
   (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:223-231`), which is why the
   shipped `:383` rule can never fire for this family and why D10 exists at all.
6. **The typestate the brief anticipated is real but is NOT increment 1's shape** — the ordering is
   intra-operation, and that is §17.4's whole cost.

**The constraint the brief imposed, and how it was met.** The registry is at full cap: `live_rows()`
25, `BUDGET_CAP` 25, zero headroom. **This increment asks for no row in any branch.** Every mechanism is
either derived (M-INH, M3), free under a unit already spent (R-ARM, on D4's own
pattern-not-instance argument), or one further ceiling unit on the existing loud-failure row (D7).
`REASON_VOCABULARY` stays 12 of 12 and no thirteenth is proposed, matching increment 7's restraint.

**Owed before this document is implemented:** an adversarial round. The three claims to attack first,
named by this document rather than left to be found. **(1) §17.4.3's no-new-assumption claim** — build
a program in which the ordered walk's state at a guard depends on a fact no listed assumption supplies;
if it exists, the assumption must be named before T52 lands. **(2) §17.7's argument that R-ARM costs
nothing** — it rests on D4's pattern-not-instance box, and the amended predicate-position clause is
arguably an evaluator rule rather than a path shape. **(3) §17.8.3's certain/target split** — the 173
certain operations for `:375` rest on this document's reading of which M1 clause refuses which entry
point, and that reading is from source, not from measurement.

---

## References

- Main specification (amended): `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` — the deferred
  rows, with (e) — the `move_*` family — at `:2520` and (f), precision targets, at `:2524`.
- Increment 1: `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md` — §10.2.2's typestate
  anchor, §10.2.4's effects, §10.4's transfer functions, §10.5's graph walk, and §10.6.3's named
  assumption table (`:744-754`), which §17.4.3 leaves at five rows and which supplies **A-COMPLETES**
  (`:752`) as the licence for the inter-operation initial state.
- Increment 5: `.praxia/docs/specs/260903_plr-sema-volume-increment.md` — §14.6's O5 pattern, the
  precedent §17.3's `arm_slots` argument is stated against, and R1's own risk direction, which §17.5.1
  is explicitly designed to stay out of.
- Increment 6: `.praxia/docs/specs/260904_plr-sema-predicate-increment.md` — §15.1's tiers and its
  derived-tier box (§17.8.4's refusal 1), §15.2's grammar, §15.4's `E-CALL`/`E-TYPE`/`E-SCOPE`/
  `E-UNCOND`, §15.7's ordered reason procedure (unchanged here), and §15.16.3's lesson that a class
  which can only ever report 0 is a publication and not a gate.
- Increment 7: `.praxia/docs/specs/260909_plr-sema-observation-increment.md` — §16.2's observation
  record and its closed refusal list, §16.3's derived backend surface and C15 absence rule, §16.4's
  argument map and M1, §16.5's `E-ENV` rules (§16.5.1's predicate-position sentence is amended by
  §17.1.2), §16.9's registry arithmetic and D4's pattern-not-instance box, §16.10.4's anti-gaming
  discipline, §16.14's deferred row (e) (`:2025-2027`) and its D5a deferral (`:1979-1983`), and
  §16.15's D5/D6 boxes with D-G6's one-directionality argument.
- The instrument: `outputs/plr-sema/unknown_ledger_260909_final.json` with its companion
  `outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json`, both read directly at every cited
  range and neither produced by this author.
- Sprint 130's plan, read for its §8 log style and its §9 outcome:
  `.praxia/docs/plans/260909_plr-sema-sprint130-observation.md:122-161`.
