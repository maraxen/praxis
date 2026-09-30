---
title: PLR 1.0 phase 2 PR-0 baselines
description: 'Pre-change baselines for #5664 phase 2: deprecated-API inventory (bathos 82c34286 PASS), protected training bytes, backend per-file pytest, Angular tsc/ng test.'
status: active
task_id: 260930_plr10-phase2-pr0
date: '260930'
confidence: ''
sources: ''
---
# PLR 1.0 phase 2 PR-0 baselines

This is PR-0 of the phase-2 plan (`.praxia/docs/plans/260929_plr-1.0-phase2-plan.md` §5, backlog #5664). It changes no code. It records the pre-change state that PR-1 to PR-8 diff against.

All four baselines were taken on a tree whose content equals `main` at `bd72dd2b` (the #194 merge) plus this PR's own scripts. The inventory is the only baseline that is a finding (plan §8), so it is a registered bathos run. The other three are plain verification.

## 1. Deprecated-API inventory (registered)

- **Script and sidecar:** `scripts/plr10/phase2_inventory.py` and `scripts/plr10/phase2_inventory.bth.toml`, committed at `d98947cd` **before** any root scan ran.
  - Only the synthetic controls were run first, into a scratch directory, so the count below was unseen when the sidecar was written.
  - The script ports the 260929 recon script with unchanged classification rules, and regenerates the vocabulary from PLR 1.0.0b1 source on every run.
- **Run:** bathos `82c34286-8325-4bc6-acef-ba831d9a5648`, via `bth run --project-slug praxis -- uv run --no-sync python scripts/plr10/phase2_inventory.py --out-dir outputs/plr10/phase2_inventory_pr0 --recon-tsv <recon tsv>`.
- **Verified by its record, not by console text:** the cool-tier parquet, and the warm index after `bth compact`, both show `status = completed`, `outcome = pass`, `exit_code = 0` and `git_hash = d98947cd`.
- **`git_dirty = true` is explained.** The only entries are untracked: the session's harness files (`.claude/*`, `.mcp.json`) and the bathos lock file the run itself writes. The script refuses to run with tracked changes under any scanned root.
- **Outputs:** force-added under `outputs/plr10/phase2_inventory_pr0/`: `result.json`, `detail.json`, `inventory.tsv`, and `units/` with its sha256 stamps.

| field | value |
|---|---:|
| upstream deprecation rows / vocabulary | 95 / 92 |
| files scanned (7 roots) | 3294 |
| parse errors | 0 |
| positive control (.py forms / .ts names) | 93/93 · 86/86 |
| negative control hits (89 replacement lines) | 0 |
| **code/data rows (files)** | **93 (26)** |
| survey_data / test-fixture / ambiguous / docstring | 814 / 160 / 88 / 16 |

**Attribution against the recon's 88.**
- The per-file delta has exactly one non-zero entry: `scripts/plr10/phase2_inventory.py` at +5. That is the scanner's own vocabulary tables, which name the deprecated forms.
- Every other file's code/data count equals the recon's.
- **So praxis's real usage is 88 rows in 25 files, unchanged since the recon.** #191, #192 and #193 moved no code/data row; their `has_tip` and `num_rails` edits classify as `ambiguous`.
- **Follow-up for PR-8's after-run:** its new sidecar should classify the scanner itself as the instrument, or the target "0 outside survey_data/docstrings" is unreachable by construction.

## 2. Protected training bytes

`scripts/plr10/protected_bytes.py record` writes the manifest `scripts/plr10/baselines/protected_bytes_pr0.json`: 20 files under `training/assemble/out`, `training/golden`, `training/overlay_gen/out`, `training/overlay_gen/frozen`, and `training/assemble/pin.py`, each with its sha256 and size.

- **All tracked.** Every protected file is tracked by git, and on-disk equals tracked. The script refuses untracked, missing or modified files.
- **Comparator checked.** `compare` on the manifest against itself reports identical. A copy with one hash perturbed reports that path as `changed` and exits 1.
- **Not the byte gate.** PR-5's byte gate is its own pre-registered run (plan §8 item 2); PR-0 only records.

## 3. Backend per-file pytest (plan §4)

The files were run one process each, via `uv run --no-sync python -m pytest <file> -q`. All pass.

| file | result |
|---|---|
| `tests/core/test_workcell_runtime.py` | 24 passed |
| `tests/protocols/test_chatterbox_execution.py` | 29 passed |
| `tests/utils/test_sanitation.py` | 35 passed |
| `tests/backend/core/test_consumable_assignment.py` | 24 passed |
| `tests/backend/core/test_deck_config.py` | 6 passed |

## 4. Angular (`praxis/web-client`), never run in phase 1

Setup: `bun install --frozen-lockfile` installed 782 packages. `BUN_TMPDIR` and `BUN_INSTALL_CACHE_DIR` had to point at a writable directory under the sandbox.

| check | result |
|---|---|
| `bunx tsc --noEmit -p tsconfig.app.json` | **clean**, 0 errors |
| `bunx tsc --noEmit -p tsconfig.spec.json` | **37 errors, already red on main.** Error list: `scripts/plr10/baselines/tsc_spec_errors_pr0.txt` |
| `bun run test -- --watch=false` (`ng test`) | **the test bundle does not compile: 0 tests executed.** 38 build errors: `scripts/plr10/baselines/ng_test_build_errors_pr0.txt` |

The build errors fall into these groups:
- missing `jasmine` and `global` types in vitest specs;
- a stale `ProtocolRun` fixture shape (TS2741, `previous_accession_id`);
- `import type` under `isolatedModules` (TS1272);
- one unresolved module, `./sqlite.service`.

**Consequence for the plan.** PR-7b and PR-8 verify with "`ng test` diffed against PR-0". While the bundle fails to compile, that diff can only show that the same compile errors persist; it cannot catch a behavioural regression. Repairing the spec build is outside #5664 and is filed as backlog **#5678**. Until it lands, those PRs can only be verified by "no new `tsc` app or spec errors against these two lists", plus a manual smoke test.

