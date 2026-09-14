---
title: 'Teacher backend: Gemini 3.7 Flash for full-scale floor_gen/overlay_gen pass'
description: 'Resolves the 260827 full-scale-generation backend blocker: Gemini 3.7 Flash chosen over titanix-vllm-primary, shelled via the local agy CLI (no API key) with batched, guided-decoding-enforced teacher calls. Covers PLR task-type/contract coverage strategy (incl. the chory-lab/plr-cookbook 91-recipe source), batching rationale (measured), version-brittleness mitigations, and empirical guided-decoding null-handling caveats.'
status: accepted
task_id: 260825_copilot_pipeline_spec
date: '260827'
supersedes: ''
backlog_ids: ''
---
# Teacher backend: Gemini 3.7 Flash for full-scale floor_gen/overlay_gen pass

Resolves the sole remaining P2.5 GO condition blocker (`260825_p25_slice_gate.md`
§5 condition 1, [[coxswain-p25-backend-blocker]]): titanix-vllm-primary was
user-flagged 260827 as not viable for the full-scale `floor_gen`/
`overlay_gen --full` pass. Replacement: **Gemini 3.7 Flash**
(`gemini-3.7-flash`, released 2026-08-13), reached by **shelling to the
local `agy` CLI** (`/home/marielle/.local/bin/agy`), NOT the raw Gemini HTTP
API.

**Revision note (same day):** the first version of this decision used a
direct `GEMINI_API_KEY` + raw HTTP design. User-corrected: "we don't need a
gemini api key. it's via the agy command line." `agy` is a general-purpose
agentic CLI (same flag family as a coding-agent harness — `--print`,
`--model`, `--agent`, `mcp`, `plugin`, `--dangerously-skip-permissions`) that
happens to expose Gemini 3.7 Flash as one of its selectable models
(`agy models`: `gemini-3.7-flash-{high,medium,low}` — note the bare
`gemini-3.7-flash` string used in the first version of this doc is NOT a
valid `--model` value) and owns its own auth. Everything below reflects the
agy-shelled design; nothing here required a raw API key at any point past
this revision.

## 1. Why Gemini 3.7 Flash needs no D13 re-check

D13 (`260825_gemma-license-deployment-gate.md` §1) exists because F6 was
written assuming a **non-Gemma teacher** keeps the training corpus outside
Gemma's Model-Derivative pathway. Gemini 3.7 Flash is not a Gemma-family
model (different lineage, different license, Google's general Gemini API
terms) — F6's non-Gemma-teacher assumption still holds unchanged. No
re-run needed. (If a future backend swap ever lands on a Gemma-family
model, D13 re-runs; this decision doesn't relax that trigger.)

## 2. Implementation

Two call sites, kept as two classes rather than unified (matching how
`floor_gen` and `overlay_gen` already each define their own local
`TeacherBackend` Protocol — see §5):

- `floor_gen/teachers.py::GeminiTeacher` — implements floor_gen's
  `TeacherBackend` (`complete(system, user) -> str`,
  `teacher_model_version` property), PLUS an additional
  `complete_batch(system, users, ids) -> dict[id, raw]` method for grouped
  calls (§3, §4). Wired as `--backend gemini` in `floor_gen/cli.py` (alongside
  existing `titanix`/`fake`), with a new `--batch-size` flag
  (`GEMINI_BATCH_SIZE = 20` default).
- `overlay_gen/pair_builder.py::GeminiTeacherClient` — implements
  overlay_gen's `TeacherBackend` (`complete(prompt) -> str`,
  `model_version` property). Wired as `--backend gemini` in
  `overlay_gen/run_smoke.py` (previously `VllmTeacherClient()` was
  hardcoded there with no backend flag at all — this decision adds the
  flag, not just the new backend). **Not yet batched** — see §8 item 3.

