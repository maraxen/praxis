---
title: 'Coxswain MVP UX specification (N1-N8)'
description: 'Implementable specification for the Coxswain propose/confirm, clarification, FFT-gate-extension and audit-trail surfaces: formalizes the eight negotiable UX axes (N1-N8) resolved in brainstorm session 48789b43 against the locked architecture (F1-F10), with fixer-ready work-item decomposition, correlation-ID contract, structural safety constraints mandated by the pre-mortem, and a risk table. Revised 260824 to close the adversarial review cycle (audits 260824_coxswain_spec_challenge / _defense) — see the Revision Log.'
status: draft
task_id: 260824_coxswain_spec_design
date: '260824'
confidence: ''
sources: ''
---

# Specification: Coxswain MVP UX (N1-N8)

## Revision Log (260824)

Targeted revision pass closing the adversarial review cycle (challenge
`260824_coxswain_spec_challenge`, defense `260824_coxswain_spec_defense`, both in
`.praxia/audits.jsonl` under task `260824_coxswain_spec_design`). Objection IDs below are that
exchange's. Objections **C2, C4, C7, C17, C18, C19, C24, C26, C32, C34 and C38** were rebutted
with evidence and are deliberately left unchanged.

**Blocking:**

- **C1** — FR-6, §2.4, AC-9: the staleness comparison now names its field set explicitly
  (`{concurrency_active, precondition_digest}`) and marks the four provenance fields as excluded.
  As previously worded ("differ in any field") every execution would have aborted.
- **C3** — new **W1.0** CI work item, a §5 preamble clause, **AC-18** and **RISK-15**: no AC in
  this spec is satisfied until a CI job runs `uv run pytest coxswain/tests -q` and
  `bun test web-repl/shell/coxswain`, with `coxswain/**` added to both of `repl.yml`'s path
  trigger lists.
- **C6** — `ConcurrencyProbe` given a named signal source (§4.5), its own files in W2, and
  **AC-16** asserting a "not active" result is backed by a real read.
- **C8** — FR-12, AC-11, W4, RISK-11: the Coxswain highlight subscriber moves out of
  `visualizer-augmentations/index.js` into a conditionally staged
  `overlay/assets/coxswain/viz_highlight.js`; AC-11 gains a byte-identity clause on the
  augmentation file. Rationale for choosing conditional staging over test-only relaxation is in
  §6.1a's deviation table.
- **C9** — **AC-14**: a tier floor. No deck/resource-mutating PLR call may be tagged `read_only`.
- **C12** — FR-9 rewritten: "synchronously" replaced by an acknowledged-write-before-disposition
  guarantee, with a stated flush window and tab-close behavior; new disposition
  `blocked:audit_unavailable`; **AC-19**.
- **C31** — new **NFR-7** (output encoding: `textContent` only, with max lengths) and **AC-15**.

**Conceded:**

- **C13** — AC-1 split into AC-1a (W1) and AC-1b (W2); the old form was red-by-construction at W1.
- **C16** — new field state `awaiting_clarification` for an inline edit whose re-grounding exits
  `clarify:disambiguate` (§3.1, §4.2).
- **C20** — §4.6 specifies the `session_id` handshake for the visualizer document and its
  fail-closed behavior before the handshake completes.
- **C21** — new **§6.1a** recorded-deviations table (D-A/D-B/D-C); the
  JS-lives-under-`web-repl/shell/coxswain/` choice is now explicit rather than implicit.
- **C22** — §7 row: the relay's HTTP receiver service is out of scope and unverified, so N6's
  relay half may ship inert.
- **C25** — §2.3 defines turn open/closed/abandoned and states eviction is oldest-**closed**-first
  and never targets an open turn.
- **C27** — `schema_version` added to the persisted shapes (§2.4) with a loud-refusal /
  read-only-degrade upgrade policy; **AC-21**.
- **C28** — H1 gets numbers: 300 ms edit debounce, 2 s cue-2 re-grounding timeout, 5 s kernel
  round-trip timeout, all in one constants module (§4.7).
- **C29** — §7 records that deferring `learn()` makes cold start permanent for alias-only
  references, while deck-graph-resolvable references are unaffected.
- **C30** — FR-8's re-entry rule corrected: a cue re-enters **itself** while any slot it governs
  is unresolved; **AC-20** covers the two-ambiguous-reference case.

**Partial:**

- **C5** — the execution-failure card renderer is now an explicit W3 sub-item with its own file,
  rather than a message kind with no owning work item.
- **C10** — **AC-13**: an empty, partial or mismatched confirmation phrase emits no execute
  message, tested at both the JS derivation layer and the kernel.
- **C11** — FR-3 states the multi-target object-phrase rule.
- **C14** — the stray `── W5` edge deleted from §6.2's graph; W5's prose was already correct.
- **C15** — FR-4 names cue 3 as the cue a scalar edit re-enters.

**Suggestions taken:** C33 (AC-6 gains a `__dataclass_fields__` structural assertion), C35 (W1.0
proves the `bun test` harness before W1 depends on it), C37 (**AC-17**: quota-exceeded surfaces
loudly).

---

## Overview

Build the user-facing half of Coxswain — the propose/confirm card, the clarification card, the
FFT gate extensions those cards depend on, and the audit trail that records every gate decision —
so that a scientist typing a lab command into web-repl's Coxswain panel sees an auditable,
editable, friction-tiered proposal that cannot be executed while any part of it is unvalidated.

Architecture is **locked and not relitigated here**. F1-F10 (plugin injection into web-repl,
one shared Pyodide kernel, `functiongemma-270m-it` + LoRA adapters, the 4-cue FFT gate and its
cue order, NLU-only-at-parse layering, Chrome on-device Web Speech API, the two grounding
contracts, the `coxswain/` uv-workspace boundary, the L0-L3 persistence contract, and the
tool-calling schema shape) are given by
`.praxia/docs/research/260824_gemma-finetuned-plr-voice-text-copilot-scoping.md` and are cited,
not reopened.

This spec formalizes the eight negotiable axes resolved in
`.praxia/docs/specs/260824_coxswain-ux-open-design-axes-task-id-260.md` (session `48789b43`):

| Axis | Resolution (from the Decision Log) |
|---|---|
| N1 | Static call-type risk tiering in the tool schema; parameter-scaled risk demoted to a warning annotation; irreversible tier confirmed by a typed keyword mirroring the action verb |
| N2 | Full inline per-field editing, debounce-on-blur re-grounding, **with a mandatory visible "unvalidated — re-checking" state that structurally blocks Confirm** |
| N3 | Confirm-time re-run of cues 0 and 3 stays the mechanism; its result is formalized as a typed fingerprint record for the audit trail. Zero auto-repair — any drift hard-aborts |
| N4 | Reuse of `praxis/backend/core/simulation` assumed **only** pending a concrete blocking recon check; falls through to full deferral if the check comes back DB-coupled |
| N5 | Default propose/confirm card shape unchanged; Matches/Conflicts/Omissions categorization applied **only** to clarification cards |
| N6 | Dual-write audit log: coxswain-local is the offline-first source of truth, best-effort relay to `transduction_log` never blocks it |
| N7 | Expert override scoped to cue 3 (precondition) exits only, with typed justification and an immutable audit entry |
| N8 | Minimal target-prominence highlighting of the ambiguous location on the existing committed-state Visualizer; no hypothetical-state ghosting |

The brainstorm's own Acceptance Criteria section terminates in a literal placeholder
(`[ ] _add specific measurable criteria_`). Filling that in with concrete, executable gates is
the primary deliverable of this document.

---

## 1. Requirements

### 1.1 Functional requirements

**FR-1 — Turn identity.** Every user command submission mints exactly one conversation-turn
identifier (`turn_id`). Every downstream artifact of that turn — pending intent, gate decisions,
staleness fingerprints, override records, execution outcome, transcript entries — carries it.

**FR-2 — Risk tiering (N1).** Every function in the tool schema carries exactly one static
`risk_tier` of `read_only`, `reversible`, or `irreversible`. Confirmation friction is a pure
function of that tier and nothing else:

| Tier | Friction |
|---|---|
| `read_only` | No confirmation. Executes on propose. |
| `reversible` | Single Confirm activation (click or Enter on the focused Confirm control). |
| `irreversible` | Confirm stays inert until the user enters the required confirmation phrase verbatim into a labelled text field. |

Parameter-derived risk (N1-B, merged) appears **only** as advisory `warnings[]` badges on the
card (e.g. `large_volume`, `multi_plate`). Warnings never change the tier and never change
which friction path applies.

**FR-3 — Confirmation phrase (N1-D).** For `irreversible` calls the required phrase is derived
deterministically from the resolved call as `"<verb> <short object phrase>"` (e.g.
`discard tips at C3`), rendered verbatim on the card, and matched case-insensitively with
collapsed internal whitespace and trimmed ends. No other normalization. The field is a labelled
`<input type="text">` — never a modal keystroke trap, never a hold gesture (N1-C rejected on the
accessibility floor, H4).

`derive_phrase(resolved_call) -> str` is a pure function in
`web-repl/shell/coxswain/phrase.js`, mirrored by `coxswain/src/coxswain/phrase.py`, and both must
agree on the same fixtures. Its rules, exhaustively:

- **verb** — the schema's `verb` field for the call, lowercased. Never the raw function name.
- **object phrase** — a resolved resource or location descriptor, never a quantity. Volumes,
  counts and units therefore never appear in a phrase, so the field is always plain ASCII and
  typeable on any keyboard layout.
- **multi-target calls** — when the call resolves more than one target (e.g. `transfer` to three
  wells), the object phrase is the **first target in the call's declared argument order**
  (as-given, never sorted, never deduplicated) followed by ` +<n-1> more`. A `transfer` to A1, A2
  and A3 yields `transfer to A1 +2 more`. The rendered card still lists all targets in full above
  the phrase field; only the phrase is abbreviated.
- **length** — the derived phrase is capped at 60 characters; if the first target's descriptor
  alone exceeds that, it is truncated on a word boundary and the phrase is regenerated from the
  truncated form, so the string a user is asked to type is always exactly the string rendered.

**FR-4 — Inline editing (N2).** Every parameter on a propose/confirm card is editable in place.

- Editing a **scalar** field (volume, count, tip type) marks the card dirty and, on blur,
  re-enters the FFT gate at **cue 3** (precondition) — the tier and the grounding are unchanged
  by a scalar edit, but the preconditions the new value must satisfy are not.
- Editing a **symbolic-reference** field (source well, target plate, location) re-enters the gate
  at **cue 2** on blur, and then continues into cue 3 as any cue-2 pass does.

Both are debounced, not per-keystroke, per H1: the debounce interval is 300 ms and a blur flushes
it immediately (§4.7).

**FR-5 — Unvalidated state is a block, not a hint (N2, pre-mortem Failure 1).** While any field
is `dirty_unvalidated` or `revalidating`, the Confirm action is blocked at three independent
layers (§3.1). The visible "unvalidated — re-checking" state is a *disclosure of* the block, not
the block itself.

**FR-6 — Staleness (N3).** Cues 0 and 3 re-run immediately before execution. Both the propose-time
and the confirm-time pass emit a `StalenessFingerprint` record.

**The comparison is over exactly two fields: `{concurrency_active, precondition_digest}`.** These
are cue 0's and cue 3's own outputs and nothing else. `taken_at`, `gate_seq`, `fingerprint_id` and
`card_revision` are **provenance/audit fields and are excluded from the equality comparison** — by
construction they differ between any two passes, so comparing the whole record would abort every
execution that ever reached confirm time. A conforming implementation compares
`(fp.concurrency_active, fp.precondition_digest)` tuples and nothing more; the comparison function
is the single place this field set is named, and adding a field to `StalenessFingerprint` must not
silently add it to the comparison.

