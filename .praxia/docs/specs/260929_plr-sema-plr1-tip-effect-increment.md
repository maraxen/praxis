---
title: 'plr-sema PLR 1.0 tip-effect increment (backlog #5622)'
description: Restore derived tip effects under PLR 1.0's rewritten TipTracker (backing-field alias, arg-classified helper following, constructor seeding, effects_unresolved -> widen), decide _check_tip_racks_available via a closed observation + D6 row with a move-family conjunct, plus cross-pin drift tests
status: draft
task_id: 260929_plr-1.0-migration
date: '260929'
backlog_ids: '5622'
adversarial_review: ''
---
# §18 — the PLR 1.0 tip-effect increment (backlog #5622)

> **This document amends `260901_plr-sema-pre-corpus-spec.md` by reference** and adds §18 to its
> numbering, as increments 7 and 8 added §16 and §17. It edits text in three earlier documents, each
> named where it happens and each landed by a task row. In increment 1 it amends §10.2.4's P4 rule
> (the "both kinds → no effect" clause, §18.4.4), §10.4's E2 (which now widens when depth-0 and deep
> effects coexist, §18.4.4) and the §10.6.3 assumption table (one new row, §18.5.5). In increment 7
> it amends §16.2.1's closed observation record (one new field) and §16.2.2's third failure-mode test
> (a frame-condition clause), both in §18.5.2. Increment
> 5's V5 rule, including its 260929 amendment, is **unchanged** (L5). `schema_version` stays 1,
> `REASON_VOCABULARY` gets no new member, and no new registry row is added (L0).
>
> **Status: revision r3 — adversarial review converged** (rounds 1–3 REVISE, round 4 ACCEPT: ready
> for implementation; the revision log is §18.17). Final: the owner ruled on OI-21 and OI-4 on 260929
> (§18.17, "Final (owner rulings)"). Where this document asserts a number it names the file it
> was read from. Where a claim is reasoned from reading source rather than measured, it says
> *(reasoned)*. The recon's *(exploratory)* numbers are **not** evidence here and are quoted only as
> labelled expectations. The owner's locked decisions L0–L7 (§18.2) are inputs, not open questions.

## 18.0 What this increment is, in one paragraph

PLR 1.0.0b1 rewrote `TipTracker`. Its state now lives behind two read-only properties and two private
helpers. The analyzer's P4 effect scan (increment 1 §10.2.4) looks only for direct assignments to
the state fields, so at 1.0 it finds none. The consequences are that `entry_reset` disappears,
`pick_up_tips`/`drop_tips` lose their `channel_effect`, and every tip-state verdict decays to
`UNKNOWN`. Separately, a new PLR guard, `_check_tip_racks_available`, now runs inside every tip
pickup and drop, and its predicate is unparseable. The pre-registered characterisation
run `fd63e9cd` measured the result: still sound, but **0** operations at `scope_verdict == SAFE`,
against **216** at the dd79c4c89 pin. This increment adds five **derived** rules (R-A to R-E) that
restore the effects under the new tracker shape. It also fixes one old unsoundness instead of copying
it. Any tip write whose value might be `None` (a call result, a subscript, an attribute read and so on)
is now classed `UNRESOLVED`, and a bridged method with such a write widens rather than asserting
`HAS_TIP` (L1). `load_state` is the instance at both pins. At the old pin it writes
`cast(…, deserialize(…))`; at 1.0 it writes an `IfExp` with a `None` arm. Both are `UNRESOLVED`, so
the fix does not depend on the shape PLR happened to choose. Finally it decides
`:338` with one closed observation field and one fourth D6 site rule, which returns `False` only and
declines whenever a move-family call could have changed the rack topology (L3).

| axis | at `a176bac7` (PLR 1.0.0b1, V5 amendment in) | this increment |
|---|---|---|
| `receiver_state["LiquidHandler"].effects` | `{}` | `{add_tip: HAS_TIP, clear: NO_TIP, remove_tip: NO_TIP}` *(expected, §18.4.9)* |
| `entry_reset` | absent | `{"method": "setup", "post": "no_tip"}` *(expected)* |
| `channel_effect` of `pick_up_tips` / `drop_tips` / `load_state` | `None` / `None` / `None` | `HAS_TIP` / `NO_TIP` / `widen` |
| receivers in `receiver_state` | `LiquidHandler`, `LiquidHandlerBackend`, `TipTracker` (spurious) | `LiquidHandler`, `LiquidHandlerBackend` |
| `:338` (`_check_tip_racks_available`) | `guard_predicate_unparsed` on every op | `SAFE` under observation + stable topology; otherwise unchanged |
| observation record fields | 5 | 6 (`tip_racks_available`) |
| `D6_SITE_RULES` / HM-26 `declared` | 3 / 3 | 4 / 4 |
| HM-25 `declared` | 12 | 13 (one collective unit, §18.7 — see open issue OI-4) |
| `live_rows()` / `BUDGET_CAP` | 25 / 25 | 25 / 25 — **no new row** |
| `REASON_VOCABULARY`, wire `schema_version` | unchanged | unchanged |

---

## 18.1 The problem, measured

**The instrument.** The bathos run `fd63e9cd` (lock file
`plr-sema/eval/plr10_characterize.bth.fd63e9cd-4310-435b-a5ba-08c588d59a73.bth.lock.toml`) was
pre-registered by `plr-sema/eval/plr10_characterize.bth.toml` and ran `plr-sema/eval/plr10_characterize.py`.
That script has two arms over the frozen tier-1 benchmark. The `real` arm is the shipped analyzer. The
`all_safe` arm is a negative control that forces every static verdict to `SAFE`. The run's result
file is `outputs/plr-sema/plr10_char_260929/result.json`, and its sidecar outcome was **pass**. These
are its fields, verbatim:

| field | value | meaning |
|---|---|---|
| `control_fires` | `true` | the `all_safe` mutant was caught: `all_safe_unsound` 7 ≥ `runtime_raised_ops_all_safe_arm` 7 |
| `real_rows_executed` / `real_rows_setup_error` | 343 / 0 | same denominator as every prior increment |
| `real_operations_executed` | 548 | |
| `real_unsound` / `real_unsound_scoped` | 0 / 0 | sound |
| `real_totality_violations` / `real_check_graph_exceptions` | 0 / 0 | total |
| `real_n_operations_scope_verdict_safe` | **0** | precision floor at 1.0 |
| `real_unknown_rate` | 1.0 | |

**The comparison baseline.** At dd79c4c89 the same 343-row benchmark gave
`n_operations_scope_verdict_safe` **216**, and all 216 are `pick_up_tips` (`n_ops` 223,
`n_scope_verdict_safe` 216). The source is `summary_flat` and `scope_verdict_by_method.pick_up_tips` in
`outputs/plr-sema/unknown_ledger_260911_volwire.oracle_replay.json`. The characterisation sidecar names
this ledger as the reproduction target. No other method had a scope-`SAFE` operation at the old pin,
so the whole headline is one method.

**Where the 216 went.** In the 1.0 `real` report (`outputs/plr-sema/plr10_char_260929/real.oracle_replay.json`),
`scope_verdict_by_method.pick_up_tips.residual_site_sets` shows the same 216 operations blocked by
exactly three sites:

1. `legacy/liquid_handling/liquid_handler.py:338:_check_tip_racks_available` — the new PLR guard;
2. `legacy/liquid_handling/liquid_handler.py:758:LiquidHandler.pick_up_tips` — the own `HasTipError`
   guard `self.head[channel].has_tip`;
3. `legacy/tip_tracker.py:153:TipTracker.add_tip` — the bridged `HasTipError` guard.

The remaining 7 operations carry the same three sites plus `:720`. That is the `TypeError` guard
that also blocked those 7 at the old pin as `:498`. Sites 2 and 3 are `UNKNOWN` because there is no
`entry_reset`, so the channel state at the first pickup is `TOP`; the same report shows
`channel_state_unknown` at 644 findings. Site 1 is `UNKNOWN` because its predicate is `Not(Opaque(…))`.
The `guard_predicate_unparsed` count is 783 against 495 at the old pin. The difference of 288 equals
the 223 + 31 + 34 `pick_up_tips`/`drop_tips`/`discard_tips` operations that inline `:338` *(reasoned:
the arithmetic matches, per-finding attribution was not re-derived)*.

**Two root causes, both addressed here, and one already closed:**

- **RC-1 (effects).** Increment 1's P4 derivation finds no effects under the 1.0 `TipTracker`
  (§18.3). This removes `entry_reset`, the pickup/drop `channel_effect`s, and the `tip_dropping`
  family. It is fixed by §18.4.
- **RC-2 (`:338`).** A new guard whose condition the analyzer cannot evaluate. It is fixed by §18.5.
- **Closed, not reopened: the V5 hole.** RC-1 had also opened a false `SAFE` in the volume family. The
  260929 V5 amendment (commit `223d690d`, `reset_tip_cells`) closed it, and it stays as it is (L5,
  §18.6).

---

## 18.2 Locked decisions (owner, 260929) — inputs to this document

These decisions are recorded as given. Nothing here re-opens them. Where this document found a
consequence the owner may not have priced, it goes to §18.14 as an open issue. The decision itself is
not re-argued.

- **L0.** The fix is a spec increment made of **derived** rules, with **no new hand-maintained
  registry row**. The registry is full at 25/25 (`BUDGET_CAP` in
  `plr-sema/src/plr_sema/_hand_maintained.py:49`). Any count that must change is a ceiling change on an
  existing row, and must be justified in the text. This document makes two such changes: HM-26 3 → 4
  (§18.5.6) and HM-25 12 → 13 (§18.7).
- **L1 (`load_state`): FIX, not parity.** The derivation separates "untouched" from "touched but
  unresolved" and publishes an `effects_unresolved` set. A bridged method with an unresolved tip write
  maps to `channel_effect: "widen"`. It never maps to omission, because omission is a no-op in
  `tipstate` and a no-op there is unsound. `LiquidHandler.load_state` goes from `HAS_TIP` (old pin) to
  `widen`. Parity with the old pin is therefore **10 of 11 by design**. The 11 is the recon's
  exploratory count; the fixture generator of §18.8 establishes the real count.
- **L2 (spurious `receiver_state["TipTracker"]`).** Suppress it **structurally**, with receiver
  discovery rooted at machine-frontend attributes, and do not recurse into tracker classes' own
  annotated attributes. No name-exclusion list is allowed, and a test pins the derived receiver set.
  §18.4.7 is the rule.
- **L3 (`_check_tip_racks_available`).** The guard is decided by (a) one new closed observation key,
  meaning the harness asserts that every `TipRack` on the observed deck has
  `_available_for_tip_handling`, and (b) a 4th `D6_SITE_RULES` row keyed `(qualname, raises, condition)`.
  That row returns `False` only. It **declines** if any move-family call precedes the operation, and
  no `SAFE` rests on an assumption. §18.5 is the rule.
- **L4 (depth).** Helper following is **unbounded**, stopped only by a call-stack cycle guard. The
  artifact publishes the maximum depth reached.
- **L5.** The V5 amendment (`223d690d`, `reset_tip_cells`) is retained unchanged.
- **L6.** `upstream_nonlegacy` stays frozen at `3a50a567f` and is out of scope.
  `plr-sema/data/derived_contracts.upstream_nonlegacy.json` is **not** regenerated by any task here.
- **L7.** Effects and `entry_reset` land **atomically**, in one fixer task (T57).

---

## 18.3 Why the effects vanished — the 1.0 tracker, read

All of the following was read at the 1.0 pin (`786ac2c4e`) this session.

- The boolean view is unchanged. `has_tip` returns `self._pending_tip is not None`
  (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:105-108`), so P2's anchor still resolves to
  `(has_tip, _pending_tip, not_none)`. The shipped 1.0 artifact confirms it
  (`plr-sema/data/derived_contracts.json`, `receiver_state.LiquidHandler.bool_view`).
- `_pending_tip` is now a **property**, not a field (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:55-61`).
  It returns `self._carried` when the tracker has no holder, and the holder's tree child otherwise.
- `_tip` is now a property too (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:63-72`). Its
  getter returns `self._pending_tip` or `cast(Optional["Tip"], self._before)`, and its setter writes `_before`.
- State changes take two helper hops. `add_tip` calls `self._hold(tip)`, `remove_tip` calls
  `self._hold(None)`, `_hold` calls `self._put(tip)`, and `_put` finally writes
  `self._carried = tip` (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:74-96`, which covers
  both `_hold` and `_put`; the write is at `:86`).
- `__init__` seeds `self._carried: Optional["Tip"] = None` as an `ast.AnnAssign`
  (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:39-49`).
- No 1.0 method assigns `_pending_tip` or `_tip`, and no method's own body writes a state field.

**So P4 measures `{}` at 1.0.** `_effects` (`plr-sema/src/plr_sema/derive/receiver_state.py:903-925`)
scans only `ast.Assign` to `self.<F>` for `F` in `state_fields = ["_pending_tip", "_tip"]`, and only in the
method's own body. `_constructor_state` (`plr-sema/src/plr_sema/derive/receiver_state.py:1015-1055`)
therefore finds no state-field write in `__init__` and returns `None`. `_entry_reset`
(`plr-sema/src/plr_sema/derive/receiver_state.py:1058-1081`) then emits nothing, with ledger
`"absent"`. With `effects == {}`, the `effects.get(method)` lookup in `compute_channel_bridge`
(`plr-sema/src/plr_sema/derive/receiver_state.py:1483-1582`) never fires, so every `channel_effect` is `None`.

**LiquidHandler's side is unchanged in shape.** It still reaches the tracker through the bridge shape
`self.head[channel].<m>`. `pick_up_tips` calls `self.head[channel].add_tip(...)`
(`external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:761`); `drop_tips` calls
`self.head[channel].remove_tip()` (`external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:909`).
Both still end in a commit-or-rollback fold whose callee is a conditional expression (`:796`, `:948`).
The survey records no `dropped_calls` entry for that shape: no `self.head[channel].commit` or
`…rollback` string occurs in `training/verify/data/plr_preconditions.json`, which is stamped at
`786ac2c4e`. So neither `commit` nor `rollback` is bridged on `head` *(verified by absence)*. The 96-head
variants do call `self.head96[i].rollback`/`commit` as plain calls. The deterministic tie-break
(`"head" < "head96"`) makes `head` the channel attribute, so they are not bridged either, which is
unchanged from the old pin.

---

## 18.4 The derivation rules (normative)

### 18.4.1 Vocabulary

- `C` is the tracker class: a P2-anchored class that is the value of a receiver's P1a channel attribute.
- `S` is `state_fields(C)`. It is computed exactly as today, by `_state_fields_for_class`
  (`plr-sema/src/plr_sema/derive/receiver_state.py:862-881`). At 1.0, `S = {_pending_tip, _tip}`.
- `B` is the **backing-field set**, defined by R-A. At 1.0 it is expected to be `{_carried}`.
- `W = S ∪ B` is the **write-target set**. Only assignments to `self.<x>` with `x ∈ W` are tip writes.
- Every tip write, argument and local receives exactly one **class** from a closed four-element set:
  `NO_TIP`, `HAS_TIP`, `COPY` (the value is a read of the merged abstract cell itself) and `UNRESOLVED`.
- A method's **result** is computed by §18.4.3's fold. It is one of `NO_TIP`, `HAS_TIP`, `UNRESOLVED`
  or `UNTOUCHED`.

`COPY` is new. It replaces the old `_classify_write`'s `"ambiguous"`
(`plr-sema/src/plr_sema/derive/receiver_state.py:889-900`), with identical semantics under A-COMMIT: a
write of the cell to itself is the identity on the merged cell. That is §10.2.4's own reading of
`commit` ("under A-COMMIT a commit is a no-op on the abstraction"), stated once and named. It is
**not** a new assumption. See §18.4.3 for why this, and not the recon's "≥ 1 argument" filter, is
what keeps a zero-argument helper from poisoning its caller.

### 18.4.2 R-A — backing-field alias

For each `F ∈ S`, let `G_F` be `C`'s getter for `F`. That is the unique `FunctionDef` directly in `C`'s
body named `F` whose `decorator_list` contains the bare `Name("property")`.

> **Normative (plain field, r2, C11).** `F` counts as a **plain field** only if nothing in `C` or in `C`'s
> PLR base closure binds `F` at class level. "Binds at class level" covers:
>
> - a `FunctionDef` of any decoration (`@property`, `@functools.cached_property`, an `Attribute`
>   decorator such as `@x.setter`);
> - a class-body assignment `F = …`, including `F = property(get, set)`.
>
> A plain field contributes nothing to `B`, which is the old-pin case. An `F` bound at class level
> **without** a `property`-decorated getter in `C` is **neither** a plain field nor an R-A property.
> Examples are a class-body `property(...)` call, a `cached_property` or an inherited property. Every
> write to it is `UNRESOLVED` (M3), and it contributes nothing to `B`, which is fail-closed.
>
> **Cost: zero at both pins.** The 1.0 `S` members are `FunctionDef` properties in `TipTracker`'s own
> body. The old pin's (`pr159` `pylabrobot/resources/tip_tracker.py`, `__init__` at lines 39-46) are
> plain `self.x = …` fields with no class-level binding in the class or its base `SerializableMixin`
> *(reasoned from reading both files)*.

Walk every `ast.Return` inside `G_F`, descending into `If`/`Try`/`With` bodies but not into nested
`FunctionDef`/`Lambda`/`ClassDef`. Then apply these rules to each return value:

| return value's AST, exactly | contribution |
|---|---|
| `Attribute(value=Name("self"), attr=X)`, where `X` names **no** direct `FunctionDef`/`AsyncFunctionDef` of `C` (so it is neither a property nor a method; r1, m16) | `X` joins `B` |
| `Attribute(value=Name("self"), attr=P)`, where `P` **is** a property of `C` | recurse into `G_P`, with the property names already visited as the cycle guard (a revisit contributes nothing) |
| `Attribute(value=Name("self"), attr=M)`, where `M` names a non-property direct method of `C` | nothing (a bound method is not a tip) |
| anything else: a `Call` (including `cast(…, self.X)`), a non-`self` attribute (`holder.tip`), a `Name`, a `Constant` | nothing |

`B` is published sorted (§18.4.8). **At 1.0:** `_pending_tip` returns `self._carried`, which gives
`B ∋ _carried`. It also returns `holder.tip`, which contributes nothing. `_tip` returns
`self._pending_tip` (a property, so the rule recurses and again reaches `_carried`) and `cast(…, self._before)`,
which contributes nothing. **So `B = {_carried}` and `_before` is excluded.**

> **The `_before` exclusion rests on one syntactic accident, and this document says so.** `_before` is
> left out only because the 1.0 source wraps it in `cast(...)`. If PLR removed the `cast`, `_before`
> would join `B`, and the following would happen *(reasoned from §18.4.3's fold; corrected in r1, m1)*:
>
> - `commit`'s `self._before = _NOTHING_PENDING` would classify `UNRESOLVED`. `_NOTHING_PENDING` is a
>   module global, so it is a `Name` bound nowhere in the method.
> - `add_tip` and `remove_tip` **both** follow `self.commit()`, so both would become `UNRESOLVED`.
> - Both `pick_up_tips` and `drop_tips` would therefore widen.
> - `__init__`'s `self._before: object = _NOTHING_PENDING` would make `constructor_state` `UNRESOLVED`,
>   so `entry_reset` would disappear as well.
>
> Every one of these consequences fails closed. It is a silent **precision** loss, not an unsoundness,
> and precision losses are exactly what nobody notices. **AC-18.1 pins
> `effect_backing_fields == ["_carried"]` at the pin**, so the change fails loudly in CI rather than
> quietly in a number. §18.8's cross-pin fixture is a second, independent tripwire, because
> `pick_up_tips` and `drop_tips` would both move.

**Setters and hidden getter dependencies (r1, M3; this replaces r0's "What R-A is NOT").** R-A does
not model what a property's setter does, so it must not pretend to know. r0 claimed that an
assignment `self.<F> = v` with `F ∈ S` is a write of the merged cell. That is false in general. At
1.0, `_tip`'s setter writes only `_before` (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:63-72`),
which does not change `has_tip` at all. The rule is now:

> **Normative (M3).** An assignment to `self.F`, where `F ∈ S` and `F` is a property of `C` (it has a
> `<F>.setter`, or has only a getter, in which case the assignment would raise), classifies
> **`UNRESOLVED`**. An assignment to a plain-field `F ∈ S`, which is the old-pin case, keeps the old
> rule and classifies as `cls(value)`.

A getter return that "contributes nothing" to `B` (such as `holder.tip`) can still depend on other
self attributes. At 1.0, `_pending_tip` reads `self._holder`, a property that reads `self._holder_ref`
(`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:51-53`). A method that rewrote `_holder_ref`
would change `has_tip` while writing no `W` field. R-B would then classify it `UNTOUCHED`, which acts
as a no-op and is unsound after `entry_reset`. Two **checked tripwires**, asserted over the pin in
AC-18.1, keep this out (redefined in r2, C8/C9):

> **Normative (the dependency set `D(F)`, r2).** For a getter `G_F`, `D(F)` is the set of names `a` such
> that some `Attribute(value=Name("self"), attr=a)` in **Load** context occurs **anywhere in `G_F`'s
> body**. That includes behind a local such as `holder = self._holder`, not only in return
> expressions. Every property name found is followed into its own getter. `B` and all property names
> are removed. The scan runs over **every** getter `G_F` with `F ∈ S`, not only the bool-view one.
>
> **At the pin *(read this revision)*:**
>
> | getter | reads | `D(·)` |
> |---|---|---|
> | `_pending_tip` | `self._holder` → `_holder`'s getter → `self._holder_ref`; `self._carried` ∈ `B` | `{_holder_ref}` |
> | `_tip` | `self._before`; `self._pending_tip` (recursed) | `{_before, _holder_ref}` |
>
> **The bool-view getter's set is `{"_holder_ref"}`**, as the adjudication pins it. **The set over all
> `S` getters is `{"_holder_ref", "_before"}`.** Both are asserted.

- **(i) Pinned writer snapshots.** For each `a` in the all-getter dependency set, the set of methods of
  `C` that write `self.a` is asserted equal to a **pinned snapshot**.
  - **"Writes `self.a"` (r3, minor 3)** means any statement shape in §18.4.3's full write-shape set,
    applied to `a`. That covers `Assign`, `AnnAssign` with a value, `AugAssign`, tuple/list targets,
    `Delete`, and the C3/X1 catch-alls: other Store/Del contexts, `setattr`/`delattr`/`object.__setattr__`/
    `__delattr__` on `self`, `self.__dict__`/`vars(self)`, and any non-attribute-base Load of `self`.
    The last three count as writes of **every** `a`.
  - It must **not** reuse `_attribute_writers` (P1b, `plr-sema/src/plr_sema/derive/receiver_state.py:247-266`).
    That scan counts only `ast.Assign`. It would miss `__init__`'s
    `self._before: object = _NOTHING_PENDING`, an `AnnAssign`
    (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:46`), and would silently miss
    `setattr`/`AugAssign`/tuple-target writers.
  - Any new writer breaks CI rather than silently leaving a method `UNTOUCHED`. The snapshots at the
    pin *(read this revision from `external/pylabrobot/pylabrobot/legacy/tip_tracker.py`)* are:
  - `_holder_ref` → `{__init__}` (`:41`);
  - `_before` → `{__init__, _tip (setter), _hold, commit, rollback, clear, load_state}` (`:46`, `:72`,
    `:77`, `:174`, `:186`, `:191`, `:211`).

  `_before`'s writers are exactly the transaction bookkeeping that A-COMMIT reasons about. A **new**
  writer of `_before` (for example, a public method writing a non-sentinel tip into it) would change
  what `get_tip`'s guard reads while pending, and it must be adjudicated before regeneration.
- **(ii) No writing getters.** No getter of `C` writes any self attribute.

If either tripwire fires, the test fails, and the derivation must be extended before it is
regenerated. Neither is assumed. **Cost: zero** — these are assertions over the pin, and they change
no classification.

### 18.4.3 R-B — argument-classified helper following

**Scope of a method body.** "The body of `m`" is every node reachable from `m.body` without entering a
nested `FunctionDef`, `AsyncFunctionDef`, `Lambda` or `ClassDef`. This is a deliberate narrowing of
today's `ast.walk(member)`, which enters nested definitions. Code in a nested definition does not run
when `m` is called. No 1.0 `TipTracker` method contains one *(verified by reading the file)*.

