"""Browserless tests for ``praxis/viz/viewer3d.py`` (task C3; spec D11, AC-31, and the C3 parts of AC-29/30/32).

``DockedViewer3D`` subclasses the PLR pin's ``pylabrobot.visualizer3D.server.Viewer3D`` and talks to the
docked deck-panel iframe over the ``praxis_viz3d`` BroadcastChannel instead of a websocket server. There is
no browser here: a ``Bus`` of ``Endpoint`` objects stands in for the channel (one endpoint per
``DockedViewer3D``, like one ``BroadcastChannel`` object per context; a post reaches every OTHER endpoint,
never the sender, and raises once the endpoint is closed), and a ``Page`` plays the iframe's socket shim.
The channel interface is the one ``viewer3d.py`` injects: ``post(str)``, ``add_listener(fn)``,
``remove_listener(fn)``, ``close()``.

Every module is loaded by path under a fresh synthetic name (ADR Sec 2.4: never put
``web-repl/overlay/assets/python`` on ``sys.path``, its ``praxis/`` would shadow the repo's). A fresh load
starts the ``PACKAGE_ROOT`` rebind guard unset, which AC-31's rebind and state-snapshot checks need; an
autouse fixture restores the stock ``PACKAGE_ROOT`` after each test.

Controls. A check that could pass vacuously has a positive control (the same probe sees the effect where it
must) and, where an instrument could be blind, a negative control (a broken stand-in that must fail):
the recording channel raises on a post after close; the ``threading`` / ``websockets`` patches demonstrably
break the STOCK ``Viewer3D.start``; the snapshot comparison reports a patched ``Viewer3D`` attribute; the
override comparison reports a fourth override; the mesh check first shows a ``.glb`` under the root DOES
yield a ``mesh`` without the rebind; the git-cleanliness probe reports a modified file in a scratch repo.

What no test here can show (needs a real Pyodide kernel and page): BroadcastChannel delivery order and
timing, the ``js`` / ``pyodide.ffi`` channel adapter, and the page shim actually parsing these envelopes
(``viz3d_socket.test.js`` covers the shim side; ``test_kinds_match_the_page_shim_and_the_shell`` below
compares the literals).
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import hashlib
import importlib.util
import itertools
import json
import os
import re
import subprocess
import sys
import threading
import types
from pathlib import Path
from typing import Any, Callable

import pytest

import pylabrobot.visualizer3D.server as plr_server
from pylabrobot.resources import Coordinate
from pylabrobot.resources.corning import cor_96_wellplate_360uL_Fb
from pylabrobot.resources.hamilton import (
    hamilton_96_tiprack_1000uL,
    hamilton_plate_carrier_L5_ac,
    hamilton_tip_carrier_L5,
)
from pylabrobot.visualizer3D.facility import Facility

Viewer3D = plr_server.Viewer3D

_WEB_REPL = Path(__file__).resolve().parents[1]
_REPO_ROOT = _WEB_REPL.parent
_VIEWER3D_PY = _WEB_REPL / "overlay" / "assets" / "python" / "praxis" / "viz" / "viewer3d.py"
_SOCKET_JS = _WEB_REPL / "overlay" / "assets" / "visualizer3d-augmentations" / "socket.js"
_DOCK_JS = _WEB_REPL / "shell" / "display" / "dock.js"
_VENDOR_MANIFEST = _WEB_REPL / "overlay" / "assets" / "visualizer3d" / "VENDOR_MANIFEST.json"
_PLR_PIN = "786ac2c4e4f7afe37885af2d98ff5b0afe274c67"

#: Every awaited thing in this file is bounded; the whole scenario gets this much.
SCENARIO_TIMEOUT_S = 30.0

_load_counter = itertools.count()


def load_viewer3d():
    """Load ``viewer3d.py`` fresh under a synthetic name (a fresh ``PACKAGE_ROOT`` guard each time)."""
    name = f"_praxis_viewer3d_c3_{next(_load_counter)}"
    spec = importlib.util.spec_from_file_location(name, _VIEWER3D_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _restore_plr_package_root():
    stock = plr_server.PACKAGE_ROOT
    yield
    plr_server.PACKAGE_ROOT = stock


def run(scenario: Callable[[], Any]) -> Any:
    async def bounded():
        return await asyncio.wait_for(scenario(), SCENARIO_TIMEOUT_S)

    return asyncio.run(bounded())


async def until(predicate: Callable[[], Any], what: str, timeout: float = 3.0) -> None:
    """Turn the loop until ``predicate()`` holds; fail with ``what`` after ``timeout`` seconds."""
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError(f"timed out waiting for: {what}")
        await asyncio.sleep(0.005)


async def turn(n: int = 5) -> None:
    for _ in range(n):
        await asyncio.sleep(0)


def pending_handlers() -> list[asyncio.Task]:
    """Live tasks running the inherited ``Viewer3D._handler`` (found by coroutine name, not by any
    attribute of ``viewer3d.py``)."""
    return [
        t for t in asyncio.all_tasks()
        if not t.done() and getattr(t.get_coro(), "__qualname__", "") == "Viewer3D._handler"
    ]


# --------------------------------------------------------------------------------------------------
# The fake channel and the fake page
# --------------------------------------------------------------------------------------------------
class Endpoint:
    """One BroadcastChannel object. ``post`` reaches the other endpoints, never this one."""

    def __init__(self, bus: "Bus") -> None:
        self.bus = bus
        self.listeners: list[Callable[[Any], None]] = []
        self.closed = False
        self.raw_posts: list[str] = []

    def post(self, message: str) -> None:
        if self.closed:
            raise RuntimeError("InvalidStateError: the BroadcastChannel is closed")
        assert isinstance(message, str), f"every message is a JSON string, got {type(message).__name__}"
        self.raw_posts.append(message)
        decoded = json.loads(message)
        self.bus.log.append(decoded)
        if self.bus.on_post is not None:
            self.bus.on_post(decoded)
        for other in list(self.bus.endpoints):
            if other is not self:
                other.receive(message)

    def add_listener(self, listener: Callable[[Any], None]) -> None:
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[Any], None]) -> None:
        if listener in self.listeners:
            self.listeners.remove(listener)

    def close(self) -> None:
        self.closed = True

    def receive(self, raw: Any) -> None:
        if self.closed:
            return
        for listener in list(self.listeners):
            listener(raw)


class Bus:
    def __init__(self) -> None:
        self.endpoints: list[Endpoint] = []
        self.log: list[dict] = []  # every kernel post, decoded, in order
        self.on_post: Callable[[dict], None] | None = None

    def endpoint(self) -> Endpoint:
        ep = Endpoint(self)
        self.endpoints.append(ep)
        return ep

    def page_post(self, message: Any) -> None:
        """Another context (the page, the shell) posts: reaches every live endpoint. A dict is
        JSON-encoded; anything else (a str, an int, bytes) is delivered as it is."""
        raw = json.dumps(message) if isinstance(message, (dict, list)) else message
        for ep in list(self.endpoints):
            ep.receive(raw)

    def kinds(self, kind: str, **match: Any) -> list[dict]:
        return [m for m in self.log if m.get("kind") == kind and all(m.get(k) == v for k, v in match.items())]


class Page:
    """The iframe's socket shim, for one client id."""

    def __init__(self, bus: Bus, viewer: str, client: str) -> None:
        self.bus, self.viewer, self.client = bus, viewer, client

    def open(self) -> None:
        self.bus.page_post({"kind": "open", "viewer": self.viewer, "client": self.client})

    def bye(self) -> None:
        self.bus.page_post({"kind": "bye", "viewer": self.viewer, "client": self.client})

    def send(self, data: Any) -> None:
        self.bus.page_post({"kind": "msg", "viewer": self.viewer, "client": self.client, "data": data})

    def hello(self, backend: str = "WebGL2") -> None:
        # the shape of static/transport.js sayHello()
        self.send(json.dumps({"event": "hello", "data": {
            "backend": backend, "renderer": "test renderer", "software": False,
            "quality": "high", "userAgent": "test-agent"}}))

    def addressed(self, *kinds: str) -> list[dict]:
        return [m for m in self.bus.log if m.get("client") == self.client
                and m.get("viewer") == self.viewer and (not kinds or m["kind"] in kinds)]

    def events(self) -> list[str]:
        """The websocket events carried to this client, in order (``scene``, ``state``, ...)."""
        return [json.loads(m["data"])["event"] for m in self.addressed("msg")]


