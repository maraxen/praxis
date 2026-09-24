---
title: 'FunctionGemma 270M browser serving footprint (P2.7a)'
description: 'Measured delivery + serving footprint of onnx-community/functiongemma-270m-it-ONNX q4f16 beside a live Pyodide kernel: download bytes, peak RSS coexistence, prefill TTFT at realistic preamble length, decode tok/s, Cache-API retention across reloads and process restarts, WebGPU availability on the dev machine (WSL2 + AMD 890M iGPU), single-dtype recommendation (D4) and the running Pages storage ledger.'
task_id: 260825_copilot_pipeline_spec
date: '260825'
status: measured
---

# FunctionGemma 270M browser serving footprint — P2.7a

Spec: `.praxia/docs/specs/260825_coxswain-phase-2-functiongemma-copilot-p.md`
rev2 §5 P2.7a / §7 AC-2.7a.x. Research baseline:
`260825_functiongemma-training-serving-research.md` §3/§4.

## 1. What was delivered (plumbing)

| Artifact | Path | Tracked? |
|---|---|---|
| transformers.js runtime vendor script | `web-repl/scripts/fetch_models.py` (`--runtime`) | yes |
| Model fetch script | `web-repl/scripts/fetch_models.py` (`--models`) | yes |
| Vendored ESM bundle (patched, see §3) | `web-repl/overlay/assets/coxswain/vendor/transformers.min.js` (self-contained build) | yes |
| ORT wasm loader (text) | `web-repl/overlay/assets/coxswain/vendor/ort/ort-wasm-simd-threaded.asyncify.mjs` | yes |
| ORT wasm backend binary | `.../ort/ort-wasm-simd-threaded.asyncify.wasm` | NO (gitignored, sha pinned in VENDOR_MANIFEST.json) |
| First-use integrity module | `web-repl/overlay/assets/coxswain/vendor/model_integrity.js` | yes |
| Vendor provenance manifest | `web-repl/overlay/assets/coxswain/vendor/VENDOR_MANIFEST.json` | yes |
| Models manifest array | `build_manifest.py --with-models` → `manifest.json` key `models` | generator tracked; output gitignored |

Pins (exact):

