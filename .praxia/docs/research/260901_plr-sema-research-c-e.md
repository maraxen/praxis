---
title: 'plr-sema deferred items (c),(e): research findings'
description: 'Research subagent output (260901) on deferred semantic questions (c) and (e); claims tagged by source (notebook / web / our code / measured), survey pin dd79c4c89.'
status: final
task_id: 260901_plr-jit-research-c-e
date: '260901'
confidence: ''
sources: ''
---
# Deferred items (c) and (e) — research findings

`task_id: 260901_plr-jit-research-c-e` · 2026-09-01 · survey pin `dd79c4c89` (`pylabrobot 0.2.2`)

Claim tags: `[notebook: <spill>]` · `[web: <url>]` · `[our code: <file:line>]` · `[measured: <what I ran>]`

Measurement scripts (read-only, no repo writes) are reproduced in
`/home/marielle/.claude/jobs/d54cd068/tmp/scripts/` and were run from the praxis repo root against
`training/verify/data/plr_preconditions.json` and `external/pylabrobot/`.

---

## Headline

Three measurements reframe both deferred items, and one of them contradicts the spec's own premise.

1. **The `self.head[channel]` frontier is 7 call nodes.** Across the de-duplicated union of all ten
   `SUPPORTED_TOOLS` closures there are **133** dropped-receiver calls. Exactly **7 (5.3%)** have the
   `self.<field>[i].m()` shape §7.4/§7.6/RISK-1 treat as the canonical hazard, and they are **three
   distinct expressions**: `self.head[channel].get_tip()` ×5, `.remove_tip()` ×1, `.add_tip()` ×1.
   `[measured: analyze_dropped_detail.py]`
2. **That shape is resolved by reading one annotation.** `self.head: Dict[int, TipTracker] = {}`
   `[our code: external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:162]`. PLR annotates
   **94.1%** of non-`self` parameters and carries **1,064** `AnnAssign` nodes.
   `[measured: analyze_resolvability.py]`
3. **The content behind it is already on disk.** `TipTracker.get_tip` is an indexed survey record
   whose single finding is `raise_guard / "self._tip is None" / NoTipError`. Nothing needs to be
   re-surveyed; only the *edge* is missing. `[measured: jq over plr_preconditions.json]`

Consequently: (e) is a **call-graph edge-resolution** problem, not an aliasing problem; the spec's
stated dependency of (e) on (a) is **backwards**; and RISK-1 — as written, an approach-invalidating
risk — **does not fire**, though (e) does block *useful output* for 5 of 10 tools.

---

## Q1 — Reframing (e): type inference, aliasing, or typestate-with-permissions?

### Verdict

**(e) is a name-resolution / lightweight-type-inference problem. It is not an aliasing problem and
not a typestate-with-permissions problem.** The typestate and shape-analysis literature is the right
literature for a *different* question that plr-jit has not reached and, under §0's "every v1 verdict
is `UNKNOWN`", may never reach in its current form.

### The distinction that does the work

The corpus is unambiguous that aliasing, not the state lattice, is the hard part of typestate:

> "Objects often define usage protocols that clients must follow… Aliasing makes it notoriously
> difficult to check whether clients and implementations are compliant with such protocols."
> — Bierhoff & Aldrich, OOPSLA'07 `[notebook: /home/marielle/projects/praxis/.praxia/nlm/260901-141515__two-distinct-questions-about-ordering-and-depend__9b7e89ff.json]`

> "Without tracking aliases, a program could delete a resource through one name and then reference it
> through another." — DeLine & Fähndrich, Vault, PLDI'01 `[notebook: same spill]`

Strom & Yemini's original typestate simply **forbade aliasing** in NIL; Vault reintroduced it via
tracked types and held-key sets; Bierhoff & Aldrich via linear-logic access permissions
`[notebook: same spill]`.

That difficulty is real — **for the question "does channel 3 currently hold a tip?"**. plr-jit's §7
closure is not asking that. It is asking **"which guards exist on the code path this call reaches?"**
Those are separated by what each needs from the receiver:

| question | needs from `self.head[channel]` | machinery |
|---|---|---|
| §7.2 closure: which guards get inlined | its **class** (`TipTracker`) | annotation read |
| §3 evaluation: is the guard satisfied *here* | the **identity and current state of that element** | heap abstraction / permissions |

Resolving `self.head[channel].get_tip()` → `TipTracker.get_tip` needs no knowledge of *which* channel,
of whether any tip is present, or of whether another reference aliases that tracker. Every element of
`Dict[int, TipTracker]` has the same class, so the summary-node imprecision that ruins per-element
*state* tracking is **irrelevant to class resolution**. The strong-vs-weak-update problem — the entire
reason the typestate literature is hard — arises only once you attach mutable state to the abstract
location. §7 attaches none.

### What the measurement shows the frontier actually is

De-duplicated union of all 10 `SUPPORTED_TOOLS` closures (24 functions), 133 dropped-receiver calls
`[measured: analyze_dropped_detail.py]`:

