---
title: 'plr-sema sprint 127 plan: the predicate language (increment 6, deferred row (c)) measured by the UNKNOWN ledger'
description: 'Sprint plan for 260904_sema-predicates: Band B0 the UNKNOWN ledger (root-cause clusters on the frozen tier-1 benchmark, deferred (f) shape) as the instrument; Band A increment 6 spec (deferred row (c), the predicate language) draft + adversarial round 1; Band B the derive-side parsed predicate and local-binding idioms with published measured sets as the gate; Band C the three-valued evaluator, reason refinements, tier-1 re-measure and ledger delta; Band D measurement debts (check-only elapsed for #4923, tips_dirty precision cost). Headline target: the first joined SAFE on a real executed operation. Decision hooks, baselines, exclusions.'
status: active
task_id: 260904_sema-predicates
date: '260904'
sprint: '127'
backlog_ids: '4976,4977,4978,4979,4981,4982'
---
# plr-sema sprint 127 plan: the predicate language (increment 6, deferred row (c)) measured by the UNKNOWN ledger

> Task id `260904_sema-predicates`. Spine: a **new** spec increment,
> `.praxia/docs/specs/260904_plr-sema-predicate-increment.md` (increment 6, spec_version 16), to be
> authored in band A from band B0's ledger. It takes the main spec's deferred row (c) — "the predicate
> language turning guard `condition` + `mentions_params` into a checkable predicate", which §7 carries
> as opaque strings "precisely so this can land later without reshaping the pipeline"
> (`260901_plr-sema-pre-corpus-spec.md:2518`, boundary table `:2534`). Planned at HEAD `7fc7271b` on
> `coxswain-p2-pipeline`, PLR pin `dd79c4c89`, sprint 123 `260903_sema-volume` closed and pushed.

## 0. Why this increment, and not the volume follow-ups

Sprint 123 closed with every oracle tier at 0 unsound and the first volume `WILL_FAIL` — and with the
tier-1 replay reporting **`unknown_rate` 1.0 for every one of the ten methods**
(`outputs/plr-sema/oracle_replay_260904_inc5.json`, `unknown_rate_by_method`): on all 548 executed real
operations the per-operation joined verdict is `UNKNOWN`. The analyzer has never said anything definite
about a real program. The memory's follow-up candidates from sprint 123 (well-side `is_disabled`
discharge, capacity operand, `delegates_to` volume propagation) do not move that number: the corpus
never seeds a well or disables a tracker (0 of 1523 sidecar rows mention `set_volume`/`set_liquids`/
`disable_volume_trackers`), so every volume cell is `TOP` at entry on real rows regardless, and
increment 5 §14.6 records why the `is_disabled` discharge is closed without new facts.

**The planning-time probe** (ephemeral, `$TMPDIR/probe/unknown_reason_probe.py`, a `check_ir` wrapper
around `oracle_replay.main` over the first 150 corpus rows — reproduced as a tracked script by band B0,
which is the citable version): 129 executed operations, 1,155 findings —

| finding (verdict, reason) | count |
|---|---|
| `unknown` / `guard_predicate_unparsed` | 936 |
| `safe` (tip typestate: `tip_tracker.py:65`/`:92`, `liquid_handler.py:535`) | 144 |
| `unknown` / `volume_state_unknown` | 75 |

Per operation, the set of reasons blocking the join is `{guard_predicate_unparsed}` on 84 ops and
`{guard_predicate_unparsed, volume_state_unknown}` on the other 45. **One reason blocks every
operation**, and it is the reason `check/__init__.py:292-313` emits for *every* guard because "no
predicate parser exists yet" (`:60`). That is deferred row (c), due now.

**Where the blocked guards sit** (probe, top sites; `d1` = inlined from a delegate):

