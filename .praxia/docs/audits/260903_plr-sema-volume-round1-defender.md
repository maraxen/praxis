---
title: 'plr-sema increment 5 (the volume family) — adversarial round 1, defender'
description: 'Defender adjudication of the round-1 challenger on spec_version 13 draft (5458f24b). O1 PARTIAL — the challenger''s global claim ("WILL_FAIL unreachable on every tier") is REJECTED with a mechanism: the B1-bound `for` header is structurally satisfied, not hypothetical (PLR''s own ValueError at liquid_handler.py:989-992 pins the trip count to the pair-list length), and `is_disabled` fail-closed costs exactly zero on the one guard that matters, because dispense''s `op.tip.tracker.remove_liquid` (:1235) is NOT under the is_disabled test and IS the decidable direction; the sprint gate is met on the tip cell. CONCEDED within O1: AC-14.5(a), AC-14.6''s executed half and AC-14.10''s fixture set are on the aspirate/well path, which is permanently blocked, and must move to the dispense/tip path. O2 CONCEDE (P1c must scan every method, not `__init__`; verified exactly three `self.tracker =` writes in PLR, no intra-class duplication, so the wider scan is strictly safer AND makes §14.11''s language-construct argument true). O3 CONCEDE (verified `"op"` at ir.py:860-887 and `"resources"` at ir.py:320,446 / graph.py:193; remedy is the shipped module-scoped precedent at receiver_state.py:303-306, which stays green and still gates). O4 CONCEDE, blocking (retip false SAFE verified; remedy is a tip-cell transfer function plus a monotone tips_dirty flag — TOP-always kills the family, [0,0]-always is unsound). O5 PARTIAL (window conceded; challenger''s region_oracle ordering claim CORRECTED — execution at :516 precedes static at :527). O6 CONCEDE. O7 CONCEDE polarity and Q3 survey-side, on a stronger reason than the challenger''s: the survey''s lineno is what lets O1''s for-recognition key on node position rather than text. O8 PARTIAL — (2) REJECTED outright (T11 decoupled SUPPORTED_TOOLS from the analyzed surface; VolumeTracker.set_volume is a real contract key at derived_contracts.json:158185) and (1)''s "no mechanism" REJECTED (lower_calls accepts receiver/receiver_type overrides, ir.py:794-795, and Call.receiver IS a slot int); (3) conceded on a verified gap finding. O9 PARTIAL. O10 PARTIAL, with a strictly-more-derived remedy (AugAssign sign at volume_tracker.py:96/:109). O11 CONCEDE. O12 PARTIAL (the instrument is HM-24, not HM-25). O13 CONCEDE. O14 PARTIAL. Two defender-identified blocking gaps the challenger missed: D1 the tip guard''s cell_param is a LOCAL pairing (tips built at liquid_handler.py:974), never a kwarg, so V0 as written cannot produce a tip cell id at all — and after O1 the entire headline deliverable runs through the tip cell; D2 V0 must also agree with a literal use_channels. Verdict needs_revision.'
status: final
task_id: 260903_sema-volume
backlog_id: '4962'
date: '260903'
confidence: high
sources: 'praxia:spec-defender (claude-opus-5). Spec read in full (887 lines). Challenger report read in full (O1-O14). Increment-4 round-1 defender read in full; increment-4 challenger read via the defender''s per-objection quotations and the spec''s §14.0 restatement. NO BASH TOOL available to this agent: `git -C`, `rg`, `sed -n` and `uv run pytest` were not runnable; every citation below is from Read (cat -n line numbers) or Grep (ripgrep-backed). Pin verified by reading `.git/modules/external/pylabrobot/HEAD` = dd79c4c89bc008629a1c598ea614be5e6067d1f9. PLR at that pin: liquid_handling/liquid_handler.py:648-667,955-1068,1220-1249,1273-1361,1925-1943; liquid_handling/standard.py:30-84; resources/volume_tracker.py (full, 171 lines); resources/container.py:75-94; resources/tip.py (full, 83 lines); grep `self\.tracker\s*=` over the whole submodule. Analyzer: derive/receiver_state.py:155-199,295-314,535-587,715-793 + full def-line index; check/ir.py:170-208,756-825,910-953; check/__init__.py:96-120,340-393,680-739,766; check/_supported_tools.py (full); check/tipstate.py:245; verdict.py:125-159; _hand_maintained.py:43,240-269,786-872. Harness: eval/region_oracle.py:330-366,398-440,512-531; eval/tip_mutants.py:160-204; training/verify/verifier.py:100-159; training/tests/test_verify_postconditions.py:70-86; scripts/survey_plr_preconditions.py:130-189. Artifacts: plr-sema/data/derived_contracts.json:157973,158054,158110,158185-158197; plr-sema/tests/test_spec_lint.py:25-49,210-254. No file edited. Persisted verbatim by the orchestrator: the defender agent type has no write tool.'
---

# plr-sema increment 5 (the volume family) — adversarial round 1, defender

Target: `.praxia/docs/specs/260903_plr-sema-volume-increment.md` at `5458f24b`. Challenger: `.praxia/docs/audits/260903_plr-sema-volume-round1-challenger.md`. Verbatim defense.

**Tooling disclosure.** This agent has no Bash tool. `git -C external/pylabrobot rev-parse HEAD` was not runnable; the pin was verified by reading `/home/marielle/projects/praxis/.git/modules/external/pylabrobot/HEAD`, which contains `dd79c4c89bc008629a1c598ea614be5e6067d1f9` — the spec's and the challenger's stated pin. `uv run pytest plr-sema/tests/test_spec_lint.py -q` was likewise not runnable; O13's citation-lint prediction is adjudicated on the file contents, not on a run, and that limitation is carried into the remediation list as an item someone must actually execute.

**Scope.** §14.16 Q1 is settled by the user and is not re-opened. The `is_disabled` fail-closed rule stays for soundness; the question the mandate puts is whether *anything else* may soundly enter the recognition set, and whether the family is firable at all under the answer. That is O1 and it is where most of this report goes.

---

## O1 — BLOCKER as filed — **PARTIAL. The global claim is REJECTED with a mechanism; four acceptance criteria are CONCEDED and must move to a different guard.**

The challenger's structural facts are all correct and I re-verified every one. The conclusion drawn from them is not.

### What is true

`liquid_handler.py:1031-1035`, read directly:

```
1031    for op in aspirations:
1032      if does_volume_tracking():
1033        if not op.resource.tracker.is_disabled:
1034          op.resource.tracker.remove_liquid(op.volume)
1035        op.tip.tracker.add_liquid(volume=op.volume)
```

and the dispense mirror at `:1231-1235`:

```
1231    for op in dispenses:
1232      if does_volume_tracking():
1233        if not op.resource.tracker.is_disabled:
1234          op.resource.tracker.add_liquid(volume=op.volume)
1235        op.tip.tracker.remove_liquid(op.volume)
```

`caller_scope` is derived from PLR's source and no fixture changes it — conceded, that part of the objection is exactly right, and §14.6's escape sentence ("only the tier-3 mutants — whose fixtures the harness controls") is the category error the challenger names. §14.0.2's single measured expectation for both of `aspirate`'s guards is also wrong, for the reason the challenger files as "secondary".

### Why the "secondary" point is not secondary — it is the whole mechanism

Indentation is load-bearing here and the challenger read past it. **The two guards of one method have different scopes, and at this pin the difference lands exactly on the decidable/undecidable axis.** Enumerating all four bridged guards against §14.2's capacity argument:

| site | expression | direction | decidable? (§14.2) | `caller_scope` | under `is_disabled`? |
|---|---|---|---|---|---|
| `:1034` | `op.resource.tracker.remove_liquid` | under-draw | **yes** | for · dvt · is_disabled | **yes** |
| `:1035` | `op.tip.tracker.add_liquid` | over-fill | no (capacity ⊤) | for · dvt | no |
| `:1234` | `op.resource.tracker.add_liquid` | over-fill | no (capacity ⊤) | for · dvt · is_disabled | yes |
| **`:1235`** | **`op.tip.tracker.remove_liquid`** | **under-draw** | **yes** | **for · dvt** | **no** |

