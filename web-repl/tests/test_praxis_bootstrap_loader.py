"""CPython integration tests for ``web-repl/bootstrap/praxis_bootstrap.py``'s
``praxis_main()`` -- the ordered fail-closed stage ledger (P3.7/P3.8).

There is no real browser here, so ``js`` and ``micropip`` -- the two modules
``praxis_bootstrap.py`` legitimately imports (unlike ``stages.py``/
``transport.py``, which the ADR requires stay ``import js``-free) -- are
replaced with bare Python fakes in ``sys.modules`` before each test imports
or reloads the loader. This is the same fake-the-browser-object technique
``test_transport.py`` uses at the function level, applied at the module
level so the WHOLE ordered ledger can be driven end to end and observed
failing at each required point, per this task's brief:

  - a missing manifest raises PraxisUnavailableError, and ``praxis:ready``
    is NEVER broadcast -- only ``praxis:error`` (``test_ready_not_reached_when_manifest_missing``)
  - a sha256 mismatch on a fetched source raises PraxisDriftError, and
    ``praxis:ready`` is NEVER broadcast (``test_ready_not_reached_on_source_drift``)
  - a D1 shell/manifest sha mismatch fails closed before any source is
    fetched (``test_ready_not_reached_on_shell_sha_mismatch``)
  - the R-ID identity invariant is asserted, and a deliberately
    reintroduced double-``exec`` (class A vs class B) is OBSERVED failing
    it, exactly as ADR Sec 2.2's own negative-test mandate requires
    (``test_r_id_double_exec_is_observed_failing``)
  - the full ledger CAN succeed and reach ``praxis:ready`` -- proving the
    negative tests above are testing a real gate, not a function that
    always raises (``test_ready_reached_on_full_success``)

Notebook display epic, task B8 (spec D13, AC-20): step 13 installs ``praxis.display`` AFTER
``verify_identity`` and BEFORE ``praxis:ready``, as the ONE deliberate exception to fail-closed. An
exception in ``import praxis.display`` or in ``install()`` is caught, logged with ``console.error`` and
posted as ``{"type": "praxis:display-error", "reason": ...}``, and the REPL still reaches
``praxis:ready`` (the ``display`` fixture below stands in for the package; the real ``install()`` is
tested in ``test_display_install.py``):

  - ``test_display_stage_runs_after_verify_identity_and_before_ready`` (order, by source and by run)
  - ``test_display_failure_is_non_fatal_and_loud`` / ``test_missing_display_package_is_non_fatal``
  - ``test_display_stage_is_not_reached_when_an_earlier_stage_fails``

Per ADR Sec 2.4, ``web-repl/overlay/assets/python`` is never added to
``sys.path`` here -- every fetched file in these tests is synthetic content
served by ``FakeXHR`` and written under ``tmp_path``, never the real
``overlay/`` tree.
"""

from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import sys
import types
from pathlib import Path

import pytest

_BOOTSTRAP_DIR = Path(__file__).resolve().parents[1] / "bootstrap"
if str(_BOOTSTRAP_DIR) not in sys.path:
    sys.path.insert(0, str(_BOOTSTRAP_DIR))

HOST_ROOT = "https://example.invalid/repl/"

