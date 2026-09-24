---
title: 'plr-sema deferred items (a),(d): literature adjudication'
description: 'Research subagent output (260901) adjudicating deferred semantic questions (a) and (d) against the abstract-interpretation/typestate corpus; R3 (join grouped by operation_id) was later found to be wrong and is recorded as must-not-implement in the spec.'
status: final
task_id: 260901_plr-jit-research-a-d
date: '260901'
confidence: ''
sources: ''
---
# Deferred items (a) and (d): literature adjudication

task_id: 260901_plr-jit-research-a-d · date: 2026-09-01 · agent: research (no code written, `src/` untouched)

## Source ledger

Notebook `8f1e2dda-0b5d-44d2-bcb2-2a8459b1a28c` — 16 sources (listed, not 17). Relevant to this
report: Miné *Octagon*; Miné *Tutorial on Static Inference of Numeric Invariants*; Nielson/Nielson/Hankin
*PPA*; Kildall POPL'73; Nielson & Nielson *Semantics with Applications*; Cousot *Basic Concepts* (WCC 2004);
Cousot & Halbwachs POPL'78; Rival & Yi *Introduction to Static Analysis*; Sagiv/Reps/Wilhelm *Parametric
Shape Analysis via 3-Valued Logic*; DeLine & Fähndrich *Vault* (PLDI 2001); Bierhoff & Aldrich *Modular
Typestate Checking* (OOPSLA 2007); Aldrich et al. *Typestate-Oriented Programming* (OOPSLA 2009);
Jones *Partial Evaluation*; Wadler *Linear Types*; Honda et al. ESOP'98; plus one unrelated JAX PDF.

Spill files (each holds the full upstream payload incl. every `cited_text`):

| ref | spill path | grounding |
|---|---|---|
| **S1** | `.praxia/nlm/260901-141200__in-abstract-interpretation-and-dataflow-analysis__9b7e89ff.json` | 56 refs, 7 sources |
| **S2** | `.praxia/nlm/260901-141346__consider-a-three-element-set-of-analysis-outcome__9b7e89ff.json` | 21 refs, 5 sources |
| **S3** | `.praxia/nlm/260901-141449__when-the-analysis-question-is-not-what-numeric-r__9b7e89ff.json` | 36 refs, 6 sources |
| **S4** | `.praxia/nlm/260901-141618__what-is-the-bottom-element-of-an-abstract-domain__9b7e89ff.json` | 35 refs, 4 sources |
| **S5** | `.praxia/nlm/260901-141657__loop-handling-what-exactly-does-a-widening-opera__9b7e89ff.json` | 50 refs, 4 sources |
| **S6** | `.praxia/nlm/260901-141819__distinguish-two-different-aggregations-in-a-stat__9b7e89ff.json` | **0 refs, 0 sources — UNGROUNDED** |
| **S7** | `.praxia/nlm/260901-142003__using-the-typestate-sources-deline-f-hndrich-s-v__9b7e89ff.json` | 63 refs, 5 sources |

**Adversarial note on S6.** The single query whose answer is most load-bearing for Question 1 —
the (A) control-flow-join vs. (B) obligation-summarization distinction — came back with
`references: 0, citations: 0, sources_used: 0`. NotebookLM answered from model priors, not from
the corpus. Every claim I take from S6 is therefore labelled `[notebook-UNGROUNDED]` and I have
re-derived or independently grounded each one before relying on it. The one checkable factual
claim in S6 — that Rival's SAS 2005 paper "Understanding the Origin of Alarms in Astrée" exists
and concerns cascading alarms / semantic slicing — verifies
`[web: https://www.di.ens.fr/~rival/papers/sas05.pdf]`, but the paper is **not** in the corpus, so
S6's Astrée claims are outside this notebook's evidence base. The reachability half of the same
argument *is* grounded, in S7 §4, from Rival & Yi.

---

## Question 1 — Is a flat finding multiset rich enough to survive a real abstract domain?

### Headline

**The spec's verdict is right, its reasoning is wrong, and the wrong reasoning understates one
migration cost while overstating another.**

- Right: `Finding`'s field set survives. I found nothing in the corpus that requires a new
  `Finding` field.
- Right: `join`'s signature must change.
- **Wrong reasoning:** the stated reason — *"a real lattice join operates over abstract states at
  control-flow merge points, not over a flat finding list"* — is **false as a general claim about
  lattice joins**, and it is **not the reason `join` must change**.