Exactly one of the four is both decidable *and* outside the `is_disabled` test: `dispense`'s tip-side `remove_liquid` at `:1235`. The `is_disabled` fail-closed rule costs the family **precisely one** decidable guard (`:1034`), and blocks two guards (`:1234`, and `:1034`'s mirror direction) that §14.2 already proves are permanently `½`. So the honest accounting of A-TRACKER-ENABLED's precision cost is not "no definite verdict anywhere"; it is "no definite verdict on a *well*; a definite verdict on a *tip* survives".

That leaves one entry standing between `:1235` and a `WILL_FAIL`: the `for` header.

### The exact syntactic condition under which the `for` header may soundly be admitted

**Position: (i) is admissible, and it is not a hypothesis at all.** It should be recognised *structurally*, independently of `env`, under this condition and no wider:

> A `caller_scope` entry is recognised as satisfied, independently of `env`, **iff it is the very `ast.For` statement B1 used to bind `<name>` for this guard**, identified by **position containment** — the entry's recorded `lineno`/`end_lineno` bracket the `dropped_calls` entry's own `lineno` — not by reconstructed text. Every other `ast.For`, every `ast.While`, every `ast.AsyncFor`, and every `ast.For` whose target is a tuple (B1 already binds nothing there) stays unrecognised.

Three mechanical conjuncts make this sound, none of which is an assumption:

1. **The analyzer already models this loop.** §14.5's V2 says the pairs of V0's list are "applied one at a time, in list order, to a running state … mirroring PLR's own `for op in aspirations`". That sentence *is* an unrolling of `:1031`. B1 binds `op → SingleChannelAspiration` over that same loop. Recognising the header asserts nothing V2 has not already computed; refusing to recognise it means the analyzer fails closed on the one control-flow construct it is simultaneously claiming to simulate exactly.
2. **The trip count is pinned by PLR itself, not assumed.** Every zip input is normalised to `len(use_channels)` at `liquid_handler.py:962-965` (`offsets`, `flow_rates`, `liquid_height`, `blow_out_air_volume`), `:974` (`tips`), `:999` (`resources` on the single-resource spread path) and `:1026` (`mix`), and PLR then **raises `ValueError` at `:989-992`** if `resources`, `vols`, `offsets`, `flow_rates`, `liquid_height` or `blow_out_air_volume` disagrees with `len(use_channels)`. So on every path that reaches `:1031`, `len(aspirations) == len(resources) == len(vols)` — which is the length V0 already requires of `cells(op)`/`amounts(op)`. The loop cannot execute fewer times than the pair list has pairs.
3. **Fail-closed is preserved at the only point it could leak.** If V0 does not apply, V3 widens and no definite verdict exists regardless; R1 can therefore never convert an unknown pairing into a definite verdict. And R1 recognises a *node*, not a shape: a second `for` in the same method, or a `while`, or any loop B1 did not bind over, remains an unrecognised entry and blocks `WILL_FAIL`.

Contrast the other two entries, which is what shows R1 is a boundary and not a slope. `if does_volume_tracking()` reads a module global (`volume_tracker.py:13-22`) the analyzer cannot see — that is a genuine hypothesis and `env` is the right instrument. `if not op.resource.tracker.is_disabled` reads a per-instance flag (`volume_tracker.py:54-56`, `@property` over `self._is_disabled`, initialised `False` at `:46`, set only by `disable()` at `:58-60`) — that needs per-instance knowledge and stays fail-closed.

### On the mandate's (ii): could `is_disabled` be discharged instead of blocked?

**No, and it should not be attempted.** The two candidate discharges both fail:

- *A second `env` hypothesis.* `does_volume_tracking()` is a module-level zero-argument function whose value is a single global; `is_disabled` is one flag per `VolumeTracker` instance, and a deck carries one tracker per well plus one per tip (`container.py:85`, `tip.py:45`). There is no single observation the harness can take that stands for "every tracker relevant to this guard was enabled". A single `env` member would be a quantified claim dressed as an observation — the precise failure §0 exists to prevent.
- *"No `.disable()` / `no_volume_tracking` appears in the program under analysis."* This is sound only if the analyzed graph is the *whole* world. It is not: for a corpus row the graph is an extracted protocol, and the deck construction that instantiates every tracker is code the analyzer never sees. A tracker can arrive disabled from outside the graph. This is exactly the "what breaks if it is false" column of A-TRACKER-ENABLED, and adopting it would re-introduce the assumption the row forbids.

So (ii) stays fail-closed. Per the table above, that costs the family `:1034` and nothing else that was decidable.

### On the mandate's (iii): polarity

**If the recognition set grows, P10 must carry polarity — this is not optional and I concede it in full under O7.** The instant `if does_volume_tracking()` can be *recognised as satisfied*, an `orelse` enclosure recorded as if it were the positive branch becomes an unblocked `WILL_FAIL` on a site that runs only when the hypothesis is false. The challenger's site is real: `dispense96` at `liquid_handler.py:1932-1935` puts `tip.tracker.remove_liquid` under `if does_volume_tracking():` at `:1933` **and** under its `elif` at `:1935`. See O7 for the disposition and for my Q3 position, which is survey-side and for a stronger reason than the challenger gives.

### What this costs the document — conceded, precisely

**REJECTED:** "there is no fixture, mutant, or `env` value that removes the blockage"; "`WILL_FAIL` is unreachable on every tier"; "the sprint gate as stated cannot be met". With R1 admitted, `dispense`'s `op.tip.tracker.remove_liquid` (`:1235`) has `caller_scope` = [ the B1-bound `for` (structural) · `if does_volume_tracking()` (`env`) ] and is fully recognised. A harness fixture — `pick_up_tips` → `aspirate(vols=[50])` → `dispense(vols=[60])` — drives a static `WILL_FAIL` at `PlrSite(volume_tracker.py, 92, "VolumeTracker.remove_liquid")` under `env = {"does_volume_tracking"}`, and the execution raises `TooLittleLiquidError` at `liquid_handler.py:1235`. That is the gate as the orchestrator stated it, met by a mechanism.

**CONCEDED, blocking:** the increment's headline deliverable moves from *the well* to *the tip*, and four ACs are written against the blocked path:

- **AC-14.5(a)** (seed 100, `aspirate(vols=[200])` → `WILL_FAIL`) — unsatisfiable. Rewrite onto `pick_up_tips`/`aspirate(50)`/`dispense(60)`.
- **AC-14.5(b)/(c)** — survive on either path; (b)'s `SAFE` is unaffected by §14.6 in both directions.
- **AC-14.6** (two-channel one-well `aspirate`) — the **static** half survives only against a *synthetic* contract table; the **executed** half is unsatisfiable, because the two channels of a `dispense` touch two distinct tip cells and the one-cell-touched-twice shape exists at this pin only on `aspirate`'s well, which is blocked. See O14: `_verdict_at` joins on `(op, iteration)` anyway (`region_oracle.py:344-351`), so the executed half had no pair-discrimination to begin with.
- **AC-14.7** — survives; its premise (a non-default `env` yields `WILL_FAIL`) is now true on the dispense fixture.
- **AC-14.10** — the four tier-2b fixtures must be re-specified as tip-cell over-draws. All four shapes remain expressible: straight-line (aspirate 50, dispense 60), second-iteration (loop dispensing 30 from a tip holding 50), collective exhaustion (loop dispensing 20 from a tip holding 50 — fires at iteration 3), and — for the two-channel case — nothing. That one is withdrawn as an *executed* criterion.

**Also conceded:** §14.0.2's single measured expectation must become **four**, one per bridged guard, with the `is_disabled` entry present for `:1034`/`:1234` and absent for `:1035`/`:1235`. A fixer publishing one shared scope publishes a wrong one, exactly as the challenger says.

---

## O2 — BLOCKER as filed — **CONCEDED in full. And the resolution the challenger frames as a three-way choice has a determinate answer that also fixes §14.11.**

