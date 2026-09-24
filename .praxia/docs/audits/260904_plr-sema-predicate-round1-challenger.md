---
title: 'plr-sema increment 6 (predicate language) -- adversarial round 1, challenger report'
description: 'Challenger report (praxia:spec-challenger, Opus) on .praxia/docs/specs/260904_plr-sema-predicate-increment.md spec_version 16 draft: C1-C18, six blockers (C1 null-condition x E-UNCOND false WILL_FAIL on ~268 clean ops; C2 InlinedGuard has no caller_scope; C3 excludes_sites rests on a non-existent, non-injective exc_class->site mapping; C4 E-TYPE F rule unsound for supertype declarations, T rule equality-only; C5 AC-15.8 floor met by reason rename alone; C6 rebinding clause deletes all eight beta sites), seven must-fix, verdict needs_revision.'
status: final
task_id: 260904_sema-predicates
date: '260904'
sprint: '127'
backlog_ids: '4977'
---
# Round-1 challenge — increment 6, the predicate language

> Persisted verbatim by the orchestrator from the challenger agent's final report (the agent has no
> write tool). Target: `.praxia/docs/specs/260904_plr-sema-predicate-increment.md` at commit
> `6407d92a` (spec_version 16, status draft). Companion: `260904_plr-sema-predicate-round1-defender.md`.

**Target:** `/home/marielle/projects/praxis/.praxia/docs/specs/260904_plr-sema-predicate-increment.md` (spec_version 16, 1027 lines)
**Verdict: `needs_revision`.** Six blockers. The grammar (§15.2) is sound and well-argued; the *evaluator* (§15.4) and the *fence* (§15.5, §15.10) are not, and three of the six blockers are cases where the spec's own normative text produces a false `WILL_FAIL` on operations the benchmark executed clean. Two more are gates that pass while the increment is broken.

---

## C1 — BLOCKER — `parse(None) = TRUE` + E-UNCOND's vacuous satisfaction emits `WILL_FAIL` on 310 findings / ~268 clean operations

**Location.** §15.2 G0 (`:233-239`), §15.4 E-VERDICT (`:456-468`), §15.4 E-UNCOND (`:470-494`).

**The claim.** G0: "`parse(None) = TRUE` — a `None` condition means the guard fires unconditionally". E-VERDICT: `fires == T` ⇒ `Verdict.WILL_FAIL`, *"only if the guard is unconditional (E-UNCOND below)"*. E-UNCOND: "every entry of its `scope_trail` … is recognised as satisfied, in exactly three ways".

**The attack.** A guard with an **empty** `scope_trail` satisfies E-UNCOND vacuously — "every entry" over an empty tuple is `True`. Combined with G0, **every `condition: null` guard becomes a `WILL_FAIL` on every operation that carries it.** The ledger has four such clusters on real executed ops:

| site | condition | n_findings | n_ops | methods |
|---|---|---|---|---|
| `liquid_handler.py:117:_check_no_lid` | `<unconditional>` | 163 | 163 | aspirate 77, dispense 40, stamp 27, transfer 19 (`unknown_ledger_260904_before.json:396-408`) |
| `liquid_handler.py:2092:pick_up_resource` | `<unconditional>` | 93 | 81 | move_resource/lid/plate (`:673-684`) |
| `liquid_handler.py:1770:aspirate96` | `<unconditional>` | 27 | 27 | stamp (`:1462-1471`) |
| `liquid_handler.py:1920:dispense96` | `<unconditional>` | 27 | 27 | stamp (`:1627-1636`) |

`check/__init__.py:298-308` records that **"9 of the 119 guards in the shipped contract table carry `condition: null`"** — this is not a corner case, it is a designed-for population.

**Concrete failure scenario.** `_check_no_lid` at `external/pylabrobot/.../liquid_handler.py:110-120`:

```python
lidded = _lidded_ancestor(resource)
if lidded is None:
    return                                  # :114  EARLY RETURN
if lidded is resource:
    raise ValueError(...)                   # :116  condition "lidded is resource"
raise ValueError(...)                       # :117  condition None  <- statement position, EMPTY scope_trail
```

`:117` is at statement position in the function body. `survey_plr_preconditions.py:191-229` pushes trail entries only for `ast.If` / `ast.For` / `ast.While` — **a preceding `return` is not a scope entry and `visit_Try` is not overridden at all**, so a `raise` after an early return, or a `raise e` inside an `except` handler (`liquid_handler.py:2090-2092`), both carry an empty trail. Under the spec as written the analyzer emits `WILL_FAIL/precondition_state` on 163 aspirate/dispense/stamp/transfer ops that ran clean and on 81 `move_*` ops likewise. `oracle_common.py:645-647`:

```python
unsound = (verdict == "safe" and outcome.startswith("raised")) or (
    verdict == "will_fail" and outcome == "ran_ok")
```

So **AC-15.8's `unsound == 0` fails by construction**, at T32, after ~1,250 LOC — and AC-15.9's `region_unsound == 0` with it. The spec's own §15.10 asserts "`unknown_rate` is expected to stay 1.0"; it will not, it will collapse into false `WILL_FAIL`s.

**Probe.** For a guard whose `condition` is `None` and whose `scope_trail` is empty, what distinguishes "PLR raises unconditionally when this function is entered" from "PLR raises here only on the path that does not take an earlier `return`"? Nothing in `PreconditionFinding` records the difference.

**Minimal remediation I would accept.** E-UNCOND gains a fourth blocking clause, normative: *a guard whose `scope_trail` is empty may emit `WILL_FAIL` only if the defining function `K` contains no `ast.Return`, no `ast.Try`, and no `ast.Raise` at a lower `lineno` than the guard's, and the guard is at `depth == 0`.* Failing that, `½` and `guard_env_dependent`. Plus a fixture over `_check_no_lid` asserting `UNKNOWN`, in AC-15.6.

---

## C2 — BLOCKER — `InlinedGuard` has no `caller_scope`; every depth-1 guard's call-site reachability is unmodelled and the spec asserts otherwise

