#!/usr/bin/env python3
"""Spike S4 (notebook display epic, task C1): the pin's ``pylabrobot.visualizer3D`` in the
JupyterLite Pyodide kernel.

Pre-registered by ``scripts/spikes/260929_s4_viewer3d_pyodide.bth.toml`` (committed BEFORE the
first run; this file was AUTHORED ONLY: no browser, no dist build and no ``bth run`` had
happened when it was committed). Design: ``.praxia/docs/specs/260929_notebook-display-epic.md``
D1 (row S4), D11 (the docked viewer, the ``PACKAGE_ROOT`` rebind, GATE X), D16 (shared unit
runner, bounded teardown), D17 (one declared bounded unit ``viewer3d_pyodide``, 10 min, resume,
completeness) and Sprint C task C1. Run it as::

    bth run --project-slug praxis --output-paths outputs/spikes/260929_s4 -- \
        uv run --no-sync python3 scripts/spikes/260929_s4_viewer3d_pyodide.py \
        --out-dir outputs/spikes/260929_s4 --dist <dist built at the pin> [--resume]

(``bth run`` has no ``--out`` option; the result reaches bathos through ``$BTH_RESULTS_PATH``.)

DIST REQUIREMENT (a stated limitation). Only a dist built at the PLR pin (1.0.0b1,
``786ac2c4e4f7afe37885af2d98ff5b0afe274c67``) contains ``pylabrobot/visualizer3D``. The local
``web-repl/dist`` built 260828 carries PLR 0.2.2, which does NOT: against it this probe fails
fast (``aborted = "visualizer3d_absent"``), records the PLR version it actually saw, and the
outcome is ``invalid`` (no branch claim). Never cite an S4 branch from such a run.

Two modes, one file, the same shape as the S3 driver (``260929_s3_ipython_hooks.py``, left
untouched: its script hash is recorded in a committed bathos lock; the shared plumbing is
DUPLICATED from it on purpose so the spikes stay independent):

* **Driver** (no ``--unit``): runs the one D17 S4 unit as its own subprocess
  ``<script> --unit viewer3d_pyodide --out-dir <dir> ...`` through ``unit_runner.run_unit``
  (timeout = 10 min + 60 s), applies the ``--resume`` rule, and evaluates the sidecar's
  ``[outcomes]`` inputs ONLY when the unit is complete. An incomplete run writes no
  ``$BTH_RESULTS_PATH`` and exits 3, so bathos records no outcome.
* **Unit** (``--unit viewer3d_pyodide``): ``ensure_token`` -> arm the ``Watchdog`` (10 min) ->
  clear own stamp/artifact/timeout marker -> probe -> write ``<out>/units/viewer3d_pyodide.json``
  under the watchdog lock -> bounded teardown (browser and Playwright closed, ``kill_tree``,
  flush) -> commit ``<out>/units/viewer3d_pyodide.stamp.json`` through ``Watchdog.commit`` ->
  ``os._exit(stamp.exit)``.

What the unit does. It seeds a notebook (built in this file; its canonical JSON is the
``fixture`` input, i.e. the probe's kernel code), opens it in the served lab with FULL Chromium,
waits for the Pyodide kernel (PLR boots through PYTHONSTARTUP and gates every cell on that
boot), and then runs the probe cells in that ONE kernel: the imports STUB-FREE (``socket``,
``http.server``, ``webbrowser``, ``threading``; ``websockets``, ``websockets.asyncio.server``,
``websockets.http11``; ``pylabrobot.visualizer3D`` and its sub-modules) and
``socket.gethostname()``; the D17 negative control (a stub-free import of ``tkinter`` and
``curses``, absent from Pyodide, must fail); the WebLoop checks (``call_later`` with a cancel
control, ``call_soon_threadsafe``); the construction and ``start()`` of a ``Viewer3D`` subclass
stub shaped like D11's ``DockedViewer3D`` (a spike-level stand-in: the real subclass is C3)
with no threads, no ``websockets.serve``, no file server and no browser (each patched to raise
during ``start()``, with a control that the patches trip); the real inherited ``_handler``
driven by a virtual connection (first ``scene`` message bytes, its ``mesh`` models) over the
STOCK ``PACKAGE_ROOT`` and then over the REBOUND one (D11's guarded first-construction rebind
to an empty ``tempfile.mkdtemp()``), with the first ``_models_on_disk`` walk timed on each root
through an instrument wrapper; a seeded ``.glb`` positive control that proves the ``mesh``
reader can say yes; and the loop-driven rebuild after ``assign_child_resource``.

Measurement discipline (``~/.claude/rules/BATHOS.md``): every result is read from the NOTEBOOK
MODEL (``notebook.content.model.cells``: each cell's ``outputs`` and ``execution_count`` as
JSON), never from the DOM, the console or printed text. Kernel-side observations are sent back
as structured ``display_data`` bundles (``application/json``, raw) and read from the same
model. A verdict that could be a probe bug is only reported next to a control that proves the
instrument can say the opposite (see the sidecar); anything uncontrolled or unmeasured is
``None``, and any ``None`` in a validity check makes the run ``invalid``, never a branch claim.
A probe that raises is an ``error`` finding, never a negative result. A raised STEP inside the
viewer path is ``None`` (inconclusive), not a measured "no"; only the import attempts and the
direct loop-API calls turn a raised exception into a measured failure.

``--dry-run`` prints the unit, the pre-registered fields, the kernel cells and the resolved
inputs' sources without launching a browser or hashing the dist.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import hashlib
import importlib.util
import json
import logging
import os
import subprocess
import sys
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

LOG = logging.getLogger("s4_spike")

SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "unit_runner.py"
REPL_SMOKE_PATH = REPO_ROOT / "scripts" / "repl_smoke.py"
DEFAULT_DIST = REPO_ROOT / "web-repl" / "dist"

UNIT_NAME = "viewer3d_pyodide"
#: D17 S4 row: ONE bounded unit, 10 min. The driver kills at this + 60 s (D16/D17). The
#: estimate is the spec's, not a measurement; not changed here.
UNIT_TIMEOUT_S = 10 * 60.0
DRIVER_EXTRA_S = 60.0
#: The probe stops STARTING work at this fraction of the unit budget (540 s of 600 s), so an
#: artifact reporting how far it got is written before the watchdog can fire.
DEADLINE_FRACTION = 0.9

#: The PLR pin (D11, Revision 10). A dist built at any other PLR is not an S4 measurement.
PIN_SHA = "786ac2c4e4f7afe37885af2d98ff5b0afe274c67"
PIN_VERSION_PREFIX = "1.0.0b1"

VIEWPORT = {"width": 1440, "height": 900}
NB_PATH = "s4_viewer3d_pyodide.ipynb"
NAV_TIMEOUT_MS = 90_000
#: Internal step caps (seconds). Each is further clipped to the time left before the deadline.
IDLE_TIMEOUT_S = 240.0
WARMUP_TIMEOUT_S = 180.0
CELL_TIMEOUT_S = 45.0
HEAVY_CELL_TIMEOUT_S = 90.0

#: The D17 negative control: modules known ABSENT from Pyodide (its docs list tkinter and curses
#: as removed). A stub-free ``importlib.import_module`` of each must fail.
NEG_ABSENT_MODULES = ("tkinter", "curses")

#: The import groups of D1 S4. STDLIB failing is S4-B; the others are recorded.
STDLIB_IMPORTS = ("socket", "http.server", "webbrowser", "threading")
INFO_IMPORTS = ("ssl",)  # recorded only: the boot stubs it (install_native_stubs), not a criterion
WEBSOCKETS_IMPORTS = ("websockets", "websockets.asyncio.server", "websockets.http11")
PLR_IMPORTS = (
    "pylabrobot.visualizer3D",
    "pylabrobot.visualizer3D.scene",
    "pylabrobot.visualizer3D.facility",
    "pylabrobot.visualizer3D.server",
)
ALL_IMPORTS = STDLIB_IMPORTS + INFO_IMPORTS + WEBSOCKETS_IMPORTS + PLR_IMPORTS


# --------------------------------------------------------------------------- #
# The unit table (D17 S4 row) and its pre-registered artifact fields
# --------------------------------------------------------------------------- #


@dataclasses.dataclass(frozen=True)
class UnitSpec:
    name: str
    required: tuple[str, ...]


UNITS: tuple[UnitSpec, ...] = (
    UnitSpec(
        UNIT_NAME,
        (
            "kernel_ready", "boot", "prelude", "cells", "sub_errors", "plr", "imports", "hostname",
            "negative_control", "loop", "viewer", "roots", "scene", "walk", "seeded_control",
            "skipped", "all_cells_done", "deadline_hit", "aborted",
        ),
    ),
)
UNIT_NAMES = tuple(u.name for u in UNITS)
UNIT_BY_NAME = {u.name: u for u in UNITS}


# --------------------------------------------------------------------------- #
# The kernel cells (the seeded notebook). Kernel-side code has never met the real dist:
# every observation is echoed as a structured bundle and read back from the model.
# --------------------------------------------------------------------------- #

SETUP_SRC = r"""
import asyncio, importlib, importlib.util, json, os, sys, tempfile, threading, time, types, warnings
try:
    from IPython.display import display
except ImportError:  # pragma: no cover - the kernel always has IPython
    display = globals()["display"]

_S4 = {"walk_log": [], "root_done": False, "orig_models": None, "ready": False}


def _s4_emit(tag, **payload):
    payload["tag"] = tag
    clean = json.loads(json.dumps(payload, default=str))
    display({"application/json": clean, "text/plain": json.dumps(clean)}, raw=True, metadata={"s4": tag})


def _s4_err(e):
    return {"type": type(e).__name__, "message": str(e)[:300], "name": getattr(e, "name", None)}


def _s4_resolution():
    best = None
    for _ in range(100):
        a = time.perf_counter()
        b = a
        n = 0
        while b == a and n < 200000:
            b = time.perf_counter()
            n += 1
        if b > a and (best is None or b - a < best):
            best = b - a
    return best


def _s4_setup():
    out = {"python_version": sys.version.split()[0], "platform": sys.platform,
           "find_spec": {}, "find_spec_errors": {}, "errors": {}}
    for name in ("pylabrobot", "pylabrobot.visualizer3D", "websockets"):
        try:
            out["find_spec"][name] = importlib.util.find_spec(name) is not None
        except BaseException as e:
            out["find_spec"][name] = None
            out["find_spec_errors"][name] = _s4_err(e)
    try:
        import pylabrobot
        out["pylabrobot_version"] = getattr(pylabrobot, "__version__", None)
        out["pylabrobot_file"] = getattr(pylabrobot, "__file__", None)
    except BaseException as e:
        out["errors"]["pylabrobot"] = _s4_err(e)
    try:
        info = importlib.import_module("pylabrobot._praxis_build_info")
        out["plr_source_sha"] = getattr(info, "PLR_SOURCE_SHA", None)
        out["plr_build_id"] = getattr(info, "BUILD_ID", None)
    except BaseException as e:
        out["plr_source_sha"] = None
        out["errors"]["build_info"] = _s4_err(e)
    try:
        import importlib.metadata as md
        for dist in ("pylabrobot", "websockets"):
            try:
                out[dist + "_dist_version"] = md.version(dist)
            except BaseException as e:
                out[dist + "_dist_version"] = None
                out["errors"][dist + "_dist"] = _s4_err(e)
    except BaseException as e:
        out["errors"]["metadata"] = _s4_err(e)
    out["boot_stubs"] = {
        n: (n in sys.modules and getattr(sys.modules[n], "__spec__", None) is None)
        for n in ("ssl", "usb", "serial")
    }
    out["preloaded"] = {n: (n in sys.modules) for n in @@ALL_IMPORTS@@}
    out["perf_counter_resolution_s"] = _s4_resolution()
    return out


_s4_emit("setup", **_s4_setup())
"""

IMPORTS_SRC = r"""
def _s4_import(name):
    pre = sys.modules.get(name)
    rec = {"preloaded": pre is not None,
           "preloaded_stub_like": pre is not None and getattr(pre, "__spec__", None) is None}
    t = time.perf_counter()
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            mod = importlib.import_module(name)
        rec["ok"] = True
        rec["file"] = getattr(mod, "__file__", None)
        rec["stub_like"] = getattr(mod, "__spec__", None) is None
        rec["warnings"] = sorted({w.category.__name__ for w in caught})
    except BaseException as e:
        rec["ok"] = False
        rec["error"] = _s4_err(e)
    rec["seconds"] = round(time.perf_counter() - t, 4)
    return rec


