---
title: 'plr-sema deferred items (b),(f): literature findings'
description: 'Research subagent output (260901) on deferred semantic questions (b) and (f) from the abstract-interpretation/typestate corpus (NLM notebook + web).'
status: final
task_id: 260901_plr-jit-research-b-f
date: '260901'
confidence: ''
sources: ''
---
# Deferred items (b) and (f) — literature findings

task_id: 260901_plr-jit-research-b-f · date: 2026-09-01 · status: research output, no code written

## Source key

Notebook `8f1e2dda-0b5d-44d2-bcb2-2a8459b1a28c` ("abstract interpretation", 17 sources). Every
`notebook_query` answer spilled its full citation payload; claims below cite the spill file. Grep a
spill for `cited_text` to recover the underlying quote.

| tag | spill path |
|---|---|
| nlm-1 | `/home/marielle/projects/praxis/.praxia/nlm/260901-141234__in-abstract-interpretation-what-precisely-is-the__9b7e89ff.json` |
| nlm-2 | `/home/marielle/projects/praxis/.praxia/nlm/260901-141419__consider-an-analyzer-that-does-not-abort-for-eac__9b7e89ff.json` |
| nlm-3 | `/home/marielle/projects/praxis/.praxia/nlm/260901-141545__our-unsoundness-risk-is-not-in-the-abstract-stat__9b7e89ff.json` |
| nlm-4 | `/home/marielle/projects/praxis/.praxia/nlm/260901-141744__how-did-the-astree-static-analyzer-actually-achi__9b7e89ff.json` |
| nlm-5 | `/home/marielle/projects/praxis/.praxia/nlm/260901-141908__does-the-literature-distinguish-in-an-analyzer-s__9b7e89ff.json` |

All five queries share `conversation_id` `9b7e89ff-211a-415b-8c8c-5fb7211f628a`, so they can be
continued as one thread.

---

## Q1 — Is "sound over-approximation vs. bail-out" a real distinction?

**Answer: it is real, but the spec has named the wrong axis, and the axis it named is the less
dangerous one.** The literature separates *three* things where deferred item (b) names two, and our
live hazard is the third — the one (b) does not mention.

### The three things

**(A) Assigning ⊤.** ⊤ is a first-class element of the abstract domain with γ(⊤) = the entire
concrete universe. Assigning it *trivially satisfies* the local soundness condition
`⟦s⟧(γ(a)) ⊆ γ(⟦s⟧#(a))`, because the right-hand side is everything. Analysis continues; the
imprecise value is passed downstream and can be *refined back* by a later guard (a subsequent
`if x >= 0` applies the abstract test transformer to ⊤ and recovers `[0, +∞)`).
[notebook: nlm-1]

**(B) Bail-out.** The literature's default reading of "bail-out" is *meta-level termination* of the
analysis: an uncaught exception, a fatal error, an aborted propagation. It produces no invariant at
or beyond that point, computes no fixpoint, and lies outside the domain (an `Result<D#, Error>`, not
a `D#`). In that reading ⊤ and bail-out are formally distinct, and the notebook says so flatly.
[notebook: nlm-1]

**(C) Silently dropping the obligation.** The construct is neither modelled as ⊤ nor reported — it
simply never generates a proof obligation. This is not a domain question at all; it is a hole in the
*property catalogue*. The literature calls this a **silent false negative — a soundness bug in the
front end**, and prescribes **fail-closed front ends**: a front end that cannot categorize a
syntactic shape must emit an explicit unsupported-construct token or a synthetic `assert(false)`, and
is *never* allowed to ignore it. [notebook: nlm-3, nlm-5]

### Where the "false dichotomy" intuition is right, and where it is wrong

The brief's suspicion — that a *reported* bail-out may be indistinguishable from ⊤ — is **correct at
the level of the emitted verdict and incorrect at the level of state propagation**. The notebook
splits it precisely: [notebook: nlm-2]

- If the analyzer emits `UNKNOWN` for the operation, logs which step failed, **sets the affected
  state components to ⊤, and feeds that over-approximated state into the successor nodes**, then
  "this is precisely the standard abstract interpretation mechanism of assigning ⊤". Same thing, two
  names.
- If the analyzer merely logs `UNKNOWN` **and continues without updating the abstract state** —
  freezing the pre-state, omitting the operation's side effects, skipping propagation — it is *not*
  assigning ⊤. This "corrupts the abstract transition relation, rendering downstream claims of SAFE
  unsound."

