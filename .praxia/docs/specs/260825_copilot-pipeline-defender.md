---
title: 'Defender review: coxswain phase-2 FunctionGemma copilot pipeline spec'
description: 'DEFENDER counter-role review of 260825_coxswain-phase-2-functiongemma-copilot-p.md: steelman of D1-D10, robustness audit of load-bearing-but-fragile claims, critical-path feasibility re-verified against the tree, and resilience judgment of §8 counters. All repo cites re-verified 260825 on branch repl-fresh-boot.'
status: review
task_id: 260825_copilot_pipeline_spec
date: '260825'
---

# Defender review — phase-2 copilot pipeline draft

Role: DEFENDER (counter to a concurrent CHALLENGER). The job is to defend each decision as
hardly as possible while being maximally adversarial toward the draft's *weaknesses*: where the
spec would crumble under review, not where its choices are merely debatable. Every repo claim
below was re-verified in the working tree today; research-doc claims are cited as
`research §n`, recon claims as `recon §n`.

---

## 1. Steelman pass (D1–D10)

**D1 — Approach C hybrid staged corpus.**
Forced from three independent directions. (a) Corpus asymmetry is measured, not assumed: the
entire natural corpus is 6 runnable protocols + 16 LH-core notebooks (`recon §3/§4`, counts
re-verified today); that cannot cover a verb × ambiguity-class matrix even at 1,000-example
scale, so a synthesis floor (B) is arithmetically necessary for coverage. (b) Pure floor fails
from the other side: `research §6` establishes there is **no existing lab-automation FC dataset
on HF** (closest hit: 30 downloads), so naturalness cannot be imported, only mined or taught;
and mobile-actions (9.65k rows) anchors what a comparable single-domain fine-tune consumed.
(c) Execution verification is nearly free here — `recon §2.3` *measured* ~0.5–1 s per protocol
execution on the existing ChatterboxRunner harness (10/10 pairs, 14.2 s), which is what makes
"all execution-verified" a cheap invariant rather than an aspiration. The B-alone fallback under
time pressure is pre-recorded. Residue genuinely discretionary: the A/B mixing ratio.

**D2 — Baseline-first gate (~50 pairs before generation spend).**
The base model's OOTB numbers are mediocre-to-poor exactly where this pipeline lives (BFCL
Live-Multiple 25.7, Live-Parallel 22.9, `research §1`), and the Mobile-Actions result (58→85)
proves domain fine-tuning moves it — but *neither fact says anything about zero-shot PLR-domain
accuracy*, which is the number D2 buys for ~50 hand-written pairs. Given D3 forecloses
constrained decoding, knowing how deterministic greedy decoding already is on this surface is
load-bearing for the serving design too, not just for generation budgeting. Discretionary
residue: 50 vs 100 pairs; the gate itself is evidence-forced.

**D3 — Greedy + hardened parser + bounded retry; constrained decoding OUT.**
The most heavily evidenced decision in the doc. Constrained decoding is triply unavailable:
PR #1733 closed Aug 24 2026 in favor of #1758 which is open/unmerged with the package
unpublished on npm (`research §4`); even merged, #1758 constrains JSON, not FunctionGemma's
`<escape>`-wrapped bespoke syntax; and the documented flexible-whitespace/greedy fixed-point
trap plus 11%/token overhead are known failure/cost modes. Physics Playground ships the exact
D3 recipe (greedy + regex parse) in production today (`research §6`). Bounded-retry UX specified
up front closes the "greedy occasionally emits garbage" gap deterministically. This decision
would survive a hostile reviewer intact.

**D4 — q4f16 primary / fp16 fallback, one dtype cached per device class.**
Grounded in *fetched file sizes*, not vibes: q4f16 = 425.7 MB, fp16 = 569.9 MB, q4 = 801.1 MB
(`research §3`) — the q4-is-biggest inversion is explained by untied 262k-vocab embeddings
(flagged UNVERIFIED as an explicit statement, but the size pattern itself is primary data).
Exactly-one-dtype-cached comes straight from the eviction-gotcha mitigations list
(`research §5`): caching two dtypes doubles eviction exposure for zero benefit. The storage row
(§8) makes byte-minimization mandatory given G5 forbids CDN offload. Residue: fp16 as the
*weak-WebGPU* fallback (vs WASM/q4) is a judgment call, but it is the only fallback smaller than
q4 and shares the runtime path.

