"""Out-of-process extractor runner (spec 260903 §12.4.1, backlog #4880,
AC-12.16). Invoked as a SUBPROCESS by ``tier2_extractor.py`` -- never
imported by anything under ``plr-sema/src/`` or ``plr-sema/eval/``.

There is no extractor CLI today: the only public entry point is
``extract_graph_from_source``
(``praxis/backend/utils/plr_static_analysis/visitors/computation_graph_extractor.py:925``)
and nothing outside that module calls it. This script is a thin wrapper --
source path in, ``graph.model_dump(mode="json")`` out -- so that
``plr-sema``'s own package (and the rest of ``plr-sema/eval/``) never
imports ``praxis`` and ``plr-sema/tests/test_import_boundary.py`` keeps
holding.

**This is the one module in ``plr-sema/eval/`` permitted to ``import
praxis``**, and even here the import is LAZY -- confined to
:func:`main`, after argument parsing and the cache-hit check -- so a
static AST import scan never needs to execute this module to see that the
import exists; it is grep-visible directly. ``plr-sema/tests/
test_import_boundary.py``'s ``eval/``-scoped scan (AC-12.16) exempts
exactly this file, by name, for exactly this reason.

Usage::

    uv run python plr-sema/eval/extract_runner.py \\
        --source path/to/protocol.py --function protocol --out graph.json \\
        [--cache-dir DIR]

Caches by sha256 digest of the source text under ``--cache-dir`` (default:
``$TMPDIR/plr_sema_extract_cache`` or ``/tmp/plr_sema_extract_cache``) --
the harness (``tier2_extractor.py``) shells to this script once per row,
so digest-keyed caching avoids re-running libcst extraction over an
identical rendered source (e.g. two corpus rows whose call sequence
renders to the same protocol body).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def _cache_path(cache_dir: Path, digest: str) -> Path:
    return cache_dir / f"{digest}.json"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", type=Path, required=True, help="path to a .py file")
    ap.add_argument("--function", type=str, required=True, help="function name to extract")
    ap.add_argument("--out", type=Path, required=True, help="graph JSON output path")
    ap.add_argument(
        "--cache-dir", type=Path, default=None,
        help="digest-keyed cache dir (default: $TMPDIR/plr_sema_extract_cache)",
    )
    args = ap.parse_args(argv)

    source_text = args.source.read_text(encoding="utf-8")
    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()

    cache_dir = args.cache_dir or Path(os.environ.get("TMPDIR", "/tmp")) / "plr_sema_extract_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(cache_dir, digest)

    if cache_file.is_file():
        args.out.write_text(cache_file.read_text(encoding="utf-8"), encoding="utf-8")
        sys.stderr.write(f"extract_runner: cache HIT {digest}\n")
        return 0

    sys.stderr.write(f"extract_runner: cache MISS {digest}\n")

    # praxis import is LAZY and confined to this function -- see the module
    # docstring's AC-12.16 note. `sys.path` is not touched: this script is
    # run under `uv run python` from a `cwd` where `praxis` is already
    # importable (the same environment `tests/utils/test_computation_graph.py`
    # runs under), never under plr-sema's own minimal environment.
    import libcst as cst

    from praxis.backend.utils.plr_static_analysis.visitors.computation_graph_extractor import (
        extract_graph_from_source,
    )

    # `extract_graph_from_source` itself collapses a genuine libcst parse
    # failure and a merely-absent function name into the SAME `None`
    # return (`except cst.ParserSyntaxError: return None`) -- re-parse
    # here, before calling it, purely to give the harness an honest,
    # distinguishable reason for the two very different failure modes
    # (found live, 260903: a renderer bug that emitted an invalid Python
    # identifier as a parameter name produced a parse failure that was
    # initially misreported as "function not found").
    try:
        cst.parse_module(source_text)
        parse_error: str | None = None
    except cst.ParserSyntaxError as e:
        parse_error = str(e)

    if parse_error is not None:
        payload: dict = {"error": f"source did not parse: {parse_error}"}
    else:
        graph = extract_graph_from_source(source_text, args.function)
        if graph is None:
            payload = {"error": f"function {args.function!r} not found in source"}
        else:
            payload = graph.model_dump(mode="json")

    text = json.dumps(payload)
    cache_file.write_text(text, encoding="utf-8")
    args.out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
