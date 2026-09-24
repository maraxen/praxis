---
title: 'P2.6 eval-revision jury brief: unknown-verb abstention, vague-span policy, golden id grammar'
description: Quantifies three candidate eval-revision policies (J1 unknown-verb-as-abstention, J2 ambiguous-referent vague-span comparison, J3 golden id grammar transform) against checkpoints A/A2/A3 on the frozen 228-row eval split; scorer untouched, revisions not applied.
status: draft
task_id: 260903_p26d_eval_revision_brief
date: '260903'
confidence: ''
sources: ''
---
# P2.6 eval-revision jury brief: unknown-verb abstention, vague-span policy, golden id grammar

Task `260903_p26d_eval_revision_brief`. Pure counterfactual quantification over the three frozen
generation dumps (checkpoints A/P2.6, A2/P2.6b, A3/P2.6c) on the pinned 228-row eval split, using
the FROZEN `baseline_eval` scorer as-is (imported, never edited). This brief measures three
jury-proposed eval-revision policies and their combination; it recommends nothing and applies
nothing. Every number below comes from
`python -m praxis_training.finetune.eval_revision_brief --out-json training/eval/reports/260903_eval_revision_brief.json`,
implemented in `training/src/praxis_training/finetune/eval_revision_brief.py`, tested in
`training/tests/test_eval_revision_brief.py` (18 tests, all passing).

## 1. What was measured, and how

Reuse discipline: the module never reimplements the exact-match rule for the "no revision" case --
`score_example_cf(raw, intent, policy)` calls the real `metrics.score_example` directly whenever
every policy flag is off (test `test_off_policy_delegates_to_real_score_example` asserts object
equality, not just numeric agreement). Aggregation (Wilson intervals, tripwire, per-class,
confusion) is likewise never duplicated: every counterfactual report is built by feeding freshly
scored `metrics.ScoredExample` rows through the real, frozen `metrics.build_report`.

**J1 -- unknown-verb emission as abstention.** Today, a generation whose emitted call(s) are ALL to
a verb outside the tool schema (e.g. `read_sample`) fails exact-match as a genuine wrong call and,
on an out-of-surface row, counts toward the AC-2.6.3 tripwire (raw parse count > 0). Counterfactual:
when `parse_function_calls` finds >=1 call and EVERY one fails `derive_call_gaps` (KeyError), treat
the row as an abstention (zero calls) for BOTH exact-match and the tripwire's own `n_calls_emitted`
field. A row with at least one VALID call alongside an unknown-verb one is untouched (J1 only fires
on "all unknown").

**J2 -- ambiguous-referent vague-span policy.** Ambiguous-referent gold rows carry exactly one
(rarely two) argument whose gold value is a natural-language span ("the plate", "there", "the tip
rack") rather than a groundable id; today's rule demands the literal string. Three policies, applied
ONLY to calls of gold rows with `ambiguity_class == "ambiguous_referent"`, and ONLY to the
arguments the GOLD record's own params derive as `SYMBOLIC_RESOURCE_REF` (via `derive_call_gaps`
on the gold params -- never guessed):
- (a) `literal` = today: exact string equality.
- (b) `normalized`: case-fold, strip ONE leading article (the/a/an), collapse internal whitespace,
  then compare (`_normalize_vague`).
- (c) `any_span`: accept any non-empty predicted string for that argument, regardless of content.
  Known over-generosity, reported not hidden: since EVERY `SYMBOLIC_RESOURCE_REF` argument of an
  ambiguous-referent call is marked unresolved by D11 (not only the vague one -- e.g. a call's
  concrete, already-grounded `source` can sit alongside its vague `destination`), policy (c) relaxes
  BOTH, not only the genuinely vague one.

**J3 -- golden id grammar.** Golden (hand-authored) rows write ids fully underscore-joined
(`source_plate_A1`, `tube_rack_B3`); floor/coverage rows use the dotted well grammar (`plate_1.D1`).
A "pure grammar transform" (`_dotted_form`) matches a trailing `_XN`/`.XN` well suffix (one letter +
1-2 digits) and normalizes it to a leading dot; two strings are a pure-transform pair iff both have
a dotted form and those forms are equal. Deliberately conservative: no lookup table, no guessing --
`plate_1` (missing well) and `plate["A1"]` (bracket syntax) both return "not a transform" rather than
a fabricated guess (verified in `test_j3_conservative_no_lookup_no_guess`).

