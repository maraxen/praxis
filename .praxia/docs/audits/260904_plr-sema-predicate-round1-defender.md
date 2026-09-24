---
title: 'plr-sema increment 6 (predicate language) -- adversarial round 1, defender report'
description: 'Defender report (praxia:spec-defender, Opus) on .praxia/docs/specs/260904_plr-sema-predicate-increment.md spec_version 16 draft against the challenger C1-C18: adjudications (C12 REBUTTED -- the 93/81 gap is (row_id, op_id) set dedup under content-digest collisions; C3/C9/C10 collapse into one free change -- drop the fence narrowing, tier (iii) emits UNKNOWN/guard_env_dependent; C13 registry -> HM-25 8->9 not HM-24, a user decision), three defender-identified gaps (D1 BLOCKER: E-CALL step (2) recorded default does not exist -> param_defaults; D2 channels_for_call exact-set count must be measured; D3 self-entry in scope_trail[0]), eighteen-item ordered remediation list, four user decisions, revised gate prediction (pick_up_tips GO survives C6+C14), verdict needs_revision.'
status: final
task_id: 260904_sema-predicates
date: '260905'
sprint: '127'
backlog_ids: '4977'
---
> Persisted verbatim by the orchestrator from the defender agent's final report (the agent has no
> write tool). Target: `.praxia/docs/specs/260904_plr-sema-predicate-increment.md` at commit
> `6407d92a`. Challenger companion: `260904_plr-sema-predicate-round1-challenger.md`.
> Note (orchestrator, 260905): item 17 of the remediation list (the ledger `row_id` fix) landed as
> `ca756bce` before this report was persisted -- the ledger now keys ops positionally; the
> `unresolved_delegate` cluster reports 93 and `:375`/`:383` report 544; the 12 collision ops are all
> `move_*` with reason set exactly `{guard_predicate_unparsed, unresolved_delegate}`.

# plr-sema increment 6 — adversarial round 1, defender

Target: `/home/marielle/projects/praxis/.praxia/docs/specs/260904_plr-sema-predicate-increment.md` (spec_version 16, 1027 lines). Challenger: `/home/marielle/projects/praxis/.praxia/docs/audits/260904_plr-sema-predicate-round1-challenger.md` (C1–C18).

**Tooling disclosure.** No Bash tool. No `pytest`, `git rev-parse` or `rg` run. Every citation below is from Read (`cat -n` line numbers) or Grep. AC-15.11's lint prediction could not be executed and is carried into the remediation list as an item requiring execution, not judgement.

**Headline.** The challenger is right about ten of eighteen in whole or in part, and two of his six blockers rest on factual errors I correct below. But the report's structure hides the two things that actually matter: **C3, C9 and C10 collapse into a single change that costs the increment nothing** (because §15.5 already concedes there is no joined `SAFE`), and **C12 is arithmetically resolvable from the accumulator and is not a hole in Q1**. Against that, I raise three defender-identified gaps the challenger missed, one of which (D1) is a blocker that independently falsifies §15.9's `transfer` row and C14's own premise.

---

## C1 — BLOCKER as filed — **PARTIAL. The mechanism is CONCEDED and live. The magnitude is overstated by 54 ops, and the gate candidate is untouched.**

### What is true, verified