**Location.** §15.4 E-SCOPE (`:446-454`), E-UNCOND (`:470-487`), §15.3's scope condition (`:374-390`).

**The claim.** E-SCOPE: "`parse` and evaluate each entry of its `scope_trail` … and, **for a bridged guard, of its `caller_scope`** (increment 5 §14.0.2)". E-UNCOND: "Everything else blocks `WILL_FAIL`: … and a `null` scope."

**The attack.** `InlinedGuard` (`plr-sema/src/plr_sema/derive/__init__.py:466-472`) has exactly seven fields — `condition, scope_trail, raises, kind, free_vars, site, depth`. **There is no `caller_scope`.** `caller_scope` exists only on the *volume bridge* guards emitted by `derive/receiver_state.py:1962-1985` (`_caller_scope_for_expr`, P10). Every guard in §15.1's tables is an `InlinedGuard`. So:

- "a `null` scope" has no referent for an `InlinedGuard`. Two readings: (a) absent ⇒ null ⇒ `WILL_FAIL` blocked for every `depth >= 1` guard — which kills `:875`, `:117`, `:2092`, `:375`, `:409`, `:321` as WILL_FAIL sources but leaves C1's depth-0 cases; (b) absent ⇒ vacuously satisfied — which is C1's blowup. **The single most consequential normative rule in the increment has two readings that differ by 268 operations, and the spec does not say which.** §15.3's own scope condition (`:375-376`, "the delegate's own body for a guard at `depth == 1`") indicates reading (b) was intended.
- Increment 5's rule is strictly *stronger* than E-UNCOND here: §14.6 says a volume guard "is **conditional** iff its P10 `caller_scope` is `null`, **or** contains any entry the evaluator does not recognise" (`260903_plr-sema-volume-increment.md:619-622`). E-UNCOND claims to be a *generalisation* of that rule; on the artifact it is a weakening, because the field it generalises over does not exist on the type it is applied to.

**Concrete failure scenario.** `aspirate` calls `_check_no_lid` inside a loop:

```python
for resource in resources:            # :977
    _check_no_lid(resource, "aspirate from")   # :978
```

and `dispense` likewise at `:1190-1191`. `_check_no_lid`'s guards at `:116`/`:117` are inlined at `depth == 1` with the delegate's own (empty / one-entry) trail. The `for` header at the call site — which is exactly what increment 5's R1 exists to reason about — is invisible. There is no way for T31 to implement E-UNCOND correctly for these guards without first building the P10 equivalent for the ordinary closure, and **T30's scope (`:907`) does not budget it.**

**Minimal remediation.** Either (i) T30 extends `InlinedGuard` with `caller_scope`/`caller_lineno` for `depth >= 1` (reusing `_caller_scope_for_expr`) and E-UNCOND is stated over it, with the LOC estimate revised; or (ii) a normative one-liner: **no guard at `depth >= 1` may ever emit `WILL_FAIL` in this increment**, plus a fixture. (ii) is cheap and I would accept it, but it must be written down, because it also changes §15.9's predicted residuals.

---

## C3 — BLOCKER — `excludes_sites` narrows the fence via an `exc_class → PLR site` taxonomy that does not exist and cannot be injective (this is §15.14 Q6, answered "yes")

**Location.** §15.5 normative box (`:530-549`), §15.10 (`:758-765`), AC-15.8 (`:865-871`).

**The claim.** "for a row where execution raised at operation `i` and the static side says `SAFE` at `op_i`, the row is unsound **unless** the executed exception's class is one the taxonomy maps to a `plr_site` in `excludes_sites`."

**The attack — the row the narrowed predicate excuses and the old one caught.** The harness's `exc_class` is a *string prefix of a message*: `exc_class = error.split(":", 1)[0].strip()` (`plr-sema/eval/oracle_common.py:368`). There is no taxonomy anywhere in the repo mapping an exception class name to a PLR raise site, and none can be total or injective, because **`TypeError` is raised at `liquid_handler.py:375`, `:383`, `:498`, `:1743`, `:1770`** — all PLR-precondition sites — **and re-raised at `:576`**, which is exactly the tier-(iii) site that would be in `excludes_sites`.

Concrete: a `pick_up_tips` row where the analyzer wrongly says `SAFE` (say via C4 or C14) and PLR's own `:498` `raise TypeError("Resources must be TipSpots")` fires. Runtime reports `exc_class == "TypeError"`. `TypeError` maps to a site set containing `:576 ∈ excludes_sites` ⇒ the row is **excused**. The old predicate caught it. Every `TypeError`-, `ValueError`- and `RuntimeError`-raising row is excusable under the narrowed predicate, which is essentially the whole raise population.

**Aggravating.** §15.5's own dataclass paragraph concedes the category set is "unbounded" at this pin and switches to a site set to escape that — but the site set inherits the same non-injectivity through the *observation* side, which the paragraph does not address.

**Minimal remediation.** Either drop the narrowing entirely (publish `SAFE`-on-raise rows unnarrowed and let `rows_excused_by_scope` be a *published annotation* with no effect on the gate), or specify the mapping as **the raising site itself**, observed — i.e. `run_runtime` must capture `traceback.extract_tb(...)[-1]` `(filename, lineno)` and the narrowing keys on that, not on `exc_class`. The second is ~10 lines and makes the fence honest; the first is free. As written, AC-15.8's `unsound == 0` is not a fence.

---

## C4 — BLOCKER — E-TYPE's `F` rule is unsound for a supertype declaration, and its `T` rule is equality-only, so it both fabricates `WILL_FAIL` and fails §15.9's own predictions

**Location.** §15.4 E-TYPE (`:411-419`), §15.9 table (`:742-748`).

**The claim.** "It is `F` iff the declared name is present and is **not** any `Tᵢ` **and** the declared name is a known PLR class that is not a subclass of any `Tᵢ`; `T` iff it equals some `Tᵢ`."

**Attack (a) — the `F` rule is unsound.** A declared type is an **upper bound**, not an exact type. A resource declared `Container` may at runtime be a `Trash`. The rule returns `F` for it, because `Container` is not a subclass of `Trash`.

