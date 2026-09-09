---
title: "plr-sema increment 5 — the volume family: an interval domain that decides a tip over-draw"
description: "Fifth post-corpus increment to the plr-sema pre-corpus specification, remediated after its own adversarial round 1 (challenger O1-O14, defender's twelve-item ordered list). What it ships, stated as narrowly as round 1 forced: **a definite `WILL_FAIL` on a tip over-draw, and `SAFE`/`UNKNOWN` on every well.** The challenger's O1 established that §14.6's fail-closed recognition rule blocks `WILL_FAIL` on every guard whose `caller_scope` contains a `for` header; the defender rejected the global claim with a mechanism — R1, which recognises the B1-bound `ast.For` **structurally, by position containment**, because V2 already unrolls that exact loop and PLR's own `ValueError` (`liquid_handler.py:989-992`) pins its trip count to the pair list's length. `is_disabled` stays fail-closed (per-instance; both candidate discharges fail), and that costs exactly one decidable guard: of the four bridged guards, only `dispense`'s `op.tip.tracker.remove_liquid` (`liquid_handler.py:1235`) is both under-draw and outside the `is_disabled` test, and it is the headline deliverable. Consequently the acceptance criteria move from the well to the tip, AC-14.6's executed half is withdrawn, and §14.9's mutant class is re-sited onto `dispense`. Q3 **inverts to survey-side**: `scripts/survey_plr_preconditions.py:250` records `(text, lineno, scope_trail)` and `plr_preconditions.json` is regenerated, because the `lineno` is what lets R1 key on node position instead of reconstructed text, and because the survey's `visit_If` already carries the `else of: if ...` polarity a derive-side P10 would have had to re-implement. Three further blockers are folded in: P1c scans **every method** of a class (`Tip.tracker` is written in `__post_init__`), a tip cell gets a lifecycle (`TOP` on drop, `[0,0]` on pickup only while a monotone `tips_dirty` is false), and V0 gains the clause (D1) that resolves the tip guard's local pairing to `[(\"tip\", c) for c in channels_for_call(op)]`. Registry: **HM-24 `declared` 1 → 3** (the volume bridge shape and B1, both silent-collapse failures), HM-25 6 → 8, `REASON_VOCABULARY` 8 → 10 of cap 12, `live_rows()` unchanged at 24. **The HM-24 arithmetic was approved by the user 260904 and T27 spent it** — the previously planned figure was 1 → 2."
status: implemented-round-1
spec_version: 15
amends: 260901_plr-sema-pre-corpus-spec.md
task_id: 260903_sema-followups
date: '260903'
confidence: medium
sources: "Created by re-scoping section 13.2 of .praxia/docs/specs/260903_plr-sema-families-cache-increment.md (spec_version 12 draft, b89de024) after that document's adversarial round 1, then remediated after this document's OWN adversarial round 1. Round-1 reports on THIS document, read in full: .praxia/docs/audits/260903_plr-sema-volume-round1-challenger.md (O1-O14) and .praxia/docs/audits/260903_plr-sema-volume-round1-defender.md (adjudications, D1/D2, the twelve-item ordered remediation list, verdict needs_revision). Round-1 reports on increment 4, also read in full: .praxia/docs/audits/260903_plr-sema-families-cache-round1-challenger.md and .praxia/docs/audits/260903_plr-sema-families-cache-round1-defender.md. Specs: .praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md sections 10.1-10.5, 10.9; .praxia/docs/specs/260902_plr-sema-ir-bytecode-increment.md sections 11.1.2-11.1.4, 11.3; .praxia/docs/specs/260903_plr-sema-real-programs-increment.md sections 12.1.2-12.1.6, 12.3.3, 12.13; .praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md sections 0, 0.1, Open decisions 2, 9.1-9.4, Deferred. Analyzer source re-read and re-anchored this pass (every citation below verified against cat -n output): plr-sema/src/plr_sema/derive/receiver_state.py:167-170,173-184,298-307,547-587,714-733,978-1042; plr-sema/src/plr_sema/check/ir.py:180-205,320,446,780-824,860-887,915-953; plr-sema/src/plr_sema/check/__init__.py:340-393,710-779; plr-sema/src/plr_sema/check/tipstate.py:238-257; plr-sema/src/plr_sema/check/_supported_tools.py:1-24; plr-sema/src/plr_sema/check/graph.py:193; plr-sema/src/plr_sema/verdict.py:129-154; plr-sema/src/plr_sema/_hand_maintained.py:43,238-272,553-572,786-872. Survey: scripts/survey_plr_preconditions.py:78-120,128-198,225-264. Harness: plr-sema/eval/oracle_common.py:690-739,976-1006; plr-sema/eval/tip_mutants.py:63-70,86-224,227-251; plr-sema/eval/region_oracle.py:340-351,405-439,508-533; training/verify/verifier.py:105-152; training/tests/test_verify_postconditions.py:70-85. Lint: plr-sema/tests/test_spec_lint.py:28-49,212-255. PLR at submodule pin dd79c4c89: liquid_handling/liquid_handler.py:648-667,955-1069,1170-1199,1220-1249,1273-1361,1925-1943; liquid_handling/standard.py:48-75; resources/volume_tracker.py (in full, 171 lines); resources/container.py:22-94; resources/tip.py:11-80; resources/tip_rack.py:40-59. Artifacts: plr-sema/data/derived_contracts.json:157962-158133,158054,158185-158197; training/verify/data/plr_exception_taxonomy.json:2964-2972,2991-2999,3010-3056; training/verify/data/plr_preconditions.json:49764-49773,49808-49812,49863-49864. Data: outputs/plr-sema/oracle_replay_260903_rebaseline.json:2-29; outputs/plr-sema/tier2b_260903.json:1-45."
---

# Increment 5: the volume family