### What the literature settles

**A join over a flat set of facts is a perfectly ordinary lattice join.** [notebook: S1 §2]
Reaching definitions is `(P(Var × Lab), ⊆)` with join = set union; live variables is `(P(Var), ⊆)`
with union; available expressions is `(P(AExp), ⊇)` with intersection. None of these carries a
per-variable environment; an element is literally "a set of facts currently known to hold."
Flow-insensitive pointer analysis goes further and merges a single global fact base with *no
CFG merge joins at all* [notebook: S1 §2.2]. So "flat multiset ⇒ not a real lattice" does not
hold, and the spec should not rest on it.

**The actual reason `join` must change is a category distinction.** There are two aggregations in
any analyzer, and §3.2 conflates them [notebook-UNGROUNDED: S6 §1–2; reachability half grounded in
notebook: S7 §4]:

- **(A) Control-flow confluence** — `⊔`, at a CFG merge point, combining abstract states arriving
  along alternative paths at the *same* program point. Over-approximates the union of concrete
  states. This is Kildall's meet-of-pools and NNH's MFP equation
  `Entry(ℓ) = ⨆_{ℓ' ∈ Pred(ℓ)} f_{ℓ'}(Entry(ℓ'))` [notebook: S1 §3–4].
- **(B) Verification-result summarization** — collapsing per-check-site results into one
  whole-procedure verdict. This is a **conjunction over independent proof obligations**,
  `Safe(P) ⟺ ⋀_{ℓ ∈ CheckSites} (M♯(ℓ) ⊑♯ α(Safe_ℓ))` — a different mathematical object at a
  different level, not a join over the state lattice.

`plr_jit.verdict.join` is (B). `[our code: plr-jit/src/plr_jit/verdict.py:129-152]` — its input is a
tuple of `Finding`s each keyed by a *distinct* `operation_id`, i.e. a set of per-check-site results,
not a set of states at one point.

**Therefore the boundary declaration's central sentence is inverted.** §3.2 says the join table is
*"the place deferred item (a) will attach."* It is not. When (a) lands, the abstract-domain join
`⊔♯` will be a **new function operating on abstract states inside the per-operation analysis**, and
it will not live in `verdict.py` at all. §3.2's `join` survives (a) as the obligation conjunction it
already is. The attachment point for (a) is upstream — wherever per-operation `Finding`s are
*produced*, which the spec does not name.

### Two concrete defects the flat multiset already has

Neither is about richness of `Finding`. Both are about `join` discarding structure that is already
in the data.

**D-A: `join` ignores `operation_id`, so it merges same-operation findings with the wrong operator.**
Today `join` computes `{f.verdict for f in findings}` — a set over the whole multiset, with
`operation_id` never read `[our code: verdict.py:147]`. Two findings for the *same* operation with
verdicts SAFE and WILL_FAIL (which is exactly what a branch produces once (a) lands) yield
WILL_FAIL. The correct within-operation merge is the **Kleene information join**: `0 ⊔ 1 = 1/2` —
neither definite value absorbs the other, and conflicting evidence yields "unknown"
[notebook: S2 §3A, grounded in Sagiv/Reps/Wilhelm]. Returning WILL_FAIL there asserts *"every
execution reaching this point fails"* when one branch is provably safe. That is unsound
[notebook: S2 §2B].

The fix is structural and cheap because `Finding.operation_id` already exists: group by
`operation_id`, apply the Kleene/diamond join **within** a group, apply the obligation conjunction
**across** groups. `Finding`'s field set does not change. `join`'s signature does not even have to
change for this part.

**D-B: `join` claims a must-error without a reachability proof.** "any WILL_FAIL → WILL_FAIL"
declares the protocol will definitely fail. Rival & Yi require **two** conditions for a definite
error at `ℓ`: local invalidation `γ(M♯(ℓ)) ∩ Safe = ∅` **and** a reachability proof
`Reachable(ℓ) ≠ ∅` [notebook: S7 §4]. A WILL_FAIL operation on a never-taken `false_branch` makes
the protocol verdict WILL_FAIL under the current table. *This* is what `join` needs the graph for —
not a merge topology, just reachability.

### What `join` concretely needs from the graph, and the migration cost

It needs less than "the graph." It needs, per `operation_id`:

1. **A reachability class** — unconditional / conditional / loop-body. Enough to distinguish
   "definitely executed" from "may be executed."
