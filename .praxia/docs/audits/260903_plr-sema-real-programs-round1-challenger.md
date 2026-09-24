---
title: 'plr-sema real-programs increment — adversarial round 1, challenger'
description: 'Challenger report on .praxia/docs/specs/260903_plr-sema-real-programs-increment.md (spec_version 11 draft, 8868b34e): O1 BLOCKER tier 2b names plan_call as the per-iteration recorder but plan_call is index-keyed to call_sequence and is never invoked when a fixture coroutine executes directly; O2 BLOCKER the trip=0 fixture (body never visited) contradicts AC-6.4(amended)/AC-7.2/AC-12.13 equality over non-REGION ops; O3 MAJOR stale increment-2 "CALL followed by region open => widen" compensation mis-widens unrelated calls once real headers exist; O4 MAJOR the extractor must become body-scoped and _active_states must be arm-scoped; O5/O6 MINOR (unused FOREACH/CONDITIONAL enum members; load_state path missing from the assumption table). Verdict: not implementable until O1/O2.'
status: final
task_id: 260903_sema-real-programs
date: '260903'
confidence: high
sources: 'praxia:spec-challenger (claude-sonnet-5); code read directly (ir.py, check/__init__.py, tipstate.py, receiver_state.py, oracle_common.py, verifier.py, dispatcher.py, models.py, computation_graph_extractor.py, PLR liquid_handler.py/tip_tracker.py at pin dd79c4c89, branchy_graph.json). Persisted verbatim by the orchestrator: the challenger agent type has no write tool.'
---
# plr-sema real-programs increment — adversarial round 1, challenger

Target: `.praxia/docs/specs/260903_plr-sema-real-programs-increment.md` at `8868b34e`. Verbatim report.

---

### O1 — BLOCKER — tier 2b's executed-ground-truth recording mechanism does not exist and is self-contradictory as specified

**Location:** §12.4.2 (lines 593-626), "Execution mechanics" paragraph (618-621); §12.5's oracle table row "a proved trip count is the real trip count" and "min(trip,K) unrolled iterations are real executions"; AC-12.17; the T21 task row's claim "this is the increment's only executed soundness evidence for regions."

**Issue:** §12.4.2 states the fixture source is executed **directly as a coroutine, "not replayed as a call sequence — that is the entire point,"** and in the very next paragraph claims: *"The per-iteration record comes from the same `plan_call` wrapper tier 1 already uses, extended with a monotonically increasing visit counter per call site."* These two sentences are mutually exclusive given the actual code. `plan_call` (`training/verify/dispatcher.py:92`, `def plan_call(call: Mapping[str, Any], index: int, setup, *, strict: bool) -> PlanResult`) and its caller `_execute` (`training/verify/verifier.py:47-51`, `for i, call in enumerate(call_sequence): plan = plan_call(call, i, setup, strict=strict)`) are **structurally bound to `call_sequence` iteration** — `plan_call` takes a JSON `call` dict and its **list index**, not a live Python call site. `oracle_common.py`'s existing recording mechanism (`recording_plan_call`, lines 144-153) works by monkey-patching `verifier.plan_call`, which is only ever invoked from inside `_execute`'s `call_sequence` loop.

