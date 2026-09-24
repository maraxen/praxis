---
title: 'plr-sema oracle harness: assessing the analyzer in simulated use'
description: 'Design for catching plr-sema bugs by comparing static verdicts against PLR''s chatterbox simulator (STRICT + tip/volume tracking) as ground-truth oracle: four input tiers (corpus replay, source-rendered corpus, mutation/metamorphic, wire-format fuzz), the soundness contract each verdict must satisfy, metrics, and phasing.'
status: draft
task_id: 260902_preflight-checkers-rename
date: '260902'
sprint: ''
backlog_ids: '4879, 4880, 4881, 4882'
---
# plr-sema oracle harness: assessing the analyzer in simulated use

## The question

`plr-sema` is a sound static analyzer: for every operation in a protocol's
execution graph it returns `SAFE` / `WILL_FAIL` / `UNKNOWN`. Its tests check
that the *machinery* behaves (contracts derive, findings are total, the join is
right). None of them check that a verdict is *true* — that a protocol the
analyzer calls `SAFE` really runs, or one it calls `WILL_FAIL` really raises.
That is the class of bug a static analyzer ships silently, and it needs an
independent second reading of the same protocol to catch.

PyLabRobot supplies that second reading for free. `LiquidHandler` on the
`LiquidHandlerChatterboxBackend` with `set_tip_tracking(True)` and
`set_volume_tracking(True)` enforces the very preconditions the analyzer
targets, at runtime, with no hardware:

| PLR raises | where | when |
|---|---|---|
| `NoTipError` | `tip_tracker.py:65,105` | aspirate/dispense/drop with no tip mounted |
| `HasTipError` | `tip_tracker.py:92`, `liquid_handler.py:535` | pick up onto a channel that has a tip |
| `TooLittleLiquidError` | `volume_tracker.py:92` | aspirate more than the well holds |
| `TooLittleVolumeError` | `volume_tracker.py:105` | dispense over capacity |
| `BlowOutVolumeError` | `liquid_handler.py:1185-1188` | dispense volume exceeds the tip |
| `ValueError` | `liquid_handler.py:116,990` | lidded resource; volume-list shape mismatch |

(Line numbers at submodule pin `dd79c4c89`.) `training/verify/verifier.py`
already wires all of this: `verify(call_sequence, intent_record)` builds a
chatterbox deck, sets STRICT + both trackers, plans each call through
`dispatcher.plan_call`, awaits it, and absorbs any exception into one
`error: "ExcClass: message"` string. The corpus that P2.5/P2.6 executed through
it — 812 rows in `training/assemble/out/corpus_p25.jsonl` plus 88 golden pairs
— is in **tool-call form** (`[{name, params}]`), not Python source.

So the oracle exists in fragments. What is missing is the glue that produces the
static reading of the same protocol and lines the two up per operation.

## Feasibility: the spike (260902)

`plr-sema/scripts/oracle_spike.py` closes the loop for the four verifier
examples in `training/examples/`:

1. **runtime** — `verify()` with `plan_call` wrapped to record which operation
   index was being planned when the run raised (the verifier itself only keeps
   the string).
2. **static** — the same call sequence adapted straight into the §6.2 graph
   wire format (one `OperationNode` per call on receiver `lh: LiquidHandler`,
   one `ResourceNode` per deck-layout resource), then `check_graph` against the
   shipped `derived_contracts.json`; per-operation verdict = `join` of that
   operation's findings.
3. **compare** — per operation: `ran_ok` / `raised:<Class>` / `not_reached`
   against the static verdict.

Result: 4 examples, 10 operations, every operation aligned, 0 unsound. A
hand-made mutant (`clean_transfer` with `pick_up_tips` removed) produced
`raised:NoTipError` at op_0 and `not_reached` at op_1 — the oracle sees
precondition failures at the right step. Every static verdict was `UNKNOWN`
with 9–17 findings per operation, exactly as v1 specifies (§0: no `SAFE`
constructed anywhere, `join(∅) = UNKNOWN`).

