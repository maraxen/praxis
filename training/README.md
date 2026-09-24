# praxis-training

Coxswain phase-2 copilot training pipeline (uv workspace member). Four
sub-pipelines share this directory; each owns its own package:

| Sub-pipeline | Spec item | Package | Owner backlog |
|--------------|-----------|---------|---------------|
| Golden pair set + baseline eval harness | P2.1 | `src/praxis_training/` | 4476 |
| Execution-verify harness | P2.2 | `verify/` | 4477 |
| Coverage-floor generator | P2.3 | `floor_gen/` | 4478 |
| Naturalness overlay | P2.4 | `overlay_gen/` | 4479 |

Shared-file rule for `pyproject.toml`: EXTEND (`include` globs, deps,
scripts), never replace wholesale.

## P2.1 (backlog 4476) -- golden pair set + baseline harness

### Layout

```
golden/
  golden_pairs.jsonl          FunctionGemma-native rows {metadata, tools[], messages[]}
  golden_intent_sidecar.jsonl parallel intent records (provenance "golden"),
                              line N <-> pairs line N
  manifest.json               counts by tool/class/split, scaffold version,
                              PLR submodule SHA keying (D9)
eval/
  fixtures/recorded_fixture_mechanics_proof.json   hand-made, NOT model outputs
  reports/                                         generated eval reports
src/praxis_training/
  golden_build/corpus.py      THE authored golden data (human-reviewed)
  golden_build/build.py       deterministic generator (byte-for-byte re-derivable)
  baseline_eval/fgml_parser.py hardened <start_function_call> extractor
  baseline_eval/metrics.py    exact-match / clarify recall+precision + Wilson 95%
  baseline_eval/runner.py     recorded-artifacts mode + local inference lane
  baseline_eval/local_infer.py transformers lane (lazy imports; gated-repo guard)
tests/                        scorer/parser/golden-consistency tests
```

### Commands

```bash
# regenerate golden artifacts (drift alarm is a test)
uv run --package training python -m praxis_training.golden_build.build

# mechanics proof over the hand-made fixture (clearly labeled, PARTIAL)
uv run --package training python -m praxis_training.baseline_eval \
    --recorded training/eval/fixtures/recorded_fixture_mechanics_proof.json \
    --split eval --allow-partial \
    --out training/eval/reports/260825_recorded_fixture_report.json

# REAL baseline run -- BLOCKED until license acceptance + token:
#   1. accept Google's Gemma terms at https://huggingface.co/google/functiongemma-270m-it
#   2. export HF_TOKEN=<token>
# then:
uv run --package training python -m praxis_training.baseline_eval \
    --model google/functiongemma-270m-it --revision <pin-a-sha> \
    --split eval --out training/eval/reports/baseline_real.json
```

Tests: `uv run --package training pytest training/tests/test_fgml_parser.py
training/tests/test_metrics_wilson.py training/tests/test_golden_consistency.py
training/tests/test_runner_modes.py -q`

### Recorded decisions (P2.1)

- **Scaffold**: research §2a developer template verbatim MINUS date/time
  preamble (D6-rev2 requires the omission be explicit). Tools list repeats all
  13 included tools per row (mobile-actions pattern).
- **Split policy**: ALL clarify-class examples held out (`metadata:"eval"`,
  36 total = 12 per class, >= D8's 30-held-out floor). Positives split
  2 train / 2 eval per tool so both splits carry every verb. Training-side
  negative mixing is P2.5 assembly's job (D7), not golden's.
- **Gap fields**: `missing_required` / `unresolved_slots` in the sidecar are
  ALWAYS derived via `coxswain.plr.slot_derivation` (D11) -- never authored,
  never model-predicted. Juror finding enforced by build assertions: clarify
  rows carry NON-EMPTY gap fields.
- **Static clarify scope** (recorded): clarify recall/precision measure
  out-of-surface abstention and missing-slot detection (cue 1). Cue-2
  referent resolution needs LIVE kernel state (F1-rev2/C-M1 mandatory
  kernel-side validation) and is verified at P2.9 integration, not here;
  ambiguous-referent rows contribute to exact-match passthrough fidelity and
  carry their derived slots downstream.
- **Excluded verbs are wrong-call failures**, not clarifications: an emitted
  call to a phantom/excluded verb fails exact match AND does not count as
  clarify-routing (the kernel gate would exit as an error, not a question).

## BLOCKED ITEM (action needed by orchestrator/user)

`google/functiongemma-270m-it` is a GATED HF repo. The real off-the-shelf
baseline run (AC-2.1.x "local CPU lane exercised") needs:
1. Gemma license terms accepted for the hub account owning the token
   (D13 gate artifact records the recommendation; user sign-off pending),
2. `HF_TOKEN` exported in the environment.

Until then the harness is proven in recorded-artifact mode against the tiny
hand-made fixture (mechanics proof only; report labeled RECORDED/PARTIAL).

## P2.5 (backlog 480) -- corpus assembly + slice gate

### Layout

```
assemble/
  developer_scaffold_template.txt   EXACT developer-turn scaffold (D6-rev2,
                                    no date injection; header states it)
  scaffold.py                       loader (bytes live in the template file)
  build.py                          deterministic assembly core + manifest
  __main__.py                       CLI
  out/
    corpus_p25.jsonl                ONE FunctionGemma-native JSONL
                                    {metadata, tools[], messages[]}
    corpus_p25_sidecar.jsonl        parallel lineage rows, line N <-> line N
    manifest.json                   PLR sha, versions, counts, exclusions,
                                    shortfall, split rule
```

### Run

```bash
uv run --package training python -m assemble          # idempotent regeneration
uv run pytest training/tests/test_assembly_split_disjointness.py \
              training/tests/test_assembly_scaffold_byte_match.py \
              training/tests/test_assembly_manifest_completeness.py \
              training/tests/test_assembly_idempotent.py -q
```

### Recorded decisions (P2.5)

- **Metadata normalization**: every emitted row carries `metadata` = FINAL
  assembled split ("train"|"eval"), assigned HERE per the recorded rule --
  golden-provenance ALL eval (instruments never train), synthetic strata
  (provenance x class x verb) sorted by record_id with last k -> eval,
  k = min(n-1, floor(0.2n)), bumped to >=1 once n>=4. Splits disjoint by
  construction; sidecar keeps each row's full lineage.
- **Uniform tool block**: every row repeats the FULL 13-tool declaration list
  (mobile-actions pattern) regardless of source branch's embedded block.
- **Validation gate excludes whole records loudly** (manifest `exclusions`):
  calls outside PHASE2_TOOL_NAMES, params outside the canonical namespace,
  numeric literals as strings, multi-value args on scalar-declared params
  (parallel/multi-channel calls the declared grammar cannot express).
- **Shortfall is recorded, never padded**: smoke-scale inputs yield 188 rows
  vs the ~1000 target; see manifest `target.shortfall_reason`.
- **Idempotency**: assembly is a pure function of committed inputs; upstream
  teacher caches (R4/D9) make same-inputs => same-corpus bytes. Drift-alarm
  test compares committed artifacts against a fresh build.
- **Gate docs**: thresholds PROVISIONAL at
  `.praxia/docs/specs/260825_p25_provisional_thresholds.md`; GO/NO-GO jury doc
  at `.praxia/docs/specs/260825_p25_slice_gate.md`; storage ledger entry in
  `.praxia/docs/research/260825_functiongemma-footprint.md` §6.
