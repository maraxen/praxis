---
title: 'P2.6b pre-registration: floor_gen surface-form data fix, arm-A retrain on the frozen eval split'
description: 'Pre-registration (task 260902_p26b_surface_data) for the floor_gen data fix: repair the 60 cardinality-excluded floor rows without moving any accepted row (synth 0.2.1, frozen seed), add a natural-phrasing lane (locations and verbs) routed to train only, assemble 0.1.4 with the pinned 228-row eval split and a probe set, retrain the arm-A recipe once and score it against baseline v2 and the existing A checkpoint under the unchanged promotion rule; row-level predictions registered before generation.'
status: registered-cc662026; run-21842239 evaluated
task_id: 260902_p26b_surface_data
date: '260902'
---
# P2.6b pre-registration: floor_gen surface-form data fix, arm-A retrain on the frozen eval split


Registered BEFORE any generator change, generation, or training (commit order is the
proof; the freeze artefacts are commit `b86a9127`). Backlog 4890 (depends on 4861).
Sidecar `scripts/experiments/p26b_finetune.bth.toml`. Decision it follows: promotion doc
`.praxia/docs/audits/260901_p26-promotion.md` §6 item 2, chosen by the user 2026-09-02
over the recipe sweep. User decisions 260902: golden eval rows stay AS-IS; ONE
natural-phrasing lane covering locations AND verbs; retrain the arm-A recipe only.

## 1. What is fixed (frozen), what changes

| Item | Status |
|---|---|
| Eval split | **FROZEN.** The 228 rows of assembly 0.1.3, pinned by record_id AND native-row content in `training/assemble/data/eval_split_pin.json` (rows sha256 `8e023a33c2320c42a9be3cd0fc98110f3b7fae690871fff58bc9db51e22687d4`). The assembler asserts the pin; any drift is a deviation. |
| Comparators | baseline v2 re-score `training/eval/reports/260902_p26_rescore_baseline.json` (45/228 = 0.197) and arm A re-score `260902_p26_rescore_A.json` (145/228 = 0.636 [0.572, 0.696], recall 0.864, prec 0.835, tripwire 1). Both use the fixed scorer (amendment 8fe1b111). |
| Control checkpoint | the existing arm A (`outputs/p26/A/checkpoint`, sha256 `376cac6e…`), trained on `corpus_p25.jsonl` sha `3ce238b8…` -- identical native rows to today's file (assembly 0.1.3 changed only the sidecar). |
| Recipe | `RECIPE_VERSION 0.1.0` UNCHANGED (TRL SFT full-param, lr 1e-5 cosine, warmup 0.1, bf16, bs 4 x accum 4, 8 epochs, completion-only loss). Arm A = raw mix (every negative kept), seed 0. Optimizer steps will rise with the larger train set (~470-480 vs 264); recorded as a confound, not tuned. |
| Base model | `google/functiongemma-270m-it@39eccb09…` UNCHANGED. |
| Scorer | UNCHANGED since the 260902 amendment. |
| Promotion rule / D8 anchors | UNCHANGED (prereg 260901 §3); revision UNSPENT. |
| Floor corpus | CHANGES ONLY on the 60 rows assembly 0.1.3 excluded: synth 0.2.1 coerces to the declared surface (`DECLARED_ARRAY_PARAMS`) after synthesis, consuming no RNG; `SYNTH_SEED_VERSION` stays 0.2.0. The 625 accepted rows are pinned byte-identical (modulo `provenance.generator_version`) in `training/floor_gen/data/floor_0.2.0_accepted_digests.json`. Base prompt text untouched (cache-preserving). |
| New data | natural-phrasing lane (`coverage_natural`): the SAME structured calls as in-surface floor rows, teacher asked for natural location phrasing and everyday verbs, deterministic identifier filter; variants of TRAIN-base rows join train, variants of EVAL-base rows form a separate PROBE set, never the 228. |
| Assembly | 0.1.4: pinned eval, repaired rows train-only, natural rows per base split, probe files, manifest records the pin sha and the strata that have no hold-out by construction. |
| Teacher | Gemini 3.7 Flash medium via `agy` (same as the 0.2.0 floor). |

## 2. Hypothesis

Training data that phrases locations naturally ("well D1 of plate 1") and names actions
with everyday verbs, paired with the same canonical `{name, params}` labels, teaches the
model the surface-to-canonical mapping it currently lacks (96% of floor training utterances
contain the canonical token verbatim; golden eval rows 13%; the coverage eval rows whose
gold reference is not verbatim in the utterance fail 9/9 today). Repairing the 60 excluded
rows additionally restores the `pick_up_tips__ambiguous-referent` cell and the multi-value
aspirate/dispense/transfer rows to train.

## 3. Pre-registered predictions (frozen 228 split, fixed scorer, A2 vs A)

**P1 -- location surface (primary).** The 6 coverage eval rows whose gold reference is a
dotted id absent from the utterance, all misses on A today:
`cov-0092-dispense__missing-slot-12`, `cov-0093-dispense__missing-slot-13`,
`cov-0094-dispense__missing-slot-14`, `cov-0172-transfer__ambiguous-referent-12`,
`cov-0173-transfer__ambiguous-referent-13`, `cov-0174-transfer__ambiguous-referent-14`.
**Prediction: A2 exact-matches >= 4 of 6.**

