---
title: "plr-sema increment 6 — the predicate language: a three-valued grammar over guard conditions, measured by the UNKNOWN ledger"
description: "Sixth post-corpus increment to the plr-sema pre-corpus specification, taking the main spec's deferred row (c), revised after adversarial round 1 (C1-C18 + D1-D3). What it ships, narrowed as round 1 forced: **per-finding SAFE on real executed operations plus a legible residual** -- NO joined SAFE this increment. Round-1 changes carried here: E-UNCOND gains clauses (4) no WILL_FAIL at depth >= 1, (5) a depth-0 empty scope_trail is not vacuously unconditional, (6) the raise_guard's own condition entry at scope_trail[0] is excluded from both scope tests; the tier-1 soundness fence is left UNMODIFIED (the exc_class -> site narrowing is deleted) and rows_excused_by_scope becomes a pure annotation; tier (iii) is DERIVED as guard.is_dynamic_raise and emits one Finding, UNKNOWN/guard_env_dependent, plus an excludes_sites annotation; the GO gate is restated over REASONS (zero guard_predicate_unparsed and zero guard_operand_unknown on >= 1 executed op) rather than over tiers, which would have been self-satisfying; E-TYPE is restated T iff is-or-subclass-of / F iff hierarchy-disjoint AND exact, with _generic_plr_type_name declarations normatively never exact; E-CALL gains param_defaults (D1), the beta truthiness interaction, the parameter-rebinding clause and the depth->=1 forbiddance; beta gains the length-preserving-rebinding exception (population 8, measured) and the iterand single-write clause; AC-15.8's >= 1,000 floor is replaced by n_findings_decided >= 223. Four decisions were left at round 1 as pending user approval with this round's recommendation (all four APPROVED 260907; see the amendment note below): HM-25 declared 8 -> 9 for alpha+beta (recommend yes), the headline substitution to increment 7 (recommend yes), gamma (recommend no, increment 7), and REASON_VOCABULARY 10 -> 12 of cap 12 (recommend yes, one-member fallback described). Ledger re-run under positional (row_idx, op_id) keying: 544 executed ops, unresolved_delegate cluster 93, :375/:383 at 544, consistency ok, n_row_id_collisions 12 all move_*. AMENDED 260907 (spec_version 18) after band B measured the gate NO-GO. All five sprint decisions are APPROVED by the user: HM-25 declared 8 -> 9 (AC-15.7 asserts 9), the headline substitution, gamma NOT adopted, REASON_VOCABULARY 10 -> 12, and this amendment itself. The amendment adds three productions to section 15.2: EnvRef(path, args) for an expression rooted at the literal name self (an attribute chain, optionally the callee of a call whose arguments all parse as Terms); Zip(items) as a Term usable as the seq of AllOf/AnyOf; and the membership comparators in/not in as Cmp ops. All three evaluate to half/top unconditionally (section 15.4 E-ENV) and carry guard_env_dependent rather than guard_predicate_unparsed when no Opaque node remains (section 15.7), which reconciles the section 15.7 / section 15.9 disagreement over line 409 that the measurement exposed. Re-predicted: pick_up_tips' two blockers (liquid_handler.py:409 and :514) both flip, giving {decidable, guard_env_dependent} = GO; every other candidate method's blocker is NOT self-rooted and does not flip (:657 rooted at a local, :116 an is-comparison with a non-None RHS, :2030 tuple displays, :2211 a BinOp, :2226 an is-comparison). Section 15.9 gains a published n_env_ref per cluster and per op, a top-10 EnvRef path list, a normative no-Var(self) invariant, and a T35 task row (grammar amendment, contract regeneration, the t30_measure population and family-dispatch fix-ups, re-measure) before T31. REVISED 260907 (spec_version 19) after the amendment's short adversarial pass (A-C1..A-C13, verdict needs_revision, revise-and-advance; no objection changed the GO prediction). What round 2 changed: G7 shape (2) now admits a self-rooted CALL only when the callee path has length >= 3 or its length-2 name is ABSENT from the derive package's own PLR function index -- a derived test, no list -- so PLR-layer helper calls (self._is_error_tail, self._check_96_head_fits_in_container, self._find_available_sites_sorted) stay Opaque as the coverage gaps they are, the stamp row's :1778/:1940 no longer flip, and n_env_ref_refused_plr_layer is published; the withdrawn narrowness claim is replaced by the measured 210/41 absorption counts. 'The amendment decides nothing' is now a THEOREM rather than a prediction: a Zip resolves to top unless every item resolves to a concrete Seq (then the positional zip truncated to the shortest), AllOf/AnyOf over a top seq is half and never vacuously T, and the membership deciding case is DELETED -- every in/not in Cmp is half unconditionally this increment, recorded as a refused production in section 15.13. Both contains_opaque and contains_env_ref range over the alpha/beta-SUBSTITUTED predicate, which the shipped classifier already assumes. Section 15.7's clauses are reordered so the operand test precedes contains_env_ref. The registry point is conceded: EnvRef/Zip/in are named inside the alpha+beta HM-25 entry and _measure_hm25 must import the production symbols. n_env_ref is split into n_env_ref_nodes (block 3) and n_env_ref_guards (block 4); the re-prediction table restates every cell as an exact guards/nodes pair. T30c is renamed T35 so the cross-reference lint can see it, and the amendment's ACs are gated on T35 directly. Its output is outputs/plr-sema/t30_measured_260908.json or later; the population fix-up already landed as t30_measured_260907.json (commit 15b84d31). REFINED 260908 (spec_version 20) after band C landed T35, T31 and T32 -- a POST-ROUND REFINEMENT, NOT adversarially reviewed, which is why status stays reviewed-round-2. T35 (a2cd0499, 100ab273) measured the gate GO: pick_up_tips 223/223 with residual {decidable, guard_env_dependent}, 386 guard sites carrying EnvRef over 417 nodes, n_env_ref_refused_plr_layer 12, n_var_self 0, n_zip 1, n_membership_cmp 48, and every method matching section 15.9's re-prediction table exactly incl. stamp at 0/0. T31 (1a58b337, 436c0edb) landed check/predicate.py with E-CALL/E-TYPE/E-SCOPE/E-VERDICT/E-UNCOND(1)-(6)/E-ENV and the section 15.7 clause order, REASON_VOCABULARY 12 of 12, HM-25 declared 9 measured as one collective probe, live_rows 24. T32 (e3970b3a, f63b3ff8) measured tier 1 at 0 unsound, crosscheck 191/191, n_findings_decided 1,563 against a floor of 223, guard_predicate_unparsed 5,656 -> 495, the after-ledger at 54 -> 53 clusters and 6,036 -> 5,157 findings with pick_up_tips residual exactly {guard_env_dependent} on all 223, unknown_rate still 1.0 as section 15.5 predicted, and non-regression exact at m1 199/199, m2 289/289, v1 67/67, tier 2b 16/0/7/3. ONE acceptance criterion failed: AC-15.10's predicate-mutant floor, 0 achieved on all three mutators, and the cause was E-UNCOND(5) itself -- pick_up_tips' :502 and :522 are depth-0 empty-trail guards standing below the conditional raise TypeError at :498, and C1's remedy blocked on any earlier ast.Raise. What spec_version 20 changes: E-UNCOND(5) is REFINED so that a depth-0 empty-trail guard may emit WILL_FAIL iff K has no earlier ast.Return, the guard is not lexically enclosed by an ast.Try or ast.With, and there is no earlier ast.Break/ast.Continue -- an earlier ast.Raise or assert NO LONGER blocks, on the argument (now normative, with C1's stronger wording recorded as superseded) that if the earlier raise fires the operation fails there and if it does not, control reaches the guard, which fires, so the operation fails either way and WILL_FAIL is a claim about the operation rather than the site, which is how join propagates it and how oracle_common.compare scores it. A new additive derived boolean reachability_clear (not has_return_before and not enclosed_by_try_or_with and not has_break_continue_before, absent means None means fail-closed) carries the clause to the evaluator, whose k_reachability_clear T31 shipped with every production caller passing None. AC-15.10's floor is RETAINED and re-measured; AC-15.6 gains four fixtures (earlier conditional raise allows WILL_FAIL, earlier conditional return blocks, enclosing try or with blocks, absent field blocks). A new task row T36 (~80 LOC, Sonnet, depends on T32) derives, regenerates, wires and re-runs p1 plus tier 1 plus non-regression; AC-15.6 moves off T31's gate cell and AC-15.10 off T32's onto T36's, so every AC stays gated exactly once. Section 15.15 is filled for T35/T31/T32 and section 15.16.3 is added: R1 the clause-(5) refinement, R2 T31's three narrower-than-spec implementation choices recorded as deviations rather than spec changes (E-CALL(5) via the beta mechanism only; E-TYPE's class_hierarchy None in production so the T clause is exact-name equality; E-UNCOND way (3) unsatisfiable for an InlinedGuard, which has no for_span field), R3 O1 found unwired in oracle_replay.main and enabled there with zero measured effect. Section 15.10 additionally publishes the measured static-vs-evaluator agreement, 254/544 at 46.7 percent with 2 of 10 methods exact, and fixes the T30/T35 structural classifier's status as a prediction instrument only."
status: implemented-round-2
spec_version: 20
amends: 260901_plr-sema-pre-corpus-spec.md
task_id: 260904_sema-predicates
date: '260904'
confidence: medium
sources: "Round-1 adversarial reports read in full and dispositioned in section 15.16: .praxia/docs/audits/260904_plr-sema-predicate-round1-challenger.md (C1-C18), .praxia/docs/audits/260904_plr-sema-predicate-round1-defender.md (adjudications, three defender-identified gaps D1-D3, the eighteen-item ordered remediation list, the four user decisions, the revised gate prediction). Sprint plan read in full: .praxia/docs/plans/260904_plr-sema-sprint127-predicates.md (sections 0, 2, 3, 5; the gate at 97-110, the decision hooks at 112-140, the baselines at 144-151). Instrument RE-RUN and re-read after the band-B0 row_id fix (commit ca756bce): outputs/plr-sema/unknown_ledger_260904_before.json (header 2-20, baseline_comparison 21-28, totals 29-37, the 54 clusters 38-2161 incl. :375 at 39-85, :383 at 86-132, :409 at 133-140, :116 at 406-445, :117 at 446-486, :2092 at 763-774, the unresolved_delegate cluster at 1123-1134, per_op_reason_set_histogram 2162-2183, n_row_id_collisions/collision_ops 2184-2273, consistency 3243-3263, notes 3264-3271); its producer plr-sema/eval/unknown_ledger.py:122-172,175-203,221-234,249-270,284-303,332-407,505-557. Specs: .praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md sections 3.1-3.4 (510-699), 4.1 (757-791), 7.2 (1481-1512), 8.1 (2078-2117), 9.4 (2412-2456), Open decisions 2 (95-105, 3320-3342), Deferred table (2505-2534); .praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md sections 10.2.3 (269-291), 10.3.1-10.3.3 (505-613), 10.4 (617-634), 10.6.3 (744-767), 10.6.4 (769-810), 10.8 (988-1077); .praxia/docs/specs/260903_plr-sema-volume-increment.md sections 14.0 (38-79), 14.0.1 (80-174), 14.0.2 (176), 14.5 (466-598), 14.6 (602-741), 14.7 (745-757), 14.11 (900-969), 14.12 (973-1117), 14.13 (1121-1148), 14.14 (1152-1188), 14.15 (1192-1218), 14.16 (1222-1261), 14.17 (1265-1288). Analyzer source re-read and re-anchored this pass, every citation below verified against the file: plr-sema/src/plr_sema/derive/__init__.py:446-449,452-478,499-503,513-538; plr-sema/src/plr_sema/derive/receiver_state.py:900-934,937-965,2056-2094; plr-sema/src/plr_sema/check/__init__.py:50-69,291-313; plr-sema/src/plr_sema/verdict.py:118-168; plr-sema/src/plr_sema/_hand_maintained.py:43,613-631,841-896,897-953,957-961; plr-sema/src/plr_sema/check/ir.py:178-192,194-204,686-701,750-781,796-808,918-953; plr-sema/src/plr_sema/check/volumestate.py:108-131,143-205,401-433,436-469; plr-sema/src/plr_sema/check/tipstate.py:245-270,355-401,404-439,442-452,551-565. Survey: scripts/survey_plr_preconditions.py:140-146,154-171,177-189,191-209,211-229,231-254,256-258. Harness: plr-sema/eval/oracle_common.py:166-203,225-232,235-248,251-274,277-308,336-373,397-410,413-442,476-496,524-577,586-624,632-652. Verifier and the exception taxonomy the round-1 fence argument turns on: training/verify/verifier.py:138-151; training/verify/data/plr_exception_taxonomy.json:1-29. Lint: plr-sema/scripts/check_spec_citations.py:105-157,160-213; plr-sema/scripts/check_spec_crossrefs.py:52-62,102-156; plr-sema/tests/test_spec_lint.py:28-37,212-255. PLR at submodule pin dd79c4c89: external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:106-120,187-197,315-321,348-389,403-409,488-524,540-576,643-668,812-825,869-875,950-1011,1145-1181,1269-1279,1328-1345,1755-1773,1798-1811; external/pylabrobot/pylabrobot/resources/volume_tracker.py:86-109; external/pylabrobot/pylabrobot/resources/trash.py:1-8. AMENDMENT-PASS (round 2, spec_version 19) sources, each read at the cited line this pass: the challenger report .praxia/docs/audits/260907_plr-sema-predicate-amendment-challenger.md (A-C1-A-C13, verdict needs_revision, revise-and-advance), dispositioned in section 15.16.2; plr-sema/src/plr_sema/derive/predicate_ast.py read in FULL (the four citations previously anchored by memory are re-anchored against it: Term/Predicate unions at :195,:291, _CMP_OPS at :298-305, _parse_term at :518-539, _parse_filtered's identity check at :542-558, contains_opaque at :566-593, to_json/from_json at :601-679, _TERM_KINDS/_PREDICATE_KINDS at :637-638); plr-sema/src/plr_sema/derive/__init__.py:454-505 (InlinedGuard's NINE fields at :491-499, is_dynamic_raise at :501-505) and :541-545 (function_index); plr-sema/src/plr_sema/derive/bindings.py:150-182 (free_var_names) and :460-472 (compute_local_bindings_for_guard); plr-sema/src/plr_sema/derive/receiver_state.py:1275-1308 (build_plr_function_index, the (module, qualname, lineno) map the G7 shape-(2) index test reads); scripts/survey_plr_preconditions.py:111-128 (FunctionPreconditions.class_name/params/delegates_to); plr-sema/src/plr_sema/_hand_maintained.py:300-351 (_measure_hm25's import-the-symbols measure and its return of len(shape_matchers)+len(productions)) and :897-953 (HM-25's what/declared/measure, incl. P3a at :904-906 and P8 at :918-920); plr-sema/scripts/check_spec_crossrefs.py:52-62 (TASK_ROW_RE at :58, whose [a-z]? suffix is on the #\\d+ alternative only); plr-sema/eval/t30_measure.py:19-38 (the landed population fix-up sourcing the executed set from oracle_replay.main itself), :550 (collect_executed_population), :802-815 (_effective_unparsed -- the shipped alpha-substituted walk), :818-866 (classify_guard_structural and its K_params test); outputs/plr-sema/t30_measured_260907.json:505-532 (the pick_up_tips :502/:514/:522 clusters) and its ten self.-rooted conditions at :515,:575,:615,:625,:645,:655,:735,:805,:875,:925; PLR at pin dd79c4c89: external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:405-409, :500-517, :1684-1693 (_check_96_head_fits_in_container's pure-arithmetic body), :1775-1780 and :1937-1941 (its two call sites and their raises), and :521/:665/:980 (the three _make_sure_channels_exist call sites, which is why :409 reaches pick_up_tips/drop_tips/aspirate and NOT dispense); external/pylabrobot/pylabrobot/storage/inheco/incubator_shaker_backend.py:416 (_is_error_tail) and external/pylabrobot/pylabrobot/storage/incubator.py:87 (_find_available_sites_sorted), both class methods and therefore both in the function index the shape-(2) test reads. BAND-C / REFINEMENT-PASS (spec_version 20) sources, each read this pass: outputs/plr-sema/t30_measured_260908.json (T35's GO, the EnvRef/Zip/membership whole-table counts, the re-prediction match); outputs/plr-sema/oracle_replay_260908_inc6.json (n_findings_decided 1,563 at :20 and :109 with its per-site breakdown at :110, the crosscheck block at :101, guard_predicate_unparsed 495 at :128, rows_excused_by_scope at :134, the per-op reason-set histogram at :148-196); outputs/plr-sema/unknown_ledger_260908_after.json (consistency.ok, the cluster and finding deltas, pick_up_tips' residual); outputs/plr-sema/predicate_mutants_260908_inc6.json (p1a at :4-18, p1b at :21-35, p1c at :38-52, and the two floor-FAILED notes at :57-58 -- the measurement R1 diagnoses); the non-regression set outputs/plr-sema/tip_mutants_260908_inc6.json, outputs/plr-sema/volume_mutants_260908_inc6.json and outputs/plr-sema/tier2b_260908_inc6.json. PLR re-read at the pin for the refinement: external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:488-524 (pick_up_tips' body -- the conditional raise TypeError at :498 followed by the depth-0 empty-trail asserts at :502 and :522, which is the shape C1's remedy blocked and R1 unblocks) and :438 (the def whose span encloses them). The two lint scripts re-read for the AC-gating move: plr-sema/scripts/check_spec_crossrefs.py:102-156 (TASK_ROW_RE at :58, the gate cell is cells[3] at :143-147, ac_multiply_gated/ac_ungated at :148-156) and plr-sema/scripts/check_spec_citations.py:105-213 (the resolver, the range check at :197-200 and the co-named-identifier rule at :160-212). Band C's evaluator, oracle and derive code are cited BY SYMBOL rather than by line throughout the spec_version 20 additions, because a fixer was editing them concurrently with this pass."
---

# Increment 6: the predicate language

> **This document amends `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` by reference** and
> adds §15 to that document's numbering, exactly as increment 5 adds §14. It takes the deferred row
> (c) — *"the predicate language turning guard `condition` + `mentions_params` into a checkable
> predicate"* (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2518`) — and executes the two
> boundary rows the main spec pre-declared for it: `InlinedGuard` gains a parsed `predicate` field
> interpreted according to `kind`'s polarity with `condition` retained as source of truth
> (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2532`), and §8.1's string-mention bridge is
> "replaced wholesale by real predicate comparison"
> (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2534`).
>
> **What this increment ships, stated as narrowly as the ledger and round 1 together force:**
> *per-finding `SAFE` on real executed operations, a `WILL_FAIL` on a syntactically decidable violation
> that is also established reachable, and a residual that names which observation is missing.*
> **Not a joined `SAFE` on a real operation.** §15.5 is the whole argument for that last sentence, and
> it is the document's central finding: the sprint plan's headline target is unreachable in this
> increment for a reason that has nothing to do with the grammar.
>
> **This is the round-1-revised text as AMENDED on 260907, then REVISED by the amendment's own short
> adversarial pass (spec_version 19, `status: reviewed-round-2`).** That pass filed A-C1–A-C13 (three
> blockers, five must-fix, three should-fix, two notes;
> `.praxia/docs/audits/260907_plr-sema-predicate-amendment-challenger.md`), returned `needs_revision`
> as a **revise-and-advance** — *no objection changes the GO prediction for `pick_up_tips`* — and found
> the amendment **not** gaming the gate while finding its anti-gaming *argument* unsound as written.
> §15.16.2 records the disposition of each objection. Band B landed T30a/T30b and the
> reason-based gate measured **NO-GO** (§15.15's T30 row). The user then took all five open decisions
> at once (`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:262-265`): **(1) HM-25
> `declared` 8 → 9 for α+β — APPROVED** (§15.8, AC-15.7 asserts 9); **(2) the headline substitution —
> APPROVED** (§15.5); **(3) γ NOT adopted — CONFIRMED** (§15.13, §15.14 Q3); **(4) `REASON_VOCABULARY`
> 10 → 12 of cap 12 — APPROVED** (§15.7); and **(5) the `EnvRef` grammar amendment — APPROVED**, which
> is what spec_version 18 carries.
>
> **spec_version 20 (260908) is a POST-ROUND REFINEMENT and has NOT been adversarially reviewed.**
> `status` stays `reviewed-round-2` for that reason: rounds 1 and 2 attacked spec_version 16 and 18,
> and nothing added at 20 has been attacked by anyone. Band C landed **T35 (GATE: GO — `pick_up_tips`
> 223/223, residual {`decidable`, `guard_env_dependent`}, every cell of §15.9's re-prediction table
> matched exactly)**, **T31** (the evaluator; `REASON_VOCABULARY` 12/12, HM-25 `declared` 9,
> `live_rows()` 24) and **T32** (tier 1 at **0 unsound**, crosscheck 191/191, `n_findings_decided`
> **1,563** against a floor of 223, `guard_predicate_unparsed` 5,656 → **495**, `unknown_rate` still
> 1.0 exactly as §15.5 predicted). **One acceptance criterion failed — AC-15.10's mutant floor, at 0
> achieved on all three mutators — and the cause was E-UNCOND(5), a clause this document wrote in round
> 1.** §15.4's clause (5) is **refined** here: an earlier `ast.Raise` no longer blocks a depth-0
> empty-trail guard, because if it fires the operation fails there and if it does not, control reaches
> the guard, which fires — the operation fails either way, and `WILL_FAIL` is a claim about the
> *operation*, not the site. A new additive derived boolean `reachability_clear` carries the surviving
> clauses to the evaluator, fail-closed on absence, and **T36** derives, wires and re-measures against
> the unchanged floor. §15.16.3 records this (R1) beside two things that are **not** spec changes:
> T31's three narrower-than-spec implementation choices (R2) and O1's wiring into the replay (R3).
> **The refinement widens what may emit `WILL_FAIL`** — the one direction in this document that can
> produce a false positive on a clean operation, and the direction round 1 filed six blockers about —
> so it is named here as the first candidate for the next adversarial pass.
>
> **One item is nevertheless owed back to the user, and round 2 is where that is said (A-C7).** The
> option put for decision 5 named **two** productions — *"an `EnvRef` leaf for an expression rooted at
> `self.` … plus `zip(<Term>, <Term>)` as a `Term` for `AllOf`/`AnyOf`"*
> (`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:252-260`). The **third**, widening
> `_CMP_OPS` with `in`/`not in`, was not named there, and it is load-bearing for the gate: without it
> `c not in self.head` is `Opaque` regardless of `EnvRef` and `:409` does not flip. It is recorded as
> an amendment-scope item in §15.16.1 A3, marked **in scope of decision 5 by necessity** — it is the
> comparator that makes `:409`'s filter readable at all — **to be confirmed with the user at sprint
> close**. So: nothing in this document is pending a *new* decision, and exactly one production is
> pending *confirmation* that it fell inside an approved one.
>
> **The amendment in one paragraph.** The two guards that held `pick_up_tips` back are both
> expressions **rooted at the literal name `self`** — `c not in self.head` inside `:409`'s bound
> comprehension and `self.backend.can_pick_up_tip(channel, tip)` under a `zip(...)` at `:514`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:405-409`, `:506-514`) — i.e. the
> receiver's own head and backend, **tier (ii) by §15.1's definition**, which the grammar had no
> production for and therefore charged to `guard_predicate_unparsed`, the reason reserved for *"the
> grammar failed here"*. §15.2 G7/G8 add three productions — `EnvRef`, `Zip`, and the membership
> comparators — that **recognise** an environment read without deciding one (§15.4 E-ENV: ½ as a
> predicate, ⊤ as a term, unconditionally, in this increment), and §15.7 assigns them
> `guard_env_dependent`. **The amendment cannot decide anything new by itself** (§15.9's anti-gaming
> box); what it changes is which of the two existing reasons an already-undecided guard carries, and
> therefore whether the gate can see the difference between a coverage gap and a missing observation.
>
> **Round 1 filed eighteen items; §15.16 records
> the disposition of each C1–C18 and D1–D3. Four of them changed what the increment ships, not merely
> how it is worded: the soundness fence is left **unmodified** (§15.5), tier (iii) emits an `UNKNOWN`
> `Finding` rather than none (§15.5), the GO gate is stated over **reasons** rather than over tiers
> (§15.9), and no guard at `depth >= 1` may emit `WILL_FAIL` at all (§15.4 E-UNCOND(4)).
>
> **Registry arithmetic this increment carries, with the one spend it now proposes.**
> `REASON_VOCABULARY` **10 → 12 of cap 12** (`plr-sema/src/plr_sema/_hand_maintained.py:650-667`,
> HM-14 `declared=12`), which **exhausts HM-14's headroom** — **approved 260907**
> (§15.14 Q4; the one-member fallback in §15.7 is dead). No registry **row** is added; `live_rows()` stays 24
> against `BUDGET_CAP = 24` (`plr-sema/src/plr_sema/_hand_maintained.py:43`). §15.8's draft position
> that **neither** HM-24 nor HM-25 should be spent **did not survive round 1**: α and β are filed on
> **HM-25, `declared` 8 → 9** — **approved 260907**, exactly as increment 5
> carried "HM-24 1 → 2 planned" before the user approved 1 → 3. **The 260907 grammar amendment adds
> nothing to this arithmetic**: no row, no ceiling, no vocabulary member (§15.8).

---

## 15.0 The instrument and the claim

Sprint 123 closed with every oracle tier at 0 unsound and `unknown_rate` 1.0 on all ten methods. Band
B0 built the instrument that says *why*, and it is a stronger instrument than the planning-time probe:
it reuses `run_static_calls` unmodified and reads findings through the `FINDINGS_SINK` seam installed
after relabelling (`plr-sema/eval/oracle_common.py:593-611`), so the numbers are the pipeline's own.

**The numbers, verbatim, from the ledger as re-run after band B0's `row_id` fix.** 544 executed
operations, 544 with `n_ops_unknown` equal to `n_ops_executed` (`outputs/plr-sema/unknown_ledger_260904_before.json:29-37`); 6,036 findings,
of which `guard_predicate_unparsed` 5,656 / `volume_state_unknown` 194 / `unresolved_delegate` 186;
**54 clusters** keyed on `(reason, PLR site, condition text)`.

> **Round-1 correction (C12 / item 17, landed as `ca756bce` before this revision).** Every per-op set
> in the ledger is now keyed by the **positional** `(row_idx, op_id)` pair, never by `(row_id, op_id)`
> (`plr-sema/eval/unknown_ledger.py:133-155`, whose docstring states the rule and its reason).
> `row_id` is a content digest that collides across a documented ~4% of corpus rows, so the pre-fix
> ledger silently merged two different ops from two different rows into one `ops_blocked` entry.
> **Three published numbers moved as a result**: the `unresolved_delegate` cluster's `n_ops_blocked`
> 81 → **93**, `liquid_handler.py:375`'s and `:383`'s 532 → **544**, and `:2092`'s 81 → **93**. The
> ledger now publishes a `consistency` block reporting `"ok": true` with an empty `violations` list
> and three independent invariants checked
> (`outputs/plr-sema/unknown_ledger_260904_before.json:3243-3263`;
> `plr-sema/eval/unknown_ledger.py:332-407` defines them), plus `n_row_id_collisions` **12** and a
> `collision_ops` section naming every one of the twelve
> (`outputs/plr-sema/unknown_ledger_260904_before.json:2184-2273`). All twelve are `move_*`
> (`move_plate` 7, `move_lid` 3, `move_resource` 2), each carrying the reason set exactly
> `{guard_predicate_unparsed, unresolved_delegate}` and 13 distinct guard sites — `_check_args`'s
> `:375` and `:383` among them
> (`outputs/plr-sema/unknown_ledger_260904_before.json:2216-2230`). **So the challenger's "12
> unaccounted operations" do not exist**: they were duplicate `move_*` occurrences the pre-fix set
> keying folded away, and they are inside the 93 the histogram always reported. §15.14 Q1's stated
> refutation criterion is answered below.

**Three reason-set combinations, not two** (`outputs/plr-sema/unknown_ledger_260904_before.json:2162-2183`):

| per-op reason set | ops | note |
|---|---|---|
| `{guard_predicate_unparsed}` | 334 | `pick_up_tips`, `drop_tips`, `discard_tips`, `stamp`, and the tip half of the mixed rows |
| `{guard_predicate_unparsed, volume_state_unknown}` | 117 | `aspirate` 77 + `dispense` 40 — the unseeded volume cell |
| `{guard_predicate_unparsed, unresolved_delegate}` | 93 | `move_lid` 31 / `move_plate` 31 / `move_resource` 31 — **deferred row (e)**, `_state_updated` |

**The third combination is out of this increment and can never be a gate candidate.** Its
`unresolved_delegate` cluster is not a guard at all: its `plr_site` is `<none>` and its `condition` is
the bare delegate name `_state_updated`, with `n_findings` 186 over `n_ops_blocked` **93** and a
`per_method` breakdown that now sums to 93
(`outputs/plr-sema/unknown_ledger_260904_before.json:1123-1134`), i.e. the transitive `delegates_to`
closure hit an `unresolved_calls` entry (`plr-sema/src/plr_sema/derive/__init__.py:616-617`). That is
deferred row (e) (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2520`), which no predicate
grammar touches. Every `move_*` operation therefore keeps a residual this increment cannot move, and
`move_resource`/`move_lid`/`move_plate` are excluded from §15.9's candidate list by construction.

**`n_ops_sole_blocker` is 0 for all 54 clusters.** Every cluster in the ledger reports
`"n_ops_sole_blocker": 0` — the largest, `liquid_handler.py:375`'s `len(missing) > 0`, blocks **all
544** ops and is the sole blocker of none
(`outputs/plr-sema/unknown_ledger_260904_before.json:39-57`). **The consequence is normative for how
this increment is measured**: removing any cluster, or any set of clusters short of *all* of an
operation's, moves `unknown_rate` by exactly zero. A metric of the form "clusters removed" or
"findings converted" would show a large number while the analyzer still says nothing about any
program. §15.9's gate is therefore **per-op residual tier composition** (sprint plan
`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:97-110`), and that is the only number in
this document allowed to decide GO.

**Three places the ledger corrects the sprint plan, recorded because a stale premise is how the next
person mis-sizes the work.**

1. **`liquid_handler.py:191`'s `self.setup_finished` guard does not reach real operations.** The plan's
   §0 table carries a `:191 d1 setup` row at count 38 and asks band B0 to explain it
   (`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:63`). The ledger's own `notes` show it
   *cannot* appear: `run_static_calls` computes `setup_pcs` from the bytecode's `origin` sideband and
   filters every setup-pc finding out of `raw_findings` **before** relabelling
   (`plr-sema/eval/oracle_common.py:600-607`), so no setup-pc finding can be relabelled onto a real
   `op_<i>` and the seam never sees one
   (`outputs/plr-sema/unknown_ledger_260904_before.json:1914-1915`). The plan's row was an artifact of
   an ephemeral probe that wrapped `check_ir` directly. **No cluster at `liquid_handler.py:191` exists
   in the ledger, and `LiquidHandler.setup`'s own guard is not in scope for this increment.**
2. **544 executed ops, not 548 — and 544 is now both the occurrence count and the distinct count.**
   `oracle_replay.py`'s own `operations_executed` is 548; the ledger counts 544 **positional**
   `(row_idx, op_id)` pairs carrying ≥ 1 real finding. The four-op gap is ops that received a synthetic
   zero-finding placeholder rather than a `check_ir` result, which carry no reason to cluster
   (`outputs/plr-sema/unknown_ledger_260904_before.json:3266`). *The draft called 544 "distinct
   `(row_id, op_id)` pairs"; under the old keying that phrase named a smaller population than the
   counter actually held, which is precisely C12's complaint.* Under positional keying the two
   coincide: `n_ops_executed` increments once per `(row_idx, op_id)` and the key is unique by
   construction, asserted in the clustering loop itself
   (`plr-sema/eval/unknown_ledger.py:226-235`). The ledger's own note 2 text retains the legacy
   "distinct `(row_id, op_id)` pairs" wording (`plr-sema/eval/unknown_ledger.py:507-516`); the value it
   reports is correct and this document, not the note string, is the place the distinction is stated.
   Every ratio in this document uses 544.
3. **Two reason-set combinations were planned; there are three.** The plan's §0 probe found
   `{guard_predicate_unparsed}` and `{guard_predicate_unparsed, volume_state_unknown}`
   (`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:42-43`); the full-benchmark ledger adds
   the `unresolved_delegate` combination, which is 93 ops — 17% of the benchmark — permanently outside
   this increment.

**The coupling claim is now confirmed per operation, not merely per method.** §15.5's argument used to
rest on a per-method reading of the clusters, which C12 correctly objected could not see an individual
operation. Under the corrected keying it can: `liquid_handler.py:375` and `:383` each report
`n_findings` 544 over `n_ops_blocked` 544 with a `per_method` breakdown summing to 544
(`outputs/plr-sema/unknown_ledger_260904_before.json:39-57`, `:86-104`), and the ledger's own
`consistency` invariant 3 asserts `sum(per_method) == n_ops_blocked` for **every** cluster
(`plr-sema/eval/unknown_ledger.py:353-356`, result at
`outputs/plr-sema/unknown_ledger_260904_before.json:3244-3245`). So **every one of the 544 executed
operations carries both `_check_args` guards**, both of which are tier (ii). §15.14 Q1's refutation
criterion — *"name one executed operation whose non-(iii) residual is empty"* — is therefore answered
in the negative by measurement rather than by argument: there is no such operation.

**The claim, stated as narrowly as increment 5 stated its own — and the user approved this narrowing
on 260907** (§15.5's decision box, §15.14 Q7;
`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:262-265`). A joined `SAFE` on a real operation
would claim that operation cannot fail. This increment **does not produce one** (§15.5), and the
narrow claim it does support is: *for a guard whose condition parses to a non-`Opaque` predicate and
whose every operand resolves from the IR call, the analyzer states whether that guard fires, and when
it says `SAFE` the claim is "this PLR precondition does not hold against this call", nothing more.*
Everything wider — that the operation succeeds, that the backend accepts it, that the deck contains
the resource — is out of scope and is named as such, per finding, by §15.7's reasons.

---

## 15.1 The three decidability tiers

> **Normative (the tiers).** Every guard reachable from an executed operation is assigned exactly one
> tier, and the assignment is a property of *what would decide the guard*, not of whether this
> increment decides it.
>
> **(i) syntactic.** Decided from the call's literal kwargs, the resolved contract's parameter
> defaults, and `RESOURCE` operands as declared in the IR (`type`, `element_type`, `grid` —
> `plr-sema/src/plr_sema/check/ir.py:178-192`). No hypothesis, no observation.
>
> **(ii) environment / observation.** Requires state outside the extracted graph: a process-global
> (`get_strictness()`, the `does_volume_tracking()` shape increment 5 already models as an `env`
> member, §14.6), the backend class and its method signatures, the deck (membership, lid topology, head
> channel count), or a container's seeded contents. Decidable only under a recorded hypothesis or an
> observation returned from the executed window.
>
> **(iii) opaque.** The backend's own raise, re-raised. `error is not None` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:575-576` and its three siblings.
> Never decided from the PLR layer, under any observation this analyzer can take.

> **Normative (tier (iii) is DERIVED, at zero registry cost — round 1, C8).** A guard is tier (iii)
> **iff** `guard.is_dynamic_raise` — the shipped property that tests `raises.startswith("<dynamic:")`
> (`plr-sema/src/plr_sema/derive/__init__.py:516-520` — re-anchored in round 2, A-C11; the property
> moved when `bindings` was added), which the survey sets for a
> `raise <ast.Name>`, i.e. a re-raise of a locally-bound exception name
> (`scripts/survey_plr_preconditions.py:231-240`). **No site list, no `condition` text match, no new
> pattern, no registry row.** At this pin the rule selects exactly seven sites in
> `liquid_handler.py` — `:576`, `:726`, `:1067`, `:1271`, `:1510`, `:1590`, `:2092` — which is the
> population §15.1's tables name plus `:2092`, the one a syntactic `condition == "error is not None"`
> rule would have missed (`:2092`'s condition is `<unconditional>`,
> `outputs/plr-sema/unknown_ledger_260904_before.json:763-774`).
>
> **Tiers (i) and (ii) are NOT derived and are not the gate.** The draft's implicit assumption — that
> the evaluator could recognise a tier at measurement time — is withdrawn. A derived (i)/(ii) split of
> the form *"decides ⇒ (i), else (ii)"* would make §15.9's GO condition true by construction, which is
> the opposite of what §15.9 says it is for. **§15.1's (i)/(ii) tiering below is therefore this
> document's PREDICTION only**; the gate is restated over reasons in §15.9, and T30's measured block
> (3) publishes the reason each cluster actually carries so prediction and measurement can diverge
> visibly.