**D5 — TRL SFT full-parameter, Mobile-Actions hyperparams, venue-flexible.**
Both official Google recipes are full-parameter SFT with no PEFT anywhere (`research §2`);
LoRA demotion is forced by two documented absences: no official multi-adapter stacking story,
and Transformers.js LoRA hot-swap explicitly unverified (`scoping :149`). Hyperparams inherited
from the published 58→85% recipe (lr 1e-5 cosine, bf16, completion_only_loss) are the strongest
available transfer prior and are falsified-or-confirmed by AC-2.6 eval either way. Venue
ordering (Colab A100 default → Engaging SLURM → tuning-lab Space) matches all three documented
paths. Residue: consumer-GPU training times remain UNVERIFIED (`research §2b`) — correctly not
load-bearing since venue choice is empirical at run time.

**D6 — Native JSONL format, verbatim developer scaffold, completion-only loss.**
Not a style choice: the trigger phrase ("You are a model that can do function calling…") is
documented as the capability switch between tooling and conversation modes (`research §1`),
so byte-identical scaffolding (AC-2.5.1) is correctness, not tidiness. Assistant-supervision-as-
tool_calls and `completion_only_loss=True` mirror both the TRL formats contract and the exact
mobile-actions shape (`research §2b/§7`). Predicting only `{name, params, …}` while tier/verb
metadata stays schema-keyed (`tool_schema.py:147-150`, verified) shrinks the target space the
270M model must learn — strictly better than the scoping doc's richer prediction surface.

**D7 — Clarify as first-class class with controlled negatives.**
Directly evidence-backed twice over: FunctionGemma's pretraining explicitly includes
"request clarifications when the prompt is ambiguous or incomplete" and its BFCL Irrelevance
score (73.7) evidences a trained don't-call prior (`research §1/§7`) — i.e., the behavior exists
in the base model and a positives-only SFT distribution is the *predictable way to destroy it*
(catastrophic drift toward always-call). The multi-turn caveat cuts the same way: clarify loops
are "not explicitly trained" OOTB (`research §1`), so single-turn clarification targets must be
taught deliberately. This is the pre-mortem #2 counter and it is prevention-shaped (training
distribution), not detection-shaped.

**D8 — Three-number promotion gate.**
Each number kills one distinct failure axis: exact-match (wrong call), clarify recall (silent
guessing — the dangerous direction for a robot-adjacent tool), clarify precision ( nagging —
the adoption-killing direction). An accuracy-only gate provably passes an always-emit-tool_call
model at whatever its call accuracy happens to be; that is precisely the collapse mode D7
creates the risk of. Deferring thresholds to P2.5 baseline-measured spread rather than
inventing them now is epistemically correct. Weakness acknowledged in §2 below (R9): the
golden clarify slice may be too small to estimate precision tightly — fixable inside the DAG.

**D9 — Versioned, regenerable eval keyed to PLR_SOURCE_SHA.**
The threat is concrete: vendored PLR is a moving submodule (222 commits behind upstream per the
260817 brainstorm, wheel upgrades planned), so unkeyed eval sets rot silently. The marginal cost
is near zero because the stamping mechanism already exists in-tree — `build_wheels.py:200`
writes `PLR_SOURCE_SHA` into `_praxis_build_info.py` and `build_manifest.py:78` reads it back
(both verified today). Making regeneration a pipeline stage rather than a one-time artifact is
what converts the key from documentation into enforcement.

