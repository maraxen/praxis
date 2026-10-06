"""Tests for the shim <-> pylabrobot IO contract gate
(``web-repl/scripts/shim_contract_probe.py`` + ``check_shim_contract.py``).

Why this exists: the browser shims replace ``pylabrobot.io.{Serial,USB,HID,
FTDI}`` wholesale, and nothing tied their signatures to pylabrobot's. The
1.0.0b1 pin added ``human_readable_device_name`` (and more) to every IO
constructor, so connecting a Hamilton STAR from the browser died with::

    TypeError: WebUSB.__init__() got an unexpected keyword argument
               'human_readable_device_name'

Three layers, cheapest first:

1. Rule tests on synthetic classes (pure CPython, no wheel): each rule the
   probe enforces is shown both passing a compliant shim and FAILING a
   deliberately broken one -- the probe is not trusted on the green case alone.
2. Wheel-backed: the probe passes the shipped shims against the BUILT wheel,
   and a copy of the shims with the historical WebUSB signature restored fails
   it naming ``hamilton/base.py`` (negative control).
3. End to end in the wheel venv: the real ``stages.apply()`` patches the real
   shims in, and pylabrobot's own ``STARBackend()`` constructs on top of them.

The wheel-backed arms need ``web-repl/scripts/build_wheels.py`` to have run
(CI's "Build the wheels" step does).
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_TESTS_DIR = Path(__file__).resolve().parent
_WEB_REPL_ROOT = _TESTS_DIR.parent
_REPO_ROOT = _WEB_REPL_ROOT.parent
_SCRIPTS_DIR = _WEB_REPL_ROOT / "scripts"
_SHIMS_DIR = _WEB_REPL_ROOT / "overlay" / "assets" / "shims"
_BOOTSTRAP_DIR = _WEB_REPL_ROOT / "bootstrap"
_FIXTURES_DIR = _TESTS_DIR / "fixtures"

for _p in (_SCRIPTS_DIR, _BOOTSTRAP_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import build_wheels  # noqa: E402
import check_shim_contract  # noqa: E402
import check_wheel_contract  # noqa: E402
import shim_contract_probe as probe  # noqa: E402
import stages  # noqa: E402

# --- 1. rule tests on synthetic classes ---------------------------------------


class _PLRLike:
    def __init__(self, id_vendor: int, id_product: int, human_readable_device_name: str, timeout: int = 30):
        pass

    async def read(self, timeout=None, size=None):
        pass

    def sync_thing(self):
        pass

    @property
    def port(self) -> str:
        return ""

    def serialize(self):
        return {}


def _shim_from(src: str) -> type:
    ns: dict = {}
    exec(textwrap.dedent(src), ns)  # noqa: S102 -- synthetic test classes
    return ns["Shim"]


_GOOD_SHIM = """
class Shim:
    def __init__(self, id_vendor, id_product, human_readable_device_name="x", timeout=30):
        pass
    async def read(self, timeout=None, size=None, endpoint=None):
        pass
    def sync_thing(self):
        pass
    @property
    def port(self):
        return ""
    def serialize(self):
        return {}
"""


def _details(violations) -> str:
    return "\n".join(str(v) for v in violations)


def test_rule_compliant_shim_passes():
    assert probe.check_members(_PLRLike, _shim_from(_GOOD_SHIM), waivers={}) == []


def test_rule_missing_keyword_is_caught():
    """The exact historical failure: the shim's __init__ predates a new kwarg."""
    bad = _shim_from(_GOOD_SHIM.replace('human_readable_device_name="x", ', ""))
    out = _details(probe.check_members(_PLRLike, bad, waivers={}))
    assert "does not accept keyword 'human_readable_device_name'" in out


def test_rule_positional_misorder_is_caught():
    bad = _shim_from(
        _GOOD_SHIM.replace(
            "id_vendor, id_product, human_readable_device_name", "human_readable_device_name, id_vendor, id_product"
        )
    )
    assert "a positional call would misbind" in _details(probe.check_members(_PLRLike, bad, waivers={}))


