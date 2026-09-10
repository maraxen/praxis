---
title: 'plr-sema increment 8 (the move_* family, spec_version 2) -- adversarial round 2, challenger'
description: 'Round-2 challenger pass (praxia:spec-challenger, Opus) on the increment 8 remediation: R2-C1..R2-C14, verdict not_ready. All twenty-one round-1 dispositions in SS17.16 are honest -- every one names a change the text contains, no concession recorded as a rebuttal, and BOTH round-1 rebuttals (C6, C10) independently re-verified sound. But spec_version 2 re-establishes round 1s central outcome by two NEW independent routes. R2-C1 (blocker): M-SURF fixes the surface ATTACHMENT half only; row candidacy runs through collect_env_ref_method_names, which scans guard.predicate and guard.caller_args, and caller_args is populated only for a depth==1 guard against an entry point with exactly one call site -- self.backend.drop_resource appears only at liquid_handler.py:2364 inside move_resource, which has TWO _check_args calls and pops _check_args at depth 2, so there is no *.drop_resource row anywhere in derived_contracts.json (nine pick_up_resource rows, zero drop_resource) and :375 stays 1/2 on all 93 with M-SURF, M3, D7, D8, D9 all taken. Residual is EIGHT not seven; SS17.8.3s 321->0 falsified; the spec worried about pick_up_resource (which IS a row) instead of drop_resource. R2-C2 (blocker): SS17.4.2s third absence clause (qualname defined at more than one lineno) makes the increments only typestate anchor ABSENT, since _resource_pickup is a getter/setter pair at :179/:184 and the inherited C15 docstring says clause 3 is exactly for that -- the identical contradiction class round 1s C4 forced to be re-derived, one clause over. R2-C3 (blocker): SS17.4.0s "the route already exists" overreaches -- consumed indices are recorded only in tipstate.pys own-guards loop, which is inside if channels is not None, and move_* declares no use_channels so channels is None; parse_bridge_atoms bare-self shape is used only in the channel_guards loop which records no consumed index; atom_truth/_finding_for_atom are typed over TipState fed by a per-channel TipWalk fold. No shipped path satisfies all four requirements, so T52 must invent the evaluator entry point, gate, matcher, walk and lattice generalisation. R2-C4 (major): p3a_pickup_already_held is not constructible -- every mutator in predicate_mutants.py is a Callable[[dict],bool] kwargs transform and a second pick_up_resource is a program-structure mutation, which is the same fact SS17.9 uses two paragraphs later to refuse a :2055 mutator. R2-C5 (major): arithmetic -- decided guards are not findings and the two counts are disjoint per site (321+223=544), so n_findings is 3,903-894-186 = 2,823, not the 3,717 SS17.8.3 and AC-17.6 hard-code. R2-C6 (major): the derived handler-terminator test has an unfenced UNSOUND direction (a handler whose last statement is ast.Raise but which contains an earlier Return/Break/Continue leaves normally carrying rolled-back state -> false SAFE), and it is not among the two shapes SS17.15 named. R2-C7 (major): three semantic AC orphans -- AC-17.4/AC-17.5 assert per-operation benchmark counts but T53/T54s gate cells run only pytest files, and AC-17.3 asserts p3a but T52 does not touch predicate_mutants.py. Plus R2-C8..R2-C14 (text-level). Favourable findings recorded: SS17.1.4s MECHANISM is correct and confirmed by the artifact (five attached entries, only pick_up_tips executed, 223+321=544); D10s refusal is correctly derived twice over at bindings.py:971-972 and :974-975; D11s repaired argument holds; D7s two units are honestly argued and nothing in v2 needs a 27th row; and SS17.15s owed item (2) is answerable POSITIVELY from the cited instrument -- exactly two unresolved calls in the move closure, both _state_updated, and M-INHs newly-admitted bodies add none.'
status: final
task_id: 260909_sema-move-family
date: '260909'
---

> Persisted verbatim by the orchestrator from the round-2 challenger agent's final report (no write tool).
> Target: `.praxia/docs/specs/260909_plr-sema-move-family-increment.md` (spec_version 2, status
> `reviewed-round-1`, 1941 lines, committed at `4dfade54`). Round 1:
> `.praxia/docs/audits/260909_plr-sema-move-family-round1-challenger.md` (C1-C21, `not_ready`) and
> `.praxia/docs/audits/260909_plr-sema-move-family-round1-defender.md` (11 conceded, 9 partial, 1
> rebutted). Worktree `/home/marielle/projects/praxis/.claude/worktrees/wt-20260909-172820`, branch
> `plr-sema-inc8-move-family`, analyzer HEAD `52178d80`, PLR pin `dd79c4c89`.

# Increment 8 round-2 challenger report

Target: `/home/marielle/projects/praxis/.claude/worktrees/wt-20260909-172820/.praxia/docs/specs/260909_plr-sema-move-family-increment.md` (spec_version 2, `reviewed-round-1`, 1941 lines), read in full.
Round 1 read in full: `.../.praxia/docs/audits/260909_plr-sema-move-family-round1-challenger.md`, `.../260909_plr-sema-move-family-round1-defender.md`.

