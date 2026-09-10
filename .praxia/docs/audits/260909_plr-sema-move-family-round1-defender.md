---
title: 'plr-sema increment 8 (the move_* family, spec_version 1) -- adversarial round 1, defender'
description: 'Defender pass (praxia:spec-defender, Opus) against the round-1 challenger''s C1-C21: 11 conceded (C2 K is always entry_K captured at depth 0, 142 of the certain 173 never bind; C8 Resource._state_updated does contain a recordable serialize_state call and M-INH would resolve it against the overridden base; C9 the base-name extractor is not shipped; C11 M-INH perturbs depth benchmark-wide; C12 scope entries share the same evaluator so D11''s kind-argument is architecturally false; C13 caller_args wire-shape underspecified; C14 the amended predicate-position clause does not ride HM-25''s measured probe; C16 arm_slots stability precondition unstated; C17 lane qualification missing from SS17.8.3; C18 eleven _check_args call sites not ten, :2364 omitted; C19 the per-operation ground truth is the ledger''s collision_ops block, undisclosed), 9 partial (C1 real failure is C2''s not M1 clause 4; C3 LIFO-depth trace independently reproduced and correct but the third candidate cause for the 148 is falsified; C4 the try/except contradiction is real but closes with a derived handler-terminator rule, no new assumption; C5/C6/C7/C15/C20 correct remedy, wrong or overstated premise), 1 rebutted outright (C10 -- the typestate emits WILL_FAIL via tipstate.py''s own consumed-index replacement with no depth gate at all, so p3a''s denominator is 93 not 31), C6 also largely rebutted on the same fact. Overall verdict: needs_revision, not un-deliverable -- the challenger''s claim that gate condition (1) fails on all 93 as written is independently reconfirmed (C4 forces it on 93, C2/C3 force it on 62), but every fix is derivable and confined to SS17.1.4, SS17.5.1(b), SS17.4.3 condition 2, SS17.7''s registry accounting, and SS17.8.2/SS17.8.3.'
status: final
task_id: 260909_sema-move-family
date: '260909'
---

> Persisted verbatim by the orchestrator from the defender agent's final report (no write tool).
> Target: `.praxia/docs/specs/260909_plr-sema-move-family-increment.md` (spec_version 1, draft),
> challenger: `.praxia/docs/audits/260909_plr-sema-move-family-round1-challenger.md` (C1-C21, `not_ready`).
> Worktree `/home/marielle/projects/praxis/.claude/worktrees/wt-20260909-172820`, branch
> `plr-sema-inc8-move-family`. Every citation below was independently re-verified this pass.

## Summary verdict

Eleven objections concede outright, nine are partial, one is rebutted. **The challenger's central
structural claim — that gate condition (1) is predicted to fail on all 93 move_* operations as currently
specified — is CORRECT and independently reconfirmed**, but it is carried by two causes rather than four,
and both have targeted fixes derivable from source already in hand. C3's LIFO-depth trace is right
(independently re-traced `move_resource`'s real sorted delegate list, confirming `_check_args` lands at
depth 2, and `move_lid` at depth 3), corroborated by the fact that the 223 operations that DID flip under
D6 are exactly `pick_up_tips`, whose `_check_args` sits at depth 1 with a single call site. **C2 is the
true blocker**: `derive_contract` computes `compute_caller_args(entry_K, K)` and `_find_delegate_call`
scans only the entry point's own body, so 142 of the "certain 173" never bind at any depth. C4 is a
genuine internal contradiction between §17.4.3's widening condition 2 and §17.8.3.