If a fixture is executed as a native coroutine (`await protocol_fixture_fn(lh, tip_racks, plate)`, with the fixture's own `for`/`while` doing real Python control flow and calling `lh.pick_up_tips(...)` directly), `verifier.plan_call` is **never invoked at all** — there is no `call_sequence`, no `index`, nothing for `recording_plan_call` to wrap. "The same `plan_call` wrapper... extended with a visit counter" names a real function whose signature and call site are incompatible with the execution mode the paragraph just described.

**Counterexample:** Take T21's own `for`-fixture (a loop that fails at iteration 2). Under §12.4.2's stated mechanics, executing it directly means PLR's `HasTipError` is raised from inside real Python `for` iteration 2, inside `_execute`(...)-free code. Nothing records "operation X, iteration 2" for that raise, because the only existing recording path (`plan_call`) is dead code on this execution path. AC-12.17's assertion — *"the comparison keyed on `(operation, iteration)`"* — has no producer for the executed side of that key.

**What must change:** Either (a) name a real instrumentation mechanism — e.g., monkey-patching the PLR methods themselves (`LiquidHandler.pick_up_tips` et al.) with a call-site visit counter, independent of `plan_call`/`dispatcher.py` — and specify how it maps a wrapped method call back to the *graph operation id* the static side uses for the same call (since without `call_sequence`, there is no `index` to correlate against `lower_graph`'s `origin` map at all); or (b) concede that tier 2b requires a genuinely new recording layer, size it as its own task, and downgrade T21's current ~460 LOC estimate accordingly. Since T21 is named as "the increment's only executed soundness evidence for regions," and §12.9 item 5 conditions the *deletion* of AC-11.11/AC-11.13's fixture-only qualifiers on T21 passing, this is the single highest-leverage defect in the document.

---

### O2 — BLOCKER — the AC-12.6 trip=0 exploit is incompatible with AC-6.4(amended)/AC-7.2/AC-12.13's totality guarantees

**Location:** §12.2.3 (338-342, "trip = 0 is a legal proved value"), AC-12.6 (778-784), §12.3.4's AC-7.2 restatement (492-496), AC-12.13 (821-826).

**Issue:** §12.2.3 says a `trip == 0` loop is "walked once under §12.3's unroll-`min(trip,K)` rule with `min(0,K) = 0` iterations, i.e. the body contributes no findings and no state change" — the walk **never visits** the body's `CALL` pcs. But the body's operations are real, non-`REGION` `OperationNode`s in the graph, so they are members of `{op.id for op in graph.operations if op.node_type is not GraphNodeType.REGION}` — precisely the set AC-6.4 (as amended by §12.3.4) requires `{f.operation_id}` to **equal**, and that AC-12.13 restates verbatim as its own totality/equality check "for... every region fixture." A body op that is never visited receives zero findings, so it can never appear in `{f.operation_id}`. The two sets cannot be equal whenever a proved-trip-0 region has a non-empty body.

§12.3.4's own AC-7.2 discussion tries to address this ("A region whose proved trip is `0` does not [pay for its header]... so the totality inequality is asserted on the call-bearing count there too") but this sentence only rescues the **inequality** direction of AC-7.2, and only if the denominator itself is read to exclude the never-visited body ops too — which the literal set comprehension (`node_type is not REGION`) does not do. It does not touch AC-6.4's **equality**, which AC-12.6's own fixture — described as producing "zero findings and no state change," a claim that is only a meaningful, stub-defeating assertion if the trip-0 loop actually contains a state-mutating operation (otherwise "no state change" is vacuously true of an empty body and the AC tests nothing) — directly violates.

**Counterexample:** `range(0)` loop containing `pick_up_tips(use_channels=[0])`. Lowering: `LOOP(trip=0)`, `CALL pick_up_tips`, `END`. Walking: `min(0,8)=0` visits → the `pick_up_tips` `CALL`'s pc is never reached → zero findings for it → its `op.id` is absent from `{f.operation_id}` but present in `{op.id : node_type != REGION}` → AC-6.4 (amended) fails on this exact, spec-mandated fixture.

**What must change:** Either (a) explicitly except proved-trip-0 regions' body operations from AC-6.4/AC-7.2/AC-12.13's call-bearing set (and say so in the amendment text, not just in the AC-7.2-specific aside), or (b) require the walk to visit a trip-0 region's body exactly once anyway, purely to discharge totality, while suppressing any findings/state effects from that visit (a "totality-only dry visit") — which is a real design decision this document currently makes silently by omission. As written, a fixer who takes AC-12.6 literally (a trip-0 loop with a real body, to make "contributes zero findings" non-vacuous) breaks AC-6.4/AC-12.13 on that very fixture.

---

### O3 — MAJOR — a stale increment-2 compensation ("CALL immediately followed by a region open") silently mis-widens unrelated calls once real region headers exist

**Location:** `plr-sema/src/plr_sema/check/__init__.py:462-478`, specifically the guard at 477-478 and its docstring (464-476); §12.2.2's rejection of "attach region fields to the first call" (300-307); T20's task row (879) — never mentions this code.

**Issue:** The existing `check_ir` contains a compensation for increment 2's *old* region shape (an operation that carries its own `foreach_source`/`condition_expr` and therefore gets a `CALL` immediately followed by the region it opens): `if pc + 1 < n_instr and isinstance(bytecode.instructions[pc + 1], (ir.Loop, ir.Branch)): walk.widen(instr.receiver)`. Its own docstring states the justification explicitly: *"always the operation that CARRIES the `foreach_source`/`foreach_body` or `condition_expr` that opened it."*

§12.2.2 **eliminates** that shape for real data: region headers are now separate, `CALL`-less `OperationNode`s (`method_name==""`). Once real regions exist, "a `CALL` immediately followed by a `LOOP`/`BRANCH`" is no longer *necessarily* the region's owner — it is true whenever the loop/branch simply happens to be the **next statement** after an unrelated call, which is the common case (`lh.setup()` directly before a `for` loop; any call at the end of a straight-line preamble before a loop). The compensation would then widen that unrelated call's own receiver **before its own guards are evaluated** — corrupting that call's own SAFE/WILL_FAIL verdict into a spurious `UNKNOWN`, silently.

I traced whether this actually breaks AC-12.10 (whose fixture puts `setup()` directly before the loop): it does not, *by coincidence* — E6's reset (§12.1.4) unconditionally overwrites the receiver's whole `ChannelState` **after** the pre-widen runs (both happen inside/around the same `CALL`'s evaluation, and E6 runs last), so the stray widen is masked for `setup()` specifically. But nothing guarantees every region fixture built for AC-12.11/AC-12.12/AC-12.14 puts a self-overwriting reset immediately before the region; any fixture that puts an ordinary tip-state-relevant call directly before a loop/branch it does not own will silently lose precision on that call, and **no AC exercises this configuration** — every named fixture (AC-12.10/11/12/14) is free to (and, per the traced AC-12.10 case, does) dodge it via adjacency to `setup()`.

**What must change:** T20's task row must explicitly name removing or reworking this compensation (it needs to be restructured wholesale anyway to support L1's re-visitation, so folding this in is not extra scope — but the spec should say so, since otherwise a minimally-invasive patch that "adds L1/L2/L3" on top of the existing pass would leave this stale and wrong). Add a fixture where an ordinary tip-state call directly precedes an unrelated region it does not own, and assert that call's own guard evaluates against its real pre-call state, not `TOP`.

---

### O4 — MAJOR — the extractor's region-header emission is described as a producer for an existing consumer, but requires restructuring a flat single-pass visitor into a body-scoped one, and the interaction with existing branch-arm state tracking is unaddressed

**Location:** §12.2.2's normative rule (283-292); `praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:376-389` (`visit_For`/`visit_While`/`visit_If`, currently flag-only, return `True` to continue the *same* flat traversal), `:456-517` (`visit_Call`, unconditionally appends `op_id` to `self._execution_order` at line 515 and mutates `self._active_states` at lines 479-491 with no notion of "current region/arm").

**Issue:** §12.2.2 frames this as "a producer for a consumer that already exists" (271) — true of `lower_graph`, false of the extractor. Today's visitor is a single flat `libcst` traversal: `visit_Call` appends unconditionally to `self._execution_order`, and `visit_For`/`While`/`If` do nothing but flip booleans and let the traversal continue into the body *at the same level*. Implementing "body operations... are not repeated at top level in `execution_order` — the header owns them" requires the visitor to know, at the moment it would otherwise append an operation, whether it is inside a region body currently being collected for a header — a materially different traversal shape (an explicit body-accumulator stack pushed/popped around `for`/`while`/`if`), not a small patch to the existing flag-setters. The spec's ~520 LOC estimate and "leaves the tree green on its own" framing for sub-steps (1)+(2)+(3) does not name this restructuring as a risk.

Separately, and more concretely: `visit_Call`'s existing `_active_states` bookkeeping (`"tips_loaded"` add/discard at lines 479-491, feeding `_determine_preconditions`'s auto-satisfaction) is **not arm-scoped**. If a `BRANCH`'s true arm contains `pick_up_tips` (adds `"tips_loaded"`) and the false arm contains `aspirate` (whose `TIPS_LOADED` precondition would be auto-satisfied if `"tips_loaded"` is already active), a naive sequential visit of true-arm-then-false-arm leaks the true arm's state into the false arm's precondition computation — even though the two arms are mutually exclusive at runtime. `check_ir` never reads `preconditions`/`creates_state` (they are `X`-dispositioned, per DISPOSITIONS/AC-11.14) so this does not touch this increment's own soundness claims, but it does mean the extractor's own hand-written contract fields (§8's comparison target) become wrong the moment branch bodies are actually visited by the same stateful pass — an interaction the spec never names.