This is live, not hypothetical. `_generic_plr_type_name` (`oracle_common.py:235-248`) returns the most-specific MRO ancestor whose name is in `_PLR_GENERIC_RESOURCE_NAMES` (`:225-232`). **`Trash` is not in that set**; `Container` is. `external/pylabrobot/pylabrobot/resources/trash.py:4` is `class Trash(Container)`. So under O1 a `Trash` object's recorded `element_type` is **`"Container"`**. Then at `liquid_handler.py:645-647`:

```python
not_tip_spots = [ts for ts in tip_spots if not isinstance(ts, (TipSpot, Trash))]
if len(not_tip_spots) > 0:
    raise TypeError(...)
```

α binds, G3 gives `AnyOf(tip_spots, Not(IsInstance(ts, (TipSpot, Trash))))`. `"Container"` ≠ TipSpot, ≠ Trash, and is not a subclass of either ⇒ E-TYPE says **F** ⇒ `Not(...)` is **T** ⇒ `AnyOf` **T** ⇒ raise_guard fires ⇒ **`WILL_FAIL` on `discard_tips`** (34 ops) and `drop_tips` (31 ops) that ran clean. Unsound in the false-positive direction, scored by `compare:646`.

**Attack (b) — the `T` rule fails §15.9's own table.** `T` requires *equality*. `_check_containers` at `:873-875` tests `isinstance(r, Container)`; a `Well` has `element_type "Well"` (Well is in the generic set). `"Well"` ≠ `"Container"` ⇒ not `T`; `Well` **is** a subclass of `Container` (`well.py:31: class Well(Container)`) ⇒ the `F` clause is excluded ⇒ **½**. §15.9's `aspirate` row asserts "`:959` and `:875` clear". They do not. The subclass relation the spec goes out of its way to derive (`:418-419`) is used only in the `F` clause, never in the `T` clause.

**Minimal remediation.** Restate E-TYPE as: `T` iff the declared name **is or is a subclass of** some `Tᵢ`; `F` iff the declared name and every `Tᵢ` are **disjoint in the class hierarchy** (neither is an ancestor of the other) *and* the declaration is known to be exact; `½` otherwise — with a normative note that a declared type derived from `_generic_plr_type_name` is **never exact** (its own docstring, `:238-243`, says it falls back to the concrete name only when nothing generic matches), so under O1 the `F` branch is unreachable on the benchmark and every `isinstance` atom is `T`-or-`½`. That is fail-closed, keeps `:498`/`:647` working in the `SAFE` direction, and makes `:875` clear.

---

## C5 — BLOCKER — AC-15.8's "≥ 1,000 findings converted" floor is satisfied by the reason rename alone, with zero guards decided

**Location.** AC-15.8 (`:865-871`), §15.10 (`:773-778`).

**The claim.** "the `guard_predicate_unparsed` count is asserted to have **decreased**, with a floor of **≥ 1,000** findings converted". §15.10: "the `guard_predicate_unparsed` 5,656 is the number that must move".

**The attack.** A finding leaves `guard_predicate_unparsed` the moment its condition parses non-`Opaque`, *regardless of whether anything is decided*. The two largest clusters do exactly that and decide nothing:

- `liquid_handler.py:375`, `len(missing) > 0` — **544 findings** (`unknown_ledger:39-57`). Parses to `Cmp(Len(Var(missing)), >, Lit(0))`. `missing = non_default - backend_kws` is an `ast.BinOp`, neither α nor β ⇒ free name unresolved ⇒ `guard_env_dependent`. **Converted, decides nothing.**
- `liquid_handler.py:383`, `strictness == Strictness.STRICT` — **544 findings** (`:81-99`). Parses to `Cmp(Var, ==, Attr(...))` ⇒ `guard_env_dependent`. **Converted, decides nothing.**

1,088 > 1,000 from two clusters the spec itself tiers as (ii) and explicitly defers. Add `:409` (384), `:321`, `:116` and the floor is met three times over before a single guard is evaluated. **AC-15.8's headline number can pass with the grammar stubbed to "parse everything, resolve nothing."**

**Minimal remediation.** Replace the floor with one that cannot be met by renaming: *the count of findings whose verdict becomes `SAFE` or `WILL_FAIL`* ≥ N, published per PLR site, plus the `guard_env_dependent` count published separately and **excluded** from "converted". Derive N from §15.9's own candidate table rather than asserting 1,000.

---

## C6 — BLOCKER — §15.3's rebinding clause excludes all eight β sites that §15.3 names as β's "real population", falsifying AC-15.2's floor and §15.9's dispense row

**Location.** §15.3 β (`:355-372`), the rebinding clause (`:374-383`), §15.1.3 (`:194-200`), AC-15.2 (`:815-824`), §15.9 (`:745`).

**The claim.** "β's real population is the two-operand form: `offsets = offsets or [Coordinate.zero()] * len(tip_spots)` (`:517`), `:661`, `:962-965`, `:1156-1159`." AC-15.2 requires "**≥ 6** β entries". §15.1.3 calls `:1185`/`:1188` "the increment's cleanest result", clearing via E-SCOPE because `blow_out_air_volume` defaults at `:1159`.

**The attack.** The rebinding clause is unconditional: "**`x` is written exactly once in `K`**. Any second write to `x` anywhere in `K` — conditional or not, before or after the guard — makes the binding `Opaque`." In `aspirate` and `dispense`, every one of those eight names is written twice, two to six lines later:

| name | β write | second write | K |
|---|---|---|---|
| `offsets` | `:962` | `:1004` | aspirate |
| `flow_rates` | `:963` | `:969` | aspirate |
| `liquid_height` | `:964` | `:970` | aspirate |
| `blow_out_air_volume` | `:965` | `:971` | aspirate |
| `offsets` | `:1156` | `:1177` | dispense |
| `flow_rates` | `:1157` | `:1163` | dispense |
| `liquid_height` | `:1158` | `:1164` | dispense |
| `blow_out_air_volume` | `:1159` | `:1165` | dispense |