Verified. `Tip` is `@dataclass` (`tip.py:11-12`) with no `__init__`; `self.tracker = VolumeTracker(...)` is at `:45`, inside `__post_init__` (`:32`). `_constructor_state` — the precedent P1c is "modelled directly on" — scans `ast.iter_child_nodes` for `member.name == "__init__"` and **`return None`** when none is found (`receiver_state.py:563-569`). A literal P1c returns nothing for `Tip`. §14.2's own tip-cell bullet says `__post_init__`; §14.0.1 says `__init__`. The document contradicts itself and the `__init__` reading is the one that ships.

The consequences are as filed and, after O1, worse than the challenger states: without `Tip.tracker → VolumeTracker` the tip cell does not exist, and after O1 **the entire headline deliverable is the tip cell**. This is now the first blocker in the chain, not the second.

**The mandate asks what P1c should key on. The answer is: every method of the class, and the fail-closed rule gets stronger rather than weaker under the wider scan.** Three reasons:

1. Widening the *scan* widens the *evidence the fail-closed rule sees*. P1c's rule is "a name written more than once with two different constructors, or written both by a constructor call and by something else, records nothing". Scanning only `__init__` hides a contradicting write in another method and records a fact the wider scan would refuse. The narrow scan is the *less* safe one.
2. It is the only reading under which §14.11's argument is true. The challenger is right that "`self.x = C()` is a Python language construct, not a PLR idiom" holds only for the all-methods form; `{__init__}` or `{__init__, __post_init__}` is a bet on which method PLR writes trackers in, and PLR demonstrably writes them in two.
3. **It is free at this pin.** Grepping `self\.tracker\s*=` over the whole submodule returns exactly three writes, in three different classes, one each: `container.py:85` (`Container.__init__`), `tip.py:45` (`Tip.__post_init__`), `tip_rack.py:52` (`TipSpot`, `TipTracker`). No class writes `tracker` twice. `Container.__init__` also calls `self.tracker.register_callback(...)` at `container.py:88`, which is a method call *on* the attribute and not a write, so P1c's "written by something else" clause is not triggered. Both measured expectations in §14.0.1's P1c box are satisfied by the all-methods form and by no narrower one.

**Minimum addition:** replace "locates a class's own `__init__` … walks the same `__init__`" with "walks every `ast.FunctionDef`/`ast.AsyncFunctionDef` child of the `ClassDef`", keep the fail-closed clause verbatim (it now ranges over the union of writes), keep the `_constructor_state` citation as the *architectural* precedent for reading `ast.Assign` alongside `ast.AnnAssign` while stating explicitly that P1c does **not** inherit its `__init__` restriction, and re-make §14.11's HM-25 argument against the all-methods form — which is the form that argument was already written for.

---

## O3 — BLOCKER as filed — **CONCEDED. The remedy is the shipped precedent, it stays green, and it still gates the three strings that matter.**

Verified mechanically. Grepping `plr-sema/src/plr_sema` for the two contested literals:

- `"resources"` — `check/ir.py:320` (`"resources": "I"`), `check/ir.py:446` (`payload.get("resources") or {}`), `check/graph.py:193` (`payload.get("resources", {})`).
- `"op"` — `check/ir.py:860, 872, 879, 881, 883, 885, 887` (the opcode tag in `instruction_to_json`'s canonical serialisation, which `bytecode_hash`/`cache_key` are computed over).

AC-14.2(iii) as written is red on an unmodified tree, before a line of increment-5 code exists. Conceded, and the challenger's severity is right: an unrunnable anti-hand-typing gate leaves §14.11's whole table unenforced.

**The remedy is not an invention and does not defeat the gate.** The precedent AC-14.2(iii) generalises is already module-scoped in shipped code — `_channel_default_idiom`'s docstring: "AC-10.9/AC-13.15(iii)'s AST literal scan forbids spelling it as a string constant **anywhere in this module or `plr_sema.check.tipstate`**" (`receiver_state.py:303-306`). Scope AC-14.2(iii) the same way: `plr_sema/derive/receiver_state.py` plus the new `plr_sema/check/volumestate.py`. Answering the challenger's closing question directly — **yes, the narrowed scan still forbids all three of `"tracker"`, `"op"` and `"resources"`**, because the grep above finds `"op"` and `"resources"` only in `check/ir.py` and `check/graph.py`, neither of which is in the volume family's scope, and finds `"tracker"` nowhere in `src/`. The gate keeps every bit of its content and becomes runnable.

---

## O4 — BLOCKER (soundness) as filed — **CONCEDED. A live false `SAFE`, and after O1 it sits directly on the headline path.**

Verified end to end.

- `drop_tips`'s own guard is `if tip.tracker.get_used_volume() > 0 and not allow_nonzero_volume: raise RuntimeError` (`liquid_handler.py:656-657`). With `allow_nonzero_volume=True` the step is legal PLR, so the counterexample is not contrived.
- `drop_tips`/`pick_up_tips` carry no volume bridge, and V2's "cells outside `cells(op)` are unchanged" plus V3's two widen conditions ("a volume bridge only at depth > 0", "two depth-0 bridges disagree in direction") cover neither. Nothing in §14.3, §14.5 or §14.7 touches a tip cell across a tip change.
- A freshly picked `Tip` is a distinct object with a fresh `VolumeTracker` at `tip.py:45`, whose `pending_volume` is `initial_volume or 0` = 0 (`volume_tracker.py:49-50`). So after the retip the real used volume is 0, `dispense(50)` reaches `op.tip.tracker.remove_liquid(50)` at `liquid_handler.py:1235`, and `50 - 0 > 1e-6` raises `TooLittleLiquidError`, while a channel-keyed cell still holding `[50,50]` evaluates `a - lo = 0 ≤ 1e-6` → `F` → `SAFE`.

A-TIP-CELL is written entirely about the "analyzer knows it doesn't know" direction and does not cover "analyzer thinks it knows and is wrong". Conceded as filed. **And this is now the most urgent concession in the report**, because under O1 the tip cell is the only cell that produces a definite verdict, so O4's false `SAFE` is not a corner — it is on the main path.

**The mandate asks what transfer function `drop_tips`/`pick_up_tips` must carry. Neither of the two simple answers works, and the reason is worth stating because it constrains the fix:**

- *`TOP` on every `HAS_TIP` transition* is sound and **destroys the family**. With the cell `TOP = [0, +inf]` at pickup, `aspirate(50)` gives `[50, +inf]`, and `dispense(60)` evaluates `a - hi = 60 - inf`, not `T`, and `a - lo = 10 > 1e-6`, not `F` — `½` forever. Every over-draw becomes `UNKNOWN` and the increment ships no `WILL_FAIL` after all.
- *`[0,0]` on every `HAS_TIP` transition* is exactly the unsound rule O4 exhibits.

**The rule that is both sound and precise enough is program-local and monotone:**

> A `pick_up_tips` sets the cell `("tip", c)` for every bound channel `c` to `[0,0]` **iff** no prior operation in the walk has made the tip population dirty, and to `TOP` otherwise. A `drop_tips`/`discard_tips` sets `("tip", c)` to `TOP` for every bound channel and, **iff** the departing cell's interval is not provably `[0,0]` (i.e. `hi > 0`, or the cell is `TOP`), sets a monotone walk-level `tips_dirty` flag. Any operation that moves tips without a modelled tip effect — `move_resource`/`move_plate` over a tip rack, `stamp`, any 96-head operation, and any operation whose bound channels are `⊤` — sets `tips_dirty` unconditionally.

Under the counterexample: aspirate → `[50,50]`; `drop_tips(allow_nonzero_volume=True)` → `hi = 50 > 0` → `tips_dirty`; `pick_up_tips` → `TOP`; `dispense(50)` → `½` `UNKNOWN`. Sound. Under the ordinary protocol (pick up, aspirate 100, dispense 100, drop empty, pick up again) the departing cell is provably `[0,0]`, `tips_dirty` stays false, and the family keeps full precision across arbitrarily many retips. The rule needs its own assumption row and its own executed fixture — a retip fixture, which no AC currently has.

---

## O5 — MAJOR as filed — **PARTIAL. The window is CONCEDED. The challenger's tier-2b ordering claim is factually wrong, and correcting it changes what the remedy is.**

**Conceded:** there is no "after the verifier establishes its configuration" window. `training/verify/verifier.py` sets `set_volume_tracking(True)` at `:114` inside a `try` and restores `old_volume_tracking` in the `finally` at `:151`. `training/tests/test_verify_postconditions.py:76-85` pins exactly this (`assert does_volume_tracking() is False` after a run). In tier 3, `run_one_mutant` calls `oc.run_runtime(mutant)` at `tip_mutants.py:178` and `oc.run_static_calls(...)` at `:188`; an observation between them returns `False` (the module default at `volume_tracker.py:14`), `env` stays empty, and every volume guard is `volume_tracking_unasserted`. §14.6's third paragraph is wrong as written and AC-14.9's v1 count would be 0 for a reason unrelated to the interval domain. This is a real defect.

**Corrected:** the challenger writes that in tier 2b "`_static_report` (`:354-366`) runs before `_run_fixture_execution` (`:398`)". Those are *definition* line numbers. The per-fixture call order is the opposite: `_run_fixture_execution` at `region_oracle.py:516`, `_static_report` at `:527`. So the leaked flag — `set_volume_tracking(True)` at `:414` with a `finally` at `:436-437` that restores strictness only — **is** observable at the point the static side runs. The challenger's underlying point survives and is the right one: two harnesses disagree, one of them by accident, and a value the document calls an observed fact is order-dependent and would silently partition `cache_key` (`ir.py:953`).

**Minimum addition, and it is small:** stop observing a process global from outside the window. Have the executed side *return* the observation. `training/verify/verifier.py` gains one additive result key set between `:114` and `:129` from a call to the imported `does_volume_tracking` callable; `region_oracle._run_fixture_execution` gains the same inside its `try`. The harness reads `env` from that field. This preserves §14.11's "no string typed" property intact — the name still comes from the callable's `__name__` on one side and the guard's own `caller_scope` on the other — and it removes the order dependence rather than documenting it.

**On the `check_graph` sub-point — REJECTED as a contradiction, CONCEDED as under-specification.** §14.6 says "`check_graph`'s two-positional-argument signature does not change". Adding a keyword-only `env` does not change a two-positional signature, and the precedent is in the same signature at `check/__init__.py:714-719`, where `#4922` added `cache: CacheStore | None = None` keyword-only for exactly this reason. So the spec is *compatible* with `check_graph` gaining `env=`, and that is plainly what the AC fixtures need. It should say so in one clause rather than leaving a fixer to infer it.

---

## O6 — MAJOR as filed — **CONCEDED. Both halves verified; the correction is textual and the scoping consequence is real.**

`cache_key` at `check/ir.py:918-953` already takes `env: frozenset[str] = frozenset()` keyword-only and already returns a five-tuple ending in `tuple(sorted(env))`. Its own docstring at `:934-944` says so and explains it defaults empty "because the volume family (its only producer) is deferred out of this increment (#4922) … until a later increment threads a real `env` through `check_ir`/`check_graph`". §14.14(6)'s "this increment adds the component" is stale, and its "invalidates every entry written before it" is false in both directions exactly as filed: today's entries have fifth component `()`, a default-`env` run reproduces it identically (nothing invalidated), and a non-default run *partitions* rather than invalidates.

The duplication risk is real and the document does specify the wrong work. **The work that actually remains is the threading**, and it is one call site: `check/__init__.py:766` reads `key = ir.cache_key(bc_hash, contracts_json, stamp)` with no `env=`. T27's scope should read: thread `env` from `check_graph` → `check_ir` → the `cache_key(...)` call at `check/__init__.py:766`, and through `CacheStore`'s lookup; **do not add a component to `cache_key`, it has one**. That is materially less than ~200 LOC and the estimate should move with it.

---

## O7 — MAJOR as filed — **CONCEDED on polarity. Q3 CONCEDED survey-side, and the decisive reason is one the challenger did not give.**

**Polarity, conceded without reservation, and O1 is what makes it urgent.** The survey's `visit_If` pushes `f"if {test_src}"` for the body at `survey_plr_preconditions.py:167` and `f"else of: if {test_src}"` for the `orelse` at `:177`, with the comment at `:172-176` explaining that an `elif` chain self-nests and compounds correctly. P10's box records only "enclosing `ast.If` test sources". The live PLR shape is real: `dispense96` at `liquid_handler.py:1932-1935` has `tip.tracker.remove_liquid` at `:1933` under `if does_volume_tracking():` and again at `:1935` under its `elif` — the second runs only when tracking is **off**. While §14.6 recognised nothing, this was harmless; the moment `if does_volume_tracking()` is recognisable under `env`, a polarity-blind P10 emits an unblocked `WILL_FAIL` on a site that executes only when the hypothesis is false. The challenger is also right that it is masked at this pin by luck (two textual occurrences → `caller_scope: null`) rather than by design, and right that A-SCOPE-TEXT's discharge argument addresses call *identity* and not branch *polarity*.

**Q3: survey-side. I concede the decision and I will give the argument that actually settles it, because the challenger's cost comparison is not it.** O1's recognition rule (R1) requires that the recognised entry be *the `ast.For` node B1 bound over*, not a `for` header that looks like it. Under the derive-side option the entry is a reconstructed string and the identity test is a text match — which re-introduces a text key at the precise point soundness now depends on it, and A-SCOPE-TEXT is not written to discharge that. Under the survey-side option the entry carries a `lineno`, and the derive side — which already holds B1's `ast.For` node — can test `for_node.lineno <= call_lineno <= for_node.end_lineno`. That is **position containment**, which is the strong key §14.0.2 itself concedes the survey-side option has and prices as unaffordable. It is not unaffordable; it is the enabling condition for the mechanism that rescues the increment.

Three supporting facts, all verified: the change is at one existing site (`survey_plr_preconditions.py:250`) where `self._scope_trail` is already live (`:135`) and where `_record` already builds the same three-tuple for findings (`:157-160`); the trail already handles `for` headers in the exact form P10 wants (`visit_For` at `:182-189`) and already fixes a nearest-first convention (`insert(0, …)`) that P10's outermost-first declaration and §14.0.2's own measured expectation each contradict differently; and `self.dropped` is `set[str]` (`:142`), so preserving multiplicity requires touching that declaration anyway. I add one more: **survey-side is also cheaper on the registry.** `visit_If`/`visit_For` already exist and are already accounted for; a derive-side P10 re-implements them and, per O12's own criterion, adds a pattern with a silent failure mode to a registry at zero headroom.

**Consequence for the document:** §14.0.2's option table, its "Decision: derive-side" box, P10's normative box, A-SCOPE-TEXT and §14.15's "not in this increment" bullet all invert. §14.14 gains an item for the survey schema change. The `caller_scope`/`scope_trail` ordering conflict AC-14.3(ii) glosses over disappears, because both then use the survey's one convention.

---

## O8 — MAJOR as filed — **PARTIAL. Point (2) is REJECTED outright on the module's own docstring; point (1)'s "no mechanism" is REJECTED with the shipped lowering path; point (3) is CONCEDED, and the finding it names is not the one the challenger predicted.**

**(2) REJECTED.** "`VolumeTracker` is not a supported tool … an operation whose receiver is outside the analyzed surface yields `unsupported_tool`" was true before 260901 T11 and is false now. `check/_supported_tools.py:5-21` states it in terms: "**No longer the analyzed-surface boundary (260901 T11).** … `plr_sema.check`'s `unsupported_tool` reason now means 'key absent from that whole-survey contract table', not 'not in this frozenset'". `check/__init__.py:346-348` and `:363-366` implement exactly that — one contract-table lookup, no `SUPPORTED_TOOLS` test. And `"VolumeTracker.set_volume"` **is** a key in the shipped table, at `plr-sema/data/derived_contracts.json:158185`. The seed `CALL` does not produce `unsupported_tool`.

**(1) REJECTED as "no mechanism", CONCEDED as loose phrasing.** `lower_calls` accepts per-call `receiver`/`receiver_type` overrides — `receiver_name = call.get("receiver", "lh")` and `receiver_type = call.get("receiver_type", "LiquidHandler")` at `check/ir.py:794-795`, documented as "a strict superset" at `:764-766`. And `Call.receiver` is an **`int`** (`ir.py:201`) assigned by `get_slot(receiver_name)` at `:818`, where `get_slot` (`:784-787`) mints a slot per name in first-appearance order. So the seed `CALL` is expressible today with no wire change and no `IR_VERSION` bump: `{"receiver": <the same resource variable name the protocol's `Ref` uses>, "receiver_type": "VolumeTracker", "method": "set_volume", "kwargs": {"volume": <Lit>}}`. Slot identity between the seed's receiver and the aspirate's `Ref` follows from `get_slot` name identity, which is the property §14.3 is relying on when it says the cell id "reuses the `Ref(slot, cell)` pair". What §14.8 must *not* do is pass the cell as a kwarg: `set_volume`'s trusted params are `["self", "volume"]` (`derived_contracts.json:158193-158196`), so a synthetic cell kwarg falls into the untrusted branch at `ir.py:806-808`, is renamed `?j`, and emits `Widen(_ARGUMENTS)` at `:811-812`. §14.8's phrase "with the cell as receiver" is right in substance and needs to say *which* name, plus one sentence on the `("container", slot, cell)` form when the protocol addresses a well as `plate["A1"]` rather than by its own name.

**(3) CONCEDED, and sharpened.** The challenger predicted a spurious finding and was right that `origin` does not suppress one — but the finding is not the fallback it names. `VolumeTracker.set_volume` carries a real gap in the shipped table: `"gaps": [["unresolved_delegate", "_callback"]]` at `derived_contracts.json:158186-158191` (from `self._callback()` at `volume_tracker.py:71-72`), with `"guards": []`. `_evaluate_call` emits one `_findings_for_gap` finding per gap at `check/__init__.py:372-374`, so the seed `CALL` contributes exactly one `unresolved_delegate` finding — and never reaches the zero-guards/zero-gaps fallback at `:383-392`. In defense of the AC: "exactly one `Finding` with `verdict is Verdict.WILL_FAIL`" admits the reading "exactly one `WILL_FAIL` finding among however many", under which it passes. But both readings are natural, this is precisely the "two equally reasonable interpretations" case, and a one-word disambiguation costs nothing. §14.8's closing claim that the seed reuses increment 3's precedent should also note that the `setup()` precedent's receiver is `LiquidHandler` and this one's is not — the challenger is right that that is a new fact, even though it is a benign one after T11.

---

## O9 — MAJOR as filed — **PARTIAL. The non-sequitur is CONCEDED. The scope question is CONCEDED as unstated, and it has a resolution that makes AC-14.1(iii) true by construction instead of by coincidence.**

**Mechanism, conceded.** `_annotated_attributes` (`receiver_state.py:173-184`) iterates `ast.walk(class_node)` — breadth-first — and writes with `out.setdefault(...)` at `:183`, i.e. first-writer-wins. A class-level `AnnAssign` is a depth-1 child of the `ClassDef`; a method-body `self.x: T` is deeper. On any name collision the new B2 branch is visited first and **displaces** the existing selection. "Disjoint predicate" therefore does not entail "unaffected"; the "so" in the B2 box is a non-sequitur, and stating a guarantee structurally while asking the fixer to measure it is the wrong shape for §13.2.4's own discipline.

**Empirically safe at this pin, confirmed independently.** Grepping the whole submodule for a class-level annotation typed to `TipTracker` or `VolumeTracker` returns **zero** matches, so no existing selection can be displaced by B2 today and AC-14.1(iii) will pass. That is why this is not a blocker.

**The scope question is the part a fixer gets wrong, and the document should answer it the other way from the challenger's "natural reading".** `derive_receiver_states` calls `_annotated_attributes(receiver_node)` at `receiver_state.py:720`, iterates `sorted(annotated)` at `:724`, and `break`s on the first qualifying attribute at `:785` — with the comment at `:721-723` flagging the alphabetical tie-break as load-bearing (`"head" < "head96"`). **Recommend: B2 and P1c feed a separate, bridge-only map and do not touch the map consumed at `:720` at all.** Nothing in the volume family needs the receiver-selection loop — the bridge needs to type `SingleChannelAspiration.resource` and `Container.tracker`, and neither is a channel attribute of a receiver class. Under that resolution AC-14.1(iii) is true by construction, `derived_contracts.json`'s `receiver_state` block is byte-identical by definition rather than by an alphabetical accident, the BFS/`setdefault` hazard never arises, and §14.4's "P1a-as-extended-by-B2" / "P1a **or** P1c" phrasings must be rewritten to name the bridge map explicitly. The B2 box's guarantee then becomes a fact about which function is called, not a prediction about a shared dict.

---

## O10 — MAJOR as filed — **PARTIAL. The under-determination is real; the remedy makes V2 *more* derived, not less, and closes it permanently rather than tie-breaking it.**

Verified: `VolumeTracker` has two methods raising `TooLittleLiquidError` from an `ast.Compare` over `get_used_volume()` and one of the method's own parameters — `remove_liquid` (`volume_tracker.py:88-99`, guard `:91`, raise `:92`) and the deprecated `get_liquids` (`:122-138`, guard `:135`, raise `:136`). `VolumeTracker.get_liquids` is a real contract entry (`derived_contracts.json:158054`). The challenger is right that P7 survives (both name the same accessor, so the "≥2 candidate used-volume accessors" clause does not fire) and right that V2's singular "P7's `TooLittleLiquidError`-guarded method" has no tie-break.

In partial defense: read as a *predicate on the bridged method* rather than as a definite description selecting one method per class, V2 is determinate, and nothing at this pin bridges `get_liquids` (the bridge shape is four dotted segments and no `dropped_calls` entry of that shape names it). So the objection is latent, as the challenger says.

**But there is a better fix available than a tie-break, and it removes the latency instead of documenting it.** The direction is *directly derivable* from the anchored field's own write: `remove_liquid` writes `self.pending_volume -= volume` (`volume_tracker.py:96`), `add_liquid` writes `self.pending_volume += volume` (`:109`), and `get_liquids` writes nothing at all. So:

> **The direction of a bridged method `C.m` is the sign of `m`'s `ast.AugAssign` on `C`'s P7-anchored field** — `ast.Sub` decreasing, `ast.Add` increasing. A bridged method with no write to the anchored field, or with two writes of different signs, carries its **guard** but **no transfer** and is fail-closed for V2.

This is one sentence, it is fully derived (nothing typed), it classifies `get_liquids` correctly *as a pure read* rather than by excluding it by name, it survives the deprecation removal the challenger worries about, and it deletes the "which method is which" row's exposure in §14.11's table rather than qualifying it.

---

## O11 — MAJOR as filed — **CONCEDED. Verified in full; v2 has no static side.**

`LiquidHandler.transfer` (`liquid_handler.py:1273-1361`) contains no `ast.ListComp`/`GeneratorExp` over a `zip` of names, so P8 does not match; no `for` over a comprehension's output, so B1 binds nothing; and no four-segment `<name>.<field>.<attr>.<method>` call, so the volume bridge never fires. It reaches the trackers only through `await self.aspirate(...)` at `:1347` and `await self.dispense(...)` at `:1355`, and what it passes is computed — `vols=[sum(target_vols)]` at `:1349`, `target_vols = [source_vol * r / sum(ratios) for r in ratios]` at `:1345`, `vols=[vol]` at `:1357` over the `zip` at `:1354`. §14.5 V0 requires `amounts(op)` to be a `Seq` of numeric `Lit`s; none of these is. And nothing in §14.0, §14.4 or §14.5 specifies volume-guard propagation through `delegates_to` — the bridge box attaches guards to `K`, the entry whose own `dropped_calls` carried the expression. The challenger's distinction between #4946's *channel* binding (`delegate_channel_binding.transfer.{aspirate,dispense}`) and a *volume* one is correct; they are different mechanisms.

So AC-14.9's v2 cannot fail, and §14.9's own closing paragraph — "a class whose gate can only ever be `0 of n` measures the spec's own scope decision rather than the implementation", written to justify declining an over-fill mutant class — applies to v2 verbatim and is not applied. **Recommend v2 be withdrawn**, T28 re-sized accordingly, and §14.16 Q5 resolved by the withdrawal rather than left open. If it is retained, §14.4 must first specify volume-guard propagation through `delegates_to` as a normative box with its own measured expectation, which is a fifth unproved derivation in an increment already carrying four.

---

## O12 — MINOR as filed — **PARTIAL. The count is conceded; the instrument is not, and the challenger's own criterion is what decides it.**

Verified: HM-25 `declared=6` at `_hand_maintained.py:842`, its `what` enumerating exactly six at `:825-840` including P9; HM-24 `declared=1` at `:802` with `_measure_hm24` asserting `_BRIDGE_SHAPE_RE.groups == 3` at `:257-260`. §14.11's entry condition is right and "No objection to HM-24 1→2" is right.

**Conceded:** B1 is a pattern by HM-25's own `breaks_when` test. `for i, op in enumerate(aspirations):` is idiomatic Python PLR could adopt tomorrow, and B1's fail-closed rule ("the `ast.For` target is a tuple rather than a single `ast.Name` … B1 binds nothing") would silently disable the family. §14.11's counterargument ("what they match is a *binding*, resolved by Python's own scoping rules") is not true of B1 as specified, which matches a shape. And after O1 the argument is weaker still, because R1 makes B1's `ast.For` node load-bearing for *soundness*, not only for precision.

**Rejected: "≥9 on HM-25".** The challenger identifies the right criterion and then applies it to the wrong row. The 260902 Q7 split is explicit in the registry: HM-24 is the pattern "whose failure mode is a SILENT family collapse rather than a loud exact-count test failure" (`_hand_maintained.py:796-799`, and `breaks_when` at `:810-820`: "Fails CLOSED … the tip-requiring/tip-loading families silently empty … it cannot produce a wrong verdict, only fewer of them"); HM-25's `breaks_when` says "Fails LOUDLY here (unlike HM-24)" (`:857-861`). B1's failure mode is a silent family collapse. So B1 belongs on **HM-24**, not HM-25. The correct arithmetic is:

- **HM-24 `declared` 1 → 3** — the volume bridge shape and B1 — with `_measure_hm24` returning 3 and each new pattern asserted the way the existing one is.
- **HM-25 `declared` 6 → 8** — P7's accessor-anchor shape and P8's zip-comprehension idiom — unchanged from §14.11.
- **P10 drops out of the registry entirely under Q3's survey-side resolution** (O7): the survey's `visit_If`/`visit_For` already exist and adding a `lineno` and a trail to an existing record adds no pattern.

Eleven patterns over two rows, no row addition, no cap conversation, `live_rows()` unchanged at 24 against `BUDGET_CAP = 24` (`_hand_maintained.py:43`). §14.16 Q2's own instinct — a split rather than a ceiling bump — is right, and the split it wants already exists; the document just filed B1 on the wrong side of it. §14.11's "B1 and P10 are closer to the line … but what they match is a *binding*" paragraph should be replaced with the silent-versus-loud test and the row reassignment.

---

## O13 — MINOR as filed — **CONCEDED, all three parts, with corrections in both directions.**

**(a) Stale scheduling text.** Conceded as listed. Line 716's "**Every row in this table is unscheduled**" sits immediately under line 714's "**scheduled: next sprint (user decision 260903)**"; the frontmatter `description`'s "NOT SCHEDULED", the `title`'s "deferred out of increment 4", line 16-17's "`draft-deferred`: nothing in it is scheduled", §14.0's heading, §14.12's preamble and the References/changelog's "This document has had no adversarial round of its own" (×2) are all now false. The last of those is falsified by this report and its counterpart.

**(b) T29 is already satisfied except for one rename.** Verified: `SPEC_INCREMENT_5` is defined at `plr-sema/tests/test_spec_lint.py:36` and parametrised into both live-spec tests at `:220` and `:243`. What remains is the stale parametrise id, `increment-5-volume-deferred`, at both sites, and the `INDEX.md` regeneration. T29's ~15 LOC is ~2.

**(c) Citation drift — conceded, with two corrections.** I re-derived every line number from `cat -n` output and my numbers differ from the challenger's by one on three of them; the challenger's direction is right in every case and only the exact target differs. Against the current tree:

| spec cites | challenger says | verified |
|---|---|---|
| `_is_self_attr` `:164-167` | `:166-169` | **`:167-170`** |
| `_annotated_attributes` `:170-181`, `AnnAssign` test `:177` | `:172-183`, `:179` | **`:173-184`, test at `:180`** |
| `_constructor_state` `:523-563`, "locates `__init__` (`:540-545`)" | `:546-586`; `:540-545` in `reset_rule_candidates` | **`:547-587`**; `:540-545` is inside `reset_rule_candidates` (def at `:496`) — the challenger's diagnosis is exactly right, the fixer is pointed at the wrong pass |
| "walks `ast.Assign` (`:548`) / `ast.AnnAssign` (`:551`)" | `:571`/`:574`, docstring lines | **`:572`/`:575`**; `:548`/`:551` are docstring lines |
| `compute_channel_bridge` "the copy at `:787`" | `:1041` | **`:1042`** — the sole `scope_trail` occurrence in the file; `:789-794` is the P9 section comment |
| `live_rows()` `:851-855` | `:867-871` | **`:867-871`** |
| HM-24 row `:781-814`, fields `:793-795` | `:788-822`, `:801-803` | **`:788-822`, `:801-803`** |
| HM-25 row `:815-847`, fields `:828-830` | `:823-863`, `:841-843` | **`:823-863`, `:841-843`**; `:828-830` lands inside the `what` string's prose |
| `SingleChannelDispense` mirror `standard.py:63-67` | class is `:63-72`, `volume` at `:68` | **confirmed** — `:63-72`, `volume: float` at `:68` |

Two things in the document's favour that the challenger did not credit: `SingleChannelAspiration`'s citations are **exact** (`resource: Container` at `standard.py:53`, `tip: Tip` at `:55`, `volume: float` at `:56`), and so are `verdict.py:129-154` for `REASON_VOCABULARY`, `_hand_maintained.py:43` for `BUDGET_CAP = 24`, `check/ir.py:184-191` for `Resource`'s seven operands, `check/__init__.py:713` for `check_graph`, and `container.py:84-85`, `tip.py:27,45`, `volume_tracker.py:14,21-22,25-30,49-50,54-56,66-72,88-99,101-112,114-116,118-120,135-136,140-151` throughout §14.1/§14.2/§14.6. The drift is concentrated in one file, `derive/receiver_state.py`, and in the registry rows — which is consistent with those two having moved under #4922/#4946 after the citations were written.

**AC-14.11 is a prediction, not a fact, and I could not convert it.** With no Bash tool I cannot run `uv run pytest plr-sema/tests/test_spec_lint.py -q`. The `:828-830` case (a range with no matching symbol) is the most likely to fire the citation lint. This goes on the remediation list as an item requiring execution, not judgement.

---

## O14 — MINOR as filed — **PARTIAL. AC-14.6's executed half is CONCEDED inert, and O1 makes it worse than the challenger says. The publish-only observation is CONCEDED. Nothing here is rejected.**

Verified: `_verdict_at` returns `join_fn(tuple(per_iter[iteration]))` or, failing that, `join_fn(tuple(per_iter[None]))` (`region_oracle.py:344-351`). Both pairs of one `aspirate` are the same operation at the same iteration, so the comparison key has no pair dimension and a `SAFE`+`WILL_FAIL` pair joins to one verdict. The executed half of AC-14.6 adds a run and no discrimination, while §14.10's soundness table lists it as *the* oracle for "checked sequentially, not simultaneously".

**And after O1 it is worse:** there is no executed two-channel/one-cell over-draw at this pin at all. The shape requires one cell touched twice within one operation, which exists only on `aspirate`'s well (blocked by `is_disabled`); `dispense`'s two channels touch two distinct tip cells. So AC-14.6's executed half must be withdrawn outright, and its static half must be re-specified against a **synthetic** contract table whose bridged guard carries `caller_scope == ["for op in aspirations", "if does_volume_tracking()"]` — modelling a guard without the `is_disabled` conjunct. That is a legitimate fixture (AC-14.4's four fixtures are synthetic for the same reason) and it retains the full stub-defeating power: a snapshot implementation emits two `SAFE`s and fails.