> **This document amends `260901_plr-sema-pre-corpus-spec.md` by reference** and adds §14 to that
> document's numbering. It was created by moving §13.2 out of
> `260903_plr-sema-families-cache-increment.md` (spec_version 12) after that document's adversarial
> round 1, and it has now had **its own** adversarial round 1 (challenger O1–O14, defender's twelve
> ordered items), which this revision executes. Increment 4 ships the cache (#4922), the derived inert
> filter (#4883) and the delegate-call channel binding (#4946), and keeps a one-paragraph §13.2 stub
> pointing here.
>
> **What this increment ships, stated as narrowly as round 1 forced it:** *a definite `WILL_FAIL` on a
> tip over-draw, and `SAFE`/`UNKNOWN` on every well.* §14.6's R1 and its disposition table (§14.0.2)
> are the whole argument for that sentence, and §14.12's criteria are written against it rather than
> against the wider claim the draft made.
>
> **The registry arithmetic increment 4 does *not* spend, and this increment carries:** HM-24
> `declared` **1 → 3**, HM-25 `declared` 6 → 8, and `REASON_VOCABULARY` 8 → 10 of cap 12. Increment 4
> spends only HM-25 5 → 6, for P9 alone. The row-count cap is untouched at 24 live against
> `BUDGET_CAP = 24` (`plr-sema/src/plr_sema/_hand_maintained.py:43`) in both documents.
> **HM-24 1 → 3 was approved by the user 260904, and T27 spent it** — the
> figure this document carried into round 1 was 1 → 2, and the defender's O12 adjudication moved B1
> from HM-25 to HM-24 on the registry's own silent-versus-loud criterion (§14.11).

---

## 14.0 What must be proved first

§13.2 claimed the volume family was *the* derivable one — the counterpart to the lid family, which
§13.1 declined on four structural blockers. Increment 4's round 1 verified that claim and falsified it
in a specific, bounded way, and this document's own round 1 then found three more blockers inside the
remediation. **Almost all of the section still survives**, and it is worth saying exactly which parts.

**What survived both rounds, unchallenged:** the interval domain and its lattice (§14.3), the capacity
asymmetry that makes the over-fill half undecidable (§14.2), the two-conjunct taxonomy selector that
picks `{TooLittleLiquidError, TooLittleVolumeError}` out of four `volume_state` members (§14.1), the
seeding convention that reuses §12.1.6's scaffolding-`CALL` precedent (§14.8), and V2's sequential
threading (§14.5). Both challengers checked the guard shapes, the taxonomy categories and the
`dropped_calls` entries against source and confirmed all of them; this round's challenger additionally
confirmed that volume tracking **is** enabled where the fixtures execute
(`training/verify/verifier.py:114`, `plr-sema/eval/region_oracle.py:414`), which is what makes the
executed oracle possible at all.

**What did not survive increment 4's round 1 is one sentence: that the bridge derives.** §13.2.1
offered four facts as evidence, and fact 3 — *"the bridge expressions are already recorded"* — is true
of the *survey* and false of the *matcher*. `dropped_calls` does record
`op.resource.tracker.remove_liquid` (`training/verify/data/plr_preconditions.json:62202`), and
§13.2.4's normative box cannot match it. Four independent gaps:

| id | gap | evidence | precedent in `derive/` |
|---|---|---|---|
| **G1** | `<name>` must be "a comprehension target of a P8 match". `op` is not one: P8's zip-bound names are `r, v, o, fr, lh, t, bav, m` (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1018-1031`), and `op` is the loop variable of a **separate** statement, `for op in aspirations:` (`:1031`), iterating the comprehension's *output list* assigned at `:1007` | `liquid_handler.py:1007-1031` | none |
| **G2** | `<attr>`'s type must come from a P1a map. `SingleChannelAspiration` is a `@dataclass(frozen=True)` whose fields are **class-level bare-name annotations** — `resource: Container` at `external/pylabrobot/pylabrobot/liquid_handling/standard.py:53`, `tip: Tip` at `:55`, `volume: float` at `:56`. `_annotated_attributes` keeps only `ast.AnnAssign` nodes whose target passes `_is_self_attr` (`plr-sema/src/plr_sema/derive/receiver_state.py:221`, predicate at `:208-211`), and a dataclass field's target is `ast.Name("resource")`, which fails that predicate unconditionally | `external/pylabrobot/pylabrobot/liquid_handling/standard.py:51-60`, `receiver_state.py:208-224` | none |
| **G3** | Even granting G2, the *second* hop fails independently: `Container.__init__` writes `self.tracker = VolumeTracker(...)` as a plain `ast.Assign` (`external/pylabrobot/pylabrobot/resources/container.py:85`), and P1a walks `ast.AnnAssign` only | `container.py:85`, `receiver_state.py:180` | **yes** — `_constructor_state` (`receiver_state.py:588-627`) already walks both `ast.Assign` (`:613`) and `ast.AnnAssign` (`:616`) in a class's own `__init__` |
| **G4** | The `env` gate has nothing to gate. `compute_channel_bridge` sources a bridged guard's `scope_trail` from `derive_contract(...)` on the **callee** (`receiver_state.py:978-1042`, the copy at `:1042`), and `VolumeTracker.remove_liquid`'s own record names only its own condition. The caller-side conjuncts `if does_volume_tracking():` and `if not …is_disabled:` (`liquid_handler.py:1032-1033`) live one syntactic level above the dropped call, and the survey's `dropped_calls` is a **bare string list** with no line number and no scope (`plr_preconditions.json:62190-62216`, pre-T25 shape) | as cited | partial — the survey *does* carry `scope_trail` for a method's own findings, just never for a dropped call |

**G4 is a soundness gap, not a precision gap.** With the bridge fixed (G1–G3) and the threading
absent, §14.6's rule finds no `does_volume_tracking` anywhere in the bridged guard, never marks it
conditional, and under the **default** `env = frozenset()` emits `WILL_FAIL` for a program in which
volume tracking may never have been on and the guard body never ran. That is the first-severity error
class — a definite verdict constructed from a hypothesis nobody asserted.

> **Normative (the gate on this increment).** No `Finding`-constructing machinery from §14.5 or §14.6
> may land until **T24 and T25 have both landed and published their measured selections**. This is
> not a scheduling preference; it is G4's soundness argument. A partial landing of T24 alone leaves
> the analyzer able to construct a definite volume verdict with no hypothesis gate, which is strictly
> worse than today's `guard_predicate_unparsed`.

### 14.0.1 Task (a) — the volume bridge, three normative sub-boxes

Each box below is stated at the same discipline §13.2.4 demanded of P7 and P8: **the expectation is
measured and published by the fixer, never assumed from this document.**

> **Normative (B1 — for-loop binding over a comprehension's output list).** Extend the `<name>`
> binding of the volume bridge. In addition to a P8 comprehension target, `<name>` may be the single
> target of an `ast.For` statement, at **depth 0** in `K`'s body (excluding nested function and lambda
> definitions), whose `iter` is a bare `ast.Name` that is the single `ast.Assign` target of a P8
> match's own comprehension **within the same method**. The bound element type is that P8 match's
> element class `O`.
>
> **B1 additionally records that `ast.For` node's own span** — `for_span: [lineno, end_lineno]` — on
> every guard the bridge attaches through this binding. That span is not decoration: it is the key
> §14.6's R1 tests position containment against, and it is the *only* reason R1 can recognise a loop
> header without falling back to reconstructed text (§14.0.2, O7/Q3).
>
> **Fail-closed.** If `K`'s body contains more than one such `ast.For` over the same name, or the
> `ast.For` target is a tuple rather than a single `ast.Name`, or the assignment of the comprehension
> to that name is not a single-target `ast.Assign`, B1 binds nothing and the bridge widens. Two loops
> over one list can disagree about which element field is read, and picking one is §10.5 rule 1's
> "two views of one fact" case.
>
> **Measured expectation, to be reproduced and published:** in `LiquidHandler.aspirate`, the P8 match
> assigns to `aspirations` (`liquid_handler.py:1007`) with element class `SingleChannelAspiration`
> (`:1008`), and the single depth-0 `ast.For` over it binds `op` (`:1031`) — so `op : SingleChannelAspiration`.
> The fixer publishes the complete set of `(K, name, element_class, for_span)` tuples B1 binds over the
> whole contract table, not only `aspirate`'s.

> **Normative (B2 — dataclass field annotations, into a bridge-only map — round-1 O9).**
> A new pass `_dataclass_field_annotations` admits an `ast.AnnAssign` that is a **direct statement of
> the class body** (not inside any method) whose target is a bare `ast.Name`, recording
> `name → unwrapped annotation`. It is a **new function producing a new map**, consumed only by the
> volume bridge. It is **not** a branch inside `_annotated_attributes`
> (`plr-sema/src/plr_sema/derive/receiver_state.py:173-184`), and `_is_self_attr` (`:167-170`) is not
> changed.
>
> **Why a separate map, and not the "disjoint branch" the draft specified.** The draft argued that a
> disjoint *predicate* inside `_annotated_attributes` left every existing P1a selection "bit-for-bit
> unaffected". That inference is invalid: `_annotated_attributes` walks with `ast.walk` (breadth-first)
> and writes with `out.setdefault(...)` at `:183`, so first-writer-wins; a class-level `ast.AnnAssign`
> is a depth-1 child of the `ClassDef` and a method-body `self.x: T` is deeper, and on any name
> collision the new branch would be visited **first** and displace the existing selection. That map is
> the input to `derive_receiver_states`'s receiver-selection loop (`receiver_state.py:720`), whose
> alphabetical tie-break at `:724` is load-bearing (`"head" < "head96"`) and which `break`s on the
> first qualifying attribute at `:785`. **Nothing in the volume family needs that loop** — the bridge
> types `SingleChannelAspiration.resource` and `Container.tracker`, neither of which is a channel
> attribute of a receiver class. So the extended knowledge goes in its own map, `receiver_state.py:720`'s
> input is untouched, and AC-14.1(iii) becomes true **by construction — because
> `derive_receiver_states` does not call the new pass at all — and is measured anyway.**
>
> **Measured expectation:** `SingleChannelAspiration.resource → Container`, `.tip → Tip`,
> `.volume → float` (`external/pylabrobot/pylabrobot/liquid_handling/standard.py:53-56`), and the
> mirror for `SingleChannelDispense` (`:63-72`, whose `volume: float` is at `:68`).

> **Normative (P1c — constructor-call typing through an unannotated write, over every method —
> round-1 O2).** A new pass in `derive/receiver_state.py` which, for a class `C`, walks **every
> `ast.FunctionDef`/`ast.AsyncFunctionDef` child of the `ClassDef`** and, for every
> `self.<name> = <Callee>(...)` whose value is an `ast.Call` with an `ast.Name` func that is a key of
> the P1 class index, records `name → <Callee>` into the same bridge-only map B2 feeds.
>
> **It does not scan `__init__`, and it must not.** `Tip` is a `@dataclass` (`tip.py:11-12`) with no
> `__init__` at all; its tracker write is at `tip.py:45`, inside `__post_init__` (`:32`). Keying on
> `__init__` — or on `{__init__, __post_init__}` — is a bet on which method PLR writes trackers in, and
> PLR demonstrably writes them in two. `_constructor_state`
> (`plr-sema/src/plr_sema/derive/receiver_state.py:588-627`) remains the **architectural** precedent —
> it is what establishes that a derive pass may read `ast.Assign` (`:613`) alongside `ast.AnnAssign`
> (`:616`) inside a class body — but P1c explicitly does **not** inherit its `__init__` restriction,
> which is implemented as an `iter_child_nodes` scan for `member.name == "__init__"` returning `None`
> when none is found (`receiver_state.py:604-610`).
>
> **Fail-closed, now over the union of writes.** A name written more than once **anywhere in the
> class** with two different constructors, or written both by a constructor call and by something else,
> records nothing. The wider scan makes this rule *stronger*, not weaker: an `__init__`-only scan hides
> a contradicting write in another method and records a fact the all-methods scan would refuse. P1c is
> consulted **only after** B2: an annotated field always wins, so P1c can add knowledge and never
> overwrite it.
>
> **Measured expectation:** `Container.tracker → VolumeTracker`
> (`external/pylabrobot/pylabrobot/resources/container.py:85`) and `Tip.tracker → VolumeTracker`
> (`external/pylabrobot/pylabrobot/resources/tip.py:45`). At the pin there are exactly **three**
> `self.tracker = …` writes in the whole submodule — `container.py:85` (`Container.__init__`),
> `tip.py:45` (`Tip.__post_init__`) and `tip_rack.py:52` (`TipSpot.__init__`, a `TipTracker`) — in three
> different classes, one each, so no class trips the fail-closed clause. `Container.__init__` also calls
> `self.tracker.register_callback(...)` at `container.py:88`, which is a method call *on* the attribute
> and not a write, so the "written by something else" clause does not fire. The fixer publishes the
> complete P1c selection over the whole surface — this pass sees every unannotated constructor write in
> PLR, so its population is large and its *size* is the first thing a reviewer should be shown.

With B1, B2 and P1c, the two-hop resolution of `op.resource.tracker` is:
`op → SingleChannelAspiration` (B1) → `.resource → Container` (B2) → `.tracker → VolumeTracker` (P1c),
and `VolumeTracker` is P7-anchored (§14.4). The tip half resolves identically through
`.tip → Tip` → `.tracker → VolumeTracker`, and **after §14.6's R1 that half is the increment's entire
definite-verdict surface.** **That chain is the thing T24 must demonstrate, and demonstrating it is
AC-14.2, not an argument in this document.**

### 14.0.2 Task (b) — caller-scope threading, survey-side (round-1 O7, Q3 resolved)

G4 needs the caller's enclosing conjuncts attached to a guard that arrives through `dropped_calls`.
The draft weighed two options and chose derive-side on blast radius. **Round 1 inverted that decision,
and the reason is not cost — it is that §14.6's R1 needs a position key, and only the survey can
supply one.**

| option | what changes | cost | who else benefits |
|---|---|---|---|
| **survey-side (ADOPTED)** — `scripts/survey_plr_preconditions.py` records, per `dropped_calls` entry, its line number and enclosing scope trail | the survey artifact's schema; `plr_preconditions.json` is regenerated; `dropped_calls` stops being a `list[str]` | every consumer of the survey re-reads a changed shape; the artifact is an input to `plr_sema.derive` **and** to the differential harness | every future bridge, and the deferred-item-(e) worklist, which could then rank by scope |
| **derive-side (DECLINED)** — a new pass in `derive/receiver_state.py` re-parses the caller's own AST, locates the call expression matching the `dropped_calls` string, and accumulates its enclosing `ast.If`/`ast.For`/`ast.While` tests | one new pass in one module; no artifact change | the match is by *reconstructed expression text*, so R1 would have to test loop identity by text at the precise point soundness depends on it; and it re-implements `visit_If`/`visit_For`/`visit_While` semantics, including the `else`/`elif` polarity the survey already handles | only `plr_sema` |

**Three decisive facts, all verified against the tree.**

1. **The survey already maintains exactly this datum, at exactly the right place, and the change is
   three lines.** The dropped call is recorded inside `visit_Call` while `self._scope_trail` is live:
   `self.dropped.append(DroppedCall(expr=expr, lineno=node.lineno, scope_trail=list(self._scope_trail)))`
   at `scripts/survey_plr_preconditions.py:288` (landed as this box specified — T25, `5582ae08`),
   with `self.dropped: list[DroppedCall] = []` initialised at `:171`. `_record` already builds the
   same three-tuple shape for findings at `:148-160`.
2. **The survey's trail is polarity-aware; a derive-side P10 would not have been.** `visit_If` pushes
   `f"if {test_src}"` for the body at `:167` and `f"else of: if {test_src}"` for the `orelse` at `:177`,
   with the comment at `:171-176` explaining that an `elif` chain self-nests and compounds correctly.
   PLR writes the shape that makes this load-bearing: the 96-head dispense path has
   `tip.tracker.remove_liquid` under `if does_volume_tracking():` **and again** under its `elif`
   (`liquid_handler.py:1932-1935`), where the second call runs only when tracking is **off**. A
   polarity-blind trail records `"if does_volume_tracking()"` for that site, and the moment §14.6 can
   recognise that entry as satisfied, the analyzer emits an unblocked `WILL_FAIL` on a call that
   executes only when the hypothesis is false. At the pin this is masked by luck — two textual
   occurrences of the same expression — not by design.
3. **The `lineno` is what R1 needs.** §14.6's R1 recognises the `ast.For` **B1 bound over**, tested by
   `for_span[0] <= call_lineno <= for_span[1]`. Under the derive-side option the recognised entry would
   be a reconstructed string and the identity test a text match, which is exactly the key soundness
   must not rest on. §14.0.2's draft priced position containment as unaffordable; it is the enabling
   condition for the mechanism that rescues the increment.

> **Normative (the survey schema change).** `scripts/survey_plr_preconditions.py:250` records
> `(ast.unparse(target), node.lineno, list(self._scope_trail))`; `self.dropped` at `:142` becomes a
> `list` of those tuples rather than a `set[str]` (multiplicity is preserved, not reconstructed); and
> `FunctionPreconditions.dropped_calls` (`:120`) changes from `list[str]` to a list of
> `{expr, lineno, scope_trail}` records. `training/verify/data/plr_preconditions.json` is
> **regenerated** by the same command that produces it today, and the regeneration diff is published.
> The trail keeps the survey's own **nearest-first** convention, documented at `:85-87` and implemented
> by `insert(0, …)` at `:167`/`:187`; there is now exactly one ordering convention in the system.

> **Normative (P10, caller-scope threading — now a consumer).** For a bridged guard attached to
> contract entry `K` via a `dropped_calls` record `E`, P10 reads `E.scope_trail` and `E.lineno` and
> attaches them to the guard's payload as `caller_scope` and `caller_lineno`, additively, alongside its
> existing `scope_trail`, which is **not** modified — the callee's own trail and the caller's are
> different facts and are kept apart. `caller_scope` carries the survey's polarity verbatim: an entry
> beginning `else of: if …` is a **negated** enclosure and is never recognised as satisfied by §14.6,
> under any `env`.
>
> **Fail-closed.** A `dropped_calls` record lacking a `lineno` or a `scope_trail` — which is what every
> record produced before the schema change looks like — yields `caller_scope: null`, and §14.6's rule
> treats a `null` caller scope as **an unrecognised conjunct**, blocking `WILL_FAIL`. A pre-increment
> survey artifact therefore degrades to today's behaviour rather than to an ungated verdict.
>
> **P10 adds no pattern to the registry.** `visit_If`/`visit_For`/`visit_While` already exist, are
> already accounted for, and are not re-implemented; adding a `lineno` and an already-computed trail to
> an existing record is not a syntactic pattern over how PLR is written (§14.11).

**Four measured expectations, one per bridged guard — not one shared expectation (round-1 O1).**
Indentation is load-bearing here. The two guards of one method have **different** scopes, and at this
pin the difference lands exactly on the decidable/undecidable axis. Read directly from
`liquid_handler.py:1031-1035` and the dispense mirror at `:1231-1235`:

| # | site | expression | direction | decidable (§14.2)? | expected `caller_scope`, nearest-first | recognised under §14.6? |
|---|---|---|---|---|---|---|
| 1 | `liquid_handler.py:1034` | `op.resource.tracker.remove_liquid` | under-draw | **yes** | `["if not op.resource.tracker.is_disabled", "if does_volume_tracking()", "for op in aspirations"]` | **no** — the `is_disabled` entry is unrecognisable |
| 2 | `liquid_handler.py:1035` | `op.tip.tracker.add_liquid` | over-fill | no (capacity ⊤) | `["if does_volume_tracking()", "for op in aspirations"]` | yes — but the guard is ½ regardless |
| 3 | `liquid_handler.py:1234` | `op.resource.tracker.add_liquid` | over-fill | no (capacity ⊤) | `["if not op.resource.tracker.is_disabled", "if does_volume_tracking()", "for op in dispenses"]` | no |
| 4 | **`liquid_handler.py:1235`** | **`op.tip.tracker.remove_liquid`** | **under-draw** | **yes** | `["if does_volume_tracking()", "for op in dispenses"]` | **yes** |

**This table is the increment's own accounting of what §14.6 costs.** Exactly one of the four guards
is both decidable *and* outside the `is_disabled` test — `dispense`'s tip-side `remove_liquid` at
`liquid_handler.py:1235`. The fail-closed treatment of `is_disabled` costs the family **precisely one**
decidable guard (row 1) and blocks two (rows 2 and 3) that §14.2 already proves are permanently ½. So
the honest statement of A-TRACKER-ENABLED's precision cost is not "no definite verdict anywhere"; it is
**"no definite verdict on a well; a definite verdict on a tip survives"**, and that sentence is the
increment's headline deliverable.

The fixer publishes all four scopes as produced and **does not reconcile them to this table**; the
table is written by eye from the two cited ranges and is exactly the kind of expectation §13.2.4's own
discipline exists to make measurable.

---

## 14.1 Why the volume family is the derivable one, and the correction to the original dispatch

The dispatch that produced §13.2 described the volume guards as testing `_used_volume`/`_pending_volume`
against `max_volume`. **The field names are wrong and the correction matters**, because the anchor
derivation keys on them: `VolumeTracker.__init__` writes `self.volume` and `self.pending_volume`
(`external/pylabrobot/pylabrobot/resources/volume_tracker.py:49-50`), and the guards read them only
through two accessor **methods** — `get_used_volume` returning `self.pending_volume` (`:114-116`) and
`get_free_volume` returning `self.max_volume - self.get_used_volume()` (`:118-120`). There is no
`_used_volume` anywhere in the module. The raises are at `:92` (`TooLittleLiquidError` inside
`remove_liquid`, `:88-99`), `:105` (`TooLittleVolumeError` inside `add_liquid`, `:101-112`) and `:136`
(`TooLittleLiquidError` inside the deprecated `get_liquids`, `:122-138`).

Four facts, all in shipped artifacts, and **both round-1 challengers verified all four**:

1. **The guards are clean, depth-0 and already derived.** `plr-sema/data/derived_contracts.json`
   carries `"VolumeTracker.remove_liquid"` (`:158102-158133`) with a single depth-0 `raise_guard`,
   `condition: "volume - self.get_used_volume() > 1e-06"`, `raises: "TooLittleLiquidError"`, sited at
   `volume_tracker.py:92`; and `"VolumeTracker.add_liquid"` (`:157965-157996`) with
   `condition: "volume - self.get_free_volume() > 1e-06"`, `raises: "TooLittleVolumeError"`, sited at
   `:105`. Both carry `free_vars: ["self", "volume"]` — the condition mentions the method's own
   parameter, which is exactly the value a `CALL`'s kwarg supplies.
2. **The exception selector is the tip selector, verbatim in shape.** Both classes carry
   `"category": "volume_state"` and `"module": "pylabrobot.resources.errors"`
   (`training/verify/data/plr_exception_taxonomy.json:3011-3019` and `:3038-3046`). The unfiltered
   `category == "volume_state"` set has **four** members; the module conjunct narrows it to **two**,
   excluding `BlowOutVolumeError` (module `pylabrobot.liquid_handling.liquid_handler`, `:2964-2972`)
   and `LiquidLevelError` (a Hamilton backend class, `:2991-2999`). That is the same 5 → 2 narrowing
   §10.2.5 performs for tip state, against the same module path, so **no new hand-typed string enters
   `plr_sema`** — the module literal is the one AC-10.9 already declares.
3. **The bridge expressions are recorded — by the survey, and not yet matchable by the matcher.**
   `training/verify/data/plr_preconditions.json`'s `dropped_calls` carries
   `"op.resource.tracker.remove_liquid"` and `"op.tip.tracker.add_liquid"` for aspirate
   (`:49766-49772`) and the mirror pair for dispense (`:49863-49864`). They survive the inert filter.
   **§13.2.1 stated this fact as if it discharged the derivation; it does not** — §14.0's G1–G3 are the
   distance between "the survey wrote the string down" and "a rule matches it", and that distance is
   why this increment exists.
4. **`BlowOutVolumeError` is genuinely out of scope and the module conjunct is what puts it there.**
   Its two raises (`liquid_handler.py:1185` and `:1188`, inside the `does_volume_tracking()` block at
   `:1182-1188`) guard `self._blow_out_air_volume` against a requested blow-out volume — a
   `LiquidHandler` instance field, not a tracker cell, and therefore a different domain.

---

## 14.2 The two cell kinds, and the capacity problem

A volume cell is **a `VolumeTracker` instance**, and there are two kinds in the verdict path:

- **container cells** — `Container.__init__` sets
  `self.tracker = VolumeTracker(thing=..., max_volume=self.max_volume)` with
  `self.max_volume = max_volume or (size_x * size_y * size_z)`
  (`external/pylabrobot/pylabrobot/resources/container.py:84-85`). Wells, troughs, tubes.
- **tip cells** — `Tip.__post_init__` (`external/pylabrobot/pylabrobot/resources/tip.py:32`) sets
  `self.tracker = VolumeTracker(thing=thing, max_volume=self.maximal_volume)` (`tip.py:45`), with
  `maximal_volume: float` declared at `:27`. An aspirate moves liquid out of a container cell **and
  into a tip cell** in the same statement pair (`liquid_handler.py:1034-1035`).

Both writes are the unannotated `ast.Assign` shape §14.0.1's P1c exists to read, and **`Tip`'s is in
`__post_init__`, not `__init__` — which is precisely why P1c scans every method of a class.** (The
draft's §14.0.1 said `__init__` while this paragraph said `__post_init__`; round 1's O2 found the
contradiction and the `__init__` reading was the one that would have shipped. The two sections now
agree, on the all-methods form.)

> **Normative (the capacity asymmetry).** `max_volume` is **⊤ for every cell**. For a container it is
> a function of the labware's physical dimensions (`container.py:84`), and for a tip it is
> `Tip.maximal_volume` (`tip.py:27,45`); neither reaches the analyzer, because `RESOURCE`'s operands
> are `slot`/`type`/`element_type`/`is_container`/`is_parameter`/`parents`/`grid`
> (`plr-sema/src/plr_sema/check/ir.py:184-191`) and none of them is a capacity. Therefore:
>
> - the **under-draw** half — `remove_liquid`'s `volume - get_used_volume() > 1e-06`, raising
>   `TooLittleLiquidError` — is **decidable** from the interval alone, since `get_used_volume()`
>   returns `self.pending_volume` (`volume_tracker.py:114-116`) and nothing else;
> - the **over-fill** half — `add_liquid`'s `volume - get_free_volume() > 1e-06`, raising
>   `TooLittleVolumeError` — is **not decidable**, since `get_free_volume()` is
>   `self.max_volume - self.get_used_volume()` (`:118-120`) and `max_volume` is ⊤. It stays Kleene ½
>   and emits `volume_state_unknown`.
>
> A rule that guessed a capacity — a default well volume, a nominal tip volume — would construct a
> definite verdict from a number nobody measured, which is the failure §0 exists to prevent.

The half that would make over-fill decidable is a capacity operand on `RESOURCE`, which is a wire
change and an `IR_VERSION` bump. §14.15 keeps it deferred **and records increment 4's round-1
correction to the sequencing argument for taking it early**: `ir_version` is already a component of
§11.3.3's cache key (`plr-sema/src/plr_sema/check/ir.py:918-925`), so a later bump invalidates a
populated cache exactly as completely as an early one. There is no accumulating cost being avoided by
taking the bump before #4922 ships, and increment 4's §13.13 Q2 is resolved against the sequencing
framing on that basis.

---

## 14.3 The abstract state

```
Interval    ::=  [lo, hi]  with 0 <= lo <= hi <= +inf   |   TOP
VolumeState =  dict[cell: CellId, Interval]
CellId      =  ("container", slot: int, cell: str|null)  |  ("tip", channel: int)
```

`TOP` is `[0, +inf]` and the two are identified; the join is `[min(lo), max(hi)]`, which is the least
upper bound in the information order and gives a lattice of infinite height. **Infinite height is why
a widening operator is needed here and was not needed for tip state** (§10.1.1: "height 1 above its
two atoms … needs no widening operator"). The widening is §14.5's V4.

`CellId`'s container form reuses the `Ref(slot, cell)` pair the value grammar already produces
(§11.1.2), so a well reference in a kwarg *is* a cell id with no new resolution machinery. The tip form
keys on the channel index the tip family already computes (§10.1.3), which is the one place the two
families touch: **a tip cell exists only where the tip family says a channel has a tip.** If the
channel's `TipState` is not `HAS_TIP`, the tip cell is `TOP` — the analyzer does not know which tip is
mounted, so it cannot know its used volume.

**A channel index is not a tip identity, and round 1's O4 is the consequence.** `("tip", channel)`
names a slot in the head, not the `Tip` object mounted in it, and a `drop_tips` followed by a
`pick_up_tips` swaps the object while the key stays put. §14.5's V5 is the lifecycle rule that closes
that gap; it is a *soundness* rule, not a precision one, and it is on the increment's only
definite-verdict path.

---

## 14.4 The derived inputs

> **Normative (P7, the volume anchor).** A class `C` is **volume-anchored** iff it has ≥1
> zero-argument method whose body is a single `return <expr>` over `self.<F>` for some instance field
> `<F>` written in `C.__init__`, **and** ≥1 method whose body contains an `ast.Raise` of a class in
> the two-conjunct `volume_state` set (§14.1 fact 2) guarded by an `ast.Compare` mentioning one of
> those accessors and one of the method's own parameters. `C`'s **used-volume accessor** is the
> accessor named by the `TooLittleLiquidError` guard's comparison; its **free-volume accessor** is the
> one named by the `TooLittleVolumeError` guard's. Both are recorded by name; neither name is typed
> into `plr_sema`.
>
> **Fail-closed rule.** Zero anchors, or ≥2 candidate used-volume accessors, and P7 emits nothing for
> `C`; the volume family is disabled for every cell typing to `C`, and every verdict reverts to
> today's. The gap ledger records `volume_anchor: "absent"|"ambiguous"|{...}` per candidate class, the
> same visible-absence discipline §10.2.2 established for `tipstate_anchor`.
>
> **Measured expectation**, to be reproduced and published: `C = VolumeTracker`, used-volume accessor
> `get_used_volume`, free-volume accessor `get_free_volume`, field `pending_volume`.

> **Normative (the direction rule — round-1 O10).** The **direction** of a bridged method `C.m` is the
> sign of `m`'s `ast.AugAssign` on `C`'s P7-anchored field: `ast.Sub` is *used-volume-decreasing*,
> `ast.Add` is *used-volume-increasing*. A bridged method with **no** write to the anchored field, or
> with two writes of different signs, carries its **guard** but **no transfer**, and V2 applies no
> update for it.
>
> **Why this replaces "the `TooLittleLiquidError`-guarded method".** At the pin, `VolumeTracker` has
> **two** methods raising `TooLittleLiquidError` from an `ast.Compare` over `get_used_volume()` and one
> of the method's own parameters — `remove_liquid` (`volume_tracker.py:88-99`) and the deprecated
> `get_liquids` (`:122-138`, whose raise is at `:136`), and `"VolumeTracker.get_liquids"` is a real
> contract entry (`plr-sema/data/derived_contracts.json:158054`). P7 survives — both name the same
> accessor, so the "≥2 candidate used-volume accessors" clause does not fire — but a direction rule
> phrased in the singular has no tie-break, and classifying `get_liquids` as *decreasing* would move an
> interval on a pure read. The `AugAssign` sign classifies all three correctly and derives more, not
> less: `self.pending_volume -= volume` at `volume_tracker.py:96`, `self.pending_volume += volume` at
> `:109`, and no write at all in `get_liquids`. It also survives the deprecation removal that would
> otherwise change which method is "the" one.

> **Normative (P8, the operand-pairing idiom).** For a method `m` of receiver class `R`, match an
> `ast.ListComp` (or `GeneratorExp`) whose element is an `ast.Call` to a class `O` with keyword
> arguments, and whose single comprehension iterates `zip(a1, …, an)` where each `ai` is an
> `ast.Name`. Record, per keyword `k` of the element call whose value is a comprehension target bound
> at zip position `i`, the pair `(O.k → ai)`. When `ai` is a parameter of `m`, the binding is a
> **parameter pairing**; otherwise it is a **local pairing** and is recorded, marked as local, and
> resolved by V0's second clause (§14.5) rather than by a kwarg lookup.
> **P8 additionally records the comprehension's own assignment target**, which is what §14.0.1's B1
> binds a `for` loop against.
>
> **Measured expectation:** `LiquidHandler.aspirate`'s comprehension
> (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1007-1028`, element call at
> `:1008`, `zip` at `:1018-1027`) yields `SingleChannelAspiration.resource → resources` (`:1009`, zip
> position 0), `.volume → vols` (`:1010`, position 1) and `.tip → tips` (`:1014`, position 5 — a
> **local** pairing, since `tips` is the list built at `:974`, not a parameter), with assignment
> target `aspirations` (`:1007`).

> **Normative (the volume bridge, a second HM-24 pattern).** Match, against every `dropped_calls`
> record reached at **depth 0** in `K`'s own body, the shape
>
> ```
> <name>.<field>.<attr>.<method>          e.g.  op.resource.tracker.remove_liquid
> ```
>
> where `<name>` is bound either by a P8 comprehension target **or by §14.0.1's B1**, `<field>` is a
> keyword of the bound element class `O` typed by **the bridge-only map** B2 feeds, `<attr>` is sent by
> that same bridge-only map (B2's admission, or P1c's) to a P7-anchored class `C`, and
> `f"{C}.{method}"` is a key in the contract table. When it matches, attach every guard of `C.<method>`
> to `K` as a **volume guard** carrying the originating expression in `via`, the paired parameter name
> (or the local-pairing marker) in `cell_param`, the guard-parameter-to-`K`-parameter binding in
> `amount_param`, the derived direction, B1's `for_span` when the binding came through B1, and P10's
> `caller_scope`/`caller_lineno` (§14.0.2).
>
> `derived_contracts.json` gains one additive block per anchored class under `receiver_state` and one
> additive `volume_guards` list per contract entry, both read through `.get()` with an empty default
> so a pre-increment table degrades to today's behaviour. `schema_version` stays **1**.

**Measured expectation, to be reproduced and published:** `LiquidHandler.aspirate` acquires two volume
guards — `cell_param: "resources"`, `amount_param: "vols"`, direction *decreasing*,
`via: "op.resource.tracker.remove_liquid"`, raising `TooLittleLiquidError`; and
`cell_param: <the tip local>`, direction *increasing*, `via: "op.tip.tracker.add_liquid"`, raising
`TooLittleVolumeError`. `LiquidHandler.dispense` acquires the mirror pair
(`plr_preconditions.json:49863-49864`), of which `via: "op.tip.tracker.remove_liquid"` is the guard
this increment exists to decide. **This is the expectation increment 4's round 1 showed the §13.2.4
rule could not meet; AC-14.2 is what proves the extended rule does.**

---

## 14.5 Transfer functions and the interval arithmetic

For an operation `op` with a volume guard carrying `cell_param` and `amount_param`, let `amounts(op)`
be the `Value` of `op.kwargs[amount_param]`, and let `cells(op)` be resolved by V0.

> **Normative (V0, pairing).** Two clauses, tried in order, plus one conjunct.
>
> **(a) Parameter pairing.** If `cell_param` names a parameter of `K`, `cells(op)` is the `Value` of
> `op.kwargs[cell_param]`. If that is `Seq([c₁…cₙ])` with every `cᵢ` a `Ref`, and `amounts(op)` is
> `Seq([a₁…aₙ])` with every `aᵢ` a `Lit` of a JSON number, and the two lengths agree, then `op` pairs
> to the **ordered list** `[(cell(c₁), a₁), …, (cell(cₙ), aₙ)]`. A bare `Ref`/`Lit` pair is the
> length-1 case.
>
> **(b) Local pairing — the tip cells (round-1 D1).** When `cell_param` is P8's **local** pairing —
> a list built per channel rather than passed as a kwarg, e.g. `tips` at
> `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:974` — there is no kwarg to read
> and clause (a) cannot apply. The cell list is instead
> `[("tip", c) for c in channels_for_call(op)]`, taken in `use_channels` order so it threads in the
> same order V2 requires, using the channel binding
> `plr_sema.check.tipstate.channels_for_call` (`plr-sema/src/plr_sema/check/tipstate.py:245-247`)
> already computes and #4946 already extends. When that binding is `⊤` — `channels_for_call` returns
> `None` — V0 does not apply and V3 widens. **Without this clause V0 cannot produce a tip cell id at
> all**, and after §14.6 the tip cell carries the whole deliverable.
>
> **(c) The `use_channels` conjunct (round-1 D2).** When `op`'s `use_channels` lowers to a `Seq` of
> numeric `Lit`s, its length must agree with the pair list's too, else V3. PLR raises `ValueError`
> *before* the loop when any of `resources`/`vols`/`offsets`/`flow_rates`/`liquid_height`/
> `blow_out_air_volume` disagrees with `len(use_channels)` (`liquid_handler.py:989-992`), so a pair
> list of a different length describes iterations that never happen; the verdict would stay sound but
> the `plr_site` would be wrong and a tier-2b `(operation, iteration)` comparison would attribute a
> raise to the wrong site.
>
> **In every other case — either operand `Top`, a length mismatch, a `Seq` containing a `Top` or a
> non-numeric `Lit` — V0 does not apply and V3 does.** Clause (a) mirrors PLR's own zip
> (`liquid_handler.py:1018-1027`), which is why the length agreement is a *conjunct* and not a
> recovery. **`cells(op)` may contain the same `Ref` more than once and this is not an error** — see
> V2.
>
> **Normative (V1, evaluate then transition).** Guards are evaluated against the pre-state, then the
> post-state is computed — E1's ordering, unchanged. **"Pre-state" means the state at the pair's own
> position in V2's threading, not at the operation's entry.**
>
> **Normative (V2, exact transfer, threaded sequentially).** The pairs of V0's ordered list are applied
> **one at a time, in list order, to a running state**: pair `i`'s guard is evaluated against the state
> produced by pairs `1 … i-1`, and its own transfer is applied before pair `i+1` is evaluated. For a
> pair `(cell, a)` with running-state interval `[lo, hi]`: a **decreasing** guard (§14.4's direction
> rule) gives `[max(0, lo - a), max(0, hi - a)]`; an **increasing** one gives `[lo + a, hi + a]`; a
> guard with **no** direction carries its guard evaluation and leaves the interval unchanged. Cells
> outside `cells(op)` are unchanged, except as V5 requires.
>
> **Normative (V3, widen).** Every cell in `cells(op)` becomes `TOP` when V0 does not apply; **every
> cell of the whole state** becomes `TOP` when `op`'s method has a volume bridge only at depth > 0, or
> when two depth-0 volume bridges on the same cell disagree in direction — the E4.2/E4.3 discipline of
> §10.4, transposed.
>
> **Normative (V4, region widening).** On entry to a `LOOP` region whose `trip` is `null`, and on the
> `K`-th iteration of L1's bounded unroll (§12.3.3), **every** volume cell mentioned in the region
> becomes `TOP`. This is the widening operator the infinite-height lattice needs, and it is
> deliberately the crudest one: an interval that grows without bound across a fixpoint is exactly the
> non-termination case §12.3.3's finite-height argument did not have to handle, and jumping straight
> to `TOP` terminates in one step. Precision inside a **proved-trip** unroll is unaffected, because L1
> threads real iterations and only the tail widens.
>
> **Normative (V5, the tip-cell lifecycle — round-1 O4).** The walk carries one **monotone** boolean,
> `tips_dirty`, initially false. Then:
>
> - a `pick_up_tips` sets `("tip", c)` to `[0,0]` for every bound channel `c` **iff `tips_dirty` is
>   false**, and to `TOP` otherwise;
> - a `drop_tips`/`discard_tips` sets `("tip", c)` to `TOP` for every bound channel and, **iff the
>   departing cell's interval is not provably `[0,0]`** (`hi > 0`, or the cell is `TOP`), sets
>   `tips_dirty`;
> - any operation that moves tips without a modelled tip effect — a `move_resource`/`move_plate` over a
>   tip rack, a `stamp`, any 96-head operation, and any operation whose bound channels are `⊤` — sets
>   `tips_dirty` unconditionally.
>
> `tips_dirty` is never cleared. It is a walk-level fact, not a per-channel one, because the
> unmodelled movements it guards against are not channel-scoped.

**Why V5 is neither of the two simple rules.** *`TOP` on every `HAS_TIP` transition* is sound and
**destroys the family**: with the cell `TOP = [0, +inf]` at pickup, `aspirate(50)` gives `[50, +inf]`,
and `dispense(60)` evaluates `a - hi = 60 - inf` (not `T`) and `a - lo = 10 > 1e-06` (not `F`) — ½
forever, and the increment ships no `WILL_FAIL` after all. *`[0,0]` on every `HAS_TIP` transition* is
unsound, and the counterexample is legal PLR:

```
lh.pick_up_tips(tip_rack["A1"])                       # tip cell ch0 := [0,0]
await lh.aspirate([well_A], vols=[50])                # tip cell ch0 := [50,50]
await lh.drop_tips(tip_rack["A1"], allow_nonzero_volume=True)
lh.pick_up_tips(tip_rack["A2"])                       # a DIFFERENT Tip, fresh tracker
await lh.dispense([well_B], vols=[50])                # 50 - 50 = 0 <= 1e-06 → F → SAFE
```

The tip from `A2` is a distinct object with its own `VolumeTracker` (`tip.py:45`) whose
`pending_volume` is `initial_volume or 0` = 0 (`volume_tracker.py:49-50`), so `dispense` reaches
`op.tip.tracker.remove_liquid(op.volume)` at `liquid_handler.py:1235` with `50 - 0 > 1e-06` and
**raises**. `allow_nonzero_volume=True` is what makes the drop legal — PLR's own guard is
`if tip.tracker.get_used_volume() > 0 and not allow_nonzero_volume` (`liquid_handler.py:656-657`) — so
the program is valid and the shape is not contrived. Under V5: the drop sees `hi = 50 > 0`, sets
`tips_dirty`, the next pickup yields `TOP`, and the dispense is ½ `UNKNOWN`. Under an ordinary
protocol — pick up, aspirate 100, dispense 100, drop an empty tip, pick up again — the departing cell
is provably `[0,0]`, `tips_dirty` stays false, and precision survives arbitrarily many retips.

**Why V2 threads rather than snapshots (increment 4's round-1 O4).** PLR explicitly supports one well
being drawn by several channels in one call: when a single resource is passed with multiple channels,
`resources = [resource] * len(use_channels)`
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:997-999`). It then processes the
paired operations **sequentially** — `for op in aspirations:` at `:1031`, with
`op.resource.tracker.remove_liquid(op.volume)` at `:1034` mutating `pending_volume` synchronously
(`volume_tracker.py:96`) before the next iteration. So the second channel's guard is checked against
the volume the first channel already reduced. §13.2.5's V1 read as *simultaneous* — evaluate every
guard against one shared pre-operation snapshot, then transition — and against PLR's sequential order
that produces a **false `SAFE`**: a well seeded to 100 µL with `aspirate(resources=[well, well],
vols=[60, 60], use_channels=[0, 1])` gives both guards `60 - 100 ≤ 1e-06` under a snapshot reading,
while the real run raises `TooLittleLiquidError` on the second channel. AC-14.6 is that fixture — as a
**static** criterion against a synthetic contract table, because this round's O14 established that no
*executed* two-channel one-cell over-draw exists at this pin (the shape needs one cell touched twice
within one operation, which exists only on `aspirate`'s well, and that guard is blocked).

**Guard evaluation.** The two conditions are `volume - self.get_used_volume() > 1e-06` and
`volume - self.get_free_volume() > 1e-06`, where `volume` binds to the paired amount `a` and the
accessor reads the cell's running interval. With `used ∈ [lo, hi]`:

| guard | fires (`T`) iff | does not fire (`F`) iff | otherwise |
|---|---|---|---|
| under-draw (`remove_liquid`) | `a - hi > 1e-06` | `a - lo <= 1e-06` | `½` |
| over-fill (`add_liquid`) | never (capacity ⊤) | never | **always `½`** (§14.2) |

`T`/`F`/`½` then produce `WILL_FAIL`/`SAFE`/`UNKNOWN` through §10.3.3's existing table unchanged,
with `category = "precondition_state"` and, for `½`, `reason = "volume_state_unknown"`.

**The `1e-06` tolerance is read from the guard, not typed.** It is a literal in the derived
`condition` string (`plr-sema/data/derived_contracts.json:89595`) and is evaluated as part of the
`Cmp`; nothing in `plr_sema`'s source names it.

---

## 14.6 The hypothesis gate — fail-closed, with one structural exception

Every volume guard in `LiquidHandler` sits under conditions the analyzer must account for. In
`aspirate` they are a loop and two tests: `for op in aspirations:` at
`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1031`, `if does_volume_tracking():`
at `:1032`, and `if not op.resource.tracker.is_disabled:` at `:1033`, wrapping the tracker calls at
`:1034-1035`. Main spec §Open decisions 2 and increment 1 §10.9 both record that a definite volume
verdict therefore needs a `SoundnessScope` environment record, which does not exist.

**It is not needed, because the two verdict directions are not symmetric under such a condition:**

- If the condition is **false**, `remove_liquid` is never called from `aspirate` at all, so the site
  cannot raise. A `SAFE` finding for that guard — "this guard does not fire" — is therefore **true
  under both branches** and needs no hypothesis.
- A `WILL_FAIL` finding claims the site *does* raise, which is false when the condition is false. It
  needs the hypothesis.

> **Normative (the conditional-guard rule, generalised).** A volume guard is **conditional** iff its
> P10 `caller_scope` (§14.0.2) is `null`, **or** contains any entry the evaluator does not recognise as
> satisfied. A conditional guard may emit `SAFE` and `UNKNOWN` but **never `WILL_FAIL`**. A
> `T`-evaluating conditional guard emits `UNKNOWN` with reason `volume_tracking_unasserted`.
>
> **An entry is recognised as satisfied in exactly two ways, and no others:**
>
> 1. **By hypothesis.** It is a bare zero-argument call `f()` whose callee name is a member of `env`.
> 2. **By structure — R1, below.** It is the `ast.For` statement B1 bound `<name>` over for *this*
>    guard.
>
> **Everything else — any other `for` header, any `while`, any `async for`, an attribute test, a
> comparison, a `UnaryOp`, a call with arguments, an entry beginning `else of: if …`, an unparseable
> string — is unrecognised and blocks `WILL_FAIL`.** In particular `not op.resource.tracker.is_disabled`
> is unrecognised, because `VolumeTracker.is_disabled` is a `@property`
> (`external/pylabrobot/pylabrobot/resources/volume_tracker.py:54-56`) and the conjunct is an
> `ast.UnaryOp` over an `ast.Attribute` with no `ast.Call` in it at all. The generalised rule covers it
> by **not** recognising it, which is the fail-closed direction and needs no second mechanism.

> **Normative (R1, structural satisfaction of the B1-bound loop — round-1 O1).** A `caller_scope` entry
> is recognised as satisfied, **independently of `env`**, iff it is the very `ast.For` statement B1
> used to bind `<name>` for this guard, identified by **position containment**: the guard's B1
> `for_span` brackets the guard's own `caller_lineno`, i.e.
> `for_span[0] <= caller_lineno <= for_span[1]`, and the entry's ordinal in the nearest-first
> `caller_scope` is the outermost one that `for_span` covers. **The test is on positions, never on
> reconstructed text.** Every other `ast.For`, every `ast.While`, every `ast.AsyncFor`, and every
> `ast.For` whose target is a tuple (B1 already binds nothing there) stays unrecognised.
>
> **Three mechanical conjuncts make R1 sound, and none of them is an assumption.**
>
> 1. **The analyzer already models this loop.** §14.5's V2 applies the pairs of V0's list "one at a
>    time, in list order, to a running state" — that sentence *is* an unrolling of
>    `liquid_handler.py:1031`, and B1 binds `op` over that same statement. Recognising the header
>    asserts nothing V2 has not already computed. Refusing to recognise it means failing closed on the
>    one control-flow construct the analyzer is simultaneously claiming to simulate exactly.
> 2. **The trip count is pinned by PLR itself, not assumed.** Every zip input is normalised to
>    `len(use_channels)` — `offsets`/`flow_rates`/`liquid_height`/`blow_out_air_volume` at
>    `liquid_handler.py:962-965`, `tips` at `:974`, `resources` on the single-resource spread path at
>    `:999`, `mix` at `:1026` — and PLR then **raises `ValueError` at `:989-992`** if any of
>    `resources`, `vols`, `offsets`, `flow_rates`, `liquid_height` or `blow_out_air_volume` disagrees
>    with `len(use_channels)`. So on every path that reaches `:1031`,
>    `len(aspirations) == len(resources) == len(vols)`, which is the length V0 already requires of
>    `cells(op)`/`amounts(op)`. The loop cannot execute fewer times than the pair list has pairs. V0's
>    clause (c) makes the analyzer's own model match that guard.
> 3. **Fail-closed is preserved at the only point it could leak.** If V0 does not apply, V3 widens and
>    no definite verdict exists regardless, so R1 can never convert an unknown pairing into a definite
>    one. And R1 recognises a **node**, not a shape: a second `for` in the same method, or a `while`,
>    or any loop B1 did not bind over, remains unrecognised and blocks `WILL_FAIL`.
>
> **Contrast the other two entries — which is what shows R1 is a boundary and not a slope.**
> `if does_volume_tracking()` reads a module global (`volume_tracker.py:17-22`) the analyzer cannot
> see: a genuine hypothesis, and `env` is the right instrument. `if not op.resource.tracker.is_disabled`
> reads a per-instance flag (`volume_tracker.py:54-56`, a `@property` over `self._is_disabled`,
> initialised `False` at `:46` and set only by `disable()` at `:58-60`): that needs per-instance
> knowledge and stays fail-closed.

> **Normative (why `is_disabled` is not discharged — the two failed discharges, stated).** Both
> candidate discharges were examined and both fail, and this box records them so the question is not
> re-opened without new facts.
>
> - *A second `env` hypothesis.* `does_volume_tracking()` is a module-level zero-argument function
>   whose value is a single global; `is_disabled` is one flag per `VolumeTracker` instance, and a deck
>   carries one tracker per well plus one per tip (`container.py:85`, `tip.py:45`). There is no single
>   observation the harness can take that stands for "every tracker relevant to this guard was
>   enabled". A single `env` member would be a quantified claim dressed as an observation — the precise
>   failure §0 exists to prevent.
> - *"No `.disable()` / `no_volume_tracking` appears in the program under analysis."* Sound only if the
>   analyzed graph is the whole world. It is not: for a corpus row the graph is an extracted protocol,
>   and the deck construction that instantiates every tracker is code the analyzer never sees. A
>   tracker can arrive disabled from outside the graph. That is exactly A-TRACKER-ENABLED's "what
>   breaks if it is false" column, and adopting it would re-introduce the assumption the row forbids.

> **Normative (the env argument).** `check_ir` gains a keyword-only parameter
> `env: frozenset[str] = frozenset()`, and **`check_graph` gains the same keyword-only `env=`**, on the
> `cache=` precedent added by #4922 in that same signature
> (`plr-sema/src/plr_sema/check/__init__.py:714-719`). `env` defaults to empty and **`check_graph`'s
> two-positional-argument call form does not change**, so every existing test, every existing fixture
> and the whole tier-1 replay are unaffected by construction. `env` is **already** the fifth component
> of §11.3.3's cache key (`plr-sema/src/plr_sema/check/ir.py:918-925`); this increment threads a real
> value into it and adds nothing to the tuple (§14.14 item 6).

> **Normative (the harness asserts the hypothesis by observation, from inside the executed window —
> round-1 O5).** The draft had the harness call
> `pylabrobot.resources.volume_tracker.does_volume_tracking()` "after the verifier establishes its
> configuration". **There is no such window.** `training/verify/verifier.py` sets
> `set_volume_tracking(True)` at `:114` inside a `try` and restores the old value in the `finally` at
> `:151`; `training/tests/test_verify_postconditions.py:76-85` pins exactly that by asserting
> `does_volume_tracking() is False` after a run. In tier 3, `run_one_mutant` calls `run_runtime` at
> `plr-sema/eval/tip_mutants.py:178` and `run_static_calls` at `:188`; an observation taken between
> them returns `False`, `env` stays empty, and every volume guard is `volume_tracking_unasserted` for a
> reason that has nothing to do with the interval domain. Tier 2b behaves differently **by accident**:
> `region_oracle._run_fixture_execution` sets `set_volume_tracking(True)` at
> `plr-sema/eval/region_oracle.py:414` and its `finally` at `:436-437` restores strictness only, so the
> flag leaks and a later process-wide observation returns `True` — and the executed side really does run
> first (`_run_fixture_execution` at `:516`, `_static_report` at `:527`), so the leak *is* observable at
> the point the static side runs. That is a non-determinism in a value this document calls an observed
> fact, and it would silently partition `cache_key` (`plr-sema/src/plr_sema/check/ir.py:953`).
>
> **So the observation is never taken from outside the window.** The executed side **returns** it:
> `training/verify/verifier.py` gains one additive result key, set between `:114` and `:129` from a call
> to the imported `does_volume_tracking` callable, and `region_oracle._run_fixture_execution` gains the
> same inside its `try` (`plr-sema/eval/region_oracle.py:412-435`). The harness reads `env` from that
> field and passes `env = {"does_volume_tracking"}` iff it is true. **No string is typed into
> `plr_sema` or into the harness** — the name comes from the callable's `__name__` on one side and from
> the guard's own `caller_scope` on the other, which is why this costs no registry row.

**Consequence, stated plainly.** With R1 admitted and `is_disabled` fail-closed, §14.0.2's disposition
table decides the whole outcome: of the four bridged guards at this pin, `dispense`'s
`op.tip.tracker.remove_liquid` (`liquid_handler.py:1235`) has
`caller_scope = ["if does_volume_tracking()", "for op in dispenses"]` — the first entry recognised by
`env`, the second by R1 — and is **fully recognised**. A harness fixture — `pick_up_tips` →
`aspirate(vols=[50])` → `dispense(vols=[60])` — drives a static `WILL_FAIL` at
`PlrSite(volume_tracker.py, 92, "VolumeTracker.remove_liquid")` under `env = {"does_volume_tracking"}`,
and the execution raises `TooLittleLiquidError`. **The increment's headline deliverable is therefore
"a definite `WILL_FAIL` on a tip over-draw, and `SAFE`/`UNKNOWN` on every well"** — narrower than the
draft claimed, and *firable*, which is the premise §14.16's Q1 resolution rested on. **§14.16 Q1
remains RESOLVED by the user (260903, option (a): build it if it is firable at all);** round 1 did not
re-open it, it corrected a factual input to it, and the correction lands on the side that satisfies it.

Recognising a per-instance property test would require per-instance knowledge the analyzer does not
have; recognising it by *assuming* trackers are enabled is exactly what A-TRACKER-ENABLED's "what
breaks if it is false" column forbids. That is a precision cost of exactly one decidable guard
(§14.0.2, row 1), disclosed here rather than discovered at gate time.

---

## 14.7 The assumptions, named so a reviewer can attack them

| id | assumption | why it is needed | what breaks if it is false | oracle |
|---|---|---|---|---|
| **A-VOLUME-TRACKING** | when `"does_volume_tracking"` ∈ `env`, tracking was on for the whole walk | `WILL_FAIL` claims the guard was reached | a `WILL_FAIL` on a run that never evaluated the guard. `no_volume_tracking()` is a context manager (`volume_tracker.py:25-30`) the analyzer cannot see, exactly as §10.1.3's `use_channels` manager | tier 3's volume mutants (0 unsound gate) and tier 1's 0-unsound gate over 525 operations (`outputs/plr-sema/oracle_replay_260903_rebaseline.json:10-11`) |
| **A-TRACKER-ENABLED** | no cell's tracker was individually disabled | `liquid_handler.py:1033`'s `not …is_disabled` conjunct is unrecognised | **nothing for soundness** — an unrecognised conjunct blocks `WILL_FAIL` outright. Retained as a *precision* note: it is why the well guard at `liquid_handler.py:1034` never produces a definite verdict (§14.0.2, row 1) | §14.6's rule is asserted directly by AC-14.4 |
| **A-FOR-STRUCTURAL** (new, R1) | the B1-bound `ast.For` executes at least once per pair of V0's list | R1 recognises that header without `env` | a `WILL_FAIL` attributed to an iteration that never ran. Discharged **mechanically, not by argument**: PLR normalises every zip input to `len(use_channels)` and raises `ValueError` on disagreement (`liquid_handler.py:962-965,974,989-992,999,1026`), and V0's clause (c) makes the analyzer's own pair list match that check. What would break it is PLR dropping the length check while keeping the loop | AC-14.4's R1 sub-assertions and AC-14.10's executed rows |
| **A-SCOPE-POSITION** (new, replaces A-SCOPE-TEXT) | the survey's recorded `(lineno, scope_trail)` for a dropped call describes that call's real enclosing scopes, with polarity | R1 keys on position containment; §14.6 keys on trail entries | a `caller_scope` attached to the wrong call site, or an `orelse` enclosure read as an asserted one. Both are structural properties of `_BodyScanner`: the trail is pushed and popped around the visit (`scripts/survey_plr_preconditions.py:162-189`) and the `orelse` branch is pushed as `"else of: if …"` at `:177`. **The text-key risk the draft's A-SCOPE-TEXT tried to discharge no longer exists**, because nothing matches by reconstructed text any more | AC-14.3(iii)'s duplicate-expression fixture and AC-14.3(iv)'s `orelse` fixture |
| **A-NO-CORRECTION** | the volume PLR charges a cell is the literal the kwarg carries | V2 adds and subtracts the kwarg literal verbatim | an interval that drifts from the real one, in either direction, after the first corrected transfer. PLR's `vols` are `[float(v) for v in vols]` at `liquid_handler.py:968` — no liquid-class correction is applied on this path at the current pin | tier 1 + tier 3; a drift shows up as an unsound row, because the oracle compares against the executed raise |
| **A-COMMIT-VOLUME** | a committed transfer equals a pending one for the abstraction | V2 reads `get_used_volume()`, which returns `pending_volume` (`volume_tracker.py:114-116`), while `commit` copies it to `volume` (`:140-146`) and `rollback` restores it (`:148-151`) | an interval that reflects a rolled-back operation. `aspirate` commits or rolls back every touched tracker in one block (`liquid_handler.py:1058-1064`), which is A-COMMIT's own argument (§10.2.2) transposed to volume — and the rollback path only runs when the backend raised, which A-COMPLETES already scopes out | tier 3's volume mutants |
| **A-TIP-CELL** | a tip cell's interval is `TOP` unless the tip family says the channel is `HAS_TIP` | the tip cell's identity is the mounted tip | nothing in the `SAFE` direction: an unknown tip cell is `TOP` and every guard on it is ½ | AC-14.5(d)'s tip-cell assertion |
| **A-TIP-LIFECYCLE** (new, from V5) | a `pick_up_tips` taken while `tips_dirty` is false mounts a tip whose used volume is 0 | V5 seeds `[0,0]` rather than `TOP`, which is what keeps the family precise across retips | a false `SAFE` on a re-tipped channel — the round-1 O4 counterexample. Guarded by `tips_dirty`, which any drop of a not-provably-empty tip and any unmodelled tip movement sets, monotonically. What would break it is a *modelled* drop of a provably-empty tip that nonetheless leaves residue, which PLR's own `drop_tips` guard (`liquid_handler.py:656-657`) forbids without `allow_nonzero_volume` | AC-14.5(e)'s retip fixture and AC-14.10's executed retip row |
| **A-TIP-PAIRING** (new, from V0(b)) | for a local per-channel pairing, the cell list is `[("tip", c) for c in channels_for_call(op)]` in `use_channels` order | the tip guard has no kwarg to read | a tip transfer applied to the wrong channel. `channels_for_call` (`plr-sema/src/plr_sema/check/tipstate.py:245-247`) is the binding the tip family already trusts for exactly this question, and it returns `None` (⊤) rather than guessing, which routes to V3 | AC-14.5(a)'s per-channel siting and AC-14.10's executed rows |

---

## 14.8 Seeding, and why it reuses increment 3's scaffolding precedent

An executed corpus row starts with wells that already contain liquid. The harness computes those
seeds itself — `_precondition_plan` returns a `seed_volumes` dict (`plr-sema/eval/oracle_common.py:888-894`;
the aspirate branch builds `dict(zip(sources, vols))` at `:755-762`) and `row_to_verifier_inputs` puts
it in `deck_layout` at `:983-989`. **That dict is a harness artifact and is not in the extractor's
graph**, so a `check_graph` on real extracted source sees no seeds and every cell is `TOP` at entry.
That is correct and is not a defect.

For the *oracle*, the two sides must describe one execution, which is §12.1.6's argument for lowering
the scaffolding `setup()` call. The same remedy applies:

> **Normative.** For each `(cell, volume)` in the row's `deck_layout.seed_volumes`, the caller in
> `plr-sema/eval/` prepends a `CALL` to the derived volume-setting method — `VolumeTracker.set_volume`
> at the current pin (`external/pylabrobot/pylabrobot/resources/volume_tracker.py:66-72`, which writes
> both `volume` and `pending_volume`) — **before** the scaffolding reset, with `origin` the string
> `"seed"`. The method is selected by P7's own accessor pass (a method assigning the anchored field
> from a parameter, unconditionally, at statement position), not named in our source. It is emitted
> **by the caller**, not synthesised inside `lower_calls`, which stays a pure function of its input
> sequence.
>
> **The exact wire shape, since round 1 showed the draft's "with the cell as receiver" was under-specified
> (O8).** The prepended call is
> `{"receiver": <the resource variable's own name, exactly as the protocol's `Ref` spells it>,
> "receiver_type": "VolumeTracker", "method": "set_volume", "kwargs": {"volume": <Lit>}}`.
> `lower_calls` accepts per-call `receiver`/`receiver_type` overrides
> (`plr-sema/src/plr_sema/check/ir.py:794-795`), `Call.receiver` is an `int`
> (`plr-sema/src/plr_sema/check/ir.py:201`) minted by `get_slot` in first-appearance order
> (`:784-787`, assigned at `:818`), so **slot identity between the seed and the protocol's own `Ref`
> follows from name identity** — which is the property §14.3 relies on when it says the cell id
> "reuses the `Ref(slot, cell)` pair". When the protocol addresses a well as `plate["A1"]` rather than
> by its own name, the cell id is the `("container", slot, cell)` form and the seed's receiver is the
> plate's name with the same `cell` component.
>
> **The cell must not be passed as a kwarg.** `set_volume`'s trusted params are `["self", "volume"]`
> (`plr-sema/data/derived_contracts.json:158193-158196`), so a synthetic cell kwarg falls into the
> untrusted branch (`plr-sema/src/plr_sema/check/ir.py:806-812`), is renamed `?j`, and emits
> `Widen(_ARGUMENTS)`.

**Two corrections round 1 made to this section's own claims.**

- **`VolumeTracker` is not `unsupported_tool`.** That would have been true before 260901 T11 and is
  false now: `plr-sema/src/plr_sema/check/_supported_tools.py:5-21` states in terms that the set is
  "**No longer the analyzed-surface boundary**" and that `unsupported_tool` now means "key absent from
  that whole-survey contract table"; `plr-sema/src/plr_sema/check/__init__.py:363-366` implements
  exactly one contract-table lookup with no membership test. `"VolumeTracker.set_volume"` **is** a key
  in the shipped table (`plr-sema/data/derived_contracts.json:158185-158197`).
- **The seed `CALL` does contribute one finding of its own, and it is not the fallback.**
  `VolumeTracker.set_volume` carries a real gap in the shipped table —
  `"gaps": [["unresolved_delegate", "_callback"]]` (`plr-sema/data/derived_contracts.json:158317-158329`,
  from `self._callback()` at `volume_tracker.py:71-72`) with `"guards": []` — and `_evaluate_call`
  emits one `_findings_for_gap` finding per gap (`plr-sema/src/plr_sema/check/__init__.py:398-406`), so
  the seed never reaches the zero-guards/zero-gaps fallback at `:383-392`. `origin` relabels finding
  op-ids and suppresses nothing. AC-14.5(a) is written against that fact rather than around it.

**This is why no `IR_VERSION` bump is needed for seeding.** A prepended `CALL` reuses an opcode, a
lowering path and an `origin` convention that all shipped in increment 3 and are pinned by AC-12.3.
It does extend the precedent in one respect the draft did not name: increment 3's prepended `setup()`
has receiver type `LiquidHandler`, and this one does not. After T11 that is a benign new fact, not a
surface extension.

---

## 14.9 The oracle: one mutant class and a fixture set

**Tier 3 (mutants).** `plr-sema/eval/tip_mutants.py`'s pattern generalises exactly, and the reason it
generalises is a property of the existing code that must be stated because the whole construction
depends on it: `row_to_verifier_inputs` is called on the **base** row and its `deck_layout` — seeds
included — is carried into the mutant unchanged (`plr-sema/eval/tip_mutants.py:238-247`, where
`example` is built from the base row's three outputs and the mutators at `:167` then edit only
`example["call_sequence"]`). So a mutant that *raises* a volume over-draws against a state computed
from the **unmutated** call, and genuinely raises. Had the state been recomputed from the mutant, the
mutation would be self-cancelling and the class would measure nothing — the same trap
`_shift_tip_ref`'s docstring records for m2 (`tip_mutants.py:127-140`).

> **Normative.** **One** class, in a new `plr-sema/eval/volume_mutants.py`:
> **v1 (`v1_overdraw_dispense`)** multiplies the last `dispense`'s `volume_ul` so it exceeds what the
> mounted tip holds after the row's own preceding `aspirate`; expected exception
> `TooLittleLiquidError`, raised at `op.tip.tracker.remove_liquid` (`liquid_handler.py:1235`).
> It reuses `run_one_mutant`'s shape (`tip_mutants.py:170-224`), which is refactored to take the
> mutator and the expected exception as arguments rather than reading the module globals `_MUTATORS`
> (`:167`) and `_EXPECTED_EXC` (`:69`). **The refactor must not move the m1/m2 numbers**, and AC-14.9
> gates that as a non-regression.
>
> **The class is sited on `dispense`, not on `aspirate`, and that is forced by §14.0.2's table.** An
> aspirate over-draw hits the *well* guard at `liquid_handler.py:1034`, which is permanently
> conditional, so its static side would be `UNKNOWN` for every row and the class would measure the
> spec's own scope decision rather than the implementation.
>
> **No over-fill mutant class is specified**, because §14.2 makes an over-fill `WILL_FAIL`
> unreachable; a class whose gate can only ever be `0 of n` measures the spec's own scope decision
> rather than the implementation.
>
> **The draft's second class, `v2_overdraw_transfer`, is WITHDRAWN (round-1 O11).**
> `LiquidHandler.transfer` (`liquid_handler.py:1273-1361`) contains no `ast.ListComp`/`GeneratorExp`
> over a `zip` of names, so P8 does not match; no `for` over a comprehension's output, so B1 binds
> nothing; and no four-segment `<name>.<field>.<attr>.<method>` call, so the volume bridge never fires.
> It reaches the trackers only through `await self.aspirate(...)` at `:1347` and
> `await self.dispense(...)` at `:1355`, and what it passes is computed — `vols=[sum(target_vols)]` at
> `:1349` over `target_vols = [source_vol * r / sum(ratios) for r in ratios]` at `:1345` — none of
> which is a `Seq` of numeric `Lit`s, so V0 does not apply and V3 widens. Nothing in §14.0, §14.4 or
> §14.5 specifies volume-guard propagation through `delegates_to`; #4946's
> `delegate_channel_binding.transfer.{aspirate,dispense}`
> (`plr-sema/data/derived_contracts.json:168096-168113`) is a **channel** binding and a different
> mechanism. So v2's static side is `UNKNOWN` by construction, its gate can only ever be `0 of n`, and
> the argument this section already makes for declining the over-fill class applies to it verbatim.

**Tier 2b (executed fixtures).** The region fixture set (`plr-sema/eval/fixtures/regions/`, 11 fixtures
at `outputs/plr-sema/tier2b_260903.json:7`) gains **four tip-cell volume fixtures**: a straight-line
tip over-draw, a tip over-draw at the second iteration of a proved-trip loop, a loop whose per-iteration
dispense is safe individually and exhausts the tip collectively, and **a retip fixture** (§14.5's V5).
The two-channel/one-well fixture the draft named is **not** in this set: the shape needs one cell
touched twice within one operation, which at this pin exists only on `aspirate`'s well, whose guard is
permanently conditional — a `dispense`'s two channels touch two *distinct* tip cells. AC-14.6 keeps
that case as a **static** criterion against a synthetic contract table. The existing
`region_unsound = 0` and `region_will_fail_fired = 3` (`tier2b_260903.json:8-9`) become the floor, not
the target.

---

## 14.10 Soundness claims and the oracle that checks each

| claim | § | oracle |
|---|---|---|
| the bridge actually matches on real PLR at the pin | 14.0.1, 14.4 | AC-14.2 — the published `volume_guards` block for `aspirate`/`dispense`. **This is the claim increment 4's round 1 falsified about §13.2 and is the reason this increment exists** |
| B2 and P1c disturb no existing receiver selection | 14.0.1 | AC-14.1(iii) — true by construction (a separate map) *and* asserted on `LiquidHandler.head → TipTracker` |
| the caller's conjuncts, with polarity and position, reach the bridged guard | 14.0.2 | AC-14.3 — four scopes published, plus the duplicate-expression and `orelse` fixtures |
| an unrecognised conjunct cannot produce `WILL_FAIL`, and R1 recognises exactly one loop | 14.6 | AC-14.4, asserted over `is_disabled`, a non-B1 `for` header, an `else of: if …` entry and a `null` caller scope |
| a paired under-draw guard evaluating `T` really raises | 14.5 | tier 3's v1 mutants (0 unsound) and tier 1's 0-unsound gate over 525 operations |
| a re-tipped channel is not credited with the departed tip's contents | 14.5 V5 | AC-14.5(e) statically and AC-14.10's executed retip row — the round-1 O4 false `SAFE` |
| the tip guard's local pairing resolves to real channel cells | 14.5 V0(b) | AC-14.5(a)'s per-channel siting — round-1 D1 |
| **two channels drawing one well are checked sequentially, not simultaneously** | 14.5 V2 | AC-14.6, **static only**, against a synthetic contract table; the executed half is withdrawn because `region_oracle._verdict_at` joins on `(operation, iteration)` (`plr-sema/eval/region_oracle.py:344-351`) and has no pair dimension to discriminate on |
| the over-fill half is genuinely undecidable and is not quietly guessed | 14.2 | AC-14.5(d)'s assertion that an `add_liquid`-derived guard yields `volume_state_unknown` for every fixture |
| V4's `TOP` widening terminates the fixpoint on an infinite-height lattice | 14.5 | AC-14.5's `while`-loop volume fixture |
| A-VOLUME-TRACKING, A-TRACKER-ENABLED, A-FOR-STRUCTURAL, A-SCOPE-POSITION, A-NO-CORRECTION, A-COMMIT-VOLUME, A-TIP-CELL, A-TIP-LIFECYCLE, A-TIP-PAIRING | 14.7 | the per-row entries in that table |
| the volume exception set is `{TooLittleLiquidError, TooLittleVolumeError}` and is derived | 14.1 | AC-14.2(ii): 4 members unfiltered, 2 after the module conjunct, plus an AST literal scan |

---

## 14.11 Hand-maintained impact

**New registry rows: zero. Retired registry rows: zero.** `live_rows()` is 24
(`plr-sema/src/plr_sema/_hand_maintained.py:867-871`) against `BUDGET_CAP = 24` (`:43`).
**Headroom 0, before and after.**

**Two per-row ceilings move, both loud one-line diffs and neither a row addition:**

| row | on entry to this increment | after | what the new patterns are |
|---|---|---|---|
| **HM-24** (`_hand_maintained.py:788-822`, `metric="patterns"`/`declared=1`/`status="CAPPED"` at `:801-803`) | live 1, declared 1 | **live 3, declared 3** | (a) the volume bridge shape `<name>.<field>.<attr>.<method>` (§14.4) and (b) **B1**'s `for`-over-a-comprehension's-output shape (§14.0.1). `_measure_hm24` (`_hand_maintained.py:244-261`) returns 3, and each new pattern is asserted the way the existing one is — the tip regex's `_BRIDGE_SHAPE_RE.groups == 3` assertion at `:257-260` is unchanged, the volume regex gets its own, and B1's gets a structural assertion on its own matcher |
| **HM-25** (`_hand_maintained.py:823-863`, the same three fields at `:841-843`) | live 6, declared 6 **after increment 4's P9 bump** | **live 8, declared 8** | P7's accessor-anchor shape and P8's zip-comprehension pairing idiom (§14.4) |

**Why B1 is on HM-24 and not HM-25 (round-1 O12 — the count was conceded, the instrument was not).**
The draft argued that B1 and P10 "match a *binding*, resolved by Python's own scoping rules, not a
recognisable idiom", and that argument is **withdrawn**: B1 does not resolve bindings, it matches a
shape (single-`Name` `For` target, bare-`Name` `iter`, single-target `Assign`, depth 0), and
`for i, op in enumerate(aspirations):` is idiomatic Python PLR could adopt tomorrow, at which point
B1's own fail-closed clause would silently disable the family. Under R1 (§14.6) B1's `ast.For` node is
load-bearing for *soundness*, not only precision, which makes the point sharper still.

**The right instrument is the registry's own silent-versus-loud criterion, which already exists.** The
260902 Q7 split is explicit: HM-24 is the pattern "whose failure mode is a SILENT family collapse
rather than a loud exact-count test failure" (`_hand_maintained.py:796-799`, with `breaks_when` at
`:810-820`: "Fails CLOSED … the tip-requiring/tip-loading families silently empty … it cannot produce
a wrong verdict, only fewer of them"), while HM-25's `breaks_when` says "Fails LOUDLY here (unlike
HM-24)" (`:857-861`). B1's failure mode is a silent family collapse. So the arithmetic is **HM-24
1 → 3, HM-25 6 → 8** — eleven patterns over two rows, no row addition, no cap conversation, and §14.16
Q2's own instinct (a split rather than a ceiling bump) satisfied by a split that already exists.

- **B2 and P1c are not counted, and now that argument is true.** `self.x: T` as a class-body field
  annotation and `self.x = C()` are Python language constructs, not PLR idioms. The challenger's
  objection was that this holds only for P1c's *all-methods* form — keying on `__init__` is a bet on
  which method PLR writes trackers in, and PLR writes them in two — and §14.0.1's P1c is now the
  all-methods form, which is the form this argument was already written for.
- **P10 is off the registry entirely**, under Q3's survey-side resolution. `visit_If`/`visit_For`/
  `visit_While` already exist and are already accounted for; adding a `lineno` and an
  already-computed trail to an existing record adds no syntactic pattern over how PLR is written. A
  derive-side P10 *would* have added one, with a silent failure mode, to a registry at zero headroom.

**`REASON_VOCABULARY` (HM-14): 8 → 10 of cap 12** (`plr-sema/src/plr_sema/verdict.py:129-154`; the row
is `CAPPED` at declared 12, `_hand_maintained.py:650-654`, so live 10 ≤ 12 and **no `declared` edit is
needed**). `volume_state_unknown` (the cell's interval, or the capacity, is `TOP`) and
`volume_tracking_unasserted` (the atom evaluated `T` but the guard is conditional, §14.6). Neither
member is added by increment 4 — increment 4's round-1 Q6 observed that shipping a vocabulary member
whose producer does not work is the same "dead data" problem §13.7 raises for `lid_state_unknown`, and
the user's decision holds `REASON_VOCABULARY` at 8 until this increment lands. **Both members now have
working producers under §14.6** (§14.16 Q4).

**What could have been hand-typed, and what it is instead:**

| what could have been typed | what it is instead |
|---|---|
| `{"TooLittleLiquidError", "TooLittleVolumeError"}` as a class-name list | the two-conjunct taxonomy filter (§14.1 fact 2), reusing the module literal AC-10.9 already declares. 4 members → 2 |
| `"get_used_volume"` / `"get_free_volume"` / `"pending_volume"` as accessor names | P7 reads them off the guards' own `ast.Compare` operands (§14.4) |
| a per-method map from resource parameter to volume parameter (`aspirate → (resources, vols)`) | P8's zip-comprehension pairing over `liquid_handler.py:1007-1028` |
| `"op"`, or a map from method to loop-variable name | B1 matches the `for`-over-`Name` shape and reads the target (§14.0.1) — **counted, as HM-24 pattern (b)** |
| which bridged method decreases and which increases the cell | the sign of the `ast.AugAssign` on the P7-anchored field (§14.4's direction rule) — `-=` at `volume_tracker.py:96`, `+=` at `:109`, and no write at all in `get_liquids` |
| `"tracker"`, or `Container.tracker → VolumeTracker` as a fact | P1c reads the constructor call over every method of the class (§14.0.1) |
| `"does_volume_tracking"` as an environment key | the harness **calls** the imported callable and reads its `__name__` (§14.6) |
| a list of "conjuncts that are safe to ignore" | §14.6 recognises exactly two shapes — a zero-argument call in `env`, and R1's B1-bound node by position — and fails closed on everything else |
| a default well capacity or nominal tip volume | **nothing.** The over-fill half stays ½ (§14.2) |

**Wire format: no `plr_sema` change; one survey-artifact schema change.** `volume_guards`, the
per-class volume block, `caller_scope`/`caller_lineno` and `for_span` are new optional keys read
through `.get()`; `env` is a keyword-only parameter with a default that reproduces today's behaviour;
`IR_VERSION` stays **2** and `derived_contracts.json`'s `schema_version` stays **1**. **What does
change is the survey artifact**: `dropped_calls` stops being a `list[str]` and
`training/verify/data/plr_preconditions.json` is regenerated (§14.0.2, §14.14 item 8). That is a
cross-package event and is stated as one rather than folded into the "no change" claim.

---

## 14.12 Acceptance criteria

- **AC-14.1 (the three bridge sub-boxes derive, and the widening disturbs nothing).** Four
  sub-assertions, each published as a measured set. (i) **B1** binds
  `op : SingleChannelAspiration` in `LiquidHandler.aspirate` via the comprehension assigned to
  `aspirations` (`liquid_handler.py:1007,1031`), with a `for_span` bracketing both `:1034` and `:1035`;
  the complete set of `(K, name, element_class, for_span)` tuples is published and has **≥ 2** entries
  (`aspirate` and `dispense`); and a two-`for`-loops-over-one-list fixture binds **nothing**. (ii)
  **B2** yields `SingleChannelAspiration.resource → Container`, `.tip → Tip`, `.volume → float`
  (`external/pylabrobot/pylabrobot/liquid_handling/standard.py:53-56`) and the `SingleChannelDispense`
  mirror (`:63-72`); the complete selection is published and contains **≥ 8** attributes over **≥ 2**
  classes. (iii) **B2 and P1c disturb no existing selection**: `derive_receiver_states` does not call
  either pass — asserted directly, by a test that the receiver-selection input at
  `plr-sema/src/plr_sema/derive/receiver_state.py:720` is `_annotated_attributes`' result and nothing
  else — *and* `receiver_state["LiquidHandler"]["channel_attr"]` is still `"head"` with tracker class
  `TipTracker` and the shipped `derived_contracts.json`'s `receiver_state` block is **byte-identical**
  except for the additive volume keys. (iv) **P1c** yields `Container.tracker → VolumeTracker`
  (`container.py:85`) and `Tip.tracker → VolumeTracker` (`tip.py:45`, written in `__post_init__` at
  `tip.py:32`), with the whole-surface selection published at **≥ 3** entries, and a
  two-different-constructors-in-two-different-methods fixture records **nothing** — the stub-defeating
  half, since an `__init__`-only pass passes the `Container` half and fails both the `Tip` half and
  this one.
- **AC-14.2 (the bridge matches on the real pin).**
  `contracts["LiquidHandler.aspirate"]["volume_guards"]` contains exactly two entries: one raising
  `TooLittleLiquidError` with `via == "op.resource.tracker.remove_liquid"`, `cell_param ==
  "resources"`, `amount_param == "vols"`, direction *decreasing*; one raising `TooLittleVolumeError`
  with `via == "op.tip.tracker.add_liquid"`, a local `cell_param` and direction *increasing*.
  `LiquidHandler.dispense` carries the mirror pair, including
  `via == "op.tip.tracker.remove_liquid"` with direction *decreasing* — the guard this increment
  exists to decide. Three further sub-assertions: (ii) the unfiltered taxonomy set
  `category == "volume_state"` has **4** members and the module conjunct selects exactly
  `{TooLittleLiquidError, TooLittleVolumeError}`, asserted against
  `training/verify/data/plr_exception_taxonomy.json`; (iii) an AST literal scan **of
  `plr_sema/derive/receiver_state.py` and the new `plr_sema/check/volumestate.py`** finds no
  `ast.Constant` string equal to `"get_used_volume"`, `"get_free_volume"`, `"pending_volume"`,
  `"tracker"`, `"op"`, `"TooLittleLiquidError"`, `"TooLittleVolumeError"`, `"resources"` or `"vols"` —
  module-scoped exactly as the shipped precedent is
  (`plr-sema/src/plr_sema/derive/receiver_state.py:298-307`, whose docstring already forbids
  `"use_channels"` "anywhere in this module or `plr_sema.check.tipstate`"), because the draft's
  whole-`src/` scope is **red on an unmodified tree**: `"op"` is the IR's opcode tag
  (`plr-sema/src/plr_sema/check/ir.py:860-887`) and `"resources"` is the graph payload's own key
  (`plr-sema/src/plr_sema/check/ir.py:320`, `:446`, `plr-sema/src/plr_sema/check/graph.py:193`); (iv)
  the narrowed scan is asserted to still forbid all three of `"tracker"`, `"op"` and `"resources"` in
  the two scanned modules, so the gate keeps its content.
- **AC-14.3 (caller scope reaches the bridged guard, with polarity and position).** All **four**
  bridged guards of `aspirate`/`dispense` carry a non-null `caller_scope`, published verbatim as
  produced, each of length **≥ 2**, and the two guards under the `is_disabled` test —
  `liquid_handler.py:1034` and `:1234` — carry an entry the other two do not, asserted as a set
  difference and not by eye. Three
  further sub-assertions: (ii) each guard's own `scope_trail` is **unchanged** from the callee's
  contract — `["if volume - self.get_used_volume() > 1e-06"]` — so the two facts are kept apart, and
  both use the survey's nearest-first convention; (iii) a fixture whose method body contains the same
  dotted call expression twice under different `if` scopes yields **two** `dropped_calls` records with
  **different** `lineno`s and **different** `scope_trail`s — multiplicity preserved, not collapsed;
  (iv) a fixture whose call sits in an `orelse` records an entry beginning `"else of: if "`, and that
  entry is **not** recognised as satisfied even when its test text is a member of `env`. (iv) is the
  stub-defeating half.
- **AC-14.4 (fail-closed on anything unrecognised; R1 recognises exactly one node).** With
  `env == {"does_volume_tracking"}`: a guard whose `caller_scope` is
  `["if does_volume_tracking()", "for op in dispenses"]` **with a `for_span` containing its
  `caller_lineno`** may emit `WILL_FAIL`; the same guard emits `UNKNOWN` with reason
  `volume_tracking_unasserted` under each of six perturbations, one fixture apiece — an added
  `is_disabled` attribute test; a second `for` header whose span does **not** contain the
  `caller_lineno`; the same `for` entry with `for_span` absent; a `while` header; an
  `"else of: if does_volume_tracking()"` entry; and `caller_scope: null`. The `null` case and the
  span-absent case are the stub-defeating halves: an implementation that treated a missing scope as an
  empty one, or that recognised `for` headers by text, passes the others and fails these.
- **AC-14.5 (the interval domain decides the tip half and provably declines the rest).** Five
  fixtures, each with a prepended seed `CALL` (§14.8). (a) **the headline**: `pick_up_tips` on channel
  0, well seeded to 100, `aspirate(vols=[50])`, `dispense(vols=[60])` → **exactly one finding whose
  `verdict is Verdict.WILL_FAIL`**, with `category == "precondition_state"` and
  `plr_site == PlrSite("external/pylabrobot/pylabrobot/resources/volume_tracker.py", 92,
  "VolumeTracker.remove_liquid")`, sited on the tip cell of channel 0 (V0(b)); the report also contains
  the seed `CALL`'s own `unresolved_delegate` finding (§14.8) and the well-side
  `volume_state_unknown`, and asserting *exactly one `WILL_FAIL`* rather than *exactly one finding* is
  deliberate. (b) the same graph with `dispense(vols=[40])` → a `Verdict.SAFE` finding at the same
  site; and the well's own `aspirate` guard yields `Verdict.SAFE` too, which is the well half this
  increment does ship. (c) the same graph with `vols` lowering to `Top` → `Verdict.UNKNOWN` with reason
  `volume_state_unknown`. (d) **the declining half**: `dispense(vols=[10_000])` into a seeded well
  yields `Verdict.UNKNOWN` with reason `volume_state_unknown` at the `add_liquid` site — never
  `WILL_FAIL` — because the capacity is `TOP`; and a tip cell on a channel whose `TipState` is not
  `HAS_TIP` likewise yields `volume_state_unknown` (A-TIP-CELL). (e) **the retip half (V5)**:
  `pick_up_tips` / `aspirate(50)` / `drop_tips(allow_nonzero_volume=True)` / `pick_up_tips` /
  `dispense(50)` yields `Verdict.UNKNOWN` with reason `volume_state_unknown` — **not** `SAFE` — and
  `tips_dirty` is asserted true after the drop; the same sequence with the drop taken at a provably
  empty tip leaves `tips_dirty` false and yields `Verdict.SAFE`. A sixth fixture, a `while` loop whose
  body dispenses a literal volume, asserts `check_ir` converges within `K` passes, does not raise, and
  leaves every cell in the region `TOP` after the region's `END` (V4). (d) and (e) are the
  stub-defeating halves.
- **AC-14.6 (V2 threads sequentially — static only).** Against a **synthetic** contract table whose
  bridged guard carries `caller_scope == ["if does_volume_tracking()", "for op in aspirations"]` and a
  containing `for_span` — i.e. a guard without the `is_disabled` conjunct, which no real `aspirate`
  guard has — a well seeded to 100 with `aspirate(resources=[well, well], vols=[60, 60],
  use_channels=[0, 1])` yields a `Verdict.SAFE` finding for the **first** pair and a
  `Verdict.WILL_FAIL` for the **second**, both sited at `VolumeTracker.remove_liquid`, and **no**
  `SAFE` for the second. An implementation that evaluated both guards against one shared
  pre-operation snapshot emits two `SAFE`s and fails. A second sub-assertion: the same fixture with
  `use_channels=[0, 1, 2]` (a length disagreeing with the pair list) widens to `TOP` and emits no
  definite verdict — V0's clause (c), round-1 D2. **The executed half of this criterion is
  withdrawn**: `region_oracle._verdict_at` joins all static findings for one
  `(operation, iteration)` key (`plr-sema/eval/region_oracle.py:344-351`), so an executed comparison
  has no pair dimension, and no executed two-channel one-cell over-draw exists at this pin anyway.
- **AC-14.7 (`env` gates `WILL_FAIL` only, and defaults to unasserted).** AC-14.5's fixture (a), run
  through `check_ir` with the default `env == frozenset()`, yields `Verdict.UNKNOWN` with reason
  `volume_tracking_unasserted` — **not** `WILL_FAIL` — while fixture (b)'s `SAFE` is **unchanged** by
  `env`, in both directions. `check_graph(g, c)` with two positional arguments compiles, runs and
  returns the identical report it returns today for every shipped fixture, and `check_graph(g, c,
  env={"does_volume_tracking"})` reproduces the `check_ir` result. A third sub-assertion pins the
  observation window: the harness's `env` is read from the additive result field the *executed* side
  returns (`training/verify/verifier.py:114-129`, `plr-sema/eval/region_oracle.py:412-435`), and a
  process-wide call to `does_volume_tracking` taken outside that window is asserted **not** to be the
  source. The `SAFE`-unchanged half is the whole content of §14.6's asymmetry argument.
- **AC-14.8 (the registry arithmetic is exactly as specified).** After this increment,
  `len(live_rows()) == 24` and `BUDGET_CAP == 24`; HM-24's `declared` is **3** and `_measure_hm24`
  returns 3, with a structural assertion per pattern; HM-25's `declared` is **8** and its measure
  returns 8; `len(REASON_VOCABULARY) == 10` against HM-14's unchanged `declared == 12`; and
  `test_no_surface_exceeds_its_declared_size` and `test_total_declared_within_budget` both pass. A
  second assertion pins the *entry* condition: the commit's parent has HM-24 at 1 and HM-25 at 6, so
  the diffs are visibly 1 → 3 and 6 → 8 and not 1 → 2 or 5 → 8.
- **AC-14.9 (tier 3 — the volume mutant fires, and the tip mutants do not regress).**
  `plr-sema/eval/volume_mutants.py` reports v1 with **0 unsound** in both directions and its achieved
  `WILL_FAIL`-at-the-raised-index count published, with a floor of **≥ 1** — the floor exists because
  a class that can only ever report 0 is not a gate, which is the reason v2 was withdrawn (§14.9). As
  a non-regression, m1's and m2's numbers are re-measured and published against whatever baseline is
  current at the time this increment runs, each over **≥ 1** row, and any movement is attributed
  before the run is accepted — the `run_one_mutant` refactor (§14.9) is what could move them.
- **AC-14.10 (tier 2b — executed tip-cell ground truth, including the collective and retip cases).**
  The four new region fixtures (§14.9) are executed against the chatterbox deck and compared on
  `(operation, iteration)`: **zero** unsound rows; the straight-line tip over-draw and the
  second-iteration tip over-draw each carry a static `WILL_FAIL` at the `(operation, iteration)` the
  execution raised; the **collective-exhaustion** fixture carries a static `WILL_FAIL` at the
  iteration the execution raised, **not** at the first iteration and **not** nowhere; the **retip**
  fixture carries `UNKNOWN` at the dispense the execution raised — sound, and the case a `[0,0]`-always
  implementation gets wrong by emitting `SAFE`; and the existing `region_unsound == 0` and
  `region_will_fail_fired >= 3` (`outputs/plr-sema/tier2b_260903.json:8-9`) still hold. The collective
  and retip cases are the stub-defeating halves: a per-operation check that never accumulates passes
  the first two and fails the third, and a lifecycle-free implementation passes the first three and
  fails the fourth.
- **AC-14.11 (this document is machine-checked).** `plr-sema/tests/test_spec_lint.py` already carries
  `SPEC_INCREMENT_5` (`:36`) in both parametrised live-spec tests (`:220`, `:243`); their parametrise
  id is renamed off `increment-5-volume-deferred`, `.praxia/docs/INDEX.md` is regenerated, and
  `uv run pytest plr-sema/tests/test_spec_lint.py -q` is **actually run** with its result recorded —
  both the citation checker and the AC-gating half of the cross-reference checker reporting **zero**
  failing violations over this file. Round 1 could not execute this and adjudicated it as a
  prediction; it is a gate, not a prediction, and the run is the gate.

---

## 14.13 Task rows — implemented (sprint 123, 260904)

> Ordering within the table is forced by §14.0's normative gate: **T24 and T25 must both land before
> T26 or T27.** T25 is where the survey schema changes, so T24's bridge is written against the
> *current* `dropped_calls` shape (a bare string is all the four-segment match needs) and T25 migrates
> the one accessor to the record form at the same time as it regenerates the artifact. That keeps the
> dependency in the direction the numbering already implies and avoids a half-migrated schema.

| task | scope | files | gate | ~LOC | depends on | model |
|---|---|---|---|---|---|---|
| **T24** | The bridge derivation (§14.0.1, §14.4): B1's for-loop-over-comprehension-output binding with its `for_span` record and its two fail-closed cases; B2's dataclass-field pass and P1c's **all-methods** constructor-call pass, both feeding a **bridge-only map** that `derive_receiver_states` never consults; P7, P8, the extended volume bridge, the `ast.AugAssign` direction rule and the `volume_guards` payload; every selection published as a measured set | modify `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/tests/test_derive.py`, `plr-sema/data/derived_contracts.json` (regenerated) | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; then `uv run python -m plr_sema.derive --survey-json training/verify/data/plr_preconditions.json --taxonomy-json training/verify/data/plr_exception_taxonomy.json --out $TMPDIR/contracts_t24.json --gap-ledger $TMPDIR/ledger_t24.json` and publish the measured sets — satisfying **AC-14.1**, **AC-14.2** | ~450 | — | Sonnet — four derivations, each of which must be measured and published rather than asserted |
| **T25** | Caller-scope threading, **survey-side** (§14.0.2, §14.6): the survey records `(expr, lineno, scope_trail)` per dropped call and `plr_preconditions.json` is regenerated; P10 as a *consumer* attaching `caller_scope`/`caller_lineno` disjointly from `scope_trail`, with polarity and nearest-first ordering carried through; the generalised conditional-guard rule **and R1's position-containment recognition** | modify `scripts/survey_plr_preconditions.py`, `training/verify/data/plr_preconditions.json` (regenerated), `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/tests/test_derive.py`, `training/tests/test_verify_postconditions.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run python scripts/survey_plr_preconditions.py --out training/verify/data/plr_preconditions.json` and publish the regeneration diff; then re-run T24's derivation command into `$TMPDIR/contracts_t25.json` and publish all four `caller_scope`s verbatim — satisfying **AC-14.3**, **AC-14.4** | ~300 | T24 | Sonnet — the fail-closed boundary is the soundness fence, R1 is the one admission, and the published scopes are measurements |
| **T26** | The interval domain and the transfer functions (§14.3, §14.5): `check/volumestate.py` with V0–V5, **V2 threaded pair-by-pair**, **V0(b)'s `channels_for_call` clause**, **V0(c)'s `use_channels` conjunct** and **V5's `tips_dirty` lifecycle**, wired into `check/__init__.py`; the tip over-draw, retip, two-channel-synthetic and `while` fixtures | create `plr-sema/src/plr_sema/check/volumestate.py`, `plr-sema/tests/fixtures/volume_{overdraw,safe,top,overfill,retip,while,two_channel_one_well}_graph.json`; modify `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/tests/test_check_graph.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_wire_fuzz.py -q` — satisfying **AC-14.5**, **AC-14.6** | ~430 | T24, T25 | Sonnet — V2's threading order and V5's lifecycle are the two places a plausible implementation is unsound |
| **T27** | The hypothesis gate and the registry (§14.6, §14.11): keyword-only `env` on `check_ir` **and on `check_graph`**, threaded into the existing `cache_key(...)` call at `plr-sema/src/plr_sema/check/__init__.py:781-849` and through `CacheStore`'s lookup — **`cache_key` already has the `env` parameter and the fifth component, add neither**; the two new `REASON_VOCABULARY` members; the harness's observation returned as an additive result field from inside the executed window; **HM-24 `declared` 1 → 3 and HM-25 `declared` 6 → 8** (approved by the user 260904), each with its `why_not_derived`/`breaks_when` extended | modify `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/src/plr_sema/check/ir.py`, `plr-sema/src/plr_sema/verdict.py`, `plr-sema/src/plr_sema/_hand_maintained.py`, `plr-sema/eval/oracle_common.py`, `plr-sema/eval/region_oracle.py`, `training/verify/verifier.py`, `plr-sema/tests/test_{verdict,check_graph,hand_maintained_ratchet,cache}.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_verdict.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q`; `uv run pytest training/tests/test_verify_postconditions.py -q` — satisfying **AC-14.7**, **AC-14.8** | ~110 | T25, T26 | Sonnet — the default-`env` direction is a soundness assertion, and the cache work is a thread-through, not an addition |
| **T28** | The oracle (§14.9): `volume_mutants.py` with **v1 only** (`v1_overdraw_dispense`) and the `run_one_mutant` parameterisation; the four tier-2b tip fixtures (straight-line, second-iteration, collective-exhaustion, **retip**); the bathos sidecar fields `volume_fixtures`/`volume_unsound`/`volume_will_fail_fired` | create `plr-sema/eval/volume_mutants.py`, `plr-sema/eval/fixtures/regions/volume_*.py`; modify `plr-sema/eval/tip_mutants.py`, `plr-sema/eval/region_oracle.py`, `plr-sema/eval/tier2_extractor.bth.toml`, `plr-sema/tests/test_oracle_replay.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q`; then `uv run python plr-sema/eval/volume_mutants.py --corpus training/assemble/out/corpus_p25.jsonl --examples-dir training/examples --contracts plr-sema/data/derived_contracts.json --report $TMPDIR/volume_mutants.json`; `uv run python plr-sema/eval/tip_mutants.py --corpus training/assemble/out/corpus_p25.jsonl --examples-dir training/examples --contracts plr-sema/data/derived_contracts.json --report $TMPDIR/tip_mutants_regression.json`; `uv run python plr-sema/eval/region_oracle.py --fixtures plr-sema/eval/fixtures/regions --contracts plr-sema/data/derived_contracts.json --report $TMPDIR/tier2b_volume.json` — satisfying **AC-14.9**, **AC-14.10** | ~320 | T26, T27 | Sonnet — every published number is a measurement |
| **T29** | **DONE (260904, this pass).** Lint and index: rename the stale parametrise id `increment-5-volume-deferred` → `increment-5-volume` at `plr-sema/tests/test_spec_lint.py:220` and `:243` (`SPEC_INCREMENT_5` itself is already defined at `:36` and already parametrised into both live-spec tests); regenerate `.praxia/docs/INDEX.md`; run the lint and record the result | modify `plr-sema/tests/test_spec_lint.py`; regenerate `.praxia/docs/INDEX.md` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_spec_lint.py -q` — satisfying **AC-14.11** | ~2 | — | Haiku |

**Sizing note.** T24 at ~450 is past one session and splits at B2/P1c plus the bridge-only map (the two
typing passes, which land together and leave the tree green because nothing consumes them yet) versus
B1, P7/P8, the direction rule and the extended bridge. **Do not split T24 from T25 across a sprint
boundary**: §14.0's normative gate makes a landed T24 without T25 the configuration in which the
analyzer can construct an ungated volume `WILL_FAIL`, which is the soundness bug this whole re-scope
exists to avoid. T25 grew from ~230 because it now owns the survey schema change and its regeneration
as well as R1. T27 shrank from ~200 because `cache_key` already carries `env` and its fifth component
(round-1 O6) — the remaining work is a thread-through of one call site plus `CacheStore`'s lookup — and
T28 shrank from ~430 because the v2 mutant class is withdrawn (round-1 O11). T27 and T28 gained an
explicit second dependency: T27 needs T25's `caller_scope` before its `env` threading means anything,
and T28 needs both the domain (T26) and the observation plumbing (T27).

---

## 14.14 What this changes in increments 1–4

1. **Main spec §Open decisions 2's sunset clause.** Its resolution reads *"leave numeric atoms at ½
   through v1 and the first post-corpus increment"*. Increments 1–4 have shipped, so the reservation
   no longer holds anything back, and this increment reopens it **for exactly one class of atom**: a
   `Cmp` in a guard raising a taxonomy `volume_state` exception from `pylabrobot.resources.errors`,
   evaluated against §14.3's interval domain. **Every other numeric `Cmp` still folds to ½** —
   including `drop_tips`'s `tip.tracker.get_used_volume() > 0 and (not allow_nonzero_volume) and
   does_volume_tracking()`, which is a **compound** condition excluded by §10.3.1's single-atom
   criterion, not by its numerics.
2. **§Open decisions 2's `SoundnessScope` prerequisite is discharged by narrowing, not by building
   it** (§14.6). `SoundnessScope` as a wire record remains unbuilt and remains deferred row (b).
3. **Increment 1 §10.9's first bullet** ("Volume atoms — every numeric `Cmp` stays ½ … Volume also
   needs a `SoundnessScope` record") is superseded by items 1 and 2. Its *second* clause — that tip
   state does not need such a record — is unchanged and still true.
4. **Increment 1 §10.1.1's "finite-height and needs no widening operator"** is narrowed to the tip
   lattice. §14.3's interval lattice has infinite height and §14.5's V4 is its widening operator.
5. **Increment 1 §10.2.1's P1a is *not* extended.** B2 and P1c are new passes producing a separate
   bridge-only map (§14.0.1, round-1 O9); `_annotated_attributes` and the receiver-selection loop at
   `plr-sema/src/plr_sema/derive/receiver_state.py:720` are untouched, and AC-14.1(iii) pins that.
6. **Increment 2 §11.3.3's cache key already has its fifth component; this increment supplies a real
   value for it.** `cache_key` at `plr-sema/src/plr_sema/check/ir.py:918-925` already takes
   `env: frozenset[str] = frozenset()` and already returns `tuple(sorted(env))` as the fifth element
   (`:953`); #4922 shipped it. **Nothing is invalidated by this increment**: every entry ever written
   has fifth component `()`, and a post-increment default-`env` run reproduces that key identically.
   A run with `env == {"does_volume_tracking"}` produces a *different* key — which **partitions** the
   cache by hypothesis rather than invalidating it, and that partition is exactly what makes §14.6's
   default-`env` direction sound. (The draft claimed this increment *adds* the component and
   *invalidates* every prior entry; round-1 O6 showed both halves false.)
7. **Increment 4 §13.2** is a stub pointing here, and increment 4's §13.7 carries only HM-25 5 → 6.
8. **The survey artifact's schema changes, and that is a cross-package event** (§14.0.2).
   `FunctionPreconditions.dropped_calls` (`scripts/survey_plr_preconditions.py:146`) stops being a
   `list[str]` and becomes a list of `{expr, lineno, scope_trail}` records; `self.dropped` (`:142`)
   stops being a `set[str]`; and `training/verify/data/plr_preconditions.json` is regenerated. Every
   consumer of `dropped_calls` — `plr_sema.derive` and the differential harness — re-reads the changed
   shape, and T25 owns the migration. The change is additive in information and lossless in the old
   field's content.

---

## 14.15 Explicitly not in this increment

- **A capacity operand on `RESOURCE`.** What would make the over-fill half decidable (§14.2): a wire
  change, an `IR_VERSION` bump, and an upstream extractor change to read `Container.max_volume` /
  `Tip.maximal_volume` off the labware definition. Increment 4's round 1 removed the argument for
  taking it early — `ir_version` is already a cache-key component, so a later bump costs exactly what
  an early one does.
- **Liquid-class corrections.** A-NO-CORRECTION assumes none is applied; PLR at this pin applies none
  on the aspirate path (`liquid_handler.py:968`).
- **The 96-head's volume cells.** Excluded by A-TIP-CELL, and V5 sets `tips_dirty` unconditionally on
  any 96-head operation rather than modelling it.
- **`BlowOutVolumeError`.** Excluded by the module conjunct (§14.1 fact 4).
- **A derive-side re-parse of the caller's AST.** §14.0.2 chose **survey-side**; the derive-side pass
  the draft specified is named there and declined, because a text key is exactly what R1 must not rest
  on. (This bullet is the inverse of the draft's, which declined the survey-side option.)
- **Recognising a per-instance flag such as `is_disabled`.** §14.6 fails closed on it and records the
  two candidate discharges that fail. This is the direct cause of the well half producing no definite
  verdict (§14.0.2, row 1).
- **A `transfer` volume mutant class, and volume-guard propagation through `delegates_to`.**
  Withdrawn under round-1 O11 (§14.9). Retaining v2 would first require §14.4 to specify propagation
  through `delegates_to` as a normative box with its own measured expectation — a fifth unproved
  derivation in an increment already carrying four.
- **An executed two-channel one-cell over-draw.** No such shape exists at this pin outside the blocked
  `aspirate` well guard, and `region_oracle._verdict_at` has no pair dimension anyway
  (`plr-sema/eval/region_oracle.py:344-351`). AC-14.6 keeps the case statically.
- **Precision targets.** Deferred (f) stands. AC-14.9's v1 number is published against a floor of 1,
  not gated at a target.

---

## 14.16 Open questions — dispositions after round 1

1. **§14.6's disclosed consequence: what the family says on real data. RESOLVED (user, 260903):
   (a) — build it if it is firable at all.** The corpus is a set of examples, not the sum of what is
   valid and useful; a family that produces `SAFE` on real rows and `WILL_FAIL` on every protocol a
   fixture or a future corpus row can construct is covered, not worthless. **Round 1 did not re-open
   this and this revision does not either**; what round 1 corrected is a factual *input* to it. The
   challenger's O1 argued the family was firable on no tier, which would have falsified the
   resolution's premise; the defender's R1 (§14.6) shows it is firable on the tip path, and §14.0.2's
   table is the accounting. The deliverable is narrower than the draft claimed — *a definite
   `WILL_FAIL` on a tip over-draw, `SAFE`/`UNKNOWN` on every well* — and it is firable, which is the
   premise the resolution rested on.
2. **§14.11's pattern accounting. RESOLVED against the draft (round-1 O12).** The draft argued B1 and
   P10 were bindings rather than idioms and put neither on the registry; that argument is withdrawn
   for B1, which matches a shape. The instrument is **HM-24, not HM-25**, on the registry's own
   silent-versus-loud criterion (`plr-sema/src/plr_sema/_hand_maintained.py:796-799`, `:857-861`): B1's
   failure mode is a silent family collapse. **HM-24 1 → 3, HM-25 6 → 8, P10 off-registry, eleven
   patterns over two rows, no row addition and no cap conversation.** Q2's own instinct — a split
   rather than a ceiling bump — is satisfied by the split that already exists. **This arithmetic was
   approved by the user 260904**: the figure carried into round 1 was HM-24 1 → 2, and T27 spent
   1 → 3 against that approval.
3. **The derive-side-versus-survey-side choice (§14.0.2). RESOLVED survey-side (round-1 O7).** Both
   reports took the survey-side position; the decisive reason is the defender's rather than the
   challenger's cost comparison: R1 requires that the recognised entry be *the `ast.For` node B1 bound
   over*, and only the survey's `lineno` makes that a position test rather than a text match. The
   supporting facts — three lines at an existing site (`scripts/survey_plr_preconditions.py:250`), the
   `else`/`elif` polarity already handled at `:167-180`, the nearest-first ordering already
   conventional at `:85-87`, and multiplicity preserved rather than reconstructed — all hold, and the
   change also keeps a pattern with a silent failure mode off a registry at zero headroom.
4. **Whether `volume_tracking_unasserted` survives. RESOLVED: it lands.** Q1 resolved to (a), and
   §14.6 gives the member a working producer — in fact it is the outcome of every conditional guard
   that evaluates `T`, which after §14.0.2's table means the whole well half. `volume_state_unknown`
   likewise. The dead-data risk increment 4's Q6 raised does not apply to either.
5. **AC-14.9's ungated v2 class. RESOLVED by withdrawal (round-1 O11).** The reviewer position that an
   ungated class should not ship is upheld, and the sharper form of it is that v2 *cannot* be gated:
   `transfer` has no volume-guard derivation path at all (§14.9), so its static side is `UNKNOWN` by
   construction and the class measures the spec's scope decision rather than the implementation —
   verbatim the argument §14.9 already makes for declining an over-fill mutant class. v2 is withdrawn,
   T28 is re-sized, and v1 gains a floor of ≥ 1 so the surviving class is a gate rather than a
   publication.

---

## 14.17 Implementation record (sprint 123, 260904)

T24–T28 landed on branch `coxswain-p2-pipeline` in dependency order, per §14.0's normative gate (T24
and T25 both landed before T26/T27 were started). HM-24 `declared` 1 → 3 and HM-25 `declared` 6 → 8
were **approved by the user 260904** and spent by T27 (§14.11, §14.16 Q2). Reports:
`outputs/plr-sema/t24_measured_260904.json`, `outputs/plr-sema/t25_measured_260904.json`,
`outputs/plr-sema/{volume_mutants,tip_mutants,tier2b,oracle_replay}_260904_inc5.json`.

| row | commit | what landed | measured vs the spec's expectation | divergences |
|---|---|---|---|---|
| T24 | `2e50e613` | B1's for-loop-over-comprehension-output binding with `for_span`; B2's dataclass-field pass; P1c's all-methods constructor-call pass, both feeding the bridge-only map; P7, P8, the extended volume bridge, the `ast.AugAssign` direction rule, the `volume_guards` payload | All four bridged guards derive at `liquid_handler.py:1034/1035/1234/1235` — AC-14.2's exact-two-entries claim holds for both `aspirate` and `dispense`; `:1235` resolves via `Tip.tracker → VolumeTracker` through P1c's all-methods form (AC-14.1(iv)). B1: 2 `(K, name, element_class, for_span)` tuples published, ≥ 2 required by AC-14.1(i) — met. B2: 100 classes / 467 attributes selected, ≥ 8 attributes over ≥ 2 classes required by AC-14.1(ii) — met by a wide margin. P1c: 45 classes / 67 entries, ≥ 3 required by AC-14.1(iv) — met. P7 anchors `VolumeTracker` as specified (§14.4) | P8 needed a per-keyword `Name` relaxation not spelled out in the normative box: `zip`'s last argument (`mix or [None]*n`) is a `BoolOp`, not a bare `Name` — accepted, because P8's own fail-closed clause (§14.4) only requires *the paired names* to be `Name`s, and `mix` is not one of the two guards this increment reads. P7's free-volume/used-volume accessor uniqueness is enforced symmetrically (both directions), tightening §14.4's fail-closed rule rather than loosening it — acceptable, strictly safer. The local-pairing wire shape is `{local: true, name}` rather than a bare sentinel — additive, does not change V0(b)'s reading (§14.5). The P8-target alternative binding (an alternate resolution path considered during implementation) was not implemented — a follow-up only if a future PLR method needs it; no current contract requires it |
| T25 | `5582ae08` | Survey schema change: `DroppedCall{expr, lineno, scope_trail}` records `dropped_calls`; P10 as a consumer attaching `caller_scope`/`caller_lineno`; `volume_guard_is_unconditional` (R1) | Survey re-run: 4770 records unchanged, dropped-call entries 4717 → 5769 with multiplicity preserved (0 non-additive diffs) — matches §14.0.2's "additive in information, lossless in the old field's content" claim exactly. Four caller_scopes published as AC-14.3 requires: `:1034`/`:1234` carry the `is_disabled` entry under both `env`s (conditional); `:1035`/`:1235` are unconditional under `env={does_volume_tracking}` — reproduces §14.0.2's disposition table row-for-row. GATE = GO (the user's go/no-go per §14.0's normative gate) | R1 (`volume_guard_is_unconditional`) lives in `plr_sema/derive/receiver_state.py`, not a new `check/` module — the normative box did not mandate a location; this keeps R1 next to the bridge it recognises rather than splitting the recognition logic from the attachment logic, and both round-1 reports read this module regardless. Side effect not predicted by the spec text: `channel_guards` iteration order is now AST order (a consequence of the schema migrating from a `set` to a `list`) — noted as a benign ordering change, not a soundness or precision effect; no AC depends on iteration order |
| T26 | `92776b8e` | `check/volumestate.py` (V0–V5); `env=` keyword-only on `check_ir`/`check_graph`; `REASON_VOCABULARY` 8 → 10; seven region fixtures | First volume `WILL_FAIL`: the overdraw fixture under `env={does_volume_tracking}` yields exactly one `WILL_FAIL` at `PlrSite(volume_tracker.py, 92, VolumeTracker.remove_liquid)` plus the seed's `unresolved_delegate` finding — matches AC-14.5(a) exactly, including the "exactly one `WILL_FAIL`" (not "exactly one finding") distinction the AC calls out. `env={}` → `UNKNOWN`/`volume_tracking_unasserted`, matching AC-14.7. Retip never `SAFE` (AC-14.5(e)); `while` widens every region cell to `TOP` after `END` (AC-14.5's sixth fixture, V4). Two-channel-one-well: pair 1 `SAFE`, pair 2 `WILL_FAIL`, matching AC-14.6's sequential-threading claim exactly (a simultaneous-evaluation implementation would have produced two `SAFE`s). `test_tip_typestate`'s pinned count excludes the four additive volume findings, as AC-11.6-style non-regression requires | The seven fixtures shipped as `volume_{overdraw,safe,top,overfill,retip,while,two_channel_one_well}_graph.json`, not the `volume_tip_{overdraw,safe,...}` names §14.12/§14.13 originally wrote — reconciled to the shipped names in this pass (§14.9, §14.12, §14.13 T26). Acceptable: the shipped names are unambiguous (there is exactly one volume fixture family) and avoid implying a `tip_typestate`-namespace collision with the unrelated `tip_*` fixtures increment 1 already ships. V4's widening is scoped to volume cells specifically (tip cells are not re-widened by this rule) — consistent with §14.3's statement that volume cells are not run through the K-pass tip fixpoint (infinite-height lattice) |
| T27 | `96234d90` | `env` threaded into the `ir.cache_key(...)` call and `CacheStore`; the harness's `volume_tracking_observed` returned from inside the executed window; HM-24/HM-25 registry spend | `env` partitions the cache; the default-`env` key is byte-identical to every pre-T27 entry (`test_env_partitions_the_cache`), confirming §14.14 item 6's partition (not invalidation) claim. `volume_tracking_observed` is read from inside `verifier.py:128` (`region_oracle._run_fixture_execution`, whose `finally` also restores the tracking flags) — matches AC-14.7's third sub-assertion that the observation window is pinned to the executed side, not a process-wide read. Registry: HM-24 `declared` 1 → 3, `_measure_hm24` returns 3 (tip bridge regex, volume bridge regex, B1 structural — one pattern per HM-24 sub-item, §14.11); HM-25 `declared` 6 → 8 (P7, P8); `live_rows() == 24 == BUDGET_CAP`, satisfying AC-14.8 | The seed setter is **derived**, not hand-typed: `_volume_setter` recognises a unique unconditional `self.<anchored_field> = <bare param>` at statement position and publishes `is_volume_setter: true` on the setter's own contract entry — because the shared `receiver_state` block cannot host extra per-class keys (`tipstate` indexes `channel_attr` unconditionally, so a bare boolean addition there would collide). Not specified as a normative box in §14.0.1/§14.4; disclosed here as an implementation-found mechanism, not a deviation from any stated rule — acceptable, and it keeps HM-25's "no hand-typed accessor name" claim true for the setter path too. `_UNMODELLED_TIP_MOVEMENT_METHODS` (a named-list stopgap from an earlier increment) is replaced by a structural rule — `tips_dirty` iff the contract has no `volume_guards` and the call references ≥ 1 resource — a strict improvement (a list can miss a method; the structural rule cannot), not a divergence from this increment's own spec text. The literal-scan list (AC-14.2(iii)) grew to 11 names to cover both the tip- and volume-family literals in one scan — expected growth, not a scope change |
| T28 | `c67fc230` | `eval/volume_mutants.py` with `v1_overdraw_dispense`; `run_one_mutant(mutator, expected_exc)` refactored to accept both classes; four executed tip fixtures (straight-line, second-iteration, collective-exhaustion, retip); bathos sidecar fields | v1: 67/67 raised, 67/67 `WILL_FAIL` at the raised index, 0 unsound — satisfies AC-14.9's ≥ 1 floor by a wide margin. m1 199/199, m2 289/289 (corpus 1523 rows), 0 unsound — the `run_one_mutant` refactor did not move the m1/m2 numbers, satisfying AC-14.9's non-regression clause. Tier-2b: 16 fixtures, `region_unsound` 0, `region_will_fail_fired` 7 (4 tip + 3 volume), `volume_will_fail_fired` 3, retip `UNKNOWN` at `(dispense, 1)` — matches AC-14.10's four sub-claims (straight-line and second-iteration `WILL_FAIL` at the raised `(operation, iteration)`, collective-exhaustion `WILL_FAIL` at the iteration that actually raised, retip `UNKNOWN` not `SAFE`). Tier 1: unsound 0, totality 0, crosscheck 191/191, `rows_executed` 343, `setup_error` 0. Real-row diagnostic scan (591 rows): `safe` 66, `volume_state_unknown` 340, `WILL_FAIL` 0, `volume_tracking_unasserted` 0 — `volume_state_unknown` takes precedence over the hypothesis reason on unseeded cells, consistent with §14.2's capacity-undecidability argument | v1's mutation seeds the source well at 300 µL with an empty destination, rather than mutating a bare seeded well directly, because `dispense` checks the destination's `add_liquid` capacity **before** the tip's `remove_liquid` (V1's evaluate-then-transition order, §14.5) — a single seeded well would have hit its own over-fill guard (permanently `½`, §14.2) before the tip guard could fire, measuring the wrong half of the family. Documented in `volume_mutants.py` and here rather than left implicit — acceptable, forced by the guard-evaluation order this increment itself specifies, not a workaround for a bug |

**Divergence summary.** No divergence recorded above changes a soundness claim (§14.10) or narrows an
acceptance criterion; each is either a strictly-safer tightening (P7's symmetric uniqueness), a
structural improvement over a named-list stopgap (`tips_dirty`'s rule), an implementation-found
mechanism not previously specified (`_volume_setter`), a benign ordering change with no AC dependence
(`channel_guards` iteration order), or a fixture/file naming reconciliation folded back into this
document (§14.9, §14.12, §14.13). No follow-up ticket is required by any row above; the P8-target
alternative (T24) is the only item explicitly left as future work, and it is future work only if a
PLR method not currently in the corpus needs it.

---

## References

- Main specification (amended): `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md` — §0, §0.1,
  §Open decisions 2 (amended, §14.14), §6.2, §7.3–7.4, §9.1–9.4, §Deferred rows (b)/(c)/(d)/(f).
- Increment 1 (amended): `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md` — §10.1.1
  (narrowed), §10.1.3, §10.2.1 (**not** extended — see §14.14 item 5), §10.2.2, §10.2.5–10.2.6,
  §10.3.1–10.3.3, §10.4, §10.5, §10.9 (superseded for volume).
- Increment 2 (amended): `.praxia/docs/specs/260902_plr-sema-ir-bytecode-increment.md` — §11.1.2,
  §11.1.3, §11.1.4, §11.3.1–11.3.3 (the cache key's fifth component, already shipped), §11.4.1.
- Increment 3: `.praxia/docs/specs/260903_plr-sema-real-programs-increment.md` — §12.1.2 (the
  `_constructor_state` precedent P1c's architecture is modelled on, and whose `__init__` restriction
  P1c does not inherit), §12.1.6 (the scaffolding-`CALL` convention §14.8 reuses), §12.3.3 (L1's tail
  widen, which V4 attaches to), §12.13.
- Increment 4 (the document this was re-scoped out of):
  `.praxia/docs/specs/260903_plr-sema-families-cache-increment.md` — §13.2 (the stub pointing here),
  §13.7 (which carries HM-25 5 → 6 only), §13.13 Q2/Q3/Q6.
- Adversarial round 1 on increment 4, which produced this document:
  `.praxia/docs/audits/260903_plr-sema-families-cache-round1-challenger.md` (O1 the bridge does not
  match at the pin; O2 the `env` gate cannot reach a bridged guard; O3 `is_disabled` is a property;
  O4 the V0/V2 update order) and
  `.praxia/docs/audits/260903_plr-sema-families-cache-round1-defender.md` (all six CONCEDED; the
  re-scope recommendation).
- **Adversarial round 1 on this document, which this revision executes:**
  `.praxia/docs/audits/260903_plr-sema-volume-round1-challenger.md` (O1–O14; O1 `WILL_FAIL`
  unreachable, O2 P1c cannot see `__post_init__`, O3 the literal scan is red at HEAD, O4 the retip
  false `SAFE`, O5 the observation window, O6 the cache key already has `env`, O7 P10 re-implements
  the survey without polarity, O8 the seed `CALL`'s surface, O9 B2's non-sequitur, O10 the direction
  under-determination, O11 `transfer` has no path, O12 the registry count, O13 stale text and drifted
  citations, O14 publish-only ACs) and
  `.praxia/docs/audits/260903_plr-sema-volume-round1-defender.md` (O1 PARTIAL with R1; O2/O3/O4/O6/
  O7/O11/O13 CONCEDE; O5/O8/O9/O10/O12/O14 PARTIAL; D1 the tip guard's local pairing, D2 the
  `use_channels` conjunct; verdict `needs_revision`, twelve ordered items).
- PLR source at submodule pin `dd79c4c89`: `liquid_handling/liquid_handler.py` (the `drop_tips`
  non-zero-volume guard at `:656-657`, the zip-input normalisations at `:962-965`, the `vols`
  coercion at `:968`, `tips` at `:974`, the length `ValueError` at `:989-992`, the multi-channel
  expansion at `:997-999`, the aspiration comprehension at `:1007-1028` with `resource=r` at `:1009`,
  `volume=v` at `:1010`, `tip=t` at `:1014`, the `zip` at `:1018-1027` and `mix` at `:1026`, the
  `for op in aspirations:` at `:1031`, the tracking and `is_disabled` conjuncts at `:1032-1033`, the
  tracker calls at `:1034-1035`, the commit/rollback block at `:1058-1064`, the `BlowOutVolumeError`
  raises at `:1185`/`:1188`, the dispense mirror at `:1231-1235`, `transfer` at `:1273-1361`, and the
  96-head `if`/`elif` volume-tracking shape at `:1932-1935`); `liquid_handling/standard.py:51-60` and
  `:63-72` (the two dataclasses whose class-level annotations B2 must admit, `volume: float` at
  `:68`); `resources/volume_tracker.py` (the tracking flag at `:17-22`, `no_volume_tracking` at
  `:25-30`, `__init__`'s fields at `:40-52` with `_is_disabled` false at `:46`, `is_disabled` as a
  `@property` at `:54-56`, `disable` at `:58-60`, `set_volume` at `:66-72` with the `_callback` call
  at `:71-72`, `remove_liquid` at `:88-99` with its guard at `:91`, its raise at `:92` and its
  `-=` write at `:96`, `add_liquid` at `:101-112` with its raise at `:105` and its `+=` write at
  `:109`, `get_used_volume` at `:114-116`, `get_free_volume` at `:118-120`, `get_liquids` at
  `:122-138` with its raise at `:136`, `commit`/`rollback` at `:140-151`);
  `resources/container.py:84-85` (the unannotated `self.tracker` write P1c must read) and `:88` (the
  `register_callback` call that is not a write); `resources/tip.py:11-12,27,32,45`;
  `resources/tip_rack.py:52` (the third and last `self.tracker =` write in the submodule).
- Analyzer source: `plr-sema/src/plr_sema/derive/receiver_state.py` (`_is_self_attr` at `:167-170`,
  `_annotated_attributes` at `:173-184` with its `ast.AnnAssign` test at `:180` and its `setdefault`
  at `:183`, `_channel_default_idiom`'s module-scoped literal-scan precedent at `:298-307`,
  `_constructor_state` at `:588-627` walking `ast.Assign` at `:613` and `ast.AnnAssign` at `:616`,
  the receiver-selection loop at `:714-733` with its alphabetical tie-break at `:724`,
  `compute_channel_bridge` at `:978-1042` with the callee-sourced `scope_trail` at `:1042`);
  `plr-sema/src/plr_sema/check/ir.py:184-191,201,320,446,784-787,794-795,806-812,818,860-887,918-925,953`;
  `plr-sema/src/plr_sema/check/__init__.py:363-366,372-374,383-392,714-719,766`;
  `plr-sema/src/plr_sema/check/tipstate.py:245-247`; `plr-sema/src/plr_sema/check/graph.py:193`;
  `plr-sema/src/plr_sema/check/_supported_tools.py:5-21`;
  `plr-sema/src/plr_sema/_hand_maintained.py:43,244-261,561-565,788-822,823-863,867-871`;
  `plr-sema/src/plr_sema/verdict.py:129-154`.
- Survey source: `scripts/survey_plr_preconditions.py` (`scope_trail`'s nearest-first convention at
  `:85-87`, `dropped_calls` at `:120`, `_scope_trail` at `:135`, `self.dropped` at `:142`, `_record`
  at `:148-160`, `visit_If`'s polarity at `:162-180`, `visit_For` at `:182-189`, `visit_Call`'s drop
  at `:230-252` with the recording line at `:250`).
- Harness: `plr-sema/eval/oracle_common.py:690-739,983-989`;
  `plr-sema/eval/tip_mutants.py:69,127-140,167,170-224,178,188,238-247`;
  `plr-sema/eval/region_oracle.py:344-351,412-435,508-533`; `training/verify/verifier.py:105-129,149-152`;
  `training/tests/test_verify_postconditions.py:76-85`.
- Lint: `plr-sema/tests/test_spec_lint.py:36,220,243`.
- Artifacts: `plr-sema/data/derived_contracts.json:157965-157996,158054,158102-158133,158185-158197,168096-168113`;
  `training/verify/data/plr_exception_taxonomy.json:2964-2972,2991-2999,3010-3056`;
  `training/verify/data/plr_preconditions.json:49766-49772,49808-49812,49863-49864`.
- Data: `outputs/plr-sema/oracle_replay_260903_rebaseline.json:2-29`;
  `outputs/plr-sema/tier2b_260903.json:1-45`.

---

## Remediation changelog (round 1)

Applied against the defender's adjudication of this document's own round-1 challenger, in the
defender's ordered-list order. `status` moved `draft` → `reviewed-round-1`; `spec_version` **13 → 14**.
The AC count is unchanged at eleven — no renumbering was needed, because the criteria were re-sited
rather than added or dropped — and the task-row count is unchanged at six. The largest single change
is not an edit but a **re-siting**: the increment's headline deliverable moves from the well to the
tip.

| item | O/D-id | verdict | change | section(s) |
|---|---|---|---|---|
| 1 | **O1** | PARTIAL — global claim rejected, four ACs conceded | §14.6 gains **R1**: a `caller_scope` entry is recognised independently of `env` iff it is the `ast.For` B1 bound over, tested by **position containment** (`for_span` brackets `caller_lineno`), never by text. The three-conjunct soundness argument is carried verbatim — V2 already unrolls that loop; PLR's own `ValueError` pins the trip count (`liquid_handler.py:962-965,974,989-992,999,1026`); V0-not-applying ⇒ V3 widens. `is_disabled` stays fail-closed, with both failed discharges stated in their own box. §14.16 Q1 stays **resolved (user)**; the deliverable is restated as "a definite `WILL_FAIL` on a tip over-draw, `SAFE`/`UNKNOWN` on every well" | §14.6, §14.0.1, §14.16 Q1, top blockquote |
| 2 | **O1** | CONCEDE | §14.0.2 publishes **four** measured expectations, one per bridged guard, with the decidable × under-`is_disabled` disposition table — `liquid_handler.py:1034`/`:1234` carry the `is_disabled` entry, `:1035`/`:1235` do not, and only `:1235` is both decidable and recognised | §14.0.2 |
| 3 | **O7 / Q3** | CONCEDE — inverted | Q3 resolves **survey-side**: `scripts/survey_plr_preconditions.py:250` records `(text, lineno, scope_trail)`, `self.dropped` (`:142`) becomes a list of tuples, `dropped_calls`'s schema changes and `plr_preconditions.json` is regenerated. P10 becomes a **consumer** carrying the survey's `else of: if …` polarity (`:167-180`) and nearest-first order (`:85-87`), and leaves the registry arithmetic. A-SCOPE-TEXT is replaced by **A-SCOPE-POSITION**. §14.14 gains item 8 for the schema change; §14.15's bullet inverts; T25's files gain the survey script and the regenerated JSON | §14.0.2, §14.7, §14.11, §14.13 T25, §14.14, §14.15, §14.16 Q3 |
| 4 | **O2** | CONCEDE (blocking) | P1c scans **every `ast.FunctionDef`/`ast.AsyncFunctionDef` child of the `ClassDef`**, not `__init__` — `Tip` is a `@dataclass` (`tip.py:11-12`) whose tracker write is in `__post_init__` (`:32`, write at `:45`) and `_constructor_state` returns `None` when no `__init__` exists (`receiver_state.py:604-610`). The fail-closed clause is kept verbatim over the union of writes; the three `self.tracker =` writes (`container.py:85`, `tip.py:45`, `tip_rack.py:52`) are noted as non-colliding; §14.2's `__post_init__` sentence is reconciled with §14.0.1; §14.11's language-construct argument is re-made against the all-methods form | §14.0.1, §14.2, §14.11 |
| 5 | **O4 + D1 + D2** | CONCEDE (blocking, on the headline path) | §14.5 gains **V5**, the tip-cell lifecycle: `TOP` on drop, `[0,0]` on pickup iff a monotone `tips_dirty` is false, `tips_dirty` set by any drop of a not-provably-empty tip and by any unmodelled tip movement — with the two simple rules (`TOP`-always, `[0,0]`-always) shown to destroy the family and to be unsound respectively. **V0 gains clause (b)** resolving a local per-channel pairing to `[("tip", c) for c in channels_for_call(op)]` (`plr-sema/src/plr_sema/check/tipstate.py:245-247`), fail-closed to V3 on `⊤` (D1), and **clause (c)**, the literal-`use_channels` length conjunct (D2). New assumption rows **A-TIP-LIFECYCLE** and **A-TIP-PAIRING**; a retip fixture in AC-14.5(e) and in AC-14.10 | §14.3, §14.5, §14.7, AC-14.5, AC-14.10 |
| 6 | **O1 + O8 + O14** | CONCEDE | §14.12 re-sited onto the tip path. AC-14.5(a) becomes `pick_up_tips`/`aspirate(50)`/`dispense(60)` → **exactly one `WILL_FAIL` finding** at `PlrSite(volume_tracker.py, 92, VolumeTracker.remove_liquid)`, with the seed's `unresolved_delegate` finding named (`derived_contracts.json:1782-1794`). AC-14.6's **executed half is withdrawn** and its static half re-specified against a synthetic contract table. AC-14.10's four fixtures become tip over-draws including the retip case. AC-14.2(iii)'s scan is narrowed to `derive/receiver_state.py` + `check/volumestate.py` per the shipped precedent (`receiver_state.py:298-307`) — the draft's whole-`src/` scan is red at HEAD (`plr-sema/src/plr_sema/check/ir.py:320,446,860-887`, `plr-sema/src/plr_sema/check/graph.py:193`). Publish-only clauses gain cardinality floors | §14.8, §14.12, §14.10 |
| 7 | **O10 + D2** | PARTIAL — better remedy than a tie-break | §14.4 gains the **direction rule**: the direction of a bridged method is the sign of its `ast.AugAssign` on the P7-anchored field. `volume_tracker.py:96` writes `-=` and `:109` writes `+=`; *no write ⇒ guard without transfer*, which classifies the deprecated `get_liquids` (`:122-138`) correctly as a pure read rather than excluding it by name. V0's `use_channels` conjunct (D2) lands in the same pass | §14.4, §14.5 V0/V2, §14.11's table |
| 8 | **O9** | PARTIAL | B2 and P1c feed a **bridge-only map**; `plr-sema/src/plr_sema/derive/receiver_state.py:720`'s input is untouched. The B2 box's "disjoint branch **so** bit-for-bit unaffected" non-sequitur is replaced by the BFS/`setdefault` hazard (`:183`) and by "true by construction, because `derive_receiver_states` does not call the new pass — and AC-14.1(iii) measures it anyway". §14.4's "P1a-as-extended-by-B2" and "P1a or P1c" are rewritten to name the bridge map | §14.0.1, §14.4, §14.14 item 5, AC-14.1(iii) |
| 9 | **O11** | CONCEDE | `v2_overdraw_transfer` **withdrawn**: `transfer` (`liquid_handler.py:1273-1361`) matches neither P8 nor B1 nor the bridge shape, and its computed `vols` (`:1345`, `:1349`) fail V0, so the class can only ever report `0 of n`. T28 re-sized ~430 → ~320; §14.16 Q5 resolved by the withdrawal, citing §14.9's own over-fill-mutant argument. v1 is re-sited onto `dispense` for the same reason and gains a floor of ≥ 1 | §14.9, §14.13 T28, §14.15, §14.16 Q5, AC-14.9 |
| 10 | **O5 + O6** | PARTIAL / CONCEDE | `cache_key` **already** carries `env` and its fifth component (`plr-sema/src/plr_sema/check/ir.py:918-925,953`); T27 threads it into the call at `plr-sema/src/plr_sema/check/__init__.py:766` and through `CacheStore` and **adds nothing to the tuple**. §14.14(6)'s "invalidates every entry" is replaced by **partition** semantics. §14.6's observation paragraph is replaced by the additive-result-field mechanism returned from inside the executed window (`training/verify/verifier.py:114-129`, `plr-sema/eval/region_oracle.py:412-435`), with the challenger's tier-2b ordering claim corrected (execution at `region_oracle.py:516` precedes static at `:527`). `check_graph` gains keyword-only `env=` on the `cache=` precedent (`plr-sema/src/plr_sema/check/__init__.py:967-973`). T27 re-sized ~200 → ~110 | §14.6, §14.13 T27, §14.14 item 6, AC-14.7 |
| 11 | **O12** | PARTIAL — count conceded, instrument rejected | **HM-24 `declared` 1 → 3** (the volume bridge shape **and B1**) with `_measure_hm24` returning 3; **HM-25 6 → 8** (P7 + P8); **P10 off-registry** under survey-side; `live_rows()` unchanged at 24. The "bindings rather than idioms" paragraph is replaced by the registry's own silent-versus-loud criterion (`plr-sema/src/plr_sema/_hand_maintained.py:796-799`, `:857-861`). **Marked PENDING USER APPROVAL at T27** — the previously planned figure was HM-24 1 → 2 | §14.11, §14.13 T27, §14.16 Q2, top blockquote, AC-14.8 |
| 12 | **O13** | CONCEDE | Every stale unscheduled/deferred sentence deleted: the frontmatter `title` and `description`, the top blockquote's "`draft-deferred`: nothing in it is scheduled", §14.0's heading, §14.12's preamble, §14.13's "Every row in this table is unscheduled" blockquote (which contradicted the heading immediately above it), and the References/changelog's "This document has had no adversarial round of its own" (×2). The nine drifted citations are fixed to the defender's verified values — `_is_self_attr` `:164-167` → `:167-170`; `_annotated_attributes` `:170-181`/`:177` → `:173-184`/`:180`; `_constructor_state` `:523-563` → `:547-587` (the draft's `:540-545` was inside `reset_rule_candidates`); its `ast.Assign`/`ast.AnnAssign` walks `:548`/`:551` → `:572`/`:575`; `compute_channel_bridge`'s `scope_trail` copy `:787` → `:1042`; `live_rows()` `:851-855` → `:867-871`; HM-24 `:781-814`/`:793-795` → `:788-822`/`:801-803`; HM-25 `:815-847`/`:828-830` → `:823-863`/`:841-843`; `SingleChannelDispense` `liquid_handling/standard.py:63-72` → `:63-72` with `volume: float` at `:68`. T29 is re-scoped to the parametrise-id rename at `plr-sema/tests/test_spec_lint.py:220`/`:243` plus the `INDEX.md` regeneration, ~15 → ~2 LOC, and AC-14.11 now requires the pytest run to be **executed and recorded** rather than predicted. §14.13's estimates and dependency column updated (T25 ~230 → ~300, T27 ~200 → ~110, T28 ~430 → ~320; T27 gains T25, T28 gains T26) | frontmatter, top blockquote, §14.0, §14.12, §14.13, References, this table |

---

## Changelog (sprint 123 close, 260904)

`status` moved `reviewed-round-1` → `implemented-round-1`; `spec_version` **14 → 15**. Not an
adversarial round — a docs-close pass reconciling this document to what T24–T28 actually shipped.

| item | change | section(s) |
|---|---|---|
| 1 | Every "PENDING USER APPROVAL" marker resolved to **approved by the user 260904**: HM-24 `declared` 1 → 3, HM-25 `declared` 6 → 8, spent by T27 | frontmatter description, top blockquote, §14.13 T27, §14.16 Q2 |
| 2 | New §14.17 added: the per-row implementation record (commit, what landed, measured numbers against this document's own published expectations, divergences and why each is acceptable) | §14.17 (new) |
| 3 | §14.9/§14.12/§14.13 T26's fixture names reconciled to the shipped names — `volume_{overdraw,safe,top,overfill,retip,while,two_channel_one_well}_graph.json`, not the `volume_tip_*` form this document previously specified | §14.9, §14.12, §14.13 T26 |
| 4 | §14.13's heading changed from "scheduled: next sprint" to "implemented (sprint 123, 260904)"; T29's own row marked done by this pass | §14.13 |
| 5 | Thirteen drifted citations re-anchored to their symbols' current locations across this document, following the same code churn (T24–T28) that made §14.9/§14.12/§14.13's fixture names stale; none deleted, none widened | throughout, per `check_spec_citations.py` |
| 6 | Main spec (`260901_plr-sema-pre-corpus-spec.md`) §9.2's HM-24/HM-25 ceilings brought into agreement with this document's registry (1 → 3, 6 → 8), closing the `hm_ceiling_mismatch` cross-reference violation; increment 4's §13.2 stub and §13.14 updated to record the volume family as implemented and #4881a as landed at `7761af22` | (external) main spec §9.2, increment 4 §13.2/§13.14 |