**Diagnostic pass (J3 listing).** `diagnose_ref_only_row` runs a MAXIMALLY permissive snap (every
differing `SYMBOLIC_RESOURCE_REF` string pair, regardless of content) against a row that misses
today, to answer "would this row exact-match if every reference-string argument were considered
equivalent" -- i.e. isolates rows whose ONLY discrepancy is reference-string content, independent of
whether that content difference happens to be a pure transform. Of those, `_is_pure_transform_pair`
flags which pairs qualify for J3's actual counterfactual.

**Combined** = J1 + J2(b, normalized) + J3(pure-transform) together, checked against the unchanged
promotion thresholds (`T_acc=0.80`, `T_clr_recall=0.70`, `T_clr_prec=0.90`, tripwire `== 0`).

## 2. Per-item, per-checkpoint numbers

All accuracy/recall/precision cells are `value (successes/n)`; tripwire is a raw count.

### Today (no revision)

| checkpoint | exact match | clarify recall | clarify precision | tripwire |
|---|---|---|---|---|
| A  | 0.636 (145/228) | 0.864 (76/88) | 0.835 (76/91) | 1 |
| A2 | 0.671 (153/228) | 0.920 (81/88) | 0.853 (81/95) | 3 |
| A3 | 0.671 (153/228) | 0.898 (79/88) | 0.878 (79/90) | 3 |

### J1 (unknown-verb-as-abstention)

| checkpoint | exact match | clarify recall | clarify precision | tripwire | flips (exact-match) | golden-out-surface-05 clears? |
|---|---|---|---|---|---|---|
| A  | 0.636 (145/228) | 0.864 (76/88) | 0.826 (76/92) | 1 | none | True (already an abstention today -- A never emits `read_sample`) |
| A2 | 0.675 (154/228) | 0.932 (82/88) | 0.845 (82/97) | 2 | `golden-out-surface-05` miss->hit | **True** |
| A3 | 0.675 (154/228) | 0.909 (80/88) | 0.870 (80/92) | 2 | `golden-out-surface-05` miss->hit | **True** |

Only `golden-out-surface-05` clears the tripwire under J1, for A2 and A3 (checkpoint A already
abstains on it in plain English, no function-call span at all). The other two TRIPWIRE3 rows
(`golden-out-surface-10`, `-11`) emit VALID-verb hallucinated calls (`move_plate`, `pick_up_tips`)
-- J1 cannot touch them; tripwire drops from 3 to 2 for A2/A3, never to 0.

Side effect worth flagging (see also §5): checkpoint A's clarify precision drops slightly
(0.835 -> 0.826, successes unchanged 76 but n grows 91->92) purely from J1 -- the unknown-verb row
`ovl-f33ef17438` is NOT out-of-surface, so treating it as an abstention creates a NEW clarify false
positive there. A2/A3's precision actually rises (one true clarify recovered on
`golden-out-surface-05` outweighs one new false positive elsewhere, e.g. `golden-clean-move_lid-04`).

### J2 (ambiguous-referent vague span; n=33 ambiguous-referent rows)

| checkpoint | (a) literal | (b) normalized | (c) any-span | total acc (a) | total acc (b) | total acc (c) |
|---|---|---|---|---|---|---|
| A  | 18/33 | 18/33 | 30/33 | 0.636 (145/228) | 0.636 (145/228) | 0.689 (157/228) |
| A2 | 19/33 | 19/33 | 27/33 | 0.671 (153/228) | 0.671 (153/228) | 0.706 (161/228) |
| A3 | 20/33 | 20/33 | 28/33 | 0.671 (153/228) | 0.671 (153/228) | 0.706 (161/228) |

