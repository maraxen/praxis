---
title: "plr-sema increment 4 — a content-addressed cache, a derived inert-name filter, and delegate-call channel binding"
description: "Fourth post-corpus increment to the plr-sema pre-corpus specification, as revised after adversarial round 1. Three items ship and two families do not. (1) #4922 lands the content-addressed cache on increment 2's existing key, storing the PRE-relabel `Finding` tuple -- post-relabel storage is unsound because `sideband.origin` is excluded from `bytecode_hash`, so two graphs differing only in operation ids share a hash -- with read-through hooked in `check_graph`, which is the only function holding the raw `contracts_json` string the key needs (round-1 O5). (2) #4883 derives the dropped-receiver inert-name filter, and its registry finding is the opposite of the one the dispatch predicted: it retires NO row, because `_INERT_RECEIVER_PREFIXES`/`_INERT_CALL_SUFFIXES` were never registered -- unregistered discovery under section 9.4, whose one re-baseline is spent -- so headroom stays 0. Clause 1 is import-resolved only and per-file (round-1 O6 plus a second correction found in implementation): a head counts as stdlib ONLY when that file's own module-level import table binds the name to a `sys.stdlib_module_names` member, because bare coincidence with a stdlib name wrongly filtered 280 whole-surface calls on `resource.*`. (3) #4946 binds a delegate-inherited guard's channel set from the caller's literal call-site argument, the only item that moves an already-missed gate. The LID family is specified and NOT adopted, on four verified structural blockers, with the `null`-condition landmine pinned by a regression test. The VOLUME family is DEFERRED whole to increment 5 (`260903_plr-sema-volume-increment.md`): round 1 established that its bridge does not match on real PLR at the pin and that its `env` gate cannot reach a bridged guard, which would have shipped an unsound default-`env` `WILL_FAIL`. Zero new registry rows, zero retired, ONE per-row ceiling bump (HM-25 5 -> 6, for P9 alone); HM-24 stays 1 and `REASON_VOCABULARY` stays 8 of 12 -- increment 5 carries the rest. No wire-format change, no `IR_VERSION` bump. Go/no-go: #4923 NO-GO (workload unmeasured; #4922 absorbs the case it targets); #4924 NO-GO (re-planning a liquid move needs an over-fill verdict that is undecidable until `max_volume` reaches the wire)."
status: implemented-round-1
spec_version: 12
amends: 260901_plr-sema-pre-corpus-spec.md
task_id: 260903_sema-followups
date: '260903'
confidence: medium
sources: "Read this session, in full or in the cited ranges. Specs and plans: .praxia/docs/specs/260903_plr-sema-real-programs-increment.md (in full, including the section 12.13 implementation record and the round-1 remediation changelog); .praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md:55-170,173-501,505-646,650-701,1136-1165; .praxia/docs/specs/260902_plr-sema-ir-bytecode-increment.md:88-160,425-491,624-653; .praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md:42-138 (Open decisions), 139-205 (section 0 and 0.1), 2287-2345 (section 9.1), 2347-2385 (section 9.2 inventory), 2412-2495 (section 9.4), 2499-2535 (Deferred + boundary summary), plus the section-header index. Audits read in full during round-1 remediation: .praxia/docs/audits/260903_plr-sema-families-cache-round1-challenger.md (O1-O6) and .praxia/docs/audits/260903_plr-sema-families-cache-round1-defender.md (all six CONCEDED; ordered remediation list); and, for objection style, .praxia/docs/audits/260903_plr-sema-real-programs-round1-challenger.md:1-58. Analyzer source: plr-sema/src/plr_sema/verdict.py:100-179; plr-sema/src/plr_sema/_hand_maintained.py:1-80,240-263,640-690,753-847,851-871 plus a grep index of every `what=`/`id=` field across all 25 REGISTRY rows; plr-sema/src/plr_sema/derive/__init__.py:840-959; plr-sema/src/plr_sema/derive/receiver_state.py:160-190,523-563,770-799; plr-sema/src/plr_sema/check/ir.py:50-95,178-192,690-702,770-781,830-870,900-926; plr-sema/src/plr_sema/check/__init__.py:443-457,686-700,713-727. Harness: plr-sema/eval/oracle_common.py:690-739,976-1006; plr-sema/eval/tip_mutants.py:63-70,86-166,166-224,227-251. Front end: praxis/backend/utils/plr_static_analysis/models.py:95-105,340-350,555-563,575-599. PLR at submodule pin dd79c4c89: liquid_handling/liquid_handler.py:90-229,968-1069,1170-1199,1273-1289,1330-1374 and the `_check_no_lid`/`does_volume_tracking`/`maximal_volume` grep index over the whole file; resources/lid.py (in full, 121 lines); resources/volume_tracker.py (in full, 171 lines); resources/container.py:22-88; resources/tip.py:16-80; liquid_handling/standard.py:40-67. Artifacts: plr-sema/data/derived_contracts.json:53592-53633,58363-58394,58432-58486,157962-158133,159897-159936,161251-161253; plr-sema/data/gap_ledger.json:28-60 (the 50063d52 inert-filter run: `derive_python_version` at :38, the newly-admitted `logger.debug`/`logger.warning` entries at :119,:139); training/verify/data/plr_exception_taxonomy.json:2964-2972,2991-2999,3010-3056; training/verify/data/plr_preconditions.json:49764-49773,49863-49864. Data: outputs/plr-sema/oracle_replay_260903_rebaseline.json:2-29; outputs/plr-sema/oracle_replay_260903_4950.json:1-29; outputs/plr-sema/tip_mutants_260903_4938.json:1-38; outputs/plr-sema/tip_mutants_260903_4946.json:1-38; outputs/plr-sema/tier2a_260903.json:1-26; outputs/plr-sema/tier2b_260903.json:1-45."
---

# Increment 4: cache, inert names, delegate binding

> **This document amends `260901_plr-sema-pre-corpus-spec.md` by reference.** It adds §13 to that
> document's numbering. **Post-round-1 it edits nothing in the main spec**: the volume family, which
> was the only thing that reopened §Open decisions 2's numeric-atom reservation, has moved out whole
> to increment 5 (`.praxia/docs/specs/260903_plr-sema-volume-increment.md`), and that reservation is
> untouched here. It amends `260902_plr-sema-tip-typestate-increment.md` (spec_version 9) in one place
> and `260902_plr-sema-ir-bytecode-increment.md` (spec_version 10) in two; §13.10 lists all three.
> Everything else in spec_version 8–11 — `Verdict`, `Finding`, `PlrSite`, `AnalysisReport`, `join`,
> `REASON_VOCABULARY`, the telemetry schema, the fork-drift tests, the derivation closure mechanic,
> the value grammar, the canonical form, the hash, the cache key, `OBLIGED(graph)`, L1/L2/L3 and
> B1/B2/B3 — is **unchanged**. No `schema_version` bump; no wire-format change; **no `IR_VERSION`
> bump** (it is `2`, `plr-sema/src/plr_sema/check/ir.py:93`); **zero new registry rows and zero rows
> retired** (24 live against `BUDGET_CAP = 24`, `plr-sema/src/plr_sema/_hand_maintained.py:43`,
> headroom 0). **One** per-row ceiling moves — HM-25 `declared` 5 → 6, for P9 alone — and
> `REASON_VOCABULARY` stays at 8 of cap 12; §13.7 does the arithmetic.

---

## 13.0 What this increment is, in one paragraph

Increment 3 gave the analyzer real programs to run on; this increment asks what it can *say* about
them beyond tip state, whether it has to say it twice, and whether the machinery it says it with is
still hand-typed. It was dispatched with five scope items and, after adversarial round 1, **three
ship and two do not** — which is the honest summary and is stated first because the two that do not
ship were the two the dispatch called the headline. **#4881** was dispatched as "two new guard
families, derived like the tip family", and the evidence reversed the framing on both. The **lid**
family, sold as the cheap tip-shaped one, is not tip-shaped in any of the four ways that matter —
`Liddable` has no state field, `has_lid` is a plain method rather than a property, the wire format
carries no children so entry state is unavoidably `TOP`, and the lid guards that actually reach
`aspirate`/`dispense` carry conditions `"lidded is resource"` and `null` because the survey drops the
`if lidded is None: return` early-out that guards them — so it is **specified and not adopted for
verdicts** (§13.1), with a named trigger and a landmine pinned by a regression test. The **volume**
family looked derivable and, round 1 established, is not yet: its bridge does not match
`op.resource.tracker.remove_liquid` on real PLR at the pin, and the `does_volume_tracking()` gate it
depends on cannot reach a bridged guard at all — which would have shipped a `WILL_FAIL` for programs
whose tracking hypothesis was never asserted. **It is deferred whole to increment 5**, not patched and
not dropped (§13.2). What ships is three items that round 1 left standing: **#4922**, the cache, on
increment 2's existing key, with one correctness argument that is not obvious and easy to get wrong
in the unsound direction; **#4883**, the derived inert-name filter, whose registry finding is the
opposite of the one the dispatch expected — there is no row to retire, because the surface was never
registered; and **#4946**, the only item here that moves an already-missed gate, binding a
delegate-inherited guard's channel set from the caller's own literal call-site argument.

| axis | today (spec_version 11) | this increment |
|---|---|---|
| guard families with an evaluator | tip only | **tip only** — lid specified and not adopted (§13.1); volume deferred to increment 5 (§13.2) |
| channel set for a guard inherited through `delegates_to` | `⊤` — the guard folds to ½ | bound from the **delegate call site's literal** channel argument, else `⊤` (§13.5) |
| `LiquidHandler.transfer`'s bridged `NoTipError` guard | `guard_predicate_unparsed` on every row | evaluated on channel 0; the m1 gate moves from 82% to **≥ 91%** (§13.5.4) |
| repeat `check_graph` on one program | full re-lower + re-walk | optional read-through cache on §11.3.3's key, hooked in `check_graph` |
| the inert-name filter | 9 hand-typed prefixes + 11 hand-typed suffixes | derived, **import-resolved per file**, plus the shipped class-object rule |
| numeric `Cmp` atoms | all Kleene ½ (main spec §Open decisions 2) | **all Kleene ½ — unchanged**; the reservation is increment 5's to spend |
| registry rows | 24 live, cap 24, headroom 0 | **24 live, cap 24, headroom 0** — unchanged |
| per-row ceilings | HM-24 `CAPPED (1)`, HM-25 `CAPPED (5)` | HM-24 **unchanged at 1**; **HM-25 → 6** for P9 alone (one loud diff, no new row) |
| `REASON_VOCABULARY` | 8 of cap 12 | **8 of cap 12 — unchanged** |
| `IR_VERSION` | 2 | **2** — unchanged |

**Deliverable of this increment, stated as the properties that must become true.** Three, one per
shipped item. **(a)** `check_graph(g, c, cache=store)` called twice on one payload returns, the second
time, findings element-wise equal to the first — and returns the *second* graph's operation ids when a
second payload differing only in `OperationNode` ids hits the same `bytecode_hash`, which is the case
a plausible implementation gets silently wrong. **(b)** The dropped-receiver worklist filters
`asyncio.sleep` and admits `logger.debug`, with both movements published as counts, and no registry
row is added in the process. **(c)** A protocol whose only tip-relevant operation is a
`LiquidHandler.transfer` produces `Verdict.WILL_FAIL` at the bridged `NoTipError` guard when the
preceding `pick_up_tips` is removed — an operation whose channel set is `⊤` and whose *guard's*
channel set is `[0]`, read out of the delegate call site's own literal.

---

## 13.1 #4881, first half — the lid family: specified, and not adopted

### 13.1.1 The PLR fact, and it is not the one the dispatch described

