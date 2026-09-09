---
title: "plr-sema — pre-corpus specification (round 6 + T11 whole-surface decoupling + three open decisions resolved)"
description: "Buildable-today specification for plr-sema: a self-contained package providing preflight (pre-execution) sound static validation of PyLabRobot execution graphs. Covers the eight corpus-INDEPENDENT sections (package seam + AST import boundary, provenance cherry-pick, tri-valued verdict data contract, telemetry error model, fork-drift tests, extractor/checker split, contract-derivation mechanics, differential harness) and defers all abstract-interpretation semantics to a literature corpus in compilation. Carries a mandatory hand-maintained/derived classification on every piece of logic, plus a hand-maintained surface budget and ratchet. spec_version 7 (T11) decouples derivation coverage from SUPPORTED_TOOLS: plr-sema now analyzes the whole PyLabRobot surface (4,770 methods) rather than 10 LiquidHandler tools. spec_version 8 (260901, task 260901_plr-jit-resolve-three-decisions) resolves all three §Open decisions items via an independent outside analysis (Fable), spot-verified by the orchestrator: no `UNREACHABLE` member now (reserve the string, add an unrecognized-verdict-string consumer rule instead); volume tracking is already in the verdict path (PLR put it there), the real question — whether the predicate evaluator interprets numeric atoms — is deferred through v1 and the first increment; the shipped join table is NOT inverted, its ordering is the correct obligation-conjunction order, distinct from the (unrelated) information order that governs pre-emission state merging. No schema_version bump; no new machinery."
status: draft
spec_version: 8
task_id: 260901_plr_jit_spec
date: '260901'
confidence: medium
sources: "Measured substrate supplied in dispatch brief (praxis/backend/utils/plr_static_analysis 5868 LOC; praxis/backend/core/simulation 11 modules; coxswain/src/coxswain/fft/preconditions live fork; training/verify execution oracle; scripts/survey_plr_*.py + training/verify/data/*.json). Independently re-read this session: /home/marielle/projects/cisternal/src/cisternal/telemetry/git_state.py; training/verify/failure_taxonomy.py; scripts/plr_survey_common.py; scripts/survey_plr_preconditions.py; coxswain/tests/test_import_boundary.py; coxswain/tests/test_sim_port.py; coxswain/pyproject.toml; pyproject.toml; praxis/common/type_inspection.py; praxis/backend/models/enums/plr_category.py; praxis/backend/utils/plr_static_analysis/models.py:520-661."
---

# Specification: plr-sema, pre-corpus (round 6)

> **Renamed 260902 (twice):** `plr-jit` → `plr-preflight` → `plr-sema`. "JIT" named a mechanism that never
> existed; "preflight" named only the pre-execution moment and excluded the error-recovery and
> graph-validity work this substrate is meant to carry. `plr-sema` names what it is: the semantic-analysis
> pass over PLR programs (import `plr_sema`). Historical task_ids (`260901_plr-jit-*`, `260901_plr_jit_spec`,
> `260902_preflight-*`) are identifiers and keep their names deliberately.

