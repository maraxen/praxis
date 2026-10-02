---
title: 'Sema web integration, Slice 1: plr-sema owns the graph and extractor, shared analyze() seam, CLI/CI first consumer'
description: 'Slice 1 of four (decomposed 261002): lift the protocol computation-graph models and the libcst extractor from praxis into plr-sema behind re-export shims, add an analyze() surface over extract->check_graph, ship the contract table compact+gzipped (0.42 MB, pre-registered run 4137815b PASS), define a content-hash VerdictKey, and ship a `python -m plr_sema check` CLI with a dedicated plr-sema CI workflow as the first consumer.'
status: approved
task_id: 261002_sema-web-integration
date: '261002'
backlog_ids: ''
adversarial_review: ''
---
# Sema web integration, Slice 1: plr-sema owns the graph and extractor, shared analyze() seam, CLI/CI first consumer

## 0. Why this slice, and what it is not

**Goal (user, 261002):** plr-sema verdicts appear natively in praxis — a pre-run gate on cell
execute in the browser workspace, plus UX for four surfaces outside it: the run-protocol
pre-flight gate, the execution monitor during a run, the protocol library on save/upload, and a
CLI/CI check over a protocol repo.

**Decomposition** (each slice gets its own spec → plan → implementation):

| Slice | Delivers | Depends on |
|---|---|---|
| **1 (this spec)** | One analysis seam: `plr_sema.analyze(source, …)`; graph models + extractor owned by plr-sema; deterministic gz contracts; `VerdictKey`; CLI + CI | — |
| 2 | Browser: run `analyze()` in Pyodide on cell execute; pre-run gate UI; top-level cell code (not a `FunctionDef`) | 1 |
| 3 | Backend surfaces: protocol-library save/upload verdict + run-protocol pre-flight gate; verdict persistence keyed by `VerdictKey` | 1 |
| 4 | Execution monitor: show the pre-run verdict, flag the failing op when it is reached | 1, 3 |

Slice 1 has **no UI**. Its user-visible deliverable is the CLI (the fourth outside surface), which is
also what proves the seam before two UIs depend on it.

## 1. Locked decisions

- **D1 — gate placement (browser):** pre-run gate on cell execute. (User, 261002.) Slice 2.
- **D2 — surfaces outside the browser:** all four above are in scope for the epic. (User, 261002.)
- **D3 — order:** Spike 0 (Pyodide feasibility) first, then this spec. (User, 261002.) Spike 0 done, §3.
- **D4 — extractor ownership:** lift it into `plr_sema.extract`. (User, 261002.) praxis keeps
  re-export shims; there is exactly one extractor.
- **D5 — one analysis function for every surface:** browser, backend, and CLI all call
  `plr_sema.analyze()`. No surface re-implements extraction or checking. (Section 2, approved.)
- **D6 — gate semantics: warn-only first, block later.** (User, 261002.) plr-sema's precision at
  the PLR 1.0 pin is currently unmeasured-to-zero, so UI surfaces show `WILL_FAIL` prominently but
  do **not** block. Blocking (with an explicit override, recorded against the `VerdictKey` so the
  execution monitor can show "ran despite WILL_FAIL") is enabled only after precision at the 1.0
  pin is re-measured under a pre-registered sidecar and clears a bar fixed in that sidecar.
  Invariants from day one: `UNKNOWN` never blocks; `NotAnalyzed` never blocks and is never shown as
  `SAFE`. Slice 1 is unaffected: the CLI exit codes (§6) are signals, and CI users choose whether
  exit 1 fails their build.

## 2. Assumptions (tagged)

