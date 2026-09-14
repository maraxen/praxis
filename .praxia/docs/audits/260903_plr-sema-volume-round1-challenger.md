---
title: 'plr-sema increment 5 (the volume family) — adversarial round 1, challenger'
description: 'Challenger report on .praxia/docs/specs/260903_plr-sema-volume-increment.md (spec_version 13 draft, e3441272): O1 BLOCKER §14.6''s generalised fail-closed rule makes WILL_FAIL unreachable on EVERY tier, fixtures included, because `aspirate`/`dispense`''s caller_scope permanently contains a `for` header and the `is_disabled` test — contradicting AC-14.5(a), AC-14.6, AC-14.7, AC-14.10 and the sprint GO gate; O2 BLOCKER P1c keys on `__init__` but `Tip.tracker` is written in `__post_init__` of a `@dataclass` that has no `__init__` in the AST, so P1c''s own measured expectation is unsatisfiable and both tip-cell bridge halves die — including `dispense`''s only decidable guard; O3 BLOCKER AC-14.2(iii)''s whole-`src/` AST literal scan is already false at HEAD on `"resources"` and `"op"`, and its only literal remedy contradicts §14.11''s "wire format: no change"; O4 BLOCKER a tip cell keyed on channel index is never reset across drop_tips+pick_up_tips, giving a false SAFE; O5 MAJOR the §14.6 harness observation window reads `does_volume_tracking()` after the verifier has already restored it; O6 MAJOR the cache key already carries `env` (#4922 shipped it) so §14.14(6) and T27 are stale and the invalidation claim is false; O7 MAJOR P10 re-implements, without else-polarity, a survey pass that already exists and is already correct at the exact site the dropped call is recorded; O8 MAJOR §14.8''s seed CALL names a receiver outside SUPPORTED_TOOLS and a `.tracker` the IR cannot express; O9 MAJOR B2''s "bit-for-bit unaffected" is a non-sequitur over a shared setdefault dict; O10 MAJOR two methods raise TooLittleLiquidError so V2''s direction assignment is under-determined; O11 MAJOR `transfer` has no derivation path at all so AC-14.9''s v2 class has no static side; O12/O13 MINOR HM-25 undercount and stale scheduling text. §14.1''s taxonomy arithmetic, §14.2''s capacity argument, §14.5''s O4 sequential correction and the verifier''s tracking-enabled setup all verified TRUE. Verdict: not implementable as written.'
status: final
task_id: 260903_sema-volume
backlog_id: '4962'
date: '260903'
confidence: high
sources: 'praxia:spec-challenger (claude-opus-5). Spec read in full (887 lines). Round-1 reports on increment 4 read (challenger O1–O6, defender). PLR submodule pin verified `dd79c4c89bc008629a1c598ea614be5e6067d1f9` by reading `.git/modules/external/pylabrobot/HEAD` (no Bash tool available to this agent; `git -C` not runnable). PLR at that pin: `liquid_handling/liquid_handler.py:123-192,955-1271,1273-1361,1760-1829,1918-1977`, `liquid_handling/standard.py:30-79`, `resources/volume_tracker.py` (full, 171 lines), `resources/container.py:20-99`, `resources/tip.py:1-80`, `liquid_handling/backends/backend.py:27-38`. Analyzer: `derive/receiver_state.py:105-350,510-586,677-824,977-1071`, `check/ir.py:170-199,895-953`, `check/__init__.py` (grep for origin), `check/_supported_tools.py`, `_hand_maintained.py:36-49,230-289,540-569,770-884`, `verdict.py:120-179`. Harness: `eval/region_oracle.py:330-440`, `eval/tip_mutants.py:60-99,165-254`, `training/verify/verifier.py:100-193`, `scripts/survey_plr_preconditions.py:37-261`. Artifacts: `plr-sema/data/derived_contracts.json:157973,158054,158110-158137,168077-168160`, `training/verify/data/plr_exception_taxonomy.json:2966-3046`, `training/verify/data/plr_preconditions.json:49755-49834`. Tests: `plr-sema/tests/test_spec_lint.py:32-246`, `training/tests/test_verify_postconditions.py:78-84`. No file edited; no pytest run. Persisted verbatim by the orchestrator: the challenger agent type has no write tool.'
---

# plr-sema increment 5 (the volume family) — adversarial round 1, challenger

Target: `.praxia/docs/specs/260903_plr-sema-volume-increment.md` at `e3441272`. Verbatim report.

Pin verification: `/home/marielle/projects/praxis/.git/modules/external/pylabrobot/HEAD` reads `dd79c4c89bc008629a1c598ea614be5e6067d1f9` — the document's stated pin. Every PLR line number below is against that tree.

**Scope note.** §14.16 Q1 is settled and is not re-litigated. Increment 4's O1–O4 are not re-raised as unaddressed; §14.0/§14.5/§14.6 are attacked as *remediations*. Three of them fail on their own terms.

**What I verified TRUE and am not objecting to**, so the defender does not have to re-prove it: §14.1 fact 2's taxonomy arithmetic (exactly four `category == "volume_state"` members — `plr_exception_taxonomy.json:2972,2999,3019,3046` — of which exactly two are from `pylabrobot.resources.errors`, `errors.py:8` and `:12`); §14.1 fact 1's derived guards (`derived_contracts.json:158110-158137`, condition and the `1e-06` literal at `:158119`, `raises: "TooLittleLiquidError"`, site lineno 92 — the `:158119` citation is exact); §14.2's capacity argument (`Resource`'s seven operands at `check/ir.py:184-191` carry no capacity — citation exact); §14.5's O4 sequential-threading correction, including that `aspirate(resources=[well, well], vols=[60,60], use_channels=[0,1])` reaches the sequential loop (`liquid_handler.py:981-999,1031-1035`); §14.8's implicit claim that `set_volume` is the unique unconditional statement-position writer of `pending_volume` from a bare parameter (`volume_tracker.py:66-72` vs `:50`, `:151`, `:164-167`); and — answering the mandate's item 7 — volume tracking **is** enabled where the fixtures execute, at `training/verify/verifier.py:114` and `plr-sema/eval/region_oracle.py:414`, so AC-14.10's tier-2b fixtures can raise. That last one is a real strength of the plan; the *observation* of it is O5.

---

## Objections

### O1 — BLOCKER — §14.6's generalised rule makes `WILL_FAIL` unreachable on **every** tier, fixtures included, not just on real corpus rows

**Location.** §14.6 normative box ("the conditional-guard rule, generalised — round-1 O3") and its closing paragraph; §14.0.2's P10 measured expectation; AC-14.4, AC-14.5(a), AC-14.6, AC-14.7, AC-14.10.

**Issue.** §14.6 defines: a volume guard is conditional iff its `caller_scope` is `null` **or contains any entry the evaluator does not recognise**, and "an entry is recognised as satisfied in exactly one way: it is a bare zero-argument call `f()` whose callee name is a member of `env`." A conditional guard "may emit `SAFE` and `UNKNOWN` but **never** `WILL_FAIL`."

Now read the actual nesting the bridge derives against:

```
1031    for op in aspirations:
1032      if does_volume_tracking():
1033        if not op.resource.tracker.is_disabled:
1034          op.resource.tracker.remove_liquid(op.volume)
1035        op.tip.tracker.add_liquid(volume=op.volume)
```
(`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1031-1035`; the `dispense` mirror at `:1231-1235`.)

Every one of the four bridged volume guards at the pin sits under `for op in aspirations` / `for op in dispenses`. A `for` header is not "a bare zero-argument call `f()`" and can never be a member of `env`. §14.0.2's own measured expectation writes it into the payload: `caller_scope == ["if does_volume_tracking()", "for op in aspirations", "if not op.resource.tracker.is_disabled"]`. Therefore **every volume guard the bridge produces at this pin is permanently conditional, under every value of `env`, for every program the analyzer is ever handed.**

`caller_scope` is a property of *PLR's source*, derived once into `derived_contracts.json`. It is not a property of the program under analysis. §14.6's closing paragraph concedes the corpus case — "the *first* landing of this increment produces `SAFE` and `UNKNOWN` and **no `WILL_FAIL` at all** on real corpus rows" — but then asserts an escape hatch that does not exist: "only the tier-3 mutants — **whose fixtures the harness controls** — will exercise the `WILL_FAIL` path." The harness controls the *program*, not `LiquidHandler.aspirate`'s syntax. There is no fixture, mutant, or `env` value that removes `for op in aspirations` from the guard's `caller_scope`. §14.15 then explicitly rules out the only stated alternative ("Recognising a per-instance flag such as `is_disabled`. §14.6 fails closed on it").

**Counterexample / contradictions.** Four acceptance criteria in this document require the verdict §14.6 forbids:

- **AC-14.5(a)**: "seed 100, `aspirate(vols=[200])` → exactly one `Finding` with `verdict is Verdict.WILL_FAIL` … `plr_site == PlrSite("…/volume_tracker.py", 92, "VolumeTracker.remove_liquid")`". That site is reachable only through the `aspirate` bridge. Under §14.6 the verdict is `UNKNOWN`/`volume_tracking_unasserted`. **AC-14.5(a) fails against AC-14.4 on the same implementation.**
- **AC-14.6**: "a `Verdict.WILL_FAIL` for the **second**" pair. Same blockage.
- **AC-14.7**: asserts fixture (a) under default `env` yields `UNKNOWN` *rather than* `WILL_FAIL` — the whole assertion is only meaningful if a non-default `env` yields `WILL_FAIL`. It cannot.
- **AC-14.10**: "the straight-line over-draw and the second-iteration over-draw each carry a static `WILL_FAIL` at the `(operation, iteration)` the execution raised". These fixtures are real protocols calling `lh.aspirate` (`region_oracle.py:398-439` executes `protocol_fn(setup.machine, **kwargs)`). Same blockage. The "collective-exhaustion" and "two-channel" halves — the two named stub-defeating assertions — fail identically.

This also fails the sprint gate as the orchestrator stated it: *"GO if the extended bridge binds `remove_liquid`/`add_liquid` guards on the real pin so a harness fixture can drive `WILL_FAIL` under the asserted env."* Per §14.6 as written, a harness fixture **cannot** drive `WILL_FAIL`. This is not Q1 re-litigated — Q1(a) resolved "build the family if it is *firable*", and this objection reports that the document's own rules make it unfirable everywhere, which is the premise Q1's resolution rested on rather than the question it answered.

**Secondary, same box.** §14.6's closing paragraph names only `is_disabled` and the `for` header as blockers for `aspirate`. Note that `op.tip.tracker.add_liquid` at `:1035` is **not** under the `is_disabled` test — its `caller_scope` is `["for op in aspirations", "if does_volume_tracking()"]`. The document treats the two guards of one method as having the same scope; they do not. The `for` header alone still blocks it, so the conclusion is unchanged, but a fixer reproducing §14.0.2's single measured expectation for both entries will publish a wrong one.

**What must be resolved.** Does any `caller_scope` producible by P10 from `liquid_handler.py:1031-1035` or `:1231-1235` contain *only* recognised entries under §14.6's definition? If not, name the mechanism — not the intention — by which AC-14.5(a), AC-14.6, AC-14.7 and AC-14.10 are satisfiable at the same time as AC-14.4, and state which of the five is withdrawn if none exists.

---

### O2 — BLOCKER — P1c reads `__init__`; `Tip.tracker` is written in `__post_init__` of a `@dataclass` that has no `__init__` in the AST, and §14.2 already says so

**Location.** §14.0.1's P1c normative box and its measured expectation; §14.2's "tip cells" bullet; §14.4's bridge box; AC-14.1(iv), AC-14.2.

**Issue.** P1c is defined twice over as an `__init__` pass: "modelled directly on `_constructor_state` … **it locates a class's own `__init__`** … **P1c walks the same `__init__`** and, for every `self.<name> = <Callee>(...)` … records `name → <Callee>`." Its measured expectation is "`Container.tracker → VolumeTracker` … **and `Tip.tracker → VolumeTracker` (`external/pylabrobot/pylabrobot/resources/tip.py:45`)**."

`Tip` is a `@dataclass` (`tip.py:11-12`). It defines **no `__init__`** — the tracker write is in `__post_init__`:

```
32    def __post_init__(self):
...
45      self.tracker = VolumeTracker(thing=thing, max_volume=self.maximal_volume)
```
(`external/pylabrobot/pylabrobot/resources/tip.py:32,45`.)

The precedent P1c is "modelled directly on" hard-fails in exactly this case: `_constructor_state` scans `ast.iter_child_nodes` for `member.name == "__init__"` and **returns `None` when none is found** (`plr-sema/src/plr_sema/derive/receiver_state.py:562-568`). A literal P1c returns nothing for `Tip`.

The document contradicts itself on the same fact one section later: §14.2's tip-cell bullet says "**`Tip.__post_init__`** sets `self.tracker = VolumeTracker(...)` (`resources/tip.py:45`)". §14.2 knows; §14.0.1 does not.

**Counterexample.** Without `Tip.tracker → VolumeTracker`, the two-hop resolution `op → SingleChannelAspiration` (B1) → `.tip → Tip` (B2) → `.tracker → ?` (P1c) fails, and:
- `LiquidHandler.aspirate` acquires **one** volume guard, not two. AC-14.2's "contains exactly two entries" fails, as does §14.4's published measured expectation.
- `LiquidHandler.dispense` loses `op.tip.tracker.remove_liquid` (`liquid_handler.py:1235`) — which is **dispense's only decidable guard**. Its other half, `op.resource.tracker.add_liquid` (`:1234`), is the over-fill direction that §14.2 proves is permanently `½`. So dispense's entire volume contribution collapses to `volume_state_unknown`, and AC-14.5(d)'s "yields `Verdict.UNKNOWN`" would pass for the wrong reason — a stub that derives nothing at all satisfies it.
- AC-14.1(iv) explicitly asserts "`P1c` yields … `Tip.tracker → VolumeTracker` (`tip.py:45`)". It cannot.

**What must be resolved.** Is P1c a `__init__` pass, a `__init__`-or-`__post_init__` pass, or a pass over every method of a class? Each has a different blast radius — §14.11's argument that P1c is "a Python language construct, not a PLR idiom" is *only* true of the third; keying on `__init__` (or on `{__init__, __post_init__}`) is a bet on which method PLR writes trackers in, and PLR already writes them in two different ones. Whichever is chosen, §14.11's HM-25 argument for P1c has to be re-made against it.