Against that, **C10 is rebutted outright** and **C6 is largely rebutted**, on the same shipped fact the
challenger did not read: increment 1's typestate — which §17.4 explicitly adopts as its template and whose
files T52 modifies — decides guards through `tipstate.py`'s own `_null_check`/`atom_truth`/
`_finding_for_atom` path with a `consumed`-index replacement, never through `_resolve_env_ref` or
`_eval_is`, and `_finding_for_atom` emits `WILL_FAIL` with no depth gate at all. So no fifth `EnvRef` path
shape, no broadened `_eval_is`, no short §17.7 accounting, and no 31-operation cap on p3a's denominator.
C3's proposed third cause for the 148 is also falsified: none of `aspirate`, `dispense` or `drop_tips` has
a sibling delegate that calls `_check_args`.

**`spec_version 2` is required, but the surgery is confined to §17.1.4's fence table, §17.5.1(b),
§17.4.3's condition 2, §17.7's registry accounting, and §17.8.2/§17.8.3** — the instrument, the
identical-residual observation, the `unresolved_delegate` diagnosis, the `:375` arithmetic, and the
E-TYPE refusal all survive intact.

---

## Point-by-point

### Conceded

**C2 — conceded.** `derive_contract` (`plr-sema/src/plr_sema/derive/__init__.py:640-651`) calls
`compute_caller_args(entry_K, K)` with `entry_K` captured once at depth 0. `_find_delegate_call` scans
`K.body` only (`bindings.py:884-886`). `move_lid`'s body contains exactly two self-calls, `_log_command`
at `:2415` and `move_resource` at `:2427`. Lifting the depth restriction therefore binds nothing for
`move_lid`, `move_plate`, `transfer`, `discard_tips` or `stamp` — 142 of the 173 the spec calls "certain".
§17.5.1(b) says "the argument at the call site" without ever saying whose body the call site is in, and
the shipped signature answers: the entry point's.

**C8 — conceded.** `resource.py:934` is `callback(self.serialize_state())`; `serialize_state` is defined
on `Resource` at `:838`; `visit_Call` calls `generic_visit` at `survey_plr_preconditions.py:300`, so the
inner call is visited and `survey:291-292` records it as a delegate. §17.1.1's stated ground is false at
its own cited lines. The override at `liquid_handler.py:214-237` is real and no fail-closed condition
covers it. Mitigation: `LiquidHandler.serialize_state` also carries no raise and no assert, so the
"zero guards" number in §17.8.3 survives — the defect is a missing condition, not a wrong cell.

**C9 — conceded.** `subclass_closure_from_bases` has exactly three callers in the repo, all in
`tests/test_predicate.py`, all with hand-built fixture maps. Nothing extracts `ClassDef.bases` anywhere in
plr-sema. "Already shipped" is overstated in precisely the place a wrong resolution enters.

**C11 — conceded.** `_walk_closure` pushes `rec.delegates_to` (`derive/__init__.py:456-459`), the survey
emits it as `sorted(set(...))` (`survey:338`), and depth gates `caller_args`/`caller_reachability_clear`/
`caller_scope_trail` (`derive/__init__.py:640-651`) and D1's `WILL_FAIL` lift (`predicate.py:1092-1109`).
Adding `_state_updated` to `pick_up_resource`'s and `drop_resource`'s `delegates_to` changes the sorted
list, hence push order, hence pop order, hence depth — confirmed by trace that `Resource._state_updated`
itself already carries `serialize_state` in `delegates_to`. `InlinedGuard.depth` is already on the wire,
so publishing the per-guard depth multiset before/after is cheap.

**C12 — conceded.** `_scope_entry_value` evaluates trail entries through the same `evaluate_predicate`
with the same `ctx` (`predicate.py:1011-1025`), and `scope_excludes` runs at `evaluate_guard:1442-1444`
before the site rule at `:1446`. Two of the four mechanisms this increment takes can themselves produce
`F` inside a scope entry: the amended `Seq`-truthiness clause and the typestate's `Is` decisions. D11's
real ground is that an exactness field is a derived TYPE claim over a corpus this increment cannot audit
and that it clears six sites at once — not a difference in kind.