# Minimal, self-contained fake shim/web_bridge source served over the fake
# XHR -- deliberately NOT the real overlay/assets/python/web_bridge.py
# (which drags in pylabrobot.liquid_handling and a great deal else): this
# suite is testing the LOADER's sequencing and gating, not PyLabRobot or the
# real web_bridge, so the fakes implement just enough surface for
# praxis_main() to exercise every stage.
_SHIM_SOURCES = {
    "web_serial_shim.py": "class WebSerial:\n    pass\n",
    "web_usb_shim.py": "class WebUSB:\n    pass\n",
    "web_hid_shim.py": "class WebHID:\n    pass\n",
    "web_ftdi_shim.py": "class WebFTDI:\n    pass\n",
}
_WEB_BRIDGE_SOURCE = (
    "def bootstrap_playground(namespace=None):\n"
    "    pass\n\n"
    "def register_broadcast_channel(channel):\n"
    "    pass\n\n"
    "def handle_interaction_response(id_, value):\n"
    "    pass\n"
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class FakeXHR:
    def __init__(self, routes: dict[str, tuple[int, str]]):
        self._routes = routes
        self._url = None
        self.status = 0
        self.responseText = ""

    def open(self, method, url, async_):
        self._url = url

    def send(self, body):
        status, text = self._routes.get(self._url, (404, ""))
        self.status = status
        self.responseText = text


class FakeChannel:
    """Stand-in for ``js.BroadcastChannel`` -- records every posted message
    and, if armed with a pong sha, answers a ``praxis:shell-ping`` exactly
    once with a synchronous ``praxis:shell-pong``.
    """

    def __init__(self, pong_sha: str | None):
        self.pong_sha = pong_sha
        self.posted: list[dict] = []
        self.onmessage = None

    def postMessage(self, js_obj) -> None:
        # praxis_bootstrap.py converts dicts via js.Object.fromEntries --
        # our fake js.Object.fromEntries (below) just returns the dict
        # unchanged, so js_obj here IS the original python dict.
        self.posted.append(dict(js_obj))
        if js_obj.get("type") == "praxis:shell-ping" and self.pong_sha is not None:
            handler = self.onmessage
            if handler is not None:
                handler(_FakeEvent({"type": "praxis:shell-pong", "praxis_git_sha": self.pong_sha}))


class _FakeEvent:
    def __init__(self, data: dict):
        self.data = data


class FakeConsole:
    def __init__(self):
        self.errors: list[tuple] = []

    def log(self, *a, **k):
        pass

    def error(self, *a, **k):
        self.errors.append(a)


def _install_fake_js(monkeypatch, pong_sha: str | None) -> FakeChannel:
    channel = FakeChannel(pong_sha)
    fake_js = types.ModuleType("js")
    fake_js.XMLHttpRequest = types.SimpleNamespace(new=lambda: FakeXHR(_ROUTES_HOLDER["routes"]))
    fake_js.BroadcastChannel = types.SimpleNamespace(new=lambda name: channel)
    fake_js.Object = types.SimpleNamespace(fromEntries=lambda pairs: dict(pairs))
    fake_js.console = FakeConsole()
    monkeypatch.setitem(sys.modules, "js", fake_js)
    return channel


def _install_fake_micropip(monkeypatch, installed: list) -> None:
    fake_micropip = types.ModuleType("micropip")

    # Wheel URLs land in *installed* (what the tests assert on). Bare requirement
    # names -- the PLR core deps the bootstrap must request itself because the
    # wheels install deps=False (PLR 1.0: `typing-extensions`) -- are recorded on
    # the fake so they can be asserted separately instead of polluting the wheel list.
    fake_micropip.requested_names = []

    async def _install(url, deps=False):
        if "/" in url:
            installed.append(url)
        else:
            fake_micropip.requested_names.append(url)

    fake_micropip.install = _install
    monkeypatch.setitem(sys.modules, "micropip", fake_micropip)


def _install_fake_pylabrobot(monkeypatch, source_sha: str = "abc123") -> None:
    """Stub just enough of ``pylabrobot`` for ``stages.install_native_stubs``
    / ``stages.apply()`` / ``_check_wheel_drift`` / ``_import_resources`` to
    run against a real, importable (if fake) package tree.
    """
    pkg = types.ModuleType("pylabrobot")
    pkg.__path__ = []  # mark as a package so submodule imports resolve
    io_pkg = types.ModuleType("pylabrobot.io")
    io_pkg.__path__ = []
    io_serial = types.ModuleType("pylabrobot.io.serial")
    io_serial.Serial = None
    io_usb = types.ModuleType("pylabrobot.io.usb")
    io_usb.USB = None
    io_hid = types.ModuleType("pylabrobot.io.hid")
    io_hid.HID = None
    io_ftdi = types.ModuleType("pylabrobot.io.ftdi")
    io_ftdi.FTDI = None
    io_ftdi.HAS_PYLIBFTDI = False
    resources = types.ModuleType("pylabrobot.resources")
    resources.Plate = type("Plate", (), {})
    build_info = types.ModuleType("pylabrobot._praxis_build_info")
    build_info.PLR_SOURCE_SHA = source_sha

    for name, mod in [
        ("pylabrobot", pkg),
        ("pylabrobot.io", io_pkg),
        ("pylabrobot.io.serial", io_serial),
        ("pylabrobot.io.usb", io_usb),
        ("pylabrobot.io.hid", io_hid),
        ("pylabrobot.io.ftdi", io_ftdi),
        ("pylabrobot.resources", resources),
        ("pylabrobot._praxis_build_info", build_info),
    ]:
        monkeypatch.setitem(sys.modules, name, mod)


# The FakeXHR factory closure needs a mutable indirection so each test can
# set its own routes AFTER the fake js module is installed but BEFORE
# praxis_main runs (praxis_main constructs its own xhr_new lazily, calling
# FakeXHR(_ROUTES_HOLDER["routes"]) each time -- so mutating the holder in
# place lets one test's routes differ from another's without reinstalling
# the fake js module).
_ROUTES_HOLDER: dict[str, dict] = {"routes": {}}


def _bootstrap_self_fetch_routes() -> dict[str, tuple[int, str]]:
    """Real stages.py/transport.py content, served at the one hardcoded
    URL this loader is specified to use for its own self-bootstrap (see
    praxis_bootstrap.py's module docstring) -- this exercises the ACTUAL
    self-bootstrap fetch, not a bypass of it.
    """
    routes = {}
    for filename in ("stages.py", "transport.py"):
        text = (_BOOTSTRAP_DIR / filename).read_text()
        routes[HOST_ROOT + f"bootstrap/{filename}"] = (200, text)
    return routes


@pytest.fixture(autouse=True)
def _clean_builtin_shims():
    """stages.apply() staples Web* shim classes DIRECTLY onto builtins, which
    monkeypatch cannot unwind. Without this cleanup the leak reaches
    test_rid_invariant's defensive precondition (builtins must be shim-free)
    whenever both modules run in one process -- a cross-module pollution bug,
    fixed here at the only module that causes it. Also clean up the
    _PRAXIS_BOOT_DONE guard flag."""
    yield
    import builtins

    for name in ("WebSerial", "WebUSB", "WebHID", "WebFTDI", "_PRAXIS_BOOT_DONE"):
        if hasattr(builtins, name):
            delattr(builtins, name)


def _install_success_routes(monkeypatch, installed_wheels: list, web_bridge_source: str | None = None) -> None:
    """Helper to install the standard success-path routes (shims, web_bridge,
    manifest with pylabrobot wheel entry) for tests that exercise a full
    successful bootstrap. Reuses _ROUTES_HOLDER pattern.
    """
    routes = _bootstrap_self_fetch_routes()
    sources = []
    for filename, text in _SHIM_SOURCES.items():
        path = f"assets/shims/{filename}"
        sources.append({"path": path, "sha256": _sha(text)})
        routes[HOST_ROOT + path] = (200, text)
    bridge = _WEB_BRIDGE_SOURCE if web_bridge_source is None else web_bridge_source
    sources.append({"path": "assets/python/web_bridge.py", "sha256": _sha(bridge)})
    routes[HOST_ROOT + "assets/python/web_bridge.py"] = (200, bridge)

    manifest = {
        "praxis_git_sha": "dev",
        "wheels": [
            {
                "package": "pylabrobot",
                "filename": "pylabrobot-0.1.6+gdeadbeef-py3-none-any.whl",
                "version": "0.1.6",
                "source_sha": "deadbeef",
                "sha256": "0" * 64,
                "bytes": 0,
            }
        ],
        "sources": sources,
    }
    routes[HOST_ROOT + "assets/wheels/manifest.json"] = (200, json.dumps(manifest))
    _ROUTES_HOLDER["routes"] = routes


class FakeDisplay:
    """Stands in for ``praxis.display`` (D13's stage does ``import praxis.display; praxis.display.install()``).

    ``calls`` records, at the moment ``install()`` runs, what had already been posted on the channel and
    whether the once-guard flag was set, so a test can prove WHERE in the ledger the stage sits.
    ``behaviour`` is what ``install()`` does: return, or raise.
    """

    def __init__(self):
        self.calls: list[dict] = []
        self.behaviour = lambda: None
        self.channel: FakeChannel | None = None

    def install(self, *args, **kwargs):
        import builtins

        self.calls.append(
            {
                "posted": [m["type"] for m in (self.channel.posted if self.channel else [])],
                "boot_done": getattr(builtins, "_PRAXIS_BOOT_DONE", False),
                "args": args,
                "kwargs": kwargs,
            }
        )
        return self.behaviour()


@pytest.fixture(autouse=True)
def display(monkeypatch):
    """A fake ``praxis`` package with a fake ``praxis.display`` for every test in this file, so the
    display stage has something to import and the existing ledger tests are not polluted by an
    import failure (a real ``praxis`` may be importable from the repo root, and must not be touched)."""
    fake = FakeDisplay()
    pkg = types.ModuleType("praxis")
    pkg.__path__ = []
    mod = types.ModuleType("praxis.display")
    mod.install = fake.install
    pkg.display = mod
    monkeypatch.setitem(sys.modules, "praxis", pkg)
    monkeypatch.setitem(sys.modules, "praxis.display", mod)
    return fake


@pytest.fixture()
def loader(tmp_path, monkeypatch):
    """Import a fresh ``praxis_bootstrap`` module per test, running with cwd
    set to an isolated tmp_path (so its VFS writes -- and the self-bootstrap
    writes of stages.py/transport.py -- land there, never in the real repo
    tree), and with the module cache cleared of ``stages``/``transport`` so
    each test's self-bootstrap fetch genuinely re-imports them fresh.
    """
    monkeypatch.chdir(tmp_path)
    # In the real Pyodide worker, cwd is on sys.path by default, which is
    # what lets a shim fetched-and-written to cwd be importable by bare
    # module name immediately afterward. CPython does not do this
    # automatically on a plain os.chdir, so make the same assumption
    # explicit here rather than silently relying on pytest's own rootdir
    # happening to be importable.
    monkeypatch.syspath_prepend(str(tmp_path))
    for mod_name in ("praxis_bootstrap", "stages", "transport"):
        sys.modules.pop(mod_name, None)
    import importlib

    module = importlib.import_module("praxis_bootstrap")
    # Stamp the loader sha pins the way build_repl.stage_bootstrap() does. The
    # SOURCE tree ships _LOADER_MODULE_SHA256 empty on purpose -- an unstamped
    # bootstrap fails closed rather than executing unverified loader code -- so
    # without this every test here would fail with "no pinned sha256" instead of
    # exercising what it is actually about. Stamping from the same files
    # _bootstrap_self_fetch_routes() serves keeps the REAL fetch and the REAL
    # verification in the loop; a test that monkeypatched the check away would
    # quietly stop covering it.
    module._LOADER_MODULE_SHA256 = {
        name: hashlib.sha256((_BOOTSTRAP_DIR / name).read_bytes()).hexdigest()
        for name in module._LOADER_MODULE_FILES
    }
    yield module
    sys.modules.pop("praxis_bootstrap", None)


def test_ready_not_reached_when_manifest_missing(loader, monkeypatch) -> None:
    """REQUIRED: praxis:ready is NOT reached on a failed stage (manifest
    404). OBSERVED failing: routes have the self-bootstrap files but no
    manifest.json entry at all.
    """
    channel = _install_fake_js(monkeypatch, pong_sha="dev")
    _install_fake_micropip(monkeypatch, installed=[])
    _ROUTES_HOLDER["routes"] = _bootstrap_self_fetch_routes()  # no manifest route

    asyncio.run(loader.praxis_main(HOST_ROOT))

    types_posted = [m["type"] for m in channel.posted]
    assert "praxis:ready" not in types_posted
    assert "praxis:error" in types_posted
    error_msg = next(m for m in channel.posted if m["type"] == "praxis:error")
    assert "manifest" in error_msg["reason"].lower()


def test_ready_not_reached_on_shell_sha_mismatch(loader, monkeypatch) -> None:
    """D1: a real manifest sha against a shell that never answers (or
    answers with a different sha) must fail closed BEFORE any source is
    fetched, and praxis:ready must never post.
    """
    channel = _install_fake_js(monkeypatch, pong_sha="0000000000000000000000000000000000000000")
    _install_fake_micropip(monkeypatch, installed=[])
    routes = _bootstrap_self_fetch_routes()
    manifest = {
        "praxis_git_sha": "1111111111111111111111111111111111111111",
        "wheels": [],
        "sources": [],
    }
    routes[HOST_ROOT + "assets/wheels/manifest.json"] = (200, json.dumps(manifest))
    _ROUTES_HOLDER["routes"] = routes

    asyncio.run(loader.praxis_main(HOST_ROOT))

    types_posted = [m["type"] for m in channel.posted]
    assert "praxis:ready" not in types_posted
    assert "praxis:error" in types_posted


def test_ready_not_reached_on_source_drift(loader, monkeypatch) -> None:
    """REQUIRED: a sha256 mismatch on a fetched source raises
    PraxisDriftError, and praxis:ready is NOT reached. Shell handshake
    succeeds (dev/dev) so the failure under test is isolated to D2 source
    verification.
    """
    channel = _install_fake_js(monkeypatch, pong_sha="dev")
    _install_fake_micropip(monkeypatch, installed=[])
    routes = _bootstrap_self_fetch_routes()
    manifest = {
        "praxis_git_sha": "dev",
        "wheels": [],
        "sources": [
            {
                "path": "assets/shims/web_serial_shim.py",
                "sha256": _sha("class WebSerial:\n    pass\n"),
            }
        ],
    }
    routes[HOST_ROOT + "assets/wheels/manifest.json"] = (200, json.dumps(manifest))
    # Serve WRONG content relative to the manifest's declared sha256.
    routes[HOST_ROOT + "assets/shims/web_serial_shim.py"] = (200, "class WebSerial:\n    tampered = True\n")
    _ROUTES_HOLDER["routes"] = routes

    asyncio.run(loader.praxis_main(HOST_ROOT))

    types_posted = [m["type"] for m in channel.posted]
    assert "praxis:ready" not in types_posted
    assert "praxis:error" in types_posted
    error_msg = next(m for m in channel.posted if m["type"] == "praxis:error")
    assert "sha256" in error_msg["reason"].lower()


def test_ready_reached_on_full_success(loader, monkeypatch) -> None:
    """The full ledger CAN succeed and reach praxis:ready -- proving the
    three negative tests above exercise a real gate, not a function that
    always raises. Every stage (D1, D2 sources, shim R-ID staging, native
    stubs, wheel install, D2 wheel drift, apply()/identity assert, resource
    spray, web_bridge bootstrap, broadcast listener) runs for real against
    fakes, all the way to the final praxis:ready post.
    """
    channel = _install_fake_js(monkeypatch, pong_sha="dev")
    installed_wheels: list[str] = []
    _install_fake_micropip(monkeypatch, installed_wheels)
    _install_fake_pylabrobot(monkeypatch, source_sha="deadbeef")
    _install_success_routes(monkeypatch, installed_wheels)

    asyncio.run(loader.praxis_main(HOST_ROOT))

    types_posted = [m["type"] for m in channel.posted]
    assert "praxis:error" not in types_posted, channel.posted
    assert types_posted[-1] == "praxis:ready"
    assert installed_wheels == [HOST_ROOT + "assets/wheels/pylabrobot-0.1.6+gdeadbeef-py3-none-any.whl"]
    # PLR 1.0 imports typing_extensions unguarded and the wheels install deps=False.
    assert sys.modules["micropip"].requested_names == ["typing-extensions"]

    # R-ID: exactly one class object per shim name, asserted by identity.
    import builtins

    assert sys.modules["pylabrobot.io.serial"].Serial is builtins.WebSerial
    assert sys.modules["pylabrobot.io.usb"].USB is builtins.WebUSB
    assert sys.modules["pylabrobot.io.hid"].HID is builtins.WebHID
    assert sys.modules["pylabrobot.io.ftdi"].FTDI is builtins.WebFTDI


def test_wheel_source_sha_drift_fails_closed(loader, monkeypatch) -> None:
    """D2 for the wheels array: the manifest's declared source_sha for a
    package must match the just-installed wheel's own
    _praxis_build_info.PLR_SOURCE_SHA. OBSERVED failing: the fake
    pylabrobot's build-info reports a DIFFERENT sha than the manifest.
    """
    channel = _install_fake_js(monkeypatch, pong_sha="dev")
    _install_fake_micropip(monkeypatch, installed=[])
    _install_fake_pylabrobot(monkeypatch, source_sha="ACTUALLY-INSTALLED-SHA")

    routes = _bootstrap_self_fetch_routes()
    manifest = {
        "praxis_git_sha": "dev",
        "wheels": [
            {
                "package": "pylabrobot",
                "filename": "pylabrobot-0.1.6+gstale0000-py3-none-any.whl",
                "version": "0.1.6",
                "source_sha": "MANIFEST-EXPECTED-SHA",
                "sha256": "0" * 64,
                "bytes": 0,
            }
        ],
        "sources": [],
    }
    routes[HOST_ROOT + "assets/wheels/manifest.json"] = (200, json.dumps(manifest))
    _ROUTES_HOLDER["routes"] = routes

    asyncio.run(loader.praxis_main(HOST_ROOT))

    types_posted = [m["type"] for m in channel.posted]
    assert "praxis:ready" not in types_posted
    error_msg = next(m for m in channel.posted if m["type"] == "praxis:error")
    assert "MANIFEST-EXPECTED-SHA" in error_msg["reason"]
    assert "ACTUALLY-INSTALLED-SHA" in error_msg["reason"]


def test_r_id_double_exec_is_observed_failing(monkeypatch) -> None:
    """ADR Sec 2.2's own mandated negative test: re-introducing the
    double-``exec`` (class A vs class B) pattern must be OBSERVED failing
    the identity assert, not merely "not present in the new code".

    This directly exercises ``stages.assert_identity`` (imported the normal
    way, no loader/js involved) against two textually-identical but
    distinct class objects -- exactly what ``exec(src, {})`` called twice
    manufactures.
    """
    sys.modules.pop("stages", None)
    import stages

    src = "class WebSerial:\n    pass\n"
    ns_a: dict = {}
    ns_b: dict = {}
    exec(src, ns_a)  # noqa: S102 -- deliberately reproducing the historical bug
    exec(src, ns_b)
    class_a = ns_a["WebSerial"]
    class_b = ns_b["WebSerial"]
    assert class_a is not class_b  # sanity: exec-into-throwaway-namespace really does make two

    fake_module = types.ModuleType("pylabrobot.io.serial")
    fake_module.Serial = class_a  # module already patched with "class A"

    with pytest.raises(stages.PraxisDriftError, match="single-class-object invariant"):
        stages.assert_identity(fake_module, "Serial", class_b, "WebSerial")  # "class B" staged after


def test_positional_call_still_swallows(loader, monkeypatch) -> None:
    """Default raise_on_error=False: positional callers (legacy cells) behave
    exactly as before -- exceptions are caught and posted as praxis:error,
    not re-raised. This is backward-compatible behavior.
    """
    channel = _install_fake_js(monkeypatch, pong_sha="dev")
    _install_fake_micropip(monkeypatch, installed=[])
    routes = _bootstrap_self_fetch_routes()
    # Missing manifest to force an exception in the try block
    _ROUTES_HOLDER["routes"] = routes

    # Call with positional arg only (no raise_on_error kwarg)
    asyncio.run(loader.praxis_main(HOST_ROOT))

    types_posted = [m["type"] for m in channel.posted]
    assert "praxis:error" in types_posted
    # Verify it did NOT re-raise (test would have failed if it did)


def test_raise_on_error_reraises_after_posting_error(loader, monkeypatch) -> None:
    """With raise_on_error=True, the exception is re-raised AFTER posting
    praxis:error. This allows callers who need the exception to catch it.
    """
    channel = _install_fake_js(monkeypatch, pong_sha="dev")
    _install_fake_micropip(monkeypatch, installed=[])
    routes = _bootstrap_self_fetch_routes()
    # Missing manifest to force an exception
    _ROUTES_HOLDER["routes"] = routes

    # Call with raise_on_error=True
    with pytest.raises(Exception, match="manifest"):
        asyncio.run(loader.praxis_main(HOST_ROOT, raise_on_error=True))

    # Verify praxis:error was still posted before the re-raise
    types_posted = [m["type"] for m in channel.posted]
    assert "praxis:error" in types_posted


def test_once_guard_skips_stages_and_reposts_ready(loader, monkeypatch) -> None:
    """Once-guard: a second call after success skips all stages and
    re-posts praxis:ready without re-running any stage logic.
    """
    channel = _install_fake_js(monkeypatch, pong_sha="dev")
    installed_wheels: list[str] = []
    _install_fake_micropip(monkeypatch, installed_wheels)
    _install_fake_pylabrobot(monkeypatch, source_sha="deadbeef")
    _install_success_routes(monkeypatch, installed_wheels)

    # First call: successful bootstrap
    asyncio.run(loader.praxis_main(HOST_ROOT))
    types_posted_1 = [m["type"] for m in channel.posted]
    assert types_posted_1[-1] == "praxis:ready"
    assert installed_wheels == [HOST_ROOT + "assets/wheels/pylabrobot-0.1.6+gdeadbeef-py3-none-any.whl"]

    # Reset for second call
    channel.posted = []
    installed_wheels.clear()

    # Second call: should skip all stages and just re-post ready
    asyncio.run(loader.praxis_main(HOST_ROOT))
    types_posted_2 = [m["type"] for m in channel.posted]
    # Only praxis:ready should be posted
    assert types_posted_2 == ["praxis:ready"]
    # No wheels should be installed on the second call
    assert installed_wheels == []


def test_failed_sequence_does_not_set_guard(loader, monkeypatch) -> None:
    """A failed sequence does NOT set the guard, so a retry re-runs the
    stages. This allows recovery after a failure.
    """
    channel = _install_fake_js(monkeypatch, pong_sha="dev")
    _install_fake_micropip(monkeypatch, installed=[])
    routes = _bootstrap_self_fetch_routes()
    # Missing manifest to force an exception
    _ROUTES_HOLDER["routes"] = routes

    # First call: fails (manifest missing)
    asyncio.run(loader.praxis_main(HOST_ROOT))
    types_posted_1 = [m["type"] for m in channel.posted]
    assert "praxis:error" in types_posted_1

    # Verify guard is NOT set after failure
    import builtins
    assert not getattr(builtins, "_PRAXIS_BOOT_DONE", False)

    # Now set up routes for success
    channel.posted = []
    installed_wheels: list[str] = []
    _install_fake_micropip(monkeypatch, installed_wheels)
    _install_fake_pylabrobot(monkeypatch, source_sha="deadbeef")

    routes = _bootstrap_self_fetch_routes()
    sources = []
    for filename, text in _SHIM_SOURCES.items():
        path = f"assets/shims/{filename}"
        sources.append({"path": path, "sha256": _sha(text)})
        routes[HOST_ROOT + path] = (200, text)
    sources.append({"path": "assets/python/web_bridge.py", "sha256": _sha(_WEB_BRIDGE_SOURCE)})
    routes[HOST_ROOT + "assets/python/web_bridge.py"] = (200, _WEB_BRIDGE_SOURCE)

    manifest = {
        "praxis_git_sha": "dev",
        "wheels": [
            {
                "package": "pylabrobot",
                "filename": "pylabrobot-0.1.6+gdeadbeef-py3-none-any.whl",
                "version": "0.1.6",
                "source_sha": "deadbeef",
                "sha256": "0" * 64,
                "bytes": 0,
            }
        ],
        "sources": sources,
    }
    routes[HOST_ROOT + "assets/wheels/manifest.json"] = (200, json.dumps(manifest))
    _ROUTES_HOLDER["routes"] = routes

    # Second call: should run the stages (NOT skip due to guard) and succeed
    asyncio.run(loader.praxis_main(HOST_ROOT))
    types_posted_2 = [m["type"] for m in channel.posted]
    assert "praxis:error" not in types_posted_2
    assert types_posted_2[-1] == "praxis:ready"
    # Wheels should be installed (confirming stages actually ran)
    assert len(installed_wheels) > 0


def test_guard_flag_is_set_before_ready_is_posted(loader, monkeypatch) -> None:
    """ORDERING TEST: The once-guard flag must be set BEFORE the final
    praxis:ready is posted, not after. This ensures that if a listener
    processes the ready message, the flag is already in place.

    This test wraps the fake channel's postMessage to capture the state
    of builtins._PRAXIS_BOOT_DONE at the exact moment each message is
    posted.
    """
    channel = _install_fake_js(monkeypatch, pong_sha="dev")
    installed_wheels: list[str] = []
    _install_fake_micropip(monkeypatch, installed_wheels)
    _install_fake_pylabrobot(monkeypatch, source_sha="deadbeef")
    _install_success_routes(monkeypatch, installed_wheels)

    import builtins

    # Track the flag state at the moment each message is posted
    flag_states_at_post: dict[str, bool] = {}
    original_postMessage = channel.postMessage

    def wrapped_postMessage(js_obj) -> None:
        msg_type = js_obj.get("type", "unknown")
        # Capture the flag state at this exact moment
        flag_states_at_post[msg_type] = getattr(builtins, "_PRAXIS_BOOT_DONE", False)
        # Call the original postMessage
        return original_postMessage(js_obj)

    channel.postMessage = wrapped_postMessage

    # Run bootstrap successfully
    asyncio.run(loader.praxis_main(HOST_ROOT))

    # Verify praxis:ready was posted
    assert "praxis:ready" in flag_states_at_post, f"praxis:ready not found in {flag_states_at_post}"

    # THE KEY ASSERTION: The flag was True when praxis:ready was posted
    assert (
        flag_states_at_post["praxis:ready"] is True
    ), "Flag must be set BEFORE praxis:ready is posted"


def test_old_saved_notebook_calling_main_twice_is_harmless(tmp_path, monkeypatch) -> None:
    """AC-6: an old saved notebook with a legacy bootstrap cell that calls
    praxis_main twice is harmless. The second call skips via the once-guard.
    This is the key behavior that makes auto-setup safe with old notebooks.

    CRUCIALLY: This test uses TWO FRESH, INDEPENDENT copies of praxis_bootstrap
    (via separate imports after clearing sys.modules), because the spec says
    builtins is used "because every caller exec's a fresh copy of this file".
    """
    import importlib

    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))

    channel = _install_fake_js(monkeypatch, pong_sha="dev")
    installed_wheels: list[str] = []
    _install_fake_micropip(monkeypatch, installed_wheels)
    _install_fake_pylabrobot(monkeypatch, source_sha="deadbeef")
    _install_success_routes(monkeypatch, installed_wheels)

    # First exec: load the first fresh copy of praxis_bootstrap
    for mod_name in ("praxis_bootstrap", "stages", "transport"):
        sys.modules.pop(mod_name, None)
    loader1 = importlib.import_module("praxis_bootstrap")
    loader1._LOADER_MODULE_SHA256 = {
        name: hashlib.sha256((_BOOTSTRAP_DIR / name).read_bytes()).hexdigest()
        for name in loader1._LOADER_MODULE_FILES
    }

    # Run first bootstrap successfully
    asyncio.run(loader1.praxis_main(HOST_ROOT))
    wheel_count_after_first = len(installed_wheels)
    assert wheel_count_after_first > 0

    # Verify the guard flag was set
    import builtins
    assert getattr(builtins, "_PRAXIS_BOOT_DONE", False) is True

    # Reset for second exec
    channel.posted = []
    installed_wheels.clear()

    # Second exec: load a FRESH, INDEPENDENT copy of praxis_bootstrap
    # (simulating the old notebook cell running in a fresh exec() namespace)
    for mod_name in ("praxis_bootstrap", "stages", "transport"):
        sys.modules.pop(mod_name, None)
    loader2 = importlib.import_module("praxis_bootstrap")
    loader2._LOADER_MODULE_SHA256 = {
        name: hashlib.sha256((_BOOTSTRAP_DIR / name).read_bytes()).hexdigest()
        for name in loader2._LOADER_MODULE_FILES
    }

    # Second call: the fresh module sees the builtins guard and skips stages
    asyncio.run(loader2.praxis_main(HOST_ROOT))

    # Verify it skipped via the once-guard
    types_posted_2 = [m["type"] for m in channel.posted]
    assert types_posted_2 == ["praxis:ready"]
    # No wheels installed on second call (all stages skipped)
    assert installed_wheels == []


