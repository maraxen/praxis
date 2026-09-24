---
title: "plr-sema increment 1 — per-channel tip typestate (deferred (a) and (c), narrowed to the tip-state guard family)"
description: "First post-corpus increment to the plr-sema pre-corpus specification. Narrows deferred item (a) (abstract domain) to a three-element per-channel tip typestate lattice and deferred item (c) (predicate language) to three atom productions over that lattice, so that the tip-loading / tip-requiring / tip-dropping method families produce real SAFE and WILL_FAIL findings instead of UNKNOWN. Every method family, every tracker class, every state field, every effect and every channel-arity default is DERIVED by AST inspection of PLR source and of the shipped contract table -- no hand-written method contract, and no hand-typed exception-class name (the two tip-state exception names come from plr_exception_taxonomy.json's own tip_state category, narrowed by that artifact's own module field). Adds one REASON_VOCABULARY member (7 -> 8 of 12), two check/graph.py mirror fields, one registry row (HM-24, the front end's six syntactic patterns), and no wire-format change. Gated by the oracle harness (#4879 corpus replay, #4881 mutants), not by a threshold. Revised after adversarial round 1 -- see the remediation changelog at the end."
status: reviewed-round-1
spec_version: 9
amends: 260901_plr-sema-pre-corpus-spec.md
task_id: 260902_sema-oracle-tipstate
date: '260902'
confidence: medium
sources: "Read this session, in full or in the cited ranges: .praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md (§0, §3, §6.2, §7.2-7.3, §9, Deferred, Open decisions, Fixer task decomposition); .praxia/docs/research/260901_plr-sema-research-a-d.md (Q3, R3); .praxia/docs/research/260901_plr-sema-research-c-e.md (Q2, Q5); .praxia/docs/plans/260902_plr-sema-oracle-harness.md; plr-sema/src/plr_sema/verdict.py; plr-sema/src/plr_sema/check/__init__.py; plr-sema/src/plr_sema/check/graph.py; plr-sema/src/plr_sema/derive/__init__.py; plr-sema/scripts/oracle_spike.py; plr-sema/eval/oracle_common.py; plr-sema/tests/fixtures/simple_transfer_graph.json; plr-sema/data/derived_contracts.json (LiquidHandler.{aspirate,pick_up_tips,drop_tips} and TipTracker.{get_tip,add_tip,remove_tip} entries, read verbatim); training/verify/data/plr_preconditions.json (LiquidHandler.{aspirate,pick_up_tips,drop_tips} records); training/verify/data/plr_exception_taxonomy.json (HasTipError/NoTipError entries); training/verify/failure_taxonomy.py:70-109; training/verify/dispatcher.py:37-41,159-161; training/floor_gen/exec_verify.py:186-210; praxis/backend/utils/plr_static_analysis/models.py:520-651; external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py (:162-164, :197, :455-504, :525-576, :645-726, :940-978, :1372-1390) and external/pylabrobot/pylabrobot/resources/tip_tracker.py:50-118, both at submodule pin dd79c4c89."
---

# Increment 1: per-channel tip typestate

> **This document amends `260901_plr-sema-pre-corpus-spec.md` by reference.** It adds §10 to that
> document's numbering and edits exactly four things in it: §3.3's `REASON_VOCABULARY` (one new
> member), §6.2's normative mirror field table (two new rows), §9.2's registry (one new row, HM-24),
> and the [§Deferred](#references) table's (a) and (c) rows (narrowed, not closed). Everything else
> in spec_version 8 — the verdict wire type, `join`, the telemetry schema, the fork-drift tests, the
> derivation closure mechanic, the differential harness, the budget and ratchet — is **unchanged**.
> No `schema_version` bump anywhere.

## 10.0 What this increment is, in one paragraph

`plr-sema` v1 is a **trivially sound** analyzer: `check/` constructs no `SAFE` or `WILL_FAIL`
`Finding` anywhere (`plr-sema/src/plr_sema/check/__init__.py:177-257` — seven constructors, every
one of them `verdict=Verdict.UNKNOWN`), and `join` maps the empty multiset to `UNKNOWN`
(`plr-sema/src/plr_sema/verdict.py:278-279`). Main spec §0 states this and states plainly that it is
a weak claim. This increment converts the **smallest** family of guards into real verdicts: the
**per-channel tip typestate** of a `LiquidHandler`'s `head` trackers. It is the smallest family that
is worth doing because it is the only one for which (i) PLR raises unconditionally rather than under
a runtime tracking flag, (ii) the abstract domain is finite and three-valued so no widening operator
is needed, and (iii) every fact the analyzer needs — which methods load a tip, which require one,
which drop one, which field holds the state, which exception names mean "tip state" — is derivable
by inspection, so main spec decision 2 ("no hand-written method contracts") survives intact.

**Deliverable of this increment, stated as the property that must become true:** a graph in which
`pick_up_tips` is applied twice to a statically-known channel set, with no intervening drop, produces
`Verdict.WILL_FAIL` on the second operation, with `category="precondition_state"` and
`plr_site=PlrSite("external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py", 535,
"LiquidHandler.pick_up_tips")`. Today it produces ten `UNKNOWN` findings.

| axis | v1 (spec_version 8) | this increment |
|---|---|---|
| abstract domain | none — deferred (a) | per-channel tip typestate, 3 elements, no widening operator |
| predicate language | none — every guard is `guard_predicate_unparsed` | 3 atom productions over the tip typestate; everything else still ½ |
| verdicts constructed by `check/` | `UNKNOWN` only | `UNKNOWN`, `SAFE` (per-guard), `WILL_FAIL` (per-guard) |
| `Verdict` / `Finding` / `AnalysisReport` / `join` | — | **unchanged** |
| `REASON_VOCABULARY` | 7 of cap 12 | 8 of cap 12 |
| registry rows | 22 live, cap 24 | 23 live, cap 24 |
| gate | unit tests | unit tests **plus** oracle #4879 replay and #4881 mutants |

---

## 10.1 The domain (deferred item (a), narrowed)

### 10.1.1 The lattice

For one channel of one `LiquidHandler` receiver, the abstract tip state is

```
TipState  ::=  NO_TIP  |  HAS_TIP  |  TOP
```

with the **information order** `NO_TIP ⊑ TOP`, `HAS_TIP ⊑ TOP`, `NO_TIP ⋢ HAS_TIP`, and the join

| ⊔ | NO_TIP | HAS_TIP | TOP |
|---|---|---|---|
| **NO_TIP** | NO_TIP | TOP | TOP |
| **HAS_TIP** | TOP | HAS_TIP | TOP |
| **TOP** | TOP | TOP | TOP |

`TOP` means "the analyzer knows nothing about this channel". The concretization is
`γ(NO_TIP) = {states where this channel's tracker holds no tip}`, `γ(HAS_TIP)` its complement within
the tracker's reachable states, `γ(TOP)` = everything. `⊑` is `γ`-inclusion; the join is the least
upper bound; the lattice has height 1 above its two atoms, so it is **finite-height and needs no
widening operator** — which is exactly research a-d's Q3 finding (`260901_plr-sema-research-a-d.md:246-254`:
"the whole `SUPPORTED_TOOLS` frontier is tip state on `self.head[channel]` … That is textbook
typestate", and `:256-266`'s cost table ranking typestate the primary candidate and octagons
explicitly not indicated). Main spec's Deferred (d) row already anticipates this: "If (a) resolves
to a finite-height typestate domain, (d) resolves to *nothing to design*."

**There is no ⊥ in this lattice.** Main spec §Open decisions 1 reserves ⊥ for the deferred-(a) state
type on the grounds that it prunes dead paths and is the branch-merge join's unit. This increment
has neither branches (§10.5) nor an emptiness-detecting transfer function, so introducing ⊥ now
would add an element nothing constructs and nothing consumes. `Verdict.UNREACHABLE` stays reserved
and unused; `Verdict.from_wire` (`plr-sema/src/plr_sema/verdict.py:96-113`) is untouched.

### 10.1.2 The two orders, kept apart (main spec §Open decisions 3)

`⊔` above is the **information order** (Kleene / Sagiv-Reps-Wilhelm: knowing less is higher). It
governs merging abstract states *before* any guard is evaluated. It is **not** the order `join`
implements. `plr_sema.verdict.join` (`plr-sema/src/plr_sema/verdict.py:220-285`) implements the
**obligation order** `SAFE ⊏ UNKNOWN ⊏ WILL_FAIL` over already-emitted `Finding`s, and this
increment does not change one line of it. The two live at different pipeline stages, exactly as
`verdict.py:232-246` says. Concretely, in this increment: `TipState.⊔` has call sites only inside the
new `check/tipstate.py` module's state merge; `join` has its existing call site at
`check/__init__.py:334` and nowhere else.

### 10.1.3 Channel identity

`LiquidHandler` holds one tracker per channel:
`self.head: Dict[int, TipTracker] = {}` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:162`),
populated at setup as `{c: TipTracker(thing=f"Channel {c}") for c in range(self.backend.num_channels)}`
(`:197`). **The channel count is a backend property and is therefore never statically known** — it is
`self.backend.num_channels`, resolved at `setup()` time. The abstract state consequently maps a
*channel index* to a `TipState` and carries a default for every index not in the map:

```
ChannelState  =  (default: TipState, exact: dict[int, TipState])
state(c)      =  exact.get(c, default)
```

`default` is `TOP` at graph entry (§10.5) and is only ever *lowered* to `NO_TIP`/`HAS_TIP` by a
transfer function that provably applies to every channel — which nothing in this increment does. In
practice `default` stays `TOP` for the whole walk and precision comes entirely from `exact`.

**How an operation's channel set is obtained.** PLR resolves it identically in all four
channel-taking `LiquidHandler` methods:

```python
use_channels = use_channels or self._default_use_channels or list(range(len(tip_spots)))
```

— `liquid_handler.py:501` (`pick_up_tips`), `:650` (`drop_tips`), `:958` (`aspirate`, over
`resources`), `:1152` (`dispense`, over `resources`). The analyzer mirrors that three-term disjunction
exactly, over `OperationNode.arguments` (a `dict[str, str]` of argument name → source expression,
`praxis/backend/utils/plr_static_analysis/models.py:536-538`):

1. **Explicit.** `arguments["use_channels"]` present and `ast.literal_eval`s to a list of `int` →
   `channels = that list`, exact.
2. **Instance default.** If any operation anywhere in the graph, on this receiver variable, has a
   `method_name` in the derived **channel-default-disabler set** (§10.2.3, P3b) → `channels = ⊤` for
   this and every operation on that receiver, permanently. (`self._default_use_channels` is written
   only at `liquid_handler.py:1385` and `:1390`, both inside the `use_channels` context manager —
   which is a **synchronous** `@contextlib.contextmanager`, `liquid_handler.py:1363-1364`, not an
   async one (round 1, O9); the analyzer cannot see whether a `with` block is active, so a single
   occurrence of the writer method poisons the receiver.)
3. **Arity default.** Else, if the method has a derived channel-default parameter `p` (§10.2.3, P3a)
   and `arguments[p]` `ast.literal_eval`s to a list of length `n` → `channels = [0 … n-1]`, exact.
4. **Otherwise `channels = ⊤`** — the operation's channel set is unknown.

`channels = ⊤` is not "no channels": it is "possibly any channel", and it forces the widening in
§10.5. Rule 1 is tried before rule 3 because PLR's own `or` chain does (`:501`), and rule 2 sits
between them for the same reason.

**Measured against the shipped fixtures, honestly.** The committed four-operation fixture
(`plr-sema/tests/fixtures/simple_transfer_graph.json:13-101`) carries `arguments` of
`{"resource": "tips"}`, `{"resource": "source[\"A1\"]", "volume": "100"}`, … — no `use_channels`, and
no key matching any PLR channel-default parameter (`tip_spots`/`resources`). **Every operation in
that fixture therefore falls to rule 4, and every verdict in it stays `UNKNOWN` under this
increment.** This contradicts the natural expectation (and the dispatch brief's suggested acceptance
criterion) that "the four-op fixture flips specific ops to specific verdicts"; it does not, and
AC-10.4 pins that it does not, rather than pretending otherwise. New fixtures are required
(§10.7, AC-10.1–10.3). The same is true of the oracle harness's tier-1 adapter, for a different and
more interesting reason — see AC-10.11's vacuity disclosure and §10.10's Q3 disposition.

### 10.1.4 The abstract state

```
AbstractState = dict[receiver_variable: str, ChannelState]
```

State is **per `OperationNode.receiver_variable`** (`plr-sema/src/plr_sema/check/graph.py:88-91`), not
per `receiver_type`: two `LiquidHandler`s in one protocol are two independent states. Any receiver
variable whose `receiver_type` is not a class carrying a derived channel-tracker attribute (§10.2.1)
never gets an entry, and every operation on it behaves exactly as it does today — `UNKNOWN`,
unchanged. That is the whole of the "other receiver types" answer: they are not touched, not
special-cased.

---

## 10.2 The derived inputs (four build-time passes) — nothing here is hand-typed

Everything the evaluator needs is computed at build time by `plr_sema.derive` and shipped in
`plr-sema/data/derived_contracts.json`. `check/` remains stdlib-only, imports no `pylabrobot`, and
performs no AST work — main spec §6.2's packaging fact is untouched.

The existing derivation (`plr-sema/src/plr_sema/derive/__init__.py:446-492`) already gives us guards
with polarity (`InlinedGuard.kind`, `:406-432`), the raising class (`InlinedGuard.raises`), the
defining site, and depth. It throws away one field that this increment needs:
`SurveyRecord.dropped_calls` (`derive/__init__.py:181-199`) — the receiver-qualified call expressions
the survey drops for every non-`self.<name>` attribute receiver. `derive_contract` never reads it.

### 10.2.1 P1 — receiver-attribute typing (research c-e's rule R3)

A stdlib-`ast` pass over PLR source (the same tree `scan_dropped_receiver_calls` already walks,
`derive/__init__.py:685-720`) building, per class:

- **P1a `annotated_attributes`**: every `self.<name>: <annotation>` `ast.AnnAssign` in the class body
  or its `__init__`, with the annotation unwrapped through `Dict[K,V] → V`, `List[T] → T`,
  `Optional[T] → T` to a bare class name. For `LiquidHandler` this yields `head → TipTracker` from
  `liquid_handler.py:162`.
- **P1b `attribute_writers`**: for every `self.<name> = …` `ast.Assign`, the qualname of the
  enclosing method. For `_default_use_channels` this yields exactly one method (`liquid_handler.py:1385`,
  `:1390`).

This is precisely rule R3 of research c-e's ranked recommendation
(`260901_plr-sema-research-c-e.md:152-160`), and that report already measured the exact case this
increment depends on: "`self.head[channel].get_tip` resolves under R3 to `TipTracker` with
`owns_method=True`" (`:175-176`). **DERIVED.**

### 10.2.2 P2 — the typestate anchor (which field, and which way round)

For a candidate tracker class `C` (any class appearing as a value of P1a), find every **property**
of `C` whose body is a single `return self.<F> <is|is not> None`. `TipTracker` has exactly one:

```python
@property
def has_tip(self) -> bool:
    return self._pending_tip is not None      # tip_tracker.py:52-55