**Tip writes in a body.**

| statement shape | class contributed |
|---|---|
| `Assign`, or `AnnAssign` with a value, whose target is `self.x`, where `x ∈ S` is a **property** of `C` (M3) | `UNRESOLVED` |
| `Assign`, or `AnnAssign` with a value, whose target is `self.x` with `x ∈ W` otherwise | `cls(value)` (table below). An `Assign` with several targets is classified once per `W` target |
| `AugAssign` on `self.x`, `x ∈ W` | `UNRESOLVED` |
| a `Tuple`/`List` target containing `self.x`, `x ∈ W` | `UNRESOLVED` |
| `Delete` of `self.x`, `x ∈ W` | `UNRESOLVED` |
| **(r2, C3) catch-all:** any other `Attribute(value=Name("self"), attr=x)`, `x ∈ W`, in **Store** or **Del** context that no row above matched. Examples are a `for self._carried in …` target, `with … as self._carried`, and a `match` capture | `UNRESOLVED` |
| **(r2, C3)** a call to `setattr`, `delattr`, `object.__setattr__` or `object.__delattr__` whose first argument is `Name("self")`, **whatever the attribute-name argument is** (a literal or not) | `UNRESOLVED` |
| **(r2, C3)** any Load of `self.__dict__`, or any call `vars(self)`, anywhere in the body (store into it or not) | `UNRESOLVED` |
| **(r3, X1; generalises r2's D-3)** **any Load of `Name("self")` that is not the `value` of an `ast.Attribute` node**, anywhere in the body. That covers a bare argument to any call, followed or not (`self._h(self)` binds `self` to a callee parameter `p`, which can then write `p._carried = x`); a local alias (`me = self; me._carried = tip`, `t = self; t._put(None)`); a return, a container element and a comparison operand. Every such escape of the receiver is `UNRESOLVED` for the **whole method**, and the rule does not try to track the alias | `UNRESOLVED` |
| any assignment to `self.y`, `y ∉ W` (e.g. `_before`, `_tip_origin`) | nothing |

> **Cost of C3 + D-3: zero recovered effects at both pins** *(read this revision)*.
>
> - **At 1.0** no `TipTracker` method has a `for`/`with` target on `self.<W>`. None calls
>   `setattr`/`delattr`/`object.__setattr__`/`__delattr__`, and none reads `self.__dict__` or calls
>   `vars(self)`. None passes bare `self` to a call. The calls are `self._put(...)`, `self._hold(...)`,
>   `self.commit()`, `self._callback()`, `holder.(un)assign_child_resource(...)`,
>   `resting_location(holder, tip)`, `cast(…, self._before)`, `weakref.ref(holder)` and
>   `self._tip.tracker.register_callback(self._callback)`. Each passes attribute reads or other names,
>   never bare `self`.
> - **At the old pin** (`pr159` `pylabrobot/resources/tip_tracker.py`), `load_state`'s
>   `deserialize(state.get(…))` and `commit`'s callback calls likewise pass no bare `self`.
> - **The only D-3-shaped call in either tracker is the callback invocation `self._callback()`.** It
>   passes no argument at all. C15 below states the assumption that covers it.
> - **X1 (r3) is also zero cost at both pins** *(orchestrator-verified)*. In 1.0
>   `legacy/tip_tracker.py` and in the old pin's `resources/tip_tracker.py`, every `self` that is not
>   an attribute base is a method's own parameter declaration (an `ast.arg`, not a `Name` in Load
>   context), so X1 does not fire on it. Every `self` inside a method body in both files is the
>   `value` of an `Attribute` (round-4 challenger read the 1.0 file in full).

**Self-calls.** Every `ast.Call` in the body, at any expression position (statement, RHS, argument,
`await`), whose `func` is exactly `Attribute(value=Name("self"), attr=h)` is a candidate self-call to
`h`. **"Same class" means the direct methods of `C`**: `FunctionDef`/`AsyncFunctionDef` nodes that are
immediate children of `C`'s `ClassDef`, with no base-class resolution and no subclass overrides. The
candidate is resolved as follows:

- `h` names exactly one direct method with no decorator: **follow it** (below).
- `h` names more than one direct definition, or only a property, or a method decorated with
  `staticmethod`, `classmethod` or anything else (r1, m6): the call contributes `UNRESOLVED`
  (fail-closed, and there is no instance at 1.0).
- `h` names no direct method: **not followed, contributes nothing.** This covers inherited methods
  and callable attributes. The 1.0 instance is `commit`'s `self._callback()`
  (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:172-179`), where `_callback` is an instance
  attribute set by `register_callback`, not a method.

> **The callback residual, stated as a checked fact plus one assumption (r2, C15).** "Not a method" is
> why `self._callback()` is not followed, but it is not why skipping it is sound. That rests on two
> things:
>
> - **(a) Checked at the pin, and asserted in AC-18.2(q).** Every `register_callback` argument in
>   `LiquidHandler` is `self._state_updated`
>   (`external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:428-431`). `LiquidHandler`
>   does not override it, so it resolves to `Resource._state_updated`
>   (`external/pylabrobot/pylabrobot/resources/resource.py:1372-1374`). That method is a notifier: it
>   calls each registered state-update callback with `self.serialize_state()`, and it writes no tracker
>   field.
> - **(b) Assumed.** The **downstream** state-update callbacks registered on the liquid handler by user
>   code do not write a head tracker's state. This is not checkable from PLR source. It is recorded as
>   **A-CALLBACK-INERT**. The owner accepted it on 260929 (OI-21). Its row text is fixed in §18.5.5,
>   and T61 adds it to increment 1's §10.6.3 assumption table together with A-RACK-STATIC.

> **Why direct methods only is sound for the channel trackers, and where it stops being.** The head
> trackers are constructed by **name** as exactly `C`. R-C requires this through increment 3's
> fresh-only-construction conjunct (`reset_rule_candidates`,
> `plr-sema/src/plr_sema/derive/receiver_state.py:964-1012`), so their dynamic type is `C` and no
> subclass override can run. An **inherited** helper that writes a `W` field would be invisible.
> This is exactly the old P4's posture (P4 followed no calls at all), so R-B does not regress it.
> AC-18.2(k) turns the residual into a checked fact at the pin: no class in `C`'s PLR base closure
> assigns any `x ∈ W`.

**Binding.** Following `self.h(a₁, …, aₙ, k₁=v₁, …)` from a caller context `E` (a map from name to
class) builds the callee context `E′`:

1. Take `h`'s parameters after the first (`self`) in declaration order. Positional `aᵢ` bind to them
   in order, and `kⱼ=vⱼ` bind by name, exactly as Python binds them.
2. Each bound parameter gets `cls_E(argument)`.
3. An unbound parameter gets `cls(default)` if it has a default, and `UNRESOLVED` otherwise.
4. If the call site contains `ast.Starred` or `**`, or `h`'s signature has `*args`/`**kwargs`, **every**
   parameter of `h` gets `UNRESOLVED`.
5. **(r1, m6)** If the call would not bind under Python's rules, **every** parameter of `h` gets
   `UNRESOLVED`. That covers too many positionals, an unknown keyword, a keyword aimed at a
   positional-only parameter, a keyword-only parameter passed positionally, or the same parameter
   bound twice. Such a call would raise `TypeError` at runtime; the rule declines rather than
   reasoning about that.

**The argument/value classification `cls_E(e)`.** The first matching row wins.

| `e` | class |
|---|---|
| `Constant(None)` | `NO_TIP` |
| any other `Constant` | **`UNRESOLVED`** (r1, B1) |
| `Attribute(Name("self"), x)` with `x ∈ W` | `COPY` |
| `IfExp(test, body, orelse)` | `join(cls_E(body), cls_E(orelse))` |
| `Name(n)` with `n ∈ E` (a parameter of the current method) that is **never** bound in the body | `E[n]` |
| `Name(n)` with `n ∈ E` that **is** bound somewhere in the body (r1, B2) | `join(E[n], cls_E(v₁), …, cls_E(vₖ))` over **every** binding `n = vᵢ` in the body. Any other binding form of `n` gives `UNRESOLVED` (see the binding-forms rule below) |
| `Name(n)`, a local of the current method (not a parameter) | `join` of `cls_E(v)` over **every** binding `n = v` in the body. Any other binding form gives `UNRESOLVED`. Evaluated as a least fixpoint (r2, C10; see below) |
| `Name(n)` bound nowhere in the method (a global or free name) | `UNRESOLVED` |
| anything else: `Call`, `Subscript`, `BoolOp`, `Await`, `BinOp`, `UnaryOp`, a non-`W` attribute, `Lambda`, a comprehension, … | **`UNRESOLVED`** (r1, B1) |

`join(x, y) = x` if `x == y`, and `UNRESOLVED` otherwise.

> **Normative (locals as a Kleene least fixpoint, r2 C10; redefined r3).** For one method under one
> context `E`, let `N` be the set of names that the body binds by `=`/`AnnAssign`, including rebound
> parameters.
>
> - **The domain.** Classes are extended with a bottom `⊥` that `join` treats as its identity:
>   `join(⊥, x) = x`.
> - **Initialisation.** Every `n ∈ N` starts at `⊥`.
> - **One step.** Recompute every `n ∈ N` **simultaneously**, as the `join` of `cls(v)` over all of
>   `n`'s bindings. A rebound parameter also joins in `E[n]`, and a non-`=` binding form contributes
>   `UNRESOLVED`. A `Name(m)` inside a value, with `m ∈ N`, reads `m`'s value from the previous step.
> - **Termination.** Iterate until no value changes. This terminates: the lattice
>   `⊥ < {NO_TIP, HAS_TIP, COPY} < UNRESOLVED` has height 2, each step is monotone, and `N` is finite.
> - **Result.** Any name still at `⊥` is mapped to **`UNRESOLVED`**, meaning no grounded source.
>
> Because every name is iterated to stability together, the result is **independent of query order
> and of memoisation**. It replaces r2's stack formulation, which the round-3 challenger showed could
> depend on which name was queried first.
>
> Worked cases:
>
> | bindings | result |
> |---|---|
> | `tip = tip` alone | `UNRESOLVED`, since it stays at `⊥` |
> | `a = b; b = a` | `a`, `b` ↦ `UNRESOLVED` |
> | `a = b; b = a; b = None` | step 1: `a = ⊥`, `b = NO_TIP`; step 2: `a = NO_TIP`; stable, so `a`, `b` ↦ `NO_TIP` |
> | `a = None; a = a` | `NO_TIP` |
>
> **Cost: zero at both pins.** No tracker method in either has a self- or mutually-referential local
> binding. AC-18.2(r) is the fixture.

**Binding forms (r1, B2 and m6).** Only a plain `n = v` (`ast.Assign` whose targets include `Name(n)`
as a whole target) and an `AnnAssign` `n: T = v` count as a classifiable binding. **Every other form
that binds `n` in the body gives `UNRESOLVED`**: tuple or list unpacking, a `for`/`async for` target,
`with … as n`, `except … as n`, a walrus `n := …`, `AugAssign`, `global`/`nonlocal`, `del`, an
`import n`/`from … import n`, a `match` capture, and any form not listed here. At 1.0, `_put`
contains `from pylabrobot.resources.tip_rack import resting_location`, which binds
`resting_location`, not `tip`. The rule is keyed on the name, so that import does not affect `tip`.

> **Why B1 replaced "anything else → `HAS_TIP`" (r1).** r0 kept the old P4 row that turned any
> non-`None` expression into `HAS_TIP`. That row is the source of the old unsoundness L1 exists to fix,
> and it reproduces it on the old-pin tracker. There, `load_state` writes
> `self._tip = cast(Optional[Tip], deserialize(state.get("tip")))` (old pin, pr159 worktree,
> `pylabrobot/resources/tip_tracker.py` lines 141-142). That value is a `Call`, which r0's table
> classed `HAS_TIP`. Any expression that may evaluate to `None` would likewise have made a later
> `NoTipError` guard decide `SAFE` while the runtime raises. Examples are a call result, `state.get(…)`,
> `x or None` and `holder.tip`. r0 got L1 right at 1.0 only because PLR happened to write an `IfExp`
> with a `None` arm there.
>
> **Cost at 1.0: zero** *(reasoned; the defender traced it: 0 effects and 0 of the 216 lost)*. The only
> `W` writes in the 1.0 tracker are these:
>
> - `_put`'s `self._carried = tip`, which is a parameter;
> - `__init__`'s `= None`.
>
> `add_tip`'s `tip` is still `HAS_TIP` through its entry annotation `Tip`. **The positive tip value
> now comes only from an entry parameter whose annotation passes the allowlist below (r2, C2).** No
> expression form is presumed to be a tip, and neither is an unannotated parameter.

**Entry context (rewritten in r2, C2: an allowlist on the annotation's node shape).** When a method `m`
is classified on its own (the top of a derivation, not a followed call), each parameter `p` of `m`
gets one of two classes.

1. **Derive the tip type name `T`.**
   - `T = { P1a(C)[x] : x ∈ W ∩ dom P1a(C) }`, where `P1a(C)` is `_annotated_attributes(C)`, the
     existing `self.<x>: <ann>` scan. It **already returns the unwrapped class-name string**
     (`plr-sema/src/plr_sema/derive/receiver_state.py:233-244`), so no second unwrap is applied (r3,
     minor 1).
   - **`T` must be a singleton `{t}`.** If it is empty, or holds more than one name, no parameter of
     any method of `C` gets `HAS_TIP`, which fails closed.
   - It is derived over **`W`**, not `B` (defender's correction), so the old pin, where `B = ∅`, still
     yields a type name.
   - No literal type name is typed anywhere.
2. **Classify `p`.**
   - **`HAS_TIP` iff all of these hold:**
     - `p` has an annotation;
     - the annotation node is **exactly** one of `Name(id=t)`, `Attribute(attr=t)` (any value), or
       `Constant(value=t)` where `t` is a string;
     - `p`'s default is not `Constant(None)`.
   - **Otherwise `UNRESOLVED`.** That covers:
     - an unannotated parameter;
     - `Any` / `object`;
     - `Optional[t]` / `typing.Optional[t]`;
     - `Union[t, None]`;
     - `t | None` and `None | t | X`;
     - any alias name (`MaybeTip`);
     - `Annotated[…]`;
     - a string that parses to any of these;
     - any annotation naming something other than `t`.
   - **The match is on the node shape. The implementation must not test
     `_unwrap_annotation(p.annotation) == t`.** That helper strips `Optional[…]` and `X | None`
     (`plr-sema/src/plr_sema/derive/receiver_state.py:187-224`), so the test would re-admit `Optional[Tip]`.

At the two pins:

| pin | `W ∩ dom P1a(C)` | `T` | entry parameter | class |
|---|---|---|---|---|
| 1.0 | `{_carried}` (`self._carried: Optional["Tip"]`); `_before: object` and `_tip_origin` are ∉ `W` | `{"Tip"}` | `add_tip(self, tip: Tip, …)`, annotation `Name("Tip")` (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:137-159`) | `HAS_TIP` |
| old pin | `{_tip, _pending_tip}` (`pr159` `pylabrobot/resources/tip_tracker.py` lines 42-43, both `Optional["Tip"]`) | `{"Tip"}` | `add_tip(self, tip: Tip, …)`, same shape (lines 76-79) | `HAS_TIP` |

**Cost of C2: zero recovered effects at both pins** *(read this revision)*. The only entry parameter
whose class reaches a `W` write through a public method is `add_tip`'s `tip`, and it is a bare
`Name("Tip")` at both pins. `_hold`'s and `_put`'s `tip: Optional["Tip"]` were already `UNRESOLVED`,
and they are private and unpublished. **OI-20 is closed.**

**The fold.** Collect the multiset `K(m, E)` of classes contributed by `m`'s own tip writes and by every
followed self-call. A followed call contributes its callee's **result** under `E′`, by recursion, where
`UNTOUCHED` contributes nothing. Then drop every `COPY` and read the result:

| `K` after dropping `COPY` | result |
|---|---|
| empty | `UNTOUCHED` |
| `{HAS_TIP}` only | `HAS_TIP` |
| `{NO_TIP}` only | `NO_TIP` |
| contains `UNRESOLVED`, or contains both `HAS_TIP` and `NO_TIP` | `UNRESOLVED` |

The fold is **flow-insensitive**, as P4 has always been. A write under a condition counts as if it
happened. This is inherited, not introduced, and OI-5 records why it survives at 1.0. `_put`'s
holder-less write is conditional on `holder is None`, and R-C's holder-less conjunct is what makes it
the executed path for the head trackers.

**The cycle guard (L4).** The recursion carries the call stack as a frozenset of method names, which
is the same device `_walk_anchor_stmts` uses
(`plr-sema/src/plr_sema/derive/receiver_state.py:625-688`). **One difference, stated:** a call whose
callee is already on the stack contributes `UNRESOLVED`, where the anchor walk contributes nothing.
The anchor walk threads one running state, so a revisit re-applies effects it has already seen. R-B
re-binds arguments on each call, so a recursive call may carry a different binding. Skipping it could
hide a write. **The depth is unbounded.** It terminates because the stack only grows, and it is
bounded by the number of direct methods of `C`.

> **Normative (`effects_max_depth`, r1, M4).** The artifact publishes `effects_max_depth`. It is the
> maximum, over all **entry methods**, of the length of the longest chain of followed self-calls that
> **ends in a `W` write**. The chain length is the number of call edges; a write in the entry method's
> own body has length 0.
>
> - **Entry methods** are the public direct methods of `C` (names not beginning with `_`) plus `__init__`.
> - The value is a structural property of the call graph. It is independent of evaluation order and of
>   any memoisation the implementation uses.
> - A chain that passes through a cycle-guarded call ends at that call and does not count.
>
> The expected value at 1.0 is **2** (`add_tip` → `_hold` → `_put`, which writes `_carried`).

> **The interaction with the recon's zero-argument rule, and why that rule is not adopted.** The recon
> proposed following only self-calls that pass at least one argument. Its reason: following the
> zero-argument `self.commit()` poisons `add_tip`/`remove_tip` at the old pin, because old `commit`
> writes `self._tip = self._pending_tip` and that write is classified `"ambiguous"`. This document
> follows **every** resolved self-call, zero-argument ones included, and gets the same non-poisoning
> from `COPY`. Old `commit`'s write is `self.<S> = self.<S>`, which classifies `COPY` and is dropped by the
> fold. Old `add_tip` is therefore `{HAS_TIP, COPY}`, which gives `HAS_TIP`. The recon's filter is
> **unsound in general**. A zero-argument helper that writes a constant, such as 1.0's `clear()`
> (`self._put(None)`) called from some future public method, would be skipped entirely. Its caller would
> then be classed `UNTOUCHED`, a no-op, when it really clears the tip. AC-18.2(c) and AC-18.2(d) pin
> both halves: a zero-argument `COPY` helper does **not** poison its caller, and a zero-argument
> constant-writing helper **does** propagate its class.

### 18.4.4 L1 — `effects_unresolved`, and the widen mapping in the bridge

**Publication.** For every direct method `m` of `C` whose name does not begin with `_` (R-D), classify
`m` under its entry context:

- `HAS_TIP`/`NO_TIP` → `effects[m]`.
- `UNRESOLVED` → `m ∈ effects_unresolved`.
- `UNTOUCHED` → neither.

**Amendment to increment 1 §10.2.4.** §10.2.4 said that a method whose writes are "of both kinds" has
"no effect (the method is transparent to this abstraction)". Under L1 that disposition is withdrawn
for tracker methods: both kinds is `UNRESOLVED`. The old wording made a method that clears in one
branch and loads in another a no-op, which is the omission-as-no-op unsoundness L1 exists to close.
The E4.3 rule (conflicting **bridges** on the receiver) is untouched, because it already widens.

**Amendment to increment 1 §10.4's E2 (r1, M2, decided as a rule change).** E2 takes a method's
single depth-0 effect. Today's code applies it **even when a deep effect is also present**
(`plr-sema/src/plr_sema/derive/receiver_state.py:1576-1582`), so a method with a direct `add_tip` and
a nested `drop_tips` would get `HAS_TIP`. Restoring effects makes that case live. **Normative: when
depth-0 and deep tracker-mutating effects coexist, `channel_effect` is `"widen"`.** This is recorded
beside the §10.2.4 amendment and landed by T64's text edit. **Cost at 1.0: zero** *(the defender
traced it)*.

**Its breadth is published, not just argued (r2, C14).** T57 adds a top-level derivation count,
`receiver_state_diagnostics.n_contracts_depth0_and_deep_coexist` (`int`), to
`derived_contracts.json`. It counts contracts where depth-0 and deep tracker-mutating effects coexist,
and the prediction is **0**. The challenger confirmed the rule does not create a second divergence:
`update_head_state` widens at both pins through its conflicting depth-0 bridges (1.0
`external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:483-503`; old pin `pr159`,
lines 277-282). The M11 counter catches any moved key regardless. **OI-19 is closed.**

**Definition (r1, m8).** A **bridge** of a contract entry `K` is a `dropped_calls` entry, anywhere in
`K`'s `delegates_to` closure, whose expression matches `self.<channel_attr>[<name>].<m>` for the
receiver's own derived `channel_attr`. "`K` has a bridge" means at least one such match exists.

**The bridge (normative change to `compute_channel_bridge`).** During the closure walk, for each
bridge `self.<channel_attr>[…].<m>`, the following rules run **before** today's
`if c_key not in index: continue` skip (`plr-sema/src/plr_sema/derive/receiver_state.py:1536-1538`),
which r0 placed its rules behind (r1, M1):

0. **(r1, M1)** If `m` is not a direct method of `C`, or `(tracker_module, "C.m")` is not in the
   survey index, set `any_unresolved = true`. A bridge the survey cannot see is omission-as-no-op,
   which L1 forbids. At the pin every 1.0 `TipTracker` method is in `training/verify/data/plr_preconditions.json`
   *(challenger-verified; zero cost)*.
1. If `m ∈ effects_unresolved`, set `any_unresolved = true`, at any depth.
2. Else if `m` begins with `_`, also set `any_unresolved = true`. A private tracker method is never
   published, so a bridge to it cannot be justified from the artifact. AC-18.3 asserts that no bridged
   method at the pin is private.
3. Else, the existing depth-0 / deep bookkeeping over `effects.get(m)` applies.

Only after rules 0–3 does the index skip apply, and only to the guard-attachment half of the loop:
there are no guards to attach for a method the index lacks.

`channel_effect` is then decided in this order:

1. `"widen"` if `any_unresolved`;
2. otherwise `"widen"` if depth-0 and deep effects coexist (M2);
3. otherwise the existing three-way outcome.

**Unresolved takes precedence over everything.** Check-side needs **no change**: `_apply_transfer` already widens the
whole receiver on `"widen"` (`plr-sema/src/plr_sema/check/tipstate.py:568-596`), and V5 already
treats `"widen"` as a departure (`plr-sema/src/plr_sema/check/volumestate.py:547-588`).