`scripts/survey_plr_preconditions.py` overrides exactly six visitors — `visit_If` (`:191`), `visit_For`/`visit_AsyncFor` (`:211`/`:220`), `visit_While` (`:222`), `visit_Raise` (`:231`), `visit_Assert` (`:256`), `visit_Call` (`:259`). **There is no `visit_Try` and no `visit_Return`.** Confirmed by exhaustive grep of `def visit_` over the file. So a `raise` after an early `return`, and a `raise` inside an `except` handler, both carry an empty `scope_trail`. `_check_no_lid` at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:110-120` is exactly that shape, read directly:

```
112    lidded = _lidded_ancestor(resource)
113    if lidded is None:
114      return
115    if lidded is resource:
116      raise ValueError(...)
117    raise ValueError(          # statement position, EMPTY trail, condition None
```

And the shipped precedent settles the reading the challenger says is undecided. `volume_guard_is_unconditional` (`plr-sema/src/plr_sema/derive/receiver_state.py:2056-2094`) fails closed **only on `None`** (`:2079-2080`); an **empty list falls through the loop and returns `True`** — vacuous satisfaction, in shipped code, documented as such at `:2067-2069`. An implementer following the one precedent in the tree implements C1's blowup. **Conceded: the vacuous reading is not merely available, it is the one already in the repo.**

`compare`'s unsound predicate is verbatim as quoted (`plr-sema/eval/oracle_common.py:645-647`), and `join`'s "any `WILL_FAIL` ⇒ `WILL_FAIL`" (`.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:579`) propagates one false finding to the whole operation. AC-15.8 fails by construction.

### What is not true — 54 of the 268 ops

`:1770` (`aspirate96`) and `:1920` (`dispense96`), 27 ops each, are **not** empty-trail cases. Read at `liquid_handler.py:1761-1773`: the `raise TypeError` sits in the `else:` of a three-branch `if`/`elif`/`elif` chain. `visit_If` pushes `"else of: if …"` for every `orelse` (`:206`) and an `elif` self-nests (`:200-209`), so `:1770`'s trail is three `"else of: if …"` entries deep. E-UNCOND already blocks those explicitly — *"an entry beginning `"else of: if …"` is recognised **only** by way (1)"* (`:486-487`) — and way (1) requires the negated `isinstance` test to evaluate `T`, which under a corrected E-TYPE (C4) it never will. **`:1770`/`:1920` are already fail-closed by the spec as written.** The challenger's table conflates "condition is `<unconditional>`" with "trail is empty"; the two coincide only when the nearest trail entry does not start with `"if "` **and** there is no enclosing scope at all.

A second correction with the same root: `visit_Raise` sets `condition` from `scope_trail[0]` when and only when that entry starts with `"if "` (`:247-248`), **without popping it**. So every `raise_guard` with a non-null condition has a non-empty trail whose first entry *is* its own condition. The vacuous-satisfaction population is therefore exactly: null-condition guards with no enclosing `if`/`for`/`while` — `:117` (163 ops), `:2092` (81 distinct ops), and the four `assert`-kind guards' analogues. Roughly 244 ops, not 268, and `:2092`'s 81 are the `move_*` family §15.0 already excludes from every candidate list.

### What it costs the gate: nothing

`pick_up_tips` carries no `<unconditional>` guard — §15.1.1's ten-row table has none, and `_check_no_lid` is not in its closure. C1 is fatal to AC-15.8 and AC-15.9 and harmless to §15.9's GO candidate.

**Remediation — adopt the challenger's (ii) plus a strengthened depth-0 clause.** Both, normatively, in E-UNCOND:

> **E-UNCOND(4), depth.** No guard at `depth >= 1` may emit `Verdict.WILL_FAIL` in this increment. Its `Finding` is `Verdict.UNKNOWN` with `reason="guard_env_dependent"`.
>
> **E-UNCOND(5), the empty trail.** A guard at `depth == 0` whose `scope_trail` is empty is **not** vacuously unconditional. It may emit `WILL_FAIL` only if `K`'s body contains no `ast.Return`, `ast.Try`, `ast.Raise`, `ast.Break` or `ast.Continue` at any nesting depth at a `lineno` lower than the guard's. Otherwise `½` and `guard_env_dependent`. This clause exists because `scripts/survey_plr_preconditions.py` pushes trail entries for `ast.If`/`ast.For`/`ast.While` only, so a preceding early return leaves no trace in the record the evaluator reads.
>
> **E-UNCOND(6), the self-entry.** For a `raise_guard` whose `scope_trail[0]` is `"if " + condition`, that entry is the guard's own condition (`survey_plr_preconditions.py:247-248`, which reads it without popping) and is excluded from both E-SCOPE and E-UNCOND, which range over `scope_trail[1:]`.

Acceptance check: a fixture over `_check_no_lid`'s `:117` yields `UNKNOWN`/`guard_env_dependent`, asserted by name, in AC-15.6.

---

## C2 — BLOCKER as filed — **CONCEDED. The field does not exist and the two readings do differ.**

Verified. `InlinedGuard` (`plr-sema/src/plr_sema/derive/__init__.py:452-478`) has exactly seven fields — `condition`, `scope_trail`, `raises`, `kind`, `free_vars`, `site`, `depth`. **No `caller_scope`.** `caller_scope`/`caller_lineno` are attached only inside `compute_volume_bridge`'s per-guard JSON (`derive/receiver_state.py:1962`, `:1985-1986`), i.e. only to `volume_guards`, and `volume_guard_is_unconditional` is the only consumer (`check/volumestate.py:425-426`).

E-SCOPE's "for a bridged guard, of its `caller_scope`" is therefore vacuous for every guard in §15.1's tables, and "a `null` scope" has no referent. E-UNCOND is not a generalisation of increment 5 §14.6 on this type; it is silent on it. Conceded in full.

**Remediation: the challenger's (ii), which E-UNCOND(4) above already states.** Do not build the `InlinedGuard` P10 equivalent this increment — it is genuinely unbudgeted in T30's ~420 lines and it is entangled with the unspecified substitution (see D-list / "the one thing the spec does not say"). §15.9's predicted residuals do not move: every depth-1 guard on `pick_up_tips` (`:375`, `:383`, `:409`, `:321`) is already predicted tier (ii)/`guard_env_dependent`, and the three guards the gate rests on (`:498`, `:502`, `:522`) are all at depth 0 in `pick_up_tips`'s own body.

Acceptance check: AC-15.6 gains a fixture asserting a depth-1 guard whose predicate is `T` yields `UNKNOWN`, not `WILL_FAIL`.

---

## C3 — BLOCKER as filed — **PARTIAL. The "no taxonomy exists" claim is FACTUALLY WRONG. The non-injectivity is CONCEDED and is fatal. Drop the narrowing — and it costs nothing, for a reason the challenger does not give.**

### The factual correction

`training/verify/data/plr_exception_taxonomy.json` is exactly an exception-class → PLR-raise-site mapping, version-stamped at the same pin (`"git_sha": "dd79c4c89bc008629a1c598ea614be5e6067d1f9"`, `:4`), carrying 132 classes each with `trigger_sites: [{file, lineno, enclosing_function, enclosing_condition, kind}]` (`:20-28`). The challenger's "there is no taxonomy anywhere in the repo mapping an exception class name to a PLR raise site" is wrong.

### Why it does not save the narrowing

The taxonomy covers **PLR-defined** classes only. Grep for `"name": "(TypeError|ValueError|RuntimeError|AssertionError|NotImplementedError)"` returns **no matches**, and grep for `"lineno": (575|576|725|726|1066|1067|1270|1271|2092)` returns **no matches**. So the taxonomy contains neither the builtins the benchmark actually raises nor any of the tier-(iii) re-raise sites. Building the mapping the spec assumes would mean *inventing* it, and it could not be injective: a re-raise carries the backend's own exception class, which is unbounded by construction.

Worse, `run_runtime` has nothing better. `exc_class = error.split(":", 1)[0].strip()` (`oracle_common.py:368`) over `error = f"{type(e).__name__}: {e}"` (`training/verify/verifier.py:144`). Reliable as a class name, useless as a site. **No traceback is captured anywhere** — `verify()`'s two return dicts (`:150-162`, `:184-194`) carry `error` as a string and nothing else. The challenger's second option (`traceback.extract_tb(...)[-1]`) is available at `verifier.py:143`'s `except Exception as e` and costs ~3 lines, and it is *better* than he realises: for `raise error` at `:576`, the re-raised exception retains its original traceback, so `extract_tb[-1]` is the **backend's** deepest frame, cleanly distinguishable from a PLR-layer raise at `:498`.

### The disposition, and why it is free

**Take the first option: drop the narrowing.** The tier-1 unsoundness predicate stays exactly `oracle_common.py:645-647`, unmodified. `rows_excused_by_scope` is published as a pure annotation with **no effect on any gate**.

This costs the increment nothing, because §15.5's own central finding is that **no operation reaches a joined `SAFE` this increment** — every one carries tier-(ii) guards. A narrowing that only bites on `SAFE`-on-raise rows therefore has no rows to bite on. The spec is weakening its own fence to buy a result it simultaneously proves it cannot obtain. **§15.14 Q6 answers itself: yes, it weakens the fence, and the weakening purchases nothing.**

Under this disposition, C9 and C10 also resolve (below), and the ~10-line traceback change moves to increment 7, where a joined `SAFE` first becomes possible and the fence actually needs the discrimination.

Acceptance check: AC-15.8 asserts `unsound == 0` under the **unmodified** predicate; `rows_excused_by_scope` is published with no threshold; no `exc_class` mapping is constructed anywhere in T32.

---

## C4 — BLOCKER as filed — **CONCEDED in full. The restatement is correct, sufficient, and keeps `:498` decidable in the `SAFE` direction.**

Both attacks verified live.

**(a)** `_PLR_GENERIC_RESOURCE_NAMES` (`oracle_common.py:225-232`) contains `Container`, not `Trash`; `_generic_plr_type_name` (`:235-248`) walks `type(obj).__mro__` most-to-least specific and returns the first name in that set. `external/pylabrobot/pylabrobot/resources/trash.py` declares `class Trash(Container)`. So under O1 a `Trash` records `"Container"`, and `liquid_handler.py:645-647`'s `(TipSpot, Trash)` tuple test yields E-TYPE **F** ⇒ `Not` **T** ⇒ `AnyOf` **T** ⇒ a false `WILL_FAIL` on `drop_tips`/`discard_tips`. The declared type is an upper bound and the `F` rule treats it as exact.

**(b)** `Well` is in the generic set, so `_check_containers`'s `isinstance(r, Container)` (`liquid_handler.py:871-875`) gets declared `"Well"`: not equal ⇒ not `T`; `Well(Container)` ⇒ the `F` clause's disjointness conjunct fails ⇒ ½. §15.9's `aspirate` row (`:744`, "`:959` and `:875` clear") is false as written. The derived subclass relation is used only in the `F` clause, never in the `T` clause — the challenger's diagnosis is exact.

**Adopt the challenger's restatement verbatim, with one addition.** Replace E-TYPE's second sentence with:

> `IsInstance(t, (T₁ … Tₙ))` is **`T`** iff the declared name **is, or is a subclass of, some `Tᵢ`**; **`F`** iff the declared name and every `Tᵢ` are **disjoint in the class hierarchy** (neither is an ancestor of the other) **and** the declaration is known to be **exact**; **½** otherwise. **A declaration derived from `_generic_plr_type_name` (`plr-sema/eval/oracle_common.py:235-248`) is never exact** — it returns the most-specific *generic* ancestor, not the concrete class, so on the frozen benchmark the `F` branch is unreachable and every `IsInstance` atom is `T`-or-`½`. A declaration read from a graph-lane `RESOURCE` (`plr-sema/src/plr_sema/check/ir.py:694-695`) is exact iff the graph payload marks it so; absent such a mark, it is not exact.

I verified this keeps the gate: `TipSpot` is in the generic set and is its own most-specific match, so `:498`'s `element_type` is `"TipSpot"` ⇒ `IsInstance` `T` ⇒ `Not` `F` ⇒ `AnyOf` `F` ⇒ `raise_guard` does not fire ⇒ **`SAFE`**. `:875`'s `Well ⊂ Container` ⇒ `T` ⇒ `SAFE`, restoring §15.9's `aspirate` row for that guard. `:647`'s `Container` vs `(TipSpot, Trash)` ⇒ not disjoint (ancestor of `Trash`) ⇒ ½ ⇒ fail-closed, no false `WILL_FAIL`.

Acceptance check: AC-15.1 gains a fixture asserting `IsInstance(declared="Container", (TipSpot, Trash))` is `½` and `IsInstance(declared="Well", (Container,))` is `T`.

---

## C5 — BLOCKER as filed — **CONCEDED. The floor is met by the rename alone. Here is the replacement, derived from §15.9's own table rather than invented.**

Verified from the ledger: `:375` `len(missing) > 0` is 544 findings (`unknown_ledger_260904_before.json:39-57`), `:383` `strictness == Strictness.STRICT` is 544 (`:81-99`), `:409` `not len(invalid_channels) == 0` is 384 (`:123-133`). All three parse to non-`Opaque` predicates under G1 and all three decide nothing — the spec itself tiers them (ii) and defers them in §15.13. 1,088 > 1,000 from two clusters, before a single guard is evaluated.

**Replacement for AC-15.8's floor:**

> The published number is **`n_findings_decided`** — findings whose emitted `verdict` is `Verdict.SAFE` or `Verdict.WILL_FAIL` — broken down **per PLR site**, with a floor of **≥ 223**. 223 is `pick_up_tips`'s own operation count from §15.9's candidate table, i.e. the minimum implied by one of its three tier-(i) guards clearing on every op; it is derived from the document's own prediction rather than asserted. `guard_env_dependent` and `guard_operand_unknown` counts are published **separately** and are explicitly **excluded** from "converted". The `guard_predicate_unparsed` delta is still published, with **no floor**, as the grammar's coverage measure only.

Acceptance check: an implementation that parses every condition and resolves nothing yields `n_findings_decided == 0` and fails.

---

## C6 — BLOCKER as filed — **PARTIAL. Consequence 1 is REBUTTED with a sound narrower clause that keeps eight β entries. Consequences 2 and 3 are CONCEDED.**

### The eight second writes, verified

Read directly at `liquid_handler.py:962-971`, `:1004`, `:1156-1165`, `:1177`. Every one of the challenger's eight rows is correct.

### The ordering question the mandate asks, answered

`:969-971` (aspirate) sit **before** the guard at `:989-990` that reads them. `:1163-1165` (dispense) sit **before** `:1183`, `:1184`, `:1187` and `:1201`. So the challenger's own suggested narrowing — "no write between the β line and the guard line" — **saves none of the six**. That option is dead and should not be pursued.

### The clause that does work, and it needs no reaching-definitions pass

Read the six writes literally:

```
969    flow_rates = [float(fr) if fr is not None else None for fr in flow_rates]
970    liquid_height = [float(lh) if lh is not None else None for lh in liquid_height]
971    blow_out_air_volume = [float(bav) if bav is not None else None for bav in blow_out_air_volume]
```

Each is a single-comprehension list comprehension **over `x` itself, with no `if` clause** — the conditional is an `ast.IfExp` in the element expression, not a comprehension filter. **`Len(x)` is preserved exactly.** Since β binds *only* a length (§15.3's own restriction, `:357-358`), this write cannot invalidate a β binding. Contrast `:1004`/`:1177`, `offsets = [c + o for c, o in zip(center_offsets, offsets)]` — the `iter` is a `zip(...)` call, not the bare name, so the length is `min(...)`, not preserved; and both sit inside `if len(set(resources)) == 1:`. `offsets` correctly stays `Opaque`.

> **Normative (β-preserving rebinding).** A second write to `x` of the form `x = [<elt> for <e> in x]` — a single `ast.ListComp` with exactly one `comprehension`, no `if` clause, `is_async` false, a bare-`ast.Name` target, and an `iter` that is the bare `ast.Name` `x` itself — **preserves `Len(x)`** and does not invalidate a β binding, which binds only `Len(x)`. Every other second write to `x`, and every second write of any shape to an **α**-bound `x` (α binds elements, not a length), makes the binding `Opaque`.

Under this clause β's population at this pin is **eight**: `flow_rates`/`liquid_height`/`blow_out_air_volume` in `aspirate` (`:963-965`) and in `dispense` (`:1157-1159`), plus `:517` and `:661`. **AC-15.2's `≥ 6` floor holds and should be published as an exact measurement, not left as an assertion.**

### Conceded

**Consequence 2.** β "binds no elements", and `any(bav is not None and bav != 0.0 for bav in blow_out_air_volume)` at `:1183` needs elements. Even a β element-binding extension for the `[<Lit>] * len(<p>)` form would die at `:1165`'s comprehension, which preserves length but not (syntactically) elements. E-SCOPE gets ½, not `F`. **`:1185`/`:1188` do not clear**, and §15.1.3's "the increment's cleanest result" paragraph (`:194-200`) must be deleted, not softened.

**Consequence 3.** §15.9's `dispense` row's "`:1185`/`:1188` clear via E-SCOPE" (`:745`) is false. This changes nothing at the gate — `dispense` is NO-GO on `:1202`/γ regardless — but the document must not carry a false worked example, least of all one it labels its cleanest.

Acceptance check: AC-15.2's β fixture set gains one case asserting `x = [f(e) for e in x]` preserves a β length binding and one asserting `x = [f(a,b) for a,b in zip(y,x)]` does not.

---

## C7 — MUST-FIX as filed — **PARTIAL. (a) CONCEDED. (b)'s forbidden-literal half CONCEDED; (b)'s "collision" half REBUTTED — `channels_for_call` already implements E-CALL's ordering.**

**(a) Conceded.** §15.3's single-write clause protects α/β-bound locals and says nothing about parameters PLR rebinds before a guard reads them. Verified live: `use_channels` at `:501`/`:650`/`:958`/`:1152`, `resources` at `:999`/`:1172`, `vols` at `:968`/`:1162`, `ratios` at `:1343`. Adopt his wording, symmetric with §15.3:

> **E-CALL(5).** A `Var(name)` naming a parameter of `K` that is written anywhere in `K` at a `lineno` below the guard's resolves to ⊤, unless that write is a β-preserving rebinding (§15.3) and the term is a `Len`.

**(b) forbidden literal — conceded, verbatim.** `plr-sema/src/plr_sema/check/tipstate.py:254-257` reads exactly as quoted: `channel_kwarg` is *"read from `receiver_state`'s own derived `channel_kwarg`, **never hand-typed as `"use_channels"` here — that string is one of AC-13.15(iii)'s forbidden literals**"*. §15.3's normative box (`:368`) types it. Restate as: *"The grammar consults `channels_for_call` (`plr-sema/src/plr_sema/check/tipstate.py:245`) for every term naming the receiver's derived `channel_kwarg` or its `channel_default_param[method]`, and never re-derives it."*

**(b) collision — rebutted.** `channels_for_call`'s body is `explicit = _int_seq(call.kwargs.get(channel_kwarg))` first, `channel_default_param.get(call.method)` second (`tipstate.py:262-269`). That **is** E-CALL step (1) followed by a fallback. The two rules cannot disagree, because the shipped function already resolves the kwarg first. There is nothing to arbitrate; the spec should say so in a clause rather than leave the reader to check.

---

## C8 — MUST-FIX as filed — **PARTIAL. The hand-typed-site-list horn is REBUTTED with a shipped derived property. The tier-tautology point is CONCEDED and is worse than filed — the challenger's own remedy makes the gate self-satisfying.**

### Tier (iii) is already derived, at zero registry cost

`InlinedGuard.is_dynamic_raise` (`plr-sema/src/plr_sema/derive/__init__.py:474-478`) returns `raises.startswith("<dynamic:")`, set by `survey_plr_preconditions.py:234-240` for `raise <ast.Name>` — the D18 sentinel. Grepping `^\s*raise [a-z_][a-zA-Z_0-9]*\s*$` over `liquid_handler.py` returns **exactly seven** sites: `:576`, `:726`, `:1067`, `:1271`, `:1510`, `:1590`, `:2092`. That is precisely §15.1's tier-(iii) population — `error is not None` "and its three siblings", **plus `:2092`**, which the challenger correctly says a syntactic `condition == "error is not None"` rule would miss. And `dynamic:` already appears 146 times in the shipped `plr-sema/data/derived_contracts.json`.

> **Normative (tier (iii) is derived).** A guard is tier (iii) **iff** `guard.is_dynamic_raise` — a re-raise of a locally-bound exception name. No site list, no `condition` text match, no new pattern, no registry row. §15.8's "zero rows" survives on this point.

### The tautology, which the challenger introduces and must not be adopted

His proposed derived tiering is *"condition parses non-`Opaque` ∧ all free names resolve ⇒ (i); … else (ii)"*. Under that definition **every guard this increment fails to decide is (ii) by construction**, so every operation's residual is ⊆ {(ii), (iii)} trivially and §15.9's GO gate **always passes**. That is strictly worse than transcribing §15.1's table. The gate must not be stated over derived tiers at all.

**Remediation — restate §15.9's gate over reasons, which are shipped, mechanical and non-tautological:**

> **GO iff ≥ 1 executed real operation carries zero findings whose `reason` is `guard_predicate_unparsed` or `guard_operand_unknown`** — i.e. every guard on it is either decided (`SAFE`/`WILL_FAIL`), or undecided because a free name resolves to state outside the call (`guard_env_dependent`), or a derived tier-(iii) re-raise. §15.1's (i)/(ii) tiering is published as **this document's prediction**, and T30's block (3) publishes, per cluster, the reason each guard **actually** carries, so any divergence between prediction and measurement is visible rather than absorbed.

That is the form under which §15.9's own framing — *"to be falsified by the measurement and not assumed by it"* — is satisfiable.

### Two smaller concessions inside C8

- §15.1.3's table (`:188`) tiers `:117` as "(ii) lid topology". It has no operands; `parse(None) = TRUE` makes it `T`, not ½. Retier it as **(iii)-adjacent / unreachability-blocked** and let E-UNCOND(4)/(5) dispose of it.
- §15.1.4 enumerates seven conditions for the nine `move_*` clusters and `:2092`'s `<unconditional>` is not among them. Add it, marked `is_dynamic_raise`.

---

## C9 — MUST-FIX as filed — **PARTIAL. The contradiction and the totality break are CONCEDED. The challenger's remedy is REJECTED as unsound; here is the one that is not.**

**Conceded.** AC-15.5(iv) ("exactly `n` findings" for `n` guards, `:844-845`) and AC-15.6 ("a tier-(iii) guard emits **no** `Finding`", `:852-853`) are directly contradictory and neither fixture is scoped to exclude the other. Downstream, `derive_contract`'s totality docstring (`derive/__init__.py:499-503`, *"Every operation therefore receives at least one Finding downstream"*) and the join's "zero findings ⇒ `UNKNOWN`" row (`260901…:578`) mean an all-(iii) operation silently becomes `UNKNOWN` with no evidence. And `unknown_ledger.py`'s accumulator clusters *findings* (`:222-236`), so a suppressed guard is uncountable and §15.9(3) is uncomputable for exactly the four `<unconditional>` clusters.

**The challenger's remedy — "emit the tier-(iii) `Finding` as `Verdict.SAFE` with a `detail` marker" — is REJECTED.** A `SAFE` at `:576` asserts the guard does not fire, i.e. that the backend did not raise. Under `join`, an operation all of whose other findings were `SAFE` would join to `SAFE`, claiming an operation cannot fail *including at the backend*. That is A-COMPLETES applied to the current operation — precisely the unsound claim §15.5 Q1 exists to avoid. Adopting it re-creates the C3 hole from the other side.

**The remedy that preserves totality, the ledger, the invariant and the fence, at zero vocabulary cost:**

> A tier-(iii) guard emits **one `Finding`, `Verdict.UNKNOWN`, `reason="guard_env_dependent"`**, and additionally contributes its `site` to `AnalysisReport.scope.excludes_sites`. §15.7 already defines `guard_env_dependent` as covering *"tiers (ii) **and** (iii) together"* (`:625`), so no definition changes and no thirteenth member is needed. One `Finding` per guard holds; AC-15.5(iv) and AC-15.6 stop contradicting; totality holds; the ledger counts it; `excludes_sites` is a published annotation with no effect on `join` and no effect on the fence (C3).

Cost: none. §15.5 already establishes no joined `SAFE` is reachable, so making tier (iii) yield `UNKNOWN` removes nothing the increment could have had.

While adopting this, widen `guard_env_dependent`'s definition by one clause to cover E-UNCOND(4)/(5)'s new give-up point: *"…or the guard's reachability is not established (depth ≥ 1, or a depth-0 empty trail in a `K` containing an earlier `Return`/`Try`/`Raise`)."* That keeps `REASON_VOCABULARY` at 12 of 12 and keeps the reason honest.

---

## C10 — MUST-FIX as filed — **CONCEDED, all four parts.**

Verified against `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md`. The dataclass is defined twice in five lines with two different single fields. `harness_internal` is defined at `:788` as *"analyzer/plumbing bug; always paired with `reason="internal_error"`"* and has nothing to do with a backend re-raise. "Unbounded" is load-bearing and unargued. And neither cited line defines `SoundnessScope` — `:103` is a forward reference into `260901_plr-sema-research-b-f.md`; `:3327-3330` notes only that a definite volume verdict would need one. Grepping `src/` finds no `SoundnessScope`.

**Remediation:** one field, `excludes_sites: tuple[PlrSite, ...]`; delete the `excludes`/`harness_internal` sentence entirely; state plainly that `SoundnessScope` is **new in this increment**; replace the two citations with a single sentence naming Open decision 2 as the *motivation*, not the definition. Under C3 the type carries no fence semantics, which makes this trivially safe.

---

## C11 — MUST-FIX as filed — **PARTIAL. (a) CONCEDED on the fact, REBUTTED on the sizing. (b) CONCEDED with a fail-closed rule. (c) CONCEDED as a user disclosure.**

**(a).** `resource_type_of` (`oracle_common.py:251-274`) is parent-wins verbatim: `target = parent if parent is not None else obj`, then `_generic_plr_type_name(target)`. For a list of `TipSpot`s it returns `{tip_rack: "TipRack"}`. The element's own class is discarded by design. §15.4's "the observation the harness already computes" is **wrong about the half the gate rests on**, and §15.9's "~25-line harness change over data the harness already computes" (`:753`) must be corrected.

**Rebutted on sizing.** `resource_types_from_kwargs`'s `walk` (`:296-304`) already visits every element. Recording `_generic_plr_type_name(obj)` for the object itself alongside the parent's is a second `dict` and ~10 lines; the heterogeneity guard below is ~5 more; threading into `resources_from_example` (`:397-410`) is ~10. **~40 lines, not "a new element-walk" of unknown size.** The claim is wrong; the estimate survives.

**(b) conceded, with the rule.** `Resource` carries one `element_type` per slot (`check/ir.py:178-191`), `ir_value_of` keys a cell-carrying `Ref` by the parent's name, and `out.setdefault(name, cls)` is first-element-wins. A `Deck`-parented set collapses. Normative fix:

> Record, per parent name, the **set** of element generic classes. `element_type` is that class iff the set is a singleton, and **`None`** otherwise (fail-closed). The count of parents with heterogeneous children is published in AC-15.4 beside the coverage numbers.

**(c) conceded, and it is a user-facing disclosure, not a text fix.** O1 is a tier-(ii) observation, the increment defers tier (ii), and the GO rests on the one operation whose tier-(i) clearance is the whole gate. §15.9(5)'s with/without delta measures whether O1 *matters*, not whether the residual is legitimately (i). The honest statement, which §15.9 must carry in its own words: **"this increment's GO is conditional on one tier-(ii) observation, admitted to repair the benchmark's data poverty; in the graph lane the same atoms are tier (i) and the field is read at `plr-sema/src/plr_sema/check/ir.py:695`, but no count of populated graph payloads is offered."**

---

## C12 — MUST-FIX as filed — **REBUTTED. The arithmetic closes, and the mechanism is in the accumulator. There are no 12 unaccounted operations and Q1 cannot be refuted this way.**

Resolved from `plr-sema/eval/unknown_ledger.py:122-236`, read in full.

`ClusterAccumulator.ops_blocked` is a **`set[tuple[str, str]]`** (`:128`) and `per_method` increments only `if is_new_op` (`:135`, `:138-139`). So `n_ops_blocked = len(set)` and `sum(per_method) == n_ops_blocked` **deduplicate across `(row_id, op_id)` collisions**. `row_id` is a content digest (`corpus_p25:<hex>`), so two rows with identical content collide — and the module *already warns about exactly this*, at `:204-210`: `"duplicate (row_id, op_id) … row_id likely collided"`.

By contrast, `n_ops_executed += 1` (`:212`) and `reason_set_histogram[...] += 1` (`:236`) are **unconditional per occurrence** and do not deduplicate.

So:

- **The histogram's 93 is an occurrence count and is correct.**
- **The `unresolved_delegate` cluster's `n_ops_blocked` 81 is a distinct-pair count and is correct for its own denominator.**
- There are exactly **12 duplicated `(row_id, op_id)` occurrences**, and cross-checking pins them: `:375` covers every operation and reports 532 (= 544 − 12); `:409` does *not* cover `move_*` and reports 384 with `n_findings == n_ops_blocked`, i.e. **zero** dedup loss. The 12 duplicates are therefore all in the `move_*` family — consistent to the op with `93 − 81 = 12`.

**The 12 are not unattributed operations. They are duplicate occurrences of `move_*` operations already inside the 81 and already excluded by §15.0.** The challenger's escalation — that they are "precisely §15.14 Q1's stated refutation criterion" — is rejected: there is no operation in the benchmark that carries no `_check_args` guard, and the coupling argument is not exposed here.

**What is genuinely wrong, and B0 must fix it:** two fields in one document use different denominators without saying so, the ledger's own note claims collisions *"affect only method attribution … never cluster membership"* (`:1918`) which is **false** — they affect `n_ops_blocked` and `per_method` — and §15.0's note 2 (`:93-97`) calls 544 *"distinct `(row_id, op_id)` pairs"* when it is an occurrence count and the distinct count is 532.

**B0's fix is two lines, not a hunt.** Make `row_id` unique at the sink call site (`oracle_common.py:609-611`) by appending the row index — `f"{row_id}#{row_idx}"` — and re-run. Every field then closes at 544/93 simultaneously and the histogram is unchanged. Correct the ledger note at `:1918` and §15.0's note 2 either way.

Acceptance check: in `unknown_ledger_260904_after.json`, `sum(per_method) == n_ops_blocked == n_findings` for the `unresolved_delegate` cluster, and `:375`'s `per_method` sums to 544.

---

## C13 — MUST-FIX (user decision) as filed — **PARTIAL. (1) CONCEDED with a one-clause fix that restores reason 1. (2) CONCEDED as genuinely unspecified. The registry disposition is HM-25, not HM-24, and it IS a ceiling spend.**

**(1) conceded, and the fix is one clause.** §15.3's rebinding clause constrains writes to `x` only; nothing constrains α's `iter` or β's `<p>`. Verified that PLR rebinds those routinely (`resources` `:999`/`:1172`, `use_channels` `:501`/`:958`/`:1152`). At this pin α is safe by accident — `_check_containers`'s `resources` is its own parameter, written once (`liquid_handler.py:871-875`) — but the *rule* permits a wrong term. Fix:

> The single-write requirement ranges over **`x` and over the term's own iterand** — α's `iter` name, β's `<p>` name — in the same body `K`, under the same β-preserving-rebinding exception.

With that, reason 1's first leg is restored: α/β can only produce `Opaque`, never a wrong term, from a same-body rebinding.

**(2) conceded outright.** See "the one thing the spec does not say" below — it is real, and no clause restores reason 1 against it this increment.

**Registry disposition — I do not accept HM-24, and I do accept that a row is owed.** The registry's criterion is silent-vs-loud (`_hand_maintained.py:844-846` for HM-24; `:945` *"Fails LOUDLY here (unlike HM-24)"* for HM-25). Two facts decide it:

1. HM-24's harm is a *silent family collapse*: `channel_guards` goes empty, *"the tip-requiring/tip-loading families silently empty"* (`:878-880`). α's failure returns one guard to `guard_predicate_unparsed` — its pre-increment reason — and empties no family. There is no family here.
2. **AC-15.2 publishes an exact floor (`≥ 3` α, `≥ 6` β) that goes red on a PLR rewrite.** That is HM-25's own criterion verbatim (`:946-948`, "exact-count/gate assertions … go red").
3. HM-25's `what` **already carries P3a as `<p> = <p> or self.<x> or list(range(len(<q>)))`** (`:905-906`) — β's three-operand sibling, same idiom family, same row.

So: **HM-25 `declared` 8 → 9**, one entry covering α and β as a single "argument-default and filtered-comprehension binding shapes" pattern, with `breaks_when` naming AC-15.2's floor as the loud test. Not HM-24. Not zero. `live_rows()` stays 24 against `BUDGET_CAP = 24` (`_hand_maintained.py:43`, `:957-961`); no row is added.

**Conceded plainly, because the orchestrator must route it: §15.8's "neither row" position does not survive, and HM-25 8 → 9 is a per-row ceiling spend the user must approve before band B.** AC-15.7 must then assert HM-25 `declared == 9` and HM-24 `declared == 3` — the reverse of what it says today (`:860-861`).

---

## C14 — MUST-FIX as filed — **PARTIAL. (a) is REBUTTED on the artifact — but the rebuttal exposes a blocker the challenger missed (D1). (b) is CONCEDED; his rule is right with one correction.**

**(a) rebutted.** The attack turns on E-CALL step (2) returning the signature default `None`. **Step (2) has no data source.** Grepping `derived_contracts.json` for `"defaults"`, `"param_defaults"` and `"signature"` returns **zero matches**; the survey records `params` (trusted names) and nothing about default values, and `derive/__init__.py` contains no default-extraction anywhere. So for an absent `offsets` kwarg, resolution falls straight through to step (3) — the β binding — which is exactly its intended case. **β is not dead.**

**But that is not a defense of the spec, it is D1** (below): E-CALL step (2) cites a field that does not exist, and three of §15.9's own predicted clearances depend on it.

**(b) conceded.** Nothing in §15.3 or §15.4 models truthiness, and `x = x or <default>` fires on `[]` as well as `None`. Adopt his rule, corrected so that `Lit(None)` routes to β rather than to ⊤ (E-CALL's current last sentence sends `Len` of any `Lit` to ⊤, which would silently kill the common case):

> **E-CALL(β), the truthiness interaction.** For a `Var(name)` that is the target of a β assignment in `K`: (1) if the call-side resolution yields a **statically known-falsy** value — `Lit(null)`, `Lit(false)`, `Lit(0)`, or an empty `Seq` — the term resolves to the **β binding**; (2) if it yields a **statically known-truthy** value — a non-empty `Seq`, or a non-zero non-null `Lit` — it resolves to **that value**; (3) if the parameter is absent from `call.kwargs` **and** has a recorded default that is known-falsy, the term resolves to the **β binding**; (4) otherwise ⊤.

Acceptance check: AC-15.2 gains three fixtures, one per branch, including `offsets=[]` asserted to resolve to the β length (**not** to `Len == 0`, which would be a false `WILL_FAIL` at `:522`).

**On the gate:** `:522` survives. `offsets` is written exactly once in `pick_up_tips` (`:517`; `:493` is a kwarg pass inside `_log_command`, not a write), so C6 does not touch it; under (b) an absent/None `offsets` binds to `Len(tip_spots)`; `use_channels` resolves through `channels_for_call`; all three `Len`s are equal ⇒ the `assert` does not fire ⇒ `SAFE`. **§15.9's `pick_up_tips` row survives C6 + C14 together**, contrary to the challenger's "no predicted GO candidate at all". That claim is rejected.

---

## C15 — SHOULD-FIX — **CONCEDED. Two-line rule, no vocabulary cost.**

The nested-`Opaque` bucket is real and the spec's own worked example creates it: `invalid_channels = [c for c in channels if c not in self.head]` (`liquid_handler.py:405-409`) — α binds the term, the `if` clause parses `Opaque`, every free name resolves. 384 findings (`unknown_ledger_260904_before.json:123-133`). None of §15.7's three definitions covers it, and §15.7's legibility claim (*"the residual `guard_predicate_unparsed` count* is *the grammar's coverage gap"*, `:643-644`) is falsified. Adopt his rule verbatim:

> A predicate containing **any** `Opaque` node is `Opaque` for **reason-assignment** purposes (keeping `guard_predicate_unparsed`), while still being **evaluated** under Kleene — so an `And` with an `F` conjunct still decides.

---

## C16 — SHOULD-FIX — **CONCEDED, textual.**

`cache_key` is `(bc_hash, contracts_sha, surface_identity, ir_version, env)` with `contracts_sha = sha256(contracts_json)` (`check/ir.py:918-953`, computed at `:946`). T30's file list (`:907`) regenerates `plr-sema/data/derived_contracts.json` to add `predicate`. Every key moves, for every caller. §15.8's "every key it produces is byte-identical to today's" (`:704`) is false, and it sits in the same paragraph as "the benchmark's keys move". Replace with his one sentence: *the contract-table regeneration moves `contracts_sha`, so the whole cache is cold after T30 by design; `env` is untouched, which is the property that actually matters.* Add a check that no test pins a literal key.

---

## C17 — SHOULD-FIX — **PARTIAL. The `strictness` half stands (he concedes it). The cost wording is CONCEDED; the disposition does not move.**

Verified verbatim at `liquid_handler.py:353-389`: `sig = inspect.signature(method)` (`:353`), `missing = non_default - backend_kws` (`:373`), `raise TypeError` (`:375`), `if len(vars_keyword) > 0: return set()` (`:377-378`), `extra = backend_kws - set(args.keys())` (`:380`), `if len(extra) > 0 and len(vars_keyword) == 0:` (`:381`), `if strictness == Strictness.STRICT:` (`:382`). §15.6's evidence is exact, and his passing observation is correct and reinforces C1: `:377`'s early return makes `:381`'s second conjunct dead.

**Conceded on wording.** On the frozen benchmark the backend is one named literal class (`example.get("backend", "LiquidHandlerChatterboxBackend")`, `oracle_common.py:362`), not a surface. §15.6 prices the general case and charges the specific one for it.

**Rejected as a disposition change**, and he agrees. Deriving over one benchmark backend produces a fact that cannot enter the shipped contract table (which is keyed on PLR's own surface, not on a harness choice), so it is a benchmark-local hack, not increment 7's derivation. Restate Q2's disposition as: *deferred because the general derivation is a new class surface with its own measured selection, and because the increment already carries more soundness risk than it can absorb* — and drop the implication that the specific case is expensive.

---

## C18 — NOTE — **CONCEDED, both defects. One addition.**

- **AC-15.12 (`:891`)** — `oracle_common.py:593-595` is `run_static_calls` *constructing* `env` from an already-returned flag; the producer is `run_runtime` at `:372` (`bool(result.get("volume_tracking_observed"))`). Verified. The citation names the consumer as the producer.
- **§15.5 (`:515`)** — `260901…:103`/`:3327-3330` do not define `SoundnessScope`. Verified; see C10.
- **Addition.** §15.0's note 2 (`:93-97`) states 544 is "distinct `(row_id, op_id)` pairs". It is an occurrence count (`unknown_ledger.py:212`). Correct it with C12.

I re-derived the challenger's thirteen "clean" citations and confirm them, plus these the spec gets exactly right and he did not credit: `derive/__init__.py:452-478` for `InlinedGuard`'s seven fields, `:499-503` for the totality docstring, `:528` for `free_vars = mentions_params`; `check/__init__.py:291-313`'s `<unconditional>` sentinel and its "9 of the 119 guards" count; `check/ir.py:918-953` for `cache_key`; `tipstate.py:245`/`:254-257`; `oracle_common.py:225-232`/`:235-248`/`:251-274`/`:277-308`/`:397-410`; `_hand_maintained.py:43`, `:841-896` (HM-24 `declared=3`), `:897-953` (HM-25 `declared=8`), `:957-961`; `verdict.py:133-168` (`REASON_VOCABULARY` = exactly 10 members).

---

## Defender-identified gaps the challenger did not raise

### D1 — BLOCKER — E-CALL step (2)'s "recorded default" does not exist, and §15.9's `transfer` row depends on it

E-CALL step (2) (`:407-408`) resolves a `Var` to *"the resolved contract's recorded default for that parameter"*. **No such field exists.** `derived_contracts.json` has zero matches for `"defaults"`, `"param_defaults"` or `"signature"`; the derive package extracts no defaults anywhere.

This is not cosmetic. Read `liquid_handler.py:1333-1343`:

```
1333    if target_vols is not None:
1334      if ratios is not None:
1335        raise TypeError(...)
1336      if source_vol is not None:
1337        raise TypeError(...)
1338    else:
1339      if source_vol is None:
1340        raise TypeError(...)
```

§15.9 predicts these three *"clear on the grammar alone"* (`:743`) and §15.1.3 tiers them (i) *"grammar alone"* (`:191`). They cannot. `target_vols` is absent from `call.kwargs` for every planned `transfer`; without a recorded default, step (1) misses, step (2) has no data, step (3) has no α/β binding ⇒ ⊤ ⇒ the enclosing scope entry is ½ ⇒ E-SCOPE returns nothing ⇒ all three are ½. **`transfer`'s only three predicted-clearing guards do not clear, and C14(b) case (3) has no data source either.**

**Minimum addition, and it is genuinely derived (no registry cost, no hand-typed anything):** T30 records `param_defaults: {param: <IR value JSON>}` per contract entry, read from the PLR function's own `ast.arguments.defaults`/`kw_defaults` restricted to `ast.Constant` values (anything else is omitted, fail-closed). ~30 LOC. With it: an absent `target_vols` is `Lit(null)` ⇒ `"if target_vols is not None"` is `F` ⇒ E-SCOPE ⇒ **`SAFE`** on `:1335` and `:1337`; `:1340`'s `else of:` entry evaluates `T` by way (1) and `source_vol is None` is `F` ⇒ `SAFE`. §15.9's `transfer` row is restored, and β's falsy case becomes decidable. This is high-value, not merely corrective — but it must be written down and budgeted.

### D2 — MUST-MEASURE — the gate's second guard depends on an exact channel set nobody has measured on this benchmark

`:502`'s `len(set(use_channels)) == len(use_channels)` clears only if `channels_for_call` returns an exact tuple. Reading `tipstate.py:262-269`, the path for `pick_up_tips` is `channel_default_param["pick_up_tips"] == "tip_spots"` → `call.kwargs["tip_spots"]` must be an `ir.Seq` → `tuple(range(len(items)))`. That should hold, since `tip_spots` is a trusted param and so is not renamed `?<j>` (`check/ir.py:802-808`). But `tipstate.py:557-559` records that *"the shipped fixture's operations never resolve an exact channel set"*, and no number anywhere covers the tier-1 benchmark. **T30's block (2) must publish the count of executed `pick_up_tips` operations for which `channels_for_call` returns non-`None`, with a floor of `== 223`.** If it is 0 the gate fails on `:502` for a reason unrelated to the grammar, and §15.9 would attribute it to O1.

### D3 — MINOR — the guard's own condition is duplicated into `scope_trail[0]`

Covered as E-UNCOND(6) under C1. `visit_Raise` reads `scope_trail[0]` into `condition` without popping it (`survey_plr_preconditions.py:247-251`), so E-SCOPE and E-VERDICT would both dispose of the same test. The answers agree, so this is not unsound — but AC-15.5(i)'s "exactly one `SAFE` finding" becomes ambiguous about which rule produced it, and an implementer will trip over it once.

---

## Severity table (pre → post)

| id | challenger | disposition | post-defense | fix class |
|---|---|---|---|---|
| C1 | BLOCKER | **PARTIAL** — mechanism conceded (and worse: the shipped precedent implements it); magnitude −54 ops; gate untouched | blocking | 3 normative clauses + 1 fixture |
| C2 | BLOCKER | **CONCEDE** | blocking | one normative line (remedy (ii)) |
| C3 | BLOCKER | **PARTIAL** — "no taxonomy" rebutted; non-injectivity conceded | blocking | delete the narrowing (free) |
| C4 | BLOCKER | **CONCEDE** | blocking | restate E-TYPE + 2 fixtures |
| C5 | BLOCKER | **CONCEDE** | blocking | replace the floor |
| C6 | BLOCKER | **PARTIAL** — floor rebutted (8 β entries); `:1185`/`:1188` conceded | blocking (text) | 1 clause + delete 2 claims |
| C7 | MUST-FIX | **PARTIAL** — (a) conceded, (b) literal conceded, collision rebutted | must-fix | 1 clause + 1 rewording |
| C8 | MUST-FIX | **PARTIAL** — site-list rebutted via `is_dynamic_raise`; his own remedy is a tautology | blocking (the gate metric) | derive (iii); restate the gate over reasons |
| C9 | MUST-FIX | **PARTIAL** — contradiction conceded; his remedy REJECTED as unsound | blocking | (iii) ⇒ `UNKNOWN`/`guard_env_dependent` |
| C10 | MUST-FIX | **CONCEDE** | must-fix | one field, delete 2 sentences |
| C11 | MUST-FIX | **PARTIAL** — fact conceded, sizing rebutted (~40 LOC) | must-fix | element walk + singleton rule + disclosure |
| C12 | MUST-FIX | **REBUT** — arithmetic closes; no 12 mystery ops | minor (reporting) | unique `row_id`, 2 lines |
| C13 | MUST-FIX (user) | **PARTIAL → CONCEDE on the registry** | **user decision** | HM-25 8 → 9 + iterand clause |
| C14 | MUST-FIX | **PARTIAL** — (a) rebutted, exposes D1; (b) conceded | must-fix | truthiness rule + 3 fixtures |
| C15 | SHOULD-FIX | **CONCEDE** | should-fix | two-line rule |
| C16 | SHOULD-FIX | **CONCEDE** | should-fix | one sentence |
| C17 | SHOULD-FIX | **PARTIAL** — wording conceded, disposition unchanged | note | reword Q2's reason |
| C18 | NOTE | **CONCEDE** + 1 addition | note | 3 citation fixes |
| **D1** | — | defender-identified | **blocking** | `param_defaults`, ~30 LOC |
| **D2** | — | defender-identified | must-measure | one published count with a floor |
| **D3** | — | defender-identified | minor | E-UNCOND(6) |

---

## (1) Ordered remediation list

Execute in this order. Items 1–8 are the blocking set and must land in the spec before T30 is dispatched. Item 0 is a user decision that gates the whole band.

0. **Take C13's registry finding and §15.5's target substitution to the user** (see §2 below) before any band-B dispatch. *Check: both answers recorded in the sprint plan's decision log.*
1. **§15.4 E-UNCOND — add clauses (4), (5) and (6)**: no `WILL_FAIL` at `depth >= 1`; a depth-0 empty `scope_trail` is not vacuously unconditional unless `K`'s body has no earlier `Return`/`Try`/`Raise`/`Break`/`Continue`; a `raise_guard`'s own condition entry at `scope_trail[0]` is excluded from both scope tests. State that the shipped `volume_guard_is_unconditional` (`derive/receiver_state.py:2079-2080`) returns `True` on `[]` and that this increment's rule deliberately does not. *Check: an AC-15.6 fixture over `_check_no_lid`'s `:117` asserts `UNKNOWN`/`guard_env_dependent`.*
2. **§15.5 / §15.10 / AC-15.8 — delete the fence narrowing.** The tier-1 unsoundness predicate stays `oracle_common.py:645-647` unmodified; `rows_excused_by_scope` is published as an annotation with no threshold and no gate effect; no `exc_class → site` mapping is constructed. *Check: T32 contains no reference to `exc_class` in the comparison path.*
3. **§15.5 / AC-15.5(iv) / AC-15.6 — a tier-(iii) guard emits one `Finding`, `Verdict.UNKNOWN`, `reason="guard_env_dependent"`, and contributes its site to `excludes_sites`.** Widen `guard_env_dependent`'s §15.7 definition by one clause to cover unestablished reachability. *Check: an operation with `n` guards yields exactly `n` findings, `k` of which are (iii), and `join` is called once.*
4. **§15.1 / §15.5 / §15.9 — derive tier (iii) as `guard.is_dynamic_raise`** (`derive/__init__.py:474-478`), naming the seven `raise <name>` sites at this pin (`:576`, `:726`, `:1067`, `:1271`, `:1510`, `:1590`, `:2092`), and **restate §15.9's GO gate over reasons**: GO iff ≥ 1 executed operation carries zero `guard_predicate_unparsed` and zero `guard_operand_unknown` findings. Publish §15.1's (i)/(ii) tiering as prediction only, with T30 block (3) publishing the reason each cluster actually carries. Add `:2092` to §15.1.4 and retier `:117`. *Check: the gate number is computable from `t30_measured_260904.json` without reading this document.*
5. **§15.4 E-TYPE — restate as `T` iff is-or-subclass-of, `F` iff hierarchy-disjoint AND exact, `½` otherwise, with `_generic_plr_type_name`-derived declarations normatively never exact.** *Check: AC-15.1 fixtures assert `IsInstance("Container", (TipSpot, Trash)) == ½` and `IsInstance("Well", (Container,)) == T`; §15.9's `aspirate` row's `:875` claim is restored.*
6. **§15.4 E-CALL — add `param_defaults` (D1), the truthiness interaction (C14b), and the parameter-rebinding clause (C7a).** T30 derives `param_defaults` from `ast.arguments.defaults`/`kw_defaults` restricted to `ast.Constant`, fail-closed on anything else; step (2) is restated over it. *Check: `:1335`/`:1337`/`:1340` are asserted `SAFE` in AC-15.5, and `offsets=[]` is asserted to resolve to the β length.*
7. **§15.3 — add the β-preserving-rebinding clause and extend the single-write requirement to the iterand.** Publish β's population as measured, expecting eight (`:517`, `:661`, `:963-965`, `:1157-1159`); state that `offsets` at `:962`/`:1156` correctly fails closed. *Check: AC-15.2's β floor is `≥ 6`, met by measurement not assertion, with two new fail-closed fixtures.*
8. **§15.1.3 / §15.9 — delete the `:1185`/`:1188` "cleanest result" claim and the `dispense` row's E-SCOPE clearance.** *Check: no worked example in the document depends on β binding elements.*
9. **AC-15.8 — replace the ≥ 1,000 floor with `n_findings_decided ≥ 223`, published per PLR site**, with `guard_env_dependent`/`guard_operand_unknown` published separately and excluded from "converted". *Check: a parse-everything/resolve-nothing stub scores 0 and fails.*
10. **§15.4 O1 / AC-15.4 — restate the sizing (~40 LOC, a new element walk, not an extension of `resource_types_from_kwargs`), add the heterogeneous-parent singleton rule (`element_type = None` otherwise) with its published count, and state plainly that the GO is conditional on one tier-(ii) observation.** *Check: AC-15.4 publishes the heterogeneous-parent count and the with/without residual delta.*
11. **§15.7 — add C15's nested-`Opaque` rule** (a predicate containing any `Opaque` node is `Opaque` for reason assignment, still Kleene-evaluated). *Check: `:409`'s 384 findings are asserted to keep `guard_predicate_unparsed`.*
12. **§15.8 / AC-15.7 — file α + β on HM-25, `declared` 8 → 9**, with `breaks_when` naming AC-15.2's floor as the loud test and citing HM-25's existing P3a entry (`_hand_maintained.py:905-906`) as the same idiom family. AC-15.7 asserts HM-25 `declared == 9`, HM-24 `declared == 3`, `live_rows() == 24`. *Check: `test_no_surface_exceeds_its_declared_size` and `test_total_declared_within_budget` pass.*
13. **§15.3 / §15.4 — specify the delegate→caller substitution, or forbid it.** See §3 below; the minimum is the normative forbiddance plus T30 publishing the count of depth-≥1 guards whose free vars resolve only by name coincidence. *Check: `_make_sure_channels_exist`'s `channels` is asserted ⊤, and `_check_containers`'s `resources` is asserted ⊤ **unless** the substitution ships.*
14. **§15.10 / T32 — add D2's measurement**: the count of executed `pick_up_tips` ops for which `channels_for_call` returns non-`None`, floor `== 223`. *Check: published in `t30_measured_260904.json` block (2).*
15. **§15.8 — correct the cache paragraph (C16)**: the contract-table regeneration moves `contracts_sha` (`check/ir.py:946`), so the cache is cold after T30 by design; `env` is untouched. *Check: no test pins a literal `cache_key`.*
16. **§15.5 — `SoundnessScope` has one field, `excludes_sites: tuple[PlrSite, ...]`**; delete the `excludes`/`harness_internal` sentence; state the type is new in this increment; drop the two non-definitional citations. *Check: AC-15.6 references only `excludes_sites`.*
17. **B0 — make `row_id` unique at the sink (`oracle_common.py:609-611`) and re-run the ledger**; correct the ledger's note at `:1918` and §15.0's note 2. *Check: `sum(per_method) == n_ops_blocked == 93` for the `unresolved_delegate` cluster; `:375` sums to 544.*
18. **Housekeeping.** Fix the AC-15.12 citation (producer is `oracle_common.py:372`, not `:593-595`); reword §15.6's Q2 cost argument per C17; add `SPEC_INCREMENT_6` to `plr-sema/tests/test_spec_lint.py` and parametrise it (T33); regenerate `.praxia/docs/INDEX.md`. **Then actually run `uv run pytest plr-sema/tests/test_spec_lint.py -q` and record the result** — AC-15.11 is a prediction and no one in this round could execute it.

---

## (2) Items requiring a user decision before band B

1. **Spend HM-25's per-row ceiling, 8 → 9, to file α and β?**
 *Recommend **yes**.* §15.8's "neither row" position rests on reason 1, and C13(1)+(2) break it; the correct row is HM-25 (loud, exact-count-gated, same idiom family as the P3a entry already on it), not HM-24. `live_rows()` stays 24 against `BUDGET_CAP = 24`; no row is added and no cap conversation is opened. Declining means α and β ship unregistered against a criterion they demonstrably meet.

2. **Substitute the sprint's headline — per-finding `SAFE` + a legible residual now, joined `SAFE` in increment 7?**
 *Recommend **yes**.* §15.5's coupling argument survives C12 intact (there are no 12 unaccounted operations to refute it with) and is reinforced by this round: with tier (iii) now emitting `UNKNOWN` (item 3), every operation carrying a re-raise is `UNKNOWN` by construction, which makes the coupling structural rather than incidental.

3. **Adopt γ (§15.13) into this increment?**
 *Recommend **no**.* §15.14 Q3 asks it; without γ, `aspirate`/`dispense` (117 ops) keep a `guard_predicate_unparsed` residual and the gate rests on `pick_up_tips` alone. But γ is a loop-recognition rule in R1's territory, this round has already conceded eight blocking items, and D1 restores `transfer`'s three guards at lower risk. Revisit in increment 7 alongside the `pred`-aware `BRANCH`.

4. **Ship both new reasons (`REASON_VOCABULARY` 10 → 12 of 12), exhausting HM-14's headroom?**
 *Recommend **yes**.* §15.7's mechanical distinguishability test survives, and item 3's widening of `guard_env_dependent` to cover unestablished reachability makes the second member carry strictly more traffic than the spec anticipated. The one-member fallback would collapse the exact distinction that scopes increment 7.

---

## (3) The one thing the spec does not say — adjudicated: **genuinely unspecified. No mechanism exists. Conceded and sized.**

I looked for the mechanism the challenger says is missing, and it is missing.

- **`delegates_to` carries no arguments.** `SurveyRecord.delegates` is a `set[str]` of bare names (`survey_plr_preconditions.py:163`, `:292`), and `_walk_closure` expands it by name alone (`derive/__init__.py:446-449`). Nothing anywhere in the closure records an argument list, a position, or a keyword.
- **The closest shipped thing is P9, and it does not fit.** `_delegate_channel_bindings` (`derive/receiver_state.py:937-965`) **is** a delegate-parameter → caller-argument substitution, but it (i) reads `call.keywords` only (`:907`) — and PLR calls every delegate that matters **positionally**: `self._check_containers(resources)` (`:956`), `_check_no_lid(resource, "aspirate from")` (`:978`), `self._make_sure_channels_exist(use_channels)` (`:980`), `self._assert_resources_exist(tip_spots)` (`:520`); (ii) requires `func.value.id == "self"` (`:954`), so a module-level delegate like `_check_no_lid` is excluded outright; (iii) resolves one parameter to a *value*, not a general name map.
- **The name-coincidence claim is exact.** `_check_containers(self, resources)` (`liquid_handler.py:871`) is called at `:956` with a caller local also named `resources` — so a naive `call.kwargs["resources"]` lookup works **by accident**. `_make_sure_channels_exist(self, channels)` (`:405`) is called at `:980` with `use_channels` — so it fails closed **by accident**. Both accidents flip on a PLR rename, in opposite directions, with no test able to see it.

**Concession, with the minimum that resolves it.** Two options; I recommend (a) for this increment.

**(a) Forbid it, normatively, and measure the exposure.** Add to E-CALL:

> A `Var(name)` in a guard at `depth >= 1` resolves **only** through `channels_for_call` (for the derived channel term) or an α/β binding in the delegate's own body over the delegate's own parameters. It **never** resolves against the entry point's `call.kwargs`, because no argument mapping across a `delegates_to` edge is recorded (`plr-sema/src/plr_sema/derive/__init__.py:446-449`; `SurveyRecord.delegates` is a `set[str]`). Every other depth-≥1 free name is ⊤.

T30 publishes the count of depth-≥1 guards whose free vars would have resolved by name coincidence, so the size of what is being forgone is on the record. This costs the gate nothing — `pick_up_tips`'s three deciding guards are all depth 0 — and it costs `:875` (`_check_containers`), which then does **not** clear, so §15.9's `aspirate` row must say so.

**(b) Build it.** A `delegate_arg_binding` map: for a delegate called **exactly once** in `K` (P9's shipped rule-1 singleton test, `receiver_state.py:957-959`), record `{delegate_param: <caller expression>}` over both positional and keyword arguments, matched against the delegate's own `ast.arguments`, fail-closed on `*args`/`**kwargs`/`Starred`/a delegate called more than once. That is **~90 LOC over a new derived field with its own measured selection and its own registry argument** — not in T30's ~420, and it would land α/β's HM-25 entry alongside a third pattern. If the round wants `:875` and `:117`, this is what it costs; it belongs in increment 7 with the tier-(ii) work.

---

## (4) Revised gate prediction

After the remediations above, and **only** if items 1–8 land:

| method | ops | post-remediation residual | why |
|---|---|---|---|
| **`pick_up_tips`** | 223 | **{`guard_env_dependent`} — GO** | `:498` clears (α + O1 + restated E-TYPE ⇒ `IsInstance` `T` ⇒ `AnyOf` `F` ⇒ `SAFE`); `:502` clears (G4 + `channels_for_call`, **conditional on D2**); `:522` clears (G2 + β + truthiness rule + `channels_for_call`); `:514`/`:375`/`:383`/`:409`/`:321` are `guard_env_dependent`; `:576` is derived (iii) ⇒ `guard_env_dependent` + `excludes_sites`; `:535` is already decided |
| `transfer` | 19 | {`guard_predicate_unparsed`} — NO-GO | `:1335`/`:1337`/`:1340` now clear via D1's `param_defaults`, but `transfer` inherits `aspirate`'s `:990` and `dispense`'s `:1202`, which need γ |
| `aspirate` | 77 | {`guard_predicate_unparsed`} — NO-GO | `:959` clears; `:875` does **not** (item 13, option (a)); `:990` needs γ; `:117` is `guard_env_dependent` under E-UNCOND(4) |
| `dispense` | 40 | {`guard_predicate_unparsed`} — NO-GO | `:1153` clears; `:1185`/`:1188` do **not** (C6); `:1202` needs γ |
| `drop_tips`/`discard_tips` | 65 | {`guard_predicate_unparsed`} — NO-GO | `:666` loop-append, `:657` numeric `Cmp`, unchanged; `:647` is now `½` not a false `WILL_FAIL` (C4) |
| `stamp` | 27 | {`guard_predicate_unparsed`} — NO-GO | `containers` branch-bound; `:1770`/`:1920` are `guard_env_dependent`, not false `WILL_FAIL` |
| `move_*` | 81 distinct / 93 occ. | out of scope | `unresolved_delegate`; `:2092` is derived (iii) |

**On `pick_up_tips` `:522` under C6 + C14 together — explicitly, since the challenger predicts it dies:** it survives. `offsets` is written **exactly once** in `pick_up_tips` (the β assignment at `:517`; `:493` is a kwarg pass inside `_log_command`, not a write), so C6's eight-second-writes finding does not reach it. C14(a)'s "β is unreachable" rests on E-CALL step (2) returning a signature default; **step (2) has no data source today**, and after D1 it returns `Lit(None)` — statically known-falsy — which the C14(b) truthiness rule routes to the β binding. Both paths end at `Len(offsets) = Len(tip_spots)`. **The challenger's "the gate has no predicted GO candidate at all" is rejected.**

**The gate remains a single point of failure and now has three, not one.** O1's element walk must yield `"TipSpot"` (C11, C4); `channels_for_call` must return exact channels on 223 real rows (D2); and `tip_spots` must lower as an `ir.Seq`. All three are measurable in T30 before T31 constructs a single verdict, which is exactly what §15.9's ordering gate exists for. If any fails, the increment is NO-GO on every operation and the decision goes to the user, as §15.9 already provides.

---

## (5) Verdict

**`needs_revision`.** Confidence: high.

**Implementable as written: no.** The grammar (§15.2 G0–G6), the tipstate/volume dispatch rule, §15.6's `strictness` evidence and §15.0's ledger reading are sound and should survive revision intact — as should §15.5's coupling finding, which this round strengthens rather than weakens. But the evaluator emits false `WILL_FAIL`s on ~244 clean operations by a mechanism the repo's own shipped precedent implements; the type atom the gate rests on is unsound in one direction and inert in the other; the fence is narrowed by an artifact that does not exist; the headline measurement passes with nothing decided; and E-CALL's step (2) cites a contract field that was never derived.

Against that, three of the challenger's six blockers are less than they appear, and one of his must-fixes is wrong in a way that would have made the gate self-satisfying if adopted. C12 does not open a hole in Q1 — the 93/81 gap is `(row_id, op_id)` set dedup under content-digest collisions, exactly as `unknown_ledger.py:204-210` already warns, and the 12 are duplicate `move_*` occurrences already inside the 81. C3, C9 and C10 collapse into one change that costs the increment nothing, because §15.5 already proves there is no joined `SAFE` for a narrowed fence to protect. And `pick_up_tips`'s `:522` survives C6 and C14 together, so the gate keeps a predicted GO candidate.

Every remediation above is a bounded text change against facts now fully in hand: the seven `raise <name>` sites are enumerated, the eight β second-writes are read and classified by length-preservation, the survey's six visitors are exhaustively listed, the cluster accumulator's set semantics are traced, the exception taxonomy is opened and found to cover the wrong 132 classes, and the absence of `param_defaults` is confirmed by grep over both the artifact and the derive package. **`needs_recon` is not warranted.**

**`reviewed-round-1` requires:** items 1–8 landed in the spec text; the user's answers to decisions 1 and 2 recorded; item 17's ledger re-run producing a `_before` file whose arithmetic closes; and AC-15.11's lint actually executed rather than predicted. Eighteen ordered items, of which eight block T30's dispatch and one blocks the band.