| shape | n | % | what resolving it needs |
|---|---:|---:|---|
| `local.m()` bare local/import/global | 38 | 28.6% | import table or local binding |
| `param.m()` bare parameter | 35 | 26.3% | the parameter's annotation |
| `<expr>.<field>.m()` deeper chain | 28 | 21.1% | two-hop annotation lookup |
| `self.<field>.m()` | 20 | 15.0% | class field annotation |
| **`self.<field>[i].m()`** | **7** | **5.3%** | class field annotation + container unwrap |
| `f(...).m()` call result | 4 | 3.0% | return annotation |
| other | 1 | 0.8% | — |

Of the `local` receivers, **23 of 38 are module imports or module globals** (`logger`,
`Coordinate.zero`, `inspect`, `warnings`) — library noise, not domain content.

All 7 `self.<field>[i]` sites, in full `[measured: analyze_dropped_detail.py]`:

```
LiquidHandler.aspirate:974       self.head[channel].get_tip()
LiquidHandler.aspirate:1063      self.head[channel].get_tip()
LiquidHandler.dispense:1179      self.head[channel].get_tip()
LiquidHandler.dispense:1264      self.head[channel].get_tip()
LiquidHandler.drop_tips:655      self.head[channel].get_tip()
LiquidHandler.drop_tips:684      self.head[channel].remove_tip()
LiquidHandler.pick_up_tips:538   self.head[channel].add_tip()
```

### What the literature settles vs. what is judgment

**Settled by the literature.**
- Access-permission typestate (Bierhoff & Aldrich) **requires source annotations** and is a modular
  type-checking system, not an inference analysis
  `[notebook: /home/marielle/projects/praxis/.praxia/nlm/260901-141310__compare-and-contrast-three-approaches-to-determi__9b7e89ff.json]`.
  The brief states we cannot annotate PLR and will not fork it. **This eliminates option (3)
  categorically, before any cost discussion.**
- Points-to and 3-valued shape analysis are both annotation-free and inference-capable
  `[notebook: same spill]`.
- Both of those buy their precision specifically for *strong updates on individual heap cells* — a
  capability §7's closure does not consume.

**Judgment call (mine, stated as such).** That the §7 closure needs only class resolution follows
from reading §7.2's `derive_contract` — it appends `InlinedGuard`s and pushes resolved delegates onto
a frontier; nothing in it inspects a receiver's state `[our code: spec §7.2, lines 1101-1130]`. I
believe this is uncontroversial, but it is an argument from the spec's own mechanic, not a citation.

### The counter-argument, taken seriously

One could object: the derived contract's *usefulness* depends on eventually evaluating
`self._tip is None` against a concrete program, and *that* is the aliasing problem, so we are only
deferring it. True — and it is worth saying plainly that a future `SAFE` verdict on
"`drop_tips` will not raise `NoTipError`" **does** require per-channel state tracking, and at that
point the typestate literature becomes exactly right. But §0 fixes every v1 verdict at `UNKNOWN`, and
§7.4's own "forward hazard" note already fences the first `SAFE`. So the aliasing problem is
correctly deferred *behind* item (b) and the `SAFE` fence, not behind item (e).

---

## Q2 — Cheapest sound-enough mechanism, ranked

### Recommendation, ranked

**#1 — Annotation-driven receiver typing (stdlib `ast`, build-time only).** ~400–600 LOC productionized,
**1–2 sessions**. Rules, in the order I implemented and measured them:

| rule | what it reads |
|---|---|
| R1 | parameter annotation in the enclosing `def` |
| R2 | `self.f: T` `AnnAssign` in the owning class |
| R3 | R2 + container unwrap `Dict[K,V]→V`, `List[T]→T`, `Optional[T]→T` |
| R4 | module import / module-global table (classifies noise out) |
| R5 | two-hop: type the base, then read that class's field annotation (cross-file class table) |
| R6 | `self.f = Ctor(...)` and `self.f = <annotated __init__ param>` — an annotation-equivalent binder PLR uses pervasively |
| R7 | `for x in <annotated iterable>` / `zip` / `enumerate` element unwrap |

Measured yield `[measured: analyze_resolvability.py, analyze_final.py]`:

- R1–R4 alone, no dataflow: **80/133 = 60.2%** of all dropped receivers.
- Full R1–R7 with the noise bucket separated: 38 calls are library noise; of the **95 domain-relevant**
  calls, **64 (67.4%) resolve to a class**, and for **33** of those the called method is confirmed
  present on the resolved class. The remaining 31 resolve to a `Union[...]` whose members were not
  split (a further, easy increment).
- Cross-file tables built for the whole of PLR: **234 classes / 955 annotated fields**, **650 classes /
  6,011 methods** `[measured: analyze_resolvability2.py]`.
- Baseline that makes this work: **8,309/8,827 (94.1%)** non-`self` params annotated; **3,421/7,031
  (48.7%)** return annotations; **1,064** `AnnAssign` nodes across 502 files
  `[measured: analyze_resolvability.py]`.

Crucially, `self.head[channel].get_tip` resolves under R3 to `TipTracker` with `owns_method=True`
`[measured: analyze_final.py]`. The single most-cited hazard in the spec is discharged by rule R3.

**#2 — Points-to / alias analysis (Rival & Yi).** Annotation-free, polynomial, scales to 10⁵–10⁶ LOC
`[notebook: 260901-141310 spill]`. **Rejected as over-engineering for this problem**: its precision
budget is spent distinguishing *which* heap cell a reference denotes, which is exactly the axis we do
not need. It would additionally *lose* to #1 on the `Union[...]` cases, where a declared annotation is
strictly more informative than a points-to set derived from PLR's own construction sites.

