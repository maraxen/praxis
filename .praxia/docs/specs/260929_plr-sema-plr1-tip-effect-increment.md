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
> named where it happens and each landed by a task row: increment 1's §10.2.4 P4 rule (the
> "both kinds → no effect" clause, §18.4.4) and its §10.6.3 assumption table (one new row,
> §18.5.5); and increment 7's §16.2.1 closed observation record (one new field, §18.5.2). Increment
> 5's V5 rule, including its 260929 amendment, is **unchanged** (L5). `schema_version` stays 1,
> `REASON_VOCABULARY` gets no new member, and no new registry row is added (L0).
>
> **Status: DRAFT for adversarial review.** Where this document asserts a number it names the file it
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
it: `load_state`'s conditional tip now widens rather than asserting `HAS_TIP` (L1). Finally it decides
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
  `self._carried = tip` (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:80-96`, the
  write at `:86`).
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
body named `F` whose `decorator_list` contains the bare `Name("property")`. If `F` has no such getter,
it is a plain field and contributes nothing to `B`, which is the old-pin case.

Walk every `ast.Return` inside `G_F`, descending into `If`/`Try`/`With` bodies but not into nested
`FunctionDef`/`Lambda`/`ClassDef`. Then apply these rules to each return value:

| return value's AST, exactly | contribution |
|---|---|
| `Attribute(value=Name("self"), attr=X)`, where `X` is **not** a property of `C` | `X` joins `B` |
| `Attribute(value=Name("self"), attr=P)`, where `P` **is** a property of `C` | recurse into `G_P`, with the property names already visited as the cycle guard (a revisit contributes nothing) |
| anything else: a `Call` (including `cast(…, self.X)`), a non-`self` attribute (`holder.tip`), a `Name`, a `Constant` | nothing |

`B` is published sorted (§18.4.8). **At 1.0:** `_pending_tip` returns `self._carried`, which gives
`B ∋ _carried`. It also returns `holder.tip`, which contributes nothing. `_tip` returns
`self._pending_tip` (a property, so the rule recurses and again reaches `_carried`) and `cast(…, self._before)`,
which contributes nothing. **So `B = {_carried}` and `_before` is excluded.**

> **The `_before` exclusion rests on one syntactic accident, and this document says so.** `_before` is
> left out only because the 1.0 source wraps it in `cast(...)`. If PLR removed the `cast`, `_before`
> would join `B`, and three things would follow *(reasoned from §18.4.3's fold)*:
>
> - `commit`'s `self._before = _NOTHING_PENDING` would classify `HAS_TIP`, because it is a bare `Name`,
>   not a `W` read.
> - `remove_tip` follows `self.commit()`. Its result would become `{NO_TIP, HAS_TIP}`, which is
>   `UNRESOLVED`.
> - `drop_tips` would then widen instead of carrying `NO_TIP`.
>
> That is a silent **precision** loss, not an unsoundness, and precision losses are exactly what nobody
> notices. **AC-18.1 pins `effect_backing_fields == ["_carried"]` at the pin**, so the change fails
> loudly in CI rather than quietly in a number. §18.8's cross-pin fixture is a second, independent
> tripwire, because `drop_tips` would move off `NO_TIP`.

**What R-A is NOT.** It does not read property **setters**. The recon found them irrelevant, and this
document agrees for a different reason. An assignment `self.<F> = v` with `F ∈ S` is already a tip
write under the unchanged old rule. What the setter does internally (at 1.0, writing `_before`) is a
concrete-state detail, and the merged cell abstracts it away. No 1.0 method assigns `_tip` or
`_pending_tip`, so the question has no instance at the pin.

### 18.4.3 R-B — argument-classified helper following

**Scope of a method body.** "The body of `m`" is every node reachable from `m.body` without entering a
nested `FunctionDef`, `AsyncFunctionDef`, `Lambda` or `ClassDef`. This is a deliberate narrowing of
today's `ast.walk(member)`, which enters nested definitions. Code in a nested definition does not run
when `m` is called. No 1.0 `TipTracker` method contains one *(verified by reading the file)*.

**Tip writes in a body.**

| statement shape | class contributed |
|---|---|
| `Assign`, or `AnnAssign` with a value, whose target is `self.x` with `x ∈ W` | `cls(value)` (table below). An `Assign` with several targets is classified once per `W` target |
| `AugAssign` on `self.x`, `x ∈ W` | `UNRESOLVED` |
| a `Tuple`/`List` target containing `self.x`, `x ∈ W` | `UNRESOLVED` |
| `Delete` of `self.x`, `x ∈ W` | `UNRESOLVED` |
| any assignment to `self.y`, `y ∉ W` (e.g. `_before`, `_tip_origin`) | nothing |

**Self-calls.** Every `ast.Call` in the body, at any expression position (statement, RHS, argument,
`await`), whose `func` is exactly `Attribute(value=Name("self"), attr=h)` is a candidate self-call to
`h`. **"Same class" means the direct methods of `C`**: `FunctionDef`/`AsyncFunctionDef` nodes that are
immediate children of `C`'s `ClassDef`, with no base-class resolution and no subclass overrides. The
candidate is resolved as follows:

- `h` names exactly one direct method with no `property`/`<name>.setter` decorator: **follow it** (below).
- `h` names more than one direct definition, or only a property: the call contributes `UNRESOLVED`
  (fail-closed, and there is no instance at 1.0).
- `h` names no direct method: **not followed, contributes nothing.** This covers inherited methods
  and callable attributes. The 1.0 instance is `commit`'s `self._callback()`
  (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:172-179`), where `_callback` is an instance
  attribute set by `register_callback`, not a method.

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
   in order, and `kⱼ=vⱼ` bind by name.