| # | Assumption | Status | Evidence |
|---|---|---|---|
| A1 | The vendored Pyodide ships libcst and pydantic wheels | **verified** | `web-repl/vendor/pyodide-314.0.1.tar.bz2` lockfile: libcst 1.8.6, pydantic 2.12.5 |
| A2 | The extractor runs in Pyodide at interactive latency | **verified (exploratory)** | Spike 0: 31-statement protocol parsed in 80 ms + 28 ms metadata, `libcst.native` loaded. Run under bun, not Chromium, and not pre-registered — Slice 2 must re-measure in Chromium under a sidecar before citing a latency budget |
| A3 | The contract table fits a browser payload budget (≤ 1 MB transferred) | **verified (pre-registered)** | bathos run `4137815b`, outcome **pass**: 18,394,524 B raw → 9,826,575 B compact → **421,775 B** gzip-9 (ratio 0.0429), round-trip equal, 5,808 contracts; negative control (incompressible stream) 9,829,593 B gz, correctly over budget. Sidecar `plr-sema/eval/contract_payload.bth.toml`, commit 69b0f1f6 |
| A4 | The extractor's only praxis imports are `models`, `resource_hierarchy`, `type_inspection` | **verified** | read `visitors/computation_graph_extractor.py` imports (1,050 lines) |
| A5 | Moving the pydantic graph classes does not break persisted data | **verified** | `computation_graph_json` is a `JsonVariant` dict column; `ParseCache` stores json; `protocol_discovery.py:298` persists `graph.model_dump(exclude_none=True)` — no pickled class paths |
| A6 | plr-sema's suite is green on main, so a new CI job starts green | **verified** | local run on origin/main e06ab3b1: 1302 passed, 20 skipped, 1 failed. The failure (`test_fork_drift::test_git_state_matches_cisternal`) needs a sibling cisternal checkout and **skips** when it is absent, as on a CI runner; locally it reports real cisternal drift |
| A7 | `check_graph` accepts the extractor's `model_dump` output unchanged | **verified** | `tests/test_check_graph_mirror_drift.py` asserts two-way field parity between `check/graph.py` and `models.py:504–671` |
| A8 | `parameter_types` can be derived from the protocol function's annotations | **verified** | `extract_graph_from_function` already does this when `parameter_types is None` (annotation text, else `"Any"`); `analyze()` passes `None` |
| A9 | The browser kernel does not import any moved module, so Slice 1 cannot break the web REPL | **verified** | the browser's `praxis` package is the overlay `web-repl/overlay/assets/python/praxis/` (`display`, `interactive`, `viz`); none of them reference the four moved modules |
| A10 | Moving files does not break the dated plr-sema specs' line citations | **verified** | all five specs citing the moved files carry a frontmatter `citations_at: <sha>` pin, and `check_spec_citations.py` resolves pinned citations against that revision |
| A11 | Extractor output is deterministic, so byte-exact parity goldens are viable | **verified (spike)** | 26 top-level functions (16 `plr-sema/eval/fixtures` files + 6 `praxis/protocol/protocols`) give identical sorted-key JSON under `PYTHONHASHSEED` 0–3 |

## 3. Correction to Section 1 (accepted 261002)

Section 1 proposed deleting the stdlib mirror `plr_sema/check/graph.py` once plr-sema owns the
pydantic models. **That contradicts the other Section 1 commitment, that `check/` stays
pydantic-free** (it is what runs with zero dependencies, and `import plr_sema` must keep working on
plain CPython — `test_plain_cpython_import_of_public_surface`).

**Revised:** the mirror stays. Its role changes from guarding a cross-repo seam to guarding an
in-package seam (`plr_sema.graph` pydantic ↔ `plr_sema.check.graph` stdlib), and
`test_check_graph_mirror_drift.py` keeps enforcing it, now importing both sides from plr-sema.
Add `pydantic` to the forbidden imports under `check/` in `test_import_boundary.py`
(today only `pylabrobot` and `libcst` are enforced).

## 4. Package layout

