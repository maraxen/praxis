---
title: Coxswain P2.6 promotion decision -- three-arm mixing ablation vs baseline v2 (pre-registered rule)
description: 'Mechanical application of the pre-registered P2.6 promotion rule to arms A/B/C: all eligible, all marginal, A selected, NOT PROMOTED. Failure breakdown separates two scorer artifacts and one gold-set defect from genuine misses; the single D8 revision is proposed AGAINST spending now.'
status: decided-260901; re-scored-260902 (§8)
task_id: 260901_p26_finetune
date: '260901'
verdict: 'NOT PROMOTED (selected A) -- all three arms marginal; D8 revision UNSPENT (user decision 260901); fixed-scorer re-score 260902 (§8): A 0.636, still NOT PROMOTED'
base_sha: ebd6b76d
---
# Coxswain P2.6 promotion decision -- three-arm mixing ablation vs baseline v2 (pre-registered rule)

Task `260901_p26_finetune` (backlog 4848, continues 480). Pre-registration:
`.praxia/docs/preregistration/260901_p26-finetune-prereg.md` (committed `2664681b`,
before any job was submitted). Rule applied by
`training/src/praxis_training/finetune/promotion.py`; machine output
`training/eval/reports/260901_p26_promotion.json`. Nothing in this document
re-scores a report or alters the rule; §5 is a *proposal* to the user, per D8.

## 0. Decision (user, 260901)

The user accepted all three items on 2026-09-01: (1) the mechanical
verdict NOT PROMOTED stands; (2) the single D8 threshold revision stays
**unspent** -- anchors remain 0.80 / 0.70 / 0.90 / tripwire 0; (3) the next
sprint is §6 item 1: scorer fixes plus a re-score of the same three
checkpoints under a pre-registration amendment (no retraining). P2.7b stays
blocked on a promoted checkpoint.

## 1. Verdict (mechanical)

| Arm | T_acc (>= 0.80) | T_clr_recall (>= 0.70) | T_clr_prec (>= 0.90) | tripwire (== 0) | eligible | outcome |
|---|---|---|---|---|---|---|
| baseline v2 | 0.162 [0.120, 0.216] (37/228) | 0.705 [0.602, 0.790] (62/88) | 0.564 [0.470, 0.653] (62/110) | 13 (derived) | -- | -- |
| A (raw, 56% neg) | 0.386 [0.325, 0.451] (88/228) | 0.864 [0.777, 0.920] (76/88) | 0.835 [0.746, 0.897] (76/91) | 1 | yes | marginal |
| B (50% neg) | 0.373 [0.313, 0.437] (85/228) | 0.841 [0.751, 0.903] (74/88) | 0.851 [0.761, 0.911] (74/87) | 2 | yes | marginal |
| C (33% neg) | 0.355 [0.296, 0.419] (81/228) | 0.784 [0.687, 0.857] (69/88) | 0.841 [0.747, 0.905] (69/82) | 3 | yes | marginal |

Rule (prereg §3): eligible iff `clarify_recall >= 0.705`; selected = highest
`exact_match_accuracy` among eligible (tie: higher precision, then earlier
letter); promoted iff acc >= 0.80 AND prec >= 0.90 AND recall >= 0.70 AND
tripwire == 0.

Eligible: A, B, C. Selected: **A**. **Verdict: NOT PROMOTED (selected A).**