So the distinction that survives is not `⊤ vs. bail-out`; it is **`does the give-up propagate?`** and,
one level up, **`was the obligation generated at all?`**.

### Where plr-jit v1 actually sits

Fourth category, and the literature names it exactly. Rival & Yi §1.3.5, quoted in the notebook:

> "From a logical point of view, the soundness objective is very easy to meet since the trivial
> analysis defined to always return false [rejecting every program as unproven] obviously satisfies
> definition 1.2 ... This analysis is not useful since it will never produce a conclusive answer."

Nielson & Nielson, *Semantics with Applications* §5.1, same point: "an analysis that always returns
these 'fail-safe' properties will be a safe analysis although not a very informative one."
[notebook: nlm-2]

§0's phrase "trivially sound analyzer" is therefore **literally the literature's own term**, correctly
applied [our code: `.praxia/docs/specs/260901_plr-jit-pre-corpus-spec.md:31`]. The honest corollary,
which §0 does not currently state, is that **trivial soundness carries zero mathematical obligation**
— soundness is the implication `A(p) = SAFE ⟹ p ⊨ P`, and an analyzer that never emits SAFE makes
the antecedent false everywhere. `def analyze(op): return UNKNOWN` satisfies the definition. So v1's
soundness is *true* and *carries no evidence whatsoever* that the post-corpus analyzer will be sound.
[notebook: nlm-2]

Further: **v1 cannot express the (A)/(B) distinction at all**, because it has no abstract state to
propagate. `join` is a pure fold over a flat finding multiset
[our code: `plr-jit/src/plr_jit/verdict.py:129-152`]. There is nothing to set to ⊤. This is a real
argument that deferring (b) *alongside* (a) is correct — the half of (b) that is about ⊤-propagation
is genuinely unrepresentable until a domain exists.

**But the other half of (b) is not deferrable and is being deferred anyway.** Whether an obligation is
*generated* is decided by `derive`/the survey — code being written now, in T6 — and it is decided
wrong today: the survey's recording rule is an allow-list over receiver shapes, so calls whose
receiver is not a bare `self` leave no trace at all
[our code: `.praxia/docs/specs/260901_plr-jit-pre-corpus-spec.md:1218-1226`]. That is category (C).
§7.4 already spotted it and correctly deferred the *fence*; what it did not spot is that (C) is a
front-end/TCB defect rather than a domain question, and therefore **does not depend on deferred item
(a) at all**.

### Settled vs. judgment call

- **Settled by the literature:** ⊤ and a give-up that propagates ⊤ are the same mechanism; a give-up
  that does not propagate is unsound as soon as anything else is claimed; a silently dropped
  obligation is a front-end soundness bug, not an over-approximation; an always-UNKNOWN analyzer is
  sound and vacuously so.
- **Judgment call:** whether to restate deferred item (b) along the axis the literature actually
  uses. My recommendation is yes — see R1.

---

## Q2 — What each choice obliges us to do

Framed as: *if* UNKNOWN is to mean "sound over-approximation", what must hold of everything else?

The notebook gives four obligations for an analyzer that is sound-because-it-assigns-⊤, and one
(non-)obligation for the vacuous case. [notebook: nlm-1, nlm-2]

| # | obligation | what it costs plr-jit |
|---|---|---|
| O1 | **Local soundness of every transfer function**: `∀a#. f(γ(a#)) ⊆ γ(f#(a#))`. ⊤ satisfies this for free. | Cheap *for the give-up cases*. Expensive for every case where we want precision: each derived contract's effect on state must be shown to over-approximate PLR's real effect. Presupposes (a). |
| O2 | **Compositionality**: sequential and branching composition preserves the inclusion. | Presupposes (a). Currently unrepresentable — `join` folds findings, not states. |
| O3 | **Fixpoint / convergence**: post-fixpoint soundness (`F#(Y#) ⊑ Y# ⟹ lfp F ⊆ γ(Y#)`), plus a widening `∇` on infinite-height domains. | This is deferred item (d) restated. `loop_bounds_unknown` is the placeholder. |
| O4 | **Non-triviality**: precision must be maintained for uncompromised operations, or the whole thing degenerates to the trivial analyzer. | This is what makes (f) matter at all. |
| O5 | **(vacuous case)** *nothing*. No concrete semantics, no domain, no Galois connection, no fixpoint. | Free — which is the point, and the danger. |