```
plr-sema/src/plr_sema/
  __init__.py          # unchanged eager surface: check_graph, AnalysisReport, Verdict
                       # + lazy __getattr__ for analyze, VerdictKey (no eager libcst/pydantic import)
  __main__.py          # NEW: CLI (§6)
  analysis.py          # NEW: analyze(), AnalysisOutcome, VerdictKey (§5). Not `analyze.py`:
                       # a submodule named `analyze` would shadow the lazy `plr_sema.analyze` function
  contracts.py         # NEW: load_contracts(path) for .json / .json.gz; build_gz() (§7)
  graph/               # NEW: moved from praxis (pydantic + stdlib)
    models.py          #   from praxis/backend/utils/plr_static_analysis/models.py:504–671 only
    resource_hierarchy.py   # from praxis (whole file, 492 lines)
    type_inspection.py      # from praxis/common/type_inspection.py (whole file, 442 lines)
  extract/             # existing empty placeholder, now populated
    computation_graph_extractor.py  # moved (1,050 lines), imports rewritten to plr_sema.graph.*
  check/               # unchanged; stays stdlib-only
```

- `pyproject.toml`: `[project.optional-dependencies] extract = ["libcst>=1.1.0", "pydantic>=2.0.0"]`.
  Base install stays dependency-free.
- **praxis shims:** the four praxis modules become re-exports
  (`from plr_sema.graph.resource_hierarchy import *` plus explicit names for anything private that
  consumers import). The remainder of `models.py` (everything outside 504–671) stays in praxis and
  imports the graph classes from plr-sema. Each shim gets an identity test
  (`praxis_mod.X is plr_sema_mod.X`) so `isinstance` checks across the ~10 consumers keep working.
- **Dependency direction reverses:** praxis now depends on plr-sema at runtime. Root
  `pyproject.toml` adds `plr-sema[extract]` as a workspace dependency
  (`[tool.uv.sources] plr-sema = { workspace = true }`). See R1 for the Dockerfile.

## 5. `analyze()` contract

```python
def analyze(
    source: str,
    function_name: str | None = None,   # None → the single top-level def; ambiguous → NotAnalyzed
    *,
    contracts: Contracts | None = None, # None → resolve via §7; unavailable → NotAnalyzed
    deck_layout_type: DeckLayoutType | None = None,
) -> AnalysisOutcome: ...

AnalysisOutcome = Analyzed | NotAnalyzed

@dataclass(frozen=True)
class Analyzed:
    report: AnalysisReport   # existing type from check_graph
    key: VerdictKey
    function_name: str       # the function actually analyzed
    op_lines: dict[str, int] # OperationNode.id -> line in `source` (CLI output, Slice 2 gutter marks)

@dataclass(frozen=True)
class NotAnalyzed:
    reason: NotAnalyzedReason  # SYNTAX_ERROR | FUNCTION_NOT_FOUND | AMBIGUOUS_FUNCTION
                               # | EXTRACT_FAILED | CHECK_FAILED | EXTRACTOR_UNAVAILABLE
                               # | CONTRACTS_UNAVAILABLE
    detail: str
```

- Two top-level definitions with the target name, or several top-level functions with
  `function_name=None`, give `AMBIGUOUS_FUNCTION` (the praxis extractor silently takes the first).
- `analyze` never raises for a bad protocol; it returns `NotAnalyzed`. It raises only for
  programmer errors (wrong argument types).
- `EXTRACTOR_UNAVAILABLE` is what a base install (no `[extract]`) returns, so callers on plain
  CPython get a typed answer instead of an `ImportError`.
- **`NotAnalyzed` is never rendered or exit-coded as SAFE.** This is the invariant every surface
  inherits.
- `parameter_types` are derived from the function's annotations (A8); if derivation fails, pass
  `None` rather than failing the analysis.

### VerdictKey

`VerdictKey(source_sha256, contracts_sha256, analyzer_sha256, schema_version)`:

- `source_sha256`: **full** sha256 of the analyzed function's source text (not the whole file, so
  editing an unrelated cell or function does not invalidate it).
- `contracts_sha256`: sha256 of the canonical compact JSON of the contract table — identical
  whether it was loaded from `.json` or `.json.gz`.
- `analyzer_sha256`: sha256 over the sorted (relative path, bytes) of `plr_sema/**/*.py` in the
  installed package — changes whenever the extractor or checker changes, with no manual version bump.
- `schema_version`: `plr_sema.verdict.SCHEMA_VERSION` (already the `AnalysisReport` wire pin; reused, not duplicated).