(read directly: `liquid_handler.py:962-971`, `:1004`, `:1156-1165`, `:1177`.)

**Consequences, all three of which are the spec contradicting itself:**
1. β's *surviving* population is `pick_up_tips:517` and `drop_tips:661` — **two** entries in `LiquidHandler`. AC-15.2's `≥ 6` floor is asserted with no evidence that four more exist anywhere on the PLR surface.
2. §15.1.3's "cleanest result" fails twice over: β declines `blow_out_air_volume`, **and** β "binds no elements" while `any(bav is not None and bav != 0.0 for bav in blow_out_air_volume)` needs the elements. E-SCOPE gets `½`, not `F`. `:1185`/`:1188` do **not** clear.
3. §15.9's `dispense` row ("`:1185`/`:1188` clear via E-SCOPE") is therefore false, and §15.9's `pick_up_tips` GO prediction is the only surviving row — narrowing an already-single-point-of-failure gate.

**Minimal remediation.** Either narrow the single-write clause to "no write to `x` between the β assignment's `lineno` and the guard's `lineno` **on a path that reaches the guard**" (which requires a reaching-definitions notion the increment declines) — or concede: restate β's population as `{:517, :661}`, drop AC-15.2's floor to `≥ 2` (or measure it before asserting it), and delete the `:1185`/`:1188` claim from §15.1.3 and §15.9.

---

## C7 — MUST-FIX — E-CALL has no parameter-rebinding clause, and the `use_channels` escape hatch hand-types an AC-13.15(iii)-forbidden literal

**Location.** §15.4 E-CALL (`:405-409`), §15.3 β's P3a paragraph (`:368`).

**The claim.** "A `Var(name)` term resolves, in order: (1) to `call.kwargs[name]` … (2) to the resolved contract's recorded default … (3) to an α/β binding …". And: "**The grammar consults `channels_for_call` for every `use_channels` term and never re-derives it.**"

**Attack (a).** §15.3's single-write clause protects α/β-bound *locals*. It does not protect **parameters read directly by a guard after PLR has rebound them**. E-CALL step (1) resolves such a `Var` to the *caller's* value. PLR rebinds parameters constantly before guards read them: `use_channels` at `:501`/`:650`/`:958`/`:1152`, `resources` at `:999`/`:1172`, `ratios` at `:1343`, `vols` at `:968`/`:1162`. Any guard downstream of one of those and naming it is evaluated against the wrong value, in both directions.

**Attack (b).** The spec's own escape hatch for the worst case is a hard-coded parameter name. `plr-sema/src/plr_sema/check/tipstate.py:254-257` states the opposite rule as normative:

> `channel_kwarg` — the keyword PLR itself uses to select channels explicitly (§13.5.2/AC-13.15(iii): read from `receiver_state`'s own derived `channel_kwarg`, **never hand-typed as `"use_channels"` here — that string is one of AC-13.15(iii)'s forbidden literals**).

§15.3 writes exactly that literal into a normative box. It also collides with E-CALL's own ordering: if `use_channels` is present in `call.kwargs`, step (1) wins and `channels_for_call` is never consulted; the two rules give different answers and the spec does not say which governs.

**Minimal remediation.** (a) Add to E-CALL: *a `Var(name)` naming a parameter of `K` that is written anywhere in `K` at a `lineno` below the guard's resolves to ⊤* (fail-closed, symmetric with §15.3). (b) Restate the P3a hook as "for every term naming the receiver's derived `channel_default_param` / `channel_kwarg`", and state that this hook takes precedence over E-CALL step (1).

---

## C8 — MUST-FIX — nothing assigns tiers at evaluation or measurement time; the tier-(iii) "no `Finding`" rule needs a hand-maintained site list, which §15.8 says costs zero registry rows

**Location.** §15.1 (`:116-132`), §15.5 (`:536`), §15.9 (`:723-735`), §15.8 (`:661`).

**The claim.** "A guard classified tier (iii) emits **no `Finding` at all** and instead contributes its `site` to `excludes_sites`." And the GO gate is "≥ 1 executed real operation's residual tier set is exactly ⊆ {(ii), (iii)}".

**The attack.** There is no `tier` field on `InlinedGuard` (`derive/__init__.py:466-472`), no tier in `derived_contracts.json`, and §15.1's tiering is a **table in a Markdown document**. So:

- The evaluator must recognise tier (iii) by *something*. Two options, neither specified: a hard-coded list of PLR sites (`:576`, `:726`, `:1067`, `:1271`, `:2092`, …) — which is **newly hand-typed surface over how PLR is written**, i.e. **growth** under main spec §9.4 (`260901…:2429-2431`), requiring a registry row that §15.8 says is zero — or a syntactic rule ("`condition` is `error is not None`"), which is a fourth pattern and silently misses `:2092` (`raise e`, condition `null`) and `:1770`/`:1920`.
- §15.9's GO number is "residual tier set ⊆ {(ii),(iii)}", but tier assignment is a human judgement in §15.1's table. **Who computes the tier at measurement time?** If `t30_measure.py` reads a table transcribed from the spec, the GO condition is the spec's own prediction restated as a measurement — self-fulfilling, and §15.9's own framing ("this document's own prediction, to be falsified by the measurement and not assumed by it") is not satisfiable.
- §15.1's own table already mis-tiers: `:117` is listed tier (ii) "lid topology" (`:188`), but it has no operands at all — the evaluator will call it `T`, not `½`. §15.1.4 enumerates seven conditions for the "nine clusters at `:2055`–`:2290`" and `:2092`'s `<unconditional>` is not among them.

**Minimal remediation.** Make the tier a **derived, published field**, computed mechanically from the guard record (`condition` parses non-`Opaque` ∧ all free names resolve from the call ⇒ (i); `raises` is a re-raise of an `except`-bound name ⇒ (iii); else (ii)) and emitted into `t30_measured_260904.json`, with §15.1's tables re-derived from it and any divergence recorded. If instead a site list is used, §15.8 must price it as a registry row.

---

