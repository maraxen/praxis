---
title: 'D13 gate: Gemma license & deployment-audience analysis for the FunctionGemma copilot'
description: 'Terms-of-use and prohibited-use-policy read-through (P2.0, backlog 4475); redistribution constraints for serving a functiongemma-270m-it fine-tune from a GitHub Pages origin; audience options + recommendation pending orchestrator/user sign-off.'
status: recommendation-pending-signoff
task_id: 260825_copilot_pipeline_spec
date: '260825'
---

# Gemma license & deployment-audience gate (D13)

Sources read 2026-08-25:

- Gemma Terms of Use, <https://ai.google.dev/gemma/terms> (last modified 2026-04-01)
- Gemma Prohibited Use Policy, <https://ai.google.dev/gemma/prohibited_use_policy> (last modified 2024-02-21)

`google/functiongemma-270m-it` is listed in the Terms' Appendix (as
"FunctionGemma", both ai.google.dev and Kaggle entries), so the Gemma Terms of
Use ("GTOU") govern it. **Note:** Google has released Gemma 4 under an Apache-2
license (<https://ai.google.dev/gemma/apache_2>); that license does NOT cover
functiongemma-270m-it, which remains on the GTOU Appendix. Do not conflate the
two.

## 1. Why this binds us

Our plan (spec rev2, D5) is a FULL-parameter SFT of `functiongemma-270m-it`.
That makes the resulting checkpoint a **Model Derivative** by the plain text of
GTOU §1.1(e)(i)-(ii) (a modification of / work based on Gemma).

Two adjacent cases deliberately checked:

- **Teacher-generated NL data**: GTOU §1.1(e)(iii) also sweeps in models
  trained on *synthetic outputs* of Gemma (distillation). Our sanctioned
  teachers are ox-alpha workers and titanix-vllm-primary (F6) -- neither is a
  Gemma family model -- so the training CORPUS does not create a derivative
  pathway. Keep it that way: do not substitute a Gemma-family teacher without
  re-running this gate.
- **Model Outputs**: GTOU §1.1(e)/§3.3 -- outputs of the model are NOT Model
  Derivatives and Google claims no rights in them. Parsed tool calls produced
  by our copilot are ours to use.

## 2. Is serving from GitHub Pages a "Distribution"?

Yes, unambiguously. GTOU §1.1(b) defines Distribution as "any transmission,
publication, or other sharing of Gemma or Model Derivatives **to a third
party**", expressly including hosting. Two distinct flows matter:

| Flow | Third party? | Consequence |
|---|---|---|
| Model runs in-browser after the visitor's browser downloads the ONNX from our Pages origin | Yes -- the visitor receives the derivative BYTES | Full §3.1 redistribution conditions apply |
| Model executes server-side; user sees only parsed calls (outputs) | No bytes transferred | Output-only; §3.3, no redistribution conditions |

Our architecture (F3/D12: Transformers.js worker, lazy fetch from site origin,
no CDN per G5) is the FIRST row: we ship weight bytes to every visitor of the
Pages origin. Whoever can reach that URL is a redistributee, whether or not they
click anything. An unauthenticated Pages deploy is therefore PUBLIC
REDISTRIBUTION of a Model Derivative.

## 3. Redistribution constraints (GTOU §3.1) for any byte-serving deploy

All four are mandatory whenever the derivative is served to any third party:

1. **Flow-down restrictions**: the §3.2 use restrictions (Prohibited Use Policy
   + applicable-law clause) must appear as an ENFORCEABLE provision in an
   agreement governing use of the served model (site terms of use), with notice
   to recipients.
2. **Agreement copy**: provide every recipient a copy of the GTOU (a vendored
   `LICENSE-GEMMA.txt` beside the model files + a visible link satisfies this;
   a bare external link alone is weaker than shipping the text).
3. **Modification notices**: modified files carry prominent notices that they
   were modified. Practical mapping for us: a MODEL_CARD / provenance entry in
   the `models` manifest array stating "fine-tuned from
   google/functiongemma-270m-it (Gemma Terms of Use); modified by <project>".
   F3 already requires source_sha/sha256/bytes provenance -- add a license
   field there.
4. **Notice file**: Distributions other than through a Hosted Service must be
   accompanied by a NOTICE text file containing verbatim: *"Gemma is provided
   under and subject to the Gemma Terms of Use found at
   ai.google.dev/gemma/terms"*. Because we ship raw weight FILES (not just
   hosted functionality), assume this applies: ship `NOTICE.txt` next to the
   model artifacts regardless.

