---
title: "plr-sema increment 3 — real programs: derived setup() entry state, extractor-emitted regions, loop semantics, and the tier-2 oracle"
description: "Third post-corpus increment to the plr-sema pre-corpus specification. Closes the four gaps that keep increments 1 and 2 fixture-only on real data. (1) #4938 derives PLR's setup() head-reset as an effect, so a receiver whose setup() the analyzer OBSERVED enters NO_TIP on every channel and ChannelState.default finally has a producer; a receiver with no observed setup stays TOP. (2) #4932 makes praxis's libcst extractor emit real LOOP/BRANCH regions instead of two graph-level booleans, with proved trip counts from language semantics only, plus self.<attr> resource registration (round-1 O4). (3) The checker stops widening every receiver at region entry: a proved trip count of n is unrolled to min(n, K) iterations with a widened tail, an unproved one goes to a fixpoint over the height-2 lattice whose findings are emitted from the final pass only, and BRANCH becomes an arm-wise walk with a join at the merge. (4) #4880 lands tier 2 in two halves -- a bytecode-level extractor/renderer differential against tier 1, and an authored source-fixture set whose ground truth is EXECUTED against the verifier's chatterbox deck, which is the only thing that lifts the LOOP/BRANCH soundness claims off fixtures -- folding in #4939's loader-only well-ref normalisation. Zero new registry rows, zero new REASON_VOCABULARY members, zero wire-format change, no schema_version bump; one upstream enum member (GraphNodeType.REGION), one disposition change (node_type S+W -> I+S+W), and seven amendments across increments 1 and 2. Revised after adversarial round 1: the tier-2b recorder is now instance-level method wrapping joined on OperationNode.line_number rather than plan_call, which cannot fire on that execution path (O1); AC-6.4/AC-7.2/AC-11.7 read over a single defined set OBLIGED(graph) that excludes proved-trip-0 region bodies (O2); L3 retires the stale increment-2 CALL-followed-by-region compensation (O3); a Continue anywhere in a loop body withdraws the trip proof and A-COMPLETES is generalised to early exit (O7); plus the visitor-restructuring estimate risk (O4), an _active_states follow-up, a REGION-versus-FOREACH/CONDITIONAL rationale (O5), and the A-NO-REINTRODUCTION assumption row (O6). One correction found while remediating and raised by neither report: LiquidHandler.load_state satisfies the draft's two-conjunct reset rule, which would have selected two methods and disabled the feature, so P5 gains an unconditional-statement-position conjunct. See the remediation changelog at the end."
status: implemented-round-1
spec_version: 11
amends: 260901_plr-sema-pre-corpus-spec.md
task_id: 260903_sema-real-programs
date: '260903'
confidence: medium
sources: "Read this session, in full or in the cited ranges. Specs and plans, in full: .praxia/docs/specs/260902_plr-sema-ir-bytecode-increment.md; .praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md; .praxia/docs/plans/260902_plr-sema-oracle-harness.md; .praxia/docs/audits/260902_plr-sema-ir-round1-challenger.md. Main spec .praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md, section header index plus 139-208 (section 0), 2499-2537 (Deferred + boundary summary), 2538-2543 (RISK-1). Analyzer source: plr-sema/src/plr_sema/check/tipstate.py:1-278,345-471; plr-sema/src/plr_sema/check/__init__.py:380-489; plr-sema/src/plr_sema/check/ir.py:500-620,653-742; plr-sema/src/plr_sema/derive/receiver_state.py:1-120,441-510 and the whole-module symbol index; plr-sema/src/plr_sema/derive/__main__.py:285-321; plr-sema/src/plr_sema/_hand_maintained.py:36-43,240-291,294-315,496-513,676-731,780-848; plr-sema/src/plr_sema/verdict.py:129-154. Harness and lint: plr-sema/eval/oracle_common.py:490-579 and the whole-module symbol index; plr-sema/eval/tip_mutants.py:1-60,90-134; plr-sema/eval/oracle_replay.bth.toml; plr-sema/tests/test_spec_lint.py; plr-sema/scripts/check_spec_citations.py; plr-sema/scripts/check_spec_crossrefs.py. Front end: praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:260-535,667; praxis/backend/utils/plr_static_analysis/models.py:520-659; tests/utils/test_computation_graph.py:225-274. Verifier: training/verify/verifier.py:90-139; training/verify/deck.py symbol index. PLR at submodule pin dd79c4c89: external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:155-224,530-541; external/pylabrobot/pylabrobot/resources/tip_tracker.py:30-69. Data: outputs/plr-sema/oracle_replay_260902.json:1-60. Read additionally during round-1 remediation, in full: .praxia/docs/audits/260903_plr-sema-real-programs-round1-challenger.md; .praxia/docs/audits/260903_plr-sema-real-programs-round1-defender.md. Ranges read to verify the remediation: praxis/backend/utils/plr_static_analysis/models.py:495-519; plr-sema/src/plr_sema/check/ir.py:272-291; plr-sema/eval/oracle_common.py:140-157,325-348; training/verify/dispatcher.py:90-103; training/verify/verifier.py:44-57; plr-sema/tests/fixtures/branchy_graph.json (node_type and method_name fields); external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:236-261; external/pylabrobot/pylabrobot/resources/tip_tracker.py:130-147."
---

# Increment 3: real programs

> **This document amends `260901_plr-sema-pre-corpus-spec.md` by reference.** It adds §12 to that
> document's numbering and edits exactly three things in it: **AC-6.4**'s set equality and
> **AC-7.2**'s totality (both re-read over `OBLIGED(graph)`, §12.3.4) and §Deferred row **(d)**'s live
> surface (proved trip counts from language semantics are now consumed; the
> `items_x`/`items_y`-from-`wells()` half stays deferred, §12.11). **It also amends
> `260902_plr-sema-tip-typestate-increment.md`** (spec_version 9) in three places — including
> **A-COMPLETES**, generalised from "did not raise" to "was reached" — and
> **`260902_plr-sema-ir-bytecode-increment.md`** (spec_version 10) in four; §12.9
> lists all seven. Everything else in spec_version 8, 9 and 10 — `Verdict`, `Finding`, `PlrSite`,
> `AnalysisReport`, `join`, `REASON_VOCABULARY`, the telemetry schema, the fork-drift tests, the
> derivation closure mechanic, the value grammar, the canonical form, the hash and the cache key — is
> **unchanged**. No `schema_version` bump; no wire-format change; **zero new registry rows** (the
> registry is at 24 live against `BUDGET_CAP = 24`, headroom 0 —
> `plr-sema/src/plr_sema/_hand_maintained.py:36-43`); **zero new `REASON_VOCABULARY` members** (8 of
> cap 12, `plr-sema/src/plr_sema/verdict.py:129-154`). `IR_VERSION` **must** bump — §12.2.7.

---

## 12.0 What this increment is, in one paragraph

Increments 1 and 2 built a tip-typestate evaluator and a bytecode for it to run on, and both of them
carry a scope qualifier that says, in effect, *this does not fire on real data yet*. Three separate
facts produce that qualifier and they are the whole of this increment's subject. **First**, the
abstract entry state of every `LiquidHandler` receiver is `TOP`, so nothing can ever be `SAFE`
against a fresh machine — `ChannelState.default` is documented as "`TOP` for the whole walk"
(`plr-sema/src/plr_sema/check/tipstate.py:98-111`) and increment 1's §10.10 Q6 kept the field for
exactly one future producer, PLR's own `setup()`, which replaces the head map wholesale
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:187-214`). **Second**, the
extractor never emits a loop or a branch: `visit_For`/`visit_While`/`visit_If`
(`praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:376-389`) flip two
booleans and return, so every `LOOP`/`BRANCH` guarantee in increment 2 is met by hand-written
fixtures and the only real-data mechanism is the whole-stream synthetic wrap, which widens the entire
program. **Third**, tier 2 of the oracle plan was never built, so nothing executes a protocol with a
loop in it and compares the result to what the analyzer said. **This increment closes all three, plus
the one-line loader defect (#4939) that costs the replay 40 golden rows.** It adds no new abstract
domain, no new verdict, no new opcode and no new hand-maintained fact. What it adds is *reach*: the
same evaluator, running on programs that have entry states, loops and branches in them, checked by an
oracle that actually executes those loops.

| axis | today (spec_version 9 + 10) | this increment |
|---|---|---|
| entry state of a `LiquidHandler` | `TOP` on every channel, forever | `TOP` until an **observed** `setup()` `CALL`; `NO_TIP` on every channel after one |
| `ChannelState.default` | declared, never lowered — no producer | one producer, the derived reset effect (§12.1) |
| loop/branch on real payloads | zero real regions; whole-stream synthetic wrap | real regions from the extractor; the wrap becomes the fallback |
| loop semantics | widen every receiver in the region at entry | unroll `min(trip, K)` with a widened tail, or a fixpoint |
| branch semantics | widen at region entry **and** exit | arm-wise walk, `⊔` at the merge; widen only when synthetic |
| trip counts | `LOOP null` always (AC-11.11) | proved from language semantics; `null` otherwise |
| tier 2 | not started | bytecode differential **plus** executed source fixtures |
| registry rows | 24 live, cap 24, headroom 0 | **24 live, cap 24, headroom 0** — unchanged |
| `REASON_VOCABULARY` | 8 of cap 12 | **8 of cap 12** — unchanged |

**Deliverable of this increment, stated as the property that must become true:** a protocol that
picks up tips inside a `for` loop with no intervening drop produces `Verdict.WILL_FAIL` at the second
iteration's `HasTipError` guard
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:534-535`), and an *executed* run of
that same protocol source against the verifier's chatterbox deck raises `HasTipError` at the same
iteration — with the agreement checked by a harness that ran the program, not by a fixture asserting
what someone believed the program would do.

---

## 12.1 #4938 — the derived `setup()` head-reset effect

### 12.1.1 The PLR fact

`LiquidHandler.__init__` leaves the head map empty
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:162`) and `setup` replaces it
wholesale (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:187-214`), at `:197`:

```python
self.head = {c: TipTracker(thing=f"Channel {c}") for c in range(self.backend.num_channels)}
```

Every value in the new map is a freshly constructed `TipTracker`, and a fresh `TipTracker` holds no
tip: `TipTracker.__init__` writes `self._tip = None` and `self._pending_tip = None`
(`external/pylabrobot/pylabrobot/resources/tip_tracker.py:39-46`). Both of those are members of P2's
`state_fields`, so under P4's own classification rule a fresh tracker is `NO_TIP`. **Nothing here is
a new fact about PLR that a human has to assert** — it is two AST reads of source the derivation
already parses.

### 12.1.2 The derivation rule (P5), stated so that no new syntactic template is introduced

The obvious formulation of this rule is a *template*: "match `self.<a> = {<k>: <C>(…) for <k> in
<it>}`". That formulation is rejected here, and the reason is arithmetic rather than aesthetic. Such
a template is a sixth pattern for HM-25, whose row is `CAPPED (5)` at live 5
(`plr-sema/src/plr_sema/_hand_maintained.py:815-847`, measured by `_measure_hm25` at
`plr-sema/src/plr_sema/_hand_maintained.py:264-290`), and the registry has zero headroom, so a sixth
pattern is a cap conversation. The rule below is stated instead as a **whole-expression property**
over inputs the derivation already computes, which is not a pattern over how PLR is written and
therefore not a hand-maintained surface. **This choice is disclosed, not hidden**, and it is
§12.12's Q1.

> **Normative (P5, the reset effect).** Let `R` be a receiver class with a P1a channel attribute `a`
> typing to a P2-anchored tracker class `C`. A method `m` of `R` **resets** `a` iff `m`'s own body
> (depth 0) contains an `ast.Assign` whose single target is an `ast.Attribute` on `self` naming `a`
> — **not** an `ast.Subscript` of it — where the assignment satisfies **all three** of:
>
> 1. **fresh-only construction.** Every `ast.Call` in the value expression `E` whose `func` is an
>    `ast.Name` that is a key of the P1 class index constructs `C`, and at least one such call exists.
>    (Calls to names the class index does not know — `range`, `len`, `dict` — are ignored: they cannot
>    produce a tracker.)
> 2. **no carry-over of the old map.** `E` contains no load of `self.<a>` anywhere. This is the
>    load-bearing conjunct for correctness: it is what rules out `self.head = {k: v for k, v in
>    self.head.items() if …}`, a reassignment that *preserves* existing trackers and whose post-state
>    is the pre-state, not `NO_TIP`.
> 3. **unconditional.** The `ast.Assign` is a **direct statement of `m`'s body** — not nested inside
>    an `If`, `For`, `While`, `Try`, `With` or `match` within `m`. An assignment that executes on only
>    some paths through `m` does not establish a post-state on all of them, and E6 asserts a
>    post-state unconditionally.
>
> The post-state is `constructor_state(C)` — P4's existing three-way classification
> (`_classify_write`, `plr-sema/src/plr_sema/derive/receiver_state.py:462-473`) applied to `C`'s
> `__init__` writes to `state_fields`, exactly as `_effects`
> (`plr-sema/src/plr_sema/derive/receiver_state.py:410-440`) applies it to `C`'s other methods.
> `NO_TIP` and `HAS_TIP` are both admissible outcomes; **both-kinds or ambiguous is not a reset** and
> `m` gets no reset effect at all (fail-closed, the same direction as P2's anchor rule).
>
> If more than one method of `R` qualifies, **P5 emits nothing for `R`** and the feature is disabled
> for that class. A silent choice between two reset methods is exactly the "two views of one fact"
> case increment 1 §10.5 rule 1 already dispositions as *a reason to know less*.

Measured expectation over the current pin, which the fixer must **reproduce and publish, not assume**:
`R = LiquidHandler`, `a = head`, `m = setup`, `constructor_state(TipTracker) = no_tip`. Note that
`head96` is also reassigned inside the same method
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:187-214`); it is a *different*
attribute and is scoped out by §10.9's 96-head exclusion, which this increment does not reopen.

