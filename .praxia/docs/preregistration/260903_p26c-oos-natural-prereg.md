---
title: 'P2.6c pre-registration: out-of-surface natural-phrasing lane, arm-A retrain vs A2 on the frozen eval split'
description: Pre-registration (task 260903_p26c_oos_natural, backlog 4933) for extending the natural-phrasing lane to the 160 out-of-surface floor rows with the base row's clarification as supervision, assembling 0.1.5 with the pinned 228-row eval split unchanged, retraining the arm-A recipe once and scoring it against arm A2 (control) under the unchanged promotion rule; tripwire, no-regression, retention and out-of-surface probe predictions registered before generation.
status: registered 3c943fe4; run 21886402 evaluated -- P1/P4 fail, P2/P3 hold, NOT PROMOTED
task_id: 260903_p26c_oos_natural
date: '260903'
---
# P2.6c pre-registration: out-of-surface natural-phrasing lane, arm-A retrain vs A2 on the frozen eval split


Registered BEFORE any generator change, generation, or training (commit order is the
proof; the freeze artefact is commit `ca2fbc6a`, the 519 in-surface natural rows pinned
modulo `provenance.teacher_model_version`). Backlog 4933 (depends on 4890, done). Sidecar
`scripts/experiments/p26c_finetune.bth.toml`. Decision it follows: P2.6b decision doc
`.praxia/docs/audits/260902_p26b-floor-surface-decision.md` §6 ("the lane needs an
out-of-surface counterpart"), chosen by the user 2026-09-03 over the recipe sweep, a
matched-steps control arm, and the eval revision (golden id grammar / vague-span policy).

## 1. What is fixed (frozen), what changes

| Item | Status |
|---|---|
| Eval split | **FROZEN.** The 228 rows pinned by record_id AND native-row content in `training/assemble/data/eval_split_pin.json` (rows sha256 `8e023a33c2320c42a9be3cd0fc98110f3b7fae690871fff58bc9db51e22687d4`, pinned at assembly 0.1.3). The assembler asserts the pin; any drift is a deviation. |
| Comparators | baseline v2 re-score `training/eval/reports/260902_p26_rescore_baseline.json` (45/228 = 0.197); arm A re-score `260902_p26_rescore_A.json` (145/228 = 0.636, tripwire 1); **control: arm A2** `260902_p26b_A.json` (153/228 = 0.671 [0.608, 0.729], recall 0.920, precision 0.853, tripwire 3; checkpoint sha256 `ddcd3b41…`, bathos run `595e8374-ae36-4111-bd1b-f5f664cd531e`). All under the fixed scorer (amendment 8fe1b111). |
| Recipe | `RECIPE_VERSION 0.1.0` UNCHANGED (lr 1e-5 cosine, warmup 0.1, bf16, bs 4 × accum 4, 8 epochs, completion-only loss). Arm A = raw mix, seed 0. Optimizer steps rise with ~130 more train rows (≈ 560 vs 496); recorded as a confound, not tuned. |
| Base model, scorer, promotion rule, D8 anchors | UNCHANGED; revision UNSPENT. |
| Floor corpus (685 rows, 0.2.1) | UNCHANGED (`floor_0.2.0_accepted_digests.json` still asserted). Golden rows UNCHANGED. |
| Natural corpus, in-surface rows | The 519 committed rows stay byte-identical except `provenance.teacher_model_version`, which is corrected from `fake-teacher@test` (a stamping bug: the final P2.6b pass ran the fake backend on a warm cache) to the cache record's `gemini-3.7-flash-medium`. Pinned in `training/floor_gen/data/natural_v2_accepted_digests.json`; the in-surface prompt, its version and the lexicon are untouched (cache-preserving). |
| New data | natural variants of the 160 out-of-surface floor rows (`coverage_natural`, class `out_of_surface`): own prompt version `p23_nlify_v2_natural_oos` (same system string, seeded with the cell's off-surface request and the base utterance; keep every concrete detail, natural locations, no tool names, no identifiers); the base row's `clarification` is copied VERBATIM as the target, so supervision is identical to the base row and only the utterance surface varies; deterministic filter = identifier / dotted-well / bracket / base-duplicate / eval-duplicate rules (the canonical-verb rule is skipped for this class because out-of-surface requests legitimately mention liquid verbs). Variants of TRAIN-base rows (128) join train; variants of EVAL-base rows (32) join the PROBE set, never the 228. |
| Assembly | 0.1.5: pinned eval, natural rows per base split, probe gains an `out_of_surface` class; manifest records the pin sha and the train-only strata. `cross_split_duplicate_utterances` must stay at its ceiling 41. |
| Teacher | Gemini 3.7 Flash medium via `agy` (same as 0.2.0 floor and the P2.6b lane). |

## 2. Hypothesis

P2.6b's lane paraphrased only in-surface rows, so every casually phrased training utterance
was a tool call and the model learned "everyday phrasing ⇒ emit a call" (decision doc §4:
`golden-out-surface-11` "Order more tips from the vendor website" → `pick_up_tips{}`).
Casually phrased out-of-surface requests supervised with the same clarification target
restore the casual-phrasing ⇒ abstain balance without unlearning the surface mapping.

## 3. Pre-registered predictions (frozen 228 split, fixed scorer, A3 vs A2)

Row lists are frozen in `training/src/praxis_training/finetune/p26c_predictions.py`; the
checks are computed by `p26c_report.py` and the trainer's `--compare-report` path.

**P1 -- tripwire (primary).** Tripwire on the 228 **≤ 1** (A2: 3) AND at least **2 of the 3**
A2 tripwire rows (`golden-out-surface-05` → `read_sample`, `-10`, `-11` → `pick_up_tips{}`)
exact-match on A3.

**P2 -- no regression vs A2.** A3 exact ≥ 153/228 (0.671, the control's point estimate,
by the P2.6b convention); clarify recall ≥ 0.705; rows flipping hit → miss (A2 → A3) ≤ 5
(single unpaired seed; every flip listed by record_id and class).

**P3 -- surface gains retained.** `surface6` (`cov-0092/0093/0094-dispense__missing-slot`,
`cov-0172/0173/0174-transfer__ambiguous-referent`) still ≥ 4/6 (A2: 4); the 22 verb rows
still ≥ 11/22 outside {name_mismatch, no_call, unknown_verb} (A2: 11); the 90 in-surface
probe rows ≥ 0.80 (A2: 0.844; ≈ 1 SE).

**P4 -- out-of-surface probe (secondary, non-gating).** On the natural variants of the 32
out-of-surface eval-base floor rows (`corpus_p25_probe.jsonl`, class `out_of_surface`,
exact match = no call emitted), A3 − A2 ≥ +0.10 absolute; A2 and A are scored on the same
rows in the same job.

**P5 -- exploratory, no prediction.** `golden-ambig-ref-02/-11/-12` and
`golden-clean-drop_tips-01` (A2 over-canonicalised a vague span: `there` → `the well`,
`storage` → `storage_well`, `trash` → `trash_well`): expected 0-1/4; these need the
ambiguous-referent vague-span policy decision (coverage normalises to pool strings, golden
keeps them verbatim), not data. Golden miss count (A 61, A2 63) reported. The 44
out-of-surface eval rows' exact count (A2: 41) reported.

**Ceiling and verdict.** Recovering every non-golden miss gives 167/228 = 0.732 < T_acc 0.80.
**Expected: NOT PROMOTED** under the unchanged rule; `promotion.py` decides mechanically with
A, A2 and A3 side by side against baseline v2.

**Sidecar.** `pass` iff P1 ∧ P2 ∧ P3; `marginal` iff P1 holds, recall holds, flips ≤ 8 and
exact ≥ 0.608 (A2's Wilson lower bound) but a P2/P3 bound slipped; `fail` residual.

**Confounds recorded:** ≈ 1.13× optimizer steps at the fixed recipe; one seed, unpaired
shuffles (A2 vs A3 differ in data AND shuffle); same teacher model; out-of-surface
clarifications copied from the base rows, not teacher-written (the base lane's clarifications
were teacher-written for their own utterance, so a natural variant whose copied reply no
longer fits is a filter gap to record, not to silently accept).

## 4. Deviations

Any of: a pinned eval row missing or content-changed; any of the 685 floor rows or the 519
in-surface natural rows changed (beyond the teacher stamp); an edit to the in-surface natural
prompt, its version or the lexicon; a recipe change; more than one training run; A3 scored
on anything but the pinned split with the fixed scorer. A prediction failing is NOT a
deviation -- it is the result. Out-of-surface lane acceptance below 70 % on the first slice
allows tightening the oos prompt (its own version) BEFORE the full run, because no scored
artefact depends on it; the tightened text is recorded here.

## 5. Storage

Natural corpus + manifest + ~160 cache files (`training/out/corpus_p23_floor_natural.jsonl`,
`manifest_natural.json`, `training/cache/`); assembly 0.1.5 outputs incl. probe files; train
manifest `training/out/p26c/A/train_manifest.json`; reports
`training/eval/reports/260903_p26c_A3.json`, `260903_p26c_probe_{A,A2,A3}.json` with generation
dumps under `training/eval/outputs/`; checkpoint uncommitted at `outputs/p26c/A/checkpoint`
(sha256 in the manifest). bathos run tagged `arm:A3`, `task:260903_p26c_oos_natural`.

### 5.1 Local dry-run before submission (assembly 0.1.5, commit `4315538b`)

`p26c_finetune.py --arm A --seed 0 --dry-run`: train rows assembled 1199, dedup dropped 91,
selected 1108 (clean_parse 382 / missing_slot 265 / ambiguous_referent 216 / out_of_surface 245;
A2 trained on 984 with 121 out_of_surface), negative fraction 0.655 (A2: 0.612). Expected
optimizer steps ≈ 8 × ⌈1108/16⌉ = 560 (A2: 496; ≈ 1.13×, the recorded confound). Eval pin
asserted at assembly (228 ids + digests); probe 122 rows (90 in-surface + 32 out-of-surface).
Job = one Slurm GPU job: `bth run` (train + eval + probe) for A3, then the eval CLI scoring the
A2 and A checkpoints on the same 122-row probe (`--dump-outputs`), as in P2.6b's job 21842239.

## 6. Outcome (260903, mechanical)

P1 **fails** (tripwire 3, 0/3 recovered -- the same three golden rows, same generations as A2),
P2 **holds** (0.671 = control, recall 0.898, 1 flip each way), P3 **holds** (surface6 4/6,
verb22 12/22, in-surface probe 0.811), P4 **fails** (A, A2 and A3 all 32/32 on the casual
out-of-surface probe: the probe never discriminated), P5 ambig4 0/4, golden misses 63 → 63.
Sidecar `fail` (residual). Promotion: NOT PROMOTED (selected A3 on the precision tie-break).
Deviations: none. The hypothesis in §2 is falsified: the tripwire rows are near-surface topical
confusions, not a casual-phrasing cue. Decision doc
`.praxia/docs/audits/260903_p26c-oos-natural-decision.md`.
