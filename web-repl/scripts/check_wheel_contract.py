#!/usr/bin/env python3
"""CI-invocable arm of R17b (wheel spec :202, :330; ADR Sec 4.3 "preserved
verbatim: ... check_wheel_contract.py").

Creates a throwaway venv under ``$TMPDIR``, installs the wheels named in
web-repl's generated manifest ``--no-deps`` (mirroring the browser's own
micropip install, which is ``deps=False`` at every call site), runs
``plr_contract.CONTRACT`` as a subprocess PROBE inside that venv, and
asserts the venv's ``pylabrobot.__file__`` does **NOT** resolve under
``external/``.

**The editable-install trap, which is why this script exists at all:** root
``pyproject.toml`` (``[tool.uv.sources] pylabrobot = { path =
"external/pylabrobot", editable = true }``) installs pylabrobot as an
EDITABLE PATH dependency. A contract check run in THIS repo's own venv would
therefore import the submodule SOURCE, not the wheel this script is meant to
gate -- and would pass unchanged even against an empty wheel. Every
assertion below runs inside a disposable venv, built fresh, with ONLY the
wheels named in the manifest installed ``--no-deps``.

**Path deviation from the wheel spec, noted deliberately** (same rationale
as ``check_wheel_coherence.py``'s docstring): this file lives under
``web-repl/scripts/`` per the ADR's canonical tree, not repo-root
``scripts/`` as T14's file list (:319) has it.

This is the standalone CLI/CI counterpart of the pytest fixture and
wheel-backed test functions in ``web-repl/tests/test_plr_contract.py`` (see
that file for the fuller documented rationale: the native-stubs prelude,
the DeprecationWarning escalation, why CPython 3.11 is pinned for the
throwaway venv rather than whatever the outer interpreter is). CI (wheel
spec :141, :322) invokes THIS script directly --
``uv run python scripts/check_wheel_contract.py`` -- independent of pytest.

House rules: uv-run only, argparse + logging, narrow scope, fail loud.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger("check_wheel_contract")

# --- fixed layout (ADR Sec 2.1 canonical tree) -------------------------------
_THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = _THIS_FILE.parent
WEB_REPL_ROOT = SCRIPTS_DIR.parent
REPO_ROOT = WEB_REPL_ROOT.parent
TESTS_DIR = WEB_REPL_ROOT / "tests"

for _path in (SCRIPTS_DIR, TESTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import build_manifest  # noqa: E402 -- path setup must precede this import
import build_wheels  # noqa: E402 -- path setup must precede this import
import plr_contract  # noqa: E402 -- path setup must precede this import

# Pinned for the same reason web-repl/tests/test_plr_contract.py pins it:
# CPython 3.14's stdlib itself raises DeprecationWarning under
# `pylabrobot.centrifuge` (ctypes._layout.get_layout, unrelated to
# pylabrobot's own API), which would make this script's escalation fire on
# a false positive. 3.11 sits inside CI's actual 3.10/3.11/3.12 matrix
# (wheel spec :141) and does not exhibit it.
_VENV_PYTHON = "3.11"

_CONTRACT_CHECK_BODY = """\
import importlib
import json
import sys
import warnings

contract = json.load(open(sys.argv[1], encoding="utf-8"))
warnings.simplefilter("error", DeprecationWarning)

missing = []
for mod_name, sym_name in contract:
    try:
        mod = importlib.import_module(mod_name)
        getattr(mod, sym_name)
    except Exception as exc:  # noqa: BLE001 -- reported below, not swallowed
        missing.append(f"{mod_name}.{sym_name}: {exc!r}")

import pylabrobot

print("PYLABROBOT_FILE=" + pylabrobot.__file__)

if missing:
    for line in missing:
        print("CONTRACT-FAIL " + line, file=sys.stderr)
    sys.exit(1)