Additional standing obligations regardless of audience:

- **Termination tail** (§4.5): on breach, Google may terminate and copies must
  be deleted. A breach by ONE redeployed copy taints the deployment; keep the
  compliance artifacts auditable.
- **Remote restriction right** (§3.2): Google reserves the right to restrict
  usage it believes violates the terms. Another reason not to bake the model
  into anything hard to retract (it is lazy-fetched and gitignored -- good).
- **Prohibited Use Policy**: standard content/harm restrictions. Our domain --
  a single-turn lab-automation parser emitting structured tool calls -- triggers
  none of it. Two edges worth recording: (a) do not market/shape the copilot as
  making automated decisions affecting material individual rights (PUP
  "automated decisions" bullet); (b) it assists, and the FFT confirmation gates
  keep a human approving every mutating call -- consistent with the PUP's
  unlicensed-profession concerns. No prohibited-use exposure identified for
  phase 2 scope.

## 4. Deployment-audience options

| Option | Who receives bytes | §3.1 kit needed? | Notes |
|---|---|---|---|
| **A. Private / internal** (localhost dev, loopback demos, intranet or auth-gated Pages restricted to project members under NDA/entity control) | No third parties (same legal entity / authorized collaborators) | Not strictly; recommended anyway as hygiene | Zero redistribution exposure. NOTE: a public GitHub repo does NOT itself distribute the model (weights are gitignored per F3); exposure happens only when a reachable Pages deploy serves them |
| **B. Gated fetch** (public-ish site but model bytes require authenticated, ToS-accepting accounts) | Only users who accepted site terms embedding §3.2 + received the GTOU copy | YES -- all four, enforced at the gate | Compliance is checkable per-user; weakest point is account sharing; engineering cost: an auth boundary the repl stack does not have today |
| **C. Public anonymous serving** (current Pages default: anyone can fetch `/vendor/models/*.onnx`) | Everyone on the internet | YES -- all four, plus the practical inability to enforce anything beyond posted terms | Simplest UX; turns the demo into unconditional public redistribution; direct-download URL means we cannot even argue "hosted service" treatment |

## 5. Recommendation (FOR SIGN-OFF -- not decided here)

**Recommended staged posture:**

1. **Through P2.7/P2.8 development and all evaluation work: Option A
   (private/internal).** Nothing in the DAG requires public exposure before
   integration lands; dev servers and CI are loopback. This is also the safest
   reading of D13's intent (decide BEFORE teacher spend -- spend happens under A
   either way).
2. **At the P2.8/P2.9 delivery boundary, choose between B and C**, with this
   guidance:
   - If the goal is an internal/demo artifact for stakeholders: stay A/B.
   - If a public demo is wanted: Option C is permissible ONLY AFTER the four-item
     §3.1 compliance kit ships (site-terms snippet embedding the §3.2
     restrictions, vendored GTOU copy + link, manifest `license` +
     modification-notice fields, `NOTICE.txt` beside artifacts). Estimated cost
     is small (static files + one manifest field), but it is a HARD precondition,
     not a follow-up.
3. **Record as constraint now**: no public anonymous serving of any
   functiongemma-270m-it derivative from any project origin until the audience
   decision is signed off and, if C, the §3.1 kit is verified in the built dist.

**Decision requested from orchestrator/user:** pick A, B, or C for the phase-2
deployment audience (with C conditioned on the compliance kit). This document
does not decide it.

## 6. Verification pointers

- Re-fetch both URLs and diff against this document if >90 days elapse before
  the audience decision (Google updates these pages; GTOU last touched
  2026-04-01, PUP 2024-02-21).
- When P2.7a lands the `models` manifest array, add a `license: "gemma"` field
  + CI assertion that `NOTICE.txt` exists beside every gemma-licensed artifact
  (cheap prevention against later silent drops).