**The `load_state` case, end to end.** `TipTracker.load_state` binds
`pending_tip = Tip.deserialize(pending_tip_data) if pending_tip_data is not None else None` and then calls
`self._put(pending_tip)` (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:201-211`). The local's
one binding is an `IfExp`. Under B1 its `Call` arm is itself `UNRESOLVED`, so the join is `UNRESOLVED`
whatever the other arm says. The conclusion therefore does **not** depend on the `IfExp`'s `None` arm.
On the old pin's shape, `self._tip = cast(…, deserialize(…))`, the write is a `Call` and is
`UNRESOLVED` directly (AC-18.2(l), inline fixture). `_put` binds `tip ↦ UNRESOLVED` and writes `self._carried = tip`, which is also
`UNRESOLVED`. So `load_state ∈ effects_unresolved`. `LiquidHandler.load_state` bridges
`self.head[channel].load_state(tracker_state)` at depth 0
(`external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:460-478`), so its
`channel_effect` is `"widen"`. At runtime, `load_state({"tip": None, "pending_tip": None, …})` leaves no
tip, and a serialized tip leaves one. The state after the call genuinely depends on data. `widen` is
the only honest summary of that, and `HAS_TIP` (the old pin's value) was a false `WILL_FAIL` waiting to
happen on a subsequent pickup. **Predicted benchmark impact: none.** `load_state` is not in the tier-1
tool vocabulary; the ten methods in `real.oracle_replay.json`'s `scope_verdict_by_method` are listed in
§18.9. The change is evidenced by AC-18.3 and AC-18.9, not by the run.

### 18.4.5 R-C — constructor seeding, the holder-less conjunct, and atomicity (L7)

**R-C(1).** `constructor_state(C)` is the R-B result of `C.__init__` under its entry context, with
`AnnAssign`-with-value included, as `_constructor_state` already includes it. It is computed over `W`,
not `S`. At 1.0, `__init__`'s `self._carried: Optional["Tip"] = None`
(`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:39-49`) classifies `NO_TIP`, and no other `W`
write occurs, so `constructor_state = NO_TIP`.

**R-C(2), the holder-less conjunct (new, fail-closed).** `entry_reset` is emitted only if, in addition
to increment 3's three conjuncts, **every** constructor call of `C` in the single `conj123` assignment's
right-hand side binds **no parameter of `C.__init__` whose default is `Constant(None)`**. Binding
follows R-B's rules, and `*`/`**` at the call site makes the call inadmissible. If R-C(2) fails,
`entry_reset` is absent with the existing ledger value `"absent"`, so no new vocabulary is needed. At
1.0 the reset site is `setup`'s
`self.head = {c: TipTracker(thing=f"Channel {c}") for c in range(self.backend.num_channels)}`
(`external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:408-433`, the line at `:418`).
It binds only `thing`. `holder`'s default is `None` and it is left unbound, so R-C(2) holds.
`load_state`'s own construction (`:469`) sits inside an `if`, so it is `conj12` only, which is unchanged
from the old pin.

> **Why R-C(2) exists.** R-A treats `_carried` as `_pending_tip`'s backing, but that is true only on the
> getter's `holder is None` path. On a holder-full tracker the initial state is the holder's child, which
> may be a tip. R-C(2) is the cheapest derived witness that the reset constructs trackers without the
> optional collaborator that selects the other path. It is a signature heuristic, not a proof, and OI-5
> says so. **It fails closed only while the holder-selecting parameter has a `None` default** (r1, m2).
> If PLR builds head trackers with a holder passed to such a parameter, `entry_reset` disappears and
> every first-pickup guard returns to `UNKNOWN`. If PLR instead made the holder a **required** parameter,
> or gave it a non-`None` default, R-C(2) would pass **vacuously**, and nothing in R-C(2) would notice.
> M3's tripwire (i) and AC-18.9's holder-full polarity check are the backstops for that case.

**L7, atomicity.** R-A, R-B, the L1 mapping and R-C land in **one** task (T57) and **one** regeneration
of `plr-sema/data/derived_contracts.json`. The hazard the recon named is real. With `entry_reset` but
no `add_tip` effect, the walk would start every channel at `NO_TIP` and **never** move it to `HAS_TIP`
after a pickup. A repeated `pick_up_tips` would then evaluate its own `:758` guard against `NO_TIP` and
emit `SAFE` where PLR raises `HasTipError` *(reasoned from `tipstate.evaluate_call` and
`_apply_transfer`, `plr-sema/src/plr_sema/check/tipstate.py:568-596`; not run)*. AC-18.4(c) pins the
invariant on the artifact: `entry_reset` present ⇒ `effects` contains both a `HAS_TIP` and a `NO_TIP`
entry.

### 18.4.6 R-D — publication hygiene

`effects` and `effects_unresolved` list only methods whose name does not begin with `_`. This covers
`_hold`, `_put` and `__init__`. The recon asked for this so the published maps describe the tracker's
public protocol. **The bridge does not depend on it.** Rules 0 and 2 of §18.4.4 widen on any bridge
to a private method, or to a method outside `C` or outside the index, so an unpublished
classification can never silently drive a verdict.
`constructor_state` stays internal, as it is today, and is visible only through `entry_reset`.

### 18.4.7 R-E — receiver roots (L2)

`derive_receiver_states` (`plr-sema/src/plr_sema/derive/receiver_state.py:1160-1289`) iterates **every**
PLR class and admits any class with an annotated attribute that types to a P2-anchored class. At 1.0,
`TipTracker.__init__`'s `self._carried: Optional["Tip"]` types to `Tip`, and `Tip` has a P2 anchor
(`has_collar_height`), so `TipTracker` is admitted as a receiver of its own. The shipped artifact shows
it (`receiver_state.TipTracker`, `channel_attr: "_carried"`, `tracker_class: "Tip"`).

**Rule R-E.** It runs in two passes over the same inputs.

1. Compute the **candidate** set: `Cand = {R : R has a P1a attribute whose target class has a P2 anchor}`,
   with today's alphabetical attribute tie-break. Also compute the **tracker** set:
   `T = {tracker_class(R) : R ∈ Cand}`.
2. The published receivers are `Cand \ T`.

A class that is some candidate's tracker is never a receiver. That is "rooted at machine-frontend
attributes, not recursing into tracker classes' own annotated attributes", stated as set algebra over
facts P1a and P2 already compute. **No class name appears in the rule.**

**Expected at 1.0:** `Cand = {LiquidHandler, LiquidHandlerBackend, TipTracker}` and
`T = {TipTracker, Tip}`, which leaves the receivers **`{LiquidHandler, LiquidHandlerBackend}`**.
`LiquidHandlerBackend` (`channel_attr: "_head"`) is in the shipped 1.0 artifact today, is not a tracker,
and is kept. The recon did not mention it. **AC-18.6 pins the derived receiver set.**

**Feasibility and breadth, answered rather than assumed.** The rule is feasible: it needs only the
`anchor_cache` and the P1a map already built inside `derive_receiver_states`. It **can** be over-broad in
one shape. A class that is both a legitimate channel receiver and the P2-anchored tracker of another
candidate would be dropped. That drop fails closed (lost precision, never a wrong verdict), and there is
no instance at 1.0. `LiquidHandler`'s only `@property` is `_resource_pickup`, whose body is
`return self._resource_pickups.get(0)` (`external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:399-406`).
That is not P2's `return self.<F> is/is not None` shape, so `LiquidHandler` cannot become some other
class's tracker. OI-15 records the residual.

### 18.4.8 The artifact — fields, types, placement

All new keys are **additive** in `derived_contracts.json → receiver_state[R]`. Check-side reads none of
them; it reads only `channel_effect` and `entry_reset`, both of which already exist. So a stale table
degrades exactly as AC-10.7 already requires.

| key | type | always emitted? | meaning |
|---|---|---|---|
| `effects` | `object<str, "HAS_TIP"\|"NO_TIP">` | yes (existing) | R-B results for public methods of `C` |
| `effects_unresolved` | `array<str>`, sorted | **yes, possibly `[]`** | public methods whose R-B result is `UNRESOLVED` |
| `effect_backing_fields` | `array<str>`, sorted | **yes, possibly `[]`** | `B` from R-A |
| `effects_max_depth` | `int ≥ 0` | **yes** | L4's published depth |
| `entry_reset` | `{"method": str, "post": "no_tip"\|"has_tip"}` | when admissible (existing) | now reached through R-C |

There is one further additive key, at the **top level** of `derived_contracts.json` rather than per
receiver (r2, C14): `receiver_state_diagnostics: {"n_contracts_depth0_and_deep_coexist": int}`,
predicted `{"n_contracts_depth0_and_deep_coexist": 0}` at 1.0.

"Always emitted" is deliberate. It lets AC-18.8 tell "the new derivation ran and found nothing" from
"this table predates §18". Per-contract `channel_effect` keeps its existing domain
`{absent, "HAS_TIP", "NO_TIP", "widen"}`.

**Expected `receiver_state["LiquidHandler"]` at 1.0.** This is what the fixer must reproduce. It is
not an input: publish the measured value and adjudicate any difference, never paper over it. Only the
changed keys are shown.

```jsonc
"LiquidHandler": {
  "channel_attr": "head", "tracker_class": "TipTracker",           // unchanged
  "state_fields": ["_pending_tip", "_tip"],                          // unchanged
  "effect_backing_fields": ["_carried"],                             // NEW (R-A)
  "effects": {"add_tip": "HAS_TIP", "clear": "NO_TIP", "remove_tip": "NO_TIP"},   // was {}
  "effects_unresolved": ["load_state"],                              // NEW (L1)
  "effects_max_depth": 2,                                            // NEW (L4)
  "entry_reset": {"method": "setup", "post": "no_tip"}               // was absent (R-C)
}
```

**Expected `receiver_state["LiquidHandlerBackend"]` at 1.0 (r1, m7).** It has the same tracker class,
so the tracker-keyed values are identical: `effect_backing_fields`, `effects`, `effects_unresolved` and
`effects_max_depth` all equal `LiquidHandler`'s above. It has **no `entry_reset`**. Its only write of
`self._head` is `set_heads`'s `self._head = head`
(`external/pylabrobot/pylabrobot/legacy/liquid_handling/backends/backend.py:63-66`), which is not a
fresh construction, so increment 3's conjunct 1 fails. No contract bridges `self._head[…]`, so no
`LiquidHandlerBackend` contract gains a `channel_effect` *(reasoned from the 1.0 survey's
`dropped_calls`: every bridge-shaped entry there is on `head`/`head96`)*.

### 18.4.9 The expected selection, per 1.0 `TipTracker` method *(reasoned from reading `legacy/tip_tracker.py`; T57 measures)*

| method | tip writes / followed calls | result | published as |
|---|---|---|---|
| `add_tip` | `self._hold(tip)`, with `tip ↦ HAS_TIP` from the entry annotation `Tip`; `_hold` → `_put` → `_carried = tip`; `self.commit()` followed, `UNTOUCHED` | `HAS_TIP` | `effects` |
| `remove_tip` | `self._hold(None)` → `NO_TIP`; `commit` `UNTOUCHED` | `NO_TIP` | `effects` |
| `clear` | `self._put(None)` | `NO_TIP` | `effects` (new relative to the recon's list; not bridged from `LiquidHandler`) |
| `load_state` | `self._put(pending_tip)`; the local is an `IfExp` whose `Call` arm is `UNRESOLVED` under B1 | `UNRESOLVED` | `effects_unresolved` |
| `rollback` | `self._put(self._tip)`, so `COPY` | `UNTOUCHED` | neither |
| `commit` | writes only `_before` (∉ `W`); `self._callback()` not a method | `UNTOUCHED` | neither |
| `_hold`, `_put` | entry `tip: Optional["Tip"]`, so `UNRESOLVED` | `UNRESOLVED` | neither (R-D) |
| `__init__` | `_carried: … = None` | `NO_TIP` | `constructor_state` only |
| all others | no `W` write | `UNTOUCHED` | neither |

---

## 18.5 The `:338` site rule and the sixth observation field (L3)

### 18.5.1 The guard, and why it is `UNKNOWN` today

`_check_tip_racks_available` (`external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:332-338`)
collects each distinct `TipRack` parent of the passed spots and raises `ValueError` if any of them is not
`_available_for_tip_handling`. That property (`external/pylabrobot/pylabrobot/resources/tip_rack.py:355-363`)
is false when the rack has a lid, or when it sits in a z-`ResourceStack` and is not the top child. PLR
calls the guard in four places: `pick_up_tips` at `:721`, `drop_tips` at `:872`, `pick_up_tips96` at
`:1706` and `drop_tips96` at `:1787` (all in `external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py`).

The shipped 1.0 contract record is inlined into each caller at depth 1, or at depth 2 through
`discard_tips`. It is `condition: "not rack._available_for_tip_handling"`, `raises: "ValueError"`,
`site.qualname: "_check_tip_racks_available"`, predicate `Not(Opaque("rack._available_for_tip_handling"))`
and `reachability_clear: true` (`plr-sema/data/derived_contracts.json`, read under
`LiquidHandler.discard_tips`). `guard_reason` maps any predicate containing `Opaque` to
`guard_predicate_unparsed` (`plr-sema/src/plr_sema/check/predicate.py:1043-1053`). **This remains the
reason on every decline below, so the site rule adds no reason and moves no reason when it declines.**

The guard cannot be read through the existing `:321` deck-membership rule, because the wire carries
no lid or stack field for any resource. The resource being present on the deck is a different fact
from the rack being clear of anything on top.

### 18.5.2 The observation field `tip_racks_available`

> **Normative (the sixth field).** The observation record gains **one** field.
>
> | field | type | what it decides |
> |---|---|---|
> | `tip_racks_available` | `bool` | the `:338` site rule's observation conjunct, and nothing else |
>
> **How the harness computes it.** `capture_observation`
> (`training/verify/deck.py:389-426`) computes it at the **same single capture point** that already
> exists: after `await setup.machine.setup()` and before `_execute`
> (`training/verify/verifier.py:201-204`), inside the same fail-closed guard. The value is
> `all(node._available_for_tip_handling for node in <deck tree> if isinstance(node, TipRack))`, and the
> deck tree is walked by the same stack walk `deck_resource_names` uses
> (`training/verify/deck.py:166-184`). It is vacuously `True` on a deck with no tip rack. A raising read
> makes the whole record `None`, as today (§16.2.1). `region_oracle.py`'s capture shares
> `capture_observation` and inherits the field.
>
> **Encoding.** `observation_env_members` (`plr-sema/eval/oracle_common.py:746-852`) adds
> `obs:tip_racks_available=` + `json.dumps(value)`, giving `true` or `false`, read **by name**.
> `OBSERVATION_KEYS` (`plr-sema/eval/oracle_common.py:740-743`) grows to six. The cache key partitions
> on it through `env` (§16.2.3), with no sixth `cache_key` component.
>
> **The harness can build a lidded rack (r2, C5/D-4; owned by T60).** `DeckLayout`
> (`training/verify/deck.py:89-112`) has only `resources`, `seed_volumes` and `holders`, and nothing in
> `training/` builds a `Lid`. Without a lidded rack, neither AC-18.10's own lidded fixture nor the m3
> mutant could exist. T60 therefore adds:
>
> - **A new field.** `lidded_tip_racks: list[str] = field(default_factory=list)` on `DeckLayout`, with
>   `merged()` concatenating it like `holders`.
> - **`build_setup`, after the tip racks are placed.** For each named rack, it assigns a real PLR `Lid`
>   sized to that rack. At least as large as the rack is enough: PLR's lid placement raises only if the
>   rack already has a lid, or if the lid is more than 1 mm smaller than the rack *(challenger's reading
>   of `lid.py`; not re-read here)*.
> - **The default is empty**, so every existing layout builds byte-identically. That is pinned by a
>   default-layout-unchanged unit test, and on the benchmark by the hard term `real_rows_executed = 343`.
>
> PLR 1.0 accepts a real `Lid` on a `TipRack` because `TipRack` is `Liddable`
> (`external/pylabrobot/pylabrobot/resources/tip_rack.py:306`).
>
> **Amendment to §16.2.1's closed record.** The closed field list grows by exactly this field.
> §16.2.1's refusal list also names **"lid topology — refused"**. This field is an aggregate boolean
> over lid **and** stack topology, so it is a narrowed, explicit exception to that refusal. It is not a
> general admission of lid topology: no per-rack or per-lid fact enters the record. §17.3's `arm_slots`
> set the precedent for extending the closed record inside a later increment.

**The legitimacy argument, and the objection it does not fully answer.** §16.2.2's third failure mode
refuses any observation that "is a **function of the guard being decided**". Its test: *could the
harness compute this field only by evaluating the same expression the guard evaluates?* **Read
literally, `tip_racks_available` fails that test.** It evaluates `_available_for_tip_handling`, the same
property whose negation is the guard's condition. This document does not pretend otherwise. The case
for admitting it anyway has three parts:

1. **When it is read.** The field is taken before execution, over the **initial** deck. The guard runs
   later, over the racks of one operation's spots. The refusal exists to stop "conditioning a static
   verdict on the outcome". Here the harness reads a pre-execution state fact, exactly as
   `deck_resource_names` is a pre-execution fact about the set `get_resource` searches.
2. **What bridges the gap.** The move-family conjunct (§18.5.4) is what makes the initial fact carry
   forward. Without it the field would indeed be the answer by another name. With it, the field is
   the initial state and the conjunct is the frame condition.
3. **Scope.** It quantifies over *every* rack on the deck, not the operation's racks, so it is strictly
   stronger than the guard needs. One lidded rack anywhere makes every `:338` decline.

> **Amendment to §16.2.2's text (r1, M10; landed by T60, asserted by AC-18.10).** Amending only §16.2.1
> would leave §16.2.2's normative test contradicted by a field the record admits. The third
> failure-mode paragraph gains one clause, verbatim:
>
> *"An observation that is a pre-execution state fact may coincide with the value a guard reads **only
> together with a frame condition the analyzer itself checks over the program**, one that declines
> whenever the program could have changed that state before the guard runs. `tip_racks_available` with
> §18.5.4's `rack_topology_stable` is the one instance. Without a checked frame condition such a field
> is the answer, not an observation, and is refused."*

OI-1 is resolved by this amendment. The residual risk is that the frame condition is incomplete. That
is A-RACK-STATIC's (§18.5.5), and it is tracked there.

**One raising read nulls the whole record, and that is accepted (r1, m12).** `_available_for_tip_handling`
is a **private** PLR property. If reading it raises on some rack, §16.2.1's one-capture-point rule makes
the **entire** `plr_observation` `None`. That disables not only `:338` but every other observation
rule for that row: `:321`, R-HEAD, R-CONST, `:375`/`:383` and R-ARM. This is accepted deliberately. A
partial record is exactly what §16.2.1 forbids, and the failure direction is decline, which is sound.
The cost is precision on that row only. AC-18.10's raising-read fixture asserts that the whole record
is `None`.

### 18.5.3 The site rule (4th `D6_SITE_RULES` row)

> **Normative.** `D6_SITE_RULES` (`plr-sema/src/plr_sema/check/predicate.py:1455-1463`) gains
> **one** entry keyed by symbol:
>
> `("_check_tip_racks_available", "ValueError", "not rack._available_for_tip_handling")`
>
> Its function `_eval_tip_racks_available_site_rule(ctx) -> bool | None` returns **`False`** iff all
> three conjuncts hold **and the guard's `kind` is `"raise_guard"`** (r1, m5), and **`None`** (decline)
> otherwise. **It never returns `True`.**
>
> The kind check matters because `evaluate_guard` negates the value for non-`raise_guard` kinds
> (`plr-sema/src/plr_sema/check/predicate.py:1604-1605`), which would turn a `False` into a firing
> `True`. The shipped `:338` record is `"raise_guard"`. The site-rule signature gains access to the
> guard's `kind`, as a `_Ctx` field `guard_kind` set by `evaluate_guard`; the three existing D6 rules
> ignore it.
>
> 1. `_observation(ctx.env).get("tip_racks_available") is True`;
> 2. `_observation(ctx.env).get("deck_resources_verified") is True`, the existing aggregate the `:321`
>    rule reads (`plr-sema/src/plr_sema/check/predicate.py:1198-1236`);
> 3. `ctx.rack_topology_prefix_ok is True and ctx.rack_topology_loop_ok is True`, whose conjunction is
>    §18.5.4's `rack_topology_stable` (r2 split it into two fields). Both fields default to `None`, so
>    a caller that does not thread them gets a decline.
>
> **Factoring (r2, C4).** The decision is a pure function,
> `tip_racks_decline_reason(ctx) -> str | None`. It returns the **first failing conjunct**, checked in
> this fixed order:
>
> 1. `"kind"` — `ctx.guard_kind != "raise_guard"`;
> 2. `"observation"` — `tip_racks_available` is not `True`;
> 3. `"deck"` — `deck_resources_verified` is not `True`;
> 4. `"topology_prefix"` — clause (i) of §18.5.4 fails (a disturber at an earlier pc);
> 5. `"topology_loop"` — clause (i) holds, but clause (ii) fails (inside a loop with a disturber
>    anywhere);
> 6. `None` — every conjunct holds.
>
> The site rule returns `False` **iff** that function returns `None`, and returns `None` otherwise.
> Separating (4) from (5) needs the two clauses. So `_Ctx` carries `rack_topology_prefix_ok` and
> `rack_topology_loop_ok` (both `bool | None`, default `None`, where `None` counts as failing (4))
> instead of the single r1 `rack_topology_stable` field. `rack_topology_stable` is their conjunction.
> The measurement script calls this same function (§18.9), so the attribution cannot drift from the
> decision.

**False-only, and why that is the whole soundness story on the `T` side.** `evaluate_guard` maps a
site-rule `False` to `SAFE` without consulting depth or reachability
(`plr-sema/src/plr_sema/check/predicate.py:1522-1620`, the dispatch at `:1602-1603`). A `None` flows to
`guard_reason`, which returns `guard_predicate_unparsed` as today. The rule can therefore add `SAFE`
findings and cannot add a `WILL_FAIL`. The same holds for the three existing D6 rules (D-G6).

**Why the whole-deck observation covers the operation's racks: the harness-grounding premise (r1, M6,
rewritten).** r0 said conjunct 2 "covers off-deck racks". **That claim is withdrawn.**
`deck_resources_verified` is vacuously true for a row that declares no deck-parented resource, and it
covers only resources parented directly to `Deck`. So it cannot carry that claim. The rule rests
instead on how the harness builds every executed call:

1. On every harness path (tier 1 and region oracle), a tip-spot argument reaches PLR only as an object
   the verifier's planner **resolved from the built deck**. That deck is the same tree
   `tip_racks_available` walks, so the parent rack of every spot an executed call passes is a rack
   the observation quantified over.
2. A call whose arguments cannot be resolved is never planned, and `calls_from_plr_kwargs` drops it
   from the static stream (`plr-sema/eval/oracle_common.py:653-657`). **Premise, stated (m10):** an
   un-planned call means the runtime raised at that index, so nothing after it is reached, and the
   frame condition is never asked about a call that did not execute.
3. `env` carries `obs:` members only when the harness built them, so a program analyzed outside the
   harness gets no observation, and the rule declines.

Conjunct 2 stays as **defence in depth**: cheap, and already true on the pickup population. It is no
longer load-bearing for any off-deck argument.

**No argument-reading conjunct is added.** Reading the guard's own tip-spot argument would need either
a binding for `_check_tip_racks_available`'s `resources` parameter or a hand-typed parameter name.
There is no binding: it is a module-level delegate, M1 binds nothing for those (AC-16.3), and every
inlined `:338` record in the shipped 1.0 table carries `caller_args: null` and `caller_args_sites: []`
(read this session in `plr-sema/data/derived_contracts.json`). A hand-typed name is forbidden by L0 and
would be a second HM-26 unit. The residual case is a program that constructs its own off-deck
`TipRack` and reaches this rule. It moves to OI-3, where a derived argument binding for module-level
delegates is recorded as the follow-up that would close it (backlog #5663).

### 18.5.4 Rack-topology stability — the move-family conjunct

**The move family, derived rather than listed.** A `CALL` on receiver type `R` is a **move-family call**
iff its contract carries `anchor_net_effects` mapping some field in `receiver_state[R].anchor_fields`
to `"EMPTY"` or `"HELD"`. These are P6's derived net effects of the move-family increment's own
`_resource_pickup` typestate. In the shipped 1.0 table this selects exactly
**`{drop_resource, move_lid, move_plate, move_resource, pick_up_resource}`** on `LiquidHandler`, which
is a superset of the owner's three. Every other `LiquidHandler` entry carrying `anchor_net_effects`
maps both fields to `"TOP"`. That applies to `_format_param`, `aspirate`, `consolidate_tip_inventory`,
`dispense`, `drop_tips`, `move_tips`, `pick_up_tips`, `transfer` and `use_tips`, all read from
`plr-sema/data/derived_contracts.json` this session. `"TOP"` there is P6 declining over unresolved
delegates. It does not mean the method moves resources, so it does not count. Using the owner's three
literal names instead would have hand-typed method names in `check/` and missed a direct
`pick_up_resource`/`drop_resource` call.

**The derived family is pinned, not trusted (r1, M5).** AC-18.11(i) asserts that the family computed
from the **shipped** `plr-sema/data/derived_contracts.json` equals exactly
`{drop_resource, move_lid, move_plate, move_resource, pick_up_resource}`. A P6 regression that
decays, say, `move_lid` to `"TOP"` would silently drop it from the family and make `:338` unsound, so
it must fail CI instead. Treating `"TOP"` as not disturbing is **fail-open**, and A-RACK-STATIC's
row (§18.5.5) now says so.

**A `CALL` is topology-disturbing** iff any of the following holds:

- (a) it is a move-family call;
- (b) its `receiver_type` is `None`;
- (c) it has no contract (`unsupported_tool`);
- (d) its `receiver_type` differs from the receiver type of the call being checked. Only calls on the
  same liquid-handler type are presumed topology-neutral; a call on a deck, rack or any other resource
  receiver may place a lid.

**Normative (`rack_topology_stable`).** `check_ir` pre-scans `bytecode.instructions` **once** and keeps
the pcs of the `CALL`s that are candidates for disturbance. For the `CALL` at pc `p`, visited with
`inside_loop = L` (`check_ir`'s own flag, `plr-sema/src/plr_sema/check/__init__.py:751-769`):

> `rack_topology_stable(p)` is true iff (i) no `CALL` at a pc `q < p` is topology-disturbing relative to
> `p`'s receiver type, **and** (ii) if `L`, no `CALL` anywhere in the stream is topology-disturbing
> relative to it.

Clause (ii) exists because inside a loop a later pc runs before `p` on the next iteration. It is
deliberately coarse, since any loop plus any disturber anywhere means a decline. Branch arms need no
special case. A disturber in an earlier arm has a lower pc and forces a decline. A disturber in the
sibling arm has a higher pc, and the two arms cannot both run in one pass. The value is threaded to the
site rule as two keywords, `rack_topology_prefix_ok` / `rack_topology_loop_ok: bool | None = None`
(clauses (i) and (ii) separately, r2, C4), on `evaluate_guard` and
same-named `_Ctx` fields (`plr-sema/src/plr_sema/check/predicate.py:244-289`), set from `process_call`
through `_findings_for_call` and `_findings_for_guards`
(`plr-sema/src/plr_sema/check/__init__.py:409-479`). Every other guard ignores it.

The pre-scan is exported as a pure function (r1, m3):

```
rack_topology_disturbers(instructions, contracts, receiver_states) -> dict[int, tuple[str | None, frozenset[str]]]
```

It maps each `CALL` pc to that call's `(receiver_type, classes)`, where `classes ⊆
{"move_family", "receiver_type_none", "no_contract"}`. Clause (d) cannot be precomputed, because it is
relative to the checked call's receiver type. The caller evaluates it by comparing receiver types.
**How the measurement script uses it (r2, D-2).** The script uses `rack_topology_disturbers`, together
with `tip_racks_decline_reason`, to compute the **analyzer-side** decline reason for each `:338`
finding. It does **not** use it for the independent side of the M8 consistency term, which is a
separate scan (§18.9).

**The static stream includes the prepended `setup` call.** `calls_from_plr_kwargs` puts
`{"method": "setup", …}` first (`plr-sema/eval/oracle_common.py:649-651`). `LiquidHandler.setup` has no
`anchor_net_effects` entry, and it has a contract and the same receiver type, so it is not a disturber
(this closes OI-14).

### 18.5.5 The residual assumption, named: A-RACK-STATIC

The conjunct removes the obvious frame violation, a move before the pickup. It does not prove that
**no other same-receiver `LiquidHandler` method** changes a rack's lid or stack position. This document
names that as an assumption rather than leaving it buried. **Adding a named assumption was a user
decision in increment 7 (D2).** L3 implies this one, but OI-2 asks the owner to confirm it
explicitly.

| id | assumption | why it is needed | what breaks if it is false |
|---|---|---|---|
| **A-RACK-STATIC** (added 260929, §18.5.5; r1) | between the observation capture point and an operation, a `TipRack`'s lid and stack position change only through a topology-disturbing call (§18.5.4) | the `:338` site rule reads a pre-execution observation (§18.5.2) | a non-move-family `LiquidHandler` method that places a lid on, or stacks onto, a tip rack before a pickup gives `SAFE` at `:338` where PLR raises `ValueError`, which is unsound. **Known fail-open edge (r1, M5):** a method whose P6 net effect is `"TOP"` (P6 declined) is treated as non-disturbing. The shipped-table family pin (AC-18.11(i)) catches a known member decaying to `"TOP"`, but not an unknown method that moves resources while being `"TOP"`. **Checked on the corpus** by the unmodified tier-1 fence, and given one **hand-built** adversarial witness per disturber class in AC-18.11(d)(e)(f). The in-run m3 mutant (§18.9) exercises only the **observation** conjunct, not this frame condition (r2, C16) |

| **A-CALLBACK-INERT** (added 260929, PLR 1.0 tip-effect increment §18.4.3, owner ruling on OI-21) | a state-update callback reached from a head tracker's `commit` does not write any head tracker's tip state | the §18 effect derivation does not follow `commit`'s `self._callback()`, because `_callback` is an instance attribute, not a method, so any tracker write made through a callback would be invisible to it | **checked at the pin** (AC-18.2(q)): every `register_callback` argument in `LiquidHandler` is `self._state_updated`, which resolves to `Resource._state_updated`, a notifier that only passes `serialize_state()` to its registered callbacks. **Assumed, not checkable from PLR source:** the user-registered downstream state-update callbacks do not write a head tracker. If one does, a method judged `UNTOUCHED` or `HAS_TIP`/`NO_TIP` could leave a different tip state than the walk records, and both a false `SAFE` and a false `WILL_FAIL` become possible. Follow-up, backlog #5661 (outside #5622): any analysed protocol that registers its own state-update callback makes tip state `UNKNOWN`, which turns this assumption into a check |

**Both rows are added to increment 1's §10.6.3 table by T61, copied verbatim from this table**, so that
table goes from five rows to **seven**. The same task moves
`test_ac_16_13_a_deck_object_assumption_table_has_five_rows`
(`plr-sema/tests/test_check_graph.py:1534-1547`) to seven. The rows are deliberately **not** added to
increment 1 by the spec finalization itself: doing so before T61 would leave that test red on `main`
from the moment the spec merged.

### 18.5.6 HM-26 bookkeeping — a ceiling change, not a row

HM-26 (`plr-sema/src/plr_sema/_hand_maintained.py:1238-1289`) is "site-keyed semantic models of NAMED
PLR function bodies". The new rule is exactly that kind: keyed on one PLR qualname's own guard, and it
hand-models what `_check_tip_racks_available`'s body checks. The fourth rule is therefore **one further
unit on HM-26**. `declared` goes **3 → 4**; the measure `_measure_hm26`
(`plr-sema/src/plr_sema/_hand_maintained.py:556-573`) is `len(D6_SITE_RULES)` and moves on its own.
`live_rows()` stays 25 and `BUDGET_CAP` stays 25.

- **No headroom is added**, so `declared == live`, following HM-26's own T48/T49 precedent rather than
  §9.1's live+2 rule. A spare unit would pre-authorise a fifth site rule without an argument.
- **The row's `what` and `breaks_when` are rewritten** to name the fourth rule, its three conjuncts and
  the new observation field. The rewrite states that the rule also stops dispatching if PLR changes
  the guard text, raising class or qualname, which `test_d6_site_rule_keys_each_match_exactly_one_site`
  turns red.
- **The loud half is a published count**, following increment 7's precedent for HM-26:
  `n_tip_racks_decided = {total, attempted, predicted_target}` in the oracle replay report, beside
  `n_assert_resources_decided`. The predicted target is **288** *(reasoned from the 288-finding
  `guard_predicate_unparsed` delta, §18.1)*.
  - `attempted` is the number of executed operations carrying a `:338` finding.
  - `total` is how many of those were decided `SAFE`.
  - These are the sidecar's `real_n_tip_racks_attempted` / `real_n_tip_racks_decided` on the `real`
    arm (r2, C13).
  - **The per-conjunct decline attribution is not published by `oracle_replay`.** Under ruling D-2 it
    is computed by T63's measurement script (§18.9), so nothing is threaded through `check/`'s report
    for it.
- Tests move in the same commit. In `test_hm26_d6_spend_is_one_new_row_not_an_overrun`
  (`plr-sema/tests/test_hand_maintained_ratchet.py:373-391`), `declared` and live go 3 → 4. In
  `test_d6_site_rule_keys_each_match_exactly_one_site` (`plr-sema/tests/test_check_graph.py:1567-1579`),
  the count goes 3 → 4. The latter test's `site.file.endswith("liquid_handler.py")` clause still holds.

---

## 18.6 V5 — unchanged, and what now flows through it (L5)

`_apply_v5` (`plr-sema/src/plr_sema/check/volumestate.py:547-588`) is not edited. Its behaviour changes
only because its input `channel_effect` changes:

- `pick_up_tips` (`HAS_TIP`) and `drop_tips` (`NO_TIP`) leave the third bullet. They now take V5's
  modelled first and second bullets, so across ordinary protocols `tips_dirty` stays false and
  volume-family precision returns.
- `load_state` and `update_head_state` (`widen`) are departures. With no resolvable channel set, they
  set `tips_dirty` and call `reset_tip_cells`. The channel set is unresolvable because
  `channels_for_call` returns `None` when a call has neither the channel keyword nor a channel-default
  parameter, and neither method has either (`plr-sema/src/plr_sema/check/tipstate.py:303-311`). r1
  (m9) adds a check-level fixture to AC-18.5 that shows this rather than asserting it.

The amendment's reset (`plr-sema/src/plr_sema/check/volumestate.py:204`, `reset_tip_cells`) stays on
every path where it fires today. The two tests that pinned the 1.0 soundness hole,
`test_ac_14_5_e_retip_dirty_tip_never_safe` (in `plr-sema/tests/test_check_graph.py`) and the file
`plr-sema/tests/test_tips_dirty_cost.py`, must stay green through the modelled path. That is AC-18.5,
and T62's gate runs both files (r1, M9).

---

## 18.7 Registry, vocabulary and wire-format impact

- **HM-26: 3 → 4** (§18.5.6).
- **HM-25: 12 → 13 — one collective unit, and this document's position rather than a settled fact.**
  R-A recognises a getter shape (`return self.X`, recursing through properties). R-C(2) recognises a
  signature shape (a constructor binding no `None`-default parameter). Both are patterns over how PLR
  is written, and HM-25 books exactly that kind of thing: P2's anchor property is its first entry. R-B's
  binding and argument table is a Python-language construct. It maps positions to parameters and
  literal kinds to classes, which is §16.9's accepted "costs nothing" argument for the delegate→caller
  map. The spec still books it into the **same** unit, because R-A and R-B are one mechanism and
  either one alone recovers nothing.
  - **Failure profile: loud.** If R-A stops matching, `effects` empties. AC-18.8's structural invariant
    and AC-18.7's cross-pin fixture both fail in CI. That is HM-25's criterion, not HM-24's.
  - **The unit's probe.** `_measure_hm25` gains a thirteenth probe that imports the R-A/R-B/R-C(2)
    implementing symbols and exercises them against a synthetic three-hop chain, asserting the derived
    `HAS_TIP`. **If the measured count is not exactly 13, T57 STOPS and asks, per the row's standing
    contingency.**
  - **Owner ruling 260929 (OI-4): book HM-25 12 → 13.** A zero-cost alternative was considered and
    declined: it argued that R-A/R-B extend P4, which has never been on a registry row. It was declined
    because R-A and R-C(2) are patterns over how PLR is written, which is exactly the class of fact
    whose silent breakage caused this regression. The booking adds no row and does not change
    `BUDGET_CAP`.
- **R-E: zero cost.** It is a set difference over P1a/P2 outputs, with no pattern, no literal and no
  table.
- **The move-family predicate of §18.5.4: zero cost.** It reads P6's already-published
  `anchor_net_effects` and introduces no pattern or name. The strings `"EMPTY"`/`"HELD"` are this
  analyzer's own derived vocabulary.
- **`REASON_VOCABULARY`: unchanged.** Declines reuse `guard_predicate_unparsed`. Unresolved effects
  surface as `channel_state_unknown` through the existing widen path.
- **Wire: unchanged.** `Verdict`, `Finding`, `AnalysisReport`, `SCHEMA_VERSION = 1`, and the
  `derived_contracts.json` `schema_version` 1 are all untouched. New keys are additive and ignored by
  `check/`. The regenerated table changes the table digest, so cache entries cool by design, as at
  T41.
- **The AST literal scan (increment 1's AC-10.9)** must stay green. Nothing in §18 introduces `"TipTracker"`, `"has_tip"`,
  `"_pending_tip"`, `"head"` or `"_carried"` as a string constant in `plr-sema/src/`, because
  `_carried` is derived. The site-rule key tuple and the observation name `"tip_racks_available"` are
  literals of the same class as the existing D6 keys and `"deck_resources_verified"`, which is HM-26's
  own surface.

---

## 18.8 Drift tests

These are the tests that make the next PLR bump fail **in CI** rather than in a precision number. None
of them lists methods by hand, except as the **generated** content of the baseline fixture.

1. **Cross-pin baseline fixture.**
   - A committed generator, `plr-sema/scripts/gen_channel_effect_baseline.py`, reads a
     `derived_contracts.json`, either `--from PATH` or `--from-git-rev REV` via `git show`. It writes
     `plr-sema/tests/fixtures/channel_effect_baseline.json`, which contains
     `{source_rev, plr_pin, channel_effects: {"<Class.method>": <value>, …}, intended_divergences: {…}}`
     and lists **every** contract carrying a `channel_effect`.
   - `--rebase` regenerates `channel_effects` **and refuses** unless `intended_divergences` is supplied
     explicitly on the command line. It prints every key whose value moved, so a rebase is a reviewed
     act and never a silent one.
   - The first generation reads the **old-pin** table. That is the last commit whose table stamp has
     `plr.hash` `dd79c4c89…`, and T59 records the rev it used in `source_rev`. It declares exactly one
     intended divergence, `"LiquidHandler.load_state": {"old": "HAS_TIP", "new": "widen", "reason": "L1 (§18.4.4)"}`.
   - The test runs over the current table, with absence treated as a value (r1, M11):
     - **Old keys.** Every baseline key must still exist (a **vanished key fails**) and carry the same
       value, unless it is listed in `intended_divergences`, in which case it must carry the declared
       `new`.
     - **New keys.** A contract that carries a `channel_effect` at 1.0 but is **absent from the
       baseline** fails, unless it is listed with `"old": "absent"`.
     - **The counter.**
       `baseline_divergences = |{k ∈ keys(baseline) ∪ keys(current) : value_baseline(k) ≠ value_current(k)}|`,
       where a missing key has the value `absent`. The test asserts
       `baseline_divergences == len(intended_divergences)`, and prints `parity = matched/total` over the
       union of keys.
   - **Any other divergence fails, and T59 must adjudicate it in this document's implementation record.
     It must not rebase it away.** The old-pin expectation is now derived rather than unknown (r1,
     OI-9). The fixture itself comes from the old-pin **artifact** through `git show`, and it — not the
     derivation below — is the authority.
2. **Structural invariants** are checked on the regenerated table, for every receiver in
   `receiver_state`:
   - (a) `effects` has at least one `HAS_TIP` and at least one `NO_TIP` value whenever some contract
     entry on the receiver has a bridge, in §18.4.4's sense (r1, m8);
   - (b) `entry_reset` present ⇒ (a) holds, which is L7's invariant;
   - (c) the gap ledger's `tip_state` families `tip_loading`, `tip_dropping` and `tip_requiring` are
     non-empty for `LiquidHandler`;
   - (d) the four new keys of §18.4.8 are present with the declared types;
   - (e) no method bridged from any receiver begins with `_`;
   - (f) **moved to a pin-scoped fixture (r1, m8).** "`effects_max_depth ≥ 1` whenever
     `effect_backing_fields` is non-empty" is true of 1.0's shape only. A future PLR that writes a
     backing field directly at depth 0 would break it legitimately. It is therefore asserted only as
     part of AC-18.2's pin values (`effects_max_depth == 2`), not as a structural invariant.
3. **Behavioural oracle, against real PLR.** Drive a holder-less `pylabrobot.legacy.tip_tracker.TipTracker`
   through each public method `m` in `effects`:
   - Construct the tracker in the pre-state its own guard admits: `NO_TIP` for a `HAS_TIP` effect, and
     `HAS_TIP` (via `add_tip(…, commit=True)`) for a `NO_TIP` effect.
   - Call `m` with a real `Tip` wherever it needs one, then commit.
   - Assert `has_tip` after the call equals the derived polarity.
   - For every `m` in `effects_unresolved`, exhibit **both** outcomes. For `load_state` that means
     `{"tip": None, "pending_tip": None}` gives `has_tip is False`, and a serialized tip gives
     `has_tip is True`. This is L1's witness that "unresolved" is genuinely state-dependent.
   - Assert that a fresh tracker has `has_tip is False`, which is R-C's `NO_TIP`.
   - **Holder-full polarity (r1, m11).** Repeat the `effects` polarity checks on a tracker built with a
     real `TipSpot` holder. Every method's `has_tip` after the call must equal the same derived
     polarity. This closes OI-5's polarity half empirically: the holder path assigns and unassigns the
     spot's child (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:88-96`).
   - **Rollback after an uncommitted `add_tip` (r1, m11).** On a `NO_TIP` tracker, call
     `add_tip(tip, commit=False)` then `rollback()`, and assert `has_tip is False`. This bounds OI-6: it
     shows what COPY's identity reading abstracts away, namely that `rollback` does change `has_tip`
     mid-transaction and is identity only at operation boundaries.
   - **Import-order caveat (from the recon, not re-verified):** import `pylabrobot.resources` before
     `pylabrobot.legacy.tip_tracker`, otherwise a circular import fails. The test does this explicitly
     and says why in a comment.
   - The test must **not** be skipped when PLR is importable. If it cannot run, it fails.
