---
title: 'plr-sema increment 7 (the observation record, spec_version 1) -- adversarial round 1, challenger'
description: 'Challenger pass (praxia:spec-challenger, Opus) on the increment 7 draft: C1-C26 -- 5 blockers (C1 the :375/:383 SAFE-direction discharge is computable from the derived signature table so D5 is a false binary and the NO-GO is not established; C2 the gate is predicted NO-GO by construction; C3 R-DECK matches a shape absent from the contract table and `resource` is a for-target nothing binds; C4 the gated floor 2,170 assumes the uncertain 384 reach; C5 extract_tb[-1] is the innermost frame so F2 excuses nothing on a :576 re-raise), 14 must-fix (Q-MONO overturns a shipped G8(1) statement; Q-BIND soundness needs an evaluator invariant; G3-constructed quantifiers need target inheritance; caller_args origin unspecified; caller-side lineno; byte-identical claim over-scoped; cache-key encoding not injective; verify() third return site; topology extraction; decorated constant_return; selection rule undefined; capture placement; A-DECK-OBJECT fence claim is not evidence; in-loop guards for the depth-1 lift), 6 should-fix, 1 note. Verdict needs_revision (revise-and-advance). Objections changing the gate: C1 C2 C3 C4 C5 C21; changing user decisions: D5 (C1 C2 C22), D2 (C3 C14 C18), D1 (C19 C10 C11 C26), D3 (C15 C16), D4 (C25).'
status: final
task_id: 260909_sema-observation
date: '260909'
sprint: '130'
backlog_ids: '5022'
---
> Persisted verbatim by the orchestrator from the challenger agent's final report (no write tool).
> Target: `.praxia/docs/specs/260909_plr-sema-observation-increment.md` at commit `7893168a`
> (spec_version 1, status draft).

# Increment 7 round-1 challenger report

The document is unusually honest about the thing it cannot do and unusually loose about three things it claims it can. Its central finding — the headline is unreachable — rests on a sizing box (§16.1.1) that prices a *general* model of `_check_args` while the gate only needs the *one-sided SAFE* direction, and that one-sided direction is computable from two columns §16.3 already derives (`params`, `has_var_keyword`) plus the caller-argument map §16.4 already ships: for the benchmark backend `non_default = params − default = ∅` and `has_var_keyword` is true, which decides `:375` by value and `:383` by scope. So D5 as put to the user is a false binary and the NO-GO prediction is not established. Two of the three sites the document claims it *does* flip are shakier than stated: `:321`'s R-DECK matches a shape that does not exist in the IR at all (the `resource_from_deck` assignment is neither α nor β, and `resource` is a `for`-target nothing binds), and `:409`'s 384-op reach is hedged in §16.10.3 but hard-coded into AC-16.9's gated floor. The fence, built precisely for the moment the headline arrives, keys on `extract_tb(...)[-1]`, which for a re-raise is the *original* backend frame and never `:576` — so it would excuse nothing, and the predicted NO-GO hides that. Q-MONO is sound but silently overturns a shipped normative statement and a shipped code invariant. Verdict: `needs_revision`.

---

