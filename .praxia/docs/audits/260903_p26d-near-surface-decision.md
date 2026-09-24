---
title: 'P2.6d decision: near-surface out-of-surface matrix cells, arm A4 vs A3 on the frozen eval split'
description: 'Mechanical decision for task 260903_p26d_near_surface (backlog 4940): six near-surface out-of-surface cells appended to the matrix (v3), assembly 0.1.6 with the 228-row pin unchanged and a 24-row near-surface probe, arm A4 retrained once at recipe 0.1.0 and scored against arm A3 under the pre-registered P1-P5 checks and the unchanged promotion rule; includes the parallel eval-revision jury brief.'
status: decided-mechanically-260903; user call pending
verdict: NOT PROMOTED (selected A3 on the precision tie-break); P1 and P4 hold, P2 and P3 fail by one unit each; sidecar marginal
base_sha: d852f082
task_id: 260903_p26d_near_surface
date: '260903'
verdict: ''
base_sha: ''
---
# P2.6d decision: near-surface out-of-surface matrix cells, arm A4 vs A3 on the frozen eval split

Every number below comes from `p26d_report` (`training/eval/reports/260903_p26d_predictions.json`)
and `promotion.py` (`260903_p26d_promotion.json`) over the committed reports; the flip readings
come from the committed generation dumps. Nothing here re-scores or alters the rule.
Pre-registration: `.praxia/docs/preregistration/260903_p26d-near-surface-prereg.md`
(registered `c9ad28cc`, before any matrix change). Slurm 21926397, bathos run
`31f79868-821c-4f38-bc42-ebb535ce40d4` (outcome **marginal**), reproduces the P2.6c run.

## 1. What was built (all pre-registered)

- **Matrix v3** (`d413cada`): six near-surface out-of-surface cells appended
  (`tip_inventory`, `consumables_ordering`, `deck_display`, `sample_value_query`,
  `scheduling_logging`, `run_status`; verb null, 20 examples each). New cell field
  `appended_in_matrix_version`; `cells_round_robin` iterates appended cells after the original
  design, so the 685 existing record ids are unchanged (asserted against the committed corpus).
- **Rows** (`2cef646f`): 120/120 accepted with the unchanged base prompt (cache preserved;
  120 new entries), stamped `gemini-3.7-flash-medium`; supervision `nl_clarification`.
- **Assembly 0.1.6** (`fc52d75d`): 1523 rows; eval 228 = the pin (digests asserted); train 1295
  (+96); the last four examples of each new cell form the 24-row **near-surface probe**;
  natural probe 122 unchanged; cross-split duplicates 41 (ceiling); exclusions 12.
- **Pre-check before submission** (`d852f082`, lesson 485 applied): A3 and A2 scored locally on
  CPU on the near probe: 12/24 abstain, tripwire 12 -- the probe discriminates, P4 live.
- **One training run**: arm A recipe 0.1.0, seed 0, 600 optimizer steps (A3: 560), loss 0.673,
  checkpoint sha256 `41eec7bd…` (uncommitted, `outputs/p26d/A/checkpoint` locally + Engaging).

## 2. Results on the frozen 228-row split (fixed scorer)

| model | exact match | clarify recall | clarify precision | tripwire |
|---|---|---|---|---|
| baseline v2 | 0.197 [0.151, 0.254] (45/228) | 0.705 (62/88) | 0.564 (62/110) | 13 |
| A2 (P2.6b, 0.1.4) | 0.671 [0.608, 0.729] (153/228) | 0.920 (81/88) | 0.853 (81/95) | 3 |
| A3 (P2.6c, 0.1.5) = control | 0.671 [0.608, 0.729] (153/228) | 0.898 (79/88) | 0.878 (79/90) | 3 |
| **A4 (P2.6d, 0.1.6)** | 0.671 [0.608, 0.729] (153/228) | **0.966** (85/88) | 0.867 (85/98) | **1** |

| class | A3 | A4 | n |
|---|---|---|---|
| ambiguous_referent | 20 | 18 | 33 |
| clean_parse | 62 | 60 | 107 |
| missing_slot | 30 | 32 | 44 |
| out_of_surface | 41 | 43 | 44 |

Residual categories A4: param_content 57, name_mismatch 12, no_call 3, unknown_verb 2,
spurious_call 1. Golden misses 63 → **59**.

## 3. Pre-registered predictions

| prediction | value | needed | holds |
|---|---|---|---|
| P1 tripwire (primary) | tripwire 1; tripwire3 recovered 2/3 (`-05`, `-10`) | ≤ 1 and ≥ 2/3 | **holds** |
| P2 no regression vs A3 | acc 0.671 (≥ 0.671), recall 0.966 (≥ 0.705), hit→miss **6** | ≤ 5 | fails by one flip |
| P3 surface gains retained | surface6 **3/6** (A3 4/6), verb22 11/22, in-surface probe 0.833 | 4/6, 11/22, ≥ 0.80 | fails by one row |
| P4 near-surface probe (n = 24) | A3 0.500 → A4 **0.958** (delta +0.458; tripwire 12 → 1) | ≥ +0.10 | **holds** |
| P5 exploratory | ambig4 0/4; oos44 41 → 43; golden misses 63 → 59; natural oos probe 1.000 → 0.969 (one row) | -- | reported |

Sidecar: **marginal** (P1 holds, both P2 and P3 slip by exactly one unit, everything inside the
marginal bounds). Deviations from the prereg: none (pin held, one run, recipe unchanged, no seed
edited, no prompt edited).

