"""Tests for the debt #1396 auto-setup build assertions in ``build_repl.py``.

These four assertions are the build-time half of the auto-setup design (spec
``.praxia/docs/specs/260914_first-run-auto-setup.md``, sections 8.2/9, T5):

- ``assert_autosetup_env`` -- AC-9(a): the runtime config must actually wire
  ``PYTHONSTARTUP`` to the shipped shim, or IPython never runs it.
- ``assert_praxis_startup_shipped`` -- AC-9(b): the shim itself must be both
  staged AND indexed, or the kernel's ``/drive`` mount never sees it.
- ``assert_kernel_autosetup_contract`` -- AC-9(c) / failure mode 10: the
  vendored pyodide-kernel wheel must still carry the transform-internals the
  gate depends on (``cleanup_transforms`` running before ``line_transforms``,
  and every transform being awaited).

All three run against SYNTHETIC fixtures built under ``tmp_path`` -- never a
real ``jupyter lite build`` output, which needs the vendored Pyodide and is
covered separately by the full-build CI step (spec section 9, T5's gate).
``assert_no_hardcoded_bootstrap_in_notebooks`` lives in ``test_base_path.py``
per the spec's own file assignment (section 8.1), not here.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build_repl  # noqa: E402 -- path setup must precede this

# --- shared fixture helpers ----------------------------------------------


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def _jupyter_lite_json(
    out_dir: Path,
    *,
    env: dict | None = None,
    disable_pypi: bool = True,
    pyodide_url: str | None = "./static/pyodide/pyodide.mjs",
    top_level_env: dict | None = None,
) -> None:
    kernel_settings: dict = {}
    if disable_pypi:
        kernel_settings["disablePyPIFallback"] = True
    if pyodide_url is not None:
        kernel_settings["pyodideUrl"] = pyodide_url
    if env is not None:
        kernel_settings["loadPyodideOptions"] = {"env": env}

    config_data = {
        "litePluginSettings": {
            "@jupyterlite/pyodide-kernel-extension:kernel": kernel_settings,
        }
    }
    if top_level_env is not None:
        # A misfiled key: sits at jupyter-config-data's own top level, not
        # nested under the kernel's litePluginSettings.loadPyodideOptions.env.
        config_data["loadPyodideOptions"] = {"env": top_level_env}

    _write_json(out_dir / "jupyter-lite.json", {"jupyter-config-data": config_data})


_GOOD_ENV = {"PYTHONSTARTUP": "/drive/praxis_startup.py"}


def _contents_index(out_dir: Path, paths: list[str]) -> None:
    _write_json(out_dir / "api" / "contents" / "all.json", {"content": [{"path": p} for p in paths]})


_KERNEL_PY_GOOD = (
    "class LiteKernel:\n"
    "    async def run(self, code):\n"
    "        code = await self.lite_transform_manager.transform_cell(code)\n"
    "        return code\n"
)
_KERNEL_PY_NO_AWAIT = (
    "class LiteKernel:\n"
    "    async def run(self, code):\n"
    "        code = self.lite_transform_manager.transform_cell(code)\n"
    "        return code\n"
)
_LITETRANSFORM_PY_GOOD = (
    "class LiteTransformManager:\n"
    "    async def transform_cell(self, lines):\n"
    "        for transform in self.cleanup_transforms + self.line_transforms:\n"
    "            lines = await transform(lines)\n"
    "        return lines\n"
)
_LITETRANSFORM_PY_NOT_AWAITED = (
    "class LiteTransformManager:\n"
    "    async def transform_cell(self, lines):\n"
    "        for transform in self.cleanup_transforms + self.line_transforms:\n"
    "            lines = transform(lines)\n"
    "        return lines\n"
)
_LITETRANSFORM_PY_REORDERED = (
    "class LiteTransformManager:\n"
    "    async def transform_cell(self, lines):\n"
    "        for transform in self.line_transforms + self.cleanup_transforms:\n"
    "            lines = await transform(lines)\n"
    "        return lines\n"
)
_LITETRANSFORM_PY_RENAMED_LIST = (
    "class LiteTransformManager:\n"
    "    async def transform_cell(self, lines):\n"
    "        for transform in self.cleanup_xforms + self.line_transforms:\n"
    "            lines = await transform(lines)\n"
    "        return lines\n"
)


def _wheel_dir(out_dir: Path) -> Path:
    return out_dir / build_repl._KERNEL_WHEEL_DIR


def _write_kernel_wheel(
    out_dir: Path,
    *,
    version: str = "0.8.2",
    kernel_py: str = _KERNEL_PY_GOOD,
    litetransform_py: str = _LITETRANSFORM_PY_GOOD,
    filename: str | None = None,
) -> Path:
    wheel_dir = _wheel_dir(out_dir)
    wheel_dir.mkdir(parents=True, exist_ok=True)
    name = filename or f"pyodide_kernel-{version}-py3-none-any.whl"
    path = wheel_dir / name
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("pyodide_kernel/kernel.py", kernel_py)
        zf.writestr("pyodide_kernel/litetransform.py", litetransform_py)
    return path


# --- assert_autosetup_env -------------------------------------------------


def test_autosetup_env_missing_config_file_fails(tmp_path):
    with pytest.raises(build_repl.BuildAssertionError, match="does not exist"):
        build_repl.assert_autosetup_env(tmp_path)


def test_autosetup_env_good_passes(tmp_path):
    _jupyter_lite_json(tmp_path, env=_GOOD_ENV)
    build_repl.assert_autosetup_env(tmp_path)  # must not raise


def test_autosetup_env_missing_key_fails(tmp_path):
    """No env at all -- the doit-regeneration shape (build_repl.py:227-247)."""
    _jupyter_lite_json(tmp_path, env=None)
    with pytest.raises(build_repl.BuildAssertionError, match="PYTHONSTARTUP"):
        build_repl.assert_autosetup_env(tmp_path)


def test_autosetup_env_wrong_path_fails(tmp_path):
    _jupyter_lite_json(tmp_path, env={"PYTHONSTARTUP": "/drive/wrong_name.py"})
    with pytest.raises(build_repl.BuildAssertionError, match="PYTHONSTARTUP"):
        build_repl.assert_autosetup_env(tmp_path)


def test_autosetup_env_misfiled_at_top_level_fails(tmp_path):
    """The key exists in the JSON tree, but not where the kernel addon reads
    it from -- nested under the kernel's own litePluginSettings block.
    """
    _jupyter_lite_json(tmp_path, env=None, top_level_env=_GOOD_ENV)
    with pytest.raises(build_repl.BuildAssertionError, match="PYTHONSTARTUP"):
        build_repl.assert_autosetup_env(tmp_path)


def test_autosetup_env_missing_disable_pypi_fallback_fails(tmp_path):
    _jupyter_lite_json(tmp_path, env=_GOOD_ENV, disable_pypi=False)
    with pytest.raises(build_repl.BuildAssertionError, match="disablePyPIFallback"):
        build_repl.assert_autosetup_env(tmp_path)


def test_autosetup_env_missing_pyodide_url_fails(tmp_path):
    _jupyter_lite_json(tmp_path, env=_GOOD_ENV, pyodide_url=None)
    with pytest.raises(build_repl.BuildAssertionError, match="pyodideUrl"):
        build_repl.assert_autosetup_env(tmp_path)


# --- assert_praxis_startup_shipped ----------------------------------------


def test_startup_shipped_staged_and_indexed_passes(tmp_path):
    (tmp_path / "files").mkdir(parents=True)
    (tmp_path / "files" / "praxis_startup.py").write_text("# shim\n")
    _contents_index(tmp_path, ["praxis_startup.py", "praxis_boot.py"])
    build_repl.assert_praxis_startup_shipped(tmp_path)  # must not raise


def test_startup_shipped_staged_but_unindexed_fails(tmp_path):
    (tmp_path / "files").mkdir(parents=True)
    (tmp_path / "files" / "praxis_startup.py").write_text("# shim\n")
    _contents_index(tmp_path, ["praxis_boot.py"])  # startup shim omitted
    with pytest.raises(build_repl.BuildAssertionError, match="MISSING from the contents index"):
        build_repl.assert_praxis_startup_shipped(tmp_path)


def test_startup_shipped_indexed_but_missing_fails(tmp_path):
    _contents_index(tmp_path, ["praxis_startup.py"])
    # No files/praxis_startup.py written on disk at all.
    with pytest.raises(build_repl.BuildAssertionError, match="does not exist"):
        build_repl.assert_praxis_startup_shipped(tmp_path)


def test_startup_shipped_missing_index_file_fails(tmp_path):
    (tmp_path / "files").mkdir(parents=True)
    (tmp_path / "files" / "praxis_startup.py").write_text("# shim\n")
    # No api/contents/all.json at all.
    with pytest.raises(build_repl.BuildAssertionError, match="contents index"):
        build_repl.assert_praxis_startup_shipped(tmp_path)


# --- assert_kernel_autosetup_contract -------------------------------------


def test_kernel_contract_good_wheel_passes(tmp_path):
    _write_kernel_wheel(tmp_path)
    build_repl.assert_kernel_autosetup_contract(tmp_path)  # must not raise


def test_kernel_contract_no_wheel_fails(tmp_path):
    _wheel_dir(tmp_path).mkdir(parents=True)
    with pytest.raises(build_repl.BuildAssertionError, match="found 0"):
        build_repl.assert_kernel_autosetup_contract(tmp_path)


def test_kernel_contract_missing_wheel_dir_fails(tmp_path):
    with pytest.raises(build_repl.BuildAssertionError, match="found 0"):
        build_repl.assert_kernel_autosetup_contract(tmp_path)


def test_kernel_contract_two_wheels_fails(tmp_path):
    _write_kernel_wheel(tmp_path)
    _write_kernel_wheel(tmp_path, filename="pyodide_kernel-0.8.2-py3-none-any.whl.bak.whl")
    with pytest.raises(build_repl.BuildAssertionError, match="found 2"):
        build_repl.assert_kernel_autosetup_contract(tmp_path)


def test_kernel_contract_wrong_version_fails(tmp_path):
    _write_kernel_wheel(tmp_path, version="0.9.0")
    with pytest.raises(build_repl.BuildAssertionError, match="0.9.0"):
        build_repl.assert_kernel_autosetup_contract(tmp_path)


def test_kernel_contract_missing_transform_cell_await_fails(tmp_path):
    _write_kernel_wheel(tmp_path, kernel_py=_KERNEL_PY_NO_AWAIT)
    with pytest.raises(build_repl.BuildAssertionError, match="literal"):
        build_repl.assert_kernel_autosetup_contract(tmp_path)


def test_kernel_contract_transform_not_awaited_fails(tmp_path):
    _write_kernel_wheel(tmp_path, litetransform_py=_LITETRANSFORM_PY_NOT_AWAITED)
    with pytest.raises(build_repl.BuildAssertionError, match="literal"):
        build_repl.assert_kernel_autosetup_contract(tmp_path)


def test_kernel_contract_reordered_loop_fails(tmp_path):
    """cleanup_transforms must run BEFORE line_transforms (which holds
    pip_magic) -- a reorder would let a first `%pip install` cell slip past
    the gate.
    """
    _write_kernel_wheel(tmp_path, litetransform_py=_LITETRANSFORM_PY_REORDERED)
    with pytest.raises(build_repl.BuildAssertionError, match="literal"):
        build_repl.assert_kernel_autosetup_contract(tmp_path)


def test_kernel_contract_renamed_list_fails(tmp_path):
    _write_kernel_wheel(tmp_path, litetransform_py=_LITETRANSFORM_PY_RENAMED_LIST)
    with pytest.raises(build_repl.BuildAssertionError, match="literal"):
        build_repl.assert_kernel_autosetup_contract(tmp_path)


def test_kernel_contract_missing_module_in_wheel_fails(tmp_path):
    wheel_dir = _wheel_dir(tmp_path)
    wheel_dir.mkdir(parents=True)
    with zipfile.ZipFile(wheel_dir / "pyodide_kernel-0.8.2-py3-none-any.whl", "w") as zf:
        zf.writestr("pyodide_kernel/kernel.py", _KERNEL_PY_GOOD)
        # litetransform.py deliberately omitted.
    with pytest.raises(build_repl.BuildAssertionError):
        build_repl.assert_kernel_autosetup_contract(tmp_path)


def test_kernel_contract_against_real_dist_wheel():
    """Read-only check against the real vendored wheel checked in at
    web-repl/dist, if a build happens to be present locally. Skips cleanly
    when it is not -- CI's real-build gate (spec section 9, T5) covers this
    path for real; this is a bonus, not the gate.
    """
    real_dist = Path(__file__).resolve().parents[1] / "dist"
    wheel_dir = _wheel_dir(real_dist)
    if not wheel_dir.is_dir() or not list(wheel_dir.glob(build_repl._KERNEL_WHEEL_GLOB)):
        pytest.skip("no local web-repl/dist build present")
    build_repl.assert_kernel_autosetup_contract(real_dist)  # must not raise
