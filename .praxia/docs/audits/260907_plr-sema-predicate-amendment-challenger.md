---
title: 'plr-sema increment 6 amendment (EnvRef/Zip, spec_version 18) -- short adversarial pass, challenger'
description: 'Scoped challenger pass (praxia:spec-challenger, Opus) on the increment 6 amendment delta only: A-C1..A-C13 (3 blockers: EnvRef shape (2) absorbs PLR-layer helper calls so the narrowness claim is false; Zip vacuous-quantification and membership open definite-verdict paths the anti-gaming counter cannot see; Zip sequence resolution unspecified at the gate site), 5 must-fix (alpha-substituted walk, clause ordering vs guard_operand_unknown, registry fallback needs measured symbols, in/not-in is a scope expansion, n_env_ref units), 3 should-fix, 2 notes. GO prediction for pick_up_tips survives every objection; not gaming the gate; verdict needs_revision (revise-and-advance).'
status: final
task_id: 260904_sema-predicates
date: '260907'
sprint: '127'
backlog_ids: '4978'
---
> Persisted verbatim by the orchestrator from the challenger agent's final report (no write tool).
> Target: `.praxia/docs/specs/260904_plr-sema-predicate-increment.md` at commit `f441d27e`
> (spec_version 18). The amendment was approved by the user 260907 as decision 5 in the sprint plan §8.

# Spec Challenger — increment 6 amendment (spec_version 18), delta only

Target: `/home/marielle/projects/praxis/.praxia/docs/specs/260904_plr-sema-predicate-increment.md`
Verdict: **`needs_revision`** · confidence **high** · 13 objections (3 blocker, 5 must-fix, 3 should-fix, 2 note)

Read in full: `plr-sema/src/plr_sema/derive/predicate_ast.py`, `derive/bindings.py:140-183`, `derive/__init__.py:440-505`, `check/tipstate.py:238-271`, `_hand_maintained.py:244-330,890-961`, `plr-sema/scripts/check_spec_crossrefs.py:45-160`, `outputs/plr-sema/t30_measured_260905.json` (block1/block3/block4/gate), `plr-sema/data/derived_contracts.json` (targeted), the sprint plan §8, and PLR at pin `dd79c4c89` (`:400-417`, `:488-527`, `:643-670`, `:1168-1192`, `:1684-1693`, `:1755-1794`, `:2203-2232`, `resources/volume_tracker.py:84-109`).

---

## Blockers

### A-C1 — "`EnvRef` is syntactically narrow" is falsified by the contract table, and one absorbed expression is provably not an environment read
**Location.** §15.9 anti-gaming box (line 1576, sentence 1); §15.2 G7 shape (2) (lines 458-463); §15.16.1 A2.

**Claim attacked.** *"`EnvRef` is syntactically narrow and has no fallback — it fires only on an expression rooted at the literal name `self`, in two enumerated shapes … so no arbitrary text can reach it."*

**Evidence.** `plr-sema/data/derived_contracts.json` carries **210** condition strings containing a `self.`-rooted call expression; **41** of them are the single shape `self._is_error_tail(response)`. G7 shape (2) admits it verbatim (callee is a `self`-rooted `ast.Attribute`, one bare-`Name` argument, no keywords, no `Starred`, no `Var("self")` in args). The document's own top-10 list already contains two more (`block_id not in self.available_blocks` ×5, `SparkDevice.FLUORESCENCE not in self.reader.devices` ×3), both of which flip.

The named counterexample the attack surface asked for is on the benchmark, not in a backend: `self._check_96_head_fits_in_container(container)` at `liquid_handler.py:1777`/`:1939` — the amendment predicts it **flips** (§15.9 re-prediction, `stamp` row). Its body is