2. **A branch-exclusivity relation** — which operations sit on mutually exclusive arms, so a
   WILL_FAIL on one arm is not reported as a whole-protocol must-fail.

**The migration cost is not in `verdict.py`. It is in `check/graph.py`, and the spec has already
paid a hidden price there.** The upstream model carries exactly the needed fields —
`GraphNodeType.CONDITIONAL`, `condition_expr`, `true_branch`, `false_branch`
`[our code: praxis/backend/utils/plr_static_analysis/models.py:504-560]` — and the plr-jit
"derived-from-consumers" stdlib mirror **omits all four**
`[our code: plr-jit/src/plr_jit/check/graph.py:92-105]`. `ProtocolComputationGraph` mirrors only
`protocol_fqn`, a flat `operations` tuple, and a `resources` dict
`[our code: check/graph.py:126-140]`. So plr-jit currently **cannot see a branch at all**.

Two consequences worth stating plainly:

- The mirror's field-set justification ("derived from consumers") is self-fulfilling: it derives
  the field set from today's consumers, which are the ones that ignore control flow. Fork C's
  `test_mirror_fields_match_operation_node` (D8) will not catch this — it checks the mirrored
  fields still exist upstream, not that the mirror covers what a sound analysis needs.
- The migration for (a) therefore costs a **mirror field-set change plus a fixture regeneration**,
  not just a `join` body edit. That is a bigger, more visible diff than §3.2's boundary summary
  implies — but it is still additive and does **not** bump `schema_version`, since `AnalysisReport`
  is unaffected.

### What remains a judgment call

- Whether `join` should take `(findings, graph)` or `(findings, reachability_map)`. The literature
  is silent; it only says the reachability fact must exist. A narrow `reachability_map` keeps the
  "exactly one function aggregates" rule intact with a much smaller surface, and I lean that way,
  but this is a design preference, not a settled result.
- Whether the two aggregations should be two named functions (`merge_operation` + `join_report`)
  or one. The literature distinguishes them conceptually; nothing forces two functions.

---

## Question 2 — Is `{SAFE, WILL_FAIL, UNKNOWN}` a lattice under the §3.2 table?

### What the literature settles — and this one is decisive

**Yes, the table is a lattice join. Of the wrong lattice.** [notebook: S2 §1]

The operation `⊕` is:
- **Idempotent** — `x ⊕ x = x` for all three. ✓
- **Commutative** — the rule tests set membership, order-independent. ✓
- **Associative** — both bracketings reduce to "WILL_FAIL if present, else UNKNOWN if present,
  else SAFE." ✓
- **Has a unit** — `SAFE` is the unique identity (`x ⊕ SAFE = x` for all `x`). ✓

Associative + commutative + idempotent ⟹ join-semilattice. The canonically induced order
`x ⊑ y ⟺ x ⊕ y = y` gives a **3-element total chain**:

```
SAFE  ⊏  UNKNOWN  ⊏  WILL_FAIL
 ⊥                        ⊤
```

So `join` is a genuine lattice join, associative, commutative and idempotent — but **`WILL_FAIL` is
top and `SAFE` is bottom.** That is the exact opposite of the module's stated intent, which calls
UNKNOWN the value where "analysis established nothing"
`[our code: verdict.py:42]` — i.e. ⊤ semantics — while the table places UNKNOWN strictly *below*
WILL_FAIL.

**Why the two cannot both hold.** By definition ⊤ absorbs: `∀x. x ⊔ ⊤ = ⊤`. If UNKNOWN were ⊤ then
`WILL_FAIL ⊔ UNKNOWN = UNKNOWN`; the table says WILL_FAIL. Forcing `UNKNOWN ⊑ WILL_FAIL` forces
`γ(UNKNOWN) ⊆ γ(WILL_FAIL)` by monotone concretization, and since `γ(UNKNOWN)` contains safe
executions, `γ(WILL_FAIL)` would have to contain them too — breaking the Galois connection and
the soundness argument [notebook: S2 §2B, §3C].

**Is it monotone in the right direction for soundness?** Under the (A) reading — a state join — no.
Under the (B) reading — an obligation conjunction, "does any obligation fail?" — yes, and the
absorption is correct: if op1 definitely fails (and is reachable), the protocol definitely fails
regardless of op2's status. The table is *the right operator for the wrong-labelled job*.