**The concrete answer to "how expensive is soundness for us":** O1–O3 are all gated on (a) and are
genuinely expensive. **O0 — the obligation the table above does not contain, because it sits below the
domain — is cheap and is the one that actually binds us.** From nlm-3, the three conditions to
discharge before any tool may output "proved safe":

1. **Syntactic obligation exhaustion.** Every operation inducing a precondition is mapped to a proof
   obligation; no syntactic pattern is silently dropped. If the target or state of a receiver cannot
   be resolved, the obligation is registered as *unresolved*, **not omitted**.
2. **Sound abstract inductive invariant** (`lfp F ⊆ γ(M#)`).
3. **Total abstract entailment** at every obligation site: `M#(c) ⊑# α(Pre(c))`.

Condition 1 is a property of our AST pass and costs one refactor (allow-list → exhaustive traversal
plus explicit unhandled token). Conditions 2 and 3 are (a)+(c)+(d). **The cheap condition is the one
we currently fail.**

The literature is also explicit that condition 1 lives in the **trusted computing base**: the property
extractor is inside the TCB, because if extraction is weaker than reality
(`S_extracted ⊃ S_actual`), proving `γ(M#) ⊆ S_extracted` does **not** prove `γ(M#) ⊆ S_actual`.
[notebook: nlm-3]

---

## Q3 — The soundness fence (highest-value section)

### What the fence is fencing

§7.4's hazard, restated in the literature's vocabulary: our derived contract table is a
**specification extraction step inside the TCB**, and it is known-incomplete in a way that is
*invisible in its own output*. A method whose closure reports `unresolved_calls: []` has not been
shown to have no preconditions; it has been shown that the survey's allow-list never fired. The gap
ledger's rename `methods_fully_derived → methods_with_no_recorded_gap` already encodes this honestly
[our code: `.praxia/docs/specs/260901_plr-jit-pre-corpus-spec.md:1218-1240`], but the honesty is in a
*name*, not in a *gate*. The fence turns it into a gate.

### Grounding

The fence must assert the literature's three conditions, plus Astrée's fourth (scope declaration).
[notebook: nlm-3, nlm-5, nlm-4]

Astrée's soundness is never claimed in a vacuum — it is relative to (i) an enumerated target error
class (absence of run-time errors: division by zero, overflow, invalid FP, out-of-bounds indexing —
*not* functional correctness), (ii) a restricted language subset `L_snd` (no dynamic allocation, no
unbounded recursion, no complex pointer arithmetic, no OS calls, no unrestricted concurrency), (iii)
hardware/compiler/environment hypotheses, and (iv) the "error-state cut": soundness applies *up to
the first unproved alarm*. Rival & Yi formalize this as **Theorem 6.1, Soundness Under Assumption**,
over subsets `L_snd` of programs and `E_snd` of executions. An unsupported construct is an
**assumption violation** — it falsifies the theorem's premise, so a subsequent "proved safe" is "not
a formal proof — it is an unverified assumption." [notebook: nlm-3, nlm-5]

### Proposed fence — `may_emit_safe(method, pin) -> bool`

Five assertions. F1–F3 are the literature's conditions specialized to our pipeline; F4 is Astrée's
scope declaration; F5 is a calibration requirement (my addition, not settled by the literature — see
below). **No SAFE finding may be constructed for any operation whose target method fails any of
these.** Implement as a hard precondition inside the single function permitted to construct a
`Finding(verdict=SAFE)`, not as a test — a test can be skipped, a precondition cannot.

---

**F1 — Obligation coverage is total *and proved*, not assumed.**

> For method `M` and PLR pin `P`, let `candidate(M)` be the set of `PlrSite`s produced by an
> independent, exhaustive stdlib-`ast` traversal of `M`'s transitive-closure bodies that visits
> **every** `ast.Call` node and every attribute load, with **no receiver-shape filter of any kind**.
> Let `recorded(M)` be the set of sites the survey/derivation actually turned into either a derived
> obligation or an explicitly recorded gap token.
>
> **Assert `candidate(M) ⊆ recorded(M)`.** Sites in `candidate(M) \ recorded(M)` are the *silent
> drop* population and must be empty.
>
> **Then assert `unhandled(M) = ∅`**, where `unhandled(M)` is the subset of `recorded(M)` carrying a
> gap token rather than a discharged obligation.