**#3 — Off-the-shelf checker inference (pyright / mypy) as a build-time oracle.** Pyright infers
return types from bodies even when unannotated, and infers parameter types where mypy does not
`[web: https://github.com/microsoft/pyright/blob/main/docs/mypy-comparison.md]`; a published AWS
static-analysis system uses precisely this pattern — pyright-derived types resolved into call-receiver
nodes before rule evaluation `[web: https://arxiv.org/pdf/2205.04432]`. This would cover the 48.7%
return-annotation gap and the `f(...).m()` bucket "for free". **Ranked below #1 only on integration
cost, not capability**: it adds a heavyweight non-stdlib dependency to the derivation step, a
subprocess/JSON protocol, and a version-pinning obligation on the §2.2 stamp. It is the right
*second* increment if #1's residual matters. It does not touch §6.2's Pyodide constraint, because
derivation is a build-time step whose output is shipped as JSON.

**#4 — 3-valued shape analysis (TVLA).** Materialises individual nodes via Focus and permits strong
updates `[notebook: 260901-141310 spill]` — genuinely the most precise option for the *state*
question. **Rejected for (e)**: worst-case exponential-to-doubly-exponential, scalable to hundreds of
LOC intraprocedurally, and it demands hand-crafted instrumentation predicates and predicate-update
formulas from the analyser author `[notebook: same spill]`. Cost is one to two orders of magnitude
above #1 for zero gain on class resolution.

**#5 — Access-permission typestate.** **Structurally unavailable.** Not inference-capable; requires
pervasive source annotations in the analysed program `[notebook: same spill]`. We cannot annotate PLR.

### Residual after #1, and honest caveats

The 31 domain-relevant residuals cluster tightly `[measured: analyze_final.py]`:
`tip.tracker.*` and `op.{tip,resource}.tracker.*` (VolumeTracker calls — liquid volume, not tip state,
reached through loop variables bound by `zip`), `resource.rotate/rotated/unassign`, and four
`destination.<method>(...).rotated()` call-result receivers.

**Three ways my numbers could mislead, stated up front:**
1. **My 133 is a depth-1 frontier, not a fixpoint.** Once (e) resolves cross-class edges, the closure
   grows (`TipTracker`, `VolumeTracker`, `Deck`, `Resource` enter it) and a *new* dropped population
   appears at the new frontier. The right way to read 133 is "the first wave", not "the whole debt".
2. **My noise filter is heuristic** (uppercase-initial receiver, plus a method denylist including
   `.get`). It could suppress a real domain method. I inspected the resolved/residual lists by hand
   and saw none, but the filter is a judgment call, not a measurement.
3. **31 of 64 "resolved" are `Union[...]`** with no method confirmation. Counting them as resolved is
   optimistic; counting them as unresolved is pessimistic, since union-splitting is a small increment.
   The defensible floor is 33/95 = 34.7%; the defensible ceiling is 64/95 = 67.4%.

---

## Q3 — Does (e) depend on (a)? **No. The stated dependency is backwards.**

The spec's Deferred table says (e) "requires type inference whose precision requirements follow from
(a)" `[our code: spec Deferred table, ~line 1741]`. The corpus contradicts this directly:

> "The claim that *'we must pick the abstract domain first, then the aliasing precision follows'* is
> **fundamentally backwards**. The heap/alias abstraction does not merely refine or parameterize an
> existing value domain — the heap abstraction dictates the semantic structure of the memory model
> itself, which in turn determines what kinds of value domains are expressible, sound, and capable of
> strong updates."
> `[notebook: /home/marielle/projects/praxis/.praxia/nlm/260901-141515__two-distinct-questions-about-ordering-and-depend__9b7e89ff.json]`

In Rival & Yi's formulation `M♯ = (X ∪ N_site) → V♯`, once the memory abstraction collapses cells into
a summary, `*x := e` must weak-update `μ ↦ M♯(μ) ⊔♯ v♯`, and **no amount of precision in the value
domain — exact polyhedra included — recovers what the heap abstraction discarded** `[notebook: same
spill]`. In TVLA the point is sharper still: value properties *are* predicates over heap individuals,
so the shape abstraction determines whether a strong update is expressible at all `[notebook: same
spill]`. And typestate is not formulated as a value domain over a fixed heap abstraction at
all — it is a system whose *entire* correctness obligation is the aliasing/strong-update question
`[notebook: same spill]`.

**Adjudication.** The dependency arrow in the Deferred table points the wrong way for *both* readings:
- If (e) were the aliasing problem the spec implies, the literature says the heap abstraction
  constrains the domain, so **(a) would depend on (e)**, not the reverse.
- Under the Q1 reframing — (e) is class resolution — the two are **independent**. Class resolution
  reads declarations; it consumes no lattice, no join, no widening.

**Consequence for task ordering, which is the point of the question.** (e) is currently gated behind a
literature-corpus deliverable it does not need. It can be unblocked and scheduled **now**, in
parallel with (a), against data already on disk. This is the single highest-leverage correction in
this document.