**Headline.** The twenty-one dispositions in §17.16 are honest — every one names a change the text actually contains, and both REBUTs (C6, C10) are factually correct; I re-verified their load-bearing facts from source and they hold. But spec_version 2 re-establishes round 1's central outcome by two *new*, independent routes, and one of them is visible in a shipped artifact the document explicitly declined to read (`plr-sema/data/derived_contracts.json`). **Gate condition (1) is again predicted to fail on all 93 operations.** Verdict `not_ready`.

The single most useful thing I can report: the spec's own §17.15 named three claims for round 2 to attack. Item (1) — "if `LiquidHandlerChatterboxBackend.pick_up_resource` is absent from the surface `rows` for a reason M-SURF does not address … then `:375` does not clear and gate condition (1) fails on all 93" — was the right thing to worry about, but the spec worried about the wrong method. `pick_up_resource` **is** a row. `drop_resource` is not, and cannot become one under M-SURF as specified.

---

## R2-C1 — BLOCKER — §17.1.4 (M-SURF), §17.8.2 condition (1), §17.8.3, §17.0.3, AC-17.4, AC-17.5, frontmatter, Q9

**Claim challenged.** "M-SURF … alone clears `:375` and `:383` on the 148 … `:375`. 321 → **0**" (§17.8.3), and §17.1 table cell "`:375` … **Y** (M-SURF) **and Y iff D8** (the 93) | `SAFE` on 321", and the gate's "removes SIX of the move family's thirteen residual entries and leaves SEVEN".

**Evidence, read this pass.**

1. The `:375`/`:383` site rules reach the surface through one key. `_check_args_surface_row` (`plr-sema/src/plr_sema/check/predicate.py:1234-1249`):

```python
return ctx.backend_surface.get(f"{backend_class}.{method}")
```

with `method = _check_args_method_name(ctx)` = the last path segment of `ctx.caller_args["method"]` (`predicate.py:1199-1208`), and `ctx.backend_surface = contract.get("backend_surface", {}).get("rows", {})` (`predicate.py:1439`). So the lookup needs a **row**, not merely an attachment.

2. The rows shipped at this pin. `plr-sema/data/derived_contracts.json:3-5` reports `n_surface_candidates: 160`, `n_surface_absent_by_c15: 71`, `n_surface_rows: 89`. Every chatterbox row (grepped, exhaustive):

```
151: "LiquidHandlerChatterboxBackend.aspirate"          params ["ops","use_channels"], has_var_keyword true
159: "LiquidHandlerChatterboxBackend.aspirate96"        params ["aspiration"],         has_var_keyword false
166: "LiquidHandlerChatterboxBackend.can_pick_up_tip"
175: "LiquidHandlerChatterboxBackend.dispense"          has_var_keyword true
183: "LiquidHandlerChatterboxBackend.dispense96"
190: "LiquidHandlerChatterboxBackend.drop_tips"         has_var_keyword true
198: "LiquidHandlerChatterboxBackend.drop_tips96"
205: "LiquidHandlerChatterboxBackend.pick_up_resource"  params ["pickup"], has_var_keyword false
212: "LiquidHandlerChatterboxBackend.pick_up_tips"
220: "LiquidHandlerChatterboxBackend.pick_up_tips96"
```

There is **no `*.drop_resource` row anywhere in the file** — a grep for `^      "[A-Za-z_]+\.(pick_up_resource|drop_resource|move_picked_up_resource)":` returns nine `pick_up_resource` rows and zero `drop_resource` rows.

3. Why, and why M-SURF does not fix it. Row candidacy is `qualname`'s last segment ∈ `selected_method_names` (`plr-sema/src/plr_sema/derive/receiver_state.py:1537-1542`), and `selected_method_names = collect_env_ref_method_names(contracts)` scans exactly two JSON locations per guard — `guard["predicate"]` and `guard["caller_args"]` (`receiver_state.py:1488-1500`). `caller_args` is populated **only** for a `depth == 1` guard, against the entry point (`plr-sema/src/plr_sema/derive/__init__.py:640-651`), and `compute_caller_args` refuses a caller whose body holds more than one call site (`plr-sema/src/plr_sema/derive/bindings.py:966-968`, via `_find_delegate_call`'s `return calls[0] if len(calls) == 1 else None` at `:884-886`).
   `self.backend.drop_resource` occurs as a `_check_args` argument at exactly one place in PLR: `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:2364-2369`, inside `move_resource`, whose body carries **two** `_check_args` calls (`:2345`, `:2364`) and from which `_check_args` is popped at **depth 2** (the LIFO trace both round-1 parties independently reproduced). `drop_resource` itself calls no `_check_args` — I read `:2132-2299` in full and there is none. So `drop_resource` never enters any `caller_args`, never enters `selected_method_names`, never becomes a row.
   `pick_up_resource` escapes only by accident of the corpus-independent contract table: `LiquidHandler.pick_up_resource` is itself an entry with a unique depth-1 `_check_args` call at `:2079`, so its `caller_args["method"]` supplies the name.
   **M-SURF changes the ATTACHMENT filter only** (`plr-sema/src/plr_sema/derive/__main__.py:341-356`), i.e. *which entries receive the `rows` dict*. It adds no rows. And §17.5.1's C13 remedy deliberately puts M3's per-site data in a **new** field `caller_args_sites`, which `collect_env_ref_method_names` does not scan.