**Policy (b) normalized moves ZERO rows on any checkpoint.** Every ambiguous-referent mismatch found
in the dumps is a genuine content/semantic difference (e.g. gold `"that plate"` vs predicted
`"the plate"`, gold `"it"` vs predicted `"the plate"`), never a pure casing/article/whitespace
artifact. Policy (c) any-span moves 8-12 rows per checkpoint (full list in §3) -- it is
substantially more permissive because, per the known over-generosity noted in §1, it also validates
the CONCRETE half of two-slot-argument calls (e.g. `cov-0172...`'s already-correct dotted `source`
gets re-validated alongside the genuinely vague `destination`... in this corpus that concrete half
happens to already be wrong too in some rows, e.g. `plate_2 D9` vs gold `plate_2.D9`, so (c) is
doing real work there, not just accepting a no-op).

### J3 (golden id grammar; golden rows only)

| checkpoint | golden rows failing ONLY on a ref-string mismatch | of those, pure-transform | counterfactual accuracy if pure-transform pairs count as hits |
|---|---|---|---|
| A  | 24 | 0 | 0.636 (145/228, unchanged) |
| A2 | 30 | 1 (`golden-clean-aspirate-04`) | 0.675 (154/228) |
| A3 | 30 | 1 (`golden-clean-aspirate-04`) | 0.675 (154/228) |