**What must change:** Name the visitor restructuring as its own sub-step with its own estimate, and specify that `_active_states` (or its replacement) must be arm-scoped (snapshot/restore around each branch arm) rather than accumulated across arms.

---

### O5 — MINOR — `GraphNodeType.REGION` is proposed as a new enum member without acknowledging the two, more specific, already-unused members that look purpose-built for exactly this

**Location:** §12.2.2 (283-288, "one new member on the existing enum, `models.py:539-541`"); `models.py:504-511`.

**Issue:** `GraphNodeType` already declares `CONDITIONAL = "conditional"` and `FOREACH = "foreach"` (models.py:509-510), and neither is ever assigned by any current code (`visit_Call` only ever sets `STATIC`/`DYNAMIC`, lines 494/499). These read as placeholders for exactly the loop/branch-header distinction §12.2.2 introduces, yet the spec adds a third, less specific member (`REGION`, collapsing loop and branch headers into one tag) without discussing why the two existing members aren't reused, or whether they're dead code that should be retired instead. This doesn't break any AC (disambiguation between LOOP/BRANCH headers is recoverable from which of `foreach_body`/`true_branch`+`false_branch` is populated), but it's a real gap in a document that otherwise justifies much smaller decisions at length — and it's suspicious enough (existing "branchy_graph.json" fixture actually uses `"node_type": "conditional"` on a *call-bearing* op, confirming `CONDITIONAL` is already live vocabulary elsewhere) that the choice deserves one sentence of rationale.

