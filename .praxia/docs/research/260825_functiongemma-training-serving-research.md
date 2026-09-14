---
title: "Fine-tuning and browser-serving google/functiongemma-270m-it for a PyLabRobot lab-automation copilot"
status: draft
task_id: 260825_copilot_pipeline_spec
date: 260825
sources:
  - https://huggingface.co/google/functiongemma-270m-it
  - https://ai.google.dev/gemma/docs/functiongemma
  - https://ai.google.dev/gemma/docs/functiongemma/formatting-and-best-practices
  - https://ai.google.dev/gemma/docs/functiongemma/finetuning-with-functiongemma
  - https://github.com/google-gemini/gemma-cookbook/blob/main/FunctionGemma/%5BFunctionGemma%5DFinetune_FunctionGemma_270M_for_Mobile_Actions_with_Hugging_Face.ipynb
  - https://huggingface.co/datasets/google/mobile-actions
  - https://huggingface.co/onnx-community/functiongemma-270m-it-ONNX
  - https://huggingface.co/onnx-community/functiongemma-270m-it-ONNX-GQA
  - https://huggingface.co/spaces/webml-community/FunctionGemma-Physics-Playground
  - https://huggingface.co/Xenova/functiongemma-270m-game
  - https://huggingface.co/spaces/google/functiongemma-tuning-lab
  - https://github.com/huggingface/transformers.js/releases (v3.8.1, v4.0.x, v4.1.0, v4.2.0)
  - https://huggingface.co/blog/transformersjs-v4
  - https://huggingface.co/blog/transformersjs-v3
  - https://github.com/huggingface/transformers.js/pull/1733
  - https://github.com/huggingface/transformers.js/pull/1758
  - https://github.com/huggingface/transformers.js/issues/1328
  - https://github.com/huggingface/transformers.js/blob/main/packages/transformers/src/env.js
  - https://github.com/huggingface/transformers.js-examples/tree/main/llama-3.2-webgpu
  - https://developers.googleblog.com/en/introducing-gemma-3-270m/
  - https://ai.google.dev/gemma/terms
  - https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k
  - https://arxiv.org/abs/2406.18518
  - https://huggingface.co/datasets/NousResearch/hermes-function-calling-v1
  - https://huggingface.co/docs/trl/en/dataset_formats
  - https://huggingface.co/acon96/Home-FunctionGemma-270m
  - https://huggingface.co/litert-community/functiongemma-270m-ft-mobile-actions
---

# FunctionGemma 270M: Training + Browser Serving Research

Web research only, no code changes. Every claim carries a URL; anything not confirmable from a primary source is marked **UNVERIFIED**. All URLs fetched 2026-08-25.

---

## TL;DR for the Praxis copilot gate

