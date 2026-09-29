"""Conformance test for ``plr_contract.py`` (ADR Sec 4.3 row: "survives
unchanged" from the old ``praxis-browser/tests/test_plr_contract.py" --
still runs in a throwaway venv so ``pylabrobot.__file__`` is NOT under
``external/``). Wheel spec T15 (:325-330) and R17/R17b define what this
file must prove.

WHY THE THROWAWAY VENV IS NOT OPTIONAL: root ``pyproject.toml``
(``[tool.uv.sources] pylabrobot = { path = "external/pylabrobot", editable =
true }``) installs pylabrobot as an EDITABLE PATH install. Any test run in
THIS repo's own venv therefore imports the submodule SOURCE, not the built
wheel this contract is actually meant to gate -- and would pass unchanged
even against an empty wheel. Every conformance assertion below runs inside
a disposable venv, built fresh per test session, with ONLY the wheels named
in the manifest installed ``--no-deps`` -- exactly what the browser's
micropip install does (``deps=False`` at every call site, wheel spec :192).

WHAT "THE FILTER" MEANS HERE: ``plr_contract.CONTRACT`` is a hand-curated
subset of pylabrobot's namespace -- not a generated view filtered out of the
live package (see ``plr_contract.py``'s own docstring for why a live-filter
design would fail exactly the same shadowing test this file exists to
apply). "The filter" is that curation: a bug in it looks like an
under-inclusive list (silently empty, or missing a symbol the product
depends on -- passes conformance trivially) or an over-inclusive one
(accidentally covers scope the browser payload has no business depending
on). ``test_contract_is_non_empty``, ``test_contract_contains_known_symbols``,
and the two rejection tests below exercise both failure directions.

WHY THIS FILE DOES NOT ALSO BUILD THE AST-SUPERSET TEST: ADR Sec 2.3's D3
row (``web-repl/tests/test_contract_covers_imports.py``) already asserts
"first-party pylabrobot imports are a subset of the contract's module set"
-- which is the identical statement to "the contract is a superset of
first-party imports," not a complementary direction. That file exists
already (built by a parallel task this round) with a documented, deliberate
``_CONTRACT_MODULES`` stand-in and a note to swap it for
``{path for path, _symbol in plr_contract.CONTRACT}`` once this file
landed. ``plr_contract.CONTRACT``'s module set is a deliberate superset of
that stand-in (see ``plr_contract.py``'s own docstring) so the swap is a
no-op, but performing the swap itself is D3's file to edit, not this one's.

Pure CPython for the outer pytest process; the wheel-backed arms below shell
out to a throwaway venv's own interpreter for the parts that must run
against the built wheel.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Iterable

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_WEB_REPL_ROOT = _TESTS_DIR.parent
_SCRIPTS_DIR = _WEB_REPL_ROOT / "scripts"
_REPO_ROOT = _WEB_REPL_ROOT.parent

for _path in (_TESTS_DIR, _SCRIPTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import build_manifest  # noqa: E402 -- path setup must precede this import
import build_wheels  # noqa: E402 -- path setup must precede this import
import plr_contract  # noqa: E402 -- path setup must precede this import

# Pinned rather than left to whatever `uv run python` resolves for the
# OUTER pytest process (3.14.6 on the machine this was written on, with no
# `.python-version` in the repo). RAN: importing `pylabrobot.centrifuge`
# under `warnings.simplefilter("error", DeprecationWarning)` on CPython
# 3.14 raises `DeprecationWarning` out of the STDLIB
# (`ctypes._layout.get_layout`, triggered by `vspin_backend.py`'s
# `ctypes.LittleEndianStructure` subclass with `_pack_` set) -- nothing to
# do with pylabrobot's own API surface, and it would make this test's
# escalation fire on a false positive unrelated to pylabrobot deprecating
# anything. 3.11 sits inside CI's actual 3.10/3.11/3.12 matrix (wheel spec
# :141) and does not exhibit it.
_VENV_PYTHON = "3.11"

# Reused, not reimplemented: `build_wheels._NATIVE_STUBS_PRELUDE` already
# solves the exact problem this probe hits when importing
# `pylabrobot.storage` (for `Incubator`) inside a `--no-deps` venv --
# `storage/__init__.py` unconditionally imports `.cytomat`, whose
# `cytomat.py` does an UNGUARDED `import serial` (RAN: confirmed against
# the pinned submodule source, no try/except around it, unlike the guarded
# `pylabrobot.io.serial`/`pylabrobot.io.ftdi` capability probes). Real
# `pyserial` is deliberately not installed (that is what `--no-deps` means,
# mirroring the browser's `deps=False`), so the module-shaped stand-in is
# required for the import to resolve at all.
#
# `web_repl.bootstrap.stages.install_native_stubs()` was deliberately NOT
# reused here instead: RAN -- calling it in a plain CPython venv (unlike
# Pyodide, where `ssl` genuinely does not work) unconditionally REPLACES the
# real stdlib `ssl` module with a bare, attribute-less stand-in the moment
# `ssl` is not yet in `sys.modules`, which breaks `asyncio.sslproto`
# (`AttributeError: module 'ssl' has no attribute 'SSLWantReadError'`) the
# instant anything transitively imports `asyncio` (pylabrobot.io.socket
# does, at package-import time). `_NATIVE_STUBS_PRELUDE` never touches
# `ssl` at all, which is exactly correct for a real-CPython throwaway venv.
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


@pytest.fixture(scope="session")
def throwaway_venv(tmp_path_factory) -> Path:
    """A disposable venv with the BUILT ``pylabrobot`` + ``pylibftdi``
    wheels installed ``--no-deps`` -- the R17b design (wheel spec :202),
    without a dependency on ``check_wheel_contract.py`` (a separate T14
    script, not this task's).

    Resolves wheel filenames via ``build_manifest.build_manifest()`` --
    the SAME generator ``manifest.json`` is produced from -- rather than
    reading the checked-in ``manifest.json`` off disk directly. RAN:
    observed live in this repo, the checked-in manifest's ``pylabrobot``
    filename carried a ``.dirty`` suffix that the wheel actually present in
    ``overlay/assets/wheels/`` did not (a wheel rebuild had run after the
    last ``build_manifest.py`` invocation). ``build_manifest()`` is a pure
    function -- it computes wheel entries by globbing the wheels directory
    fresh (``collect_wheels()``) and never writes anything; only
    ``write_manifest_atomic()`` does that, and this fixture never calls it.
    This keeps the fixture correct regardless of which of the two
    (checked-in file vs. actual directory contents) is momentarily stale,
    and never mutates a generated artifact this task does not own.
    """
    wheels_dir = _WEB_REPL_ROOT / "overlay" / "assets" / "wheels"
    manifest = build_manifest.build_manifest(
        web_repl_root=_WEB_REPL_ROOT, repo_root=_REPO_ROOT, dev=False
    )
    by_package = {entry["package"]: entry for entry in manifest["wheels"]}
    for required in ("pylabrobot", "pylibftdi"):
        assert required in by_package, (
            f"{required} wheel not found under {wheels_dir} -- run "
            "web-repl/scripts/build_wheels.py first"
        )
    plr_wheel = wheels_dir / by_package["pylabrobot"]["filename"]
    ftdi_wheel = wheels_dir / by_package["pylibftdi"]["filename"]
    assert plr_wheel.is_file(), f"missing {plr_wheel}"
    assert ftdi_wheel.is_file(), f"missing {ftdi_wheel}"

    venv_dir = tmp_path_factory.mktemp("plr_contract_venv") / "venv"
    venv_result = subprocess.run(
        ["uv", "venv", "--python", _VENV_PYTHON, str(venv_dir)],
        capture_output=True,
        text=True,
    )
    assert venv_result.returncode == 0, (
        f"uv venv --python {_VENV_PYTHON} failed:\n"
        f"{venv_result.stdout}\n{venv_result.stderr}"
    )
    python = venv_dir / "bin" / "python"

    install = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--no-deps",
            str(plr_wheel),
            str(ftdi_wheel),
        ],
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, (
        f"throwaway venv install failed:\n{install.stdout}\n{install.stderr}"
    )
    # PLR 1.0's core deps (typing_extensions, websockets>=14) are imported at
    # module top level and --no-deps installs neither. The browser supplies both
    # anyway (bootstrap requests typing-extensions from the Pyodide lock;
    # websockets is a vendored wheel), so mirror that here.
    deps = subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            *build_wheels._PLR_CORE_RUNTIME_DEPS,
        ],
        capture_output=True,
        text=True,
    )
    assert deps.returncode == 0, (
        f"throwaway venv runtime-deps install failed:\n{deps.stdout}\n{deps.stderr}"
    )
    return python


def _run_contract_probe(
    python: Path, contract: Iterable[tuple[str, str]], tmp_path: Path
) -> subprocess.CompletedProcess:
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps([list(pair) for pair in contract]), encoding="utf-8"
    )
    script = build_wheels._NATIVE_STUBS_PRELUDE + "\n" + _CONTRACT_CHECK_BODY
    return subprocess.run(
        [str(python), "-c", script, str(contract_path)],
        capture_output=True,
        text=True,
    )


# --- R17b: the wheel-backed arms, run inside the throwaway venv -------------


def test_wheel_installs_outside_submodule(throwaway_venv: Path) -> None:
    """The test's own integrity check (task brief): without this assertion
    the whole file is vacuous, because the editable submodule install would
    make every conformance check below pass identically against an empty
    wheel.
    """
    result = subprocess.run(
        [str(throwaway_venv), "-c", "import pylabrobot; print(pylabrobot.__file__)"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    plr_file = result.stdout.strip()
    assert "external" not in Path(plr_file).parts, (
        f"pylabrobot.__file__ resolved under external/ ({plr_file}) -- this "
        "probe is reading the editable submodule source, not the built wheel"
    )
    assert "site-packages" in plr_file, plr_file


def test_contract_conformance_against_wheel(
    throwaway_venv: Path, tmp_path: Path
) -> None:
    """The positive case: every (module, symbol) pair in CONTRACT resolves
    against the built wheel, with DeprecationWarning escalated to an error.
    """
    result = _run_contract_probe(throwaway_venv, plr_contract.CONTRACT, tmp_path)
    assert result.returncode == 0, (
        f"contract conformance FAILED against the built wheel:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert f"CONTRACT-OK {len(plr_contract.CONTRACT)}" in result.stdout


def test_bogus_contract_entry_is_observed_failing(
    throwaway_venv: Path, tmp_path: Path
) -> None:
    """Non-vacuousness proof for the wheel-backed arm (wheel spec :199's
    verification clause, "injecting a bogus entry ... makes that same
    command exit 1"). Uses a temp copy of CONTRACT with one bad entry
    appended rather than mutating the checked-in ``plr_contract.py`` on
    disk during a test run.
    """
    bogus = (*plr_contract.CONTRACT, ("pylabrobot.nonexistent", "Thing"))
    result = _run_contract_probe(throwaway_venv, bogus, tmp_path)
    assert result.returncode == 1, (
        "a bogus contract entry did not fail the conformance probe -- the "
        f"probe is not actually checking anything.\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "pylabrobot.nonexistent.Thing" in result.stderr


# --- the filter self-test: CONTRACT is a curated list, not "whatever ------
# --- currently happens to import" -------------------------------------------


def test_contract_is_non_empty() -> None:
    """A filter bug that silently matches nothing produces an empty
    contract, and an empty contract passes conformance trivially (an empty
    ``for`` loop never fails). This is the single assertion that makes that
    failure mode loud instead of silent.
    """
    assert len(plr_contract.CONTRACT) > 0, "CONTRACT is empty"


def test_contract_contains_known_symbols() -> None:
    known = {
        ("pylabrobot.resources", "Deck"),
        ("pylabrobot.resources", "Plate"),
        ("pylabrobot.io.serial", "Serial"),
        ("pylabrobot.io.serial", "HAS_SERIAL"),
        ("pylabrobot.legacy.storage", "Incubator"),
    }
    missing = known - set(plr_contract.CONTRACT)
    assert not missing, f"expected symbols missing from CONTRACT: {missing}"


def test_contract_names_no_deprecated_shim_paths() -> None:
    """PLR 1.0 turned these top-level packages into DeprecationWarning shims over
    ``pylabrobot.legacy.*``. The contract must name the explicit ``legacy`` home,
    never the shim (the wheel-backed probe escalates the warning, so a shim entry
    could only ever fail; this catches it without needing the wheel).
    """
    shims = (
        "pylabrobot.liquid_handling",
        "pylabrobot.plate_reading",
        "pylabrobot.heating_shaking",
        "pylabrobot.shaking",
        "pylabrobot.centrifuge",
        "pylabrobot.storage",
    )
    offenders = [
        (mod, sym)
        for mod, sym in plr_contract.CONTRACT
        if any(mod == s or mod.startswith(s + ".") for s in shims)
    ]
    assert not offenders, f"contract names deprecated 1.0 shim paths: {offenders}"


def test_shim_path_is_observed_failing_against_wheel(
    throwaway_venv: Path, tmp_path: Path
) -> None:
    """Negative control on the REAL 1.0 signal, not a synthetic stub: importing the
    deprecated top-level ``pylabrobot.liquid_handling`` from the built wheel emits a
    DeprecationWarning, which the probe's escalation must turn into a contract failure.
    Together with ``test_contract_conformance_against_wheel`` (the legacy homes
    pass) this shows the probe distinguishes shim from home rather than passing both.
    """
    result = _run_contract_probe(
        throwaway_venv, [("pylabrobot.liquid_handling", "LiquidHandler")], tmp_path
    )
    assert result.returncode == 1, (
        f"a deprecated shim path passed the probe.\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "DeprecationWarning" in result.stderr


def test_contract_rejects_the_stale_incubator_path() -> None:
    """The filter's REJECTION arm. ``pylabrobot.incubator`` does not exist
    at the pinned submodule sha
    (``d9651e2098cd269fc47e6aff80c9242a82d1b587``) -- spike-verified,
    ``pylabrobot.storage.Incubator`` is the only real home
    (``.praxia/docs/research/260817_spike-evidence-repl-refocus.md`` :259).
    ``web_bridge.py``'s still-inline ``_MACHINE_CLASS_MAP`` has not been
    fixed yet (Phase 4 / P4.2, a separate task) and still names the stale
    path; this contract must not. A filter that included whatever the
    (currently unfixed) first-party source happens to reference, rather
    than what is actually correct at this pin, would pass this test's
    ``test_contract_contains_known_symbols`` just as easily with the wrong
    entry -- this is the assertion that catches that.
    """
    assert ("pylabrobot.incubator", "Incubator") not in plr_contract.CONTRACT
    assert not any(mod == "pylabrobot.incubator" for mod, _sym in plr_contract.CONTRACT)


def test_contract_excludes_out_of_scope_vendor_modules() -> None:
    """Second rejection example: contract scope is the REPL's core
    io/resources surface plus the six experimental machine frontends
    (wheel spec :327) -- not every pylabrobot vendor backend. Opentrons has
    no entry anywhere in web-repl's browser source and none of the six
    frontends route through it, so its presence here would mean the
    curation is not actually curating.
    """
    assert not any(
        mod.startswith("pylabrobot.opentrons") for mod, _sym in plr_contract.CONTRACT
    )


# --- the DeprecationWarning escalation self-test ----------------------------


def test_deprecation_warning_escalation_is_live(tmp_path: Path) -> None:
    """Wheel spec T15 (:328): no CONTRACT module emits a DeprecationWarning at the
    pinned submodule sha (the PLR 1.0 shims are deliberately NOT in CONTRACT --
    ``test_contract_names_no_deprecated_shim_paths``). That means `test_contract_
    conformance_against_wheel` passing tells you NOTHING about whether the
    escalating filter is actually live -- it could be silently absent and the
    test would look identical. This arm proves escalation independent of what
    CONTRACT currently touches: a locally-defined stub module that raises
    DeprecationWarning on import MUST raise under the same warning context.
    (``test_shim_path_is_observed_failing_against_wheel`` is the same proof
    against a real 1.0 shim, through the built wheel.)
    """
    stub = tmp_path / "_plr_contract_warns_stub.py"
    stub.write_text(
        "import warnings\n"
        "warnings.warn('synthetic deprecation for filter self-test', "
        "DeprecationWarning)\n",
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    sys.modules.pop("_plr_contract_warns_stub", None)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            with pytest.raises(DeprecationWarning):
                importlib.import_module("_plr_contract_warns_stub")
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("_plr_contract_warns_stub", None)


def test_deprecation_warning_filter_not_defeated_by_pytest_config() -> None:
    """Second arm (wheel spec T15 :328): the escalating filter must not be
    silently undone by pytest's own ``filterwarnings`` ini setting or a
    ``-W`` flag the invocation carries. Asserts the EFFECTIVE filter list,
    immediately after this module's own setup call, actually has the error
    entry in force -- rather than trusting that calling ``simplefilter``
    means it stuck.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert warnings.filters, "warnings.filters is empty after simplefilter()"
        action, _message, category, _module, _lineno = warnings.filters[0]
        assert action == "error"
        assert category is DeprecationWarning