## C9 — MUST-FIX — AC-15.5(iv) and AC-15.6 contradict each other; "no `Finding`" also collides with AC-7.2 totality and with the ledger

**Location.** AC-15.5(iv) (`:844-845`), AC-15.6 (`:852-856`), §15.4 "Interaction with the join" (`:496-500`).

**The claim.** AC-15.5(iv): "One `Finding` per guard is preserved: an operation with `n` guards yields exactly `n` findings, asserted as a count." AC-15.6: "a tier-(iii) guard emits **no** `Finding` and contributes its `site` to `AnalysisReport.scope.excludes_sites`."

**The attack.** An operation with `n` guards of which `k` are tier (iii) yields `n − k` findings. Both criteria are asserted over "an operation"; the spec never says the AC-15.5(iv) fixture is (iii)-free. An implementer satisfies one and fails the other. Downstream:

- Main spec §7.2's totality (AC-7.2, `derive/__init__.py:499-503`: "Every operation therefore receives at least one Finding downstream") and §3.2's join table (`260901…:576-581`: "zero findings ⇒ `UNKNOWN`") mean an operation *all* of whose guards are tier (iii) silently becomes `UNKNOWN` with no evidence, rather than `SAFE`-with-scope.
- The ledger (`unknown_ledger.py:231-236`) clusters *findings*. A suppressed guard cannot be counted, so §15.9(3) ("per ledger cluster (all 54): tier, `parsed?`, `bound?`, and the reason it would carry") is uncomputable for tier-(iii) clusters after the change, and the before/after delta in AC-15.8 silently loses 4 clusters' worth of findings that were never "converted", they were deleted.

**Minimal remediation.** Emit the tier-(iii) `Finding` as `Verdict.SAFE` with a new dedicated `detail` marker (no new reason needed, no vocabulary cost), *and* record the site in `excludes_sites`. Totality, the join, the ledger and the one-Finding-per-guard invariant all survive; the scope annotation still does its work. If suppression is genuinely wanted, AC-15.5(iv) must be restated as `n − |tier(iii)|` and the ledger's denominator adjusted explicitly.

---

## C10 — MUST-FIX — `SoundnessScope` is defined twice, with different single fields, inside one normative box

**Location.** §15.5 (`:530-538`).

**The claim, verbatim.** "`SoundnessScope` is a frozen dataclass with a single field `excludes: frozenset[str]` ⊆ `FAILURE_CATEGORIES`. Its **only** value in this increment is `frozenset({"harness_internal"})` ∪ the categories a re-raise can carry, which at this pin is unbounded — **so the exclusion is stated as a site set, not a category set**: `excludes_sites: tuple[PlrSite, ...]`."

**The attack.** Three defects in five lines. (1) The dataclass has "a single field `excludes`" and then a single field `excludes_sites`; an implementer must guess, and AC-15.6 only ever references `excludes_sites`. (2) `harness_internal` is a nonsensical member — main spec `:788` defines it as "analyzer/plumbing bug; always paired with `reason="internal_error"`", which has nothing to do with a backend re-raise. (3) "unbounded" is used as an argument for switching representations but is never justified; it is the reason the category form is abandoned, so it is load-bearing.

Separately: the spec cites `260901…:103` and `:3327-3330` as the definition of `SoundnessScope`. Neither defines it — `:103` is a forward reference ("cross-reference the soundness-fence discussion in deferred row (b)/`260901_plr-sema-research-b-f.md`") and `:3327-3330` merely notes that a definite *volume* verdict would need one. There is no shipped `SoundnessScope` anywhere. This increment is *inventing* the type, which is fine, but it should say so rather than cite two non-definitions.

**Minimal remediation.** One field: `excludes_sites: tuple[PlrSite, ...]`. Delete the `excludes`/`harness_internal` sentence. State that `SoundnessScope` is new in this increment.

---

## C11 — MUST-FIX — O1 is a tier-(ii) observation the gate depends on, and the harness does **not** already compute the half that matters

**Location.** §15.4 O1 (`:421-444`), §15.9 (`:750-754`), AC-15.4 (`:830-837`), §15.6/§15.13.

**Claim (a).** "The fix is the observation the harness already computes and discards: `resource_types_from_kwargs` … O1 threads it into `resources_from_example` as the RESOURCE `type`, and extends the walk to record the **element's own** generic class … as `element_type`." §15.9: "O1 is a ~25-line harness change over data the harness already computes."

**The attack.** `resource_type_of` (`oracle_common.py:251-274`) implements **parent-wins**:

```python
parent = getattr(obj, "parent", None)
target = parent if parent is not None else obj
name = getattr(target, "name", None)
return name, _generic_plr_type_name(target)
```

For a list of `TipSpot`s it returns `{tip_rack_name: "TipRack"}`. **The element's own class is exactly the thing this function is written to discard.** The `type` half is already computed; the `element_type` half — the half the gate rests on, since `:498` is the guard that must clear — is not computed anywhere. "~25 lines over data the harness already computes" is wrong about the half that matters, and the sizing of the gate task depends on it.

**Claim (b) — the heterogeneous-parent hole.** `check/ir.py:178-192`: a `Resource` instruction has **one** `element_type` per slot, and a slot is one resource *name*. `ir_value_of` (`:198-202`) keys a cell-carrying `Ref` by the **parent's** name. So all children of one parent share one `element_type`, and `resource_types_from_kwargs` uses `out.setdefault(name, cls)` — **first element wins**. A `Deck`-parented reference set (a `Trash`, a `Plate`, a `TipRack` all have `parent == deck`) collapses to a single `element_type` chosen by iteration order. E-TYPE then decides `IsInstance` for every cell under that parent against one arbitrary sibling's class — combined with C4(a), a false `WILL_FAIL`.

**Claim (c) — tier smuggling.** §15.4 concedes O1 "is therefore a tier-(ii) input by §15.1's own definition". §15.6 recommends DEFER for tier (ii); §15.13 lists tier (ii) as "not in this increment". The gate's GO ("residual ⊆ {(ii),(iii)}") is then computed *with* a tier-(ii) observation supplied, on the operation whose tier-(i) clearance is the whole gate. The concession is honest but incomplete: §15.9(5)'s with/without delta measures whether O1 *matters*, not whether the residual is legitimately (i). And the "graph lane is tier (i) with no observation" escape (`:443-444`) is true of the *field* (`ir.py:695` reads `decl["element_type"]`) but says nothing about whether any real graph payload populates it — the spec offers no count.