Sidecar outcomes (`scripts/experiments/p26_finetune.bth.toml`, evaluated by
bathos on the compute node, pulled into the local catalog): A `marginal`
(run `76b08523`), B `marginal` (`e59d35b2`), C `marginal` (`455a50cb`) --
identical to the script's per-arm outcome column. Every arm cleared the
0.216 distinguishability bound (baseline's Wilson upper) by a wide margin and
none regressed recall, so the ablation is a real lift that fails the anchors,
not a null result.

Direction of the mixing effect: A > B > C on accuracy AND recall, monotone in
the amount of negatives kept. The confidence intervals overlap heavily (one
seed, n=228), so this is a trend, not a finding; the pre-registered selection
still picks A.

## 2. Provenance

- Recipe `0.1.0` (`finetune/versions.py`): TRL `SFTTrainer` full-parameter,
  lr 1e-5 cosine, warmup 0.1, bf16, grad-checkpointing, bs 4 x accum 4,
  `completion_only_loss=True`, `packing=False`, 8 epochs (the one recorded
  deviation from D5's 2 epochs; prereg §1). `max_length` 1489 = longest
  rendered row 1389 + 100, identical across arms.
- Libraries: torch 2.13.0+cu130, transformers 4.57.1, trl 0.25.1, datasets
  4.4.1, accelerate 1.14.0, Python 3.14.3. Base
  `google/functiongemma-270m-it@39eccb091651513a5dfb56892d3714c1b5b8276c`,
  weights rsynced from the local HF cache; jobs ran `HF_HUB_OFFLINE=1
  TRANSFORMERS_OFFLINE=1`. No token left this machine.
- Venue: Engaging `mit_normal_gpu`, one NVIDIA L40S per arm, `bth run` inside
  `myxcel submit-job` (preset `gpu`). Slurm 21781446 (A, 464 s train),
  21781448 (B, 401 s), 21781449 (C, 304 s); eval ~90 s each. Three earlier
  submissions failed on harness wiring, not on the recipe
  (21781111/21781114: `bth run` invoked the wrong interpreter; 21781118
  cancelled) -- bathos records them as `error`.
- Train sets after dedup (69 exact normalized-utterance duplicates dropped
  from 584 train rows): A 515 (neg 0.561), B 452 (0.500), C 339 (0.333); the
  235 positives are never subsampled; class proportions of negatives held
  (mixing block of each manifest lists the record_ids).
- Loss curves (manifest `training.log_history`): all arms fall from ~3.3 to
  ~0.4 by epoch 3 and plateau there (A final train_loss 0.677 averaged,
  mean_token_accuracy 0.93). No divergence; a non-fatal CUDA caching
  allocator OOM-retry was logged at step 1 on each arm, after which every
  step ran (8.0 epochs completed in all three manifests).
- Checkpoints: 545 MB each, NOT committed. On Engaging and locally at
  `outputs/p26/<arm>/checkpoint` (gitignored). Directory digests, verified
  against the pulled copies: A `376cac6e5edf…`, B `792f7d5c396b…`,
  C `f00876d0daa5…` (full sha256 in `training/out/p26/<arm>/train_manifest.json`).
  The manifests' `git` block is empty because the Engaging copy is an rsync
  mirror without `.git`; the training code that ran is commit `ebd6b76d`
  (last commit before submission; the promotion script `2f027ecb` and later
  commits change nothing the jobs executed).
- Committed this sprint: three eval reports + three manifests + promotion
  JSON + failure breakdown JSON, 312 KB total; zero staged-dist bytes.

## 3. What the fine-tune fixed, per class (exact match; A vs baseline v2)

| class | n | baseline exact | A exact | B exact | C exact | baseline spurious clarify | A spurious clarify |
|---|---|---|---|---|---|---|---|
| clean_parse | 107 | 6 (0.056) | 25 (0.234) | 25 | 24 | 34 | 13 |
| missing_slot | 44 | 0 (0.000) | 16 (0.364) | 14 | 12 | -- (28/44 flagged) | -- (33/44 flagged) |
| ambiguous_referent | 33 | 0 (0.000) | 4 (0.121) | 4 | 4 | 14 | 2 |
| out_of_surface | 44 | 31 (0.705) | 43 (0.977) | 42 | 41 | -- (13 fabricated) | -- (1 fabricated) |

The two behaviours the gate doc said a fine-tune must fix both moved:
spurious clarifies on clean rows fell 34 -> 13 and fabricated calls on
out-of-surface rows fell 13 -> 1 (the residual 1 is the tripwire miss).
Clarify precision rose 0.564 -> 0.835 because of the first; recall rose
0.705 -> 0.864 because missing-slot rows are now flagged 33/44 instead of 28/44.
Exact match on tool-call rows is the anchor that stays far away.

## 4. Where the remaining misses go (diagnostic, not a re-score)

`training/src/praxis_training/finetune/failure_breakdown.py` classifies every
failed row's scorer reasons; output
`training/eval/reports/260901_p26_failure_breakdown.json`; unit-tested on
synthetic reasons (`test_finetune_failure_breakdown.py`).

| report | exact | no_call | spurious_call | unknown_verb | name_mismatch | list_escape_format | slot_order_only | gold_slot_annotation | param_content | other | artifact rows | ceiling if artifacts fixed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline_v2 | 37/228 | 56 | 13 | 0 | 33 | 1 | 4 | 3 | 71 | 10 | 8 | 0.197 |
| A | 88/228 | 10 | 1 | 1 | 11 | 12 | 26 | 16 | 60 | 3 | 54 | 0.623 |
| B | 85/228 | 9 | 2 | 1 | 13 | 10 | 25 | 15 | 66 | 2 | 50 | 0.592 |
| C | 81/228 | 6 | 3 | 1 | 14 | 11 | 22 | 14 | 73 | 3 | 47 | 0.561 |

Three categories are measurement problems, verified in source, not model errors:

1. **`list_escape_format` (12 rows on A).** FunctionGemma's chat template
   serialises a list argument as `[<escape>a<escape>,<escape>b<escape>]`
   (`format_argument` macro, checkpoint `chat_template.jinja`); the training
   labels therefore carry that form and the model reproduces it faithfully.
   `baseline_eval/fgml_parser.py` has no nested-list decoding
   (`_strip_escapes` only unwraps a value that *starts* with `<escape>`), so
   the value is compared as one string against the intended Python list and
   fails. Example: predicted `at: '[<escape>tip_rack.C5<escape>]'` vs intended
   `at: ['tip_rack.C5']`. The render round-trip test in
   `test_finetune_render.py` sampled the first 25 tool-call rows and none had
   a list-valued argument -- the test's coverage, not its logic, missed this.
2. **`slot_order_only` (26 rows on A).** The template's `dictsort` emits
   argument keys alphabetically; `check_intent_agreement`
   (`coxswain/src/coxswain/plr/intent_record.py`) compares the derived
   `unresolved_slots` *tuple* positionally against the gold tuple, whose
   order follows the sidecar's parameter order. Params are equal on these
   rows (no `params mismatch` reason is emitted), only the slot order differs.
3. **`gold_slot_annotation` (16 rows on A, all `golden-ambig-ref-*`).** Params
   equal, yet the gold record's own `unresolved_slots` annotation is empty
   while `derive_call_gaps` on those same params yields slots. No model can
   ever pass such a row; it is a gold-set defect (the golden records predate
   the D11 derivation and were never re-annotated).

Crediting every artifact row as a hit -- an upper bound, not a score -- A
would reach **0.623**, still far below the 0.80 anchor. The genuine
remainder on A is 60 `param_content` rows plus 11 wrong tool names and 10
abstentions. The dominant genuine patterns, read off the reasons:
surface-form slot references the model emits in a canonical-looking but
wrong shape (`plate[1]` for `plate_1.D1`; `plate_2 D9` for `plate_2.D9`),
hallucinated extra arguments (a `source` that the utterance never gave),
and `move_plate` vs `move_resource` confusion (8 + 3 rows). The first is the
`floor_gen` synth-vs-surface gap the gate doc already tracks; the second is
a data-coverage issue for missing-slot rows; the third is a name-level
ambiguity in the 13-tool surface itself.

## 5. D8 threshold revision -- PROPOSAL: do not spend it now

D8 allows exactly one revision at P2.6, with a written reason
(`260825_p25_provisional_thresholds.md` §4). The numbers argue against
spending it:

- No admissible revision changes the verdict. A's accuracy upper bound is
  0.451 against T_acc 0.80; even the artifact-corrected ceiling is 0.623.
  A revision that A could pass would set T_acc at or below ~0.45, which is
  not a calibration but an abandonment of the anchor. Precision alone
  (0.835 vs 0.90) is within reach of a modest revision, but the promotion
  would still fail on accuracy and on the tripwire (1, 2, 3 fabricated
  calls), so revising precision flips nothing.
- Neither legitimate reason in §4 applies: the eval slices did not change
  (same 228 rows as baseline v2), and the live baseline is already the
  reference measurement.
- The gap is measurement (54 artifact rows) plus data (surface forms),
  not threshold calibration. Spending the single revision before those are
  fixed forfeits it for a later, better-informed use.

**Proposed: keep all three anchors as they stand and the D8 revision
unspent.** If the user prefers to spend it anyway, the only candidate the
numbers support is `T_clr_prec` 0.90 -> 0.85 (A: 0.835 [0.746, 0.897];
B: 0.851 [0.761, 0.911]); it would not promote any arm.

## 6. Recommended next sprint (not started; user's call)

1. **Scorer fixes, then RE-SCORE the same three checkpoints (no retraining).**
   Nested-list decoding in `fgml_parser`, order-insensitive `unresolved_slots`
   comparison in `check_intent_agreement`, and re-derived `unresolved_slots`
   for the 16 golden rows. This is a scoring change, so it needs a short
   pre-registration amendment stating that the fixed scorer is applied to
   baseline v2 AND all three arms, both sets of numbers are reported, and
   the promotion rule is unchanged. The breakdown script's ceiling (0.623)
   is the pre-registered prediction of what A can reach; anything above it
   would mean the fix changed more than the artifacts.
2. **Data:** the `floor_gen.synth` scalar-surface fix already on the gate
   doc's open list (recovers the surface-form misses and the
   `pick_up_tips__ambiguous-referent` cell), plus coverage for the
   hallucinated-argument pattern on missing-slot rows.
3. **Recipe (new prereg):** the loss plateau at ~0.4 by epoch 3 with lr 1e-5
   suggests under-fitting at 270M; a small lr sweep (3e-5, 1e-4) on arm A's
   mix is the cheapest next lever, and a second seed on A would size the
   interval that the one-seed ablation cannot.

## 7. Cross-links

- Thresholds doc status line updated (`260825_p25_provisional_thresholds.md`):
  P2.6 applied, revision unspent, pointer here.
- Slice gate doc §5 (`260825_p25_slice_gate.md`): item 4 points here.
- Reports: `training/eval/reports/260901_p26_arm_{A,B,C}.json`,
  `260901_p26_promotion.json`, `260901_p26_failure_breakdown.json`.
- Manifests: `training/out/p26/{A,B,C}/train_manifest.json`.
- bathos: `bth find --slurm-job 21781446|21781448|21781449` (project `praxis`).

## 8. Addendum 260902 -- fixed-scorer re-score (task `260902_p26_rescore`, backlog 4861)

Executed §6 item 1 under the pre-registration amendment
`.praxia/docs/preregistration/260902_p26-rescore-amendment.md` (commit `8fe1b111`,
before any scorer change). Nothing was retrained; the generations of every model were
frozen first (`training/eval/outputs/260902_p26_dump_*.json`, commit `d82d4404`) and the
old scorer over those dumps reproduced this document's §1 numbers exactly (identical
failed-row sets, clarify metrics and tripwire; baseline on local CPU fp32, arms on an
Engaging L40S cuda/bf16, Slurm 21810821). The three defects of §4 were then fixed at
their source -- `fgml_parser` nested-value decoding (`dd4498e7`), order-insensitive
`unresolved_slots` comparison in `check_intent_agreement` (`1b9ed30f`), and an assembler
that derives gap fields for every call (0.1.3, `cda6a770`; sidecar sha `fb18d8d0…` ->
`d66f7185…`, pairs file byte-identical, eval record set unchanged) -- and the dumps were
re-scored in recorded mode (four bathos runs of `scripts/experiments/p26_rescore.py`,
sidecar `p26_rescore.bth.toml`, all `pass`).