4. Consequence. Under §17.5.1's conjunctive fold ("½ if any entry declines"), the `:2364` site declines for want of a row, so **`:375` stays ½ on all 93 move operations with M-SURF, M3, D7, D8 and D9 all taken.** The move-family residual is **eight**, not seven; §17.8.2 condition (1) fails on every one of the 93; §17.8.3's `321 → 0` is falsified; §17.0.3's "removes SIX … leaves SEVEN" is wrong by one; AC-17.5's "`:375` is asserted `SAFE` on the 93 `move_*` operations **by name**" is unsatisfiable; Q10's headline claim "`:375` discharged on all 321 operations" is unsatisfiable.

**Why a fixer is blocked.** T53's scope cell says M-SURF is the identical rule T49 closed "on the SELECTION side", asserting the selection half is done. It is not done for any method name that only ever appears at depth ≥ 2. A fixer implementing T53 and T54 exactly as written will regenerate the table, find `:375` still ½ on 93, and have to invent the remedy — including deciding whether the selection scan may read a field that does not exist until T54 lands, which reverses §17.11's stated "T53 must precede T54" attribution story.

**Minimal fix.** Either (a) add to T54 the extension of `collect_env_ref_method_names` to scan `caller_args_sites` as well as `caller_args`, state that the move family's `:375` is therefore **D8-dependent in both halves** (surface selection *and* argument map), re-argue §17.1.4's blast-radius box for the ~9 backend classes that gain a `drop_resource` row (R-CONST is still unaffected — `drop_resource` appears in no guard predicate — but `n_surface_rows` moves off 89 and the argument owes that), and have AC-17.4 assert `LiquidHandlerChatterboxBackend.drop_resource` present in `rows` **by name**; or (b) restate the residual as **eight**, keep `:375` in it, and restate §17.8.3 as `321 → 93` with the reason named.

---

## R2-C2 — BLOCKER — §17.4.2's absence rule, third clause, vs §17.8.3

**Claim challenged.** "At the pin `_resource_pickup` **is** a property, and it survives precisely because its setter is the single statement `self._resource_pickups[0] = value`" (§17.4.2), and §17.8.3's `:2070`/`:2120`/`:2147` → `SAFE` on 93.

**Evidence.** §17.4.2's absence rule declares an anchor candidate absent when any of three things holds, the third being "**when the qualname is defined at more than one lineno**", and says the rule is "inherited from §16.3's C15". The shipped C15 rule is `_backend_surface_row_absent` (`plr-sema/src/plr_sema/derive/receiver_state.py:1424-1454`), whose own docstring is explicit about what clause 3 is for:

```
3. the same ``(module, qualname)`` is defined at more than one lineno
   (``n_definitions_at_qualname > 1`` …)
```
> "a getter/setter PAIR sharing a qualname is caught by (3)"  — `receiver_state.py:1434-1435`

`LiquidHandler._resource_pickup` is exactly a getter/setter pair: `def _resource_pickup(self)` at `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:179` and `def _resource_pickup(self, value)` at `:184`, two definitions of one qualname. Read literally, §17.4.2's third clause makes the increment's only anchor **absent**, the typestate declines, `:2070`/`:2120`/`:2147` stay ½, and gate condition (1) fails on all 93 — the *identical* internal contradiction round 1's C4 found, in the section C4 forced to be re-derived, one clause over.

Note that §17.4.2 visibly *narrows* the inherited clause 1 (from "`node.decorator_list` is non-empty" to "a property whose setter body is not a single assignment statement") and argues that narrowing. It performs no such narrowing on clause 3 and does not mention it.

**Why a fixer is blocked.** The two readings give opposite gate outcomes and the spec asserts the favourable one without licensing it. There is also a latent definitional ambiguity a fixer cannot resolve: clause 1 is about `F`-as-property (a function), clause 2 about `F`-as-attribute (assignments), clause 3 about "the qualname" of an unspecified thing.

**Minimal fix.** State clause 3 as "when `<Class>.<F>` is defined at more than one lineno **other than as a getter/setter pair of one `property`**", cite `receiver_state.py:1438-1440` and its docstring as the rule being deliberately narrowed, and add the narrowing to AC-17.3's absence fixtures (a three-definition qualname asserted absent, beside the two-definition property pair asserted present).

---

## R2-C3 — BLOCKER — §17.4.0's "route to a verdict", AC-17.3, T52

**Claim challenged.** "The state reaches a verdict through the SAME mechanism increment 1's typestate uses … `evaluate_predicate` is not touched by the typestate at all"; "**`_finding_for_atom`'s ½ branch must carry `guard_env_dependent` for this anchor** … That is the ONE line of that function this increment parametrises". AC-17.3 asserts `:2070`/`:2120`/`:2147` "decided through `evaluate_call`'s `consumed`-index replacement".

**Evidence.** The two halves §17.4.0 combines are mutually exclusive in the shipped code (`plr-sema/src/plr_sema/check/tipstate.py`, read `:360-653`):