def make_deck(name: str = "c3-facility") -> Facility:
    f = Facility(name=name, size_x=1200, size_y=800, size_z=600)
    car = hamilton_tip_carrier_L5(name="c3-tip-carrier")
    car[0] = hamilton_96_tiprack_1000uL(name="c3-tips")
    f.assign_child_resource(car, location=Coordinate(100, 100, 0))
    pc = hamilton_plate_carrier_L5_ac(name="c3-plate-carrier")
    pc[0] = cor_96_wellplate_360uL_Fb(name="c3-plate")
    f.assign_child_resource(pc, location=Coordinate(400, 100, 0))
    return f


class Rig:
    def __init__(self, mod, viewer, deck, bus) -> None:
        self.mod, self.viewer, self.deck, self.bus = mod, viewer, deck, bus

    def page(self, n: int) -> Page:
        return Page(self.bus, self.viewer.viewer_id, f"client-{n}")

    def client_ids(self) -> set[str]:
        return {c.client for c in self.viewer._clients}


@contextlib.asynccontextmanager
async def running(mod=None, *, deck=None, bus=None, **kw):
    """A started ``DockedViewer3D`` on a recording bus; stopped (idempotently) on the way out."""
    mod = mod if mod is not None else load_viewer3d()
    bus = bus if bus is not None else Bus()
    deck = deck if deck is not None else make_deck()
    kw.setdefault("session", "sess-test")
    viewer = mod.DockedViewer3D(deck, channel_factory=bus.endpoint, **kw)
    await viewer.start()
    try:
        yield Rig(mod, viewer, deck, bus)
    finally:
        await asyncio.wait_for(viewer.stop(), 5)


async def open_pages(rig: Rig, n: int, *, start: int = 1) -> list[Page]:
    pages = [rig.page(i) for i in range(start, start + n)]
    for p in pages:
        p.open()
    await until(lambda: {p.client for p in pages} <= rig.client_ids(), f"{n} handlers registered")
    return pages


# --------------------------------------------------------------------------------------------------
# The instrument itself (negative controls for the fakes)
# --------------------------------------------------------------------------------------------------
class TestInstrument:
    def test_post_after_close_raises(self):
        ep = Bus().endpoint()
        ep.post(json.dumps({"kind": "x"}))
        ep.close()
        with pytest.raises(RuntimeError):
            ep.post(json.dumps({"kind": "x"}))

    def test_a_post_reaches_other_endpoints_never_the_sender(self):
        bus = Bus()
        a, b = bus.endpoint(), bus.endpoint()
        got_a, got_b = [], []
        a.add_listener(got_a.append)
        b.add_listener(got_b.append)
        a.post(json.dumps({"kind": "x"}))
        assert got_a == [] and len(got_b) == 1

    def test_a_closed_endpoint_hears_nothing(self):
        bus = Bus()
        a = bus.endpoint()
        heard = []
        a.add_listener(heard.append)
        bus.page_post({"kind": "query"})
        a.close()
        bus.page_post({"kind": "query"})
        assert len(heard) == 1

    def test_the_handler_probe_sees_a_stock_handler_and_only_that(self):
        class Conn:  # the smallest connection the inherited _handler accepts
            def __init__(self):
                self.q = asyncio.Queue()

            async def send(self, message):
                return None

            def __aiter__(self):
                return self

            async def __anext__(self):
                item = await self.q.get()
                if item is None:
                    raise StopAsyncIteration
                return item

        async def scenario():
            viewer = Viewer3D(make_deck(), open_browser=False)
            viewer._loop = asyncio.get_running_loop()
            conn = Conn()
            task = asyncio.ensure_future(viewer._handler(conn))
            other = asyncio.ensure_future(asyncio.sleep(10))
            await turn()
            assert pending_handlers() == [task]  # sees the handler, not the unrelated task
            conn.q.put_nowait(None)
            await asyncio.wait_for(task, 3)
            assert pending_handlers() == []
            other.cancel()

        run(scenario)


# --------------------------------------------------------------------------------------------------
# GATE X (spec D11; AC-31 parts 1 and 2)
# --------------------------------------------------------------------------------------------------
def override_set(cls: type) -> set[str]:
    return {n for n in vars(cls) if callable(getattr(Viewer3D, n, None))}


def snapshot() -> tuple[dict, dict]:
    return dict(vars(Viewer3D)), dict(vars(plr_server))


def snapshot_diff(before: tuple[dict, dict], after: tuple[dict, dict]) -> set[str]:
    """Keys that were added, removed or rebound (by identity), class dict then module dict, excluding
    ``PACKAGE_ROOT``."""
    out: set[str] = set()
    for label, b, a in (("Viewer3D.", before[0], after[0]), ("server.", before[1], after[1])):
        for key in set(b) | set(a):
            if label == "server." and key == "PACKAGE_ROOT":
                continue
            if key not in b or key not in a or a[key] is not b[key]:
                out.add(label + key)
    return out