**One thing the literature does not settle.** Whether *(a)* should be designed after (e) lands is a
genuine judgment call. The corpus's argument (heap-first) applies when the domain must track heap
state. If plr-jit's domain ends up tracking only *argument* properties at a call boundary — a
plausible reading of §3.2's "flat finding multiset" — the heap-first constraint may not bind. I would
not assert an (a)-depends-on-(e) edge on this evidence; I assert only that the (e)-depends-on-(a) edge
as written is unsupported.

---

## Q4 — Is (e) blocking? **No for the pipeline; yes for the content of 5 of 10 tools.**

§7.6's trigger is: *"If the numbers indicate most content hides behind the unrecordable frontier,
deferred item (e) is promoted from 'later' to 'blocking' and §§7–8 pause."*
`[our code: spec §7.6 / RISK-1]`

### Applying the trigger

**Does most content hide behind the frontier?** For tip state, in the specific and load-bearing
sense: **yes for 5 tools, no for the rest.**

Per-tool closure membership and recorded findings `[measured: per-tool closure script]`:

| tool | closure | findings | tip-state precondition status |
|---|---:|---:|---|
| `pick_up_tips` | 6 | 10 | **recorded** — `self.head[channel].has_tip` is a `raise_guard` in the body (`HasTipError`) |
| `drop_tips` | 6 | 9 | **hidden** — `NoTipError` lives in `TipTracker.get_tip`, reached only through the dropped receiver |
| `discard_tips` | 7 | 10 | **hidden** (delegates to `drop_tips`) |
| `aspirate` | 9 | 9 | **hidden** — `tips = [self.head[channel].get_tip() …]` at `:974` |
| `dispense` | 8 | 10 | **hidden** — same shape at `:1179` |
| `transfer` | 11 | 17 | **hidden** (closure contains `aspirate` + `dispense`) |
| `stamp` | 8 | 15 | n/a — 96-head path, no `self.head[i]` calls |
| `move_resource` / `move_plate` / `move_lid` | 7–8 | 13 | n/a — no `self.head[i]` calls |

So: **`drop_tips`, `discard_tips`, `aspirate`, `dispense`, `transfer` — 5 of 10 — cannot express
"this channel must currently hold a tip", which is the single most important precondition in the tool
set.** `pick_up_tips` is fine because PLR happens to write the inverse guard (`has_tip` → `HasTipError`)
inline rather than delegating it. That asymmetry is luck, not design.

### Why RISK-1 nevertheless does not fire

RISK-1's impact column is **"invalidates the approach"**, and its failure condition is that derivation
"produces near-universal `UNKNOWN`, and `plr-jit` v1 is sound but empty" `[our code: spec §7.6]`. That
is a claim about *recoverability*, and it is now falsified by measurement:

- The missing content is not lost, it is **indexed**: `TipTracker.get_tip` / `add_tip` / `remove_tip`
  are survey records with recorded findings today. `[measured: jq over plr_preconditions.json]`
- The missing edge is resolved by **one annotation read** — R3 over
  `self.head: Dict[int, TipTracker]` `[our code: liquid_handler.py:162]` — inside a mechanism measured
  at 60–67% coverage of the whole frontier `[measured: analyze_final.py]`.
- The cost is **1–2 sessions of stdlib `ast`**, not a research programme.

**A risk whose mitigation is a two-day increment is not an approach-invalidating risk.** RISK-1 should
be **downgraded to medium impact** and its round-1 measurement recorded as *discharged*, with the
finding that the dominant dropped shape was `param.m()`/`local.m()` (55% combined), not
`self.<field>[i].m()` (5.3%).

### Direct answer