_names = @@ALL_IMPORTS@@
_records = {}
for _n in _names:
    _records[_n] = _s4_import(_n)
_bare = types.ModuleType("s4_bare_stub_control")
_controls = {
    "positive_json": _s4_import("json"),
    "bare_module_reads_stub_like": getattr(_bare, "__spec__", None) is None,
}
_s4_emit("imports", order=list(_names), records=_records, controls=_controls)
"""

HOSTNAME_SRC = r"""
try:
    import socket
    _v = socket.gethostname()
    _rec = {"ok": isinstance(_v, str) and len(_v) > 0, "value": _v[:80] if isinstance(_v, str) else None,
            "value_type": type(_v).__name__}
except BaseException as e:
    _rec = {"ok": False, "error": _s4_err(e)}
_s4_emit("hostname", **_rec)
"""

NEG_SRC = r"""
_cands = {}
for _n in @@NEG_MODULES@@:
    try:
        importlib.import_module(_n)
        _cands[_n] = {"ok": True}
    except BaseException as e:
        _cands[_n] = {"ok": False, "error": _s4_err(e)}
_s4_emit("neg_import", candidates=_cands)
"""

LOOP_SRC = r"""
_rec = {"errors": {}}
_loop = asyncio.get_running_loop()
_rec["loop_type"] = type(_loop).__module__ + "." + type(_loop).__qualname__
_rec["has_call_later"] = hasattr(_loop, "call_later")
_rec["has_call_soon_threadsafe"] = hasattr(_loop, "call_soon_threadsafe")
_fired = []
_t0 = time.perf_counter()
try:
    _h_later = _loop.call_later(0.05, _fired.append, "later")
    _h_cancel = _loop.call_later(0.05, _fired.append, "cancelled")
    _h_cancel.cancel()
    _rec["cancel_returned_handle"] = hasattr(_h_cancel, "cancel")
except BaseException as e:
    _rec["errors"]["call_later"] = _s4_err(e)
try:
    _loop.call_soon_threadsafe(_fired.append, "soon_threadsafe")
except BaseException as e:
    _rec["errors"]["call_soon_threadsafe"] = _s4_err(e)
for _ in range(60):
    if "later" in _fired and "soon_threadsafe" in _fired:
        break
    await asyncio.sleep(0.05)
await asyncio.sleep(0.15)  # a cancelled timer that wrongly fires would have by now
_rec["fired"] = list(_fired)
_rec["call_later_fired"] = "later" in _fired
_rec["cancelled_fired"] = "cancelled" in _fired
_rec["soon_threadsafe_fired"] = "soon_threadsafe" in _fired
_rec["elapsed_s"] = round(time.perf_counter() - _t0, 4)


async def _seven():
    return 7


try:
    _rec["ensure_future_ok"] = (await asyncio.ensure_future(_seven())) == 7
except BaseException as e:
    _rec["ensure_future_ok"] = None
    _rec["errors"]["ensure_future"] = _s4_err(e)
try:
    _ev = asyncio.Event()
    try:
        await asyncio.wait_for(_ev.wait(), 0.05)
        _rec["wait_for_times_out"] = False
    except asyncio.TimeoutError:
        _rec["wait_for_times_out"] = True
except BaseException as e:
    _rec["wait_for_times_out"] = None
    _rec["errors"]["wait_for"] = _s4_err(e)
_th = {}
try:
    _t = threading.Thread(target=lambda: None)
    _t.start()
    _t.join(2)
    _th["thread_start_ok"] = True
except BaseException as e:
    _th["thread_start_ok"] = False
    _th["thread_start_error"] = _s4_err(e)
try:
    _th["to_thread_ok"] = (await asyncio.wait_for(asyncio.to_thread(lambda: 1), 5)) == 1
except BaseException as e:
    _th["to_thread_ok"] = False
    _th["to_thread_error"] = _s4_err(e)
_th["active_count"] = threading.active_count()
_rec["threads"] = _th
_s4_emit("loop", **_rec)
"""

VIEWER_SETUP_SRC = r"""
_rec = {"errors": {}}
try:
    from pylabrobot.visualizer3D import server as _s4_server
    from pylabrobot.visualizer3D.scene import legacy_size as _s4_legacy_size
    from pylabrobot.visualizer3D.facility import Facility as _S4Facility
    from pylabrobot.resources import Coordinate as _S4Coordinate
    from pylabrobot.resources.hamilton import (
        hamilton_96_tiprack_1000uL, hamilton_plate_carrier_L5_ac, hamilton_tip_carrier_L5)
    from pylabrobot.resources.corning import cor_96_wellplate_360uL_Fb

    def _s4_deck():
        f = _S4Facility(name="s4-facility", size_x=1200, size_y=800, size_z=600)
        car = hamilton_tip_carrier_L5(name="s4-tip-carrier")
        car[0] = hamilton_96_tiprack_1000uL(name="s4-tips")
        f.assign_child_resource(car, location=_S4Coordinate(100, 100, 0))
        pc = hamilton_plate_carrier_L5_ac(name="s4-plate-carrier")
        pc[0] = cor_96_wellplate_360uL_Fb(name="s4-plate")
        f.assign_child_resource(pc, location=_S4Coordinate(400, 100, 0))
        return f

    def _s4_ensure_root():
        # D11's guarded, idempotent first-construction rebind: the ONE deliberate PLR-state change
        if _S4["root_done"]:
            return
        _s4_server.PACKAGE_ROOT = tempfile.mkdtemp()
        _S4["root_done"] = True

    class _S4Viewer(_s4_server.Viewer3D):
        # a spike-level stand-in shaped like D11's DockedViewer3D: overrides __init__, start, stop
        def __init__(self, root, *, rebind=True, **kw):
            if rebind:
                _s4_ensure_root()
            kw["open_browser"] = False
            super().__init__(root, **kw)

        async def start(self):
            self._loop = asyncio.get_running_loop()
            self._browser_drawing = asyncio.Event()
            self._legacy_bytes = _s4_legacy_size(self.root)  # synchronous: no threads
            # no websockets.serve, no file server, no _models_on_disk pre-warm, no browser

        async def stop(self):
            await super().stop()

    class _S4Conn:
        # a virtual connection: async send, async iteration over a queue, a sentinel ends it
        def __init__(self):
            self.sent = []
            self.q = asyncio.Queue()

        async def send(self, message):
            self.sent.append(message)

        def __aiter__(self):
            return self

        async def __anext__(self):
            item = await self.q.get()
            if item is None:
                raise StopAsyncIteration
            return item

        def end(self):
            self.q.put_nowait(None)

    _S4["orig_models"] = _s4_server._models_on_disk

    def _s4_timed_models(root):
        before = _S4["orig_models"].cache_info().misses
        t = time.perf_counter()
        found = _S4["orig_models"](root)
        dt = time.perf_counter() - t
        _S4["walk_log"].append({"root": root, "seconds": dt, "n_models": len(found),
                                "cache_miss": _S4["orig_models"].cache_info().misses > before})
        return found

    _s4_server._models_on_disk = _s4_timed_models
    _S4["ready"] = True
    _rec["ready"] = True
    _rec["viewer_base"] = _s4_server.Viewer3D.__module__ + "." + _s4_server.Viewer3D.__qualname__
    _rec["overrides"] = sorted(n for n in vars(_S4Viewer) if callable(getattr(_s4_server.Viewer3D, n, None)))
except BaseException as e:
    _rec["ready"] = False
    _rec["errors"]["setup"] = _s4_err(e)
_s4_emit("viewer_setup", **_rec)
"""

VIEWER_SRC = r"""
_rec = {"errors": {}}
_v = None
try:
    _deck = _s4_deck()
    _rec["deck_children"] = len(_deck.get_all_children())
    _v = _S4Viewer(_deck, rebind=False)
    _rec["construct_ok"] = True
    _rec["loop_before_start"] = _v._loop is None
    _rec["subscribed"] = len(_v._subscribed)
    _rec["base_is_viewer3d"] = type(_v).__mro__[1] is _s4_server.Viewer3D
except BaseException as e:
    _rec["construct_ok"] = None
    _rec["errors"]["construct"] = _s4_err(e)
if _v is not None:
    import webbrowser
    import websockets
    _calls = {"thread_start": 0, "websockets_serve": 0, "webbrowser_open": 0}

    def _mk(key):
        def _f(*a, **k):
            _calls[key] += 1
            raise RuntimeError("s4-patched-" + key)
        return _f

    _orig = (threading.Thread.start, websockets.serve, webbrowser.open)
    try:
        threading.Thread.start = _mk("thread_start")
        websockets.serve = _mk("websockets_serve")
        webbrowser.open = _mk("webbrowser_open")
        _ctl = {}
        for _key, _fn in (("thread_start", lambda: threading.Thread.start(None)),
                          ("websockets_serve", lambda: websockets.serve(None, "h", 1)),
                          ("webbrowser_open", lambda: webbrowser.open("http://x"))):
            try:
                _fn()
                _ctl[_key] = False
            except RuntimeError as e:
                _ctl[_key] = str(e) == "s4-patched-" + _key
        _rec["patch_control_all_raise"] = all(_ctl.values())
        _rec["patch_control"] = _ctl
        for _key in _calls:
            _calls[_key] = 0
        _rec["threads_before"] = threading.active_count()
        try:
            await _v.start()
            _rec["start_ok"] = True
        except BaseException as e:
            _rec["start_ok"] = None
            _rec["errors"]["start"] = _s4_err(e)
        _rec["calls_during_start"] = dict(_calls)
        _rec["threads_after"] = threading.active_count()
    finally:
        threading.Thread.start, websockets.serve, webbrowser.open = _orig
    try:
        _rec["loop_is_running_loop"] = _v._loop is asyncio.get_running_loop()
        _rec["browser_event_is_event"] = isinstance(_v._browser_drawing, asyncio.Event)
        _rec["legacy_bytes"] = _v._legacy_bytes
        _rec["walk_calls_in_start"] = len(_S4["walk_log"])
    except BaseException as e:
        _rec["errors"]["post_start_reads"] = _s4_err(e)
    try:
        await _v.stop()
        _rec["stop_ok"] = True
        _rec["subscribed_after_stop"] = len(_v._subscribed)
    except BaseException as e:
        _rec["stop_ok"] = None
        _rec["errors"]["stop"] = _s4_err(e)
_s4_emit("viewer", **_rec)
"""

ROOTS_STOCK_SRC = r"""
_rec = {"errors": {}}
_S4["walk_log"].clear()
try:
    _root = _s4_server.PACKAGE_ROOT
    _real = os.path.realpath(_root)
    _plr_dir = os.path.realpath(os.path.dirname(sys.modules["pylabrobot"].__file__))
    _rec["root"] = _root
    _rec["exists"] = os.path.isdir(_root)
    _rec["server_file"] = getattr(_s4_server, "__file__", None)
    _rec["derived_from_server_file"] = (
        os.path.dirname(os.path.dirname(os.path.abspath(_s4_server.__file__))) == _root)
    _rec["in_plr_package"] = _real == _plr_dir
    _rec["in_site_packages"] = "site-packages" in _real
    _t = time.perf_counter()
    _n = 0
    _d = 0
    for _dir, _, _files in os.walk(_root):
        _d += 1
        _n += sum(1 for _f in _files if _f.endswith(".glb"))
    _rec["glb_count"] = _n
    _rec["dirs_walked"] = _d
    _rec["glb_walk_seconds"] = time.perf_counter() - _t
except BaseException as e:
    _rec["errors"]["roots"] = _s4_err(e)
try:
    _deck = _s4_deck()
    _v = _S4Viewer(_deck, rebind=False)
    await _v.start()
    _S4["walk_log"].clear()
    _t = time.perf_counter()
    _payload = _v._scene_message()
    _rec["scene_build_seconds"] = time.perf_counter() - _t
    _rec["walk_log"] = list(_S4["walk_log"])
    _models = _payload["models"]
    _rec["n_models"] = len(_models)
    _mesh = [m for m in _models if "mesh" in m]
    _rec["n_mesh_models"] = len(_mesh)
    _rec["mesh_model_names"] = [str(m.get("model")) for m in _mesh][:20]
    _msg = _s4_server._encode("scene", _payload)
    _rec["scene_message_bytes"] = len(_msg.encode("utf-8"))
    _rec["root_used"] = _s4_server.PACKAGE_ROOT
    await _v.stop()
