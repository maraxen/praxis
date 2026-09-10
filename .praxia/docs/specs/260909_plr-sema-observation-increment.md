---
title: "plr-sema increment 7 — the observation record: tier (ii), the delegate→caller argument map, and the first scoped joined verdict"
description: "Seventh post-corpus increment to the plr-sema pre-corpus specification, taking increment 6 section 15.13's deferred tier-(ii) row and section 15.6's Q2 defer. The headline the user substituted into this increment on 260907 -- **the first joined SAFE on a real executed operation of the frozen tier-1 benchmark** -- is measured against the after-ledger and reported as **NOT REACHABLE in increment 7**, for a reason this document names, sizes and site-identifies rather than discovers at a gate: `_check_args`'s two guards, liquid_handler.py lines 375 and 383, sit on ALL 544 executed operations, and deciding either requires modelling five comprehensions over `inspect.signature`, a set-difference term, a set-display term and the residual `**kwargs` key set -- five productions and a per-row ceiling spend, sized at ~350 LOC and refused here as increment 8's. What increment 7 DOES ship, stated as narrowly as the ledger forces: the observation record (backend class, num_channels, head channel key set), taken inside the verifier's window and returned by the executed side on increment 5 section 14.6's O5 pattern, entering the cache key as `obs:key=value` members of the existing fifth `env` component; the derived backend surface (per (class, method) parameter names, has-var-keyword, has-var-positional, constant-return value), derived over the derive package's own PLR function index with NO hand-typed base-class name; the delegate->caller argument map at depth 1, `self.`-receiver-only, singleton-call-only, fail-closed to Top on every other shape; four E-ENV resolution rules that turn `self.head`, `self.backend.<attr>` and `self.backend.<method>` from unconditional half/Top into real values; the reopening of increment 6 section 15.13's membership deciding case under all three of its stated conditions; a refinement of A-C13 that binds a single-name quantifier target element-wise over a concrete Seq (additive `target` field on Filtered/AllOf/AnyOf, absent => None => today's behaviour); a monotonic quantifier clause that decides AllOf over a Top seq when the body is T under Top-bound targets; the LIFT of E-UNCOND(4)'s depth >= 1 WILL_FAIL forbiddance under three new normative preconditions; Q1's scoped joined verdict as a second, additive `scope_verdict` report field computed by the UNCHANGED join over the findings whose site is not in `scope.excludes_sites`, with the unscoped `verdict` staying UNKNOWN and `schema_version` staying 1; and the fence's site-keyed narrowing, built on a ~3-line `traceback.extract_tb(...)[-1]` frame capture, publishing a SECOND counter `unsound_scoped` beside the unmodified `unsound` whose definition does not change. Measured prediction, per site, for the gate candidate `pick_up_tips` (223 ops): liquid_handler.py line 409 flips to SAFE on 223 (and on up to 384 across five methods), line 514 flips to SAFE on 223 via the constant-return derivation, line 321 flips to SAFE ONLY under user decision D2 (a deck-membership observation plus a fifth named assumption A-DECK-OBJECT, recommended YES on the argument that the tier-1 fence checks it on 288 real operations), :375 and :383 do NOT flip, :576 stays tier (iii) and annotated. So `pick_up_tips`'s residual falls from SIX guard_env_dependent sites to TWO (three without D2), `n_findings_decided` is predicted 1,563 -> >= 2,170, and `scope_verdict` is predicted UNKNOWN on every one of the 544 executed operations -- **GATE: predicted NO-GO, with the obstruction named in advance**. Five user decision hooks are surfaced with recommendations and never spent in the text: D1 (lift E-UNCOND(4), recommend YES), D2 (A-DECK-OBJECT + the deck observation, recommend YES), D3 (nothing -- the derived surface introduces no hand-typed fact, recorded as a non-decision so the round can attack it), D4 (HM-25 declared 9 -> 10 for the E-ENV path-shape table, recommend YES), D5 (model `_check_args` in this increment, recommend NO). REASON_VOCABULARY stays 12 of 12 and `live_rows()` stays 24 of BUDGET_CAP 24; no registry row is added and no thirteenth reason is proposed. Increment 6 section 15.16.3 R1's owed adversarial review is restated here as five numbered claims (R1-C1..R1-C5) so the round can attack them, together with the interaction between the refined E-UNCOND(5) and this increment's depth-1 WILL_FAIL. REVISED 260909 (spec_version 2) after adversarial round 1 -- challenger C1-C26 (5 blockers, 14 must-fix, 6 should-fix, 1 note) and defender (13 conceded, 13 partial, 0 clean rebuttals, six defender gaps D-G1..D-G6, a 14-step ordered remediation list), both verdicts needs_revision; section 16.17 records the disposition of every objection. What round 1 changed, in the order it matters. (1) THE HEADLINE REVERSES from unreachable to reachable, and now rests on ONE user decision. C1's arithmetic was reproduced at the pin: the SAFE direction of line 375 needs only that `params` for the observed backend method is a subset of the call site's `default`, so `missing` is empty whatever `backend_kws` is; and line 383 falls to E-SCOPE over the RECORDED scope entry once `has_var_keyword` is known -- both columns section 16.3 already derives, and neither needs the set-difference term, the keys() term or the residual kwargs key set. The five-production refusal is withdrawn and D5 is repriced as D5a (the general model, ~350 LOC, increment 8's) / D5b (two SAFE-direction site rules, ~100-130 LOC) / D5c (no). C22's reconciliation is paid: increment 6 section 15.6 was RIGHT that AST-deriving the backend signatures is the condition, and spec_version 1 shipped that derivation and then declared the sites undecidable on a different ground without noticing. (2) A NEW decision hook D6 -- accept site-keyed semantic models of named PLR function bodies as a class of hand-maintained fact, one new registry row against a full BUDGET_CAP 24, i.e. a cap conversation -- because the repaired line-321 rule and D5b are the SAME ask and the gate needs BOTH (D-G2). Recommendation YES; total cost ~250 LOC across T48 and T49; D-G6's one-directionality (both `_check_args` guards carry `reachability_clear` false, and a false `fires` returns SAFE unguarded by depth) is its strongest argument. Section 16.10.2 states the conjunction and section 16.10.3 predicts every site BOTH WAYS. (3) R-DECK IS WITHDRAWN as an EnvRef shape (C3): the shipped guard record for line 321 carries no EnvRef and empty bindings, and `resource` is a for-target nothing binds; the 2,458 floor and the 50-cluster cell go with it, and line 321 is respecified as a site rule over the caller-bound `resources` plus the deck-name observation. (4) Q-BIND IS WITHDRAWN in full as dead machinery (D-G1): line 409 is evaluated by `_maybe_alpha_emptiness` and `_eval_alpha_existential`, which already bind element-wise, so the additive `target` field on Filtered/AllOf/AnyOf, its parse half and its counter are all deleted and T43 shrinks ~200 to ~150 LOC. Q-MONO survives, now stated as an EXPLICIT amendment of increment 6 G8(1)/A-C3 with the increment-6 file in T43's list (C6), and C7's evaluator invariant E-INV is stated normatively with R-CONST and Q-MONO as its two named instances. (5) THE FENCE WAS BROKEN AND IS FIXED (C5): `traceback.extract_tb` returns frames outermost-first, so the last-frame capture was the backend's original raise and could never match the re-raise site -- F2 excused nothing. `error_frames` is now a list, F2 excuses on ANY frame with the outermost-PLR-match tie-break, one normalisation helper carries both stated identities (C20), and AC-16.8 gains the re-raise fixture the innermost version could never pass. (6) The gated floor moves 2,170 to 2,009 (C4) with 2,170 published as target and every aggregate split 223-certain / up-to-384, because the 384 was the exact number section 16.10.3 declined to claim. (7) The gate becomes a conjunction the increment can fail on its own terms (C2) when D6 is declined. Also: one fail-closed capture point after `machine.setup()` with a None observation on the deck-build early return and on any raising read (C13, C17); recursive deck-name extraction (C14); JSON-encoded env values with numeric int sort (C12) and the deck map's digest entering env (D-G3); the C15 decorator/property/multi-lineno absence rule as R-CONST's and D5b's shared soundness gate; one closed section 16.3 selection rule with published counts (C16); M2's origin clause and the caller-side call-statement lineno (C9, C10); C19's blocking half REBUTTED on the evidence (`scope_trail` records for headers, unsatisfiable under ways 1-3) with one normative sentence and no fourth precondition; `scope_verdict` threaded into the unknown ledger (D-G4); `t30_measure` re-run or explicitly retired (D-G5); p2a published as achieved over attempted (C23); the lane asymmetry disclosed for all rules with tier-2b's attribution corrected (C24); R-ATTR kept as an explicit sub-note under D4 (C25); T42's spurious T41 dependency dropped with the D1-decline withdrawal list stated exactly (C26). D1, D3 and D4 are unchanged after adjudication."
status: reviewed-round-1
spec_version: 2
amends: 260901_plr-sema-pre-corpus-spec.md
task_id: 260909_sema-observation
date: '260909'
confidence: medium
sources: "Increment 6 read in FULL as the structural model and as the text this document extends: .praxia/docs/specs/260904_plr-sema-predicate-increment.md (frontmatter 1-11; preamble 13-105; section 15.0 108-223; section 15.1 226-423; section 15.2 426-707; section 15.3 710-840; section 15.4 843-1312; section 15.5 1315-1448; section 15.6 1451-1504; section 15.7 1507-1646; section 15.8 1649-1797; section 15.9 1800-2086; section 15.10 2089-2201; section 15.11 2204-2446; section 15.12 2449-2531; section 15.13 2534-2617; section 15.14 2620-2694; section 15.15 2697-2711; section 15.16 2714-2841; References 2844-2855). Increment 5 section 14.6 read in full as the environment-member precedent every legitimacy argument here is stated against: .praxia/docs/specs/260903_plr-sema-volume-increment.md:602-741 (the conditional-guard rule 619-636, R1 638-673, the TWO FAILED is_disabled discharges 675-689, the env argument 691-698, O5 -- observed inside the window, returned by the executed side 700-723, the consequence 725-741). Main spec: .praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:574-581 (the join table), :2514-2524 (the deferred rows, (c) at 2518, (e) at 2520, (f) at 2524), :2526-2534 (the boundary summary), :3316-3345 (Open decisions 3, the additive direction at 3322-3326). Increment 1: .praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:744-754 (the named-assumption table -- A-SINGLE 751, A-COMPLETES 752, A-COMMIT 753, A-ENABLED 754). PLR at submodule pin dd79c4c89, every line below read THIS pass: external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:155-203 (the receiver fields at 158-166, `setup` and the head construction at 187-197), :300-321 (`_assert_resources_exist`), :323-389 (`_check_args` in full -- the AsyncMock early return 347-350, `inspect.signature` 353-359, `non_default`/`missing` 369-375, the **kwargs early return 377-378, `extra`/`strictness` 380-389), :391-409 (`_compute_spread_offsets`, `_make_sure_channels_exist`), :488-524 (pick_up_tips' body), :541-556, :575-576; external/pylabrobot/pylabrobot/liquid_handling/strictness.py:1-24 (the module-global and its two accessors); external/pylabrobot/pylabrobot/liquid_handling/backends/backend.py:1-60 and :175-188 (`LiquidHandlerBackend`, the abstract `can_pick_up_tip`); external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:30-79 and :232-243 (`__init__`, `num_channels`, `pick_up_tips`, `can_pick_up_tip`); external/pylabrobot/pylabrobot/liquid_handling/backends/serializing_backend.py:236-242; external/pylabrobot/pylabrobot/resources/resource.py:160-174 (`__eq__`) and :566-589 (`get_resource` and its ResourceNotFoundError). The six direct LiquidHandlerBackend subclasses enumerated by ripgrep over the whole PLR tree at the pin and each class line read: external/pylabrobot/pylabrobot/liquid_handling/backends/opentrons_backend.py:80, external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:24, external/pylabrobot/pylabrobot/liquid_handling/backends/tecan/EVO_backend.py:56, external/pylabrobot/pylabrobot/liquid_handling/backends/serializing_backend.py:26, external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/base.py:46, external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/tcp_backend.py:66; the eight can_pick_up_tip definitions likewise, of which exactly two are a single return of a constant. Analyzer source, each citation verified against the file this pass: plr-sema/src/plr_sema/check/ir.py:170-204 and :905-953; plr-sema/src/plr_sema/verdict.py:125-199, :250-275, :278-323; plr-sema/src/plr_sema/check/__init__.py:400-470, :600-639, :920-990; plr-sema/src/plr_sema/check/predicate.py:262-295, :597-658, :666-679, :765-800, :818-888; plr-sema/src/plr_sema/derive/__init__.py:454-528; plr-sema/src/plr_sema/derive/bindings.py:113-124,158,215,279-304,690-737,778-815; plr-sema/src/plr_sema/derive/receiver_state.py:1275-1308; plr-sema/src/plr_sema/_hand_maintained.py:36-49, :648-667, :890-1019; plr-sema/eval/oracle_common.py:398,415-439,446,463,551,623,767-786. Harness: training/verify/verifier.py:95-200; training/verify/deck.py:130-163. Lint, read in full so every citation and every task row in this document is written against the checker rather than against a memory of it: plr-sema/scripts/check_spec_citations.py:1-80,100-213; plr-sema/scripts/check_spec_crossrefs.py:45-199; plr-sema/tests/test_spec_lint.py:20-51,205-258. The instrument and its companions, read this pass: outputs/plr-sema/unknown_ledger_260909_after.json:2-19,29-38,41-45,90-94,136-148,177-188,217-223,257-261,2119-2156,2158-2169; outputs/plr-sema/oracle_replay_260909_inc6.json:2-30,105-137,138-199; outputs/plr-sema/predicate_mutants_260909_inc6.json:2-58; outputs/plr-sema/t30_measured_260908.json:28555-28610. plr-sema/data/derived_contracts.json read for its FOUR top-level keys only (`contracts`, `receiver_state`, `schema_version`, `stamp`). Not read this pass and therefore cited BY SYMBOL rather than by line throughout: plr-sema/eval/predicate_mutants.py, plr-sema/eval/region_oracle.py, plr-sema/eval/unknown_ledger.py, plr-sema/src/plr_sema/derive/predicate_ast.py, plr-sema/src/plr_sema/check/tipstate.py. ROUND-1 PASS (spec_version 2) sources, both reports read in FULL and dispositioned in section 16.17: .praxia/docs/audits/260909_plr-sema-observation-round1-challenger.md:1-158 (the frontmatter classification 1-9, the summary 16, C1-C5 the blockers 20-43, C6-C19 the must-fix set 45-113, C20-C25 the should-fix set 115-143, C26 the note 145-148, the verdict and the two objection-impact lists 150-158); .praxia/docs/audits/260909_plr-sema-observation-round1-defender.md:1-125 (the frontmatter adjudication summary 1-9, the opening 18, the per-objection adjudications C1-C26 at 22-73, the six defender gaps D-G1..D-G6 at 77-89, the post-round user-decision table 93-102 including the NEW D6 row at 102, the 14-step ordered remediation list 106-121, the verdict 123-125). Analyzer source re-read THIS pass for the round-1 remediation, every citation verified against the file: plr-sema/src/plr_sema/check/predicate.py:218-256 (`_resolve_var` and its origin contract), :400-481 (the G3 alpha-existential path D-G1 turns on -- the module note at 402-410, `_eval_alpha_existential` at 433-456 with the per-item override at 449-451, `_maybe_alpha_emptiness` at 459-480), :530-559 (`_eval_cmp`'s dispatch and the membership half at 542-543), :561-607 (`_eval_is`, the quantifier module note at 574-579, `_resolve_seq_length`, `_eval_allof_anyof` at 597-606), :700-739 (`guard_reason` at 704-714 and `_scope_entry_value` at 724-738). plr-sema/data/derived_contracts.json read at the three guard records the round turns on: :88795-88824 (line 321's predicate, empty bindings, `reachability_clear` true and the two-entry `scope_trail` whose second entry is the `for` header), :88862-88879 (line 375's `reachability_clear` false and its one-entry trail), :88880-88913 (line 383's recorded enclosing scope entry `if len(extra) > 0 and len(vars_keyword) == 0`, and its `reachability_clear` false)."
---

# Increment 7: the observation record

