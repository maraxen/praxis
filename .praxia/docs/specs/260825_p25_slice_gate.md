---
title: 'Coxswain P2.5 slice gate: GO/NO-GO for P2.6 fine-tune spend'
description: "Blocking gate doc (backlog 480), rev 260901: full-scale corpus (812 rows) + live baseline on the whole 228-row eval split; verdict CONDITIONAL GO for P2.6 spend under three recipe/measurement conditions."
task_id: 260825_copilot_pipeline_spec
date: '260825'
status: ready-for-jury
backlog_item: 480
---

# P2.5 slice gate — baseline vs coverage plan vs class balance

Spec: `.praxia/docs/specs/260825_coxswain-phase-2-functiongemma-copilot-p.md`
rev2 §5 P2.5 / §7 AC-2.5.x. This doc gates P2.6 (fine-tune) spend; the
orchestrator runs a blocking jury on it.

## RECOMMENDATION (rev 260901): **CONDITIONAL GO — spend P2.6 on this corpus, under three conditions**

Every deficit the 0826 revision cited is closed: the assembled corpus is 812
rows (was 188), the reference baseline is live inference over the full
228-row eval split (was a golden-only n=62 point, itself preceded by an n=8
mechanics proof), and train-side negatives are 131/90/128 per clarify class
(was 1/5/9). The real baseline says the fine-tune is needed (T_acc 0.162
against a 0.80 anchor) and that clarify recall is already AT the 0.70 anchor
(0.705, CI [0.60, 0.79]) while precision is not (0.564 vs 0.90) -- so the
lift P2.6 must produce is on accuracy and on not over-abstaining, not on
abstaining more.

Conditions the jury should attach (all are P2.6 recipe/measurement choices,
none needs more data):

1. **Set the negative-mixing ratio explicitly.** Train is 60% clarify-class
   negatives (§4.1). Subsample or down-weight to the ratio D5 names; do not
   train on the raw split.
2. **Measure every P2.6 delta against `260901_baseline_real_v2.json` on the
   same 228-row eval split**, never against the 0827 golden-only point. Treat
   T_clr_recall as must-not-regress and T_acc / T_clr_prec as the targets.
3. **Decide train-side dedup** (86 exact duplicates, §2) in the recipe, and
   accept `ambiguous_referent` eval at 33 as a known, tracked gap -- it is not
   statically scored at P2.6 (§4.3), so it does not gate this spend.

If the jury instead wants all three clarify classes at >= 40 eval AND the
60 wasted floor rows recovered before any spend, the NO-GO path is one
cheap sprint: make `floor_gen.synth` respect the scalar surface, bump
GENERATOR_VERSION (~685 teacher rows re-fetched), regenerate, re-run this
gate. That buys ~+60 rows and a clean ambiguous_referent slice; it does not
change what the baseline says the model needs.

## 1. What landed as inputs (all jury-cleared at Gate 1)

| Branch | Artifact | Rows |
|---|---|---|
| P2.1 golden | `training/golden/golden_pairs.jsonl` (+ sidecar) | 88 |
| P2.3 coverage floor | `training/out/corpus_p23_floor.jsonl` (matrix v2, 43 cells x 15/20) | 685 |
| P2.4 naturalness overlay | `training/overlay_gen/out/overlay_full.jsonl` (all sources, 37 canonicals x3) | 111 |
| P2.2 verify harness | execution-verification substrate behind synthetic labels | (code, no rows) |

**Revision 260901 (task `260901_p25_gate_close`).** The 0826 revision of this
doc was measured on the SMOKE outputs (30 + 92 rows): the assembler's input
constants still pointed at `corpus_p23_smoke.jsonl` / `overlay_smoke.jsonl`,
so the full-scale pass this doc's own §5 asked for was never assembled. Both
generators have since run at full scale (floor 0 rejections; overlay 0
execution rejections after the tip-arming fix), the matrix was raised from 3
to 15 examples per cell (20 for the 8 out-of-surface cells) so the split rule
yields eval support per clarify class, and the assembler now reads the
full-scale files. Every number below is from the regenerated
`training/assemble/out/manifest.json` (assembly_version 0.1.2).

Assembly (`training/assemble/`): ONE FunctionGemma-native JSONL, every row
`{metadata, tools[], messages[]}`, developer turn byte-matching the committed
scaffold template (no date injection, D6-rev2). PLR_SOURCE_SHA
`dd79c4c89bc008629a1c598ea614be5e6067d1f9` (= submodule HEAD, = golden
manifest pin).

## 2. Assembled corpus (after the assembly validation gate)

72 input records were excluded whole (77 reason entries; a record with two
bad calls is one exclusion), loudly counted in the manifest:

- 62 entries are a multi-value argument on a param the shipped surface
  declares SCALAR (`aspirate.volume_ul [10,75]`, `transfer.destination
  [p1,p2]`): 50 from the floor, 12 from the overlay. These are the
  parallel/multi-channel calls the 13-tool grammar cannot express; the
  scalar surface was re-affirmed as a deliberate P2.1 decision on 260901
  (declaring arrays would teach the model to emit lists the utterances never
  contain). Keeping them would train schema violations.
- 15 entries are the ENTIRE `pick_up_tips__ambiguous-referent` floor cell:
  `pick_up_tips.at` is declared ARRAY but the synthesizer emits it non-list
  for the ambiguous-referent case. This is a floor_gen synth-vs-surface
  mismatch, not a data defect; fixing it needs a GENERATOR_VERSION bump
  (full cache invalidation) and is left for the jury (§5).

Padding is forbidden by the task line.

| Split | clean_parse | missing_slot | ambiguous_referent | out_of_surface | total |
|---|---|---|---|---|---|
| eval | 107 | 44 | 33 | 44 | 228 |
| train | 235 | 131 | 90 | 128 | 584 |
| total | 342 | 175 | 123 | 172 | **812** |

Provenance: golden 88 (ALL eval, per task AC -- human-authored instruments
never train on), coverage 625 kept / 60 excluded, naturalness 99 kept / 12
excluded. Eval clarify total = 121 >= D8's 30 floor, spanning all three
classes. Splits are disjoint by construction; stratification is provenance x
class x verb (rule recorded in the manifest): 42 coverage strata contribute
122 eval rows, 5 naturalness strata contribute 18.

**Duplicates (measured, not dropped):** `counts.duplicate_utterances_normalized
= 86` exact normalized-utterance collisions across the whole corpus. On the
eval side they are few (per class distinct/rows: clean_parse 106/107,
missing_slot 41/44, ambiguous_referent 32/33, out_of_surface 44/44); on the
train side they concentrate in cells whose slot space is tiny (train
distinct/rows: 227/235, 102/131, 69/90, 121/128; worst cells
`move_lid__missing-slot` 12, `discard_tips__ambiguous-referent` 10,
`move_resource__missing-slot` 8). Whether P2.6 should dedup train is a jury
question (§5); the eval numbers above are effectively distinct.

**Shortfall: 188 examples below the 1000 target** (was 812 below at smoke
scale). The remaining gap is bounded by matrix size x examples_per_cell and
by the 37 unique mined overlay canonicals, not by a pending run.

## 3. Baseline failure distribution (what a fine-tune must fix)

Source: `training/eval/reports/260901_baseline_real_v2.json` -- mode
local_inference, LIVE LOCAL INFERENCE, `google/functiongemma-270m-it@39eccb09`,
greedy decode, CPU, **n=228 = the whole assembled eval split** (every class,
every provenance). This REPLACES `260827_baseline_real.json` (n=62, golden
rows only) as the reference point; the two are not comparable row-for-row
and the anchors in the thresholds doc are unchanged (D8).

| Metric | v2 (n=228) | Wilson 95% | 0827 golden-only (n=62) | anchor |
|---|---|---|---|---|
| `T_acc` exact-match | 0.162 (37/228) | [0.120, 0.216] | 0.210 | 0.80 |
| `T_clr_recall` | 0.705 (62/88) | [0.602, 0.790] | 0.833 | 0.70 |
| `T_clr_prec` | 0.564 (62/110) | [0.470, 0.653] | 0.556 | 0.90 |

Clarify confusion (statically scoreable classes only, §4.3): TP 62, FN 26,
FP 48, TN 92.

Per class (exact-match successes / n; clarify predicted / expected), with
the failure reasons the scorer recorded (`exact_match_failures[].reasons`):

| class | n | exact | clarify pred/exp | dominant failure reasons |
|---|---|---|---|---|
| clean_parse | 107 | 6 / 107 | 34 / 0 | 47 slot/reference derivation mismatch on an emitted call; 18 empty completion; 8 over-generation (2 calls for 1); 7 `drop_tips`/`discard_tips` name confusion; 7 missing wavelength params |
| missing_slot | 44 | 0 / 44 | 28 / 44 | 24 empty completion (abstains by silence); 10 hallucinated the missing param (`missing_required` derived empty); 12 slot derivation mismatch; 3 params mismatch |
| out_of_surface | 44 | 31 / 44 | 34 / 44 | 13 fabricated a call (1-3 calls where 0 intended); was 12/12 on golden -- synthetic off-surface asks are harder |
| ambiguous_referent | 33 | 0 / 33 | 14 / 0 | 18 slot derivation mismatch; 14 empty completion; 4 name confusion; 6 params mismatch (not statically scored) |

