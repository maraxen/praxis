---
title: 'P2.6 FunctionGemma fine-tune: pre-registered negative-mixing ablation and promotion rule'
description: 'Pre-registration for the Coxswain P2.6 fine-tune (backlog 4848): fixed D5 recipe with one recorded deviation, three mixing arms (A raw / B 50% / C 33% negatives) after train-side dedup, the promotion rule applied mechanically against baseline v2 on the same 228-row eval split, what would count as the single D8 threshold revision, and where checkpoints live.'
status: registered
task_id: 260901_p26_finetune
date: '260901'
---
# P2.6 FunctionGemma fine-tune: pre-registered negative-mixing ablation and promotion rule


Registered **before** any training run (commit order is the proof). Sidecar:
`scripts/experiments/p26_finetune.bth.toml` (validated with `bth validate-sidecar`).
Backlog 4848; jury call GO on the P2.5 gate (`260825_p25_slice_gate.md` rev 260901)
taken by the user on 2026-09-01.

## 1. What is fixed

| Item | Value | Source |
|---|---|---|
| Base model | `google/functiongemma-270m-it` @ `39eccb091651513a5dfb56892d3714c1b5b8276c` | same pin as baseline v2 |
| Corpus | `training/assemble/out/corpus_p25.jsonl` (812 rows, assembly 0.1.2), sha256 in every `train_manifest.json` | P2.5 |
| Train pool | `metadata == "train"` (584) -> exact normalized-utterance dedup, keep lowest `record_id` -> **515** (69 dropped) | gate condition 3 |
| Eval split | the SAME 228 rows baseline v2 scored; never touched, never deduped | gate condition 2 |
| Recipe | TRL `SFTTrainer`, full-parameter, lr 1e-5 cosine, warmup 0.1, bf16, gradient checkpointing, `adamw_torch_fused`, `completion_only_loss=True`, `packing=False`, `max_length = longest example + 100` (1489 on the full pool) | D5 / research §2b |
| Recorded deviation | `num_train_epochs=8`, effective batch 16 (bs 4 x accum 4). Mobile-Actions' 2 epochs x batch 32 on 9.6k rows is ~600 optimizer steps; on <=515 rows it would be ~32. Arms land at ~170-260 steps. | this doc |
| Seed | 0 (`(RECIPE_VERSION="0.1.0", arm, seed)` fully determines the row set) | `versions.py` |
| Decode at eval | greedy, `max_new_tokens=128`, stop at `<end_of_turn>` / `<start_function_response>` | F4/D3, unchanged |
| Venue | Engaging `mit_normal_gpu` (non-preemptable; L40S/H100/H200), `uv run --package training --extra train`, `HF_HUB_OFFLINE=1`, weights rsynced from the local HF cache | user decision 260901 |

## 2. The ablation (gate condition 1)

Positives (`clean_parse`, 226 after dedup) are never subsampled. Negatives are
drawn per clarify class proportionally to their post-dedup counts
(missing_slot 102 / ambiguous_referent 66 / out_of_surface 121), largest-remainder
rounding, `random.Random("0.1.0|<arm>|0")` over rows sorted by `record_id`.

| Arm | Ratio (neg per pos) | Rows | clean / missing / ambiguous / oos | Negative fraction |
|---|---|---|---|---|
| A | raw (all) | 515 | 226 / 102 / 66 / 121 | 0.561 |
| B | 1.0 | 452 | 226 / 80 / 51 / 95 | 0.500 |
| C | 0.5 | 339 | 226 / 40 / 26 / 47 | 0.333 |

Pinned by `training/tests/test_finetune_mixing.py`; a corpus change fails the test on purpose.

## 3. Promotion rule (applied mechanically, written before training)

Baseline v2 (`training/eval/reports/260901_baseline_real_v2.json`, n=228):
T_acc 0.162 [0.120, 0.216], T_clr_recall 0.705 [0.602, 0.790], T_clr_prec 0.564 [0.470, 0.653],
out-of-surface fabricated calls 13/44.

1. **Eligible** arm: `clarify_recall >= 0.705` (baseline point; must not regress).
2. **Selected** arm: highest `exact_match_accuracy` among eligible arms; tie -> higher `clarify_precision`.
3. **Promoted** iff the selected arm has `exact_match_accuracy >= 0.80` AND
   `clarify_precision >= 0.90` AND `clarify_recall >= 0.70` AND
   `tripwire_out_of_surface_tool_calls == 0` (AC-2.6.3), all on the full 228-row split.
4. Otherwise: report every arm's three numbers with Wilson 95% intervals beside
   baseline v2 and STOP. A **single** D8 threshold revision may be *proposed* to the
   user with the measured numbers as justification; it is never applied by the
   orchestrator. Sidecar outcomes mirror this: `pass` = promoted; `marginal` =
   eligible and above the baseline's upper Wilson bound (0.216) but an anchor
   missed; `fail` (residual) = recall regressed or accuracy indistinguishable
   from baseline.

What would NOT count as the revision: re-running with another seed or more
epochs until an arm clears (that is a new pre-registration), or scoring a
different eval split.

## 4. Controls and known limits

- The untrained base model scored on the identical split is the negative
  control (baseline v2). There is no positive control at 270M for this
  surface (rule card DSGN-001 acknowledged): a "no lift" result is checked
  against the training loss curve and the smoke's tokenization-contract guard
  (one `<bos>`, completion mask == prompt length) rather than a known-good model.
- Thresholds (rule card PREREG-001): T_acc / T_clr_recall / T_clr_prec are the
  provisional anchors of `260825_p25_provisional_thresholds.md`; the recall
  floor 0.705 and the 0.216 distinguishability bound are baseline v2's point
  estimate and Wilson upper bound respectively.
- `ambiguous_referent` clarify behaviour is not statically scored (harness
  `clarify_scope_note`); its eval slice (33 rows) contributes to exact match only.
- Checkpoints (~540 MB) are not committed: `outputs/p26/<arm>/checkpoint` on
  Engaging and `training/out/checkpoints/` locally (both gitignored); each
  arm's `train_manifest.json` and `eval_report.json` are committed under
  `training/out/p26/<arm>/` and `training/eval/reports/260901_p26_arm_<arm>.json`.
