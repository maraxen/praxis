---
title: 'P2.6c decision: out-of-surface natural lane, arm A3 vs A2 on the frozen 228-row split'
description: 'Mechanical decision for task 260903_p26c_oos_natural (backlog 4933): arm A3 (recipe 0.1.0 on assembly 0.1.5, natural lane covering the out-of-surface floor rows) scored on the pinned 228-row eval split and the 122-row probe against arm A2 as control; the pre-registered predictions P1-P5 evaluated by p26c_report, promotion decided by promotion.py under the unchanged rule.'
status: decided-mechanically-260903; user call pending
task_id: 260903_p26c_oos_natural
date: '260903'
verdict: NOT PROMOTED (selected A3); P1 and P4 fail, P2 and P3 hold; sidecar fail (residual)
base_sha: 0de3da09
---
# P2.6c decision: out-of-surface natural lane, arm A3 vs A2 on the frozen 228-row split


Task `260903_p26c_oos_natural` (backlog 4933). Pre-registration
`.praxia/docs/preregistration/260903_p26c-oos-natural-prereg.md` (commit `3c943fe4`, before any
generator change; freeze artefact `ca2fbc6a`). Sidecar `scripts/experiments/p26c_finetune.bth.toml`,
bathos run `1387da1c` (Slurm 21886402, Engaging L40S, 24 min incl. two probe re-scores). Every
number below comes from `python -m praxis_training.finetune.p26c_report` over the committed
reports (`training/eval/reports/260903_p26c_predictions.json`) and from `promotion.py`
(`260903_p26c_promotion.json`). Nothing here re-scores or alters the rule.

## 1. What was built (all pre-registered)

- **Natural lane, out-of-surface**: 160 base rows → 158 variants accepted (98.8 %; 2 duplicates of
  their base), own prompt version `p23_nlify_v2_natural_oos`, the base row's clarification copied
  verbatim as supervision; the in-surface prompt, version and lexicon untouched (685/685 cache
  hits on the full pass; the 519 in-surface rows byte-identical modulo the corrected teacher stamp).
- **Provenance fix**: every committed natural row had said `teacher_model_version =
  fake-teacher@test` while its cache entry said `gemini-3.7-flash-medium`; the lane now stamps
  from the cache record and the corpus test forbids the fake stamp.
- **Assembly 0.1.5**: 1427 rows = eval 228 (pin `8e023a33…` asserted, digests unchanged) +
  train 1199 (1073 + 126); probe 90 → 122 (32 `out_of_surface`); cross-split duplicates 41
  (ceiling); mixing for arm A: 1108 rows after dedup (245 out_of_surface; A2 had 984 / 121).
- **Arm A3**: recipe 0.1.0 unchanged, seed 0, 560 optimizer steps (A2 496), train loss 0.529
  (A2 0.422 -- more clarification-text targets), checkpoint sha256 `f8d247d1…` (uncommitted,
  `outputs/p26c/A/checkpoint`, also on Engaging).

## 2. Results on the frozen 228-row split (fixed scorer)

| model | exact match | clarify recall | clarify precision | tripwire |
|---|---|---|---|---|
| baseline v2 | 0.197 [0.151, 0.254] (45/228) | 0.705 [0.602, 0.790] (62/88) | 0.564 [0.470, 0.653] (62/110) | 13 |
| A (P2.6, corpus 0.1.3) | 0.636 [0.572, 0.696] (145/228) | 0.864 [0.777, 0.920] (76/88) | 0.835 [0.746, 0.897] (76/91) | 1 |
| A2 (P2.6b, corpus 0.1.4, control) | 0.671 [0.608, 0.729] (153/228) | 0.920 [0.845, 0.961] (81/88) | 0.853 [0.768, 0.910] (81/95) | 3 |
| **A3 (P2.6c, corpus 0.1.5)** | **0.671 [0.608, 0.729] (153/228)** | 0.898 [0.817, 0.945] (79/88) | 0.878 [0.794, 0.930] (79/90) | **3** |

| class | A2 | A3 | n |
|---|---|---|---|
| ambiguous_referent | 19 | 20 | 33 |
| clean_parse | 62 | 62 | 107 |
| missing_slot | 31 | 30 | 44 |
| out_of_surface | 41 | 41 | 44 |

Residual categories A3: name_mismatch 11, no_call 2, param_content 58, spurious_call 2,
unknown_verb 2 (A2: 11 / 2 / 58 / 2 / 2 -- identical shape). Golden misses 63 → 63.

## 3. Pre-registered predictions

| prediction | value | needed | holds |
|---|---|---|---|
| P1 tripwire | tripwire 3, tripwire3 recovered 0/3 | ≤ 1 and ≥ 2/3 | **False** |
| P2 no regression vs A2 | acc 0.671 (≥ 0.671), recall 0.898 (≥ 0.705), hit→miss 1 (≤ 5) | all | True |
| P3 surface gains retained | surface6 4/6 (≥ 4), verb22 12/22 (≥ 11), in-surface probe 0.811 (≥ 0.80, n = 90) | all | True |
| P4 oos probe (n = 32) | A2 1.000 → A3 1.000 (Δ +0.000) | ≥ +0.10 | **False** |
| P5 exploratory | ambig4 0/4; oos44 exact 41 → 41; golden misses 63 → 63 | -- | -- |