> **Conjunct 3 is not hypothetical, and it is the reason this rule selects one method rather than
> none.** `LiquidHandler.load_state` also assigns `self.head` to a fresh-`TipTracker` dict
> comprehension (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:239-257`, the
> assignment at `:248`), and that expression satisfies conjuncts 1 and 2 exactly as `setup`'s does —
> it constructs only `TipTracker`s and loads no `self.head`. **Under conjuncts 1–2 alone, P5 would
> select `{setup, load_state}` at the current pin, hit its own more-than-one rule, emit nothing, and
> disable the entire feature.** Conjunct 3 separates them on a real semantic difference rather than a
> convenient one: `setup`'s assignment is a direct statement of its body, while `load_state`'s sits
> inside `if head_state and self.head == {}:` and therefore does not run when a head map already
> exists. A conditional reassignment cannot establish a post-state on every path, so withdrawing the
> reset there is correct independently of the arithmetic. `load_state` is additionally *not* safe to
> treat as a reset for a second reason — it immediately reintroduces state through
> `self.head[channel].load_state(tracker_state)` at `:250` — and that second reason is what
> §12.1.5's `A-NO-REINTRODUCTION` row records. **This correction was found while verifying round-1's
> O6 and was not raised by either round-1 report; it is disclosed here rather than folded in
> silently.**

**Where P1 already does most of the work.** P1a's `_annotated_attributes`
(`plr-sema/src/plr_sema/derive/receiver_state.py:169-182`) already gives `head → TipTracker`, and
P1b's `_attribute_writers` (`plr-sema/src/plr_sema/derive/receiver_state.py:228-246`) already indexes
every `self.<name> = …` write by the writing method's qualname — so P5's *candidate set* is
`_attribute_writers[a]`, and P5 adds only the three-conjunct test above plus the constructor-state
read. It is a filter over an existing index, not a new scan.

### 12.1.3 Where it lands in the payload, and the provenance stamp

`ReceiverState` (`plr-sema/src/plr_sema/derive/receiver_state.py:663-688`) gains one field and
`receiver_state_to_json` (`plr-sema/src/plr_sema/derive/receiver_state.py:692-715`) one key:

```jsonc
"receiver_state": {
  "LiquidHandler": {
    "channel_attr": "head",
    "entry_reset": {"method": "setup", "post": "no_tip"},   // NEW -- absent when P5 emits nothing
    "…": "every other key unchanged"
  }}
```

`schema_version` stays **1**. `check/` reads the block through `.get()` with an empty default
(`evaluate_call`, `plr-sema/src/plr_sema/check/tipstate.py:509-536`, already does this for every
other key), so a pre-increment table degrades to today's `default = TOP` behaviour — the same
fail-closed direction as AC-10.7 and AC-11.12, and pinned here by AC-12.2's third sub-assertion.

**Provenance.** Two records, both existing artifacts, neither new:

- The **gap ledger's** `tip_state` block (`plr-sema/src/plr_sema/derive/__main__.py:481-499`, built by
  `compute_tip_families`) gains an `entry_reset` entry per anchored receiver class, alongside
  `tipstate_anchor`. Its value is the derived `{method, post}` pair, or the string `"absent"` /
  `"ambiguous"` when P5 emitted nothing and why. This is the visible surface AC-10.10 established for
  family selection, extended to the reset rule for the same reason: an absence must be *readable in
  the artifact*, not inferred from an absence of verdicts.
- The **`SurveyStamp`** the table already carries is unchanged; the reset is derived at the same pin
  as everything else, so it needs no new provenance field and no `surface_identity` change.

### 12.1.4 The transfer function, and what happens to `default`

> **E6 (reset).** For a `CALL` whose `receiver_type` has a `receiver_state` entry carrying
> `entry_reset` and whose `method` equals `entry_reset.method`: after the call's own guards have been
> evaluated against the pre-state (E1's ordering is unchanged), the receiver's state becomes
> `ChannelState(default = entry_reset.post, exact = {})`.

This is the **first and only producer** of `ChannelState.default`
(`plr-sema/src/plr_sema/check/tipstate.py:98-111`). Increment 1 §10.10's Q6 disposition — *"`default`
stays and stays `TOP`… the field is kept for the `setup()`-aware rule"* — is hereby discharged: the
field stops being dead data and becomes the cell that carries "every channel I have not otherwise
heard about". Three consequences worth stating rather than discovering:

1. **Precision arrives on channels nobody named.** After a reset, `aspirate(use_channels=[7])` with no
   intervening pickup reads `state(7) = default = NO_TIP` and its bridged `NoTipError` guard fires —
   a `WILL_FAIL` on a channel index the graph never mentioned. That is correct: the reset is a claim
   about *all* channels, which is exactly why it is the `default` cell and not an `exact` entry.
2. **E4 still wipes it, and must.** `walk.widen` sets `ChannelState()` — `default = TOP`
   (`plr-sema/src/plr_sema/check/tipstate.py:135-140`) — so any later widen discards the reset
   permanently. This is not an oversight: a widening method such as `move_tips` may have left a tip on
   an unnamed channel, so `default` must go back to `TOP` with everything else. The cost is a
   precision cliff (one `move_tips` erases the reset for the remainder of the walk) and it is
   accepted here for the same reason increment 1 accepted E4's over-widening under its Q5.
3. **`join_tip` is untouched.** `default` is joined channel-wise like any other state; §10.1.1's table
   and §10.3.2's fold are unchanged, and `fold_channels`
   (`plr-sema/src/plr_sema/check/tipstate.py:77-90`) reads `default` through `state_of` already.

### 12.1.5 Soundness: `NO_TIP` only from an **observed** reset

> **Normative.** The entry state of every receiver slot is `TOP`. `NO_TIP` at entry is established
> **only** by a `CALL` instruction on that slot whose `method` is the derived `entry_reset.method`.
> There is no "assume the caller called `setup()`" rule, in either lowering.

This is the whole soundness content of #4938 and it is worth being blunt about what it forbids. A
graph extracted from

```python
async def protocol(lh: LiquidHandler, tips: TipRack, plate: Plate):
    await lh.aspirate([plate["A1"]], vols=[50])
```

has `lh` as a **parameter** with no `setup()` call in the body. Its state stays `TOP`, its bridged
`NoTipError` guard folds to `½`, and the finding is `UNKNOWN` with reason `channel_state_unknown`.
That is uninformative and it is right: the protocol may be called with a handler that already has
tips mounted. Assuming otherwise would construct `WILL_FAIL` from an unevaluated guard, which §0's
organizing claim forbids in both directions. **A-SETUP is therefore *not* an assumption this
increment makes** — the absence of an observed reset is handled by not knowing, not by a hypothesis.

Four real assumptions are added, each named so a reviewer can attack it. The last two arrived in
round 1 (O6 and O7) — both were live and unstated in the draft, and both discharge safely today, which
is exactly why they had to be written down rather than relied upon:

| id | assumption | why it is needed | what breaks if it is false | oracle |
|---|---|---|---|---|
| **A-CHANNELS** | the reset method populates at least every channel index a later operation names | `default = NO_TIP` answers for indices `exact` does not carry; if the map is *smaller* than the operation's channel set, PLR raises `KeyError` where the analyzer says `SAFE` | a `SAFE` against a run that raised — the first-severity class. Requires a backend whose `num_channels` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:197`) is below the operation's arity; no corpus row and no chatterbox configuration produces one | tier 1's 0-unsound gate over 268 executed rows / 426 operations, and tier 2b's executed fixtures (§12.4.2) |
| **A-RESET-ONCE** | a second reset call is a reset, not an error | E6 applies unconditionally; PLR in fact raises `RuntimeError` on a repeat `setup()` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:190-191`) | nothing in the `SAFE` direction: the *analyzer* would report `NO_TIP` for a program that raises before reaching the next operation, which A-COMPLETES already scopes out — a `WILL_FAIL` claim is a claim about the trace *reaching* that index | the same two |
| **A-NO-REINTRODUCTION** (round-1 O6) | no method other than the derived `entry_reset.method` reintroduces tip state between an observed reset and a later read, *unless* the ordinary P4 bridge machinery catches it | E6 fires only on the exact reset method; every other tracker-touching method is left to §10.2.4's effect classification and §10.4's E2/E4 split, so the reset's `default` survives across calls the bridge does not model | a channel silently reading `NO_TIP` after something put a tip on it. The live instance is `LiquidHandler.load_state` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:239-257`), which calls `self.head[channel].load_state(...)` at `:250` — the HM-24 bridge shape exactly — and `TipTracker.load_state` assigns `self._tip = cast(...)` (`external/pylabrobot/pylabrobot/resources/tip_tracker.py:138-142`), which `_classify_write` (`plr-sema/src/plr_sema/derive/receiver_state.py:462-473`) classifies `HAS_TIP` since the RHS is neither a `None` literal nor a self-attr load. **It discharges safely today, but by machinery rather than by argument:** `channels_for_call` returns `None` for `load_state` (no `use_channels`, no channel-default idiom), so `_apply_transfer`'s channels-are-`Top` branch (`plr-sema/src/plr_sema/check/tipstate.py:478-504`) widens instead of asserting anything. What would break it is a future reintroducing method that *does* resolve an exact channel set | tier 1 + tier 2b; and, structurally, AC-12.1's requirement that P5 select exactly one reset method |
| **A-EARLY-EXIT** (round-1 O7) | control did not exit a region early via `break`, `return` or `raise` before the pc being checked | L1 evaluates every listed body operation on every unrolled iteration; a terminated loop's later iterations do not happen | findings for iterations the execution never ran. Sound because the oracle declines to constrain unreached call sites, the same exemption `compare` already gives post-raise operations (`plr-sema/eval/oracle_common.py:632-651`); this row is the generalisation of increment 1's A-COMPLETES from "did not raise" to "was reached", stated at the width §12.2.3 actually uses it. `continue` is **not** covered here — it does not terminate anything — and is handled instead by withdrawing the trip proof (§12.2.3 condition 4) | tier 2b's `(operation, iteration)` comparison, in which an unvisited call site is not-reached by construction (AC-12.17) |

### 12.1.6 The corpus rows must carry the real `setup()` call

`lower_calls` (`plr-sema/src/plr_sema/check/ir.py:653-727`) today lowers exactly the planned
tool-call sequence. The verifier's scaffolding awaits `setup.machine.setup()` **before** `_execute`
(`training/verify/verifier.py:117-126`), inside the same STRICT + tip/volume-tracking configuration it
establishes just above (`training/verify/verifier.py:104-116`). So every executed corpus row *does*
run a real reset, and a bytecode that omits it is not a faithful lowering of what ran — it would leave
tier 1 and tier 3 entering `TOP` while the simulator entered `NO_TIP`, which is precision loss in the
sound direction but also a **structural mismatch between the two sides of the oracle**, and the whole
point of the oracle is that the two sides describe one execution.

> **Normative.** `lower_calls` emits a `CALL` for the scaffolding's reset before the first call of the
> sequence, on the same receiver slot, with empty `kwargs`. It is emitted by the *caller* in
> `plr-sema/eval/` — which knows the verifier's scaffolding — and passed to `lower_calls` as the first
> element of `calls`, **not** synthesised inside `lower_calls`, which must stay a pure function of
> its input sequence. `origin` for that pc is the string `"setup"`, outside the integer-string index
> space `lower_calls` assigns to real calls
> (`plr-sema/src/plr_sema/check/ir.py:695-727`), so no comparison against P2.5's recorded per-operation
> results is shifted by one.

This is what makes AC-12.4's mutant numbers movable at all. `make_m1_remove_pickup`
(`plr-sema/eval/tip_mutants.py:101-121`) documents the current ceiling precisely: removing the last
`pick_up_tips` from a **single-cycle** example cannot produce a static `WILL_FAIL`, because "the walk
never treats 'nothing ever loaded a tip' as itself meaning `NO_TIP`" — state defaults to `TOP`. With
E6 that sentence stops being true: the scaffolding's reset establishes `NO_TIP` at entry, so a
single-cycle m1 mutant has a real `NO_TIP` to reason from and its downstream `aspirate` fires. That
is the mechanism behind the m1 gate moving from **1 of 55** to **≥ 50 of 55**.

---

## 12.2 #4932 — the extractor emits real LOOP and BRANCH regions

### 12.2.1 What is there today

Three visitors set a boolean and return `True`
(`praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:376-389`); one
`OperationNode` is constructed per syntactic call, with none of the five region fields passed
(`praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:501-512`); the
fields exist and are typed (`praxis/backend/utils/plr_static_analysis/models.py:551-559`); and the
graph carries `has_loops`/`has_conditionals`
(`praxis/backend/utils/plr_static_analysis/models.py:643-646`). The consumer is already written and
already total: `lower_op_and_regions` (`plr-sema/src/plr_sema/check/ir.py:622-640`) opens `Loop` and
`Branch` regions from exactly those fields and recurses into the body ids, and the synthetic
whole-stream wrap (`plr-sema/src/plr_sema/check/ir.py:570-579`) is the fallback that fires when no
real region was emitted. **This item is a producer for a consumer that already exists.**

### 12.2.2 How a region is represented — the decision, and the alternative it beat

Two shapes were on the table. **(ii) a new region node type on the graph** — a fourth pydantic model
alongside `OperationNode`/`ResourceNode`/`ProtocolComputationGraph` — was rejected: it would add a
model to §11.1.4's disposition table, which AC-11.1 checks for exhaustiveness against
`model_fields` on exactly three models, and it would give `lower_graph` a second stream to merge into
one instruction order. **(i) the increment-2 convention** — the region-owning operation gets its own
`CALL`, then the region — is adopted, with one necessary addition, because a `for` loop is *not* a
call and has no operation of its own to own the region.

> **Normative.** For every `for`/`while`/`if` statement whose body contains at least one operation the
> extractor would otherwise emit, the extractor emits a **region-header `OperationNode`**: a normal
> node with `method_name == ""`, `receiver_variable == ""`, `receiver_type is None`, empty
> `arguments`/`preconditions`/`creates_state`/`depends_on_params`, `node_type ==
> GraphNodeType.REGION` (one new member on the existing enum,
> `praxis/backend/utils/plr_static_analysis/models.py:539-541`), and the region fields populated:
> `foreach_source` + `foreach_body` for a loop, `condition_expr` + `true_branch` + `false_branch` for
> a conditional. Its id enters `execution_order` at the statement's position. Body operations are
> emitted as ordinary nodes, listed by id in the header's region field, **and are not repeated at top
> level in `execution_order`** — the header owns them.
>
> **`lower_graph` emits no `CALL` for a `REGION` header.** It emits the region alone (`LOOP` /
> `BRANCH … ELSE … END`). `node_type`'s disposition moves **`S+W` → `I+S+W`** (it is now read to
> decide whether a `CALL` is emitted), and `lower_one_call`'s `recomputed_node_type` cross-check
> (`plr-sema/src/plr_sema/check/ir.py:520-524`) is **skipped** for `REGION` nodes, which would
> otherwise disagree with both `"static"` and `"dynamic"` and emit a spurious `WIDEN node_type` on
> every loop.

The alternative *within* shape (i) — attaching the region fields to the **first machine call inside
the body** and emitting no header — was rejected on correctness, not on taste: that call would then
sit *before* the `LOOP` it opens, so under §12.3's unrolling it would execute once while the rest of
the body executed `n` times. Increment 2's own `check_ir` already compensates for that shape by
widening a `CALL` immediately followed by a region open
(`plr-sema/src/plr_sema/check/__init__.py:462-478`); that compensation is a *widen*, and a widen is
exactly what §12.3 is trying to stop doing. (§12.3.3's L3 retires that compensation outright, for a
second and independent reason.)

**Why a third enum member rather than the two unused ones already there (round-1 O5).**
`GraphNodeType` already declares `CONDITIONAL = "conditional"` and `FOREACH = "foreach"`
(`praxis/backend/utils/plr_static_analysis/models.py:504-511`), neither of which `visit_Call` ever
assigns — it only ever sets `STATIC` or `DYNAMIC`. They look purpose-built for this, and reusing them
would avoid a new member and retire two dead ones, so the choice owes an argument rather than an
omission. **They are not reused, because they are not dead vocabulary — they are *live* vocabulary
with an incompatible meaning.** `plr-sema/tests/fixtures/branchy_graph.json` carries `"node_type":
"conditional"` on `op_1`, a **call-bearing** node whose `method_name` is `"aspirate"` and which also
carries its own `condition_expr`/`true_branch`/`false_branch` — the pre-§12.2.2 shape this section
replaces. In that vocabulary `"conditional"` means *"this operation's own execution is conditional"*,
an operation-level tag on a real call. A header node needs a tag meaning *"this is not an operation at
all; it is a region boundary and emits no `CALL`"*. Collapsing the two makes `node_type`'s reading
depend on whether `method_name` is empty — a field whose meaning is a function of another field, which
no other entry in §11.1.4's disposition table is, and which `lower_graph` would have to branch on
twice for one decision. `REGION` is therefore kept distinct, and the loop-versus-branch distinction a
reused `FOREACH`/`CONDITIONAL` pair would have carried is recovered losslessly from **which** region
field is populated (`foreach_body` versus `true_branch`/`false_branch`), which `lower_op_and_regions`
already switches on. Retiring `FOREACH`/`CONDITIONAL` as genuinely dead is a separate question this
increment does not answer: `branchy_graph.json` proves at least one of them is not.

**Why a header op does not break totality.** §11.4.4 restates AC-7.2 over instructions: every `CALL`
receives ≥1 `Finding`, every non-`CALL` receives none. A `REGION` header emits no `CALL`, so it
carries no obligation and generates no finding. What it *does* break is main spec **AC-6.4**'s set
equality between finding `operation_id`s and `{op.id}`; §12.3.4 states the amendment.

### 12.2.3 Proved trip counts — language semantics only