- `consumed` indices are recorded in exactly one place, the **own-guards** loop, and that loop is inside `if channels is not None:` (`:570-582`). Its matcher is `parse_own_atom`, whose `base_ok` requires the receiver expression to be `self.<channel_attr>[<name>]` (`_is_channel_subscript`, `:404-411`; `parse_own_atom`, `:414-425`). `self._resource_pickup is None` does not have that shape.
- The bare-`self` shape §17.4.0 step 2 names — `parse_bridge_atom` (`:428-439`) — is used only in the **channel_guards** loop (`:598-616`), which iterates a *different* wire field (`contract.get("channel_guards", ())`) and records **no** `consumed` index at all (the docstring at `check/__init__.py:506-509` says so: "every `channel_guards` entry that parsed is an ADDITIVE finding … no old finding to replace").
- `channels_for_call` is the operation's tip-channel set. `move_lid`/`move_plate`/`move_resource` declare no `use_channels` parameter, so `channels` is `None` and the own-guards loop does not run for a single move operation. The shipped docstring states the consequence: "An INEXACT channel set … means the guard is not tip-state-interpretable AT ALL — it falls through to the old `guard_predicate_unparsed` finding, UNCHANGED" (`tipstate.py:553-559`).
- `atom_truth(atom, s)` is typed over `TipState` and its body compares `s is TipState.HAS_TIP` / `TipState.NO_TIP` (`:442-452`); `_finding_for_atom(…, s: TipState)` calls it (`:460`); and `s` is produced by `fold_channels(channels, lambda c: walk.state(call.receiver, c))` (`:571`) — a per-channel fold over a `TipWalk`. §17.6's own table concedes "this anchor has no channels".

So there is no shipped path that (i) matches a bare-`self` `x is None` atom against an entry of `contract["guards"]`, (ii) outside the `channels is not None` gate, (iii) against a non-channel state, and (iv) records a `consumed` index. All four are required. The favourable facts §17.4.0 rests on are true — I verified `_finding_for_atom` takes no `depth` and never calls `guard_is_unconditional` (`:455-472`, `WILL_FAIL` at `:464-467`), and `_findings_for_guards` skips *any* consumed index regardless of reason (`plr-sema/src/plr_sema/check/__init__.py:451-453`, `if idx in consumed: continue`) — but they do not add up to "the route already exists".

**Why a fixer is blocked.** T52 is already flagged as "the largest and riskiest row" at ~300 LOC, and its scope cell describes the route as pre-existing machinery to reuse. A fixer must instead invent: where the new per-call loop lives; what (if anything) gates it; the atom matcher for a bare-`self` anchor field over `contract["guards"]`; the state source (§17.4.3 condition 4 says "in `TipWalk`'s own manner" — a *new* walk object, unnamed and unpriced); and whether `atom_truth`/`_finding_for_atom` are generalised over two lattices or duplicated. Each is a design decision, and the last one determines whether `_measure_hm25` gains one symbol or three — which is exactly T52's STOP contingency.

**Minimal fix.** Replace §17.4.0's four numbered steps with a normative statement of the new evaluator entry point: its name, its position relative to `evaluate_call`'s two existing loops, an explicit "the `channels is not None` gate does NOT apply to a channel-free anchor", the new matcher's name and shape test, the new walk's name, and which of `atom_truth`/`_finding_for_atom` are parametrised vs. duplicated. Re-price T52 and re-state §17.7 unit 12's scope so it covers whatever new symbols this adds.

---

## R2-C4 — MAJOR — §17.9's `p3a_pickup_already_held` is not constructible with the shipped mutator API, by §17.9's own argument

**Claim challenged.** "`plr-sema/eval/predicate_mutants.py` is extended by **`p3a_pickup_already_held`**: mutate a planned program so a second `pick_up_resource` is issued while a resource is still held … the floor is **`achieved == attempted` with `attempted ≥ 60`**", and AC-17.3's "`p3a` is published … its denominator is asserted to be 93 and not 31".

**Evidence.** Every mutator in that module is a kwargs transform:

```python
_MUTATORS: dict[str, Callable[[dict[str, Any]], bool]] = { … }   # plr-sema/eval/predicate_mutants.py:138-142
```
`make_p1a_duplicate_use_channels(kwargs)` `:106`, `make_p1b_short_offsets(kwargs)` `:113`, `make_p1c_non_tipspot_element(kwargs)` `:127`, `make_p2a_channel_out_of_range(kwargs, num_channels)` `:145`. The driver "Mutates the FIRST `_TARGET_CALL` … call's grounded `PlanResult.kwargs` in place" (`:173-174`). Issuing a *second* `pick_up_resource` is a program-structure mutation, which no `Callable[[dict], bool]` can express — and no kwarg of a `move_*` call can leave `self._resource_pickup` non-`None` at entry.