Two separate assertions on purpose, and the ordering matters. The first says *we saw everything*; the
second says *everything we saw is discharged*. The current pipeline can only ever assert something
like the second, over a population defined by the very filter that causes the problem.

*Implementation note — this is a strictly stronger requirement than the T6 counter as specified.*
T6's counter uses the corrected predicate "`func` is `ast.Attribute` AND NOT (`func.value` is
`ast.Name` with `id == "self"`)" [our code:
`.praxia/docs/specs/260901_plr-jit-pre-corpus-spec.md:1229-1231`]. That is a *hand-enumerated pattern
for the dropped population* — the same class of construct that caused the bug. F1 must instead be a
**set difference against the recorded set**, so that a receiver shape nobody has thought of yet lands
in the residual automatically. Concretely, `derive` must start emitting site sets, not just counts:

```
DerivedContract.obligation_sites: frozenset[PlrSite]
DerivedContract.unhandled_sites:  frozenset[PlrSite]   # explicit gap tokens
# and, from the independent pass:
candidate_sites(method, pin) -> frozenset[PlrSite]
```

`PlrSite` already carries `(file, lineno, qualname)` and is hashable and frozen
[our code: `plr-jit/src/plr_jit/verdict.py:74-80`], so it is usable as the set element with no schema
change. This is the literature's prescribed refactor verbatim: "change the AST visitor from an
**allow-list of supported receiver patterns** to an **exhaustive traversal of all call nodes**", with
unsupported shapes generating "an explicit unhandled-obligation token that resolves to UNKNOWN."
[notebook: nlm-3]

**F2 — Every generated obligation is discharged by entailment, not by absence.**

> For every obligation `o ∈ obligation_sites(M)`, the analysis state at `o` must entail `Pre(o)`
> (`M#(c) ⊑# α(Pre(c))`). Operationally in v1 terms: **no reason in the closure of `M` may be a
> precision-class reason.** In particular `guard_predicate_unparsed`, `loop_bounds_unknown`, and
> `argument_not_static` anywhere in `M`'s closure block SAFE for every operation targeting `M`.

Note that a method with *zero* obligations is legitimately SAFE — but only because F1 established
there are no hidden ones. F1 and F2 are not independent; F2 without F1 is exactly the §7.4 hazard.

**F3 — Closure termination by exhaustion, not by cap.**

> The transitive `delegates_to` closure for `M` terminated with an empty unresolved frontier **and**
> was not truncated by a depth or node budget. Assert `closure.truncated is False` and
> `closure.unresolved == ()`.

A depth-capped closure is category (C) again, one level up: the untraversed frontier generates no
obligations and leaves no gap token unless the cap is explicitly recorded as one. §7.2's
frontier-carried `depth` makes this checkable
[our code: `.praxia/docs/specs/260901_plr-jit-pre-corpus-spec.md:1793`].

**F4 — SAFE is machine-readably scoped (soundness under assumption).**

> A `SAFE` verdict is never emitted bare. It is emitted only alongside a `SoundnessScope` record,
> carried on `AnalysisReport`, that enumerates:
>
> - the PLR pin (already in `SurveyStamp` — reuse, do not duplicate);
> - the **target failure class**: the subset of `FAILURE_CATEGORIES` for which obligations are
>   generated at all. Anything outside it is out of scope of the claim, exactly as Astrée's A-RTE
>   class excludes functional correctness;
> - the **excluded language subset** `L_snd^c` — the Python constructs under which the extraction is
>   known not to hold. At minimum: `getattr`/`setattr` and reflective dispatch, monkeypatching,
>   `**kwargs` forwarding into an unresolved callee, and the backend `send_command` transport
>   boundary (750/967 = 77.6% of unresolved entries
>   [our code: `.praxia/docs/specs/260901_plr-jit-pre-corpus-spec.md:1243-1245`]);
> - the **environment hypotheses**: which backend, simulated vs. real, and any deck-state
>   preconditions assumed rather than checked.
>
> The claim the user is entitled to read off a SAFE is then: *"no precondition statically derivable
> from PLR source at pin P, within failure class C, is violated, assuming the program contains no
> construct in `L_snd^c`."* Never "this will work."