print(f"CONTRACT-OK {len(contract)}")
"""


class ContractError(RuntimeError):
    """Raised for a fatal setup problem (missing wheel, venv creation
    failure, etc). Distinguished from a genuine CONTRACT-FAIL so the CLI
    can report each with an accurate message.
    """


def build_throwaway_venv(venv_dir: Path, *, web_repl_root: Path, repo_root: Path) -> Path:
    """Resolves wheel filenames via ``build_manifest.build_manifest()`` --
    the SAME generator ``manifest.json`` is produced from -- rather than
    reading the checked-in ``manifest.json`` off disk directly, so this
    script is correct even when the checked-in file is momentarily stale
    relative to what is actually in ``overlay/assets/wheels/`` (observed
    live in this repo: the checked-in manifest's pylabrobot filename once
    carried a ``.dirty`` suffix the on-disk wheel did not). ``build_manifest()``
    is pure -- it globs the wheels directory fresh and never writes anything.
    """
    wheels_dir = web_repl_root / "overlay" / "assets" / "wheels"
    manifest = build_manifest.build_manifest(web_repl_root=web_repl_root, repo_root=repo_root, dev=False)
    by_package = {entry["package"]: entry for entry in manifest["wheels"]}
    for required in ("pylabrobot", "pylibftdi"):
        if required not in by_package:
            raise ContractError(
                f"{required} wheel not found under {wheels_dir} -- run "
                "`uv run python web-repl/scripts/build_wheels.py` first."
            )
    plr_wheel = wheels_dir / by_package["pylabrobot"]["filename"]
    ftdi_wheel = wheels_dir / by_package["pylibftdi"]["filename"]
    for wheel in (plr_wheel, ftdi_wheel):
        if not wheel.is_file():
            raise ContractError(f"missing {wheel} on disk -- run build_wheels.py first.")

    venv_result = subprocess.run(
        ["uv", "venv", "--python", _VENV_PYTHON, str(venv_dir)],
        capture_output=True,
        text=True,
    )
    if venv_result.returncode != 0:
        raise ContractError(
            f"uv venv --python {_VENV_PYTHON} failed:\n{venv_result.stdout}\n{venv_result.stderr}"
        )
    python = venv_dir / "bin" / "python"

    install = subprocess.run(
        [
            "uv", "pip", "install",
            "--python", str(python),
            "--no-deps",
            str(plr_wheel), str(ftdi_wheel),
        ],
        capture_output=True,
        text=True,
    )
    if install.returncode != 0:
        raise ContractError(f"throwaway venv install failed:\n{install.stdout}\n{install.stderr}")

    # PLR 1.0's core deps (typing_extensions, websockets>=14) are imported at module
    # top level, and --no-deps installs neither. The browser gets them anyway -- the
    # bootstrap requests typing-extensions from the Pyodide lock and websockets is a
    # vendored wheel -- so the throwaway venv must supply the same two, or the probe
    # fails on ModuleNotFoundError instead of testing the contract.
    deps = subprocess.run(
        ["uv", "pip", "install", "--python", str(python), *build_wheels._PLR_CORE_RUNTIME_DEPS],
        capture_output=True,
        text=True,
    )
    if deps.returncode != 0:
        raise ContractError(f"throwaway venv runtime-deps install failed:\n{deps.stdout}\n{deps.stderr}")
    return python


def run_contract_probe(python: Path, contract, tmp_dir: Path) -> subprocess.CompletedProcess:
    contract_path = tmp_dir / "contract.json"
    contract_path.write_text(json.dumps([list(pair) for pair in contract]), encoding="utf-8")
    # Reused, not reimplemented: build_wheels._NATIVE_STUBS_PRELUDE already
    # solves the exact problem this probe hits importing pylabrobot.storage
    # (for Incubator) inside a --no-deps venv -- see that module's own
    # comment for why (storage/__init__.py -> cytomat.py does an UNGUARDED
    # `import serial`).
    script = build_wheels._NATIVE_STUBS_PRELUDE + "\n" + _CONTRACT_CHECK_BODY
    return subprocess.run(
        [str(python), "-c", script, str(contract_path)],
        capture_output=True,
        text=True,
    )


def check_wheel_contract(*, web_repl_root: Path, repo_root: Path, keep_venv: bool) -> int:
    tmp_root = Path(tempfile.mkdtemp(prefix="check_wheel_contract-"))
    venv_dir = tmp_root / "venv"
    try:
        try:
            python = build_throwaway_venv(venv_dir, web_repl_root=web_repl_root, repo_root=repo_root)
        except ContractError as exc:
            logger.error("%s", exc)
            return 1

        # R17b's own integrity check: this whole script is vacuous if the
        # probe below secretly reads the editable submodule source instead
        # of the wheel just installed --no-deps.
        identity = subprocess.run(
            [str(python), "-c", "import pylabrobot; print(pylabrobot.__file__)"],
            capture_output=True,
            text=True,
        )
        if identity.returncode != 0:
            logger.error(
                "could not import pylabrobot inside the throwaway venv:\nstdout:\n%s\nstderr:\n%s",
                identity.stdout, identity.stderr,
            )
            return 1
        plr_file = identity.stdout.strip()
        if "external" in Path(plr_file).parts:
            logger.error(
                "pylabrobot.__file__ resolved UNDER external/ (%s) -- this venv is "
                "reading the editable submodule source, not the built wheel. The "
                "contract probe would pass identically against an empty wheel; "
                "refusing to report a meaningful result.",
                plr_file,
            )
            return 1
        if "site-packages" not in plr_file:
            logger.error(
                "pylabrobot.__file__ (%s) is not under site-packages -- unexpected "
                "throwaway-venv layout, refusing to trust the result.",
                plr_file,
            )
            return 1
        logger.info("pylabrobot.__file__ = %s (confirmed NOT under external/)", plr_file)

        probe = run_contract_probe(python, plr_contract.CONTRACT, tmp_root)
        if probe.returncode != 0:
            logger.error(
                "CONTRACT-FAIL against the built wheel:\nstdout:\n%s\nstderr:\n%s",
                probe.stdout, probe.stderr,
            )
            return 1
        last_line = probe.stdout.strip().splitlines()[-1] if probe.stdout.strip() else ""
        logger.info("contract OK: %s", last_line)
        return 0
    finally:
        if keep_venv:
            logger.info("kept throwaway venv+tmp dir: %s", tmp_root)
        else:
            shutil.rmtree(tmp_root, ignore_errors=True)


# --- CLI -----------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--web-repl-root",
        type=Path,
        default=WEB_REPL_ROOT,
        help="Override web-repl/ root (testing only -- points at a scratch tree "
        "with a deliberately mutated wheel for the negative arm).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Override superproject root used for `git rev-parse HEAD` (testing only).",
    )
    parser.add_argument("--keep-venv", action="store_true", help="Do not delete the throwaway venv (debugging).")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug-level logging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    return check_wheel_contract(
        web_repl_root=args.web_repl_root.resolve(),
        repo_root=args.repo_root.resolve(),
        keep_venv=args.keep_venv,
    )


if __name__ == "__main__":
    raise SystemExit(main())