Two facts the spike surfaced that shape the design:

- **Ground truth has two kinds.** `wrong_slot_known_failure.json` runs *clean*
  on the simulator; its failure is an intent-agreement check
  (`checks.py:_check_slot_agreement`), i.e. a postcondition against the user's
  stated intent, not a PLR precondition. The harness must record PLR exceptions
  and verifier check failures as separate columns — only the first is a claim
  the static analyzer makes.
- **The failing index needs the wrapper.** `verify()`'s return carries
  `bindings` from executed calls but not a count; wrapping `plan_call` is the
  cheapest faithful source and should become a supported return field
  (`executed_count`) rather than a monkeypatch when tier 1 lands.

## The soundness contract being checked

Per operation `i`, with `s_i` the static verdict and `r_i` the runtime outcome:

| `s_i` | `r_i` | reading |
|---|---|---|
| `SAFE` | `raised:*` | **unsound** — a bug of the first severity; `SAFE` must never be wrong |
| `WILL_FAIL` | `ran_ok` | **unsound** — a definite-failure claim the semantics contradict |
| `WILL_FAIL` | `raised:C` | agreement; additionally check `C ∈ contract.raises` for that guard |
| `SAFE` | `ran_ok` | agreement |
| `UNKNOWN` | anything | no constraint — counted as the precision cost |
| any | `not_reached` | no constraint (an earlier operation raised) |

Zero unsound rows is a hard gate. The `UNKNOWN` rate per method family is the
number that should fall as deferred items (a) abstract domain and (c) predicate
evaluator land; it is 100% today by construction.

## Four input tiers

**Tier 1 — corpus replay (#4879, first).** The spike generalised to the 812 +
88 rows, bathos-tracked. Outputs: the agreement matrix above; `UNKNOWN` rate by
method family; and — the actionable one — the ranked list of exception classes
the simulator actually raised across the corpus. That list says which contract
guards are worth making decidable first: there is no point evaluating a guard
family the corpus never trips. Also checks totality on real inputs
(`len(findings) >= len(operations)` for every row, AC-7.2) and that
`check_graph` never raises.

**Tier 2 — through the extractor (#4880).** Tier 1 bypasses libcst. Tier 2
renders each call sequence to a minimal Python protocol
(`await lh.transfer(source["A1"], dest["B1"], 50)` with resources as
parameters), runs praxis's `computation_graph_extractor` out of process, and
feeds *that* graph to `check_graph`. Tier-1 and tier-2 verdicts for the same
row must agree; a divergence is an extractor defect **or a tier-1 adapter
defect** — the flow-sensitive tips gate at `computation_graph_extractor.py:547`,
receiver typing, argument capture on one side; argument naming on the other.

> **Qualified 260902 (T18, spec increment §10.10 Q3).** The spike's adapter emits
> the corpus's *tool* parameter names (`at`, `source`, `volume_ul` — see
> `training/verify/dispatcher.py`) as `OperationNode.arguments`, while derived
> guards are written over PLR's *method* parameter names (`tip_spots`,
> `use_channels`, `offsets`). Any evaluator keyed on argument names therefore
> sees no recognisable arguments and widens every tier-1 row to ⊤ — the tier-1
> gate would pass vacuously for the tip-typestate increment. Fix for tier 1:
> build `arguments` from `PlanResult.kwargs` (the bound `LiquidHandler` kwargs
> the dispatcher already produces), not from the tool call's params. Until that
> lands, the increment's real oracle gate is tier 3's PLR-named mutants
> (AC-10.12), not tier 1.

