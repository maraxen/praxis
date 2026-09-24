---
title: 'P2.6 re-score amendment: fixed scorer + re-derived gold gap fields on the same generations'
description: 'Pre-registration amendment (backlog 4861) to the P2.6 prereg: three scoring defects are fixed (parser nested-list decoding, order-insensitive unresolved_slots comparison, assembler-derived gold gap fields) and the SAME three checkpoints plus baseline v2 are re-scored from saved generations with a row-level prediction registered before any scorer change; promotion rule and D8 anchors unchanged.'
status: registered-8fe1b111; held-260902
task_id: 260902_p26_rescore
date: '260902'
---
# P2.6 re-score amendment: fixed scorer + re-derived gold gap fields on the same generations


Amends `.praxia/docs/preregistration/260901_p26-finetune-prereg.md` (task
`260901_p26_finetune`, backlog 4848) for task `260902_p26_rescore` (backlog 4861).
Registered BEFORE any scorer or gold-data change (commit order is the proof); the
sidecar is `scripts/experiments/p26_rescore.bth.toml` (`bth validate-sidecar` ok).
Decision it follows: promotion doc `.praxia/docs/audits/260901_p26-promotion.md` §0 and
§6 item 1 (user, 2026-09-01) -- fix the measurement, re-score the same checkpoints, no
retraining, D8 revision unspent.

## 1. What changes, what does not

| Item | Status |
|---|---|
| Checkpoints | UNCHANGED. `outputs/p26/{A,B,C}/checkpoint`, sha256 `376cac6e…` / `792f7d5c…` / `f00876d0…` (full in `training/out/p26/<arm>/train_manifest.json`); remote copies verified byte-identical (`model.safetensors` sha256 equal on Engaging and locally, 260902). |
| Base model | UNCHANGED. `google/functiongemma-270m-it@39eccb091651513a5dfb56892d3714c1b5b8276c`. |
| Eval split | UNCHANGED. The same 228 rows (`metadata == "eval"` in `training/assemble/out/corpus_p25.jsonl`, sha256 `3ce238b8…`, byte-identical before and after). |
| Model generations | FROZEN. Every model's raw output over the 228 rows is saved as a `praxis-recorded-model-outputs` artifact (`training/eval/outputs/260902_p26_dump_<model>.json`) and the re-score runs in `--recorded` mode -- no inference is repeated after this amendment. |
| Promotion rule | UNCHANGED (prereg §3): eligible iff recall >= 0.705; selected = max accuracy (tie: precision, earlier letter); promoted iff acc >= 0.80 AND prec >= 0.90 AND recall >= 0.70 AND tripwire == 0. `finetune/promotion.py` untouched. |
| D8 anchors | UNCHANGED, revision UNSPENT (user decision 260901). |
| Scorer | FIXED (three defects, §2). |
| Gold sidecar | RE-DERIVED gap fields only (§2 item 3); `corpus_p25_sidecar.jsonl` sha256 `fb18d8d0…` -> new value recorded in the decision addendum; no utterance, params, class, split, or record_id changes (checked mechanically, §4). |

## 2. The three defects (found 260901-02, all in code, none in the model)

1. **Parser has no nested-value decoding.** `baseline_eval/fgml_parser.py:_strip_escapes`
   unwraps only a whole-escaped scalar; the chat template's `format_argument` macro serialises
   a list as `[<escape>a<escape>,<escape>b<escape>]` and a mapping as `{k:v}`, so a list
   argument comes back as ONE STRING and fails raw dict equality against the gold list.
   Fix: recursive value decoder mirroring the macro (lists, mappings; leaves through the
   existing scalar path). Booleans and the escaped-numeric coercion (`<escape>007<escape>` -> 7)
   are explicitly OUT of scope (debt item) so the fix cannot touch anything but list/map rows.
2. **Slot comparison is positional.** `coxswain/src/coxswain/plr/intent_record.py:check_intent_agreement`
   compares the derived `unresolved_slots` tuple to the gold tuple with `!=`. Derived order =
   the predicted key order (template `dictsort`: alphabetical); gold order = authored order.
   Fix: compare both sides after a STABLE sort by `arg_name` (order across args irrelevant,
   order within one list-valued arg preserved).
3. **Assembler drops golden gap annotations.** `training/assemble/build.py:load_golden` emits
   calls as `{name, params}` only (annotation parked under `lineage.gap_fields`); the
   assembled sidecar therefore has 70 eval rows with an empty `unresolved_slots` where
   `derive_call_gaps` yields slots (52 golden, 18 naturalness-overlay rows never annotated),
   12 golden rows lacking `missing_required`, and 32 rows whose annotation order disagrees with
   the sorted-key params the assembler itself writes. Zero content disagreements.
   Fix: the assembler derives both gap fields from the params it writes for EVERY call
   (`ASSEMBLY_VERSION` 0.1.2 -> 0.1.3), asserts multiset equality against any source
   annotation, and a new test pins the invariant on the assembled sidecar.

## 3. Reproduction control (done BEFORE this amendment, commit `d82d4404`)

The OLD scorer over the fresh dumps reproduces the committed 260901 reports exactly:

| model | venue of dump | committed | old scorer on dump | failed-row sets | clarify + tripwire |
|---|---|---|---|---|---|
| baseline v2 | local CPU, default dtype (same as 260901) | 37/228 | 37/228 | identical | identical (tripwire field appears: 13) |
| A | Engaging L40S, cuda/bf16 (same as 260901; Slurm 21810821) | 88/228 | 88/228 | identical | identical (tripwire 1) |
| B | same job | 85/228 | 85/228 | identical | identical (tripwire 2) |
| C | same job | 81/228 | 81/228 | identical | identical (tripwire 3) |

`training/eval/reports/260902_p26_dump_reproduction.json` holds the row-level diffs.
The arm dumps went through `scripts/slurm/bth_run.sh`, whose `BTH_CATALOG_DIR` export was
confirmed in the job log (the catalog-wiring fix, lesson 469).

## 4. Pre-registered prediction (row-level; `training/eval/reports/260902_p26_rescore_prediction.json`)

For each model, with OLD = the old-scorer report over its dump and NEW = the fixed scorer
(+ re-derived sidecar) over the SAME dump, checked by `finetune/rescore_check.check_prediction`:

1. **No row flips hit -> miss.**
2. **Every row that flips miss -> hit is in the breakdown's artifact set** for that model
   (`list_escape_format` + `slot_order_only` + `gold_slot_annotation` + `gold_missing_required`,
   classified by `finetune/failure_breakdown.py` on the OLD report). Artifact rows that
   remain misses are allowed (a second, genuine defect on the same row) and are listed as
   `predicted_but_still_missed` -- a classifier shortfall, not a deviation.
3. **Clarify recall, clarify precision, the confusion counts and the tripwire are identical**
   (they depend on neither params nor slots). Baseline v2's committed report predates the
   tripwire field; its re-score must carry the reconstructed value 13.
4. **n_examples == 228** for every report.

Expected ceilings (successes if every artifact row flips):

| model | old successes | artifact rows | ceiling | expected tripwire |
|---|---|---|---|---|
| baseline v2 | 37 | 8 (1 list / 4 order / 3 slot-annotation / 0 missing_required) | 45/228 = 0.197 | 13 |
| A | 88 | 57 (12 list / 26 order / 16 slot-annotation / 3 missing_required) | 145/228 = 0.636 | 1 |
| B | 85 | 52 (10 / 25 / 15 / 2) | 137/228 = 0.601 | 2 |
| C | 81 | 50 (11 / 22 / 14 / 3) | 131/228 = 0.575 | 3 |

**Expected verdict under the unchanged rule: NOT PROMOTED** (A's ceiling 0.636 < T_acc 0.80).
This sprint corrects the measurement for the data/recipe sprints that follow; it cannot promote.

Sidecar outcomes: `pass` = prediction holds (items 1-4) on that model; `fail` (residual) =
anything else. A `fail` is reported as a deviation in the decision addendum and the report is
NOT fed to `promotion.py`.

Mechanical checks on the regenerated corpus (also pre-registered): `corpus_p25.jsonl` byte-identical;
the sidecar diff restricted to `calls[].missing_required` / `calls[].unresolved_slots`;
`training/assemble/out/manifest.json` diff restricted to the assembly version and the new
gap-field rule; `test_assembly_idempotent.py` green.

## 5. What would count as a deviation

- Any hit -> miss flip, or any miss -> hit flip outside the artifact set (the fix changed
  more than the artifacts): stop, list the rows, hand to the user.
- Any change in clarify recall / precision / confusion / tripwire.
- Any change to the pairs file, to a sidecar field other than the two gap fields, or to the
  set of 228 eval record_ids.
- Re-running inference after this amendment (the dumps are the frozen input).

Not a deviation: artifact rows that stay misses; the cosmetic `base_revision` suffix
(`@main` on the 260902 dumps vs `@local` on the 260901 reports -- the CLI default revision
string for a local checkpoint directory; the weights are pinned by sha256 in `model_label`).

## 6. Storage

Dumps (4 x ~47 KB) and old-scorer reports under `training/eval/outputs/` and
`training/eval/reports/260902_p26_dumpscore_old_<model>.json` (commit `d82d4404`);
re-score reports `training/eval/reports/260902_p26_rescore_<model>.json` + `.check.json`;
bathos runs tagged `model:<model>` under project `praxis`. Checkpoints stay uncommitted
(`outputs/p26/<arm>/checkpoint`, gitignored; the 260901 prereg's `training/out/checkpoints/`
location was a documentation slip -- the manifests' `checkpoint.dir` is authoritative).

## 7. Outcome (260902, after the fixes)

Prediction held on all four models (`training/eval/reports/260902_p26_rescore_*.check.json`,
bathos runs `81c30927` baseline / `563e5133` A / `d55ad860` B / `01e07b30` C, all `pass`):
flips miss -> hit = artifact rows exactly (8 / 57 / 52 / 50), zero hit -> miss, zero
unpredicted, clarify metrics and tripwire identical, n = 228. New exact match: baseline
45/228 (0.197), A 145/228 (0.636), B 137/228 (0.601), C 131/228 (0.575). Corpus checks
held (pairs byte-identical; sidecar diff limited to the two gap fields; manifest diff =
version + rule + generator_versions.assemble; `test_assembly_idempotent` green). Verdict
under the unchanged rule: NOT PROMOTED (selected A). Decision addendum:
`.praxia/docs/audits/260901_p26-promotion.md` §8.
