---
title: 'Sema web integration Slice 1: implementation plan'
description: 'Nine TDD tasks implementing spec 261002_sema-web-integration-slice1: parity goldens, move graph models + extractor into plr-sema behind praxis shims, check/ boundary, contracts loader, analyze()/VerdictKey, CLI, CI workflow and dependency wiring.'
status: draft
task_id: 261002_sema-web-integration
date: '261002'
---
# Sema web integration Slice 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** plr-sema owns the protocol computation-graph models and the libcst extractor, exposes one `analyze(source, function_name)` seam returning a typed outcome with a content-hash `VerdictKey`, and ships it as `python -m plr_sema check` with its own CI workflow.

**Architecture:** Move four praxis modules into `plr-sema/src/plr_sema/{graph,extract}/` with `git mv` (verbatim, so line numbers and history survive) and leave re-export shims at the old paths. Add `contracts.py` (stdlib loader + resolver chain), `analysis.py` (`analyze`, `VerdictKey`), and `__main__.py` (CLI). `check/` stays stdlib-only; the stdlib mirror `check/graph.py` stays and is now checked against `plr_sema.graph.models`.

**Tech Stack:** Python ≥3.10 (venv is 3.14.6), libcst, pydantic v2, pytest, uv workspace, GitHub Actions.

**Spec:** `.praxia/docs/specs/261002_sema-web-integration-slice1.md` (status approved, commit f3e60588 + plan-time corrections). Read it before Task 1.

## Global Constraints