**The tiering of every cluster in the ledger.** Conditions are quoted verbatim from the ledger; local
bindings are quoted from PLR at pin `dd79c4c89`. "grammar" = decidable by §15.2 alone; "α"/"β" = needs
that §15.3 idiom; "O1" = needs §15.4's operand observation. **Every (i)/(ii) cell is a prediction to be
falsified by T30, per the box above.**

### 15.1.1 The `pick_up_tips` closure — the gate candidate

| PLR site | condition (verbatim) | local binding | tier | needs |
|---|---|---|---|---|
| `liquid_handler.py:498` | `len(not_tip_spots) > 0` | `not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, TipSpot)]` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:496`) | (i) | α + O1 |
| `liquid_handler.py:502` | `len(set(use_channels)) == len(use_channels)` | `use_channels = use_channels or self._default_use_channels or list(range(len(tip_spots)))` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:501`) | (i) | grammar + P3a |
| `liquid_handler.py:522` | `len(tip_spots) == len(offsets) == len(use_channels)` | `offsets = offsets or [Coordinate.zero()] * len(tip_spots)` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:517`) | (i) | β + P3a |
| `liquid_handler.py:514` | `not all((self.backend.can_pick_up_tip(channel, tip) for channel, tip in zip(use_channels, tips)))` | — | (ii) backend | — |
| `liquid_handler.py:375` | `len(missing) > 0` | `missing = non_default - backend_kws` over `inspect.signature(method)` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:353-373`) | (ii) backend signature | — |
| `liquid_handler.py:383` | `strictness == Strictness.STRICT` | under `if len(extra) > 0 and len(vars_keyword) == 0:` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:381`) | (ii) env **and** backend | — |
| `liquid_handler.py:409` | `not len(invalid_channels) == 0` | `invalid_channels = [c for c in channels if c not in self.head]` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:407`) | (ii) head channel count | — |
| `liquid_handler.py:321` | `not resource_from_deck == resource` | `resource_from_deck = self.deck.get_resource(resource.name)` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:318`) | (ii) deck membership | — |
| `liquid_handler.py:576` | `error is not None` | `error` rebound in an `except` handler (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:551-555`) | **(iii)** | — |
| `liquid_handler.py:535` | *(tip typestate; decided since increment 1, `SAFE`/`WILL_FAIL`/`channel_state_unknown`)* | — | decided | — |

`pick_up_tips` carries ten guards and zero gaps at this pin; nine appear in the ledger (223 findings
each, e.g. `:498`'s cluster at `outputs/plr-sema/unknown_ledger_260904_before.json:217-227`) and the
tenth is already evaluated. **Its predicted residual after §15.2–§15.4 is `{guard_env_dependent}`
alone** — no `guard_predicate_unparsed`, no `guard_operand_unknown` — which is §15.9's restated GO
condition.

> **Measured, then amended (260907).** T30 falsified that prediction: `:409` and `:514` carried
> `guard_predicate_unparsed`, because their conditions read the receiver's head and backend through
> shapes the grammar had no production for — `c not in self.head` and a `zip(...)` over
> `self.backend.can_pick_up_tip(channel, tip)`. **Note that this table already tiered both (ii)**, so
> the failure was never in the tiering; it was that a tier-(ii) *read* and a grammar *gap* were
> indistinguishable in the reason vocabulary's output. §15.2 G7/G8 make them distinguishable and
> §15.9's re-prediction table restores this row's `{guard_env_dependent}` — as a prediction for **T35**
> to falsify in turn, not as a restatement of the one that already failed. Note that all three of the guards the gate rests on (`:498`, `:502`, `:522`) sit at
`depth == 0` in `pick_up_tips`'s own body
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:488-524`), so E-UNCOND(4)'s new
`depth >= 1` forbiddance does not reach them; the five depth-1 guards (`:375`, `:383`, `:409`, `:321`
and, at depth 0 but backend-dependent, `:514`) were already predicted `guard_env_dependent`.

### 15.1.2 The `drop_tips` / `discard_tips` closure — *not* a candidate, and why

| PLR site | condition | local binding | tier | needs |
|---|---|---|---|---|
| `liquid_handler.py:647` | `len(not_tip_spots) > 0` | `not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, (TipSpot, Trash))]` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:645`) | (i) | α (tuple form) + O1 |
| `liquid_handler.py:651` | `len(set(use_channels)) == len(use_channels)` | as `:501` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:650`) | (i) | grammar + P3a |
| `liquid_handler.py:657` | `tip.tracker.get_used_volume() > 0 and (not allow_nonzero_volume)` | `tip = self.head[channel].get_tip()` inside `for channel in use_channels:` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:654-655`) | **½ by decision** | — |
| `liquid_handler.py:666` | `len(tip_spots) == len(offsets) == len(use_channels) == len(tips)` | `tips = []` then `tips.append(tip)` in a loop (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:653-658`) | (i) **unbindable** | — |
| `liquid_handler.py:726` | `error is not None` | — | (iii) | — |
| `:375` / `:383` / `:409` / `:321` | as §15.1.1 | — | (ii) | — |

**Two obstructions, both disclosed rather than discovered at gate time.** `:657` is a compound
condition whose left conjunct is a numeric `Cmp` over a tip's used volume; main spec Open decision 2
and increment 5 §14.14 item 1 keep every numeric `Cmp` outside the `volume_guards` bridge at ½, and
this guard is not a `volume_guards` entry (it calls no tracker mutator). It stays ½ and this increment
does not reopen that. `:666` binds `tips` by an **append inside a loop**, which is neither §15.3
idiom; it fails closed. `drop_tips`/`discard_tips` therefore keep a `guard_predicate_unparsed`
residual and are **not** gate candidates. `discard_tips` additionally carries `n == 0` at `:822`
(`outputs/plr-sema/unknown_ledger_260904_before.json:1593`) whose `n = len(use_channels)` at
`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:819` sits after a conditional
rebinding of `use_channels` at `:816-817` — excluded by §15.3's rebinding clause.

**Round-1 correction to this table (C4).** `:647`'s `not_tip_spots` comprehension tests
`isinstance(ts, (TipSpot, Trash))`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:645-647`). Under the **draft's**
E-TYPE, an element whose declared name is `"Container"` — which is what O1 records for a `Trash`,
since `Trash` is not in `_PLR_GENERIC_RESOURCE_NAMES` and `Container` is
(`plr-sema/eval/oracle_common.py:225-232`; `external/pylabrobot/pylabrobot/resources/trash.py:4`) —
would have evaluated `F`, making `Not(...)` `T`, `AnyOf` `T`, and the guard fire: **a false
`WILL_FAIL` on the 65 `drop_tips`/`discard_tips` operations that ran clean.** §15.4's restated E-TYPE
makes it `½` instead. This row is not a gate candidate either way; it is recorded because it was one
of round 1's two live false-`WILL_FAIL` mechanisms.

### 15.1.3 The `aspirate` / `dispense` / `transfer` closure

| PLR site | condition | tier | needs |
|---|---|---|---|
| `liquid_handler.py:959`, `:1153` | `len(set(use_channels)) == len(use_channels)` | (i) | grammar + P3a |
| `liquid_handler.py:990`, `:1202` | `len(p) != len(use_channels)` — `p` is the target of `for n, p in [("resources", resources), …]` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:981-989`) | (i) **unbindable** | γ (§15.13) |
| `liquid_handler.py:875` | `len(not_containers) > 0`, `not_containers = [r for r in resources if not isinstance(r, Container)]` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:873-875`) | (i) | α + O1 |
| `liquid_handler.py:1185`, `:1188` | `self._blow_out_air_volume is None`; `requested_bav is not None and done_bav is not None and (requested_bav > done_bav)` — both under `if any(bav is not None and bav != 0.0 for bav in blow_out_air_volume)` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1179-1188`) | **do NOT clear** (round 1, C6) | — |
| `liquid_handler.py:116` | `lidded is resource` — `lidded = _lidded_ancestor(resource)` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:112`) | (ii) lid topology | — |
| `liquid_handler.py:117` | `<unconditional>` — **retiered in round 1 (C8)**: it has no operands at all, so `parse(None) = TRUE` makes it `T`, not ½, and tiering it "(ii) lid topology" mis-stated why it is undecided | **reachability-blocked** | disposed by E-UNCOND(5) ⇒ `UNKNOWN`/`guard_env_dependent` |
| `liquid_handler.py:1067`, `:1271` | `error is not None` | (iii) | — |
| `volume_tracker.py:92`, `:105` | `volume - self.get_used_volume() > 1e-06`; `volume - self.get_free_volume() > 1e-06` (`external/pylabrobot/pylabrobot/resources/volume_tracker.py:91,104`) | **already evaluated by increment 5**; residual is `volume_state_unknown` = an unseeded cell at `TOP` | (ii) observation |
| `liquid_handler.py:1335`, `:1337`, `:1340` | `ratios is not None`; `source_vol is not None`; `source_vol is None` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1333-1340`) | (i) | grammar alone |
| `:375` / `:383` / `:409` | as §15.1.1 | (ii) | — |

**Withdrawn in round 1: `:1185`/`:1188` were the draft's "cleanest result" and they do not clear.**
The draft argued that `blow_out_air_volume` defaults to `[None] * len(use_channels)` at
`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1159`, so the enclosing
`any(bav is not None and bav != 0.0 for bav in blow_out_air_volume)` at `:1183` is **F**, the guards
are unreachable, and E-SCOPE returns `SAFE`. **Two independent defects kill it, and the paragraph is
deleted rather than softened.** (1) β binds **only a length** (§15.3), and the `any(...)` scope entry
needs the *elements*; E-SCOPE gets ½, not `F`. (2) Even an element-binding extension of β would die at
`:1165`, where `blow_out_air_volume` is rebound by a comprehension that preserves the length but not,
syntactically, the elements. §15.9's `dispense` row is corrected to match. The two volume clusters
`volume_tracker.py:92`/`:105`
(`outputs/plr-sema/unknown_ledger_260904_before.json:1165`, `:529`) remain **not** this increment's
business: increment 5 already evaluates them and their residual is an unseeded cell, not an unparsed
predicate.

**Round-1 correction to `:875` (C4b + item 13).** The draft predicted `_check_containers`'s
`len(not_containers) > 0` at
`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:871-875` would clear. It does not,
for a reason the restated E-TYPE alone would have fixed but the depth rule does not: a `Well`'s
declared name is `"Well"`, `Well` **is** a subclass of `Container`, and under §15.4's restated E-TYPE
that is now `T` ⇒ the guard is `SAFE` — **but the guard sits at `depth == 1`** inside a delegate
called positionally at `:956`, and §15.4's E-CALL(depth) forbids resolving its free names against the
entry point's `call.kwargs`. So `resources` is ⊤ and the guard is `½`/`guard_env_dependent`. Both
facts are recorded because they are separable: option (b) of §15.4's substitution disposition would
make it clear, at ~90 LOC that this increment does not spend.

**Round-1 addition (D1): `:1335`/`:1337`/`:1340` need `param_defaults`, which does not exist today.**
The draft tiered them "(i) grammar alone". `target_vols` is absent from `call.kwargs` for every
planned `transfer`, and the contract table records no parameter defaults at all — grep over
`plr-sema/data/derived_contracts.json` for `"defaults"`, `"param_defaults"` and `"signature"` returns
zero matches, and the derive package extracts none. Without a default the term is ⊤, the enclosing
`if target_vols is not None:` at `:1333` is ½, and all three guards are ½. §15.4's E-CALL(2) is
restated over a new derived `param_defaults` field, which restores them; `transfer`'s three
parameters are all `ast.Constant` `None` defaults at
`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1277-1279`.

### 15.1.4 The two families that stay out

- **The `move_*` family** — eleven clusters at `liquid_handler.py:2055`–`:2290`
  (`outputs/plr-sema/unknown_ledger_260904_before.json:685-1122`), all inside `pick_up_resource` /
  `move_picked_up_resource` / `drop_resource`. Their conditions divide into instance-state tests
  (`self.setup_finished and (not self._resource_pickups)`, `self._resource_pickup is not None`,
  `self._resource_pickup is None`) — tier (ii), receiver state the graph does not carry —
  destination-topology tests (`destination.direction == 'z'`,
  `resource_rotation_wrt_destination % 180 != 0`,
  `destination.resource is not None and destination.resource is not resource`,
  `not isinstance(resource, Plate)`,
  `isinstance(destination, ResourceStack) and destination.direction != 'z'`) — tier (ii), deck
  topology — **and one the draft's seven-condition enumeration omitted: `:2092`'s `<unconditional>`**
  (93 ops, `outputs/plr-sema/unknown_ledger_260904_before.json:763-774`), which is `raise e` in an
  `except` handler and is therefore **derived tier (iii)** by `is_dynamic_raise`, not a topology test
  at all (round 1, C8). Every one of the 93 ops in this family also carries the `unresolved_delegate`
  residual (§15.0), so none can clear regardless.
- **The 96-head / `stamp` family** — ten clusters at `liquid_handler.py:1743`–`:2030`
  (`outputs/plr-sema/unknown_ledger_260904_before.json:1631-2048`), 27 ops. `:1743` and `:1893`
  (`not (isinstance(resource, (Plate, Container)) or (isinstance(resource, list) and all((isinstance(w, Well) for w in resource))))`,
  `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1739-1743`) and `:1807`/`:1963`
  (`not len(containers) == 96`) are tier (i) under §15.2's `isinstance`/`all` productions;
  `:1778`/`:1940` (`not self._check_96_head_fits_in_container(container)`) and `:1804`/`:1960`
  (`well.parent != plate`, `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1801-1804`)
  are tier (ii) topology; `:1770`/`:1920` are `<unconditional>`. The family is **not excluded by rule**
  — its tier-(i) members are in scope for the grammar — but it is not a gate candidate, because
  `containers` is bound by a branch this increment does not model.
  **Round-1 correction (C1):** `:1770`/`:1920` are `<unconditional>` but their `scope_trail` is **not
  empty**. Each sits in the `else:` of a three-branch `if`/`elif`/`elif` chain
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1761-1773`), and `visit_If`
  pushes an `"else of: if …"` entry for every `orelse`
  (`scripts/survey_plr_preconditions.py:200-209`), an `elif` self-nesting to compound both conditions.
  E-UNCOND already blocks those — an `"else of: if …"` entry is recognised **only** by way (1), whose
  negated `isinstance` test never evaluates `T` under the restated E-TYPE. So these 54 ops were never
  in C1's false-`WILL_FAIL` population; the guards that were are `:117` (163 ops) and `:2092` (93).

---

## 15.2 The grammar

> **Normative (G0, the parse is a total function).** `parse : condition -> Predicate` is **total**.
> Every `condition` string produces a `Predicate`; the only escape is `Opaque`, and `Opaque` is a
> constructor of the type, not a failure. `parse(None) = TRUE` — a `None` condition means the guard
> fires unconditionally, which is what `check/__init__.py`'s `"<unconditional>"` sentinel already
> encodes (`plr-sema/src/plr_sema/check/__init__.py:298-312`), and 9 of the shipped table's guards
> carry it. A `SyntaxError` from `ast.parse` yields `Opaque`, as `tipstate._parse_atom` already does
> (`plr-sema/src/plr_sema/check/tipstate.py:393-398`).
>
> **`parse(None) = TRUE` is a statement about the PREDICATE, never about reachability.** A guard whose
> predicate is `TRUE` still has to satisfy E-UNCOND before it may emit `WILL_FAIL`, and round 1 showed
> that the natural reading of the draft's E-UNCOND satisfied it *vacuously* on an empty `scope_trail`
> — which would have produced `WILL_FAIL` on 163 clean `aspirate`/`dispense`/`stamp`/`transfer`
> operations at `:117` and 93 `move_*` operations at `:2092`. §15.4's E-UNCOND(5) closes that, and
> **G0 must not be read as licensing it.**
>
> **`condition` is retained as the source of truth on the wire.** `InlinedGuard` gains `predicate`
> alongside its other fields — **nine in the landed dataclass**, `condition`, `predicate`,
> `scope_trail`, `raises`, `kind`, `free_vars`, `site`, `depth`, `bindings`
> (`plr-sema/src/plr_sema/derive/__init__.py:491-499`; re-anchored in round 2, A-C11 — the pre-T30b
> citation `:452-478` now spans the `@dataclass` decorator and the docstring, not the fields); nothing
> is replaced. This is the boundary the main spec pre-declared
> (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2532`).

> **Normative (G1, the mini-AST).** Over Kleene three-valued logic `{T, F, ½}`:
>
> ```
> Predicate ::= TRUE
>             | Not(Predicate)
>             | And(Predicate, …)          # Kleene: F if any F, T if all T, else ½
>             | Or(Predicate, …)           # Kleene: T if any T, F if all F, else ½
>             | Cmp(Term, op, Term)        # op ∈ {==, !=, <, <=, >, >=, in, not in}, CHAINED allowed
>             | Is(Term, negated)          # `x is None` / `x is not None`
>             | AllOf(Term, Predicate)     # all(<pred> for <v> in <seq>)
>             | AnyOf(Term, Predicate)     # any(<pred> for <v> in <seq>)
>             | IsInstance(Term, (Type, …))
>             | EnvRef(path, args)         # G7 — an environment read, in EITHER position
>             | Opaque
> Term      ::= Len(Term) | SetOf(Term) | Var(name) | Lit(json) | Attr(Term, name)
>             | Filtered(Term, Predicate)  # the comprehension of §15.3(α), as a TERM
>             | Zip(items)                 # G8 — `zip(<Term>, …)`, only as a <seq>
>             | EnvRef(path, args)         # G7 — the same node, in term position
> ```
>
> **Two of these lines were corrected against the shipped module rather than the draft's prose
> (amendment, 260907).** `Is` has exactly two fields, `term` and `negated` — the RHS `None` is a
> *precondition of the production*, not a field
> (`plr-sema/src/plr_sema/derive/predicate_ast.py:251-259`) — and `AllOf`/`AnyOf`'s first field is a
> general `Term`, not a `Var`, because G3 builds one directly out of a `Filtered` term's own `seq`
> (`plr-sema/src/plr_sema/derive/predicate_ast.py:271-289`). The three new lines (`EnvRef`, `Zip`, the
> widened `op` set) are the amendment's whole surface; every other line is unchanged.
>
> **Anything the walk does not recognise is `Opaque`.** `Opaque` evaluates to ½ under every state and
> keeps the guard's existing `guard_predicate_unparsed` reason (§15.7) — so an unrecognised shape is
> **exactly today's behaviour**, per finding, with no new failure mode. This is the fail-closed
> direction and it is why G0 can be total. **A predicate containing an `Opaque` *sub*-node is
> `Opaque` for reason-assignment purposes too** — §15.7's normative nested-`Opaque` rule, added in
> round 1 (C15) so the residual `guard_predicate_unparsed` count remains an honest coverage measure —
> while still being **evaluated** under Kleene, so an `And` with an `F` conjunct still decides.

> **Normative (G7, `EnvRef` — a RECOGNISED environment read; new in the 260907 amendment).** An
> expression **rooted at the literal name `self`** parses to a single leaf
> `EnvRef(path: tuple[str, ...], args: tuple[Term, ...] | None)`, admissible in **both** predicate and
> term position, in exactly two shapes and no others:
>
> 1. **The attribute chain.** An `ast.Attribute` chain whose innermost value is `ast.Name("self")`:
>    `self.head` → `EnvRef(("self", "head"), None)`; `self.backend` → `EnvRef(("self", "backend"),
>    None)`; `self._resource_pickup.direction` → `EnvRef(("self", "_resource_pickup", "direction"),
>    None)`. `args` is `None`, which is what distinguishes a read from a call of no arguments.
> 2. **The call of such a chain, subject to the PLR-layer test below.** An `ast.Call` whose `func` is
>    shape (1) and whose arguments **all parse as `Term`s**, with no `keywords`, no `Starred`, and no
>    argument containing `Var("self")`: `self.backend.can_pick_up_tip(channel, tip)` →
>    `EnvRef(("self", "backend", "can_pick_up_tip"), (Var("channel"), Var("tip")))`. **If any argument
>    fails to parse as a `Term`, the whole call is `Opaque`** — there is no partial admission and no
>    fallback.
>
> > **Normative (the PLR-layer test on shape (2) — new in round 2, A-C1). A `self`-rooted call is
> > admitted as an `EnvRef` only when it is a read THROUGH a receiver attribute, or names a method the
> > closure could not have inlined.** Concretely, a shape-(2) candidate whose `path` is
> > `("self", p₁, …, pₖ)` is admitted **iff**
> >
> > - **`k >= 2`** — i.e. `len(path) >= 3`, the `self.<attr>.<method>(…)` form: `self.backend.can_pick_up_tip(…)`,
> >   `self.deck.get_resource(…)`. The receiver of the call is an attribute of `self`, so the call is a
> >   read of state the PLR layer does not own; **or**
> > - **`k == 1`** — the `self.<name>(…)` form — **and `<name>` is ABSENT from the derive package's own
> >   PLR function index for the receiver class of the guard's defining record.** The index is
> >   `build_plr_function_index`'s `(module, qualname, lineno) → AST` map
> >   (`plr-sema/src/plr_sema/derive/receiver_state.py:1275-1308`), whose `qualname` for a method is
> >   `f"{class_name}.{name}"` (`:1306`); the receiver class is the defining record's own `class_name`
> >   (`scripts/survey_plr_preconditions.py:111-117`). The test is *"does a key
> >   `(module, f"{class_name}.{<name>}", *)` exist?"* — **a derived test over a shipped index, not a
> >   list**, and the same universe `_walk_closure` expands through `delegates_to`
> >   (`scripts/survey_plr_preconditions.py:120-124`, `plr-sema/src/plr_sema/derive/__init__.py:446-451`).
> >
> > **A `self.<name>(…)` whose `<name>` IS an indexed PLR-layer method of the receiver class stays
> > `Opaque`**, and this is the correct answer for the correct reason: `self._is_error_tail(response)`,
> > `self._check_96_head_fits_in_container(container)`
> > (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1684-1693` — pure arithmetic over
> > its own argument, reading **no** receiver state at all, so it is not tier (ii) under §15.1's
> > definition), `self._find_available_sites_sorted(plate)`
> > (`external/pylabrobot/pylabrobot/storage/incubator.py:87`) and
> > `self._is_error_tail` (`external/pylabrobot/pylabrobot/storage/inheco/incubator_shaker_backend.py:416`)
> > are all **coverage gaps the closure could have inlined** — exactly what `guard_predicate_unparsed`
> > means — not missing observations. `self.get_used_volume()` likewise: it is `VolumeTracker`'s own
> > indexed method, so it is refused here as well as by the two mechanisms the closed list below already
> > names.
> >
> > **Staging and fail-closed default.** `parse` sees one condition string and no context
> > (`plr-sema/src/plr_sema/derive/predicate_ast.py:9-15`), so the syntactic half is `parse`'s and the
> > index half is applied where the `function_index` already lives — `derive/bindings.py`'s
> > per-guard pass (`plr-sema/src/plr_sema/derive/bindings.py:460-472`), which demotes a refused
> > shape-(2) `EnvRef` to `Opaque` at its smallest enclosing predicate construction. **When no
> > `function_index` is supplied, every `k == 1` shape-(2) candidate is `Opaque`** — the same
> > fail-closed default `InlinedGuard.bindings` already takes
> > (`plr-sema/src/plr_sema/derive/__init__.py:480-488`).
> >
> > **The count of shape-(2) candidates refused by this test is published as
> > `n_env_ref_refused_plr_layer`** (§15.9 block (6)), so the artefact that makes the production
> > inspectable is not itself populated by the shapes the production should not have absorbed.
>
> **`EnvRef` inhabits BOTH unions, and that is a deliberate break of a shipped partition (round 2,
> A-C12 — a note, recorded so it is not discovered as a surprise).** `Predicate` and `Term` are
> disjoint `Union`s today (`plr-sema/src/plr_sema/derive/predicate_ast.py:272`, `:291`) with matching
> `_TERM_KINDS`/`_PREDICATE_KINDS` sets partitioning the wire tags (`:637-638`). `EnvRef` is the one
> node admissible in both positions, so **it belongs to both sets** and the partition becomes a cover
> with a one-element overlap. `from_json` is unaffected — it dispatches on the `"node"` tag, not on
> the sets (`:641-679`) — but any consumer that assumes disjointness must be updated with the
> production, and T35's row names the round-trip work that proves it.
>
> **`EnvRef` is not `Opaque`, and this is the entire point.** `contains_opaque`
> (`plr-sema/src/plr_sema/derive/predicate_ast.py:566-593`) is **false** for an `EnvRef` node; a new
> total sibling `contains_env_ref`, the same recursion collecting a different predicate, is **true**.
> §15.7's reason rule reads exactly those two functions and nothing else.
>
> > **Normative (both walks range over the α/β-SUBSTITUTED predicate — new in round 2, A-C4).**
> > `contains_opaque` and `contains_env_ref` are applied to the tree obtained by replacing each α/β-bound
> > `Var` with its bound `Term`, **not** to the raw `predicate` field. Without this clause the
> > amendment's own worked example does not fire: `:409`'s condition is
> > `not len(invalid_channels) == 0`, which parses to
> > `Not(Cmp(Len(Var("invalid_channels")), "==", Lit(0)))` — no `Filtered`, no `EnvRef`, no `Opaque`.
> > The `c not in self.head` filter lives in `InlinedGuard.bindings`
> > (`plr-sema/src/plr_sema/derive/__init__.py:480-488`, `tuple[dict[str, Any], ...]` at `:499`), which
> > no walk in `predicate_ast.py` or `bindings.py` reaches from `predicate`
> > (`plr-sema/src/plr_sema/derive/bindings.py:150-182`). **T35 lands the general helper this box
> > requires**: `bindings.substitute` (`plr-sema/src/plr_sema/derive/bindings.py:214-230`) replaces every
> > alpha-bound `Var` with its bound term, recursively, and `t30_measure.py`'s classifier calls it before
> > testing `contains_opaque`/`contains_env_ref` (`plr-sema/eval/t30_measure.py:821-822`) — which is why
> > the measurement can report `guard_predicate_unparsed` for `:409` at all — but nothing in §15.2, §15.3
> > or §15.7 said so before this pass, and an implementer adding a literal sibling walk over `predicate`
> > gets `contains_env_ref == False` there. AC-15.1 pins it with a fixture. (Re-anchored, T35: the
> > pre-T35 shipped classifier's own ad hoc one-level substitution, formerly named `_effective_unparsed`,
> > is retired in favour of this general, recursive helper.)
>
> **Shape (1) SUBSUMES the `Attr(Var("self"), …)` chains the shipped walk already produces**
> (`plr-sema/src/plr_sema/derive/predicate_ast.py:526-528`). This is a normalisation, not a new
> admission: `self._resource_pickup is None` already parsed; after the amendment it parses to
> `Is(EnvRef(…), negated=False)` instead of `Is(Attr(Var("self"), …), negated=False)`. **The reason it
> carries changes for a defect-fixing reason, not a gate-chasing one** — see the `Var("self")`
> invariant below and §15.9's re-prediction of `:1185`.
>
> **Normative (the `Var("self")` invariant).** **After the amendment no parsed predicate anywhere in
> the contract table may contain a `Var` node whose `name` is `"self"`.** If `self` occurs in any
> position other than as the root of an `EnvRef` path — subscripted (`self.head[channel]`), passed as
> an argument (`f(self)`), or standing alone as an operand — the **smallest enclosing predicate
> construction is `Opaque`**, fail-closed. This is a checkable invariant (AC-15.1, and the
> `n_var_self` / `n_opaque_only_by_var_self` counts of §15.9 block (6)), and it closes a real defect: `self` is a parameter of every PLR method, so
> a free `Var("self")` is indistinguishable from a resolvable parameter to any rule that asks *"is this
> name a parameter of `K`?"* — which is exactly what T30's shipped classifier asks
> (`plr-sema/eval/t30_measure.py:739-745`, `K_params`) and why `self.<x>` guards were being reported
> `decidable_or_operand_dependent`.
>
> **The closed list of what is NOT an `EnvRef`.** Each of these stays `Opaque`, or stays whatever
> non-env production already claims it; the list is exhaustive and a shape absent from it is by
> definition not admitted:
>
> | shape | example at this pin | disposition |
> |---|---|---|
> | a call whose callee is not `self`-rooted | `get_capture_or_validation_active()`, `time.time()` (`outputs/plr-sema/t30_measured_260905.json:30-45`) | `Opaque` |
> | `self` **subscripted** anywhere in the path | `self.head[channel].has_tip` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:534`), `self._parse_scpi_response(res)['status']` (`outputs/plr-sema/t30_measured_260905.json:22-25`) | `Opaque` |
> | `self` as an **argument** or bare operand | `f(self)` | `Opaque` (the `Var("self")` invariant) |
> | an attribute chain rooted at a **parameter or local** | `resource.parent`, `tip.tracker`, `destination.direction` | unchanged: `Attr(Var(…), …)`, a `Term`, resolved or ⊤ by E-CALL |
> | a call rooted at a parameter or local | `tip.tracker.get_used_volume()` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:656-657`) | `Opaque` — the tip/volume families' business, not the grammar's |
> | a `self`-rooted read inside an arithmetic `BinOp` | `volume - self.get_used_volume()` (`external/pylabrobot/pylabrobot/resources/volume_tracker.py:91`) | `Opaque` — a `BinOp` is not a `Term` in G1, before `EnvRef` is even reached |
>
> **The family-dispatch rule is unchanged and takes precedence over G7.** A guard the tip family
> claims, or a `volume_guards` entry, is skipped by the predicate evaluator entirely (§15.2's dispatch
> paragraph below), so `volume_tracker.py:92`/`:105` keep `volume_state_unknown` and **do not** become
> `guard_env_dependent` — increment 5 keeps them. Two independent mechanisms give that answer here (the
> dispatch rule, and the `BinOp` row above), which is deliberate: G7 is receiver-agnostic — it keys on
> the literal name `self`, whatever class it belongs to — so the dispatch rule, not the grammar, is
> what keeps family ownership stable.

> **Normative (G8, `Zip` and the membership comparators; new in the 260907 amendment).** Two minimal
> additions, each forced by one shipped condition and neither wider than that:
>
> 1. **`Zip(items: tuple[Term, ...])` is a `Term`.** `zip(<e₁>, …, <eₙ>)` with `n >= 2`, no `keywords`
>    and no `Starred`, each `<eᵢ>` parsing as a `Term`, parses to `Zip`. It is admissible **only as the
>    `seq` of an `AllOf`/`AnyOf`**; a `Zip` in any other position (in particular under `Len`, where its
>    length is a `min` this increment does not model) makes the enclosing construction `Opaque`. When
>    the comprehension's target is an `ast.Tuple`, every element must be a bare `ast.Name` and the
>    tuple's arity must equal `n`, else `Opaque`; the correspondence is positional, `target[i] ↔
>    items[i]`. As today, the bound names are recorded nowhere and appear inside the body as ordinary
>    free `Var`s (`plr-sema/src/plr_sema/derive/predicate_ast.py:53-60`), so no node gains a field and
>    the wire shape of `AllOf`/`AnyOf` is unchanged. **How a `Zip` RESOLVES as a sequence is normative
>    and is stated in §15.4 E-ENV** (round 2, A-C3): it is ⊤ unless every item resolves to a concrete
>    `Seq`, and `AllOf`/`AnyOf` over a ⊤ seq is ½, **never vacuously `T`**. A name bound by an
>    `AllOf`/`AnyOf` comprehension target resolves to ⊤ and never against `call.kwargs` (round 2,
>    A-C13) — also E-ENV, and still no node gains a field.
> 2. **`Cmp` admits `in` and `not in`, and every membership `Cmp` is ½ — round 2, A-C2/A-C10.** The op
>    set becomes exactly `{==, !=, <, <=, >, >=, in, not in}`, i.e. `_CMP_OPS`
>    (`plr-sema/src/plr_sema/derive/predicate_ast.py:298-305`) gains `ast.In` and `ast.NotIn` and
>    nothing else. Chaining (G2) applies unchanged. **Neither operand is required to be an `EnvRef`** —
>    the production is over `Term`s, as every other `Cmp` is — and **the evaluator decides a membership
>    `Cmp` in no case at all this increment: it is ½ unconditionally** (§15.4 E-ENV). The deciding case
>    spec_version 18 granted (RHS a concrete `Seq` of `Lit`s, LHS a `Lit`) is **deleted**, and §15.13
>    records it as a refused production with its reopening condition. The measured effect of this half
>    is therefore exactly *"one fewer `Opaque`"*, with no verdict consequence anywhere.
>
> **`Zip` does NOT reopen §15.3's β exclusions.** α and β are shape tests over an `ast.Assign`
> statement and both require a **bare `ast.Name`** iterand; `offsets = [c + o for c, o in
> zip(center_offsets, offsets)]` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1004` is a non-match for that
> reason and stays one. β's population stays **eight**, `offsets` at `:962`/`:1156` stays excluded, and
> §15.3 is not edited by this amendment at all.

> **Normative (G2, chained comparisons).** `ast.Compare` with `n` operators is `And` of `n` binary
> `Cmp`s, with each middle operand evaluated once. `len(tip_spots) == len(offsets) == len(use_channels)`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:522`) is
> `And(Cmp(Len(tip_spots), ==, Len(offsets)), Cmp(Len(offsets), ==, Len(use_channels)))`. Under Kleene
> `And`, one unresolved conjunct does **not** poison the rest: if `len(offsets) != len(use_channels)`
> resolves `F`, the whole is `F` regardless of the first conjunct.

> **Normative (G3, the emptiness-of-a-filtered-comprehension idiom).**
> `len(<x>) <cmp> <int>` where `<x>` is `Filtered(seq, pred)` — the term §15.3(α) binds — is evaluated
> as an existential over `seq`: `len(Filtered(seq, pred)) > 0` is `AnyOf(seq, pred)`, and
> `len(Filtered(seq, pred)) == 0` is `Not(AnyOf(seq, pred))`. This is the whole content of PLR's
> "reject the wrongly-typed elements" pattern: `len(not_tip_spots) > 0` with
> `not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, TipSpot)]` becomes
> "**∃** an element of `tip_spots` that is not a `TipSpot`". Only the comparisons `> 0`, `>= 1`,
> `== 0`, `!= 0` are recognised; every other numeric relation over a `Filtered` term is `Opaque`,
> because a count is not an emptiness test.

> **Normative (G4, `set(P)` uniqueness).** `Cmp(Len(SetOf(x)), ==, Len(x))` evaluates `T` iff `x`
> resolves to a `Seq` of hashable `Lit`s with no duplicate, `F` iff it resolves to such a `Seq` with a
> duplicate, and ½ otherwise. This is the only production that reads `set(...)`, and it reads it as an
> operator on a resolved sequence, never as a Python value.

> **Normative (G5, numeric atoms stay at ½ — no change to Open decision 2).** A `Cmp` whose operands
> are numeric and are not `Len`/`SetOf` terms folds to ½, exactly as
> `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:3327-3330` resolved and increment 5 §14.14
> item 1 narrowed. The **one** exception is increment 5's: a `Cmp` in a guard raising a taxonomy
> `volume_state` exception, evaluated against `volumestate`'s interval domain
> (`plr-sema/src/plr_sema/check/volumestate.py:117-131`, `:401-433`). This increment adds no second
> exception and in particular does **not** decide
> `tip.tracker.get_used_volume() > 0 and (not allow_nonzero_volume)`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:656-657`) — its right conjunct is
> a literal kwarg and resolves, but Kleene `And` of `½` and `T` is `½`.

