"""``scripts/repl_smoke.py`` must import without the PyLabRobot submodule (A1c).

Epic 260929_notebook-display-design, D16 "Import-time submodule dependency, removed in A1"
(Revision 11, C11-3). ``repl_smoke.py`` used to derive the expected PLR version from the
submodule's ``version.txt`` at import, through the module-level tuple ``NOTEBOOK_EXPECTED``.
Every harness consumer that loads the module by path (the shared unit runner's Chromium
case, the spike drivers, the A7 resume tests) then failed in any checkout whose
``external/pylabrobot`` was not initialised.

The fix makes it lazy: ``notebook_expected()`` is a function, read once per
``--notebook-check`` run. This file proves both halves:

* import succeeds with ``version.txt`` MISSING, and only ``notebook_expected()`` (and the run
  that binds it first) raises, naming the missing file;
* with ``version.txt`` present the returned strings carry ``<base>+g``.

Each case builds a temporary tree (``pyproject.toml`` so ``find_repo_root`` resolves, a copy
of ``repl_smoke.py``, and a copy of ``unit_runner.py`` so the test survives A7 making
``repl_smoke`` load it) and loads the copy by path under a fresh synthetic module name, so
the real repo's submodule state cannot leak in and no import cache is shared between cases.
No browser is launched.
"""

from __future__ import annotations

import importlib.util
import logging
import shutil
import stat
import sys
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"


def _make_tree(tmp_path: Path, *, version_txt: str | None) -> Path:
    """A minimal repo: pyproject.toml + scripts/{repl_smoke,unit_runner}.py (+ version.txt)."""
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "pyproject.toml").write_text('[project]\nname = "fake"\nversion = "0"\n')
    shutil.copy(SCRIPTS / "repl_smoke.py", root / "scripts" / "repl_smoke.py")
    assert (SCRIPTS / "unit_runner.py").is_file(), "scripts/unit_runner.py missing"
    shutil.copy(SCRIPTS / "unit_runner.py", root / "scripts" / "unit_runner.py")
    if version_txt is not None:
        vt = root / "external" / "pylabrobot" / "pylabrobot" / "version.txt"
        vt.parent.mkdir(parents=True)
        vt.write_text(version_txt)
    return root


@pytest.fixture
def load_repl_smoke():
    """Return ``load(root)`` -> a fresh module object for ``<root>/scripts/repl_smoke.py``."""
    names: list[str] = []

    def load(root: Path):
        path = root / "scripts" / "repl_smoke.py"
        name = f"repl_smoke_import_under_test_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        names.append(name)
        spec.loader.exec_module(module)
        return module

    yield load
    for n in names:
        sys.modules.pop(n, None)


def test_import_succeeds_without_the_submodule(tmp_path, load_repl_smoke):
    root = _make_tree(tmp_path, version_txt=None)
    assert not (root / "external" / "pylabrobot" / "pylabrobot" / "version.txt").exists()
    mod = load_repl_smoke(root)  # the regression: this raised VizCheckError at import
    assert callable(mod.notebook_expected)
    # the module resolved its repo root from the temporary tree, not from the real repo
    assert Path(mod.REPO_ROOT).resolve() == root.resolve()
    assert not hasattr(mod, "NOTEBOOK_EXPECTED"), "the eager module-level tuple must be gone"


def test_notebook_expected_raises_naming_the_missing_file(tmp_path, load_repl_smoke):
    root = _make_tree(tmp_path, version_txt=None)
    mod = load_repl_smoke(root)
    with pytest.raises(mod.VizCheckError) as exc:
        mod.notebook_expected()
    assert "version.txt" in str(exc.value)
    assert str(root / "external" / "pylabrobot" / "pylabrobot" / "version.txt") in str(exc.value)


def test_notebook_expected_carries_the_submodule_version(tmp_path, load_repl_smoke):
    root = _make_tree(tmp_path, version_txt="9.9.9\n")
    mod = load_repl_smoke(root)
    expected = mod.notebook_expected()
    assert isinstance(expected, tuple)
    assert len(expected) == 3
    assert all(isinstance(s, str) for s in expected)
    assert any("9.9.9+g" in s for s in expected)
    # behaviour-preserving: the other two needles are the same strings as before
    assert "praxis auto-setup state: ready" in expected
    assert "Serial is the browser shim: True" in expected
    assert "PyLabRobot 9.9.9+g" in expected


def test_run_notebook_check_fails_before_any_browser_work(tmp_path, load_repl_smoke):
    """The version is bound at the top of ``run_notebook_check`` (spec S1 note), so a missing
    ``version.txt`` fails before Playwright is imported or a browser launched. The serve dir
    does not exist and the chrome path is bogus: reaching either would raise something else."""
    root = _make_tree(tmp_path, version_txt=None)
    mod = load_repl_smoke(root)
    with pytest.raises(mod.VizCheckError) as exc:
        mod.run_notebook_check(
            serve_dir=tmp_path / "no-such-dist",
            base_path="/",
            chrome_path=str(tmp_path / "no-such-chrome"),
            timeout_s=1.0,
        )
    assert "version.txt" in str(exc.value)


def test_main_notebook_check_still_exits_1_without_version_txt(tmp_path, load_repl_smoke, caplog):
    """``main`` keeps its existing error handling: a missing ``version.txt`` is exit 1."""
    root = _make_tree(tmp_path, version_txt=None)
    mod = load_repl_smoke(root)
    fake_chrome = tmp_path / "chrome"
    fake_chrome.write_text("#!/bin/sh\nexit 0\n")
    fake_chrome.chmod(fake_chrome.stat().st_mode | stat.S_IXUSR)
    serve = tmp_path / "dist"
    serve.mkdir()
    with caplog.at_level(logging.ERROR, logger="repl_smoke"):
        rc = mod.main(
            ["--notebook-check", "--serve-dir", str(serve), "--chrome-path", str(fake_chrome)]
        )
    assert rc == 1
    assert any("version.txt" in r.getMessage() for r in caplog.records)