**(e) is not blocking on §§7–8, and they should not pause.** §7's mechanic, §7.3's table, §7.4's
ledger and §8's harness are all specified over whatever edge set exists; (e) enlarges that set without
changing any structure — which the spec's own boundary table already asserts ("the frontier shrinks;
the gap ledger's totals move. **No structural change**") `[our code: spec boundary summary, §7.2
closure row]`.

**(e) *is* blocking on the tip-state content of `drop_tips`, `discard_tips`, `aspirate`, `dispense`
and `transfer`.** It should be promoted from "later" to **next**, scheduled immediately after T6, and
explicitly un-gated from the literature corpus per Q3.

### Two defects found in the shipped ledger while checking this

Reported because they affect how the §7.4 numbers are read, not as a request to change scope.

**D-A. `methods_with_dropped_receiver_call` is not commensurable with `methods_with_no_recorded_gap`,
which is exactly what D4 required it to be.** The ledger reports
`methods_attempted: 1314`, `methods_with_dropped_receiver_call: 1976`
`[our code: plr-jit/data/gap_ledger.json]`. A method count cannot exceed its own denominator. Recomputed
`[measured: independent ast pass over the survey records]`:

| population | matched | methods with ≥1 dropped call | dropped call nodes |
|---|---:|---:|---:|
| all 4,770 survey records | 4,770 | **1,989** | 6,194 |
| 1,314 finding-bearing only | 1,314 | **674** | 2,936 |

1,976 ≈ 1,989, i.e. the counter runs over **all 4,770 records** while `methods_attempted` runs over the
**1,314 finding-bearing** ones. The figure D4 actually asks for is **674 / 1,314 = 51.3%**.

**D-B. `dropped_receiver_calls_by_method` is own-body only, not closure-wide.** The ledger reports
`stamp: 0`, `transfer: 0`, `move_plate: 0`, `move_lid: 0`
`[our code: plr-jit/data/gap_ledger.json]`; measured over each tool's `delegates_to` closure the same
methods carry 44, 27, 65 and 65 respectively `[measured: analyze_conditions.py part 2]`. Since §7.4's
asymmetry note exists precisely to interpret `methods_with_no_recorded_gap` — itself a *closure*
property — the own-body counter is not the right companion figure and reads as far more reassuring
than the closure figure warrants.

---

## Q5 — The minimum predicate language for (c)

### Corpus first, as instructed

Whole surface, 2,814 findings `[measured: analyze_conditions.py part 1]`:
- 2,081 `raise_guard` / 733 `assert` (26.0% asserts — matches §7.2's stated figure exactly).
- **379 `raise_guard` findings have `condition: None`** — a `raise` with no enclosing `if`
  `[our code: scripts/survey_plr_preconditions.py:195-197]`. **13.5% of all findings carry no
  predicate at all.** The predicate language must have a defined behaviour for this, and the spec does
  not mention it.
- 2,435 non-null conditions, **100% parse under `ast.parse(mode="eval")`** — zero unparseable.
  The `condition` field is always a syntactically valid Python expression.

Top-level shapes, whole surface:

| shape | n | % |
|---|---:|---:|
| `Compare/LtELtE` (chained range `a <= x <= b`) | 373 | 15.3% |
| `Not(Compare/LtELtE)` | 336 | 13.8% |
| `Not(Call/all)` | 206 | 8.5% |
| `Compare/Is` | 193 | 7.9% |
| `Compare/IsNot` | 158 | 6.5% |
| `Compare/Eq` | 135 | 5.5% |
| `Compare/NotEq` | 132 | 5.4% |
| `Compare/Gt` | 97 | 4.0% |
| `BoolOp/and` | 96 | 3.9% |
| `BoolOp/or` | 87 | 3.6% |
| remainder (16 further shapes) | 622 | 25.6% |

Feature prevalence: attributes 27.8%, comprehensions 12.4%, subscripts 3.2%. AST depth ≤ 5 for
2,377/2,435 (97.6%). Top calls inside conditions: `all` 257, `len` 185, `isinstance` 98, `any` 43.
`mentions_params` cardinality: **0 for 1,636 (67.2%)**, 1 for 1,063, 2 for 110, 3 for 5.

### The scope correction that matters

Whole-surface figures are **dominated by firmware/backend drivers** (PreciseFlex, Hamilton STAR,
MicroSpin) that plr-jit never checks — that is where the `1 <= speed_percent <= 100` range guards and
the `_parse_scpi_response` calls live. The predicate language only has to cover conditions that reach
a derived contract. Scoped `[measured: analyze_scoped_conditions.py]`:

| scope | functions | findings | parsed conditions |
|---|---:|---:|---:|
| S1 — current 10-tool closure | 24 | 52 | **48** |
| S2 — S1 + annotation-reachable classes (`TipTracker`, `VolumeTracker`, `Deck`, `Resource`, `Plate`, `Well`, `Container`, `TipSpot`, …) | 233 | 118 | 100 |
| S0 — whole surface | 4,770 | 2,814 | 2,435 |

**S1 is 48 conditions and fits on one screen.** Reproduced in full, because a predicate language
should be designed against them rather than against a taxonomy:

```
(source.num_items_x, source.num_items_y) == (target.num_items_x, target.num_items_y)
destination.direction == 'z'
destination.resource is not None and destination.resource is not resource
error is not None
isinstance(destination, ResourceStack) and destination.direction != 'z'
len(missing) > 0
len(not_containers) > 0
len(not_tip_spots) > 0
len(p) != len(use_channels)
len(set(use_channels)) == len(use_channels)
len(tip_spots) == len(offsets) == len(use_channels)
len(tip_spots) == len(offsets) == len(use_channels) == len(tips)
lidded is resource
n == 0
not (isinstance(resource, (Plate, Container)) or (isinstance(resource, list) and all((isinstance(w, Well) for w in resource))))
not all((self.backend.can_pick_up_tip(channel, tip) for channel, tip in zip(use_channels, tips)))
not isinstance(resource, Plate)
not len(containers) == 96
not len(invalid_channels) == 0
not resource_from_deck == resource
not self._check_96_head_fits_in_container(container)
ratios is not None
requested_bav is not None and done_bav is not None and (requested_bav > done_bav)
resource_rotation_wrt_destination % 180 != 0
self._blow_out_air_volume is None
self._resource_pickup is None
self._resource_pickup is not None
self.head[channel].has_tip
self.setup_finished and (not self._resource_pickups)
source_vol is None
source_vol is not None
strictness == Strictness.STRICT
tip.tracker.get_used_volume() > 0 and (not allow_nonzero_volume)
well.parent != plate
```

### Minimum grammar

Decomposing to atoms (splitting `and`/`or`/`not`), the atom kinds in S1 (n=58) and S2 (n=124):

| atom kind | S1 | S2 |
|---|---:|---:|
| `isinstance(x, T)` / `issubclass` | 12.1% | 10.5% |
| `<name> is/is not None` | 13.8% | 8.6% |
| `<attr> is/is not None` | 8.6% | 16.2% |
| `len(x) <op> const` | 12.1% | 8.0% |
| `len(x) <op> len(y)` (arity agreement) | 10.4% | 4.0% |
| `all(...)` / `any(...)` over a generator | 5.2% | 3.2% |
| attribute truthiness (`self.foo`) | 5.2% | 6.5% |
| `<expr> <cmp> <expr>` general | remainder | remainder |

**This yields a five-production grammar that covers ~80% of S1/S2 atoms:**

```
Pred  := And(Pred*) | Or(Pred*) | Not(Pred) | Atom
Atom  := NullCheck(Path, is_none: bool)              # x is None / x is not None
       | TypeCheck(Path, types: [str], negated)      # isinstance(x, (A, B))
       | LenCmp(Path, op, LenCmp | IntLit)           # len(x) == 96, len(a) == len(b)
       | Quant(ALL | ANY, var, Path, Pred)           # all(p(w) for w in wells)
       | Cmp(Expr, op, Expr)                         # residual, uninterpreted operands