# ---------------------------------------------------------------------------
# Loader sha pinning (the pre-existing audit CANDIDATE, closed 260820).
# ---------------------------------------------------------------------------
def test_tampered_loader_module_is_refused(loader, monkeypatch) -> None:
    """A modified stages.py must never be executed.

    stages.py and transport.py are fetched by hardcoded URL over a raw
    synchronous XHR and then RUN. They execute before D1 (the shell
    praxis_git_sha handshake) and before D2 (manifest source verification) exist
    to check anything -- transport.py *is* D2's fetch loop, so the manifest
    cannot vouch for its own fetcher. Until this pin landed, `status != 200` was
    the only barrier between the kernel and substituted loader code.
    """
    _install_fake_js(monkeypatch, pong_sha="dev")
    _install_fake_micropip(monkeypatch, installed=[])
    routes = _bootstrap_self_fetch_routes()
    url = HOST_ROOT + "bootstrap/stages.py"
    status, text = routes[url]
    routes[url] = (status, text + "\n# tampered\n")
    _ROUTES_HOLDER["routes"] = routes

    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        loader._bootstrap_loader_modules(HOST_ROOT)


def test_tampered_transport_module_is_refused(loader, monkeypatch) -> None:
    """Same for transport.py -- both files are pinned, not just the first."""
    _install_fake_js(monkeypatch, pong_sha="dev")
    _install_fake_micropip(monkeypatch, installed=[])
    routes = _bootstrap_self_fetch_routes()
    url = HOST_ROOT + "bootstrap/transport.py"
    status, text = routes[url]
    routes[url] = (status, text + "\n# tampered\n")
    _ROUTES_HOLDER["routes"] = routes

    with pytest.raises(RuntimeError, match="transport.py"):
        loader._bootstrap_loader_modules(HOST_ROOT)