4. **Synthetic derivation controls.** Positive and negative controls over hand-built `ast.ClassDef`
   fixtures, listed in AC-18.2. This is the "verify the instrument on synthetic ground truth" step for
   the derivation. Every negative control must be able to fail, and each is written so that removing
   the rule it guards turns it red.

---

## 18.9 Measurement plan — a NEW pre-registered sidecar

The sidecar is **written and committed before the run** (T63, first step). It is not created by this
document. It pre-registers a new script, `plr-sema/eval/plr10_tip_effects_measure.py`. That script
reuses `plr10_characterize.py`'s two-arm structure unchanged (`real` and `all_safe`, the same seam, the
same `oracle_replay.main`), and adds these (r1 additions marked):

1. a per-method read of `scope_verdict_by_method`;
2. one `tip_mutants.py` run for the direction controls: m1, m2, p3a, and the **new m3 lidded-rack
   class** (r1, M7). **The script reads `tip_mutants`'s report JSON, never its exit code** (r2, C1).
   `main` returns 1 on any hard violation
   (`plr-sema/eval/tip_mutants.py:581-583`), and that includes the p3a floor failure that is
   known and out of scope (D-1);
3. one `volume_mutants.py` run for the v1 class (r1, M7), also read from its report JSON;
4. reads of the regenerated contracts;
5. the baseline-parity numbers from §18.8(1), with the M11 counter;
6. **an independent IR scan (r1, M8).** For every planned `pick_up_tips` operation, the script decides
   from its own code whether a topology disturber precedes it (clause (i)) and whether the loop clause
   (ii) applies. It uses the §18.5.4 definition, written again in the script **without importing
   `rack_topology_disturbers` or `tip_racks_decline_reason`**;
7. **the analyzer-side `:338` decline attribution (r2, C4 and D-2 option (B)).**
   - During the `real` arm, the script installs `oc.FINDINGS_SINK` and `oc.LOWERED_SINK`,
     chain-composed and restored in `finally`, on the precedent at `plr-sema/eval/t30_measure.py:663-670`.
     This captures each row's lowered bytecode and its findings.
   - **The producers of the inputs (r3, X2).** Neither sink carries `env`. Patching `oc.run_runtime`
     would intercept nothing, because `oracle_replay` imports that function by name. And `inside_loop`
     is internal to `check_ir`. So the inputs come from three places:
     - **`env` observation members.** The script wraps **`oc.observation_env_members`**, which
       `run_static_calls` calls as a module global once per row, unconditionally, before lowering
       (`plr-sema/eval/oracle_common.py:1003`). The wrapper is chain-composed: it calls the original,
       appends its return value to a list, and returns it unchanged. It is restored in `finally`. The
       list is correlated with `FINDINGS_SINK` / `LOWERED_SINK` **by position**, and the script
       hard-asserts a four-way length invariant (eligible rows, findings, lowered, env), extending
       the three-way precedent at `plr-sema/eval/t30_measure.py:677`. A mismatch raises, the run produces no `result.json`, and
       the outcome is FAIL by construction. **`run_static_calls` is unchanged.**
     - **Topology.** The script runs `rack_topology_disturbers` over each row's lowered bytecode, the
       `bc` that `LOWERED_SINK` delivers, and derives `rack_topology_prefix_ok` at the operation's pc
       from it.
     - **`rack_topology_loop_ok`.** The script **hard-asserts that no lowered tier-1 stream contains a
       loop instruction**: no `ir.Loop` instance anywhere in `bc.instructions`. A synthetic
       `has_loops` wrap also lowers to an `ir.Loop`, preceded by `Widen(reason="has_loops")`, and the
       same check catches it. Under that assertion `rack_topology_loop_ok` is `True` for every
       operation, and `n_338_declined_topology_loop = 0` holds **by construction on this benchmark**,
       consistent with its "predicted 0" report. If a loop ever appears, the assertion fails with the
       row id and pc. The script then raises, no `result.json` is written, and the outcome is
       FAIL-with-cause, never a silent `loop_ok = True`. Extending the script to compute clause (ii) is
       then a named follow-up.
   - For each planned `pick_up_tips` operation that carries a `:338` finding, the script calls the
     **same** exported `tip_racks_decline_reason` with these inputs and the guard's `kind`.
   - **Nothing is threaded through `check/`.**

**The m3 lidded-rack mutant (r1, M7; revised in r2, C5/C6/C7/C16 and D-4).** This is a new mutator,
`make_m3_lid_on_tip_rack`, in `plr-sema/eval/tip_mutants.py`, with expected exception `ValueError`.

- **What it builds.** For each `pick_up_tips` base, it adds the base's pickup rack to the row layout's
  new `DeckLayout.lidded_tip_racks` (owned by T60, §18.5.2). `build_setup` then lids that rack with a
  real `Lid`, so the observation is `false` and the site rule must decline at its `"observation"`
  conjunct.
  - **The rack name (r3, minor 4)** is the base name of the first pickup's `at` reference: the part
    before the first `.`/`[`, the same split as `deck.py`'s `_base_name`.
  - **A base whose `deck_layout` is `None` or absent** gets a fresh layout carrying only
    `lidded_tip_racks`. `DeckLayout.merged()` combines it with the harness default.
  - A base with no `pick_up_tips`, or whose `at` does not parse, returns `None`, which is counted in
    `n_construction_skipped`.
- **The Lid (r3, closing OI-24).** `build_setup` sizes each `Lid` to its rack's own `size_x`/`size_y`.
  PLR's placement raises only if the rack already has a lid, or if the lid is undersized beyond
  `LID_UNDERSIZE_TOLERANCE` (`external/pylabrobot/pylabrobot/resources/lid.py:104-122`, verified).
  `location` is optional there. T60 uses a **nonzero `nesting_z_height`** and a **deck-unique lid
  name**.
- **m3b is DROPPED (D-4).** The harness has no real `Lid` source to move, and moving a `Plate` does not
  set `rack.lid`.
- **Honest scope (C16).** m3 is an in-run falsifier of a wrong `:338` `SAFE` **through the observation
  conjunct only**. The topology conjunct is witnessed by AC-18.11(d)(e)(f), which are unit and
  hand-built fixtures, not by the run.
- **Construction.** Bases that cannot be constructed count in `n_construction_skipped`.
- **Hard terms.**
  - `static_338_safe_on_m3 = 0`.
  - `runtime_raised_m3 > 0`, where `runtime_raised_m3` counts m3 rows whose runtime raised **at the
    `:338` site**. That means the `ValueError` message contains `"something is stacked on top of it"`,
    or its `error_frames` include `_check_tip_racks_available`, **at the pickup index**
    (`_first_pickup_index`). A `ValueError` from `pick_up_tips`'s position-uniqueness check does not
    count.
  - **If m3 cannot be built at all, `runtime_raised_m3 = 0`, and that gives FAIL, not MARGINAL** (C5).
- **Reported, not gated.** `m3_attempted` (C7).

**Mutant floors (revised in r2, C1).**

- **The denominators, redefined.** `mX_attempted := n_raised_as_expected` and
  `mX_achieved := static_verdict_at_raising_index.will_fail`.
  - m1 removes a pickup, so some mutants raise nothing downstream.
  - Increment 7's run had m1 at `n_ran` 289, raised 199, will_fail 199 (orchestrator-verified in
    `tip_mutants_260909_inc7.json`). On r1's `n_ran` denominator even a perfect analyzer would have
    scored 199/289, and `PASS` was unreachable.