> **Normative (G6, polarity from `kind`, never from the text).** `kind == "raise_guard"` fires when the
> predicate is `T`; `kind == "assert"` fires when it is `F`
> (`plr-sema/src/plr_sema/derive/__init__.py:458-463`). Unlike increment 1 §10.3.1's criterion 1, this
> increment **admits both**, because the ledger contains real `assert`-kind guards that the grammar
> decides: `len(set(use_channels)) == len(use_channels)` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:502` is an `assert`, and it is one
> of `pick_up_tips`'s three tier-(i) guards. Increment 1's own condition for re-adding the `assert`
> branch — *"a real or synthetic contract fixture with an `assert`-kind guard, added at the same time as
> the branch"* — is met by AC-15.1's fixture set.

**The grammar subsumes `tipstate`'s atom parser rather than duplicating it.** `parse_own_atom` and
`parse_bridge_atom` (`plr-sema/src/plr_sema/check/tipstate.py:414-439`) produce a three-production
`_Atom` (`BoolView`, `NullCheck(is_none=True)`, `NullCheck(is_none=False)`,
`plr-sema/src/plr_sema/check/tipstate.py:361-363`) whose truth comes from a *channel state*, not from
the call (`plr-sema/src/plr_sema/check/tipstate.py:442-452`). `BoolView(p)` is this grammar's
`Attr(p, has_tip)` used as a bare predicate and `NullCheck` is `Is`. **`tipstate` keeps ownership of
those two shapes and of their evaluation**: the tip family's atoms are decided by the tip lattice, and
G1's evaluator must not re-decide them. §15.4's dispatch rule is: a guard the tip family claims (its
existing `evaluate_call` selection, `plr-sema/src/plr_sema/check/tipstate.py:521-536`) is skipped by the
predicate evaluator entirely; a guard the volume family claims (a `volume_guards` entry) is likewise
skipped. **One `Finding` per guard remains invariant** — the rule increment 1 §10.3.3 states and
`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:3334-3339` records as must-not-implement.

---

## 15.3 The local-binding idiom

A guard's condition names free locals of the enclosing PLR method — `not_tip_spots`, `offsets`,
`missing`, `invalid_channels`. `InlinedGuard.free_vars` is `finding.mentions_params`
(`plr-sema/src/plr_sema/derive/__init__.py:528`), i.e. the intersection with the *parameter* names, so
it is silent about exactly these. Resolving them in general is the dataflow pass increment 4 §13.12
declined. **This increment resolves exactly two statement shapes and fails closed on everything else.**

> **Normative (α — the filtered comprehension).** In the body of the PLR function `K` that *defines*
> the guard, a single-target `ast.Assign` at **statement position** whose target is a bare `ast.Name`
> `x` and whose value is an `ast.ListComp` with **one** `comprehension`, no `is_async`, exactly one
> `if` clause, a bare-`ast.Name` target `e`, an `iter` that is a bare `ast.Name` naming a parameter of
> `K`, and an element expression that is that same `e`. The bound term is `Filtered(iter, pred)` where
> `pred` is `parse`d from the `if` clause. Both polarities are admitted: `if not isinstance(e, T)` and
> `if isinstance(e, T)`. `T` may be a single `ast.Name` or an `ast.Tuple` of them —
> `not isinstance(ts, (TipSpot, Trash))` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:645` is the real case that forces
> the tuple form.
>
> **Measured expectation, to be reproduced and published:**
> `not_tip_spots` in `pick_up_tips` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:496`),
> in `drop_tips` (`:645`), and `not_containers` in `_check_containers`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:873`). `invalid_channels`
> (`:407`) matches the *shape* but its `if` clause is `c not in self.head`, which `parse`s to
> `Opaque` — so α binds the term and the predicate stays ½. That asymmetry is the point: α is a
> binding rule, not a decision rule.

> **Normative (β — the `or`-default expansion, length only).** A single-target `ast.Assign` whose
> target is a bare `ast.Name` `x`, whose value is an `ast.BoolOp(Or)` whose **first** operand is
> `ast.Name(x)` (the self-default idiom) and whose **last** operand is either
> `list(range(len(<p>)))` or `[<expr>] * len(<p>)` with `<p>` a bare `ast.Name`. β binds **only the
> length** of `x`, as `Len(x) = Len(p)`, and binds it **only when every intermediate operand of the
> `BoolOp` resolves `F`**. It binds no elements.
>
> **The intermediate-operand clause is not decoration.** `use_channels = use_channels or
> self._default_use_channels or list(range(len(tip_spots)))`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:501`) has `self._default_use_channels`
> in the middle, which is instance state the analyzer cannot see — so β **declines** it and the
> already-shipped P3a/P3b machinery owns it instead (increment 1 §10.2.3,
> `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:271-284`): `channel_default_param`
> records `pick_up_tips → tip_spots`, `channel_default_disablers` poisons on a write to the middle
> term, and `channels_for_call` (`plr-sema/src/plr_sema/check/tipstate.py:245-270`) returns the
> resolved channel list or `None` for ⊤.
>
> **The P3a hook, restated (round 1, C7b).** The draft wrote *"the grammar consults `channels_for_call`
> for every `use_channels` term"*, hand-typing a string that `tipstate.py`'s own normative comment
> forbids: `channel_kwarg` is *"read from `receiver_state`'s own derived `channel_kwarg`, never
> hand-typed as `"use_channels"` here — that string is one of AC-13.15(iii)'s forbidden literals"*
> (`plr-sema/src/plr_sema/check/tipstate.py:254-257`). **Correct statement:** *the grammar consults
> `channels_for_call` for every term naming the receiver's derived `channel_kwarg` or its
> `channel_default_param[method]`, and never re-derives it.* There is no ordering collision with
> E-CALL step (1): `channels_for_call` already resolves the explicit kwarg first and falls back to the
> arity default (`plr-sema/src/plr_sema/check/tipstate.py:262-269`), which **is** E-CALL step (1)
> followed by a fallback, so the two rules cannot disagree.
>
> **β's population is eight, and it is published as a measurement rather than asserted.** Round 1
> established that every one of the six `aspirate`/`dispense` names is written a second time two to
> six lines later (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:962-971`,
> `:1156-1165`), so the draft's own rebinding clause would have deleted them all. The
> β-preserving-rebinding clause below rescues six of the eight and correctly fails closed on the other
> two. The eight: `pick_up_tips` `:517`; `drop_tips` `:661`; `aspirate` `:963`, `:964`, `:965`;
> `dispense` `:1157`, `:1158`, `:1159`. **`offsets` at `:962` and `:1156` is NOT in the population** —
> its second write at `:1004`/`:1177` is `offsets = [c + o for c, o in zip(center_offsets, offsets)]`,
> whose `iter` is a `zip(...)` call rather than the bare name, so the length becomes `min(...)` and the
> binding correctly goes `Opaque`.

> **Normative (the scope condition, and the rebinding clause).** Both idioms apply only when: the
> assignment is in the **same function body** as the guard (depth 0 of `K`, or the delegate's own body
> for a guard at `depth == 1`, `plr-sema/src/plr_sema/derive/__init__.py:472`); the assignment's
> `lineno` precedes the guard's; the assignment is not nested inside any `ast.If`, `ast.For`,
> `ast.While`, `ast.Try` or `ast.With` **that does not also contain the guard**; and **`x` — and the
> term's own iterand, i.e. α's `iter` name and β's `<p>` name — is written exactly once in `K`**. Any
> second write to any of those names anywhere in `K` — conditional or not, before or after the guard —
> makes the binding `Opaque`, **except** for the β-preserving shape below. This is what excludes
> `discard_tips`'s `use_channels`, which is rebound under `if use_channels is None:`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:816-817`), and `aspirate`'s
> `offsets`, rebound at `:1004` under the single-resource-spread branch.
>
> **The iterand half is new in round 1 (C13(1)).** The draft constrained writes to `x` only, and PLR
> rebinds iterands routinely — `resources` at `:999` and `:1172`, `use_channels` at `:501`, `:650`,
> `:958`, `:1152`. At this pin α is safe by accident (`_check_containers`'s `resources` is its own
> parameter, written once, `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:871-875`),
> but the *rule* permitted a term over the wrong sequence — a wrong verdict, not an `Opaque`. With this
> clause, α and β can again only produce `Opaque` from a same-body rebinding.

> **Normative (β-preserving rebinding — round 1, C6).** A second write to `x` of the form
> `x = [<elt> for <e> in x]` — a single `ast.ListComp` with exactly one `comprehension`, **no `if`
> clause**, `is_async` false, a bare-`ast.Name` target, and an `iter` that is the bare `ast.Name` `x`
> itself — **preserves `Len(x)`** and does **not** invalidate a β binding, because β binds only
> `Len(x)`. Every other second write to `x`, and every second write of any shape to an **α**-bound `x`
> (α binds elements, not a length), makes the binding `Opaque`.
>
> **This is the only clause that saves six of the eight β entries, and the obvious alternative does
> not work.** The natural narrowing — "no write between the β assignment and the guard" — saves none
> of them: `:969-971` sit *before* the guard at `:989-990` that reads them, and `:1163-1165` before
> `:1183`, `:1187` and `:1201`. Read literally, those six writes are
> `flow_rates = [float(fr) if fr is not None else None for fr in flow_rates]` and its two siblings
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:969-971`, `:1163-1165`): the
> conditional is an `ast.IfExp` in the *element* expression, not a comprehension filter, so the length
> is preserved exactly and the shape test above is a syntactic decision procedure for it. Contrast
> `:1004`/`:1177`, whose `iter` is a `zip(...)` call — length not preserved, `Opaque`, correctly.
>
> **Additionally, `scope_trail` must not place the guard under a header that rebinds `x`.** A guard
> whose nearest-first `scope_trail` (`scripts/survey_plr_preconditions.py:177-189`) contains a `for`
> entry whose target is `x` is `Opaque` for that free var. The survey already records those entries
> with polarity (`scripts/survey_plr_preconditions.py:191-209`; the `orelse` form is pushed as
> `"else of: if …"` at `:206`) and `for` headers at `:211-218`, so this is a read of an existing field,
> not a new derivation.

**Why this is not the general dataflow pass.** Increment 4 §13.12 declined "resolving a local's type
from its assignment" as a pass with unbounded blast radius. α and β are two `ast.Assign` shapes with a
single-write requirement, matched inside one function body, producing a *term* rather than a type, and
returning `Opaque` on every ambiguity. The measured population is publishable in one table (AC-15.2),
which a general pass's is not. **The difference that matters is failure mode**: a general pass that
mis-resolves a binding produces a wrong predicate and can produce a wrong verdict; α/β, *with the
iterand clause and the depth-≥1 forbiddance of §15.4 both in force*, can only produce `Opaque`, which
is today's behaviour.

**Both qualifiers are load-bearing, and round 1 is why they are written down.** Without the iterand
clause, a future PLR that moved a comprehension below a rebinding of its own `iter` would leave α
matching and binding a term over the wrong sequence — silently wrong, with no published count moving.
Without the depth forbiddance, α's terms would be matched in the *delegate's* parameter namespace and
evaluated against the *entry point's* `call.kwargs`, a substitution nothing in the repo records:
`SurveyRecord.delegates` is a bare `set[str]` (`scripts/survey_plr_preconditions.py:163`) and
`_walk_closure` expands it by name alone (`plr-sema/src/plr_sema/derive/__init__.py:446-449`), so
today `_check_containers(self, resources)` resolves only because the caller's local at `:956` happens
to share the name, and `_make_sure_channels_exist(self, channels)` fails closed only because
`use_channels` at `:980` happens not to. §15.4 forbids the resolution outright and T30 publishes the
size of what is forgone. **§15.8's reason 1 survives only under both qualifiers, and §15.8 no longer
rests the registry disposition on it.**

---

## 15.4 Evaluation against the IR call

> **Normative (E-CALL, operand resolution).** A `Var(name)` term resolves, in order: (1) to
> `call.kwargs[name]` if the IR `Call` carries it (`plr-sema/src/plr_sema/check/ir.py:194-204`) —
> note that `lower_calls` renames an untrusted kwarg to `?<j>`
> (`plr-sema/src/plr_sema/check/ir.py:796-808`), so a renamed key resolves to nothing and the term is
> ⊤; (2) to the contract entry's **`param_defaults`** value for that parameter (below); (3) to an α/β
> binding (§15.3); (4) otherwise ⊤. `Len` of a `Seq` is its length; `Len` of a `Ref` or `Top` is ⊤;
> `Len` of a `Lit` is ⊤ **except** where E-CALL(β) below routes it to a β binding.

> **Normative (E-CALL(2) is restated over a NEW derived field, `param_defaults` — round 1, D1).** The
> draft resolved step (2) against *"the resolved contract's recorded default"*. **No such field
> exists**: grep over `plr-sema/data/derived_contracts.json` for `"defaults"`, `"param_defaults"` and
> `"signature"` returns zero matches, and the derive package extracts no defaults anywhere. T30
> therefore records, per contract entry, `param_defaults: {param: <IR value JSON>}` read from the PLR
> function's own `ast.arguments.defaults` / `kw_defaults` **restricted to `ast.Constant` values** —
> anything else (a call, a name, a display) is **omitted**, fail-closed, never guessed. This is a
> derivation over PLR's own recorded surface, not a hand-typed table, so it adds no registry row.
>
> **It is not merely corrective.** With it, `transfer`'s absent `target_vols` resolves to `Lit(null)`
> ⇒ `if target_vols is not None` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1333` is `F` ⇒ E-SCOPE ⇒ **`SAFE`**
> at `:1335` and `:1337`; the `else of:` entry then evaluates `T` by E-UNCOND way (1) and
> `source_vol is None` is `F` ⇒ `SAFE` at `:1340`. Without it those three are ½ and §15.9's `transfer`
> row is false. Defaults at this pin: `source_vol` `:1277`, `ratios` `:1278`, `target_vols` `:1279`,
> all `ast.Constant` `None`.

> **Normative (E-CALL(5), the parameter-rebinding clause — round 1, C7a).** §15.3's single-write
> requirement protects α/β-bound locals. It says nothing about a **parameter** PLR rebinds before a
> guard reads it, which E-CALL step (1) would otherwise resolve to the *caller's* value. PLR does this
> constantly: `use_channels` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:501`, `:650`, `:958`, `:1152`;
> `resources` at `:999`, `:1172`; `vols` at `:968`, `:1162`; `ratios` at `:1343`.
>
> **A `Var(name)` naming a parameter of `K` that is written anywhere in `K` at a `lineno` below the
> guard's resolves to ⊤**, unless that write is a β-preserving rebinding (§15.3) and the term is a
> `Len`. Symmetric with §15.3, fail-closed in both directions.

> **Normative (E-CALL(β), the truthiness interaction — round 1, C14b).** `x = x or <default>` fires
> the default when `x` is `[]`, not only when it is `None`, and nothing in the draft modelled that.
> For a `Var(name)` that is the target of a β assignment in `K`:
>
> 1. if the call-side resolution yields a **statically known-falsy** value — `Lit(null)`, `Lit(false)`,
>    `Lit(0)`, or an empty `Seq` — the term resolves to the **β binding**;
> 2. if it yields a **statically known-truthy** value — a non-empty `Seq`, or a non-zero non-null
>    `Lit` — it resolves to **that value**;
> 3. if the parameter is absent from `call.kwargs` **and** its `param_defaults` entry is known-falsy,
>    the term resolves to the **β binding**;
> 4. otherwise ⊤.
>
> **Both directions are errors the draft would have made.** Resolving `offsets=[]` through step (1) to
> `Seq([])` gives `Len == 0 ≠ len(tip_spots)`, so the `assert`-kind guard at `:522` fires: a **false
> `WILL_FAIL`**. Making β unconditionally win would override a real caller-supplied list and produce a
> **false `SAFE`** on the exact mismatch `:522` exists to catch. The falsy/truthy split is what makes
> both impossible.

> **Normative (E-CALL(depth), the delegate→caller substitution is FORBIDDEN this increment — round 1,
> item 13 option (a)).** A `Var(name)` in a guard at `depth >= 1` resolves **only** through
> `channels_for_call` (for the derived channel term, §15.3) or an α/β binding in the delegate's own
> body over the delegate's own parameters. It **never** resolves against the entry point's
> `call.kwargs`, because no argument mapping across a `delegates_to` edge is recorded anywhere:
> `SurveyRecord.delegates` is a bare `set[str]` (`scripts/survey_plr_preconditions.py:163`) and
> `_walk_closure` expands it by name alone (`plr-sema/src/plr_sema/derive/__init__.py:446-449`). Every
> other depth-≥1 free name is ⊤.
>
> **The closest shipped mechanism does not fit and is not repurposed.** P9's
> `_delegate_channel_bindings` (`plr-sema/src/plr_sema/derive/receiver_state.py:937-965`) **is** a
> delegate-parameter → caller-argument substitution, but it reads `call.keywords` only
> (`plr-sema/src/plr_sema/derive/receiver_state.py:907`) while PLR calls every delegate that matters
> **positionally** — `self._check_containers(resources)` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:956`,
> `_check_no_lid(resource, "aspirate from")` at `:978`, `self._make_sure_channels_exist(use_channels)`
> at `:980`, `self._assert_resources_exist(tip_spots)` at `:520` — and it requires a `self.` receiver
> (`plr-sema/src/plr_sema/derive/receiver_state.py:954`), excluding a module-level delegate like
> `_check_no_lid` outright. Building the general map is ~90 LOC over a new derived field with its own
> measured selection and its own registry argument; it is **increment 7's**, alongside tier (ii).
>
> **T30 publishes the exposure this forgoes**: the count of depth-≥1 guards whose free vars *would*
> have resolved by name coincidence against the entry point's kwargs (§15.9 block (2)). The cost at
> this pin is `:875` (`_check_containers`) and `:117` (`_check_no_lid`); the gate is untouched, because
> `pick_up_tips`'s three deciding guards are all at depth 0.