```

This one pattern yields three facts at once and is the reason the design needs no hand-typed
polarity table:

- the **boolean view** attribute name: `has_tip`
- the **state field**: `_pending_tip`
- the **polarity**: `has_tip` is true ⟺ the field is not `None` ⟺ `HAS_TIP`

**Fail-closed rule (error-proofing).** If `C` has zero such properties, or more than one, P2 emits
nothing for `C`, the whole tip-typestate feature is disabled for every receiver whose channel
attribute types to `C`, and every verdict reverts to today's `UNKNOWN`. A silent partial derivation
is forbidden; the gap ledger records `tipstate_anchor: "absent"|"ambiguous"|"<field>"` per candidate
class so the condition is visible in the artifact rather than inferred from an absence of verdicts.

**The second state field, and why merging it is sound here.** `C` has a *second* field that tip-state
guards read: `TipTracker.get_tip` guards on `self._tip is None` (`tip_tracker.py:64-65`), the
committed field, while `add_tip`/`remove_tip` guard on and write `self._pending_tip`
(`:91-93`, `:104-106`). They can disagree mid-operation — `remove_tip(commit=False)` is the default
(`tip_tracker.py:100`).

**A-COMMIT holds for exactly two methods, and the claim is narrowed to them (round 1, O1).** The
general form of this claim — "every `LiquidHandler` tip operation commits or rolls back every touched
head tracker before returning" — is **false**, and this document said it in round 1. It is verified
only for `pick_up_tips` (`liquid_handler.py:570-573`) and `drop_tips` (`:716-723`), each of which
ends in an explicit commit-or-rollback fold over every channel it touched. It is **violated** by:

- `LiquidHandler.update_head_state` (`liquid_handler.py:262-282`), whose tracker calls are
  `self.head[channel].remove_tip()` (`:278`, `:281`) and `self.head[channel].add_tip(tip)` (`:282`),
  with `remove_tip`'s `commit` parameter defaulting to `False` (`tip_tracker.py:100`) and no
  subsequent `commit()` anywhere in the body — so on return `_pending_tip` has been cleared while
  `_tip` has not;
- `LiquidHandler.clear_head_state` (`:284-287`), a one-line delegation to `update_head_state`, which
  inherits the same violation.

**Neither violator can reach the merged cell, and the reason is mechanical rather than a
special case.** Both are already covered by rules this increment states elsewhere:

- `clear_head_state` reaches every tracker mutator only through the `self.update_head_state(...)`
  hop — a resolved delegate, so **depth 1** (`derive/__init__.py:400-403` appends resolved delegates
  at `depth + 1`; `InlinedGuard.depth` is defined as `0 = own body, >0 = inlined from a delegate`,
  `derive/__init__.py:426`). §10.2.6's depth-0-only effect rule gives it **no** effect and §10.4's
  **E4** widens the receiver to `TOP` — the same treatment `move_tips` gets.
- `update_head_state` does have depth-0 bridges, but **two of them, with disagreeing P4 effects**
  (`remove_tip` → `NO_TIP`, `add_tip` → `HAS_TIP`). §10.2.4's conflicting-bridge rule sends that
  shape to **E4** as well.

So the merged cell is only ever read across methods for which A-COMMIT is verified; every method
that could desynchronise the two fields widens the receiver to `TOP` before any guard of a later
operation is evaluated. §10.6.4 walks the round-1 counterexample that motivated this narrowing as an
explicit non-example.

P2 records `state_fields = ["_tip", "_pending_tip"]` — every field named in a `NullCheck` atom by any
guard of `C` that raises a `tip_state` exception — and the evaluator treats all of them as views of
the one abstract cell. This is assumption **A-COMMIT** (§10.6.3), narrowed as above, and it is the
one place in this increment where an abstraction merges two concrete locations.

### 10.2.3 P3 — the channel-arity idiom and its disablers

- **P3a `channel_default_param`**: for each method of a class, match the assignment idiom
  `<p> = <p> or self.<x> or list(range(len(<q>)))` (`ast.Assign` whose value is a two-level
  `BoolOp(Or)` ending in `Call(list, [Call(range, [Call(len, [Name q])])])`). Record `method → q`.
  Expected selection over `LiquidHandler`, from the four sites read this session:
  `pick_up_tips → tip_spots` (`:501`), `drop_tips → tip_spots` (`:650`), `aspirate → resources`
  (`:958`), `dispense → resources` (`:1152`). The fixer must publish the *measured* set, not this one.
- **P3b `channel_default_disablers`**: from P1b, the set of methods that write the `self.<x>` middle
  term of any P3a match — for `LiquidHandler`, `{use_channels}` (the two writes at `:1385`/`:1390`
  live in the `use_channels` context manager, a synchronous `@contextlib.contextmanager` at
  `liquid_handler.py:1363-1364` — round 1, O9 — whose contract key `LiquidHandler.use_channels` is
  present in the shipped table). The sync/async distinction does not change the derivation: P3b is
  driven by P1b's assignment scan, which is indifferent to whether the enclosing function is a
  coroutine. It is corrected because a reader checking the claim against source would find the text
  wrong and reasonably stop trusting the rest.

A method with no P3a match — `LiquidHandler.transfer` is the important one, since it computes its own
channel usage internally (see `training/floor_gen/exec_verify.py:188-193`, which documents that
`transfer` "internally does ONE `aspirate(resources=[source])` then loops `dispense(…, use_channels=[0])`
serially") — gets no channel-set derivation and is handled by rule 4 of §10.1.3: `channels = ⊤`.
That is correct and deliberately imprecise; making `transfer` precise requires modelling a method
body, which is not this increment.

### 10.2.4 P4 — effects

A guard tells you a *precondition*; it never tells you a *transition*. For each method `m` of an
anchored class `C`, classify `m`'s writes to any field in `state_fields`:

- `self.<F> = None` → `m` establishes `NO_TIP`
- `self.<F> = <expr>` where `<expr>` is not the literal `None` → `m` establishes `HAS_TIP`
- writes to no state field, or writes of both kinds → no effect (the method is transparent to this
  abstraction)

Measured over `TipTracker`: `add_tip` writes `self._pending_tip = tip` (`tip_tracker.py:93`) →
`HAS_TIP`; `remove_tip` writes `self._pending_tip = None` (`:106`) → `NO_TIP`; `commit` writes
`self._tip = self._pending_tip` (`:113`) → both-kinds-unknown → no effect, which is right, since
under A-COMMIT a commit is a no-op on the abstraction. **DERIVED.**

**Conflicting depth-0 bridges — widen, never E2, and never "no effect" (round 1, O2).** The
three-way classification above is about a class `C`'s *own* direct field writes. The bridge
mechanism (§10.2.5) can additionally attach two *different* `C` methods to one contract entry `K`,
and if their P4 effects disagree then `K` has no single effect at all. **Normative rule: if `K`'s
own body contains ≥2 depth-0 bridges to `C` methods whose P4 effects disagree, `K` triggers §10.4's
E4 — widen the receiver to `TOP` — never E2, and never "no effect".**
`LiquidHandler.update_head_state` (`liquid_handler.py:275-282`) is exactly this shape:
`self.head[channel].remove_tip()` (`NO_TIP`) in both branches and `self.head[channel].add_tip(tip)`
(`HAS_TIP`) in one of them, all at depth 0 in its own body.

Carrying §10.2.4's "no effect" outcome over to the bridge case would be **unsound**, not merely
imprecise, and the trace is short enough to check by hand:

1. `pick_up_tips(use_channels=[0])` — E2 sets `σ.exact[0] = HAS_TIP`.
2. `update_head_state({0: None})` — under a hypothetical "no effect" rule, `σ` is unchanged, so
   `σ.exact[0]` stays `HAS_TIP`.
3. `pick_up_tips(use_channels=[0])` again — its own depth-0 guard `self.head[channel].has_tip`
   (`liquid_handler.py:534`) parses as `BoolView`, evaluates `T` under `HAS_TIP`, and a
   `raise_guard` firing on `T` emits **`WILL_FAIL`**.

At runtime step 3 **succeeds**: `has_tip` reads `_pending_tip` (`tip_tracker.py:53-55`), and
`remove_tip()` sets `self._pending_tip = None` (`tip_tracker.py:106`) *even when* `commit` is left
at its `False` default (`tip_tracker.py:100`) — the clearing write is unconditional, only the
propagation to `_tip` is gated. So "no effect" manufactures a false `WILL_FAIL` on a clean
operation, which is precisely the row AC-10.11's zero-unsound-rows gate exists to catch. E4 emits
`UNKNOWN` there instead, which asserts nothing and therefore cannot be wrong (§10.5).

### 10.2.5 The channel bridge, and the shape of the payload addition

For each contract entry `K` on receiver class `R`, and each `dropped_calls` expression reached
anywhere in `K`'s closure, match the **channel-receiver shape**

```
self.<attr>[<name>].<method>            e.g.  self.head[channel].get_tip
```

where `R`'s P1a map sends `<attr>` to a class `C` with a P2 anchor, and `f"{C}.{method}"` is a key in
the contract table. When it matches, attach every guard of `C.<method>` to `K` as a **channel guard**
carrying the originating expression. This is deferred item (e), solved for exactly one receiver
shape, by exactly the annotation mechanism research c-e ranked first and measured
(`260901_plr-sema-research-c-e.md:149-176`) — not by type inference in general.

`derived_contracts.json` gains two additive blocks; `schema_version` stays `1` because `check/`
reads both through `.get()` with empty defaults, so a stale table degrades to today's all-`UNKNOWN`
behaviour rather than raising (pinned by AC-10.7):

```jsonc
{ "schema_version": 1,
  "stamp": { /* unchanged */ },
  "receiver_state": {                                    // NEW — P1..P4 output, one entry per anchored receiver class
    "LiquidHandler": {
      "channel_attr": "head",
      "tracker_class": "TipTracker",
      "bool_view":   {"attr": "has_tip", "field": "_pending_tip", "true_when": "not_none"},
      "state_fields": ["_tip", "_pending_tip"],
      "effects":     {"add_tip": "has_tip", "remove_tip": "no_tip"},
      "channel_default_param":     {"pick_up_tips": "tip_spots", "drop_tips": "tip_spots",
                                    "aspirate": "resources", "dispense": "resources"},
      "channel_default_disablers": ["use_channels"],
      "tip_state_exceptions":      ["HasTipError", "NoTipError"]
    }},
  "contracts": {
    "LiquidHandler.aspirate": {
      "gaps": [], "guards": [ /* unchanged, 9 entries */ ],
      "channel_guards": [                                // NEW
        {"condition": "self._tip is None", "kind": "raise_guard", "raises": "NoTipError",
         "free_vars": ["self"], "scope_trail": ["if self._tip is None"], "depth": 1,
         "site": {"file": "external/pylabrobot/pylabrobot/resources/tip_tracker.py",
                  "lineno": 65, "qualname": "TipTracker.get_tip"},
         "via": "self.head[channel].get_tip"}
      ]}}}