- Work in the worktree `/tmp/praxis-sema-s1`, branch `feat/sema-slice1-spec`. Never `git add -A`; stage explicit paths. Never force-push. Merging is the user's decision.
- Environment once per session: `cd /tmp/praxis-sema-s1 && uv sync --all-packages`. Then every command is `uv run --no-sync …` (bare `uv run` re-syncs).
- **Never run a whole test suite locally.** Run the named files only. `export OMP_NUM_THREADS=4`.
- `plr-sema` base install has `dependencies = []`; `import plr_sema` must work on plain CPython and must not load `libcst`, `pydantic` or `pylabrobot`.
- Nothing under `plr-sema/src/plr_sema/` may import `praxis`, `verify` or `training`. Nothing under `plr_sema/check/` may import `pylabrobot`, `libcst` or `pydantic`.
- Optional extra: `extract = ["libcst>=1.1.0", "pydantic>=2.0.0"]`.
- Graph wire format is exactly `json.dumps(graph.model_dump(mode="json"))` (what `plr-sema/eval/extract_runner.py` sends today).
- Moved files are moved **verbatim** (praxis uses 2-space indentation; keep it). Only import lines change, and the import block keeps its line count.
- New plr-sema files use 4-space indentation (plr-sema's convention). New praxis-side shim text uses 2-space.
- `NotAnalyzed` is never reported or exit-coded as SAFE.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and carry `(261002_sema-web-integration)`.

## Review Focus

These inputs are implied by the spec but not exercised by its build-sequence gates; each has a test in the owning task.

1. **A file with two top-level functions of the same name** → `NotAnalyzed(AMBIGUOUS_FUNCTION)`, not "first one wins" (the praxis extractor silently takes the first). Task 6.
2. **An extractor crash on odd but valid code** (e.g. `lh.aspirate(*args, **kw)` or a lambda receiver) → `NotAnalyzed(EXTRACT_FAILED)` with the exception type named, never a traceback; CLI exit 2. Task 6 + Task 7.
3. **A truncated or corrupt `.json.gz` contracts file** → `ContractsError` from the loader and `NotAnalyzed(CONTRACTS_UNAVAILABLE)` from `analyze`, not `EOFError`/`BadGzipFile`. Task 5 + Task 6.
4. **A CLI input file that is not UTF-8** (or does not exist) → exit 2 with a one-line message, not a `UnicodeDecodeError` traceback. Task 7.
5. **Editing a sibling function, or the blank lines/comments between functions** → `VerdictKey.source_sha256` of the analyzed function is unchanged (the key hashes the function without its `leading_lines`). Task 6.

---

### Task 1: Extractor parity goldens (before anything moves)

Pins today's extractor output byte-for-byte over a fixed corpus, so the moves in Tasks 2 and 4 are provably behavior-preserving.

**Files:**
- Create: `plr-sema/tests/_extract_corpus.py`
- Create: `plr-sema/scripts/capture_extract_goldens.py`
- Create: `plr-sema/tests/fixtures/extract_goldens.json` (generated)
- Create: `plr-sema/tests/test_extract_parity.py`

**Interfaces:**
- Produces: `corpus() -> list[tuple[str, str, str]]` (key `"<repo-relative path>::<function>"`, source, function name); `GOLDENS: Path`; `dump(graph) -> dict`. The parity test imports `extract_graph_from_source` from `praxis.backend.utils.plr_static_analysis.visitors.computation_graph_extractor` in this task; Task 4 switches it.

- [ ] **Step 1: Write the corpus helper**

`plr-sema/tests/_extract_corpus.py`:

```python
"""The fixed protocol corpus for the extractor parity goldens (spec 261002 Slice 1, T1).

Every top-level function in these files is extracted and its graph pinned in
``fixtures/extract_goldens.json``. Verified deterministic across
PYTHONHASHSEED 0-3 (26 graphs) before this file was written.
"""

from __future__ import annotations

from pathlib import Path

import libcst as cst

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_GLOBS = (
    ("plr-sema/eval/fixtures", "**/*.py"),
    ("praxis/protocol/protocols", "*.py"),
)
GOLDENS = Path(__file__).resolve().parent / "fixtures" / "extract_goldens.json"


def corpus() -> list[tuple[str, str, str]]:
    """(key, source, function_name) for every top-level def, sorted by key."""
    items: list[tuple[str, str, str]] = []
    for root, pattern in CORPUS_GLOBS:
        for path in sorted((REPO_ROOT / root).glob(pattern)):
            source = path.read_text(encoding="utf-8")
            try:
                module = cst.parse_module(source)
            except cst.ParserSyntaxError:
                continue
            rel = path.relative_to(REPO_ROOT).as_posix()
            for stmt in module.body:
                if isinstance(stmt, cst.FunctionDef):
                    items.append((f"{rel}::{stmt.name.value}", source, stmt.name.value))
    return sorted(items)


def dump(graph) -> dict | None:
    return None if graph is None else graph.model_dump(mode="json")
```

- [ ] **Step 2: Write the capture script**

`plr-sema/scripts/capture_extract_goldens.py`:

```python
"""Regenerate tests/fixtures/extract_goldens.json from the CURRENT extractor.

Run only when an extractor behavior change is intended and reviewed:
    uv run --no-sync python3 plr-sema/scripts/capture_extract_goldens.py
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from _extract_corpus import GOLDENS, corpus, dump  # noqa: E402

log = logging.getLogger("capture_extract_goldens")


def _extractor():
    try:
        from plr_sema.extract.computation_graph_extractor import extract_graph_from_source
    except ImportError:
        from praxis.backend.utils.plr_static_analysis.visitors.computation_graph_extractor import (
            extract_graph_from_source,
        )
    return extract_graph_from_source


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=GOLDENS)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    extract = _extractor()
    goldens = {key: dump(extract(source, fn)) for key, source, fn in corpus()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(goldens, sort_keys=True, indent=1) + "\n", encoding="utf-8")
    log.info("wrote %d goldens (%d non-null) to %s", len(goldens),
             sum(v is not None for v in goldens.values()), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Write the parity test (fails: no goldens yet)**

`plr-sema/tests/test_extract_parity.py`:

```python
"""Extractor parity goldens (spec 261002 Slice 1, T1): the moved extractor must
produce byte-identical graphs to the praxis extractor it replaced."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("libcst")
pytest.importorskip("pydantic")

from _extract_corpus import GOLDENS, corpus, dump  # noqa: E402
from praxis.backend.utils.plr_static_analysis.visitors.computation_graph_extractor import (  # noqa: E402
    extract_graph_from_source,
)

CORPUS = corpus()


def _goldens() -> dict:
    return json.loads(GOLDENS.read_text(encoding="utf-8"))


def test_corpus_is_the_expected_size() -> None:
    assert len(CORPUS) >= 26, [k for k, _, _ in CORPUS]


def test_goldens_cover_exactly_the_corpus() -> None:
    assert sorted(_goldens()) == [k for k, _, _ in CORPUS]


@pytest.mark.parametrize("key,source,fn", CORPUS, ids=[k for k, _, _ in CORPUS])
def test_extractor_matches_golden(key: str, source: str, fn: str) -> None:
    assert dump(extract_graph_from_source(source, fn)) == _goldens()[key]
```

`plr-sema/tests/` has no `__init__.py` or `conftest.py`, so pytest's default `prepend` import mode puts that directory on `sys.path` and `from _extract_corpus import …` resolves.

- [ ] **Step 4: Run it; expect failure**

Run: `uv run --no-sync pytest plr-sema/tests/test_extract_parity.py -q`
Expected: FAIL, `FileNotFoundError` for `extract_goldens.json`.

- [ ] **Step 5: Capture goldens and run again**

Run: `uv run --no-sync python3 plr-sema/scripts/capture_extract_goldens.py && uv run --no-sync pytest plr-sema/tests/test_extract_parity.py -q`
Expected: the script logs `wrote N goldens (26 non-null)`; the tests PASS.

- [ ] **Step 6: Negative control (the test must be able to fail)**

Edit one value in `extract_goldens.json` by hand (e.g. change one `"line_number"`), run the test, and confirm exactly that key fails. Then `git checkout -- plr-sema/tests/fixtures/extract_goldens.json` (or re-run the capture script) and confirm it passes again.

- [ ] **Step 7: Commit**

```bash
git add plr-sema/tests/_extract_corpus.py plr-sema/scripts/capture_extract_goldens.py \
  plr-sema/tests/fixtures/extract_goldens.json plr-sema/tests/test_extract_parity.py
git commit -m "test(plr-sema): pin extractor output with parity goldens before the move (261002_sema-web-integration)"
```

---

### Task 2: Move the graph models, resource hierarchy and type inspection into `plr_sema.graph`

**Files:**
- Create: `plr-sema/src/plr_sema/graph/__init__.py`
- Move: `praxis/common/type_inspection.py` → `plr-sema/src/plr_sema/graph/type_inspection.py` (then a shim at the old path)
- Move: `praxis/backend/utils/plr_static_analysis/resource_hierarchy.py` → `plr-sema/src/plr_sema/graph/resource_hierarchy.py` (then a shim)
- Create: `plr-sema/src/plr_sema/graph/models.py` (header + `models.py` lines 504–671)
- Modify: `praxis/backend/utils/plr_static_analysis/models.py` (truncate at 503, append re-export)
- Modify: `plr-sema/pyproject.toml`, root `pyproject.toml`
- Test: `plr-sema/tests/test_graph_shims.py`

**Interfaces:**
- Consumes: Task 1 goldens.
- Produces: `plr_sema.graph.models.{GraphNodeType, PreconditionType, OperationNode, ResourceNode, StatePrecondition, ProtocolComputationGraph}`; `plr_sema.graph.resource_hierarchy.{DeckLayoutType, get_parental_chain, …}`; `plr_sema.graph.type_inspection.{PLR_MACHINE_FRONTEND_TYPES, PLR_RESOURCE_TYPES, extract_resource_types, get_element_type, is_container_type, is_pylabrobot_resource, serialize_type_hint, …}`. The praxis import paths keep working and return the **same objects**.

- [ ] **Step 1: Write the failing identity test**

`plr-sema/tests/test_graph_shims.py`:

```python
"""praxis re-export shims return the SAME objects as plr_sema.graph (spec 261002 §4).

Identity, not equality: isinstance checks across praxis consumers depend on it.
"""

from __future__ import annotations

import importlib

import pytest

pytest.importorskip("pydantic")

GRAPH_NAMES = (
    "GraphNodeType",
    "PreconditionType",
    "OperationNode",
    "ResourceNode",
    "StatePrecondition",
    "ProtocolComputationGraph",
)


def _assert_reexports_everything(old_name: str, new_name: str) -> None:
    old = importlib.import_module(old_name)
    new = importlib.import_module(new_name)
    public = [n for n in vars(new) if not n.startswith("_")]
    wrong = [n for n in public if getattr(old, n, None) is not getattr(new, n)]
    assert public, f"{new_name} exports nothing"
    assert wrong == [], f"{old_name} does not re-export {wrong} from {new_name}"


def test_graph_models_are_identical() -> None:
    old = importlib.import_module("praxis.backend.utils.plr_static_analysis.models")
    new = importlib.import_module("plr_sema.graph.models")
    for name in GRAPH_NAMES:
        assert getattr(old, name) is getattr(new, name), name


def test_resource_hierarchy_shim() -> None:
    _assert_reexports_everything(
        "praxis.backend.utils.plr_static_analysis.resource_hierarchy",
        "plr_sema.graph.resource_hierarchy",
    )


def test_type_inspection_shim() -> None:
    _assert_reexports_everything("praxis.common.type_inspection", "plr_sema.graph.type_inspection")


def test_backend_type_inspection_still_resolves() -> None:
    # praxis/backend/utils/type_inspection.py re-imports from praxis.common.type_inspection.
    backend = importlib.import_module("praxis.backend.utils.type_inspection")
    new = importlib.import_module("plr_sema.graph.type_inspection")
    assert backend.extract_resource_types is new.extract_resource_types
```

- [ ] **Step 2: Run it; expect failure**

Run: `uv run --no-sync pytest plr-sema/tests/test_graph_shims.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'plr_sema.graph'`.

- [ ] **Step 3: Move the two whole files and write their shims**

```bash
mkdir -p plr-sema/src/plr_sema/graph
git mv praxis/common/type_inspection.py plr-sema/src/plr_sema/graph/type_inspection.py
git mv praxis/backend/utils/plr_static_analysis/resource_hierarchy.py plr-sema/src/plr_sema/graph/resource_hierarchy.py
```

`plr-sema/src/plr_sema/graph/__init__.py`:

```python
"""plr_sema.graph: the protocol computation-graph data model (pydantic).

Moved from praxis by spec 261002 Slice 1; praxis keeps re-export shims at the
old paths. Requires the ``extract`` extra (pydantic). Never imported by
``plr_sema.check`` -- that subtree reads the stdlib mirror
``plr_sema.check.graph`` instead.
"""
```

`praxis/common/type_inspection.py` (new, shim):

```python
"""Re-export shim: moved to ``plr_sema.graph.type_inspection`` (spec 261002 Slice 1)."""

from plr_sema.graph.type_inspection import *  # noqa: F401,F403
```

`praxis/backend/utils/plr_static_analysis/resource_hierarchy.py` (new, shim):

```python
"""Re-export shim: moved to ``plr_sema.graph.resource_hierarchy`` (spec 261002 Slice 1)."""

from plr_sema.graph.resource_hierarchy import *  # noqa: F401,F403
```

(No consumer imports an underscore-prefixed name from either module; verified with an `rg` over every `from … import` of them.)

- [ ] **Step 4: Split `models.py`**

```bash
M=praxis/backend/utils/plr_static_analysis/models.py
N=plr-sema/src/plr_sema/graph/models.py
cat > "$N" <<'PY'
"""plr_sema.graph.models: the protocol computation-graph models.

Moved verbatim from ``praxis/backend/utils/plr_static_analysis/models.py``
lines 504-671 (at e06ab3b1) by spec 261002 Slice 1; praxis re-exports them.
``plr_sema.check.graph`` is the stdlib mirror of these classes and
``tests/test_check_graph_mirror_drift.py`` keeps the two in step.
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

PY
sed -n '499,671p' "$M" >> "$N"
head -n 498 "$M" > "$M.new" && mv "$M.new" "$M"
cat >> "$M" <<'PY'
# =============================================================================
# Computation Graph Models -- moved to plr_sema.graph.models (spec 261002 Slice 1)
# =============================================================================

from plr_sema.graph.models import (  # noqa: E402,F401  re-export
  GraphNodeType,
  OperationNode,
  PreconditionType,
  ProtocolComputationGraph,
  ResourceNode,
  StatePrecondition,
)
PY
```

Then read the two boundaries by eye: `tail -n 20 "$M"` and `sed -n '1,25p' "$N"`. In the original, line 497 is the `}` closing `FRONTEND_TO_BACKEND_MAP`'s dict, 498 is blank, 499–501 are the `# ===` / `# Computation Graph Models` / `# ===` banner, 502–503 are blank, and 504 is `class GraphNodeType`. After the split, `$M` ends with `}`, one blank line and the new re-export banner; `$N` has the original banner exactly once, followed by `class GraphNodeType`. The graph section references no name defined earlier in `models.py` (verified), so nothing else needs to move.

- [ ] **Step 5: Declare the dependency in both pyprojects**

In `plr-sema/pyproject.toml`, after `dependencies = []`:

```toml
[project.optional-dependencies]
extract = ["libcst>=1.1.0", "pydantic>=2.0.0"]
```

In the root `pyproject.toml`: add `"plr-sema[extract]",` to `[project].dependencies` (after `"libcst>=1.1.0",`), and under `[tool.uv.sources]` add:

```toml
plr-sema = { workspace = true }
```

Run: `uv lock && uv sync --all-packages` (`uv.lock` is gitignored in this worktree; do not commit it).

- [ ] **Step 6: Run the identity test, the goldens and the praxis consumers**

```bash
uv run --no-sync pytest -q plr-sema/tests/test_graph_shims.py plr-sema/tests/test_extract_parity.py \
  plr-sema/tests/test_import_boundary.py plr-sema/tests/test_hand_maintained_ratchet.py \
  tests/utils/test_resource_hierarchy.py tests/utils/test_type_inspection.py \
  tests/common/test_type_inspection_plr_matching.py tests/utils/test_computation_graph.py \
  tests/core/test_precondition_resolver.py
```

Expected: all PASS. `test_no_praxis_imports_under_src` must stay green (neither moved file imports praxis: `resource_hierarchy` imports only `enum` and `pydantic`, `type_inspection` only stdlib).

- [ ] **Step 7: Commit**

