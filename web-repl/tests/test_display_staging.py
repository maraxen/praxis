"""Display modules staging (A6, AC-6): stage_shell copies shell/display/ to
dist/shell/display/, leaving out tests, and assert_dist_complete requires
shell/display/index.js and shell/display/chrome.js.

Same idiom as test_persistence_staging.py. The staging cases build a temporary
shell/ source tree and exercise the production stage_shell (no
re-implementation), so nothing here needs a dist build, a browser or the
network. One case runs stage_shell against the REAL shell/ source into a
temporary dist: that is AC-6's `test -f dist/shell/display/index.js` and
`! test -e dist/shell/display/__tests__` without the wheel/JupyterLite build.

B9 (this file's second revision) adds stale.js and interact.js to the required
list. B8 (third revision) adds the kernel-side package: assert_dist_complete also
requires assets/python/praxis/display/__init__.py (spec section 4, build_repl.py row:
"C6 ... and assets/python/praxis/display/__init__.py, the last from B8"). Without it a
dist could ship a bootstrap whose D13 stage imports a package that is not there, and
the failure would surface only as a runtime praxis:display-error. Later tasks (C6)
extend the staged/required lists and this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import build_repl  # noqa: E402 -- path setup must precede this import

# What a dist requires under shell/display/. A6: index.js, chrome.js. B9 appends
# stale.js and interact.js; C6 appends dock.js in its own commit.
_REQUIRED_DISPLAY = ("index.js", "chrome.js", "stale.js", "interact.js")

# The kernel-side package B8 adds (path relative to dist/).
_DISPLAY_PY_INIT = "assets/python/praxis/display/__init__.py"


def _make_shell_source_tree(tmp_path: Path) -> tuple[Path, Path]:
    """A minimal temporary shell/ source tree: praxis-shell.js plus a display/
    dir with the required modules, a __tests__ directory and sibling *.test.js
    files (A5 keeps its bun tests next to the modules), all of which must be
    excluded. Returns (shell_dir, display_dir)."""
    shell_dir = tmp_path / "shell_src"
    shell_dir.mkdir()
    (shell_dir / "praxis-shell.js").write_text("// praxis-shell.js\n")

    src = shell_dir / "display"
    src.mkdir()
    for name in _REQUIRED_DISPLAY:
        (src / name).write_text(f"// {name}\n")

    (src / "chrome.test.js").write_text("// sibling test\n")
    (src / "index.test.js").write_text("// sibling test\n")
    tests_dir = src / "__tests__"
    tests_dir.mkdir()
    (tests_dir / "fakes.js").write_text("// fakes\n")
    (tests_dir / "x.test.js").write_text("// test file\n")
    return shell_dir, src


def _make_dist_dir(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    (dist / "shell").mkdir(parents=True)
    return dist


def _write_complete_dist(dist: Path) -> None:
    """Every path assert_dist_complete requires today, display modules included."""
    files = {
        "assets/wheels/manifest.json": "{}",
        "assets/wheels/pkg-1.0.0-py3-none-any.whl": "wheel",
        "assets/shims/web_serial_shim.py": "# shim\n",
        "assets/shims/web_usb_shim.py": "# shim\n",
        "assets/shims/web_hid_shim.py": "# shim\n",
        "assets/shims/web_ftdi_shim.py": "# shim\n",
        "assets/python/web_bridge.py": "# bridge\n",
        "assets/python/praxis/__init__.py": "",
        "assets/python/praxis/interactive.py": "# interactive\n",
        _DISPLAY_PY_INIT: "# display\n",
        "assets/visualizer/lib.js": "// lib\n",
        "assets/visualizer/index.html": "<html></html>",
        "assets/visualizer-augmentations/index.js": "// aug\n",
        "assets/theme/praxis-theme.css": "/* theme */\n",
        "assets/theme/praxis-mark.svg": "<svg></svg>",
        "assets/theme/praxis-favicon.svg": "<svg></svg>",
        "assets/theme/fonts/RobotoFlex-Variable.woff2": "font",
        "assets/theme/fonts/JetBrainsMono-Variable.woff2": "font",
        "bootstrap/praxis_bootstrap.py": "# bootstrap\n",
        "bootstrap/stages.py": "# stages\n",
        "bootstrap/transport.py": "# transport\n",
        "shell/praxis-shell.js": "// shell\n",
        "shell/persistence/codec.js": "// codec\n",
        "shell/persistence/core.js": "// core\n",
        "shell/persistence/panel.js": "// panel\n",
        "lab/index.html": "<html></html>",
        "repl/index.html": "<html></html>",
        "files/welcome.ipynb": "{}",
        "api/contents/all.json": "{}",
        **{f"shell/display/{name}": f"// {name}\n" for name in _REQUIRED_DISPLAY},
    }
    for rel, text in files.items():
        p = dist / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)


def _staged_files(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


# --- stage_shell -------------------------------------------------------------


def test_stage_shell_stages_display_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """stage_shell copies display/ with identical bytes, and stages neither
    __tests__/ nor any *.test.js."""
    shell_dir, src = _make_shell_source_tree(tmp_path)
    dist = _make_dist_dir(tmp_path)
    monkeypatch.setattr(build_repl, "SHELL_DIR", shell_dir)

    build_repl.stage_shell(dist)

    dst = dist / "shell" / "display"
    for name in _REQUIRED_DISPLAY:
        assert (dst / name).read_bytes() == (src / name).read_bytes()
    assert not (dst / "__tests__").exists()
    assert _staged_files(dst) == set(_REQUIRED_DISPLAY), (
        "only the shipping modules may be staged (no tests, no fakes)"
    )


def test_stage_shell_removes_stale_display_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file in dist/shell/display/ from an earlier build, absent from source,
    is removed by stage_shell."""
    shell_dir, _src = _make_shell_source_tree(tmp_path)
    dist = _make_dist_dir(tmp_path)
    dst = dist / "shell" / "display"
    dst.mkdir(parents=True)
    stale = dst / "old.js"
    stale.write_text("// stale file\n")
    stale_nested = dst / "__tests__" / "old.test.js"
    stale_nested.parent.mkdir()
    stale_nested.write_text("// stale nested test\n")
    monkeypatch.setattr(build_repl, "SHELL_DIR", shell_dir)

    build_repl.stage_shell(dist)

    assert not stale.exists(), "stale file must be removed after staging"
    assert not stale_nested.exists(), "stale nested file must be removed after staging"
    for name in _REQUIRED_DISPLAY:
        assert (dst / name).is_file()