Probe by class (successes / n): A 3/21, 7/37, 11/32, **32/32**; A2 19/21, 32/37, 25/32,
**32/32**; A3 19/21, 32/37, 22/32, **32/32** (ambiguous_referent, clean_parse, missing_slot,
out_of_surface).

## 4. The flips and the tripwire rows, read from the dumps

- **Only one flip each way, both `move_lid` rows trading the same pattern**:
  `cov-0547-move_lid__missing-slot-12` hit → miss (A3 adds `lid: "the lid"` on a row whose
  gold omits it) and `cov-0608-move_lid__ambiguous-referent-13` miss → hit (A3 now echoes the
  vague `lid`). Net zero; 153/228 both sides.
- **The three tripwire rows are byte-for-byte the same failure as on A2**:
  `golden-out-surface-05` "What's the concentration of sample 4?" → `read_sample{at:[sample_4]}`;
  `-10` "Show me the deck layout." → `move_plate{destination: deck_layout_container_1}` (A2:
  `deck_layout_string`); `-11` "Order more tips from the vendor website." →
  `pick_up_tips{at:[the vendor website]}` (A2: `pick_up_tips{}`). Each names a surface object
  (sample/read, deck/plate, tips) and asks for an unsupported action.
- **Every checkpoint abstains on every casual floor-style out-of-surface probe row** -- A (which
  never saw a natural row), A2 and A3 all score 32/32. The 8 floor out-of-surface cells (mix,
  blow_out, touch_tip, dispense_to_waste, set_temperature, shake, stop_shaking, generic) are far
  from the surface in topic, and abstaining on them was never the problem.
- The four over-canonicalised golden ambiguous rows are unchanged (`the well`, `storage_well`,
  `trash_well`, bare `drop_tips{}`), as predicted: a policy item, not data.

## 5. Verdict

Sidecar: **fail** (residual: `tripwire3_recovered 0 < 2`). Promotion (`promotion.py`, rule and
anchors unchanged): eligible A, A2, A3; selected **A3** (accuracy tie with A2, higher
clarify precision); **NOT PROMOTED** (T_acc 0.80, T_clr_prec 0.90, tripwire 0 all unmet). D8
revision UNSPENT. Deviations from the prereg: none (pin held, one training run, recipe unchanged,
in-surface natural rows byte-stable, no prompt tightening needed).

## 6. What this establishes, and the next lever (user's call)

- **The P2.6b mechanism claim is falsified.** P2.6b's decision doc §4 attributed the tripwire
  regression to "everyday phrasing ⇒ emit a call". P2.6c tested exactly that: 124 casual
  out-of-surface abstain rows in train changed nothing on the three tripwire rows, and every
  checkpoint already abstains on casual floor-style requests. The real mechanism is **topical
  proximity to the surface**: requests that mention a surface object (sample/read, deck/plate,
  tips) while asking for an unsupported action (measure, show, order). The floor matrix has no
  out-of-surface cell of that shape, so nothing in train teaches "mentions tips ≠ pick up tips".
- **The probe was not discriminative and the prereg should have checked that.** A2 (and A)
  scoring 32/32 on the new probe class was knowable before submission by scoring the control on
  the regenerated probe locally on CPU (122 rows, minutes). Lesson filed.
- **Abstention data is cheap and safe**: +124 clarification rows moved the 228 by net zero flips
  and the in-surface probe by 0.844 → 0.811 (missing_slot 25 → 22 -- the `move_lid` hallucination
  pattern), recall 0.920 → 0.898 and precision 0.853 → 0.878. Nothing to promote, nothing lost.
- **Next candidate (new pre-registration, matrix change):** near-surface out-of-surface cells --
  requests naming a surface object but asking for an unsupported action (order/count/status
  queries on tips, "show/describe" the deck or a plate, concentration/measurement of a sample,
  "how much is left in well X"). That is a `MATRIX_VERSION` bump (new cells, ordinals appended
  after the existing 685 so record ids stay stable), teacher generation for the new cells only,
  assembly 0.1.6 with the pin unchanged (new rows train-only, eval-base natural variants
  n/a), predictions on `golden-out-surface-05/10/11` and the tripwire. Filed as backlog.
- **Jury items unchanged**: golden id grammar (underscore vs dotted); ambiguous-referent
  vague-span policy (4 golden rows). New jury item: the scorer counts an unknown-verb emission
  (`read_sample`) as a tripwire hit -- whether the runtime treats unknown-verb calls as
  abstentions is a policy decision that would mechanically fix `golden-out-surface-05`.
- The recipe sweep (promotion doc §6 item 3) is still untried; A3 ran 560 steps vs A2 496 and
  A 264 at the same recipe (confound recorded each time).

## 7. Cross-links

Prereg `.praxia/docs/preregistration/260903_p26c-oos-natural-prereg.md` (§6 outcome);
P2.6b decision `.praxia/docs/audits/260902_p26b-floor-surface-decision.md` (§4 diagnosis
superseded by §6 above); thresholds `.praxia/docs/specs/260825_p25_provisional_thresholds.md`
(status line 260903); gate doc `.praxia/docs/specs/260825_p25_slice_gate.md` §5 item 7.
Reports `training/eval/reports/260903_p26c_{A3,probe_A,probe_A2,probe_A3,predictions,promotion}.json`;
dumps `training/eval/outputs/260903_p26c_*`; train manifest `training/out/p26c/A/train_manifest.json`
(git `0de3da09`); commits `ca2fbc6a`..`89d1514f` on `coxswain-p2-pipeline`.