def test_unstamped_bootstrap_fails_closed(loader, monkeypatch) -> None:
    """An unstamped copy must refuse to run, not fall back to trusting the fetch.

    Failing OPEN here would be the worst of both worlds: the pin would appear to
    exist while doing nothing on exactly the deployments that skipped stamping.
    """
    _install_fake_js(monkeypatch, pong_sha="dev")
    _install_fake_micropip(monkeypatch, installed=[])
    _ROUTES_HOLDER["routes"] = _bootstrap_self_fetch_routes()
    loader._LOADER_MODULE_SHA256 = {}  # as the SOURCE tree ships it

    with pytest.raises(RuntimeError, match="no pinned sha256"):
        loader._bootstrap_loader_modules(HOST_ROOT)


def test_matching_shas_are_accepted(loader, monkeypatch) -> None:
    """Positive control: the pin does not simply reject everything."""
    _install_fake_js(monkeypatch, pong_sha="dev")
    _install_fake_micropip(monkeypatch, installed=[])
    _ROUTES_HOLDER["routes"] = _bootstrap_self_fetch_routes()

    loader._bootstrap_loader_modules(HOST_ROOT)  # must not raise

    import stages  # noqa: F401 - importable only if the fetch+write succeeded
    import transport  # noqa: F401


def test_source_tree_ships_the_placeholder_empty() -> None:
    """The stamping marker must exist exactly once, and ship EMPTY.

    build_repl.stamp_loader_shas() rewrites this line wholesale; if the marker
    were missing the build fails loudly, and if the source shipped real values
    they would go stale silently the moment either loader changed.
    """
    text = (_BOOTSTRAP_DIR / "praxis_bootstrap.py").read_text()
    marker_lines = [ln for ln in text.splitlines() if "PRAXIS-LOADER-SHA-INJECT" in ln]
    assert len(marker_lines) == 1, f"expected exactly one marker line, got {marker_lines}"
    assert "_LOADER_MODULE_SHA256 = {}" in marker_lines[0], (
        "the source tree must ship the pin dict EMPTY so an unbuilt tree fails "
        f"closed; got {marker_lines[0]!r}"
    )