Slice 1 defines and tests the key only. **Storage is Slice 2 (browser) and Slice 3 (backend).** Note
for Slice 3: `protocol_discovery.py:298` uses a truncated 16-char `source_hash`; it is not reused
as a verdict key (Q4).

## 6. CLI

`python -m plr_sema check <file.py> [--function NAME] [--json] [--contracts PATH]`

| Exit | Meaning |
|---|---|
| 0 | analyzed; no `WILL_FAIL` verdicts (`UNKNOWN` allowed) |
| 1 | analyzed; at least one `WILL_FAIL` |
| 2 | not analyzed (any `NotAnalyzedReason`), or usage error |

Text output: one line per finding (`file:line op verdict reason`), then a summary line.
`--json` emits `{"key": …, "outcome": "analyzed"|"not_analyzed", …}` with a stable schema
(snapshot-tested). Multiple files: `check a.py b.py` → worst exit code wins.

## 7. Contracts loading

- `load_contracts(path)` accepts `.json` and `.json.gz` (detected by gzip magic bytes, not by
  extension).
- `build_gz(src, dst)` is deterministic: compact separators, `sort_keys=True`,
  `gzip.compress(level=9, mtime=0)`. Same input → byte-identical output (tested).
- The pretty `.json` stays the committed source of truth. **The `.gz` is a build artifact and is
  never committed.**
- Default resolution when `contracts=None` (no default path in library code): explicit argument >
  `PLR_SEMA_CONTRACTS` env var (`none`/empty disables) > `[tool.plr-sema] contracts` in the nearest
  `pyproject.toml` > unavailable (→ `CONTRACTS_UNAVAILABLE`). `contracts_source()` reports which
  layer decided; a malformed config fails loudly.
- The table lives at `plr-sema/data/derived_contracts.json` (verified: outside `src/`, so **not**
  package data today). This repo's root `pyproject.toml` gets
  `[tool.plr-sema] contracts = "plr-sema/data/derived_contracts.json"`, which is what the CLI and CI
  resolve to. Bundling the `.gz` into a wheel or the browser build is Slice 2/3 work, not Slice 1.

## 8. CI

New workflow `.github/workflows/plr-sema.yml`, triggered on `plr-sema/**`, the four moved praxis
modules and their shims, and the workflow file itself. It runs the plr-sema suite plus a CLI
smoke test (one known-SAFE protocol → exit 0; one seeded WILL_FAIL → exit 1; one syntax error → exit 2).