Read: the golden-only baseline overstated the base model on both clarify
axes. At scale the failure anatomy is (a) reference/slot derivation on
clean positives -- the model picks the verb and emits a call, but the
referent it names does not derive to the intended slot (47/107), (b)
missing-slot hallucination-without-abstention (10/44 fill in the param the
utterance never stated), and (c) empty completions on clean positives
(18/107) plus 13/44 fabricated calls on off-surface asks. (b) and (c) pull
recall and precision in opposite directions, which is why the recipe must
target precision without buying it by abstaining less. All three are
trainable behaviors and the corpus now carries train-side support for each
(§4.2).

## 4. Adequacy analysis

### 4.1 Coverage plan vs corpus

- Train side holds 584 rows: 235 positive (clean_parse) / 349 negative
  (clarify classes) = **60% negative**, up from 17% at smoke scale. D7's
  "controlled ratio" now cuts the other way: the negatives are no longer
  thin, they dominate. P2.6's recipe (D5) must set the mixing ratio
  explicitly (subsample negatives or upweight positives) rather than train
  on the raw split; this is a training-recipe knob, not a data deficit.
- Verb coverage: 20 distinct verbs across 812 rows; every one of the 13
  included verbs appears in both splits via golden. Synthetic diversity per
  verb is now full-scale (largest naturalness stratum n=36, `pick_up_tips`;
  coverage strata n=15/20 per cell before exclusion), with the duplicate
  caveat in §2.
- The 43-cell matrix at v2 supports 685 floor rows per sweep; 625 survived
  assembly. The 60 lost rows are all in three aspirate/dispense/transfer
  multi-value cells and the one broken pick_up_tips cell (§2) -- i.e. the
  generator spends teacher calls on calls the surface then rejects. Making
  `floor_gen.synth` respect the scalar surface would recover them at the
  cost of a GENERATOR_VERSION bump (every cached row re-fetched, ~685
  teacher rows).

### 4.2 Ambiguity-class balance

Eval side: missing_slot 44 and out_of_surface 44 clear the ~40 target set
in §5; **ambiguous_referent is 33** -- short by 7, entirely because 39 of
its 150 floor rows were excluded (§2: the whole pick_up_tips cell plus 24
multi-value aspirate/dispense rows), which also pushed those two strata
below the n>=4 eval threshold. Note ambiguous_referent is NOT statically
scoreable in this harness (§4.3); its eval support matters at P2.9, not for
the T_clr metrics this gate reads.

Train side is balanced across clarify classes: missing_slot 131,
out_of_surface 128, ambiguous_referent 90 -- against 1 / 9 / 5 at smoke
scale. A model trained now sees substantial missing-slot-negative gradient,
which was the single worst-supported behavior in the 0826 revision.

### 4.3 Measurement caveats the jury should hold

- **Reference point moved (260901).** `260901_baseline_real_v2.json` (n=228,
  the full assembled eval split) replaces the 0827 golden-only point
  (n=62). Do not read the recall drop 0.833 -> 0.705 as regression: the
  model did not change, the eval did. The anchors in
  `260825_p25_provisional_thresholds.md` are provisional policy margins and
  remain unchanged per D8's one-revision-at-P2.6 rule; they are now checked
  against a split-representative baseline instead of the golden subset.
- Static clarify scoring covers out_of_surface + missing_slot only (88 eval
  items = the recall denominator); ambiguous_referent verifies at P2.9 with
  live grounding (F1-rev2/C-M1). Its 33 eval rows therefore do not enter
  T_clr_* at this gate.
- Wall clock for the baseline lane: ~18 min on CPU for 228 rows (270M,
  greedy, 128 new tokens). Re-running after P2.6 is cheap.

## 5. What flips this to GO — status at rev 260901

1. **DONE 260901.** Full-scale generation assembled: `floor_gen` at matrix
   v2 (43 cells x 15/20 = 685 rows, 0 rejections, Gemini 3.7 Flash via
   `agy`, batched) + `overlay_gen --full` (111 rows, 0 execution
   rejections). Re-assembled: **812 rows** against the ">= ~800" line;
   missing_slot train mass **131** against ">= ~30"; eval clarify
   **44 / 33 / 44** against ">= ~40 each" -- two of three clear, the third
   (ambiguous_referent, not statically scored) is short by 7 for the reason
   in §2. The assembler had been reading the smoke files until this
   revision; that is fixed and pinned by the drift-alarm test.
2. **DONE 260901.** Real baseline re-measured on the assembled eval split
   (§3). Supersedes the 0827 golden-only point as the P2.6 reference.
3. **DONE -- this revision.** Gate re-run with fresh numbers; verdict at the
   top.
4. **P2.6 RUN 260901 (jury said GO).** Three-arm negative-mixing ablation
   on Engaging, promotion rule applied mechanically: all arms eligible and
   `marginal`, A selected, **NOT PROMOTED**; D8 revision unspent (user
   decision 260901); next: scorer fixes + re-score under a prereg amendment. Two scorer artifacts and one gold-set defect account for 54
   of A's 140 misses. Decision doc:
   `.praxia/docs/audits/260901_p26-promotion.md`.