# --------------------------------------------------------------------------- D13: the display stage (B8, AC-20)

_BOOTSTRAP_PATH = _BOOTSTRAP_DIR / "praxis_bootstrap.py"

# A web_bridge whose bootstrap re-binds builtins.WebSerial to a second class object: exactly what the
# R-ID identity check (step 12, stages.verify_identity) exists to catch.
_REBINDING_WEB_BRIDGE = (
    "import builtins\n\n"
    "def bootstrap_playground(namespace=None):\n"
    "    builtins.WebSerial = type('WebSerial', (), {})\n\n"
    "def register_broadcast_channel(channel):\n"
    "    pass\n\n"
    "def handle_interaction_response(id_, value):\n"
    "    pass\n"
)


def _boot_success(loader, monkeypatch, display, *, web_bridge_source=None):
    """Wire every fake for a full ledger run and return the recording channel."""
    # step 10 does `import web_bridge`: a copy cached by an earlier test would hide this test's source
    monkeypatch.delitem(sys.modules, "web_bridge", raising=False)
    channel = _install_fake_js(monkeypatch, pong_sha="dev")
    display.channel = channel
    installed_wheels: list[str] = []
    _install_fake_micropip(monkeypatch, installed_wheels)
    _install_fake_pylabrobot(monkeypatch, source_sha="deadbeef")
    _install_success_routes(monkeypatch, installed_wheels, web_bridge_source)
    return channel