| PLR site | guard (`condition`) | count | planning-time tier (see §2) |
|---|---|---|---|
| `liquid_handler.py:375` d1 `_check_args` | `len(missing) > 0` — backend signature vs kwargs | 91 | (ii) backend |
| `:383` d1 `_check_args` | `strictness == Strictness.STRICT` | 91 | (ii) env, process-global like `does_volume_tracking` |
| `:409` d1 `_make_sure_channels_exist` | `not len(invalid_channels) == 0`, `invalid_channels = [c for c in channels if c not in self.head]` | 76 | (ii) head channel count |
| `:116`/`:117` d1 `_check_no_lid` | `lidded is resource` / enclosing-lid walk | 53+53 | (ii) topology (increment 4 §13.1: no lid state field) |
| `:875` d1 `_check_containers` | `len(not_containers) > 0`, `[r for r in resources if not isinstance(r, Container)]` | 53 | (i) syntactic |
| `:321` d1 `_assert_resources_exist` | `not resource_from_deck == resource` | 38 | (ii) deck membership |
| `:498` `pick_up_tips` | `len(not_tip_spots) > 0`, `[ts for ts in tip_spots if not isinstance(ts, TipSpot)]` | 38 | (i) |
| `:502` / `:959` / `:1153` | `len(set(use_channels)) == len(use_channels)` (assert), `use_channels = use_channels or … or list(range(len(…)))` | 38 each | (i) literal or default |
| `:514` `pick_up_tips` | `not all(self.backend.can_pick_up_tip(channel, tip) …)` | 38 | (ii) backend |
| `:522` | `len(tip_spots) == len(offsets) == len(use_channels)`, `offsets = offsets or [Coordinate.zero()] * len(tip_spots)` | 38 | (i) |
| `:990` / `:1202` | `len(p) != len(use_channels)` | 38 / 23 | (i) — V0 clause (c) already decides this conjunct for the volume bridge |
| `:576` / `:1067` / `:1153`+ | `error is not None` — the backend's own raise, re-raised | 38 / 38 / 23 | (iii) opaque backend outcome |
| `:191` d1 `setup` | `self.setup_finished` | 38 | (ii) — the scaffolding `setup()`'s own guard reaching real ops via inlining; band B0 must say why it lands on real op ids |

`LiquidHandler.pick_up_tips` carries 10 guards / 0 gaps at this pin; `aspirate` 9 guards
(`plr-sema/data/derived_contracts.json`). Tip typestate already evaluates `:535`; volume evaluates
`:1034/:1035/:1234/:1235`.

## 1. Composition