except BaseException as e:
    _rec["errors"]["scene"] = _s4_err(e)
_s4_emit("roots_stock", **_rec)
"""

ROOTS_REBOUND_SRC = r"""
_rec = {"errors": {}}
_S4["walk_log"].clear()
_stock_root = _s4_server.PACKAGE_ROOT
_v = None
_conn = None
_task = None
try:
    _rec["root_before"] = _stock_root
    _rec["flag_before"] = _S4["root_done"]
    _deck = _s4_deck()
    _v = _S4Viewer(_deck)  # the FIRST construction with the guard: rebinds PACKAGE_ROOT
    _after = _s4_server.PACKAGE_ROOT
    _rec["root_after"] = _after
    _rec["flag_after"] = _S4["root_done"]
    _rec["exists"] = os.path.isdir(_after)
    _rec["listing"] = sorted(os.listdir(_after))
    _rec["differs_from_stock"] = _after != _stock_root
    _s4_ensure_root()
    _rec["idempotent"] = _s4_server.PACKAGE_ROOT == _after
except BaseException as e:
    _rec["errors"]["rebind"] = _s4_err(e)
if _v is not None:
    try:
        await _v.start()
        _rec["walk_calls_in_start"] = len(_S4["walk_log"])
        _conn = _S4Conn()
        _task = asyncio.ensure_future(_v._handler(_conn))
        for _ in range(100):
            if len(_conn.sent) >= 2:
                break
            await asyncio.sleep(0.05)
        _sent = list(_conn.sent)
        _rec["events"] = [json.loads(m).get("event") for m in _sent]
        _rec["first_message_bytes"] = len(_sent[0].encode("utf-8")) if _sent else None
        _rec["first_message_chars"] = len(_sent[0]) if _sent else None
        _rec["second_message_bytes"] = len(_sent[1].encode("utf-8")) if len(_sent) > 1 else None
        _first = json.loads(_sent[0]) if _sent else {}
        _models = (_first.get("data") or {}).get("models") or []
        _rec["n_models"] = len(_models)
        _rec["n_mesh_models"] = sum(1 for m in _models if "mesh" in m)
        _rec["mesh_substring_count"] = _sent[0].count('"mesh"') if _sent else None
        _rec["epoch_first"] = (_first.get("data") or {}).get("epoch")
        _rec["walk_log"] = list(_S4["walk_log"])
        _rec["scene_message_equals_encode"] = bool(_sent) and _sent[0] == _s4_server._encode("scene", _v._scene_message())
    except BaseException as e:
        _rec["errors"]["handler"] = _s4_err(e)
    try:
        _conn.q.put_nowait(json.dumps({"event": "hello", "data": {
            "backend": "s4", "renderer": "s4", "error": None, "userAgent": "s4"}}))
        await asyncio.wait_for(_v.wait_for_browser(timeout=2), 3)
        _rec["hello_seen"] = len(_v.clients_seen) == 1
        _rec["wait_for_browser_ok"] = True
    except BaseException as e:
        _rec["hello_seen"] = None
        _rec["wait_for_browser_ok"] = None
        _rec["errors"]["hello"] = _s4_err(e)
    try:
        _epoch0 = _v._epoch
        _n0 = len(_conn.sent)
        _car = hamilton_plate_carrier_L5_ac(name="s4-extra-carrier")
        _deck.assign_child_resource(_car, location=_S4Coordinate(700, 100, 0))
        _t = time.perf_counter()
        for _ in range(80):
            if len(_conn.sent) >= _n0 + 2:
                break
            await asyncio.sleep(0.05)
        _new = list(_conn.sent)[_n0:]
        _rec["flush"] = {"events": [json.loads(m).get("event") for m in _new],
                         "epoch_before": _epoch0, "epoch_after": _v._epoch, "rebuilds": _v.rebuilds,
                         "elapsed_s": time.perf_counter() - _t}
    except BaseException as e:
        _rec["errors"]["flush"] = _s4_err(e)
    try:
        if _conn is not None:
            _conn.end()
        if _task is not None:
            await asyncio.wait_for(_task, 3)
            _rec["handler_task_done"] = _task.done()
        await _v.stop()
        _rec["subscribed_after_stop"] = len(_v._subscribed)
    except BaseException as e:
        _rec["errors"]["cleanup"] = _s4_err(e)
_s4_emit("roots_rebound", **_rec)
"""

SEEDED_SRC = r"""
_rec = {"errors": {}}
_prev = _s4_server.PACKAGE_ROOT
_S4["walk_log"].clear()
try:
    _v0 = _S4Viewer(_s4_deck(), rebind=False)
    await _v0.start()
    _models0 = _v0._scene_message()["models"]
    await _v0.stop()
    _pick = next((m for m in _models0 if m.get("type") == "TipCarrier" and m.get("model")), None)
    _pick = _pick or next((m for m in _models0 if m.get("model")), None)
    _name = str(_pick["model"]) if _pick else None
    _rec["model"] = _name
    _rec["mesh_without_seed"] = any("mesh" in m for m in _models0)
    _rec["root_without_seed"] = _prev
    if _name:
        _seed = tempfile.mkdtemp()
        with open(os.path.join(_seed, _name + ".glb"), "wb") as _fh:
            _fh.write(b"glTF\x02\x00\x00\x00")
        _s4_server.PACKAGE_ROOT = _seed
        _v1 = _S4Viewer(_s4_deck(), rebind=False)
        await _v1.start()
        _models1 = _v1._scene_message()["models"]
        await _v1.stop()
        _rec["seed_root"] = _seed
        _rec["n_mesh_models"] = sum(1 for m in _models1 if "mesh" in m)
        _rec["mesh_seen"] = any(m.get("model") == _name and "mesh" in m for m in _models1)
        _rec["only_the_seeded_model"] = all(m.get("model") == _name for m in _models1 if "mesh" in m)
except BaseException as e:
    _rec["errors"]["seeded"] = _s4_err(e)
finally:
    _s4_server.PACKAGE_ROOT = _prev
_rec["root_restored"] = _s4_server.PACKAGE_ROOT == _prev
_s4_emit("seeded", **_rec)
"""

RESTORE_SRC = r"""
_rec = {}
try:
    if _S4["orig_models"] is not None:
        _s4_server._models_on_disk = _S4["orig_models"]
    _rec["models_on_disk_restored"] = _s4_server._models_on_disk is _S4["orig_models"]
    _rec["package_root_final"] = _s4_server.PACKAGE_ROOT
except BaseException as e:
    _rec["error"] = _s4_err(e)