> **Normative (E-ENV, an `EnvRef` decides NOTHING in this increment — new in the 260907 amendment).**
> An `EnvRef` node evaluates to **½ in predicate position and ⊤ in term position, unconditionally**,
> under every state, for every path, with no exceptions and no lookup table. **No environment is read
> in increment 6.** In particular: `env` gains no member (§15.8's `cache_key` paragraph is unchanged),
> no observation record is consulted, and `EnvRef.path` is never matched against a list of known
> attributes — a rule that matched paths would be a hand-maintained surface, which §15.8 argues this
> production is not.
>
> Everything above it is ordinary Kleene: a `Cmp`, `Is`, `IsInstance`, `AllOf`, `AnyOf` or `Not`
> containing an `EnvRef` is ½; `Len(EnvRef)` is ⊤ and so is `Len` of a `Zip`; an `And` with an `F`
> conjunct is still `F` and an `Or` with a `T` disjunct is still `T`.
>
> > **Normative (`Zip` resolution, and quantification over a ⊤ seq — new in round 2, A-C3).** **A
> > `Zip` resolves to ⊤ unless EVERY item resolves to a concrete `Seq`, in which case it resolves to
> > the positional zip truncated to the shortest; `AllOf`/`AnyOf` over a ⊤ seq is ½, never vacuously
> > `T`.** E-TYPE's quantifier rule — *"`AnyOf(seq, pred)` over a `Seq` is `T` if any element is `T`,
> > `F` if all are `F`, else ½"* — is conditioned on the seq being a `Seq` and does not reach a `Zip`;
> > this clause supplies the missing case at the one node the gate candidate's second blocker is made
> > of. **It matters at `:514` because the two items are asymmetric**: `use_channels` resolves to an
> > exact tuple via `channels_for_call` (`plr-sema/src/plr_sema/check/tipstate.py:245-269`), while
> > `tips = [tip_spot.get_tip() for tip_spot in tip_spots]`
> > (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:504`) is a **projecting**
> > comprehension whose `elt` is not the identity map of its target, so `_parse_filtered`'s identity
> > check rejects it (`plr-sema/src/plr_sema/derive/predicate_ast.py:542-558`), α does not bind it, and
> > `tips` is ⊤. An implementer who built the zip from the operand that *did* resolve would construct a
> > sequence of the wrong length; `AnyOf` returning `F` over it, negated, is a **false `WILL_FAIL`**,
> > and the dual — `AllOf` over a short or empty zip returning `T` vacuously, negated to `F`, emitting
> > `SAFE` at the `raise_guard` — is a **false `SAFE` at the gate site**. Both are closed by rule.
> >
> > **Normative (comprehension-bound names — new in round 2, A-C13).** A name bound by an
> > `AllOf`/`AnyOf` comprehension target (`channel`, `tip` at `:514`; the single target of an ordinary
> > `all(... for v in ...)`) **resolves to ⊤ and is never resolved against `call.kwargs`**, even when it
> > collides with a real parameter name. G8(1)'s positional correspondence `target[i] ↔ items[i]` is
> > therefore normative for *reading* the source and is deliberately not reconstructible downstream —
> > **no node gains a field**, and nothing downstream needs one, because every such name is ⊤ anyway.
> > This closes a pre-existing hazard for single-target `AllOf` that `Zip` would otherwise have doubled
> > per comprehension.
> >
> > **Normative (membership decides nothing — new in round 2, A-C2/A-C10).** **Every `in` / `not in`
> > `Cmp` evaluates ½, unconditionally, in this increment**, whatever its operands resolve to. The
> > spec_version 18 deciding case is deleted for three independent reasons, each sufficient: there is
> > **no literal-container `Term`** that can reach it (`_parse_term` has no `ast.List`/`ast.Tuple`
> > branch, `plr-sema/src/plr_sema/derive/predicate_ast.py:518-539`, and §15.13 confirms the amendment
> > adds none); its **measured population at this pin is zero**, with no fixture; and deciding
> > `not in` ⇒ `T` would require an `ir.Seq` to be **complete** rather than a lower bound, which
> > nothing in §15.4 asserts of one. §15.13 records it as a refused production with its reopening
> > condition.
>
> **What follows is a theorem, not a prediction (round 2, A-C2).** With the two clauses above, the
> amendment's **only** path to a new definite value is Kleene short-circuit over an **already
> decidable** conjunct — `And(EnvRef, F) = F`, `Or(EnvRef, T) = T`. That is Kleene, it is sound, and it
> is the same behaviour §15.2 G1 already specifies for a nested `Opaque` node. The two other paths the
> adversarial pass found — **vacuous quantification over a `Zip`** and the **membership deciding
> case** — are closed **by rule** rather than counted, which is why §15.9's box can now assert that the
> amendment decides nothing rather than predict it. §15.9 block (4) still publishes
> `n_decided_via_env_ref_shortcircuit`, the residual path's own count, predicted **0** at this pin (no
> cluster in the ledger is an `And`/`Or` mixing an `EnvRef` with an independently decidable operand). A
> non-zero value is not a failure — it is the number that must be inspected before T31's verdicts are
> accepted.
>
> **The probe, answered explicitly.** `Zip((Seq[8], ⊤))` resolves to **⊤** — not to an 8-element
> sequence, and not to an empty one — because its second item is not a concrete `Seq`. `AllOf` over it
> with a ½ body is **½**. `AllOf(Zip(Seq([]), ⊤), <½>)` is likewise **½**, not `T`: the empty `Seq`
> does not make the zip empty, because the zip is not built at all.
>
> **Interaction with E-SCOPE and E-UNCOND, stated so the amendment cannot manufacture reachability.**
> A scope entry containing an `EnvRef` evaluates ½: it never returns `F`, so E-SCOPE never turns it
> into a `SAFE`, and it never evaluates `T`, so E-UNCOND way (1) is never satisfied by it and no
> `WILL_FAIL` becomes newly permissible. Ways (2) and (3) are untouched — an `EnvRef` is not a bare
> zero-argument call in `env` (way (2) tests the callee name against `env`, and `EnvRef` paths are
> never entered into `env` in this increment) and it is not an `ast.For` node (way (3)).
>
> **Where an `EnvRef` first acquires a value: increment 7's tier (ii).** §15.6 defers the observation
> record — backend class and signature, deck membership, head channel count, lid topology — to
> increment 7, and T34 (§15.12) is the row that builds it. The amendment makes that increment's job
> mechanically obvious rather than exploratory: tier (ii) is *"give `EnvRef` a lookup against an
> observation returned from the executed window, and partition `cache_key` on it"*, over a population
> §15.9 now publishes by path. `self.backend.can_pick_up_tip` is the one `EnvRef` on the gate candidate
> that needs a backend **method body** rather than an observed value, which §15.6 already records as
> the expensive half.

> **Normative (E-TYPE, `RESOURCE` operands — restated in round 1, C4).** `IsInstance(t, (T₁ … Tₙ))`
> where `t` resolves to a `Ref` is decided against the referenced `RESOURCE` instruction's declared
> `type`, or its `element_type` when the `Ref` carries a `cell`
> (`plr-sema/src/plr_sema/check/ir.py:178-192`). It is:
>
> - **`T`** iff the declared name **is, or is a subclass of, some `Tᵢ`**;
> - **`F`** iff the declared name and every `Tᵢ` are **disjoint in the class hierarchy** (neither is an
>   ancestor of the other) **and** the declaration is known to be **exact**;
> - **½** otherwise — including whenever the declared name is `None`, or is not a class the subclass
>   test can decide.
>
> **A declaration derived from `_generic_plr_type_name` is NEVER exact**
> (`plr-sema/eval/oracle_common.py:235-248`): it returns the most-specific *generic* MRO ancestor whose
> name is in `_PLR_GENERIC_RESOURCE_NAMES` (`plr-sema/eval/oracle_common.py:225-232`), not the concrete
> class, so on the frozen benchmark the `F` branch is **unreachable** and every `IsInstance` atom is
> `T`-or-`½`. A declaration read from a graph-lane `RESOURCE`
> (`plr-sema/src/plr_sema/check/ir.py:694-695`) is exact iff the graph payload marks it so; absent such
> a mark, it is not exact.
>
> `AnyOf(seq, pred)` over a `Seq` is `T` if any element is `T`, `F` if all are `F`, else ½. The
> subclass relation itself is **derived**, from the P1 class index the derive package already builds
> over the PLR surface — never a hand-typed table (§15.8).
>
> **What the draft's rule did, and why both halves were wrong.** Its `F` clause treated a declared type
> as *exact* when a declaration is an **upper bound**: a `Trash` records `"Container"` under O1
> (`external/pylabrobot/pylabrobot/resources/trash.py:4`; `Trash` is absent from the generic set,
> `Container` is present), so `Container` vs `(TipSpot, Trash)` returned `F` ⇒ `Not` `T` ⇒ `AnyOf` `T`
> ⇒ a **false `WILL_FAIL`** on 65 clean `drop_tips`/`discard_tips` operations. Its `T` clause required
> *equality*, so `_check_containers`'s `isinstance(r, Container)` against a `Well` was neither `T`
> (not equal) nor `F` (`Well` **is** a `Container`, so not disjoint) — ½, falsifying the draft's own
> `:875` prediction. The restated rule keeps `:498` decidable in the `SAFE` direction — `TipSpot` is in
> the generic set and is its own most-specific match, so `element_type == "TipSpot"` ⇒ `IsInstance`
> `T` ⇒ `Not` `F` ⇒ `AnyOf` `F` ⇒ the `raise_guard` does not fire — and makes `:647` fail closed at ½
> rather than fabricating a verdict.

> **Normative (O1 — the operand observation, and why the benchmark cannot run without it).** On tier 1
> the RESOURCE declarations are built by `resources_from_example`
> (`plr-sema/eval/oracle_common.py:397-410`), which sets `type` from `deck_layout.resources` and sets
> **no `element_type` and no grid at all**. `deck_layout` carries only the scaffolding's own additions
> — the harness's own docstring records that most referenced resources are never in it and that
> `infer_layout()` silently defaults an unrecognised name to a bare `Plate`
> (`plr-sema/eval/oracle_common.py:284-292`). **Consequently every `IsInstance` atom on the frozen
> benchmark is ½ today for a reason that has nothing to do with the grammar.**
>
> **The `type` half is already computed; the `element_type` half — the half the gate rests on — is
> NOT, and round 1 corrected the draft on exactly that point (C11a).**
> `resource_types_from_kwargs` returns `{resource_name: plr_class_name}` for every resource reachable
> from a call's raw kwargs (`plr-sema/eval/oracle_common.py:277-308`), and `run_runtime` already
> captures it into `RuntimeOutcome.resource_types`
> (`plr-sema/eval/oracle_common.py:336-373`). But it does so via `resource_type_of`'s **parent-wins**
> rule — `target = parent if parent is not None else obj`
> (`plr-sema/eval/oracle_common.py:251-274`) — so for a list of `TipSpot`s it returns
> `{tip_rack_name: "TipRack"}`. **The element's own class is precisely what that function is written to
> discard.** The draft's *"the observation the harness already computes"* was true of the half that
> does not decide `:498` and false of the half that does.
>
> **O1, sized honestly.** (a) Thread the existing `{resource_name: class}` map into
> `resources_from_example` as the RESOURCE `type` (~10 LOC over
> `plr-sema/eval/oracle_common.py:397-410`). (b) Add a **new element walk** alongside the existing one
> in `resource_types_from_kwargs`, recording `_generic_plr_type_name(obj)` for the object *itself*
> rather than for its parent, keyed by parent name (~10 LOC). (c) The heterogeneity guard below (~5).
> (d) Thread `element_type` through (~10). **~40 LOC, not "~25 lines over data the harness already
> computes."**
>
> **Normative (the heterogeneous-parent rule — round 1, C11b).** A `Resource` instruction carries one
> `element_type` per slot (`plr-sema/src/plr_sema/check/ir.py:178-192`), a slot is one resource *name*,
> and `resource_types_from_kwargs` uses `out.setdefault(name, cls)` — **first element wins**
> (`plr-sema/eval/oracle_common.py:294-308`). A `Deck`-parented reference set (a `Trash`, a `Plate` and
> a `TipRack` all have `parent == deck`) would therefore collapse to one arbitrary sibling's class, and
> E-TYPE would decide every cell under that parent against it. **O1 records, per parent name, the SET
> of element generic classes; `element_type` is that class iff the set is a singleton, and `None`
> otherwise** (fail-closed). The count of parents with heterogeneous children is published in AC-15.4.
>
> **This is an observation from the executed window, exactly increment 5 §14.6's shape**, and it is
> therefore a tier-(ii) input by §15.1's own definition. It is admitted here, and only here, because
> without it §15.9's measured sets cannot distinguish "the grammar failed" from "the harness supplied
> no type", which is the one confusion that would make the gate uninterpretable. **In the graph lane
> (`lower_graph`, `plr-sema/src/plr_sema/check/ir.py:686-701`) `element_type` is a graph field read
> straight off the declaration at `:695` and the same atoms are tier (i) with no observation at all** —
> O1 repairs the benchmark, not the analyzer. **Disclosure the user is owed, in this document's own
> words (round 1, C11c):** *this increment's GO is conditional on one tier-(ii) observation, admitted
> to repair the benchmark's data poverty, in an increment that otherwise defers tier (ii); §15.9(5)'s
> with/without delta measures whether O1 matters, not whether the residual is legitimately tier (i);
> and no count of populated graph-lane payloads is offered here.*

> **Normative (E-SCOPE, an unsatisfied enclosing scope makes `SAFE` true).** Before evaluating a
> guard's own predicate, `parse` and evaluate each entry of its `scope_trail[1:]` (its own body's
> conditions, less the self-entry E-UNCOND(6) excludes). If **any** entry evaluates `F`, the guard is
> not reached, cannot raise, and the emitted `Finding` is `Verdict.SAFE` regardless of the guard's own
> predicate. This is increment 5 §14.6's asymmetry — *"if the condition is false, the site cannot
> raise, so a `SAFE` finding is true under both branches and needs no hypothesis"* — applied to a scope
> entry. An entry beginning `"else of: if "` is evaluated as the negation of its test; an entry that is
> a `for`/`while` header, or that parses `Opaque`, contributes ½ and never `F`.
>
> **`caller_scope` is NOT part of E-SCOPE, contrary to the draft (round 1, C2; arithmetic corrected in
> round 2, A-C11).** `InlinedGuard` has **nine** fields in the landed dataclass — `condition`,
> `predicate`, `scope_trail`, `raises`, `kind`, `free_vars`, `site`, `depth`, `bindings`
> (`plr-sema/src/plr_sema/derive/__init__.py:491-499`) — **none of them `caller_scope`**. The draft's
> "exactly seven" counted the pre-T30a field set and was stale the moment `predicate` and `bindings`
> landed; the conclusion is unaffected, the arithmetic was not. That field exists
> only on the volume bridge's per-guard JSON, attached by P10
> (`plr-sema/src/plr_sema/derive/receiver_state.py:900-934` is its sibling constructor; the consumer is
> `volume_guard_is_unconditional`). Every guard in §15.1's tables is an `InlinedGuard`, so the draft's
> *"and, for a bridged guard, of its `caller_scope`"* was vacuous, and its *"a `null` scope"* had no
> referent — two readings differing by ~256 operations. **This increment does not build the
> `InlinedGuard` P10 equivalent**; it forbids the `WILL_FAIL` instead (E-UNCOND(4)).

> **Normative (E-VERDICT, from predicate truth to a `Finding`).** With `fires` computed from the
> predicate and `kind`'s polarity (G6), and with §15.4's E-SCOPE not having already returned `SAFE`:
>
> | `fires` | `Finding` |
> |---|---|
> | **F** | `Verdict.SAFE`, `category=""`, `reason=""`, `plr_site=guard.site`, `detail=guard.condition` |
> | **T** | `Verdict.WILL_FAIL`, `category="precondition_state"`, `reason=""` — **only if the guard is unconditional (E-UNCOND below)**; otherwise `Verdict.UNKNOWN` with `reason="guard_env_dependent"` |
> | **½** | `Verdict.UNKNOWN` with the finest applicable reason (§15.7) |
>
> This is increment 1 §10.3.3's table
> (`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:582-586`) with one row split.
> `precondition_state` is an existing `FAILURE_CATEGORIES` member
> (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:765-768`) and HM-5 stays FROZEN at 6.

> **Normative (E-UNCOND — generalising increment 5's R1).** A guard may emit `WILL_FAIL` only if it is
> **unconditional**: every entry of its `scope_trail[1:]` is recognised as satisfied, in exactly three
> ways and no others, **and clauses (4) and (5) below do not block it**.
>
> 1. **By evaluation.** The entry `parse`s to a non-`Opaque` predicate that evaluates **T** under
>    §15.4. This is new, and it is the generalisation: increment 5's rule could only recognise a bare
>    zero-argument call in `env`, because it had no evaluator.
> 2. **By hypothesis.** The entry is a bare zero-argument call `f()` whose callee name is in `env`
>    (increment 5 §14.6, unchanged; `plr-sema/src/plr_sema/check/ir.py:918-944` is the key component
>    that partitions the cache by it).
> 3. **By structure — R1.** The entry is the `ast.For` statement increment 5's B1 bound `<name>` over
>    for this guard, recognised by position containment against its `for_span` (increment 5 §14.6).
>
> **Everything else blocks `WILL_FAIL`**: a `while` header, an `async for`, any `for` header R1 did
> not bind, an entry that evaluates ½, and an entry that parses `Opaque`. In particular, an entry
> beginning `"else of: if …"` is recognised **only** by way (1) — its negated test must itself
> evaluate `T` — and never by way (2), preserving increment 5's AC-14.4 behaviour that an `else of:`
> entry is not satisfied merely because its test text is in `env`.
>
> **Why way (1) is sound where increment 5 needed a structural exception.** Increment 5's R1 exists
> because the analyzer could not evaluate `for op in aspirations:` and had to recognise the node
> instead. Way (1) evaluates the entry as a predicate over the same call the guard is being checked
> against; if it is `T`, the branch is taken on every execution of this call, and the guard is reached.
> It cannot manufacture reachability, because a `for`/`while` header has no predicate form and always
> falls through to way (3) or to unrecognised.

> **Normative (E-UNCOND(4), depth — round 1, C2).** **No guard at `depth >= 1` may emit
> `Verdict.WILL_FAIL` in this increment.** Its `Finding` is `Verdict.UNKNOWN` with
> `reason="guard_env_dependent"`. The reason is structural, not conservatism for its own sake: an
> inlined guard's reachability depends on the *call site* in the entry point, and `InlinedGuard`
> records nothing about it (E-SCOPE's box above). Building that record is entangled with the
> unspecified delegate→caller substitution E-CALL(depth) forbids, and both are increment 7's.

> **Normative (E-UNCOND(5), the empty trail — round 1 C1, REFINED at spec_version 20 after T32
> measured AC-15.10's floor unmet).** A guard at `depth == 0` whose `scope_trail` is empty — **after
> E-UNCOND(6)'s self-entry exclusion**, so "empty" means `scope_trail[1:]` is empty and there is no
> enclosing `if`/`for`/`while` entry — is **not** vacuously unconditional. It may emit `WILL_FAIL`
> **iff all three of the following hold of the defining function `K`**, and **otherwise yields ½ and
> `guard_env_dependent`**:
>
> 1. **No earlier `ast.Return`.** `K`'s body contains no `ast.Return` node, at **any** nesting depth,
>    at a `lineno` lower than the guard's. A conditional early return means the operation may complete
>    without ever reaching the guard, so the guard's own truth says nothing about the operation.
> 2. **Not lexically enclosed by an `ast.Try` or an `ast.With`.** No `ast.Try` and no `ast.With` node
>    of `K` has a span containing the guard. A handler may catch the raise and a context manager's
>    `__exit__` may suppress it, so the operation may complete despite the guard firing. Note this is
>    an **enclosure** test, not the lineno-ordered one spec_version 19 wrote.
> 3. **No earlier `ast.Break` and no earlier `ast.Continue`** at any nesting depth at a `lineno` lower
>    than the guard's. Conservative: both are exits from an enclosing statement about which the trail
>    records nothing.
>
> **An earlier `ast.Raise` does NOT block, and neither does an earlier `assert`. That reversal is the
> whole of the refinement.**

> **Normative (why an earlier `raise` cannot falsify a `WILL_FAIL` — the argument, stated so it can be
> attacked directly rather than inferred).** Let `G` be a depth-0, empty-trail guard whose predicate
> evaluates `T` and which satisfies (1)–(3), and let `R` be any `ast.Raise` (or `assert`) in `K` at a
> `lineno` below `G`'s. Exactly two executions are possible.
>
> - **(a) `R` fires.** The operation raises at `R` and does **not** complete.
> - **(b) `R` does not fire.** Control is not diverted anywhere else either — (1) forbids an earlier
>   return, (2) forbids a swallowing handler or context manager, (3) forbids a break/continue — so
>   control reaches `G`, whose predicate is `T`, so `G` fires and the operation raises at `G`.
>
> **In both branches the operation fails**, so no hypothesis about `R` is needed and none is taken.
>
> **This turns on `WILL_FAIL` being a claim about the OPERATION, not about the site.** `join`
> propagates one `WILL_FAIL` finding to the whole operation
> (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:576-581`), and the oracle's `compare` scores
> the operation's *index* — `verdict == "will_fail"` against `outcome == "ran_ok"` — never the identity
> of the statement that raised. A `WILL_FAIL` attributed to `G`'s `site` on an operation that in fact
> raised at `R` is therefore **not** scored unsound, and is not scored unsound for a good reason
> rather than by an accident of the comparison: the published claim ("this operation fails") is true.
> A-COMPLETES is **not** invoked, because nothing here claims the operation completes. What the
> analyzer does lose in branch (a) is the *attribution* of the failure to `G` rather than to `R`; that
> is a precision claim this increment never made and no acceptance criterion reads.
>
> **Superseded: C1's remedy exactly as written at spec_version 16–19.** *"It may emit `WILL_FAIL` only
> if `K`'s body contains no `ast.Return`, `ast.Try`, `ast.Raise`, `ast.Break` or `ast.Continue`, at any
> nesting depth, at a `lineno` lower than the guard's."* That wording is **withdrawn**, on two
> independent grounds. (a) It blocked on any earlier `ast.Raise`, which by the argument above cannot
> make a `WILL_FAIL` false — so it bought **no** soundness and cost every decidable verdict downstream
> of any earlier check. (b) It tested `ast.Try` by `lineno` order rather than by enclosure, which is
> both wider than the hazard (a `try` block that closed above the guard is harmless) and aimed at the
> wrong property (what matters is whether a handler is *around* the guard). **The cost was measured,
> not hypothesised**: `pick_up_tips`'s `:502` and `:522` are depth-0 empty-trail `assert`s whose only
> earlier control statement is the conditional `raise TypeError` at `:498`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:496-522`), which is the *normal*
> shape of a PLR precondition sequence — check, raise, check, raise. Under the superseded wording no
> such guard can ever emit `WILL_FAIL`, and T32 duly measured all three p1 mutators at **0 achieved**
> (`outputs/plr-sema/predicate_mutants_260908_inc6.json`; §15.15's T32 row, §15.16.3 R1).
>
> **What the refinement does NOT relax.** Clauses (1)–(3) are unchanged in direction and each is still
> fail-closed; E-UNCOND(4)'s `depth >= 1` forbiddance is untouched; ways (1)–(3) of the trail test are
> untouched; and the population the refinement can reach is exactly the depth-0 empty-trail guards,
> which §15.4's E-UNCOND(6) corollary bounds to the null-condition guards plus the `assert`-kind
> analogues. `:117` and `:2092` — C1's two original false-`WILL_FAIL` sites — **stay blocked**: `:117`
> sits below `_check_no_lid`'s early `return` and so fails clause (1), and `:2092` is `raise e` in an
> `except` handler and so fails clause (2) *and* is derived tier (iii) by `is_dynamic_raise` before
> E-UNCOND is reached at all.

> **Normative (the wire field, `reachability_clear` — new at spec_version 20).** The evaluator cannot
> compute clauses (1)–(3): it reads a guard record, not `K`'s AST. E-UNCOND(5) is therefore evaluated
> against **one additive derived boolean** on `InlinedGuard` and on the contract table's guard record,
> named `reachability_clear`, computed by the derive package at guard-construction time from `K`'s AST:
>
> ```
> reachability_clear = (not has_return_before)
>                      and (not enclosed_by_try_or_with)
>                      and (not has_break_continue_before)
> ```
>
> with `has_return_before` and `has_break_continue_before` ranging over `K`'s whole body at any nesting
> depth at a `lineno` below the guard's, and `enclosed_by_try_or_with` true iff some `ast.Try` or
> `ast.With` span contains the guard. **`ast.Raise` and `ast.Assert` appear in none of the three
> tests** — that is the refinement, expressed once, in the derivation.
>
> - **Additive.** No existing field changes and `condition` remains the source of truth, exactly as
>   `predicate` and `bindings` were added before it (§15.2 G0).
> - **Absent ⇒ `None` ⇒ fail-closed.** A guard record written before T36, or any record lacking the
>   field, yields `None`, and E-UNCOND(5) treats `None` as *not clear* and blocks `WILL_FAIL`. This is
>   the same fail-closed default `bindings` already takes, and it is what makes the field safe to add
>   without a coordinated regeneration.
> - **Consulted only for depth-0 empty-trail guards.** It is not a general reachability claim and no
>   other clause reads it.
> - **Zero registry cost.** It is a derived test over `ast` node classes, in the same class as
>   `is_dynamic_raise` (§15.1's derived-tier-(iii) box): no `REASON_VOCABULARY` member, no registry row,
>   no per-row ceiling.
>
> The evaluator's parameter is `k_reachability_clear: bool | None`, fed from the field. **T31 shipped
> that parameter with every production caller passing `None`** (§15.15's T31 row), which is why this is
> a *wiring* task (T36) and not a semantics rewrite: the clause's shape was already right, its input
> was never derived.

> **This clause exists because the record the evaluator reads cannot distinguish the two cases.**
> `scripts/survey_plr_preconditions.py` overrides exactly six visitors — `visit_If` (`:191`),
> `visit_For`/`visit_AsyncFor` (`:211`/`:220`), `visit_While` (`:222`), `visit_Raise` (`:231`),
> `visit_Assert` (`:256`) — and **there is no `visit_Try` and no `visit_Return`**. So a `raise` after
> an early `return`, and a `raise` inside an `except` handler, both carry an *empty* trail, and nothing
> in the record says which. `_check_no_lid` is exactly that shape:
> `lidded = _lidded_ancestor(resource)`, `if lidded is None: return`, `if lidded is resource: raise …`,
> then a statement-position `raise` at `:117`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:110-120`).
>
> **`reachability_clear` is precisely the repair for those two missing visitors**, and it is derived
> rather than added to the trail for a reason: a `visit_Try`/`visit_Return` override would change the
> *shape* of `scope_trail` for every guard in the table and re-key everything that reads it, whereas a
> boolean computed from the same AST at guard-construction time answers the one question E-UNCOND(5)
> asks and touches nothing else.
>
> **The shipped precedent implements the wrong reading, and this increment deliberately departs from
> it.** `volume_guard_is_unconditional` fails closed **only on `None`**
> (`plr-sema/src/plr_sema/derive/receiver_state.py:2079-2080`); an empty list falls through its loop
> and returns `True` (`plr-sema/src/plr_sema/derive/receiver_state.py:2084-2094`) — vacuous
> satisfaction, in shipped code. An implementer following the one precedent in the tree would emit
> `WILL_FAIL` on 163 clean operations at `:117` and 93 at `:2092`, and since `join` propagates any
> `WILL_FAIL` to the whole operation
> (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:576-581`) and `compare` scores
> `verdict == "will_fail" and outcome == "ran_ok"` as unsound
> (`plr-sema/eval/oracle_common.py:645-647`), AC-15.8 would fail by construction. **That is why this is
> normative text and not a note.**

> **Normative (E-UNCOND(6), the self-entry — round 1, D3).** For a `raise_guard` whose
> `scope_trail[0]` is `"if " + condition`, that entry **is** the guard's own condition: `visit_Raise`
> reads `scope_trail[0]` into `condition` **without popping it**
> (`scripts/survey_plr_preconditions.py:246-254`). It is therefore excluded from both E-SCOPE and
> E-UNCOND, which range over `scope_trail[1:]`. The two rules would otherwise dispose of the same test
> twice; the answers agree, so this is not unsound, but AC-15.5(i)'s "exactly one `SAFE` finding" would
> be ambiguous about which rule produced it.
>
> **A corollary worth stating, because it bounds C1's population.** Since `visit_Raise` sets a non-null
> `condition` only when `scope_trail[0]` starts with `"if "`, **every `raise_guard` with a non-null
> condition has a non-empty trail.** The empty-trail population is therefore exactly the null-condition
> guards with no enclosing `if`/`for`/`while` — `:117`, `:2092`, and the `assert`-kind analogues — and
> *not* every `<unconditional>` cluster: `:1770`/`:1920` are `<unconditional>` with three-deep
> `"else of: if …"` trails (§15.1.4).

**Interaction with the join.** `join` is unchanged
(`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:576-581`) and stays the one function that
aggregates. A per-op `SAFE` therefore requires **every** finding on that operation to be `SAFE` — every
guard `F` or excluded by E-SCOPE, every gap absent, and every family (tip, volume) also `SAFE`. §15.5
is about whether that is reachable. **After round 1 it is not, and now structurally so**: a tier-(iii)
guard emits `UNKNOWN` (§15.5), every liquid-handling operation carries one, and one `UNKNOWN` makes the
operation `UNKNOWN`. What the draft treated as a contingent finding about tier (ii) is now also a
consequence of the fence.

---

## 15.5 Q1 — what a joined `SAFE` means on an operation carrying a tier-(iii) guard

Every liquid-handling operation carries `error is not None`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:575-576`, `:725-726`, `:1066-1067`,
`:1270-1271`). A `SAFE` finding on it would claim the backend did not raise — which is A-COMPLETES
(`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:752`) applied to the *current*
operation rather than to its predecessors, and A-COMPLETES is an assumption the analyzer explicitly
does not discharge. Two options.

**(a) A scoped `SAFE`.** The report-level verdict is over the PLR precondition layer, and backend
outcomes are excluded, recorded as a `SoundnessScope` annotation. **`SoundnessScope` is NEW in this
increment** — there is no such type anywhere in `plr-sema/src/`. Main spec Open decision 2 is its
*motivation*, not its definition (round 1, C10/C18).

**(b) Never `SAFE` on such an operation.** The headline is unreachable by construction and the
increment's deliverable is the ledger delta alone.

> **Position: (a), with a disclosure that changes what the sprint can claim.** Option (b) is not a
> soundness position, it is a scope refusal: it says that because the analyzer cannot speak about the
> backend, it may not speak about PLR either. That is the same reasoning increment 5 §14.16 Q1 rejected
> when the user resolved *"build it if it is firable at all"*. The `error is not None` guard is a
> **re-raise of an exception the backend already produced**; it is not a PLR precondition, and the four
> `FAILURE_CATEGORIES` re-interpretations at
> `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:781-788` already draw exactly this line —
> `precondition_state` is "a derived guard is statically established to fire", which a backend re-raise
> is not.
>
> **What (a) means after round 1, stated so the position is not read as more than it is.** The
> tier-(iii) guard still emits a `Finding` — `UNKNOWN`, not `SAFE` and not nothing (below) — so (a)
> does not, in this increment, produce a joined `SAFE` on anything. What (a) buys is the *annotation*:
> the report records which sites were excluded from the PLR-precondition claim, so a later increment
> that can reach a joined `SAFE` inherits a scope statement rather than having to invent one. Option
> (b) would forgo even that.

> **Normative (the annotation).** `AnalysisReport` gains one optional field,
> `scope: SoundnessScope | None = None`. **`SoundnessScope` is a frozen dataclass with exactly one
> field, `excludes_sites: tuple[PlrSite, ...]`** — the guards classified tier (iii). It has no
> `excludes: frozenset[str]` field and no `FAILURE_CATEGORIES` member; the draft defined the dataclass
> twice in five lines with two different single fields, and `harness_internal`
> (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:781-788`: *"analyzer/plumbing bug; always
> paired with `reason="internal_error"`"*) has nothing to do with a backend re-raise (round 1, C10).
> `join` is unchanged and never sees the annotation.
> `schema_version` stays 1 (additive field, old readers unaffected —
> `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:3322-3326`'s additive direction).

> **Normative (a tier-(iii) guard emits ONE `Finding`, `Verdict.UNKNOWN`, `reason="guard_env_dependent"`
> — round 1, C9).** It *additionally* contributes its `site` to `excludes_sites`. §15.7 already defines
> `guard_env_dependent` as covering tiers (ii) **and** (iii) together, so no definition changes and no
> thirteenth vocabulary member is needed.
>
> **The draft's "no `Finding` at all" broke three shipped invariants and contradicted its own AC set.**
> AC-15.5(iv) asserts exactly `n` findings for `n` guards, while the draft's AC-15.6 said a tier-(iii)
> guard emits **none** — i.e. `n − k` — and neither fixture was scoped to exclude the other, so an
> implementer satisfies one and fails the other. `derive_contract`'s totality docstring — *"Every
> operation therefore receives at least one Finding downstream"*
> (`plr-sema/src/plr_sema/derive/__init__.py:499-503`) — plus the join's "zero findings ⇒ `UNKNOWN`"
> row mean an all-(iii) operation would become `UNKNOWN` **with no evidence** rather than
> `SAFE`-with-scope. And the ledger clusters *findings*
> (`plr-sema/eval/unknown_ledger.py:271-282`), so a suppressed guard is uncountable and §15.9's per-
> cluster block would be uncomputable for exactly the re-raise clusters.
>
> **The challenger's alternative — emit tier (iii) as `Verdict.SAFE` with a `detail` marker — is
> REJECTED as unsound and must not be implemented.** A `SAFE` at `:576` asserts the guard does not
> fire, i.e. that the backend did not raise. Under `join`, an operation whose other findings were all
> `SAFE` would then join to `SAFE`, claiming the operation cannot fail *including at the backend* —
> A-COMPLETES (`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:752`) applied to the
> current operation, which is exactly the claim this section exists to refuse.
>
> **Cost: none.** §15.5 already establishes that no joined `SAFE` is reachable this increment, so
> making tier (iii) yield `UNKNOWN` removes nothing the increment could have had. It also makes the
> coupling structural rather than incidental (§15.14 Q1).

> **Normative (the tier-1 soundness fence is left UNMODIFIED — round 1, C3; the draft's narrowing is
> DELETED).** The tier-1 unsoundness predicate stays exactly
> `unsound = (verdict == "safe" and outcome.startswith("raised")) or (verdict == "will_fail" and
> outcome == "ran_ok")` (`plr-sema/eval/oracle_common.py:645-647`), unmodified.
> `rows_excused_by_scope` is published as a **pure annotation with no threshold and no effect on any
> gate**, and **no `exc_class → PLR site` mapping is constructed anywhere in T32**.
>
> **Why the draft's narrowing had to go, and why deleting it is free.** The draft would have excused a
> `SAFE`-on-raise row when *"the executed exception's class is one the taxonomy maps to a `plr_site` in
> `excludes_sites`"*. A taxonomy does exist —
> `training/verify/data/plr_exception_taxonomy.json:1-29` carries 132 classes at the same pin, each
> with `trigger_sites` — but it covers **PLR-defined** classes only: it contains none of
> `TypeError`/`ValueError`/`RuntimeError`, which is what the benchmark actually raises, and none of the
> re-raise sites. Building the mapping would mean inventing it, and it **cannot be injective**: a
> re-raise carries the backend's own exception class, which is unbounded by construction, and
> `TypeError` alone is raised at `liquid_handler.py:375`, `:383`, `:498` and `:1770` — all PLR
> precondition sites — *and* re-raised at `:576`. Every `TypeError` row would be excusable, i.e. the
> narrowing excuses precisely the rows the fence exists to catch. The runtime side is no better:
> `exc_class = error.split(":", 1)[0].strip()` (`plr-sema/eval/oracle_common.py:368`) over
> `error = f"{type(e).__name__}: {e}"` (`training/verify/verifier.py:143-144`) — reliable as a class
> name, useless as a site — and **no traceback is captured anywhere**.
>
> **And the narrowing purchased nothing.** It bites only on `SAFE`-on-raise rows, and §15.5's own
> central finding is that no operation reaches a joined `SAFE` this increment. The draft was weakening
> its own fence to buy a result it simultaneously proves it cannot obtain. **§15.14 Q6 therefore
> answers itself: yes, it weakened the fence, and the weakening bought nothing.** The ~3-line
> `traceback.extract_tb(...)[-1]` capture that would make a site-keyed narrowing honest — available at
> the bare `except Exception as e` handler
> (`training/verify/verifier.py:143-144`) — moves to **increment 7**, where a joined `SAFE` first
> becomes possible and the fence actually needs the discrimination.

> **The finding that changes the sprint's target: Q1(a) does not produce a joined `SAFE`, because Q1
> and Q2 are coupled — and round 1 strengthened this rather than weakening it.** Scoping out tier (iii)
> leaves tier (ii). Every one of the ten methods in the benchmark carries tier-(ii) guards that no
> grammar decides — `pick_up_tips` carries five, all inherited from its delegates, starting with the `missing`-arguments raise (`liquid_handler.py:375`, `:383`, `:409`, `:321`,
> `:514`); `aspirate` and `dispense` carry those plus the lid pair (`:116`, `:117`) plus an unseeded
> volume cell; the `move_*` family carries an `unresolved_delegate` gap besides. Under `join`'s third
> row, one `UNKNOWN` makes the operation `UNKNOWN`
> (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:576-581`). **So the first joined `SAFE` on a
> real operation requires tier (ii), i.e. Q2 answered "ship it", and §15.6 recommends the opposite on
> evidence.** The two questions cannot be decided independently, and the plan's §3 treats them as if
> they could.
>
> **Two round-1 results make the coupling harder, not softer.** (1) The `(row_idx, op_id)` re-keying
> shows `_check_args`'s two tier-(ii) guards on **all 544** executed operations, so the coupling is now
> established per operation and not merely per method (§15.0). (2) With tier (iii) emitting `UNKNOWN`
> (above), every operation carrying a re-raise is `UNKNOWN` *by construction*, independently of tier
> (ii). The claim survives its own adversarial round.

> **APPROVED BY THE USER, 260907 — the headline is SUBSTITUTED** (recommendation was: substitute;
> `.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:262-265`).
> The question, in the plan's own stop-and-ask sense
> (`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:114-124` reserves that language for
> option (b)): *is "the first definite verdict on a real program" this sprint's deliverable, or
> increment 7's?* The honest answer this document can support is **increment 7's**, and the sprint's
> own deliverable is per-finding `SAFE`, a `WILL_FAIL` on a decidable and reachable violation, and a
> residual that names the missing observation per guard. That is a strictly smaller claim than the
> plan's headline. **The user took that answer on 260907**, so band B's and T31's claims are bounded by
> it: nothing in this sprint may be reported as a joined `SAFE` on a real operation, and the 260907
> grammar amendment does not change that — an `EnvRef` is ½, so an operation carrying one is `UNKNOWN`
> under `join` exactly as before (§15.4 E-ENV).

---

## 15.6 Q2 — does tier (ii) ship here or as increment 7?

> **Recommendation: DEFER to increment 7. #4981 is not started in this sprint.** The argument is not
> cost; it is that the cheap half does not work.

**The legitimacy question is settled in tier (ii)'s favour, and that is not the obstacle.** Increment 5
§14.6 records two failed `is_disabled` discharges: a second `env` member would be "a quantified claim
dressed as an observation" because a deck carries one tracker per well and per tip, and "no `.disable()`
appears in the program" is sound only if the graph is the whole world. **Neither objection applies to an
observation taken from the executed window.** `strictness`, the backend class, the deck's membership
and the head's channel count are single, observable facts about one run, and the harness already takes
`setup.snapshot()` before execution and returns `backend`. Increment 5 already built the pattern and the
cache-key partition that makes it honest (`plr-sema/src/plr_sema/check/ir.py:918-944`). So the
*mechanism* is available and legitimate.

**The obstacle is that the one cheap member decides nothing.** The plan argues `strictness` is "the
exact `does_volume_tracking` shape and costs one `env` member"
(`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:125-129`). It is not, and the reason is
two lines above the guard. `strictness == Strictness.STRICT` at
`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:382-383` sits inside
`if len(extra) > 0 and len(vars_keyword) == 0:` at `:381`, where
`extra = backend_kws - set(args.keys())` at `:380` and `args` comes from
`inspect.signature(method)` over the **backend's own bound method** at `:353-354`. Adding `strictness`
to `env` therefore converts a ½ into a ½: the enclosing scope entry is still tier-(ii) backend, so
E-UNCOND blocks `WILL_FAIL` and E-SCOPE cannot return `SAFE`. **The cheap member is gated behind the
expensive fact in the same guard's own scope.**

So tier (ii) is all-or-nothing here: to move either `:375` or `:383` — the two clusters that block
**all 544** operations (`outputs/plr-sema/unknown_ledger_260904_before.json:39-57`, `:86-104`) — the
increment must AST-derive the backend class's method signatures.

> **Round-1 correction to the cost argument (C17), which does not move the disposition.** The draft
> called that *"a whole increment's work"* and priced the **general** case while charging the
> **specific** one for it. On the frozen benchmark the backend is a single named literal class —
> `example.get("backend", "LiquidHandlerChatterboxBackend")`
> (`plr-sema/eval/oracle_common.py:362`) — not a surface, and its `pick_up_tips`/`aspirate`/`dispense`
> signatures are AST-derivable by machinery the derive package already runs over PLR. **The corrected
> reason for deferring is: the general derivation is a new class surface with its own measured
> selection and its own registry argument, AND this increment already carries more soundness risk than
> it can absorb** — round 1 conceded eight blocking items. Deriving over one benchmark backend would
> produce a fact that cannot enter the shipped contract table (which is keyed on PLR's own surface, not
> on a harness choice), i.e. a benchmark-local hack rather than increment 7's derivation. **DEFER
> stands**, alongside the `pred`-aware `BRANCH` the same evaluator serves (increment 3 §12.3.6 B2).
>
> **One passing fact from round 1 that reinforces E-UNCOND(5):** `:377-378`'s
> `if len(vars_keyword) > 0: return set()` makes `:381`'s second conjunct dead — an early-return fact
> the survey's trail records nothing about
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:377-381`).

**What defers with it:** the deck-membership observation (`:321`), the lid topology (`:116`/`:117`, and
increment 4 §13.1's lid disposition stands), the head channel count (`:409`), the well-seeding
observation that would move `volume_state_unknown`, and `can_pick_up_tip` (`:514`), which needs the
backend's *method body*, not just its signature.

---

## 15.7 Reasons

> **Normative — APPROVED BY THE USER 260907 (§15.14 Q4). `REASON_VOCABULARY` 10 → 12, of cap 12**
> (`plr-sema/src/plr_sema/verdict.py:133-168` enumerates the current ten; HM-14 is `CAPPED` at
> `declared=12`, `plr-sema/src/plr_sema/_hand_maintained.py:650-667`, so live 12 ≤ 12 and **no
> `declared` edit is needed**). This exhausts HM-14's headroom, which is why it is the user's call and
> not the sprint's. Two members:
>
> - **`guard_operand_unknown`** — the condition parsed to a non-`Opaque` predicate and every free name
>   resolved, but an **operand of this call** is ⊤: a non-literal kwarg, a kwarg `lower_calls` renamed
>   to `?<j>` (`plr-sema/src/plr_sema/check/ir.py:796-808`), or a `RESOURCE` whose declared `type`/
>   `element_type` cannot decide an `IsInstance`.
> - **`guard_env_dependent`** — the condition parsed, but ≥ 1 free name does not resolve to a call
>   operand or to an α/β binding at all: it names instance state (`self.<x>`), a module global, a
>   backend attribute, or a local the idioms decline; **or the guard's reachability is not established
>   — `depth >= 1` (E-UNCOND(4)), or a depth-0 empty trail in a `K` containing an earlier
>   `Return`/`Try`/`Raise` (E-UNCOND(5))**; **or the guard is a derived tier-(iii) re-raise** (§15.5).
>   This is tiers (ii) **and** (iii) together, plus round 1's two new give-up points.
>
> **The one-member fallback is DEAD (the user approved two on 260907), and is kept only as the record
> of what was offered.** It was: ship `guard_env_dependent` alone
> (`REASON_VOCABULARY` 10 → 11, one slot of headroom kept) and let `guard_operand_unknown`'s
> population fold into it. The cost would have been exactly the distinction that scopes increment 7 —
> *"the analyzer needs one observation it could take"* versus *"the analyzer needs one value this call
> did not carry"* — and, concretely, §15.9's GO gate would have lost one of its two zero-conditions and
> would have had to be restated over `guard_predicate_unparsed` alone, which is a weaker gate.
>
> **The 260907 amendment adds no member and needs none.** An `EnvRef` residual is precisely *"a free
> name resolves to state outside the call"* — the first clause of `guard_env_dependent`'s own
> definition above, of which `self.<x>` is the first example it names. What the amendment changes is
> that the analyzer can now say so about a shape it previously could not read at all; the vocabulary
> stays at the approved 12 and HM-14 stays at zero headroom.

**Against increment 1 §10.8's criterion, which is the right instrument.** That section's argument for
`channel_state_unknown` is that `guard_predicate_unparsed` means "could not be turned into a
predicate", which becomes a **false statement** for a guard the analyzer does parse, and that main spec
§0's rule requires a reason to name *which pipeline stage returned nothing* —
"the parse stage returned something; the *evaluation* stage did not"
(`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:992-998`). Both new members are
evaluation-stage give-up points and both are mechanical (they name our own give-up point, not a
semantic property), so §3.3's hand-maintenance justification carries over unchanged. They are
distinguishable from each other by a purely mechanical test — *did every free name resolve?* — which is
what keeps them from being one member split into two for appearance's sake (§9.4's anti-gaming
concern, `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2429-2431`).

**Three members were considered and rejected, each for a stated reason.**

- **`guard_predicate_opaque`: rejected.** `guard_predicate_unparsed` already means exactly that, and an
  `Opaque` predicate is precisely "could not be turned into a predicate". Adding it would be a rename
  costing a vocabulary slot. **`Opaque` keeps `guard_predicate_unparsed`**, which also makes the ledger
  delta legible: the residual `guard_predicate_unparsed` count *is* the grammar's coverage gap —
  **but only under the nested-`Opaque` rule below, which round 1 showed the draft needed and lacked,
  and only under G7's PLR-layer test on shape (2), which round 2 showed the amendment needed and
  lacked (A-C1).** Without that test a `self.<name>(…)` naming a method the closure could have inlined
  would leave `guard_predicate_unparsed` while gaining no coverage — ≥ 41 findings at this pin from
  `self._is_error_tail(response)` alone — and this sentence would be false in the same stroke.

> **Normative (nested `Opaque` — round 1, C15).** **A predicate containing ANY `Opaque` node is
> `Opaque` for reason-assignment purposes** (i.e. it keeps `guard_predicate_unparsed`), while still
> being **evaluated** under Kleene — so an `And` with an `F` conjunct still decides. Two lines, no
> vocabulary cost.
>
> **Without it the three-reason taxonomy has a hole, and §15.7's own legibility claim is false.**
> §15.3's own worked example creates it: `invalid_channels = [c for c in channels if c not in
> self.head]` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:405-409`) — α binds
> the term, the `if` clause parses `Opaque`, and every free name resolves. The guard
> `not len(invalid_channels) == 0` is then not `guard_predicate_unparsed` (the top node parsed), not
> `guard_operand_unknown` (no call operand is ⊤; the failure is syntactic, inside the comprehension),
> and not `guard_env_dependent` (the free name resolved via α). All three definitions exclude it, and
> there are **384 such findings** (`outputs/plr-sema/unknown_ledger_260904_before.json:133-140`).
> Under the rule they stay `guard_predicate_unparsed`, which is what makes the ledger delta a coverage
> measure a reader can interpret rather than an overstatement.

> **Normative (the `EnvRef` reason rule — new in the 260907 amendment, REORDERED in round 2 (A-C5); it
> AMENDS the worked example immediately above).** Reason assignment for a guard the predicate evaluator
> owns is a decision procedure over the two total predicate walks — **both applied to the
> α/β-substituted tree** (§15.2 G7) — in **exactly this order**:
>
> 1. **`contains_opaque` ⇒ `guard_predicate_unparsed`.** Unchanged. The nested-`Opaque` rule above is
>    unchanged. Any `Opaque` node anywhere still means *"the grammar failed here"*.
> 2. **Else, if an operand of *this call* is ⊤ ⇒ `guard_operand_unknown`.** Unchanged in content, moved
>    **ahead** of the `contains_env_ref` clause. **The gate has two zero-conditions and the amendment
>    may relax neither**; leaving the `EnvRef` clause first would have relabelled `self.backend.f(<x>)`
>    — where `<x>` is a non-literal kwarg, or one renamed to `?<j>` in the lowered `kwargs`
>    (`plr-sema/src/plr_sema/check/ir.py:796-808`) — as `guard_env_dependent` when §15.7's own
>    definition (above) says it is `guard_operand_unknown`. At this pin the exposure is nil, because O1
>    drives `guard_operand_unknown` to 0 everywhere
>    (`outputs/plr-sema/t30_measured_260905.json:1143-1146`); the rule is wrong independently of the
>    pin, and the shape it is wrong about — an `EnvRef` with `Term` arguments — is precisely the one
>    the amendment introduces. AC-15.5(iii) pins it with a fixture.
> 3. **Else, if `contains_env_ref` and the guard is still undecided ⇒ `guard_env_dependent`.**
>    The grammar **recognised** the read; what is missing is an observation, not a production. This is
>    the same member §15.5 already assigns to a derived tier-(iii) re-raise and to an unestablished
>    reachability, and it needs no new vocabulary slot: `REASON_VOCABULARY` stays at the approved 12.
> 4. Otherwise the existing rules stand: a free name resolving to nothing ⇒ `guard_env_dependent`;
>    decided ⇒ `SAFE`/`WILL_FAIL` with no reason at all.
>
> **`:409` is the worked example, and the amendment moves it from clause (1) to clause (3).** It does
> **not** stop at the reordered clause (2): `channels` is `_make_sure_channels_exist`'s own parameter
> at `depth == 1` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:405-409`), which
> E-CALL(depth) forbids resolving against the entry point's kwargs, so it is ⊤ and it is **not an
> operand of this call** — the two routes to `guard_env_dependent` here are independent, and the GO
> prediction survives even if the α-substitution clause were dropped. Before
> the amendment `invalid_channels = [c for c in channels if c not in self.head]`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:405-409`) bound its term under α
> while its `if` clause parsed `Opaque` — twice over, once for the `not in` comparator and once for
> `self.head` in predicate-operand position — so the nested-`Opaque` rule assigned
> `guard_predicate_unparsed` to all **384** of its findings
> (`outputs/plr-sema/t30_measured_260905.json:473-482`). After G7/G8 the filter parses to
> `Cmp(Var("c"), "not in", EnvRef(("self", "head"), None))`, `contains_opaque` is false,
> `contains_env_ref` is true, and the guard carries `guard_env_dependent`. **Nothing about the guard's
> truth value changed**: it was ½ before and it is ½ now.
>
> **This resolves an internal inconsistency the measurement found, and the resolution is by rule
> rather than by editing one table cell (§15.16 A1).** §15.9's prediction table said `:409` would carry
> `guard_env_dependent`; §15.7's nested-`Opaque` rule, whose own worked example was that very site,
> said `guard_predicate_unparsed`. Both statements were in spec_version 17 and they contradicted each
> other; T30's measurement reported the second
> (`outputs/plr-sema/t30_measured_260905.json:473-482`), correctly, because that is what the normative
> text said. The amendment makes them agree **in the direction §15.7's own definition supports** — the
> residual at `:409` names a missing observation (how many channels the head has), not a shape the
> grammar cannot read — and it does so by adding the production that makes the second statement true,
> not by relaxing the nested-`Opaque` rule, which is untouched and is still what fences the honest
> coverage measure.
- **A third member separating tier (iii) from tier (ii): rejected.** It would be a 13th and the cap
  conversation is the user's, not the sprint's
  (`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:130-131`). The (ii)/(iii) distinction is
  published in §15.9's measured set, where it belongs, rather than encoded in a wire vocabulary.
- **Shipping only `guard_operand_unknown`: considered, and rejected as the weaker option.** It would
  collapse "the analyzer needs one observation it could take" into "the analyzer needs one value this
  call did not carry", which is exactly the distinction the next increment is scoped by. **This is the
  cheaper fallback if the user declines to exhaust HM-14's headroom** (§15.14 Q4).

**Cap consequence, stated rather than buried: if the user approves, after this increment
`REASON_VOCABULARY` is at 12 of 12 and HM-14 has zero headroom.** Any future give-up point then needs
the cap conversation. Round 1's own argument for approving is that item 3's widening of
`guard_env_dependent` to cover unestablished reachability makes that member carry strictly more
traffic than the draft anticipated, which sharpens rather than blurs the distinction from
`guard_operand_unknown`.

---

## 15.8 Registry

**New rows: zero. Retired rows: zero. Per-row ceilings proposed to move: zero.** `live_rows()` is 24
(`plr-sema/src/plr_sema/_hand_maintained.py:957-961`) against `BUDGET_CAP = 24`
(`plr-sema/src/plr_sema/_hand_maintained.py:43`) before and after. Headroom 0, unchanged.

**The question the round must decide: does the local-binding idiom belong on HM-24 (ceiling 3 → 4) or
HM-25 (8 → 9)?** The registry's own criterion is silent-versus-loud: HM-24 is the pattern "whose
failure mode is a SILENT family collapse rather than a loud exact-count test failure"
(`plr-sema/src/plr_sema/_hand_maintained.py:841-896`), while HM-25's `breaks_when` records "Fails
LOUDLY here (unlike HM-24)" (`plr-sema/src/plr_sema/_hand_maintained.py:934-951`).

> **APPROVED BY THE USER, 260907 — HM-25 `declared` 8 → 9** (recommendation was: spend it;
> `.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:262-265`). The
> draft's position was *"neither row"*; round 1 broke the leg it rested on and the position is
> withdrawn. **α and β are filed as one HM-25 entry** — an "argument-default and filtered-comprehension
> binding shapes" pattern — with `breaks_when` naming **AC-15.2's exact floor as the loud test**.
> `live_rows()` stays 24 against `BUDGET_CAP = 24`
> (`plr-sema/src/plr_sema/_hand_maintained.py:43`, `:957-961`); **no row is added**, so no cap
> conversation is opened. AC-15.7 asserts HM-25 `declared == 9` unconditionally; the "if the user
> declines, α and β ship unregistered at `declared == 8`" branch is **dead** and is retained only in
> §15.14 Q5 as the record of what was asked.
>
> **Why HM-25 and not HM-24, which is what the challenger proposed.** The registry's criterion is
> silent-versus-loud. (1) HM-24's harm is a *silent family collapse* —
> *"the tip-requiring/tip-loading families silently empty"*
> (`plr-sema/src/plr_sema/_hand_maintained.py:874-880`). α's failure returns one guard to
> `guard_predicate_unparsed`, its pre-increment reason, and empties **no family**; there is no family
> here. (2) AC-15.2 publishes an exact floor that goes red on a PLR rewrite, which is HM-25's own
> criterion verbatim — *"Fails LOUDLY here (unlike HM-24) … exact-count/gate assertions … go red"*
> (`plr-sema/src/plr_sema/_hand_maintained.py:945-948`). (3) HM-25's `what` **already carries P3a** as
> `<p> = <p> or self.<x> or list(range(len(<q>)))`
> (`plr-sema/src/plr_sema/_hand_maintained.py:899-906`) — β's three-operand sibling, same idiom family,
> same row. The B1 precedent the challenger invoked went to HM-24 because *"R1 (§14.6) makes its
> `ast.For` node load-bearing for SOUNDNESS"* (`plr-sema/src/plr_sema/_hand_maintained.py:855-861`),
> which is a claim about a *loop-recognition* rule, not about a binding shape whose failure is a
> published count going red.
>
> **The draft's own reasoning, kept for the record, and where it fails.** Three reasons, in decreasing
> strength; **reason 1 no longer survives unqualified**.
>
> 1. **The failure mode is neither silent nor a collapse.** If PLR rewrites
>    `not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, TipSpot)]` as a `filter(...)` call
>    or a generator, α binds nothing, the term is `Opaque`, and the guard emits
>    `guard_predicate_unparsed` — **the pre-increment behaviour**, not a wrong verdict and not an
>    emptied family. Contrast HM-24's own `breaks_when`, whose harm is that "the tip-requiring /
>    tip-loading families silently empty". There is no family here to empty; there is a per-guard
>    coverage number.
> 2. **That number is a published gate, so the failure is loud by construction.** AC-15.2 requires the
>    complete α/β selection to be published with a floor, and AC-15.3 requires the per-op residual. A
>    PLR rewrite that broke α would move a published count and fail an exact-count assertion — which is
>    HM-25's *loud* criterion, not HM-24's, and having satisfied the loud criterion the pattern needs no
>    row to make it loud.
> 3. **α and β are Python language constructs, not PLR idioms** — a list comprehension with a filter,
>    and an `or`-chain default — which is verbatim the argument increment 5 §14.11 already accepted for
>    B2 and P1c (`.praxia/docs/specs/260903_plr-sema-volume-increment.md:930-934`). The one place that
>    argument is genuinely weaker here is β's `[<expr>] * len(<p>)` tail, which is closer to an idiom;
>    β binds **only a length** and declines the three-operand form outright, so the surface it claims is
>    smaller than P3a's, which is already on HM-25.
>
> **What round 1 attacked, and what it found.** The draft nominated reason 3 as its weakest and rested
> on reason 1. Round 1 went at reason 1 instead and broke it two ways. (a) The single-write clause
> covered `x` but not the **iterand**, so a PLR rewrite that moved a comprehension below a rebinding of
> its own `iter` would leave α matching and binding a term over the *wrong* sequence — a wrong verdict,
> silently, with no published count moving. (b) The **delegate→caller substitution** is unspecified, so
> α's terms are matched in the delegate's namespace and evaluated against the entry point's kwargs,
> which works today only by name coincidence. §15.3's iterand clause repairs (a); §15.4's
> E-CALL(depth) forbiddance repairs (b) — **but only because both were written down in this
> revision**, and "reason 1 holds *given two new normative clauses*" is not the same claim as "reason 1
> holds". **Hence the row.** The correct disposition is HM-25 8 → 9, a per-row ceiling spend the user
> had to approve before it was spent
> (`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:132-135`) **and did approve on 260907**;
> AC-15.7 asserts HM-25 `declared == 9` and HM-24 `declared == 3` — the reverse of the draft's
> assertion. **T31 is the row that spends it** (§15.12), which is why band B's derive work could and
> did proceed first: it spends nothing.

> **Normative (the amendment's own registry disposition — CONCEDED in round 2, A-C6: the productions
> are NAMED inside the HM-25 entry α and β already spend, and `_measure_hm25` must import them; no
> second row, no further ceiling).** The spec_version 18 position was that `EnvRef`, `Zip` and the
> membership comparators need no registry mention at all, resting on reason 1 below. **Round 2 broke
> reason 1 against the shipped registry and it is withdrawn as the sole argument**; the fallback
> §15.8 stated in advance is now the disposition.
>
> 1. ~~**They are derived by the total `parse`, over Python syntax, not over PLR idiom.**~~
>    **WITHDRAWN (A-C6).** The claim was that `EnvRef`'s trigger is the language's own `self`
>    convention plus `ast.Attribute`/`ast.Call`, `Zip`'s the builtin `zip`, and the comparators
>    `ast.In`/`ast.NotIn` — so the same argument §15.8 reason 3 makes for α and β. **HM-25's own `what`
>    refutes it**: it already books **P8**, *"zip-comprehension operand-pairing idiom (an
>    `ast.ListComp`/`GeneratorExp` over a `zip(...)`-bound element call)"*
>    (`plr-sema/src/plr_sema/_hand_maintained.py:918-920`, user-approved 260904) — G8's `Zip`
>    production is a `GeneratorExp` over `zip(...)`, the same shape with the opposite disposition — and
>    **P3a**, *"the channel-default idiom (`<p> = <p> or self.<x> or list(range(len(<q>)))`)"*
>    (`plr-sema/src/plr_sema/_hand_maintained.py:904-906`), which is a `self.<x>` recognition. The
>    registry's own criterion, applied to essentially these two shapes, has already produced entries;
>    the amendment cannot both cite `_hand_maintained.py:945-948` as its authority and exempt itself
>    from what that authority already booked.
> 2. **The failure mode is loud and already measured.** §15.9 block (1) publishes parse coverage per
>    atom kind over the whole contract table — 2,805 distinct guard sites, 313 `Opaque` at the
>    pre-amendment measurement (`outputs/plr-sema/t30_measured_260905.json:3-20`) — and blocks (3)/(4)
>    now publish `n_env_ref_nodes` / `n_env_ref`, `n_env_ref_refused_plr_layer` and the top-10
>    `EnvRef` paths. A PLR rewrite that moved these shapes
>    breaks a published count, which is HM-25's own loud criterion
>    (`plr-sema/src/plr_sema/_hand_maintained.py:945-948`), not HM-24's silent one.
> 3. **There is no list to maintain.** The one design that *would* have created hand-maintained
>    surface — matching `EnvRef.path` against a table of known receiver attributes — is forbidden
>    outright by §15.4 E-ENV. A production that recognises a shape and returns ½ has nothing to go
>    stale.
>
> **The fallback was stated in advance so the adversarial pass would have a landing place rather than
> a veto; the pass landed on it, and it is now NORMATIVE (round 2, A-C6).** `EnvRef`, `Zip` and the
> `in`/`not in` comparators are **named inside the HM-25 entry α and β already spend** — the entry's
> `what` becomes "argument-default, filtered-comprehension and environment-read recognition shapes" —
> which costs **no further ceiling**: HM-25's `declared` stays **8 → 9** by the user's approval,
> `live_rows()` stays 24 against `BUDGET_CAP = 24`
> (`plr-sema/src/plr_sema/_hand_maintained.py:43`), and AC-15.7's assertions are unchanged. It is
> **not** a second row and **not** a second ceiling spend; either of those is a user decision and not
> this amendment's to take.
>
> > **Normative (the entry's measure must track its `what` — round 2, A-C6's second-order defect).**
> > `_measure_hm25` measures HM-25 by **importing the symbols that implement its patterns** — five
> > shape matchers plus three `atom_truth` productions, returning
> > `len(shape_matchers) + len(productions)`, so it *"fails loudly, `ImportError`/`AttributeError`, if
> > any is deleted"* (`plr-sema/src/plr_sema/_hand_maintained.py:300-351`). **Naming three more
> > patterns in the `what` without adding measured symbols would leave three live patterns the measure
> > cannot see**, so `test_no_surface_exceeds_its_declared_size` passes while the row silently
> > undercounts — which is HM-24's *silent* criterion, the exact failure mode §15.8 argues these
> > productions do not have. **Normative for T31's registry spend: `_measure_hm25` must additionally
> > import the production symbols — `EnvRef`, `Zip`, and the membership branch of `_CMP_OPS`
> > (`plr-sema/src/plr_sema/derive/predicate_ast.py:298-305`) — so the measure moves when the `what`
> > does.**
> >
> > **The contingency, surfaced now rather than at T31.** The measure returns a **count**, and the
> > entry's `declared` is 9. If, with the production symbols added, the measured pattern count for
> > HM-25 **exceeds 9**, that is a further ceiling spend and therefore **a user decision, surfaced at
> > T31 before the spend, not discovered after it**. T31 must not raise `declared` past 9 on its own
> > authority; it must stop and ask.

**`cache_key` gains no component, and the whole cache goes cold anyway — round 1, C16.** Its `env`
element already exists and is already the fifth (`plr-sema/src/plr_sema/check/ir.py:918-953`); this
increment adds no component and threads no new value. But `contracts_sha` is
`sha256(contracts_json)`, computed at `plr-sema/src/plr_sema/check/ir.py:946`, and T30 **regenerates
`plr-sema/data/derived_contracts.json`** to add `predicate` and `param_defaults`. **So every key moves,
for every caller, not just the benchmark: the cache is cold after T30 by design.** O1 additionally
moves `bc_hash` for the benchmark, for the same reason. The draft's *"every key it produces is
byte-identical to today's"* was false and sat in the same paragraph as "the benchmark's keys move".
**The property that actually matters is that `env` is untouched** — no partitioning, no correctness
event, a full re-computation. T30's gate includes checking that no test pins a literal `cache_key`.
Under Q2-defer, `strictness` never enters `env`.

---

## 15.9 Measured sets (band B, T30)

> **Normative (the report file names, corrected against what band B actually wrote; 260907, extended
> in round 2 for the landed population re-run).** There are now **three** reports and each means
> something different:
>
> 1. **`outputs/plr-sema/t30_measured_260905.json`** — the first measurement, the one that recorded
>    NO-GO. The draft's text said `t30_measured_260904.json` and no such file was written (§15.15's
>    T30 row, divergence 3).
> 2. **`outputs/plr-sema/t30_measured_260907.json`** — the **population re-run**, commit `15b84d31`.
>    Fix-up (1) below has **already landed**: `t30_measure.py` now sources the executed set from
>    `oracle_replay.main()` itself via `collect_executed_population`
>    (`plr-sema/eval/t30_measure.py:19-38`, `:550`), and the measured population is **544 /
>    `pick_up_tips` 223**. The named cause of the earlier 923 / 361 is recorded in the script's own
>    docstring: `row_to_verifier_inputs` was called **without** the sidecar's `ambiguity_class`, which
>    directly sets `skip_reason` there, so every non-`"clean_parse"` row `run_row` would have skipped
>    was silently admitted (`plr-sema/eval/t30_measure.py:25-35`). This report carries **no** amendment
>    effect — the grammar is unchanged in it.
> 3. **`outputs/plr-sema/t30_measured_260908.json` or later** — the amendment's own re-measurement,
>    produced by **T35** after the grammar lands, and **the GO/NO-GO that decides whether T31 starts is
>    the one recorded there.**
>
> All three are kept. The amendment's evidence is the delta between (2) and (3) — same population,
> different grammar — and **not** the delta between (1) and (3), which confounds the two changes. No
> number from an earlier report is republished as if it were a later one.

> **Normative.** The measured report publishes, computed over the whole
> `plr-sema/data/derived_contracts.json` and over the frozen benchmark's own lowered IR calls (via
> `lower_row_calls`, `plr-sema/eval/oracle_common.py:551-571`, with no analyzer change and no
> `check_ir` invocation):
>
> 1. **Parse coverage.** Of all guards in the contract table: the count parsing to a non-`Opaque`
>    predicate, broken down **per atom kind** (`Cmp`, chained `Cmp`, `Is`, `IsInstance`, `AllOf`/
>    `AnyOf`, `SetOf`-uniqueness, `Filtered`-emptiness, `TRUE`), and the count remaining `Opaque` with
>    the ten most frequent unparsed shapes named.
> 2. **Binding coverage.** The complete set of `(K, x, idiom, term)` tuples α and β bind, and the count
>    of guards with ≥ 1 free local of which every / some / no local binds. **Plus two counts round 1
>    requires**: (i) the number of executed `pick_up_tips` operations for which `channels_for_call`
>    returns non-`None` (D2, floor `== 223`), and (ii) the number of depth-≥1 guards whose free vars
>    *would* have resolved by name coincidence against the entry point's kwargs had E-CALL(depth) not
>    forbidden it (item 13), so the size of what is forgone is on the record.
> 3. **Per ledger cluster** (all 54): the predicted tier, `parsed?`, `bound?`, and **the reason the
>    guard ACTUALLY carries** after §15.7. §15.1's (i)/(ii) tiering is a prediction; this block is the
>    measurement, and any divergence between them is published rather than absorbed. **Amendment
>    additions**: **`n_env_ref_nodes`** — the number of `EnvRef` **nodes** in that cluster's
>    α/β-substituted predicate (renamed from `n_env_ref` in round 2, A-C8: block (3) and block (4)
>    published the same name in two different units, and `:2055` — one guard, two nodes — is the cell
>    where that bites) — and `env_ref_paths`, the dotted paths themselves, so a reader can see exactly
>    what the production absorbed, per site, without reading this document.
> 4. **Per executed operation**: the residual **reason set**, plus the residual tier set as a published
>    annotation, plus — separately — the count of guards on that operation that are `parsed but
>    operand-unknown`, so a residual caused by a missing declared type is distinguishable from a
>    genuinely environmental one. **Amendment additions**: `n_env_ref` — **per-guard, and this block is
>    the only place that name carries that unit** (round 2, A-C8): the number of guards on that
>    operation whose α/β-substituted predicate contains ≥ 1 `EnvRef` node; and
>    `n_decided_via_env_ref_shortcircuit`, the number of guards that reach a definite value only
>    because an `EnvRef`-containing compound short-circuited over an already-decidable conjunct
>    (§15.4 E-ENV), predicted **0**. **No sibling counters for the vacuous-`Zip` and membership paths
>    are published, because round 2 closed both by rule rather than by measurement** (§15.4 E-ENV) —
>    that is the point of the theorem, and a counter for a path the semantics forbids would be
>    theatre.
> 5. **The O1 delta**: (4) computed twice, with and without §15.4's operand observation. If the two
>    differ by zero, O1 is not doing what §15.4 claims and the gate is re-opened.
> 6. **The amendment's own surface (new, 260907; one field added in round 2).** Over the whole contract
>    table: the **top-10 `EnvRef` paths by occurrence** with their counts; `n_env_ref_guards` and
>    `n_env_ref_nodes`; `n_zip`; `n_membership_cmp`; **`n_var_self`, asserted `== 0`** (§15.2's
>    `Var("self")` invariant); `n_opaque_only_by_var_self`, the guards that are `Opaque` *only* because
>    that invariant fired, predicted **0** and published rather than assumed; and — **new in round 2,
>    A-C1 — `n_env_ref_refused_plr_layer`**, the number of shape-(2) candidates refused by G7's
>    PLR-layer test, i.e. `self.<name>(…)` calls whose `<name>` is an indexed method of the receiver
>    class. **This is the field that keeps the top-10 path list interpretable**: without the test those
>    calls would have populated it, and with the test their count is visible instead of invisible. It
>    is predicted **non-zero** — `self._is_error_tail(response)` alone contributes 41 condition strings
>    to the contract table, and `:1778`/`:1940`'s
>    `not self._check_96_head_fits_in_container(container)` two more. Block (1)'s `top10_unparsed_shapes` is
>    republished so the shapes the amendment did **not** absorb stay visible: at the pre-amendment
>    measurement two of the ten are membership tests over a `self` chain and three are `self`-rooted
>    but subscripted or arithmetic (`outputs/plr-sema/t30_measured_260905.json:21-62`), and the second
>    group must still be `Opaque` afterwards.
>
> **Normative (the gate is stated over REASONS, not over tiers — round 1, C8).**
>
> > **GO iff ≥ 1 executed real operation carries ZERO findings whose `reason` is
> > `guard_predicate_unparsed` and ZERO whose `reason` is `guard_operand_unknown`** — i.e. every guard
> > on it is either decided (`SAFE`/`WILL_FAIL`), or undecided because a free name resolves to state
> > outside the call (`guard_env_dependent`), or a derived tier-(iii) re-raise (which also carries
> > `guard_env_dependent`).
>
> NO-GO otherwise: publish the counts and the structural reason in §15.15, keep the derive code (it is
> a strict information gain on the contract table either way), and bring the decision to the user
> before the evaluator lands.
>
> **Why not the draft's tier formulation.** The draft's *"residual tier set ⊆ {(ii), (iii)}"* has no
> mechanical referent: there is no `tier` field among `InlinedGuard`'s nine
> (`plr-sema/src/plr_sema/derive/__init__.py:491-499`; re-anchored in round 2, A-C11), none in
> `derived_contracts.json`, and §15.1's
> tiering is a table in a Markdown document. Either the measurement script transcribes that table — in
> which case the gate is this document's own prediction restated as a measurement, and §15.9's framing
> *"to be falsified by the measurement and not assumed by it"* is unsatisfiable — or the tier is
> derived. **The obvious derivation is worse.** *"Condition parses non-`Opaque` ∧ all free names
> resolve ⇒ (i); else (ii)"* makes every guard this increment fails to decide (ii) by construction, so
> every operation's residual is ⊆ {(ii), (iii)} trivially and the gate **always passes**. Reasons are
> shipped (`plr-sema/src/plr_sema/verdict.py:133-168`), mechanical, and non-tautological: a guard
> carries `guard_predicate_unparsed` iff the grammar failed on it, which is exactly the thing the gate
> is trying to see. **The gate number must be computable from the measured JSON without
> reading this document.**

> **Normative (the anti-gaming argument for `EnvRef`, stated because the gate's zero-condition is
> exactly what the amendment relaxes; 260907).** The GO gate requires **zero**
> `guard_predicate_unparsed` findings on some executed operation, and it requires that *because*
> `guard_predicate_unparsed` is the reason that means "the grammar failed here". An amendment that
> converts that reason into `guard_env_dependent` is, structurally, an amendment that makes the gate
> easier to pass — so the burden is on this box, and the three-sentence form is:
>
> **`EnvRef`'s reach is MEASURED, not asserted — and it is fenced away from PLR-layer code by a
> derived test** (round 2, A-C1). The spec_version 18 form of this sentence was *"`EnvRef` is
> syntactically narrow and has no fallback … so no arbitrary text can reach it"*, and **that sentence
> is withdrawn**: `plr-sema/data/derived_contracts.json` carries **210** condition strings containing a
> `self.`-rooted call expression, of which **41** are the single shape `self._is_error_tail(response)`
> — which spec_version 18's shape (2) admitted verbatim, and which reads no receiver state, is not
> tier (ii) by §15.1's definition, and is a coverage gap the closure could have inlined. The replacement
> is a rule plus two published numbers: G7 shape (2) admits a `self`-rooted call **only** through a
> receiver attribute (`len(path) >= 3`) or when its length-2 name is **absent from the derive package's
> own PLR function index** for the receiver class; shape (1) is unchanged and keeps subscripts,
> arithmetic and non-`self` receivers `Opaque` by the closed negative list; and both
> `n_env_ref_refused_plr_layer` and the top-10 `EnvRef` path list are published so a reader can check
> the reach rather than take this box's word for it. **`EnvRef` decides nothing — and after round 2
> that is a theorem, not a prediction** (§15.4 E-ENV): E-ENV fixes it at ½/⊤ unconditionally, it can
> neither satisfy E-UNCOND nor produce an E-SCOPE `SAFE`, the **vacuous-`Zip`** path is closed by the
> `Zip`-resolution rule (a ⊤ seq quantifies to ½, never vacuously `T`), the **membership deciding
> case** is deleted outright, and the **only** remaining path to a new definite value — Kleene
> short-circuit over an *already decidable* conjunct — is published as
> `n_decided_via_env_ref_shortcircuit` and predicted 0. **`EnvRef`'s count is published
> and is excluded from every success measure** — per cluster, per operation and by path (blocks (3),
> (4), (6)), under `guard_env_dependent`, which §15.10 and AC-15.8 already exclude from "converted"
> and which the gated number `n_findings_decided` already ignores.
>
> **The gate's SECOND zero-condition is relaxed by nothing, and round 2 is where that is said (A-C5).**
> `guard_operand_unknown` is the other reason the gate requires to be zero, and §15.7's reason rule as
> first written put `contains_env_ref` **ahead** of the operand test, which would have relabelled a
> `self.backend.f(<⊤ operand>)` guard `guard_env_dependent`. The clauses are reordered — operand test
> first — so the amendment relaxes neither zero-condition, and AC-15.5(iii) pins it.
>
> **Two further properties make the relaxation checkable rather than trusted.** (a) The amendment
> cannot move `n_findings_decided`: a reader who suspects the gate was bought rather than earned can
> compare the two reports' `n_findings_decided` and `guard_env_dependent` counts and see that the
> first is unchanged while the second absorbs exactly the flipped findings. (b) The amendment is
> **falsifiable per site**: §15.9's re-prediction below names, for every candidate method, which
> `guard_predicate_unparsed` members flip and which do not: of the **ten** blocker sites the
> measurement named, exactly **three flip** (`:409`, `:514`, `:2055`) and **seven do not** (`:116`,
> `:657`, `:1778`, `:1940`, `:2030`, `:2211`, `:2226`). An `EnvRef` that had become a sink for
> arbitrary opaque text would have flipped all ten. **`:1778`/`:1940` moved from the flip column to the
> no-flip column in round 2** (A-C1): `self._check_96_head_fits_in_container(container)` is a length-2
> `self.<name>(…)` naming an indexed `LiquidHandler` method, so G7's PLR-layer test refuses it and it
> stays `Opaque` — which is the right answer, because its body
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1684-1693`) is pure arithmetic
> over its own argument and reads no environment at all. **The amendment got strictly narrower under
> adversarial pressure, and the number that moved is a published one.**

**Round 1's prediction table, kept as the record of what was predicted BEFORE band B measured — it was
falsified on one row and that is what the amendment exists for.** The `pick_up_tips` row predicted
`{guard_env_dependent}` ⇒ GO; the measurement returned the residual reason set
`decidable+guard_env_dependent+guard_predicate_unparsed` on every `pick_up_tips` occurrence
(`outputs/plr-sema/t30_measured_260905.json:1045-1051`), and the `gate` block records `go` false for
both the with-O1 and the without-O1 computation
(`outputs/plr-sema/t30_measured_260905.json:1149-1162`). Every other row's prediction held.

| method | ops | predicted residual (reasons) | the guards that must clear, and how |
|---|---|---|---|
| **`pick_up_tips`** | 223 | **{`guard_env_dependent`} — GO** | `liquid_handler.py:498` clears (α + O1 + restated E-TYPE ⇒ `IsInstance` `T` ⇒ `Not` `F` ⇒ `AnyOf` `F` ⇒ `SAFE`); `:502` clears (G4 + `channels_for_call`, **conditional on D2**); `:522` clears (G2 + β + E-CALL(β) + `channels_for_call`); `:514`/`:375`/`:383`/`:409`/`:321` are `guard_env_dependent`; `:576` is derived (iii) ⇒ `guard_env_dependent` + `excludes_sites`; `:535` is already decided |
| `transfer` | 19 | {`guard_predicate_unparsed`} — NO-GO | `:1335`/`:1337`/`:1340` **now clear via D1's `param_defaults`** (they did **not** on the grammar alone), but `transfer` inherits `aspirate`'s `:990` and `dispense`'s `:1202`, which need γ |
| `aspirate` | 77 | {`guard_predicate_unparsed`} — NO-GO | `:959` clears; **`:875` does NOT** (E-CALL(depth) forbids the depth-1 resolution); `:990` needs γ; `:117` is `guard_env_dependent` under E-UNCOND(5) |
| `dispense` | 40 | {`guard_predicate_unparsed`} — NO-GO | `:1153` clears; **`:1185`/`:1188` do NOT** (β binds no elements, C6); `:1202` needs γ |
| `drop_tips` / `discard_tips` | 65 | {`guard_predicate_unparsed`} — NO-GO | `:666` binds `tips` by loop-append and `:657` is a numeric `Cmp`; both fail closed (§15.1.2). `:647` is now `½` rather than a **false `WILL_FAIL`** (C4) |
| `stamp` | 27 | {`guard_predicate_unparsed`} — NO-GO | `containers` is branch-bound (§15.1.4); `:1770`/`:1920` are `guard_env_dependent`, not false `WILL_FAIL` |
| `move_resource` / `move_lid` / `move_plate` | 93 | out of scope — `unresolved_delegate` (§15.0) | `:2092` is derived (iii) |

**The re-prediction under the 260907 amendment as revised in round 2, per candidate method, with the
measured blocker named and its disposition argued from its own syntax.** Operation counts are the
ledger's frozen population (§15.0). **The last column is a `guards / nodes` pair, in the two units
blocks (4) and (3) respectively publish** (round 2, A-C8 — one name in two units was the defect):
`guards` is block (4)'s per-operation `n_env_ref`, the number of that operation's guards whose
α/β-substituted predicate contains ≥ 1 `EnvRef` node; `nodes` is the sum of block (3)'s
`n_env_ref_nodes` over those guards. **Hedged ranges are gone** — each cell is either an exact pair or
the words *not predicted*, because a hedged cell is unfalsifiable in exactly the place the ambiguity
bit. Every cell is a prediction for **T35** to falsify.

| method | ops | measured blocker(s) carrying `guard_predicate_unparsed` | flips? | re-predicted residual | expected `n_env_ref` guards / nodes |
|---|---|---|---|---|---|
| **`pick_up_tips`** | 223 | `:409` `not len(invalid_channels) == 0`, whose α-bound filter is `c not in self.head`; `:514` `not all(self.backend.can_pick_up_tip(channel, tip) for channel, tip in zip(use_channels, tips))` | **both** — G8's `not in` + G7 shape (1) under the α-substituted walk; G8's `Zip` + G7 shape (2), admitted because `("self", "backend", "can_pick_up_tip")` has length 3 | **{`decidable`, `guard_env_dependent`} ⇒ GO** | **2 / 2** |
| `drop_tips` / `discard_tips` | 65 | `:657` `tip.tracker.get_used_volume() > 0 and (not allow_nonzero_volume)` (`outputs/plr-sema/t30_measured_260905.json:763-772`) | **no** — rooted at the local `tip`, not at `self`; the closed negative list's "call rooted at a parameter or local" row | {`decidable`, `guard_env_dependent`, `guard_predicate_unparsed`} — NO-GO | **1 / 1** (`:409` only, reached via `self._make_sure_channels_exist(use_channels)` at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:665`) |
| `aspirate` | 77 | `:116` `lidded is resource` (`outputs/plr-sema/t30_measured_260905.json:543-552`) | **no** — an `is` comparison whose RHS is not the constant `None`, so it is not the `Is` production; no `self` anywhere in it | {…, `guard_predicate_unparsed`} — NO-GO | **1 / 1** (`:409`, via `self._make_sure_channels_exist(use_channels)` at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:980`) |
| `dispense` | 40 | `:116`, as `aspirate` | **no** | NO-GO | **1 / 1** (`:1185` only — `dispense` does **not** reach `:409`; `_make_sure_channels_exist` has exactly three call sites, `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:521`, `:665`, `:980`, and none is in `dispense`) |
| `transfer` | 19 | `:116`, inherited | **no** | NO-GO | **not predicted** — it certainly contains `:409` (inherited from `aspirate`) and `:1185` (from `dispense`), so ≥ 2 / ≥ 2, but this document has not enumerated `transfer`'s full closure and will not publish a number it cannot derive |
| `stamp` | 27 | `:116`; `:2030` `(source.num_items_x, source.num_items_y) == (target.num_items_x, target.num_items_y)` (`outputs/plr-sema/t30_measured_260905.json:953-962`); `:1778`/`:1940` `not self._check_96_head_fits_in_container(container)` (`outputs/plr-sema/t30_measured_260905.json:873-882`) | **none** — round 2 moved `:1778`/`:1940` to no-flip (A-C1: a length-2 `self.<name>(…)` naming an indexed `LiquidHandler` method, refused by G7's PLR-layer test, and its body reads no receiver state); `:116` and `:2030` do not flip either — a tuple *display* is not a `Term` in G1 and the amendment adds none | NO-GO | **0 / 0** — and both refused calls appear in `n_env_ref_refused_plr_layer` instead |
| `move_resource` / `move_lid` / `move_plate` | 93 | `:2055` `self.setup_finished and (not self._resource_pickups)` (`outputs/plr-sema/t30_measured_260905.json:613-622`); `:2211` `resource_rotation_wrt_destination % 180 != 0`; `:2226` `destination.resource is not None and destination.resource is not resource` | `:2055` **flips** (two `EnvRef` leaves in predicate position — the shape the unamended walk had no production for); `:2211` does not (an arithmetic `BinOp` is not a `Term`); `:2226` does not (`is not resource`) | out of scope regardless — `unresolved_delegate` (§15.0) | **4 / 5** — `:2055` (1 guard, 2 nodes) plus the three single-leaf `self._resource_pickup` guards (`outputs/plr-sema/t30_measured_260907.json:625`, `:645`, `:655`). **This is the cell the A-C8 unit collision was hiding**: the old "4–5" was one count under each definition, not a range |

**Three predictions in that table are about reasons that do NOT change, and they are the ones worth
attacking first.** (1) `volume_tracker.py:92`/`:105` are the volume family's, by the dispatch rule
(§15.2), and keep `volume_state_unknown` — the pre-amendment measurement reported
`guard_predicate_unparsed` for them
(`outputs/plr-sema/t30_measured_260905.json:733-742`), which is the family-dispatch fix-up below, not
an amendment effect; either way they are not one of the gate's two zero-conditions, so
`aspirate`/`dispense` are blocked by `:116` alone. (2) `:1185`'s `self._blow_out_air_volume is None`
already parsed and was reported `decidable_or_operand_dependent`
(`outputs/plr-sema/t30_measured_260905.json:803-812`); under G7 it becomes
`Is(EnvRef(("self", "_blow_out_air_volume")), negated=False)` and its reason is predicted to **change
to `guard_env_dependent`** — a prediction that would be a *regression* if `EnvRef` were merely
cosmetic, and that is instead the `Var("self") ∈ K_params` defect being fixed. (3) `n_findings_decided`
is predicted **unchanged** by the amendment alone.

> **Normative (two measurement fix-ups that must land BEFORE the re-measured numbers are cited;
> 260907). Neither changes the NO-GO that was recorded, and that is why they are fix-ups rather than
> corrections.**
>
> 1. **The population — LANDED, commit `15b84d31`, report
>    `outputs/plr-sema/t30_measured_260907.json` (round 2 update).** `t30_measure.py`'s row loop was a
>    *"deliberately MINIMAL re-implementation"* of `run_row`'s skip/no_call gating and counted **923**
>    operations — `pick_up_tips` **361** (`outputs/plr-sema/t30_measured_260905.json:1045-1051`,
>    `:1067`) — where the ledger's frozen benchmark population is **544** and 223 (§15.0). The
>    executed-op population is now sourced from `oracle_replay.main()` itself, via
>    `collect_executed_population` and the `FINDINGS_SINK`/`LOWERED_SINK` seams
>    (`plr-sema/eval/t30_measure.py:19-38`, `:550`), and `--sidecar`/`--crosscheck` are REQUIRED. **The
>    named cause is recorded** (`plr-sema/eval/t30_measure.py:25-35`): `row_to_verifier_inputs` was
>    called without the sidecar's `ambiguity_class`, which directly sets `skip_reason` there, so every
>    non-`"clean_parse"` row (`missing_slot`/`ambiguous_referent`/`out_of_surface`) that `run_row`
>    would have skipped was silently admitted. The per-site classification in block (3) is
>    population-independent, which is why the NO-GO stands as recorded; every *ratio* and every per-op
>    count in block (4) is not. **The amendment's delta is therefore taken against
>    `t30_measured_260907.json`, not against `t30_measured_260905.json`** — same population, one
>    change.
> 2. **Family dispatch in blocks (3) and (4).** The classifier assigns a predicate reason to guards the
>    tip and volume families own, contradicting §15.2's dispatch rule: it reported a predicate reason
>    for `volume_tracker.py:92` and `:105` — `guard_predicate_unparsed` — where the ledger's own reason
>    is `volume_state_unknown` (`outputs/plr-sema/t30_measured_260905.json:733-742`). **T35** must skip
>    family-claimed guards and report the family's own reason, exactly as T31's evaluator will. Without
>    this, `aspirate`/`dispense` residuals name a blocker the predicate evaluator never owned.
>
> **A third number will move for a stated reason, and it is not a fix-up.** Block (2)'s
> `name_coincidence_exposure_count` is **936**, and its published examples include entries whose
> exposed name is literally `self`
> (`outputs/plr-sema/t30_measured_260905.json:86-103`) — the same `Var("self")` defect §15.2's
> invariant closes. After the amendment those occurrences cease to exist, so the count is **predicted
> to fall**, and the fall must be attributed to the invariant rather than read as E-CALL(depth)'s
> forbiddance having narrowed.

**So the gate rests on `pick_up_tips` alone, and it now has three points of failure, not one.** All
three are measurable in T30 **before** T31 constructs a single verdict, which is exactly what the
ordering gate above exists for:

1. **O1's element walk must yield `"TipSpot"`** for `tip_spots`' cells. If it does not, `:498` is ½,
   `pick_up_tips` keeps a `guard_operand_unknown` residual, and the increment is NO-GO on every
   operation. §15.9(5) measures O1's effect directly rather than assuming it. O1 is ~40 LOC (§15.4),
   not the ~25 the draft claimed.
2. **`channels_for_call` must return an exact tuple on 223 real rows** (D2). `:502`'s
   `len(set(use_channels)) == len(use_channels)` clears only then. The path for `pick_up_tips` is
   `channel_default_param["pick_up_tips"] == "tip_spots"` → `call.kwargs["tip_spots"]` must be an
   `ir.Seq` → `tuple(range(len(items)))`
   (`plr-sema/src/plr_sema/check/tipstate.py:262-269`); that should hold, since `tip_spots` is a
   trusted param and so is not renamed `?<j>` (`plr-sema/src/plr_sema/check/ir.py:796-808`). **But no
   number anywhere covers the tier-1 benchmark**, and `tipstate.py` itself records that *"the shipped
   fixture's operations never resolve an exact channel set"*
   (`plr-sema/src/plr_sema/check/tipstate.py:551-565`). If the measured count is 0 the gate fails on
   `:502` for a reason unrelated to the grammar, and without this block §15.9 would have misattributed
   it to O1.
3. **`tip_spots` must lower as an `ir.Seq`**, which (2) depends on and which block (2) also exposes.

**Measured (T30): all three points of failure held, and the gate failed on none of them.**
`channels_for_call` returned non-`None` on **every** executed `pick_up_tips` operation the script
counted (`outputs/plr-sema/t30_measured_260905.json:64-68`, `d2`), `tip_spots` lowered as an `ir.Seq`
on all of them, and with O1 the `guard_operand_unknown` count is **0** everywhere, the O1 delta
differing on 389 operations (`outputs/plr-sema/t30_measured_260905.json:1143-1146`). **The gate failed
on a fourth thing this list did not contain** — two guards whose conditions the grammar could not read
at all — which is the amendment's subject and is why the list is left standing rather than rewritten:
it was a correct list of the risks that were foreseen, and the one that fired was not among them. D2's
floor `== 223` is reported as 361/361 under the script's own population, which is fix-up (1) above,
not a second failure.

**On `:522` surviving C6 and C14 together, explicitly, because round 1 disputed it.** `offsets` is
written **exactly once** in `pick_up_tips` — the β assignment at
`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:517`; `:493` is a kwarg pass inside
`_log_command`, not a write — so C6's eight-second-writes finding does not reach it. The "β is
unreachable" attack rested on E-CALL step (2) returning a signature default of `None`; step (2) had
**no data source at all** before D1, and after D1 it returns `Lit(None)`, which is statically
known-falsy and which E-CALL(β) case (3) routes to the β binding. Both paths end at
`Len(offsets) = Len(tip_spots)`. **The gate keeps a predicted GO candidate.**

---

## 15.10 The oracle and the fence

**Tier 1 re-run is the gate: 0 unsound, under the UNMODIFIED predicate.** A `SAFE` on an operation that
raised is the failure this increment makes possible **for the first time** — increments 1–5 could
produce `WILL_FAIL` and per-finding `SAFE`, but no path from a parsed condition to a `SAFE` on a guard
the analyzer previously declined. Round 1 deleted the draft's narrowing (§15.5): the predicate stays
exactly `plr-sema/eval/oracle_common.py:645-647`, and `rows_excused_by_scope` is published as an
annotation with **no threshold and no gate effect**. T32 contains no reference to `exc_class` in the
comparison path.

**The other direction — a false `WILL_FAIL` on an operation that ran clean — is the one round 1 found
live, and it is now fenced by construction rather than by measurement.** `compare` scores
`verdict == "will_fail" and outcome == "ran_ok"` as unsound at the same three lines, and `join`
propagates one such finding to the whole operation. E-UNCOND(4)/(5) and the restated E-TYPE are the
three clauses that stop it; AC-15.6's fixture set asserts each by name.

**Non-regression, each re-measured and published, any movement attributed before the run is accepted:**
m1 199/199, m2 289/289, v1 67/67 `WILL_FAIL` at the raised index, tier 2b 16 fixtures with
`region_unsound` 0 and `region_will_fail_fired` 7, tier 1 `rows_executed` 343 / `setup_error` 0 /
crosscheck 191/191, and the spec lint at 24 passed with six specs at zero failing citations
(`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:144-151`).

**The ledger after-run.** `outputs/plr-sema/unknown_ledger_260904_after.json`, produced by the same
script with no change, plus a published delta over: `n_findings_by_reason`, `n_clusters`, and the
`per_op_reason_set_histogram`. **`unknown_rate` is expected to stay 1.0** under §15.5's finding, and
that expectation is recorded here so a 1.0 at close is read as "predicted", not as "the increment did
nothing".

> **The `guard_predicate_unparsed` 5,656 is published with NO floor — round 1, C5.** The draft made it
> the headline with a floor of ≥ 1,000 converted. That floor is met by the **reason rename alone**:
> `:375`'s `len(missing) > 0` (544 findings) and `:383`'s `strictness == Strictness.STRICT` (544)
> both parse to non-`Opaque` predicates under G1 and both decide **nothing** — their free names
> resolve to a `BinOp` and to module state respectively, so both become `guard_env_dependent`. 1,088 >
> 1,000 from two clusters this document itself tiers (ii) and defers, before a single guard is
> evaluated; add `:409`'s 384 and the floor is met three times over. **An implementation with the
> grammar stubbed to "parse everything, resolve nothing" would have passed AC-15.8's headline.** The
> count is still published, as the grammar's coverage measure and nothing more; the number that gates
> is `n_findings_decided` (AC-15.8).
>
> **The consistency invariants must still hold on the after-ledger.** `consistency.ok` is `true`, with
> `sum(per_method) == n_ops_blocked` for every cluster and `sum(histogram.n_ops) == n_ops_unknown`
> (`plr-sema/eval/unknown_ledger.py:332-407`). A violation means the clustering arithmetic drifted, not
> that the increment worked.

> **Normative (a new mutant class — p1, `predicate_arity`).** Adopt one, in this increment, at tier 3.
> `plr-sema/eval/predicate_mutants.py` mutates a *planned* call's kwargs to violate one decided guard
> and asserts the static side emits `WILL_FAIL` at the raised index: (a) a duplicated `use_channels`
> entry, which violates `len(set(use_channels)) == len(use_channels)`
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:501-502`) and raises
> `AssertionError`; (b) an `offsets` list one element short, violating the chained equality at `:522`;
> (c) a non-`TipSpot` element in `tip_spots`, violating `:496-498` and raising `TypeError`.
>
> **Why it belongs here rather than in increment 7.** It is the only way to show a predicate
> `WILL_FAIL` lands at the *raised index* rather than merely somewhere, which is the property tier 1's
> aggregate cannot see and which increment 5's v1 class exists to prove for volume. It reuses
> `run_one_mutant(mutator, expected_exc)`, already parameterised by increment 5's T28
> (`.praxia/docs/specs/260903_plr-sema-volume-increment.md:1279`). **Its floor is ≥ 1 achieved
> `WILL_FAIL` at the raised index with 0 unsound in both directions** — increment 5 §14.16's own
> resolution that a class which can only ever report 0 is a publication, not a gate.
>
> **Mutant (a) is the stub-defeating one**: it fires on an `assert`-kind guard, so an implementation
> that kept increment 1 §10.3.1's `raise_guard`-only restriction (G6) passes (b) and (c) and fails (a).
>
> **Round-1 consequence for mutant (c), stated before the run rather than discovered by it.** Under the
> restated E-TYPE a `_generic_plr_type_name`-derived declaration is **never exact**, so the `F` branch
> is unreachable and `IsInstance` is `T`-or-`½`. A non-`TipSpot` element therefore yields **½, not
> `WILL_FAIL`** — mutant (c) is expected to report `0 achieved` and `0 unsound`, and it is published as
> such. The floor of ≥ 1 is carried by (a) and (b), which do not depend on the type atom. **This is
> the fail-closed price of not fabricating the `:647` false `WILL_FAIL` (C4)**, and recording it here
> is what stops a zero on (c) being read at close as an implementation defect. Recovering a decidable
> `F` on (c) needs an *exact* declaration, which is a graph-lane property (§15.4 E-TYPE) and is
> increment 7's.
>
> **Mutant (b) survives E-CALL(β) explicitly**: a short but non-empty `offsets` list is statically
> known-truthy, so case (2) resolves it to the caller's value rather than to the β length, and the
> chained equality at `:522` is `F` for an `assert`-kind guard ⇒ fires ⇒ `WILL_FAIL`. Had E-CALL(β)
> let β win unconditionally, this mutant would have been silently defeated — which is the false-`SAFE`
> direction §15.4 names.