> **This document amends `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` by reference** and
> adds §16 to that document's numbering, exactly as increment 6 adds §15. It takes increment 6 §15.6's
> Q2 defer — *"tier (ii) ships as increment 7"* — together with the four items §15.13 named as
> increment 7's by name: the delegate→caller argument map, the `EnvRef` path lookup against an
> observation, the site-keyed soundness-fence narrowing, and the membership deciding case with its
> three reopening conditions.
>
> **What this increment ships unconditionally, stated as narrowly as the after-ledger forces.** The
> observation record and its cache-key partition; the derived backend surface; the delegate→caller
> argument map; **three** `E-ENV` resolution rules; **one** quantifier clause; the scoped joined
> verdict; and the fence's site-keyed narrowing. On the frozen benchmark this turns **two** of the gate
> candidate's six `guard_env_dependent` sites into `SAFE` — `liquid_handler.py:409` and `:514`.
>
> **THE HEADLINE IS REACHABLE THIS INCREMENT, AND ITS REACHABILITY RESTS ON ONE USER DECISION.** That
> sentence reverses spec_version 1's central finding, and it is the whole of what round 1 changed.
> Under **D6** — *accept site-keyed semantic models of named PLR function bodies as a class of
> hand-maintained fact, one new registry row against a full `BUDGET_CAP` 24* — the remaining three
> sites decide: `:375` and `:383` by the `SAFE`-direction arithmetic §16.1.1 works out at the pin, and
> `:321` by a site rule over the caller-bound `resources` and the deck-name observation. Together they
> are ~250 LOC across two task rows, and **`pick_up_tips` reaches `scope_verdict == SAFE` on a
> predicted ≥ 167 of its 223 operations.** Under D6 declined, `scope_verdict` stays `UNKNOWN`
> everywhere and the increment is measured against §16.10.2's conjunctive NO-GO-side criterion.
> **§16.10.2 states the conjunction, §16.10.3 predicts every site both ways, and §16.15 D6 puts the
> decision with this document's recommendation: YES.**
>
> **What spec_version 1 got wrong, said here rather than buried in §16.17.** It priced a **general**
> model of `_check_args` when the gate needs only the `SAFE` direction, which is computable from two
> columns §16.3 already derives; and it specified `:321`'s rule against a predicate shape that does not
> occur in the shipped contract table. Both were load-bearing for its "unreachable" claim and neither
> survives. **Increment 6 §15.6 was right**: AST-deriving the backend signatures *was* the condition
> for moving those two sites, spec_version 1 shipped that derivation, and then declared the sites
> undecidable on a different ground without noticing it had met the earlier document's own test
> (§16.1.1's reconciliation).
>
> **Registry arithmetic, with the two spends it proposes and never takes.** `REASON_VOCABULARY` stays
> at **12 of 12** — no thirteenth reason is proposed and none is needed (§16.8). **Under D6 declined**,
> `live_rows()` stays **24** against `BUDGET_CAP = 24`
> (`plr-sema/src/plr_sema/_hand_maintained.py:43`) and the only spend is **D4**, a per-row ceiling unit
> — HM-25 `declared` **9 → 10** — for §16.5's `EnvRef` path-shape table, which is genuinely
> hand-maintained surface and which increment 6 §15.4's `E-ENV` box forbade outright *"in this
> increment"* precisely so this increment would have to argue for it. **Under D6 taken**, one row is
> added and the cap moves to 25 — a cap conversation, which is exactly why D6 is the user's and not the
> sprint's. Round 1's defender is explicit that these site rules are **not** HM-25's kind: every entry
> there is keyed on a *shape*, and nothing in the registry is keyed on a PLR qualname.

---

## 16.0 The instrument and the claim

**The instrument is the after-ledger increment 6 closed with**, `outputs/plr-sema/unknown_ledger_260909_after.json`,
produced by the unmodified `plr-sema/eval/unknown_ledger.py` against the frozen benchmark
`tier1-sidecar-gated-dd79c4c89` at PLR pin `dd79c4c89`
(`outputs/plr-sema/unknown_ledger_260909_after.json:2-19`). Its numbers, verbatim: **544 executed
operations**, 544 with `n_ops_unknown` equal to `n_ops_executed`, **5,157 findings**, **53 clusters**
(`outputs/plr-sema/unknown_ledger_260909_after.json:29-38`). By reason: `guard_env_dependent` 4,138,
`guard_predicate_unparsed` 495, `volume_state_unknown` 194, `unresolved_delegate` 186,
`guard_operand_unknown` 144.

**The per-operation residual histogram is five rows, and every row begins with `guard_env_dependent`**
(`outputs/plr-sema/unknown_ledger_260909_after.json:2119-2156`):

| per-op reason set | ops | note |
|---|---|---|
| `{guard_env_dependent}` | **223** | `pick_up_tips` — the gate candidate, and the only set with no coverage gap in it |
| `{guard_env_dependent, guard_predicate_unparsed, volume_state_unknown}` | 117 | `aspirate` 77 + `dispense` 40 — the unseeded volume cell plus `:116` |
| `{guard_env_dependent, guard_predicate_unparsed, unresolved_delegate}` | 93 | the `move_*` family — **deferred row (e)** (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2520`), out of scope by construction |
| `{guard_env_dependent, guard_predicate_unparsed}` | 58 | `stamp` 27 + `drop_tips` 31 |
| `{guard_env_dependent, guard_operand_unknown, guard_predicate_unparsed}` | 53 | `discard_tips` 34 + `transfer` 19 |

**The gate candidate is `pick_up_tips`, 223 operations, and the ledger identifies it without argument.**
It is the one method whose residual reason set is a singleton, and it is the method increment 6 §15.9
named in advance and T35 confirmed cell for cell. The per-method residual sets in the replay report
agree: `pick_up_tips` is `decidable+guard_env_dependent` on 223 of 223
(`outputs/plr-sema/oracle_replay_260909_inc6.json:138-199`), and every other method carries at least
one further reason.

### 16.0.1 The six sites, and why they are coupled

`pick_up_tips`'s residual is exactly six `guard_env_dependent` guard sites, all in
`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py` at pin `dd79c4c89`. Their cluster
sizes, read off the ledger:

| site | condition (verbatim from the ledger) | `n_findings` / `n_ops_blocked` | ledger anchor |
|---|---|---|---|
| `:375` | `len(missing) > 0` | 544 / 544 | `outputs/plr-sema/unknown_ledger_260909_after.json:41-45` |
| `:383` | `strictness == Strictness.STRICT` | 544 / 544 | `outputs/plr-sema/unknown_ledger_260909_after.json:90-94` |
| `:409` | `not len(invalid_channels) == 0` | 384 / 384 | `outputs/plr-sema/unknown_ledger_260909_after.json:136-148` |
| `:321` | `not resource_from_deck == resource` | 288 / 288 | `outputs/plr-sema/unknown_ledger_260909_after.json:177-188` |
| `:514` | `not all((self.backend.can_pick_up_tip(channel, tip) for channel, tip in zip(use_channels, tips)))` | 223 / 223 | `outputs/plr-sema/unknown_ledger_260909_after.json:217-223` |
| `:576` | `error is not None` | 223 / 223 | `outputs/plr-sema/unknown_ledger_260909_after.json:257-261` |

**Every one of the six blocks every one of the 223 `pick_up_tips` operations.** The three that also
reach other methods carry the same reason there: `:409`'s `per_method` breakdown is `pick_up_tips` 223,
`aspirate` 77, `discard_tips` 34, `drop_tips` 31, `transfer` 19 — summing to 384 — and `:321`'s is
`pick_up_tips` 223, `discard_tips` 34, `drop_tips` 31, summing to 288
(`outputs/plr-sema/unknown_ledger_260909_after.json:136-148`, `:177-188`). Both sums close, which the
ledger's own `consistency` invariant 3 asserts for every cluster.

> **Normative (the coupling, and why no subset of the six is a deliverable).** `join` is unchanged
> (`plr-sema/src/plr_sema/verdict.py:313-323`) and is still the only function that aggregates: one
> `UNKNOWN` finding makes the operation `UNKNOWN`. **A joined verdict is therefore an all-or-nothing
> property of the six**, and every cluster in the ledger reports `n_ops_sole_blocker` 0. The
> consequence is normative for how this increment is measured: a metric of the form "clusters removed"
> or "findings converted" can move by 607 while `scope_verdict` stays `UNKNOWN` on all 544 operations.
> §16.10's gate is therefore stated over **`scope_verdict` per operation**, and that is the only
> number in this document allowed to decide GO.

### 16.0.2 The claim

**The claim, stated as narrowly as increment 5 and increment 6 each stated their own, and REVISED at
spec_version 2 after round 1 broke the version below it.** Increment 7 makes **two** of the six sites
`SAFE` unconditionally — `:409` and `:514` — annotates `:576` out of the PLR-precondition scope as
increment 6 already does, and gives `AnalysisReport` a second, additive verdict field that says what
the analyzer knows within that scope. The remaining **three** — `:375`, `:383` and `:321` — are decided
**iff and only iff the user takes D6**, and they are decided by three site rules of one kind, which is
what D6 names.

> **What spec_version 1 claimed and round 1 falsified, recorded because the correction is the whole of
> this revision.** The draft claimed (a) that `:375`/`:383` require five productions and are therefore
> out of reach — **false**: the `SAFE` direction needs only `params` and `has_var_keyword`, two columns
> §16.3 already derives (C1, conceded, arithmetic re-verified at the pin in §16.1.1); (b) that `:321`
> would flip under an `EnvRef` rule R-DECK — **false**: the shipped guard record for `:321` carries no
> `EnvRef` at all and `resource` is a `for`-target nothing binds (C3, conceded against the contract
> table in §16.1.3); and (c) that the headline was therefore unreachable — **not established**. The
> corrected statement is narrower *and* more optimistic: **the headline is reachable this increment,
> and its reachability rests on exactly one user decision.** §16.10.2 states the conjunction.

---

## 16.1 The six sites, and what each one needs

> **Normative (how to read this table).** "Decidable this increment" is a **prediction** in exactly
> increment 6 §15.1's sense: the measured column is §16.10's, produced by T46, and where the two
> disagree the measurement wins and the divergence is recorded rather than absorbed. A `Y` cell is a
> claim that this document specifies every mechanism the site needs; an `N` cell names what is missing
> and sizes it.

| site | guard | depth | the fact it needs | from where | decidable? | resolves to |
|---|---|---|---|---|---|---|
| `:375` | `len(missing) > 0` | 1 | `Len(Var("missing"))` = 0, from `params(class, method) ⊆ default` | §16.3's `params` + §16.4's `caller_args` + one site rule (§16.1.1) | **Y iff D6** | `SAFE` on 544, else ½ |
| `:383` | `strictness == Strictness.STRICT` | 1 | `Len(Var("vars_keyword"))` > 0 ⇒ the recorded scope entry is `F` ⇒ E-SCOPE | §16.3's `has_var_keyword` + one site rule (§16.1.1) | **Y iff D6** | `SAFE` on 544, else ½ |
| `:409` | `not len(invalid_channels) == 0` | 1 | `channels ← use_channels` (§16.4) + `self.head`'s key set (§16.2/§16.5.1) + the membership deciding case (§16.5.4) | the observation + the argument map | **Y** | `SAFE` on 223 (up to 384) |
| `:321` | `not resource_from_deck == resource` | 1 | the caller-bound `resources` + the deck name map, via one site rule — **not** an `EnvRef` shape (§16.1.3) | the observation + one site rule + A-DECK-OBJECT | **Y iff D6** | `SAFE` on 288, else ½ |
| `:514` | `not all(... can_pick_up_tip ... zip(use_channels, tips))` | 0 | the backend method's **body**, plus a monotonic quantifier clause over a ⊤ `Zip` | the derived backend surface (§16.3) | **Y** | `SAFE` on 223 |
| `:576` | `error is not None` | 0 | nothing — tier (iii), derived by `is_dynamic_raise` | already shipped | **n/a** | one `UNKNOWN` + `excludes_sites` |

### 16.1.1 `:375` and `:383` — repriced after round 1 (C1, C22, D-G6)

`_check_args` is read in full at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:323-389`
and its call site inside `pick_up_tips` at `:541-546`, which passes the bound backend method
`self.backend.pick_up_tips`, the entry point's `backend_kwargs`, `default={"ops", "use_channels"}`,
and `strictness=get_strictness()`.

> **WITHDRAWN at spec_version 2 (C1, conceded).** spec_version 1 priced a **general** model of
> `_check_args` and refused it, then reported the headline unreachable on that refusal. **The gate
> needs only the direction that yields `SAFE`, and that direction is decidable from two columns §16.3
> already derives.** The arithmetic is re-verified at the pin below. The refusal is withdrawn; what
> replaces it is a repriced, three-option decision (D5a/D5b/D5c) and a new decision hook (D6) naming
> the class of fact D5b needs.

**The `SAFE` arithmetic for `:375`, step by step, at the pin.** `default_args = default.union({"self"})`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:351`); `args` drops `default_args`
and then every `VAR_POSITIONAL`/`VAR_KEYWORD` parameter (`:354`, `:360-368`); `non_default` keeps the
no-default residue (`:369`) — which is **set-equal to §16.3's `params` minus `default`**, because
§16.3's `params` is defined as exactly "the parameter names after `self`, excluding `*args`/`**kwargs`,
that have no default". At the pin the backend method is
`pick_up_tips(self, ops, use_channels, **backend_kwargs)`
(`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:63`) and the call site passes
`default={"ops", "use_channels"}`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:541-546`). So
`params = {ops, use_channels} ⊆ default`, `non_default = ∅`, and **`missing = ∅ − backend_kws = ∅`
whatever `backend_kws` is**. `Len(Var("missing")) > 0` is `F`, the `raise_guard` does not fire, and the
guard is `SAFE`. **Neither the set-difference term nor the residual `**kwargs` key set is needed** —
the subtrahend is irrelevant when the minuend is empty.

**`:383` falls the same way, through the recorded scope trail and not through the early return.** Its
shipped guard record carries `"scope_trail": ["if strictness == Strictness.STRICT", "if len(extra) > 0
and len(vars_keyword) == 0"]` (`plr-sema/data/derived_contracts.json:88880-88913`). E-UNCOND(6)
excludes the self-entry, so E-SCOPE evaluates the second entry; `has_var_keyword` is **true** for the
pin's backend method, so `Len(Var("vars_keyword"))` is ≥ 1, `len(vars_keyword) == 0` is `F`, the `And`
is `F`, and `scope_excludes` returns `_SAFE` before the predicate is evaluated at all
(`plr-sema/src/plr_sema/check/predicate.py:874-876`). **`strictness` is never resolved and the
early-return route (b) is unnecessary** — increment 6 §15.6 flagged the un-recorded `:377-378` early
return as an obstacle, and spec_version 1 repeated the flag; the recorded trail makes route (a)
sufficient on its own.

> **Normative (D-G6 — the discharge is ONE-DIRECTIONAL by construction, and this is D5b's strongest
> argument).** Both guards carry `"reachability_clear": false` in the shipped table
> (`plr-sema/data/derived_contracts.json:88869-88873`, `:88904-88909`), because of the `return set()`
> at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:347-350`. Combined with
> `evaluate_guard`'s **unguarded** `fires is False → _SAFE` return
> (`plr-sema/src/plr_sema/check/predicate.py:878-887`), a site rule over `_check_args` can only ever
> add `SAFE`; it can **never** emit a `WILL_FAIL`, false or otherwise, and it needs **no** interaction
> with D1's depth-1 lift. The false-positive direction is closed by construction rather than by
> argument, which is not true of any other new mechanism in this increment.

> **Normative (the reconciliation with increment 6 §15.6, owed and now paid — C22).** Increment 6
> stated the condition for moving these two sites in one sentence: *"to move either `:375` or `:383` …
> the increment must AST-derive the backend class's method signatures"*
> (`.praxia/docs/specs/260904_plr-sema-predicate-increment.md:1478-1480`). §16.3 ships exactly that.
> **§15.6 was right**, and spec_version 1's declaration that the sites remained undecidable on a
> different ground was wrong: it priced the general model and never noticed the previously stated
> condition had been met. A reader of both documents should read §15.6's sentence as satisfied by
> §16.3, and §16.1.1's spec_version 1 refusal as withdrawn.

> **Normative (the honest cost of the site rules — the defender's repricing, not the challenger's).**
> The rules **are not** in α/β/P3a/P8/P9's class and must not be filed as HM-25 units. Every entry on
> HM-24 and HM-25 is keyed on a *shape* — a syntactic pattern over how PLR is written, which
> `why_not_derived` says in those terms
> (`plr-sema/src/plr_sema/_hand_maintained.py:976-983`). A rule that decides `Len(Var("missing"))` is
> keyed on `(module, qualname) == (liquid_handling.liquid_handler, "LiquidHandler._check_args")` **and
> on two of that function's local names**, `missing` and `vars_keyword`. That is a hand-written
> semantic model of one named PLR function body — §8's class, not HM-25's — and nothing in the registry
> is keyed on a PLR qualname today.
>
> **Consequences, each stated because each is a cost:** (1) it is a **new registry row against a full
> `BUDGET_CAP` 24**, i.e. a cap conversation, not a ceiling unit; (2) `_measure_hm25`'s
> import-the-symbol measure would see only *deletion of the rule*, never PLR renaming `vars_keyword`,
> so the loud half must be a **published count** (`n_check_args_decided`, asserted 544) rather than an
> import; (3) it inherits **C15's absence rule** (§16.3) as a soundness precondition — an AST-derived
> `params`/`has_var_keyword` for a decorated or multiply-defined definition does not describe the
> runtime object `inspect.signature` sees, so a `(class, method)` row that fails C15's test must make
> the site rule decline rather than decide.

> **Normative (`strictness` decides nothing, restated and now with a second reason).** Increment 6
> §15.6 established that adding `strictness` to `env` converts a ½ into a ½ because the enclosing
> scope entry is tier-(ii) backend. A second, independent reason is recorded here: even with the
> process-global observed, `Strictness.STRICT` on the comparison's right-hand side is an
> `ast.Attribute` chain rooted at the **module-level name** `Strictness`
> (`external/pylabrobot/pylabrobot/liquid_handling/strictness.py:5-10`), not at `self`, so it is not an
> `EnvRef` under G7 and it resolves to ⊤ as an ordinary `Attr` term. Deciding `:383` from the left-hand
> side alone is therefore impossible **whatever `env` carries** — which is why §16.1.1's route is
> E-SCOPE over the recorded trail and not the predicate. **`strictness` is refused as an observation
> member by name in §16.2**, and this box is the reason.

> **Normative (`strictness` decides nothing, restated and now with a second reason).** Increment 6
> §15.6 established that adding `strictness` to `env` converts a ½ into a ½ because the enclosing
> scope entry is tier-(ii) backend. A second, independent reason is recorded here: even with the
> process-global observed, `Strictness.STRICT` on the comparison's right-hand side is an
> `ast.Attribute` chain rooted at the **module-level name** `Strictness`
> (`external/pylabrobot/pylabrobot/liquid_handling/strictness.py:5-10`), not at `self`, so it is not an
> `EnvRef` under G7 and it resolves to ⊤ as an ordinary `Attr` term. Deciding `:383` from the left-hand
> side alone is therefore impossible **whatever `env` carries**, and an enum-constant `Term` production
> would be a further production this document does not adopt. **`strictness` is refused as an
> observation member by name in §16.2**, and this box is the reason.

> **Normative (D5 repriced as THREE options — the round-1 remediation's first item).**
>
> **D5a — the general model.** Both directions, every value `missing`/`extra`/`vars_keyword` can take:
> **(1)** a `set(<x>.keys())` `Term`; **(2)** a set-difference `BinOp` `Term` over two resolved `Seq`s;
> **(3)** a set-display `Term`; **(4)** an `E-SIG` rule resolving the three comprehension shapes PLR
> writes over `inspect.signature(<t>).parameters.items()`; **(5)** a representation of the residual
> `**kwargs` key set. **~350 LOC**, increment 8's. Nothing in this increment needs it, and the gate
> needs none of (1), (2) or (5): the `SAFE` direction never forms the difference.
>
> **D5b — two site rules, the `SAFE` direction only.** A rule keyed on
> `(LiquidHandler._check_args, :375)` resolving `Len(Var("missing"))` to `0` when
> `params(backend_class, m) ⊆ default`, and a rule keyed on `(LiquidHandler._check_args, :383)`
> resolving `Len(Var("vars_keyword"))` to `1` when `has_var_keyword` is true — both reading
> `(backend_class, m)` from §16.2's observation, `m` and `default` from §16.4's `caller_args`, and
> `params`/`has_var_keyword` from §16.3. One further `Term` production is required and only one: an
> `ast.Set` display of `ast.Constant`s, for `default={"ops", "use_channels"}`. **~100–130 LOC plus a
> new registry row against a full `BUDGET_CAP` 24** (the box above), with C15's absence rule as its
> soundness precondition and D-G6's one-directionality as its argument. **It lands the headline in
> this increment**, conditional on `:321` also clearing (§16.10.2's conjunction).
>
> **D5c — NO.** `:375` and `:383` stay ½ on all 544 operations, `scope_verdict` stays `UNKNOWN`
> everywhere, and the increment is measured against §16.10.2's conjunctive NO-GO-side criterion.
>
> **The three options are put to the user through D6**, because D5b and the repaired `:321` rule
> (§16.1.3) are the **same class of fact** and it would be dishonest to ask twice for one concession.

### 16.1.2 `:409` — decidable, and the three mechanisms it needs

`_make_sure_channels_exist` is three lines
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:405-409`): `invalid_channels = [c
for c in channels if c not in self.head]`, then `if not len(invalid_channels) == 0: raise ValueError`.

Under increment 6's shipped machinery the guard already parses without an `Opaque` node: α binds
`invalid_channels` to `Filtered(Var("channels"), Cmp(Var("c"), "not in", EnvRef(("self", "head"), None)))`
and the guard's truth is exactly *"∃ a channel not in `self.head`"*.

> **Normative correction (D-G1, conceded — spec_version 1 named the wrong evaluation path).** The draft
> said G3 "rewrites `len(Filtered) == 0` as `Not(AnyOf(seq, pred))`" and that the resulting quantifier
> would need element-wise binding, citing `_eval_allof_anyof`. **Both halves are wrong.** G3 constructs
> **no** `AnyOf` node: `_eval_cmp` dispatches this shape to `_maybe_alpha_emptiness`
> (`plr-sema/src/plr_sema/check/predicate.py:459-480`) and thence to `_eval_alpha_existential`
> (`plr-sema/src/plr_sema/check/predicate.py:433-456`), which **already loops over the iterand's real
> resolved items and overrides the bound name per element** (`:449-451`). The module's own docstring
> distinguishes this path from `_eval_allof_anyof` by name and says why
> (`plr-sema/src/plr_sema/check/predicate.py:402-410`). **`:409` therefore needs no new quantifier
> machinery at all**, and spec_version 1's Q-BIND clause — an additive `target` field on three wire
> nodes plus a `parse` half — is **withdrawn in full** (§16.5.5). It was dead machinery: no site at
> this pin reaches it.

**Three things stop `:409` deciding, and this increment supplies all three — and only these three:**

1. **`channels` never binds.** It is `_make_sure_channels_exist`'s own parameter at `depth == 1`, and
   increment 6's `E-CALL(depth)` forbids resolving it against the entry point's kwargs. §16.4's
   delegate→caller argument map binds it from the positional call
   `self._make_sure_channels_exist(use_channels)` at
   `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:520-522`, after which
   `use_channels` resolves in `pick_up_tips`'s own namespace through the P3a hook — `channels_for_call`
   returned non-`None` on **every** executed `pick_up_tips` operation at T30, and `:502`'s own
   dependence on that resolution is measured decided at 223/223
   (`outputs/plr-sema/oracle_replay_260909_inc6.json:109-125`).
2. **`self.head` is ⊤ in term position.** §16.5's rule **R-HEAD** resolves
   `EnvRef(("self", "head"), None)` to the observed key set of the receiver's `head` dict (§16.2), a
   `Seq` this document declares **complete**.
3. **Membership decides nothing.** Increment 6 §15.13 deleted the deciding case with three explicit
   reopening conditions; the shipped `_eval_cmp` returns `None` for every membership operator
   (`plr-sema/src/plr_sema/check/predicate.py:542-543`). §16.5.4 satisfies all three reopening
   conditions and states which clause answers which.

**Nothing else.** `:409` needs the caller map, R-HEAD in term position, and the membership case — no
quantifier refinement, no `target` field, no `parse` change.

### 16.1.3 `:321` — the deck, and what `SAFE` there would actually assert

`_assert_resources_exist` loops over `resources` and, per resource, looks the deck up **by name** and
compares (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:305-321`). Two facts about
PLR make this site much harder than "deck membership", and both were read at the pin this pass.

**Fact 1: the lookup raises before the guard is reached.** `Resource.get_resource` returns `self` on a
name match, recurses into `children`, and otherwise raises `ResourceNotFoundError`
(`external/pylabrobot/pylabrobot/resources/resource.py:566-589`). So *"the resource is not on the
deck"* does **not** make `:321` fire; it makes `:318` raise a different exception at a site the
contract table carries no guard for. A membership observation therefore decides a **different** raise
from the one `:321` names.

**Fact 2: the comparison is structural, and the IR cannot represent it.** `Resource.__eq__` compares
name, all three absolute sizes, location, category **and children**
(`external/pylabrobot/pylabrobot/resources/resource.py:160-170`). The IR's `Resource` value carries
`slot`, `type`, `element_type`, `is_container`, `is_parameter`, `parents` and `grid` and **no name at
all** (`plr-sema/src/plr_sema/check/ir.py:178-191`) — let alone geometry, location or children. Since
the lookup key is `resource.name`, the name half of `__eq__` is `True` by construction; what remains is
a geometry-and-children comparison between two objects the analyzer models as one slot index.

> **Normative (what a `SAFE` at `:321` asserts, and what would have to be assumed).** A `SAFE` at
> `:321` asserts: *the object this call passes at this slot is structurally equal to the deck's object
> of that name*. No observation available to this analyzer establishes it without observing the guard's
> own answer, and no derivation establishes it at all. It is therefore an **assumption**, and this
> document names it rather than smuggling it:
>
> **A-DECK-OBJECT** — *a resource the program passes to a `LiquidHandler` operation is the deck's own
> object of that name.*
>
> **What breaks if it is false:** a program that constructs a second `Resource` with a name already on
> the deck and passes it gets a `SAFE` where PLR raises `ValueError` — a false `SAFE`, the unsound
> direction. **What checks it, stated honestly after C18:** the tier-1 fence, unmodified
> (`plr-sema/eval/oracle_common.py:767-786`), checks it **on the corpus** — on each of the 288
> operations, had A-DECK-OBJECT been false the guard would have fired, PLR would have raised, and the
> `SAFE` row would have been counted unsound. That is a real check of exactly A-ENABLED's kind, and it
> is **not** a check of the assumption in general: §16.11 establishes that no kwarg mutator can
> construct a violation, so *its exposure is bounded by argument on the corpus, not by adversarial
> measurement*. AC-16.13 therefore requires one **hand-built** duplicate-name fixture — a second
> `Resource` with a matching name and mismatched geometry, constructed directly rather than through the
> mutator API — so the assumption has at least one adversarial witness. **This changes D2's basis, not
> its sign, and the user is told so.** **How it compares to what the analyzer already assumes:** it is
> strictly narrower than **A-SINGLE**, which claims one receiver variable denotes one instance for the
> whole graph with no aliasing, and it is partly self-discharging under **A-COMPLETES** in exactly
> A-ENABLED's manner — a completed preceding operation on the same resource implies that operation's
> own `_assert_resources_exist` passed; the four-row table is at
> `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:749-754`.
>
> **Adding a fifth named assumption is a USER decision, not the sprint's.** It is **D2** (§16.15),
> recommended **YES**, and after round 1 it is **conditional on D6**, because the only mechanism that
> can fire it is a site rule of D5b's class.

> **Normative (C3, conceded — R-DECK as an `EnvRef` shape is WITHDRAWN in full).** spec_version 1
> specified R-DECK to match
> `Cmp(EnvRef(("self", "deck", "get_resource"), (t,)), "==", u)`. **That shape does not occur in the
> contract table.** The shipped guard record for `:321` is
> `Not(Cmp(Var("resource_from_deck"), "==", Var("resource")))` with `"bindings": []` and
> `"free_vars": []` (`plr-sema/data/derived_contracts.json:88795-88822`) — no `EnvRef` anywhere. Two
> independent reasons, each sufficient: (a) `resource_from_deck = self.deck.get_resource(resource.name)`
> is a plain `ast.Assign` of a call, which is neither α (a `ListComp` with a bare-`ast.Name` `iter`)
> nor β (a length), and `bindings.substitute` replaces **only** α-bound `Var`s
> (`plr-sema/src/plr_sema/derive/bindings.py:215-237`), so `Var("resource_from_deck")` is never
> replaced by anything; and (b) `resource` is a **`for`-loop target** — the record's own trail is
> `["if not resource_from_deck == resource", "for resource in resources"]`
> (`plr-sema/data/derived_contracts.json:88819-88822`) — and nothing in this increment binds a `for`
> target.
>
> **The two productions that would repair the `EnvRef` route are NOT adopted**: a third binding idiom
> for `x = <call>` plain assignments, and element-wise binding over a `for` target. Each is a new
> production with its own soundness argument and its own registry consequence, and together they price
> D2 far above spec_version 1's ~110 LOC.

> **Normative (the repaired `:321` rule — a SITE RULE, of exactly D5b's class).** A rule keyed on
> `(LiquidHandler._assert_resources_exist, :321)` evaluates the guard **`F`** iff **every** element of
> the caller-bound `resources` resolves to an `ir.Ref` whose slot's observed name is a member of the
> observation's `deck_resource_names`, and **½** otherwise. It **never** evaluates `T` (Fact 1: an
> absent name raises at `:318`, not at `:321`).
>
> **`resources` binds cleanly and that is what makes the rule cheap.** `self._assert_resources_exist(tip_spots)`
> at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:520-522` is the positional call
> §16.4's map handles, and `tip_spots` is `pick_up_tips`'s own parameter, resolving to a `Seq` of
> `ir.Ref`s. The rule reads a **caller-bound parameter** and an **observed name map**; it never touches
> `resource_from_deck` or the `for` target, which is why the two refused productions are not needed.
>
> **The cost is the same cost D5b carries, and it is the same concession:** it is keyed on a PLR
> qualname and on that function's own parameter name, so it is a hand-written semantic model of a named
> PLR function body. **It is D6, not a separate ask** (§16.15).

The two alternatives are recorded so the decision is a choice between named options rather than a
single ask. **(a) Add `name` to `ir.Resource`.** That is a wire change and an `IR_VERSION` bump
(`plr-sema/src/plr_sema/check/ir.py:170-191`, `:905-915`), it re-keys every cached entry, and it still
does not decide `__eq__` — it decides only the name half, which is already `True` by construction. It
buys nothing the site rule does not, at strictly higher cost. **Rejected, and recorded as rejected.**
**(b) Leave `:321` at ½.** `pick_up_tips`'s residual keeps a third site, `n_findings_decided` gains
607 instead of 895, and `scope_verdict` stays `UNKNOWN` on every operation **even if D5b ships** —
which is the conjunction §16.10.2 now states and spec_version 1 never did.

### 16.1.4 `:514` — decidable from the backend's method body

The condition is `not all(self.backend.can_pick_up_tip(channel, tip) for channel, tip in
zip(use_channels, tips))` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:506-514`),
which increment 6 parses to
`Not(AllOf(Zip((Var("use_channels"), Var("tips"))), EnvRef(("self", "backend", "can_pick_up_tip"), (Var("channel"), Var("tip")))))`.

**The `Zip` cannot resolve, and this increment does not make it resolve.** Increment 6's `Zip` rule is
⊤ unless **every** item resolves to a concrete `Seq`; `tips = [tip_spot.get_tip() for tip_spot in
tip_spots]` at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:504` is a
*projecting* comprehension that α rejects, so `tips` is ⊤ and the `Zip` is ⊤. That stays true here.

**What decides the guard is the body, not the sequence.** The chatterbox backend's `can_pick_up_tip`
body is exactly `return True`
(`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:241-242`). If the `EnvRef`
resolves to the constant `True` **independently of its arguments** — which is what a constant-return
body means — then `AllOf` over a ⊤ sequence of a uniformly-`T` body is `T` (§16.5.5's monotonic
clause), `Not(T)` is `F`, and the `raise_guard` does not fire: **`SAFE`**. The measured population of
constant-return `can_pick_up_tip` bodies across the whole PLR tree at the pin is **2 of 8** —
`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:241-242` and
`external/pylabrobot/pylabrobot/liquid_handling/backends/serializing_backend.py:241-242` — while the
abstract base is a docstring-only `@abstractmethod`
(`external/pylabrobot/pylabrobot/liquid_handling/backends/backend.py:183-187`) and the remaining five
are multi-statement. §16.3 publishes the whole-surface count rather than this one.

---

## 16.2 The observation record

> **This section's every legitimacy argument is stated against increment 5 §14.6**
> (`.praxia/docs/specs/260903_plr-sema-volume-increment.md:602-741`), which is the only precedent in
> the analyzer for reading anything outside the extracted graph, and which recorded **two failed
> discharges** so the question would not be re-opened without new facts
> (`.praxia/docs/specs/260903_plr-sema-volume-increment.md:675-689`). Each field below is argued
> against both, individually and by name.

### 16.2.1 The record

> **Normative (O2 — the observation record).** The executed side returns **one additive result key**,
> `plr_observation`, a JSON object with exactly the fields below and no others. Every field is taken
> **inside** the verifier's window and **returned by** the executed side; nothing is observed from
> outside it. This is increment 5's O5 pattern verbatim
> (`.praxia/docs/specs/260903_plr-sema-volume-increment.md:700-723`), and `volume_tracking_observed`
> (`training/verify/verifier.py:110-128`, returned at `:184-200`) is the shipped instance of it.
>
> | field | type | what it decides |
> |---|---|---|
> | `backend_class` | a `str` | selects the row of §16.3's derived surface |
> | `num_channels` | an `int` | published; **decides nothing on its own** — see the box below |
> | `head_channels` | a list of `int` | R-HEAD (§16.5.1) — the key set `:409` reads |
> | `deck_resource_names` | a list of `str` | **D6 only** — §16.1.3's `:321` site rule |
>
> **Normative (ONE capture point, and it is fail-closed — C13, C17, conceded).** All four fields are
> read at a **single** point: **after** `await setup.machine.setup()` and **before** `_execute`
> (`training/verify/verifier.py:130-134`), inside a guard that sets `plr_observation = None` on any
> exception rather than propagating.
>
> - **After `machine.setup()`**, because the receiver's head dict is empty until PLR's own setup builds
>   it — declared at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:155-166` and
>   filled at `:187-197`. spec_version 1 placed `backend_class`/`num_channels` "after `build_setup`,
>   before `_execute`", a window that **straddles** `machine.setup()` and sits outside the inner
>   handler, so a raising read would be caught by the outer handler at `training/verify/verifier.py:143-144`
>   and converted into a harness-level failure. One capture point removes that window entirely.
> - **Before `_execute`**, because a failed operation may leave the trackers rolled back.
> - **`plr_observation` is `None`, never partial.** It is `None` on the **deck-build early return**
>   (`training/verify/verifier.py:143-162`, where `setup is None` and no field is obtainable — the same
>   path on which `volume_tracking_observed` returns its default at `training/verify/verifier.py:234`),
>   and `None` whenever **any** field's read raises. `verify()` has **three** return sites, not two, and
>   spec_version 1's AC-16.1 was unsatisfiable on the third. A `None` observation contributes no `obs:`
>   member, so §16.5's rules all decline — which is exactly §16.5.1's partial-record refusal, now agreed
>   with on both sides.
>
> **Normative (`deck_resource_names` is extracted RECURSIVELY — C14, conceded).** `snapshot()["topology"]`
> is `self.deck.serialize()` (`training/verify/deck.py:146-159`), a nested serialisation and not a name
> list, while `Resource.get_resource` matches the deck's own name **plus every descendant**, reached by
> recursion (`external/pylabrobot/pylabrobot/resources/resource.py:566-589`). The observation is
> therefore *the deck's own `name` together with the `name` of every descendant, by the same recursion*.
> It is read directly off the live tree inside the window — the pattern `SetupHandle` already uses in
> `iter_tracked` (`training/verify/deck.py:130-137`) — rather than by re-parsing the serialisation,
> because a serialisation walk would have to reproduce `get_resource`'s recursion in a second place.

> **Normative (the record is CLOSED, and these are refused BY NAME).** A field absent from the table
> above is not observed. Refusing them by name is what keeps the record from growing one
> convenience at a time:
>
> - **`strictness`** — refused. §16.1.1's box: it decides nothing alone and `Strictness.STRICT` is not
>   a `Term`. Increment 6 §15.6 reached the same conclusion by a different route; two independent
>   arguments now stand behind the refusal.
> - **per-well seeded volumes** — refused. That is the well-seeding observation increment 6 §15.13
>   defers, it belongs to the volume family's `volume_state_unknown` cell, and admitting it here would
>   move a number this increment's gate does not read.
> - **lid topology** — refused. Increment 4 §13.1's disposition stands and `:116`/`:117` are not on the
>   gate candidate.
> - **`head96`** and **`_default_use_channels`** — refused. Neither appears in any guard on any of the
>   544 executed operations; admitting a field no guard reads is exactly the surface growth §9.4 exists
>   to prevent.
> - **anything read from `after`** — refused, categorically. `after = setup.snapshot()` is taken
>   *after* execution (`training/verify/verifier.py:142`); a fact read from it is a fact about the
>   outcome, and conditioning a static verdict on the outcome is not an observation, it is the answer.
> - **the value of any guard's own condition** — refused, categorically, for the same reason.

### 16.2.2 The legitimacy argument, per field

Increment 5's two failed discharges are: *(i) a single `env` member would be a quantified claim dressed
as an observation*, because a deck carries one tracker per well and per tip and no single fact stands
for "every tracker relevant to this guard was enabled"; and *(ii) "no `.disable()` appears in the
program" is sound only if the analyzed graph is the whole world*
(`.praxia/docs/specs/260903_plr-sema-volume-increment.md:675-689`).

| field | against (i) — is it quantified? | against (ii) — does it assume the graph is the world? |
|---|---|---|
| `backend_class` | No. One process, one `LiquidHandler`, one `backend` attribute assigned once at construction (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:155-158`). It is a single value, exactly `does_volume_tracking()`'s shape. | No. It is read *from* the executed object, not inferred from the absence of something in the graph. |
| `num_channels` | No. A single `int` off a single backend instance (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:59-61`). | No, same. |
| `head_channels` | **This is the field to attack, and the attack is answered by observing the key set rather than deriving it.** Deriving `range(num_channels)` from `:197` would be a claim about how `head` is *built*; observing `sorted(self.head)` is a claim about what it *contains* at one instant. The set is finite, enumerated, and returned. | No. |
| `deck_resource_names` (**D6**) | Borderline, and the border is where D2 sits. The set is finite and enumerated, so it is not quantified over unseen instances — but it decides only the `get_resource` half of `:321`, and the `__eq__` half needs **A-DECK-OBJECT**. §16.1.3 is the argument; D2, conditional on D6, is the decision. | No for the observation; **yes for the assumption**, which is why the assumption is named, published in the assumption table with its breakage column, checked by the fence **on the corpus**, and given one hand-built adversarial witness in AC-16.13. |

> **Normative (a third failure mode increment 5 did not have to name, because it had one member).**
> An observation that is a **function of the guard being decided** is refused however it is taken. The
> test is mechanical: could the harness compute this field only by evaluating the same expression the
> guard evaluates? If yes, it is the answer, not an observation. `head_channels` passes (the guard
> evaluates a membership test *against* the key set; the field is the key set). A hypothetical
> `assert_resources_exist_passed` fails. This test is what makes the closed list above a rule rather
> than a preference.

### 16.2.3 The cache key

> **Normative (O2 enters `env`; the tuple gains no component).** The observation is encoded as
> `obs:<key>=<value>` **string members of the existing `env` frozenset**, not as a sixth `cache_key`
> component. `cache_key` stays exactly five-tuple-shaped
> (`plr-sema/src/plr_sema/check/ir.py:918-953`), `check_ir`'s and `check_graph`'s keyword-only `env=`
> parameters are unchanged (`plr-sema/src/plr_sema/check/__init__.py:616-624`, `:968-975`), and the
> `tuple(sorted(env))` encoding keeps the key JSON-round-trippable and order-independent by
> construction — the two properties `cache_key`'s own docstring names.
>
> **Why not a sixth component.** A sixth element changes the key's **arity**, which every caller, every
> persisted store and every test that unpacks a key sees; the existing `env` slot was added for exactly
> this purpose and already carries a runtime-observed environment set. Extending it costs no signature
> change, no `IR_VERSION` bump, and preserves the property that a caller passing no observation gets a
> key **byte-identical** to today's.
>
> **Normative (canonical encoding — the value is JSON, and that is what makes it INJECTIVE; C12,
> conceded on the injectivity half).** The value of an `obs:<key>=<value>` member is
> `json.dumps(<value>, sort_keys=True, separators=(",", ":"))` of the field's own Python value, and
> **nothing else**. A list of `int` is sorted **numerically** before encoding; a list of `str` is sorted
> **lexicographically**. So the benchmark's own members are exactly
> `obs:backend_class="LiquidHandlerChatterboxBackend"`, `obs:num_channels=8`,
> `obs:head_channels=[0,1,2,3,4,5,6,7]`.
>
> **spec_version 1's `,`-joined encoding is WITHDRAWN as non-injective.** `deck_resource_names` carries
> user-chosen PLR resource names, which may contain `,` or `=`; under the joined encoding two distinct
> observations produce the same `env` member, so `cache_key` can return a verdict computed under a
> *different* observation. That is a cache-correctness event, not a hygiene one. JSON escaping closes
> it, and the `int`-vs-`str` sort rule closes the second half: string-sorting a 16-channel head gives
> `0,1,10,11,…,2` where numeric sorting gives another string, and two implementations would disagree on
> the key for one observation. AC-16.1 carries a fixture over a resource name containing both `,` and
> `=`.
>
> **Normative (the deck observation ENTERS `env` — D-G3, conceded).** spec_version 1 enumerated three
> `obs:` members and threaded `deck_resource_names` to the evaluator as a per-slot boolean built by
> `resources_from_example` (`plr-sema/eval/oracle_common.py:574`), which meant a fact that changes the
> verdict might never reach the fifth `cache_key` component — falsifying §16.6's own claim (4). **Under
> D6 the observation adds a fourth member,
> `obs:deck_resources=<sha256 of the JSON-encoded per-slot name map>`.** A digest rather than the map
> itself, because the map is per-benchmark-row and would make `env` unbounded; a digest of the exact
> object the evaluator reads, because anything less does not partition. The per-slot map is still
> threaded to the evaluator by the harness that builds the RESOURCE instructions; **what changes is
> that its digest is in the key**, so no two observations share a verdict.
>
> **The `obs:` prefix is load-bearing and is reserved.** `E-UNCOND` way (2) tests a bare zero-argument
> callee **name** against `env` (`plr-sema/src/plr_sema/check/predicate.py:1088-1097`). A member
> containing `:` and `=` can never equal a Python identifier, so no `obs:` member can satisfy way (2)
> and **no observation can manufacture reachability**. No member without the prefix is ever added by
> this increment, and `does_volume_tracking` — the one existing member — is untouched.

> **Normative (the fail-closed default, SCOPED to what it actually covers — C11, conceded).** With no
> `obs:` member in `env`, **every** rule in §16.5 declines and every `EnvRef` is ½ in predicate
> position and ⊤ in term position, which is increment 6's `E-ENV` unchanged
> (`plr-sema/src/plr_sema/check/predicate.py:262-278`, `:646-658`).
>
> **That is a claim about §16.5, and spec_version 1 over-scoped it to the increment.** It is **not**
> true after T42: the argument map resolves depth-1 names with **no observation at all**, and D1's lift
> can emit `WILL_FAIL` on a population that previously could not — both with `env` empty. It is **not**
> true after T48/T49 either, whose site rules read the observation and would decline, but whose
> presence changes nothing about the empty-`env` case only because they decline. **The byte-identical
> assertion in AC-16.1 is therefore scoped explicitly to the T40 state**, where it holds and where it
> is the one assertion a stubbed implementation cannot fake; re-run after T43 it is a statement about
> §16.5's rules alone, and an implementer who reads it as a standing invariant will chase a phantom
> regression.

---

## 16.3 The derived backend surface

> **Normative (S1 — the table).** For every `(class, method)` pair in the derive package's own PLR
> function index, the surface records:
>
> | key | derivation | fail-closed default |
> |---|---|---|
> | `params` | the parameter names after `self`, excluding `*args`/`**kwargs`, that have **no** default | `[]` never guessed; a method whose AST does not parse is **absent** from the table |
> | `has_var_keyword` | some parameter is `**kwargs` | absent ⇒ unknown ⇒ every rule reading it declines |
> | `has_var_positional` | some parameter is `*args` | as above |
> | `constant_return` | present **iff** the body is **exactly one** `ast.Return` whose `value` is an `ast.Constant`; the value is that constant, JSON-encoded | absent ⇒ no constant-return rule fires |
>
> **`constant_return`'s shape test is deliberately the narrowest that decides `:514`.** Exactly one
> statement, that statement an `ast.Return`, its value an `ast.Constant`. A docstring **counts as a
> statement**, so a docstring-plus-return body is **not** admitted — which is what keeps the rule from
> becoming "the first return wins". Anything wider — two statements, a conditional return, a return of
> a name — is a dataflow pass by another name (increment 4 §13.12) and is refused.

> **Normative (the ABSENCE rule — the surface is an AST fact and every rule reading it claims a RUNTIME
> value; C15, conceded, and it is D5b's soundness gate too).** A `(class, method)` row is **absent**
> from the surface — so every rule reading it declines — when **any** of the following holds of the
> definition:
>
> 1. its `decorator_list` is **non-empty**;
> 2. it is a `property` (the `@property`/setter pair is caught by (1), and a `property(...)` assignment
>    by (3));
> 3. the same `(module, qualname)` is defined at **more than one** `lineno` in the index.
>
> **Why this is not conservatism for its own sake.** `constant_return` is read off the AST and R-CONST
> claims the value the *runtime call* returns; a non-`functools.wraps` decorator makes those two
> different, and a `@some_wrapper`-decorated `can_pick_up_tip` whose body is `return True` would produce
> a false `SAFE` at `:514` — the unsound direction. The same gap sits under `params` and
> `has_var_keyword`, which is exactly what D5b reads and what `inspect.signature` resolves at runtime
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:353-359`). The rule **bites
> immediately**: the abstract base's `can_pick_up_tip` is `@abstractmethod`-decorated
> (`external/pylabrobot/pylabrobot/liquid_handling/backends/backend.py:183-187`), so it is absent, which
> is the right answer. `staticmethod` and `classmethod` fall to clause (1) as well. Clause (3) closes
> the conditional-redefinition case, where two ASTs share a qualname and the index's first-wins rule
> would pick one arbitrarily (`plr-sema/src/plr_sema/derive/receiver_state.py:1288-1291` records that
> first-definition-wins). AC-16.2 carries the negative fixture; a decorated body that is otherwise a
> perfect `return True` must yield an absent row.