Transport for both: `subprocess.run(["agy", "--model", ..., "--output-format",
"json", "--json-schema", <schema>, "--print=<prompt>"], capture_output=True)`,
parsing the returned JSON envelope's `structured_output` field (agy's own
schema-validated result, not hand-parsed text). No API key anywhere in this
repo's code — `agy` owns its auth. `GeminiTeacher`/`GeminiTeacherClient`
construct with zero required arguments and fail loudly only if `agy` itself
isn't on `PATH` or errors at call time (`GeminiError`), not at construction
time (there's no key to check upfront anymore).

**Real end-to-end verification (not just unit-level):** ran
`floor_gen.cli generate --backend gemini --limit 8 --batch-size 4` against 8
real matrix cells (2 real `agy` batch calls of 4 items each) spanning all
four ambiguity classes — `cells=8 examples=24 accepted=24 rejected=0
pass_rate=1.000 cache_hits=24 cache_misses=0
teacher=gemini-3.7-flash-medium`. The cache-prewarm design means every row
after the 2 teacher calls is a cache hit, so the existing per-item row
-construction/validation loop needed zero changes.

## 3. Guided decoding: yes -- with real, empirically-found caveats

**Directly answers "can guided decoding enforce strict contracts when we
know them and the types involved": yes, `agy --json-schema` supports
exactly this** — pass a JSON Schema, get back `structured_output` that's
already been decode-constrained to match it. But "enforced" turned out to
mean "shape is enforced" more reliably than "every field-level semantic is
enforced" — see the null-handling caveat below, found by actually running
calls, not by reading docs.

Both existing teacher contracts in this codebase were, until now, enforced
only by **prompt instruction text plus hope**:

- `floor_gen`'s `_RESPONSE_SHAPE` (`prompts.py`) tells the model in English
  to reply with exactly one JSON object, no markdown fences, no commentary.
  `TitanixTeacher.complete()` has a bounded-retry loop specifically to
  paper over empty/malformed completions from this soft contract.
- `overlay_gen`'s `paraphrase_prompt()` tells the model in English to
  produce exactly N lines, one phrase per line, no numbering. A regex
  (`_BULLET_RE`) then defensively strips bullets/numbering that the model
  adds anyway despite the instruction.

`GeminiTeacher` replaces the soft side of that contract with an actual
enforced schema, single-item AND batched:

- `_GEMINI_RESPONSE_SCHEMA` (single-item): the exact
  `{"utterance": <str>, "clarification": <str|null>}` shape as a JSON
  Schema object, `required: [utterance, clarification]`. Comment ties it
  explicitly to `response_shape_instructions()` in `prompts.py` — the
  free-text version and the schema version are declared as ONE contract
  described twice; a future change to either without the other is now a
  documented invariant violation, not just a hope.
- `_GEMINI_BATCH_RESPONSE_SCHEMA` (batched, §4): wraps an array of the same
  per-item shape (plus an `id` field for join-back) under a `results` key.
  **agy's `--json-schema` rejects a bare top-level ARRAY schema outright**
  (exit 1, 0 tokens billed — rejected client-side before reaching the
  model, confirmed by testing both shapes directly) — the top level MUST be
  an OBJECT. Not documented anywhere I found; discovered by trying both.

**Empirical caveat, found by testing, not assumed:** `nullable: true` on a
STRING field does NOT reliably yield a real JSON `null`. Two DISTINCT
non-null stand-ins were observed across a handful of manual calls: an empty
string `""` on one call, and separately the literal four-character STRING
`"null"` (quoted text) on another. Both `complete` and `complete_batch`
normalize known stand-ins back to `None` before returning
(`_NULL_STANDINS` in `teachers.py`) — necessary because
`corpus.py::validate_class_shape` treats "clarification present" as "must
be an out-of-surface row"; an un-normalized stand-in would silently
misclassify an in-surface row. This is flagged as an OPEN reliability
question in the code, not a closed one: two failure modes surfaced in a
handful of calls means a third, uncaught one is plausible at full-scale
volume — the full run's manifest/rejection counts are the real check, not
this normalization list.

`overlay_gen`'s paraphrase array-of-strings schema (as originally designed
in the pre-agy revision of this doc, extracting N from
`paraphrase_prompt()`'s embedded count) is UNCHANGED in code as of this
revision but similarly needs the object-wrapping fix and hasn't been
re-verified against agy directly — see §8 item 3.

Net effect: for the full-scale pass, a structural class of failure
(malformed/wrapped/prose-contaminated teacher output, wrong item count)
becomes impossible by construction instead of retried-around; a narrower
class (a nullable field's null-ness specifically) still needed defensive
normalization after finding it empirically. `complete()`/`complete_batch()`
still return raw text per the `TeacherBackend` protocol, so no downstream
parsing code needed to change.

## 4. Batching: why, measured against real numbers

**User-directed (260827): "rather than 800 individual calls, it would be
better to group many into one."** Confirmed empirically, not just
theoretically -- a trivial single-item smoke call
(`agy --model gemini-3.7-flash-low --json-schema ... --print=...`) cost
**21,647 input tokens, 16,271 of them cache-reads**, for a ~15-word prompt,
and took **11.2s**. A batch of 3 items cost 22,855 input tokens (16,278
cache-read) and took 8.0s. **The fixed per-call overhead (a large
cached-but-still-billed context, plus several seconds of latency) is
essentially invariant to how many items ride along in one call** -- almost
certainly the CLI's own agent-harness system prompt/tool definitions, not
our content. At ~800 individual calls (the corpus's own `>= ~800 assembled
rows` target, `260825_p25_slice_gate.md` §5), that overhead alone would
plausibly be the majority of total cost and wall-clock time, before a single
content token is considered.

`GeminiTeacher.complete_batch()` (§2, §3) groups `GEMINI_BATCH_SIZE` (20,
`floor_gen/versions.py`) items into one `agy` call, wrapped in
`floor_gen/corpus.py::_prewarm_cache_batched()` -- a cache-prewarm pass that
runs BEFORE the existing per-item loop, so the per-item loop itself required
NO changes (every lookup is a hit once prewarm finishes). Verified at
`batch_size=4` in the real end-to-end run (§2): 8 items became exactly 2
`agy` calls. At `batch_size=20` on the full ~129-call floor_gen matrix,
that's ~7 calls instead of 129 -- worth re-measuring once the actual
overhead-vs-batch-size curve is known past batch size 4 (does overhead stay
flat past a few dozen items, or does content volume start to dominate?
Not yet tested at that scale).

## 5. Coverage of different task types and contracts in PLR

Two separate coverage questions worth distinguishing:

**(a) Coverage of the CURRENT 13-tool phase-2 surface is already
structurally guaranteed, not just tested.** `floor_gen/matrix.py::_validate()`
loudly asserts, at matrix-load time, that every phase-2-included verb
(`PHASE2_TOOL_NAMES` from `coxswain.plr.tool_schema`) has exactly one
`none`-class cell, that every verb with a required param has a
`missing-slot` cell whose `missing_param` really is required (cross-checked
against `coxswain.plr.param_namespace`), and same for `ambiguous-referent`
against `symbolic_slots()`. A drift between the committed
`ambiguity_matrix.json` and the live namespace tables raises `MatrixError`
before any teacher call happens. This is real coverage enforcement, already
landed — nothing new needed here for the current 13-tool surface.

**(b) The current surface is a small slice of PLR's actual task-type space,
and `out-of-surface` seeds are hand-authored, not sourced.** Cloned the
upstream PyLabRobot repo to `~/projects/repos/pylabrobot` and surveyed
`pylabrobot/` top-level packages: beyond `liquid_handling` +
`plate_reading` (what the 13-tool surface covers), PLR ships first-class
machine categories entirely absent from the copilot surface —
`centrifuge`, `thermocycling`, `shaking`/`heating_shaking`, `sealing`,
`peeling`, `powder_dispensing`, `scales`, `storage`, `microscopy`, `pumps`,
`tilting`, `plate_washing`, `barcode_scanners`, `manual_operator`, plus
per-vendor backend modules (`hamilton`, `agilent`, `azenta`, `inheco`,
`qinstruments`, `sartorius`, `thermo_fisher`, `ufactory`, ~20 more).
`matrix.py`'s `out-of-surface` cells currently anchor on a handful of
hand-written `off_surface_request` strings — real coverage of "what should
trigger an out-of-surface clarification" but sourced from imagination, not
from PLR's actual documented capability surface.

**CORRECTION (260827, user-supplied): the real cookbook is
`https://github.com/chory-lab/plr-cookbook`, not the sparse 3-recipe
`docs/cookbook/` folder this doc originally pointed at inside
`PyLabRobot/pylabrobot`.** An earlier pass here searched `stefangolas`'s own
~60 GitHub repos and the wrong PR's authorship and concluded no
stefangolas-authored cookbook existed — that search missed it because it
lives under the `chory-lab` org, not his personal account. Verified
directly: `stefangolas` is the dominant contributor (102 commits vs. 22 and
7 for the next two), and the repo description is literally "The PyLabRobot
Cookbook — a task-indexed manual for PyLabRobot 0.2.2." Cloned to
`~/projects/repos/plr-cookbook`. This is a substantially better
out-of-surface source than either the official docs/cookbook (3 recipes) or
hand-invented phrasing: **91 recipes across 18 chapters**
(`cookbook/recipes.yml`), each with a `title` phrased exactly as a user
would search for the task, a `chapter`, and the real PLR `apis` it exercises
— e.g. chapter 4 ("Pipetting")'s "Mix during a transfer" is a concrete,
already-validated case: `mix` is NOT one of the copilot's 13 phase-2 tools,
and in this session's own smoke test (§2) the teacher correctly produced an
out-of-surface clarification offering `transfer` as the alternative for
exactly that request — real PLR capability, real copilot gap, already
proven to work as a seed. Chapters 10-18 (errors, state persistence, SQLite
tracking, custom backends, custom labware, hardware jogging) are entirely
orthogonal task types with essentially zero overlap to the current
copilot surface — the richest single vein of real out-of-surface material
found so far.

**Recommendation (not implemented — P2.5.x-scale follow-up, does not block
the full-scale pass or this decision):** mine `out-of-surface` seed
candidates from `cookbook/recipes.yml`'s 91 `title`s directly (already
machine-readable, already task-phrased, already versioned against a pinned
PLR release) instead of hand-invented phrasing — pin the cookbook repo's SHA
the same way `PLR_SUBMODULE_SHA` is pinned elsewhere, so a future
`ambiguity_matrix.json` regeneration stays reproducible against a fixed
recipe list rather than whatever the repo currently contains.

## 6. Avoiding brittleness to versions

The codebase already has one strong existing pattern worth extending
consistently, not replacing:

- **Pin exact strings; record what's actually pinned.** `PLR_SUBMODULE_SHA`
  pins the vendored PLR the namespace table is parity-checked against;
  `TitanixTeacher._resolve_model_version()` calls the live `/models`
  endpoint and folds the served `root` into `teacher_model_version` so
  silent backend-side swaps are visible in provenance, not silently
  absorbed. `GeminiTeacher` follows the pin half of that shape but NOT the
  live-resolve half: `GEMINI_MODEL = "gemini-3.7-flash-medium"` is a
  literal, effort-tiered model ID (never `-latest`; `agy models` confirmed
  no such alias exists anyway), but `agy` exposes no `models.get`-equivalent
  the way the raw Gemini API did, so `teacher_model_version` is now just the
  static pinned string with no live confirmation that `agy` is actually
  still serving that exact model version underneath. **This is a real,
  acknowledged regression vs. `TitanixTeacher`'s pattern**, traded for not
  managing an API key -- flagged here rather than silently accepted; if
  `agy` grows a way to report what it actually served (its output envelope
  currently doesn't), wire it in the same way.
- **The response contract is now versioned in two places by construction,
  which is the brittleness risk to actually watch.** `_GEMINI_RESPONSE_SCHEMA`
  duplicates (deliberately, per §3) the shape already described in
  `prompts.py::_RESPONSE_SHAPE`. `PROMPT_VERSION` bumps on any text change
  to the free-text contract (existing rule); this decision adds the
  obligation that a `responseSchema` change carries the same bump, since
  the two are one contract, not two. No code currently enforces this
  pairing mechanically — a comment states it. If this drifts in practice,
  a cheap guard would be a test asserting the schema's declared field
  names against a set literal shared with `prompts.py`.
- **Known, un-fixed contract-shape drift (flagged, not touched):**
  `floor_gen.teachers.TeacherBackend` (`complete(system, user)`,
  `teacher_model_version`) and `overlay_gen.pair_builder.TeacherBackend`
  (`complete(prompt)`, `model_version`) are two independently-defined,
  incompatible Protocol shapes for what is conceptually the same "teacher
  backend" concept — pre-existing, not introduced by this change. Adding
  `GeminiTeacher`/`GeminiTeacherClient` as two separate classes matches
  that pre-existing split rather than papering over it. Unifying the two
  Protocols would be a real simplification but is out of scope here
  (neither module's tests or callers asked for it, and it would touch two
  working generators beyond this backend swap).

## 7. Cost note (superseded from the raw-API version of this doc)

The original version of this section cited raw Gemini API $/token pricing
($0.75/1M input, $3.75/1M output). That framing doesn't directly apply
anymore -- `agy` is a CLI with its own account/billing model, not a
pass-through to per-token API pricing this repo pays directly, and its
usage envelope reports token counts (§4's 21-24K/call) without this repo
knowing how those map to cost under `agy`'s billing. What's real and
measured: the fixed per-call overhead (§4) means call COUNT, not raw
content volume, is the dominant cost/latency lever here -- which is exactly
why batching (§4) matters more than any $/token estimate would have
suggested. No dollar figure is asserted; if `agy`'s billing model matters
for budgeting, that's a question for whoever administers the `agy`
account, not something inferable from this repo's code.

## 8. Next steps

1. Run `floor_gen.cli generate --backend gemini --batch-size 20` (full
   matrix, no `--limit`) -- no API key or other setup needed, `agy` is
   already installed and authenticated on this machine.
2. Re-measure the overhead-vs-batch-size curve at the real full-matrix scale
   (§4) and retune `GEMINI_BATCH_SIZE` if the flat-overhead assumption
   breaks down past a few dozen items.
3. Extend the SAME batching design to `overlay_gen` (§2's "not yet batched"
   note): `overlay_gen/pair_builder.py::build_pairs()` currently calls
   `teacher.complete(prompt)` once per unique canonical sentence in a single
   loop (`pair_builder.py:433-451`), structurally identical to floor_gen's
   pre-batching per-item loop. Also re-verify `GeminiTeacherClient`'s
   array-of-strings paraphrase schema against real `agy` calls (only
   `GeminiTeacher`'s object schema has been live-tested as of this
   revision) and apply the same object-wrapping fix if the bare-array
   rejection (§3) reproduces there too.
4. Run `overlay_gen.run_smoke --full --backend gemini`.
5. Re-assemble the corpus (`training/assemble/`) and re-run the P2.5 slice
   gate per `260825_p25_slice_gate.md` §5 condition 3.
6. (Optional, non-blocking) PLR-taxonomy-sourced out-of-surface seed
   generator per §5(b).

## 9. The real cookbook: `chory-lab/plr-cookbook` (user-supplied, confirmed)

Superseded finding. This section originally concluded, after searching only
`stefangolas`'s own ~60 personal repos and the wrong PR's authorship, that
no stefangolas-authored cookbook existed separate from
`PyLabRobot/pylabrobot`'s sparse `docs/cookbook/` (3 recipes, authored by
GitHub user `BioCam`). **That search was incomplete, not the repo's
non-existence** — user supplied the actual URL:
`https://github.com/chory-lab/plr-cookbook`. Verified directly (not
just trusted): `stefangolas` is the dominant contributor (102 commits vs. 22
and 7 for the next two contributors), repo description is "The PyLabRobot
Cookbook — a task-indexed manual for PyLabRobot 0.2.2," 91 recipes across 18
chapters. It lives under the `chory-lab` GitHub org — a lab/organization
account, not `stefangolas`'s personal namespace — which is exactly why a
search scoped to his personal repos missed it. Cloned to
`~/projects/repos/plr-cookbook`. Full content survey and its use as an
out-of-surface seed source: §5(b).

**Lesson for next time:** an authorship/provenance search scoped to one
account (a person's personal repos) doesn't cover org-owned repos that
person dominantly contributes to — GitHub's contributor listing on the
target repo itself, not the person's own repo list, is the check that would
have found this the first time.