_s4_emit("final", **_rec)
"""


def build_cell_sources(neg_modules: tuple[str, ...] = NEG_ABSENT_MODULES) -> tuple[tuple[str, str], ...]:
    """The seeded notebook's cells, in run order (built at call time so the tests can swap the
    negative-control candidates for a name that is absent from CPython)."""
    subs = {"@@ALL_IMPORTS@@": repr(ALL_IMPORTS), "@@NEG_MODULES@@": repr(tuple(neg_modules))}

    def fill(src: str) -> str:
        for key, value in subs.items():
            src = src.replace(key, value)
        return src

    return (
        ("warm", "s4_warm = 1\n"),
        ("setup", fill(SETUP_SRC)),
        ("imports", fill(IMPORTS_SRC)),
        ("hostname", HOSTNAME_SRC),
        ("neg_import", fill(NEG_SRC)),
        ("loop", LOOP_SRC),
        ("viewer_setup", VIEWER_SETUP_SRC),
        ("viewer", VIEWER_SRC),
        ("roots_stock", ROOTS_STOCK_SRC),
        ("roots_rebound", ROOTS_REBOUND_SRC),
        ("seeded", SEEDED_SRC),
        ("restore", RESTORE_SRC),
    )


CELL_SOURCES: tuple[tuple[str, str], ...] = build_cell_sources()
CELL_NAMES = tuple(name for name, _ in CELL_SOURCES)
CELL_INDEX = {name: i for i, name in enumerate(CELL_NAMES)}
VIEWER_CELLS = ("viewer_setup", "viewer", "roots_stock", "roots_rebound", "seeded", "restore")
HEAVY_CELLS = frozenset({"imports", "viewer_setup", "viewer", "roots_stock", "roots_rebound", "seeded"})


def build_fixture(sources: tuple[tuple[str, str], ...] | None = None) -> dict[str, Any]:
    """The seeded notebook (nbformat 4.5, one code cell per probe cell, nothing executed)."""
    cells = [
        {
            "cell_type": "code",
            "execution_count": None,
            "id": "s4-" + name.replace("_", "-"),
            "metadata": {},
            "outputs": [],
            "source": source.splitlines(keepends=True),
        }
        for name, source in (sources or CELL_SOURCES)
    ]
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python (Pyodide)", "language": "python", "name": "python"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def fixture_bytes() -> bytes:
    return json.dumps(build_fixture(), sort_keys=True, indent=1).encode()


# --------------------------------------------------------------------------- #
# Loading the shared modules BY PATH (nothing edits sys.path)
# --------------------------------------------------------------------------- #


def _load_by_path(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


unit_runner = _load_by_path("unit_runner", RUNNER_PATH)
_REPL_SMOKE: Any = None


def repl_smoke() -> Any:
    """``scripts/repl_smoke.py`` loaded by path, once (ServedDir, chromium_launch_args, ...)."""
    global _REPL_SMOKE
    if _REPL_SMOKE is None:
        _REPL_SMOKE = _load_by_path("repl_smoke", REPL_SMOKE_PATH)
    return _REPL_SMOKE


# --------------------------------------------------------------------------- #
# Hashing and the unit's input set (D17 "Inputs hashed")
# --------------------------------------------------------------------------- #


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | os.PathLike[str]) -> str:
    return unit_runner._sha256_file(Path(path))


@dataclasses.dataclass
class InputEnv:
    """Everything the input set is built from, already hashed (so tests can fake it)."""

    script: str
    runner: str
    harness: str  # sha256 of scripts/repl_smoke.py (loaded by path; D17 "harness" input)
    dist: str
    fixture: str  # sha256 of the canonical JSON of the seeded notebook (the probe's kernel code)
    chrome: str
    driver: str
    base_path: str = "/"
    chrome_path: str = ""
    chrome_version: str = ""


def chrome_version_of(chrome_path: str) -> str:
    try:
        proc = subprocess.run(
            [chrome_path, "--version"], capture_output=True, text=True, timeout=30, check=False
        )
        return (proc.stdout or proc.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unavailable: {type(exc).__name__}"


def build_env(args: argparse.Namespace) -> InputEnv:
    """Resolve and hash the real inputs. Raises FileNotFoundError on a missing dist/chrome."""
    chrome_path = str(repl_smoke().resolve_chrome_path(args.chrome_path))
    if "headless_shell" in chrome_path or "headless-shell" in chrome_path:
        raise RuntimeError(
            f"{chrome_path} is a headless shell; S4 uses FULL Chromium like S1-S3 (D16). "
            "Pass --chrome-path."
        )
    version = chrome_version_of(chrome_path)
    return InputEnv(
        script=sha256_file(SCRIPT_PATH),
        runner=sha256_file(RUNNER_PATH),
        harness=sha256_file(REPL_SMOKE_PATH),
        dist=unit_runner.dist_hash(args.dist),
        fixture=sha256_bytes(fixture_bytes()),
        chrome=sha256_bytes(f"{chrome_path}\n{version}".encode()),
        driver=unit_runner.driver_input(),
        base_path=args.base_path,
        chrome_path=chrome_path,
        chrome_version=version,
    )


def compute_inputs(unit: str, env: InputEnv) -> dict[str, str]:
    """The stamp's ``inputs``: script, runner, harness, dist, fixture, chrome, driver, args.
    S4 has one unit and no upstream unit, so there is no ``upstream:*`` input. The PLR wheel
    that carries ``pylabrobot.visualizer3D`` is covered by the ``dist`` hash (Revision 10).
    """
    return {
        "script": env.script,
        "runner": env.runner,
        "harness": env.harness,
        "dist": env.dist,
        "fixture": env.fixture,
        "chrome": env.chrome,
        "driver": env.driver,
        "args": sha256_bytes(
            json.dumps(
                {"unit": unit, "viewport": VIEWPORT, "base_path": env.base_path}, sort_keys=True
            ).encode()
        ),
    }


# --------------------------------------------------------------------------- #
# Unit files, completeness and the resume rule (D17)
# --------------------------------------------------------------------------- #


def unit_paths(out_dir: Path, name: str) -> dict[str, Path]:
    units = out_dir / "units"
    return {
        "artifact": units / f"{name}.json",
        "stamp": units / f"{name}.stamp.json",
        "timeout": units / f"{name}.timeout.json",
    }


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _rm(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def inspect_unit(out_dir: Path, spec: UnitSpec, current_inputs: dict[str, str]) -> dict[str, Any]:
    """Classify the unit's files against the CURRENT inputs.

    * ``complete``: artifact and a matching stamp exist (the stamp's ``artifact_sha256``
      equals the artifact on disk and its ``inputs`` equal the current inputs). A raised
      probe is complete (its ``error`` finding is in the artifact). Only a timeout or a
      stampless crash is incomplete.
    * ``reusable`` (the ``--resume`` rule): complete AND ``stamp.exit == 0`` AND no
      ``error`` finding AND every pre-registered field present.
    * ``mismatched``: the input names whose hash differs from the stamp's.
    """
    paths = unit_paths(out_dir, spec.name)
    artifact_bytes: bytes | None
    try:
        artifact_bytes = paths["artifact"].read_bytes()
    except OSError:
        artifact_bytes = None
    stamp = _read_json(paths["stamp"])
    artifact = None
    if artifact_bytes is not None:
        try:
            artifact = json.loads(artifact_bytes)
        except ValueError:
            artifact = None
    state: dict[str, Any] = {
        "unit": spec.name,
        "artifact": artifact,
        "stamp": stamp if isinstance(stamp, dict) else None,
        "artifact_path": str(paths["artifact"]),
        "complete": False,
        "reusable": False,
        "mismatched": [],
        "reasons": [],
    }
    if artifact is None or not isinstance(artifact, dict):
        state["reasons"].append("no artifact")
        return state
    if state["stamp"] is None:
        state["reasons"].append("no stamp")
        return state
    stamp = state["stamp"]
    if stamp.get("artifact_sha256") != sha256_bytes(artifact_bytes or b""):
        state["reasons"].append("artifact_sha256 does not match the artifact on disk")
        return state
    recorded = stamp.get("inputs") or {}
    mismatched = sorted(
        name
        for name in set(recorded) | set(current_inputs)
        if recorded.get(name) != current_inputs.get(name)
    )
    state["mismatched"] = mismatched
    if mismatched:
        state["reasons"].append("stamp inputs differ from current inputs")
        return state
    state["complete"] = True
    if stamp.get("exit") != 0:
        state["reasons"].append(f"stamp.exit == {stamp.get('exit')}")
    if artifact.get("error") is not None:
        state["reasons"].append("artifact carries an error finding")
    missing = [f for f in spec.required if f not in artifact] + list(
        artifact.get("missing_fields") or []
    )
    if missing:
        state["reasons"].append(f"pre-registered fields missing: {sorted(set(missing))}")
    state["reusable"] = not state["reasons"]
    return state


# --------------------------------------------------------------------------- #
# Reading the notebook model (pure; unit-tested without a browser)
# --------------------------------------------------------------------------- #

_CAP = 4096
_OWN_CAP = 256 * 1024


def _mime_text(value: Any) -> str | None:
    """A mime value as text: nbformat stores multiline text as a list of strings."""
    if isinstance(value, list) and all(isinstance(x, str) for x in value):
        return "".join(value)
    return value if isinstance(value, str) else None


def _shrink(value: Any, cap: int = _CAP) -> Any:
    """Keep a JSON value if it is small; otherwise a marked head of its JSON text."""
    if isinstance(value, str):
        return value if len(value) <= cap else value[:cap] + f"...[+{len(value) - cap} chars]"
    text = json.dumps(value, default=str, sort_keys=True)
    if len(text) <= cap:
        return value
    return {"_truncated": len(text), "head": text[:cap]}


def trim_output(output: dict[str, Any]) -> dict[str, Any]:
    """A bounded copy of one nbformat output (the artifact keeps the model's evidence)."""
    kind = output.get("output_type")
    out: dict[str, Any] = {"output_type": kind}
    if kind in ("display_data", "execute_result"):
        # the probe's own tagged bundles (metadata.s4) carry its measurements: never truncate them
        own = isinstance((output.get("metadata") or {}).get("s4"), str)
        cap = _OWN_CAP if own else _CAP
        out["data"] = {
            mime: _shrink(_mime_text(v) if isinstance(v, list) else v, cap)
            for mime, v in (output.get("data") or {}).items()
        }
        out["metadata"] = _shrink(output.get("metadata") or {})
        if "execution_count" in output:
            out["execution_count"] = output["execution_count"]
    elif kind == "error":
        out["ename"] = _shrink(output.get("ename"))
        out["evalue"] = _shrink(output.get("evalue"))
        out["traceback"] = [_shrink(line, 2048) for line in (output.get("traceback") or [])[:24]]
    elif kind == "stream":
        out["name"] = output.get("name")
        out["text"] = _shrink(_mime_text(output.get("text")) or "")
    return out


def is_done(rec: dict[str, Any] | None) -> bool:
    """The cell's run settled (its command promise resolved or rejected): it was executed."""
    return bool(rec) and rec.get("state") in ("resolved", "rejected")


def emit_payload(outputs: list[dict[str, Any]] | None, tag: str) -> tuple[dict[str, Any] | None, str | None]:
    """The payload of the ``display_data`` output that kernel-side ``_s4_emit(tag)`` produced,
    and the channel it was read from (``application/json``, else the ``text/plain`` JSON).
    """
    for output in outputs or []:
        if output.get("output_type") != "display_data":
            continue
        if (output.get("metadata") or {}).get("s4") != tag:
            continue
        data = output.get("data") or {}
        as_json = data.get("application/json")
        if isinstance(as_json, dict):
            return as_json, "application/json"
        text = _mime_text(data.get("text/plain"))
        if text is not None:
            try:
                parsed = json.loads(text)
            except ValueError:
                continue
            if isinstance(parsed, dict):
                return parsed, "text/plain"
    return None, None


def error_output(outputs: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    return next((o for o in outputs or [] if o.get("output_type") == "error"), None)


def summarize_error(outputs: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    err = error_output(outputs)
    if err is None:
        return None
    return {
        "ename": err.get("ename"),
        "evalue": err.get("evalue"),
        "traceback_tail": _shrink("\n".join(str(x) for x in (err.get("traceback") or []))[-2048:], 2048),
    }


# --------------------------------------------------------------------------- #
# The judges (pure): kernel payload -> the sub-probe result stored in the artifact.
# Every judge maps a missing, unreadable or errored payload to None, never to a claim.
# --------------------------------------------------------------------------- #


def _is_bool(x: Any) -> bool:
    return isinstance(x, bool)


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _get(d: Any, *keys: str) -> Any:
    for k in keys:
        d = d.get(k) if isinstance(d, dict) else None
    return d


def judge_plr(setup: dict[str, Any] | None) -> dict[str, Any]:
    """The PLR version the kernel actually has, whether ``pylabrobot.visualizer3D`` exists in it
    (``find_spec``, no import), and whether it is the pin. ``at_pin`` prefers the build-info sha
    (exact) and falls back to the version prefix; ``None`` when neither was readable.
    """
    if not isinstance(setup, dict):
        return {"measured": False, "visualizer3d_present": None, "at_pin": None, "version": None,
                "source_sha": None, "pin_evidence": None}
    present = _get(setup, "find_spec", "pylabrobot.visualizer3D")
    version = setup.get("pylabrobot_version")
    sha = setup.get("plr_source_sha")
    if isinstance(sha, str) and sha:
        at_pin: bool | None = sha == PIN_SHA
        evidence = "sha"
    elif isinstance(version, str) and version:
        at_pin = version.startswith(PIN_VERSION_PREFIX)
        evidence = "version_only"
    else:
        at_pin, evidence = None, None
    return {
        "measured": _is_bool(present),
        "visualizer3d_present": present if _is_bool(present) else None,
        "at_pin": at_pin,
        "pin_evidence": evidence,
        "version": version,
        "dist_version": setup.get("pylabrobot_dist_version"),
        "source_sha": sha if isinstance(sha, str) else None,
        "build_id": setup.get("plr_build_id"),
        "websockets_dist_version": setup.get("websockets_dist_version"),
        "python_version": setup.get("python_version"),
        "platform": setup.get("platform"),
        "boot_stubs": setup.get("boot_stubs"),
        "perf_counter_resolution_s": setup.get("perf_counter_resolution_s"),
        "pylabrobot_file": setup.get("pylabrobot_file"),
    }


def _real_ok(rec: Any) -> bool | None:
    """An import measured as a REAL success (not merely present as a stub): True / False / None."""
    if not isinstance(rec, dict) or not _is_bool(rec.get("ok")):
        return None
    if rec["ok"]:
        return rec.get("stub_like") is False
    return False


def judge_imports(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Per-group results of the stub-free imports, with the two instrument controls
    (``json`` imports for real; a bare ``ModuleType`` reads as stub-like).
    """
    records = payload.get("records") if isinstance(payload, dict) else None
    controls = payload.get("controls") if isinstance(payload, dict) else None
    if not isinstance(records, dict):
        return {"measured": False, "records": None}
    real = {n: _real_ok(records.get(n)) for n in ALL_IMPORTS}
    measured = all(v is not None for v in real.values())

    def group(names: tuple[str, ...]) -> tuple[bool | None, list[str]]:
        failed = [n for n in names if real[n] is False]
        if any(real[n] is None for n in names):
            return None, failed
        return not failed, failed

    std_ok, std_failed = group(STDLIB_IMPORTS)
    ws_ok, ws_failed = group(WEBSOCKETS_IMPORTS)
    plr_ok, plr_failed = group(PLR_IMPORTS)
    pos = (controls or {}).get("positive_json")
    positive_ok = _real_ok(pos) is True
    stub_detector_ok = (controls or {}).get("bare_module_reads_stub_like") is True and (
        isinstance(pos, dict) and pos.get("stub_like") is False
    )
    return {
        "measured": measured,
        "stdlib_ok": std_ok,
        "stdlib_failures": std_failed,
        "websockets_ok": ws_ok,
        "websockets_failures": ws_failed,
        "visualizer3d_ok": plr_ok,
        "visualizer3d_failures": plr_failed,
        "positive_control_ok": positive_ok,
        "stub_detector_control_ok": stub_detector_ok,
        "info": {n: records.get(n) for n in INFO_IMPORTS},
        "records": records,
    }


def judge_hostname(payload: dict[str, Any] | None) -> dict[str, Any]:
    ok = payload.get("ok") if isinstance(payload, dict) else None
    return {
        "measured": _is_bool(ok),
        "ok": ok if _is_bool(ok) else None,
        "value": (payload or {}).get("value"),
        "error": (payload or {}).get("error"),
    }


def judge_negative_import(payload: dict[str, Any] | None, candidates: tuple[str, ...]) -> dict[str, Any]:
    """The D17 negative control: every stub-free import of a module absent from Pyodide must FAIL
    with an ImportError that names that module. ``failed_as_required`` is None (never True)
    unless every candidate was read; a candidate that imported has NOT failed as required.
    """
    cands = payload.get("candidates") if isinstance(payload, dict) else None
    if not isinstance(cands, dict) or not all(isinstance(cands.get(n), dict) for n in candidates):
        return {"measured": False, "failed_as_required": None, "candidates": cands}
    verdicts: dict[str, bool] = {}
    for name in candidates:
        rec = cands[name]
        err = rec.get("error") or {}
        named = name in str(err.get("name") or "") or name in str(err.get("message") or "")
        verdicts[name] = rec.get("ok") is False and err.get("type") in (
            "ModuleNotFoundError", "ImportError") and named
    return {
        "measured": True,
        "failed_as_required": bool(candidates) and all(verdicts.values()),
        "per_candidate": verdicts,
        "unexpected_success": [n for n in candidates if cands[n].get("ok") is True],
        "candidates": cands,
    }


def judge_loop(payload: dict[str, Any] | None) -> dict[str, Any]:
    """WebLoop's ``call_later`` and ``call_soon_threadsafe``. ``supported`` is False only when the
    attribute is missing or the call raised ``NotImplementedError``/``AttributeError``; any other
    error, or a timer that never fired within the wait, is None (inconclusive, not a "no").
    """
    if not isinstance(payload, dict):
        return {"measured": False, "call_later_supported": None, "call_soon_threadsafe_supported": None}
    errors = payload.get("errors") if isinstance(payload.get("errors"), dict) else {}

    def supported(has_key: str, fired_key: str, err_key: str) -> bool | None:
        if payload.get(has_key) is False:
            return False
        err = errors.get(err_key)
        if isinstance(err, dict):
            return False if err.get("type") in ("NotImplementedError", "AttributeError") else None
        fired = payload.get(fired_key)
        return True if fired is True else None

    later = supported("has_call_later", "call_later_fired", "call_later")
    soon = supported("has_call_soon_threadsafe", "soon_threadsafe_fired", "call_soon_threadsafe")
    cancel_control = None
    if later is True:
        cancel_control = payload.get("cancelled_fired") is False
    return {
        "measured": later is not None and soon is not None,
        "call_later_supported": later,
        "call_soon_threadsafe_supported": soon,
        "timer_cancel_control_ok": cancel_control,
        "ensure_future_ok": payload.get("ensure_future_ok"),
        "wait_for_times_out": payload.get("wait_for_times_out"),
        "loop_type": payload.get("loop_type"),
        "threads": payload.get("threads"),
        "elapsed_s": payload.get("elapsed_s"),
        "errors": errors,
    }


def _no_step_errors(payload: Any, *steps: str) -> bool:
    errs = payload.get("errors") if isinstance(payload, dict) else None
    return isinstance(errs, dict) and not any(s in errs for s in steps)


def judge_viewer(setup: dict[str, Any] | None, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Construction, ``start()`` without threads (each of ``Thread.start``, ``websockets.serve``
    and ``webbrowser.open`` patched to raise, with a control that the patches trip), and ``stop``.
    A raised step is None. ``start_without_threads`` is None unless the patch control held.
    """
    ready = isinstance(setup, dict) and setup.get("ready") is True
    if not ready or not isinstance(payload, dict):
        return {"measured": False, "setup_ready": ready, "construct_ok": None, "start_ok": None,
                "start_without_threads": None, "stop_ok": None, "patch_control_ok": None}
    control = payload.get("patch_control_all_raise")
    calls = payload.get("calls_during_start")
    construct = payload.get("construct_ok") if _no_step_errors(payload, "construct") else None
    start = payload.get("start_ok") if _no_step_errors(payload, "start") else None
    without_threads = None
    if start is True and control is True and isinstance(calls, dict):
        without_threads = all(v == 0 for v in calls.values()) and set(calls) == {
            "thread_start", "websockets_serve", "webbrowser_open"}
    return {
        "measured": construct is not None and start is not None,
        "setup_ready": True,
        "construct_ok": construct,
        "start_ok": start,
        "start_without_threads": without_threads,
        "stop_ok": payload.get("stop_ok") if _no_step_errors(payload, "stop") else None,
        "patch_control_ok": control if _is_bool(control) else None,
        "calls_during_start": calls,
        "loop_is_running_loop": payload.get("loop_is_running_loop"),
        "legacy_bytes": payload.get("legacy_bytes"),
        "walk_calls_in_start": payload.get("walk_calls_in_start"),
        "subscribed": payload.get("subscribed"),
        "subscribed_after_stop": payload.get("subscribed_after_stop"),
        "overrides": (setup or {}).get("overrides"),
        "errors": payload.get("errors"),
    }


def judge_roots(stock: dict[str, Any] | None, rebound: dict[str, Any] | None) -> dict[str, Any]:
    """Both ``PACKAGE_ROOT``s as resolved in the kernel, and what the rebind did."""
    s_ok = isinstance(stock, dict) and _no_step_errors(stock, "roots") and isinstance(stock.get("root"), str)
    r_ok = (
        isinstance(rebound, dict)
        and _no_step_errors(rebound, "rebind")
        and isinstance(rebound.get("root_after"), str)
    )
    return {
        "measured": bool(s_ok and r_ok),
        "stock": {
            "measured": s_ok,
            "root": (stock or {}).get("root"),
            "in_plr_package": (stock or {}).get("in_plr_package"),
            "in_site_packages": (stock or {}).get("in_site_packages"),
            "derived_from_server_file": (stock or {}).get("derived_from_server_file"),
            "glb_count": (stock or {}).get("glb_count"),
            "glb_walk_seconds": (stock or {}).get("glb_walk_seconds"),
            "dirs_walked": (stock or {}).get("dirs_walked"),
            "server_file": (stock or {}).get("server_file"),
        },
        "rebound": {
            "measured": r_ok,
            "root": (rebound or {}).get("root_after"),
            "empty": ((rebound or {}).get("listing") == []) if r_ok else None,
            "exists": (rebound or {}).get("exists"),
            "differs_from_stock": (rebound or {}).get("differs_from_stock"),
            "idempotent": (rebound or {}).get("idempotent"),
            "root_before": (rebound or {}).get("root_before"),
        },
    }


def judge_scene(stock: dict[str, Any] | None, rebound: dict[str, Any] | None) -> dict[str, Any]:
    """The fixture deck's first ``scene`` message (the REAL inherited ``_handler``, rebound root),
    its ``mesh`` models on both roots, the hello / ``wait_for_browser`` path and the loop-driven
    rebuild after ``assign_child_resource``.
    """
    events = (rebound or {}).get("events")
    first_bytes = (rebound or {}).get("first_message_bytes")
    handler_ok = _no_step_errors(rebound, "handler")
    flush = (rebound or {}).get("flush") if _no_step_errors(rebound, "flush") else None
    flush_ok = None
    if isinstance(flush, dict) and isinstance(flush.get("events"), list):
        e0, e1 = flush.get("epoch_before"), flush.get("epoch_after")
        flush_ok = (
            flush["events"] == ["scene", "state"]
            and flush.get("rebuilds") == 1
            and _is_num(e0) and _is_num(e1) and e1 == e0 + 1
        )
    measured = (
        handler_ok
        and isinstance(events, list)
        and events[:2] == ["scene", "state"]
        and isinstance(first_bytes, int)
        and first_bytes > 0
    )
    return {
        "measured": bool(measured),
        "first_scene_message_bytes": first_bytes if measured else None,
        "first_scene_message_chars": (rebound or {}).get("first_message_chars"),
        "first_state_message_bytes": (rebound or {}).get("second_message_bytes"),
        "event_order": events,
        "n_models": (rebound or {}).get("n_models"),
        "mesh_models_rebound": (rebound or {}).get("n_mesh_models") if measured else None,
        "mesh_substring_count_rebound": (rebound or {}).get("mesh_substring_count"),
        "mesh_models_stock": (stock or {}).get("n_mesh_models") if _no_step_errors(stock, "scene") else None,
        "mesh_model_names_stock": (stock or {}).get("mesh_model_names"),
        "stock_scene_message_bytes": (stock or {}).get("scene_message_bytes"),
        "handler_matches_encode": (rebound or {}).get("scene_message_equals_encode"),
        "hello_seen": (rebound or {}).get("hello_seen") if _no_step_errors(rebound, "hello") else None,
        "wait_for_browser_ok": (rebound or {}).get("wait_for_browser_ok")
        if _no_step_errors(rebound, "hello") else None,
        "flush": flush,
        "flush_ok": flush_ok,
        "handler_task_done": (rebound or {}).get("handler_task_done"),
        "subscribed_after_stop": (rebound or {}).get("subscribed_after_stop"),
    }


def _walk_on_root(found: dict[str, Any] | None, log: Any, root: Any) -> bool | None:
    """Did the timed walk run over ``root``? True if a walk on it was logged; False if walks were
    logged but none on it; None if there is nothing to read."""
    if found is not None and isinstance(root, str) and root:
        return True
    if isinstance(log, list) and log:
        return False
    return None


def judge_walk(stock: dict[str, Any] | None, rebound: dict[str, Any] | None, roots: dict[str, Any]) -> dict[str, Any]:
    """The first ``_models_on_disk`` walk on each root, taken from the instrument wrapper around
    the inherited scene build (a first, cache-missing call on the root the viewer used). The
    rebound walk is valid only if it ran over the rebound root and was a cache miss.
    """

    def first(log: Any, root: Any) -> dict[str, Any] | None:
        if not isinstance(log, list) or not isinstance(root, str):
            return None
        return next((w for w in log if isinstance(w, dict) and w.get("root") == root), None)

    s_root = _get(roots, "stock", "root")
    r_root = _get(roots, "rebound", "root")
    s = first((stock or {}).get("walk_log"), s_root)
    r = first((rebound or {}).get("walk_log"), r_root)
    return {
        "measured": bool(s and r and s.get("cache_miss") is True and r.get("cache_miss") is True),
        "stock": {"seconds": (s or {}).get("seconds"), "root": s_root, "cache_miss": (s or {}).get("cache_miss"),
                  "n_models": (s or {}).get("n_models")},
        "rebound": {"seconds": (r or {}).get("seconds"), "root": r_root, "cache_miss": (r or {}).get("cache_miss"),
                    "n_models": (r or {}).get("n_models"),
                    "on_rebound_root": _walk_on_root(r, (rebound or {}).get("walk_log"), r_root)},
        "walks_in_start": (rebound or {}).get("walk_calls_in_start"),
        "resolution_s": None,
    }


def judge_seeded(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Positive control for the ``mesh`` reader: a ``<model>.glb`` seeded into a temporary root
    makes exactly that model carry a ``mesh`` (so a reading of zero on the rebound root means
    something), and the temporary root restores the previous ``PACKAGE_ROOT``.
    """
    if not isinstance(payload, dict) or not _no_step_errors(payload, "seeded"):
        return {"measured": False, "mesh_seen": None, "model": None}
    seen = payload.get("mesh_seen")
    return {
        "measured": _is_bool(seen),
        "mesh_seen": seen if _is_bool(seen) else None,
        "model": payload.get("model"),
        "only_the_seeded_model": payload.get("only_the_seeded_model"),
        "mesh_without_seed": payload.get("mesh_without_seed"),
        "root_restored": payload.get("root_restored"),
    }


# --------------------------------------------------------------------------- #
# Derivations (pure): the sub-probe judgments -> the flat fields the sidecar reads
# --------------------------------------------------------------------------- #


def _viewer_required(imp: dict[str, Any], flags: dict[str, Any]) -> bool:
    """The viewer-path measurements are required only when they can exist: the stdlib imports
    are fine, the loop has ``call_later`` and ``pylabrobot.visualizer3D`` imported.
    """
    return (
        not imp.get("stdlib_failures")
        and imp.get("stdlib_ok") is True
        and flags["gethostname_ok"] is True
        and flags["call_later_supported"] is not False
        and flags["visualizer3d_import_ok"] is True
    )


def evaluate_validity(art: dict[str, Any], flags: dict[str, Any]) -> dict[str, bool]:
    """Named checks whose conjunction is ``measurement_valid``, in the priority order that
    ``invalid_reason`` reports. Any ``error`` finding, an absent ``visualizer3D``, a PLR that is
    not the pin, an uncontrolled or unmeasured verdict, a cell that never settled, a hit deadline,
    an aborted boot or a negative control that did not fail as required makes the run ``invalid``:
    it never satisfies a branch outcome.
    """
    boot = art.get("boot") or {}
    imp = art.get("imports") or {}
    plr = art.get("plr") or {}
    loop = art.get("loop") or {}
    checks: dict[str, bool] = {
        "no_error_findings": art.get("error") is None and not art.get("sub_errors"),
        "kernel_ready": art.get("kernel_ready") is True,
        "boot_ok": boot.get("warmup_done") is True and boot.get("warmup_error") is None,
        "prelude_ok": (art.get("prelude") or {}).get("ok") is True,
        "visualizer3d_present": plr.get("visualizer3d_present") is True,
        "plr_at_pin": plr.get("at_pin") is True,
        "not_aborted": art.get("aborted") is None,
        "all_cells_done": art.get("all_cells_done") is True,
        "deadline_not_hit": art.get("deadline_hit") is False,
        "imports_measured": imp.get("measured") is True,
        "import_positive_control": imp.get("positive_control_ok") is True,
        "stub_detector_control": imp.get("stub_detector_control_ok") is True,
        "hostname_measured": flags["gethostname_ok"] is not None,
        "negative_control_failed_as_required": flags["negative_control_failed_as_required"] is True,
        "loop_measured": loop.get("measured") is True,
        "timer_cancel_control": flags["call_later_supported"] is not True
        or loop.get("timer_cancel_control_ok") is True,
    }
    if _viewer_required(imp, flags):
        viewer, scene, walk = art.get("viewer") or {}, art.get("scene") or {}, art.get("walk") or {}
        roots, seeded = art.get("roots") or {}, art.get("seeded_control") or {}
        checks.update(
            {
                "viewer_measured": viewer.get("measured") is True,
                "patch_control_ok": viewer.get("patch_control_ok") is True,
                "start_without_threads_measured": viewer.get("start_without_threads") is not None,
                "scene_measured": scene.get("measured") is True,
                "flush_measured": scene.get("flush_ok") is not None,
                "roots_measured": roots.get("measured") is True,
                "walk_measured": walk.get("measured") is True and _get(walk, "rebound", "on_rebound_root") is True,
                "mesh_counts_measured": _is_num(scene.get("mesh_models_rebound"))
                and _is_num(scene.get("mesh_models_stock")),
                "seeded_control_sees_mesh": seeded.get("mesh_seen") is True,
                "rebind_effective": _get(roots, "rebound", "differs_from_stock") is True
                and _get(roots, "rebound", "empty") is True,
            }
        )
    return checks


def derive_branch(f: dict[str, Any]) -> str:
    """D1 S4 branch from VALID measured fields. S4-C dominates (a stop: the design cannot work
    even with stubs); then S4-B (a stdlib import or ``gethostname`` fails); then anything the
    design-as-written needs that failed and no D1 branch names (UNMAPPED); then MESH (everything
    works but the rebind did not remove every ``mesh``: D11's premise is false); else S4-A.
    """
    if f["call_later_supported"] is False:
        return "S4-C"
    if f["stdlib_imports_ok"] is False or f["gethostname_ok"] is False:
        return "S4-B"
    yes = (
        f["websockets_imports_ok"], f["visualizer3d_import_ok"], f["construct_ok"], f["start_ok"],
        f["start_without_threads"], f["call_soon_threadsafe_supported"], f["scene_flush_ok"],
        f["first_scene_message_bytes"] is not None,
    )
    if not all(v is True for v in yes):
        return "UNMAPPED"
    if f["mesh_models_rebound"] != 0:
        return "MESH"
    return "S4-A"


def derive_outcome_fields(art: dict[str, Any]) -> dict[str, Any]:
    """The flat scalar fields the sidecar's ``[outcomes]`` conditions read, plus the
    ``details`` (validity checks, per-axis verdicts).
    """
    plr = art.get("plr") or {}
    imp = art.get("imports") or {}
    host = art.get("hostname") or {}
    loop = art.get("loop") or {}
    viewer = art.get("viewer") or {}
    roots = art.get("roots") or {}
    scene = art.get("scene") or {}
    walk = art.get("walk") or {}
    neg = (art.get("negative_control") or {}).get("failed_as_required")
    stdlib_failures = list(imp.get("stdlib_failures") or [])
    gethostname_ok = host.get("ok")
    stubs = stdlib_failures + (["socket.gethostname"] if gethostname_ok is False else [])
    flags = {
        "gethostname_ok": gethostname_ok,
        "call_later_supported": loop.get("call_later_supported"),
        "visualizer3d_import_ok": imp.get("visualizer3d_ok"),
        "negative_control_failed_as_required": neg,
    }
    validity = evaluate_validity(art, flags)
    valid = all(validity.values())
    invalid_reason = "none" if valid else next(k for k, v in validity.items() if not v)
    flat: dict[str, Any] = {
        "all_units_complete": True,
        "n_units": len(UNITS),
        "n_error_units": 1 if (art.get("error") is not None) else 0,
        "measurement_valid": valid,
        "invalid_reason": invalid_reason,
        "kernel_ready": art.get("kernel_ready"),
        "aborted": art.get("aborted") or "none",
        "plr_version": plr.get("version"),
        "plr_source_sha": plr.get("source_sha"),
        "plr_at_pin": plr.get("at_pin"),
        "visualizer3d_present": plr.get("visualizer3d_present"),
        "stdlib_imports_ok": imp.get("stdlib_ok"),
        "gethostname_ok": gethostname_ok,
        "stubs_required": (",".join(stubs) if stubs else "none")
        if (imp.get("measured") is True and gethostname_ok is not None) else "unmeasured",
        "websockets_imports_ok": imp.get("websockets_ok"),
        "visualizer3d_import_ok": imp.get("visualizer3d_ok"),
        "construct_ok": viewer.get("construct_ok"),
        "start_ok": viewer.get("start_ok"),
        "start_without_threads": viewer.get("start_without_threads"),
        "call_later_supported": loop.get("call_later_supported"),
        "call_soon_threadsafe_supported": loop.get("call_soon_threadsafe_supported"),
        "scene_flush_ok": scene.get("flush_ok"),
        "first_scene_message_bytes": scene.get("first_scene_message_bytes"),
        "stock_root": _get(roots, "stock", "root"),
        "stock_root_in_plr_package": _get(roots, "stock", "in_plr_package"),
        "stock_glb_count": _get(roots, "stock", "glb_count"),
        "rebound_root": _get(roots, "rebound", "root"),
        "rebound_root_empty": _get(roots, "rebound", "empty"),
        "rebound_differs_from_stock": _get(roots, "rebound", "differs_from_stock"),
        "rebind_idempotent": _get(roots, "rebound", "idempotent"),
        "mesh_models_stock": scene.get("mesh_models_stock"),
        "mesh_models_rebound": scene.get("mesh_models_rebound"),
        "walk_stock_seconds": _get(walk, "stock", "seconds"),
        "walk_rebound_seconds": _get(walk, "rebound", "seconds"),
        "walk_on_rebound_root": _get(walk, "rebound", "on_rebound_root"),
        "negative_control_failed_as_required": neg,
        "d1_branch": None,
    }
    if valid:
        flat["d1_branch"] = derive_branch(flat)
    details = {"validity_checks": validity, "stubs_required": stubs}
    return {"flat": flat, "details": details}


# --------------------------------------------------------------------------- #
# The in-page probe library (installed as window.__s4; read via page.evaluate)
# --------------------------------------------------------------------------- #

S4_JS = r"""
(() => {
  if (window.__s4) return true;
  const S = {};
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const raf2 = () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
  S.settle = async (ms) => { await raf2(); await sleep(ms === undefined ? 350 : ms); await raf2(); return true; };
  S.shell = () => window.jupyterapp.shell;
  S.nbPanel = () => {
    for (const w of S.shell().widgets('main')) {
      if (w.node && w.node.classList.contains('jp-NotebookPanel') && w.content) return w;
    }
    return null;
  };
  S.cellCount = () => { const nb = S.nbPanel(); return nb ? nb.content.widgets.length : null; };
  S.kernelStatus = () => {
    const nb = S.nbPanel();
    return nb && nb.sessionContext && nb.sessionContext.session && nb.sessionContext.session.kernel
      ? nb.sessionContext.session.kernel.status : null;
  };
  S.runs = {};
  S._dispatch = (key) => {
    S.runs[key] = {state: 'pending', error: null, value: null};
    let pr;
    try { pr = window.jupyterapp.commands.execute('notebook:run-cell'); }
    catch (e) { S.runs[key] = {state: 'rejected', error: String(e), value: null}; return true; }
    Promise.resolve(pr).then(
      (v) => { S.runs[key] = {state: 'resolved', error: null, value: v === undefined ? null : v}; },
      (e) => { S.runs[key] = {state: 'rejected', error: String(e), value: null}; });
    return true;
  };
  S.runCell = (i, key) => {
    const nb = S.nbPanel().content;
    nb.deselectAll(); nb.activeCellIndex = i;
    return S._dispatch(key);
  };
  S.runState = (key) => (S.runs[key] ? S.runs[key].state : null);
  S.runInfo = (key) => S.runs[key] || null;
  S.cellRead = (i) => {
    const nb = S.nbPanel();
    const cells = nb && nb.content && nb.content.model && nb.content.model.cells;
    if (!cells) return null;
    const cell = cells.get ? cells.get(i) : cells[i];
    if (!cell) return null;
    const j = typeof cell.toJSON === 'function' ? cell.toJSON() : {};
    return {
      index: i,
      execution_count: j.execution_count === undefined ? null : j.execution_count,
      execution_state: cell.executionState === undefined ? null : cell.executionState,
      outputs: j.outputs || [],
    };
  };
  window.__s4 = S;
  return true;
})()
"""

SAVE_JS = """async (a) => {
    try {
        await window.jupyterapp.serviceManager.contents.save(a.path, {
            type: "notebook", format: "json", content: a.content});
        return {ok: true};
    } catch (e) { return {ok: false, error: String(e)}; }
}"""


# --------------------------------------------------------------------------- #
# Browser session (real), the page-backed kernel driver, and the probe context
# --------------------------------------------------------------------------- #


class BrowserSession:
    """Served dist + Playwright + one full-Chromium page. ``close()`` is the teardown's
    step 2: browser closed, Playwright stopped, server shut down; every failure is logged
    with ``logging.error`` and never changes the artifact's keys.
    """

    def __init__(self, args: argparse.Namespace, env: InputEnv) -> None:
        from playwright.sync_api import sync_playwright

        rs = repl_smoke()
        self.pageerrors: list[str] = []
        self.prefix = rs._normalize_base_path(args.base_path)
        self._stack = contextlib.ExitStack()
        self._pw: Any = None
        self._browser: Any = None
        try:
            served = self._stack.enter_context(
                rs.ServedDir(Path(args.dist), args.base_path, coi=False)
            )
            self.port = served.port
            self.origin = f"http://127.0.0.1:{served.port}"
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                executable_path=env.chrome_path,
                headless=True,
                args=rs.chromium_launch_args(offline=False),
            )
            context = self._browser.new_context(viewport=dict(VIEWPORT))
            # D16 persistence gate: the first-save modal must not block the harness.
            context.add_init_script(
                'window.localStorage.setItem("praxis-repl-persistence-ack", "browser-only");'
            )
            self.page = context.new_page()
            self.page.on("pageerror", lambda exc: self.pageerrors.append(str(exc)))
        except BaseException:
            self.close()
            raise

    @property
    def lab_url(self) -> str:
        return f"{self.origin}{self.prefix}lab/index.html"

    def close(self) -> None:
        for label, fn in (
            ("browser.close", lambda: self._browser and self._browser.close()),
            ("playwright.stop", lambda: self._pw and self._pw.stop()),
            ("served dir", self._stack.close),
        ):
            try:
                fn()
            except Exception:
                LOG.exception("teardown step failed: %s", label)


@dataclasses.dataclass
class ProbeCtx:
    unit: str
    args: argparse.Namespace
    env: InputEnv
    fixture: dict[str, Any]
    deadline: float  # time.monotonic() value after which no new work is started


class PageKernelDriver:
    """The kernel seam, backed by the real page. ``run_viewer_probe`` only ever talks to this
    interface (``open``, ``wait_idle``, ``run_cell``), so the tests can put a fake kernel behind
    it. Results are read from the notebook model (``window.__s4.cellRead``).
    """

    def __init__(self, sess: Any, ctx: ProbeCtx) -> None:
        self.sess = sess
        self.ctx = ctx
        self.page = sess.page

    @property
    def pageerrors(self) -> list[str]:
        return list(getattr(self.sess, "pageerrors", []) or [])

    def _ev(self, expr: str, arg: Any = None) -> Any:
        return self.page.evaluate(f"async (a) => window.__s4.{expr}", arg)

    def open(self) -> None:
        page = self.page
        page.goto(self.sess.lab_url, wait_until="load", timeout=NAV_TIMEOUT_MS)
        page.wait_for_function(
            "() => !!window.jupyterapp && !!window.jupyterapp.shell", timeout=NAV_TIMEOUT_MS
        )
        page.evaluate(S4_JS)
        saved = page.evaluate(SAVE_JS, {"path": NB_PATH, "content": self.ctx.fixture})
        if not saved.get("ok"):
            raise RuntimeError(f"could not seed the S4 notebook: {saved.get('error')!r}")
        repl_smoke()._open_existing_notebook(page, NB_PATH, timeout_ms=NAV_TIMEOUT_MS)
        page.wait_for_function(
            "(n) => { const w = window.__s4.nbPanel(); return !!w && w.content.widgets.length >= n; }",
            arg=len(CELL_NAMES),
            timeout=NAV_TIMEOUT_MS,
        )
        self._ev("settle(800)")

    def wait_idle(self, timeout_s: float) -> bool:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        try:
            self.page.wait_for_function(
                "() => window.__s4.kernelStatus() === 'idle'", timeout=timeout_s * 1000
            )
            return True
        except PlaywrightTimeoutError:
            return False

    def _wait_settled(self, key: str, timeout_s: float) -> bool:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        try:
            self.page.wait_for_function(
                "(k) => { const s = window.__s4.runState(k); return s !== null && s !== 'pending'; }",
                arg=key,
                timeout=timeout_s * 1000,
            )
            return True
        except PlaywrightTimeoutError:
            return False

    def _record(self, name: str, key: str, started: float) -> dict[str, Any]:
        info = self._ev("runInfo(a)", key) or {"state": "pending", "error": None}
        read = self._ev("cellRead(a)", CELL_INDEX[name]) or {}
        return {
            "name": name,
            "index": CELL_INDEX[name],
            "state": info.get("state"),
            "error": info.get("error"),
            "execution_count": read.get("execution_count"),
            "execution_state": read.get("execution_state"),
            "outputs": [trim_output(o) for o in (read.get("outputs") or [])],
            "seconds": round(time.monotonic() - started, 3),
        }

    def run_cell(self, name: str, timeout_s: float) -> dict[str, Any]:
        started = time.monotonic()
        key = f"cell:{name}"
        self._ev("runCell(a.i, a.k)", {"i": CELL_INDEX[name], "k": key})
        self._wait_settled(key, timeout_s)
        self._ev("settle(150)")
        return self._record(name, key, started)


#: Replaceable seams (the plumbing tests substitute stubs; nothing in production does).
def open_session(unit: str, args: argparse.Namespace, env: InputEnv) -> Any:
    return BrowserSession(args, env)


SESSION_FACTORY: Callable[[str, argparse.Namespace, InputEnv], Any] = open_session
KERNEL_DRIVER_FACTORY: Callable[[Any, ProbeCtx], Any] = PageKernelDriver


# --------------------------------------------------------------------------- #
# The probe: orchestration over the kernel seam
# --------------------------------------------------------------------------- #


def _tail(text: str, limit: int = 4096) -> str:
    raw = text.encode("utf-8", "replace")
    return raw[-limit:].decode("utf-8", "replace")


def collect_sub_probes(
    registry: dict[str, Callable[[dict[str, Any]], Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Run each sub-probe in order, each seeing the earlier results. A sub-probe that RAISES
    is caught: its result is None and its ``{type, message, traceback_tail}`` goes into
    ``sub_errors`` (the unit lifts the first into the artifact's ``error`` finding, so the
    unit still completes and the finding counts toward ``[outcomes]``). Later sub-probes still
    run: their evidence is kept, but the run is ``invalid``.
    """
    results: dict[str, Any] = {}
    errors: dict[str, dict[str, Any]] = {}
    for name, fn in registry.items():
        try:
            results[name] = fn(results)
        except Exception as exc:
            LOG.exception("sub-probe %s raised", name)
            results[name] = None
            errors[name] = {
                "type": type(exc).__name__,
                "message": str(exc)[:2000],
                "traceback_tail": _tail(traceback.format_exc()),
            }
    return results, errors


class ProbeRun:
    """One pass over the probe cells in the ONE kernel, recording every cell."""

    def __init__(self, kd: Any, deadline: float, neg_modules: tuple[str, ...] = NEG_ABSENT_MODULES) -> None:
        self.kd = kd
        self.deadline = deadline
        self.neg_modules = neg_modules
        self.cells: dict[str, dict[str, Any]] = {}
        self.skipped: dict[str, str] = {}
        self.aborted: str | None = None
        self.deadline_hit = False

    def _budget(self, cap_s: float) -> float:
        return min(cap_s, self.deadline - time.monotonic())

    def _skipped(self, name: str, reason: str) -> dict[str, Any]:
        return {
            "name": name, "index": CELL_INDEX.get(name), "state": "skipped", "error": reason,
            "execution_count": None, "execution_state": None, "outputs": [], "seconds": 0.0,
        }

    def _admit(self, cap_s: float) -> float | None:
        """Seconds allowed for the next step, or None if nothing may start."""
        if self.aborted is not None:
            return None
        left = self._budget(cap_s)
        if left <= 1.0:
            self.deadline_hit = True
            self.aborted = self.aborted or "deadline"
            return None
        return left

    def cell(self, name: str, cap_s: float | None = None) -> dict[str, Any]:
        cap = cap_s if cap_s is not None else (
            HEAVY_CELL_TIMEOUT_S if name in HEAVY_CELLS else CELL_TIMEOUT_S)
        left = self._admit(cap)
        if left is None:
            rec = self._skipped(name, self.aborted or "aborted")
        else:
            rec = self.kd.run_cell(name, left)
            if not is_done(rec):
                self.aborted = f"cell_timeout:{name}"
        self.cells[name] = rec
        return rec

    def payload(self, name: str, tag: str) -> dict[str, Any] | None:
        rec = self.cells.get(name)
        return emit_payload(rec.get("outputs"), tag)[0] if rec else None

    def skip(self, name: str, reason: str) -> None:
        self.skipped[name] = reason

    # ---- sub-probes -------------------------------------------------------- #

    def sub_plr(self, _r: dict[str, Any]) -> dict[str, Any]:
        return judge_plr(self.payload("setup", "setup"))

    def sub_imports(self, _r: dict[str, Any]) -> dict[str, Any]:
        self.cell("imports")
        return judge_imports(self.payload("imports", "imports"))

    def sub_hostname(self, _r: dict[str, Any]) -> dict[str, Any]:
        self.cell("hostname")
        return judge_hostname(self.payload("hostname", "hostname"))

    def sub_negative(self, _r: dict[str, Any]) -> dict[str, Any]:
        self.cell("neg_import")
        return judge_negative_import(self.payload("neg_import", "neg_import"), self.neg_modules)

    def sub_loop(self, _r: dict[str, Any]) -> dict[str, Any]:
        self.cell("loop")
        return judge_loop(self.payload("loop", "loop"))

    def _viewer_reachable(self, results: dict[str, Any]) -> bool:
        imp = results.get("imports") or {}
        return imp.get("visualizer3d_ok") is True and not imp.get("stdlib_failures")

    def sub_viewer(self, results: dict[str, Any]) -> dict[str, Any]:
        if not self._viewer_reachable(results):
            for name in VIEWER_CELLS:
                self.skip(name, "imports_not_ok")
            return judge_viewer(None, None)
        self.cell("viewer_setup")
        setup = self.payload("viewer_setup", "viewer_setup")
        if not (isinstance(setup, dict) and setup.get("ready") is True):
            for name in VIEWER_CELLS[1:]:
                self.skip(name, "viewer_setup_not_ready")
            return judge_viewer(setup, None)
        self.cell("viewer")
        return judge_viewer(setup, self.payload("viewer", "viewer"))

    def sub_roots(self, results: dict[str, Any]) -> dict[str, Any]:
        if "roots_stock" in self.skipped or not self._viewer_reachable(results):
            self.skip("roots_stock", self.skipped.get("roots_stock", "imports_not_ok"))
            self.skip("roots_rebound", self.skipped.get("roots_rebound", "imports_not_ok"))
            return judge_roots(None, None)
        self.cell("roots_stock")
        self.cell("roots_rebound")
        return judge_roots(self.payload("roots_stock", "roots_stock"), self.payload("roots_rebound", "roots_rebound"))

    def sub_scene(self, _r: dict[str, Any]) -> dict[str, Any]:
        return judge_scene(self.payload("roots_stock", "roots_stock"), self.payload("roots_rebound", "roots_rebound"))

    def sub_walk(self, results: dict[str, Any]) -> dict[str, Any]:
        out = judge_walk(self.payload("roots_stock", "roots_stock"), self.payload("roots_rebound", "roots_rebound"),
                         results.get("roots") or {})
        out["resolution_s"] = (results.get("plr") or {}).get("perf_counter_resolution_s")
        return out

    def sub_seeded(self, results: dict[str, Any]) -> dict[str, Any]:
        if "seeded" in self.skipped or "roots_stock" in self.skipped or not self._viewer_reachable(results):
            self.skip("seeded", self.skipped.get("seeded", "imports_not_ok"))
            self.skip("restore", self.skipped.get("restore", "imports_not_ok"))
            return judge_seeded(None)
        self.cell("seeded")
        self.cell("restore")
        return judge_seeded(self.payload("seeded", "seeded"))


def run_viewer_probe(kd: Any, deadline: float, neg_modules: tuple[str, ...] = NEG_ABSENT_MODULES) -> dict[str, Any]:
    """The whole probe over a kernel driver. Every pre-registered field is returned (None
    where unmeasured); ``aborted`` names why the probe stopped early, if it did.
    """
    run = ProbeRun(kd, deadline, neg_modules)
    fields: dict[str, Any] = dict.fromkeys(UNIT_BY_NAME[UNIT_NAME].required)
    fields.update(cells=run.cells, sub_errors={}, aborted=None, deadline_hit=False, all_cells_done=False,
                  skipped=run.skipped)
    t0 = time.monotonic()
    kd.open()
    ready = kd.wait_idle(max(1.0, min(IDLE_TIMEOUT_S, deadline - time.monotonic())))
    idle_s = round(time.monotonic() - t0, 3)
    fields["kernel_ready"] = ready
    boot: dict[str, Any] = {"kernel_idle_seconds": idle_s, "warmup_done": False, "warmup_error": None, "warmup_seconds": None}
    fields["boot"] = boot
    fields["prelude"] = {"ok": False, "payload": None, "channel": None}
    if not ready:
        fields["aborted"] = "kernel_not_idle"
        return fields
    warm = run.cell("warm", WARMUP_TIMEOUT_S)
    boot.update(warmup_done=is_done(warm), warmup_error=summarize_error(warm.get("outputs")), warmup_seconds=warm.get("seconds"))
    if not is_done(warm) or boot["warmup_error"] is not None:
        run.aborted = run.aborted or "warmup_failed"
    setup = run.cell("setup")
    payload, channel = emit_payload(setup.get("outputs"), "setup")
    fields["prelude"] = {
        "ok": is_done(setup) and payload is not None and error_output(setup.get("outputs")) is None,
        "payload": payload, "channel": channel,
    }
    if not fields["prelude"]["ok"]:
        run.aborted = run.aborted or "prelude_failed"
    plr = judge_plr(payload)
    if run.aborted is None and plr["visualizer3d_present"] is False:
        # FAIL FAST (task C1 / the dist requirement): a dist not built at the pin, e.g. PLR 0.2.2
        run.aborted = "visualizer3d_absent"
    registry = {
        "plr": run.sub_plr, "imports": run.sub_imports, "hostname": run.sub_hostname,
        "negative_control": run.sub_negative, "loop": run.sub_loop, "viewer": run.sub_viewer,
        "roots": run.sub_roots, "scene": run.sub_scene, "walk": run.sub_walk,
        "seeded_control": run.sub_seeded,
    }
    results, sub_errors = collect_sub_probes(registry)
    fields.update(results)
    fields["plr"] = plr if results.get("plr") is None else results["plr"]
    fields["sub_errors"] = sub_errors
    fields["aborted"] = run.aborted
    fields["deadline_hit"] = run.deadline_hit
    fields["all_cells_done"] = bool(run.cells) and all(is_done(r) for r in run.cells.values())
    return fields


def probe_viewer3d(sess: Any, ctx: ProbeCtx) -> dict[str, Any]:
    return run_viewer_probe(KERNEL_DRIVER_FACTORY(sess, ctx), ctx.deadline)


PROBES: dict[str, Callable[[Any, ProbeCtx], dict[str, Any]]] = {UNIT_NAME: probe_viewer3d}


# --------------------------------------------------------------------------- #
# Unit mode: the D17 per-unit sequence
# --------------------------------------------------------------------------- #


def _flush_all() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (OSError, ValueError):
            pass
    for handler in logging.getLogger().handlers:
        try:
            handler.flush()
        except Exception:  # pragma: no cover
            pass


def _sleep_forever_until_killed() -> None:  # pragma: no cover - the watchdog exits the process
    while True:
        time.sleep(1)


def run_unit_mode(args: argparse.Namespace, *, unit_timeout_s: float = UNIT_TIMEOUT_S) -> None:
    """Never returns: ends in ``os._exit`` (stamp.exit, or 124 from the watchdog)."""
    spec = UNIT_BY_NAME[args.unit]
    token = unit_runner.ensure_token()  # may re-exec; a no-op under run_unit
    out_dir = Path(args.out_dir)
    paths = unit_paths(out_dir, spec.name)
    paths["artifact"].parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    deadline = time.monotonic() + unit_timeout_s * DEADLINE_FRACTION

    def on_expire() -> None:
        _rm(paths["artifact"])
        marker = {
            "unit": spec.name, "budget_s": unit_timeout_s, "started": started, "expired": time.time(),
        }
        try:
            unit_runner.write_atomic(paths["timeout"], json.dumps(marker).encode())
        except OSError:
            pass
        unit_runner.emit_line(json.dumps({"unit": spec.name, "status": "timeout", "budget_s": unit_timeout_s}))

    watchdog = unit_runner.Watchdog(unit_timeout_s, on_expire)  # first act after ensure_token
    for key in ("stamp", "artifact", "timeout"):  # stamp first: never a stamp without its artifact
        _rm(paths[key])

    error: dict[str, Any] | None = None
    fields: dict[str, Any] = {}
    session: Any = None
    env: InputEnv | None = None
    try:
        env = build_env(args)
        ctx = ProbeCtx(spec.name, args, env, build_fixture(), deadline)
        session = SESSION_FACTORY(spec.name, args, env)
        fields = PROBES[spec.name](session, ctx)
    except Exception as exc:  # a raised probe is an `error` finding, and the unit still completes
        LOG.exception("probe %s raised", spec.name)
        error = {
            "type": type(exc).__name__, "message": str(exc)[:2000],
            "traceback_tail": _tail(traceback.format_exc()),
        }
    if error is None and fields.get("sub_errors"):
        # a raised SUB-probe is an `error` finding in the one artifact (D17): the first one
        first = next(iter(fields["sub_errors"]))
        error = {"sub_probe": first, **fields["sub_errors"][first]}
    if env is None:  # build_env itself failed; the stamp still needs inputs (best effort)
        env = InputEnv("", "", "", "", "", "", "", getattr(args, "base_path", "/"))

    missing = [f for f in spec.required if f not in fields]
    artifact: dict[str, Any] = {"unit": spec.name, "error": error}
    for name in spec.required:
        artifact[name] = fields.get(name)
    for name, value in fields.items():
        artifact.setdefault(name, value)
    artifact.update(
        {
            "missing_fields": missing if error is None else [],
            "pageerrors": list(getattr(session, "pageerrors", []) or []),
            "chrome_path": env.chrome_path, "chrome_version": env.chrome_version,
            "viewport": dict(VIEWPORT), "started": started, "finished": time.time(),
        }
    )
    data = json.dumps(artifact, indent=1, sort_keys=True, default=str).encode()
    if not watchdog.write_result(lambda: unit_runner.write_atomic(paths["artifact"], data)):
        _sleep_forever_until_killed()

    # Bounded teardown (D16, C9-1): close browser + Playwright, kill any residual descendant.
    if session is not None:
        try:
            session.close()
        except Exception:
            LOG.exception("session close raised")
    try:
        survivors = unit_runner.kill_tree(os.getpid(), token)
        if survivors:
            LOG.error("descendants survived kill_tree: %s", survivors)
    except Exception:
        LOG.exception("kill_tree raised during teardown")
    _flush_all()

    exit_code = 0 if (error is None and not missing) else 1
    stamp = {
        "unit": spec.name,
        "inputs": compute_inputs(spec.name, env),
        "artifact_sha256": sha256_bytes(data),
        "started": started, "finished": time.time(), "exit": exit_code, "timeout_s": unit_timeout_s,
    }
    stamp_bytes = json.dumps(stamp, indent=1, sort_keys=True).encode()
    if not watchdog.commit(lambda: unit_runner.write_atomic(paths["stamp"], stamp_bytes)):
        _sleep_forever_until_killed()
    os._exit(exit_code)  # nothing runs after the stamp: no atexit, no threads, no shutdown


# --------------------------------------------------------------------------- #
# Driver mode
# --------------------------------------------------------------------------- #


def _dry_run(args: argparse.Namespace) -> int:
    plan = {
        "script": str(SCRIPT_PATH), "dist": str(args.dist), "dist_exists": Path(args.dist).is_dir(),
        "unit_timeout_s": UNIT_TIMEOUT_S, "driver_timeout_s": UNIT_TIMEOUT_S + DRIVER_EXTRA_S,
        "probe_deadline_s": UNIT_TIMEOUT_S * DEADLINE_FRACTION, "viewport": VIEWPORT,
        "units": [{"name": u.name, "required_fields": list(u.required)} for u in UNITS],
        "kernel_cells": list(CELL_NAMES), "fixture_sha256": sha256_bytes(fixture_bytes()),
        "imports": list(ALL_IMPORTS), "negative_control_modules": list(NEG_ABSENT_MODULES),
        "plr_pin": {"sha": PIN_SHA, "version_prefix": PIN_VERSION_PREFIX},
        "dist_requirement": "a dist built at the PLR pin; PLR 0.2.2 has no visualizer3D and is `invalid`",
    }
    try:
        plan["chrome_path"] = str(repl_smoke().resolve_chrome_path(args.chrome_path))
    except Exception as exc:  # any failure to load repl_smoke or to find Chromium
        plan["chrome_path"] = None
        plan["chrome_error"] = f"{type(exc).__name__}: {str(exc).splitlines()[0]}"
    print(json.dumps(plan, indent=1))
    return 0


def run_driver(
    args: argparse.Namespace,
    *,
    unit_argv_prefix: list[str] | None = None,
    unit_timeout_s: float = UNIT_TIMEOUT_S,
    driver_extra_s: float = DRIVER_EXTRA_S,
    runner: Any = None,
    env: InputEnv | None = None,
) -> int:
    """Run the unit (resuming if asked), then evaluate outcomes iff it is complete.

    Exit 0: the unit is complete and the outcome fields were written (the sidecar's
    ``[outcomes]`` then evaluate them; an ``invalid`` outcome is still exit 0). Exit 3: the
    unit is incomplete; no outcome is written. Exit 2: the environment is unusable (no
    dist, no chrome).
    """
    runner = runner or unit_runner
    out_dir = Path(args.out_dir)
    (out_dir / "units").mkdir(parents=True, exist_ok=True)
    if env is None:
        try:
            env = build_env(args)
        except (FileNotFoundError, RuntimeError) as exc:
            LOG.error("cannot build the input set: %s", exc)
            return 2
    prefix = unit_argv_prefix if unit_argv_prefix is not None else [sys.executable, str(SCRIPT_PATH)]

    states: dict[str, dict[str, Any]] = {}
    status: dict[str, dict[str, Any]] = {}
    reused: list[dict[str, Any]] = []
    recomputed: list[str] = []
    timed_out: list[str] = []
    stale: list[dict[str, Any]] = []

    for spec in UNITS:
        inputs = compute_inputs(spec.name, env)
        current = inspect_unit(out_dir, spec, inputs)
        if args.resume and current["reusable"]:
            LOG.info("unit %s reused (stamp valid, exit 0, no error, fields present)", spec.name)
            states[spec.name] = current
            reused.append(
                {
                    "unit": spec.name, "source": current["artifact_path"],
                    "inputs": current["stamp"]["inputs"],
                    "artifact_sha256": current["stamp"]["artifact_sha256"],
                }
            )
            status[spec.name] = {"status": "reused"}
            continue
        if args.resume and current["stamp"] is not None:
            stale.append(
                {"unit": spec.name, "mismatched": current["mismatched"], "reasons": current["reasons"]}
            )
        paths = unit_paths(out_dir, spec.name)
        for key in ("stamp", "artifact", "timeout"):
            _rm(paths[key])
        argv = prefix + [
            "--unit", spec.name, "--out-dir", str(out_dir), "--dist", str(args.dist),
            "--base-path", args.base_path,
        ]
        if env.chrome_path:
            argv += ["--chrome-path", env.chrome_path]
        LOG.info("starting unit %s (timeout %.0f s)", spec.name, unit_timeout_s + driver_extra_s)
        outcome = runner.run_unit(argv, unit_timeout_s + driver_extra_s, cwd=str(REPO_ROOT))
        after = inspect_unit(out_dir, spec, inputs)
        states[spec.name] = after
        if after["complete"]:
            if outcome.timed_out:
                LOG.warning("unit %s: run_unit timed out over a VALID stamp; the stamp governs", spec.name)
            recomputed.append(spec.name)
            status[spec.name] = {
                "status": "recomputed", "exit": after["stamp"]["exit"],
                "error": after["artifact"].get("error"),
                "artifact_path": after["artifact_path"],
                "artifact_sha256": after["stamp"]["artifact_sha256"],
                "inputs": after["stamp"]["inputs"],
            }
        else:
            marker = paths["timeout"].exists()
            if outcome.timed_out or marker or outcome.exit == 124:
                timed_out.append(spec.name)
                status[spec.name] = {"status": "timeout", "exit": outcome.exit}
            else:
                status[spec.name] = {"status": "crashed", "exit": outcome.exit, "reasons": after["reasons"]}
            LOG.error("unit %s is INCOMPLETE: %s", spec.name, status[spec.name])

    all_complete = all(states[u.name].get("complete") for u in UNITS)
    aggregate: dict[str, Any] = {
        "spike": "S4", "all_units_complete": all_complete, "outcome_evaluated": False,
        "units": status, "reused": reused, "recomputed": recomputed, "timed_out": timed_out,
        "blocked": [], "stale": stale,
        "incomplete": [u.name for u in UNITS if not states[u.name].get("complete")],
        "error_findings": {
            u.name: states[u.name]["artifact"]["error"]
            for u in UNITS
            if states[u.name].get("complete") and states[u.name]["artifact"].get("error") is not None
        },
        "chrome_path": env.chrome_path, "chrome_version": env.chrome_version,
        "inputs_hashed": {"script": env.script, "runner": env.runner, "harness": env.harness,
                          "dist": env.dist, "fixture": env.fixture, "chrome": env.chrome, "driver": env.driver},
    }
    exit_code = 3
    if all_complete:
        derived = derive_outcome_fields(states[UNIT_NAME]["artifact"])
        aggregate.update(derived["details"])
        aggregate["outcome_fields"] = derived["flat"]
        aggregate["outcome_evaluated"] = True
        results_path = os.environ.get("BTH_RESULTS_PATH")
        if results_path:
            unit_runner.write_atomic(results_path, json.dumps(derived["flat"], sort_keys=True).encode())
        exit_code = 0
    else:
        LOG.error("NOT evaluating outcomes: incomplete units %s", aggregate["incomplete"])
    unit_runner.write_atomic(
        out_dir / "result.json", json.dumps(aggregate, indent=1, sort_keys=True, default=str).encode()
    )
    print(json.dumps(aggregate, sort_keys=True, default=str))
    return exit_code


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out-dir", required=True, help="Output dir (units/<name>.json + stamp + result.json).")
    p.add_argument("--resume", action="store_true", help="Skip a verified-complete unit (D17 rule).")
    p.add_argument("--unit", choices=UNIT_NAMES, default=None, help="Unit mode: run exactly one unit.")
    p.add_argument("--dist", default=str(DEFAULT_DIST),
                   help="Built dist to serve (lab/ entry). MUST be built at the PLR pin (1.0.0b1).")
    p.add_argument("--chrome-path", default=None, help="Full Chromium executable (not headless_shell).")
    p.add_argument("--base-path", default="/", help="URL prefix the dist is served under.")
    p.add_argument("--dry-run", action="store_true", help="Print the plan; launch nothing, hash nothing.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(
    argv: list[str] | None = None,
    *,
    unit_argv_prefix: list[str] | None = None,
    unit_timeout_s: float = UNIT_TIMEOUT_S,
    driver_extra_s: float = DRIVER_EXTRA_S,
) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if args.dry_run:
        return _dry_run(args)
    if args.unit:
        run_unit_mode(args, unit_timeout_s=unit_timeout_s)  # never returns
        return 1  # pragma: no cover
    return run_driver(
        args, unit_argv_prefix=unit_argv_prefix, unit_timeout_s=unit_timeout_s,
        driver_extra_s=driver_extra_s,
    )


if __name__ == "__main__":
    sys.exit(main())
