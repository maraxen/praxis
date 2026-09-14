---
title: 'Coxswain/FunctionGemma copilot pipeline: code-level recon'
description: 'Verification of the 260824 scoping doc claims against current code, filling gaps for the next phase spec: tool-schema extraction seams, Chatterbox execution verification, protocol fixtures, PLR docs corpus, web-repl serving substrate, parse-source seam, and artifact-size constraints.'
status: draft
task_id: 260825_copilot_pipeline_spec
date: '260825'
---

# Coxswain/FunctionGemma copilot pipeline: code-level recon

Read-only recon verifying `.praxia/docs/research/260824_gemma-finetuned-plr-voice-text-copilot-scoping.md`
(the "scoping doc") against the current tree on branch `repl-fresh-boot`, and filling its gaps
for the next-phase spec (synthetic data pipeline → FunctionGemma fine-tune → browser serving).
Every claim below carries a file:line cite. Line refs checked 260825.

**Headline correction up front:** the scoping doc predates the Coxswain MVP landing. Much of what
it scoped as greenfield now exists: `coxswain/src/coxswain/` (kernel-side Python, FFT gate,
tool schema, pre-simulation), `web-repl/shell/coxswain*` (injected panel + 17 JS modules + 17
test files), `--with-coxswain` build plumbing end-to-end in `web-repl/scripts/build_repl.py`,
and a locked spec at `.praxia/docs/specs/260824_coxswain-mvp-ux-spec.md` whose architecture
section (`:88-94`, F1-F10) explicitly cites the scoping doc and closes further architecture
debate. The next phase spec builds *on* these, not beside them.

---

## 1. Tool-schema extraction

### 1.1 What `plr_inspection` actually provides

`plr_inspection` is a **package**, not a single file: `praxis/backend/utils/plr_inspection/{__init__,docs,runtime,validation}.py`.

- Exports (`praxis/backend/utils/plr_inspection/__init__.py:3-36`): `get_capabilities`, `get_deck_details` (docs.py); ~20 `runtime.py` discovery helpers (`get_all_classes`, `get_resource_classes`, `discover_deck_classes`, `get_constructor_params_with_defaults`, …); three validators `is_{resource,machine,deck}_subclass` (`validation.py:16-43`).
- **The runtime half is formally deprecated**: `runtime.py:1-8` carries a module docstring ".. deprecated:: ... uses runtime inspection which has side effects (imports PLR modules). For machine/backend discovery, use plr_static_analysis instead." `docs.py:get_capabilities` is likewise deprecated with a `DeprecationWarning` (`docs.py:16-28`) and its body is name-string heuristics (`"96" in name` → channels, `docs.py:41-55`). `static.py` is a one-line placeholder: "# This file is reserved for static analysis functions." (`static.py:1`).
- Output shapes are plain dicts: `get_constructor_params_with_defaults` → `{param_name: default}` (`runtime.py:88-114`); `get_deck_details` → `{fqn, constructor_args, assignment_methods[{name,signature,parameters,doc}], category, model}` (`docs.py:58-95`).

### 1.2 What `plr_static_analysis` provides

LibCST-based, no-import static analysis (`praxis/backend/utils/plr_static_analysis/`):

- Entry point `PLRSourceParser(plr_source_root, use_cache)` (`parser.py:65-79`) with glob patterns covering all machine packages incl. `pylabrobot/liquid_handling/**/*.py` (`parser.py:45-61`). Public API: `discover_all_classes() -> list[DiscoveredClass]` (`parser.py:80-112`), `discover_machine_classes` / `_resource_classes` / `_backend_classes` / `discover_frontend_classes` / `discover_deck_classes` (`parser.py:114-201`), `discover_resource_factories()` for `def Cor_96_wellplate_360ul_Fb(name) -> Plate` factory functions (`parser.py:203-242`).
- Visitors: `CapabilityExtractorVisitor` (`visitors/capability_extractor.py:33-192`), `ProtocolFunctionVisitor` for `@protocol_function` functions (`visitors/protocol_discovery.py:26-255`), `ProtocolRequirementExtractor` capturing `lh.pick_up_tips96()`-style requirements (`visitors/protocol_requirement_extractor.py:85-251`), `ResourceFactoryVisitor`, `ComputationGraphExtractor`.
- Models (`models.py`): `DiscoveredClass` with `capabilities`, `machine_capabilities`, `capabilities_config`, `connection_config`; typed per-machine schemas e.g. `LiquidHandlerCapabilities{channels, has_iswap, has_core96, ...}` (`models.py:133-141`); protocol-side `ProtocolFunctionInfo{name, fqn, parameters: list[ProtocolParameterInfo], computation_graph, ...}` (`models.py:107-124`) where each parameter carries `is_itemized`, `itemized_spec`, `linked_to` (`models.py:86-104`).