Across all 3 checkpoints and ~84 golden reference-string mismatches surveyed, exactly ONE pair is a
pure grammar transform: `golden-clean-aspirate-04`, gold `tube_rack_B3` vs predicted `tube_rack.B3`
(A2/A3 only; A fails that row for a different reason and isn't in the ref-only set). Every other
mismatch mined (examples: `plate_1.G6` -> `plate_1` (truncation, not a transform), `plate_A_H12` ->
`plate["A"]["H12"]` (bracket hallucination), `destination_plate_A1` -> `plate_A1` (dropped prefix
word)) is a genuine content error the conservative regex correctly refuses to paper over.

## 3. Moved rows (pairs)

**J1 exact-match flips**: `golden-out-surface-05` only, A2 and A3 (miss -> hit). No hit -> miss flips
on any checkpoint under any single policy or the combination (verified: `_flips` reports both
directions, none observed in the miss-to-hit direction... i.e. no regressions).

**J2(b) normalized**: no rows move on any checkpoint (empty list, all three).

**J2(c) any-span** (record_id: `[{arg_name, gold_reference, predicted_reference}, ...]`):

- **A** (12 rows): `cov-0172-transfer__ambiguous-referent-12` source `plate_2.D9`/`plate_2 D9`;
  `cov-0173-transfer__ambiguous-referent-13` source `plate_1.A1`/`plate_1["A1"]`;
  `cov-0174-transfer__ambiguous-referent-14` source `plate_2.C3`/`plate_2 C3`;
  `cov-0367-drop_tips__ambiguous-referent-12` destination `the tip rack`/`the box`;
  `cov-0369-drop_tips__ambiguous-referent-14` destination `the tip rack`/`the rack`;
  `cov-0609-move_lid__ambiguous-referent-14` lid `the lid`/`plate.lid`;
  `golden-ambig-ref-03` plate `that plate`/`the plate`;
  `golden-ambig-ref-06` destination `where they came from`/`the tip spot`;
  `golden-ambig-ref-07` source `it`/`the plate`;
  `golden-ambig-ref-08` destination `wherever it belongs`/`the deck`;
  `golden-ambig-ref-09` destination `the plate we just talked about`/`the plate`;
  `golden-ambig-ref-10` destination `the other plate`/`the_other_plate_well` AND source
  `column 2`/`column_2["column_2"]`.
- **A2** (8 rows): `cov-0173-...-13` source `plate_1.A1`/`plate_1["A1"]`;
  `cov-0609-move_lid-14` lid `the lid`/`the plate lid`;
  `golden-ambig-ref-02` destination `there`/`the well`;
  `golden-ambig-ref-03` destination `the reader station`/`reader_station_1` AND plate
  `that plate`/`the plate`;
  `golden-ambig-ref-07` destination `the matching plate`/`the same well as the plate` AND source
  `it`/`the same well as the plate`;
  `golden-ambig-ref-09` destination `the plate we just talked about`/`the plate`;
  `golden-ambig-ref-10` destination `the other plate`/`the_other_plate.columns[2]` AND source
  `column 2`/`column_2`;
  `golden-ambig-ref-12` destination `storage`/`storage_well`.
- **A3** (8 rows): same record_ids as A2 with near-identical pairs (`cov-0609` lid
  `the lid`/`plate_lid`; `golden-ambig-ref-10` destination `the other plate`/`the_other_plate_column_2`,
  source `column 2`/`column_2`; the rest byte-identical to A2's list).

**J3 pure-transform**: `golden-clean-aspirate-04`, arg `source`, gold `tube_rack_B3` vs predicted
`tube_rack.B3` -- A2 and A3 only.

## 4. Combined counterfactual (J1 + J2(b) + J3) vs promotion thresholds

Thresholds unchanged: `T_acc >= 0.80`, `T_clr_prec >= 0.90`, `T_clr_recall >= 0.70`, tripwire `== 0`.

| checkpoint | exact match | clarify recall | clarify precision | tripwire | would promote? |
|---|---|---|---|---|---|
| A  | 0.636 (145/228) | 0.864 (76/88) | 0.826 (76/92) | 1 | **no** |
| A2 | 0.680 (155/228) | 0.932 (82/88) | 0.845 (82/97) | 2 | **no** |
| A3 | 0.680 (155/228) | 0.909 (80/88) | 0.870 (80/92) | 2 | **no** |

Since J2(b) contributes zero flips on any checkpoint, the combined delta over "today" is exactly the
sum of J1's one flip (`golden-out-surface-05`, A2/A3 only) and J3's one flip
(`golden-clean-aspirate-04`, A2/A3 only): +2 successes for A2/A3, +0 for A. **No checkpoint would
promote under this combined counterfactual.** Accuracy remains far below the 0.80 floor (0.636-0.680
vs 0.80 needed) and tripwire never reaches 0 (drops from 3 to 2 for A2/A3, since only 1 of the 3
TRIPWIRE3 rows is an unknown-verb emission -- the other two are valid-verb hallucinations no eval
revision here touches). The gap is structural, not measurement noise: even the MOST permissive
single policy surveyed (J2 any-span, +12/+8/+8 rows) does not close it, and stacking three policies
together moves only 2 rows for A2/A3 because two of the three (J1, J3) are individually narrow
(one qualifying row each) and the third (J2b) found nothing to move.

## 5. Caveats

- **Single seed, frozen dumps, no re-generation.** Every number here is a re-score of the SAME
  recorded generations already committed for P2.6/P2.6b/P2.6c; nothing here reflects a different
  training run, seed, or recipe.
- **Scorer untouched.** `baseline_eval/metrics.py`, `intent_record.py`, `slot_derivation.py`,
  `tool_schema.py`, and `fgml_parser.py` were read and imported, never edited. This brief's own
  policy logic (`_snap_predicted`, `_normalize_vague`, `_dotted_form`) is new code living entirely in
  `training/src/praxis_training/finetune/eval_revision_brief.py`; it is exercised, never applied, by
  the frozen scorer.
- **J2(c) any-span is a known over-generous policy**, not a recommendation: it relaxes comparison on
  EVERY `SYMBOLIC_RESOURCE_REF` argument of an ambiguous-referent call (concrete grounded ones
  included), not only the genuinely vague span. Reported exactly as measured; not narrowed to "only
  the vague one" because that would require guessing which argument is "the vague one" without a
  spec-level definition -- out of scope for a QUANTIFY-only brief.
- **J1's tripwire relief is partial by construction**: only unknown-VERB emissions are affected;
  valid-verb hallucinations on out-of-surface rows (2 of 3 TRIPWIRE3 rows, both A2/A3) are entirely
  unaffected by any policy quantified here.
- **J3's pure-transform yield is tiny (n=1 across 3 checkpoints)** despite surveying ~84 golden
  reference mismatches; the underscore/dot delimiter swap this jury item worried about is real but
  rare in what the model actually emits -- most golden mismatches are genuine content errors
  (paraphrase, wrong prefix, hallucinated bracket syntax), not grammar-only.
- **No policy is recommended.** This document only quantifies; the decision (if any) is the user's,
  as directed by the task brief.