**The structural defect is that `Verdict` is doing double duty.** The same three symbols are used
as (i) a per-finding state abstraction, where UNKNOWN must be ⊤, and (ii) a report-level obligation
summary, where WILL_FAIL absorbs. Those require **two different orders on the same carrier set**.
This is precisely the two-order structure Sagiv/Reps/Wilhelm formalize as a semi-bilattice: a
*logical* order and an *information* order, deliberately kept separate [notebook: S2 §3A].

**The correct state domain is not a chain.** It is the diamond `P({Safe, Fail})`
[notebook: S2 §3B]:

```
              UNKNOWN = ⊤ = {Safe, Fail}
                 /            \
      SAFE = {Safe}        WILL_FAIL = {Fail}
                 \            /
              UNREACHABLE = ⊥ = ∅
```

**This has four elements. `Verdict` has three — there is no ⊥.** A dead-code operation has no
representable verdict today. Adding `UNREACHABLE` is a change to `Verdict`, and `Verdict` is on the
wire inside `AnalysisReport` `[our code: verdict.py:117-126]`. The spec's boundary summary promises
"`Finding`'s fields do not change" but is silent on `Verdict` gaining a member — a `schema_version`
bump that §3.5 calls "the highest-consequence assumption in the document" is therefore reachable by
a route the boundary table does not cover.

### What remains a judgment call

- Whether to add `UNREACHABLE` now (cheap, pre-corpus, no persisted reports yet) or accept the
  later bump. Adding it now is free today and expensive later; but it is a real API decision.
- Whether to keep one enum with two documented orders, or split into two types. Splitting is
  cleaner and defeats the "exactly one function aggregates" simplicity the spec values.

---

## Question 3 — Which domains are candidates? (Do not assume octagons.)

### What the literature settles

**Numerical domains are needed only under four conditions** [notebook: S3 §2]:

1. Guard entailment requires **arithmetic generalization** (`assert x >= 0` where `x = y + 2`).
2. Guard depends on an **inductive loop-counter invariant** (`0 <= i < n` inside `for i in ...`).
3. Guard involves a **multi-variable relational offset** (`offset + len <= capacity`).
4. Guard involves **alignment or stride** (`ptr % 4 == 0` → congruence domain).

**Our guards match none of these as stated.** The reason vocabulary is state-shaped, not
arithmetic-shaped: `receiver_type_unknown`, `argument_not_static`, `unsupported_tool`
`[our code: verdict.py:50-71]`, and the whole `SUPPORTED_TOOLS` frontier is tip state on
`self.head[channel]` — "does the channel hold a tip", "is the container present". That is
**textbook typestate**: an object whose legal operations depend on its lifecycle state, with
method preconditions expressed as required incoming states
[notebook: S7 §1, from Vault / Bierhoff & Aldrich / Aldrich et al.]. Vault's own worked example is
`tracked file[f] [f: open → closed]` — structurally identical to `pick_up_tips`/`drop_tips` over a
channel's tip state.

**Cost/precision profile, worst-to-best fit for our question** [notebook: S3 §1]:

| framework | fit for "does this guard fire" | cost | verdict for us |
|---|---|---|---|
| Bit-vector dataflow | very coarse — syntactic matching only, no arithmetic | near-linear | too weak alone |
| **Typestate / property automata** | **exact for lifecycle/protocol guards** | finite-state, polynomial | **primary candidate** |
| Predicate abstraction over finite Π | exact for Boolean combinations of tracked predicates | exponential in \|Π\|; needs a decision procedure | **candidate for item (c)** |
| Intervals | scalar bounds `x ∈ [a,b]` | O(n) space/time; needs widening | only if volumes enter |
| Octagons | relational `±X ±Y ≤ c` | **O(n²) space, O(n³) time** | **not justified** |
| Polyhedra | general affine | worst-case exponential | not justified |

**Octagons are explicitly not indicated.** They buy relational constraints between *two* numeric
variables. I found no guard class in our frontier that is relational-numeric. The corpus centres on
octagons because of how it was assembled, not because our problem needs them. Adopting Miné's
domain here would be paying O(n³) closure for expressiveness we cannot use.

**Predicate abstraction is the right frame for deferred item (c), and its usual weakness does not
bite us.** Predicate abstraction's standard failure is the *predicate-discovery problem* — needing
CEGAR to synthesize the right Π [notebook: S3 §1(b)]. We do not have that problem: our Π is
**given**, by PLR's own `raise`/`assert` conditions, carried today as opaque strings in
`InlinedGuard.condition` with polarity already explicit in `kind`
`[our code: plr-jit/src/plr_jit/derive/__init__.py:260-287]`. Parsing them yields a finite,
enumerable predicate set. That is a materially easier problem than the literature's default case,
and it is worth saying so in the spec.