```

`channel_guards` is kept **separate from `guards`** so that the existing per-guard
`guard_predicate_unparsed` emission (`plr-sema/src/plr_sema/check/__init__.py:236-246`) and every existing count-based
acceptance criterion are untouched by construction.

`tip_state_exceptions` is **not hand-typed**, and round 1 (O3) corrected the selection rule that
makes it so. The rule is a **conjunction of two fields the taxonomy artifact already carries**:

> `tip_state_exceptions` = the set of class names whose entry in
> `training/verify/data/plr_exception_taxonomy.json` carries **both** `"category": "tip_state"`
> **and** `"module": "pylabrobot.resources.errors"`.

The round-1 draft stated only the first conjunct and asserted the result was `{HasTipError,
NoTipError}`. That was wrong: **the unfiltered `category == "tip_state"` set has five members**, not
two, and all five are in the shipped artifact —

| name | module | taxonomy `lineno` |
|---|---|---|
| `HasTipError` | `pylabrobot.resources.errors` | 16 |
| `NoTipError` | `pylabrobot.resources.errors` | 20 |
| `HamiltonNoTipError` | `pylabrobot.liquid_handling.backends.hamilton.STAR_backend` | 361 |
| `TipAlreadyFittedError` | `pylabrobot.liquid_handling.backends.hamilton.STAR_backend` | 351 |
| `TipTooLittleVolumeError` | `pylabrobot.liquid_handling.backends.hamilton.STAR_backend` | 340 |

The `module` conjunct narrows this to exactly `{HasTipError, NoTipError}`. It is still **DERIVED**:
`module` is an existing field on every taxonomy entry, no class name is typed into `plr_sema`, and
the filter is a module *path*, not a name list.

**The three Hamilton members are harmless today, and it is worth saying why rather than relying on
the filter alone.** None of the three appears anywhere in `plr-sema/data/derived_contracts.json` —
zero occurrences of the three names, hence zero `"raises"` matches. Their only recorded trigger
sites in the taxonomy are entries in `STAR_backend.py`'s `codes` error-code dispatch dict
(`external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/STAR_backend.py:798-806`:
`6: TipTooLittleVolumeError`, `7: TipAlreadyFittedError`, `8: HamiltonNoTipError`), not `raise`
statements, so the precondition survey never turns them into guards. Admitting them would therefore
change nothing measurable today — which is exactly why the filter has to be stated and AC-checked
rather than left to rest on the current emptiness of the derived table. It is also why the
correction is text-only: no derived value in the shipped artifact changes.

`plr_sema.derive` already takes a required `--taxonomy-json PATH` in the sibling differential
harness (main spec T10), so this is an existing input, not a new dependency, and no HM row is needed
for it. The one string the filter does put into `plr_sema`'s source — the module path itself — is
declared and argued explicitly under AC-10.9's third sub-assertion rather than left implicit.

### 10.2.6 What the rules actually select — measured against the shipped table

The whole point of grounding the rules in `plr-sema/data/derived_contracts.json` rather than in what
PLR "should" do is that the shipped table is **much emptier of tip state than it looks**. Measured
this session over the whole 4,770-entry table:

| fact | measurement |
|---|---|
| guards with `"raises": "HasTipError"` | **6** — five are the *same* guard (`LiquidHandler.pick_up_tips`'s own `self.head[channel].has_tip` at `liquid_handler.py:535`) inlined at depth 0 into `pick_up_tips` and at depth 1 into four callers; the sixth is `TipTracker.add_tip` at `tip_tracker.py:92` |
| guards with `"raises": "NoTipError"` | **2**, both at depth 0 inside `TipTracker`'s own contracts: `TipTracker.get_tip` (`tip_tracker.py:65`) and `TipTracker.remove_tip` (`tip_tracker.py:105`) |
| `LiquidHandler.aspirate`'s guard set | **9 guards, 0 gaps, and not one tip-state guard.** Its tip requirement lives entirely in `tips = [self.head[channel].get_tip() for channel in use_channels]` (`liquid_handler.py:974`), a dropped cross-class call |
| `LiquidHandler.drop_tips`'s guard set | **9 guards, 0 gaps, no tip-state guard.** Its volume guard `tip.tracker.get_used_volume() > 0 and (not allow_nonzero_volume)` is at depth 0; its tip requirement is `self.head[channel].get_tip()` at `liquid_handler.py:655` and its effect is `self.head[channel].remove_tip()` at `:684`, both dropped |
| `LiquidHandler.pick_up_tips`'s guard set | **10 guards, 0 gaps**, of which exactly one is tip state: the depth-0 `raise_guard` `self.head[channel].has_tip` / `HasTipError` / `liquid_handler.py:535` |

**Consequence, stated as bluntly as it deserves: without the §10.2.5 bridge, the tip-*requiring*
family is not derivable at all, and this increment would be able to say nothing about `aspirate`,
`dispense`, `drop_tips` or `transfer`.** A design that identified families only by scanning
`InlinedGuard.raises` in `contracts[K]["guards"]` — the obvious reading of the dispatch brief's
"tip-requiring if it raises `NoTipError`" — selects the empty set for every `LiquidHandler` method.
The bridge is not an optimisation; it is load-bearing.

With the bridge, the families are (this is the normative derivation, and the listed selections are
the expected result the fixer must reproduce and publish, not an input):

- **tip-loading(K)** ⟺ `K`'s guards ∪ channel_guards contain a `raise_guard` raising a `tip_state`
  exception whose atom demands `NO_TIP`, **or** `K` bridges to a `C` method whose P4 effect is
  `HAS_TIP`. Expected: `pick_up_tips` (both ways: its own `:535` guard *and*
  `self.head[channel].add_tip` at `:538`).
- **tip-requiring(K)** ⟺ `K`'s guards ∪ channel_guards contain a guard demanding `HAS_TIP`.
  Expected: `aspirate`, `dispense`, `drop_tips`, and — through `delegates_to`, since `self.aspirate(…)`
  *is* a `self.<name>` call and therefore a resolved delegate rather than a dropped one — `transfer`.
- **tip-dropping(K)** ⟺ `K` bridges **at depth 0** to a `C` method whose P4 effect is `NO_TIP`.
  Expected: `drop_tips` (`self.head[channel].remove_tip` at `:684`) — **and nothing else**.

  Round 1 (O4) struck `discard_tips` and `return_tips` from this list. Both reach
  `TipTracker.remove_tip` **only** through `self.drop_tips(...)` — `return_tips` at
  `liquid_handler.py:775-781`, `discard_tips` at `:833-839` — which is a resolved `delegates_to`
  hop, so depth 1. That is structurally identical to `move_tips`, whose own `self.pick_up_tips(...)`
  / `self.drop_tips(...)` pair sits at `:862-869`, and which the depth-0-only rule below explicitly
  widens. Listing them as tip-dropping while widening `move_tips` was a self-contradiction, and the
  conservative half is the one that survives: **`discard_tips` and `return_tips` widen via E4, like
  `move_tips`.** They emit `UNKNOWN`, not a wrong effect.

  A **single-hop-passthrough rule** — "a method whose entire body is one delegating call inherits
  that delegate's effect and channel set" — would recover `discard_tips`/`return_tips` without
  recovering `move_tips` (which makes two calls, not one). It is a real precision win and it is
  **named as a follow-up outside this increment**, not adopted here: it is new machinery in the
  derivation (a body-shape classifier plus argument forwarding for the channel set), and adopting it
  under time pressure is how an unsound passthrough gets shipped. Note that this repo's own
  extractor already draws the boundary inconsistently: the hand-typed
  `TIPS_DROPPING_METHODS = frozenset({"drop_tips", "drop_tips96", "return_tips", …})`
  (`praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:80-83`)
  includes `return_tips` but not `discard_tips`, despite the two being structurally identical —
  which is an argument for deriving the rule properly rather than approximating it.

Note the two families are not disjoint and must not be forced to be: `drop_tips` is both
tip-requiring and tip-dropping, which is exactly right.

**Flagged as looking wrong, for the fixer to check rather than assume:** `LiquidHandler.move_tips`,
`consolidate_tip_inventory` and `probe_tip_presence_via_pickup` all carry the `:535` `HasTipError`
guard at depth 1 (verified — the guard appears in their contract entries), so the rule classifies
them tip-loading. For `move_tips` and `consolidate_tip_inventory` that is a *sequence* of pickups
and drops whose net effect on any given channel is not `HAS_TIP`. The rule as written would apply a
`HAS_TIP` effect to them, which is unsound. **Normative fix, and it is the reason effects are P4's
job and not the guard set's:** the effect of `K` on a channel is taken **only** from P4 via the
bridge (`self.<channel_attr>[…].<m>` reached at **depth 0** in `K`'s own body), never from a
guard's polarity, and **never at depth > 0**. A method that reaches a tracker mutator only through a
delegate gets *no* effect and instead widens the receiver to `TOP` (§10.4, rule E4.2). `move_tips`,
`discard_tips`, `return_tips` and `clear_head_state` therefore widen rather than mis-transition.

**The companion rule, added in round 1 (O2):** depth-0 is necessary but not sufficient. A method
whose own body reaches ≥2 depth-0 bridges with *disagreeing* P4 effects also widens (§10.2.4;
§10.4, rule E4.3). `LiquidHandler.update_head_state` is the shipped instance, and unlike the
depth > 0 cases it is not caught by the depth rule at all — it needed its own. Between the two
rules, every `LiquidHandler` method that touches a head tracker other than `pick_up_tips` and
`drop_tips` widens, which is the same set for which A-COMMIT is unverified (§10.2.2). That
coincidence is not an accident: both rules are asking "does this method leave the head trackers in a
state I can name?", and the answer is yes for exactly the two methods that commit-or-roll-back.

---

## 10.3 The evaluator (deferred item (c), narrowed)

### 10.3.1 Which atoms are interpreted

A guard is **tip-state-interpretable** for operation `op` iff **all four** hold:

1. `guard.kind` is `"raise_guard"` — and **only** `"raise_guard"` (round 1, Q2). Polarity is still
   read from `kind` rather than folded into the condition text, exactly as
   `derive/__init__.py:406-432` specifies; the point of the restriction is that no tip-state guard in
   the shipped table is an `assert`, so an `assert` branch here would be specified-but-unexercised
   code, which is the kind that rots. An `assert`-kind guard falls through to
   `guard_predicate_unparsed`, unchanged. **This is re-addable in one line** — the polarity field
   already carries the information — and the condition for re-adding it is a *test*: a real or
   synthetic contract fixture with an `assert`-kind tip-state guard, added at the same time as the
   branch, never before it;
2. `guard.condition` is not `None` and parses under the atom grammar below to a single atom (no
   `and`/`or`/`not` — a compound condition is **not** interpreted in this increment; it falls through
   to `guard_predicate_unparsed`, unchanged);
3. the atom's path is **channel-scoped**: either it begins `self.<channel_attr>[<name>]` (an own
   guard, e.g. `pick_up_tips`'s `self.head[channel].has_tip`) or the guard came from
   `channel_guards`, whose `via` expression supplies the channel scope;
4. `op`'s channel set is exact (§10.1.3 rules 1 or 3) **and** every channel in it has a state that is
   not `TOP`.

The grammar is three productions, a strict subset of the five research c-e proposes
(`260901_plr-sema-research-c-e.md:454-464`, where they appear as `NullCheck` and attribute
truthiness):

```
Atom ::= BoolView(Path)                    #  <path>.<bool_view.attr>       e.g. self.head[c].has_tip
       | NullCheck(Path, is_none=True)     #  <path>.<state_field> is None
       | NullCheck(Path, is_none=False)    #  <path>.<state_field> is not None