class TestGateX:
    def test_exactly_three_overrides_over_the_pin(self):
        mod = load_viewer3d()
        assert mod.DockedViewer3D.__mro__[1] is Viewer3D
        assert mod.DockedViewer3D.__module__ == mod.__name__
        assert override_set(mod.DockedViewer3D) == {"__init__", "start", "stop"}

    def test_negative_control_a_fourth_override_is_reported(self):
        mod = load_viewer3d()

        class Fourth(mod.DockedViewer3D):
            def _mark_scene_dirty(self):  # the S4-C case
                return None

        assert override_set(Fourth) == {"_mark_scene_dirty"}
        assert override_set(Fourth) != {"__init__", "start", "stop"}

    def test_the_pin_actually_has_the_three_names_as_callables(self):
        # the comparison is only meaningful if the base defines what the subclass overrides
        assert {"__init__", "start", "stop"} <= {n for n in vars(Viewer3D) if callable(vars(Viewer3D)[n])}

    def test_state_snapshot_identical_after_construct_start_stop_except_package_root(self):
        before = snapshot()
        stock_root = plr_server.PACKAGE_ROOT
        mod = load_viewer3d()

        async def scenario():
            bus = Bus()
            viewer = mod.DockedViewer3D(make_deck(), channel_factory=bus.endpoint, session="s")
            await viewer.start()
            await viewer.stop()

        run(scenario)
        after = snapshot()
        assert set(before[0]) == set(after[0]) and set(before[1]) == set(after[1])
        assert snapshot_diff(before, after) == set()
        assert plr_server.PACKAGE_ROOT != stock_root, "the rebind is the one deliberate deviation"

    def test_negative_control_a_patched_viewer3d_attribute_is_reported(self, monkeypatch):
        before = snapshot()
        monkeypatch.setattr(Viewer3D, "_mark_scene_dirty", lambda self: None)
        assert snapshot_diff(before, snapshot()) == {"Viewer3D._mark_scene_dirty"}

    def test_negative_control_a_rebound_module_global_is_reported(self, monkeypatch):
        before = snapshot()
        monkeypatch.setattr(plr_server, "PROTOCOL", 99)
        assert snapshot_diff(before, snapshot()) == {"server.PROTOCOL"}

    def test_the_viewer3d_module_imports_only_the_contract_listed_visualizer3d_module(self):
        tree = ast.parse(_VIEWER3D_PY.read_text(encoding="utf-8"))
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found |= {a.name for a in node.names if a.name.split(".")[0] == "pylabrobot"}
            elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "pylabrobot":
                found.add(node.module)
        assert found, "viewer3d.py must import the pin's package"
        assert all(n == "pylabrobot.visualizer3D" or n.startswith("pylabrobot.visualizer3D.") for n in found), found
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            import plr_contract
        finally:
            sys.path.remove(str(Path(__file__).resolve().parent))
        assert found <= {path for path, _ in plr_contract.CONTRACT}, found
        assert ("pylabrobot.visualizer3D.server", "Viewer3D") in plr_contract.CONTRACT

    def test_no_plr_python_is_vendored_under_overlay_or_scripts(self):
        needle = b"plr_visualizer3d"
        hits: list[str] = []
        for base in (_WEB_REPL / "overlay", _WEB_REPL / "scripts"):
            for path in base.rglob("*"):
                if path.is_file() and path.stat().st_size < 8_000_000 and needle in path.read_bytes():
                    hits.append(str(path.relative_to(_REPO_ROOT)))
        assert hits == []
        assert not (_WEB_REPL / "overlay" / "assets" / "python" / "plr_visualizer3d").exists()

    def test_viewer3d_py_mentions_the_channel_name(self):
        assert _VIEWER3D_PY.read_text(encoding="utf-8").count("praxis_viz3d") >= 1


def _plr_dir() -> Path:
    return Path(plr_server.__file__).resolve().parent


def _sha_tree(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*.py"))}


def git_dirty(repo_root: Path, subpath: str) -> list[str]:
    """Porcelain lines (modified, untracked) under ``subpath`` of a git checkout; raises if it is not one."""
    out = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", subpath],
        cwd=repo_root, capture_output=True, text=True, timeout=60, check=True,
    ).stdout
    return [line for line in out.splitlines() if "__pycache__" not in line]


class TestVendoredPlrBytesUntouched:
    def test_pre_and_post_hashes_of_the_pins_visualizer3d_sources_are_equal(self):
        before = _sha_tree(_plr_dir())
        assert before, "the pin's pylabrobot/visualizer3D/*.py must be readable"
        mod = load_viewer3d()

        async def scenario():
            async with running(mod) as rig:
                (p,) = await open_pages(rig, 1)
                p.hello()
                await until(lambda: rig.viewer.clients_seen, "hello")

        run(scenario)
        assert _sha_tree(_plr_dir()) == before

    def test_the_pin_checkout_is_clean_and_at_the_recorded_commit(self):
        plr_root = _plr_dir().parent.parent
        try:
            dirty = git_dirty(plr_root, "pylabrobot/visualizer3D")
            head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=plr_root, capture_output=True,
                                  text=True, timeout=60, check=True).stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError) as exc:
            pytest.skip(f"the PLR in this interpreter is not a git checkout ({type(exc).__name__}); "
                        "the hash comparison above still ran")
        assert dirty == [], f"vendored PLR bytes differ from the pin: {dirty}"
        recorded = json.loads(_VENDOR_MANIFEST.read_text(encoding="utf-8"))["source_sha"]
        assert recorded == _PLR_PIN
        assert head == recorded, "the PLR checkout is not at the pin recorded in VENDOR_MANIFEST.json"

    def test_negative_control_the_probe_reports_a_modified_file(self, tmp_path):
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t"}
        d = tmp_path / "repo"
        (d / "pkg").mkdir(parents=True)
        (d / "pkg" / "a.py").write_text("x = 1\n")
        for args in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "c"]):
            subprocess.run(["git", *args], cwd=d, check=True, env=env, capture_output=True, timeout=60)
        assert git_dirty(d, "pkg") == []
        (d / "pkg" / "a.py").write_text("x = 2\n")
        assert git_dirty(d, "pkg") != []


# --------------------------------------------------------------------------------------------------
# PACKAGE_ROOT rebind (D11 "Trigger"; AC-31)
# --------------------------------------------------------------------------------------------------
def first_scene(page: Page) -> dict:
    for m in page.addressed("msg"):
        decoded = json.loads(m["data"])
        if decoded["event"] == "scene":
            return decoded["data"]
    raise AssertionError("no scene message was carried to the page")


def seed_root_with_a_fixture_model(tmp_path: Path) -> tuple[Path, str]:
    """A temporary root holding a ``.glb`` named after a fixture model (standing in for the stock root's
    63 models). The model name is read from the fixture's own scene, not guessed."""
    probe = Viewer3D(make_deck(), open_browser=False)
    models = probe._scene_message()["models"]
    pick = next(m for m in models if m.get("type") == "TipCarrier" and m.get("model"))
    name = str(pick["model"])
    seeded = tmp_path / "seeded-root"
    seeded.mkdir()
    (seeded / f"{name}.glb").write_bytes(b"glTF\x02\x00\x00\x00")
    return seeded, name


