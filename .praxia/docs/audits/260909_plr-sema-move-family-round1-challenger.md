---
title: 'plr-sema increment 8 (the move_* family, spec_version 1) -- adversarial round 1, challenger'
description: 'Challenger pass (praxia:spec-challenger, Opus) on the increment 8 draft: C1-C21 -- 12 blockers (C1 :383 cannot reach move_lid/move_plate because the entry point''s **backend_kwargs passes through a ** unpacking M1 clause 4 refuses and M3 does not touch; C2 M3''s K at depth>=2 is undefined and _walk_closure carries no parentage and dedups multi-parent nodes, which also breaks the conjunctive fold''s own soundness argument; C3 _walk_closure''s LIFO depth means _check_args is inlined at depth 2/3 for the move family, so the fence attribution in 17.1.4 is wrong and the 173-certain split is not derived -- plus a third unnamed cause for the 148; C4 17.4.3 widening condition 2 makes :2120/:2147 TOP and contradicts 17.8.3, and keeping HELD needs a control-flow fact no assumption supplies -- the no-new-assumption claim is falsified on the pin; C5 a guard "position" is ill-defined for a site reached at several program points; C6 the typestate has no evaluator rule at all and _eval_is decides only for ir.Lit; C7 ir.Call.kwargs is NOT a complete key set in the graph lane, a direct false-SAFE channel for :383; C8 M-INH resolves an inherited body''s own self-calls against the base while the receiver overrides them, and 17.1.1''s "no call the survey would record" is false; C9 the base closure is name-keyed and its base map is not shipped; C10 p3a''s WILL_FAIL is structurally forbidden at depth>=2 so the attempted>=60 floor is unreachable on 62 of 93; C11 M-INH silently perturbs every guard''s depth and nothing measures it; C12 D11''s asymmetry argument is architecturally false -- scope entries are evaluated by the same evaluator every new rule extends), 8 must-fix, 1 suggestion. Verdict not_ready. Objections changing the gate: C1 C2 C3 C4 C6 C7 C10 C11; changing user decisions: D7 (C4 C5 C6 C10 C14 C15), D8 (C2 C3 C13), D9 (C8 C9 C11), D10 (C1 C7), D11 (C12).'
status: final
task_id: 260909_sema-move-family
date: '260909'
---

> Persisted verbatim by the orchestrator from the challenger agent's final report (no write tool).
> Target: `.praxia/docs/specs/260909_plr-sema-move-family-increment.md` (spec_version 1, status draft),
> worktree `/home/marielle/projects/praxis/.claude/worktrees/wt-20260909-172820`, branch
> `plr-sema-inc8-move-family`, analyzer HEAD `52178d80`, PLR pin `dd79c4c89`.
> Every citation below was read at the cited lines this pass; no number here is measured by this author.

# Increment 8 round-1 challenger report

