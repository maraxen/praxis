#!/usr/bin/env python3
"""CI gate: the browser IO shims accept every call the shipped pylabrobot wheel
makes of the classes they replace.

Builds the same throwaway venv as ``check_wheel_contract.py`` (the wheels from
web-repl's manifest, installed ``--no-deps``, exactly like the browser's
micropip), then runs ``shim_contract_probe.py`` inside it against
``web-repl/overlay/assets/shims/``. See the probe's docstring for what is
checked and why; see ``check_wheel_contract.py``'s for why the venv is not
optional (the repo venv has pylabrobot as an EDITABLE submodule install, so a
check run there would read the submodule source, not the wheel being shipped).

Exit 0 only on ``SHIM-CONTRACT-OK`` from a probe whose ``pylabrobot.__file__``
is confirmed to be the wheel in site-packages.

    uv run python web-repl/scripts/check_shim_contract.py
    uv run python web-repl/scripts/check_shim_contract.py --shims-dir <mutated copy>   # negative control

House rules: uv-run only, argparse + logging, narrow scope, fail loud.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger("check_shim_contract")

_THIS_FILE = Path(__file__).resolve()
SCRIPTS_DIR = _THIS_FILE.parent
WEB_REPL_ROOT = SCRIPTS_DIR.parent
REPO_ROOT = WEB_REPL_ROOT.parent
SHIMS_DIR = WEB_REPL_ROOT / "overlay" / "assets" / "shims"
PROBE = SCRIPTS_DIR / "shim_contract_probe.py"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_wheels  # noqa: E402 -- path setup must precede this import
import check_wheel_contract  # noqa: E402 -- path setup must precede this import


def run_probe(python: Path, shims_dir: Path, report_path: Path | None = None) -> subprocess.CompletedProcess:
    """Run the probe under ``python`` with the native-stubs prelude installed first.

    The prelude (``build_wheels._NATIVE_STUBS_PRELUDE``) stands in for pyserial /
    pyusb, which ``--no-deps`` deliberately leaves out, so ``pylabrobot.io.*``
    imports the same way it does in Pyodide.
    """
    argv = ["--shims-dir", str(shims_dir)]
    if report_path is not None:
        argv += ["--json", str(report_path)]
    script = (
        build_wheels._NATIVE_STUBS_PRELUDE
        + "\nimport runpy, sys\n"
        + f"sys.argv = [{str(PROBE)!r}, *{argv!r}]\n"
        + f"runpy.run_path({str(PROBE)!r}, run_name='__main__')\n"
    )
    return subprocess.run([str(python), "-c", script], capture_output=True, text=True)


def check_shim_contract(
    *,
    web_repl_root: Path,
    repo_root: Path,
    shims_dir: Path,
    keep_venv: bool,
    report_path: Path | None,
) -> int:
    tmp_root = Path(tempfile.mkdtemp(prefix="check_shim_contract-"))
    try:
        try:
            python = check_wheel_contract.build_throwaway_venv(
                tmp_root / "venv", web_repl_root=web_repl_root, repo_root=repo_root
            )
        except check_wheel_contract.ContractError as exc:
            logger.error("%s", exc)
            return 1

        probe = run_probe(python, shims_dir, report_path)
        plr_lines = [line for line in probe.stdout.splitlines() if line.startswith("PYLABROBOT_FILE=")]
        if not plr_lines:
            logger.error(
                "probe did not run to completion:\nstdout:\n%s\nstderr:\n%s",
                probe.stdout,
                probe.stderr,
            )
            return 1
        plr_file = plr_lines[0].split("=", 1)[1]
        if "external" in Path(plr_file).parts or "site-packages" not in plr_file:
            logger.error(
                "pylabrobot.__file__ = %s is not the installed wheel -- refusing to "
                "report a result that would pass identically against an empty wheel.",
                plr_file,
            )
            return 1
        logger.info("pylabrobot.__file__ = %s (the built wheel)", plr_file)
        for line in probe.stdout.splitlines():
            if line.startswith(("CALL_SITES", "USAGES", "WAIVED_UNUSED")):
                logger.info("%s", line)
        if probe.returncode != 0 or "SHIM-CONTRACT-OK" not in probe.stdout:
            logger.error("shim contract FAILED against the built wheel:\n%s", probe.stderr)
            return 1
        logger.info("shim contract OK")
        return 0
    finally:
        if keep_venv:
            logger.info("kept throwaway venv+tmp dir: %s", tmp_root)
        else:
            shutil.rmtree(tmp_root, ignore_errors=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--web-repl-root", type=Path, default=WEB_REPL_ROOT)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--shims-dir",
        type=Path,
        default=SHIMS_DIR,
        help="Shim modules to check (default: the shipped overlay). Point at a "
        "mutated copy to observe the gate failing.",
    )
    parser.add_argument("--json", type=Path, help="Write the probe's full JSON report here.")
    parser.add_argument("--keep-venv", action="store_true", help="Do not delete the throwaway venv.")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    return check_shim_contract(
        web_repl_root=args.web_repl_root.resolve(),
        repo_root=args.repo_root.resolve(),
        shims_dir=args.shims_dir.resolve(),
        keep_venv=args.keep_venv,
        report_path=args.json.resolve() if args.json else None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