```bash
git add plr-sema/src/plr_sema/graph/ praxis/common/type_inspection.py \
  praxis/backend/utils/plr_static_analysis/resource_hierarchy.py \
  praxis/backend/utils/plr_static_analysis/models.py plr-sema/pyproject.toml pyproject.toml \
  plr-sema/tests/test_graph_shims.py
git commit -m "refactor: move graph models, resource hierarchy and type inspection into plr_sema.graph behind praxis shims (261002_sema-web-integration)"
```

---

### Task 3: Hold the `check/` boundary

**Files:**
- Modify: `plr-sema/tests/test_import_boundary.py`
- Modify: `plr-sema/tests/test_check_graph_mirror_drift.py:52-70` and its skip message at `:93-97`
- Modify: `plr-sema/src/plr_sema/check/graph.py` module docstring (lines 1–20)

**Interfaces:**
- Consumes: `plr_sema.graph.models` (Task 2).

- [ ] **Step 1: Add the two boundary tests**

Append to `plr-sema/tests/test_import_boundary.py`:

```python
def test_no_pydantic_import_under_check() -> None:
    """Spec 261002 §3: `check/` stays pydantic-free now that plr-sema owns the
    pydantic graph models in `plr_sema.graph`. `check/` reads the stdlib
    mirror `check/graph.py`; the mirror-drift test keeps the two in step."""
    offenders: list[str] = []
    for path in sorted(CHECK_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            for import_node, top in _iter_imports(node):
                if top == "pydantic":
                    offenders.append(f"{path}: {ast.unparse(import_node)}")
    assert offenders == [], f"Spec violation: {offenders}"


def test_base_import_loads_no_optional_dependency() -> None:
    """Spec 261002 §4: `import plr_sema` must not pull in the `extract` extra
    (or PLR), so a base install and Pyodide-without-libcst both work."""
    code = (
        "import sys, plr_sema\n"
        "bad = sorted(m for m in ('libcst', 'pydantic', 'pylabrobot') if m in sys.modules)\n"
        "print(bad)\n"
        "raise SystemExit(1 if bad else 0)\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 2: Run them; then prove each can fail**

Run: `uv run --no-sync pytest plr-sema/tests/test_import_boundary.py -q`
Expected: PASS. If `test_base_import_loads_no_optional_dependency` FAILS, stop: some existing `check/` or `verdict.py` import already loads pydantic, and the spec's premise is wrong. Report which module does it rather than working around it.

Negative control: add `import pydantic  # noqa` as the last line of `plr-sema/src/plr_sema/check/cache.py`, re-run, confirm both new tests FAIL, then `git checkout -- plr-sema/src/plr_sema/check/cache.py`.

- [ ] **Step 3: Repoint the mirror-drift test at `plr_sema.graph.models`**

In `plr-sema/tests/test_check_graph_mirror_drift.py` replace lines 54–70 (the `try:` block importing from `praxis.backend.utils.plr_static_analysis.models`) with:

```python
try:
    from plr_sema.graph.models import OperationNode as UpstreamOperationNode
    from plr_sema.graph.models import ProtocolComputationGraph as UpstreamProtocolComputationGraph
    from plr_sema.graph.models import ResourceNode as UpstreamResourceNode
except ImportError as exc:  # pragma: no cover - environment-dependent (no `extract` extra)
    UpstreamOperationNode = None
    UpstreamResourceNode = None
    UpstreamProtocolComputationGraph = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None
```

and change the skip text to `f"plr_sema.graph not importable (install plr-sema[extract]) ({_IMPORT_ERROR!r}) -- "`. In the module docstring, replace the sentence that names `praxis.backend.utils.plr_static_analysis.models` as the comparison target with: "Since spec 261002 Slice 1 the pydantic side is `plr_sema.graph.models` (moved from praxis), so both halves of the seam live in this package."

- [ ] **Step 4: Update the `check/graph.py` docstring**

In `plr-sema/src/plr_sema/check/graph.py` lines 5–10, replace the parenthetical path ``praxis/backend/utils/plr_static_analysis/models.py:524-662`` with ``plr_sema/graph/models.py`` and the clause "are pydantic ``BaseModel``s under ``praxis.*`` -- forbidden under ``check/`` by §1.3 (no ``praxis`` import under ``src/plr_sema/``) and unmovable per §1.1 (round 1 moves nothing out of ``praxis/``)" with "are pydantic ``BaseModel``s -- forbidden under ``check/`` (no ``pydantic`` import; spec 261002 §3, enforced by ``test_no_pydantic_import_under_check``)". Leave the rest of the docstring alone.

- [ ] **Step 5: Run and commit**

Run: `uv run --no-sync pytest -q plr-sema/tests/test_import_boundary.py plr-sema/tests/test_check_graph_mirror_drift.py plr-sema/tests/test_check_graph.py plr-sema/tests/test_spec_lint.py`
Expected: PASS (mirror-drift now runs against `plr_sema.graph.models`, not skipped).

```bash
git add plr-sema/tests/test_import_boundary.py plr-sema/tests/test_check_graph_mirror_drift.py \
  plr-sema/src/plr_sema/check/graph.py
git commit -m "test(plr-sema): ban pydantic under check/, keep base import dependency-free, mirror-drift against plr_sema.graph (261002_sema-web-integration)"
```

---

### Task 4: Move the extractor into `plr_sema.extract`

**Files:**
- Move: `praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py` → `plr-sema/src/plr_sema/extract/computation_graph_extractor.py` (then a shim)
- Modify: `plr-sema/src/plr_sema/extract/__init__.py` (docstring)
- Modify: `plr-sema/tests/test_extract_parity.py` (import), `plr-sema/tests/test_graph_shims.py` (one more identity test)

**Interfaces:**
- Produces: `plr_sema.extract.computation_graph_extractor.extract_graph_from_source(source, function_name, module_name="protocol", deck_layout_type=DeckLayoutType.CARRIER_BASED) -> ProtocolComputationGraph | None` and `extract_graph_from_function(function_node, module_name, parameter_types=None, deck_layout_type=DeckLayoutType.CARRIER_BASED, *, _wrapper=None) -> ProtocolComputationGraph` — unchanged signatures.

- [ ] **Step 1: Add the failing identity test**

Append to `plr-sema/tests/test_graph_shims.py`:

```python
def test_extractor_shim() -> None:
    _assert_reexports_everything(
        "praxis.backend.utils.plr_static_analysis.visitors.computation_graph_extractor",
        "plr_sema.extract.computation_graph_extractor",
    )
```

Run: `uv run --no-sync pytest plr-sema/tests/test_graph_shims.py::test_extractor_shim -q` → FAIL (`ModuleNotFoundError`).

- [ ] **Step 2: Move it and rewrite its three import lines**

```bash
git mv praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py \
  plr-sema/src/plr_sema/extract/computation_graph_extractor.py
F=plr-sema/src/plr_sema/extract/computation_graph_extractor.py
sed -i \
  -e 's/^from praxis\.backend\.utils\.plr_static_analysis\.models import (/from plr_sema.graph.models import (/' \
  -e 's/^from praxis\.backend\.utils\.plr_static_analysis\.resource_hierarchy import (/from plr_sema.graph.resource_hierarchy import (/' \
  -e 's/^from praxis\.common\.type_inspection import (/from plr_sema.graph.type_inspection import (/' "$F"
grep -n "praxis" "$F"
```

Expected: the `grep` prints only docstring/comment mentions, no `import` line. The import block keeps its line count, so every line number in the file is unchanged.

Shim at the old path, `praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py`:

```python
"""Re-export shim: moved to ``plr_sema.extract.computation_graph_extractor`` (spec 261002 Slice 1)."""

from plr_sema.extract.computation_graph_extractor import *  # noqa: F401,F403
```

(No caller imports an underscore name from the extractor; verified.)

- [ ] **Step 3: Update `extract/__init__.py`'s docstring**

Replace the docstring of `plr-sema/src/plr_sema/extract/__init__.py` with:

```python
"""plr_sema.extract: source -> ProtocolComputationGraph (libcst).

Since spec 261002 Slice 1 this is the one extractor: it was moved here from
``praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py``,
which is now a re-export shim. Requires the ``extract`` extra. Import the
functions from ``plr_sema.extract.computation_graph_extractor``; this package
``__init__`` stays import-free so ``import plr_sema.extract`` does not load libcst.
"""
```

Keep `from __future__ import annotations` and `__all__: list[str] = []`.

- [ ] **Step 4: Point the parity test at the new home**

In `plr-sema/tests/test_extract_parity.py` change the import to `from plr_sema.extract.computation_graph_extractor import extract_graph_from_source  # noqa: E402`.

- [ ] **Step 5: Run and commit**

```bash
uv run --no-sync pytest -q plr-sema/tests/test_graph_shims.py plr-sema/tests/test_extract_parity.py \
  plr-sema/tests/test_import_boundary.py plr-sema/tests/test_tier2.py plr-sema/tests/test_ir.py \
  tests/utils/test_computation_graph.py tests/core/test_precondition_resolver.py
```

Expected: PASS, goldens byte-identical. Also run the discovery path that uses the extractor through the shim: `uv run --no-sync pytest -q tests -k protocol_discovery` (a `-k` selector, not the whole suite).