**C13 — conceded.** All three consumers call `.get(...)` on a `Mapping`: `caller_args.get("method")`
(`predicate.py:1199-1208`), `caller_args.get("default")` (`:1222-1231`), and
`_Ctx.caller_args=guard.get("caller_args")` (`:1431`). A list has no `.get`. §17.5.1(a) specifies the
consumer's tolerance and never names the producer's wire field.

**C14 — conceded.** HM-25's tenth unit is booked for "an `EnvRef` path admitted against the observation
record" and its probe imports and exercises `_resolve_env_ref`, "the ONE symbol implementing all three
rules" (`_hand_maintained.py:350-362`). R-ARM lands inside `_resolve_env_ref` (`predicate.py:336-356`) and
genuinely rides the unit. The amended predicate-position clause lands in `evaluate_predicate`
(`:934-944`), which no HM-25 probe imports or exercises. D7 is recommended YES on HM-25's LOUD-failure
property, and that property does not extend to the one evaluator rule the increment adds.

**C16 — conceded.** `liquid_handler.py:176` initialises `self._resource_pickups: Dict[int,
Optional[ResourcePickup]] = {}`; the setter at `:183-185` is `self._resource_pickups[0] = value`, which
CREATES key 0 in an empty dict; `setup` rebuilds it wholesale at `:212` and the capture point sits after
that. The completeness declaration needs a stability property — the key set is fixed for the whole
program after the capture point — which is true at this pin for `num_arms >= 1` and is nowhere stated.

**C17 — conceded.** Increment 7 §16.5.6 is normative for exactly this class of rule ("The graph lane has
no harness and no observation, so every rule declines … a lane asymmetry in the verdict itself",
`260909_plr-sema-observation-increment.md:1127-1140`). §17.8.3's table carries no lane qualification while
§17.9's tier-2b box does disclose. A one-word header plus one sentence per row.

**C18 — conceded.** Independently counted: `self._check_args(` occurs at `liquid_handler.py:541, 687,
1037, 1238, 1481, 1559, 1745, 1895, 2079, 2345` and `2364` — ELEVEN. §17.5.1's "All ten" omits `:2364`,
the site whose distinct `default={"drop"}` the per-call-site fold argument depends on.

**C19 — conceded.** The fifteen-finding list is read from `collision_ops`
(`unknown_ledger_260909_final.json:2174` onwards), whose neighbouring key is `n_row_id_collisions: 12`
(`:2173`). Content agrees with the replay's residual set (compared against `oracle_replay.json:245`).
Concede the provenance fix and the publish ask.

### Partial

**C1 — partial.** The conclusion (`:383` does not reach 62 of 93) is correct but misattributed: the spec
never proposes propagating kwargs through the `move_resource` unpacking hop at all; `_eval_check_args_
strict_site_rule` reads only `ctx.caller_args`, which is unavailable at the guard for `move_lid`/
`move_plate` for the same reason C2 names. Remedy is C2's, not "a fourth relaxation of M1".

**C3 — partial.** Independently re-traced and confirmed: `move_resource`'s self-calls sorted give
`['_check_args','_log_command','drop_resource','move_picked_up_resource','pick_up_resource']`; LIFO pops
`pick_up_resource` first, pushing `_check_args` at depth 2 (its call at `:2079`), popped before the
depth-1 entry beneath it — so `_check_args` lands at depth 2 for `move_resource`, depth 3 for `move_lid`/
`move_plate`. Corroboration: `pick_up_tips` has no sibling delegate calling `_check_args`, so it sits at
depth 1 — exactly the 223 that flipped under D6. BUT the proposed third candidate cause for the 148 is
falsified: `aspirate` (`:945/:956/:1037`), `dispense` (`:1135/:1150/:1238`) and `drop_tips`
(`:637/:664/:687`) each have no sibling delegate calling `_check_args`, so the LIFO artifact explains
nothing about the 148 and should not enter §17.1.4's open-diagnosis box.

