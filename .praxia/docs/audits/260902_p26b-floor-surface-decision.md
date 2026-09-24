---
title: Coxswain P2.6b decision -- floor_gen surface-form data fix, arm A retrained on the frozen eval split
description: 'Outcome of the pre-registered P2.6b sprint (task 260902_p26b_surface_data, backlog 4890): synth 0.2.1 repaired the 60 excluded floor rows without moving the eval split, the natural-phrasing lane added 429 train rows and a 90-row probe set, arm A was retrained once at the unchanged recipe and scored on the pinned 228 rows against baseline v2 and the existing A checkpoint; predictions P1-P4 evaluated mechanically, promotion rule unchanged.'
status: decided-mechanically-260902; user call pending
task_id: 260902_p26b_surface_data
date: '260902'
verdict: ''
base_sha: ''
---
# Coxswain P2.6b decision -- floor_gen surface-form data fix, arm A retrained on the frozen eval split


Task `260902_p26b_surface_data` (backlog 4890). Pre-registration
`.praxia/docs/preregistration/260902_p26b-floor-surface-prereg.md` (commit `cc662026`, before any
generator change; freeze artefacts `b86a9127`). Sidecar `scripts/experiments/p26b_finetune.bth.toml`,
bathos run `595e8374` (Slurm 21842239, Engaging L40S, 20 min). Every number below comes from
`python -m praxis_training.finetune.p26b_report` over the committed reports
(`training/eval/reports/260902_p26b_predictions.json`) and from `promotion.py`
(`260902_p26b_promotion.json`). Nothing here re-scores or alters the rule.

## 1. What was built (all pre-registered)

- **Floor 0.2.1**: the 60 rows assembly 0.1.3 excluded (cardinality bug in `synth.py`) are
  repaired by a post-synthesis coercion keyed on `DECLARED_ARRAY_PARAMS`; the RNG seed stayed at
  0.2.0, so the 625 previously accepted rows are byte-identical and the 228-row eval split is
  untouched (pin `8e023a33…`, content digests asserted by the assembler). 60 teacher rows re-fetched.
- **Natural-phrasing lane**: 525 in-surface base rows → 519 variants accepted (98.9%; 6 rejected for
  a canonical liquid verb), same structured calls, natural locations and everyday verbs, own prompt
  version (`p23_nlify_v2_natural`); base prompt text untouched.
- **Assembly 0.1.4**: 1301 rows = eval 228 (pinned) + train 1073 (584 + 60 repaired + 429 natural);
  90 natural variants of eval-base rows form the probe set; exclusions 12 (overlay, by design);
  cross-split duplicate utterances unchanged at 41.
- **A2**: arm-A recipe 0.1.0 unchanged (8 epochs, bs 4 x 4, lr 1e-5), seed 0, on 984 deduped train
  rows (61% negatives): 496 optimizer steps (A: 264), train_loss 0.422, checkpoint sha256
  `ddcd3b41…` (uncommitted, `outputs/p26b/A/checkpoint`). Scored on the pinned 228 (cuda/bf16,
  generations dumped) with the fixed scorer; the existing A checkpoint is the control.

## 2. Results on the frozen 228-row split (fixed scorer)

| model | exact match | clarify recall | clarify precision | tripwire |
|---|---|---|---|---|
| baseline v2 | 0.197 [0.151, 0.254] (45/228) | 0.705 [0.602, 0.790] (62/88) | 0.564 [0.470, 0.653] (62/110) | 13 |
| A (P2.6, corpus 0.1.3) | 0.636 [0.572, 0.696] (145/228) | 0.864 [0.777, 0.920] (76/88) | 0.835 [0.746, 0.897] (76/91) | 1 |
| **A2 (P2.6b, corpus 0.1.4)** | **0.671 [0.608, 0.729] (153/228)** | **0.920 [0.845, 0.961] (81/88)** | 0.853 [0.768, 0.910] (81/95) | **3** |

Per class (exact, A → A2): clean_parse 59 → 62 / 107; missing_slot 25 → 31 / 44;
ambiguous_referent 18 → 19 / 33; out_of_surface 43 → 41 / 44. Flips: 16 miss → hit, 8 hit → miss.

## 3. Pre-registered predictions