def _main_source_lines() -> dict[str, list[int]]:
    """Source line numbers, in ``praxis_main``, of the calls the D13 order is stated over."""
    tree = ast.parse(_BOOTSTRAP_PATH.read_text())
    (main,) = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "praxis_main"]
    found: dict[str, list[int]] = {"verify_identity": [], "import_display": [], "install": [], "ready": [],
                                   "display_error": []}
    for node in ast.walk(main):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "verify_identity":
                found["verify_identity"].append(node.lineno)
            if node.func.attr == "install" and ast.unparse(node.func.value) == "praxis.display":
                found["install"].append(node.lineno)
        if isinstance(node, ast.Import) and any(a.name == "praxis.display" for a in node.names):
            found["import_display"].append(node.lineno)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_post":
            for arg in node.args:
                if isinstance(arg, ast.Dict):
                    values = [ast.literal_eval(v) for v in arg.values if isinstance(v, ast.Constant)]
                    if "praxis:ready" in values:
                        found["ready"].append(node.lineno)
                    if "praxis:display-error" in values:
                        found["display_error"].append(node.lineno)
    return found


def test_display_stage_source_order_is_after_verify_identity_and_before_ready() -> None:
    """D13: the stage runs after step 12 (``stages.verify_identity()``) and before the final
    ``praxis:ready`` post (the once-guard branch's earlier ready post is a different code path)."""
    lines = _main_source_lines()
    assert len(lines["verify_identity"]) == 1, lines
    assert len(lines["import_display"]) == 1 and len(lines["install"]) == 1, lines
    final_ready = max(lines["ready"])
    assert len(lines["ready"]) == 2, "the once-guard re-post and the final post"
    assert lines["verify_identity"][0] < lines["import_display"][0] < lines["install"][0] < final_ready
    assert len(lines["display_error"]) == 1