**C4 — partial.** The contradiction is real: the rollback at `:2091` is inside the `try` at
`liquid_handler.py:2085-2092`, and `:2094`/`:2120`/`:2147` are all after it, so condition 2 puts them at
TOP while §17.8.3 predicts SAFE on 93 — both cannot hold, and this alone makes the gate fail on all 93.
But the rescue is derivable, not an assumption: the handler's terminator is `raise e` (`:2092`), and
`isinstance(handler.body[-1], ast.Raise)` is a pure AST shape test of the same class §17.4.2's absence
rule already uses. No new named assumption needed; ~5 LOC.

**C5 — partial.** Structurally confirmed (`derive_contract` emits `rec.findings` once per key; the
proposed walk assigns positions to call statements, and `_check_args`/`_state_updated` each execute at
more than one position in the move family). But at the pin none of the three anchor-reading guards
(`:2070`, `:2120`, `:2147`) sits in a multiply-called function — each has exactly one call site. Correct
as a soundness-hardening ask, not pin-blocking. Downgrade to must-fix.

**C6 — largely rebutted.** The premise is false: increment 1's typestate — §17.4's own named template,
whose files T52 modifies — does NOT route through `_resolve_env_ref`/`_eval_is`. `evaluate_call`
re-parses the guard's own condition string (`_parse_atom`, `tipstate.py:387-401`), matches via
`_null_check` (`:372-384`), applies `atom_truth` (`:442-452`), and emits a `Finding` directly via
`_finding_for_atom` (`:455-472`), recording `consumed` indices so the ordinary predicate emission is
skipped one-for-one. No fifth `EnvRef` path shape needed; no new `Is`-position rule needed; §17.7's
accounting is not short by one; the "obvious repair" of broadening `_eval_is` is not proposed and not
needed. `atom_truth` reads the STATE, never the payload, so "the payload never affects the three guards'
truth" is exactly increment 1's shape. What survives: one missing normative sentence naming the route,
plus `n_typestate_decided` in block (3).

**C7 — partial.** The completeness claim is uncited and unsupportable as stated, and it is wrong in both
lanes, not just the graph lane (`ir.py:577-590` graph, `:798-802` tier 1, `param_names=None` documented as
"trust nothing — fail-closed default" at `:390-391`). BUT the renaming half (`?<i>` keys) fails SAFE, not
unsafe — a synthetic key is never a declared parameter, so the residual `Seq` is spuriously non-empty and
the rule declines to ½. The genuine false-SAFE channel is an un-modelled keyword absent from `arguments`
entirely, which the challenger asserts without citation. Remedy stands in full; `lower_kwargs`'s existing
`Widen(reason=_ARGUMENTS)` (`ir.py:600-601`) gives the precondition a shipped signal to hang on.

**C15 — partial.** Premise is false: `_measure_hm25` returns `len(shape_matchers) + len(productions)`
(`_hand_maintained.py:434`), a mechanically computed count, not a hand-written integer — the STOP
contingency IS checkable via the `measure() <= declared` ratchet. The surviving half is right:
`_typestate_anchor` is already in `shape_matchers` (`:415`), so a P5 implemented as its variant adds no
new symbol and the eleventh unit passes the ratchet vacuously — it must name a distinct symbol.

**C20 — partial.** The citation complaint is narrower than stated: `predicate.py:1047-1057` is
`_entry_satisfies_uncond`, and `guard_is_unconditional` begins at `:1060` — but ways (1)-(3) genuinely
live at the cited lines. Wrong function label, right line range, not a dangling reference. The
substantive half is fully correct: `scope_trail` is a `PreconditionFinding` field, no call statement
carries one, and `caller_scope_trail` exists only at `depth == 1`. Concede the fix and T52's re-size.