- **The pre-registered floors** are `m1_attempted >= 150` (inc7 had 199), `m2_attempted >= 200` (289)
  and `v1_attempted >= 50` (67), each with achieved == attempted.
- **p3a is REPORTED-ONLY (ruling D-1).**
  - `p3a_attempted` and `p3a_achieved` are published, and no value is pre-registered.
  - Increment 8 measured p3a at 0/178 with `floor_met = false` at the old pin (the `:2070` NO-GO,
    out of scope per §18.13), and its 1.0 baseline is unmeasured.
  - p3a's criteria (i) and (ii) stay hard, through `mutants_unsound` and `mutants_criterion_ii`.
  - `mutants_gate_passed` is replaced by `mutants_hard_violations_excl_p3a_floor = 0`. Its source is
    the report's `hard_violations` list, minus the single entry for p3a's floor.

The inputs are the **same four paths the `fd63e9cd` run used**, read off its record, not retyped from
memory:

```bash
bth sql "SELECT id, command FROM runs WHERE id LIKE 'fd63e9cd%'"
```

The invocation is `bth run --project-slug <fd63e9cd's slug> -- uv run --no-sync python plr-sema/eval/plr10_tip_effects_measure.py …`.
It uses **`bth`, not `uv run bth`**, and the wrapped form, so the project venv is used. The run is
verified **by its record**: `bth compact` first, then `bth sql` on `status, outcome, exit_code`. It is
never verified by exit code or console text.

**Preemption-safe and resumable by design (owner rule, finalization 260929).** This governs how the
run is **scheduled**. It **never** changes the `[outcomes]` criteria.

- **Units of work.** There are seven, each a separate unit: the two arms (`real`, `all_safe`) and the
  five mutant classes (`m1`, `m2`, `p3a`, `m3`, `v1`).
  - To run the `tip_mutants` classes one at a time, T63 adds a `--classes` filter to
    `tip_mutants.py`; the default (all classes) keeps its current behaviour. `v1` is
    `volume_mutants.py`'s only class.
  - The `real` unit's output also persists its three sink captures (findings, lowered `bc`, and the
    wrapped `observation_env_members` list). The `:338` attribution and the independent scan can then
    be recomputed from disk without re-running the arm.
- **Persist on completion.** Each unit writes its own output file under the run's `--out-dir`
  (`units/<unit>.json`) as soon as it finishes, followed by a completion stamp
  (`units/<unit>.stamp.json`). The stamp records:
  - the unit name;
  - the input hashes: sha256 of `plr-sema/data/derived_contracts.json`, of each corpus file, of the
    sidecar input and of each crosscheck file, plus the git `HEAD` sha;
  - the sha256 of the unit's output file.

  The stamp is written only after the output file is fully written and flushed.
- **Resume.** On re-invocation with the same `--out-dir`, a unit is **reused** only when both hold:
  its stamp's input hashes equal the current run's, and its output file's sha256 equals the stamp's.
  Otherwise the unit is **recomputed**. `result.json` carries a `units` block recording, for each
  unit:
  - `reused` or `computed`;
  - the source path;
  - the input hashes and the output sha256.

  This block is a provenance record, outside `[result_schema]`, so the outcome conditions are
  untouched.
- **Bounded blast radius.**
  - Each unit runs in **its own subprocess with its own timeout**, and there is **no whole-run
    timeout**.
  - A unit that times out or crashes leaves every completed unit's files intact, and the run reports
    that unit as `incomplete`.
  - All seven units are required. If any is incomplete, **no `result.json` is written**, which is
    FAIL by construction, the same way as the length-invariant mismatch in item 7.
  - A re-invocation then recomputes only the incomplete unit or units.
- **Per-unit timeouts** are a judgement, not derived. They are set at roughly 10× the characterisation
  run's wall-clock: `fd63e9cd` took about 148 s for its `real` arm (`wall_elapsed_s` in
  `outputs/plr-sema/plr10_char_260929/real.oracle_replay.json`).
  - `real` and `all_safe`: **30 min** each.
  - Each `tip_mutants` class (`m1`, `m2`, `p3a`, `m3`) and `v1`: **30 min** each. They have not been
    timed at 1.0.
  - A timeout is recorded with the unit name and elapsed time. It is never retried inside the same
    invocation.

**The sidecar, as it must be committed** (`plr-sema/eval/plr10_tip_effects_measure.bth.toml`):

```toml
# bathos sidecar for plr-sema/eval/plr10_tip_effects_measure.py
# (backlog #5622, task 260929_plr-1.0-migration, spec 260929 §18.9).
# PRE-REGISTERED before any run. Baseline: run fd63e9cd (1.0 floor, 0 scope-SAFE),
# dd79c4c89 ledger unknown_ledger_260911_volwire (216 scope-SAFE, all pick_up_tips).
# No number from the #5622 recon's exploratory scripts is evidence for or against this hypothesis.
#
# SCHEDULING (owner rule 260929: preemption-safe and resumable; scheduling only, never [outcomes]):
#   Seven units, each in its own subprocess with its own timeout and no whole-run timeout:
#   real, all_safe (30 min each) and m1, m2, p3a, m3, v1 (30 min each). The timeouts are a judgement,
#   about 10x fd63e9cd's ~148 s real-arm wall-clock.
#   Each unit persists units/<unit>.json as it completes, then units/<unit>.stamp.json holding
#   {unit, input sha256s (derived_contracts.json, corpus files, sidecar input, crosschecks, git HEAD),
#   output sha256}.
#   Re-invocation reuses a unit only if its input hashes AND its output sha256 match; otherwise it
#   recomputes. result.json records per unit: reused|computed, source path, hashes.
#   Any required unit incomplete (timeout or crash) => no result.json => FAIL by construction.

[experiment]
hypothesis = "With spec §18's derived rules (R-A..R-E, L1's effects_unresolved->widen) and the fourth D6 site rule at :338, the analyzer at PLR 1.0.0b1 (a) stays sound and total on the frozen 343-row tier-1 benchmark with a live negative control; (b) fires tip-state WILL_FAIL at the raising index in m1/m2 on every row that raised as expected, above pre-registered floors, never emits a WILL_FAIL where the simulator ran clean in any class (p3a included), keeps the v1 volume direction control, and never calls :338 SAFE on an m3 lidded-rack mutant that raised at :338; (c) recovers pick_up_tips scope-SAFE from 0 to at least 205 of the 216 it had at dd79c4c89, and no other method reaches scope-SAFE; (d) publishes LiquidHandler.load_state channel_effect = 'widen' with exactly one baseline divergence, which is the only intended one; (e) changes no benchmark counter through load_state, which the tier-1 vocabulary never calls; and (f) every :338 decline on a planned pick_up_tips is attributed to exactly one conjunct, and the topology-prefix declines agree with an independent IR scan. p3a's floor is reported, not predicted."
stage_name = "tip_effect_increment"
novel = false

# HARD block H (both pass and marginal require all of it; fail is exactly NOT H):
#   control_fires = true AND real_unsound = 0 AND real_unsound_scoped = 0 AND real_totality_violations = 0
#   AND real_check_graph_exceptions = 0 AND real_rows_setup_error = 0 AND real_rows_executed = 343
#   AND mutants_unsound = 0 AND mutants_criterion_ii = 0 AND mutants_hard_violations_excl_p3a_floor = 0
#   AND static_338_safe_on_m3 = 0 AND runtime_raised_m3 > 0
#   AND m1_will_fail_fired = true AND m2_will_fail_fired = true AND load_state_channel_effect = 'widen'
#   AND baseline_divergences = baseline_intended_divergences AND n_ops_load_state = 0
#   AND n_338_declined_unattributed = 0 AND n_338_safe_with_reason = 0
#   AND n_338_declined_topology_prefix = n_pickups_with_preceding_disturber_indep
#   AND real_pick_up_tips_scope_safe >= 123
# EXTRAS X (pass requires all; marginal is H AND NOT X):
#   m1_achieved = m1_attempted AND m1_attempted >= 150 AND m2_achieved = m2_attempted AND m2_attempted >= 200
#   AND v1_gate_passed = true AND v1_achieved = v1_attempted AND v1_attempted >= 50
#   AND baseline_intended_divergences = 1 AND n_338_declined_topology_loop = 0
#   AND real_pick_up_tips_scope_safe >= 205 AND real_pick_up_tips_scope_safe <= 216
#   AND real_n_operations_scope_verdict_safe = real_pick_up_tips_scope_safe
# Exclusive and exhaustive by construction: pass = H AND X, marginal = H AND NOT X, fail = NOT H.
# (H and X are written out in full in each condition below; these comments are for the reader only.)

[outcomes.pass]
condition = "control_fires = true AND real_unsound = 0 AND real_unsound_scoped = 0 AND real_totality_violations = 0 AND real_check_graph_exceptions = 0 AND real_rows_setup_error = 0 AND real_rows_executed = 343 AND mutants_unsound = 0 AND mutants_criterion_ii = 0 AND mutants_hard_violations_excl_p3a_floor = 0 AND static_338_safe_on_m3 = 0 AND runtime_raised_m3 > 0 AND m1_will_fail_fired = true AND m2_will_fail_fired = true AND load_state_channel_effect = 'widen' AND baseline_divergences = baseline_intended_divergences AND n_ops_load_state = 0 AND n_338_declined_unattributed = 0 AND n_338_safe_with_reason = 0 AND n_338_declined_topology_prefix = n_pickups_with_preceding_disturber_indep AND real_pick_up_tips_scope_safe >= 123 AND m1_achieved = m1_attempted AND m1_attempted >= 150 AND m2_achieved = m2_attempted AND m2_attempted >= 200 AND v1_gate_passed = true AND v1_achieved = v1_attempted AND v1_attempted >= 50 AND baseline_intended_divergences = 1 AND n_338_declined_topology_loop = 0 AND real_pick_up_tips_scope_safe >= 205 AND real_pick_up_tips_scope_safe <= 216 AND real_n_operations_scope_verdict_safe = real_pick_up_tips_scope_safe"
is_residual = false
decision = "Precision at PLR 1.0 is recovered to within 5% of the dd79c4c89 headline with soundness intact, every gated direction control at floor, every :338 decline attributed, and the instrument live. Close #5622's measurement; publish the per-conjunct decline counts and the reported-only p3a and m3 counts beside the result."
reasoning = "The 216 at 1.0 are blocked by exactly {:338, :758, tip_tracker:153}; R-A..R-C restore the last two by the old pin's own mechanism, the site rule decides the first. The only decline paths the old pin did not have are an observed lidded/stacked rack and a preceding topology disturber; a loss of at most 11 (5%) is a judgement, stated as one."

[outcomes.marginal]
condition = "control_fires = true AND real_unsound = 0 AND real_unsound_scoped = 0 AND real_totality_violations = 0 AND real_check_graph_exceptions = 0 AND real_rows_setup_error = 0 AND real_rows_executed = 343 AND mutants_unsound = 0 AND mutants_criterion_ii = 0 AND mutants_hard_violations_excl_p3a_floor = 0 AND static_338_safe_on_m3 = 0 AND runtime_raised_m3 > 0 AND m1_will_fail_fired = true AND m2_will_fail_fired = true AND load_state_channel_effect = 'widen' AND baseline_divergences = baseline_intended_divergences AND n_ops_load_state = 0 AND n_338_declined_unattributed = 0 AND n_338_safe_with_reason = 0 AND n_338_declined_topology_prefix = n_pickups_with_preceding_disturber_indep AND real_pick_up_tips_scope_safe >= 123 AND (m1_achieved != m1_attempted OR m1_attempted < 150 OR m2_achieved != m2_attempted OR m2_attempted < 200 OR v1_gate_passed = false OR v1_achieved != v1_attempted OR v1_attempted < 50 OR baseline_intended_divergences != 1 OR n_338_declined_topology_loop != 0 OR real_pick_up_tips_scope_safe < 205 OR real_pick_up_tips_scope_safe > 216 OR real_n_operations_scope_verdict_safe != real_pick_up_tips_scope_safe)"
is_residual = false
decision = "Sound, instrument live, every :338 decline attributed and the topology prefix reconciled, but a floor or prediction missed: a direction control under its floor, a second intended baseline divergence, a loop-clause decline, recovery below 205, or an unpredicted SAFE population. Publish every n_338_declined_* counter and the per-class mutant counts; attribute every miss to a named rule; the owner decides whether a finer conjunct or a harness fix is worth an increment. No precision claim beyond the measured number."
reasoning = "Every soundness and accounting term held, so what missed is precision or coverage, not correctness."

[outcomes.fail]
condition = "control_fires = false OR real_unsound > 0 OR real_unsound_scoped > 0 OR real_totality_violations > 0 OR real_check_graph_exceptions > 0 OR real_rows_setup_error > 0 OR real_rows_executed != 343 OR mutants_unsound > 0 OR mutants_criterion_ii > 0 OR mutants_hard_violations_excl_p3a_floor > 0 OR static_338_safe_on_m3 > 0 OR runtime_raised_m3 = 0 OR m1_will_fail_fired = false OR m2_will_fail_fired = false OR load_state_channel_effect != 'widen' OR baseline_divergences != baseline_intended_divergences OR n_ops_load_state != 0 OR n_338_declined_unattributed != 0 OR n_338_safe_with_reason > 0 OR n_338_declined_topology_prefix != n_pickups_with_preceding_disturber_indep OR real_pick_up_tips_scope_safe < 123"
is_residual = true
decision = "Stop and attribute the cause through the published counters before any claim. Soundness/instrument: a soundness counter, criterion (ii) in any class, a non-p3a-floor hard violation, a wrong :338 SAFE on m3, m3 never raising at :338 (including an unbuildable m3a), a dead negative control, or a changed denominator (the observation-field or DeckLayout change touched the harness runtime path). Derivation: a wrong load_state value or an unintended baseline divergence. Accounting: an unattributed decline, a SAFE with a decline reason, or topology-prefix declines that disagree with the independent scan. Precision below 123: read n_338_declined_{kind,observation,deck,topology_prefix,topology_loop} against the non-:338 residual sites to say which mechanism lost the operations, and do not infer 'mechanism broken' until that breakdown says so."
reasoning = "Every prior increment held 0 unsound on this 343-row denominator; a failed direction control, a wrong load_state value, or an unaccounted decline means the implementation is not the one specified."

[result_schema]
control_fires = "bool"
real_rows_executed = "int"
real_rows_setup_error = "int"
real_operations_executed = "int"
real_unsound = "int"
real_unsound_scoped = "int"
real_totality_violations = "int"
real_check_graph_exceptions = "int"
real_n_operations_scope_verdict_safe = "int"
real_pick_up_tips_scope_safe = "int"
real_pick_up_tips_n_ops = "int"
real_n_findings_decided = "int"
real_n_tip_racks_decided = "int"
real_n_tip_racks_attempted = "int"
n_338_pickups_attempted = "int"
n_338_pickups_safe = "int"
n_338_declined_kind = "int"
n_338_declined_observation = "int"
n_338_declined_deck = "int"
n_338_declined_topology_prefix = "int"
n_338_declined_topology_loop = "int"
n_338_declined_unattributed = "int"
n_338_safe_with_reason = "int"
n_pickups_with_preceding_disturber_indep = "int"
all_safe_unsound = "int"
all_safe_operations_executed = "int"
runtime_raised_ops_all_safe_arm = "int"
m1_will_fail_fired = "bool"
m2_will_fail_fired = "bool"
m1_attempted = "int"
m1_achieved = "int"
m2_attempted = "int"
m2_achieved = "int"
p3a_attempted = "int"
p3a_achieved = "int"
mutants_hard_violations_excl_p3a_floor = "int"
mutants_unsound = "int"
mutants_criterion_ii = "int"
m3_attempted = "int"
runtime_raised_m3 = "int"
static_338_safe_on_m3 = "int"
v1_attempted = "int"
v1_achieved = "int"
v1_gate_passed = "bool"
load_state_channel_effect = "str"
baseline_divergences = "int"
baseline_intended_divergences = "int"
baseline_parity_matched = "int"
baseline_parity_total = "int"
n_ops_load_state = "int"
```

**Field definitions (r1; every field defined in r2, C13).**

- **Mutant fields.**
  - `mX_attempted` is the class's `n_raised_as_expected` (r2, C1).
  - `mX_achieved` is its `static_verdict_at_raising_index.will_fail`. Both are read from the report
    JSON. This covers m1, m2, v1 and p3a; p3a is reported only.
  - `mutants_unsound` sums the lengths of every class's `unsound_safe_where_simulator_raised` list,
    across all `tip_mutants` classes (m1, m2, p3a, m3) and v1.
  - `mutants_criterion_ii` sums the lengths of every class's
    `unsound_will_fail_where_simulator_ran_clean` list, over the same classes.
  - `mutants_hard_violations_excl_p3a_floor` is `len(tip_mutants.report.hard_violations)` minus the
    entries that are p3a floor violations. Those entries start `"p3a_pickup_already_held: floor FAILED"`.
  - `v1_gate_passed` is `volume_mutants`'s own report `gate_passed`.
  - `m1_will_fail_fired` / `m2_will_fail_fired` (defined in r3, minor 4) are
    `static_verdict_at_raising_index.will_fail > 0` for the class. That is the same predicate as
    `tip_mutants`'s own `will_fail_fired[mclass]`. They stay in H as a cheap direction check, even
    though X's achieved == attempted ≥ floor implies them.
  - `m3_attempted` is m3's `n_ran`, reported only.
  - `runtime_raised_m3` is read from the report key
    **`by_class.m3_lid_on_tip_rack.n_runtime_raised_at_338`** (r3, minor 4). It counts m3 rows that
    raised at the `:338` site at the pickup index (§18.9, m3 paragraph).
  - `static_338_safe_on_m3` is read from **`by_class.m3_lid_on_tip_rack.n_static_338_safe`**. It counts
    m3 rows that raised at `:338` at the pickup index **and** carry any `SAFE` finding sited at
    `_check_tip_racks_available` at that index. It reads the new site-keyed `site_verdicts_at_index`
    field (AC-18.16), never the operation-level verdict.
  - Both counts also need the runtime's error text and frames. They come from a **second defaulted
    trailing `MutantResult` field**, `runtime_error: tuple[str | None, list[dict] | None] = (None, None)`,
    filled from `rt.error` and `rt.error_frames` (r3, minor 4).
- **`:338` counters.**
  - Their scope (r2, C4) is **planned `pick_up_tips` operations on the `real` arm that carry a
    `:338` finding**. `n_338_pickups_attempted` counts them, and `n_338_pickups_safe` counts those whose
    `:338` finding is `SAFE`.
  - Each non-`SAFE` operation is attributed to the **first failing conjunct**, in the fixed order
    `kind → observation → deck → topology_prefix → topology_loop`, by `tip_racks_decline_reason`
    (§18.5.3), computed as in item 7. That gives `n_338_declined_{kind, observation, deck,
    topology_prefix, topology_loop}`.
  - `n_338_declined_unattributed` is `n_338_pickups_attempted − n_338_pickups_safe − Σ declined_*`
    (hard `= 0`).
  - `n_338_safe_with_reason` counts `SAFE` `:338` findings whose recomputed reason is not `None`
    (hard `= 0`).
- **The M8 consistency term.**
  - `n_pickups_with_preceding_disturber_indep` is the independent scan's count of planned
    `pick_up_tips` operations carrying a `:338` finding, **restricted to those where `kind`,
    `observation` and `deck` all held**, that have a topology disturber at an earlier pc.
  - **Its inputs (r3, X2).** The restriction to `kind` ∧ `observation` ∧ `deck` reads the same
    wrapped-`observation_env_members` list and the guard's `kind`. The disturber scan runs over the same
    `LOWERED_SINK` `bc`, with the script's **own** re-implementation of §18.5.4 in place of the exported
    functions. Loops are excluded by the hard no-`ir.Loop` assertion in item 7.
  - It is compared, as a hard term, with `n_338_declined_topology_prefix`. Both sides share the same
    restriction by construction, because the prefix reason is reached only after the first three
    conjuncts held.
  - `n_338_declined_topology_loop` is reported separately and predicted 0.
- **Other fields.**
  - `real_n_tip_racks_decided` / `real_n_tip_racks_attempted` are §18.5.6's
    `n_tip_racks_decided.total` / `.attempted` on the `real` arm. Their scope is every executed
    operation carrying `:338`, drops included.
  - `baseline_parity_matched` is the number of keys in `keys(baseline) ∪ keys(current)` whose values
    are equal, with absence as a value; the intended-divergence keys, whose values differ by design,
    are excluded. `baseline_parity_total` is `|keys(baseline) ∪ keys(current)|`.
  - `baseline_divergences` and `baseline_intended_divergences` are M11's counter and
    `len(intended_divergences)`.
  - `n_ops_load_state` is the number of executed operations whose method is `load_state`.

**How the thresholds were chosen.**

- **205 (PASS).** The recovery mechanism is structural: each of the three residual sites is addressed
  by name. So the only expected losses come from the two decline paths the old pin never had. The
  first is `tip_racks_available == false`: `build_setup` places each tip-typed base on its own named
  rack *(reasoned from its docstring; lid/stack placement not audited)*. The second is a topology
  disturber preceding a pickup. A 5% allowance (11 operations) is a judgement. It is stated as one
  here and is not derived.
- **123 (MARGINAL/FAIL boundary), reframed in r1 (M8).** r0 called 123 "derived". It is only an
  anchor. The arithmetic is 216 − 93, where 93 is the benchmark's move-family operations (31 each for
  `move_lid`, `move_plate` and `move_resource`, from `real.oracle_replay.json`). But the arithmetic
  ignores disturber classes (b), (c) and (d), the loop clause, and `tip_racks_available = false`.
  The ten methods account for 544 of the 548 executed operations, so 4 operations lie outside them.
  Two measurements now make a result below 123 interpretable instead of presumptively "mechanism
  broken":
  - **the hard consistency term** `n_338_declined_topology_prefix = n_pickups_with_preceding_disturber_indep`,
    together with the attribution terms `n_338_declined_unattributed = 0` and
    `n_338_safe_with_reason = 0` (r2);
  - **the FAIL decision's attribution** through the decline counters.
- **≤ 216, and total == `pick_up_tips`.** These are predictions. The 7 `:720` operations cannot reach
  scope-`SAFE`, and every other method keeps at least one undecidable site in its 1.0 residual
  (`drop_tips` keeps `:882`/`:891`, per `real.oracle_replay.json`). A violation of either routes to
  MARGINAL for attribution. It is not a pass.

**The explicit `load_state` prediction** has three parts:

- (i) `load_state_channel_effect == "widen"` in the regenerated table, a deterministic artifact property
  and a hard term;
- (ii) `baseline_divergences == baseline_intended_divergences == 1` (M11's counter over the key union,
  absence counted as a value). The one divergence is `load_state` HAS_TIP → widen, derived from the
  old-pin source in OI-9;
- (iii) `n_ops_load_state == 0`, which means the benchmark cannot observe the change, so any movement
  in a benchmark counter must be attributed to something else.

**Reported, not gated:**

- `real_n_findings_decided`, predicted to rise;
- `n_findings_by_reason.guard_predicate_unparsed`, predicted to fall by up to 288 toward 495;
- `channel_state_unknown`, predicted to fall from 644;
- the volume-family counters, which move through V5's modelled path.

---

## 18.10 Acceptance criteria

Each criterion names its fixture or artifact field and states what a stub would fail.