This is the same fact §17.9 uses two paragraphs later to refuse a `:2055` mutator: "the mutator API mutates kwargs". The section therefore refuses one mutator and asks for another on contradictory premises. (Program-level mutation does exist elsewhere — `tip_mutants.make_m1_remove_pickup` is referenced at `predicate_mutants.py:116-117` — so the fix is reachable, but it is in a different module with a different API, and T55's scope cell names only "`predicate_mutants.py` extended with `p3a_pickup_already_held`".)

**Why a fixer is blocked.** T55 must produce `achieved == attempted` with `attempted ≥ 60`. With the API as shipped, `attempted` is 0 and the floor is unreachable — increment 6 §15.16.3's "a class which can only ever report 0 is a publication and not a gate", which §17.9 itself cites.

**Minimal fix.** Name the harness the mutator lives in and the API it uses (a program-level insertion in `tip_mutants.py`'s style, or a stated extension to `predicate_mutants.py`'s driver), price it in T55, and re-state the `:2055` non-constructibility argument on a ground that does not also kill p3a (the backend-class property, not the API's shape). If neither is affordable, withdraw p3a and say the typestate's `T` direction is untested this increment.

---

## R2-C5 — MAJOR — §17.8.3's `n_findings` figure is wrong, and AC-17.6 hard-codes it

**Claim challenged.** "**`n_findings`.** 3,903 → **3,717**" (§17.8.3); AC-17.6: "`n_findings` is published against **3,717**".

**Evidence.** In this instrument a *decided* guard is not a finding. `n_findings_by_reason` partitions `n_findings_total` exactly: 2884 + 495 + 194 + 186 + 144 = 3903 = `n_findings_total` (`outputs/plr-sema/unknown_ledger_260909_final.json:29-38`). And the two counts are disjoint per site: the `:375` cluster carries `n_findings: 321` (`:45`) while `n_findings_decided_by_site[":375"] = 223` (`oracle_replay.json:117`) and `n_check_args_decided.attempted[":375"] = 544` (`:180`) — 321 + 223 = 544.

So the 894 findings §17.8.3 moves into `n_findings_decided` (+372 +321 +201, giving 2,817 → 3,711 ✓) must also **leave** `n_findings`, exactly as the same bullet's `guard_env_dependent` 2,884 → 1,990 (−372 −321 −201) already concedes. Correct arithmetic: 3,903 − 894 − 186 = **2,823**. The document subtracted only M-INH's 186.

**Why a fixer is blocked.** AC-17.6 asserts a published number against a figure that cannot be met by a fully successful implementation; T55 would record a spurious divergence in §17.14 against its own success.

**Minimal fix.** `n_findings` 3,903 → **2,823** in §17.8.3 and AC-17.6. (Cross-check: 3,711 decided + 2,823 unknown = 6,534 = 6,720 − 186 ✓.)

---

## R2-C6 — MAJOR — §17.4.3 condition 2's terminator test has an unsound direction, and it is not among the two §17.15 names

**Claim challenged.** "decided by the pure AST shape test `isinstance(handler.body[-1], ast.Raise)`. A handler whose last statement is a `raise` contributes **no** state to positions after the `try`."

**Evidence.** §17.15 owed item (3) names two shapes it says the test "gets wrong in opposite directions": a `raise` inside a nested `try`, and a `raise` that is not the last statement but is last on every path. Both err **safe** (they widen). The shape that errs **unsafe** is not named: a handler whose last statement *is* an `ast.Raise` but which contains an earlier `ast.Return` (or `Break`/`Continue` in a loop). Then execution can leave the handler normally, carrying the rolled-back state, and positions after the `try` — including, for this anchor, a later delegate's guard — read `HELD` when the field is `None`. That is a false `SAFE`, the one failure mode §17.1.5 says the project exists to prevent.

At the pin the test is decidable and correct: `pick_up_resource`'s handler is exactly `[self._resource_pickup = None, raise e]` (`liquid_handler.py:2090-2092`) and it is the only in-handler assignment to the anchor in the move closure. But P5/P6 selection is published **whole-surface** (§17.8.1 block 3), so the rule ships against handlers nobody has enumerated.

**Minimal fix.** One clause: "…and the handler body contains no `ast.Return`, `ast.Break` or `ast.Continue` at any depth; otherwise it widens." Add the negative fixture to AC-17.3's condition-2 pair.

---

## R2-C7 — MAJOR — semantic AC↔task-row orphans: three ACs are gated on rows whose gate cells cannot test them

The mechanical crossref lint reads column 4 only (`plr-sema/scripts/check_spec_crossrefs.py:139-156`, per §17.11's own box) and each of AC-17.1…AC-17.9 is gated exactly once — that half is clean. The semantic half is not:

- **AC-17.4 → T53.** AC-17.4 asserts "`:375` is asserted `SAFE` on the 148 `aspirate`/`dispense`/`drop_tips` operations and `:383` likewise". T53's gate cell is `pytest test_derive.py`, `test_check_graph.py`, `test_cache.py` — no ledger, no replay, no corpus. A per-operation count over the frozen benchmark is not reachable from those three files, and T55's ACs (17.6–17.8) never assert the 148.
- **AC-17.5 → T54.** Same defect for "`:375` is asserted `SAFE` on the 93 `move_*` operations **by name**, and `:383` asserted **still ½** on all 93".
- **AC-17.3 → T52.** Asserts "`p3a` is published as `achieved/attempted` … with the floor of §17.9" and "its denominator is asserted to be 93". T52 does not touch `predicate_mutants.py` and its gate cell does not run it; T55 does both.

**Why a fixer is blocked.** A row cannot be closed against a criterion its own gate cannot evaluate, and §17.11's box explicitly makes a declined decision withdraw the criterion *with* its row — which only works if the row can satisfy it.

**Minimal fix.** Move the benchmark-level clauses of AC-17.4/AC-17.5 into AC-17.8 (T55) as named sub-assertions, or add the tier-1 replay + ledger step to T53's and T54's gate cells; move AC-17.3's p3a clause to AC-17.7 while keeping the withdraw-with-T52 linkage stated in prose.

---

## R2-C8 — MINOR — §17.8.1 block (4) does not publish the counter that would falsify R2-C1 cheaply

Block (4) publishes `n_entries_with_backend_surface` before/after, the newly-attached **contract keys**, and R-CONST's `n_resolved_by_rule`. None of those moves when a **row** is missing: `n_surface_candidates: 160 / n_surface_absent_by_c15: 71 / n_surface_rows: 89` (`derived_contracts.json:3-5`) and the `rows` key list are the quantities that decide whether `:375` can clear, and they are unpublished. §17.8.2's failure mode 6 would therefore surface R2-C1 only at T55, after T50/T52/T54 have all landed.

**Fix.** Block (4) publishes `n_surface_candidates`, `n_surface_absent_by_c15`, `n_surface_rows` and the sorted `rows` key list, before and after; AC-17.4 asserts `LiquidHandlerChatterboxBackend.{pick_up_resource, drop_resource}` both present.

---

## R2-C9 — MINOR — §17.1.4 quotes a stale code comment as a fact about the pin, and the artifact that contradicts it was declined

§17.1.4: "its own comment records that this is *'only 10 of 4,770 entries … at this pin'*" (`derive/__main__.py:326-356` — the quote is verbatim at `:336-337`). The shipped table carries **five**: `backend_surface` occurs at `derived_contracts.json:2` (top-level) and at `:103528`, `:109799`, `:111528`, `:113040`, `:117033`, whose owning entries are `LiquidHandler.consolidate_tip_inventory`, `LiquidHandler.move_tips`, `LiquidHandler.pick_up_tips`, `LiquidHandler.probe_tip_presence_via_pickup`, `LiquidHandler.use_tips`.

The *mechanism* §17.1.4 diagnoses is confirmed by this list — only closures reaching `pick_up_tips`'s `can_pick_up_tip` guard are attached, and of the five only `pick_up_tips` is executed (`oracle_replay.json:79-90` lists the ten executed methods; the other four are absent), so "the 223 that flipped are `pick_up_tips`" is right and closes exactly (`scope_verdict_by_method.pick_up_tips.n_ops: 223`, `oracle_replay.json:192`; 223 + 321 = 544 ✓). But the frontmatter lists `derived_contracts.json` under "NOT read this pass", and reading it would have both confirmed the diagnosis and surfaced R2-C1.

**Fix.** Replace the code-comment quote with the artifact's own numbers and the five-entry list, and remove `derived_contracts.json` from the not-read list.

---

## R2-C10 — MINOR — §17.8.3's `:383` bullet omits a D8 dependency §17.8.2 states correctly

§17.8.3: "**`:383`.** 321 → **120**. Clearing: the 148, plus `transfer` 19 and `discard_tips` 34, all through the **shipped** `has_var_keyword` route once M-SURF attaches the surface — 201 operations." The *route* is shipped, but `_check_args_surface_row` needs `m` from `caller_args` (`predicate.py:1246-1248`), and `transfer`/`discard_tips` reach `_check_args` at depth ≥ 2, so 53 of the 201 need M3/D8. §17.8.2's hook table gets this right ("**M-SURF still lands and still clears `:375`/`:383` on the 148**"); §17.8.3's bullet reads as if all 201 were hook-free, and Q10's "under a total decline of D7, D8 and D9 it may still claim `:375` and `:383` on the 148" is the correct number.

**Fix.** "…the 148 on M-SURF alone; `transfer` 19 and `discard_tips` 34 additionally require M3 (D8)."

---

## R2-C11 — MINOR — §17.5.1's clause accounting misdescribes `compute_caller_args`

"`compute_caller_args` today refuses a `(K, D)` pair outright on two grounds this increment relaxes, and on four it does not touch (`plr-sema/src/plr_sema/derive/bindings.py:931-941`)." Clause 6 (`depth == 1`) is not in that function at all — its own docstring says so: "Clause 6 (depth == 1 only) is NOT this function's job: it has no `depth` parameter at all" (`bindings.py:944-948`); the gate is in `derive_contract` (`derive/__init__.py:640`). And clause 4 is three separate refusals (`bindings.py:969-975`), of which §17.5.2's derivation uses one. The cited range `:931-941` is the docstring, not the refusals.

**Fix.** Say "clauses 1/2 (single call site, `bindings.py:966-968`) and clause 6 (`depth == 1`, enforced in `derive_contract`, `derive/__init__.py:640`)"; cite `:969-975` for clause 4's three sub-refusals.

*(For the record, §17.5.2's own derivation is stronger than it claims and I verified it end to end: `:2079` is `self._check_args(self.backend.pick_up_resource, backend_kwargs, default={"pickup"}, strictness=get_strictness())` (`liquid_handler.py:2079-2081`); `pick_up_resource`'s `backend_kwargs` is bound only through `await self.pick_up_resource(..., **pickup_kwargs)` (`:2353-2359`) off a `DictComp` (`:2351`); and that call is refused **twice** — `any(kw.arg is None for kw in call.keywords)` at `bindings.py:971-972`, and `d_args.kwarg is not None` at `:974-975`, since `pick_up_resource` declares `**backend_kwargs` (`:2044`). D10 = NO is correctly derived.)*

---

## R2-C12 — MINOR — the "second pass over `_walk_closure`'s already-visited node set" is not available as stated

§17.5.1: "It is computed in a **second pass over `_walk_closure`'s already-visited node set**, with each caller record's own `K` taken from the SAME `function_index` `derive_contract` already holds … the parentage C2 asked for is recovered afterwards, from data the walk already produced."

`seen` is a generator-local set inside `_walk_closure` and is neither returned nor exposed (`derive/__init__.py:445-459`), and `derive_contract` constructs and appends each `InlinedGuard` **inside** the walk loop (`:665-681`) — a `@dataclass(frozen=True, slots=True)` (`:462`). So a genuine second pass requires either buffering `(rec, key, depth)` and deferring guard construction to after the walk, or rebuilding every guard via `dataclasses.replace`. Mechanical, but it is a restructure of the one function the increment's three other rows also modify, and T54's ~300 LOC is stated as covering "a second traversal pass, per-site caller resolution, a new wire field with its cache round trip, and two site-set fail-closed conditions" without it.

**Fix.** One sentence naming the shape: collect the walk's `(rec, key, depth)` triples into a list during the existing pass, resolve the per-delegate site sets from that list, and emit guards in a second loop.

---

## R2-C13 — MINOR — §17.8.2's decision-hook table has no branch for D10 or D11 being approved

The table's column is headed "if declined", and the D10/D11 rows read "*taken as recommended* — no change; D10 is **NO** in this document's own text". A user who **approves** D10 or D11 finds no task row, no LOC, no gate change and no AC — and §17.5.2 prices D10 at four productions plus four hops, i.e. not deliverable in this increment. Read against the other five rows the cell is also ambiguous: "if declined → no change" invites the reading that declining D10 costs nothing, when declining a NO recommendation means taking it.

**Fix.** Re-head those two rows explicitly ("if APPROVED: the increment cannot deliver it; it returns to increment 9's scope and no row lands here"), matching §17.12's own text.

---

## R2-C14 — MINOR — §17.16 cites task ids that did not exist in the document round 1 reviewed, without saying rows were renumbered

M3 was T53 in spec_version 1 (the challenger's C2 and C13 both cite "T53 (line 1090)"; the defender writes "resizing T53 beyond ~200 LOC"). In spec_version 2 M3 is **T54** and M-SURF is the new T53. §17.16's C2 row reads "T54 re-sized ~200 → ~300" and C13's reads "T54", with no note that the numbering shifted. Every other row's ids (T50, T51, T52) are stable, which makes the two shifted ones read as if round 1 had reviewed them.

**Fix.** One line under the disposition table: "M3 moved from spec_version 1's T53 to T54; T53 is now M-SURF, which spec_version 1 did not have."

---

## Round-1 dispositions: which are genuinely closed

**Genuinely closed — the text contains the claimed change, and I re-verified the load-bearing source fact where one was cited: C1, C2, C3, C5, C7, C8, C9, C11, C12, C13, C14, C15, C16, C17, C18, C19, C20.** Spot checks I ran rather than assumed:

- **C8** — the corrected ground holds. Neither `Resource._state_updated` (`resource.py:932-934`), nor `Resource.serialize_state` (`:838-849`), nor `LiquidHandler.serialize_state` (`liquid_handler.py:214-237`) contains a `raise` or `assert`. "Zero guards" ✓.
- **C9** — `subclass_closure_from_bases`'s consumer map is genuinely unbuilt; `build_plr_class_index` keys bare (`receiver_state.py:1255-1268`) ✓.
- **C14/C15** — `_measure_hm25` returns `len(shape_matchers) + len(productions)` = 7 + 3 = 10 (`_hand_maintained.py:414-434`); its probes import `_resolve_env_ref`, `atom_truth`, `_match_alpha/_match_beta`, `EnvRef`, `Zip`, `_CMP_OPS` and five `receiver_state` symbols — **`evaluate_predicate` is not among them** (`:364-377`), and `_typestate_anchor` **is** in `shape_matchers` (`:415`). So unit 11 is genuinely unridden and unit 12 genuinely needs a distinct symbol. D7's arithmetic checks: 9 matchers + 3 productions = 12 = the requested `declared`, with `BUDGET_CAP = 25` (`:49`) and HM-25 `declared = 10` (`:1053`) unchanged otherwise. **Nothing in spec_version 2 requires a 27th row** that I could find: block (10)'s additive `GuardResult` boolean, M-SURF's boolean, M3's traversal and the base-name extractor are all code, not hand-maintained patterns. The one residual risk is R2-C3's unnamed new-lattice symbols, which T52's own STOP contingency covers.
- **C20** — `_entry_satisfies_uncond` begins at `predicate.py:1047` and `guard_is_unconditional` at `:1060`; the corrected label is right.
- **C12** — `scope_excludes` runs at `predicate.py:1443` and the site rule at `:1446-1447`; the "differs in kind" retraction is correct.
- **C19** — `n_row_id_collisions: 12` at `unknown_ledger_260909_final.json:2173` with `collision_ops` opening at `:2174`; provenance correctly named.

**Both REBUTs are legitimate — I checked them independently rather than assuming.**
- **C6.** `plr-sema/src/plr_sema/check/tipstate.py` reaches a verdict entirely through `_parse_atom`/`_null_check`/`atom_truth`/`_finding_for_atom` (`:372-472`) and never calls `_resolve_env_ref` or `_eval_is`. No fifth `EnvRef` path shape and no broadened `Is` rule is needed. Rebuttal sound; but §17.4.0's *conclusion* overreaches — see R2-C3.
- **C10.** `_finding_for_atom` (`:455-472`) takes no `depth` argument, never calls `guard_is_unconditional`, and returns `Verdict.WILL_FAIL` on `truth == "T"` at `:464-467`; `_findings_for_guards` skips consumed indices unconditionally (`check/__init__.py:451-453`). The 31-operation denominator C10 asked for would indeed have been wrong. Rebuttal sound; but the denominator is moot until R2-C4 is answered.

**Closed in text, reopened in substance: C4 and C21.** C4's remedy landed (the terminator test is in §17.4.3) but the same *class* of internal contradiction reappears one clause over in §17.4.2 (R2-C2), and the replacement rule ships an unfenced unsound direction (R2-C6). C21's remedy landed (the gate is re-derived, the residual is seven, failure modes 5/6 and blocks 4/10 are added) but its finding — "gate condition (1) is predicted to fail on all 93" — is re-established by R2-C1 and R2-C2, each independently sufficient.

**Falsely claimed closed: none.** Every disposition in §17.16 names a change the current text contains, no concession is recorded as a rebuttal, and the two rebuttals are factually correct. This is a materially more honest remediation than round 1's target, and §17.15's self-nominated attack list is what made R2-C1 findable.

One favourable finding worth recording against §17.15's owed item (2): it is answerable from the instrument the document already cites, and the answer is positive. The `unresolved_delegate` cluster is `n_findings: 186 / n_ops_blocked: 93`, `condition: "_state_updated"`, `per_method` 31/31/31 (`unknown_ledger_260909_final.json:811-822`) — exactly two unresolved calls in the entire move closure, both `_state_updated`. And the bodies M-INH newly admits add none: `LiquidHandler.serialize_state`'s calls are `tracker.serialize()` (an `ast.Attribute` non-`self` receiver → `dropped_calls`, `scripts/survey_plr_preconditions.py:268-288`), `serialize(pickup)` (an `ast.Name` neither module-level nor validation-looking → recorded nowhere, `:290-299`), and `super().serialize_state()` (`target.value` is an `ast.Call`, not an `ast.Name`, so it falls to the `dropped_calls` branch). So §17.5.1's first site-set condition is satisfiable post-M-INH, and the hedge "this document cannot measure either" can be replaced with the measurement.

---

## Verdict

**`not_ready`.**

Confidence **high** on R2-C1, R2-C2, R2-C3, R2-C4, R2-C5 (each is a shipped artifact, a shipped signature, or an arithmetic identity read at the cited lines this pass); **high** on R2-C7 through R2-C14; **medium** on R2-C6 (the unsound shape is certain, its presence anywhere in PLR's whole surface is not measurable from here).

**Shortest path to `ready`,** in the order a fixer needs them:

1. **R2-C1.** Extend the surface **selection** half, not only the attachment half — `collect_env_ref_method_names` must scan `caller_args_sites` — and re-state the move family's `:375` as D8-dependent in both halves; or restate the residual as **eight** and `:375` as `321 → 93`. Update §17.0.3, §17.1's table, §17.8.2(1), §17.8.3, §17.8.4, Q9, Q10, AC-17.4, AC-17.5, the frontmatter. Add block (4)'s row-level counters (R2-C8) and the `drop_resource` row assertion.
2. **R2-C2.** Narrow §17.4.2's third absence clause for the property getter/setter pair, against `receiver_state.py:1438-1440`, and fixture both directions.
3. **R2-C3.** Specify the typestate's new evaluator entry point (loop position, gate, matcher, walk, lattice generalisation) and re-price T52 and §17.7 unit 12.
4. **R2-C4.** Name p3a's harness and API, or withdraw the class with its reason; repair the `:2055` argument so it does not contradict the ask.
5. **R2-C5.** `n_findings` 3,717 → **2,823** in §17.8.3 and AC-17.6.
6. **R2-C6.** Add the `Return`/`Break`/`Continue` clause to widening condition 2.
7. **R2-C7.** Re-home the three benchmark-level AC clauses onto T55, or add a replay step to T53/T54's gate cells.

Items 8–14 (R2-C9…R2-C14) are text-level and can land in the same pass.

**What must not be lost in revision.** The instrument's facts are exactly as cited and I re-verified every range I used: the identical thirteen-entry residual across all three methods (`oracle_replay.json:241-261`), the 223/321 split closing to 544, `n_check_args_decided` 223/223 against `attempted` 544, `n_resolved_by_rule` R-CONST 223, the 186/93 `unresolved_delegate` cluster, `gate.go true` with 216. §17.0.1's identical-residual observation is real and is the right foundation for a structural gate. §17.1.4's *mechanism* — the attachment filter, one guard, five entries — is correct and is a genuine advance over spec_version 1; it is the fix's reach, not the diagnosis, that is wrong. D10's refusal is correctly derived at the pin. D11's repaired argument holds (`_eval_is_instance` returns `True` or `None`, never `False`, `predicate.py:575-594`, and all six sites do sit inside `isinstance(destination, ...)` arms — `liquid_handler.py:2203-2214`, `:2224-2233`, `:2282-2290`, read in full). D7's two units are honestly argued and mechanically checkable. And §17.15's decision to nominate its own three weakest claims is what made the blocker findable in one pass.
