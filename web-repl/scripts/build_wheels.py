#!/usr/bin/env python3
"""Build the browser wheels for the praxis web REPL.

Owns exactly two artifacts under ``web-repl/overlay/assets/wheels/``:

- ``pylabrobot-<version>+g<sha8>[.dirty]-py3-none-any.whl``, exported via
  ``git archive`` from the ``external/pylabrobot`` submodule AT ITS PINNED
  COMMIT, never by mutating or checking out the submodule.
- ``pylibftdi-0.0.0-py3-none-any.whl``, built from the checked-in stub
  source at ``web-repl/scripts/pylibftdi_stub/`` (owned by a different
  task; this script only builds it, never authors it).

Per ADR ``.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md``
(revision 2, accepted) there is NO ``praxis_browser`` package/wheel and NO
shared ``BUILD_ID`` tying two wheels together -- that scheme existed only to
keep two praxis-authored wheels in lockstep, and with a single praxis wheel
(zero, in fact -- praxis's own browser Python ships as loose fetched files)
it is meaningless. Drift detection is instead three independent detectors
(ADR Sec 2.3, D1/D2/D3) owned by other scripts. This script's job stops at:
produce correct, self-describing wheels, and prove each one is loadable.

See also: .praxia/docs/specs/260817_spec-wheel-build-plr-upgrade.md (T2/T3
describe this script's git-archive export and version-stamping behaviour,
preserved verbatim per ADR Sec 4.3's "Preserved verbatim" paragraph).

House rules: uv-run only, argparse + logging, narrow runs, fail loud.
"""

from __future__ import annotations

import argparse
import io
import logging
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

logger = logging.getLogger("build_wheels")

# --- fixed layout -----------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
WEB_REPL_ROOT = _THIS_FILE.parents[1]
REPO_ROOT = _THIS_FILE.parents[2]
SUBMODULE_DIR = REPO_ROOT / "external" / "pylabrobot"
PYLIBFTDI_STUB_DIR = WEB_REPL_ROOT / "scripts" / "pylibftdi_stub"
OUTPUT_DIR = WEB_REPL_ROOT / "overlay" / "assets" / "wheels"

# The pin this pipeline builds against. Phase 4 (260818) bumped it from
# d9651e2098cd269fc47e6aff80c9242a82d1b587 (0.1.6) to PLR 0.2.2; the PLR 1.0
# migration (260929) bumped it to 1.0.0b1. There is NO `v1.0.0b1` tag on this
# commit -- `git describe` reports `v0.2.1-376-g786ac2c4e` -- so the full SHA is
# the only correct way to name it.
# This script refuses to build against any other submodule commit.
EXPECTED_PLR_SHA = "786ac2c4e4f7afe37885af2d98ff5b0afe274c67"

KNOWN_TARGETS = ("pylabrobot", "pylibftdi")


class BuildError(RuntimeError):
    """Raised for any condition that must fail the build loudly (never silently)."""


# --- small subprocess helpers ------------------------------------------------


def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    logger.debug("+ %s%s", " ".join(str(c) for c in cmd), f"  (cwd={cwd})" if cwd else "")
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def _git(args: list[str], cwd: Path) -> str:
    return _run(["git", "-C", str(cwd), *args]).stdout.strip()


# --- pylabrobot: export, stamp, build ---------------------------------------


def resolve_pinned_sha() -> str:
    """Read the submodule's actual HEAD and assert it matches the declared pin."""
    sha = _git(["rev-parse", "HEAD"], SUBMODULE_DIR)
    if sha != EXPECTED_PLR_SHA:
        raise BuildError(
            f"external/pylabrobot HEAD is {sha}, but this pipeline builds AT THE "
            f"PINNED commit {EXPECTED_PLR_SHA}. Refusing to build against an "
            "unpinned submodule -- bump EXPECTED_PLR_SHA deliberately, never silently."
        )
    return sha


def submodule_is_dirty() -> bool:
    status = _run(["git", "-C", str(SUBMODULE_DIR), "status", "--porcelain"]).stdout
    return bool(status.strip())