> **Round 6 of an adversarial convergence cycle** (spec → challenger → defender → remediation → repeat)
> — the **convergence pass**. Round 5 was chartered to de-anchor and closed with 0 CONCEDE-in-full at
> BLOCKER/MAJOR · 5 PARTIAL · 2 REBUT · 1 CONCEDE (minor) (see
> [§Remediation changelog (round 4 → round 5)](#remediation-changelog-round-4--round-5)). **Round 6
> reviewed the document itself for internal coherence and cold-start executability** rather than
> hunting new design defects, and found **zero design errors and zero contradictions with prior
> adjudications** — every one of its 20 findings was stale text, incomplete propagation of an already-
> landed remediation, or a bookkeeping omission. 14 CONCEDE, 6 PARTIAL, 0 REBUT; post-defense severity
> 1 BLOCKER · 9 MAJOR · 10 MINOR — see
> [§Remediation changelog (round 5 → round 6)](#remediation-changelog-round-5--round-6) for the full
> record. **Round 7 was deliberately not run**: the defender's convergence judgment (reproduced in that
> changelog) is that the remaining defect class — stale line citations, off-by-one AC ranges, a
> changelog claiming a body edit it only half made — is exactly the kind a ~30-line citation-anchor
> checker and a cross-reference lint catch mechanically, not the kind a seventh adversarial round finds
> reliably. All five prior rounds' changelogs are kept intact below this one. This revision remains
> deliberately *narrow*: it specifies only what is buildable without answers from the
> abstract-interpretation / typestate literature corpus currently being compiled. Six semantic questions
> are named in [§Deferred](#deferred) and specified **nowhere**. **Three further decisions are open and
> pending the user** — see [§Open decisions](#open-decisions) immediately below.

---

## Open decisions

**RESOLVED 260901 (task `260901_plr-jit-resolve-three-decisions`).** All three decisions below were
recorded by round 6 (R14) as genuinely pending with the user and gating T10's dispatch. They are kept
in full, not deleted, so a reader can see they *were* open and how they closed — history, not a live
gate. Resolution source: an independent outside analysis (Fable, no prior contact with the spec
rounds — full text at `fable_three_decisions.md`), spot-verified against the codebase by the
orchestrator before being accepted as authoritative (verification evidence is inline in each
resolution below). **User-approved.** The unifying move that dissolves two of the three is recorded as
a new paragraph in [§3](#3-the-verdict-type-and-record-shape--the-hinge), immediately before §3.1:
`Verdict` is the *output* of evaluating one obligation against one abstract state, not the abstract
domain itself. Once that is accepted as the organizing fact (rather than left implicit), decisions 1
and 3 stop being open questions about `Verdict`'s design and become one clarifying docstring change
each; decision 2 was never actually about `Verdict` at all.

1. **Does `Verdict` gain a fourth, `UNREACHABLE` member now? — No, not now.** ⊥ (bottom/unreachable) is
   needed by the analyzer's internal per-operation abstract-state lattice that deferred item (a) will
   build — it prunes dead paths (`⟦C⟧♯(⊥) = ⊥`) and is the unit of the branch-merge join. Neither of
   those is a thing the wire type needs to say to a consumer: a provably-dead operation is either a
   vacuous `SAFE` ("cannot fail because it never runs" — literally satisfied by `Verdict.SAFE`'s own
   docstring) or a lint/annotation, not a fourth verdict. Adding the member now would also require
   deciding its row in the §3.2 table — vacuous `SAFE` under the conjunction unit, or ⊥ strictly below
   `SAFE` under the information order — with no domain yet built to check that decision against; that
   is exactly the kind of call that is 50/50 in foresight and obvious only in hindsight. **Instead:**
   the wire string `"unreachable"` is reserved (comment in `verdict.py`, not consumed anywhere), and one
   new normative consumer rule is added: **an unrecognized `Verdict` string deserializes to `UNKNOWN`.**
   Widening what a consumer knows is always sound (it can only lose precision, never gain a false
   claim), so this makes `UNREACHABLE` — or any future member (a) needs — a non-breaking addition for
   compliant consumers, without committing to `UNREACHABLE`'s semantics today. Implemented as
   `Verdict.from_wire(value: str) -> Verdict` in `plr_sema/verdict.py`, tested in
   `test_verdict.py::test_from_wire_maps_unrecognized_string_to_unknown`.
   **Corrects §3.5's schema-bump direction, which had it backwards for an additive enum member:** for
   an *additive* enum member, only *old* readers choke on *new* reports; new readers already accept old
   reports as a strict subset. §3.5's
   claim that a bump makes "every persisted report unreadable by the new checker" describes the
   opposite direction. The migration cost is also not live today regardless of direction: zero
   consumers outside `plr-sema/tests` import `plr_sema.verdict` or read a report `schema_version`
   (re-verified this pass), and zero `AnalysisReport`s are persisted anywhere in the repo. See the
   corrected §3.5 text below.
2. **Is volume tracking in the v1 verdict path? — The question was mis-posed; restated below, and the
   restated question resolves to "leave numeric atoms uninterpreted through v1 and the first
   post-corpus increment."** Volume is not a hypothetical the analyzer might someday choose to model —
   PLR's own preconditions are volume-shaped and the derivation pipeline already carries them as
   guards: `LiquidHandler.drop_tips` (and 9 sibling `LiquidHandler.*` contracts, via delegation) carries
   `tip.tracker.get_used_volume() > 0 and (not allow_nonzero_volume)` at depth 0 today — verified,
   `plr-sema/data/derived_contracts.json`; the whole-surface table carries 257 volume/liquid-shaped
   guards across 93 methods. So "is volume in the verdict path" is already true, and answerable by
   `grep`, not judgment. **The actual open question was:** does deferred item (c)'s predicate evaluator
   *interpret* numeric comparison atoms (`Cmp(Expr, op, Expr)`, e.g.
   `volume - self.get_used_volume() > 1e-06`), or leave every such atom at Kleene ½ (`UNKNOWN`)?
   **Resolution: leave numeric atoms at ½ through v1 and the first post-corpus increment.** This is
   additive and fully reversible — it touches one grammar production in (c)'s evaluator and nothing on
   the wire (no `Verdict`, `Finding`, or `join` change), so the option to add interval interpretation
   later is nearly free to keep open. Two facts Fable's analysis established weaken the old
   volume-⟹-widening link the deferred (d) row's framing relied on: (i) upstream `ResourceNode` carries
   `items_x`/`items_y` (verified, `models.py:593-597`), so loops over plate wells have **proved**, not
   heuristically-guessed, trip counts — bounded loops with proved counts need no widening even under an
   interval domain, narrowing "widening is needed" to "the verdict path includes numeric accumulation
   across a loop whose trip count cannot be proved from the graph," a strictly smaller and possibly
   empty condition; (ii) PLR's volume guards are gated by a process-global `does_volume_tracking()` flag
   (verified, `liquid_handler.py:1032-1235`) — an environment hypothesis, not a graph fact — so any
   definite volume verdict needs a `SoundnessScope` record (cross-reference the soundness-fence
   discussion in deferred row (b)/`260901_plr-sema-research-b-f.md`) before it can be honest, which is itself
   post-corpus machinery. The [§Deferred](#deferred) table's (d) row is updated accordingly, below.
3. **Does the `join` lattice ordering invert so `UNKNOWN` is genuinely top? — No; keep the table.** The
   shipped [§3.2 table](#32-the-report-level-join--specified-as-structure-deferred-as-semantics) is the
   correct join of the **obligation order** (`SAFE ⊏ UNKNOWN ⊏ WILL_FAIL`, `WILL_FAIL` top): one
   definite, reachable failure must dominate ninety-nine unknowns, because a protocol with one such
   failure and ninety-nine unknowns *will fail*, and reporting `UNKNOWN` there would discard the one
   thing a user most needs to know. `UNKNOWN`-as-top belongs to a genuinely different, and also real,
   **information order** (Kleene / Sagiv-Reps-Wilhelm: `SAFE ⊔ WILL_FAIL = UNKNOWN`) — but that order
   governs merging *abstract states* at a branch confluence, upstream of `Finding` emission, before any
   guard is evaluated against the merged state. It has no call site in `verdict.py` today and never
   will: `verdict.py`'s `join` conjoins independent per-guard obligations *after* they are already
   `Finding`s. Both orders are real; they apply at different pipeline stages, and the prior framing of
   this as one ordering choice was the actual defect. `verdict.py`'s module docstring and `join`'s own
   docstring are corrected to name both orders explicitly and state which one `join` implements — see
   the source; no table, body, or test assertion changes.
   **A related, more serious correction, recorded prominently so a later round does not resurrect
   it:** `260901_plr-sema-research-a-d.md`'s R3 recommended grouping `join`'s input by `operation_id` and
   Kleene-joining findings within each group. **This must NOT be implemented.** Verified,
   `check/__init__.py`'s `_findings_for_operation`: v1 emits **one `Finding` per guard** in the resolved
   contract (measured: `aspirate` yields 9 findings from 9 distinct guard sites, `transfer` yields 17).
   Two findings sharing one `operation_id` are, today and by construction, two *independent*
   obligations (guard A, guard B) that correctly *conjoin* — if guard B definitely fires the operation
   definitely fails regardless of guard A being provably satisfied. Grouping by `operation_id` and
   Kleene-joining within the group would **mask a definite guard failure whenever a sibling guard on
   the same operation is satisfied** — unsound in the `SAFE` direction. R14/round-4's M9 and
   `260901_plr-sema-research-a-d.md` both had this backwards; do not implement R3 as written, and do not re-raise the
   `operation_id`-grouping shape without first re-deriving why v1's per-guard emission makes it unsound.
   `test_join_absorbs_across_shared_operation_id` (`test_verdict.py`) pins the *correct* per-guard
   conjoining behavior — its docstring previously described itself as pinning a case research flags as
   `join`'s absorption logic getting it wrong; that was backwards, and the docstring is corrected below
   (assertions unchanged).

---

## 0. The organizing claim

**The pre-corpus deliverable is a trivially sound analyzer.**

`plr-sema` v1's eight sections are corpus-*independent* plumbing. Wire them all together and you get a
program that walks a protocol's execution graph, attempts contract derivation against real PLR
source, and emits a verdict record for every operation — where **every verdict is `UNKNOWN`**, each
carrying a machine-readable reason naming which derivation step gave up. **Round 1's entry point
ingests a pre-extracted execution graph** (`check_graph`, §6.2) — a program that ingests a protocol
*function* directly (source in, verdict out) is the `@jit`/`check(fn)` capability, which is round 2's
work, not round 1's (D9).

**The concrete invariant that makes "every verdict is `UNKNOWN`" true (round-4 remediation, B1/B2/
§0(ii), fix 5).** Round 1–3 asserted this as a claim about the *pipeline's shape*, without stating the
two code-level facts that actually make it hold: `check/` constructs no `SAFE`/`WILL_FAIL` `Finding`
anywhere (only `UNKNOWN`, per the `_reason_*` constructors in `check/__init__.py`), and
`plr_sema.verdict.join` returns `UNKNOWN` on the empty finding multiset (§3.2, unconditionally as of
this round — see below). Together these two facts, not an appeal to "the corpus hasn't run yet",
are what pin `report.verdict is Verdict.UNKNOWN` for every v1 protocol. Before this round, `join(())`
returned `SAFE` on the empty multiset — a live soundness bug reachable via `check_graph` on a
zero-operation graph, or via any operation whose resolved contract happened to carry zero guards,
zero gaps, and no loop (§6.2, §7.4).

That is a *sound* analyzer (it never claims `SAFE` for something that fails, nor `WILL_FAIL` for
something that succeeds — it claims nothing). It is also a *useless* one. The corpus work converts
`UNKNOWN`s into `SAFE`/`WILL_FAIL`s; the gap ledger (§7.4) measures that conversion.

**"Trivially sound" is a true but weak claim, and round 1–3 let it read as stronger than it is
(round-4 remediation, the §0 "trivially sound" framing objection, PARTIAL — text-only, independent of
B1).** Trivial soundness here means `A(p) = SAFE ⟹ p ⊨ P` with the antecedent false for every `p`
(§0.2's `analyze(op): return UNKNOWN` satisfies the definition) — it carries **zero mathematical
obligation** and gives no evidence about the post-corpus analyzer's actual precision or soundness once
`SAFE`/`WILL_FAIL` verdicts start being emitted. The invariant named just above (`check/` constructs
no `SAFE`/`WILL_FAIL`; `join(())` is `UNKNOWN`) is what makes the *code* actually satisfy this weak
claim today — the claim itself was never in question; what was missing was stating plainly that it is
weak, not an achievement to be proud of.

This framing is what makes the spec buildable without the deferred answers, and it is the single
assumption most worth attacking in round 2. Two consequences:

1. **Every section's acceptance criterion is expressible without an abstract domain.** "Emits
   `UNKNOWN` with reason `unresolved_delegate` for `LiquidHandler.aspirate`" is a testable string
   equality today.
2. **The `UNKNOWN` *reason* vocabulary must be derivation-mechanical, not semantic.** A reason names
   *which pipeline stage returned nothing* (`no_contract_derived`, `unresolved_delegate`,
   `guard_predicate_unparsed`, `loop_bounds_unknown`), never *why the property is undecidable*. The
   latter is deferred item (b); the former is knowable from control flow through our own code. This
   distinction is load-bearing: without it, decision 7's gap-ledger histogram would need a stable key
   set, and a stable key set would be a semantic commitment we are explicitly deferring.

### 0.1 The mandatory classification tag

Every piece of logic introduced below carries **exactly one** tag:

| Tag | Meaning |
|---|---|
| **DERIVED** | Computed from AST/CST inspection of PLR source. The derivation is named at the point of use. |
| **HAND-MAINTAINED** | A human types the fact. Requires: why it cannot be derived, and what breaks when PLR changes underneath it. Every instance gets a row in the registry (§9). |
| **DERIVABLE-NOT-YET** | Hand-typed today, with a *concrete named trigger* that converts it to DERIVED. Also gets a registry row, but counts against a separate, decaying sub-budget. |

**Scope note on decision 2** ("no hand-written method contracts"). Decision 2 bans hand-written
*contract bodies* — a human asserting that `aspirate` requires tips. It does **not** ban
hand-maintained *derivation machinery* (the validator-name prefix list, the effect-type vocabulary,
the exception-module allowlist). The machinery is where essentially all surviving hand-maintained
surface lives, and therefore where the §9 budget applies. Conflating the two makes decision 2 look
either trivially satisfied or impossible; it is neither.

---

## 1. Package seam, compatibility shim, AST import boundary

### 1.1 Interface / data contract

A new uv workspace member, structurally identical to the `coxswain` precedent (verified:
`pyproject.toml:43-45` declares `[tool.uv.workspace] members = ["coxswain", "training"]`).

```
plr-sema/
  pyproject.toml           # name = "plr-sema", requires-python = ">=3.10"
  src/plr_sema/
    __init__.py            # public surface (round 1): check_graph, Verdict, AnalysisReport.
                           # `jit`/`check(fn)` (source→graph, server-side) are ROUND 2 — see §6.2.
    _provenance/           # §2
    verdict.py             # §3
    telemetry.py           # §4
    extract/               # §6 server-side, libcst permitted
    check/                 # §6 browser-side, NO libcst, NO pylabrobot import
    derive/                # §7
    _hand_maintained.py    # §9 registry
  tests/
```

Root `pyproject.toml` gains `"plr-sema"` to `[tool.uv.workspace] members`.

**`plr-sema/pyproject.toml` MUST carry its own `[tool.pytest.ini_options]` with
`addopts = ["--no-cov"]` and `testpaths = ["tests"]`.** Without it the package inherits the root
`addopts` (`pyproject.toml:158-174`), which includes `--cov=praxis`; running pytest inside `plr-sema/`
would report ~0% coverage of `praxis` and hard-fail the moment CI restores `--cov-fail-under`. This
is the exact trap coxswain documents at `coxswain/pyproject.toml:23-28`.

**Round-1 contents: new code only.** Nothing is moved out of `praxis/` in round 1. The package ships
§2 provenance, §3 verdict types, §4 telemetry, §9 registry — all greenfield. Hardening happens
*inside* the seam thereafter.

### 1.2 The shim, and its mandatory direction

> **FLAG — locked decision 1 is implementable in exactly one direction, and the brief does not say
> which.** "A compatibility shim so existing `praxis.*` import sites keep resolving" is
> direction-agnostic. The naive reading — `plr_sema` re-exports from `praxis` — is **structurally
> incompatible with the day-one import-boundary test**, which fails on any `praxis.*` import inside
> the package. The two locked requirements can only both hold if the shim runs
> **praxis → plr_sema**.

**Normative:** the dependency arrow points `praxis → plr_sema`, never the reverse. When a symbol
eventually migrates, the vacated `praxis` module becomes a thin re-export:

```python
# praxis/backend/utils/plr_static_analysis/<mod>.py  (post-migration shim)
from plr_sema.<mod> import *   # noqa: F403  -- compatibility shim, see spec 260901
from plr_sema.<mod> import __all__  # noqa: F401
```

In round 1 there is nothing to shim yet (nothing has moved). The shim *pattern* is specified now so
that round 2's first move cannot accidentally invert the arrow.

**Classification: HAND-MAINTAINED** (one shim module per migrated module). *Why not derived:* a
re-export file is generated text, but which symbols were public at the seam is a judgement about
downstream callers, not a fact in PLR source. *What breaks when PLR changes:* nothing — this surface
is coupled to `praxis`, not to PLR. *Ratchet:* shim modules are counted (registry row HM-16) and the
count must **monotonically decrease** after its peak; each shim is deleted when its callers are
updated.

### 1.3 Verification

Port `coxswain/tests/test_import_boundary.py` (read this session; D20 — the LOC count is deliberately
omitted here after two prior corrections (46 → 61 → 60): "read this session, ported verbatim in
structure" already carries the meaning, and a third hand-count invites a fourth correction) verbatim
in structure, with
`SRC_ROOT` repointed. Its `_iter_imports` helper already handles both `ast.Import` and
`ast.ImportFrom` with `level == 0` guarding, which is the correct treatment (relative imports are not
cross-package).

```bash
uv run pytest plr-sema/tests/test_import_boundary.py -q
```

Four tests, all failing-by-default on violation (round-6 remediation, R12 — was documented as three;
`test_no_verify_or_training_imports_under_src` shipped alongside `test_no_praxis_imports_under_src`
and was never added to this list):

- `test_no_praxis_imports_under_src` — walks every node of every `.py` under `src/plr_sema/`, asserts
  no import whose top-level module is `praxis`.
- `test_no_verify_or_training_imports_under_src` — same walk, asserting no import whose top-level
  module is `verify` or `training` — the second half of §1.2's "no praxis, no training/verify"
  boundary, on the same `ast.walk` as the row above.
- `test_no_pylabrobot_import_under_check` — same walk restricted to `src/plr_sema/check/`, asserting
  no `pylabrobot` and no `libcst` top-level import (§6's packaging fact, mechanised).
- `test_plain_cpython_import_of_public_surface` — subprocess `python -c "import plr_sema"`, asserting
  exit 0.

**Classification of the boundary test itself: DERIVED** — it computes the violation set from the AST
of our own source; no allowlist is typed.

> A deliberate design choice worth challenging: the boundary test is **vacuous on day one** (an
> almost-empty package cannot import `praxis`). That is the point — it is a ratchet installed before
> there is anything to ratchet, which is the only time installing one is free. The alternative
> (add it after the first move) is how the coxswain fork ended up with a `PORT PROVENANCE` header and
> no drift test.

### 1.4 Failure mode if the assumption is wrong

**Assumption:** the two external couplings of `plr_static_analysis` are exactly
`praxis.common.type_inspection` (symbols `is_pylabrobot_resource`, `extract_resource_types`,
`get_element_type`, `is_container_type`, `PLR_RESOURCE_TYPES`) and
`praxis.backend.models.enums.plr_category` (symbol `infer_category_from_name`).

**If wrong:** a later move stalls with an unbounded transitive-dependency tail, and the boundary test
converts that stall into a red test rather than a silent `praxis` import. That is the *desired*
failure mode — loud and early. The measured risk is low but non-zero: the count was taken over
static imports; a function-local `import praxis...` inside a rarely-taken branch would have been
missed by a module-level scan. **Mitigation:** the boundary test walks *every* node
(`ast.walk`), not just module-level body, so it catches function-local imports that the coupling
survey may have missed.

### 1.5 Acceptance criteria

- **AC-1.1** `uv sync` at repo root resolves with `plr-sema` as a workspace member; `uv run python -c
  "import plr_sema"` exits 0.
- **AC-1.2** `uv run pytest plr-sema/tests/test_import_boundary.py -q` passes, and passes **as a
  meaningful test**: a scratch commit adding `import praxis` to any `src/plr_sema/` module makes it
  fail. (Demonstrate once; do not commit the scratch.)
- **AC-1.3** `uv run pytest plr-sema -q` runs without inheriting `--cov=praxis` (assert by observing no
  coverage report in output).
- **AC-1.4** Zero files under `praxis/` are modified by the round-1 task other than root
  `pyproject.toml`'s workspace member list. `git diff --stat` is the check.

---

## 2. Provenance layer

### 2.1 Interface / data contract

Cherry-pick `/home/marielle/projects/cisternal/src/cisternal/telemetry/git_state.py` **verbatim** to
`plr-sema/src/plr_sema/_provenance/git_state.py`, prepending a provenance header (below) and changing
nothing else.

Re-verified this session against the cisternal source:

- **Stdlib-only.** Module-level: `os`, `shutil`, `subprocess`, `tempfile`, `dataclasses`, `pathlib`.
  **`hashlib` is imported function-locally** at `git_state.py:182` inside `_diff_sha256_fallback`.
  A "check module-level imports are stdlib" test would miss it; the §2.3 check must walk all nodes.
- **Zero cisternal-internal imports.** Confirmed by read.
- **Public surface:** `GitState` (frozen slots dataclass) and `capture_git_state(cwd=None, *,
  compute_dirty_content_id=True) -> GitState`. Never raises (`git_state.py:249-251` catch-all
  degrades to the `_UNAVAILABLE` sentinel).
- **Fields:** `hash`, `branch`, `dirty`, `dirty_content_id`, `provenance_source` ∈
  {`git`,`nogit`,`unavailable`}, `toplevel` — exactly as decision 6 specifies.
  `dirty_content_id` is **40-hex** when the primary throwaway-index tree-OID mechanism succeeds
  (`git write-tree`), **64-hex** when it falls back to `_diff_sha256_fallback`
  (`git_state.py:181-195`, sha256), and `None` on a clean tree. The two lengths are not
  interchangeable and callers must not assume 40-hex unconditionally.

**Not accept-dependency**, for the reasons decision 6 records and this session confirms:
cisternal is `requires-python >=3.13`; praxis (`pyproject.toml:11`) and coxswain
(`coxswain/pyproject.toml:11`) are both `>=3.10`; and `cisternal/__init__.py` pulls cyclopts and
`fastmcp==4.0.0a2`.

**Verbatim, not paraphrased.** Two mechanisms are load-bearing and must not be "simplified":

1. **`GIT_DIR` stripping** (`_GIT_REPO_LOCATION_ENV_VARS`, `git_state.py:46-59`). Six env vars
   override `-C <path>` repo discovery. Without stripping, a `plr-sema` survey run from inside a git
   hook stamps the *hook's* repo, not the PLR submodule.
2. **Throwaway-index tree OID** (`_compute_dirty_content_id`, `git_state.py:135-178`). Copies the
   real index to a temp file, `GIT_INDEX_FILE`-overrides it, `git add -A` + `write-tree`, discards.
   This sees unstaged *and* untracked changes without mutating the caller's staging area. The
   `sha256(git diff HEAD)` fallback (`:171-185`) is strictly weaker — it misses untracked files.

The prohibition on paraphrase is not stylistic. Reimplementing "obviously equivalent" security- or
identity-critical code from reading it is precisely the Debian OpenSSL PRNG failure mode: a change
that looked like removing dead code silently collapsed the entropy space.

**Required header (verbatim text, first lines of the file):**

```python
# --- CHERRY-PICK PROVENANCE ------------------------------------------------
# Verbatim copy of cisternal/src/cisternal/telemetry/git_state.py
#   upstream repo:   /home/marielle/projects/cisternal
#   upstream commit: <40-hex SHA at pick time>
#   upstream sha256: <sha256 of the upstream file bytes at pick time>
#   picked:          2026-09-01   license: MIT (same author)
# Copied, not depended on: cisternal is requires-python >=3.13 (praxis/coxswain
# are >=3.10) and cisternal/__init__.py imports cyclopts + fastmcp==4.0.0a2.
# DO NOT EDIT. Drift is enforced by plr-sema/tests/test_provenance_drift.py.
# ---------------------------------------------------------------------------
```

### 2.2 The stamp schema it feeds

`plr_sema._provenance.stamp.survey_stamp() -> SurveyStamp`, a frozen dataclass, superseding the
current `plr_survey_common.plr_version_stamp()` (read this session, `scripts/plr_survey_common.py:52-76`):

| field | source | note |
|---|---|---|
| `plr` | `capture_git_state(external/pylabrobot)` | full `GitState`, replacing today's `{git_sha, git_dirty: bool}` |
| `praxis` | `capture_git_state(repo root)` | the analyzer's own version |
| `pylabrobot_version` | `getattr(pylabrobot, "__version__", None)` | unchanged; installed pkg may differ from submodule checkout |
| `stamped_at` | `datetime.now(timezone.utc).isoformat()` | |
| `schema_version` | literal `1` | |

**Normative — memoization.** `survey_stamp()` is memoized at most once per process (a module-level
cache populated on first call); repeated calls within the same process return the cached
`SurveyStamp` rather than re-invoking `capture_git_state`. A dirty tree's tree-OID computation costs
~8 subprocesses (`_compute_dirty_content_id`), so a `SurveyStamp` is ~16 subprocesses total (`plr` +
`praxis`) if recomputed per call — the memoization is what keeps §4's "every emitted event carries
the full `SurveyStamp`" affordable. `emit` (§4.1) never shells out; it only serializes whatever
`SurveyStamp` object it is handed.

**This is the concrete fix decision 6 buys.** Today `git_dirty` is a `bool`
(`plr_survey_common.py:68`): two different dirty working trees stamp *identically*, so two survey
outputs that disagree are indistinguishable from two runs of the same tree. With
`dirty_content_id`, a dirty tree is content-addressed. This matters immediately and measurably at
the current pin: `external/pylabrobot @ dd79c4c89` has **57 dirty files**, of which **0 are under the
scanned `pylabrobot/` root**. Today that reads as `git_dirty: true` and is unfalsifiable. With a
tree OID it becomes a stable identity that a later run can compare against.

> Note the residual imprecision, which the challenger should press on: `dirty_content_id` covers the
> whole submodule working tree, so an edit to a file *outside* `pylabrobot/` still changes the stamp
> even though it cannot change the survey output. That is over-sensitivity, not unsoundness — it
> causes spurious "inputs changed" signals, never a missed one. A scan-root-scoped content id is a
> possible round-2 refinement; it is not specified here.

### 2.3 Verification

```bash
uv run pytest plr-sema/tests/test_provenance.py -q
```

- `test_git_state_is_stdlib_only` — `ast.walk` (not module-body-only, per the `hashlib` note) over
  the picked file; every imported top-level module ∈ `sys.stdlib_module_names`. **DERIVED.**
- `test_capture_never_raises` — parametrized over: a real repo, `tmp_path` (non-repo → `nogit`), and
  a `PATH`-scrubbed env (→ `unavailable`). Asserts a `GitState` is returned in all three and
  `provenance_source` matches.
- `test_dirty_content_id_distinguishes_trees` — the load-bearing one. In a `tmp_path` git repo:
  capture, write file A, capture, write file B instead, capture. Assert all three
  `dirty_content_id`s differ and the clean one is `None`. **This test fails against the current
  `git_dirty: bool` implementation**, which is the point.
- `test_dirty_content_id_sees_untracked` — add an *untracked* file only; assert
  `dirty_content_id` changes. This is the assertion the `sha256(git diff HEAD)` fallback cannot
  satisfy, so it pins the throwaway-index path specifically.
- `test_git_env_stripping` — `monkeypatch.setenv("GIT_DIR", <unrelated repo path>)` **in the test
  process**, then capture against a known repo and assert the returned `toplevel` is the known repo.
  (Not "in the subprocess env": `_clean_git_env()` (`git_state.py:56-59`) filters the *parent's*
  `os.environ`, and `_run_git` builds the subprocess env from that filtered copy — the test must
  poison the parent process's environment, not the child's, or the mechanism under test never runs.)
  Pins mechanism 1.

**Classification: HAND-MAINTAINED** — the picked file is 241 LOC of human-written code we now own.
*Why not derived:* it is upstream source, by definition. *What breaks when PLR changes:* nothing;
this surface is coupled to `git`'s CLI, not to PLR. *Registry row:* HM-17, metric = LOC, with the
explicit note that it is **frozen** (edits are forbidden by the header and caught by §5's drift
test), so it is a one-time cost, not a growing one.

### 2.4 Failure mode

**Assumption:** the picked file remains stdlib-only and cisternal-import-free across future re-picks.

**If wrong:** a re-pick silently introduces a cisternal or third-party import, breaking
`import plr_sema` in Pyodide and possibly on 3.10. `test_git_state_is_stdlib_only` converts this into
a red test at pick time. **Residual:** the test checks stdlib membership, not 3.10 *availability* —
`sys.stdlib_module_names` is evaluated on the running interpreter. A module that is stdlib on 3.14
but absent on 3.10 would pass. Accepted: the picked file uses only long-stable modules; a 3.10 tox
run is the proper fix and is out of round-1 scope.

### 2.5 Acceptance criteria

- **AC-2.1** All five `test_provenance.py` tests pass.
- **AC-2.2** `test_dirty_content_id_distinguishes_trees` demonstrably fails when `capture_git_state`
  is called with `compute_dirty_content_id=False` — proving the test tests the mechanism, not the
  wrapper.
- **AC-2.3** `survey_stamp()` invoked at repo root returns `plr.provenance_source == "git"`,
  `plr.dirty is True`, and a `plr.dirty_content_id` that is 40-hex when the primary tree-OID
  mechanism succeeds or 64-hex if it falls back to `_diff_sha256_fallback` (given the current 57
  dirty submodule files); on this machine, with a working `git` binary, the primary 40-hex path is
  the one expected to fire.
- **AC-2.4** The header's `upstream sha256` matches the actual upstream file at pick time — asserted
  by §5's drift test, not by eye.
- **AC-2.5** Root `pyproject.toml`'s ruff `exclude` list (`pyproject.toml:215-220`) includes
  `plr-sema`, or `plr-sema/.ruff.toml` independently excludes `_provenance/git_state.py` — asserted by
  running `pre-commit run ruff --files plr-sema/src/plr_sema/_provenance/git_state.py` once locally and
  observing zero diff. Without this, `.pre-commit-config.yaml:2-7`'s unrestricted `ruff --fix` /
  `ruff-format` hooks (root config: `indent-width = 2`) reindent the picked 4-space file the moment
  it is staged, tripping §5.2 tier 1's sha256 self-consistency check on the very first commit.

---

## 3. The verdict type and record shape — **the hinge**

This section is the boundary between corpus-independent plumbing (§§1,2,4,5,6) and corpus-gated
semantics (deferred a–f). It must be specifiable **without presupposing an abstract domain**, and it
must not have to change when the domain lands.

**`Verdict` is the OUTPUT of evaluating an obligation against a state. It is not the abstract domain.**
(Added 260901, resolving [§Open decisions](#open-decisions) 1 and 3 — independent outside analysis,
spot-verified, user-approved.) The state deferred item (a) will build — per-channel tip typestate plus
Kleene truth values for tracked predicates — is a separate, internal type owned by (a); it needs ⊤
*and* ⊥ for its own reasons (strictness, the branch-merge join's unit). `Verdict` needs neither: for one
obligation evaluated against one state, entailed ⇒ `SAFE`, contradicted ⇒ `WILL_FAIL`, neither ⇒
`UNKNOWN`. It carries lattice structure only for **aggregation** — the report-level conjunction §3.2
specifies — which is a different operation from the internal domain's branch-merge join, over a
different carrier, at a different pipeline stage. Two decisions in [§Open decisions](#open-decisions)
dissolve directly out of this: **decision 1** (⊥/`UNREACHABLE`) — ⊥ belongs to the deferred (a) *state*
type, never to this wire enum, so the resolution is a docstring/reservation, not a new member; and
**decision 3** (join ordering) — the shipped §3.2 table is the correct join of the *obligation* order
(`WILL_FAIL` top), which is what `join` computes; `UNKNOWN`-as-top belongs to a different, real
*information* order that governs merging abstract states before a guard is ever evaluated, upstream of
`Finding` emission and outside this module entirely — the table stays exactly as shipped.

### 3.1 Interface / data contract

```python
class Verdict(str, Enum):
    SAFE     = "safe"       # analysis established the operation cannot fail
    WILL_FAIL = "will_fail" # analysis established the operation must fail
    UNKNOWN  = "unknown"    # analysis established nothing  (DEFAULT)

@dataclass(frozen=True, slots=True)
class Finding:
    verdict: Verdict
    operation_id: str            # OperationNode.id from the extracted graph
    category: str                # ∈ FAILURE_CATEGORIES (§4). REQUIRED for WILL_FAIL.
    plr_site: PlrSite | None     # where in PLR the evidence lives
    reason: str                  # ∈ REASON_VOCABULARY. REQUIRED for UNKNOWN.
    detail: str = ""             # human-readable; NEVER parsed by any consumer
    evidence: tuple[PlrSite, ...] = ()   # supporting guard sites, may be empty

@dataclass(frozen=True, slots=True)
class PlrSite:
    file: str        # repo-relative, e.g. "external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py"
    lineno: int
    qualname: str    # e.g. "LiquidHandler._check_containers"

@dataclass(frozen=True, slots=True)
class AnalysisReport:
    protocol_fqn: str
    verdict: Verdict             # join of findings — see 3.2
    findings: tuple[Finding, ...]
    stamp: SurveyStamp           # §2.2 — pins the contract-BUILD-time PLR+analyzer SHA
    schema_version: int = 1
    analyzer_stamp: SurveyStamp | None = None   # the check-run's own provenance; None in round 1 (M8, below)
```

**`stamp` vs. `analyzer_stamp` (round-4 remediation, M8).** These are two DIFFERENT provenance facts
that pre-round-4 shared one slot. `stamp` is the contract-**build**-time provenance: it is
deserialized verbatim from whatever `derived_contracts.json` already recorded when `plr_sema.derive`
last ran (`check/` never shells out to recompute one — §6.2's module docstring) — it answers "which
PLR tree were the contracts derived against?", not "which analyzer commit is running right now?".
Round 1–3's comment ("pins PLR SHA + analyzer SHA") overstated this: `stamp.praxis` is the *contracts
build's* analyzer SHA, not the checker's own. **Concretely illustrated, as a historical snapshot so
this example cannot itself go stale (round-6 remediation, R18/R13):** at the round-4 measurement,
`derived_contracts.json` carried `praxis.hash = e6eda0b1…` against a live `git rev-parse HEAD` of
`28d6800f`; by round 6 the artifact had moved on to `praxis.hash = 8be56345c7e0…` against a live HEAD
of `b3608eaaa` — two different snapshots of the same always-true fact: `stamp.praxis` is a
build-time pin, not a live measurement, and will differ from `HEAD` again the next time either moves.
The point (build-time ≠ run-time provenance) does not depend on which pair of hashes is current. The
checker's own code version was, and in round 1 remains, unrecorded. `analyzer_stamp`
is reserved for that fact and is `None` in round 1: `check/` cannot shell out (browser-side, no
subprocess), and there is no build-time-baked constant wired in yet either. AC-6.7 (§6.5) is rewritten
accordingly — see there.

**Never a boolean, at any layer.** `AnalysisReport` exposes no `__bool__`; defining one is
forbidden, because `if report:` would silently collapse `UNKNOWN` into a truth value and reintroduce
exactly the two-valued logic decision 5 bans. A ruff/AST check enforces the absence (§3.4).

### 3.2 The report-level join — specified as *structure*, deferred as *semantics*

The report's aggregate `verdict` is defined by a **table**, not by an inline expression:

| findings contain | report verdict |
|---|---|
| zero findings | `UNKNOWN` |
| any `WILL_FAIL` | `WILL_FAIL` |
| else any `UNKNOWN` | `UNKNOWN` |
| else (all `SAFE`, ≥1 finding) | `SAFE` |

**Round-4 remediation (B1/B2/§0(ii), fixes 1/4).** Rounds 1–3 stated the third row as "all `SAFE`,
*possibly zero findings*" ⇒ `SAFE`, and argued (below, now struck) that the zero-finding case was
"unreachable in v1" because §7's totality guarantee (AC-7.2) supposedly emitted an `UNKNOWN` finding
for every operation. That argument does not hold: AC-7.2's guarantee was never actually enforced at
`check_graph`'s own boundary — nothing asserted `join(())` itself, and nothing asserted every
operation in a real graph receives ≥1 finding (`len(findings) >= len(operations)`, AC-6.3's own
count-only form, does not imply the surjective per-operation claim; `260901_plr-sema-research-a-d.md:348-354`,
independently confirmed by reading `test_check_graph.py`). `check_graph('{"protocol_fqn":"p",
"operations":[],"resources":{}}', contracts)` — a graph with zero operations — is a reachable public
path that produced `SAFE` before this fix. `join` now maps the empty multiset to `UNKNOWN`
unconditionally; `check/` separately synthesizes a fallback `no_contract_derived` Finding for any
operation whose resolved contract has zero guards/gaps/no loop (§6.2), so the per-operation side of
the old argument is also now independently true rather than merely asserted.

> **Boundary declaration.** This table is *the* place deferred item (a) (lattice, ⊑, join at branch
> merges, widening) will attach. What is specified here is only that the aggregation is a **pure
> total function of the finding multiset**, computed in one named function
> `plr_sema.verdict.join(findings) -> Verdict`, with no other call site allowed to aggregate. **What
> will have to change when (a) lands:** the body of `join`, and possibly its signature. `join` is an
> obligation *conjunction* across independent check sites, not a control-flow-merge join in the
> classical dataflow sense (round-4 remediation, M9: the prior wording here — "a real lattice join
> operates over abstract states at control-flow merge points, not over a flat finding list" —
> overstated the contrast; reaching-definitions/live-variables/available-expressions are also lattice
> joins over flat fact sets, so that framing is not what distinguishes `join` from a real dataflow
> join). What (a) actually needs that the flat finding list does not carry is a per-`operation_id`
> **reachability** fact (`260901_plr-sema-research-a-d.md:126-134`) — the anticipated extension point is a narrow
> `reachability_map` parameter alongside the finding list, which preserves "exactly one function
> aggregates" (nothing in the corpus forces splitting `join` into two named functions;
> `260901_plr-sema-research-a-d.md:156-161` explicitly prefers the narrow-parameter form for exactly this reason).
> **What will NOT change:** `Finding`, `PlrSite`, `AnalysisReport`'s field set, and the rule that
> exactly one function aggregates. This is the specific claim the challenger should test: *is a flat
> finding multiset (plus, from round 4 on, a reachability map) a rich enough intermediate
> representation to survive the arrival of a real abstract domain?* I believe yes for `Finding`'s
> field set and no for `join`'s signature, and have specified accordingly.

**Zero findings ⇒ `UNKNOWN` (round-4 remediation; previously `SAFE`, see above).** This is now the
conservative choice by construction, not merely the more conservative of two live options — an
analyzer that says nothing about a protocol says `UNKNOWN`, not `SAFE`. `test_join_truth_table`'s
empty-multiset case pins this (§3.4), and the same claim is additionally exercised end-to-end by
`check_graph` on a zero-operation graph (demonstrated in this round's fixer report).

### 3.3 The `UNKNOWN` reason vocabulary

Closed per release, mechanically defined, DERIVED from our own pipeline's control flow in the
sense that each reason corresponds to exactly one `return`-with-no-result site in `plr_sema.derive`.
(The bold classification tag for this section is stated once, normatively, below — this sentence is
prose emphasis, not a second, conflicting tag.)

| reason | emitted when |
|---|---|
| `no_contract_derived` | the target method has no entry in the derived contract table at all (this now also covers a resolved contract with zero guards/gaps/no loop — round-4 remediation, B1, see §6.2) |
| `unresolved_delegate` | the transitive `delegates_to` closure hit an `unresolved_calls` entry |
| `guard_predicate_unparsed` | a guard `condition` string could not be turned into a predicate (deferred item (c)) |
| `loop_bounds_unknown` | an operation sits inside a loop whose trip count is not established (deferred item (d)) |
| `receiver_type_unknown` | `OperationNode.receiver_type is None` |
| `unsupported_tool` | method outside the analyzed surface (mirrors §4's category) |
| `internal_error` | analyzer bug; always paired with a telemetry emit (this pairing is now actually implemented — round-4 remediation, M2, §6.2) |

**`argument_not_static` withdrawn (round-4 remediation, B4, CONCEDE).** Round 1–3 specified an eighth
reason, `argument_not_static` ("a guard's `mentions_params` references an argument classified
dynamic"), checked by intersecting a guard's `free_vars` (PLR callee-parameter names, e.g. `resource`,
`source`, `destination`) against `OperationNode.depends_on_params` (protocol-level parameter names).
Measured this round: the union of `free_vars` over all 10 shipped contracts is `['action',
'destination', 'method', 'offsets', 'resource', 'self', 'source', 'target', 'tip_spots',
'use_channels']`; `depends_on_params` across the four fixture operations is `['tips']`/`[]`. The
intersection is empty — the two namespaces are genuinely disjoint in every shipped fixture, so this
reason never fired. Worse, several `free_vars` names (`resource`/`source`/`destination`) are plausible
protocol-parameter names too, so a same-named collision would have fired the reason for no semantic
cause — a live false-positive path, not merely a dead one. **Withdrawn from `REASON_VOCABULARY`
entirely** rather than fixed in place: reinstating it correctly requires specifying the actual
binding chain — guard free var → PLR parameter *position* → `op.arguments[param]` → protocol
expression → `depends_on_params` — which is out of round-1 scope (deferred item (c) territory: it
needs the same predicate-language work that gives `guard_predicate_unparsed` its escape hatch). Every
guard now gets `guard_predicate_unparsed` unconditionally (§6.2).

**Budget: 7 today, hard cap 12** (registry row HM-14; was 8/12 — B4 above withdrew one member, the
cap is untouched). Adding an eighth is a deliberate, reviewable act; adding a thirteenth fails the
ratchet test.

**Classification: HAND-MAINTAINED**, with an unusual and important justification. *Why not derived:*
the vocabulary describes **our own analyzer's** give-up points, which exist in our source, not PLR's.
Deriving it from our own AST would be circular. *What breaks when PLR changes:* **nothing** — that
is the entire reason this vocabulary is safe to hand-maintain while a *semantic* vocabulary would not
be. *Enforcement:* `test_reason_vocabulary_closed` (§3.4) AST-scans every `Finding(..., reason=...)`
construction in `src/plr_sema/`, resolving the `reason=` argument as either a string literal or a
reference to a module-level constant (resolved to its assigned literal value). **A bare local
variable or a computed expression fails the scan** rather than silently passing — the original
"every literal `reason=` argument" wording was one-directional and would pass vacuously against any
natural implementation (`Finding(reason=SOME_CONST)` or `reason=r`), since neither yields a literal
to scan. A second, reverse assertion in the same test checks that every `REASON_VOCABULARY` member is
reachable from ≥1 construction site, so the table cannot grow orphaned entries either.

### 3.4 Verification

```bash
uv run pytest plr-sema/tests/test_verdict.py -q
```

- `test_join_truth_table` — parametrized over all 10 multisets of ≤2 findings (see §3.4's own
  discrepancy note below); asserts the §3.2 table exactly via a literal
  `dict[tuple[Verdict, ...], Verdict]` table (round-4 remediation, M7 — replacing a re-implementation
  of `join`'s own absorption logic that lived in the test file, which meant a wrong `join` body could
  only be caught by accident of both copies agreeing). The empty-tuple key maps to `UNKNOWN` — this
  is the T3-level AC closing the T3→T8 window B2 named (fix 6): `join(())` is asserted `UNKNOWN`
  before any pipeline exists to run it through, not only at T8 via `check_graph` on an empty graph.
- `test_join_absorbs_across_shared_operation_id` — **new, round-4 remediation (M7).** None of the
  parametrized cases above ever share an `operation_id`; this pins the case
  `260901_plr-sema-research-a-d.md` flags as sound-today-but-not-post-(a): `join((SAFE@op1, WILL_FAIL@op1))` absorbs
  to `WILL_FAIL`, identically to two findings on different operations — today's specified behavior,
  not yet a per-operation grouping.
- `test_no_bool_protocol` — `ast.walk` over `src/plr_sema/`, assert no `__bool__` def on `Verdict`,
  `Finding`, or `AnalysisReport`; plus a runtime `pytest.raises(TypeError)`-style guard is *not*
  used (a dataclass is truthy by default) — instead assert the class dict lacks `__bool__` and that
  a lint rule forbids `if <AnalysisReport>` shapes. **DERIVED** (computed from our AST).
- `test_will_fail_requires_category` / `test_unknown_requires_reason` — `__post_init__` raises
  `ValueError`; asserted directly.
- `test_reason_vocabulary_closed` — AST scan of every `Finding(...)` construction in
  `src/plr_sema/`; every `reason=` argument, resolved as a literal or a module-level constant, ∈
  `REASON_VOCABULARY` (an unresolvable form — a bare local variable, a computed expression — fails
  the test rather than passing vacuously); plus the reverse check that every `REASON_VOCABULARY`
  member is reachable from ≥1 construction site. **DERIVED.**
- `test_report_round_trips_json` — `asdict` → `json.dumps` → parse → reconstruct; field-equal. Pins
  the record as a wire contract, which §6's extractor/checker split requires.

### 3.5 Failure mode

**Assumption:** `Finding`'s field set survives the arrival of the abstract domain.

**If wrong:** `schema_version` bumps, and old readers may reject new reports. **Corrected 260901
(§Open decisions 1 — round 6/pre-260901 text had this backwards):** for a *structural* field-set change
this is real and directional as stated. But for the specific, narrower case this section previously
conflated it with — an *additive* `Verdict` enum member (e.g. a future `UNREACHABLE`) — the direction is
the reverse: only *old* readers choke on *new* reports; a new reader already accepts an old report as a
strict subset, because it recognizes a superset of verdict strings. §Open decisions 1 also adds a
standing consumer rule that shrinks this failure mode further for that case: **a consumer that meets a
`Verdict` string it does not recognize must map it to `UNKNOWN`** (implemented as
`Verdict.from_wire`, `plr_sema/verdict.py`, tested in `test_verdict.py`) — mapping an unknown value to
the fail-closed default is always sound (it can only widen, never fabricate a false claim), so a
compliant consumer degrades gracefully on an unrecognized member instead of raising. **Mitigation
(general case, unchanged):** `schema_version` is present from day one and the JSON round-trip test pins
it; consumers must branch on it rather than duck-type. **This is the highest-consequence assumption
in the document** and is the reason `Finding` carries `detail: str` as an explicitly
never-parsed escape hatch — new information can land there without a schema bump, and the closed
`category`/`reason` fields stay machine-readable. That mirrors the discipline
`training/verify/failure_taxonomy.py` already enforces (classify by type/module, never by parsing
message text), inverted: we *emit* free text but forbid *consuming* it. **No `schema_version` bump was
needed for the 260901 resolution pass itself** — no member was added, no field changed; only the string
`"unreachable"` was reserved (comment, unused) and the `from_wire` consumer rule was added.

### 3.6 Acceptance criteria

- **AC-3.1** All `test_verdict.py` tests pass (round-6 remediation, R15 — a hard-coded count is not a
  gate: §3.4 names seven tests across six bullets, and the shipped file collects **eight** functions
  because `test_reason_vocabulary_closed` ships as `_forward`/`_reverse`; asserting the count would
  drift again the next time a bulleted test splits into more than one function, per the same reasoning
  §8.3 already gives for asserting the 45 hand contracts dynamically rather than hard-coding).
- **AC-3.2** `grep -rn "__bool__" plr-sema/src/` returns nothing.
- **AC-3.3** `Finding(verdict=UNKNOWN, operation_id="op1", category="", plr_site=None, reason="")`
  raises `ValueError` (an empty `reason` is invalid for an `UNKNOWN` verdict); the same call with
  `reason="not_a_real_reason"` also raises `ValueError`. (`reason: str` has no default, so *omitting*
  it entirely raises `TypeError` for a missing required argument before `__post_init__` ever runs —
  that is a dataclass mechanic, not the validated error this AC is testing, so it is not the case
  exercised here.)
- **AC-3.4** (reworded, D15) An `AnalysisReport` **constructed directly** (as
  `test_report_round_trips_json`, §3.4, already does — no pipeline run required) serializes to JSON
  and deserializes field-identically. The full-pipeline form of this claim (fixture graph →
  `check_graph` → report → round-trip) is **AC-6.6**, gated in T8, since T3 alone has no working
  pipeline to run.
- **AC-3.5** (round-4 remediation, B1/B2, fix 6) `plr_sema.verdict.join(())` (the empty finding tuple)
  returns `Verdict.UNKNOWN`. This closes the T3→T8 window B2 named: the claim is asserted at T3,
  directly against `join`, not only observable later via a full `check_graph` run in T8.

---

## 4. Telemetry schema

### 4.1 Interface / data contract

**Promote `training/verify/failure_taxonomy.py`'s closed 6-set into the package's error model,
verbatim:**

```python
FAILURE_CATEGORIES: frozenset[str] = frozenset({
    "unsupported_tool", "ungroundable_reference", "shape_mismatch",
    "precondition_state", "harness_internal", "postcondition_mismatch",
})
```

Read this session at `training/verify/failure_taxonomy.py:82-89`. The set is battle-tested at corpus
scale and its module docstring records *why* each category exists (`:17-34`) — that rationale is the
justification for freezing it, and must be carried across in the copied docstring.

Four categories need explicit re-interpretation in a *static* analyzer, since they were coined for a
*dynamic* harness (round-5 remediation, m1, CONCEDE — the table below always rewrote four rows,
`precondition_state`/`postcondition_mismatch`/`shape_mismatch`/`ungroundable_reference`; only
`unsupported_tool`/`harness_internal` are marked "same"; the prose undercounted them as "two"). This
re-interpretation is a genuine semantic act and should be attacked:

| category | dynamic meaning (verify/) | static meaning (plr-sema) |
|---|---|---|
| `precondition_state` | a PLR exception escaped at runtime | a derived guard is statically established to fire |
| `postcondition_mismatch` | ran clean, but effect checks disagreed | **unreachable in v1** — no effects are simulated. Reserved. |
| `shape_mismatch` | `DispatchError` — bad call shape | arity/keyword mismatch against the derived signature |
| `ungroundable_reference` | `GroundingError` — no such deck object | a resource variable with no `ResourceNode` in the graph |
| `unsupported_tool` | method outside `SUPPORTED_TOOLS` | same; the analyzed-surface boundary |
| `harness_internal` | analyzer/plumbing bug | same; always paired with `reason="internal_error"` |

`postcondition_mismatch` being unreachable in v1 is stated so that a zero count is read as
"correctly unreachable", not "suspiciously clean".

**Emission surface — zero new dependencies.** Telemetry is greenfield (no opentelemetry, structlog,
logfire, or cisternal in praxis's `pyproject.toml`, confirmed this session). Adding one now would
prejudge both the Pyodide question (§6) and an org-wide observability choice not in scope. Instead:

```python
class TelemetrySink(Protocol):
    def emit(self, event: Mapping[str, Any]) -> None: ...

def set_sink(sink: TelemetrySink | None) -> None: ...   # process-global, default None
```

Default sink is a no-op. A `JsonlSink(path)` ships in-package (stdlib `json` + append). Adapters to
real backends are downstream code, not ours.

**Event schema** (one JSON object per line):

```json
{
  "schema_version": 1,
  "event": "finding" | "internal_error" | "derivation_gap",
  "ts": "<ISO-8601 UTC>",
  "protocol_fqn": "...",
  "operation_id": "...",
  "verdict": "safe|will_fail|unknown",
  "category": "<FAILURE_CATEGORIES member or null>",
  "reason": "<REASON_VOCABULARY member or null>",
  "plr_site": {"file": "...", "lineno": 0, "qualname": "..."},
  "stamp": { "...": "SurveyStamp (§2.2)" }
}
```

**Every emitted event carries the full `SurveyStamp`.** This is what makes decision 3 ("telemetry on
errors is first-class") mean something concrete: an error report is worthless without knowing which
PLR tree it was computed against, and the 57-dirty-file submodule state makes a bare SHA
insufficient.

**Never raises.** `emit` failures are swallowed (matching `capture_git_state`'s discipline).
Telemetry that can crash the analyzer is worse than no telemetry.

**`check_graph` itself emits (round-4 remediation, M2, CONCEDE).** Rounds 1–3 specified the emission
surface (this section) but nothing under `check/` ever called it — `check_graph` built and returned
an `AnalysisReport` without emitting a single event, despite §3.3's `internal_error` reason being
documented as "always paired with a telemetry emit". That pairing is now real: `check_graph`'s
`_check` helper calls `emit_finding` for every `Finding` it produces (not only `internal_error`'s,
so the pairing claim is true of every reason, not just one) after building the report and before
returning it. This costs nothing when no sink is attached (`set_sink(None)` is the default — AC-4.4)
and is exercised end-to-end by AC-6.7 (§6.5, also reworded this round).

### 4.2 Verification

```bash
uv run pytest plr-sema/tests/test_telemetry.py -q
```

- `test_categories_match_upstream` — imports `FAILURE_CATEGORIES` from **both**
  `plr_sema.telemetry` and `verify.failure_taxonomy`, asserts set equality. This is a live
  cross-package drift test (see §5), not a copied constant. Skipped with an explicit reason if
  `training/verify` is not importable.
- `test_every_will_fail_carries_a_category` — property-style over constructed findings.
- `test_sink_failure_is_swallowed` — a sink whose `emit` raises; assert analysis completes and
  returns a report.
- `test_event_carries_stamp` — assert `stamp.plr` is present in every emitted event; parametrized over
  a real-repo capture (assert `stamp.plr.hash` is 40-hex) **and** a `tmp_path`/`PATH`-scrubbed
  capture (assert `stamp.plr.hash` equals the module's documented `nogit`/`unavailable` sentinel
  instead of asserting hex-length). An unconditional "always 40-hex" assertion is wrong by
  construction: `capture_git_state` returns a sentinel hash, not a hex digest, on those two branches
  (`git_state.py:93-96`).
- `test_jsonl_sink_round_trip` — write N events, read back, assert N parseable lines with
  `schema_version == 1`.

**Classification: HAND-MAINTAINED (frozen).** *Why not derived:* the 6 categories are *our*
semantics — a taxonomy of what kinds of thing can go wrong from our perspective — not a fact
recoverable from PLR source. No AST walk over PLR can tell you that "the harness's synthesized setup
didn't establish the state the call assumes" is a distinct category worth naming. *What breaks when
PLR changes:* nothing. PLR adding exception classes changes which classes *map into*
`precondition_state`, not the category set — and that mapping is now RETIRED, not DERIVABLE-NOT-YET
(below). *Registry rows:* HM-5 (categories, 6, **frozen**), HM-6 (module-prefix dispatch, 2),
HM-7 (`our_names` map, 3), HM-8 (RETIRED, round 4 M5 — declared 0; see §9.2).

> **Resolved by T7 (`3a3a9f00`) — recorded for provenance, not live.** `failure_taxonomy._plr_exception_class_names()`
> (`training/verify/failure_taxonomy.py:159`) used to introspect exactly **two** modules —
> `pylabrobot.liquid_handling.errors` and `pylabrobot.resources.errors` — via `inspect.getmembers`,
> while `training/verify/data/plr_exception_taxonomy.json` records **132** exception classes
> AST-derived across all 502 PLR source files. That gap affected only `classify_check_failure`
> (`:215`), which consumes `_plr_exception_class_names()` at `:245`. `classify_exception` (`:187`)
> dispatches by module-prefix match (`module.startswith("pylabrobot.")`, `:209`) and was **never**
> affected — it does not go through the two-module allowlist at all. **T7 (`3a3a9f00`) replaced the
> two-module `inspect.getmembers` walk with `_load_taxonomy_artifact()`, a load of
> `plr_exception_taxonomy.json` keyed by class name (`:109`)** — the loader refuses an artifact lacking
> a non-empty `version.git_sha` or a non-empty `classes` array (`TaxonomyArtifactError`) and exposes the
> recorded SHA for comparison (`plr_exception_taxonomy_git_sha()`). 11 → 132 names became visible, 121
> newly, none lost. **Round 1 performs no staleness COMPARISON; that policy belongs to the caller**
> (round-4 remediation, M4, PARTIAL — the round-1/2/3 text's "stamped by §2.2 — T7's gate requires the
> loaded JSON carry a validated `SurveyStamp`" overclaimed: the artifact is validated against its OWN
> shape, not `plr_sema`'s `SurveyStamp` — `training/` gains no `plr_sema` import to satisfy the literal
> §2.2 phrasing, a deliberate, flagged deviation — and no comparison against a live checkout is
> performed anywhere). The registry row this trigger fired is HM-8, now `RETIRED` — see §9.2.

### 4.3 Failure mode

**Assumption:** the 6-set is complete for *static* analysis, having been validated for *dynamic*
verification.

**If wrong:** a static failure kind exists with no home and lands in `harness_internal`, which is
defined as "a bug in our plumbing" — so miscategorisation shows up as an implausible
`harness_internal` rate. **Detection (round-4 remediation, M3, CONCEDE):** no detection mechanism
exists in round 1 — `check/` never constructs a `WILL_FAIL` `Finding` (§0 fixes every v1 verdict at
`UNKNOWN`), `Finding.category` is validated only for `WILL_FAIL` (§3.1), and the gap ledger's
`by_category` block is therefore `None` for all six categories with a sibling
`by_category_status: "not_applicable_v1"` field naming this explicitly (round 1–3 published all-zero
counts here, which read as a *measurement* of zero rather than "not applicable" — RISK-4's tripwire
could never have fired against six zeros that were never wired to anything). **The
`harness_internal`-rate tripwire this paragraph originally named becomes live only once `WILL_FAIL` is
first emitted** — a future round's responsibility, not round 1's. **Response is *not* to add a 7th
category reflexively** — the set is frozen precisely so that pressure to extend it becomes a
visible design conversation rather than a silent commit.

### 4.4 Acceptance criteria

- **AC-4.1** All five `test_telemetry.py` tests pass.
- **AC-4.2** `test_categories_match_upstream` passes with `training/verify` importable (i.e. the sets
  are genuinely equal today, not merely skipped).
- **AC-4.3** (reworded, D15) With `JsonlSink` attached, **directly constructing and emitting** a
  `Finding`-derived event (as `test_jsonl_sink_round_trip`, §4.2, already does — no pipeline run
  required) yields a parseable line whose `stamp.plr.hash` equals `dd79c4c89`'s full SHA at the
  current pin. The full-pipeline form of this claim (a real run over one protocol emitting ≥1 line)
  is **AC-6.7**, gated in T8, since T4 alone has no working pipeline to run. (The `dd79c4c89`-pin
  clause is self-scoping to the current checkout state per the round-1 rebuttal — untouched.)
- **AC-4.4** `plr_sema` imports and analyzes with `set_sink(None)` — telemetry is strictly optional.

---

## 5. Fork-drift tests

Two forks exist. Neither has a drift test today. Both get one, and they are **structurally
different**, which matters.

### 5.1 Fork A — the coxswain port (both sides in-repo)

`coxswain/src/coxswain/fft/preconditions/` contains **six**, not four, ported modules, carrying
**three distinct `PORT PROVENANCE` header forms** — confirmed by read this remediation round:

| module | source | header form |
|---|---|---|
| `method_contracts.py` (547 lines) | `praxis/backend/core/simulation/method_contracts.py:1-546` | single-range verbatim |
| `state_models.py` (586 lines) | `praxis/backend/core/simulation/state_models.py:1-585` | single-range verbatim |
| `failure_modes.py` (124 lines) | `praxis/backend/core/simulation/failure_detector.py`, disjoint ranges, header `:1-8` | multi-member partial lift, differently-named source |
| `simulation_result.py` | `praxis/backend/core/simulation/simulator.py`, disjoint ranges, header `:1-8` | multi-member partial lift, differently-named source |
| `pipeline_models.py` | `praxis/backend/core/simulation/pipeline.py`, disjoint ranges, header `:1-7` | multi-member partial lift, differently-named source |
| `bounds_analyzer.py` (379 lines) | `praxis/backend/core/simulation/bounds_analyzer.py`, **no line range**, explicit `# ADAPTATION` block, header `:1-14` | adapted whole-module lift, deliberately **NOT** verbatim |

"Verbatim copies of four modules" was wrong on both counts: it is six modules, and "verbatim" only
describes two of them (`method_contracts.py`, `state_models.py`). The other four are either partial
lifts of a *differently-named* upstream module with disjoint member ranges, or a declared adaptation.
Confirmed by read: `method_contracts.py:1` reads
`# --- PORT PROVENANCE (verbatim copy of praxis/backend/core/simulation/method_contracts.py:1-546)`.

`coxswain/tests/test_sim_port.py` exists but is **not a drift test** — it is a *parity* test that
re-encodes upstream constants as hand-typed literals (`assert SIMULATION_VERSION == "1.0.0"`,
`# failure_detector.py:34-47`). If upstream changes, that test keeps passing against the stale copy
until someone notices. It even documents the intent — "one definition, zero divergence (RISK-3's
two-implementations failure mode)" — while implementing the mechanism that cannot detect divergence.

**Interface:** `plr-sema/tests/test_fork_drift.py::test_coxswain_port_matches_upstream` +
`plr-sema/tests/test_fork_drift.py::test_every_ported_module_is_covered`.

**Mechanism, scoped to round 1 — precise restatement (D21).** A single-range-verbatim header parses
trivially to `(upstream_path, start, end)`. **The multi-member and adaptation headers also parse** —
the multi-member form records per-member ranges in a uniform, regex-parseable
`#   - <Name>  <file>.py:<start>-<end>` form; round 1's earlier claim that these forms "do not [parse]
without inventing a grammar" was imprecise. What round 1 actually declines to build is **per-member
body extraction from the fork file** to compare each parsed range against the fork's corresponding
body slice — that needs symbol-range resolution (locating where in the fork file a given ported
member's body begins and ends), not a header-parsing grammar, and it is a materially larger piece of
work than header parsing. Round 1 therefore:

- **Scopes the byte/content comparison to the two whole-file-verbatim modules only**
  (`method_contracts.py`, `state_models.py`). `test_coxswain_port_matches_upstream` parses their
  single-range headers, reads the named line range from the live upstream file, and compares against
  the fork's body (fork content minus its header lines), **normalized**: strip trailing whitespace,
  drop blank lines. Do **not** compare raw bytes — a formatter run on one side would produce a
  permanently red test that gets muted, which is worse than no test.
- **Adds `test_every_ported_module_is_covered`**: enumerate every file under
  `coxswain/src/coxswain/fft/preconditions/` carrying a `PORT PROVENANCE` header (all six), and
  **fail loudly** — a named, readable assertion failure, not a silent skip — on any header whose form
  the parser does not recognize. This converts "four of six modules have no drift coverage" from a
  silent gap into a visible, tracked one, without prematurely inventing a grammar for disjoint
  multi-member ranges or adaptation blocks. Extending byte-comparison to the remaining four modules is
  explicitly out of round-1 scope and is named as follow-on work.

**Classification: DERIVED**, restated honestly for what round 1 actually implements — the comparison
target for the two whole-file-verbatim modules is parsed out of the header, not typed into the test,
so adding a **third** whole-file-verbatim module requires no test edit. This property does **not**
extend to the four partial-lift/adaptation modules: `test_every_ported_module_is_covered` verifies
their headers are *parseable-or-loudly-rejected*, not that their bodies match upstream. That gap is
real and named, not silently closed by this classification.

**On failure (whole-file-verbatim comparison):** the test message must name the drifted file, the
upstream line range, and a unified diff. A drift is *not* automatically a bug — it may be an
intentional upstream fix the fork should take. The test's job is to make the choice explicit.

### 5.2 Fork B — the cherry-picked `git_state.py` (upstream out-of-repo)

> **FLAG — locked decision 6's drift test is not fully implementable as stated.** The upstream lives
> at `/home/marielle/projects/cisternal`, a **machine-local absolute path outside this repo**. A test
> that reads it cannot run in CI, on a fresh clone, or on any machine without that checkout. As
> written, decision 6 specifies a test that is green-when-skipped nearly everywhere — the weakest
> possible form of a drift test.

**Resolution: two tiers, and the always-on tier must be the load-bearing one.**

- **Tier 1 — self-consistency (always runs, no cisternal needed).** The header records
  `upstream sha256`. The test recomputes sha256 over the local file *with the header block stripped*
  and asserts equality. This catches the actual failure this test exists to prevent: **someone
  editing the local copy.** The header says `DO NOT EDIT`; tier 1 enforces it. It does *not* detect
  upstream moving.
- **Tier 2 — upstream comparison (skips when cisternal is absent).** If
  `$PLR_SEMA_CISTERNAL_ROOT` (default `/home/marielle/projects/cisternal`) exists, read the upstream
  file, compare bytes, and additionally assert the header's recorded `upstream commit` is an ancestor
  of the upstream's current `HEAD` (`git merge-base --is-ancestor`) — a drifted-but-not-rebased pick
  is a different finding from a rebased one. **Skip must be `pytest.skip` with an explicit reason
  string naming the missing path**, never a silent pass.

**Classification: HAND-MAINTAINED** (the header's recorded SHAs are typed once at pick time; registry
row HM-18, metric = 2 recorded hashes). *Why not derived:* the upstream identity cannot be recovered
from the local file. *What breaks:* nothing PLR-coupled. *Ratchet:* if `git_state.py` is ever picked
into a second package, the tier-1 mechanism must be shared, not re-typed.

### 5.3 Fork C — the `check/graph.py` stdlib mirror (in-repo, cross-package) — **new, D8**

Unlike Forks A and B, this fork's "upstream" is a **live pydantic model**
(`praxis.backend.utils.plr_static_analysis.models.OperationNode`/`ResourceNode`, `:524-662`), not a
static file snapshot, and the "fork" is `plr_sema/check/graph.py`'s stdlib-dataclass mirror (§6.2,
D1). §6.2's own text ("no third model hierarchy is introduced") is correctly scoped by its own
em-dash clause and is not itself wrong — but the mirror is still a **hand-typed projection** of a
model definition §1.1 pins in place without freezing: a future field rename/removal on
`OperationNode`/`ResourceNode` has no built-in signal reaching `check/graph.py`. Neither of §5's
existing drift mechanisms reaches it — Fork A's is scoped to `coxswain/`; Fork B's is scoped to the
cherry-picked `git_state.py`.

**Resolution.** `plr-sema/tests/test_check_graph_mirror_drift.py::test_mirror_fields_match_operation_node`
— living under `plr-sema/tests/`, which §1.3's boundary walk does **not** cover (that walk is scoped
to `src/plr_sema/`), so this test file may import
`praxis.backend.utils.plr_static_analysis.models` and compare the mirror's derived field set (§6.2's
D1 table) against the live model's `model_fields` keys — the same pattern §4.2's
`test_categories_match_upstream` already uses for `training.verify.failure_taxonomy` (import with a
skip-if-unavailable guard). Skipped with an explicit reason if `praxis` is not importable in the
running environment.

**Interaction with D1.** This test is only meaningful once §6.2's D1 fix makes the mirror's field set
a named, derived-from-consumers enumeration rather than an ad hoc "nothing else" list — before that
fix there is no well-defined comparison target. Once both land, Fork C's drift test is what keeps the
derived-from-consumers enumeration honest against upstream changes over time.

**Classification: DERIVED** for the per-field presence check (the comparison target is the live
model's `model_fields`, not a typed list) — but the *decision of which fields to mirror* remains
HAND-MAINTAINED, registered as **HM-21** (§9.2): a human decided which §3.3 reasons/§7.3 lookups
exist today, and that decision is not itself recoverable from PLR source.

### 5.4 Verification

```bash
uv run pytest plr-sema/tests/test_fork_drift.py -q -rs   # -rs surfaces skip reasons
```

- `test_coxswain_port_matches_upstream` — parametrized over the **two whole-file-verbatim** ported
  modules (`method_contracts.py`, `state_models.py`), derived from their single-range headers.
- `test_every_ported_module_is_covered` — enumerates **all six** ported modules; asserts each carries
  a `PORT PROVENANCE` header that either parses to a recognized form (single-range verbatim,
  multi-member partial lift, or no-range adaptation) or fails the test with a named, readable message
  — never a silent skip or silent drop from enumeration.
- `test_port_provenance_headers_are_parseable` — every file under
  `coxswain/src/coxswain/fft/preconditions/` with a `PORT PROVENANCE` header parses to a valid
  provenance record and the referenced upstream path exists. Guards against a header that drifts into
  unparseability and silently drops its module from parametrization — a classic self-disabling-test
  failure.
- `test_git_state_self_consistent` (tier 1).
- `test_git_state_matches_cisternal` (tier 2, skip-with-reason).

That is all five tests `test_fork_drift.py` itself carries (AC-5.1's "all five tests" refers to this
file). Fork C's own drift test is a T8 deliverable, not a T5 one — it ships against `check/graph.py`,
which does not exist until T8:

```bash
uv run pytest plr-sema/tests/test_check_graph_mirror_drift.py -q
```

- `test_mirror_fields_match_operation_node` — **new, D8, Fork C.** Parametrized over
  `OperationNode` and `ResourceNode`; asserts every field name in `check/graph.py`'s mirror (§6.2's
  D1 table) is a member of the live model's `model_fields`. Skips with an explicit reason if `praxis`
  is not importable. Gated by T8 (AC-5.5, added to T8's row — round-3 changelog's "AC-5.1–5.4 →
  AC-5.1–5.6" was wrong by one; D8 added exactly AC-5.5, and it is filed here because
  `test_fork_drift.py` cannot satisfy it before `check/graph.py` exists.)

### 5.5 Failure mode

**Assumption:** `PORT PROVENANCE` headers accurately name their source ranges.

**If wrong:** the test compares against the wrong lines and is either spuriously red (noticed) or
spuriously green (not noticed). The green case is the dangerous one, and it arises when a header's
range is *too narrow* — comparing a subset that happens to match. **Mitigation, per-member:** for the
two **whole-file-verbatim** modules, `test_port_provenance_headers_are_parseable` asserts the claimed
single range's length is within ±2 lines of the fork file's non-header body length, catching gross
range errors (line-exact ranges are already recorded, e.g. `:1-546` against a 547-line file, so the
tolerance is tight enough to be meaningful). **This tolerance is incoherent for the four
partial-lift/adaptation modules**: their headers record either disjoint multi-member ranges that sum
to far less than the fork file's body length by design (a partial lift), or no range at all (the
adaptation form) — a ±2-line check against total body length would be meaningless or unsatisfiable in
either case. For those four, `test_port_provenance_headers_are_parseable` checks only that the header
parses to a recognized form and its referenced upstream path exists; no length tolerance is applied.

**Fork C's own failure mode (D8).** **Assumption:** the mirror's derived-from-consumers field set
(D1) stays a subset of `OperationNode`/`ResourceNode`'s live field set. **If wrong:** a mirrored field
no longer exists on the upstream model, and `check/graph.py`'s `json.loads` + explicit field
extraction silently produces `None`/a missing key at runtime rather than an import-time error, since
the mirror never imports the pydantic model to fail against. **Mitigation:**
`test_mirror_fields_match_operation_node` fails closed (an assertion, not a skip) whenever `praxis`
is importable in the test environment, converting a silent runtime gap into a red test at review
time.

### 5.6 Acceptance criteria

- **AC-5.1** All five tests pass on this machine, with tier 2 **running** (not skipped) — proving the
  mechanism works before it is allowed to skip elsewhere. `test_every_ported_module_is_covered`
  specifically enumerates and accepts (or loudly rejects) all **six** ported modules — not four.
- **AC-5.2** `uv run pytest plr-sema/tests/test_fork_drift.py -q` with `PLR_SEMA_CISTERNAL_ROOT`
  pointed at a nonexistent path yields exactly one skip with a reason naming the path, and zero
  failures.
- **AC-5.3** Manually appending a whitespace-only line to a coxswain fork file does **not** trip the
  test (normalization works); manually changing an identifier **does** (the test has teeth).
  Demonstrate both, commit neither.
- **AC-5.4** Manually editing one character in the picked `git_state.py` body trips tier 1.
- **AC-5.5** (D8) `test_mirror_fields_match_operation_node` passes when `praxis` is importable in this
  repo's own test environment — i.e. genuinely checked, not skipped, here.

---

## 6. Extractor / checker split as a packaging fact

### 6.1 The forcing constraint

`libcst` 1.9.0 ships a Rust native extension (`native.cpython-314-*.so`); `libcst>=1.1.0` is a praxis
dependency (`pyproject.toml:29`). Native extensions are not available under Pyodide unless
specifically built for it. Therefore **any code path that must run in the browser cannot import
libcst** — and cannot import `pylabrobot` either, since importing PLR to check a protocol defeats the
point of a static analyzer that runs before the environment exists.

`praxis/backend/core/simulation/graph_replay.py` (488 LOC) already exists specifically to replay a
*pre-extracted* graph with no PLR imports. That module is the existing proof that this split is the
right shape; plr-sema makes it a **packaging fact** rather than a convention.

**Why three packages, not two (round-5 remediation, m2, PARTIAL).** §6.1's `libcst`/`pylabrobot`
import constraint above forces exactly a TWO-way split (`extract/` vs. `check/`); `derive/` satisfies
`check/`'s own constraints (stdlib-only, reads JSON) and the three-way split is NOT forced by §6.1
alone — round 5's challenge correctly named this gap. But the three-way split IS forced, by a
constraint §6.1 had not written down: `derive/` calls `scan_dropped_receiver_calls`
(`derive/__init__.py:400-405,591,678-704`), which `rglob`s and `ast.parse`s the PLR source tree **on
disk** under `external/`. Needing PLR's source files on disk — not just avoiding `libcst`/`pylabrobot`
imports — is a browser-disqualifying constraint independent of §6.1's import rule: a Pyodide
deployment has no `external/pylabrobot` checkout to `rglob`. `derive/` is additionally justified on
build-vs-run staging (contracts are built once, checked many times) — both reasons hold together, and
neither alone is §6.1's import constraint restated. (`derive/`'s own `SUPPORTED_TOOLS` was already
re-homed into `check/_supported_tools.py` to avoid a third copy — round 5 reads that seam as
corroborating evidence that the split was under-justified, not as a reason to collapse it.)

### 6.2 Interface / data contract

```
src/plr_sema/extract/     SERVER-SIDE.  libcst permitted. pylabrobot import permitted. ROUND 2 — see below.
                         Input: protocol source. Output: ProtocolComputationGraph (JSON).
src/plr_sema/check/       BROWSER-SIDE. NO libcst. NO pylabrobot. stdlib only (no pydantic — see below).
                         Input: graph JSON + derived contract table JSON + SurveyStamp.
                         Output: AnalysisReport (JSON).
src/plr_sema/derive/      BUILD-TIME. §7's derivation pipeline. libcst not required; reads the
                         on-disk survey JSON via a **required** `--survey-json PATH` CLI argument
                         (no default — D19; see §7.3/§7.4).
                         Input: survey JSON. Output: derived_contracts.json (§7.3), consumed by check/.
```

The **wire format between them is JSON**, which is why §3.4's `test_report_round_trips_json` and the
graph's own serializability are load-bearing rather than nice-to-have.

**`plr_sema.check` never imports `pydantic`.** `OperationNode`, `ResourceNode`,
`ProtocolComputationGraph` (`plr_static_analysis/models.py:524-661`) are pydantic `BaseModel`s under
`praxis.*` — forbidden by §1.3 (no `praxis` import under `src/plr_sema/`) and unmovable per §1.1
(round 1 moves nothing out of `praxis/`) — so `check/` cannot import them directly, independent of
any Pyodide question. Round 1 defines a **parallel, minimal stdlib-dataclass mirror** of the node
types it actually reads, in `plr_sema/check/graph.py`. This is mechanical, not a design choice
requiring justification, because the wire format is already JSON (per this section): the mirror
types are populated by `json.loads` + explicit field extraction, never by a pydantic
`model_validate`.

**The mirror's field set is derived-from-consumers, not "nothing else" (D1).** A field is mirrored
iff it is consumed by the §3.3 reason vocabulary or the §7.3 contract-table lookup key, enumerated
per consumer below. This is a normative enumeration, not an example — a field not listed here is not
mirrored, and a new consumer that needs a field not listed requires a visible edit to this table, not
a silent addition to `graph.py`.

**Round-4 remediation (Cluster 2 — B4 + B5 + M1 + m1, one pass over this table, fix 8-12).** The
round-3 table was simultaneously OVER-inclusive and UNDER-inclusive, and this pass fixes both in one
place rather than four separate, potentially-inconsistent edits:

- **Over-inclusive (M1, CONCEDE):** `line_number`, `node_type`, and `arguments` were mirrored but
  never read by anything except `graph.py`'s own declaration/parse — confirmed by grep of the whole
  `src/plr_sema/` tree. `line_number` was `0` for all four fixture operations, so a `PlrSite` built
  from it would have been silently wrong, and the fixture could not have caught it. **Deleted**, along
  with their extraction in `_operation_from_dict`.
- **Over-inclusive, with a live false-positive risk (B4, CONCEDE):** `arguments`/`depends_on_params`
  fed `argument_not_static`, which §3.3 has now withdrawn entirely (see §3.3's B4 note) — the
  guard-`free_vars` namespace and the `depends_on_params` protocol-parameter namespace it intersected
  are disjoint in every shipped fixture, so the reason never fired, and a same-named collision would
  have fired it for no semantic cause. `arguments` is **deleted** (confirmed never read outside
  `graph.py`'s own parse); `depends_on_params` is **kept**, despite currently having no consumer,
  because it is the one piece B4's reinstatement note names as still needed for a future, correctly
  specified `argument_not_static` (guard free var → PLR parameter position → `arguments[param]` →
  protocol expression → `depends_on_params`) — the same forward-looking treatment `receiver_variable`
  already got below (m1), not a silent violation of "derived-from-consumers" but a flagged exception
  to its letter in service of its spirit.
- **Under-inclusive (B5, PARTIAL):** see the new paragraph below this table — `preconditions`/
  `creates_state` and `condition_expr`/`true_branch`/`false_branch` are addressed there, not by adding
  rows here.
- **Unconsumable justification (m1, PARTIAL):** `ResourceNode`'s justification is restated
  forward-looking, not as a live consumer — see the paragraph after the table.

| `OperationNode` field (`plr_static_analysis/models.py`) | consumer |
|---|---|
| `receiver_type` (`:535`) + `method_name` (`:533`) | §7.3 contract-table lookup key, `f"{receiver_type}.{method_name}"` (e.g. `"LiquidHandler.aspirate"`) |
| `receiver_type` (`:535`), checked for `None` | reason `receiver_type_unknown` |
| `method_name` (`:533`), paired with `receiver_type` and checked against the whole-survey contract table (§7.3; **redefined 260901 T11** — no longer the copied `SUPPORTED_TOOLS` set, see the paragraph below) | reason `unsupported_tool` |
| `foreach_source` (`:551`), `foreach_body` (`:554`) | reason `loop_bounds_unknown` (deferred item (d)'s placeholder — these fields identify the loop construct, not its bounds) |
| `id` (`:531`) | `Finding.operation_id` provenance (AC-6.4) |
| `receiver_variable` (`:534`) | matching a resource reference against the mirrored `ResourceNode` set, below (forward-looking — see m1 paragraph below) |
| `depends_on_params` (`:546`) | no current consumer — forward-looking; a future, correctly-specified `argument_not_static` needs it (B4, above) |

**`ResourceNode` is mirrored too.** `ungroundable_reference` (§4.1) — "a resource variable with no
`ResourceNode` in the graph" — has no other source: it is a graph-membership test (does
`OperationNode.receiver_variable` correspond to a `ResourceNode.variable_name` present in the graph's
`resources` mapping? — `variable_name`, not `id`: the live `ResourceNode` model has no `id` field, see
`check/graph.py`'s own SPEC GAP note), which requires `check/graph.py` to carry a minimal
`ResourceNode` mirror alongside the `OperationNode` mirror. **No third model hierarchy is
introduced** — this pair of stdlib mirrors is the *only* model hierarchy `check/` ever sees. This
retires the pydantic-under-Pyodide question (formerly RISK-6, §6.4/Risk table) as moot for `check/`:
pydantic is simply never imported there. A server-side `extract/` (round 2) may still use pydantic
freely, since it never ships to a browser.

**`ResourceNode`'s justification, restated forward-looking (round-4 remediation, m1, PARTIAL).** The
membership test itself (`is_grounded`) is not wired into any `Finding` in round 1 — wiring it would
need a reason meaning "resource reference is ungroundable", which the closed §3.3 vocabulary (now 7
members, was 8 — B4 above) does not have. The mirror and the membership-test helper exist so the
mechanism is *ready* — five slots of headroom remain under §3.3's hard cap of 12 (7 today) — and so
Fork C's field-set drift test (§5.3) has a real comparison target in the meantime, not because
anything consumes it today. This is a forward-looking justification, not a live-consumer one, stated
as such rather than implying present use.

**Why `preconditions`/`creates_state`/`condition_expr`/`true_branch`/`false_branch` are deliberately
NOT mirrored (round-4 remediation, B5, PARTIAL).** Two sub-claims were raised about these five fields;
one holds, one does not, both are addressed here rather than by adding rows above:

- `preconditions`/`creates_state` are produced by four hand-typed frozensets in
  `computation_graph_extractor.py:41-70` (`TIPS_REQUIRED_METHODS`/`TIPS_LOADING_METHODS`/
  `PLATE_ACCESS_METHODS`, roughly) asserting facts like "`aspirate` requires tips" — this is a
  hand-written method contract, the precise thing decision 2 bans, and it is §8's comparison
  **target**, not an input `check/` may consume. Mirroring these fields into `check/` would launder a
  hand-written contract through the "mirror, not hand-written" framing without changing what it is.
  **Not mirrored, by design, not by oversight.**
  - The alleged "third source of truth disagreement" between these fields and the survey's own
    flow-sensitive tip tracking does **not** exist: `computation_graph_extractor.py:547` reads
    `if method_name in TIPS_REQUIRED_METHODS and "tips_loaded" not in self._active_states`, and
    `pick_up_tips` (op_1) already adds `tips_loaded` to `_active_states` at `:457` — so `aspirate`
    (op_2) correctly omits the precondition because it was already satisfied by the preceding
    operation. That is flow-sensitive satisfaction working correctly, not a disagreement, and there is
    nothing for §8 to compare here.
- `condition_expr`/`true_branch`/`false_branch` genuinely have no round-1 consumer, but they are named
  here as (a)'s required inputs for the *reachability* proof `join` currently omits (§3.2's boundary
  declaration; `260901_plr-sema-research-a-d.md:136-146`) — i.e. they are the field-set cost of eventually building
  (a)'s attachment point, not dead weight. **Additional cost, ratchet-visible under HM-21:** when (a)
  lands, the mirror field-set change these three fields represent, plus fixture regeneration, is a
  real, visible cost §3.2's boundary-summary table (§Deferred) should be read alongside.

> **FLAG — `check_graph` is degenerate, not inert, under the pre-fix mirror, and the failure mode is
> worse than a hard failure (D1).** Before this fix, `receiver_type_unknown` was reachable and
> AC-6.4 was satisfiable using only the `id` field — meaning AC-6.3's "≥1 finding" requirement could
> pass on a finding that required no contract-table lookup at all, with the contract table entirely
> unexercised. A gate that passes without touching the thing it is meant to gate is worse than one
> that fails, because it hides the gap instead of surfacing it. The derived-from-consumers table above
> closes this specific hole for `receiver_type_unknown` (it is still a legitimate, cheap reason — the
> concern was never that it exists, but that it alone could satisfy the AC) — implementers and
> reviewers should confirm AC-6.3/AC-6.4 are exercised against a fixture where **at least one**
> operation's contract-table lookup actually succeeds or fails on a populated table, not solely via
> `receiver_type_unknown`.

**Adjacent fix, same location: `unsupported_tool` needs `SUPPORTED_TOOLS`, copied not imported
(D1).** The reason `unsupported_tool` (§3.3) was originally (round 1–6) checked against
`SUPPORTED_TOOLS` (`training/verify/dispatcher.py:37-41`), a 10-tool frozenset. `check/` is
stdlib-only and forbidden from importing `praxis`/`verify` (§1.3) — so `SUPPORTED_TOOLS` had to be
**copied verbatim** into `plr_sema/check/`, exactly as §4.1 copies `FAILURE_CATEGORIES` rather than
importing `training.verify.failure_taxonomy`. **No new registry row was needed** — HM-9 (§9.2)
already registered `SUPPORTED_TOOLS` as a fact; the copy is the same fact physically duplicated across
a package boundary, not a new hand-typed fact. The copy needed the same drift protection §4.2 gives
`FAILURE_CATEGORIES`: `test_supported_tools_match_upstream` (living in `tests/`, which may import both
`plr_sema.check` and `training.verify.dispatcher`, since the import-boundary restriction is scoped to
`src/plr_sema/` per §1.3) asserts set equality, skipped with an explicit reason if `training.verify` is
not importable.

**Redefined, 260901 T11: `unsupported_tool` no longer checks `SUPPORTED_TOOLS` membership.** T11
decouples §7's derivation pipeline from `SUPPORTED_TOOLS` entirely — `plr_sema.derive` now derives a
contract for every method the survey indexed (4,770 at the current pin, not just the 10 tool names,
§7.3/§7.6), so `SUPPORTED_TOOLS` membership and "has a contract table entry" are no longer the same
question, and gating `unsupported_tool` on the former would have silently re-imposed the 10-method
scope this task exists to remove. `_findings_for_operation`'s step 2 is now a single lookup:
`f"{op.receiver_type}.{op.method_name}"` absent from the (now whole-surface) contract table ⇒
`unsupported_tool`. `SUPPORTED_TOOLS` and its copy/drift-test (previous paragraph) are UNCHANGED and
still shipped — `plr_sema.check.SUPPORTED_TOOLS` still exists, is still re-exported, and
`test_supported_tools_match_upstream` still passes — but the set is now purely informational
(`plr_sema.derive.build_gap_ledger`'s `supported_tools`-scoped reporting subset) plus the one drift
test; it no longer gates which methods get a derived contract or which `Finding.reason` an operation
receives. See HM-9 (§9.2) for the registry-row restatement and `plr_sema.check`'s module docstring
("`unsupported_tool`, redefined") for the full mechanical account.

**Round-1 entry point: `check_graph(graph_json, contracts_json) -> AnalysisReport`, browser-side,
no libcst, no pylabrobot.** The `@jit` decorator and functional `check(fn)` form (source→graph,
server-side, requiring `extract/`) are **round 2** — `extract/` does not exist as a working
implementation in round 1 (see §6.4/C5 below on why building it now is circular). Round-1 tests and
ACs exercise `check_graph` directly against a **fixture graph JSON produced out-of-process**: either
a subprocess call into the existing `praxis.backend.utils.plr_static_analysis` extractor, or a
committed fixture file generated once by that route and checked into
`plr-sema/tests/fixtures/`. Producing that fixture is itself round-1 work (see T8 below); it is not an
`ast`-visible `praxis` import from `src/plr_sema/`, so §1.3 stays intact.

**In the pre-corpus state, `report.verdict` is `UNKNOWN` for every protocol**, and that is the
correct v1 behaviour per §0. Argument decomposition into (PLR resources / static-invariant / dynamic)
is performed by the existing extractor and surfaces as `ResourceNode` vs.
`OperationNode.depends_on_params` — no new classification logic is specified here.

**A resolved contract with zero guards, zero gaps, and no loop now synthesizes a fallback finding
(round-4 remediation, B1, CONCEDE, fix 3).** Round 1–3's `_findings_for_operation` mechanic (below)
produced an empty finding list for this combination, with a comment arguing it "does not occur for
any of the 10 `SUPPORTED_TOOLS` entries in the current `derived_contracts.json`". That argument was
true of the data but not a guarantee: if it ever DID occur — or if a graph had zero operations at
all — `join`'s pre-round-4 empty-multiset default (`SAFE`) fired on a reachable public path. `check/`
now appends a `no_contract_derived` finding (detail: `"contract resolved with zero guards, zero gaps
and no loop"`) whenever the per-operation walk produces nothing, independently of `join`'s own
now-unconditional empty-multiset handling (§3.2) — defense in depth, not the sole fix.

**On the "any stub passes" concern (partially rebutted):** AC-7.2's `len(findings) >=
len(operations)` and §7.5's `test_aspirate_closure_reaches_check_containers` are genuine anti-stub
gates already — a `check_graph` that returns a constant empty report fails both. The fixes above
strengthen an already-nonzero bar (giving `check_graph` a real fixture to run against, and pinning
`operation_id` provenance below), not repair a total absence of one.

### 6.3 Verification

```bash
uv run pytest plr-sema/tests/test_import_boundary.py::test_no_pylabrobot_import_under_check -q
uv run python -c "import plr_sema.check"   # in an env where libcst is NOT installed
```

- The AST boundary test (§1.3) mechanises the prohibition — **DERIVED**.
- `test_check_imports_without_libcst` — spawn a subprocess with `sys.modules['libcst'] = None` and
  `sys.modules['pylabrobot'] = None` installed via a `sitecustomize` shim (or a `-c` preamble that
  poisons both entries), then `import plr_sema.check`. Assert exit 0. Poisoning is stronger than
  simply not installing them, because it fails even if the import is merely *reachable*.
- `test_fixture_graph_yields_unknown_report_with_findings` — load the **committed fixture** graph JSON
  (produced out-of-process by the existing praxis extractor, per §6.2; round 1 does not extract live),
  deserialize in a fresh process with PLR poisoned, feed to `check_graph`. Assert an `AnalysisReport`
  is produced (round-6 remediation, R20 — shipped under this name; earlier round text named it
  `test_graph_json_round_trips`, which does not exist in `tests/test_check_graph.py`).
- `test_operation_ids_are_a_subset_of_real_graph_ids` (AC-6.4) — **naming note (round-6 remediation,
  R20).** The shipped name says "subset"; the shipped body asserts *equality*
  (`{f.operation_id for f in report.findings} == {op.id for op in graph.operations}`), per the
  round-4 B2 strengthening below. The name should be renamed `test_operation_ids_equal_real_graph_ids`
  to match; recorded here as a known discrepancy rather than corrected in this documentation-only
  pass — the assertion itself, not the function name, is what AC-6.4 gates.
- `test_supported_tools_match_upstream` — **new, D1.** Imports `SUPPORTED_TOOLS` from both
  `plr_sema.check` (the copy) and `training.verify.dispatcher` (upstream), asserts set equality. Same
  drift-test pattern as §4.2's `test_categories_match_upstream`; skipped with an explicit reason if
  `training.verify` is not importable.

**Classification: DERIVED** — the prohibition is enforced by walking our own AST; no manifest of
allowed modules for `check/` is typed beyond the two banned names, which are themselves the
statement of the constraint rather than a maintained list.

### 6.4 Failure mode

**Assumption:** the extract/check cut is placeable — i.e. no analysis step genuinely needs CST access
at check time.

**If wrong:** some contract application turns out to require re-parsing PLR source in the browser, and
the split collapses. **Detection:** `test_check_imports_without_libcst` fails the moment someone
reaches for libcst in `check/`. **Response:** push the work into `extract/` and enrich the wire
format — the derived contract table is precisely the artifact designed to absorb this, since it is
computed once, server-side, and shipped as data. **Residual risk:** the contract table could grow
large enough to be an unacceptable browser download. Not measurable pre-corpus; recorded as RISK-5.

### 6.5 Acceptance criteria

- **AC-6.1** `import plr_sema.check` succeeds in a process where both `libcst` and `pylabrobot` are
  poisoned to `None` in `sys.modules`.
- **AC-6.2** `test_no_pylabrobot_import_under_check` fails when a scratch `import libcst` is added to
  any `check/` module.
- **AC-6.3** The **committed fixture graph JSON** (produced out-of-process by the existing praxis
  extractor, §6.2), passed to `check_graph` in a PLR-poisoned subprocess, yields an `AnalysisReport`
  with `verdict == UNKNOWN` and ≥1 finding.
- **AC-6.4** (round-4 remediation, B2, strengthened from subset to surjectivity, fix 6) For the
  fixture protocol, `{f.operation_id for f in report.findings} == {op.id for op in
  graph.operations}` — EQUALITY, not just `⊆`. The pre-round-4 subset-only form was the
  anti-fabrication anchor but said nothing about coverage: `len(findings) >= len(operations)` (AC-6.3)
  does not imply every operation actually received ≥1 finding, and a `check_graph` that only ever
  emitted findings for one operation would have passed both the subset check and the count-only check
  simultaneously while silently never reporting on the rest (`260901_plr-sema-research-a-d.md:348-354`).
- **AC-6.5** (D1) `test_supported_tools_match_upstream` passes with `training.verify` importable —
  i.e. the two `SUPPORTED_TOOLS` copies are genuinely equal today, not merely skipped.
- **AC-6.6** (D15, moved from AC-3.4) An `AnalysisReport` produced by running the full T8 pipeline
  (fixture graph JSON → `check_graph` → report) over the fixture protocol serializes to JSON and
  deserializes field-identically. AC-3.4 (§3.6) covers the narrower, earlier-available claim —
  constructing an `AnalysisReport` directly and round-tripping it — which does not require T8.
- **AC-6.7** (D15, moved from AC-4.3; round-4 remediation, M8, rewritten to a falsifiable identity,
  fix 23) With `JsonlSink` attached BEFORE the run, `check_graph` itself (M2, §4.1/§4.2 — it now
  emits) over the fixture protocol emits ≥1 line, every line parses, and every line's
  `stamp.plr.hash` equals **`contracts_payload["stamp"]["plr"]["hash"]`** — the stamp the
  `derived_contracts.json` fixture ACTUALLY carries, not a hardcoded pin string. A hardcoded pin
  passes silently against an arbitrarily stale artifact (`stamp` is build-time-only provenance, per
  `AnalysisReport`'s docstring, §3.1) — the falsifiable identity form catches drift a fixed string
  cannot. The `dd79c4c89` pin is retained as a secondary, self-scoping sanity check that the identity
  holds against a value confirmed live for the current checkout, not as the primary assertion.

---

## 7. Contract-derivation pipeline — mechanics only

**Mechanics only.** This section specifies graph plumbing over data that already exists on disk. It
specifies **no** predicate semantics, **no** abstract domain, **no** loop handling. Those are
deferred items (a)–(f).

### 7.1 Input — regenerated by round-5 T0, pinned thereafter

`training/verify/data/plr_preconditions.json` (3.0 MB → **3.39 MB after round-5 T0**, below). Record
schema confirmed this session at `scripts/survey_plr_preconditions.py:74-120`:

```
{qualname, class_name, module, file, lineno, params[],
 findings[{kind, condition, raises, scope_trail[], mentions_params[], lineno}],
 delegates_to[], unresolved_calls[], dropped_calls[]}
```

**`dropped_calls[]` — new field, round-5 remediation (F1, PARTIAL — the additive half only,
CONCEDE).** Every call whose receiver is an `ast.Attribute` but is NOT the literal `self.<name>(...)`
shape (`self.head[channel].get_tip()`, `tip_spot.get_tip()`, ...) previously left **no trace at all**
— not a `delegates_to` entry, not an `unresolved_calls` entry, nothing. `visit_Call`'s dispatch on
`target` gains a third branch (4 hunks, 9 lines of code) recording the FULL receiver-qualified call
expression (`ast.unparse` of the whole `Call.func` node — `self.head[channel].get_tip`, not the bare
`get_tip`), so a reader can distinguish it from `tip_spot.get_tip`. **Strictly additive, measured:**
regenerating the whole survey (`scripts/verify_survey_additivity.py`) against the pre-T0 artifact
shows 4,770/4,770 records, **0 non-additive diffs** across every pre-existing field
(`qualname`/`class_name`/`module`/`file`/`lineno`/`params`/`findings`/`delegates_to`/
`unresolved_calls`) and every top-level meta field; the sole new key is `dropped_calls`. Run time 1.5s.
`derive/`'s `_record_from_dict` reads every field via `.get()` and ignores unknown keys, so this
required **zero consumer changes** and **zero test rebaselines** (all nine gate files, 91 tests,
passed unmodified before and after). **What round 5 declined (F1's interpretive half):** deleting
T6's second, independent AST pass (`scan_dropped_receiver_calls` et al.), redefining `gaps` to include
`dropped_calls`, deleting §7.4's asymmetry note below, or answering RISK-1 with a bare `0/10`. See
[§Remediation changelog (round 4 → round 5)](#remediation-changelog-round-4--round-5), F1, for why: the
`0/10` figure the challenge's patch produces is generated by `logger.debug`/`inspect.signature`/
`warnings.warn` saturating every `SUPPORTED_TOOLS` closure through `_check_args`, not by tip-state
guards, and the disambiguation it claims to supply was already published
(`gap_ledger.json`'s `dropped_receiver_calls_by_method`, all ten `SUPPORTED_TOOLS` entries nonzero,
round-4 M11).

**Retitled from "already on disk, do not regenerate" (round-5 remediation, F6, PARTIAL).** §7.1's
prior title had hardened a scheduling convenience into an apparent prohibition; round 5's challenge
demonstrated regeneration costs 1.5s and is byte-identical on every pre-existing field (above). The
spec's actual instinct — don't let derivation silently depend on a moving input — is preserved by
**pinning after T0**, not by never regenerating at all.

Measured contents: 4,770 functions scanned, **1,314 with ≥1 finding**, **2,081 `raise_guard` + 733
`assert`** findings, **967 unresolved-call entries across 854 functions (75 distinct call names)** —
`unresolved` is a per-function `set` of bare names (`survey_plr_preconditions.py:138,263`), so the
967 figure counts (function, name) entries, not distinct calls or call sites; names are not
class-qualified, so unrelated `_check_*`-style helpers defined on different classes collapse into one
row if they share a bare name (`plr_survey_common.py:127-129` independently confirms duplicate class
names exist in the PLR surface, the same fact §7.2's index-key resolution rule has to account for).
(N=854, M=75 measured this remediation round via a `grep`-based extraction of every non-empty
`unresolved_calls` array plus manual dedup of the resulting name list — not an automated script run,
so treat as a spot-check pending T6's authoritative gap-ledger figures, not a re-derivation of the
survey.) Companions: `plr_exception_taxonomy.json` (132 classes; **not merely a companion — §8.1's
bridge requires loading it, via a required `--taxonomy-json PATH` on `plr_sema.differential`, no
default, D19**), `plr_deprecations.json` (166 sites).

### 7.2 The mechanic — transitive closure over `delegates_to`

The load-bearing example, which motivates the entire section: **`LiquidHandler.aspirate` has only 3
findings in its own body**, but `delegates_to = [_check_args, _check_containers, _check_no_lid,
_compute_spread_offsets, _log_command, _make_sure_channels_exist]`. The real preconditions live in the
delegates. A derivation that reads only a method's own `findings` would conclude `aspirate` is nearly
unconstrained — dangerously wrong in the `SAFE` direction.

**Normative resolution rule for `delegates_to` entries.** `delegates_to` holds **bare** method/function
names (`survey_plr_preconditions.py:253` adds a same-class name; `:255` adds a bare module-level
name) — it is not a qualname and not `(module, qualname)`. The survey index (below) is keyed by
`(module, qualname)`, so a delegate must be **resolved** before lookup:

```
resolve(name, rec) -> (module, qualname) | None:
  1. if rec.class_name is not None:
       candidate = f"{rec.class_name}.{name}"
       if (rec.module, candidate) in index: return (rec.module, candidate)
  2. if (rec.module, name) in index: return (rec.module, name)     # module-level function
  3. gaps.append(("no_contract_derived", name)); return None
```

**Class-first precedence is explicit and normative**: step 1 (same-class method) is tried before step
2 (module-level function) unconditionally. The residual ambiguity — a class method and a module-level
function sharing the same bare name in the same module — is **accepted**: step 1 wins, step 2 is
never reached for that name in that module. `plr_survey_common.py:127-129` already proves duplicate
class names exist in the PLR surface, so this is not a hypothetical edge case; it is a known,
accepted imprecision, not a bug. **No survey regeneration is required** — the discriminator needed to
build `resolve` (same-class vs. module-level vs. unresolved) is exactly what
`survey_plr_preconditions.py:256`/`:302` already computed at survey time; `delegates_to`'s bare-name
records are a **projection** of that discriminator, and `resolve` reconstructs it via lookup against
the `(module, qualname)`-keyed index rather than needing a new field.

The index itself: `index: dict[tuple[module, qualname], Record]`, built once from
`plr_preconditions.json` by keying every record on `(rec.module, rec.qualname)`.

**`(module, qualname)` is not unique in the artifact — last-in-source wins (round-5 remediation, F6,
PARTIAL — the collision conceded in full, "four implementations disagreeing" rebutted).** 12 keys
collide at the current pin (8 among the 1,314 finding-bearing records), all `@property`/`@x.setter`
pairs (`Serial.dtr`/`Serial.rts`, `SerialValidator.dtr`/`SerialValidator.rts`, ...) — AST traversal
visits class members in source order and a setter is conventionally defined after its getter, so
`build_index`'s `{key: rec for rec in records}` silently keeps the setter and discards the getter.
This was previously undocumented; `4,758` (`4,770` minus the twelve collisions) is first computed
here, not previously appeared — §7.1 publishes only the `4,770` scan count, with no distinct-key
figure and no explanation of a delta. **Not fixed by
changing `resolve()`**: bare-name delegate resolution (above) has no `lineno` to disambiguate a
getter from its setter, so `resolve()`'s class-first precedence is intentionally unchanged. Two things
changed instead: (1) `build_index(records)` now DOCUMENTS the discard is deterministic
(lowest-`lineno`/getter-preferring across ties, not "whichever the dict comprehension visited last")
and (2) a companion `build_unique_index(records) -> dict[(module, qualname, lineno), Record]` gives
any caller that needs every record addressable a collision-free key (two records cannot share one
module's one definition `lineno`), plus `count_index_key_collisions(records)` measures the discard
rather than leaving it silent — surfaced in the gap ledger as `index_key_collisions` (§7.4). None of
the twelve collisions sit inside the ten-`SUPPORTED_TOOLS` closure, so this does not change any
`SUPPORTED_TOOLS`-scoped figure published below — the impact is on whole-surface population counts
only (§7.4's 671-vs-667 footnote). **"Four implementations of one predicate, four answers"** (the
challenge's characterization of `674`/`671`/`667`/the patch's `649`) **is rebutted**: 671 is
`_methods_with_dropped_receiver_call` over the 1,314-record population, 667 is the identical predicate
over the 1,306-distinct-key population (the collision above), and 649 is a structurally NARROWER
traversal (the survey's own in-body scanner, blind at `if`-test/`raise`-argument/`assert`-test
positions — 18 methods lost, 0 gained, strict subset) — one predicate over three named, explainable
populations, not four disagreeing implementations. `674` was an earlier, unreproduced estimate,
superseded when `671` was derived in code (round-4, M11).

```
derive_contract(module, qualname) -> DerivedContract:
  1. seen = set(); frontier = [((module, qualname), 0)]; guards = []; gaps = []
  2. while frontier:
       (q, depth) = frontier.pop()
       if q in seen: continue          # cycle-safe: PLR delegation graphs may cycle
       seen.add(q)
       rec = index.get(q)  or  (gaps.append(("no_contract_derived", q)); continue)
       for f in rec.findings:
           guards.append(InlinedGuard(
               condition   = f.condition,           # RAW STRING. Not parsed. (deferred (c))
               scope_trail = f.scope_trail,         # RAW STRINGS.
               raises      = f.raises,              # exception class name, `None` (assert), or a
                                                     # "<dynamic:...>"-prefixed sentinel — detect via
                                                     # `raises.startswith("<dynamic:")` (D18), never by
                                                     # equality against a literal glob string
               kind        = f.kind,                # "raise_guard" | "assert" -- see §7.2's polarity note
               free_vars   = f.mentions_params,     # the predicate's free variables
               site        = PlrSite(rec.file, f.lineno, rec.qualname),
               depth       = depth,                 # 0 = own body, >0 = inlined from a delegate; carried on the frontier, not derived from `len(seen)`
           ))
       for name in rec.delegates_to:
           resolved = resolve(name, rec)
           if resolved is not None:
               frontier.append((resolved, depth + 1))
       for u in rec.unresolved_calls:
           gaps.append(("unresolved_delegate", u))
  3. return DerivedContract(qualname, guards, gaps, stamp=survey_stamp())
```

Three properties this mechanic must have, all testable without semantics:

- **Cycle-safe.** `seen` is checked before expansion. PLR's `delegates_to` graph is not guaranteed
  acyclic and a naive recursion would hang. `_check_args` calling a helper that calls back is
  entirely plausible.
- **Provenance-preserving.** Every guard carries the `PlrSite` of the *file that actually contains
  it*, not of the entry-point method. A `WILL_FAIL` on `aspirate` must point at
  `_check_containers`'s real line, because that is where a user or a fixer must look. `depth` is
  carried explicitly as a `(qualname, depth)` pair on the frontier — **not** derived from
  `len(seen)`, which counts total nodes visited across the whole closure (a visit counter), not
  distance from the entry point, and would be wrong under LIFO `frontier.pop()` traversal order.
- **Gap-recording, never gap-hiding.** `unresolved_calls` entries reached during a closure become
  recorded gaps, which become `UNKNOWN` findings with `reason="unresolved_delegate"`. This is the
  *measurable frontier*, and it is exactly what the survey deliberately declined to resolve
  (`survey_plr_preconditions.py:30-37`: only same-class `self.<name>(...)` and module-level
  `bare_name(...)` calls are attributed, because cross-class calls like `self.head[channel].get_tip()`
  need type inference). **This bullet's own boundary is narrower than it looks — see §7.4's**
  **"upper bound" note**: **the corrected predicate (D3) is `func` is `ast.Attribute` AND NOT
  (`func.value` is `ast.Name` with `id == "self"`)** — i.e. the survey does not attempt to record
  *any* `<expr>.<method>()` receiver other than the literal name `self`, not merely a `Subscript`
  receiver on `self`. This includes plain `resource.get_item()`-style calls, where `<expr>` is itself
  a bare `ast.Name` (just not `self`) — a shape the round-2 text's "Subscript, not a bare `self`"
  framing incorrectly implied was already covered. So the true unresolved-call frontier is larger
  than what `unresolved_calls` reports, and larger than the round-2 framing suggested; the gap
  ledger's completeness figures must be read accordingly.

**`condition` and `scope_trail` are carried as opaque strings in v1.** Turning them into checkable
predicates is deferred item (c). This is what keeps §7 mechanical.

**Guard polarity (normative, C4).** `InlinedGuard.kind` is `"raise_guard"` when the finding came from
`raise_guard`'s recording rule (`condition` is the nearest enclosing `if` test; the guard **fires
when `condition` evaluates true** — `survey_plr_preconditions.py:212-222`), and `"assert"` when it
came from an `assert` statement (the guard **fires when `condition` evaluates false** — `:226`).
733 of 2,814 recorded findings (26%) are asserts. Dropping `kind` makes this polarity permanently
unrecoverable from the shipped artifact, which is why `InlinedGuard` carries it as a first-class
field rather than folding it into `condition`'s text.

**`condition is None` means the guard fires UNCONDITIONALLY, not "no constraint" (round-4
remediation, m5, CONCEDE).** `condition` is a raw, unparsed string in v1 (above) and `None` is a real
value the survey emits, not a missing-field sentinel — 379 of 2,814 (13.5%) of survey findings, and 9
of the 119 guards in the shipped `derived_contracts.json`, carry `condition: null`. `check/`'s
`_finding_from_guard` used to map `condition is None` to `Finding.detail = ""` via
`guard.get("condition") or ""` — indistinguishable from an empty-string condition, and unsound in the
`SAFE` direction if a future round ever reads `detail` as evidence (it does not today; `detail` is
explicitly never-parsed, §3.5, so this was latent, not live). `condition is None` now maps to the
explicit sentinel string `"<unconditional>"` in the emitted `Finding.detail`.

**Classification: DERIVED.** The derivation: transitive closure over the `delegates_to` field of an
AST-derived survey of PLR source, stamped by §2.2. Zero contract bodies are typed. This is decision
2, discharged.

> **FLAG — decision 2 is implementable but will *underperform* the 45 hand-written contracts it
> replaces, and the spec should say so rather than let it surface as a surprise.** "No hand-written
> method contracts" means a method whose closure hits an unresolved cross-class delegate yields
> `UNKNOWN`, not a hand-patched answer. Today's `method_contracts.py` has a human-asserted answer for
> 45 methods. Some fraction of those 45 will become `UNKNOWN` under derivation. That is *correct*
> (the hand-written answer was an unverified assertion) and it is *worse for users* (fewer actionable
> verdicts) simultaneously. §8's differential harness measures the fraction. **Decision 2 is
> therefore only sustainable if the differential harness is treated as a research instrument rather
> than a regression gate** — if a `DERIVED=UNKNOWN` vs. `HAND=answer` disagreement blocks a merge,
> the pressure to hand-patch returns immediately and decision 2 fails in practice. This spec treats
> §8 as an instrument (see AC-8.x: no threshold gates on agreement rate).

### 7.3 Output — the derived contract table

Serialized to `plr-sema/data/derived_contracts.json`, a **build artifact, never hand-edited**:

```json
{"schema_version": 1,
 "stamp": {"...": "SurveyStamp"},
 "contracts": {"LiquidHandler.aspirate": {"guards": [], "gaps": []}}}
```

**Whole-surface, not `SUPPORTED_TOOLS`-only (260901 T11).** `contracts` now holds one entry per
record the survey indexed — **4,770 at the current pin** (345 classes, 28 PLR subpackages), not just
the 10 `SUPPORTED_TOOLS` names it held through spec_version 6. The key is `qualname`
(`"LiquidHandler.aspirate"`, matching `check/`'s `f"{receiver_type}.{method_name}"` lookup, §6.2)
**unless that name collides across >1 record in the whole survey**, in which case the key is
`f"{qualname}@{module}:{lineno}"` — see "Contract-table key collisions" below. A record with zero own
`PreconditionFinding`s still gets an entry (`guards: []`), possibly non-empty if its `delegates_to`
closure reaches a finding-bearing method (measured: 580 of the 3,456 zero-own-finding records do);
`gaps: []` only if the closure is also gap-free. Measured at the current pin: 4,770 total entries,
2,592 non-empty (1,314 finding-bearing + 580 zero-own-finding-but-delegate-guarded + 698
zero-own-finding-with-only-gaps), 2,178 fully empty (`guards: []`, `gaps: []`) — the "known and
unconstrained" case, §0/RISK-1's zero-findings decision (below). Serialized size at the current pin:
4.4 MB pretty-printed, 3.0 MB minified, 146 KB gzipped — payload growth from the pre-T11 68 KB
(10-entry) artifact is real but not a blocker at this scale (measured, not estimated).

**Contract-table key collisions (T11 item 2).** The bare-`qualname` key collides for 26 distinct
names across the whole 4,770-record survey (52 records) — a strictly LARGER population than
`build_index`'s `(module, qualname)` collision count (12 records, §7.2's F6), because a bare
`qualname` also collides across DIFFERENT modules for same-named module-level functions (e.g.
`_height_of_volume_in_spherical_cap`, defined independently in both
`pylabrobot.resources.height_functions` and `pylabrobot.resources.height_volume_functions`) — a
collision source `(module, qualname)` structurally cannot see, and one the task brief that scoped
this work did not anticipate (it cited only the 8 finding-bearing property/setter pairs). The
disambiguator (`build_contract_keys`, `plr_sema.derive`): if `qualname` is unique among the population
being emitted, the key is the bare `qualname`; otherwise it is `f"{qualname}@{module}:{lineno}"` —
`(module, qualname, lineno)` is collision-free by construction (`build_unique_index`'s own assertion:
two records in one module cannot share a definition line), so this single rule resolves both
collision sources without branching on which produced it. **Known, accepted limitation:** a
disambiguated key is unreachable via `check/`'s lookup format (`receiver_type.method_name`, no module
or line number) — every measured collision is either a property/setter pair (accessed via attribute
syntax, never emitted as an `OperationNode` by an extractor that only records `ast.Call` sites) or a
module-level function with no receiver at all (never reachable through `receiver_type.method_name` in
the first place) — so no entry point any real graph could name is made unreachable by this choice.
`test_contract_keys_are_collision_free` (`tests/test_derive.py`) pins both collision sources and
asserts collision-freedom against real survey data.

**The zero-findings decision (T11 item 4).** The survey scans 4,770 methods; 1,314 bear ≥1
`PreconditionFinding`. A method the survey scanned but recorded zero findings for is **known and
unconstrained as far as the survey sees** — a materially different fact from a method the survey
never scanned at all (not PLR, a typo, or a receiver type outside the analyzed surface). This
decision required choosing whether `contracts` carries entries for the 3,456 zero-finding methods,
and the answer is **yes, derived exactly like any other entry point** (not a special-cased empty
stub): `derive_contract` is run with every one of the 3,456 as its own entry point, exactly as for
the 1,314 finding-bearing ones. This is load-bearing, not merely tidy — measured, 580 of the 3,456
inherit ≥1 REAL guard through their `delegates_to` closure (e.g. `PlateReader.read_absorbance` has
zero own findings but delegates to `get_plate`, which has one); treating zero-own-finding methods as
out of scope for derivation, rather than merely for their OWN body's findings, would have silently
dropped every one of those 580 inherited guards — the same own-body-only failure mode §7.2 exists to
prevent, recurring one level up at entry-point selection instead of closure-walking. The remaining
2,178 (zero own findings, empty closure) get a real but empty entry (`guards: []`, `gaps: []`), which
`check/`'s existing zero-guards/zero-gaps/no-loop fallback (round-4 B1/B2, §6.2) already turns into
one `no_contract_derived` `Finding` — "known and unconstrained" reuses an existing reason rather than
needing a new `REASON_VOCABULARY` member (§3.3's closed 7-member set, cap 12, is unchanged by T11).
**`unsupported_tool`** (§6.2, redefined) is reserved for the disjoint case: a method name the
whole-survey derivation never saw at all — key absent from `contracts` entirely, not merely present
with an empty body.

This file is the payload the browser-side checker consumes (§6.2). It is regenerated by

```bash
uv run python -m plr_sema.derive \
    --survey-json training/verify/data/plr_preconditions.json \
    --out plr-sema/data/derived_contracts.json
```

**`--survey-json PATH` is required, with no default (D19).** `derive/` is a workspace member
forbidden to import `praxis` (§1.3's boundary is scoped to `src/plr_sema/`, but `derive/`'s own
independence from `praxis` is a separate, load-bearing property — see §1.4), so it cannot resolve
`training/verify/data/plr_preconditions.json`'s location via a `praxis`-relative import; a hardcoded
default path would silently couple `derive/` to the caller's repo layout. The flag makes the
dependency explicit and the invocation portable.

### 7.4 The gap ledger — a generated build artifact

Per decision 7, **not** a hand-maintained document:

```bash
uv run python -m plr_sema.derive \
    --survey-json training/verify/data/plr_preconditions.json \
    --gap-ledger plr-sema/data/gap_ledger.json
```

```json
{"schema_version": 1,
 "stamp": {"...": "SurveyStamp — this is what version-stamps the ledger"},
 "totals": {"methods_attempted": 0, "methods_with_no_recorded_gap": 0,
            "methods_with_gaps": 0, "methods_with_dropped_receiver_call": 0},
 "by_reason": {"unresolved_delegate": 0, "no_contract_derived": 0},
 "by_category": {"precondition_state": null},
 "by_category_status": "not_applicable_v1",
 "top_unresolved": {"whole_surface": [{"call": "send_command", "blocks_methods": 0}],
                     "supported_tools_closure": [{"call": "send_command", "blocks_methods": 0}],
                     "dropped_receiver": [{"call": "self.head[channel].get_tip", "blocks_methods": 0}],
                     "dropped_receiver_unfiltered": [{"call": "Coordinate.zero", "blocks_methods": 0}]},
 "dropped_receiver_calls_by_method": {"aspirate": 0},
 "validation_looking_dropped_receiver_calls_by_method": {"aspirate": 0},
 "index_key_collisions": {"all_records": 12, "finding_bearing_records": 8}}
```

**`index_key_collisions` — new field, round-5 remediation (F6, PARTIAL, minimal fix).** Reports how
many `(module, qualname)` keys `build_index` collapses (§7.2's last-in-source-wins note): `all_records`
over the whole 4,770-record artifact (12), `finding_bearing_records` over the 1,314 records
`methods_attempted` counts (8). Makes the collision a published measurement instead of an undocumented
delta between two prior figures (`4,770` vs. `4,758`).

**`top_unresolved.dropped_receiver` is now receiver-qualified and filtered, sourced from
`dropped_calls` — new, round-5 remediation (F1, PARTIAL, "the one durable win").** Previously sourced
from the independent D3 AST pass's bare `by_attr` breakdown (`{"call": "get_tip", "blocks_methods":
6}`); a bare name collapses `self.head[channel].get_tip`, `tip_spot.get_tip`, `channel.get_tip`,
`ts.get_tip`, `op.resource.get_tip`, `tracker.get_tip` into one indistinguishable row. Sourced instead
from the new `dropped_calls` field (above), ranked over the SAME `SUPPORTED_TOOLS`-closure population
(walked via the same `_walk_closure` core the other views use). **Unfiltered, this view saturates on
noise by construction** — every `SUPPORTED_TOOLS` closure passes through
`LiquidHandler._check_args`, which calls `inspect.signature`/`sig.parameters.items`/`args.keys`/
`', '.join`/`warnings.warn`, and every closure member logs, so an unfiltered ranking's top rows are
`logger.debug`-class plumbing plus `Coordinate.zero` (a value-factory classmethod call in several
tools' bodies, not a state-bearing receiver) — this is exactly why F1's unfiltered `0/10` closure
figure (below) is uninterpretable in the same way. The shipped `dropped_receiver` view excludes these
via a stated filter (round-5 T0 item 4): receiver prefixes that are never a typestate-bearing receiver
(`logger`/`logging`/`warnings`/`inspect`/`args`/`kwargs`/`sig`/`backend_kwargs`/`default`), trailing
call names that are generic container/string plumbing regardless of receiver (`keys`/`items`/
`values`/`union`/`join`/`append`/`get`/`update`/`format`/`strip`/`split`), and any call whose receiver
head is capitalized (a class/type-level call — `Coordinate.zero`, not an instance whose typestate this
analysis reads; real receivers in this population are always lowercase locals: `self`, `tip_spot`,
`channel`, `resource`, `container`, `tracker`, ...). The pre-filter ranking is published alongside it
as `dropped_receiver_unfiltered` rather than discarded, so the filter's own effect is auditable from
the artifact. Measured at the current pin: filtered rank 1 is `self.head[channel].get_tip`
(`blocks_methods: 3`); unfiltered rank 1 is `Coordinate.zero` (`blocks_methods: 4`), with
`logger.debug`/`logger.warning` also above the real signal. The D3 pass itself and its own two
counters (`dropped_receiver_calls_by_method`, `validation_looking_dropped_receiver_calls_by_method`,
and `methods_with_dropped_receiver_call`) are **unchanged** — round 5 declined deleting T6's second,
independent AST pass (F6: it is the only one of the three measured variants that sees guard sites
behind `if`/`raise`/`assert` tests).

**`by_category` is `null` per category, with a sibling `by_category_status` (round-4 remediation,
M3, CONCEDE).** Round 1–3's example (and the shipped generator) published `0` for every category.
That reads as a MEASUREMENT of zero, which is false: no gap this module records is EVER classified
into a `FAILURE_CATEGORY` in round 1 (a gap only ever produces an `UNKNOWN` finding downstream, never
`WILL_FAIL`, and `category` is validated only for `WILL_FAIL` per `Finding.__post_init__`) — there is
no detection mechanism yet for RISK-4's `harness_internal`-rate tripwire (§4.3), which only becomes
live once `WILL_FAIL` is first emitted, a future round's work. `by_category_status:
"not_applicable_v1"` names this explicitly rather than leaving a reader to infer "not applicable"
from six identical zeros.

**`top_unresolved` gains a third view, `dropped_receiver` (round-4 remediation, M12/Cluster 3/B3(e),
CONCEDE + PARTIAL).** The independent D3 AST pass (below) is computed correctly but was, until this
round, never ranked into a worklist — `supported_tools_closure` aggregates `unresolved_calls`, which
the dropped-receiver population structurally never enters (that is the entire point of calling it
"dropped" — see §7.6), so neither existing view could ever surface it. `dropped_receiver` ranks call
names from the D3 pass by how many distinct `SUPPORTED_TOOLS`-closure methods contain ≥1 call to that
name, the same `blocks_methods` semantics the other two views already use. This is the worklist B3
row (e)'s corrected reason (below) schedules a future task (T11) against — landing the counter
without the ranked view would leave that task with nothing to prioritize from.

**Field renamed: `methods_fully_derived` → `methods_with_no_recorded_gap`.** The old name claims more
than the survey can support. `survey_plr_preconditions.py:232` requires a call's receiver be
`ast.Name` with `id == "self"`; `self.head[channel].get_tip()` has a `Subscript` receiver, so `name`
stays `None` and the recording block at `:246-263` is skipped **entirely** — the call leaves no trace
at all, not even an unresolved-call entry. **The corrected predicate for the dropped population is
`func` is `ast.Attribute` AND NOT (`func.value` is `ast.Name` with `id == "self"`) (D3)** — this is
strictly wider than "`self.<expr>.<method>()`": it also drops `resource.get_item()`-style calls whose
receiver *is* a bare `ast.Name`, just not literally `self`. A method whose closure hits none of this
survey's *recorded* gaps can still have real, unrecorded preconditions hiding behind a dropped
receiver — `"methods_fully_derived"` would call that method fully derived; the new name does not make
that claim.

**Example correction (D10).** The dominant `top_unresolved` entry at the current pin is
**`send_command`** (750 of 967 entries, 77.6% — a firmware/transport method on `*Backend` classes,
D12), not `get_tip` — the JSON example above uses the empirically dominant name so the example
carries real information. This does not mean a bare `get_tip` can never be recorded: `self.get_tip()`
on a class that does not itself define `get_tip` *is* recordable (bare `self.<name>(...)` is exactly
the resolved shape, §7.2). What is unrecordable **by `unresolved_calls`/`delegates_to`, and by the
original two `top_unresolved` views that aggregate them,** is specifically the *literal*
`self.head[channel].get_tip()` shape (a `Subscript` receiver) — do not overstate the gap to "every
mention of `get_tip` is invisible." **Round-5 T0 (F1) makes this shape recordable, in a third field
(`dropped_calls`) and view (`top_unresolved.dropped_receiver`) — see §7.1 and the JSON schema below;
`unresolved_calls`/`delegates_to`/the whole-surface and `SUPPORTED_TOOLS`-closure `top_unresolved`
views are otherwise unchanged.**

**Normative — this is an upper bound, not a measurement of completeness.** The renamed count is an
**upper bound** on how many methods are genuinely fully derived, because the survey's own recording
rule cannot detect the receiver shapes it is most likely to miss. `top_unresolved` entries are bare
call names (`survey_plr_preconditions.py:235,256,263` extracts `target.attr` as a bare string, never
the full expression), so the literal `self.head[channel].get_tip()` shape is **unproducible** by this
mechanism — it would never appear in `top_unresolved`'s original `whole_surface`/
`supported_tools_closure` views even though it is exactly the shape §7.6 flags as the plausible
location of most tip-related preconditions. This claim is true as written (its subject is
`top_unresolved`'s bare-name views specifically) and round 5 leaves it unchanged for those two views —
what round 5 added is a THIRD view over a different field (`dropped_receiver`, §7.4's JSON schema
below), not a correction to this one. **`top_unresolved` was published in two views as of round 4
(D12), now three as of round 5 (F1, §7.4):** `whole_surface` — the honest aggregate over all 854
functions — and
`supported_tools_closure` — restricted to the transitive `delegates_to` closure of the 10
`SUPPORTED_TOOLS` methods, i.e. the actionable worklist. **AC-7.4 gates on neither view** — both are
measurement, not a threshold. Ranked by how many entry-point methods each unresolved call blocks,
`top_unresolved` is the prioritisation signal for deferred item (e) in both views, but it is a
worklist over the *recordable* frontier only, not the whole one. **Names are not class-qualified**
(§7.1), so an entry for a bare name shared by unrelated `_check_*`-style helpers on different classes
collapses into a single row in either view, potentially overstating that one name's true blocking
count. **A markdown rendering may be generated from this JSON; the JSON is the artifact and the
markdown is never the source of truth.**

**Asymmetry, load-bearing for RISK-1's interpretation — and the actual figures this predicts (D12).**
A **low** `methods_with_no_recorded_gap` still refutes decision 2's approach conclusively — real
preconditions demonstrably aren't being recovered. A **high** value is **uninterpretable** on its
own: it could mean the closure genuinely recovers most preconditions, or it could mean most
preconditions hide behind a dropped receiver and the survey simply never sees them to record as gaps.
**New work inside T6** (see task table) adds the counter that resolves this ambiguity: a second,
independent stdlib-`ast` pass over PLR source under `external/` (no `praxis` import — §1.3 is
untouched) computing, per method, **two counts (D3):** (1) the total count of call nodes matching the
corrected dropped-receiver predicate above (the honest figure — `dropped_receiver_calls_by_method`),
and (2) the subset of those whose attribute name is validation-looking, using the same
`_is_validation_looking` prefix test HM-3 already names
(`validation_looking_dropped_receiver_calls_by_method`, the tighter figure). **The primary figure
(1) must not gate on `_is_validation_looking`**: that gate is defined over the survey's own recording
block, which the dropped population never enters, so applying it to the *counter* (rather than the
survey) would be gating on a predicate that was never evaluated for this population. Separately, the
ledger also reports a method-level count, **`methods_with_dropped_receiver_call`** (D4; renamed from
the non-ASCII `methods_with_≥1_dropped_receiver_call` this round — round-4 remediation, m4, CONCEDE:
the shipped artifact and code always used the ASCII form, the spec prose was the one inconsistent
with it, and a non-ASCII wire-format key is a poor choice independently of the inconsistency) — this
is commensurable with `methods_with_no_recorded_gap` (both are *method* counts, unlike the per-method
call-node counts above, which are a secondary diagnostic, not a denominator for anything).

**Population fix (round-4 remediation, M11 first half, CONCEDE).** `methods_with_dropped_receiver_call`
used to be computed over ALL 4,758 indexed survey records while `methods_attempted` counted only the
1,314 finding-bearing ones — a population mismatch (the subset figure, 1976, exceeded its own
denominator, 1314). Both are now computed over the SAME `finding_bearing` population. Recomputed
this round, derived in code (not copied from any prior estimate): **671** — printed and reported by
the fixer, with a new self-consistency assertion
(`methods_with_dropped_receiver_call <= methods_attempted`) added to
`test_ledger_totals_are_internally_consistent` (§7.5) so this population mismatch cannot silently
recur.

**Population footnote — 671 vs. 667 vs. 649, three named populations, not four disagreeing
implementations (round-5 remediation, F6, PARTIAL).** `671` is `_methods_with_dropped_receiver_call`
computed over the 1,314-**record** `finding_bearing` population above. Over the 1,306-**key**
population (§7.2's collision, 8 finding-bearing records lost) the identical predicate gives `667` —
the gap is exactly the 8-record collision, not drift. A third figure, `649`, comes from evaluating the
same predicate inside the survey's OWN in-body scanner (round-5 challenge's patch) rather than T6's
independent second pass; it is strictly narrower (18 methods lost, 0 gained) because the survey's
`visit_If`/`visit_Raise`/`visit_Assert` never descend into `if`-test/`raise`-argument/`assert`-test
positions, which is precisely where several guard sites live
(`STARBackend._assert_valid_resources`, `VantageBackend._assert_valid_resources`,
`BioShake.set_temperature`). **`671` remains the published figure**: it is computed over the SAME
record population `methods_attempted` counts (so the self-consistency assertion above stays
meaningful), and it is the widest of the three traversals, not the narrowest.

**Closure-wide recomputation (round-4 remediation, M11 second half, CONCEDE).**
`dropped_receiver_calls_by_method`/`validation_looking_dropped_receiver_calls_by_method` used to look
up the D3 pass's counts by the entry-point key alone — own-body-only — which silently under-reports
every `SUPPORTED_TOOLS` method whose real dropped-receiver calls live behind a delegate rather than in
its own body. `stamp`/`transfer`/`move_plate`/`move_lid` reported `0` under the own-body-only form;
all four are nonzero once summed over the transitive `delegates_to` closure (the SAME cycle-safe
closure walk `derive_contract` already uses, reused rather than reimplemented, so the two traversals
cannot silently drift apart). **AC-7.4 publishes:** `methods_attempted`, `methods_with_no_recorded_gap`,
and `methods_with_dropped_receiver_call` (three commensurable method counts) for the 10
`SUPPORTED_TOOLS` methods, **plus** the two per-method call-node counts above (now closure-wide) as
secondary diagnostics for the same 10 methods. Concretely: all four `SUPPORTED_TOOLS`-closure records
inspected this round have `unresolved_calls: []` (`aspirate:45211`, `pick_up_tips:44929`,
`drop_tips:45019`, `_check_containers:45147`). **`methods_with_no_recorded_gap` landed at 7/10 (T6,
`51f53866`)** — round-6 remediation, R11: prior text left this as an unmeasured forecast ("will likely
land at or near 10/10") after T6 had already shipped and measured it — high enough to be
uninterpretable in exactly the way this asymmetry note names, and the reason RISK-1's entire round-1
answer rests on this counter being specified correctly, not on its value alone.

**`validation_looking_dropped_receiver_calls_by_method` is mostly, but no longer entirely, zero —
this is a measurement, not a defect (round-4 remediation, M11 bullet 3, un-changed by the closure-wide
fix above but re-measured against it).** Own-body-only, all ten `SUPPORTED_TOOLS` methods showed `0`
here — re-running the D3 predicate over the four tool bodies directly finds attribute names
(`get_tip`/`add_tip`/`remove_tip`/`add_liquid`/`remove_liquid`/`zero`/`warning`/`append`/
`request_tip_presence`/`can_pick_up_tip`/…), none of which matches HM-3's six validation-looking
prefixes, so `0` was a correct fact about PLR's naming at this pin, not a defect (AC-7.4 deliberately
sets no threshold on this figure). **Once made closure-wide** (M11 second half, above), three of ten
methods (`move_lid`/`move_plate`/`move_resource`) pick up exactly one validation-looking call each
from within their delegate closures — still a small, measured figure, not a defect either; recorded
here so a future reader sees the actual post-fix numbers rather than the pre-fix "all zero" claim.

**Classification: DERIVED** — every number is counted from the closure run (or, for the new T6
counters, from a second independent AST pass).

**Forward hazard, not a round-1 defect.** §0 fixes every v1 verdict at `UNKNOWN`, so no `SAFE` is ever
emitted in round 1 and this hazard cannot fire yet. But once derivation begins feeding real verdicts
(post-corpus), emitting `SAFE` for a method whose closure "completed" with zero *recorded* gaps —
while the receiver-shape hole above means the closure may have silently skipped real preconditions —
would be unsound. **A fence is required before the first `SAFE` is ever emitted**; this document does
not specify that fence (deferred), it only names the hazard so it is not rediscovered as a surprise
in a later round.

### 7.5 Verification

```bash
uv run pytest plr-sema/tests/test_derive.py -q
uv run python -m plr_sema.derive \
    --survey-json training/verify/data/plr_preconditions.json \
    --gap-ledger /tmp/ledger.json && jq . /tmp/ledger.json
```

- `test_aspirate_closure_reaches_check_containers` — the load-bearing regression. Assert the derived
  contract for `LiquidHandler.aspirate` contains ≥1 guard whose `site.qualname` is
  `LiquidHandler._check_containers` and whose `depth > 0`. **This test fails against a
  own-body-only derivation**, which is its entire purpose.
- `test_closure_terminates_on_cycle` — synthetic index with `A→B→A`; assert termination and correct
  `seen` set. Run under `pytest-timeout` (already a dev dependency).
- `test_unresolved_calls_become_gaps` — synthetic record with one `unresolved_calls` entry; assert
  exactly one `("unresolved_delegate", ...)` gap.
- `test_guard_sites_point_at_defining_file` — **respecified, D5.** The antecedent "`depth > 0` and
  the delegate is cross-file" is structurally unsatisfiable at C1's `resolve()` (§7.2): both of
  `resolve`'s lookups run against `rec.module`, and one module is one file, so no guard at `depth > 0`
  is ever cross-file under round-1 `resolve()` — a test gated on that antecedent would pass
  vacuously while AC-7.1 still counts it as a pass. **Respecified as a universal over the closure,
  not deleted:** for every guard with `depth > 0`, assert `site.qualname != entry_qualname` and
  `site.lineno` equals the delegate's recorded line — i.e. the guard's site is *the defining site*,
  the property §7.2 actually states. The cross-file form of this property becomes satisfiable only
  after deferred item (e) (cross-class resolution) lands; until then this test exercises the
  same-file, same-module case exclusively, and that is what it is specified to do.
- `test_ledger_totals_are_internally_consistent` — `methods_with_no_recorded_gap + methods_with_gaps
  == methods_attempted`; `sum(by_reason.values()) == total gap count`; **round-4 remediation, M11,
  additionally asserts `methods_with_dropped_receiver_call <= methods_attempted`** for both the
  whole-surface `totals` block and the `supported_tools` block — a real check as of this round, since
  both figures are now computed over the same population (previously the whole-surface figure could,
  and did, exceed its own denominator).
- `test_ledger_is_stamped` — `ledger["stamp"]["plr"]["hash"]` is 40-hex.
- `test_dropped_receiver_calls_are_counted` — **new, T6, corrected predicate (D3).** The independent
  stdlib-`ast` pass over PLR source under `external/` finds ≥1 dropped-receiver call node — `func` is
  `ast.Attribute` AND NOT (`func.value` is `ast.Name` with `id == "self"`) — in a synthetic fixture
  containing a `self.head[channel].get_tip()`-shaped call (a `Subscript` receiver) **and** in a
  fixture containing a `resource.get_item()`-shaped call (a bare, non-`self` `Name` receiver); and
  finds 0 in a fixture containing only `self.foo()`/`bare_call()` shapes. Also asserts the
  validation-looking subset count never exceeds the total count for the same fixture. Pins both
  counters §7.4's asymmetry note depends on.
- `test_ledger_regenerates_deterministically` — **new, round-4 remediation, m2, CONCEDE.** Two
  `build_gap_ledger` calls against the same fixed `stamp` and unchanged survey data serialize
  (`json.dumps(..., sort_keys=True)`) to byte-identical output. Mechanizes AC-7.3, which previously
  had no test behind it at all (grepped `plr-sema/tests/` for byte-identity/determinism checks: zero
  hits, pre-round-4).

### 7.6 Failure mode

**Assumption:** `delegates_to` is a sufficiently complete delegation edge set that closure over it
recovers materially more preconditions than a method's own body.

**If wrong** (i.e. most real preconditions hide behind the unresolved cross-class calls rather
than behind resolved same-class delegates): derivation produces near-universal `UNKNOWN`, and
`plr-sema` v1 is sound but empty. **This is the single biggest content risk in the document** (RISK-1).
**Detection is cheap and should be the very first thing built:** run the closure over all 1,314
finding-bearing functions and read the gap ledger's `methods_with_no_recorded_gap` count, **read
alongside T6's second and third counters (§7.4) — the AST pass computing, per method, the total
dropped-receiver call-node count and its validation-looking subset (D3), and the method-level
`methods_with_dropped_receiver_call` count (D4)** — since a high `methods_with_no_recorded_gap`
figure alone is uninterpretable (§7.4's asymmetry note) and needs those counts to mean anything. That
is a one-session measurement against data already on disk, and it either validates or invalidates the
whole approach before any user-facing surface is written. **Task T6 is scheduled first among the
derivation tasks for exactly this reason.**

Note the survey's own scope note is honest about the limit: it resolves same-class and module-level
calls only, and `self.head[channel].get_tip()` is named as the canonical example — though per §7.4's
correction, this specific shape is not *recorded by `unresolved_calls`* (its `Subscript` receiver
fails the survey's `name is not None` check before the unresolved-call recording block is ever
reached), making it the canonical shape **not recorded by the survey's current `unresolved_calls`
rule (recoverable — see round-5 T0, F1)**, one level worse than "unresolved" by that specific field —
**correction, round-5 remediation (F1, PARTIAL):** the prior wording called this the canonical
"**unrecordable**" shape, which was a claim about the *problem*, not about `unresolved_calls`'s rule,
and is false: the shape is 9 lines away from being recorded (`dropped_calls`, §7.1), which is exactly
what round-5 T0 did. "Unrecordable" is retired from this document; every remaining use names the
specific field/rule that doesn't record it — and, per D3, only one instance of the wider
dropped-receiver population (`func` is `ast.Attribute` AND NOT (`func.value` is `ast.Name` with
`id == "self"`)), which also includes plain `resource.get_item()`-style calls. Tip state lives on
`head[channel]`, so it is plausible that a substantial share of *tip-related* preconditions —
which is to say, the ones that matter most for `SUPPORTED_TOOLS`'s 10 LiquidHandler tools — sit
behind exactly this frontier. Do not assume otherwise; measure.

### 7.7 Acceptance criteria

- **AC-7.1** All `test_derive.py` tests pass (eight, as of round-4 remediation's added
  `test_ledger_regenerates_deterministically`, m2 — was seven).
- **AC-7.2 (totality, whole-surface as of 260901 T11 — was `SUPPORTED_TOOLS`-only, T6-only, through
  spec_version 6)** For every record the survey indexed — **the whole 4,770-record survey, not just
  the 10 `SUPPORTED_TOOLS` names** — `derive_contract` returns a `DerivedContract`: never raises,
  never returns `None`. Every operation therefore receives at least one `Finding`, for ANY method the
  whole-survey derivation covers, not only the former 10-method scope. **Totality itself is
  unchanged** (still `derive_contract`'s own never-raises property, §7.2); what T11 changes is the
  POPULATION this property is asserted over — `build_derived_contracts_payload`
  (`plr_sema.derive.__main__`) now iterates `build_unique_index(records)` (every record individually,
  including both twins of a getter/setter collision) rather than
  `resolve_supported_tool`-mapped `SUPPORTED_TOOLS` names.
  `resolve_supported_tool`/`module_of(LiquidHandler_record)` (D22, round-4 m3's fail-loud module
  disambiguation) are **UNCHANGED and still used** — but only for `build_gap_ledger`'s
  `supported_tools`-scoped reporting subset (§7.4), no longer for selecting which methods get a
  contract. **The full-pipeline coupling check (`len(findings) >= len(operations)` over a real graph)
  is AC-6.3, gated in T8, not here** — round 1 had no working `extract/` to run a full pipeline
  against (see §6.2/C5), so AC-7.2 originally asserted only the per-method never-raises property
  against the `SUPPORTED_TOOLS` list directly; T11's `test_whole_surface_contract_count`
  (`tests/test_derive.py`) now asserts it against the full survey population instead, and
  `test_non_liquid_handler_family_resolves_end_to_end` (`tests/test_check_graph.py`) exercises AC-6.3's
  full-pipeline form for a non-`LiquidHandler` family (`PlateReader`) for the first time.
- **AC-7.3** `gap_ledger.json` regenerates deterministically: two consecutive runs against an
  unchanged tree produce byte-identical output modulo `stamped_at`. **Mechanized this round
  (round-4 remediation, m2, CONCEDE) — `test_ledger_regenerates_deterministically`** (§7.5): before
  this round, nothing in `tests/test_derive.py` asserted this claim at all; the AC existed with no
  test behind it.
- **AC-7.4** The ledger reports a **non-zero** `methods_attempted`; a **published**
  `methods_with_no_recorded_gap` figure for the 10 `SUPPORTED_TOOLS` methods; a **published**
  `methods_with_dropped_receiver_call` figure for the same 10 methods (D4 — commensurable with the
  prior figure, both being method counts, and computed over the SAME population as
  `methods_attempted` as of this round — M11, §7.4); **and**, as secondary diagnostics for the same 10
  methods, the T6 counter's per-method total dropped-receiver call-node counts and their
  validation-looking subset (D3), now computed closure-wide rather than own-body-only (M11, §7.4).
  `methods_with_dropped_receiver_call <= methods_attempted` is asserted directly
  (round-4 remediation, M11, `test_ledger_totals_are_internally_consistent`, §7.5) — a population
  mismatch previously let the subset figure (1976) exceed its own denominator (1314); corrected value
  this round: **671**, derived in code, not copied from any prior estimate. No threshold is set on
  any of these figures in round 1 — they are the measurement that informs the deferred-corpus work,
  and setting a target before measuring would invite gaming.

  **AC-7.4's `totals`/`supported_tools` structure is UNCHANGED by 260901 T11** — `totals` remains
  computed over the same 1,314-record finding-bearing population (§7.6's whole-surface figures);
  `supported_tools` remains the 10-method subset, now purely informational rather than derivation's
  scope boundary (see AC-7.2 above). One field is added, not restructured: `contract_table`
  (`{total_entries, distinct_bare_qualnames, disambiguated_keys}`) reports the SEPARATE collision
  population the derived-contracts payload's OWN key (bare `qualname`, §7.3) sees — 26 colliding
  names / 52 records over the whole 4,770-record survey, a strictly larger count than
  `index_key_collisions`' 12 (§7.2's F6), because it also catches same-named module-level functions
  in different modules, which `(module, qualname)` cannot see as colliding. No threshold is set on it
  either.

---

## 8. Differential-test harness

### 8.1 Interface / data contract

Compare **45 hand-written `MethodContract` instances**, loaded by **AST-reading** the file named by a
required `--contracts-path PATH` (D19, round-6 remediation — same mechanism as `--survey-json` /
`--taxonomy-json`; **never imported** — `src/plr_sema/` may not import `praxis`, §1.3/AC-1.2), against
`DerivedContract`s for the same qualnames. In practice this points at
`praxis/backend/core/simulation/method_contracts.py`, but the harness itself takes only the flag —
`ast.parse` + a walk for `Call(func=Name("MethodContract"))` recovers all 45 instances and their
keyword values with no import and no boundary violation, exactly as `derive/` already reads the 3.4 MB
`plr_preconditions.json` from `training/verify/data/` via `--survey-json` today (§8.3's gate command
and T10's row both carry `--contracts-path`). Field shape confirmed this session (`method_contracts.py:47-60`
in the coxswain fork, verbatim from praxis): `method_name`, `receiver_type`, `requires_tips: bool`,
`requires_tips_count: int | None`, and further precondition/effect fields.

**On importing the coxswain fork instead (round-6 remediation, R1 sub-claim — rejected).** Importing
`coxswain.fft.preconditions.method_contracts` would also cross no boundary (`coxswain` is a root
workspace member per `pyproject.toml:44`, and `method_contracts.py` is one of the two
whole-file-verbatim ported modules, byte-identical to the `praxis` original per §5.1's drift test,
currently green). That path is *safe*, not a trap — it is simply not the one specified, because
`plr-sema/pyproject.toml` declares `dependencies = []` and §1.2's arrow says the package does not reach
sideways into repo packages. The AST-read-by-path form above is preferred for that reason, not because
the fork is unsafe.

```python
@dataclass(frozen=True, slots=True)
class Disagreement:
    qualname: str
    kind: Literal["hand_only", "derived_only", "conflict", "agree"]
    hand: str        # rendered hand-written claim
    derived: str     # rendered derived evidence
    plr_sites: tuple[PlrSite, ...]
```

**Comparison is at the level of *claims*, not of representations.** The hand-written form is a
boolean field (`requires_tips=True`); the derived form is a set of inlined guards with raw condition
strings. Bridging those in general requires the predicate language (deferred item (c)). **In v1 the
bridge is a deliberately narrow, mechanical one:** a derived contract *supports* `requires_tips=True`
iff its guard set contains a guard whose `raises` is a **tip-related PLR exception class — defined
explicitly as `category == "tip_state"`** in the hand-typed category-keyword table (§9.2, HM-19; only
5 of 132 classes carry this category) — or whose `condition` mentions a tip-related identifier.
Everything else is reported as `hand_only` (we cannot corroborate) or `derived_only` (we found
evidence the human did not encode).

**"A tip-related identifier" is made mechanical, not lexical (D13).** The round-2 text left this
phrase undefined, and AC-8.2's headline deliverable depends on it. Defining it as a lexical set (a
hand-typed word list) would need both a definition and a new HM registry row. Instead, define it
**derived**, from data the spec already has: a guard's `condition` "mentions a tip-related
identifier" iff `mentions_params ∩ tip_bearing_params(qualname) ≠ ∅`, where `tip_bearing_params(qualname)`
is **the survey record's own `params` whose names contain, case-insensitively, an HM-19
`_NAME_KEYWORD_CATEGORIES` keyword mapped to `tip_state` (today: `Tip`)** (round-6 remediation, R2 —
see below for why the previous definition was unachievable). This adds **no registry row** — HM-19
is already registered and already feeds this bridge's `raises`-clause (above); `tip_bearing_params`
reuses it rather than adding a second surface. At the current pin this matches `tip_spots` and
`tip_rack`, firing on 4 of `LiquidHandler`'s 81 findings (`pick_up_tips`, `drop_tips`,
`probe_tip_presence_via_pickup` on `tip_spots`; `pick_up_tips96` on `tip_rack`): narrow, but live, not
`∅` for all 45.

**Why the previous definition (`MethodContract`'s own `requires_tips_count`-governed parameter) does
not work (round-6 remediation, R2 — CONCEDE, and the round-6 challenge under-diagnosed it).**
`MethodContract`'s 21 fields contain no parameter-name-bearing tip field: `requires_tips_count` is
`int | None`, set on exactly 4 of 45 contracts, always the literal `96` — it governs no *parameter
name* at all, so `tip_bearing_params` under the old definition is `∅` for all 45 contracts, not merely
narrow. The obvious repair, `requires_on_deck`, also fails: `pick_up_tips` carries
`requires_on_deck=('tips',)` while the PLR method's actual parameters are `['self', 'tip_spots',
'use_channels', 'offsets', 'backend_kwargs']` — `'tips'` is not among them, so the intersection stays
empty. **There is no purely-derived construction available from `MethodContract`'s own fields**; D13's
premise (define it derived, from data the spec already has) is unachievable from that specific source,
not merely mis-cited — which is why the definition above routes through the *survey record*'s
`params` and HM-19 instead. Severity: MAJOR, not BLOCKER — AC-8.1 (every contract classified) stays
satisfiable with the clause returning `∅` on a miss, and AC-8.2 carries an explicit written-note
waiver for that case. (A lexical identifier list remains an option if the derived form proves too
narrow in practice, but it would then need both a written definition and a registry row; the derived
form above is preferred here.)

**Resolving each hand contract's `(module, qualname)` (round-6 remediation, R5).** T10's population
(all 45 hand contracts) is wider than `SUPPORTED_TOOLS`, which is the only population D22's lookup was
previously exercised against. Resolve each contract's `(module, qualname)` by PascalCasing
`receiver_type` (`heater_shaker` → `HeaterShaker`) and applying D22's existing "UNIQUE module among
indexed survey records whose `class_name == X`" lookup, unchanged. Measured against
`plr_preconditions.json` at the current pin: **29 of 45 resolve uniquely** by this two-line mechanical
transform (`LiquidHandler` 55 recs/1 module, `Centrifuge` 15/1, `Thermocycler` 26/1, `PlateReader`
9/1, `TemperatureController` 7/1, `HeaterShaker` 2/1, `Shaker` 6/1, `Sealer` 6/1, `Peeler` 3/1) — no
hand-typed device→class table is required and no new registry row is needed.

**Two dispositions D22 does not specify, because T10's population is wider than `SUPPORTED_TOOLS`
(round-6 remediation, R5 — the genuine defect the round-6 challenge missed).** D22's rule as written
fails loudly — naming every distinct module found — the moment more than one module matches, and
fails loudly again if the resolved module lacks the named method. Applied verbatim to all 45
contracts, that aborts the harness on **16 of 45** at the current pin, not the 3 D22 was written
against:

1. **A class resolving to >1 module.** `Pump` resolves to two (`pylabrobot.pumps.pump`,
   `pylabrobot.liquid_handling.backends.hamilton.pump`) — 3 contracts (`run_for_duration`,
   `run_for_volume`, `halt`).
2. **A class with no such method in the index.** 13 contracts resolve to a class but not a method on
   it (`LiquidHandler.transfer_96`/`mix`/`blow_out`/`touch_tip`, six `HeaterShaker.*`,
   `Centrifuge.open_lid`/`close_lid`, `Thermocycler.run_profile`).

Both dispositions are classified **`hand_only`**, with the reason recorded — a first-class §8.2 kind,
not an error, and *not* the loud abort D22 specifies for its narrower, `SUPPORTED_TOOLS`-only origin
population. Tally at this pin: **29 resolve, 13 method-absent, 3 module-ambiguous = 45.** AC-8.1
(every contract classified) is satisfiable if and only if §8.1 states these two disposition rules,
which is what this paragraph does.

**Bridge behaviour when `raises` is not a plain class name (C4).** `raises` may be `None` (the
finding came from an `assert`, which has no exception class at all — `kind == "assert"`) or the
`"<dynamic:..."`-prefixed sentinel (`survey_plr_preconditions.py:203-210`; minted when the raised
exception is constructed from a variable rather than a literal class name —
the `LiquidHandler.aspirate` record's third finding in `plr_preconditions.json` is a live instance; detect via
`raises.startswith("<dynamic:")`, D18, never by equality against a glob string). Neither is matchable
against `plr_exception_taxonomy.json`'s class-name keys. The bridge's `raises`-based clause is
therefore **inapplicable** in both cases and falls through to the
condition-mentions-a-tip-related-identifier clause (now the derived form above), which does not
depend on `raises` at all; if that clause also fails to match, the guard contributes nothing toward
corroborating `requires_tips=True` (it does not count as *evidence against* it either — absence of
support is not evidence of absence here).

**The `raises`-based clause is live, not dead — and needs a polarity fix (D13).**
`LiquidHandler.pick_up_tips` carries `"raises": "HasTipError"` (the `LiquidHandler.pick_up_tips` record in `plr_preconditions.json`, from
`liquid_handler.py:535`), and `_NAME_KEYWORD_CATEGORIES`'s first pair is `("tip_state", "Tip")` with
first-match-on-class-name, so `HasTipError` categorizes as `tip_state` and the `raises`-based clause
does fire for this method — it is not a dead code path. (`LiquidHandler.aspirate` merely *looks* dead
for a specific, instructive reason: `NoTipError` appears in `liquid_handler.py` only at `:486`/`:632`,
in docstrings — the real raise lives in the tip tracker behind a cross-class call, i.e. exactly the
D3/§7.6 dropped-receiver frontier (recorded, as of round-5 T0, in `dropped_calls` — §7.1 — though the
D3 pass and this bridge discussion predate and are independent of that field), not a bridge defect.)
**But `HasTipError` corroborating
`requires_tips=True` is polarity-inverted**: `pick_up_tips` requires an *empty* channel — `HasTipError`
fires when tips are already present, i.e. it is evidence *against* `requires_tips=True` reading
naively, not for it. `InlinedGuard.kind` (§7.2, C4) exists precisely so this polarity is recoverable:
`"raise_guard"` fires when `condition` is true, `"assert"` fires when `condition` is false. **The
bridge must consult `kind`, not just the exception-category match, to determine whether a guard
asserts tip-presence or tip-absence** before deciding which side of `requires_tips` it corroborates.
Without this, the harness's first run reports a confident false `agree` on the two most-scrutinized
methods in the whole differential surface.

> This bridge is the weakest link in §8 and is where round 2 should press hardest. It is a
> *heuristic* string-mention test sitting inside a spec that elsewhere forbids classification by
> string matching (§4's "structural, never by parsing message text"). The justification for the
> inconsistency: §4's rule governs *production* classification, where a wrong answer becomes a wrong
> verdict; §8's bridge governs a *research instrument*, where a wrong answer becomes a
> false disagreement that a human reads. Those have genuinely different error costs. **But the
> justification only holds while §8 is not a gate** — see the AC-8 note. If a future round makes §8
> gating, this bridge must be replaced first.

### 8.2 Disagreements are findings in both directions

- `hand_only` — the human asserted something derivation cannot corroborate. Either the human is
  right and derivation is incomplete (a gap-ledger entry), or the human was wrong (a bug that has
  been silently shipping).
- `derived_only` — PLR source contains a guard the hand-written contract omits. Almost always a real
  missing precondition. **Highest-value output of the whole harness.**
- `conflict` — direct contradiction. Highest priority; each gets triaged individually.
- `agree` — corroboration; the count is the headline number.

### 8.3 Verification

```bash
uv run python -m plr_sema.differential \
    --taxonomy-json training/verify/data/plr_exception_taxonomy.json \
    --contracts-path praxis/backend/core/simulation/method_contracts.py \
    --report /tmp/diff.json
uv run pytest plr-sema/tests/test_differential.py -q
```

- `test_all_45_hand_contracts_are_classified` — every hand-written contract lands in exactly one of
  the four kinds. Guards against silent drops. **The count 45 is asserted dynamically** (`len` of the
  loaded instances), not hard-coded, so adding a 46th hand contract does not break the test — it
  moves the ratchet (§9).
- `test_report_is_stamped` — carries `SurveyStamp`.
- `test_known_disagreement_is_stable` — pick one triaged disagreement, pin it as a regression fixture
  so the harness's behaviour is itself under test.

**Classification of the harness: DERIVED** (it computes both sides). **Classification of the 45
hand-written contracts: HAND-MAINTAINED**, registry row HM-13, **target 0** — this is the cautionary
case the whole §9 budget exists for.

### 8.4 Failure mode

**Assumption:** the hand-written contracts are a meaningful baseline.

**If wrong** — they encode a *different* abstraction (coarse boolean "needs tips" vs. PLR's
fine-grained per-channel guards) rather than a coarser version of the same one — then most
comparisons are category errors and the harness produces noise. **Detection:** an implausibly high
`conflict` rate (>50%) on the first run means the bridge is mismatched, not that the contracts are
wrong. **Response:** narrow the bridge to the fields where the abstraction genuinely aligns
(`requires_tips`, `requires_tips_count`) and report the rest as `hand_only` by construction, rather
than forcing a comparison.

### 8.5 Acceptance criteria

- **AC-8.1** `test_differential.py` passes; every loaded hand contract is classified.
- **AC-8.2** The report distinguishes all four kinds and includes ≥1 `derived_only` entry with a
  concrete `PlrSite` — i.e. the harness demonstrably found at least one precondition the humans
  missed. If it finds zero, that is itself a reportable result and AC-8.2 is waived with a written
  note (it would suggest the bridge is too narrow to see anything).
- **AC-8.3 (explicitly negative)** **No threshold is set on the agreement rate, and the differential
  harness does not gate CI in round 1.** Per the §7.2 flag, making it a gate reintroduces pressure to
  hand-patch contracts and defeats decision 2.

---

## 9. Hand-maintained surface: inventory, budget, ratchet

The 45 hand-written contracts are the cautionary case: they grew with no ceiling and now cover an
unknown fraction of a 502-file library, against 55 `LiquidHandler` methods alone. **Every
hand-maintained fact in `plr-sema` gets a registry row, a size metric, and a test that fails when the
measured size exceeds the declared size.**

### 9.1 The registry

`plr-sema/src/plr_sema/_hand_maintained.py` — a data module, imported by the ratchet test:

```python
@dataclass(frozen=True, slots=True)
class HandMaintainedSurface:
    id: str
    what: str
    metric: str                 # what is counted
    declared: int               # the ceiling
    status: Literal["FROZEN", "CAPPED", "DERIVABLE_NOT_YET", "TARGET_ZERO", "RETIRED"]
    why_not_derived: str        # REQUIRED, non-empty
    breaks_when: str            # REQUIRED, non-empty
    trigger: str = ""           # REQUIRED and non-empty iff status == DERIVABLE_NOT_YET
    measure: str = ""           # EITHER an import path of a zero-arg callable returning the live
                                # count, OR (C7) an import path of an AST-reading callable, defined
                                # in the ratchet test module, taking (source_path, target_symbol) and
                                # returning a live count computed by parsing the source — needed for
                                # facts embedded in function bodies (e.g. inline branch/prefix/rule
                                # counts) that no zero-arg import can observe.
    peak: int = 0               # D16(a): the recorded high-water mark, for rows whose declared
                                # ceiling must monotonically DECREASE after a peak (HM-16). 0 for
                                # every other row. `test_shims_never_grow_after_peak` (§9.3) reads
                                # this field directly rather than inferring it from `declared`.
```

**Why `measure` must permit both forms (C7).** At least five registry rows (HM-2, HM-3, HM-4, HM-6,
HM-7) measure facts embedded in *function bodies* — inline branches, inline string-prefix
literals in a `return` expression, local dispatch tables — which are uncountable by any zero-arg
import callable. **Correction (D6):** HM-15 is not the only `scripts/`-sourced row that is
import-measurable as a module-level constant — `_NAME_KEYWORD_CATEGORIES` (HM-19,
`scripts/survey_plr_exceptions.py:66-80`, 13 pairs) is a module-level `list[tuple[str,str]]`,
exactly like HM-15's `_ROOT_EXCEPTION_NAMES`. So **HM-15 and HM-19** are import-measurable; HM-19's
`measure` may equivalently use the plain import-path form rather than the AST-reading form (its
current specification, via the same `scripts/`-sys.path/AST-reading mechanism as HM-3/HM-4, is not
wrong, just more machinery than the fact needs — simplification is optional, not required). The
ratchet test module therefore defines a small set of bespoke AST-reading counters (source path +
target function/class → live count) alongside the plain import-path form. `scripts/` has no
`__init__.py` and is excluded via `norecursedirs` (`pyproject.toml:140-153`), so the ratchet test module
also carries a `sys.path` shim (append the repo-root `scripts/` directory) for the rows (HM-15,
HM-19) that use a real import.

**Headroom rule for MEASURE + CAPPED rows (D16c).** When `--update-baselines` (T9) fills in a
`declared` value for a row whose `status` is `CAPPED`, the human filling it in writes **live + 2**,
matching HM-3/HM-4's existing precedent (`CAPPED (8)` against a live count of 6) — not the bare live
count. A bare live-count ceiling gives **zero headroom**: the very next commit that adds one entry to
that surface trips the ratchet, which is the opposite of what a reviewable-growth mechanism should
do. This rule applies to `CAPPED` rows only — `FROZEN` rows use `declared == live` exactly (per
`test_frozen_surfaces_are_exact`, §9.3), and `DERIVABLE_NOT_YET`/`TARGET_ZERO` rows are aimed at
shrinking, so headroom is not applicable to them either.

**Table prose vs. field values (D16b, a clarification, not a violation).** Entries like "`CAPPED,
must decrease after peak`" (HM-16) or "`CAPPED (8)`" in the table above combine the `status` field's
actual `Literal` value with human-readable prose or a parenthetical ceiling number. The `status`
field itself is always exactly one of the five `Literal` members (`FROZEN`, `CAPPED`,
`DERIVABLE_NOT_YET`, `TARGET_ZERO`, `RETIRED`) — the parenthetical numbers and trailing clauses are
inventory-table annotations for the reader, not additional enum members, and no code inspects them as
structured data.

### 9.2 Inventory (baseline)

| id | surface | metric | baseline | status | trigger → DERIVED |
|---|---|---|---|---|---|
| HM-1 | `PLR_RESOURCE_TYPES` class-name set (`praxis/common/type_inspection.py:14-56`) | entries | **34** | DERIVABLE_NOT_YET | Point `plr_survey_common.collect_all_classes` + the `exception_name_closure` fixpoint at `Resource`/`Machine` instead of `Exception`. The machinery already exists and is proven on 132 exception classes. |
| HM-2 | `infer_category_from_name` substring rules (`plr_category.py:129+`, 186 LOC, self-documented "BRITTLE") | branches | **MEASURE** | DERIVABLE_NOT_YET | PLR classes carry a real `category` attribute; the function is documented as a fallback for when the class object is unavailable. Derive by AST-reading the attribute per class into a table. |
| HM-3 | validator-name prefixes in `_is_validation_looking` (`survey_plr_preconditions.py:149-151`) | prefixes | **6** | CAPPED (8) | None known — a heuristic over PLR's naming. |
| HM-4 | PLR test-file stem heuristic (`plr_survey_common.py:35-40`) | rules | **3** | CAPPED (4) | None known. |
| HM-5 | `FAILURE_CATEGORIES` (`failure_taxonomy.py:82-89`) | categories | **6** | FROZEN | None — these are our semantics, not PLR's. |
| HM-6 | `classify_exception` module-prefix dispatch (`:197,209`) | prefixes | **2** | CAPPED (3) | None. |
| HM-7 | `our_names` harness-exception map (`:241-242`) | entries | **3** | DERIVABLE_NOT_YET | Duplicates the `isinstance` dispatch in `classify_exception`, above; derive from the three classes' `__name__`. |
| HM-8 | ~~`_plr_exception_class_names` module allowlist~~ **RETIRED (round 4, M5)** | modules | **0** (was 2) | **RETIRED** | Trigger FIRED: T7 (`3a3a9f00`) replaced the 2-module `inspect.getmembers` walk with a validated load of `plr_exception_taxonomy.json`. 11 → 132 names, 121 newly visible, none lost. The surface no longer exists. |
| HM-9 | `SUPPORTED_TOOLS` (`dispatcher.py`) | tools | **10** | CAPPED (10) | **Redefined 260901 T11**: through spec_version 6 this row doubled as both `training.verify.dispatcher`'s dynamic-execution capability limit AND `plr_sema`'s entire analyzed surface, because both derivation and `unsupported_tool` were hand-gated on it. T11 decouples the two: `plr_sema.derive` now derives a contract for every method the survey indexes (4,770 at the current pin, §7.3/§7.6), and `unsupported_tool` means "key absent from that whole-survey contract table" (§6.2), not "outside this 10-tool set". This row is UNCHANGED and still real — it remains `training.verify.dispatcher`'s own dynamic-execution-harness scope boundary (what it can actually dispatch at runtime), a fact about OUR harness, not PLR — but it no longer gates what `plr_sema` derives or checks. None known — growth of the *harness's* boundary is still a deliberate scope decision made in `verify/`, orthogonal to `plr_sema`. |
| HM-10 | `EffectType` enum (`method_contracts.py:17-29`) | members | **9** | CAPPED (9) | None in v1 (effects are not simulated). |
| HM-11 | `PreconditionType` enum (`models.py:~500-521`) | members | **MEASURE** | CAPPED | Candidate for derivation from guard `raises` classes once (c) lands. |
| HM-12 | `MethodContract` field vocabulary | fields | **MEASURE** | TARGET_ZERO | Superseded entirely by `DerivedContract`. |
| HM-13 | **the 45 `MethodContract` instances** | contracts | **45** | **TARGET_ZERO** | §7's derivation replaces them; §8 measures the replacement. **The cautionary case.** |
| HM-14 | `REASON_VOCABULARY` (§3.3) | reasons | **7** (round-4 remediation, B4: was 8 — `argument_not_static` withdrawn) | CAPPED (12) | None — describes our own give-up points; deriving from our own AST would be circular. |
| HM-15 | `_ROOT_EXCEPTION_NAMES` (`plr_survey_common.py:32`) | names | **2** | FROZEN | None — Python's, not PLR's. Zero drift risk. |
| HM-16 | compatibility shim modules (§1.2) | modules | **0** | CAPPED, **must decrease after peak** | Each is deleted when its callers migrate. |
| HM-17 | picked `git_state.py` (§2) | LOC **excluding the §2.1 provenance header** (round-6 remediation, R19 — the file is 251 lines on disk; the 10-line delta is the header §2.1 itself mandates, and `test_frozen_surfaces_are_exact` requires `measure() == declared` exactly, so `measure` must strip it the same way §5.2 tier 1 already does for its own sha256 check, reusing T5's `parse_cherry_pick_header` to derive the boundary rather than hardcoding it) | **241** | FROZEN | None — upstream source we now own. One-time cost; §5 tier 1 forbids edits. |
| HM-18 | cherry-pick header recorded hashes (§5.2) | hashes | **2** | FROZEN | None. |
| HM-19 | category-keyword pairs table, `_NAME_KEYWORD_CATEGORIES` (`scripts/survey_plr_exceptions.py:66-80`, first-match on class name; feeds §8.1's tip-related-category bridge) | pairs | **13** (D6 — confirmed by read this round; not MEASURE) | CAPPED (15) | None known — a heuristic over PLR's exception-class *names*, in the same spirit as HM-3. Import-measurable as a module-level `list[tuple[str,str]]`, exactly like HM-15 (D6); the AST-reading `measure` mechanism from C7 also works but is not required. |
| HM-20 | module-substring category fallback table, `_MODULE_SUBSTRING_CATEGORIES` (`scripts/survey_plr_exceptions.py:83-90`, consulted only on an HM-19 miss) | pairs | **6** | CAPPED (8) | None known — a heuristic over PLR's module-path structure, same spirit as HM-3/HM-19 (D7). **Cannot perturb §8.1's bridge**: its six categories (`pump_state`, `centrifuge_state`, `plate_reader_state`, `storage_state`, `channel_state`, `resource_state`) do not include `tip_state`. The `category: str = "uncategorized"` default (`:101`) is the absence-case for a miss on *both* tables and is not itself enumerated as a row — it is noted here in `breaks_when`: a class whose category is genuinely ambiguous falls through to `"uncategorized"` rather than a miscategorization. |
| HM-21 | field set mirrored by `check/graph.py` from `OperationNode`/`ResourceNode` (§6.2, D1) | fields mirrored | **MEASURE** | CAPPED | Which fields the mirror needs is a judgement about which §3.3 reasons and §7.3 lookups exist today, not a fact recoverable from PLR source — so the *decision of which fields to include* is hand-maintained even though each individual field's continued presence in the upstream pydantic model is drift-tested (Fork C, §5.3, D8). Breaks when a §3.3 reason is added needing a field not yet mirrored (a reviewable ratchet-visible diff), or when `OperationNode`/`ResourceNode` rename/remove a mirrored field (caught by Fork C's drift test, not by this ratchet). |
| HM-22 | `_TAXONOMY_PATH` + the 2-key artifact-validation schema (`failure_taxonomy.py:140-153`) | validated artifact keys | **2** | CAPPED (4) | None — our own artifact contract. |
| HM-23 | `EXPECTED_SUBMODULE_PIN`, Fork D's expected-pin literal (`plr-sema/tests/test_fork_drift.py`, added 260901 T13 — live row 22) | declared pin literals | **1** | FROZEN | None — a fixed expectation is the whole point of a drift test; deriving it from the submodule would make the check vacuous (same reasoning as HM-17/HM-18). |
| HM-24 | tip-typestate channel-receiver bridge shape (`plr_sema.derive.receiver_state._BRIDGE_SHAPE_RE`, `self.<attr>[<name>].<method>`, added 260902 tip typestate increment §10.2.5/§10.10 Q7 — split from a single 6-pattern row per the user's decision, option B), plus the volume bridge shape and B1's for-loop-over-comprehension-output binding (increment 5 §14.4/§14.0.1, added 260903, user-approved 260904 — see §14.11) | patterns | **3** | CAPPED (3) | None known — a syntactic pattern over how PLR is written, same argument as HM-3. Fails CLOSED (a silent family collapse, not a wrong verdict) — the reason it is its own row rather than folded into HM-25. |
| HM-25 | tip-typestate front-end syntactic patterns, the other five (typestate-anchor property shape P2, channel-default idiom P3a, and the three atom productions BoolView/NullCheck-is-None/NullCheck-is-not-None, §10.2.2/§10.2.3/§10.3.1, added 260902 tip typestate increment — split from HM-24 per the user's Q7 decision), plus a sixth pattern (delegate-call literal channel binding P9, §13.5.2, added 260903 sprint-122 backlog #4946, user-approved 260903), plus P7's accessor-anchor shape and P8's zip-comprehension operand-pairing idiom (increment 5 §14.4, added 260903, user-approved 260904 — see §14.11), plus the local-binding idiom (alpha/beta, §15.3) and the 260907 amendment's EnvRef/Zip/membership-comparator productions named inside the same entry (increment 6 §15.2/§15.3/§15.8, added 260904, user-approved 260907 — see §15.12 T31) | patterns | **9** | CAPPED (9) | None known — same argument as HM-3/HM-24. Fails LOUDLY (AC-10.1–AC-10.3/AC-15.1–AC-15.3's exact-count assertions), unlike HM-24. |

**MEASURE** = a one-off helper (`uv run python -m plr_sema._hand_maintained --update-baselines`, run
during T9) prints the live count for every row whose `declared` is not yet filled; a human copies
those numbers into `_hand_maintained.py` in one reviewable commit. **The ratchet test itself never
writes** — it only asserts `measure() <= declared` (§9.3). A self-writing test would be
non-idempotent, would dirty a read-only CI tree, and has no defined ordering guarantee under
`pytest-randomly>=3.12.0` (`pyproject.toml:88`), so writing is deliberately kept out of the test and
pushed into a one-off, human-reviewed step. No number is invented in this document that was not
measured; every **MEASURE** row above is filled with a real number by T9 before it ships (all rows,
once C7 broadens what `measure` may compute).

### 9.3 The ratchet mechanism

```bash
uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q
```

- `test_no_surface_exceeds_its_declared_size` — for every row with a `measure` callable, assert
  `measure() <= declared`. Growth requires editing `_hand_maintained.py`, which is a visible,
  reviewable one-line diff that a reviewer can question. **This is the entire mechanism: growth is
  not forbidden, it is made loud.**
- `test_frozen_surfaces_are_exact` — `status == FROZEN` requires `measure() == declared`, not `<=`.
- `test_every_row_justifies_itself` — `why_not_derived` and `breaks_when` are non-empty;
  `DERIVABLE_NOT_YET` rows have a non-empty `trigger`. A row cannot be added without an argument.
- `test_shims_never_grow_after_peak` — HM-16's declared value must be `<=` the recorded peak, stored
  in the row.
- `test_hand_written_contracts_content_is_pinned` — **HM-13-specific content ratchet (C18).** Records
  a sha256 over the concatenated, normalized field-values of all 45 `MethodContract` instances (not
  just their count) and asserts the live sha256 matches. This exists because the count-only ratchet
  (`measure() <= declared`) cannot see a **body edit** to an existing contract — RISK-9's actual
  failure mode is a hand-patched field value (e.g. `requires_tips=True` silently flipped to `False`
  to make a §8 disagreement go away), which never changes the count of 45 and would otherwise pass
  the ratchet test invisibly. A body edit changes the hash; growth (a 46th contract) changes both the
  hash and the count, and is still the visible, reviewable diff §8.3 describes.
- `test_total_declared_within_budget` — see below.

### 9.4 Budget and measurable shrink target

**Total budget: 24 registry rows** (raised from 20, round 3 — see below). **Baseline after this
round's discovery: 21 rows** (19 from round 2 + HM-20 + HM-21). **Headroom: 3.**

**Discovery vs. growth — the normative distinction the cap was missing.** Two rounds in a row (C16 in
round 2, D7/D8 here) found genuine pre-existing hand-maintained surface that the registry had not yet
named. That is the ratchet process working, not failing — but a cap set at "baseline + 1" fails on
the very next honest discovery, and it fails at exactly the moment a fixer is under schedule pressure
to ship, which is when ratchets get quietly deleted rather than respected. The registry therefore
distinguishes:

- **Discovery** — registering pre-existing surface that was always there but unregistered. Permitted
  to re-baseline the cap **once**, at T9, in a single reviewed commit, with each newly added row
  carrying its own `why_not_derived`/`breaks_when` argument (`test_every_row_justifies_itself`, §9.3,
  already enforces the per-row argument; the re-baseline itself is a one-time, human-reviewed act, not
  a test).
- **Growth** — introducing *newly hand-typed* surface that did not exist before. **Never** raises the
  cap; it is always a visible diff against whatever cap is currently in force, exactly as
  `test_no_surface_exceeds_its_declared_size` already enforces per-row.

**`RETIRED` semantics and the cap (round-4 remediation, M5 — CONCEDE).** §9 previously specified how
rows are *added* but never how a row whose conversion trigger has FIRED leaves the registry. T7
eliminated HM-8's surface outright, leaving it in an undefined state: none of the four original
status values fit, `test_no_surface_exceeds_its_declared_size` passed vacuously (`0 <= 2`) so the
ratchet could not distinguish "converted" from "still there", and `test_every_row_justifies_itself`
requires a non-empty `trigger` iff `DERIVABLE_NOT_YET`, which a fired trigger no longer is.

A `RETIRED` row is **kept, not deleted** — the historical record of what was hand-maintained and how
it was discharged is the registry's whole point. Normative rules:

- `RETIRED` requires `declared == 0` and a `why_not_derived` that names the commit which discharged it.
- `test_frozen_surfaces_are_exact` extends to `RETIRED`: `measure() == 0` exactly, so a retired
  surface silently reappearing turns the ratchet red instead of passing vacuously.
- **`RETIRED` rows do not count toward `live_rows`.** This is the load-bearing consequence: retiring
  HM-8 drops `live_rows` 21 → 20 while the cap stays 24, so headroom silently grows 3 → 4 — exactly
  the drift §9.4's strict-monotonicity clause exists to prevent. **The cap therefore moves with the
  count: retiring a row lowers the cap by one.** Growth still never raises it.

**T7 introduced unregistered hand-maintained surface (round-4 remediation, M5).** `_TAXONOMY_PATH`
plus the hand-typed 2-key artifact-validation schema (`version.git_sha`, `classes`) at
`training/verify/failure_taxonomy.py:140-153` is, under §9.4's own discovery-vs-growth rule,
**growth** — newly hand-typed surface that did not exist before — and it has no row. It gets one at
T9 as **HM-22** (metric: validated artifact keys, baseline 2, CAPPED(4)). Net effect on the count:
HM-8 retires (−1), HM-22 registers (+1), so `live_rows` returns to 21 and the cap of 24 stands as
specified. The two changes must land in the *same* T9 commit; applying either alone leaves the
arithmetic inconsistent.

**Re-baseline mechanism.** At T9, the cap is re-baselined once to `live_rows + 3` (21 + 3 = 24 at this
round's count). After T9 ships, the cap is fixed and `test_total_declared_within_budget` (§9.3)
enforces it with strict monotonicity — no further re-baselining without a new adversarial round
finding new discovery, which is exactly the process that produced this one.

**Measurable shrink target for the corpus-gated phase — the number that matters:**

| conversion | facts eliminated |
|---|---|
| HM-13 → 0 (derived contracts replace hand-written) | **45** |
| HM-1 → DERIVED (resource-type closure) | **34** |
| ~~HM-8 → DERIVED (exception taxonomy load)~~ **DONE, T7 `3a3a9f00`** | **2 modules → 132 derived classes** (11 → 132 names visible; row now `RETIRED`, M5) |
| HM-7 → DERIVED | **3** |

**Target: ≥82 hand-typed facts eliminated, and the count of `TARGET_ZERO` + `DERIVABLE_NOT_YET` rows
reduced from 5 to ≤2.** (HM-8 is already `RETIRED`, not `DERIVABLE_NOT_YET`, so the current baseline
count of this pair of statuses — HM-1, HM-2, HM-7, HM-12, HM-13 — is 5, not 6.) **Corrected survivor
count (D17): 16, not 11.** Of the 21 live rows (post-HM-22), converting/removing HM-1, HM-7 (→
DERIVED) and HM-13 (→ 0) leaves 18 (HM-8 is not in this list — it already converted, and as a
`RETIRED` row it does not count toward `live_rows` at all, §9.4 above); of those 18, HM-2 and HM-12
are the "≤2 `DERIVABLE_NOT_YET`/`TARGET_ZERO`" rows still pending resolution, leaving **16** rows as
the stable FROZEN/heuristic-CAPPED core:
HM-3/4/5/6/9/10/11/14/15/16/17/18/19/20/21/22
— all either FROZEN or genuinely heuristic, and each with a written argument for why.

**Anti-gaming clause, restated honestly (C13).** The round-1 mechanism is deliberately narrow: each
row's `measure() <= declared` is checked independently (§9.3), and the 24-row total (round 3) is a
cap on the count of *rows* (`test_total_declared_within_budget`). **This does not, by itself, prevent
splitting a large set into several smaller rows** — a 34-entry set split into three ~11-entry rows
would pass every per-row check and would not trip the row-count cap either (3 rows is well under 24).
Round 1
accepts this as a known, named gap rather than inventing an unenforced cross-row sum: splitting is
still a reviewable act, since `test_every_row_justifies_itself` requires a non-empty
`why_not_derived`/`breaks_when` argument for every new row, which raises the cost of gaming without
formally closing it. A real anti-gaming metric (e.g. summing `declared` across rows that share a
`metric` kind) is left for a later round if the row-count cap proves insufficient in practice.

---

## Deferred

Blocked on a literature corpus (abstract interpretation + typestate) currently being compiled.
**Nothing about these is specified anywhere in this document.** (For three related, but distinct,
open questions that are pending a **user** decision rather than the literature corpus — the
`UNREACHABLE` `Verdict` member, whether volume tracking is in v1, and the `join` lattice ordering —
see [§Open decisions](#open-decisions) near the top of this document, added round 6, R14.)

**Round-4 remediation (B3, PARTIAL, and materially overstated by the round-4 challenge) — of the six
rows in this table's dependency structure, exactly ONE ((e)) is genuinely falsified; (d) is not
falsified at all; (b) and (f) have their stated reasons CONFIRMED by the very evidence cited against
them and are merely under-scoped, not wrong.** Rows (b)/(e)/(f) below are edited; (d) gets one
optional clause; (a)/(c) are untouched (not challenged).

| # | deferred | one-line reason |
|---|---|---|
| (a) | The abstract domain — lattice, ⊑, join at branch merges, widening | Choosing a domain before reading the literature would hard-code a precision/soundness tradeoff we cannot yet evaluate; §3.2 names the exact attachment point. |
| (b1) | The formal meaning of `UNKNOWN` — sound over-approximation vs. bail-out, i.e. how `UNKNOWN` should PROPAGATE (⊤-propagation semantics) | Genuinely presupposes (a): propagation needs an abstract state to propagate, which does not exist pre-(a). **(round-4 remediation, B3 row (b), split — the stated reason survives:** `260901_plr-sema-research-b-f.md:35` opens "it is real, but the spec has named the wrong axis" about the UNDIVIDED row, not about this half.) |
| (b2) | Whether an `UNKNOWN`-worthy obligation is generated AT ALL, for a construct the front end cannot yet classify | **Not blocked on (a) — in scope for T6's recording rule now (round-4 remediation, B3 row (b), split, CONCEDE half).** A front-end/TCB recording-completeness property, not a propagation-semantics one; the literature prescribes a fail-closed front end (`260901_plr-sema-research-b-f.md:53-59,100-104`). Silently dropping the obligation (rather than recording SOME `UNKNOWN` reason for it) was the actual gap — category (C) in `260901_plr-sema-research-b-f.md`. |
| (c) | The predicate language turning guard `condition` + `mentions_params` into a checkable predicate | §7 carries conditions as opaque strings precisely so this can land later without reshaping the pipeline. |
| (d) | Loop handling — `bounds_analyzer`'s `items_x`×`items_y` heuristic vs. sound widening | Widening is a lattice operation and presupposes (a). `loop_bounds_unknown` is the placeholder reason. **(round-4 remediation, B3 row (d) — REBUTTED, no change to the reason itself; one optional clause added:** whether the domain has finite height *is* (a)'s question, so the (a)-dependency claim is correct as written, not merely a conditional dressed up as one — `260901_plr-sema-research-a-d.md:395-399`'s "if the domain is typestate ... item (d) largely dissolves" IS that dependency, not a counterexample to it. If (a) resolves to a finite-height typestate domain, (d) resolves to *nothing to design*; if the verdict path ever includes numeric/volume accumulation, it does not — `260901_plr-sema-research-a-d.md:441-449` keeps that escape hatch open on its own.) **(260901, §Open decisions 2 — the volume/widening link this row's escape-hatch clause anticipated is narrower than that clause implied, on evidence, not merely narrowed by choice:** volume guards are already in the verdict path (`drop_tips` et al., depth 0, verified) — the actual open sub-question was never "is volume in scope" but "does (c)'s predicate evaluator interpret numeric `Cmp` atoms, or leave them at Kleene ½"; resolved to leave them at ½ through v1 and the first post-corpus increment, additive and reversible, touching one grammar production in (c), nothing in (a)/(d)/the wire. Two further facts narrow (d)'s live surface specifically: upstream `ResourceNode.items_x`×`items_y` (verified, `models.py:593-597`) gives **proved**, not heuristic, trip counts for plate-well loops, so bounded loops with a provable count need no widening even under an eventual interval domain — the condition under which (d) is live shrinks to "numeric accumulation across a loop whose trip count cannot be proved from the graph," which may be empty for the corpus this analyzer actually sees; and PLR's volume guards are gated by a process-global `does_volume_tracking()` runtime flag (verified, `liquid_handler.py:1032-1235`), so the first definite volume verdict needs a `SoundnessScope` environment-hypothesis record (deferred row (b)) before it is honest regardless of (d)'s resolution. See [§Open decisions](#open-decisions) 2 for the full resolution and evidence.) |
| (e) | Resolution strategy for the ~967 unresolved cross-class calls, INDEPENDENT of (a) | **(round-4 remediation, B3 row (e) — CONCEDE, fully; the stated reason was FALSE.)** `260901_plr-sema-research-c-e.md:225-265` calls the original "requires type inference whose precision requirements follow from (a)" ordering "fundamentally backwards" and shows the two are independent under a class-resolution reframing, backed by a 133-call measurement: 60–67% of the 10-tool closure's dropped-receiver calls resolve via a stdlib `ast` annotation pass that needs nothing from (a). **Scheduled as T11, after T6**, gated on `drop_tips` acquiring a `TipTracker.get_tip` guard at `depth > 0` (a concrete, checkable trigger — not "later" left unscheduled). §7.4's `top_unresolved.dropped_receiver` ranked view (M12) is T11's worklist — as of round-5 T0
(item 4), receiver-qualified and filtered rather than bare-named, so it now ranks e.g.
`self.head[channel].get_tip` (`blocks_methods: 3`) directly instead of collapsing it into a bare
`get_tip` row shared with five other receivers. |
| (f) | Precision / false-positive targets — the NUMBER is deferred | Meaningless before (a) and (b) fix what a "false positive" is; AC-7.4 and AC-8.3 deliberately set no thresholds. **(round-4 remediation, B3 row (f) — the stated reason SURVIVES, appended, not rewritten:** `260901_plr-sema-research-b-f.md:390-392`, endorsed: "'false positive' still has no referent for us: while every verdict is `UNKNOWN` there are no positives to be false" — that IS this row's reason. What is settled, per the same report, is the *shape*: an absolute count of `UNKNOWN` root causes — clusters, not raw findings — measured on a named, frozen benchmark at a fixed PLR pin, set after the first T6 measurement. Only the number stays deferred.) |

**Boundary summary — what this spec assumes and what changes when they land:**

| boundary | assumed now | changes when deferred item lands |
|---|---|---|
| §3.2 `join` | aggregation is a pure total function of a flat finding multiset | (a): `join`'s body and possibly signature (may need the graph, not just findings). `Finding`'s fields do not change. |
| §3.3 reasons | reasons are mechanical (which stage gave up), not semantic | (b): reasons stay; a *separate* soundness annotation may be added alongside. |
| §7.2 guards | `condition`/`scope_trail` are opaque strings; polarity is carried explicitly via `kind` (`raise_guard` fires true, `assert` fires false) | (c): `InlinedGuard` gains a parsed `predicate` field, interpreted according to `kind`'s existing polarity convention; `condition` is retained as the source of truth. |
| §7.2 closure | closure over resolved delegates only; unresolved → gap | (e): the frontier shrinks; the gap ledger's totals move. No structural change. |
| §8.1 bridge | a narrow string-mention heuristic, non-gating | (c): replaced wholesale by real predicate comparison. Must be replaced *before* §8 is ever made gating. |

---

## Risk table

| # | risk | likelihood | impact | mitigation / rollback |
|---|---|---|---|---|
| RISK-1 | **Closure over `delegates_to` recovers too little** — most real preconditions hide behind unresolved cross-class calls, and v1 is sound but empty (§7.6). Tip state lives on `self.head[channel]`, the canonical shape **not recorded by the survey's current `unresolved_calls` rule (recoverable — see round-5 T0, F1)** (§7.4 — this receiver shape isn't captured as an `unresolved_calls` gap; round-4's "unrecordable" wording overstated this as a property of the problem rather than of that one field/rule, and round-5 T0 recorded it, in `dropped_calls`, without changing `unresolved_calls` itself), and tips are what the 10 `SUPPORTED_TOOLS` care about. **This entire risk's round-1 answer rests on T6's counter being specified correctly (D12):** all four `SUPPORTED_TOOLS`-closure records inspected this round have `unresolved_calls: []` (`aspirate:45211`, `pick_up_tips:44929`, `drop_tips:45019`, `_check_containers:45147`), so `methods_with_no_recorded_gap` for the 10 tools **landed at 7/10 (T6, `51f53866`)** — high enough to be uninterpretable in exactly the way this risk names (round-6 remediation, R11 — corrected from an unmeasured "expected to land at or near 10/10" forecast left in place after T6 had already measured it). Separately, 750 of 967 unresolved-call entries (77.6%) are `send_command`, a firmware/transport method — the whole-surface `top_unresolved` aggregate is dominated by one name outside the tip-state frontier, which is why D12 requires publishing a `SUPPORTED_TOOLS`-closure-restricted view as well. | medium | **high — invalidates the approach** | **Measure first, and measure the right numbers (D3/D4/D12):** T6 runs the closure over all 1,314 finding-bearing functions and publishes `methods_with_no_recorded_gap` **alongside** the corrected dropped-receiver counters — `methods_with_dropped_receiver_call` (a commensurable method count) plus the per-method total/validation-looking call-node counts, using the corrected predicate (`func` is `ast.Attribute` AND NOT (`func.value` is `ast.Name` with `id == "self"`), not "non-`Name`-receiver") — and `top_unresolved` in both whole-surface and `SUPPORTED_TOOLS`-closure views. `methods_with_no_recorded_gap` alone is uninterpretable at a high value (§7.4's asymmetry note) — it could mean real derivation success, or it could mean the survey never saw the gaps to record. The dropped-receiver counters are what resolves the ambiguity. One session, data already on disk, before any user-facing surface. If the numbers indicate most content hides behind the frontier not recorded by `unresolved_calls`, deferred item (e) is promoted from "later" to "blocking" and §§7–8 pause. **Round-5 addendum (F1, PARTIAL):** the round-5 challenge patched the survey to record this frontier and reported the resulting whole-`SUPPORTED_TOOLS` figure moving `7/10 → 0/10` as proof the risk had resolved favorably. Reproduced and rejected: the `0/10` is produced by `logger.debug`/`inspect.signature`/`warnings.warn`/`args.keys` saturating every closure through `LiquidHandler._check_args`, not by tip-state guards — an unfiltered predicate that saturates by construction is exactly as uninterpretable as the `7/10` upper bound it claims to replace, only in the other direction, and it cannot ever move. The disambiguation it claims to supply was already published (`gap_ledger.json`'s `dropped_receiver_calls_by_method`, all ten `SUPPORTED_TOOLS` entries nonzero, round-4 M11). RISK-1's round-1 answer is unchanged: `methods_with_no_recorded_gap` (still an upper bound) plus the two D3 counters, now joined by a filtered, receiver-qualified `top_unresolved.dropped_receiver` worklist (round-5 T0 item 4, §7.4) that ranks the real signal (`self.head[channel].get_tip`, `blocks_methods: 3`) above the noise. |
| RISK-2 | Shim direction inverted — `plr_sema` imports `praxis` — making the boundary test unsatisfiable (§1.2). | low (now flagged) | high | §1.2 makes the arrow normative; the day-one boundary test converts a violation into a red test on the first offending commit rather than after N modules have moved. |
| RISK-3 | Cherry-pick drift test is skip-only off this machine (§5.2). | **certain** | medium | Two tiers. Tier 1 (header sha256 vs. local body) always runs and catches local edits, which is the failure this test primarily guards. Tier 2 skips loudly with the missing path named. AC-5.1 requires tier 2 to *run* here once, proving the mechanism before it is allowed to skip. |
| RISK-4 | Freezing `FAILURE_CATEGORIES` (dynamic-harness semantics) is wrong for a static analyzer; a static failure kind has no home (§4.3). | medium | medium | Miscategorisation surfaces as an implausible `harness_internal` rate in the gap ledger. Frozen-not-forbidden: extending is a design conversation, not a silent commit. |
| RISK-5 | The derived contract table is too large to ship to a browser (§6.4). | **measured, not blocking (260901 T11)** | medium | T6 measured 68 KB (10-entry, pretty-printed) for the pre-T11 `SUPPORTED_TOOLS`-only table; T11 measured the WHOLE-surface table (4,770 entries) at 4.4 MB pretty-printed / 3.0 MB minified / **146 KB gzipped** — not a blocker at this scale (see RISK-1's whole-surface update, above). "Restrict shipped contracts to `SUPPORTED_TOOLS`" is no longer this risk's mitigation, since that would re-impose the scope T11 exists to remove; the live mitigation lever, if payload ever DOES become a blocker at a larger future scale, is per-family sharding (`liquid_handling` 408 / `resources` 183 / `storage` 128 / `plate_reading` 124 entries) — available, not implemented. Decision 4 (Pyodide is a goal, not a gate) still means this cannot block v1. |
| RISK-6 | **RETIRED (remediation round 1, C11).** Formerly: `pydantic` in `plr_sema.check` unavailable/heavy under Pyodide. Resolved by removing the premise: §6.2 now specifies `check/` uses a stdlib-dataclass mirror of the node types it reads, and never imports `pydantic` at all — the Pyodide-availability question for `check/` no longer arises. (A server-side `extract/`, round 2, may still use pydantic; it never ships to a browser.) | — | — | Retired, not mitigated: the condition that would have triggered it cannot occur. |
| RISK-7 | §8's string-mention bridge produces noise, and the noise is mistaken for signal (§8.4). | medium | low-medium | Non-gating by AC-8.3. A >50% conflict rate is defined in advance as "bridge mismatched", not "contracts wrong" — a pre-registered interpretation that prevents post-hoc rationalisation. |
| RISK-8 | Hand-maintained ratchet is gamed by splitting rows (§9.4). | low | medium | **Partially mitigated, not closed (C13):** `test_every_row_justifies_itself` requires a written `why_not_derived`/`breaks_when` argument for any new row, raising the cost of splitting, and the 24-row cap (round 3; was 20) bounds proliferation. There is **no** cross-row sum check — splitting a 34-entry set into three ~11-entry rows would pass every per-row check and stay well under the row cap. Accepted as a known gap; see §9.4. The round-3 discovery of HM-20/HM-21 and the resulting cap raise (§9.4's discovery-vs-growth distinction) is itself an argument that the row-count cap is a coarse instrument — genuine discovery needs headroom, which cuts against a tight cap being the anti-gaming mechanism; the per-row justification requirement is doing the real work. |
| RISK-9 | The 45 hand-written contracts get hand-patched to fix §8 disagreements, silently defeating decision 2. | **medium-high** | high | AC-8.3 makes §8 explicitly non-gating; HM-13 is `TARGET_ZERO` with a monotonic count ratchet, so *adding* a 46th contract requires editing the declared ceiling in a visible diff. **The count ratchet alone fences growth only, not body edits** — `test_hand_written_contracts_content_is_pinned` (§9.3, C18) adds a content-hash ratchet over the 45 contracts' field values specifically to fence silent in-place edits, which is the failure mode this risk actually names. |

**RISK-1, whole-surface update (260901 T11).** RISK-1's round-1 answer above was scoped to the
`SUPPORTED_TOOLS`-closure population (10 methods, `7/10 methods_with_no_recorded_gap`). T11 decouples
derivation from that scope and re-runs the identical closure mechanic over the WHOLE 1,314
finding-bearing survey population, measured this session: **1,314 derived, 0 errors, 0.1s** (the
never-raises totality property, AC-7.2, held over 131x the prior population with zero exceptions);
**5,180 guards total, 2,360 (46%) inlined from a delegate at `depth > 0`** — i.e. own-body-only
derivation would have recovered fewer than half the guards this closure actually finds, the same
own-body-only failure mode `test_aspirate_closure_reaches_check_containers` (§7.5) already regression-
tests for one method, now confirmed at whole-surface scale; **610 gaps, 26 distinct method-name
"families" (by receiver class) represented** across the closure. Hand-sampled across families
(`VSpinBackend.spin`, `BioShake.start_shaking`, `CytomatBackend.send_command`,
`CytationBackend.set_gain`, `PreciseFlexBackend.set_motion_profile_values`, `NimbusDeck.from_files`,
`HID.setup`, `EL406ManifoldStepsMixin.manifold_prime`), all produced real, non-degenerate contracts.
This reconfirms RISK-1's mitigation is not an artifact of `LiquidHandler`-specific closure structure:
the same transitive-closure mechanic that resolved the risk for the 10-tool population resolves it
equally for the other 335 classes. **Payload is not a blocker at whole-surface scale either**
(measured, not estimated, §7.3): 4.4 MB pretty-printed / 3.0 MB minified / 146 KB gzipped for the full
4,770-entry table (RISK-5's concern, below, restated with a real number rather than "unknown
pre-corpus"). Per-family sharding (`liquid_handling`: 408 entries, `resources`: 183,
`storage`: 128, `plate_reading`: 124) remains available if payload ever does become a blocker at a
larger scale than measured here, but is explicitly NOT implemented by T11 — noted as a future lever,
not a present need.

**Rollback path (whole spec):** every round-1 change is additive **except T7** (C12) — T7 modifies
`training/verify/failure_taxonomy.py`. `training/verify/` sits outside `praxis/`, so AC-1.4's "no
`praxis` module is modified" claim is literally unviolated, but the spec as a whole is not purely
additive, and T7 gets its own revert step: `git checkout -- training/verify/failure_taxonomy.py` (or
revert the specific commit) restores the two-module `inspect.getmembers` walk. For every other task,
rollback is `git rm -r plr-sema/` and reverting the one added line in root `pyproject.toml`. No
`praxis` module is modified by any round-1 task, so no existing `praxis` import site can break
(AC-1.4 asserts this).

---

## Fixer task decomposition

Each task is ≤1 session, independently completable, with a runnable gate.

| task | scope | files | gate | ~LOC | depends on |
|---|---|---|---|---|---|
| **T1** | Package skeleton + workspace member + pytest config + AST import-boundary test | create `plr-sema/pyproject.toml`, `src/plr_sema/__init__.py`, `tests/test_import_boundary.py`; modify root `pyproject.toml:44` | `uv run pytest plr-sema/tests/test_import_boundary.py -q` + AC-1.1–1.4 | ~120 | — |
| **T2** | Cherry-pick `git_state.py` verbatim + header + `SurveyStamp` + provenance tests **+ ruff exclusion for `plr-sema` (root `pyproject.toml`'s `exclude` list, or a `plr-sema/.ruff.toml`)** so pre-commit's unrestricted `ruff --fix`/`ruff-format` doesn't reindent the picked 4-space file (C10) | create `src/plr_sema/_provenance/{__init__,git_state,stamp}.py`, `tests/test_provenance.py`; modify root `pyproject.toml`'s ruff `exclude` (or create `plr-sema/.ruff.toml`) | `uv run pytest plr-sema/tests/test_provenance.py -q` + AC-2.1–2.5 | ~190 (241 copied) | T1 |
| **T3** | Verdict types: `Verdict`, `Finding`, `PlrSite`, `AnalysisReport`, `join`, `REASON_VOCABULARY` + tests (incl. C15's literal-or-constant `reason=` resolution + reverse reachability check) | create `src/plr_sema/verdict.py`, `tests/test_verdict.py` | `uv run pytest plr-sema/tests/test_verdict.py -q` + AC-3.1–3.5 | ~220 | T2 |
| **T4** | Telemetry: `FAILURE_CATEGORIES` promotion, `TelemetrySink`, `JsonlSink`, event schema + tests | create `src/plr_sema/telemetry.py`, `tests/test_telemetry.py` | `uv run pytest plr-sema/tests/test_telemetry.py -q` + AC-4.1–4.4 | ~180 | T3 |
| **T5** | Fork-drift tests, both forks, both tiers, **`test_every_ported_module_is_covered` across all six coxswain-ported modules** (C3) | create `tests/test_fork_drift.py` | `uv run pytest plr-sema/tests/test_fork_drift.py -q -rs` + AC-5.1–5.4 | ~200 | T2 |
| **T6** | **Derivation closure + gap ledger — MEASURE FIRST (RISK-1)**. Load `plr_preconditions.json` via required `--survey-json PATH` (D19), `(module, qualname)`-keyed index + bare-name `resolve()` (C1), transitive `delegates_to` closure with frontier-carried `depth`, guard inlining incl. `kind` (C4), gap recording, ledger emitter with `methods_with_no_recorded_gap`, **`methods_with_dropped_receiver_call`, and `top_unresolved` published in both whole-surface and `SUPPORTED_TOOLS`-closure views** (D4/D12) **+ second independent AST pass over `external/` counting dropped-receiver call nodes per method using the corrected predicate — `func` is `ast.Attribute` AND NOT (`func.value` is `ast.Name` with `id == "self"`) — split into a total count and a validation-looking subset** (D3), **+ the derived `SUPPORTED_TOOLS`-name-to-`(module,qualname)` lookup rule** (D22), **+ respecified `test_guard_sites_point_at_defining_file`** (D5) | create `src/plr_sema/derive/{__init__,closure,ledger,receiver_shapes}.py`, `tests/test_derive.py` | `uv run pytest plr-sema/tests/test_derive.py -q` + `python -m plr_sema.derive --survey-json ... --gap-ledger` + AC-7.1–7.4 | ~450 | T3, T4 |
| **T7** | HM-8 → DERIVED: replace the 2-module exception walk with a `plr_exception_taxonomy.json` load, validated against the artifact's own `version.git_sha` / non-empty `classes` shape (`TaxonomyArtifactError`), **not** `plr_sema`'s `SurveyStamp` — M4, deliberate flagged deviation (C12c) | modify `training/verify/failure_taxonomy.py`; add regression test | existing `training/verify` tests pass + a new test asserting a class outside the 2 modules classifies as `precondition_state` **+ a test asserting the loaded taxonomy JSON is refused when it lacks a non-empty `version.git_sha` or `classes` array** | ~60 | T4 |
| **T8** | Extractor/checker split: package layout, stdlib-dataclass graph mirror (`check/graph.py`, no pydantic — C11) **with the derived-from-consumers field set for `OperationNode` and `ResourceNode`, plus a copied (not imported) `SUPPORTED_TOOLS` + its `test_supported_tools_match_upstream` drift test** (D1), `check_graph` round-1 entry point, **out-of-process fixture-graph generation** (subprocess call into the existing praxis extractor, committed under `tests/fixtures/`) (C5), poisoned-import tests, **Fork C's `test_mirror_fields_match_operation_node` field-set drift test against live `OperationNode`/`ResourceNode.model_fields`** (D8, ~+25 LOC), **the two moved-in end-to-end pipeline tests (AC-6.6/6.7, shipped as `test_full_pipeline_report_round_trips_json` / `test_full_pipeline_emits_stamped_jsonl`) for `AnalysisReport` round-trip and telemetry emission over the full T8 pipeline** (D15) | create `src/plr_sema/{extract,check}/__init__.py`, `src/plr_sema/check/graph.py`, `src/plr_sema/check/_supported_tools.py`, `tests/fixtures/<protocol>_graph.json`, `tests/test_check_graph.py`, `tests/test_check_graph_mirror_drift.py`, extend `tests/test_import_boundary.py` | AC-5.5, AC-6.1–6.7 | ~330 | T6 |
| **T9** | Hand-maintained registry + ratchet tests (incl. **broadened `measure` supporting AST-reading callables + `scripts/` sys.path shim** (C7), **HM-19 category-keyword row, now baseline 13/CAPPED(15), plus new HM-20 and HM-21 rows** (D6/D7/D8), **`peak: int` field on `HandMaintainedSurface`** (D16a), **live+2 headroom rule for MEASURE+CAPPED rows** (D16c), **HM-13 content-hash ratchet** (C18), **one-time registry cap re-baseline to `live_rows + 3` (21 + 3 = 24), discovery-vs-growth distinction documented** (registry cap decision); **+ HM-8 → `RETIRED` (declared 0) and the new HM-22 row, which must land in the same commit (§9.4, M5); + the `RETIRED` `Literal` member, `test_frozen_surfaces_are_exact` extended to `measure() == 0`, and the cap-lowers-with-retirement rule**); fill every **MEASURE** baseline via a one-off `--update-baselines` helper, committed in one reviewable commit — the ratchet test itself never writes (C14) | create `src/plr_sema/_hand_maintained.py`, `tests/test_hand_maintained_ratchet.py` | `uv run pytest plr-sema/tests/test_hand_maintained_ratchet.py -q` | ~380 | T3–T8 (needs all surfaces to exist) |
| **T10** | Differential harness vs. the 45 hand-written contracts, **loaded via a required `--contracts-path PATH`, AST-read, never imported** (D19, round-6 remediation R1), **`tip_bearing_params(qualname)` derived from the survey record's own `params` matched against HM-19's `tip_state` keyword** (D13, round-6 remediation R2 — the `MethodContract`-field-based definition was unachievable and is replaced), **`(module, qualname)` resolved by PascalCasing `receiver_type` + D22's unique-module lookup, with module-ambiguous (`Pump`, 3 contracts) and method-absent (13 contracts) both classified `hand_only`, not aborted** (round-6 remediation R5), **bridge handles `raises is None` / a `"<dynamic:"`-prefixed sentinel (detected via `.startswith`, D18) by falling through to the mechanical, derived condition-mention clause** (`mentions_params ∩ tip_bearing_params(qualname)`, D13), **consults `InlinedGuard.kind` to resolve the `HasTipError`/`pick_up_tips` polarity inversion before crediting a guard toward `requires_tips=True`** (D13), **loads `plr_exception_taxonomy.json` via a required `--taxonomy-json PATH`** (D19) | create `src/plr_sema/differential.py`, `tests/test_differential.py` | `python -m plr_sema.differential --taxonomy-json ... --contracts-path ... --report` + AC-8.1–8.3 | ~235 | T6, T9 |

**Dependency ordering.** `T1 → T2 → T3 → T4`; then `T5` and `T6` in parallel off T2/T4; `T7` off T4;
`T8` off T6; `T9` after T3–T8; `T10` last.

**Scheduling note that overrides the dependency graph (corrected, D14):** if capacity is limited,
**do T1 → T2 → T3 → T4 → T6 and stop.** The round-2 text named "T1 → T2 → T3 → T6" as the minimal
path, but T6's own dependency row requires T4 (§4's `FAILURE_CATEGORIES`), and T6's AC-7.4 gate
publishes a `by_category` block keyed on `FAILURE_CATEGORIES` (§7.4), which T4 creates — skipping T4
would degrade the gap ledger's category breakdown, not merely reorder unrelated work. T4 is ~180 LOC,
materially smaller than degrading T6's ledger to work around its absence. T6's gap ledger still
answers RISK-1, the only risk that can invalidate the approach, and it still does so against data
already on disk. Building T5/T8/T9/T10 before knowing T6's number is building infrastructure for a
pipeline that may need a different shape.

---

## Flags — locked decisions with implementability concerns

Per the brief's instruction to surface rather than silently work around. (Three further decisions are
open, not locked, and pending the user — see [§Open decisions](#open-decisions) near the top of this
document, added round 6, R14 — rather than filed here as flags on an already-made call.)

1. **Decision 1's shim is direction-ambiguous and only one direction is implementable.** "A
   compatibility shim so existing `praxis.*` import sites keep resolving" reads naturally as
   `plr_sema` re-exporting from `praxis`, which is structurally incompatible with the day-one
   boundary test. §1.2 resolves it normatively as `praxis → plr_sema`, but the resolution is mine,
   not the brief's, and should be confirmed.

2. **Decision 6's drift test cannot run off this machine.** The cisternal upstream is a
   machine-local absolute path. As stated, the test is green-when-skipped nearly everywhere. §5.2
   splits it into an always-on self-consistency tier and a skipping upstream tier; the always-on
   tier catches the primary failure (local edits) but *not* upstream drift. Decision 6 as literally
   stated ("ship a drift test against the cisternal source") is only satisfiable on developer
   machines with cisternal checked out.

3. **Decision 2 is implementable but will reduce actionable output relative to today.** Derivation
   yields `UNKNOWN` where a human previously asserted an answer. That is more honest and less
   useful, simultaneously. It is only sustainable if §8 stays non-gating (AC-8.3); otherwise the
   pressure to hand-patch returns and decision 2 fails in practice while appearing to hold.

4. **Decision 7's gap ledger needs a stable `UNKNOWN`-reason key set, which looks like a semantic
   commitment we are deferring.** §0/§3.3 resolves this by making reasons *derivation-mechanical*
   (which stage gave up) rather than semantic (why the property is undecidable). I believe this is
   sound, but it is the load-bearing move that lets decisions 5 and 7 coexist with deferred item
   (b), and it deserves adversarial attention.

5. **Not an unimplementability, but the largest content risk:** RISK-1. Nothing in the spec
   establishes that closure over `delegates_to` recovers materially more than a method's own body
   *at scale*. The `aspirate` example proves it recovers more in one case. T6 is scheduled first to
   turn this from an assumption into a number.

## References

- Dispatch brief, `task_id: 260901_plr_jit_spec` (measured substrate — figures cited throughout).
- `/home/marielle/projects/cisternal/src/cisternal/telemetry/git_state.py` — cherry-pick source.
- `training/verify/failure_taxonomy.py` — the closed 6-category set and its rationale.
- `scripts/plr_survey_common.py`, `scripts/survey_plr_preconditions.py` — survey mechanics + record schema.
- `coxswain/tests/test_import_boundary.py` — the AC-2/NFR-2 boundary-test precedent.
- `coxswain/tests/test_sim_port.py` — the parity-test anti-pattern §5.1 **complements** (not
  replaces, C17): it covers symbols from the three partial-lift modules, while pre-C3 §5.1 reached
  only the two whole-file-verbatim modules — a real, if incidental, disjointness. Post-C3, §5.1's
  `test_every_ported_module_is_covered` reaches all six ported modules' headers, so the disjointness
  this note originally flagged no longer holds, though nothing here instructs deleting or altering
  `test_sim_port.py` itself.
- `coxswain/pyproject.toml` — workspace-member + pytest-addopts precedent.
- `praxis/backend/utils/plr_static_analysis/models.py:520-661` — graph node types.
- `.praxia/docs/specs/260827_coxswain-corpus-ingestion-increment-1.md` — adversarial-convergence format precedent.

---

## Remediation changelog (round 1 → round 2)

Applied by the remediation specialist against the challenger's 24 objections and the defender's
adjudication, `task_id: 260901_plr_jit_spec`. Every fix below is applied exactly as adjudicated — no
locked decision was reopened, and none of the six literature-corpus-deferred items (abstract
domain/lattice/widening; the formal meaning of `UNKNOWN`; the predicate language; loop handling;
resolution of unresolved cross-class calls; precision/FP targets) was specified.

**BLOCKER**

- **C1** — §7.2: added a normative `resolve()` rule for bare `delegates_to` names (class-first
  precedence, then module-level, then `no_contract_derived` gap); index rekeyed to
  `(module, qualname)`; noted no survey regeneration is needed (the discriminator is recoverable from
  `survey_plr_preconditions.py:253/255`); residual same-name-different-class ambiguity accepted.
- **C2** — §7.4/§7.1/§7.6/§7.7/T6: renamed `methods_fully_derived` → `methods_with_no_recorded_gap`
  everywhere; stated normatively that the survey never records `self.<expr>.<method>()` receivers, so
  the figure is an upper bound; added the low-refutes/high-uninterpretable asymmetry and updated
  RISK-1's mitigation; corrected §7.4's example JSON to a bare call name; added a new T6 deliverable
  (independent AST pass counting non-`Name`-receiver calls per method) and raised T6's budget
  350→420 LOC; named the pre-`SAFE` fence as a forward hazard, not a round-1 defect.
- **C3** — §5.1/§5.3/§5.4/§5.5/T5: corrected "four" ported modules to **six**, with all three header
  forms documented; scoped byte/content comparison to the two whole-file-verbatim modules; added
  `test_every_ported_module_is_covered` (fail loudly on any unrecognized header form); corrected the
  DERIVED classification claim to state its actual (narrower) scope; respecified the ±2-line
  tolerance as per-member and inapplicable to the four disjoint/adaptation modules; AC-5.1 now covers
  five tests and all six modules; modest T5 budget bump (160→200 LOC).
- **C4** — §7.2/§7.7/§8.1/deferred-boundary table/T6/T10: added `InlinedGuard.kind` (`raise_guard`
  fires true, `assert` fires false) with the polarity stated normatively; updated the boundary-summary
  row; specified §8.1's bridge behavior when `raises` is `None` (assert) or the `"<dynamic:*>"`
  sentinel (falls through to the condition-mention clause, contributes neither for-nor-against).
- **C5** — §6.2/§6.3/§6.5/§7.7/T8: round-1 entry point is `check_graph(graph_json, contracts_json)`;
  `@jit`/`check(fn)` (source→graph) deferred to round 2; fixtures produced out-of-process by the
  existing praxis extractor, committed under `tests/fixtures/`; moved the full-pipeline
  `len(findings) >= len(operations)` coupling check from AC-7.2 to AC-6.3 (T8's gate), resolving the
  T6/T8 circularity by decoupling rather than inverting the dependency; added AC-6.4 pinning
  `operation_id` provenance against the fixture graph's real node ids; noted AC-7.2/§7.5's existing
  anti-stub gates are being strengthened, not repaired from nothing; added `derive/` to §6.2's
  server/browser/build-time enumeration (the "§1.1 omits extract/check/derive" objection's actual
  target — §1.1's own tree already listed all three; §6.2's three-way split did not mention `derive/`
  at all, which is the enumeration this fix corrects).

**MAJOR**

- **C6** — HM-1 baseline 33→34; §9.4 shrink-target total 81→82.
- **C7** — §9.1/T9: broadened `measure` to permit an AST-reading callable (source path + target
  symbol) alongside the import-path form, since six rows (HM-2/3/4/6/7/8) measure facts embedded in
  function bodies; added a `scripts/` `sys.path` shim for HM-15's import-based measure; raised T9's
  budget 250→350 LOC.
- **C8** — §2.2: added one normative sentence — `survey_stamp()` is memoized at most once per
  process; `emit` never shells out.
- **C9** — §2.1/AC-2.3/§4.2: corrected "40-hex `dirty_content_id`" to state both the 40-hex
  (tree-OID) and 64-hex (sha256 fallback) cases; made `test_event_carries_stamp` sentinel-tolerant for
  the `nogit`/`unavailable` branches instead of asserting universal 40-hex.
- **C10** — Elevated to normative, tested T2 scope: added AC-2.5 and a T2 deliverable requiring
  `plr-sema` be excluded from root `pyproject.toml`'s ruff `exclude` (or a `plr-sema/.ruff.toml`), since
  the unrestricted pre-commit `ruff --fix`/`ruff-format` hooks would otherwise reindent the 4-space
  cherry-picked file on first commit.
- **C11** — §6.2/Risk table: dropped the pydantic permission for `check/`; adopted RISK-6's own
  mitigation (stdlib-dataclass mirror of the node types `check/` reads) as the round-1 design; RISK-6
  marked RETIRED rather than deleted, with the resolution recorded in place.
- **C12** — §4.2/rollback path/T7: restricted the exception-classifier gap claim to
  `classify_check_failure` only (`classify_exception` is unaffected — confirmed by read); named T7 as
  the one non-additive round-1 change with its own revert step; added a T7 gate requirement that the
  loaded taxonomy JSON carry a validated `SurveyStamp`. Did not add the rebutted
  already-published-corpus-statistics or name-collision claims.
- **C13** — §9.4/RISK-8: replaced the unenforced "sums `declared` across rows sharing a metric kind"
  claim with an honest statement of the actual (narrower) per-row + row-count-cap mechanism, naming
  the splitting-for-gaming gap as accepted rather than closed.
- **C14** — §9.2/T9: replaced the self-writing-ratchet-test description with a one-off
  `--update-baselines` helper (T9, human-reviewed commit); the ratchet test itself never writes. Did
  not add the rebutted "only 15 of 18 rows evaluable" claim — C7's broadened `measure` makes all rows
  numeric by T9 completion.
- **C15** — §3.3/§3.4: unbolded the "DERIVED from our own pipeline's control flow" prose emphasis
  (did not retag the section's one formal `Classification:` tag, which was already correct);
  redefined `test_reason_vocabulary_closed` to resolve `reason=` as a literal-or-module-constant
  (failing on unresolvable forms) plus a reverse reachability check; small T3 budget bump (200→220).
- **C16** — §8.1/§9.2/§9.4: added registry row HM-19 (category-keyword pairs table,
  `scripts/survey_plr_exceptions.py:61`); named the tip-related category explicitly as `category ==
  "tip_state"`; registry 18→19 rows, budget headroom 2→1.
- **C17** — References: changed "the parity-test anti-pattern §5.1 replaces" to "complements", with a
  note that C3's fix dissolves the disjointness the original phrasing implied.
- **C18** — §9.3/RISK-9: added `test_hand_written_contracts_content_is_pinned`, a sha256 content
  ratchet over the 45 hand-written contracts' field values, fencing silent body edits that the
  count-only ratchet cannot see; updated RISK-9's mitigation accordingly. Did not touch AC-8.3 or the
  46th-contract framing (rebutted).

**MINOR**

- **C19** — §1.3: corrected `test_import_boundary.py`'s LOC count 46→61.
- **C20** — folded into C1's §7.2 rewrite: `seen = {}` → `seen = set()`; `depth` now carried
  explicitly on the frontier as `(qualname, depth)` rather than derived from `len(seen) - 1`.
- **C21** — AC-3.3: reworded to construct `Finding(..., reason="")` explicitly (raises `ValueError`)
  rather than omitting `reason` (which raises `TypeError` before `__post_init__` runs).
- **C22** — §2.3: corrected `test_git_env_stripping` to set `GIT_DIR` via `monkeypatch.setenv` in the
  **test process**, not "the subprocess env".
- **C23** — §7.1/§7.2/§7.4: reworded "967 `unresolved_calls`" to "967 unresolved-call entries across
  854 functions (75 distinct call names)" — N and M computed this round via `Grep`-based extraction of
  every non-empty `unresolved_calls` array against `training/verify/data/plr_preconditions.json`
  followed by manual dedup (no code-execution tool was available in this remediation pass to automate
  the dedup; treat 75 as a spot-check, not an authoritative re-derivation — T6's gap ledger is the
  authoritative source going forward). Noted names are not class-qualified, so unrelated `_check_*`
  helpers on different classes collapse into one `top_unresolved` row.
- **C24** — folded into C1: index keyed by `(module, qualname)`; `plr_survey_common.py:127-129`'s
  duplicate-class-name fact cited as the reason the class-first precedence rule is needed at all.

**Conflicts between fixes, and how they were resolved.** C2 and C5 both touch T6/T8's boundary: C2
adds a new T6 deliverable (the receiver-shape counter) while C5 moves the full-pipeline coupling
check out of T6's gate (AC-7.2) into T8's (AC-6.3). These are complementary, not conflicting — C2
narrows what T6 measures (mechanical, no graph needed) exactly as C5 narrows what T6 gates on
(no `check_graph` needed), so applying both together is what makes T6 buildable standalone at all. No
other fix pair required a resolution choice beyond what each objection specified.

**Not applied, and why.** Nothing was left unapplied among the adjudicated fixes. Two items are
flagged as approximate rather than exact: (1) C23's M=75 distinct-name figure, per the methodology
note above (no code-execution tool available to this remediation pass — `Grep`/`Read` only); (2) the
"§1.1 omits extract/check/derive" clause of C5 was applied to §6.2 instead of §1.1, since §1.1's
directory tree already listed all three subpackages and §6.2's server/browser split was the actual
enumeration missing `derive/` — the underlying intent (a complete, consistent file-layout enumeration)
is satisfied either way.

**Updated task-budget table (T5/T6/T8/T9 changed; others listed for context):**

| task | round-1 LOC | round-2 LOC | delta | driver |
|---|---|---|---|---|
| T1 | ~120 | ~120 | — | — |
| T2 | ~180 (241 copied) | ~190 (241 copied) | +10 | C10 (ruff exclusion) |
| T3 | ~200 | ~220 | +20 | C15 (reason resolution + reverse check) |
| T4 | ~180 | ~180 | — | — |
| T5 | ~160 | ~200 | +40 | C3 (six-module coverage test) |
| T6 | ~350 | ~420 | +70 | C2 (receiver-shape counter) |
| T7 | ~60 | ~60 | — (gate strengthened, not LOC) | C12 |
| T8 | ~200 | ~260 | +60 | C5 (fixture generation + stdlib mirror) |
| T9 | ~250 | ~350 | +100 | C7 (AST-reading measures + shim), C16, C18 |
| T10 | ~220 | ~220 | — (bridge logic reworded, not sized) | C4 |

**Registry row count and budget headroom:** 18 → **19** rows (HM-19 added, C16); budget cap unchanged
at 20; headroom 2 → **1**.

**Everything applied; nothing left for a future round by omission** — the six literature-corpus
deferrals remain exactly as scoped in round 1, untouched.

---

## Remediation changelog (round 2 → round 3)

Applied by the remediation specialist against the round-2 challenger's 22 objections (D1–D22) and the
defender's adjudication, `task_id: 260901_plr_jit_spec`. Every fix below is applied exactly as
adjudicated — no locked decision was reopened (seam-first; no hand-written contracts; telemetry
first-class; Pyodide goal-not-gate; tri-valued verdict; verbatim `git_state.py` cherry-pick; generated
gap ledger; `praxis → plr_sema` shim direction), and none of the six literature-corpus-deferred items
was specified.

**BLOCKER**

- **D1** — §6.2/§6.3/§6.5/T8: replaced the "id, receiver_type, depends_on_params, and a node-kind
  discriminant, nothing else" enumeration with a derived-from-consumers table (each mirrored field
  named against the §3.3 reason or §7.3 lookup that consumes it: `id:531`, `line_number:532`,
  `method_name:533`, `receiver_variable:534`, `receiver_type:535`, `arguments:536`, `node_type:539`,
  `depends_on_params:546`, `foreach_source:551`, `foreach_body:554`); stated normatively that
  `ResourceNode` is mirrored too (`ungroundable_reference` has no other source); flagged
  `check_graph`'s pre-fix degenerate-not-inert failure mode (AC-6.3/AC-6.4 satisfiable from `id`
  alone); added the adjacent `SUPPORTED_TOOLS`-must-be-copied-not-imported fix with a
  `test_supported_tools_match_upstream` drift test (new AC-6.5) mirroring §4.2's pattern, needing no
  new registry row (HM-9 already covers the fact).
- **D2** — §6.2: deleted the `_common/` line; replaced with a note that `derive/`'s survey-JSON input
  is resolved via a required `--survey-json PATH` (folds in D19's first half).

**MAJOR — the load-bearing fix (D3) and its dependents**

- **D3** — §7.2/§7.4/§7.5/§7.6/§7.7/RISK-1/T6: corrected the dropped-receiver predicate to `func` is
  `ast.Attribute` AND NOT (`func.value` is `ast.Name` with `id == "self"`), replacing the false
  "receiver is not a bare `ast.Name`" characterization, which under-counted by excluding
  `resource.get_item()`-style calls whose receiver *is* a bare, non-`self` `Name`. Widened §7.2's
  scope-note framing from `self.<expr>.<method>()` to the corrected predicate. Split T6's new counter
  into two published figures — total dropped-receiver call-node count and its validation-looking
  subset — and stated the primary figure must not gate on `_is_validation_looking` (unreachable for
  the dropped population). Renamed and re-specified `test_non_name_receiver_calls_are_counted` →
  `test_dropped_receiver_calls_are_counted` with both the `Subscript`-receiver and bare-non-`self`-
  `Name`-receiver cases as fixtures.
- **D4** — §7.4/§7.7/RISK-1/T6: named the second, method-level figure
  `methods_with_≥1_dropped_receiver_call` (commensurable with `methods_with_no_recorded_gap`, both
  method counts) rather than calling per-method call-node counts "the denominator"; demoted the
  per-method call-node counts to an explicitly secondary diagnostic; stated exactly which three
  figures AC-7.4 publishes as method counts and which two are secondary.
- **D5** — §7.5: respecified `test_guard_sites_point_at_defining_file`, whose "`depth > 0` and
  cross-file" antecedent is structurally unsatisfiable under C1's `resolve()` (both lookups run
  against `rec.module`), as a universal property over the closure — for every guard with `depth > 0`,
  `site.qualname != entry_qualname` and `site.lineno` is the delegate's line — noting the cross-file
  form becomes satisfiable only after deferred item (e).
- **D9** — §0: added one clause distinguishing round 1's actual entry point (ingests a pre-extracted
  execution graph, `check_graph`, §6.2) from the round-2 `@jit`/`check(fn)` capability (ingests a
  protocol function directly), which the stale prose had conflated.
- **D12** — §7.4/RISK-1/T6: `top_unresolved` is now published in two views — `whole_surface` (honest
  aggregate) and `supported_tools_closure` (the actionable worklist) — with AC-7.4 gating on neither;
  absorbed the 77.6%-`send_command` finding and the "all four inspected `SUPPORTED_TOOLS` records have
  `unresolved_calls: []`" finding into RISK-1's mitigation text, since it is what makes RISK-1's
  round-1 answer depend entirely on T6's counters being specified correctly.
- **D13** — §8.1/T10: defined "a tip-related identifier" mechanically as `mentions_params ∩
  tip_bearing_params(qualname)` (derived from `method_contracts.py`'s `requires_tips_count`-governed
  parameters, no new registry row), replacing the undefined lexical phrase; corrected the round-2
  claim that `pick_up_tips`'s `raises: "HasTipError"` clause is dead (it is live — `_NAME_KEYWORD_
  CATEGORIES`'s first pair matches `"Tip"` in the class name); added the free-standing polarity fix —
  `HasTipError` corroborates *absence* of tips, the opposite of `requires_tips=True` read naively — so
  the bridge must consult `InlinedGuard.kind` before crediting a guard.
- **D14** — Scheduling note: corrected "T1 → T2 → T3 → T6 and stop" to "T1 → T2 → T3 → T4 → T6 and
  stop", since T6 depends on T4 (`FAILURE_CATEGORIES`) and AC-7.4's `by_category` block is keyed on it
  — T4 is ~180 LOC, materially cheaper than degrading the ledger to work around its absence.
- **D15** — AC-3.4/AC-4.3/§6.5: reworded both ACs to construct `AnalysisReport`/a `Finding`-derived
  event directly (as their own named tests already do), and added AC-6.6/AC-6.7 in T8's block for the
  full-pipeline forms of the same claims, since T3/T4 alone have no working pipeline to run one
  against.

**MAJOR — registry and Fork C**

- **D6** — §9.1: corrected "only HM-15... is import-measurable" to "HM-15 and HM-19", since
  `_NAME_KEYWORD_CATEGORIES` (HM-19) is also a module-level `list[tuple[str,str]]`, exactly like
  HM-15; filled HM-19's baseline as **13** (confirmed by read, not MEASURE) with `measure` optionally
  simplifiable to the import form; did **not** touch §9.2's AST-mechanism specification for HM-19
  itself (rebutted as over-engineered-not-wrong).
- **D7** — §9.2/§9.4: added registry row **HM-20** (`_MODULE_SUBSTRING_CATEGORIES`, 6 pairs, CAPPED
  (8)); did **not** add the rebutted §8.1 impact claim (HM-20's six categories cannot emit
  `tip_state`); did **not** register the `category: str = "uncategorized"` default as its own row
  (noted in HM-20's `breaks_when` instead).
- **D8** — §5 (new §5.3 "Fork C"), §9.2, T8: rebutted the claim that §6.2:828's "no third model
  hierarchy" sentence is false (it is correctly scoped by its own clause; left unchanged). Conceded
  and added: Fork C (`check/graph.py`'s field-set mirror of `OperationNode`/`ResourceNode`), living
  under `plr-sema/tests/` (exempt from §1.3's `src/plr_sema/`-scoped boundary walk) so it may import
  `praxis` and compare against live `model_fields`, mirroring §4.2's `test_categories_match_upstream`
  pattern; added registry row **HM-21**; renumbered §5's Verification/Failure-mode/Acceptance-criteria
  subsections 5.3/5.4/5.5 → 5.4/5.5/5.6 to make room; folded ~+25 LOC into T8.
- **D16** — §9.1/§9.2/§9.3 (PARTIAL): (a) added `peak: int = 0` to `HandMaintainedSurface`; (c) added
  the live+2 headroom rule for MEASURE+CAPPED rows (matching HM-3/HM-4's existing precedent), since
  the bare live count gives zero headroom; (b) added one clarifying sentence that table annotations
  like "CAPPED, must decrease after peak" combine the `status` `Literal` with prose, and are not
  themselves additional enum members (softened finding, not a violation — no structural change).
- **D17** — §9.4: corrected the post-conversion survivor list from 11 to **15** rows
  (HM-3/4/5/6/9/10/11/14/15/16/17/18/19/20/21), explicitly separating out HM-2/HM-12 as the "≤2
  `DERIVABLE_NOT_YET`/`TARGET_ZERO`" rows still pending resolution.
- **Registry cap decision** — §9.4: raised the cap **20 → 24**; documented the normative
  discovery-vs-growth distinction (discovery re-baselines the cap once, at T9, in a reviewed commit;
  growth never raises it); re-baseline mechanism specified as `live_rows + 3` (21 + 3 = 24), strict
  monotonicity thereafter; updated RISK-8's cap reference and added a note that two consecutive rounds
  of honest discovery is itself evidence the row-count cap is a coarse anti-gaming instrument relative
  to the per-row justification requirement.

**MINOR**

- **D10** — §7.4: changed the JSON example's `top_unresolved` call name from `get_tip` to
  `send_command` (the empirically dominant entry, 77.6%); added the correction that a bare `get_tip`
  *can* be recorded (only the literal `self.head[channel].get_tip()` shape cannot) — did not overstate
  the gap.
- **D11** — §8.1: repointed the citation "§4.2, HM-19" to **§9.2**, where the registry table (and
  HM-19) actually live.
- **D18** — §7.2/§8.1: replaced equality-against-`"<dynamic:*>"` with the normative detection rule
  `raises.startswith("<dynamic:")`, in both the `derive_contract` pseudocode comment and §8.1's bridge
  text.
- **D19** — §6.2/§7.3/§7.4/T6: specified a required `--survey-json PATH` (no default) on every
  `python -m plr_sema.derive` invocation; §7.1/T10: specified a required `--taxonomy-json PATH` on
  `python -m plr_sema.differential`, and added it to T10's row and gate command.
- **D20** — §1.3: deleted the `test_import_boundary.py` LOC count entirely (46 → 61 → 60 across three
  rounds) rather than attempting a fourth correction; "read this session, ported verbatim in
  structure" already carries the meaning.
- **D21** — §5.1: replaced the imprecise "the disjoint-multi-member and no-range-adaptation forms do
  not [parse]" with the precise statement that the multi-member headers *do* parse (a uniform,
  regex-parseable per-member form); what round 1 actually declines to build is per-member body
  extraction from the fork file, which needs symbol-range resolution, not a header grammar. Left §5.4
  (now §5.5)'s ±2-line tolerance discussion untouched (rebutted — the incoherence claim holds for all
  four partial-lift/adaptation modules, confirmed arithmetically against `failure_modes.py`).
- **D22** — AC-7.2: replaced the implicit hand-written-map assumption with a derived rule — for each
  `SUPPORTED_TOOLS` bare name, look up `(module_of(LiquidHandler_record), f"LiquidHandler.{name}")`
  against the existing `(module, qualname)`-keyed index, failing loudly if absent — giving AC-7.2 a
  real failure mode if PLR relocates `LiquidHandler` or renames a tool, with no new registry row.

**Conflicts between fixes, and how they were resolved.** D3 and D4 both touch the same counter: D3
corrects the *predicate* and splits it into two per-method call-node figures; D4 renames the
*method-level* aggregate and clarifies which figures are commensurable. These are complementary, not
conflicting — applying both together produces the final shape (two call-node diagnostics from D3, one
new method-count headline from D4, three commensurable method counts published by AC-7.4). D1 and D8
both touch `check/graph.py`'s field set: D1 defines *what* is mirrored (derived-from-consumers); D8
adds the drift test that keeps that mirror honest over time. Applying D1 before D8 is required — D8's
own text says its drift test "is only meaningful once §6.2's D1 fix" lands — and both are applied in
that order in §6.2/§5.3 respectively. D5 and D3/D22 all touch §7.2's `resolve()`/closure mechanics but
target disjoint properties (guard-site provenance vs. dropped-receiver counting vs.
`SUPPORTED_TOOLS`-name lookup) and required no reconciliation beyond keeping all three normative rules
stated in the same section without contradiction.

**Not applied, and why.** Nothing was left unapplied among the adjudicated fixes. Every BLOCKER,
MAJOR, and MINOR item (D1–D22) plus the registry cap decision was applied. The six
literature-corpus-deferred items remain exactly as scoped in round 1, untouched.

**Updated task-budget table (T5/T6/T8/T9/T10 changed; others listed for context):**

| task | round-2 LOC | round-3 LOC | delta | driver |
|---|---|---|---|---|
| T1 | ~120 | ~120 | — | — |
| T2 | ~190 (241 copied) | ~190 (241 copied) | — | — |
| T3 | ~220 | ~220 | — | — |
| T4 | ~180 | ~180 | — | — |
| T5 | ~200 | ~200 | — (AC range only: 5.1–5.4 → 5.1–5.5, corrected round 6 — the original arithmetic was wrong by one; D8 added exactly one AC (AC-5.5), and it gates T8, not T5 — see T5's row) | D8 (Fork C ACs, no T5 LOC) |
| T6 | ~420 | ~450 | +30 | D3 (dual dropped-receiver counters), D4 (method-count figure), D12 (two `top_unresolved` views), D22 (derived `SUPPORTED_TOOLS` lookup), D5 (respecified guard-site test) |
| T7 | ~60 | ~60 | — | — |
| T8 | ~260 | ~330 | +70 | D1 (mirror field-set + `SUPPORTED_TOOLS` copy + drift test), D8 (Fork C drift test, ~+25), D15 (two moved-in end-to-end ACs) |
| T9 | ~350 | ~380 | +30 | HM-20/HM-21 rows, `peak` field, live+2 headroom rule, one-time cap re-baseline (D6/D7/D8/D16/registry cap decision) |
| T10 | ~220 | ~235 | +15 | D13 (mechanical tip-identifier + `kind`-based polarity check), D18 (`.startswith` detection), D19 (`--taxonomy-json` flag) |

**Registry row count, cap, and headroom:** 19 → **21** rows (HM-20, HM-21 added); cap **20 → 24**;
headroom 1 → **3**.

**Everything applied; nothing left for a future round by omission** — the six literature-corpus
deferrals remain exactly as scoped in round 1, untouched. The spec remains gated on the literature
corpus for the six deferred semantic questions; this round closes out the mechanical/structural gaps
the round-2 challenger found in the corpus-independent plumbing.

---

## Remediation changelog (round 3 → round 4)

**What made round 4 different.** Rounds 1–3 reviewed a *document*. Round 4 reviewed *running code*:
T1–T8 shipped between round 3 and round 4, and eight tasks of building falsified claims the spec had
made from reading. 22 objections (5 BLOCKER, 12 MAJOR, 5 MINOR); adjudicated **13 CONCEDE, 8 PARTIAL,
1 REBUT**.

**The defect class this round found — worth stating once, because it recurred four times.**
*Acceptance criteria satisfiable without the property being true.* AC-1.1 passed against a package
exporting nothing (M6). AC-6.7 passed because the test did the emitting the pipeline never does (M2).
`test_join_truth_table` passed by comparing `join` against a copy of itself (M7). And AC-6.3's
`len(findings) >= 1` never established the per-operation covering its own justification rested on
(B2). These survived three prior rounds because a document review cannot see them.

### Conceded, with what changed

| id | sev | change |
|---|---|---|
| **B1** | BLOCKER | `check_graph` returned `SAFE` for a zero-operation graph — §0's organizing claim was **false about the shipped artifact**. `join(())` met a `_findings_for_operation` returning `[]`, emitting `SAFE` with zero obligation discharged, before the fence §7.4 defers even exists. Fixed in code; §0:39 and §6.2:962 corrected. |
| **B2** | BLOCKER | §3.2's "unreachable in v1" claim deleted. AC-7.2 asserts only never-raises, per-method, *not* against a graph — so "every operation therefore receives at least one `Finding`" was a non-sequitur, and the coupling was asserted nowhere across T3→T8. |
| **B4** | BLOCKER | `argument_not_static` **withdrawn**, `REASON_VOCABULARY` 8 → 7. It intersected `free_vars` (PyLabRobot's *callee* parameter namespace) with `depends_on_params` (the *user protocol's*) — disjoint scopes, so it fired only on name coincidence, generating false positives and false negatives simultaneously. Shipping a reason that cannot work is worse than not shipping it. |
| **M2** | MAJOR | Telemetry: no `src/` path ever called `emit`. §4/§0's "first-class" claim and AC-6.7 rewritten to describe what is actually tested. |
| **M3** | MAJOR | RISK-4's `harness_internal` tripwire is structurally inert in v1 (`category` is required only for `WILL_FAIL`, which v1 never emits). Marked "no detection in round 1" rather than describing a mechanism that cannot fire. |
| **M4** | MAJOR | T7's `SurveyStamp` wording dropped; the artifact carries `{git_sha, git_dirty, pylabrobot_version}` and staleness is **queryable, not enforced**. Recorded honestly rather than claiming a detectability the code does not deliver. |
| **M5** | MAJOR | §9 gained a **`RETIRED`** status, kept-not-deleted, `declared == 0`, exactness enforced. HM-8's trigger FIRED at T7 so the row retires; T7's own unregistered surface (`_TAXONOMY_PATH` + the 2-key validation schema) registers as **HM-22**. Net `live_rows` 21 → 20 → 21; cap 24 stands. **Retiring a row now lowers the cap by one**, closing the headroom drift (3 → 4) that strict monotonicity exists to prevent. |
| **M6** | MAJOR | `check_graph`, `Verdict`, `AnalysisReport` exported; AC-1.1 strengthened from "`import plr_sema` exits 0" to asserting importability of the declared surface. |
| **M8** | MAJOR | `AnalysisReport.stamp` is the *contract-build* stamp, not the analysis stamp — `check/` never computes one, so a browser deployment leaves the checker's own version unrecorded. Recorded as build-time-only; AC-6.7 rewritten to a falsifiable claim. |
| **m2** | MINOR | AC-7.3's byte-identity determinism claim was unmechanized; now tested. |
| **m4** | MINOR | Field name reconciled: the non-ASCII `methods_with_≥1_dropped_receiver_call` is not a wire-format key. Artifact name `methods_with_dropped_receiver_call` is normative. |
| **m5** | MINOR | 379 of 2,814 findings (13.5%) carry `condition: null` — a `raise` with no enclosing `if`. Specified as predicate **TRUE**, not "no constraint"; the latter reading is unsound in the `SAFE` direction. §7.2's polarity note extended. |
| **§0(i)** | — | §0 now states that trivial soundness carries **zero mathematical obligation** and gives no evidence about the post-corpus analyzer — `def analyze(op): return UNKNOWN` satisfies the definition. Independent of B1; §0(ii) *is* B1 and was not remediated twice. |

### Partial — where the challenge overreached

| id | what stands / what does not |
|---|---|
| **B3** | **Shrank from "4 of 6 Deferred rows falsified" to 1.** Only **(e)** is genuinely falsified — its stated dependency on (a) is backwards, and 60–67% of the 10-tool frontier resolves by a stdlib `ast` annotation pass. **(d) is not falsified at all**: whether the domain is finite-height *is* (a)'s question, so "widening presupposes (a)" holds as written. **(b) and (f) have their stated reasons *confirmed*** by the very reports cited against them — under-scoped, not wrong. §0's narrowness justification and RISK-1's trigger **survive**. |
| **B5** | The mirror's omissions are real (branch structure, and four unconsumed fields — see M1). But the sharpest sub-claim is **factually wrong**: `computation_graph_extractor.py:547` gates the tips precondition on `"tips_loaded" not in self._active_states`, and op_1 adds it — so `aspirate` omitting it is correct flow-sensitive satisfaction, not a hidden disagreement. Decisively, that typestate content comes from **five hand-typed frozensets** (`TIPS_REQUIRED_METHODS` et al., `:41-77`): mirroring it would **launder a hand-written method contract into the analyzer**, which decision 2 bans and §8 exists to measure against. The "third source of truth" is real and must *not* be trusted. |
| **M1** | The four unconsumed mirror fields are real; the mirror is over- *and* under-inclusive against its own normative *iff*. Fixed. |
| **M7** | "Establishes nothing" is overstated — `_expected_verdict` lives in a different file, so a wrong `join` body *does* turn it red. What genuinely matters: no case ever shared an `operation_id`, so the unsound Kleene case was never exercised. Literal table + same-operation case added. |
| **M9** | The parenthetical reason *is* loose and was replaced. But the alleged contradiction with "exactly one function aggregates" **is not in the report** — `research_a_d` states it as an open preference ("nothing forces two functions") and explicitly prefers a narrow `reachability_map` that keeps the rule intact. |
| **M11** | Population mismatch real: the counter ran over 4,758 indexed records while `methods_attempted` counted 1,314. **Three independent attempts produced 674 / 671 / 667**, so the value was *derived in code* from the same population rather than copied: **671**. Assertion `dropped <= attempted` added. Bullet 3 is **not** a defect — `validation_looking = 0` is a true fact about PLR at this pin (no dropped attribute name matches HM-3's prefixes). |
| **M12** | The 1-row worklist is real and a third `dropped_receiver` view was added. But "stop describing it as the (e) worklist" over-corrects: §7.4 **already** says `top_unresolved` covers "the *recordable* frontier only" and that AC-7.4 gates on neither view. |
| **m1** | `ungroundable_reference` genuinely cannot fire in v1 — real. But "a cost §3.3 never books" is **false**: the budget is 8-of-12 with four slots explicitly reserved for deliberate additions. |
| **m3** | Under-specified, but the ambiguity is **latent, not live** — all 54 `LiquidHandler` records sit in one module, so first-match is deterministic at this pin. Uniqueness assertion taken as cheap defense in depth. |

### Rebutted — recorded so a later round does not re-raise it

| **M10** | **The research reports do not conflict.** `research_a_d`'s R6 concerns *termination*; `research_c_e`'s caveat concerns *precision*, and c_e explicitly places aliasing behind item (b) and the `SAFE` fence, **not** behind (e). The challenger's synthesis — "the product over an unbounded, symbolically-indexed location set is not finite-height" — **conflates the concrete and abstract location sets**: summarization exists precisely to bound the abstract count, so canonical abstraction over a fixed predicate set yields finitely many structures and Kleene iteration terminates. A summary node forces *weak updates*, costing precision, not termination. Operationally the objection also asks for nothing: the spec nowhere records "(d) dissolves". **No change.** |

### Known anchoring risk — carried forward to round 5, not closed here

Rounds 1–4 all adjudicated *"is the spec right about the code?"* rather than *"is the code the right
code?"* Named instances, none remediated in this round: the survey's non-`self` receiver drop
(`survey_plr_preconditions.py:214-219`) is treated as a fact of nature though it is ~10 lines in a
script we own, and an entire measurement apparatus plus deferred item (e) is built around it; §7.1's
"do not regenerate" hardened from scheduling convenience into architectural constraint;
`FAILURE_CATEGORIES` is frozen from a *dynamic* harness while §4.1 concedes four of six need static
re-interpretation; Fork C's drift test asserts mirror ⊆ upstream, structurally forbidding the mirror
from leading; `SUPPORTED_TOOLS = 10` is inherited from the execution harness's scope boundary.

**Round 5 ran as the chartered de-anchoring round (updated post-round-5).** Outcome: **0
CONCEDE-in-full at BLOCKER/MAJOR · 5 PARTIAL · 2 REBUT · 1 CONCEDE (minor)** — see
[§Remediation changelog (round 4 → round 5)](#remediation-changelog-round-4--round-5) below for the
full record. The anchoring risk named above was real in two of its four named instances and false, or
overstated, in the other two: the survey's non-`self` receiver drop **was** ~10 lines in a script this
project owns, and is now fixed (F1's additive half — `dropped_calls`, §7.1); §7.1's "do not
regenerate" **was** hardened past its original justification, and is now retitled and pinned only
after the T0 regeneration (§7.1). But `FAILURE_CATEGORIES` staying frozen is **not** anchoring bias —
F3's REBUT shows `Finding.category` costs nothing while inert-by-construction (§0 fixes every v1
verdict at UNKNOWN) and re-tightening a hinge type later costs more than declining now; and Fork C's
`mirror ⊆ upstream` direction is **not** anchoring bias either — F5's REBUT shows the alternative
(assert `consumed ⊆ upstream`, let the mirror lead) would give a plr-sema-invented field a permanent
`None` for the exact upstream-rename case the test exists to catch, and the receiver-expression content
F1/F2 wanted travels through `derive_contract`'s own unconstrained `dict.get()` payload instead, never
needing to touch `OperationNode` at all. `SUPPORTED_TOOLS = 10` staying as the analyzed surface (F4)
and the extractor's frozensets staying hand-typed rather than derived (F2) were both **partly**
inherited-constraint findings (real staleness, real provenance) with **no accompanying fitness
evidence** for the proposed alternative — declined for now, revisit after T9/T10 land (see F2/F4's
"decline" writeups in the round-5 changelog). De-anchoring is not "always widen": three of the four
named risks above held up under the probe.

---

## Remediation changelog (round 4 → round 5)

**What made round 5 different.** Round 5 was chartered as a *de-anchoring* round: rounds 1–4 all
asked "is the spec right about the code?"; round 5 asked "is the code the right code, and is the
spec's frame the right frame?" — targeting three artifacts the spec owns (the survey script, the
extractor's five frozensets, the dynamic harness's two frozensets) that had been treated as fixed
inputs across four rounds. The challenge found three real inherited-but-not-necessary constraints
(F1, F2, F6) and repeatedly slid from *provenance* ("this was inherited") to *fitness* ("therefore it
should change") without measuring fitness; the defense reproduced every factual claim this session and
adjudicated on the fitness evidence actually offered, not on provenance alone. **2 BLOCKER · 4 MAJOR ·
2 MINOR; adjudicated 0 CONCEDE-in-full at BLOCKER/MAJOR · 5 PARTIAL · 2 REBUT · 1 CONCEDE (minor).**
Full challenge and defense: `.claude/jobs/d54cd068/tmp/round5_{challenge,defense}.md` (not committed;
this changelog is the durable record).

### The defect class this round found, and its mirror image

Round 4's recurring defect was *acceptance criteria satisfiable without the property being true*.
Round 5's is the mirror image: **a metric satisfiable in either direction by construction, reported as
if it measured content.** F1's headline `7/10 → 0/10` is produced by an UNFILTERED predicate that
saturates at `0/10` because every `SUPPORTED_TOOLS` closure passes through
`LiquidHandler._check_args`'s logging/introspection calls — exactly as uninterpretable as the `7/10`
upper bound it claims to replace, only pinned in the opposite direction, and incapable of ever moving.
A high value from an unfiltered predicate and a high value from an over-narrow filter are the same
failure mode wearing different numbers.

### Conceded (fully), with what changed

| id | sev | change |
|---|---|---|
| **m1** | MINOR | §4.1's prose said "**Two** categories need explicit re-interpretation"; the table it introduces rewrites **four**. Prose corrected to "four" with the two genuinely mechanical rewrites (`shape_mismatch`, `ungroundable_reference`) named alongside the two genuinely semantic ones (`precondition_state`, `postcondition_mismatch`). |

### Partial — real defect conceded, proposed remedy narrowed or declined

| id | what stands / what does not |
|---|---|
| **F1** | **Conceded: the additive half.** `visit_Call` gains a `dropped_calls` field recording the full receiver-qualified call expression for every non-`self.<name>` Attribute receiver (9 lines, `scripts/survey_plr_preconditions.py`) — reproduced this session as strictly additive (4,770/4,770 records, 0 non-additive diffs on every pre-existing field, sole new key `dropped_calls`; `scripts/verify_survey_additivity.py`). `training/verify/data/plr_preconditions.json` regenerated (3.0 MB → 3.39 MB); `plr-sema/data/derived_contracts.json` regenerated byte-identical modulo stamp; `plr-sema/data/gap_ledger.json` regenerated with all whole-surface/`SUPPORTED_TOOLS` totals unchanged. **Declined: the interpretive half** — deleting T6's second AST pass, redefining `gaps` to include `dropped_calls`, deleting §7.4's asymmetry note, or answering RISK-1 with `0/10`. The `0/10` figure is produced by `logger.debug`/`inspect.signature`/`warnings.warn`/`args.keys` saturating every `SUPPORTED_TOOLS` closure through `_check_args`, not by tip-state guards, and the disambiguation it claims to supply was already published (`gap_ledger.json`'s `dropped_receiver_calls_by_method`, all ten entries nonzero since round-4 M11). **What round 5 DID add cheaply**: `top_unresolved.dropped_receiver` now ranks receiver-qualified names sourced from `dropped_calls`, with a stated, principled inert-receiver filter (§7.4) — real signal `self.head[channel].get_tip` now ranks first (`blocks_methods: 3`) instead of being collapsed into a bare `get_tip` row shared with five other receivers; the unfiltered ranking is published alongside it (`dropped_receiver_unfiltered`) rather than discarded. |
| **F2** | **Conceded: the staleness, and worse than stated.** Of `TIPS_REQUIRED_METHODS`' 8 entries, 3 (`blow_out`/`mix`/`touch_tip`) don't exist on `LiquidHandler` at this pin; `PLATE_MOVE_METHODS`'s `get_plate`/`put_plate` are 2/4 miscategorised too (staleness the challenge itself missed). **Declined: deriving the frozensets now.** The offered derivation is recall-only over n=5 live entries against an oracle the same finding proves is 37.5% wrong, and the derived set contains a typestate inversion: `pick_up_tips96` appears in both the derived `TIPS_REQUIRED` set and the hand-typed `TIPS_LOADING` set — its closure reaches `NoTipError` through `tip_spot.get_tip()` (the RACK must have tips), not through head-tip-presence (the HEAD must NOT have tips) — opposite typestates for exactly the methods this analysis most needs to distinguish. Hand-typing moved from the set to the derivation rule; not shipped. **Minimal fix taken instead** (praxis, not plr-sema — out of THIS spec's scope, tracked separately): delete the 3 dead names, add the genuinely-missing 96-head tip verbs, add a liveness test asserting every frozenset name resolves to a real method at the current pin. Revisit derivation after T10's differential harness exists to validate a derivation rule against, not just an oracle already proven partly wrong. |
| **F3** | **Conceded: six nulls and the doubled `unsupported_tool` are real.** **Declined: dropping `Finding.category`, moving T4 off the critical path, or unfreezing HM-5.** T4 stays on the path regardless of `by_category`'s fate — `check/__init__.py` imports `emit_finding` and emits every finding through the telemetry sink (round-4 M2), which is T4's actual live consumer; only `derive/__init__.py`'s `FAILURE_CATEGORIES` import is for the null dict, and only that half of T4's justification (the §7.4 scheduling note) is wrong and gets corrected. `category` stays required-for-`WILL_FAIL`: it costs nothing in v1 (never set, §0 fixes every verdict at UNKNOWN) and re-tightening a hinge type later costs more than declining now; HM-5 stays FROZEN. |
| **F6** | **Conceded in full: the `(module, qualname)` collision** (12 keys collide, 8 among finding-bearing records, all `@property`/`@x.setter` pairs — real, live, previously undocumented). Fixed: `build_index` documents the deterministic discard; a companion `build_unique_index` (keyed `(module, qualname, lineno)`, collision-free by construction) and `count_index_key_collisions` are added; the collision count is published in the gap ledger as `index_key_collisions`. `resolve()`'s bare-name, class-first precedence is UNCHANGED (it has no `lineno` to disambiguate a getter from its setter). **Partial — "four implementations of one predicate, four answers" rebutted**: 671/667/649 are one predicate over three named, explainable populations (records / distinct keys / the survey's own narrower in-body scanner, which is blind at `if`-test/`raise`-argument/`assert`-test positions and loses 18 methods to guard sites), not four disagreeing implementations. `674` was an earlier, unreproduced estimate superseded by `671` at round 4. **Declined**: retitling §7.1 to license unconditional regeneration (retitled instead to "regenerated by T0, pinned thereafter" — narrower), and class-qualifying `unresolved_calls` in the same change (a separate, larger, non-additive change with its own regeneration cost — `top_unresolved`'s existing 75-distinct-name/`send_command`-750 figures would all move). |
| **m2** | **Partial — the diagnosis is wrong, the remedy is right.** §6.1's `libcst`/`pylabrobot` import constraint forces only a two-way split (`extract/` vs. `check/`); `derive/` satisfies `check/`'s own constraints and the three-way split is not forced by §6.1 alone, as claimed. But the three-way split IS forced — by a constraint §6.1 had not written down: `derive/` reads PLR's source tree off disk (`rglob` + `ast.parse` under `external/`), a browser-disqualifying constraint independent of the import rule. §6.1 now states both forcing reasons (the on-disk-source constraint, and build-vs-run staging) rather than resting on the import constraint alone. |

### Rebutted — recorded so a later round does not re-raise it

| id | why |
|---|---|
| **F4** | **REBUT.** Provenance is correct (`SUPPORTED_TOOLS` is `dispatcher.py`'s mock-backend execution boundary, copied verbatim); fitness is asserted, not measured. Widening the analyzed surface in v1 changes **zero** verdicts (§0 fixes every v1 verdict at UNKNOWN regardless of surface) — only the `reason` string changes. F4's most vivid example (`PlateReader.read_absorbance`/`read_fluorescence`/`read_luminescence`) is measured on the WRONG class: the findings it cites live on `BioTekPlateReaderBackend`, which no `OperationNode.receiver_type` ever names; the front-end `PlateReader` class's three `read_*` verbs have zero findings of their own and delegate to one method with one guard — widening buys one guard. The genuinely sharp observation (`TIPS_REQUIRED_METHODS` names `return_tips`; `SUPPORTED_TOOLS` excludes it) is real but argues for adding ~7 named verbs with a written reason each, not for replacing a typed list with a rule that also admits `deserialize`/`setup`. Revisit after T10 makes the cost of a wider surface measurable. |
| **F5** | **REBUT.** The `⊆` direction (mirror fields ⊆ upstream model fields) is the correct invariant for a consumer of someone else's JSON, and F5's proposed inversion is answered by the same fact that answered round-4's M1/B5: the mirror is a consumer-derived projection of `praxis`'s schema, and a projection that leads its source acquires a field with a guaranteed `None` — the exact silent-failure mode the test exists to convert into a red one. The claimed "hard structural ceiling" does not exist: `check_graph` takes TWO payloads, and `derived_contracts.json` (plr-sema's own build artifact) is read through unconstrained `dict.get()` with no field-set constraint at all — the receiver expression F1/F2 want is produced in `derive/` at build time and travels in THAT payload; it never needs to touch `OperationNode`. |

### Known anchoring risk — status after round 5

See the updated note directly above this changelog (end of the [round-4 anchoring-risk
paragraph](#known-anchoring-risk--carried-forward-to-round-5-not-closed-here)): two of the four named
instances were genuine anchoring bias and are fixed (F1's additive survey patch, §7.1's retitling);
two survive de-anchoring on the evidence (`FAILURE_CATEGORIES` freeze, Fork C's `⊆` direction) and are
now REBUTTED rather than merely defended, closing them to re-litigation absent new evidence.
`SUPPORTED_TOOLS = 10` and the extractor's hand-typed frozensets remain genuinely inherited and
genuinely unfitted-by-measurement in places (F2's staleness, F4's `return_tips` inconsistency); both
get the cheap, bounded fix (liveness test; documented provenance) now and the larger structural change
(derivation; surface widening) deferred to when T9/T10 exist to validate against, per F2/F4's "decline"
reasoning above. No BLOCKER/MAJOR objection reordered the task graph or invalidated a shipped artifact
this round — every `SUPPORTED_TOOLS`/whole-surface figure in `gap_ledger.json` is numerically unchanged
from round 4 (verified: `totals`, `by_reason`, `supported_tools`, `dropped_receiver_calls_by_method`,
`validation_looking_dropped_receiver_calls_by_method` are byte-identical before/after round-5 T0; only
`top_unresolved.dropped_receiver`'s source changed, and two new keys — `dropped_receiver_unfiltered`,
`index_key_collisions` — were added).

---

## Remediation changelog (round 5 → round 6)

**What made round 6 different — the convergence pass.** Rounds 1–5 all hunted for defects in the
spec's *design*. Round 6 was chartered to review the document for **internal coherence and cold-start
executability** instead — "would a fixer who reads only this document, T9 or T10 in hand, produce
what §9/§8 actually require?" It found **zero design errors and zero contradictions with prior
adjudications.** Every one of its 20 findings is one of three shapes: (1) a remediation that landed in
one place but not everywhere it needed to (R3+R4+R9+R10, R6, R8), (2) a stale line citation into code
that moved (R13, plus four inside R3, plus R17/R18), or (3) a genuine gap in a not-yet-built task's
spec text (R1, R2, R5, R14, R19). No shipped test went from green to red, no AC became unsatisfiable
by the shipped code, and no prior round's adjudication was reopened. 20 objections (4 BLOCKER, 10
MAJOR, 6 MINOR); adjudicated **14 CONCEDE, 6 PARTIAL, 0 REBUT**. Post-defense severity: **1 BLOCKER ·
9 MAJOR · 10 MINOR** (downgraded: R1, R2, R4 BLOCKER → MAJOR; R12 MAJOR → MINOR; upgraded: R19 MINOR →
MAJOR). Full challenge and defense: `.claude/jobs/d54cd068/tmp/round6_{challenge,defense}.md` (not
committed; this changelog is the durable record).

### The defect class this round found, and why it clusters

**The single most important structural fact about round 6: its 4 filed BLOCKERs are 2 actual
defects.** R3+R4+R9+R10 are one propagation failure — round-4 remediation M5 (retire HM-8, add HM-22)
was applied in full in §9.4 and **nowhere else**: §4.2 kept the pre-M5 bug description in the present
tense (R3, the round's best finding — a reader would report a fixed bug as live), §9.1 kept the
pre-M5 four-member `Literal` enumeration and six-row C7 list (R10), §9.2 never gained HM-22's row
(R4), and §9.4's own shrink-target arithmetic never re-ran (R9). One remediation, four reported
defects, one edit set. Separately, R7+R16 are one off-by-one (the round-3 changelog's "AC-5.1–5.4 →
AC-5.1–5.6" arithmetic, wrong by one — D8 added exactly one AC), and R6+R8 share the same *shape* as
the M5 cluster (a changelog claiming a body edit that only half landed) from two different
remediations. R1, R2, and R5 are the only three genuinely independent findings, and all three are
T10-specific — T10 is unbuilt, so these are gaps in *specification*, not in shipped code.

### Conceded (fully), with what changed

| id | sev (filed → final) | change |
|---|---|---|
| **R3** | BLOCKER → BLOCKER | §4.2's "Live inconsistency worth surfacing now" passage described a bug T7 (`3a3a9f00`) already fixed, in the present tense, with four stale line citations, 1,300 lines above the table that already recorded it `RETIRED`. Retitled "Resolved by T7 — recorded for provenance", rewritten past tense, cites re-anchored. |
| **R4** | BLOCKER → MAJOR | T9's task row named neither HM-22 nor the `RETIRED` machinery, though every normative fact both need is already in §9.4. Row appended; not a missing decision, a missing pointer. |
| **R6** | MAJOR → MAJOR | T7's task row still said "stamped via §2.2 (C12c)" + a `SurveyStamp` test clause; the body (M4, round 4) and the shipped docstring both say the opposite. Row corrected to match the body. |
| **R7** | MAJOR → MAJOR | AC-5.6 does not exist (§5.6 defines through AC-5.5); T5's row gated "AC-5.1–5.6". The round-3 changelog's arithmetic was wrong by one. T5's row corrected to AC-5.1–5.4; AC-5.5 (Fork C's mirror test, a T8 deliverable per the shipped `test_fork_drift.py` docstring) moved to T8's gate. |
| **R8** | MAJOR → MAJOR | T3's row gated "AC-3.1–3.4"; AC-3.5 (closing the B2 T3→T8 window) exists and was never added. Row corrected to AC-3.1–3.5. |
| **R9** | MAJOR → MAJOR | §9.4's survivor-count arithmetic (D17) never re-ran after M5: omitted HM-22, double-counted `RETIRED` HM-8 against live rows, and listed HM-8 twice (once "to convert", once already `DONE`). Recomputed: 16 survivors (was 15, wrongly), "reduced from 6 to ≤2" corrected to "5 to ≤2". |
| **R10** | MAJOR → MAJOR | §9.1's dataclass `Literal` already has five members (including `RETIRED`, added by round-4 M5) but the prose still said "always exactly one of the four". Corrected to five. |
| **R13** | MAJOR → MAJOR (split MAJOR/MINOR by the defense) | Eight spot-checked line citations into `survey_plr_preconditions.py`/`failure_taxonomy.py` were all stale, shifted by round-5's T0 and T7's rewrite respectively. Applied as one anchoring pass per file (14 citations total, plus the four inside R3); the actively-misleading ones (landing on unrelated live code) and the merely-shifted ones both fixed, since §9.1's `(source_path, target_symbol)` `measure` signature means implementation survives this regardless — only *review* was at risk. |
| **R14** | MAJOR → MAJOR | Three decisions pending the user (an `UNREACHABLE` `Verdict` member; whether volume tracking is in v1; whether the `join` lattice ordering inverts) appeared in none of the document's three mechanisms for recording an open question. **Not resolved** — a new, prominent [§Open decisions](#open-decisions) section records what each blocks and that it is the user's call, per this round's instruction not to decide them. |
| **R15** | MINOR → MINOR | AC-3.1 said "All six" `test_verdict.py` tests; §3.4 names seven across six bullets; the shipped file collects eight (one bullet ships as two functions). Reworded to drop the hard-coded count, matching §8.3's existing reasoning for the 45 hand contracts. |
| **R16** | MINOR → MINOR | Same root cause as R7; fixed together (Group C). |
| **R17** | MINOR → MINOR | §7.2 attributed the `4,758` distinct-key figure to "already appeared in the spec (§7.1 measured contents)"; §7.1 publishes only the `4,770` scan count. Corrected to "first computed here". |
| **R18** | MINOR → MINOR | §3.1's illustrative `stamp.praxis.hash`/live-`HEAD` pair (`e6eda0b1…`/`28d6800f`) no longer exists on disk. Rewritten as an explicitly historical two-snapshot illustration (the round-4 pair alongside the round-6 pair, `8be56345c7e0…`/`b3608eaaa`) so the point — build-time provenance ≠ run-time provenance — cannot itself go stale again. |
| **R20** | MINOR → MINOR | T8's files column omitted `tests/test_check_graph.py` (which carries 5 of T8's ACs, including the two D15 end-to-end tests); §6.3's `test_graph_json_round_trips` does not exist under that name (shipped as `test_fixture_graph_yields_unknown_report_with_findings`); AC-6.4's shipped test is named "...subset..." but asserts equality. Files column corrected; test names corrected in §6.3's list; the naming mismatch recorded as a known discrepancy (documentation-only pass — the shipped test's assertion, not its name, is what AC-6.4 gates). |

### Partial — real defect conceded, severity or remedy narrowed

| id | sev (filed → final) | what stands / what does not |
|---|---|---|
| **R1** | BLOCKER → MAJOR | T10's `differential.py` reading `praxis/backend/core/simulation/method_contracts.py` directly would redden AC-1.2's import-boundary test — real, and the spec named none of the four resolving mechanisms. But the resolving pattern (D19: a required path flag, AST-read, never imported) already appears twice in T10's own gate command line (`--taxonomy-json`, `--survey-json`), and `derive/` already consumes a 3.4 MB `training/verify/data/` artifact this way with the boundary test green today. One sentence + a new flag, not a redesign: §8.1 now specifies `--contracts-path PATH`, AST-read via `ast.parse` + a `Call(func=Name("MethodContract"))` walk. |
| **R2** | BLOCKER → MAJOR | `tip_bearing_params(qualname)`, defined against `MethodContract`'s own `requires_tips_count`-governed parameter, has no referent — confirmed, and worse than filed: the obvious repair (`requires_on_deck`) also fails, because `pick_up_tips`'s `requires_on_deck=('tips',)` does not intersect PLR's actual `tip_spots` parameter. **No purely-derived construction exists from `MethodContract`'s own fields** — D13's premise was unachievable from that source, not merely mis-cited. A working construction that needs no new registry row does exist, routed through HM-19's already-registered `tip_state` keyword category (measured live: 4 of `LiquidHandler`'s 81 findings) — §8.1 redefines `tip_bearing_params` against the survey record's own `params` instead. |
| **R5** | MAJOR → MAJOR | The filed framing ("fixer must invent a hand-typed device→class table") is false — a two-line PascalCase transform plus D22's existing unique-module lookup resolves 29 of 45 contracts with no new registry row. But R5 concealed a worse defect: D22's fail-loud rule, applied verbatim to all 45 contracts instead of the 10 `SUPPORTED_TOOLS` it was written against, aborts the harness on 16 of 45 at the current pin (3 module-ambiguous `Pump` contracts, 13 method-absent). §8.1 now specifies both cases as `hand_only` dispositions, not errors. |
| **R11** | MAJOR → MAJOR | §7.4/RISK-1 forecast "~10/10" in the future tense where T6 had already measured and shipped 7/10 (`gap_ledger.json`'s `supported_tools.methods_with_no_recorded_gap`) — a cold reader cannot tell which is current. The forecast's *substance* is unchanged by 7 vs. 10 (both are high enough to be uninterpretable, which is the risk's whole point) — only the tense was wrong. Both mentions corrected to the measured value with its commit. |
| **R12** | MAJOR → MINOR | §1.3 said "Three tests"; `test_import_boundary.py` collects four (`test_no_verify_or_training_imports_under_src` undocumented). The count is real, but the load-bearing claim — that an undocumented test could trip up a T9/T10 fixer — does not hold: T10 loads via path flags, never imports, so there is nothing to hit; T9's `measure` values are import-path *strings*, not `ast.Import`/`ast.ImportFrom` nodes, so `_iter_imports` cannot see them either. Doc/test drift with zero consequence for the unbuilt tasks it was filed against; count corrected to four with the fourth test named. |
| **R19** | MINOR → MAJOR (escalated) | HM-17 declares `git_state.py` at 241 LOC `FROZEN`; the file is 251 lines on disk. The 10-line delta is §2.1's own mandated provenance header — the one finding in the round that turns a *correct* T9 run red, and silently: `test_frozen_surfaces_are_exact` requires exact equality, and a fixer who measures 251 will reasonably assume they counted wrong rather than that the baseline was mis-declared. §5.2 tier 1 already establishes the header-stripping convention for exactly this file's own sha256 check; HM-17's `measure` just never inherited it. Fixed by specifying the metric excludes the header, reusing `test_fork_drift.py`'s existing `parse_cherry_pick_header` to derive the boundary rather than hardcoding a second line count. |

### Rebutted

None. Every one of the 20 findings had a true factual core; the defense's disagreements were about
severity and remedy, never about the underlying fact.

### Defender's convergence judgment, and why round 7 was not run

The defense (reproduced in full at `.claude/jobs/d54cd068/tmp/round6_defense.md`) closed with an
explicit recommendation to stop, on three grounds, all adopted here:

1. **The yield curve.** Round 6's 4 filed BLOCKERs collapse to 2 actual defects (R3's cluster and R2),
   one of which is a single passage that should have been deleted and the other a single mis-cited
   field. A seventh adversarial round against a freshly-remediated document would most likely find
   stale citations introduced by round 6's own edits — precisely the failure mode this round
   diagnosed, not a new one.
2. **The defect class is mechanical, not the kind a human round finds reliably.** Fourteen stale line
   citations, an AC range off by one in two places, a `Literal` enumerated with different arity in two
   places, four task rows missing ACs their own sections define — the defense's own recommendation is
   two checkers, not a round: a citation-anchor validator (parse every `` `file:start-end` ``, assert
   the named symbol is in range) and a cross-reference lint (every `AC-N.M` appears in exactly one
   task row's gate; every `HM-N` in §9.2 appears in §9.4's arithmetic and vice versa). Neither exists
   yet; building them is future work, not this remediation.
3. **R14 is a decision gate, not a defect.** The three open decisions this round surfaced are
   correctly left unresolved — recording them is the fix; deciding them is the user's call and the
   actual gate on T10's dispatch, independent of any further adversarial round.

**Convergence, stated plainly: round 6 found zero design errors and zero contradictions with any
prior round's adjudication.** Five rounds of design review (1–5) and one round of coherence review
(6) is the full cycle this document is chartered for. Round 7 was deliberately not run. The
recommended next steps — build the two checkers named above, take a scoped read of §8.1 and T10's row
specifically (the only genuinely new spec text this remediation added), and put the three open
decisions in front of the user — are process, not further adversarial rounds, and are outside this
remediation pass's scope.

---

## T11 — whole-surface decoupling from SUPPORTED_TOOLS (spec_version 6 → 7)

**Not an adversarial round.** Unlike rounds 1–6 above, T11 is a user-directed, in-scope implementation
task (task_id `260901_plr-jit-t11-decouple-surface`), not a challenge/defense cycle — recorded here as
a changelog entry rather than a numbered "round" because there is no opposing challenge to adjudicate
against. The trigger is explicit user intent, stated directly: "this should work generally across the
PLR surface" — a fitness claim for the general-widening question that no prior round had in hand.

**F4 (round 5) raised this exact question and was rebutted — the rebuttal was sound against the
argument as made, and does not apply here.** Round 5's F4 argued for widening `plr_sema`'s analyzed
surface past `SUPPORTED_TOOLS`'s 10 methods and was **REBUT** (see "Remediation changelog (round 4 →
round 5)" above): "provenance is correct... fitness is asserted, not measured," and F4's own headline
example (`PlateReader.read_absorbance`) was measured on the wrong class, buying "one guard" for one
method. Both factual claims in that rebuttal are RECONFIRMED this session, not overturned:
`PlateReader.read_absorbance` genuinely has zero own findings and delegates to exactly one method
(`get_plate`) carrying exactly one guard — precisely what F4's rebuttal said, independently
re-measured via `derive_contract`. **What changed is not the fact, but the argument the fact sits
inside.** F4 argued from a single method's payoff ("widening buys one guard") with no stated fitness
case for paying that cost across the whole surface — the rebuttal's "fitness is asserted, not
measured" objection was correct against that argument as made. T11 does not re-litigate F4's factual
premise; it supplies the fitness argument F4's challenge lacked: (1) an explicit statement of intent
from the user, who is the one party who can actually make a fitness call for `plr_sema`'s intended
scope, and (2) at whole-surface scale (not one method), the payoff is not "one guard" — it is 580 of
3,456 zero-own-finding methods inheriting real guards through delegation, 46% of all 5,180
whole-surface guards arriving only through closure inlining, and 26 non-`LiquidHandler` families
producing real, non-degenerate contracts on inspection (RISK-1's whole-surface update, above). A
future round must not re-raise F4 as though this were unconsidered — the rebuttal stands as correct
against what was argued in round 5; T11 answers a different, better-supported argument the user
supplied this round, not the one round 5 correctly rejected.

**What changed, mechanically (see §6.2, §7.3, §9.2/HM-9, and the Risk table's RISK-1/RISK-5 updates
above for the normative text; this entry is the durable summary):**

1. `plr_sema.derive.__main__.build_derived_contracts_payload` now derives a contract for every record
   the survey indexed (4,770 at the current pin) instead of only the 10 `SUPPORTED_TOOLS` names —
   including the 3,456 zero-own-finding records, which may still inherit real guards through
   `delegates_to` (measured: 580 do).
2. A new contract-table key collision source was found and fixed: the bare-`qualname` key (what
   `check/` actually looks up) collides 26 times at whole-survey scale — a strictly larger population
   than `build_index`'s `(module, qualname)` collision count (12, §7.2's F6), because it also catches
   same-named module-level functions in different modules, a source `(module, qualname)` cannot see.
   `build_contract_keys` disambiguates via `f"{qualname}@{module}:{lineno}"` when a collision exists,
   bare `qualname` otherwise.
3. `unsupported_tool` (§3.3) is redefined: "key absent from the whole-survey contract table," not
   "outside `SUPPORTED_TOOLS`." `SUPPORTED_TOOLS` itself is unchanged and still shipped
   (`plr_sema.check.SUPPORTED_TOOLS`, `test_supported_tools_match_upstream`) — it is now purely
   `training.verify.dispatcher`'s own dynamic-execution-harness capability boundary (HM-9, §9.2), no
   longer `plr_sema`'s analyzed-surface boundary.
4. The zero-findings case (a method the survey scanned with no `PreconditionFinding`s) is decided:
   it gets a real, empty contract entry (`guards: []`, `gaps: []`), which `check/`'s existing
   zero-guards/zero-gaps/no-loop fallback (round-4 B1/B2) already turns into one `no_contract_derived`
   finding — "known and unconstrained," reusing an existing `REASON_VOCABULARY` member rather than
   adding an 8th (the closed 7-member set, cap 12, is unchanged).
5. B1's fix (§6.2: `join(())` is unconditionally `UNKNOWN`) was re-verified against the whole-surface
   artifact: `check_graph` on a zero-operation graph still returns `Verdict.UNKNOWN`.
6. `derived_contracts.json`/`gap_ledger.json` regenerated via the CLI (never hand-edited): 4,770
   contract entries (was 10), 4.4 MB pretty-printed / 3.0 MB minified / 146 KB gzipped (was 68 KB);
   `gap_ledger.json` gains one new field, `contract_table`
   (`{total_entries, distinct_bare_qualnames, disambiguated_keys}`), reporting item 2's collision
   population — every other ledger figure (`totals`, `by_reason`, `supported_tools`,
   `index_key_collisions`) is numerically unchanged, since the whole-surface/`SUPPORTED_TOOLS`-closure
   populations `build_gap_ledger` reports over were not themselves altered by T11.

**Tests changed:** `plr-sema/tests/test_derive.py` gains
`test_contract_keys_are_collision_free`/`test_whole_surface_contract_count`;
`plr-sema/tests/test_check_graph.py` gains
`test_non_liquid_handler_family_resolves_end_to_end`/`test_unsupported_tool_fires_only_for_genuinely_unknown_methods`.
No existing test asserted the pre-T11 10-contract count or `SUPPORTED_TOOLS`-gated
`unsupported_tool` behavior as a hard-coded expectation, so nothing needed to be deleted or
inverted — the nine gate files listed in T11's dispatch brief pass unmodified in structure, only
extended.

---

## T12 — three open decisions resolved (spec_version 7 → 8)

**Not an adversarial round.** Task `260901_plr-jit-resolve-three-decisions`, user-approved,
bounded-scope pass. Resolves all three [§Open decisions](#open-decisions) items left pending since
round 6 (R14). Resolution source: an independent outside analysis (Fable, `fable_three_decisions.md`,
no prior contact with the spec rounds), spot-verified against the live codebase by the orchestrator
before being accepted, then implemented by fixer.

**The unifying move, recorded as a new paragraph opening §3 (immediately before §3.1):** `Verdict` is
the *output* of evaluating one obligation against one abstract state, not the abstract domain itself.
Decisions 1 and 3 dissolve directly out of accepting that as the organizing fact rather than leaving it
implicit; decision 2 was never actually a `Verdict`-design question.

1. **`UNREACHABLE`: not added.** Reserve the wire string `"unreachable"` (comment only, unused); add
   the standing consumer rule "an unrecognized `Verdict` string deserializes to `UNKNOWN`," implemented
   as `Verdict.from_wire(value: str) -> Verdict` in `plr_sema/verdict.py`. §3.5's schema-bump direction
   corrected for the additive-enum-member case (only old readers break on new reports, not the
   reverse — see corrected §3.5 text). No `schema_version` bump.
2. **Volume: already in the verdict path; the real question (does the predicate evaluator interpret
   numeric atoms) resolves to "no, not through v1 and the first increment."** Deferred table row (d)
   updated with the evidence (proved trip counts from `items_x`×`items_y`; the `does_volume_tracking()`
   process-global gating any definite volume verdict on a `SoundnessScope`).
3. **`join` ordering: not inverted.** The shipped table is the correct join of the obligation order;
   `UNKNOWN`-as-top belongs to a separate, real information order that governs pre-emission state
   merging and has no call site in `verdict.py`. `verdict.py`'s module docstring and `join`'s own
   docstring name both orders explicitly. **`260901_plr-sema-research-a-d.md`'s R3 (group `join`'s input by
   `operation_id`, Kleene-join within the group) is recorded as must-not-implement**: v1 emits one
   `Finding` per guard (verified, `check/__init__.py::_findings_for_operation`, 9 findings for
   `aspirate`), so two findings sharing an `operation_id` are independent obligations that correctly
   conjoin; grouping and Kleene-joining would mask a definite guard failure behind a satisfied sibling
   guard — unsound in the `SAFE` direction. `test_join_absorbs_across_shared_operation_id`
   (`test_verdict.py`) pins the correct per-guard conjoining behavior; its docstring, which previously
   described the pinned case backwards (as a known-unsound stopgap rather than correct behavior), is
   corrected. Assertions unchanged.

**No `schema_version` bump; no new machinery added.** This pass is spec text (§Open decisions rewrite,
new §3 paragraph, corrected §3.5, updated Deferred row (d)) plus two `verdict.py` docstring/consumer-rule
additions plus one test-docstring correction — no change to `join`'s body, the §3.2 table, or any
`Finding`/`AnalysisReport` field.

**Re-verified:** B1 (`join(())` / `check_graph` on an empty graph returns `Verdict.UNKNOWN`, not
`SAFE`) — re-checked against this pass's `verdict.py` changes; unaffected, still holds.

**Gates (all nine, verbatim, per-file, never a bare `pytest <dir>/`):**
```
uv run pytest plr-sema/tests/test_verdict.py -q
uv run pytest plr-sema/tests/test_check_graph.py -q
uv run pytest plr-sema/tests/test_derive.py -q
uv run pytest plr-sema/tests/test_telemetry.py -q
uv run pytest plr-sema/tests/test_provenance.py -q
uv run pytest plr-sema/tests/test_fork_drift.py -q
uv run pytest plr-sema/tests/test_import_boundary.py -q
uv run pytest plr-sema/tests/test_check_graph_mirror_drift.py -q
uv run pytest training/tests/test_failure_taxonomy.py -q
```