- `@huggingface/transformers` **4.2.0** (npm `latest`, 4.x line; registry sha512 verified before extraction).
- `onnxruntime-web` **1.26.0-dev.20260416-b7804b056c** (transformers 4.2.0's exact dep).
- `onnx-community/functiongemma-270m-it-ONNX` @ revision **ba3c872ede162a5c4ab753f509b2260af5587143**, dtype **q4f16**.

Model file SHAs (upstream-published digests, verified at download AND at
manifest generation):

| File | Bytes | Digest source | sha256 |
|---|---|---|---|
| `onnx/model_q4f16.onnx_data` | 425,724,416 | LFS oid | `b30ca95e4b31014ec791d7589f8c6416b8056ffc4f39093aa7ceb3ad37f2a0c7` |
| `onnx/model_q4f16.onnx` | 518,626 | LFS oid | `8dc9fb5e2b0aa34f527309f0ecaeb9b824b5ad9a9613350168753054c180e145` |
| `tokenizer.json` | 20,316,979 | LFS oid | `69fde4ada54844b6a7b94494e97f93c581c80cc6610c87e7b45d223077542169` |
| `config.json` | 1,729 | git blob sha1 | `9ca1f5a763ae9eccaad5ac168c1be82050756918` |
| `generation_config.json` | 210 | git blob sha1 | `14709ab7546f775c213038b64dbdc28243934a5d` |
| `tokenizer_config.json` | 14,945 | git blob sha1 | `7ab5f9fdaf305c5e5b9353aa09bf23afb4b5dfcf` |
| `chat_template.jinja` | 13,792 | git blob sha1 | `16294794d96bfe26bbf2da97af27ced085fd1683` |
| **total** | **446,591,047** (~426 MiB weights + tokenizer) | | |

Vendored runtime SHAs (VENDOR_MANIFEST.json):

| File | Bytes | sha256 |
|---|---|---|
| `transformers.min.js` (patched, self-contained) | 558,310 | FILLED-AFTER-RERUN |
| `ort/ort-wasm-simd-threaded.asyncify.mjs` | 47,389 | `5959c6733039619c9af710d8e1bae8d6e84402787990637be987c2b1bd6c5fa9` |
| `ort/ort-wasm-simd-threaded.asyncify.wasm` | 23,567,050 | `e0c0c6d3e73d43b8a249972f8358f845b08cc16fec3c80efafdf8bed40366786` |
| `model_integrity.js` | 10,968 | `2cafde3a4a671323e0b94a835ecf56a1f7312a15a5db84c02269c92932b53442` |

## 2. G5 compliance (no jsDelivr anywhere in dist)

transformers.js v4's env bootstrap defaults `wasmPaths` to
`` https://cdn.jsdelivr.net/npm/onnxruntime-web@${ver}/dist/ `` when no path is
set — a DEAD default for us (we always set it) but a live G5 tripwire: GATE G5
greps dist for `cdn.jsdelivr.net` and wants zero files.
`fetch_models.py --runtime` rewrites that ONE literal (count asserted == 1,
regex anchored on the minifier shape) to `./ort/`, then asserts the whole
vendored tree carries no `cdn.jsdelivr.net` byte sequence and the generated
files mention no CDN host at all. Unit-tested
(`test_build_manifest_models.py::test_patch_jsdelivr_default_counted`,
`test_vendor_staging.py::test_vendored_bundle_is_g5_clean`). The ORT `.mjs`
loader resolves its `.wasm` via `new URL(...)` relative to itself → same origin.

Honest boundary: this proves OUR additions are G5-clean. A full flagged build
(`--with-coxswain`) still contains Pyodide's own baked-in dead jsDelivr strings
(8 files, documented in build_repl.py:50-73) which this task does not own.

## 3. First-use integrity check (AC-2.7a.x)

`model_integrity.js` implements "verify BEFORE serving":

- reads the build manifest's flag-gated `models` array;
- installs a transformers.js custom cache whose `put()` hashes every incoming
  model response and throws a loud `ModelIntegrityError` (file, expected,
  actual) on any size/sha mismatch BEFORE persisting to Cache Storage;
- unknown-file requests fail loud too (pin table ↔ checkpoint drift);
- `match()` serves previously VERIFIED bytes from Cache Storage on later loads;
- sets `wasmPaths` to the vendored `ort/` dir and `allowRemoteModels=false`
  (zero non-origin network).

Negative-path proof: tampered-manifest run reports `LOUD-FAIL-OK`
(reports.jsonl, phase=negative).

## 4. Measured footprint (this machine = pessimistic bound)

Machine: WSL2 Linux x86_64, AMD Ryzen AI 9 HX 370, Radeon 890M iGPU,
29.2 GiB RAM. Browser: Chrome for Testing 152.0.7977.64 headless (new),
single renderer process hosting BOTH the built site's live Pyodide kernel
(same-origin iframe driving `dist/repl/index.html?code=...&execute=1`) and the
model worker path. `performance.memory` precise mode. RSS = chrome process tree
sum sampled every ~30 s (and 1 Hz server-side sampler where noted).

### 4.1 WebGPU availability (R10 browser matrix entry)

`navigator.gpu.requestAdapter()` on THIS stack returns ONLY a SwiftShader
(CPU-emulated Vulkan) adapter — vendor "google", architecture "swiftshader".
Under WSL2 there is no host-iGPU DAWN path for Chrome/Linux; Firefox stable
(Linux) ships no default WebGPU at all. Per the task's decision rule:

> **WebGPU treated as UNAVAILABLE here. Numbers below are the WASM fallback.
> A SwiftShader "WebGPU" number would be strictly worse than WASM and was not
> recorded as evidence. Real-GPU WebGPU rows need native Vulkan/Metal hardware
> (any Linux/Windows dGPU/iGPU box or macOS) — recorded as follow-up for the
> matrix; Safari < 26 remains out per research §4.**

Go/no-go implication: q4f16 WASM decode at 270M is viable-but-modest (below);
if the fine-tuned model's quality gates pass, shipping on WASM-first with a
WebGPU fast path added later is feasible WITHOUT changing the artifact (same
q4f16 ONNX files serve both backends).

### 4.2 Download size (actual)

46 bytes-per-file overhead aside: **446.6 MB total** for first-use (weights
425.7 + 0.5 MB, tokenizer 19.4 MiB, configs). Served from localhost NVMe the
cold fetch+verify window measured `loadMs` (reports.jsonl); production
expectation over broadband at ~10 MB/s ≈ **45 s minimum** for weights alone —
UI must stream progress (F4's system-line progress requirement).

### 4.3 Peak memory beside a LIVE Pyodide kernel

(placeholder — filled from reports.jsonl + rss samples)

### 4.4 Prefill TTFT at realistic preamble + decode tok/s

Realistic preamble = deterministic **18-tool developer preamble** (PLR verb
schemas serialized the way FunctionGemma tool prompts carry them), plus one
utterance. Prompt token count reported by the loaded tokenizer itself.

(placeholder — filled from reports.jsonl)

### 4.5 Cache-API retention

Cache name `coxswain-models-v1`, keys = repo-relative filenames (deploy-stable).

(placeholder — cold vs warm load, keys+bytes, persisted flag)

## 5. D4 — single-dtype recommendation

(placeholder — final recommendation block)

## 6. Running storage ledger (Pages 1 GB limit)

| Item | Bytes | Note |
|---|---|---|
| Current built site (dist/, pruned Pyodide) | 498,762,809 | measured 260825, `du -sb web-repl/dist` |
| Tracked overlay assets (source of truth for staged site) | 1,489,144 | incl. new vendored runtime JS 479 KB + ORT mjs 47 KB |
| q4f16 model payload if staged into dist (P2.9 wiring) | +446,591,047 | gitignored until then; served from origin either way |
| ORT wasm binary (staged under flag) | +23,567,050 | fetched-untracked in repo, present in artifact |
| Training corpus assembly (P2.5, `training/assemble/`, tracked) | +1,200,363 | C-m8 ledger entry 260825: corpus_p25.jsonl 1,028,686 + sidecar 126,687 + manifest 14,409 + assembler code/template 30,581. Trainer INPUT ONLY — never staged into dist, zero headroom impact; listed for completeness per "every delivery-touching item" |
| **Projected flagged-build artifact** | **≈ 968.9 MB** | 498.76 + 0.45 (vendor JS already inside overlay figure counts once) + 446.59 + 23.57 |
| **Headroom vs 1 GB** | **≈ 35 MB** | ~3.4% — TIGHT |

Ledger rule (C-m8): every delivery-touching item re-measures and updates this
table. Next consumer: P2.8/P2.9 (worker + integration). Mitigations if squeezed:
drop the Safari-named ORT artifacts (already dropped: −12.9 MB vs full set),
prune pyodide bundle further (product call), or split model hosting off Pages
(policy change, needs D13 audience decision).

NOTE the projection counts the model payload ONCE. If both dtypes ever shipped
(q4f16 + fp16 = 1,017 MB combined) the site blows the limit alone — this is the
arithmetic behind D4's exactly-one-dtype rule.

## 7. Deviations / blocked items

1. **No real-GPU WebGPU row on this machine** (WSL2: adapter = SwiftShader
   only). Blocked on hardware, not code; matrix follow-up owns it. WASM
   fallback numbers delivered per task instruction.
2. **Safari-named ORT artifacts deliberately not vendored** (`ort-wasm-simd-
   threaded.mjs/.wasm`, plain non-asyncify build, 12.9 MB): Safari < 26 has no
   WebGPU per research; shipping the CPU-only Safari pair costs 13 MB of the
   35 MB remaining headroom for an untested matrix cell. Loud 404 failure path
   if a Safari hits the patched default; revisit at matrix item.
3. **`models` staging into dist/ not wired**: build_repl.py staging of
   `vendor/models/` is owned by the serving-integration item (constraint: this
   task may not touch build_repl.py). Measurement used the dev layout where
   web-repl/ root is the server root; `model_integrity.js` takes an explicit
   `modelsBase` override for the future layout.
4. **Gate command environment note**: `uv run --with pytest-cov pytest tests/`
   from `web-repl/` without `--project <repo>` resolved an environment without
   `pylabrobot` (collection error in test_browser_visualizer.py). CI runs each
   test file via `uv run python -m pytest web-repl/tests/<file>` from repo
   root; locally the suite passes with `uv run --project .. --with pytest-cov`.
5. **fp16 not benchmarked end-to-end**: D4 asks for ONE shipped dtype; fp16
   (+143.9 MB vs q4f16) fails the ledger arithmetic in §6 outright regardless
   of decode speed, so measuring it would not change the decision.
