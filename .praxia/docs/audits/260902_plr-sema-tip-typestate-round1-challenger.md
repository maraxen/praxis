---
title: 'plr-sema tip-typestate increment — adversarial round 1, challenger'
description: 'Challenger report on .praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md (spec_version 9 draft): 3 BLOCKER (A-COMMIT false via clear_head_state/update_head_state commit=False; conflicting depth-0 bridges unruled; tip_state taxonomy category has 5 members not 2), 2 MAJOR, 4 MINOR; verdict not_ready.'
status: final
task_id: 260902_sema-oracle-tipstate
date: '260902'
confidence: high
sources: 'praxia:spec-challenger (claude-sonnet-5), code and PLR pin dd79c4c89 read directly'
---
# plr-sema tip-typestate increment — adversarial round 1, challenger

Target: `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md` at commit `ca54866d`.
Agent: `praxia:spec-challenger` (Sonnet). Verbatim report follows; adjudication is the defender's
(`260902_plr-sema-tip-typestate-round1-defender.md`) and the remediation changelog lives in the
increment itself.

---

### O1 — BLOCKER (unsoundness). A-COMMIT is not an assumption, it is false, and a concrete counterexample exists

**Location:** §10.2.2 lines 226–236 ("They cannot disagree at an operation boundary… every LiquidHandler tip operation commits or rolls back every touched head tracker before returning"); §10.6.3's A-COMMIT row (line 588: "verified true for the two methods that matter"); §10.10 Q1 (lines 824–830).

**Evidence:** `LiquidHandler.update_head_state` / `clear_head_state` (`liquid_handler.py:262-287`):
```python
def update_head_state(self, state):
    for channel, tip in state.items():
      if tip is None:
        if self.head[channel].has_tip:
          self.head[channel].remove_tip()      # <-- commit defaults to False
      else:
        if self.head[channel].has_tip:
          self.head[channel].remove_tip()      # <-- commit defaults to False
        self.head[channel].add_tip(tip)         # <-- commit defaults to True
```
`TipTracker.remove_tip(self, commit: bool = False)` (`tip_tracker.py:100`) — the *default* is `False`, unlike `pick_up_tips`/`drop_tips`, which always explicitly commit-or-rollback (`liquid_handler.py:570-573`, `:716-723`). `update_head_state`/`clear_head_state` are public `LiquidHandler` methods, not gated by `does_tip_tracking()`, and any `lh.<name>(...)` call — regardless of method name — is extracted as an `OperationNode` by the real extractor's `visit_Call` (`computation_graph_extractor.py:456-467`, which gates only on `_infer_machine_type(receiver_name)`, never on `method_name`). `derived_contracts.json`'s `LiquidHandler.update_head_state` entry confirms its own `guards` list has exactly one unrelated assert; the `remove_tip`/`add_tip` calls are dropped calls, i.e. exactly the shape §10.2.5's bridge is built to pick up.