2. Each bound parameter gets `cls_E(argument)`.
3. An unbound parameter gets `cls(default)` if it has a default, and `UNRESOLVED` otherwise.
4. If the call site contains `ast.Starred` or `**`, or `h`'s signature has `*args`/`**kwargs`, **every**
   parameter of `h` gets `UNRESOLVED`.

**The argument/value classification `cls_E(e)`.** The first matching row wins.

| `e` | class |
|---|---|
| `Constant(None)` | `NO_TIP` |
| any other `Constant` | `HAS_TIP` (the old P4 "anything else non-`None`" rule, unchanged) |
| `Attribute(Name("self"), x)` with `x ∈ W` | `COPY` |
| `IfExp(test, body, orelse)` | `join(cls_E(body), cls_E(orelse))` |
| `Name(n)` with `n ∈ E` (a parameter of the current method) | `E[n]` |
| `Name(n)`, a local of the current method | `join` of `cls_E(v)` over **every** binding `n = v` in the body. Any other binding form of `n` (tuple unpack, `for`/`with`/`except` target, walrus, `AugAssign`, `global`/`nonlocal`) gives `UNRESOLVED` |
| `Name(n)` bound nowhere in the method (a global or free name) | `UNRESOLVED` |
| anything else (`Call`, `Subscript`, a non-`W` attribute, `BinOp`, …) | `HAS_TIP` (old P4 rule, unchanged) |

`join(x, y) = x` if `x == y`, and `UNRESOLVED` otherwise.

**Entry context.** When a method `m` is classified on its own (the top of a derivation, not a followed
call), each parameter `p` of `m` gets:

- `UNRESOLVED` if `p`'s default is `Constant(None)`, or if its annotation is optional. Optional means
  `Optional[…]`, `typing.Optional[…]`, `X | None` / `None | X`, or a string constant whose
  `ast.parse(…, mode="eval")` body is one of those.
- `HAS_TIP` otherwise, which is the old rule for a parameter.