---

### O3 — BLOCKER — AC-14.2(iii)'s AST literal scan is already false at HEAD, and its only literal remedy contradicts §14.11

**Location.** AC-14.2(iii); §14.11's "Wire format: no change" paragraph; the precedent it invokes, AC-10.9.

**Issue.** AC-14.2(iii): "an AST literal scan of **`plr-sema/src/`** finds **no** `ast.Constant` string equal to `"get_used_volume"`, `"get_free_volume"`, `"pending_volume"`, `"tracker"`, **`"op"`**, `"TooLittleLiquidError"`, `"TooLittleVolumeError"`, **`"resources"`** or `"vols"`."

Two of those nine are load-bearing wire keys already present in `plr-sema/src/`, with nothing whatever to do with the volume family:

- `"resources"` — `plr-sema/src/plr_sema/check/ir.py:320` (`"resources": "I"`), `ir.py:446` (`payload.get("resources") or {}`), `plr-sema/src/plr_sema/check/graph.py:193` (`payload.get("resources", {})`). This is the graph payload's own top-level key.
- `"op"` — `plr-sema/src/plr_sema/check/ir.py:860,872,879,881,883,885,887` (`{"op": Resource.op}`, `{"op": Call.op}`, `{"op": Loop.op, …}`, …). This is the IR's opcode tag in the canonical serialisation that `bytecode_hash`/`cache_key` are computed over.

So AC-14.2(iii) **fails on an unmodified tree, before a line of increment-5 code is written**. The only way to make it pass literally is to rename the graph payload's `resources` key and the IR's `op` tag — which §14.11 forbids in the same document ("**Wire format: no change**", "`IR_VERSION` stays **2**") and which would invalidate every cache entry and every shipped fixture.

The precedent this AC generalises is **module-scoped**, and the widening to all of `plr-sema/src/` is what broke it. `_channel_default_idiom`'s own docstring records the scope: "AC-10.9/AC-13.15(iii)'s AST literal scan forbids spelling it as a string constant **anywhere in this module or `plr_sema.check.tipstate`**" (`plr-sema/src/plr_sema/derive/receiver_state.py:303-305`).

**Why this is BLOCKER and not MINOR.** AC-14.2(iii) is the anti-hand-typing gate — the criterion that makes §14.11's "what could have been hand-typed, and what it is instead" table checkable rather than rhetorical. As written it is unrunnable, so the whole table is unenforced; and a fixer who "fixes" it by narrowing the scope silently to whichever files happen to pass has defeated the gate rather than met it.

**What must be resolved.** Which modules is the scan over, and does the answer still forbid the strings the table claims are not typed — in particular `"tracker"`, `"op"` and `"resources"`, which are the three that the *bridge* would most plausibly hard-code?

---

### O4 — BLOCKER (soundness) — a tip cell is keyed on channel index but its identity is the mounted `Tip`; no transfer function resets it, giving a false `SAFE`

**Location.** §14.3's `CellId` grammar; §14.5 V2 ("Cells outside `cells(op)` are unchanged") and V3; A-TIP-CELL in §14.7; AC-14.5(d)'s tip-cell half.

**Issue.** §14.3 defines `CellId = … | ("tip", channel: int)` and says only: "**a tip cell exists only where the tip family says a channel has a tip.** If the channel's `TipState` is not `HAS_TIP`, the tip cell is `TOP`." Two things follow that the document does not state:

1. Nothing defines the tip cell's interval **when** `TipState` *is* `HAS_TIP`. A fixer who mirrors PLR (`VolumeTracker.__init__`: `self.volume = initial_volume or 0`, `volume_tracker.py:49-50`) will seed a freshly-picked tip to `[0,0]`, which is right for the *first* pickup.
2. Nothing resets or widens a tip cell across `drop_tips` + `pick_up_tips`. `drop_tips` and `pick_up_tips` carry no volume bridge, so under V2 ("Cells outside `cells(op)` are unchanged") the interval survives the tip change, and V3's widen conditions ("`op`'s method has a volume bridge only at depth > 0", "two depth-0 volume bridges … disagree in direction") do not cover it either.

A-TIP-CELL is written entirely about the *not*-`HAS_TIP` direction and claims "nothing [breaks] in the `SAFE` direction: an unknown tip cell is `TOP` and every guard on it is `½`." That covers the case where the analyzer knows it doesn't know. It does not cover the case where the analyzer *thinks it knows* and is wrong, which is the one that produces an unsound verdict.

**Counterexample (false `SAFE` — first-severity class).**

```
lh.pick_up_tips(tip_rack["A1"])                      # tip cell ch0 := [0,0]
await lh.aspirate([well_A], vols=[50])               # tip cell ch0 := [50,50]
await lh.drop_tips(tip_rack["A1"], allow_nonzero_volume=True)
lh.pick_up_tips(tip_rack["A2"])                      # tip cell ch0 STILL [50,50] — no rule touches it
await lh.dispense([well_B], vols=[50])               # guard: 50 - lo = 0 <= 1e-06  → F → SAFE
```

Real execution: the tip from `A2` is a distinct `Tip` object with its own fresh `VolumeTracker` (`tip.py:45`, `volume_tracker.py:49-50`), so `used == 0`; `dispense` reaches `op.tip.tracker.remove_liquid(op.volume)` at `liquid_handler.py:1235` and `50 - 0 > 1e-6` → **raises `TooLittleLiquidError`**. The analyzer said `SAFE`. `allow_nonzero_volume=True` is what makes the `drop_tips` step legal — PLR's own guard is `if tip.tracker.get_used_volume() > 0 and not allow_nonzero_volume` (`liquid_handler.py:656`, and the multi-channel form at `:1571`), so the program is valid PLR and this is not a contrived shape.

**Evidence that no AC catches it.** AC-14.5's five fixtures are single-`aspirate`/`dispense` and one `while`; AC-14.6 is two-channel-one-well; AC-14.10's four tier-2b fixtures are named as straight-line, second-iteration, collective-exhaustion and two-channel. None re-tips. §14.9's tier-3 classes v1/v2 mutate a volume, not a tip sequence.

Note this is the *same class* of defect as round-1's O4, one level up: O4 established that pairs within one call must thread; this establishes that a tip cell's *identity* must thread across calls. The remediation fixed the first and did not consider the second.

**What must be resolved.** What is a tip cell's interval immediately after a `pick_up_tips`, and what happens to it on `drop_tips`? If the answer is "`TOP` unless the analyzer can prove the tip is fresh", say so and state the fixture that proves the retip case; if it is "`[0,0]` on every `HAS_TIP` transition", that is a claim about PLR's tip-spot semantics that needs its own assumption row and its own executed oracle.

---

### O5 — MAJOR — §14.6's harness observation reads `does_volume_tracking()` in the one window where it is guaranteed `False`, and the two harnesses disagree

**Location.** §14.6's "the env argument" box, third paragraph ("**The harness asserts the hypothesis by observation, not by typing it** … after the verifier establishes its configuration the harness **calls** `pylabrobot.resources.volume_tracker.does_volume_tracking()` … and passes `env = {"does_volume_tracking"}` iff it returns `True`"); AC-14.7; AC-14.9; AC-14.10.

