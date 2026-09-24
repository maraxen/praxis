---
title: 'plr-sema SEMA-IR increment — adversarial round 1, challenger'
description: 'Challenger report on .praxia/docs/specs/260902_plr-sema-ir-bytecode-increment.md (spec_version 10 draft, e1af9f14): O1 BLOCKER the extractor never populates foreach_*/branch fields so LOOP/BRANCH regions are unreachable and loop bodies are treated as executing once (false-SAFE counterexample); O2 BLOCKER no test pins the three X-disposition fields; O3/O4 MAJOR the two lowerings disagree (global forbidden set; attribute-style references fall to Top); O5 MINOR; verdict not implementable until O1/O2.'
status: final
task_id: 260902_sema-oracle-tipstate
date: '260902'
confidence: high
sources: 'praxia:spec-challenger (claude-sonnet-5); code read directly (extractor, models, dispatcher, param_namespace, plr_preconditions.json, PLR pin dd79c4c89)'
---
# plr-sema SEMA-IR increment — adversarial round 1, challenger

Target: `.praxia/docs/specs/260902_plr-sema-ir-bytecode-increment.md` at `e1af9f14`. Verbatim report.

---

### O1 — BLOCKER — soundness: LOOP regions are unreachable from both real lowering paths; loop-body re-execution is silently unsound

**Location:** §11.1.3 (lines 114–151), §11.1.4's `foreach_source`/`foreach_body` disposition row (186–187), §11.9 item 2 (696–700).

**Issue:** `foreach_source`, `foreach_body`, `condition_expr`, `true_branch`, `false_branch` are declared on `OperationNode` (`models.py:551-559`) but are **never written anywhere** in the extractor. `visit_Call` (`computation_graph_extractor.py:456-517`) constructs every `OperationNode` without these kwargs (constructor at `:501-512`); `visit_For`/`visit_While`/`visit_If` (`:376-389`) only flip the graph-level `_has_loops`/`_has_conditionals` booleans and return `True`, so calls inside a loop or `if` body are visited like top-level calls — one `OperationNode` per syntactic `Call`, appended once. Grep confirms the five names appear nowhere outside `models.py` in the package. `lower_calls`'s corpus input (§11.2.2) is a flat sequence with no loop/branch structure; `verifier.py:47-55` never represents repetition either.

So **`LOOP`/`BRANCH` instructions can never be emitted from either real lowering path today** — structurally never. Increment 9 §10.5 already documents this (`260902_plr-sema-tip-typestate-increment.md:679-680`) and its rule 2 fires only when `foreach_*` is populated — which is never.

**Counterexample (false SAFE):**
```python
def protocol(lh, tip_racks, plate):
    for rack in tip_racks:
        lh.pick_up_tips(rack[0:1])   # same channel each iteration, never dropped
        lh.aspirate(plate["A1"], 50)
```
One `pick_up_tips` `Call` node syntactically → one `CALL` instruction. Iteration ≥2 raises `HasTipError` (`liquid_handler.py:534-535`). The checker evaluates the single `CALL` once against the pre-loop state and reports SAFE/UNKNOWN — never WILL_FAIL.

**What must change:** (a) state that AC-11.11/AC-11.13's LOOP/BRANCH guarantees are fixture-only and carry zero soundness claim over real data until `extract/` populates these fields, and add a stopgap: widen **every receiver mentioned anywhere in the graph** whenever `has_loops=True` but the stream contains zero `LOOP` regions (not an inert pc-0 `WIDEN`); or (b) make populating these fields a prerequisite of this increment.

---

### O2 — BLOCKER — derivability/AC-satisfiability: nothing pins which fields must carry disposition X

**Location:** §11.1.4 lines 183–184, AC-11.1 (585–592), AC-11.2 (593–599), §11.6 HM-21 redefinition (553–577).