**If volume tracking is in scope, the minimal addition is intervals, not octagons.** Coxswain
already computes aggregate volume effects (`compute_aggregate_effect`,
`[our code: praxis/backend/core/simulation/bounds_analyzer.py:312]`). A guard like
`volume_remaining - volume >= 0` is *non-relational per well* — an interval over each well's volume
suffices. Octagons would only be needed if a guard related two wells' volumes to each other. I saw
no such guard.

**Combining typestate with a numeric domain, if it comes to that** [notebook: S3 §3]: the
literature offers the **reduced product** (tuple + a reduction operator ρ exchanging information
both ways, and propagating ⊥ coalescently) and the **reduced cardinal power** (`D♯_pred → D♯_num`,
partitioning the numeric state by predicate truth values, which eliminates the spurious-join
false alarm entirely). Cardinal power is the more precise and the more expensive.

### What remains a judgment call

- Whether volume preconditions are in scope for v1. This determines whether *any* numeric domain
  is needed. The literature cannot answer it; the SUPPORTED_TOOLS frontier can.
- Whether typestate is adopted as a *checking discipline* (Vault-style: reject at merge) or as an
  *abstract domain* (join to a common super-state). See Q2.

---

## Question 4 — Zero findings ⇒ SAFE, and the coupling to totality

### What the literature settles

**⊥ = ∅ = unreachable, always** [notebook: S4 §1]. `γ(⊥) = ∅`; asserting ⊥ at `ℓ` is a *proof* that
no execution reaches `ℓ`. Mapping "I collected no facts" to ⊥ is described as **catastrophically
unsound**, for two compounding reasons: (i) **vacuous safety** — `∅ ⊆ S` for every `S`, so the
unhandled construct is trivially "safe"; and (ii) **strictness** — `⟦C⟧♯(⊥) = ⊥`, so the entire
downstream path is pruned as dead code and every later crash disappears. "No information" must map
to **⊤**, not ⊥.

**`⨆∅ = ⊥` is a theorem, not a convention** [notebook: S4 §2]. Every element is vacuously an upper
bound of ∅, so the *least* upper bound of ∅ is the least element. **This makes our code
algebraically consistent and that is exactly the trap:** on the chain induced by the §3.2 table
(Q2), ⊥ *is* SAFE, so `join(()) → SAFE` is the mathematically correct empty join **of a lattice
whose bottom means "verified safe" rather than "unreachable."** The bug is not in the empty case; it
is inherited from the ordering. Fix the ordering and the empty case fixes itself — the empty join
would then return UNREACHABLE, which is both sound and informative.

**"No counterexample ⟹ safe" is sound only under a discharged totality obligation**, and the
literature specifies exactly three layers [notebook: S4 §3–4]:

1. **Syntactic exhaustiveness** — every AST node and control edge accounted for; unrecognized forms
   must *fail closed* and emit an obligation.
2. **Semantic totality** — every abstract transformer total and locally sound; unmodelled effects
   map to ⊤, never ⊥.
3. **Inductive post-fixpoint** — `F♯(M♯) ⊑♯ M♯` at every CFG cycle.

Only with all three does the contrapositive apply. Break any link and an empty alarm list is
"merely an unhandled exception in the proof itself."

**So the spec's instinct is right: coupling zero-findings-⇒-SAFE to a totality guarantee is the
correct structure.** The literature would endorse the coupling. It would not endorse the current
*strength* of it.

### Where the coupling is weaker than §3.2 claims — three gaps

1. **AC-7.2 covers only `SUPPORTED_TOOLS`, and only "never raises."**
   `[spec: 260901_plr-jit-pre-corpus-spec.md:1383-1396]` — it asserts `derive_contract` returns a
   `DerivedContract` for each of 10 names, per-method, *"not against an extracted graph."* It does
   not establish layer 1 (syntactic exhaustiveness over a real protocol).
2. **The real totality gate is AC-6.3, and it is deferred to T8** — the `len(findings) >=
   len(operations)` coupling check `[spec:1393-1394]`. Between T3 (where `join` ships) and T8, the
   zero-findings row is **live and unguarded**, contradicting §3.2's "unreachable in v1."