Path  := Name | Path.attr | Path[Expr] | Path.m()    # opaque; carries the source text
```

`Cmp` is the escape hatch and must exist: `resource_rotation_wrt_destination % 180 != 0` and
`(source.num_items_x, source.num_items_y) == (target.num_items_x, target.num_items_y)` are not worth
first-class productions. Chained comparison (`len(a) == len(b) == len(c) == len(d)`) must desugar to a
conjunction of pairwise `LenCmp`s — **this is not optional**, it is 10.4% of S1 atoms, and it is
precisely PLR's parallel-array arity contract.

**Handle `condition: None` explicitly.** 13.5% of whole-surface findings are unconditional raises. The
right predicate is `TRUE` — the raise is reachable whenever the enclosing scope is — and the
`scope_trail` is the only remaining evidence about that scope. Silently treating `None` as
"no constraint" would be unsound in the `SAFE` direction, which is the direction §7.2 warns about.

**Do not trust `mentions_params` as the free-variable set.** 67.2% of conditions report zero mentioned
params, yet 27.8% contain attribute accesses and every `self.*` condition has a receiver. The survey
computes `mentions_params` as an intersection with the declared parameter names
`[our code: scripts/survey_plr_preconditions.py:203-204 and :176`-ish, the `param_names & {...}`
expression]`, and `self` is counted as a parameter (`TipTracker.get_tip`'s finding lists
`mentions_params: ["self"]`). A parsed predicate should recompute free variables from the AST and keep
`mentions_params` only as a cross-check.

### Is Jones's binding-time lattice the right frame?

**Yes as the staging architecture; no as a two-point lattice.** The corpus is explicit:

> "BTA is the correct structural staging framework, but a simple two-point BTA ({S, D}) is
> fundamentally insufficient on its own."
> `[notebook: /home/marielle/projects/praxis/.praxia/nlm/260901-142117__jones-gomard-sestoft-s-partial-evaluation-and-au__9b7e89ff.json]`

Under two-point congruence, if any variable in an expression is `D`, the result is `D`. So
`len(position) != 7` becomes dynamic the moment `position` is a dynamic parameter — *even though the
list's length is statically fixed* `[notebook: same spill]`. That failure mode lands directly on our
corpus: `len(...)` appears in 185 conditions, and arity-agreement atoms (`len(a) == len(b)`) are 10.4%
of S1.

The corpus's fix is **partially-static structures** — Mogensen's grammar-based BTA, Consel's
cons-point analysis, and Launchbury's projection-based BTA, where a list has projection `STRUCT`
(spine/length static, elements dynamic) distinct from `ID` (all static) and `ABS` (all dynamic)
`[notebook: same spill]`. Under `STRUCT`, `len(position)` evaluates in the static domain and the guard
is fully decided at analysis time `[notebook: same spill]`.

**This maps onto our corpus with unusual directness.** The three atom kinds that dominate S1/S2 are
exactly the three that a `STRUCT`-style projection decides statically:
- `len(x) <op> …` — decided from the spine alone.
- `isinstance(x, T)` — decided from a static type tag with a dynamic payload (Launchbury's `TAG`
  projection, Similix's tag domains) `[notebook: same spill]`.
- `x is None` — decided from a static pointer constructor over a dynamic pointee (the C-Mix
  treatment) `[notebook: same spill]`.

So the recommendation is: **adopt BTA as the staging frame, but specify a three-point-per-structure
lattice `ABS ⊑ STRUCT ⊑ ID` rather than `{S, D}`.** Our arguments are already classified
static/dynamic, which is the two-point classification; the corpus says that classification is one
refinement short of useful.

**Polyvariance is a real decision, and it is a decision for the user, not a settled question.** The
corpus recommends polyvariant divisions, because a monovariant join forces a shared helper's parameter
to `D` globally if *any* call site passes a dynamic argument `[notebook: same spill]`. Our shared
helpers are exactly the ones at issue: `_check_args`, `_make_sure_channels_exist` and `_log_command`
appear in 8–10 of the 10 tool closures `[measured: per-tool closure script]`. Under a monovariant BTA,
one dynamic caller degrades all ten. Under a polyvariant one, we pay function cloning per static
signature. I do not think the literature settles which is right for us — it depends on how many
distinct static signatures the corpus of user programs actually produces, which is unmeasured.

---

## Q6 — Parsed predicate × `kind` polarity

### Recommendation

**Keep `kind` as a first-class field alongside the parsed predicate. Do not fold polarity into the
parsed predicate, and do not normalise to NNF as a pre-processing step.**

The contract should be:

```
InlinedGuard.predicate  : Pred    # parses condition VERBATIM; polarity-free
InlinedGuard.kind       : "raise_guard" | "assert"
InlinedGuard.condition  : str     # retained, source of truth (spec boundary table already says so)

fires_when(g) = g.predicate            if g.kind == "raise_guard"   # spec §7.2 / survey:198-199
              = Not(g.predicate)       if g.kind == "assert"        # spec §7.2 / survey:208
```

`fires_when` is a **derived view computed at use site**, never a stored normalisation.

### What breaks if polarity is folded in

**1. `Not` is not a complement in any non-Boolean abstract domain.** In Kleene 3-valued logic negation
*is* an involution and *does* satisfy De Morgan, but it fails excluded middle and non-contradiction:
`p ∨ ¬p = ½` and `p ∧ ¬p = ½` when `p = ½`
`[notebook: /home/marielle/projects/praxis/.praxia/nlm/260901-142316__on-the-treatment-of-conditionals-and-guard-polar__9b7e89ff.json]`.
The corpus names the exact confusion this invites:

> "Conflating 'not definitely true' with 'definitely false'… `value(p) = ½ ⟹ ¬p = ½ ⇏ p = 0`."
> `[notebook: same spill]`

That is the failure mode for us. Given §3.3's `UNKNOWN` vocabulary and (b)'s open question about what
`UNKNOWN` means, plr-jit's evaluation domain is **not** going to be two-valued. An `assert` stored as
`Not(predicate)` therefore says something strictly weaker than "the guard fires when the predicate is
false" — it says "the guard fires when the predicate is not-definitely-true", which silently
over-approximates in the `WILL_FAIL` direction.

**2. `assume(¬c)` is not recoverable from `assume(c)`.** In abstract interpretation the two branches
of `if c` are computed by applying a single abstract test operator to `c` and separately to `¬c`; they
are **not complements**, they can overlap when the state is imprecise, and their join need not
reconstruct the pre-state `[notebook: same spill]`. There is no set-difference in interval, octagon,
polyhedral or shape domains — so an analyser given only `assume(c)` has no algebraic route to
`assume(¬c)` `[notebook: same spill]`. Folding polarity into the predicate deletes the information the
false-branch transfer function needs as an *input*.

**3. NNF is sound but lossy, and lossy in a direction we care about.** NNF preserves 3-valued truth
values (Sagiv/Reps/Wilhelm Lemma 3.6) `[notebook: same spill]`, so it is not *wrong*. But
`¬(A ∧ B) ⇝ ¬A ∨ ¬B` turns a conjunction into a disjunction, and abstract domains are closed under
conjunction but not disjunction — forcing an over-approximating join `[notebook: same spill]`. Our
corpus has this shape: `Not(BoolOp/and)` is 33 findings whole-surface and `Not(BoolOp/or)` is 2 of 48
in S1 `[measured: analyze_conditions.py, analyze_scoped_conditions.py]`. `not (isinstance(resource,
(Plate, Container)) or (isinstance(resource, list) and all(...)))` — an actual S1 condition — would
NNF into a conjunction of negated type checks and lose the relational structure a type-check domain
would otherwise exploit.

**4. It destroys the artifact.** §7.2 already argues this from the data side — "dropping `kind` makes
this polarity permanently unrecoverable from the shipped artifact" `[our code: spec §7.2, guard
polarity note]`. Folding polarity into `predicate` is the same loss with an extra step: the shipped
`predicate` would no longer round-trip against `condition`, and the §5 fork-drift and §8 differential
machinery both compare against `condition`.

**One caveat, in the other direction.** There is a real cost to keeping them separate: every consumer
must remember to apply `fires_when`, and a consumer that forgets gets a **polarity-inverted** answer
silently — the worst possible failure for a safety checker. Mitigation is mechanical, not
architectural: make `predicate` non-public on the dataclass or name it `predicate_as_written`, and
expose only `fires_when()` / `passes_when()` accessors. That is a naming decision, safe to specify now.

---

## Spec-ready recommendations

### Safe to specify now

**R1 — Reclassify (e) in the Deferred table.** Replace "Resolution strategy for the 967 unresolved
cross-class calls / *Requires type inference whose precision requirements follow from (a)*" with
"**Receiver-type resolution for dropped and unresolved cross-class calls / Independent of (a); needs
only PEP-484/526 annotation reading. Measured: 60–67% of the 10-tool frontier resolvable by a stdlib
`ast` pass.**" Q3's evidence contradicts the current dependency claim.

**R2 — Add the annotation-resolution rules R1–R7 (Q2) as a specified task, sized 1–2 sessions,
scheduled immediately after T6.** Gate: `self.head[channel].get_tip()` resolves to `TipTracker` and
`LiquidHandler.drop_tips`'s derived contract acquires a guard whose `site.qualname` is
`TipTracker.get_tip` at `depth > 0` — the direct analogue of §7.5's existing
`test_aspirate_closure_reaches_check_containers`, and the first test that will be **cross-file**,
which §7.5's `test_guard_sites_point_at_defining_file` currently notes is structurally unsatisfiable.

**R3 — Fix the two ledger defects (D-A, D-B in Q4).** `methods_with_dropped_receiver_call` must run
over the same 1,314-record population as `methods_attempted` (correct value **674**), and
`dropped_receiver_calls_by_method` must be computed over each method's `delegates_to` closure, not its
own body. Both are required for D4's stated commensurability property to hold.

**R4 — Downgrade RISK-1 from "invalidates the approach" to medium impact, and record its round-1
measurement as discharged**, with the finding that `self.<field>[i].m()` is 5.3% of the frontier while
`param.m()` + `local.m()` is 54.9%.

**R5 — Specify the five-production predicate grammar (Q5) with `Cmp` as an uninterpreted escape
hatch**, chained-comparison desugaring to pairwise conjunction, and `condition: None` mapping to
`TRUE` rather than to "no constraint".

**R6 — Specify the polarity contract (Q6)**: `predicate` parses `condition` verbatim, `kind` stays
first-class, `fires_when()` is a derived accessor, and the dataclass exposes no un-polarised predicate
under a name a caller could mistake for the firing condition. No NNF normalisation at parse time.

**R7 — Record that `mentions_params` is not the free-variable set** (67.2% report zero while 27.8% of
conditions contain attribute accesses); a parsed predicate recomputes free variables from its own AST.

### Needs a decision from the user

**D1 — Pyright as a build-time type oracle (Q2 rank #3).** Covers the 48.7% return-annotation gap and
the `f(...).m()` bucket, at the cost of a heavyweight non-stdlib dependency in `plr_jit.derive`, a
subprocess protocol, and a pyright version pin in the §2.2 stamp. My recommendation is to ship R2
first and revisit only if R2's residual (~31 domain-relevant calls, dominated by `VolumeTracker`
liquid-volume guards) turns out to matter. But adding a build-time dependency is a project-shape
decision, not a research finding.

**D2 — Binding-time lattice granularity (Q5).** The literature says two-point `{S, D}` is
insufficient and partially-static projections (`ABS ⊑ STRUCT ⊑ ID`) are needed. Adopting that means
(a)'s abstract domain must carry per-structure projections, which is materially more machinery than
"flat finding multiset" implies. This is (a)'s scope, and I flag it rather than decide it.

**D3 — Monovariant vs. polyvariant BTA (Q5).** `_check_args`, `_make_sure_channels_exist` and
`_log_command` are shared by 8–10 of the 10 tool closures. Monovariant is cheap and degrades all ten
tools when any one caller is dynamic; polyvariant preserves precision at the cost of cloning. The
right choice depends on how many distinct static signatures real user programs produce — currently
unmeasured, and measuring it needs a corpus that does not yet exist.

**D4 — Whether `Union[...]` receivers count as resolved.** 31 of my 64 "resolved" receivers are
`Union[Plate, Container, List[Well]]`-shaped with no method confirmation. Splitting unions and
requiring the method on *every* member is the sound reading (floor: 33/95 = 34.7%); requiring it on
*any* member is the permissive one (ceiling: 64/95 = 67.4%). This is a soundness policy question that
belongs with (b), not a measurement.

---

## Appendix — what I ran

| script | produces |
|---|---|
| `analyze_conditions.py` | whole-surface condition taxonomy; per-tool dropped-receiver shape counts |
| `analyze_dropped_detail.py` | de-duplicated 133-call frontier; receiver text per shape; all 7 `self.field[i]` sites |
| `analyze_resolvability.py` | tier-1 annotation resolvability (60.2%); PLR-wide annotation coverage baseline |
| `analyze_resolvability2.py` | cross-file class-field/method tables; loop-var and two-hop increments |
| `analyze_final.py` | full R1–R7 resolver with noise filter (67.4% of domain-relevant); condition samples per shape |
| `analyze_scoped_conditions.py` | S1/S2/S0 scoped condition taxonomy and atom-kind grammar counts |

All read-only. All run from `/home/marielle/projects/praxis` against the committed survey at PLR pin
`dd79c4c89`. No file under `src/` or `praxis/` was read for mutation or modified.

NotebookLM spills (full citations, greppable):
- `/home/marielle/projects/praxis/.praxia/nlm/260901-141310__compare-and-contrast-three-approaches-to-determi__9b7e89ff.json` — points-to vs. TVLA vs. access permissions
- `/home/marielle/projects/praxis/.praxia/nlm/260901-141515__two-distinct-questions-about-ordering-and-depend__9b7e89ff.json` — domain/heap dependency direction; typestate-as-aliasing
- `/home/marielle/projects/praxis/.praxia/nlm/260901-142117__jones-gomard-sestoft-s-partial-evaluation-and-au__9b7e89ff.json` — binding-time analysis, partially-static structures, polyvariance
- `/home/marielle/projects/praxis/.praxia/nlm/260901-142316__on-the-treatment-of-conditionals-and-guard-polar__9b7e89ff.json` — guard polarity, non-complemented domains, NNF