**C21 — partial.** The headline is correct and independently confirmed, but over-determined by two causes
rather than four. C4 alone forces the residual to eight (on all 93); C2/C3 alone force it on 62. C1 is
subsumed by C2. C10 contributes nothing (rebutted). So: revise the mechanisms, not "cannot deliver a
meaningful gate". The underlying arithmetic is intact — re-verified that `chatterbox.py:223-231`'s
`pick_up_resource(self, pickup)`/`drop_resource(self, drop)` declare no `**backend_kwargs`, so
`params ⊆ default` holds at both `:2345-2350` and `:2364-2369` and the site rule would return `F` at each,
once the plumbing to those two sites is fixed.

### Rebutted

**C10 — rebutted outright.** `_finding_for_atom` (`tipstate.py:455-472`) returns `Verdict.WILL_FAIL` on
`truth == "T"` with no depth argument and no call to `guard_is_unconditional`; `evaluate_call` records
`consumed` indices so `check/__init__.py` skips the ordinary predicate emission one-for-one.
`guard_is_unconditional`'s `depth >= 2` refusal governs the path the typestate REPLACES. The mutable
population for `p3a` is the full 93, not 31 — the challenger's own remedy would have written a wrong
denominator into §17.9.

---

## What must change in remediation (spec_version 2)

1. **§17.4.3 condition 2 (C4).** Replace with a derived handler-terminator shape test
   (`isinstance(handler.body[-1], ast.Raise)`), no new named assumption, ~5 LOC.
2. **§17.5.1(b) / §17.1.4 / §17.8.3 (C1, C2, C3).** State normatively what `K` is at depth ≥ 2. Either
   fold over every admitted call site of `D` across the closure (real new traversal machinery, resizing
   T53 beyond ~200 LOC), or restate `:375`/`:383` as `move_resource`-only (31 operations) and restate the
   gate over the non-uniform residual that results. Re-derive the fence table from the actual traversal,
   not from source-reading; drop the falsified third candidate cause for the 148.
3. **§17.4 (C6, C10).** Add the one normative sentence naming the tipstate-replacement route (no
   `EnvRef`/`_eval_is` involvement), and `n_typestate_decided` in block (3). Correct `p3a`'s mutable
   population to the full 93.
4. **§17.7 / D7 (C14, C15).** Either extend HM-25's probe to exercise the predicate-position clause, or
   book it as an eleventh unit with a symbol distinct from `_typestate_anchor` (D7 becomes 10 → 12).
5. **§17.2 / T50 (C9, C11).** Specify the base-name extractor and its fail-closed shapes; publish the
   per-guard depth multiset before/after, not just closure size and guard count.
6. **§17.1.1 / AC-17.1 (C8).** Correct the stated ground to "zero guards" (not "no recordable call"); add
   a fourth fail-closed condition for an inherited body whose self-call is overridden downstream.
7. **§17.3 / AC-17.2 (C16).** State the arm-dict key-set stability property as the completeness
   precondition explicitly.
8. **§17.5.2 / AC-17.5 (C7).** State completeness as a precondition per lane; decline on any `?<i>` key
   or absent `param_names`.
9. **Mechanical fixes (C13, C17, C18, C19, C20).** Name the `caller_args` wire-shape change; add the
   "tier 1" lane qualifier to §17.8.3's table; correct "ten" to "eleven" `_check_args` call sites and add
   `:2364`; name the `collision_ops` provenance of §17.0.1's ground-truth block; fix the
   `_entry_satisfies_uncond` vs `guard_is_unconditional` citation label.
10. **§17.1.5 / D11 (C12).** Restate the argument on its true ground (a derived type claim this increment
    cannot audit, clearing six sites at once) and add a tenth published block: `n_scope_excluded` per
    site, before and after.

What survives untouched: the instrument and its measured facts, §17.0.1's identical-residual observation,
the `unresolved_delegate` diagnosis and its cheap closure (M-INH, once C8/C9's fail-closed condition is
added), the `:375` site-rule arithmetic itself (once its plumbing is fixed), and the E-TYPE refusal
(D11, recommended NO) on soundness grounds.