At 1.0, `add_tip(self, tip: Tip, …)` gives `tip ↦ HAS_TIP` (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:137-159`).

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
bounded by the number of direct methods of `C`. The artifact publishes `effects_max_depth`, the
largest stack depth at which any tip write or followed call was examined while classifying any method
of `C`, with the method's own body counted as depth 0. The expected value at 1.0 is **2**
(`add_tip` → `_hold` → `_put`).

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

**The bridge (normative change to `compute_channel_bridge`).** During the closure walk, for each matched
bridge `self.<channel_attr>[…].<m>`:

1. If `m ∈ effects_unresolved`, set `any_unresolved = true`, at any depth.
2. Else if `m` begins with `_`, also set `any_unresolved = true`. A private tracker method is never
   published, so a bridge to it cannot be justified from the artifact. AC-18.3 asserts that no bridged
   method at the pin is private.
3. Else, the existing depth-0 / deep bookkeeping over `effects.get(m)` applies, unchanged.

`channel_effect` is then `"widen"` if `any_unresolved`. Otherwise the existing three-way outcome at
`plr-sema/src/plr_sema/derive/receiver_state.py:1576-1582` applies unchanged. **Unresolved takes
precedence over everything.** Check-side needs **no change**: `_apply_transfer` already widens the
whole receiver on `"widen"` (`plr-sema/src/plr_sema/check/tipstate.py:568-596`), and V5 already
treats `"widen"` as a departure (`plr-sema/src/plr_sema/check/volumestate.py:547-588`).

**The `load_state` case, end to end.** `TipTracker.load_state` binds
`pending_tip = Tip.deserialize(pending_tip_data) if pending_tip_data is not None else None` and then calls
`self._put(pending_tip)` (`external/pylabrobot/pylabrobot/legacy/tip_tracker.py:201-211`). The local's
one binding is an `IfExp` whose arms classify `HAS_TIP` (a `Call`) and `NO_TIP`, so the join gives
`UNRESOLVED`. `_put` binds `tip ↦ UNRESOLVED` and writes `self._carried = tip`, which is also
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
> says so. It fails **closed**: if PLR ever builds head trackers with a holder, `entry_reset` disappears
> and every first-pickup guard returns to `UNKNOWN`.

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
public protocol. **The bridge does not depend on it.** Rule 2 of §18.4.4 widens on any bridge to a
private method, so an unpublished classification can never silently drive a verdict.
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

### 18.4.9 The expected selection, per 1.0 `TipTracker` method *(reasoned from reading `legacy/tip_tracker.py`; T57 measures)*

| method | tip writes / followed calls | result | published as |
|---|---|---|---|
| `add_tip` | `self._hold(tip)`, with `tip ↦ HAS_TIP` from the entry annotation `Tip`; `_hold` → `_put` → `_carried = tip`; `self.commit()` followed, `UNTOUCHED` | `HAS_TIP` | `effects` |
| `remove_tip` | `self._hold(None)` → `NO_TIP`; `commit` `UNTOUCHED` | `NO_TIP` | `effects` |
| `clear` | `self._put(None)` | `NO_TIP` | `effects` (new relative to the recon's list; not bridged from `LiquidHandler`) |
| `load_state` | `self._put(pending_tip)`, local `IfExp` with a `None` arm | `UNRESOLVED` | `effects_unresolved` |
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

**This is open issue OI-1, the strongest objection available to the adversarial round.** L3 fixes the
decision. What the round can still attack is whether §16.2.2's test should be amended in its own text
(proposed wording: "…or, if it is a pre-execution state fact, only together with a frame condition that
the analyzer checks over the program") or whether this field stays a named exception.

### 18.5.3 The site rule (4th `D6_SITE_RULES` row)

> **Normative.** `D6_SITE_RULES` (`plr-sema/src/plr_sema/check/predicate.py:1455-1463`) gains
> **one** entry keyed by symbol:
>
> `("_check_tip_racks_available", "ValueError", "not rack._available_for_tip_handling")`
>
> Its function `_eval_tip_racks_available_site_rule(ctx) -> bool | None` returns **`False`** iff all
> three conjuncts hold, and **`None`** (decline) otherwise. **It never returns `True`.**
>
> 1. `_observation(ctx.env).get("tip_racks_available") is True`;
> 2. `_observation(ctx.env).get("deck_resources_verified") is True`, the existing aggregate the `:321`
>    rule reads (`plr-sema/src/plr_sema/check/predicate.py:1198-1236`);
> 3. `ctx.rack_topology_stable is True` (§18.5.4). The field defaults to `None`, so a caller that does
>    not thread it gets a decline.

**False-only, and why that is the whole soundness story on the `T` side.** `evaluate_guard` maps a
site-rule `False` to `SAFE` without consulting depth or reachability
(`plr-sema/src/plr_sema/check/predicate.py:1522-1620`, the dispatch at `:1602-1603`). A `None` flows to
`guard_reason`, which returns `guard_predicate_unparsed` as today. The rule can therefore add `SAFE`
findings and cannot add a `WILL_FAIL`. The same holds for the three existing D6 rules (D-G6).

**Conjunct 2 is present because the observation covers only on-deck racks.** A spot whose rack is off
the deck would be checked by PLR but not seen by the harness. On the harness paths every resource name
is grounded against the deck. `deck_resources_verified` is the existing proof that every declared
deck-parented name is present. The rule does not read the guard's `resources` argument at all.
`_check_tip_racks_available` is a module-level delegate, and M1 binds nothing for those (AC-16.3). So
that argument cannot be bound, and the decision rests on the whole-deck quantification instead. OI-3
records the residual case, a program that constructs its own off-deck rack. That case cannot reach
this rule on any harness path, because `env` carries `obs:` members only when the harness built them.

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
site rule as a new keyword `rack_topology_stable: bool | None = None` on `evaluate_guard` and a
same-named `_Ctx` field (`plr-sema/src/plr_sema/check/predicate.py:244-289`), set from `process_call`
through `_findings_for_call` and `_findings_for_guards`
(`plr-sema/src/plr_sema/check/__init__.py:409-479`). Every other guard ignores it. The pre-scan is also
exported as a pure function, `rack_topology_disturber_pcs(instructions, contracts, receiver_states)`, so
the measurement script can publish how many `:338`-bearing operations it made decline (§18.9).

### 18.5.5 The residual assumption, named: A-RACK-STATIC

The conjunct removes the obvious frame violation, a move before the pickup. It does not prove that
**no other same-receiver `LiquidHandler` method** changes a rack's lid or stack position. This document
names that as an assumption rather than leaving it buried. **Adding a named assumption was a user
decision in increment 7 (D2).** L3 implies this one, but OI-2 asks the owner to confirm it
explicitly.

| id | assumption | why it is needed | what breaks if it is false |
|---|---|---|---|
| **A-RACK-STATIC** (added 260929, §18.5.5) | between the observation capture point and an operation, a `TipRack`'s lid and stack position change only through a topology-disturbing call (§18.5.4) | the `:338` site rule reads a pre-execution observation (§18.5.2) | a non-move-family `LiquidHandler` method that places a lid on, or stacks onto, a tip rack before a pickup gives `SAFE` at `:338` where PLR raises `ValueError`, which is unsound. **Checked on the corpus** by the unmodified tier-1 fence, and given one **hand-built** adversarial witness per disturber class in AC-18.11 |

This row is added to increment 1's §10.6.3 table, taking it from five rows to **six**.
`test_ac_16_13_a_deck_object_assumption_table_has_five_rows`
(`plr-sema/tests/test_check_graph.py:1534-1547`) moves to six in the same commit (T61).

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
  set `tips_dirty` and call `reset_tip_cells`.

The amendment's reset (`plr-sema/src/plr_sema/check/volumestate.py:204`, `reset_tip_cells`) stays on
every path where it fires today. The two tests that pinned the 1.0 soundness hole,
`test_ac_14_5_e_retip_dirty_tip_never_safe` and `test_tips_dirty_cost`, must stay green through the
modelled path. That is part of AC-18.13.

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
  - **The zero-cost alternative is recorded and not taken:** argue that R-A/R-B extend P4, which has
    never been on a registry row. That argument is available, and OI-4 asks the owner to choose between
    the two. Neither option adds a row or changes `BUDGET_CAP`.
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
   - The test, over the current table: every baseline key must still exist (a **vanished key fails**)
     and carry the same value, unless it is listed in `intended_divergences`, in which case it must
     carry the declared `new`. The test prints `parity = matched/total`, and at 1.0 that is expected to
     be `total − 1`.
   - **Any other divergence fails, and T59 must adjudicate it in this document's implementation record.
     It must not rebase it away.** The old pin's `TipTracker` source is not on disk in this checkout, so
     whether another old-pin effect was "both kinds" is not knowable before T59 runs (OI-9).
2. **Structural invariants** are checked on the regenerated table, for every receiver in
   `receiver_state`:
   - (a) `effects` has at least one `HAS_TIP` and at least one `NO_TIP` value whenever the receiver has
     a bridge;
   - (b) `entry_reset` present ⇒ (a) holds, which is L7's invariant;
   - (c) the gap ledger's `tip_state` families `tip_loading`, `tip_dropping` and `tip_requiring` are
     non-empty for `LiquidHandler`;
   - (d) the four new keys of §18.4.8 are present with the declared types;
   - (e) no method bridged from any receiver begins with `_`;
   - (f) `effects_max_depth ≥ 1` whenever `effect_backing_fields` is non-empty, since a backing field
     is only reachable through a helper at 1.0.
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
same `oracle_replay.main`), and adds four things:

1. a per-method read of `scope_verdict_by_method`;
2. one `tip_mutants.py` run for the direction controls;
3. reads of the regenerated contracts;
4. the baseline-parity numbers from §18.8(1).

The inputs are the **same four paths the `fd63e9cd` run used**, read off its record, not retyped from
memory:

```bash
bth sql "SELECT id, command FROM runs WHERE id LIKE 'fd63e9cd%'"
```

The invocation is `bth run --project-slug <fd63e9cd's slug> -- uv run --no-sync python plr-sema/eval/plr10_tip_effects_measure.py …`.
It uses **`bth`, not `uv run bth`**, and the wrapped form, so the project venv is used. The run is
verified **by its record**: `bth compact` first, then `bth sql` on `status, outcome, exit_code`. It is
never verified by exit code or console text.

**The sidecar, as it must be committed** (`plr-sema/eval/plr10_tip_effects_measure.bth.toml`):

```toml
# bathos sidecar for plr-sema/eval/plr10_tip_effects_measure.py
# (backlog #5622, task 260929_plr-1.0-migration, spec 260929 §18.9).
# PRE-REGISTERED before any run. Baseline: run fd63e9cd (1.0 floor, 0 scope-SAFE),
# dd79c4c89 ledger unknown_ledger_260911_volwire (216 scope-SAFE, all pick_up_tips).
# No number from the #5622 recon's exploratory scripts is evidence for or against this hypothesis.

[experiment]
hypothesis = "With spec §18's derived rules (R-A..R-E, L1's effects_unresolved->widen) and the fourth D6 site rule at :338, the analyzer at PLR 1.0.0b1 (a) stays sound and total on the frozen 343-row tier-1 benchmark with a live negative control; (b) fires tip-state WILL_FAIL in the direction the simulator raised in both tip mutant classes with zero unsound mutant rows; (c) recovers pick_up_tips scope-SAFE from 0 to at least 205 of the 216 it had at dd79c4c89, and no other method reaches scope-SAFE; (d) publishes LiquidHandler.load_state channel_effect = 'widen' with exactly one baseline divergence (10/11-style parity by design); and (e) changes no benchmark counter through load_state, which the tier-1 vocabulary never calls."
stage_name = "tip_effect_increment"
novel = false

[outcomes.pass]
condition = "control_fires = true AND real_unsound = 0 AND real_unsound_scoped = 0 AND real_totality_violations = 0 AND real_check_graph_exceptions = 0 AND real_rows_setup_error = 0 AND real_rows_executed = 343 AND mutants_unsound = 0 AND m1_will_fail_fired = true AND m2_will_fail_fired = true AND load_state_channel_effect = 'widen' AND baseline_divergences = 1 AND n_ops_load_state = 0 AND real_pick_up_tips_scope_safe >= 205 AND real_pick_up_tips_scope_safe <= 216 AND real_n_operations_scope_verdict_safe = real_pick_up_tips_scope_safe"
is_residual = false
decision = "Precision at PLR 1.0 is recovered to within 5% of the dd79c4c89 headline with soundness intact and the instrument live. Close #5622's measurement; publish the per-conjunct decline counts beside the result."
reasoning = "The 216 at 1.0 are blocked by exactly {:338, :758, tip_tracker:153}; R-A..R-C restore the last two by the old pin's own mechanism, the site rule decides the first. The only decline paths the old pin did not have are an observed lidded/stacked rack and a preceding topology disturber; a loss of at most 11 (5%) is what 'rare in a benchmark of 1.6 operations per row' allows."

[outcomes.marginal]
condition = "control_fires = true AND real_unsound = 0 AND real_unsound_scoped = 0 AND real_totality_violations = 0 AND real_check_graph_exceptions = 0 AND real_rows_setup_error = 0 AND real_rows_executed = 343 AND mutants_unsound = 0 AND m1_will_fail_fired = true AND m2_will_fail_fired = true AND load_state_channel_effect = 'widen' AND baseline_divergences = 1 AND n_ops_load_state = 0 AND real_pick_up_tips_scope_safe >= 123 AND (real_pick_up_tips_scope_safe < 205 OR real_pick_up_tips_scope_safe > 216 OR real_n_operations_scope_verdict_safe != real_pick_up_tips_scope_safe)"
is_residual = false
decision = "Sound and the mechanism works, but either the new conjuncts cost more than 5% of the old headline or an unpredicted SAFE population appeared. Publish n_338_declined_observation / n_338_declined_topology / n_338_declined_deck; attribute every unpredicted SAFE to a named rule; decide (owner) whether a finer topology conjunct is worth an increment. No precision claim beyond the measured number."
reasoning = "123 = 216 - 93: even if every one of the benchmark's 93 move-family operations preceded a distinct pick_up_tips, at least 123 would survive; below that the losses cannot be the conjunct alone."

[outcomes.fail]
condition = "control_fires = false OR real_unsound > 0 OR real_unsound_scoped > 0 OR real_totality_violations > 0 OR real_check_graph_exceptions > 0 OR real_rows_setup_error > 0 OR real_rows_executed != 343 OR mutants_unsound > 0 OR m1_will_fail_fired = false OR m2_will_fail_fired = false OR load_state_channel_effect != 'widen' OR baseline_divergences != 1 OR n_ops_load_state != 0 OR real_pick_up_tips_scope_safe < 123"
is_residual = true
decision = "Stop. A soundness counter moved, the instrument is dead, the denominator changed (the observation-field change touched the harness's runtime path), a derivation prediction failed, or recovery is too small to be explained by the conjuncts alone. Triage before any claim; soundness outranks precision."
reasoning = "Every prior increment held 0 unsound on this 343-row denominator; a failed direction control or a wrong load_state value means the derivation is not the one specified."

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
n_338_declined_observation = "int"
n_338_declined_deck = "int"
n_338_declined_topology = "int"
all_safe_unsound = "int"
all_safe_operations_executed = "int"
runtime_raised_ops_all_safe_arm = "int"
m1_will_fail_fired = "bool"
m2_will_fail_fired = "bool"
mutants_unsound = "int"
load_state_channel_effect = "str"
baseline_divergences = "int"
baseline_parity_matched = "int"
baseline_parity_total = "int"
n_ops_load_state = "int"
```

**How the thresholds were chosen.**

- **205 (PASS).** The recovery mechanism is structural: each of the three residual sites is addressed
  by name. So the only expected losses come from the two decline paths the old pin never had. The
  first is `tip_racks_available == false`: `build_setup` places each tip-typed base on its own named
  rack *(reasoned from its docstring; lid/stack placement not audited)*. The second is a topology
  disturber preceding a pickup. A 5% allowance (11 operations) is a judgement. It is stated as one
  here and is not derived.
- **123 (MARGINAL/FAIL boundary).** This one is derived, with one caveat. The benchmark has 93
  move-family operations (31 each for `move_lid`, `move_plate` and `move_resource`, from
  `real.oracle_replay.json`). If each preceded a distinct `pick_up_tips`, 216 − 93 = 123 would remain.
  **Caveat:** one move could precede two pickups in the same row, so this is not a strict bound. A
  result below it points at a broken mechanism before it points at the conjunct.
- **≤ 216, and total == `pick_up_tips`.** These are predictions. The 7 `:720` operations cannot reach
  scope-`SAFE`, and every other method keeps at least one undecidable site in its 1.0 residual
  (`drop_tips` keeps `:882`/`:891`, per `real.oracle_replay.json`). A violation of either routes to
  MARGINAL for attribution. It is not a pass.

**The explicit `load_state` prediction** has three parts:

- (i) `load_state_channel_effect == "widen"` in the regenerated table, a deterministic artifact property
  and a hard term;
- (ii) `baseline_divergences == 1`, where the one divergence is `load_state` HAS_TIP → widen, i.e.
  parity is total − 1;
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
  - (b) is the stub-defeating half: an implementation that aliases every `self.X` anywhere in the
    getter passes (a), (c) and (d) and fails (b).
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
      `W`.
  - (c), (d) and (e) together are the stub-defeating core: no single simplification of the fold passes
    all three.
- **AC-18.3 (L1's widen mapping in the bridge).**
  - The regenerated table has `LiquidHandler.load_state.channel_effect == "widen"`,
    `LiquidHandler.pick_up_tips.channel_effect == "HAS_TIP"` and
    `LiquidHandler.drop_tips.channel_effect == "NO_TIP"`.
  - Synthetic bridge fixtures, one each:
    - an unresolved method bridged at depth 0 gives `"widen"`, **not** `None`;
    - an unresolved method bridged at depth 1 gives `"widen"`;
    - a bridge to an `_`-prefixed method gives `"widen"`;
    - one depth-0 resolved bridge plus one unresolved bridge gives `"widen"`, so unresolved takes
      precedence.
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
- **AC-18.5 (V5 non-regression through the modelled path).** `test_ac_14_5_e_retip_dirty_tip_never_safe`
  and `test_tips_dirty_cost` pass with `pick_up_tips`/`drop_tips` now carrying modelled effects. A new
  fixture, pickup → aspirate 50 → dispense 50 → drop → pickup → aspirate 50 → dispense 50, shows the
  second pickup's cell at `[0,0]`. That means `tips_dirty` stays false and the second dispense decides.
  This is the precision half: the amendment must not have been what made the retip tests pass.
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
    `parity`.
  - Negative self-tests:
    - deleting a baseline key from a copy of the current table fails the test (**vanished key**);
    - flipping `drop_tips` to `HAS_TIP` in a copy fails it;
    - `--rebase` without an explicit `--intended-divergences` exits non-zero.
- **AC-18.8 (structural invariants).** §18.8(2)(a)–(f) are each asserted over the regenerated table, and
  each has a synthetic counter-table that must fail it.
- **AC-18.9 (behavioural oracle).** §18.8(3), run against real PLR 1.0.0b1:
  - every `effects` polarity is matched by `has_tip` after the call;
  - `load_state` exhibits both outcomes;
  - a fresh tracker has no tip;
  - the import order is explicit;
  - the test is not skipped when PLR imports.
- **AC-18.10 (the sixth observation field).**
  - `capture_observation` returns `tip_racks_available`.
  - A fixture layout with a **lidded** tip rack yields `False`, the benchmark's clean layout yields
    `True`, and a deck with no rack yields `True`.
  - A raising read yields `plr_observation is None`, as a whole record.
  - `OBSERVATION_KEYS` has six members. `test_observation_record_closed_refusal_list` (in
    `plr-sema/tests/test_cache.py`) and `_OBSERVATION_KEYS` plus `test_plr_observation_present_on_success`
    (in `training/tests/test_verify_postconditions.py`) are updated to six.
  - `env` carries `obs:tip_racks_available=true|false`, and two observations differing only in the
    field give distinct `env` sets.
  - The empty-`env` cache key is unchanged.
  - §16.2.1's closed-record text in `.praxia/docs/specs/260909_plr-sema-observation-increment.md`
    carries the one-field amendment and the narrowed lid-topology exception.
- **AC-18.11 (the `:338` site rule, the topology conjunct, and A-RACK-STATIC).**
  - (a) The key is present in `D6_SITE_RULES` and matches exactly one site
    (`test_d6_site_rule_keys_each_match_exactly_one_site`, count 4).
  - (b) **Never `True`:** exhaustive over the 2×2×3 product of conjunct values, where
    `rack_topology_stable ∈ {True, False, None}`.
  - (c) `SAFE` at `:338` on a `setup → pick_up_tips` graph with `env` carrying
    `obs:tip_racks_available=true` and `obs:deck_resources_verified=true`.
  - (d) One fixture per decline path, each giving `UNKNOWN`/`guard_predicate_unparsed`:
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
  - (f) **Hand-built adversarial runtime fixture.** A chatterbox layout moves a lid onto a tip rack
    with `move_lid`, then calls `pick_up_tips` from that rack. The simulator raises `ValueError`, the
    static verdict at `:338` is not `SAFE`, and the tier-1 fence counts 0 unsound.
  - (g) `n_tip_racks_decided` is published, with `attempted` and `predicted_target`.
  - (h) A-RACK-STATIC is in increment 1's §10.6.3 table, and the table test asserts **six** rows.
- **AC-18.12 (registry).**
  - HM-26 has `declared == 4` and live 4, with `what`/`breaks_when` naming the fourth rule.
  - HM-25 has `declared == 13` and live 13, and its thirteenth probe exercises a synthetic three-hop
    chain. **This is conditional on the owner taking OI-4's booking option.** If the owner takes the
    zero-cost option, this half is withdrawn with its probe, and HM-25 stays 12/12, asserted.
  - `len(live_rows()) == 25` and `BUDGET_CAP == 25`, asserted unchanged.
- **AC-18.13 (goldens re-taken once, and the gate-1 failures closed).** This runs **after** T57, T58 and
  T61 have all landed, and only then.
  - `test_check_graph_report_unchanged_for_shipped_fixture` (`plr-sema/tests/test_ir.py`) is re-taken
    at **44** findings, with the `by_reason` counter **measured**, not predicted, and the comment
    recording why it moved: the two `:338` findings, whose reason stays `guard_predicate_unparsed`
    without an observation.
  - `test_ac_10_4_shipped_fixture_unchanged` compares non-volume findings **excluding** findings sited
    at `_check_tip_racks_available` against the pre-increment 38, and asserts exactly 2 such findings.
  - Every test the gate-1 report attributes to RC-1 or RC-2 passes, with no `xfail`/`skip` added:
    the 15 in `test_tip_typestate.py`, the 2 in the tier-2 test file, and the `test_oracle_replay.py`
    clean-pickup gate test. They are red at `a176bac7` per that report and were not re-run for this
    spec.
  - AC-10.9's AST literal scan is green.
- **AC-18.14 (the measurement).**
  - `plr-sema/eval/plr10_tip_effects_measure.bth.toml` is committed **before** the run, byte-identical
    to §18.9's block except for whitespace. `git log` shows the sidecar's commit preceding the run's
    timestamp.
  - `plr-sema/eval/plr10_tip_effects_measure.py` implements its `[result_schema]` exactly, checked by a
    unit test against the TOML, as `test_plr10_characterize.py` does.
  - The run's bathos record, retrieved by `bth sql` after `bth compact`, has an evaluated `outcome`.
  - The outcome and the full `result.json` are recorded in this document's implementation record,
    whichever branch fired.
- **AC-18.15 (this document is machine-checked, and the amended texts landed).**
  - `plr-sema/tests/test_spec_lint.py` gains a constant for this file and parametrises it into both
    live-spec tests.
  - `uv run pytest plr-sema/tests/test_spec_lint.py -q` is run, with zero failing citation violations
    and zero AC-gating violations over this file, and the other nine specs unchanged.
  - Increment 1's §10.2.4 carries the "both kinds → UNRESOLVED" amendment note.
  - `.praxia/docs/INDEX.md` is regenerated with the docs tool.

---

## 18.11 Fixer tasks

> **Ordering (normative).**
> - T57 is atomic (L7) and comes first.
> - T58 may land before or after T57, but T59 needs both.
> - T60 comes before T61, because the site rule reads the field T60 creates.
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
| **T57** | **Derivation, atomic (L7).** In `derive/receiver_state.py`: R-A (§18.4.2), R-B's classifier with the binding and argument table, entry context, fold and cycle guard (§18.4.3), L1's `effects_unresolved` plus `compute_channel_bridge`'s unresolved/private → `"widen"` precedence (§18.4.4), R-C(1)/(2) (§18.4.5), R-D (§18.4.6); the four new `receiver_state` keys (§18.4.8); `_classify_write`'s `"ambiguous"` renamed to `COPY` with identical semantics; one regeneration of `plr-sema/data/derived_contracts.json` and the gap ledger. HM-25 thirteenth probe and `declared` 12 → 13 **only if OI-4's booking option is taken**; STOP if the measure ≠ 13 | modify `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/derive/__main__.py` (if serialization needs it), `plr-sema/src/plr_sema/_hand_maintained.py`, `plr-sema/data/derived_contracts.json`, `plr-sema/data/gap_ledger.json` (regenerated); create `plr-sema/tests/test_tip_effects_plr1.py`; modify `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_hand_maintained_ratchet.py` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_tip_effects_plr1.py -q`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q` — satisfying **AC-18.1**, **AC-18.2**, **AC-18.3**, **AC-18.4** | ~260 | — |
| **T58** | **R-E receiver roots (§18.4.7).** Two-pass candidate/tracker set difference in `derive_receiver_states`; regenerate | modify `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/data/derived_contracts.json` (regenerated); modify `plr-sema/tests/test_tip_effects_plr1.py` | `uv run pytest plr-sema/tests/test_tip_effects_plr1.py -q`; `uv run pytest plr-sema/tests/test_derive.py -q` — satisfying **AC-18.6** | ~40 | — |
| **T59** | **Drift tests (§18.8).** Baseline generator with `--from`/`--from-git-rev`/`--rebase`/`--intended-divergences`; the generated fixture from the old-pin table; the cross-pin test; structural invariants with counter-tables; the behavioural oracle against real PLR | create `plr-sema/scripts/gen_channel_effect_baseline.py`, `plr-sema/tests/fixtures/channel_effect_baseline.json`, `plr-sema/tests/test_tip_effect_drift.py` | `uv run python plr-sema/scripts/gen_channel_effect_baseline.py --from-git-rev <old-pin rev> --out plr-sema/tests/fixtures/channel_effect_baseline.json --intended-divergences LiquidHandler.load_state=widen`; `uv run pytest plr-sema/tests/test_tip_effect_drift.py -q` — satisfying **AC-18.7**, **AC-18.8**, **AC-18.9** | ~220 | T57, T58 |
| **T60** | **The sixth observation field (§18.5.2).** `capture_observation` computes `tip_racks_available`; `OBSERVATION_KEYS` gets six members; `observation_env_members` adds the `obs:` member; closed-list tests move to six; lidded/no-rack/raising fixtures; the §16.2.1 text amendment | modify `training/verify/deck.py`, `training/verify/verifier.py` (comment only), `plr-sema/eval/oracle_common.py`, `plr-sema/tests/test_cache.py`, `training/tests/test_verify_postconditions.py`, `.praxia/docs/specs/260909_plr-sema-observation-increment.md` | `uv sync --all-packages`; `uv run pytest training/tests/test_verify_postconditions.py -q`; `uv run pytest plr-sema/tests/test_cache.py -q` — satisfying **AC-18.10** | ~90 | — |
| **T61** | **The `:338` site rule (§18.5.3–§18.5.6).** `_eval_tip_racks_available_site_rule` plus the fourth key; the `rack_topology_stable` pre-scan (`rack_topology_disturber_pcs`) and its threading through `process_call` → `_findings_for_call` → `_findings_for_guards` → `evaluate_guard` → `_Ctx`; `n_tip_racks_decided` in the replay report; HM-26 `declared` 3 → 4 with the rewritten `what`/`breaks_when`; A-RACK-STATIC added to increment 1's §10.6.3 table, with the table test at six; the hand-built `move_lid`-onto-rack runtime fixture | modify `plr-sema/src/plr_sema/check/predicate.py`, `plr-sema/src/plr_sema/check/__init__.py`, `plr-sema/src/plr_sema/_hand_maintained.py`, `plr-sema/eval/oracle_replay.py`, `plr-sema/tests/test_check_graph.py`, `plr-sema/tests/test_hand_maintained_ratchet.py`, `plr-sema/tests/test_oracle_replay.py`, `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md` | `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q` — satisfying **AC-18.11**, **AC-18.12** | ~200 | T60 |
| **T62** | **Goldens re-taken ONCE, plus non-regression.** Re-take the `test_ir.py` shipped-fixture golden (44, `by_reason` measured) and the AC-10.4 comparison (excluding `:338`-sited findings); the V5 modelled-path fixture; confirm every gate-1 RC-1/RC-2 test green with no marker | modify `plr-sema/tests/test_ir.py`, `plr-sema/tests/test_tip_typestate.py`, `plr-sema/tests/test_volumestate_v5.py` | `uv run pytest plr-sema/tests/test_ir.py -q`; `uv run pytest plr-sema/tests/test_tip_typestate.py -q`; `uv run pytest plr-sema/tests/test_volumestate_v5.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_oracle_replay.py -q`; then each tier-2 test file individually — satisfying **AC-18.5**, **AC-18.13** | ~60 | T57, T58, T61 |
| **T63** | **The measurement (§18.9).** Step 1: commit the sidecar exactly as §18.9. Step 2: implement the script (two arms reused from `plr10_characterize.py`, per-method read, `tip_mutants` m1/m2, contract reads, parity from T59's fixture, decline counters via `rack_topology_disturber_pcs`) with a schema-vs-TOML unit test. Step 3: `bth run` in wrapped form, `bth compact`, verify by record | create `plr-sema/eval/plr10_tip_effects_measure.bth.toml`, `plr-sema/eval/plr10_tip_effects_measure.py`, `plr-sema/tests/test_plr10_tip_effects_measure.py`; outputs under `outputs/plr-sema/plr10_tip_effects_<date>/` | `uv run pytest plr-sema/tests/test_plr10_tip_effects_measure.py -q`; `bth run --project-slug <fd63e9cd's slug> -- uv run --no-sync python plr-sema/eval/plr10_tip_effects_measure.py <fd63e9cd's inputs> --out-dir …`; `bth compact`; `bth sql "SELECT id, status, outcome, exit_code FROM runs WHERE id LIKE '<prefix>%'"` — satisfying **AC-18.14** | ~180 | T59, T62 |
| **T64** | **Lint, amendments and index.** Register this file in `test_spec_lint.py` (both live-spec tests); increment 1's §10.2.4 amendment note; regenerate `.praxia/docs/INDEX.md`; fill this document's implementation record with T57–T63's measured values and every divergence | modify `plr-sema/tests/test_spec_lint.py`, `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md`, this file; regenerate `.praxia/docs/INDEX.md` | `uv run pytest plr-sema/tests/test_spec_lint.py -q` — satisfying **AC-18.15** | ~20 | T63 |

**Sizing note.** The total is about 1,070 LOC across eight rows. T57 at ~260 is the largest and the only
one that must not be split, because of L7. If a session boundary falls inside it, the safe cut is
before the regeneration: rules and synthetic tests landed, table not regenerated, every existing test
unchanged. It is never between effects and `entry_reset`.

---

## 18.12 Risks

| risk | likelihood | mitigation / rollback |
|---|---|---|
| R-A silently aliases `_before` after a PLR edit (drops the `cast`), so `remove_tip` becomes `UNRESOLVED` and `drop_tips` widens (a silent precision loss) | low | AC-18.1 pins `["_carried"]`, AC-18.7 fails on `drop_tips` moving, AC-18.9's oracle disagrees. Rollback: revert T57's commit and regenerate the table |
| L7 violated: `entry_reset` lands without effects, giving a false `SAFE` on a repeated pickup | low if T57 is one commit | AC-18.4(c) invariant; T57 is one row; review checks one regeneration |
| The observation field is judged "the answer" under §16.2.2 | **medium** (OI-1) | argued in §18.5.2; the field reverts cleanly (T60) and the site rule then declines everywhere, which is sound |
| A-RACK-STATIC false for some non-move `LiquidHandler` method | low–medium (OI-2) | a hand-built witness per disturber class (AC-18.11(d)/(f)); tier-1 fence; derived family ⊇ owner's three |
| The topology conjunct costs more precision than 5% | medium | pre-registered MARGINAL branch with per-path decline counters; no claim beyond the measured number |
| The baseline fixture shows a second divergence (an old-pin "both kinds" method) | unknown (OI-9) | T59 stops and adjudicates in writing, never rebases silently; `--rebase` refuses without explicit divergences |
| R-E drops a legitimate receiver in a future PLR | low | AC-18.6 pins the set; the failure is loud and fail-closed |
| `tip_mutants.py` does not run at 1.0 | unknown | the script crashes, no `result.json` is written, and the outcome is FAIL by construction; fix the harness before re-running under the **same** sidecar |
| Cache entries built against the old table serve stale verdicts | none by construction | the table digest changes, so entries cool (§16.2.3 / T41 precedent) |
| Tests that re-derive `upstream_nonlegacy` move under the new derive code (L6) | unknown (OI-12) | T57/T58 must run every test that reads `derived_contracts.upstream_nonlegacy.json` and report. If one re-derives, freeze its expectation to the committed file, which is not regenerated |

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

- **OI-1 — the observation field vs §16.2.2's third failure mode.** `tip_racks_available` evaluates the
  guard's own property. It is admitted as a pre-execution state fact plus a checked frame condition
  (§18.5.2). It also narrows §16.2.1's "lid topology — refused". Should §16.2.2's text be amended, or
  should this remain a named exception? Increment 4's §13.1 lid disposition, which §16.2.1 cites, was
  **not** re-read for this draft.
- **OI-2 — A-RACK-STATIC.** It is a new named assumption, which in increment 7 was a user decision
  (D2). L3 implies it, and the owner should confirm it explicitly. The claim that no non-move-family
  same-receiver `LiquidHandler` method can change a rack's lid or stack was **not** exhaustively
  verified. Candidates to check include `LiquidHandler.assign_child_resource` (inherited from
  `Resource`), which is decided by condition (c) of §18.5.4 only if no `LiquidHandler.assign_child_resource`
  contract key exists.
- **OI-3 — off-deck racks.** Conjunct 2 plus harness grounding is argued to cover them. A program
  that constructs its own `TipRack` cannot reach the rule on a harness path. That is reasoned from
  `env` being harness-built, not tested.
- **OI-4 — HM-25 12 → 13 or 0.** The spec books R-A/R-B/R-C(2) as one HM-25 unit. The zero-cost
  argument (P4 was never booked) is available. The owner chooses; T57 and AC-18.12 carry both branches.
- **OI-5 — flow-insensitivity and the holder-less path.** `_put`'s `_carried` write is conditional on
  `holder is None`. The recon's claim that the holder branch has the same polarity is reasoned, not
  verified. R-C(2) is a signature heuristic that the head trackers are holder-less.
- **OI-6 — `COPY` replaces the recon's ≥ 1-argument filter.** This is a deliberate deviation. `COPY`'s
  identity semantics inherits A-COMMIT, whose verified scope is `pick_up_tips`/`drop_tips` boundaries
  (increment 1 §10.2.2). A new `LiquidHandler` method bridging only `rollback` at depth 0 would get no
  effect. That would be sound only under A-COMMIT at that method's boundary.
- **OI-7 — "direct methods only".** The PLR base-closure check (AC-18.2(k)) guards it at the pin, but a
  third-party mixin outside the PLR tree would be invisible.
- **OI-8 — beyond-parity refinements.** "Optional parameter → UNRESOLVED" and "free name → UNRESOLVED"
  go beyond parity. Their effect at 1.0 is predicted to be zero (§18.4.9, reasoned). The cross-pin
  fixture will show whether they move any old-pin value.
- **OI-9 — the old-pin `load_state` value and the "10 of 11".** The old pin's `TipTracker` source is not
  on disk in this checkout. The recon's exploratory count of 11 and `load_state: HAS_TIP` are
  unverified here. The fixture generator reading the old artifact is the authority, and any second
  divergence halts T59.
- **OI-10 — the pass threshold 205.** It is a judgement; 123 is derived with a caveat. The number of
  `pick_up_tips` operations preceded by a topology disturber was **not** measured, and could not be
  without a pre-registration of its own.
- **OI-11 — the "rollback never bridged" claim.** It is verified only by the absence of the string from
  the 1.0 survey. If a future survey records `IfExp`-callee attributes, `rollback` becomes bridged. It
  classifies `UNTOUCHED` (`COPY`), so there is still no effect, but that rests on OI-6.
- **OI-12 — L6.** It was not verified whether any test re-derives the non-legacy table from source.
- **OI-13 — the behavioural oracle's import-order caveat and `Tip` construction.** Both come from the
  recon and were not re-verified.
- **OI-14 — `setup` in the tier-1 IR.** The old pin's 216 required `entry_reset` to fire, which implies
  that the tier-1 lowering emits a `setup` `CALL`. That is reasoned from the old result and was not
  re-read from the lowering.
- **OI-15 — R-E's breadth.** A class that is both a legitimate receiver and another candidate's tracker
  is dropped. There is no instance at 1.0, and it fails closed.
- **OI-16 — HM-26 headroom.** `declared == live` (4/4) follows HM-26's precedent, not §9.1's live+2.

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
| `:338` rule reads the observation alone | adds `deck_resources_verified` and `rack_topology_stable` conjuncts | the off-deck rack case (OI-3) and L3's frame condition |
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