If those two fields differ, execution hard-aborts to a fresh clarify/re-propose cycle. No drift is
classified as benign; no value is auto-corrected.

*Deviation recorded (C23):* the brainstorm's N3-C described the fingerprint record as existing
"purely for the audit trail", while FR-6 makes the comparison the abort trigger. This is an
intentional clarification, not scope creep: no state-diff subsystem is built, no new state is
captured, and the two compared fields are literally the return values cue 0 and cue 3 already
produce on every pass. Formalizing those two return values as a typed, persisted record is what
makes the abort auditable after the fact. N3-A (a general drift-detection subsystem) remains
rejected. See §6.1a's deviation table.

**FR-7 — Clarification cards (N5-B).** A `clarify:disambiguate` or `clarify:not_found` card
renders the grounding result categorized as **Matches / Conflicts / Omissions**, derived from
Layer 2/3 output only. `clarify:incomplete` renders a missing-field prompt.
`clarify:precondition` and `blocked:concurrent` render a plain explanation. Default
propose/confirm cards keep the MVP shape — NL restatement primary, collapsed literal call
secondary, one-line disclosure when a clarification preceded the proposal — and gain no staging,
no reasoning trace (N5-A rejected).

**FR-8 — Clarification answers resolve without a model round-trip.** Click answers and typed
answers both route through the deterministic matcher against the already-fetched candidate set.

Resolving a slot re-enters the FFT at **the cue that exited, not the cue after it**, incrementing
`gate_seq`. That cue advances to the next cue only once **every** slot it governs is resolved. A
single cue-2 pass routinely surfaces more than one unresolved symbolic reference (a `transfer`
whose source *and* target are both ambiguous); under a re-enter-at-the-next-cue rule the second
reference would never be re-examined and would reach execution unresolved. Concretely:

1. Cue 2 exits `clarify:disambiguate` on the first unresolved slot it encounters, in the call's
   declared argument order.
2. The user resolves it. The gate re-enters **cue 2** at `gate_seq + 1`.
3. Cue 2 exits again on the next unresolved slot; repeat.
4. Only when cue 2 completes a pass with zero unresolved slots does control advance to cue 3.

The same rule applies to cue 1's `clarify:incomplete` exits (multiple missing required fields).
AC-20 tests the two-ambiguous-reference case end to end.

**FR-9 — Audit trail (N6).** Every FFT gate pass emits one `FftDecision` record, and **the gate
does not return its disposition to the UI until that record's write has been acknowledged as
durable.** There is no synchronous path here to claim: the gate is kernel-resident Python and the
L0 store is IndexedDB on the main thread, reached over `praxis_coxswain`; both BroadcastChannel
and IndexedDB are asynchronous. The guarantee is therefore **ordering and blocking, not
synchrony**:

- The write is issued inside the gate pass's own code path, before the disposition is returned.
  The gate awaits an `audit.ack` carrying the record's id.
- The ack is sent by `audit_store.js` on the IndexedDB **transaction's `complete` event**, not on
  the individual request's `success` event. An ack therefore means the record is durable, not
  merely queued.
- **Flush window:** the ack must arrive within the 5 s kernel round-trip timeout (§4.7). On
  timeout or on an explicit write failure the gate exits `blocked:audit_unavailable` and no
  execution occurs — fail closed, per NFR-5. Coxswain never proceeds on an unrecorded decision.
- **Tab closed mid-write:** an IndexedDB transaction that does not reach `complete` aborts whole;
  no partial record persists. Because the disposition was never returned, no execution was ever
  dispatched on that decision either. The turn is left `open` and is marked `abandoned` at the
  next session init (§2.3).
- **Never behind the relay.** The relay to `transduction_log` is attempted only when a relay
  endpoint was configured at build time, is fire-and-forget, and can never block, delay, or fail
  the local write or the ack. The gate never awaits the relay.

**FR-10 — Scoped override (N7).** A precondition exit (cue 3) may be overridden by a user who
types a non-empty justification. Cue 0, cue 1 and cue 2 exits expose no override affordance at
all — not a disabled one. Each use appends an immutable `OverrideRecord`. Overrides are never
rate-limited or throttled.

**FR-11 — Location highlight (N8-B).** During a `clarify:disambiguate` or `clarify:not_found`
turn, the ambiguous location (rail/slot) is highlighted on the existing Visualizer panel. The
highlight is drawn on a dedicated overlay layer and never mutates the committed-state model.
Under `prefers-reduced-motion: reduce` the highlight is a static outline with no flashing or
animation.

**FR-12 — Build-time optionality.** All of the above ships only when `build_repl.py` is invoked
with `--with-coxswain`. A default build produces a dist with no Coxswain assets, no
`coxswain-shell.js`, and no Coxswain manifest entries.

