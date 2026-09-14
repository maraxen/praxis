---
title: 'Coxswain Phase 2: FunctionGemma copilot pipeline'
description: 'Spec for the synthetic-data pipeline, functiongemma-270m-it fine-tune, browser serving via Transformers.js/WebGPU behind --with-coxswain, and ParseSource integration. REV 2: reconciled from challenger (2 blockers, 7 majors, 8 minors) and defender (11 robustness findings) reviews of 260825.'
status: draft-rev2
task_id: 260825_copilot_pipeline_spec
date: '260825'
---

# Coxswain Phase 2 — FunctionGemma copilot pipeline (rev 2)

Revision log: rev1 authored from contemplex session 70ae4959 + recon + research. rev2 adopts all
challenger blockers/majors (C-B1, C-B2, C-M1..C-M7, minors m1-m8) and all defender robustness
findings (R1-R11). Reviews preserved at `.praxia/docs/specs/260825_copilot-pipeline-{challenger,
defender}.md`. Changes are marked **[rev2]** inline.

## 1. Problem and goal

Coxswain's deterministic substrate shipped complete (W0–W6, backlog 4388–4395). The parse layer is
a fixture-backed stub (`FixtureParseSource`) plus a client-side demo regex stub
(`coxswain-shell.js`). This spec covers replacing those with a real model: execution-verified
training data, `google/functiongemma-270m-it` fine-tune, browser serving, integration through the
`ParseSource` seam — decomposed into a backlog DAG where every item dispatches without further
design ambiguity.

Bound inputs (do not re-litigate): scoping `260824_gemma-finetuned-plr-voice-text-copilot-scoping.md`;
recon `260825_copilot-pipeline-recon.md`; research `260825_functiongemma-training-serving-research.md`;
contemplex session `70ae4959`; MVP spec `260824_coxswain-mvp-ux-spec.md`.

## 2. Decisions locked