5. **260902 -- re-scored under a prereg amendment** (task `260902_p26_rescore`,
   backlog 4861): parser list decoding, order-insensitive slot comparison and
   assembler-derived gold gap fields (assembly 0.1.3; sidecar re-annotated,
   pairs file and eval rows unchanged); generations frozen, prediction held on
   every model. A 0.636 / 0.864 / 0.835 / tripwire 1 -> still NOT PROMOTED,
   D8 unspent. Decision doc §8; the eval-split annotation defect this gate's
   condition 2 relied on is closed by `test_assembly_gap_fields.py`.
6. **260902 -- P2.6b floor_gen data fix** (task `260902_p26b_surface_data`,
   backlog 4890): the open item below ("floor_gen.synth scalar-surface
   compliance") is CLOSED -- synth 0.2.1 repairs the 60 rows (incl. the whole
   `pick_up_tips__ambiguous-referent` cell) with the RNG seed frozen, so the
   228-row eval split is pinned and unchanged (assembly 0.1.4). A natural-
   phrasing lane added 429 train rows + a 90-row probe set. Arm A retrained
   once: 0.671 / 0.920 / 0.853 / tripwire 3, NOT PROMOTED; the natural
   surface transfers (probe +0.61, 4/6 pre-registered rows) but the lane
   needs an out-of-surface counterpart (tripwire 1 -> 3). Decision doc
   `.praxia/docs/audits/260902_p26b-floor-surface-decision.md`.

7. **260903 -- P2.6c out-of-surface natural lane** (task `260903_p26c_oos_natural`,
   backlog 4933): natural variants of the 160 out-of-surface floor rows (158
   accepted, base clarification copied) -> assembly 0.1.5 (train 1199, probe
   122 with 32 out_of_surface; pin unchanged). Arm A3: 0.671 / 0.898 / 0.878 /
   tripwire 3, NOT PROMOTED. P2.6b's "casual phrasing => emit a call" reading
   is falsified: the three tripwire rows are near-surface topical confusions
   (sample -> read_*, deck -> move_plate, tips -> pick_up_tips) and every
   checkpoint already abstains 32/32 on casual floor-style requests. Next
   candidate: near-surface out-of-surface matrix cells (new prereg). Also
   fixed: the natural corpus provenance stamp (all rows said fake-teacher@test).
   Decision doc `.praxia/docs/audits/260903_p26c-oos-natural-decision.md`.
8. **260903 -- P2.6d near-surface out-of-surface matrix cells** (task
   `260903_p26d_near_surface`, backlog 4940): six cells appended to the matrix
   (v3, record ids unchanged), 120 rows, assembly 0.1.6 (train 1295, 24-row
   near-surface probe; pin unchanged). Arm A4: 0.671 / 0.966 / 0.867 /
   tripwire 1, NOT PROMOTED (sidecar marginal: P1 and P4 hold, P2 and P3 slip
   by one unit each). golden-out-surface-05 and -10 recovered; the near probe
   went 0.50 -> 0.96; the six lost rows are cross-cell label conflicts
   (move_lid ambiguous-vs-missing on an identical utterance, move_resource vs
   move_plate). Next candidate: a label-conflict audit of the assembled corpus.
   Jury brief on the eval-revision items filed alongside (no revision promotes).
   Decision doc `.praxia/docs/audits/260903_p26d-near-surface-decision.md`.

**Open for the jury (not blockers, recorded so they are decided rather than
defaulted):**

- Negative-mixing ratio for P2.6 (train is 60% negatives).
- Train-side exact-duplicate handling (86 rows).
- ~~Whether to spend one more sprint on `floor_gen.synth` scalar-surface
  compliance (recovers ~60 rows incl. the whole
  `pick_up_tips__ambiguous-referent` cell; needs GENERATOR_VERSION bump).~~
  **Done 260902 (§5 item 6)** -- without a seed bump: the rows are train-only
  until an eval revision re-cuts the split.
- Increments 2-4 of the corpus-ingestion strategy remain declined under G1's
  STOP (user decision 260901); this gate does not depend on them.

## 6. Deliverable cross-links

- Corpus + sidecar + manifest: `training/assemble/out/` (manifest records
  versions, provenance counts, exclusions, shortfall, split rule).
- Scaffold template: `training/assemble/developer_scaffold_template.txt`.
- Thresholds (PROVISIONAL per D8):
  `.praxia/docs/specs/260825_p25_provisional_thresholds.md`.
- Storage ledger updated (C-m8): see footprint doc §6 — assembly adds ~1.24 MB
  tracked repo bytes, ZERO staged-dist bytes (trainer input, never served).