`LiquidHandler` refuses to pipette into or out of a lidded resource. The refusal is one module-level
helper (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:110-120`):

```python
def _check_no_lid(resource: Resource, action: str) -> None:
  lidded = _lidded_ancestor(resource)
  if lidded is None:
    return
  if lidded is resource:
    raise ValueError(f"Cannot {action} {resource.name!r}: it has a lid. Remove the lid first.")
  raise ValueError(...)
```

called at six sites — `:978` and `:1762`/`:1765` with `"aspirate from"`, `:1191` and `:1912`/`:1915`
with `"dispense to"`. `_lidded_ancestor` (`:95-107`) walks the **parent chain**, testing
`isinstance(current, Liddable) and current.has_lid()` at `:104`, so a lid anywhere in the ancestry
blocks pipetting — not only one on the direct parent. The dispatch brief cited `:104-116` and the
`isinstance`/`has_lid` test, and both check out; what the brief did not carry is the ancestor walk,
and the ancestor walk is one of the four reasons this family is not cheap.

### 13.1.2 The domain, specified so a later increment does not re-derive it

> **Normative (the lid lattice).** For one resource slot, `LidState ::= NO_LID | HAS_LID | TOP`, with
> the information order and join table of §10.1.1 read with `NO_LID` for `NO_TIP` and `HAS_LID` for
> `HAS_TIP`. The abstract state is `dict[slot: int, LidState]` — **per resource slot**, not per
> receiver, which is the one structural difference from the tip domain: tip state lives on the
> `LiquidHandler`, lid state lives on the `Plate`.
>
> **Normative (entry state).** The entry `LidState` of every resource slot is `TOP`, unconditionally
> and with no derivable exception. `NO_LID` and `HAS_LID` at entry are **not** establishable.

Entry `TOP` is forced by the wire format and is not a choice. The `RESOURCE` instruction's only
structural operand is `parents: tuple[str, ...]` (`plr-sema/src/plr_sema/check/ir.py:190`), lowered
from `ResourceNode.parental_chain` (`:698`), which the upstream model documents as *"Parent types from
resource to deck"* (`praxis/backend/utils/plr_static_analysis/models.py:587-589`). Three separate
things are missing at once: it records **types**, not names, so it cannot identify a slot; it records
**ancestors**, not children, and a lid is a *child* (`Liddable.lid` is
`next((child for child in self.children if isinstance(child, Lid)), None)`,
`external/pylabrobot/pylabrobot/resources/lid.py:74-77`); and it is a chain **upward**, which is the
direction `_lidded_ancestor` walks but not the direction that answers "does this plate carry a lid".
So the answer to the dispatch's question — *does the wire format say whether a plate has a lid child?*
— is **no, in three independent ways**, and the family can only ever fire after an observed lid
movement. That is stated here rather than discovered later.

### 13.1.3 Effects, and where the anchor would have to come from

`Liddable`'s mutators are the `lid` setter (`lid.py:79-86`: `None` → `unassign_child_resource`,
otherwise `assign_child_resource`) and `Liddable.assign_child_resource` itself (`lid.py:102-120`),
which raises `ValueError(f"'{self.name}' already has a lid.")` at `:110` when one is already seated.
A P4-shaped effect classification would give `assign_child_resource → HAS_LID` and
`unassign_child_resource → NO_LID`, and `LiquidHandler.move_lid` would bridge to them — the same
depth-0-only discipline §10.2.6 imposes on tip effects. **None of that is the blocker.**

The blockers are the anchor and the guard, and there are four:

| # | blocker | evidence |
|---|---|---|
| **L1** | P2's anchor rule matches a **property** whose body is `return self.<F> is/is not None` (§10.2.2). `Liddable.has_lid` is a plain **method** (`lid.py:71-72`, no decorator; the `@property` at `:74` belongs to `lid`) | `lid.py:71-77` |
| **L2** | P2 requires a **state field** `<F>` that P4 can classify writes to. `Liddable` has none: `lid` is computed from `self.children` on every read (`lid.py:74-77`), so there is nothing for `_classify_write` to see | `lid.py:74-77` |
| **L3** | The wire format carries no children, so entry is `TOP` (§13.1.2) | `ir.py:190`, `models.py:587-589` |
| **L4** | **The fatal one.** The lid guards that reach a `LiquidHandler` contract entry are unevaluable | see below |

**L4, in full, because it is the one that decides the section.** The shipped table already inlines
`_check_no_lid`'s two guards at depth 1 into six `LiquidHandler` contract entries — one such inlining
is `plr-sema/data/derived_contracts.json:53597-53630` — and carries `_check_no_lid`'s own entry with
the same two guards at depth 0 (`:159897-159933`). Their recorded shape is:

| guard | `condition` | `raises` | `site` |
|---|---|---|---|
| the self-lidded raise | `"lidded is resource"` | `"ValueError"` | `liquid_handler.py:116` |
| the ancestor-lidded raise | **`null`** | `"ValueError"` | `liquid_handler.py:117` |

Neither is a lid-state atom. The first tests *which* resource carries the lid, not *whether* one does;
the second has no condition at all. The predicate that actually decides both — `_lidded_ancestor(
resource) is None` — is expressed as an **early `return`** (`liquid_handler.py:113-114`), and the
precondition survey's `scope_trail` models `if` scopes, not early returns, so it is simply absent.
An evaluator cannot construct a lid verdict from these two rows no matter how good the state
derivation is.

And `ValueError` compounds it: the tip family selects its exception set by the two-conjunct taxonomy
filter `category == "tip_state" AND module == "pylabrobot.resources.errors"` (§10.2.5), which is
`DERIVED` precisely because no class name is typed into `plr_sema`. `ValueError` is a builtin with
**no entry at all** in `training/verify/data/plr_exception_taxonomy.json` — verified by search — so
there is no category to select on and no analogous filter to write. Selecting the lid family would
require naming `ValueError` plus a site filter in our own source, which is a hand-typed fact against
zero headroom.

> **Normative (the disposition).** The lid family is **specified and not adopted**. `plr_sema` derives
> and publishes the lid *ledger* facts — see AC-13.3 — and constructs **no `Finding` of any verdict**
> from a lid guard. Every operation carrying a `_check_no_lid`-derived guard continues to emit
> `guard_predicate_unparsed`, exactly as it does today. No `LidState` is computed, no lid entry is
> added to `receiver_state`, and no new `REASON_VOCABULARY` member is spent on a producer that does
> not exist.
>
> **The named trigger that converts this to adoptable:** the precondition survey records an
> early-`return` guard scope — i.e. `_check_no_lid`'s `:117` raise acquires the condition
> `not (lidded is None)` in its `scope_trail` — at which point L4 falls and L1/L2 become the ordinary
> cost of one new anchor shape.

**The landmine, disclosed because nothing else in this repo will.** A `raise_guard` with
`condition: null` reads, on its face, as *"this method raises unconditionally at this point"*. It is
not: `:117`'s raise is reachable only when the early `return` at `:113-114` did not fire. Today this
is harmless — a `null` condition falls through to `guard_predicate_unparsed` and asserts nothing — but
**any future rule that treats a `null`-condition `raise_guard` as a definite failure would manufacture
`WILL_FAIL` on six `LiquidHandler` methods for programs that run clean.** #4924's recovery interpreter
is precisely the consumer that would be tempted by such a rule. **Round 1 independently verified the
landmine** (`derived_contracts.json:159918-159933` does carry `"condition": null`) and adjudicated
that AC-13.4 is *"a genuine regression guard with real future value"*, recommending that #4881a be
reframed from "lid family infrastructure" to **"a regression test for a landmine"**. That reframing is
adopted: §13.9's row and AC-13.4 are what this item is for, and the ledger block is the smaller half.

**This section reverses the dispatch brief's premise, on evidence.** The brief scoped lid as
"tip-shaped, cheap". It is neither, and the four blockers above are all read out of source and shipped
artifacts at the current pin rather than argued from taste.

---

## 13.2 #4881, second half — the volume family: implemented in increment 5 (sprint 123, 260904)

The volume family was this document's headline deliverable through spec_version 12's draft. **It is
not in this increment.** Adversarial round 1 established two blocking defects — both conceded in full
by the defender, both verified against the pin by both reports — and the user's decision (260903) is
to **defer, not patch in place and not drop**.

- **The bridge does not match.** §13.2.4's rule required `<name>` to be "a comprehension target of a
  P8 match"; in `LiquidHandler.aspirate`, `op` is the loop variable of a *separate* `for op in
  aspirations:` statement over the comprehension's **output list**
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1031`), not a zip-bound name.
  Two further hops fail independently: `SingleChannelAspiration.resource` is a dataclass **class-level
  bare-name annotation** (`external/pylabrobot/pylabrobot/liquid_handling/standard.py:53`) that
  `_annotated_attributes`'s `_is_self_attr` test excludes
  (`plr-sema/src/plr_sema/derive/receiver_state.py:177`, predicate at `:164-167`), and
  `Container.tracker` is an unannotated `ast.Assign`
  (`external/pylabrobot/pylabrobot/resources/container.py:85`) that P1a cannot see at all.
- **The hypothesis gate cannot reach the guard it gates.** `compute_channel_bridge` sources a bridged
  guard's `scope_trail` from the **callee's** own contract
  (`plr-sema/src/plr_sema/derive/receiver_state.py:777-787`), and the survey's `dropped_calls` is a
  bare string list with no line number and no scope
  (`training/verify/data/plr_preconditions.json:49766-49772`). So `does_volume_tracking()` never
  appears on the bridged guard, the guard is never marked conditional, and under the **default**
  `env = frozenset()` the analyzer would emit `WILL_FAIL` for a program in which volume tracking may
  never have been on. That is a live soundness bug in the direction the whole mechanism existed to
  prevent, and it is why a partial fix — a working bridge with no threading — would be strictly worse
  than shipping nothing.

**Everything else about the family survived the round intact** — the interval domain, the capacity
asymmetry that makes the over-fill half undecidable, the taxonomy selector, the seeding convention,
the assumption table and the oracle plan — and all of it, plus two round-1 corrections the draft did
not have (sequential pair threading for two channels on one well; a fail-closed generalisation
covering `is_disabled`, which is a `@property` and not a zero-argument call), was carried under §14.x
numbering in **`.praxia/docs/specs/260903_plr-sema-volume-increment.md`** (increment 5) and has since
**landed**: sprint 123 (T24–T28, 260904) implemented the volume family in full against that document's
own §14.0 proof obligations, and the document's own §14.17 records the per-row measured result against
its published expectations. `status: implemented-round-1`, `spec_version: 15`.
**No acceptance criterion or task row in this document depended on it**, and the registry arithmetic it
carries — HM-24 1 → 3, HM-25 6 → 8, `REASON_VOCABULARY` 8 → 10 — was spent by increment 5's own T27,
approved by the user 260904, not by this document (§13.7).

---

## 13.3 #4922 — the content-addressed report cache

### 13.3.1 What is already built, and what is not

Increment 2 §11.3.3 defined `cache_key = (bytecode_hash, contracts_sha, surface_identity,
ir_version)`, and **the function already exists**: `plr_sema.check.ir.cache_key`
(`plr-sema/src/plr_sema/check/ir.py:918-926`) takes a bytecode, a `contracts_json` string and a stamp
and returns the four-tuple, with `bytecode_hash` at `:909-915` over `IR_HASH_PREFIX + canonical_text`
(`:906`). §11.5 named the store interface as the missing half. So this item is a *store* for a *key*
that is already computed, tested and hashed — the reverse of #4932's producer/consumer situation, and
correspondingly smaller.

### 13.3.2 The correctness argument, which is a purity argument and has one non-obvious half

> **Normative (the purity premise).** `check_ir(bytecode, contracts, receiver_states)` is a pure
> function of its arguments (`plr-sema/src/plr_sema/check/__init__.py:443-445`). Nothing it reads is
> outside them: it does no I/O, imports no `pylabrobot`, and reads no clock, environment variable or
> global. **A cache is sound iff its key determines every argument.**
>
> - `bytecode_hash` determines `bytecode` up to the canonical form, which is everything `check_ir`
>   reads: §11.3.2 excludes only `sideband`, and `sideband` is by §11.1.4's disposition invariant the
>   **S** class — "carried, never hashed, never read by `check_ir`".
> - `contracts_sha` is a sha256 of the **whole `contracts_json` string** (§11.3.3), and
>   `receiver_states` is a top-level key of that same document — `_check` reads
>   `contracts_payload.get("receiver_state", {})` and `contracts_payload.get("contracts", {})` from
>   one parsed object (`plr-sema/src/plr_sema/check/__init__.py:686-691`). So one hash covers both
>   arguments. This is load-bearing and is easy to break: a key computed over the `contracts`
>   *sub-dict* would not cover `receiver_state`, and a table regenerated with a changed `entry_reset`
>   would silently reuse stale findings.
> - `surface_identity` and `ir_version` answer "which PLR tree" and "which encoding" and are already
>   in the key.
>
> **The key stays a four-tuple this round.** The draft added a fifth component, `tuple(sorted(env))`,
> for the volume family's hypothesis argument; with §13.2 deferred, `env` does not exist in this
> increment and adding a component for it would be encoding a parameter no function takes. Increment 5
> adds it, and every entry written before it is invalidated by that addition — which is correct and is
> the cheap direction.

**The non-obvious half: the cache must store the *pre-relabel* findings.** `_check` calls `check_ir`
and then `ir.relabel_findings(raw_findings, origin)` (`check/__init__.py:942`), mapping each
finding's `operation_id` from `str(pc)` to the graph's own operation id through `sideband["origin"]`.
**`sideband` is excluded from `bytecode_hash`** (§11.3.2). Therefore two different graphs — the same
program with different `OperationNode` ids — share a `bytecode_hash` and have *different* origin maps.
Storing post-relabel findings would return the first graph's operation ids for the second graph: a
silently wrong report, not a cache miss.

> **Normative.** The cache stores the **`check_ir` output, before relabelling**. On a hit, the caller
> relabels with **its own** `sideband["origin"]`, joins, and assembles the `AnalysisReport` with its
> own `protocol_fqn` and its own `stamp` — which is exactly the design position §11.3.2 recorded for
> `protocol_fqn` and which §11.12's Q3 left open. **Q3 is hereby answered: findings, not reports, and
> pre-relabel findings specifically.**

**Telemetry is part of the observable behaviour and must not be skipped.** `check_graph` "emits every
finding via `plr_sema.telemetry`" (`check/__init__.py:955-964`). A hit that returned findings without
emitting them would make the cache observable, which would falsify the purity claim the cache rests
on. The emit therefore happens on the cached findings, on the hit path, unchanged.

### 13.3.3 The store, and where the read-through hooks (round-1 O5)

