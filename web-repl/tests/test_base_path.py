"""Tests for ``build_repl``'s ``--base-path`` normalization and the
auto-setup notebook guard that replaced its old HOST_ROOT rewrite.

Debt #1396 (auto-setup) retired the build-time ``apply_base_path`` rewrite:
the site root is now derived at RUNTIME by ``praxis_boot.derive_host_root()``
from the kernel worker's own location, so no notebook needs a baked-in
HOST_ROOT any more. What replaced the rewrite's guard is
``assert_no_hardcoded_bootstrap_in_notebooks``, which fails the build if any
shipped notebook's CODE cells still hand-trigger bootstrap -- a stale
``praxis_main(``, ``praxis_boot.setup(`` or ``HOST_ROOT =`` call would fight
the once-guard or reintroduce a stale absolute fetch root.

The failure this guards against is the same "looks healthy, isn't" shape the
old rewrite guarded against: the site boots, the notebook opens, and only
something more subtle goes wrong (a double-run, or a 404 on a subpath
deploy) than an outright crash.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build_repl  # noqa: E402 -- path setup must precede this


def _notebook(dest: Path, *cells: tuple[str, str]) -> Path:
    """Write a notebook. Each cell is a ``(cell_type, source)`` pair."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": cell_type, "source": [source + "\n"], "metadata": {}, "outputs": []}
                    for cell_type, source in cells
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        )
    )
    return dest


def _code(dest: Path, *sources: str) -> Path:
    return _notebook(dest, *(("code", s) for s in sources))


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("/", "/"),
        ("", "/"),
        ("praxis", "/praxis/"),
        ("/praxis", "/praxis/"),
        ("praxis/", "/praxis/"),
        ("/praxis/", "/praxis/"),
        ("  /praxis/  ", "/praxis/"),
        ("a/b", "/a/b/"),
    ],
)
def test_normalize_base_path(raw, expected):
    assert build_repl.normalize_base_path(raw) == expected


def test_missing_files_dir_fails_the_build(tmp_path):
    with pytest.raises(build_repl.BuildAssertionError, match="does not exist"):
        build_repl.assert_no_hardcoded_bootstrap_in_notebooks(tmp_path)


def test_forbidden_literal_in_markdown_only_passes(tmp_path):
    """Markdown cells may document `praxis_boot.setup()` in prose (welcome.ipynb
    does, spec section 6.5) -- only code cells are scanned.
    """
    _notebook(
        tmp_path / "files" / "welcome.ipynb",
        ("markdown", "Retry with `await praxis_boot.setup()` in a cell."),
        ("code", "print('hello')"),
    )
    build_repl.assert_no_hardcoded_bootstrap_in_notebooks(tmp_path)  # must not raise


@pytest.mark.parametrize(
    "forbidden_source",
    [
        "await praxis_boot.setup()",
        "await praxis_main(HOST_ROOT)",
        'HOST_ROOT = "/"',
    ],
    ids=["praxis_boot.setup(", "praxis_main(", "HOST_ROOT ="],
)
def test_forbidden_literal_in_code_cell_fails(tmp_path, forbidden_source):
    _code(tmp_path / "files" / "stale.ipynb", forbidden_source)
    with pytest.raises(build_repl.BuildAssertionError, match="hand-trigger"):
        build_repl.assert_no_hardcoded_bootstrap_in_notebooks(tmp_path)


def test_bare_setup_call_in_code_cell_passes(tmp_path):
    """PyLabRobot's own `await lh.setup()` idiom must stay allowed: the
    forbidden list deliberately has no bare `setup(` entry.
    """
    _code(tmp_path / "files" / "device.ipynb", "await lh.setup()")
    build_repl.assert_no_hardcoded_bootstrap_in_notebooks(tmp_path)  # must not raise


def test_rewritten_notebook_with_no_forbidden_literal_passes(tmp_path):
    _code(
        tmp_path / "files" / "welcome.ipynb",
        "import praxis_boot; praxis_boot.status()",
        "await lh.setup()",
    )
    build_repl.assert_no_hardcoded_bootstrap_in_notebooks(tmp_path)  # must not raise


def test_scans_every_notebook_not_just_the_first(tmp_path):
    """files/ is a directory, not one file -- a loop that stopped early would
    let a later offending notebook through unnoticed.
    """
    _code(tmp_path / "files" / "a.ipynb", "print(1)")
    _code(tmp_path / "files" / "nested" / "b.ipynb", 'HOST_ROOT = "/"')
    with pytest.raises(build_repl.BuildAssertionError, match="hand-trigger"):
        build_repl.assert_no_hardcoded_bootstrap_in_notebooks(tmp_path)


def test_real_source_notebooks_carry_no_bootstrap():
    """Coupling check, and the only test in this file that reads the real
    ``web-repl/files/`` tree.

    Runs against the ACTUAL shipped notebooks. Expected to fail until T6
    (welcome.ipynb's rewrite, spec section 6.5 / 9) lands -- T5 lands first
    per the spec's T5/T6 ordering (R2-3) and welcome.ipynb still carries its
    old bootstrap cell until then.
    """
    files_dir = Path(__file__).resolve().parents[1] / "files"
    build_repl.assert_no_hardcoded_bootstrap_in_notebooks(files_dir.parent)
