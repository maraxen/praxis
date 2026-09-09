---
title: 'Coxswain P2.5 provisional promotion thresholds (T_acc / T_clr_recall / T_clr_prec)'
description: 'Numeric anchor proposal for the P2.6 three-number promotion gate (D8), derived from the P2.1 recorded-artifact baseline spread and the assembled P2.5 eval slice sizes. PROVISIONAL PER D8: exactly ONE revision permitted at P2.6 fine-tune eval, with recorded justification.'
task_id: 260825_copilot_pipeline_spec
date: '260825'
status: provisional-per-D8
backlog_item: 480
---

# Provisional thresholds for the P2.6 promotion gate

> **Status 260901 (P2.6 applied):** the rule was applied mechanically to the
> three-arm ablation -- verdict NOT PROMOTED (selected A: acc 0.386, recall
> 0.864, prec 0.835, tripwire 1). **The single D8 revision is UNSPENT by
> user decision (260901)**; anchors unchanged until two scorer artifacts and
> one gold-set defect are fixed and the checkpoints are re-scored. Decision doc:
> `.praxia/docs/audits/260901_p26-promotion.md`.
>
> **Status 260902 (re-scored, task `260902_p26_rescore`):** scorer + gold-sidecar
> defects fixed under the pre-registration amendment
> `260902_p26-rescore-amendment.md`; the same checkpoints re-scored from frozen
> generations, prediction held. A: acc **0.636** [0.572, 0.696], recall 0.864,
> prec 0.835, tripwire 1 -> still NOT PROMOTED; baseline v2 0.197. **Anchors
> unchanged, D8 revision still UNSPENT.** Decision doc §8.
>
> **Status 260902 (P2.6b, task `260902_p26b_surface_data`):** floor_gen data fix
> (repaired rows + natural-phrasing lane), arm A retrained once on the pinned
> split: A2 acc **0.671** [0.608, 0.729], recall 0.920, prec 0.853, tripwire 3 ->
> NOT PROMOTED; pre-registered P1/P2/P4 held, P3 failed (tripwire, flips).
> **Anchors unchanged, D8 revision still UNSPENT.** Decision doc
> `.praxia/docs/audits/260902_p26b-floor-surface-decision.md`.

> **Status 260903 (P2.6c, task `260903_p26c_oos_natural`):** natural lane extended to the
> out-of-surface floor rows; arm A3 on assembly 0.1.5 = 0.671 [0.608, 0.729] / recall 0.898 /
> precision 0.878 / tripwire 3 on the pinned 228 -- NOT PROMOTED, anchors and D8 revision
> UNCHANGED/UNSPENT. The tripwire rows are near-surface topical confusions, not a phrasing
> cue; next lever is a near-surface out-of-surface matrix cell (new prereg). Decision doc
> `.praxia/docs/audits/260903_p26c-oos-natural-decision.md`.
>
> **Status 260903 (P2.6d, task `260903_p26d_near_surface`):** six near-surface out-of-surface
> matrix cells (v3); arm A4 on assembly 0.1.6 = 0.671 [0.608, 0.729] / recall 0.966 /
> precision 0.867 / tripwire 1 on the pinned 228 -- NOT PROMOTED (A3 selected on the precision
> tie-break), anchors and D8 revision UNCHANGED/UNSPENT. The shape diagnosis is confirmed
> (two of three tripwire rows recovered, near-surface probe 0.50 -> 0.96); exact match stays
> pinned at 153/228 by cross-cell label conflicts. Decision doc
> `.praxia/docs/audits/260903_p26d-near-surface-decision.md`.