> **Normative.** `CacheStore` is a small class in a new module `plr_sema/check/cache.py`, stdlib-only
> (the §6.2 packaging fact is untouched):
>
> ```python
> class CacheStore:
>     def __init__(self, root: Path) -> None: ...
>     def get(self, key: tuple) -> tuple[Finding, ...] | None: ...
>     def put(self, key: tuple, findings: tuple[Finding, ...]) -> None: ...
>     def invalidate_by_methods(self, methods: frozenset[str]) -> int: ...
> ```
>
> - **Location.** `root` defaults to `plr-sema/.cache/` — inside the package tree, gitignored, and
>   **never `$TMPDIR` or a system temp dir**. A cache under a temp dir is silently emptied between
>   runs, which turns a persistence bug into a performance mystery.
> - **Layout.** One JSON file per entry, at `root/<sha256(canonical_key)>.json`, where `canonical_key`
>   is `json.dumps(key, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` — the same
>   canonicalisation §11.3.1 item 6 already uses, so there is one serialisation convention in the
>   package and not two.
> - **Entry.** `{"key": <the four components, as JSON>, "created": <ISO-8601 UTC>, "findings":
>   [<Finding as the wire form already defines>], "methods": [<sorted distinct CALL.method in the
>   bytecode>]}`. The key is stored **in the entry** as well as in the filename so a hash collision or
>   a filename-truncating filesystem is a loud mismatch rather than a wrong answer: `get` compares the
>   stored key to the requested key and treats a mismatch as a miss.
> - **`methods`** is what makes §13.3.4's targeted invalidation possible and is the only field that is
>   not either the key or the payload.
> - **`findings[].reason` is validated on read, not trusted.** Deserialisation
>   (`plr-sema/src/plr_sema/check/cache.py:102-108`) passes each stored `reason` through
>   `vocabulary_reason` (`plr-sema/src/plr_sema/verdict.py:202-215`) — the one dynamic form §3.3's
>   forward scan admits — so a corrupt or foreign cache entry raises `ValueError` and becomes a miss
>   rather than a `Finding` carrying a reason nobody registered.
> - **No eviction policy.** Entries are removed only by `invalidate_by_methods` or by deleting the
>   directory. An LRU or a size cap is a real requirement the moment this runs in CI over a large
>   corpus, and it is deferred (§13.12) rather than guessed at.

> **Normative (the hook, and it is `check_graph` — round-1 O5).** The read-through lives in
> **`check_graph`** (`plr-sema/src/plr_sema/check/__init__.py:968`), which gains a keyword-only
> `cache: CacheStore | None = None`. `check_graph` computes the key from **its own `contracts_json`
> parameter**, consults the store, and on a miss calls into `_check`'s body and stores the result.
>
> **It must not live in `_check`, and the reason is not stylistic.** `cache_key`'s second component is
> a sha256 of the **raw string** (`plr-sema/src/plr_sema/check/ir.py:918-926`), and `_check`
> (`check/__init__.py:686-700`) receives only `contracts_payload: dict[str, Any]` — an
> already-`json.loads`'d object. The draft's task row put the hook there, which would have forced one
> of two bad options: thread the raw string down as an unstated signature change, or re-serialise the
> dict inside `_check` — and a re-serialisation is **not** guaranteed byte-identical to the file
> (key order, whitespace, float `repr`), so `contracts_sha` could differ between two runs over the
> same unchanged file. That direction is safe (extra misses, never a stale hit) but it silently
> falsifies AC-13.5's premise that a second run over the same inputs hits.
>
> **With `cache=None` — the default — no file is read, no file is written, and no directory is
> created**, so the existing test suite stays pure and hermetic and a test that wants the cache has to
> ask for it. `check_ir` is **not** given a cache parameter: it is the pure core the soundness argument
> is about, and giving it a cache would make the premise circular.

### 13.3.4 Invalidation on a pin bump