The publish-only ACs — AC-14.1(ii) and the "complete set … is published" halves of (i)/(iv), AC-14.3(i)'s "published verbatim as produced", AC-14.9's "published against whatever baseline is current" — are conceded as unable to fail. That is defensible for a *measurement* whose value is genuinely not known in advance, and §14.0.1's discipline is explicitly that the fixer must not reconcile a measurement to the document. The gap is that none of them names an *entry condition* (AC-14.8 is the only AC that does, as the challenger notes). Minimum addition: each publish-only clause gains a non-emptiness or a cardinality floor, which is falsifiable without predicting the value.

---

## Defender-identified gaps the challenger did not raise

Both are on the path this defense rescues, so raising them is not generosity.

### D1 — BLOCKER — the tip guard's `cell_param` is a **local** pairing, and V0 has no rule that turns one into a cell id

§14.4's measured expectation for the tip guard reads `cell_param: <the tip local>`, and §14.4's P8 box says a local pairing "is recorded **but not consumed**" — because `tips` is the list built at `liquid_handler.py:974` (`[self.head[channel].get_tip() for channel in use_channels]`), not a parameter of `aspirate`. But §14.5's V0 is written entirely as "let `cells(op)` be the `Value` of `op.kwargs[cell_param]`", and **there is no `tips` kwarg**. §14.3 names the tip form of `CellId` as `("tip", channel)` "keyed on the channel index the tip family already computes (§10.1.3)", but no rule anywhere bridges P8's local pairing to that form. As written, V0 cannot produce a tip cell id for any operation, so the tip guards produce nothing — which is fatal, because after O1 the tip cell carries the entire deliverable.