- **AC-18.1 (R-A, the backing-field alias).**
  - The regenerated artifact has `receiver_state.LiquidHandler.effect_backing_fields == ["_carried"]`.
  - Synthetic fixtures, one each:
    - (a) a getter `return self._x` aliases `_x`;
    - (b) a getter `return cast(T, self._before)` does **not** alias `_before`;
    - (c) a property chain `_tip → _pending_tip → _carried` aliases `_carried` exactly once;
    - (d) a getter returning `holder.tip` contributes nothing;
    - (e) a two-property cycle terminates.
    - (f) (r1, m16) a getter `return self.helper` where `helper` is a direct method of `C` does **not**
      alias `helper`.
  - (b) is the stub-defeating half: an implementation that aliases every `self.X` anywhere in the
    getter passes (a), (c) and (d) and fails (b).
  - **The M3 tripwires (r1), asserted over the pin with a synthetic counter-class for each:**
    - (i) the self attributes read on the bool-view getter's non-alias paths are written by no method
      other than `__init__` (at the pin that set is `{_holder_ref}`);
    - (ii) no getter of `C` writes a self attribute.
  - **(r2, C8/C9) The dependency sets and writer snapshots.**
    - The bool-view getter's `D` equals `{"_holder_ref"}`.
    - The union of `D(F)` over every `F ∈ S` equals `{"_holder_ref", "_before"}`.
    - The writer snapshots equal §18.4.2's pinned sets: `_holder_ref` → `{__init__}`, and `_before` →
      `{__init__, _tip setter, _hold, commit, rollback, clear, load_state}`.
  - Synthetic tripwire controls:
    - **The local-through shape (r2, C8).** A getter
      `holder = self._holder; if holder is None: return self._carried; return holder.tip`, plus a
      method `rebind(self, h)` that writes `self._holder_ref`, makes (i) fail. A scan of return
      expressions alone would miss this, so the control proves the scan covers the whole body;
    - a new method writing `self._before` makes the `_before` snapshot assertion fail (r2, C9);
    - a getter that assigns `self._cache` makes (ii) fail;
    - an assignment `self._tip = t` to a setter-bearing `F ∈ S` classifies `UNRESOLVED`, not
      `HAS_TIP`.
- **AC-18.2 (R-B, helper following, and its synthetic controls).**
  - The regenerated artifact has `effects == {"add_tip": "HAS_TIP", "clear": "NO_TIP", "remove_tip": "NO_TIP"}`,
    `effects_unresolved == ["load_state"]` and `effects_max_depth == 2`. **If any value differs, T57
    stops and records the measured value with its cause. It does not edit the expectation to match.**
  - Synthetic fixtures, one each:
    - (a) **positive, depth 3:** `add → _a → _b → _c → self._carried = tip` derives `add: HAS_TIP`,
      with `effects_max_depth == 3`. This proves the depth is unbounded and not fixed at 2;
    - (b) **no alias, no effect:** the same chain writing `self._other` gives `{}`;
    - (c) **zero-argument COPY helper does not poison:** `add` calls `self.commit()`, whose body is
      `self._tip = self._pending_tip`, and `add` stays `HAS_TIP`;
    - (d) **zero-argument constant helper propagates:** `reset` calls `self.clear()`, whose body is
      `self._put(None)`, and `reset` gives `NO_TIP`. The recon's ≥ 1-argument filter fails this one;
    - (e) **both kinds:** `if c: self._carried = None` / `else: self._carried = t` gives
      `effects_unresolved`, not omission;
    - (f) **conditional-`None` local:** the `load_state` shape gives `effects_unresolved`;
    - (g) **optional entry parameter:** `def set(self, tip: Optional[Tip]): self._put(tip)` gives
      `effects_unresolved`;
    - (h) **cycle:** `a → b → a`, each writing, terminates and gives `UNRESOLVED`;
    - (i) **starred call:** `self._put(*args)` gives `UNRESOLVED`;
    - (j) **callable attribute:** `self._callback()` is not followed and contributes nothing;
    - (k) **inherited helper:** a helper defined only on a base class is not followed; separately, a
      whole-surface check asserts that no class in `TipTracker`'s PLR base closure assigns any name in
      `W`;
    - (l) **(r1, B1) the old-pin `load_state` shape, as an INLINE synthetic fixture.**
      `def load_state(self, state): self._tip = cast(Optional[Tip], deserialize(state.get("tip")))`,
      with `_tip` a plain field, gives `load_state ∈ effects_unresolved`. The fixture is written into
      the test source. No test reads a sibling worktree, because CI cannot see one;
    - (m) **(r1, B1) value forms:** writes of `self._carried = f(x)`, `= state["t"]`, `= x or None`,
      `= await g()`, `= self.backend.tip` and `= "a"` each give `UNRESOLVED`;
    - (n) **(r1, B2) rebound parameter, the negative control:**
      `def _put(self, tip): if c: tip = None; self._carried = tip`, called as `self._put(t)` with
      `t ↦ HAS_TIP`, gives `UNRESOLVED`, not `HAS_TIP`. A companion with `for tip in xs:` also gives
      `UNRESOLVED`;
    - (o) **(r1, m6) catch-alls:**
      - a `staticmethod`/`classmethod` callee gives `UNRESOLVED`;
      - `import tip` in the callee body makes `tip` `UNRESOLVED`;
      - `self._put(t, u)` against `def _put(self, tip)` (too many positionals), and `self._put(x=t)`
        (unknown keyword), each give `UNRESOLVED` for every parameter;
    - (p) **(r1, M4) order independence:** classifying the methods of a synthetic tracker in two
      different orders, with and without memoisation, yields the same `effects_max_depth`;
    - (q) **(r2, C15) the callback fact:** every `register_callback` call in the 1.0 `LiquidHandler`
      passes exactly `self._state_updated`, and `LiquidHandler` defines no `_state_updated` of its own
      (AST check over the pinned source);
    - (r) **(r2, C10) local fixpoint:**
      - `tip = tip; self._carried = tip` with no parameter `tip` gives `UNRESOLVED`, and the evaluation
        terminates;
      - `a = b; b = a; self._carried = a` gives `UNRESOLVED`;
      - `a = None; a = a; self._carried = a` gives `NO_TIP`, because the self-reference contributes
        nothing and the only grounded binding is `None`;
      - **(r3)** `a = b; b = a; b = None; self._carried = a` gives `NO_TIP` via the Kleene iteration.
        The result is asserted identical whether `a` or `b` is queried first, and with or without
        memoisation;
    - (s) **(r2, C2) entry-context negative controls:** each of these gives `UNRESOLVED` for the
      written parameter, with `T = {"Tip"}` derived from a synthetic `self._carried: Optional["Tip"]`:
      - `def add(self, tip): self._put(tip)` (unannotated);
      - `tip: Any`;
      - `tip: Union[Tip, None]`;
      - `MaybeTip = Optional[Tip]` then `tip: MaybeTip`;
      - `tip: None | Tip | X`;
      - `tip: Optional[Tip]`;
      - `tip: "Optional[Tip]"`;
      - `tip: Tip = None`.

      The positive controls `tip: Tip`, `tip: mod.Tip` and `tip: "Tip"` each give `HAS_TIP`. A further
      control gives two `W` fields annotated with different types, so `T` is not a singleton, and
      asserts that nothing gets `HAS_TIP`;
    - (t) **(r2, C3 + D-3) tip-write catch-alls:** each of these makes the method `UNRESOLVED`:
      - `for self._carried in xs: pass`;
      - `with f() as self._carried: pass`;
      - `setattr(self, "_carried", t)`;
      - `setattr(self, name, t)`;
      - `object.__setattr__(self, "_carried", t)`;
      - `delattr(self, "_carried")`;
      - `self.__dict__["_carried"] = t`;
      - `vars(self)["_carried"] = t`;
      - `helper(self)`, where `helper` is a free function.

      `helper(self.thing)` does **not**: it passes an attribute read, not bare `self`.
      **(r3, X1)** Two further fixtures each also give `UNRESOLVED`:
      - a **followed** call that binds `self`: `def add(self, t): self._h(self, t)` with
        `def _h(self, p, t): p._carried = t`;
      - **local aliasing:** `def add(self, t): me = self; me._carried = t`, and
        `def clear2(self): t = self; t._put(None)`.

      A method whose only `self` uses are attribute bases (the 1.0 `add_tip` shape) is unaffected, and
      stays `HAS_TIP`;
    - (u) **(r2, C11) class-level bindings:** an `F ∈ S` bound at class level as
      `F = property(get, set)`, or as a `functools.cached_property`, or inherited as a property from a
      synthetic base class, is not a plain field. An assignment to it gives `UNRESOLVED`, not
      `cls(value)`.
  - (c), (d), (e), (l), (n) and (s) together are the stub-defeating core: no single simplification of
    the classifier passes all six.
  - **Zero cost, asserted (r2):** the regenerated artifact's pin values above, namely `effects`,
    `effects_unresolved`, `effects_max_depth` and `entry_reset` (AC-18.4(a)), are **unchanged** by
    C2, C3, D-3, C10 and C11. The reasons are given per rule in §18.4.2 and §18.4.3.
