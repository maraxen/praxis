---
title: 'Adversarial challenger review: Coxswain Phase 2 FunctionGemma copilot pipeline spec'
description: 'CHALLENGER-role findings against 260825_coxswain-phase-2-functiongemma-copilot-p.md. All file:line claims in the spec were re-verified against the tree on repl-fresh-boot; findings are ranked blocker/major/minor with cites and concrete fixes. No wholesale rewrite proposed.'
status: review
task_id: 260825_copilot_pipeline_spec
date: '260825'
---

# Challenger review — 260825_coxswain-phase-2-functiongemma-copilot-p.md

Method: read the phase-2 spec, its three bound inputs (scoping 260824, recon 260825, research
260825) and the landed MVP spec (260824), then re-verified every cheap file:line claim against
the working tree on `repl-fresh-boot`. Findings only; no rewrite proposed.

**Cites that checked out** (so the implementer knows what NOT to distrust): `tool_schema.py`
phantom entries at :83-90/:103-111 and `tier_of` :147-150; `parse_source.py` protocol :45-50 and
`_REQUIRED_FIELDS` :36; vendored LiquidHandler has no `mix`/`blow_out`/`touch_tip`/
`dispense_to_waste` (grep exit 1); `chatterbox_runner.py` DeckFactory :305/:313, run_single
:539; 58 notebooks, 6 runnable protocols, 6 golden fixtures;
`build_repl.py` coxswain staging skip ~:558-566 and `assert_no_coxswain_anywhere` :1056;
wheels manifest shape `{package, filename, version, source_sha, sha256, bytes}`
(`build_manifest.py::collect_wheels`); W1.0's CI job exists (`repl.yml:237-277`, runs
`uv run --no-sync pytest coxswain/tests -q` + `bun test web-repl/shell/coxswain`).

---

## Blockers

### C-B1 [blocker] INTERNAL COHERENCE / TECHNICAL FALSITY — the prediction-target contract is unsatisfiable as written

Cite: spec §4 (:76-78 "The model predicts `{name, params, missing_required?, unresolved_slots?}`
ONLY") vs D6 (:39-40, assistant supervision as FunctionGemma-native `tool_calls`) vs D7 (:41,
clarify supervision as NL turns) vs the ParseSource contract (recon §6; `parse_source.py:45-49`
returns `ParsedCall`).

Why it fails:

1. **FunctionGemma's native call syntax has no fields for `missing_required` or
   `unresolved_slots`.** The completion format is `call:name{arg:<escape>value<escape>}` plus an
   optional plain-text turn (research §1, §7). A `tool_calls` supervision target can carry name +
   arguments and nothing else. So D6's format cannot train the five-field prediction target §4
   promises.
2. **They also cannot be derived today.** `ToolSpec` (`tool_schema.py:27-38`) carries `{name,
   verb, receiver_type, risk_tier, effects, to_waste}` — zero parameter metadata. P2.0's ACs
   produce a required-param table (AC-2.0.3) but nothing produces arg *types* or per-slot
   `resource_type`, both of which `UnresolvedSlot{arg_name, reference, resource_type}` requires.
   Meanwhile cue 1 consumes `call.missing_required` verbatim (`fft/cues.py:156`) and today that
   value is supplied exclusively by fixture JSON (`parse_source.py:116`). Deleting the fixture
   stub deletes the only producer of these fields, and no DAG item replaces it.
3. **D7's two clarify classes have no landing on the serving side.** An out-of-surface refusal or
   an incomplete-slot "which argument is missing?" NL turn cannot be expressed as a `ParsedCall`
   (no message/refusal channel), so `ParseSource.parse()` has no defined return for exactly the
   examples D7 mandates training on. Worse, the incomplete-slot class duplicates deterministic
   cue 1's job (F1, FR-8's clarify re-entry), and D10 locks clarification re-entry to the
   deterministic FFT/cards — so the spec simultaneously trains the model to do cue 1's job in
   free text and forbids model output from doing any gate work.

An implementer hits this wall at P2.3 (what does the generator emit?) and again at P2.8 (what
does the worker post?).