**Minimum addition, with a shipped mechanism to lean on.** V0 gains a second clause: when the bridge's `<field>` resolves to a *local* pairing whose local is built per-channel, the cell list is `[("tip", c) for c in channels_for_call(op)]`, taken in `use_channels` order to match V2's threading, using the channel binding `plr_sema.check.tipstate.channels_for_call` (`check/tipstate.py:245`) already computes and #4946 already extends. When that binding is `⊤`, V0 does not apply and V3 widens — the existing fail-closed direction. This also gives A-TIP-CELL its actual content, which today is asserted but not mechanised.

### D2 — MINOR — V0's length agreement should extend to a literal `use_channels`

R1's soundness argument (O1, conjunct 2) rests on PLR's own length check at `liquid_handler.py:989-992`. When `use_channels` is present as a literal and its length disagrees with `cells(op)`/`amounts(op)`, PLR raises `ValueError` at `:990` *before* the loop, so the analyzer's pair list describes iterations that never happen. The verdict stays sound (the operation does fail, and no `SAFE` is produced), but the `plr_site` is wrong and a tier-2b `(operation, iteration)` comparison would attribute a raise to the wrong site. One conjunct in V0 — when `use_channels` lowers to a `Seq` of `Lit`s, its length must agree too, else V3 — makes the model match the guard it depends on.