Spec: `.praxia/docs/specs/260825_coxswain-phase-2-functiongemma-copilot-p.md`
rev2 D8 / §5 P2.5 deliverable 5 / §7 AC-2.5.x ("thresholds labeled
provisional"). These are ANCHORS for the blocking jury, not final gates:
**P2.6 may revise each number at most once, with recorded justification**
(D8 rev2). All reported values at P2.6 must carry Wilson 95% intervals beside
point estimates (AC-2.6.x).

## 1. Proposed anchors

| Metric | Provisional anchor | Baseline point (P2.1 recorded-artifact proof) | Baseline Wilson 95% |
|---|---|---|---|
| `T_acc` (exact-match accuracy) | **>= 0.80** | 0.75 (6/8) | [0.409, 0.929] |
| `T_clr_recall` | **>= 0.70** | 0.50 (2/4) | [0.150, 0.850] |
| `T_clr_prec`   | **>= 0.90** | 1.00 (2/2) | [0.342, 1.000] |

## 2. Where each number comes from

Baseline evidence is `training/eval/reports/260825_recorded_fixture_report.json`
-- RECORDED ARTIFACTS, NOT live inference, PARTIAL coverage (8 scored of 62
in-scope; real model lane blocked on Gemma license acceptance + `HF_TOKEN`,
see training README). With n that small the intervals are wide, so anchors are
set by POLICY margins over the baseline points, not by interval arithmetic:

- **T_acc = 0.80**: baseline point 0.75 already sits near it; a 270M model
  fine-tuned on this surface must CLEAR the off-the-shelf point estimate,
  not tie it. 0.80 is the smallest round anchor strictly above 0.75 that a
  correct-ish model cannot miss by transcription noise alone.
- **T_clr_recall = 0.70**: baseline 0.50 misses half of clarify-expected
  items. Cue-1 (out-of-surface abstention + derived missing-slot surfacing)
  is the safety behavior F1 protects; the gate must force real movement
  above coin-flip. 0.70 leaves headroom below Mobile-Actions-style targets
  while being falsifiable on the current slice.
- **T_clr_prec = 0.90**: baseline 1.00 (n=2). Over-triggering clarification
  destroys usable parses (every false positive is a blocked action); the
  asymmetric cost justifies anchoring precision higher than recall.

## 3. Slice sizes these anchors will be measured on (assembled P2.5 eval)

From `training/assemble/out/manifest.json` (assembly_version 0.1.0):

| Eval slice | n |
|---|---|
| clean_parse | 66 |
| out_of_surface | 12 |
| missing_slot | 12 |
| ambiguous_referent | 12 |
| total eval clarify (3 classes) | 36 (>= D8's 30 floor) |

Recorded scope caveat (P2.1 decision, unchanged): the STATIC harness scores
clarify over out-of-surface + missing-slot ONLY (24 items); ambiguous-referent
detection needs live kernel grounding (cue 2, F1-rev2/C-M1) and verifies at
P2.9 integration. The three-class >=30 sizing is satisfied by the corpus;
the statically-scoreable subset is 24 -- flagged in the slice-gate doc.

## 4. Revision rule (D8)

At most ONE revision of any anchor at P2.6, requiring: observed eval slice
sizes, Wilson intervals beside every point estimate, and a written reason.
Suggested legitimate reasons: full-scale corpus regeneration materially grew
a slice; live-model baseline (post-token) lands far outside the recorded
mechanics-proof spread. Vague "model feels better" is not a reason.

## 5. D2 unblocked (260827): real baseline landed

HF_TOKEN exported (gated-repo terms already accepted on the account); real
local CPU inference now runs. First attempt produced a degenerate, INVALID
result (`exact_match_accuracy` 0.194, uniform "sequence length 0" failures
across every non-abstention class) traced to a harness bug, not model
capability: `_prompt_of()` concatenated raw developer+user text and never
called `tokenizer.apply_chat_template(..., tools=...)`, so the model never
saw the 13 tool declarations. Verified directly: the same prompt built
properly (`apply_chat_template` with `tools=`) makes the untuned base model
correctly emit `call:aspirate{source: reagent_reservoir_1,volume_ul:50}`
zero-shot for a clean_parse utterance. Fixed in
`training/src/praxis_training/baseline_eval/{runner,local_infer}.py`
(`GenerateFn` now takes the native row so the local-inference lane can
build the real chat-templated prompt with tools; 12/12 existing tests
still pass with a corresponding test-fake update).

**Real baseline** (`training/eval/reports/260827_baseline_real.json`,
`google/functiongemma-270m-it@39eccb091651513a5dfb56892d3714c1b5b8276c`,
n=62 live local inference, greedy decode, CPU):

| Metric | Real baseline | Wilson 95% | vs. provisional anchor |
|---|---|---|---|
| `T_acc` | 0.210 (13/62) | [0.127, 0.326] | far below 0.80 |
| `T_clr_recall` | 0.833 (20/24) | [0.642, 0.933] | already clears 0.70 |
| `T_clr_prec` | 0.556 (20/36) | [0.396, 0.705] | below 0.90 |

This is NOT a threshold revision (that stays a P2.6-only, one-shot action
per §4) — the anchors above are unchanged. It replaces the mechanics-proof
baseline point as the reference measurement per the P2.5 slice gate's §5
GO condition 2. Per-class detail (clean_parse 0/26 exact match — mostly
natural-language-reference-vs-canonical-ID slot mismatches, e.g. "tube rack
position B3" vs `tube_rack_B3`, a grounding concern D11/D12 already assign
to deterministic post-parse resolution, not the model; out_of_surface
12/12; missing_slot 0/12 exact match but 8/12 correctly flagged for
clarification; ambiguous_referent 1/12, not cleanly scoreable per §3's
caveat) lives in the report JSON.