**Issue:** AC-11.1 asserts `set(DISPOSITIONS[M]) == set(M.model_fields)` — key-set equality only. A table that reclassified `OperationNode.preconditions`/`creates_state` and `ProtocolComputationGraph.preconditions` from `X` to `I` (laundering the hand-typed `TIPS_*` sets into `CALL.kwargs`) passes AC-11.1. AC-11.2's prose does not say whether the test hardcodes the three names or reads them from `DISPOSITIONS` (in which case reclassification silently redefines the check). AC-11.6 cannot catch it: `_findings_for_operation` (`check/__init__.py:293-321`) never reads `op.preconditions`/`op.creates_state`, so findings stay bit-identical. HM-21's new metric counts X fields; moving a field out of X *decreases* the count, which the ratchet reads as safe.

**What must change:** one explicit named test, independent of AC-11.1/11.2/11.6, hardcoding the three field identities that must never carry `I`/`W`/`S` — the one place where hardcoding is correct, because it is the thing the laundering argument depends on.

---

### O3 — MAJOR — AC-11.5's pinning code contradicts its own scoping caveat

**Location:** §11.2.3 lines 304–322 (`forbidden = {...}` at 306–309 vs caveat (i) at 317–320).

**Issue:** The code computes one **global** forbidden set across every tool in `PARAM_NAMESPACE`; caveat (i) says the intersection is scoped per method. `param_namespace.py:145-146` puts `"source"` into the global set via `aspirate`'s `_sym("source", "resources", ...)`, while `transfer`'s `_sym("source", "source", ...)` (`:156`) and `dispatcher.py:151-153` make `"source"` a legitimate `transfer` kwarg → false positive.

**What must change:** per-method derivation `forbidden(method) = {s.name for s in params_of(method) if s.plr_arg != s.name}`, plus the fallback for methods with no `PARAM_NAMESPACE` entry (e.g. `pick_up_tips96`).

---

### O4 — MAJOR — `lower_graph`'s value grammar has no rule for attribute-style resource references

**Location:** §11.2.1 lines 256–265; §11.2.2 lines 278–279; References lines 828–831.

**Issue:** The grammar recognises literal, `List`/`Tuple`, `Name`, and `Subscript` of a `Name`; `Attribute` (`plate_1.C7`) and `Subscript` of an `Attribute` (`self.plate_1["A1"]`) fall to `Top`, while `lower_calls`'s `ir_value_of` resolves the same reference to `Ref` from the grounded object. The References section's own corpus row uses `"source":"plate_1.C7"`. `_get_receiver_info` (`computation_graph_extractor.py:355-374`) handles chained receivers, but `visit_Assign` (`:395`, `isinstance(target.target, cst.Name)`) never registers `self.foo` assignments as `ResourceNode`s. Contradicts §11.10's "divergence can only be an extractor or renderer defect".

**What must change:** extend the grammar to resolve `Attribute` bases recursively against declared resources, or name attribute references as an acknowledged `Top` + `WIDEN` precision loss.

---

### O5 — MINOR — the 10% payload-cost check has no defined consequence

**Location:** §11.2.4 lines 353–355. Reporting obligation, not a gate. Probe: is there a real downstream ceiling (browser payload, Pyodide fetch) or is this observational?

---

### Open-question adjudications (§11.12)

Q1 non-issue (AC-11.7 asserts the bijection). Q2 non-issue (no in-place editing yet). Q3 genuinely open, non-blocking. **Q4 real gap, subsumed by O2.** Q5 non-issue (signature already commits to `lower_graph`). **Q6 reinforces O1**: `has_loops` disagrees with the stream on every real protocol with a `for`, so the WIDEN fires near-universally and widens no receiver — an inert safety net exactly where O1 needs a real one. Q7 real, correctly deferred.

### Verdict

Implementable as written: **no**, not before O1 and O2. O3/O4 are one-paragraph fixes. Single most important fix: make the `has_loops`/no-`LOOP`-region mismatch widen every receiver in the graph, and add the AC-11.1-independent X-disposition pin.

Audit also persisted at `.praxia/audits.jsonl` (`audit_id: 260902_sema-oracle-tipstate_spec-challenger`).