def get_dirty_paths() -> str | None:
    """Get the dirty paths in the submodule as a formatted string, or None if clean."""
    status = _run(["git", "-C", str(SUBMODULE_DIR), "status", "--porcelain"]).stdout.strip()
    if not status:
        return None
    # Format as a multi-line string prefixed with indent for readable logging
    lines = ["  " + line for line in status.splitlines()]
    return "\n".join(lines)


def export_submodule_tree(sha: str, dest: Path) -> Path:
    """``git archive <sha> | tar -x`` into *dest*, WITHOUT touching the submodule
    worktree or index. Returns the path to the exported ``pylabrobot`` package dir.
    """
    dest.mkdir(parents=True, exist_ok=True)
    archive_bytes = subprocess.run(
        ["git", "-C", str(SUBMODULE_DIR), "archive", sha],
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as tf:
        tf.extractall(dest)  # noqa: S202 -- trusted source: our own pinned submodule
    pkg_dir = dest / "pylabrobot"
    if not pkg_dir.is_dir():
        raise BuildError(
            f"git archive {sha} for external/pylabrobot did not produce a "
            f"pylabrobot/ package dir under {dest} -- export is broken or empty."
        )
    return pkg_dir


def strip_test_modules(pkg_dir: Path) -> int:
    """Remove PLR's test suite from the exported tree before building, so the
    wheel does not carry it into the browser. Matches wheel-spec T3's patterns
    (files named ``*_tests.py``, any directory literally named ``tests``) plus
    ``conftest.py`` -- pytest-only fixture wiring, equally test infrastructure,
    that neither of T3's two patterns happens to catch.
    """
    removed = 0
    for path in sorted(pkg_dir.rglob("*_tests.py")):
        path.unlink()
        removed += 1
    for path in sorted(pkg_dir.rglob("conftest.py")):
        path.unlink()
        removed += 1
    for path in sorted(pkg_dir.rglob("tests"), reverse=True):
        if path.is_dir():
            shutil.rmtree(path)
            removed += 1
    if removed == 0:
        raise BuildError(
            f"test-strip pass removed nothing under {pkg_dir} -- expected PLR's "
            "*_tests.py modules and a tests/ dir at this pin. Either the export "
            "is empty or the strip patterns no longer match upstream's layout; "
            "either way this must not silently produce an unstripped wheel."
        )
    logger.info("stripped %d test file(s)/dir(s) from exported pylabrobot tree", removed)
    return removed


def stamp_version(pkg_dir: Path, sha: str, dirty_paths: str | None = None) -> str:
    """Stamp the version from the pinned commit sha, NOT from working tree state.

    The wheel is built via ``git archive <sha>``, which exports the **committed tree
    at that sha** and ignores the working tree. So the wheel's contents contain none
    of the dirty state. If dirty entries exist (pre-existing submodule dirt), emit
    a build-time WARNING naming them so a developer still sees it -- but do not
    stamp it into the wheel version, which would be false provenance.
    """
    version_txt = pkg_dir / "version.txt"
    if not version_txt.is_file():
        raise BuildError(f"{version_txt} missing from exported tree -- cannot stamp version")
    base = version_txt.read_text().strip()
    if not base:
        raise BuildError(f"{version_txt} is empty -- cannot compute +g<sha8> stamp")
    # Derive from the pinned sha that is actually archived, not from git describe --dirty
    local = f"g{sha[:8]}"
    stamped = f"{base}+{local}"
    version_txt.write_text(stamped + "\n")
    logger.info("stamped version: %s -> %s (from pinned commit, not working tree)", base, stamped)

    # Emit dirty signal as a WARNING, not a version suffix
    if dirty_paths:
        logger.warning(
            "submodule has pre-existing dirty entries (not included in archived wheel):\n%s",
            dirty_paths,
        )

    return stamped


def write_build_info(pkg_dir: Path, sha: str) -> None:
    """Write ``_praxis_build_info.py`` as PLAIN TOP-LEVEL STRING LITERALS --
    no f-strings, no computed values, no imports -- so the coherence checker
    can ``exec`` it into an empty namespace or AST-parse it without ever
    importing pylabrobot.
    """
    build_id = f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{sha[:8]}"
    built_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    lines = [
        "# Generated by web-repl/scripts/build_wheels.py. Do not edit by hand.",
        "# Plain top-level string-literal assignments only: readable by exec()",
        "# into an empty namespace or by AST-parsing, without importing pylabrobot.",
        f"PLR_SOURCE_SHA = {sha!r}",
        f"BUILD_ID = {build_id!r}",
        f"BUILT_AT = {built_at!r}",
        "",
    ]
    (pkg_dir / "_praxis_build_info.py").write_text("\n".join(lines))
    logger.info("wrote _praxis_build_info.py (PLR_SOURCE_SHA=%s, BUILD_ID=%s)", sha, build_id)


def uv_build_wheel(src_dir: Path, out_dir: Path, *, offline: bool) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["uv", "build", "--wheel", "--out-dir", str(out_dir)]
    if offline:
        cmd.append("--offline")
    result = subprocess.run(cmd, cwd=src_dir, capture_output=True, text=True)
    if result.returncode != 0:
        # Propagate failure loudly (do not swallow) -- this is the observable
        # difference a cold uv cache under --offline is REQUIRED to produce.
        raise BuildError(
            f"uv build --wheel failed in {src_dir} (exit {result.returncode}):\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        )
    wheels = sorted(out_dir.glob("*.whl"))
    if not wheels:
        raise BuildError(f"uv build exited 0 but produced no .whl in {out_dir}")
    if len(wheels) > 1:
        raise BuildError(f"uv build produced more than one wheel in {out_dir}: {wheels}")
    wheel = wheels[0]
    if wheel.stat().st_size == 0:
        raise BuildError(f"uv build produced an EMPTY wheel: {wheel}")
    return wheel


# --- self-verification: pkgutil.walk_packages over the BUILT wheel ---------

# PLR ships intentionally-guarded (try/except ImportError, HAS_SERIAL /
# USE_USB / HAS_PYLIBFTDI style) call sites AND, historically, a handful of
# genuinely UNGUARDED top-level `import serial` / `from pylibftdi import ...`
# call sites (verified at the 0.2.2 pin: pylabrobot/sealing/a4s_backend.py,
# pylabrobot/storage/cytomat/{cytomat,heraeus_cytomat_backend}.py,
# pylabrobot/peeling/xpeel_backend.py,
# pylabrobot/pumps/cole_parmer/masterflex_backend.py, and
# pylabrobot/plate_reading/agilent/biotek_synergyh1_backend.py). At the 1.0.0b1
# pin those moved under pylabrobot/legacy/ and the ones re-checked (a4s,
# cytomat, xpeel, masterflex, biotek_synergyh1) are now try-guarded, but the
# stubs below are kept: the walk imports every module and a stray unguarded
# site is exactly what they exist for. The stubbed names (`serial`, `usb`,
# `pylibftdi`) are THIRD-PARTY modules, not PLR paths, so PLR's reorganisation
# does not invalidate them. None of
# that is a defect in THIS build -- it is exactly why the real browser boot
# installs native module stubs (ADR Sec 4.3 design (C) / spec T6
# install_native_stubs()) for `serial`, `serial.tools`,
# `serial.tools.list_ports`, `usb`, `usb.core`, `usb.util` BEFORE pylabrobot
# is ever imported, and why pylibftdi ships as its own wheel. A throwaway
# venv with neither in place is not the browser environment, and testing
# against it would flag ~90 real modules as "broken" for a property that
# has nothing to do with whether THIS build removed something it shouldn't
# have. So: inject the same minimal stand-ins (import-time-shape only, not
# the real functional stubs -- those live in the bootstrap, a different
# task) before walking, then fail ONLY on ImportError/ModuleNotFoundError,
# which is the one signal a bad strip pass would actually produce.
_NATIVE_STUBS_PRELUDE = """\
import importlib
import sys
import types


def _stub_module(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


_serial = _stub_module("serial")
_serial.Serial = type("Serial", (), {})
_serial.SerialException = type("SerialException", (Exception,), {})
for _name, _val in [
    ("EIGHTBITS", 8), ("SEVENBITS", 7), ("SIXBITS", 6), ("FIVEBITS", 5),
    ("PARITY_NONE", "N"), ("PARITY_EVEN", "E"), ("PARITY_ODD", "O"),
    ("PARITY_MARK", "M"), ("PARITY_SPACE", "S"),
    ("STOPBITS_ONE", 1), ("STOPBITS_ONE_POINT_FIVE", 1.5), ("STOPBITS_TWO", 2),
]:
    setattr(_serial, _name, _val)
_serial_tools = _stub_module("serial.tools")
_serial.tools = _serial_tools
_serial_list_ports = _stub_module("serial.tools.list_ports")
_serial_list_ports.comports = lambda: []
_serial_tools.list_ports = _serial_list_ports

_usb = _stub_module("usb")
_usb.core = _stub_module("usb.core")
_usb.util = _stub_module("usb.util")

try:
    importlib.import_module("pylibftdi")
except ImportError:
    # No real pylibftdi wheel was installed alongside this one (e.g. an
    # `--only pylabrobot` run) -- fall back to a shape-only fake matching
    # the checked-in stub's own documented public surface
    # (web-repl/scripts/pylibftdi_stub/README.md).
    _ftdi = _stub_module("pylibftdi")
    _ftdi.FtdiError = type("FtdiError", (Exception,), {})
    _ftdi.LibraryMissingError = type("LibraryMissingError", (Exception,), {})
    _ftdi.Device = type("Device", (), {})
    _driver = _stub_module("pylibftdi.driver")
    _driver.USB_VID_LIST = []
    _driver.USB_PID_LIST = []
    _ftdi.driver = _driver
"""

_WALK_PROBE = """\
# NOTE: this does NOT use pkgutil.walk_packages's own recursion. That
# function must __import__() every package it descends into just to read
# its __path__, and any non-ImportError exception raised by an __init__.py
# (pylabrobot ships ~15 intentionally-broken deprecation-redirect shims,
# e.g. pylabrobot.resources.falcon, which raise NotImplementedError on
# import BY DESIGN) terminates the whole walk with no way to skip past it.
# Instead: discover every dotted module name from the installed wheel's
# on-disk layout (no import needed to enumerate), then import each leaf
# directly. A missing module -> ImportError/ModuleNotFoundError, which is
# exactly and only the signal a bad test-strip would produce. Any other
# exception (like the deprecation shims above) is upstream's own design
# and is reported but does not fail this check.
import importlib
import sys
from pathlib import Path

top_names = sys.argv[1:]


def discover(top):
    mod = importlib.import_module(top)
    pkg_paths = list(getattr(mod, "__path__", []) or [])
    names = [top]
    for pkg_path in pkg_paths:
        for py_file in sorted(Path(pkg_path).rglob("*.py")):
            parts = list(py_file.relative_to(pkg_path).parts)
            if parts[-1] == "__init__.py":
                parts = parts[:-1]
            else:
                parts[-1] = parts[-1][: -len(".py")]
            if parts:
                names.append(top + "." + ".".join(parts))
    return names


names = sorted({n for top in top_names for n in discover(top)})
import_failures = []
other_exceptions = []
for name in names:
    try:
        importlib.import_module(name)
    except (ImportError, ModuleNotFoundError) as exc:
        import_failures.append((name, repr(exc)))
    except Exception as exc:  # noqa: BLE001 -- classified below, not swallowed
        other_exceptions.append((name, repr(exc)))

print(f"WALKED {len(names)}", file=sys.stderr)
for name, exc in other_exceptions:
    print(f"NON-FATAL (not an import-strip signal) {name}: {exc}", file=sys.stderr)
if import_failures:
    for name, exc in import_failures:
        print(f"IMPORT-FAIL {name}: {exc}", file=sys.stderr)
    sys.exit(1)
if not names:
    print("WALKED 0 -- wheel claims a package with nothing importable", file=sys.stderr)
    sys.exit(1)
"""


# PLR 1.0's core `dependencies` (typing_extensions, websockets>=14) are imported
# at module top level across the tree (pylabrobot.resources, the legacy
# LiquidHandler, visualizer3D), so the throwaway venv -- which installs the wheel
# --no-deps to avoid dragging in optional hardware extras -- must supply them
# itself, or every such module reads as a false "test-strip removed too much".
# The browser gets the same two from Pyodide's own typing-extensions build and the
# vendored websockets wheel (web-repl/vendored_wheels.json), not from PyPI.
_PLR_CORE_RUNTIME_DEPS = ("typing_extensions", "websockets>=14")


def verify_wheel_importable(
    wheel: Path,
    top_level_names: list[str],
    *,
    extra_wheels: list[Path] | None = None,
    native_stubs: bool = False,
    runtime_deps: tuple[str, ...] = (),
    offline: bool = False,
) -> None:
    """Install *wheel* (plus any *extra_wheels*, all no-deps) into a throwaway
    venv and walk-import every module it claims to provide. Catches a
    test-strip (or any packaging step) that removed something a non-test
    module actually needs. When *native_stubs* is set, minimal serial/usb/
    pylibftdi stand-ins are injected first so guarded (and PLR's several
    genuinely unguarded) hardware imports resolve the same way they do once
    the real browser bootstrap installs its native stubs -- see
    _NATIVE_STUBS_PRELUDE for exactly what is and is not verified by this.
    """
    with tempfile.TemporaryDirectory(prefix="build_wheels-verify-") as tmp:
        venv_dir = Path(tmp) / "venv"
        _run(["uv", "venv", str(venv_dir)])
        python = venv_dir / "bin" / "python"
        for whl in [wheel, *(extra_wheels or [])]:
            install = subprocess.run(
                ["uv", "pip", "install", "--python", str(python), "--no-deps", str(whl)],
                capture_output=True,
                text=True,
            )
            if install.returncode != 0:
                raise BuildError(
                    f"self-verification: could not install {whl.name} into a "
                    f"throwaway venv:\n{install.stdout}\n{install.stderr}"
                )
        if runtime_deps:
            dep_cmd = ["uv", "pip", "install", "--python", str(python), *runtime_deps]
            if offline:
                dep_cmd.insert(3, "--offline")
            deps = subprocess.run(dep_cmd, capture_output=True, text=True)
            if deps.returncode != 0:
                raise BuildError(
                    f"self-verification: could not install runtime deps "
                    f"{list(runtime_deps)} into the throwaway venv:\n"
                    f"{deps.stdout}\n{deps.stderr}"
                )
        script = (_NATIVE_STUBS_PRELUDE if native_stubs else "") + _WALK_PROBE
        probe = subprocess.run(
            [str(python), "-c", script, *top_level_names],
            capture_output=True,
            text=True,
        )
        logger.debug("walk_packages probe stderr:\n%s", probe.stderr)
        if probe.returncode != 0:
            raise BuildError(
                f"self-verification FAILED for {wheel.name}: pkgutil.walk_packages "
                f"could not import every module the wheel claims to provide "
                f"({top_level_names}). This is the check that catches a test-strip "
                f"(or any step) that removed too much.\n{probe.stderr}"
            )
        walked_line = next(
            (line for line in probe.stderr.splitlines() if line.startswith("WALKED ")), "?"
        )
        logger.info("self-verification OK for %s (%s)", wheel.name, walked_line)


# --- per-target build functions ---------------------------------------------


def build_pylabrobot(
    *, offline: bool, keep_scratch: bool, pylibftdi_wheel: Path | None = None
) -> Path:
    sha = resolve_pinned_sha()
    dirty_paths = get_dirty_paths()
    scratch = Path(tempfile.mkdtemp(prefix="build_wheels-plr-src-"))
    out_scratch = Path(tempfile.mkdtemp(prefix="build_wheels-plr-out-"))
    try:
        pkg_dir = export_submodule_tree(sha, scratch)
        strip_test_modules(pkg_dir)
        stamp_version(pkg_dir, sha, dirty_paths)
        write_build_info(pkg_dir, sha)
        wheel = uv_build_wheel(scratch, out_scratch, offline=offline)
        verify_wheel_importable(
            wheel,
            ["pylabrobot"],
            extra_wheels=[pylibftdi_wheel] if pylibftdi_wheel else None,
            native_stubs=True,
            runtime_deps=_PLR_CORE_RUNTIME_DEPS,
            offline=offline,
        )
        return _publish(wheel, "pylabrobot-*.whl")
    finally:
        if not keep_scratch:
            shutil.rmtree(scratch, ignore_errors=True)
            shutil.rmtree(out_scratch, ignore_errors=True)
        else:
            logger.info("kept scratch dirs: %s , %s", scratch, out_scratch)


def build_pylibftdi(*, offline: bool, keep_scratch: bool, required: bool) -> Path | None:
    if not PYLIBFTDI_STUB_DIR.is_dir():
        msg = (
            f"pylibftdi stub source dir {PYLIBFTDI_STUB_DIR} does not exist -- "
            "it is authored by a different task. Nothing to build."
        )
        if required:
            raise BuildError(msg)
        logger.warning("%s Skipping pylibftdi.", msg)
        return None
    has_recipe = (PYLIBFTDI_STUB_DIR / "pyproject.toml").exists() or (
        PYLIBFTDI_STUB_DIR / "setup.py"
    ).exists()
    if not has_recipe:
        raise BuildError(
            f"{PYLIBFTDI_STUB_DIR} exists but has neither pyproject.toml nor "
            "setup.py -- no declared build recipe. Refusing to guess."
        )
    out_scratch = Path(tempfile.mkdtemp(prefix="build_wheels-ftdi-out-"))
    try:
        wheel = uv_build_wheel(PYLIBFTDI_STUB_DIR, out_scratch, offline=offline)
        verify_wheel_importable(wheel, ["pylibftdi"])
        return _publish(wheel, "pylibftdi-*.whl")
    finally:
        if not keep_scratch:
            shutil.rmtree(out_scratch, ignore_errors=True)
        else:
            logger.info("kept scratch dir: %s", out_scratch)


def _publish(built_wheel: Path, stale_glob: str) -> Path:
    """Copy *built_wheel* into OUTPUT_DIR, removing any stale wheel(s) matching
    *stale_glob* first so a rebuild never leaves two versions of the same
    package sitting side by side.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in OUTPUT_DIR.glob(stale_glob):
        logger.info("removing stale wheel: %s", stale.name)
        stale.unlink()
    dest = OUTPUT_DIR / built_wheel.name
    shutil.copy2(built_wheel, dest)
    if not dest.is_file() or dest.stat().st_size == 0:
        raise BuildError(f"publish step failed to produce a non-empty {dest}")
    logger.info("published %s (%d bytes)", dest, dest.stat().st_size)
    return dest


# --- CLI ----------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--only",
        choices=KNOWN_TARGETS,
        default=None,
        help="Build only this wheel (default: build every available target).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Pass --offline to uv build. Requires a warm uv cache; a cold "
        "cache MUST fail (that failure is the point -- see GATE G3).",
    )
    parser.add_argument(
        "--keep-scratch",
        action="store_true",
        help="Do not delete scratch export/build directories (debugging).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug-level logging.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    targets = [args.only] if args.only else list(KNOWN_TARGETS)
    produced: dict[str, Path] = {}
    try:
        # Build pylibftdi first when both targets are in play, so pylabrobot's
        # self-verification can install the REAL stub wheel alongside it
        # rather than falling back to _NATIVE_STUBS_PRELUDE's shape-only fake.
        pylibftdi_wheel: Path | None = None
        if "pylibftdi" in targets:
            pylibftdi_wheel = build_pylibftdi(
                offline=args.offline,
                keep_scratch=args.keep_scratch,
                required=args.only == "pylibftdi",
            )
            if pylibftdi_wheel is not None:
                produced["pylibftdi"] = pylibftdi_wheel
        if "pylabrobot" in targets:
            produced["pylabrobot"] = build_pylabrobot(
                offline=args.offline,
                keep_scratch=args.keep_scratch,
                pylibftdi_wheel=pylibftdi_wheel,
            )
    except BuildError as exc:
        logger.error("%s", exc)
        return 1

    if not produced:
        logger.error("no wheels were produced -- nothing to build or everything was skipped")
        return 1

    for name, path in produced.items():
        logger.info("OK %s -> %s", name, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