> **Measured at T32, and it did not fire: all three mutators reported 0 achieved, so AC-15.10's floor
> is NOT MET at spec_version 19** (`outputs/plr-sema/predicate_mutants_260908_inc6.json`). (c)'s zero
> is exactly what the box above predicts. (a)'s and (b)'s are **not**, and the cause is neither the
> mutators nor E-CALL(β) — both guards are depth-0 empty-trail guards standing below `pick_up_tips`'s
> conditional `raise TypeError`, which spec_version 19's E-UNCOND(5) blocked. §15.4's refined clause (5)
> and its `reachability_clear` field are the remedy; **the floor is retained, not lowered**, and T36
> re-measures it. Recording the mechanism here is what stops a second zero at T36 being read as "the
> mutant class does not work".

> **Measured at T32 (agreement between the two instruments): the T30/T35 structural classifier and the
> shipped evaluator agree on 254 of 544 executed operations — 46.7 %, with 2 of 10 methods exact**
> (`outputs/plr-sema/oracle_replay_260908_inc6.json` against
> `outputs/plr-sema/t30_measured_260908.json`). **Published as an annotation, with no floor and no gate
> effect**, because every divergence is accounted for and neither instrument is wrong:
>
> 1. **Family-owned reasons the classifier never attributes.** `volume_state_unknown` and
>    `unresolved_delegate` are emitted by the volume family and the delegate closure, and §15.2's
>    dispatch rule keeps those guards away from the predicate evaluator entirely; the classifier does
>    not run either family, so it cannot predict either reason. This is A5's fix-up working as
>    intended, not a residual of it.
> 2. **Over-predicted `decidable` on `stamp` and `discard_tips`.** The classifier calls a guard
>    syntactically decidable; the evaluator then resolves an operand to ⊤ and returns ½. The classifier
>    tests the *shape* of a condition and the evaluator tests a *call*, so the classifier is an upper
>    bound on decidability by construction.
>
> **The consequence is normative for how every number in §15.1 and §15.9 is read: the classifier is a
> PREDICTION instrument only.** §15.1's (i)/(ii) tiering and §15.9's re-prediction table *forecast* a
> residual; the after-ledger, `n_findings_decided` and the per-op reason sets *measure* one, and where
> the two disagree **the measurement wins and the divergence is recorded rather than absorbed** — the
> same rule §15.1's derived-tier box already imposes, now with a measured disagreement rate attached to
> it. Making the classifier agree with the evaluator would require teaching it family dispatch and
> operand resolution, i.e. rebuilding the evaluator inside the measurement script, which is the
> configuration §15.9's gate exists to avoid.