---

## Answering the mandate's settle-list

- **O1 mechanism.** Admit the B1-bound `ast.For` **by node position**, not by text, and only that node. Keep `is_disabled` fail-closed. Net at this pin: `dispense`'s `op.tip.tracker.remove_liquid` (`liquid_handler.py:1235`) is fully recognised under `env = {"does_volume_tracking"}`; the sprint gate is met by a fixture that aspirates 50 into a tip and dispenses 60. Withdrawn: AC-14.5(a) as written, AC-14.6's executed half entirely, AC-14.10's fixture set as written. The headline deliverable becomes **"a definite `WILL_FAIL` on a tip over-draw, and `SAFE`/`UNKNOWN` on every well"** — narrower than §14.0 claims, and firable, which is the premise Q1's resolution rested on.
- **O2 `P1c` key.** Every method of the class. Not `__init__`, not `{__init__, __post_init__}`.
- **O3 scan scope.** `plr_sema/derive/receiver_state.py` + `plr_sema/check/volumestate.py`, per `receiver_state.py:303-306`. Verified green and still gating.
- **O4 transfer functions.** `TOP` on `drop_tips`; `[0,0]` on `pick_up_tips` only while a monotone `tips_dirty` flag is false; `tips_dirty` set by any drop of a not-provably-empty tip and by any unmodelled tip movement.
- **O5 observation window.** Inside the executed window, returned as an additive result field by both `training/verify/verifier.py` (between `:114` and `:129`) and `region_oracle._run_fixture_execution`. And yes — `check_graph` gains a keyword-only `env=`, on the `cache=` precedent at `check/__init__.py:718`.
- **O6 T27.** Thread `env` into the `cache_key` call at `check/__init__.py:766` and through `CacheStore`; do not add a sixth component.
- **O7 / Q3.** Survey-side, because the `lineno` it adds is what lets R1 key on node position instead of text. Polarity is mandatory either way.
- **O8 seed `CALL`.** `receiver_type="VolumeTracker"`, `method="set_volume"`, `receiver` = the resource *name*, seed as the trusted `volume` kwarg. Not `unsupported_tool`; it does emit one `unresolved_delegate` finding from the shipped gap at `derived_contracts.json:158186-158191`.
- **O9 map scope.** A separate bridge-only map; `receiver_state.py:720` untouched.
- **O10 tie-break.** No tie-break — derive the direction from the `ast.AugAssign` sign on the anchored field; no write ⇒ guard without transfer.
- **O11 `transfer`.** No path. Withdraw v2.
- **O12 registry.** HM-24 1 → 3 (bridge + B1), HM-25 6 → 8 (P7 + P8), P10 off-registry under survey-side. Eleven patterns, two rows, no cap move.
- **O13.** Conceded; AC-14.11 needs an actual pytest run, which this agent could not perform.
- **O14.** AC-14.6 executed half withdrawn; static half re-specified against a synthetic contract table; publish-only clauses gain cardinality floors.

---

## Severity table (pre → post)

| id | challenger | disposition | post-defense | fix class |
|---|---|---|---|---|
| O1 | BLOCKER | **PARTIAL** — global claim rejected with R1; 4 ACs conceded | blocking (AC rewrite + R1 normative box) | one normative rule + AC re-siting |
| O2 | BLOCKER | **CONCEDE** | blocking; first in the chain | one-word scope change in P1c |
| O3 | BLOCKER | **CONCEDE** | blocking but trivial | scope the scan per `receiver_state.py:303-306` |
| O4 | BLOCKER | **CONCEDE** | blocking, and on the headline path | two transfer functions + one flag + one fixture |
| O5 | MAJOR | **PARTIAL** — window conceded, ordering corrected | major | additive result field ×2 + `env=` on `check_graph` |
| O6 | MAJOR | **CONCEDE** | minor once T27 is re-scoped | text + one call-site edit |
| O7 | MAJOR | **CONCEDE** (polarity + Q3) | blocking once R1 lands | invert §14.0.2; 3 lines in the survey |
| O8 | MAJOR | **PARTIAL** — (2) rejected, (1) rejected in substance, (3) conceded | minor | name the receiver; disambiguate AC-14.5(a) |
| O9 | MAJOR | **PARTIAL** | minor | separate bridge map; restate the guarantee as measured |
| O10 | MAJOR | **PARTIAL** — better remedy than a tie-break | minor | one derived sentence |
| O11 | MAJOR | **CONCEDE** | major | withdraw v2; re-size T28 |
| O12 | MINOR | **PARTIAL** — count conceded, instrument rejected | minor | HM-24 1→3, HM-25 6→8 |
| O13 | MINOR | **CONCEDE** | minor | text + citations + one pytest run |
| O14 | MINOR | **PARTIAL** | minor | withdraw one AC half; add floors |
| **D1** | — | defender-identified | **blocking** | one V0 clause over `channels_for_call` |
| **D2** | — | defender-identified | minor | one V0 conjunct |