**What must change:** One paragraph naming why `FOREACH`/`CONDITIONAL` aren't reused for the two header kinds (or reuse them).

---

### O6 — MINOR — §12.1.5's assumption table omits a real (but, as traced, safely-widened) non-`setup()` path back to `HAS_TIP`

**Location:** §12.1.5's assumptions table (220-225); `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:239-257` (`load_state`); `external/pylabrobot/pylabrobot/resources/tip_tracker.py:138-142` (`TipTracker.load_state`, assigns `self._tip = deserialize(...)`, not derivable as `None`/non-`None` statically).

**Issue:** `LiquidHandler.load_state` calls `self.head[channel].load_state(tracker_state)` — matching the HM-24 bridge shape `self.<attr>[<name>].<method>` exactly — after `setup()` may already have run, and can leave a channel holding a real tip (deserialized from saved state). I traced this through the actual derivation code: `_classify_write` (`receiver_state.py:396-407`) classifies `TipTracker.load_state`'s writes as `"HAS_TIP"` (the RHS is a `cast(...)`/`deserialize(...)` call, matching neither the `None`-literal nor the self-attr "ambiguous" case, so it falls to the "anything else" default) — and `channels_for_call` returns `None` for `load_state` (it has no `use_channels`/channel-default-idiom parameter), so `_apply_transfer`'s "channels is Top" branch (`tipstate.py:391-395`) widens rather than asserting `NO_TIP`. This is **sound in practice**, but §12.1.5's table — which the spec says is written "so a reviewer can attack them" — names only A-CHANNELS (backend size) and A-RESET-ONCE (repeat `setup()`), and doesn't name this third class of assumption ("no other method reintroduces state between a reset and a later read, unless caught by the general bridge/effect machinery") at all. The fact that it resolves safely is a property of `_classify_write`'s crude default (non-literal, non-self-attr ⇒ `HAS_TIP`) combined with `load_state` happening to have no resolvable channel set — not a stated argument.