> **Normative (ONE closed selection rule, with its own published count — C16, conceded on the first
> half).** spec_version 1's selection was *"`method` occurs as the last segment of some admitted
> `EnvRef` path in the regenerated contract table, **or as a key of some class's own parameter set
> reachable from one**"*. The second clause defined neither "parameter set" nor "reachable", no
> acceptance criterion tested it, and two implementers would not produce the same table — which makes
> AC-16.2's "complete measured selection" unfalsifiable. **It is deleted.** The selection is now the
> first clause alone:
>
> > A `(class, method)` pair is emitted **iff** `method` equals the last segment of some `EnvRef.path`
> > occurring in the regenerated contract table, **and** the pair survives the absence rule above.
>
> Two published counts make it checkable rather than assertable: `n_surface_candidates` (pairs the
> first clause selects) and `n_surface_absent_by_c15` (pairs the absence rule then removes), with
> `n_surface_rows` their difference. The rule reads the contract table, which is derived; it reads no
> literal, and it terminates in one pass.

> **Normative (the surface is keyed on PLR's own index and introduces NO hand-typed fact — the round-1
> correction of increment 6 §15.6, applied in advance).** The table is built over
> `build_plr_function_index` (`plr-sema/src/plr_sema/derive/receiver_state.py:1773-1806`), the
> `(module, qualname, lineno) → AST` map the derive package **already** builds over every module-level
> function and every class method in the PLR tree. **The base class name `LiquidHandlerBackend` appears
> nowhere in the derivation**, and neither does any method list: the table is not "backend classes", it
> is "classes", and the selection that keeps it small is itself derived — the one closed rule in the
> box above. That test reads the contract table, which is derived; it reads no literal.
>
> **This is the difference between a derivation and a benchmark-local hack, and increment 6 §15.6 named
> it in exactly these terms**: *"deriving over one benchmark backend would produce a fact that cannot
> enter the shipped contract table (which is keyed on PLR's own surface, not on a harness choice)"*.
> The harness choice enters at **one** point and one only: §16.2's `backend_class`, which **selects a
> row** of a table derived over the whole surface. Selection is not derivation.

**The published selection, as a measured fact for the reader and not as an input to anything.** At the
pin there are exactly **six** direct `LiquidHandlerBackend` subclasses, enumerated by ripgrep over the
whole PLR tree and each `class` line read this pass:
`OpentronsOT2Backend` (`external/pylabrobot/pylabrobot/liquid_handling/backends/opentrons_backend.py:80`),
`LiquidHandlerChatterboxBackend` (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:24`),
`TecanLiquidHandler` (`external/pylabrobot/pylabrobot/liquid_handling/backends/tecan/EVO_backend.py:56`),
`SerializingBackend` (`external/pylabrobot/pylabrobot/liquid_handling/backends/serializing_backend.py:26`),
`HamiltonLiquidHandler` (`external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/base.py:46`),
and `HamiltonTCPBackend` (`external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/tcp_backend.py:66`).
Three carry `metaclass=ABCMeta`. **The one method the gate reads, `can_pick_up_tip`, has eight
definitions in the tree, of which exactly two are a single `return <Constant>`** — chatterbox's and
`SerializingBackend`'s (`external/pylabrobot/pylabrobot/liquid_handling/backends/serializing_backend.py:236-242`).
T41 publishes the whole-surface counts and this paragraph is a prediction for it to falsify.

> **Normative (where it lives: an additive top-level key of the shipped contract document).**
> `plr-sema/data/derived_contracts.json` has exactly four top-level keys today — `contracts`,
> `receiver_state`, `schema_version` and `stamp`. The surface is a **fifth**, `backend_surface`. It is
> **not** a separate file, and the reason is the cache: `contracts_sha` is
> `sha256(contracts_json)` over the whole document
> (`plr-sema/src/plr_sema/check/ir.py:918-953`), so an additive top-level key participates in the cache
> key automatically and a regeneration cools the cache by design, exactly as increment 6 §15.8 records
> for `predicate` and `param_defaults`. A separate file would be a fact the cache key does not cover,
> which is a correctness event dressed as a packaging choice.

> **Normative (registry: ZERO).** §16.3 adds no registry row, no per-row ceiling, and no vocabulary
> member. Its derivation is an AST shape test over PLR's own recorded surface, in the same class as
> `is_dynamic_raise` (`plr-sema/src/plr_sema/derive/__init__.py:1076-1080`) and `reachability_clear`
> (`plr-sema/src/plr_sema/derive/bindings.py:778-815`), both of which increment 6 established cost
> nothing. **This is recorded as a NON-decision (`D3`) precisely so the round can attack it**: if a
> reviewer can name one literal PLR fact this section hand-types, the claim is false and the section
> owes a row. The candidates a reviewer should check first are the base-class name (absent by the box
> above), the method list (absent, derived from the contract table), and `constant_return`'s shape
> (an `ast` node-class test, not a PLR idiom). **Round 1 attacked it and it survived**, with one
> clarification the section owed and did not have:
>
> > **Normative (harness-side observation paths are OUTSIDE the registry's scope, and here is why —
> > C16, second half, rebutted with the precedent named).** §16.2's record does hand-type four literal
> > PLR access paths on the harness side — `type(backend).__name__`, `backend.num_channels`,
> > `machine.head`, and the deck tree walk. **They book nothing, and the precedent is increment 5's
> > `volume_tracking_observed`** (`training/verify/verifier.py:178-190`), which reads a named PLR global
> > from inside the window, is normative in increment 6 §14.6's O5 box, and books no registry row. The
> > registry's own scope statement is *"syntactic patterns over how PLR/its own analyzer is written"*
> > (`plr-sema/src/plr_sema/_hand_maintained.py:976-983`) — the **analyzer's front end**, not the
> > evaluation harness. The split is therefore not hiding surface: what §16.5 pays a ceiling unit for is
> > the **evaluator-side** table that matches `EnvRef` paths, which is front-end surface and goes stale
> > silently; a harness read that breaks fails loudly at the next run, and the fail-closed
> > `plr_observation = None` rule (§16.2.1) makes it fail into today's behaviour rather than into a
> > verdict.

---

## 16.4 The delegate→caller argument map

Increment 6 §15.4's `E-CALL(depth)` forbids the resolution outright and §15.12's sizing note prices
building it at **~90 LOC over a new derived field with its own measured selection and its own registry
argument**, deferring it here by name. Without it `channels`, `resources` and `backend_kwargs` never
bind and `:409`, `:321` and `:875` are permanently ½.

> **Normative (M1 — the mapped call shape, and the closed list of what is refused).** For an entry
> point `K` and a delegate `D` reached by a `delegates_to` edge, the map binds `D`'s own parameter
> names to caller-side `Term`s **iff every one** of the following holds; on any failure the map for
> that `(K, D)` pair is **absent**, and an absent map resolves every free name of every guard at
> `depth >= 1` to ⊤ — today's behaviour exactly.
>
> 1. **`self.` receiver only.** The call is an `ast.Call` whose `func` is
>    `ast.Attribute(value=ast.Name("self"), attr=D)`. A module-level delegate — `_check_no_lid`, called
>    bare — is **not** mapped. This is P9's own restriction (`plr-sema/src/plr_sema/derive/receiver_state.py`,
>    `_delegate_channel_bindings`), adopted rather than widened.
> 2. **Called exactly once in `K`'s body.** P9's shipped singleton test, adopted verbatim. A delegate
>    called twice has two argument vectors and one guard record; binding either would be a choice the
>    record cannot express.
> 3. **Positional and keyword arguments, both mapped, by `D`'s own `ast.arguments`.** Positional by
>    index against `D`'s parameter list after `self`; keyword by name. This is the half P9 lacks —
>    it reads `call.keywords` only, while PLR calls every delegate that matters **positionally**
>    (`self._assert_resources_exist(tip_spots)` and `self._make_sure_channels_exist(use_channels)` at
>    `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:520-522`).
> 4. **No `ast.Starred`, no `**` unpacking, no `*args`/`**kwargs` on `D`.** Fail-closed: the mapping
>    would be positionally ambiguous.
> 5. **Every argument expression parses as a `Term`.** An argument that does not is bound to nothing
>    and its parameter resolves ⊤; the other parameters still bind. Partial maps are admitted because a
>    guard reads one name, not the vector.
> 6. **One level only.** The map is built for `depth == 1` guards. **A guard at `depth >= 2` resolves
>    every free name to ⊤**, unconditionally. Transitive composition compounds every one of the
>    conditions above and `SurveyRecord.delegates` is a bare `set[str]` that records no call site at
>    all; the general case is a call graph, not a map.

> **Normative (the wire representation, additive, on the `reachability_clear` precedent).**
> `InlinedGuard` — ten fields in the landed dataclass, `condition`, `predicate`, `scope_trail`,
> `raises`, `kind`, `free_vars`, `site`, `depth`, `bindings`, `reachability_clear`
> (`plr-sema/src/plr_sema/derive/__init__.py:505-514`) — gains an **eleventh**, `caller_args`:
>
> ```
> caller_args: dict[str, Any] | None = None     # D's parameter name -> a predicate_ast Term, JSON-encoded
> ```
>
> The value type is the **existing** `Term` JSON, so `to_json`/`from_json` need no new node kind and
> the round-trip is the one `predicate_ast` already ships. **Absent ⇒ `None` ⇒ fail-closed**, which is
> `bindings`'s default and `reachability_clear`'s, and which is what makes the field safe to add
> without a coordinated regeneration. It is computed in `derive/bindings.py`, beside
> `compute_local_bindings_for_guard` (`plr-sema/src/plr_sema/derive/bindings.py:690-737`) and
> `compute_reachability_clear` (`plr-sema/src/plr_sema/derive/bindings.py:778-815`), by a new
> `compute_caller_args(K, D)` — the module that already owns every "read `K`'s AST at
> guard-construction time" derivation, and the one entry point this increment extends.

> **Normative (M2 — how a mapped name resolves, and the ordering that prevents a double resolution).**
> For a guard at `depth == 1` whose free `Var(name)` is a parameter of `D`: **(1)** if `caller_args`
> has an entry for `name`, evaluate that `Term` **in the caller `K`'s own context** — the entry point's
> `call.kwargs`, `param_defaults`, α/β bindings and the P3a `channels_for_call` hook, with `E-CALL(5)`'s
> parameter-rebinding clause applying **in `K`**, not in `D`; **(2)** otherwise the existing rules —
> `channels_for_call` for the derived channel term, or an α/β binding in `D`'s own body over `D`'s own
> parameters; **(3)** otherwise ⊤.
>
> **Step (1) is a substitution, not a second evaluation context.** The `Term` is the caller's syntax
> and it is resolved once, against the caller. This is what closes the hazard increment 6 §15.3's
> closing paragraph names — *"α's terms would be matched in the delegate's parameter namespace and
> evaluated against the entry point's `call.kwargs`, a substitution nothing in the repo records"* —
> because the substitution is now recorded, per guard, on the wire.
>
> > **Normative (the caller-side position and scope tests key on the CALL STATEMENT's lineno in `K`,
> > never on the guard's — C10, conceded).** `compute_local_bindings_for_guard` gates every α/β binding
> > on `first_stmt.lineno < guard_lineno` and on an ancestor-prefix test, both computed inside **one**
> > function's line space (`plr-sema/src/plr_sema/derive/bindings.py:723-734`). The guard's `lineno`
> > lives in `D`; applying it against `K`'s body is meaningless in both directions. At this pin every
> > delegate is defined **above** its caller — `_make_sure_channels_exist` at
> > `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:405-409`, its call site at `:521`
> > — so the guard-lineno reading would silently drop every `K`-side binding; for a delegate defined
> > **below** its caller the same comparison would admit a rebinding written *after* the call, which is
> > an unsoundness. **Normative: every caller-side position, ancestor-prefix and `for`-shadow test uses
> > the lineno of the delegate call statement in `K`.** AC-16.3 pins the direction with a fixture in
> > which the delegate is defined below its caller.
> >
> > *One thing C10 got wrong and this box does not repeat:* the `:409` prediction does **not** depend on
> > this. `use_channels` resolves through the P3a channel hook
> > (`plr-sema/src/plr_sema/check/predicate.py:236-239`), which is context-level and lineno-independent,
> > so the 223-op prediction survives even under the broken reading. The clause is a soundness fix, not
> > a prediction rescue.
>
> > **Normative (the `origin` a `caller_args`-resolved name carries — C9, conceded, and it is chosen
> > explicitly rather than left to the implementer).** `_resolve_var` returns `(value, origin)`, with
> > `"operand"` meaning *a home was found* regardless of whether the value is concrete or ⊤, and
> > `"env"` meaning *nothing was found at all*
> > (`plr-sema/src/plr_sema/check/predicate.py:219-255`); §15.7's clause 2 fires
> > `guard_operand_unknown` on an `"operand"`-origin ⊤ and `guard_env_dependent` on an `"env"`-origin
> > one (`plr-sema/src/plr_sema/check/predicate.py:704-714`). **A name resolved through `caller_args`
> > carries origin `"operand"`** — it is an operand of this call, one frame up — which is the same
> > carve-out the α/β branch already takes at `plr-sema/src/plr_sema/check/predicate.py:245-254`. A name
> > with **no** `caller_args` entry keeps `"env"`.
> >
> > **The measured consequence at this pin is that no published reason count moves, and the reason is
> > worth stating because C9 predicted a ~544-finding swing.** The swing would happen if `:383`'s
> > `strictness` acquired a home. It does not: the caller-side expression is `get_strictness()`, a
> > non-`self`-rooted call, which is not a `Term` in G1, so M1's condition (5) gives it **no**
> > `caller_args` entry and it keeps `"env"`. `default={"ops", "use_channels"}` is an `ast.Set` display,
> > likewise not a `Term` today, likewise no entry. `:375`'s `missing` is a **local** of `_check_args`,
> > not a parameter, so it is outside `caller_args` by construction. **`guard_operand_unknown` is
> > therefore predicted unchanged at 144** (§16.10.3), and a movement there is a divergence to
> > investigate rather than an expected effect.
>
> **The name-coincidence exposure is closed in the same stroke and its count must go to zero.**
> Increment 6 block (2) published `name_coincidence_exposure_count` at **936**: depth-≥1 free names that
> *would* have resolved by name coincidence had `E-CALL(depth)` not forbidden it. Under M2 a
> depth-1 name resolves **only** through `caller_args`, so a coincidence cannot resolve anything.
> §16.10 requires the count to be republished and asserted **0** for `depth == 1`; a non-zero value
> means step (1) fell through to a namespace it should not have seen.

> **Normative (D1 — `E-UNCOND(4)` is LIFTED at `depth == 1`, under three preconditions and no fewer).**
> Increment 6's `E-UNCOND(4)` forbids `WILL_FAIL` at `depth >= 1` outright, and its stated reason is
> structural: *"an inlined guard's reachability depends on the call site in the entry point, and
> `InlinedGuard` records nothing about it"*. This increment records it. A guard at `depth == 1` may
> emit `WILL_FAIL` **iff all three hold**, and otherwise yields ½ with `guard_env_dependent` exactly as
> today:
>
> 1. **The delegate's own body is clear.** `reachability_clear` is `True` for the guard, computed
>    against `D` by `compute_reachability_clear` (`plr-sema/src/plr_sema/derive/bindings.py:778-815`) —
>    the field increment 6 T36 already derives and wires. No change.
> 2. **The call site is reached.** A **new** additive derived pair on `InlinedGuard`:
>    `caller_reachability_clear: bool | None`, `compute_reachability_clear(K, call_lineno)` for the
>    delegate's own call statement in `K`; and `caller_scope_trail: tuple[str, ...] | None`, the
>    survey's own trail for that statement. `E-UNCOND`'s ways (1)–(3) must satisfy **every** entry of
>    `caller_scope_trail`, and `caller_reachability_clear` must be `True`. Both absent ⇒ `None` ⇒
>    blocked.
> 3. **The map is total for this guard.** Every free `Var` of the guard's α/β-substituted predicate
>    that is a parameter of `D` has a `caller_args` entry that resolves to a non-⊤ value. A guard
>    firing on a ⊤ operand cannot fire, so this is implied by the predicate evaluating `T` — it is
>    stated anyway, because "implied" is what an implementer skips.
>
> **`depth >= 2` is untouched: still no `WILL_FAIL`, ever, this increment.**
>
> > **Normative (in-loop guards are protected by the TRAIL, not by a fourth precondition — C19, whose
> > blocking half is rebutted on the evidence).** C19 asked for a fourth clause forbidding `WILL_FAIL`
> > for a guard inside a `for`/`while` whose iterable may be empty. **It is not needed, and the reason
> > is a fact about the shipped record that this document owed and did not state:** `scope_trail`
> > **does** record loop headers — `:321`'s trail is
> > `["if not resource_from_deck == resource", "for resource in resources"]`
> > (`plr-sema/data/derived_contracts.json:88819-88822`) — and `_scope_entry_value` gives a `for`/`while`
> > header ½ and never `F`, because `ast.parse` on a bare header text is a `SyntaxError` and therefore
> > `Opaque` (`plr-sema/src/plr_sema/check/predicate.py:1052-1066`). `_entry_satisfies_uncond` then returns
> > `False` for such an entry, so `guard_is_unconditional`'s `all(...)` can never pass
> > (`plr-sema/src/plr_sema/check/predicate.py:773-788`). **An in-loop guard has a non-empty trail with
> > an unsatisfiable entry and can never emit `WILL_FAIL`, before or after the lift**, and precondition
> > 2 applies the identical test to `caller_scope_trail`. **No fourth precondition and no sixth AC-16.4
> > fixture.** What survives of C19 is a note rather than a clause: `compute_reachability_clear` itself
> > does not test loops and returns `True` for the in-loop `:321`
> > (`plr-sema/data/derived_contracts.json:88817-88822`) — sound only because the trail check carries
> > it, which is now written down.
>
> **Why lift it at all, stated as the cost of not lifting.** Without the lift this increment adds
> **no** `WILL_FAIL` population whatsoever: `:409` and `:321` are the only two sites it newly decides
> and both are at `depth == 1`, so every new verdict would be in the `SAFE` direction and the mutant
> class (§16.11) could not exercise a single one of them. An increment that adds only `SAFE` verdicts
> and no way to fire them is an increment whose new machinery is tested in one direction. **That is the
> argument, and it is a testability argument, not a precision one.**
>
> **Why it is the riskiest clause in the document.** `WILL_FAIL` is the direction that produces a false
> positive on a clean operation; `join` propagates one to the whole operation
> (`plr-sema/src/plr_sema/verdict.py:313-323`) and `compare` scores
> `verdict == "will_fail" and outcome == "ran_ok"` as unsound
> (`plr-sema/eval/oracle_common.py:767-786`). Round 1 of increment 6 filed six blockers in this
> direction. **`D1` is a user decision (§16.15), recommended YES**, and it is named here as the first
> candidate for the adversarial pass alongside increment 6's own R1 (§16.15 Q6).

---

## 16.5 `E-ENV` resolution

Increment 6's `E-ENV` makes every `EnvRef` **½ in predicate position and ⊤ in term position,
unconditionally, under every state, for every path, with no lookup table**
(`plr-sema/src/plr_sema/check/predicate.py:262-278` for the term half, `:646-658` for the predicate
half). Its own text names the reason: *"a rule that matched paths would be a hand-maintained surface,
which §15.8 argues this production is not."*

> **Normative (the concession, made once and made plainly).** §16.5 **is** a path-shape table, it **is**
> hand-maintained surface, and increment 6's `E-ENV` box is superseded exactly and only in this
> increment's scope. After round 1 there are **three** admitted shapes and no fourth — R-HEAD, R-ATTR
> and R-CONST — because **R-DECK is withdrawn** (C3, §16.1.3: the shape it matched does not occur in
> the contract table, and `:321` is respecified as a site rule under D6 instead). **Every path not
> matching one of the three stays ½ in predicate position and ⊤ in term position**, which is `E-ENV`
> unchanged. The registry consequence is §16.9's and is **D4**, HM-25 `declared` 9 → 10, recommended
> YES and never spent in this text.

### 16.5.1 R-HEAD — `self.head`

> **Normative.** `EnvRef(("self", "head"), None)` — `args is None`, i.e. a read and not a call —
> resolves, in **term** position, to `Seq((Lit(c₀), …, Lit(cₙ₋₁)))` where the `cᵢ` are the members of
> the observation's `head_channels`, in ascending order. **The `Seq` is declared COMPLETE** (§16.5.4).
> In **predicate** position `self.head` stays ½: a dict is not a truth value and no guard at this pin
> uses it as one.
>
> **Declines to ⊤ when:** no `obs:head_channels` member is present; or the observation's
> `backend_class` is absent (an observation must be complete to be used at all — a partial record is
> refused wholesale, so a reader cannot get a resolution from half a record).
>
> **What it does not cover.** `self.head[channel]` — subscripted — is `Opaque` by increment 6 G7's
> closed negative list and stays so. `self.head96` is not admitted. The path is `("self", "head")`
> exactly, length 2, nothing else.

> **AMENDED 260909 (spec 260909_plr-sema-move-family-increment.md §17.1.2/§17.3, T51, D7 unit 11,
> user-approved — the same shape this increment's own Q-MONO used on increment 6 G8(1)).** The sentence
> two paragraphs up — *"In predicate position `self.head` stays ½: a dict is not a truth value and no
> guard at this pin uses it as one"* — is **false in its second half**: `:2055` (the move family's
> `pick_up_resource`) uses a second dict, `self._resource_pickups`, as a truth value directly. The
> amendment is minimal and is stated as a rule, not an exception:
>
> > **A complete `Seq` decides in predicate position.** An `EnvRef` for which `_resolve_env_ref` returns
> > a **non-`Top`** `ir.Seq` **together with a `rule` whose own specification declares that `Seq`
> > complete** — today R-HEAD and, as of the move-family increment, R-ARM (`self._resource_pickups`, see
> > that increment's §17.3) — evaluates `T` iff the `Seq` is non-empty and `F` iff it is empty. An
> > `EnvRef` resolving to any other value, to `ir.Top`, or under any other rule, is ½ exactly as before.
>
> **Keyed on the RULE, not on the node.** Completeness is a property the resolution rule declares, not a
> field on `ir.Seq` itself; a clause keyed on `isinstance(value, ir.Seq)` would silently admit any future
> lower-bound-`Seq` rule, so the clause reads the `rule` string `_resolve_env_ref` already returns
> alongside the value. **`self.head`'s own predicate-position shape refusal, immediately above, is KEPT
> unchanged**: no guard at this pin reads `self.head` as a truth value, and removing a live fail-closed
> refusal that nothing needs is exactly the surface growth §9.4 exists to prevent — the refusal fires by
> SHAPE, before this amended clause is ever reached, so R-HEAD's own completeness declaration never
> actually decides anything through it at this pin.

### 16.5.2 R-ATTR — `self.backend.<attr>`

> **Normative.** `EnvRef(("self", "backend", a), None)` resolves, in term position, to `Lit(v)` where
> `v` is the observation's value for `a` **iff** `a` is a field of §16.2's record — at this pin exactly
> `num_channels`. Every other `a` resolves ⊤. In predicate position an admitted `EnvRef` of this shape
> evaluates to the Kleene truth of `Lit(v)` — `T` for a truthy constant, `F` for a falsy one — and an
> unadmitted one stays ½.
>
> **This rule decides nothing at this pin and is shipped anyway, which is a claim to check rather than
> to trust.** No guard on any of the 544 executed operations reads `self.backend.num_channels`: `:409`
> reads `self.head`, and the `range(self.backend.num_channels)` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:187-197` is a *construction* site,
> not a guard. §16.10 publishes `n_resolved_by_rule` per rule so a reader can see that R-ATTR's is
> **0** rather than take this paragraph's word for it. A non-zero count is not a failure; it is a
> number to inspect before the verdicts are accepted.
>
> > **Keeping R-ATTR is an explicit sub-note under D4, not a silent inclusion (C25, partial).** C25 is
> > right that R-ATTR's *stated* purpose in spec_version 1 — cross-checking `head_channels` against
> > `num_channels` — is a **harness** assertion and not an evaluator rule, and that a predicted-zero
> > rule inside a table costing a ceiling unit is the shape §9.4 targets. **The harness assertion moves
> > to where it belongs**: AC-16.1 now asserts `len(head_channels) == num_channels` inside the harness,
> > whether or not R-ATTR ships. **What C25 does not change is the ask.** D4 buys **one** unit for the
> > pattern *"an `EnvRef` path admitted against the observation record"*, not one per instance (§16.9's
> > own one-pattern-many-instances argument), so dropping R-ATTR reduces nothing; keeping it means the
> > next observation field needs no new rule and no new unit. **This is a presentation choice and it is
> > surfaced as one under D4** — the user may strike R-ATTR and the unit, the counters and every other
> > number in this document are unchanged either way.

### 16.5.3 R-CONST — `self.backend.<method>(…)`

> **Normative.** `EnvRef(("self", "backend", m), args)` with `args is not None` — a call — resolves,
> **independently of `args`**, to `Lit(v)` in term position and to the Kleene truth of `v` in predicate
> position, **iff** §16.3's derived surface records a `constant_return` value `v` for
> `(backend_class, m)` under the observed `backend_class`. Otherwise ⊤ / ½.
>
> **Argument-independence is the whole of the soundness argument and must be stated as such.** A method
> whose body is exactly `return <Constant>` returns that constant for **every** argument vector, so its
> value is a function of neither `args` nor of how many times it is called. That is why the rule may
> fire when the enclosing `Zip` is ⊤ (§16.1.4): the analyzer is not claiming to know the sequence, it
> is claiming the body does not read it. **An implementation that resolved `args` first and declined on
> a ⊤ argument would pass every other fixture in AC-16.5 and fail this one**, which is that
> criterion's stub-defeating half.
>
> **The MRO is not walked, and that is deliberate.** The lookup is `(backend_class, m)` exactly. A
> method inherited rather than overridden is **absent** from the observed class's row and resolves ⊤.
> Walking the MRO would require a class-hierarchy fact the production evaluator does not carry —
> increment 6 §15.16.3 R2(b) records `class_hierarchy` as `None` in production — and would silently
> widen the rule's reach at the first refactor. Fail-closed.
>
> **R-CONST additionally requires §16.3's absence rule.** A `(class, method)` row removed by C15's
> decorator/property/multi-lineno test is not in the surface at all, so R-CONST declines. Without that
> gate an AST `return True` under a non-`wraps` decorator would produce a false `SAFE` at `:514`.

> **Normative (E-INV — the evaluator invariant C7 asked for, stated as an invariant rather than as a
> clause; C7, partial, conceded on the substance).**
>
> > **A production may return a definite value with a ⊤ operand only when its value is independent of
> > that operand, and every such production is named in this box.**
>
> **The invariant holds vacuously across the whole shipped evaluator today**, which is what makes it a
> real constraint rather than a description: `_eval_is_instance` returns `None` on a non-`Ref`,
> `_eval_is` requires a `Lit` (`plr-sema/src/plr_sema/check/predicate.py:851-856`), `_eval_cmp` returns
> `None` on every membership operator and on any unresolved `Len`
> (`plr-sema/src/plr_sema/check/predicate.py:535-558`), `_maybe_setof_uniqueness` requires a `Seq` of
> hashable `Lit`s, and `_eval_alpha_existential` returns `None` unless the iterand is a concrete `Seq`
> (`plr-sema/src/plr_sema/check/predicate.py:433-456`).
>
> **This increment introduces exactly two deliberate instances, and no third is permitted without
> amending this box.** **(a) R-CONST** — its value is the method's constant return, independent of
> `args` by the shape test. **(b) Q-MONO** (§16.5.5) — `AllOf(⊤ seq, T)` is independent of the seq's
> value, which is precisely why the two decided cells are the two the empty sequence also satisfies. A
> production that returns a definite value from a ⊤ operand *without* argument-independence is unsound
> and is forbidden by this box; AC-16.5 asserts the invariant over the shipped production set.
>
> **spec_version 1's version of this argument was one clause inside Q-BIND's soundness paragraph and
> was false as written** — it claimed the refinement "only ever replaces a ½ with a definite value",
> when the shipped concrete-seq path already returns a definite value. Q-BIND is withdrawn (§16.5.5);
> the invariant is not, because **R-CONST needs it whether or not Q-BIND ships**.

### 16.5.4 The membership deciding case, reopened under all three of its conditions

Increment 6 §15.13 **deleted** the membership deciding case and recorded three explicit reopening
conditions. Each is discharged here, in order, and none is waived.

> **Normative (i) — a complete-`Seq` `Term` exists.** §16.5.1's R-HEAD produces one. **No literal
> container production is added**: `_parse_term` still has no `ast.List`/`ast.Tuple` branch and this
> increment adds none, so the only complete `Seq` reachable by any membership `Cmp` in the whole
> contract table is an `E-ENV` resolution.

> **Normative (ii) — an `ir.Seq` is a LOWER BOUND, except where this section says otherwise.** This is
> the statement increment 6 required and could not make. **A general `ir.Seq` — one resolved from
> `call.kwargs`, from a `param_defaults` entry, or from an α/β binding — is a lower bound on the
> sequence's membership and NEVER decides a `not in` to `T`.** The **one** exception is a `Seq`
> produced by an `E-ENV` rule that this section declares complete, of which there is currently exactly
> one, R-HEAD, and the completeness is a property of the *observation* — `head_channels` is the
> enumerated key set of a dict read at one instant, not an inference from how the dict was built.
>
> **The distinction lives in the evaluator, not on the wire.** `ir.Seq` gains **no field** and
> `IR_VERSION` does not move. The rule is stated at the `Cmp` node: *a membership `Cmp` decides only
> when its right operand is an `EnvRef` resolved by a rule §16.5 declares complete.* A membership
> `Cmp` whose right operand is a `Var` resolving to an `ir.Seq` is ½, **unconditionally**, exactly as
> increment 6 leaves it.

> **Normative (iii) — the population is measured and every decision is counted.**
> `n_membership_cmp` over the whole contract table is **48**
> (`outputs/plr-sema/t30_measured_260908.json:28561-28610`). §16.10 additionally publishes
> `n_membership_decided` — per site, per operation and whole-table — beside
> `n_decided_via_env_ref_shortcircuit`, and predicts it **384** (one guard, `:409`, on 384 operations)
> under R-HEAD and **0** everywhere else. A membership decision at any other site is the number to
> inspect before T46's verdicts are accepted.

> **Normative (the semantics, once all three hold).** `Cmp(t, "in", S)` where `S` is a complete `Seq`
> of `Lit`s and `t` resolves to a `Lit` is `T` iff the literal is a member, `F` otherwise;
> `Cmp(t, "not in", S)` is its exact negation. If `t` is ⊤, or `S` is not complete, or either operand
> is anything else, the result is ½. **No other comparator gains a case and `_CMP_OPS` is unchanged.**

### 16.5.5 Q-MONO — the one quantifier clause

> **Q-BIND is WITHDRAWN in full (D-G1, conceded; C8's conclusion reached by the defender's stronger
> route).** spec_version 1 specified a second clause, Q-BIND, giving `AllOf`/`AnyOf` element-wise
> binding over a concrete `Seq` via an additive `target` field on `Filtered`, `AllOf` and `AnyOf`. **It
> was dead machinery.** Its only claimed beneficiary was `:409`, and `:409` never reaches
> `_eval_allof_anyof`: it is dispatched by `_eval_cmp` to `_maybe_alpha_emptiness` and thence to
> `_eval_alpha_existential`, which **already** loops over the iterand's real items and overrides the
> bound name per element (`plr-sema/src/plr_sema/check/predicate.py:433-456`). The module docstring
> distinguishes the two paths by name (`plr-sema/src/plr_sema/check/predicate.py:402-410`). No other
> site at this pin reaches Q-BIND either. **What withdrawal removes:** ~50 LOC from T43, an additive
> field from three wire nodes, a `parse` change, a reversal of increment 6 G8(1)'s "recorded nowhere"
> sentence, and one counter. **If a later increment finds a site that needs it, that increment must
> name the site**; this one could not.
>
> **A-C13 is therefore untouched.** A name bound by a genuine `AllOf`/`AnyOf` comprehension target
> still resolves to ⊤ and is still never resolved against `call.kwargs`, exactly as increment 6 states
> and as `_resolve_var` implements (`plr-sema/src/plr_sema/check/predicate.py:434-446`). G8(1)'s
> "no node gains a field" sentence stands, unamended.

**One clause survives, it is the load-bearing novelty of §16.5, and it decides `:514`.**

> **Normative (Q-MONO — a definite body decides over a ⊤ sequence, in exactly two of four cells).**
> Let `p` be the quantifier's body evaluated with every comprehension target at ⊤. Then, for a `seq`
> that resolves to ⊤:
>
> | | `p` is `T` | `p` is `F` | `p` is ½ |
> |---|---|---|---|
> | `AllOf(seq, p)` | **`T`** | ½ | ½ |
> | `AnyOf(seq, p)` | ½ | **`F`** | ½ |
>
> **The two decided cells are the ones that are also true of the empty sequence**, which is the whole
> argument: `all(...)` over an empty sequence is `True` and `any(...)` over an empty sequence is
> `False`, so an unknown length cannot falsify either. The two ½ cells are the ones the empty sequence
> falsifies — `AllOf` over an empty ⊤ seq with an `F` body is `T`, not `F` — and they stay ½ **by
> rule**. A `seq` that resolves to a concrete `Seq` is governed by the shipped
> `_eval_allof_anyof` path unchanged (`plr-sema/src/plr_sema/check/predicate.py:909-918`); the two do
> not overlap. Q-MONO is an instance of §16.5.3's E-INV invariant and is named there.
>
> **This is the clause that decides `:514`**, and it decides it without resolving the `Zip`: `p` is
> R-CONST's `T`, the seq is ⊤, `AllOf` is `T`, `Not` is `F`, the `raise_guard` does not fire.

> **Normative (Q-MONO is an EXPLICIT AMENDMENT of increment 6 §15.2 G8(1) and §15.4 A-C3 — C6,
> conceded; spec_version 1's "preserved in both directions" was a re-reading and is withdrawn).**
> Increment 6's statement is flat and normative — *"`AllOf`/`AnyOf` over a ⊤ seq is ½, **never
> vacuously `T`**"* (`.praxia/docs/specs/260904_plr-sema-predicate-increment.md:630-634`) — and the
> shipped code says the same in a comment and in `_eval_allof_anyof`
> (`plr-sema/src/plr_sema/check/predicate.py:574-579`, `:597-600`). Q-MONO's `AllOf(⊤, T) = T`
> **overturns that sentence**, and this box says so rather than reading it away.
>
> **The amended text, which T43 writes into increment 6 itself:** *"`AllOf`/`AnyOf` over a ⊤ seq is ½
> **when the body is not definite**, and never vacuously `T` — a ⊤ seq with a ½ or oppositely-signed
> body cannot decide. When the body is definite in the direction the empty sequence also satisfies, the
> quantifier takes that value (increment 7 §16.5.5 Q-MONO)."* The shipped code comment at
> `plr-sema/src/plr_sema/check/predicate.py:574-579` is amended in the same commit.
>
> **`.praxia/docs/specs/260904_plr-sema-predicate-increment.md` is therefore in T43's file list**, on
> the precedent T48 already sets for editing an earlier increment's normative text. A normative
> sentence in an `implemented-round-2` document is not overturned by a later document's re-reading of
> it; it is overturned by an amendment, in the document that carries it, in the commit that changes the
> behaviour.

### 16.5.6 The lane asymmetry, disclosed once and for every rule

> **Normative (C24, conceded — the disclosure is general, not R-DECK's alone).** spec_version 1
> disclosed a lane asymmetry for the withdrawn R-DECK and for nothing else. **R-HEAD, R-CONST and the
> D6 site rules are equally observation-dependent, and Q-MONO is dependent on R-CONST for the one site
> it decides.** So:
>
> - **The tier-1 lane** threads `plr_observation`, so every rule can fire and `:409`/`:514` decide.
> - **The graph lane** (`lower_graph`) has no harness and no observation, so every rule declines and the
>   same program yields `UNKNOWN` where tier 1 yields `SAFE`. This is a **lane asymmetry in the verdict
>   itself**, not merely in a published count, and it is the price of an observation-conditioned rule.
>   It is honest because the verdict is a function of `env` (§16.6's claim (4)) and the graph lane's
>   `env` is empty: the two lanes are answering two different questions and the fifth `cache_key`
>   component says which.
> - **Tier 2b CAN observe, and spec_version 1 said otherwise.** `region_oracle` builds every fixture on
>   one backend — the chatterbox one, whose `can_pick_up_tip` is the constant-return case and whose head
>   is the 8-channel one — so **R-HEAD and R-CONST move tier 2b as soon as T40 threads the observation
>   into `region_oracle`, which T40's own file list says it does.** §16.11's attribution sentence is
>   corrected accordingly: the rules that could move tier 2b are **R-HEAD, R-CONST and Q-MONO**, not
>   Q-MONO alone.
>
> **The consequence is normative for T46:** any tier-2b movement must be attributed to a named rule
> before the run is accepted, and `n_resolved_by_rule` is published per lane, not only whole-table.

---

## 16.6 Q1 — the scoped joined verdict

Increment 6 §15.5 established the representation's two halves and left the third. Tier (iii) is derived
from `is_dynamic_raise` (`plr-sema/src/plr_sema/check/predicate.py:1162-1166`); it emits **one**
`Finding`, `UNKNOWN`/`guard_env_dependent`, and folds its site into `AnalysisReport.scope.excludes_sites`
(`plr-sema/src/plr_sema/check/__init__.py:409-470` collects them, `:920-955` constructs the report,
`plr-sema/src/plr_sema/verdict.py:261-275` is the `SoundnessScope` type and `:298-310` the optional
field). It also **rejected, as unsound and must-not-implement, emitting tier (iii) as `SAFE` with a
marker**, because `join` would then claim the backend did not raise — A-COMPLETES applied to the
current operation (`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:752`).

**The consequence is structural and is not negotiable: under the unchanged `join`, `pick_up_tips` can
never join to `SAFE`, even with every tier-(ii) site discharged.** Every liquid-handling operation
carries a re-raise, the re-raise emits `UNKNOWN`, and one `UNKNOWN` makes the operation `UNKNOWN`
(`plr-sema/src/plr_sema/verdict.py:313-323`). So the question Q1 asks is not *"can we get a joined
`SAFE`"* but *"what is the honest name for what the analyzer does know."*

> **Normative (the representation: a SECOND, additive report field, computed by the UNCHANGED `join`).**
> `AnalysisReport` gains one optional field beside `scope`:
>
> ```
> scope_verdict: Verdict | None = None
> ```
>
> computed as `join(tuple(f for f in findings if f.plr_site not in scope.excludes_sites))` — the
> **same** function, the **same** table, over a **sub-multiset** of the same findings. `verdict` is
> untouched, is still `join(findings)`, and on every operation carrying a re-raise is still `UNKNOWN`.
> `scope_verdict` is `None` whenever `scope` is `None`, so **no report that never saw a tier-(iii)
> guard gains one** and every pre-increment-7 report is bit-identical.
>
> **`join` is not modified, not overloaded and not called with a flag.** It stays the one function in
> the package permitted to aggregate, its own docstring's claim stays true, and the filtering happens
> at the one call site in `_check` (`plr-sema/src/plr_sema/check/__init__.py:920-955`) where
> `excludes_sites` is already in hand. An implementation that taught `join` about scope would be the
> configuration `SoundnessScope`'s own docstring refuses.

> **Normative (wire and schema).** `schema_version` stays **1**
> (`plr-sema/src/plr_sema/verdict.py:298-310`). This is an additive optional field with a `None`
> default, which is the additive direction main spec Open decisions 3 records
> (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:3322-3326`): only **old readers** break on
> new reports, and they do not break here because they never read the field. No `IR_VERSION` bump; the
> IR is untouched.

> **Normative (what `scope_verdict == SAFE` asserts, and the four things it does not).**
>
> **It asserts:** *every PLR precondition guard this analyzer evaluated for this operation, other than
> those named in `scope.excludes_sites`, does not fire against this call, under the observation
> recorded in `env`.*
>
> **It does NOT assert:**
> 1. **that the operation completes.** A-COMPLETES is not discharged and is not implicated: the field
>    says nothing about the backend, which is exactly what `excludes_sites` names.
> 2. **that the backend accepts the call.** `:576` and its three siblings are precisely the excluded
>    sites.
> 3. **that a guard the analyzer never derived does not fire.** It cannot: a coverage gap emits an
>    `UNKNOWN` `Finding` — `guard_predicate_unparsed`, `unresolved_delegate` or `no_contract_derived` —
>    which is **inside** the sub-multiset and blocks `SAFE` under `join`'s third row. This is a property
>    of the construction, not a caveat, and it is why the field can be built from `join` at all.
> 4. **anything under a different observation.** The verdict is a function of `env`, which is the fifth
>    `cache_key` component (`plr-sema/src/plr_sema/check/ir.py:918-953`). A reader who wants the
>    unconditional claim reads `verdict`.

> **Normative (how `compare` scores it: TWO counters, neither replacing the other).**
> `oracle_common.compare` reads `st[oid]["verdict"]` and computes
> `unsound = (verdict == "safe" and outcome.startswith("raised")) or (verdict == "will_fail" and outcome == "ran_ok")`
> (`plr-sema/eval/oracle_common.py:767-786`). **That predicate, that field and that counter are
> unmodified and their definition does not change.** The static side additionally publishes
> `scoped_verdict` per operation, and `compare` additionally emits `unsound_scoped`, computed by the
> **same** predicate over `scoped_verdict` and then narrowed by §16.7's frame capture. Both counters are
> published; the gate reads both; neither is derived from the other.
>
> **The alternative — replacing `verdict` with `scoped_verdict` in the fence — is REJECTED and must not
> be implemented.** It would silently retire the only number that has been at 0 across five increments.

---

## 16.7 The fence

Increment 6 §15.5 left the tier-1 unsoundness predicate **unmodified**, deleted the draft's
`exc_class → site` narrowing outright, and moved the frame capture that would make a site-keyed
narrowing honest to this increment by name. The reason it moved rather than shipped is recorded there:
`TypeError` is raised at four PLR precondition sites **and** re-raised at `:576`, so an
exception-class-keyed narrowing excuses precisely the rows the fence exists to catch.

> **WITHDRAWN at spec_version 2 (C5, conceded, and independently reproduced by the orchestrator).**
> spec_version 1 captured `traceback.extract_tb(e.__traceback__)[-1]` and matched that one frame.
> **`extract_tb` returns frames outermost-first, so `[-1]` is the INNERMOST frame — the site where the
> exception was originally raised.** The one site F2 exists to excuse is
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:575-576`, `raise error`, a re-raise
> of an object caught at `:551-556` from the `await` at `:553`: its `__traceback__` already ends in the
> backend's own raising line, and re-raising *prepends* a `:576` entry rather than appending one. So
> `[-1]` is the backend frame and **can never equal a `PlrSite` in `excludes_sites`**. F2 as specified
> excused **nothing**, `rows_excused_by_frame` was structurally 0, and the defect was invisible only
> because spec_version 1 predicted zero `SAFE` rows — the fence would have shipped untested against the
> only case it was built for.

> **Normative (F1 — the frame capture, as a LIST).** `verify()` gains one additive result key beside
> `volume_tracking_observed` (`training/verify/verifier.py:184-200`):
>
> ```
> error_frames: a list of {"file": <str>, "lineno": <int>, "qualname": <str>}, or None
> ```
>
> set from the **whole** `traceback.extract_tb(e.__traceback__)` list — outermost first, order
> preserved — at **both** `except` handlers, the inner one that catches an operation failure and the
> outer one that catches a harness/deck failure (`training/verify/verifier.py:130-144`), and `None`
> when `error` is `None`. Still ~3 lines per handler. `error` itself, `f"{type(e).__name__}: {e}"`, is
> unchanged, and so is `exc_class`, which `run_runtime` still splits off it
> (`plr-sema/eval/oracle_common.py:415-439`).

> **Normative (F2 — the narrowing: ANY frame matches, with a stated tie-break).** A row is excused from
> `unsound_scoped` **iff all three** hold:
>
> 1. the row's `scoped_verdict` is `safe` and its `outcome` starts with `raised`;
> 2. `error_frames` is present and non-empty; and
> 3. **some** frame in `error_frames`, after normalisation, matches a `PlrSite` in that report's
>    `scope.excludes_sites`.
>
> **The tie-break, when several frames match, is normative: the OUTERMOST match decides**, i.e. the
> earliest in `error_frames`. That is the re-raise — the PLR-layer statement that propagated the
> backend's exception — and it is the frame the scope statement is about. An innermost-wins rule would
> re-introduce exactly C5's defect one level down.
>
> **Everything else is counted.** In particular a `scoped_verdict == "safe"` row **none** of whose
> frames is an excluded site — i.e. one that raised at a PLR **precondition** — is counted as unsound,
> and **that is the failure this increment introduces for the first time.** No increment before this
> one could produce it: increments 1–5 could not reach a joined `SAFE` at all and increment 6 §15.5
> proved it structurally unreachable. It is named here so a non-zero `unsound_scoped` at T46 is read as
> this document's own prediction failing, not as an instrument fault.
>
> **`exc_class` appears nowhere in the comparison path**, exactly as increment 6 §15.10 requires and
> for the same reason. The narrowing keys on the **frames**, which are facts about where the exception
> was raised, not on the class, which is not.

> **Normative (F2a — the two identities the match rests on, through ONE helper; C20, conceded).**
> Frame-to-site matching compares `(file, lineno)`. Two identities carry it and **both are stated
> normatively rather than assumed**:
>
> 1. **`PlrSite.lineno` is the first line of the raising statement**, which is what `tb_lineno` — and
>    therefore `extract_tb` — reports for that frame. The shipped site strings are the submodule path,
>    then the lineno, then the qualname, joined by colons, as the ledger's own cluster keys show at
>    `outputs/plr-sema/unknown_ledger_260909_after.json:177-188`.
> 2. **The frame's `file` is a runtime `__file__`**, which equals the submodule-relative path the sites
>    use *only* when PLR resolves to `external/pylabrobot/`. Under an installed copy it does not.
>
> **One normalisation helper is applied to both sides** — the frame's path and the `PlrSite`'s — before
> comparison: resolve, then re-root onto the PLR package root and re-prefix with the submodule path.
> Neither side is normalised in only one place. **AC-16.8 asserts a match against a real `PlrSite`
> string read from the shipped table, never against a hand-written tuple**, which is what makes the
> two identities checkable rather than believed.

> **Normative (F3 — the unscoped fence is untouched, and its untouchedness is asserted rather than
> assumed).** `unsound` stays exactly `plr-sema/eval/oracle_common.py:1086-1088`, over `verdict`, with no
> narrowing, no excuse and no frame test. `rows_excused_by_scope` — increment 6's pure annotation,
> measured **0** at T36 (`outputs/plr-sema/oracle_replay_260909_inc6.json:2-21`) — keeps its definition
> and gains a sibling, `rows_excused_by_frame`, for F2's own count. AC-16.8 asserts that the two
> unscoped numbers are byte-identical to the `260909_inc6` run.

> **Normative (F4 — tier 2b parity).** `region_oracle._run_fixture_execution` gains the identical
> capture inside its own `try`, and its region comparison gains the identical narrowing. Increment 5
> §14.6 records tier 2b's execution-order asymmetry as a live hazard — the executed side runs first and
> a process-global leaks — so a fence that narrowed on tier 1 and not on tier 2b would make the two
> lanes incomparable at exactly the point the comparison matters.

---

## 16.8 Reasons

> **Normative: `REASON_VOCABULARY` does NOT change. It stays at 12 of 12, HM-14's `declared` stays 12,
> and no thirteenth member is proposed.** The vocabulary is
> `plr-sema/src/plr_sema/verdict.py:147-199` and HM-14 is `REASON_VOCABULARY`'s own registry row
> (`plr-sema/src/plr_sema/_hand_maintained.py:648-667`), `CAPPED` at `declared=12` with **zero
> headroom** after increment 6 spent it.
>
> **Every give-up point this increment adds folds into an existing member, mechanically:**
>
> | new give-up point | member | why it is that member and not a new one |
> |---|---|---|
> | no observation present | `guard_env_dependent` | ≥ 1 free name resolves to state outside the call — the member's **first** clause, verbatim |
> | an `EnvRef` path §16.5 does not admit | `guard_env_dependent` | same clause; the shape is recognised and the environment is not read |
> | `caller_args` absent or partial at `depth == 1` | `guard_env_dependent` | the member already covers "the guard's reachability is not established — `depth >= 1`", and it equally covers a name that does not resolve |
> | a membership `Cmp` over a non-complete `Seq` | `guard_env_dependent` | the operand resolved; the *completeness* is the missing environment fact |
> | a quantifier over a ⊤ seq with a ½ body | whatever §15.7's ordered procedure already assigns | unchanged; this increment adds no clause to that procedure |
>
> **§15.7's ordered reason procedure is unchanged in every clause and in its order**: `contains_opaque`
> ⇒ `guard_predicate_unparsed`; else an operand of this call is ⊤ ⇒ `guard_operand_unknown`; else
> `contains_env_ref` and still undecided ⇒ `guard_env_dependent`; else the residual rules
> (`plr-sema/src/plr_sema/check/predicate.py:666-679` is the shipped operand test the second clause
> reads). **The gate's two zero-conditions are relaxed by nothing in this increment**, and §16.10
> republishes both counts so a reader can check rather than trust.

> **Normative (the one thing that would need a thirteenth member, named so it is a decision and not a
> discovery).** If a future increment wants to distinguish *"the observation was absent"* from *"the
> observation was present and the path is not admitted"*, that is a thirteenth reason and it is the cap
> conversation. This increment deliberately does **not** want that distinction: §16.10 publishes
> `n_resolved_by_rule` and `n_declined_by_rule` per rule, which carries the same information as a
> measurement without spending a wire slot on it. That is the trade, stated so it can be disputed.

---

## 16.9 Registry

**Retired rows: zero. `REASON_VOCABULARY` members: zero.** HM-24 stays at `declared` 3 and HM-14 stays
at `declared` 12 in every branch. **New rows: zero under D6 declined, ONE under D6 taken** — which is
the arithmetic round 1 changed, and it is the difference between a ceiling spend and a cap
conversation.

- **D6 declined.** `live_rows()` (`plr-sema/src/plr_sema/_hand_maintained.py:1293-1297`) is **24**
  against `BUDGET_CAP = 24` (`plr-sema/src/plr_sema/_hand_maintained.py:43`) before and after;
  headroom **0**, unchanged. One per-row ceiling unit, HM-25 `declared` 9 → 10.
- **D6 taken.** `live_rows()` **24 → 25** and `BUDGET_CAP` **24 → 25**, plus the same HM-25 unit. The
  cap has been re-baselined exactly once, at T9, and §9.4 forbids re-baselining for growth alone — so
  this is a decision that needs an argument, and §16.9's D6 box is that argument.

> **Normative (the ONE proposed spend, and it is the user's: HM-25 `declared` 9 → 10 — `D4`).**
> §16.5's three path-shape rules — R-HEAD, R-ATTR, R-CONST — are a **table of PLR path shapes**,
> which is precisely the thing increment 6 §15.4's `E-ENV` box forbade *"in this increment"* on the
> ground that it would be hand-maintained surface. It is. The row is **HM-25**, whose `what` already
> books `EnvRef` itself along with `Zip`, the membership comparators, α, β, P3a, P7, P8 and P9
> (`plr-sema/src/plr_sema/_hand_maintained.py:933-1011`), and whose `breaks_when` already records
> *"Fails LOUDLY here (unlike HM-24)"* with the published-count criterion this increment's §16.10
> satisfies. **One entry, one further ceiling unit, no second row, no cap conversation.**
>
> **Why one unit and not three.** The three rules are one pattern with three instances — *"an `EnvRef`
> path admitted against the observation record"* — in exactly the sense that P3a is one pattern with
> one instance and α is one pattern with three. Booking three would inflate the row to make the
> arithmetic look conservative, which is the mirror image of the gaming §9.4 forbids. **This is also
> why R-DECK's withdrawal (C3) does not reduce the ask and why C25's proposal to drop R-ATTR would not
> either**: the unit buys the pattern, not the instance count (§16.5.2's sub-note).
>
> **The measure must move with the `what`, on increment 6 A-C6's own precedent.** `_measure_hm25`
> measures HM-25 by **importing the symbols that implement its patterns**, so it fails loudly if any is
> deleted. Naming the path-shape table in the `what` without adding a measured symbol would leave a
> live pattern the measure cannot see — HM-24's *silent* criterion, which is the failure mode this row
> is chosen to avoid. **Normative for T43's registry spend: `_measure_hm25` must additionally import
> the path-rule symbol.** And the same contingency increment 6 wrote applies verbatim: **if the
> measured count would exceed 10, T43 STOPS and surfaces a further spend to the user rather than
> raising `declared` on its own authority.**

> **Normative (three things that cost NOTHING, each argued rather than asserted).**
>
> 1. **§16.3's derived backend surface.** An AST shape test over PLR's own recorded surface, keyed on
>    the derive package's existing function index, introducing no literal (§16.3's own box). Same class
>    as `is_dynamic_raise` and `reachability_clear`.
> 2. **§16.4's argument map.** A shape test over `ast.Call`/`ast.arguments`, fail-closed on every
>    unrecognised shape, adopting P9's two existing restrictions rather than inventing any. It is a
>    Python-language construct, which is verbatim increment 5 §14.11's accepted argument for B2 and P1c
>    and increment 6 §15.8's reason 3 for α and β.
> 3. **§16.6's `scope_verdict` and §16.7's frame capture.** A filter over an existing field and a
>    stdlib call. No pattern, no table, no literal.
>
> **Each is stated so a reviewer can break it.** The strongest available objection is against (2): P9
> is itself booked on HM-25, so the argument map is arguably the same pattern family. The reply is that
> P9 books a **channel-argument** shape — *"a keyword argument at a `self.<delegate>(...)` call site
> holding an int-constant display"* — i.e. a shape recognised for its *content*, whereas the argument
> map recognises no content at all: it maps positions to parameters and refuses everything else. If the
> round rejects that distinction, the disposition is a **second** unit on the same row and the ask
> becomes 9 → 11; it is not a new row either way. **Round 1 did not reject it**, and (1) and (3)
> likewise survived; what round 1 added is a fourth item that costs a great deal, below.

> **Normative (the SECOND spend, and it is a new ROW rather than a unit: `D6` — new at spec_version 2).**
> The site rules §16.1.1 and §16.1.3 specify are **not** HM-25's kind and must not be filed there. Every
> entry on HM-24 and HM-25 is keyed on a **shape** — a syntactic pattern over how PLR is written — and
> `why_not_derived` says so in those words
> (`plr-sema/src/plr_sema/_hand_maintained.py:976-983`). A site rule is keyed on a PLR **qualname** and
> on that function's own local or parameter names; **nothing in the registry is keyed on a PLR qualname
> today.** It is a hand-written semantic model of one named function body, which is §8's class.
>
> **Consequences, each a real cost:** **(a)** one **new registry row**, taking `live_rows()` 24 → 25
> against a `BUDGET_CAP` the user must raise to 25 — a **cap conversation**, not a ceiling spend;
> **(b)** the loud half cannot be `_measure_hm25`'s import-the-symbol measure, which sees only deletion
> of the rule and not PLR renaming `vars_keyword` or `resources`, so it must be a **published count** —
> `n_check_args_decided` asserted 544 and `n_assert_resources_decided` asserted 288; **(c)** §16.3's
> absence rule becomes a soundness precondition for both rules, because an AST-derived
> `params`/`has_var_keyword` for a decorated definition does not describe the object
> `inspect.signature` sees at runtime.
>
> **One row, not two.** T48 and T49 share it: whichever lands first adds it, the second asserts it is
> present. Filing them separately would double a cap conversation for one concession.
>
> **This is D6 (§16.15), recommended YES, and it is never spent in this text.** Under D6 declined, this
> section's arithmetic is exactly what it was at spec_version 1: `live_rows()` 24, `BUDGET_CAP` 24,
> one ceiling unit on HM-25.

---

## 16.10 Measured sets and the gate

### 16.10.1 What T46 publishes

> **Normative.** The measured report publishes, over the frozen benchmark and the regenerated contract
> table:
>
> 1. **Per `E-ENV` rule** (R-HEAD, R-ATTR, R-CONST) and **per lane** (tier 1, tier 2b):
>    `n_resolved_by_rule` and `n_declined_by_rule`, whole-table and per executed operation. **This is
>    the block that makes §16.5's reach inspectable**, and it is the analogue of increment 6 block
>    (6)'s `n_env_ref_refused_plr_layer`: a reader who suspects a rule is a sink for arbitrary paths
>    reads its own counts rather than this document. **Plus `n_quantifier_decided_by_qmono`** — per
>    site and whole-table, predicted **223** at `:514` and **0** everywhere else (C21, conceded).
>    Q-MONO is a general clause over *every* `AllOf`/`AnyOf` with a ⊤ seq and a definite body, so
>    `n_resolved_by_rule[R-CONST]` measures R-CONST and not it; the one clause this document calls its
>    load-bearing novelty must have a counter of its own. **No Q-BIND counter is published, because
>    Q-BIND is withdrawn** (§16.5.5). Under D6 the two site rules publish `n_check_args_decided`
>    (predicted 544, and it is the loud half of D5b's registry argument) and `n_assert_resources_decided`
>    (predicted 288).
> 2. **`n_membership_decided`**, per site and whole-table, with the site list, discharging §16.5.4's
>    reopening condition (iii).
> 3. **The argument map's complete measured selection**: every `(K, D)` pair mapped, its call site's
>    `lineno`, the parameter→`Term` pairs, and — separately — the count of `(K, D)` pairs **refused**,
>    broken down by which of M1's six conditions refused it. Plus `name_coincidence_exposure_count` at
>    `depth == 1`, asserted **0** (§16.4's M2 box).
> 4. **§16.3's surface**: the number of `(class, method)` rows, the number with `constant_return`, and
>    the per-method breakdown for `can_pick_up_tip` against this document's predicted **2 of 8**.
> 5. **Per executed operation**: `verdict`, `scope_verdict`, the residual reason set, and the list of
>    non-excluded sites carrying an `UNKNOWN`. **The gate number is computable from this block alone,
>    without reading this document.**
> 6. **The fence**: `unsound` (unscoped, unmodified), `unsound_scoped`, `rows_excused_by_scope`,
>    `rows_excused_by_frame`, and — for every excused row — the captured frame, so an excuse can be
>    audited one row at a time.
> 7. **The after-ledger delta** against `outputs/plr-sema/unknown_ledger_260909_after.json`, on
>    `n_findings_by_reason`, `n_clusters` and `per_op_reason_set_histogram`, with `consistency.ok` true.
>    **Plus `scope_verdict` itself, threaded into `plr-sema/eval/unknown_ledger.py` and published per
>    operation beside the reason set (D-G4, conceded).** §16.0.1's normative box makes `scope_verdict`
>    per operation *"the only number in this document allowed to decide GO"*, and spec_version 1 put it
>    in the replay report alone — so the ledger, the instrument this whole increment is written against,
>    could not audit its own gate. It can now.
> 8. **`t30_measure`'s prediction role, re-run or retired (D-G5, conceded).** §16.10.3's
>    `n_membership_cmp = 48` is read off `outputs/plr-sema/t30_measured_260908.json`, and
>    `classify_guard_structural` is a **structural predictor of what `E-CALL` will decide** — over
>    exactly the classes this increment changes the meaning of (`AllOf`/`AnyOf` under Q-MONO,
>    membership under §16.5.4, and every `EnvRef` under §16.5). **T46 re-runs it and republishes**, so
>    the prediction instrument and the measurement instrument continue to be comparable; increment 6
>    §15.10 already fixes its status as a prediction instrument only, and a stale predictor is worse
>    than no predictor because a divergence becomes unattributable. If T46 cannot re-run it, §16.16
>    records the prediction role as **retired for the `AllOf`/`AnyOf`, `Filtered`-emptiness and
>    membership classes** and says so in the report rather than leaving the 48 to be read as current.

### 16.10.2 The gate

> **Normative (the conjunction — stated because spec_version 1 never did; D-G2, C2).** `pick_up_tips`
> reaches `scope_verdict == SAFE` **iff all four** hold:
>
> > **D6 is taken** (which supplies *both* site rules: `:375`/`:383` under D5b **and** `:321` under the
> > repaired D2) **AND D4 is taken** (which supplies §16.5's path table, hence `:409` and `:514`)
> > **AND the observation record ships** (T40) **AND the argument map ships** (T42).
>
> **Neither site rule alone is enough**, and that is the sentence spec_version 1 was missing. With
> `:576` excluded and `:409`/`:514` flipped, `scope_verdict` still joins `:375`, `:383` **and** `:321`;
> discharging `_check_args` alone leaves `:321`, and discharging `:321` alone leaves `_check_args`. This
> is why they are **one** user question (D6) and not two.

> **Normative (the GO condition, and the NO-GO-side criterion the increment can fail on its own terms).**
>
> > **GO iff ≥ 1 executed real operation reaches `scope_verdict == SAFE`, with tier-1 `unsound == 0`
> > under the unmodified predicate AND `unsound_scoped == 0` under §16.7's narrowing.**
>
> **If D6 is DECLINED, that clause is unreachable by construction and the increment is measured against
> a conjunction it can genuinely fail (C2, conceded):**
>
> > **`n_findings_decided >= 2,009` AND `unsound == 0` AND `unsound_scoped == 0` AND `scope_verdict`
> > computed and published per operation, with the `:375`/`:383`/`:321` obstruction REPRODUCED BY
> > MEASUREMENT** — i.e. §16.10.1 block (5)'s per-operation list of non-excluded `UNKNOWN` sites
> > contains exactly those three on every one of the 223 `pick_up_tips` operations, and nothing else.
>
> **Both halves are real tests and neither is a coin already called.** The GO clause is falsifiable by
> one number and, under D6, winnable by one number. The NO-GO-side clause fails if the floor is missed,
> if either fence counter moves off zero, if `scope_verdict` is not published, **or** if the residual is
> anything other than the three predicted sites — which is the case where this document's own site
> analysis is wrong.
>
> NO-GO otherwise: publish the counts and the structural reason in §16.16, keep everything landed (it
> is a strict information gain on the contract table and on the ledger either way), and bring the
> decision to the user.
>
> **Why the gate is not stated over reasons, as increment 6's was.** Increment 6's gate had to be
> stated over reasons because it could not reach a joined verdict at all and needed a proxy that was
> not self-satisfying. This increment ships the joined field, so the gate is stated over the field
> itself — which is stronger, because it cannot be met by a relabelling. **Every reason count is still
> published**, and §16.10.3's per-site table is what makes a NO-GO diagnosable rather than merely
> recorded.

### 16.10.3 The prediction, per site and per method

> **Normative (this table is a PREDICTION for T46 to falsify, cell by cell, and a divergence in either
> direction is recorded rather than absorbed.)** Counts are the ledger's frozen population.

**`pick_up_tips` — the gate candidate, 223 operations:**

| site | today | D6 DECLINED | D6 TAKEN | by what |
|---|---|---|---|---|
| `:498` | `SAFE` on **216** of 223 | unchanged, 216 | unchanged, 216 | O1-conditional; the 7 are increment 6's own disclosed residual |
| `:502` | `SAFE` 223 | unchanged | unchanged | G4 + `channels_for_call` |
| `:522` | `SAFE` 223 | unchanged | unchanged | G2 + β + `E-CALL(β)` |
| `:535` | decided 223 | unchanged | unchanged | the tip family |
| `:409` | ½ 223 | **`SAFE` 223** | **`SAFE` 223** | §16.4 M1 + R-HEAD + §16.5.4 |
| `:514` | ½ 223 | **`SAFE` 223** | **`SAFE` 223** | §16.3 `constant_return` + R-CONST + Q-MONO |
| `:375` | ½ 223 | ½ 223 | **`SAFE` 223** | the D5b site rule: `params ⊆ default` ⇒ `Len(missing) = 0` |
| `:383` | ½ 223 | ½ 223 | **`SAFE` 223** | the D5b site rule: `has_var_keyword` ⇒ the recorded scope entry is `F` ⇒ E-SCOPE |
| `:321` | ½ 223 | ½ 223 | **`SAFE` 223** | the repaired D2 site rule + A-DECK-OBJECT |
| `:576` | `UNKNOWN` + `excludes_sites` | unchanged | unchanged | tier (iii), derived |
| **`scope_verdict`** | — | **`UNKNOWN` on all 223** | **`SAFE` on ≥ 167** — see the bound below | the three site rules together |

> **The `SAFE`-side bound is stated as an inequality, not as 223, and the reason is published data.**
> `scope_verdict == SAFE` requires **every** non-excluded finding on the operation to be `SAFE`, and
> `pick_up_tips` carries decided sites the per-site counts do not all put at 223:
> `plr-sema/eval/oracle_replay.py`'s own published breakdown gives `:502`, `:522`, `:535` and
> `TipTracker.add_tip` at 223 each, `:498` at **216**, and `TipTracker.get_tip` at **167**
> (`outputs/plr-sema/oracle_replay_260909_inc6.json:109-125`). Whether the shortfalls are ops on which
> the guard is *undecided* or ops on which the guard is *absent* is not determinable from that report,
> so the honest prediction is **≥ 167 and ≤ 223**, and **T46 publishes the exact per-operation count**.
> A cell of 223 here would be a number this document cannot derive.

**Every other method, so the round can falsify the whole table and not one row of it. No method other
than `pick_up_tips` reaches `scope_verdict == SAFE` under EITHER branch:**

| method | ops | which of this increment's sites it carries | `scope_verdict` (both branches) | what still blocks it under D6 TAKEN |
|---|---|---|---|---|
| `aspirate` | 77 | `:409` (via `self._make_sure_channels_exist(use_channels)` at `:980`), `:375`, `:383` | `UNKNOWN` | `:116` (`guard_predicate_unparsed`) and the unseeded volume cell |
| `dispense` | 40 | `:375`, `:383` | `UNKNOWN` | `:116`; volume |
| `drop_tips` | 31 | `:409` (via `:665`), `:321`, `:375`, `:383` | `UNKNOWN` | `:657` and `:666` (increment 6 §15.1.2) |
| `discard_tips` | 34 | `:409`, `:321`, `:375`, `:383` | `UNKNOWN` | `:822`'s rebinding; a `guard_operand_unknown` residual |
| `transfer` | 19 | `:409` (inherited), `:375`, `:383` | `UNKNOWN` | `:990`/`:1202` need γ; `:116` |
| `stamp` | 27 | `:375`, `:383` | `UNKNOWN` | branch-bound `containers` |
| `move_*` | 93 | `:375`, `:383` | `UNKNOWN` | `unresolved_delegate` — deferred row (e), out of scope by construction |

> **A qualification this document owes on `:409`'s reach, stated rather than buried.** `:409` clears on
> `pick_up_tips`'s 223 with high confidence: `channels_for_call` is measured non-`None` on every
> executed `pick_up_tips` operation and `:502`'s dependence on the same resolution is measured decided
> at 223/223 (`outputs/plr-sema/oracle_replay_260909_inc6.json:109-125`). On the other **161** — 77
> `aspirate`, 34 `discard_tips`, 31 `drop_tips`, 19 `transfer` — it clears only if the caller-side
> `use_channels` resolves in each of those methods, which no number anywhere covers and which
> `E-CALL(5)`'s parameter-rebinding clause may block (`aspirate` rebinds `use_channels` at `:958`,
> above its delegate call at `:980`). **The prediction is therefore 223 certain and up to 384**, and
> T46 must publish the per-method count. A hedged cell is unfalsifiable, so this one is split into an
> exact claim and a named uncertainty rather than written as a range.

**Aggregate predictions, each a single number T46 either matches or does not — and each split into a
223-CERTAIN half and an UP-TO-384 half, because `:409`'s reach beyond `pick_up_tips` is exactly the
number this document declines to claim (C4, conceded).**

- **`n_findings_decided`, D6 declined.** Today **1,563**
  (`outputs/plr-sema/oracle_replay_260909_inc6.json:109-125`). **223-certain: 1,563 + 223 (`:409` on
  `pick_up_tips`) + 223 (`:514`) = 2,009.** Up-to-384: **2,170**, if `:409` also clears on the other
  161. **AC-16.9 gates at ≥ 2,009 and publishes 2,170 as the target.** spec_version 1 gated at 2,170,
  which assumed the very 384 the paragraph three lines above it declined to claim — a
  prediction-holding run would have scored 2,009 and failed its own criterion.
- **`n_findings_decided`, D6 taken.** Add `:375` 544, `:383` 544 and `:321` 288: **223-certain 3,385**,
  up-to-384 **3,546**. The gate stays at ≥ 2,009; the extra is published, not gated.
- **`guard_env_dependent` 4,138 →** 223-certain **≈ 3,692**, up-to-384 **≈ 3,531** (D6 declined);
  223-certain **≈ 2,316**, up-to-384 **≈ 2,155** (D6 taken).
- **`n_clusters` 53 →** **53, unchanged**, under the 223-certain half of either branch. A cluster is
  keyed on `(reason, site, condition)` and a *partially* cleared site is still a cluster: `:409` clears
  on 223 of 384 and `:321` on 223 of 288 in that half, so neither disappears. Clusters fall to **51**
  only if `:409` clears on all 384 **and** `:514` clears on all 223; `:375`/`:383`/`:321` clearing
  everywhere would take it to **48**. spec_version 1's `51` and `50` carried the same hidden assumption
  C4 found in the floor and are withdrawn.
- **`guard_predicate_unparsed` 495 → 495, unchanged** in every branch — this increment adds no
  production to the grammar and touches no coverage gap. **A movement in this number means something
  unintended happened.**
- **`guard_operand_unknown` 144 → 144, unchanged** — §16.4's `origin` box is the argument, and this is
  its cheapest falsification.
- **`unknown_rate` 1.0 → 1.0** in both branches: the unscoped `verdict` is `UNKNOWN` on every operation
  carrying a re-raise, which is every liquid-handling operation, and nothing here changes that.
  `scope_verdict == SAFE` on **0** operations under D6 declined and on **≥ 167** under D6 taken.

### 16.10.4 The anti-gaming counter

> **Normative (which productions and observations flip which sites — the falsification map).** The gate
> is stated over a field this increment introduces, so the burden is on this box.
>
> | mechanism | flips | does NOT flip | published counter |
> |---|---|---|---|
> | the observation alone (§16.2) | nothing | everything | `n_resolved_by_rule` all zero without §16.5 |
> | R-HEAD + the membership case (§16.5.4) | `:409` only | `:321`, `:375`, `:383`, `:514`, `:116`, `:657`, `:2030` | `n_membership_decided`, predicted at exactly one site |
> | R-CONST + Q-MONO | `:514` only | every guard whose body is not a constant-return backend method | `n_resolved_by_rule[R-CONST]` **and** `n_quantifier_decided_by_qmono`, both predicted 223 |
> | the argument map alone (§16.4) | nothing by itself | — it binds names; it decides no guard | the refusal breakdown by M1 condition |
> | the D5b site rules (**D6**) | `:375` and `:383` only | every other guard in every other PLR function | `n_check_args_decided`, predicted 544 |
> | the `:321` site rule + A-DECK-OBJECT (**D6**) | `:321` only | everything else | `n_assert_resources_decided`, predicted 288 |
> | `scope_verdict` (§16.6) | **no site at all** | — it is a `join` over a subset | `scope_verdict` per op |
>
> **Every site rule under D6 is keyed on ONE `(qualname, lineno)` pair and decides that guard and no
> other.** That is the anti-gaming property the site-rule class buys in exchange for its registry cost:
> its reach is a published integer per rule, not a shape whose population has to be surveyed.
>
> **The two cheap ways to pass this gate, both named and both REFUSED.**
>
> 1. **Put `:375` and `:383` into `excludes_sites`.** They are tier (ii) by §15.1's definition — a
>    property of the backend's signature — so a reader could argue they belong in a scope that already
>    excludes backend outcomes. **Refused.** `excludes_sites` is **derived**, from
>    `guard.is_dynamic_raise` and from nothing else
>    (`plr-sema/src/plr_sema/check/predicate.py:796-800`); it is not a site list and admitting one is
>    the configuration increment 6 §15.1's derived-tier box exists to prevent. Both guards raise
>    `TypeError` **from the PLR layer**, on real programs, for a real reason, and a scope that excluded
>    them would make `scope_verdict == SAFE` mean strictly less than "no PLR precondition fires" while
>    still being reported under that name. **This is the move that would have bought the headline, and
>    the reason it is refused is not cost.**
> 2. **Compute `scope_verdict` by anything other than the unchanged `join`.** Refused by §16.6's own
>    normative box. A `scope_verdict` that treated an `UNKNOWN` as absorbing-except-when-convenient
>    would pass this gate on the first operation that reached it.
>
> **The cheapest falsifications of this document, one per branch.** Under **D6 declined**:
> `scope_verdict == SAFE` on ≥ 1 operation, or a per-operation residual containing anything other than
> `:375`, `:383` and `:321` — either falsifies §16.1's site analysis. Under **D6 taken**:
> `scope_verdict == UNKNOWN` on all 223 `pick_up_tips` operations, which falsifies §16.1.1's
> arithmetic, §16.1.3's `resources`-binds-cleanly claim, or both. **Note that spec_version 1's stated
> cheapest falsification — a `SAFE` without D5 — was reachable inside its own budget**, which is C2's
> objection and the reason the gate is now a conjunction rather than a pre-called coin.

---

## 16.11 The oracle and the mutants

**Tier 1 re-run is the gate, under the UNMODIFIED unsoundness predicate.** Baseline, from the T36 run
this document is written against: `rows_executed` **343** over `operations_executed` **548**,
`unsound` **0**, `crosscheck_joined` **191/191** at agreement 1.0, `rows_setup_error` **0**,
`n_findings_decided` **1,563**, `rows_excused_by_scope` **0**
(`outputs/plr-sema/oracle_replay_260909_inc6.json:2-21`). Every one of those numbers is re-measured and
any movement is attributed before the run is accepted.

**Non-regression, exact, from the same close:** m1 199/199, m2 289/289, v1 67/67 at the raised index,
tier 2b 16 fixtures with `region_unsound` 0 / `region_will_fail_fired` 7 / `volume_will_fail_fired` 3.

> **Normative (which rules can move tier 2b — CORRECTED at spec_version 2; C24, conceded).**
> spec_version 1 named Q-MONO as the only candidate. That was wrong, and the reason is that **tier 2b
> can observe**: `region_oracle` builds every fixture on one backend, the chatterbox one, whose
> `can_pick_up_tip` is the constant-return case
> (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:241-242`) and whose head is
> the 8-channel one (`external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:42-47`).
> T40's own file list threads the observation into `region_oracle`, so **R-HEAD, R-CONST and Q-MONO can
> all move tier 2b**, and under D6 the two site rules can as well. Every movement must be attributed to
> a named rule, using §16.10.1 block (1)'s per-lane counters, before the run is accepted.

> **Normative (p2 — the depth-1 `WILL_FAIL` mutant class, and it has exactly ONE mutator).**
> `plr-sema/eval/predicate_mutants.py` — the p1 producer, whose three mutators measured
> 288/288, 16/16 and 0/288 with **0 unsound** in every class at T36
> (`outputs/plr-sema/predicate_mutants_260909_inc6.json:2-58`) — is extended by:
>
> **(a) `p2a_channel_out_of_range`.** Mutate a planned `pick_up_tips` call's `use_channels` to contain
> an index `>= ` the observed `num_channels`. PLR raises `ValueError` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:405-409`; the static side must emit
> `WILL_FAIL` **at the raised index**.
>
> **Floor, with a denominator (C23, conceded).** p2a publishes `n_achieved_will_fail_at_raised_index`
> **over `n_ran`**, in exactly p1's shape — p1's own published triples are 288/288, 16/16 and 0/288
> (`outputs/plr-sema/predicate_mutants_260909_inc6.json:2-58`) — together with
> `n_construction_skipped` and `n_error`. **The floor is `achieved == attempted` with `attempted >= 200`
> and 0 unsound in both directions**, not a bare "≥ 1". A bare floor of 1 is satisfied by 1/300, which
> is the same defect one level up from the one increment 6 §15.16.3 recorded when it refused to lower a
> floor to match a measurement.
>
> **This is the only mutator that exercises D1's lift, and that is exactly why it is the class's
> point.** `:409` is at `depth == 1`; without D1 it can never emit `WILL_FAIL` and (a) reports 0
> achieved. **If D1 is declined, this class is withdrawn together with its acceptance criterion rather
> than left to report 0** — increment 6 §15.16.3's own lesson, that a class which can only ever report
> 0 is a publication and not a gate.

> **Normative (a second mutator on `:321` is NOT constructible, and the reason is a fact about PLR).**
> The obvious dual — pass a resource that is not on the deck — does **not** make `:321` fire. It makes
> `Resource.get_resource` raise `ResourceNotFoundError` at
> `external/pylabrobot/pylabrobot/resources/resource.py:566-589`, one line earlier and at a site the
> contract table carries no guard for. Constructing a resource that *is* on the deck by name and
> unequal by `Resource.__eq__` requires building a second object with matching name and mismatched
> geometry, which the mutator API (which mutates a planned call's kwargs) cannot express.
> **Consequence, stated as a property of the site: `:321` can only ever produce `SAFE`**, and its `T`
> branch is unreachable by construction (§16.1.3's site-rule box). **The honest reading of that, after
> C18:** no available *mutator* can falsify A-DECK-OBJECT, so the tier-1 fence's 288 clean operations
> check the assumption **on the corpus** and not in general. AC-16.13 therefore requires one
> **hand-built** duplicate-name fixture, constructed directly rather than through the kwarg-mutator API
> — a second `Resource` carrying a name already on the deck and a mismatched geometry — so the
> assumption has one adversarial witness. That is a real argument **for** D2, but it is a weaker one
> than spec_version 1 made, and the user is told which.

---

## 16.12 Acceptance criteria

- **AC-16.1 (the observation record, its closure, its fail-closed defaults, and the T40-scoped
  identity).** `verify()` returns `plr_observation` with exactly the four fields of §16.2.1 and no
  others, all read at the **one** capture point after `await setup.machine.setup()`; a fixture asserts
  `head_channels` is non-empty there and that reading it before `machine.setup()` returns the empty
  dict, which is the placement half. **Three fail-closed fixtures, one per path:** the deck-build early
  return yields `plr_observation is None`; a field whose read raises yields `None` for the **whole**
  record, not a partial one; and a `None` record contributes no `obs:` member. The harness asserts
  `len(head_channels) == num_channels`, which is where that cross-check belongs (§16.5.2's R-ATTR
  sub-note). `env` carries the observation's `obs:` members under §16.2.3's JSON encoding, with a
  fixture over a **resource name containing both `,` and `=`** asserting that two distinct observations
  produce two distinct `env` sets, and a fixture asserting `head_channels` sorts **numerically** so a
  16-channel head encodes as `[0,1,2,…]` and not as `0,1,10,11,…`. **The stub-defeating half is the
  identity assertion, and it is scoped explicitly to the T40 state**: at T40, with `env` empty,
  `check_ir` over the shipped fixtures produces findings **byte-identical** to the pre-increment-7 run,
  asserted as an equality over the whole finding tuple and not as a count. **The criterion does not
  assert this after T42 or T43**, where the argument map and D1's lift change behaviour with `env`
  empty — spec_version 1 stated it as a standing invariant and it is not one.
- **AC-16.2 (the derived backend surface, measured and keyed on PLR's own index).**
  `plr-sema/data/derived_contracts.json` gains the `backend_surface` top-level key; its complete
  measured selection is published, including the whole-tree count of `can_pick_up_tip` definitions and
  the count of those with a `constant_return`, asserted **2** at this pin with the two files named. A
  grep over the derive package asserts the literal string `LiquidHandlerBackend` occurs **nowhere** in
  the surface's derivation — that is the no-hand-typed-fact claim of §16.3 made checkable, and it is
  this criterion's stub-defeating half. Four shape fixtures, one apiece: a single `return True` body is
  admitted; a **docstring-plus-return** body is **not**; a two-statement body is not; a `return <Name>`
  body is not. **Plus §16.3's absence rule, three fixtures (C15):** a `@some_wrapper`-decorated body
  that is otherwise a perfect `return True` yields an **absent** row, asserted positively — that is
  this criterion's second stub-defeating half, because an implementation that reads the AST and skips
  the decorator test passes every shape fixture and fails this one; a `property` yields an absent row;
  and a qualname defined at two linenos yields an absent row. The abstract base's `@abstractmethod`
  `can_pick_up_tip` (`external/pylabrobot/pylabrobot/liquid_handling/backends/backend.py:183-187`) is
  asserted **absent by name**, so the rule is shown biting on real PLR source and not only on a
  synthetic fixture. **Plus §16.3's selection counts:** `n_surface_candidates`,
  `n_surface_absent_by_c15` and `n_surface_rows` are published and asserted to satisfy
  `candidates − absent == rows`, which is what makes "the complete measured selection" falsifiable.
- **AC-16.3 (the delegate→caller argument map binds, is measured, and fails closed).** The complete
  `(K, D, param, Term)` selection is published with `self._make_sure_channels_exist(use_channels)` and
  `self._assert_resources_exist(tip_spots)` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:520-522`)
  asserted present **by name**, and the refusal count broken down by which of M1's six conditions
  refused each pair. Six fail-closed fixtures, one per condition: a module-level delegate binds
  nothing; a delegate called twice binds nothing; an `ast.Starred` argument binds nothing; a delegate
  with `**kwargs` binds nothing; an argument that does not parse as a `Term` binds **only that
  parameter** to nothing while the others still bind; and a `depth == 2` guard binds nothing.
  `name_coincidence_exposure_count` at `depth == 1` is asserted **0**. The partial-map fixture and the
  depth-2 fixture are the stub-defeating halves. **Plus two round-1 fixtures.** (a) *The caller-side
  lineno (C10)*: a delegate defined **below** its caller, with a rebinding of the mapped name written
  **after** the delegate call, binds the pre-call value and **not** the rebinding — asserted
  positively, because the guard-lineno reading admits the rebinding and is an unsoundness. (b) *The
  `origin` clause (C9)*: a `caller_args`-resolved name whose caller-side `Term` resolves to ⊤ yields
  `guard_operand_unknown`, and a parameter with **no** `caller_args` entry yields
  `guard_env_dependent`; `:383`'s `strictness` is asserted **by name** to be in the second class,
  because `get_strictness()` does not parse as a `Term`.
- **AC-16.4 (depth-1 `WILL_FAIL` only under all three preconditions — CONDITIONAL on D1).** A depth-1
  guard evaluating `T` with `reachability_clear` true, `caller_reachability_clear` true, an
  `E-UNCOND`-satisfied `caller_scope_trail` and a total map yields `Verdict.WILL_FAIL` with
  `category == "precondition_state"`; the same guard yields `UNKNOWN`/`guard_env_dependent` under each
  of **five** perturbations, one fixture apiece: `reachability_clear` false; `caller_reachability_clear`
  false; `caller_reachability_clear` **absent** (⇒ `None` ⇒ blocked); an unsatisfied
  `caller_scope_trail` entry; and one free name resolving to ⊤. A sixth asserts `depth == 2` is still
  forbidden unconditionally. **The absent-field fixture and the depth-2 fixture are the stub-defeating
  halves.** **No in-loop fixture is added and none is owed** (§16.4's C19 box): an in-loop guard has a
  non-empty trail whose `for` entry is unsatisfiable under ways (1)–(3), which is asserted **once**
  here — a `for` scope entry yields `False` from `_entry_satisfies_uncond` — rather than as a sixth
  perturbation. If D1 is declined this criterion is withdrawn together with its task row rather than
  left unsatisfied.
- **AC-16.5 (the three `E-ENV` rules resolve exactly what §16.5 says, and the E-INV invariant holds).**
  Positive, one apiece: R-HEAD resolves `self.head` to the observed complete `Seq`; R-ATTR resolves
  `self.backend.num_channels` to `Lit(8)`; R-CONST resolves
  `self.backend.can_pick_up_tip(<⊤>, <⊤>)` to `Lit(True)` **with both arguments at ⊤**, which is
  argument-independence made checkable and is this criterion's stub-defeating half. Negative, one
  apiece: `self.head96` is ⊤; `self.head[channel]` is `Opaque` unchanged; `self.backend.<m>` for an `m`
  with no `constant_return` is ⊤; `self.backend.<m>` **inherited** rather than defined on the observed
  class is ⊤ (the no-MRO-walk rule); `self.backend.<m>` whose row §16.3's absence rule removed is ⊤;
  and any path not in §16.5's three shapes is ½/⊤. **Plus E-INV (C7), asserted as an invariant and not
  as a clause:** over the shipped production set, a production returning a definite value from a ⊤
  operand is one of exactly two — R-CONST and Q-MONO — checked by a parametrised fixture that feeds
  each production a ⊤ operand and asserts `None` for every other one. Whole-table:
  `n_resolved_by_rule` is published per rule and per lane, and R-ATTR's is asserted **0** at this pin.
- **AC-16.6 (the membership case and Q-MONO).** Membership: a `not in` against an R-HEAD-resolved
  complete `Seq` decides; a `not in` against a `Var` resolving to an ordinary `ir.Seq` is **½**,
  asserted **not** `T` — the `ir.Seq`-is-a-lower-bound rule made checkable, and the stub-defeating half
  of this group. **`:409` is asserted end-to-end through the shipped `len(Filtered) == 0` idiom**, from
  the guard record to the verdict, and **not** through a hand-built quantifier node — which is what
  proves the site goes through `_eval_alpha_existential` and needs no `target` field (D-G1). Q-MONO:
  all four cells of §16.5.5's table are asserted individually, with `AllOf(⊤, F)` asserted **½** and
  `AnyOf(⊤, T)` asserted **½** — the two vacuity cells, which are the second stub-defeating half. **The
  increment-6 amendment is asserted landed**: `.praxia/docs/specs/260904_plr-sema-predicate-increment.md`
  carries the amended G8(1)/A-C3 wording and the code comment at
  `plr-sema/src/plr_sema/check/predicate.py:574-579` matches it. **No Q-BIND fixture is present**, and
  a `target` field on `Filtered`/`AllOf`/`AnyOf` is asserted **absent** from the wire.
- **AC-16.7 (the scoped joined verdict).** `AnalysisReport.scope_verdict` is `None` whenever `scope` is
  `None`; equals `join` over the non-excluded findings otherwise; `verdict` is asserted **unchanged**
  on the whole shipped fixture set; `schema_version` is asserted **1**; and `join` itself is asserted
  called with a plain tuple and no keyword, by AST scan of the call site. One fixture constructs a
  report whose only `UNKNOWN` is a tier-(iii) finding and asserts `verdict == UNKNOWN` **and**
  `scope_verdict == SAFE` simultaneously — the two-fields-two-claims property. A second constructs one
  whose non-excluded findings include a `guard_predicate_unparsed` and asserts `scope_verdict ==
  UNKNOWN`, which is §16.6's claim (3) made checkable and this criterion's stub-defeating half.
- **AC-16.8 (the fence: the frame LIST, the any-frame narrowing, and the untouched unscoped counter).**
  `verify()` returns `error_frames` as a **list** of `file`/`lineno`/`qualname` records in
  outermost-first order for a raising row, and `None` otherwise, from both handlers. **The
  stub-defeating fixture is the re-raise case (C5), and it is the one spec_version 1 did not have:** a
  row whose exception is raised **inside the backend** and re-raised at
  `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:575-576` is asserted **excused** —
  an implementation matching only the innermost frame excuses nothing and fails this fixture while
  passing every other one. A second fixture keeps spec_version 1's direct case (a raise inside
  `_make_sure_channels_exist`, whose own `qualname` must appear). A third asserts the **outermost**
  match decides when several frames match. A fourth asserts that a `scope_verdict == "safe"` row
  **none** of whose frames is an excluded site is counted `unsound_scoped` and **not** excused — the
  failure this increment introduces, asserted positively. **Every match is asserted against a real
  `PlrSite` string read from the shipped contract table, never against a hand-written tuple (C20)**,
  and one fixture drives both sides through the single normalisation helper with the PLR package
  resolved outside `external/pylabrobot/` to pin the path identity. `unsound` and
  `rows_excused_by_scope` are asserted **byte-identical** to
  `outputs/plr-sema/oracle_replay_260909_inc6.json:2-21`. `unsound_scoped` is published with
  `rows_excused_by_frame`, and every excused row's full frame list is published beside it. Tier 2b
  carries the identical capture and narrowing.
- **AC-16.9 (tier 1 — 0 unsound in both counters, and the decided-findings floor).** The
  sidecar-gated replay reports `unsound == 0` under the unmodified predicate,
  `unsound_scoped == 0`, `rows_setup_error == 0`, `rows_executed == 343`, crosscheck 191/191 at
  agreement 1.0. **The gated number is `n_findings_decided`**, per PLR site, with a floor of
  **≥ 2,009** — 1,563 plus `:409`'s **223-certain** half plus `:514`'s 223, derived from §16.10.3's own
  prediction rather than asserted. **2,170 is published as the TARGET and is not gated**, because it
  assumes `:409` clears on all 384, which §16.10.3 explicitly declines to claim; spec_version 1 gated
  on the uncertain half and a prediction-holding run would have failed its own criterion (C4). Under
  D6 the published value rises to **≥ 3,385**, still gated at 2,009. `guard_predicate_unparsed` is
  asserted **unchanged at 495** and `guard_operand_unknown` **unchanged at 144**, the two cheapest
  falsifications of the claims that this increment touches no coverage gap and moves no reason. **The
  stub-defeating half: an implementation that threads the observation but reaches no atom scores
  `n_findings_decided == 1,563` and fails.**
- **AC-16.10 (non-regression, and the depth-1 mutant).** m1 199/199, m2 289/289, v1 67/67 at the raised
  index with 0 unsound, tier 2b at 16 fixtures with `region_unsound == 0` and
  `region_will_fail_fired >= 7` and `volume_will_fail_fired == 3`, **with any tier-2b movement
  attributed to a named rule from R-HEAD / R-CONST / Q-MONO / the D6 site rules before the run is
  accepted** (§16.11's corrected attribution). p1's three mutators re-measured at 288/288, 16/16 and
  0/288 with 0 unsound — **unchanged**, which is what proves the E-UNCOND(4) lift did not disturb the
  depth-0 population. **p2a is published as `achieved/attempted` in p1's own shape**, with
  `n_construction_skipped` and `n_error` beside it, and the floor is **`achieved == attempted` with
  `attempted >= 200`** and 0 unsound in both directions — not a bare "≥ 1", which 1/300 satisfies
  (C23). It is withdrawn with AC-16.4 if D1 is declined.
- **AC-16.11 (the measured sets are published and the gate is decided by them).** All **eight** blocks
  of §16.10.1 are present and non-null in the report, including `n_quantifier_decided_by_qmono` (C21)
  and the per-lane `n_resolved_by_rule` split; the GO/NO-GO is recorded against the published
  per-operation `scope_verdict`, which the **after-ledger** also carries (D-G4); and **the gate number
  is asserted computable from the JSON alone, without reading this document.** §16.10.3's per-site
  table is reproduced against the measurement **for whichever branch of D6 the user took**, cell by
  cell, and any divergence is recorded in §16.16 rather than absorbed. `:409`'s per-method count is
  published against the 223-certain / up-to-384 split. **`t30_measure` is either re-run and republished
  or its prediction role is explicitly recorded as retired for the `AllOf`/`AnyOf`,
  `Filtered`-emptiness and membership classes** (D-G5) — the report must say which, so the 48 in
  §16.10.3 is never read as current when it is not.
- **AC-16.12 (this document is machine-checked).** `plr-sema/tests/test_spec_lint.py` gains a constant
  for this file and parametrises it into both live-spec tests; `.praxia/docs/INDEX.md` is regenerated;
  and `uv run pytest plr-sema/tests/test_spec_lint.py -q` is **actually run** with its result recorded
  — the citation checker reporting **zero** failing violations over this file and the AC-gating half of
  the cross-reference checker reporting zero, with the other seven specs unchanged at zero.
- **AC-16.13 (the `:321` site rule — CONDITIONAL, only if the user takes D6).** The site rule keyed on
  `(LiquidHandler._assert_resources_exist, :321)` ships with the `deck_resource_names` observation and
  its per-slot map, whose **digest is asserted present in `env`** (D-G3). **A-DECK-OBJECT is added to
  increment 1 §10.6.3's named-assumption table with its own "what breaks if it is false" column**, and
  a test asserts the table has five rows. The rule is asserted to evaluate `F` or ½ and **never** `T`,
  by exhaustive fixture over both branches — the `ResourceNotFoundError` argument made checkable. **One
  HAND-BUILT adversarial fixture (C18):** a second `Resource` carrying a name already on the deck and a
  mismatched geometry, constructed directly and not through the kwarg-mutator API, asserted to produce
  a `SAFE` that the fence then counts unsound — so the assumption has one witness rather than only 288
  operations on which it was never at risk. `:321` is asserted `SAFE` on 288 real operations with
  `unsound == 0` and `unsound_scoped == 0`, and `n_assert_resources_decided == 288` is published.
  **If D6 is declined this criterion is withdrawn together with its task row rather than left
  unsatisfied.**
- **AC-16.14 (the `_check_args` site rules, D5b — CONDITIONAL, only if the user takes D6).** The two
  site rules of §16.1.1's D5b option land with the one further `Term` production they need (an
  `ast.Set` display of `ast.Constant`s) and with their own measured selection; **the new registry row
  is added and `len(live_rows()) == 25` against a `BUDGET_CAP` the user has raised to 25**, asserted
  directly, so an implementation that files them as HM-25 units fails. `:375` and `:383` are asserted
  `SAFE` **by name** on 544 operations, and `n_check_args_decided == 544` is published as the row's
  loud half — an import-the-symbol measure cannot see PLR renaming `vars_keyword`, so the published
  count is what goes red. **Both rules decline when §16.3's absence rule removed the
  `(backend_class, method)` row** (C15), asserted with a decorated-backend fixture. `scope_verdict ==
  SAFE` is asserted on ≥ 1 executed operation with both fence counters at 0 — **which requires
  AC-16.13 to have landed too**, and that conjunction is asserted rather than assumed. **If D6 is
  declined this criterion is withdrawn together with its task row and becomes increment 8's.**

---

## 16.13 Task rows

> **Normative (the ordering, and it is forced by the same gate discipline increment 5 §14.0 and
> increment 6 §15.12 both impose).** **T40, T41 and T42 must land and publish their measured selections
> before T43 resolves a single `EnvRef`.** A landed resolution rule without a published observation and
> a published surface can construct a definite verdict whose basis nobody has inspected, which is the
> configuration §16.10's measured blocks (1)–(4) exist to prevent. **T44, T45 and T46 must land in that
> order**: a `scope_verdict` without a fence behind it is a `SAFE` nobody is checking. **T48 and T49
> both depend on T43 and on each other's absence being recorded**: neither alone moves `scope_verdict`,
> so a run with one landed and the other not must publish the residual rather than be read as a NO-GO
> for the increment.

> **Normative (T42's dependency on T41 is DROPPED — C26, conceded).** spec_version 1 listed T42 as
> depending on T41 and never said why. `compute_caller_args(K, D)` reads `K`'s AST and `D`'s own
> `ast.arguments` out of the function index and **touches no backend surface**; the dependency was
> spurious and is removed, so T40, T41 and T42 are three independent rows. **What a D1 decline
> withdraws from T42, stated exactly rather than left to reshape the row mid-flight:** the additive
> `caller_reachability_clear` and `caller_scope_trail` pair and their derivation (~35 LOC), the three
> preconditions in the evaluator (~15 LOC), AC-16.4 and its six fixtures (~25 LOC), and p2a in T46.
> **The argument map itself — `compute_caller_args`, the `caller_args` field, M1, M2 and AC-16.3 — is
> unconditional and survives a decline in full**, at ~120 of the row's ~170 LOC.

> **Normative (why every AC is gated exactly once, and where the conditional rows sit).** The
> cross-reference lint reads the **gate cell only** — column 4 of a row matching `TASK_ROW_RE`
> (`plr-sema/scripts/check_spec_crossrefs.py:52-62`, with the gate cell taken as `cells[3]` and the
> `ac_multiply_gated`/`ac_ungated` checks at `plr-sema/scripts/check_spec_crossrefs.py:139-156`). An
> AC named in a scope cell, in a box, or in prose is documentation and not a gate. **AC-16.4, AC-16.13
> and AC-16.14 are gated on rows T42, T48 and T49 respectively, each of which is conditional on a user
> decision** — the same construction increment 6 used for AC-15.12 on T34, and the reason a declined
> decision withdraws the criterion **with** its row rather than leaving it unsatisfied.

| task | scope | files | gate | ~LOC | depends on | model |
|---|---|---|---|---|---|---|
| **T40** | **The observation record and its cache-key partition (§16.2).** `verify()` gains the additive `plr_observation` result key with exactly the four fields of §16.2.1, all read at **ONE** capture point after `await setup.machine.setup()` and before `_execute`, inside a fail-closed guard that yields `plr_observation = None` on the deck-build early return and on any raising read; `deck_resource_names` extracted **recursively** off the live deck tree, deck name plus every descendant; the harness reads the record and builds the `obs:<key>=<value>` members under §16.2.3's **JSON** encoding, with ints sorted numerically and strings lexicographically, plus the deck map's digest member under D6; `env` is threaded unchanged through `check_ir`/`check_graph`; the `obs:` prefix is reserved and asserted never to satisfy `E-UNCOND` way (2); the closed refusal list is enforced by a test that fails if `plr_observation` grows a fifth key; the harness asserts `len(head_channels) == num_channels`. **No resolution rule, no evaluator change, no verdict moves** — with `env` carrying the new members and §16.5 unlanded, every finding is byte-identical **at this row's state** | modify `training/verify/verifier.py`, `training/verify/deck.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/eval/region_oracle.py`, `plr-sema/tests/test_cache.py`, `training/tests/test_verify_postconditions.py` | `uv sync --all-packages`; `uv run pytest training/tests/test_verify_postconditions.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q` (no test may pin a literal `cache_key`, and the empty-`env` key is asserted unchanged) — satisfying **AC-16.1** | ~180 | — | Sonnet — the fail-closed identity property is the whole of this row's value and it is asserted as an equality over findings, not as a count |
| **T41** | **The derived backend surface (§16.3).** A per-`(class, method)` table over `build_plr_function_index` recording non-default parameter names after `self`, `has_var_keyword`, `has_var_positional`, and `constant_return` under the exactly-one-`ast.Return`-of-an-`ast.Constant` shape test (a docstring counts as a statement); **the ABSENCE rule — a row is absent when `decorator_list` is non-empty, the definition is a `property`, or the qualname is defined at more than one lineno — which is what keeps an AST fact from standing in for a runtime one**; **ONE closed selection rule** (`method` equals the last segment of some `EnvRef.path` in the regenerated contract table, then the absence rule), with `n_surface_candidates`, `n_surface_absent_by_c15` and `n_surface_rows` published; **no** literal base-class name and no method list anywhere in the derivation; published as the additive fifth top-level key `backend_surface` of `plr-sema/data/derived_contracts.json`, which regenerates and cools the cache by design; the complete measured selection published, including the whole-tree `can_pick_up_tip` count against the predicted 2 of 8 | modify `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q`; then regenerate the contract table — satisfying **AC-16.2** | ~165 | — | Sonnet — the no-hand-typed-fact claim is checked by a grep assertion, and the absence rule is the soundness gate every rule reading this table inherits |
| **T42** | **The delegate→caller argument map and the depth-1 lift (§16.4).** `compute_caller_args(K, D)` in `derive/bindings.py` under M1's six conditions, fail-closed on every other shape; the additive `caller_args` field on `InlinedGuard` carrying existing `Term` JSON, absent ⇒ `None`; M2's resolution ordering, with the caller-side `Term` evaluated in `K`'s context, `E-CALL(5)` applying in `K`, **every caller-side position and scope test keyed on the delegate CALL STATEMENT's lineno in `K`**, and a `caller_args`-resolved name carrying origin `"operand"`; the additive `caller_reachability_clear` and `caller_scope_trail` pair; **D1's lift of `E-UNCOND(4)` at `depth == 1` under all three preconditions, with `depth >= 2` untouched and in-loop guards protected by the trail rather than by a fourth clause**; the complete measured selection and the M1-condition refusal breakdown published; `name_coincidence_exposure_count` at depth 1 re-measured and asserted 0 | modify `plr-sema/src/plr_sema/derive/bindings.py`, `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_check_graph.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q` — satisfying **AC-16.3** and **AC-16.4** (the latter conditional on **D1**; declined ⇒ the box above lists the exact files and ~50 LOC withdrawn, the map ships in full, and AC-16.4 is withdrawn with the lift) | ~170 | — | Sonnet — **the lift is the one clause in this increment that can produce a false positive on a clean operation**, and increment 6 round 1 filed six blockers in this direction |
| **T43** | **`E-ENV` resolution, the membership case and Q-MONO (§16.5), with the registry spend.** R-HEAD, R-ATTR and R-CONST in `check/predicate.py`, each declining to today's ½/⊤ on an absent or partial observation and on a row §16.3's absence rule removed; the membership deciding case reopened under §16.5.4's three conditions, with the `ir.Seq`-is-a-lower-bound rule stated in the evaluator and **no field added to `ir.Seq`**; **Q-MONO**, all four cells, **and the matching amendment written into increment 6's own G8(1)/A-C3 text and into the code comment that repeats it**; **E-INV** stated and asserted over the shipped production set, with R-CONST and Q-MONO its two named instances. **Q-BIND is NOT implemented and no `target` field is added** — `:409` goes through the α-existential path, which already binds element-wise. Per-rule, per-lane `n_resolved_by_rule`/`n_declined_by_rule`, `n_membership_decided` and `n_quantifier_decided_by_qmono` published. **The approved HM-25 `declared` 9 → 10 spend (D4), filed as ONE further unit inside the existing entry whose `what` now also names the path-shape table, and `_measure_hm25` importing the path-rule symbol — stopping and asking the user if the measured count would exceed 10** | modify `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/src/plr_sema/_hand_maintained.py`, `.praxia/docs/specs/260904_plr-sema-predicate-increment.md` (the G8(1)/A-C3 amendment), `plr-sema/tests/test_hand_maintained_ratchet.py`, and the fixtures under `plr-sema/tests/fixtures/` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q`; `uv run pytest plr-sema/tests/test_tip_typestate.py -q`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_spec_lint.py -q` (the increment-6 edit must not break its citations) — satisfying **AC-16.5** and **AC-16.6** | ~150 | **T40 + T41 + T42**, each with its measured selection published | Sonnet — three rules and one clause, all in the `SAFE` direction; the two vacuity cells of Q-MONO and E-INV are what stand between it and a false `SAFE`; the row **shrank ~50 LOC** when Q-BIND was withdrawn |
| **T44** | **Q1's scoped joined verdict (§16.6).** `AnalysisReport.scope_verdict`, computed at the one `_check` call site by the **unchanged** `join` over the findings whose `plr_site` is not in `scope.excludes_sites`; `None` whenever `scope` is `None`; `verdict` untouched; `schema_version` asserted 1; the static side publishes `scoped_verdict` per operation beside `verdict`. **`join` is not modified, not overloaded and not called with a flag**, asserted by AST scan of the call site | modify `plr-sema/src/plr_sema/verdict.py`, `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/tests/test_verdict.py`, `plr-sema/tests/test_check_graph.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_verdict.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q` — satisfying **AC-16.7** | ~90 | T43 | Sonnet — small, and the smallness is the point: the field is a filter plus a call to a function this row does not touch |
| **T45** | **The fence (§16.7).** The **whole** `traceback.extract_tb(...)` frame list captured at both `verify()` handlers and in `region_oracle._run_fixture_execution`, returned as the additive `error_frames` key (outermost first, order preserved, `None` when there is no error); F2's narrowing excusing a row iff **ANY** frame matches an excluded site, with the **outermost** match deciding on a tie; **ONE normalisation helper applied to both the frame path and the `PlrSite`**, with the lineno and path identities asserted rather than assumed; `rows_excused_by_frame` published with every excused row's full frame list; **`unsound` and `rows_excused_by_scope` unmodified in definition and asserted byte-identical to the `260909_inc6` run**; `exc_class` asserted absent from the comparison path | modify `training/verify/verifier.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/eval/region_oracle.py`, `plr-sema/tests/test_oracle_replay.py`, `training/tests/test_verify_postconditions.py` | `uv sync --all-packages`; `uv run pytest training/tests/test_verify_postconditions.py -q`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q` — satisfying **AC-16.8** | ~130 | T44 | Sonnet — spec_version 1 shipped an innermost-frame match that would have excused **nothing**, and the re-raise fixture is the one test that catches it |
| **T46** | **The oracle, the mutants and the gate (§16.10, §16.11).** Tier-1 re-run under the unmodified predicate with both counters published; `n_findings_decided` per PLR site against the **≥ 2,009** gated floor with 2,170 published as the target; the after-ledger with `consistency.ok`, its published delta **and `scope_verdict` threaded through `unknown_ledger.py` so the ledger can audit the gate**; §16.10.1's **eight** measured blocks; §16.10.3's per-site prediction table reproduced cell by cell for whichever branch of D6 the user took, with every divergence recorded; `plr-sema/eval/predicate_mutants.py` extended with p2a published as `achieved/attempted`; **`t30_measure` re-run and republished, or its prediction role recorded as retired for the classes this increment redefines**; the m1/m2/v1/tier-2b non-regression set re-measured with every movement attributed to a named rule; **the GO/NO-GO recorded against the published per-operation `scope_verdict`, computable from the JSON alone** | modify `plr-sema/eval/oracle_replay.py`, `plr-sema/eval/predicate_mutants.py`, `plr-sema/eval/unknown_ledger.py`, `plr-sema/eval/t30_measure.py`, `plr-sema/eval/tip_mutants.py`, `plr-sema/tests/test_oracle_replay.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q`; then the tier-1 replay with its three standard flags, `unknown_ledger.py` into `outputs/plr-sema/unknown_ledger_2609XX_after.json`, `predicate_mutants.py`, `tip_mutants.py`, `volume_mutants.py`, `region_oracle.py` and `t30_measure.py` into `outputs/plr-sema/*_2609XX_inc7.json`, publishing the delta against the `260909_inc6` set — satisfying **AC-16.9**, **AC-16.10** and **AC-16.11** | ~250 | T45 | Sonnet — every published number is a measurement, and this row is where §16.1's site analysis is either confirmed or falsified by one number, in whichever branch the user chose |
| **T47** | Lint and index: register this file in `plr-sema/tests/test_spec_lint.py` and parametrise it into both live-spec tests; regenerate `.praxia/docs/INDEX.md`; **actually run the lint and record the result** | modify `plr-sema/tests/test_spec_lint.py`; regenerate `.praxia/docs/INDEX.md` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_spec_lint.py -q` — satisfying **AC-16.12** | ~6 | — | Haiku |
| **T48** | **CONDITIONAL on D6 — do not start without the user's answer.** The `:321` **site rule**: a rule keyed on `(LiquidHandler._assert_resources_exist, :321)` evaluating `F` iff every element of the caller-bound `resources` resolves to a slot whose observed name is in `deck_resource_names`, and ½ otherwise — **never `T`**; the per-slot name map threaded from `resources_from_example` **with its digest in `env`**; **A-DECK-OBJECT added to increment 1 §10.6.3's named-assumption table with its own breakage column**, taking the table from four rows to five; one **hand-built** duplicate-name adversarial fixture; `n_assert_resources_decided` published. **This row and T49 share ONE registry row between them** — the site-rule class D6 names — and whichever lands first adds it, taking `len(live_rows())` to 25 against a `BUDGET_CAP` the user has raised; the second asserts it is already there and does not add a second | modify `training/verify/verifier.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/src/plr_sema/_hand_maintained.py`, `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md`, `plr-sema/tests/test_check_graph.py`, `plr-sema/tests/test_hand_maintained_ratchet.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q` (`live_rows` 25, `BUDGET_CAP` 25, both asserted); then re-run the tier-1 replay and re-measure — satisfying **AC-16.13** | ~120 | T43 | Sonnet — the **assumption plus the registry row**, not the observation, is what this row spends, and its check on the corpus is bounded by argument rather than by adversarial measurement |
| **T49** | **CONDITIONAL on D6 — do not start without the user's answer. This is D5b, NOT D5a.** The two `_check_args` **site rules**: one keyed on `(LiquidHandler._check_args, :375)` resolving `Len(Var("missing"))` to 0 when `params(backend_class, m)` is a subset of `default`, one keyed on `(LiquidHandler._check_args, :383)` resolving `Len(Var("vars_keyword"))` to 1 when `has_var_keyword` is true — reading the observed `backend_class`, §16.4's `caller_args` for `m` and `default`, and §16.3's surface for the two columns; **one** further `Term` production, an `ast.Set` display of `ast.Constant`s; **both rules decline when §16.3's absence rule removed the row**; `n_check_args_decided` published as the loud half. **The registry row is the one T48 also uses** (see that row); if T48 has not landed, this row adds it. **D5a — the general model, ~350 LOC and five productions — is NOT this row and remains increment 8's** | modify `plr-sema/src/plr_sema/derive/predicate_ast.py`, `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/src/plr_sema/_hand_maintained.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_check_graph.py`, `plr-sema/tests/test_hand_maintained_ratchet.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q`; then the full tier-1 replay and the whole non-regression set — satisfying **AC-16.14** | ~130 | T43 | Sonnet — one-directional by construction (D-G6: both guards carry `reachability_clear` false and `fires is False` returns `SAFE` unguarded by depth), so the whole risk is the AST-vs-runtime gap §16.3's absence rule closes |

**Sizing note, stated honestly and with the one number that is a guess flagged as one.** T40 at ~180
is mostly harness plumbing and its own identity test. T41 at ~165 is one AST pass, the absence rule,
the closed selection rule and their published counts. T42 at ~170 is increment 6 §15.12's own ~90 LOC
estimate for the map, plus ~50 for the two additive reachability fields and their round-trip, plus ~30
for the lift's three preconditions — **and ~50 of that is withdrawn on a D1 decline**, itemised in the
box above. **T43 SHRANK ~200 → ~150** when Q-BIND was withdrawn (round 1, D-G1): ~60 for the three
rules, ~30 for the membership case, ~15 for Q-MONO plus its increment-6 amendment, ~45 for the
published counters, and **zero for the `target` field and its `parse` half, which are not built**.
**T45 grew ~120 → ~130** for the frame list and the normalisation helper; **T46 grew ~220 → ~250** for
the ledger's `scope_verdict` column, the eighth measured block and `t30_measure`'s re-run.
**Total for the unconditional rows: ~1,151 LOC across seven rows, which is three sessions.** T48 adds
~120 and T49 ~130 — **so D6 taken costs ~250 LOC in total, not the ~350 spec_version 1 attributed to
`_check_args` alone**, which is the single largest number this revision moves. **T43 splits cleanly**
at the three resolution rules versus Q-MONO plus the increment-6 amendment, and it is the row to split
first if a session boundary falls inside it. **Do not split T43 from T40/T41/T42 in the other
direction**: a landed resolution rule without published observation and surface selections is the
configuration the ordering box exists to prevent.

---

## 16.14 Not in this increment

- **`_check_args`'s GENERAL model — D5a, and D5a only.** The five productions of §16.1.1's box, both
  directions, ~350 LOC. **D5b, the two `SAFE`-direction site rules, is NOT on this list** — round 1
  showed the gate needs only that direction and that it is computable from §16.3's own columns, so it
  is T49 under D6 rather than a deferral. **What stays out is the general case**, which nothing in this
  increment needs and which would price four productions the `SAFE` direction never forms.
- **Q-BIND, and the `target` field on `Filtered`/`AllOf`/`AnyOf`.** Withdrawn during round 1 as dead
  machinery: `:409` is evaluated by the α-existential path, which already binds element-wise
  (`plr-sema/src/plr_sema/check/predicate.py:433-456`), and no other site at this pin reaches the
  quantifier path. A later increment may want it; **that increment must name the site**, which this one
  could not.
- **R-DECK as an `EnvRef` shape**, and the two productions that would have repaired it — a third
  binding idiom for `x = <call>` plain assignments, and element-wise binding over a `for` target. Both
  are refused (§16.1.3); `:321` is respecified as a site rule instead.
- **The γ loop idiom, the bounded literal-display loop.** Increment 6 §15.13 deferred it here to be
  revisited *"alongside the pred-aware `BRANCH`"*. **Decision: it stays out**, and the argument is not
  cost. γ is a loop-recognition rule in increment 5 §14.6 R1's territory, and this increment already
  takes one clause in R1's own risk direction — D1's lift of `E-UNCOND(4)`, which newly permits
  `WILL_FAIL` on a population that could not previously emit one. Taking two reachability-widening
  rules in one increment puts them in the same measurement and makes a regression in either
  unattributable. Its beneficiaries, `aspirate` and `dispense`, are not gate candidates for three
  independent further reasons (`:116`, the unseeded volume cell, and `:375`/`:383`), so γ buys no
  operation anything this increment could report.
- **The `pred`-aware `BRANCH`** (increment 3 §12.3.6 B2). **Argued rather than listed (C26).** It is a
  claim about which *arm of a branch executes*, i.e. about reachability, and this increment already
  takes its one reachability-widening clause in D1. Nothing on the gate candidate is inside a `BRANCH`:
  `pick_up_tips`'s ten guards are all straight-line or loop-enclosed
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:488-524`), so admitting it would
  move no operation this increment reports and would put two reachability rules in one measurement.
- **The lid topology** (`:116`/`:117`) **and the general `Identity(Term, Term)`.** Increment 4 §13.1's
  disposition stands. `:116`'s `lidded is resource` is an object-identity relation the IR models
  nowhere; §16.5 admits three **path** shapes and no relation. Admitting `Identity` would make four more
  methods GO candidates, which is precisely why it is refused here rather than there.
- **Tuple-display comparison** (`:2030`) and **arithmetic `BinOp` terms** (`:2211`,
  `volume_tracker.py:91`). **Argued rather than listed (C26).** A tuple display is a `Term` production
  and an elementwise `Cmp` rule, i.e. two more grammar productions in an increment whose grammar
  contribution is deliberately zero; its beneficiary is `stamp`, which stays NO-GO under both branches
  of D6 for an independent reason (branch-bound `containers`), so it buys no operation anything here.
  The arithmetic `BinOp` is additionally the volume family's by the dispatch rule and sits under Open
  decision 2, whose resolution this increment does not reopen.
- **A fourth idiom for loop-append bindings** (`tips = []` then `tips.append(...)`) and for
  `n = len(<param>)`. Both are still a general dataflow pass by another name, and `tips` staying ⊤ is
  what §16.5.5's Q-MONO is built to work around rather than to hide.
- **The well-seeding observation** that would move `volume_state_unknown`. Refused by name in §16.2.1;
  it belongs to the volume family and to a gate this increment's does not read.
- **Replacing §8's hand-written-contract bridge.** §8 is not gating (AC-8.3); the debt is recorded, not
  discharged, exactly as increment 6 §15.13 records it.
- **Deferred row (e), the `move_*` family's `unresolved_delegate` gap**
  (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2520`). 93 operations, 17% of the benchmark,
  outside every mechanism here. None of §16.5's rules touches a `<none>`-sited delegate gap.
- **Precision targets, deferred row (f)**
  (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:2524`). AC-16.9's floor is a floor against a
  null result, not a target.
- **A thirteenth `REASON_VOCABULARY` member.** §16.8's box names the one distinction that would need
  one and declines it in favour of a published counter.
- **A new registry row — UNLESS D6 is taken.** Under D6 declined, `live_rows()` stays 24 against
  `BUDGET_CAP` 24 and every mechanism here is either derived (§16.3, §16.4, §16.6, §16.7) or files onto
  the existing HM-25 entry (§16.5, D4). **Under D6 taken, one row is added and the cap moves to 25** —
  the site-rule class T48 and T49 share. That is a cap conversation and it is the user's, which is what
  makes D6 a decision rather than a sprint choice.
- **#4923 / #4924** — decision hooks only, unchanged.

---

## 16.15 The questions, their dispositions, and every user decision hook

### Q1 — what is a joined `SAFE` *within scope*, and how is it represented?

**DISPOSED by §16.6: a second, additive `scope_verdict` field, computed by the unchanged `join` over
the findings whose site is not in `scope.excludes_sites`, with the unscoped `verdict` staying
`UNKNOWN`.** `schema_version` stays 1 on the additive-field rule
(`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:3322-3326`). It asserts that no PLR
precondition guard the analyzer evaluated, outside the excluded sites, fires against this call under
the recorded observation; it asserts nothing about completion (A-COMPLETES,
`.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:752`), nothing about the backend, and
nothing under a different observation. `compare` scores it with a **second** counter, `unsound_scoped`,
beside the unmodified `unsound` (`plr-sema/eval/oracle_common.py:1086-1088`), and neither replaces the
other. **The alternative considered and rejected: emitting tier (iii) as `SAFE` with a marker** —
increment 6 §15.5 already rejected it as unsound and must-not-implement, and nothing here reopens it.

### Q2 — is `:321` decidable without a name on `ir.Resource`?

**DISPOSED by §16.1.3, and REVISED at spec_version 2: yes, but only through a SITE RULE and a named
assumption, not through an `EnvRef` shape.** spec_version 1's R-DECK matched a shape absent from the
contract table (C3), and both halves of the confirmation are shipped data: `:321`'s guard record is
`Not(Cmp(Var, "==", Var))` with no `EnvRef` and empty `bindings`, and `resource` is a `for` target
(`plr-sema/data/derived_contracts.json:88795-88822`). The repaired rule reads the **caller-bound
`resources`** and the observed deck-name map, which needs neither of the two productions C3 priced.
The `Resource.__eq__` half is still an assumption: the comparison is structural over name, geometry,
location, category and children (`external/pylabrobot/pylabrobot/resources/resource.py:160-170`) and
the IR's `Resource` carries none of those (`plr-sema/src/plr_sema/check/ir.py:178-191`). Adding `name`
to `ir.Resource` costs an `IR_VERSION` bump and decides only the half that is already true by
construction; **rejected on those grounds and recorded as rejected.** The remaining options are the
site rule plus A-DECK-OBJECT (**D2, now conditional on D6**) or ½.

### Q3 — is a depth-1 `WILL_FAIL` permitted?

**DISPOSED by §16.4's D1 box: recommended YES, under three preconditions and no fewer** — the
delegate's `reachability_clear`, a new `caller_reachability_clear` plus an `E-UNCOND`-satisfied
`caller_scope_trail`, and a total argument map for the guard's free names. `depth >= 2` stays forbidden
unconditionally. **The cost of declining is that this increment adds no `WILL_FAIL` population at all**
and its two new decidable sites are exercised in one direction only; the cost of taking it is a clause
in the false-positive direction, fenced by tier 1 on 544 operations and by p2a.

### Q4 — what shape does the observation take in the cache key?

**DISPOSED by §16.2.3: `obs:<key>=<value>` members of the existing fifth `env` component, not a sixth
component.** The tuple's arity is a wire fact every caller and every persisted key sees; `env` exists
for exactly this and its `tuple(sorted(env))` encoding already guarantees the two properties
`cache_key`'s docstring requires (`plr-sema/src/plr_sema/check/ir.py:918-953`). The `obs:` prefix is
reserved so no member can satisfy `E-UNCOND` way (2), which is what prevents an observation from
manufacturing reachability.

### Q5 — what may the headline claim?

**RE-DISPOSED at spec_version 2, and the answer reverses: the headline the user substituted into
increment 7 on 260907 IS reachable in this increment, and its reachability rests on exactly one user
decision — D6.** spec_version 1 answered "not reachable" on a refusal round 1 broke in two places: the
`_check_args` sizing (C1) and R-DECK's shape (C3). Neither survives.
**What the sprint may claim under D6 taken:** the first joined `SAFE`-within-scope on real executed
operations of the frozen benchmark — predicted on **≥ 167** of `pick_up_tips`'s 223 — with the tier-1
fence at 0 unsound in both counters.
**What it may claim under D6 declined:** `:409` and `:514` decided, the scoped verdict representation
shipped with a working fence behind it, `n_findings_decided` ≥ 2,009, and the residual reduced to
**three named lines of two named PLR functions** with a ~250 LOC route to closing them. It may **not**
report a joined `SAFE`.
**Either way the user is owed the choice before the work starts and not at a gate**, which is the one
respect in which this document improves on increment 6's own late discovery of the same class of
finding — and spec_version 1 got that right about a wrong answer, which is why the answer changed and
the discipline did not. §16.10.4's last box states the cheapest falsification for each branch.

### Q6 — increment 6 §15.16.3 R1's owed adversarial review

**Increment 6's E-UNCOND(5) refinement — "an earlier `ast.Raise` or `assert` does not block a depth-0
empty-trail `WILL_FAIL`" — was measured (0 unsound on tier 1 and on all three p1 classes,
`outputs/plr-sema/predicate_mutants_260909_inc6.json:2-58`) and never attacked.** It is restated here as
five numbered claims so the round can attack them individually rather than the paragraph as a whole.

> **R1-C1.** Let `G` be a depth-0 guard whose `scope_trail[1:]` is empty, whose predicate evaluates
> `T`, and for which `compute_reachability_clear` returns `True`
> (`plr-sema/src/plr_sema/derive/bindings.py:778-815`). Then `K` contains no `ast.Return` at a lower
> `lineno`, `G` is not lexically enclosed by an `ast.Try`/`ast.With`, and `K` contains no earlier
> `ast.Break`/`ast.Continue`.
>
> **R1-C2.** Under R1-C1, exactly two executions of `K` are possible with respect to any earlier
> `ast.Raise` or `assert` `R`: either `R` fires, or it does not.
>
> **R1-C3.** If `R` fires, the operation raises at `R` and does not complete.
>
> **R1-C4.** If `R` does not fire, control is not diverted anywhere else — clause (1) forbids an
> earlier return, clause (2) a swallowing handler or context manager, clause (3) a break or continue —
> so control reaches `G`, whose predicate is `T`, so `G` fires and the operation raises.
>
> **R1-C5.** `WILL_FAIL` is a claim about the **operation**, not the site: `join` propagates one
> `WILL_FAIL` finding to the whole report (`plr-sema/src/plr_sema/verdict.py:383-386`) and `compare`
> scores the operation's index, `verdict == "will_fail"` against `outcome == "ran_ok"`, never the
> identity of the raising statement (`plr-sema/eval/oracle_common.py:767-786`). Therefore, by R1-C3 and
> R1-C4, the published claim is true in both branches and no hypothesis about `R` is taken.

**The three attacks a round should try first, named by this document rather than left to be found.**
**(1)** R1-C4's "not diverted anywhere else" is a claim about `K`'s **statements**, but a called
function can raise, be caught by a handler *outside* `K`, and return control nowhere — which does not
falsify R1-C5 (the operation still fails) but does mean the enumeration in R1-C2 is not exhaustive as
worded. **(2)** `compute_reachability_clear`'s clause (3) is conservative but its clause (1) is a
whole-body `lineno` scan that does **not** check whether the return is on a path that can precede the
guard, so it can only block, never permit — the safe direction, but it means R1-C1's antecedent is
narrower than the argument needs and the argument is therefore not tight. **(3)** `enclosed_by_try_or_with`
tests `K`'s own ancestors; a `try` in a **caller** does not appear, which is sound for R1-C5's
operation-level claim and would not be for a site-level one.

> **The interaction with this increment, stated because it is the question the round will ask.**
> **D1's depth-1 lift does not weaken R1 and does not rest on it.** R1 governs the **empty-trail**
> clause (5), which is consulted only for `depth == 0` guards; D1 adds an independent depth-1 path
> whose preconditions include `reachability_clear` for the delegate **and** the caller-side pair, so a
> depth-1 guard passes through clause (5)'s logic **twice**, once per body, and each pass is
> conservative. **The one place they touch** is that a depth-1 guard whose delegate body has an
> empty trail now reaches clause (5) at all, where before `E-UNCOND(4)` cut it off earlier — so R1's
> soundness argument is load-bearing for a population it has never been measured on. **AC-16.4's five
> perturbation fixtures are what pin that**, and p1's three mutators being re-measured **unchanged**
> at 288/288, 16/16 and 0/288 (AC-16.10) is what shows the depth-0 population did not move.
>
> **One clause of R1-C2's enumeration is now written down rather than assumed, and it answers C19 in
> R1's own terms.** *A guard lexically inside a `for` or `while` cannot reach clause (5) at all*,
> because `scope_trail` **records loop headers** — `:321`'s is
> `["if not resource_from_deck == resource", "for resource in resources"]`
> (`plr-sema/data/derived_contracts.json:88819-88822`) — and a header entry parses `Opaque`, evaluates
> ½ and is unsatisfiable under ways (1)–(3)
> (`plr-sema/src/plr_sema/check/predicate.py:724-738`, `:773-788`). So "the loop body never runs" is
> **not** a missing disjunct in R1-C2: clause (5) is the empty-trail case only, and an in-loop guard
> never has an empty trail. R1's argument is unaffected in both directions, and `compute_reachability_clear`
> not testing loops is sound **because the trail check carries it** — which was true before this round
> and undocumented.

### The user decision hooks, together, each with this document's recommendation

| id | the decision | what it costs | what declining costs | recommendation |
|---|---|---|---|---|
| **D1** | Lift `E-UNCOND(4)`'s `depth >= 1` `WILL_FAIL` forbiddance at depth 1 only, under §16.4's three preconditions | one clause in the false-positive direction, on a population increment 6 round 1 filed six blockers about | this increment adds **no** `WILL_FAIL` population; `:409` and `:321` are exercised in the `SAFE` direction only; p2a is withdrawn; ~50 LOC leaves T42 | **YES, unchanged after round 1** — C19's missing-precondition attack is rebutted on the evidence (`scope_trail` records `for` headers and they are unsatisfiable under ways (1)–(3)), and C10/C11 were scoping fixes rather than soundness defects. A new decision procedure tested in one direction is half tested, and both the tier-1 fence on 544 operations and p2a check it |
| **D2** | Admit **A-DECK-OBJECT** as a fifth named assumption, plus the `deck_resource_names` observation, so `:321` decides | the analyzer's assumption set grows from four to five for the first time since increment 1 | `:321` stays ½ on 288 operations and **`scope_verdict` stays `UNKNOWN` everywhere even if D5b ships** | **YES, but REPRICED and now CONDITIONAL ON D6.** R-DECK as written cannot fire (C3, confirmed against the shipped contract table), and the only repair is a site rule of D5b's class — so D2 is no longer ~110 LOC and no longer a standalone ask. Its evidential basis also changed: the fence checks the assumption **on the corpus**, not in general (C18), and AC-16.13's hand-built fixture is its one adversarial witness |
| **D3** | *(a NON-decision, recorded so the round can attack it)* §16.3's derived backend surface introduces **no** hand-typed PLR fact and therefore needs no row | nothing | — | **No decision is asked, and it SURVIVED round 1** — the harness-side literal PLR paths ride increment 5's `volume_tracking_observed` precedent and the registry's scope is the analyzer's own front end, which §16.3 now states with the citation. **One thing changed:** the selection rule's undefined second clause is deleted and replaced by one closed rule with published counts (C16), because an unfalsifiable "complete measured selection" is a worse defect than a hand-typed fact would have been |
| **D4** | HM-25 `declared` **9 → 10**, for §16.5's `EnvRef` path table (**three** shapes after R-DECK's withdrawal) | one per-row ceiling unit; `live_rows()` and `BUDGET_CAP` both unchanged at 24; no cap conversation | §16.5 cannot ship, and with it `:409` and `:514`; the increment reduces to plumbing | **YES, unchanged after round 1** — the unit buys the pattern regardless of instance count, so R-DECK's withdrawal does not reduce the ask and C25's R-ATTR point is a presentation improvement, now surfaced as an explicit sub-note (§16.5.2). HM-25 is the loud-failure row, §16.10's per-rule counters are the loud test, and increment 6 spent 8 → 9 on this row for this reason |
| **D5** | Model `_check_args` — **repriced as three options after round 1** | **D5a** the general model, ~350 LOC, five productions. **D5b** two `SAFE`-direction site rules, ~100–130 LOC plus the D6 registry row, C15's absence rule as its precondition. **D5c** neither | under D5c the headline slips a second time, to increment 8 | **D5b, IF D6 IS TAKEN** — the recommendation moves from NO. C1's arithmetic holds at the pin, the `SAFE` direction needs neither the set-difference term nor the `**kwargs` key set, and **D-G6 shows the discharge is one-directional by construction**: both guards carry `reachability_clear` false and `fires is False` returns `SAFE` unguarded by depth, so it can add `SAFE` and can never emit a false `WILL_FAIL`. **D5a stays increment 8's** |
| **D6** (NEW) | **Accept site-keyed semantic models of named PLR function bodies as a class of hand-maintained fact** — one new registry row against a full `BUDGET_CAP` 24, i.e. a cap conversation | one registry row and a cap raised 24 → 25; the loud half must be a published count (`n_check_args_decided`, `n_assert_resources_decided`) rather than an import-the-symbol measure, because that measure cannot see PLR renaming a local; C15's absence rule becomes a soundness precondition for both rules | **the increment's own gate becomes unwinnable** — `scope_verdict` stays `UNKNOWN` on all 544 operations and the increment is measured against §16.10.2's conjunctive NO-GO-side criterion instead | **YES.** It is the single fact **both** the repaired D2 and D5b need, so asking twice would be dishonest. It is genuinely **not** HM-25's kind — every entry there is keyed on a *shape*, and `why_not_derived` says so in those terms (`plr-sema/src/plr_sema/_hand_maintained.py:563-565`) — so filing it as a ceiling unit would be the cheaper-looking and wrong answer. Its anti-gaming property is strong: each rule is keyed on one `(qualname, lineno)` pair and its reach is a published integer. **Total cost ~250 LOC across T48 and T49**, and it is the only way the headline lands this increment |

---

## 16.16 Implementation record

*(Column shape mirrors increment 5 §14.17 and increment 6 §15.15. No row is started; the whole table is
prospective. First-column ids are deliberately unbolded so the cross-reference lint's task-row pattern
does not read this table's cells as gate cells.)*

| row | commit | what landed | measured vs the spec's expectation | divergences |
|---|---|---|---|---|
| T40 | — | — | — | — |
| T41 | — | — | — | — |
| T42 | — | — | — | — |
| T43 | — | — | — | — |
| T44 | — | — | — | — |
| T45 | — | — | — | — |
| T46 | — | — | — | — |
| T47 | — | — | — | — |
| T48 | — | — | — | — |
| T49 | — | — | — | — |

---

## 16.17 Round-1 disposition

**Round 1 was `praxia:spec-challenger` (C1–C26) against `praxia:spec-defender` (adjudication per
objection plus six defender-identified gaps D-G1–D-G6), both at Opus, both against spec_version 1 at
commit `7893168a`. Verdict on both sides: `needs_revision`.** The challenger filed 5 blockers, 14
must-fix, 6 should-fix and 1 note; the defender conceded 13 outright, ruled 13 partial and rebutted
none cleanly. **Two objections were reproduced by measurement rather than by argument**: C1's
arithmetic at the pin, and C5's traceback order, which the orchestrator confirmed by running Python
(frames outermost-first; the re-raise site at index 1 and the backend frame last).

This table records what each objection did to the text. "CONCEDE" means the remedy is now normative
here; "PARTIAL" means the diagnosis was accepted and the remedy or the costing was replaced; "REBUT"
means the text did not change on the merits.

| id | class | disposition | what changed | § touched |
|---|---|---|---|---|
| **C1** | blocker | **PARTIAL** — arithmetic conceded, costing replaced | The general-model refusal is **withdrawn**; §16.1.1 shows `params ⊆ default` decides `:375` by value and `has_var_keyword` decides `:383` by scope, needing neither the set-difference term nor the `**kwargs` key set. D5 repriced as D5a/D5b/D5c. **The challenger's "one or two HM-25 units" is rejected**: it is a semantic model of a named PLR function, hence a new row | §16.1.1, §16.15 D5/D6, §16.10.2 |
| **C2** | blocker | **PARTIAL** | The gate keeps its `scope_verdict == SAFE` clause and gains a conjunctive NO-GO-side criterion the increment can genuinely fail. The D5b-**and**-D2 conjunction is now stated explicitly | §16.10.2 |
| **C3** | blocker | **CONCEDE** | **R-DECK withdrawn in full.** `:321`'s shipped record carries no `EnvRef` and `resource` is a `for` target; the site is respecified as a site rule over the caller-bound `resources`. The `≥ 2,458` floor and the `n_clusters → 50` cell are withdrawn. The two productions C3 priced are **not** adopted | §16.1.3, §16.5 (R-DECK deleted), §16.10.3, AC-16.13, T48 |
| **C4** | blocker | **CONCEDE** | Gated floor **2,170 → 2,009**, 2,170 published as target; `guard_env_dependent` and `n_clusters` split 223-certain / up-to-384; `n_clusters` corrected to **53 unchanged** in the certain half | AC-16.9, §16.10.3 |
| **C5** | blocker | **CONCEDE** — the cleanest in the report | `error_frames` is a **list**; F2 excuses on **any** frame with the outermost-PLR-match tie-break; AC-16.8 gains the backend-raise-then-re-raise fixture, which is the case the innermost-frame version could never excuse | §16.7 F1/F2, AC-16.8, T45 |
| **C6** | must-fix | **CONCEDE** | Q-MONO is stated as an **explicit amendment** of increment 6 §15.2 G8(1) and §15.4 A-C3, with the amended wording written out and the increment-6 file added to T43's list | §16.5.5, T43 |
| **C7** | must-fix | **PARTIAL** — invariant conceded, Q-BIND framing dropped | **E-INV** is stated normatively — a production may return a definite value from a ⊤ operand only when argument-independent — with R-CONST and Q-MONO as its two named instances and an AC fixture over the whole production set. It survives Q-BIND's withdrawal because R-CONST needs it either way | §16.5.3, AC-16.5 |
| **C8** | must-fix | **PARTIAL** — premise wrong, conclusion right | G3 constructs no `AnyOf` node; `:409` goes through `_maybe_alpha_emptiness` → `_eval_alpha_existential`. **No target-inheritance sentence is added**; Q-BIND is withdrawn instead (D-G1) | §16.1.2, §16.5.5, AC-16.6 |
| **C9** | must-fix | **CONCEDE** | M2 states normatively that a `caller_args`-resolved name carries origin `"operand"`. **The predicted ~544 swing does not occur** and the reason is written down: `get_strictness()` and the `default` set display do not parse as `Term`s, so neither acquires an entry — `guard_operand_unknown` stays 144 | §16.4 M2, §16.10.3, AC-16.3 |
| **C10** | must-fix | **PARTIAL** | Caller-side position/scope tests key on the **call statement's** lineno in `K`; delegate-below-caller fixture added. **"The prediction fails" is dropped**: `use_channels` resolves through the lineno-independent P3a hook | §16.4 M2, AC-16.3 |
| **C11** | must-fix | **CONCEDE** | The byte-identical claim is scoped to §16.5's rules and AC-16.1's assertion is scoped explicitly to the **T40 state** | §16.2.3, AC-16.1 |
| **C12** | must-fix | **PARTIAL** — injectivity conceded, int-sort clarified | Values are **JSON-encoded**; ints sort numerically, strings lexicographically; a fixture covers a name containing `,` and `=` | §16.2.3, AC-16.1 |
| **C13** | must-fix | **CONCEDE** | `plr_observation` is `None` on the deck-build early return and on any raising read, never partial — the third return site spec_version 1 missed | §16.2.1, AC-16.1, T40 |
| **C14** | must-fix | **CONCEDE** | `deck_resource_names` is specified as the **recursive** extraction (deck name plus every descendant), read off the live tree inside the window | §16.2.1, T40 |
| **C15** | must-fix | **CONCEDE** | The **absence rule**: a row is absent on a non-empty `decorator_list`, a `property`, or a qualname at more than one lineno. It is also D5b's soundness precondition, and it bites on the `@abstractmethod` base | §16.3, §16.5.3, §16.1.1, AC-16.2 |
| **C16** | must-fix | **PARTIAL** — first half conceded, second rejected | The selection's undefined second clause is **deleted**; one closed rule with `n_surface_candidates` / `n_surface_absent_by_c15` / `n_surface_rows`. The harness-side reads stay outside registry scope, now argued from increment 5's `volume_tracking_observed` precedent rather than asserted | §16.3, §16.9 D3 box, AC-16.2 |
| **C17** | must-fix | **PARTIAL** — remedy taken anyway | **One** capture point after `machine.setup()`, inside a fail-closed guard, which also discharges C13 and collapses two normative windows into one | §16.2.1, T40 |
| **C18** | must-fix | **PARTIAL** | The fence checks A-DECK-OBJECT **on the corpus**, not in general; the flattering half alone is removed and AC-16.13 gains a **hand-built** duplicate-name fixture. D2's basis changes, not its sign | §16.1.3, §16.11, §16.15 D2, AC-16.13 |
| **C19** | must-fix | **PARTIAL — blocking half REBUTTED on the evidence** | `scope_trail` **does** record loop headers and such an entry is unsatisfiable under ways (1)–(3), so an in-loop guard can never emit `WILL_FAIL`. **No fourth precondition and no sixth fixture**; one normative sentence in §16.4 and §16.15 Q6 instead | §16.4 D1 box, §16.15 Q6, AC-16.4 |
| **C20** | should-fix | **CONCEDE** | Both identities stated normatively; **one** normalisation helper on both sides; AC-16.8 matches a real `PlrSite` string, not a hand-written tuple | §16.7 F2a, AC-16.8 |
| **C21** | should-fix | **PARTIAL** | `n_quantifier_decided_by_qmono` added, predicted 223 at one site. **The Q-BIND counter is not added**, because Q-BIND is withdrawn | §16.10.1, §16.10.4, AC-16.11 |
| **C22** | should-fix | **CONCEDE, verbatim** | §16.1.1 gains the reconciling paragraph, and the reconciliation is that **increment 6 §15.6 was right** — §16.3 ships the signature derivation §15.6 named as the condition | §16.1.1 |
| **C23** | should-fix | **CONCEDE** | p2a publishes `achieved/attempted` in p1's shape; the floor becomes `achieved == attempted` with `attempted >= 200`, not a bare ≥ 1 | §16.11, AC-16.10 |
| **C24** | should-fix | **CONCEDE** | One lane-asymmetry disclosure covering R-HEAD, R-CONST, Q-MONO and the D6 site rules; §16.11's tier-2b attribution corrected to name all three; `n_resolved_by_rule` published **per lane** | §16.5.6 (new), §16.10.1, §16.11 |
| **C25** | should-fix | **PARTIAL** | The `len(head_channels) == num_channels` cross-check moves to the harness in AC-16.1; **keeping R-ATTR is an explicit sub-note under D4**. The ask is unchanged, because D4 buys one unit for the pattern and not one per instance | §16.5.2, §16.15 D4, AC-16.1 |
| **C26** | note | **PARTIAL** | T42's T41 dependency **dropped**; the D1-decline withdrawal list stated exactly (files and ~50 LOC); one sentence of argument apiece for the `pred`-aware `BRANCH` and the tuple display | §16.13, §16.14 |
| **D-G1** | defender gap | **CONCEDE** | **Q-BIND withdrawn in full** as dead machinery — `:409` never reaches `_eval_allof_anyof`. Removes ~50 LOC from T43, an additive field from three wire nodes, a `parse` change, and one counter | §16.1.2, §16.5.5, §16.10.3, AC-16.6, T43 |
| **D-G2** | defender gap | **CONCEDE** | The gate needs D5b **and** a repaired D2; the conjunction is stated in §16.10.2 and the two asks are merged into **D6** | §16.10.2, §16.15 D6 |
| **D-G3** | defender gap | **CONCEDE** | The deck observation enters `env` as `obs:deck_resources=<digest>`, so a D6-enabled verdict is a function of the fifth `cache_key` component and §16.6's claim (4) stays true | §16.2.3, §16.5, AC-16.13 |
| **D-G4** | defender gap | **CONCEDE** | `scope_verdict` is threaded into `unknown_ledger.py` under T46, so the ledger can audit the number §16.0.1 makes the sole GO criterion | §16.10.1 block (7), T46 |
| **D-G5** | defender gap | **CONCEDE** | T46 re-runs and republishes `t30_measure`, **or** its prediction role is recorded as retired for the `AllOf`/`AnyOf`, `Filtered`-emptiness and membership classes — the report must say which | §16.10.1 block (8), AC-16.11, T46 |
| **D-G6** | defender gap | **CONCEDE, and it is D5b's strongest argument** | Both `_check_args` guards carry `reachability_clear` false and `fires is False` returns `SAFE` unguarded by depth, so the discharge is **one-directional by construction** and needs no interaction with D1 | §16.1.1, §16.15 D5/D6, T49 |

**What round 1 did NOT change.** D1's recommendation (YES) and D4's (YES) are unchanged; D3 survives
as a non-decision; `REASON_VOCABULARY` stays 12 of 12 and no thirteenth member is proposed; §16.6's
`scope_verdict` representation and §16.7's decision to publish two counters rather than replace one are
untouched; and the refusal to put `:375`/`:383` into `excludes_sites` — the move that would have bought
the headline for free — stands, and stands for the same reason.

**The two numbers that moved most.** The headline went from *unreachable* to *reachable under one
decision*, and the cost of reaching it went from ~350 LOC attributed to `_check_args` alone to ~250 LOC
across two site rules — both because C1's arithmetic was right and spec_version 1 priced the wrong
direction.

---

## References

- Main specification (amended): `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` — §3.2's join
  table (`:574-581`), the deferred rows (`:2514-2524`, with (c) at `:2518`, (e) at `:2520` and (f) at
  `:2524`), the boundary summary (`:2526-2534`), and Open decisions 3's additive direction
  (`:3316-3345`).
- Increment 1: `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md` — §10.6.3's named
  assumption table (`:744-754`), which A-DECK-OBJECT would extend from four rows to five, and
  A-COMPLETES (`:752`), which §16.6 names as the claim `scope_verdict` does **not** make.
- Increment 3: `.praxia/docs/specs/260903_plr-sema-real-programs-increment.md` — §12.3.6 B2, the
  `pred`-aware `BRANCH`, still deferred.
- Increment 4: `.praxia/docs/specs/260903_plr-sema-families-cache-increment.md` — §13.1 (the lid
  disposition, unchanged), §13.12 (the general dataflow pass §16.3's `constant_return` shape test and
  §16.4's map both decline).
- Increment 5: `.praxia/docs/specs/260903_plr-sema-volume-increment.md` — §14.6 in full
  (`:602-741`), the precedent every legitimacy argument in §16.2 is stated against: the
  conditional-guard rule (`:619-636`), R1 (`:638-673`), the two failed `is_disabled` discharges
  (`:675-689`), the `env` argument (`:691-698`), and O5's observed-inside-the-window,
  returned-by-the-executed-side rule (`:700-723`).
- Increment 6: `.praxia/docs/specs/260904_plr-sema-predicate-increment.md` — §15.1's tiers, §15.2's
  grammar and G7/G8, §15.3's α/β, §15.4's `E-CALL`/`E-TYPE`/`E-SCOPE`/`E-UNCOND`/`E-ENV`, §15.5's Q1
  and the unmodified fence, §15.6's Q2 defer, §15.7's ordered reason procedure, §15.8's registry
  arithmetic, §15.9's gate and anti-gaming box, §15.12's sizing of the delegate map, §15.13's five
  refused productions with their reopening conditions, and §15.16.3 R1, whose review is owed and is
  restated in §16.15 Q6.
- The instrument: `outputs/plr-sema/unknown_ledger_260909_after.json`, with
  `outputs/plr-sema/oracle_replay_260909_inc6.json`,
  `outputs/plr-sema/predicate_mutants_260909_inc6.json` and
  `outputs/plr-sema/t30_measured_260908.json` as companions.
- The shipped contract table, read directly for the three guard records round 1 turns on:
  `plr-sema/data/derived_contracts.json` — `:321`'s predicate, empty `bindings` and two-entry
  `scope_trail` at `:88795-88822`; `:375`'s `reachability_clear` at `:88862-88879`; `:383`'s recorded
  enclosing scope entry at `:88880-88913`.
- Round 1: `.praxia/docs/audits/260909_plr-sema-observation-round1-challenger.md` (C1–C26) and
  `.praxia/docs/audits/260909_plr-sema-observation-round1-defender.md` (the per-objection
  adjudication, the six defender gaps D-G1–D-G6, the post-round decision table including the new D6,
  and the 14-step ordered remediation list this revision follows). §16.17 records the disposition of
  every objection.