```bash
git add plr-sema/src/plr_sema/extract/ \
  praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py \
  plr-sema/tests/test_extract_parity.py plr-sema/tests/test_graph_shims.py
git commit -m "refactor: move the computation-graph extractor into plr_sema.extract behind a praxis shim (261002_sema-web-integration)"
```

---

### Task 5: Contracts loader, deterministic gzip, resolver chain

**Files:**
- Create: `plr-sema/src/plr_sema/contracts.py`
- Create: `plr-sema/tests/test_contracts.py`
- Modify: root `pyproject.toml` (add `[tool.plr-sema]`)

**Interfaces:**
- Produces:
  - `class ContractsError(ValueError)`
  - `@dataclass(frozen=True) class Contracts: json_text: str; sha256: str; path: Path`
  - `canonical_json(obj) -> str`
  - `load_contracts(path) -> Contracts` (raises `ContractsError`)
  - `build_gz(src, dst) -> Path`
  - `@dataclass(frozen=True) class ContractsSource: path: Path | None; layer: str`
  - `contracts_source(explicit=None, *, start=None) -> ContractsSource`
  - `ENV_VAR = "PLR_SEMA_CONTRACTS"`

- [ ] **Step 1: Write the failing tests**

`plr-sema/tests/test_contracts.py`:

```python
"""plr_sema.contracts (spec 261002 §7)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

from plr_sema.contracts import (
    ENV_VAR,
    ContractsError,
    build_gz,
    canonical_json,
    contracts_source,
    load_contracts,
)

REAL = Path(__file__).resolve().parents[1] / "data" / "derived_contracts.json"
TOY = {"b": [1, 2], "a": {"z": "ü", "y": None}}


@pytest.fixture
def toy_json(tmp_path: Path) -> Path:
    p = tmp_path / "c.json"
    p.write_text(json.dumps(TOY, indent=2), encoding="utf-8")
    return p


def test_json_and_gz_load_to_the_same_canonical_text(toy_json: Path, tmp_path: Path) -> None:
    gz = build_gz(toy_json, tmp_path / "c.json.gz")
    a, b = load_contracts(toy_json), load_contracts(gz)
    assert a.json_text == b.json_text == canonical_json(TOY)
    assert a.sha256 == b.sha256


def test_gzip_is_detected_by_magic_not_extension(toy_json: Path, tmp_path: Path) -> None:
    disguised = tmp_path / "contracts.json"
    disguised.write_bytes(gzip.compress(toy_json.read_bytes()))
    assert load_contracts(disguised).json_text == canonical_json(TOY)


def test_build_gz_is_byte_deterministic(toy_json: Path, tmp_path: Path) -> None:
    one = build_gz(toy_json, tmp_path / "1.gz").read_bytes()
    two = build_gz(toy_json, tmp_path / "2.gz").read_bytes()
    assert one == two


@pytest.mark.parametrize(
    "payload",
    [b"", b"{not json", b"\x1f\x8b\x08\x00truncated", b"[1, 2, 3]", b"\xff\xfe\x00bad"],
    ids=["empty", "bad-json", "truncated-gzip", "not-an-object", "not-utf8"],
)
def test_bad_files_raise_contracts_error(tmp_path: Path, payload: bytes) -> None:
    p = tmp_path / "bad.json"
    p.write_bytes(payload)
    with pytest.raises(ContractsError):
        load_contracts(p)


def test_missing_file_raises_contracts_error(tmp_path: Path) -> None:
    with pytest.raises(ContractsError):
        load_contracts(tmp_path / "absent.json")


def test_real_table_round_trips() -> None:
    c = load_contracts(REAL)
    assert json.loads(c.json_text) == json.loads(REAL.read_text(encoding="utf-8"))


def test_resolver_layers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    nested = tmp_path / "pkg" / "sub"
    nested.mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text('[tool.plr-sema]\ncontracts = "data/c.json"\n')
    (tmp_path / "pkg" / "pyproject.toml").write_text('[project]\nname = "pkg"\n')

    assert contracts_source("x.json", start=nested).layer == "argument"

    src = contracts_source(start=nested)  # walks past pkg/pyproject.toml (no table)
    assert src.layer == f"pyproject:{tmp_path / 'pyproject.toml'}"
    assert src.path == tmp_path / "data" / "c.json"

    monkeypatch.setenv(ENV_VAR, str(tmp_path / "env.json"))
    assert contracts_source(start=nested).layer == "env"
    for off in ("", "none", "NONE"):
        monkeypatch.setenv(ENV_VAR, off)
        assert contracts_source(start=nested) == contracts_source(start=nested)
        assert contracts_source(start=nested).path is None
        assert contracts_source(start=nested).layer == "env:disabled"


def test_resolver_none_when_nothing_configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    src = contracts_source(start=tmp_path)
    assert (src.path, src.layer) == (None, "none")


def test_malformed_pyproject_fails_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    (tmp_path / "pyproject.toml").write_text("[tool.plr-sema\ncontracts = ")
    with pytest.raises(ContractsError):
        contracts_source(start=tmp_path)


def test_non_string_contracts_value_fails_loudly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_VAR, raising=False)
    (tmp_path / "pyproject.toml").write_text("[tool.plr-sema]\ncontracts = 3\n")
    with pytest.raises(ContractsError):
        contracts_source(start=tmp_path)
```

Note: `test_resolver_layers` writes a `pyproject.toml` under `tmp_path`; pytest's `tmp_path` lives outside the repo, so the walk-up cannot reach the repo's own `pyproject.toml` before finding the toy one.

Run: `uv run --no-sync pytest plr-sema/tests/test_contracts.py -q` → FAIL (`ModuleNotFoundError: plr_sema.contracts`).

- [ ] **Step 2: Implement `contracts.py`**

`plr-sema/src/plr_sema/contracts.py`:

```python
"""plr_sema.contracts: load the derived contract table and resolve where it lives.

Stdlib only (spec 261002 §7). The committed source of truth is the pretty
``plr-sema/data/derived_contracts.json``; ``build_gz`` makes the compact,
byte-deterministic ``.json.gz`` that browser/backend surfaces ship, and that
file is a build artifact, never committed.

Resolution (no default path in library code): explicit argument >
``$PLR_SEMA_CONTRACTS`` (empty or ``none`` disables) > the first
``pyproject.toml`` walking up from ``start`` that has
``[tool.plr-sema] contracts`` (relative to that file) > unavailable.
``contracts_source()`` reports which layer decided.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: the pyproject layer is skipped
    tomllib = None  # type: ignore[assignment]

ENV_VAR = "PLR_SEMA_CONTRACTS"
_GZIP_MAGIC = b"\x1f\x8b"


class ContractsError(ValueError):
    """The contract table, or the config naming it, could not be read."""


@dataclass(frozen=True)
class Contracts:
    json_text: str  # canonical compact JSON; what check_graph receives
    sha256: str  # sha256 of json_text: identical for .json and .json.gz
    path: Path


@dataclass(frozen=True)
class ContractsSource:
    path: Path | None
    layer: str  # "argument" | "env" | "env:disabled" | "pyproject:<file>" | "none"


def canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def load_contracts(path: str | os.PathLike[str]) -> Contracts:
    p = Path(path)
    try:
        raw = p.read_bytes()
        if raw[:2] == _GZIP_MAGIC:
            raw = gzip.decompress(raw)
        obj = json.loads(raw.decode("utf-8"))
    except (OSError, EOFError, gzip.BadGzipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractsError(f"cannot load contracts from {p}: {exc}") from exc
    if not isinstance(obj, dict):
        raise ContractsError(f"contracts at {p} are not a JSON object")
    text = canonical_json(obj)
    return Contracts(json_text=text, sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(), path=p)


def build_gz(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> Path:
    contracts = load_contracts(src)
    data = gzip.compress(contracts.json_text.encode("utf-8"), compresslevel=9, mtime=0)
    out = Path(dst)
    tmp = out.with_name(f"{out.name}.tmp{os.getpid()}")
    tmp.write_bytes(data)
    os.replace(tmp, out)
    return out


def contracts_source(
    explicit: str | os.PathLike[str] | None = None, *, start: str | os.PathLike[str] | None = None
) -> ContractsSource:
    if explicit is not None:
        return ContractsSource(Path(explicit), "argument")
    env = os.environ.get(ENV_VAR)
    if env is not None:
        if env.strip().lower() in ("", "none"):
            return ContractsSource(None, "env:disabled")
        return ContractsSource(Path(env), "env")
    found = _from_pyproject(Path.cwd() if start is None else Path(start))
    return found if found is not None else ContractsSource(None, "none")


def _from_pyproject(start: Path) -> ContractsSource | None:
    if tomllib is None:
        return None
    here = start.resolve()
    for directory in (here, *here.parents):
        candidate = directory / "pyproject.toml"
        if not candidate.is_file():
            continue
        try:
            data = tomllib.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ContractsError(f"malformed {candidate}: {exc}") from exc
        value = data.get("tool", {}).get("plr-sema", {}).get("contracts")
        if value is None:
            continue
        if not isinstance(value, str) or not value:
            raise ContractsError(f"{candidate}: [tool.plr-sema] contracts must be a non-empty string")
        return ContractsSource(directory / value, f"pyproject:{candidate}")
    return None
```