---

## Ordered remediation list

Execute in this order; items 1–6 are the blocking set and 1–3 must land in the spec before T24 is dispatched.

1. **§14.6 — add R1, the structural-satisfaction rule.** A `caller_scope` entry is recognised as satisfied independently of `env` iff it is the `ast.For` statement B1 bound `<name>` over for this guard, identified by position containment (`lineno`/`end_lineno` bracketing the `dropped_calls` entry's `lineno`), never by text. Carry the three-conjunct soundness argument verbatim: V2 already unrolls this loop; `liquid_handler.py:962-965,974,989-992,999,1026` pins the trip count to the pair-list length by PLR's own `ValueError`; V0-not-applying ⇒ V3 widens, so R1 cannot convert an unknown pairing into a definite verdict. State explicitly that `is_disabled` remains unrecognised and why (per-instance; both candidate discharges fail).
2. **§14.0.2 — publish four measured expectations, not one**, one per bridged guard, and correct them by eye against `liquid_handler.py:1031-1035` and `:1231-1235`: `:1034` and `:1234` carry the `is_disabled` entry, `:1035` and `:1235` do not. Add the disposition table from O1 (decidable × blocked) as the increment's own accounting of what §14.6 costs.
3. **§14.0.2 / §14.15 / §14.16 Q3 — invert to survey-side.** `scripts/survey_plr_preconditions.py:250` records `(ast.unparse(target), node.lineno, list(self._scope_trail))`; `self.dropped` at `:142` becomes a list of those tuples; `dropped_calls`'s schema changes and `plr_preconditions.json` is regenerated. P10 becomes a *consumer* of that field, carries the survey's existing `else of: if …` polarity (`:167-180`) and nearest-first ordering (`:187`), and drops out of §14.11's registry arithmetic. Add §14.14 item 8 for the survey schema change. Rewrite A-SCOPE-TEXT: the key is position, not text.
4. **§14.0.1 P1c — scan every method**, not `__init__`. Keep the fail-closed clause verbatim over the union of writes. Note the three writes at `container.py:85`, `tip.py:45`, `tip_rack.py:52` and that none collides within a class. Restate §14.11's language-construct argument against the all-methods form and reconcile §14.2's `__post_init__` sentence with §14.0.1.
5. **§14.3/§14.5 — add the tip-cell lifecycle (O4) and the tip-cell pairing clause (D1).** The lifecycle: `TOP` on drop, `[0,0]` on pickup only while `tips_dirty` is false, `tips_dirty` monotone and set by any drop of a not-provably-empty tip and by any unmodelled tip movement. The pairing: V0's second clause resolving a local pairing to `[("tip", c) for c in channels_for_call(op)]` (`check/tipstate.py:245`), fail-closed to V3 when the binding is `⊤`. Both need a new assumption row; the lifecycle needs a **retip fixture** in AC-14.5 and AC-14.10, which no AC currently has.
6. **§14.12 — re-site the acceptance criteria onto the tip path.** AC-14.5(a) becomes `pick_up_tips`/`aspirate(50)`/`dispense(60)` → `WILL_FAIL` at `PlrSite(volume_tracker.py, 92, "VolumeTracker.remove_liquid")`; AC-14.5(a)'s finding count is disambiguated to "exactly one `WILL_FAIL` finding" and the seed's `unresolved_delegate` finding is named; AC-14.6's executed half is withdrawn and its static half re-specified against a synthetic contract table; AC-14.10's four fixtures become tip over-draws (straight-line, second-iteration, collective-exhaustion, retip) with the two-channel case replaced by the retip case; AC-14.2(iii)'s scan is narrowed to `derive/receiver_state.py` + `check/volumestate.py`; publish-only clauses in AC-14.1(i)/(ii)/(iv), AC-14.3(i) and AC-14.9 gain cardinality floors.
7. **§14.4/§14.5 — the direction rule (O10) and the `use_channels` conjunct (D2).** Direction = the sign of the `ast.AugAssign` on the anchored field (`volume_tracker.py:96`/`:109`); no write ⇒ guard without transfer. V0 gains the literal-`use_channels` length conjunct.
8. **§14.0.1 B2 / §14.4 — separate the bridge map (O9).** B2 and P1c feed a bridge-only map; `receiver_state.py:720`'s input is untouched. Replace the B2 box's "so … bit-for-bit unaffected" with "by construction, since `derive_receiver_states` does not call the extended pass — and AC-14.1(iii) measures it anyway". Rewrite "P1a-as-extended-by-B2" and "P1a or P1c" in §14.4 to name the bridge map.
9. **§14.9/§14.13/§14.16 Q5 — withdraw v2 (O11)**, re-size T28, and resolve Q5 by the withdrawal, citing §14.9's own over-fill-mutant argument.
10. **§14.6/§14.14(6)/§14.13 T27 — correct the cache and observation text (O5, O6).** `cache_key` already carries `env` (`check/ir.py:918-953`); T27 threads it into `check/__init__.py:766` and `CacheStore` and adds nothing to the tuple. Replace §14.14(6)'s invalidation sentence with the partition semantics. Replace §14.6's observation paragraph with the additive-result-field mechanism at `verifier.py:114-129` and `region_oracle.py:412-435`. State that `check_graph` gains keyword-only `env=`.
11. **§14.11/§14.16 Q2 — re-file B1 on HM-24 (O12).** HM-24 `declared` 1 → 3 with `_measure_hm24` returning 3 and each pattern asserted as the existing one is; HM-25 6 → 8; P10 off-registry; `live_rows()` unchanged at 24. Replace the "bindings rather than idioms" paragraph with the silent-versus-loud criterion from `_hand_maintained.py:796-799` / `:857-861`.
12. **Housekeeping (O13).** Delete every stale unscheduled/deferred sentence at lines 3, 2, 16-17, 29, 620, 716-717, 844 and 877-878; update the changelog to record this round. Fix the nine drifted citations to the verified values in O13(c). Rename the `test_spec_lint.py` parametrise id at `:220` and `:243` from `increment-5-volume-deferred`; T29's remaining work is that rename plus `INDEX.md`, ~2 LOC not ~15. **Then actually run `uv run pytest plr-sema/tests/test_spec_lint.py -q`** and record the result — AC-14.11 is currently a prediction and no one in this round could execute it.

---

## Verdict

**needs_revision.** Confidence high.

**Implementable as written: no** — the challenger is right about that, and about ten of his fourteen objections in whole or in part. But the single question he framed as decisive is answerable, and the answer is a mechanism rather than an intention. Admitting the B1-bound `for` header by node position is not a widening of the recognition set toward the unsound; it is the recognition of a loop the analyzer is already, in V2, claiming to simulate exactly, whose trip count PLR itself pins with a `ValueError` at `liquid_handler.py:989-992`. And the fail-closed treatment of `is_disabled` — which must stay, both by the user's resolution and by A-TRACKER-ENABLED's own terms — costs the family exactly one decidable guard, because `dispense`'s `op.tip.tracker.remove_liquid` at `:1235` sits *outside* the `is_disabled` test and *is* the under-draw direction. A harness fixture can drive `WILL_FAIL` under the asserted env. The sprint gate is meetable.

What that costs is honest and substantial: the increment's headline deliverable moves from the well to the tip, five acceptance criteria are re-sited or withdrawn, and the O4-remediation fixture that this document was largely written to add loses its executed oracle. Two further blockers are unconditional — P1c cannot see `Tip.__post_init__`, and no rule resets a tip cell across a retip — and both now sit on the *only* path that produces a definite verdict, which makes them more urgent than the challenger judged, not less. A third gap the challenger did not find (D1: the tip guard's cell is a local pairing V0 cannot read) is on the same path and is fatal as written.

Every one of these is a bounded text change against facts now fully in hand: the pin is read, the four guards are enumerated with their scopes, the three `self.tracker` writes are counted, the two contested literals are located, the cache key is inspected, the harness call orders are traced, and the survey's polarity handling is confirmed to already exist. Nothing requires information not in this report. **`needs_recon` is not warranted.** Twelve ordered items, of which six block T24's dispatch.