Fix shape: one explicit decision, recorded as a new D-item, choosing between (a) custom
supervision fields rendered into the completion (deviating from byte-native mobile-actions shape,
which weakens AC-2.5.1), or (b) deterministic post-parse derivation — P2.0 extends `ToolSpec`
with required/type/resource-type tables and defines a slot-classification rule over string-valued
resource args, the model predicts ONLY `{name, params}`, and D7's negatives become
"emit-no-tool_call" cases whose serving representation is a typed clarify result (a new return
kind alongside `ParsedCall`, specified in P2.9). Option (b) preserves F1/F5/F6 cleanly.

### C-B2 [blocker] MISSING WORK / INTERNAL COHERENCE — three incompatible param-name vocabularies, no owner

Cite: AC-2.0.3 (:113, required params derived to match `inspect.signature`) vs AC-2.9.1 (:172-173,
existing fixture corpus passes UNCHANGED through the model-backed source) vs D6 training data.

Why it fails: the fixtures use a normalized vocabulary that is not PLR's signature vocabulary:
`aspirate_source_key.json` → `params {"source": "A1", "volume_ul": 10}` (PLR:
`aspirate(resources, vols)`); `reversible_single_target.json`/`reversible_multi_target.json` →
`destination` (PLR `transfer`: `targets`); `read_only.json` → `wavelength_nm`; discard fixtures →
`{"what": ..., "at": ...}`. Verified across all six fixtures. If P2.6 trains on
signature-derived names (the only thing AC-2.0.3 produces), the worker emits `vols`/`targets`,
and AC-2.9.1's contract regression fails on param-name mismatch. If instead training uses fixture
names, AC-2.0.3's table is disconnected from everything downstream and execution dispatch has no
map back to PLR kwargs. Note there is NO dispatcher anywhere today: `execute.py:163` takes an
abstract `executor: Callable[[ParsedCall], Any]`, and `grep vols coxswain/src` returns zero hits —
the normalized→PLR translation layer simply does not exist, and no P2.x item owns creating it.

Fix shape: extend P2.0 to canonize the ParsedCall param namespace explicitly: for each schema
entry, a declared mapping `(schema param name ↔ PLR kwarg)` plus which names are symbolic
references; regenerate fixtures or annotate them as the canonical vocabulary; make the generator
(P2.3/P2.4), the training corpus (P2.5), and AC-2.9.1 all consume that one table.

---

## Majors

### C-M1 [major] SAFETY HOLES — under-predicted `unresolved_slots` reaches confirm ungrounded, and the only backstop is optional

Cite: recon §6 ("unresolved_slots drives cue 2 via `GroundingSource.resolve_slot`"); AC-2.9.4
(:178-179, kernel-side grounding module ships "otherwise documented why not needed yet"); F1.

Why it fails: cue 2 fires only on slots the parse layer reports. If the model fills a
resource-typed param with a symbolic string but reports zero unresolved slots (under-prediction —
precisely what a 270M distill will sometimes do, and precisely what B1 shows has no supervision),
cue 2 passes trivially, cue 3 evaluates preconditions against a call whose arguments are English
phrases, and the proposal card renders a literal call containing an unresolved reference one
Confirm away from dispatch. The whole W-chain rests on slot lists being trustworthy, yet the spec
makes them a model output AND leaves the kernel-side re-derivation/grounding bridge conditional.
This is the one path where model quality directly erodes the MVP's deterministic-guarantee story.

Fix shape: invert AC-2.9.4's default. Kernel-side validation that every resource-typed arg either
resolves against live state or exits `clarify:*` must be mandatory before propose; the worker's
slot list may be advisory only. If the grounding module is genuinely deferrable, the spec must
say what kernel-side check substitutes in the meantime (e.g., refuse-to-propose on any
non-literal-looking resource param).

### C-M2 [major] INTERNAL COHERENCE — `clarify:parse_failed` is outside the closed disposition vocabulary

Cite: AC-2.8.2 (:165-166) introduces `clarify:parse_failed`; MVP spec §2.4 (:441-443) declares
`disposition` a CLOSED vocabulary (`continue`, `pass`, `blocked:*`, `clarify:incomplete |
not_found | disambiguate | precondition`, `override:precondition`, `aborted:drift`) enforced by
W5's audit writer and pinned by tests.