**Issue.** The verifier sets the flag inside a `try` and **restores it in a `finally`**:

```
113        set_strictness(Strictness.STRICT if strict else Strictness.WARN)
114        set_volume_tracking(True)
...
149    finally:
150        set_strictness(old_strictness)
151        set_volume_tracking(old_volume_tracking)
```
(`training/verify/verifier.py:113-152`.)

So there is no "after the verifier establishes its configuration" window outside the verifier's own `try` block. The repo already pins this: `training/tests/test_verify_postconditions.py:78-84` imports `does_volume_tracking` and asserts `does_volume_tracking() is False` after a verifier run.

Tier 3's actual control flow makes the consequence concrete: `run_one_mutant` calls `oc.run_runtime(mutant)` at `plr-sema/eval/tip_mutants.py:178` and *then* `oc.run_static_calls(...)` at `:188`. Any observation taken between those two lines — the only place §14.6's sentence can mean — returns `False`, `env` stays empty, and every volume guard is `volume_tracking_unasserted`. AC-14.9's v1 achieved-`WILL_FAIL` count is `0` for a reason that has nothing to do with the interval domain.

Tier 2b behaves *differently*, and by accident: `region_oracle._run_fixture_execution` sets `set_volume_tracking(True)` at `plr-sema/eval/region_oracle.py:414` and its `finally` restores **only strictness** (`:436-437`) — the tracking flags leak. So after the first fixture executes, a process-wide observation returns `True`; before it, `False` (the module default, `volume_tracker.py:14`). The same static analysis therefore gets a different `env`, hence a different `cache_key` (`check/ir.py:953`), depending on which harness ran it and in what order. That is a non-determinism in a value the document treats as an observed fact.

**Counterexample.** AC-14.7 asserts fixture (a) "run through `check_ir` with the default `env == frozenset()`, yields `Verdict.UNKNOWN`". Fine. But AC-14.9/AC-14.10 require the *non*-default path, and no code path in `plr-sema/eval/` can currently produce it: `region_oracle.py:361` calls `check_mod.check_ir(bytecode, contracts, receiver_states)` positionally, and `_static_report` (`:354-366`) runs before `_run_fixture_execution` (`:398`) in the per-fixture flow.

