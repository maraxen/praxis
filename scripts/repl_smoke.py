#!/usr/bin/env python3
"""repl_smoke.py — the ONE Playwright harness for the praxis REPL refocus (task_id 260817_praxis_repl_refocus).

Two modes, one driver:

  --probe        Serves a directory over http://127.0.0.1:<port>, opens a JupyterLite app
                  page with an injected bootstrap `code` cell, waits for the in-kernel
                  probe to finish, and prints a single JSON object to stdout.

  --viz-check    ADDED for P6.3 (spec 260817_spec-visualizer-transport-shim.md, R9/T1.4,
                  gate D3). Serves the vendored, kernel-free PyLabRobot visualizer tree
                  directly (default web-repl/dist/assets/visualizer/), injects a
                  pin-matched golden fixture straight into `window.receiveFromPython(...)`
                  -- no JupyterLite, no Python kernel, no bootstrap at all -- and asserts
                  resource/shape/layer counts plus a real state-delta fill-color
                  transition. `web-repl/scripts/gen_viz_fixtures.py` produces the
                  fixtures and their FIXTURE_MANIFEST.json (pin_sha + expected counts);
                  pass --record here, once per fixture regen, to measure shape_count /
                  layer_count from an actual Konva render and write them into that
                  manifest -- every other run only VERIFIES against what --record wrote,
                  and refuses to run at all if the manifest's pin_sha does not match the
                  live `external/pylabrobot` submodule HEAD.

  WHY ONE FILE, NOT scripts/viz_render_check.py: the visualizer spec proposes a separate
  script by that name, but the execution plan overrides it explicitly -- "Do not create
  three harnesses. The specs propose `repl_smoke.py`, `web-repl/tests/e2e/*.spec.ts`, and
  `scripts/viz_render_check.py` ... One driver + typed modes." (plan §Phase 0, P0.4 note).
  `--viz-check` below is that check. It reuses `ServedDir` and the same
  pinned-Chromium-with-sandbox-disabled launch shape as `--probe` (see `run_probe`), which
  is the whole point of keeping it in this file instead of a fresh script that would have
  to re-derive both. It is a separate CODE PATH (`run_viz_check`, not a branch inside
  `run_probe`/`build_probe_code`) because it drives an entirely different surface: no
  JupyterLite console, no bootstrap fetch, no Python kernel, no probe-sentinel protocol --
  just a static page and one JS bridge function that already exists in the vendored
  `vis.js` (`window.receiveFromPython`). Forcing it through `build_probe_code`'s
  kernel-cell-execution machinery would add a fake kernel dependency to a check whose
  entire point (spec: "browserless... no Python") is not needing one.

REPOINTED 2026-08-18 (post-move, web-repl/dist/ now exists — see this task's report for
what was verified empirically, not assumed). Entry path is `lab/index.html`, not
`repl/index.html`: `inject_shell.py` only ever injects the D1 shell script
(`window.PRAXIS_GIT_SHA` + `<script src="./shell/praxis-shell.js">`) into
`dist/lab/index.html` (ADR Sec 2.3/5.5) — `dist/repl/index.html` never carries it, so
D1's `praxis:shell-ping`/`pong` handshake has no listener there and can only fail
closed. ADR Sec 7 leaves `repl/` vs `lab/` an open product question; this is "pick what
the build actually produces" for that question, not a preference.

Do NOT create a second harness for this project — see the ADR at
.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md and the execution
plan at .praxia/docs/plans/260817_praxis-repl-refocus-execution-plan.md (P0.4).

Hard constraints (verified 2026-08-17, see plan section 5.6):
  - Playwright can only launch Chromium here with the Bash sandbox DISABLED
    (dangerouslyDisableSandbox=true) AND --no-sandbox --disable-dev-shm-usage.
  - playwright 1.62.0 wants chromium build 1234, which is NOT installed; --chrome-path
    must point at the 1228 build instead (default below).
  - Serve everything over http://127.0.0.1:<port>. NEVER about:blank, NEVER file://
    — on about:blank navigator.serial reads False because it is not a secure context,
    which would wrongly read as a capability regression.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import textwrap
import threading
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

LOG = logging.getLogger("repl_smoke")

#: Last-resort Chromium path. Kept because playwright 1.62.0 on THIS box wants
#: build 1234, which is not installed, while 1228 is -- see the module docstring.
#: It is a fallback, not the default: hardcoding one developer's home directory as
#: the default made every browser gate unrunnable anywhere else, CI included.
LOCAL_FALLBACK_CHROME_PATH = (
    "/home/marielle/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome"
)
CHROME_PATH_ENV_VAR = "PRAXIS_CHROME_PATH"


def _is_executable(path: Path) -> bool:
    return path.is_file() and bool(path.stat().st_mode & 0o111)


def _chromium_build_number(path: Path) -> int:
    """Sort key for `.../chromium-1228/chrome-linux64/chrome`. 0 when unparseable."""
    name = path.parent.parent.name  # e.g. "chromium-1228" or "chromium_headless_shell-1234"
    digits = name.rsplit("-", 1)[-1]
    return int(digits) if digits.isdigit() else 0


def resolve_chrome_path(explicit: str | None = None) -> Path:
    """Find a usable Chromium, in descending order of explicitness.

    ``--chrome-path`` -> ``$PRAXIS_CHROME_PATH`` -> Playwright's own bundled
    Chromium -> this box's 1228 build. Raises with all four sources named rather
    than letting Playwright fail later about a missing executable, which reads as
    a browser bug instead of a configuration one.
    """
    tried: list[str] = []

    if explicit:
        tried.append(f"--chrome-path={explicit}")
        if _is_executable(Path(explicit)):
            return Path(explicit)

    env_value = os.environ.get(CHROME_PATH_ENV_VAR)
    if env_value:
        tried.append(f"${CHROME_PATH_ENV_VAR}={env_value}")
        if _is_executable(Path(env_value)):
            return Path(env_value)

    # Playwright's own download location -- what `playwright install chromium`
    # produces, and the only Chromium present in CI. Discovered by globbing the
    # browsers cache rather than by reading p.chromium.executable_path: that
    # requires spinning up the Playwright driver connection, which (a) reports the
    # build playwright WANTS rather than one that exists, and (b) emits
    # "Task was destroyed but it is pending" teardown noise into every run's logs.
    # Highest build number first, so a newer install wins over a stale one.
    browsers_root = Path(
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
        or (Path.home() / ".cache" / "ms-playwright")
    )
    candidates = sorted(
        browsers_root.glob("chromium*/chrome-linux*/chrome"),
        key=lambda q: _chromium_build_number(q),
        reverse=True,
    )
    tried.append(
        f"playwright cache={browsers_root} "
        f"({len(candidates)} candidate(s): {[c.parent.parent.name for c in candidates]})"
    )
    for candidate in candidates:
        if _is_executable(candidate):
            return candidate

    tried.append(f"local fallback={LOCAL_FALLBACK_CHROME_PATH}")
    if _is_executable(Path(LOCAL_FALLBACK_CHROME_PATH)):
        return Path(LOCAL_FALLBACK_CHROME_PATH)

    raise FileNotFoundError(
        "no usable Chromium found. Tried, in order:\n  "
        + "\n  ".join(tried)
        + "\nInstall one with `uv run playwright install --with-deps chromium`, or "
        f"point --chrome-path / ${CHROME_PATH_ENV_VAR} at an existing build."
    )
DEFAULT_TIMEOUT_S = 120.0

# GATE G5's offline clause. These are blackholed at the CHROMIUM RESOLVER level, not
# via `page.route()`: the plan's trap #1 records that `page.route()` does not intercept
# Web Worker requests, and the Pyodide kernel IS a Web Worker -- a route()-based offline
# gate passes vacuously while the worker happily reaches the network. Resolver rules
# apply process-wide, workers included.
OFFLINE_BLACKHOLE_HOSTS = ("cdn.jsdelivr.net", "pypi.org", "files.pythonhosted.org")

# Sacrificial port on loopback: connections are refused fast rather than hanging until
# the harness timeout, so a genuine offline breakage reports as an error, not a stall.
OFFLINE_BLACKHOLE_TARGET = "127.0.0.1:1"

BASE_CHROMIUM_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"]


def chromium_launch_args(*, offline: bool) -> list[str]:
    """Base chromium args, plus resolver blackholes when *offline*.

    One rule per host, comma-joined into a single `--host-resolver-rules` value
    (chromium takes a comma-separated rule list, not a repeated flag).
    """
    args = list(BASE_CHROMIUM_ARGS)
    if offline:
        rules = ",".join(
            f"MAP {host} {OFFLINE_BLACKHOLE_TARGET}" for host in OFFLINE_BLACKHOLE_HOSTS
        )
        args.append(f"--host-resolver-rules={rules}")
    return args


PROBE_START = "===PRAXIS_PROBE_JSON_START==="
PROBE_END = "===PRAXIS_PROBE_JSON_END==="


def find_repo_root(start: Path) -> Path:
    """Search upward from `start` for the directory containing pyproject.toml.

    Never uses Path.cwd() or a bare relative string — anchored to __file__ per
    house script conventions (see ~/.claude/rules/CLUSTER.md §1a for the pattern).
    """
    cur = start.resolve()
    for candidate in (cur, *cur.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError(f"could not locate pyproject.toml above {start}")


REPO_ROOT = find_repo_root(Path(__file__).parent)
DEFAULT_SERVE_DIR = REPO_ROOT / "web-repl" / "dist"

# --viz-check defaults. The dist copy (not overlay/) is served by default so the check
# exercises what build_repl.py actually shipped -- same "pick what the build produces"
# reasoning as DEFAULT_SERVE_DIR/lab-vs-repl above. web-repl/scripts/vendor_visualizer.py
# copies overlay/assets/visualizer/ into dist/assets/visualizer/ byte-identically, so
# pointing --visualizer-dir at overlay/ directly (e.g. right after a regen, before a dist
# rebuild) is a supported override, not a special case.
DEFAULT_VISUALIZER_DIR = REPO_ROOT / "web-repl" / "dist" / "assets" / "visualizer"
#: How long --viz-check waits for a praxis_viz envelope to reach the renderer.
#: Deliberately short: delivery is sub-second when the wiring is intact, and a
#: long budget only delays an already-certain failure.
CHANNEL_DISPATCH_TIMEOUT_S = 15.0
DEFAULT_FIXTURE_DIR = REPO_ROOT / "web-repl" / "tests" / "fixtures" / "visualizer"
DEFAULT_PLR_SUBMODULE = REPO_ROOT / "external" / "pylabrobot"


# ---------------------------------------------------------------------------
# Static file server: serves a directory at an optional URL prefix, with
# optional COOP/COEP headers so the "deployed configuration" (credentialless
# COEP) can be exercised. NOTE: `web-repl/dist/index.html` carries no
# client-side COI config at all (no coi-serviceworker.js, unlike the
# pre-move `praxis/web-client/src/index.html:9-22` this comment used to
# point at) -- these server-sent headers are the only COI mechanism for the
# new dist/, verified 2026-08-18.
# ---------------------------------------------------------------------------


def _normalize_base_path(base_path: str) -> str:
    if not base_path.startswith("/"):
        base_path = "/" + base_path
    if not base_path.endswith("/"):
        base_path += "/"
    return base_path


def make_handler(serve_dir: Path, base_path: str, coi: bool) -> type[SimpleHTTPRequestHandler]:
    prefix = _normalize_base_path(base_path)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(serve_dir), **kwargs)

        def translate_path(self, path: str) -> str:
            p = path.split("?", 1)[0].split("#", 1)[0]
            if prefix != "/" and p.startswith(prefix):
                p = "/" + p[len(prefix) :]
            elif prefix != "/" and p == prefix[:-1]:
                p = "/"
            return super().translate_path(p)

        def end_headers(self) -> None:
            if coi:
                self.send_header("Cross-Origin-Opener-Policy", "same-origin")
                self.send_header("Cross-Origin-Embedder-Policy", "credentialless")
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, fmt: str, *args: Any) -> None:
            LOG.debug("http: " + fmt, *args)

    return Handler


class ServedDir:
    """Context manager wrapping a background ThreadingHTTPServer."""

    def __init__(self, serve_dir: Path, base_path: str, coi: bool) -> None:
        handler_cls = make_handler(serve_dir, base_path, coi)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self) -> ServedDir:
        self.thread.start()
        LOG.info("serving on http://127.0.0.1:%d", self.port)
        return self

    def __exit__(self, *exc: object) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


# ---------------------------------------------------------------------------
# The in-kernel probe. Runs as a single top-level `await` cell so the execute
# request does not report idle until the whole probe (bootstrap + assertions
# + interaction roundtrip) has finished, guaranteeing the printed JSON lands
# in the same cell's output.
# ---------------------------------------------------------------------------


def build_probe_code(host_root: str, expect_praxis_sha: str | None) -> str:
    # The `code` URL param is echoed verbatim into the console's editable cell
    # BEFORE execution, so if the literal sentinel strings appeared contiguously
    # in this source, Playwright's wait_for_function would match the pre-run
    # SOURCE DISPLAY rather than the post-run PRINTED OUTPUT. Every sentinel is
    # therefore built from two literals joined with `+` at runtime so the full
    # contiguous string exists only in the printed output.
    start_a, start_b = PROBE_START[: len(PROBE_START) // 2], PROBE_START[len(PROBE_START) // 2 :]
    end_a, end_b = PROBE_END[: len(PROBE_END) // 2], PROBE_END[len(PROBE_END) // 2 :]
    return textwrap.dedent(
        f"""
        import asyncio, builtins, importlib, json, sys, traceback
        import js

        HOST_ROOT = {host_root!r}
        EXPECT_SHA = {expect_praxis_sha!r}
        _SENTINEL_START = {start_a!r} + {start_b!r}
        _SENTINEL_END = {end_a!r} + {end_b!r}
        RESULT: dict = {{"host_root": HOST_ROOT}}


        async def _main():
            # --- 1. fetch + exec the bootstrap, then await praxis_main ---
            try:
                xhr = js.XMLHttpRequest.new()
                xhr.open("GET", HOST_ROOT + "bootstrap/praxis_bootstrap.py", False)
                xhr.send(None)
                bootstrap_src = str(xhr.responseText)
                exec(compile(bootstrap_src, "praxis_bootstrap.py", "exec"), globals())
                await praxis_main(HOST_ROOT)  # noqa: F821 - injected by exec above
                RESULT["praxis_ready"] = True
            except Exception as e:  # noqa: BLE001 - probe must never die silently
                RESULT["praxis_ready"] = False
                RESULT["bootstrap_error"] = f"{{type(e).__name__}}: {{e}}"
                RESULT["bootstrap_traceback"] = traceback.format_exc()

            # --- 2. pylabrobot version/identity ---
            try:
                import pylabrobot
                RESULT["pylabrobot_version"] = getattr(pylabrobot, "__version__", None)
                RESULT["pylabrobot_file"] = getattr(pylabrobot, "__file__", None)
            except Exception as e:  # noqa: BLE001
                RESULT["pylabrobot_version"] = None
                RESULT["pylabrobot_file"] = None
                RESULT["pylabrobot_import_error"] = f"{{type(e).__name__}}: {{e}}"

            # --- 2b. websockets + HAS_WEBSOCKETS (the visualizer's precondition) ---
            # G2 criterion 1 passed only as a MECHANISM pass: it was measured with
            # micropip.install("websockets") against live PyPI. That install was
            # then superseded (it would fail GATE G5's offline run), and
            # websockets-17.0.1 was vendored into overlay/assets/wheels/ instead --
            # but the verdict's own section 8(a) notes the in-kernel probe stayed
            # OPEN. This closes it, and closes it in the configuration that matters:
            # under --offline the wheel is the only possible source.
            #
            # Load-bearing because the guard is in Visualizer.__init__ (visualizer.py
            # :144 at this pin), not in setup(). A False flag here means the class
            # cannot even be CONSTRUCTED, so BrowserVisualizer's setup()/stop()/
            # has_connection()/send_command() override design collapses to the
            # stub-websockets fallback before any of it runs.
            try:
                import websockets
                RESULT["websockets_version"] = getattr(websockets, "__version__", None)
                RESULT["websockets_file"] = getattr(websockets, "__file__", None)
            except Exception as e:  # noqa: BLE001
                RESULT["websockets_version"] = None
                RESULT["websockets_import_error"] = f"{{type(e).__name__}}: {{e}}"
            try:
                from pylabrobot.visualizer import visualizer as _plr_viz
                RESULT["plr_has_websockets"] = bool(_plr_viz.HAS_WEBSOCKETS)
                RESULT["plr_websockets_import_error"] = str(
                    getattr(_plr_viz, "_WEBSOCKETS_IMPORT_ERROR", None)
                )
            except Exception as e:  # noqa: BLE001
                RESULT["plr_has_websockets"] = None
                RESULT["plr_visualizer_import_error"] = f"{{type(e).__name__}}: {{e}}"

            # --- 2c. praxis.viz in a REAL kernel (P6.4/P6.5 counterpart) ---
            # web-repl/tests/test_browser_visualizer.py proves the ordering under
            # CPython with an injected transport. That cannot prove the module is
            # fetched by the bootstrap, that pylabrobot imports beside it in
            # Pyodide, or that Visualizer.__init__'s HAS_WEBSOCKETS guard passes
            # against the VENDORED websockets wheel. This does.
            #
            # Uses RecordingTransport, not a BroadcastChannel: the assertion here
            # is that the emit chain runs in-kernel, and a real channel would add
            # a second failure mode (origin scoping) to a check that is not about
            # that. GATE G6's pick_up_tips arm still needs a LiquidHandler and is
            # NOT covered here.
            try:
                from praxis.viz.browser import BrowserVisualizer
                from praxis.viz.transport import RecordingTransport
                from pylabrobot.resources import Coordinate, Resource

                _root = Resource(name="probe_root", size_x=100, size_y=100, size_z=10)
                _tr = RecordingTransport()
                _viz = BrowserVisualizer(
                    _root, transport=_tr, show_machine_tools_at_start=False
                )
                await _viz.setup()
                for _ in range(5):
                    await asyncio.sleep(0)
                _kid = Resource(name="probe_child", size_x=10, size_y=10, size_z=5)
                _root.assign_child_resource(_kid, location=Coordinate(0, 0, 0))
                for _ in range(5):
                    await asyncio.sleep(0)
                RESULT["viz_events"] = list(_tr.events)
                RESULT["viz_stats"] = _viz.stats()
                RESULT["viz_ok"] = True
            except Exception as e:  # noqa: BLE001
                RESULT["viz_ok"] = False
                RESULT["viz_error"] = f"{{type(e).__name__}}: {{e}}"
                RESULT["viz_traceback"] = traceback.format_exc()

            # --- 2d. GATE G6's decisive arm, IN A REAL KERNEL ---
            # "pick_up_tips produces set_state AFTER set_root_resource;
            #  viz.stats()['sent'] >= 2 -- exactly 1 is the documented FAILURE
            #  signature." The browserless half lives in
            #  web-repl/tests/test_browser_visualizer.py; this is the half the gate
            #  text actually specifies ("in a real kernel").
            #
            # set_tip_tracking(True) is REQUIRED and the gate text omits it:
            # does_tip_tracking() defaults to False, and with tracking off
            # pick_up_tips mutates no resource state, so no callback fires and no
            # set_state is emitted -- the gate then fails for a reason unrelated to
            # the transport, while chatterbox still prints a full pickup.
            try:
                from pylabrobot.liquid_handling import LiquidHandler
                from pylabrobot.liquid_handling.backends import (
                    LiquidHandlerChatterboxBackend,
                )
                from pylabrobot.resources import (
                    STARLetDeck,
                    does_tip_tracking,
                    set_tip_tracking,
                )
                from pylabrobot.resources.hamilton import (
                    hamilton_96_tiprack_1000uL_filter as _TipRack1000,
                )
                from praxis.viz.browser import BrowserVisualizer as _BV
                from praxis.viz.transport import RecordingTransport as _RT

                _prev_tracking = does_tip_tracking()
                set_tip_tracking(True)
                try:
                    _deck = STARLetDeck()
                    _lh = LiquidHandler(
                        backend=LiquidHandlerChatterboxBackend(num_channels=8),
                        deck=_deck,
                    )
                    _t2 = _RT()
                    _v2 = _BV(_deck, transport=_t2, show_machine_tools_at_start=False)
                    await _lh.setup()
                    await _v2.setup()
                    await asyncio.sleep(0.05)
                    _rack = _TipRack1000(name="tips_01")
                    _deck.assign_child_resource(_rack, rails=3)
                    await asyncio.sleep(0.05)
                    _before = len(_t2.events)
                    await _lh.pick_up_tips(_rack["A1:D1"])
                    await asyncio.sleep(0.3)
                    _ev = list(_t2.events)
                    RESULT["g6_events"] = _ev
                    RESULT["g6_after_pickup"] = _ev[_before:]
                    RESULT["g6_stats"] = _v2.stats()
                    RESULT["g6_last_state_keys"] = sorted(
                        _t2.decoded(len(_t2.messages) - 1).get("data", {{}})
                    )
                    RESULT["g6_pass"] = bool(
                        _ev and _ev[0] == "set_root_resource"
                        and "set_state" in _ev[_before:]
                        and _v2.stats().get("sent", 0) >= 2
                    )
                finally:
                    set_tip_tracking(_prev_tracking)
            except Exception as e:  # noqa: BLE001
                RESULT["g6_pass"] = False
                RESULT["g6_error"] = f"{{type(e).__name__}}: {{e}}"
                RESULT["g6_traceback"] = traceback.format_exc()

            # --- 3. four io classes: repr + identity vs. builtins, by `is` ---
            io_reprs: dict = {{}}
            io_identity: dict = {{}}
            capability_flags: dict = {{}}
            for mod_name, cls_attr, builtin_name, flag_name in [
                ("pylabrobot.io.serial", "Serial", "WebSerial", "HAS_SERIAL"),
                ("pylabrobot.io.usb", "USB", "WebUSB", "USE_USB"),
                ("pylabrobot.io.hid", "HID", "WebHID", "USE_HID"),
                ("pylabrobot.io.ftdi", "FTDI", "WebFTDI", "HAS_PYLIBFTDI"),
            ]:
                try:
                    mod = importlib.import_module(mod_name)
                    cls_obj = getattr(mod, cls_attr, None)
                    io_reprs[mod_name] = repr(cls_obj)
                    builtin_obj = getattr(builtins, builtin_name, None)
                    io_identity[mod_name] = bool(
                        cls_obj is not None and builtin_obj is not None and cls_obj is builtin_obj
                    )
                    capability_flags[flag_name] = getattr(mod, flag_name, None)
                except Exception as e:  # noqa: BLE001
                    io_reprs[mod_name] = f"ERROR: {{type(e).__name__}}: {{e}}"
                    io_identity[mod_name] = False
                    capability_flags[flag_name] = None
            RESULT["io_class_reprs"] = io_reprs
            RESULT["io_class_identity"] = io_identity
            RESULT["capability_flags"] = capability_flags

            # --- 4. serial module is a real module, not the load-bearing MagicMock ---
            try:
                serial_mod = sys.modules.get("serial")
                RESULT["serial_module_is_not_MagicMock"] = bool(
                    serial_mod is not None
                    and "unittest.mock" not in type(serial_mod).__module__
                )
            except Exception as e:  # noqa: BLE001
                RESULT["serial_module_is_not_MagicMock"] = None
                RESULT["serial_module_error"] = f"{{type(e).__name__}}: {{e}}"

            # --- 5. web_serial_shim.IN_PYODIDE (the known-broken `window` import bug) ---
            try:
                import web_serial_shim
                RESULT["web_serial_IN_PYODIDE"] = web_serial_shim.IN_PYODIDE
            except Exception as e:  # noqa: BLE001
                RESULT["web_serial_IN_PYODIDE"] = None
                RESULT["web_serial_shim_import_error"] = f"{{type(e).__name__}}: {{e}}"

            # --- 6. WebSerial() construction ---
            try:
                builtins.WebSerial()
                RESULT["WebSerial_construct"] = {{"raised": False}}
            except Exception as e:  # noqa: BLE001
                RESULT["WebSerial_construct"] = {{
                    "raised": True,
                    "exception": type(e).__name__,
                    "message": str(e),
                }}

            # --- 7. polyfill lookup (window.polyfillSerial visibility from the worker) ---
            try:
                import web_serial_shim as _wss
                if not _wss.IN_PYODIDE:
                    RESULT["polyfill_lookup"] = {{
                        "status": "not_reached",
                        "reason": "IN_PYODIDE is False; the js.window import failed before "
                        "the polyfill lookup branch could run",
                    }}
                else:
                    RESULT["polyfill_lookup"] = {{"status": "reached"}}
            except Exception as e:  # noqa: BLE001
                RESULT["polyfill_lookup"] = {{"status": "error", "detail": f"{{type(e).__name__}}: {{e}}"}}

            # --- 8. web_bridge wiring ---
            try:
                import web_bridge
                RESULT["web_bridge_import"] = True
                RESULT["has_request_user_interaction"] = hasattr(
                    web_bridge, "request_user_interaction"
                )
                RESULT["broadcast_channel_registered"] = (
                    getattr(web_bridge, "_broadcast_channel", None) is not None
                )
            except Exception as e:  # noqa: BLE001
                RESULT["web_bridge_import"] = False
                RESULT["has_request_user_interaction"] = False
                RESULT["broadcast_channel_registered"] = False
                RESULT["web_bridge_import_error"] = f"{{type(e).__name__}}: {{e}}"

            # --- 9. device-auth interaction roundtrip (97a75988 chain) ---
            # Relies on the page-side auto-responder BroadcastChannel listener
            # installed by repl_smoke.py before navigation.
            try:
                import web_bridge
                task = asyncio.ensure_future(
                    web_bridge.request_user_interaction("confirm", {{"message": "probe"}})
                )
                value = await asyncio.wait_for(task, timeout=8)
                RESULT["interaction_roundtrip"] = {{"ok": True, "value": value}}
            except Exception as e:  # noqa: BLE001
                RESULT["interaction_roundtrip"] = {{
                    "ok": False,
                    "error": f"{{type(e).__name__}}: {{e}}",
                }}

            # --- 10. praxis_git_sha drift (D1) -- not implemented pre-change ---
            RESULT["praxis_sha_match"] = None if EXPECT_SHA is None else False

            RESULT["python_version"] = list(sys.version_info[:3])


        await _main()
        print(_SENTINEL_START)
        print(json.dumps(RESULT))
        print(_SENTINEL_END)
        """
    ).strip()


def build_completion_probe_code(host_root: str) -> str:
    """In-kernel payload measuring what the completer ACTUALLY does (gate T2).

    Answers the two questions a config diff cannot. First, whether jedi is
    loaded: `IPython/core/completer.py:254` does `import jedi` at MODULE IMPORT
    time and `use_jedi` is only `Bool(default_value=JEDI_INSTALLED)` (line 998),
    so if jedi is not resident before the kernel imports IPython the completer is
    permanently on the `dir()`-based fallback and no runtime toggle fixes it
    (setting use_jedi True then selects `_jedi_matcher` against an unbound name).

    Second, and the reason this gate exists at all: LATENCY. The frontend gives a
    completion `providerTimeout` of 1000 ms by default. Jedi builds a parso
    grammar cache on its first call, single-threaded, in WASM. If that first call
    overruns the timeout the user sees NOTHING -- strictly worse than the fast
    fallback we already ship. So this times a cold call, a warm call, and a light
    control, and reports all three rather than asserting a threshold here: the
    threshold is a judgement made against the measurement, not baked into it.

    Deliberately mirrors build_probe_code's split-sentinel construction (the `code`
    URL param is echoed into the cell BEFORE execution, so a contiguous sentinel
    literal in this source would match the source display, not the output).
    """
    start_a, start_b = PROBE_START[: len(PROBE_START) // 2], PROBE_START[len(PROBE_START) // 2 :]
    end_a, end_b = PROBE_END[: len(PROBE_END) // 2], PROBE_END[len(PROBE_END) // 2 :]
    return textwrap.dedent(
        f"""
        import json, sys, time, traceback
        import js

        HOST_ROOT = {host_root!r}
        _SENTINEL_START = {start_a!r} + {start_b!r}
        _SENTINEL_END = {end_a!r} + {end_b!r}
        RESULT: dict = {{"host_root": HOST_ROOT}}


        async def _main():
            # --- 1. boot praxis so pylabrobot is importable at all ---
            try:
                xhr = js.XMLHttpRequest.new()
                xhr.open("GET", HOST_ROOT + "bootstrap/praxis_bootstrap.py", False)
                xhr.send(None)
                exec(compile(str(xhr.responseText), "praxis_bootstrap.py", "exec"), globals())
                await praxis_main(HOST_ROOT)  # noqa: F821 - injected by exec above
                RESULT["praxis_ready"] = True
            except Exception as e:  # noqa: BLE001 - probe must never die silently
                RESULT["praxis_ready"] = False
                RESULT["bootstrap_error"] = f"{{type(e).__name__}}: {{e}}"
                RESULT["bootstrap_traceback"] = traceback.format_exc()

            # --- 2. is jedi resident, and did IPython latch onto it? ---
            try:
                import IPython.core.completer as _c
                RESULT["jedi_installed"] = bool(_c.JEDI_INSTALLED)
            except Exception as e:  # noqa: BLE001
                RESULT["jedi_installed"] = None
                RESULT["completer_import_error"] = f"{{type(e).__name__}}: {{e}}"
            try:
                import jedi
                RESULT["jedi_version"] = getattr(jedi, "__version__", None)
            except Exception as e:  # noqa: BLE001
                RESULT["jedi_version"] = None
                RESULT["jedi_import_error"] = f"{{type(e).__name__}}: {{e}}"

            # --- 3. reach the live shell WITHOUT constructing one ---
            # InteractiveShell.instance() would CREATE a shell if none existed,
            # which would measure a completer that is not the kernel's. Read the
            # existing instance or report unreachable; never fabricate.
            ip = None
            try:
                from IPython.core.getipython import get_ipython
                ip = get_ipython()
                if ip is None:
                    from IPython.core.interactiveshell import InteractiveShell
                    ip = InteractiveShell._instance
            except Exception as e:  # noqa: BLE001
                RESULT["shell_error"] = f"{{type(e).__name__}}: {{e}}"
            if ip is None:
                RESULT["completer_reachable"] = False
                RESULT["python_version"] = list(sys.version_info[:3])
                return
            RESULT["completer_reachable"] = True
            RESULT["use_jedi"] = bool(getattr(ip.Completer, "use_jedi", False))

            try:
                exec("from pylabrobot.liquid_handling import LiquidHandler", ip.user_ns)
                RESULT["plr_import"] = True
            except Exception as e:  # noqa: BLE001
                RESULT["plr_import"] = False
                RESULT["plr_import_error"] = f"{{type(e).__name__}}: {{e}}"

            from IPython.core.completer import provisionalcompleter

            def _timed(text):
                t0 = time.perf_counter()
                err = None
                comps = []
                try:
                    with provisionalcompleter():
                        comps = list(ip.Completer.completions(text, len(text)))
                except Exception as e:  # noqa: BLE001
                    err = f"{{type(e).__name__}}: {{e}}"
                ms = (time.perf_counter() - t0) * 1000.0
                return {{
                    "ms": round(ms, 1),
                    "n": len(comps),
                    "sample": sorted({{c.text for c in comps}})[:8],
                    "error": err,
                }}

            # Order matters: the FIRST call pays jedi's grammar-cache cost, and
            # that is the number the providerTimeout decision turns on.
            RESULT["plr_cold"] = _timed("LiquidHandler.")
            RESULT["plr_warm"] = _timed("LiquidHandler.")
            RESULT["sys_light"] = _timed("sys.")
            RESULT["python_version"] = list(sys.version_info[:3])


        await _main()
        print(_SENTINEL_START)
        print(json.dumps(RESULT))
        print(_SENTINEL_END)
        """
    ).strip()


AUTO_RESPONDER_INIT_SCRIPT = """
(() => {
  try {
    window.__praxisRequestLog = [];
    window.__praxisAutoResponses = [];
    window.__praxisReadyReceived = false;
    const ch = new BroadcastChannel('praxis_repl');
    ch.onmessage = (event) => {
      const data = event.data;
      window.__praxisRequestLog.push({ ts: Date.now(), data: JSON.parse(JSON.stringify(data)) });
      if (data && typeof data === 'object') {
        if (data.type === 'praxis:ready') {
          window.__praxisReadyReceived = true;
        }
        if (data.type === 'USER_INTERACTION' && data.payload && data.payload.id) {
          const id = data.payload.id;
          window.__praxisAutoResponses.push(id);
          ch.postMessage({ type: 'praxis:interaction_response', id, value: 'PROBE_AUTO_RESPONSE' });
        }
      }
    };
    window.__praxisAutoChannel = ch;
  } catch (e) {
    window.__praxisAutoChannelError = String(e);
  }
})();
"""


def run_probe(
    *,
    serve_dir: Path,
    base_path: str,
    coi: bool,
    chrome_path: str,
    timeout_s: float,
    expect_praxis_sha: str | None,
    entry: str = "lab",
    offline: bool = False,
    code_override: str | None = None,
) -> dict[str, Any]:
    # `code_override` lets a caller drive this same browser/serve/sentinel
    # machinery with a DIFFERENT in-kernel payload. It exists so --completion-check
    # does not have to edit build_probe_code: that builder is shared by --probe and
    # --offline (both CI gates), and its f-string + textwrap.dedent + split-sentinel
    # construction is the path that silently produced a mis-dedented payload once
    # already. A new payload is a new function; this is the seam that allows it.
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as e:  # pragma: no cover - environment problem, not a probe result
        raise RuntimeError(f"playwright is not importable: {e}") from e

    prefix = _normalize_base_path(base_path)
    timeout_ms = timeout_s * 1000

    with ServedDir(serve_dir, base_path, coi) as served:
        url = (
            f"http://127.0.0.1:{served.port}{prefix}{entry}/index.html"
        )
        code = (
            code_override
            if code_override is not None
            else build_probe_code(prefix, expect_praxis_sha)
        )
        params = urllib.parse.urlencode(
            {"kernel": "python", "toolbar": "1", "execute": "1", "code": code}
        )
        full_url = f"{url}?{params}"
        LOG.info("navigating to %s (url length %d)", url, len(full_url))

        request_log: list[dict[str, Any]] = []
        http_errors: list[dict[str, Any]] = []
        requestfailed: list[dict[str, Any]] = []
        pageerrors: list[str] = []
        console_messages: list[dict[str, Any]] = []
        offline_blackhole_verified: bool | None = None

        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=chrome_path,
                headless=True,
                args=chromium_launch_args(offline=offline),
            )
            try:
                context = browser.new_context()
                page = context.new_page()
                page.add_init_script(AUTO_RESPONDER_INIT_SCRIPT)

                page.on(
                    "request",
                    lambda req: request_log.append(
                        {"url": req.url, "method": req.method, "resource_type": req.resource_type}
                    ),
                )
                # `req.failure` is a `str | None` in current Playwright, NOT the
                # `{"errorText": ...}` dict this handler originally assumed. The old
                # `.get("errorText")` form raised AttributeError inside the event
                # callback, so every failed request was silently DROPPED and the list
                # stayed empty. That never showed up before --offline existed, because
                # nothing ever failed; the first genuine failure then read as "0
                # failures", which is precisely backwards. Normalised here rather than
                # at the read sites so the list has one shape everywhere.
                page.on(
                    "requestfailed",
                    lambda req: requestfailed.append(
                        {
                            "url": req.url,
                            "failure": (
                                req.failure
                                if isinstance(req.failure, str) or req.failure is None
                                else (req.failure or {}).get("errorText")
                            ),
                            "resource_type": req.resource_type,
                        }
                    ),
                )
                page.on(
                    "response",
                    lambda res: http_errors.append({"url": res.url, "status": res.status})
                    if res.status >= 400
                    else None,
                )
                page.on("pageerror", lambda exc: pageerrors.append(str(exc)))
                page.on(
                    "console",
                    lambda msg: console_messages.append({"type": msg.type, "text": msg.text}),
                )

                page.goto(full_url, wait_until="load", timeout=timeout_ms)
                try:
                    page.wait_for_function(
                        "sentinel => document.body.innerText.includes(sentinel)",
                        arg=PROBE_END,
                        timeout=timeout_ms,
                    )
                except Exception as wait_exc:  # noqa: BLE001
                    # A bare "Timeout 120000ms exceeded" tells you NOTHING about why the
                    # boot never finished, and the page is about to be closed in the
                    # `finally` below -- so everything diagnostic has to be harvested
                    # HERE or it is lost forever. This matters most for --offline, whose
                    # whole job is to fail: without this, a genuine offline breakage and
                    # a slow kernel are the same message.
                    try:
                        stuck_body = page.evaluate("() => document.body.innerText")
                    except Exception:  # noqa: BLE001
                        stuck_body = "<unavailable>"
                    def _entry_url(entry: Any) -> str | None:
                        if isinstance(entry, dict):
                            return entry.get("url")
                        return entry if isinstance(entry, str) else None

                    failed_hosts = sorted(
                        {
                            urllib.parse.urlparse(u).hostname
                            for u in (_entry_url(r) for r in requestfailed)
                            if u
                        }
                        - {None}
                    )
                    raise RuntimeError(
                        f"probe never printed its sentinel: {type(wait_exc).__name__}: "
                        f"{wait_exc}\n"
                        f"  offline={offline} blackholed={list(OFFLINE_BLACKHOLE_HOSTS) if offline else []}\n"
                        f"  failed-request hosts ({len(requestfailed)} failures): {failed_hosts}\n"
                        f"  failed requests (first 10): "
                        f"{json.dumps(requestfailed[:10], indent=2)}\n"
                        f"  console (last 40): "
                        f"{json.dumps(console_messages[-40:], indent=2)}\n"
                        f"  page text (last 1500 chars): {stuck_body[-1500:]!r}"
                    ) from wait_exc

                body_text = page.evaluate("() => document.body.innerText")
                cross_origin_isolated = page.evaluate("() => window.crossOriginIsolated")
                auto_responses = page.evaluate("() => window.__praxisAutoResponses || []")
                ready_received = page.evaluate("() => window.__praxisReadyReceived === true")
                broadcast_log = page.evaluate("() => window.__praxisRequestLog || []")

                # NON-VACUITY SELF-TEST. An offline gate that never observes a
                # blackholed host actually failing proves nothing -- and this whole
                # site is deliberately self-contained, so a green offline boot is
                # ALSO what a silently-inert blackhole looks like. The two are
                # indistinguishable from the boot result alone. So: with the rules
                # in force, reach for a blackholed host from the page and require
                # the fetch to FAIL. `mode: "no-cors"` keeps CORS out of it, so a
                # rejection means the connection itself did not happen.
                if offline:
                    offline_blackhole_verified = page.evaluate(
                        """async (host) => {
                            try {
                                await fetch('https://' + host + '/praxis-offline-probe',
                                            {mode: 'no-cors', cache: 'no-store'});
                                return false;   // reachable => blackhole is NOT in force
                            } catch (e) {
                                return true;    // refused => rules are live
                            }
                        }""",
                        arg=OFFLINE_BLACKHOLE_HOSTS[0],
                    )
            finally:
                browser.close()

    match = re.search(
        re.escape(PROBE_START) + r"\s*(.*?)\s*" + re.escape(PROBE_END), body_text, re.DOTALL
    )
    if not match:
        raise RuntimeError(
            "probe sentinel not found in page text; last 2000 chars: "
            f"{body_text[-2000:]!r}"
        )
    kernel_result = json.loads(match.group(1))

    # praxis_bootstrap.py's own praxis_main() wraps its entire body in one
    # `except Exception: ... _post({"type": "praxis:error", ...})` and does NOT
    # re-raise (verified 2026-08-18, praxis_bootstrap.py:337-342 -- "fail-closed
    # catch-all, by design"). That means `await praxis_main(HOST_ROOT)` in the
    # in-kernel probe below NEVER raises on a failed boot, so the kernel-side
    # `praxis_ready` field only ever means "the call returned", not "the boot
    # succeeded" -- it is True even for a boot that failed at the very first
    # stage. The only trustworthy success signal is whether `praxis:ready` was
    # actually posted on the BroadcastChannel (`broadcast_channel_ready_received`
    # below), and the only trustworthy failure reason is a `praxis:error` message
    # in `broadcast_channel_log`, not `kernel_result["bootstrap_error"]`.
    broadcast_error_reason = None
    for _log_entry in broadcast_log:
        data = _log_entry.get("data") if isinstance(_log_entry, dict) else None
        if isinstance(data, dict) and data.get("type") == "praxis:error":
            broadcast_error_reason = data.get("reason")
            break

    result: dict[str, Any] = dict(kernel_result)
    result["crossOriginIsolated"] = cross_origin_isolated
    result["http_errors"] = http_errors
    result["requestfailed"] = requestfailed
    result["pageerrors"] = pageerrors
    result["broadcast_channel_ready_received"] = ready_received
    result["broadcast_channel_auto_responses"] = auto_responses
    result["broadcast_channel_log"] = broadcast_log
    result["broadcast_channel_error_reason"] = broadcast_error_reason
    result["request_log"] = request_log
    result["request_log_count"] = len(request_log)
    result["console_messages_count"] = len(console_messages)
    result["offline_blackhole_verified"] = offline_blackhole_verified
    result["_meta"] = {
        "url": url,
        "entry": entry,
        "base_path": prefix,
        "coi": coi,
        "chrome_path": chrome_path,
        "timeout_s": timeout_s,
        "serve_dir": str(serve_dir),
        "offline": offline,
        "offline_blackhole_hosts": list(OFFLINE_BLACKHOLE_HOSTS) if offline else [],
    }
    return result


# ---------------------------------------------------------------------------
# --viz-check: the D3 golden-render check (spec 260817_spec-visualizer-transport-shim.md
# R9/T1.4). Browserless-Python, browser-required: no Python kernel of any kind runs on
# the page, but a real Chromium + Konva render is what measures shape_count/layer_count,
# which cannot be derived from the JSON payload alone (see gen_viz_fixtures.py's
# docstring on why resource_count CAN be Python-side but shape_count cannot).
# ---------------------------------------------------------------------------


class VizCheckError(RuntimeError):
    """Raised for any condition that must fail --viz-check loudly, pin mismatch included."""


def build_fresh_boot_probe_code() -> str:
    """In-kernel payload for the fresh-notebook bootstrap (gate T4).

    Runs EXACTLY what a user is told to type in a brand-new notebook -- `import
    praxis_boot` then `await praxis_boot.setup()` -- and nothing else. It
    deliberately does NOT fetch the loader itself or pass a host root, because
    those two omissions are the whole claim being tested: that a fresh kernel
    can reach the loader with no URL and no base path typed by hand.

    Records sys.path and cwd unconditionally. `import praxis_boot` only works
    because the kernel mounts the JupyterLite contents drive at /drive and runs
    there; if that ever stops being true the import fails, and the failure would
    be indistinguishable from "the file was not shipped" without these fields.
    """
    start_a, start_b = PROBE_START[: len(PROBE_START) // 2], PROBE_START[len(PROBE_START) // 2 :]
    end_a, end_b = PROBE_END[: len(PROBE_END) // 2], PROBE_END[len(PROBE_END) // 2 :]
    return textwrap.dedent(
        f"""
        import json, os, sys, traceback
        RESULT: dict = {{}}

        RESULT["cwd"] = os.getcwd()
        RESULT["sys_path_head"] = sys.path[:4]
        RESULT["drive_listing"] = (
            sorted(os.listdir("/drive")) if os.path.isdir("/drive") else None
        )

        # Baseline: a fresh kernel must NOT already have pylabrobot, or this
        # gate would pass without the bootstrap doing anything.
        try:
            import pylabrobot as _pre
            RESULT["plr_before"] = getattr(_pre, "__version__", "present")
        except Exception as e:  # noqa: BLE001
            RESULT["plr_before"] = f"{{type(e).__name__}}"

        try:
            import praxis_boot
            RESULT["import_praxis_boot"] = True
        except Exception as e:  # noqa: BLE001
            RESULT["import_praxis_boot"] = False
            RESULT["import_error"] = f"{{type(e).__name__}}: {{e}}"

        if RESULT.get("import_praxis_boot"):
            try:
                RESULT["derived_host_root"] = praxis_boot.derive_host_root()
            except Exception as e:  # noqa: BLE001
                RESULT["derived_host_root"] = None
                RESULT["derive_error"] = f"{{type(e).__name__}}: {{e}}"

            try:
                RESULT["setup_returned"] = await praxis_boot.setup()
                RESULT["setup_ok"] = True
            except Exception as e:  # noqa: BLE001
                RESULT["setup_ok"] = False
                RESULT["setup_error"] = f"{{type(e).__name__}}: {{e}}"
                RESULT["setup_traceback"] = traceback.format_exc()

            try:
                import builtins
                import pylabrobot
                from pylabrobot.io.serial import Serial
                RESULT["plr_after"] = getattr(pylabrobot, "__version__", None)
                RESULT["serial_is_shim"] = Serial is getattr(builtins, "WebSerial", None)
            except Exception as e:  # noqa: BLE001
                RESULT["plr_after"] = None
                RESULT["serial_is_shim"] = None
                RESULT["post_import_error"] = f"{{type(e).__name__}}: {{e}}"

        print({start_a!r} + {start_b!r})
        print(json.dumps(RESULT))
        print({end_a!r} + {end_b!r})
        """
    ).strip()


TYPEAHEAD_EDITOR_SELECTORS = (
    ".jp-CodeConsole-promptCell .cm-content",
    ".jp-InputArea-editor .cm-content",
    ".jp-CodeConsole-promptCell .CodeMirror",
    ".cm-content",
)


def run_typeahead_check(
    *,
    serve_dir: Path,
    base_path: str,
    chrome_path: str,
    timeout_s: float,
    entry: str = "repl",
    offline: bool = False,
) -> dict[str, Any]:
    """Assert the completer opens WITHOUT Tab -- the as-you-type gate (T3).

    This is the only tier that can see the frontend setting at all. The build
    assertion proves `autoCompletion: true` reached the runtime config; the
    in-kernel probe proves the kernel can complete. Neither can tell you whether
    the browser actually opens a completer on keystrokes, because that behaviour
    lives entirely in the JupyterLab completer plugin.

    Deliberately never presses Tab. Tab-completion already worked before this
    change, so a gate that pressed Tab would pass identically with the setting
    off -- it would assert nothing. The whole content of this check is that the
    popup appears from typing alone.
    """
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as e:  # pragma: no cover - environment problem
        raise RuntimeError(f"playwright is not importable: {e}") from e

    prefix = _normalize_base_path(base_path)
    timeout_ms = timeout_s * 1000
    result: dict[str, Any] = {"passed": False, "failures": []}

    # Split like every other sentinel here: the `code` param is echoed into the
    # cell BEFORE execution, so a contiguous literal would match the source.
    ready_code = "import sys\nprint('TYPEAHEAD' + '_READY')"

    with ServedDir(serve_dir, base_path, False) as served:
        url = f"http://127.0.0.1:{served.port}{prefix}{entry}/index.html"
        params = urllib.parse.urlencode(
            {"kernel": "python", "toolbar": "1", "execute": "1", "code": ready_code}
        )
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=chrome_path,
                headless=True,
                args=chromium_launch_args(offline=offline),
            )
            try:
                page = browser.new_context().new_page()
                page.goto(f"{url}?{params}", timeout=timeout_ms)
                page.wait_for_function(
                    "() => document.body.innerText.includes('TYPEAHEAD_READY')",
                    timeout=timeout_ms,
                )
                LOG.info("kernel is up (sys imported); locating the prompt editor")

                editor = None
                for sel in TYPEAHEAD_EDITOR_SELECTORS:
                    loc = page.locator(sel).last
                    try:
                        loc.wait_for(state="visible", timeout=5000)
                        editor = loc
                        result["editor_selector"] = sel
                        break
                    except PlaywrightTimeoutError:
                        continue
                if editor is None:
                    result["failures"].append(
                        "no prompt editor matched any of "
                        f"{list(TYPEAHEAD_EDITOR_SELECTORS)} -- the console DOM has "
                        "changed shape and this gate needs a new selector"
                    )
                    return result

                # Control: nothing should be open before we type. Without this a
                # stale/hidden completer node would make the assertion below pass
                # for the wrong reason.
                pre = page.locator(".jp-Completer").count()
                result["completer_nodes_before_typing"] = pre

                # Type an IDENTIFIER PREFIX after the dot, not a bare `sys.`.
                # Continuous hinting fires on identifier characters, and a `.` is
                # not one -- measured 2026-08-24: typing `sys` opens the popup,
                # the following `.` DISMISSES it, and `pa` reopens it. A gate that
                # stopped at the trailing dot therefore reported "no completer" on
                # a build where as-you-type was working perfectly. Do not "simplify"
                # this back to `sys.`.
                editor.click()
                page.keyboard.type("sys.pa", delay=80)
                LOG.info("typed 'sys.pa' with no Tab; waiting for the completer")

                try:
                    page.wait_for_selector(".jp-Completer", state="visible", timeout=15000)
                    result["completer_appeared"] = True
                except PlaywrightTimeoutError:
                    result["completer_appeared"] = False
                    result["failures"].append(
                        "the completer did not appear within 15s of typing 'sys.pa' "
                        "with no Tab pressed. Either autoCompletion is not in force "
                        "at runtime, or the kernel was too slow to answer within the "
                        "completer's providerTimeout (default 1000 ms)."
                    )
                    result["body_tail"] = page.inner_text("body")[-1500:]
                    return result

                items = page.locator(".jp-Completer .jp-Completer-item")
                result["completer_item_count"] = items.count()
                try:
                    result["completer_sample"] = [
                        items.nth(i).inner_text().strip() for i in range(min(6, items.count()))
                    ]
                except Exception:  # noqa: BLE001 - sample is diagnostics, not the assertion
                    result["completer_sample"] = None
                if not result["completer_item_count"]:
                    result["failures"].append(
                        "completer opened but listed 0 items -- it is rendering an "
                        "empty popup rather than completing"
                    )
            finally:
                browser.close()

    result["passed"] = not result["failures"]
    return result


def read_submodule_sha(submodule_dir: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(submodule_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise VizCheckError(f"could not read submodule HEAD at {submodule_dir}: {e.stderr}") from e
    return out.stdout.strip()


DEFAULT_NOTEBOOK = "welcome.ipynb"

#: Strings the welcome notebook must print. These are the notebook's own output,
#: not the harness's -- if the notebook's cells change, this list must change with
#: them, and that coupling is deliberate: it is what makes this a test OF the
#: notebook rather than a test that some notebook ran.
NOTEBOOK_EXPECTED = (
    "bootstrap complete",
    "PyLabRobot 0.2.2+g",
    "Serial is the browser shim: True",
)


class NotebookCheckError(RuntimeError):
    """Raised when the welcome notebook does not execute cleanly."""


def run_notebook_check(
    *,
    serve_dir: Path,
    base_path: str,
    chrome_path: str,
    timeout_s: float,
    notebook: str = DEFAULT_NOTEBOOK,
    offline: bool = False,
) -> dict[str, Any]:
    """Open the welcome notebook in the real lab app and RUN it.

    Why this mode exists: welcome.ipynb is the entry point every user lands on,
    and nothing had ever executed it. Its bootstrap cell is byte-identical to
    build_probe_code()'s, but "identical to something that works" is not the same
    as "works" -- the notebook also has to be staged into the built site, indexed
    in the contents API, openable, and runnable against a kernel it did not
    configure itself. None of that is exercised by --probe.

    Driven through the lab app's exposed command registry
    (`window.jupyterapp.commands.execute('notebook:run-all-cells')`), which
    `exposeAppInBrowser: "true"` in jupyter-lite.json makes available. The lab app
    has no `?code=&execute=1` parameter -- that is a REPL-app feature -- so
    clicking or command-dispatch is the only way to run cells there.
    """
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    prefix = _normalize_base_path(base_path)
    timeout_ms = timeout_s * 1000
    console_messages: list[dict[str, Any]] = []
    pageerrors: list[str] = []

    with ServedDir(serve_dir, base_path, coi=False) as served:
        url = (
            f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
            f"?path={urllib.parse.quote(notebook)}"
        )
        LOG.info("navigating to %s", url)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=chrome_path,
                headless=True,
                args=chromium_launch_args(offline=offline),
            )
            try:
                page = browser.new_context().new_page()
                page.on("pageerror", lambda exc: pageerrors.append(str(exc)))
                page.on(
                    "console",
                    lambda msg: console_messages.append({"type": msg.type, "text": msg.text}),
                )
                page.goto(url, wait_until="load", timeout=timeout_ms)

                # The app object and the notebook widget appear independently;
                # waiting on only one of them races the other.
                page.wait_for_function(
                    "() => !!window.jupyterapp && !!document.querySelector('.jp-Notebook')",
                    timeout=timeout_ms,
                )
                # JupyterLite prompts for kernel selection when opening a
                # notebook with no saved preference, and that dialog blocks
                # execution silently: run-all dispatches, resolves, and nothing
                # runs. Observed as a 150s timeout whose only clue was the words
                # "Select Kernel" in the page text. Accept the preselected kernel
                # (Python (Pyodide)) if the dialog is up.
                try:
                    page.wait_for_selector(".jp-Dialog", timeout=10_000)
                    LOG.info("kernel-selection dialog present; accepting")
                    page.click(".jp-Dialog .jp-mod-accept")
                    page.wait_for_selector(".jp-Dialog", state="detached", timeout=timeout_ms)
                except PlaywrightTimeoutError:
                    LOG.info("no kernel-selection dialog appeared")

                # Count from the MODEL, not the DOM: JupyterLab 4 renders
                # notebooks windowed, so document.querySelectorAll('.jp-Cell')
                # returns only the cells currently scrolled into view (measured: 1
                # of 8). A DOM count here looks like a truncated notebook.
                cell_count = page.evaluate(
                    """() => {
                        const w = window.jupyterapp?.shell?.currentWidget;
                        const cells = w?.content?.model?.cells;
                        const n = cells?.length ?? cells?.size;
                        return typeof n === 'number'
                            ? n
                            : document.querySelectorAll('.jp-Notebook .jp-Cell').length;
                    }"""
                )
                LOG.info("notebook open with %d cell(s); running all", cell_count)

                # Dispatch WITHOUT awaiting. The run-all promise does not settle
                # until every cell has finished, and a cell that blocks (or a
                # kernel that never becomes ready) leaves page.evaluate awaiting
                # forever -- page.evaluate has no implicit timeout, so the whole
                # run hangs with no diagnostic. Observed before this change: the
                # harness sat past 280s with nothing after "running all". Fire it
                # and poll the outputs, which is what we assert on anyway.
                run = page.evaluate(
                    """() => {
                        try {
                            const pr = window.jupyterapp.commands.execute(
                                'notebook:run-all-cells');
                            if (pr && typeof pr.catch === 'function') {
                                pr.catch(e => { window.__praxisRunAllError = String(e); });
                            }
                            return {dispatched: true};
                        } catch (e) {
                            return {dispatched: false, error: String(e)};
                        }
                    }"""
                )
                if not run.get("dispatched"):
                    raise NotebookCheckError(
                        f"could not dispatch notebook:run-all-cells: {run.get('error')!r}"
                    )

                # Read OUTPUTS from the notebook MODEL, never document.body.innerText.
                # Two independent reasons:
                #  1. The cell SOURCE is rendered in the DOM, so a body-text search
                #     for `bootstrap complete` matches the literal
                #     print("bootstrap complete") in cell 3 whether or not it ever
                #     ran. Measured: that needle reported found on a notebook whose
                #     kernel dialog was still open and which had executed nothing.
                #     This is the same false-positive class the probe's sentinels
                #     are split in half to avoid.
                #  2. JupyterLab 4 windows the notebook, so outputs of off-screen
                #     cells are not in the DOM at all -- a DOM-only read would miss
                #     real output for the opposite reason.
                # r-string: the JS below contains \n escapes that must reach the
                # browser as backslash-n, not as real newlines inside a string literal
                # (which is a JS SyntaxError -- "Invalid or unexpected token").
                collect_outputs = r"""() => {
                    const w = window.jupyterapp?.shell?.currentWidget;
                    const cells = w?.content?.model?.cells;
                    const n = cells?.length ?? cells?.size;
                    if (typeof n !== 'number') return null;
                    const chunks = [];
                    for (let i = 0; i < n; i++) {
                        const cell = cells.get ? cells.get(i) : cells[i];
                        const outs = cell?.outputs;
                        const m = outs?.length ?? 0;
                        for (let j = 0; j < m; j++) {
                            const o = outs.get ? outs.get(j) : outs[j];
                            const d = o?.toJSON ? o.toJSON() : o;
                            if (!d) continue;
                            if (typeof d.text === 'string') chunks.push(d.text);
                            else if (Array.isArray(d.text)) chunks.push(d.text.join(''));
                            if (d.data && typeof d.data['text/plain'] === 'string') {
                                chunks.push(d.data['text/plain']);
                            }
                            if (d.ename) chunks.push(d.ename + ': ' + d.evalue);
                            if (Array.isArray(d.traceback)) chunks.push(d.traceback.join('\n'));
                        }
                    }
                    return chunks.join('\n');
                }"""
                # Install the collector as a page global once, rather than
                # threading its source through wait_for_function and eval()-ing it
                # there -- that shape broke on the function body's own quoting
                # ("SyntaxError: Invalid or unexpected token") for no benefit.
                page.evaluate("() => { window.__praxisCollectOutputs = %s; }" % collect_outputs)
                try:
                    page.wait_for_function(
                        "(needles) => { const t = window.__praxisCollectOutputs(); "
                        "return t !== null && needles.every(n => t.includes(n)); }",
                        arg=list(NOTEBOOK_EXPECTED),
                        timeout=timeout_ms,
                    )
                    timed_out = False
                except PlaywrightTimeoutError:
                    timed_out = True

                outputs_text = page.evaluate("() => window.__praxisCollectOutputs() || ''") or ""
                body_text = page.evaluate("() => document.body.innerText")
                run_all_error = page.evaluate("() => window.__praxisRunAllError || null")
                found = {n: (n in outputs_text) for n in NOTEBOOK_EXPECTED}
                # A traceback in the rendered output is the single most useful
                # signal and is invisible to a needle check that only looks for
                # success strings.
                tracebacks = page.evaluate(
                    "() => Array.from(document.querySelectorAll("
                    "'.jp-OutputArea-output[data-mime-type=\"application/vnd.jupyter.stderr\"],"
                    " .jp-RenderedText.jp-mod-trusted')).map(e => e.innerText).filter("
                    "t => t.includes('Traceback') || t.includes('Error'))"
                )
                result: dict[str, Any] = {
                    "notebook": notebook,
                    "url": url,
                    "cell_count": cell_count,
                    "expected": list(NOTEBOOK_EXPECTED),
                    "found": found,
                    "all_found": all(found.values()),
                    "timed_out": timed_out,
                    "run_all_error": run_all_error,
                    "tracebacks": tracebacks,
                    "pageerrors": pageerrors,
                    "offline": offline,
                }
                if not result["all_found"]:
                    result["outputs_text"] = outputs_text[-3000:]
                    result["body_text_tail"] = body_text[-2000:]
                    result["console"] = console_messages
                return result
            finally:
                browser.close()


def run_viz_check(
    *,
    visualizer_dir: Path,
    fixture_dir: Path,
    plr_submodule: Path,
    chrome_path: str,
    timeout_s: float,
    record: bool,
    offline: bool = False,
) -> dict[str, Any]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as e:  # pragma: no cover - environment problem, not a check result
        raise RuntimeError(f"playwright is not importable: {e}") from e

    manifest_path = fixture_dir / "FIXTURE_MANIFEST.json"
    root_path = fixture_dir / "set_root_resource.json"
    initial_state_path = fixture_dir / "set_state.json"
    delta_path = fixture_dir / "delta_set_state.json"
    for p in (manifest_path, root_path, initial_state_path, delta_path):
        if not p.is_file():
            raise VizCheckError(
                f"missing fixture file {p}. Generate fixtures first: "
                "uv run python web-repl/scripts/gen_viz_fixtures.py"
            )

    manifest = json.loads(manifest_path.read_text())

    # THE PIN CHECK. This must run before anything else and must name both SHAs --
    # a fixture generated at one PyLabRobot pin checked against the vendored renderer
    # of a different pin is the exact landmine the spec calls out (485 KB / 164 KB /
    # 137 KB schema differences across candidate pins). Fail with a message that says
    # what to DO, not just that counts differed.
    live_sha = read_submodule_sha(plr_submodule)
    manifest_sha = manifest.get("pin_sha")
    if manifest_sha != live_sha:
        raise VizCheckError(
            f"fixture pin mismatch: fixture was generated at pin {manifest_sha}, "
            f"current external/pylabrobot pin is {live_sha} -- regenerate with "
            "`uv run python web-repl/scripts/gen_viz_fixtures.py`"
        )

    root_fixture = json.loads(root_path.read_text())
    initial_state_fixture = json.loads(initial_state_path.read_text())
    delta_fixture = json.loads(delta_path.read_text())
    expected = manifest["expected"]
    delta_spec = manifest["delta"]
    target_resource = delta_spec["target_resource"]
    fill_before = delta_spec["fill_before"]
    fill_after = delta_spec["fill_after"]

    pageerrors: list[str] = []
    console_errors: list[str] = []

    # Serve the PARENT directory, not visualizer_dir itself. index.html's last body
    # element is
    #     <script type="module" src="../visualizer-augmentations/index.js"></script>
    # so serving the visualizer directory AS root puts that path above the document
    # root, where it 404s. Until this was fixed, every --viz-check run loaded the
    # renderer with the augmentation module missing -- which the direct-injection
    # assertions could not notice, because they call window.receiveFromPython
    # themselves and never exercise the module. Serving the parent reproduces the
    # real dist/assets/ layout, where visualizer/ and visualizer-augmentations/ are
    # siblings.
    assets_dir = visualizer_dir.parent
    viz_name = visualizer_dir.name
    with ServedDir(assets_dir, "/", coi=False) as served:
        url = f"http://127.0.0.1:{served.port}/{viz_name}/index.html"
        LOG.info("navigating to %s (serving %s)", url, assets_dir)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=chrome_path,
                headless=True,
                args=chromium_launch_args(offline=offline),
            )
            try:
                context = browser.new_context()
                page = context.new_page()
                page.on("pageerror", lambda exc: pageerrors.append(str(exc)))
                page.on(
                    "console",
                    lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
                )

                page.goto(url, wait_until="load", timeout=timeout_s * 1000)
                # `stage`/`resources` are built inside lib.js's own `window` "load"
                # listener (lib.js:3207-3235) -- Playwright's wait_until="load" fires
                # after that listener has run, but poll explicitly rather than trust
                # event-ordering across two independent "load" consumers.
                page.wait_for_function(
                    "() => window.stage && window.stage.getLayers().length > 0",
                    timeout=timeout_s * 1000,
                )

                # --- inject set_root_resource ---
                ack = page.evaluate(
                    "async (data) => await window.receiveFromPython('set_root_resource', data)",
                    root_fixture,
                )
                if not ack or ack.get("success") is not True:
                    raise VizCheckError(f"set_root_resource injection failed: ack={ack!r}")

                # --- inject the INITIAL full set_state ---
                # Real boot always sends this immediately after set_root_resource
                # (Visualizer._send_resources_and_state, visualizer.py:643-670).
                # set_root_resource carries pure geometry; tip/liquid presence lives
                # only in per-resource state, so skipping straight to the delta below
                # made an earlier version of this check read BOTH fill_before and
                # fill_after as Konva's default fill -- a false pass that would have
                # masked the #1 pre-mortem risk (state updates silently dropped)
                # instead of catching it. See gen_viz_fixtures.py's docstring.
                ack0 = page.evaluate(
                    "async (data) => await window.receiveFromPython('set_state', data)",
                    initial_state_fixture,
                )
                if not ack0 or ack0.get("success") is not True:
                    raise VizCheckError(f"initial set_state injection failed: ack={ack0!r}")

                measured_resources = page.evaluate("() => Object.keys(window.resources).length")
                measured_shapes = page.evaluate("() => window.stage.find('Shape').length")
                measured_layers = page.evaluate("() => window.stage.getLayers().length")

                fill_before_actual = page.evaluate(
                    "(name) => { const r = window.resources[name]; "
                    "const c = r && r.group.findOne('Circle'); "
                    "return c ? c.fill() : null; }",
                    target_resource,
                )

                # --- inject delta_set_state ---
                ack2 = page.evaluate(
                    "async (data) => await window.receiveFromPython('set_state', data)",
                    delta_fixture,
                )
                if not ack2 or ack2.get("success") is not True:
                    raise VizCheckError(f"delta set_state injection failed: ack={ack2!r}")

                fill_after_actual = page.evaluate(
                    "(name) => { const r = window.resources[name]; "
                    "const c = r && r.group.findOne('Circle'); "
                    "return c ? c.fill() : null; }",
                    target_resource,
                )

                # --- P6.6: drive the SAME renderer through the praxis_viz channel ---
                # Everything above injects into window.receiveFromPython directly,
                # which proves the renderer works but says nothing about the
                # augmentation module that is supposed to feed it in production.
                # This stage posts a real PLR envelope onto the channel from a
                # SECOND BroadcastChannel instance (a channel never receives its own
                # messages, so a second instance is required) and asserts the render
                # actually changed -- counters alone would pass even if the payload
                # never reached Konva.
                #
                # It restores the INITIAL state, so the assertion is that fill goes
                # back to fill_before: a real, observable reversal of the delta the
                # direct injection just applied.
                aug_before = page.evaluate(
                    "() => globalThis.__praxisVisualizerAugmentations || null"
                )
                dispatched_before = (aug_before or {}).get("dispatched", 0)
                page.evaluate(
                    """(payload) => {
                        const ch = new BroadcastChannel('praxis_viz');
                        ch.postMessage(payload);
                        ch.close();
                    }""",
                    json.dumps(
                        {
                            "id": 9001,
                            "version": "praxis-viz-check",
                            "event": "set_state",
                            "data": initial_state_fixture,
                        }
                    ),
                )
                # Bounded, NON-raising wait. A hard wait_for_function here aborts
                # the run with a bare "Timeout 120000ms exceeded" and the
                # informative checks below never execute -- observed by deleting
                # dist/assets/visualizer-augmentations/ and watching a 2-minute
                # unattributed stack trace replace the one-line "module did not
                # load" diagnosis. Channel delivery is sub-second when it works at
                # all, so a short budget is right: swallow the timeout and let the
                # failure block say WHY.
                try:
                    page.wait_for_function(
                        "(n) => ((globalThis.__praxisVisualizerAugmentations || {})"
                        ".dispatched || 0) > n",
                        arg=dispatched_before,
                        timeout=CHANNEL_DISPATCH_TIMEOUT_S * 1000,
                    )
                except PlaywrightTimeoutError:
                    LOG.error(
                        "no praxis_viz envelope dispatched within %.0fs -- "
                        "continuing so the reason is reported rather than a bare "
                        "timeout",
                        CHANNEL_DISPATCH_TIMEOUT_S,
                    )
                augmentations = page.evaluate(
                    "() => globalThis.__praxisVisualizerAugmentations"
                )
                fill_after_channel = page.evaluate(
                    "(name) => { const r = window.resources[name]; "
                    "const c = r && r.group.findOne('Circle'); "
                    "return c ? c.fill() : null; }",
                    target_resource,
                )
            finally:
                browser.close()

    result: dict[str, Any] = {
        "pin_sha": live_sha,
        "measured": {
            "resource_count": measured_resources,
            "shape_count": measured_shapes,
            "layer_count": measured_layers,
        },
        "expected": dict(expected),
        "delta": {
            "target_resource": target_resource,
            "fill_before_expected": fill_before,
            "fill_before_actual": fill_before_actual,
            "fill_after_expected": fill_after,
            "fill_after_actual": fill_after_actual,
        },
        "channel": {
            "augmentations": augmentations,
            "fill_after_channel_actual": fill_after_channel,
            "fill_after_channel_expected": fill_before,
        },
        "pageerrors": pageerrors,
        "console_errors": console_errors,
        "record_mode": record,
    }

    failures: list[str] = []

    if pageerrors:
        failures.append(f"{len(pageerrors)} pageerror(s): {pageerrors}")

    # P6.6 channel path. Checked here rather than inline so a failure is reported
    # alongside every other measurement instead of aborting the run.
    if not augmentations:
        failures.append(
            "visualizer-augmentations module did not load: "
            "globalThis.__praxisVisualizerAugmentations is absent. The renderer "
            "would receive nothing from the kernel."
        )
    else:
        if augmentations.get("noop"):
            failures.append(
                "visualizer-augmentations is still the pre-Phase-6 NO-OP stub "
                "(noop=true); it does not listen on praxis_viz at all."
            )
        if augmentations.get("errors"):
            failures.append(
                f"augmentation reported errors: {augmentations['errors']}"
            )
        if not augmentations.get("dispatched"):
            failures.append(
                "no envelope was dispatched to the renderer over praxis_viz "
                f"(received={augmentations.get('received')}). BroadcastChannel is "
                "origin-scoped and drops cross-origin posts SILENTLY."
            )
    if fill_after_channel != fill_before:
        failures.append(
            f"channel-driven set_state did not reach Konva: {target_resource} fill "
            f"is {fill_after_channel!r}, expected the restored {fill_before!r}. "
            "Counters can increment while the payload never renders."
        )

    if measured_resources != expected["resource_count"]:
        failures.append(
            f"resource_count mismatch: measured {measured_resources}, "
            f"expected {expected['resource_count']} (pin {live_sha})"
        )

    if record:
        expected["shape_count"] = measured_shapes
        expected["layer_count"] = measured_layers
        manifest["expected"] = expected
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        LOG.info(
            "RECORDED shape_count=%d layer_count=%d into %s",
            measured_shapes,
            measured_layers,
            manifest_path,
        )
    else:
        if expected.get("shape_count") is None or expected.get("layer_count") is None:
            failures.append(
                "shape_count/layer_count have never been recorded for this fixture -- "
                "run `uv run python scripts/repl_smoke.py --viz-check --record` once "
                "(with sandbox disabled) before this check can gate anything"
            )
        else:
            if measured_shapes != expected["shape_count"]:
                failures.append(
                    f"shape_count mismatch: measured {measured_shapes}, "
                    f"expected {expected['shape_count']} (pin {live_sha}, recorded "
                    f"{manifest.get('generated_at')}) -- if this is a real upstream "
                    "render change, re-record with --viz-check --record; if it is a "
                    "regression, that is exactly what this gate exists to catch"
                )
            if measured_layers != expected["layer_count"]:
                failures.append(
                    f"layer_count mismatch: measured {measured_layers}, "
                    f"expected {expected['layer_count']} (pin {live_sha})"
                )

    if fill_before_actual != fill_before:
        failures.append(
            f"{target_resource} fill BEFORE delta: measured {fill_before_actual!r}, "
            f"expected {fill_before!r}"
        )
    if fill_after_actual != fill_after:
        failures.append(
            f"{target_resource} fill AFTER delta: measured {fill_after_actual!r}, "
            f"expected {fill_after!r} -- a value equal to fill_before here is the "
            "documented failure signature (state delta silently dropped)"
        )

    result["failures"] = failures
    result["passed"] = not failures
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--probe",
        action="store_true",
        help="Run the full in-kernel probe and print JSON to stdout.",
    )
    p.add_argument(
        "--notebook-check",
        action="store_true",
        help=(
            "Open web-repl/files/<--notebook> in the REAL lab app and run every "
            "cell, asserting the notebook's own printed output. --probe cannot "
            "cover this: it injects its payload via the REPL app's ?code= "
            "parameter, so it never exercises the notebook being staged, indexed "
            "in the contents API, opened, or run against a kernel it did not "
            "configure. Driven via window.jupyterapp's command registry."
        ),
    )
    p.add_argument(
        "--notebook",
        default=DEFAULT_NOTEBOOK,
        help=f"--notebook-check only. Notebook path within the site. Default: {DEFAULT_NOTEBOOK}",
    )
    p.add_argument(
        "--completion-check",
        action="store_true",
        help=(
            "Measure the REPL's code completion in a REAL kernel (gate T2): whether "
            "jedi is resident, whether IPython latched onto it, and how long a cold "
            "completion takes against the frontend's 1000 ms providerTimeout. Reports "
            "the numbers; --require-jedi turns the jedi half into an assertion."
        ),
    )
    p.add_argument(
        "--fresh-boot-check",
        action="store_true",
        help=(
            "Assert a BRAND-NEW notebook can bootstrap with two lines and no hand-typed "
            "URL (gate T4): `import praxis_boot` then `await praxis_boot.setup()`, then "
            "check pylabrobot imports AND that its Serial is the browser shim. "
            "--notebook-check cannot cover this: it runs welcome.ipynb, which carries "
            "its own stamped HOST_ROOT and its own fetch-and-exec cell."
        ),
    )
    p.add_argument(
        "--typeahead-check",
        action="store_true",
        help=(
            "Assert the completer opens from TYPING ALONE, no Tab (gate T3). The only "
            "check that can see the frontend `autoCompletion` setting: the build "
            "assertion sees the config and --completion-check sees the kernel, but "
            "neither can tell whether the browser opens a popup on keystrokes."
        ),
    )
    p.add_argument(
        "--require-jedi",
        action="store_true",
        help=(
            "--completion-check only. FAIL unless jedi is resident and IPython is "
            "using it. Off by default so the same command measures the pre-change "
            "baseline; CI turns it on once the preload has landed."
        ),
    )
    p.add_argument(
        "--max-completion-ms",
        type=float,
        default=None,
        help=(
            "--completion-check only. FAIL if the COLD completion exceeds this many "
            "milliseconds. Left unset by default because the threshold is a judgement "
            "against a measurement, not a constant to bake in blind."
        ),
    )
    p.add_argument(
        "--viz-check",
        action="store_true",
        help=(
            "Run the browserless-Python visualizer render check (gate D3) instead of "
            "--probe: inject the golden fixture into the vendored visualizer directly, "
            "no JupyterLite kernel involved. See --record, --visualizer-dir, "
            "--fixture-dir, --plr-submodule."
        ),
    )
    p.add_argument(
        "--record",
        action="store_true",
        help=(
            "--viz-check only. Measure shape_count/layer_count from this run's real "
            "Konva render and WRITE them into FIXTURE_MANIFEST.json instead of "
            "asserting against previously-recorded values. Run once after every "
            "fixture regen (gen_viz_fixtures.py); every other run should omit this."
        ),
    )
    p.add_argument(
        "--visualizer-dir",
        type=Path,
        default=DEFAULT_VISUALIZER_DIR,
        help=f"--viz-check only. Directory containing the vendored visualizer's index.html. Default: {DEFAULT_VISUALIZER_DIR}",
    )
    p.add_argument(
        "--fixture-dir",
        type=Path,
        default=DEFAULT_FIXTURE_DIR,
        help=f"--viz-check only. Directory containing set_root_resource.json, set_state.json, delta_set_state.json, FIXTURE_MANIFEST.json. Default: {DEFAULT_FIXTURE_DIR}",
    )
    p.add_argument(
        "--plr-submodule",
        type=Path,
        default=DEFAULT_PLR_SUBMODULE,
        help=f"--viz-check only. Path to the pylabrobot submodule, read-only, for the pin-match check. Default: {DEFAULT_PLR_SUBMODULE}",
    )
    p.add_argument(
        "--expect-fail",
        metavar="ExceptionName",
        default=None,
        help=(
            "Assert that the run failed with an exception whose name matches this "
            "(checked against bootstrap_error and the full result JSON). Exit 0 if "
            "matched, 1 otherwise. Used for GATE 3's negative runs."
        ),
    )
    p.add_argument(
        "--serve-dir",
        type=Path,
        default=DEFAULT_SERVE_DIR,
        help=f"Directory to serve. Default: {DEFAULT_SERVE_DIR}",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        help=f"Timeout in seconds for navigation + probe completion. Default: {DEFAULT_TIMEOUT_S}",
    )
    p.add_argument(
        "--chrome-path",
        default=None,
        help=(
            "Path to a Chromium executable. When omitted, resolution order is "
            f"${CHROME_PATH_ENV_VAR}, then Playwright's own bundled Chromium (what "
            "`playwright install chromium` produces, and the only one present in CI), "
            f"then this box's 1228 build ({LOCAL_FALLBACK_CHROME_PATH}) -- playwright "
            "1.62.0 wants build 1234, which is not installed here."
        ),
    )
    p.add_argument(
        "--coi",
        action="store_true",
        help=(
            "Serve behind COOP: same-origin + COEP: credentialless -- web-repl/dist/ has "
            "no client-side coi-serviceworker.js of its own (unlike the pre-move "
            "praxis/web-client/src/index.html:9-22), so these are the only COI headers "
            "available -- instead of a bare http.server."
        ),
    )
    p.add_argument(
        "--base-path",
        default="/",
        help="URL path prefix to serve under. Use /praxis/ to mimic GH Pages. Default: /",
    )
    p.add_argument(
        "--expect-praxis-sha",
        default=None,
        help="Expected praxis_git_sha for the D1 whole-deployment staleness check.",
    )
    p.add_argument(
        "--entry",
        choices=["lab", "repl"],
        default="repl",
        help=(
            "Which built app to navigate to (dist/<entry>/index.html). Default 'repl': "
            "this harness drives the kernel via `?code=&execute=1`, which is a REPL-app "
            "URL parameter. The lab app has no such parameter, so --entry lab hangs at "
            "the 120s wait_for_function regardless of how healthy the build is -- that "
            "is a property of JupyterLite's lab app, not a boot failure. "
            "inject_shell.py now injects the D1 shell into EVERY dist/*/index.html, so "
            "both entries carry window.PRAXIS_GIT_SHA (corrected 260818; the previous "
            "help text here claimed repl had none, which was true only while injection "
            "was lab-only)."
        ),
    )
    p.add_argument(
        "--offline",
        action="store_true",
        help=(
            "Blackhole "
            + ", ".join(OFFLINE_BLACKHOLE_HOSTS)
            + f" to {OFFLINE_BLACKHOLE_TARGET} via chromium --host-resolver-rules, then "
            "require the site to boot anyway (GATE G5's offline clause). Implies a "
            "non-vacuity self-test: the run FAILS if a blackholed host turns out to be "
            "reachable, because a green boot with inert rules is indistinguishable from a "
            "genuinely self-contained one. NOTE: resolver rules, never page.route() -- "
            "route() does not intercept Web Worker requests and the kernel is a worker."
        ),
    )
    p.add_argument("--out", type=Path, default=None, help="Also write the JSON result to this path.")
    p.add_argument("-v", "--verbose", action="store_true", help="Enable DEBUG logging.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    if (
        not args.probe
        and not args.viz_check
        and not args.notebook_check
        and not args.completion_check
        and not args.typeahead_check
        and not args.fresh_boot_check
        and not args.expect_fail
    ):
        LOG.error(
            "nothing to do: pass --probe, --viz-check, --notebook-check, "
            "--completion-check, --typeahead-check, --fresh-boot-check, "
            "and/or --expect-fail"
        )
        return 2

    try:
        chrome_path = resolve_chrome_path(args.chrome_path)
    except FileNotFoundError as exc:
        LOG.error("%s", exc)
        return 2
    LOG.info("using chromium at %s", chrome_path)

    if args.notebook_check:
        serve_dir = args.serve_dir.resolve()
        if not serve_dir.is_dir():
            LOG.error("--serve-dir does not exist or is not a directory: %s", serve_dir)
            return 2
        try:
            result = run_notebook_check(
                serve_dir=serve_dir,
                base_path=args.base_path,
                chrome_path=str(chrome_path),
                timeout_s=args.timeout,
                notebook=args.notebook,
                offline=args.offline,
            )
        except Exception as e:  # noqa: BLE001
            LOG.error("notebook-check failed: %s: %s", type(e).__name__, e)
            LOG.error(
                "If this is a Chromium launch failure ('apply-seccomp: unshare(CLONE_NEWUSER)'), "
                "this script must be invoked with the Bash sandbox disabled "
                "(dangerouslyDisableSandbox=true) — see plan section 5.6."
            )
            return 1

        output = json.dumps(result, indent=2, sort_keys=True)
        print(output)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(output)
            LOG.info("wrote result to %s", args.out)

        if result["pageerrors"]:
            LOG.error("notebook-check: %d pageerror(s): %s", len(result["pageerrors"]), result["pageerrors"])
            return 1
        if result["tracebacks"]:
            LOG.error("notebook-check: a cell raised:\n%s", "\n".join(result["tracebacks"])[:2000])
            return 1
        if not result["all_found"]:
            missing = [k for k, v in result["found"].items() if not v]
            LOG.error(
                "notebook-check FAILED: %s did not print %r. The notebook opened "
                "with %d cell(s) and run-all was dispatched, so this is the "
                "notebook's own execution failing, not the harness.",
                result["notebook"], missing, result["cell_count"],
            )
            return 1
        LOG.info(
            "notebook-check PASSED: %s ran %d cell(s) and printed all %d expected "
            "output(s).", result["notebook"], result["cell_count"], len(NOTEBOOK_EXPECTED),
        )
        return 0

    if args.viz_check:
        visualizer_dir = args.visualizer_dir.resolve()
        if not visualizer_dir.is_dir():
            LOG.error("--visualizer-dir does not exist or is not a directory: %s", visualizer_dir)
            return 2
        try:
            result = run_viz_check(
                visualizer_dir=visualizer_dir,
                fixture_dir=args.fixture_dir.resolve(),
                plr_submodule=args.plr_submodule.resolve(),
                chrome_path=str(chrome_path),
                timeout_s=args.timeout,
                record=args.record,
                offline=args.offline,
            )
        except (VizCheckError, RuntimeError) as e:
            LOG.error("viz-check failed: %s: %s", type(e).__name__, e)
            LOG.error(
                "If this is a Chromium launch failure ('apply-seccomp: unshare(CLONE_NEWUSER)'), "
                "this script must be invoked with the Bash sandbox disabled "
                "(dangerouslyDisableSandbox=true) — see plan section 5.6."
            )
            return 1

        output = json.dumps(result, indent=2, sort_keys=True)
        print(output)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(output)
            LOG.info("wrote result to %s", args.out)

        if not result["passed"]:
            for f in result["failures"]:
                LOG.error("FAIL: %s", f)
            return 1
        LOG.info("viz-check PASSED")
        return 0

    if args.fresh_boot_check:
        serve_dir = args.serve_dir.resolve()
        if not serve_dir.is_dir():
            LOG.error("--serve-dir does not exist or is not a directory: %s", serve_dir)
            return 2
        try:
            result = run_probe(
                serve_dir=serve_dir,
                base_path=args.base_path,
                coi=args.coi,
                chrome_path=str(chrome_path),
                timeout_s=args.timeout,
                expect_praxis_sha=None,
                entry=args.entry,
                offline=args.offline,
                code_override=build_fresh_boot_probe_code(),
            )
        except Exception as e:  # noqa: BLE001
            LOG.error("fresh-boot-check run failed: %s: %s", type(e).__name__, e)
            return 2

        if args.out:
            args.out.write_text(json.dumps(result, indent=2) + "\n")
            LOG.info("wrote result to %s", args.out)

        expected_root = _normalize_base_path(args.base_path)
        LOG.info(
            "fresh boot: cwd=%s import_praxis_boot=%s derived_host_root=%s (expected %s)",
            result.get("cwd"),
            result.get("import_praxis_boot"),
            result.get("derived_host_root"),
            expected_root,
        )
        LOG.info(
            "fresh boot: plr_before=%s plr_after=%s serial_is_shim=%s",
            result.get("plr_before"),
            result.get("plr_after"),
            result.get("serial_is_shim"),
        )

        failures: list[str] = []
        if result.get("plr_before") != "ModuleNotFoundError":
            failures.append(
                f"pylabrobot was ALREADY importable before the bootstrap "
                f"(plr_before={result.get('plr_before')!r}), so this gate would pass "
                "without praxis_boot doing anything. The premise is broken, not the fix."
            )
        if not result.get("import_praxis_boot"):
            failures.append(
                f"`import praxis_boot` failed: {result.get('import_error')}. It is "
                f"importable only because the kernel runs in the contents drive "
                f"(cwd={result.get('cwd')!r}, sys.path head "
                f"{result.get('sys_path_head')!r}, /drive={result.get('drive_listing')!r}) "
                "-- either the file was not shipped into web-repl/files/ or that "
                "assumption no longer holds."
            )
        if result.get("derived_host_root") != expected_root:
            failures.append(
                f"derived host root {result.get('derived_host_root')!r} != expected "
                f"{expected_root!r} ({result.get('derive_error')}). A wrong root 404s "
                "the loader fetch, which is the whole failure this removes."
            )
        if not result.get("setup_ok"):
            failures.append(
                f"praxis_boot.setup() raised: {result.get('setup_error')}"
            )
        if not result.get("serial_is_shim"):
            failures.append(
                "pylabrobot's Serial is NOT the browser shim after setup, so device "
                "I/O would silently use desktop pyserial. Note praxis_main() never "
                "re-raises, so this can only be caught by checking, not by awaiting."
            )

        if failures:
            for f in failures:
                LOG.error("FAIL: %s", f)
            return 1
        LOG.info(
            "fresh-boot-check PASSED: two lines in a bare kernel produced PyLabRobot %s "
            "with browser shims bound",
            result.get("plr_after"),
        )
        return 0

    if args.typeahead_check:
        serve_dir = args.serve_dir.resolve()
        if not serve_dir.is_dir():
            LOG.error("--serve-dir does not exist or is not a directory: %s", serve_dir)
            return 2
        try:
            result = run_typeahead_check(
                serve_dir=serve_dir,
                base_path=args.base_path,
                chrome_path=str(chrome_path),
                timeout_s=args.timeout,
                entry=args.entry,
                offline=args.offline,
            )
        except Exception as e:  # noqa: BLE001
            LOG.error("typeahead-check run failed: %s: %s", type(e).__name__, e)
            return 2

        if args.out:
            args.out.write_text(json.dumps(result, indent=2) + "\n")
            LOG.info("wrote result to %s", args.out)

        LOG.info(
            "typeahead: appeared=%s items=%s sample=%s (editor=%s)",
            result.get("completer_appeared"),
            result.get("completer_item_count"),
            result.get("completer_sample"),
            result.get("editor_selector"),
        )
        if not result["passed"]:
            for f in result["failures"]:
                LOG.error("FAIL: %s", f)
            return 1
        LOG.info("typeahead-check PASSED (completer opened with no Tab pressed)")
        return 0

    if args.completion_check:
        serve_dir = args.serve_dir.resolve()
        if not serve_dir.is_dir():
            LOG.error("--serve-dir does not exist or is not a directory: %s", serve_dir)
            return 2
        try:
            result = run_probe(
                serve_dir=serve_dir,
                base_path=args.base_path,
                coi=args.coi,
                chrome_path=str(chrome_path),
                timeout_s=args.timeout,
                expect_praxis_sha=None,
                entry=args.entry,
                offline=args.offline,
                code_override=build_completion_probe_code(
                    _normalize_base_path(args.base_path)
                ),
            )
        except Exception as e:  # noqa: BLE001
            LOG.error("completion-check run failed: %s: %s", type(e).__name__, e)
            LOG.error(
                "If this is a Chromium launch failure ('apply-seccomp: "
                "unshare(CLONE_NEWUSER)'), this script must be invoked with the Bash "
                "sandbox disabled (dangerouslyDisableSandbox=true)."
            )
            return 2

        if args.out:
            args.out.write_text(json.dumps(result, indent=2) + "\n")
            LOG.info("wrote result to %s", args.out)

        cold = result.get("plr_cold") or {}
        warm = result.get("plr_warm") or {}
        light = result.get("sys_light") or {}
        LOG.info(
            "completion: jedi_installed=%s use_jedi=%s jedi_version=%s",
            result.get("jedi_installed"),
            result.get("use_jedi"),
            result.get("jedi_version"),
        )
        LOG.info(
            "latency ms: LiquidHandler. cold=%s warm=%s | sys. light=%s",
            cold.get("ms"), warm.get("ms"), light.get("ms"),
        )
        LOG.info(
            "matches: cold n=%s sample=%s", cold.get("n"), cold.get("sample")
        )

        failures: list[str] = []
        if not result.get("completer_reachable"):
            failures.append(
                "could not reach the kernel's IPython shell, so NOTHING here was "
                "measured -- treat the latency fields as absent, not as fast"
            )
        if cold.get("error"):
            failures.append(f"cold completion raised: {cold['error']}")
        elif not cold.get("n"):
            failures.append(
                "cold completion returned 0 matches for 'LiquidHandler.' -- the "
                "completer is reachable but producing nothing"
            )
        if args.require_jedi:
            if not result.get("jedi_installed"):
                failures.append(
                    "--require-jedi: jedi is NOT resident in the kernel. It must be "
                    "loaded BEFORE IPython imports (loadPyodideOptions.packages), "
                    "because IPython latches JEDI_INSTALLED at module import."
                )
            elif not result.get("use_jedi"):
                failures.append(
                    "--require-jedi: jedi is resident but IPython is not using it "
                    "(use_jedi False) -- load order is wrong, not the package set."
                )
        if args.max_completion_ms is not None and cold.get("ms") is not None:
            if cold["ms"] > args.max_completion_ms:
                failures.append(
                    f"cold completion {cold['ms']} ms exceeds "
                    f"--max-completion-ms {args.max_completion_ms}"
                )

        if failures:
            for f in failures:
                LOG.error("FAIL: %s", f)
            return 1
        LOG.info("completion-check PASSED")
        return 0

    serve_dir = args.serve_dir.resolve()
    if not serve_dir.is_dir():
        LOG.error("--serve-dir does not exist or is not a directory: %s", serve_dir)
        return 2

    try:
        result = run_probe(
            serve_dir=serve_dir,
            base_path=args.base_path,
            coi=args.coi,
            chrome_path=str(chrome_path),
            timeout_s=args.timeout,
            expect_praxis_sha=args.expect_praxis_sha,
            entry=args.entry,
            offline=args.offline,
        )
    except Exception as e:
        LOG.error("probe run failed: %s: %s", type(e).__name__, e)
        LOG.error(
            "If this is a Chromium launch failure ('apply-seccomp: unshare(CLONE_NEWUSER)'), "
            "this script must be invoked with the Bash sandbox disabled "
            "(dangerouslyDisableSandbox=true) — see plan section 5.6."
        )
        return 1

    output = json.dumps(result, indent=2, sort_keys=True)
    print(output)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output)
        LOG.info("wrote result to %s", args.out)

    if args.expect_fail:
        haystack = json.dumps(result)
        got_error = result.get("bootstrap_error") or ""
        got_broadcast_error = result.get("broadcast_channel_error_reason") or ""
        # `broadcast_channel_error_reason` is `str(exc)` from praxis_bootstrap.py's
        # `_post({"type": "praxis:error", "reason": str(exc)})` -- it carries the
        # exception's MESSAGE, never its class name (verified 2026-08-18: neither
        # transport.py nor stages.py's raise sites put the class name in the message
        # text). `kernel_result["bootstrap_error"]` never fires either, because
        # `praxis_main()`'s own outer `except Exception` (praxis_bootstrap.py:337,
        # "fail-closed catch-all, by design") swallows everything and never
        # re-raises to this probe's caller. So a bare class-name --expect-fail can
        # only match by the `in haystack` fallback, which is fragile. This table
        # maps each class to a message PREFIX verified directly against its one
        # raise site in transport.py / stages.py, for a real positive match instead
        # of an accidental substring hit.
        _KNOWN_MESSAGE_PREFIXES: dict[str, tuple[str, ...]] = {
            "PraxisUnavailableError": (
                "manifest fetch failed:",  # transport.py fetch_manifest, 404
                "source fetch failed:",  # transport.py fetch_sources, 404
                "D1 praxis:shell-ping timed out",  # transport.py shell_ping, no shell
            ),
            "PraxisDriftError": (
                "D2 source sha256 mismatch:",  # transport.py fetch_sources
                "D1 whole-deployment staleness check",  # stages.py assert_praxis_git_sha
            ),
        }
        matched_by_message = any(
            got_broadcast_error.startswith(prefix)
            for prefix in _KNOWN_MESSAGE_PREFIXES.get(args.expect_fail, ())
        )
        matched = (
            got_error.startswith(args.expect_fail)
            or matched_by_message
            or (args.expect_fail in haystack)
        )
        if matched:
            LOG.info("--expect-fail %s: matched", args.expect_fail)
            return 0
        LOG.error(
            "--expect-fail %s: NOT observed (bootstrap_error=%r, "
            "broadcast_channel_error_reason=%r, broadcast_channel_ready_received=%r)",
            args.expect_fail,
            got_error,
            got_broadcast_error,
            result.get("broadcast_channel_ready_received"),
        )
        return 1

    # Default success criterion for --probe. Without this the command printed its
    # JSON and returned 0 UNCONDITIONALLY: a site whose bootstrap raised -- a
    # tampered loader, a 404, a drift error -- was reported as a clean pass by exit
    # code alone, and only --offline enforced anything. Found 260820 by tampering
    # with dist/bootstrap/stages.py to test the new loader sha pin: the pin
    # correctly refused to execute the modified file, and this harness still
    # exited 0. --expect-fail returns before this point, so a deliberately-failing
    # run is unaffected.
    if result.get("broadcast_channel_ready_received") is not True:
        LOG.error(
            "PROBE FAILED: the site did not boot "
            "(broadcast_channel_ready_received=%r). praxis_ready=%r "
            "bootstrap_error=%r broadcast_channel_error_reason=%r",
            result.get("broadcast_channel_ready_received"),
            result.get("praxis_ready"),
            result.get("bootstrap_error"),
            result.get("broadcast_channel_error_reason"),
        )
        return 1

    if args.offline:
        # Two conditions, and BOTH are load-bearing. The blackhole must be proven
        # live (else a green boot proves nothing -- see the self-test comment in
        # run_probe), and the site must actually have booted with it live (else we
        # proved only that the rules work, not that the site survives them).
        verified = result.get("offline_blackhole_verified")
        booted = result.get("broadcast_channel_ready_received")
        if verified is not True:
            LOG.error(
                "--offline: blackhole NOT in force -- %s was reachable despite "
                "--host-resolver-rules (offline_blackhole_verified=%r). The offline "
                "gate would have passed vacuously; treating as FAIL.",
                OFFLINE_BLACKHOLE_HOSTS[0],
                verified,
            )
            return 1
        if booted is not True:
            LOG.error(
                "--offline: blackhole is live, but the site did NOT boot "
                "(broadcast_channel_ready_received=%r, error=%r). Something in the "
                "boot path genuinely needs one of: %s.",
                booted,
                result.get("broadcast_channel_error_reason"),
                ", ".join(OFFLINE_BLACKHOLE_HOSTS),
            )
            return 1
        LOG.info(
            "--offline PASSED: %s blackholed to %s and site booted anyway.",
            ", ".join(OFFLINE_BLACKHOLE_HOSTS),
            OFFLINE_BLACKHOLE_TARGET,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