This is the assertion I would fight hardest for. §7.4 says an unqualified SAFE would be unsound; the
Astrée precedent says the fix is not to make SAFE stronger but to make the *claim attached to SAFE*
explicit and narrow. It is also the only fence assertion that is cheap **and** immediately reduces
what a downstream consumer can over-read. [notebook: nlm-3, nlm-4]

**F5 — The fence must be shown capable of failing (planted-precondition control).**

> Before the first SAFE ships: take a method that F1–F4 would clear, and in a scratch copy of PLR
> inject a synthetic guard behind a receiver shape the survey historically dropped (canonically
> `self.head[channel].get_tip()` — the shape §7.4 flags as the plausible home of most tip
> preconditions). Assert the fence flips to blocking. Repeat for at least one shape *not* matching
> T6's corrected predicate (e.g. a call on a local alias, or a nested field expression), to
> demonstrate F1's set-difference form is doing work the pattern form would not.

**This one is not settled by the literature** — I did not find a named precedent for it in the corpus,
and I am not going to manufacture one. It is a direct application of the project's own measurement-
pipeline rule (`~/.claude/rules/BATHOS.md`: verify the instrument against synthetic ground truth
before trusting a conclusion) to a fence whose entire failure mode is *silence*. Treat as a strong
recommendation, not a literature finding. Its justification is structural: F1 asserts the absence of
something, and an absence-assertion that has never been observed to fire is indistinguishable from a
no-op.

---

### The one-line fix that is available today, before any of this

`join` returns `SAFE` for zero findings [our code: `plr-jit/src/plr_jit/verdict.py:138,152`]. It is
guarded only by §7's totality guarantee, and the docstring says so — "if that totality guarantee is
ever relaxed, this row becomes live." But AC-7.2 in round 1 asserts only the per-method
never-raises property, and the actual `len(findings) >= len(operations)` coupling check is deferred
to AC-6.3 in T8 [our code: `.praxia/docs/specs/260901_plr-jit-pre-corpus-spec.md:1383-1396`]. So for
the whole of T3→T8 the coupling that makes zero-findings-⇒-SAFE safe is *asserted nowhere*, and the
default direction of the failure is toward SAFE.

This is the fence's failure mode in miniature and it costs one line: **make the empty case `UNKNOWN`,
or require an explicit positive SAFE finding to conclude SAFE.** The literature's fail-closed
principle applies directly [notebook: nlm-3, nlm-5]. Doing this does not preempt deferred item (a) —
the domain will replace `join`'s body regardless — and it removes a latent unsoundness from a
sound-by-construction v1.

---

## Q4 — Precision / false-positive targets

### What the literature settles

**Do not set a percentage target.** Miné, *The Octagon Abstract Domain* §6.1, as reported: on a
400 kLOC program with hundreds of thousands of check sites, an analyzer at **99% selectivity still
emits thousands of alarms**. For certification work every alarm must be manually discharged by formal
argument, so a percentage that sounds excellent is operationally worthless. The literature's stated
rule of thumb for a sound verification tool is an **absolute count: zero, or at most a handful a
small team can triage.** [notebook: nlm-4]

**The denominator is genuinely ill-defined.** Both natural choices are pathological
[notebook: nlm-4]:
- *false alarms / total alarms* — a near-perfect analyzer that emits exactly one spurious alarm on a
  bug-free program scores a 100% false-positive rate.
- *false alarms / total obligations (selectivity)* — inflates the score by padding the denominator
  with thousands of trivially-safe operations.

**Measuring at all requires triage, and triage is not free.** A sound analyzer has no false negatives
by construction, so the FP rate is the only quality axis; but whether a given alarm is true or
spurious is undecidable in general and must be settled by manual invariant inspection,
counterexample search/directed testing, or a **backward analysis from the error state** — where
reaching program entry with `⊥` is a *proof* the alarm was abstraction-induced. [notebook: nlm-4]

**Count root causes, not alarms.** Imprecision cascades: one early loss corrupts every downstream
invariant and produces a cluster of dependent alarms; fixing one root cause can delete hundreds.
Modern triage frameworks therefore measure by **alarm clusters / root causes**, with two formal
groundings: Rival, *Understanding the origin of alarms in Astrée* (SAS 2005), which partitions
alarms into **primary** (precision first lost) and **secondary** with a sound dependency ranking; and
Lee, Lee, Kang, Heo & Yi, *Sound non-statistical clustering of static analysis alarms* (TOPLAS 2017),
which groups by abstract def-use chains with a soundness guarantee that fixing one member addresses
the whole cluster. [notebook: nlm-4, nlm-5]