---

## 15.11 Acceptance criteria

- **AC-15.1 (the grammar is total, and `Opaque` is its only escape).** Over the whole shipped
  `derived_contracts.json`, `parse` returns for **every** guard without raising, and the count of
  non-`Opaque` results is published. Six fixtures pin the productions, one apiece: a chained
  comparison of three `Len`s yields two conjoined `Cmp`s and evaluates `F` when the *second* conjunct
  is `F` and the first is ½; `len(<Filtered>) > 0` yields `AnyOf` and `len(<Filtered>) == 0` yields its
  negation; `len(set(x)) == len(x)` on `[0, 1, 1]` is `T` for the guard's polarity and on `[0, 1]` is
  `F`; `x is None` / `x is not None` on a `Lit(null)` kwarg are exact opposites; an `assert`-kind guard
  fires on `F` and a `raise_guard` on `T` for the identical condition string (G6); and an unrecognised
  shape — `c not in self.head` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:407`)
  — yields `Opaque` and a `guard_predicate_unparsed` finding **identical to the one emitted today**.
  The last is the stub-defeating half: an implementation that raised, or that emitted a new reason for
  an unparsed guard, fails it. **Plus three round-1 fixtures on E-TYPE and nesting**:
  `IsInstance(declared="Container", (TipSpot, Trash))` is **½** (not `F` — C4a's false-`WILL_FAIL`
  mechanism); `IsInstance(declared="Well", (Container,))` is **`T`** (not ½ — C4b); and a predicate
  whose top node parses but which contains an `Opaque` sub-node keeps `guard_predicate_unparsed` while
  still evaluating `F` when conjoined with an `F` conjunct (C15).
  **Plus the 260907 amendment's fixture set, positive and negative, one apiece.** *Positive*:
  `c not in self.head` parses to `Cmp(Var("c"), "not in", EnvRef(("self", "head"), None))` with
  `contains_opaque` false and `contains_env_ref` true;
  `not all(self.backend.can_pick_up_tip(channel, tip) for channel, tip in zip(use_channels, tips))`
  parses to `Not(AllOf(Zip((Var("use_channels"), Var("tips"))), EnvRef(("self", "backend",
  "can_pick_up_tip"), (Var("channel"), Var("tip")))))`, non-`Opaque`, and evaluates ½ against a call
  supplying both kwargs; `self.setup_finished and (not self._resource_pickups)` parses to an `And` of
  two `EnvRef` leaves **in predicate position**; and `self._resource_pickup is None` parses to
  `Is(EnvRef(…), negated=False)` rather than to `Is(Attr(Var("self"), …), …)`, asserted as the
  normalisation. *Negative — the closed list of §15.2 G7, one fixture per row*: a call whose callee is
  not `self`-rooted; `self.head[channel].has_tip` (subscripted); `f(self)` (`self` as an argument);
  `tip.tracker.get_used_volume()` (rooted at a local); `volume - self.get_used_volume() > 1e-06`
  (arithmetic `BinOp`); a `zip(...)` under `Len` rather than as a `seq`; and a tuple-target
  comprehension whose arity differs from its `Zip`'s. Every one yields `Opaque` and a
  `guard_predicate_unparsed` finding **identical to the one emitted today**. **Two whole-table
  assertions carry the invariant**: `n_var_self == 0` over the regenerated contract table, and
  `n_findings_decided` unchanged by the amendment alone. **The stub-defeating halves are the negative
  list and the `n_var_self` assertion**: an implementation that admitted any `self`-rooted text as an
  `EnvRef` passes every positive fixture and fails these.
  **Plus round 2's five fixtures, gated on T35 (§15.12), one per objection they close.**
  (a) *The PLR-layer test (A-C1)*: `not self._check_96_head_fits_in_container(container)` yields
  `Opaque` and `guard_predicate_unparsed` — asserted **negative**, reversing spec_version 18's
  positive example — while `self.backend.can_pick_up_tip(channel, tip)` stays an `EnvRef`; and
  `n_env_ref_refused_plr_layer > 0` over the regenerated table. **This is round 2's stub-defeating
  half**: an implementation that skipped the index test passes every other fixture in this criterion
  and fails this one. (b) *`Zip` resolution (A-C3)*: `AllOf(Zip(Seq([]), ⊤), <½ body>)` evaluates
  **½**, asserted **not `T`** — the vacuous-quantification false-`SAFE` mechanism — and
  `Zip((Seq[8], ⊤))` is asserted to resolve ⊤ rather than to an 8-element sequence. (c) *The
  α/β-substituted walk (A-C4)*: `contains_env_ref` is **true** for the substituted `:409` guard —
  `not len(invalid_channels) == 0` with `invalid_channels` bound to
  `Filtered(Var("channels"), Cmp(Var("c"), "not in", EnvRef(("self", "head"), None)))` — and
  **false** for its raw `predicate` field, so an implementer who walked the wrong tree fails visibly.
  (d) *Membership decides nothing (A-C2/A-C10)*: `x in ['a', 'b']` yields `Opaque` (no
  literal-container `Term`), and a membership `Cmp` whose RHS **does** resolve to a concrete `Seq` of
  `Lit`s evaluates **½**, asserted **not** `T`/`F`. (e) *The `args` round-trip (A-C12)*: `self.head`
  parses with `args is None` and a zero-argument shape-(2) call with a length-3 path (written
  `self.backend.<m>()` in the fixture, synthetic by design — the distinction under test is `None` vs
  `()`, not a PLR API) parses with `args == ()`, and **both survive `to_json`/`from_json` unchanged**,
  so JSON `null` and `[]` do not collapse into each other on the wire.
- **AC-15.2 (the two idioms bind, are measured, and fail closed).** The complete
  `(K, x, idiom, term)` selection over the whole PLR surface is published with **≥ 3** α entries
  (`liquid_handler.py:496`, `:645`, `:873`) and **≥ 6** β entries — a floor **met by measurement, not
  by assertion**: the expected β population at this pin is **exactly eight** (`:517`, `:661`, `:963`,
  `:964`, `:965`, `:1157`, `:1158`, `:1159`), with `offsets` at `:962`/`:1156` correctly excluded.
  Five fail-closed fixtures, one apiece: a second write to `x` anywhere in `K` binds nothing; an
  assignment nested in an `if` that does not contain the guard binds nothing; a three-operand `or`
  chain whose middle operand is `self.<x>` binds nothing under β **and is instead resolved by the
  existing `channels_for_call`** (`plr-sema/src/plr_sema/check/tipstate.py:245-270`), asserted through
  the receiver's **derived** `channel_kwarg`/`channel_default_param` and never through a hand-typed
  `"use_channels"` (`plr-sema/src/plr_sema/check/tipstate.py:254-257`); an assignment *after* the
  guard's `lineno` binds nothing; and a guard whose `scope_trail` contains a `for` header targeting
  `x` binds nothing. The last two are the stub-defeating halves: an implementation matching on shape
  alone, without the position and scope tests, passes the first three and fails these.
  **Plus six round-1 fixtures.** Two on the β-preserving rebinding: `x = [f(e) for e in x]` preserves a
  β length binding, and `x = [f(a, b) for a, b in zip(y, x)]` does **not**. One on the iterand: a
  second write to α's `iter` name binds nothing. Three on E-CALL(β)'s truthiness branches, one per
  case, including **`offsets=[]` asserted to resolve to the β length and NOT to `Len == 0`** — the
  latter would be a false `WILL_FAIL` at `:522`, which is the stub-defeating half of this group.
- **AC-15.3 (the measured sets are published and the gate is decided by them).**
  The measured report carries all six blocks of §15.9 — the first as
  `outputs/plr-sema/t30_measured_260905.json`, the amendment's re-measurement as
  `outputs/plr-sema/t30_measured_260908.json` — and the GO/NO-GO
  decision is recorded against the published **per-op reason set** — GO iff ≥ 1 executed real
  operation carries zero `guard_predicate_unparsed` and zero `guard_operand_unknown` findings.
  **The gate number is asserted computable from the JSON alone, without reading this document.**
  `pick_up_tips` is asserted **by name** to be that operation, or the divergence is recorded in §15.15
  and the decision goes to the user before AC-15.5's work starts. Block (3) additionally publishes,
  per cluster, the reason each guard **actually** carries against §15.1's predicted tier, and any
  divergence is recorded rather than absorbed.
  **Plus the 260907 amendment's publication requirements, gated on T35 (§15.12) and each asserted
  present and non-null in the re-measured JSON**: **`n_env_ref_nodes`** and `env_ref_paths` per cluster
  (block 3); **`n_env_ref`** (per-guard) and `n_decided_via_env_ref_shortcircuit` per executed
  operation (block 4); and block (6)'s whole-table set — the **top-10 `EnvRef` paths with counts**,
  `n_env_ref_guards`, `n_env_ref_nodes`, `n_zip`, `n_membership_cmp`, `n_var_self`,
  `n_opaque_only_by_var_self` and **`n_env_ref_refused_plr_layer`**. **Block (3)'s and block (4)'s
  fields are asserted to carry DIFFERENT names because they carry different units** (round 2, A-C8) —
  a reader cross-footing the two must be able to reconcile them from the JSON alone, and with one name
  in two units could not: `:2055` is one guard and two nodes. The two measurement fix-ups of
  §15.9 are asserted landed: the population is **544 / `pick_up_tips` 223** (fix-up (1), already landed
  as `outputs/plr-sema/t30_measured_260907.json`, or the difference is published with a named cause),
  and no guard the tip or volume family claims carries a predicate reason. **The stub-defeating half is
  the top-10 path list together with `n_env_ref_refused_plr_layer`**: a count alone cannot show what
  the production absorbed, an implementation that widened `EnvRef` beyond §15.2 G7 is visible in the
  list and nowhere else, and an implementation that skipped G7's PLR-layer test reports a refusal count
  of 0 while the list fills with `self._is_error_tail`-class entries.
- **AC-15.4 (the operand observation, its fail-closed rule, and the counterfactual).** After O1,
  `resources_from_example`'s output carries a non-`None` `type` for **≥ 90%** of the resources
  referenced by the benchmark's planned kwargs, and a non-`None` `element_type` for every `Ref`
  carrying a `cell` **whose parent's element-class set is a singleton**; the pre-O1 baseline (`type`
  from `deck_layout` only, `element_type` universally `None`,
  `plr-sema/eval/oracle_common.py:397-410`) is published beside it. **The count of parents with
  heterogeneous children — for which `element_type` is `None` by the fail-closed rule of §15.4 — is
  published beside the coverage numbers**, and a fixture asserts that a parent with two distinct child
  classes yields `element_type is None` rather than first-element-wins. §15.9(5)'s with/without
  residual comparison differs on **≥ 1** operation. A zero difference fails this criterion — that is
  the stub-defeating half, since a change that threads the field but never reaches an atom would
  otherwise pass on the field counts alone.
- **AC-15.5 (evaluation: F ⇒ SAFE, ½ ⇒ the finest reason, and E-SCOPE).** Four fixtures. (i) A guard
  evaluating `F` yields exactly one `Verdict.SAFE` finding at `guard.site` with `category == ""` and
  `reason == ""` — and, per E-UNCOND(6), the guard's own `scope_trail[0]` self-entry is asserted **not**
  to be evaluated a second time as a scope entry. (ii) A guard whose enclosing scope entry evaluates
  `F` yields `SAFE` **regardless of its own predicate**, asserted with the guard's own predicate at
  `T` — the shape is now `transfer`'s
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1333-1340`), **not** the withdrawn
  `:1185`/`:1188` one, and `:1335`/`:1337`/`:1340` are asserted `SAFE` by name under D1's
  `param_defaults`. (iii) A guard with an unresolvable kwarg yields `guard_operand_unknown`; with an
  unresolvable free name, `guard_env_dependent`. **Plus round 2's clause-ordering fixture (A-C5),
  landing with the rest of this criterion on T31: `self.backend.f(?0)` — an `EnvRef` whose one
  argument is a kwarg renamed to `?<j>` and
  therefore a ⊤ operand of this call — yields `guard_operand_unknown`, NOT `guard_env_dependent`**,
  which is the assertion that
  the amendment relaxed neither of the gate's two zero-conditions. (iv) One `Finding` per guard is
  preserved: an
  operation with `n` guards — **`k` of them tier (iii)** — yields exactly `n` findings, asserted as a
  count, and `join` is called once. (ii) is the stub-defeating half.