class TestPackageRootRebind:
    def test_loading_the_module_changes_no_plr_state(self):
        before = snapshot()
        root = plr_server.PACKAGE_ROOT
        load_viewer3d()
        assert plr_server.PACKAGE_ROOT == root
        assert snapshot_diff(before, snapshot()) == set()

    def test_first_construction_rebinds_to_an_empty_owned_directory_once(self):
        mod = load_viewer3d()
        stock = plr_server.PACKAGE_ROOT
        v1 = mod.DockedViewer3D(make_deck(), channel_factory=Bus().endpoint, session="s")
        first = plr_server.PACKAGE_ROOT
        assert first != stock
        assert os.path.isdir(first) and os.listdir(first) == []
        mod._ensure_package_root()
        assert plr_server.PACKAGE_ROOT == first
        v2 = mod.DockedViewer3D(make_deck(), channel_factory=Bus().endpoint, session="s")
        assert plr_server.PACKAGE_ROOT == first
        assert v1 is not v2

    def test_the_rebound_root_is_not_the_stock_package_tree(self):
        mod = load_viewer3d()
        mod.DockedViewer3D(make_deck(), channel_factory=Bus().endpoint, session="s")
        assert not os.path.realpath(plr_server.PACKAGE_ROOT).startswith(os.path.realpath(str(_plr_dir().parent)))

    def test_a_fresh_load_starts_the_guard_unset_so_it_rebinds_again(self):
        mod_a = load_viewer3d()
        mod_a.DockedViewer3D(make_deck(), channel_factory=Bus().endpoint, session="s")
        root_a = plr_server.PACKAGE_ROOT
        mod_b = load_viewer3d()
        mod_b.DockedViewer3D(make_deck(), channel_factory=Bus().endpoint, session="s")
        assert plr_server.PACKAGE_ROOT != root_a

    def test_the_rebind_is_what_removes_every_mesh(self, tmp_path):
        seeded, name = seed_root_with_a_fixture_model(tmp_path)
        mod = load_viewer3d()
        plr_server.PACKAGE_ROOT = str(seeded)  # after import, before the first construction
        plr_server._models_on_disk.cache_clear()

        # Positive control: over the seeded root, with no rebind, the inherited scene build DOES emit a mesh.
        stock = Viewer3D(make_deck(), open_browser=False)
        models = stock._scene_message()["models"]
        assert any(m.get("model") == name and "mesh" in m for m in models), (
            "the seeded .glb produced no mesh with the stock viewer: this check would be vacuous")

        async def scenario():
            async with running(mod) as rig:
                assert plr_server.PACKAGE_ROOT != str(seeded), "the first construction must rebind"
                (p,) = await open_pages(rig, 1)
                await until(lambda: "scene" in p.events(), "scene")
                assert not any("mesh" in m for m in first_scene(p)["models"])

        run(scenario)

    def test_negative_control_without_the_rebind_the_seeded_mesh_reaches_the_page(self, tmp_path):
        seeded, name = seed_root_with_a_fixture_model(tmp_path)
        mod = load_viewer3d()
        plr_server.PACKAGE_ROOT = str(seeded)
        plr_server._models_on_disk.cache_clear()
        mod._ensure_package_root = lambda: None  # the broken stand-in: rebind disabled

        async def scenario():
            async with running(mod) as rig:
                assert plr_server.PACKAGE_ROOT == str(seeded)
                (p,) = await open_pages(rig, 1)
                await until(lambda: "scene" in p.events(), "scene")
                assert any(m.get("model") == name and "mesh" in m for m in first_scene(p)["models"])

        run(scenario)