**The pre-registered row-level prediction held on all four models:** no row flipped
hit -> miss, every miss -> hit flip was in the artifact set, every artifact row flipped,
clarify recall / precision / confusion / tripwire identical (`*.check.json`).

| model | exact 260901 (old scorer) | exact 260902 (fixed scorer) | recall | precision | tripwire | eligible | outcome |
|---|---|---|---|---|---|---|---|
| baseline v2 | 0.162 [0.120, 0.216] (37/228) | **0.197 [0.151, 0.254] (45/228)** | 0.705 (62/88) | 0.564 (62/110) | 13 | -- | -- |
| A (raw, 56% neg) | 0.386 [0.325, 0.451] (88/228) | **0.636 [0.572, 0.696] (145/228)** | 0.864 (76/88) | 0.835 (76/91) | 1 | yes | marginal |
| B (50% neg) | 0.373 [0.313, 0.437] (85/228) | **0.601 [0.536, 0.662] (137/228)** | 0.841 (74/88) | 0.851 (74/87) | 2 | yes | marginal |
| C (33% neg) | 0.355 [0.296, 0.419] (81/228) | **0.575 [0.510, 0.637] (131/228)** | 0.784 (69/88) | 0.841 (69/82) | 3 | yes | marginal |

Rule unchanged (§1). Eligible: A, B, C. Selected: **A**. **Verdict: NOT PROMOTED
(selected A)** -- `training/eval/reports/260902_p26_rescore_promotion.json`. The D8
revision remains unspent; the accuracy gap to T_acc 0.80 is now 0.164 on the point
estimate (upper Wilson bound 0.696), all of it model behaviour.

Per class, A (fixed scorer): clean_parse 59/107 (was 25), missing_slot 25/44 (was 16),
ambiguous_referent 18/33 (was 4), out_of_surface 43/44 (unchanged). Baseline v2:
13/107, 0/44, 1/33, 31/44.

Residual misses on A (`260902_p26_rescore_failure_breakdown.json`, artifact categories
now 0 everywhere): 60 `param_content`, 11 `name_mismatch`, 10 `no_call`, 1 spurious
call, 1 unknown verb -- the surface-form / hallucinated-argument / `move_plate` vs
`move_resource` patterns already named in §4. §6 items 2 (data) and 3 (recipe) are the
next levers; each needs its own pre-registration and the user's call.

Enablers that outlive this sprint: every `baseline_eval` run can persist its generations
(`--dump-outputs`) so scorer changes are pure `--recorded` re-scores; cluster commands go
through `scripts/slurm/bth_run.sh` (catalog env verified on the compute node);
`test_assembly_gap_fields.py` and the stratified render round-trip test guard the three
defects. Deferred (debt): parser booleans and escaped-numeric coercion.