**D10 — Scope boundary (voice, candidate-resolution adapter, ghosting, chaining OUT).**
The chaining exclusion is not taste — the model card states trained workflows are Single-Turn
and Parallel ONLY, with multi-step/multi-turn explicitly not-trained OOTB (`research §1`).
Candidate-resolution exclusion follows: free-text clarify answers would need exactly the
unsupported multi-turn capability, and the closed-set click path needs zero NLU anyway (existing
deterministic matcher, `coxswain/src/coxswain/clarify.py`). Ghosting out matches the composition
correction (no hypothetical-render capability in visualizer-augmentations, `scoping :218`).
Voice out is locked F5. Each exclusion has a forcing fact; none is merely convenient.

**Summary:** D3, D6, D7, D10 are essentially forced by primary sources. D1, D2, D4, D5, D8, D9
are strongly evidenced with small discretionary residue (ratios, magnitudes, fallback picks)
that is honestly labeled. No decision needs reversal.

---

## 2. Robustness audit — load-bearing but fragile

Ordered by expected damage if wrong. "In-DAG?" = does the cheapest de-risk belong in an item's
ACs.

**R1. P2.9's integration shape hides an unresolved architecture decision. (top concern)**
`ParseSource.parse(self, utterance) -> ParsedCall` is a *synchronous* Python Protocol
(`parse_source.py:45-50`, verified); Transformers.js generation is async in a JS worker;
Pyodide runs sync Python on a single kernel-worker thread, so a blocking BroadcastChannel
round-trip is impossible without refactoring gate call-sites async — contradicting the seam's
own docstring promise of "additive replacement with no call-site changes". Meanwhile
`FixtureParseSource` has **zero production call sites today** (only tests instantiate it);
the actually-wired parse stub is client-side JS (`DEMO_CALLS`, `coxswain-shell.js:~52-81`).
So "swap stub at shell layer" (P2.9) is doubly ambiguous about *where parse runs after swap*:
(a) JS implementation consuming the same fixtures with dual-language parity (the house FR-3
pattern) posting envelopes, or (b) kernel-side ParseSource delegating over the channel, which
forces an async-interface refactor. Both are buildable; the ACs must pick one *before*
dispatch. Cheapest de-risk: one decision paragraph + AC-2.9.x asserting the chosen topology
with a parity test across both language implementations. In-DAG: yes, belongs in P2.9 ACs.

**R2. Tool-preamble token budget is unbudgeted anywhere.**
mobile-actions repeats its **7** tools in every row; Physics Playground serves **1**;
TOOL_SCHEMA has **21 entries** (counted today; the recon says 20 — see R11), ~18 after phantom
removal. At plausibly 150-400 tokens per rendered declaration, every training example and
every serving turn carries a multi-thousand-token developer preamble: training `max_length`
inflation (cost/time on the venue), and — worse — serving-time *prefill* cost on an iGPU
WebGPU stack. AC-2.7.3 measures decode tok/s but **not prefill latency/TTFT**, which is the
user-visible number for an interactive chat panel. Cheapest de-risk: add prefill tok/s +
TTFT-at-realistic-preamble-length to AC-2.7.3, and decide early whether MVP serves a pruned
tool subset (a schema-versioning knob P2.0 could cheaply preserve). In-DAG: yes, P2.7.3 (and
a note in P2.0).

**R3. Gemma-license/redistribution question is scheduled too late and is currently
detection-nothing.**
§8's counter defers "Gemma terms reviewed" to P2.6, and provenance tags (AC-2.3.2) are
bookkeeping, not compliance. But F3 delivers weights by fetch from **site origin** — if the
Pages deployment is public, serving a Gemma-derived fine-tune to anonymous visitors *is
redistribution* regardless of the "don't publish the model" non-goal, and the license's
acceptance/terms flow has no owner anywhere in the DAG. Teacher-generation spend starts at
P2.3/P2.4, also earlier than P2.6. Cheapest de-risk: read the Gemma terms + prohibited-use
policy once now (~30 min), decide deployment audience (private/internal Pages vs gated fetch),
and record it as a constraint F-item. In-DAG: yes — as a P2.0-adjacent scoping gate, not a
P2.6 footnote.