```

`<bool_view.attr>` and `<state_field>` are the P2-derived names, never literals in our source.
**Everything else stays Kleene ½**, including every numeric `Cmp` — main spec §Open decisions 2
resolved that numeric atoms are uninterpreted "through v1 and the first post-corpus increment", and
this *is* that increment, so `drop_tips`'s
`tip.tracker.get_used_volume() > 0 and (not allow_nonzero_volume)` (depth 0, verified in the shipped
table) remains `guard_predicate_unparsed`. That is unchanged, deliberate, and re-affirmed here.

**`free_vars` must not be used to identify the receiver.** The shipped table proves why: the
`TipTracker.get_tip` guard carries `free_vars: ["self"]` while `LiquidHandler.pick_up_tips`'s `:535`
guard carries `free_vars: []` despite its condition mentioning `self.head[channel]`. Research c-e
says the same from the other end (`260901_plr-sema-research-c-e.md:477-483`: "Do not trust
`mentions_params` as the free-variable set"). The path is recomputed from the parsed condition, and
`free_vars` is at most a cross-check.

### 10.3.2 Atom truth under a state

Let `s` = **§10.1.1's join `⊔` folded over `op`'s channel set** — i.e. `NO_TIP` if every channel is
`NO_TIP`, `HAS_TIP` if every channel is `HAS_TIP`, `TOP` otherwise, which is exactly what that
table's `NO_TIP ⊔ HAS_TIP = TOP` row gives. (Round 1, O6: this fold was called a "meet" in the draft.
It is not one — this lattice has no ⊥, so `NO_TIP` and `HAS_TIP` have no greatest lower bound and
the meet is undefined on the case that matters. The operation is and always was `⊔`; only the name
was wrong.)

That the join is the right fold is the *soundness* reading, not a convenience: a guard inside
`for channel in use_channels` fires if it fires for any one channel, so a mixed channel set can
neither be entailed nor refuted, and `⊔`'s `TOP` is precisely "cannot say". Using a meet — if one
existed — would let a mixed set collapse to a definite state and manufacture a verdict.

| atom | `s = NO_TIP` | `s = HAS_TIP` | `s = TOP` |
|---|---|---|---|
| `BoolView(p)` | **F** | **T** | ½ |
| `NullCheck(p, is_none=True)` | **T** | **F** | ½ |
| `NullCheck(p, is_none=False)` | **F** | **T** | ½ |

### 10.3.3 From atom truth to a `Finding`

Guard polarity, per `derive/__init__.py:412-417`: a `raise_guard` fires when its condition is TRUE.
Since §10.3.1's criterion 1 admits only `raise_guard`s, `fires` is just the atom's truth:
`fires ∈ {T, F, ½}`. (The draft also carried an `assert`-fires-on-FALSE line here; round 1's Q2
dropped it along with the `assert` production, because nothing in the shipped table exercises it.
`InlinedGuard.kind` still records the polarity — this increment simply does not consume the
`"assert"` case.)

| `fires` | `Finding` emitted for this guard |
|---|---|
| **T** | `Verdict.WILL_FAIL`, `category="precondition_state"`, `reason=""`, `plr_site=guard.site`, `evidence=(site of the effect that established the state,)`, `detail=guard.condition` |
| **F** | `Verdict.SAFE`, `category=""`, `reason=""`, `plr_site=guard.site`, `detail=guard.condition` |
| **½** | `Verdict.UNKNOWN`, `reason="channel_state_unknown"` (**new**, §10.10), `plr_site=guard.site`, `detail=guard.condition` |

`precondition_state` is an existing member of the FROZEN `FAILURE_CATEGORIES`
(`training/verify/failure_taxonomy.py:82-89`, member at `:86`); nothing about that set changes, and
HM-5 stays FROZEN at 6.

**Exactly one `Finding` per guard, and grouping by `operation_id` remains forbidden.** The emission
above replaces, one-for-one, the `guard_predicate_unparsed` finding that
`check/__init__.py:260-281` emits today for the same guard. Two findings sharing an `operation_id`
are still two *independent* obligations — guard A and guard B — which correctly conjoin under `join`'s
obligation order. Research a-d's R3 (`260901_plr-sema-research-a-d.md:520-526`: group by
`operation_id` and Kleene-join within the group) **must not be implemented**, and this increment
makes the reason sharper rather than weaker: `aspirate` under a `NO_TIP` state now emits one
`WILL_FAIL` (the bridged `NoTipError` guard) alongside nine `UNKNOWN`s — one per own guard, and
`aspirate` has nine of them (§10.2.6's measurement table).
Kleene-joining within the operation would collapse `WILL_FAIL ⊔ SAFE` to `UNKNOWN` and **erase the
one true thing the analyzer now knows** — unsound in the `SAFE` direction, and no longer merely
theoretically so. `verdict.py:248-261` already carries this warning; it stays.

**Operation-level `SAFE` is unreachable in practice, and that is not a defect.** Every
`LiquidHandler` method carries 9–17 guards, nearly all of which stay ½ (`_check_args`'s
`len(missing) > 0`, `strictness == Strictness.STRICT`, `error is not None`, …). `join`'s third row
means one ½ makes the operation `UNKNOWN`. So this increment produces **operation-level `WILL_FAIL`
and per-`Finding` `SAFE`**, and the acceptance criteria are written against the finding, not the
operation verdict, wherever `SAFE` is concerned (AC-10.2). Any AC that asserted an operation-level
`SAFE` would be unsatisfiable, and writing one would be the "acceptance criteria satisfiable without
the property being true" failure in its mirror form — a criterion unsatisfiable even when the
property *is* true.

---

## 10.4 Transfer functions

For operation `op` on receiver `v`, with `channels(op)` from §10.1.3 and the pre-state `σ`:

- **E1 (evaluate first, then transition).** Guards are evaluated against `σ` — the state *before*
  `op` — for every guard of `op`. Only then is the post-state computed. A method that is both
  tip-requiring and tip-dropping (`drop_tips`) is therefore checked against the incoming state and
  updates from it, in that order.
- **E2 (exact effect).** If `op`'s method has **exactly one** distinct depth-0 P4 effect `e ∈
  {HAS_TIP, NO_TIP}` reachable by bridge — i.e. every depth-0 bridge from `op`'s method to a
  tracker-mutating `C` method agrees on `e` — and `channels(op)` is exact, then for each
  `c ∈ channels(op)`: `σ'.exact[c] = e`. Channels outside the set are unchanged. If the depth-0
  bridges disagree, E2 does **not** apply; E4 does.
- **E3 (no effect).** If the method has no depth-0 tracker-mutating bridge, `σ' = σ`. This covers
  `aspirate`, `dispense`, `transfer` and every non-tip method: they read tip state and do not change
  it.