```python
def _check_96_head_fits_in_container(self, container: Container) -> bool:
    tip_width = 2; distance_between_tips = 9
    return (container.get_absolute_size_x() >= tip_width + distance_between_tips * 11
            and container.get_absolute_size_y() >= tip_width + distance_between_tips * 7)
```
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1684-1693`)

It reads **no receiver state at all** — it is pure arithmetic over its own argument. It is not "a process-global, the backend class and its method signatures, the deck, or a container's seeded contents" (§15.1's tier-(ii) definition, lines 201-205). What is missing is inlining a PLR-layer delegate the `delegates_to` closure already walks, i.e. a *production/coverage* gap — precisely what `guard_predicate_unparsed` means. G7 gives the right ½ for the wrong reason, and the two artefacts the amendment offers as its inspectability instrument (`n_env_ref`, the top-10 `EnvRef` path list, §15.9 block 6) are populated by it.

**Why blocker.** §15.9's box is the *entire* justification offered for relaxing the gate's zero-condition, and it is a three-sentence argument of which sentence 1 is measurably false. §15.7's "the residual `guard_predicate_unparsed` count *is* the grammar's coverage gap" (line 1297) becomes false in the same stroke: ≥41 findings leave that count with no coverage gained.

**Probe.** What is the count, over the regenerated contract table, of admitted `EnvRef` shape-(2) nodes whose path resolves to a PLR-layer method the closure could inline (`self._is_error_tail`, `self._check_96_head_fits_in_container`, `self._find_available_sites_sorted`) versus a genuine receiver/backend/deck read (`self.head`, `self.backend.*`, `self.deck.*`)?

**Minimal remediation.** Either (a) restrict shape (2) to callees **not** present in the derive package's own function index (a derived test, no list), leaving PLR-layer helper calls `Opaque`; or (b) keep shape (2) as-is and *withdraw* the "syntactically narrow" sentence, replacing it with the measured absorption count and a published `n_env_ref_plr_layer` split so the top-10 list remains interpretable. (b) is ~0 LOC in T30c beyond one extra published field.

---

### A-C2 — the anti-gaming box's "only path to a new definite verdict" claim omits two paths that G8, not G7, opens
**Location.** §15.4 E-ENV (lines 825-833: *"it is the amendment's **only** path to a new definite verdict"*); §15.9 anti-gaming box sentence 2; §15.9 block (4)'s `n_decided_via_env_ref_shortcircuit`.

**Attack.** The Kleene short-circuit claim itself is sound — `F ∧ ½ = F`, `T ∨ ½ = T`, `¬½ = ½`, and `AllOf`/`AnyOf` over a concrete `Seq` whose body is ½ everywhere stays ½. I could not construct a counterexample there. But two *other* new-definite-verdict paths exist and neither is counted:

1. **Vacuous quantification over a `Zip`.** `all(...)` over an empty `zip` is `True`. If a `Zip` resolves to an empty (or short) sequence, `AllOf(Zip(...), <½ body>)` is `T` **vacuously**, `Not(...)` is `F`, and the `raise_guard` at `:514` emits **`SAFE`** — a definite verdict produced entirely by G8, with the `EnvRef` body never consulted. `n_decided_via_env_ref_shortcircuit` counts only compounds that short-circuited, so this is invisible in the published counters.
2. **The membership deciding case.** §15.4 E-ENV (line 820-823) and §15.2 G8(2) both grant `in`/`not in` a `T`/`F` branch when the RHS resolves to a concrete `Seq` of `Lit`s. That is a second new definite-verdict mechanism, also uncounted.

**Why blocker.** The box's stated burden is "the amendment cannot decide anything new by itself"; the falsifier it publishes (`n_decided_via_env_ref_shortcircuit`, predicted 0) cannot see either path. A reader who checks the published number and finds 0 will conclude the amendment decided nothing when it may have decided at `:514` — the gate site.

**Probe.** Under what resolution of `Zip` can `AllOf(Zip(...), pred)` at `:514` return a non-½ value, and is that value published anywhere?

**Minimal remediation.** Either forbid the definite branches outright this increment (`AllOf`/`AnyOf` over a `Zip` is ½ unconditionally; membership is ½ unconditionally — see A-C3/A-C10, cost: negative LOC, zero measured population), which makes "decides nothing" a **theorem** rather than a prediction; or add `n_decided_via_zip_vacuous` and `n_decided_via_membership` beside the existing counter and gate them in AC-15.3.

---

### A-C3 — `Zip`'s term resolution is normatively unspecified, at the gate site
**Location.** §15.2 G8(1) (lines 512-520); §15.4 E-ENV (line 819: *"`Len(EnvRef)` is ⊤ and so is `Len` of a `Zip`"*).

**Attack.** E-ENV pins exactly one fact about a `Zip`: its `Len` is ⊤. It never says what a `Zip` **resolves to as a sequence**, and §15.4's only quantifier rule is E-TYPE's *"`AnyOf(seq, pred)` over a `Seq` is `T` if any element is `T`, `F` if all are `F`, else ½"* (line 870) — which is conditioned on the seq being a `Seq`. A `Zip` is neither a `Seq` nor declared ⊤.

At `:514` the two items are asymmetric, and I verified this against source: `use_channels` resolves to an **exact** tuple via `channels_for_call` (`plr-sema/src/plr_sema/check/tipstate.py:262-269`; D2 measured non-`None` on every executed op), while `tips = [tip_spot.get_tip() for tip_spot in tip_spots]` at `liquid_handler.py:504` is a **projecting** comprehension — `elt` is not the identity map of its target — so `_parse_filtered`'s identity check (`predicate_ast.py:548-553`) rejects it, α does not bind it, and `tips` is ⊤. Python's `zip` truncates to the shortest, so an implementer who builds the zip from the operand that *did* resolve constructs a sequence of the wrong length. Concrete failure: `AnyOf` returning `F` ("all elements are `F`") over a sequence whose true length is unknown, negated into a `T`, is a **false `WILL_FAIL`**; the dual (A-C2 path 1) is a **false `SAFE`**.

**Why blocker.** This is the one node the gate candidate's second blocker is made of, and the spec's own §15.11 fixture only asserts the *parse* shape and that it "evaluates ½ against a call supplying both kwargs" — which is true because the body is an `EnvRef`, so the fixture passes under every completion of the missing rule and cannot discriminate.

**Probe.** What does `Zip((Seq[8], ⊤))` resolve to, and what is `AllOf` over it when the body is ½?

**Minimal remediation.** One normative sentence in E-ENV: *"A `Zip` resolves to ⊤ unless **every** item resolves to a concrete `Seq`, in which case it resolves to the positional zip truncated to the shortest; `AllOf`/`AnyOf` over a ⊤ seq is ½, never vacuously `T`."* Plus one AC-15.1 fixture: `AllOf(Zip(Seq([]), ⊤), <½>)` asserted ½, **not** `T`.

---

## Must-fix

### A-C4 — §15.7's two-line rule ranges over `predicate`, but `:409`'s `EnvRef` lives in the α binding, not in `predicate`
**Location.** §15.7 `EnvRef` reason rule (lines 1316-1339); §15.2 G7's `contains_env_ref` definition (lines 465-468).

**Attack.** The rule is stated as `contains_opaque(predicate)` then `contains_env_ref(predicate)`, and `contains_env_ref` is specified as *"the same recursion collecting a different predicate"* — a walk over a `Predicate`/`Term` tree. But `:409`'s guard condition is `not len(invalid_channels) == 0`, which parses to `Not(Cmp(Len(Var("invalid_channels")), "==", Lit(0)))`. **No `Filtered`, no `EnvRef`, no `Opaque`.** The `c not in self.head` filter is in `InlinedGuard.bindings` (`plr-sema/src/plr_sema/derive/__init__.py:499`, `tuple[dict[str, Any], ...]`), which is not reachable from `predicate` by any walk in `predicate_ast.py` or `bindings.py:150-182`.

That the measurement reported `guard_predicate_unparsed` for `:409` (`t30_measured_260905.json:473-482`) proves the shipped classifier **already substitutes the α binding before applying `contains_opaque`** — but nothing in §15.7, §15.2 G7 or §15.3 says so, and T30c is instructed only to "add `contains_env_ref` beside `contains_opaque`". An implementer who adds a literal sibling walk over `predicate` gets `contains_env_ref == False` at `:409` and the amendment's own worked example does not fire.

**Gate impact: none.** `:409` still lands `guard_env_dependent` by clause 3 — `channels` is `_make_sure_channels_exist`'s own parameter at `depth == 1`, E-CALL(depth) forbids resolving it against the entry point's kwargs, so it is ⊤ and it is not "an operand of this call" ⇒ `guard_env_dependent`, not `guard_operand_unknown`. The GO prediction survives; the *stated mechanism* does not.

**Minimal remediation.** One sentence: *"both walks range over the α/β-**substituted** predicate — the tree obtained by replacing each α/β-bound `Var` with its bound `Term` — which is already what the nested-`Opaque` rule's `:409` worked example assumes."* Plus one AC-15.1 fixture asserting `contains_env_ref` true for the substituted `:409` guard.

### A-C5 — §15.7's clause ordering relaxes the gate's *second* zero-condition, with no argument offered
**Location.** §15.7 `EnvRef` reason rule, clauses 2 and 3 (lines 1322-1328).

**Attack.** Clause 2 (`contains_env_ref` ⇒ `guard_env_dependent`) is ordered **before** clause 3's operand test (*"an operand of this call is ⊤ ⇒ `guard_operand_unknown`"*). So a guard of the shape `self.f(<x>)` where `x` **is** a call operand that resolves to ⊤ — a non-literal kwarg, or a kwarg `lower_calls` renamed to `?<j>` (`check/ir.py:796-808`) — is labelled `guard_env_dependent` when §15.7's own definition (line 1256) says it is `guard_operand_unknown`. §15.9's GO gate has **two** zero-conditions; §15.9's anti-gaming box argues only about the first and is silent on this. At this pin the exposure is nil because O1 drives `guard_operand_unknown` to 0 everywhere (`t30_measured_260905.json:1143-1146`), but the rule is wrong independently of the pin and it is exactly the shape (`EnvRef` with `Term` args, G7 shape 2) the amendment introduces.

**Minimal remediation.** Reorder: operand test first, `contains_env_ref` second. Or add the qualifier *"and no operand of this call resolves to ⊤"* to clause 2. One AC-15.5(iii) fixture: `self.backend.f(<?j-renamed kwarg>)` asserted `guard_operand_unknown`.

### A-C6 — the registry argument is contradicted by HM-25's own contents; the fallback is owed, and the fallback's own measure undercounts
**Location.** §15.8's amendment box (lines 1446-1477), reasons 1 and 2; §15.16.1 A2/A3.

**Attack.** The claim is *"they are derived by the total `parse`, over Python syntax, not over PLR idiom … verbatim the argument §15.8 reason 3 already makes for α and β."* The shipped registry refutes it directly. HM-25's `what` already books, as hand-maintained patterns:

- **P8** — *"zip-comprehension operand-pairing idiom (an `ast.ListComp`/`GeneratorExp` over a `zip(...)`-bound element call)"* (`plr-sema/src/plr_sema/_hand_maintained.py:919-920`), user-approved 260904. G8's `Zip` production is a `GeneratorExp` over `zip(...)`. Same shape, opposite disposition.
- **P3a** — *"the channel-default idiom (`<p> = <p> or self.<x> or list(range(len(<q>)))`)"* (`:904-906`) — a `self.<x>` recognition, likewise booked.

So the registry's own criterion, applied to essentially these two shapes, has already produced entries. Either P8/P3a are misfiled or G8/G7 are; the amendment cannot have it both ways while citing `_hand_maintained.py:945-948` as its authority.

**And the stated fallback has a second-order defect.** `_measure_hm25` (`_hand_maintained.py:300-330`) measures the row by **importing the eight symbols that implement the patterns** — "fails loudly, ImportError/AttributeError, if any is deleted". Naming `EnvRef`/`Zip`/`in` inside the α+β entry without adding measured symbols leaves three live patterns that `_measure_hm25` cannot see, so `test_no_surface_exceeds_its_declared_size` passes while the row silently undercounts — which is HM-24's *silent* criterion, the exact failure mode §15.8 argues these productions do not have.

**Minimal remediation.** Adopt the stated fallback (no further ceiling — HM-25 is already going 8→9), **and** extend `_measure_hm25` to import the three new production symbols so the entry's measure tracks its `what`. If declaring three more shapes inside one entry pushes the measured pattern count past 9, that is a user decision, and it should be surfaced now rather than at T31.

### A-C7 — the `in`/`not in` production is outside the scope the user approved, and it is the one that flips `:409`
**Location.** §15.2 G8(2) (lines 521-528); frontmatter (*"adds three productions"*, line 3); sprint plan decision 5(b), `.praxia/docs/plans/260904_plr-sema-sprint127-predicates.md:252-260`.

**Attack.** The option put to the user reads: *"an `EnvRef` leaf for an expression rooted at `self.` … plus `zip(<Term>, <Term>)` as a `Term` for `AllOf`/`AnyOf`."* Two productions. It does not mention widening `_CMP_OPS` (`plr-sema/src/plr_sema/derive/predicate_ast.py:298-305`) with `ast.In`/`ast.NotIn`. Without that widening, `c not in self.head` is `Opaque` regardless of `EnvRef`, `:409` does not flip, and `pick_up_tips` stays NO-GO — so the unapproved production is **load-bearing for the gate**. Meanwhile the document asserts (line 39) *"Nothing in this document is 'pending user approval' any more."*

**Minimal remediation.** Record the third production explicitly in §15.16.1 A3 and in the sprint plan's decision log as an amendment-scope expansion, with a one-line statement of why it is in scope (it is the comparator that makes `:409`'s filter readable at all) — or route it back as a fifth-and-a-half decision. Cheap either way; the point is that "all decisions approved" is currently overstated.

### A-C8 — `n_env_ref` is published under two incompatible definitions
**Location.** §15.9 block (3) (line 1521: *"the number of `EnvRef` **nodes** in that cluster's parsed predicate"*) vs block (4) (line 1527: *"the number of **guards** on that operation whose predicate contains ≥ 1 `EnvRef`"*); re-prediction table note (line 1618) and its `pick_up_tips` cell **"2 (one node each)"**.

**Attack.** Same field name, two units. `:2055` (`self.setup_finished and (not self._resource_pickups)`) is **one guard with two nodes**: block (3) publishes `n_env_ref: 2`, block (4) counts it as 1. A reader cross-footing block (3) against block (4) — which is exactly what AC-15.3's "the gate number is asserted computable from the JSON alone, without reading this document" invites — gets an inconsistency and no way to resolve it from the JSON. AC-15.3 asserts both are "present and non-null" and never disambiguates. The `stamp` row's hedged "2–3" and `move_*`'s "4–5" make the ambiguity un-falsifiable in exactly the cells where it bites.

**Minimal remediation.** Rename block (3)'s field `n_env_ref_nodes` (matching block 6's own `n_env_ref_nodes`/`n_env_ref_guards` split) and keep `n_env_ref` for the per-guard count; restate the `pick_up_tips` cell as `n_env_ref_guards = 2`, `n_env_ref_nodes = 2`.

---

## Should-fix

### A-C9 — `**T30c**` is invisible to the cross-reference lint, and the amendment's obligations hang off an already-closed row
**Location.** §15.12 T30c row (line 1991); §15.12 T30 row's gate cell (line 1990); `plr-sema/scripts/check_spec_crossrefs.py:58`.

**Evidence.** `TASK_ROW_RE = re.compile(r"^\|\s*\*\*(T\d+|#\d+[a-z]?)\*\*[^|]*\|")` — the `[a-z]?` suffix is on the `#\d+` alternative only, so `| **T30c** |` does **not** match. The row's gate cell is never scanned by the AC-gating half.