- [ ] **Step 3: Configure this repo**

Append to the root `pyproject.toml`:

```toml
[tool.plr-sema]
# spec 261002 §7: where `python -m plr_sema check` finds the contract table in this repo.
contracts = "plr-sema/data/derived_contracts.json"
```

- [ ] **Step 4: Run and commit**

Run: `uv run --no-sync pytest plr-sema/tests/test_contracts.py plr-sema/tests/test_import_boundary.py -q` → PASS.

```bash
git add plr-sema/src/plr_sema/contracts.py plr-sema/tests/test_contracts.py pyproject.toml
git commit -m "feat(plr-sema): contracts loader (.json/.json.gz), deterministic build_gz, resolver chain (261002_sema-web-integration)"
```

---

### Task 6: `analyze()`, `NotAnalyzed`, `VerdictKey`

**Files:**
- Create: `plr-sema/src/plr_sema/analysis.py`
- Modify: `plr-sema/src/plr_sema/__init__.py` (lazy exports)
- Create: `plr-sema/tests/test_analysis.py`

**Interfaces:**
- Consumes: `load_contracts`, `contracts_source`, `Contracts`, `ContractsError` (Task 5); `extract_graph_from_function` (Task 4); `DeckLayoutType` (Task 2); `check_graph`, `AnalysisReport`, `SCHEMA_VERSION` (existing, `plr_sema.check` / `plr_sema.verdict`).
- Produces:
  - `class NotAnalyzedReason(str, Enum)`: `SYNTAX_ERROR`, `FUNCTION_NOT_FOUND`, `AMBIGUOUS_FUNCTION`, `EXTRACT_FAILED`, `CHECK_FAILED`, `EXTRACTOR_UNAVAILABLE`, `CONTRACTS_UNAVAILABLE` (values are the lower-case names)
  - `@dataclass(frozen=True) class VerdictKey: source_sha256: str; contracts_sha256: str; analyzer_sha256: str; schema_version: int` with `as_str() -> str`
  - `@dataclass(frozen=True) class Analyzed: report: AnalysisReport; key: VerdictKey; function_name: str; op_lines: dict[str, int]`
  - `@dataclass(frozen=True) class NotAnalyzed: reason: NotAnalyzedReason; detail: str; function_name: str | None = None`
  - `AnalysisOutcome = Analyzed | NotAnalyzed`
  - `analyze(source: str, function_name: str | None = None, *, contracts: Contracts | None = None, deck_layout_type=None, module_name: str = "protocol") -> AnalysisOutcome`
  - `analyzer_sha256() -> str`
  - Top-level lazy names on `plr_sema`: `analyze`, `Analyzed`, `NotAnalyzed`, `NotAnalyzedReason`, `VerdictKey`.

- [ ] **Step 1: Write the failing tests**

`plr-sema/tests/test_analysis.py`:

```python
"""plr_sema.analyze (spec 261002 §5)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("libcst")
pytest.importorskip("pydantic")

from plr_sema import Verdict  # noqa: E402
from plr_sema.analysis import Analyzed, NotAnalyzed, NotAnalyzedReason, analyze  # noqa: E402
from plr_sema.contracts import ENV_VAR, load_contracts  # noqa: E402

PKG = Path(__file__).resolve().parents[1]
FIX = PKG / "eval" / "fixtures" / "regions"
WILL_FAIL_SRC = (FIX / "for_pickup_no_drop_raises.py").read_text(encoding="utf-8")
CLEAN_SRC = (FIX / "straightline_clean.py").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def contracts():
    return load_contracts(PKG / "data" / "derived_contracts.json")


def test_will_fail_fixture_is_analyzed_as_will_fail(contracts) -> None:
    out = analyze(WILL_FAIL_SRC, "protocol", contracts=contracts)
    assert isinstance(out, Analyzed)
    assert out.report.verdict is Verdict.WILL_FAIL
    assert out.function_name == "protocol"
    assert all(isinstance(v, int) and v > 0 for v in out.op_lines.values())
    assert {f.operation_id for f in out.report.findings} <= set(out.op_lines)


def test_clean_fixture_has_no_will_fail(contracts) -> None:
    out = analyze(CLEAN_SRC, "protocol", contracts=contracts)
    assert isinstance(out, Analyzed)
    assert out.report.verdict is not Verdict.WILL_FAIL


def test_function_name_defaults_to_the_only_top_level_def(contracts) -> None:
    out = analyze(CLEAN_SRC, contracts=contracts)
    assert isinstance(out, Analyzed) and out.function_name == "protocol"


@pytest.mark.parametrize(
    "source,fn,reason",
    [
        ("def f(:\n", "f", NotAnalyzedReason.SYNTAX_ERROR),
        ("import os\n", None, NotAnalyzedReason.FUNCTION_NOT_FOUND),
        ("def a(): pass\n", "b", NotAnalyzedReason.FUNCTION_NOT_FOUND),
        ("def a(): pass\ndef b(): pass\n", None, NotAnalyzedReason.AMBIGUOUS_FUNCTION),
        ("def a(): pass\ndef a(): pass\n", "a", NotAnalyzedReason.AMBIGUOUS_FUNCTION),
        ("", None, NotAnalyzedReason.FUNCTION_NOT_FOUND),
    ],
    ids=["syntax", "no-defs", "wrong-name", "two-defs-no-name", "duplicate-name", "empty"],
)
def test_not_analyzed_reasons(contracts, source, fn, reason) -> None:
    out = analyze(source, fn, contracts=contracts)
    assert isinstance(out, NotAnalyzed), out
    assert out.reason is reason
    assert out.detail


def test_nested_def_with_the_target_name_is_not_picked(contracts) -> None:
    src = "def outer():\n    def protocol():\n        pass\n"
    out = analyze(src, "protocol", contracts=contracts)
    assert isinstance(out, NotAnalyzed) and out.reason is NotAnalyzedReason.FUNCTION_NOT_FOUND


def test_extractor_crash_is_extract_failed(contracts, monkeypatch) -> None:
    import plr_sema.extract.computation_graph_extractor as ex

    def boom(*a, **k):
        raise RuntimeError("synthetic extractor crash")

    monkeypatch.setattr(ex, "extract_graph_from_function", boom)
    out = analyze(CLEAN_SRC, "protocol", contracts=contracts)
    assert isinstance(out, NotAnalyzed) and out.reason is NotAnalyzedReason.EXTRACT_FAILED
    assert "RuntimeError" in out.detail


def test_odd_but_valid_calls_never_raise(contracts) -> None:
    src = (
        "async def protocol(lh, plate, args, kw):\n"
        "    await lh.aspirate(*args, **kw)\n"
        "    await (lambda: lh)().dispense(plate['A1'], [10])\n"
        "    getattr(lh, 'drop_tips')()\n"
    )
    out = analyze(src, "protocol", contracts=contracts)
    assert isinstance(out, (Analyzed, NotAnalyzed))
    if isinstance(out, NotAnalyzed):
        assert out.reason in (NotAnalyzedReason.EXTRACT_FAILED, NotAnalyzedReason.CHECK_FAILED)


def test_check_crash_is_check_failed(contracts, monkeypatch) -> None:
    import plr_sema.analysis as an

    def boom(*a, **k):
        raise KeyError("synthetic check crash")

    monkeypatch.setattr(an, "check_graph", boom)
    out = analyze(CLEAN_SRC, "protocol", contracts=contracts)
    assert isinstance(out, NotAnalyzed) and out.reason is NotAnalyzedReason.CHECK_FAILED


def test_contracts_unavailable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(ENV_VAR, "none")
    out = analyze(CLEAN_SRC, "protocol")
    assert isinstance(out, NotAnalyzed) and out.reason is NotAnalyzedReason.CONTRACTS_UNAVAILABLE
    bad = tmp_path / "c.json.gz"
    bad.write_bytes(b"\x1f\x8b\x08\x00truncated")
    monkeypatch.setenv(ENV_VAR, str(bad))
    out = analyze(CLEAN_SRC, "protocol")
    assert isinstance(out, NotAnalyzed) and out.reason is NotAnalyzedReason.CONTRACTS_UNAVAILABLE


def test_extractor_unavailable_on_a_base_install() -> None:
    code = (
        "import sys\n"
        "sys.modules['libcst'] = None\n"  # makes `import libcst` raise ImportError
        "import plr_sema\n"
        "out = plr_sema.analyze('def f(): pass\\n', 'f')\n"
        "print(type(out).__name__, out.reason.value)\n"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["NotAnalyzed", "extractor_unavailable"]


def test_lazy_top_level_names() -> None:
    import plr_sema

    assert plr_sema.analyze is analyze
    assert plr_sema.NotAnalyzedReason is NotAnalyzedReason


# ---- VerdictKey -------------------------------------------------------------

TWO_FNS = (
    "def protocol(lh, plate):\n"
    "    lh.aspirate(plate['A1'], [10])\n"
    "\n"
    "\n"
    "def helper():\n"
    "    return 1\n"
)


def _key(src: str, contracts, fn: str = "protocol"):
    out = analyze(src, fn, contracts=contracts)
    assert isinstance(out, Analyzed), out
    return out.key


def test_key_is_stable(contracts) -> None:
    assert _key(TWO_FNS, contracts) == _key(TWO_FNS, contracts)


def test_key_changes_when_the_function_changes(contracts) -> None:
    edited = TWO_FNS.replace("[10]", "[20]")
    assert _key(TWO_FNS, contracts).source_sha256 != _key(edited, contracts).source_sha256


def test_key_ignores_sibling_functions_and_spacing(contracts) -> None:
    sibling = TWO_FNS.replace("return 1", "return 2")
    spaced = "# header comment\n\n\n" + TWO_FNS.replace("\n\n\ndef helper", "\n\n\n\n# note\ndef helper")
    base = _key(TWO_FNS, contracts).source_sha256
    assert _key(sibling, contracts).source_sha256 == base
    assert _key(spaced, contracts).source_sha256 == base


def test_key_same_for_json_and_gz_contracts(contracts, tmp_path) -> None:
    from plr_sema.contracts import build_gz

    gz = load_contracts(build_gz(PKG / "data" / "derived_contracts.json", tmp_path / "c.json.gz"))
    assert _key(TWO_FNS, contracts) == _key(TWO_FNS, gz)


def test_key_string_form(contracts) -> None:
    k = _key(TWO_FNS, contracts)
    assert k.as_str() == f"v{k.schema_version}:{k.source_sha256}:{k.contracts_sha256}:{k.analyzer_sha256}"
    assert all(len(h) == 64 for h in (k.source_sha256, k.contracts_sha256, k.analyzer_sha256))
```

