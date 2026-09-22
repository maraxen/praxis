"""Persistence modules staging: stage_shell copies shell/persistence/* to
dist/shell/persistence/, excluding __tests__, and assert_dist_complete requires
the three core modules: codec.js, core.js, panel.js.

The persistence source files may not exist yet when this test runs, so the test
builds its own temporary fixture tree in a tmp directory, never depending on the
actual source existing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import build_repl  # noqa: E402 -- path setup must precede this import


def _make_shell_source_tree(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal temporary shell/ source tree: praxis-shell.js plus a
    persistence/ dir with the three required modules and a __tests__
    directory that should be excluded. Returns (shell_dir, persistence_dir).
    """
    shell_dir = tmp_path / "shell_src"
    shell_dir.mkdir()
    (shell_dir / "praxis-shell.js").write_text("// praxis-shell.js\n")

    src = shell_dir / "persistence"
    src.mkdir()
    (src / "codec.js").write_text("// codec.js\n")
    (src / "core.js").write_text("// core.js\n")
    (src / "panel.js").write_text("// panel.js\n")

    # Add a __tests__ directory that should be excluded during staging
    tests_dir = src / "__tests__"
    tests_dir.mkdir()
    (tests_dir / "x.test.js").write_text("// test file\n")

    return shell_dir, src


def _make_dist_dir(tmp_path: Path) -> Path:
    """Create a minimal dist directory structure for testing."""
    dist = tmp_path / "dist"
    (dist / "shell").mkdir(parents=True)
    return dist


def test_stage_shell_stages_persistence_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that build_repl.stage_shell() itself copies the three persistence
    modules from a temporary source tree and excludes __tests__. Exercising
    the production function (not a re-implementation) so a regression in
    stage_shell's persistence block fails this test."""
    shell_dir, src = _make_shell_source_tree(tmp_path)
    dist = _make_dist_dir(tmp_path)

    monkeypatch.setattr(build_repl, "SHELL_DIR", shell_dir)
    monkeypatch.setattr(build_repl, "PERSISTENCE_JS_MODULES", src)

    build_repl.stage_shell(dist)

    dst_modules = dist / "shell" / "persistence"

    # Verify the three required modules were staged with identical bytes.
    assert (dst_modules / "codec.js").read_bytes() == (src / "codec.js").read_bytes()
    assert (dst_modules / "core.js").read_bytes() == (src / "core.js").read_bytes()
    assert (dst_modules / "panel.js").read_bytes() == (src / "panel.js").read_bytes()

    # Verify __tests__ directory was NOT staged
    assert not (dst_modules / "__tests__").exists()


def test_stage_shell_removes_stale_persistence_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify that a stale file in dist/shell/persistence/, present before
    build_repl.stage_shell() runs, is removed by it."""
    shell_dir, src = _make_shell_source_tree(tmp_path)
    dist = _make_dist_dir(tmp_path)

    # Create a stale file in the destination before staging.
    dst_modules = dist / "shell" / "persistence"
    dst_modules.mkdir(parents=True, exist_ok=True)
    stale_file = dst_modules / "old.js"
    stale_file.write_text("// stale file\n")
    assert stale_file.exists(), "Setup: stale file should exist before staging"

    monkeypatch.setattr(build_repl, "SHELL_DIR", shell_dir)
    monkeypatch.setattr(build_repl, "PERSISTENCE_JS_MODULES", src)

    build_repl.stage_shell(dist)

    # Verify the stale file is gone
    assert not stale_file.exists(), "Stale file should be removed after staging"

    # Verify the new files are present
    assert (dst_modules / "codec.js").is_file()
    assert (dst_modules / "core.js").is_file()
    assert (dst_modules / "panel.js").is_file()


def test_stage_shell_removes_stale_dist_when_source_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A-10: a persistence module deleted from source cannot survive in dist.
    If PERSISTENCE_JS_MODULES no longer exists at all, a stale dist/shell/
    persistence/ dir from a previous build must still be removed."""
    shell_dir = tmp_path / "shell_src"
    shell_dir.mkdir()
    (shell_dir / "praxis-shell.js").write_text("// praxis-shell.js\n")

    # Source persistence dir is absent entirely.
    absent_src = shell_dir / "persistence"
    assert not absent_src.exists()

    dist = _make_dist_dir(tmp_path)
    dst_modules = dist / "shell" / "persistence"
    dst_modules.mkdir(parents=True, exist_ok=True)
    (dst_modules / "old.js").write_text("// stale file\n")
    assert dst_modules.exists(), "Setup: stale dist dir should exist before staging"

    monkeypatch.setattr(build_repl, "SHELL_DIR", shell_dir)
    monkeypatch.setattr(build_repl, "PERSISTENCE_JS_MODULES", absent_src)

    build_repl.stage_shell(dist)

    assert not dst_modules.exists(), (
        "Stale persistence dir must be removed even when source is absent"
    )


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