**C1 — blocker — §16.1.1 (lines 150-203), §16.15 D5 (line 1525), §16.10.2.**
The refusal of `:375`/`:383` prices a *general* model of `_check_args` (a `set(x.keys())` term, a set-difference `BinOp`, `E-SIG` over three comprehension shapes, a residual `**kwargs` key set) when the gate needs only the direction that yields `SAFE`. `missing = non_default − backend_kws` where `non_default = params(class,method) − default`, and `params` is *exactly* §16.3's already-derived key ("parameter names after `self`, excluding `*args`/`**kwargs`, that have no default", line 436). If `params ⊆ default` then `non_default = ∅`, so `missing = ∅` **whatever `backend_kws` is** — no set-difference term, no key-set representation, no signature reflection. At the pin: chatterbox `pick_up_tips(self, ops, use_channels, **backend_kwargs)` gives `params = {ops, use_channels}` and the call site passes `default={"ops","use_channels"}`. `:383` falls the same way: `has_var_keyword` is true, so `len(vars_keyword) == 0` is `F`, the enclosing `if` at `:381` is `F`, and E-SCOPE returns `SAFE` without touching `strictness` — route (a) of the document's own text, whose only missing fact it misidentifies as "the third of the five comprehensions" when the fact needed is the boolean §16.3 derives.
Evidence: `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:369-383`, `:541-546`; `external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:63`; draft `:436-439` (`params`, `has_var_keyword`); draft `:172-180`.
Remedy — this is a **user decision** and must be repriced as three options, not two. **D5a** = the general model, ~350 LOC, increment 8 (as written). **D5b** = two site-level rules over `_check_args`'s two guards, reading `params`/`has_var_keyword` from §16.3 and `method`/`default` from §16.4's `caller_args`, plus one `ast.Set`-of-`ast.Constant` Term production: ~100-130 LOC, one or two further HM-25 units (it is a PLR-idiom recognition in exactly α/β/P3a/P9's class — `plr-sema/src/plr_sema/_hand_maintained.py:934,974`), landing the headline this increment. **D5c** = NO. §16.1.1 must state the honest cost of D5b (it hand-types a named PLR function and its local names, so it is genuinely more benchmark-shaped surface than §16.5, and it goes stale silently on a PLR upgrade unless `_measure_hm25` imports its symbol) and reject or accept it on that ground — not on the ground that five productions are required, which is false for the SAFE direction.

**C2 — blocker — §16.10.2 (lines 1050-1064), §16.10.4 (line 1153).**
The gate ("GO iff ≥1 op reaches `scope_verdict == SAFE`") is predicted NO-GO by construction, and the document names its own cheapest falsification as "`scope_verdict == SAFE` on ≥1 op without D5". Under C1 that falsification is reachable inside this increment's budget, which means the gate is not a gate: it is a coin already called. A gate that the spec predicts fails, on a branch the spec did not examine, cannot decide GO for anything.
Evidence: draft `:1050-1057`, `:1153-1155`; C1's evidence.
Remedy: either take D5b (gate stands as written and is winnable) or, if the user declines, restate the gate as a conjunction the increment can actually fail — e.g. "GO iff `n_findings_decided ≥ <floor>` **and** `unsound == unsound_scoped == 0` **and** `scope_verdict` is computed and published per operation, with the `:375`/`:383` obstruction reproduced by measurement" — and move the `scope_verdict == SAFE` criterion to increment 8's gate where it can be met.

**C3 — blocker — §16.5.6 (lines 771-796), §16.1.3, §16.10.3 (line 1081), D2.**
R-DECK is specified to match `Cmp(EnvRef(("self","deck","get_resource"),(t,)), "==", u)`. That shape does not exist in the contract table. `resource_from_deck = self.deck.get_resource(resource.name)` is a plain `ast.Assign` of a call — neither α (a `ListComp` with a bare-`Name` iter) nor β (a length) — and `bindings.substitute` replaces **only** α-bound `Var`s, leaving `Var("resource_from_deck")` untouched. The ledger's own condition string confirms it: `not resource_from_deck == resource`, which parses to `Not(Cmp(Var, "==", Var))` with no `EnvRef` anywhere. Second, independent failure: `resource` is a `for`-loop target (`for resource in resources:`), and nothing in this increment binds `for` targets — Q-BIND covers comprehension targets on `AllOf`/`AnyOf`/`Filtered` only — so R-DECK's "`u` resolves to a `Ref` with a slot" cannot hold either.
Evidence: `plr-sema/src/plr_sema/derive/bindings.py:215-237` (α-only substitution), `:232-237`; `outputs/plr-sema/unknown_ledger_260909_after.json:179-181`; `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:315-321`.
Remedy: withdraw the `:321 → SAFE on 288` prediction, or make D2 explicitly conditional on **two further mechanisms the document currently refuses**: a third binding idiom for `x = <EnvRef-call>` plain assignments, and element-wise binding over a `for` target. Both are new productions with their own soundness arguments and their own registry consequence; priced honestly D2 is not ~110 LOC. Until then §16.10.3's D2 row, the `≥2,458` floor and the `n_clusters → 50` cell are all unsupported.

**C4 — blocker — AC-16.9 (lines 1281-1289) vs §16.10.3 (lines 1099-1108).**
The gated floor `n_findings_decided ≥ 2,170` is derived as `1,563 + 384 + 223`, i.e. it assumes `:409` clears on **all 384** operations — the exact number the qualification paragraph three lines above declines to claim ("223 certain and up to 384", "which no number anywhere covers"). If `:409` clears only `pick_up_tips`, the true value is 2,009 and the increment fails its own gated criterion while every prediction in it held. `guard_env_dependent ≈ 3,531` and `n_clusters 53 → 51` carry the identical hidden assumption (a partially-cleared site does not remove a cluster).
Evidence: draft `:1284-1286`, `:1099-1108`, `:1112-1116`.
Remedy: set the gated floor at `≥ 2,009` with `2,170` published as the target, and split the two aggregate cells into "223-certain" and "up-to-384" variants. Do not gate on the uncertain half.

**C5 — blocker — §16.7 F1/F2 (lines 883-916), AC-16.8.**
`traceback.extract_tb(e.__traceback__)[-1]` is the **innermost** frame — the site where the exception was originally raised. The one site F2 exists to excuse is `liquid_handler.py:576`, `raise error`, a re-raise of an object that already carries the backend's traceback; propagating out of `pick_up_tips` prepends the `:576` frame, so `[-1]` remains the backend's original raising line and never matches `excludes_sites`. F2 therefore excuses **nothing**, `rows_excused_by_frame` is structurally 0, and every future `scope_verdict == safe`-on-backend-raise row is counted `unsound_scoped`. The defect is invisible this increment precisely because §16.10.3 predicts `scope_verdict == SAFE` on zero operations — the fence ships untested against the only case it was built for.
Evidence: `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:551-576`; `training/verify/verifier.py:133-136`; draft `:893-895`, `:899-906`.
Remedy: capture the **whole** frame list (`error_frames: list[{file,lineno,qualname}]`, still ~3 lines) and make F2 excuse iff **any** frame matches an `excludes_sites` `PlrSite`, with a normative sentence saying which frame decides when several match (the outermost PLR-layer match — the re-raise — is the right one). AC-16.8 must add a fixture whose exception is raised inside the backend and re-raised at `:576`, asserting the row *is* excused; the current fixture (raise inside `_make_sure_channels_exist`) exercises only the direct case, which is the one that already works.

**C6 — must-fix — §16.5.5 Q-MONO (lines 751-769).**
Q-MONO decides `AllOf(⊤, T) = T`. Increment 6 states, normatively and in shipped code, that `AllOf`/`AnyOf` over a ⊤ seq is ½ **"never vacuously `T`"** — a flat statement, not a body-conditioned one. The draft claims Q-MONO "is increment 6 A-C3's own clause preserved in both directions"; that is a re-reading, not a preservation. The rule itself is sound (T-for-every-element and vacuous truth agree), but a shipped `implemented-round-2` normative box and a code comment asserting the opposite are being overturned with no amendment and no task row that edits increment 6.
Evidence: `.praxia/docs/specs/260904_plr-sema-predicate-increment.md:630-634` (G8(1)); `plr-sema/src/plr_sema/check/predicate.py:576-578`, `:600`.
Remedy: state it as an explicit amendment of increment 6 §15.2 G8(1) and §15.4 A-C3 ("the ½ applies when the body is not definite"), and add the increment-6 spec file to a task row's file list — the precedent exists (T48 edits increment 1's assumption table).