> **Normative.** `foreach_source` carries the iterated expression's source text, as today's field
> description says. `LOOP.trip` is a **proved** integer only when **one of conditions 1–3 identifies
> the iterable AND condition 4 holds**, and is `null` in every other case:
>
> 1. `range(<int literal>)`, and `range(<a>, <b>[, <c>])` with all-integer literals, where the
>    computed length is ≥ 0;
> 2. a literal list, tuple or set **display** — `[a, b, c]`, `(x, y)` — whose length is its element
>    count, **even when the elements are not resolvable** (the same reason `Seq` is the load-bearing
>    value form in §11.1.2: length is static when contents are not);
> 3. `range(<name>.items_x)` or `range(<name>.items_y)` where `<name>` is a declared resource whose
>    `ResourceNode` carries a non-null `items_x`/`items_y`
>    (`praxis/backend/utils/plr_static_analysis/models.py:583-589`);
>
> — one of 1–3 identifies the iterable, **and**
>
> 4. **the loop body contains no `Continue` at any nesting depth within it**, excluding nested
>    function/lambda definitions (whose `continue` would be a syntax error against *this* loop anyway).
>    A body containing a `continue` gets `trip = null` regardless of how well its iterable is known.
>
> **`while` is always `trip = null`.** There is no proof rule for a `while` condition and inventing
> one would need the predicate language deferred item (c) withdrew.

**Why condition 4 exists, and why it is `continue` specifically (round-1 O7).** L1 threads state
through `min(trip, K)` iterations and evaluates **every** listed body operation on **every** iteration.
A `continue` breaks that correspondence without raising: it skips the remainder of *this* iteration's
body while the loop proceeds to a next iteration the program genuinely reaches. Concretely — a body
that `continue`s past its `drop_tips` on iteration 1 and then picks up on iteration 2 is a program
whose real state at the iteration-2 guard is `HAS_TIP`, while L1's threaded state, having applied the
skipped `drop_tips`, says `NO_TIP`. That is a definite verdict about a point the execution *does*
visit, computed from a state it never had — the one error class the whole soundness argument exists to
exclude, and **not** covered by A-COMPLETES, whose text is about raising only. Proving the iterable
does not prove the body, so the proof is withdrawn: `trip = null` routes the loop to L2's fixpoint,
which joins across passes and is therefore correct under any intra-body control flow. The rule is
syntactic and conservative — a `continue` on a path that never fires still withdraws the proof — which
is the right direction, since the alternative is a path condition and that is deferred item (c).

**`break`, `return` and `raise` are handled differently, and the difference is worth stating.** Unlike
`continue`, these *terminate* the loop (or the protocol): the iterations after them do not happen at
all, so an unrolled iteration-3 finding for a loop that broke at iteration 2 is a claim about a trace
segment the execution never reached. That is the same shape as a finding after a raise, and it is
discharged the same way — by the oracle declining to constrain unreached operations — provided the
assumption is written down at the width it is actually used. **Amendment to increment 1's
A-COMPLETES** (`260902_plr-sema-tip-typestate-increment.md`, §10.6.3), whose text reads *"each
operation preceding the one being checked completed without raising"*: it is generalised to *"each
operation preceding the pc being checked was **reached and completed** — i.e. control did not exit
early via `break`, `return` or `raise` before that pc."* The `A-EARLY-EXIT` row in §12.1.5's table
records it in this document's own assumption table so it is attackable here and not only by reference.

**And the oracle must honour it.** Tier 2b's comparison marks a call site the execution never visited
— because a `break`, `return` or `raise` skipped it — as **not-reached**, imposing no constraint on the
static verdict there. This is not a new exemption: `compare` already assigns `not_reached` to every
operation after the failing index and constrains nothing there
(`plr-sema/eval/oracle_common.py:325-345`). What changes is only the *cause* — "not reached" stops
meaning exclusively "a prior operation raised". AC-12.17's `(operation, iteration)` key makes this
mechanical, because a call site with no recorded visit for iteration `k` is not-reached at `k` by
construction.

Case 3 is deliberately narrow. `for well in plate.wells()` is **not** proved, because the claim
"`wells()` returns `items_x × items_y` items" is a fact about PLR's API that no artifact this
analyzer reads records — it would be a hand-typed fact and, against zero registry headroom, a cap
conversation. `range(plate.items_x)` needs no such fact: it is `range` of an integer the graph already
carries. The gap between the two is named in §12.11 and is §12.12's Q2.

`trip = 0` is a legal proved value and means the body never executes. Under §12.3's L1 the region is
visited `min(0, K) = 0` times, so its body contributes no findings and no state change — precise and
sound, and the one place a proved trip count *removes* obligations rather than adding them. **That
removal has a bookkeeping consequence, and round 1 (O2) was right that the draft left it implicit:**
the body's operations are ordinary non-`REGION` nodes that receive no finding, so they must be
excluded from the totality/equality target set or AC-6.4(amended) fails on this very case. §12.3.4's
`OBLIGED(graph)` is that exclusion, stated once as a set definition; AC-12.6 and AC-12.13 pin it from
both sides.

### 12.2.4 Nesting, `elif` chains, and the well-formedness contract

- **Nesting** is structural: a region header inside another region's body list produces a nested
  region in the stream, and `lower_op_and_regions` already recurses
  (`plr-sema/src/plr_sema/check/ir.py:622-640`). `region_receivers`
  (`plr-sema/src/plr_sema/check/tipstate.py:216-239`) already handles nested opens with a depth
  counter.
- **`else`** is the header's `false_branch`. An **`elif` chain** lowers as a *nested* header in the
  `false_branch` of its predecessor — which is what libcst's own tree already is, since `elif` is an
  `If` in the `orelse` position. No flattening, no chain node.
- **A `for` with an `else` clause** and a `try` are out of scope: their bodies are emitted as ordinary
  top-level operations exactly as today, and the graph-level `has_loops`/`has_conditionals` flag
  still fires, so §11.4.1's synthetic wrap still catches them. This is the **retained fallback**, and
  it is why the wrap is not deleted (§12.9).
- **Well-formedness** is unchanged and still checked by AC-11.13's nesting half: balanced
  `LOOP`/`BRANCH`/`END`, `ELSE` only inside an open `BRANCH`. What changes is that AC-11.13's *scope
  qualifier* can be deleted for real corpus data once §12.4.2's fixtures exercise it (§12.9).

### 12.2.5 `self.<attr>` assignments register resources (round-1 O4)

`visit_Assign` registers a `ResourceNode` only when the assignment target is a bare `cst.Name`
(`praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:391-421`). Round-1
O4 established the consequence: `self.plate_1["A1"]` has **no resource slot for a `Ref` to point at**,
so `lower_graph`'s value grammar resolves it to `Top` while `lower_calls`' `ir_value_of` resolves the
same bound object to a `Ref` — a latent tier-1/tier-2 bytecode divergence that neither the extractor
nor the renderer got wrong.

> **Normative.** `visit_Assign` additionally registers a `ResourceNode` when the target is a
> `cst.Attribute` whose value is `cst.Name("self")`, under `variable_name = f"self.{attr}"`, with
> `is_parameter = False` and the same type-inference path the `cst.Name` case uses. `lower_graph`'s
> value grammar gains the matching resolution: an `ast.Attribute` on `self`, and a `Subscript` of one,
> resolve against the declared resource set by the dotted name.

This closes the **grammar residual** §11.10 named as one of tier 2's three divergence causes. It does
not close the *renderer* residual — §12.4.1 keeps that one open and measured.

### 12.2.6 The boundary

`plr_sema` **must not import `praxis`**, and `tests/test_import_boundary.py` exists to enforce that
(oracle plan, "Where it lives"). The interface between the two halves of this item is the extractor's
**JSON payload** — `graph.model_dump(mode="json")` — which is already what `lower_graph` consumes.
Concretely: #4932 is a praxis-side change with praxis-side tests
(`tests/utils/test_computation_graph.py`), #4880's runner invokes the extractor **out of process**
(§12.4.1), and the only thing crossing the boundary is a dict. AC-12.16 pins that the boundary test
does not move.

### 12.2.7 `IR_VERSION` **must** bump