# --------------------------------------------------------------------------------------------------
# start(): no servers, no threads, no browser; open -> accept -> scene -> state
# --------------------------------------------------------------------------------------------------
class TestStart:
    def test_start_needs_no_websocket_server_thread_or_browser(self, monkeypatch):
        mod = load_viewer3d()

        def boom(*a, **k):
            raise AssertionError("a forbidden call was made")

        async def scenario():
            bus = Bus()
            with monkeypatch.context() as m:
                m.setattr(plr_server.websockets, "serve", boom)
                m.setattr(threading, "Thread", boom)
                m.setattr(plr_server.webbrowser, "open", boom)
                viewer = mod.DockedViewer3D(make_deck(), channel_factory=bus.endpoint, session="s")
                await viewer.start()  # must not raise
                assert viewer.open_browser is False
            await viewer.stop()

        run(scenario)

    def test_positive_control_the_same_patches_break_the_stock_start(self, monkeypatch):
        def boom(*a, **k):
            raise AssertionError("a forbidden call was made")

        async def scenario():
            stock = Viewer3D(make_deck(), open_browser=False)
            with monkeypatch.context() as m:
                m.setattr(plr_server.websockets, "serve", boom)
                m.setattr(threading, "Thread", boom)
                m.setattr(plr_server.webbrowser, "open", boom)
                with pytest.raises(BaseException):
                    await stock.start()

        run(scenario)

    def test_start_announces_the_viewer_once_with_the_exact_shape(self):
        async def scenario():
            async with running(deck=make_deck(), session="sess-7") as rig:
                announces = rig.bus.kinds("announce")
                assert len(announces) == 1
                assert announces[0] == {"kind": "announce", "viewer": rig.viewer.viewer_id,
                                        "deck": "c3-facility", "session": "sess-7"}

        run(scenario)

    def test_announce_stays_under_the_shells_message_cap_even_for_a_huge_deck_name(self):
        async def scenario():
            async with running(deck=make_deck("x" * 10_000)) as rig:
                announces = rig.bus.kinds("announce")
                assert len(announces) == 1
                assert announces[0]["deck"], "a long name is shortened, not dropped"
                assert len(rig.bus.endpoints[0].raw_posts[0]) <= 4096  # dock.js MAX_MESSAGE
                assert 0 < len(announces[0]["viewer"]) <= 200  # dock.js MAX_ID

        run(scenario)

    def test_session_defaults_to_a_nonempty_string(self):
        async def scenario():
            mod = load_viewer3d()
            bus = Bus()
            viewer = mod.DockedViewer3D(make_deck(), channel_factory=bus.endpoint)
            await viewer.start()
            try:
                (a,) = bus.kinds("announce")
                assert isinstance(a["session"], str) and a["session"]
            finally:
                await viewer.stop()

        run(scenario)

    def test_each_viewer_mints_its_own_id(self):
        mod = load_viewer3d()
        ids = {mod.DockedViewer3D(make_deck(), channel_factory=Bus().endpoint, session="s").viewer_id
               for _ in range(5)}
        assert len(ids) == 5 and all(isinstance(i, str) and i for i in ids)

    def test_an_open_yields_accept_then_scene_then_state_to_that_client_only(self):
        async def scenario():
            async with running() as rig:
                x, y = rig.page(1), rig.page(2)
                x.open()
                await until(lambda: x.events() == ["scene", "state"], "x greeted")
                assert [m["kind"] for m in x.addressed()] == ["accept", "msg", "msg"]
                accept = x.addressed("accept")[0]
                assert accept == {"kind": "accept", "viewer": rig.viewer.viewer_id, "client": "client-1"}
                for m in x.addressed("msg"):
                    assert set(m) == {"kind", "viewer", "client", "data"}
                    assert isinstance(m["data"], str)
                    assert set(json.loads(m["data"])) == {"event", "data"}
                assert y.addressed() == [], "nothing is addressed to a client that never opened"
                # every post the kernel made for x carries x's client and this viewer's id
                assert all(m["client"] == "client-1" and m["viewer"] == rig.viewer.viewer_id
                           for m in rig.bus.log if m["kind"] in ("accept", "msg"))

        run(scenario)

    def test_the_first_scene_carries_no_mesh_key_on_any_model(self):
        async def scenario():
            async with running() as rig:
                (p,) = await open_pages(rig, 1)
                await until(lambda: "scene" in p.events(), "scene")
                models = first_scene(p)["models"]
                assert models, "the fixture scene must have models (else the check is vacuous)"
                assert not any("mesh" in m for m in models)

        run(scenario)

    def test_a_hello_appends_to_clients_seen_and_releases_wait_for_browser(self):
        async def scenario():
            async with running() as rig:
                (p,) = await open_pages(rig, 1)
                with pytest.raises(asyncio.TimeoutError):  # positive control: nobody said hello yet
                    await rig.viewer.wait_for_browser(timeout=0.05)
                p.hello("WebGPU")
                await asyncio.wait_for(rig.viewer.wait_for_browser(timeout=2), 3)
                assert len(rig.viewer.clients_seen) == 1
                assert rig.viewer.clients_seen[0]["backend"] == "WebGPU"

        run(scenario)

    def test_a_hello_from_an_unknown_client_or_another_viewer_is_ignored(self):
        async def scenario():
            async with running() as rig:
                await open_pages(rig, 1)
                Page(rig.bus, rig.viewer.viewer_id, "nobody").hello()
                Page(rig.bus, "some-other-viewer", "client-1").hello()
                await turn(20)
                assert rig.viewer.clients_seen == []
                rig.page(1).hello()  # positive control
                await until(lambda: rig.viewer.clients_seen, "the real hello")

        run(scenario)

    def test_a_set_volume_on_a_well_reaches_every_client_as_a_state_message(self):
        async def scenario():
            async with running() as rig:
                x, y = await open_pages(rig, 2)
                await until(lambda: x.events() == ["scene", "state"] and y.events() == ["scene", "state"],
                            "both greeted")
                well = rig.deck.get_resource("c3-plate").get_item("A1")
                well.set_volume(120)
                await until(lambda: x.events()[2:] == ["state"] and y.events()[2:] == ["state"], "state to both")

        run(scenario)

    def test_assigning_a_resource_yields_scene_or_moves_after_the_debounce(self):
        async def scenario():
            async with running() as rig:
                (p,) = await open_pages(rig, 1)
                await until(lambda: p.events() == ["scene", "state"], "greeted")
                car = hamilton_plate_carrier_L5_ac(name="c3-extra-carrier")
                rig.deck.assign_child_resource(car, location=Coordinate(700, 100, 0))
                await until(lambda: any(e in ("scene", "moves") for e in p.events()[2:]),
                            "scene or moves after SCENE_DEBOUNCE_S", timeout=5)

        run(scenario)


# --------------------------------------------------------------------------------------------------
# query / inbound filtering
# --------------------------------------------------------------------------------------------------
class TestInbound:
    def test_query_yields_one_announce_for_the_current_viewer(self):
        async def scenario():
            async with running(session="sess-q") as rig:
                before = len(rig.bus.kinds("announce"))
                rig.bus.page_post({"kind": "query"})
                got = rig.bus.kinds("announce")[before:]
                assert got == [{"kind": "announce", "viewer": rig.viewer.viewer_id,
                                "deck": "c3-facility", "session": "sess-q"}]

        run(scenario)

    @pytest.mark.parametrize("junk", [
        "not json at all", "", "[]", "[1,2]", '"a string"', "null", "7", "true", "{",
        123, None, b"bytes",
        {"kind": "zzz"}, {"kind": 7}, {"kind": None}, {}, {"no": "kind"},
        # kernel-to-page kinds arriving inward are not ours to act on
        {"kind": "accept", "viewer": "V", "client": "c"}, {"kind": "evict", "viewer": "V", "client": "c"},
        {"kind": "announce", "viewer": "V", "deck": "d", "session": "s"}, {"kind": "close", "viewer": "V"},
        # open / bye / msg that are malformed or aimed at another viewer
        {"kind": "open"}, {"kind": "open", "viewer": "V"}, {"kind": "open", "client": "c"},
        {"kind": "open", "viewer": "V", "client": ""}, {"kind": "open", "viewer": "V", "client": 5},
        {"kind": "open", "viewer": "V", "client": "c" * 201},
        {"kind": "open", "viewer": "another-viewer", "client": "c"},
        {"kind": "bye", "viewer": "V"}, {"kind": "msg", "viewer": "V", "client": "ghost", "data": "x"},
    ])
    def test_junk_is_dropped_without_an_exception_and_without_a_post(self, junk):
        async def scenario():
            async with running() as rig:
                # `V` stands for this viewer's id in the parametrized shapes
                msg = junk
                if isinstance(msg, dict) and msg.get("viewer") == "V":
                    msg = {**msg, "viewer": rig.viewer.viewer_id}
                posts = len(rig.bus.log)
                clients = set(rig.viewer._clients)
                rig.bus.page_post(msg)  # must not raise into the channel
                await turn(10)
                assert len(rig.bus.log) == posts, f"a post was made for {junk!r}: {rig.bus.log[posts:]}"
                assert set(rig.viewer._clients) == clients
                assert pending_handlers() == []
                # the listener survived the junk: a well-formed open right after is still accepted
                (p,) = await open_pages(rig, 1, start=50)
                assert p.addressed("accept")

        run(scenario)

    def test_positive_control_a_well_formed_open_does_produce_posts(self):
        async def scenario():
            async with running() as rig:
                posts = len(rig.bus.log)
                (p,) = await open_pages(rig, 1)
                assert len(rig.bus.log) > posts and p.addressed("accept")

        run(scenario)

    def test_a_msg_with_non_string_data_is_dropped(self):
        async def scenario():
            async with running() as rig:
                (p,) = await open_pages(rig, 1)
                p.send({"event": "hello"})  # an object, not the string the websocket would carry
                p.send(12)
                await turn(20)
                assert rig.viewer.clients_seen == []

        run(scenario)

    def test_a_duplicate_open_for_a_live_client_does_not_start_a_second_handler(self):
        async def scenario():
            async with running() as rig:
                (p,) = await open_pages(rig, 1)
                p.open()
                await turn(20)
                assert len(pending_handlers()) == 1
                assert len(p.addressed("accept")) == 1

        run(scenario)

    def test_kinds_match_the_page_shim_and_the_shell(self):
        mod = load_viewer3d()
        kernel = {"query": mod.KIND_QUERY, "announce": mod.KIND_ANNOUNCE, "open": mod.KIND_OPEN,
                  "accept": mod.KIND_ACCEPT, "msg": mod.KIND_MSG, "bye": mod.KIND_BYE,
                  "evict": mod.KIND_EVICT, "close": mod.KIND_CLOSE}
        assert kernel == {k: k for k in kernel}
        socket_js = _SOCKET_JS.read_text(encoding="utf-8")
        shim = dict(re.findall(r'const KIND_(\w+) = "(\w+)";', socket_js))
        assert {v for v in shim.values()} == {"open", "msg", "bye", "accept", "evict", "close"}
        assert re.search(r'const CHANNEL_NAME = "praxis_viz3d";', socket_js)
        dock_js = _DOCK_JS.read_text(encoding="utf-8")
        assert re.search(r'export const CHANNEL = "praxis_viz3d";', dock_js)
        assert mod.VIZ3D_CHANNEL == "praxis_viz3d"
        assert 'kind: "query"' in dock_js and 'case "announce"' in dock_js and 'case "close"' in dock_js
        # the envelope fields the shim reads back (isMine: viewer + client) are on every accept/evict/msg
        assert "m.viewer === viewer && m.client === clientId" in socket_js