def test_rule_extra_required_parameter_is_caught():
    bad = _shim_from(_GOOD_SHIM.replace("timeout=30):", "timeout=30, *, device):"))
    assert "requires 'device'" in _details(probe.check_members(_PLRLike, bad, waivers={}))


def test_rule_divergent_default_is_caught():
    bad = _shim_from(_GOOD_SHIM.replace("timeout=30):", "timeout=5):"))
    assert "default for 'timeout' is 5" in _details(probe.check_members(_PLRLike, bad, waivers={}))


def test_rule_shim_may_be_more_lenient_than_pylabrobot():
    """Optional where pylabrobot requires is fine: every pylabrobot call still binds."""
    lenient = _shim_from(_GOOD_SHIM.replace("id_product,", "id_product=0,"))
    assert probe.check_members(_PLRLike, lenient, waivers={}) == []


def test_rule_kind_mismatch_is_caught():
    bad = _shim_from(_GOOD_SHIM.replace("async def read", "def read"))
    assert "is a function, pylabrobot's is a coroutine function" in _details(
        probe.check_members(_PLRLike, bad, waivers={})
    )
    bad = _shim_from(_GOOD_SHIM.replace("@property\n    def port", "def port"))
    assert "pylabrobot's is a property" in _details(probe.check_members(_PLRLike, bad, waivers={}))


def test_rule_missing_member_is_caught_and_waivable():
    bad = _shim_from(_GOOD_SHIM.replace("    def sync_thing(self):\n        pass\n", ""))
    assert "Shim.sync_thing: missing" in _details(probe.check_members(_PLRLike, bad, waivers={}))
    assert probe.check_members(_PLRLike, bad, waivers={("_PLRLike", "sync_thing"): "why"}) == []


def test_rule_contextmanager_kind_is_distinguished():
    import contextlib

    class P:
        @contextlib.contextmanager
        def temporary_timeout(self, timeout):
            yield

    class S:
        def temporary_timeout(self, timeout):
            return None

    assert "pylabrobot's is a contextmanager" in _details(probe.check_members(P, S, waivers={}))


def test_rule_stdlib_io_base_members_are_not_contract():
    """Pylabrobot 1.0.0b1's serial.py/ftdi.py subclass the STDLIB io.IOBase by
    accident; close()/fileno()/... must not become shim requirements.
    """
    import io

    class P(io.IOBase):
        def write(self, data):
            pass

    class S:
        def write(self, data):
            pass

    assert probe.public_members(P) == ["__init__", "write"]
    assert probe.check_members(P, S, waivers={}) == []


# --- package scan, on a synthetic installed-package tree --------------------


def _write_pkg(root: Path, files: dict[str, str]) -> Path:
    pkg = root / "pylabrobot"
    for rel, src in files.items():
        path = pkg / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(src), encoding="utf-8")
    for d in [pkg, *[p for p in pkg.rglob("*") if p.is_dir()]]:
        (d / "__init__.py").touch()
    return pkg


class _USB:
    def __init__(self, id_vendor, id_product, human_readable_device_name, serial_number=None):
        pass

    async def read(self, timeout=None, size=None):
        pass

    async def drain(self):
        pass

    def secret(self):
        pass


class _OldWebUSB:
    def __init__(self, id_vendor, id_product, serial_number=None):
        self.extra = 1

    async def read(self, timeout=None):
        pass


class _NewWebUSB:
    def __init__(self, id_vendor, id_product, human_readable_device_name="x", serial_number=None):
        self.extra = 1

    async def read(self, timeout=None, size=None):
        pass

    async def drain(self):
        pass


_BACKEND = """
from pylabrobot.io.usb import USB

class Backend:
    def __init__(self):
        self.io = USB(human_readable_device_name="Hamilton", id_vendor=1, id_product=2)

    async def go(self):
        await self.io.read(timeout=1, size=64)
        await self.io.drain()
        return self.io.extra
"""


def _scan(tmp_path: Path, shim: type, files: dict[str, str], waivers=None) -> probe.Report:
    pkg = _write_pkg(tmp_path, files)
    report = probe.Report()
    probe.scan_package(
        pkg, [("pylabrobot.io.usb", "USB", _USB, shim)], report, waivers=waivers if waivers is not None else {}
    )
    return report


