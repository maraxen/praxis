---
title: 'plr-sema SEMA-IR increment — adversarial round 1, defender'
description: 'Defender adjudication of the round-1 challenger on the spec_version 10 SEMA-IR increment: O1 CONCEDE (synthetic LOOP ⊤ region when has_loops and no LOOP emitted; AC-11.11/11.13 fixture-only until extract/ populates foreach/branch fields), O2 CONCEDE (named X-disposition pin test), O3 CONCEDE (per-method forbidden set + fallback), O4/O5 PARTIAL (disclosure sentences); core survives; extract/ population is a named blocking follow-up.'
status: final
task_id: 260902_sema-oracle-tipstate
date: '260902'
confidence: high
sources: 'praxia:spec-defender (claude-sonnet-5); code read directly; challenger report 260902_plr-sema-ir-round1-challenger.md'
---
# plr-sema SEMA-IR increment — adversarial round 1, defender

Target `.praxia/docs/specs/260902_plr-sema-ir-bytecode-increment.md` at `e1af9f14`; challenger at
`260902_plr-sema-ir-round1-challenger.md`. Verbatim defense.

---

**O1 — CONCEDE (design, minimal — one paragraph + AC qualifier).** Confirmed: the `OperationNode` constructor (`computation_graph_extractor.py:501-512`) passes none of `foreach_source/foreach_body/condition_expr/true_branch/false_branch`; `visit_For`/`visit_While`/`visit_If` (`:376-389`) only flip `_has_loops`/`_has_conditionals` and return `True`. Increment 9 §10.5 rule 2 (`260902_plr-sema-tip-typestate-increment.md:662-666`) widens on `foreach_source`/`foreach_body` — never on `has_loops`; §11.1.4's `has_loops` cross-check only emits an inert `WIDEN has_loops` record not tied to per-receiver widening. The counterexample is real (`rack[0:1]` does not match `_parameter_names`, so `depends_on_params` stays empty — nothing widens the call). **Correction to the framing:** today's walk evaluates loop bodies straight-line, so a global has_loops widen is a strict improvement, not a regression. Option (b) contradicts §11.11's `extract/` round-2 exclusion. Fix: (i) qualify AC-11.11/AC-11.13's LOOP/BRANCH guarantees as fixture-only until `extract/` populates the fields; (ii) when `has_loops=True` and zero real `LOOP` regions are emitted, wrap the whole stream in a synthetic `LOOP ⊤` region, reusing §11.1.3's BRANCH-style "widen every receiver mentioned anywhere in the region, at entry" mechanic.

**O2 — CONCEDE (text-only — one named test).** `_findings_for_operation` (`check/__init__.py:293-321`) never reads `op.preconditions`, `op.creates_state`, or `graph.preconditions`; AC-11.1 is key-set equality; AC-11.2 read live off `DISPOSITIONS` is vacuous; HM-21's X-count decreases on laundering. Fix: one named test asserting the three identities carry `X`, independent of AC-11.1/11.2/11.6 — the legitimate hardcode the document itself uses elsewhere (AC-11.5's directional `tip_spots`-is-`Seq`).

**O3 — CONCEDE (text-only).** `param_namespace.py:144-146` (`aspirate`: `_sym("source", "resources", …)`) puts `"source"` in the global set; `:155-156` (`transfer`: `_sym("source", "source", …)`) and `dispatcher.py:151-153` make it legitimate for `transfer`. Fix: `forbidden(method) = {s.name for s in params_of(method) if s.plr_arg != s.name}` per caveat (i); for methods absent from `PARAM_NAMESPACE` (e.g. `pick_up_tips96`, `param_namespace.py:252-267`) forbidden = ∅.

**O4 — PARTIAL.** REBUT the evidence: the References corpus row (`"source":"plate_1.C7"`) is tool-call JSON consumed by `lower_calls`/`ground_param` (`training/verify/grounding.py:100`), never `ast.parse`d — wrong lowering path. CONCEDE the general point: §11.2.1 has no `ast.Attribute` rule, and `visit_Assign` (`computation_graph_extractor.py:395`) never registers `self.foo` assignments as `ResourceNode`s, so a grammar extension alone would still resolve to `Top` (no slot exists). PLR's `ItemizedResource` exposes only `__getitem__` (no `__getattr__` cell access), so a valid renderer emits `plate_1["C7"]` — the cell-access half is unlikely to materialise; the `self.foo`-resource half is real but latent until `extract/` round 2. Fix: one disclosure sentence naming the case as an acknowledged `Top`, and amend §11.10's divergence-cause claim to three causes (extractor, renderer, `lower_graph` grammar gap).

**O5 — PARTIAL.** REBUT the "arbitrary" framing (same reviewer-judged pattern as HM-21's redefinition); CONCEDE that the 10% figure floats free of the main spec's RISK-5 (`260901_plr-sema-pre-corpus-spec.md:1385`, browser download size for Pyodide). Fix: one sentence citing RISK-5 and stating the check is observational, not gating, until a browser-side ceiling is set.

## Severity (post-defense)

| id | pre | post | fix |
|---|---|---|---|
| O1 | BLOCKER | CONCEDE (blocking) | design, 1 paragraph + AC qualifier |
| O2 | BLOCKER | CONCEDE (blocking) | 1 named test |
| O3 | MAJOR | CONCEDE | snippet + 1 sentence |
| O4 | MAJOR | PARTIAL | 1–2 sentences |
| O5 | MINOR | PARTIAL | 1 sentence |

## Convergence judgment

Core survives — opcode set, value grammar, disposition-table structure, both lowerings, canonical hash, `check_ir` — every concession is text, a snippet correction, or one named test. Before #4888 starts: O1's synthetic-`LOOP ⊤` stopgap + fixture-only qualifiers; O2's pin test; O3's per-method `forbidden()`; O4's disclosure + §11.10 amendment; O5's RISK-5 tie-in. **The real unresolved debt is O1's root cause — `extract/` never populating `foreach_*`/`condition_expr` — round-2 scope, but every LOOP/BRANCH-dependent soundness claim in both increments is fixture-only until it lands; track it as a named blocking follow-up.**