| prediction | result | holds |
|---|---|---|
| P1 location surface (6 coverage rows, 0/6 on A) | **4/6** (`cov-0092`, `0093`, `0172`, `0174` pass; `0094` drops the well: `plate_1` for `plate_1.G6`; `0173` uses the overlay bracket grammar `plate_1["A1"]`) | **yes** (>= 4) |
| P2 verb migration (22 rows) | **11/22** leave name_mismatch / no_call / unknown_verb (verb recognised; params still fail on most) | **yes** (>= 11, exactly at the bar) |
| P2b `discard_tips` pair exact | 0/2 (still `drop_tips`) | no |
| P3 must-not-regress | acc 0.671 >= 0.636 yes; recall 0.920 >= 0.705 yes; **tripwire 3 > 1 NO**; **8 hit → miss > 5 NO** | **no** |
| P4 probe set (n=90, natural variants of eval-base rows) | A 0.233 → A2 **0.844** (+0.611); per class A2 19/21, 32/37, 25/32 | **yes** (>= +0.10) |
| Exploratory | vague3 1/3; hallucinated4 2/4; golden misses 61 → 63 | -- |

Sidecar outcome: **`fail` (residual)** -- P3 failed on the tripwire and the flip count. The
transfer effect is real (P1, P4, the probe's 0.611 jump); the regression is specific (§4).

## 4. The 8 hit → miss flips, read from the dumps

1. **Two fabricated calls on out-of-surface rows** (`golden-out-surface-05` "What's the
   concentration of sample 4?" → `read_sample`, an unknown verb; `-11` "Order more tips from the
   vendor website" → `pick_up_tips{}`). Tripwire 1 → 3. The natural lane deliberately added NO
   out-of-surface variants, so every casually phrased training utterance is an in-surface call:
   the model learned "everyday phrasing ⇒ emit a call". This is the plan's stated risk realised
   on the one class the lane did not cover.
2. **Three golden ambiguous-referent rows over-canonicalised** (`there` → `the well`, `storage` →
   `storage_well`, `the usual spot` → `drop_tips{}`), plus `golden-clean-drop_tips-01` (`trash` →
   `trash_well`): the lane taught "natural phrase → canonical id" and the model now appends
   `_well`-style suffixes to plain nouns and normalises vague spans golden keeps verbatim (the
   ambiguous-referent policy inconsistency named in the residual analysis).
3. `cov-0608` (ambiguous `lid`): A2 omits the vague `lid` argument instead of echoing it.
4. `ovl-f38dc0780c`: `stamp` for `dispense` on a code-grammar overlay row.

## 5. Verdict

Promotion rule unchanged (`promotion.py`, baseline v2 re-score as floor): eligible A, A2;
**selected A2; NOT PROMOTED** (acc 0.671 < 0.80, prec 0.853 < 0.90, tripwire 3). D8 revision
stays unspent. The pre-registered ceiling (0.732) was not reached; A2 lands 8 rows above A.

## 6. What this establishes, and the next lever (user's call)

- **Natural-surface data transfers.** Rows the model had never seen in natural phrasing flip
  (4/6 primary rows; probe +0.611) -- the data gap named in the P2.6 promotion doc §6 item 2 was
  real and is now mostly closed for coverage-style rows.
- **The lane needs an out-of-surface counterpart.** The tripwire regression is the direct
  consequence of paraphrasing only in-surface rows. The cheapest next step is natural variants
  of the 160 out-of-surface floor rows (same clarification supervision), which restores the
  casual-phrasing ⇒ abstain balance; that is a new pre-registration (P2.6c), not a tweak.
- **Ambiguous-referent policy** (coverage normalises vague spans to pool strings, golden keeps them
  verbatim) now costs rows in both directions and is a data-spec decision, not a generator fix.
- **Golden id grammar** (underscore vs dotted) remains the jury item from the prereg §3 P5; golden
  misses did not improve (61 → 63).
- Recipe sweep (promotion doc §6 item 3) is still untried; note A2 already ran 1.9× the optimizer
  steps of A at the same recipe (confound recorded).

Gate-doc open item ("floor_gen.synth scalar-surface compliance", +60 rows incl. the
`pick_up_tips__ambiguous-referent` cell) is **closed** by floor 0.2.1 / assembly 0.1.4; the
recovered cells are train-only until a future eval revision.

## 7. Cross-links

Reports `training/eval/reports/260902_p26b_{A,probe_A,probe_A2,predictions,promotion}.json`;
dumps `training/eval/outputs/260902_p26b_*`; manifest `training/out/p26b/A/train_manifest.json`;
natural manifest `training/out/manifest_natural.json`; assembly manifest 0.1.4; prereg
`260902_p26b-floor-surface-prereg.md`; bathos `bth find --tag task:260902_p26b_surface_data`.