**Also.** §14.6 states "`check_graph`'s two-positional-argument signature does not change." It does not say whether `check_graph` gains a keyword-only `env` (as it gained `cache=` in #4922 — `plr-sema/tests/test_cache.py:102-103`). Every caller in `plr-sema/tests/` uses `check_graph`; only `region_oracle` and `tip_mutants` reach `check_ir`. If `check_graph` gains no `env`, AC-14.4's and AC-14.5's fixtures must be written against `check_ir` directly, which is a different test shape than every existing fixture test.

**What must be resolved.** Name the *call site* at which the observation is taken and show it lies inside a window where the flag is `True` for the analysis it gates; and state whether `check_graph` gains `env`.

---

### O6 — MAJOR — the cache key already carries `env`; §14.14(6) and T27's scope are stale, and the stated invalidation does not happen

**Location.** §14.14 item 6; §14.6's "the env argument" box, last sentence; T27's scope column in §14.13; AC-14.8's neighbourhood.

**Issue.** §14.14(6): "**Increment 2 §11.3.3's cache key gains a fifth component**, `tuple(sorted(env))`. Increment 4 ships the cache without it (its `env` is always empty); **this increment adds the component and invalidates every entry written before it**, which is correct and is the cheap direction."

At HEAD, increment 4 shipped it:

```
918  def cache_key(
919      bc_hash: str,
920      contracts_json: str,
921      stamp: Any,
922      *,
923      ir_version: int = IR_VERSION,
924      env: frozenset[str] = frozenset(),
925  ) -> tuple[str, str, tuple[Any, Any, Any], int, tuple[str, ...]]:
...
953      return (bc_hash, contracts_sha, surface_identity, ir_version, tuple(sorted(env)))
```
(`plr-sema/src/plr_sema/check/ir.py:918-953`. Its own docstring cites "spec 260903 §13.3.2/§13.2.6" and explains that it defaults empty "because the volume family (its only producer) is deferred out of this increment (#4922)".)

Two consequences:

1. **Duplication risk.** T27's scope says "`env` on `check_ir` **and as the cache key's fifth component**". A fixer executing that literally against a `cache_key` that already has five components adds a sixth, changing every existing key and silently invalidating the whole cache — the failure §14.11's "wire format: no change" is meant to preclude. The document specifies work that is done and does not specify the work that isn't (threading `env` from `check_graph`/`check_ir` *into* the `cache_key` call, and into `CacheStore`'s lookup).
2. **The invalidation claim is false in both directions.** Every entry ever written was keyed with `env=frozenset()` → fifth component `()`. A post-increment run with the default `env` produces the *identical* key: **nothing is invalidated**. A run with `env={"does_volume_tracking"}` produces a different key — but that is a *partition* of the cache by hypothesis, not an invalidation, and it is the behaviour that makes §14.6's default-env direction sound. §14.14(6) describes neither correctly, and the "which is correct and is the cheap direction" reassurance is attached to an event that does not occur.

**What must be resolved.** What, concretely, does T27 change in `check/ir.py` and `check/cache.py` given `cache_key` already has the parameter, and what is T27's real LOC once that is subtracted?

---

### O7 — MAJOR — P10 re-implements, without polarity, a survey pass that already exists, is already correct, and already sits at the exact site the dropped call is recorded. §14.16 Q3 should resolve survey-side.

**Location.** §14.0.2's option table and its "**Decision: derive-side**" box; P10's normative box; A-SCOPE-TEXT in §14.7; §14.15's "A survey-side scope field for `dropped_calls`"; §14.16 Q3.

The mandate asks me to take a position on Q3 with evidence. **I take the survey-side position**, on four verified facts.

**(a) The survey already maintains exactly the datum P10 wants, at exactly the right place.** The dropped call is recorded inside `visit_Call`, one line, while `self._scope_trail` is live:

```
135        self._scope_trail: list[str] = []
...
250                self.dropped.add(ast.unparse(target))
```
(`/home/marielle/projects/praxis/scripts/survey_plr_preconditions.py:135,250`.) Changing `:250` to append `(ast.unparse(target), node.lineno, list(self._scope_trail))` is the same three-tuple `_record` already builds for findings at `:157-160`. §14.0.2's cost column calls this "a cross-package event"; the *code* is three lines in a visitor that already computes the value.

**(b) The survey's trail is polarity-aware; P10's, as specified, is not.** The survey pushes `"else of: if {test}"` for an `orelse` branch, with a comment explaining that an `elif` chain self-nests and compounds correctly:

```
167        self._scope_trail.insert(0, f"if {test_src}")
...
171        if node.orelse:
177            self._scope_trail.insert(0, f"else of: if {test_src}")
```
(`survey_plr_preconditions.py:167-180`.)

P10's box says only: "the ordered list of enclosing `ast.If` test sources and `ast.For`/`ast.While` headers." An `ast.If` whose `orelse` contains the call is an *enclosing* `ast.If`, and P10 as written records its test **as if it were asserted** — the exact negation of the truth. PLR writes this shape today: `dispense96`'s `tip.tracker.remove_liquid` at `liquid_handler.py:1935` sits in the `elif` of `if does_volume_tracking():` at `:1932`, i.e. it runs *only when tracking is off*, and P10 would record `"if does_volume_tracking()"` for it. Under `env = {"does_volume_tracking"}` that entry is **recognised as satisfied** by §14.6 — an unblocked `WILL_FAIL` on a site that only executes when the hypothesis is false. It is masked at this pin only because that particular text appears twice in the method (`:1933` and `:1935`) and P10's zero-or-multiple rule records `null`. That is luck, not fail-closed design, and it evaporates the moment either occurrence is renamed.

**(c) A-SCOPE-TEXT's discharge argument is wrong about what it discharges.** "What would break it is a *single* textual match that is nonetheless the wrong call — **impossible while the key is the full dotted callee**." Textual uniqueness identifies the *call*; it says nothing about the *polarity* of the branch that encloses it, which is (b). The assumption row discharges a different risk than the one that exists.

**(d) The multiplicity P10 needs is destroyed before it reaches the artifact anyway.** `self.dropped` is a `set[str]` (`survey_plr_preconditions.py:142`) and `dropped_calls` is `list[str]` (`:120`). Two occurrences of one expression collapse to one entry. So the artifact cannot tell the derive-side pass "there were two of these" — only re-parsing can, which is what P10 does, which is the re-implementation.

**Ordering, a third convention.** The survey's `scope_trail` is documented and emitted **nearest-first** (`:85-87`, `insert(0, …)`), confirmed in the artifact: `["if self._blow_out_air_volume is None", "if any(…)", "if does_volume_tracking()"]` (`training/verify/data/plr_preconditions.json:49808-49812`). P10 declares `caller_scope` **outermost-first**. §14.0.2's own measured expectation is written in a *third* order — `["if does_volume_tracking()", "for op in aspirations", "if not …is_disabled"]` — which is neither, since the real outermost frame is `for op in aspirations` (`liquid_handler.py:1031`). AC-14.3(ii) requires the two keys be "kept apart"; they will sit adjacent in one guard dict with opposite conventions and no schema note.

**Position.** The survey-side option is not "better in the long run"; it is cheaper *now* (three lines at an existing site vs. a new visitor), strictly more correct (polarity already handled, `elif` already handled, ordering already conventional), and it is the only one that preserves multiplicity rather than reconstructing it. §14.0.2's blast-radius argument counts the survey artifact's regeneration as a cost while not counting the reimplementation of `visit_If`/`visit_For`/`visit_While` semantics as one. **Q3 should resolve survey-side.**

**What must be resolved.** If derive-side stands, P10's box must state what it does for `orelse` branches, and `caller_scope`'s ordering must be reconciled with `scope_trail`'s or the difference documented in the schema.

---

### O8 — MAJOR — §14.8's seed `CALL` names a receiver outside `SUPPORTED_TOOLS` and a `.tracker` the IR grammar cannot express

**Location.** §14.8's normative box; AC-14.5's "Four fixtures, each with a prepended seed `CALL`"; AC-14.5(a)'s "**exactly one** `Finding`".

**Issue.** §14.8: "prepends a `CALL` to the derived volume-setting method — `VolumeTracker.set_volume` … — **with the cell as receiver** and the seed as a `Lit` kwarg". Two problems:

1. **The receiver is not the cell.** `set_volume` is a method on `VolumeTracker`, not on the `Well`. §14.3 says a container cell id "reuses the `Ref(slot, cell)` pair the value grammar already produces (§11.1.2), **so a well reference in a kwarg *is* a cell id with no new resolution machinery**." A `Ref(slot, cell)` names a well. Nothing in the IR names `well.tracker`. So either the `CALL`'s receiver is the `Well` (and the method `set_volume` does not exist on it) or it is a `VolumeTracker` (and there is no `Ref` that denotes one).
2. **`VolumeTracker` is not a supported tool.** `plr-sema/src/plr_sema/check/_supported_tools.py` contains no `VolumeTracker` (nor `TipTracker`). An operation whose receiver is outside the analyzed surface yields `unsupported_tool` — a live `REASON_VOCABULARY` member (`plr-sema/src/plr_sema/verdict.py:143-144`).

And the seed `CALL`'s own finding is **not suppressed**. `origin` is used only to relabel finding op-ids (`plr-sema/src/plr_sema/check/__init__.py:693-694`, `:776-777`); there is no origin-based filter on the findings list. So a prepended seed `CALL` contributes at least one `Finding` of its own, and AC-14.5(a)'s "**exactly one** `Finding`" fails on an otherwise-correct implementation.

§14.8's closing claim — "A prepended `CALL` reuses an opcode, a lowering path and an `origin` convention that all shipped in increment 3 and are pinned by AC-12.3" — is true of the *opcode* and false of the *surface*: increment 3's precedent prepends `setup()`, whose receiver `LiquidHandler` is already a supported tool. Extending the supported surface to a tracker class is a new fact, not a reuse.

**What must be resolved.** What is the seed `CALL`'s `receiver_type` and `method` as they appear in the lowered `Bytecode`, and by what rule does the checker recognise it as a seed rather than emit `unsupported_tool` / `no_contract_derived` for it?

---

### O9 — MAJOR — B2's "bit-for-bit unaffected" is asserted as structural and is only empirical; and it is unstated whether B2/P1c feed the receiver-selection loop at all

**Location.** §14.0.1's B2 box ("`_is_self_attr` … is **not** changed — the new admission is a second, disjoint branch, **so** every existing P1a selection is bit-for-bit unaffected and no shipped `receiver_state` value moves"); the P1c box ("P1c is consulted **only after** P1a: an annotated attribute always wins, so P1c can add knowledge and never overwrite it"); §14.4's bridge box ("typed by P1a-as-extended-by-B2", "`<attr>` is sent by P1a **or P1c**"); AC-14.1(iii).

**Issue (mechanism).** The "so" is a non-sequitur. The two branches are disjoint *predicates* writing into **one shared dict with `setdefault`**, and `ast.walk` is breadth-first:

```
172  def _annotated_attributes(class_node: ast.ClassDef) -> dict[str, str]:
...
177      out: dict[str, str] = {}
178      for node in ast.walk(class_node):
179          if isinstance(node, ast.AnnAssign) and _is_self_attr(node.target):
...
182              out.setdefault(node.target.attr, unwrapped)
```
(`plr-sema/src/plr_sema/derive/receiver_state.py:172-183`; note also that the docstring already advertises "class-level or inside any method", which is about `self.x: T` written at class level, not about bare-name fields.)

A class-level `AnnAssign` is a **depth-1** child of the `ClassDef`; a method-body `self.x: T` is depth ≥ 2. BFS visits depth 1 first, `setdefault` gives first-writer-wins, so on any name collision **the new branch displaces the existing selection**. "Disjoint branch" therefore does not imply "unaffected"; only a measurement does. The document states the outcome as a structural guarantee and then asks the fixer to measure the thing it just guaranteed.

**Issue (scope — the part a fixer will get wrong).** §14.4 says `<field>` is "typed by P1a-as-extended-by-B2" and `<attr>` is "sent by P1a **or P1c**". Nothing says whether the extended map is the *same* map `derive_receiver_states` consumes to select a receiver's anchored attribute:

```
718      for receiver_name, receiver_node in sorted(class_nodes.items()):
719          annotated = _annotated_attributes(receiver_node)
...
723          for attr_name in sorted(annotated):
...
784              break  # first (alphabetically) qualifying attribute wins.
```
(`receiver_state.py:718-785`.) This loop runs over **every class in the PLR tree** and its selection is an alphabetical tie-break over `annotated`'s keys. A fixer who reads "P1a-as-extended-by-B2" and "P1a or P1c" as extending *the* P1a map — the natural reading — changes this loop's input for every class in PLR, in a pass whose own docstring flags that the tie-break is load-bearing ("`head` < `head96`", `:720-722`).

**Measured, at this pin, the outcome happens to be safe** — which is why this is MAJOR and not BLOCKER. `derived_contracts.json` carries exactly two `receiver_state` entries, `LiquidHandler` (`:168078`, `channel_attr: "head"`) and `LiquidHandlerBackend` (`:168135`, `channel_attr: "_head"`), both `tracker_class: "TipTracker"` (`:168133`, `:168158`). A grep across the whole PLR tree for a class-level annotation typed to `TipTracker` or `VolumeTracker` returns **zero** matches. `LiquidHandler` has no class-level annotations at all (`liquid_handler.py:123-131`) and no constructor-call write in `__init__` (`:132-176` — `Resource.__init__`/`Machine.__init__`/`Coordinate.zero()` are `ast.Attribute` funcs, not `ast.Name`). `LiquidHandlerBackend` **does** gain one under B2 — `_num_arms: int = 0` (`external/pylabrobot/pylabrobot/liquid_handling/backends/backend.py:38`) — but `"_head" < "_num_arms"` and `int` is not in the class index, so it loses twice over.

So AC-14.1(iii) will pass. The objection is that the document says it will pass *because the branches are disjoint*, which is not the reason, and a reviewer reading the B2 box has no way to know the guarantee is contingent on a coincidence of alphabetical ordering.

**What must be resolved.** Do B2 and P1c extend the map consumed at `receiver_state.py:719`, or a separate map used only by the bridge? And is the B2 box's guarantee restated as "measured, and here is the fixture that would catch a displacement" rather than as a structural consequence?

---

### O10 — MAJOR — two methods raise `TooLittleLiquidError` under a `get_used_volume()` compare, so V2's "which method is which is **derived**, not typed" is under-determined

**Location.** §14.4's P7 box and its fail-closed rule; §14.5 V2 ("the decreasing one is P7's `TooLittleLiquidError`-guarded method and the increasing one is the `TooLittleVolumeError`-guarded one"); §14.11's "what could have been hand-typed" table, row 2.

**Issue.** At the pin, `VolumeTracker` has **two** methods raising `TooLittleLiquidError` from an `ast.Compare` naming `get_used_volume()` and one of the method's own parameters:

```
 88  def remove_liquid(self, volume: float) -> None:
 91    if (volume - self.get_used_volume()) > 1e-6:
 92      raise TooLittleLiquidError(...)
...
122  def get_liquids(self, top_volume: float) -> List[...]:
135    if (top_volume - self.get_used_volume()) > 1e-6:
136      raise TooLittleLiquidError(f"Tracker only has {self.get_used_volume()}uL")
```
(`external/pylabrobot/pylabrobot/resources/volume_tracker.py:88-99,122-138`. §14.1 names the `:136` raise itself, so the document knows about it.) `VolumeTracker.get_liquids` is a real contract entry (`plr-sema/data/derived_contracts.json:158054`).

P7's fail-closed rule covers "Zero anchors, or **≥2 candidate used-volume accessors**". Both methods name the *same* accessor, so P7 survives — correctly. But V2's direction assignment is per **method**, and it is written in the singular ("P7's `TooLittleLiquidError`-guarded method"), with no tie-break for two of them. `get_liquids` decrements nothing; classifying it as a "used-volume-**decreasing** effect" and applying `[max(0, lo-a), max(0, hi-a)]` would silently move the interval on a pure read.

At this pin nothing matches — the bridge shape is four segments (`<name>.<field>.<attr>.<method>`) and no `dropped_calls` entry of that shape names `get_liquids`. So this is latent, not live. It is MAJOR rather than MINOR because (a) `get_liquids` is deprecated (`volume_tracker.py:126-133`) and a deprecation removal is exactly the kind of change that moves which method is "the" one, and (b) §14.11's table sells "which method is which" as fully derived, and the derivation as written does not determine it.

**What must be resolved.** State P7/V2's tie-break when a class has ≥2 methods raising the same taxonomy member, and say whether it is fail-closed (emit nothing) or selective (and on what).

---

### O11 — MAJOR — `transfer` has no derivation path, so §14.9's v2 mutant class has no static side

**Location.** §14.9's normative box (v2 `v2_overdraw_transfer`); AC-14.9's v2 half; §14.16 Q5.

**Issue (answering the mandate's "what does B1 do on `transfer`").** Nothing. `LiquidHandler.transfer` (`liquid_handler.py:1273-1361`) contains no `ast.ListComp`/`GeneratorExp` over a `zip` of names, so P8 does not match; there is no `for` loop over a comprehension's output, so B1 binds nothing; and there is no four-segment `<name>.<field>.<attr>.<method>` call in its body, so the volume bridge never fires. `transfer` reaches the trackers only through `await self.aspirate(...)` at `:1347` and `await self.dispense(...)` at `:1355`.

Even if `volume_guards` were propagated through `delegates_to`, the parameter binding does not exist: `transfer`'s signature is `(source: Well, targets: List[Well], source_vol, ratios, target_vols, …)` (`:1273-1283`) — no `resources`, no `vols`. What it passes is `resources=[source]` and `vols=[sum(target_vols)]` (`:1348-1349`), a **computed** expression, and `target_vols = [source_vol * r / sum(ratios) for r in ratios]` (`:1345`), also computed. §14.5 V0 requires `amounts(op)` to be a `Seq` of numeric `Lit`s; a `sum()` over a computed list is not, so V0 does not apply and V3 widens every cell to `TOP`.

Nothing in §14.0, §14.4 or §14.5 specifies volume-guard propagation through `delegates_to` at all — the bridge box attaches guards to `K`, the method whose own `dropped_calls` carried the expression. §14.9 nonetheless names a mutant class for `transfer`, and AC-14.9 defers its threshold on the grounds that "`transfer`'s guard interacts with #4946's binding and the interaction must be measured before it is gated" — presupposing a `transfer` guard exists. #4946 *did* land a `transfer` binding (`derived_contracts.json:168096-168113`, `delegate_channel_binding.transfer.{aspirate,dispense}`), but that is a **channel** binding, not a volume one, and the two mechanisms are not the same.

**Consequence.** T28 (~430 LOC) builds a mutant class whose static side is structurally `UNKNOWN` for every row, and AC-14.9's "no threshold" makes that pass. The AC cannot fail, so it is not a gate.

**What must be resolved.** Is there a specified path by which `LiquidHandler.transfer` acquires a `volume_guards` entry? If not, does v2 stay, and on what argument, given AC-14.9 cannot distinguish "measured 0 because the interaction is subtle" from "structurally 0 because no rule matches"?

---

### O12 — MINOR — §14.11's HM-25 accounting understates, and B1's failure mode belongs to HM-24, not HM-25 (§14.16 Q2)

The mandate asks me to count against the registry's own definition of a pattern. **HM-25 is 6 today, correctly.** Its `what` field enumerates exactly six (`plr-sema/src/plr_sema/_hand_maintained.py:825-840`): P2's anchor property shape, P3a's channel-default idiom, the three atom productions, and P9's delegate-call shape; `declared=6` at `:842`, and increment 4's 5→6 P9 bump is already in the tree (HEAD `18b8d38b`). §14.11's entry condition is right.

**HM-24 1→2, which entry.** The second pattern is the volume bridge regex — a distinct shape (`<name>.<field>.<attr>.<method>`, four captures) from the tip bridge's `self.<attr>[<name>].<method>` (three captures). `_measure_hm24` returns a literal `1` and asserts `_BRIDGE_SHAPE_RE.groups == 3` (`_hand_maintained.py:255-261`), so the "gets its own measure, asserted the same way" plan is coherent. **No objection to HM-24 1→2.**

**On 8 vs 10: 8 understates.** §14.11's test for a pattern is HM-25's own `breaks_when` shape — "PLR stops writing X". Apply it to B1: `for op in aspirations:` is the shape; `for i, op in enumerate(aspirations):` is idiomatic Python that PLR could adopt tomorrow, and B1's own fail-closed rule ("the `ast.For` target is a tuple rather than a single `ast.Name`, … B1 binds nothing") would then silently disable the volume family. That is a syntactic pattern over how PLR is written, on the registry's own definition. §14.11's counterargument — "what they match is a *binding*, resolved by Python's own scoping rules, not a recognisable idiom" — is not true of B1 as specified: B1 does not resolve bindings, it matches a shape (single-`Name` `For` target, bare-`Name` `iter`, single-target `Assign`, depth 0). A binding resolver would handle `enumerate`; B1 does not.

I accept §14.11's argument for **B2** (class-level `AnnAssign` is a language construct) and, conditionally on O2's resolution, for **P1c**: if P1c stays keyed on `__init__`, it is *not* a language construct — it is a bet on which method PLR writes trackers in, and PLR already writes them in two (`container.py:85` in `__init__`, `tip.py:45` in `__post_init__`), so keying on `__init__` is a pattern. **P10** is closer to a language construct than B1, but its failure mode (a second textual occurrence appears → `caller_scope: null` → family silently produces no definite verdict) is HM-24's *silent* failure mode, not HM-25's *loud* one — which is the exact criterion the 260902 Q7 split was made on (`_hand_maintained.py:244-253,796-799,850-861`).

**So: ≥9, not 8, and the split is wrong as well as the count** — B1 (and P10, if counted) belong on the row whose declared failure mode is silent collapse. §14.16 Q2's own suggestion (a row split rather than a ceiling bump) is the better instinct, and it interacts with the zero-headroom claim (`BUDGET_CAP = 24`, `_hand_maintained.py:43`) that §14.11 states without leaving room for it.

---

### O13 — MINOR — stale scheduling text, an already-landed task, and analyzer citations that drift 2–23 lines

**(a) Stale "unscheduled/deferred" sentences.** Complete list, as the mandate requests:

| line | text |
|---|---|
| 3 (frontmatter `description`) | "**NOT SCHEDULED**: the task rows below are unscheduled by construction and no AC here gates any increment-4 work." |
| 2 (frontmatter `title`) | "…**deferred out of increment 4 until its derivation is proved**" |
| 16-17 (top blockquote) | "**It is `draft-deferred`: nothing in it is scheduled.**" |
| 29 (§14.0 heading) | "## 14.0 **Why this is deferred**, and what must be proved first" |
| 620 (§14.12 preamble) | "They gate the **unscheduled** rows of §14.13." |
| 715-717 (§14.13 blockquote) | "> **Every row in this table is unscheduled.** No row is dispatched by increment 4's sprint, **no gate below is run this round**…" |
| 844, 877-878 (References, Remediation changelog) | "**This document has had no adversarial round of its own.**" (×2) |

Line 715 is the sharpest: it directly contradicts the heading immediately above it, `## 14.13 Task rows — **scheduled: next sprint (user decision 260903)**` (line 714). A fixer reading §14.13 top-down is told in consecutive lines that the rows are scheduled and that every row is unscheduled.

**(b) T29 and AC-14.11 are already satisfied at HEAD.** `SPEC_INCREMENT_5` is already defined at `plr-sema/tests/test_spec_lint.py:36` and already parametrised into both live-spec tests at `:220` and `:243` (id `increment-5-volume-deferred` — itself now stale). T29's scope ("add `SPEC_INCREMENT_5` to `test_spec_lint.py`'s two parametrised live-spec tests") is a no-op; only the `INDEX.md` regeneration remains.

**(c) Analyzer citations drift.** Verified against the current tree — every one of these is *within* the cited range or off by a small margin, so most will survive the citation checker's bounds-and-symbol test (`test_spec_lint.py:81-132`), but they will send a fixer to the wrong code:

| spec cites | actual |
|---|---|
| `_is_self_attr` at `receiver_state.py:164-167` | `:166-169` |
| `_annotated_attributes` at `:170-181`, `AnnAssign` test at `:177` | `:172-183`, test at `:179` |
| `_constructor_state` at `:523-563`, "**locates a class's own `__init__` (`:540-545`)**" | `:546-586`; `:540-545` is inside **`reset_rule_candidates`**, a different function — the fixer is pointed at the wrong pass for the architecture P1c is "modelled directly on" |
| "walks both `ast.Assign` (`:548`) and `ast.AnnAssign` (`:551`)" | `:571` and `:574`; `:548`/`:551` are docstring lines |
| `compute_channel_bridge` "the copy at `:787`" | `:787` is the P9 section comment; the `"scope_trail": list(guard.scope_trail)` copy is at `:1041` |
| `live_rows()` at `_hand_maintained.py:851-855` | `:867-871` |
| HM-24 row at `:781-814`, its three fields at `:793-795` | row `:788-822`, fields `:801-803` |
| HM-25 row at `:815-847`, "the same three fields at `:828-830`" | row `:823-863`, fields `:841-843`; `:828-830` is prose inside the `what` string — **this one has no matching symbol in range and is the most likely to fire the citation lint** |
| `SingleChannelDispense` mirror at `standard.py:63-67` | the class is `:63-72`; `volume: float` is at `:68`, outside the cited range |

AC-14.11 asserts "**zero** failing violations over this file". Given the `:828-830` and `:793-795` cases that is a prediction, not a fact, and it is checkable in one command (`uv run pytest plr-sema/tests/test_spec_lint.py -q`) that the document does not ask anyone to run before claiming it.

---

### O14 — MINOR — three ACs are publication-without-threshold, and AC-14.6's executed half cannot distinguish the case it exists to catch

Answering the mandate's item 8 — a per-AC pass:

| AC | mechanically checkable as written? |
|---|---|
| AC-14.1(i),(iii),(iv) | yes for the assertions; **(ii) and the "complete set … is published" halves of (i)/(iv) are publish-only with no expected value** — they cannot fail |
| AC-14.2(i),(ii) | yes; (ii)'s numbers verified correct (4 → 2). **(iii) fails at HEAD — O3** |
| AC-14.3(i) | "published **verbatim as produced**" — cannot fail. (ii)/(iii) are real assertions |
| AC-14.4 | yes, and the `null` case is genuinely stub-defeating — but its premise ("a guard whose `caller_scope` is exactly `["if does_volume_tracking()"]`") cannot be constructed from the real bridge (O1), so all four fixtures must be synthetic contract tables |
| AC-14.5 | yes, modulo O8 ("exactly one `Finding`") and O1 (the `WILL_FAIL` in (a)) |
| AC-14.6 | static half yes; **executed half is inert** — see below |
| AC-14.7 | yes (the `SAFE`-unchanged half is the strongest assertion in the document) |
| AC-14.8 | yes — and it is the only AC that names both an expected value and its entry condition |
| AC-14.9 | v1 half yes; **v2 half has no threshold by design (§14.16 Q5) and, per O11, structurally cannot fail**; the m1/m2 non-regression is "published against whatever baseline is current", which is not a value |
| AC-14.10 | yes as written, but unsatisfiable per O1 |
| AC-14.11 | yes, one command — and per O13(b) half of it is already true |

**AC-14.6's executed half specifically.** It requires "the static and executed sides agreeing" for a two-channel/one-well fixture, where the static side is asserted *per pair*. But `region_oracle` compares on `(operation, iteration)` and joins all static findings for a key before comparing: `_verdict_at` returns `join_fn(tuple(per_iter[iteration]))` (`plr-sema/eval/region_oracle.py:344-351`). Both pairs of one `aspirate` are the same operation at the same iteration, so the comparison key has no pair dimension: a `SAFE` and a `WILL_FAIL` for the two pairs join to a single verdict, and an implementation that emitted `WILL_FAIL` for *both* pairs (or for the wrong one) agrees with the execution just as well. The stub-defeating power of AC-14.6 lives entirely in its static half; the executed half adds a run and no discrimination. §14.10's soundness table nonetheless lists AC-14.6 as the oracle for "two channels drawing one well are checked sequentially, **not simultaneously**".

---

## Adjudication of §14.16's open questions

1. **Q1 — settled by the user, not re-litigated.** But its premise is at issue: the resolution is "build it **if it is firable at all**", and O1 reports that under §14.6 as written it is firable on *no* tier, including the harness-controlled fixtures the resolution explicitly counts on ("a family that produces `SAFE` on real rows and `WILL_FAIL` on every protocol a fixture … can construct"). That is a factual correction to the input of the decision, not a challenge to the decision.
2. **Q2 — 8 understates; ≥9, and the split is wrong too.** See O12. B1 is a pattern by HM-25's own `breaks_when` test, and its failure mode is HM-24's (silent) rather than HM-25's (loud), so a ceiling bump on HM-25 is the wrong instrument even at the right number. Q2's own alternative — a row split — is the better one, and it is unpriced against the zero-headroom claim.
3. **Q3 — resolve survey-side.** See O7. The derive-side decision is taken on a cost comparison that counts the artifact regeneration and does not count the reimplementation of `visit_If`/`visit_For`/`visit_While`; the survey already computes the exact datum, already handles `else`/`elif` polarity which P10's box omits entirely, and already fixes an ordering convention P10 contradicts. The survey-side change is ~3 lines at `survey_plr_preconditions.py:250`. The mandate asked for a position; this is it, with the code.
4. **Q4 — follows Q1, but conditionally on O1.** `volume_tracking_unasserted` will have a producer under §14.6 — in fact it will be the *only* volume outcome besides `SAFE`/`volume_state_unknown`. The member should land. `volume_state_unknown` is fine. The dead-data risk has moved: it is now `WILL_FAIL` itself, not a reason string.
5. **Q5 — a reviewer *should* hold that an ungated class does not ship, and O11 sharpens why.** The stated reason for no threshold ("the interaction must be measured before it is gated") presupposes an interaction. Per O11, `transfer` has no volume-guard derivation path at all, so v2's static side is `UNKNOWN` by construction and the class measures nothing about the implementation. Publishing 0 from a class that can only be 0 is the failure mode §14.9's own closing paragraph names for the over-fill mutant it declined to write ("a class whose gate can only ever be `0 of n` measures the spec's own scope decision rather than the implementation"). The same argument applies to v2 and is not applied.

---

## Verdict

**Implementable as written: no.**

The re-scope did its job on three of round 1's four objections. §14.5's V2 threading (O4) is correct and its counterexample checks out against `liquid_handler.py:997-999,1031-1035`. §14.0's G1–G3 diagnosis is accurate. §14.1, §14.2, §14.3 and §14.7 survive unchallenged, and the taxonomy arithmetic, the capacity argument and the `1e-06`-is-read-not-typed claim all verified exactly.

What does not survive is the remediation of round 1's **O2**. §14.6 generalised "a zero-argument call" to "anything unrecognised blocks `WILL_FAIL`" — which is the right fail-closed direction — and then did not check what that rule does to the only guards the bridge produces. It blocks all of them, permanently, on every tier, because their `caller_scope` contains a `for` header that no `env` can ever satisfy. The document half-sees this (§14.6's closing paragraph, §14.16's Q1) and escapes it with a sentence that is a category error: the harness controls fixtures, but `caller_scope` is derived from PLR's source, not from the fixture. Five acceptance criteria and the sprint's own GO gate rest on a verdict the document's rules forbid.

Compounding it, the bridge's tip half cannot derive at all (**O2**): P1c reads `__init__`, `Tip` is a `@dataclass` whose tracker write is in `__post_init__`, and §14.2 says so twelve paragraphs later. That removes one of `aspirate`'s two guards and *both* of `dispense`'s decidable ones. And the gate that would have caught hand-typing (**O3**) is red on an unmodified tree.

**Single most important thing to resolve.** Reconcile §14.6's recognition set with the `caller_scope` the bridge actually produces at this pin. Either the recognition set admits something beyond a bare zero-argument call — in which case say precisely what, and re-argue soundness, since P10's missing `orelse` polarity (O7) becomes live the instant it does — or the `WILL_FAIL` path is withdrawn and AC-14.5(a), AC-14.6, AC-14.7 and AC-14.10 are rewritten around `SAFE`/`UNKNOWN` only, in which case the sprint gate as stated cannot be met and the increment's headline deliverable is a `SAFE`-only family. Both are defensible; the document currently asserts the first while specifying the second.

**Ordering consequence for T24/T25.** §14.0's normative gate (no `Finding` machinery before T24 **and** T25 both land) is sound and should stand. But T24 cannot publish AC-14.1(iv)'s `Tip.tracker → VolumeTracker` until O2 is resolved, and T25 cannot publish AC-14.3's `caller_scope` in a form §14.6 can act on until O1 is. Both blockers land *before* the first line of T24, not during it.