**Counterexample graph:**
```
op_0: lh.pick_up_tips(tip_spots=[ts0], use_channels=[0])   # real+abstract: HAS_TIP (both _tip, _pending_tip committed)
op_1: lh.clear_head_state()                                  # real: _pending_tip -> None, _tip UNCHANGED (still non-None)
op_2: lh.aspirate(resources=[r0], use_channels=[0])
```
Real PLR: `op_2`'s `self.head[0].get_tip()` (`liquid_handler.py:974`) reads `_tip`, which was never cleared — **no exception, aspirate succeeds.** Per the increment's own mechanical rules, `update_head_state`'s depth-0 bridge to `TipTracker.remove_tip` (P4 effect NO_TIP) makes `σ'.exact[0] = NO_TIP` after `op_1` (E2); `op_2`'s bridged `NoTipError` guard (`self._tip is None`) then evaluates `NullCheck(is_none=True)` under `NO_TIP` → **T** → **`Verdict.WILL_FAIL`** is emitted for an operation that actually runs clean. This is precisely the row AC-10.11/AC-10.12's oracle gate is built to catch — it would fail it.

**What must change:** §10.2.2's A-COMMIT justification needs to be withdrawn or narrowed to name the exact set of methods it holds for, and the evaluator needs either (a) to track `_tip`/`_pending_tip` as two cells and only emit a verdict when they agree, or (b) to exclude `update_head_state`/`clear_head_state`/any method whose committing write isn't paired from ever contributing an E2 effect.

---

### O2 — BLOCKER (implementability + latent unsoundness). E2/P4 has no rule for a method with two conflicting depth-0 bridges

**Location:** §10.2.4 (P4 effects, lines 258–271: "writes of both kinds → no effect"); §10.4 E2/E4 (lines 487–496).

**Evidence:** `update_head_state`'s own body (see O1) contains, at depth 0, a bridge to `TipTracker.remove_tip` (NO_TIP effect) **and**, in the other branch, a bridge to `TipTracker.add_tip` (HAS_TIP effect). §10.2.4's "both-kinds-unknown → no effect" rule is defined for a *class's own* direct field writes; it is never restated for the *bridge* mechanism. §10.4's E2 is written in the singular and E4's trigger conditions do not cover this case.

**What must change:** an explicit rule for "K's own body contains ≥2 depth-0 bridges with disagreeing P4 effects" — most likely "no effect / widen".

---

### O3 — BLOCKER (derivability claim is false; AC is unsatisfiable as stated). `tip_state_exceptions` is not `{HasTipError, NoTipError}`

**Location:** §10.2.5 lines 323–329; AC-10.9 (lines 655–663).

**Evidence:** `grep -c '"category": "tip_state"' training/verify/data/plr_exception_taxonomy.json` → **5**, not 2: `HamiltonNoTipError` (STAR_backend.py:361), `HasTipError` (errors.py:16), `NoTipError` (errors.py:20), `TipAlreadyFittedError` (STAR_backend.py:351), `TipTooLittleVolumeError` (STAR_backend.py:340). None of the five entries carries any additional field the stated rule could use to narrow the set back to two.

**What must change:** either an additional DERIVED filter (e.g. `module == "pylabrobot.resources.errors"`, or "reachable as a `raises` value from a `LiquidHandler`/`TipTracker` guard") specified and justified, or AC-10.9's asserted value changed to the real 5-element set with an argument for why the 3 backend-specific members are harmless.

---

### O4 — MAJOR (self-contradiction). The depth-0-only effect rule and its own "Expected" table disagree

**Location:** §10.2.6 normative fix (lines 369–379) vs. lines 362–364 ("tip-dropping(K) … Expected: drop_tips …, and by delegation discard_tips, return_tips").

**Evidence:** `return_tips` (`liquid_handler.py:728-781`) and `discard_tips` (`:783-839`) both reach `TipTracker.remove_tip` **only** via `self.drop_tips(...)` — a resolved `delegates_to` hop, depth 1 (`derive/__init__.py:390-403`). Structurally identical to `move_tips` (`:841-869`), which the same fix says must widen (E4). No rule distinguishes single-hop passthrough from composition. Corroborating: `computation_graph_extractor.py:80-84`'s hand-typed `TIPS_DROPPING_METHODS = {"drop_tips", "drop_tips96", "return_tips"}` includes `return_tips` but excludes `discard_tips`, despite structural identity.

**What must change:** drop the "by delegation" expectation (accept widening) or specify the single-hop-passthrough rule and prove it does not fire for `move_tips`.

---

### O5 — MAJOR (implementability). HM-21's ratchet measure cannot see the second new mirror field

**Location:** §10.8 lines 723–746.

**Evidence:** `_hand_maintained.py:212-215` `_measure_hm21` sums `OperationNode` + `ResourceNode` fields only; `execution_order` lives on `ProtocolComputationGraph`. Adding `arguments` moves the live count 8 → 9, not 8 → 10; the claimed ratchet trigger will not fire.

**What must change:** #4888's task row must include modifying `_measure_hm21` to count `ProtocolComputationGraph` fields.

---

### O6 — MINOR. §10.3.2's "meet" is the already-defined join, mislabeled

The per-channel fold ("NO_TIP if all NO_TIP, HAS_TIP if all HAS_TIP, TOP otherwise") computes `⊔` from §10.1.1's table; there is no meet for incomparable atoms without ⊥. Rename or correct the prose.

### O7 — MINOR. §10.6.2's worked example miscounts "other guards"

`aspirate` has 9 own guards, all non-tip-state, plus 1 bridged SAFE finding → 9 others remain UNKNOWN, not 8.

### O8 — MINOR. AC-10.9's "grep" framing understates the mechanism

Excluding docstrings/comments requires an AST literal scan (as `test_reason_vocabulary_closed_forward` does, `test_verdict.py:318-355`), not `grep`.

### O9 — MINOR. `use_channels` is a sync context manager

`liquid_handler.py:1363` is `@contextlib.contextmanager`, not async.

---

### Open questions (§10.10) — adjudicated

- **Q1 (A-COMMIT):** real gap, substantiated — see O1.
- **Q2 (assert-kind atom):** drop the unexercised row.
- **Q3 (tier-1 vacuity):** AC-10.11's own text should disclose it is currently vacuous under tier 1.
- **Q4:** one reason member is fine. **Q5:** sound, imprecise, fine. **Q6:** defer.
- **Q7:** lean toward splitting pattern 1 (bridge shape) into its own row — its failure profile (silent family collapse) differs from patterns 4–6 (caught by exact-count ACs).

## Verdict

**not_ready.** Single most important fix: O1 — either narrow A-COMMIT with a proof over the whole PLR surface, or track `_tip`/`_pending_tip` as two cells that only jointly commit to a verdict when they agree.