**Minimal remediation.** (i) Restate O1's sizing honestly (a new element-walk keyed by `(parent_name, cell_name)`, not an extension of `resource_types_from_kwargs`). (ii) Specify per-cell element types, or state normatively that a parent with heterogeneous children yields `element_type = None` (fail-closed) and publish the count of such parents on the benchmark. (iii) Either add an AC that the gate is re-decided with O1 withheld, or state plainly that the increment's GO is conditional on one tier-(ii) observation.

---

## C12 — MUST-FIX — the instrument's own arithmetic does not close, and the 12 unaccounted operations are exactly the population that could refute Q1

**Location.** §15.0 (`:52-58`, `:98-102`), §15.5 (`:551-560`), §15.9 (`:748`), §15.14 Q1 (`:958-963`).

**The claim.** §15.0's table: `{guard_predicate_unparsed, unresolved_delegate}` = **93 ops**, annotated "`move_resource` 29 / `move_lid` 28 / `move_plate` 24" — **which sums to 81**. §15.9's table gives the same family as **81**. §15.5 asserts "Every one of the ten methods in the benchmark carries tier-(ii) guards".

**The attack.** From the ledger directly:
- `per_op_reason_set_histogram` (`:1892-1912`): 334 + 117 + **93** = 544. ✓
- The sole `unresolved_delegate` cluster (`:988-999`): `n_findings` 186 (= the whole `n_findings_by_reason` total for that reason, `:35`), `n_ops_blocked` **81**, `per_method` summing to 81.
- `unknown_ledger.py:133-141`: `per_method` is incremented once per *new* op, so `sum(per_method) == n_ops_blocked` identically.

**93 ops carry `unresolved_delegate`; the only cluster carrying it blocks 81.** Either the ledger is internally inconsistent by 12 ops, or `n_findings_by_reason` and the cluster accumulator disagree. The same 12 appear on the other side: `:375`'s `per_method` sums to **532**, not 544 — twelve executed operations carry no `_check_args` guard at all.

Those twelve are precisely §15.14 Q1's stated refutation criterion: *"A refutation would name one executed operation whose non-(iii) residual is empty."* The spec's coupling argument (§15.5) is asserted **per method**, over the ten named methods, and never checked **per operation** over the 544. It cannot be, because 12 of them are not attributable to any method in any cluster.

**Minimal remediation.** Band B0 reconciles the 93/81 and 544/532 gaps and names the 12 ops (row_id, op_id, method, full finding set) before §15.5's coupling claim or §15.9's candidate table is treated as complete. If any of the 12 has an empty non-(iii) residual, Q1's central finding — and the sprint's headline substitution — is falsified.

---

## C13 — MUST-FIX (user decision) — §15.8's reason 1 is false: α and β **can** produce a wrong predicate, which puts the row on HM-24 by increment 5's own B1 precedent

**Location.** §15.8 (`:665-699`), §15.3 (`:392-398`).

**The claim.** "The failure mode is neither silent nor a collapse… α binds nothing, the term is `Opaque`… **not a wrong verdict**." §15.3: "α/β can only produce `Opaque`, which is today's behaviour."

**The attack — two ways α/β produce a wrong term, not `Opaque`.**

1. **The single-write clause covers `x`, not the iterand.** α binds `Filtered(iter, pred)` where `iter` is a parameter of `K`; β binds `Len(x) = Len(p)`. §15.3's rebinding clause constrains writes to **`x`** only. Nothing constrains `iter`/`p`. PLR rebinds those routinely: `resources` at `:999`/`:1172`, `use_channels` at `:501`/`:650`/`:958`/`:1152`. A future PLR that moves `not_containers = [r for r in resources …]` below a `resources = [resource] * len(use_channels)` leaves α matching, binding a term over the **wrong** sequence, and yielding a *wrong* `SAFE`/`WILL_FAIL` — silently. No published count moves, because α's selection is unchanged.
2. **Cross-boundary name coincidence.** α is matched "in the body of the PLR function `K` that *defines* the guard", but the resulting term is evaluated by E-CALL against the **entry point's** `call.kwargs`. §15.3/§15.4 never specify the substitution from the delegate's parameter namespace to the caller's argument list. Today `_check_containers(self, resources)` works only because the parameter is *also* called `resources` at the `aspirate` call site (`liquid_handler.py:956`). `_make_sure_channels_exist(self, channels)` (`:405`) does not coincide and fails closed to ⊤ — by luck, in both directions. A PLR rename in either direction flips a guard between correct, silent-`Opaque`, and *silently wrong*, with no test able to see it.

**Consequence for the registry.** Reason 1 is the leg §15.8 explicitly says it rests on ("The distinction this document rests on is reason 1"). With reason 1 gone, the increment-5 precedent applies directly: round-1 O12 on the volume spec put B1 on HM-24 because "its failure mode is HM-24's (silent) rather than HM-25's (loud)" (`260903_plr-sema-volume-round1-challenger.md:414`), user-approved 260904, and HM-24's own `what` field now records B1 there because "R1 (§14.6) makes its `ast.For` node load-bearing for SOUNDNESS" (`_hand_maintained.py:853-861`). α's `ast.ListComp` and β's `ast.BoolOp` are load-bearing for soundness in exactly the same way. **HM-24 3 → 4 is a per-row ceiling spend, and per the sprint plan §3.4 it is a user decision before band B spends it.**

**Minimal remediation.** Either (a) add the iterand/`p` to the single-write requirement *and* specify the delegate→caller substitution normatively (which restores reason 1 and might genuinely justify zero rows — I would then re-evaluate), or (b) concede HM-24 3 → 4 and take it to the user before T30.

---

## C14 — MUST-FIX — E-CALL's resolution order makes β dead for its own use case, and Python truthiness is nowhere modelled