**R4. D9 idempotency collides with teacher nondeterminism.**
AC-2.5.3 requires idempotent regeneration keyed to `PLR_SOURCE_SHA`; but teacher NL-ification
(P2.3/P2.4) is an LLM call whose outputs vary run-to-run and across teacher-model versions.
Same sha ⇒ different corpus unless raw teacher responses are cached and treated as versioned
data. Without a content-hash cache keyed by `(prompt_version, input_hash)`, "regenerable" is
unachievable and D9 quietly degrades to aspirational. Cheapest de-risk: make the teacher-output
cache a first-class pipeline artifact with generator/prompt/teacher-model versions in the
manifest (extends AC-2.3.2's tag set with `teacher_model_version`). In-DAG: yes, P2.3/P2.5 ACs.

**R5. Receiver coverage beyond LiquidHandler is half-unverified.**
TOOL_SCHEMA spans receivers: liquid_handler (8), plate_reader (3), heater_shaker (2) plus
multiline entries (21 total, counted today). `PlateReaderChatterboxBackend` is ACTIVE in
`CHATTERBOX_REGISTRY` (`chatterbox_runner.py:140-161`) so plate-reader examples can execute-
verify; `HeaterShaker` is SCAFFOLDED/lazy-imported only — heater-shaker training examples
cannot pass P2.2 verification today without backend work, and recon's verified signature table
(recon §1.4) covers LiquidHandler exclusively. Either the verifier grows a HeaterShaker path
(hidden sub-project) or those verbs get `experimental: true` + excluded per AC-2.0.2 — the
latter shrinks the coverage matrix honestly. Cheapest de-risk: state the receiver-by-receiver
verification plan in P2.0's ACs. In-DAG: yes, P2.0/P2.2.

**R6. transformers.js runtime sourcing under G5 is unaddressed.**
F3 covers *model artifacts*; the @huggingface/transformers library itself must also reach dist
offline, and web-repl has no package.json/bundler — a jsDelivr import like Physics Playground's
would fail the G5 grep (`build_repl.py:50-73`). House precedent resolves it: tracked vendored
libs + manifest (visualizer vendors `gif.js` etc. with `VENDOR_MANIFEST.json`, verified via
git ls-files). Cheapest de-risk: one sentence in F3 + an AC-2.8.x asserting the vendored lib
passes the same G5/integrity gates. In-DAG: yes, P2.8.

**R7. Baseline-eval access friction (HF gated repo) can hollow out the D2 gate.**
AC-2.1.2's "recorded-artifact mode" fallback means CI never re-runs the real checkpoint — the
gate then detects nothing fresh and silently rots as the base repo updates. Also gating: Colab/
CI needs an accepted-terms token. Cheapest de-risk: pin the base revision alongside recorded
outputs, and add a non-CI local-inference lane (CPU is fine for 270M × 50 pairs) exercised at
least once per phase. In-DAG: yes, P2.1 AC wording.

**R8. Web facts with short shelf-life.**
#1758 merge state (open as of 260825), transformers.js version surface (v4.2 current), HF file
sizes, notebook-deprecation moves — all volatile, all load-bearing for D3/D4/P2.7. Cheapest
de-risk: pin `@huggingface/transformers` to an exact version in-tree when P2.8 lands; re-check
#1758 status at P2.8 dispatch (one webfetch). In-DAG: yes, P2.8.

**R9. Clarify metrics rest on a tiny sample.**
≥8 golden clarify examples (AC-2.1.1) yields enormous confidence intervals on precision — D8's
dual gate could pass/fail on noise at exactly the decision it exists to settle. Cheapest
de-risk: require ≥30 held-out clarify examples spanning the three classes and report Wilson
intervals beside point estimates in AC-2.6.2. In-DAG: yes, P2.1/P2.5 split sizing.

**R10. Target-hardware class and browser matrix are undefined while dev hardware is the
hardest case.**
This machine is Linux + AMD 890M iGPU — historically the *weakest* WebGPU stack (Safari<26 is
known-out per `research §5`, but Linux/Dawn+iGPU maturity is the real risk here). AC-2.7.3's
"go/no-go on q4f16 vs fp16" is underdetermined without naming the matrix. Cheapest de-risk:
define minimum browser×OS matrix at P2.7 start; measure on the actual dev machine first since
it is the pessimistic bound. In-DAG: yes, P2.7.3.

**R11. Small cite-drift inventory (none load-bearing alone, worth re-stamping at P2.0):**
TOOL_SCHEMA has 21 `_spec(` entries, not 20 (recon §1.3); shell has 16 modules + 17 tests
(recon/spec say 17 modules); the demo stub's own comment claims to mirror "three" golden
entries but contains two regexes (`coxswain-shell.js:52-81`); the submodule working tree
carries dirty paths (deleted tool files, untracked uv.lock) which `build_wheels.py:176-183`
warns about and excludes from wheels — harmless, but P2.0's sha-pinning should assert
cleanliness or use the pinned-commit derivation (which build_wheels already prefers).

---

## 3. Critical-path feasibility (P2.0 → P2.1 → P2.5 → P2.6 → P2.7 → P2.8 → P2.9), verified against the tree

| Item | Seams verified today | Verdict |
|---|---|---|
| **P2.0** | Phantom verbs confirmed both ways: schema declares mix/blow_out/touch_tip/dispense_to_waste (`tool_schema.py`, read today); grep finds no such defs on vendored LiquidHandler. Generator seam ~90% present: `introspection.inspect_machine_methods(fqn)` with pylabrobot allow-list (`services/introspection.py:19-45`). Sha pinning mechanism real (`build_wheels.py:200`, `build_manifest.py:78`). | STARTABLE now. Hidden sub-project: inspect→JSON type-mapping layer (recon GAP #2 concedes it isn't free) and multi-receiver scope (R5). Needs a canonical "current sha" accessor that doesn't require a full wheel build (trivial: `git -C external/pylabrobot rev-parse HEAD`, but say so). |
| **P2.1** | Golden fixture corpus exists at `coxswain/tests/fixtures/parsed_calls/` (6 files, listed today); its shape is a stable contract; FR-3 dual-language parity harness already glues implementations to it (`test_phrase_parity.py`). | STARTABLE after P2.0. CPU local inference of a 270M model for 50 pairs is comfortably <2 min; R7 is the only real friction. |
| **P2.5** | Assembly is mechanical given P2.1-P2.4 outputs; GO/NO-GO is a human step with a defined artifact. | FEASIBLE with R4 fixed — otherwise its idempotency AC is unsatisfiable as written. |
| **P2.6** | Recipe is fully documented with pinned deps (`research §2b`: transformers==4.57.1, trl==0.25.1); venue options all documented. | RECIPE-REAL, venue risk external (probe Colab/SLURM availability at P2.5 time, not mid-P2.6). Watch R2 length inflation on max_length. |
| **P2.7** | Delivery patterns proven in-tree: `fetch_pyodide.py`/`fetch_vendored_wheels.py` exist; wheels array shape `{package, filename, source_sha, sha256, bytes}` at `build_manifest.py:17,168-182`; zero-tracked-binaries rule enforced. Export path is the genuine spike (optimum-onnx post-v4 restructure UNVERIFIED per `research §3`). | SPIKE, honestly labeled. Add TTFT/prefill, Cache-retention-across-browsers, and browser matrix to AC-2.7.3 (R2/R10). |
| **P2.8** | Mount point real: `overlay/assets/coxswain/` exists (css + viz_highlight.js today), flag-gated staging verified (`stage_overlay`, `build_repl.py:551-578`); `assertValidEnvelope` real (`envelope.js:99`); envelope kinds/foreign-session drop pattern established in shell. | STARTABLE after P2.7. R6 (library sourcing) is the one unbudgeted dependency. Parser grammar complexity is bounded and specified (escape round-trip, ≤2 retries, structured failure payload). |
| **P2.9** | Seam real: `ParseSource` Protocol + `FixtureParseSource` verified; ParsedCall/UnresolvedSlot types flow into GatePassContext (`fft/context.py:120-136`); kernel guards exist (`execute.py`). BUT zero production call sites today and the sync/async fork (R1) is undecided. AC-2.9.4's conditional kernel-grounding bridge (recon GAP #6) is honestly scoped with an escape hatch. | SEAM REAL, ITEM UNDERDETERMINED. Not blocked, but "done" as written hides the R1 topology decision; resolve before dispatch. |

Net: **no item is blocked**; the path is real end-to-end. Two items carry hidden decisions that
should be promoted into ACs (P2.0 partially via R5; P2.9 substantially via R1), and P2.5/P2.7
each have one AC that is unsatisfiable-or-incomplete as literally written (R4, R2).

---

## 4. Resilience of §8 counters — prevent vs detect-late

1. **Silent eval rotation ← D9 sha keying.** Keying alone *detects* drift only at
   regeneration time; nothing asserts the key continuously. Harden: CI assertion that
   manifest `PLR_SOURCE_SHA` == current submodule HEAD whenever eval-consuming items change,
   plus the R4 cache so "same sha" actually implies "same corpus". Currently
   detect-at-best; one test away from prevent.
2. **Clarify collapse ← D7 ratio + D8 dual gate.** D7 is genuine *prevention* (it shapes the
   training distribution; preserving the documented Irrelevance prior). D8 is *promote-time
   detection*, correctly placed before any serving ship, but noise-limited by sample size
   (R9). Keep both; enlarge the clarify eval slice. AC-2.6.3's zero-tool_call-on-out-of-surface
   check adds a crisp behavioral tripwire — good.
3. **Serving reality gap ← P2.7.3 footprint go/no-go.** Detection-by-measurement, placed
   early enough to redirect (dtype swap, subset, descope) — acceptable placement, incomplete
   metric set (no prefill/TTFT, no browser matrix, no Cache-retention test; R2/R10).
4. **ONNX export friction ← smoke-parity + -GQA precedent.** The precedent transfers well
   because our fine-tune changes weights, not architecture — arch-level convertibility is
   exactly what the community export demonstrates. Smoke-parity inside the spike = early
   detection with a redirect path. Sound as written.
5. **Teacher licensing/provenance ← tags + P2.6 review.** Tags are bookkeeping (neither
   prevent nor timely detect); the review is scheduled *after* teacher spend begins (P2.3/4)
   and ignores the public-serving question (R3). Move the terms reading forward and resolve
   deployment-audience policy at scoping level. Currently the weakest row in the table.
6. **Storage budget ← single-dtype + prune re-check + G5.** Policy (prevention) plus a
   detection checkpoint at P2.7; arithmetic is honest (~905 MB of 1 GB) but leaves ~120 MB
   headroom for everything phase-3+ wants to exist. Record a running budget ledger at each
   delivery-touching item so the squeeze is visible before it bites.

---

## 5. Verdict

The draft is unusually well-grounded: its decisions overwhelmingly trace to primary-source
facts or verified code seams, and the corrected ground truth (§4) spares implementers the
tombstone traps (ChatterBoxBackend, fixture locations, notebook counts) that killed earlier
iterations of plans like these. Recommended before DAG dispatch, in priority order:

1. Resolve the P2.9 parse-topology decision (client-side JS impl + dual-language parity vs
   async kernel-side bridge) and write it into AC-2.9.x (R1).
2. Extend AC-2.7.3 to measure prefill/TTFT at realistic preamble length and define the
   browser/hardware matrix; consider an MVP tool-subset knob from P2.0 (R2/R10).
3. Pull the Gemma-terms/deployment-audience decision forward to scoping level and add the
   teacher-output content cache + `teacher_model_version` to the manifest ACs (R3/R4).
4. Fold the smaller hardenings (R5 receiver plan, R6 library-vendoring AC, R7 baseline
   freshness lane, R9 clarify slice ≥30, R11 cite re-stamp) into the named items' ACs.