def test_scan_compliant_shim_passes(tmp_path):
    report = _scan(tmp_path, _NewWebUSB, {"backends/hamilton/base.py": _BACKEND})
    assert report.violations == []
    assert report.call_sites == {"USB": 1}
    assert report.usages["USB"] == 3  # read, drain, extra


def test_scan_reproduces_the_hamilton_failure(tmp_path):
    report = _scan(tmp_path, _OldWebUSB, {"backends/hamilton/base.py": _BACKEND})
    out = _details(report.violations)
    assert "[call-site]" in out and "pylabrobot/backends/hamilton/base.py:6" in out
    assert "unexpected keyword argument 'human_readable_device_name'" in out
    assert "got an unexpected keyword argument 'size'" in out  # self.io.read(size=...)
    assert "shim has no 'drain'" in out


def test_scan_waived_member_that_is_used_still_fails(tmp_path):
    src = _BACKEND.replace("await self.io.drain()", "self.io.secret()")
    report = _scan(tmp_path, _NewWebUSB, {"b.py": src}, waivers={("USB", "secret"): "reason"})
    assert "shim has no 'secret' (waived as unused, but it IS used)" in _details(report.violations)


def test_scan_import_that_bypasses_the_patch_is_caught(tmp_path):
    src = _BACKEND.replace("from pylabrobot.io.usb import USB", "from pylabrobot.io import USB")
    report = _scan(tmp_path, _NewWebUSB, {"b.py": src})
    assert "[import]" in _details(report.violations)


def test_scan_call_off_pylabrobots_own_contract_is_a_scanner_finding(tmp_path):
    """A call that does not even bind against pylabrobot's class means the scanner
    resolved the wrong thing; it is reported as such, never blamed on the shim.
    """
    src = _BACKEND.replace(
        'USB(human_readable_device_name="Hamilton", id_vendor=1, id_product=2)', 'USB(1, 2, "Hamilton", "SN", 9)'
    )
    report = _scan(tmp_path, _NewWebUSB, {"b.py": src})
    assert [v.check for v in report.violations] == ["scanner"]


class _SwappedWebUSB(_NewWebUSB):
    def __init__(self, id_product, id_vendor, human_readable_device_name="x", serial_number=None):
        pass


def test_scan_positional_call_binds_by_position(tmp_path):
    src = _BACKEND.replace(
        'USB(human_readable_device_name="Hamilton", id_vendor=1, id_product=2)', 'USB(1, 2, "Hamilton")'
    )
    assert _scan(tmp_path / "ok", _NewWebUSB, {"b.py": src}).violations == []
    # Same arity, different order: binds without error, so only the member check
    # (same index, same name) can catch it -- and must.
    assert "a positional call would misbind" in _details(probe.check_members(_USB, _SwappedWebUSB, waivers={}))


def test_scan_skips_test_files(tmp_path):
    report = _scan(tmp_path, _OldWebUSB, {"backends/STAR_tests.py": _BACKEND, "tests/x.py": _BACKEND})
    assert report.violations == [] and report.call_sites == {"USB": 0}


def test_probe_targets_cover_every_patched_class():
    """A fifth class added to stages.IO_TARGETS must come with a contract entry."""
    assert {(m, a, b) for m, a, b in stages.IO_TARGETS} == {
        (m, a, shim_cls) for m, a, _shim_mod, shim_cls in probe.TARGETS
    }


def test_probe_shim_modules_are_the_ones_the_bootstrap_imports():
    source = (_BOOTSTRAP_DIR / "praxis_bootstrap.py").read_text(encoding="utf-8")
    for _mod, _attr, shim_mod, shim_cls in probe.TARGETS:
        assert f'import_shim_class("{shim_mod}", "{shim_cls}")' in source