**Location.** §15.4 E-CALL (`:405-409`), §15.3 β (`:355-358`).

**The attack (a) — β is unreachable.** E-CALL resolves `(1) call.kwargs[name]`, `(2) contract default`, `(3) α/β binding`. For `:522`'s `len(offsets)`: if the planner bound `offsets=None` the kwarg is `Lit(None)` and step (1) wins ⇒ `Len(Lit)` is ⊤ (E-CALL's own last sentence) ⇒ `:522` is ½. If `offsets` is absent, step (2) returns the *signature* default, which is `None` ⇒ same ⊤. **Step (3) is reached only when a parameter is both absent from kwargs and has no recorded default** — which is never true of an `or`-defaulted parameter. β, whose entire purpose is "the caller passed nothing, so PLR substituted a length-`len(p)` default", can never fire. §15.9's `pick_up_tips` row depends on `:522` clearing "via G2 + β + P3a".

**The attack (b) — `[]` is falsy.** `x = x or <default>` fires the default when `x` is `[]`, not only when it is `None`. Nothing in §15.3 or §15.4 mentions truthiness. Two symmetric errors: (i) a call passing `offsets=[]` resolves via step (1) to `Seq([])`, `Len == 0 ≠ len(tip_spots)` ⇒ assert-kind guard fires ⇒ **false `WILL_FAIL`**; (ii) a call passing a non-empty `offsets` correctly resolves via step (1) — so if the ordering is "fixed" naively by making β take precedence, β would override a real caller-supplied list and produce a **false `SAFE`** on the exact mismatch `:522` exists to catch.

**Minimal remediation.** Restate E-CALL's β interaction explicitly: *a `Var(name)` that is the target of a β assignment resolves to the β-bound `Len` **iff** the call-side resolution yields a value that is statically known-falsy (`Lit(None)`, `Lit(false)`, empty `Seq`); to the call-side value iff it is statically known-truthy; and to ⊤ otherwise.* Add a fixture per branch to AC-15.2.

---

## C15 — SHOULD-FIX — the three-reason taxonomy has no bucket for a nested `Opaque`, so "the residual `guard_predicate_unparsed` count *is* the grammar's coverage gap" is false

**Location.** §15.7 (`:619-644`).

**The attack.** §15.3's own worked example: `invalid_channels = [c for c in channels if c not in self.head]` (`liquid_handler.py:407`) — "α binds the term and the predicate stays ½. **That asymmetry is the point**". The guard `not len(invalid_channels) == 0` therefore parses to a **non-`Opaque` top node containing an `Opaque` sub-predicate**, with every free name **bound**. It is not `guard_predicate_unparsed` (the top node parsed), not `guard_operand_unknown` (no call operand is ⊤ — the failure is a *syntactic* one inside the comprehension's `if`), and not `guard_env_dependent` (the free name resolved via α). All three §15.7 definitions exclude it; there are 384 such findings (`unknown_ledger:127`).

This also falsifies §15.7's own legibility argument: "the residual `guard_predicate_unparsed` count *is* the grammar's coverage gap" (`:643-644`). Nested `Opaque`s are genuine coverage gaps that vanish from that count, so the ledger delta §15.10 asks a reader to interpret systematically *overstates* coverage.

**Minimal remediation.** State that a predicate containing any `Opaque` node **is** `Opaque` for reason-assignment purposes (keeping `guard_predicate_unparsed`), while still being evaluated under Kleene so an `And` with an `F` conjunct can still decide. That is a two-line rule, costs no vocabulary slot, and restores §15.7's legibility claim.

---

## C16 — SHOULD-FIX — §15.8's "every key it produces is byte-identical to today's" is false; `contracts_sha` moves for every consumer

**Location.** §15.8 (`:701-707`).