3. **`len(findings) >= len(operations)` does not imply every operation has ≥1 finding.** Ten
   findings on one operation and zero on nine others satisfies it. AC-6.4 only asserts
   `{operation_id}` is a *subset* of real node ids `[spec:1018-1022]` — the subset direction, not
   the covering direction. **Neither AC actually asserts surjectivity onto the operation set**,
   which is the property §3.2's argument depends on.

That third point is, in my judgement, a genuine hole rather than a nitpick: it is exactly the
"absence of proof attempts mistaken for proved absence" failure the literature names.

### What remains a judgment call

- Whether to fix this by strengthening the AC (assert
  `{f.operation_id for f in findings} == {op.id for op in graph.operations}`) or by making the empty
  case structurally impossible in `join`. The literature prefers making it impossible; the spec's
  test-driven style prefers the AC. Both are defensible; doing neither is not.

---

## Question 5 — Item (d): widening vs. an `items_x × items_y` trip-count heuristic

### What the literature settles

**Widening's two obligations** [notebook: S5 §1B]: (i) covering — `X ⊑ X∇Y` and `Y ⊑ X∇Y`; and
(ii) termination — for any `(Y_i)`, the sequence `X_0 = Y_0`, `X_{i+1} = X_i ∇ Y_{i+1}` stabilizes
in finitely many steps.

**What ∇ buys over the alternatives** [notebook: S5 §1A]: bounded unrolling to depth *k* cannot
soundly summarize iteration *k+1*; syntactic trip-count estimation fails on `break`, early return,
exceptions, conditional strides, and non-linear arithmetic. Widening ignores loop syntax entirely
and operates on the semantic abstract transition, stabilizing in 2–3 abstract steps whether the
loop runs 10 times or 10 billion [notebook: S5 §1A, §4].

**Minimum machinery** [notebook: S5 §2]: a feedback-vertex-set / loop-head cutset (Bourdoncle's
WTO on unstructured CFGs; loop heads suffice on structured code) so ∇ is applied only at cycle
cuts, not everywhere (indiscriminate widening destroys relational invariants); an iteration
strategy with **delayed widening** (plain `⊔` for the first N iterations); and a **narrowing** pass
`Δ` to recover the bounds ∇ shaved off.

**And now the decisive result for us** [notebook: S5 §3; S7 §1]:

> **Widening is required only when the domain has infinite ascending chains. Typestate domains have
> finite height and satisfy ACC. Standard Kleene iteration terminates in at most `height`
> iterations. "Widening operators (∇) are strictly unnecessary for typestate checking."**

Combining with Question 3: **if the domain is typestate (as the evidence indicates it should be),
item (d) largely dissolves.** There is no widening to design, no cutset algorithm, no narrowing
pass, no delayed-widening tuning. That is by a wide margin the most valuable finding in this
report, and it is grounded in five corpus sources.

**Sound loop handling without any bounds at all** [notebook: S5 §5] — implementable today over
`foreach_body`, with no numeric domain and no widening:

1. **Syntactic frame rule** — compute the write set `Mod` = every location mutated in the loop body
   (accounting for aliasing).
2. **Conservative havoc** — set every `v ∈ Mod` to ⊤.
3. **Preserve the frame** — every `u ∉ Mod` keeps its pre-loop abstract state. *This is the part a
   blanket `loop_bounds_unknown` throws away for free.*
4. **Apply the negated guard** on the exit edge, recovering bounds from `¬cond`.

We already have exactly the input step 1 needs: `foreach_body: tuple[str, ...]` is the set of
operation ids in the loop body `[our code: plr-jit/src/plr_jit/check/graph.py:104-105]`, and
`foreach_source` identifies the loop `[our code: check/graph.py:28]`. **The `foreach` nodes are the
widening points, handed to us for free** — the cutset problem the literature spends most of §2 on
does not arise, because the graph is already structured, not an arbitrary CFG.

### Our existing heuristic is worse than unsound — it is silently unsound

`[our code: praxis/backend/core/simulation/bounds_analyzer.py:155-165]`:

```python
if ".wells()" in loop_source or ".tips()" in loop_source:
    # Assume standard 96-well/tip
    return LoopBounds(..., exact_count=96, min_count=96, max_count=96,
                      is_bounded=True, inferred_from="default 96-item assumption")
```

and `[our code: bounds_analyzer.py:112-120]`:

```python
dims = DEFAULT_DIMENSIONS.get(resource_type, (12, 8))
```