1. **Fine-tuning is cheap, fully documented, and full-parameter.** Google's own recipe: TRL `SFTTrainer`, ~60 min end-to-end on a Colab A100 (~8 min/epoch on a ~9.7k-example dataset). No LoRA needed at 270M.
2. **Output is NOT JSON.** It is a bespoke token syntax (`<start_function_call>call:name{arg:<escape>value<escape>}<end_function_call>`). Our parser must target this grammar, and any "structured output" plan must be re-scoped around it.
3. **Grammar-constrained decoding is NOT available in released transformers.js today** (open PR #1758, closed predecessor #1733, tracking issue #1328). A community package exists but is unpublished/unmerged. Gate must survive on fine-tune determinism + strict parse + retry, or vendor an unreleased artifact (risk).
4. **The "~300MB" browser artifact assumption is wrong for transformers.js.** The 288 MB figure is LiteRT dynamic-int8 on Android. Real ONNX artifacts: q4f16 = **425.7 MB**, fp16 = 569.9 MB, q4 = 801.1 MB download (untied 262k-vocab embeddings dominate). Plan bandwidth/UI around ~430 MB minimum.
5. **Prior art proves the whole loop ships in-browser**: Google/Xenova's Physics Playground runs a fine-tuned FunctionGemma on WebGPU inside one static HTML page driving matter.js physics — but it uses greedy decoding + regex parsing on the main thread (no worker), which is exactly the fragility our gate needs to improve on.

---

## 1. MODEL FACTS

Source of truth: HF model card https://huggingface.co/google/functiongemma-270m-it (all bullets below verified there unless noted).

- **Base/architecture**: "Built on the Gemma 3 270M model … The model has the same architecture as Gemma 3, but uses a different chat format." HF metadata: `gemma3_text` architecture, Safetensors BF16, ~0.3B params. Text-only function calling.
- **License + acceptance**: License tag `gemma`. Repo is gated: "you have to accept the conditions to access its files" (login + click-through of Google's usage license). Terms: https://ai.google.dev/gemma/terms ("licensed for responsible commercial use", per https://ai.google.dev/gemma/docs/functiongemma). Prohibited Use Policy applies: https://ai.google.dev/gemma/prohibited_use_policy. Fine-tunes inherit the Gemma license (observed on community finetunes, e.g. https://huggingface.co/acon96/Home-FunctionGemma-270m).
- **Context length**: "Total input context of 32K tokens"; output up to 32K minus input. (Practical deployments export far less: LiteRT recipe caps KV cache at 1024 tokens; see §3.)
- **Chat template / prompting format**: developer role carries tool definitions; exact trigger phrase required:
  - System prompt: `"You are a model that can do function calling with the following functions"` — "This phrase acts as a prompt-based trigger to switch between tooling capability and general conversation" (https://ai.google.dev/gemma/docs/functiongemma/formatting-and-best-practices).
  - Six control tokens: `<start_function_declaration>/<end_function_declaration>`, `<start_function_call>/<end_function_call>`, `<start_function_response>` (also an inference stop token) — plus `<escape>` wrapping EVERY string value so `{ } , "` stay literal.
  - Rendered example (from the official fine-tune guide):
    `<bos><start_of_turn>developer\nYou are a model that can do function calling with the following functions<start_function_declaration>declaration:get_current_weather{description:<escape>…<escape>,parameters:{properties:{location:{description:<escape>…<escape>,type:<escape>STRING<escape>}},required:[<escape>location<escape>],type:<escape>OBJECT<escape>}}<end_function_declaration><end_of_turn>\n<start_of_turn>user\nHey, what's the weather in Tokyo right now?<end_of_turn>\n<start_of_turn>model\n<start_function_call>call:get_current_weather{location:<escape>Tokyo, Japan<escape>}<end_function_call>`
  - Tool results are fed back as `<start_function_response>response:name{...}<end_function_response>` in the developer turn.
  - Stop tokens for serving (LiteRT metadata in the cookbook notebook): `<end_of_turn>` AND `<start_function_response>`.
- **Trained workflows**: explicitly Single-Turn and Parallel function calling ONLY. Multi-step chaining and multi-turn clarification loops are "not been explicitly trained" out of the box; generalization expected only after task-specific fine-tuning (formatting-and-best-practices page).
- **Benchmarks (0-shot)**: BFCL Simple 61.6 / Multiple 63.5 / Parallel 39.0 / Parallel-Multiple 29.5 / Live-Simple 36.2 / Live-Multiple 25.7 / Live-Parallel 22.9 / Live-Parallel-Multiple 20.8 / Relevance 61.1 / Irrelevance 73.7 (model card).
- **Mobile Actions claim CONFIRMED**: base FunctionGemma 58% → Mobile-Actions fine-tune **85%** on the Mobile Actions eval (model card, Evaluation section).
- **Pretraining data note** (relevant to no-op behavior): training included "Tool Use Interactions — prompts, function calls, function responses, and natural language responses … to summarise the function call response, **or request clarifications when the prompt is ambiguous or incomplete**" (model card).

## 2. FINE-TUNING RECIPE

Two official Google recipes exist; both use **Hugging Face TRL SFTTrainer with FULL-parameter fine-tuning** (no PEFT/LoRA anywhere in either guide; Keras/Tunix paths exist in the Gemma docs nav but the published FunctionGemma recipes are TRL).

### 2a. Official "resolve tool-selection ambiguity" guide
https://ai.google.dev/gemma/docs/functiongemma/finetuning-with-functiongemma

- Stack: torch + transformers + datasets + accelerate + trl (+ optional flash-attn on Ampere+). Colab/Kaggle buttons provided (this is effectively the official colab notebook).
- Dataset built as conversational messages with `tools` list; assistant supervision is `{"role": "assistant", "tool_calls": [{"type": "function", "function": {"name": ..., "arguments": {...}}}]}`. Tools generated from Python functions via `transformers.utils.get_json_schema`.
- Hyperparams: `SFTConfig(max_length=512, packing=False, num_train_epochs=8, per_device_train_batch_size=4, gradient_checkpointing=False, optim="adamw_torch_fused", learning_rate=5e-5, lr_scheduler_type="constant", bf16/fp16 auto)`.
- Result: 2/20 → 16/20 correct tool selection after 8 epochs on 40 synthetic examples. Demonstrates intent (not syntax) is what needs teaching.

### 2b. Mobile Actions recipe (the 58→85% path)
https://github.com/google-gemini/gemma-cookbook/blob/main/FunctionGemma/%5BFunctionGemma%5DFinetune_FunctionGemma_270M_for_Mobile_Actions_with_Hugging_Face.ipynb (note: repo banner says deprecated, moved to github.com/google-gemma/cookbook; same file mirrored)

- Hardware/time: "**A100 GPU** … this process can take **60 minutes end-to-end**"; "about **8 minutes for 1 epoch**" (markdown cells). So yes, "trains in about an hour" is real — on an A100-class datacenter GPU, including conversion. **UNVERIFIED**: whether a smaller consumer GPU (e.g., 8–12 GB) hits similar times; nothing official publishes non-A100 numbers.
- Deps pinned: `transformers==4.57.1 trl==0.25.1 datasets==4.4.1`.
- Data prep → **prompt-completion format** with `completion_only_loss=True`: render full conversation via `tokenizer.apply_chat_template(messages, tools=tools, add_generation_prompt=False)`, render prompt as messages[:-1] with `add_generation_prompt=True`, completion = suffix diff (exact code in notebook).
- `SFTConfig`: epochs=2, per_device_train_batch_size=4, grad_accum=8, lr=**1e-5**, scheduler=cosine, bf16=True, packing=False, gradient_checkpointing=True, optim adamw_torch_fused, completion_only_loss=True, eval/save every 50 steps/epoch. max_length set per-dataset: longest example token count + 100 (computed in-notebook).
- Deployment conversion (same notebook): ai-edge-torch `gemma3.build_model_270m` → `converter.convert_to_litert(..., prefill_seq_len=256, kv_cache_max_len=1024, quantize="dynamic_int8", output_format="litertlm")` producing `mobile-actions_q8_ekv1024.litertlm`; stop tokens `<end_of_turn>` + `<start_function_response>`; `llm_model_type: function_gemma`. Pre-built result also published at https://huggingface.co/litert-community/functiongemma-270m-ft-mobile-actions.
- There is additionally a hosted point-and-click version of this flow: **google/functiongemma-tuning-lab** Space (Gradio; upload CSV of tools/examples, one-click FT, before/after eval, export weights): https://huggingface.co/spaces/google/functiongemma-tuning-lab.

### Dataset FORMAT expected (the actionable part)
JSONL, one sample per line, exactly mirroring google/mobile-actions (https://huggingface.co/datasets/google/mobile-actions, CC-BY-4.0, 9,654 rows):

```json
{
  "metadata": "train | eval",
  "tools":   [ { "function": { "name": "...", "description": "...",
               "parameters": { "type": "OBJECT", "properties": {...}, "required": [...] } } } ],
  "messages": [
    { "role": "developer", "content": "Current date and time given in YYYY-MM-DDTHH:MM:SS format: <ts>\nDay of week is <day>\nYou are a model that can do function calling with the following functions\n" },
    { "role": "user",      "content": "<NL command>" },
    { "role": "assistant", "tool_calls": [ { "function": { "name": "...", "arguments": { ... } } } ] }
  ]
}
```

Notes: mobile-actions always injects date/time context into the developer turn; tools list repeats all 7 tools in every row; arguments are objects (stringified JSON also appears in the card's field description). For Praxis: substitute PLR protocol ops for the 7 mobile tools; keep the developer-role scaffold verbatim.

## 3. QUANTIZATION FOR BROWSER

### Where 288 MB dynamic-int8 comes from
Model-card on-device table (Samsung S25 Ultra CPU, LiteRT XNNPACK): quantization scheme **`dynamic_int8`**, Model Size **288 MB**, Peak RSS 551–554 MB, TTFT 0.3 s @ 512-prefill/32-decode, decode ~126 tok/s, context 1024. That artifact is produced by the cookbook's `convert_to_litert(quantize="dynamic_int8")` step (§2b) into `.litertlm` — an Android/LiteRT-LM format, **not directly usable in a browser**.

### Transformers.js-supported quantizations & actual FunctionGemma sizes
Transformers.js dtype options include fp32, fp16, q8, q4, q4f16 (and v4.1 added q1/q1f16/q2/q2f16 — release notes https://github.com/huggingface/transformers.js/releases tag 4.1.0). Community FunctionGemma exports already exist:

- **onnx-community/functiongemma-270m-it-ONNX** (and -GQA variant), files under `onnx/`:
  - `model.onnx` (fp32): 1139.5 MB
  - `model_fp16.onnx`: **569.9 MB**
  - `model_q4.onnx`: **801.1 MB** (!)
  - `model_q4f16.onnx`: **425.7 MB**
  (file listings fetched from HF API; repo README shows the JS usage with `tokenizer.apply_chat_template(messages, {tools:[schema], tokenize:true, add_generation_prompt:true, return_dict:true})`.)
- Why q4 > fp16: Gemma 3 270M has a 262,144 vocab and untied embeddings, so embedding tables dominate the parameter count; the community q4 export keeps them at higher precision while quantizing matmul weights (inference from file-size pattern above; **UNVERIFIED** as an explicit statement by HF — treat as strong hypothesis when budgeting).
- GGUF/MLX alternatives exist (unsloth/functiongemma-270m-it-GGUF 95 likes; ggml-org, bartowski, lmstudio-community MLX 4/5/6/8-bit) but GGUF serves llama.cpp/WASM-simd paths, not the WebGPU transformers.js path.

### Conversion path for OUR fine-tune
No first-party "fine-tuned checkpoint → transformers.js" script is documented end-to-end. Practical path used across onnx-community artifacts: `optimum-cli export onnx` (text-generation-with-past) then int4/fp16 ONNX quantization, landing in an `onnx-community/*-ONNX` style repo (**UNVERIFIED for FunctionGemma specifically**; the export script that used to live in the transformers.js repo has been removed during the v4 monorepo restructure — `packages/transformers/scripts/` now contains only build scripts, checked 2026-08-25). Alternative: ask onnx-community (they take requests) or replicate their export config. Decision risk: medium-low; the -GQA export proves the gemma3_text arch converts cleanly.

## 4. TRANSFORMERS.JS + WEBGPU (load-bearing)

- **Version state**: v3 introduced WebGPU support (blog Oct 2024: https://huggingface.co/blog/transformersjs-v3). **v4 shipped Feb/Mar 2026** (blog Feb 9, 2026: https://huggingface.co/blog/transformersjs-v4; GitHub tag 4.0.0 dated 2026-03-30): new WebGPU runtime "completely rewritten in C++" with ORT contrib ops (GroupQueryAttention, MatMulNBits, QMoE); works in browsers AND Node/Bun/Deno. v4.1 added Gemma 4 support, KV-cache improvements (`past_key_values` via pipeline), more dtypes. **v4.2 added `tools` support to TextGenerationPipeline** (#1655) and is current (4.2.0, Apr 2026 releases).
- **Proof Gemma-family runs well on WebGPU**: Physics Playground ships gemma3_text on `device:"webgpu", dtype:"q4"` in production (see §6); many webml-community demos run Gemma/Llama-family on WebGPU (examples repo: gemma-2-2b-jpn-webgpu, llama-3.2-webgpu, etc.).
- **KV cache/memory**: v4.1 "Cached generation improvements (+ `past_key_values` via pipeline function)" (release notes). At 270M scale the KV cache is small; LiteRT measured peak RSS ≈ weights × ~1.9 (288 MB → 551 MB) on Android CPU. **UNVERIFIED**: precise WebGPU VRAM ceiling for this model; measure empirically. Safari < 26 lacks default WebGPU (env.js ships a `isSafari OlderThan26` check — https://github.com/huggingface/transformers.js/blob/main/packages/transformers/src/env.js); WASM fallback remains.
- **Constrained decoding status (THE load-bearing answer)**:
  - Core transformers.js does **NOT** ship JSON-schema/grammar enforcement. Tracking issue open since 2024: #1328 "Output Generation Guided by JSON Schema" (open).
  - PR #1720/#1733 proposed extension points + an llguidance-based package (`@huggingface/transformers-llguidance`), then rewritten dependency-free (`@huggingface/transformers-response-constraint`). **#1733 was CLOSED Aug 24, 2026 "in favor of #1758"**; **#1758 "Add dependency-free response constraints" is still OPEN/unmerged** and the package is **unpublished on npm** (PR thread documents downstream users vendoring the bundle, e.g. WebAI@Home running OpenAI-style response_format over released 4.2.0).
  - Field data from that PR thread: constraint overhead ≈ **11%/token** (62.6 → 69.3 ms/tok on gemma-4-E2B q4f16/WebGPU); batch size must be 1; unsatisfiable schemas throw at construction (fail-closed).
  - Documented trap: flexible-whitespace JSON grammars + greedy decoding form a fixed-point loop (model emits newline/space forever); mitigations: `whitespace_flexible:false` + fixed separators, repetition penalty, or the PR's repeated-whitespace penalty.
  - **Implication for FunctionGemma specifically**: even if #1758 merges, its constraint targets JSON; FunctionGemma emits its own `<escape>`-delimited mini-syntax. We would need a regex/grammar constraint over THAT syntax, or constrain an equivalent JSON we translate afterwards. Near-term engineering answer: rely on (a) heavy fine-tune making greedy decoding near-deterministic (Physics Playground uses plain `do_sample:false` + string slicing), (b) a hardened parser for `call:name{...}`, (c) schema validation + bounded retry, (d) optionally vendor the response-constraint bundle behind a flag.

## 5. WORKER PATTERNS + CACHING

- **Canonical setup** (official example `huggingface/transformers.js-examples/llama-3.2-webgpu/src/worker.js`): module Web Worker owns a Singleton pipeline class with lazy `??=` init; `progress_callback` plumbed into both tokenizer/model `from_pretrained`; UI communicates via `postMessage({status:"update"| "complete"| "initiate", ...})`; generation streams through `TextStreamer` callbacks; `InterruptableStoppingCriteria` for aborts. v4 blog adds `ModelRegistry.get_pipeline_files/get_file_metadata/is_pipeline_cached/clear_pipeline_cache/get_available_dtypes` and a `progress_total` progress event for aggregate download bars.
- **Lazy-load-on-first-use**: standard pattern is instantiate on first user action (Physics Playground calls `initModel()` behind a loading overlay; llama-3.2-webgpu instantiates on first generate). Deferred init guidance matches our Angular `ensureReady()` convention.
- **Caching**: transformers.js caches model files via the **Cache API** by default (`env.useBrowserCache` — "Whether to use Cache API to cache models. By default, it is `true` if available", env.js line 219; `useFSCache` for Node, `customCache` override implementing `match`/`put`, and `env.useWasmCache` for ORT WASM binaries, v4). So a ~430 MB artifact persists per-origin without IndexedDB work by us.
- **Eviction gotchas for a ~430 MB artifact**:
  - Cache API entries live in origin storage subject to quota/eviction; Chrome can evict whole-origin storage under disk pressure, and clearing site data wipes it. Exact per-browser quotas are not standardized; MDN documents `navigator.storage.estimate()` / `persist()` for inspection/persistence requests (https://developer.mozilla.org/en-US/docs/Web/API/StorageManager/estimate; **UNVERIFIED numbers** — browsers do not publish fixed quotas).
  - Practical mitigations seen in the ecosystem: show byte-level download progress (v4 `progress_total`), check `is_pipeline_cached` before offering offline mode, pin a single dtype per device class (avoid caching q4 AND fp16 for the same model), and request persistent storage. **UNVERIFIED**: whether Cache API reliably holds >500 MB on iOS Safari (Safari ≥26 enables WebGPU but storage behavior should be tested).
- **Worker vs main thread at 270M**: Physics Playground deliberately skips the worker entirely (zero `new Worker` occurrences in its index.html). At q4f16/430 MB with sub-second TTFT, main-thread decode jank is the tradeoff; the worker pattern remains the right default for our app since generation overlaps UI (Angular zoneless helps but WebGPU work still contends).

## 6. PRIOR ART

- **FunctionGemma Physics Playground** (the demo Google referenced) = https://huggingface.co/spaces/webml-community/FunctionGemma-Physics-Playground (106 likes, sdk: static, Apache-2.0 README). Stack, read from source (`index.html`, single file):
  - matter-js 0.19.0 (2D physics) + poly-decomp + Tailwind via CDN; NO framework, NO bundler.
  - `@huggingface/transformers@3.8.1` ESM import from jsDelivr.
  - Model: **Xenova/functiongemma-270m-game** (a FunctionGemma fine-tune with a SINGLE tool `add(shape, location, size, rotation, friction, restitution, mass, delay, static, velocity, color)`), loaded `device:"webgpu", dtype:"q4"` (~801 MB q4 download).
  - Inference: developer-role trigger phrase + `apply_chat_template(tools=...)`, greedy (`do_sample:false`), max_new_tokens 128, raw-string parse of `<start_function_call>call:add{...}<end_function_call>` with regex `<escape>`→quote sanitization into JSON.parse. No constrained decoding, no worker, no streaming.
  - Mirrors exist (webgpu/FunctionGemma-Physics-Playground org space, several forks).
- **Google's other shipped demos** (both inside Google AI Edge Gallery Android app, i.e., LiteRT not WebGPU): Tiny Garden (voice-controlled garden game) and Mobile Actions (Android system-control agent) — model card §Description; pre-built artifacts: litert-community/functiongemma-270m-ft-tiny-garden, litert-community/functiongemma-270m-ft-mobile-actions.
- **google/functiongemma-tuning-lab**: Gradio Space that takes JSON tool schemas + CSV examples and fine-tunes FunctionGemma in-place with before/after eval (https://huggingface.co/spaces/google/functiongemma-tuning-lab).
- **Community NL→device/robot FunctionGemma fine-tunes** (format references, evidence of demand):
  - acon96/Home-FunctionGemma-270m — Home Assistant "Assist" control, trained with Axolotl (lr 2e-4 cosine, eff. batch 32, 597 steps) on Home-Assistant-Requests-V2; GGUF for Raspberry Pi (https://huggingface.co/acon96/Home-FunctionGemma-270m).
  - distil-labs/distil-home-assistant-functiongemma (23 likes, 730 dl).
  - renhehuang/functiongemma-270m-it-coffee-robot-mcp — NL→coffee-delivery MCP tool calls (zh).
  - BrinqAI/functiongemma-270m-physical-ai.
- **NL→lab-automation datasets: GAP.** HF dataset search returns essentially nothing for opentrons/pylabrobot/lab-automation function-calling (closest hit: `bhsu/Opentrons-Test-1`, 30 downloads). **We will have to synthesize our own PLR dataset**; mobile-actions (9.65k rows) is the size anchor Google chose for a comparable single-domain task, and their ambiguity guide shows tiny (40-example) datasets move selection accuracy substantially.

## 7. TOOL-CALLING SFT DATA FORMATS (general)

- **FunctionGemma-native** (what our trainer consumes): conversational `messages` + `tools` rendered through the model's chat template into prompt-completion pairs; supervise ONLY the assistant turn(s) (`completion_only_loss=True`) — TRL formats doc: standard/conversational × language-modeling/prompt-only/prompt-completion table (https://huggingface.co/docs/trl/en/dataset_formats). Assistant target may be `tool_calls` objects (template renders them into call-syntax) or plain text.
- **xLAM/APIGen (Salesforce)**: flat `{"query", "tools":[{name,description,parameters{type,description,required}}], "answers":[{name,arguments}]}`; 60k rows generated by DeepSeek-V2/Mixtral, each verified by format-check + real execution + semantic judge, >95% human-verified correctness (https://huggingface.co/datasets/Salesforce/xlam-function-calling-60k; paper https://arxiv.org/abs/2406.18518). Useful as a synthesis QA blueprint for PLR tool data.
- **Hermes (NousResearch)**: ChatML with `<tools>{json}</tools>` in system and target `<tool_call>{"name","arguments"}</tool_call>`; mix includes glaive-function-calling-5k plus json-mode/agentic splits (https://huggingface.co/datasets/NousResearch/hermes-function-calling-v1, Apache-2.0). Format differs from FunctionGemma's but the *mix composition* (single-turn FC + multi-turn FC + json-mode + agentic) is a reasonable template.
- **Ambiguous / no-op / clarify supervision**:
  - FunctionGemma's own pretraining explicitly includes natural-language clarifications for ambiguous/incomplete prompts, and its BFCL Irrelevance score (73.7) evidences trained "don't-call" behavior (model card). So the base model already has the prior; our SFT should preserve it by mixing negative examples rather than teaching only positive calls.
  - Concrete pattern for negatives: user utterances outside the tool surface → assistant target is a natural-language clarification/refusal turn (NOT a tool_call); underspecified utterances mapping to a real tool → target a clarification question naming the missing argument (multi-turn clarify loops are otherwise unsupported, §1). The official ambiguity guide demonstrates the policy-bias variant (same query, different correct tool) — extend the same construction to none-of-the-above cases. **UNVERIFIED**: whether mobile-actions itself contains explicit no-op rows (viewer sampling showed only positive calls; dataset card says messages "usually containing user input and the expected function call").

---

## Open questions / follow-ups for the spec task

1. Decide serving stack: transformers.js WebGPU q4f16 (~426 MB, supported today) vs vendoring response-constraint (structured-output guarantee, unmaintained-risk) vs WASM llama.cpp with GGUF + native GBNF grammar constraints (true constrained decoding, slower, different runtime). This research supports option A + parser hardening as the pragmatic default.
2. Prototype ONNX export of a Praxis-fine-tuned checkpoint early (optimum path unverified for gemma3_text post-v4 restructure).
3. Benchmark WebGPU decode speed + VRAM on our target hardware class (AMD 890M iGPU among them) before committing to q4f16 vs q4.
4. Test Cache API retention of a 430 MB artifact across reloads on Chrome + Safari ≥26.