def test_stage_shell_removes_stale_display_dir_when_source_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A-10 discipline: with no display/ in source at all, a dist/shell/display/
    left by an earlier build must not survive."""
    shell_dir = tmp_path / "shell_src"
    shell_dir.mkdir()
    (shell_dir / "praxis-shell.js").write_text("// praxis-shell.js\n")
    assert not (shell_dir / "display").exists()

    dist = _make_dist_dir(tmp_path)
    dst = dist / "shell" / "display"
    dst.mkdir(parents=True)
    (dst / "old.js").write_text("// stale file\n")
    monkeypatch.setattr(build_repl, "SHELL_DIR", shell_dir)

    build_repl.stage_shell(dist)

    assert not dst.exists(), "stale display dir must be removed even when source is absent"


def test_stage_shell_real_source_stages_display_without_tests(tmp_path: Path) -> None:
    """AC-6, without the wheel/JupyterLite build: stage the REAL shell/ source.
    `test -f dist/shell/display/index.js` and `! test -e dist/shell/display/__tests__`,
    plus chrome.js and no *.test.js anywhere under display/."""
    dist = _make_dist_dir(tmp_path)

    build_repl.stage_shell(dist)

    dst = dist / "shell" / "display"
    for name in _REQUIRED_DISPLAY:
        assert (dst / name).is_file(), f"dist/shell/display/{name} was not staged"
    assert not (dst / "__tests__").exists()
    leaked = sorted(p for p in _staged_files(dst) if p.endswith(".test.js"))
    assert leaked == [], f"test files must not ship: {leaked}"
    # Bytes match the tracked source (a copy, not a rewrite).
    for name in _REQUIRED_DISPLAY:
        assert (dst / name).read_bytes() == (build_repl.SHELL_DIR / "display" / name).read_bytes()


# --- assert_dist_complete ----------------------------------------------------


def test_assert_dist_complete_passes_with_display_modules(tmp_path: Path) -> None:
    """Positive control: the complete fixture (display modules present) passes,
    so the failures below are attributable to the missing file alone."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)

    build_repl.assert_dist_complete(dist, with_coxswain=False)  # must not raise