- **AC-18.3 (L1's widen mapping in the bridge).**
  - The regenerated table has `LiquidHandler.load_state.channel_effect == "widen"`,
    `LiquidHandler.pick_up_tips.channel_effect == "HAS_TIP"` and
    `LiquidHandler.drop_tips.channel_effect == "NO_TIP"`.
  - Synthetic bridge fixtures, one each:
    - an unresolved method bridged at depth 0 gives `"widen"`, **not** `None`;
    - an unresolved method bridged at depth 1 gives `"widen"`;
    - a bridge to an `_`-prefixed method gives `"widen"`;
    - one depth-0 resolved bridge plus one unresolved bridge gives `"widen"`, so unresolved takes
      precedence;
    - **(r1, M1)** a bridge to a method absent from the survey index gives `"widen"`, and so does a
      bridge to a name that is not a direct method of `C`. Both run **before** the index skip, so an
      implementation that leaves rules 0–3 behind `if c_key not in index: continue` fails;
    - **(r1, M2)** a depth-0 `HAS_TIP` bridge together with a depth-1 `NO_TIP` bridge gives `"widen"`,
      not `HAS_TIP`.
  - A check-level fixture `pick_up_tips(use_channels=[0])` → `load_state(...)` → `pick_up_tips(use_channels=[0])`
    yields **zero** `WILL_FAIL` findings on the third operation. Under the old `HAS_TIP` mapping that
    third operation would get a `WILL_FAIL`, so this is the old unsoundness, asserted gone.
- **AC-18.4 (R-C, entry reset, and L7's atomicity).**
  - (a) The regenerated table has `entry_reset == {"method": "setup", "post": "no_tip"}`.
  - (b) A synthetic receiver whose reset constructs the tracker **with** a `None`-default parameter
    bound (`T(thing=…, holder=h)`) yields no `entry_reset`. This is the stub-defeating half of R-C(2).
  - (c) For every receiver on the regenerated table, `entry_reset` present ⇒ `effects` has both a
    `HAS_TIP` and a `NO_TIP` value.
  - (d) End to end, on the 1.0 contracts, re-expressed at the 1.0 sites:
    - `setup` → `pick_up_tips([0])` yields `SAFE` at `LiquidHandler.pick_up_tips`'s own `HasTipError`
      guard and at `TipTracker.add_tip`'s bridged guard;
    - `setup` → `pick_up_tips([0])` → `pick_up_tips([0])` yields `WILL_FAIL` on the second pickup at the
      own guard, with `category == "precondition_state"`;
    - `setup` → `pick_up_tips([0])` → `drop_tips([0])` → `aspirate([0])` yields `WILL_FAIL` at
      `TipTracker.get_tip`.
    - These three reinstate increment 1's AC-10.1/10.2/10.3 at the new pin. The third needs the
      bridge, the effects and the channel set all to be right.
- **AC-18.5 (V5 non-regression through the modelled path).**
  - `test_ac_14_5_e_retip_dirty_tip_never_safe` (in `plr-sema/tests/test_check_graph.py`) and every
    test in the file `plr-sema/tests/test_tips_dirty_cost.py` pass, with `pick_up_tips`/`drop_tips`
    now carrying modelled effects.
  - A new fixture, pickup → aspirate 50 → dispense 50 → drop → pickup → aspirate 50 → dispense 50,
    shows the second pickup's cell at `[0,0]`. That means `tips_dirty` stays false and the second
    dispense decides. This is the precision half: the amendment must not have been what made the retip
    tests pass.
  - **(r1, m9)** A check-level fixture covers the channel-set reset: pickup → aspirate 50 →
    `update_head_state({0: None})` → pickup → dispense 50. It shows that `update_head_state` resolves no
    channel set, sets `tips_dirty`, resets every tip cell to `TOP`, and widens the tip receiver, so the
    final dispense is not `SAFE`. A companion with `load_state(...)` in place of `update_head_state`
    asserts the same.
- **AC-18.6 (R-E, receiver roots).**
  - The regenerated table has receivers set-equal to `{"LiquidHandler", "LiquidHandlerBackend"}`. The
    test pins the **set**, not a count.
  - Synthetic: a receiver `R` whose tracker `T1` itself has an annotated attribute typing to an
    anchored `T2` yields receivers `{R}` only.
  - An AST scan of the R-E implementation finds no class-name string constant.
- **AC-18.7 (cross-pin baseline fixture).**
  - `plr-sema/scripts/gen_channel_effect_baseline.py` and `plr-sema/tests/fixtures/channel_effect_baseline.json`
    exist, with `source_rev` naming the old-pin commit.
  - The drift test passes with exactly one intended divergence, `LiquidHandler.load_state`, and prints
    `parity`. The test asserts `baseline_divergences == len(intended_divergences)`, counted over the
    key union with absence as a value (r1, M11).
  - Negative self-tests:
    - deleting a baseline key from a copy of the current table fails the test (**vanished key**);
    - flipping `drop_tips` to `HAS_TIP` in a copy fails it;
    - **(r1, M11)** adding a `channel_effect` to a contract absent from the baseline fails it, unless
      the key is listed with `"old": "absent"`;
    - `--rebase` without an explicit `--intended-divergences` exits non-zero.
- **AC-18.8 (structural invariants).** §18.8(2)(a)–(e) are each asserted over the regenerated table, and
  each has a synthetic counter-table that must fail it. (f) moved to AC-18.2's pin values in r1 (m8).
- **AC-18.9 (behavioural oracle).** §18.8(3), run against real PLR 1.0.0b1:
  - every `effects` polarity is matched by `has_tip` after the call;
  - `load_state` exhibits both outcomes;
  - a fresh tracker has no tip;
  - **(r1, m11)** the holder-full tracker matches every `effects` polarity;
  - **(r1, m11)** an uncommitted `add_tip` followed by `rollback()` leaves `has_tip is False`;
  - the import order is explicit;
  - the test is not skipped when PLR imports.
- **AC-18.10 (the sixth observation field).**
  - `capture_observation` returns `tip_racks_available`.
  - **(r2, C5) `DeckLayout.lidded_tip_racks`.** The field exists with default `[]`, and `merged()`
    concatenates it. `build_setup` assigns a real `Lid` sized to each named rack after the racks are
    placed. A **default-layout-unchanged** unit test asserts that a layout without the field builds
    exactly the deck it built before T60. AC-18.10's own lidded fixture below needs this field.
  - A fixture layout with a **lidded** tip rack (via `lidded_tip_racks`) yields `False`, the benchmark's
    clean layout yields `True`, and a deck with no rack yields `True`.
  - A raising read yields `plr_observation is None`, as a whole record.
  - `OBSERVATION_KEYS` has six members. `test_observation_record_closed_refusal_list` (in
    `plr-sema/tests/test_cache.py`) and `_OBSERVATION_KEYS` plus `test_plr_observation_present_on_success`
    (in `training/tests/test_verify_postconditions.py`) are updated to six.
  - `env` carries `obs:tip_racks_available=true|false`, and two observations differing only in the
    field give distinct `env` sets.
  - The empty-`env` cache key is unchanged.
  - §16.2.1's closed-record text in `.praxia/docs/specs/260909_plr-sema-observation-increment.md`
    carries the one-field amendment and the narrowed lid-topology exception.
  - **(r1, M10)** §16.2.2's third failure-mode paragraph in the same file carries §18.5.2's
    frame-condition clause verbatim. A test asserts that the clause text is present.
- **AC-18.11 (the `:338` site rule, the topology conjunct, and A-RACK-STATIC).**
  - (a) The key is present in `D6_SITE_RULES` and matches exactly one site
    (`test_d6_site_rule_keys_each_match_exactly_one_site`, count 4).
  - (b) **Never `True`:** exhaustive over the product (r1, m4; r2, C4) where each observation field is
    `true`, `false` or absent, and each of `rack_topology_prefix_ok` / `rack_topology_loop_ok` is
    `True`, `False` or `None`. That is 3⁴ cases. Separately, the rule returns `None` for any guard whose
    `kind` is not `"raise_guard"` (r1, m5). **(r2, C4)** Over the same product plus `kind`,
    `tip_racks_decline_reason` returns the first failing conjunct in the order
    `kind → observation → deck → topology_prefix → topology_loop`, and the site rule returns `False`
    iff that function returns `None`.
  - (c) `SAFE` at `:338` on a `setup → pick_up_tips` graph with `env` carrying
    `obs:tip_racks_available=true` and `obs:deck_resources_verified=true`.
  - (d) One fixture per decline path, each **run against the shipped `plr-sema/data/derived_contracts.json`**
    (r1, M5) and each giving `UNKNOWN`/`guard_predicate_unparsed`:
    - `tip_racks_available=false`;
    - the field absent;
    - `deck_resources_verified=false`;
    - a preceding `move_lid`;
    - a preceding `pick_up_resource` (the derived family beyond the owner's three);
    - a `move_plate` at a later pc inside a shared loop;
    - a preceding call on a different receiver type;
    - a preceding call with no contract.
  - (e) A `move_lid` at a **later** pc outside any loop still decides `SAFE`, which proves the pc test
    is real and not a blanket "any move anywhere".
  - (f) **Hand-built adversarial runtime fixture (revised in r2, C5).**
    - The test code constructs a **real PLR `Lid`**, sized to the rack, and places it on the chatterbox
      deck. It does not use a `Plate` "lid" from the tier-1 layout, because moving a `Plate` onto a rack
      leaves `rack.lid` `None`.
    - It then calls `move_lid(lid, tip_rack)` followed by `pick_up_tips` from that rack.
    - The simulator raises the `:338` `ValueError`, whose message contains "something is stacked on top
      of it".
    - The static finding at `:338` is not `SAFE`, and it declines at `"topology_prefix"`.
    - The tier-1 fence counts 0 unsound.
    - This is the topology conjunct's runtime witness, since the run's m3 does not exercise it (C16).
  - (g) `n_tip_racks_decided` is published, with `attempted` and `predicted_target`.
  - (h) A-RACK-STATIC and A-CALLBACK-INERT are both in increment 1's §10.6.3 table, and the table
    test asserts **seven** rows.
  - (i) **(r1, M5) The family pin.** The move family computed from the **shipped**
    `plr-sema/data/derived_contracts.json` equals exactly
    `{drop_resource, move_lid, move_plate, move_resource, pick_up_resource}`.
- **AC-18.12 (registry: HM-26 and the cap; T61).**
  - HM-26 has `declared == 4` and live 4, with `what`/`breaks_when` naming the fourth rule.
  - `len(live_rows()) == 25` and `BUDGET_CAP == 25`, asserted unchanged.
  - The HM-25 half moved to AC-18.17 in r2 (C12), so that each criterion is gated by the task that
    lands it.
- **AC-18.13 (goldens re-taken once, and the gate-1 failures closed).** This runs **after** T57, T58 and
  T61 have all landed, and only then.
  - `test_check_graph_report_unchanged_for_shipped_fixture` (`plr-sema/tests/test_ir.py`) is re-taken
    with the finding count and the `by_reason` counter **measured**, not predicted. The predicted count
    is **44**. The comment records why it moved: the two `:338` findings, whose reason stays
    `guard_predicate_unparsed` without an observation. **If the measured count is not 44 (r1, m13),
    T62 records the measured value and its cause in §18.16 and does not edit anything to match the
    prediction.**
  - `test_ac_10_4_shipped_fixture_unchanged` compares non-volume findings **excluding** findings sited
    at `_check_tip_racks_available` against the pre-increment 38, and asserts exactly 2 such findings.
  - Every test the gate-1 report attributes to RC-1 or RC-2 passes, with no `xfail`/`skip` added:
    the 15 in `test_tip_typestate.py`, the 2 in `plr-sema/tests/test_tier2.py`, and the
    `test_oracle_replay.py` clean-pickup gate test. They are red at `a176bac7` per that report and were not re-run for this
    spec.
  - AC-10.9's AST literal scan is green.
- **AC-18.14 (the measurement).**
  - `plr-sema/eval/plr10_tip_effects_measure.bth.toml` is committed **before** the run, byte-identical
    to §18.9's block except for whitespace. `git log` shows the sidecar's commit preceding the run's
    timestamp.
  - `plr-sema/eval/plr10_tip_effects_measure.py` implements its `[result_schema]` exactly, checked by a
    unit test against the TOML, as `test_plr10_characterize.py` does.
  - **Resumability (owner rule, finalization 260929).** Three unit tests in
    `plr-sema/tests/test_plr10_tip_effects_measure.py`, each using stub unit runners so they are cheap:
    - (a) a unit whose stamp input hashes and output sha256 both match is **reused, not recomputed**.
      The stub runner asserts it was not called, and `result.json`'s `units` block records `reused`;
    - (b) a **corrupted output file** (sha256 mismatch) forces recomputation, and so, separately, does
      a **changed input** (a different `derived_contracts.json` hash);
    - (c) **killing the run after one unit completes** leaves that unit's output and stamp intact and
      reusable. The next invocation reuses it and computes only the rest. While any required unit is
      incomplete, no `result.json` exists.
    - **Negative control:** a stamp whose input hash differs from the current run's, even with a
      matching output sha256, **must NOT be reused**. The test fails if the stub runner is not called.
  - The run's bathos record, retrieved by `bth sql` after `bth compact`, has an evaluated `outcome`.
  - The outcome and the full `result.json` are recorded in this document's implementation record,
    whichever branch fired.
- **AC-18.15 (this document is machine-checked, and the amended texts landed).**
  - `plr-sema/tests/test_spec_lint.py` gains a constant for this file and parametrises it into both
    live-spec tests.
  - `uv run pytest plr-sema/tests/test_spec_lint.py -q` is run, with zero failing citation violations
    and zero AC-gating violations over this file, and the other nine specs unchanged.
  - Increment 1's §10.2.4 carries the "both kinds → UNRESOLVED" amendment note. Its §10.4 E2 carries
    the r1 M2 amendment note: widen when depth-0 and deep effects coexist.
  - `.praxia/docs/INDEX.md` is regenerated with the docs tool.
- **AC-18.16 (r1, M7; revised in r2, C5/C6/C7 and D-4: the m3 lidded-rack mutant).**
  - **Registration.** `make_m3_lid_on_tip_rack` exists in `plr-sema/eval/tip_mutants.py`. It adds the
    pickup rack to the row layout's `lidded_tip_racks`, and **m3b does not exist**. The class
    `m3_lid_on_tip_rack` is added to `_MUTATORS`, to `_EXPECTED_EXC` (`"ValueError"`) and to
    `by_class`, the hard-coded dict at `plr-sema/eval/tip_mutants.py:490-492`.
  - **Site-keyed capture (C6).** `run_one_mutant` installs `oc.FINDINGS_SINK`, chain-composed with any
    prior sink and restored in `finally`, following `plr-sema/eval/oracle_replay.py:659-728`. From it,
    it records `site_verdicts_at_index`: `{PlrSite string: [verdict, …]}` at the raising index, held in
    a **new trailing `MutantResult` field with a default**, so existing positional constructions stay
    valid. **(r3, minor 4)** A second defaulted trailing field, `runtime_error`, carries `rt.error` and
    `rt.error_frames`. m3's summary publishes `n_runtime_raised_at_338` and `n_static_338_safe` under
    `by_class.m3_lid_on_tip_rack`.
  - **The mutator's inputs (r3, minor 4).** The pickup rack is the base name of the first pickup's `at`
    reference. A `deck_layout` of `None` becomes a fresh layout carrying only `lidded_tip_racks`. An
    unparseable reference, or a base with no pickup, returns `None`.
  - **The two m3 counts.**
    - `static_338_safe_on_m3` counts m3 rows that raised at `:338` at `_first_pickup_index` **and**
      carry any `SAFE` verdict sited at `_check_tip_racks_available` there.
    - `runtime_raised_m3` counts rows whose runtime raised at the `:338` site at that index, keyed on
      the message or `error_frames` (§18.9).
  - **The class loop (C7).**
    - m3 has its **own branch placed before** the criterion-(iii) `elif`
      (`plr-sema/eval/tip_mutants.py:555`). Its hard violations are `static_338_safe_on_m3 > 0` and
      `runtime_raised_m3 == 0`.
    - Its floor (`m3_attempted`) is reported only.
    - Criteria (i) and (ii) apply to m3 generically, as to every class.
    - p3a's branch and the m1/m2 criterion-(iii) logic are unchanged.
  - **The unit test.** It runs the mutator on inline base examples, and asserts that the simulator
    raises at `:338` at the pickup index and that no `:338`-sited `SAFE` verdict appears there. A
    second assertion checks the reason: `tip_racks_decline_reason` returns `"observation"` on those rows.
  - OI-18 is closed.
- **AC-18.17 (r2, C12: the HM-25 unit; T57).**
  - HM-25 has `declared == 13` and live 13, and its thirteenth probe exercises a synthetic three-hop
    chain.
  - This is unconditional: the owner ruled on OI-4 on 260929 to book the unit. The zero-cost
    alternative was declined (§18.7).

---

## 18.11 Fixer tasks

> **Ordering (normative).**
> - T57 is atomic (L7) and comes first.
> - T58 may land before or after T57, but T59 needs both.
> - T61 comes after **both T57 and T60** (r1, m15). The site rule reads the field T60 creates, and
>   T61's gate files (`test_oracle_replay.py`, `test_check_graph.py`) stay red on the RC-1 tests
>   until T57's effects land.
> - T62 runs **once**, after T57 + T58 + T61, so the goldens are re-taken a single time against the
>   final rules.
> - T63 is last among the code rows, and its sidecar commit is its own first step.
> - T64 closes the increment.
>
> Every gate runs pytest **one file per process**, as CI does. Never run a whole suite locally.
>
> Each task that regenerates `plr-sema/data/derived_contracts.json` uses the gate-1 report's
> recipe, the one that reproduced the committed table byte-for-byte at the old pin, and leaves
> `derived_contracts.upstream_nonlegacy.json` untouched (L6).

| task | scope | files | gate | ~LOC | depends on |
|---|---|---|---|---|---|
| **T57** | **Derivation, atomic (L7).** In `derive/receiver_state.py`: R-A (§18.4.2), R-A's no-method restriction and M3's property-assignment rule plus its two tripwires (§18.4.2); R-B's classifier with the binding and argument table as revised in r1 (B1: non-`None` expressions → `UNRESOLVED`; B2: rebound parameters join; m6 catch-alls), entry context, fold, cycle guard and the structural `effects_max_depth` of M4 (§18.4.3); L1's `effects_unresolved` plus `compute_channel_bridge`'s rules 0–3 placed **before** the index skip and M2's coexistence widen (§18.4.4); R-C(1)/(2) (§18.4.5); R-D (§18.4.6); the four new `receiver_state` keys (§18.4.8); `test_derive.py` is run in full because it also rebuilds the non-legacy gap ledger (OI-12); `_classify_write`'s `"ambiguous"` renamed to `COPY` with identical semantics. **r2 additions:** C2's node-shape allowlist, with `T` derived over `W`; C3's tip-write catch-alls and D-3's bare-`self` rule; C10's local fixpoint; C11's class-level-binding rule; C8/C9's dependency sets and writer snapshots; C14's `receiver_state_diagnostics.n_contracts_depth0_and_deep_coexist`; C15's callback AST check. **Owner ruling 260929 (OI-21), an implementation-time check alongside C15:** grep praxis's own state-update callback registrations (`web-repl/`, visualizer and REPL state-sync code) and confirm they only serialize; **if any one writes a tracker, STOP and ask**. One regeneration of `plr-sema/data/derived_contracts.json` and the gap ledger. HM-25 thirteenth probe and `declared` 12 → 13 (owner ruling on OI-4, 260929); STOP if the measure ≠ 13 | modify `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/derive/__main__.py` (if serialization needs it), `plr-sema/src/plr_sema/_hand_maintained.py`, `plr-sema/data/derived_contracts.json`, `plr-sema/data/gap_ledger.json` (regenerated); create `plr-sema/tests/test_tip_effects_plr1.py`; modify `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_hand_maintained_ratchet.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_tip_effects_plr1.py -q`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q` — satisfying **AC-18.1**, **AC-18.2**, **AC-18.3**, **AC-18.4**, **AC-18.17** | ~330 | — |
| **T58** | **R-E receiver roots (§18.4.7).** Two-pass candidate/tracker set difference in `derive_receiver_states`; regenerate | modify `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/data/derived_contracts.json` (regenerated); modify `plr-sema/tests/test_tip_effects_plr1.py` | `uv run pytest plr-sema/tests/test_tip_effects_plr1.py -q`; `uv run pytest plr-sema/tests/test_derive.py -q` — satisfying **AC-18.6** | ~40 | — |
| **T59** | **Drift tests (§18.8).** Baseline generator with `--from`/`--from-git-rev`/`--rebase`/`--intended-divergences`; the generated fixture from the old-pin table; the cross-pin test; structural invariants with counter-tables; the behavioural oracle against real PLR | create `plr-sema/scripts/gen_channel_effect_baseline.py`, `plr-sema/tests/fixtures/channel_effect_baseline.json`, `plr-sema/tests/test_tip_effect_drift.py` | `uv run python plr-sema/scripts/gen_channel_effect_baseline.py --from-git-rev <old-pin rev> --out plr-sema/tests/fixtures/channel_effect_baseline.json --intended-divergences LiquidHandler.load_state=widen`; `uv run pytest plr-sema/tests/test_tip_effect_drift.py -q` — satisfying **AC-18.7**, **AC-18.8**, **AC-18.9** | ~220 | T57, T58 |
| **T60** | **The sixth observation field (§18.5.2).** `capture_observation` computes `tip_racks_available`; `OBSERVATION_KEYS` gets six members; `observation_env_members` adds the `obs:` member; closed-list tests move to six; lidded/no-rack/raising fixtures; the §16.2.1 text amendment **and the §16.2.2 frame-condition clause (r1, M10)**. **r2 (C5/D-4): `DeckLayout.lidded_tip_racks: list[str] = []` with `merged()` updated; `build_setup` assigns a real `Lid` sized to each named rack after rack placement; a default-layout-unchanged unit test.** AC-18.10's own lidded fixture and T63's m3 both depend on this field | modify `training/verify/deck.py` (`DeckLayout`, `build_setup`, `capture_observation`), `training/verify/verifier.py` (comment only), `plr-sema/eval/oracle_common.py`, `plr-sema/tests/test_cache.py`, `training/tests/test_verify_postconditions.py`, `.praxia/docs/specs/260909_plr-sema-observation-increment.md`; create `training/tests/test_deck_lidded_tip_racks.py` | `uv sync --all-packages`; `uv run pytest training/tests/test_verify_postconditions.py -q`; `uv run pytest training/tests/test_deck_lidded_tip_racks.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q` — satisfying **AC-18.10** | ~140 | — |
| **T61** | **The `:338` site rule (§18.5.3–§18.5.6).** `_eval_tip_racks_available_site_rule` plus the fourth key, returning `False` iff the exported pure `tip_racks_decline_reason(ctx)` returns `None` (r2, C4), and declining unless `kind == "raise_guard"` (via `_Ctx.guard_kind`); the pre-scan (`rack_topology_disturbers`, returning pc → `(receiver_type, classes)`), giving `rack_topology_prefix_ok` / `rack_topology_loop_ok` and their threading through `process_call` → `_findings_for_call` → `_findings_for_guards` → `evaluate_guard` → `_Ctx`; `n_tip_racks_decided` in the replay report; HM-26 `declared` 3 → 4 with the rewritten `what`/`breaks_when`; A-RACK-STATIC and A-CALLBACK-INERT (owner ruling on OI-21) added to increment 1's §10.6.3 table, copied verbatim from §18.5.5, with the table test at seven; the hand-built `move_lid`-onto-rack runtime fixture | modify `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/src/plr_sema/_hand_maintained.py`, `plr-sema/eval/oracle_replay.py`, `plr-sema/tests/test_check_graph.py`, `plr-sema/tests/test_hand_maintained_ratchet.py`, `plr-sema/tests/test_oracle_replay.py`, `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md` | `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q` — satisfying **AC-18.11**, **AC-18.12** | ~210 | T57, T60 |
| **T62** | **Goldens re-taken ONCE, plus non-regression.** Re-take the `test_ir.py` shipped-fixture golden (44, `by_reason` measured) and the AC-10.4 comparison (excluding `:338`-sited findings); the V5 modelled-path fixture; confirm every gate-1 RC-1/RC-2 test green with no marker | modify `plr-sema/tests/test_ir.py`, `plr-sema/tests/test_tip_typestate.py`, `plr-sema/tests/test_volumestate_v5.py` | `uv run pytest plr-sema/tests/test_ir.py -q`; `uv run pytest plr-sema/tests/test_tip_typestate.py -q`; `uv run pytest plr-sema/tests/test_volumestate_v5.py -q`; `uv run pytest plr-sema/tests/test_tips_dirty_cost.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q`; `uv run pytest plr-sema/tests/test_tier2.py -q` — satisfying **AC-18.5**, **AC-18.13** | ~80 | T57, T58, T61 |
| **T63** | **The measurement (§18.9).** Step 1: commit the sidecar exactly as §18.9. Step 2a (r1, M7; r2, C6/C7 and D-4): in `tip_mutants.py`, the m3 mutator `make_m3_lid_on_tip_rack`, which uses T60's `lidded_tip_racks` and has no m3b; m3 in `_MUTATORS`/`_EXPECTED_EXC`/`by_class`; `site_verdicts_at_index` captured via a chain-composed `FINDINGS_SINK` in `run_one_mutant`, held in a new defaulted trailing `MutantResult` field; and an m3 branch before the criterion-(iii) `elif`. Plus its unit test. Step 2b: implement the script: two arms reused from `plr10_characterize.py`; per-method read; `tip_mutants` m1/m2/p3a/m3 and `volume_mutants` v1, **read from their report JSON, never their exit code**, with r2's `n_raised_as_expected` denominators; contract reads; parity and `baseline_intended_divergences` from T59's fixture; the analyzer-side `:338` attribution via `FINDINGS_SINK` + `LOWERED_SINK` + `rack_topology_disturbers` + `tip_racks_decline_reason` (D-2 (B)); and **an independent disturber scan that imports neither of those two functions** (M8). A schema-vs-TOML unit test covers it. **Step 2c (owner rule, finalization): preemption-safe and resumable scheduling per §18.9.** Seven units (`real`, `all_safe`, `m1`, `m2`, `p3a`, `m3`, `v1`), each in its own subprocess with a 30-minute timeout and no whole-run timeout; `units/<unit>.json` plus a sha256 completion stamp; reuse only on matching input and output hashes; a `units` provenance block in `result.json`; no `result.json` while any unit is incomplete; a `--classes` filter on `tip_mutants.py`; the resumability tests (a)(b)(c) and the negative control. Step 3: `bth run` in wrapped form, `bth compact`, verify by record; a re-invocation after a unit timeout reuses completed units | create `plr-sema/eval/plr10_tip_effects_measure.bth.toml`, `plr-sema/eval/plr10_tip_effects_measure.py`, `plr-sema/tests/test_plr10_tip_effects_measure.py`, `plr-sema/tests/test_tip_mutants_m3.py`; modify `plr-sema/eval/tip_mutants.py`; outputs under `outputs/plr-sema/plr10_tip_effects_<date>/` | `uv run pytest plr-sema/tests/test_tip_mutants_m3.py -q`; `uv run pytest plr-sema/tests/test_plr10_tip_effects_measure.py -q`; `bth run --project-slug <fd63e9cd's slug> -- uv run --no-sync python plr-sema/eval/plr10_tip_effects_measure.py <fd63e9cd's inputs> --out-dir …`; `bth compact`; `bth sql "SELECT id, status, outcome, exit_code FROM runs WHERE id LIKE '<prefix>%'"` — satisfying **AC-18.14**, **AC-18.16** | ~420 | T59, T60, T62 |
| **T64** | **Lint, amendments and index.** Register this file in `test_spec_lint.py` (both live-spec tests); increment 1's §10.2.4 amendment note and §10.4 E2 amendment note (r1, M2); regenerate `.praxia/docs/INDEX.md`; fill this document's implementation record with T57–T63's measured values and every divergence | modify `plr-sema/tests/test_spec_lint.py`, `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md`, this file; regenerate `.praxia/docs/INDEX.md` | `uv run pytest plr-sema/tests/test_spec_lint.py -q` — satisfying **AC-18.15** | ~20 | T63 |

**Sizing note.** The total is about 1,440 LOC across eight rows after finalization. T57 grew to ~330
and T60 to ~140 (the `lidded_tip_racks` field). T63 grew to ~420: the m3 mutator, the site-keyed
capture, the v1 run, the sink-based attribution and the independent scan, plus ~90 for the unit
scheduler, stamps and resume tests. If T63 runs long, split it at step 2a / 2b+2c: the mutator and its
test land and are gated first, and the sidecar commit still precedes the run. T57 at
~330 is the only row that must not be split, because of L7. If a session boundary falls inside it, the safe cut is
before the regeneration: rules and synthetic tests landed, table not regenerated, every existing test
unchanged. It is never between effects and `entry_reset`.

---

## 18.12 Risks

| risk | likelihood | mitigation / rollback |
|---|---|---|
| R-A silently aliases `_before` after a PLR edit (drops the `cast`), so `commit`, `add_tip` and `remove_tip` become `UNRESOLVED`, both pickup and drop widen, and `entry_reset` disappears (a silent precision loss) | low | AC-18.1 pins `["_carried"]`, AC-18.7 fails on `pick_up_tips`/`drop_tips` moving, AC-18.9's oracle disagrees. Rollback: revert T57's commit and regenerate the table |
| B1's stricter value table costs a real effect in some future PLR shape (a tip value that is an expression, not an annotated parameter) | low | fails closed (widen); AC-18.7 flags the moved key; extending the table needs its own argument |
| L7 violated: `entry_reset` lands without effects, giving a false `SAFE` on a repeated pickup | low if T57 is one commit | AC-18.4(c) invariant; T57 is one row; review checks one regeneration |
| The observation field is judged "the answer" under §16.2.2 | low after r1 (M10 amends §16.2.2) | the field reverts cleanly (T60) and the site rule then declines everywhere, which is sound |
| A-RACK-STATIC false for some non-move `LiquidHandler` method, or a family member decays to `"TOP"` | low–medium (OI-2) | family pinned on the shipped table (AC-18.11(i)); a hand-built real-`Lid` witness (AC-18.11(f)) and one fixture per disturber class (AC-18.11(d)(e)); tier-1 fence. The in-run m3 covers only the observation conjunct |
| The m3 mutant cannot be built (for example, `build_setup` fails to lid the rack) | low after r2 (T60 adds the field) | `runtime_raised_m3 = 0` is in hard block H, so the outcome is **FAIL**, not MARGINAL (r2, C5). Fix the harness and re-run under the **same** sidecar |
| The `DeckLayout` change alters the benchmark's runtime | low | the default is empty; a default-layout-unchanged unit test (AC-18.10); the hard term `real_rows_executed = 343` |
| The topology conjunct costs more precision than 5% | medium | pre-registered MARGINAL branch with per-path decline counters; no claim beyond the measured number |
| The baseline fixture shows a second divergence, or a 1.0 key absent from the old table | low (OI-9 now derived) | T59 stops and adjudicates in writing, never rebases silently; `--rebase` refuses without explicit divergences; the M11 counter counts new keys |
| R-E drops a legitimate receiver in a future PLR | low | AC-18.6 pins the set; the failure is loud and fail-closed |
| `tip_mutants.py` does not run at 1.0 | unknown | the script crashes, no `result.json` is written, and the outcome is FAIL by construction; fix the harness before re-running under the **same** sidecar. Its non-zero exit on the known p3a floor failure is **not** a crash: the script reads the report JSON (r2, C1) |
| Cache entries built against the old table serve stale verdicts | none by construction | the table digest changes, so entries cool (§16.2.3 / T41 precedent) |
| Tests that re-derive `upstream_nonlegacy` move under the new derive code (L6) | low (OI-12) | the one known consumer, `test_derive.py`'s non-legacy gap-ledger fixture, asserts only unrelated fields; T57's gate runs the whole file |

---

## 18.13 Not in this increment

- **`upstream_nonlegacy`** (L6). It is frozen at `3a50a567f` and not regenerated.
- **The 96-head.** `head96` is still not the channel attribute (tie-break), so its `rollback`/`commit`
  bridges stay unbridged. The `:338` rule applies to `pick_up_tips96`/`drop_tips96` only because it is
  keyed by symbol. That changes no 96-head typestate.
- **Flow-sensitive effects.** The fold stays flow-insensitive, as P4 was (OI-5).
- **Inherited-helper following.** It is not done. The residual is checked at the pin (AC-18.2(k)).
- **Resource-tree modelling of holder-full trackers.** It is not needed while R-C(2) holds.
- **A finer topology conjunct** (per rack, per receiver slot, or loop-body-scoped). This is a named
  follow-up and is decided by §18.9's MARGINAL branch if it fires.
- **The module-level `_spot_trackers` cross-row leak** that the recon suspected
  (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:230`). It is reasoned, not observed, and
  it is a harness-hygiene question, not an analyzer rule. It is filed as a follow-up and not touched
  here.
- **Increment 9's open question** (the move family's refused sites). This increment does not touch it.
- **Precision targets beyond `pick_up_tips`.** `drop_tips`, `aspirate` and the rest keep residual sites
  this increment does not address.

---

## 18.14 Open issues for the adversarial review

Each item is something this document could not verify or had to decide by judgement.

- **OI-1 — RESOLVED in r1 (M10).** §16.2.2's test is amended in its own text (§18.5.2, T60,
  AC-18.10), so no standing text contradicts the field. The residual risk is that the frame condition
  is incomplete, and it lives in A-RACK-STATIC (OI-2). Increment 4's §13.1 lid disposition was still
  not re-read.