A pin bump changes `surface_identity`, so **every** entry misses — correct, and free. The interesting
case is the one the dispatch names: a contract table regenerated at the *same* pin (a derivation fix,
as in #4938's `_constructor_state` repair, §12.13) changes `contracts_sha` and therefore also misses
everything, which is correct but wasteful when one method's guards moved.

> **Normative.** `invalidate_by_methods(methods)` deletes every entry whose stored `methods` list
> intersects `methods`, and returns the count. The caller computes `methods` by **diffing two contract
> tables**: the set of keys `receiver.method` whose contract entry differs between them, compared over
> the canonical JSON of the entry. A key present in one table and absent from the other counts as
> changed.
>
> **This is a tool, not an automatic mechanism, and the distinction is deliberate.** Nothing calls it
> during `check_graph`. It is exposed as `python -m plr_sema.check.cache --old A.json --new B.json
> --root plr-sema/.cache` and is for the human who regenerated a table and does not want to discard a
> corpus-sized cache. **A bug in the diff produces a stale hit — a wrong answer — whereas a bug in the
> "miss everything" path produces only slowness**, so the safe default (miss everything, via
> `contracts_sha`) is the one that runs unattended, and the sharp tool is the one a human invokes.
> Round 1 agreed with this reasoning explicitly (Q5).

### 13.3.5 The fork-D drift test guards the pin half

`surface_identity` is only a real guard if the pin literal it is compared against is itself pinned.
That is HM-23 — `EXPECTED_SUBMODULE_PIN` in `plr-sema/tests/test_fork_drift.py`, a `FROZEN` row at
declared 1 (`plr-sema/src/plr_sema/_hand_maintained.py:754-768`). **No change is needed to it**, and
saying so is the point: the cache adds a consumer of the pin identity, and a reviewer should be able to
see that the existing drift test already covers the new consumer rather than having to check. AC-13.8
asserts the coverage rather than assuming it — a cache entry written at the expected pin and read back
after the stamp's pin is perturbed must miss.

---

## 13.4 #4883 — the derived inert-name filter, and the registry finding the dispatch did not expect

### 13.4.1 What is there today

`_is_inert_dropped_receiver_call` (`plr-sema/src/plr_sema/derive/__init__.py:1058-1096`) is a
three-clause predicate over a full receiver-qualified call expression:

1. the head — text before the first `.` — is in `_INERT_RECEIVER_PREFIXES`, a hand-typed frozenset of
   **nine** entries: `logger`, `logging`, `warnings`, `inspect`, `args`, `kwargs`, `sig`,
   `backend_kwargs`, `default` (`:868-871`);
2. the head is capitalized, i.e. a call on a class object rather than an instance (`:902-903`) —
   **already derived**, and its comment already makes the right argument: *"this rule generalizes past
   any one PLR class name rather than hand-naming `Coordinate`"*;
3. the tail — text after the last `.` — is in `_INERT_CALL_SUFFIXES`, a hand-typed frozenset of
   **eleven** entries: `keys`, `items`, `values`, `union`, `join`, `append`, `get`, `update`,
   `format`, `strip`, `split` (`:878-881`).

The predicate gates the two published `top_unresolved.dropped_receiver` worklist views
(`:940` and `:1011`), which are deferred item (e)'s worklist. T14 found the tables miss stdlib noise:
`asyncio.sleep`, `time.time`, `struct.*`, `bytes.*`, `contextlib.*` all pass clause 1 (their heads are
not listed) and clause 2 (lowercase) and clause 3 (their tails are not listed), so they rank as real
unresolved receivers.

### 13.4.2 The derivation — import-resolved, per file

> **Normative (the predicate's signature — round-1 O6).** `_is_inert_dropped_receiver_call` gains the
> originating record's **file**: `(call_expr: str, file: str) -> bool`. Both call sites already hold
> it — `_dropped_receiver_worklist_from_survey` and `_dropped_receiver_worklist_whole_surface` iterate
> `rec.dropped_calls` with `rec` in scope (`plr-sema/src/plr_sema/derive/__init__.py:1085-1093` and
> `:1172`) — and neither passes it today. **Alias resolution is per file, never global**, because two
> PLR files can bind the same name to different things and a global table would let one file's import
> silence another file's local.
>
> **Normative (clause 1, import-resolved only).** The head is inert iff the **file's own module-level
> import table** binds that name to a member of `sys.stdlib_module_names` — i.e. the file contains
> `import <head>` where `<head>` is a stdlib module, or `import <mod> as <head>` / `from <pkg> import
> <mod> as <head>` where the resolved module is one. **Bare coincidence with a stdlib module name is
> NOT inert.** A head that merely happens to spell a stdlib module, with no import binding it in that
> file, is a local variable and stays in the ranking.
>
> **Normative (clause 2).** Unchanged — the capitalized-head rule at `:902-903` is already derived and
> already carries its own argument.
>
> **Normative (clause 3).** The tail is inert iff it is an attribute of a builtin container or
> `str`/`bytes` type — `tail in set().union(*(dir(t) for t in (dict, list, set, tuple, str, bytes)))`,
> excluding dunders.
>
> `_INERT_RECEIVER_PREFIXES` and `_INERT_CALL_SUFFIXES` are **deleted**, not left in place as a
> fallback. A retained fallback would make the derivation unfalsifiable: every entry the derived rule
> missed would be silently covered by the list, and nobody would ever learn which rule was doing the
> work.

**The import-resolved-only clause is not a refinement; it is a correction, and it was found in
implementation rather than in review.** A first pass that treated *any* head coinciding with a
`sys.stdlib_module_names` member as inert filtered **280 whole-surface calls on `resource.*`** — because
`resource` is a Unix stdlib module *and* the single most common local variable name in PLR's own
liquid-handling code (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:977-978`
alone binds it in a `for` loop and passes it to `_check_no_lid`). Silencing `resource.*` would have
hidden the deferred-item-(e) worklist's most interesting population behind a rule that looked
principled. **The import binding is what makes the rule about the file rather than about the name**,
and AC-13.1 asserts the `resource.*` case directly so the correction cannot regress.

`sys.stdlib_module_names` is a frozenset shipped by CPython since 3.10 (the package's
`requires-python`, main spec §1.1) and is a fact about **Python**, not about PLR — so it cannot go
stale when PLR changes, which is the `breaks_when` question §9.1 makes every hand-maintained row
answer. The same is true of `dir(dict)`. **It is a fact about a specific Python, though**, which is why
the gap ledger's stamp records `derive_python_version` (`plr-sema/data/gap_ledger.json:83`, `"3.14.6"`
at the 50063d52 run): the same derivation on a different interpreter can select a different set, and
that is a provenance fact, not a bug.

**Both replacements strictly extend the shipped behaviour, and both must be measured rather than
assumed.** Of the nine typed prefixes, `logging`, `warnings` and `inspect` are stdlib module names and
are covered *when the file imports them*; `logger`, `args`, `kwargs`, `sig`, `backend_kwargs` and
`default` are **local variable names** and are **not**. So the derived rule is not a superset of the
typed one, and AC-13.1 requires the before/after ranking to be published rather than asserted — the
same "show the ranked view before and after filtering" discipline the existing `filtered=False` path
was built for (`:926-932`).

> **Normative (what happens to the six uncovered locals).** They are **not** re-added by any means.
> `logger.debug` is caught by nothing after this change and re-enters the ranking. That is the correct
> outcome and is the reason the item is worth doing: the ranking exists to be *read*, and a filter that
> hides `logger.debug` by naming it hides the fact that the derivation cannot see it. The honest remedy
> — resolving a local's type from its assignment (`logger = logging.getLogger(…)`) — is a real
> dataflow pass, is named in §13.12, and is not attempted here.

### 13.4.3 What the implementation measured

Three facts from the 50063d52 run, recorded here because they are the shape of the answer and a fixer
re-running this must reproduce them, not re-derive them from scratch:

- **`derived_contracts.json` is byte-identical.** The filter gates only the gap ledger's
  `top_unresolved.dropped_receiver` *ranking*; it feeds no contract, no guard and no verdict. A change
  that moved the contract table would mean the filter had leaked into the derivation, and AC-13.1
  asserts the byte-identity for exactly that reason.
- **Newly admitted: `logger.debug` and `logger.warning`, +3 entries whole-surface.** Both are visible
  in the shipped ledger (`plr-sema/data/gap_ledger.json:119` and `:139`), which is the published
  evidence that the typed prefix list is gone and nothing silently replaced it.
- **The interpreter is stamped.** `derive_python_version` (`plr-sema/data/gap_ledger.json:83`) joins
  the existing `plr`/`praxis` provenance in the ledger's stamp block (`:37-59`), so a ledger diff
  caused by a Python upgrade is attributable rather than mysterious.

### 13.4.4 The registry arithmetic, and the dispatch's premise is false

The dispatch asked which registry row this retires, and predicted 24 → 23 live with headroom 1.
**There is no such row.** Searched: `_hand_maintained.py` contains no occurrence of
`_INERT_RECEIVER_PREFIXES` or `_INERT_CALL_SUFFIXES`, and the §9.2 inventory table's 25 rows
(HM-1 … HM-25, main spec `260901_plr-sema-pre-corpus-spec.md:2351-2375`) name no dropped-receiver
filter. The surface was introduced by round-5 T0 item 4 — after the §9.2 inventory was written — and
was never registered.

Under §9.4's own vocabulary this is **discovery**, not growth: *"registering pre-existing surface that
was always there but unregistered"*. §9.4 permits discovery to re-baseline the cap **once**, at T9,
and that re-baseline has been spent. So the position is:

- **Registering it** would need a 25th row against `BUDGET_CAP = 24` — a cap conversation, for a
  surface that is about to be deleted.
- **Deriving it** means it never needs one. Two hand-typed sets totalling **20 strings** leave the
  codebase, counting against §9.4's ≥82-facts shrink target, and the row that would have been added is
  never added.

> **Normative.** #4883 adds no registry row, retires no registry row, and moves no cap. `live_rows()`
> stays **24**, `BUDGET_CAP` stays **24**, headroom stays **0**. **No family gets headroom from this
> item**, and §13.7's single per-row ceiling bump is what P9 uses instead. AC-13.2 asserts the deletion
> and the unchanged registry together, so that a fixer cannot satisfy the item by adding a row and
> calling it registered.

---

## 13.5 #4946 — delegate-call literal channel binding

### 13.5.1 The measured gap, and what is already working

`#4938`'s AC-12.4 gate asked for m1 ≥ 50 of 55 and got **84 `will_fail` of 101 raised-as-expected,
with 17 `unknown` and 0 unsound** (`outputs/plr-sema/tip_mutants_260903_4938.json:9-16`) — 83%
against a 91% bar. §12.13 records that *"all 17 misses collapse to a lone `transfer` call whose
derived guard is `guard_predicate_unparsed`"* and files the residual as #4946. The #4946 fixer's own
run (commit `92f97256`, `outputs/plr-sema/tip_mutants_260903_4946.json:9-16`) reports **the identical
numbers** — 84 `will_fail`, 17 `unknown`, m2 190/190 (`:24-29`), `gate_passed` true (`:34`).
**That is the point: #4946 diagnosed the residual and did not move it.** The report is this item's
*baseline*, not its result, and any reading of it as a result would conclude the bar is unreachable.

**Delegation inheritance is not the gap.** `LiquidHandler.transfer`'s contract entry already carries
the bridged tip guard: `plr-sema/data/derived_contracts.json:58363` opens the entry and its
`channel_guards` list at `:58364-58383` holds one guard — `condition: "self._tip is None"`,
`depth: 1`, `raises: "NoTipError"`, sited at `tip_tracker.py:65` `TipTracker.get_tip`, with
`via: "self.head[channel].get_tip"`. P4's bridge, inherited through `delegates_to`, works exactly as
§10.2.6 says it does. (The same entry inherits `dispense`'s `BlowOutVolumeError` guards at
`:58449-58483`, whose `scope_trail` carries `"if does_volume_tracking()"` — which is worth noting
precisely because round 1 showed it does **not** generalise: that guard is a direct finding of
`dispense`'s own body reached through a *resolved* delegate, so its scope comes along for free, while
a guard reached through an unresolved `dropped_calls` entry gets no caller scope at all. That
asymmetry is exactly what deferred the volume family, §13.2.)

**The gap is the channel set.** `transfer`'s signature
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1273-1283`) declares `source`,
`targets`, `source_vol`, `ratios`, `target_vols`, `aspiration_flow_rate`, `dispense_flow_rates` and
`**backend_kwargs` — **no `use_channels`**, and no `tip_spots`/`resources` either — and its body
contains no P3a idiom, which §10.2.3 already records (*"`LiquidHandler.transfer` … gets no channel-set
derivation and is handled by rule 4 of §10.1.3: `channels = ⊤`"*). So §10.3.1's fourth
interpretability criterion — *"`op`'s channel set is exact"* — fails, the bridged guard folds to ½,
and the finding is `UNKNOWN`. The state is known; the channel it applies to is not.

**But the channels are literals, at the delegate call sites** (`liquid_handler.py:1347-1361`):

```python
await self.aspirate(resources=[source], vols=[sum(target_vols)],
                    flow_rates=[aspiration_flow_rate], **backend_kwargs)          # :1347-1352
dispense_flow_rates = dispense_flow_rates or [None] * len(targets)                # :1353
for target, vol, dfr in zip(targets, target_vols, dispense_flow_rates):           # :1354
  await self.dispense(resources=[target], vols=[vol], flow_rates=[dfr],
                      use_channels=[0], **backend_kwargs)                         # :1355-1361
```

The `dispense` call names `use_channels=[0]` outright. The `aspirate` call does not, but passes
`resources=[source]` — a **one-element literal list** in `aspirate`'s own P3a channel-default
parameter (§10.2.3 measured `aspirate → resources`), so PLR's own three-term disjunction
(`use_channels = use_channels or self._default_use_channels or list(range(len(resources)))`) yields
`[0]`. Both channel sets are decidable from the caller's AST alone.

### 13.5.2 The rule

> **Normative (P9, delegate-call channel binding).** Let `K` be a contract entry on receiver class
> `R` that carries a `channel_guards` entry `g` inherited from a delegate `D` — i.e. `g` reached `K`
> through a `delegates_to` hop to `R.D` rather than through a depth-0 bridge in `K`'s own body. Let
> `S` be the set of `ast.Await`/`ast.Call` expressions in `K`'s own body (**depth 0**, excluding
> nested function and lambda definitions) whose callee is an `ast.Attribute` on `self` naming `D`.
> Then `g` acquires a **bound channel set** `bound_channels(g)` computed as:
>
> 1. **`S` must be a singleton.** If `K`'s body awaits `D` zero times or more than once,
>    `bound_channels(g)` is `⊤`. Two call sites can disagree, and picking one is the "two views of one
>    fact" case §10.5 rule 1 dispositions as *a reason to know less*.
> 2. **Explicit.** If the single call site passes `use_channels=<E>` where `<E>` is an `ast.List` or
>    `ast.Tuple` display whose every element is an `ast.Constant` of type `int`, then
>    `bound_channels(g)` is that list of ints, **exact**.
> 3. **Arity default, P3a re-applied at the call site.** Else, if `D` has a P3a
>    `channel_default_param` `q` (§10.2.3) and the call site passes `q=<E>` where `<E>` is an
>    `ast.List` or `ast.Tuple` **display** of length `n ≥ 1`, then `bound_channels(g)` is
>    `[0 … n-1]`, **exact**. *The elements need not be resolvable* — only the display's length is
>    read, which is the same length-without-contents property §11.1.2 makes `Seq` the load-bearing
>    value form for. This is P3a's own `list(range(len(<q>)))` production evaluated one frame up, at
>    the site that supplies `<q>`, rather than inside `D` where `<q>` is opaque.
> 4. **Disabler poisoning still applies.** If any method in P3b's `channel_default_disablers` set
>    appears anywhere in the graph on the receiver, `bound_channels(g)` is `⊤` — rule 2 of §10.1.3 is
>    unchanged and is checked *after* 2 and 3, never before.
> 5. **Otherwise `⊤`.** A `**kwargs` forward, a name, a comprehension, a starred argument, a
>    non-`int` constant, an empty display, or a `q` the call site does not pass at all — every one of
>    these widens.
>
> **The binding is per-guard, not per-operation.** `channels_for_call` is **unchanged** and still
> returns `⊤` for a `transfer` operation; §10.3.1's criterion 4 is re-read to accept, for a guard
> carrying a `bound_channels`, that bound set in place of the operation's own. A guard with no
> `bound_channels` is evaluated exactly as today.
>
> **E2 is not extended.** A bound channel set makes a guard *evaluable*; it does **not** give
> `transfer` a tip *effect*. §10.2.6's depth-0-only effect rule stands, `transfer` still reaches
> `TipTracker` mutators only through delegates, and E4.2 still widens the receiver after the call.
> This is deliberate: reading a state through a delegate is sound from the caller's AST, but claiming
> a post-state through one requires knowing the delegate ran to completion on every channel, which is
> a different and larger claim.

**Why the `for` loop around the `dispense` call does not defeat rule 1.** The call at `:1355-1361` is
lexically single — one `ast.Await` in `K`'s body — and its `use_channels=[0]` operand is a constant
display, so the bound set is iteration-invariant by construction: every iteration binds the same
`[0]`. Rule 1 counts **syntactic call sites**, not dynamic invocations, and that is the right count
here precisely because the operand carries no comprehension target. A call site whose channel operand
*did* mention a loop variable falls to rule 5 and widens, because the operand would not be a constant
display. This is stated because it is the first thing a reviewer will test.

**Soundness.** Rules 2 and 3 assert only what PLR's own resolution asserts, over syntax the caller
literally contains, and every non-matching shape widens — and widening can only destroy a verdict
(§10.5's argument, unchanged). The one new claim is that PLR's three-term disjunction is
faithfully mirrored when its **first** term is present (rule 2) or **absent and the third decides**
(rule 3); the second term is `self._default_use_channels`, which rule 4 handles by the existing
poisoning mechanism rather than by a new one.

### 13.5.3 Provenance, payload, and no hand-typed names

`bound_channels` is an additive key on an existing `channel_guards` entry — no new block, no
`schema_version` bump, read through `.get()` with a `None` default so a pre-increment table degrades
to today's `⊤` behaviour:

```jsonc
"channel_guards": [
  {"condition": "self._tip is None", "via": "self.head[channel].get_tip",
   "bound_channels": {"channels": [0], "rule": "arity_default", "delegate": "aspirate",
                      "site_lineno": 1347},        // NEW -- absent when P9 yields Top
   "…": "every other key unchanged"}]
```

The gap ledger's `tip_state` block gains a `bound_channels` entry per contract key, valued with the
derived record or the strings `"absent"` / `"ambiguous"` / `"widened"` and the rule that widened it —
the same visible-absence discipline §10.2.2 established for `tipstate_anchor` and §12.1.3 for
`entry_reset`. **Every name in the record is read from PLR:** `"aspirate"` is the callee of an
`ast.Attribute` on `self`, `"use_channels"` and `"resources"` come from P3a's own measured map, and
`1347` is a line number. AC-13.10(iii) asserts this with the AST literal scan AC-10.9 established.

### 13.5.4 What this does and does not reach, and the rescaled gate

The residual m1 rows are rows whose call sequence collapses to a lone `transfer` (§12.13). P9 makes
the `aspirate`-delegated `NoTipError` guard evaluable on channel 0 for every one of them, so a mutant
that removed the preceding `pick_up_tips` — leaving `default = NO_TIP` from the scaffolding reset
(§12.1.4) — fires `WILL_FAIL` at the `transfer` index.

**The gate is expressed as a rate, because the denominator moved under it and will move again.** The
committed baseline is `outputs/plr-sema/tip_mutants_260903_4946.json`: **84 `will_fail` of 101
raised-as-expected** (`:9-14`), over `n_corpus_bases: 186` (`:36`), m2 190/190 (`:24-29`).
**#4950 (`6e34be9b`) then changed the verifier**, and the mutant denominators moved with it: corpus
bases 186 → 250, m1 raised-as-expected 101 → 193 with 158 `WILL_FAIL` (**82%**), m2 254/254. **Those
post-#4950 numbers are not in any committed artifact** — the only committed evidence of #4950 is the
replay report (`outputs/plr-sema/oracle_replay_260903_4950.json:2-13`: 331 executed, 528 operations,
0 unsound, 0 totality violations), and the mutant run at `6e34be9b` was reported through the sprint,
not through a file.

> **Normative (the gate).** **m1 ≥ 91% of the rows the simulator rejects — i.e. ≥ 176 of 193 at
> `6e34be9b` — with 0 unsound in both directions; m2 all of its rows with 0 unsound; tier 1
> unchanged.** The percentage is the gate and the absolute is the reading of it at one commit: a fixer
> who finds a different denominator **re-measures and publishes the difference rather than reconciling
> to the number written here**, exactly as increment 3's AC-12.4 required of m2's 108/108. If the bar
> is missed, the run publishes the **per-mutant residual** — base id, the operation the simulator
> raised at, the static reason emitted there, and P9's `bound_channels` value for that guard — so a
> shortfall is diagnosed rather than merely reported.

**`transfer` is the only method this reaches at the current pin, and that must be measured rather
than assumed.** P9 applies to any inherited `channel_guards` entry, and the fixer publishes the full
selected set — every `(K, delegate, rule, channels)` tuple P9 binds — so a second beneficiary shows
up in the artifact instead of in a surprise.

---

## 13.6 Soundness claims and the oracle that checks each

Every claim this increment makes, and the thing that would catch it being wrong. A claim with no
oracle is a claim this document is not entitled to make.

| claim | § | oracle |
|---|---|---|
| the lid family emits nothing, and a `null`-condition guard is not a definite failure | 13.1.3 | AC-13.4, which asserts both the zero-lid-findings property and the `null`-condition non-firing directly |
| a delegate call site's literal channel argument really is the channel PLR uses | 13.5.2 | **tier 3's existing m1 class** — the gate moves from 82% to ≥ 91% with 0 unsound in both directions, and a mis-bound channel shows up as a `WILL_FAIL` where the simulator ran clean, which m1 already counts (`plr-sema/eval/tip_mutants.py:389-392`) |
| binding a channel does **not** license a tip effect for the caller | 13.5.2 | AC-13.10(ii): an operation *after* the `transfer` yields `channel_state_unknown`, so E4.2's widen is still in force |
| P9 selects only where the caller's AST decides, and widens everywhere else | 13.5.2 | AC-13.10(i)'s five-shape negative fixture set, each shape asserted to yield `⊤` |
| a cache hit returns exactly what a miss computes | 13.3.2 | AC-13.5's hit/miss equality over every shipped fixture |
| a cache hit is correct for a *second* graph sharing a bytecode hash | 13.3.2 | AC-13.6, the pre-relabel storage assertion — the one case where a plausible implementation is silently wrong |
| the key is computed where the raw contracts string exists | 13.3.3 | AC-13.5's stability half: a second run over the same unchanged file **hits**, which a re-serialised key cannot guarantee |
| a moved pin misses | 13.3.5 | AC-13.8 |
| the derived inert filter changes the published ranking in both directions and hides nothing | 13.4.2 | AC-13.1's before/after publication, including the `resource.*` non-filtering assertion |
| the inert filter touches no verdict | 13.4.3 | AC-13.1's `derived_contracts.json` byte-identity assertion |

---

## 13.7 Hand-maintained impact

**New registry rows: zero. Retired registry rows: zero.** `live_rows()` is 24
(`plr-sema/src/plr_sema/_hand_maintained.py:851-855` — `RETIRED` rows do not count, and HM-8 is the
only one) against `BUDGET_CAP = 24` (`:43`). **Headroom: 0, before and after.**

**One per-row ceiling moves, and it is a loud one-line diff, not a row addition:**

| row | today | after | what the new pattern is |
|---|---|---|---|
| **HM-25** (`_hand_maintained.py:815-847`, `metric="patterns"`/`declared=5`/`status="CAPPED"` at `:828-830`) | live 5 | **live 6, declared 6** | **P9 alone** — the delegate-call channel-argument shape (§13.5.2) |
| **HM-24** (`:781-814`, the same three fields at `:793-795` with `declared=1`) | live 1 | **live 1 — unchanged** | nothing this round; the volume bridge that needed it is deferred (§13.2) |

**P9 carries the same argument HM-25's existing five do:** it is a syntactic pattern over *how PLR is
written* — a keyword argument at a `self.<delegate>(…)` call site holding an int-constant display, or
a display in the delegate's own P3a parameter — not a fact PLR records about itself. Its
`breaks_when` is that PLR stops passing the channel literally at the call site (e.g. `transfer`
computes `use_channels` into a local first), and it **fails closed**: `bound_channels` goes to `⊤`,
the guard reverts to ½, and the m1 gate falls back toward 82%. That failure is caught loudly by
§13.5.4's gate rather than silently, which is the HM-25 half of the HM-24/HM-25 split (§10.10 Q7)
working as designed.

> **The mechanical question this bump turns on, and increment 3's wording is wrong about it.**
> Increment 3 §12.1.2 declined a sixth HM-25 pattern on the grounds that *"the registry has zero
> headroom, so a sixth pattern is a cap conversation."* **[Correction, recorded here rather than by
> editing increment 3, which is `implemented-round-1` and whose text is a historical record:** that
> sentence conflates two separate ratchet tests. `test_total_declared_within_budget`
> (`plr-sema/tests/test_hand_maintained_ratchet.py:344-352`) asserts `len(live_rows()) <= BUDGET_CAP`
> — a cap on the **count of rows**, indifferent to any row's `declared` field —
> while `test_no_surface_exceeds_its_declared_size` (`:271-283`) enforces `measure() <= declared`
> **per row**. A sixth HM-25 pattern adds no row and moves no cap; it is a per-row ceiling edit, which
> §9.3 describes as the mechanism working: *"growth is not forbidden, it is made loud."* Round 1's
> challenger and defender both verified this reading against the two tests and adjudicated it correct
> (Q1), and **the user approved the HM-25 5 → 6 bump on 260903** with the row-count cap explicitly
> untouched. Increment 3's own decision to avoid the bump remains defensible as a conservative choice;
> only its stated *reason* was wrong.**]**

**`REASON_VOCABULARY` (HM-14): unchanged at 8 of cap 12** (`plr-sema/src/plr_sema/verdict.py:129-154`;
the row is `CAPPED` at declared 12, `_hand_maintained.py:650-654`). The draft added
`volume_state_unknown` and `volume_tracking_unasserted`; both belong to the deferred volume family and
**both move to increment 5**. Round 1's Q6 made the argument that decided it: a vocabulary member
whose producer does not work on ship day is the same "dead data" problem §13.7 already raises for
`lid_state_unknown`, and §13.2's deferral is exactly the case where the producer does not work. No
member is added here.

**What could have been hand-typed, and what it is instead:**

| what could have been typed | what it is instead |
|---|---|
| a `{"LiquidHandler.transfer": [0]}` channel map, or `"use_channels"`/`"aspirate"` as literals in our source | P9 reads the callee off an `ast.Attribute` on `self` and the keyword off P3a's own measured `channel_default_param` map (§13.5.3). AC-13.10(iii) scans for both strings |
| 9 receiver prefixes + 11 call suffixes | a per-file **import binding** into `sys.stdlib_module_names`, and `dir(dict)`-class attributes — facts about **Python**, resolved against the file that produced the entry (§13.4.2). 20 strings deleted |
| a list of stdlib names that are "really locals" (`resource`, `platform`, `types`, …) | **nothing.** The import binding decides it per file, which is why bare name-coincidence is not inert (§13.4.2) |
| `"ValueError"` plus a site filter, to select the lid family | **nothing.** The family is not adopted (§13.1.3) |
| a cache eviction policy tuned to the corpus | no policy at all; explicit invalidation only (§13.3.3) |

**HM-21 (X dispositions): unchanged at live 3.** This increment reads no new upstream field and moves
no field into or out of `X`. `RESOURCE`'s operand set does not change, which is the same statement as
"no `IR_VERSION` bump".

**Wire format: no change.** `Verdict`, `Finding`, `PlrSite`, `AnalysisReport`, `join`,
`SCHEMA_VERSION`, `REASON_VOCABULARY`, `derived_contracts.json`'s `schema_version: 1` and
`IR_VERSION = 2` are all unchanged. `bound_channels` is a new optional key read through `.get()`;
`cache` is a keyword-only parameter whose default reproduces today's behaviour exactly.

---

## 13.8 Acceptance criteria

Written so that none can be satisfied while the property is false. Where a criterion could be passed by
a stub, the stub-defeating half is named.

- **AC-13.1 (the inert filter is derived, import-resolved, and its movement is published in both
  directions).** Five sub-assertions. (i) `_is_inert_dropped_receiver_call` classifies
  `asyncio.sleep`, `time.time`, `struct.pack` and `contextlib.suppress` as inert **when called with a
  file that imports those modules**, and `self.head[channel].get_tip` and
  `op.resource.tracker.remove_liquid` as **not** inert. (ii) **The `resource.*` correction:** a call
  expression whose head is `resource`, from a file that does **not** `import resource`, is **not
  inert** — asserted directly, since `resource` is both a Unix stdlib module and PLR's most common
  local (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:977-978`). A
  name-coincidence implementation filters it and fails. (iii) **Per-file, not global:** two files, one
  importing `struct` and one not, give opposite answers for the same `struct.pack` expression.
  (iv) The regenerated ledger publishes **three** numbers — entries newly filtered, entries newly
  admitted, and the resulting rank of `self.head[channel].get_tip` — with the newly-admitted count
  **> 0** and including `logger.debug` and `logger.warning`
  (`plr-sema/data/gap_ledger.json:119`, `:139`). (v) `plr-sema/data/derived_contracts.json` is
  **byte-identical** before and after, and the ledger's stamp carries `derive_python_version`
  (`plr-sema/data/gap_ledger.json:83`). (ii) and (v) are the stub-defeating halves: a name-coincidence
  rule passes (i) and fails (ii), and a filter that leaked into the derivation passes (i)–(iv) and
  fails (v).
- **AC-13.2 (the deletion is real and the registry does not grow).** An AST scan of
  `plr-sema/src/plr_sema/derive/__init__.py` finds no module-level assignment named
  `_INERT_RECEIVER_PREFIXES` or `_INERT_CALL_SUFFIXES` and no `ast.Constant` string equal to any of
  their twenty former members; `_is_inert_dropped_receiver_call`'s signature takes a file/record
  parameter; and `len(live_rows()) == 24` with `BUDGET_CAP == 24`, asserted after the change, so the
  item cannot be satisfied by registering the surface instead of deriving it.
- **AC-13.3 (the lid facts are derived and published, and nothing is claimed from them).** The gap
  ledger gains a `lid_state` block naming, per candidate class: the `Liddable` anchor candidates found
  (expected: `has_lid` as a **method**, not a property, so the P2 anchor is `"absent"`), the state
  fields found (expected: **none**), and the two `_check_no_lid`-derived guard conditions with their
  `raises` (expected: `"lidded is resource"`/`ValueError` and `null`/`ValueError`). Each expectation is
  asserted against the shipped `plr-sema/data/derived_contracts.json` rather than against a fixture,
  because §13.1's whole argument is about real PLR at this pin.
- **AC-13.4 (the lid family emits nothing, and the `null`-condition landmine is pinned).** For a graph
  whose operations are `setup()` then `aspirate(use_channels=[0])` on a plate: **zero** findings carry
  a `plr_site` whose `file` is `liquid_handler.py` and whose `lineno` is `116` or `117` with a verdict
  other than `Verdict.UNKNOWN`; and the finding for the `:117` guard — the one whose derived
  `condition` is `null` — is `Verdict.UNKNOWN` with reason `guard_predicate_unparsed`, **not**
  `WILL_FAIL`. The second half is the stub-defeating one: an evaluator that read a `null` condition as
  "raises unconditionally" would pass the first half and fail the second. **Round 1 adjudicated this
  criterion the whole point of #4881a** (Q4), so it is the assertion that must not be dropped if the
  row is trimmed.
- **AC-13.5 (a hit equals a miss, and the key is stable across runs).** For every shipped graph
  fixture, `check_graph(g, c)` and `check_graph(g, c, cache=store)` called twice in a row produce
  reports whose `findings` tuples are equal element-wise and whose `verdict` is equal; the second call's
  store reports a **hit**, and so does a third call made in a **fresh process** against the same
  unchanged contracts file — the stability half, which a key computed from a re-serialised dict cannot
  guarantee (§13.3.3). With `cache=None` (the default) **no file is created and no directory is
  created** under `plr-sema/.cache/` or anywhere else, asserted by comparing a directory listing before
  and after.
- **AC-13.6 (the stored findings are pre-relabel, and a second graph proves it).** Two graph payloads
  that differ **only** in their `OperationNode` ids lower to the same `bytecode_hash`; running the
  first with a cold cache and the second against the now-warm cache yields, for the second, findings
  whose `operation_id`s are the **second** graph's ids. An implementation that stored post-relabel
  findings returns the first graph's ids and fails. A third assertion pins the key's coverage: two
  contract tables differing only in their `receiver_state` block produce **different** cache keys
  (§13.3.2), which a key computed over the `contracts` sub-dict alone would not.
- **AC-13.7 (targeted invalidation deletes what changed and only what changed).** Given two contract
  tables differing in exactly one entry (`LiquidHandler.aspirate`), `invalidate_by_methods` computed
  from their diff deletes every cached entry whose bytecode contains an `aspirate` `CALL` and **zero**
  entries whose bytecode does not; the returned count equals the number deleted; and a subsequent
  `get` on a deleted key is a miss while a `get` on a retained key is a hit.
- **AC-13.8 (a moved pin misses, and the drift test covers it).** An entry written with a stamp at
  `EXPECTED_SUBMODULE_PIN` is a **miss** when read with a stamp whose `surface_pin` differs by one
  character; `plr-sema/tests/test_fork_drift.py` passes unmodified; and HM-23's row is unchanged at
  `FROZEN`/declared 1.
- **AC-13.9 (this document is machine-checked).** `plr-sema/tests/test_spec_lint.py` gains a
  `SPEC_INCREMENT_4` entry alongside `SPEC_INCREMENT_3`, and both the citation checker and the
  AC-gating half of the cross-reference checker report **zero** failing violations over this file.
- **AC-13.10 (delegate-call channel binding is derived, selective, and moves the gate).** Four
  sub-assertions. (i) **Selectivity, from both sides.** Re-running `plr_sema.derive` emits, on
  `contracts["LiquidHandler.transfer"]["channel_guards"][0]`, a `bound_channels` record with
  `channels == [0]`, `delegate == "aspirate"` and `rule == "arity_default"` — the rule-3 path, since
  the `aspirate` call site passes no `use_channels`
  (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1347-1352`) — and the fixer
  publishes the **complete** set of `(K, delegate, rule, channels)` tuples P9 binds over the whole
  contract table, not only `transfer`'s. Against five synthetic caller fixtures — two depth-0 awaits
  of the same delegate; a `**kwargs` forward; a bare `ast.Name` in `use_channels`; a starred
  argument; and a delegate-parameter display of length 0 — P9 yields `⊤` in **all five** and the
  ledger records the widening rule for each. A rule-2 fixture passing `use_channels=[1, 3]` binds
  exactly `[1, 3]`, and a rule-4 fixture in which a P3b disabler appears on the receiver yields `⊤`
  **despite** an explicit `use_channels=[0]` at the call site — the ordering half, which an
  implementation that checked the disabler first or not at all would fail.
  (ii) **Binding a channel grants no effect.** On a fixture whose operations are `setup()`,
  `pick_up_tips(use_channels=[0])`, `transfer(...)`, then `aspirate(use_channels=[0])`: the
  `transfer` operation carries a `Verdict.SAFE` finding for the bridged guard sited at
  `PlrSite("external/pylabrobot/pylabrobot/resources/tip_tracker.py", 65, "TipTracker.get_tip")`,
  and the **following** `aspirate` yields `channel_state_unknown` — E4.2 still widens the receiver
  after a delegate-only method (§10.2.6). An implementation that extended E2 passes the first half
  and fails the second.
  (iii) **No hand-typed names.** An AST literal scan of `plr-sema/src/` finds no `ast.Constant`
  string equal to `"transfer"`, `"aspirate"`, `"dispense"` or `"use_channels"`.
  (iv) **The gate, directional, rate-expressed, with a published residual.** Tier 3's existing m1
  class reports **≥ 91% of raised-as-expected rows** carrying a static `WILL_FAIL` at the index the
  simulator raised — **≥ 176 of 193 at `6e34be9b`** — with **0 unsound** in both directions; **m2 all
  of its rows** with 0 unsound; and tier 1 unchanged. The baseline this must move is 84 `will_fail` /
  17 `unknown` of 101 over 186 corpus bases
  (`outputs/plr-sema/tip_mutants_260903_4946.json:9-16,36`), and the post-#4950 denominators are
  **re-measured and published, not reconciled to** (§13.5.4). The directional half is that a binding
  which never fires cannot reach 91%; the residual publication is what makes a miss diagnosable.

---

## 13.9 Task rows

Ordering is forced in one place and free elsewhere: **#4883 lands first**, because it is the only item
that touches the derivation's shared filter and #4946 regenerates the same artifact. #4922 is
independent of both. The volume family's row is **not here** — it is increment 5's T24–T28
(`.praxia/docs/specs/260903_plr-sema-volume-increment.md`), unscheduled.

| task | scope | files | gate | ~LOC | depends on | model |
|---|---|---|---|---|---|---|
| **#4883** | Derived inert-name filter (§13.4.2): `_is_inert_dropped_receiver_call` gains a `file` parameter and both call sites pass it; clause 1 replaced by **per-file import resolution** into `sys.stdlib_module_names` (a bare name coincidence is **not** inert); clause 2 unchanged; clause 3 replaced by builtin-container attribute membership; **delete** both frozensets; regenerate the gap ledger, publish the three ranking numbers of AC-13.1(iv) including the newly-admitted `logger.debug`/`logger.warning`, stamp `derive_python_version`, and assert `derived_contracts.json` byte-identical and the registry unchanged at 24 live | modify `plr-sema/src/plr_sema/derive/__init__.py`, `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_hand_maintained_ratchet.py`, `plr-sema/data/gap_ledger.json` (regenerated) | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q`; then `uv run python -m plr_sema.derive --survey-json training/verify/data/plr_preconditions.json --taxonomy-json training/verify/data/plr_exception_taxonomy.json --out $TMPDIR/contracts_4883.json --gap-ledger plr-sema/data/gap_ledger.json` and publish the before/after ranking — satisfying **AC-13.1**, **AC-13.2** | ~150 | — | Sonnet — the ranking movement is a measurement and the `resource.*` case is the finding |
| **#4881a** | The `null`-condition landmine regression test, plus the lid ledger block (§13.1, reframed per round-1 Q4): the `lid_state` gap-ledger block recording the absent P2 anchor, the absent state fields, and the two `_check_no_lid` guard conditions with their `raises`; **no** `LidState`, **no** `receiver_state` entry, **no** `Finding` construction, **no** new `REASON_VOCABULARY` member; the negative fixture and the `null`-condition assertion | modify `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/tests/test_derive.py`, `plr-sema/tests/test_check_graph.py`; create `plr-sema/tests/fixtures/lidded_plate_aspirate_graph.json` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q` — satisfying **AC-13.3**, **AC-13.4** | ~120 | #4883 | Sonnet — the four blockers must be re-verified against the pin and published, not copied from this document |
| **#4922** | The content-addressed cache (§13.3): `plr_sema/check/cache.py` with `CacheStore.get`/`.put`/`.invalidate_by_methods`, `plr-sema/.cache/` as the default root (never `$TMPDIR`), the entry carrying the four-component key + `created` + **pre-relabel** findings + `methods`; **read-through in `check_graph`**, which holds the raw `contracts_json` the key needs — **not** in `_check`, which sees only the parsed dict (round-1 O5) — behind a new keyword-only `cache=None`, with telemetry emitted on the hit path; the `python -m plr_sema.check.cache` diff-and-invalidate entry point; `.gitignore` for the cache dir | create `plr-sema/src/plr_sema/check/cache.py`, `plr-sema/tests/test_cache.py`; modify `plr-sema/src/plr_sema/check/__init__.py`, `.gitignore` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_cache.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_fork_drift.py -q` — satisfying **AC-13.5**, **AC-13.6**, **AC-13.7**, **AC-13.8** | ~310 | — | Sonnet — the pre-relabel storage argument is the one place a plausible implementation is silently wrong |
| **#4946** | Delegate-call literal channel binding (§13.5): P9 in `derive/receiver_state.py` — the singleton-call-site rule, the explicit `use_channels` int-display path (rule 2), P3a re-applied at the call site over a length-`n` display (rule 3), P3b disabler poisoning checked **after** both (rule 4), and `⊤` for every other shape (rule 5); the additive `bound_channels` key on a `channel_guards` entry and the ledger's `bound_channels` value with its widening rule; §10.3.1 criterion 4 re-read to accept a guard's bound set in place of the operation's; **`channels_for_call` unchanged and E2 not extended**; the five negative fixtures plus the rule-2 and rule-4 fixtures; the AST literal scan; **HM-25 `declared` 5 → 6**; artifact regenerated, the full selected `(K, delegate, rule, channels)` set published, and the m1 rate re-measured against the current denominator | modify `plr-sema/src/plr_sema/derive/receiver_state.py`, `plr-sema/src/plr_sema/derive/__main__.py`, `plr-sema/src/plr_sema/check/tipstate.py`, `plr-sema/tests/test_{derive,tip_typestate,check_graph}.py`, `plr-sema/data/derived_contracts.json` (regenerated), `plr-sema/src/plr_sema/_hand_maintained.py`; create `plr-sema/tests/fixtures/transfer_after_pickup_graph.json` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_derive.py -q`; `uv run pytest plr-sema/tests/test_tip_typestate.py -q`; `uv run pytest plr-sema/tests/test_check_graph.py -q`; `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q`; then `uv run python -m plr_sema.derive --survey-json training/verify/data/plr_preconditions.json --taxonomy-json training/verify/data/plr_exception_taxonomy.json --out plr-sema/data/derived_contracts.json --gap-ledger plr-sema/data/gap_ledger.json`; then `uv run python plr-sema/eval/tip_mutants.py --corpus training/assemble/out/corpus_p25.jsonl --examples-dir training/examples --contracts plr-sema/data/derived_contracts.json --report $TMPDIR/tip_mutants_4946.json` and `uv run python plr-sema/eval/oracle_replay.py --corpus training/assemble/out/corpus_p25.jsonl --contracts plr-sema/data/derived_contracts.json --report $TMPDIR/replay_4946.json` — satisfying **AC-13.10** | ~260 | #4883 | Sonnet — the m1 rate is a measurement against a moved denominator and the residual analysis is diagnostic |
| **T23** | Lint and index: add `SPEC_INCREMENT_4` **and `SPEC_INCREMENT_5`** to `plr-sema/tests/test_spec_lint.py`'s two parametrised live-spec tests — increment 5 is `draft-deferred` but its citations and AC gating must lint from the day it exists, or it will rot before it is scheduled; regenerate `.praxia/docs/INDEX.md` | modify `plr-sema/tests/test_spec_lint.py`; regenerate `.praxia/docs/INDEX.md` | `uv sync --all-packages`; `uv run pytest plr-sema/tests/test_spec_lint.py -q` — satisfying **AC-13.9** | ~20 | — | Haiku |

**Honest sizing note.** All four substantive rows are one session each, which is the direct
consequence of round 1: the item that was not — the volume family at ~780 — is the one that left.
**#4946's ~260 should not be split**, but its risk is not its size: a handful of its LOC are P9's five
rules and the rest is the seven fixtures that pin them, and a fixer under pressure will be tempted to
ship rules 2 and 3 without 1, 4 and 5. AC-13.10(i) exists to make that fail, and it is the
sub-assertion to run first rather than last. **#4922's ~310 is the most trustworthy number here** —
the key already exists (`plr-sema/src/plr_sema/check/ir.py:918-926`) and the store is a file per
entry — and #4881a's ~120 is the least interesting, since most of its work is verification rather
than code. **T23 covers both documents deliberately**: an unscheduled spec that does not lint is a
spec whose citations decay silently between the round that wrote it and the sprint that runs it.

---

## 13.10 What this changes in increments 1–3

Three normative amendments, listed so a reader of the earlier documents is not misled by text this one
supersedes. None changes any increment's *design*. **The draft carried seven; four of them belonged to
the volume family and have moved to increment 5 §14.14.**

**In `260902_plr-sema-tip-typestate-increment.md` (spec_version 9):**

1. **§10.3.1's fourth interpretability criterion — *"`op`'s channel set is exact"* — is re-read over
   the guard, not only the operation** (§13.5.2). A `channel_guards` entry carrying a P9
   `bound_channels` set is interpreted against *that* set; a guard without one is unchanged. §10.2.3's
   observation that *"`LiquidHandler.transfer` … gets no channel-set derivation and is handled by
   rule 4 of §10.1.3: `channels = ⊤`"* stays **literally true of the operation** — `channels_for_call`
   is not touched — and stops being the end of the story for its inherited guards. §10.2.3's closing
   sentence, *"making `transfer` precise requires modelling a method body"*, is narrowed: it requires
   modelling a method body's **call sites**, which is strictly less, and §13.5.2 rules 1 and 5 are
   what keep it less.

**In `260902_plr-sema-ir-bytecode-increment.md` (spec_version 10):**

2. **§11.12's Q3 — "whether the cache stores findings or reports" — is answered**, and more narrowly
   than the question was posed: it stores **pre-relabel** findings, and §13.3.2 gives the reason
   (`sideband.origin` is outside the hash). §11.3.2's design position — *"#4922 caches the `Finding`
   tuple, and the caller reassembles the report"* — is confirmed and sharpened.
3. **§11.5's #4922 hook is realised as specified, with its host named.** The store interface
   (`CacheStore.get`/`.put`) is exactly the one §11.5 sketched; what §11.5 did not say, and round 1's
   O5 found the draft getting wrong, is **which function calls it**: `check_graph`, the only one
   holding the raw `contracts_json` that `cache_key`'s second component hashes. §11.3.3's key stays a
   **four-tuple**; increment 5 adds the fifth component when `env` exists (§14.14 item 6).

**And in the main spec:** nothing. The draft reopened §Open decisions 2's numeric-atom reservation for
volume `Cmp` atoms; with §13.2 deferred, **that reservation is untouched by this increment** and is
increment 5's to spend (`260903_plr-sema-volume-increment.md` §14.14 items 1–2).

---

## 13.11 Effect on the oracle plan (`260902_plr-sema-oracle-harness.md`)

- **Tier 3's existing m1 class acquires a moving gate and becomes #4946's oracle.** The plan's tier-3
  row records m1 as measuring the tip family's directional reach; §13.5 makes it the *only* evidence
  that a delegate-bound channel is the right channel, so the row should say which item each threshold
  belongs to — 84/101 (83%) is #4938's achieved number, 158/193 (82%) is the same analyzer measured
  after #4950 moved the denominator, and ≥ 91% is #4946's gate. **A single unlabelled "m1" threshold
  in the plan will be read as a property of the tip family rather than of a binding rule**, which is
  exactly the misreading §13.5.1 had to correct about `tip_mutants_260903_4946.json`, and **an
  absolute threshold will go stale the next time the verifier changes**, which is exactly what #4950
  did to 101.
- **The plan's "which families are firing and which are still armed" sentence gains no entry.** The
  draft would have added volume; §13.2 defers it. The sentence should say tip only, and should name
  the lid family as *specified and deliberately silent* rather than leaving its absence to be read as
  an oversight.
- **Tier 1 is unchanged and must stay unchanged.** `check_graph`'s default `cache` is `None`, so the
  replay's committed numbers — 330 executed, 525 operations, 0 unsound, 0 totality violations,
  agreement 1.0 (`outputs/plr-sema/oracle_replay_260903_rebaseline.json:2-18`), or 331/528 after
  #4950 (`outputs/plr-sema/oracle_replay_260903_4950.json:2-13`) — must be reproduced
  **byte-identically** after every task in §13.9. That is the cheapest possible regression detector
  for three items that all touch the derivation or the checker, and it costs one existing command.
- **No new tier, no new module.** The draft added `volume_mutants.py` and three tier-2b fixtures; both
  move to increment 5 §14.9.

---

## 13.12 Explicitly not in this increment

- **The volume family, whole.** §13.2, deferred to `.praxia/docs/specs/260903_plr-sema-volume-increment.md`
  by round 1 and the user's decision. Its four proof obligations are that document's §14.0, and its
  registry arithmetic (HM-24 1 → 2, HM-25 6 → 8, `REASON_VOCABULARY` 8 → 10) is not spent here.
- **Lid verdicts.** §13.1's disposition. The named trigger is the precondition survey recording an
  early-`return` guard scope.
- **A capacity operand on `RESOURCE`.** Increment 5 §14.15; round 1 also removed the argument for
  taking it *early*, since `ir_version` is already a cache-key component
  (`plr-sema/src/plr_sema/check/ir.py:918-926`) and a later bump invalidates a populated cache exactly
  as completely as an early one.
- **`env`, and the fifth cache-key component.** Both belong to the volume family's hypothesis gate
  (increment 5 §14.6) and neither is built here. The key is a four-tuple this round.
- **Cache eviction.** No LRU, no size cap, no TTL (§13.3.3). Required the moment this runs unattended
  over a corpus; guessing a policy now would be tuning against a workload nobody has measured — the
  same reason #4923 is a no-go below.
- **Single-hop passthrough effects.** §13.5's P9 binds a *channel set* for a guard inherited through
  `delegates_to`; it does **not** give the caller the delegate's *effect*, so §10.2.6's named
  follow-up — recovering `discard_tips`/`return_tips` without recovering `move_tips` — is untouched
  and `transfer` still widens its receiver after the call (§13.5.2, AC-13.10(ii)). The two are easy to
  conflate because both are about reading a delegate from its caller, and the asymmetry is the point:
  a precondition read through a call site is sound from syntax, a post-state is not.
- **Resolving a local's type from its assignment** — the pass that would recover `logger.debug` after
  §13.4.2 deletes the prefix list, and the same pass that would let the inert filter see through
  `logger = logging.getLogger(…)`. A real dataflow pass; named, not attempted.
- **A `pred`-aware `BRANCH`.** Still §12.3.6's B2, still the natural next increment.
- **Precision targets.** Deferred (f) stands. §13.5.4's m1 rate is a *directional* gate on one
  mutation class, not an `UNKNOWN`-rate threshold.

### 13.12.1 Go/no-go: #4923, incremental re-check — **NO-GO**

**Decision criterion.** Incrementality earns its complexity iff, *after* #4922 ships, a whole-corpus
re-check following a contract-table regeneration still costs more than ~60 s of **check** time — check
only, excluding execution and excluding the extractor subprocess.

**The measurement does not exist, and this is the finding.** No committed artifact records a
check-only wall time. `outputs/plr-sema/oracle_replay_260903_rebaseline.json`'s `summary_flat`
(`:2-18`) has no timing field at all, and neither does `oracle_replay_260903_4950.json`'s (`:2-18`).
The only two committed timings measure something else:
`outputs/plr-sema/tier2a_260903.json:16` reports `elapsed_seconds: 89.256` for 330 rows, which
includes executing every row against the simulator **and** an out-of-process extractor invocation per
row (§12.4.1), so it is an upper bound on the check cost by an unknown and probably large factor; and
`outputs/plr-sema/tier2b_260903.json:14` reports `6.069` for 11 fixtures, which is too small a
population to extrapolate. **The threshold therefore cannot be evaluated today, and a go decision
taken now would be taken on no data.**

**Two further reasons the answer is no even before the measurement.** First, **#4922 absorbs the case
#4923 targets.** The dominant re-check workload is "the same programs, again" — a corpus replay after
a derivation fix — and a content-addressed cache answers that with a file read. What is left for
incrementality is only the *changed-prefix* case: a program edited in the middle, where a prefix of the
bytecode is shared. That case does not arise in a corpus replay at all; it arises in an editor loop
that does not exist. Second, **increment 3 already recorded that unrolling breaks #4923's memo point**:
§12.11 notes that a `pc` inside an unrolled region has one prefix hash per iteration, so the
per-instruction memo §11.5 hooked is no longer unique and #4923 would have to define what it means
first. That is design work with no measured payoff.

**Recommendation: no-go.** Re-open only after (a) `plr-sema/eval/oracle_replay.py` publishes a
check-only elapsed field — a ~5-line change that should be folded into whichever task next touches the
replay — and (b) the post-#4922 residual exceeds the threshold.

### 13.12.2 Go/no-go: #4924, error-recovery interpreter — **NO-GO**

**Decision criterion.** The interpreter is worth building iff a pass produces state a re-planner can
act on. The dispatch states the precondition as "a pass produces real state"; **that precondition is
already met and is not the right one.** The tip family produces real state today: 84 of 101
raised-as-expected m1 mutants carry a `WILL_FAIL` at the raised index with zero unsound rows
(`outputs/plr-sema/tip_mutants_260903_4946.json:9-16`). If "a pass produces real state" were the test,
#4924 would already be a go. The sharper precondition is: **the state must answer the questions a
re-planner asks**, and a liquid-move re-planner asks two — *"where is there enough liquid to draw
from"* and *"where is there room to put it"*.

**This increment answers neither, and after round 1 that is more true than the draft claimed.** The
volume family — which would have answered the first — is deferred whole (§13.2), so as of this
increment the analyzer says nothing about liquid at all. Even once increment 5 lands, its §14.2 makes
the over-fill half undecidable at the current wire format, so an interpreter re-planning a dispense
would have to choose a destination with no capacity information — i.e. re-plan into exactly the
failure class it is recovering from, and do so with a `WILL_FAIL` it is not entitled to construct.

**The minimum this increment would have to deliver, and does not.** #4922's cache (delivered) plus a
volume family whose **over-fill half is decidable** (not delivered, and now two increments away:
increment 5 ships the under-draw half, and the over-fill half is blocked behind the `RESOURCE`
capacity operand). §11.5's own hook — the `(pc, concrete state, abstract state)` triple — is untouched
and remains available; the pc join it rests on is unchanged by this increment.

**Recommendation: no-go**, and more firmly than the draft's. Revisit when the capacity operand lands,
which is a decision about the wire format and not about the interpreter.

---

## 13.13 Open questions — dispositions after round 1

Round 1 (challenger `.praxia/docs/audits/260903_plr-sema-families-cache-round1-challenger.md`,
defender `.praxia/docs/audits/260903_plr-sema-families-cache-round1-defender.md`) adjudicated all six
of the draft's open questions, and the user decided the one that needed deciding. **None is left open
for a second round on this document.**

1. **Per-row ceiling bumps — DECIDED (user, 260903).** The draft argued that §9.4's cap of 24 is a cap
   on the *count of rows* and that a per-row `declared` edit is ordinary, loud growth under §9.3.
   **Both reports verified the mechanical claim against the two tests** —
   `test_total_declared_within_budget` checks `len(live_rows()) <= BUDGET_CAP`
   (`plr-sema/tests/test_hand_maintained_ratchet.py:344-352`) and
   `test_no_surface_exceeds_its_declared_size` enforces per-row ceilings separately (`:271-283`) — and
   confirmed that increment 3 §12.1.2's "cap conversation" wording conflates them. **The user approved
   HM-25 5 → 6 for P9, with the row-count cap untouched at 24/24, HM-24 held at 1 and
   `REASON_VOCABULARY` held at 8.** The scope the question originally covered — paying for P7, P8 and
   the volume bridge — moved out with §13.2, so what remains approved is exactly one pattern.
   §13.7 records the arithmetic and the bracketed correction to increment 3's wording.
2. **The capacity asymmetry and this document's sequencing — RESOLVED against the draft.** The draft
   named "take the `IR_VERSION` bump now, while nothing is cached" as the strongest argument against
   its own ordering. Round 1 dissolved it: `ir_version` is **already** a component of §11.3.3's cache
   key (`plr-sema/src/plr_sema/check/ir.py:918-926`), so a future capacity bump invalidates a
   populated cache exactly as completely as one taken today. There is no accumulating cost being
   avoided, the sequencing concern was not load-bearing, and the capacity operand stays deferred on
   its own merits (increment 5 §14.15).
3. **The `env` mechanism — MOVED to increment 5.** Round 1 ruled sub-question (a) moot until O2 was
   fixed (the mechanism could not reach the guard it gated) and O3 a real defect (`is_disabled` is a
   `@property`, not a zero-argument call, so the "same rule" claim did not hold). Both are addressed in
   increment 5 §14.6, which generalises the rule to fail closed on **anything** unrecognised. Round 1's
   sub-question (b) — that a `WILL_FAIL` carries no record of which hypothesis it rested on — is
   carried forward there as an unresolved usability gap.
4. **The lid family's non-adoption and #4881a — KEPT, reframed.** Round 1 verified the landmine
   independently (`plr-sema/data/derived_contracts.json:159918-159933` does carry `"condition": null`)
   and adjudicated AC-13.4 *"a genuine regression guard with real future value"*, recommending #4881a
   stay but be described as **a regression test for a landmine** rather than as lid-family
   infrastructure. §13.1.3 and §13.9's row adopt that framing.
5. **Invalidation-as-a-tool — KEPT as specified.** Round 1 agreed with the document's own asymmetry
   argument: a diff bug in an automatic path returns a wrong answer, while a diff bug in a
   human-invoked tool wastes a human's time.
6. **The `REASON_VOCABULARY` count — RESOLVED by the deferral.** Round 1 held that
   `volume_tracking_unasserted` risked shipping as a member with no working producer — the same "dead
   data" objection §13.7 raises for `lid_state_unknown` — and should be treated as blocked rather than
   open. §13.2's deferral resolves it: both volume members move to increment 5, and this increment
   holds the vocabulary at **8 of cap 12**.

---

## 13.14 Implementation record (sprint 122)

- #4883 `50063d52` + `995b4948`: derived inert filter; frozensets deleted, no fallback; clause 1
  import-resolved ONLY — the first cut's bare `sys.stdlib_module_names` membership wrongly filtered
  280 whole-surface calls on PLR variables named `resource`/`cmd`/`site` (Unix stdlib module names);
  `derived_contracts.json` byte-identical; newly admitted `logger.debug`/`logger.warning`; interpreter
  version stamped `derive_python_version`; registry 24/24 unchanged (the frozensets were never
  registered).
- #4881a `7761af22`: the `null`-condition landmine regression test plus the lid gap-ledger block
  (§13.1, reframed per round-1 Q4) — **recorded here now; this row was never added when the commit
  landed in sprint 122.** `null`-condition assertion and the negative fixture pass; no `LidState`, no
  `receiver_state` entry, no `Finding` construction, no new `REASON_VOCABULARY` member — exactly
  AC-13.3/AC-13.4's scope.
- #4922 `1f082238`: cache per §13.3 with the round's O5 relocation (hook in `check_graph`); key
  `(bytecode_hash, contracts_sha, surface_identity, ir_version, env)`, `env` empty by default;
  pre-relabel storage; hit == miss (checker invoked once); invalidation CLI `python -m
  plr_sema.check.cache invalidate --old --new --cache-dir`; deviations: `CacheStore.put(...,
  methods=frozenset())`; moved-pin miss tested.
- #4946 `18b8d38b` (P9): binding published as
  `receiver_state.LiquidHandler.delegate_channel_binding.transfer = {aspirate: [0] arity_default @1347,
  dispense: [0] explicit @1355}`, one `bound_channels` record in the whole table (attribution tie
  resolved by `delegates_to` declaration order); E2 not extended, transfer widens after a bound-channel
  evaluation; `channel_kwarg` derived from P3a's matched target, removing a pre-existing hand-typed
  `"use_channels"` literal; HM-25 declared 5→6 (user-approved 260903), `_measure_hm25` counts P9;
  **m1 193/193 WILL_FAIL at the raised index (was 158/193 at `6e34be9b`, 84/101 before #4950), 0
  unsound; m2 254/254**; tier 1 unchanged (331/528/0/0/191 exact/1.0/setup_error 12). Tests named
  `test_ac_13_15_*` refer to the pre-renumbering AC id (now AC-13.10) — recorded here as the alias.
- Band A context (already in the sprint record elsewhere): #4948/#4951 `fe58ce4b`, #4949 `cc072883`,
  #4950 `6e34be9b`, #4884 praxia `902786026`.
- Denominator note: mutant bases 186 → 250 after #4950's verifier typing change (`6e34be9b`); the
  260903_4938/4946 reports are pre-change baselines.
- `a83e4067` (post-#4922 follow-up, sprint 122): the §3.3 reason-vocabulary forward scan admits ONE
  dynamic form — `reason=vocabulary_reason(<expr>)`, a validator in `plr-sema/src/plr_sema/verdict.py`
  (`:157-169`) that returns `value` iff it is `""` or a `REASON_VOCABULARY` member and raises
  `ValueError` otherwise. The cache's `_finding_from_dict`
  (`plr-sema/src/plr_sema/check/cache.py:102-108`) uses it, so a corrupt or foreign cache entry becomes
  a miss instead of a `Finding` carrying an unregistered reason; the AST scan in `tests/test_verdict.py`
  treats that call as validated (it adds no member to the reverse-direction count). Found by the
  orchestrator's final per-file run: #4922's deserialiser had failed
  `test_reason_vocabulary_closed_forward` (2 tests), which no fixer's gate had run.

---

## References

- Main specification (unchanged by this increment): `.praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md`
  — §0 (the organizing claim), §0.1 (the DERIVED / HAND-MAINTAINED classification and decision 2's
  scope note), §Open decisions 2 (**not** reopened here; increment 5's to spend), §6.2, §7.3–7.4,
  §9.1 (the registry dataclass and the `measure` forms), §9.2 (the 25-row inventory), §9.3 (the ratchet
  tests), §9.4 (the row-count cap, discovery-vs-growth, and `RETIRED` semantics), §Deferred rows
  (b)/(c)/(e)/(f).
- Increment 1 (amended): `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md` — §10.1.3,
  §10.2.2, §10.2.3 (P3a/P3b, whose measured map P9 re-applies at a call site), §10.2.5–10.2.6 (the
  bridge and the depth-0-only effect rule §13.5.2 leaves intact), §10.3.1 (criterion 4 re-read by
  §13.10 item 1), §10.3.3, §10.4 (E2/E4.2), §10.5, §10.8, §10.10 Q7 (the HM-24/HM-25 split).
- Increment 2 (amended): `.praxia/docs/specs/260902_plr-sema-ir-bytecode-increment.md` — §11.1.2 (the
  value grammar and `Seq`'s length-without-contents property), §11.1.3, §11.1.4 (the disposition
  invariant and the S class), §11.3.1–11.3.3 (canonical form, hash, cache key — the key stays a
  four-tuple, §13.10 item 3), §11.4.1, §11.5 (the #4922/#4923/#4924 hooks), §11.6, §11.12 Q3
  (answered, §13.10 item 2).
- Increment 3: `.praxia/docs/specs/260903_plr-sema-real-programs-increment.md` — §12.1.2 (the
  "cap conversation" wording corrected in §13.7's bracketed note; the `_constructor_state` precedent),
  §12.1.3–12.1.4 (the ledger convention and the reset effect P9's bound channels read against),
  §12.11, §12.13 (the implementation record whose numbers this document cites).
- **Increment 5, created by this round's re-scope:**
  `.praxia/docs/specs/260903_plr-sema-volume-increment.md` — the volume family whole, under §14.x, with
  §14.0's four proof obligations, §14.5's sequential pair threading (round-1 O4), §14.6's fail-closed
  generalisation (round-1 O3), and the registry arithmetic this document does not spend.
- Oracle plan (affected): `.praxia/docs/plans/260902_plr-sema-oracle-harness.md` — the soundness
  contract table, tiers 1–4, "Where it lives".
- **Adversarial round 1 on *this* document:**
  `.praxia/docs/audits/260903_plr-sema-families-cache-round1-challenger.md` (O1 the volume bridge does
  not match at the pin; O2 the `env` gate cannot reach a bridged guard; O3 `is_disabled` is a
  `@property`; O4 the V0/V2 update order; O5 the cache hook's host; O6 per-file alias resolution) and
  `.praxia/docs/audits/260903_plr-sema-families-cache-round1-defender.md` (all six **CONCEDED**, a
  severity table, the re-scope recommendation, and a seven-item ordered remediation list whose items
  1–3 became increment 5 and whose items 4–7 are the changes in this document). The remediation
  changelog below maps each item to the text that changed.
- Adversarial round 1 on increment 3, read for objection style:
  `.praxia/docs/audits/260903_plr-sema-real-programs-round1-challenger.md`.
- Backlog: `#4922` (the cache), `#4883` (the derived inert filter), `#4946` (delegate-call literal
  channel binding — the residual #4938 filed and commit `92f97256` diagnosed without moving),
  `#4881` (the two families: lid not adopted, volume deferred); go/no-go only: `#4923` (incremental
  re-check), `#4924` (error-recovery interpreter). Related items referenced but not addressed:
  `#4948` (`OperationNode.line_number` is 0 at every call site), `#4950` (the verifier change at
  `6e34be9b` that moved the mutant denominators).
- Code read for this document: `plr-sema/src/plr_sema/verdict.py`;
  `plr-sema/src/plr_sema/_hand_maintained.py`; `plr-sema/src/plr_sema/derive/__init__.py`;
  `plr-sema/src/plr_sema/derive/receiver_state.py`; `plr-sema/src/plr_sema/check/ir.py`;
  `plr-sema/src/plr_sema/check/__init__.py`; `plr-sema/eval/oracle_common.py`;
  `plr-sema/eval/tip_mutants.py`; `praxis/backend/utils/plr_static_analysis/models.py`.
- PLR source at submodule pin `dd79c4c89`: `liquid_handling/liquid_handler.py` (`BlowOutVolumeError` at
  `:91-92`, `_lidded_ancestor` at `:95-107` with the `Liddable`/`has_lid` test at `:104`,
  `_check_no_lid` at `:110-120` with its two raises at `:116` and `:117-120`, the aspirate lid check
  and its `resource` loop variable at `:977-978`, the dispense lid check at `:1191`,
  `transfer`'s signature at `:1273-1283` with no `use_channels` parameter, and its two delegate call
  sites at `:1347-1352` (`aspirate`, with `resources=[source]` at `:1348` and no `use_channels`) and
  `:1355-1361` (`dispense`, with `use_channels=[0]` at `:1359`, inside the `for` at `:1354`));
  `resources/lid.py` (`Liddable` at `:62-72` with `has_lid` as a plain method at `:71-72`, the `lid`
  property at `:74-77`, the setter at `:79-86`, `assign_child_resource` at `:102-120` with the
  already-lidded raise at `:110`).
- Artifacts read: `plr-sema/data/derived_contracts.json` (`_check_no_lid`'s own entry at
  `:159897-159933` with the `null` condition at `:159918-159933`, `_lidded_ancestor`'s at
  `:161251-161253`, one of the six depth-1 lid-guard inlinings at `:53597-53630`, and
  `LiquidHandler.transfer`'s entry at `:58363` with its single inherited `channel_guards` bridge at
  `:58364-58383` and `dispense`'s inherited `BlowOutVolumeError` guards at `:58449-58483`);
  `plr-sema/data/gap_ledger.json` (the 50063d52 inert-filter run: `derive_python_version` at `:38`
  inside the stamp block at `:37-59`, the newly-admitted `logger.debug` at `:119` and `logger.warning`
  at `:139`); `training/verify/data/plr_exception_taxonomy.json` (searched for `ValueError`: **no
  entry**, which is §13.1.3's L4 half); `training/verify/data/plr_preconditions.json:49766-49772` (the
  flat `dropped_calls` string list that is §13.2's second deferral reason).
- Data read: `outputs/plr-sema/oracle_replay_260903_rebaseline.json:2-29` (330 executed, 525
  operations, 0 unsound, 0 `check_graph` exceptions, 0 totality violations, `unknown_rate` 1.0,
  191 exact crosscheck joins, agreement 1.0 — **and no elapsed-time field, which is §13.12.1's
  finding**); `outputs/plr-sema/oracle_replay_260903_4950.json:2-29` (331 executed, 528 operations,
  12 setup errors, the same zero-unsound gate — the only committed evidence of #4950, and it carries
  no timing field either); `outputs/plr-sema/tip_mutants_260903_4938.json:1-38` (m1 84 `will_fail` /
  17 `unknown` of 101 raised-as-expected over 190 run, m2 190/190, both with empty unsound lists,
  `gate_passed` true); `outputs/plr-sema/tip_mutants_260903_4946.json:1-38` (commit `92f97256` —
  **numerically identical** to the `…_4938` run in every field, which is what establishes it as
  §13.5's baseline rather than a result, with `n_corpus_bases: 186` at `:36`);
  `outputs/plr-sema/tier2a_260903.json:1-26` (330 compared, 235 agreeing, extractor divergences 0,
  renderer 122, grammar 0, reset 0, directional 208/210, `elapsed_seconds` 89.256);
  `outputs/plr-sema/tier2b_260903.json:1-45` (11 fixtures, 35 operations, `region_unsound` 0,
  `region_will_fail_fired` 3, trip mismatches 0, `elapsed_seconds` 6.069).

---

## Remediation changelog (round 1)

Applied against the defender's adjudication of the round-1 challenger, in the defender's own order.
`status` moved `draft` → `reviewed-round-1`; `spec_version` stays **12**. The largest change is a
**re-scope, not an edit**: §13.2 left this document entirely. Every AC and task row that gated it left
with it, so the AC count moves 15 → 10 and the task-row count 6 → 5, and the surviving ACs were
renumbered contiguously (the volume ACs were 13.9–13.13; T23's lint AC became AC-13.9 and #4946's
became AC-13.10).

| item | O-id | verdict | change | section(s) |
|---|---|---|---|---|
| 1 | **O1** | CONCEDE (blocking) | The volume bridge does not match at the pin under any literal reading — `op` is a for-loop variable over the comprehension's **output list** (`liquid_handler.py:1031`), `SingleChannelAspiration.resource` is a dataclass class-level annotation `_is_self_attr` excludes (`external/pylabrobot/pylabrobot/liquid_handling/standard.py:52-53`, `receiver_state.py:208-211,221`), and `Container.tracker` is an unannotated `ast.Assign` (`container.py:85`). Three new mechanisms, one without precedent. **§13.2 moved whole to `260903_plr-sema-volume-increment.md`**, whose §14.0.1 states B1, B2 and P1c as three normative sub-boxes each with a measured expectation | §13.2 (now a stub), §13.0, new increment 5 |
| 1 | **O2** | CONCEDE (blocking, live soundness bug) | `compute_channel_bridge` sources `scope_trail` from the **callee** (`receiver_state.py:977-1041`) and `dropped_calls` is a bare string list (`plr_preconditions.json:62190-62216`, pre-T25 shape; T25 later migrated this to the `{expr, lineno, scope_trail}` record form — see increment 5 §14.0.2), so `does_volume_tracking()` never reaches the bridged guard and a default-`env` run would emit `WILL_FAIL` unasserted. Moved with O1; increment 5 §14.0.2 specifies P10 (derive-side, with the survey-side alternative costed and declined) and §14.0 gates T26/T27 behind **both** T24 and T25 | §13.2, increment 5 §14.0.2 |
| 2 | **O4** | CONCEDE (soundness) | V2's pair-update order was unspecified and read as simultaneous; PLR is sequential (`liquid_handler.py:1031`, `volume_tracker.py:96`) and two channels drawing one well would have produced a false `SAFE`. Folded into increment 5 §14.5 as a normative threading sentence plus the two-channel/one-well fixture (AC-14.6) | increment 5 §14.5, AC-14.6 |
| 3 | **O3** | CONCEDE | `VolumeTracker.is_disabled` is a `@property` (`volume_tracker.py:54-56`), not a zero-argument call, so the draft's "handled by the same rule" was false. Folded into increment 5 §14.6, which **generalises** the rule: anything unrecognised blocks `WILL_FAIL`. A-TRACKER-ENABLED downgraded from a soundness assumption to a precision note, and the consequence — no `WILL_FAIL` on real corpus rows at the current pin — is disclosed and raised as that document's Q1 | increment 5 §14.6, §14.7, §14.16 |
| 4 | **O5** | CONCEDE | The cache read-through moved from `_check` — which receives only `contracts_payload: dict` (`check/__init__.py:686-700`) — to **`check_graph`** (`:713`), the only function holding the raw `contracts_json` string `cache_key` hashes (`ir.py:918-926`). §13.3.3 gains a normative box naming the host and the two bad options the draft's placement would have forced; the #4922 row and AC-13.5 (a fresh-process hit) follow | §13.3.3, §13.9 #4922, AC-13.5 |
| 5 | **O6** | CONCEDE | `_is_inert_dropped_receiver_call` gains the record's `file` and resolves aliases **per file**; both call sites (`derive/__init__.py:940`, `:1011`) pass it. **Plus a second correction found in implementation (50063d52) that neither report raised:** clause 1 is **import-resolved only** — a head coinciding with a stdlib module name but not bound by that file's imports is **not** inert, because the first implementation wrongly filtered 280 whole-surface `resource.*` calls. §13.4.3 records the implementation facts (`derived_contracts.json` byte-identical, `logger.debug`/`logger.warning` newly admitted, `derive_python_version` stamped); AC-13.1 grows to five sub-assertions with the `resource.*` case as a stub-defeater | §13.4.2, §13.4.3, §13.9 #4883, AC-13.1, AC-13.2 |
| 6 | — | user decision | Registry arithmetic reduced to what ships: **HM-25 `declared` 5 → 6 for P9 alone**; HM-24 stays **1**; `REASON_VOCABULARY` stays **8 of 12**; rows 24/24, headroom 0. Increment 5 carries HM-24 1 → 2, HM-25 6 → 8 and the two volume reasons. Increment 3 §12.1.2's "cap conversation" wording corrected by a **bracketed note in §13.7**, not by editing that document | §13.7, §13.0's table |
| 7 | — | round-1 adjudication | §13.13 rewritten from six open questions to six dispositions: Q1 **decided** by the user with the mechanical claim verified against both ratchet tests; Q2 **resolved against** the draft's sequencing argument (`ir_version` is already a key component); Q3 and Q6 **moved** to increment 5; Q4 **kept, reframed** as a landmine regression test per the round's own recommendation; Q5 **kept as specified** | §13.13, §13.1.3, §13.9 #4881a |
| — | housekeeping | — | `status` → `reviewed-round-1`; frontmatter `description` rewritten around what ships; `sources` extended with both round-1 audit files, the gap ledger (anchors in `sources`), `outputs/plr-sema/oracle_replay_260903_4950.json` and the PLR/analyzer ranges read to verify the remediation; §13.5.4's gate **rescaled from an absolute to a rate** (≥ 91%, i.e. ≥ 176 of 193 at `6e34be9b`) after #4950 moved the denominators 186 → 250 bases and 101 → 193 raised rows, with the post-#4950 numbers flagged as **not in any committed artifact** and required to be re-measured; §13.1.3's blocker ids renamed B1–B4 → L1–L4 to stop colliding with increment 5's B1/B2; T23 extended to lint increment 5 as well | frontmatter, §13.1.3, §13.5.4, §13.9 T23, References |