| Band | Item | What | Model | Depends on |
|---|---|---|---|---|
| B0 — instrument | **#4976** | `plr-sema/eval/unknown_ledger.py` (bathos sidecar) over the sidecar-gated tier-1 executed rows at pin `dd79c4c89`: clusters keyed `(reason, PLR site, condition text)` with finding count, ops blocked, per-method share — the "absolute count of `UNKNOWN` root causes, clusters not raw findings, on a named frozen benchmark at a fixed pin" shape the main spec's deferred row (f) settled. `outputs/plr-sema/unknown_ledger_260904_before.json`. No analyzer change. | Sonnet | — |
| A — spec | **#4977** | Increment 6 draft (Opus, `praxia:specification-specialist`) from the ledger; adversarial round 1 (challenger + defender, Opus, no write tool — orchestrator persists `.praxia/docs/audits/260904_plr-sema-predicate-round1-{challenger,defender}.md`); remediation → `reviewed-round-1`. Must dispose Q1–Q4 (§3). | Opus | #4976 |
| B — gate | **#4978** | Derive side: `InlinedGuard.predicate` (typed mini-AST; `condition` retained as source of truth per the boundary table) and the **local-binding idiom** — a guard's free local bound at statement position in the same body by `x = [e for e in <param> if not isinstance(e, T)]` or `x = <param> or <default>` (the pass increment 4 §13.12 named "resolving a local's type from its assignment" and declined; scoped here to the ledger's shapes, fail-closed on every other shape). Every selection **measured and published** (`outputs/plr-sema/t30_measured_260904.json`): of the 5,180 guards, how many parse non-opaque; how many free locals bind; per-tier counts against the ledger's clusters. **Go/no-go lives here (§2).** | Sonnet | #4977 |
| C — machinery + oracle | **#4979** | `check/predicate.py`: Kleene evaluation against the IR call (literal kwargs, `RESOURCE` `type`/`element_type`/`grid`, contract defaults) and the tip/volume walks; F ⇒ `SAFE`, T under a `raise_guard` ⇒ `WILL_FAIL` only if unconditional (increment 5 §14.6's rule generalised), ½ ⇒ the finest applicable reason. `REASON_VOCABULARY` 10 → ≤ 12 (HM-14 cap 12). Tier 1 re-run (0 unsound is the gate — a `SAFE` on an op that raised is the failure this increment introduces for the first time); m1/m2/v1/tier-2b non-regression; ledger re-run → `unknown_ledger_260904_after.json`; `SPEC_INCREMENT_6` in the lint; implementation record. | Sonnet / Haiku (lint) | #4978 |
| C — conditional | **#4981** | Tier (ii): env members (strictness) and an **observation record** (backend class + signature, deck membership, head channel count, lid topology) — the harness already takes `setup.snapshot()` *before* execution (`training/verify/verifier.py:118-119`, `deck.py` `snapshot`: topology + `free_volume` per tracked object) and returns `backend` (`verifier.py:192`). **Do not start until round 1 disposes it** (§3 Q2). If it ships here, it is a cache-key component and fail-closed by default. | Sonnet | #4977, round-1 disposition |
| D — debts, parallel | **#4982** | (1) check-only elapsed field in `oracle_replay.py` — increment 4 §13.12.1's criterion (a) for #4923, ~5 lines, the report has no timing field today; (2) the `tips_dirty` precision cost on tiers 1/2b (cells widened by the structural rule vs unseeded `TOP`; findings turned from definite to `volume_state_unknown`) → `outputs/plr-sema/tips_dirty_cost_260904.json`. No analyzer change. | Haiku (1) / Sonnet (2) | — |