| # | Decision | Basis |
|---|----------|-------|
| D1 | Data strategy = Approach C hybrid staged corpus (schema-driven floor + naturalness overlay), all execution-verified; B-alone is the fallback | session winner; defender steelman §1 |
| D2 | Baseline-first gate: off-the-shelf accuracy on golden set measured BEFORE generation spend; golden-50 stays human-reviewed regardless of teacher | D absorbed; F6 amendment |
| D3 | Serving = greedy decode (`do_sample:false`) + hardened parser for FunctionGemma native `<start_function_call>` syntax + schema validation + bounded retry (≤2). Constrained decoding OUT (PR #1758 open/unmerged, package unpublished, targets JSON not the escape-syntax) | research §4; Physics Playground precedent |
| D4 | **[rev2]** Exactly ONE dtype ships globally, chosen at P2.7a go/no-go (q4f16 ~426 MB expected primary; fp16 only if q4f16 fails footprint/quality gates). Unsupported-device degrade is a LOUD SYSTEM LINE, not a second shipped artifact (two dtypes ≈ 1.48 GB > Pages 1 GB limit) | C-M5 fix; recon §7 budget math |
| D5 | TRL SFTTrainer FULL-parameter (no LoRA at 270M), Mobile-Actions hyperparams (lr 1e-5 cosine, bf16, completion_only_loss=True), deps pinned `transformers==4.57.1 trl==0.25.1`; venue empirical at run time (Colab A100 default → Engaging SLURM via myxcel → functiongemma-tuning-lab Space) | research §2 |
| D6 | Dataset format = FunctionGemma-native JSONL `{metadata, tools[], messages[]}`; developer-role scaffold committed as an exact template in P2.5 **[rev2: dates/timestamp injection OMITTED — stated explicitly]**; assistant supervision as tool_calls; completion_only_loss | research §2; C-m3 fix |
| D7 | Clarify supervision first-class: negatives mixed at controlled ratio. **[rev2] Supervision shape: out-of-surface utterances supervise an NL clarification turn (no tool_call); incomplete-slot utterances supervise a tool_call with `missing_required` derivable deterministically — see D11 — NOT free-text slot naming** | research §7; C-B1 fix |
| D8 | Promotion gates THREE-number: exact-match accuracy, clarify recall, clarify precision. **[rev2]** Eval split sized for the decision: ≥30 held-out clarify examples spanning all three classes; Wilson intervals reported beside point estimates; ONE threshold revision permitted at P2.6 with recorded justification (P2.5 numbers are provisional anchors, not final) | C-M6 + R9 fixes |
| D9 | Eval set versioned + regenerable keyed to `PLR_SOURCE_SHA`; **[rev2]** golden-provenance pairs EXEMPT (human-authored, re-not-regenerated); teacher outputs cached content-addressed `(prompt_version, input_hash)` with `teacher_model_version` in manifest — same sha ⇒ same corpus | C-m1 + R4 fixes |
| D10 | Out of scope: voice, candidate-resolution adapter, ghost rendering, multi-step chaining, production-mode backend, LoRA family, public dataset/model publishing | session frame; model card single-turn-only fact |
| **D11** | **[rev2] Prediction target = `{name, params}` ONLY.** `missing_required` and `unresolved_slots` are derived DETERMINISTICALLY post-parse from the P2.0 canonical tables (required-set per verb; slot-classification rule over string-valued resource-typed args). Rationale: FunctionGemma's native call syntax cannot express these fields (C-B1); deriving keeps them out of model hands AND makes them trustworthy for cue 1/cue 2. Clarify-expected training examples = utterances whose supervision target is deliberately NO tool_call or an incomplete tool_call, teaching abstention — the fields themselves stay deterministic | C-B1 fix, option (b) |
| **D12** | **[rev2] Parse topology (MVP) = CLIENT-SIDE JS implementation** consuming the same fixture corpus, dual-language FR-3 parity tests against the kernel-side `ParseSource` contract (house pattern from W3). The sync Python Protocol ↔ async JS worker mismatch (defender R1) is resolved by NOT bridging: the kernel-side `ParseSource` remains the contract/spec surface + test harness; production parsing happens in the JS layer where async lives naturally. Kernel-side delegation is a documented non-goal for phase 2 | defender R1 top concern |
| **D13** | **[rev2] Gemma license & deployment-audience gate runs at P2.0 time** (before any teacher spend): read terms + prohibited-use policy once; decide deployment audience (private/internal Pages vs gated fetch); record as constraint. Public anonymous serving of a Gemma derivative IS redistribution — decided early, not at P2.6 | defender R3 |

## 3. Fixed constraints (inherited)

1. **F1 Safety**: FFT gate unchanged, model-free; candidate parses only; zero new kernel authority.
   **[rev2 strengthening per C-M1]** Kernel-side validation that every resource-typed arg either
   resolves against live state or exits `clarify:*` is MANDATORY before propose; the worker's
   slot/unresolved reporting is ADVISORY ONLY (under-prediction cannot bypass cue 2).
2. **F2 Import boundary**: `coxswain/` never imports `praxis.backend.*`; `training/` (new uv
   workspace member) may, in CPython context only. **[rev2]** AST boundary test also asserts
   `coxswain/` never imports `training/`, overlay/staged python never sees `training/`, and browser
   bundles never contain it (C-m5).
3. **F3 Delivery**: model binaries never git-tracked; fetched to gitignored `web-repl/vendor/models/`
   via fetch script; NEW `models` manifest array (wheels-shaped: name/filename/source_sha/sha256/
   bytes); G5 forbids CDN at runtime; lazy fetch from site origin on first chat interaction.
   **[rev2]** The @huggingface/transformers LIBRARY ITSELF is vendored origin-local the same way as
   visualizer's gif.js (tracked vendored lib + VENDOR_MANIFEST treatment), pinned to an exact
   version — a jsDelivr import would fail the G5 grep (C-M4.1/R6).
4. **F4 Worker**: own module Web Worker under `overlay/assets/coxswain/`; progress as system lines;
   Cache API persistence + `navigator.storage.persist()` after first download.
   **[rev2]** Lifecycle fixed in one place (C-m4): session_id/turn_id passed via worker init message;
   main thread owns `seq` allocation; envelopes wrapped on MAIN thread through
   `assertValidEnvelope` (worker emits raw results); decode config = stop tokens
   [`<end_of_turn>`, `<start_function_response>`], max_new_tokens 128, greedy.
5. **F5 Text-first**; voice push-to-talk later.
6. **F6 Teacher backends (amended 260825, user-directed; amended again 260827)**: ox-alpha via
   spawned jcode workers (ambiguity-injection, golden authoring) + titanix-vllm-primary localhost
   vLLM (verified live; smoke-scale mechanical passes only as of 260827) + **Gemini 3.7 Flash
   (`gemini-3.7-flash-medium`, shelled via the local `agy` CLI -- no API key, agy owns its own
   auth), the full-scale-pass teacher (260827)** after titanix-vllm-primary was flagged as not
   viable at that scale; golden-50 human-reviewed always. Non-Gemma model -- D13's
   teacher-derivative gate does not apply. Implemented in `floor_gen.teachers.GeminiTeacher`
   (batched per user direction; real-verified) / `overlay_gen.pair_builder.GeminiTeacherClient`
   (not yet batched), both using `agy --json-schema` guided decoding to enforce the exact response
   contract at decode time
   (see `.praxia/docs/decisions/260827_teacher-backend-gemini-3-7-flash-for-full-scale-floor_gen-overlay_gen-pass.md`
   for the full design + coverage/brittleness analysis).

## 4. Corrected ground truth (implementer must honor)

Unchanged from rev1 (recon-verified): tombstone backend name (`LiquidHandlerChatterboxBackend`, not
`ChatterBoxBackend`); runnable corpus = `praxis/protocol/protocols/` (6 protocols); 58 notebooks
(16 LH-core); fixture location `coxswain/tests/fixtures/parsed_calls/` (6 files, all clean-parse —
hard-case fixtures added by P2.9 per C-m6); TOOL_SCHEMA drift (phantom verbs) drives P2.0.
**[rev2 additions]** TOOL_SCHEMA has **21** entries (not 20); shell has 16 modules + 17 test files;
demo stub mirrors two golden entries by regex (its comment says three) — re-stamped here per R11.
**Param-name vocabularies (C-B2)**: fixtures use normalized names (`source`/`volume_ul`/
`destination`/`wavelength_nm`) ≠ PLR signatures (`resources`/`vols`/`targets`) and NO dispatcher
exists today (`execute.py:163` takes abstract executor). P2.0 owns the canonical mapping table;
everything downstream consumes it.

## 5. Work items — the DAG

| ID | Item | Depends on |
|----|------|-----------|
| P2.0 | Schema reconciliation: signature sweep vs TOOL_SCHEMA pinned to submodule HEAD; phantom removal/exclusion; **include/exclude list as recorded product decision** (96-channel, tip-return families excluded unless promoted); receiver-by-receiver verification plan (HeaterShaker = experimental/excluded until backend exists); **canonical param namespace + (schema name ↔ PLR kwarg) mapping table + symbolic-slot classification rule + required/type tables** (feeds D11, C-B2); intent-record shape definition (C-M3); **Gemma license + deployment-audience gate (D13)** | — |
| P2.1 | Golden set + baseline harness. Pair count DERIVES from reconciled verb count (≥2 per included verb + ≥30 clarify examples spanning 3 classes — R9 sizing); harness reports 3 metrics + Wilson intervals; **local CPU inference lane exercised in-phase** (270M × N pairs is minutes) + base-revision pin beside any recorded outputs (R7) | P2.0 |
| P2.2 | Execution-verify harness: chatterbox_runner-based, STRICT mode, tracker post-conditions, intent-record slot-agreement axis (**intent record defined in P2.0** — dependency added per C-M3) | P2.0 |
| P2.3 | Coverage-floor generator: verb × ambiguity matrix → structured calls → teacher NL-ification; **teacher-output content-hash cache** (R4) | P2.0 |
| P2.4 | Naturalness overlay: notebooks + runnable protocols → verified calls → teacher pairs; dedupe | P2.0 |
| P2.5 | Assembly + slice gate: ~1000-example stratified split; **exact scaffold template committed (no date injection)**; thresholds PROVISIONAL; GO/NO-GO comparing baseline failure distribution vs coverage plan; **storage-budget ledger started** (C-m8) | P2.1, P2.2, P2.3, P2.4 |
| P2.6 | Fine-tune run (D5 recipe); eval report w/ intervals; promotion per D8 (one threshold revision allowed, justified); clarify tripwire (zero tool_call on out-of-surface) | P2.5 |
| **P2.7a** | **Delivery plumbing + footprint spike — runs EARLY, parallel off P2.0/P2.1 (C-M7)**: optimum ONNX export path proven on the COMMUNITY functiongemma ONNX export (checkpoint-independent); transformers.js runtime vendoring + G5 compliance; `fetch_models.py` + `models` manifest array; first-use integrity check; footprint doc incl. **prefill TTFT at realistic preamble length (21-tool preamble is multi-thousand tokens — R2)**, decode tok/s, Cache-retention across reloads, browser×OS matrix (dev machine = pessimistic bound, R10); single-dtype global choice (D4); running storage ledger | P2.0 |
| **P2.7b** | Fine-tuned-checkpoint export parity: token-level greedy equality on 20 fixed utterances (C-m7 — deviations are go/no-go signals, not "semantic equivalence") | P2.6, P2.7a |
| P2.8 | Serving worker: lazy module worker; lifecycle per F4; hardened grammar parser; schema validation + bounded retry → **vocabulary amendment owned here: `clarify:parse_failed` disposition added to audit-writer allowlist + envelope kinds enumerated + audit semantics of failed parses specified (C-M2)**; transformers.js version pinned exact (R8); re-check #1758 status at dispatch | P2.7a |
| P2.9 | Integration: **client-side JS ParseSource implementation (D12)** consuming fixture corpus + model; dual-language FR-3 parity; **mandatory kernel-side resource-arg validation before propose (C-M1)**; **fixture corpus extended with hard cases** (missing_required, unresolved_slots, refusal — C-m6); demo stub deleted; end-to-end audit trail check | P2.7b, P2.8 |

Critical path: P2.0 → {P2.1 → P2.5 → P2.6} ∥ P2.2 ∥ {P2.3, P2.4} ; P2.7a ∥ (P2.1..P2.6) after P2.0;
then P2.7b, P2.8 → P2.9. The C-M7 fix moves serving-feasibility evidence months earlier: P2.7a can
conclude while generation/fine-tune still run.

## 6. Non-goals

Voice input; candidate-resolution adapter; ghost rendering; multi-step chained calls;
production-mode `WorkcellRuntime` backend; LoRA family; public dataset/model publishing;
kernel-side parse delegation (D12); constrained decoding (D3).

## 7. Acceptance criteria

Changes from rev1 marked. Unlisted rev1 ACs carry over unchanged except where superseded:

- **AC-2.0.x (extended)**: subset assertion TOOL_SCHEMA ⊆ vendored API pinned to submodule HEAD;
  phantom entries removed or `experimental:true`+excluded; required-param derivation matches
  inspect.signature (recon §1.4 table); **NEW: canonical namespace + mapping table committed as
  data (every fixture param name maps to a PLR kwarg or is declared symbolic); include/exclude list
  recorded; receiver verification plan (LiquidHandler+PlateReader verifiable today; HeaterShaker
  excluded); intent-record shape defined; D13 gate artifact (terms read, audience decided)**.
- **AC-2.1.x**: count derives from reconciled verbs; ≥30 clarify examples (3 classes); harness
  metrics + Wilson intervals; **local CPU lane run recorded; base revision pinned**.
- **AC-2.2.x**: as rev1 + verifier keyed to P2.0's intent-record/effect tables.
- **AC-2.3/2.4.x**: as rev1 + **teacher-output cache present; `teacher_model_version` +
  `prompt_version` in provenance tags**.
- **AC-2.5.x**: as rev1 + **scaffold template committed verbatim (dates omitted)**; thresholds
  labeled provisional; **storage ledger initialized**.
- **AC-2.6.x**: as rev1 + **Wilson intervals; at most one threshold revision w/ justification;
  tripwire unchanged**.
- **AC-2.7a.x (new)**: community-checkpoint ONNX→q4f16 smoke; vendored runtime passes G5 grep +
  integrity; models array lands; footprint doc covers download bytes, peak memory beside live
  Pyodide, prefill TTFT @ realistic preamble, decode tok/s, Cache retention, browser matrix;
  dtype choice recorded; ledger updated.
- **AC-2.7b.x (new)**: fine-tuned export; token-level greedy parity on 20 utterances vs Python-side.
- **AC-2.8.x**: as rev1 + **disposition-vocabulary amendment landed with audit-writer tests; worker
  transport/lifecycle per F4 exactly; transformers.js pinned exact; #1758 status re-checked and
  recorded at dispatch; vendored-lib G5/integrity assertion**.
- **AC-2.9.x**: as rev1, with **topology per D12 asserted (JS impl + dual-language parity);
  kernel-side resource-arg validation MANDATORY pre-propose (advisory worker slots cannot satisfy
  cue 2 alone); fixture corpus gains ≥3 hard-case fixtures (missing_required / unresolved_slots /
  refusal paths through the full gate)**; demo stub deleted; E2E audit-trail check unchanged.

## 8. Risks (updated)

| Risk | Counter | Prevent/Detect |
|------|---------|----------------|
| Silent eval rotation | D9 sha keying + **CI assertion manifest sha == submodule HEAD when eval-consuming files change (defender §4.1 hardening)** + teacher cache | prevent |
| Clarify collapse | D7 distribution shaping + D8 dual gates w/ ≥30-example slices + intervals + AC-2.6.3 tripwire | prevent + promote-time detect |
| Serving reality gap | P2.7a moved EARLY (parallel branch); TTFT/prefill + browser matrix + Cache retention measured; D4 single dtype; D3 retry UX pre-specified | early detect w/ redirect |
| ONNX export friction | -GQA precedent transfers (arch unchanged by FT); P2.7a proves path pre-spend; P2.7b parity gates | early detect |
| Gemma license/redistribution | D13 gate AT P2.0 (pre-spend); audience decision recorded as constraint | prevent |
| Storage squeeze (~479 site + 426 model + runtime bundles) | D4 single dtype; ledger at every delivery-touching item; prune re-check | detect early |
| Teacher nondeterminism breaks idempotency | R4 content-hash cache + versions in manifest | prevent |
| Under-predicted slots reach confirm | C-M1 fix: kernel-side validation mandatory; worker slots advisory | prevent |

## 9. Open questions (resolved or deferred with owner)

- Thresholds T_acc/T_clr_recall/T_clr_prec: provisional at P2.5.4, final at P2.6 w/ ≤1 revision (D8).
- Training venue: empirical at P2.6 run time (D5).
- Cue-2/3 in-tab grounding bridge: SUPERSEDED by C-M1 mandate — kernel-side resource-arg validation
  before propose is REQUIRED (was conditional in rev1); whether full grounding moves in-tab or the
  validation uses serialized-state summaries is a P2.9 implementation choice within the mandate.