Run: `uv run --no-sync pytest plr-sema/tests/test_analysis.py -q` → FAIL (`ModuleNotFoundError: plr_sema.analysis`).

- [ ] **Step 2: Implement `analysis.py`**

`plr-sema/src/plr_sema/analysis.py`:

```python
"""plr_sema.analysis: the one analysis seam every surface calls (spec 261002 §5).

``analyze(source, function_name)`` extracts the protocol function's graph and
checks it against the contract table. It never raises for a bad protocol: it
returns ``Analyzed`` or a typed ``NotAnalyzed``. A ``NotAnalyzed`` is never a
SAFE verdict, on any surface.

Importable on a base install: libcst, pydantic and the extractor are imported
inside ``analyze``, so without the ``extract`` extra it returns
``NotAnalyzed(EXTRACTOR_UNAVAILABLE)`` instead of raising ``ImportError``.
"""

from __future__ import annotations

import enum
import functools
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from plr_sema.check import check_graph
from plr_sema.contracts import Contracts, ContractsError, contracts_source, load_contracts
from plr_sema.verdict import SCHEMA_VERSION, AnalysisReport


class NotAnalyzedReason(str, enum.Enum):
    SYNTAX_ERROR = "syntax_error"
    FUNCTION_NOT_FOUND = "function_not_found"
    AMBIGUOUS_FUNCTION = "ambiguous_function"
    EXTRACT_FAILED = "extract_failed"
    CHECK_FAILED = "check_failed"
    EXTRACTOR_UNAVAILABLE = "extractor_unavailable"
    CONTRACTS_UNAVAILABLE = "contracts_unavailable"


@dataclass(frozen=True)
class VerdictKey:
    source_sha256: str  # the analyzed function, without its leading blank lines/comments
    contracts_sha256: str  # Contracts.sha256 (same for .json and .json.gz)
    analyzer_sha256: str  # every plr_sema/**/*.py in the installed package
    schema_version: int  # plr_sema.verdict.SCHEMA_VERSION

    def as_str(self) -> str:
        return f"v{self.schema_version}:{self.source_sha256}:{self.contracts_sha256}:{self.analyzer_sha256}"


@dataclass(frozen=True)
class Analyzed:
    report: AnalysisReport
    key: VerdictKey
    function_name: str
    op_lines: dict[str, int]  # OperationNode.id -> line in `source`


@dataclass(frozen=True)
class NotAnalyzed:
    reason: NotAnalyzedReason
    detail: str
    function_name: str | None = None


AnalysisOutcome = Union[Analyzed, NotAnalyzed]


@functools.lru_cache(maxsize=1)
def analyzer_sha256() -> str:
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def analyze(
    source: str,
    function_name: str | None = None,
    *,
    contracts: Contracts | None = None,
    deck_layout_type=None,
    module_name: str = "protocol",
) -> AnalysisOutcome:
    R = NotAnalyzedReason
    try:
        import libcst as cst
        from libcst.metadata import MetadataWrapper

        from plr_sema.extract import computation_graph_extractor as extractor
        from plr_sema.graph.resource_hierarchy import DeckLayoutType
    except ImportError as exc:
        return NotAnalyzed(R.EXTRACTOR_UNAVAILABLE, f"install plr-sema[extract]: {exc}", function_name)

    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        return NotAnalyzed(R.SYNTAX_ERROR, str(exc), function_name)
    wrapper = MetadataWrapper(module)
    defs = [s for s in wrapper.module.body if isinstance(s, cst.FunctionDef)]
    names = [d.name.value for d in defs]

    if function_name is None:
        if not defs:
            return NotAnalyzed(R.FUNCTION_NOT_FOUND, "no top-level function in source")
        if len(defs) > 1:
            return NotAnalyzed(R.AMBIGUOUS_FUNCTION, f"several top-level functions {names}; pass function_name")
        target = defs[0]
    else:
        matches = [d for d in defs if d.name.value == function_name]
        if not matches:
            return NotAnalyzed(R.FUNCTION_NOT_FOUND, f"no top-level function {function_name!r} (found {names})", function_name)
        if len(matches) > 1:
            return NotAnalyzed(R.AMBIGUOUS_FUNCTION, f"{function_name!r} is defined {len(matches)} times", function_name)
        target = matches[0]
    name = target.name.value

    if contracts is None:
        where = contracts_source()
        if where.path is None:
            return NotAnalyzed(R.CONTRACTS_UNAVAILABLE, f"no contract table configured (layer: {where.layer})", name)
        try:
            contracts = load_contracts(where.path)
        except ContractsError as exc:
            return NotAnalyzed(R.CONTRACTS_UNAVAILABLE, str(exc), name)

    try:
        graph = extractor.extract_graph_from_function(
            target,
            module_name,
            deck_layout_type=deck_layout_type or DeckLayoutType.CARRIER_BASED,
            _wrapper=wrapper,
        )
    except Exception as exc:  # noqa: BLE001 -- an extractor crash is a typed outcome, never a traceback
        return NotAnalyzed(R.EXTRACT_FAILED, f"{type(exc).__name__}: {exc}", name)

    try:
        report = check_graph(json.dumps(graph.model_dump(mode="json")), contracts.json_text)
    except Exception as exc:  # noqa: BLE001 -- same rule for the checker
        return NotAnalyzed(R.CHECK_FAILED, f"{type(exc).__name__}: {exc}", name)

    function_source = wrapper.module.code_for_node(target.with_changes(leading_lines=()))
    key = VerdictKey(
        source_sha256=hashlib.sha256(function_source.encode("utf-8")).hexdigest(),
        contracts_sha256=contracts.sha256,
        analyzer_sha256=analyzer_sha256(),
        schema_version=SCHEMA_VERSION,
    )
    return Analyzed(
        report=report,
        key=key,
        function_name=name,
        op_lines={op.id: op.line_number for op in graph.operations},
    )
```

Notes for the implementer:
- `extract_graph_from_function` is called through the module (`extractor.extract_graph_from_function`) so the monkeypatch test in Step 1 works.
- `check_graph` is imported at module level in `analysis.py` (stdlib-only), so the `CHECK_FAILED` test patches `plr_sema.analysis.check_graph`.
- `typing.Union` keeps the module importable on Python 3.10.

- [ ] **Step 3: Add the lazy top-level names**

Replace the body of `plr-sema/src/plr_sema/__init__.py` after its docstring with:

```python
from plr_sema.check import check_graph
from plr_sema.verdict import AnalysisReport, Verdict

_LAZY = {
    "analyze": "plr_sema.analysis",
    "Analyzed": "plr_sema.analysis",
    "NotAnalyzed": "plr_sema.analysis",
    "NotAnalyzedReason": "plr_sema.analysis",
    "VerdictKey": "plr_sema.analysis",
}

__all__ = ["check_graph", "AnalysisReport", "Verdict", *_LAZY]


def __getattr__(name: str):
    # spec 261002 §4: lazy so `import plr_sema` never loads plr_sema.analysis's
    # contracts/tomllib machinery at import time; analysis itself defers libcst.
    if name in _LAZY:
        import importlib

        value = getattr(importlib.import_module(_LAZY[name]), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'plr_sema' has no attribute {name!r}")
```

Append one sentence to the existing docstring: "Since spec 261002 Slice 1 it also exposes ``analyze`` and its outcome types lazily (see ``__getattr__``)."

- [ ] **Step 4: Run and commit**