def test_display_stage_is_a_narrow_exception_guard_that_never_reraises() -> None:
    """The one deliberate exception to fail-closed: ``except Exception`` around the display stage ONLY,
    posting ``praxis:display-error`` and not re-raising (the outer ``praxis:error`` guard is untouched)."""
    tree = ast.parse(_BOOTSTRAP_PATH.read_text())
    (main,) = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "praxis_main"]
    guards = [
        n for n in ast.walk(main)
        if isinstance(n, ast.Try)
        and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "install"
                and ast.unparse(c.func.value) == "praxis.display" for b in n.body for c in ast.walk(b))
    ]
    inner = [g for g in guards if len(g.body) <= 3]  # the narrow one, not the outer stage ledger
    assert len(inner) == 1
    (guard,) = inner
    (handler,) = guard.handlers
    assert ast.unparse(handler.type) == "Exception"
    assert not any(isinstance(n, ast.Raise) for h in guard.handlers for n in ast.walk(h))
    assert any(
        isinstance(n, ast.Constant) and n.value == "praxis:display-error" for n in ast.walk(handler)
    )
    # the other stages still sit under the fail-closed guard: exactly one bare-Exception handler posts praxis:error
    error_posts = [
        n for n in ast.walk(main)
        if isinstance(n, ast.Constant) and n.value == "praxis:error"
    ]
    assert len(error_posts) == 1


