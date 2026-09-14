---
title: 'plr-sema tip-typestate increment — adversarial round 1, defender'
description: 'Defender adjudication of the round-1 challenger report on the spec_version 9 tip-typestate increment: O1 PARTIAL (counterexample does not reproduce under depth semantics; A-COMMIT text must narrow), O2 CONCEDE sharpened (conflicting depth-0 bridges must WIDEN — "no effect" is unsound), O3 CONCEDE (module filter on the taxonomy artifact), O4/O5 CONCEDE, O6–O9 trivial; 2 blockers survive, all text-only; verdict needs_revision, design intact.'
status: final
task_id: 260902_sema-oracle-tipstate
date: '260902'
confidence: high
sources: 'praxia:spec-defender (claude-sonnet-5), code and PLR pin dd79c4c89 read directly; challenger report 260902_plr-sema-tip-typestate-round1-challenger.md'
---
# plr-sema tip-typestate increment — adversarial round 1, defender

Target: `.praxia/docs/specs/260902_plr-sema-tip-typestate-increment.md` at `ca54866d`; challenger
report at `260902_plr-sema-tip-typestate-round1-challenger.md`. Verbatim defense follows.

---

## Per-objection verdicts

**O1 — PARTIAL.** The literal counterexample doesn't reproduce. `op_1: lh.clear_head_state()` calls `self.update_head_state(...)` — a `self.<name>` call, i.e. a `delegates_to` hop, not a `dropped_calls` entry (§10.2.5's own distinction, corroborated by `derive/__init__.py:400-403`'s `frontier.append((resolved, depth+1))`). `InlinedGuard.depth`'s docstring: `depth: int # 0 = own body, >0 = inlined from a delegate` (`derive/__init__.py:426`). So the `self.head[channel].remove_tip()`/`add_tip()` calls inside `update_head_state`'s body sit at **depth 1 relative to `clear_head_state`**. §10.2.6's normative fix says exactly this shape gets **E4 (widen)** — the rule already covering `move_tips`. `op_2` (`aspirate`) therefore evaluates under `TOP`: ½ → `UNKNOWN`, not `WILL_FAIL`.
Concession: §10.2.2's blanket A-COMMIT claim is still literally false for `update_head_state`/`clear_head_state` (`remove_tip(commit=False)` default, `tip_tracker.py:100`; no subsequent `commit()` in `liquid_handler.py:262-282`) — narrow it to the two methods it is verified for. Text-only.
The real risk is a *direct* `lh.update_head_state(...)` call, which does have a depth-0 conflict — that is O2.

**O2 — CONCEDE (blocker stands, text-only fix).** Confirmed: nothing addresses a K whose own body has ≥2 depth-0 bridges to disagreeing effects — `update_head_state` (`liquid_handler.py:276-282`) is exactly this shape. Sharper than the challenger's framing: **"no effect" is unsound**, not just imprecise. Trace: `pick_up_tips(ch=0)` [HAS_TIP] → `update_head_state({0: None})` [under "no effect", σ stays HAS_TIP] → `pick_up_tips(ch=0)` again. `pick_up_tips`'s guard `self.head[channel].has_tip` (`liquid_handler.py:534`) reads `_pending_tip` (`tip_tracker.py:53-55`), which **was** cleared by `remove_tip()` even with `commit=False` (`tip_tracker.py:106`) — the second `pick_up_tips` succeeds. Under "no effect": `BoolView` = T → false `WILL_FAIL`. Only **widen (E4)** is sound. Minimal fix: one sentence in §10.2.4/§10.4 — "K's own body with ≥2 depth-0 bridges to disagreeing P4 effects triggers E4, never E2."

**O3 — CONCEDE (blocker stands, text-only fix).** 5 `tip_state` members confirmed (`HamiltonNoTipError`, `HasTipError`, `NoTipError`, `TipAlreadyFittedError`, `TipTooLittleVolumeError`). Verified fix: `module == "pylabrobot.resources.errors"` narrows to exactly `{HasTipError, NoTipError}`; the 3 Hamilton members carry `module: "pylabrobot.liquid_handling.backends.hamilton.STAR_backend"`. Also verified harmless today: no guard in `derived_contracts.json` raises any of the three (`kind: "dispatch_table"` entries only). Recommend the module filter over "reachable-from-guard" — simpler, does not couple to the derived table's current emptiness, field already exists in the artifact (still DERIVED).

**O4 — CONCEDE (major stands, text-only, conservative option).** `return_tips` (`liquid_handler.py:775-781`) and `discard_tips` (`:833-839`) reach `remove_tip` only via `self.drop_tips(...)`, depth 1 — structurally identical to `move_tips` (`:862-869`). Strike "by delegation discard_tips, return_tips" from §10.2.6's Expected list; they widen like `move_tips`. A single-hop-passthrough rule is possible but is new machinery — follow-up, not this increment.

**O5 — CONCEDE (major stands, text + one code line).** `_measure_hm21` (`_hand_maintained.py:212-215`) counts `OperationNode` + `ResourceNode` only; `execution_order` lands on `ProtocolComputationGraph`. 8→9, not 8→10. Task #4888 needs an explicit line: extend `_measure_hm21` to count `ProtocolComputationGraph` fields.

**O6–O9 — CONCEDE (trivial).** §10.3.2 "meet" is `⊔` folded over a set — one word. §10.6.2 "eight" → nine. AC-10.9 "grep" → AST literal scan as `test_reason_vocabulary_closed_forward` does (`test_verdict.py:318-355`). `use_channels` at `liquid_handler.py:1363` is `@contextlib.contextmanager` (sync).

## Post-defense severity

| id | original | post-defense | fix scope |
|---|---|---|---|
| O1 | BLOCKER | downgraded → folds into O2 (A-COMMIT narrowing) | text |
| O2 | BLOCKER | **survives**, sharpened (widen-only) | text (reuses E4) |
| O3 | BLOCKER | **survives** | text (module filter, existing field) |
| O4 | MAJOR | survives | text |
| O5 | MAJOR | survives | text + 1 code line in #4888 |
| O6–O9 | MINOR | survive | 1 word / clause each |

**Blockers surviving: 2 (O2, O3).** Both close with targeted text that reuses machinery already in the increment.

## Convergence judgment

**needs_revision** — not a rewrite, not new recon. Core design (per-channel typestate lattice, dropped-receiver channel bridge, depth-0-only effect/widen split, execution-order walk, per-guard findings) intact. Revise §10.2.2, §10.2.4/§10.4, §10.2.5, §10.2.6, §10.8, then re-gate with the two mechanical checkers.