The document's measured facts hold — the identical thirteen-entry residual across all three methods
(`outputs/plr-sema/unknown_ledger_260909_final.oracle_replay.json:241-261`), the 186/93 `unresolved_delegate`
cluster with `per_method` 31/31/31 (`outputs/plr-sema/unknown_ledger_260909_final.json:811-822`), the 216
(`:2172`) — and its central diagnosis, that the `unresolved_delegate` gap is mechanical rather than semantic,
is correct in outline. Almost everything downstream of that is not yet derived. **Five of the seven entries
the increment claims to remove are not reachable by the mechanisms as specified**, and in every case the
obstruction is a shipped property of the analyzer this document did not read: `_walk_closure`'s LIFO depth
assignment and its parent-less, deduplicating traversal (`plr-sema/src/plr_sema/derive/__init__.py:424-459`);
`derive_contract`'s hard binding of the argument map to `entry_K` and to `depth == 1` (`:640-651`);
`_eval_is`'s `ir.Lit`-only decision (`plr-sema/src/plr_sema/check/predicate.py:817-822`);
`lower_kwargs`'s renaming of every untrusted keyword to `?<i>` (`plr-sema/src/plr_sema/check/ir.py:577-590`);
and M1 clause 4's `**`-unpacking refusal, which sits directly on the one path `:383` must travel
(`plr-sema/src/plr_sema/derive/bindings.py:931-941`, and `move_lid`/`move_plate`'s own
`self.move_resource(..., **backend_kwargs)` at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2427-2437`,
`:2495-2505`). The three claims the document nominates for attack all fail, and the first fails on the pin
rather than on a synthetic fixture: §17.4.3's own widening condition 2 puts `:2120` and `:2147` at `TOP` and
thereby contradicts §17.8.3's prediction for them, and the only thing that rescues the prediction is the fact
that `pick_up_resource`'s `except` block ends in `raise e` — a control-flow fact no listed assumption
supplies. The gate as written (condition 1, "exactly six") is therefore predicted to fail on all 93
operations. Verdict: `not_ready` — the increment's shape is sound and worth keeping; §17.1, §17.4.3, §17.5
and §17.8.3 need re-deriving against the traversal and the lowering.

---

**C1 — blocker — §17.5.2 (lines 642-676), §17.8.3 (line 859), D10 (line 1208).**
`:383`'s new route needs the `_check_args` call site's `backend_kwargs` argument to resolve to an empty
complete `Seq`. §17.5.2 names exactly one further hop — the dict comprehension at `liquid_handler.py:2351` —
and misses the hop that decides 62 of the 93 operations. `move_lid` and `move_plate` do not call
`_check_args` at all; they call `self.move_resource(..., **backend_kwargs)` (`:2427-2437`, `:2495-2505`), a
call-side `**` unpacking into a delegate that itself declares `**backend_kwargs`. That is refused twice over
by M1 clause 4 (`compute_caller_args`'s own docstring: "call-side `ast.Starred`/`**` unpacking, or `D` itself
declares `*args`/`**kwargs`", `plr-sema/src/plr_sema/derive/bindings.py:931-941`), and §17.5.1 states
explicitly that M3 relaxes two clauses "and on four it does not touch". So for `move_lid`/`move_plate` the
entry point's own `**kwargs` never reaches any `_check_args` call site, `Var(W)` has nothing to resolve
against, and `:383` stays ½. Gate condition (1) fails on 62 of 93 operations, and §17.8.3's `:383` row and
its "certain 173" both inherit the error.
Evidence: draft `:642-676`, `:851-861`; `liquid_handler.py:2427-2437`, `:2495-2505`, `:2345-2351`;
`bindings.py:931-941`.
Remedy: either state a fourth relaxation (propagating a `**<name>` unpacking of the entry point's own
`**kwargs` parameter into the callee's VAR_KEYWORD parameter, with its own soundness argument and its own
fail-closed conditions), or restate §17.8.3's `:383` cell as `move_resource` only (31), and restate the gate:
with D10 taken the residual is six on 31 operations and seven on 62, which is not the uniform set condition
(1) is written over.

**C2 — blocker — §17.5.1(b) (lines 616-627), T53 (line 1090).**
M3 lifts the `depth == 1` restriction for "a `(K, D)` pair at any depth `d ≥ 1`", but at depth ≥ 2 there is
no `K`. `derive_contract` computes `compute_caller_args(entry_K, K)` — the caller is **always** the entry
point, captured once at depth 0 (`plr-sema/src/plr_sema/derive/__init__.py:628-651`) — and `_walk_closure`
yields `(rec, key, depth)` with no parent at all, adding each key to `seen` on first pop so a function
reachable from several callers is inlined exactly once (`:445-459`). Two horns, both fatal as written:
(a) if `K` stays `entry_K`, `_find_delegate_call(move_lid_ast, "_check_args")` finds nothing (`move_lid`'s
body has no such call), so nothing binds at any depth and `:375` fails on the same 62 operations as C1;
(b) if `K` becomes the actual parent, `_walk_closure` must carry parentage and stop deduplicating across
parents — unspecified, absent from T53's scope cell, and it destroys the fold's own soundness argument,
because "the guard genuinely executes once per call site, so `SAFE` requires `SAFE` at all of them" is
exactly what a single-parent attribution cannot see. At the pin `_check_args` is reached from `move_resource`
twice **and** from `pick_up_resource` once (`:2079`); under (b) the analyzer folds over one caller's sites
and silently ignores the other's — a `SAFE` justified by call sites that are not all the call sites.
Evidence: `derive/__init__.py:628-651`, `:445-459`; draft `:604-627`, `:1090`; `liquid_handler.py:2079`,
`:2345-2350`, `:2364-2369`.
Remedy: state normatively what `K` is at depth ≥ 2, state what happens to a delegate reachable from more than
one caller (the only sound answer is: fold over **every** admitted call site on **every** path in the
closure, or decline), and re-size T53 — the parentage change to `_walk_closure` is not in the ~200 LOC.

**C3 — blocker — §17.1.4's fence table (lines 317-322), §17.8.3's certain/target split (lines 863-870), Q9 (line 1178).**
The document's third nominated claim does not survive. Depth is not a property of the source: it is assigned
by `_walk_closure`'s LIFO frontier at **push** time and settled at **pop** time (`derive/__init__.py:445-459`),
over a `delegates_to` list the survey emits as `sorted(set(...))` (`scripts/survey_plr_preconditions.py:163`,
`:338`). Trace it for entry point `move_resource`: the frontier is pushed `[_check_args(1), _log_command(1),
drop_resource(1), move_picked_up_resource(1), pick_up_resource(1)]`; `pop()` takes `pick_up_resource(1)`,
which pushes `_check_args(2)`; that depth-2 entry is popped before the depth-1 entry buried below it, so
**`_check_args`'s guards are inlined at depth 2**, `caller_args` is never computed for them at all, and the
clause that refuses is **clause 6**, not "clauses 1–2, the single-call-site rule" as the table states. The
same trace gives `move_lid`/`move_plate` `_check_args` at **depth 3** via `pick_up_resource`, not "depth 2 via
`move_resource`". This is not cosmetic: the whole 173/148 split is presented as derived from which M1 clause
refuses which entry point, and it is not derived. It also supplies a **third candidate cause** for the 148
that §17.1.4's open-diagnosis box does not name and could have named from source: any delegate reachable by
two paths lands at the deeper depth, so `aspirate`/`dispense`/`drop_tips` need only one sibling delegate that
also calls `_check_args` to lose their depth-1 status.
Evidence: `derive/__init__.py:445-459`, `:640-651`; `survey_plr_preconditions.py:163`, `:329-345`;
draft `:317-322`, `:863-870`, `:1178-1187`.
Remedy: re-derive the fence table from the traversal, not from the source text; add the LIFO-depth artifact as
candidate cause (c) in §17.1.4's box; and either publish the per-guard `depth` for all 544 operations from the
shipped contract table before the sprint starts (it is already on the wire, `InlinedGuard.depth`), or restate
every "certain" number as diagnosis-dependent.

**C4 — blocker — §17.4.3 widening condition 2 (lines 570-576) vs §17.8.3 (lines 856-857), §17.4.3's no-new-assumption box (lines 586-594).**
The document's first nominated claim fails on the pin, not on a synthetic fixture. Condition 2 is normative:
an assignment to `self.<F>` inside an `ast.Try` handler "is **not** folded into the ordered state; instead the
state becomes `TOP` at every position after the enclosing `try`". `pick_up_resource`'s rollback is inside the
`try/except` at `liquid_handler.py:2085-2092`, and `:2094`, `:2120` and `:2147` are all at positions **after**
that `try`. So the rule the document ships makes `:2120` and `:2147` read `TOP`, and §17.8.3 predicts both
`SAFE` on 93 — the two statements cannot both hold. The sentence that tries to have it both ways ("On the pin
this costs nothing, because both `:2120` and `:2147` are reached only when `pick_up_resource` returned
normally, and the analyzer cannot know that; taking the loss is the point") concedes the loss in its second
half and denies it in its first. And the fact that rescues the prediction — the handler's last statement is
`raise e` (`:2092`), so no execution falls out of the handler into a later position — is a **control-flow**
fact about a `Try` handler's termination that neither **A-SINGLE** nor **A-COMPLETES** supplies. That is
precisely the falsification §17.4.3 invites, and it exists at the pin.
Evidence: `liquid_handler.py:2085-2094`, `:2119-2120`, `:2146-2147`; draft `:570-576`, `:856-857`, `:586-594`.
Remedy: replace condition 2 with a derived rule that inspects the handler's own terminator ("a handler whose
every path ends in a `raise` contributes no state to positions after the `try`; any other handler widens"),
publish it as part of §17.8.1 block (3), and either name the new assumption or show the rule is derived. If
neither, `:2120`/`:2147` must move to the "stays ½" column and the gate's residual is eight.

**C5 — blocker — §17.4.3's ordering box (lines 551-559), §17.4.2.**
"Every guard in the flattened list therefore acquires a **position**" is false for any site reached at more
than one program point, and the move family contains two such sites. The contract table carries one guard
entry per `(site, lineno)` — `derive_contract` emits `rec.findings` once per key and `_walk_closure` visits
each key once (`derive/__init__.py:445-459`, `:652-681`) — while the proposed walk assigns positions to **call
statements**. `_check_args` executes three times per `move_resource` operation (`:2345`, `:2364` and `:2079`),
at three different positions, and after M-INH `_state_updated` executes twice, at `:2094` (state `HELD`) and
`:2264` (state `EMPTY`, since `:2263` clears the field). A guard on an anchor inside either function would
have two different pre-states and one entry to record them in.
Evidence: `derive/__init__.py:445-459`, `:652-681`; `liquid_handler.py:2079`, `:2261-2264`, `:2345`, `:2364`;
draft `:551-559`.
Remedy: one normative sentence — a guard reached at several positions takes the **join** of the states at all
of them, which is `TOP` on any disagreement — plus an AC-17.3 fixture with a two-call-site delegate whose two
positions disagree, asserted `guard_env_dependent` and not a verdict.

**C6 — blocker — §17.4 as a whole (lines 504-594), §17.7 (lines 732-750), §17.8.4 (lines 889-901).**
§17.4 specifies a lattice, an anchor shape, an effect table and an order, and never specifies **how the state
reaches the evaluator**. The three guards are `Is` nodes over `EnvRef(("self","_resource_pickup"))`.
`_resolve_env_ref` admits exactly three path shapes and returns `(ir.Top(), None)` for everything else
(`plr-sema/src/plr_sema/check/predicate.py:309-356`), and `_eval_is` decides **only** for an `ir.Lit`,
returning `None` for `Ref`, `Seq` and `Top` alike (`:817-822`). So the increment needs, unstated: (i) a
**fifth** `EnvRef` path shape for `self._resource_pickup` — a different path from R-ARM's
`self._resource_pickups`, so §17.7's "R-ARM is a fourth instance" accounting is short by one; and (ii) a new
`Is`-position rule for a non-`Lit` value. The `HELD` payload makes (ii) worse, not better: if the path
resolves to the payload `ir.Ref`, `_eval_is` returns ½ and `:2120`/`:2147` do not decide, so "the payload
never affects the three guards' truth" is only true if the payload is *not* what the path resolves to — which
the document never says. And the obvious repair (broaden `_eval_is` to "any non-`Top` value is not `None`") is
a benchmark-wide change to every `Is` guard, which gate condition (5) does not fence and §17.8.4's
falsification map does not list.
Evidence: `predicate.py:309-356`, `:817-822`, `:934-944`; draft `:514-521`, `:732-750`, `:889-901`.
Remedy: specify the resolution rule and the `Is` rule normatively, add `n_typestate_decided` to §17.8.1 block
(3) as a counter distinct from the state assignment, re-run §17.7's accounting with the fifth path shape and
the new evaluator rule named, and add an AC asserting no other `Is` guard in the benchmark changes value.

**C7 — blocker — §17.5.2's completeness claim (lines 648-654), AC-17.5 (lines 1025-1037).**
"It is **complete** in R-HEAD's sense — an operation's keyword set is total in the IR, not a lower bound" is
the load-bearing sentence of the only mechanism in this increment that turns an **emptiness** claim into
`SAFE`, and it carries no citation. It is false in the graph lane: `lower_kwargs` keeps a keyword's real name
only when it is in the per-contract `trusted` list and otherwise stores it under the synthetic key `f"?{i}"`
(`plr-sema/src/plr_sema/check/ir.py:577-590`); when `param_names` is `None`, **every** key is renamed. The
residual keys — those not among the entry point's declared parameters — are exactly the untrusted ones. Worse
in the other direction: a keyword the extractor did not model does not appear in `arguments` at all, so the
residual `Seq` is falsely **empty**, `:383` returns `F`, and the guard is `SAFE` while PLR would raise
`TypeError` at `:383`. That is a false `SAFE` with nothing between it and the verdict, reached through the
mechanism the document declares "one-directional by construction" — the one-directionality argument is about
`WILL_FAIL`, and answers a different question.
Evidence: `ir.py:194-204`, `:577-590`, `:750-795`; draft `:648-676`, `:1025-1037`.
Remedy: state the completeness property as a **precondition** with a citation per lane (`lower_calls` vs
`lower_graph`), make the Term decline whenever any `?<i>` key is present or `param_names` is absent —
fail-closed, and cheap — and add the negative fixture to AC-17.5 in the graph lane, not only in tier 1.
§16.5.6's lane-asymmetry disclosure applies to this rule and is not made.

**C8 — blocker — §17.1.1 (lines 180-212), §17.2's direction-of-change box (lines 451-457), AC-17.1.**
Two defects, one mechanism. (a) The stated ground is false: `Resource._state_updated` **does** contain a call
the survey records — `callback(self.serialize_state())`
(`external/pylabrobot/pylabrobot/resources/resource.py:934`) — and `serialize_state` is defined on `Resource`
itself (`:838`), so `visit_Call` puts it in `delegates_to` (`survey_plr_preconditions.py:290-292`) and
`_walk_closure` will follow it. The claim "no `raise`, no `assert`, and no call the survey would record as a
precondition" is wrong at the cited lines; only the "zero guards" conclusion happens to survive, and it
survives by luck. (b) The mechanism it exposes is the real problem: `resolve` binds an inherited body's own
self-calls with the **base's** class-first, same-module keys (`derive/__init__.py:414-421`), so
`self.serialize_state()` inside `Resource._state_updated` resolves to `Resource.serialize_state` even though
the receiver is a `LiquidHandler` that **overrides** it (`liquid_handler.py:214-237`). M-INH therefore trades
a fail-closed `unresolved_delegate` for a claim derived from a body that does not run. §17.2's box —
"Resolving a previously-unresolved call **adds** that function's guards to the closure … the **sound**
direction" — is wrong in exactly this case: relative to today it *removes* the fail-closed `UNKNOWN` and
replaces it with the wrong function's (here, empty) guard set. The three fail-closed conditions cover
ambiguity **among bases**, a base outside the index, and closure doubling; none covers an override on the
analyzed class or on any subclass of it.
Evidence: `resource.py:838-849`, `:932-934`; `liquid_handler.py:214-237`; `derive/__init__.py:414-421`;
`survey_plr_preconditions.py:290-299`, `:347-357`; draft `:180-212`, `:451-457`, `:970-981`.
Remedy: add a fourth fail-closed condition — an inherited body's own `self.<n>()` call resolves only when
**no** class in the analyzed class's own closure (or, conservatively, no class in the index deriving from the
defining base) redefines `n`; otherwise the gap stands — and correct §17.1.1's ground to "zero guards", which
is the claim AC-17.1 actually asserts.

**C9 — blocker — §17.2's "the base closure and the module map are DERIVED and already shipped" (lines 426-434).**
Neither shipped helper supplies what M-INH needs, and the gap is where a wrong resolution enters.
`build_plr_class_index` keys **by bare class name**, whole-tree, first definition wins via `setdefault`, and
returns `class_modules` on the same bare key (`plr-sema/src/plr_sema/derive/receiver_state.py:1241-1268`), so
two same-named classes in different PLR modules collapse and `module_of(B)` can name the wrong module — a
resolution to a different class's method of the same name, invisible to condition 1, which only counts
definitions **inside** the computed closure. `subclass_closure_from_bases` consumes a
`{name: tuple[base names]}` map (`predicate.py:541-566`) that **nothing builds**: extracting base names from
`ClassDef.bases` means handling `ast.Attribute` bases, `ast.Subscript` generics and import aliases — new code
with its own failure modes. "No base-class name is typed anywhere" is true and beside the point.
Evidence: `receiver_state.py:1241-1268`; `predicate.py:541-566`; draft `:426-434`, `:970-981`.
Remedy: specify the base-name extractor and its fail-closed shapes (an unresolvable base expression makes the
whole closure refuse, not merely contribute nothing), key the class index on `(module, name)` for this use or
refuse on a name collision, and add the collision case to AC-17.1's three fixtures as a fourth.

**C10 — blocker — §17.9's mutant class (lines 942-958), AC-17.3 (line 1008), D7.**
`p3a_pickup_already_held` requires the static side to emit `WILL_FAIL` at `:2070`. `guard_is_unconditional`
returns `False` unconditionally for `depth >= 2` (`predicate.py:1092-1093`), and at `depth == 1` it
additionally requires `caller_reachability_clear` and `caller_scope_trail`, both `depth == 1`-only fields that
§17.5.1 explicitly leaves untouched (`:1094-1109`; draft `:637-640`). Under the traversal of C3,
`pick_up_resource` sits at depth 1 for `move_resource` but at depth **2** for `move_lid`/`move_plate` — so
`:2070` can never emit `WILL_FAIL` on 62 of the 93 operations, by construction and independently of the
typestate. The declared floor is `achieved == attempted` with `attempted >= 60`, and §17.9 says the mutable
population is the 93 move operations. The floor is therefore unreachable unless every attempt is drawn from
the 31 `move_resource` operations, which the text does not say.
Evidence: `predicate.py:1092-1113`; `derive/__init__.py:445-459`; draft `:942-958`, `:1002-1009`.
Remedy: state the mutable sub-population explicitly (`move_resource` only, or entry-point `pick_up_resource`
operations if the corpus has any), re-derive `attempted`, and assert the depth of `:2070` per entry point as
part of AC-17.3 — a floor whose denominator is structurally capped below its own threshold is increment 6
§15.16.3's failure in a new costume.

**C11 — blocker — §17.2 (lines 451-457), §17.8.1 block (1) (lines 768-771), §17.8.2 conditions (4)-(5).**
M-INH changes `delegates_to` for many PLR functions, and `delegates_to` is what `_walk_closure` pushes: adding
`_state_updated` to `pick_up_resource` and `drop_resource` changes push order, hence pop order, hence the
**depth** at which unrelated delegates are inlined (`derive/__init__.py:445-459`). Depth gates `caller_args`,
`caller_reachability_clear`, `caller_scope_trail` and D1's `WILL_FAIL` lift (`derive/__init__.py:640-651`;
`predicate.py:1092-1109`). So M-INH can silently move guards into and out of the depth-1 population
benchmark-wide — including on the 216 `pick_up_tips` operations condition (4) protects — with no guard body
changing at all. §17.2's blast-radius box considers only "it may add guards", and T50's published closure size
and guard count cannot detect a depth change.
Evidence: `derive/__init__.py:445-459`, `:640-651`; `predicate.py:1092-1109`; draft `:451-457`, `:768-771`.
Remedy: T50 must publish the **per-guard depth** before and after, not only closure size and guard count, and
AC-17.1 must assert the depth multiset is unchanged for every entry point whose newly-resolved set is empty.
If depths move, the ordering constraint "T50 before T52" is not sufficient — T53's own selection becomes
T50-dependent too.

**C12 — blocker — §17.1.5's normative refusal box (lines 381-393), §17.12 (lines 1112-1117), D11.**
The argument that distinguishes D11 from the four mechanisms taken is: "Every other mechanism … that can
produce a `SAFE` does so through a guard's own `fires is False` return, where a wrong answer is at least
visible as a guard the analyzer claims not to fire. A wrong `F` in a **scope** entry is different in kind."
That is architecturally false. `_scope_entry_value` re-parses each trail entry and evaluates it with **the
same `ctx`** through the same `evaluate_predicate` (`predicate.py:1011-1025`), and `scope_excludes` returns
`SAFE` on the first `F` before any predicate is evaluated (`:1040-1044`, `:1442-1444`). Every rule this
increment adds — the amended `Seq`-truthiness clause, R-ARM, the typestate's `Is` decisions, and any name M3
newly binds — is therefore *also* live inside scope entries and can produce exactly the silent excision the
box reserves for E-TYPE. D11 differs in **degree** (six sites at once, on a chain of `isinstance` arms) and in
the fact that its `F` is a type claim; it does not differ in kind. Nothing in §17.8.1's nine blocks counts
scope exclusions, so a new silent exclusion anywhere outside the move family is unobservable except through
the tier-1 oracle's `unsound_scoped`, which only sees operations that actually raised.
Evidence: `predicate.py:1011-1025`, `:1040-1044`, `:1442-1444`; draft `:381-393`, `:1112-1117`.
Remedy: restate the D11 argument on its true ground (an exactness field is a *derived type* claim over a
corpus this increment cannot audit, and it clears six sites at once), and add a tenth published block:
`n_scope_excluded` per site, before and after, with any newly-excluded site named. That block also gives
§17.8.2 failure mode 2 something to point at.

**C13 — must-fix — §17.5.1(a) (lines 606-614), T53 (line 1090).**
"`caller_args` becomes, additively, a list of per-call-site maps" plus "a wire consumer seeing the old
single-map shape, or `None`, behaves exactly as today" specifies the consumer and not the producer. The three
shipped consumers call `caller_args.get(...)` on a `Mapping` (`predicate.py:1199-1208`, `:1222-1231`, and
`_Ctx.caller_args`'s own type), so re-typing the same key breaks them, while adding a new key leaves the old
one to go stale. The cache key and the contract-table round trip are affected either way, and T53's gate lists
`test_cache.py` without saying what it must assert.
Evidence: `predicate.py:1199-1231`, `:1431`; draft `:606-614`, `:1090`.
Remedy: name the wire field and its shape normatively (a new `caller_args_sites` list beside the existing
`caller_args`, or a re-typed key with every consumer named), and state the cache consequence.

**C14 — must-fix — §17.7 item 1 (lines 736-743), D7.**
The D4 precedent holds for the **path shape** and is verified: HM-25's tenth unit is booked as one collective
unit for "an `EnvRef` path admitted against the observation record", and its probe imports `_resolve_env_ref`,
"the ONE symbol implementing all three rules" (`plr-sema/src/plr_sema/_hand_maintained.py:350-362`,
`:1038-1050`). R-ARM lands inside that symbol, so it genuinely rides the unit. **The amended
predicate-position clause does not**: it lands in `evaluate_predicate` (`predicate.py:934-944`), which no
HM-25 probe imports or exercises, so the row's loud-failure property — the whole ground on which D7 is
recommended YES — does not extend to the one evaluator rule this increment adds. The document also treats two
structurally identical cases in opposite directions: the truthiness clause is free "on D4's precedent" while
the residual-`**kwargs` Term, equally a resolution of an existing node against already-modelled data, is said
to ride D7. That asymmetry runs in the direction that lowers the ask.
Evidence: `_hand_maintained.py:306-362`, `:1000-1053`; `predicate.py:934-944`; draft `:736-757`.
Remedy: either extend the tenth unit's probe to exercise the predicate-position clause (and say so in HM-25's
`what`), or book the clause as the eleventh unit and move the typestate's shapes to a twelfth — D7 becomes
10 → 12. Either is a ceiling unit, not a row; the point is that an unmeasured rule inside a LOUD-failure row
is the silent-collapse mode HM-24 already produced once.

**C15 — must-fix — §17.7's D7 contingency (lines 720-730), T52 (line 1089).**
"`_measure_hm25` measures the row by importing the symbols that implement its patterns … if the measured count
would exceed 11, T52 STOPS" is not mechanically checkable: `_measure_hm25` runs probes and then returns a
**hand-written integer** (`_hand_maintained.py:306-390`, the same shape as `_measure_hm24`'s `return 3` at
`:303`), so "the measured count" is a human judgement, not a computed one. And `_typestate_anchor` is
**already** imported by that function (`:373`): if P5 is implemented as a variant of increment 1 P2's anchor —
the natural implementation, since P5 is a property/assignment shape on the same kind of field — there is no
new symbol to import and the eleventh unit is unmeasurable.
Evidence: `_hand_maintained.py:303`, `:326-330`, `:364-377`; draft `:720-730`.
Remedy: name the new symbol T52 must add (and require it to be distinct from `_typestate_anchor`), or state
that the eleventh unit's probe is an exercise of the anchor function against a synthetic `property`-with-a-fat
setter and asserts the absence rule bites — which is AC-17.3's fixture, reused as the probe.

**C16 — must-fix — §17.3's O3 box (lines 461-500), AC-17.2.**
`arm_slots` is argued as "a claim about what the dict *contains* at one instant", and then used to decide a
guard at a different instant. The key set is not invariant: `_resource_pickup`'s setter is
`self._resource_pickups[0] = value` (`liquid_handler.py:183-185`), which **creates** key 0 in an empty dict,
so a receiver whose backend declares zero arms acquires a key at the first pickup; and the dict is rebuilt
wholesale by `setup` (`:212`), which the capture point sits after. The soundness property the "complete `Seq`"
declaration actually needs is *the key set is stable for the whole program after the capture point*, which is
true at this pin for `num_arms >= 1` and is nowhere stated.
Evidence: `liquid_handler.py:176`, `:183-185`, `:212`; draft `:461-500`, `:982-996`.
Remedy: state the stability property as the completeness precondition, and have AC-17.2 assert it (an
operation sequence with a pickup and a drop leaves `sorted(self._resource_pickups)` unchanged).

**C17 — must-fix — §17.8.3's per-entry table (lines 849-861), §17.9's tier-2b box.**
The table states `:2055 -> SAFE on 93`, `:2070/:2120/:2147 -> SAFE on 93` and `:375/:383 -> SAFE on 93` without
the lane qualification increment 7 §16.5.6 made normative for exactly this class of rule: R-ARM, the
typestate's inter-operation carry and the residual-kwargs Term are all observation- or lowering-dependent, and
the graph lane has no observation at all. §17.9 discloses that tier 2b **can** move; §17.8.3 reads as if the
numbers were lane-independent.
Evidence: `.praxia/docs/specs/260909_plr-sema-observation-increment.md:1127-1140`; draft `:849-861`, `:935-940`.
Remedy: add "tier 1" to the table's header and one sentence naming the graph lane's value for each row.

**C18 — must-fix — §17.5.1's "The pin makes this exact" (lines 629-635), frontmatter sources.**
There are **eleven** `self._check_args(...)` call sites in `liquid_handler.py` — `:541`, `:687`, `:1037`,
`:1238`, `:1481`, `:1559`, `:1745`, `:1895`, `:2079`, `:2345` **and `:2364`** — and §17.5.1's "All ten" list
omits `:2364`, the second `move_resource` site, which is the very site whose distinct `default={"drop"}` the
per-call-site fold argument depends on and which AC-17.4 asserts by name. The frontmatter's "eight of the ten
`_check_args` call sites" inherits the same undercount.
Evidence: `liquid_handler.py:541`, `:687`, `:1037`, `:1238`, `:1481`, `:1559`, `:1745`, `:1895`, `:2079`,
`:2345`, `:2364`; draft `:629-635`, frontmatter `:10`.
Remedy: correct to eleven and add `:2364-2369` to the enumeration.

**C19 — must-fix — §17.0.1 (lines 74-93), §17.8.1 block (8).**
The "per-operation ground truth" fifteen-finding list is read from the ledger's **`collision_ops`** block,
whose selection criterion is `n_row_id_collisions: 12`
(`outputs/plr-sema/unknown_ledger_260909_final.json:2173-2185`) — not a canonical per-operation dump. Its
content agrees with the replay's residual set, so the substance stands, but the document presents a diagnostic
block as ground truth without naming it, and the twelve row-id collisions are an instrument anomaly no part of
§17.8 accounts for even though they bear on the 93-operation population the gate ranges over.
Evidence: ledger `:2172-2185`; draft `:74-93`, `:791-793`.
Remedy: name the block, and have §17.8.1 block (8) publish `n_row_id_collisions` before and after with a
sentence on whether a collision can double-count an operation in the gate's denominator.

**C20 — must-fix — §17.4.3 condition 1 (lines 564-569).**
Two problems in one sentence. The citation `plr-sema/src/plr_sema/check/predicate.py:1047-1057` is
`_entry_satisfies_uncond`, not `guard_is_unconditional` (which begins at `:1060`) — the ways (1)-(3) are
there, but the named function is not. More substantively, condition 1 tests a **call statement's**
`scope_trail`, and no call statement has one: `scope_trail` is a field of a `PreconditionFinding`
(`survey_plr_preconditions.py:106`, `:186-189`), and the only per-call-site scope data on the wire is
`caller_scope_trail`, which exists at `depth == 1` only. The new walk must compute a call statement's
enclosing scope from the AST itself — new machinery T52's ~110-LOC estimate for "the ordered walk and the four
widening conditions" does not obviously carry.
Evidence: `predicate.py:1047-1113`; `survey_plr_preconditions.py:106`, `:186-199`;
`derive/__init__.py:640-651`; draft `:564-569`, `:1098-1101`.
Remedy: fix the citation, state where a call statement's conditionality comes from, and re-size T52.

**C21 — suggestion — §17.8.2 (lines 803-813), §17.0.3.**
Taking C1, C2/C3, C4 and C10 together, the gate's condition (1) is predicted to fail on **all 93** operations
with all four hooks taken — the mirror image of increment 7 round 1's C2, and the same defect: a gate whose
outcome is already determined by facts the document did not read decides nothing. The document's instinct to
gate on structure rather than on a verdict is right and should be kept; what it needs is a residual set
re-derived after C1-C7 are answered, plus the `n_scope_excluded` and per-guard depth blocks (C11, C12), which
are what would make a divergence attributable rather than merely visible.
Evidence: draft `:141-146`, `:803-826`; C1, C2, C3, C4, C10.
Remedy: re-derive §17.1's thirteen-entry disposition after the traversal and lowering facts are folded in, and
re-state the gate over whatever set survives — including the honest possibility that increment 8's residual is
eight or nine and that the `unresolved_delegate` condition (2) is the only clean win.

---

## Verdict

`not_ready`. Confidence: **high** on C1-C10 and C13-C20 (each is a shipped property of the analyzer or of PLR,
read at the cited lines this pass); **medium** on C11 and C12 (the mechanism is certain, the benchmark-wide
magnitude is not measurable from here); **medium** on C21, which is an aggregate of the others.

Objections that change the gate: **C1, C2, C3, C4, C6, C7, C10, C11**.
Objections that change a user decision: **D7** (C4, C5, C6, C10, C14, C15), **D8** (C2, C3, C13),
**D9** (C8, C9, C11), **D10** (C1, C7), **D11** (C12).

What the document gets right and should not lose in revision: the measured facts are exactly as cited and were
re-verified this pass; §17.0.1's identical-residual observation is real and is the right foundation for a
structural gate; the `unresolved_delegate` diagnosis is correct and its closure is genuinely cheap; the
refusal to retire the reason (§17.6) and the refusal to admit a site list into `excludes_sites` (§17.8.4
refusal 1) are both right; and §17.1.4's decision to publish a falsified prediction of the preceding increment
as prominently as its own claims is the discipline that made C3 findable at all.