### 1.3 Could a script emit a function-calling JSON schema for LiquidHandler as-is?

**No — there is a genuine, narrow gap.** Nothing in either package extracts *method signatures of one class into a JSON-Schema-shaped function catalog*:

- `plr_static_analysis` discovers classes and class-level capabilities/decorated-protocol metadata; it does not walk arbitrary public method parameters of `LiquidHandler`. Its `ProtocolFunctionVisitor` targets `@protocol_function` functions, not machine frontends.
- `plr_inspection.runtime` could do it at runtime via `inspect.signature`, and in fact a ready seam already exists elsewhere: `praxis/backend/services/introspection.py:19-80` `inspect_machine_methods(fqn) -> list[MethodInfo]` — public-method sweep (skips `_`-prefixed and `object` members, `introspection.py:40-45`), returns `MethodInfo{name, doc, args: list[ArgumentInfo{name,type,default}]}` (`introspection.py:7-18`), JSON-safe defaults enforced (`introspection.py:66-74`), pylabrobot-namespace allow-list (`introspection.py:23-24`). This is ~90% of a generator; what's missing is (a) mapping `inspect` types → JSON types, (b) required-vs-optional derivation, (c) the symbolic-resource-reference convention from the scoping doc (`:115-127`), and (d) enum-constraining closed vocabularies.
- **Important:** the fine-tune target should probably NOT be a freshly generated schema. `coxswain/src/coxswain/plr/tool_schema.py:59-131` already ships a hand-authored, risk-tiered `TOOL_SCHEMA` (20 entries: `pick_up_tips`, `aspirate`, `dispense`, `transfer`, `stamp`, `drop_tips`, `discard_tips`, `move_resource/plate/lid`, plate-reader reads, heater-shaker verbs) with `ToolSpec{name, verb, receiver_type, risk_tier, effects, to_waste}` (`tool_schema.py:27-56`). The pipeline spec should treat this as the canonical function set and reconcile it against generated signatures (see GAPS #1).

### 1.4 LiquidHandler public methods worth exposing (vendored PLR)

Signatures verified by `inspect.signature` against `external/pylabrobot` (method lines in `external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py`):

| method | line | required params |
|---|---|---|
| `pick_up_tips(tip_spots: List[TipSpot], use_channels=None, offsets=None)` | :438 | `tip_spots` |
| `drop_tips(tip_spots, use_channels=None, allow_nonzero_volume=False)` | :587 | `tip_spots` |
| `return_tips(use_channels=None, ...)` | :728 | — |
| `discard_tips(use_channels=None, allow_nonzero_volume=True, ...)` | :783 | — |
| `aspirate(resources: Sequence[Container], vols: List[float], ...)` | :878 | `resources`, `vols` |
| `dispense(resources, vols, ...)` | :1070 | `resources`, `vols` |
| `transfer(source: Well, targets: List[Well], source_vol=None, ratios=None, target_vols=None)` | :1273 (scoping doc cite `:1273` confirmed) | `source`, `targets` |
| `stamp(source: Plate, target: Plate, volume: float)` | :2001 | `source`, `target`, `volume` |
| `pick_up_tips96(tip_rack: TipRack)` | :1448 | `tip_rack` |
| `drop_tips96(resource)` | :1517 | `resource` |
| `aspirate96(resource, volume)` | :1695 | `resource`, `volume` |
| `dispense96(resource, volume)` | :1847 | `resource`, `volume` |
| `move_resource(resource, to)` | :2301 | `resource`, `to` |
| `move_plate(plate, to)` | :2439 | `plate`, `to` |
| `move_lid(lid, to)` | :2379 | `lid`, `to` |
| `move_tips(source_tip_spots, dest_tip_spots)` | :841 | both |

State/query surface also available: `serialize_state`/`load_state` (:214/:239), `update_head_state` (:262), `get_mounted_tips()` (:578), `get_picked_up_resource()` (:426), `probe_tip_presence_via_pickup` (:2589), `probe_tip_inventory` (:2666), `consolidate_tip_inventory` (:2712). **Note:** `mix`, `blow_out`, `touch_tip` do **not** exist on this vendored LiquidHandler (verified by `getattr`; grep of the file finds no such defs) although `TOOL_SCHEMA` lists them (`tool_schema.py:103-111`).

---

## 2. Execution verification

### 2.1 Naming correction

`ChatterBoxBackend` is a **deprecated tombstone**: `external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox_backend.py:1-5` — `__init__` immediately raises `NotImplementedError("...Use LiquidHandlerChatterboxBackend instead.")`. The scoping doc's reference (`:36`) needs updating. The real backends:

- `LiquidHandlerChatterboxBackend(LiquidHandlerBackend)` — `external/pylabrobot/pylabrobot/liquid_handling/backends/chatterbox.py:24-242`. Device-free; every op prints a formatted table. It implements the full op vocabulary (`pick_up_tips` :63, `drop_tips` :93, `aspirate` :123, `dispense` :162, `*_tips96` :201-205, `aspirate96/dispense96` :207-221, resource pickup/move/drop :223-230) plus `request_tip_presence()` reading the handler's head state (:232-239) and `can_pick_up_tip(...) -> True` (:241-242).
- `STARChatterboxBackend` — `external/pylabrobot/pylabrobot/liquid_handling/backends/hamilton/STAR_chatterbox.py` (imported by the runner at `praxis/backend/core/simulation/chatterbox_runner.py:28-30`).

### 2.2 Can it validate arbitrary generated calls?

Yes, with the right mental model of *where* validation lives:

- The backend validates nothing — it prints. The validation lives in the **LiquidHandler/tracker layers above it**: `TipTracker` raises `NoTipError` on remove-without-tip and `HasTipError` on double-pickup (`external/pylabrobot/pylabrobot/resources/tip_tracker.py:65,:92,:105`); `VolumeTracker` raises `TooLittleLiquidError`/`TooLittleVolumeError` on over-draw/over-fill (`external/pylabrobot/pylabrobot/resources/volume_tracker.py:92,:105,:136`). Deck-layout errors (`ChannelsDoNotFitError`, `NoChannelError`) come from `liquid_handling/errors.py:4-18`. Strictness is process-global and defaults to `WARN` (`external/pylabrobot/pylabrobot/liquid_handling/strictness.py:13`, settable via `set_strictness` :15-19) — a verification harness likely wants `STRICT`.
- The harness around it is real and battle-tested: `ChatterboxProtocolRunner` (`praxis/backend/core/simulation/chatterbox_runner.py:453-588`) with `CHATTERBOX_REGISTRY` mapping machine types → `(name, class, kwargs)` entries — LiquidHandler gets both generic + STAR backends (`chatterbox_runner.py:140-161`), plus 14 scaffolded lazy-imported backends for other machine types (:164-202). `DeckFactory.create_setup` builds carrier-based Hamilton decks (`STARLetDeck` + `TIP_CAR_480_A00`@rails=1 + `PLT_CAR_L5AC_A00`@rails=9, :351-413) or slot-based OTDeck (:415-445). `run_single` captures `{type(e).__name__: e}` + full traceback + `execution_time_ms` into `BackendResult` (:539-588, models :97-119), bypassing decorators so no DB/context is needed (:562-565).
- Tip tracking, volume tracking, error raising: all exercised, because they're PLR-core behavior independent of backend. Post-condition *assertions* (e.g. "volume actually left A1") are not part of the harness today — `BackendResult` is pass/fail-on-exception only. A training-data verifier can add them cheaply by reading `lh.get_mounted_tips()` / well `volume_tracker.get_free_volume()` after the sequence, and `LiquidHandler.serialize_state/load_state` (:214-261) give an exact before/after diff surface.

### 2.3 Speed — measured, not estimated

Ran `uv run python tests/protocols/test_chatterbox_execution.py` (the file's own conftest-bypassing runner, `tests/protocols/test_chatterbox_execution.py:349-389`): **10/10 protocol-backend pairs passed, 14.2 s wall total including ~4 s of `uv run` interpreter startup** — i.e., roughly 0.5-1 s per protocol execution, dominated by deck construction. Extrapolation: ~1000 single-call-sequence examples ≈ minutes single-process, embarrassingly parallel across workers if needed. CI-scale: trivially yes. Caveat: the pytest path pulls `tests/` conftest; the manual-runner pattern (or a dedicated `scripts/` harness importing `chatterbox_runner` directly) avoids that entirely.

### 2.4 Minimal execution-verify harness shape

```python
from praxis.backend.core.simulation.chatterbox_runner import (
    CHATTERBOX_REGISTRY, DeckFactory, BackendResult)   # chatterbox_runner.py:140, :305, :97

async def verify(call_sequence, backend="LiquidHandlerChatterboxBackend"):
    setup = DeckFactory().create_setup(                       # :313-336
        backend, {"source_plate": "Plate", "dest_plate": "Plate", "tip_rack": "TipRack"})
    lh, deck = setup["machine"], setup["deck"]                # LiquidHandler w/ STARLetDeck
    await lh.setup()
    try:
        for fn, args, kwargs in call_sequence:
            await getattr(lh, fn)(*args, **kwargs)            # e.g. ("transfer", ([src],[dst]))
        return {"passed": True,
                "mounted_tips": lh.get_mounted_tips(),        # post-condition hooks:
                "state": lh.serialize_state()}                # exact before/after diff
    except Exception as e:
        return {"passed": False, "error": f"{type(e).__name__}: {e}"}
    finally:
        await lh.stop()
```

Imports resolve without SQLAlchemy (the runner deliberately inlines machine-type detection to avoid `backend.core.__init__` → db, `chatterbox_runner.py:46-60`). One caveat: `chatterbox_runner` imports `praxis.common.type_inspection` (:49) — fine for CPython CI, but see GAPS #6 for the Pyodide/browser direction.

---

## 3. Protocol fixtures inventory

Two distinct corpora; the task's premise conflates them:

**A. `tests/fixtures/protocols/` — 6 files** (`__init__.py`, `conditional.py`, `loop_based.py`, `multi_machine.py`, `simple_linear.py`, `test_itemized_args.py`). Four async protocol functions using **string annotations and no imports** (`simple_linear.py:11-16`: `lh: "LiquidHandler"`, plus a duplicated `SIMPLE_TRANSFER_SOURCE` string literal :33-45 for graph-extraction testing). Call style uses positional volume (`lh.aspirate(src, volume)`, `loop_based.py:31`). **They are not ChatterBox-runnable**: (a) the execution test's discovery points elsewhere (`tests/protocols/test_chatterbox_execution.py:38` → `PROTOCOLS_DIR = .../"praxis"/"protocol"/"protocols"`), (b) `load_protocol_function` requires `_protocol_metadata` or `__wrapped__` (:67-68), which none have, (c) no test consumes them as executables — their consumers are static-analysis tests (`grep`: `tests/utils/test_computation_graph.py`, `tests/core/test_tracers.py`, `tests/core/test_precondition_resolver.py`). As NL-pairing material they're thin (4 examples) but their *patterns* (linear/conditional/loop/multi-machine) match the scoping doc's claim (`:31`).

**B. `praxis/protocol/protocols/` — the real runnable corpus: 6 `@protocol_function` protocols** (`simple_transfer.py`, `serial_dilution.py`, `selective_transfer.py`, `plate_preparation.py`, `kinetic_assay.py`, `plate_reader_assay.py`). These carry real PLR type hints, `param_metadata`, keyword-call style (`vols=[volume_ul]`, `simple_transfer.py:105-106`), and are exactly what `TestRealProtocols` parametrizes over (`test_chatterbox_execution.py:333-346`; measured 10/10 passing in §2.3). This is the seed corpus the synthetic pipeline should imitate stylistically.

---

## 4. PLR docs corpus

**58 notebooks total** under `external/pylabrobot/docs/` (counted via find). Breakdown:

| cluster | count | LH-relevant? |
|---|---|---|
| `user_guide/00_liquid-handling/**` | 16 | **core corpus** — `basic`, `mixing`, `moving-channels-around`, `container_no_go_zones`, `tutorial_tip_inventory_consolidation`, `hamilton-star/*` (9: 96head, autoload, core-grippers, foil, liquid-classes, surface-following, x/y/z-probing), `opentrons/ot2/*` (2), `plate-washing/biotek-el406` |
| `user_guide/01_material-handling/**` | 16 | marginal (centrifuge/storage/temp/heating; arm PF400) |
| `user_guide/02_analytical/**` | 12 | plate-reader reads pair with LH transfer steps (12: plate-reading ×11 incl. byonoy, scales ×1) |
| `user_guide/machine-agnostic-features/**` | 6 | partial (logging/validation relevant to verification semantics) |
| `cookbook/*.ipynb` | 2 | 1 (`star_movement_plate_to_alpaqua_core`) — LH + movement; `slack_notifications` not |
| `resources/**/*.ipynb` | 6 | indirect (carriers, plate quadrants, resource-stack — grounding vocab, not calls) |

Scoping doc said "59 example notebooks" (`:30`); actual count is **58**, and its directory list omitted `01_material-handling` and `machine-agnostic-features`. Characterization: code-first notebooks with prose cells interleaved — good raw material for NL-pair synthesis, but note several Hamilton-star notebooks require hardware context (probing/grippers) that doesn't map to simulator-verifiable calls; filter those out at pairing time. `community-protocols/` remains an index page only (`docs/community-protocols/index.md`), confirming the scoping doc's skepticism (`:32`).

---

## 5. Web-repl serving substrate (post-Coxswain landing)

### 5.1 Channel wiring — done

`web-repl/shell/coxswain-shell.js` (W3, injected only under `--with-coxswain`, header comment :1-22):

- Dedicated channel: `const CHANNEL_NAME = "praxis_coxswain"` (:36) — never reuses `praxis_repl`/`praxis_viz` (NFR-4, per comment :13). All traffic goes through typed envelopes: `buildEnvelope`/`assertValidEnvelope` from `shell/coxswain/envelope.js` (:25, used at :167, :294); foreign-session messages dropped (:299).
- Kinds seen: outbound `coxswain.user_command` (:275), `coxswain.execute_request` (:243); inbound `coxswain.outcome` → failure card (:302-317), `coxswain.system` (:319), `coxswain.hello`/`hello_ack` handshake (:323-325); unknown kinds render a visible system line, never silence (:330).
- `turn_id` minted once per submission at input capture, before any parse work (:265-286). Parse layer is a clearly-marked DEMO STUB mirroring golden-corpus regexes (:52-81); execution is acknowledged locally with "kernel guards pending their bridge" (:244-246).
- Panel: Chat/Visualizer tabs wrapping `<body>` in plain CSS (:102-146); visualizer iframe loads `../visualizer/index.html?coxswain_session=` (:206) with the highlight subscriber shipped as conditionally-staged `overlay/assets/coxswain/viz_highlight.js` (W4, deviation D-C, spec `:33-36`).

Kernel side mirrors this in Python: `coxswain/src/coxswain/execute.py` (kernel guards), `relay_config.js` endpoint baked at build time (`build_repl.py:1291-1312`).

### 5.2 Where a Transformers.js inference Worker mounts

There is **no inference worker yet** — the only worker in the stack is JupyterLite's own Pyodide kernel worker. The natural mount, consistent with everything above:

- Code: a new ES module under `overlay/assets/coxswain/` (e.g. `parse_worker.js` + loader) — this directory is already flag-gated (`stage_overlay` skips any path containing "coxswain" unless `include_coxswain`, `build_repl.py:558-566`) and sha-tracked (`collect_coxswain_assets`, see below). Spawn from `coxswain-shell.js` with `new Worker(new URL(...), {type:"module"})`; keep the worker off the safety path exactly like the demo stub — the kernel re-derives everything (`coxswain-shell.js:54-56` comment; spec FR/NLU-only-at-parse layering).
- Transport: either the worker posts results to the main thread for envelope-wrapping onto `praxis_coxswain`, or uses `BroadcastChannel` directly (workers have same-origin access); either way `assertValidEnvelope` stays the gate.
- Kernel-side counterpart follows the established fetched-Python-module pattern (`overlay/assets/python/praxis/viz/{transport,browser}.py` — present on disk; ADR tree `decisions/260817_repl-layout-and-delivery-mechanism.md:117`): a small `coxswain` kernel module would ship the same way if grounding moves into Pyodide (see GAPS #6).

### 5.3 Build staging path + manifest/sha tracking — done, copy this pattern

`--with-coxswain` already exists end-to-end (`build_repl.py:1213-1222`):

1. `run_build_manifest(with_coxswain=True)` threads the flag to `build_manifest.py` (:504-510).
2. `stage_overlay(include_coxswain)` stages `overlay/assets/coxswain/*` (currently `coxswain.css`, `viz_highlight.js`) (:551-578).
3. `stage_coxswain_shell(out_dir)` stages `shell/coxswain-shell.js` + `shell/coxswain/*` (17 modules), asserting the nine required DOM-free modules exist and skipping `__tests__/` (:847-895).
4. `assert_dist_complete` requires the shell entry, all nine modules, css, and `viz_highlight.js` under the flag (:994-1011).
5. AC-11 enforcement: default builds assert **zero** paths matching `*coxswain*` anywhere in dist (`assert_no_coxswain_anywhere`, :1056-1068) and no coxswain `<script>` in the vendored visualizer (:1071-1091); flagged builds assert **exactly one** injected tag (:1121-1140); `visualizer-augmentations/index.js` byte-identity holds in every mode (:1027-1053).
6. Manifest tracking: `build_manifest.py` defines `COXSWAIN_ASSET_SUBDIR="coxswain"`, `COXSWAIN_ASSET_SUFFIXES={".js",".css"}` (:62-63) and `collect_coxswain_assets()` emits `{path, sha256}` entries enumerated from disk (:188-212) into a **separate key** the bootstrap loader never reads (:57-61 rationale).

The ADR pattern being copied is §2.3's three-detector design (D1 shell-injected `praxis_git_sha` for whole-deployment staleness; D2 per-entry `manifest.json` sha256 for per-file integrity, "no source file is ever stamped"; D3 AST import-coverage test in CPython CI — `decisions/260817_repl-layout-and-delivery-mechanism.md`, §2.3 table and following paragraphs). A model-artifact directory should extend this with a **wheels-shaped array** (the only existing shape carrying `bytes` + provenance `source_sha`: `build_manifest.py:168-182` and manifest shape :14-21), not the js/css sources key — see GAPS #4.

---

## 6. Parse-source seam (W3 landed)

Exact interface the fine-tuned parser must satisfy — `coxswain/src/coxswain/parse_source.py`:

- **Protocol**: `ParseSource.parse(self, utterance: str) -> ParsedCall` (:45-50), `@runtime_checkable`. That is the entire surface; the docstring states the Transformers.js implementation arrives as "an additive replacement with no call-site changes" (:4-8).
- **Stub**: `FixtureParseSource` serves the golden corpus deterministically (:70-157); refuses an empty/missing corpus loudly (:83-93); normalizes utterances (trim/collapse/casefold, :53-56); raises `ParseError` listing known utterances rather than guessing (:39-42, :135-141); hands out fresh copied `params` dicts per request (:143-151).
- **Output type**: `ParsedCall` frozen dataclass — `name: str, receiver_type: str, params: dict[str, Any], missing_required: tuple[str, ...], unresolved_slots: tuple[UnresolvedSlot, ...]` (`coxswain/src/coxswain/fft/context.py:48-61`); `UnresolvedSlot{arg_name, reference, resource_type}` (:37-45). Downstream: `missing_required` drives FFT cue 1, `unresolved_slots` drives cue 2 via `GroundingSource.resolve_slot(reference, resource_type) -> tuple[KernelInstance, ...]` (:67-76); the whole gate pass takes a frozen `GatePassContext{turn_id, session_id, card_revision, probe, kernel_state, instance_source, audit, ts}` (:119-136).
- Constraint: pure stdlib, no `js`, no `praxis.*` (NFR-1/NFR-2, module docstring :15-16; enforced structurally by `coxswain/tests/test_import_boundary.py`).
- **Fixture location correction:** the task brief said `tests/fixtures/parsed_calls/*.json`; actual location is **`coxswain/tests/fixtures/parsed_calls/`** (default dir derived at `parse_source.py:32-34`). Six fixtures: `read_only.json`, `reversible_single_target.json`, `reversible_multi_target.json`, `irreversible_discard_tips.json`, `aspirate_source_key.json`, `long_descriptor_truncation.json`. Shape (all fields validated at load, required set at :36): `{"utterance", "name", "verb", "receiver_type", "params", "missing_required": [], "unresolved_slots": [{arg_name, reference, resource_type}], "expected_phrase", "_comment"}` — e.g. `aspirate_source_key.json` maps `"aspirate 10 uL from A1"` → `params {"source": "A1", "volume_ul": 10}` with `expected_phrase "aspirate from A1"`. The JS demo stub intentionally mirrors three of these (`coxswain-shell.js:53-56`), and FR-3 parity tests pin both language implementations to the same corpus (RISK-8 drift mitigation, :10-14).

So the fine-tune's *contract* is already fixed: given an utterance, emit `{name, receiver_type, params, missing_required?, unresolved_slots?}` — note this is a **superset of the scoping doc's tool-schema JSON** (`:115-127`): the tier/verb/effect metadata lives in `TOOL_SCHEMA` keyed by `name` (`tier_of`, `tool_schema.py:147-150`), so the model need not predict risk metadata at all.

## 7. Wheel/kernel constraints on a ~288 MB lazy-loaded asset

From `web-repl/scripts/build_repl.py` (all verified this session) and the wheel-build spec (`.praxia/docs/specs/260817_spec-wheel-build-plr-upgrade.md`):

- **Total-site budget, not per-file limits.** No per-asset size cap exists anywhere in the build scripts. The operative constraint is GitHub Pages storage: `prune_pyodide_bundle`'s docstring targets "headroom against the 1 GB limit" (`build_repl.py:706-740`, specifically :713). Measured baselines recorded in-tree: full vendored Pyodide bundle was 512 MB before pruning (:706-712), and `--allow-cdn` produced a "byte-comparable 479 MB site" (:1180-1182). Adding ~288 MB lands the site near ~800 MB — inside 1 GB but consuming most remaining headroom; deploy-workflow artifact upload cost scales with it.
- **CDN policy (GATE G5):** builds must vendor everything; the gate greps dist for `cdn.jsdelivr.net` and wants zero hits (:50-73). `--allow-cdn` changes only where the *build fetches* Pyodide, never how the site loads it (:177-216, :1173-1186); `assert_pyodide_is_local` fails the build if runtime `pyodideUrl` is remote or missing (:258-298). **Consequence for FunctionGemma: the ~288 MB must ship inside dist/ (or behind a deliberate policy change); there is no CDN escape hatch that survives G5.**
- **Offline runtime is absolute:** `disablePyPIFallback: true` makes un-vendored runtime deps *unobtainable*, not slow — the piplite-wheel assertion exists because that failure mode was silent (:391-451). Any model-fetch-at-first-use design must therefore fetch from the site's own origin.
- **Zero tracked binaries rule:** "Do NOT commit the .whl — R6/R8 require zero tracked wheels repo-wide" (:49, :448-450). A committed model checkpoint violates the same principle; it must arrive via a fetch script writing into a gitignored vendor/ dir, exactly like `fetch_pyodide.py` / `fetch_vendored_wheels.py`, then be pinned in a manifest with sha256+bytes.
- **Lazy-load precedent is normative:** the ADR/scoping-doc lesson (delete `PyodidePoolService.preWarm()`; scoping doc `:232`) — the model must not join base page load. Current coxswain assets are tiny (css + one JS subscriber); the manifest's coxswain key tracks them individually, so a large binary needs the wheels-style entry (below).
- **Base-path discipline:** subpath deploys rewrite `HOST_ROOT` at build time (`apply_base_path`, :628-681) because the kernel worker has no `document.location`; any hardcoded model URL in a notebook or kernel-side code needs the same treatment. Staged-copy-only rewrites are the house pattern (never mutate tracked sources, cf. `stamp_loader_shas` :585-622).

**Manifest extension shape to copy** (recommendation, consistent with existing arrays): a `"models"` array mirroring `wheels` — `{package/name, filename, version_or_rev, source_sha, sha256, bytes}` (`build_manifest.py:168-182` shape) — plus a fetcher script and a boot-time or first-use integrity check through the D2 transport. The current `coxswain_assets` key only accepts `.js/.css` (:62-63) and carries no `bytes` field; do not shoehorn a 288 MB blob into it.

---

## GAPS/RISKS

1. **TOOL_SCHEMA ↔ vendored-PLR drift (high, concrete).** `coxswain/plr/tool_schema.py` declares `mix`, `blow_out`, `touch_tip` (:103-111) and `dispense_to_waste` (:83-90); the vendored `LiquidHandler` has **no such methods** (verified via `inspect` + grep, §1.4). Training-data generation against the schema would produce calls that fail execution verification — caught, but wasteful — or worse, force ad-hoc dispatch shims. Next spec needs a reconciliation step: generate candidate schemas from `inspect_machine_methods`/LibCST and assert `TOOL_SCHEMA ⊆ vendored API`, pinned to the PLR wheel's `PLR_SOURCE_SHA` (mechanism exists: `build_manifest.py:77-79`).
2. **Schema generation is not free (medium).** Neither `plr_inspection` nor `plr_static_analysis` emits method-level function-calling schemas today (`plr_inspection/static.py` is a placeholder; runtime discovery is deprecated). Nearest reusable piece is `services/introspection.py:19-80`. Budget a small generator + type-mapping layer; do not assume "extractable as-is" from the scoping doc's phrasing (`:18`).
3. **Execution verification is pass/fail-only (medium).** `BackendResult` captures exceptions, nothing asserts desired post-states (`chatterbox_runner.py:97-105`, :568-582). For training-data QA, extend the harness with tracker-based post-conditions (§2.4) and consider `set_strictness(STRICT)` (`strictness.py:15-19`) so WARN-level anomalies fail loudly.
4. **Model-artifact delivery has no home yet (high for the serving phase).** Manifest coxswain tracking covers only `.js/.css` with no size/provenance fields (`build_manifest.py:62-63`, :188-212); R6/R8 forbid committing the binary; G5 forbids CDN loading; Pages budget ~479 MB used of 1 GB. Needs: fetch-script + `models` manifest array + lazy first-use integrity check (§7 recommendation). Also unresolved: LoRA-adapter hot-swap support in Transformers.js (already flagged open in the scoping doc `:149`).
5. **Naming/location drift between docs and reality (low but recurring).** `ChatterBoxBackend` is dead (`chatterbox_backend.py:1-5`); fixtures live at `coxswain/tests/fixtures/parsed_calls/` not `tests/fixtures/parsed_calls/`; notebook count is 58 not 59. The next spec should cite the corrected names to avoid sending an implementer at tombstones.
6. **Kernel-side grounding path is unbuilt in browser mode (medium).** `chatterbox_runner` and `plr_static_analysis` are CPython+SQLAlchemy-free-ish but import `praxis.*` and full `pylabrobot` — neither ships in Pyodide today (ADR §5.2: no import path between `praxis/` and `web-repl/`; only build-time pinned copies). If cue-2/cue-3 grounding runs inside the tab's kernel (as the scoping doc's composition assumes, `:230`), the grounding logic must be re-shipped as a small fetched module like `praxis/viz/` — `coxswain`'s NFR-1/NFR-2 purity rules (`context.py:9-11`) suggest the authors already anticipate this, but no such module exists in `overlay/assets/python/` yet.
7. **Corpus asymmetry (low).** Runnable seed corpus is 6 real protocols (§3-B) + 16 LH notebooks; the 4 `tests/fixtures/protocols` files are static-analysis-only and use a stale positional-volume call style. Synthetic generation should imitate corpus B's keyword style (`vols=[...]`) to stay execution-verifiable.
8. **CI wiring for the new tests is specified but not verified here** — spec W1.0 requires `uv run pytest coxswain/tests -q` and `bun test web-repl/shell/coxswain` in repl.yml (`spec:27-29`); confirming the workflow actually carries them is follow-up, not done in this read-only pass.