**P1b -- exploratory, no prediction.** `cov-0367`, `cov-0369` (gold `"the tip rack"` vs
utterance "the box" / "the rack") and `cov-0609` (gold `"the lid"` vs "the plate lid"): the
exact-match scorer demands the pool's literal vague string. Expected 0-1/3; the finding to
record is that these need a scorer/gold decision on vague-string equality, not data.
`cov-0158`, `cov-0547/0548/0549` (hallucinated extra argument on missing-slot rows): the
natural lane keeps the omission instruction; no prediction, reported.

**P2 -- verb paraphrase.** The 22 rows A fails in category `name_mismatch` / `no_call` /
`unknown_verb` (`failure_breakdown.classify_reasons`): `cov-0467-move_resource__none-12`,
`cov-0482/0483/0484-move_plate__missing-slot-12/13/14`, `cov-0498-move_resource__ambiguous-referent-13`,
`golden-clean-aspirate-03`, `golden-clean-discard_tips-02`, `golden-clean-discard_tips-04`,
`golden-clean-dispense-02`, `golden-clean-dispense-04`, `golden-clean-move_lid-03`,
`golden-clean-move_plate-02`, `golden-clean-move_plate-03`, `golden-clean-move_resource-02`,
`golden-clean-move_resource-03`, `golden-clean-read_fluorescence-02`, `golden-clean-stamp-02`,
`golden-clean-stamp-03`, `golden-clean-transfer-02`, `golden-clean-transfer-04`,
`golden-missing-slot-02`, `ovl-f33ef17438`. **Prediction: >= 11 of 22 no longer classify
in {name_mismatch, no_call, unknown_verb} on A2** (the verb is recovered even if params still
fail). Sub-prediction: `golden-clean-discard_tips-02/-04` (no reference args) exact >= 1/2.
The 4 `move_plate`/`move_resource` rows with an elided object are cross-cell label conflicts
("Move to reservoir_1" appears in both cells) and are expected NOT to migrate.

**P3 -- must-not-regress.** A2 exact-match >= 145/228 (0.636); clarify recall >= 0.705;
tripwire <= 1; rows flipping hit -> miss <= 5 (single unpaired seed; every flip listed by
record_id and pattern). Out-of-surface behaviour unchanged (no natural variants for that class).

**P4 -- probe set (secondary, non-gating).** Natural variants of eval-base rows
(`training/assemble/out/corpus_p25_probe.jsonl`, n expected 70-90): A2 exact-match exceeds
A's by >= 0.10 absolute, both scored the same way (cuda/bf16, same job).

**P5 -- golden surface rows (exploratory).** The 44 golden `param_content` rows are reported
separately. Golden ids follow an underscore convention (`source_plate_A1`, `tube_rack_B3`)
while the floor grammar is dotted (`plate_1.D1`); no recovery is predicted. **Jury item:**
whether golden references should be re-annotated to the groundable dotted grammar in a later
eval revision.

**Ceiling and verdict.** Recovering every non-golden miss gives 167/228 = 0.732 < T_acc 0.80.
**Expected: NOT PROMOTED** under the unchanged rule; `promotion.py` decides mechanically
with A and A2 side by side against baseline v2.

**Confounds recorded:** ~1.8x optimizer steps at the fixed recipe; one seed, unpaired
shuffles (A vs A2 differ in data AND in shuffle); same teacher model.

## 4. Deviations

Any of: a pinned eval row missing or content-changed; any of the 625 accepted floor rows
changed; a base-prompt text edit; a recipe change; more than one training run per arm;
A2 scored on anything but the pinned split with the fixed scorer. A prediction failing is
NOT a deviation -- it is the result, reported as such. Natural-lane acceptance below 70% on
the first batch allows tightening the natural prompt (its own version) BEFORE the full run,
because no scored artefact depends on it.

## 5. Storage

Floor 0.2.1 corpus + manifest + ~60 cache files; natural corpus + manifest + cache;
assembly 0.1.4 outputs incl. probe files; train manifest `training/out/p26b/A/train_manifest.json`;
reports `training/eval/reports/260902_p26b_A.json`, `260902_p26b_probe_{A,A2}.json` with
generation dumps under `training/eval/outputs/`; checkpoint uncommitted at
`outputs/p26b/A/checkpoint` (sha256 in the manifest). bathos run tagged `arm:A2`.

## 6. Outcome (260902, mechanical)

P1 **4/6** (holds), P2 **11/22** (holds), P2b 0/2, P3 **fails** (tripwire 3 > 1; 8 hit → miss > 5;
accuracy 0.671 and recall 0.920 fine), P4 probe A 0.233 → A2 0.844 (holds). Sidecar `fail`
(residual). Promotion: NOT PROMOTED (selected A2). Deviations: none (all frozen items held; one
training run; no recipe change). Decision doc `.praxia/docs/audits/260902_p26b-floor-surface-decision.md`.