A **guess** is returned with `is_bounded=True` and `min_count == max_count == exact_count` — the
data shape that signals "proved exactly," on a path whose own `inferred_from` string says
"default … assumption." An unknown resource type silently becomes a 12×8 plate. The literature's
sound degradation is *"if the loop exit cannot be **definitively proved**, fall back to ⊤"*
[notebook: S5 §4] — a guess presented as an exact count is the opposite move. Its cost is also
named: falling to ⊤ causes catastrophic precision collapse, forgetting invariants a widening would
have kept [notebook: S5 §4]. The frame rule above is how you avoid paying that in full.

Note this file is `praxis/backend/core/simulation/` — a *simulation* component, and the coxswain
copy at `coxswain/src/coxswain/fft/preconditions/bounds_analyzer.py` is near-identical. Using it for
simulation/UX is fine. Wiring it into a verdict path is not.

### What remains a judgment call

- Whether volume accumulation across a loop (`compute_aggregate_effect`) is in the verdict path.
  If it is, the frame rule havocs volume to ⊤ and every volume guard becomes UNKNOWN — at which
  point intervals + a trivial widening (`[a,b] ∇ [a',b'] = [a' < a ? -∞ : a, b' > b ? +∞ : b]`)
  become worth their cost. If it is not, no widening is ever needed.
- Whether to implement the frame rule now or keep the blanket `loop_bounds_unknown`. The blanket
  reason is sound; it is just needlessly imprecise. This is a precision/effort call, not a
  soundness one.

---

## Separating settled from unsettled

**Settled by the literature (high confidence, grounded in ≥4 corpus sources each):**

- A merge over a flat set of facts is a legitimate lattice join. The spec's stated reason for
  changing `join`'s signature is wrong. (S1)
- The §3.2 table is associative, commutative, idempotent, has SAFE as unit, and induces the total
  order SAFE ⊏ UNKNOWN ⊏ WILL_FAIL — with **WILL_FAIL as ⊤**, inverting the stated intent. (S2)
- UNKNOWN-as-⊤ and WILL_FAIL-absorbs-UNKNOWN are mutually exclusive; the latter breaks the Galois
  connection if read as a state join. (S2)
- The sound state domain for "safe / fails / don't know / unreachable" is the four-element diamond
  `P({Safe, Fail})`, not a three-element chain. (S2)
- ⊥ = unreachable; "no information" must map to ⊤; `⨆∅ = ⊥`; the three-layer totality obligation
  is what makes "no alarms ⟹ safe" sound. (S4)
- Numerical domains are needed only for arithmetic generalization, inductive counter invariants,
  relational offsets, or alignment. Octagons cost O(n²)/O(n³) and buy relational numeric
  expressiveness. (S3)
- Typestate domains are finite-height and **need no widening at all**. (S5, S7)
- A definite/must error requires both local invalidation and a reachability proof. (S7)
- Sound bound-free loop handling = write-set havoc to ⊤ + frame preservation + negated exit guard.
  (S5)

**Not settled — judgment calls for the user:**

- Whether `join` takes the graph or a narrow reachability map.
- Whether `Verdict` gains `UNREACHABLE` now or later (schema_version consequences).
- Whether volume preconditions are in v1 scope — this alone decides whether any numeric domain,
  and hence any widening, is ever needed.
- Whether typestate is adopted as a checking discipline (Vault: reject at merge) or as an abstract
  domain (join to common super-state). Vault emits a compile-time error on divergent merge and
  refuses to invent a ⊤ state; Bierhoff & Aldrich join to a common super-state or a linear
  disjunction requiring a dynamic test. (S7 §2) Both are in the corpus; they disagree; the corpus
  does not adjudicate for us.

**Where I could not get an answer:**

- The (A)/(B) aggregation distinction, which is the spine of Question 1, came back **ungrounded**
  (S6). I believe it, because it is re-derivable from S1's MFP equation (which is per-program-point)
  plus S7's reachability requirement (which is per-check-site), and because Rival & Yi's alarm
  discussion is the standard treatment of (B). But no corpus source states the distinction in those
  terms, and I will not claim it is settled by this notebook. If it matters enough to specify, it
  should be re-grounded against Rival & Yi §1.3/§6.3 directly, or the Astrée alarm-origin paper
  should be added to the notebook.
- Nothing in the corpus speaks to *lab-automation* preconditions specifically. Every mapping from
  the literature to our domain in this report is mine, not the corpus's.

---

