---
title: 'Gemma-finetuned PLR voice/text copilot: scoping'
description: 'Scoping assessment for a Gemma model fine-tuned to translate voice/text lab instructions into validated PyLabRobot calls inside the JupyterLite Playground rebase: training-data sourcing, browser deployment feasibility, clarification UX, and build-location recommendation.'
status: draft
task_id: 260824_gemma_plr_copilot_scoping
date: '260824'
confidence: ''
sources: ''
---
# Gemma-finetuned PLR voice/text copilot: scoping

## Ask

Scope a Gemma model fine-tuned for PyLabRobot (PLR): a voice- or text-driven copilot that turns instructions like "pipette 50 µL from A1 to B3 in clear tips" into validated PLR calls, with clarification tooling for ambiguous ("raises") requests, deployed in-browser as part of the in-flight JupyterLite Playground rebase. Assess: sourcing existing PLR scripts/codebook/examples as a basis for a ~1,000-example calibration training set; the UX; and whether to build this as a separate tool or fold it into PLR.

## What already exists to build on (praxis + vendored PLR)

- **LiquidHandler has a small, closed, typed API surface** — `pick_up_tips`, `drop_tips`, `aspirate`, `dispense`, `transfer`, `move_resource`/`move_plate`/`move_lid`, `aspirate96`/`dispense96`, etc. (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py`). This is effectively the tool/function schema a function-calling model needs — it doesn't need to be invented, it can be extracted.
- **`praxis/backend/utils/plr_inspection` + `plr_static_analysis` + `backend/services/introspection.py`** — LibCST-based static analysis already built for the Dec-2025 Asset Management Refactor, used to discover machine capabilities and typed resource properties. Directly reusable for (a) auto-generating the tool schema from PLR source instead of hand-maintaining it, and (b) validating a generated call against the real resource/machine types in a given deck config (a built-in hallucination guard).
- **Browser Mode** already runs Python via Pyodide (WASM) with SQLite-in-browser, no backend required — the deployment substrate this feature would need already exists and is the thing currently being rebased (`web-repl/`, `praxis/web-client/src/app/features/playground/`).
- **`experimental/direct-control`** (`direct-control-kernel.service.ts`, `pyodide-pool.service.ts`, `python-runtime.service.ts`) plus the WebSerial/WebUSB/FTDI driver registry (`experimental/drivers/`) already bridges a live Pyodide kernel to physical hardware. A "speak/type a command → it runs on the deck" feature is a UI layer on top of this, not new plumbing.
- **Workcell Visualizer** (3D/2D deck view) already exists — the natural substrate for grounding: highlight the source/target wells a parsed command refers to before executing. This covers most of "clarification tooling for raises" essentially for free.
- **Nothing exists yet** for voice input, NL→PLR translation, any fine-tuned/prompted model, training-data generation, or a chat/copilot UI — this is greenfield inside praxis. (Checked: no hits for gemma/copilot/nl-to-protocol/speech recognition anywhere in `praxis/`.)
- Recent adjacent work: `.praxia/docs/research/260817_wheel-build-plr-upgrade-and-version-cohe*` locked down how the PLR wheel is built/stamped/versioned for the browser kernel — anything this feature ships should consume PLR through that same wheel/manifest path, not a side channel.

## Sourcing training data (~1,000-example calibration set)

Source tiers, roughly in order of grounding quality:

1. **PLR's own docs/cookbook** — 59 example notebooks under `external/pylabrobot/docs/` (`cookbook/`, `user_guide/00_liquid-handling/`, `02_analytical/`, `resources/*`): real, runnable code covering aspirate/dispense/transfer/mixing/tip-inventory patterns. Code-first, not paired with NL instructions — needs synthetic instruction generation per example.
2. **praxis's own protocol fixtures** (`tests/fixtures/protocols/*.py`: `simple_linear`, `conditional`, `loop_based`, `multi_machine`) — smaller, but praxis-idiomatic protocol-composition examples.
3. **`docs/community-protocols`** — currently just an index page pointing out to the PLR forums; likely thin as a first-party corpus. Check depth at the source (forums.pylabrobot.org) rather than assuming it's a real corpus.
4. **Synthetic generation, execution-verified:**
   - Enumerate the LiquidHandler tool surface × deck/resource-type combinations via `plr_inspection`'s existing LibCST analysis, to get a combinatorial space of valid calls.
   - Use strong models to generate paired (NL instruction → PLR call) examples — including deliberately ambiguous/underspecified instructions that *should* trigger clarification rather than a guess. This org already has a pattern for exactly this: the `teacher-panel-eval` skill (strong-model panel → reference labels + distilled rubric, used to calibrate a cheap/local model before committing to fine-tuning).
   - **Execution-verify every generated example** against PLR's simulator backend (see `tests/protocols/test_chatterbox_execution.py` — `ChatterBoxBackend`) rather than trusting plausible-looking output. This is the same "verify the measurement pipeline before trusting it" discipline this org applies elsewhere (`BATHOS.md`), applied to training-data QA instead of a metric function.

1,000 examples reads as a **calibration/eval set**, not fine-tuning volume — small enough for careful human review. Recommend treating it that way explicitly: distill from strong models first, calibrate a cheap/local (Gemma) candidate against it, and only fine-tune once the calibration set shows the gap is real and structural, not prompting.

## Model choice: which Gemma, where

This org already serves `engaging/google/gemma-4-12B-it-qat-w4a16-ct` via vLLM on Engaging for praxia's own rig-run flows (`CLUSTER.md`, `scripts/vllm/gemma4_node4007.sbatch`) — real, load-bearing Gemma infra already in the ecosystem. But "available in the browser" and "the model already running on Engaging" are two different sizes:

- **Server/cluster-side** (training-data generation support, fine-tune experiments via bathos): the existing 12B deployment is a reasonable base — though the *teacher* role for generating/verifying training data should stay Opus/Sonnet per this org's routing table; Gemma is the distillation target, not the teacher.
- **Browser-side** (actual inference target): a 12B model cannot run client-side. This needs a much smaller Gemma variant (2B-class or smaller), quantized, on a WebGPU-backed in-browser runtime. This is an open feasibility question, not a solved point — flag explicitly as the biggest unknown/go-no-go, especially memory-budget interaction with Pyodide's own WASM footprint already running in the same tab.

## UX: voice/text → PLR command, with clarification

- **Input:** text box in the Playground first (cheap, near-term); Web Speech API (`SpeechRecognition`) for voice next — browser-native, no new backend infra, but genuinely new to this codebase (no speech API usage found anywhere in `web-client/`).
- **Parse → propose → confirm:** NL command parses to a candidate PLR call (or short sequence) against the LiquidHandler tool schema; render it as a preview before executing — highlight source/target wells on the Workcell Visualizer, show the literal `await lh.transfer(...)` call it's about to run. Cheap to build since the visualizer and Pyodide kernel already exist; this is the standard propose-then-confirm pattern.
- **Clarification, not guessing:** when a parse is ambiguous or underspecified (unresolved "this well", missing volume, non-unique plate reference given current deck state), the model should emit an explicit `clarify` action carrying a targeted follow-up or a short disambiguation menu grounded in the *actual* current deck state (via `plr_inspection`/introspection), instead of its most likely guess. This maps directly onto a discipline this org already enforces in its own rig-run flows — schema-enforced tool calls so a node can't emit a bare "done" with no real output (`developing-praxia-workflows` §3.6) — applied here as "no bare PLR call under low confidence, must route through `clarify`."
- **Safety/state grounding:** validate every generated call against live `WorkcellState`/deck config before execution (tip present? volume within capacity? channel free?). `plr_inspection`'s typed-capability tracking already provides this as a reusable guardrail rather than something to build fresh.

## Build as a separate tool, or fold into PLR?

**Recommend: build inside praxis** (new panel/service in `web-client`, following the existing modular service-oriented architecture), not inside PLR itself, for now:

- The fine-tuned model, training pipeline, and voice UI are product surface specific to this deployment, not core robotics-abstraction concerns PLR's broader maintainer community would want to own.
- Nearly all the reusable substrate (Pyodide kernel bridge, WebSerial drivers, Workcell Visualizer, `plr_inspection`) already lives in praxis, not PLR.
- PLR is a multi-institution library; a lab-specific fine-tuned assistant is far easier to iterate on and re-target (Hamilton vs. Opentrons vs. simulated backends) inside praxis's own repo.

**Candidate for later upstreaming:** the tool-schema *extraction* piece — auto-generating a machine-readable function-calling schema from LiquidHandler's typed methods via LibCST — is generically useful to the whole PLR community and PLR-specific, not praxis-specific. Worth proposing upstream once the schema format stabilizes. Everything else (voice, clarification UX, deployed model, training set) stays praxis-side.

## State architecture (the crux)

"State" here is four distinct problems that need different treatment — conflating them is the likely design mistake.

1. **Deck/physical state (ground truth).** Already handled by PLR itself: every resource carries a live `volume_tracker`/`tip_tracker` (`external/pylabrobot/pylabrobot/resources/{volume,tip}_tracker.py`). Do not build a parallel model of deck state, and do not bake specific state into training data — training data must map language → call *shape*, not language → facts about a specific plate. The copilot queries the live object graph at generation time; it never assumes.
2. **Where the live object graph actually lives is mode-dependent — the real fork.** Production Mode has a server-owned `WorkcellRuntime` (in-memory, Redis-backed `PraxisState`, Postgres history — see `praxis/web-client/src/assets/docs/architecture/state-management.md`). Browser Mode (the copilot's actual target) has none of that: `deck`/`lh` live only inside the tab's Pyodide process, same as `direct-control-kernel.service.ts` already assumes. The copilot cannot be a stateless service calling `WorkcellRuntime` the way production features do — in-browser it must introspect the live kernel directly. If it's ever meant to run in both modes, this needs one state-query interface with two backends (kernel-introspection vs. `WorkcellRuntime`), decided explicitly now rather than discovered mid-build. Kernel persistence across reloads should reuse `pyodide-snapshot.service.ts` rather than get its own mechanism.
3. **Conversation/clarification state is cheap — don't over-build it.** The "which plate did you mean?" round-trip needs only a small pending-intent object (parsed slots + what's missing), scoped to one tab session. No Redis, no DB.
4. **Reuse point: the clarification loop already has a home.** `praxis/backend/core/simulation/state_resolution.py` (`identify_uncertain_states` / `UncertainStateChange` / `ResolutionType` / `apply_resolution`) is the existing "system is uncertain what happened, surface to a human, apply their answer, resume" lifecycle — built for protocol-error recovery (did liquid actually leave the tip after a failed dispense?), but structurally identical to what a low-confidence NL parse needs. Coxswain's `clarify` action should adapt onto this pattern instead of inventing a parallel one. **Superseded below (Composition, 260824): the actual module cannot import this code — see the correction.**

**The actually hard part:** staleness between propose and confirm. The state used to *generate* a proposed call can go stale before the user confirms it — another command ran, an error occurred, or (the bigger gap) a scheduled protocol is executing concurrently. Checked `direct-control.component.ts`: there is currently **no mutual exclusion** against an active protocol run — nothing stops an ad hoc voice/text command from firing while a scheduled run is mid-execution on the same hardware. Recommend gating Coxswain's execution on `AppStore.hasActiveRun` (already tracked in the signal store) and re-validating state immediately before execution, not only at proposal time.

## Spike: browser feasibility (resolved 260824)

**Verdict: feasible, and further along than "assess feasibility" implied — the base model already exists.**

- **`google/functiongemma-270m-it`** is a real, Google-released model: a 270M-param fine-tune of Gemma 3 270M purpose-built for function calling. ~288 MB at dynamic-int8 quantization, 32K context, Gemma license (requires accepting terms on HF). This is the correct starting checkpoint — not "Gemma 3 270M plus invent a function-calling fine-tune from scratch."
- **Fine-tuning is still mandatory, not optional polish.** Google's own published recipe (the "Mobile Actions" domain) went from 58% baseline accuracy to 85% after task-specific fine-tuning. Read straight across to PLR: expect FunctionGemma's out-of-the-box PLR accuracy to be mediocre until it gets the same specialization treatment the calibration-set work (above) is already scoped to produce.
- **Browser deployment is demonstrated, not hypothetical.** A shipped "FunctionGemma Physics Playground" runs 100% client-side via Transformers.js + WebGPU — a game, i.e. an interactive app doing local function-calling inference, close in shape to this feature. 288 MB is a modest budget relative to typical browser-LLM demos (multi-GB), which substantially de-risks the memory-budget-vs-Pyodide concern raised above; still worth an empirical check once integrated, but no longer the top unknown.
- **Correction to the "train it in browser" framing:** what's real is fine-tune off-device (Colab/local GPU, under an hour because the model is tiny) → quantize → ship the artifact to the browser for inference. Training itself is not happening inside WebGPU. This doesn't change the plan (the training step is cheap and off the critical path either way) but changes where the ~1,000-example calibration set gets used: a training/eval step in a notebook or on Engaging, not a client-side operation.
- Sources: [FunctionGemma announcement](https://blog.google/innovation-and-ai/technology/developers-tools/functiongemma/) · [model card](https://huggingface.co/google/functiongemma-270m-it) · [on-device fine-tuning guide](https://developers.googleblog.com/en/own-your-ai-fine-tune-gemma-3-270m-for-on-device/) · [Gemma 3 270M announcement](https://developers.googleblog.com/en/introducing-gemma-3-270m/)

## Clarification architecture: fast-and-frugal tree (FFT) gate (revised 260824 — cue order corrected)

Fast-and-frugal trees ([Gigerenzer et al.](https://en.wikipedia.org/wiki/Fast-and-frugal_trees); toolbox: [FFTrees](https://www.sas.upenn.edu/~baron/journal/17/17217/jdm17217.html)) are small ordered sequences of yes/no cues where any cue can exit early with a classification — deliberately not a full ML classifier. That's the right property for a deterministic safety gate sitting between an LLM's output and a robot: auditable, debuggable, robust to noise, and — critically — it means the model's own confidence score is never what decides whether to ask a clarifying question. **Worth naming honestly: this is FFT in structure (ordered exit-early gate), not the classical psychology-literature sense.** Real FFTs order cues by statistically measured predictive validity from data; these cues are exact deterministic checks, so ordering is by cost-and-decisiveness instead — cheapest and most conclusive first.

**Pipeline (model does semantic parsing only; everything after is deterministic):**

1. **Input** — text box first; Web Speech API voice later (push-to-talk, not always-listening — see Chat UI below), feeding the same text channel.
2. **Parse (FunctionGemma)** — NL → a candidate structured call against the LiquidHandler tool schema. Slots may still be *symbolic* ("lane C", "the plate carrier") rather than resolved object references — the model's job stops at "what shape of call, with what named references."
3. **Ground (deterministic)** — every symbolic slot resolved against the live kernel's deck/resource graph via `plr_inspection`. "Lane C" → a hard rail index. "The plate carrier" → the actual candidate set of resource objects that could fill that slot.
4. **FFT triage** — cost-and-decisiveness ordered, corrected from the first pass (concurrency was originally last; it should be first — it's both the cheapest check and, on failure, makes every other cue moot):

   | # | Cue | Cost | Exit(s) |
   |---|---|---|---|
   | 0 | Is a protocol run currently active? | free — local `AppStore.hasActiveRun` read | `blocked:concurrent` |
   | 1 | Does the parse have every required slot? | free — no kernel round-trip | `clarify:incomplete` |
   | 2 | Does every symbolic reference resolve to exactly one live object? | kernel round-trip | `clarify:not_found` (0 matches) / `clarify:disambiguate` (>1 matches — the Hamilton/two-compatible-carriers case) |
   | 3 | Do preconditions hold for the resolved call? (tip state, capacity, resource-type validity, via PLR's own trackers) | kernel round-trip, depends on cue 2's output | `clarify:precondition` |
   | — | all pass | | → propose/confirm |

   Each cue is a pure function `(parsed_call, grounded_context) → {continue} | {exit, type, payload}`. Every `clarify:*`/`blocked:*` exit carries a **typed** payload — candidate list for `disambiguate`, missing-field list for `incomplete`, etc. — so the chat UI renders each kind differently instead of a generic error string, and the gate stays auditable rather than becoming a pile of ad hoc if-branches.
5. **Clarify, without a second model round-trip.** A small `PendingIntent` object (the "conversation state" layer from the state-architecture discussion above) holds the original parse, resolved slots so far, and which cue exited. The user's answer is resolved by a **lightweight deterministic matcher** against the known candidate set (label, position, or simple synonym match) — not a re-run of FunctionGemma, since a clarification answer is almost always a closed-set pick. Resolving the slot re-enters the FFT at the cue *after* the one that exited. Adapted onto the existing `state_resolution.py` *pattern* (uncertain state → surface → resolve → resume), reimplemented dependency-free per the Composition correction below — not imported.
6. **Propose → confirm** — render a natural-language restatement as the primary reading ("aspirate 50 µL from A1, dispense into B3"), with the literal call (e.g. `deck.assign_child_resource(carrier, rails="C")`) available as secondary/collapsed detail, plus a one-line "why am I asking" disclosure when a clarification preceded it (e.g. "2 plate carriers matched your Hamilton") — cheap, and it's the actual payoff of an auditable gate over a bare confidence score. Highlight the affected location on the Visualizer. **Re-run cues 0 and 3 immediately before execution** — these are the time-sensitive ones (another run starting, tip/volume/capacity changing between propose and confirm); cues 1/2 aren't meaningfully time-sensitive the same way and don't need re-checking on every confirm.
7. **Execute** — against live kernel objects (Browser Mode) or `WorkcellRuntime` (Production Mode) via the state-adapter split above. **If execution itself fails mid-operation, that's the same uncertain-state shape as a pre-execution `clarify:*` exit, just triggered post-execution** — reuse the same resolve-then-resume adapter rather than building a second recovery mechanism. See Chat UI's "execution-failure card" below.

**Gap: PLR has no carrier↔machine compatibility metadata** (grepped `resources/carrier.py` and the Hamilton carrier defs — carriers are grouped only by vendor namespace, not tagged per-machine-model). Originally scoped as "needs a hand-curated table"; **superseded by the Grounding contracts section below** — resolved via a derive-from-usage contract instead of a static table.

## Tool-calling schema (260824)

Grounded against the real `LiquidHandler` API, not assumed. Representative example, checked against the actual `transfer()` signature (`external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py:1273`):

```jsonc
{
  "name": "transfer",
  "description": "Move liquid from one source well to one or more target wells. Requires tips already loaded on the active channel(s) — this call does not pick up or drop tips.",
  "parameters": {
    "source": { "type": "string", "description": "Symbolic reference to the source well, e.g. 'A1' or 'the plate in lane C, well A1'." },
    "targets": { "type": "array", "items": { "type": "string" }, "description": "Symbolic references to one or more target wells." },
    "source_vol": { "type": "number", "description": "Volume in µL to withdraw from source. Mutually exclusive with target_vols." },
    "target_vols": { "type": "array", "items": { "type": "number" }, "description": "Explicit per-target volumes in µL. Mutually exclusive with source_vol/ratios." }
  },
  "required": ["source", "targets"]
}
```

Two design decisions this surfaced:

1. **`transfer` requiring pre-loaded tips is a real precondition** (confirmed by reading the source — it only calls aspirate/dispense, no tip handling inside it), not an incidental detail. This is Cue 3's job: no tips loaded → `clarify:precondition` (or the FFT could auto-insert a `pick_up_tips` step against the currently-mounted rack rather than asking — a real product-taste call, not resolved here).
2. **Schema verb granularity should not mirror PLR's method granularity 1:1.** `move_plate`/`move_lid`/`move_resource` are three PLR methods but one natural verb ("move X to Y"). The schema exposes one `move_resource` function; a deterministic dispatcher picks the correct underlying PLR call based on the *resolved* resource's type after grounding, not before — keeps the model's job "what does the user want," not "which of three PLR methods applies."

The schema also needs a first-class **`clarify`** function, not a fallback bolted on outside the schema — same discipline as this org's own rig-run flows (schema-enforced `write_X_result` tools instead of a bare `done`, `developing-praxia-workflows` §3.6): forces "I need more information" to be a structured call the model can only reach through the tool set, never a guess dressed up as confidence.

**Resource-category and location arguments should be enum-constrained wherever the vocabulary is closed**, not left as free strings — see Pipeline layering below for why this is load-bearing, not just tidiness.

## FunctionGemma fine-tuning: LoRA adapters per pipeline stage (260824)

Checked, not assumed: Google's released `functiongemma-270m-it` checkpoint is itself a full merged fine-tune (their "Mobile Actions" recipe demonstrates full-parameter fine-tuning, cheap because the model is tiny — under an hour). But ~28 community LoRA adapters already exist on the HF hub, so LoRA fine-tuning is a real, supported path even though it's not Google's documented default. No official guidance exists on stacking/swapping multiple adapters for different tasks — open design space, not an established pattern to follow.

**The FFT gate itself needs zero models, by design.** Cues 0–3 are pure deterministic code — that's not a shortcut, it's the entire reason FFT was chosen over an LLM-judged gate (auditability, no black box in a safety-critical role). Adding a model call inside the gate would undo the point of it.

**Recommendation: one resident FunctionGemma base, a small family of task-specific LoRA adapters swapped per stage**, not one adapter doing everything and not separate full models per stage:
- **Parse adapter** — NL → structured PLR call (the ~1,000-example calibration set).
- **Candidate-resolution adapter** — free-form clarification answer + candidate list → selected ID. Narrower, smaller training set. Only invoked on the free-text/voice clarification-answer path — click/button answers (the default UI affordance) never touch a model at all.
- More addable later per stage without scope-creeping either existing adapter — same "don't build the abstraction until there's a second real consumer" discipline already applied to the coxswain/PLR module split.

**Open, unverified:** in-browser LoRA hot-swapping (load base once, swap small deltas without a full reload) is well-established server-side (`transformers`+`peft`) but is less proven territory in Transformers.js/WebGPU specifically. Needs its own small spike before this is treated as settled.

## Pipeline layering: where NLU actually happens (260824)

Sharpened after catching an imprecision: the FFT gate does not parse language, and neither does most of "grounding" — if a "deterministic" layer needs to fuzzy-match free text, that's a leak, and the fix is pushing more structure into the schema/parse step, not adding fuzzy logic downstream where it undermines the auditability the FFT was chosen for.

| Layer | Does what | NLU? | State-dependent? | Composable boundary |
|---|---|---|---|---|
| 0. Input | Capture text/voice | no | no | pure I/O |
| 1. Parse | NL → structured call, symbolic slots | **yes — the only NLU in the system** | **no** — doesn't touch the deck | testable offline against golden (NL, call) pairs; no kernel needed |
| 2a. Symbol normalize | Closed-vocab token → canonical form (e.g. a location string → rail index) | no | no — fixed geometry/vocab, not live state | pure lookup, versioned with the schema — see Grounding contracts below for how the vocab itself gets populated |
| 2b. Instance resolve | Canonical form → live object(s) on the deck right now | no | **yes — fresh every call, never cached** | the one layer with a Browser-Mode/Production-Mode backend split (kernel introspection vs. `WorkcellRuntime`) |
| 3. FFT triage | Pass/exit decision over Layer 1+2's output | no | yes for cues 0/2/3, no for cue 1 | pure function, identical regardless of domain — the actual "coxswain-core" layer |
| 4. Clarify | Resolve a clarification answer | only on the free-text path | no — operates over Layer 2's already-fetched candidates, no new kernel query | button answers: zero NLU; typed/spoken answers: the candidate-resolution adapter |
| 5. Propose/confirm | Render, re-run cues 0/3 for staleness | no | yes, fresh reads | — |
| 6. Execute | The real PLR call | no | yes — mutates state | — |
| 7. Visualizer paint | Reactive repaint | no | yes, but fully decoupled — fires off PLR's own callbacks | already built, established earlier |

## Grounding contracts, not hardcoded tables (260824)

User pushback, correct: a hand-maintained lookup table is the wrong default for Layer 2a's closed vocabularies. But the two cases originally scoped as "needs a table" are different in kind, and the fix differs per case — an agentic process can't discover an *arbitrary naming convention* by reasoning about it (there's no ground truth to derive; a different lab could validly pick a different mapping), but it also can't invent a *physical compatibility fact* out of nothing either. Two distinct contracts, not one:

**1. Lane-letter → rail-index (and similar addressing conventions): learn-from-clarification, not a static table.** Checked and confirmed: PLR's own `rails` parameter (`resources/hamilton/hamilton_decks.py`) is a 1-indexed **integer**, no lettered addressing anywhere in PLR — "lane C" is a convention this lab would have to establish, not something to discover. This isn't a new subsystem — it's the *existing* `clarify:not_found` exit through the FFT, with one addition: the resolved answer gets written back instead of discarded.

```
resolve(symbolic_ref, scope) -> Known(target) | Unknown
learn(symbolic_ref, target, scope)   # called only after a clarification round confirms it
invalidate(symbolic_ref, scope)      # see staleness below
list(scope)                          # auditability — a settings surface a scientist can review/correct
```
`scope` is an open question, not assumed: per-deck-config, per-workcell, or per-user (different scientists on the same Hamilton may hold different personal conventions). Storage rides the same L0–L3 layered persistence contract already decided for notebooks/chat transcripts — not a third bespoke persistence mechanism.

**Two risks this introduces that a static table wouldn't have, both need an answer, not to be ignored:**
- **Cold-start chattiness** — a brand-new deck config needs at least one clarification round per location reference before the system is fluent. Expected, not a bug, but worth naming so it doesn't read as broken on day one.
- **Staleness is worse here than elsewhere, because it's the one place a wrong answer wouldn't even ask.** A learned alias must be treated as a **prior, not an override** — it still passes through Layer 2b's live-instance check every time (does rail 3 actually hold what "lane C" implies right now?); a mismatch invalidates the alias and re-triggers `clarify` rather than silently trusting memory. Same discipline as re-running cues 0/3 at confirm time: never let a cached belief substitute for a fresh state check on the safety-relevant path.

**2. Carrier↔machine compatibility: derive-from-usage, not a static table either.** There IS a ground truth here (a physical/hardware fact PLR just doesn't encode), so the fix is a different shape than "ask and remember" — query the corpus of deck configurations already used in this lab's own session/workcell history as the live source of truth, improving as the lab uses the system rather than requiring anyone to pre-populate a table.

## Chat UI (260824)

Five message kinds, not one undifferentiated transcript:

1. **User turn** — text or voice transcript, rendered identically regardless of input mode.
2. **Propose/confirm card** — see FFT step 6 above: natural-language restatement primary, literal call secondary, disclosure line when relevant.
3. **Clarification card** — renders the FFT exit payload directly: candidate picker (click, type, or voice-answerable) for `disambiguate`; field prompt for `incomplete`; plain explanation for `precondition`/`blocked`.
4. **Execution-failure card** — reuses the resolve-then-resume adapter (FFT step 7), triggered post-execution instead of pre-execution; not a second mechanism.
5. **System/status line** — blocked-by-concurrent-run, model still loading, etc.

**Voice needs a safety property text never did.** This executes on real hardware — an always-listening microphone transcribing ambient lab conversation into robot commands is a genuine hazard here, unlike a coding assistant. **Push-to-talk is a hard requirement, not a nice-to-have.**

**Speech-to-text decision (260824): Chrome's on-device Web Speech API, not a vendored Whisper/Moonshine model.** Chrome 139 (shipped Aug 2025, over a year mature) added a genuine on-device mode to the standard `SpeechRecognition` API — audio/transcript never leave the device, no server round-trip, with a capability check + install-prompt flow for the on-device language pack. Chosen over Moonshine/Whisper via Transformers.js specifically because it doesn't fight the pattern the rest of this doc already committed to: zero vendoring cost (vs. another ML runtime alongside the already-heavy, already-lazy-loaded FunctionGemma), and Chromium-only is already priced in by the product's hard WebSerial/WebUSB requirement, not a new cost this decision introduces. Open implementation detail, not a blocker: the on-device language pack isn't guaranteed present on a fresh machine and needs the availability-check-then-install-prompt flow, same loud-failure discipline already used elsewhere in this codebase.

**Confirmation friction should scale with reversibility, not be uniform.** A read-only deck query needs no confirm; a normal pipetting op gets the standard propose/confirm card; something irreversible (a discard that can't be undone) plausibly deserves higher friction than one click. Flagged as a real design dimension, not built out as a full tiering scheme yet.

**Transcript persistence rides the existing layered persistence contract** (L0 IndexedDB autosave → L1 `persist()` → L2 File System Access working folder → L3 export/import, from the 260817 ADR's "F" decision) rather than inventing separate chat-history storage — the same "savable" guarantee a scientist already gets for notebooks should cover what they told the robot to do.

**Layout:** Chat/Visualizer tabbed side panel per the "Coxswain as optional plugin" decision above — Visualizer tab makes grounding visible non-verbally (e.g. ghosting candidate carrier types at lane C during `clarify:disambiguate`, once that rendering capability exists — see the visual-ghosting gap noted in Composition).

## Naming: Coxswain (working name, 260824)

Considered and rejected "copilot" — genuine semantic collision with GitHub Copilot. Shortlist checked against PyPI: bare `deckhand` is taken (an unrelated OpenStack/Airship tool; `praxis-deckhand` is open), `helm` and `wrangler` were ruled out immediately as worse versions of the same collision problem (Kubernetes Helm, Cloudflare Wrangler — both more entrenched in a developer's namespace than Copilot itself), `coxswain` is open on PyPI.

**Decision: working name is `coxswain`.** Framing is deliberately broader than PLR: the user's stated intent is for Coxswain to become a general baseline library for managing fine-tuned function-calling-model web deploys (model loading, the FFT triage gate, propose/confirm primitives, the state-grounding adapter pattern) — PLR is the first and, for now, only consumer, not a permanent scope boundary. Practical consequence for the code, without over-building an abstraction layer prematurely: keep the model-loading/FFT-engine/propose-confirm code free of gratuitous PLR-specific imports where that's already the natural shape (it queries a grounding interface, not `pylabrobot` directly), but do not construct a formal plugin/adapter system now — there is exactly one consumer. Final published name (`coxswain` vs. `plr-deckhand`) is explicitly deferred to publish time, once it's clear whether a second consumer actually materializes.

## Composition (260824, revised after checking current web-repl state)

Two corrections to earlier sections in this doc, found by reading the actual current repo state rather than assuming:

1. **`state_resolution.py` cannot be reused as-is (revises "Clarification architecture" above).** `.praxia/docs/research/260817_standalone-web-repl-extraction-shell-and-brainstorm.md` (winner "B′ INJECT", accepted) and its ADR `.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md` establish that web-repl is a **static site with no server at runtime**, that Direct Control and the protocol-runner worker are retiring to a deferred "experimental" scope, and that `web-repl/` and `praxis/` have **no Python import path in either direction** (ADR §5.2) — the only sanctioned edge is a build-time pinned-artifact copy. `state_resolution.py` is SQLAlchemy/Postgres-coupled and lives in that deferred backend scope; it cannot be imported into a static, serverless artifact. The uncertain-state → resolve → resume *pattern* is still worth keeping, reimplemented dependency-free inside the new copilot module rather than imported.
2. **A live visualizer already exists — the "screenshot" plan should not be built.** `web-repl/overlay/assets/visualizer/` already vendors PLR's own renderer (`index.html`/`vis.js`/`konva.min.js`/`gif.js`), and `web-repl/overlay/assets/python/praxis/viz/{transport,browser}.py` already implements `BrowserVisualizer` (PLR's `Visualizer` with its websocket/HTTP server removed — Pyodide has no sockets/threads — replaced with a `BroadcastChannel` named `praxis_viz`, deliberately split from the device-auth `praxis_repl` channel; Phase 6, spike-gated: G2, S-D). It fires automatically on every PLR state mutation via PLR's own callback registration — no capture code needed. **Coxswain's visualizer toggle should reveal/hide this existing panel, not build new screenshot-capture plumbing** — screenshotting would be strictly more work for a worse (polled vs. event-ordered) result. Real gap found by reading `visualizer-augmentations/index.js`: it only relays *real, committed* state — there is no hypothetical/"ghost" rendering capability, so visually ghosting multiple disambiguation candidates (the plate-carrier example) is a genuinely new capability, not something to assume exists. MVP scope: keep disambiguation/proposal previews **text-only in chat**; visual ghosting is a later, separable feature.

**Module boundary:** new top-level `coxswain/` directory, uv workspace member (internal-organization choice, not a git submodule — this repo has a demonstrated history of letting submodule pins go stale: `external/pylabrobot` is 222 commits/six months behind upstream per the 260817 brainstorm; a workspace member gets the same boundary with none of that risk, and is still cleanly extractable to an independent repo later since it's already a self-contained package). Root `pyproject.toml` has no `[tool.uv.workspace]` yet — this introduces the pattern, it doesn't extend an existing one. Same import-boundary discipline as the existing `praxis`/`web-repl` split (ADR §5.2): `coxswain/` must not import `praxis.backend.*`; its browser-facing pieces vendor into the static build the same way `visualizer/` and the shims do, tracked in the same manifest/sha-integrity scheme (ADR §2.3, detectors D1–D3) rather than hand-copied; kernel-side grounding logic ships as another small fetched Python module, same pattern as `praxis/viz/`. Per the naming note above, the PLR-specific pieces (LiquidHandler tool schema, machine↔carrier compatibility table, `plr_inspection`-based grounding) should stay legibly separate within `coxswain/` from the model-loading/FFT/propose-confirm core — informally, not as a built plugin system yet.

## Kernel-ownership fork: resolved (260824) — Coxswain is an optional plugin to web-repl, not a separate page

User decision: no separate landing page. One clean interface that is both the notebook and the chat — Coxswain becomes an optional plugin *of* web-repl, sharing its one kernel. This picks fork option (b) from the prior entry, with the mechanism specified rather than left open.

**Verified before recommending a mechanism, not assumed:** re-checked whether the constraint that made the 260817 ADR *defer* (not reject) a real JupyterLab federated-extension version of this ("option B — NATIVE") still holds. It does — `node`/`npm` are still absent from this machine (`bun` only), and `web-repl/` still has no `package.json`. `@jupyterlab/builder`'s federated-extension packaging is a Node/webpack toolchain; building one here would also break this repo's own Bun convention (`AGENTS.md`). So: **extend the injection pattern that already won (B′ INJECT), don't build a Lumino-registered extension.** The ADR explicitly designed for this: *"praxis-shell.js can later be repackaged as a labextension without changing the kernel-side contract, because the contract is BroadcastChannel message shapes, not JS API surface"* — meaning nothing here is wasted if a real extension happens later once the toolchain exists; the channel-shaped contract carries over.

**Design:**
- **Layout:** `lab/` fills the main area, completely untouched. A `coxswain-shell.js` — injected the same asserting way as `praxis-shell.js` — wraps `<body>` in a plain CSS side panel, not by touching JupyterLab's own Lumino docking (avoids fighting its layout engine entirely). The panel has two tabs: **Chat** (default) and **Visualizer** — the Visualizer tab is the already-existing vendored panel, nothing new to build there.
- **Threading/channels:** three same-origin contexts. The Pyodide kernel worker (existing) runs FFT grounding queries against live deck state via a small fetched module, same pattern as `praxis/viz/`. FunctionGemma/Transformers.js inference runs in its **own** Worker (Transformers.js's standard pattern, keeps the UI thread responsive), producing a candidate parsed call. The main thread renders chat/propose-confirm/clarification. A **new `praxis_coxswain` BroadcastChannel** carries traffic between them — following `transport.py`'s own stated principle for why `praxis_viz` was split from `praxis_repl` in the first place (different traffic classes shouldn't share a channel); reusing either existing channel for this would violate that same reasoning.
- **"Optional" is a build-time mechanism, not just framing:** `build_repl.py` gets a flag (e.g. `--with-coxswain`) gating whether `coxswain-shell.js` and its assets are injected/vendored at all, manifest/sha-tracked the same way as everything else (ADR §2.3, D1–D3) — a plain web-repl build is completely unaffected when it's off.
- **The model must be lazy-loaded even when the plugin is on.** FunctionGemma (~288 MB) dwarfs everything currently vendored combined. It must not be part of the base page load — fetch only on first chat interaction, same lesson this codebase already learned the hard way (the ADR calls out deleting `PyodidePoolService.preWarm()` for exactly this class of mistake: don't eagerly boot a heavy thing nobody asked for yet).

## Suggested next steps (not yet started — scoping only)

1. Build the machine↔carrier (and other machine↔resource) compatibility table Cue 2 depends on — doesn't exist in PLR today; see gap above.
2. Draft the tool-calling schema for the LiquidHandler core methods — mechanical, can likely be generated directly from `plr_inspection` output rather than hand-written.
3. Generate and execution-verify a first small slice (~50-100 examples) against `ChatterBoxBackend` to validate the data pipeline before scaling to the full 1,000; fine-tune `functiongemma-270m-it` (not a base model) on it.
4. Prototype the FFT gate + propose→confirm UX inside the existing `direct-control`/Playground surface using the off-the-shelf (not yet fine-tuned) FunctionGemma checkpoint, to validate the UX and the grounding/clarification pipeline before investing further in fine-tuning.
5. Empirically check WebGPU/Transformers.js memory footprint alongside a live Pyodide+PLR kernel in the same tab, now a secondary check rather than the primary unknown.