**This constrains where the Visualizer highlight subscriber may live.**
`web-repl/overlay/assets/visualizer-augmentations/index.js` is required in **every** build —
`assert_dist_complete` asserts its presence unconditionally (`web-repl/scripts/build_repl.py:864`)
and `vendor_visualizer.py:141` injects its `<script>` tag into the vendored
`visualizer/index.html` on every vendor pass. If the Coxswain subscriber were added to that file,
Coxswain code would ship in the default build, FR-12's first sentence would be false, and AC-11's
path-substring check would pass vacuously (that file's path contains no `coxswain`).

Therefore the subscriber is a **separate module, conditionally staged**:
`web-repl/overlay/assets/coxswain/viz_highlight.js`, staged and manifest/sha-tracked only under
`--with-coxswain`, and loaded by a second `<script type="module" src="../coxswain/viz_highlight.js">`
tag that the `--with-coxswain` build path injects into `visualizer/index.html` alongside — never
instead of — the existing augmentation tag. `visualizer-augmentations/index.js` is **not modified
by this spec at all** and a default build's copy of it must be byte-identical to the current
tracked file (AC-11).

Conditional staging was chosen over the alternative of leaving the code in the augmentation file
and merely rewriting AC-11 to assert byte-identity against a "no-Coxswain baseline": the
alternative would keep dead Coxswain code in the shipping default build and make the baseline an
artifact that has to be regenerated whenever the augmentation file legitimately changes, which
turns a real gate into a maintenance chore that gets rubber-stamped. Conditional staging makes
FR-12 true rather than merely tested. The byte-identity assertion is retained anyway as AC-11's
enforcement mechanism, since it is cheap and it is what catches a regression back into the
augmentation file.

### 1.2 Non-functional and structural requirements

**NFR-1 — CPython importability.** Every Python module under `coxswain/src/coxswain/` must import
cleanly in CPython outside Pyodide. No module-level `import js`. (Precedent: the 260817 recon found
`web_bridge.py`'s module-level `import js` falsified the claim that it was CPython-testable —
do not repeat that.) Browser-only bindings are injected at call sites or imported lazily inside
functions.

**NFR-2 — No `praxis.backend.*` import.** Per ADR
`.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md` §5.2 and
`coxswain/README.md`, `coxswain/` must not import `praxis.backend.*`. Anything needed from the
backend is reimplemented dependency-free.

**NFR-3 — DOM-free safety logic.** All safety-load-bearing JS logic (confirm-enablement
derivation, confirmation-phrase matching, revision comparison, envelope validation) lives in
DOM-free pure modules under `web-repl/shell/coxswain/` so it is unit-testable with `bun test`
and zero installed dependencies. DOM wiring is a thin adapter over those modules. This is a hard
constraint because web-repl has no `package.json`, no `node`/`npm`, and therefore no DOM test
harness (see RISK-6).

**NFR-4 — Traffic-class channel separation.** Coxswain traffic rides a new `praxis_coxswain`
BroadcastChannel. It must not reuse `praxis_repl` (device authorization) or `praxis_viz`
(committed PLR state) — the same principle `web-repl/overlay/assets/python/praxis/viz/transport.py:10`
already states for why `praxis_viz` was split off. The Visualizer highlight (FR-11) is Coxswain UI
traffic, so it rides `praxis_coxswain` and the conditionally-staged
`overlay/assets/coxswain/viz_highlight.js` subscribes to it as a read-only consumer (FR-12, D-C —
**not** `visualizer-augmentations/index.js`, which ships in every build); it does **not** ride
`praxis_viz`. The handshake by which that module learns whose session it is listening to is §4.6.

**NFR-5 — Fail closed.** Any cue whose input cannot be determined (concurrency probe unreachable,
kernel round-trip timeout, malformed grounding response, audit write unacknowledged) exits as a
block, never as `continue`. Every timeout this rule depends on is a named constant with a value
in §4.7 — a fail-closed rule with an unspecified timeout is a guess, not a requirement.

**NFR-6 — Accessibility floor (H4).** Every interactive affordance specified here is
keyboard-reachable and labelled. Copy uses active-voice verbs and non-hedging failure text
("Coxswain cannot resolve 'lane C' on this deck.", not "Something might have gone wrong").

**NFR-7 — Output encoding.** This page holds live WebSerial/WebUSB device grants and renders two
classes of untrusted-ish string as prose: **model-derived** (the NL parse restatement, candidate
labels, warning text) and **user-derived** (override justifications, edited field values, typed
clarification answers, resource names originating in a user-authored deck file). Therefore:

- Every such string is written to the DOM via `textContent` (or `document.createTextNode` /
  `Text.data`). `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, and
  `Element.setHTML` are **prohibited anywhere under `web-repl/shell/coxswain/`**, including in
  template helpers. Markup is built with `createElement` + `append`, never by string
  concatenation.
- Strings are truncated at render to a stated maximum, with the full value available only via a
  `title` attribute (also set as a property, not as markup): NL restatement **400**, candidate
  label **120**, warning badge text **64**, edited field value **200**, override justification
  **500**, derived confirmation phrase **60** (FR-3). A string exceeding its cap is truncated on a
  word boundary and suffixed with `…`; it is never rejected silently.
- The same caps are enforced kernel-side in `coxswain/src/coxswain/records.py` before persistence,
  so a record cannot carry an unbounded string that a later viewer renders.
- AC-15 gates this with a grep-style structural test, not a review convention.

---

## 2. The correlation contract (mitigates pre-mortem Failure 4)

Pre-mortem Failure 4's root cause was that N6's "supplements, not replaces" framing named a
relationship between two trails without specifying a joinable key or a shared retention contract.
This section specifies both. **Field names below are normative; an implementer must not choose
their own.**

### 2.1 Identifiers

| Field | Type | Minted where | Meaning |
|---|---|---|---|
| `session_id` | `str` | Once per tab session, in `coxswain-shell.js` on panel init | Tab-scoped session |
| `turn_id` | `str` | Once per user command submission, at input capture in `coxswain-shell.js` | The conversation turn. Format: `cx-<epoch_ms>-<6 chars base36>` |
| `gate_seq` | `int` | Incremented by the gate, starting at 0 | Which FFT pass within the turn: `0` = initial, `1..n` = re-entries after clarification, final = confirm-time re-check |
| `card_revision` | `int` | Incremented by the card on every field edit, starting at 0 | Which edit generation of the proposal |
| `fingerprint_id` | `str` | Per fingerprint capture | `<turn_id>:<gate_seq>:fp` |
| `override_id` | `str` | Per override use | `<turn_id>:<gate_seq>:ovr` |

`(turn_id, gate_seq)` uniquely identifies one FFT gate pass. `turn_id` alone is the join key
across **all three** trails: the resolve-then-resume clarify/execution-failure trail, the N3-C
fingerprint records, and the N6 FFT decision log.

### 2.2 Threading

1. `coxswain-shell.js` mints `turn_id` at the moment the user's input is accepted, **before** any
   parse or grounding work starts.
2. Every **turn-scoped** message on `praxis_coxswain` carries the envelope
   `{ v: 1, session_id, turn_id, kind, seq, ts, payload }`. A turn-scoped message missing
   `turn_id` is **rejected loudly** by the receiver (logged + surfaced as a system line), never
   defaulted or auto-minted downstream.
3. There is exactly one closed, enumerated set of **session-scoped** kinds that legitimately carry
   no `turn_id`: `coxswain.hello` and `coxswain.hello_ack` (§4.6's handshake). They carry
   `{ v, session_id, kind, seq, ts }` with `turn_id: null`, and the envelope validator accepts
   `turn_id: null` **only** for those two kinds — an unrecognized kind with a null `turn_id` is
   rejected exactly as before. The exemption is a whitelist in `envelope.js`, not a nullable
   field, so it cannot widen by accident. No session-scoped message may carry a payload that
   causes any physical action or any audit write.
4. The kernel-side gate echoes `turn_id` unchanged on every response and stamps it into every
   record it emits.
5. The parse worker echoes `turn_id` unchanged; it never mints one.
6. The audit writer refuses to persist any record whose `turn_id` is absent or does not match an
   open turn.

### 2.3 Shared retention contract

- All per-turn artifacts are persisted as **one** `CoxswainTurnRecord` aggregate keyed by
  `turn_id`, in a single L0 IndexedDB object store `coxswain_turns`. It contains the transcript
  entries, `PendingIntent` history, `FftDecision[]`, `StalenessFingerprint[]`, and
  `ExecutionOutcome` for that turn.
- **Turn lifecycle.** A turn is `open` from the moment `turn_id` is minted. It becomes `closed`
  on the first of: an `ExecutionOutcome` being written (any `status`, including `failed` and
  `aborted_stale`); the user cancelling or dismissing the card; or the gate reaching a terminal
  block with the card dismissed and no re-entry pending. A turn found still `open` at session
  init — i.e. the tab closed mid-turn — is closed as `abandoned` at load, with `closed_at` set to
  the load time. `state ∈ {open, closed, abandoned}` and `closed_at` are fields on the record
  (§2.4). A clarification round-trip does **not** close a turn; a turn can stay open for as long
  as the user takes to answer.
- Eviction is **atomic per turn record and never per-trail**. FIFO over whole turn records, with
  a configurable cap (default 1000 turns). It is structurally impossible for one trail to be
  evicted while another survives — which is the specific failure Failure 4 described.
- **Eviction never targets an open turn.** The FIFO is over `closed` and `abandoned` records only,
  oldest `closed_at` first. An open turn is skipped regardless of age, so a long-lived tab cannot
  have the turn the user is currently looking at truncated out from under it. The cap may
  therefore be exceeded transiently by open turns; if open turns alone reach `cap + 16`, the store
  stops accepting new turns and surfaces a loud system line rather than evicting one (this is a
  pathological state — it means turns are being minted and never resolved — and it should be
  visible, not absorbed).
- `OverrideRecord`s live in a separate store `coxswain_overrides` and are **exempt from
  eviction**; they retain their `turn_id` so an exported override can still be joined to an
  exported turn record even after the turn itself was evicted.
- L1 `persist()`, L2 File System Access working folder, and L3 export/import all treat both
  stores as one bundle. An L3 export writes both stores plus the transcript into a single JSON
  document keyed by `turn_id`.

### 2.4 Record shapes

Defined in `coxswain/src/coxswain/records.py` as frozen dataclasses:

- `CoxswainTurnRecord` — `{schema_version: int, turn_id, session_id, state: "open"|"closed"|"abandoned", opened_at: float, closed_at: float | None, transcript, pending_intents, decisions, fingerprints, outcome}`. The persisted aggregate of §2.3.
- `FftDecision` — `{turn_id, session_id, gate_seq, cue: int, category: "initial"|"re_entry"|"confirm_recheck", disposition: str, payload_kind: str, card_revision: int, ts: float, fingerprint_id: str | None, override_id: str | None}`. The N6 "3-field log" is `category`/`cue`/`disposition`; the remaining fields are the correlation and provenance keys this section mandates.
- `StalenessFingerprint` — `{fingerprint_id, turn_id, gate_seq, card_revision, taken_at: float, concurrency_active: bool, precondition_digest: str}`.
  - **Compared fields (FR-6): exactly `concurrency_active` and `precondition_digest`.**
  - **Provenance only, excluded from comparison: `fingerprint_id`, `turn_id`, `gate_seq`,
    `card_revision`, `taken_at`.** These exist so a drift abort can be reconstructed afterwards;
    they necessarily differ between passes and comparing them would abort every execution.
  - `compare(a, b) -> bool` in `fft/fingerprint.py` is the **only** place the compared field set
    is enumerated. A test asserts that adding a field to the dataclass does not change
    `compare`'s behavior on two records differing only in the new field.
- `OverrideRecord` — `{schema_version: int, override_id, turn_id, gate_seq, cue: int, justification: str, ts: float}`.
- `PendingIntent` — `{turn_id, parsed_call, resolved_slots, exited_cue, unresolved_slots, candidates, card_revision}`. `unresolved_slots` is what FR-8's re-enter-the-same-cue rule tests for emptiness before advancing.
- `ExecutionOutcome` — `{turn_id, gate_seq, status: "ok"|"failed"|"aborted_stale", detail: str | None, ts: float}`.

`disposition` is a closed vocabulary: `continue`, `pass`, `blocked:concurrent`,
`blocked:stale_card`, `blocked:audit_unavailable`, `clarify:incomplete`, `clarify:not_found`,
`clarify:disambiguate`, `clarify:precondition`, `override:precondition`, `aborted:drift`.

### 2.5 Schema versioning and upgrade policy

`SCHEMA_VERSION: Final[int]` lives in `coxswain/src/coxswain/records.py` and is mirrored as the
IndexedDB database version in `audit_store.js`. Both persisted aggregates (`CoxswainTurnRecord`,
`OverrideRecord`) carry `schema_version` in the record body as well, so an exported L3 bundle is
self-describing independently of the database it came from.

The upgrade policy is **loud refusal with read-only degrade** — MVP performs no migration:

- Record `schema_version` **equal** to the running build's: normal operation.
- Record `schema_version` **greater** than the running build's (an older build opening a store a
  newer build wrote): the store opens **read-only**. Existing turns remain readable and
  exportable. Coxswain refuses to mint new turns and surfaces a persistent, non-dismissable system
  line naming both numbers: "Coxswain's audit store was written by a newer build (schema 4, this
  build understands 3). Existing records are readable; Coxswain will not run until you update."
  This is fail-closed by necessity: FR-9 makes every disposition contingent on a durable audit
  write, so a store that cannot be written is a store in which nothing may execute.
- Record `schema_version` **lower** than the running build's: same read-only degrade and the same
  loud line, phrased for the older-data direction. A migration path may be added later by a spec
  amendment that names the source and target versions; until such an amendment exists, an
  implementation **must not** silently coerce, backfill, or drop fields.

There is deliberately no configuration flag that downgrades any of these to a warning.

---

## 3. Structural safety constraints (mitigate pre-mortem Failures 1-3)

These three are **hard requirements with their own acceptance criteria**, not clauses inside a
larger story. Each pre-mortem failure narrative traced back to a safety property that was
documented but not structurally enforced; each is answered here with a mechanism a code change
would be needed to defeat.

### 3.1 Confirm is blocked in code while re-grounding is in flight (Failure 1)

The card maintains a per-field validation state:
`validated | dirty_unvalidated | revalidating | awaiting_clarification | invalid`.

`awaiting_clarification` (added per C16) covers the case the original four-state vocabulary had no
slot for: an inline symbolic-field edit whose cue-2 re-grounding comes back
`clarify:disambiguate` or `clarify:not_found` rather than resolving. The new value is neither
valid nor provably invalid — it is ambiguous, and the user must choose. Handling:

- The field enters `awaiting_clarification` and renders "needs a choice — Coxswain found 2
  matches" beneath it. Confirm stays blocked (only `validated` counts in the derivation below).
- `card_revision` does **not** change; the edit is already counted.
- The turn emits a clarification card for that slot at a new `gate_seq`, exactly as a first-pass
  cue-2 exit would, and the proposal card stays on screen behind it.
- Resolving the clarification moves the field to `revalidating` and then to `validated` or
  `invalid`. Dismissing the clarification without answering reverts the field to its last
  `validated` value and re-renders the original proposal; it never leaves a resolved-looking field
  that was never resolved.

Confirm is blocked at **three independent layers**, each of which must independently deny:

1. **Presentation** — the Confirm control carries `disabled` and `aria-disabled="true"`, and the
   card renders the visible "unvalidated — re-checking" state on each affected field.
2. **Handler** — the Confirm handler recomputes
   `confirm_enabled = all(f.state == "validated" for f in fields) and not gate_in_flight`
   from the DOM-free card-state module and returns early without emitting any message when it is
   false. This catches a fast click, an Enter keypress on a stale focus, and a programmatic
   dispatch alike.
3. **Kernel** — the execute entrypoint rejects any execute request whose `card_revision` differs
   from the `validated_revision` stamped by the last completed validation pass, with disposition
   `blocked:stale_card`.

Layer 3 is the authoritative one: it is Python, it is in `coxswain/`, and it is therefore gated
by `pytest` rather than by a UI test harness that does not exist yet. **A visible cue alone does
not satisfy this requirement and must not be accepted at review.**

### 3.2 The N4 recon check is a blocking task with its own task_id (Failure 2)

The recon check is **W0** below. It carries its own `task_id`
(`260824_coxswain_n4_simulation_reuse_recon`), its own deliverable (a `transduction_log`
`append_recon` record with an explicit verdict field), and it **gates W2's cue-3 implementation
and W6 entirely**. No work item that touches pre-simulation or cue-3 precondition enumeration may
be picked up before W0's record exists. If W0's verdict is `db_coupled`, pre-simulation falls
through to N4-C — deferred out of this spec entirely, requiring a follow-up spec — and an inline
"minimal version for now" reimplementation is **prohibited**, since that is precisely the
divergence Failure 2 describes.

### 3.3 Override scope is a compile-time constant, not a configuration flag (Failure 3)

```
# coxswain/src/coxswain/schema/types.py
OVERRIDABLE_CUES: Final[frozenset[int]] = frozenset({3})
```

Design constraint, binding and not merely advisory: **widening override scope must require a
source change to this constant plus a new spec decision. It must never be achievable by
configuration, environment variable, build flag, feature toggle, URL parameter, or support
ticket.** Concretely:

- `OVERRIDABLE_CUES` is a module-level `Final[frozenset[int]]`. Nothing reads it from
  `os.environ`, a config file, a build argument, or a function parameter.
- Override eligibility is decided **only** in the gate, and shipped to the UI as a boolean
  `overridable` field on the exit payload. The UI never computes eligibility itself and has no
  copy of the cue list.
- The exit payload types for cues 0, 1 and 2 do not carry the override affordance fields at all,
  so an over-eager UI cannot render an override control for them even by mistake.

---

## 4. User-facing behavior

### 4.1 Message kinds in the Coxswain panel

Per the locked Chat UI design (F-locked), five kinds: user turn, propose/confirm card,
clarification card, execution-failure card, system/status line. This spec adds no sixth.

### 4.2 Propose/confirm card

```
┌──────────────────────────────────────────────────────────────┐
│ Transfer 50 µL from A1 to B3.                    [reversible] │
│ ⚠ large-volume                        (warnings, advisory)    │
│                                                               │
│ Volume   [ 50 ] µL          Source [ A1 ]     Target [ B3 ]   │
│                                                               │
│ ▸ Show the call                       (collapsed by default)  │
│ Coxswain asked which carrier because 2 matched "Hamilton".    │
│                                                               │
│                                    [ Cancel ]   [ Confirm ]   │
└──────────────────────────────────────────────────────────────┘
```

- Natural-language restatement is the primary reading. The literal call is collapsed secondary
  detail. The one-line disclosure appears only when a clarification preceded this proposal.
- Editing `Source` to `B3` immediately switches that field to
  `dirty_unvalidated`, showing `unvalidated — re-checking` beneath it; on blur (or 300 ms after
  the last keystroke, §4.7) it becomes `revalidating`; when cue-2 re-grounding returns it becomes
  `validated`, `invalid`, or `awaiting_clarification` (§3.1). If re-grounding does not return
  within 2 s it fails closed to `invalid` with "Coxswain could not check 'B3' in time." Confirm is
  blocked throughout (§3.1).
- For an `irreversible` tier the Confirm row is replaced by:
  `Type "discard tips at C3" to confirm: [        ]  [ Confirm ]` with Confirm inert until the
  typed text matches.

### 4.3 Clarification card

Renders the exit payload directly, with the N5-B categorization applied only where a real
candidate set exists:

```
Coxswain found 2 carriers that match "the plate carrier".

Matches       PLT_CAR_L5AC_A00 on rails 7  ·  PLT_CAR_P3AC_A00 on rails 13
Conflicts     Both accept the plate you named.
Omissions     You did not say which rail.

[ rails 7 ]  [ rails 13 ]        or type/say a rail number
```

Simultaneously, rails 7 and 13 are highlighted on the Visualizer panel (FR-11). Clicking a
candidate resolves the slot deterministically and re-enters the gate at **cue 2** — the cue that
exited — per FR-8. Cue 2 then either exits again on the next unresolved slot in the same call, or,
having none, advances to cue 3.

For a cue-3 exit, the card additionally renders — and only for cue 3 —
`Override this check:  [ justification ] [ Override ]`, per §3.3.

### 4.4 Staleness abort

If the confirm-time fingerprint differs from the propose-time one on either compared field
(FR-6), execution does not happen. The card is replaced by a system line naming the specific
drift — `concurrency_active` flipped false→true yields "A protocol run started while this proposal
was open."; a changed `precondition_digest` yields "The tip state on channel 1 changed since
Coxswain checked." — and the turn re-enters the gate at cue 0 with a new `gate_seq`. Nothing is
silently repaired.

### 4.5 The concurrency signal source (cue 0)

RISK-7 is that cue 0 has no defined concurrency source in web-repl. The interface and its signal
source are therefore both specified here rather than left to the implementer.

```python
# coxswain/src/coxswain/fft/concurrency.py
class ConcurrencyProbe(Protocol):
    def is_active(self) -> bool | None: ...   # None == cannot determine
```

`None` maps to `blocked:concurrent` (NFR-5). The MVP implementation is
`KernelExecutionProbe`, and its signal is **kernel-resident, in-process, and read at call time**
from two sources, OR'd:

1. **`ExecutionFlag`** (`coxswain/src/coxswain/runtime/execution_flag.py`) — a module-level
   reentrancy counter that `execute.py` increments before dispatching any PLR call and decrements
   in a `finally`. This covers every Coxswain-initiated execution.
2. **`DispatchWatch`** — a counter incremented and decremented by a thin wrapper installed over
   the resident `LiquidHandler`'s dispatch entrypoint at Coxswain init. This covers PLR calls a
   user issues **directly from a notebook cell**, which source 1 cannot see. It is needed because
   the kernel is single-threaded but not non-interleaving: an `await` inside a user's cell yields
   control, and a Coxswain gate pass can run in that window.

Both sources live in the same interpreter as the gate, so reading them is a local attribute read
with no round trip and no timeout. There is no BroadcastChannel hop and therefore no
"probe unreachable" case for the MVP probe — `None` is reserved for a future out-of-process probe
(Production Mode, §7) and for the case where `DispatchWatch` failed to install at init, which is
itself an unknown and must block.

**Named residual gap:** a PLR call reaching hardware by a path that bypasses both the Coxswain
executor and the wrapped dispatch entrypoint (e.g. a user holding a direct reference to a backend
object) is invisible to this probe. This is a known limitation of an in-process probe, is recorded
here rather than discovered later, and is a reason cue 3 and FR-6's confirm-time re-check exist
rather than cue 0 alone being trusted.

AC-16 gates the thing that actually goes wrong here: a probe that returns "not active"
unconditionally would satisfy every other criterion in this spec.

### 4.6 Visualizer `session_id` handshake (FR-11)

`visualizer/index.html` is a **separate document**. It never runs `coxswain-shell.js`, so it has
no `session_id` of its own, and RISK-12's "receivers drop messages whose `session_id` is not their
own" is not implementable there without a handshake. The handshake:

1. When the Coxswain shell creates or reuses the visualizer frame, it sets the frame `src` with
   `?coxswain_session=<session_id>` appended.
2. `coxswain/viz_highlight.js` reads `coxswain_session` from `location.search` at module load and
   stores it as its own `session_id`.
3. It then posts `{kind: "coxswain.hello", session_id}` on `praxis_coxswain`. The shell replies
   `{kind: "coxswain.hello_ack", session_id}` only if the id matches its own.
4. **Highlights are honored only after a matching `hello_ack` has been received.** Before that —
   and for any highlight message whose `session_id` does not match — the module **ignores the
   message** (fail closed) and logs one debug line per session, not per message.

A visualizer page opened directly, outside the shell, therefore has no `coxswain_session`
parameter, never completes the handshake, and never draws a highlight. That is the intended
behavior, not a degradation: a highlight with no owning session has no meaning.

### 4.7 Timing constants (H1)

One module per side, so these are changed in one place and are visible to review:
`web-repl/shell/coxswain/timing.js` and `coxswain/src/coxswain/timing.py`, asserted equal by a
test in W1.

| Constant | Value | Applies to |
|---|---|---|
| `EDIT_DEBOUNCE_MS` | `300` | FR-4 inline-edit re-grounding. Blur flushes immediately without waiting out the interval. |
| `REGROUND_TIMEOUT_MS` | `2000` | Cue-2/cue-3 re-grounding after an inline edit. On expiry the field fails closed to `invalid` (never to `validated`). |
| `KERNEL_RTT_TIMEOUT_MS` | `5000` | NFR-5's "kernel round-trip timeout", and FR-9's audit-ack flush window. On expiry the pass exits `blocked:*`, never `continue`. |

The two edit-path values are deliberately different: 300 ms is a typing pause, 2 s is a work
budget, and collapsing them into one number is how a debounce silently becomes a timeout. These
are first-cut values chosen to be revisited against real latency measurements; what is normative
is that each has **a** value and that expiry is always the fail-closed direction.

---

## 5. Acceptance criteria (spec level)

Each is concrete and executable. Work-item-level gates in §6 refine these.

**None of these criteria is satisfied until W1.0's CI job exists and runs them.** A command that
is only ever typed by hand is not a gate; pre-mortem Failure 1's root cause was stated as
"nothing failed CI", and until `coxswain/tests` and `bun test web-repl/shell/coxswain` are
collected by a workflow, every AC below is a local-only convention. AC-18 is the criterion that
makes the rest enforceable and is a prerequisite of all of them, not a peer.

- **AC-1a (W1)** `uv run pytest coxswain/tests -q` passes, and
  `uv run python -c "import coxswain.records, coxswain.ids, coxswain.schema.types"` succeeds in
  plain CPython (NFR-1). Scoped to the modules W1 creates — `coxswain.fft` does not exist yet at
  W1, so an AC naming it would be red by construction there.
- **AC-1b (W2)** `uv run python -c "import coxswain.fft.gate"` additionally succeeds in plain
  CPython, completing NFR-1's coverage once the gate package exists.
- **AC-2** `uv run pytest coxswain/tests/test_import_boundary.py` asserts no module under
  `coxswain/src/` contains an import of `praxis.backend` (NFR-2), and none contains a
  module-level `import js`.
- **AC-3** `bun test web-repl/shell/coxswain` passes with zero installed dependencies (NFR-3).
- **AC-4 (Failure 1 gate, load-bearing)** A test dispatches Confirm while a symbolic field is in
  `revalidating` and asserts **no execute message is emitted**; a second test posts an execute
  request whose `card_revision` is one behind `validated_revision` and asserts the kernel returns
  `blocked:stale_card` and performs no PLR call. Both must pass. A test that only asserts the
  presence of a CSS class or an `aria-disabled` attribute does **not** satisfy AC-4.
- **AC-5 (Failure 2 gate)** A `transduction_log` recon record with `task_id`
  `260824_coxswain_n4_simulation_reuse_recon` exists and contains an explicit
  `verdict ∈ {reusable, db_coupled, partially_reusable}` before W2's cue-3 item or W6 is started.
- **AC-6 (Failure 3 gate)** `coxswain/tests/test_override_constant.py` asserts
  `OVERRIDABLE_CUES == frozenset({3})`; asserts `request_override()` raises for cues 0, 1, 2;
  greps the `coxswain/src/` tree asserting `OVERRIDABLE_CUES` is never read from
  `os.environ`, `os.getenv`, a config loader, or a function argument; **and asserts §3.3's
  structural claim rather than restating it** — for each cue in `{0, 1, 2}`, the exit payload
  dataclass for that cue has no override-related field, checked by introspecting
  `__dataclass_fields__` against the override field-name set (`overridable`, `override_prompt`,
  `justification`), while cue 3's payload does carry them. A payload type that gains an override
  field by copy-paste then fails a test instead of silently enabling an override control.
- **AC-7 (Failure 4 gate)** Given a synthetic turn that clarifies once, overrides once at cue 3,
  and then aborts on drift, a single query by `turn_id` returns the `PendingIntent` history, all
  `FftDecision` records, both `StalenessFingerprint` records, the `OverrideRecord`, and the
  `ExecutionOutcome` — with no manual stitching. A second test evicts that turn record and
  asserts the `OverrideRecord` survives with its `turn_id` intact.
- **AC-8** Every function in the PLR tool schema carries exactly one `risk_tier`; a property test
  asserts `tier_of(call) == tier_of(schema[call.name])` for randomized parameters — i.e. tier is
  provably independent of parameters (N1 auditability).
- **AC-9** Cues re-run at confirm time are exactly `{0, 3}` and produce exactly one
  `StalenessFingerprint`. Three assertions, all required:
  1. Two fingerprints differing **only** in `taken_at`, `gate_seq`, `fingerprint_id` and
     `card_revision` — the realistic no-drift case — compare **equal**, and execution proceeds.
     (Without this the spec's own comparison rule aborts every execution ever attempted.)
  2. Two fingerprints differing in `concurrency_active`, and separately two differing in
     `precondition_digest`, each yield `ExecutionOutcome.status == "aborted_stale"` and zero PLR
     calls.
  3. Adding a new field to `StalenessFingerprint` and giving two records different values for it
     leaves `compare()` returning equal — the compared set is closed and enumerated in one place
     (§2.4).
- **AC-10** A relay-unreachable test asserts every local audit write still completes, that its
  latency is unaffected, and that with no relay endpoint configured **zero** network requests are
  issued.
- **AC-11** A build without `--with-coxswain` produces a dist whose asset manifest contains no
  entry whose path includes `coxswain`, and `uv run python web-repl/scripts/build_repl.py`'s
  existing `assert_dist_complete` / inject-shell checks pass unchanged. **The path-substring half
  is not sufficient on its own** and must be paired with two content assertions, because the file
  most likely to smuggle Coxswain code into a default build has no `coxswain` in its path:
  1. `dist/.../assets/visualizer-augmentations/index.js` in a default build is **byte-identical**
     (sha256) to the tracked `web-repl/overlay/assets/visualizer-augmentations/index.js`.
  2. A default build's `dist/.../assets/visualizer/index.html` contains **no** `<script>` tag
     referencing `coxswain`, and a `--with-coxswain` build contains exactly one.
- **AC-12** Under a simulated `prefers-reduced-motion: reduce`, the highlight module returns a
  static-outline directive with no animation frames (NFR-6/N8-B).
- **AC-13 (irreversible friction gate, mirrors AC-4's structure)** For an `irreversible`-tier
  card, a Confirm dispatch emits **no** execute message when the typed phrase is empty, a strict
  prefix of the required phrase, the required phrase with one character changed, or the required
  phrase from a *different* call. Tested at both layers, and both must pass:
  - **JS** — `web-repl/shell/coxswain/__tests__/phrase.test.js` asserts `confirm_enabled` is false
    and the handler returns without emitting, for each of the four cases plus the multi-target
    phrase of FR-3.
  - **Kernel** — `coxswain/tests/test_execute_phrase_guard.py` posts an execute request for an
    `irreversible` call carrying a missing or mismatched `typed_phrase` directly to the execute
    entrypoint and asserts it is rejected with zero PLR calls. A UI that forgets the check does
    not reach hardware.
  A test that only asserts a `disabled` attribute does **not** satisfy AC-13.
- **AC-14 (tier floor)** AC-8 proves tier is independent of parameters; AC-14 constrains the
  assignment itself, because a schema tagging every function `read_only` satisfies AC-8 and
  bypasses the entire product (`read_only` executes on propose with no confirmation).
  `coxswain/tests/test_tier_floor.py` asserts:
  1. **No state-mutating call is `read_only`.** At minimum `drop_tips`, `discard_tips`,
     `pick_up_tips`, `aspirate`, `dispense`, `transfer`, `move_resource`, `move_plate`,
     `move_lid` — plus, structurally, every schema entry whose declared effect set is non-empty —
     carries `reversible` or `irreversible`.
  2. **The irreversible family is `irreversible`**: `drop_tips` / `discard_tips` to waste and
     dispense-to-waste calls.
  3. The check is **closed over the schema**, not a hand-listed allowlist: a newly added schema
     entry declaring a state mutation and tagged `read_only` fails the test without anyone
     remembering to update it.
- **AC-15 (output encoding, NFR-7)** A structural test asserts no source file under
  `web-repl/shell/coxswain/` or `web-repl/overlay/assets/coxswain/` contains `innerHTML`,
  `outerHTML`, `insertAdjacentHTML`, `document.write`, or `setHTML`; and a `bun test` renders a
  candidate label of `<img src=x onerror=alert(1)>` and asserts the resulting node has zero
  element children and a `textContent` equal to the input. A second test asserts each of NFR-7's
  caps truncates rather than rejects.
- **AC-16 (ConcurrencyProbe is backed by a real read, §4.5)** Three assertions:
  1. With the `ExecutionFlag` counter forced to a non-zero value, `probe.is_active()` returns
     `True` and cue 0 exits `blocked:concurrent`.
  2. With it zero and `DispatchWatch` non-zero, the same.
  3. **A probe whose `is_active()` ignores its sources fails the suite**: the test flips each
     source and asserts the probe's return value flips with it, so a constant-`False`
     implementation cannot pass. Additionally, `probe.is_active()` returning `None` (source not
     installed) asserts a `blocked:concurrent` exit, not `continue`.
- **AC-17 (RISK-9 mitigation)** Forcing an IndexedDB `QuotaExceededError` on an audit write
  asserts: the write does not silently drop; a loud system line naming the store and the failed
  `turn_id` is rendered; and the gate pass that issued it exits `blocked:audit_unavailable` with
  zero PLR calls (FR-9's fail-closed clause).
- **AC-18 (CI enforcement, prerequisite of every other AC)** A GitHub Actions job exists that runs
  `uv run pytest coxswain/tests -q` and `bun test web-repl/shell/coxswain`, is triggered by
  changes under `coxswain/**` and `web-repl/**`, and has been **observed failing** — a deliberately
  broken assertion is pushed once and the job is confirmed red before the fix lands. A gate only
  ever seen green is not known to be wired to anything (this repo's `repl.yml` header states that
  rule for itself).
- **AC-19 (audit ordering, FR-9)** A test intercepts the audit sink and asserts the gate's
  disposition is not emitted before the corresponding `audit.ack` is received; a second test drops
  the ack entirely and asserts the pass exits `blocked:audit_unavailable` after
  `KERNEL_RTT_TIMEOUT_MS` with zero PLR calls; a third asserts the relay being unreachable or slow
  changes neither the ack timing nor the disposition (with AC-10).
- **AC-20 (multi-slot clarification, FR-8)** A `transfer` whose source **and** target are both
  ambiguous resolves both before cue 3 is ever reached: the test asserts the `FftDecision`
  sequence is cue 2 → cue 2 → cue 3 (not cue 2 → cue 3), that `gate_seq` increments on each
  re-entry, and that `PendingIntent.unresolved_slots` is empty at the moment cue 3 first runs. A
  re-enter-at-the-next-cue implementation fails this test.
- **AC-21 (schema versioning, §2.5)** Opening a store whose records carry a `schema_version`
  greater than the build's asserts: the store is readable, an L3 export still succeeds, **no**
  write is accepted, no new turn can be minted, and the system line naming both version numbers is
  rendered. The lower-version direction asserts the same. No test may pass by silently coercing
  the record.

---

## 6. Work-item decomposition

### 6.1 Deviation from the brainstorm's W0-W4, and why

The brainstorm proposed W0 (N4 recon, blocking), W1 (FFT gate extensions), W2 (propose/confirm
card), W3 (clarification card), W4 (audit trail). I am keeping that spine but making **two
changes**, as the specification authority:

1. **Split out a new W1 "contracts and record schema foundation"**, pushing the gate work to W2
   and shifting the rest down. Reason: the correlation contract of §2 (`turn_id`, the envelope,
   the record dataclasses, `OVERRIDABLE_CUES`, the shared retention aggregate) is consumed by
   every one of the brainstorm's W1-W4. If it is built inside the audit-trail item — which lands
   last — then the gate, the propose card and the clarification card will each improvise their own
   identifiers first. That is pre-mortem Failure 4's root cause reproduced in the work ordering,
   not just in the code. The foundation must land before its first consumer.
2. **Add a conditional W6 for pre-simulation**, explicitly gated on W0's verdict. The brainstorm
   left N4's implementation home implicit; naming it as a distinct, conditional, blocked item is
   what makes "the recon check gates real work" mean something concrete (Failure 2).

Mapping: brainstorm W0 → **W0**; brainstorm W1 → **W2**; brainstorm W2 → **W3**; brainstorm W3 →
**W4**; brainstorm W4 → **W5**; new items **W1** (foundation, whose first sub-item **W1.0** is the
CI wiring) and **W6** (conditional pre-simulation).

### 6.1a Recorded deviations from the locked architecture and the brainstorm

Deviations are recorded, not hidden. Each below is a deliberate choice this spec makes that
differs from the wording of an upstream document; none reopens a locked architectural decision.

| # | Deviation | From | Why it is defensible |
|---|---|---|---|
| D-A | Coxswain's browser-facing JS lives **permanently** under `web-repl/shell/coxswain/` (plus `web-repl/overlay/assets/coxswain/` for the visualizer module), authored there and staged from there. It is **not** authored inside `coxswain/` and vendored into the build. | Scoping doc line 220, which implies coxswain's browser-facing pieces vendor into the static build "rather than hand-copied", i.e. that `coxswain/` is the authoring home for JS too. | It mirrors the existing, working `praxis-shell.js` injection pattern (`stage_shell` / `run_inject_shell`), which is the sanctioned seam this repo already has and already sha-tracks. The part of Coxswain that is genuinely reusable and extractable is the **Python** half — the gate, the records, the tier schema — and that stays wholly in `coxswain/` with its own import boundary (NFR-2). Splitting the JS into a second authoring home would buy nothing but a copy step and a drift detector for it. Manifest/sha tracking, which is what line 220 was actually protecting, is preserved either way. |
| D-B | `StalenessFingerprint` is both an audit record **and** the abort trigger (FR-6). | Brainstorm N3-C, which described the record as existing "purely for the audit trail". | No new machinery is introduced: the two compared fields are literally cue 0's and cue 3's own return values on a pass the spec already performs. Formalizing them as a typed record is what makes the abort reconstructable afterwards. N3-A — a general state-diff/drift-detection subsystem — remains rejected, and this deviation does not smuggle it back in: see FR-6 and §2.4's closed compared-field set. |
| D-C | The Coxswain visualizer subscriber is a new conditionally-staged file rather than an edit to `visualizer-augmentations/index.js`. | The obvious reading of "the augmentation file is the sanctioned seam" (RISK-11, and the 260817 findings). | The augmentation file ships in **every** build (`build_repl.py:864`), so editing it would falsify FR-12. The seam principle is honored — the new module is a sibling under `overlay/assets/`, loaded by an injected `<script>` tag exactly as the augmentation file is, and never forks vendored draw code. See FR-12 and AC-11. |

### 6.2 Dependency graph

```
W0 (recon, blocking) ──────┬──> W2.cue3 ──> W3 ──> W4
                           └──> W6 (conditional, only if verdict != db_coupled)
W1.0 (CI) ──> W1 (foundation) ──> W2 ──> W3 ──> W4
                                   └──────────────> W5
```

W1 has no dependency on W0 and the two can proceed in parallel. W1.0 lands before the rest of W1,
so the foundation's own tests are enforced from their first commit. **W5 depends on W1 and W2
only** — it is independent of W3 and W4 and may run in parallel with them; the graph's first line
carries no edge into W5 (an earlier revision drew one, contradicting W5's own text — C14).

---

### W0 — N4 simulation-reuse recon check (BLOCKING)

**task_id**: `260824_coxswain_n4_simulation_reuse_recon` (its own task, not a sub-item of W2)

Read and grep `praxis/backend/core/simulation/simulator.py`,
`praxis/backend/core/simulation/failure_detector.py`, and
`praxis/backend/core/simulation/pipeline.py` (which holds `HierarchicalSimulator`) for:
SQLAlchemy / SQLModel imports, DB-session parameters or attributes, `WorkcellRuntime` coupling,
Redis/`PraxisState` coupling, and any transitive import that pulls in `praxis.backend.core` or
`praxis.backend.models`. Apply the same test that already disqualified `state_resolution.py`
per the scoping doc's Composition correction. Also check
`praxis/backend/core/simulation/bounds_analyzer.py` and `method_contracts.py`, since the
precondition-enumeration logic cue 3 would want may live there rather than in the three named
modules.

**Files**: read-only across `praxis/backend/core/simulation/*.py` (no modification).
**Deliverable**: a `transduction_log` `append_recon` record under this task_id whose findings
include a top-level `verdict` of `reusable` | `partially_reusable` | `db_coupled`, per-module
import evidence with line numbers, and — if `partially_reusable` — the named subset that is
dependency-free.
**Gate**: `transduction_query(scope="task", task_id="260824_coxswain_n4_simulation_reuse_recon")`
returns a recon record containing a `verdict` field. AC-5.
**Blocks**: W2's cue-3 precondition sub-item, and W6 in its entirety.
**Scope estimate**: ~0 LOC (recon only); ~1 short session.

---

### W1.0 — CI wiring and harness proof (LANDS FIRST, gates everything)

Every acceptance criterion in §5 is a shell command that no workflow currently runs. Verified:
the root `pyproject.toml` sets `testpaths = ["tests"]`, so `ci.yml` never collects
`coxswain/tests`; `repl.yml`'s Tests step enumerates `web-repl/tests/*.py` **by name**, so a new
file is not picked up by accident; `repl.yml`'s `paths:` triggers (lines 17-31) list `web-repl/**`
but **not** `coxswain/**`; and no workflow in the repo invokes `bun` at all. Until this item
lands, "nothing failed CI" — pre-mortem Failure 1's stated root cause — is the literal state of
this spec's gates.

Three sub-tasks, in order:

1. **Prove the harness before depending on it.** `bun test` needs no `package.json` by design, but
   that is a claim this repo has never executed. Land one trivial DOM-free module plus its test
   under `web-repl/shell/coxswain/` and confirm `bun test web-repl/shell/coxswain` discovers and
   runs it, both locally and on the runner. NFR-3 makes every JS safety criterion depend on this
   harness; discovering at W3 that it does not work would strand AC-4's JS half (C35).
2. **Add the CI job.** A `coxswain` job running, at minimum:
   `uv run pytest coxswain/tests -q` (an explicit path argument, which overrides `testpaths` — do
   not assume the root config will collect it) and `bun test web-repl/shell/coxswain`, with a
   `oven-sh/setup-bun` step. Placed in `repl.yml` alongside the existing browser gates rather than
   in `ci.yml`, since its subject is the web-repl-delivered product.
3. **Extend the path triggers.** Add `coxswain/**` to **both** the `push` and `pull_request`
   `paths:` lists in `repl.yml` (they are duplicated deliberately — that file's own comment
   explains GitHub Actions rejects YAML anchors here, so both copies must be edited).
   `web-repl/**` already covers `web-repl/shell/coxswain/**`.

**Observe the job fail before trusting it.** Push one deliberately broken assertion, confirm the
job goes red, then fix it. `repl.yml`'s own header states this rule for its existing steps
("none of them is a check that has only ever been seen green"); this job is held to it too.

**Files**: modify `.github/workflows/repl.yml`. Create
`web-repl/shell/coxswain/__tests__/harness_smoke.test.js` and the trivial module it exercises.
**Gate**: AC-18 — the job exists, is triggered by a `coxswain/**`-only change, and has been
observed red.
**Depends on**: nothing.
**Scope estimate**: ~60 lines of workflow YAML + ~20 LOC.

---

### W1 — Contracts, record schema, and persistence foundation

Create the correlation contract of §2 and the structural constants of §3.3 as code, with no
gate, card, or model logic. This is deliberately the boring item and it lands first (after W1.0).

- `records.py` — the six frozen dataclasses of §2.4, `SCHEMA_VERSION`, the closed `disposition`
  vocabulary, and NFR-7's kernel-side string caps.
- `ids.py` — `mint_turn_id()`, `fingerprint_id_for()`, `override_id_for()`.
- `schema/types.py` — `RiskTier`, `CueId`, `Disposition`, the per-cue exit payload types (with
  cues 0/1/2 payloads structurally lacking override fields), and
  `OVERRIDABLE_CUES: Final[frozenset[int]] = frozenset({3})`.
- `timing.py` + `web-repl/shell/coxswain/timing.js` — §4.7's three constants, with a test
  asserting the two sides agree.
- `persistence/store.py` — the `CoxswainTurnRecord` aggregate, the turn lifecycle of §2.3
  (`open`/`closed`/`abandoned`, `closed_at`, abandon-on-load), the eviction policy — **FIFO over
  closed records only, never an open turn** — the override-store exemption, and §2.5's
  schema-version check, as a pure interface with an injected backend (no IndexedDB code here —
  that is W5's JS side).
- `web-repl/shell/coxswain/envelope.js` — DOM-free envelope build/validate; rejects a missing
  `turn_id` loudly.

**Files**: create `coxswain/src/coxswain/records.py`, `coxswain/src/coxswain/ids.py`,
`coxswain/src/coxswain/timing.py`,
`coxswain/src/coxswain/schema/__init__.py`, `coxswain/src/coxswain/schema/types.py`,
`coxswain/src/coxswain/persistence/__init__.py`, `coxswain/src/coxswain/persistence/store.py`,
`web-repl/shell/coxswain/envelope.js`, `web-repl/shell/coxswain/timing.js`,
`web-repl/shell/coxswain/__tests__/{envelope,timing}.test.js`,
`coxswain/tests/test_records.py`, `coxswain/tests/test_override_constant.py`,
`coxswain/tests/test_retention.py`, `coxswain/tests/test_schema_version.py`,
`coxswain/tests/test_timing_parity.py`, `coxswain/tests/test_import_boundary.py`.
Modify: `coxswain/README.md` (status line), root `pyproject.toml` only if the uv workspace member
is not yet registered.
**Gate**: `uv run pytest coxswain/tests -q` and `bun test web-repl/shell/coxswain`, **run by
W1.0's CI job**. Satisfies AC-1a, AC-2, AC-3, AC-6, AC-7's retention half (including the
open-turn-never-evicted case), AC-21.
**Depends on**: W1.0.
**Scope estimate**: ~550 LOC + ~320 LOC tests.

---

### W2 — FFT gate extensions (N1 tiering, N3 fingerprint, N6 emission, N7 override)

Implement the gate as a pure Python module in coxswain core, kernel-resident, consuming W1's
types. Cues 0-3 already have their semantics fixed by F4; this item adds the four axis
extensions and the `ConcurrencyProbe`/`GroundingSource` interfaces the cues call.

- `fft/cues.py` — the four cue functions, each `(parsed_call, grounded_context) -> Continue | Exit`,
  each stamping an `FftDecision`.
- `fft/gate.py` — pass orchestration, `gate_seq` management, re-entry-at-next-cue after a
  clarification, confirm-time re-check restricted to `{0, 3}`, `request_override()` enforcing
  `OVERRIDABLE_CUES`, and fail-closed handling (NFR-5).
- `fft/fingerprint.py` — capture and compare `StalenessFingerprint`. `compare()` is the **only**
  place FR-6's compared field set (`{concurrency_active, precondition_digest}`) is enumerated;
  provenance fields are excluded there and nowhere else. Any difference in those two →
  `aborted:drift`. No benign-drift classification exists in this file, by design.
- `fft/concurrency.py` — the `ConcurrencyProbe` protocol of §4.5, the `None → blocked:concurrent`
  mapping, and `KernelExecutionProbe`, which reads the two named in-process sources.
- `runtime/execution_flag.py` — the `ExecutionFlag` reentrancy counter and the `DispatchWatch`
  wrapper installer. Kernel-resident, pure Python, no `import js` (NFR-1): the counters are
  incremented by Coxswain's own executor and by a wrapper over the resident `LiquidHandler`'s
  dispatch entrypoint, both of which live in this interpreter. This is the file whose absence
  made RISK-7's "named as an explicit W2 deliverable" untrue in the previous revision.
- `plr/tool_schema.py` — the tool schema with static `risk_tier` per function, kept legibly
  separate from core per the naming decision.
- `plr/warnings.py` — advisory `warnings[]` computation (N1-B, demoted); must not be importable
  from the tier path.
- `plr/grounding.py` — Layer 2b instance resolution against live kernel objects; `resolve()` read
  path only.
- **Cue-3 sub-item (blocked on W0)** — precondition enumeration. If W0's verdict is `reusable`
  or `partially_reusable`, port the named dependency-free subset; if `db_coupled`, implement the
  minimal tip/volume/capacity/type checks directly against PLR's own trackers and record that
  choice as following N4-C.

**Files**: create `coxswain/src/coxswain/fft/{__init__,gate,cues,fingerprint,concurrency,context}.py`,
`coxswain/src/coxswain/runtime/{__init__,execution_flag}.py`,
`coxswain/src/coxswain/plr/{__init__,tool_schema,warnings,grounding}.py`,
`coxswain/tests/test_fft_gate.py`, `coxswain/tests/test_fingerprint.py`,
`coxswain/tests/test_tier_static.py`, `coxswain/tests/test_tier_floor.py`,
`coxswain/tests/test_concurrency_probe.py`, `coxswain/tests/test_reentry_multislot.py`,
`coxswain/tests/test_fail_closed.py`.
Must NOT import: `praxis.backend.*`, `js`, or anything from `web-repl/`.
**Gate**: `uv run pytest coxswain/tests -q` (the CI job of W1.0 runs the whole package; the
files above are the new ones). Satisfies AC-1b, AC-8, AC-9, AC-14, AC-16, AC-20, the cue-side half
of AC-6, and NFR-5.
**Depends on**: W1 (all), W0 (cue-3 sub-item only).
**Scope estimate**: ~850 LOC + ~620 LOC tests.

---

### W3 — Propose/confirm card (N1 friction, N2 editing, N5 default shape)

The panel shell plus the propose card, including the three-layer Confirm block of §3.1.

- `coxswain-shell.js` — injected side panel wrapping `<body>` in plain CSS (not Lumino docking),
  Chat/Visualizer tabs, `turn_id` minting at input capture, `praxis_coxswain` wiring.
- `shell/coxswain/card_state.js` — **DOM-free**: field validation state machine,
  `card_revision` increment, `confirm_enabled` derivation, confirmation-phrase derivation and
  matching. This is where AC-4's JS half is tested.
- `shell/coxswain/propose_card.js` — thin DOM adapter over `card_state.js`. All string rendering
  goes through `text.js` (below); this file contains no HTML string literals.
- `shell/coxswain/phrase.js` + `coxswain/src/coxswain/phrase.py` — FR-3's `derive_phrase`, on both
  sides, agreeing on the same fixtures, including the multi-target `+<n-1> more` rule.
- `shell/coxswain/text.js` — **DOM-free**: NFR-7's cap-and-truncate helper plus the
  `set_text(node, s)` primitive every renderer uses. Centralizing it is what makes AC-15's
  structural grep meaningful rather than a per-file discipline.
- **`shell/coxswain/failure_card.js` — the execution-failure card renderer** (§4.1's fourth
  message kind). Its data was already fully specified — `ExecutionOutcome.status`/`detail`, the
  `PendingIntent` history, and the joined `FftDecision[]` per AC-7 — but no work item built the UI
  that shows it, so a `failed` or `aborted_stale` outcome would have rendered nothing. Renders the
  outcome status, the failure detail, the call as attempted, and, for `aborted_stale`, §4.4's
  drift line. Read-only: it offers no retry affordance in MVP (a retry is a new turn, typed by the
  user, so it re-runs the whole gate).
- `coxswain/src/coxswain/execute.py` — the kernel-side execute entrypoint enforcing
  `card_revision == validated_revision` (§3.1 layer 3), enforcing the confirmation phrase for
  `irreversible` calls independently of the UI (AC-13's kernel half), and emitting
  `ExecutionOutcome`. It also owns `ExecutionFlag`'s increment/decrement (§4.5).
- `web-repl/scripts/build_repl.py` + `inject_shell.py` — the `--with-coxswain` flag, asset
  staging, and manifest/sha tracking (ADR §2.3, D1-D3), mirroring the existing `stage_shell` /
  `run_inject_shell` path at `web-repl/scripts/build_repl.py:812` and `:832`.
- A `ParseSource` interface with a fixture-backed stub implementation (see §7 — the model itself
  is out of scope), so the card is demoable and testable with no model present.

**Files**: create `web-repl/shell/coxswain-shell.js`,
`web-repl/shell/coxswain/{card_state,propose_card,failure_card,phrase,text}.js`,
`web-repl/shell/coxswain/__tests__/{card_state,phrase,text,failure_card}.test.js`,
`web-repl/overlay/assets/coxswain/coxswain.css`,
`coxswain/src/coxswain/execute.py`, `coxswain/src/coxswain/phrase.py`,
`coxswain/src/coxswain/parse_source.py`,
`coxswain/tests/test_execute_revision_guard.py`,
`coxswain/tests/test_execute_phrase_guard.py`, `coxswain/tests/test_phrase_parity.py`,
`coxswain/tests/fixtures/parsed_calls/*.json`.
Modify: `web-repl/scripts/build_repl.py`, `web-repl/scripts/inject_shell.py`,
`web-repl/scripts/build_manifest.py`.
**Gate**: `uv run pytest coxswain/tests -q` and `bun test web-repl/shell/coxswain` (via W1.0's CI
job) and a `--with-coxswain` / default build pair satisfying all three of AC-11's clauses.
Satisfies AC-4 (both halves), AC-11, AC-13 (both halves), AC-15.
**Depends on**: W1, W2.
**Scope estimate**: ~1050 LOC + ~500 LOC tests.

---

### W4 — Clarification card (N5-B categorization, N8-B highlight, deterministic answer matching)

- `clarify.py` — the deterministic matcher (label / position / simple synonym) over the
  already-fetched candidate set; **re-entry at the cue that exited, repeating until that cue's
  `unresolved_slots` is empty** (FR-8); no model call on the click path and none on the typed path
  in MVP (see §7).
- `categorize.py` — Matches / Conflicts / Omissions derivation from the Layer 2/3 candidate set.
  Applies to clarification cards only; a test asserts it is never invoked from the propose-card
  path.
- `shell/coxswain/clarify_card.js` — renders each exit payload kind distinctly
  (`disambiguate` candidate picker, `incomplete` field prompt, `precondition` explanation +
  override affordance, `blocked` explanation with no override affordance).
- `shell/coxswain/highlight.js` — DOM-free directive builder honoring `prefers-reduced-motion`.
- **`overlay/assets/coxswain/viz_highlight.js` (new file, conditionally staged)** — a read-only
  `praxis_coxswain` subscriber that draws the highlight on a **dedicated Konva overlay layer**
  added to the vendored renderer's global `stage`, cleared on every committed-state repaint, never
  writing into the committed-state model. It performs §4.6's `session_id` handshake before
  honoring any highlight message and ignores highlights until the handshake completes.
  **`visualizer-augmentations/index.js` is not touched** — see FR-12 and deviation D-C: that file
  ships in every build, so putting Coxswain code in it would falsify FR-12 and make AC-11 vacuous.
- `web-repl/scripts/vendor_visualizer.py` / the `--with-coxswain` build path — inject a second
  `<script type="module" src="../coxswain/viz_highlight.js">` tag into `visualizer/index.html`
  alongside the existing `_AUGMENTATION_TAG` (`vendor_visualizer.py:141`), only under
  `--with-coxswain`. The 260817 finding about the augmentation file's fragile relative script
  anchor applies identically to the new tag: `coxswain/` must be a sibling of `visualizer/` under
  `overlay/assets/`, and neither directory may be relocated as part of this work.

**Files**: create `coxswain/src/coxswain/clarify.py`, `coxswain/src/coxswain/categorize.py`,
`web-repl/shell/coxswain/{clarify_card,highlight}.js`,
`web-repl/overlay/assets/coxswain/viz_highlight.js`,
`web-repl/shell/coxswain/__tests__/{highlight,clarify_answer,viz_handshake}.test.js`,
`coxswain/tests/test_clarify_matcher.py`, `coxswain/tests/test_categorize.py`.
Modify: `web-repl/scripts/vendor_visualizer.py` and the `--with-coxswain` staging path in
`web-repl/scripts/build_repl.py`. **Do not modify**
`web-repl/overlay/assets/visualizer-augmentations/index.js` — AC-11 asserts a default build's copy
is byte-identical to the tracked file.
**Gate**: `uv run pytest coxswain/tests -q` and `bun test web-repl/shell/coxswain` (via W1.0's CI
job), plus a test asserting the highlight path issues zero writes to the committed-state model,
plus a test asserting a highlight message received before the §4.6 handshake completes draws
nothing. Satisfies AC-12, AC-11's second and third clauses, and FR-7/FR-8/FR-11.
**Depends on**: W1, W2, W3.
**Scope estimate**: ~680 LOC + ~400 LOC tests.

---

### W5 — Audit trail: local store, retention, and best-effort relay (N6, N3 records)

- `audit.py` — the writer: validates `turn_id`, appends `FftDecision` /
  `StalenessFingerprint` / `OverrideRecord`, enforces the closed `disposition` vocabulary, and
  implements FR-9's **ack-before-disposition** contract: it issues the write inside the gate
  pass's own path and awaits `audit.ack` for up to `KERNEL_RTT_TIMEOUT_MS`, returning
  `blocked:audit_unavailable` on timeout or explicit failure. There is no fire-and-forget path
  from the gate to the local store — that shape belongs only to the relay.
- `shell/coxswain/audit_store.js` — the L0 IndexedDB backend for `coxswain_turns` and
  `coxswain_overrides`, implementing §2.3's turn lifecycle, closed-turns-only eviction and
  override exemption, and §2.5's schema-version check at open. **It sends `audit.ack` on the
  transaction's `complete` event, never on a request's `success` event** — an ack is a durability
  claim (FR-9). `QuotaExceededError` and any other abort are reported back as an explicit write
  failure plus a loud system line, never swallowed (AC-17).
- `shell/coxswain/relay.js` — best-effort `transduction_log` relay: only active when a relay
  endpoint was configured at build time, fire-and-forget, queue-and-drop on failure, a visible
  failure counter in a debug line rather than a toast. Zero network calls when unconfigured. It is
  never in the ack path and its latency is never observable in a disposition (AC-19's third
  assertion). See §7 — no receiver service is specified or known to exist, so this half may ship
  permanently inert.
- L1/L2/L3 wiring: `persist()`, the File System Access working folder, and export/import treat
  both stores as one bundle.

**Files**: create `coxswain/src/coxswain/audit.py`,
`web-repl/shell/coxswain/{audit_store,relay,export}.js`,
`web-repl/shell/coxswain/__tests__/{audit_store,relay,quota}.test.js`,
`coxswain/tests/test_audit_writer.py`, `coxswain/tests/test_audit_ordering.py`,
`coxswain/tests/test_correlation_join.py`.
Modify: `web-repl/scripts/build_repl.py` (relay endpoint build flag).
**Gate**: `uv run pytest coxswain/tests -q` and `bun test web-repl/shell/coxswain` (via W1.0's CI
job). Satisfies AC-7 (join half), AC-10, AC-17, AC-19, and AC-21's store-side half.
**Depends on**: W1, W2. Independent of W3/W4 and may run in parallel with them.
**Scope estimate**: ~600 LOC + ~430 LOC tests.

---

### W6 — Graduated pre-execution simulation (CONDITIONAL — do not start)

**Do not pick this item up.** It exists so that the conditional branch is visible in the plan
rather than improvised later. It becomes real only if W0's verdict is `reusable` or
`partially_reusable`, and even then it requires a short scope amendment to this spec naming the
exact reused subset. If W0's verdict is `db_coupled`, W6 is **cancelled**, pre-simulation is out
of scope per N4-C, and a follow-up spec is required before any pre-simulation work begins.

**Gate**: not applicable until W0 resolves. **Depends on**: W0.

#### W6 scope amendment (2026-08-25, post-W0 verdict `partially_reusable` conf 0.9; owner: orchestrator rhino; user go received)

W6 is activated per the condition above. **Exact reused subset** = the `reusable_subset` array of
recon record `260824_w0_simulation_reuse_verdict` in `.praxia/recon.jsonl`, reproduced here as
authoritative:

- whole modules (already ported by W2 into `coxswain/src/coxswain/fft/preconditions/` — no new work):
  `method_contracts`, `bounds_analyzer`, `simulation.state_models`
- from `pipeline.py`: `InferredRequirement`, `HierarchicalSimulationResult`, `StatefulSimulationResult`
- from `failure_detector.py`: `FailureMode`, `FailureDetectionResult`, `BooleanStateConfig`,
  `generate_boolean_states`
- from `simulator.py`: `ProtocolSimulationResult`, `SIMULATION_VERSION`, `is_cache_valid`

Explicitly NOT reused: `HierarchicalSimulator` itself (its constructor requires ProtocolTracing's
closure) and anything reaching `praxis.backend.core.tracing.*`. The two coupling mechanisms W0
identified (tracing imports at pipeline.py:30-35; package-init chains via `core/__init__` → ORM
models and `utils/__init__` → db.py + redis_lock.py) are cut by porting the named symbols into new
stdlib/pydantic-only modules under `coxswain/src/coxswain/sim/` with zero runtime imports of
`praxis.backend.*`; an AST-walking import-boundary test (same pattern as W2's) must enforce this.
Pre-simulation runs at propose time only, feeding existing gate/card surfaces; it introduces no new
kernel-side authority. All W2/W3 ACs continue to hold unchanged.

---

## 7. Out of scope

Named explicitly so a reviewer does not wonder whether they were forgotten. Each was considered
and deliberately excluded.

| Excluded | Why | Where it goes |
|---|---|---|
| **Auto-repair of detected drift** (N3-D) | Rejected outright under H2's friction-over-smoothness tiebreak; nobody has shown a "benign" drift class is provably safe to auto-correct | Future work requiring its own safety review |
| **Full candidate ghosting on the Visualizer** (N8-C) | Requires new hypothetical-state rendering in the vendored PLR visualizer, which only relays real committed state today | Deferred, separable feature; reassess after N8-B ships with real usage data |
| **ReAct-style Think/Act/Observe staging** (N5-A) | A single-pass 270M parse plus a deterministic gate has no multi-step reasoning to disclose; a staged trace would be theater | Rejected, not deferred |
| **Override of cue 0 or cue 2** (N7-B) | Collapses a hard hardware mutual-exclusion hazard and an act-on-the-wrong-object hazard into the same class as a precondition nag | Rejected. Widening requires a source change to `OVERRIDABLE_CUES` and a new spec decision (§3.3) |
| **The parse layer itself** (FunctionGemma load, Transformers.js worker, LoRA adapters) | Architecture-locked but a separate work stream; keeping it out lets W2-W5 be tested against golden fixtures with no 288 MB artifact in CI | A `ParseSource` interface with a fixture stub is specified in W3; the real implementation is a separate spec |
| **Fine-tuning, the ~1,000-example calibration set, execution-verification against `ChatterBoxBackend`** | Off-device training work, off this spec's critical path | Separate spec |
| **Voice input (Web Speech API, push-to-talk)** | Text-first MVP. Every affordance here is keyboard-reachable and dictation-compatible, so voice layers on without redesign; note that the irreversible-tier phrase must be entered into its field, never triggered by ambient audio | Separate spec |
| **The `learn()` write-back for location aliases and the derive-from-usage carrier-compatibility corpus** | Grounding-contract architecture is locked, but MVP needs only the `resolve()` read path for cue 2. **Consequence, stated plainly:** the scoping doc frames cold-start chattiness as transient — clarification-heavy "before the system is fluent". Without `learn()` there is no write-back, so for **alias-only** references ("lane C", "the usual source plate", a nickname the deck graph does not contain) cold start is the *permanent* MVP state, not a phase: the same reference will require the same clarification on every turn, forever. This is a real UX cost and is accepted knowingly. It does **not** affect deck-graph-resolvable references — `A1`, `rails 7`, resource IDs, and anything else cue 2 can resolve against live kernel objects ground on the first pass and are unaffected. Those are the demo path and the expected majority of real usage | Separate spec |
| **Production Mode (`WorkcellRuntime`) backend of Layer 2b** | MVP targets Browser Mode only; the adapter seam is specified in W2 so the second backend is additive | Later, if Coxswain ever runs server-side |
| **In-browser LoRA hot-swapping** | Unverified in Transformers.js/WebGPU; needs its own spike | Spike, per the scoping doc |
| **The relay's receiving service** (an HTTP endpoint that accepts a relayed `FftDecision` and forwards it to `transduction_log`) | FR-9's relay is gated on "a relay endpoint configured at build time", which presumes an **HTTP receiver**. It is not direct access to the `transduction_log` MCP tool: that is an MCP/stdio surface with no browser-reachable wire protocol, and a static offline-first page cannot call it. **No such receiver is specified here and none is known to exist in this repo**, so N6's relay half may ship permanently inert — every build to date would configure no endpoint, take the zero-network path, and satisfy AC-10 vacuously. That is an acceptable MVP outcome (the coxswain-local store is the source of truth by design, per N6), but it must not be mistaken for "the relay works and is simply unconfigured" | Separate spec, if org-side aggregation is ever actually wanted. Whoever writes it owns the auth, transport, and privacy review that RISK-10 gestures at |
| **The execution-failure card's retry affordance** | The renderer itself is in W3 (see C5). A one-click retry is not: re-running a call means re-running the whole gate against fresh state, which is exactly what typing the command again already does, and a retry button invites treating a failed hardware operation as idempotent | Revisit only with usage data |
| **Confirmation-friction tiers beyond the three static ones** | Three tiers cover the reversibility spectrum the product actually has today | Revisit only with usage data |

---

## 8. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| RISK-1 | **N4 reuse verdict is genuinely unknown.** `praxis/backend/core/simulation/*` may be DB-coupled exactly as `state_resolution.py` was, invalidating the reuse assumption | Medium | Medium — cue-3 implementation cost, not correctness | W0 is a blocking task with its own task_id and an explicit `verdict` deliverable (§3.2). W6 is pre-cancelled on a `db_coupled` verdict. **This spec deliberately does not predict the outcome** — doing so is the guessing H3 exists to prevent |
| RISK-2 | **Failure 1 — the visible re-check state ships without the block.** A dev implements debounce-on-blur and the CSS class, nothing fails CI, a fast clicker confirms a stale card | High if unmitigated | High — wrong physical operation on real hardware | Three independent block layers (§3.1), the authoritative one in Python; AC-4 explicitly rejects a CSS/aria-only test as satisfying it; **and W1.0 wires the CI job that makes "nothing failed CI" stop being literally true** (RISK-15) |
| RISK-15 | **The acceptance criteria are never run.** Verified at spec time: root `testpaths = ["tests"]` excludes `coxswain/tests`, `repl.yml` enumerates its test files by name and omits `coxswain/**` from its path triggers, and no workflow invokes `bun`. Every AC in §5 would be a command that only ever runs on a developer's laptop | **Certain** if unmitigated — this was the state of the repo when the spec was written | High — it is the direct root cause of pre-mortem Failure 1 and silently degrades every other mitigation in this table to a convention | W1.0 lands first and is a prerequisite of the whole spec (§5 preamble); AC-18 requires the job to have been **observed failing**, not merely to exist, matching the standard `repl.yml`'s own header sets for its existing steps |
| RISK-3 | **Failure 2 — the recon check never runs; N4-A silently becomes N4-B.** Two divergent simulation implementations exist 18 months later | High if unmitigated | Medium — long-term maintenance ambiguity | W0 is a standalone blocking task (§3.2); AC-5 requires its record to exist before W2's cue-3 item or W6 starts; inline "minimal version for now" reimplementation is prohibited by name |
| RISK-4 | **Failure 3 — override scope quietly widens** to cue 2 under social pressure and is never re-reviewed | Medium | Very high — acting on the wrong physical object | `OVERRIDABLE_CUES` is a compile-time `Final[frozenset]` (§3.3); eligibility is computed only in the gate and shipped as a payload boolean; cue 0/1/2 payload types structurally lack override fields; AC-6 greps for config-sourced reads |
| RISK-5 | **Failure 4 — the two audit trails cannot be joined** after an incident; different retention windows force manual stitching | Medium | High — incident review under time pressure | §2's normative `turn_id`/`gate_seq` contract; one atomic `CoxswainTurnRecord` aggregate with per-turn eviction; override records exempt from eviction but retaining `turn_id`; AC-7 tests the join and the eviction asymmetry |
| RISK-6 | **No JS test harness exists.** `web-repl/` has no `package.json`, and `node`/`npm` are absent from this machine (bun only) — UI acceptance criteria could become untestable | High | Medium — safety criteria degrade to manual review | NFR-3 forces all safety-load-bearing JS into DOM-free pure modules testable by `bun test` with zero dependencies; the authoritative Confirm block is Python and gated by pytest |
| RISK-7 | **Cue 0's concurrency source is undefined in web-repl.** The scoping doc's `AppStore.hasActiveRun` is unreachable from web-repl either way (a challenge grep found it only in an Angular architecture doc, in no `.ts` source — which changes nothing about web-repl's inability to read it) | High | High — cue 0 is the cheapest and most decisive cue; a wrong answer makes every other cue moot. The specific failure is not "unreachable" — NFR-5 handles that — but a probe that cheerfully returns "not active" because it reads nothing | §4.5 names the interface **and its two in-process signal sources** (`ExecutionFlag`, `DispatchWatch`), gives them their own files in W2's file list, and states the residual gap (a call bypassing both wrappers). AC-16 asserts the probe's result **flips when its sources flip**, so a constant-`False` implementation fails the suite. Unknown → `blocked:concurrent` (NFR-5) |
| RISK-8 | **Fixture-stubbed parse drifts from real model output.** W2-W5 pass against golden fixtures, then break on first contact with FunctionGemma | Medium | Medium | Fixtures are generated from the tool schema, not hand-written; the `ParseSource` interface is the only seam; the parse spec must add a contract test against the same fixtures |
| RISK-9 | **Audit log growth exhausts the IndexedDB quota**, silently dropping writes | Medium | Medium — audit gaps | Bounded FIFO retention with a configurable turn cap over closed turns only (§2.3); a quota-exceeded event surfaces as a loud system line, never a silent drop, and the issuing gate pass exits `blocked:audit_unavailable` rather than executing on an unrecorded decision (FR-9). **AC-17 tests this** rather than leaving the mitigation as prose |
| RISK-10 | **The relay leaks lab data off-device.** A static, offline-first product that starts making network calls to an org log service is a privacy regression | Low | High — trust, possibly compliance | The relay is inert unless a relay endpoint is configured at build time; AC-10 asserts zero network requests when unconfigured |
| RISK-11 | **Vendored-visualizer drift.** W4 adds a Coxswain module to the visualizer document; a future re-vendor of PLR's renderer could clobber or desync it | Medium | Low-Medium | W4 leaves `visualizer-augmentations/index.js` **untouched** (deviation D-C) and ships `overlay/assets/coxswain/viz_highlight.js` as a sibling, loaded by a second injected `<script>` tag under `--with-coxswain` only. Both files are manifest/sha-tracked; the highlight uses a separate Konva overlay layer so it never touches vendored draw code, and `VENDOR_MANIFEST.json` remains the drift detector. AC-11's byte-identity clause additionally catches a regression that puts Coxswain code back into the always-shipped augmentation file |
| RISK-12 | **`turn_id` collision** across tabs sharing an origin and a BroadcastChannel | Low | Medium — cross-talk between sessions | `turn_id` embeds an epoch-ms plus 6 base36 random chars, and every envelope also carries `session_id`; receivers drop messages whose `session_id` is not their own. **The visualizer document is a receiver with no `session_id` of its own** — it never runs `coxswain-shell.js` — so §4.6 specifies the handshake that gives it one and makes it ignore every highlight until the handshake completes |
| RISK-13 | **N2-A proves too costly to ship first-cut** (the visible-revalidation state plus three-layer block) | Low-Medium | Low — scope, not safety | N2-B (scalar-only editing, symbolic references not inline-editable) is the pre-approved documented fallback. Falling back requires recording the decision here; it does **not** license dropping §3.1's block, which applies to scalar edits too |
| RISK-14 | **`--with-coxswain` regresses the default build.** Injection is a shared code path with `praxis-shell.js` | Low | Medium — breaks the shipping product | AC-11 gates a default build against the existing `assert_dist_complete` and inject-shell checks; manifests must differ only in coxswain entries |

---

## 9. References

- `.praxia/docs/research/260824_gemma-finetuned-plr-voice-text-copilot-scoping.md` — locked architecture F1-F10
- `.praxia/docs/specs/260824_coxswain-ux-open-design-axes-task-id-260.md` — brainstorm session `48789b43`, Idea Pool / Decision Log / Pre-mortem Record for N1-N8
- `.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md` — §2.3 manifest/sha integrity (D1-D3), §5.2 import boundary, §5.4 pytest addopts isolation
- `.praxia/docs/research/260817_standalone-web-repl-extraction-shell-and-brainstorm.md` — "B′ INJECT" winner, the injection pattern W3 extends
- `.praxia/docs/specs/260817_spec-visualizer-transport-shim.md` — the visualizer transport shim W4 builds on
- `coxswain/README.md`, `coxswain/pyproject.toml` — existing scaffold and its stated boundary
- `web-repl/scripts/build_repl.py` — `stage_shell` (:812), `run_inject_shell` (:832), `assert_dist_complete` (:852)
- `web-repl/overlay/assets/python/praxis/viz/transport.py` — `VIZ_CHANNEL` and the channel-separation principle NFR-4 extends
- Recon record `260824_coxswain_recon1` (task `260824_coxswain_spec_design`) — `HierarchicalSimulator` / `FailureModeDetector` locations, PLR integer-only rail addressing
- Audit records `260824_coxswain_spec_challenge` and `260824_coxswain_spec_defense` in `.praxia/audits.jsonl` — the adversarial review cycle this revision closes; the "why" behind every entry in the Revision Log, including the reasoning for the eleven objections deliberately **not** actioned
- `.github/workflows/repl.yml` — the existing browser-gate workflow W1.0 extends (`paths:` triggers at :17-31, duplicated deliberately; the Tests step at :199 enumerating test files by name)
- `web-repl/scripts/vendor_visualizer.py` — `_AUGMENTATION_TAG` (:141) and the sibling-directory constraint the new `coxswain/viz_highlight.js` tag inherits