Run: `uv run --no-sync pytest -q plr-sema/tests/test_analysis.py plr-sema/tests/test_import_boundary.py`
Expected: PASS. If `test_odd_but_valid_calls_never_raise` shows the extractor raising, that is the intended `EXTRACT_FAILED` path, not a test failure.

```bash
git add plr-sema/src/plr_sema/analysis.py plr-sema/src/plr_sema/__init__.py plr-sema/tests/test_analysis.py
git commit -m "feat(plr-sema): analyze() seam with typed NotAnalyzed reasons and content-hash VerdictKey (261002_sema-web-integration)"
```

---

### Task 7: CLI `python -m plr_sema check`

**Files:**
- Create: `plr-sema/src/plr_sema/__main__.py`
- Create: `plr-sema/tests/test_cli.py`
- Create: `plr-sema/tests/fixtures/cli/check_json_shape.json` (snapshot, generated in Step 4)

**Interfaces:**
- Consumes: `analyze`, `Analyzed`, `NotAnalyzed` (Task 6); `load_contracts`, `contracts_source`, `ContractsError` (Task 5).
- Produces: `main(argv: list[str] | None = None) -> int`; exit codes 0 (analyzed, no WILL_FAIL), 1 (≥1 WILL_FAIL), 2 (not analyzed / usage / unreadable input). Multiple files: the worst code wins. `--json` prints one object: `{"results": [ {"file", "function", "outcome": "analyzed"|"not_analyzed", "verdict"?, "key"?, "findings"?, "reason"?, "detail"?} ], "exit_code": int}`.

- [ ] **Step 1: Write the failing tests**

`plr-sema/tests/test_cli.py`:

```python
"""`python -m plr_sema check` (spec 261002 §6)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("libcst")

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parent
FIX = PKG / "eval" / "fixtures" / "regions"
CONTRACTS = PKG / "data" / "derived_contracts.json"
SNAPSHOT = PKG / "tests" / "fixtures" / "cli" / "check_json_shape.json"


def run(*args: str, env_extra: dict | None = None):
    import os

    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(
        [sys.executable, "-m", "plr_sema", "check", *args],
        capture_output=True, text=True, cwd=REPO, env=env,
    )


def test_clean_protocol_exits_0() -> None:
    r = run(str(FIX / "straightline_clean.py"), "--contracts", str(CONTRACTS))
    assert r.returncode == 0, r.stdout + r.stderr


def test_will_fail_protocol_exits_1_and_names_the_line() -> None:
    r = run(str(FIX / "for_pickup_no_drop_raises.py"), "--contracts", str(CONTRACTS))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "will_fail" in r.stdout
    assert "for_pickup_no_drop_raises.py:" in r.stdout


def test_syntax_error_exits_2(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("def protocol(:\n")
    r = run(str(bad), "--contracts", str(CONTRACTS))
    assert r.returncode == 2 and "syntax_error" in r.stdout


def test_worst_exit_code_wins() -> None:
    r = run(str(FIX / "straightline_clean.py"), str(FIX / "for_pickup_no_drop_raises.py"),
            "--contracts", str(CONTRACTS))
    assert r.returncode == 1


def test_missing_and_non_utf8_files_exit_2(tmp_path: Path) -> None:
    latin = tmp_path / "latin.py"
    latin.write_bytes(b"def protocol():\n    x = '\xe9'\n")
    for path in (tmp_path / "absent.py", latin):
        r = run(str(path), "--contracts", str(CONTRACTS))
        assert r.returncode == 2, r.stdout + r.stderr
        assert "Traceback" not in r.stderr


def test_contracts_resolve_from_repo_pyproject(monkeypatch) -> None:
    # No --contracts: the root pyproject's [tool.plr-sema] table (cwd = repo root).
    monkeypatch.delenv("PLR_SEMA_CONTRACTS", raising=False)
    r = run(str(FIX / "straightline_clean.py"))
    assert r.returncode == 0, r.stdout + r.stderr


def test_contracts_disabled_exits_2() -> None:
    r = run(str(FIX / "straightline_clean.py"), env_extra={"PLR_SEMA_CONTRACTS": "none"})
    assert r.returncode == 2 and "contracts_unavailable" in r.stdout


def test_function_flag_and_ambiguity(tmp_path: Path) -> None:
    two = tmp_path / "two.py"
    two.write_text("def a(): pass\n\ndef b(): pass\n")
    assert run(str(two), "--contracts", str(CONTRACTS)).returncode == 2
    assert run(str(two), "--function", "a", "--contracts", str(CONTRACTS)).returncode == 0


def _shape(obj):
    if isinstance(obj, dict):
        return {k: _shape(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_shape(obj[0])] if obj else []
    return type(obj).__name__


def test_json_output_shape_is_stable() -> None:
    r = run(str(FIX / "for_pickup_no_drop_raises.py"), "--json", "--contracts", str(CONTRACTS))
    payload = json.loads(r.stdout)
    assert payload["exit_code"] == r.returncode == 1
    assert _shape(payload) == json.loads(SNAPSHOT.read_text(encoding="utf-8"))
```

Run: `uv run --no-sync pytest plr-sema/tests/test_cli.py -q` → FAIL (`No module named plr_sema.__main__`).

- [ ] **Step 2: Implement `__main__.py`**

`plr-sema/src/plr_sema/__main__.py`:

```python
"""`python -m plr_sema check <file.py>...` (spec 261002 §6).

Exit codes: 0 analyzed with no WILL_FAIL (UNKNOWN allowed); 1 at least one
WILL_FAIL; 2 not analyzed, unreadable input, or usage error. Several files:
the worst code wins. A not-analyzed file is never reported as safe.
"""

from __future__ import annotations

import argparse
import dataclasses
import enum
import json
import sys
from pathlib import Path

from plr_sema.analysis import Analyzed, NotAnalyzed, NotAnalyzedReason, analyze
from plr_sema.contracts import ContractsError, contracts_source, load_contracts
from plr_sema.verdict import Verdict

EXIT_OK, EXIT_WILL_FAIL, EXIT_NOT_ANALYZED = 0, 1, 2


def _jsonable(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        items = [_jsonable(v) for v in obj]
        return sorted(items, key=json.dumps) if isinstance(obj, (set, frozenset)) else items
    return obj


def _check_one(path: Path, function: str | None, contracts) -> tuple[int, dict, list[str]]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        detail = f"cannot read {path}: {exc}"
        return EXIT_NOT_ANALYZED, {"file": str(path), "function": function, "outcome": "not_analyzed",
                                   "reason": "unreadable_input", "detail": detail}, [f"{path}: unreadable_input {detail}"]
    out = analyze(source, function, contracts=contracts)
    if isinstance(out, NotAnalyzed):
        rec = {"file": str(path), "function": out.function_name, "outcome": "not_analyzed",
               "reason": out.reason.value, "detail": out.detail}
        return EXIT_NOT_ANALYZED, rec, [f"{path}: not analyzed: {out.reason.value}: {out.detail}"]
    assert isinstance(out, Analyzed)
    lines = []
    for f in out.report.findings:
        line = out.op_lines.get(f.operation_id, 0)
        why = f.category if f.verdict is Verdict.WILL_FAIL else f.reason
        lines.append(f"{path}:{line} {f.operation_id} {f.verdict.value} {why}")
    lines.append(f"{path}::{out.function_name} -> {out.report.verdict.value} ({len(out.report.findings)} findings)")
    rec = {"file": str(path), "function": out.function_name, "outcome": "analyzed",
           "verdict": out.report.verdict.value, "key": out.key.as_str(),
           "findings": _jsonable(list(out.report.findings))}
    code = EXIT_WILL_FAIL if out.report.verdict is Verdict.WILL_FAIL else EXIT_OK
    return code, rec, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m plr_sema")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="statically check PLR protocol files")
    check.add_argument("files", nargs="+", type=Path)
    check.add_argument("--function", help="function to analyze (default: the only top-level def)")
    check.add_argument("--json", action="store_true", help="machine-readable output")
    check.add_argument("--contracts", help="contract table (.json or .json.gz)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse exits 2 on usage errors already; normalize anything else
        return EXIT_NOT_ANALYZED if exc.code else EXIT_OK

    where = contracts_source(args.contracts)
    contracts = None
    contracts_error = None
    if where.path is None:
        contracts_error = f"no contract table configured (layer: {where.layer})"
    else:
        try:
            contracts = load_contracts(where.path)
        except ContractsError as exc:
            contracts_error = str(exc)

    worst, records, text = EXIT_OK, [], []
    for path in args.files:
        if contracts is None:
            code = EXIT_NOT_ANALYZED
            rec = {"file": str(path), "function": args.function, "outcome": "not_analyzed",
                   "reason": NotAnalyzedReason.CONTRACTS_UNAVAILABLE.value, "detail": contracts_error}
            lines = [f"{path}: not analyzed: {NotAnalyzedReason.CONTRACTS_UNAVAILABLE.value}: {contracts_error}"]
        else:
            code, rec, lines = _check_one(path, args.function, contracts)
        worst = max(worst, code)
        records.append(rec)
        text.extend(lines)

    if args.json:
        print(json.dumps({"results": records, "exit_code": worst}, sort_keys=True))
    else:
        print("\n".join(text))
    return worst


if __name__ == "__main__":
    sys.exit(main())
```