**Astrée's zero-alarm result was not achieved by generic automation.** It came from specializing the
analyzer to a *program family* — synchronous reactive fly-by-wire C, no `malloc`, no recursion, no
unions, no unconstrained pointer arithmetic, no third-party library calls, single-threaded,
periodic `while(1){wait_clock(); step();}` — plus per-program user directives. The authors state
plainly that a sound, fully automatic, zero-alarm analyzer for arbitrary C is impossible (Rice).
[notebook: nlm-4] [web: https://www.astree.ens.fr/ — zero false alarms on A340 primary flight control,
development Nov 2001 → Nov 2003; the frequently-cited 132 kLOC figure was **not** confirmed by the
sources I reached, so do not quote it] [web: https://www.astree.ens.fr/papers/astree_airbus_sas2007.pdf]

### Which Astrée levers are available to us in v1

| Astrée technique | needs | available to plr-jit v1? |
|---|---|---|
| Specialized domains + reduced product (octagons, FP linearization, filter domains, variable packing) | expression syntax, types, variable co-occurrence | **No** — presupposes (a). |
| Trace / control partitioning | branch points *as predicates*, plus split/merge directives | **No** — guards are opaque strings; blocked by (c). This is the single biggest precision lever we cannot pull. |
| Context sensitivity (semantic inlining; possible because recursion was banned) | static call graph, call-site chains | **Yes — we already have it.** §7.2's transitive `delegates_to` closure *is* a context-sensitive inlining walk. Worth naming as such rather than reinventing later. |
| Loop unrolling + widening with thresholds + narrowing | loop heads, guards, syntactic constants | **No** — this *is* deferred item (d). |
| User directives / annotations (`__ASTREE_unroll`, partition ranges) | pragmas, config, hardware model | **Mechanically yes, politically no** — collides head-on with decision 2 and the §9 budget. See R5. |
| Specialization to a program family | conformance to a coding subset | **Yes, and partly done** — `SUPPORTED_TOOLS` (10 methods) is already a family restriction; it is currently framed as scope-limiting rather than as the precision mechanism it actually is. |
| Primary/secondary alarm ranking (Rival SAS 2005) | dependency structure over alarms | **Yes, cheaply** — `top_unresolved`'s `blocks_methods` ranking is already a crude primary-alarm ranking. Reframing it explicitly costs nothing and gives the corpus work a principled worklist ordering. |

### What (f) should actually say

The spec's instinct at AC-7.4 and AC-8.3 — *publish figures, set no thresholds* — is **endorsed by the
literature**, not merely tolerated by it, and for a reason the spec does not state: the percentage
form of the target is meaningless at any scale we will reach, and the denominator is undefined.

But (f) is more answerable than "meaningless before (a) and (b)". The *shape* of a meaningful target
is settled even though the number is not:

> On a named, frozen benchmark set B (the 10 `SUPPORTED_TOOLS` × the differential-harness protocol
> corpus) at PLR pin P, the target is an **absolute count of UNKNOWN root causes** (clusters, not raw
> findings), set **after** the first T6 measurement, never before.

Two caveats I want on the record. First, "false positive" still has no referent for us: while every
verdict is UNKNOWN there are no positives to be false. The measurable quantity in v1 is **coverage**
(how many obligations we can discharge), not precision. Second, the differential harness's >50%
conflict rule [our code: `.praxia/docs/specs/260901_plr-jit-pre-corpus-spec.md`, RISK-7] is a
pre-registered *interpretation*, not a precision target — it is doing a different job and should not
be conflated with (f).

---

## Q5 — Is the mechanical reason vocabulary the right shape?

### What the literature settles

**Yes to mechanical, and the boundary table's prediction was right.** But the literature identifies
**one** semantic distinction that is categorical, consequential, and *not* optional — and our eight
reasons currently straddle it without marking it. [notebook: nlm-5]

| | (i) unsupported construct / coverage warning | (ii) alarm / unproved obligation |
|---|---|---|
| formally | `p ∉ L_snd` or `e ∉ E_snd` | `p ∈ L_snd`, but `M# ⋢ α(Safe)` |
| where | front end, AST surveyor, extractor | fixpoint engine / VC evaluator |
| means | "the analyzer does not know what this code means" | "the analyzer knows what it means but the abstraction is too coarse" |
| **soundness** | **threatens the soundness theorem** unless the tool fails closed | **preserves soundness** — this is correct behaviour for an incomplete analyzer |

Sorting our vocabulary [our code: `plr-jit/src/plr_jit/verdict.py:50-71`]:

- **coverage class (i)** — `no_contract_derived` (no obligations generated at all),
  `unresolved_delegate` (closure frontier unexplored), `receiver_type_unknown`,
  `unsupported_tool` (explicitly out of scope — the honest case), `internal_error`.
- **precision class (ii)** — `guard_predicate_unparsed`, `loop_bounds_unknown`,
  `argument_not_static`.

Two of these are arguable — `guard_predicate_unparsed` is "the predicate language does not cover this
shape", which reads as coverage of a *sub-language* even though the obligation was generated. The
discriminator that resolves it, and the one I would specify: **was the obligation generated? If yes →
precision. If the obligation was never generated → coverage.** By that rule
`guard_predicate_unparsed` is precision (the guard was found; we could not parse it) and
`no_contract_derived` is coverage.

**No to a full cause taxonomy.** The corpus does enumerate the standard cause taxonomy (unmodeled
environment, join/non-convexity, missing relational information, widening extrapolation, heap
smudging, non-linear arithmetic) — but it also says attributing an alarm to a *unique* cause is
"fundamentally undecidable and partially non-unique", an artifact of the iteration strategy rather
than a property of the source. Formal grounding exists only via backward analysis or sound clustering,
neither of which we can run. **Adding a semantic cause field now would be manufacturing a commitment
the literature says is not well-founded.** [notebook: nlm-5]

### New field, or `Finding.detail`?

**Neither.** `detail` is explicitly "NEVER parsed by any consumer"
[our code: `plr-jit/src/plr_jit/verdict.py:99`], so it cannot carry a bit the fence has to read — a
gate reading `detail` would silently break the contract that makes `detail` free-form. But a new
`Finding` field is also unnecessary, because **the coverage/precision class is a total function of
`reason` alone**: §3.3 already establishes that each reason corresponds to exactly one give-up site in
`plr_jit.derive`. So:

```python
# module-level, alongside REASON_VOCABULARY
REASON_CLASS: Mapping[str, Literal["coverage", "precision"]] = {...}
```

with a test asserting totality over `REASON_VOCABULARY` (the same shape as the existing reverse-
reachability test). Zero wire-contract change, zero consumer change, no new `Finding` field, and it
is exactly what the boundary table already predicted: *"(b): reasons stay; a separate soundness
annotation may be added alongside."*
[our code: `.praxia/docs/specs/260901_plr-jit-pre-corpus-spec.md`, boundary summary row §3.3]

The fence needs this: F1/F2's distinction between "we never saw it" and "we saw it and could not
prove it" is precisely the coverage/precision split, and without a machine-readable class the fence
would have to hard-code a reason list — a second hand-maintained surface that would drift from
`REASON_VOCABULARY`.

---

## Recommendations

### Safe to specify now

**R1 — Restate deferred item (b) along the literature's axis.** Replace "sound over-approximation vs.
bail-out" with the two questions that actually differ: *(b1) does a give-up propagate as ⊤ through
the abstract state?* (genuinely blocked on (a)) and *(b2) is the proof obligation generated at all?*
(**not** blocked on (a) — it is a front-end/TCB property, decided by T6's code today). Keep (b1)
deferred; promote (b2) to in-scope. Grounding: nlm-1, nlm-2, nlm-3.

**R2 — Close the `join` empty case.** Zero findings ⇒ `UNKNOWN`, or require an explicit positive SAFE
finding. One line, no dependency on any deferred item, removes a latent unsoundness whose only
current guard (AC-7.2's totality coupling) is not actually asserted until T8/AC-6.3. Grounding: the
fail-closed principle, nlm-3/nlm-5; the coupling gap is visible in the spec text itself.

**R3 — Specify the fence as F1–F4 (defined in Q3), and make it a precondition on SAFE construction,
not a test.** F1 must be a **set difference against the recorded set**, not a hand-enumerated dropped-
shape predicate — this is the difference between the fence and a slightly better version of the bug.
It requires `DerivedContract` to expose `obligation_sites` / `unhandled_sites` as `frozenset[PlrSite]`
and an independent exhaustive-traversal pass to expose `candidate_sites`; `PlrSite` is already frozen
and hashable, so no schema change is needed. Grounding: nlm-3 (three discharge conditions, fail-closed
front ends, extractor-is-in-TCB), nlm-5 (coverage vs. alarm), nlm-4 (Astrée's scope qualification).

**R4 — Add `REASON_CLASS: Mapping[str, "coverage"|"precision"]` beside `REASON_VOCABULARY`, with a
totality test.** No new `Finding` field, `detail` untouched, wire contract unchanged. This is the
"separate soundness annotation alongside" the boundary table already anticipated, and the fence needs
it. Do **not** add a full semantic cause taxonomy — the literature says unique root-cause attribution
is undecidable without backward analysis or sound clustering. Grounding: nlm-5.

**R6 — Reframe (f) as an absolute root-cause count on a frozen benchmark, set after measurement.**
Explicitly forbid percentage targets in the spec, citing the selectivity paradox. Keep AC-7.4 and
AC-8.3 threshold-free — the literature endorses that choice. Also reframe `top_unresolved`'s
`blocks_methods` ranking as a primary-vs-secondary alarm ranking (Rival SAS 2005) so the corpus
worklist has a principled ordering. Note in the spec that in v1 the measurable quantity is
**coverage**, not precision, because there are no positives yet. Grounding: nlm-4, nlm-5.

**R7 — Name `SUPPORTED_TOOLS` as a program-family specialization, not merely a scope limit.** Astrée's
zero-alarm result depended on family restriction; ours is the closest structural analogue we have and
is currently under-exploited in the spec's own reasoning. Grounding: nlm-4.

### Needs a decision from the user

**R5 — Decision 2 versus the Astrée precedent.** Astrée did not reach zero alarms by automation
alone: it required end-user directives (`__ASTREE_unroll`, partition ranges), hardware/environment
models, and per-family specialization. Decision 2 ("no hand-written method contracts") plus the §9
shrinking budget forbid the analogue. These are not obviously reconcilable, and the tension is a
strategic one, not a spec-drafting one. Note the narrow reading is already available — §0.1's scope
note distinguishes hand-written *contract bodies* (banned) from hand-maintained *derivation
machinery* (permitted, budgeted), and an Astrée-style directive is arguably machinery. Whether to
lean on that reading, and how much directive surface to budget, is a call I should not make.
Grounding: nlm-4, and `.praxia/docs/specs/260901_plr-jit-pre-corpus-spec.md` §0.1 / §9.

**R8 — F5 (the planted-precondition control) is my recommendation, not a literature finding.** I found
no named precedent for it in this corpus and did not go looking for one outside. It is an application
of the project's own instrument-verification rule to a fence whose failure mode is silence. Adopting
it costs one scratch-copy mutation test before the first SAFE; declining it means F1's absence-
assertion ships never having been observed to fire.

### Explicitly not recommended

- Do **not** add a semantic root-cause taxonomy alongside the mechanical reasons (Q5, nlm-5).
- Do **not** set any percentage-based precision or false-positive target (Q4, nlm-4).
- Do **not** quote "132,000 lines" for the Astrée/A340 result — I could not confirm it from the
  sources reached [web: https://www.astree.ens.fr/]. The confirmable claim is: zero false alarms on
  Airbus A340 primary flight control software, development Nov 2001 → Nov 2003.

---

## What remains genuinely open

1. **Whether (b1) has a *useful* answer for us at all.** Our "state" is deck/tip typestate, not
   numeric. Whether ⊤-propagation is the right mechanism for typestate — versus a typestate-specific
   lattice where the give-up element is not the same object as the join of all states — is a question
   about deferred item (a) that this corpus (numeric-domain heavy) does not settle.
2. **Whether F1 is achievable at acceptable cost.** An exhaustive traversal with a fail-closed
   unhandled token will, on first run, produce a very large `unhandled_sites` for every method — quite
   possibly making F1 unsatisfiable for all 10 `SUPPORTED_TOOLS` indefinitely. That is the *correct*
   outcome (it is the honest measurement RISK-1 asks for), but it means the fence may block SAFE for a
   long time. I have not estimated the size; T6's counter will.
3. **The relationship between F1 and RISK-1.** If F1's residual is large, RISK-1's "invalidates the
   approach" branch fires. The fence and the risk are measuring the same thing from opposite ends, and
   the spec does not currently connect them.