# --------------------------------------------------------------------------------------------------
# The client cap, eviction, bye (AC-31 "Client cap", "bye"; D11 inbound bounds; B-1)
# --------------------------------------------------------------------------------------------------
class TestClientCap:
    def test_a_fifth_open_is_accepted_and_the_oldest_client_is_evicted(self):
        async def scenario():
            async with running() as rig:
                pages = await open_pages(rig, 4)
                await until(lambda: all(p.events() == ["scene", "state"] for p in pages), "four greeted")
                assert len(rig.viewer._clients) == 4 and len(pending_handlers()) == 4
                assert rig.bus.kinds("evict") == []  # positive control: four is under the cap

                fifth = rig.page(5)
                fifth.open()
                # synchronous: the evicted connection left _clients before the new handler has run
                assert "client-1" not in rig.client_ids()
                assert len(rig.viewer._clients) <= 4
                evicts = rig.bus.kinds("evict")
                assert evicts == [{"kind": "evict", "viewer": rig.viewer.viewer_id, "client": "client-1"}]
                assert fifth.addressed("accept"), "the fifth open gets accept"
                order = [m["kind"] for m in rig.bus.log if m["kind"] in ("evict", "accept")][-2:]
                assert order == ["evict", "accept"]

                await until(lambda: len(pending_handlers()) == 4 and rig.client_ids() == {
                    "client-2", "client-3", "client-4", "client-5"}, "oldest handler ended, fifth registered")
                assert len(rig.viewer._clients) == 4
                await until(lambda: fifth.events() == ["scene", "state"], "fifth greeted")

        run(scenario)

    def test_eviction_addresses_only_the_oldest_and_its_traffic_stops(self):
        async def scenario():
            async with running() as rig:
                pages = await open_pages(rig, 4)
                await until(lambda: all(p.events() == ["scene", "state"] for p in pages), "four greeted")
                before = {p.client: len(p.addressed()) for p in pages}
                fifth = rig.page(5)
                fifth.open()
                await until(lambda: len(pending_handlers()) == 4, "handler count back to four")
                for p in pages[1:]:
                    assert p.addressed("evict") == []
                assert len(pages[0].addressed("evict")) == 1
                # a later broadcast reaches the four live clients and not the evicted one
                rig.deck.get_resource("c3-plate").get_item("B2").set_volume(50)
                await until(lambda: "state" in fifth.events()[2:], "state to the fifth")
                assert len(pages[0].addressed()) == before["client-1"] + 1  # only the evict itself
                # its hello is no longer heard
                pages[0].hello()
                await turn(20)
                assert rig.viewer.clients_seen == []

        run(scenario)

    def test_the_cap_holds_over_many_reloads_and_evicts_in_insertion_order(self):
        async def scenario():
            async with running() as rig:
                seen_max = 0
                pages = []
                for i in range(1, 11):
                    p = rig.page(i)
                    pages.append(p)
                    p.open()
                    seen_max = max(seen_max, len(rig.viewer._clients))
                    await turn(3)
                    seen_max = max(seen_max, len(rig.viewer._clients))
                await until(lambda: len(pending_handlers()) == 4, "four live handlers")
                assert seen_max <= 4
                assert rig.client_ids() == {f"client-{i}" for i in range(7, 11)}
                evicted = [m["client"] for m in rig.bus.kinds("evict")]
                assert evicted == [f"client-{i}" for i in range(1, 7)]

        run(scenario)

    def test_a_bye_frees_a_slot_so_no_eviction_is_needed(self):
        async def scenario():
            async with running() as rig:
                pages = await open_pages(rig, 4)
                pages[1].bye()
                await until(lambda: len(pending_handlers()) == 3, "bye ended a handler")
                fifth = rig.page(5)
                fifth.open()
                await until(lambda: "client-5" in rig.client_ids(), "fifth registered")
                assert rig.bus.kinds("evict") == []
                assert len(rig.viewer._clients) == 4

        run(scenario)

    def test_bye_ends_the_connection_its_handler_and_its_place_in_clients(self):
        async def scenario():
            async with running() as rig:
                x, y = await open_pages(rig, 2)
                await until(lambda: x.events() == ["scene", "state"], "greeted")
                x.bye()
                assert "client-1" not in rig.client_ids()  # left _clients synchronously
                await until(lambda: len(pending_handlers()) == 1, "x's handler ended")
                assert rig.client_ids() == {"client-2"}
                x.bye()  # a second bye is harmless
                Page(rig.bus, rig.viewer.viewer_id, "ghost").bye()  # so is one for a client never seen
                Page(rig.bus, "another-viewer", "client-2").bye()  # and one for another viewer
                await turn(20)
                assert rig.client_ids() == {"client-2"} and len(pending_handlers()) == 1
                x.hello()  # x is gone: its hello is not heard
                await turn(20)
                assert rig.viewer.clients_seen == []

        run(scenario)

    def test_a_bye_right_after_the_open_leaves_no_handler_and_sends_the_departed_nothing(self):
        async def scenario():
            async with running() as rig:
                p = rig.page(1)
                p.open()
                p.bye()  # before the handler task has run a single step
                await until(lambda: pending_handlers() == [], "handler ended")
                await turn(20)
                assert rig.viewer._clients == set()
                assert p.addressed("msg") == [], "nothing is posted to a client that already left"

        run(scenario)