- **E4 (widen).** `σ' = (default=TOP, exact={})` for `v` — the whole receiver is widened — under any
  of four conditions:
  1. the method has a tracker-mutating bridge but `channels(op)` is `⊤`;
  2. the bridge is only reachable at depth > 0 (§10.2.6's `move_tips` case, and
     `clear_head_state`'s delegation through `update_head_state`, §10.2.2);
  3. **(round 1, O2)** the method's own body contains ≥2 depth-0 bridges to `C` methods whose P4
     effects **disagree** — `LiquidHandler.update_head_state` (`liquid_handler.py:275-282`) is the
     shipped instance. This case must never fall through to E2, and must never be treated as "no
     effect" (E3): §10.2.4 gives the trace showing "no effect" manufactures a false `WILL_FAIL`;
  4. a channel-default disabler method (§10.2.3, P3b) appears anywhere in the graph on `v`.
- **E5 (unknown receiver).** `receiver_type is None`, or a type with no P2 anchor: no state, no
  evaluation, findings unchanged from today.

E1's ordering assumes the operation *completes* — see A-COMPLETES in §10.7.

---

## 10.5 The graph walk, v1

`check/__init__.py:329-330` iterates `graph.operations`. This increment keeps that shape and adds a
single left-to-right state fold. Three rules, and no fixpoint:

1. **Order.** The mirror gains `execution_order` (§10.10). Operations are visited in
   `execution_order` when it is non-empty and is a permutation of the operation ids; otherwise in
   `operations` order, which the upstream model documents as execution order
   (`praxis/backend/utils/plr_static_analysis/models.py:623-625`). If `execution_order` is non-empty
   and is *not* such a permutation, the walk widens every receiver to `TOP` immediately and emits
   nothing but today's findings — a disagreement between two views of the same fact is a reason to
   know less, never to pick one.
2. **Loops widen.** Any operation with `foreach_source is not None` or non-empty `foreach_body`
   (`check/graph.py:120-121`) widens its receiver to `TOP` **before** its own guards are evaluated,
   and the receiver stays `TOP` for the remainder of the walk. There is no trip-count reasoning, no
   loop-body re-entry, and no fixpoint iteration. The existing `loop_bounds_unknown` finding
   (`check/__init__.py:309-310`) is unchanged and still emitted.

   **On the IR, rule 2's widening is delivered by region entry, not by a per-operation field
   (amendment, spec_version 10 / `260902_plr-sema-ir-bytecode-increment.md` §11.4.1).** Once this
   walk is a pass over SEMA-IR, the trigger is no longer `foreach_source is not None or foreach_body`
   on an individual operation — it is **entry to a `LOOP` region**, at which every receiver mentioned
   anywhere in the region is widened to `TOP` before the region's first `CALL` is evaluated. This
   matters because the extractor never populates `foreach_source`/`foreach_body`, so as literally
   written rule 2 fires on no real payload: a looping protocol arrives with only the graph-level
   `has_loops` flag set and one operation per syntactic call, and the walk evaluates the loop body
   straight-line, once, against the pre-loop state — which is the direction that produces a false
   `SAFE`. The IR increment closes that with a **synthetic `LOOP ⊤` region**: when `has_loops` is set
   and the lowered stream contains zero real `LOOP` regions, the whole stream is wrapped in one, so
   the region-entry rule widens **every** receiver in the program and a looping protocol is
   all-`UNKNOWN` rather than straight-line evaluated. Coarser than a real region, and correct in the
   only direction that matters; the precision returns without a spec change the moment `extract/`
   emits real regions.
3. **Dynamic arguments widen.** Any operation with non-empty `depends_on_params`
   (`check/graph.py:119`) widens its receiver to `TOP` before evaluation, same permanence. In the
   committed fixture that is `op_1` and `op_4` (`depends_on_params: ["tips"]`).

**Why this is sound and not merely convenient (Rival & Yi §1.3.5's over-approximation discipline).**
Widening a channel to `TOP` can only move an atom from `T`/`F` to `½`, and `½` yields
`Verdict.UNKNOWN`, which asserts nothing. So every widening can only *destroy* a verdict, never
create a wrong one: it can turn a would-be `SAFE` or `WILL_FAIL` into `UNKNOWN`, and it can never
turn an `UNKNOWN` into either. The absence of a fixpoint is therefore a precision decision, not a
soundness one. It also means the increment cannot regress the oracle's zero-unsound-rows gate by
being *too coarse* — only by being too fine.

Branches are not handled at all: `condition_expr`/`true_branch`/`false_branch` are still not
mirrored (main spec §6.2's B5 note), so the walk never sees a branch. If a future extractor emits
branch nodes, they will arrive as operations with unrecognised shape; AC-10.6 pins that an operation
carrying a non-empty `condition_expr` in the raw payload widens rather than being silently
straight-lined. This is the one place where a *future* upstream change could otherwise turn this
increment unsound, so it is fenced now rather than later.

---

## 10.6 The soundness argument

### 10.6.1 The chain behind a `WILL_FAIL`

For the double-`pick_up_tips` case, the claim "operation `op_1` must fail" rests on exactly these
links, each one checkable:

1. **Graph.** `op_0` and `op_1` are on the same `receiver_variable`, in this order, neither in a
   loop, neither with dynamic arguments (`check/graph.py:115-121`).
2. **Channel set.** Both carry `use_channels` (or a `tip_spots` list) that `ast.literal_eval`s to
   `[0]`, so `channels = {0}` exactly, by rules 1/3 of §10.1.3, which mirror
   `liquid_handler.py:501`.
3. **Effect.** `op_0`'s method bridges at depth 0 to `TipTracker.add_tip` (from
   `LiquidHandler.pick_up_tips`'s `dropped_calls` entry `self.head[channel].add_tip`, verified in
   `training/verify/data/plr_preconditions.json`), whose P4 effect is `HAS_TIP`
   (`tip_tracker.py:93`). So `σ.exact[0] = HAS_TIP` after `op_0`.
4. **Guard.** `op_1`'s contract carries the depth-0 guard
   `{"condition": "self.head[channel].has_tip", "kind": "raise_guard", "raises": "HasTipError",
   "site": {"file": ".../liquid_handler.py", "lineno": 535}}` — verified verbatim in
   `plr-sema/data/derived_contracts.json`'s `LiquidHandler.pick_up_tips` entry.
5. **Atom.** `self.head[channel].has_tip` parses as `BoolView` with a channel-scoped path, using the
   P2-derived `bool_view.attr = "has_tip"` (`tip_tracker.py:53-55`).
6. **Evaluation.** `BoolView` under `HAS_TIP` is `T` (§10.3.2); `kind = "raise_guard"` fires on `T`;
   so `fires = T` ⟹ `WILL_FAIL` with `category="precondition_state"`.
7. **Runtime correspondence.** PLR executes exactly this: `if self.head[channel].has_tip: raise
   HasTipError("Channel has tip")` (`liquid_handler.py:534-535`), unconditionally — not inside any
   `does_tip_tracking()` test.

### 10.6.2 The chain behind a `SAFE` finding

Same links 1–3, with `op_1` an `aspirate` on `channels = {0}`; link 4 becomes the *bridged* guard
`{"condition": "self._tip is None", "kind": "raise_guard", "raises": "NoTipError", "site":
{".../tip_tracker.py", 65, "TipTracker.get_tip"}}` reached via `self.head[channel].get_tip`
(`liquid_handler.py:974`); link 5 parses it as `NullCheck(is_none=True)` on the P2 state field; link
6 gives `F` under `HAS_TIP` ⟹ that guard is `SAFE`. The operation's aggregate verdict stays
`UNKNOWN` because its other **nine** guards are ½ — `aspirate` has nine own guards, none of them
tip-state (§10.2.6's measurement table), and the bridged guard is a tenth finding, not one of the
nine. (Round 1, O7: the draft said "eight" here, which double-counted the bridged guard as one of
`aspirate`'s own.) `UNKNOWN` is the correct, honest answer.

### 10.6.3 The assumptions, named

Every one of these is an assumption the analyzer cannot discharge from the graph. They are listed so
a reviewer can attack them; none of them is buried in code.

| id | assumption | why it is needed | what breaks if it is false |
|---|---|---|---|
| **A-SINGLE** | one `receiver_variable` denotes one `LiquidHandler` instance for the whole graph, and no other name aliases it | state is keyed on the variable name (§10.1.4) | a second alias mutating the head trackers desynchronises `σ`; both a false `SAFE` and a false `WILL_FAIL` become possible. Mitigation: no `plr_static_analysis` graph today emits two names for one instance, and `is_grounded` (`plr-sema/src/plr_sema/check/graph.py:204-212`) exists to detect ungrounded references when a reason for it lands |
| **A-COMPLETES** | each operation preceding the one being checked completed without raising | E1/E2's post-state is the state *after a successful* call | it is the same assumption the oracle's own comparison already makes: `oracle_common.compare` marks every operation after the failing index `not_reached` and imposes no constraint there (`plr-sema/eval/oracle_common.py:632-651`; the round-1 draft cited `:148-163`, which is `run_static`'s per-operation grouping, not the comparison). A `WILL_FAIL` at index `i` is a claim about the trace *reaching* `i` |
| **A-COMMIT** (narrowed, round 1 O1) | at operation boundaries **of `pick_up_tips` and `drop_tips` only**, `_tip` and `_pending_tip` agree | P2 merges two concrete fields into one abstract cell (§10.2.2) | verified for exactly those two: each ends in a commit-or-rollback fold over every touched channel (`liquid_handler.py:570-573`, `:716-723`). It is **known false** for `update_head_state` (`liquid_handler.py:262-282`, `remove_tip(commit=False)` with no later `commit()`) and `clear_head_state` (`:284-287`) — both of which widen to `TOP` before any later guard is evaluated, by §10.4's E4.2 and E4.3 respectively, so neither can read the merged cell. What breaks it is a *new* PLR method that mutates a head tracker at depth 0 with a single non-conflicting effect and no commit; Fork D's pin test is the tripwire, and §10.6.4 is the worked non-example |
| **A-ENABLED** | the head trackers are not `disable()`d | `TipTracker.add_tip`/`remove_tip` raise `RuntimeError` when disabled (`tip_tracker.py:89-90`, `:102-103`) | **largely self-discharging**: under A-COMPLETES, if `op_0`'s `add_tip` had raised `RuntimeError`, `op_0` would not have completed, so a completed `pick_up_tips` implies its head tracker was enabled. The residual is a `disable()` call *between* two operations, which no graph emits |

**The brief's premise about `does_tip_tracking()` is, for this family, false — and that is good news
worth stating.** Main spec §Open decisions 2 correctly notes that PLR's *volume* guards are gated by
a process-global tracking flag, and the oracle plan runs with `set_tip_tracking(True)`. But the head
trackers are **not** so gated. At `liquid_handler.py:536-538`, only the *tip-spot* tracker call is
inside `if does_tip_tracking() and not op.resource.tracker.is_disabled:`; the head-tracker call
`self.head[channel].add_tip(op.tip, origin=op.resource, commit=False)` at `:538` sits outside it. The
same asymmetry holds in `drop_tips` (`:678-684`: the guarded block covers `op.resource.tracker.add_tip`,
while `self.head[channel].remove_tip()` at `:684` is unguarded), and the `HasTipError` raise at
`:534-535` is unguarded too. So a `WILL_FAIL` from this increment is a claim about PLR **regardless
of the tip-tracking flag**, and no `SoundnessScope` environment record is required for it — unlike
the volume family, which does need one. This is the strongest single reason to pick tip state as the
first increment rather than volume.

### 10.6.4 A worked non-example: the round-1 counterexample, and why it does not reproduce

This is the sharpest test the soundness argument has had, and it is recorded in full rather than
summarised, because the *reason* it fails to reproduce is a load-bearing property of the design and
not a lucky accident. Round 1's challenger proposed (O1):

```
op_0: lh.pick_up_tips(tip_spots=[ts0], use_channels=[0])
op_1: lh.clear_head_state()
op_2: lh.aspirate(resources=[r0], use_channels=[0])
```

**Real PLR behaviour.** `clear_head_state` delegates to `update_head_state`
(`liquid_handler.py:284-287`), which calls `self.head[channel].remove_tip()`
(`liquid_handler.py:278`) with `commit` at its `False` default (`tip_tracker.py:100`). So
`_pending_tip` becomes `None` (`tip_tracker.py:106`) while `_tip` is left holding the tip.
op_2's `self.head[channel].get_tip()` (`liquid_handler.py:974`) reads `_tip`
(`tip_tracker.py:64-65`), which is **not** `None` — so `aspirate` runs clean, raising nothing. The
challenger's claim was that the analyzer would nonetheless set `σ.exact[0] = NO_TIP` at `op_1` via
E2 and then emit `WILL_FAIL` at `op_2` — a false `WILL_FAIL`, and exactly the kind of row
AC-10.11's zero-unsound-rows gate exists to fail on.

**Why it does not reproduce.** `clear_head_state`'s body contains no tracker call at all. Its only
statement is `self.update_head_state({c: None for c in self.head.keys()})` — a `self.<name>` call,
which the derivation resolves as a **delegate**, not as a `dropped_calls` entry (§10.2.5 bridges
only the `self.<attr>[<name>].<method>` shape). `derive/__init__.py:400-403` pushes resolved
delegates onto the frontier at `depth + 1`, and `InlinedGuard.depth` is defined as
`0 = own body, >0 = inlined from a delegate` (`derive/__init__.py:426`). The `remove_tip`/`add_tip`
calls therefore sit at **depth 1 relative to `clear_head_state`**, and §10.2.6's depth-0-only effect
rule gives `clear_head_state` **no effect** and §10.4's **E4.2** widens the receiver to `TOP`.
`op_2` then evaluates its bridged `NoTipError` guard under `s = TOP` ⟹ `½` ⟹ `UNKNOWN`. No verdict
is emitted, and none is wrong.

**What the counterexample did establish, and it was not nothing.** Two things survive it:

1. The prose justifying A-COMMIT was a claim about "every `LiquidHandler` tip operation", and that
   claim is false. §10.2.2 now names the two methods it holds for and the two it does not. The
   *behaviour* was already right; the *argument* was over-broad, and an over-broad argument is how
   the next person extends the rule into the region where it fails.
2. A **direct** `lh.update_head_state({0: None})` call — one hop shorter than the challenger's
   graph — really does have depth-0 bridges, and there the counterexample bites. That case is O2,
   and it is closed by a rule that did not exist in the draft (§10.2.4's conflicting-bridge rule,
   §10.4's E4.3), not by one that already did. Had the challenger written `update_head_state`
   instead of `clear_head_state`, the objection would have landed as a live unsoundness rather than
   as a prose defect.

The general lesson, stated so a future increment inherits it: **depth is the mechanism that keeps
this analyzer sound across delegation, and it is doing real work.** Every rule that says "depth 0
only" is buying soundness at a measurable cost in precision (`discard_tips`, `return_tips`,
`move_tips`, `clear_head_state` all widen and could in principle be handled). Any future proposal to
relax a depth-0 restriction has to re-examine this non-example first, because relaxing it by one hop
is exactly what turns it into a real counterexample.

---

## 10.7 Acceptance criteria

Written so that none can be satisfied while the property is false. Each names the fixture, the
operation, and the exact site, so a stubbed evaluator that returns a constant fails.

- **AC-10.1 (`WILL_FAIL` on a repeated pickup).** Fixture `double_pickup_graph.json`: two
  `pick_up_tips` operations on receiver `lh` (`receiver_type: "LiquidHandler"`), each with
  `arguments["use_channels"] == "[0]"`, empty `depends_on_params`, no loop.
  `check_graph(...)` yields a report in which `op_1` has **exactly one** `Finding` with
  `verdict is Verdict.WILL_FAIL`, and that finding has `category == "precondition_state"` and
  `plr_site == PlrSite("external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py", 535,
  "LiquidHandler.pick_up_tips")`. The per-operation `join` of `op_1`'s findings is
  `Verdict.WILL_FAIL`; the per-operation join of `op_0`'s is `Verdict.UNKNOWN`.
- **AC-10.2 (`SAFE` finding after a pickup, and no operation-level `SAFE`).** Fixture
  `pickup_then_aspirate_graph.json`: `pick_up_tips(use_channels=[0])` then
  `aspirate(use_channels=[0])`. `op_1` has **exactly one** `Finding` with
  `verdict is Verdict.SAFE`, whose `plr_site` is
  `PlrSite("external/pylabrobot/pylabrobot/resources/tip_tracker.py", 65, "TipTracker.get_tip")`.
  The per-operation join of `op_1` is `Verdict.UNKNOWN` (its other guards are ½). No `Finding` in
  the whole report has `verdict is Verdict.WILL_FAIL`.
- **AC-10.3 (`WILL_FAIL` sited in the tip tracker).** Fixture `aspirate_after_drop_graph.json`:
  `pick_up_tips(use_channels=[0])`, `drop_tips(use_channels=[0])`, `aspirate(use_channels=[0])`.
  `op_2` has exactly one `WILL_FAIL` finding, `category == "precondition_state"`, `plr_site ==
  PlrSite(".../resources/tip_tracker.py", 65, "TipTracker.get_tip")`, and `report.verdict is
  Verdict.WILL_FAIL`. (This is the criterion that cannot pass without the §10.2.5 bridge, the P4
  effect derivation, *and* the channel-set derivation all being right — it is the increment's single
  best end-to-end gate.)
- **AC-10.4 (the shipped fixture is unchanged in verdict, changed in one reason).** Against
  `plr-sema/tests/fixtures/simple_transfer_graph.json`, `report.verdict is Verdict.UNKNOWN` and
  every `Finding.verdict is Verdict.UNKNOWN`, exactly as today; and the finding count per operation
  is unchanged from the pre-increment run. Additionally, no finding in that report carries
  `reason == "channel_state_unknown"` (its operations widen on `depends_on_params` before any guard
  is evaluated, so the new reason is not reached).
- **AC-10.5 (widening erases, never inverts).** Take `double_pickup_graph.json` and produce three
  variants: (a) `op_1.foreach_source = "wells"`, (b) `op_1.depends_on_params = ["n"]`, (c)
  `op_0.arguments["use_channels"] = "channels"` (a bare name, not a literal). In all three, `op_1`
  has **zero** findings with `verdict is Verdict.WILL_FAIL` and zero with `verdict is Verdict.SAFE`,
  and `report.verdict is Verdict.UNKNOWN`.
- **AC-10.6 (unknown shapes widen).** A graph payload whose operation carries a non-null
  `condition_expr`, or a `use_channels` disabler operation
  (`method_name` in the derived `channel_default_disablers`) anywhere on the receiver, yields zero
  `SAFE`/`WILL_FAIL` findings for every operation on that receiver.
- **AC-10.7 (stale contract table degrades, does not crash).** `check_graph` against a contract
  table with no `receiver_state` block and no `channel_guards` keys (i.e. the pre-increment
  artifact, committed as a test fixture) returns the pre-increment report, byte-identical after
  JSON round-trip. `check_graph` never raises on it.
- **AC-10.8 (empty graph unchanged).** `check_graph('{"protocol_fqn":"p","operations":[],"resources":{}}',
  contracts)` returns `Verdict.UNKNOWN` with zero findings — main spec AC-3.5 / §3.2's empty-multiset
  row, re-asserted because this increment adds the first code path that could have special-cased it.
- **AC-10.9 (derivation reproducibility, published not asserted).** `python -m plr_sema.derive
  --survey-json … --taxonomy-json … --out …` re-emits `derived_contracts.json` with a
  `receiver_state` block whose `LiquidHandler` entry has `channel_attr == "head"`,
  `tracker_class == "TipTracker"`, `bool_view.field == "_pending_tip"`,
  `effects == {"add_tip": "has_tip", "remove_tip": "no_tip"}`, and
  `tip_state_exceptions == ["HasTipError", "NoTipError"]` — each read out of PLR source and the
  taxonomy artifact, none written into `plr_sema`'s source. Three sub-assertions, all mechanical:

  1. **Block equality.** The emitted `receiver_state["LiquidHandler"]` equals the value above.
  2. **The module filter is itself checked, not just its output (round 1, O3).** The test asserts,
     against `training/verify/data/plr_exception_taxonomy.json` as loaded: that the entries with
     `category == "tip_state"` number **five** and are exactly
     `{HamiltonNoTipError, HasTipError, NoTipError, TipAlreadyFittedError, TipTooLittleVolumeError}`;
     that filtering those by `module == "pylabrobot.resources.errors"` yields exactly
     `{HasTipError, NoTipError}`; and that `tip_state_exceptions` equals the *filtered* set. This is
     what makes the two-conjunct rule of §10.2.5 a checked fact rather than a claim — a future
     taxonomy entry that lands a sixth `tip_state` member turns this red and forces a decision,
     instead of silently widening or silently not widening the set.
  3. **No hand-typed names.** An **AST literal scan** of `plr-sema/src/` — not `grep` — finds none of
     `"TipTracker"`, `"has_tip"`, `"_pending_tip"`, `"NoTipError"`, `"HasTipError"` or `"head"` as an
     `ast.Constant` string value. (Round 1, O8: `grep` cannot exclude docstrings and comments, and
     that exclusion is the whole point of the criterion. The mechanism already exists in this repo:
     `test_reason_vocabulary_closed_forward` (`plr-sema/tests/test_verdict.py:401-483`) walks the parsed
     tree via `_find_finding_reason_sites` / `_is_finding_call` / `_resolve_reason_kwarg`
     (`plr-sema/tests/test_verdict.py:318-355`) rather than scanning text; this criterion reuses that
     shape. A docstring is an `ast.Expr` whose value is a `Constant`, so the scan must skip docstring
     position explicitly — a short exclusion that must itself be tested with a fixture that *does*
     put one of the names in a docstring, or the criterion passes for the wrong reason.)

  **What the scan deliberately does not forbid, said out loud.** The module path
  `"pylabrobot.resources.errors"` **is** one string literal in `plr_sema`'s source, and pretending
  otherwise would be the kind of quiet exception that makes an anti-hand-typing gate worthless. The
  spec's position is that it does not need its own HM row: it names PLR's *package layout*, not any
  tip-state fact — it says nothing about which exceptions exist, what they mean, or which methods
  raise them, all of which stay derived — and it fails **closed**, since a module rename makes the
  filter select the empty set, which disables the feature (§10.2.2's fail-closed rule) rather than
  producing a wrong verdict. Sub-assertion 2 is what keeps that position honest: it fails loudly the
  moment the filter stops selecting exactly two. A reviewer who disagrees should say so — the
  remedy is one more `CAPPED` HM row, not a change to the design.
- **AC-10.10 (family selection is published).** The gap ledger gains a `tip_state` block listing, per
  anchored receiver class, the derived tip-loading / tip-requiring / tip-dropping method sets and the
  `tipstate_anchor` status. The test asserts the sets are non-empty and that
  `"aspirate" ∈ tip_requiring`, `"pick_up_tips" ∈ tip_loading`, `"drop_tips" ∈ tip_requiring ∩
  tip_dropping` — the three §10.2.6 expectations, so a rule that silently selects nothing fails.
- **AC-10.11 (oracle gate — replay; vacuous under tier 1 as configured, and says so).** `#4879`'s
  tier-1 corpus replay over the 812 + 88 rows reports **0 unsound rows** under
  `oracle_common.compare`'s own `unsound` predicate (`plr-sema/eval/oracle_common.py:632-651`): no
  operation is `SAFE` where the simulator raised, and none is `WILL_FAIL` where the simulator ran
  clean. This is a hard gate. The `UNKNOWN` rate is **reported, not gated** — main spec Deferred (f)
  still defers the number.

  **This criterion is vacuous whenever tier 1 is run with tool-named arguments, which is its default
  configuration — and the disclosure is part of the criterion (round 1, Q3, resolved as option
  (c)).** `oracle_common.adapt_graph`'s fallback branch builds `arguments` as
  `{k: json.dumps(v) for k, v in (call.get("params") or {}).items()}`
  (`plr-sema/eval/oracle_common.py:118-125`) — i.e. the corpus's *tool* parameter names. The tool
  schema names `pick_up_tips`'s argument `at`, not `tip_spots`
  (`training/verify/dispatcher.py:159-161`), and carries no `use_channels` at all. Under §10.1.3
  every such row falls to rule 4 (`channels = ⊤`), every verdict stays `UNKNOWN`, and "0 unsound
  rows" is satisfied by an analyzer that never fires. **Read that way, AC-10.11 gates totality and
  non-regression only** — that the new code path runs over 900 real rows without raising and without
  flipping anything. The **real** directional gate is **AC-10.12**, whose criterion (iii) cannot be
  satisfied by an evaluator that never fires; that is precisely why it is a separate criterion.

  **The vacuity is configuration, not a wall, and the escape is already built.** `adapt_graph` takes
  an optional `plr_kwargs: dict[int, dict[str, Any]]` (`plr-sema/eval/oracle_common.py:94`) and
  prefers it over the tool params when present (`:118-125`), and `run_runtime` already *harvests*
  PLR-named kwargs from the verifier's own `plan_call` return value
  (`plr-sema/eval/oracle_common.py:56`, `:63-64`: `plr_kwargs[index] = {k: repr(v) for k, v in
  plan_result.kwargs.items()}`), carrying them out on `RuntimeOutcome`. So option (a) of the round-1
  question — "fix `adapt_graph` to emit PLR parameter names" — needs **no** hand-typed tool→PLR name
  map: the names come from the verifier's own planner. Whether `#4879` threads `plr_kwargs` through,
  and whether `plan_result.kwargs` actually carries `use_channels`, are facts about `#4879` and the
  verifier that this document does not settle.

  **So the criterion is written to detect its own vacuity rather than assert it.** The replay report
  must print `n_exact_channel_sets` — the count of tier-1 operations whose channel set resolved by
  §10.1.3 rule 1 or rule 3. If it is **0**, AC-10.11 has gated totality and nothing else, and the
  report must say so in those words. If it is **non-zero**, AC-10.11 has become a real soundness gate
  and its 0-unsound-rows result is load-bearing. Either outcome passes; what is forbidden is not
  knowing which one happened. This is the difference between an honest option (c) and an evasion.

  *Corollary for the oracle plan (`260902_plr-sema-oracle-harness.md`):* its tier-2 section calls any
  tier-1/tier-2 divergence "an extractor defect by construction". Under this increment that is no
  longer true — a divergence can equally be an `adapt_graph` argument-naming artefact. That sentence
  needs qualifying in the oracle plan; it is named here so the qualification is not forgotten, and it
  is not a task in this increment.
- **AC-10.12 (oracle gate — mutants, direction only; the increment's real oracle gate).** `#4881`'s
  tip-family mutants (remove `pick_up_tips` → `NoTipError`; duplicate it → `HasTipError`) are
  replayed with **hand-authored PLR-named arguments** (see AC-10.11's Q3 resolution; the mutant
  fixtures carry `use_channels` and `tip_spots`, not `at`). The gate is directional and has no rate:
  (i) **zero** mutant rows in
  which the simulator raised `NoTipError`/`HasTipError` at index `i` carry a static `SAFE` at `i`;
  (ii) **zero** rows in which the simulator ran index `i` clean carry a static `WILL_FAIL` at `i`;
  (iii) **at least one** row in each of the two mutation classes carries a static `WILL_FAIL` at the
  index the simulator raised — i.e. the family moved off `UNKNOWN` in the correct direction at least
  once. Criterion (iii) is what makes this gate unsatisfiable by an evaluator that never fires.

### Task row

| task | scope | files | gate | ~LOC | depends on |
|---|---|---|---|---|---|
| **#4888** | Tip typestate increment, in this order: (1) derive P1/P2/P3/P4 passes + `channel_guards` bridge + `receiver_state` payload block + ledger `tip_state` block, with `tip_state_exceptions` filtered by **both** `category` and `module` (§10.2.5); (2) `check/graph.py` mirror gains `arguments` (`OperationNode`) and `execution_order` (`ProtocolComputationGraph`), §6.2 table edit, Fork C drift test extended to both; (3) `plr_sema/check/tipstate.py` — lattice, channel-set derivation, atom parser (`raise_guard` kinds only), evaluator, and §10.4's E2/E4 split **including E4.3, the conflicting-depth-0-bridge rule**; (4) `check/__init__.py` wiring + the `channel_state_unknown` constructor; (5) `test_reason_vocabulary_closed_forward` verdict-aware exemption (§10.8); (6) three new fixtures + tests, plus the AC-10.9 taxonomy-filter assertions and the AST literal scan; (7) **extend `_measure_hm21` to count `ProtocolComputationGraph` fields and update HM-21's `what` string** (§10.8, round 1 O5) — without this the mirror grows invisibly; (8) HM-14 `declared` 7→8, HM-24 new row, HM-21 `declared` 10→15 (live 8→13 under the fixed measure) | create `plr-sema/src/plr_sema/check/tipstate.py`, `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/tests/test_tipstate.py`, `plr-sema/tests/fixtures/{double_pickup,pickup_then_aspirate,aspirate_after_drop}_graph.json`, `plr-sema/tests/fixtures/derived_contracts_pre_increment.json`; modify `plr-sema/src/plr_sema/check/{__init__,graph}.py`, `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/src/plr_sema/verdict.py`, `plr-sema/src/plr_sema/_hand_maintained.py`, `plr-sema/tests/test_{verdict,derive,check_graph,check_graph_mirror_drift,hand_maintained_ratchet}.py`, `plr-sema/data/derived_contracts.json` (regenerated) | `uv run pytest plr-sema/tests -q` satisfying AC-10.1, AC-10.2, AC-10.3, AC-10.4, AC-10.5, AC-10.6, AC-10.7, AC-10.8, AC-10.9, AC-10.10; then `uv run python -m plr_sema.derive --survey-json training/verify/data/plr_preconditions.json --taxonomy-json training/verify/data/plr_exception_taxonomy.json --out plr-sema/data/derived_contracts.json`; then **AC-10.11** via `#4879`'s tier-1 replay (reporting `n_exact_channel_sets`) and **AC-10.12** via `#4881`'s mutants — AC-10.12 is `#4888`'s gate, not a downstream nicety, and `#4888` is not done until its criterion (iii) fires | ~750 | main spec T1–T9 (shipped); oracle `#4879` for AC-10.11, `#4881` for AC-10.12 |

**Honest sizing note.** ~750 LOC (revised up from ~700 in round 1: the E4.3 conflicting-bridge rule,
the AC-10.9 taxonomy-filter assertions and AST literal scan, and the `_measure_hm21` fix are all new
since the draft) is past the upper edge of one session, above every task in the main spec's own
decomposition except T6 (~450). Sub-steps (1)+(2)+(7) are independently completable and leave the
tree green (the payload grows, `check/` ignores it, the measure fix and its `declared` bump are a
self-contained ratchet diff, every existing test passes) — that is the **minimum shippable split
point** if the session runs long. Do not split between (3) and (4): an evaluator with no emitter is
untested code.

---

## 10.8 Registry, vocabulary and wire-format impact

### `REASON_VOCABULARY` (HM-14): 7 → 8, cap 12 unchanged

One new member, `channel_state_unknown`: *"a guard's condition parsed as a tip-state atom, but the
channel state it reads is ⊤"*. It is required and cannot be folded into an existing member:
`guard_predicate_unparsed` means "could not be turned into a predicate", which would become a **false
statement** for a guard this increment does parse, and main spec §0's rule that a reason names *which
pipeline stage returned nothing* would be violated — the parse stage returned something; the
*evaluation* stage did not. The member is mechanical, not semantic (it names our own give-up point),
so §3.3's classification argument for hand-maintaining the vocabulary carries over unchanged. HM-14's
`declared` moves 7 → 8; the cap of 12 is untouched; the ratchet sees a one-line reviewable diff,
which is exactly what it is for.

`test_reason_vocabulary_closed_forward` **must be amended**, and this is the sharpest trap in the
task. It AST-scans every `Finding(..., reason=...)` construction and requires the resolved literal or
module-level constant to be in `REASON_VOCABULARY` (main spec §3.4). `Finding.reason` has no default
(`plr-sema/src/plr_sema/verdict.py:173`), so the new `SAFE`/`WILL_FAIL` constructors must pass
`reason=""`, which the scan would reject. **Amendment:** the scan resolves the `verdict=` argument at
the same call site; when it resolves to the attribute literal `Verdict.SAFE` or `Verdict.WILL_FAIL`,
the `reason=` argument must be the empty-string literal and is exempt from membership; when it
resolves to `Verdict.UNKNOWN`, or is unresolvable, the existing rule applies unchanged. The reverse
test (every vocabulary member reachable from ≥1 construction site) is unaffected. Giving `reason` a
default instead is **forbidden** — that is a field-set change to the wire record, which §3.5 names as
the highest-consequence assumption in the document.

### Mirror field set (HM-21): the measure is broken, and fixing it is part of the task (round 1, O5)

`check/graph.py` gains one `OperationNode` field and one `ProtocolComputationGraph` field, and main
spec §6.2's normative derived-from-consumers table gains two rows:

| field | consumer |
|---|---|
| `arguments` (`models.py:536-538`) | §10.1.3's channel-set derivation (rules 1 and 3) — the *only* source for `use_channels` and for the channel-default parameter's cardinality |
| `execution_order` (`models.py:642-644`, on `ProtocolComputationGraph`) | §10.5 rule 1 — cross-checks the `operations` list order the state fold depends on |

`arguments` was deliberately **deleted** by the main spec's round-4 M1/B4 pass ("never read by
anything except `graph.py`'s own declaration/parse"; it also fed the withdrawn `argument_not_static`).
Re-adding it is not a reversal of that finding — the finding was that it had no consumer; it now has
one, named above, which is precisely the condition §6.2 sets for a field to be mirrored. B4's
warning still stands and is respected: this increment reads `arguments` **by PLR parameter name and
by `ast.literal_eval` of the value**, never by intersecting it with `depends_on_params`, so the
same-named-collision false-positive path B4 withdrew stays closed.

**The round-1 draft said "8 → 10" and that was wrong, because the measure cannot see the second
field.** `_measure_hm21` (`plr-sema/src/plr_sema/_hand_maintained.py:216-241`) is

```python
def _measure_hm21() -> int:
    from plr_sema.check.graph import OperationNode, ResourceNode
    return len(dataclasses.fields(OperationNode)) + len(dataclasses.fields(ResourceNode))
```

— `OperationNode` + `ResourceNode` only. `execution_order` lands on `ProtocolComputationGraph`
(`plr-sema/src/plr_sema/check/graph.py:135-145`), which the measure never counts. Adding
`arguments` alone would move the measure **8 → 9**, and adding `execution_order` would move it
**not at all**. HM-21 is `declared=10`, `CAPPED`, so 9 sits under the cap and the ratchet **would
not fire** — a hand-maintained surface would have grown invisibly, which is the one thing the
ratchet exists to prevent. This is a live defect in the measure, not merely a bookkeeping slip in
this document: it has been under-counting `ProtocolComputationGraph`'s three mirrored fields since
T9.

**Normative fix, and it is a task line in `#4888`, not a note:** extend `_measure_hm21` to count
`ProtocolComputationGraph`'s fields as well, i.e.

```python
return (len(dataclasses.fields(OperationNode))
        + len(dataclasses.fields(ResourceNode))
        + len(dataclasses.fields(ProtocolComputationGraph)))
```

and update HM-21's `what` string, which today names only "OperationNode/ResourceNode", to name all
three mirror classes.

**The recomputed arithmetic, with the pre-existing under-count separated from this increment's own
growth:**

| | `OperationNode` | `ResourceNode` | `ProtocolComputationGraph` | measure |
|---|---|---|---|---|
| today, as measured | 7 | 1 | *(not counted)* | **8** |
| today, under the fixed measure | 7 | 1 | 3 | **11** |
| after this increment, fixed measure | 8 (`+arguments`) | 1 | 4 (`+execution_order`) | **13** |

So the fixer's ratchet diff is `declared: 10 → 15` (§9.1's live+2 headroom rule for `CAPPED` rows,
applied to the post-increment live count of 13), and the commit message must separate the two
components: **+3 is the correction of a measure that was never counting a mirrored class, +2 is this
increment's actual new surface.** Rolling them together would understate the increment and overstate
the defect, or vice versa, and a ratchet diff that cannot be read is not a review artifact. Fork C's
`test_mirror_fields_match_operation_node` (§5.3) must be extended to both new fields in the same
commit or it will not see them.

### Registry: one new row, HM-24 — the front end's syntactic patterns

The design needs **no** hand-typed PLR fact: no class name, no method list, no exception name, no
field name. What it does need is six *syntactic patterns* — heuristics over how PLR is written, in
the same spirit as HM-3's validator-name prefixes:

| # | pattern | where |
|---|---|---|
| 1 | channel-receiver shape `self.<attr>[<name>].<method>` | §10.2.5 bridge |
| 2 | typestate-anchor shape: a property whose body is `return self.<F> is/is not None` | §10.2.2 |
| 3 | channel-default idiom `<p> = <p> or self.<x> or list(range(len(<q>)))` | §10.2.3 |
| 4 | atom `<path>.<bool_view.attr>` | §10.3.1 |
| 5 | atom `<path>.<state_field> is None` | §10.3.1 |
| 6 | atom `<path>.<state_field> is not None` | §10.3.1 |

**HM-24** — *tip-typestate front-end syntactic patterns* — metric: patterns; baseline **6**; status
**CAPPED (8)** (live+2, §9.1's D16c rule); `why_not_derived`: *"These are patterns over PLR's coding
style, not facts about PLR that any artifact records. Deriving them would require a meta-analysis
that recognises 'this is how this codebase spells a typestate', which is the analyzer's own
judgement, not PLR's data — the same argument HM-3 makes for validator-name prefixes."*;
`breaks_when`: *"PLR renames `has_tip`'s pattern, replaces `self.head[c]` with a method accessor
(`self.channel(c)`), or drops the `or list(range(len(...)))` idiom. All three fail **closed**: the
pattern stops matching, the feature disables itself for that class (§10.2.2's fail-closed rule), and
every verdict reverts to `UNKNOWN`. None of them can produce a wrong verdict."*

Live rows: 22 → **23**. Cap stays **24**; headroom 2 → **1**. Registering these as *one* row rather
than two or six is deliberate and is the opposite of RISK-8's splitting concern: they are one
coherent surface (the front end's syntax) with one failure mode.

**This is option A of an open decision, not a settled fact.** Round 1 argued that pattern 1 (the
bridge shape) has a materially different failure profile from patterns 4–6 (the atom grammar) —
silent family collapse versus a loud exact-count test failure — and should be its own row. That
would make it 24 live rows, headroom **0**. §10.10's Q7 disposition carries the full arithmetic for
both options and reserves the choice for the user; if B is chosen, this subsection splits into
HM-24 and HM-25 and the summary table at the head of this document changes `23 live` to `24 live`.
Nothing else in the increment depends on which way it goes.

**No HM row is needed for the two exception class names** — `HasTipError`/`NoTipError` are selected
by `category == "tip_state"` **and** `module == "pylabrobot.resources.errors"` from
`training/verify/data/plr_exception_taxonomy.json` (§10.2.5, corrected in round 1: the category
alone selects five names, not two), an artifact whose categories are themselves derived by HM-19's
already-registered keyword table. Writing the names into `plr_sema` would be new hand-typed surface;
reading them out of the artifact is not. AC-10.9's **AST literal scan** — not a grep (round 1, O8) —
is the enforcement, and AC-10.9's second sub-assertion pins the filter itself so the two-conjunct
rule is checked rather than trusted.

### Wire format: no change

`Verdict`'s three members, `Finding`'s seven fields, `PlrSite`, `AnalysisReport`'s field set,
`SCHEMA_VERSION = 1` (`plr-sema/src/plr_sema/verdict.py:74`), and `join`'s body and signature are all
**unchanged**. `Verdict.from_wire`'s widening rule is unchanged. `derived_contracts.json` keeps
`schema_version: 1`: both additions are new optional keys read through `.get()`, and a checker
running against a pre-increment table degrades to today's behaviour (AC-10.7) rather than raising —
which is the same fail-closed-to-`UNKNOWN` direction §Open decisions 1 establishes as always sound.

---

## 10.9 Explicitly not in this increment

- **Volume atoms.** Every numeric `Cmp` stays ½, per main spec §Open decisions 2, including
  `drop_tips`'s depth-0 `tip.tracker.get_used_volume() > 0 and (not allow_nonzero_volume)`. Volume
  also needs a `SoundnessScope` record for `does_volume_tracking()`, which tip state does not
  (§10.6.3).
- **Branches.** `condition_expr`/`true_branch`/`false_branch` stay unmirrored; the walk widens on
  them (AC-10.6) rather than modelling them. No branch-merge join, no ⊥, no fixpoint.
- **Loops.** Widen, do not analyse. `items_x`/`items_y` trip counts are not consulted; deferred (d)
  stays deferred.
- **Aliasing.** A-SINGLE is assumed, not checked (§10.6.3).
- **The 96-head.** `head96`, `pick_up_tips96`, `aspirate96`, `drop_tips96`, `stamp` are untouched.
  `head96` has a different attribute name and a different tracker arity; the P1 pass will type it,
  but §10.1.3 has no channel-set rule for it, so every 96-head operation falls to rule 4 (`⊤`).
- **Compound conditions.** Only single atoms are interpreted; `and`/`or`/`not` conditions fall
  through to `guard_predicate_unparsed`, unchanged.
- **`assert`-kind tip-state guards.** Round 1's Q2 dropped the `assert` production (§10.3.1). No
  guard in the shipped table exercises it; the branch returns when a test does.
- **Single-hop passthrough.** `discard_tips` and `return_tips` widen rather than inheriting
  `drop_tips`'s effect (§10.2.6, round 1's O4). Recovering them is a named follow-up.
- **Non-`LiquidHandler` receivers.** Any receiver class without a P1a channel attribute typing to a
  P2-anchored class gets no state and no behaviour change. The whole-surface contract table
  (4,770 entries) is untouched; this increment reads it, it does not narrow it.
- **The non-legacy surface.** The verifier and the oracle run at submodule pin `dd79c4c89`, where
  `LiquidHandler` lives under `legacy/`. `upstream_nonlegacy` has contracts (T14) but no executable
  oracle, so this increment is specified, derived and gated **at the pin**. `SurveyStamp.surface` /
  `surface_pin` (`plr-sema/src/plr_sema/check/__init__.py:158-173`) already record which surface a table came from; the
  fixer changes nothing there.
- **Precision targets.** No threshold, no rate, no `UNKNOWN`-reduction goal. Deferred (f) stands.

---

## 10.10 Dispositions of the round-1 open questions

The draft closed with seven open questions for the adversarial round. All seven were adjudicated by
the round-1 challenger (`.praxia/docs/audits/260902_plr-sema-tip-typestate-round1-challenger.md`)
and the adjudication was accepted by the defender
(`.praxia/docs/audits/260902_plr-sema-tip-typestate-round1-defender.md`). **Six are closed. One
(Q7) is a decision reserved for the user**, with both options costed below. None is left open for a
second adversarial round.

**Q1 — merging `_tip` and `_pending_tip`: RESOLVED. The merge stands; the argument for it did not.**
The challenger produced a concrete PLR path that leaves a head tracker uncommitted across an
operation boundary — `clear_head_state` → `update_head_state` → `remove_tip(commit=False)` — which
is exactly what the question asked for. It does not produce a wrong verdict, because the path is
depth-1 and widens (§10.6.4 walks it in full). But the *prose* justifying A-COMMIT claimed a
property of "every `LiquidHandler` tip operation" that is false, and §10.2.2 now names the two
methods it holds for (`pick_up_tips`, `drop_tips`) and the two it does not (`update_head_state`,
`clear_head_state`). The proposed remedy — two cells that must agree — is **not** adopted: it is
unnecessary once every method that can desynchronise the fields widens first, and it would add
machinery to model a state the analyzer never reads. See also Q1's sibling, O2, which is the case
where the same path *does* bite and which is closed by a new rule (§10.2.4, §10.4's E4.3).

**Q2 — the `assert`-kind atom: RESOLVED as option (b). The production is dropped.** §10.3.1's
criterion 1 now admits `raise_guard` only, and §10.3.3's polarity line no longer carries the
`assert`-fires-on-FALSE half. The reasoning is the one the draft itself leaned toward on Chesterton
grounds: no tip-state guard in the shipped table is an `assert`, so specifying the branch ships
untested code that will rot before it is ever exercised. `InlinedGuard.kind` still records polarity,
so **re-adding it costs one line** — and the condition for re-adding it is stated in §10.3.1: a
contract fixture, real or synthetic, that exercises an `assert`-kind tip-state guard, landed in the
same commit as the branch and never after it.

**Q3 — tier-1 vacuity: RESOLVED as option (c), with the vacuity written into AC-10.11's own text.**
The challenger's judgement was that (c) is honest *provided the criterion discloses it*, and it now
does: AC-10.11 states in its own body that it is vacuous under tool-named arguments, states that it
therefore gates totality and non-regression only, and requires the replay to report
`n_exact_channel_sets` so that the vacuity is *measured* rather than assumed. AC-10.12 carries the
real directional gate and is `#4888`'s own gate, not a downstream one (see the task row). One thing
the round-1 draft got wrong in the challenger's favour and against its own: option (a) does **not**
require hand-typing a tool→PLR name map — `run_runtime` already harvests PLR-named kwargs from the
verifier's `plan_call` (wrapped by `recording_plan_call`, `plr-sema/eval/oracle_common.py:404-415`) and `adapt_graph` already
accepts them (`:94`, `:118-125`). Option (a) is therefore cheaper than the draft claimed and is the
natural follow-up; (c) is chosen for *this* increment because it does not make `#4888` depend on a
change to `#4879`'s harness. The corollary for the oracle plan — that a tier-1/tier-2 divergence is
no longer "an extractor defect by construction" — is recorded under AC-10.11 so the qualification is
not lost.

**Q4 — one `channel_state_unknown` member or two: RESOLVED as one.** The challenger's adjudication
was that one member is fine. HM-14 moves 7 → 8 of cap 12. The distinction the question worried about
(state widened vs. argument not a literal) is real but is recoverable from the ledger and from
AC-10.11's `n_exact_channel_sets` counter without spending a second vocabulary slot; splitting it
later is a one-member diff, and the ratchet will show it.

**Q5 — E4 over-widening: RESOLVED as accepted.** The challenger's adjudication was "sound,
imprecise, fine". E4 widens the whole receiver rather than a may-touch channel subset, which the
graph does not carry. Round 1 made this *more* consequential rather than less — `discard_tips`,
`return_tips` (O4) and `clear_head_state`/`update_head_state` (O1/O2) all now widen too — so the
imprecision is larger than the draft estimated and is accepted anyway, because every alternative
trades a measurable `UNKNOWN` rate for an unmeasurable soundness risk. `#4879` reports the
`UNKNOWN` rate by method family; that report, not this document, is where the cost becomes visible.

**Q6 — should `default` leave `TOP`: RESOLVED as no; `default` stays and stays `TOP`.** The
challenger's adjudication was "defer". The field is kept for the `setup()`-aware rule named in
§10.1.3 (`liquid_handler.py:197`), which is the cheapest precision win left. Note this is
deliberately *not* the same call as Q2, which removed an unexercised production: `default` is a data
field with no branch behind it, so it cannot silently rot the way an uninterpreted `assert` branch
can — there is no code path to test.

**Q7 — one registry row for six patterns, or two: DECISION FOR THE USER. Not resolved here.** The
challenger leaned toward splitting pattern 1 (the `self.<attr>[<name>].<method>` bridge shape) into
its own row, on the grounds that its failure profile differs from the atom grammar's: if the bridge
shape stops matching, the tip-*requiring* family collapses to empty and every verdict silently
reverts to `UNKNOWN` — a **silent family collapse** — whereas if an atom production stops matching,
AC-10.1/10.2/10.3's exact-count assertions fail loudly. That is a real asymmetry and it is the
strongest argument available in either direction. It is left to the user because it spends the
registry's last headroom, and headroom is the user's budget, not the spec's.

> **Decided 260902 (user): SPLIT.** HM-24 = the channel-receiver bridge pattern alone (its failure
> mode is a silent family collapse, invisible without an `UNKNOWN`-rate measurement); HM-25 = the other
> five patterns (typestate-anchor property, channel-default idiom, three atom productions), each of
> whose failures AC-10.1–10.3's exact-count assertions catch. Live rows 22 → 24, headroom **0**: the next
> hand-typed fact requires a new adversarial-round argument to widen `BUDGET_CAP`, which is what §9.4
> intends. #4888 files both rows. Also decided the same day: this increment is now BLOCKED on the
> IR/bytecode increment (spec_version 10, #4921) — §10.8's `arguments`/`execution_order` re-mirroring
> and §10.1.3's channel-set inference are implemented as the lowering, not as mirror fields.

The arithmetic, stated so the decision is a choice between two numbers rather than a judgement call.
Pre-increment: **22 live rows, cap 24, headroom 2.**

| option | rows added | live | cap | headroom | what breaks loudly | what breaks silently |
|---|---|---|---|---|---|---|
| **A — one row (HM-24, six patterns)** — as specified in §10.8 | 1 | **23** | 24 | **1** | atom-grammar drift (AC-10.1/10.2/10.3 fail on exact counts) | bridge-shape drift (tip-requiring family empties; every verdict reverts to `UNKNOWN`; AC-10.10 catches it only because it asserts `"aspirate" ∈ tip_requiring`) |
| **B — two rows (HM-24 atom grammar 3 patterns + HM-25 bridge shape 1 pattern, with 2 remaining patterns assigned)** | 2 | **24** | 24 | **0** | same, plus the bridge shape now has its own `breaks_when` and its own reviewable baseline | nothing new; the split is precisely to make the silent case visible in the registry |

Under **A**, the next hand-maintained surface anyone adds hits the cap and forces a cap-raise
conversation. Under **B**, that conversation happens now. Neither is gaming: §9.4's anti-gaming
clause targets *splitting to dilute*, and RISK-8 concedes there is no cross-row sum check, so both
directions are currently unconstrained by the mechanism — which is itself worth recording as a gap
in §9.4 rather than resolved by picking whichever number looks better.

**Recommendation, offered and not assumed:** the challenger's argument is good and **B** is the
better engineering answer, because the failure mode it separates out is the only one in this
increment that is invisible to every acceptance criterion except AC-10.10. But **A** is what §10.8
currently specifies, and this document does not change it without the user's word — spending the
registry's last slot is exactly the kind of decision the ratchet exists to route to a human.

---

## References

- Main specification (amended by this document): `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md`
  — §0 (the organizing claim), §3 (verdict/finding/join, `REASON_VOCABULARY`), §6.2 (mirror field
  set, `check_graph`), §7.2–7.3 (closure mechanic, `InlinedGuard`, contract table), §9 (registry,
  budget, ratchet), Deferred (a)/(c)/(d)/(e)/(f), Open decisions 1–3.
- Research: `.praxia/docs/research/260901_plr-sema-research-a-d.md` (Q3's typestate adjudication,
  `:246-266`; R3 at `:520-526` is **wrong and must not be implemented**, per main spec §Open
  decisions 3's correction and `plr-sema/src/plr_sema/verdict.py:248-261`);
  `.praxia/docs/research/260901_plr-sema-research-c-e.md` (Q2's ranked resolution mechanisms and the
  measured `self.head[channel].get_tip → TipTracker` result, `:149-176`; Q5's atom grammar,
  `:439-483`).
- Oracle: `.praxia/docs/plans/260902_plr-sema-oracle-harness.md`; `plr-sema/scripts/oracle_spike.py`;
  `plr-sema/eval/oracle_common.py`. Backlog `#4879` (tier-1 replay), `#4880` (tier-2 extractor),
  `#4881` (tier-3 mutants), `#4882` (tier-4 fuzz).
- Code read for this document: `plr-sema/src/plr_sema/verdict.py`,
  `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/src/plr_sema/check/graph.py`,
  `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/tests/fixtures/simple_transfer_graph.json`,
  `training/verify/failure_taxonomy.py`, `training/verify/dispatcher.py`,
  `training/floor_gen/exec_verify.py`, `praxis/backend/utils/plr_static_analysis/models.py`.
- Artifacts read verbatim: `plr-sema/data/derived_contracts.json`,
  `training/verify/data/plr_preconditions.json`, `training/verify/data/plr_exception_taxonomy.json`.
- PLR source at submodule pin `dd79c4c89`:
  `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py`,
  `external/pylabrobot/pylabrobot/resources/tip_tracker.py`.
- **Adversarial round 1:** challenger
  `.praxia/docs/audits/260902_plr-sema-tip-typestate-round1-challenger.md` (O1–O9 + adjudication of
  §10.10's seven open questions); defender
  `.praxia/docs/audits/260902_plr-sema-tip-typestate-round1-defender.md` (per-objection
  REBUT/CONCEDE/PARTIAL, post-defense severity table, verdict `needs_revision`). The defender's
  adjudication is what this revision applies; the changelog below maps each objection to the text
  that changed.
- Additional source read to verify the round-1 remediation, at the same pin:
  `external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/STAR_backend.py`,
  `praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py`,
  `plr-sema/eval/oracle_common.py`, `plr-sema/src/plr_sema/_hand_maintained.py`,
  `plr-sema/tests/test_verdict.py`.

---

## Remediation changelog (round 1)

Target of the round: this document at commit `ca54866d`, `status: draft`. Verdict was
`needs_revision` with 2 surviving blockers, both closable with text. Every change below is text or a
task-row line; **no change to the core design** (per-channel typestate lattice, dropped-receiver
channel bridge, depth-0-only effect/widen split, execution-order walk, per-guard findings), no
`schema_version` bump, no wire-format change, no new deferred item.

| id | severity (orig → post-defense) | what changed | section(s) |
|---|---|---|---|
| **O1** | BLOCKER → PARTIAL | A-COMMIT narrowed from "every `LiquidHandler` tip operation" to `pick_up_tips` + `drop_tips` only; `update_head_state` / `clear_head_state` named as explicit violators, each with the rule that keeps them from reading the merged cell (E4.2 and E4.3 respectively). The challenger's counterexample recorded in full as a **worked non-example**, including what it did and did not establish. The A-COMMIT assumption row rewritten. | §10.2.2, **§10.6.4 (new)**, §10.6.3 |
| **O2** | BLOCKER → **survives** | New normative rule: a `K` whose own body contains ≥2 depth-0 bridges to disagreeing P4 effects triggers **E4 (widen)** — never E2, never "no effect". Includes the defender's three-step trace showing "no effect" manufactures a false `WILL_FAIL` (`has_tip` reads `_pending_tip`, which `remove_tip()` clears even uncommitted). E2 restated to require a single agreed effect; E4 restructured into four numbered triggers. | §10.2.4, §10.4, §10.2.6 |
| **O3** | BLOCKER → **survives** | `tip_state_exceptions` selection rule corrected to `category == "tip_state"` **and** `module == "pylabrobot.resources.errors"`. The unfiltered 5-member set named in a table. The 3 Hamilton members shown harmless (0 occurrences in `derived_contracts.json`; their taxonomy trigger sites are `codes`-dict dispatch entries, not `raise` statements). AC-10.9 restructured into three sub-assertions, the second of which makes the module filter an AC-checked fact. | §10.2.5, AC-10.9, §10.8 |
| **O4** | MAJOR | "by delegation `discard_tips`, `return_tips`" struck from §10.2.6's tip-dropping Expected list; both shown to reach `remove_tip` only at depth 1, structurally identical to `move_tips`, and therefore widening via E4. Single-hop-passthrough named as a follow-up outside this increment, with the reason it is not adopted now. | §10.2.6, §10.9 |
| **O5** | MAJOR | `_measure_hm21` shown to count `OperationNode` + `ResourceNode` only, so `execution_order` (on `ProtocolComputationGraph`) is invisible to it and `arguments` alone moves it 8 → 9, under the `declared=10` cap — the ratchet would not fire. Explicit task line added to extend the measure; declared bump recomputed as **10 → 15** (live 8 → 13 under the fixed measure), with the +3 pre-existing under-count separated from the +2 of this increment. | §10.8, task row `#4888` |
| **O6** | MINOR | §10.3.2's "meet" corrected to §10.1.1's join `⊔` folded over the channel set, with the reason a meet does not exist here (no ⊥) and why the join is the sound fold. | §10.3.2 |
| **O7** | MINOR | "eight" → **nine** in §10.6.2's worked `SAFE` example (`aspirate` has nine own guards; the bridged guard is a tenth finding). *Extended, disclosed:* the identical miscount in §10.3.3's `join`-grouping argument was corrected the same way; it was not separately raised in round 1. | §10.6.2, §10.3.3 |
| **O8** | MINOR | AC-10.9's "grep" replaced with an **AST literal scan**, citing the existing mechanism (`test_reason_vocabulary_closed_forward` / `_find_finding_reason_sites`), plus the requirement that the docstring exclusion itself be tested. | AC-10.9, §10.8 |
| **O9** | MINOR | `use_channels` corrected from "async context manager" to a synchronous `@contextlib.contextmanager` (`liquid_handler.py:1363-1364`) in both places it appeared, with a note that the correction changes no derivation. | §10.1.3, §10.2.3 |
| **Q1** | open question | Resolved: merge stands, argument narrowed. See O1/O2. | §10.10 |
| **Q2** | open question | Resolved as option (b): `assert`-kind atom production **dropped** from §10.3.1's criterion 1 and its half of §10.3.3's polarity line removed; re-add condition stated as a test, not a preference. | §10.3.1, §10.3.3, §10.9, §10.10 |
| **Q3** | open question | Resolved as option (c): AC-10.11's own text now states it is vacuous under tier 1's tool-named arguments and gates totality/non-regression only; AC-10.12 named as the real gate and moved into `#4888`'s own gate. Adds a required `n_exact_channel_sets` report so the vacuity is measured. Corrects the round-1 claim that option (a) needs a hand-typed name map — `run_runtime`/`adapt_graph` already carry PLR-named kwargs. | AC-10.11, AC-10.12, §10.10, task row |
| **Q4–Q6** | open questions | Recorded as decided: one `channel_state_unknown` member (Q4); E4 over-widening accepted, and noted to be *larger* after O1/O2/O4 (Q5); `default` stays and stays `TOP` (Q6). | §10.10 |
| **Q7** | open question | **Reserved for the user, then DECIDED 260902: split (HM-24 bridge shape, HM-25 the five others; headroom 0)** —, with full ratchet arithmetic for both options: A (one row) → 23 live / cap 24 / headroom **1**; B (split the bridge shape out) → 24 live / cap 24 / headroom **0**. Recommendation stated (B) and explicitly not applied. | §10.10, §10.8 |
| *lint* | cross-reference | AC-10.12 was defined but gated by no task row; it is now named explicitly in `#4888`'s gate ("AC-10.12 is `#4888`'s gate, not a downstream nicety"), and every AC in that gate is spelled out individually rather than as a range. | task row `#4888` |

**Corrections made in passing, disclosed because they were not raised in round 1.** Each was found
while verifying a citation the remediation touched, and each is a citation that was wrong in the
draft:

| what | was | now |
|---|---|---|
| A-COMPLETES's citation for the oracle's `not_reached` marking | `oracle_common.py:148-163` (that range is `run_static`'s per-operation grouping) | `plr-sema/eval/oracle_common.py:198-204`, inside `compare` |
| AC-10.11's citation for `compare`'s unsoundness predicate | `oracle_common.py:161-163` (a comment banner) | `plr-sema/eval/oracle_common.py:206-211`, the `unsound` expression |
| §10.2.2's cross-reference to the assumptions table | "§10.7" | §10.6.3 |
| §10.1.3's forward reference to the tier-1 vacuity discussion | "§10.12, Q3" (no §10.12 exists) | AC-10.11 and §10.10's Q3 |
| §10.7's `#4888` scope step (5) cross-reference for the vocabulary amendment | "§10.10" | §10.8 |

**Not applied, and why.** Nothing in the defender's adjudication was left unapplied. Two items are
deliberately *not* resolved in this revision because they are not the spec's to resolve: **Q7**
(registry row split — costed, recommended, reserved for the user) and the **module-path literal**
disclosed under AC-10.9, where the spec takes a position (no HM row needed, it names package layout
and fails closed) and invites a reviewer to overrule it with one more `CAPPED` row.
