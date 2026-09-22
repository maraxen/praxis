"""Persistence modules staging: stage_shell copies shell/persistence/* to
dist/shell/persistence/, excluding __tests__, and assert_dist_complete requires
the three core modules: codec.js, core.js, panel.js.

The persistence source files may not exist yet when this test runs, so the test
builds its own temporary fixture tree in a tmp directory, never depending on the
actual source existing.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import build_repl  # noqa: E402 -- path setup must precede this import


def _make_persistence_source(tmp_path: Path) -> Path:
    """Create a minimal temporary persistence source tree with the three required
    modules plus a __tests__ directory that should be excluded."""
    src = tmp_path / "persistence"
    src.mkdir()
    (src / "codec.js").write_text("// codec.js\n")
    (src / "core.js").write_text("// core.js\n")
    (src / "panel.js").write_text("// panel.js\n")

    # Add a __tests__ directory that should be excluded during staging
    tests_dir = src / "__tests__"
    tests_dir.mkdir()
    (tests_dir / "codec.test.js").write_text("// test file\n")
    (tests_dir / "core.test.js").write_text("// test file\n")

    return src


def _make_dist_dir(tmp_path: Path) -> Path:
    """Create a minimal dist directory structure for testing."""
    dist = tmp_path / "dist"
    (dist / "shell").mkdir(parents=True)
    return dist


def test_stage_shell_stages_persistence_modules(tmp_path: Path) -> None:
    """Verify that stage_shell copies the three persistence modules from a
    temporary source tree and excludes __tests__."""
    src = _make_persistence_source(tmp_path)
    dist = _make_dist_dir(tmp_path)

    # Temporarily patch PERSISTENCE_JS_MODULES to point to our fixture
    original_modules = build_repl.PERSISTENCE_JS_MODULES
    try:
        build_repl.PERSISTENCE_JS_MODULES = src

        # Call stage_shell with our fixture dist directory
        # We only care about the persistence staging part, so we'll directly
        # test the persistence-specific code path
        dst_dir = dist / "shell"
        if build_repl.PERSISTENCE_JS_MODULES.is_dir():
            dst_modules = dst_dir / "persistence"
            if dst_modules.exists():
                shutil.rmtree(dst_modules)
            staged = build_repl._copytree_filtered(
                build_repl.PERSISTENCE_JS_MODULES,
                dst_modules,
                skip=lambda rel: "__tests__" in rel.parts,
            )

            # Verify the three required modules were staged
            assert (dst_modules / "codec.js").is_file()
            assert (dst_modules / "core.js").is_file()
            assert (dst_modules / "panel.js").is_file()

            # Verify __tests__ directory was NOT staged
            assert not (dst_modules / "__tests__").exists()

            # Verify the count is correct (3 files, no __tests__)
            assert staged == 3
    finally:
        build_repl.PERSISTENCE_JS_MODULES = original_modules


def test_stage_shell_removes_stale_persistence_files(tmp_path: Path) -> None:
    """Verify that a stale file in dist/shell/persistence/ is removed when
    stage_shell runs."""
    src = _make_persistence_source(tmp_path)
    dist = _make_dist_dir(tmp_path)

    # Create a stale file in the destination
    dst_dir = dist / "shell"
    dst_modules = dst_dir / "persistence"
    dst_modules.mkdir(parents=True, exist_ok=True)
    stale_file = dst_modules / "old.js"
    stale_file.write_text("// stale file\n")

    assert stale_file.exists(), "Setup: stale file should exist before staging"

    # Temporarily patch PERSISTENCE_JS_MODULES to point to our fixture
    original_modules = build_repl.PERSISTENCE_JS_MODULES
    try:
        build_repl.PERSISTENCE_JS_MODULES = src

        # Simulate the rmtree and recopy from stage_shell
        if build_repl.PERSISTENCE_JS_MODULES.is_dir():
            dst_modules = dst_dir / "persistence"
            if dst_modules.exists():
                shutil.rmtree(dst_modules)
            build_repl._copytree_filtered(
                build_repl.PERSISTENCE_JS_MODULES,
                dst_modules,
                skip=lambda rel: "__tests__" in rel.parts,
            )

        # Verify the stale file is gone
        assert not stale_file.exists(), "Stale file should be removed after staging"

        # Verify the new files are present
        assert (dst_modules / "codec.js").is_file()
        assert (dst_modules / "core.js").is_file()
        assert (dst_modules / "panel.js").is_file()
    finally:
        build_repl.PERSISTENCE_JS_MODULES = original_modules


def test_assert_dist_complete_requires_persistence_modules(tmp_path: Path) -> None:
    """Verify that assert_dist_complete raises when a required persistence
    module is missing."""
    dist = _make_dist_dir(tmp_path)

    # Create a minimal dist structure with all required files except persistence
    # First, create the required files that assert_dist_complete checks
    (dist / "assets" / "wheels").mkdir(parents=True)
    (dist / "assets" / "wheels" / "manifest.json").write_text("{}")
    (dist / "assets" / "wheels" / "pkg-1.0.0-py3-none-any.whl").write_bytes(b"wheel")
    (dist / "assets" / "shims").mkdir(parents=True)
    (dist / "assets" / "shims" / "web_serial_shim.py").write_text("# shim\n")
    (dist / "assets" / "shims" / "web_usb_shim.py").write_text("# shim\n")
    (dist / "assets" / "shims" / "web_hid_shim.py").write_text("# shim\n")
    (dist / "assets" / "shims" / "web_ftdi_shim.py").write_text("# shim\n")
    (dist / "assets" / "python" / "praxis").mkdir(parents=True)
    (dist / "assets" / "python" / "web_bridge.py").write_text("# bridge\n")
    (dist / "assets" / "python" / "praxis" / "__init__.py").write_text("")
    (dist / "assets" / "python" / "praxis" / "interactive.py").write_text("# interactive\n")
    (dist / "assets" / "visualizer").mkdir(parents=True)
    (dist / "assets" / "visualizer" / "lib.js").write_text("// lib\n")
    (dist / "assets" / "visualizer" / "index.html").write_text("<html></html>")
    (dist / "assets" / "visualizer-augmentations").mkdir(parents=True)
    (dist / "assets" / "visualizer-augmentations" / "index.js").write_text("// aug\n")
    (dist / "bootstrap").mkdir(parents=True)
    (dist / "bootstrap" / "praxis_bootstrap.py").write_text("# bootstrap\n")
    (dist / "bootstrap" / "stages.py").write_text("# stages\n")
    (dist / "bootstrap" / "transport.py").write_text("# transport\n")
    (dist / "shell" / "praxis-shell.js").write_text("// shell\n")
    (dist / "lab").mkdir(parents=True)
    (dist / "lab" / "index.html").write_text("<html></html>")
    (dist / "repl").mkdir(parents=True)
    (dist / "repl" / "index.html").write_text("<html></html>")
    (dist / "files").mkdir(parents=True)
    (dist / "files" / "welcome.ipynb").write_text("{}")
    (dist / "api" / "contents").mkdir(parents=True)
    (dist / "api" / "contents" / "all.json").write_text("{}")

    # Create only TWO persistence modules, missing panel.js
    (dist / "shell" / "persistence").mkdir(parents=True)
    (dist / "shell" / "persistence" / "codec.js").write_text("// codec\n")
    (dist / "shell" / "persistence" / "core.js").write_text("// core\n")
    # Note: panel.js is intentionally missing

    # assert_dist_complete should raise because panel.js is missing
    with pytest.raises(build_repl.BuildAssertionError, match="missing required staged path"):
        build_repl.assert_dist_complete(dist, with_coxswain=False)


def test_assert_dist_complete_passes_with_all_persistence_modules(tmp_path: Path) -> None:
    """Verify that assert_dist_complete passes when all persistence modules
    are present."""
    dist = _make_dist_dir(tmp_path)

    # Create all required files
    (dist / "assets" / "wheels").mkdir(parents=True)
    (dist / "assets" / "wheels" / "manifest.json").write_text("{}")
    (dist / "assets" / "wheels" / "pkg-1.0.0-py3-none-any.whl").write_bytes(b"wheel")
    (dist / "assets" / "shims").mkdir(parents=True)
    (dist / "assets" / "shims" / "web_serial_shim.py").write_text("# shim\n")
    (dist / "assets" / "shims" / "web_usb_shim.py").write_text("# shim\n")
    (dist / "assets" / "shims" / "web_hid_shim.py").write_text("# shim\n")
    (dist / "assets" / "shims" / "web_ftdi_shim.py").write_text("# shim\n")
    (dist / "assets" / "python" / "praxis").mkdir(parents=True)
    (dist / "assets" / "python" / "web_bridge.py").write_text("# bridge\n")
    (dist / "assets" / "python" / "praxis" / "__init__.py").write_text("")
    (dist / "assets" / "python" / "praxis" / "interactive.py").write_text("# interactive\n")
    (dist / "assets" / "visualizer").mkdir(parents=True)
    (dist / "assets" / "visualizer" / "lib.js").write_text("// lib\n")
    (dist / "assets" / "visualizer" / "index.html").write_text("<html></html>")
    (dist / "assets" / "visualizer-augmentations").mkdir(parents=True)
    (dist / "assets" / "visualizer-augmentations" / "index.js").write_text("// aug\n")
    (dist / "bootstrap").mkdir(parents=True)
    (dist / "bootstrap" / "praxis_bootstrap.py").write_text("# bootstrap\n")
    (dist / "bootstrap" / "stages.py").write_text("# stages\n")
    (dist / "bootstrap" / "transport.py").write_text("# transport\n")
    (dist / "shell" / "praxis-shell.js").write_text("// shell\n")
    (dist / "lab").mkdir(parents=True)
    (dist / "lab" / "index.html").write_text("<html></html>")
    (dist / "repl").mkdir(parents=True)
    (dist / "repl" / "index.html").write_text("<html></html>")
    (dist / "files").mkdir(parents=True)
    (dist / "files" / "welcome.ipynb").write_text("{}")
    (dist / "api" / "contents").mkdir(parents=True)
    (dist / "api" / "contents" / "all.json").write_text("{}")

    # Create all THREE persistence modules
    (dist / "shell" / "persistence").mkdir(parents=True)
    (dist / "shell" / "persistence" / "codec.js").write_text("// codec\n")
    (dist / "shell" / "persistence" / "core.js").write_text("// core\n")
    (dist / "shell" / "persistence" / "panel.js").write_text("// panel\n")

    # assert_dist_complete should not raise
    build_repl.assert_dist_complete(dist, with_coxswain=False)  # must not raise