# --------------------------------------------------------------------------------------------------
# stop(): ends every connection, posts close, leaves the channel, idempotent
# --------------------------------------------------------------------------------------------------
class TestStop:
    def test_stop_ends_every_connection_then_posts_close_then_leaves_the_channel(self):
        async def scenario():
            mod = load_viewer3d()
            bus = Bus()
            handlers_at_close: list[int] = []
            bus.on_post = lambda m: handlers_at_close.append(len(pending_handlers())) if m["kind"] == "close" else None
            viewer = mod.DockedViewer3D(make_deck(), channel_factory=bus.endpoint, session="s")
            await viewer.start()
            rig = Rig(mod, viewer, None, bus)
            await open_pages(rig, 3)
            assert len(pending_handlers()) == 3  # positive control
            assert viewer._subscribed, "the viewer listens to its tree before stop"
            await asyncio.wait_for(viewer.stop(), 5)
            closes = bus.kinds("close")
            assert closes == [{"kind": "close", "viewer": viewer.viewer_id, "reason": closes[0]["reason"]}]
            assert isinstance(closes[0]["reason"], str) and closes[0]["reason"]
            assert bus.log[-1] == closes[0], "close is the last thing the viewer posts"
            assert handlers_at_close == [0], "every _handler had ended before close was posted"
            assert pending_handlers() == []
            assert viewer._subscribed == {}
            assert viewer._clients == set()
            ep = bus.endpoints[0]
            assert ep.listeners == [] and ep.closed is True

        run(scenario)

    def test_stop_is_idempotent_and_posts_nothing_more(self):
        async def scenario():
            async with running() as rig:
                await open_pages(rig, 2)
                await asyncio.wait_for(rig.viewer.stop(), 5)
                posts = len(rig.bus.log)
                raw = len(rig.bus.endpoints[0].raw_posts)
                await asyncio.wait_for(rig.viewer.stop(), 5)  # the channel is closed: a post would raise
                await asyncio.wait_for(rig.viewer.stop(), 5)
                assert len(rig.bus.log) == posts and len(rig.bus.endpoints[0].raw_posts) == raw
                assert len(rig.bus.kinds("close")) == 1

        run(scenario)

    def test_two_concurrent_stops_post_one_close(self):
        async def scenario():
            async with running() as rig:
                await open_pages(rig, 2)
                await asyncio.wait_for(asyncio.gather(rig.viewer.stop(), rig.viewer.stop()), 5)
                assert len(rig.bus.kinds("close")) == 1
                assert pending_handlers() == []

        run(scenario)

    def test_stopping_a_viewer_that_never_started_raises_nothing_and_posts_nothing(self):
        async def scenario():
            mod = load_viewer3d()
            bus = Bus()
            viewer = mod.DockedViewer3D(make_deck(), channel_factory=bus.endpoint, session="s")
            await asyncio.wait_for(viewer.stop(), 5)
            await asyncio.wait_for(viewer.stop(), 5)
            assert bus.log == []
            assert viewer._subscribed == {}

        run(scenario)

    def test_a_stopped_viewer_answers_no_query_and_accepts_no_open(self):
        async def scenario():
            async with running() as rig:
                # positive control: the live viewer answers both
                n = len(rig.bus.log)
                rig.bus.page_post({"kind": "query"})
                assert [m["kind"] for m in rig.bus.log[n:]] == ["announce"]
                (live,) = await open_pages(rig, 1, start=1)
                assert live.addressed("accept")
                await asyncio.wait_for(rig.viewer.stop(), 5)
                n = len(rig.bus.log)
                rig.bus.page_post({"kind": "query"})
                rig.page(9).open()
                await turn(20)
                assert rig.bus.log[n:] == []
                assert rig.viewer._clients == set() and pending_handlers() == []

        run(scenario)

    def test_stop_with_no_clients_and_stop_right_after_start(self):
        async def scenario():
            async with running() as rig:
                await asyncio.wait_for(rig.viewer.stop(), 5)
                assert len(rig.bus.kinds("close")) == 1

        run(scenario)

    def test_no_post_is_attempted_on_a_closed_channel_even_when_a_late_message_arrives(self):
        async def scenario():
            async with running() as rig:
                (p,) = await open_pages(rig, 1)
                await asyncio.wait_for(rig.viewer.stop(), 5)
                # a message the dying page posted after the viewer left: nobody is listening
                p.hello()
                p.bye()
                rig.bus.page_post({"kind": "query"})
                await turn(20)
                assert rig.viewer.clients_seen == []

        run(scenario)


# --------------------------------------------------------------------------------------------------
# dock() (D11 "dock(deck, **kw)")
# --------------------------------------------------------------------------------------------------
def answer_announces_with_a_page(bus: Bus, mod=None) -> None:
    """When a viewer announces, play a page that opens and says hello at once (so dock()'s wait ends)."""
    state = {"n": 0}

    def on_post(m: dict) -> None:
        if m["kind"] == "announce":
            state["n"] += 1
            page = Page(bus, m["viewer"], f"dock-page-{state['n']}")
            asyncio.get_running_loop().call_soon(lambda: (page.open(), page.hello()))

    bus.on_post = on_post