def test_display_stage_runs_after_verify_identity_and_before_ready(loader, monkeypatch, display) -> None:
    channel = _boot_success(loader, monkeypatch, display)

    asyncio.run(loader.praxis_main(HOST_ROOT))

    types_posted = [m["type"] for m in channel.posted]
    assert len(display.calls) == 1, "install() runs exactly once"
    (call,) = display.calls
    assert call["args"] == () and call["kwargs"] == {}, "the stage calls praxis.display.install() bare"
    assert "praxis:ready" not in call["posted"], "install() ran BEFORE praxis:ready was posted"
    assert "praxis:error" not in call["posted"]
    assert "praxis:error" not in types_posted and "praxis:display-error" not in types_posted
    assert types_posted[-1] == "praxis:ready"
    # Everything before the stage had already run: the D1 handshake was answered and the shell was pinged.
    assert "praxis:shell-ping" in call["posted"]


def test_display_stage_runs_only_after_the_identity_check_passes(loader, monkeypatch, display) -> None:
    """The order, by run: with step 12 (verify_identity) failing, the display stage is never reached, the
    ledger fails closed with ``praxis:error`` and neither ``praxis:display-error`` nor ``praxis:ready``
    is posted. (Positive control: the same wiring without the rebinding bridge reaches the stage.)"""
    channel = _boot_success(loader, monkeypatch, display, web_bridge_source=_REBINDING_WEB_BRIDGE)

    asyncio.run(loader.praxis_main(HOST_ROOT))

    types_posted = [m["type"] for m in channel.posted]
    assert "praxis:error" in types_posted
    assert display.calls == []
    assert "praxis:ready" not in types_posted and "praxis:display-error" not in types_posted
    error = [m for m in channel.posted if m["type"] == "praxis:error"][0]
    assert "single-class-object invariant" in error["reason"]


def test_display_stage_is_not_reached_when_an_earlier_stage_fails(loader, monkeypatch, display) -> None:
    channel = _install_fake_js(monkeypatch, pong_sha="dev")
    display.channel = channel
    _install_fake_micropip(monkeypatch, installed=[])
    _ROUTES_HOLDER["routes"] = _bootstrap_self_fetch_routes()  # no manifest

    asyncio.run(loader.praxis_main(HOST_ROOT))

    assert display.calls == []
    assert "praxis:error" in [m["type"] for m in channel.posted]


def test_display_failure_is_non_fatal_and_loud(loader, monkeypatch, display) -> None:
    """AC-20: with an ``install()`` that raises, ``praxis:ready`` is still posted, and exactly one
    ``praxis:display-error`` message precedes it. It is loud: a console error names it too."""
    channel = _boot_success(loader, monkeypatch, display)

    def boom():
        raise RuntimeError("boom: cannot draw")

    display.behaviour = boom

    asyncio.run(loader.praxis_main(HOST_ROOT))

    types_posted = [m["type"] for m in channel.posted]
    assert "praxis:error" not in types_posted, channel.posted
    assert types_posted.count("praxis:display-error") == 1
    assert types_posted[-2:] == ["praxis:display-error", "praxis:ready"]
    message = [m for m in channel.posted if m["type"] == "praxis:display-error"][0]
    assert message == {"type": "praxis:display-error", "reason": "boom: cannot draw"}
    console_errors = sys.modules["js"].console.errors
    assert any("boom: cannot draw" in " ".join(str(x) for x in args) for args in console_errors), console_errors

    import builtins

    assert builtins._PRAXIS_BOOT_DONE is True, "a failed display does not fail the boot: the once-guard is set"


def test_display_failure_does_not_raise_even_with_raise_on_error(loader, monkeypatch, display) -> None:
    channel = _boot_success(loader, monkeypatch, display)
    display.behaviour = lambda: (_ for _ in ()).throw(ValueError("nope"))

    asyncio.run(loader.praxis_main(HOST_ROOT, raise_on_error=True))  # must not raise

    assert [m["type"] for m in channel.posted][-2:] == ["praxis:display-error", "praxis:ready"]


def test_display_failure_with_an_empty_message_still_gives_a_reason(loader, monkeypatch, display) -> None:
    channel = _boot_success(loader, monkeypatch, display)
    display.behaviour = lambda: (_ for _ in ()).throw(KeyError())  # str(KeyError()) == ""

    asyncio.run(loader.praxis_main(HOST_ROOT))

    message = [m for m in channel.posted if m["type"] == "praxis:display-error"][0]
    assert message["reason"] and "KeyError" in message["reason"]


def test_missing_display_package_is_non_fatal(loader, monkeypatch, display) -> None:
    """An unstaged ``praxis/display/`` (import error) takes the same non-fatal, loud path."""
    channel = _boot_success(loader, monkeypatch, display)
    monkeypatch.setitem(sys.modules, "praxis.display", None)  # `import praxis.display` -> ImportError

    asyncio.run(loader.praxis_main(HOST_ROOT))

    types_posted = [m["type"] for m in channel.posted]
    assert types_posted[-2:] == ["praxis:display-error", "praxis:ready"]
    message = [m for m in channel.posted if m["type"] == "praxis:display-error"][0]
    assert "praxis.display" in message["reason"]
    assert display.calls == []


def test_display_stage_does_not_rerun_on_the_once_guard_path(loader, monkeypatch, display) -> None:
    channel = _boot_success(loader, monkeypatch, display)

    asyncio.run(loader.praxis_main(HOST_ROOT))
    channel.posted.clear()
    asyncio.run(loader.praxis_main(HOST_ROOT))

    assert [m["type"] for m in channel.posted] == ["praxis:ready"]
    assert len(display.calls) == 1


def test_a_display_failure_is_retried_nowhere_and_does_not_block_a_second_boot(loader, monkeypatch, display) -> None:
    """The boot succeeded (only the drawing layer did not), so the once-guard holds: a second call
    re-posts ``praxis:ready`` and does not try the display again."""
    channel = _boot_success(loader, monkeypatch, display)
    display.behaviour = lambda: (_ for _ in ()).throw(RuntimeError("once"))

    asyncio.run(loader.praxis_main(HOST_ROOT))
    channel.posted.clear()
    asyncio.run(loader.praxis_main(HOST_ROOT))

    assert [m["type"] for m in channel.posted] == ["praxis:ready"]
    assert len(display.calls) == 1