Why it fails: phase 2 silently extends a vocabulary another spec declares closed and test-enforced,
with no item owning the amendment, no envelope-kind addition listed (worker progress/result kinds
are new too — benign since `envelope.js` accepts any kind string, but the shell's handler switch
and the audit writer are not), and no statement of whether a parse-failed turn writes ANY
`FftDecision`. If it does not, there is an audit-trail gap for every failed parse (turn minted,
nothing recorded but transcript); if it does, the writer rejects the unknown disposition.

Fix shape: add an explicit "vocabulary amendment" sub-item to P2.8/P2.9 naming the new
disposition(s) and kinds, updating the audit-writer allowlist and its tests, and stating the
audit semantics of parse failures.

### C-M3 [major] DEPENDENCY ERRORS — P2.2 is declared dependency-free but its central contract is undefined and schema-shaped

Cite: §5 table row P2.2 (:89, depends on "—"), AC-2.2.1/:124 and AC-2.2.3 (:128-129, "intent
record" slot-agreement axis), AC-2.3.2 (:135, generators emit "intent record").

Why it fails: "intent record" is never defined anywhere in the spec — no field list, no owner,
yet four items consume or produce it (P2.2, P2.3, P2.4, P2.5). Its content is necessarily keyed
to reconciled verbs/effects/receiver types (post-conditions like mounted-tips delta need per-verb
effect semantics), so building P2.2 truly in parallel with P2.0 means building against phantom
verbs (`mix`, `blow_out`, …) and reworking after reconciliation. This is a hidden missing edge
(P2.2 ← P2.0, at least soft) plus an unspecified shared contract — the same failure mode the MVP
spec's W1 split was invented to prevent (its §6.1 rationale).

Fix shape: define the intent-record shape in P2.0 (it is a schema artifact) or in a short P2.2
preamble paragraph; add the P2.2←P2.0 edge to the DAG table.

### C-M4 [major] TECHNICAL FALSITY / MISSING WORK — the delivery stack has three unnamed load-bearing pieces

Cite: F3 (:53-56), G5 (recon §7), P2.7 (:94), AC-2.1.2 (:119-121); research §1 (gated repo), §6
(Physics Playground imports transformers.js from jsDelivr CDN).

Why it fails:

1. **The inference LIBRARY has no delivery path.** G5 forbids runtime CDN, but the proven
   precedent (Physics Playground) loads `@huggingface/transformers` from jsDelivr; web-repl has
   no package.json/npm/node by design. Transformers.js + onnxruntime-web (WASM and WebGPU
   bundles, several MB) must be origin-local, but P2.7 covers MODEL artifacts only. No item owns
   vendoring the JS runtime, and the `models` manifest array does not fit it (not a single binary).
2. **`fetch_models.py` has no source to fetch from.** Our fine-tune will not be published
   (§6 non-goals), the base repo is gated (license click-through + token, research §1), so where
   does the build-time fetch URL point? An internal bucket, a GitHub Release asset, a Space?
   Unnamed, and Gemma-license compliance for hosting a derivative is waved at P2.6 only via the
   risk table.
3. **CI home for the new tests is unowned.** `training/` is a NEW uv workspace member
   (`pyproject.toml:43-44`, members = ["coxswain"]) with heavy deps (torch/trl/optimum). The
   existing coxswain CI job deliberately runs `uv run --no-sync` (`repl.yml:271`) and would not
   collect `training/tests`. AC-2.0.x and AC-2.1.2 say "CPython CI" without saying which job, and
   off-the-shelf checkpoint evaluation needs gated-weight download (HF token secret) — cold
   download of a 426 MB+ artifact inside AC-2.1.2's "<2 min" budget is impossible; the escape
   hatch, "recorded-artifact mode," tests recorded outputs rather than the harness, which largely
   defeats AC-2.1.2's purpose.

Fix shape: give P2.7 explicit sub-deliverables for library vendoring (with its own manifest
treatment) and artifact-hosting decision; add a CI wiring sub-item (new job or matrix entry) for
`training/` with a stated token/secret plan; redefine AC-2.1.2's CI mode as
"small-fixture harness self-test + recorded outputs labeled as such".

### C-M5 [major] INTERNAL COHERENCE — D4's fp16 fallback cannot be delivered under F3/G5 and the storage budget

Cite: D4 (:38, "q4f16 primary, fp16 fallback for weak WebGPU; exactly one dtype cached per device
class") vs F3/G5 (site-origin-only delivery) vs risk table :190 (~479 MB site + 426 MB model ≈
905 MB of 1 GB — i.e., ONE artifact budgeted).

Why it fails: artifacts ship inside dist from site origin (recon §7: "there is no CDN escape
hatch that survives G5"; offline runtime is absolute). Two dtypes shipped = ~1.48 GB > Pages
limit; one dtype shipped = the "per device class" policy is false — devices with weak/no WebGPU
get q4f16 on WASM (slow, and fp16-on-CPU is worse) with no fallback artifact to fetch. P2.7.3's
go/no-go ("on q4f16 vs fp16") implicitly picks ONE globally, contradicting D4's wording.

Fix shape: reword D4 to "exactly one dtype ships, globally, chosen at P2.7.3; unsupported-device
degrade is a loud system line, not a second artifact" — or own the budget math for shipping both
(including tokenizer/config/runtime bytes, see C-m8) if per-device-class is real.

### C-M6 [major] ESTIMATION TRAPS — D8 thresholds are statistically hollow at the specified sample sizes

Cite: D8 (:42), AC-2.1.1 (:116-117, ≥50 pairs, ≥8 clarify examples), AC-2.6.2 (:150-151).

Why it fails: on n=50, accuracy moves in 2-point quanta and the binomial 95% CI is roughly ±14
points; clarify recall measured on ≥8 examples moves in 12.5-point quanta; clarify precision on
any stratified slice that small is mostly noise. Thresholds "set empirically from baseline-measured
spread" (§9) anchor the fine-tune gate to a DIFFERENT model's variance and freeze before any
fine-tune result exists (P2.5.4 precedes P2.6) — so the promotion gate is likely either vacuous
or unreachable, and as written cannot be verified meaningfully.

Fix shape: size the eval split for the decision (even a rough power note per class), define the
clarify metrics operationally (what counts as an emitted clarification — any non-tool_call turn?
matched to the expected missing-arg name?), and permit one threshold revision at P2.6 with a
recorded justification instead of pretending P2.5.4 numbers are final.

### C-M7 [major] DEPENDENCY ERRORS — the export/delivery spike sits AFTER the expensive step it de-risks

Cite: §5 critical path (:98, P2.6 → P2.7), risk table :188 ("ONNX export friction for gemma3_text
post-v4 restructure"), research doc Open question 2 ("Prototype ONNX export … early").

Why it fails: the spec's own risk table says ONNX export of a fine-tuned gemma3_text checkpoint is
unproven, and the bound research doc explicitly recommends prototyping the export early. As
sequenced, the entire corpus + fine-tune investment (P2.1-P2.6, the long pole) completes BEFORE
discovering whether the resulting checkpoint can be exported/served at all. Most of P2.7's
content (fetch script, models manifest array, integrity check, footprint beside live Pyodide,
tok/s measurement) is checkpoint-independent and can run against the community
`functiongemma-270m-it-ONNX` export today.

Fix shape: split P2.7 into P2.7a (delivery plumbing + footprint, parallel branch off P2.0/P2.1)
and P2.7b (fine-tuned-checkpoint export parity, depends on P2.6). Critical path then de-risks
serving reality months of work earlier.

---

## Minors

### C-m1 [minor] INTERNAL COHERENCE — D9's regeneration blanket contradicts hand-authored provenance, and AC-2.1.1's arithmetic breaks if P2.0 grows verbs

D9 (:43) makes the eval set "regenerable … never a one-time artifact," but provenance=golden
pairs are human-reviewed by definition (AC-2.1.1) and cannot be regenerated, only re-authored.
Also: coverage math is 20 verbs × 2 + ≥8 clarify = 48 ≤ 50 today; if reconciliation ADDS the
real-but-unlisted methods (`return_tips`, `move_tips`, `pick_up_tips96`, `drop_tips96`,
`aspirate96`, `dispense96` — all present on the vendored handler per recon §1.4), coverage
requires >50 pairs and AC-2.1.1 becomes unsatisfiable as written. Fix: exempt golden provenance
from D9's regeneration clause and make AC-2.1.1's count derive from the reconciled verb count.

### C-m2 [minor] MISSING WORK — P2.0's subset assertion is asymmetric

AC-2.0.1 asserts TOOL_SCHEMA ⊆ vendored API. The opposite direction (vendored API ⊄ schema) is a
product decision nobody owns: entire workflow families (96-channel heads, tip return/move) exist
on the handler and are absent from the schema. Fine to exclude, but the exclusion should be a
recorded decision in P2.0, because it silently bounds the copilot's competence and the coverage
matrix. Fix: add an explicit include/exclude list deliverable to P2.0.

### C-m3 [minor] ESTIMATION TRAP — AC-2.5.1's "byte-identical developer scaffold" is ambiguous

mobile-actions prepends current date/time + day-of-week to the developer turn (research §2
dataset format); the formatting guide's trigger phrase is bare. "Byte-identical to formatting
guide example" cannot hold across rows if timestamps are injected, and whether Praxis wants date
injection at all is unstated. Fix: commit the exact scaffold template (and state that dates are
omitted) as part of P2.5.

### C-m4 [minor] MISSING WORK — worker lifecycle details unspecified for P2.8

No item specifies how session_id/turn_id reach the worker (spawn query? init message?), who owns
`seq` allocation, whether envelopes are wrapped in-worker or on the main thread (recon §5.2
allows both), or generation config (stop tokens `<end_of_turn>` + `<start_function_response>`,
max_new_tokens — Physics Playground caps at 128). Each is small; together they let two
implementations of P2.8 diverge. Fix: one paragraph in P2.8 fixing transport, seq ownership, and
decode config.

### C-m5 [minor] MISSING WORK — no import-boundary test for `training/`

F2 grants `training/` the right to import `praxis.backend.*`; nothing enforces the converse
boundaries: `coxswain/` must never import `training/`, staged overlay Python must never see it,
and browser bundles must never contain it. Mirror `coxswain/tests/test_import_boundary.py` as an
AST test owned by P2.0 or P2.2's first landing.

### C-m6 [minor] INTERNAL COHERENCE — AC-2.9.1's regression corpus contains zero hard cases

All six golden fixtures have `missing_required: []` and `unresolved_slots: []` (verified). The
"contract regression" therefore exercises only clean parses through the new source; the
interesting contract surface (slots, missing fields, refusal results per C-B1) has no fixture
coverage. Fix: extend the fixture corpus as part of P2.9 or scope the AC honestly.

### C-m7 [minor] ESTIMATION TRAP — AC-2.7.1's parity standard is unfalsifiable

"token-level or semantic-equivalent" lets a failing export pass review. Token-level greedy
equality on 20 fixed utterances is cheap and achievable when quantization is the only delta; pick
that, and treat deviations as go/no-go signals rather than "semantic equivalence."

### C-m8 [minor] STORAGE ARITHMETIC — headroom is thinner than the risk table states

Risk table :190 counts 479 MB site (measured WITH `--allow-cdn`, byte-comparable per recon §7)
plus one 426 MB model ≈ 905 MB, omitting tokenizer/generation-config files, the ORT WASM/WebGPU
runtime bundles (C-M4), and any fp16 residue. Realistic slack is well under the implied ~95 MB,
and deploy-artifact upload cost scales with every byte. Fold the full accounting into P2.7.3's
doc.

---

## Summary counts

- Blockers: 2 (C-B1 prediction-target contract unsatisfiable; C-B2 param-vocabulary collision)
- Majors: 7 (C-M1 safety backstop optional; C-M2 disposition vocabulary breach; C-M3 intent-record
  undefined + missing edge; C-M4 delivery stack holes; C-M5 dtype fallback undeliverable; C-M6
  threshold statistics; C-M7 spike mis-sequenced)
- Minors: 8

The spec's strongest assets are its corrected ground truth (§4) and the recon's verified cites —
none of those failed verification here. The systematic weakness is at the seams BETWEEN contracts
it inherited (ParseSource shape, TOOL_SCHEMA poverty, closed vocabularies, delivery constraints)
and the FunctionGemma-native formats it adopts: each seam assumes the other side already speaks
its vocabulary, and no item owns the translation.
