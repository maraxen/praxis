# floor_gen -- Coxswain P2.3 coverage-floor generator

Backlog 4478, spec rev2 §7 AC-2.3.x (`260825_copilot_pipeline_spec`).

Pipeline: committed verb x ambiguity matrix -> deterministic structured-call
synthesizer (corpus-B keyword style from the canonical namespace table) ->
teacher NL-ification behind a content-hash cache -> provenance-tagged corpus
rows with FunctionGemma tool declarations rendered from the namespace table.

## Layout

| Path | Purpose |
|------|---------|
| `data/ambiguity_matrix.json` | THE matrix as committed data: verbs x {none, missing-slot, ambiguous-referent, out-of-surface}, validated against `coxswain.plr.param_namespace` + `TOOL_SCHEMA` at load |
| `versions.py` | generator/prompt version pins + provenance-tag factory |
| `value_formats.py` | pinned value-format conventions (volumes uL floats; wells `A1`-style uppercase; snake_case deck ids; vague refs only in ambiguous cells) |
| `declarations.py` | FunctionGemma tool-declaration rendering FROM the table (descriptions included) |
| `synth.py` | seeded structured-call synthesizer (determinism = sha256 of generator_version + cell + index) |
| `prompts.py` | versioned prompt builder (`p23_nlify_v1`) |
| `cache.py` | R4/D9 content-hash cache keyed by `(prompt_version, input_hash)` |
| `teachers.py` | titanix vLLM direct HTTP backend + ox-alpha batch writer + offline FakeTeacher |
| `corpus.py` | cache-first driver, D7/D11 supervision assembly, canonical JSONL output |
| `oxalpha_batches/` | fan-out-ready worker batch files (offline deliverable) |

## Supervision shapes (D7/D11)

- `none` -> complete tool_call
- `missing-slot` -> incomplete tool_call; `missing_required` derived via
  `coxswain.plr.slot_derivation`, never authored
- `ambiguous-referent` -> complete tool_call with a vague string reference;
  `unresolved_slots` derived (cue-2 clarify at serving time)
- `out-of-surface` -> NO tool_call; supervision is an NL clarification turn

## Commands (run from `training/`, or repo root with cwd=root)

    # live titanix smoke/full batch:
    ../.venv/bin/python -m floor_gen.cli generate --backend titanix --limit 12

    # ox-alpha fan-out files (no network):
    ../.venv/bin/python -m floor_gen.cli batches --limit 12

    # rebuild from cache ONLY (zero calls); byte-compare to prove R4/D9:
    ../.venv/bin/python -m floor_gen.cli regenerate --manifest out/manifest.json

Note: run pytest for training/ with the repo root as CWD; some sibling-suite
tests resolve repo-relative git paths.

## Import boundary (F2-rev2)

floor_gen imports `coxswain.plr.*`. Nothing in `coxswain/`, `praxis.backend.*`
(kernel-side), or any browser bundle may import back into `training/`.