**Deviation from the Section 2 wording ("wire into repl.yml"):** `repl.yml`'s path filter excludes
`plr-sema/**` and its job is browser/Chromium. Adding a Python suite there would either run it on
every web change or not at all on plr-sema changes. A separate workflow is cheaper and matches the
trigger. (This is plr-sema's first CI coverage of any kind.)

Expected starting state (A6): green, with `test_git_state_matches_cisternal` skipped.

**Merge-policy note:** the `main` ruleset requires checks from the disabled `ci.yml`, and merges are
the owner's `--admin` bypass. `plr-sema.yml` is **not** a required check (Q5).

## 9. Build sequence (TDD; each step red → green)

| Step | What | Gate |
|---|---|---|
| T1 | **Parity golden:** run today's praxis extractor over every protocol source the existing extractor tests use (`tests/utils/test_computation_graph.py`, `tests/core/test_precondition_resolver.py`, `plr-sema/tests/test_check_graph.py`, `plr-sema/tests/test_tier2.py`) and commit the `model_dump` JSON, before any move | goldens committed |
| T2 | Move `graph/` (3 modules); praxis shims + identity tests; `pydantic` added to the `check/` import ban | praxis + plr-sema tests green, goldens unchanged |
| T3 | Move the extractor into `extract/`; rewrite its imports; praxis shim | goldens byte-identical |
| T4 | `analyze()` + `NotAnalyzed` reasons, one test per reason | every reason reachable from a fixture |
| T5 | `contracts.py`: load .json/.json.gz, deterministic `build_gz`, resolver chain + `contracts_source()` | determinism test (two builds byte-equal) |
| T6 | `VerdictKey` + invalidation tests (edit fn → key changes; edit other fn → unchanged; .json vs .gz → same) | |
| T7 | CLI + exit-code tests + `--json` snapshot | |
| T8 | Move citations in the same change: `_hand_maintained.py:854` (cites `models.py:~500-521`), docstrings in `check/graph.py` and `tests/test_check_graph.py` | `test_spec_lint` + ratchet tests green |
| T9 | `plr-sema.yml` workflow; root dependency + Dockerfile change (R1) | workflow green on the PR; `docker build` succeeds and `python -c "import praxis.backend…"` runs in the image |

No step runs the whole praxis suite locally (local-compute rule); praxis verification is the
consumers of the moved modules, selected by path.

## 10. Risks

- **R1 — the image breaks at import time.** The Dockerfile does `COPY . .` then
  `pip install --no-deps .`; once the praxis shims import `plr_sema`, the image needs plr-sema
  installed. T9 adds `pip install --no-deps ./plr-sema` before the root install. **This cannot be
  verified in Slice 1:** no workflow builds the image, Docker is not available locally, and the
  Dockerfile already has the same failure mode for `pylabrobot` (`uv pip compile pyproject.toml`
  runs before the repo, including `external/pylabrobot`, is copied in). Adding `plr-sema` to
  `[project].dependencies` makes that compile step fail outright, because no `plr-sema` exists on
  PyPI. T9 therefore filters workspace members out of the compiled requirements; a real
  image-build check is a follow-up outside this slice.
- **R2 — silent behavior drift during the move.** Mitigated by the T1 goldens (byte-identical
  extractor output before and after) and the identity tests.
- **R3 — stale live citations.** The dated specs are pinned (A10). What remains is prose and
  docstrings that name the old paths: `_hand_maintained.py:652` and `:854` (`what=` strings, which
  are display text and not path-checked), the `check/graph.py` module docstring, and
  `tests/test_check_graph.py`. T8 updates them.
- **R4 — local-only red.** `test_git_state_matches_cisternal` fails on machines with a drifted
  cisternal checkout. Not a CI blocker (it skips there), but anyone running the suite locally will
  see it. Out of scope here.

## 11. Resolved questions (user, 261002)

- **Q1 — keep the stdlib mirror, ban pydantic under `check/`:** accepted (§3).
- **Q2 — gate semantics:** warn-only until precision at the 1.0 pin is re-measured (D6).
- **Q3 (Slice 2) — top-level cell code:** wrap the cell in a synthetic function rather than extend
  the extractor to module bodies. Free names defined in earlier cells become the synthetic
  function's parameters, typed from the live kernel objects (better than annotations). Slice 2 must
  spike two things first: line-number mapping back to the cell, and top-level `await` (requires a
  synthetic `async def`).
- **Q4 (Slice 3) — `protocol_discovery` 16-char `source_hash`:** leave it; it is a discovery-cache
  key. `VerdictKey` is used only for verdicts.
- **Q5 — required check:** no. A path-filtered workflow as a required check leaves unrelated PRs
  stuck at "Expected — waiting", and merges are owner `--admin` bypass anyway. If it is ever made
  required, add an always-run no-op job for unmatched paths.

## 12. Evidence index

- bathos run `4137815b-ebe4-4720-bacc-8b7ed48cc3ad` — contract payload, outcome pass; script + sidecar
  `plr-sema/eval/contract_payload{.py,.bth.toml}` (commit 69b0f1f6); report
  `outputs/sema_s1/contract_payload.json`; input sha256 `09336b5f…e403`; PLR pin `786ac2c4e`.
- Spike 0 (exploratory, bun + Pyodide 314.0.1): libcst + pydantic load; 31-statement parse 80 ms +
  metadata 28 ms. Not pre-registered — re-measure in Chromium under a sidecar in Slice 2.
- Baseline: plr-sema suite on origin/main e06ab3b1 — 1302 passed / 20 skipped / 1 failed (cisternal
  drift, skips on CI), 375 s.