The amendment routes around this deliberately: T30c "Satisfies the amended halves of **AC-15.1** … and **AC-15.3**, **both of which stay gated on T30's row**." That keeps the lint at zero violations, but T30 is recorded **landed** in §15.15 (`58e5c3fc`/`7c0fe59a`/`6cbbe442`), so the amendment's new fixture set and its seven new publications are formally gated by a completed task. Nothing mechanically enforces them. Compounding it, T30's gate cell still says *"run `t30_measure.py` into `outputs/plr-sema/t30_measured_260904.json`"* — the file §15.9's own normative box (line 1497) says **was never written**.

**Minimal remediation.** Rename the row `T35` (or `#4978`, which the regex does accept), gate the amendment's ACs on it directly, and correct T30's gate cell to `_260905.json`. ~3 line edits; T33 already re-runs the lint.

### A-C10 — the membership deciding case has zero population, no fixture, and no `Term` production that can reach it
**Location.** §15.2 G8(2) (lines 525-528); §15.4 E-ENV (lines 820-823); §15.11 AC-15.1's amendment fixture list.

**Attack.** The deciding case requires the RHS to resolve to *"a concrete `Seq` of hashable `Lit`s"*. There is **no `ast.List`/`ast.Tuple` display production in `Term`** — `_parse_term` (`predicate_ast.py:518-539`) has no branch for either, and §15.13 confirms *"a tuple display is not a `Term` in G1 and the amendment adds none."* So a literal-container RHS (`x in ['a','b']`) is `Opaque`, and the only reachable route is a `Var` resolving to an `ir.Seq` from `call.kwargs`. Answering the attack-surface question directly: **at this pin there is no such guard** — I found none where the RHS is a literal container that would now decide. So the spec ships an evaluator branch (T31) that can emit a definite verdict, with zero measured population, no AC-15.1 fixture (the amendment's fixture set pins only `not in self.head`, which is ½), and no published counter. Additionally, deciding `not in` ⇒ `T` requires the `Seq` to be *complete* rather than a lower bound, which §15.4 nowhere asserts of `ir.Seq`.

Separately, and answering the second half of the same question: the `EnvRef` RHS at `:409` **is** guaranteed ⊤ and cannot be accidentally resolved through `Attr` handling — G7 shape (1) intercepts at the `ast.Attribute` chain root before `_parse_term:526-528` can build `Attr(Var("self"), "head")`, and the `Var("self")` invariant fails the residual case closed.

**Minimal remediation.** Delete the deciding case for this increment (all membership `Cmp`s ½), which also strengthens A-C2. If kept: one AC fixture and a published counter.

### A-C11 — the frontmatter's "every citation verified against the file" claim does not hold for `derive/__init__.py`
**Location.** frontmatter `sources` (line 10); §15.4 E-SCOPE box (lines 945-950); §15.9 (line 1556); §15.1 tier-(iii) box (line 216).

**Evidence** (all against the working tree, post-T30a/T30b):
- `InlinedGuard` now has **nine** fields, not seven — `condition, predicate, scope_trail, raises, kind, free_vars, site, depth, bindings` (`plr-sema/src/plr_sema/derive/__init__.py:491-499`). §15.4's C2-remediation box still asserts *"exactly seven fields"*. The conclusion (no `caller_scope`) survives; the arithmetic does not.
- The citation `derive/__init__.py:452-478` used for that field list (and again at §15.9 line 1557 for "no `tier` field") now spans the `@dataclass` decorator and docstring, not the fields.
- `is_dynamic_raise` is at `:502-505`. §15.1 cites `:489-493`; the frontmatter's re-anchoring list cites `:499-503`; AC-15.6 cites `:501-505` (correct). Three citations to one property, two wrong.

This matters because the amendment's frontmatter explicitly asserts the citation set was re-verified this pass, and a reviewer budgets accordingly.

**Minimal remediation.** Re-anchor those four citations and change "exactly seven fields" to "nine fields, none of them `caller_scope`". T33 already runs the citation checker; run it before, not after.

---

## Notes

### A-C12 — `EnvRef` inhabits both unions; `args=None` vs `()` has no round-trip fixture
`Predicate` and `Term` are disjoint `Union`s today (`predicate_ast.py:195,291`) with matching `_TERM_KINDS`/`_PREDICATE_KINDS` partitions at `:637-638`. `EnvRef` in both positions breaks the partition. Separately, G7 makes `args is None` (a read) versus `args == ()` (a zero-arg call) load-bearing — *"`args` is `None`, which is what distinguishes a read from a call of no arguments"* (line 456) — and JSON `null` vs `[]` must survive `to_json`/`from_json`. T30c's row names the round-trip work; AC-15.1's fixture list does not pin it. One fixture: `self.get_used_volume()` round-trips to `args == ()`, `self.head` to `args is None`.

### A-C13 — `Zip`'s positional correspondence is normative but unrepresentable on the wire
G8(1) states *"the correspondence is positional, `target[i] ↔ items[i]`"* and in the same sentence that *"the bound names are recorded nowhere … no node gains a field"* (`predicate_ast.py:53-60`). So the stated correspondence cannot be reconstructed downstream. Consequence: comprehension-bound names (`channel`, `tip`) enter the body as ordinary free `Var`s, and E-CALL step (1) will resolve one against `call.kwargs` if the name collides with a real parameter — a pre-existing hazard for single-target `AllOf`, doubled per comprehension by `Zip`. Harmless at `:514` (body is an `EnvRef`, ½ regardless). Remediation: either record the target names, or state normatively that a name bound by an `AllOf`/`AnyOf` target resolves to ⊤ and never to `call.kwargs`.

---

## Answers to the three questions asked

**Which objections would change the GO prediction for `pick_up_tips`?**
**None.** I attacked this specifically and the prediction survives every objection above.
- `:409` reaches `guard_env_dependent` under two independent routes: the amendment's stated one (A-C4 shows it needs the α-substitution clause to work as written) **and**, failing that, §15.7 clause 3 — `channels` is `_make_sure_channels_exist`'s own parameter at `depth == 1`, ⊤ by E-CALL(depth), not a call operand, therefore `guard_env_dependent` and not `guard_operand_unknown`.
- `:514` is non-`Opaque` under every completion of A-C3's missing `Zip` rule; the only divergence is whether it stays ½ or decides, and both satisfy the gate.
- The three guards the GO actually rests on — `:498`, `:502`, `:522` — contain no `self` and are untouched by the amendment; I verified this against `liquid_handler.py:496-522`.
- Verified from `t30_measured_260905.json:452-542`: `:409` and `:514` are the **only** `guard_predicate_unparsed` members on `pick_up_tips`. Its other eight clusters measure `guard_env_dependent` (`:375`, `:383`, `:321`, `:498`, `:522`, `:576`) or `decidable_or_operand_dependent` (`:502`), plus `:535` owned by the tip family.

Other re-prediction rows I spot-checked and confirm: `aspirate`/`dispense` are blocked by `:116` **alone** — `:990`/`:1202` measure `guard_env_dependent`, not unparsed (`:602-611`, `:822-831`), and `:875` likewise (`:563-571`); `Is` admits only a literal `None` RHS (`predicate_ast.py:450-453`), so `lidded is resource` correctly does not flip and `_check_no_lid`'s `:117` is a separate `<unconditional>` cluster measuring `decidable_or_operand_dependent`, not a second `:116`-class blocker. `drop_tips`'s sole unparsed blocker is `:657` (`:763-771`); `:666`/`:822` measure `guard_env_dependent`. `:1778`/`:1940` flip; `:2030` (tuple display), `:2211` (`%` BinOp) and `:2226` (`is not resource`) do not — all three verified against PLR source. Block (1)'s top-10 spot-check is accurate as claimed: exactly two are membership tests over a `self` chain (they flip) and three are `self`-rooted but subscripted or arithmetic (`:24`, `:28`, `:52` — they stay `Opaque`). `volume_tracker.py:91`/`:104` are genuinely double-fenced (family dispatch **and** the parenthesised `BinOp`), so A5 holds — though note the dispatch rule it leans on sits in an ordinary paragraph at lines 587-590, not in a `Normative` box, while §15.2 G7's normative box defers precedence to it.

**Is the amendment gaming the gate? — No.**
Reason: the reason-flip at `:409`/`:514` moves in the direction §15.7's own definition already supports (the residual names a missing observation about the head and the backend, not a shape the grammar cannot read); `n_findings_decided` is unchanged and separately asserted; five of the ten measured blocker sites do not flip and are named individually; and §15.16.1's list of four refused productions — the general `x is y` alone would have made 163 operations GO candidates — is a real, checkable act of self-restraint. **But the anti-gaming *argument* is unsound as written**: sentence 1 is falsified by the contract table (A-C1), sentence 2's "only path" is incomplete (A-C2), and the box is silent on the gate's second zero-condition, which §15.7's clause ordering can also relax (A-C5). Fix those three and the box supports its own burden.

**Verdict: `needs_revision`.**
A-C1, A-C2 and A-C3 are blockers because they land on the amendment's own justification and on the semantics of the node the gate candidate's second blocker is made of. All three remediations are text-only or LOC-negative and none of them re-opens the GO prediction — this is a revise-and-advance, not a re-litigation. A-C4 through A-C8 are must-fix before T30c writes `t30_measured_260908.json`, because four of them (A-C4, A-C5, A-C8, A-C9) determine what that file means.