- **AC-15.6 (`WILL_FAIL` only when reachability is established, and the scope annotation).** A guard
  evaluating `T` at depth 0 with an empty `scope_trail` **whose `K` yields `reachability_clear` true —
  no earlier `Return`, no enclosing `Try`/`With`, no earlier `Break`/`Continue`, and, per
  spec_version 20's refinement, an earlier `Raise` or `assert` being expressly permitted** — yields
  `Verdict.WILL_FAIL` with
  `category == "precondition_state"`; the same guard yields `Verdict.UNKNOWN` with
  `reason == "guard_env_dependent"` under each of **eight** perturbations, one fixture apiece — a
  `while` header in the trail; a `for` header R1 did not bind; a trail entry parsing `Opaque`; a trail
  entry evaluating ½; a trail entry beginning `"else of: if "` whose test text is in `env` (which must
  **not** satisfy it, preserving increment 5's AC-14.4 behaviour); **the same guard at `depth == 1`
  with a `T` predicate** (E-UNCOND(4)); **`_check_no_lid`'s `:117`, asserted by name**, whose empty
  trail sits after the early `return` at
  `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:113-114` (E-UNCOND(5)); and a
  depth-0 empty-trail guard **lexically enclosed by** an `ast.Try`. Separately: **a tier-(iii) guard
  emits exactly one `Finding`, `Verdict.UNKNOWN`, `reason == "guard_env_dependent"`**, and contributes
  its `site` to `AnalysisReport.scope.excludes_sites`; tier (iii) is asserted to be selected by
  `guard.is_dynamic_raise` (`plr-sema/src/plr_sema/derive/__init__.py:516-520`) and **not** by any site
  list or condition-text match; `join`'s input multiset **is** asserted to contain it; and
  `check_graph`'s two-positional-argument call form returns a report whose `schema_version` is still 1.
  The `else of:` case, the `:117` case and the depth-1 case are the stub-defeating halves.
  **Plus spec_version 20's four fixtures, gated on T36 (§15.12), which pin the refined clause (5) in
  both directions.** (α) *An earlier conditional `raise` does NOT block*: a depth-0 empty-trail guard
  whose `K` contains an earlier `ast.Raise` under an `if`, and no earlier `Return`/`Break`/`Continue`
  and no enclosing `Try`/`With`, has `reachability_clear` **true** and yields `Verdict.WILL_FAIL` —
  asserted **positive**, reversing spec_version 19's reading — and `pick_up_tips`'s `:502` is asserted
  **by name** to be that shape. (β) *An earlier conditional `return` DOES block*: the otherwise
  identical guard, with an `ast.Return` at a lower `lineno` in place of the `raise`, has
  `reachability_clear` **false** and yields `Verdict.UNKNOWN`/`guard_env_dependent`. (γ) *Enclosure
  blocks*: the same guard lexically inside an `ast.Try` yields `UNKNOWN`/`guard_env_dependent`, and so
  does one lexically inside an `ast.With` — asserted separately, since the two are different AST nodes
  under one clause. (δ) *The wire field fails closed*: a guard record from which `reachability_clear`
  is **absent** yields `None` and `UNKNOWN`/`guard_env_dependent` even when every syntactic condition
  of (α) holds. **(β) and (δ) are the stub-defeating halves**: an implementation that reduced clause
  (5) to "no earlier return" passes (α) and fails (γ), and one that defaulted the missing field to
  `True` passes (α), (β) and (γ) and fails (δ) — which is the regeneration-ordering hazard the field's
  additive design creates and the only one it creates.
- **AC-15.7 (the vocabulary and registry arithmetic is exactly as specified, under the user's 260907 answers).**
  `len(REASON_VOCABULARY) == 12` against HM-14's unchanged `declared == 12`
  (`plr-sema/src/plr_sema/_hand_maintained.py:650-667`); the commit's parent has 10, so the diff is
  visibly 10 → 12; `len(live_rows()) == 24` and `BUDGET_CAP == 24`; **HM-25's `declared` is 9 and
  HM-24's is 3**, asserted directly, so a spend on the wrong row fails;
  `test_no_surface_exceeds_its_declared_size`, `test_total_declared_within_budget` and
  `test_reason_vocabulary_closed_forward` all pass, the last with both new members reachable from ≥ 1
  construction site. **No longer conditional: the user approved both §15.14 Q4 and Q5 on 260907**
  (`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:262-265`), so the assertions are
  `len(REASON_VOCABULARY) == 12` and HM-25 `declared == 9` **unconditionally** — the declined branches
  (11 members, `declared == 8`) are dead and a silent divergence in either direction fails.
  The 260907 amendment adds **no** vocabulary member and **no** registry row (§15.8), so this
  criterion's arithmetic is unchanged by it — which is itself asserted, as the amendment's cheapest
  falsification.
  **Plus round 2's registry concession (A-C6), asserted at T31 where the spend lands.** HM-25's `what`
  names `EnvRef`, `Zip` and the `in`/`not in` comparators, **and `_measure_hm25` imports the symbols
  that implement them**, so the entry's measure moves when its `what` does
  (`plr-sema/src/plr_sema/_hand_maintained.py:300-351`). The measured pattern count for HM-25 is
  asserted `<= declared == 9`; **if the added symbols push it past 9, T31 STOPS and surfaces a further
  ceiling spend to the user rather than raising `declared` on its own authority** — the contingency is
  written here so it is a decision, not a discovery.
- **AC-15.8 (tier 1 — 0 unsound under the unmodified predicate, and the decided-findings floor).** The
  sidecar-gated replay reports `unsound == 0` under the **unmodified** predicate
  (`plr-sema/eval/oracle_common.py:645-647`, unchanged by this increment), `rows_setup_error == 0`,
  `rows_executed == 343`, crosscheck 191/191 at agreement 1.0, and `rows_excused_by_scope` published as
  an annotation with **no threshold**. The after-ledger is produced by the unmodified
  `plr-sema/eval/unknown_ledger.py` with `consistency.ok == true`, and the delta on
  `n_findings_by_reason` / `n_clusters` / `per_op_reason_set_histogram` is published.
  **The gated number is `n_findings_decided`** — findings whose emitted `verdict` is `Verdict.SAFE` or
  `Verdict.WILL_FAIL` — broken down **per PLR site**, with a floor of **≥ 223**. 223 is
  `pick_up_tips`'s own operation count from §15.9's candidate table, i.e. the minimum implied by one of
  its three tier-(i) guards clearing on every op; it is derived from this document's own prediction
  rather than asserted. `guard_env_dependent` and `guard_operand_unknown` counts are published
  **separately** and are explicitly **excluded** from "converted". The `guard_predicate_unparsed` delta
  is published with **no floor**, as the grammar's coverage measure only. **The stub-defeating half:
  an implementation that parses every condition and resolves nothing scores `n_findings_decided == 0`
  and fails** — which the draft's ≥ 1,000-converted floor would have passed (§15.10).
- **AC-15.9 (non-regression across tiers 2b and 3).** m1 199/199, m2 289/289, v1 67/67 at the raised
  index with 0 unsound, tier 2b at 16 fixtures with `region_unsound == 0` and
  `region_will_fail_fired >= 7` and `volume_will_fail_fired == 3`. Every number is re-measured against
  the sprint-123 close baseline and any movement is attributed before the run is accepted — the
  E-SCOPE rule is what could move tier 2b, by converting a previously-`UNKNOWN` guard to `SAFE` inside
  an executed region.
- **AC-15.10 (tier 3 — the predicate mutant fires at the raised index).**
  `plr-sema/eval/predicate_mutants.py` reports p1 with **0 unsound** in both directions and its
  achieved `WILL_FAIL`-at-the-raised-index count published against a floor of **≥ 1**, over all three
  mutators (duplicate `use_channels`, short `offsets`, non-`TipSpot` element), **published per
  mutator**. The duplicate-`use_channels` mutator is asserted to fire against an `assert`-kind guard
  specifically. **The non-`TipSpot` mutator is asserted to report `0 achieved` / `0 unsound`** under
  the restated E-TYPE's never-exact rule (§15.10), so a zero there passes and a `WILL_FAIL` there
  *fails* — an implementation that fabricated it would be the C4 false-positive mechanism reappearing.
  **MEASURED NOT MET at T32 and re-gated on T36 (spec_version 20).** T32 published (a) 288 raised / 0
  achieved / 0 unsound, (b) 16 / 0 / 0, (c) 288 / 0 / 0
  (`outputs/plr-sema/predicate_mutants_260908_inc6.json`): (c) as predicted, (a) and (b) blocked by
  spec_version 19's E-UNCOND(5), not by the mutators (§15.10, §15.15's T32 row). **The floor stays
  `>= 1` and is re-measured after `reachability_clear` is derived and wired**; the 0-unsound halves and
  the `assert`-kind assertion on (a) already hold and must continue to. **A second zero on (a) or (b)
  at T36 fails this criterion outright** — with the mechanism named in §15.4 and the field wired, there
  is no remaining explanation for one, and that is what makes this a gate rather than a publication.
- **AC-15.11 (this document is machine-checked).** `plr-sema/tests/test_spec_lint.py` gains
  `SPEC_INCREMENT_6` and parametrises it into both live-spec tests
  (`plr-sema/tests/test_spec_lint.py:212-255`); `.praxia/docs/INDEX.md` is regenerated; and
  `uv run pytest plr-sema/tests/test_spec_lint.py -q` is **actually run** with its result recorded —
  both the citation checker and the AC-gating half of the cross-reference checker reporting **zero**
  failing violations over this file, and the other six specs unchanged at zero.
- **AC-15.12 (tier (ii), conditional — only if the round overturns §15.6).** `env` gains
  `get_strictness`; the observation is returned from inside the executed window as increment 5's
  `volume_tracking_observed` is — **the producer is `run_runtime`'s return at
  `plr-sema/eval/oracle_common.py:370-373`**, not `run_static_calls`'s consumption of the already-
  returned flag at `:593-595`, which is what the draft cited (round 1, C18); `cache_key`'s fifth
  component partitions on it, with the default-`env` key asserted byte-identical to today's; and the
  backend-signature derivation publishes its complete measured selection. **If §15.6's recommendation
  stands, this criterion is withdrawn together with its task row rather than left unsatisfied.**

---

## 15.12 Task rows

> Ordering is forced by §15.9's gate: **T30 must land and publish its measured sets, and the GO/NO-GO
> must be recorded, before T31 constructs any `SAFE` or `WILL_FAIL`.** T30 landed and recorded
> **NO-GO** (§15.15); **T35 inherits the whole of that gate condition** — it is the amendment plus a
> re-measure, and T31 waits on *its* recorded GO, not on T30's. A T35 that landed the grammar without
> re-running the measurement would be the exact configuration this box exists to prevent, with the
> added hazard that the amendment moves a reason the gate reads. This is the same normative gate
> increment 5 §14.0 imposes for the same reason: a landed evaluator without a published coverage
> measurement can construct a definite verdict whose basis nobody has inspected.

> **Normative (why the amendment's row is `T35` and not `T30c` — round 2, A-C9).** The cross-reference
> lint's task-row pattern is
> `TASK_ROW_RE = re.compile(r"^\|\s*\*\*(T\d+|#\d+[a-z]?)\*\*[^|]*\|")`
> (`plr-sema/scripts/check_spec_crossrefs.py:58`), and the `[a-z]?` suffix sits on the `#\d+`
> alternative **only** — so `| **T30c** |` never matched, its gate cell was never scanned by the
> AC-gating half, and the amendment's obligations were formally hung off **T30**, a row §15.15 records
> as landed. The row is renamed **`T35`**, which the regex accepts, and **AC-15.1 and AC-15.3 move
> from T30's gate cell to T35's** — T35 ships the final grammar and writes the report the gate is read
> from, so it satisfies both criteria in full, while T30's contribution is a precondition rather than a
> gate. AC-15.5(iii)'s new clause-ordering fixture stays with AC-15.5 on **T31**, which is the row that
> owns the reason rule it asserts. **Every AC in this document is gated exactly once** — the lint's own
> `ac_multiply_gated` / `ac_ungated` checks (`plr-sema/scripts/check_spec_crossrefs.py:148-156`) are
> what enforce that, and they read the **gate cell** (column 4) only, so an AC named in a scope cell is
> documentation and not a gate. T33 re-runs the lint, which is what will catch a regression here.

> **Normative (why AC-15.6 and AC-15.10 move to T36 — spec_version 20, and it is the same move round 2
> made for AC-15.1/AC-15.3).** T31 and T32 have landed (§15.15). Both criteria are **re-measured** by
> T36 against a changed rule — §15.4's refined E-UNCOND(5) and its derived `reachability_clear` field —
> so leaving either on a landed row's gate cell would gate a criterion on work that finished before the
> criterion changed, which is the formally-empty configuration A-C9 identified. **AC-15.6 moves from
> T31's gate cell to T36's** and **AC-15.10 moves from T32's to T36's**; T31 keeps AC-15.5 and AC-15.7,
> T32 keeps AC-15.8 and AC-15.9, and neither is re-gated. What T31 and T32 actually landed is recorded
> in §15.15 rather than erased. **Every AC in this document remains gated exactly once**, which
> `ac_multiply_gated`/`ac_ungated` (`plr-sema/scripts/check_spec_crossrefs.py:148-156`) enforce over the
> gate cell only — so the AC names appearing in this box and in T36's *scope* cell are documentation,
> not gates. T33, still unstarted, is the row that re-runs the lint and would catch a slip here.

| task | scope | files | gate | ~LOC | depends on | model |
|---|---|---|---|---|---|---|
| **T30** | Derive + measure (§15.2, §15.3, §15.4's O1 and `param_defaults`, §15.9). The typed mini-AST and the total `parse`; `InlinedGuard.predicate` as an additive field with `condition` retained; **`param_defaults` per contract entry** from `ast.arguments.defaults`/`kw_defaults` restricted to `ast.Constant`, fail-closed (D1); the α and β idioms with the scope clause, the **iterand** single-write clause and the **β-preserving-rebinding** exception; O1's **new element walk** with the **heterogeneous-parent singleton rule**; all five measured blocks published — including **D2's `channels_for_call` non-`None` count on executed `pick_up_tips` ops (floor `== 223`)** and the **name-coincidence exposure count** for depth-≥1 guards — and the GO/NO-GO recorded against the reason-based gate | modify `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/data/derived_contracts.json` (regenerated — this moves `contracts_sha` and cools the whole cache by design, §15.8), `plr-sema/tests/test_derive.py`; create `plr-sema/eval/t30_measure.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; **`uv run pytest plr-sema/tests/test_cache.py -q`** (no test may pin a literal `cache_key`); then regenerate the contract table and run `t30_measure.py` into `outputs/plr-sema/t30_measured_260905.json` (**corrected in round 2, A-C9** — the cell said `t30_measured_260904.json`, a file §15.9's own normative box records as never written; the population re-run of the same row is `outputs/plr-sema/t30_measured_260907.json`, commit `15b84d31`) — satisfying **AC-15.2** and **AC-15.4** | ~530 | — | Sonnet — six selections, each measured and published rather than asserted; the gate lives here, and three of its preconditions (O1's element type, D2's channel set, `tip_spots` lowering as a `Seq`) are measurable only in this row |
| **T35** | **The 260907 amendment as revised by its round-2 adversarial pass (§15.2 G7/G8, §15.4 E-ENV, §15.7's reordered reason rule) plus the remaining measurement fix-up, then a re-measure.** Add `EnvRef`, `Zip` and the `in`/`not in` comparators to the mini-AST and to `parse`, admissible in the positions §15.2 G7/G8 name and no others; implement **G7's PLR-layer test on shape (2)** — the `len(path) >= 3` OR absent-from-`build_plr_function_index` rule, applied in `derive/bindings.py` where the `function_index` already is, fail-closed to `Opaque` when none is supplied (A-C1); add `contains_env_ref` beside `contains_opaque` and apply **both to the α/β-substituted tree** (A-C4); implement the **`Zip` resolution rule** (⊤ unless every item is a concrete `Seq`; `AllOf`/`AnyOf` over a ⊤ seq is ½, never vacuously `T`) and the **comprehension-target ⊤ rule** (A-C3/A-C13); **membership `Cmp` is ½ unconditionally — ship no deciding branch** (A-C2/A-C10); enforce the `Var("self")` invariant fail-closed; extend `to_json`/`from_json` for the two new node kinds and add `EnvRef` to **both** `_TERM_KINDS` and `_PREDICATE_KINDS` (A-C12); regenerate `plr-sema/data/derived_contracts.json` (this moves `contracts_sha` again — §15.8's cold-cache-by-design property is unchanged); make `t30_measure.py` respect §15.2's tip/volume family dispatch (fix-up (2); fix-up (1), the population, already landed as `15b84d31`); publish block (3)'s `n_env_ref_nodes`, block (4)'s per-guard `n_env_ref`, and block (6) **including `n_env_ref_refused_plr_layer`**. Satisfies **AC-15.1 in full** (T30's fixture set plus the amendment's positive/negative set, round 2's five fixtures, and the `n_var_self` invariant) and **AC-15.3 in full** (the measured blocks, the publication requirements and the fix-ups) — **both gated on this row's gate cell**, not on T30's landed one (A-C9). AC-15.5(iii)'s new clause-ordering fixture stays with the rest of AC-15.5 on **T31**, because it asserts a *reason assignment* and only T31 has an evaluator. **No evaluator, no verdict, no `check_ir`** — T31's boundary is unmoved | modify `plr-sema/src/plr_sema/derive/predicate_ast.py`, `plr-sema/src/plr_sema/derive/bindings.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/eval/t30_measure.py`, `plr-sema/tests/test_derive.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q`; then regenerate the contract table and re-run `t30_measure.py` into `outputs/plr-sema/t30_measured_260908.json` (or later — the file name tracks the run date, and its delta is taken against `t30_measured_260907.json`, same population), recording GO/NO-GO against the unchanged reason-based gate — satisfying **AC-15.1** and **AC-15.3** (both moved here from T30's gate cell in round 2, A-C9: T35 is the row that ships the final grammar and writes the report the gate is read from, so gating them on a landed row was formally empty; every AC in this document is gated **exactly once**, which `check_spec_crossrefs.py`'s `ac_multiply_gated` check enforces) | ~145 | T30 + the user's 260907 approvals + the round-2 adversarial pass (`.praxia/docs/audits/260907_plr-sema-predicate-amendment-challenger.md`, dispositioned in §15.16.2) | Sonnet — the amendment relaxes the gate's own zero-condition, so every published count in §15.9 block (6) is what makes the relaxation inspectable |
| **T31** | The evaluator and the reasons (§15.4, §15.5, §15.7): `plr-sema/src/plr_sema/check/predicate.py` with E-CALL (incl. **`param_defaults` step (2)**, **E-CALL(5)** parameter-rebinding, **E-CALL(β)** truthiness, **E-CALL(depth)** forbiddance) / **restated E-TYPE** / E-SCOPE over `scope_trail[1:]` / E-VERDICT / E-UNCOND **(1)–(3) plus (4) depth, (5) empty trail, (6) self-entry**; **tier (iii) derived from `guard.is_dynamic_raise`, emitting one `UNKNOWN`/`guard_env_dependent` `Finding` plus an `excludes_sites` entry**; the **nested-`Opaque`** reason rule; **E-ENV — every `EnvRef` at ½ in predicate position and ⊤ in term position, unconditionally; `Len` of a `Zip` at ⊤; a `Zip` resolving to ⊤ unless every item is a concrete `Seq`, with `AllOf`/`AnyOf` over a ⊤ seq at ½ and never vacuously `T`; every membership `Cmp` at ½ **unconditionally** (no deciding branch); a comprehension-bound target name at ⊤, never resolved against `call.kwargs` — and §15.7's **reordered** reason rule (`contains_opaque`, then the operand test, then `contains_env_ref` ⇒ `guard_env_dependent`), both walks over the α/β-substituted tree**; dispatch that skips guards the tip and volume families already claim; `SoundnessScope` (one field, `excludes_sites`) and `AnalysisReport.scope`; `REASON_VOCABULARY` 10 → 12 and **the approved HM-25 `declared` 8 → 9 spend, filed as ONE entry whose `what` now also names `EnvRef`/`Zip`/`in` and whose `_measure_hm25` imports the production symbols (§15.8, A-C6) — stopping and asking the user if the measured count would exceed 9** | create `plr-sema/src/plr_sema/check/predicate.py`; modify `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/src/plr_sema/verdict.py`, `plr-sema/tests/test_check_graph.py`, `plr-sema/tests/test_verdict.py`, `plr-sema/tests/test_hand_maintained_ratchet.py`, and the fixtures under `plr-sema/tests/fixtures/` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_verdict.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q`; `uv run pytest plr-sema/tests/test_tip_typestate.py -q` — satisfying **AC-15.5** and **AC-15.7** (the third criterion this row was written to satisfy is re-gated on **T36** by the box above, because spec_version 20 changed the rule it asserts after this row landed) | ~560 | **T35** + a GO recorded in the re-measured report (the user's §15.14 Q4/Q5 answers landed 260907) | Sonnet — **E-UNCOND(4)/(5) and the restated E-TYPE are the three clauses standing between this row and a false `WILL_FAIL` on ~256 clean operations**, and the shipped precedent (`volume_guard_is_unconditional`) implements the wrong reading of (5) |
| **T32** | The oracle (§15.10): tier-1 re-run under the **UNMODIFIED** unsoundness predicate, with `rows_excused_by_scope` published as an annotation and **no `exc_class` reference anywhere in the comparison path**; `n_findings_decided` per PLR site with its ≥ 223 floor; m1/m2/v1/tier-2b non-regression; the after-ledger with `consistency.ok == true` and its published delta; `plr-sema/eval/predicate_mutants.py` with p1's three mutators | create `plr-sema/eval/predicate_mutants.py`; modify `plr-sema/eval/oracle_replay.py`, `plr-sema/eval/tip_mutants.py`, `plr-sema/eval/tier2_extractor.bth.toml`, `plr-sema/tests/test_oracle_replay.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q`; then the tier-1 replay with its three standard flags, `unknown_ledger.py` into `unknown_ledger_260904_after.json`, `predicate_mutants.py`, `tip_mutants.py`, `volume_mutants.py` and `region_oracle.py` — satisfying **AC-15.8** and **AC-15.9** (the tier-3 mutant criterion this row was written to satisfy measured its floor UNMET and is re-gated on **T36** by the box above) | ~300 | T31 | Sonnet — every published number is a measurement; this row shrank because the narrowed-predicate comparison path was deleted |
| **T36** | **The E-UNCOND(5) refinement (§15.4, spec_version 20): derive `reachability_clear`, regenerate, wire, re-run.** Derive the boolean at guard-construction time in the derive package — `not has_return_before and not enclosed_by_try_or_with and not has_break_continue_before`, with **no `ast.Raise` and no `ast.Assert` term**, over `K`'s AST at any nesting depth for the two lineno tests and by span containment for the enclosure test; add it as an **additive** field on `InlinedGuard` and on the contract table's guard record, with a `to_json`/`from_json` round-trip in which an absent field reads back as `None`; regenerate `plr-sema/data/derived_contracts.json` (this moves `contracts_sha` a third time — §15.8's cold-cache-by-design property is unchanged, and no test may pin a literal `cache_key`); **feed the evaluator's `k_reachability_clear` from the field at every production call site**, replacing the `None` T31 shipped (§15.15's T31 row), with `None` retained as the fail-closed default for a record lacking the field; add spec_version 20's four AC-15.6 fixtures (earlier conditional `raise` ⇒ `WILL_FAIL`; earlier conditional `return` ⇒ `UNKNOWN`; enclosing `try` and enclosing `with` ⇒ `UNKNOWN`; absent field ⇒ `UNKNOWN`); then **re-run p1, tier 1 and the whole non-regression set**, since a clause that newly permits `WILL_FAIL` is exactly the clause that can newly produce a false one. **No new production, no new reason, no registry spend, no change to E-UNCOND(4) or to ways (1)–(3)** — this row's whole surface is one derived boolean and its wiring. It satisfies the tier-3 mutant criterion and the reachability criterion re-gated here by the box above | modify the derive package's guard construction and predicate JSON round-trip (`plr-sema/src/plr_sema/derive/`), `plr-sema/data/derived_contracts.json` (regenerated), the predicate evaluator and its call sites (`plr-sema/src/plr_sema/check/`), `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_check_graph.py`; re-run (no source change expected) `plr-sema/eval/predicate_mutants.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q`; `uv run pytest plr-sema/tests/test_verdict.py -q`; then regenerate the contract table and re-run the tier-1 replay with its three standard flags, `unknown_ledger.py`, `predicate_mutants.py`, `tip_mutants.py`, `volume_mutants.py` and `region_oracle.py` into `outputs/plr-sema/*_260909_inc6.json` or later, publishing the delta against the `260908_inc6` set — satisfying **AC-15.6** and **AC-15.10**, whose floor of ≥ 1 achieved `WILL_FAIL` at the raised index on mutators (a) and (b) is the number this row exists to move, with `unsound == 0` in both directions, `n_findings_decided >= 1,563`, and m1/m2/v1/tier-2b unchanged | ~80 | **T32** (the refinement is a response to what T32 measured; §15.16.3 R1) | Sonnet — the row *unblocks* `WILL_FAIL` on a population that could not previously emit one, so the non-regression re-run is the substance of it and the tier-1 `unsound == 0` is the thing at risk |
| **T33** | Lint and index: add `SPEC_INCREMENT_6` to `plr-sema/tests/test_spec_lint.py:28-37`'s constants and parametrise it into both live-spec tests (`plr-sema/tests/test_spec_lint.py:212-255`); regenerate `.praxia/docs/INDEX.md`; **actually run the lint and record the result** — AC-15.11 was a prediction no one in round 1 could execute | modify `plr-sema/tests/test_spec_lint.py`; regenerate `.praxia/docs/INDEX.md` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_spec_lint.py -q` — satisfying **AC-15.11** | ~6 | — | Haiku |
| **T34** | **CONDITIONAL — do not start. Q2's round-1 disposition is DEFER (§15.6, reaffirmed with a corrected cost argument), so this row belongs to increment 7.** Tier (ii) (#4981): `get_strictness` as an `env` member; the observation record for backend class and signature, deck membership, head channel count and lid topology; the backend-signature derivation with its measured selection; `cache_key` partitioning | modify `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/src/plr_sema/check/ir.py`, `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/eval/oracle_common.py`, `training/verify/verifier.py`, `plr-sema/tests/test_cache.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_cache.py -q`; `uv run pytest training/tests/test_verify_postconditions.py -q` — satisfying **AC-15.12** | ~300 | increment 7 | Sonnet |

**Sizing note, revised honestly after round 1.** T30 grew ~420 → **~530**: `param_defaults` is ~30 LOC
of new derivation (D1), O1 is ~40 rather than ~25 and is a *new* element walk rather than an extension
of `resource_types_from_kwargs` (C11a), the heterogeneous-parent rule is ~5 more, and blocks (2)'s two
new counts — D2's `channels_for_call` tally and the name-coincidence exposure — are ~35 together.
T31 grew ~450 → **~560**: three E-UNCOND clauses, three E-CALL clauses, the restated E-TYPE, the
derived tier-(iii) path, the nested-`Opaque` rule, and roughly a dozen new fixtures. T32 **shrank**
~380 → **~300**, because deleting the fence narrowing removes an entire comparison path and its
published count. **T30 at ~530 is past one session and splits cleanly** at the grammar (G0–G6, pure,
with its own fixtures) versus the idioms plus `param_defaults` plus O1 plus the measurement script.
**Do not split T30 from T31 across a sprint boundary in the other direction**: a landed T31 without
T30's published measurement is the configuration §15.9's gate exists to prevent.
**T35 is ~145** (was ~120 as T30c, before round 2): roughly 55 for the three productions plus
`contains_env_ref`, the `Var("self")` invariant and the JSON round-trip; **~25 for round 2's additions
— G7's PLR-layer index test and its fail-closed default, the α/β-substituted walk, and
`n_env_ref_refused_plr_layer`** (the `Zip`-resolution, comprehension-target and membership rules are
*negative* LOC on the derive side, since the deleted deciding branch was never written); ~10 for the
remaining family-dispatch fix-up, fix-up (1) having landed; ~40 for block (6) and the
per-cluster/per-op `n_env_ref_nodes`/`n_env_ref` fields; ~15 for round 2's five new fixtures.
**T36 is ~80**: ~35 for the three AST tests and their assembly into `reachability_clear`, ~10 for the
additive field plus its `to_json`/`from_json` round-trip and the `None`-on-absent default, ~10 for
replacing T31's hardcoded `None` at the evaluator's call sites, and ~25 for the four AC-15.6 fixtures.
The regeneration and the five re-runs are cost in wall-clock, not in LOC — which is the honest shape of
a refinement row and the reason it is **not** folded into T33. It does
**not** grow T31, which gains E-ENV as a short evaluation rule and the §15.7 reason rule as a
three-branch decision — the amendment's cost is concentrated in the derive side and in what gets
published, which is where its inspectability lives.

**One item this document deliberately does NOT budget: the delegate→caller argument map.** §15.4's
E-CALL(depth) forbids the resolution rather than building it. Building it — a `delegate_arg_binding`
map over both positional and keyword arguments, matched against the delegate's own `ast.arguments`,
fail-closed on `*args`/`**kwargs`/`Starred`/a delegate called more than once, using P9's shipped
singleton test (`plr-sema/src/plr_sema/derive/receiver_state.py:957-959`) — is **~90 LOC over a new
derived field with its own measured selection and its own registry argument**. It would land `:875`
and `:117`, and it belongs in increment 7 with the tier-(ii) work.

---

## 15.13 Not in this increment

- **Tier (ii), under §15.6's recommendation.** The backend signature (`liquid_handler.py:375`,
  `:383`), deck membership (`:321`), head channel count (`:409`), lid topology (`:116`/`:117`, and
  increment 4 §13.1's lid disposition stands), `can_pick_up_tip` (`:514`), and the well-seeding
  observation that would move `volume_state_unknown`.
- **A third binding idiom (γ), the bounded literal-display loop.** `for n, p in [("resources", resources), …]`
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:981-989`) is a `for` over an
  `ast.List` of `(str, Name)` tuples whose trip count and per-iteration binding are both syntactically
  evident, and it is the **only** thing standing between `aspirate`/`dispense` and a
  `{guard_env_dependent}`-only residual (§15.9). **Round 1 disposed it: NOT adopted, deferred to
  increment 7, to be revisited alongside the `pred`-aware `BRANCH`** (§15.14 Q3). It is a *loop*
  recognition rule and therefore lands in increment 5 §14.6 R1's territory; this round already
  conceded eight blocking items, and D1's `param_defaults` restores `transfer`'s three guards at
  strictly lower risk. Adopting γ would grow T30 by roughly 60 further lines on top of the ~530 it
  already carries.
- **A fourth idiom for loop-append bindings** (`tips = []` then `tips.append(...)`,
  `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:653-658`) and for
  `n = len(<param>)` (`:819`). Both are real, both are needed by `drop_tips`/`discard_tips`, and both
  are a general dataflow pass by another name.
- **Four productions the 260907 amendment CONSIDERED and did NOT adopt, named individually because
  each would have flipped a further method's residual and that is precisely why they are refused.**
  *(A fifth, withdrawn in round 2 after the amendment had already granted it, follows this group.)*
  The amendment's mandate was the two `self`-rooted blockers on the gate candidate; adopting a
  production *because* it moves some other method's residual is the anti-gaming failure §15.9's box
  exists to prevent, and each of these is a real production with its own soundness argument to make in
  its own increment.
  - **A general `Identity(Term, Term)` for `x is y`.** `:116`'s `lidded is resource`
    (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:116`) is the single blocker
    keeping `aspirate` (77 ops), `dispense` (40), `transfer` (19) and `stamp` (27) — 163 operations,
    30% of the benchmark — from `{decidable, guard_env_dependent}`. `Is` deliberately admits only the
    constant `None` on its right
    (`plr-sema/src/plr_sema/derive/predicate_ast.py:251-259`). Generalising it is ~15 LOC and would
    make four more methods GO candidates, which is exactly the reason to refuse it here: it is not an
    environment-read recognition, it decides object identity — a relation the IR models nowhere — and
    it belongs with increment 7's lid topology, which is what `:116` actually needs.
  - **Tuple-display comparison** (`:2030`'s
    `(source.num_items_x, source.num_items_y) == (target.num_items_x, target.num_items_y)`) — a
    `Term` for `ast.Tuple` displays, elementwise `Cmp`. Increment 7.
  - **Arithmetic `BinOp` terms** — `:2211`'s modulo, and the subtraction at `volume_tracker.py`'s
    `:91`. This is
    Open decision 2's territory (G5) and the volume family's; unchanged.
  - **`EnvRef` path lookup against an observation.** Forbidden outright by §15.4 E-ENV in this
    increment; it *is* increment 7's tier (ii) and T34's row.
- **A FIFTH refused production, withdrawn in round 2 after the amendment had already granted it: the
  membership DECIDING case (A-C2/A-C10).** spec_version 18's G8(2) let a membership `Cmp` evaluate
  `T`/`F` when its right operand resolved to a concrete `Seq` of hashable `Lit`s and its left to a
  `Lit`. **That branch is deleted; every `in`/`not in` `Cmp` is ½ unconditionally this increment**
  (§15.4 E-ENV). Three independent reasons, each sufficient: **(a) nothing can reach it** — there is no
  `ast.List`/`ast.Tuple` display production in `Term` (`_parse_term`,
  `plr-sema/src/plr_sema/derive/predicate_ast.py:518-539`), and this amendment adds none, so a literal
  container RHS is `Opaque` and only a `Var` resolving to an `ir.Seq` from `call.kwargs` remains;
  **(b) its measured population at this pin is zero**, with no fixture and no published counter — it
  would have shipped an evaluator branch capable of emitting a definite verdict that nothing exercises;
  and **(c) soundness** — deciding `not in` ⇒ `T` requires the `Seq` to be **complete** rather than a
  lower bound, and §15.4 asserts that of an `ir.Seq` nowhere. Deleting it is also what makes §15.4's
  *"the amendment decides nothing"* a theorem rather than a prediction, which is the property §15.9's
  anti-gaming box needs and could not otherwise have.
  **Reopening condition, stated so this is a deferral and not a taboo:** the branch may be re-adopted
  in the increment that (i) adds a literal-container `Term` production, (ii) states normatively whether
  an `ir.Seq` is complete or a lower bound, and (iii) publishes a measured population plus a
  per-decision counter beside `n_decided_via_env_ref_shortcircuit`. Absent all three it stays refused.
- **Numeric `Cmp` outside the volume bridge.** Open decision 2's resolution stands unchanged (G5).
- **A `pred`-aware `BRANCH`** (increment 3 §12.3.6 B2). The same evaluator serves it and it is the
  natural increment 7 alongside tier (ii).
- **Replacing §8's hand-written-contract bridge.** The main spec's boundary row says (c) replaces the
  string-mention bridge "wholesale"
  (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2534`) and adds "must be replaced *before*
  §8 is ever made gating". §8 is **not** gating (AC-8.3), so the replacement is deferred, and this
  document records the debt rather than discharging it: the grammar this increment ships is the
  machinery §8.1's `requires_tips` comparison needs
  (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2111-2117`), and rewiring §8 onto it is a
  separate task with its own disagreement-rate measurement.
- **The delegate→caller argument map**, forbidden by §15.4's E-CALL(depth) and sized at ~90 LOC in
  §15.12's sizing note. Increment 7, with tier (ii).
- **A site-keyed soundness-fence narrowing.** The ~3-line `traceback.extract_tb(...)[-1]` capture at
  `training/verify/verifier.py:143` that would let the fence distinguish a backend re-raise from a
  PLR-layer raise is increment 7's, where a joined `SAFE` first becomes possible (§15.5).
- **Precision targets.** Deferred row (f) stands
  (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2524`). AC-15.8's floor of ≥ 223 decided
  findings is a *floor against a null result*, not a target — and it replaces the draft's ≥ 1,000
  converted findings, which round 1 showed was met by the reason rename alone (§15.10).
- **#4923 / #4924** — decision hooks only, per the plan's §3.5–3.6. **#4956** is the Coxswain track.

---

## 15.14 The eight questions, and their dispositions

**All seven are now closed. Four were disposed by argument or measurement in round 1; the three that
were the user's — Q4, Q5 and Q7 — were answered on 260907, together with Q3's confirmation and one new
question the measurement raised (Q8, the amendment)
(`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:262-265`). Nothing in this section is
pending.**

1. **Q1 — is the coupling in §15.5 real, and does the sprint's headline move? DISPOSED: the coupling
   holds; the substitution was APPROVED BY THE USER 260907 (Q7).** The stated refutation criterion
   was *"name one executed operation whose non-(iii) residual is empty."* The re-run ledger answers it
   by measurement: `_check_args`'s two tier-(ii) guards carry `n_ops_blocked` 544 with `per_method`
   summing to 544 (§15.0), so **no such operation exists**. The challenger's proposed refutation — 12
   unaccounted operations — was arithmetic: they are duplicate `move_*` occurrences the pre-fix
   `(row_id, op_id)` set keying folded away, now published in `collision_ops`. The coupling is
   additionally now structural via tier (iii) ⇒ `UNKNOWN`.
2. **Q2 — does §15.6's evidence close tier (ii)? DISPOSED: DEFER stands, with a corrected reason.**
   `strictness == Strictness.STRICT` is gated behind `len(extra) > 0` in its own enclosing scope
   (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:380-383`), so the one cheap `env`
   member converts no guard — round 1 conceded this half outright. It also showed the draft's *cost*
   argument was wrong: on the frozen benchmark the backend is one named literal class, not a surface.
   **The corrected disposition is "deferred because the general derivation is a new class surface with
   its own measured selection, and because the increment already carries more soundness risk than it
   can absorb"** — not "because the specific case is expensive" (§15.6).
3. **Q3 — does γ (§15.13) belong in this increment? DISPOSED: no — and CONFIRMED by the user 260907
   (decision 3, "γ not adopted"). Deferred to increment 7, to be
   revisited alongside the `pred`-aware `BRANCH`.** Without it `aspirate` and `dispense` — 117 of 544
   operations — keep a `guard_predicate_unparsed` residual and the gate rests on `pick_up_tips` alone,
   which is a real cost and is stated as one. Against it: γ is a loop-recognition rule in increment 5
   R1's territory, this round already conceded eight blocking items, and D1's `param_defaults`
   restores `transfer`'s three guards at lower risk.
4. **Q4 — two new reasons, or one? APPROVED BY THE USER 260907: two.** Shipping both exhausts
   HM-14 at 12 of 12 (`plr-sema/src/plr_sema/verdict.py:133-168`). §15.7's mechanical
   distinguishability test — *did every free name resolve?* — survived round 1, and item 3's widening
   of `guard_env_dependent` to cover unestablished reachability makes that member carry strictly more
   traffic than the draft anticipated. **The one-member fallback is described in §15.7 and costs the
   distinction that scopes increment 7 plus one of the GO gate's two zero-conditions.**
5. **Q5 — is §15.8's "neither HM-24 nor HM-25" position sound? DISPOSED: no. HM-25 `declared` 8 → 9,
   APPROVED BY THE USER 260907.** The position rested on reason 1, and round 1 broke
   reason 1 two ways (the unconstrained iterand, and the unspecified delegate→caller substitution).
   Both are repaired by new normative clauses in this revision, which is not the same as reason 1
   having held. The correct row is **HM-25**, not HM-24 — loud, exact-count-gated, same idiom family
   as the P3a entry already on it (`plr-sema/src/plr_sema/_hand_maintained.py:899-906`). `live_rows()`
   stays 24; no row is added and no cap conversation opens.
6. **Q6 — does §15.5's `excludes_sites` weaken the fence more than it appears? DISPOSED: yes, and the
   narrowing is deleted.** The requested construction exists and is easy: any `TypeError` row. There
   is no `exc_class → site` mapping that could be total or injective — the shipped taxonomy covers 132
   PLR-defined classes and none of the builtins the benchmark raises
   (`training/verify/data/plr_exception_taxonomy.json:1-29`), the runtime side captures no traceback,
   and `TypeError` is raised at four PLR precondition sites *and* re-raised at `:576`. The narrowing
   also purchased nothing, because §15.5 proves no joined `SAFE` is reachable for it to protect. The
   fence is now the unmodified `plr-sema/eval/oracle_common.py:645-647` and
   `rows_excused_by_scope` is a pure annotation.
7. **Q7 (raised by round 1) — the headline substitution itself. APPROVED BY THE USER 260907:
   substituted.** Formally distinct from Q1, which is the technical claim; Q7 is what the sprint may
   say it delivered. The sprint's deliverable is per-finding `SAFE`, a `WILL_FAIL` on a decidable and
   reachable violation, and a residual that names the missing observation per guard; **the first
   joined `SAFE` on a real operation is increment 7's.** See §15.5's decision box.
8. **Q8 (raised by the T30 measurement, not by round 1) — the NO-GO: accept it, or amend the grammar?
   APPROVED BY THE USER 260907: amend, narrowly, as spec_version 18, with a short adversarial pass.**
   The two blockers on the only GO candidate are `self`-rooted environment reads the grammar had no
   production for, so the residual was being charged to `guard_predicate_unparsed` — "the grammar
   failed here" — when the true residual is a missing observation. The amendment is §15.2 G7/G8,
   §15.4 E-ENV and §15.7's reason rule; its anti-gaming argument is §15.9's box; its registry
   disposition is §15.8's; and its own falsification set is §15.9's re-prediction table plus block
   (6). **What was NOT approved and is not taken here**: any production that would flip a *second*
   method's residual (§15.13's four, now five), any environment *read* (§15.4 E-ENV), and any further
   ceiling or vocabulary spend (§15.8).
   **The short adversarial pass RAN on 260907** and its thirteen objections are dispositioned in
   §15.16.2. It returned `needs_revision` as a revise-and-advance, left the GO prediction intact, and
   made the amendment strictly narrower: G7 shape (2) gained a PLR-layer refusal test, the membership
   deciding case was deleted, `Zip` resolution was pinned, and §15.8's registry position was conceded
   to the fallback. **One item it surfaced is owed back to the user at sprint close** — the
   `in`/`not in` widening was not one of the two productions decision 5 named (A-C7).

---

## 15.15 Implementation record

*(Column shape mirrors increment 5 §14.17. Band B landed T30 and T35; band C landed T31 and T32. T36
is the refinement §15.4 and §15.16.3 R1 describe and is not started; T33 and T34 are not started.)*

| row | commit | what landed | measured vs the spec's expectation | divergences |
|---|---|---|---|---|
| T30 | `58e5c3fc` (T30a), `7c0fe59a` (T30b-1), `6cbbe442` (T30b-2) | Typed mini-AST + total `parse`; `InlinedGuard.predicate` (`condition` retained); `param_defaults`; α/β bindings with the iterand single-write and β-preserving rebinding; O1 element types (default-off); `t30_measure.py` with the five blocks and the reason-based gate | Parse: 7,528 guards, 6,295 non-`Opaque`, 1,233 `Opaque`, 925 nested-`Opaque`. Bindings: α **5** (predicted ≥ 3), β **11** (predicted 8 — extras at transfer line 1353 and two in VantageBackend). `param_defaults`: transfer's target_vols/ratios/source_vol and pick_up_tips' offsets/use_channels all `null`, as D1 requires. Heterogeneous parents: **0**. D2: `channels_for_call` non-`None` on **every** executed pick_up_tips op (floor met); tip_spots lowers as `ir.Seq` on all. Name-coincidence exposure: 936 depth≥1 occurrences. O1 delta: 389 ops differ; with O1 `guard_operand_unknown` is **0** everywhere (§15.4's O1 claim holds). **GATE: NO-GO** — no executed op reaches zero `guard_predicate_unparsed`; pick_up_tips' residual is {decidable, guard_env_dependent, guard_predicate_unparsed}, the last carried by two guards: line 409 (α binds invalid_channels but the filter `c not in self.head` is `Opaque` ⇒ §15.7's nested-`Opaque` rule) and line 514 (`zip(...)` is not a G1 `Term` ⇒ `Opaque`). Per §15.9: derive code kept, T31 not started, decision to the user | (1) §15.9's prediction table called line 409 `guard_env_dependent`; §15.7's nested-`Opaque` rule, whose worked example is that very site, assigns `guard_predicate_unparsed` — an internal §15.7/§15.9 inconsistency the measurement exposed. Both blockers are expressions rooted at `self.` (head, backend): tier (ii) by §15.1's definition, but the grammar has no production that recognises an environment read as such. Proposed amendment for the user (spec_version 18): an `EnvRef` leaf (expression rooted at `self.`, optionally called with `Term` args) that evaluates ½ and carries `guard_env_dependent`, plus `zip(Term, Term)` as a `Term`. **APPROVED by the user 260907 and now normative as §15.2 G7/G8, §15.4 E-ENV and §15.7's reason rule; T35 (renamed from T30c in round 2, A-C9) re-measures.** (2) `t30_measure.py` re-implemented `run_row`'s gating and counted 923 ops (pick_up_tips 361) against the ledger's 544 (223); per-site classification is population-independent so the verdict stands. **FIXED in `15b84d31`**: the population is now sourced from `oracle_replay.main()` itself and re-measured at 544 / 223 into `outputs/plr-sema/t30_measured_260907.json`; named cause = `row_to_verifier_inputs` called without the sidecar's `ambiguity_class`, which sets `skip_reason` there. (3) The measured report is `outputs/plr-sema/t30_measured_260905.json` (the text above said 260904). |
| T35 | `a2cd0499`, `100ab273` | The 260907 amendment as revised by round 2: `EnvRef`, `Zip` and the `in`/`not in` comparators in the mini-AST and in `parse`; **G7's PLR-layer index test on shape (2)**, applied where the `function_index` already lives and fail-closed to `Opaque` when none is supplied; `contains_env_ref` beside `contains_opaque`, **both over the α/β-substituted tree** via the general `substitute` helper; the `Zip` resolution rule and the comprehension-target ⊤ rule; membership `Cmp` at ½ with **no** deciding branch shipped; the `Var("self")` invariant; `to_json`/`from_json` for both new kinds, with `EnvRef` in both kind sets; contract table regenerated; `t30_measure.py`'s family dispatch fix-up; blocks (3), (4) and (6) published | **GATE: GO.** `pick_up_tips` reaches zero `guard_predicate_unparsed` and zero `guard_operand_unknown` on **223 of 223** executed operations with O1 — residual exactly {`decidable`, `guard_env_dependent`}, which is §15.9's restated GO condition, met by the method §15.9 named in advance. Whole table: **386** guard sites carry an `EnvRef` over **417** nodes; `n_env_ref_refused_plr_layer` **12**, so A-C1's index test is doing work rather than being vacuous; `n_var_self` **0** (A6's invariant holds); `n_zip` **1**, the single `:514` site, as predicted; `n_membership_cmp` **48**. **Every method matched §15.9's re-prediction table exactly**, cell for cell as a guards/nodes pair — including `stamp` at **0 / 0**, the cell round 2's PLR-layer test was introduced to hold and the one an unnarrowed shape (2) would have flipped. Report: `outputs/plr-sema/t30_measured_260908.json` | **None on the re-prediction table** — no cell diverged in either direction, which is the first time a prediction table in this document survived its own measurement intact. The GO is O1-conditional exactly as §15.4's disclosure states, and `:498` is the guard carrying that conditionality, visible as T32's 216/223. |
| T31 | `1a58b337`, `436c0edb` | `check/predicate.py`: **E-CALL** (`param_defaults` step (2), E-CALL(5) parameter-rebinding, E-CALL(β) truthiness, E-CALL(depth) forbiddance), the **restated E-TYPE**, **E-SCOPE** over `scope_trail[1:]`, **E-VERDICT**, **E-UNCOND (1)–(6)**, **E-ENV**, and §15.7's **reordered** clause order (`contains_opaque`, then the operand test, then `contains_env_ref`); tier (iii) derived from `is_dynamic_raise`, emitting one `UNKNOWN`/`guard_env_dependent` finding plus an `excludes_sites` entry; dispatch that skips guards the tip and volume families claim; `SoundnessScope(excludes_sites)` and `AnalysisReport.scope` | Registry arithmetic exactly as AC-15.7 asserts: `REASON_VOCABULARY` **12** against HM-14's unchanged `declared` 12, with the parent at 10 so the diff reads 10 → 12; `len(live_rows())` **24** against `BUDGET_CAP` 24; HM-25 `declared` **9** and HM-24 **3**. Per A-C6, HM-25 is measured by **one collective probe** that imports α, β, `EnvRef`, `Zip` and the membership comparators, so the entry's measure moves with its `what`; the measured count did **not** exceed 9, so the STOP-and-ask contingency did not fire. `REASON_VOCABULARY` is 12 of 12 — HM-14's headroom is now exhausted, as §15.8 said it would be | **Four implemented deviations, every one narrower than the spec text and every one fail-closed; §15.16.3 R2 records the first three and R1 the fourth.** (a) **E-CALL(5) is implemented only through the β mechanism** — no wire field detects any other rebinding shape, so a parameter rebound by a statement β does not model is simply not recognised as rebound. (b) **E-TYPE's subclass relation is an optional `class_hierarchy` argument, `None` in production**, so the `T` clause degenerates to exact-name equality: `:498` still decides (`TipSpot` against `TipSpot`) and the gate is unaffected, but `Well ⊂ Container` cases such as `:875` stay ½ instead of reaching `T` — strictly less decisive, never more. (c) **E-UNCOND way (3), the structural R1 `for_span` test, is unsatisfiable for an `InlinedGuard`**, which carries no `for_span` field; the way exists in code and cannot fire this increment. (d) **E-UNCOND(5) takes `k_reachability_clear: bool | None` and every production caller passes `None`**, so **no depth-0 empty-trail guard can emit `WILL_FAIL` at all**. (d) is the deviation T32 then measured as the unmet mutant floor; §15.4's clause (5) is refined at spec_version 20 and T36 wires the field. |
| T32 | `e3970b3a`, `f63b3ff8` | Tier-1 re-run under the **unmodified** unsoundness predicate with no `exc_class` anywhere in the comparison path; `n_findings_decided` published per PLR site; the after-ledger with its delta; `plr-sema/eval/predicate_mutants.py` with p1's three mutators; the m1/m2/v1/tier-2b non-regression set | `outputs/plr-sema/oracle_replay_260908_inc6.json`: **343** rows executed over **548** operations, **0 unsound**, crosscheck **191/191** at agreement 1.0, `rows_setup_error` 0, `rows_excused_by_scope` **0** (annotation, no threshold). **`n_findings_decided` 1,563** against the ≥ 223 floor — seven times over — with `:502`, `:522` and `:535` at 223/223 each, `:498` at **216/223** (the O1-dependent seven), `drop_tips`'s `:647` at 31/31 and `transfer`'s `:1335`/`:1337` at 19/19. `n_findings_by_reason`: `guard_env_dependent` 4,138, **`guard_predicate_unparsed` 495** (from 5,656), `volume_state_unknown` 194, `unresolved_delegate` 186, `guard_operand_unknown` 144. `unknown_rate_by_method` **1.0 everywhere** — no joined `SAFE` on any operation, which is §15.5's central finding confirmed and predicted, not a shortfall. Check-only elapsed **18.8 s**, from 35.8 s. After-ledger `outputs/plr-sema/unknown_ledger_260908_after.json`: `consistency.ok`, `n_ops_unknown` 544 → 544, clusters 54 → **53**, findings 6,036 → **5,157**, four clusters gone (`:502`, `:522`, `:1335`, `:1337`) and 40 renamed to `guard_env_dependent`/`guard_operand_unknown`; `pick_up_tips`'s residual is **exactly {`guard_env_dependent`}** on all 223. Non-regression exact: m1 199/199, m2 289/289, v1 67/67, tier 2b 16/0/7/3 | **(1) AC-15.10's floor is NOT MET.** p1 reported (a) 288 raised / **0 achieved** / 0 unsound, (b) 16 / **0** / 0, (c) 288 / 0 / 0 (`outputs/plr-sema/predicate_mutants_260908_inc6.json`). (c)'s zero is what §15.10 predicts. (a)'s and (b)'s are not, and the cause is neither the mutators nor E-CALL(β): both target depth-0 empty-trail guards standing below `pick_up_tips`'s conditional `raise TypeError`, which spec_version 19's E-UNCOND(5) blocked and T31's `None` input blocked a second time. Remedied by §15.4's refined clause (5); **the floor is retained and re-measured at T36**. **(2) O1 was found unwired in `oracle_replay.main` and was enabled there.** `observe_element_types` was reaching `t30_measure.py` but not the replay, so every tier-1 run before this row was measured without it. Enabling it moved **nothing** — unsound, crosscheck and row counts are identical with and without — so no published number is retracted; it is recorded (§15.16.3 R3) because an instrument gap that happens to be inert is still an instrument gap, and the next observation added may not be inert. **(3) Static-vs-evaluator agreement is 254/544 (46.7 %), 2 of 10 methods exact.** Every divergence is either a family-owned reason the structural classifier never attributes (`volume_state_unknown`, `unresolved_delegate`) or an over-predicted `decidable` on `stamp`/`discard_tips`; §15.10 records what this means and fixes the classifier's status as a prediction instrument only. |
| T36 | `f82ce87d` | `derive.bindings.compute_reachability_clear(K, guard_lineno)` (no earlier `Return`; not enclosed by `Try`/`With`; no earlier `Break`/`Continue`; an earlier `Raise`/`assert` does NOT block); additive `InlinedGuard.reachability_clear` on the wire (absent ⇒ fail-closed); `check_ir` feeds it to the evaluator's `k_reachability_clear`; contract table regenerated | Ten named sites: pick_up_tips 498/502/514/522/576, aspirate 959/990, dispense 1153/1202 all `True`; `_check_no_lid` 117 `False` (blocked by the `return` at line 114). **p1 mutants** (`outputs/plr-sema/predicate_mutants_260909_inc6.json`): (a) duplicate use_channels **288/288** WILL_FAIL at the raised index (was 0), (b) short offsets **16/16** (was 0), (c) non-TipSpot 0/288 as the spec asserts; **0 unsound** in every class — AC-15.10's floor MET. Tier 1 (`oracle_replay_260909_inc6.json`): 343/548/191, **0 unsound**, `n_findings_decided` 1,563, byte-identical to the 260908 run except timing — no new WILL_FAIL on any real row. Non-regression exact: m1 199/199, m2 289/289, v1 67/67, tier 2b 16/0/7/3; after-ledger `consistency.ok`, 544/544, 53 clusters, 5,157 findings | None against the refined clause. Note: the refinement (§15.16.3 R1) widens WILL_FAIL and was not adversarially reviewed; the fence (0 unsound on tier 1 and on all three mutant classes) is its only evidence this sprint — first candidate for the next pass. |
| T33 | (close pass, this document's final commit) | `SPEC_INCREMENT_6` registered in `plr-sema/tests/test_spec_lint.py` (landed with the round-1 remediation); citation re-anchors after T30a/T30b/T35/T31/T32/T36 across all seven specs; INDEX regenerated | `test_spec_lint.py` **26 passed**; `check_spec_citations.py` per spec: main 80/0 failing, increment 1 109/0, increment 2 88/0, increment 3 112/0, increment 4 118/0, increment 5 229/0, increment 6 **401/0**; AC gating 0 violations; INDEX regenerated by `docs index` | None. The lint enforces this document from spec_version 17 onward; every band's fixer re-anchored the citations its edits shifted (listed in each commit). |
| T34 | — | — | — | — |

---

## 15.16 Round-1 disposition

**Round 1 was `praxia:spec-challenger` (C1–C18) against `praxia:spec-defender` (adjudications plus
three defender-identified gaps D1–D3), both at Opus, both against spec_version 16 at commit
`6407d92a`. Verdict on both sides: `needs_revision`.** This table records what each objection did to
the text. "Adopted" means the remedy is now normative here; "adopted (defender's form)" means the
challenger's diagnosis was accepted and his proposed remedy was replaced; "rebutted" means the text
did not change on the merits.

| id | disposition | what changed in the text | § touched |
|---|---|---|---|
| **C1** | adopted, magnitude corrected | E-UNCOND(5): a depth-0 empty `scope_trail` is not vacuously unconditional unless `K` has no earlier `Return`/`Try`/`Raise`/`Break`/`Continue`. The shipped `volume_guard_is_unconditional` precedent is named as implementing the *wrong* reading. Population is `:117` (163 ops) + `:2092` (93), not the filed ~268: `:1770`/`:1920` have three-deep `"else of: if …"` trails and were already blocked | §15.2 G0, §15.4 E-UNCOND(5), §15.1.4, AC-15.6 |
| **C2** | conceded in full | `InlinedGuard` has no `caller_scope`; E-SCOPE's bridged-guard clause is deleted. Remedy is the forbiddance, not the field: **E-UNCOND(4)**, no `WILL_FAIL` at `depth >= 1` | §15.4 E-SCOPE, E-UNCOND(4), AC-15.6 |
| **C3** | adopted (drop the narrowing); "no taxonomy exists" rebutted | The fence narrowing is **deleted**; the predicate stays `oracle_common.py:645-647` unmodified and `rows_excused_by_scope` becomes a pure annotation. A taxonomy does exist but covers 132 PLR-defined classes and none of the builtins or re-raise sites, and cannot be injective | §15.5, §15.10, AC-15.8, §15.14 Q6 |
| **C4** | conceded in full | E-TYPE restated: `T` iff is-or-subclass-of, `F` iff hierarchy-disjoint **and** exact, ½ otherwise; a `_generic_plr_type_name` declaration is normatively never exact, so the `F` branch is unreachable on the benchmark. Kills a live false `WILL_FAIL` on 65 `drop_tips`/`discard_tips` ops and restores the `:875` type reasoning | §15.4 E-TYPE, §15.1.2, AC-15.1 |
| **C5** | conceded | The ≥ 1,000-converted floor is replaced by **`n_findings_decided ≥ 223`**, per PLR site, with `guard_env_dependent`/`guard_operand_unknown` published separately and excluded; the `guard_predicate_unparsed` delta keeps no floor | AC-15.8, §15.10, §15.13 |
| **C6** | consequence 1 rebutted with a narrower clause; 2 and 3 conceded | **β-preserving rebinding** clause (a single length-preserving `ast.ListComp` over `x` itself) keeps β's population at **eight**, published as a measurement. The `:1185`/`:1188` "cleanest result" paragraph is **deleted**, and §15.9's `dispense` row corrected. The challenger's own suggested narrowing is recorded as dead (it saves none of the six) | §15.3, §15.1.3, §15.9, AC-15.2 |
| **C7** | (a) conceded; (b) literal conceded, collision rebutted | **E-CALL(5)**: a `Var` naming a parameter written below the guard resolves to ⊤. The P3a hook is restated over the receiver's **derived** `channel_kwarg`/`channel_default_param`, never the forbidden literal `"use_channels"`. No ordering collision exists: `channels_for_call` already resolves the kwarg first | §15.3 β, §15.4 E-CALL(5), AC-15.2 |
| **C8** | site-list horn rebutted; tautology conceded, and his remedy rejected | Tier (iii) is **derived** from `guard.is_dynamic_raise` (seven `raise <name>` sites at this pin), zero registry cost. His proposed derived (i)/(ii) tiering is rejected as **self-satisfying**; the GO gate is restated over **reasons**. `:117` retiered, `:2092` added to the `move_*` enumeration | §15.1 (new box), §15.1.3, §15.1.4, §15.9 |
| **C9** | contradiction conceded; his remedy rejected as unsound | Tier (iii) emits **one `Finding`, `UNKNOWN`, `guard_env_dependent`** plus an `excludes_sites` entry. Emitting `SAFE` would let `join` claim the backend did not raise — A-COMPLETES on the current operation. `guard_env_dependent`'s definition widened by one clause for unestablished reachability | §15.5, §15.7, AC-15.5(iv), AC-15.6 |
| **C10** | conceded, all four parts | `SoundnessScope` has exactly one field, `excludes_sites: tuple[PlrSite, ...]`; the `excludes`/`harness_internal` sentence is deleted; the type is stated as **new in this increment**; the two non-definitional citations are replaced by a motivation reference | §15.5 |
| **C11** | (a) fact conceded / sizing rebutted; (b) conceded; (c) conceded as disclosure | O1 restated as a **new element walk** (~40 LOC, not ~25 "over data the harness already computes"); **heterogeneous-parent singleton rule** with `element_type = None` fail-closed and a published count; the tier-(ii)-dependence of the GO is stated plainly in this document's own words | §15.4 O1, §15.9, AC-15.4 |
| **C12** | **REBUTTED on the merits, but the instrument was fixed anyway** | The 93/81 and 544/532 gaps were `(row_id, op_id)` set dedup under content-digest collisions, not unaccounted operations. Item 17 re-keyed the ledger positionally (`ca756bce`); every field now closes at 544/93, `consistency.ok` is `true`, and the 12 collisions are published and are all `move_*`. §15.0's note 2 wording corrected | §15.0 (notes 1–2 + new correction box) |
| **C13** | (1) conceded with a clause; (2) conceded outright; registry **HM-25, not HM-24** | The single-write requirement now ranges over **the iterand** as well as `x`. The delegate→caller substitution is forbidden (E-CALL(depth)) rather than assumed. §15.8's "neither row" position is withdrawn: **HM-25 8 → 9**, approved by the user 260907 | §15.3, §15.4 E-CALL(depth), §15.8, AC-15.7, §15.14 Q5 |
| **C14** | (a) rebutted (and exposes D1); (b) conceded | β is **not** dead: E-CALL step (2) had no data source at all, so resolution fell through to the β binding. **E-CALL(β)** models truthiness in four cases, with `Lit(None)` routed to β rather than to ⊤. `:522` survives C6 and C14 together, so the gate keeps a GO candidate | §15.4 E-CALL(β), §15.9, AC-15.2 |
| **C15** | conceded | **Nested-`Opaque` rule**: a predicate containing any `Opaque` node is `Opaque` for reason assignment, still Kleene-evaluated. Restores §15.7's legibility claim; `:409`'s 384 findings keep `guard_predicate_unparsed` | §15.2 G1, §15.7 |
| **C16** | conceded, textual | The contract-table regeneration moves `contracts_sha`, so the whole cache is **cold after T30 by design**; `env` is untouched, which is the property that matters. T30's gate adds a check that no test pins a literal key | §15.8, §15.12 T30 |
| **C17** | wording conceded; disposition unchanged | Q2's cost argument corrected — the draft priced the general case and charged the specific one for it. DEFER stands on soundness-risk grounds. The `:377-378` early-return fact is recorded as reinforcing E-UNCOND(5) | §15.6, §15.14 Q2 |
| **C18** | conceded, both defects | AC-15.12's producer citation corrected to `oracle_common.py:370-373`; §15.5's two non-definitional `SoundnessScope` citations dropped; §15.0's note-2 "distinct pairs" wording corrected | AC-15.12, §15.5, §15.0 |
| **D1** | adopted (defender-identified **blocker**) | E-CALL step (2)'s "recorded default" did not exist. T30 derives **`param_defaults`** from `ast.arguments.defaults`/`kw_defaults` restricted to `ast.Constant`, fail-closed (~30 LOC). Restores `transfer`'s `:1335`/`:1337`/`:1340` and gives E-CALL(β) case (3) a data source | §15.4 E-CALL(2), §15.1.3, §15.12 T30, AC-15.5 |
| **D2** | adopted (must-measure) | T30 block (2) publishes the count of executed `pick_up_tips` ops for which `channels_for_call` returns non-`None`, floor `== 223`. Without it a `:502` failure would be misattributed to O1 | §15.9(2), §15.12 T30/T32 |
| **D3** | adopted (minor) | **E-UNCOND(6)**: the `raise_guard`'s own condition sits at `scope_trail[0]` and is excluded from both scope tests, which range over `scope_trail[1:]` | §15.4 E-SCOPE, E-UNCOND(6), AC-15.5(i) |

**Items that landed outside this document.** Item 0 (routing the two user decisions) is the
orchestrator's. Item 17 (the ledger `row_id` fix and re-run) landed as `ca756bce`; its results are
folded into §15.0. Item 18's lint execution is T33's, and is the one AC in this document that no one in
round 1 could execute.

### 15.16.1 Amendment record — spec_version 17 → 18 (260907)

**Source: the T30 measurement, not an adversarial round.** Band B landed T30a/T30b, the reason-based
gate measured **NO-GO** (§15.15), and the user approved a narrow grammar amendment plus the four
outstanding decisions (§15.14 Q3–Q8). This table records what the measurement showed and what changed
in the text. A1–A6 were written to be attacked individually, and **they were**: the amendment's short
adversarial pass ran on 260907 and its thirteen objections are dispositioned in §15.16.2, which is why
`status` is now `reviewed-round-2`.

| id | what the measurement showed | what changed in the text | § touched |
|---|---|---|---|
| **A1** | **An internal inconsistency this document shipped in spec_version 17.** §15.9's prediction table said `liquid_handler.py:409` would carry `guard_env_dependent`; §15.7's nested-`Opaque` rule — whose *own* worked example is that site — said `guard_predicate_unparsed`. The measurement reported the latter (`outputs/plr-sema/t30_measured_260905.json:473-482`), correctly, because that is what the normative text said, and the gate turned on the difference. **The inconsistency existed and was not caught by round 1** | §15.7 gains a normative `EnvRef` reason rule that makes the two agree **by rule**: `contains_opaque` first (unchanged), then `contains_env_ref` ⇒ `guard_env_dependent`. The nested-`Opaque` rule is untouched; what changed is that the filter at `:409` no longer contains an `Opaque` node | §15.7, §15.9 |
| **A2** | Both of `pick_up_tips`'s residual blockers are expressions **rooted at the literal name `self`** — the receiver's head and backend, tier (ii) by §15.1's own definition — that the grammar could not recognise as environment reads and therefore charged to the reason meaning "the grammar failed" | **G7, `EnvRef(path, args)`**: two enumerated shapes, admissible in predicate and term position, with a closed negative list and the `Var("self")` invariant; **E-ENV**: ½/⊤ unconditionally, no environment read, no path table; §15.8's registry argument and its fallback; §15.9's anti-gaming box and block (6). **Round 2 narrowed shape (2) (A-C1)** with the PLR-layer index test — a `self.<name>(…)` naming an indexed method of the receiver class stays `Opaque` — and **withdrew §15.8's reason 1 and adopted the fallback (A-C6)**: the productions are named inside the HM-25 entry and `_measure_hm25` must import them | §15.2, §15.4, §15.7, §15.8, §15.9, §15.11, §15.12 |
| **A3** | `:514`'s condition is `not all(<expr> for channel, tip in zip(use_channels, tips))`; `zip(...)` is not a G1 `Term`, so the whole guard was `Opaque` **even though its body would have parsed** once `EnvRef` existed | **G8**: `Zip(items)` as a `Term` admissible **only** as an `AllOf`/`AnyOf` `seq`, with a positional tuple-target arity check; and `_CMP_OPS` widened by `in`/`not in` only. Explicitly recorded: `Zip` does **not** reopen §15.3's β exclusions, because α/β test the `ast.Assign` shape and still require a bare-`ast.Name` iterand. **AMENDMENT-SCOPE ITEM (round 2, A-C7):** decision 5 as put to the user named **two** productions — the `EnvRef` leaf and `zip(<Term>, <Term>)` (`.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:252-260`) — and **not** the `in`/`not in` widening of `_CMP_OPS`. It is taken **in scope of decision 5 by necessity**, on one stated ground: it is the comparator that makes `:409`'s filter `c not in self.head` readable at all, and without it `:409` stays `Opaque` and `pick_up_tips` stays NO-GO, i.e. it is load-bearing for the gate. **To be confirmed with the user at sprint close**; the header box's "nothing is pending" is softened accordingly. **Round 2 also narrowed this row's semantics**: `Zip` resolution is now normative (⊤ unless every item is a concrete `Seq`; quantification over a ⊤ seq is ½, never vacuously `T`), comprehension-bound targets are ⊤, and the membership **deciding** case is deleted outright (§15.13) | §15.2, §15.4, §15.11, §15.13 |
| **A4** | **The population caveat.** `t30_measure.py` re-implements `run_row`'s gating (`plr-sema/eval/t30_measure.py:19-37`) and counts 923 operations against the ledger's 544. The per-site classification is population-independent, so the NO-GO stands; every ratio and per-op count is not | §15.9 gains a normative fix-up box. **LANDED as `15b84d31`, before T35**: the population is sourced from `oracle_replay.main()` itself (`collect_executed_population`, `plr-sema/eval/t30_measure.py:19-38`) and re-measured at 544 / `pick_up_tips` 223 into `outputs/plr-sema/t30_measured_260907.json`, with the named cause recorded (the sidecar's `ambiguity_class` was not passed to `row_to_verifier_inputs`). **The amendment's delta is therefore taken against that report, not against `t30_measured_260905.json`.** AC-15.3 asserts it | §15.9, §15.11, §15.12 |
| **A5** | **A family-dispatch violation in the measurement, not in the analyzer.** Blocks (3)/(4) assigned a predicate reason to `volume_tracker.py:92` and `:105` — `guard_predicate_unparsed` — where the ledger's own reason is `volume_state_unknown` (`outputs/plr-sema/t30_measured_260905.json:733-742`) — §15.2's dispatch rule says the predicate evaluator never sees them. This mis-attributed `aspirate`/`dispense`'s blocker set | The same fix-up box: **T35** skips family-claimed guards and reports the family's own reason. §15.2 G7 additionally records that the dispatch rule, not the grammar, is what keeps family ownership stable — `EnvRef` is receiver-agnostic and `self.get_used_volume()` would otherwise match its shape (round 2 adds a **third** independent mechanism: G7's PLR-layer test refuses it, since `get_used_volume` is an indexed method of its own receiver class) | §15.2, §15.9 |
| **A6** | **`Var("self")` was being treated as a resolvable parameter.** `self` is a parameter of every PLR method, so the shipped classifier's *"is this name a parameter of `K`?"* test (`plr-sema/eval/t30_measure.py:914-926`) accepted it: `self.<x>` guards were reported `decidable_or_operand_dependent` (e.g. `:1185`, `outputs/plr-sema/t30_measured_260905.json:803-812`), and block (2)'s name-coincidence exposure list contains entries whose exposed name is literally `self` (`outputs/plr-sema/t30_measured_260905.json:86-103`) | The `Var("self")` invariant (§15.2 G7): after the amendment no parsed predicate may contain `Var("self")`, fail-closed, asserted as `n_var_self == 0` over the whole contract table (AC-15.1) with `n_opaque_only_by_var_self` published. §15.9 predicts `name_coincidence_exposure_count` **falls** for this reason and requires the fall to be attributed to it | §15.2, §15.9, §15.11 |

**What this amendment deliberately did not do, recorded here because each was available and would have
moved a published number.** It adopted no production that flips a second method's residual (§15.13's
four — five after round 2 withdrew the membership deciding case — of which a general `x is y` would
alone have made `aspirate`/`dispense`/`transfer`/`stamp` — 163
operations — GO candidates); it read no environment; it spent no registry row, no per-row ceiling and
no vocabulary slot; and it edited neither §15.3's idioms nor §15.9's gate condition, which is still
zero `guard_predicate_unparsed` and zero `guard_operand_unknown` on ≥ 1 executed operation.

### 15.16.2 Amendment-pass disposition — spec_version 18 → 19 (260907)

**Source: `praxia:spec-challenger` (Opus) scoped to the amendment delta only, against spec_version 18
at commit `f441d27e`; report persisted at
`.praxia/docs/audits/260907_plr-sema-predicate-amendment-challenger.md`.** Thirteen objections — three
blockers, five must-fix, three should-fix, two notes — verdict **`needs_revision`**, explicitly framed
as **revise-and-advance**. The pass answered its own three questions on the record: **no objection
changes the GO prediction for `pick_up_tips`**; the amendment is **not** gaming the gate; but its
**anti-gaming argument was unsound as written** (sentence 1 measurably false, sentence 2 incomplete,
silent on the gate's second zero-condition). Every objection below is **adopted**; none was rebutted.

| id | class | disposition | what changed in the text | § touched |
|---|---|---|---|---|
| **A-C1** | blocker | adopted — remedy (a), **derived**, plus (b)'s published split | G7 shape (2) admits a `self`-rooted call **only** when `len(path) >= 3` (a read *through* a receiver attribute) **or** its length-2 name is **absent from the derive package's own PLR function index** for the receiver class (`build_plr_function_index`, `plr-sema/src/plr_sema/derive/receiver_state.py:1275-1308`) — a derived test, **no list**. PLR-layer helper calls (`self._is_error_tail`, `self._check_96_head_fits_in_container`, `self._find_available_sites_sorted`) stay `Opaque`, which is the coverage gap `guard_predicate_unparsed` means. `n_env_ref_refused_plr_layer` is published. The *"syntactically narrow … no arbitrary text"* sentence is **withdrawn** and replaced by the measured formulation (210 `self.`-rooted call conditions, 41 of them one shape, plus the refusal count). Fail-closed when no `function_index` is supplied. **The `stamp` row's `:1778`/`:1940` no longer flip** | §15.2 G7, §15.7, §15.9 (box + block 6 + table), §15.11, §15.12 T35, §15.16.1 A2 |
| **A-C2** | blocker | adopted — both uncounted paths closed **by rule**, not counted | With the `Zip`-resolution clause and the deleted membership deciding case, *"the amendment decides nothing"* becomes a **theorem**: the only path to a definite value is Kleene short-circuit over an already-decidable conjunct, published as `n_decided_via_env_ref_shortcircuit` (predicted 0). No `n_decided_via_zip_vacuous` / `n_decided_via_membership` counters are added, deliberately — a counter for a path the semantics forbids would be theatre | §15.4 E-ENV, §15.9 box + block (4) |
| **A-C3** | blocker | adopted verbatim | **Normative:** a `Zip` resolves to ⊤ unless **every** item resolves to a concrete `Seq`, then to the positional zip truncated to the shortest; `AllOf`/`AnyOf` over a ⊤ seq is ½, **never vacuously `T`**. The asymmetry at `:514` is stated (`use_channels` exact via `channels_for_call`; `tips` ⊤ because `[tip_spot.get_tip() for tip_spot in tip_spots]` is a *projecting* comprehension `_parse_filtered` rejects). AC-15.1 fixture (b): `AllOf(Zip(Seq([]), ⊤), <½>)` ⇒ **½** | §15.2 G8(1), §15.4 E-ENV, §15.11 AC-15.1 |
| **A-C4** | must-fix | adopted | **Normative:** both `contains_opaque` and `contains_env_ref` range over the **α/β-substituted** predicate — built by the new general helper `bindings.substitute` (`plr-sema/src/plr_sema/derive/bindings.py:214-230`), which `t30_measure.py`'s classifier now calls explicitly (`plr-sema/eval/t30_measure.py:821-822`; re-anchored, T35 — the pre-T35 shipped classifier's own ad hoc one-level substitution, formerly named `_effective_unparsed`, is retired in favour of it), and which nothing normative said before this pass. AC-15.1 fixture (c) asserts `contains_env_ref` true for the substituted `:409` guard and false for its raw `predicate`. §15.7 additionally records the *second, independent* route by which `:409` reaches `guard_env_dependent`, so the GO survives even if this clause were dropped | §15.2 G7, §15.7, §15.11 AC-15.1 |
| **A-C5** | must-fix | adopted — reordered | §15.7's clauses are now (1) `contains_opaque`, (2) **the operand test** ⇒ `guard_operand_unknown`, (3) `contains_env_ref` ⇒ `guard_env_dependent`, (4) the residual rules. The gate has **two** zero-conditions and the amendment relaxes neither; §15.9's box now says so. AC-15.5(iii) gains a fixture: `self.backend.f(?0)` ⇒ `guard_operand_unknown` | §15.7, §15.9 box, §15.11 AC-15.5 |
| **A-C6** | must-fix | **conceded** | §15.8 reason 1 is **withdrawn** (HM-25's own `what` already books P8's zip-comprehension shape and P3a's `self.<x>` recognition). The stated fallback is now the disposition: `EnvRef`/`Zip`/`in` are named **inside** the α+β HM-25 entry (`declared` stays 8 → 9, approved), **and `_measure_hm25` must import the production symbols** so the entry's measure tracks its `what`. Contingency stated: a measured count above 9 is a **user decision surfaced at T31 before the spend**. The loud-failure argument (reason 2) is kept | §15.8, §15.11 AC-15.7, §15.12 T31 |
| **A-C7** | must-fix | conceded — recorded as amendment scope | The `in`/`not in` widening is recorded in §15.16.1 A3 as an amendment-scope item, **in scope of decision 5 by necessity** (it is the comparator that makes `:409`'s filter readable), **to be confirmed with the user at sprint close**; the header's *"nothing is pending user approval any more"* is softened to distinguish a pending *decision* from a pending *confirmation* | header, §15.16.1 A3 |
| **A-C8** | must-fix | adopted | Block (3)'s field is renamed **`n_env_ref_nodes`**; **`n_env_ref`** keeps the per-guard unit and appears only in block (4). The re-prediction table restates every cell as an exact `guards / nodes` pair with no hedged ranges; `move_*`'s old "4–5" is revealed as **4 / 5**, one count under each definition. AC-15.3 asserts the two names differ because the units do | §15.9 blocks (3)/(4) + table, §15.11 AC-15.3 |
| **A-C9** | should-fix | adopted | The row is renamed **T35**, which `TASK_ROW_RE` accepts (`plr-sema/scripts/check_spec_crossrefs.py:58` — `[a-z]?` is on the `#\d+` alternative only, so `T30c` was invisible to the lint). **AC-15.1 and AC-15.3 move from T30's gate cell to T35's** (T35 ships the final grammar and writes the report the gate is read from); AC-15.5(iii)'s new fixture stays with AC-15.5 on T31. Every AC is gated **exactly once** — `ac_multiply_gated`/`ac_ungated` (`plr-sema/scripts/check_spec_crossrefs.py:148-156`) enforce it, over the gate cell only — and none rides on a landed row. T30's gate cell is corrected to `t30_measured_260905.json`, the population re-run is named as `t30_measured_260907.json` (`15b84d31`), and T35's output is `t30_measured_260908.json` or later | §15.9, §15.11, §15.12, §15.15 |
| **A-C10** | should-fix | adopted — **deleted, not fixtured** | The membership deciding case is removed: every `in`/`not in` `Cmp` is ½ unconditionally. Recorded in §15.13 as a refused production with a three-part reopening condition (a literal-container `Term`; a normative statement of whether an `ir.Seq` is complete or a lower bound; a measured population plus counter). Also strengthens A-C2 | §15.2 G8(2), §15.4 E-ENV, §15.13 |
| **A-C11** | should-fix | adopted, all four | `InlinedGuard` is **nine** fields, none `caller_scope`, at `plr-sema/src/plr_sema/derive/__init__.py:491-499` (three sites re-anchored from the stale `:452-478`); `is_dynamic_raise` is cited at `:501-505` everywhere (§15.1's `:489-493` and the frontmatter's `:499-503` were both wrong; AC-15.6 was already right) | frontmatter, §15.1, §15.2 G0 box, §15.4 E-SCOPE, §15.9 |
| **A-C12** | note | adopted | The `Predicate`/`Term` partition break is recorded normatively: `EnvRef` belongs to **both** `_TERM_KINDS` and `_PREDICATE_KINDS` (`plr-sema/src/plr_sema/derive/predicate_ast.py:943-947`), `from_json` is unaffected because it dispatches on the tag. AC-15.1 fixture (e) pins the `args is None` (read) vs `args == ()` (zero-argument call) round-trip through `to_json`/`from_json` | §15.2 G7, §15.11 AC-15.1, §15.12 T35 |
| **A-C13** | note | adopted — the second option | **Normative:** a name bound by an `AllOf`/`AnyOf` comprehension target resolves to **⊤** and is **never** resolved against `call.kwargs`, even on a collision with a real parameter name. **No node gains a field**, so G8(1)'s "recorded nowhere" stays true and nothing downstream needs the correspondence | §15.4 E-ENV, §15.2 G8(1) |

**What round 2 did NOT do.** It re-opened no user decision (the five approvals of 260907 stand); it
adopted no new production — it **removed** one (membership deciding) and **narrowed** another (G7 shape
(2)); it spent no registry row, no vocabulary slot and no further ceiling; and it left §15.9's gate
condition exactly as it was. **The amendment is strictly narrower after the pass than before it**, and
the two numbers that moved — five flips became three, and one new refusal count — are both published.

### 15.16.3 Post-round refinements — spec_version 19 → 20 (260908)

**Source: what T31 and T32 measured, not an adversarial round.** Band C landed the evaluator and the
oracle (§15.15). Tier 1 held at **0 unsound** and `n_findings_decided` cleared its floor seven times
over, but **AC-15.10's mutant floor was not met**, and the cause was a clause this document itself
wrote. This section records the one normative change that follows, plus two things that are *not*
normative changes and must not be mistaken for them.

> **Disclosure, stated in the document's own words. Nothing in §15.16.3 has been adversarially
> reviewed.** Rounds 1 and 2 attacked spec_version 16 and spec_version 18; R1 below is newer than both
> and has been attacked by no one. `status` therefore stays `reviewed-round-2` rather than advancing,
> and this section is kept separate from §15.16.1/§15.16.2 precisely so a reader can tell which
> normative text carries a review behind it and which carries only a measurement and an argument. R1
> **widens** what may emit `WILL_FAIL`, which is the one direction in this document that can create a
> false positive on a clean operation, and it is exactly the direction round 1 filed six blockers
> about. It is the first candidate for the next adversarial pass.

| id | class | source | what changed | § touched |
|---|---|---|---|---|
| **R1** | **normative — the only spec change in this pass** | T32 measured p1 (a) and (b) at **0 achieved** with 0 unsound (`outputs/plr-sema/predicate_mutants_260908_inc6.json`), and the cause is neither the mutators nor E-CALL(β): `pick_up_tips`'s `:502` and `:522` are depth-0 empty-trail guards whose only earlier control statement is the conditional `raise TypeError` at `:498` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:496-522`) — the ordinary check-raise-check-raise shape of a PLR precondition sequence | **E-UNCOND(5) refined.** A depth-0 empty-trail guard may emit `WILL_FAIL` iff `K` has **no earlier `ast.Return`**, the guard is **not lexically enclosed by an `ast.Try` or `ast.With`**, and there is **no earlier `ast.Break`/`ast.Continue`**. **An earlier `ast.Raise` or `assert` no longer blocks**, on the argument §15.4 states normatively: if the earlier raise fires the operation fails there, and if it does not, control reaches the guard, which fires — the operation fails either way, and `WILL_FAIL` is a claim about the *operation*, not the site, which is how `join` propagates it and how `oracle_common.compare` scores it. C1's remedy as written at spec_version 16–19 is recorded as **superseded** and why: over-strong for soundness, and it blocked every guard standing below any earlier check. A new additive derived boolean `reachability_clear` carries clauses (1)–(3) to the evaluator, absent ⇒ `None` ⇒ fail-closed; **T36** derives, regenerates, wires and re-measures. `:117` and `:2092` stay blocked | §15.4 E-UNCOND(5) (three new boxes), §15.10, §15.11 AC-15.6/AC-15.10, §15.12 (T36 + the AC-move box), §15.15 |
| **R2** | **not a spec change — implemented deviations, recorded** | T31 shipped three clauses **narrower** than this document's text, each fail-closed and none affecting the gate | Recorded in §15.15's T31 row and **nowhere else**, deliberately: the normative text in §15.4 is unchanged, because each deviation is an implementation that decides *less* than the spec permits, which needs no licence. (a) **E-CALL(5) through the β mechanism only** — no wire field detects any other rebinding shape. (b) **E-TYPE's `class_hierarchy` is `None` in production** ⇒ the `T` clause is exact-name equality, so `:498` still decides and `Well ⊂ Container` cases such as `:875` stay ½. (c) **E-UNCOND way (3) is unsatisfiable for an `InlinedGuard`**, which has no `for_span` field. **Each is a live gap between text and code and each is a candidate for the next increment**; recording them as deviations rather than quietly narrowing §15.4 keeps the spec the statement of intent and §15.15 the statement of fact | §15.15 |
| **R3** | **not a spec change — an instrument fix** | T32 found O1 (`observe_element_types`) reaching `t30_measure.py` but **not** `oracle_replay.main`, so every tier-1 run before that row was measured without it | Enabled in the replay. **Zero effect measured**: unsound, crosscheck 191/191 and the row counts are identical with and without, so no published number is retracted and §15.4's O1 disclosure is unchanged. Recorded because an instrument gap that happens to be inert is still an instrument gap — the next observation admitted may not be inert, and §15.9(5)'s with/without delta is only meaningful if both lanes actually carry the observation | §15.15 |

**What this pass deliberately did not do.** It re-opened no user decision; it added no production, no
reason, no registry row, no per-row ceiling and no vocabulary slot; it did not touch E-UNCOND(4)'s
`depth >= 1` forbiddance, ways (1)–(3) of the trail test, the restated E-TYPE, or §15.9's gate
condition; it did not lower AC-15.10's floor to match the measurement, which was the available and
wrong move; and it did not fold T36 into T33, because a row that newly permits `WILL_FAIL` on a
population that could not previously emit one has to re-run tier 1 and the whole non-regression set,
and that is not a lint row's work.

---

## References

- Main specification (amended): `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` — §3.1–§3.4
  (the `Finding` field set, the join table, the reason vocabulary), §4.1 (`FAILURE_CATEGORIES` and the
  static re-interpretation), §7.2 (the closure), §8.1 (the bridge this row replaces), §9.4 (the budget),
  Open decisions 2 (numeric atoms and the `SoundnessScope` prerequisite), Deferred rows (c), (e), (f)
  and the boundary summary.
- Increment 1: `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md` — §10.2.3 (P3a/P3b,
  which §15.3(β) defers to rather than duplicating), §10.3.1–§10.3.3 (the atom grammar this one
  subsumes, and the verdict table), §10.6.3 (A-COMPLETES, A-ENABLED), §10.8 (the parse-stage /
  evaluation-stage criterion §15.7 applies).
- Increment 3: `.praxia/docs/specs/260903_plr-sema-real-programs-increment.md` — §12.3.6 B2, the
  `pred`-aware `BRANCH` the same evaluator would serve, deferred to increment 7.
- Increment 4: `.praxia/docs/specs/260903_plr-sema-families-cache-increment.md` — §13.1 (the lid
  disposition, unchanged), §13.12 (the general dataflow pass §15.3 declines).
- Increment 5 (amended): `.praxia/docs/specs/260903_plr-sema-volume-increment.md` — §14.0 (the
  measure-before-you-construct gate §15.9 reuses), §14.5 (the guard-evaluation table §15.2 G5 leaves
  alone), §14.6 (the conditional-guard rule and R1, generalised by §15.4's E-UNCOND), §14.11 (the
  registry criterion §15.8 argues against), §14.14 item 6 (the cache key), §14.16 Q1/Q2, §14.17 (the
  implementation-record shape).
- Sprint plan: `.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md` — §2 (the tiers and the
  gate), §3 (Q1–Q6), §4 (the baselines §15.10 holds to), §5 (the exclusions §15.13 carries).
- Instrument: `outputs/plr-sema/unknown_ledger_260904_before.json`, produced by
  `plr-sema/eval/unknown_ledger.py` at PLR pin `dd79c4c89` over the sidecar-gated tier-1 benchmark,
  **re-generated after band B0's positional-keying fix (`ca756bce`)** and now carrying `consistency`,
  `n_row_id_collisions` and `collision_ops`.
- Round-1 adversarial reports, dispositioned in §15.16:
  `.praxia/docs/audits/260904_plr-sema-predicate-round1-challenger.md` (C1–C18, six blockers, verdict
  `needs_revision`) and `.praxia/docs/audits/260904_plr-sema-predicate-round1-defender.md`
  (adjudications, D1–D3, the ordered remediation list, the user decisions, the revised gate
  prediction, verdict `needs_revision`).
- **The amendment's own short adversarial pass, dispositioned in §15.16.2**:
  `.praxia/docs/audits/260907_plr-sema-predicate-amendment-challenger.md` (A-C1–A-C13 — three blockers,
  five must-fix, three should-fix, two notes; verdict `needs_revision`, revise-and-advance; GO
  prediction for `pick_up_tips` survives every objection; "not gaming the gate", but the anti-gaming
  *argument* unsound as written). Scoped to the spec_version 18 delta only, against commit `f441d27e`.
- **The landed population re-run**: `outputs/plr-sema/t30_measured_260907.json` (commit `15b84d31`),
  the report against which the amendment's delta is taken — same 544 / 223 population as the ledger,
  pre-amendment grammar.
- Exception taxonomy consulted for §15.5's fence argument and found to cover the wrong population:
  `training/verify/data/plr_exception_taxonomy.json` (132 PLR-defined classes at the same pin).
- **Band B's landed code and measurement, read in full for the 260907 amendment** — the shipped
  grammar `plr-sema/src/plr_sema/derive/predicate_ast.py` (the node set §15.2 G1 is now reconciled
  against, `parse`'s term/predicate dispatch at `:518-539` and `:350-362`, `_parse_quantifier` at
  `:408-421`, `_CMP_OPS` at `:298-305`, `contains_opaque` at `:566-593`); `free_var_names`
  (`plr-sema/src/plr_sema/derive/bindings.py:150-182`); the measurement script's own scope statement
  and structural classifier (`plr-sema/eval/t30_measure.py:18-24`, `:699-745`); and the measured
  report `outputs/plr-sema/t30_measured_260905.json` (block 1 at `:3-62`, block 3's 54 clusters at
  `:452-993`, block 4 at `:994-1142`, the O1 delta at `:1143-1146`, the `gate` block at `:1149-1162`,
  `scope_notes` at `:1164-1168`).
- **Band C's measurements, read in full for spec_version 20's refinement** (§15.15's T35/T31/T32 rows,
  §15.16.3): `outputs/plr-sema/t30_measured_260908.json` (T35's GO and the re-prediction match),
  `outputs/plr-sema/oracle_replay_260908_inc6.json` (0 unsound, crosscheck 191/191,
  `n_findings_decided` 1,563 with its per-site breakdown, `n_findings_by_reason`),
  `outputs/plr-sema/unknown_ledger_260908_after.json` (`consistency.ok`, 54 → 53 clusters,
  6,036 → 5,157 findings, `pick_up_tips`'s residual), `outputs/plr-sema/predicate_mutants_260908_inc6.json`
  (p1 (a) 288/0/0, (b) 16/0/0, (c) 288/0/0 — the unmet floor R1 diagnoses), and the non-regression set
  `outputs/plr-sema/tip_mutants_260908_inc6.json`, `outputs/plr-sema/volume_mutants_260908_inc6.json`,
  `outputs/plr-sema/tier2b_260908_inc6.json`.
- **The user's five decisions of 260907**, recorded in the sprint plan's execution log:
  `.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:198-265` — the band-B NO-GO at `:237-250`,
  the measurement caveat at `:247-250`, decision 5 and its two options at `:252-260`, and the approvals
  at `:262-265`.
