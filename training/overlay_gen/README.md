# P2.4 naturalness-overlay generator

Spec: `.praxia/docs/specs/260825_coxswain-phase-2-functiongemma-copilot-p.md`
rev2 §5 P2.4 / §7 AC-2.3-2.4.x. Backlog item 479, task_id
`260825_copilot_pipeline_spec`.

## What this is

Mines liquid-handling calls from two corpora, normalizes them to the P2.0
namespace-table shapes (`coxswain.plr.param_namespace`), pairs each with
teacher-paraphrased natural-language instructions, deduplicates normalized
utterances, and emits provenance-tagged candidate rows.

Sources:

1. `external/pylabrobot/docs/user_guide/00_liquid-handling/**` -- code cells
   AST-parsed (never executed/imported). At PLR 1.0.0b1 this is 5 notebooks
   (16 at the pre-1.0 pin; the hamilton-star and OT2 notebooks left this
   tree). Hardware-context-only notebooks (probing / grippers / barcode
   reader / surface-following / liquid classes / plate washer) are skipped
   whole when present; reasons recorded in the mining manifest.
   **Receiver gate:** only calls whose receiver resolves to a legacy
   `LiquidHandler` are kept. The modern device-API calls in
   `hamilton-prep/prep_basic_demo.ipynb` (`prep.pipettes.*`, `prep.head8.*`)
   share verb names but not semantics; they are recorded as exclusions
   ("receiver ... not a legacy LiquidHandler"), never relabelled.
2. `praxis/protocol/protocols/*.py` -- the 6 runnable `@protocol_function`
   modules, AST-parsed.

Verbs outside the phase-2 surface (phantoms, 96-channel family, tip-return
family, heater-shaker family, state/query plumbing) are counted then dropped;
expert kwargs (`offsets`, `use_channels`, `mix` lists...) are dropped per the
P2.0 scope policy and recorded per call in `dropped_kwargs`.

## Run

```bash
# from repo root; stdlib-only code, any CPython >=3.10 with coxswain importable
PYTHONPATH=training python -m overlay_gen.run_smoke          # smoke subset
PYTHONPATH=training python -m overlay_gen.run_smoke --full   # later full-scale gate
```

Artifacts land in `overlay_gen/out/` (mining manifest, `overlay_*.jsonl`,
report). Teacher responses cache content-addressed under `overlay_gen/cache/`
-- same sha => same corpus, so re-runs are idempotent and offline-replayable.

## Tests

```bash
python -m pytest training/tests/test_miner_extraction.py \
                  training/tests/test_dedup_and_pairs.py \
                  training/tests/test_shapes.py
```

(Scoped to these files on purpose: other phase-2 workers own the rest of
`training/tests/`.)

## Known duplication (deliberate)

`cache.py` implements the R4 teacher-output cache locally because P2.3's
coverage-floor generator (which owns "the" shared cache per spec) was not
merged at 260825. When P2.3 lands, reconcile both into one util and delete
the loser.