class TestDock:
    def test_dock_returns_a_started_viewer_after_the_page_says_hello(self):
        async def scenario():
            mod = load_viewer3d()
            bus = Bus()
            answer_announces_with_a_page(bus, mod)
            viewer = await mod.dock(make_deck(), channel_factory=bus.endpoint, session="s")
            try:
                assert isinstance(viewer, mod.DockedViewer3D)
                assert len(viewer.clients_seen) >= 1
                assert len(bus.kinds("announce")) == 1
            finally:
                await viewer.stop()

        run(scenario)

    def test_second_dock_stops_the_first_before_announcing_the_second(self):
        async def scenario():
            mod = load_viewer3d()
            bus = Bus()
            answer_announces_with_a_page(bus, mod)
            v1 = await mod.dock(make_deck(), channel_factory=bus.endpoint, session="s")
            v2 = await mod.dock(make_deck(), channel_factory=bus.endpoint, session="s")
            try:
                assert v1 is not v2 and v1.viewer_id != v2.viewer_id
                assert v1._subscribed == {}
                kinds = [(m["kind"], m["viewer"]) for m in bus.log if m["kind"] in ("announce", "close")]
                assert kinds == [("announce", v1.viewer_id), ("close", v1.viewer_id), ("announce", v2.viewer_id)]
                # a query now yields exactly one announce, the new viewer's
                n = len(bus.log)
                bus.page_post({"kind": "query"})
                got = bus.log[n:]
                assert [(m["kind"], m["viewer"]) for m in got] == [("announce", v2.viewer_id)]
                assert bus.endpoints[0].closed and not bus.endpoints[1].closed
            finally:
                await v2.stop()

        run(scenario)

    def test_a_dock_after_the_users_own_stop_posts_no_second_close_for_the_old_viewer(self):
        async def scenario():
            mod = load_viewer3d()
            bus = Bus()
            answer_announces_with_a_page(bus, mod)
            v1 = await mod.dock(make_deck(), channel_factory=bus.endpoint, session="s")
            await v1.stop()
            assert len(bus.kinds("close", viewer=v1.viewer_id)) == 1
            v2 = await mod.dock(make_deck(), channel_factory=bus.endpoint, session="s")
            try:
                assert len(bus.kinds("close", viewer=v1.viewer_id)) == 1
            finally:
                await v2.stop()

        run(scenario)

    def test_a_timeout_waiting_for_the_browser_is_stated_in_one_printed_line(self, capsys):
        waited: list[Any] = []

        class Fake:
            def __init__(self, deck, **kw):
                self.deck, self.kw = deck, kw

            async def start(self):
                return None

            async def stop(self):
                return None

            async def wait_for_browser(self, timeout=None):
                waited.append(timeout)
                raise asyncio.TimeoutError()

        async def scenario():
            mod = load_viewer3d()
            mod.DockedViewer3D = Fake
            viewer = await mod.dock("a-deck", extra="kw")
            assert isinstance(viewer, Fake) and viewer.kw == {"extra": "kw"}

        run(scenario)
        assert waited == [15] or waited == [15.0]
        lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
        assert len(lines) == 1 and "15" in lines[0], lines

    def test_positive_control_no_timeout_no_line(self, capsys):
        class Fake:
            def __init__(self, deck, **kw):
                pass

            async def start(self):
                return None

            async def stop(self):
                return None

            async def wait_for_browser(self, timeout=None):
                return None

        async def scenario():
            mod = load_viewer3d()
            mod.DockedViewer3D = Fake
            await mod.dock("a-deck")

        run(scenario)
        assert capsys.readouterr().out.strip() == ""

    def test_dock_awaits_the_old_viewers_stop_before_constructing_the_next(self):
        events: list[str] = []

        class Fake:
            count = 0

            def __init__(self, deck, **kw):
                Fake.count += 1
                self.n = Fake.count
                events.append(f"init{self.n}")

            async def start(self):
                events.append(f"start{self.n}")

            async def stop(self):
                events.append(f"stop{self.n}-begin")
                await asyncio.sleep(0.01)
                events.append(f"stop{self.n}-end")

            async def wait_for_browser(self, timeout=None):
                return None

        async def scenario():
            mod = load_viewer3d()
            mod.DockedViewer3D = Fake
            await mod.dock("d1")
            await mod.dock("d2")

        run(scenario)
        assert events == ["init1", "start1", "stop1-begin", "stop1-end", "init2", "start2"]

    def test_a_start_that_fails_does_not_leave_a_dead_current_viewer(self):
        async def scenario():
            mod = load_viewer3d()
            bus = Bus()

            def bad_factory():
                raise RuntimeError("no channel")

            with pytest.raises(RuntimeError):
                await mod.dock(make_deck(), channel_factory=bad_factory, session="s")
            answer_announces_with_a_page(bus, mod)
            v = await mod.dock(make_deck(), channel_factory=bus.endpoint, session="s")  # works afterwards
            await v.stop()

        run(scenario)


# --------------------------------------------------------------------------------------------------
# The real channel adapter, against fakes of ``js`` and ``pyodide.ffi`` (the JS side is not testable here)
# --------------------------------------------------------------------------------------------------
class FakeJsChannel:
    def __init__(self, name: str) -> None:
        self.name, self.posted, self.listeners, self.closed = name, [], [], False

    def postMessage(self, message):  # noqa: N802 - the JS name
        self.posted.append(message)

    def addEventListener(self, kind, proxy):  # noqa: N802
        assert kind == "message"
        self.listeners.append(proxy)

    def removeEventListener(self, kind, proxy):  # noqa: N802
        assert kind == "message"
        self.listeners.remove(proxy)

    def close(self):
        self.closed = True


class FakeProxy:
    def __init__(self, fn) -> None:
        self.fn, self.destroyed = fn, False

    def __call__(self, event):
        return self.fn(event)

    def destroy(self):
        self.destroyed = True


def event(data):
    return types.SimpleNamespace(data=data)


class TestRealChannelAdapter:
    def _install_fakes(self, monkeypatch):
        made: list[FakeJsChannel] = []
        js = types.ModuleType("js")
        js.BroadcastChannel = types.SimpleNamespace(new=lambda name: made.append(FakeJsChannel(name)) or made[-1])
        ffi = types.ModuleType("pyodide.ffi")
        ffi.create_proxy = FakeProxy
        pyodide = types.ModuleType("pyodide")
        pyodide.ffi = ffi
        monkeypatch.setitem(sys.modules, "js", js)
        monkeypatch.setitem(sys.modules, "pyodide", pyodide)
        monkeypatch.setitem(sys.modules, "pyodide.ffi", ffi)
        return made

    def test_make_viz3d_channel_opens_the_named_channel_and_round_trips(self, monkeypatch):
        made = self._install_fakes(monkeypatch)
        mod = load_viewer3d()
        channel = mod.make_viz3d_channel()
        assert [c.name for c in made] == ["praxis_viz3d"]
        channel.post('{"kind": "x"}')
        assert made[0].posted == ['{"kind": "x"}']
        heard = []
        channel.add_listener(heard.append)
        assert len(made[0].listeners) == 1
        made[0].listeners[0](event('{"kind": "query"}'))
        assert heard == ['{"kind": "query"}']  # the listener gets the event's data, a string

    def test_remove_listener_detaches_and_destroys_the_proxy_and_close_closes(self, monkeypatch):
        made = self._install_fakes(monkeypatch)
        mod = load_viewer3d()
        channel = mod.make_viz3d_channel()
        a, b = (lambda d: None), (lambda d: None)
        channel.add_listener(a)
        channel.add_listener(b)
        proxies = list(made[0].listeners)
        channel.remove_listener(a)
        assert made[0].listeners == [proxies[1]] and proxies[0].destroyed and not proxies[1].destroyed
        channel.remove_listener(a)  # a second removal is harmless
        channel.close()
        assert made[0].listeners == [] and proxies[1].destroyed and made[0].closed

    def test_a_docked_viewer_runs_end_to_end_on_the_adapter(self, monkeypatch):
        made = self._install_fakes(monkeypatch)
        mod = load_viewer3d()

        async def scenario():
            viewer = mod.DockedViewer3D(make_deck(), session="s")  # default factory: the real adapter
            await viewer.start()
            (fake,) = made
            assert [json.loads(m)["kind"] for m in fake.posted] == ["announce"]
            fake.listeners[0](event(json.dumps({"kind": "query"})))
            assert [json.loads(m)["kind"] for m in fake.posted] == ["announce", "announce"]
            await viewer.stop()
            assert fake.listeners == [] and fake.closed
            assert json.loads(fake.posted[-1])["kind"] == "close"

        run(scenario)