§11.4.1 property 3 stated this as a hard requirement of exactly this follow-up: the synthetic
whole-stream wrap is part of the canonical stream and therefore of `bytecode_hash`, so an extractor
that emits real regions **changes the hash of every protocol that currently gets a synthetically
wrapped stream**. `IR_VERSION` goes `1 → 2` in the same commit as #4932's consumer-side changes. No
cache exists yet to invalidate (#4922 is unbuilt), which is precisely why doing it now is free and
doing it later would not be.

---

## 12.3 Checker semantics for a region with a proved trip

### 12.3.1 What today's walk does, and why it has to change

On `LOOP` or `BRANCH`, `check_ir` widens every receiver slot mentioned anywhere in the region before
that region's first call is evaluated
(`plr-sema/src/plr_sema/check/__init__.py:444-461`, using `region_receivers`,
`plr-sema/src/plr_sema/check/tipstate.py:216-239`). Widening can only destroy a
verdict, so this is sound; it is also *total* destruction. Once §12.2 makes regions real, the blanket
widen would mean that **every protocol with a `for` in it is entirely `UNKNOWN` inside the loop** —
including the round-1 challenger's counterexample, which is the single most valuable thing this
analyzer could be right about.

### 12.3.2 The three candidates, costed

| option | the O1 counterexample (`pick_up_tips` in a 2-trip loop, no drop) | cost | soundness |
|---|---|---|---|
| **bounded unrolling** | `WILL_FAIL` at the second iteration's guard — the exact answer | findings multiply by `trip`; needs a bound, and has nothing to say when `trip` is `null` | sound: `n` unrolled iterations are `n` real executions in order |
| **fixpoint over the lattice** | `UNKNOWN` — the loop head's state is `NO_TIP ⊔ HAS_TIP = TOP` | none; converges in ≤ 2 passes on a height-2 lattice | sound, and total (works for `while`) |
| **both** | `WILL_FAIL` | one more code path | sound |

The fixpoint alone cannot produce the counterexample's answer, and that answer is the deliverable.
Unrolling alone cannot handle `while`, which §12.2.3 leaves at `trip = null` permanently. **Adopted:
both**, with the split stated normatively below. The blanket entry-widen is **replaced**, not
supplemented — it survives only for a *synthetic* region (§12.3.6).

### 12.3.3 The rule

> **Normative (L1, bounded unroll).** On a `LOOP` whose `trip` is a proved integer `n`, `check_ir`
> visits the region body `min(n, K)` times, left to right, threading the abstract state from one
> iteration into the next. Guards are evaluated on every iteration and findings are emitted on every
> iteration. **If `n > K`, after the `K`-th iteration every receiver slot in the region is widened**
> (`region_receivers`' set, the same one today's entry rule uses) and the walk continues past the
> region. `K = 8`.
>
> **Normative (L2, fixpoint).** On a `LOOP` whose `trip` is `null`, `check_ir` iterates the body over
> the abstract state until the state at the loop head is stable: `σ_{i+1} = σ_i ⊔ post(body, σ_i)`,
> with `⊔` the per-receiver, per-channel information-order join of §10.1.1. **Findings are emitted
> from the final pass only.** The loop's post-state is the stable head state joined with the body's
> post-state.
>
> **Normative (L3).** A region carries no other widening. The blanket entry-widen of
> `plr-sema/src/plr_sema/check/__init__.py:444-461` applies **only** to a region `lower_graph`
> synthesised (§11.4.1), where there is by construction no trip count and no known extent.
>
> **L3 additionally retires the stale increment-2 compensation at
> `plr-sema/src/plr_sema/check/__init__.py:462-478`** — the rule *"a `CALL` immediately followed by a
> `LOOP`/`BRANCH` open widens its own receiver"*. Its own docstring gives its justification: under
> increment 2's shape the region-owning operation carried its own `foreach_source`/`condition_expr`
> and was therefore *always* the instruction immediately preceding the region it opened. §12.2.2
> deletes that shape: a region is opened by a `CALL`-less header, so the predicate no longer
> identifies an owner — it now fires on **any** call that merely happens to be the statement before a
> loop or a branch. It **must not fire** under real headers.

**Why retiring it is a correctness fix and not a cleanup (round-1 O3).** Left in place, the
compensation widens an unrelated call's receiver *before that call's own guards are evaluated*,
turning a real `SAFE` or `WILL_FAIL` into `UNKNOWN` silently — precision loss with no diagnostic. The
common shape that triggers it is ordinary: a straight-line preamble followed by a loop. Round 1
observed that AC-12.10's own fixture escapes the bug only by coincidence — it puts `setup()`
immediately before the region, and E6 (§12.1.4) overwrites the whole `ChannelState` afterwards, so the
stray widen is masked. Nothing generalises that masking, and no criterion in the round-1 draft
exercised the unmasked configuration. AC-12.14 now names the fixture that does: an ordinary
tip-relevant call directly preceding a region it does not own.

**Why "final pass only" is not an optimisation.** A finding emitted on pass 1 of L2 is computed
against a state that is not yet a valid over-approximation of the loop head — it is the *first
iteration's* state, which is sound only if the loop runs once. Emitting `WILL_FAIL` from it would be
a definite-failure claim about a program that may take the other path on iteration 2. This is the one
place in this increment where a plausible implementation is *unsound*, so it is stated as a rule
rather than left to the fixer, and AC-12.11 tests it directly by asserting that a body whose net
effect differs between the first and second pass emits nothing definite.

**Termination of L2 is not an assumption.** The state is a finite map from channel index to a
three-element lattice plus a `default` cell, and `⊔` is monotone, so the sequence `σ_i` ascends in a
lattice of height 2 per cell. The *set of cells* is bounded because `exact` only gains keys from
`apply_exact` over a proved-exact channel set (`_apply_transfer`,
`plr-sema/src/plr_sema/check/tipstate.py:368-396`) and the body is finite. A hard iteration cap of
`K` passes is nonetheless imposed, with a widen on reaching it, so a bug in the join cannot hang the
checker — the same fail-closed discipline as everywhere else.

### 12.3.4 `pc`, `operation_id`, and how AC-7.2 and AC-6.4 read now

Unrolling is a property of the **walk**, not of the **stream**: `check_ir` re-visits the same `pc`
range `n` times and `lower_graph` emits the region once. Three consequences, all of them chosen to
minimise the amendment surface.

1. **`bytecode_hash` is unaffected.** The bytecode still identifies the *program*, and §11.3.3's cache
   key stays meaningful — a cached result is a function of the program plus the contracts, not of how
   many times the checker chose to walk a region. Putting the unroll in the lowering instead would
   have made the hash depend on `K`, which is a checker tuning parameter.
2. **`operation_id` stays `str(pc)`.** One `OperationNode` therefore receives `n` findings per guard,
   all sharing an `operation_id`. This is already legal and already specified: two findings sharing an
   `operation_id` are two independent obligations that **conjoin** under `join`'s obligation order,
   and §10.3.3's prohibition on Kleene-joining within an operation is unchanged and is what makes the
   conjunction correct. The **iteration index goes in `Finding.detail`**, prefixed to the guard
   condition — no new field, no wire change. (§12.12's Q4 records the alternative: a
   `sideband.unroll` map from `pc` to iteration, which would be more machine-readable and is not
   needed by anything today.)
3. **`sideband.origin` stops being injective, and that was anticipated.** Increment 2 §11.4.3's
   relabel maps `pc → op.id`; under unrolling many findings at one `pc` still map to one `op.id`, so
   the *map* is unchanged — what changes is that `{f.operation_id}` after relabelling is no longer in
   bijection with the finding multiset. §11.12's Q1 named exactly this and recorded that AC-11.7
   *asserts* the bijection rather than assuming it, so the test goes red and the choice is made
   deliberately. **Amendment:** AC-11.7's bijection clause becomes *"`sideband.origin` restricted to
   `CALL` pcs is a **function onto** `OBLIGED(graph)`"*, with `OBLIGED` as defined below.

**The obligation set, defined once and used by all three criteria.** Main spec **AC-6.4** requires
`{f.operation_id} == {op.id for op in graph.operations}`. Two constructs this increment introduces
break that equality, and both are excluded by one definition rather than by two asides:

```
OBLIGED(graph) = { op.id  for op in graph.operations
                   if op.node_type is not GraphNodeType.REGION          # (1) headers emit no CALL
                   and not nested_in_dead_region(op, graph) }

nested_in_dead_region(op, graph)  ⟺  op.id lies, at any nesting depth, within the
                                     foreach_body / true_branch / false_branch of some
                                     region header whose lowered LOOP carries a proved trip of 0
```

Exclusion (1) is the region header itself: it lowers to no `CALL`, so it carries no obligation
(§12.2.2). **Exclusion (2) is round-1 O2, and it is a real design decision made here rather than left
to be discovered.** A `LOOP` with a proved `trip == 0` is visited `min(0, K) = 0` times, so its body's
`CALL` pcs — which exist in the stream at fixed indices — are never evaluated by the walk and can
never contribute a `Finding`. Those body operations are ordinary non-`REGION` nodes, so under the
first exclusion alone they would remain in the target set and AC-6.4's equality would fail on the very
fixture AC-12.6 mandates. The alternative remedy — a "totality-only dry visit" that walks the body once
purely to manufacture a finding — is **rejected**: it would need its own rule for which state to
evaluate against and which finding to emit, and any finding it emitted would be an assertion about
code the program provably does not run, which is exactly what §12.2.3 means by *"the one place a
proved trip count removes obligations rather than adding them"*. Excluding is bookkeeping; dry-visiting
is a new semantics.

**Amendment:** AC-6.4 is re-read as `{f.operation_id} == OBLIGED(graph)`. **AC-7.2**'s totality
becomes `len(findings) >= len(OBLIGED(graph))`, which is unaffected in the direction that matters and
strictly looser everywhere else: unrolling adds findings, and a live region with at least one body
call and `min(trip, K) ≥ 1` more than pays for its header. AC-12.13 pins both halves, and AC-12.6
states the exclusion at the one fixture that exercises it.

**Why the exclusion cannot be abused.** `nested_in_dead_region` keys on a *proved* `trip == 0`, which
§12.2.3 grants only from a literal `range(0)`, an empty literal display, or a resource whose
`items_x`/`items_y` is `0`. An unproved trip is `null`, which routes to L2's fixpoint and visits the
body, so nothing is excused by not knowing. A lowering that emitted `trip = 0` where the real trip is
non-zero would silence real obligations — which is why AC-12.6 asserts the proved value for every one
of its seven loops rather than only for the interesting ones, and why tier 2b's executed iteration
count must equal the proved `trip` (AC-12.17).

### 12.3.5 `K = 8`, and why the number is not load-bearing

The **tail-widen** clause of L1 is what makes `K` a reporting budget rather than a soundness
parameter: whatever `K` is, the first `min(trip, K)` iterations really do execute in order, and the
remainder is answered by a widen, which asserts nothing. Raising or lowering `K` can only move
findings between definite and `UNKNOWN`; it can never make one wrong. Given that, `8` is chosen
because:

- The soundness-relevant precision needs `K ≥ 2`. On a height-2 typestate lattice with idempotent
  per-channel transfer functions, the first repeat-failure of the tip family — the O1 counterexample —
  is at iteration 2, and no tip-state fact is discovered for the first time after iteration 3.
- `8` covers the 8-channel row idiom (`for i in range(8)`) that real `LiquidHandler` protocols write,
  so the common proved-trip case unrolls fully rather than tail-widening.
- Cost is linear: `K × |body|` findings for a fully-unrolled region. At `K = 8` a 20-call body
  produces 160 `CALL` visits, the same order as the 9–17 findings a single operation already produces.
- `96` — the well-plate count — is deliberately **not** covered. Unrolling a 96-iteration body would
  multiply the report by 96 for zero additional tip-state knowledge past iteration 3.

`K` is a module constant in `plr_sema.check`, not a contract-table value, because it is a property of
our walk and not of PLR. It is **not** a hand-maintained surface under §0.1's classification: it is a
tuning parameter of the analyzer's own algorithm whose every value is sound, in the same class as a
recursion depth limit — not a fact about PLR that could go stale. §12.12's Q3 invites the reviewer to
disagree.

### 12.3.6 What `BRANCH` does

> **Normative (B1).** On a real `BRANCH` region, `check_ir` walks the true arm from the region's entry
> state `σ`, walks the false arm from the **same** `σ`, and sets the post-state to the per-receiver,
> per-channel join `σ_true ⊔ σ_false` (§10.1.1's table). Guards inside each arm are evaluated against
> that arm's own state. A missing arm (an `if` with no `else`) contributes `σ` unchanged to the join —
> the fall-through path.
>
> **Normative (B2).** `pred` stays `null` and is **not** evaluated, even when it is an atom over the
> same state. Deferred item (c) still governs the predicate language, and increment 2 §11.1.3's
> argument stands unchanged: `condition_expr` is a raw source string and parsing it needs the binding
> chain §3.3 withdrew `argument_not_static` for not having. A `pred`-aware branch is the natural next
> increment and is named in §12.11, not adopted here.
>
> **Normative (B3).** A **synthetic** `BRANCH` (§11.4.1's whole-stream wrap) keeps today's behaviour
> exactly: widen every receiver at entry and again at exit. There is no arm structure to walk.

B1 is strictly more precise than the entry-and-exit widen it replaces and is sound by the standard
argument: the join is the least upper bound in the information order, so `γ(σ_true ⊔ σ_false) ⊇
γ(σ_true) ∪ γ(σ_false)`, which contains every concrete post-state either arm can produce. It is also
the first place in this analyzer where a *merge* happens, which is what §Open decisions 1 reserved ⊥
for; **⊥ is still not introduced**, because B1's join never needs a unit — a missing arm contributes
`σ`, not the empty state.

---

## 12.4 #4880 — tier 2, in two halves

The oracle plan's tier 2 is one paragraph long and describes one thing: render, extract, compare. That
is half of what is needed, and the missing half is the more important one.

### 12.4.1 Half (a) — the bytecode differential against tier 1

**What it does.** For every corpus row tier 1 executes, render the executed call sequence to a minimal
Python protocol, run praxis's extractor over that source **out of process**, `lower_graph` the
resulting payload, and compare the canonical bytecode against `lower_calls`' bytecode for the same
row.

**The renderer.** Resources become **typed parameters** of the protocol function, because
`_initialize_resources_from_params`
(`praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:278-298`) is what
turns a parameter's type hint into a `ResourceNode`; a resource that is not a parameter is not seen.
Each call renders as `await lh.<method>(...)` with **PLR method parameter names taken from the bound
`PlanResult.kwargs`** — the same dict `lower_calls` reads — so the renderer never invents a name and
the tool-name barrier (§11.2.3) is respected by construction. The scaffolding reset (§12.1.6) renders
as `await lh.setup()`.

**The runner, and why it is a separate process.** There is no extractor CLI today: the only public
entry point is `extract_graph_from_source`
(`praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:667`) and nothing
outside the module calls it. `plr-sema/eval/extract_runner.py` is a thin script — source path in,
`graph.model_dump(mode="json")` out — invoked as a subprocess under the praxis environment (which has
`libcst`), so that the plr-sema package never imports praxis and `tests/test_import_boundary.py` keeps
holding. The harness shells to it once per row and caches by source digest.

**The comparison is over bytecode, not verdicts** (§11.10). A divergence localises to an instruction
index and a field. Its three possible causes are already named and this increment adds a fourth
disposition to the taxonomy:

| cause | example | disposition |
|---|---|---|
| the extractor | a call inside a region is emitted at top level | **defect** — fails the gate |
| the renderer | a positional argument rendered where tier 1 bound a keyword, so §11.2.4's trust rule untrusts it | **residual** — counted and reported, not gated, until the renderer is name-complete |
| `lower_graph`'s value grammar | `self.plate_1["A1"]` → `Top` vs. `Ref` | **closed by §12.2.5**; any survivor is a defect |
| the reset call | tier 1 emits the scaffolding reset, tier 2's rendered source contains it as a real call | **must agree** — this is AC-12.15's directional half |

The renderer residual is the honest reason this half is a **measured differential, not a hard gate on
equality**: a rendered protocol is a different program text from a planned call sequence, and until
the renderer binds every argument by keyword the two can legitimately differ on `WIDEN arguments`.
The gate is therefore: zero **extractor-cause** divergences, and the renderer-cause count published.

### 12.4.2 Half (b) — authored source fixtures with **executed** ground truth

This is the half that does not exist in the plan and is the reason the plan's tier 2 could not lift
increment 2's fixture-only qualifiers. **The corpus is straight-line.** It is a set of tool calls;
there is no loop in it and there never will be. So no amount of tier-1 or tier-2a work can produce a
single executed observation of a program with a `for` in it — and every LOOP/BRANCH soundness claim in
§12.3 is, until such an observation exists, exactly the kind of claim a fixture asserts and does not
check.

> **Normative.** `plr-sema/eval/fixtures/regions/*.py` is a set of authored **source** protocols
> containing `for`, `while`, `if`/`elif`/`else` and nesting, each with both tip outcomes represented
> (a loop that fails at iteration 2; a loop that drops before re-picking and runs clean; a branch
> where one arm picks up and the other does not). Ground truth is obtained by **executing the source**
> against the verifier's own chatterbox deck — `build_setup` (`training/verify/deck.py:368`) under the
> STRICT + tip/volume-tracking configuration `verify` establishes
> (`training/verify/verifier.py:104-116`) — recording, per raise, the **operation and the iteration**
> at which it happened. The static side runs the same source through §12.4.1's runner, `lower_graph`,
> and `check_ir`.

The soundness contract is the plan's own, unchanged: `SAFE` where the execution raised is unsound;
`WILL_FAIL` where it ran clean is unsound; zero unsound rows is a hard gate; the `UNKNOWN` rate is
reported, not gated. What is **added** is an iteration coordinate on both sides, because a loop's
ground truth is not "operation `i` raised" but "operation `i` raised on iteration `k`", and a static
`WILL_FAIL` at the wrong iteration is a claim the execution contradicts.

**Execution mechanics (round-1 O1: the recorder is *not* `plan_call`).** The fixture source is executed
directly (it is a coroutine taking the deck's resources as parameters), not replayed as a call
sequence — that is the entire point: a call sequence has no loop. **That execution mode structurally
excludes tier 1's recorder.** `plan_call` is a pure function of a JSON call dict and its *list index*
(`training/verify/dispatcher.py:92-101`), reached only from `_execute`'s
`for i, call in enumerate(call_sequence)` loop (`training/verify/verifier.py:47-55`), and
`recording_plan_call` records by monkey-patching that module-level name
(`plr-sema/eval/oracle_common.py:144-153`). A fixture coroutine that calls `lh.pick_up_tips(...)` from
inside a real Python `for` never invokes it at all. The round-1 draft named it anyway; that was wrong
and this is the replacement.

> **Normative (the tier-2b recorder).** Before the fixture coroutine is awaited, the harness wraps
> **each tool method on the `setup.machine` instance** `build_setup` returned — instance attributes,
> not the class, so nothing global is patched and no other test can observe it — with an `async`
> `functools.wraps` shim. On entry the shim reads its **caller's source line**,
> `sys._getframe(1).f_lineno`, increments a monotonic counter in a
> `dict[(method_name, lineno), int]`, and records `(method_name, lineno, visit_index)`; on an
> exception it records the same triple plus the exception class before re-raising. The method set to
> wrap is the receiver class's own methods that appear as contract keys — derived, not typed.
>
> **The join to the static side is `OperationNode.line_number`.** That field already exists
> (`praxis/backend/utils/plr_static_analysis/models.py:532`), is already populated at every call site
> (`praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:503`)
> **[FALSIFIED 260903 — see §12.13: `_current_line` is set to 0 in `__init__` and never reassigned,
> so `OperationNode.line_number` is 0 at every call site, not populated per-site; the join degrades to
> method-only and is guarded by the fixture's one-call-site-per-method constraint plus
> `DuplicateCallSiteError`, not by the two-part key this paragraph describes; praxis-side defect
> tracked as backlog #4948]**, and is
> already carried into the bytecode's sideband
> (`plr-sema/src/plr_sema/check/ir.py:538`). Since §12.4.1's runner extracts **the same source file**
> the harness just executed, the executed side's `lineno` and the static side's `line_number` are two
> readings of one file and agree by construction. The executed key `(method_name, lineno,
> visit_index)` therefore joins to the static key `(CALL.method, sideband["span"][pc], iteration)`,
> and `sideband["origin"][pc]` converts the pc to the graph operation id.

**The fixture-design constraint that makes the join unambiguous, stated as a requirement rather than
left to luck.** `(method_name, lineno)` identifies a call site only if no two call sites in the
fixture share both. **Each fixture body therefore contains at most one call site per PLR method**, and
no fixture puts two calls on one physical line. This is cheap to honour in authored fixtures and it is
what makes the recorder a *lookup* rather than a heuristic; a fixture that violates it is a fixture
bug, and the harness must **fail loudly** on a duplicate `(method_name, lineno)` registration rather
than silently picking one. A future fixture that needs two call sites for one method needs a
column-level key, which `f_lineno` does not carry — named here so it is not discovered later.

**What this mechanism does not need.** No change to `dispatcher.py`, no change to `verifier.py`, no
new `PlanResult` field, and no `call_sequence` at all. It is smaller than extending `plan_call` would
have been, which is why T21's estimate moves only slightly (§12.8).

**This is what lets the qualifiers go.** AC-11.11's and AC-11.13's *"fixture-only, zero soundness
claim over real corpus or graph data"* scope qualifiers, and increment 1's AC-10.6 and §10.5 rule 2,
all become claims checked by execution. §12.9 records the deletion.

### 12.4.3 #4939 — the loader's well-ref normalisation, scoped to the loader

The tier-1 replay loses 40 golden rows to unparseable underscore references such as
`tip_rack_3_F7` — a residual the plan records in its own status table
(`.praxia/docs/plans/260902_plr-sema-oracle-harness.md:159`), against a run whose other numbers were
268 rows executed, 426 operations, 0 unsound, 189 of 189 crosscheck agreement
(`outputs/plr-sema/oracle_replay_260902.json:2-17`).

> **Normative.** `row_to_verifier_inputs` (`plr-sema/eval/oracle_common.py:1038-1046`) normalises a
> reference of the form `<base>_<Row><Col>` to `<base>.<Row><Col>` **if and only if `<base>` is a
> declared resource of the row's own deck layout** — the layout it has already computed, not a name
> pattern. `<Row>` is a single `A`–`H`, `<Col>` one or two digits, matching the regex shape
> `tip_mutants.py` already uses for well refs
> (`plr-sema/eval/tip_mutants.py:124`). A reference whose base is not a declared layout resource is
> left exactly as it is and continues to produce whatever `skip_reason` it produces today.
>
> **The corpus files are not rewritten and `training/verify/grounding.py` is not touched.** This is a
> loader-side reading of an ambiguous reference, not a change to what a reference *means*. The count
> is reported as `rows_normalised` in the replay report, alongside `rows_parse_error`, so the
> intervention is visible rather than absorbed.

The base-is-declared condition is the whole safety argument: without it, `tip_rack_3_F7` and a
hypothetical resource genuinely named `tip_rack_3_F7` are indistinguishable, and the normalisation
would rename a real resource into a well of a resource that does not exist. With it, the rewrite only
fires where the dotted reading is the only one that resolves.

### 12.4.4 Bathos

Both halves are bathos-tracked with a sidecar modelled on `plr-sema/eval/oracle_replay.bth.toml`:
`plr-sema/eval/tier2_extractor.bth.toml`, with `[outcomes.pass]` requiring zero extractor-cause
divergences and zero unsound region-fixture rows, `[outcomes.marginal]` for zero-unsound-with-nonzero
renderer residual, and `[outcomes.fail]` residual on any unsound row. `[result_schema]` publishes
`rows`, `operations`, `bytecode_divergences_extractor`, `bytecode_divergences_renderer`,
`region_fixtures`, `region_unsound`, `region_will_fail_fired`, `rows_normalised`.

---

## 12.5 Soundness claims and the oracle that checks each

Every claim this increment makes, and the thing that would catch it being wrong. A claim with no
oracle is a claim this document is not entitled to make.

| claim | §  | oracle |
|---|---|---|
| an observed reset means `NO_TIP` on every channel | 12.1.4 | tier 3 mutants (m1 ≥ 50/55 with 0 unsound), tier 1 (0 unsound over 426 operations), AC-12.2's negative fixture |
| an **unobserved** reset means nothing (state stays `TOP`) | 12.1.5 | AC-12.2's parameter-receiver fixture; tier 2b, where a fixture with no `setup()` in its source must produce no definite verdict |
| A-CHANNELS, A-RESET-ONCE | 12.1.5 | tier 1 + tier 2b executed runs |
| A-NO-REINTRODUCTION (round-1 O6) | 12.1.5 | tier 1 + tier 2b; and structurally, AC-12.1(iv), which asserts P5 selects exactly `{"setup"}` and not `{"setup", "load_state"}` |
| A-EARLY-EXIT (round-1 O7) | 12.1.5 | tier 2b's `(operation, iteration)` comparison, in which an unvisited call site is not-reached by construction |
| a `continue` in a body cannot corrupt a threaded state, because such a body is never unrolled | 12.2.3 cond. 4 | AC-12.6's seventh loop (`trip is None` despite a provable iterable); tier 2b's `continue` fixture, whose executed trace visits the loop but skips a listed operation |
| a region's extent is what the extractor said it is | 12.2.2 | tier 2a's bytecode differential (an extractor-cause divergence fails the gate) |
| a proved trip count is the real trip count | 12.2.3 | tier 2b: the executed iteration counter must equal the proved `trip` for every proved-trip fixture |
| the executed side's `(method, lineno, visit)` really is the static side's `(method, span, iteration)` | 12.4.2 | AC-12.17(ii)'s totality-of-join assertion and (iii)'s loud duplicate-key failure — a mis-join shows up as an orphaned executed record, not as a silent agreement |
| `min(trip, K)` unrolled iterations are real executions in order | 12.3.3 L1 | tier 2b's per-iteration ground truth |
| the L2 fixpoint over-approximates the loop head | 12.3.3 L2 | tier 2b's `while` fixtures, plus AC-12.11's final-pass-only assertion |
| a `BRANCH` join over-approximates both arms | 12.3.6 B1 | tier 2b's branch fixtures, both arms exercised by different deck seeds |
| the two lowerings agree on one program | 12.4.1 | tier 2a |
| normalisation never renames a real resource | 12.4.3 | AC-12.19's base-is-declared assertion + `rows_normalised` publication |

---

## 12.6 Hand-maintained impact

**New registry rows: zero.** The registry is at 24 live against `BUDGET_CAP = 24`
(`plr-sema/src/plr_sema/_hand_maintained.py:36-43`), headroom 0. Every fact this increment relies on
is derived, and the two places where it *could* have been otherwise are called out rather than
quietly routed around:

| what could have been typed | what it is instead |
|---|---|
| a reset idiom template (`self.<a> = {k: C(…) for k in …}`) — a **sixth** HM-25 pattern against a `CAPPED (5)` ceiling | §12.1.2's three-conjunct whole-expression-plus-statement-position property over P1's existing class index and P4's existing `_classify_write`. Not a template; no `_measure_hm25` change |
| "`wells()` returns `items_x × items_y` items" — a PLR API fact | **not adopted.** §12.2.3 proves trip counts from language semantics only; the `wells()` case is deferred (§12.11) precisely because adopting it needs a row |
| `K` as a tuned per-method table | one module constant whose every value is sound (§12.3.5) |
| a tool→PLR name map in the renderer | `PlanResult.kwargs`, the same dict `lower_calls` reads (§12.4.1) |
| a well-ref name pattern for #4939 | the row's own **declared layout resource set** as the gate; the row/column shape reuses the regex already in `plr-sema/eval/tip_mutants.py:124` |
| a list of "control-flow constructs that invalidate a trip proof" | §12.2.3 condition 4 tests for **one** node type, `Continue`, and it is a Python language construct, not a PLR idiom. `break`/`return`/`raise` need no entry on such a list either: they are handled by an *assumption* (`A-EARLY-EXIT`) plus an oracle exemption that already exists, not by a syntactic veto |
| an instrumentation table mapping wrapped methods to graph operations | the executed side's own caller line, joined to `OperationNode.line_number`, which the extractor already populates (§12.4.2). No table, and the wrapped method set is the receiver class's contract keys — derived |

**`REASON_VOCABULARY` (HM-14): unchanged at 8 of cap 12.** Nothing in this increment gives up at a new
pipeline stage. A guard inside a region that the fixpoint left at `TOP` gives up at the *evaluation*
stage and uses `channel_state_unknown`, exactly as increment 1 §10.8 specified; a `null` trip count
is not a finding at all, it is an operand.

**HM-21 (X dispositions): unchanged at live 3, ceiling 5**
(`plr-sema/src/plr_sema/_hand_maintained.py:682-731`). This increment changes **one** disposition —
`node_type` from `S+W` to `I+S+W` (§12.2.2) — and moves no field into or out of `X`. The three
excluded identities pinned by AC-11.14 are untouched, and `_measure_hm21` returns the same number.
Worth stating explicitly because HM-21's metric counts `X` dispositions, so a *change* to a non-`X`
disposition is invisible to it by design, and an invisible change is exactly what the ratchet is for
— the visible protection here is AC-11.1's exhaustiveness check, which sees the disposition table's
key set and is unaffected, plus AC-12.5, which asserts the new behaviour directly.

**HM-24 and HM-25: unchanged at 1 and 5.** No new syntactic pattern (see the table above).

**`GraphNodeType.REGION` gets no row, and this is a position, not an oversight.** It is a member of
*praxis's own* graph model, describing the shape of praxis's own output — in the same class as
`OperationNode`'s field names, which carry no rows either, and unlike `PreconditionType` (HM-11,
`plr-sema/src/plr_sema/_hand_maintained.py:496-513`), whose members assert *what kinds of PLR
precondition exist*. `REGION` asserts nothing about PLR. It also fails **closed**: an extractor that
stops emitting the member emits no regions, `has_loops` still fires, and §11.4.1's synthetic wrap
widens the program — today's behaviour. A reviewer who disagrees should say so; the remedy is one row
and a cap conversation, and it is §12.12's Q5.

**Wire format: no change.** `Verdict`, `Finding` (including `detail`, which §12.3.4 uses without
changing its type), `PlrSite`, `AnalysisReport`, `join`, `SCHEMA_VERSION` and
`derived_contracts.json`'s `schema_version: 1` are all unchanged. `entry_reset` is a new optional key
read through `.get()`. `IR_VERSION` bumps (§12.2.7), which is an *internal* version and not a wire
format.

---

## 12.7 Acceptance criteria

Written so that none can be satisfied while the property is false. Where a criterion could be passed
by a stub, the stub-defeating half is named.

- **AC-12.1 (the reset rule is derived and published, not asserted).** Re-running `plr_sema.derive`
  emits `receiver_state["LiquidHandler"]["entry_reset"] == {"method": "setup", "post": "no_tip"}`, and
  the gap ledger's `tip_state` block carries the same pair. Four sub-assertions, all mechanical: (i)
  the emitted value equals the above; (ii) an **AST literal scan** of `plr-sema/src/` — the mechanism
  AC-10.9 established, not a grep — finds no `ast.Constant` string equal to `"setup"`, `"head"` or
  `"TipTracker"`, so the method name is read from PLR and not typed; (iii) a synthetic class fixture
  with **two** qualifying reset methods produces **no** `entry_reset` and a ledger value of
  `"ambiguous"`, and one with a carry-over value expression (`{k: v for k, v in self.head.items()}`)
  produces none either — two of the three fail-closed halves of §12.1.2, which a rule that matched
  only the positive case would pass without; (iv) **conjunct 3 is checked against real PLR, not a
  synthetic fixture**: the set of `LiquidHandler` methods satisfying conjuncts 1 **and** 2 alone is
  asserted to be exactly `{"setup", "load_state"}` — two members — and the set satisfying all three
  exactly `{"setup"}`. Sub-assertion (iv) is the one that fails if conjunct 3 is dropped or weakened,
  and it fails *loudly and in the right place*: without it the whole feature silently disables itself
  at this pin (§12.1.2), which would look like a wiring bug rather than a rule defect.
- **AC-12.2 (entry state fires only on an observed reset, both directions).** Three fixtures. (a)
  `setup_then_aspirate_graph.json` — `setup()` then `aspirate(use_channels=[0])` — yields exactly one
  `Finding` with `verdict is Verdict.WILL_FAIL` on the aspirate, `category == "precondition_state"`,
  `plr_site == PlrSite("external/pylabrobot/pylabrobot/resources/tip_tracker.py", 65,
  "TipTracker.get_tip")`. (b) `aspirate_no_setup_graph.json` — the same graph with the `setup()`
  operation deleted — yields **zero** `WILL_FAIL` and zero `SAFE` findings and
  `report.verdict is Verdict.UNKNOWN`. (c) The same fixture (a) against a contract table with no
  `entry_reset` key returns fixture (b)'s report, never raising. (b) is the stub-defeating half: an
  implementation that seeds `NO_TIP` at graph entry passes (a) and fails (b).
- **AC-12.3 (the corpus lowering carries the real reset).** For every executed row of the tier-1
  replay, the lowered bytecode's first `CALL` has `method == "setup"` and empty `kwargs`, its
  `sideband.origin` entry is the string `"setup"`, and the `origin` values for every other `CALL` are
  unchanged from the pre-increment run — so the exact `record_id` join to P2.5's recorded results is
  not shifted by one. The unchanged-`origin` half is what makes this more than "a setup call appears
  somewhere".
- **AC-12.4 (the oracle gate — direction and non-regression).** `#4881`'s tip-family mutants report
  **m1 ≥ 50 of 55** rows carrying a static `WILL_FAIL` at the index the simulator raised, with **0
  unsound**; **m2 stays 108 of 108** with 0 unsound; and AC-10.12's criteria (i) and (ii) hold for
  both classes. Tier 1 stays at **0 unsound**, 0 `check_graph` exceptions, 0 totality violations and
  189 of 189 crosscheck agreement over its 268 executed rows / 426 operations
  (`outputs/plr-sema/oracle_replay_260902.json:2-17`). The m1 number is the directional half: it
  cannot be reached by an evaluator that never fires, and today it is **1 of 55** for the reason
  `make_m1_remove_pickup` documents (`plr-sema/eval/tip_mutants.py:101-121`).
- **AC-12.5 (real regions are emitted, and the synthetic wrap stops firing).** For the extractor's own
  `LOOP_PROTOCOL_SOURCE` and `CONDITIONAL_PROTOCOL_SOURCE` fixtures
  (`tests/utils/test_computation_graph.py:240-254`): the graph contains a `node_type ==
  GraphNodeType.REGION` header whose `foreach_body` (respectively `true_branch`) names the body
  operations; those operations do **not** additionally appear at top level in `execution_order`; and
  `lower_graph` over the payload produces a stream with ≥ 1 real `LOOP` (respectively `BRANCH … ELSE …
  END`) and **zero** synthetic wraps, i.e. no `WIDEN has_loops` / `WIDEN has_conditionals` instruction.
  `has_loops`/`has_conditionals` remain `True`.
- **AC-12.6 (proved trip counts are exhaustive over three sources and `null` everywhere else).** A
  fixture protocol with seven loops — `range(3)`; `range(2, 10, 2)`; `[a, b, c]` with unresolvable
  elements; `range(plate.items_x)` on a resource whose `ResourceNode` carries `items_x == 12`;
  `plate.wells()`; a `while`; and `for i in range(4)` whose body contains a `continue` nested inside
  an `if` — lowers to `trip` values `3, 4, 3, 12, None, None, None` in that order. The last three are
  the stub-defeating half: a rule that guesses a count fails `wells()` and the `while`, and a rule
  that reads only the iterable fails the `continue` loop, whose iterable alone proves `4`
  (round-1 O7). An eighth loop, `range(0)`, containing a real `pick_up_tips(use_channels=[0])`, lowers
  to `trip == 0` and contributes **zero** findings and no state change — **and its body operation is
  excluded from `OBLIGED(graph)` by §12.3.4's `nested_in_dead_region` clause**, so AC-6.4(amended),
  AC-7.2 and AC-12.13 are satisfied on this fixture rather than contradicted by it (round-1 O2). The
  body must be non-empty or the "zero findings" assertion is vacuous.
- **AC-12.7 (nesting and `elif` chains are structural and well-formed).** A fixture with a `for`
  containing an `if`/`elif`/`else`, itself containing a `while`, lowers to a balanced stream —
  `LOOP` → `BRANCH` → `ELSE` → nested `BRANCH` → `ELSE` → `LOOP` → matched `END`s — with `ELSE` only
  inside an open `BRANCH`, and `check_ir` never raises on it. The `elif` appears as a nested `BRANCH`
  in the outer branch's false arm, not as a third arm.
- **AC-12.8 (`self.<attr>` resources are registered and resolve to `Ref`).** A protocol assigning
  `self.plate_1 = deck.get_resource("plate")` and then calling `lh.aspirate([self.plate_1["A1"]],
  vols=[50])` produces a `ResourceNode` under `variable_name == "self.plate_1"` with `is_parameter is
  False`, and `lower_graph` resolves the argument to `Ref(slot_of("self.plate_1"), "A1")` — **not**
  `Top`. Round-1 O4's latent divergence is thereby closed, and the assertion is on the `Ref`, not on
  the absence of a `WIDEN`.
- **AC-12.9 (the extractor does not regress).** Every existing test in
  `tests/utils/test_computation_graph.py` passes unmodified, including
  `test_multi_machine_operation_count` (`tests/utils/test_computation_graph.py:351-358`), whose
  straight-line protocol must still produce exactly 5 operations and **no** region header. A change
  that emitted a header for every statement would fail it.
- **AC-12.10 (bounded unrolling is precise on the round-1 counterexample).** The O1 fixture — a
  `for rack in [r0, r1]` region containing `pick_up_tips(use_channels=[0])` and
  `aspirate(use_channels=[0])`, with no drop and a preceding `setup()` — has proved `trip == 2`, and
  the report contains **exactly one** `Finding` with `verdict is Verdict.WILL_FAIL`, `category ==
  "precondition_state"`, `plr_site ==
  PlrSite("external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py", 535,
  "LiquidHandler.pick_up_tips")`, whose `detail` names iteration **2**. The first iteration's
  `pick_up_tips` guard is `SAFE`. Iteration identification in `detail` is what makes this
  unsatisfiable by an implementation that widens and then guesses.
- **AC-12.11 (the fixpoint emits from the final pass only).** A `while` fixture whose body picks up on
  the first pass and drops on a later one — so the loop-head state differs between pass 1 and pass 2 —
  produces **zero** `WILL_FAIL` and **zero** `SAFE` findings for the affected receiver, and
  `report.verdict is Verdict.UNKNOWN`. An implementation that emits pass-1 findings produces a
  `WILL_FAIL` here and fails. The same fixture also asserts the walk converges within `K` passes and
  `check_ir` does not raise.
- **AC-12.12 (the tail widen fires at `K`).** A proved `trip == 20` loop over a body that establishes
  `HAS_TIP` produces findings for iterations 1 through 8 and **none** for 9 through 20, and every
  receiver in the region reads `TOP` immediately after the region's `END` — asserted through a
  following `aspirate` on the same receiver yielding `channel_state_unknown` rather than a definite
  verdict.
- **AC-12.13 (totality and the relabel under unrolling).** For the AC-12.10 fixture, for AC-12.6's
  eighth (`range(0)`) loop, and for every region fixture: every `CALL` pc **visited** by `check_ir`
  receives ≥ 1 `Finding` and no non-`CALL` pc receives any; `sideband.origin` restricted to `CALL` pcs
  is a **function onto** `OBLIGED(graph)` as §12.3.4 defines it; after relabelling, `{f.operation_id}`
  equals `OBLIGED(graph)` (main spec AC-6.4 as amended); and `len(findings) >= len(OBLIGED(graph))`.
  A second assertion pins the carve-out from the other side, so that it cannot be widened silently:
  `OBLIGED(graph)` differs from `{op.id for op in graph.operations if op.node_type is not
  GraphNodeType.REGION}` on **exactly** the body operations of proved-`trip == 0` regions, and on the
  AC-12.10 fixture — which has no dead region — the two sets are **equal**.
- **AC-12.14 (regions widen-or-join, never construct `SAFE` without an evaluated guard, and never
  widen a call that owns no region).** Four assertions. On one branch fixture whose true arm picks up
  and whose false arm does not: (i) a guard inside the true arm evaluates against the true arm's own
  state and can be `SAFE`; (ii) an operation **after** the region reads the join and yields
  `channel_state_unknown`, not `SAFE`. Over all region fixtures: (iii) every `Finding` whose
  `verdict is Verdict.SAFE` carries a non-empty `detail` equal to a guard `condition` present in the
  contract table — the mechanical form of §0's "no `SAFE` constructed without an evaluated guard".
  And, on a dedicated fixture `call_before_unowned_region_graph.json` (round-1 O3): (iv) in a graph
  whose operations are `setup()`, then `pick_up_tips(use_channels=[0])`, then a region header the
  `pick_up_tips` does not own and whose body touches a *different* receiver, the `pick_up_tips`
  operation's own guard is evaluated against its **real pre-call state** — `default == NO_TIP` from
  the reset — and yields exactly one `Verdict.SAFE` finding sited at
  `PlrSite("external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py", 535,
  "LiquidHandler.pick_up_tips")`, with **no** `channel_state_unknown` for that operation. The reset
  sits at the top of the graph and **not** adjacent to the region, which is the whole point:
  adjacency is what masked the defect in AC-12.10's fixture (§12.3.3), so a fixture that reproduces
  that adjacency would pass with the stale compensation still in place.
- **AC-12.15 (tier 2a — the two lowerings agree, and the reset agrees too).** Over every executed
  tier-1 row: **zero** extractor-cause bytecode divergences; the renderer-cause count published; and,
  directionally, for at least one row the tier-2 stream's first `CALL` has `method == "setup"` and its
  `pick_up_tips` `CALL` carries a `tip_spots` kwarg whose value is a `Seq` of the same length as tier
  1's. The directional half is what a comparison that always reports "equal" cannot pass.
- **AC-12.16 (the runner is out of process and the boundary holds).** `plr-sema/eval/extract_runner.py`
  is invoked as a subprocess; `tests/test_import_boundary.py` passes unmodified; and an AST import
  scan of `plr-sema/src/` and `plr-sema/eval/` finds no `import praxis` outside the subprocess
  argument list.
- **AC-12.17 (tier 2b — executed ground truth for regions, produced by a named recorder).** Over the
  authored region fixtures: **zero** unsound rows under the plan's own contract, with the comparison
  keyed on `(operation, iteration)` rather than operation alone; and **at least one** fixture in each
  of the three shapes (`for`, `while`, `if`) carries a static `WILL_FAIL` at the `(operation,
  iteration)` the execution raised. For every proved-`trip` fixture, the executed iteration count
  equals the proved `trip`. Four sub-assertions pin the producer, because round 1 (O1) found the draft
  naming one that cannot run on this execution path: (i) the executed side's records come from the
  **instance-level method wrapper** of §12.4.2, and `verifier.plan_call` is **never invoked** during a
  region-fixture run — asserted by leaving `recording_plan_call`
  (`plr-sema/eval/oracle_common.py:144-153`) installed and requiring its `planned` list to stay empty;
  (ii) every executed record's `lineno` is a key of the static side's `sideband["span"]`, so the join
  is total and no executed call site is orphaned; (iii) registering a duplicate `(method_name,
  lineno)` raises rather than overwriting, tested with a deliberately malformed fixture; (iv) the
  wrapper is removed on teardown and the class object is unmodified, tested by asserting the unbound
  method is the original after the run. (i) is the stub-defeating half: it fails for any
  implementation that quietly falls back to tier 1's recorder.
- **AC-12.18 (the run is bathos-tracked and its schema is complete).**
  `plr-sema/eval/tier2_extractor.bth.toml` validates, its `[result_schema]` names every field §12.4.4
  lists, and the harness writes a result carrying all of them — including `region_will_fail_fired`,
  whose value being `0` must make `[outcomes.pass]`'s condition false.
- **AC-12.19 (#4939 normalises only what the layout declares).** `row_to_verifier_inputs` normalises
  `<base>_<Row><Col>` to dotted form exactly when `<base>` is a declared resource of the row's own
  layout: a golden row referencing `tip_rack_3_F7` with `tip_rack_3` declared resolves and executes; a
  row referencing `foo_A1` with no `foo` declared is left verbatim and keeps its current
  `skip_reason`. The replay report carries `rows_normalised`; `rows_parse_error` for the golden
  provenance falls from 40 toward 0 and the achieved number is published. `training/verify/grounding.py`
  and every file under `training/assemble/out/` are **byte-identical** before and after — asserted, not
  assumed.
- **AC-12.20 (this document is machine-checked).** `plr-sema/tests/test_spec_lint.py` is extended with
  a `SPEC_INCREMENT_3` entry alongside `SPEC_INCREMENT_2`
  (`plr-sema/tests/test_spec_lint.py:209-221`), and both the citation checker and the AC-gating half of
  the cross-reference checker report **zero** failing violations over this file.

---

## 12.8 Task rows

Ordering is forced in two places and free elsewhere: **#4938 must land before AC-12.4 can be measured**
(the mutant numbers move because of it), and **#4932 must land before T20** (there is nothing to unroll
until real regions exist). #4880 and T21 both depend on #4932; #4939 is independent of everything and
can land first.

| task | scope | files | gate | ~LOC | depends on | model |
|---|---|---|---|---|---|---|
| **#4939** | Loader-only well-ref normalisation (§12.4.3): `<base>_<Row><Col>` → `<base>.<Row><Col>` iff `<base>` is a declared layout resource of that row; `rows_normalised` added to the replay report next to `rows_parse_error`. Corpus files and `training/verify/grounding.py` untouched, asserted by a byte-identity test | modify `plr-sema/eval/oracle_common.py`, `plr-sema/eval/oracle_replay.py`, `plr-sema/tests/test_oracle_replay.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q`; then `uv run python plr-sema/eval/oracle_replay.py --corpus training/assemble/out/corpus_p25.jsonl --contracts plr-sema/data/derived_contracts.json --report $TMPDIR/replay_4939.json` and publish `rows_normalised` — satisfying **AC-12.19** | ~90 | — | Haiku |
| **#4938** | The derived reset effect, in this order: (1) P5 in `derive/receiver_state.py` — the **three**-conjunct rule (fresh-only construction, no carry-over, **unconditional statement position**) + `constructor_state(C)` via the existing `_classify_write`, plus both fail-closed cases; (2) `ReceiverState.entry_reset` + `receiver_state_to_json` key + the ledger's `entry_reset` value in `derive/__main__.py`; (3) E6 in `check/tipstate.py` and its wiring in `check/__init__.py`; (4) `plr-sema/eval/` prepends the scaffolding reset call to `lower_calls`' input with `origin == "setup"`; (5) two new graph fixtures + the two fail-closed derivation fixtures + the AST literal scan + **AC-12.1(iv)'s real-PLR selection check, which must show conjuncts 1–2 alone selecting two methods and all three selecting one (round-1 remediation)**; (6) artifact regenerated | create `plr-sema/tests/fixtures/{setup_then_aspirate,aspirate_no_setup}_graph.json`; modify `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/src/plr_sema/check/tipstate.py`, `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/eval/tip_mutants.py`, `plr-sema/tests/test_{derive,tip_typestate,check_graph}.py`, `plr-sema/data/derived_contracts.json` (regenerated) | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_tip_typestate.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; then `uv run python -m plr_sema.derive --survey-json training/verify/data/plr_preconditions.json --taxonomy-json training/verify/data/plr_exception_taxonomy.json --out plr-sema/data/derived_contracts.json --gap-ledger plr-sema/data/gap_ledger.json`; then `uv run python plr-sema/eval/tip_mutants.py --corpus training/assemble/out/corpus_p25.jsonl --examples-dir training/examples --contracts plr-sema/data/derived_contracts.json --report $TMPDIR/tip_mutants_4938.json` and `uv run python plr-sema/eval/oracle_replay.py --corpus training/assemble/out/corpus_p25.jsonl --contracts plr-sema/data/derived_contracts.json --report $TMPDIR/replay_4938.json` — satisfying **AC-12.1**, **AC-12.2**, **AC-12.3**, **AC-12.4** | ~420 | #4939 (so the replay baseline is the post-normalisation one) | Sonnet — the derivation is diagnostic and the m1 number is a measurement, not a mechanical edit |
| **#4932** | Praxis-side region emission (§12.2): `GraphNodeType.REGION`; region-header `OperationNode`s from `visit_For`/`visit_While`/`visit_If` with body ids collected and not re-emitted at top level — **note that this restructures the visitor from a flat single-pass traversal (where `visit_Call` appends unconditionally to `_execution_order`) into a body-accumulator, stack-scoped one pushed and popped around each region body; that traversal-shape change, not the trip-count arithmetic, is this estimate's largest risk (round-1 O4)**; proved trip counts from the three language-semantics sources only, withdrawn by a `Continue` anywhere in the body; `elif` as a nested header; `self.<attr>` `ResourceNode` registration; consumer side — `lower_graph` emits no `CALL` for a `REGION` header, skips the `node_type` cross-check for one, resolves `self.<attr>` bases in the value grammar, and bumps `IR_VERSION` 1 → 2 | modify `praxis/backend/utils/plr_static_analysis/models.py`, `praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py`, `plr-sema/src/plr_sema/check/ir.py`, `tests/utils/test_computation_graph.py`, `plr-sema/tests/test_ir.py` | `uv sync --all-packages`; `uv run pytest tests/utils/test_computation_graph.py -q`; `uv run pytest plr-sema/tests/test_ir.py -q` — satisfying **AC-12.5**, **AC-12.6**, **AC-12.7**, **AC-12.8**, **AC-12.9** | ~520 | — | Sonnet — the region/execution-order restructure is diagnostic, and AC-12.9 is a non-regression judgement over a 515-line existing test file |
| **T20** | Region semantics in the checker (§12.3): L1 bounded unroll with the tail widen at `K = 8`; L2 fixpoint with final-pass-only emission and a `K`-pass hard cap; L3 restricting the blanket entry-widen to synthetic regions **and retiring the stale increment-2 compensation at `plr-sema/src/plr_sema/check/__init__.py:462-478`, whose "CALL immediately followed by a region open ⇒ widen own receiver" predicate stops identifying a region owner once headers are real (round-1 O3)**; B1 arm-wise branch walk with `⊔` at the merge, B3 keeping today's behaviour for a synthetic branch; iteration index into `Finding.detail`; `OBLIGED(graph)` (§12.3.4) implemented once and used by the relabel, AC-11.7's bijection clause and main spec AC-6.4, all amended in the same commit | modify `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/src/plr_sema/check/tipstate.py`; create `plr-sema/tests/fixtures/{loop_double_pickup,while_alternating,branch_join,trip_20,call_before_unowned_region,dead_loop_body}_graph.json`; modify `plr-sema/tests/test_{ir,tip_typestate,check_graph}.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_tip_typestate.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_wire_fuzz.py -q` — satisfying **AC-12.10**, **AC-12.11**, **AC-12.12**, **AC-12.13**, **AC-12.14** | ~380 | #4932, #4938 | Sonnet — the fixpoint's final-pass-only rule is the one place a plausible implementation is unsound |
| **#4880** | Tier 2a (§12.4.1): the source renderer over `PlanResult.kwargs` with resources as typed parameters; `plr-sema/eval/extract_runner.py` as an out-of-process runner keyed by source digest; the bytecode differential against tier 1 with divergences classified into extractor / renderer / grammar / reset causes and counted | create `plr-sema/eval/extract_runner.py`, `plr-sema/eval/tier2_extractor.py`, `plr-sema/eval/render_protocol.py`; modify `plr-sema/eval/oracle_common.py`, `plr-sema/tests/test_oracle_replay.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q`; `uv run pytest plr-sema/tests/test_import_boundary.py -q`; then `uv run python plr-sema/eval/tier2_extractor.py --corpus training/assemble/out/corpus_p25.jsonl --contracts plr-sema/data/derived_contracts.json --report $TMPDIR/tier2a.json` — satisfying **AC-12.15**, **AC-12.16** | ~430 | #4932, #4938 | Sonnet — divergence classification is diagnostic |
| **T21** | Tier 2b (§12.4.2): (1) **the recorder** — an instance-level `async functools.wraps` shim over the tool methods of the `setup.machine` object `build_setup` returns, with a `sys._getframe(1).f_lineno` call-site key, a monotonic `dict[(method_name, lineno), int]` visit counter, loud failure on a duplicate registration, and teardown that leaves the class untouched; **not** `plan_call`, which cannot fire on this execution path (round-1 O1); (2) authored region source fixtures with both tip outcomes across `for`/`while`/`if`/nesting, plus one `continue` body and one `break` body (the §12.2.3 condition-4 and `A-EARLY-EXIT` cases), all honouring the one-call-site-per-method-per-body constraint the join needs; (3) execution against the chatterbox deck under the verifier's STRICT + tracker configuration; (4) static side through §12.4.1's runner; (5) the `(operation, iteration)`-keyed comparison, joining executed `lineno` to `sideband["span"]` and thence to `sideband["origin"]`, and marking call sites skipped by `break`/`return`/`raise` as not-reached (§12.2.3); (6) the bathos sidecar and its result schema | create `plr-sema/eval/fixtures/regions/*.py`, `plr-sema/eval/region_recorder.py`, `plr-sema/eval/region_oracle.py`, `plr-sema/eval/tier2_extractor.bth.toml`; modify `plr-sema/eval/oracle_common.py`, `plr-sema/tests/test_oracle_replay.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q`; then `uv run python plr-sema/eval/region_oracle.py --fixtures plr-sema/eval/fixtures/regions --contracts plr-sema/data/derived_contracts.json --report $TMPDIR/tier2b.json` — satisfying **AC-12.17**, **AC-12.18** | ~490 | T20, #4880 | Sonnet — this is the increment's only executed soundness evidence for regions |
| **T22** | Lint and index: add `SPEC_INCREMENT_3` to `plr-sema/tests/test_spec_lint.py`'s two parametrised live-spec tests; regenerate `.praxia/docs/INDEX.md` | modify `plr-sema/tests/test_spec_lint.py`; regenerate `.praxia/docs/INDEX.md` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_spec_lint.py -q` — satisfying **AC-12.20** | ~15 | — | Haiku |

**Honest sizing note.** #4932 (~520) and T21 (~490) are both past the upper edge of one session. #4932
splits cleanly at the producer/consumer seam — the praxis-side emission plus its own tests leaves the
tree green on its own, because `lower_graph` already consumes the fields and the synthetic wrap
already stops firing when real regions appear; the consumer-side `REGION` handling and the
`IR_VERSION` bump are the second half. Its ~520 is the least trustworthy number on this table, for the
reason its own row now names: the visitor's flat-to-stack-scoped restructuring is a traversal-shape
change, and the round-1 draft's framing of #4932 as "a producer for a consumer that already exists"
was accurate about `lower_graph` and understated the producer. **Do not split T21 between the
recorder and the comparison, or between the fixtures and the comparison:** a recorder with nothing to
compare, or a fixture set with no executed comparison, is exactly the fixture-only evidence this
increment exists to replace. T21's estimate moved ~460 → ~490 in round-1 remediation — the
instance-wrapping recorder is *smaller* than extending `plan_call` would have been, but the draft's
~460 was sized against a mechanism that cannot run at all (O1), so the number is re-derived rather
than adjusted. Do not split T20 between L1 and L2 either — an unroll with no fallback silently changes
`while` behaviour with no test covering it.

---

## 12.9 What this changes in increments 1 and 2

Seven normative amendments, listed so a reader of the earlier documents is not misled by text this one
supersedes. None changes either increment's *design*.

**In `260902_plr-sema-tip-typestate-increment.md` (spec_version 9):**

1. **§10.1.3's `default` and §10.10's Q6 disposition.** *"`default` is `TOP` at graph entry and is only
   ever lowered by a transfer function that provably applies to every channel — which nothing in this
   increment does"* is superseded: E6 (§12.1.4) is that transfer function, and Q6's *"the field is kept
   for the `setup()`-aware rule"* is discharged. `default` still starts at `TOP`, and `E4` still resets
   it to `TOP`.
2. **§10.5 rule 2 ("loops widen").** Superseded by §12.3's L1/L2/L3. The rule's *soundness* argument —
   widening can only destroy a verdict — is unchanged and is still what makes L1's tail widen and L3's
   synthetic-region widen correct; what changes is that widening is no longer the *only* thing a loop
   does. §10.5's own 260902 paragraph, which relocated rule 2 to SEMA-IR region entry, is likewise
   narrowed to synthetic regions.
3. **§10.6.3's A-COMPLETES is generalised from "did not raise" to "was reached" (round-1 O7).** Its
   text — *"each operation preceding the one being checked completed without raising"* — is about
   exceptions only, and unrolling introduces two other ways for a listed body operation not to run:
   `break`/`return` terminate the region, and `continue` skips the rest of an iteration. The
   generalised form reads *"each operation preceding the pc being checked was reached and completed —
   control did not exit early via `break`, `return` or `raise` before that pc"*, and is recorded as
   `A-EARLY-EXIT` in §12.1.5's own table. `continue` is deliberately **not** folded into it: it does
   not terminate anything, so no reachability assumption discharges it, and §12.2.3's fourth
   trip-proof condition withdraws the proof instead.

**In `260902_plr-sema-ir-bytecode-increment.md` (spec_version 10):**

4. **§11.4.1's synthetic whole-stream wrap becomes the fallback, not the real-data mechanism.** It
   fires only when `has_loops`/`has_conditionals` is set and no real region was emitted — which after
   #4932 means the constructs §12.2.4 leaves out of scope (`for`/`else`, `try`), not every loop. Its
   three load-bearing properties stand; property 3's *"a later extractor that emits real regions
   changes the hash"* is discharged by §12.2.7's `IR_VERSION` bump.
4. **§11.1.4's `node_type` disposition moves `S+W` → `I+S+W`**, and the `recomputed_node_type`
   cross-check is skipped for `REGION` nodes (§12.2.2). The disposition table's *key set* is unchanged,
   so AC-11.1 is unaffected; AC-11.2's `I` half gains one field.
5. **AC-11.7's bijection clause and AC-11.11/AC-11.13's scope qualifiers.** The bijection becomes a
   function onto `OBLIGED(graph)` (§12.3.4) — the generalisation §11.12's Q1 costed and
   deferred, now forced by unrolling. The *"fixture-only, zero soundness claim over real corpus or
   graph data"* qualifiers on AC-11.11 and AC-11.13 are **deleted**, not reworded, once T21's executed
   region fixtures pass — which is the condition §11.11's named blocking follow-up set for exactly this
   deletion. **AC-11.11's "every `LOOP` has `trip is None`" half is superseded** by §12.2.3.
6. **§11.10's tier-2 divergence taxonomy.** Three causes become four (§12.4.1's table), with the
   `lower_graph` **grammar** cause closed by §12.2.5 and a new **reset** cause added; the renderer
   residual is retained, measured and explicitly not gated.

**And in the main spec:** AC-6.4's set equality and AC-7.2's totality are both re-read over
`OBLIGED(graph)` — call-bearing operations, minus the bodies of proved-`trip == 0` regions (§12.3.4)
— and §Deferred row (d)'s escape-hatch clause about `items_x`×`items_y` giving proved trip counts is
now *partly* exercised — `range(<resource>.items_x)` is consumed, `wells()` is not (§12.11).

---

## 12.10 Effect on the oracle plan (`260902_plr-sema-oracle-harness.md`)

- **Tier 1's status row changes twice.** The 40-golden-row parse residual it names
  (`.praxia/docs/plans/260902_plr-sema-oracle-harness.md:159`) is closed by #4939 with a published
  `rows_normalised` count; and the row's *"with P2.5's scaffolding every executed row runs clean, so
  tier 3 is the only source of PLR-exception ground truth"* is no longer the whole story — tier 2b is a
  second source, and unlike tier 3 it produces ground truth for constructs the corpus does not contain.
- **Tier 2's one-paragraph description is replaced by two halves** (§12.4). The plan's *"a divergence is
  an extractor defect"* sentence, already qualified twice, gets its final form: *a divergence is a
  defect in the extractor, in the renderer, in `lower_graph`'s value grammar, or in the reset
  convention; it can no longer be an adapter artefact.* The renderer cause is a measured residual, not
  a gate.
- **Tier 2's status moves from "not started" to the two-half decomposition**, and the plan's *"What this
  does not measure"* first bullet — *"until an emitter constructs `SAFE` or `WILL_FAIL` there are no
  positives to be false; the harness is armed, not firing"* — becomes false for the tip family. It
  should be rewritten to say precisely which families are firing and which are still armed, because a
  blanket claim that nothing fires is exactly the sentence that stops a reader from checking.
- **A fifth input class is *not* added.** Tier 2b is authored source fixtures inside tier 2, not a new
  tier: it shares tier 2's renderer-free extraction path and tier 1's comparison contract. Adding a
  tier would imply a new input *population*; this is the same population read a second way.

---

## 12.11 Explicitly not in this increment

- **The volume and lid guard families (#4881's other mutation classes).** Every numeric `Cmp` stays
  Kleene ½ per main spec §Open decisions 2, and a volume verdict additionally needs a `SoundnessScope`
  record for `does_volume_tracking()` that tip state does not. Unchanged from increment 1 §10.9.
- **The content-addressed cache (#4922).** The key is defined and now has one more reason to be
  version-aware; no store, no eviction, no interface. §11.12's Q3 (whether the cache stores findings or
  reports) is still open and still the reviewer's call.
- **Incremental re-check (#4923).** Unrolling makes the per-`pc` memo point non-unique — a `pc` inside
  an unrolled region has one prefix hash per iteration — which #4923 will have to handle. Named here so
  it is not discovered there; not specified.
- **Arm-scoping the extractor's `_active_states` (round-1 O4, second half).** `visit_Call` mutates a
  flat `self._active_states` set — adding `"tips_loaded"` on a tip-loading method, discarding it on a
  tip-dropping one, and auto-satisfying `TIPS_LOADED` preconditions from it
  (`praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:479-491`) — with
  no snapshot/restore around branch arms. Once #4932 actually visits both arms of a conditional in one
  stateful pass, a true arm's `pick_up_tips` leaks `"tips_loaded"` into the false arm's precondition
  computation, even though the two arms are mutually exclusive at runtime. **This increment does not
  fix it, and provably cannot regress because of it:** `preconditions` and `creates_state` are the two
  `X`-dispositioned `OperationNode` fields (`plr-sema/src/plr_sema/check/ir.py:272-288`), so
  `check_ir` never reads either — that exclusion is what AC-11.14 pins by identity, and it is why the
  leak cannot reach a verdict. It does corrupt the extractor's own hand-written precondition fields,
  which are §8's *comparison target*, so it must be fixed before §8's differential is ever read as
  evidence. The fix is a snapshot/restore of `_active_states` around each arm, and it belongs with
  whoever next touches §8, not here.
- **The error-recovery interpreter (#4924).** Unchanged.
- **A `pred`-aware `BRANCH`.** §12.3.6's B2. The natural next increment, since `condition_expr` now
  actually arrives populated; deferred item (c) still governs.
- **Trip counts from `wells()` / `items_x × items_y` cardinality.** §12.2.3 case 3 covers
  `range(<resource>.items_x)` and nothing more. `for w in plate.wells()` stays `trip = null` because
  the cardinality claim is a PLR API fact with no artifact behind it, and adopting it costs a registry
  row against zero headroom. The concrete trigger that converts it: the precondition survey emitting a
  return-cardinality record for `ItemizedResource`'s accessors, at which point it becomes DERIVED.
- **The 96-head.** `head96` is reassigned by the same `setup()` and is still excluded (§10.9); §12.1.2
  scopes P5 to the P1a channel attribute the tip feature already uses.
- **Aliasing.** A-SINGLE is still assumed, not checked, and unrolling does not weaken it.
- **`check_graph` never raising** on a malformed payload. Still #4882's question.
- **Any precision target.** Deferred (f) stands. The m1 number in AC-12.4 is a *directional* gate on
  one mutation class, not an `UNKNOWN`-rate threshold.

---

## 12.12 Open questions for the adversarial round

Six, and the first three are the ones where a design was chosen over a live alternative rather than
found.

**Post-round-1 status.** Round 1 (challenger `260903_plr-sema-real-programs-round1-challenger.md`,
defender `260903_plr-sema-real-programs-round1-defender.md`) adjudicated all six. **Q2** (the
`wells()` line) and **Q3** (unroll + fixpoint, `K = 8`) are **non-issues by agreement of both sides**
and are kept below as the record of why. **Q5** is **resolved by O5** — §12.2.2 now argues why
`REGION` is not `FOREACH`/`CONDITIONAL`, which was the precondition the round set on adjudicating the
registry-row half; the registry-row question itself is carried forward unresolved. **Q6** is
**agreed** (the conservative "no"). **Q1 is sharpened rather than closed** — round 1 called the rule
sound for its stated target, and the remediation then found `load_state`, a live near-miss that forced
a third conjunct (§12.1.2); the question is now about the discriminator, not about existence.
**Q4 was ruled moot until O1 was resolved and is now live again**, since the executed side finally has
a producer to compare an iteration index against.

1. **§12.1.2's template-free reset rule.** The rule is stated as a three-conjunct whole-expression
   property rather than as a `DictComp` template, and §12.6 says plainly that the reason is HM-25's
   zero headroom. It **sharpens** `TOP → NO_TIP`, so unlike a widening rule it is not free.
   **Round 1 adjudicated this "sound for its stated target"** — `TipTracker.__init__` sets both state
   fields to `None` regardless of arguments, so fresh-only construction always yields `NO_TIP` — but
   the remediation then found a live near-miss the round did not: `LiquidHandler.load_state` satisfies
   conjuncts 1 and 2 and was excluded only by the newly added conjunct 3. That is one near-miss found
   in one pass over one class, so the question a round 2 should press is **not** the original "is
   there such an expression?" but the sharper: **how many more are there, and is statement-position
   the right discriminator or merely the one that separated the two cases we happen to have?** If a
   second discriminator is needed, the remedy is the template plus a sixth HM-25 pattern plus a cap
   conversation, and the document should say so rather than defending the cheaper rule.
2. **§12.2.3's three proof sources, and the `wells()` line.** `range(plate.items_x)` is proved and `for
   w in plate.wells()` is not, on the grounds that the first is language semantics over a field the
   graph carries and the second is a PLR API fact. A reviewer may think that line is drawn in the wrong
   place — `wells()` is the shape real protocols actually write, and the cardinality is arguably
   derivable from `ItemizedResource`'s own source. Which side of the line it falls on decides whether
   this increment's loop precision reaches real plate protocols at all.
3. **§12.3's unroll-and-fixpoint split, and `K = 8`.** Three sub-questions. (a) Is *both* right, or
   would fixpoint-only be the honest answer, given that a height-2 lattice converges in two passes and
   the only thing unrolling buys is the ability to *name the iteration*? (b) Is `K = 8` defensible, or
   is the tail-widen clause doing all the work and `K = 2` the principled value? (c) Should the unroll
   live in the walk (as specified, so the hash is `K`-independent) or in the lowering (so a disassembly
   shows what was checked)? The document takes a position on all three; (a) is the one where a reviewer
   could reasonably reverse it.
4. **§12.3.4's iteration index in `Finding.detail`.** A string prefix on a free-form field is the
   minimal change and is machine-unreadable. The alternative is `sideband.unroll: {pc: iteration}`,
   which is structured but is state about *a walk* stored in a sideband that describes *a program*.
   Nothing consumes either today; tier 2b's `(operation, iteration)` comparison will be the first, and
   it can read the prefix. A reviewer who thinks the structured form should land now should say so
   before T21 writes a parser for the string.
5. **`GraphNodeType.REGION` and the registry.** §12.6 argues it is a shape marker on praxis's own model
   and gets no row. The counter-argument is that HM-11 registers `PreconditionType`, another enum on
   the same model, so the precedent points the other way. The distinguishing claim is that
   `PreconditionType`'s members assert what kinds of PLR precondition exist while `REGION` asserts
   nothing about PLR — a reviewer may find that too fine a distinction to spend on, in which case the
   remedy is a cap conversation, not a redesign.
6. **Can an *unobserved* `setup()` ever be assumed?** §12.1.5 says no: a parameter `lh` with no
   observed reset stays `TOP`, and every protocol in the corpus that arrives as a *function* rather
   than as a call sequence will therefore be uninformative about tip state. That is a large precision
   cost paid for a soundness property, and there is a real middle position — a `SoundnessScope`
   environment record of the form "this analysis assumes the handler was set up and had no tips
   mounted", which main spec deferred row (b) already reserves the machinery for. The document does not
   take that position because the record does not exist yet; a reviewer may think it should be built
   here rather than deferred, since the same record is what the volume family will need.

## 12.13 Implementation record (sprint 121)

- #4939 b35bc338: premise corrected — the 40 golden rows never parse-failed; they executed and
  raised inside `training/verify/deck.py`'s `infer_layout`/`ground_ref`. Only 1 of 16
  underscore-shaped refs meets AC-12.19's declared-base gate; `rows_normalised` = 1. The verifier
  types non-`'tip'`-prefixed names as `Plate` (coxswain-side defect, out of scope).
- Harness follow-up #4944 85fe6eb5: the regenerated corpus (assembly 0.1.5, 900 → 1427 rows) plus a
  replay run without `--sidecar` produced 297 spurious totality violations; fixed with a
  `rows_setup_error` bucket (13 rows), content-digest `record_id`, sidecar re-baseline: 330 executed
  / 525 ops / 191 exact join / agreement 1.0 / 0 unsound / 0 totality
  (`outputs/plr-sema/oracle_replay_260903_rebaseline.json`). Like-for-like vs 260902 on the 728
  shared rows: 216/341/0/0.
- #4932 297ce8f9 + 976ed6d8: as specified; AC-12.6 trip values 3,4,3,12,None,None,None,0 observed;
  `for`/`while … else` left flat (out of scope); one PRE-EXISTING extractor test failure
  (`test_resource_on_deck_preconditions`, assert 4 == 3) reproduced at the parent commit, attributed
  to b5635334.
- #4938 b39020cd + f1cecd0e: `entry_reset == {"method":"setup","post":"no_tip"}` derived;
  AC-12.1(iv) confirmed conjuncts 1–2 alone select {setup, load_state}; real bug fixed —
  `TipTracker.__init__` uses `AnnAssign`, which `_effects` never scanned (new `_constructor_state`
  pass). AC-12.4 on the regenerated corpus: m1 **84/101** WILL_FAIL at the raised index (was 1/55),
  17 UNKNOWN, 0 unsound; m2 **190/190**; tier 1 byte-identical to the rebaseline. The 91% bar (50/55)
  is NOT met at 83%: all 17 misses collapse to a lone `transfer` call whose derived guard is
  `guard_predicate_unparsed` — follow-up #4946. No tuning was applied.
- T20 cea29d77: as specified; the O1 counterexample yields `SAFE` at iteration 1 and exactly one
  WILL_FAIL verdict at iteration 2, sited at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:535`
  (the raise site); `while_alternating` fixture simplified
  to a single-call body (documented in its test) because a pick+drop body converges on pass 0 and
  would not exercise the final-pass rule; `obliged_operation_ids` implements `OBLIGED(graph)`; two
  existing tests re-read over it.
- #4880 12bc591a (tier 2a): 330 rows compared as bytecode, extractor-cause divergences 0, renderer
  122, grammar 0, reset 0, 235 agreeing, directional 208/210; `RESOURCE` declarations and
  `WIDEN(depends_on_params)` excluded from the compared substream (structural asymmetries). Two
  harness defects fixed (vendor PLR subclass recognition via MRO; slot canonicalisation shifted by
  dropped residuals → compare by resource name).
- T21 88f01fdb (tier 2b): 11 fixtures (`for` ×2, `while` ×2, `if` ×2, nested, `range(0)`, `continue`,
  `break`, straight-line); `region_unsound = 0`, `region_will_fail_fired = 3` (one per shape), trip
  mismatches 0; bathos sidecar validates. **Spec claim falsified:** §12.4.2's "`line_number` is
  already populated at every call site" is false — `_current_line` is set to 0 in `__init__` and
  never reassigned, so every `OperationNode.line_number == 0` (predates #4932). The recorder's
  `(method, lineno)` join therefore degrades to method-only today and is guarded by a
  fixture-wide one-call-site-per-method rule + `DuplicateCallSiteError`. Filed as a praxis-side
  defect, backlog #4948.
- T22: done in 8868b34e (lint extended for the new AC gating).

Status (260903, sprint 121 close): all increment-3 tasks landed; this section is a factual record
of what was observed against what was specified, not a re-derivation of the spec's argument.

---

## References

- Main specification (amended): `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` — §0 (the
  organizing claim; no `SAFE` constructed without an evaluated guard), §0.1 (the DERIVED /
  HAND-MAINTAINED classification), §6.2 (the graph wire format), §7.3–7.4 (contract table and gap
  ledger), §9.1–9.4 (registry, budget, ratchet), §Deferred rows (a)/(c)/(d)/(f) + the boundary summary,
  §Open decisions 1–3, RISK-1.
- Increment 1 (amended): `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md` — §10.1.3
  (channel identity and `default`), §10.2.1–10.2.6 (P1–P4, the bridge, the families), §10.3 (atoms and
  evaluation), §10.4 (E1–E5), §10.5 (the walk, rules 1–3), §10.6.3 (the assumptions table), §10.7's
  task row and AC-10.9/AC-10.10/AC-10.12, §10.8 (registry and vocabulary), §10.9, §10.10 Q4/Q5/Q6/Q7.
- Increment 2 (amended): `.praxia/docs/specs/260902_plr-sema-ir-bytecode-increment.md` — §11.1.2–11.1.5
  (values, opcodes, dispositions, the widen vocabulary), §11.2.1–11.2.4 (both lowerings, the tool-name
  barrier, the trust rule), §11.3 (canonical form, hash, cache key), §11.4.1–11.4.4 (the seam, the
  synthetic wrap, `operation_id`, totality), §11.6 (hand-maintained impact and HM-21's redefinition),
  §11.7 (AC-11.1 through AC-11.14), §11.9, §11.10, §11.11's named `extract/` follow-up, §11.12 Q1/Q3/Q7.
- Oracle plan (affected): `.praxia/docs/plans/260902_plr-sema-oracle-harness.md` — the soundness
  contract table, tiers 1–4, "Where it lives", the 260902 status table. Backlog `#4879`/`#4880`/
  `#4881`/`#4882`.
- Adversarial round 1 on increment 2:
  `.praxia/docs/audits/260902_plr-sema-ir-round1-challenger.md` (O1 is the origin of #4932's region
  emission and of the false-`SAFE` loop counterexample §12.3.2 answers; O4 is the origin of §12.2.5's
  `self.<attr>` registration) and `.praxia/docs/audits/260902_plr-sema-ir-round1-defender.md`.
- **Adversarial round 1 on *this* increment:**
  `.praxia/docs/audits/260903_plr-sema-real-programs-round1-challenger.md` (O1–O6, plus the
  orchestrator's O7 addendum) and
  `.praxia/docs/audits/260903_plr-sema-real-programs-round1-defender.md` (per-objection verdicts —
  O1/O2/O3/O6 CONCEDE, O4 and O5 PARTIAL, O7 CONCEDE for `continue` and PARTIAL for
  `break`/`return`/`raise` — a severity table, and an eight-item ordered remediation list). The
  defender's list is the remediation contract; the changelog below maps each item to the text that
  changed, and records the one correction found while applying it that neither report raised.
- Backlog: `#4938` (derived `setup()` head-reset), `#4932` (extractor regions), `#4880` (tier 2),
  `#4939` (loader well-ref normalisation); deferred hooks `#4922`/`#4923`/`#4924`; `#4881` (tier-3
  mutants, the gate AC-12.4 moves).
- Code read for this document: `plr-sema/src/plr_sema/check/tipstate.py`;
  `plr-sema/src/plr_sema/check/__init__.py`; `plr-sema/src/plr_sema/check/ir.py`;
  `plr-sema/src/plr_sema/derive/receiver_state.py`; `plr-sema/src/plr_sema/derive/__main__.py`;
  `plr-sema/src/plr_sema/_hand_maintained.py`; `plr-sema/src/plr_sema/verdict.py`;
  `plr-sema/eval/oracle_common.py`; `plr-sema/eval/tip_mutants.py`; `plr-sema/eval/oracle_replay.bth.toml`;
  `plr-sema/tests/test_spec_lint.py`; `plr-sema/scripts/check_spec_citations.py`;
  `plr-sema/scripts/check_spec_crossrefs.py`;
  `praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py`;
  `praxis/backend/utils/plr_static_analysis/models.py`; `tests/utils/test_computation_graph.py`;
  `training/verify/verifier.py`; `training/verify/deck.py`. Additionally read during round-1
  remediation: `training/verify/dispatcher.py`; `plr-sema/tests/fixtures/branchy_graph.json`;
  `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py` (`load_state`) and
  `external/pylabrobot/pylabrobot/resources/tip_tracker.py` (`load_state`).
- Data read: `outputs/plr-sema/oracle_replay_260902.json` — the tier-1 numbers this document cites
  (900 rows processed, 268 executed, 426 operations, 0 unsound, 0 `check_graph` exceptions, 0 totality
  violations, 189 of 189 crosscheck agreement) are its `summary_flat` block verbatim. **The 40
  unparseable golden rows are *not* in that file** — its own `rows_parse_error` is 0, because the
  golden rows are counted as skipped rather than as parse errors; the 40 comes from the oracle plan's
  own status table (`.praxia/docs/plans/260902_plr-sema-oracle-harness.md:159`), and #4939's gate is
  written to publish the achieved number rather than to hit that one. **The m1 1-of-55 and m2 108-of-108
  figures are not in any committed artifact**: `plr-sema/eval/tip_mutants.py` writes its report to a
  `--report` path (`plr-sema/eval/tip_mutants.py:36-43`), and the 260902 run's numbers reached this
  document through the sprint handoff, not through a file. AC-12.4's gate therefore **re-measures**
  m2's 108/108 rather than trusting it, and a fixer who finds a different baseline should publish the
  difference rather than reconcile to the number written here.
- PLR source at submodule pin `dd79c4c89`:
  `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py` (`head` at `:162`, `setup`'s head
  reset at `:187-214` and `:197`, the `HasTipError` raise at `:534-535`) and
  `external/pylabrobot/pylabrobot/resources/tip_tracker.py` (`__init__`'s two `None` writes at
  `:39-46`, `has_tip` at `:52-55`, `get_tip`'s `NoTipError` at `:57-66`).

---

## Remediation changelog (round 1)

Applied against the defender's adjudication of the round-1 challenger, in the defender's own order.
`status` moved `draft` → `reviewed-round-1`; `spec_version` stays **11** — every entry below is text,
one set definition, one added trip-proof condition, two assumption rows, one new fixture and one
revised AC. No opcode, no verdict, no wire change, no registry change, and no new AC id (the AC count
is unchanged at 20, so nothing renumbers and every existing gate still resolves).

| item | O-id | verdict | change | section(s) |
|---|---|---|---|---|
| 1 | **O1** | CONCEDE (blocking) | §12.4.2's "Execution mechanics" rewritten: `plan_call` reuse is **retired** and shown to be structurally impossible on this execution path (it is a function of a JSON call dict and its list index, reached only from `_execute`'s `call_sequence` loop, and `recording_plan_call` patches that module-level name). Replaced by a normative **instance-level** recorder: an `async functools.wraps` shim over the tool methods of the `setup.machine` object, a `sys._getframe(1).f_lineno` call-site key, a monotonic `dict[(method_name, lineno), int]` visit counter, and a join to the static side through `OperationNode.line_number` → `sideband["span"]` → `sideband["origin"]`. Adds the fixture-design constraint (one call site per method per body) that makes the join a lookup rather than a heuristic, and requires loud failure on a duplicate key | §12.4.2 (new normative block + two new paragraphs) |
| 1 | **O1** | CONCEDE | AC-12.17 gains four sub-assertions pinning the producer, of which (i) — `verifier.plan_call` is never invoked during a region-fixture run, asserted by leaving `recording_plan_call` installed and requiring its `planned` list to stay empty — is the stub-defeating half | AC-12.17 |
| 1 | **O1** | CONCEDE | T21's row rewritten to name the recorder as sub-step (1) and the `continue`/`break` fixtures as part of (2); estimate re-derived ~460 → ~490 with the reason stated (the old number was sized against a mechanism that cannot run, not against a bigger one) | §12.8 T21, honest-sizing note |
| 2 | **O2** | CONCEDE, remedy (a) | §12.3.4 now defines **`OBLIGED(graph)`** once — call-bearing operations, minus those nested at any depth in a region whose lowered `LOOP` carries a proved `trip == 0` — and AC-6.4(amended), AC-7.2 and AC-11.7's function-onto clause all read over it. Remedy (b) (a "totality-only dry visit") is named and rejected, with the reason: it needs its own rule for which state to evaluate against and which finding to emit, and any finding it emitted would assert something about code the program provably does not run. A closing paragraph states why the exclusion cannot be abused (`trip == 0` is *proved*, never inferred from ignorance) | §12.3.4 |
| 2 | **O2** | CONCEDE | AC-12.6's `range(0)` case now states the exclusion explicitly and requires the body to be non-empty (a real `pick_up_tips`) or the "zero findings" assertion is vacuous; AC-12.13 gains a second assertion pinning the carve-out from the other side — `OBLIGED` differs from the plain call-bearing set on **exactly** dead-region bodies, and on AC-12.10's fixture the two are equal | AC-12.6, AC-12.13 |
| 3 | **O3** | CONCEDE | §12.3.3's L3 additionally **retires** the stale increment-2 compensation at `plr-sema/src/plr_sema/check/__init__.py:462-478`, with its own docstring's pre-§12.2.2 justification quoted as the reason it no longer identifies a region owner; a following paragraph records that AC-12.10's fixture escapes the bug only by coincidence (adjacency to a reset, which E6 overwrites) | §12.3.3, §12.2.2 (one cross-reference) |
| 3 | **O3** | CONCEDE | AC-12.14 gains assertion (iv) and the named fixture `call_before_unowned_region_graph.json`: `setup()`, then `pick_up_tips(use_channels=[0])`, then a region header it does not own over a *different* receiver — the reset deliberately **not** adjacent to the region, because adjacency is what masks the defect. T20's row gains the fixture and the retirement clause | AC-12.14, §12.8 T20 |
| 4 | **O7** | CONCEDE (`continue`) | §12.2.3's trip-proof rule gains a **fourth** condition: `trip = null` whenever the body contains a `Continue` at any nesting depth within it, excluding nested function/lambda defs. A worked paragraph gives the counterexample (a `continue` past a `drop_tips` on iteration 1 makes L1's threaded state wrong at an iteration the execution *does* reach) and states why A-COMPLETES does not cover it | §12.2.3 |
| 4 | **O7** | PARTIAL (`break`/`return`/`raise`) | A-COMPLETES generalised from *"completed without raising"* to *"was reached and completed — control did not exit early via `break`, `return` or `raise` before that pc"*, recorded as the **`A-EARLY-EXIT`** row in this document's own assumption table; and tier 2b's comparison is required to mark call sites skipped by early exit as **not-reached**, the same exemption `compare` already gives post-raise operations | §12.2.3, §12.1.5, §12.9 item 3 |
| 4 | **O7** | CONCEDE | AC-12.6's loop list grows to seven with a `continue`-containing `for i in range(4)`; trip values corrected to `3, 4, 3, 12, None, None, None`; the `range(0)` loop becomes the eighth. T21 gains a `continue` fixture and a `break` fixture | AC-12.6, §12.8 T21 |
| 5 | **O4** (first half) | CONCEDE | #4932's row names the visitor's flat-single-pass → body-accumulator (stack-scoped) restructuring as **the estimate's largest risk**, and the honest-sizing note says plainly that the draft's "a producer for a consumer that already exists" framing was accurate about `lower_graph` and understated the producer | §12.8 #4932, honest-sizing note |
| 6 | **O4** (second half) | REBUT → named follow-up | §12.11 gains a bullet on `_active_states`'s cross-arm leak: what it is, why #4932 makes it reachable, why it **provably cannot regress any AC here** (`preconditions`/`creates_state` are the two `X`-dispositioned fields `check_ir` never reads), and why it must nonetheless be fixed before §8's differential is read as evidence | §12.11 |
| 7 | **O5** | PARTIAL — keep `REGION` | §12.2.2 gains a paragraph: `FOREACH`/`CONDITIONAL` are **live**, not dead — `branchy_graph.json` carries `"node_type": "conditional"` on a *call-bearing* `aspirate` — so reuse would make `node_type`'s reading depend on `method_name`, which no other disposition does. The loop-vs-branch distinction is recovered losslessly from which region field is populated. Retiring the two as dead is explicitly *not* claimed | §12.2.2 |
| 8 | **O6** | CONCEDE | §12.1.5's table gains **`A-NO-REINTRODUCTION`**, tracing the `load_state` path in full: it matches the HM-24 bridge shape, `_classify_write` classifies `TipTracker.load_state` as `HAS_TIP`, and it discharges safely **by machinery rather than by argument** — `channels_for_call` returns `None` for it, so `_apply_transfer` widens. What would break it is named: a reintroducing method that *does* resolve an exact channel set | §12.1.5 |
| — | lint | — | Every `/tmp/...` report path in §12.8's gate commands replaced with `$TMPDIR/...`, since the Bash sandbox writes only under `$TMPDIR` | §12.8 (four paths, three rows) |
| — | housekeeping | — | `status` → `reviewed-round-1`; `sources` extended with both round-1 audit files and the six ranges read to verify the remediation; References gains a round-1 entry for this increment and the extra code read; §12.9 grows 6 → 7 amendments; §12.12 gains a post-round-1 status paragraph (Q2/Q3 non-issues by agreement, Q5's precondition discharged by O5, Q6 agreed, Q1 sharpened, Q4 live again now that O1 has a producer); §12.5's oracle table gains four rows for the claims this round added | frontmatter, References, §12.9, §12.12, §12.5 |

### Correction made in passing, disclosed because neither round-1 report raised it

Verifying O6's `load_state` trace surfaced a defect in **this document's own P5 rule**, and it would
have disabled the entire increment at the current pin. `LiquidHandler.load_state` assigns
`self.head = {c: TipTracker(thing=f"Channel {c}") for c in head_state}`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:239-257`, the assignment at
`:248`) — an expression that satisfies the draft's conjunct 1 (constructs only `TipTracker`s) and
conjunct 2 (loads no `self.head`) exactly as `setup`'s does. Under the two-conjunct rule P5 would have
selected **two** qualifying methods, hit its own more-than-one fail-closed clause, emitted nothing,
and silently reverted every verdict to `UNKNOWN` — a failure that would have presented as a wiring bug
rather than as a rule defect.

**Fix: a third conjunct — the assignment must be a direct statement of the method's body, not nested
inside an `If`/`For`/`While`/`Try`/`With`/`match`.** This is not a patch chosen to make the arithmetic
come out: a reassignment that runs on only some paths through `m` cannot establish a post-state on all
of them, and E6 asserts a post-state unconditionally, so withdrawing the reset there is correct
independently of how many methods it happens to separate. `setup`'s assignment is top-level;
`load_state`'s sits under `if head_state and self.head == {}:`.

**AC-12.1 gains sub-assertion (iv) to keep the fix honest**, and it is deliberately checked against
**real PLR rather than a synthetic fixture**: the set satisfying conjuncts 1–2 alone must be exactly
`{"setup", "load_state"}` and the set satisfying all three exactly `{"setup"}`. A synthetic fixture
would have tested the rule against an example built to fit it; this tests it against the codebase that
broke it. §12.12's Q1 is re-pointed accordingly — the live question is no longer "does such an
expression exist" (one does) but "is statement position the right discriminator, or merely the one
that separated the two cases we have".
