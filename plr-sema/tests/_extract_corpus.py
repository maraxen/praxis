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