## 4. The flips and the tripwire rows, read from the dumps

**Recovered (miss → hit, 6):** `golden-out-surface-05` "What's the concentration of sample 4?"
→ A3 `read_sample{at:[sample_4]}`, A4 *"I cannot look up or report sample concentrations. I can,
however, …"*; `golden-out-surface-10` "Show me the deck layout." → A3
`move_plate{destination: deck_layout_container_1}`, A4 *"I cannot view or display deck layouts…"*;
`golden-clean-move_plate-02` ("Place assay plate onto the shaker platform" → A3 `stamp`, A4 the
correct `move_plate`); `golden-missing-slot-03` (A3 hallucinated `the tip well`, A4 omits the
slot); `cov-0548/0549-move_lid__missing-slot` (A4 omits the missing `lid`).

**Still tripping (1):** `golden-out-surface-11` "Order more tips from the vendor website." → A3
`pick_up_tips{at:[the vendor website]}`, A4 `pick_up_tips{}`. The consumables cell's own probe
rows pass 4/4; the golden phrasing ("vendor website") is not covered by the seed's surface.

**Lost (hit → miss, 6):**
- `cov-0417-move_resource__missing-slot-12` "Move to scale_station_1." and
  `cov-0467-move_resource__none-12` "Move hotel_stack_1 to scale_station_1." → A4 emits
  `move_plate` instead of `move_resource`. These are the cross-cell label conflicts the P2.6b
  prereg already flagged ("Move to reservoir_1" appears in both cells with different gold).
- `cov-0607-move_lid__ambiguous-referent-12` "Move the lid to reservoir_1." → A4 omits `lid`.
  **The same utterance is gold for BOTH `move_lid{lid: "the lid"}` (ambiguous-referent) and
  `move_lid{}` with `lid` missing (`cov-0548/0549`).** A4 chose the missing-slot reading, gaining
  two rows and losing one: this flip is label noise inside the corpus, not learning.
- `cov-0172-transfer__ambiguous-referent-12` → A4 drops the well (`plate_2` for `plate_2.D9`):
  the one surface6 row lost.
- `ovl-c1b96d6ed1` → `tr20uL:95` for `tr20uL[95]` (bracket grammar); `ovl-f33ef17438` → A4
  emits an unknown verb named after the variable `diluent_volume_ul` (this row was already in the
  P2.6b verb22 list as a known oddity).

Net on the 228: zero. The near-surface probe: A4 misses one row of 24 (`sample_value_query-17`
"absorbance reading for well C4" → `read_absorbance{at:[C4]}`, a genuinely adjacent request).

## 5. Verdict

Sidecar: **marginal**. Promotion (`promotion.py`, rule and anchors unchanged): eligible A, A2,
A3, A4; selected **A3** (accuracy four-way tie; A3 wins the clarify-precision tie-break 0.878 vs
0.867); **NOT PROMOTED** (T_acc 0.80, T_clr_prec 0.90, tripwire 0 all unmet). D8 revision
UNSPENT.

## 6. What this establishes, and the next lever (user's call)

- **The P2.6c diagnosis is confirmed.** Cells with the tripwire rows' SHAPE (surface noun +
  unsupported action) transfer to golden phrasing: two of the three tripwire rows recovered, the
  228-split tripwire 3 → 1, the near-surface probe 0.50 → 0.96, clarify recall 0.898 → 0.966. Two
  paraphrase lanes (P2.6b/c, 677 rows) had moved these rows by nothing; 96 rows of the right
  shape moved them at once. Data shape beats data volume here.
- **Exact match is pinned at 153/228 by label noise, not capacity.** All four post-P2.6 arms score
  exactly 0.671; A4's six lost rows are dominated by cross-cell label conflicts (`move_lid`
  ambiguous-vs-missing on an identical utterance; `move_resource` vs `move_plate` on elided
  objects) and one bracket-grammar row. Those conflicts cap what any run of this corpus can reach
  and produce spurious flips on every retrain. **Recommended next lever: a label-conflict audit of
  the assembled corpus** (identical normalized utterance, different gold) with a deterministic
  resolution rule, before any recipe sweep -- a sweep on conflicting labels measures noise.
- **The eval-revision jury brief** (Track B, `research/260903_p2-6-eval-revision-jury-brief-…`)
  shows no candidate revision promotes anything: unknown-verb-as-abstention clears one row
  (`-05`, which A4 now clears on its own), article normalization moves zero rows, and exactly one
  golden miss is a pure id-grammar transform. Combined counterfactual for A2/A3: 0.680. The D8
  revision would buy 2 rows; it is not the lever.
- **The remaining tripwire row** (`-11`, "vendor website") is a seed-surface gap, not a shape gap;
  a second cell set is a new pre-registration and is not worth a sprint on its own.
- Recipe sweep still untried (A4 600 steps vs A3 560, A2 496, A 264 at the same recipe).

## 7. Cross-links

Prereg `.praxia/docs/preregistration/260903_p26d-near-surface-prereg.md` (§6 outcome);
P2.6c decision `.praxia/docs/audits/260903_p26c-oos-natural-decision.md`; jury brief
`.praxia/docs/research/260903_p2-6-eval-revision-jury-brief-unknown-verb-abstention-vague-span-policy-golden-id-grammar.md`;
thresholds `.praxia/docs/specs/260825_p25_provisional_thresholds.md` (status 260903 P2.6d);
gate `.praxia/docs/specs/260825_p25_slice_gate.md` §5 item 8; backlog 4940 (done).