def test_probe_is_stdlib_only():
    """It runs inside the --no-deps throwaway venv, where nothing else exists."""
    tree = ast.parse((_SCRIPTS_DIR / "shim_contract_probe.py").read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    roots -= {"pylabrobot", "__future__"}
    assert roots <= set(sys.stdlib_module_names), roots - set(sys.stdlib_module_names)


# --- 2. wheel-backed ---------------------------------------------------------


@pytest.fixture(scope="session")
def wheel_python(tmp_path_factory) -> Path:
    try:
        return check_wheel_contract.build_throwaway_venv(
            tmp_path_factory.mktemp("shim_contract_venv") / "venv",
            web_repl_root=_WEB_REPL_ROOT,
            repo_root=_REPO_ROOT,
        )
    except check_wheel_contract.ContractError as exc:
        pytest.fail(f"cannot build the wheel venv (run web-repl/scripts/build_wheels.py): {exc}")


def test_shipped_shims_satisfy_the_contract_against_the_wheel(wheel_python, tmp_path):
    result = check_shim_contract.run_probe(wheel_python, _SHIMS_DIR, tmp_path / "report.json")
    assert result.returncode == 0, result.stderr
    assert "SHIM-CONTRACT-OK" in result.stdout
    plr_file = next(line for line in result.stdout.splitlines() if line.startswith("PYLABROBOT_FILE="))
    assert "site-packages" in plr_file and "external" not in Path(plr_file.split("=", 1)[1]).parts
    # Non-vacuous: the scanner really found the Hamilton constructor.
    assert '"USB": 0' not in result.stdout


def _broken_shims(tmp_path: Path) -> Path:
    """A copy of the shims with WebUSB's pre-fix constructor signature restored."""
    dest = tmp_path / "shims"
    shutil.copytree(_SHIMS_DIR, dest, ignore=shutil.ignore_patterns("__pycache__"))
    usb = dest / "web_usb_shim.py"
    src = usb.read_text(encoding="utf-8")
    patched, n = re.subn(r'\n    human_readable_device_name: str = "WebUSB device",', "", src)
    assert n == 1, "negative control could not find the line to remove -- update this test"
    usb.write_text(patched, encoding="utf-8")
    return dest


def test_negative_control_old_webusb_signature_fails_naming_hamilton(wheel_python, tmp_path):
    result = check_shim_contract.run_probe(wheel_python, _broken_shims(tmp_path))
    assert result.returncode == 1, result.stdout
    assert "SHIM-CONTRACT-OK" not in result.stdout
    assert re.search(
        r"\[call-site\] USB -> WebUSB @ pylabrobot/legacy/liquid_handling/backends/hamilton/base\.py:\d+: "
        r"got an unexpected keyword argument 'human_readable_device_name'",
        result.stderr,
    ), result.stderr


def test_cli_negative_control_exits_nonzero(tmp_path):
    """The CI entry point itself, not just run_probe(), fails on drift."""
    assert (
        check_shim_contract.main(["--shims-dir", str(_broken_shims(tmp_path))]) == 1
    )


# --- 3. end to end: real stages.apply() + a real pylabrobot backend ---------

_E2E = r"""
import builtins, sys
sys.path[:0] = [{shims!r}, {fixtures!r}, {bootstrap!r}]
import fake_pyodide
fake_pyodide.install()
import stages
for _mod, _attr, shim_mod, shim_cls in {targets!r}:
    setattr(builtins, shim_cls, stages.import_shim_class(shim_mod, shim_cls))
stages.apply()
stages.verify_identity()

from pylabrobot.legacy.liquid_handling.backends.hamilton.STAR_backend import STARBackend
backend = STARBackend()
assert type(backend.io) is builtins.WebUSB, type(backend.io)
assert backend.io.human_readable_device_name == "Hamilton Liquid Handler"
print("E2E-OK", type(backend.io).__name__)
"""


def test_e2e_star_backend_constructs_on_patched_shims(wheel_python):
    script = build_wheels._NATIVE_STUBS_PRELUDE + _E2E.format(
        shims=str(_SHIMS_DIR),
        fixtures=str(_FIXTURES_DIR),
        bootstrap=str(_BOOTSTRAP_DIR),
        targets=list(probe.TARGETS),
    )
    result = subprocess.run([str(wheel_python), "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "E2E-OK WebUSB" in result.stdout