Order: B0 → A → B → C serially (each is the next one's premise; A cannot size the grammar without
B0's clusters). D runs in parallel with B0 from the first dispatch, in a worktree — it touches
`oracle_replay.py`, which B0's new script only imports.

## 2. The go/no-go gate (band B) — restated after the planning-time tiering

The three decidability tiers the spec must use:

- **(i) syntactic** — decided from the call's literal kwargs, the contract's defaults, and `RESOURCE`
  operands (declared/element type, grid). No hypothesis.
- **(ii) environment / observation** — reads state outside the extracted graph: a process-global
  (`get_strictness()`, the `does_volume_tracking` shape → an `env` member observed inside `verify()`'s
  window), the backend class (`backend_name`, its method bodies AST-derivable), the deck (membership,
  lids, channel count). Decidable only under a recorded hypothesis or an observation from the world.
- **(iii) opaque** — the backend's own raise re-raised (`error is not None`). Never decided from the
  PLR layer.

**Planning-time inspection already shows tier (i) alone cannot clear a whole operation:** of
`pick_up_tips`'s ten guards, (i) covers `:498/:502/:522`, tip typestate covers `:535`, and the other
six are (ii) `:514/:375/:383/:409/:321` and (iii) `:576`. So the gate is **not** "tier (i) clears an
op". It is:

- **GO** if, after B's parsed predicates and local-binding idioms, the published per-op residual on the
  frozen benchmark is **exactly tiers (ii) and (iii)** for at least one executed real operation — i.e.
  every syntactic guard on it parses and binds, and nothing unparsed remains that is not observation-
  or backend-dependent. Then C ships (i) + the finer reasons, and whether the first joined `SAFE`
  lands this sprint is decided by Q1/Q2 (below), not by derivation.
- **NO-GO** if some tier-(i) guard on every candidate op still fails to parse or bind after the
  idioms land. Publish the counts and the structural reason in the spec's implementation record, keep
  the derive code (it is a strict information gain on the contract table either way), and bring the
  decision to the user before the evaluator.

## 3. Decision hooks — the round must dispose, and some stop for the user

1. **Q1 — what a joined `SAFE` means for an operation with a tier-(iii) guard.** Every liquid-handling
   op carries `error is not None`. A `SAFE` finding on it would claim the backend did not raise —
   which is A-COMPLETES (increment 1 §10.7, `260902_plr-sema-tip-typestate-increment.md:752`) applied
   to the *current* op, not a PLR-side precondition. Options the spec must argue: (a) a **scoped**
   `SAFE` — the verdict is over the PLR precondition layer and backend outcomes are excluded by
   failure category (§4's `FAILURE_CATEGORIES`), recorded as a `SoundnessScope`-style annotation
   (main spec `:103`, `:3330`), so the join can be `SAFE` with the backend guard carrying its own finer
   reason outside the join; or (b) never `SAFE` on such an op — in which case the headline is
   unreachable by construction and the sprint's deliverable is the ledger delta only. **If the round
   lands on (b), stop and put it to the user**: it decides whether "first definite verdict on a real
   program" is a goal of this analyzer at all.
2. **Q2 — does tier (ii) ship in increment 6 or as increment 7?** `strictness` is the exact
   `does_volume_tracking` shape and costs one `env` member; backend/deck/channels need an observation
   record and a cache-key extension. The legitimacy argument must be stated against increment 5
   §14.6's two failed `is_disabled` discharges (an observation taken from the world is not a
   quantified claim, and is not "the graph is the whole world"). Round's call; #4981 follows it.
3. **`REASON_VOCABULARY` 10 → 12 is the ceiling** (HM-14, cap 12). If the grammar needs a 13th member
   the cap conversation is the user's (§9.4 anti-gaming), not the sprint's.
4. **Registry headroom is 0** (`live_rows() == 24 == BUDGET_CAP`; HM-24 3, HM-25 8 as approved
   260904). The local-binding idiom is a shape match with a silent failure mode — if the round puts it
   on HM-24 (ceiling 3 → 4) or HM-25 (8 → 9), that is a per-row ceiling spend and a **user decision
   before band B spends it**, exactly as sprint 123's Q2.
5. **#4923 re-evaluation** once D publishes the check-only elapsed: increment 4 §13.12.1's threshold is
   ~60 s check-only for a whole-corpus re-check; record the number against it in the sprint outcome.
   The decision stays NO-GO unless the number exceeds the threshold *and* the user wants it.
6. **#4924 stays NO-GO** (increment 4 §13.12.2): its criterion is the capacity operand, which this
   sprint does not touch.

## 4. Baselines that must hold at close

| Tier | Baseline (sprint 123 close) | Where |
|---|---|---|
| 1 sidecar-gated replay | 343 executed / 548 ops, `rows_setup_error` 0, crosscheck 191/191 agreement 1.0, **0 unsound**, `unknown_rate` 1.0 (the number this sprint exists to move) | `outputs/plr-sema/oracle_replay_260904_inc5.json` |
| 2b executed regions | 16 fixtures, `region_unsound` 0, `region_will_fail_fired` 7, `volume_will_fail_fired` 3 | `outputs/plr-sema/tier2b_260904_inc5.json` |
| 3 tip mutants | m1 199/199, m2 289/289, 0 unsound | `outputs/plr-sema/tip_mutants_260904_inc5.json` |
| 3 volume mutants | v1 67/67 `WILL_FAIL` at the raised index, 0 unsound | `outputs/plr-sema/volume_mutants_260904_inc5.json` |
| registry | rows 24/24 (cap 24), HM-24 3, HM-25 8, `REASON_VOCABULARY` 10/12 | `test_hand_maintained_ratchet.py` |
| spec lint | 24 passed, six specs 0 failing citations | `plr-sema/tests/test_spec_lint.py` |

Tier-1 replay is always run with `--sidecar training/assemble/out/corpus_p25_sidecar.jsonl
--crosscheck training/out/corpus_p23_floor.jsonl --crosscheck training/overlay_gen/out/overlay_full.jsonl`.
The one number allowed to move is `unknown_rate` (down) — and only with `unsound` staying 0. A `SAFE`
that raised is the failure this increment makes possible for the first time; the oracle is the fence.

## 5. Explicitly out

- **The volume follow-ups from sprint 123** — well-side `is_disabled` discharge (closed by increment 5
  §14.6 without new facts; Q2's observation record is the only legitimate re-opening path),
  capacity operand on `RESOURCE` (§14.15; corpus wells are `TOP` at entry regardless), `delegates_to`
  volume propagation / transfer v2 mutant (§14.15).
- **#4923 / #4924** — decision hooks only (§3.5–3.6), no implementation.
- **A `pred`-aware `BRANCH`** (increment 3 §12.3.6 B2, `260903_plr-sema-real-programs-increment.md:673,1231`)
  — the same evaluator would serve it, and it is the natural increment 7 *alongside* tier (ii); not
  this sprint.
- **Lid verdicts** — increment 4 §13.1's disposition stands; `_check_no_lid` is tier (ii) and lands, if
  at all, under #4981's topology observation, not as a lid family.
- **A general dataflow pass over PLR method bodies.** The local-binding idiom is two statement shapes,
  fail-closed. Anything wider is a new increment.
- **#4956** P2.6e label-conflict audit — Coxswain track, user's call. REPL P0–P7, Coxswain W0–W6 —
  other track.

## 6. Dispatch conventions (unchanged from sprints 121–123)

- Fixer briefs mandate: `uv run python` never bare python; per-file pytest only (the jax-mem-guard
  blocks any path ending in `/tests`); path-scoped `git add`; **no background Bash, no monitors**;
  foreground with timeout; final line `COMMIT: <full sha>`; trailers `Co-Authored-By: Claude Fable 5.1
  <noreply@anthropic.com>` + `Claude-Session: https://claude.ai/code/session_01QgK1DBdBsTFJou6ML91sNT`.
- Full per-file set before closing a band: `test_derive`, `test_check_graph`, `test_wire_fuzz`,
  `test_verdict` (the §3.3 reason scan), `test_hand_maintained_ratchet`, `test_cache`,
  `test_tip_typestate`, `test_oracle_replay`, `test_spec_lint`.
- Spec author / challenger / defender have no Bash; the orchestrator persists their reports and runs
  `test_spec_lint` itself after every spec edit; `check_spec_citations.py` skips `.claude/`.
- Diagnostic and measurement rows go to Sonnet, never Haiku (sprint 121 lesson); demand per-cluster
  root causes, never a bare PASS.
- Never touch the other session's dirty entries; `outputs/plr-sema` is gitignored (force-add reports);
  `git push` needs the sandbox off.

## 7. Estimate

B0 ~150 lines + a report; A a draft the size of increment 5 plus a round (the largest single cost —
increment 5's round took most of a day); B ~400 (parser + two idioms + measured sets); C ~450
(evaluator + reasons + oracle re-measure + ledger delta); #4981 ~300 if admitted; D ~60. Two days if
tier (ii) ships, a day and a half if the round defers it.

## 8. Execution log and decision log (260905, orchestrator)

**Landed on `coxswain-p2-pipeline`:** B0 `67194770` + fix `ca756bce` (ledger keys ops positionally; 12
`record_id` collisions no longer merge ops; `consistency.ok == true`); D1 `55b84dc4` (check-only elapsed
**35.8 s** vs the ~60 s #4923 threshold, runtime 51.8 s, wall 88.4 s, baseline 343/548/0 unsound held);
D2 `f6a77baa` (`tips_dirty` cost: tier 1 **0** definite verdicts lost of 194 `volume_state_unknown`, tier
2b **1** of 34 — the designed `volume_retip` counterexample); increment 6 draft `6407d92a`; round-1
challenger `4d75b386` (C1–C18, six blockers) and defender `2fa228e8` (D1–D3, 18-item list); remediation
`c9f4779e` (spec_version 17, `reviewed-round-1`, `SPEC_INCREMENT_6` enforced — lint 26 passed, 275
citations 0 failing).

**What round 1 changed about this plan.** §2's gate is restated **over reasons, not tiers** (C8): GO iff
≥ 1 executed op carries zero `guard_predicate_unparsed` and zero `guard_operand_unknown` findings. §3
Q1 resolved to (a) scoped `SAFE` but with the fence narrowing **deleted** (C3) and tier (iii) emitting
`UNKNOWN`/`guard_env_dependent` + an `excludes_sites` annotation (C9); §3 Q2 resolved **DEFER** to
increment 7 (#4981 = increment 7, not this sprint). The planning-time claim that `setup :191` reaches
real ops was a probe artifact (ledger note 1). The ledger shows three reason-set combinations, not two
(`{gpu}` 334, `{gpu, volume}` 117, `{gpu, unresolved_delegate}` 93 — all `move_*`, deferred row (e)).

**Decisions pending the user before band B *spends* anything (defender §(2); band B's derive work
proceeds meanwhile because it is an information gain either way and spends no ceiling):**

| # | question | round-1 recommendation | status |
|---|---|---|---|
| 1 | Spend HM-25 `declared` 8 → 9 to file α+β (one entry; `live_rows()` stays 24/24)? If no, α/β ship unregistered and AC-15.7 asserts 8. | **yes** | **approved by the user 260907** |
| 2 | Substitute the sprint headline: per-finding `SAFE` + a legible residual now; the first *joined* `SAFE` in increment 7 (needs tier (ii))? | **yes** | **approved by the user 260907** |
| 3 | Adopt γ (bounded literal-display loop) this increment? Without it `aspirate`/`dispense` (117 ops) stay NO-GO and the gate rests on `pick_up_tips` alone. | **no** | **approved by the user 260907** |
| 4 | Ship both new reasons, `REASON_VOCABULARY` 10 → 12 of cap 12 (exhausts HM-14 headroom)? Fallback: `guard_env_dependent` alone, 10 → 11. | **yes** | **approved by the user 260907** |

**#4923 re-evaluation (§3.5):** check-only 35.8 s < 60 s threshold → NO-GO stands. **#4924:** NO-GO stands (§3.6).

**Band B landed (260906):** T30a `58e5c3fc` (typed mini-AST, total `parse`, `InlinedGuard.predicate`,
contract table regenerated: 7,528 guards, 6,295 parse non-`Opaque`, 1,233 `Opaque`, 925 nested-`Opaque`);
T30b-1 `7c0fe59a` (`param_defaults`; α 5 / β 11 bindings vs the spec's predicted 4 / 8 — the extras are
`_assert_positions_unique:294` and `transfer:1353` plus two `VantageBackend` β; O1 element types,
default-off, 0 heterogeneous parents); T30b-2 `6cbbe442` (`t30_measure.py`: D2 `channels_for_call`
non-`None` on every executed `pick_up_tips` op, `tip_spots` lowers as `ir.Seq` on all; name-coincidence
exposure 936 depth≥1 occurrences; O1 delta 389 ops; `guard_operand_unknown` **0** everywhere with O1).

**Gate (§2 restated, reason-based): NO-GO.** No executed op reaches zero `guard_predicate_unparsed`.
`pick_up_tips`'s residual is `{decidable, guard_env_dependent, guard_predicate_unparsed}`; the two
`guard_predicate_unparsed` members are `liquid_handler.py:409` (`invalid_channels = [c for c in channels
if c not in self.head]` — α binds, the filter `c not in self.head` is `Opaque`, §15.7's nested-`Opaque`
rule assigns `guard_predicate_unparsed`, while §15.9's prediction table said `guard_env_dependent`) and
`:514` (`not all(self.backend.can_pick_up_tip(channel, tip) for channel, tip in zip(use_channels, tips))`
— `zip(...)` is not a G1 `Term`, so `Opaque`). Both are expressions rooted at `self.` — the receiver's head
and backend, tier (ii) by §15.1's definition — that the grammar cannot recognise as environment reads.
Per §2 / spec §15.9: derive code kept (information gain), T31 NOT started, decision to the user.

**Measurement caveat (T32 fix-up, not a gate factor):** `t30_measure.py` re-implements `run_row`'s
skip/no_call gating and reports 923 ops (`pick_up_tips` 361) where the ledger's frozen population is 544
(`pick_up_tips` 223); the per-site classification is population-independent, so the NO-GO stands, but
the script must reuse `oracle_replay.run_row`'s own gating before any published delta.

**Decision 5 for the user (the NO-GO):** (a) accept NO-GO — the sprint closes with the ledger, D, the
spec, and the derive-side gains, no evaluator; or (b) amend the grammar narrowly (spec_version 18):
an `EnvRef` leaf for an expression rooted at `self.` (attribute chain, optionally called with `Term`
args) that the grammar *recognises* as an environment read, evaluates to ½, and carries
`guard_env_dependent`, not `guard_predicate_unparsed`; plus `zip(<Term>, <Term>)` as a `Term` for
`AllOf`/`AnyOf`. Under (b) `pick_up_tips`'s residual becomes `{decidable, guard_env_dependent}` ⇒ GO,
and T31 proceeds. Anti-gaming check for (b): `EnvRef` is syntactically narrow (rooted at `self`), decides
nothing, and its count is published under `guard_env_dependent`, which the gate already excludes from
"converted". Orchestrator's recommendation: **(b)**, with a short adversarial pass on the amendment.

**Decisions taken (user, 260907): all five recommendations approved** — (1) HM-25 `declared` 8 → 9 for α+β;
(2) headline substituted (per-finding `SAFE` + legible residual now; first joined `SAFE` in increment 7);
(3) γ not adopted; (4) `REASON_VOCABULARY` 10 → 12; (5) the `EnvRef` grammar amendment (spec_version 18,
short adversarial pass), after which the gate is re-measured and, on GO, T31–T33 proceed.

**Amendment round and re-measure (260907–260908):** population fix `15b84d31` (t30_measure now drives
`oracle_replay.main` via `FINDINGS_SINK` + `LOWERED_SINK`; 544 / 223; cause: sidecar `ambiguity_class`
not passed to `row_to_verifier_inputs`); amendment `f441d27e` (spec_version 18); challenger `aaa00f8a`
(A-C1–A-C13: not gaming, GO prediction survives, needs_revision revise-and-advance); remediation
`15ae7c45` (spec_version 19, `reviewed-round-2`: G7 shape (2) gated by the derive function index,
`Zip` ⊤ unless every item concrete and never vacuously T, membership always ½, α/β-substituted walks,
reason clauses reordered, HM-25 fallback normative with `_measure_hm25` symbols, T30c → T35). Scope
note for the user: the `in`/`not in` comparator widening was not named in decision 5's text but is what
makes `:409`'s filter readable; treated as in scope by necessity, to confirm at close. **T35** `a2cd0499`
+ `100ab273`: **GATE GO** — `pick_up_tips` clears on 223/223 executed ops with O1 (residual
{decidable, guard_env_dependent}); every method's residual matches §15.9's re-prediction table exactly;
12 PLR-layer `self.<name>(...)` calls refused; `n_var_self` 0; 386 guard sites carry `EnvRef`. Band C
(T31 evaluator → T32 oracle → T33 lint/INDEX) dispatched.

## 9. Outcome (260909)

**Sprint 127 closed. Increment 6 `implemented-round-2` (spec_version 20).** Headline, as the user
approved it 260907: **per-finding `SAFE` and `WILL_FAIL` on real executed operations, plus a legible
residual — no joined `SAFE` this increment** (every op carries `_check_args` `:375`/`:383`, tier (ii),
deferred to increment 7 with #4981).

| Band | Item | Commits | Numbers |
|---|---|---|---|
| B0 | #4976 | `67194770`, fix `ca756bce` | Ledger: 544 executed ops all UNKNOWN, 54 clusters, 6,036 findings; three reason-set combos; `consistency.ok` |
| D | #4982 | `55b84dc4`, `f6a77baa` | check-only 35.8 s (< 60 s ⇒ #4923 NO-GO stands); `tips_dirty` cost tier 1 0/194, tier 2b 1/34 |
| A | #4977 | `6407d92a`, audits `4d75b386`/`2fa228e8`, remediation `c9f4779e` | Round 1: six blockers conceded (C1 false WILL_FAIL on ~244 clean ops; C3 fence narrowing; C4 E-TYPE; C5 floor; C6 β; D1 param_defaults); gate restated over reasons |
| B | #4978 | T30a `58e5c3fc`, T30b `7c0fe59a`/`6cbbe442`, population fix `15b84d31`, amendment `f441d27e`→`15ae7c45` (+ audit `aaa00f8a`), T35 `a2cd0499`/`100ab273` | 7,528 guards, 6,295 parse; α 5 / β 11; first gate **NO-GO** (`:409` `self.head` filter, `:514` zip/backend call), then **GO** after the `EnvRef`/`Zip` amendment: `pick_up_tips` 223/223, residual {decidable, guard_env_dependent}; 12 PLR-layer calls refused |
| C | #4979 | T31 `1a58b337`/`436c0edb`, T32 `e3970b3a`/`f63b3ff8`, T36 `f82ce87d` | Tier 1 **0 unsound**, 343/548/191 held; `n_findings_decided` **1,563** (floor 223); `guard_predicate_unparsed` **5,656 → 495**; `REASON_VOCABULARY` 12/12; HM-25 9, `live_rows()` 24; m1 199/199, m2 289/289, v1 67/67, tier 2b 16/0/7/3 exact; p1 predicate mutants (a) 288/288, (b) 16/16 WILL_FAIL at the raised index, (c) 0 as asserted, 0 unsound |
| — | #4981 | — | Tier (ii): increment 7 (round-1 Q2 DEFER) |

**Decisions taken (user, 260907):** HM-25 8 → 9; headline substitution; γ not adopted; reasons 10 → 12;
the `EnvRef` amendment. **Scope note to confirm:** the `in`/`not in` comparator widening rode with the
amendment (it is what makes `:409`'s filter readable) — recorded in spec §15.16.1 A3.
**Not adversarially reviewed:** spec §15.16.3 R1, the E-UNCOND(5) refinement (an earlier `raise` does
not block WILL_FAIL) — soundness argued in the spec, evidenced by 0 unsound on tier 1 and on all three
mutant classes; first candidate for the next pass.

**Increment 7 candidates (not scheduled):** tier (ii) observation record + `strictness` env (#4981);
the delegate→caller argument map (~90 LOC); γ (bounded literal-display loop); the `pred`-aware
`BRANCH`; a PLR class hierarchy on the wire (E-TYPE subclass cases); `for_span` on `InlinedGuard`
(E-UNCOND way (3)); the site-keyed fence narrowing via `traceback.extract_tb` when a joined `SAFE`
first becomes possible.