Notes: contracts load **once** per invocation (each `check_graph` call takes ~0.13 s against the real table; the 18 MB load is the expensive part). `max()` gives "worst wins" because the codes are ordered 0 < 1 < 2.

- [ ] **Step 3: Run the non-snapshot tests**

Run: `uv run --no-sync pytest plr-sema/tests/test_cli.py -q -k "not json_output_shape"` → PASS.

- [ ] **Step 4: Generate and review the JSON-shape snapshot**

```bash
mkdir -p plr-sema/tests/fixtures/cli
uv run --no-sync python3 - <<'PY'
import json, subprocess, sys
sys.path.insert(0, "plr-sema/tests")
from test_cli import _shape, FIX, CONTRACTS
r = subprocess.run([sys.executable, "-m", "plr_sema", "check", str(FIX / "for_pickup_no_drop_raises.py"),
                    "--json", "--contracts", str(CONTRACTS)], capture_output=True, text=True)
open("plr-sema/tests/fixtures/cli/check_json_shape.json", "w").write(
    json.dumps(_shape(json.loads(r.stdout)), indent=1, sort_keys=True) + "\n")
PY
cat plr-sema/tests/fixtures/cli/check_json_shape.json
```

Read the snapshot: it must contain `exit_code: int`, and per result `file`, `function`, `outcome`, `verdict`, `key` (all `str`) and a `findings` list of objects with `verdict`, `operation_id`, `category`, `reason`, `detail`, `plr_site`. If a field you expect is missing, fix `_check_one`, not the snapshot.

Run: `uv run --no-sync pytest plr-sema/tests/test_cli.py -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add plr-sema/src/plr_sema/__main__.py plr-sema/tests/test_cli.py plr-sema/tests/fixtures/cli/check_json_shape.json
git commit -m "feat(plr-sema): python -m plr_sema check CLI with 0/1/2 exit codes and --json (261002_sema-web-integration)"
```

---

### Task 8: Prose citations that name the old paths

**Files:**
- Modify: `plr-sema/src/plr_sema/_hand_maintained.py:652` and `:854`
- Modify: `plr-sema/tests/test_check_graph.py` (docstring mentions)
- Modify: `plr-sema/tests/test_hand_maintained_ratchet.py:24` (docstring)

The five dated plr-sema specs that cite the moved files are pinned with `citations_at:` and resolve against history, so they are **not** edited (spec A10).

- [ ] **Step 1: Find every live mention**

Run: `rg -n "praxis/common/type_inspection|plr_static_analysis/resource_hierarchy|plr_static_analysis/models\.py|visitors/computation_graph_extractor" plr-sema/src plr-sema/tests plr-sema/eval plr-sema/scripts`

Expected hits include `_hand_maintained.py:652`, `_hand_maintained.py:854`, and docstrings in `tests/test_check_graph.py` and `tests/test_hand_maintained_ratchet.py`. `plr-sema/eval/extract_runner.py` and `tier2_extractor.py` keep importing through the praxis shim; leave them.

- [ ] **Step 2: Rewrite each hit**

- `_hand_maintained.py:652`: `what="PLR_RESOURCE_TYPES class-name set (plr_sema/graph/type_inspection.py:14-92)"` (line numbers unchanged by the verbatim move; confirm with `sed -n '14,16p;90,92p' plr-sema/src/plr_sema/graph/type_inspection.py`).
- `_hand_maintained.py:854`: `what="PreconditionType enum (plr_sema/graph/models.py)"` — find the class's new line range with `grep -n "class PreconditionType\|class OperationNode" plr-sema/src/plr_sema/graph/models.py` and write it as `models.py:<start>-<end>`.
- Docstrings: replace the old path with the new one; where a docstring explains that a test "subprocesses into praxis's extractor", add "(now `plr_sema.extract`, reached through the praxis shim)".

- [ ] **Step 3: Run the citation and ratchet tests**

Run: `uv run --no-sync pytest -q plr-sema/tests/test_spec_lint.py plr-sema/tests/test_hand_maintained_ratchet.py plr-sema/tests/test_check_graph.py`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add plr-sema/src/plr_sema/_hand_maintained.py plr-sema/tests/test_check_graph.py plr-sema/tests/test_hand_maintained_ratchet.py
git commit -m "docs(plr-sema): point live citations at plr_sema.graph/extract after the move (261002_sema-web-integration)"
```

---

### Task 9: CI workflow and image dependency

**Files:**
- Create: `.github/workflows/plr-sema.yml`
- Modify: `Dockerfile:28-38`

**Interfaces:**
- Consumes: the CLI (Task 7), the suite.

- [ ] **Step 1: Read the existing workflow conventions**

Run: `sed -n 70,100p .github/workflows/repl.yml; sed -n 480,500p .github/workflows/repl.yml`. Copy its checkout (with `submodules: recursive` — `external/pylabrobot` is a submodule), its `astral-sh/setup-uv` step and version pin, and its `uv sync --all-packages` form exactly.

- [ ] **Step 2: Write the workflow**

`.github/workflows/plr-sema.yml` (adjust the action versions to the ones `repl.yml` pins):

```yaml
name: plr-sema

on:
  pull_request:
    paths:
      - "plr-sema/**"
      - "praxis/common/type_inspection.py"
      - "praxis/backend/utils/plr_static_analysis/models.py"
      - "praxis/backend/utils/plr_static_analysis/resource_hierarchy.py"
      - "praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py"
      - "pyproject.toml"
      - ".github/workflows/plr-sema.yml"
  push:
    branches: [main]
    paths:
      - "plr-sema/**"
      - ".github/workflows/plr-sema.yml"

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive
      - uses: astral-sh/setup-uv@v5
      - name: Sync workspace
        run: uv sync --all-packages
      - name: plr-sema suite
        run: uv run --no-sync pytest plr-sema/tests -q -p no:cacheprovider
      - name: Shim identity and parity
        run: uv run --no-sync pytest -q tests/utils/test_computation_graph.py tests/core/test_precondition_resolver.py tests/utils/test_resource_hierarchy.py
      - name: CLI smoke
        run: |
          set +e
          uv run --no-sync python -m plr_sema check plr-sema/eval/fixtures/regions/straightline_clean.py; a=$?
          uv run --no-sync python -m plr_sema check plr-sema/eval/fixtures/regions/for_pickup_no_drop_raises.py; b=$?
          printf 'def protocol(:\n' > "$RUNNER_TEMP/bad.py"
          uv run --no-sync python -m plr_sema check "$RUNNER_TEMP/bad.py"; c=$?
          echo "exit codes: clean=$a will_fail=$b syntax=$c"
          test "$a" = 0 && test "$b" = 1 && test "$c" = 2
```

Not a required check (spec Q5). The full plr-sema suite runs here, on the runner — never locally.

- [ ] **Step 3: Dockerfile**

The compile step (`uv pip compile pyproject.toml`, line 28) runs before the repo is copied, and `plr-sema` is not on PyPI, so it would fail once the root depends on it. Change lines 23–38 to the block below. Check locally that the filter does what it claims: `grep -v -e '"plr-sema\[extract\]",' -e '^plr-sema = { workspace = true }' pyproject.toml | grep -c plr-sema` must print only the count of the remaining `[tool.uv.workspace]` / `[tool.plr-sema]` / ruff-exclude mentions, none of them a dependency.

```dockerfile
# Copy pyproject.toml to cache dependencies
COPY pyproject.toml .

# Generate requirements.txt using uv. The workspace member plr-sema is not on
# PyPI and its source is not copied yet: compile from a copy of pyproject.toml
# without it, and install it from source below (spec 261002 R1).
RUN grep -v -e '"plr-sema\[extract\]",' -e '^plr-sema = { workspace = true }' pyproject.toml > pyproject.docker.toml \
 && uv pip compile pyproject.docker.toml --extra dev -o requirements.txt

# Install dependencies into /install prefix
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Copy application code
COPY . .

# Install the workspace member, then the application itself, into /install
RUN pip install --no-cache-dir --prefix=/install --no-deps ./plr-sema
RUN pip install --no-cache-dir --prefix=/install --no-deps .
```

This is **unverified**: no workflow builds the image and Docker is not available locally (spec R1). Say so in the PR description and do not claim the image works.

- [ ] **Step 4: Local checks that are possible**

Run: `uv run --no-sync python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/plr-sema.yml'))"` (or `uvx yamllint` if available) and the CLI smoke block from Step 2 by hand in the worktree, with `RUNNER_TEMP=$TMPDIR`.
Expected: YAML parses; printed `exit codes: clean=0 will_fail=1 syntax=2`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/plr-sema.yml Dockerfile
git commit -m "ci(plr-sema): dedicated workflow with suite + CLI smoke; install plr-sema in the image (unverified) (261002_sema-web-integration)"
```

- [ ] **Step 6: Push and open the PR (only when the user asks)**

When asked: `git push -u origin feat/sema-slice1-spec`, then open one non-draft PR against `main` with `gh pr create`. In the body, list what CI verifies (the plr-sema suite, the shim/parity tests, the CLI smoke) and what it does not (the Docker image, the browser). End the body with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Never merge.