**Tier 3 — mutation / metamorphic (#4881).** Every clean corpus row spawns
mutants PLR is known to reject: remove `pick_up_tips` → `NoTipError`; duplicate
it → `HasTipError`; aspirate above seed volume → `TooLittleLiquidError`;
dispense over capacity → `TooLittleVolumeError`; lid a plate before access →
`ValueError`. Metamorphic relation: the simulator's rejection at op `i` forbids
`SAFE` at `i`; its acceptance forbids `WILL_FAIL`. Each mutation class also
names the guard family the analyzer must eventually decide, so the report
tracks per class how many mutants flip from `UNKNOWN` to `WILL_FAIL` over time.

**Tier 4 — wire-format fuzz (#4882).** `hypothesis` over random §6.2 payloads
and contract tables into `check_graph`: never raises; totality holds; never
`SAFE` without an evaluated guard; `Verdict.from_wire` widens every unknown
string to `UNKNOWN`; `join` is order-independent and idempotent. Fast, no PLR
import, runs in the normal suite.

## Where it lives

Not under `src/plr_sema/` — the harness imports `pylabrobot` and
`training.verify`, and `tests/test_import_boundary.py` exists precisely to keep
those out of the analyzer. `plr-sema/eval/` (tiers 1–3, bathos sidecar per
run, `uv run --package plr-sema`) and `plr-sema/tests/test_wire_fuzz.py`
(tier 4). The spike stays in `scripts/` as the worked example.

## Status (260902, end of day)

| tier | backlog | state | numbers |
|---|---|---|---|
| 1 corpus replay | #4879 | **re-baselined 260903** (#4944 85fe6eb5) | regenerated corpus (assembly 0.1.5, 900 → 1427 rows) replayed without `--sidecar`; 297 spurious totality violations fixed with a new `rows_setup_error` bucket (13 rows) and content-digest `record_id`s: 330 executed / 525 ops / 191 exact join / agreement 1.0 / 0 unsound / 0 totality (`outputs/plr-sema/oracle_replay_260903_rebaseline.json`). Like-for-like vs the 260902 baseline on the 728 shared rows: 216/341/0/0. Residual: of the 40 golden rows once thought unparseable, only 1 of 16 underscore-shaped refs meets AC-12.19's declared-base gate (#4939 b35bc338) — they executed and raised inside the verifier, not a parse failure. |
| 2 through the extractor | #4880 | **done** — 2a #4880 12bc591a, 2b T21 88f01fdb | 2a (bytecode differential): 330 rows compared, extractor-cause divergences 0, renderer 122, grammar 0, reset 0, 235 agreeing, directional 208/210 (`RESOURCE` declarations and `WIDEN(depends_on_params)` excluded, structural asymmetries). 2b (executed region fixtures): 11 fixtures (`for`/`while`/`if` ×2, nested, `range(0)`, `continue`, `break`, straight-line), `region_unsound = 0`, `region_will_fail_fired = 3`, trip mismatches 0. **Caveat:** the tier-2b join was specified as `(method, lineno)` but `OperationNode.line_number` is 0 at every call site (`_current_line` never reassigned past its `__init__` default, predates #4932) — the join degrades to method-only, guarded by a one-call-site-per-method fixture constraint + `DuplicateCallSiteError`; praxis-side fix tracked as backlog #4948. See spec §12.13. |
| 3 mutation / metamorphic | #4881 | **tip family + VOLUME family done** (v1 67/67) — tip family #4938 b39020cd + f1cecd0e, up to m1 193/193/m2 254/254 by #4946; volume family T28 `c67fc230` (sprint 123, 260904); lid family still open (not adopted, increment 4 §13.1) | tip family, current: m1 193/193 WILL_FAIL at the raised index, m2 254/254, 0 unsound (#4946, 260903). Volume family, new (260904): v1 (`v1_overdraw_dispense`, sited on `dispense`'s `op.tip.tracker.remove_liquid`) **67/67** raised, 67/67 `WILL_FAIL` at the raised index, 0 unsound; m1/m2 non-regression held at 199/199 and 289/289 (corpus grew to 1523 rows) over the same refactored `run_one_mutant`. Tier-2b volume: 4 new fixtures (straight-line, second-iteration, collective-exhaustion, retip) under `plr-sema/eval/fixtures/regions/volume_*.py`, `region_will_fail_fired` 7 total (4 tip + 3 volume), `region_unsound` 0. v2 (`v2_overdraw_transfer`) WITHDRAWN — `transfer` has no volume-guard derivation path (spec §14.9, round-1 O11). Lid family remains not adopted per increment 4 §13.1 (four structural blockers, none derivable). |
| 4 wire-format fuzz | #4882 | **done** (b81a93f8) | 8 properties × 150 examples; malformed-payload classes pinned; found a duplicate-operation-id totality bug in step 0 during development |

**260903 (sprint 121 close):** tier 1 re-baselined, tier 2 (2a+2b) done, tier 3's tip family done —
see `.praxia/docs/specs/260903_plr-sema-real-programs-increment.md` §12.13 for the full
implementation record and commit shas. Volume/lid mutation families (tier 3) remain under #4881.

**260903 (sprint 122 close):** tier 1 331 executed / 528 ops after #4950 (the verifier now types
resources by call-sequence usage rather than name prefix; `rows_setup_error` 13 → 12; the one residual
is `build_setup`'s own limits, tracked as #4952). Tier 2a 330/330 agreeing (the renderer residual
closed, #4949). Tier 2b's join is now by the real `(method, line_number)` pair rather than the
method-only degradation §12.13's caveat recorded (#4948), fires 4 findings, 0 unsound. Tier 3's tip
family: m1 193/193 WILL_FAIL at the raised index, m2 254/254, 0 unsound (#4946, up from 84/101 at the
sprint-121 baseline). Volume and lid mutation families remain deferred, now explicitly to increment 5
(`.praxia/docs/specs/260903_plr-sema-volume-increment.md`) rather than open-ended under #4881.

**260904 (sprint 123 close):** tier 1 343 executed / 548 ops after #4952 (`build_setup` limits: one
TipRack per tip-typed base, free-rail iterator for Troughs, skip auto trash when declared;
`rows_setup_error` 12 → 0). Tier 3's volume family lands (T24–T28, `.praxia/docs/specs/260903_plr-sema-volume-increment.md`
§14.17 has the per-row implementation record): the bridge derives on real PLR (`liquid_handler.py:1031-1235`),
the caller-scope threading and R1's position-containment recognition close the soundness gap increment
4's round 1 found, and the interval domain (V0–V5) ships with the tip-cell lifecycle (V5) and region
widening (V4). Registry: HM-24 `declared` 1 → 3, HM-25 `declared` 6 → 8, `REASON_VOCABULARY` 8 → 10,
`live_rows() == 24 == BUDGET_CAP` — approved by the user 260904. Real-row diagnostic scan (591 rows):
`safe` 66, `volume_state_unknown` 340, `WILL_FAIL` 0, `volume_tracking_unasserted` 0 at this pin (the
family is firable, per the user's 260903 "build it if it is firable" resolution, but the corpus does
not currently trip the `does_volume_tracking()` hypothesis on any row). Tier 2/2a/2b unchanged from
sprint 122.

The adapter this plan described (`adapt_graph`) is retired: tier 1 lowers call sequences with
`lower_calls` over `PlanResult.kwargs` (SEMA-IR §11.2.2), so the tool-vs-PLR parameter-name defect
noted above is closed structurally (Gate B: 104 CALLs, 0 violations).

## What this does not measure

- Precision. Until an emitter constructs `SAFE` or `WILL_FAIL`, there are no
  positives to be false; the harness is armed, not firing.
- Anything the chatterbox backend does not enforce — physical collisions,
  timing, backend-specific limits. Those are hardware truths, not simulator
  truths, and out of v1 scope with error recovery and optimization.
- Non-legacy PLR. The verifier runs at the pinned submodule (`dd79c4c89`);
  the `upstream_nonlegacy` surface has contracts (T14) but no executable
  oracle here until praxis migrates off the pin.
