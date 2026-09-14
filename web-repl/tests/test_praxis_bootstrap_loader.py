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

Per ADR Sec 2.4, ``web-repl/overlay/assets/python`` is never added to
``sys.path`` here -- every fetched file in these tests is synthetic content
served by ``FakeXHR`` and written under ``tmp_path``, never the real
``overlay/`` tree.
"""

from __future__ import annotations

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
    def log(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass


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

    async def _install(url, deps=False):
        installed.append(url)

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
    fixed here at the only module that causes it."""
    yield
    import builtins

    for name in ("WebSerial", "WebUSB", "WebHID", "WebFTDI"):
        if hasattr(builtins, name):
            delattr(builtins, name)


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

    asyncio.run(loader.praxis_main(HOST_ROOT))

    types_posted = [m["type"] for m in channel.posted]
    assert "praxis:error" not in types_posted, channel.posted
    assert types_posted[-1] == "praxis:ready"
    assert installed_wheels == [HOST_ROOT + "assets/wheels/pylabrobot-0.1.6+gdeadbeef-py3-none-any.whl"]

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