**The attack.** `cache_key` is `(bc_hash, contracts_sha, surface_identity, ir_version, env)` (`check/ir.py:918-953`), and `contracts_sha = sha256(contracts_json)`. T30 adds `InlinedGuard.predicate` and **regenerates `plr-sema/data/derived_contracts.json`** (§15.12 T30's files list, `:907`). Every key moves, for every caller, not just the benchmark. The spec attributes the movement to O1's `bc_hash` alone and concludes "the cache is neither invalidated nor partitioned" in the same paragraph that says "the benchmark's keys move". The behaviour is correct (a full re-computation, not a correctness event) — the *statement* is wrong, and `test_cache.py` may pin a key.

**Minimal remediation.** One sentence: the contract-table regeneration moves `contracts_sha`, so the whole cache is cold after T30 by design; `env` is untouched, which is the property that actually matters.

---

## C17 — SHOULD-FIX — §15.6's cost argument for deferring tier (ii) overstates the backend-signature derivation

**Location.** §15.6 (`:589-609`), §15.14 Q2 (`:964-968`).

**The `strictness` half is correct and I concede it.** `liquid_handler.py:381` is verbatim `if len(extra) > 0 and len(vars_keyword) == 0:` with `extra = backend_kws - set(args.keys())` at `:380` over `inspect.signature(method)` at `:353`. An `env` member for `strictness` converts ½ to ½. (Note in passing that `:377`'s `if len(vars_keyword) > 0: return set()` makes `:381`'s second conjunct dead — an early-return fact that also reinforces C1.)

**The attack is on the second half.** "the increment must AST-derive the backend class's method signatures, which is a new derivation over a new class surface, with its own measured selection and its own registry argument. That is a whole increment's work." On the frozen benchmark the backend is a **single, named, literal class**: `example.get("backend", "LiquidHandlerChatterboxBackend")` (`oracle_common.py:362`). It is not a surface, it is one class whose `pick_up_tips`/`aspirate`/`dispense` signatures are AST-derivable by the machinery the derive package already runs over PLR. That would decide `len(missing) > 0` at `:375` — the cluster blocking 532 of 544 ops — and, via `:381`, `strictness` too. §15.6 prices the general case and charges the specific case for it.

I am not arguing tier (ii) should ship; C1–C6 make that reckless. I am arguing the *stated reason* for deferral is wrong, and Q2's disposition should say "deferred because the increment already has more soundness risk than it can carry", not "because it is a whole increment's work".

---

## C18 — NOTE — citation defects (15 spot-checked; 13 clean)

Read at the cited lines. Clean and supporting: `derive/__init__.py:458-463`, `:466-472`, `:528`, `:536-537`; `check/__init__.py:298-312`; `_hand_maintained.py:43`, `:613-631`, `:841-896`, `:934-951` (the "Fails LOUDLY here (unlike HM-24)" text is at `:945`), `:957-961`; `ir.py:178-192`, `:194-204`, `:918-944`; `tipstate.py:245`, `:521-536`; `survey_plr_preconditions.py:177-189`, `:191-209` (the `"else of: if …"` push is at `:206`), `:211-218`; `oracle_common.py:251-274`, `:277-308`, `:340/:350/:370-373`, `:397-410`; `260901…:576-581`, `:765-768`, `:781-788`; `260902…:752`; `liquid_handler.py:381-383`, `:496-502`, `:517`, `:522`, `:645-647`, `:661`, `:666`, `:873-875`, `:981-992`, `:1182-1188`, `:1333-1340`, `:1739-1743`.

Two do not support the claim:

- **AC-15.12 (`:891`)** — "the observation is returned from inside the executed window as increment 5's `volume_tracking_observed` is (`plr-sema/eval/oracle_common.py:593-595`)". Lines 593-595 are `run_static_calls` **constructing** `env` from an already-returned flag. The return from inside the window is at `:372` (`bool(result.get("volume_tracking_observed"))` in `run_runtime`). The citation names the consumer as if it were the producer.
- **§15.5 (`:515`)** — `260901…:103` / `:3327-3330` cited for `SoundnessScope`. Neither defines it (see C10). `:103` is itself a forward reference to `260901_plr-sema-research-b-f.md`.

Also: `oracle_common.py:284-292` is cited for the `infer_layout()` fact; the sentence actually spans `:286-292` — inside the range, fine, but flagged because the lint checks range/symbol, not meaning, and the range was chosen two lines early.

---

## Ranked — the five most consequential

1. **C1** — `<unconditional>` × E-UNCOND ⇒ ~268 false `WILL_FAIL`s on clean operations. Fails AC-15.8 and AC-15.9 at T32, after both other tasks have landed. The single largest defect.
2. **C3** — the `excludes_sites` narrowing rests on an `exc_class → site` taxonomy that does not exist and cannot be injective; it excuses precisely the rows the fence exists to catch. Q6 answers "yes, worse than it appears".
3. **C4** — E-TYPE's `F` rule is unsound for supertype declarations (`Trash → "Container"` is live on `discard_tips`), and its equality-only `T` rule falsifies §15.9's `:875` prediction. This is the *soundness of the grammar's one type atom*, which is also the atom the gate rests on.
4. **C5** — AC-15.8's ≥1,000 floor is met by `:375` + `:383` alone via the reason rename, so the increment's headline measurement can pass with nothing decided.
5. **C2 / C6 (tie)** — C2: `caller_scope` does not exist on `InlinedGuard`, so E-SCOPE/E-UNCOND are undefined for every depth-1 guard and the two readings differ by 268 ops. C6: §15.3's own rebinding clause deletes all eight β sites §15.3 names as β's population, falsifying AC-15.2's floor and §15.9's dispense row.

## Objections that change go/no-go or require a user decision

- **C13** — if conceded, **HM-24 3 → 4** is a per-row ceiling spend, a user decision *before band B starts* (sprint plan §3.4, `260904_plr-sema-sprint127-predicates.md:132-135`). §15.8's "neither row" position does not survive the loss of reason 1.
- **C12** — if any of the 12 unaccounted operations has an empty non-(iii) residual, §15.5's coupling finding is refuted, the "headline moves to increment 7" substitution is unnecessary, and the §15.14 Q1 stop-and-ask changes shape. This must be resolved by measurement, not argument, before the user is asked to approve the substitution.
- **C6 + C14 together** — if both stand, §15.9's `pick_up_tips` row (`:498` α+O1, `:502` G4+P3a, `:522` G2+β+P3a) loses `:522`, and the gate has **no** predicted GO candidate at all. That converts §15.9 from "single point of failure" to "predicted NO-GO", which is a different sprint and a different user conversation.
- **C11(c)** — the user should be told plainly that the gate's GO depends on a tier-(ii) observation in an increment that defers tier (ii).

## The one thing the spec does not say

**How a `depth >= 1` guard's free variables are mapped from the delegate's parameter namespace into the entry point's call kwargs.** Every guard on `pick_up_tips` except `:498`, `:502`, `:522`, `:535`, `:576` is at depth 1 (`_check_args`, `_check_containers`, `_check_no_lid`, `_make_sure_channels_exist`, `_assert_resources_exist`), and that is true of every method in §15.1's tables. §15.3 matches α/β "in the body of the PLR function `K` that *defines* the guard"; §15.4 E-CALL evaluates the resulting terms against `call.kwargs` of the *entry point*. Between those two sentences sits an entire inlining substitution — argument position → parameter name, positional and keyword, across a `delegates_to` edge the derive package does not record arguments for — and it is nowhere in the spec, nowhere in the AC set, and unbudgeted in T30's ~420 lines. Today it works for `_check_containers` only by name coincidence (`liquid_handler.py:956` passes a local also called `resources`) and fails closed for `_make_sure_channels_exist` only by name *non*-coincidence. That is the assumption an implementer will make silently, and it is the same assumption C2 and C13(2) each break from a different side.

**Verdict: `needs_revision`.** Confidence: high. C1, C3, C4, C5, C6 are each independently sufficient to fail the increment's own acceptance criteria; C2, C8, C9, C10, C11, C12, C14 leave an implementer with normative text they cannot execute without inventing the missing rule. §15.2's grammar (G0–G6), §15.2's tipstate/volume dispatch rule, and §15.6's `strictness` evidence are sound and should survive revision intact.