- **OI-2 — A-RACK-STATIC (updated r1).** It is a new named assumption, and the owner should confirm it
  explicitly (D2 precedent). One candidate is now closed: `LiquidHandler.assign_child_resource` always
  raises `NotImplementedError`
  (`external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py:2813-2822`), so it cannot
  place a lid. The challenger found that it has a contract key, so disturber condition (c) does not
  apply to it, and that is harmless. **Deferred as a follow-up (orchestrator ruling; backlog #5662):** a whole-surface
  check that no non-family `LiquidHandler` method's closure reaches `assign_child_resource` /
  `unassign_child_resource` on a non-tip resource. The survey does not carry the receiver-type
  resolution that check needs. The `"TOP"` fail-open edge is named in A-RACK-STATIC's row.
- **OI-3 — off-deck racks (updated r1, M6).** r0's claim that conjunct 2 "covers off-deck racks" is
  withdrawn. The rule rests on the harness-grounding premise (§18.5.3). The residual is a program that
  constructs its own off-deck `TipRack` and reaches the rule with a harness-built `env`, which is not
  tested. **Follow-up:** a derived argument binding for module-level delegates, so the rule could check
  that the guard's own spots are declared deck `Ref`s. Every inlined `:338` record today has
  `caller_args: null` and `caller_args_sites: []`, so no existing table supplies this, and a
  hand-typed parameter name is forbidden (L0/HM-26).
- **OI-4 — RESOLVED (owner ruling 260929): book HM-25 12 → 13.** R-A/R-B/R-C(2) form one HM-25 unit
  (AC-18.17, T57). The zero-cost alternative ("P4 was never booked") was considered and declined.
  R-A and R-C(2) are patterns over how PLR is written, the class of fact whose silent breakage caused
  this regression.
- **OI-5 — flow-insensitivity and the holder-less path (updated r1).**
  - **The polarity half is confirmed.** The holder path unassigns the spot's current child and assigns
    the new tip (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:88-96`), which is the same
    polarity as the holder-less write. AC-18.9's holder-full check tests it empirically.
  - **The R-C(2) half remains.** It fails closed only while the holder-selecting parameter has a `None`
    default (m2). A required or non-`None`-default holder would pass it vacuously.
- **OI-6 — `COPY` replaces the recon's ≥ 1-argument filter.** This is a deliberate deviation. `COPY`'s
  identity semantics inherits A-COMMIT, whose verified scope is `pick_up_tips`/`drop_tips` boundaries
  (increment 1 §10.2.2). A new `LiquidHandler` method bridging only `rollback` at depth 0 would get no
  effect. That would be sound only under A-COMMIT at that method's boundary.
- **OI-7 — "direct methods only".** The PLR base-closure check (AC-18.2(k)) guards it at the pin, but a
  third-party mixin outside the PLR tree would be invisible.
- **OI-8 — beyond-parity refinements.** These go beyond parity: "optional parameter → UNRESOLVED",
  "free name → UNRESOLVED", and (r1) B1's "every non-`None` expression → UNRESOLVED". Their effect at
  1.0 is predicted to be zero (§18.4.9, reasoned; the defender traced B1). On the old-pin source, B1
  moves exactly one value, `load_state`, which is the intended L1 divergence (OI-9).
- **OI-9 — the old-pin value, now DERIVED (r1).** The old-pin PLR source is on disk in the sibling
  worktree `outputs/pr159` (tracker at `pylabrobot/resources/tip_tracker.py`). It was read for this
  revision. The old P4 effects were:
  - `add_tip` HAS_TIP (`self._pending_tip = tip`, line 93);
  - `remove_tip` NO_TIP (line 106);
  - `clear` NO_TIP (lines 127-128);
  - `load_state` HAS_TIP (lines 141-142, two `cast(…, deserialize(…))` writes).

  The only old-pin `head[...]` bridge to `load_state` is `LiquidHandler.load_state` (pr159
  `pylabrobot/liquid_handling/liquid_handler.py`, line 250). Under §18's rules the old-pin classes are:
  - `add_tip` HAS_TIP, since `tip` is an annotated entry parameter;
  - `remove_tip` and `clear` NO_TIP;
  - `load_state` UNRESOLVED, since its writes are `Call`s (B1).

  So exactly one channel-effect divergence is expected, `LiquidHandler.load_state` HAS_TIP → widen.
  T59's generated fixture, read from the old-pin **artifact**, remains the authority. Tests use inline
  fixtures (AC-18.2(l)), never that path.
- **OI-10 — RESOLVED in r1 (M8).** 205 remains a stated judgement. 123 is now called an anchor, not a
  derivation. The topology declines are reconciled against an independent scan as a hard term, and the
  FAIL decision attributes its cause through the published decline counters.
- **OI-11 — the "rollback never bridged" claim.** It is verified only by the absence of the string from
  the 1.0 survey. If a future survey records `IfExp`-callee attributes, `rollback` becomes bridged. It
  classifies `UNTOUCHED` (`COPY`), so there is still no effect, but that rests on OI-6.
- **OI-12 — L6 (updated r1).** The one known consumer is `test_derive.py`'s non-legacy fixtures
  (`plr-sema/tests/test_derive.py:596-622`). They rebuild a gap ledger from the committed non-legacy
  survey through `build_gap_ledger`, and assert only fields unrelated to §18. The risk is low, and
  T57's gate runs the whole file. No other re-deriving test was found, but this was not an exhaustive
  search.
- **OI-13 — the behavioural oracle's import-order caveat and `Tip` construction.** Both come from the
  recon and were not re-verified. The test fails rather than skips, so the gap cannot pass silently.
- **OI-14 — CLOSED in r1.** `calls_from_plr_kwargs` prepends a `setup` `CALL`
  (`plr-sema/eval/oracle_common.py:649-651`), and `evaluate_call` fires `entry_reset` on it. It is not a
  topology disturber (§18.5.4).
- **OI-15 — R-E's breadth.** A class that is both a legitimate receiver and another candidate's tracker
  is dropped. There is no instance at 1.0, and it fails closed.
- **OI-16 — HM-26 headroom.** `declared == live` (4/4) follows HM-26's precedent, not §9.1's live+2.
- **OI-17 — ANSWERED and CLOSED in r2 (C5, D-4).**
  - PLR 1.0 accepts a real `Lid` on a `TipRack`, because it is `Liddable`.
  - The harness could not build one. T60 now adds `DeckLayout.lidded_tip_racks` and has `build_setup`
    assign a real `Lid`.
  - m3b is dropped.
  - The r1 fallback text was wrong. An unbuildable m3 gives `runtime_raised_m3 = 0`, which is in hard
    block H, so the outcome is **FAIL**, not MARGINAL.
- **OI-18 — CLOSED in r2 (C7).** The m3 branch lives in `tip_mutants`, placed before the criterion-(iii)
  `elif`. Its hard violations are `static_338_safe > 0` and `runtime_raised == 0`, and criteria (i)
  and (ii) apply generically. `mutants_gate_passed` is replaced by
  `mutants_hard_violations_excl_p3a_floor`.
- **OI-19 — CLOSED in r2 (C14).** `n_contracts_depth0_and_deep_coexist` is published, predicted 0. The
  M11 counter catches any moved key, and `update_head_state` widens at both pins.
- **OI-20 — CLOSED in r2 (C2).** The entry context is now an allowlist on the annotation's node shape,
  `Name(T)` / `Attribute(attr=T)` / `Constant(T)`, with `T` derived over `W`. Unannotated parameters,
  and anything else, are `UNRESOLVED`. It costs zero at both pins.
- **OI-21 — RESOLVED (owner ruling 260929): A-CALLBACK-INERT is ACCEPTED as a named assumption.**
  - **Checked at the pin (AC-18.2(q)).** The head trackers' callback is `LiquidHandler._state_updated`,
    which is `Resource._state_updated`, a notifier.
  - **Assumed.** The user-registered state-update callbacks it forwards to do not write a head
    tracker. That is not checkable from PLR source.
  - **It is added to increment 1's §10.6.3 assumption table**, taking the table to seven rows together
    with A-RACK-STATIC. T61 lands the row and the table test at seven.
  - **Implementation-time check (T57).** Before regenerating, grep praxis's own state-update callback
    registrations, in `web-repl/` and in visualizer or REPL state-sync code, and confirm they only
    serialize. **If any one writes a tracker, STOP and ask.**
  - **FOLLOW-UP, not in #5622's scope; filed as backlog #5661.** A fail-closed guard: any analysed
    protocol that registers its own state-update callback makes tip state `UNKNOWN`. That turns this
    assumption into a check.
- **OI-22 — NEW in r2: the `_before` writer snapshot will churn with PLR.** **Round-3 classification:
  non-blocker. The churn is the intended loud-over-silent trade.**
  - C9 pins seven writers of `_before`. Any PLR refactor of the transaction bookkeeping breaks the
    snapshot and forces a re-adjudication, even when it is harmless. That is the intended trade: loud
    over silent.
  - The snapshot pins **which** methods write `_before`, not **what** they write. A changed value in
    an existing writer (for example, `commit` writing a tip instead of the sentinel) would pass it.
    Only A-COMMIT plus the load_state widening cover that case at the pin.
- **OI-23 — CLOSED in r3 (not an issue).** The scope limit below is stated in §18.9 (C16), and no claim
  depends on it. It is kept for the record:
  - Every m3 row lids the rack in the layout, so the site rule declines at `"observation"` and never
    reaches the topology conjuncts.
  - m3 is therefore a live falsifier of a wrong `SAFE` only if some implementation bug made the
    observation conjunct pass on a lidded deck, which is exactly what `static_338_safe_on_m3 = 0`
    watches.
  - It says nothing about topology. That is stated in §18.9 (C16) and repeated here, so no reader
    over-credits the run.
- **OI-24 — CLOSED in r3 (not an issue).** `Liddable.assign_child_resource` raises only on an existing
  lid, or on a lid undersized beyond `LID_UNDERSIZE_TOLERANCE`. `location` is optional
  (`external/pylabrobot/pylabrobot/resources/lid.py:104-122`, verified this revision).
  - T60 sizes the `Lid` to the rack's own dimensions, uses a nonzero `nesting_z_height`, and gives it
    a deck-unique name.
  - AC-18.10's lidded fixture proves `rack.lid is not None` and `_available_for_tip_handling is False`
    after `build_setup`.

---

## 18.15 Where this document departs from the recon, or found it wrong

| recon said | this document | why |
|---|---|---|
| R-B: "follow only calls with ≥ 1 argument" | follow **all** resolved self-calls; `COPY` stops the poisoning | the filter is unsound for zero-argument constant-writing helpers (§18.4.3, AC-18.2(d)) |
| "writes of both kinds → no effect" was inherited silently | both kinds → `UNRESOLVED` → `widen` when bridged | L1 applied consistently; §10.2.4 amended (§18.4.4) |
| R-D: do not publish private helpers | same, **plus** a bridge to any private method widens | publication hygiene must not be able to hide a classification from the bridge |
| "`rollback` (now `raise RuntimeError`, never bridged)" | `rollback`'s body is `self._put(self._tip)`; it raises only when disabled (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:181-186`). "Never bridged" holds for `head` only: the survey does record `self.head96[i].rollback` | read at the pin; `head96` is not the channel attribute |
| the spurious receiver is `TipTracker` | also found `LiquidHandlerBackend` (`_head` → `TipTracker`) in the 1.0 artifact; R-E keeps it | read from `plr-sema/data/derived_contracts.json` |
| R-A: "bare `return self.X`" | same, but it recurses through properties, and the exclusion of `_before` is shown to rest on the `cast(...)` wrapper | the fragility is pinned by AC-18.1 |
| move-family conjunct over `move_lid`/`move_plate`/`move_resource` | derived via `anchor_net_effects ∈ {EMPTY, HELD}`, giving five methods incl. `pick_up_resource`/`drop_resource`, plus other-receiver / no-contract / `receiver_type is None` disturbers | no hand-typed names; closes direct `pick_up_resource`/`drop_resource` calls |
| `:338` rule reads the observation alone | adds `deck_resources_verified` (defence in depth only, after r1's M6) and `rack_topology_stable` conjuncts, plus a `raise_guard` kind check | L3's frame condition; the off-deck residual stays in OI-3 |
| (recon silent on value forms) | r1: any non-`None` expression value is `UNRESOLVED` (B1), and rebound parameters join (B2) | the recon's P4-parity row reproduced the old `load_state` unsoundness on the old-pin source |
| R-C: seed `_constructor_state` with the backing fields | same, plus R-C(2), the holder-less construction conjunct | `_carried` backs `_pending_tip` only on the holder-less path |
| the recon's exploratory 11/11 | not cited as evidence; 10/11 is the owner's expected parity, and the fixture generator is the authority | the recon's own provenance note |
| `tip_rack.py:355-363`, call sites `:721 :872 :1706 :1787`, `liquid_handler.py:418, 421, 469, 476` | **confirmed** at `786ac2c4e` | read this session |

---

## 18.16 Implementation record

*(Filled by T64. First-column ids are deliberately unbolded so the cross-reference lint does not read
this table's cells as gate cells.)*

| row | commit | what landed | measured vs the spec's expectation | divergences |
|---|---|---|---|---|
| T57 | — | — | — | — |
| T58 | — | — | — | — |
| T59 | — | — | — | — |
| T60 | — | — | — | — |
| T61 | — | — | — | — |
| T62 | — | — | — | — |
| T63 | — | — | — | — |
| T64 | — | — | — | — |

---

## 18.17 Revision log

**r1 (260929): adversarial round 1.** The challenger returned REVISE: 2 blockers, 11 major and 16
minor objections. The defender also returned REVISE, conceding 20, partially conceding 10 and
rebutting none. The binding list of changes is the orchestrator's `adjudication_r1.md`, and every item
on it is applied. L0–L7 are unchanged.

| id | change | where |
|---|---|---|
| B1 | `cls_E`: any non-`None` `Constant`, `Call`, `Subscript`, `BoolOp`, `Await`, non-`W` attribute or other expression → `UNRESOLVED`. Inline old-pin `load_state` fixture added. The L1 claim is rewritten so it no longer rests on the `IfExp` | §18.0, §18.4.3, §18.4.4, AC-18.2(l)(m) |
| B2 | A parameter rebound in the body joins `E[n]` with every binding; non-`=` binding forms give `UNRESOLVED`; negative control added | §18.4.3, AC-18.2(n) |
| M1 | Bridge rules run before the index skip. New rule 0: a bridge to a method that is not a direct method of `C`, or not in the index, sets `any_unresolved` | §18.4.4, AC-18.3 |
| M2 | Rule change: widen when depth-0 and deep effects coexist. Increment 1's E2 amended | §18.4.4, amendment box, T64, AC-18.3, AC-18.15 |
| M3 | Assignment to a property `F ∈ S` gives `UNRESOLVED`. Two checked tripwires added (hidden writers of non-alias getter dependencies; writing getters). r0's "What R-A is NOT" replaced | §18.4.2, §18.4.3, AC-18.1 |
| M4 | `effects_max_depth` defined structurally: the longest followed-call chain ending in a `W` write, over entries (public methods + `__init__`), independent of evaluation order | §18.4.3, AC-18.2(p) |
| M5 | Family pinned on the shipped table; AC-18.11(d) runs on shipped contracts; `"TOP"` named fail-open in A-RACK-STATIC. The whole-surface closure check is deferred to OI-2 | §18.5.4, §18.5.5, AC-18.11(d)(i), OI-2 |
| M6 | Conjunct 2 rationale rebuilt on the harness-grounding premise; the "covers off-deck racks" claim withdrawn; no argument-reading conjunct (no derived table supplies one); follow-up recorded in OI-3 | §18.5.3, OI-3 |
| M7 | Sidecar: `mutants_gate_passed`, `mutants_criterion_ii`, `p3a_floor_met`, attempted/achieved floors, a v1 class, and the new m3 lidded-rack mutant with hard terms `static_338_safe_on_m3 = 0` and `runtime_raised_m3 > 0`, owned by T63 | §18.9, AC-18.16, T63 |
| M8 | Hard term `n_338_declined_topology = n_pickups_with_preceding_disturber_indep` from an independent scan; loop-clause declines reported separately; the FAIL decision attributes its cause; 123 reframed as an anchor | §18.9, OI-10 |
| M9 | `plr-sema/tests/test_tips_dirty_cost.py` added to T62's gate | §18.6, AC-18.5, T62 |
| M10 | §16.2.2 amended in its own text (frame-condition clause), in T60 and AC-18.10 | §18.5.2, AC-18.10, T60, OI-1 |
| M11 | New 1.0 keys absent from the baseline fail unless listed; `baseline_divergences` defined over the key union with absence as a value, and equal to `len(intended_divergences)` | §18.8(1), AC-18.7, §18.9 |
| m1 | `_before` note corrected: `_NOTHING_PENDING` is a global, so `UNRESOLVED`; both pickup and drop would widen, and `entry_reset` would vanish | §18.4.2, §18.12 |
| m2 | R-C(2) fails closed only with a `None`-default holder parameter | §18.4.5, OI-5 |
| m3 | The pre-scan function returns pc → `(receiver_type, classes)` | §18.5.4, T61 |
| m4 | AC-18.11(b) is 3×3×3 | AC-18.11(b) |
| m5 | The rule declines unless `kind == "raise_guard"` | §18.5.3, AC-18.11(b), T61 |
| m6 | Catch-alls: unlisted binding forms including `import`; `staticmethod`/`classmethod` callees; calls that do not bind | §18.4.3, AC-18.2(o) |
| m7 | Expected `LiquidHandlerBackend` block added | §18.4.8 |
| m8 | "Bridge" defined; invariant (f) moved to a pin-scoped assertion | §18.4.4, §18.8(2), AC-18.8 |
| m9 | Check fixture for the `load_state`/`update_head_state` channel-set reset | §18.6, AC-18.5 |
| m10 | Premise stated: an un-planned call means the runtime raised there | §18.5.3 |
| m11 | AC-18.9 gains a holder-full polarity check and a rollback-after-uncommitted-`add_tip` witness | §18.8(3), AC-18.9 |
| m12 | One raising read nulls the whole observation record; stated and accepted | §18.5.2 |
| m13 | Tier-2 file named (`test_tier2.py`); a measured golden that is not 44 is recorded, not edited to match | AC-18.13, T62 |
| m14 | Citation widened to `tip_tracker.py` 74-96 | §18.3 |
| m15 | T61 depends on T57 + T60; the ordering box matches the table | §18.11 |
| m16 | An R-A alias `X` must name no direct `FunctionDef` of `C` | §18.4.2, AC-18.1(f) |
| OI-9 | Derived from the old-pin source; T59 stays the authority | OI-9, §18.8(1) |
| OI-14 | Closed (the prepended `setup` is not a disturber) | §18.5.4, OI-14 |
| OI-2/5/12 | Updated as ruled | §18.14 |
| OI-4 | T57 defaults to the booking option | §18.7, OI-4 |
| OI-1/3/10 | Resolved by M10/M6/M8 | §18.14 |

New open issues created by this revision: OI-17 (can the m3 mutant be built), OI-18 (where the m3
criterion-(iii) exclusion should live), OI-19 (M2's breadth beyond tip effects) and OI-20 (unannotated
entry parameters still default to `HAS_TIP`).

**r2 (260929): adversarial round 2.** The challenger returned REVISE: 4 blockers (C1–C4), 6 major
(C5–C10) and 7 minor (C11–C17). The defender conceded every blocker, with corrected fixes, and
partially conceded C8, C9 and C13. The binding list is the orchestrator's `adjudication_r2.md`; where
the defender's corrections differ from the challenger's, the defender's are applied. Orchestrator
rulings are D-1 (p3a reported only), D-2 (option (B)), D-3 (included) and D-4 (m3b dropped). L0–L7
are unchanged.

| id | change | where |
|---|---|---|
| C1 | `mX_attempted := n_raised_as_expected`; `mutants_gate_passed` replaced by `mutants_hard_violations_excl_p3a_floor = 0`; reports read as JSON, never by exit code; PASS/MARGINAL/FAIL re-derived as `H∧X` / `H∧¬X` / `¬H` | §18.9 sidecar and field definitions, §18.12 |
| C2 | Entry context is a node-shape allowlist; `T` is derived over `W` and must be a singleton, never via `_unwrap_annotation(param) == T`; the §18.4.3 contradiction fixed; zero cost at both pins shown; OI-20 closed | §18.4.3, AC-18.2(s), OI-20 |
| C3 + D-3 | Tip-write catch-alls: Store/Del-context `self.<W>`, `setattr`/`delattr`/`object.__setattr__`/`__delattr__` on `self`, `self.__dict__`/`vars(self)`, bare `self` passed to an unfollowed call; zero cost at both pins shown | §18.4.3, AC-18.2(t) |
| C4 + C13 + D-2 | `tip_racks_decline_reason` factored out (order kind → observation → deck → topology_prefix → topology_loop); two `_Ctx` fields replace `rack_topology_stable`; counters scoped to planned pickups carrying `:338`; hard terms `n_338_declined_unattributed = 0` and `n_338_safe_with_reason = 0`; M8 term restricted to kind∧observation∧deck; analyzer-side reason computed in T63 via `FINDINGS_SINK` + `LOWERED_SINK` (option (B)), with nothing threaded through `check/`; every schema field defined | §18.5.3, §18.5.4, §18.5.6, §18.9, AC-18.11(b), T61, T63 |
| C5 + C16 + D-4 | `DeckLayout.lidded_tip_racks` and a real `Lid` in `build_setup`, owned by T60 with a default-layout-unchanged test; m3 reuses it; m3b dropped; AC-18.11(f) uses a real `Lid`; `runtime_raised_m3` keyed on the `:338` message or frame at the pickup index; an unbuildable m3 gives FAIL; "the one in-run falsifier" narrowed to the observation conjunct | §18.5.2, §18.5.5, §18.9, AC-18.10, AC-18.11(f), T60, §18.12, OI-17 |
| C6 + C7 | `run_one_mutant` captures site-keyed verdicts through a chain-composed `FINDINGS_SINK` (defaulted trailing `MutantResult` field); `static_338_safe_on_m3` defined on them; m3 added to `_MUTATORS`/`_EXPECTED_EXC`/`by_class`, with a branch before the criterion-(iii) `elif`; OI-18 closed | AC-18.16, T63, OI-18 |
| C8 + C9 | Dependency set over the whole getter body, through properties, over every `S` getter: bool-view `{_holder_ref}`, all getters `{_holder_ref, _before}`; pinned writer snapshots for both | §18.4.2, AC-18.1 |
| C10 | Locals evaluated as a least fixpoint; fixture added | §18.4.3, AC-18.2(r) |
| C11 | Plain field only if nothing in `C` or its PLR base closure binds `F` at class level | §18.4.2, AC-18.2(u) |
| C12 | HM-25 split out as AC-18.17, gated by T57 (each AC still gated exactly once) | AC-18.12, AC-18.17, T57 |
| C14 | `receiver_state_diagnostics.n_contracts_depth0_and_deep_coexist` published (predicted 0); OI-19 closed | §18.4.4, §18.4.8, OI-19 |
| C15 | `register_callback` arguments are all `self._state_updated`, a notifier; checked in AC-18.2(q); downstream callbacks assumed (OI-21) | §18.4.3, AC-18.2(q), OI-21 |
| D-1 | p3a is reported only (`p3a_attempted`, `p3a_achieved`), with criteria (i)/(ii) hard | §18.9 |

**Zero-cost statement (r2).** C2, C3 and D-3 each cost **zero recovered effects at 1.0 and at the old
pin**. The evidence is in §18.4.3:

- the only positive entry parameter, at both pins, is `add_tip`'s `tip: Tip`, a bare `Name`;
- neither tracker has a `for`/`with` target on a write target, a `setattr`/`delattr`/`__dict__`/`vars`
  use, or a bare `self` argument;
- `T = {"Tip"}` is derived at both pins.

C10, C11 and C8/C9 are likewise zero-cost: no self-referential locals, no class-level bindings of an
`S` field, and assertions only. The value tables in §18.0, §18.4.8, AC-18.2/18.3/18.4 and the sidecar's
predictions are therefore unchanged from r1.

New open issues created by r2: OI-21 (A-CALLBACK-INERT), OI-22 (writer-snapshot churn, and value
changes it cannot see), OI-23 (m3 covers only the observation conjunct), OI-24 (the `Lid` sizing
tolerance is the challenger's reading).

**r3 (260929): adversarial round 3, the convergence round.** The challenger found every
`adjudication_r2` item applied, with no regressions in the value tables, AC gating, task dependencies
or file ownership. It returned REVISE for two narrow fixes plus minors, and all of them are applied.
L0–L7 are unchanged.

| id | change | where |
|---|---|---|
| X1 | D-3 generalised: any Load of `Name("self")` that is not an `Attribute` base makes the method `UNRESOLVED`. This covers `self._h(self)` and local aliasing (`me = self`, `t = self`). Zero cost at both pins: the only non-attribute `self` token in either tracker is `add_tip`'s parameter declaration, which is an `ast.arg`, not a Load | §18.4.3 table and cost box, AC-18.2(t) |
| X2 | Producers named: the wrapped `oc.observation_env_members` (called at `oracle_common` line 1003; chain-composed; position-correlated with a three-way length invariant, as at `t30_measure` line 677) supplies `env`; `LOWERED_SINK`'s `bc` supplies topology; a hard no-`ir.Loop` assertion makes loop declines 0 by construction, and a loop gives FAIL-with-cause; `run_static_calls` unchanged | §18.9 item 7, M8 field definition |
| minor 1 | `T = {P1a(C)[x] : …}`; `_annotated_attributes` already unwraps | §18.4.3 |
| minor 2 | Locals are a Kleene least fixpoint from `⊥` (`⊥ ↦ UNRESOLVED`), independent of query order and memoisation; fixture `a = b; b = a; b = None` | §18.4.3, AC-18.2(r) |
| minor 3 | "Writes `self.a`" means the full write-shape set, catch-alls included; `_attribute_writers` must not be reused (it misses `__init__`'s `AnnAssign` of `_before`, legacy tracker line 46) | §18.4.2 |
| minor 4 | Second defaulted `MutantResult` field `runtime_error`; report keys `n_runtime_raised_at_338` / `n_static_338_safe`; the rack name is taken from the pickup's `at`, and `deck_layout` of `None` is handled; `m1_will_fail_fired` / `m2_will_fail_fired` defined | §18.9, field definitions, AC-18.16 |
| minor 5 | FAIL tests `n_338_declined_unattributed != 0` (a signed difference), keeping the outcomes exhaustive; status line updated to r3; T57 sizing made consistent (~330) | sidecar, header, §18.11 |
| OI-21/22 | Classified non-blocker; OI-21 needs the owner's ruling before any soundness claim outside the harness | §18.14 |
| OI-23/24 | Closed (not issues); OI-24 records PLR's `lid.py` placement rule (lines 104-122) and T60's `Lid` parameters | §18.14, §18.9 |

**Final (owner rulings), 260929.** Round 4 returned ACCEPT, and the status was marked converged. The
owner then ruled, and these are applied here. L0–L7 are unchanged, and PASS/MARGINAL/FAIL are
unchanged: `pass = H∧X`, `marginal = H∧¬X`, `fail = ¬H`, exhaustive.

| id | ruling / change | where |
|---|---|---|
| OI-21 | ACCEPTED A-CALLBACK-INERT as a named assumption. Its row text is fixed in §18.5.5, and T61 adds it with A-RACK-STATIC to increment 1's §10.6.3 table (five rows to seven), moving the table test to seven in the same task. It is not added at finalization, so `main` stays green when the spec merges. Also added: T57's implementation-time grep of praxis's own callback registrations (STOP if one writes a tracker), and a FOLLOW-UP for backlog, outside #5622: a fail-closed guard that makes tip state `UNKNOWN` for any protocol registering its own state-update callback | §18.4.3 C15 box, §18.5.5, AC-18.11(h), T57, T61, OI-21, increment 1 §10.6.3 |
| OI-4 | Book HM-25 12 → 13. The conditional wording is removed; the zero-cost alternative is recorded as declined, because R-A/R-C(2) are patterns over how PLR is written, the class of fact whose silent breakage caused this regression | §18.7, AC-18.17, T57, OI-4 |
| scheduling | Preemption-safe, resumable measurement: seven units (two arms, five mutant classes), each persisted with a sha256 stamp, reused only on matching hashes, in its own subprocess with a 30-minute timeout and no whole-run timeout; an incomplete unit means no `result.json`, which is FAIL by construction. Specified in §18.9's prose **and** the sidecar comment block, so the committed sidecar still matches §18.9. Resumability tests (a)(b)(c) and a negative control are added to AC-18.14 | §18.9, sidecar, AC-18.14, T63 |

---

## References

- Recon: `.praxia/docs/research/260929_plr-sema-tip-effects-plr1-recon.md` (mechanics, R-A to R-D, the
  `:338` analysis, drift-test shapes; its *(exploratory)* numbers are not cited).
- Gate report: `outputs/plr-sema/260929_plr10_wsC_gate1_report.md` (RC-1/RC-2, V5 hole, golden moves).
- Characterisation: `plr-sema/eval/plr10_characterize.bth.toml`, `plr-sema/eval/plr10_characterize.py`,
  `outputs/plr-sema/plr10_char_260929/result.json`, `outputs/plr-sema/plr10_char_260929/real.oracle_replay.json`
  (bathos run `fd63e9cd`).
- Old-pin baseline: `outputs/plr-sema/unknown_ledger_260911_volwire.oracle_replay.json`.
- Increments amended or anchored: `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md`
  (§10.2.2, §10.2.4, §10.4, §10.6.3), `.praxia/docs/specs/260903_plr-sema-volume-increment.md` (§14.5 V5
  and its 260929 amendment), `.praxia/docs/specs/260909_plr-sema-observation-increment.md` (§16.2.1,
  §16.2.2, §16.2.3, §16.9, D6), `.praxia/docs/specs/260909_plr-sema-move-family-increment.md` (§17.0.1
  move family, §17.3 `arm_slots` precedent, §17.4 P5/P6), `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md`
  (§9.1, §9.4).
- Code read this session: `plr-sema/src/plr_sema/derive/receiver_state.py`,
  `plr-sema/src/plr_sema/check/tipstate.py`, `plr-sema/src/plr_sema/check/volumestate.py`,
  `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/src/plr_sema/check/__init__.py`,
  `plr-sema/src/plr_sema/_hand_maintained.py`, `plr-sema/eval/oracle_common.py`,
  `plr-sema/eval/tip_mutants.py`, `training/verify/deck.py`, `training/verify/verifier.py`,
  `plr-sema/tests/test_spec_lint.py`, `plr-sema/scripts/check_spec_citations.py`,
  `plr-sema/scripts/check_spec_crossrefs.py`.
- PLR 1.0.0b1 (`786ac2c4e`): `external/pylabrobot/pylabrobot/legacy/tip_tracker.py`,
  `external/pylabrobot/pylabrobot/legacy/liquid_handling/liquid_handler.py`,
  `external/pylabrobot/pylabrobot/resources/tip_rack.py`,
  `external/pylabrobot/pylabrobot/resources/tip_tracker.py` (the deprecation shim).