@pytest.mark.parametrize("missing", _REQUIRED_DISPLAY)
def test_assert_dist_complete_requires_each_display_module(
    tmp_path: Path, missing: str
) -> None:
    """Negative control: with exactly one display module missing it raises
    BuildAssertionError that names that file (and only that display file)."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)
    (dist / "shell" / "display" / missing).unlink()

    with pytest.raises(build_repl.BuildAssertionError) as exc:
        build_repl.assert_dist_complete(dist, with_coxswain=False)

    msg = str(exc.value)
    assert "missing required staged path" in msg
    assert f"shell/display/{missing}" in msg.replace("\\", "/")
    for present in (n for n in _REQUIRED_DISPLAY if n != missing):
        assert f"shell/display/{present}" not in msg.replace("\\", "/")


def test_assert_dist_complete_requires_display_dir(tmp_path: Path) -> None:
    """Every module missing (no display/ at all) -> every one is named."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)
    for name in _REQUIRED_DISPLAY:
        (dist / "shell" / "display" / name).unlink()
    (dist / "shell" / "display").rmdir()

    with pytest.raises(build_repl.BuildAssertionError) as exc:
        build_repl.assert_dist_complete(dist, with_coxswain=False)

    msg = str(exc.value).replace("\\", "/")
    for name in _REQUIRED_DISPLAY:
        assert f"shell/display/{name}" in msg


def test_assert_dist_complete_requires_the_display_python_package(tmp_path: Path) -> None:
    """B8: with only ``praxis/display/__init__.py`` missing (the fixture is otherwise complete, as the
    positive control above shows) it raises BuildAssertionError naming exactly that file."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)
    (dist / _DISPLAY_PY_INIT).unlink()

    with pytest.raises(build_repl.BuildAssertionError) as exc:
        build_repl.assert_dist_complete(dist, with_coxswain=False)

    msg = str(exc.value).replace("\\", "/")
    assert "missing required staged path" in msg
    assert _DISPLAY_PY_INIT in msg
    # and only that one path is missing
    assert msg.count("\n  ") == 1, msg


def test_assert_dist_complete_requires_the_display_python_package_dir(tmp_path: Path) -> None:
    """No ``praxis/display/`` directory at all: still named."""
    dist = _make_dist_dir(tmp_path)
    _write_complete_dist(dist)
    (dist / _DISPLAY_PY_INIT).unlink()
    (dist / "assets" / "python" / "praxis" / "display").rmdir()

    with pytest.raises(build_repl.BuildAssertionError) as exc:
        build_repl.assert_dist_complete(dist, with_coxswain=False)

    assert _DISPLAY_PY_INIT in str(exc.value).replace("\\", "/")


def test_the_real_overlay_ships_the_display_python_package() -> None:
    """The source tree has what the dist requires: the overlay's ``praxis/display/__init__.py`` exists
    (``stage_overlay`` copies ``overlay/assets/`` wholesale, so this is what lands in dist)."""
    init = (
        Path(__file__).resolve().parents[1] / "overlay" / "assets" / "python" / "praxis" / "display" / "__init__.py"
    )
    assert init.is_file(), init