**C7 — must-fix — §16.5.5 Q-BIND soundness paragraph (lines 745-749).**
"Q-BIND only ever replaces a ½ with a definite value" is false as written. Today's evaluator already returns a *definite* value for the concrete-seq case: it computes `n`, and for `n ≥ 1` returns the body evaluated once with all targets at ⊤ (`return evaluate_predicate(node.predicate, _with_all_to_top(ctx))`). Q-BIND replaces that whole computation. It is safe only under a global monotonicity property — "no production returns a definite value from a ⊤ operand unless argument-independent" — which the draft asserts in one clause and never states as an invariant, never gates, and which R-CONST is the first production to stress (it returns `T` from ⊤ arguments by design).
Evidence: `plr-sema/src/plr_sema/check/predicate.py:597-606`; draft `:745-749`, `:667-674`.
Remedy: restate the soundness argument as a normative **evaluator invariant** ("a production may return a definite value with a ⊤ operand only when its value is independent of that operand"), name R-CONST as its one deliberate instance, and add an AC fixture asserting Q-BIND and the ⊤-once path agree wherever both are definite.

**C8 — must-fix — §16.5.5 Q-BIND (lines 740-743), AC-16.6.**
`target` is specified as written by `parse` "for a bare-`ast.Name` comprehension target". But `:409`'s quantifier is not parsed from a comprehension at all — G3 *constructs* `AnyOf(seq, pred)` out of a `Filtered` term's own `seq` at rewrite time. An implementer who adds `target` to `Filtered` and leaves the G3-constructed `AnyOf.target` at `None` gets today's behaviour at the exact site Q-BIND exists for, while every AC-16.6 fixture (which builds `AnyOf` directly) passes.
Evidence: `.praxia/docs/specs/260904_plr-sema-predicate-increment.md:474-477` (G3 builds `AllOf`/`AnyOf` from a `Filtered`'s seq); draft `:740-743`, `:1258-1260`.
Remedy: one normative sentence — "a G3-constructed `AnyOf`/`AllOf` inherits the source `Filtered`'s `target`" — plus an AC-16.6 fixture that goes through the `len(Filtered) == 0` idiom end to end, not through a hand-built node.

**C9 — must-fix — §16.4 M2 (lines 553-565), §16.8 (lines 941-956), §16.10.3.**
M2 says how a mapped name *resolves* but not what `origin` it carries. `_resolve_var` returns `(value, origin)` and `origin == "operand" and value is Top` is precisely clause 2 of §15.7's reason procedure (`guard_operand_unknown`); an unbound name returns `("env")`. So whether a depth-1 name that resolves through `caller_args` to ⊤ produces `guard_operand_unknown` or `guard_env_dependent` is unspecified — and that choice moves §16.10.3's `guard_env_dependent 4,138 → ≈3,531` prediction, §16.8's fold-in table row 3, and the gate's two published zero-conditions.
Evidence: `plr-sema/src/plr_sema/check/predicate.py:240-255`, `:666-676`; draft `:947`, `:1115`.
Remedy: a normative clause in M2 — a `caller_args`-resolved name carries origin `"operand"` (it is an operand of *this* call, one frame up) or `"env"`, chosen explicitly — plus the matching predicted reason counts in §16.10.3.

**C10 — must-fix — §16.4 M2 step (1) (lines 553-559).**
"Evaluate that `Term` in the caller `K`'s own context" is silent on which **lineno** the caller-side α/β position and scope tests use. The existing machinery is guard-lineno-relative (`first_stmt.lineno < guard_lineno`, plus the ancestor-prefix and `for`-shadow tests), and the guard's lineno lives in `D`, a different function. At this pin every delegate is defined *above* its caller (`_make_sure_channels_exist` at 405, `pick_up_tips` at 488), so `use_channels = use_channels or ...` at `:501` fails `501 < 409` and every K-side binding is silently dropped — the prediction fails. For any delegate defined *below* its caller the same comparison admits a rebinding written *after* the call — an unsoundness.
Evidence: `plr-sema/src/plr_sema/derive/bindings.py:723-734`; `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:405-409`, `:501`, `:521`.
Remedy: normative — caller-side resolution uses the **call statement's** lineno in `K` for every position/scope test, never the guard's; an AC-16.3 fixture with the delegate defined below the caller pins the direction.

**C11 — must-fix — §16.2.3 (lines 420-425), AC-16.1 (lines 1210-1214).**
"With `env` empty, findings are byte-identical to the pre-increment-7 run, by construction" is true of §16.5's rules alone and false of the increment. After T42 the map resolves depth-1 names with **no observation at all**, and D1's lift can emit `WILL_FAIL` on a population that previously could not, again with `env` empty. AC-16.1 is gated on T40, where the claim is true; re-run after T43 it is false, and an implementer reading it as a standing invariant will chase a phantom regression.
Evidence: draft `:420-425`, `:574-594`, `:1210-1214`.
Remedy: scope the claim — "with no `obs:` member, every §16.5 rule declines and no `EnvRef` resolves" — and scope AC-16.1's identity assertion to the T40 state explicitly.

**C12 — must-fix — §16.2.3 canonical encoding (lines 407-411).**
The encoding `obs:<key>=<value>` with lists joined by `,` is not injective. `deck_resource_names` members are user-chosen PLR resource names that may contain `,` or `=`; two distinct observations then produce the same `env` set, and `cache_key` returns a verdict computed under a *different* observation — a correctness event, not a hygiene one. Separately, "sorted members" is ambiguous for ints: string-sorting a 16-channel head gives `0,1,10,11,...,2`, numeric sorting gives another string, and two implementations disagree on the key for the same observation.
Evidence: draft `:407-411`; `plr-sema/src/plr_sema/check/ir.py:918-953` (the key's own claimed properties).
Remedy: JSON-encode the value (`obs:head_channels=[0,1,...]`) or percent-escape `,` and `=`; state the sort as *by value for ints, lexicographic for strings*; add an AC fixture over a name containing `,` and `=`.

**C13 — must-fix — §16.2.1 (lines 326-346), AC-16.1, T40.**
`verify()` has **three** return sites, not two: the success return, and an early return on a deck-build failure where `setup is None` and every observation field is unobtainable. AC-16.1 as written ("returns `plr_observation` with exactly the four fields") is unsatisfiable there. The volume precedent handles this explicitly by returning its default on that path.
Evidence: `training/verify/verifier.py:143-162` (early return), `:161` (`volume_tracking_observed` default).
Remedy: normative — `plr_observation` is `None` on the deck-build path and whenever any field's read raises; a partial record is refused wholesale (which §16.5.1 already requires downstream, so the two statements must agree).

**C14 — must-fix — §16.2.1 (line 338), §16.5.6.**
`deck_resource_names` is specified as "the `topology` key of `before = setup.snapshot()`". `topology` is `self.deck.serialize()` — a nested serialization, not a name list — and the set `get_resource` actually matches is the deck's own name plus every descendant, reached recursively. The extraction is the load-bearing half of D2's observation and is not specified.
Evidence: `training/verify/deck.py:146-159`; `external/pylabrobot/pylabrobot/resources/resource.py:566-588`.
Remedy: specify the recursive extraction (deck name + all descendants, by the same recursion `get_resource` uses), or read `deck.get_all_children()` names directly inside the window.

**C15 — must-fix — §16.3 `constant_return` (lines 439-445), §16.5.3.**
The surface is derived from **AST**; the value R-CONST claims is produced at **runtime**. Nothing excludes a decorated function, so a `@some_wrapper`-decorated `can_pick_up_tip` whose body is `return True` yields `constant_return = True` while the runtime call returns whatever the decorator returns — a false `SAFE` in the `:514` position, the unsound direction. The same gap sits under C1's D5b rule (`inspect.signature` of a bound method vs the AST signature) and under §16.3's `params`/`has_var_keyword`.
Evidence: draft `:439-445`, `:663-674`; `external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:241-242` (undecorated at the pin, which is luck, not a rule).
Remedy: normative — a `(class, method)` row is **absent** when the definition carries a non-empty `decorator_list`, is a `property`, or is redefined at more than one lineno for the same qualname; add the negative fixture to AC-16.2.

**C16 — must-fix — §16.3 selection rule (lines 447-456), D3.**
The selection is "emitted iff `method` occurs as the last segment of some admitted `EnvRef` path in the regenerated contract table, **or as a key of some class's own parameter set reachable from one**". The second clause is undefined — "parameter set", "reachable", and the reachability relation are all unspecified, and no AC tests it. D3 asks the round to find a hand-typed fact; the more consequential finding is that the *derivation itself* is not specified precisely enough for two implementers to produce the same table, which makes AC-16.2's "complete measured selection" unfalsifiable. Separately on D3's own question: §16.2's record hand-types four literal PLR paths (`backend.num_channels`, `machine.head`, `snapshot()["topology"]`, `type(backend).__name__`) on the harness side and books nothing, while §16.5 books a ceiling unit for reading the same table from the evaluator side.
Evidence: draft `:452-456`, `:326-346`, `:974-981`.
Remedy: define the selection as a single closed rule with its own published count, and add one sentence saying whether harness-side literal PLR paths are inside the registry's scope — if they are not, say why the split does not hide surface.

**C17 — must-fix — §16.2.1 placement (lines 336, 341-346).**
`num_channels` and `backend_class` are specified "after `build_setup` and before `_execute`" while `head_channels` is "after `await setup.machine.setup()`". The first window straddles `machine.setup()`, and any read placed there sits **outside** the inner `try` that converts an operation failure into `error` — so a backend whose `num_channels` raises before setup turns a normal row into a harness-level failure, and AC-16.9 asserts `rows_setup_error == 0`.
Evidence: `training/verify/verifier.py:116-144` (inner handler at `:133-136`, outer at `:143`).
Remedy: one capture point, after `await setup.machine.setup()` and before `_execute`, inside a fail-closed guard that sets `plr_observation = None` rather than propagating.

**C18 — must-fix — §16.11 (lines 1189-1199) vs §16.1.3 (lines 256-277), D2.**
The document argues D2 is safe because "the tier-1 fence checks it on 288 real operations", and in the same document proves the counterexample is **unconstructible** by the mutator (you would need a second `Resource` with a matching name and mismatched geometry). Both cannot be evidence: if no instrument in the harness can build a program where A-DECK-OBJECT is false, then 288 passing operations are 288 operations on which it was never at risk. The fence is a check that the corpus never violates the assumption, not a check of the assumption.
Evidence: draft `:268-270`, `:1189-1199`, `:1522`.
Remedy: replace "fence-checked on 288 operations" with the honest statement — "no available instrument can falsify A-DECK-OBJECT; its exposure is bounded by argument, not by measurement" — and add one hand-built fixture (not a kwarg mutator) constructing the duplicate-name resource, so the assumption has at least one adversarial witness. This changes D2's recommendation basis materially and the user should be told so.

**C19 — must-fix — §16.4 D1 (lines 574-594), §16.15 Q6 R1-C4 (lines 1485-1487).**
Neither `compute_reachability_clear` nor D1's three preconditions test whether the guard sits inside a **loop whose iterable may be empty**. The function's three clauses are Return-before, enclosing-`Try`/`With`, and Break/Continue-before; a `for` header is not among them, and R1-C4's enumeration of "control is not diverted anywhere else" omits "the loop body never runs". This is not hypothetical at the pin: `:321` is inside `for resource in resources:` and `:534` inside `for channel, op in zip(...)`. At this pin I cannot construct a *firing* false `WILL_FAIL` — the only newly decidable depth-1 site is `:409`, which is not in a loop, and R-DECK never evaluates `T`-then-`WILL_FAIL` — but the rule as written is one decidable in-loop guard away from one, and D1 is exactly the clause that removes the previous blanket protection.
Evidence: `plr-sema/src/plr_sema/derive/bindings.py:812-829`; `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:315-321`, `:533-535`; draft `:1485-1487`.
Remedy: add a fourth clause to the lift's precondition 1 (and record it as a refinement owed to `compute_reachability_clear`): a guard lexically inside a `for`/`while` within `K` or `D` may not emit `WILL_FAIL` unless the iterable resolves to a non-empty concrete `Seq`. Add it to AC-16.4's perturbation set as a sixth fixture. State explicitly whether `scope_trail` records loop headers — the answer decides whether E-UNCOND ways (1)-(3) already cover this, and the document assumes it without saying.

**C20 — should-fix — §16.7 F2 (lines 899-906).**
Frame-to-site matching is specified as `(error_frame.file, error_frame.lineno)` against a `PlrSite`. Two unstated identities carry it: that `PlrSite`'s lineno is the *first line of the raise statement* (which is what `tb_lineno` reports), and that the frame's file path, "made relative to the repo root", equals the submodule-relative path the sites use — false whenever PLR resolves to an installed copy rather than `external/pylabrobot/`.
Evidence: `outputs/plr-sema/unknown_ledger_260909_after.json:179` (site string form); draft `:893-895`.
Remedy: normalise both sides through one helper, state the two identities normatively, and make AC-16.8 assert a match against a real `PlrSite` string rather than against a hand-written tuple.

**C21 — should-fix — §16.10.4 (lines 1128-1135).**
The falsification map's R-CONST/Q-MONO row is backed by `n_resolved_by_rule[R-CONST]`. That counter measures R-CONST, not Q-MONO: Q-MONO is a general clause over every `AllOf`/`AnyOf` with a ⊤ seq and a definite body, and nothing published bounds its reach. The one rule the document calls the "load-bearing novelty" is the one rule with no counter of its own.
Evidence: draft `:1132`, `:1026-1046`.
Remedy: add `n_quantifier_decided_by_qmono` and `n_quantifier_decided_by_qbind`, per site and whole-table, to §16.10.1's block (1), with predictions (223 and 384 respectively) and AC-16.11 coverage.

**C22 — should-fix — §16.1.1 (lines 150-203) vs increment 6 §15.6.**
Increment 6 states the condition for moving `:375`/`:383` in one sentence: *"the increment must AST-derive the backend class's method signatures."* Increment 7 ships exactly that (§16.3) and then declares the sites undecidable on a different ground, without ever noting that the previously stated condition has been met. A reader of both documents cannot tell whether the earlier claim was wrong or the later one is.
Evidence: `.praxia/docs/specs/260904_plr-sema-predicate-increment.md:1478-1480`, `:1495-1498`; draft `:150-203`.
Remedy: one paragraph in §16.1.1 reconciling the two — and per C1 the reconciliation is that §15.6 was right.

**C23 — should-fix — §16.11 p2a (lines 1173-1187), AC-16.10.**
p2a's floor is "≥1 achieved with 0 unsound". Increment 6's p1 publishes achieved/total (288/288, 16/16, 0/288), and the document itself invokes that precedent for why a class that can only report 0 is a publication and not a gate. A floor of 1 with no denominator is the same defect one step up: 1/300 satisfies it.
Evidence: `outputs/plr-sema/predicate_mutants_260909_inc6.json:2-58` cited at draft `:1175-1176`; draft `:1181`, `:1294-1295`.
Remedy: publish `achieved/attempted` for p2a and set the floor as a ratio or as an absolute with the attempted count named.

**C24 — should-fix — §16.5.6 (lines 792-796), §16.5.1, §16.11.**
The lane asymmetry is disclosed for R-DECK only. R-HEAD and R-CONST are equally observation-dependent, so the graph lane (which has no harness) will produce `UNKNOWN` where the tier-1 lane produces `SAFE` for the same program — and §16.11 names Q-MONO as the only rule that could move tier 2b, when R-HEAD/R-CONST move it too if T40 threads the observation into `region_oracle` (which T40's file list says it does).
Evidence: draft `:792-796`, `:1170-1171`, `:1342` (T40 modifies `region_oracle.py`).
Remedy: one normative disclosure covering all four rules and both lanes, and correct §16.11's attribution sentence to name R-HEAD, R-CONST and Q-MONO.

**C25 — should-fix — §16.5.2 R-ATTR (lines 645-659), D4.**
R-ATTR is shipped deciding nothing, predicted `n_resolved_by_rule == 0`, and its stated purpose — cross-checking that `head_channels` and `num_channels` agree — is a *harness* assertion, not an evaluator rule. It nonetheless enlarges the hand-maintained path table D4 is being asked to pay a ceiling unit for.
Evidence: draft `:653-659`, `:974-981`.
Remedy: drop R-ATTR and replace it with an AC-16.1 assertion `len(head_channels) == num_channels` inside the harness; D4's ask then covers three shapes with one non-zero counter each, which is a stronger case for the same unit.

**C26 — note — §16.14 (lines 1383-1390), §16.13 T42.**
Two of the four items increment 6 §15.13 sent here are refused by assertion rather than argument: the `pred`-aware `BRANCH` gets "the same evaluator serves it; unchanged", and the tuple display gets "Open decision 2's resolution stands". γ and the lid disposition are argued properly; these two are listed. Separately, T42's stated dependency on T41 is unexplained — the argument map reads no backend surface — and bundling D1's lift into a row whose gate also carries the unconditional AC-16.3 means a mid-row decline changes the row's shape rather than removing a row.
Evidence: draft `:1383-1390`, `:1344`.
Remedy: one sentence of argument apiece, and either split D1's lift into its own row or state in T42 exactly which files and which LOC are withdrawn on a decline.

---

## Verdict

`needs_revision` — three blockers (C1, C3, C5) and one gated-criterion contradiction (C4) are all fixable inside this increment's scope, but each changes what the document asks the user to decide, so the spec cannot advance as written.

**Objections that change the gate prediction:** C1 (a sound `:375`/`:383` discharge inside budget makes GO reachable), C2 (the gate as stated is uninformative either way), C3 (removes `:321` from the flip list and the `≥2,458` floor), C4 (the gated floor is unachievable on the document's own hedge), C5 (`unsound_scoped == 0` is currently satisfied only by the absence of any `SAFE`), C21 (Q-MONO's reach is unmeasured, so a divergence would be unattributable).

**Objections that change a user decision:** **D5** — C1 (three priced options, not two), C2, C22. **D2** — C3 (the rule cannot fire without two further refused productions), C14, C18 (the "fence-checked on 288 ops" argument is not evidence). **D1** — C19 (a missing fourth precondition), C10, C11, C26. **D3** — C15, C16 (the derivation is underspecified, and the harness-side literal PLR paths are booked nowhere). **D4** — C25 (drop R-ATTR and the same unit buys three rules that each do something).