**What must change:** Add a third row to §12.1.5's table naming this class of assumption explicitly, even though (as traced) it currently discharges safely.

---

## Adjudication of §12.12's six open questions

1. **Template-free reset rule (Q1).** For the reset rule's own stated target (`setup`'s `self.head = {...}` reassignment), I found no PLR expression satisfying both conjuncts that leaves a tracker holding a tip — `TipTracker.__init__` unconditionally sets both state fields to `None` regardless of constructor arguments, so "fresh-only construction" always yields `NO_TIP`. **Sound for its stated target.** But see O6: the adjacent, unnamed `load_state` path shows the *soundness table*, not the *rule itself*, is incomplete.
2. **`wells()` line (Q2).** Reasonable, defensible engineering line as drawn. Non-blocking.
3. **Unroll-and-fixpoint split, `K=8` (Q3).** The "both, K non-load-bearing via tail-widen" argument holds. Non-blocking; agree with the spec's own position.
4. **Iteration index in `Finding.detail` (Q4).** Moot until O1 is resolved — whichever encoding is chosen, there is currently no producer on the executed side to compare it against.
5. **`GraphNodeType.REGION` registry row (Q5).** Before adjudicating the registry-row question, resolve O5 — the choice of a new, less-specific enum member over the two existing unused ones should be justified first.
6. **Unobserved `setup()` (Q6).** Agree with the spec's "no" — correctly conservative given `SoundnessScope` machinery doesn't exist yet. Real precision cost, correctly disclosed, not a blocker.

---

## Verdict

**Implementable as written: no.** O1 and O2 are both genuine blockers — O1 because the increment's only claimed executed evidence for LOOP/BRANCH soundness rests on a recording mechanism (`plan_call`) that is structurally incompatible with the execution mode the same paragraph specifies, and O2 because the trip-0 exploit AC-12.6 asks for is incompatible with the totality/equality guarantees (AC-6.4-amended, AC-7.2, AC-12.13) the same document asserts elsewhere.

**Single most important fix:** name a real instrumentation mechanism for tier 2b (O1) — everything else in this increment (the region-header shape, the L1/L2/L3 walk semantics, the reset rule) can be independently sound, but the document's central claim — *"an executed run... raises `HasTipError` at the same iteration — with the agreement checked by a harness that ran the program, not by a fixture"* — is currently not backed by any working code path.

---

## Orchestrator addendum — O7 (raised by the orchestrator, not the challenger; for the defender to adjudicate)

**O7 — proposed MAJOR — a proved trip count is only the real trip count if the body cannot exit early.** §12.2.3 proves `trip` from the iterable alone (`range(<int>)`, literal list, `items_x`). L1 (§12.3.3) then threads state through `min(trip, K)` iterations "as `n` real executions in order". A body containing `break`, `continue`, `return`, or a `raise` reachable before the region's last call does not execute `n` full iterations, so an unrolled iteration-2 guard may be evaluated against a state the program never reaches (`continue` skipping a `drop_tips` on iteration 1, then `pick_up_tips` on iteration 2 → the analyzer says WILL_FAIL where the run may be clean if the `continue` fires differently; `break` after a pickup → iteration-2 findings for iterations that never happen — sound only because A-COMPLETES scopes out non-reached ops, but `continue` is not scoped by A-COMPLETES). What must change: the extractor sets `trip = null` whenever the loop body (at any depth inside it) contains `Break`, `Continue`, `Return`, or `Raise`, and AC-12.6 gains such a loop as a seventh `None` entry; alternatively L1 must state why `continue` is sound under the unroll.