## Spec-ready recommendations

### Safe to specify now

**R1 — Correct §3.2's boundary declaration's stated reason.**
Replace *"a real lattice join operates over abstract states at control-flow merge points, not over a
flat finding list"* with: the flat multiset is a legitimate lattice carrier (bit-vector frameworks
are exactly that); `join` must change because it is a **conjunction over per-operation proof
obligations**, not a control-flow confluence, and item (a)'s `⊔♯` will be a *new* function in the
per-operation analysis rather than a replacement for this one. Cite S1 §2, S2 §3.

**R2 — Document the two orders on `Verdict` explicitly, and stop calling the table "the join."**
The table is correct as an obligation conjunction and incorrect as a state join. Name it
`join_report` or `conjoin_obligations` and state in the docstring that the *information* order
(UNKNOWN = ⊤, per Kleene / Sagiv-Reps-Wilhelm) governs merging findings about the **same**
operation, while this function implements the **across-operation** obligation summary. This is a
docstring + rename, zero behavioural change, and it prevents the next reader from attaching (a) at
the wrong place.

**R3 — Make `join` group by `operation_id`.** Within a group, the Kleene information join
(`SAFE ⊔ WILL_FAIL = UNKNOWN`); across groups, the existing table. `Finding.operation_id` already
exists; `Finding`'s field set does not change; the change is pure and testable today. Add a test
case to `test_join_truth_table` for two findings sharing an `operation_id` — the current
parametrization over "multisets of ≤2 findings" almost certainly does not distinguish this.

**R4 — Strengthen AC-6.3 from a count to a covering.** Assert
`{f.operation_id for f in report.findings} == {op.id for op in graph.operations}`, not
`len(findings) >= len(operations)`. The count check is satisfied by ten findings on one operation.
This is the *only* thing standing between §3.2's zero-findings row and unsoundness, and it is
currently a proxy. (Note also that this gate lives in T8 while `join` ships in T3 — either move the
covering assertion earlier or say plainly in §3.2 that the row is unguarded until T8.)

**R5 — Fence `bounds_analyzer` out of the verdict path, normatively.** Add a line to the Deferred
table's (d) row: `bounds_analyzer.LoopBounds` may inform simulation and UX but must never produce
or upgrade a `Verdict`. Any operation with `foreach_source is not None` gets `loop_bounds_unknown`
unless a bound is *proved*. Grounded in the observation that
`bounds_analyzer.py:155-165` returns `is_bounded=True, exact_count=96` from a string named
"default 96-item assumption."

**R6 — Record in the Deferred table that typestate, not a numerical domain, is the indicated frame
for (a) — and that this makes (d) largely moot.** Typestate domains are finite-height, satisfy ACC,
and need no widening (S5 §3, S7 §1). The (d) row currently reads *"widening is a lattice operation
and presupposes (a)"*; it should read that widening is required only if (a) selects a domain with
infinite ascending chains, which the evidence suggests it should not.

### Needs a decision from the user

**R7 — Add `UNREACHABLE` to `Verdict` now, or accept a later `schema_version` bump?**
The sound domain is the four-element diamond; `Verdict` has no ⊥. Adding it pre-corpus is free —
no persisted reports exist. Adding it after v1 ships bumps the wire contract, which §3.5 calls the
document's highest-consequence assumption. **The boundary summary does not currently cover this
route to a bump**, which is itself worth surfacing regardless of the decision.

**R8 — Is volume tracking in the v1 verdict path?**
This single question decides whether any numeric domain is needed, and hence whether widening is
ever needed. If no: typestate only, no widening, (d) closes. If yes: add **intervals** (not
octagons — no relational-numeric guard was found) plus a trivial interval widening, combined with
typestate via a reduced product. I cannot answer this from the spec; the SUPPORTED_TOOLS guard
inventory can.

**R9 — Vault-style rejection or Bierhoff-Aldrich-style state join at divergent merges?**
Vault emits a compile-time error and refuses to invent a ⊤ state, forcing the programmer to make
the uncertainty explicit; Bierhoff & Aldrich join to a common super-state or a linear disjunction
`(available ⊕ end)` discharged by a dynamic test. Both are in the corpus and they genuinely
disagree. Given that our consumer is an analyzer over *other people's* protocols and not a type
system users write against, I lean Bierhoff-Aldrich (join to ⊤ = UNKNOWN, never reject) — but this
is a product decision about what the tool is for, not something the literature settles.
