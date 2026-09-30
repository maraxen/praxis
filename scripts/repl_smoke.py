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

  --display-check  ADDED for the notebook display epic (260929_notebook-display-design, D16,
                  tasks A7 and B10): scenarios D1 (Light), D1-dark (sprint A) and D2, D3, D4
                  (sprint B: reprs, error panels, staleness, keyboard, trust loss, High
                  Contrast), each its own unit in its own process with its own watchdog,
                  result and stamp, resumable. See the
                  "--display-check" section above `parse_args`.

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
import base64
import contextlib
import dataclasses
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import traceback
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

#: Shared forbidden-list (spec .praxia/docs/specs/260914_first-run-auto-setup.md,
#: AC-10 / section 8.3 / section 8.4 trap 1): a probe or shipped notebook code
#: cell that calls any of these itself would make auto-setup gates pass even
#: with auto-setup entirely broken. Deliberately excludes a bare `setup(` so
#: PyLabRobot's own `await lh.setup()` stays allowed. The build-side copy of
#: this same list lives in web-repl/scripts/build_repl.py (T5, out of this
#: task's scope) and web-repl/tests/test_base_path.py (T5/T6) -- kept as a
#: separate literal there rather than imported, since repl_smoke.py is not on
#: the build's import path.
FORBIDDEN_BOOTSTRAP_CALLS: tuple[str, ...] = ("praxis_main(", "praxis_boot.setup(", "HOST_ROOT =")

#: Import lines that would make AC-1's playground-names clause pass vacuously
#: (spec section 8.3, --fresh-boot-check row, T3b): the whole point of that
#: clause is that LiquidHandler/STAR are resolvable with NO import.
PLAYGROUND_NAME_IMPORT_NEEDLES: tuple[str, ...] = (
    "import LiquidHandler",
    "from pylabrobot.liquid_handling",
    "from pylabrobot.legacy.liquid_handling",
)


def find_forbidden_bootstrap_call(source: str) -> str | None:
    """Return the first shared-forbidden-list substring found in *source*, or None."""
    for needle in FORBIDDEN_BOOTSTRAP_CALLS:
        if needle in source:
            return needle
    return None


def probe_imports_playground_names(source: str) -> bool:
    """True if *source* imports LiquidHandler/STAR itself (spec section 8.3, T3b)."""
    return any(needle in source for needle in PLAYGROUND_NAME_IMPORT_NEEDLES)


@dataclasses.dataclass
class Fault:
    """One ServedDir fault (spec section 8.3, --autosetup-fault-check row).

    kind:
      - "404"    -- answer with an HTTP 404 instead of serving the file.
      - "tamper" -- serve the real file with corrupted bytes appended, so a
        sha256 pin over the served content mismatches.
      - "delay"  -- sleep `delay_s` in the handler thread, then serve the file
        unmodified. **Never put this on a sync-XHR asset**
        (`bootstrap/praxis_bootstrap.py`, `bootstrap/stages.py`,
        `bootstrap/transport.py`, `assets/wheels/manifest.json`, the
        `assets/python`/`assets/shims` sources): a sync XHR blocks the worker
        thread and would delay kernel-ready itself, so a probe cell would
        never observe `state == "running"` (test-design trap 8). Delays only
        ever target the async micropip wheel fetch.

    `suffix` is matched against `urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)`
    (C-17: `unquote`, not `unquote_plus`, so a literal `+` in a wheel filename
    survives). `max_hits` bounds how many of the FIRST matching requests are
    actually faulted (`--fault-count`, default 1); every match beyond that is
    served normally, which is what makes a post-fault retry succeed
    (--autosetup-fault-check cell 3). `hits` is the running counter the harness
    reads back to prove the fault path was actually exercised (test-design
    trap 5).
    """

    kind: str
    suffix: str
    delay_s: float = 0.0
    max_hits: int = 1
    hits: int = 0

    def __post_init__(self) -> None:
        if self.kind not in ("404", "tamper", "delay"):
            raise ValueError(
                f"unknown fault kind {self.kind!r}; expected one of 404, tamper, delay"
            )


def parse_fault(spec: str, *, max_hits: int) -> Fault:
    """Parse a `--fault` value: `404:<suffix>`, `tamper:<suffix>`, or `delay:<suffix>:<seconds>`.

    The delay form is split with `rsplit(":", 1)` (spec section 8.3) so a
    `suffix` containing colons (none of ours do, but paths are not guaranteed
    not to) still parses; only the LAST colon-separated field is the seconds.
    """
    kind, _, rest = spec.partition(":")
    if kind == "delay":
        try:
            suffix, seconds_s = rest.rsplit(":", 1)
            delay_s = float(seconds_s)
        except ValueError as e:
            raise ValueError(
                f"bad delay fault {spec!r}: expected delay:<path-suffix>:<seconds>"
            ) from e
        return Fault(kind="delay", suffix=suffix, delay_s=delay_s, max_hits=max_hits)
    if not rest:
        raise ValueError(f"bad fault {spec!r}: expected <kind>:<path-suffix>")
    return Fault(kind=kind, suffix=rest, max_hits=max_hits)


#: --fresh-boot-check's always-on wheel-delay fault (spec section 8.3, R2-1).
#: S0 E2 measured kernel boot ~9.8s with setup starting ~3.9s in; the wheel
#: fetch comes after D1/D2, so holding it 15s keeps state=="running" for at
#: least ~9s past first idle (and still covers a CI runner twice as slow)
#: while staying well inside the cell timeout.
FRESH_BOOT_WHEEL_DELAY_S = 15.0


def read_wheel_filename(serve_dir: Path, package: str) -> str:
    """Read a wheel's served filename from assets/wheels/manifest.json.

    Never hardcode a wheel filename (spec section 8.3): the pylabrobot wheel's
    +g<sha> local version segment changes on every rebuild.
    """
    manifest_path = serve_dir / "assets" / "wheels" / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text())
    except OSError as e:
        raise RuntimeError(f"could not read {manifest_path}: {e}") from e
    for entry in manifest.get("wheels", []):
        if entry.get("package") == package and entry.get("filename"):
            return entry["filename"]
    raise RuntimeError(f"no {package!r} entry with a filename in {manifest_path}")


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


def make_handler(
    serve_dir: Path, base_path: str, coi: bool, faults: list[Fault] | None = None
) -> type[SimpleHTTPRequestHandler]:
    prefix = _normalize_base_path(base_path)
    fault_list = faults if faults is not None else []

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

        def _matching_fault(self) -> Fault | None:
            # C-17: unquote (never unquote_plus) so a literal '+' in a wheel
            # filename survives, and match on the parsed URL PATH only --
            # translate_path above already strips the query string, but
            # urlsplit().path is used here directly since faults are matched
            # BEFORE translate_path runs.
            req_path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
            for fault in fault_list:
                if fault.hits < fault.max_hits and req_path.endswith(fault.suffix):
                    return fault
            return None

        def _serve_tampered(self) -> None:
            fs_path = self.translate_path(self.path)
            try:
                with open(fs_path, "rb") as fh:
                    data = fh.read()
            except OSError:
                self.send_error(404, "praxis fault injection: tamper source missing")
                return
            tampered = data + b"\n# praxis-fault-injected-tamper\n"
            self.send_response(200)
            ctype = self.guess_type(fs_path)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(tampered)))
            self.end_headers()
            self.wfile.write(tampered)

        def do_GET(self) -> None:
            fault = self._matching_fault()
            if fault is not None:
                fault.hits += 1
                LOG.info(
                    "fault injected: kind=%s suffix=%s hit=%d/%d path=%s",
                    fault.kind, fault.suffix, fault.hits, fault.max_hits, self.path,
                )
                if fault.kind == "404":
                    self.send_error(404, "praxis fault injection: 404")
                    return
                if fault.kind == "tamper":
                    self._serve_tampered()
                    return
                if fault.kind == "delay":
                    # Holds only THIS request/thread: ThreadingHTTPServer gives
                    # every connection its own thread, so the rest of the site
                    # (and the kernel-ready path) stays responsive while this
                    # one sleeps (spec section 8.3, trap 8).
                    time.sleep(fault.delay_s)
                    super().do_GET()
                    return
            super().do_GET()

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

    def __init__(
        self, serve_dir: Path, base_path: str, coi: bool, faults: list[Fault] | None = None
    ) -> None:
        self.faults = faults if faults is not None else []
        handler_cls = make_handler(serve_dir, base_path, coi, self.faults)
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
            # --- 1. auto-setup already ran via PYTHONSTARTUP + the cleanup_transforms
            # gate before this cell was ever dispatched (spec 260914_first-run-auto-setup.md
            # section 8.3, --probe/--probe --offline/--completion-check row); this call is
            # therefore a no-op guarded by praxis_boot's once-guard/lock, not a second run
            # (AC-6). Kept (rather than removed outright) so this probe still measures
            # `praxis_boot.state` end to end, and still works standalone if ever run
            # against a kernel where PYTHONSTARTUP did not fire.
            try:
                import praxis_boot
                await praxis_boot.setup()
                RESULT["praxis_ready"] = praxis_boot.state == "ready"
                RESULT["praxis_boot_state"] = praxis_boot.state
                RESULT["autostart_origin"] = getattr(praxis_boot, "autostart_origin", None)
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
            # :168 at the 1.0.0b1 pin), not in setup(). A False flag here means the class
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
                from pylabrobot.legacy.liquid_handling import LiquidHandler
                from pylabrobot.legacy.liquid_handling.backends import (
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
            # --- 1. auto-setup already ran via PYTHONSTARTUP + the gate; this is a
            # no-op retry through the once-guard/lock (AC-6), not a second run --
            # kept only so pylabrobot is importable and praxis_boot.state is measured
            # even if PYTHONSTARTUP did not fire (spec section 8.3, --completion-check row) ---
            try:
                import praxis_boot
                await praxis_boot.setup()
                RESULT["praxis_ready"] = praxis_boot.state == "ready"
                RESULT["praxis_boot_state"] = praxis_boot.state
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
                exec("from pylabrobot.legacy.liquid_handling import LiquidHandler", ip.user_ns)
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
    faults: list[Fault] | None = None,
) -> dict[str, Any]:
    # `code_override` lets a caller drive this same browser/serve/sentinel
    # machinery with a DIFFERENT in-kernel payload. It exists so --completion-check
    # does not have to edit build_probe_code: that builder is shared by --probe and
    # --offline (both CI gates), and its f-string + textwrap.dedent + split-sentinel
    # construction is the path that silently produced a mis-dedented payload once
    # already. A new payload is a new function; this is the seam that allows it.
    # `faults` (spec section 8.3) lets --fresh-boot-check always hold the async
    # pylabrobot wheel fetch so AC-2's wait is deterministic, and lets --autosetup-
    # fault-check/--fault inject 404/tamper/delay faults at the harness's static
    # server, never via page.route() (trap 5: route() does not see Worker requests).
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as e:  # pragma: no cover - environment problem, not a probe result
        raise RuntimeError(f"playwright is not importable: {e}") from e

    prefix = _normalize_base_path(base_path)
    timeout_ms = timeout_s * 1000

    with ServedDir(serve_dir, base_path, coi, faults=faults) as served:
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
        probe_wall_start = time.monotonic()
        probe_wall_s: float | None = None

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
                except Exception as wait_exc:
                    # A bare "Timeout 120000ms exceeded" tells you NOTHING about why the
                    # boot never finished, and the page is about to be closed in the
                    # `finally` below -- so everything diagnostic has to be harvested
                    # HERE or it is lost forever. This matters most for --offline, whose
                    # whole job is to fail: without this, a genuine offline breakage and
                    # a slow kernel are the same message.
                    try:
                        stuck_body = page.evaluate("() => document.body.innerText")
                    except Exception:
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

                # Approximates "wall time from sending the execute request to its
                # execute_reply" (spec section 8.3's --fresh-boot-check row): this is
                # actually navigation-start-to-sentinel-found, a superset that also
                # includes full kernel boot -- precise execute-request timing would
                # need frontend instrumentation of kernel status transitions, which
                # this harness does not have. Recorded for evidence, not thresholded.
                probe_wall_s = time.monotonic() - probe_wall_start

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
        "probe_wall_s": probe_wall_s,
        "faults": [dataclasses.asdict(f) for f in (faults or [])],
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
    """In-kernel payload for AC-1/AC-2 fresh-boot auto-setup (spec
    260914_first-run-auto-setup.md section 8.3, --fresh-boot-check row).

    PREMISE REPLACED (was gate T4's "type two lines"): auto-setup already ran
    via PYTHONSTARTUP + the `cleanup_transforms` gate by the time this cell was
    ever dispatched to the kernel, so this probe must NOT import or call
    `praxis_boot.setup()` (nor `praxis_main()`, nor set `HOST_ROOT`) itself --
    doing so would make the gate pass even if auto-setup were entirely broken
    (test-design trap 1). It only READS `praxis_boot` state and then imports
    pylabrobot. Two static checks the HARNESS makes on THIS SOURCE STRING
    before it is ever sent to the kernel close the rest of that gap:
    `setup_called_by_probe` (none of the shared forbidden list
    `praxis_main(`/`praxis_boot.setup(`/`HOST_ROOT =` appear below --
    `find_forbidden_bootstrap_call`) and the playground-names import-free
    check (no `import LiquidHandler`/`from pylabrobot.liquid_handling` line
    below -- `probe_imports_playground_names`); AC-1's playground-names clause
    (T3b) is only meaningful if the names were never imported by the probe.

    Records sys.path/cwd unconditionally, same reasoning as before: `import
    praxis_boot` only works because the kernel mounts the JupyterLite contents
    drive at /drive and runs there, and a failure there would otherwise be
    indistinguishable from "the file was not shipped".
    """
    start_a, start_b = PROBE_START[: len(PROBE_START) // 2], PROBE_START[len(PROBE_START) // 2 :]
    end_a, end_b = PROBE_END[: len(PROBE_END) // 2], PROBE_END[len(PROBE_END) // 2 :]
    return textwrap.dedent(
        f"""
        import builtins, json, os, sys
        RESULT: dict = {{}}

        RESULT["cwd"] = os.getcwd()
        RESULT["sys_path_head"] = sys.path[:4]
        RESULT["drive_listing"] = (
            sorted(os.listdir("/drive")) if os.path.isdir("/drive") else None
        )

        try:
            import praxis_boot
            RESULT["import_praxis_boot"] = True
        except Exception as e:  # noqa: BLE001
            RESULT["import_praxis_boot"] = False
            RESULT["import_error"] = f"{{type(e).__name__}}: {{e}}"

        if RESULT.get("import_praxis_boot"):
            RESULT["state"] = getattr(praxis_boot, "state", None)
            RESULT["gate_waited"] = getattr(praxis_boot, "gate_waited", None)
            RESULT["autostart_origin"] = getattr(praxis_boot, "autostart_origin", None)
            RESULT["kernel_nonce"] = getattr(praxis_boot, "kernel_nonce", None)
            RESULT["derived_host_root"] = getattr(praxis_boot, "host_root", None)
            try:
                RESULT["failure"] = repr(getattr(praxis_boot, "failure", None))
            except Exception:  # noqa: BLE001 - a bad __repr__ must not sink the probe
                RESULT["failure"] = "<unprintable exception>"

            try:
                import pylabrobot
                from pylabrobot.io.serial import Serial
                RESULT["plr_after"] = getattr(pylabrobot, "__version__", None)
                RESULT["serial_is_shim"] = Serial is getattr(builtins, "WebSerial", None)
            except Exception as e:  # noqa: BLE001
                RESULT["plr_after"] = None
                RESULT["serial_is_shim"] = None
                RESULT["post_import_error"] = f"{{type(e).__name__}}: {{e}}"

            # Playground names (AC-1's last sentence, T3b): the legacy welcome
            # bootstrap cell exec'd the loader into the NOTEBOOK globals, so
            # LiquidHandler/STAR landed in the user namespace with no import.
            # Evaluated with NO import of either name anywhere in this probe --
            # the harness checks that statically (probe_imports_playground_names)
            # before this source is ever sent.
            try:
                RESULT["playground_names_ok"] = bool(
                    "LiquidHandler" in globals()
                    and LiquidHandler.__name__ == "LiquidHandler"  # noqa: F821
                    and "STAR" in globals()
                )
            except Exception as e:  # noqa: BLE001
                RESULT["playground_names_ok"] = False
                RESULT["playground_names_error"] = f"{{type(e).__name__}}: {{e}}"

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
                except Exception:
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


def expected_plr_version_prefix() -> str:
    """``<base>+g`` -- the version prefix the built wheel must report in the browser.

    ``build_wheels.stamp_version`` stamps ``<pylabrobot/version.txt>+g<sha8>`` from the
    pinned commit, so the base is read from the submodule's own ``version.txt`` instead
    of being a second literal that drifts on every PLR bump (it was ``0.2.2`` here until
    the 1.0.0b1 migration).
    """
    version_txt = DEFAULT_PLR_SUBMODULE / "pylabrobot" / "version.txt"
    try:
        base = version_txt.read_text().strip()
    except OSError as e:
        raise VizCheckError(f"could not read PLR version from {version_txt}: {e}") from e
    if not base:
        raise VizCheckError(f"{version_txt} is empty; cannot derive the expected PLR version")
    return f"{base}+g"


DEFAULT_NOTEBOOK = "welcome.ipynb"

def notebook_expected() -> tuple[str, ...]:
    """Strings the welcome notebook must print.

    These are the notebook's own output, not the harness's -- if the notebook's cells
    change, this list must change with them, and that coupling is deliberate: it is what
    makes this a test OF the notebook rather than a test that some notebook ran.

    A function, not a module-level tuple: the PLR version comes from the submodule's
    ``version.txt`` (``expected_plr_version_prefix``), and reading it at import made every
    harness consumer that loads this module by path fail without an initialised submodule
    (epic 260929_notebook-display-design, D16 "Import-time submodule dependency, removed in
    A1"). ``run_notebook_check`` binds the result once at its top; ``main`` reads only the
    length off the returned result dict's ``expected`` list. Raises ``VizCheckError`` when
    ``version.txt`` is missing or empty.
    """
    return (
        "praxis auto-setup state: ready",
        f"PyLabRobot {expected_plr_version_prefix()}",
        "Serial is the browser shim: True",
    )


def find_forbidden_bootstrap_in_notebook(nb_path: Path) -> list[str]:
    """Scan a staged notebook's CODE cells only for the shared forbidden list (AC-10).

    Markdown cells may still mention `praxis_boot.setup()` (spec section 8.3,
    --notebook-check row); only `cell_type == "code"` cells are scanned, same
    scope as the AC-10 unit test and the fresh-boot static probe-source check.
    """
    nb = json.loads(nb_path.read_text())
    hits: list[str] = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        needle = find_forbidden_bootstrap_call(source)
        if needle:
            hits.append(needle)
    return hits


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
    # Bind the expected strings ONCE, first: a missing PLR ``version.txt`` must fail here,
    # before Playwright is imported or a browser launched. Every later use in this function
    # reads ``expected``; ``main`` uses ``len(result["expected"])`` (no second call).
    expected = notebook_expected()

    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    prefix = _normalize_base_path(base_path)
    timeout_ms = timeout_s * 1000
    console_messages: list[dict[str, Any]] = []
    pageerrors: list[str] = []

    # AC-10 static check, made BEFORE the notebook is ever run (spec section
    # 8.3, --notebook-check row): a shipped code cell calling praxis_main(/
    # praxis_boot.setup(/HOST_ROOT = would make this gate pass even with
    # auto-setup entirely broken.
    nb_path = serve_dir / "files" / notebook
    forbidden_bootstrap_hits = (
        find_forbidden_bootstrap_in_notebook(nb_path) if nb_path.is_file() else None
    )

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
                        arg=list(expected),
                        timeout=timeout_ms,
                    )
                    timed_out = False
                except PlaywrightTimeoutError:
                    timed_out = True

                outputs_text = page.evaluate("() => window.__praxisCollectOutputs() || ''") or ""
                body_text = page.evaluate("() => document.body.innerText")
                run_all_error = page.evaluate("() => window.__praxisRunAllError || null")
                found = {n: (n in outputs_text) for n in expected}
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
                    "expected": list(expected),
                    "found": found,
                    "all_found": all(found.values()),
                    "timed_out": timed_out,
                    "run_all_error": run_all_error,
                    "tracebacks": tracebacks,
                    "pageerrors": pageerrors,
                    "offline": offline,
                    "forbidden_bootstrap_hits": forbidden_bootstrap_hits,
                }
                if not result["all_found"]:
                    result["outputs_text"] = outputs_text[-3000:]
                    result["body_text_tail"] = body_text[-2000:]
                    result["console"] = console_messages
                return result
            finally:
                browser.close()


# ---------------------------------------------------------------------------
# --autosetup-fault-check / --restart-check (spec 260914_first-run-auto-setup.md
# section 8.3). Both drive a HARNESS-CREATED blank notebook in the real lab app
# (never welcome.ipynb), because the S0 spike found `notebook:run-all-cells`
# halts at the first raising cell (section 5.1) -- a gated setup failure would
# stop a run-all at cell 1, which is fine for --notebook-check (a failure there
# SHOULD fail loudly) but wrong for a check that needs cells 2-4 to run
# regardless of cell 1's outcome. Cells are therefore run ONE AT A TIME via
# `notebook:run-cell` on an explicit active-cell index.
#
# NOT independently browser-verified in this task: there is no local browser
# run available here (the built site is stale; CI runs the browser gates on
# the PR). The JupyterLab/jupyterlite command and shared-model surface used
# below (`docmanager:open` with an explicit kernel, `notebook:run-cell`,
# `model.sharedModel.insertCell`/`deleteCell`, `cell.sharedModel.setSource`,
# `sessionContext.session.kernel.restart()`) is written from the pinned
# jupyterlite-core 0.8.1 API as documented, mirroring the ALREADY-VERIFIED
# patterns in run_notebook_check (kernel-selection dialog handling, reading
# outputs from the model rather than the DOM -- repl_smoke.py:1342-1353 in the
# pre-change file). Every step's own return value is checked before the next
# step runs, so a wrong API name surfaces as a `dispatched: False` / raised
# result in CI rather than a silent false pass.
# ---------------------------------------------------------------------------

#: Cell 1/2 of --autosetup-fault-check: a side-effect sentinel that must be
#: ABSENT from the cell's own output if the gate blocked it (spec section 8.3).
#: Built from two literals, like the split-sentinel convention used by
#: build_probe_code, so the contiguous string exists only in printed output.
AUTOSETUP_FAULT_SIDE_EFFECT_CELL = (
    "_S = 'side' + 'effect'; import builtins; builtins.__praxis_cell_ran = True; print(_S)"
)
AUTOSETUP_FAULT_SIDE_EFFECT_NEEDLE = "side" + "effect"

#: Cell 3: the fault count is spent by the time this runs (PYTHONSTARTUP's own
#: auto-setup attempt already consumed it), so this manual retry succeeds.
#: Also records gate_waited for AC-2 measurement.
AUTOSETUP_FAULT_RETRY_CELL = (
    "import praxis_boot\nawait praxis_boot.setup()\n"
    "import json; print(json.dumps({\"gate_waited\": praxis_boot.gate_waited}))"
)

#: AC-1's literal zero-action cell (spec section 3): used verbatim as cell 4
#: of --autosetup-fault-check and as the pre/post-restart cell of
#: --restart-check by wrapping it in the same sentinel-JSON shape as
#: build_fresh_boot_probe_code so kernel_nonce/state are readable too.
AC1_ZERO_ACTION_LINE = (
    "import builtins, pylabrobot; from pylabrobot.io.serial import Serial; "
    "print(Serial is builtins.WebSerial)"
)

#: Substring expected in a gate-blocked cell's traceback text for each fault
#: kind (spec section 8.3/failure modes 1-3), read off praxis_bootstrap.py's
#: own error text (`HTTP {status}` / `loader module sha256 mismatch`).
FAULT_REASON_NEEDLE: dict[str, str] = {
    "404": "HTTP 404",
    "tamper": "sha256 mismatch",
}

#: Regex to match the exact success line printed by praxis_boot.setup() when
#: setup completes normally (spec section 6.2 _run_setup step 6, trap 2).
#: The line is: `PyLabRobot {version} ready (site root {root}); Serial is the browser shim`
#: This pattern matches the stable parts that are independent of version and root.
AUTOSETUP_SUCCESS_LINE_PATTERN = re.compile(
    r"PyLabRobot\s+\S+\s+ready\s+\(site\s+root\s+[^)]*\);\s+Serial\s+is\s+the\s+browser\s+shim"
)


def build_restart_probe_cell() -> str:
    """AC-1 + nonce probe cell for --restart-check, run before and after a
    kernel restart. Deliberately does not call setup()/praxis_main() itself
    (same trap-1 reasoning as build_fresh_boot_probe_code): auto-setup must
    already have completed via PYTHONSTARTUP by the time this cell runs.
    """
    start_a, start_b = PROBE_START[: len(PROBE_START) // 2], PROBE_START[len(PROBE_START) // 2 :]
    end_a, end_b = PROBE_END[: len(PROBE_END) // 2], PROBE_END[len(PROBE_END) // 2 :]
    return textwrap.dedent(
        f"""
        import builtins, json
        RESULT: dict = {{}}
        try:
            import praxis_boot
            RESULT["state"] = getattr(praxis_boot, "state", None)
            RESULT["kernel_nonce"] = getattr(praxis_boot, "kernel_nonce", None)
            import pylabrobot
            from pylabrobot.io.serial import Serial
            RESULT["serial_is_shim"] = Serial is getattr(builtins, "WebSerial", None)
        except Exception as e:  # noqa: BLE001
            RESULT["error"] = f"{{type(e).__name__}}: {{e}}"
        print({start_a!r} + {start_b!r})
        print(json.dumps(RESULT))
        print({end_a!r} + {end_b!r})
        """
    ).strip()


def _extract_sentinel_json(text: str) -> dict[str, Any]:
    """Pull the PROBE_START/PROBE_END-delimited JSON blob out of *text*.

    Shared by --restart-check/--autosetup-fault-check cell output, which is
    read from the notebook MODEL (a cell's stdout stream text), not the DOM --
    same reasoning as run_probe's page-text sentinel search.
    """
    match = re.search(
        re.escape(PROBE_START) + r"\s*(.*?)\s*" + re.escape(PROBE_END), text, re.DOTALL
    )
    if not match:
        raise NotebookCheckError(
            f"no sentinel-delimited JSON found in cell output; last 500 chars: {text[-500:]!r}"
        )
    return json.loads(match.group(1))


def _open_blank_notebook(page: Any, *, timeout_ms: float) -> str:
    """Create a blank notebook via the contents API and open it with an
    explicit Python kernel, handling the Select Kernel dialog if it appears
    (same trap as run_notebook_check: a notebook with no saved kernel
    preference prompts and silently blocks every later dispatch until
    accepted). Returns the notebook's server-side path.
    """
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    page.wait_for_function("() => !!window.jupyterapp", timeout=timeout_ms)

    created = page.evaluate(
        """async () => {
            try {
                const model = await window.jupyterapp.serviceManager.contents.newUntitled(
                    {type: "notebook", path: ""});
                return {ok: true, path: model.path};
            } catch (e) {
                return {ok: false, error: String(e)};
            }
        }"""
    )
    if not created.get("ok"):
        raise NotebookCheckError(f"could not create a blank notebook: {created.get('error')!r}")
    notebook_path = created["path"]
    LOG.info("harness-created blank notebook at %s", notebook_path)

    opened = page.evaluate(
        """async (path) => {
            try {
                await window.jupyterapp.commands.execute("docmanager:open", {
                    path, factory: "Notebook", kernel: {name: "python"}});
                return {ok: true};
            } catch (e) {
                return {ok: false, error: String(e)};
            }
        }""",
        notebook_path,
    )
    if not opened.get("ok"):
        raise NotebookCheckError(f"could not open the blank notebook: {opened.get('error')!r}")

    page.wait_for_function(
        "() => !!document.querySelector('.jp-Notebook')", timeout=timeout_ms
    )
    try:
        page.wait_for_selector(".jp-Dialog", timeout=10_000)
        LOG.info("kernel-selection dialog present; accepting")
        page.click(".jp-Dialog .jp-mod-accept")
        page.wait_for_selector(".jp-Dialog", state="detached", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        LOG.info("no kernel-selection dialog appeared")

    page.wait_for_function(
        """() => {
            const w = window.jupyterapp?.shell?.currentWidget;
            return w?.sessionContext?.session?.kernel?.status === 'idle';
        }""",
        timeout=timeout_ms,
    )
    return notebook_path


# ---------------------------------------------------------------------------
# --persistence-check (spec .praxia/docs/specs/260922_repl-persistence-ladder.md).
# T8a below: S1-S3 (AC-8, AC-9, AC-13, AC-14, AC-17). T8b (further down,
# scenarios S4-S10, AC-10/11/12) builds on this same harness.
#
# Each scenario runs in its OWN fresh browser context (spec A-8/B-6: "Every
# scenario starts in a fresh browser context, so IndexedDB, OPFS and
# localStorage all start empty unless the scenario seeds them"). The harness
# never uses page.dispatch_event -- every gesture-bound interaction goes
# through a real page.click() or page.keyboard, because the whole point of
# D6/AC-9 is proving the product's gesture calls are reachable from REAL
# user-activation-carrying clicks, not synthetic DOM events (which a headless
# browser would happily deliver even through an `await`).
#
# Stable selectors this harness depends on (T6, panel.js header comment):
#   #praxis-persistence[data-praxis-tier][data-praxis-excluded]
#   [data-praxis-action=protect|choose-folder|reconnect|restore|keep-browser-only|toggle-panel]
#   dialog#praxis-persistence-first-save
# ---------------------------------------------------------------------------

#: Installed on every persistence-check context (S1-S3 alike). Wraps
#: `navigator.storage.persist`/`.persisted`, calling through to the real
#: implementation, and installs the capture/bubble click listeners that
#: `inClickDispatch` reads (D6 table, browser level). Activation and the
#: in-click-dispatch flag are captured SYNCHRONOUSLY at call time, before the
#: wrapped call's promise settles -- a call made after even a short `await`
#: would still read `userActivation: true` (Chromium's transient activation
#: lasts seconds), so capturing it post-resolution would prove nothing.
PERSISTENCE_BASE_INIT_SCRIPT = r"""
(() => {
  window.__praxisGestureLog = [];
  window.__praxisInClickDispatch = false;
  window.addEventListener('click', () => { window.__praxisInClickDispatch = true; }, true);
  window.addEventListener('click', () => { window.__praxisInClickDispatch = false; }, false);

  function activation() {
    return !!(window.navigator.userActivation && window.navigator.userActivation.isActive);
  }

  const storage = window.navigator && window.navigator.storage;
  if (storage) {
    if (typeof storage.persist === 'function') {
      const origPersist = storage.persist.bind(storage);
      storage.persist = function () {
        const userActivation = activation();
        const inClickDispatch = !!window.__praxisInClickDispatch;
        return origPersist().then((result) => {
          window.__praxisGestureLog.push({ api: 'persist', userActivation, inClickDispatch, result });
          return result;
        });
      };
    }
    if (typeof storage.persisted === 'function') {
      const origPersisted = storage.persisted.bind(storage);
      storage.persisted = function () {
        const userActivation = activation();
        const inClickDispatch = !!window.__praxisInClickDispatch;
        return origPersisted().then((result) => {
          window.__praxisGestureLog.push({ api: 'persisted', userActivation, inClickDispatch, result });
          return result;
        });
      };
    }
  }
})();
"""

#: S2 only. Stubs `showDirectoryPicker` with a REAL OPFS subdirectory handle
#: (AC-10's picker-stub shape, reused here since D6's gesture proof needs a
#: real FileSystemDirectoryHandle, not a mock) and wraps
#: `FileSystemHandle.prototype.{queryPermission,requestPermission}` -- adding
#: them if the browser's OPFS handles don't implement the permission API at
#: all (`permission_methods_polyfilled`, spec risk table) -- with the
#: forced-"prompt" test switch. That switch lives ONLY here, never in product
#: code (B-11): `queryPermission` returns "prompt" while
#: `localStorage["__praxis_test_force_prompt"] === "1"`, until
#: `requestPermission` is called, which clears the flag.
PERSISTENCE_PICKER_STUB_INIT_SCRIPT = r"""
(() => {
  window.__praxisPermissionMethodsPolyfilled = false;
  const proto = window.FileSystemHandle && window.FileSystemHandle.prototype;

  function activation() {
    return !!(window.navigator.userActivation && window.navigator.userActivation.isActive);
  }

  if (proto) {
    if (typeof proto.queryPermission !== 'function') {
      proto.queryPermission = function () { return Promise.resolve('granted'); };
      window.__praxisPermissionMethodsPolyfilled = true;
    }
    if (typeof proto.requestPermission !== 'function') {
      proto.requestPermission = function () { return Promise.resolve('granted'); };
      window.__praxisPermissionMethodsPolyfilled = true;
    }

    const origQueryPermission = proto.queryPermission;
    const origRequestPermission = proto.requestPermission;

    proto.queryPermission = function (...args) {
      const userActivation = activation();
      const inClickDispatch = !!window.__praxisInClickDispatch;
      if (window.localStorage.getItem('__praxis_test_force_prompt') === '1') {
        window.__praxisGestureLog.push({
          api: 'queryPermission', userActivation, inClickDispatch, result: 'prompt', forced: true,
        });
        return Promise.resolve('prompt');
      }
      return origQueryPermission.apply(this, args).then((result) => {
        window.__praxisGestureLog.push({ api: 'queryPermission', userActivation, inClickDispatch, result });
        return result;
      });
    };

    proto.requestPermission = function (...args) {
      const userActivation = activation();
      const inClickDispatch = !!window.__praxisInClickDispatch;
      return origRequestPermission.apply(this, args).then((result) => {
        window.localStorage.removeItem('__praxis_test_force_prompt');
        window.__praxisGestureLog.push({ api: 'requestPermission', userActivation, inClickDispatch, result });
        return result;
      });
    };
  }

  window.showDirectoryPicker = function () {
    const userActivation = activation();
    const inClickDispatch = !!window.__praxisInClickDispatch;
    window.__praxisGestureLog.push({ api: 'showDirectoryPicker', userActivation, inClickDispatch });
    if (typeof window.__praxisPickerCalled === 'function') {
      window.__praxisPickerCalled();
    }
    return window.navigator.storage.getDirectory().then((root) =>
      root.getDirectoryHandle('praxis-persist-probe', { create: true }));
  };
})();
"""

#: S3 only. Added AFTER PERSISTENCE_BASE_INIT_SCRIPT so it wins: feature
#: detection is `window.isSecureContext && typeof win.showDirectoryPicker ===
#: "function"` (panel.js D5), so deleting the function is enough to make
#: `fsaSupported` false with no user-agent sniffing involved.
PERSISTENCE_NO_FSA_INIT_SCRIPT = r"""
(() => { window.showDirectoryPicker = undefined; })();
"""

#: How long to wait to prove a selector is ABSENT (S1's repl_entry_has_chip).
#: Short relative to --timeout: the loader IIFE's pathname check is a
#: synchronous early return (D2/T6), so if the chip were going to appear it
#: would within milliseconds, not seconds.
_PERSISTENCE_ABSENCE_TIMEOUT_MS = 5000


def _persistence_seed_notebook_js(path: str) -> str:
    return (
        """async () => {
            try {
                await window.jupyterapp.serviceManager.contents.save(%s, {
                    type: "notebook", format: "json",
                    content: { cells: [], metadata: {}, nbformat: 4, nbformat_minor: 5 },
                });
                return { ok: true };
            } catch (e) {
                return { ok: false, error: String(e) };
            }
        }"""
        % json.dumps(path)
    )


def _run_persistence_scenario_s1(browser: Any, served: ServedDir, prefix: str, timeout_ms: float) -> dict[str, Any]:
    """S1 (AC-8): fresh context, no seeding. Chip appears on lab/ before any
    save, `initial_tier` is read off the `persisted()` wrapper's own log (not
    just the DOM, per T8a), and repl/ never gets a chip."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    out: dict[str, Any] = {}
    context = browser.new_context()
    context.add_init_script(PERSISTENCE_BASE_INIT_SCRIPT)
    try:
        page = context.new_page()
        lab_url = f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
        page.goto(lab_url, wait_until="load", timeout=timeout_ms)
        try:
            page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
            out["indicator_present_before_save"] = True
        except PlaywrightTimeoutError:
            out["indicator_present_before_save"] = False

        if out["indicator_present_before_save"]:
            try:
                page.wait_for_function(
                    "() => (window.__praxisGestureLog||[]).some(e => e.api === 'persisted')",
                    timeout=timeout_ms,
                )
            except PlaywrightTimeoutError:
                pass
            gesture_log = page.evaluate("() => window.__praxisGestureLog || []")
            persisted_entries = [e for e in gesture_log if e.get("api") == "persisted"]
            out["initial_tier"] = (
                ("L1" if persisted_entries[-1].get("result") is True else "L0")
                if persisted_entries
                else None
            )
            out["s1_persisted_log"] = persisted_entries
        else:
            out["initial_tier"] = None

        repl_url = f"http://127.0.0.1:{served.port}{prefix}repl/index.html"
        page2 = context.new_page()
        page2.goto(repl_url, wait_until="load", timeout=timeout_ms)
        try:
            page2.wait_for_selector(
                "#praxis-persistence", state="attached", timeout=_PERSISTENCE_ABSENCE_TIMEOUT_MS
            )
            out["repl_entry_has_chip"] = True
        except PlaywrightTimeoutError:
            out["repl_entry_has_chip"] = False
    finally:
        context.close()
    return out


def _run_persistence_scenario_s2(browser: Any, served: ServedDir, prefix: str, timeout_ms: float) -> dict[str, Any]:
    """S2 (AC-9, AC-14): fresh context with the OPFS picker stub, drive seeded
    with persist-probe.ipynb. Clicks Protect, then Choose working folder;
    sets the forced-prompt flag, reloads, and clicks Reconnect. No content
    assertions (that is T8b's job) -- only gesture-synchrony and storage
    hygiene."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    out: dict[str, Any] = {}
    picker_calls = {"n": 0}
    context = browser.new_context()

    def _on_picker_called() -> None:
        picker_calls["n"] += 1

    context.expose_function("__praxisPickerCalled", _on_picker_called)
    context.add_init_script(PERSISTENCE_BASE_INIT_SCRIPT)
    context.add_init_script(PERSISTENCE_PICKER_STUB_INIT_SCRIPT)
    try:
        page = context.new_page()
        lab_url = f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
        page.goto(lab_url, wait_until="load", timeout=timeout_ms)
        page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
        page.wait_for_function("() => !!window.jupyterapp", timeout=timeout_ms)

        seeded = page.evaluate(_persistence_seed_notebook_js("persist-probe.ipynb"))
        out["seed_ok"] = bool(seeded.get("ok"))
        out["seed_error"] = seeded.get("error")

        # -- Protect ----------------------------------------------------
        page.click("[data-praxis-action=toggle-panel]", timeout=timeout_ms)
        page.click("[data-praxis-action=protect]", timeout=timeout_ms)
        try:
            page.wait_for_function(
                "() => (window.__praxisGestureLog||[]).some(e => e.api === 'persist')",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            pass
        page.wait_for_timeout(300)  # let core.js's own .then()/notify()/render() land

        log_before_choose = page.evaluate("() => window.__praxisGestureLog || []")
        persist_entries = [e for e in log_before_choose if e.get("api") == "persist"]
        out["persist_returned"] = persist_entries[-1].get("result") if persist_entries else None
        out["tier_after_persist"] = page.get_attribute("#praxis-persistence", "data-praxis-tier")

        # -- Choose working folder ---------------------------------------
        page.click("[data-praxis-action=choose-folder]", timeout=timeout_ms)
        try:
            page.wait_for_function(
                "() => (window.__praxisGestureLog||[]).some(e => e.api === 'showDirectoryPicker')",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            pass
        try:
            page.wait_for_function(
                "() => document.querySelector('#praxis-persistence')"
                "?.getAttribute('data-praxis-tier') === 'L2'",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            pass

        out["permission_methods_polyfilled"] = page.evaluate(
            "() => !!window.__praxisPermissionMethodsPolyfilled"
        )
        log_before_reload = page.evaluate("() => window.__praxisGestureLog || []")

        # -- Force prompt, reload, Reconnect -----------------------------
        page.evaluate("() => window.localStorage.setItem('__praxis_test_force_prompt', '1')")
        page.reload(wait_until="load", timeout=timeout_ms)
        page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
        try:
            page.wait_for_function(
                "() => document.querySelector('#praxis-persistence')"
                "?.getAttribute('data-praxis-tier') === 'L2-paused'",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            pass
        out["tier_on_prompt"] = page.get_attribute("#praxis-persistence", "data-praxis-tier")

        page.click("[data-praxis-action=toggle-panel]", timeout=timeout_ms)
        page.click("[data-praxis-action=reconnect]", timeout=timeout_ms)
        try:
            page.wait_for_function(
                "() => (window.__praxisGestureLog||[]).some(e => e.api === 'requestPermission')",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            pass
        page.wait_for_timeout(300)

        log_after_reload = page.evaluate("() => window.__praxisGestureLog || []")
        # __praxisGestureLog is a page-realm global: page.reload() replaces the
        # JS realm, so the array (and anything logged before it) is gone --
        # merge the pre- and post-reload halves here, in Python, rather than
        # trying to smuggle state across the reload inside the page.
        out["gesture_log"] = log_before_reload + log_after_reload
        out["picker_calls"] = picker_calls["n"]

        # -- AC-14 storage hygiene, evaluated at the end of S2 ------------
        db_names = page.evaluate(
            "async () => (await indexedDB.databases()).map((d) => d.name)"
        )
        out["indexeddb_names"] = db_names
        out["hygiene_no_legacy_jupyterlite_dbs"] = not any(
            re.match(r"^JupyterLite Storage - ", n or "") for n in (db_names or [])
        )
        out["hygiene_one_praxis_repl_contents"] = (db_names or []).count("praxis-repl-contents") == 1
        out["hygiene_praxis_repl_persistence_present"] = "praxis-repl-persistence" in (db_names or [])

        probe = page.evaluate(
            """async () => {
                try {
                    const model = await window.jupyterapp.serviceManager.contents.get(
                        "persist-probe.ipynb", { content: true });
                    return { ok: true, has_content: model.content !== undefined && model.content !== null };
                } catch (e) {
                    return { ok: false, error: String(e) };
                }
            }"""
        )
        out["hygiene_probe_readable"] = bool(probe.get("ok") and probe.get("has_content"))
        out["hygiene_probe_error"] = probe.get("error")
    finally:
        context.close()
    return out


def _run_persistence_scenario_s3(browser: Any, served: ServedDir, prefix: str, timeout_ms: float) -> dict[str, Any]:
    """S3 (AC-13): fresh context whose init script deletes
    `window.showDirectoryPicker` -- the non-FSA / D5 degraded-browser path.
    Also drives a real explicit save (via the harness's own
    `_open_blank_notebook`, already used by --autosetup-fault-check /
    --restart-check) to prove the first-save gate's modal model excludes the
    "Choose working folder" option when `pickDirectory === null`."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    out: dict[str, Any] = {}
    context = browser.new_context()
    context.add_init_script(PERSISTENCE_BASE_INIT_SCRIPT)
    context.add_init_script(PERSISTENCE_NO_FSA_INIT_SCRIPT)
    try:
        page = context.new_page()
        lab_url = f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
        page.goto(lab_url, wait_until="load", timeout=timeout_ms)
        try:
            page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
            out["nofsa_indicator_present"] = True
        except PlaywrightTimeoutError:
            out["nofsa_indicator_present"] = False

        if out["nofsa_indicator_present"]:
            out["nofsa_l2_controls"] = page.locator("[data-praxis-action=choose-folder]").count()
            panel_text = page.eval_on_selector("#praxis-persistence", "(el) => el.textContent") or ""
            out["nofsa_message_mentions_chromium"] = "Chromium" in panel_text
        else:
            out["nofsa_l2_controls"] = None
            out["nofsa_message_mentions_chromium"] = None

        modal_choose_absent = None
        if out["nofsa_indicator_present"]:
            try:
                _open_blank_notebook(page, timeout_ms=timeout_ms)
                page.evaluate(
                    """async () => {
                        try {
                            await window.jupyterapp.commands.execute("docmanager:save");
                        } catch (e) {
                            /* the gate is driven by evt.result settling either way (D4) */
                        }
                    }"""
                )
                page.wait_for_selector(
                    "dialog#praxis-persistence-first-save[open]", timeout=timeout_ms
                )
                modal_choose_absent = (
                    page.locator(
                        "dialog#praxis-persistence-first-save [data-praxis-action=choose-folder]"
                    ).count()
                    == 0
                )
            except (PlaywrightTimeoutError, NotebookCheckError) as e:
                out["s3_modal_trigger_error"] = f"{type(e).__name__}: {e}"
        out["nofsa_modal_choose_absent"] = modal_choose_absent
    finally:
        context.close()
    return out


# ---------------------------------------------------------------------------
# T8b: scenarios S4-S10 (AC-10, AC-11, AC-12), built on T8a's harness above.
#
# Same discipline as T8a (D6/AC-9, and the T8b dispatch's own instruction):
# every gesture-bound or UI interaction is a real page.click() / page.keyboard
# call, never page.dispatch_event. Every storage/content assertion compares
# BY CONTENT (parsed notebook `.cells`, or exact bytes where the assertion is
# specifically about bytes staying unchanged), never by presence alone.
# ---------------------------------------------------------------------------


def _persistence_seed_notebook_with_source_js(path: str, source: str) -> str:
    """JS to seed *path* as a notebook with exactly ONE code cell whose
    source is *source*. S1-S3's `_persistence_seed_notebook_js` seeds an
    empty-cells notebook, which is enough for hygiene/gesture checks that
    never edit anything -- T8b scenarios open, EDIT and re-save a cell, so
    they need something to click into and replace.
    """
    content = {
        "cells": [
            {
                "cell_type": "code",
                "source": [source],
                "metadata": {},
                "outputs": [],
                "execution_count": None,
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return (
        """async () => {
            try {
                await window.jupyterapp.serviceManager.contents.save(%s, {
                    type: "notebook", format: "json",
                    content: %s,
                });
                return { ok: true };
            } catch (e) {
                return { ok: false, error: String(e) };
            }
        }"""
        % (json.dumps(path), json.dumps(content))
    )


#: Seed arbitrary files (by TEXT content) into the picker stub's real OPFS
#: subdirectory (`praxis-persist-probe`, the same one
#: `PERSISTENCE_PICKER_STUB_INIT_SCRIPT`'s `showDirectoryPicker` stub hands
#: back). Called with `page.evaluate(_PERSISTENCE_OPFS_WRITE_FILES_JS,
#: {"sub/a.ipynb": "...", ".hidden": "..."})` -- BEFORE the picker/choose
#: click, so the seeded bytes are already "on disk" the moment core.js binds
#: the folder. Creates parent directories and dot-prefixed entries alike;
#: dot-prefixed SKIPPING is the product's job (D1), not the seed's.
_PERSISTENCE_OPFS_WRITE_FILES_JS = r"""
async (files) => {
    try {
        const root = await navigator.storage.getDirectory();
        const probeDir = await root.getDirectoryHandle('praxis-persist-probe', { create: true });
        for (const [path, text] of Object.entries(files)) {
            const segments = path.split('/');
            const fileName = segments.pop();
            let dir = probeDir;
            for (const seg of segments) {
                dir = await dir.getDirectoryHandle(seg, { create: true });
            }
            const fileHandle = await dir.getFileHandle(fileName, { create: true });
            const writable = await fileHandle.createWritable();
            await writable.write(text);
            await writable.close();
        }
        return { ok: true };
    } catch (e) {
        return { ok: false, error: String(e) };
    }
}
"""

#: Read one file's TEXT back out of the same OPFS probe directory. Called
#: with `page.evaluate(_PERSISTENCE_OPFS_READ_FILE_JS, "sub/a.ipynb")`.
#: Returns `{exists: false, text: null}` for a genuinely absent path (never
#: raises), so callers can compare "before" vs "after" without special-casing
#: a first read.
_PERSISTENCE_OPFS_READ_FILE_JS = r"""
async (path) => {
    try {
        const root = await navigator.storage.getDirectory();
        const probeDir = await root.getDirectoryHandle('praxis-persist-probe', { create: true });
        const segments = path.split('/');
        const fileName = segments.pop();
        let dir = probeDir;
        for (const seg of segments) {
            dir = await dir.getDirectoryHandle(seg, { create: false });
        }
        const fileHandle = await dir.getFileHandle(fileName, { create: false });
        const file = await fileHandle.getFile();
        const text = await file.text();
        return { exists: true, text };
    } catch (e) {
        if (e && (e.name === 'NotFoundError' || e.name === 'InvalidStateError')) {
            return { exists: false, text: null };
        }
        return { exists: false, text: null, error: String(e) };
    }
}
"""

#: Read the DRIVE's copy of a path through the real contents API (never the
#: DOM). Called with `page.evaluate(_PERSISTENCE_DRIVE_GET_JS, "a.ipynb")`.
_PERSISTENCE_DRIVE_GET_JS = r"""
async (path) => {
    try {
        const model = await window.jupyterapp.serviceManager.contents.get(path, { content: true });
        return { exists: true, content: model.content, format: model.format };
    } catch (e) {
        return { exists: false, content: null, error: String(e) };
    }
}
"""


def _notebook_json_text(source: str) -> str:
    """Build standalone notebook JSON text used to seed OPFS "on-disk" bytes
    directly (S5, S7). This is NOT necessarily byte-identical to what the
    product's `codec.js` would emit for the same cells -- scenarios that need
    that never compare raw bytes across the OPFS/drive boundary; they compare
    parsed `.cells` (`_cells_match`) instead. The one place raw-byte equality
    matters (S5's `differs_disk_untouched_after_save`) compares this
    function's own output against itself before/after a skipped mirror
    write, never against the product's serialization.
    """
    content = {
        "cells": [
            {
                "cell_type": "code",
                "source": [source],
                "metadata": {},
                "outputs": [],
                "execution_count": None,
            }
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return json.dumps(content, indent=1) + "\n"


def _cells_match(opfs_text: str | None, drive_content: Any) -> bool:
    """Compare a notebook BY CONTENT (`.cells`), the comparison every T8b
    scenario uses except S5's byte-exact "unchanged" check."""
    if opfs_text is None or not isinstance(drive_content, dict):
        return False
    try:
        disk = json.loads(opfs_text)
    except (TypeError, ValueError):
        return False
    if not isinstance(disk, dict):
        return False
    return disk.get("cells") == drive_content.get("cells")


def _decode_notebook_content(content: Any, fmt: str | None) -> dict[str, Any] | None:
    """Normalize whatever `contents.get(..., {content:true})` returns for a
    notebook into a parsed dict, regardless of which `format` the backend
    chose. Measured empirically (S10): our own save/mirror paths return
    `format="json"` with `content` already parsed, but JupyterLite's OWN
    file-browser Upload path returns `format="base64"` with `content` as a
    base64 string for a freshly-uploaded .ipynb -- so a caller that assumes
    "json" and does `content.get(...)` crashes on a plain str. This decodes
    either shape (and a bare "text" JSON string) before comparing, which is
    still an exact-content comparison, just format-agnostic."""
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        return None
    raw = content
    if fmt == "base64":
        try:
            raw = base64.b64decode(content).decode("utf-8")
        except Exception:
            return None
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _cell_source_text(cells: list[dict[str, Any]] | None, index: int = 0) -> str:
    """nbformat allows a cell's `source` to be a string OR a list of
    strings -- normalize either shape to one string for marker checks."""
    if not cells or index >= len(cells):
        return ""
    source = cells[index].get("source")
    if isinstance(source, list):
        return "".join(source)
    return source or ""


def _dialog_open(page: Any) -> bool:
    """Whether the first-save gate `<dialog>` is currently open. Polled after
    EVERY step of S6 (`gate_never_opened_s6`) and used directly by S8/S9."""
    return bool(
        page.evaluate(
            "() => { const d = document.querySelector('dialog#praxis-persistence-first-save');"
            " return !!(d && d.open); }"
        )
    )


def _poll_until(fn: Any, *, timeout_s: float = 10.0, interval_s: float = 0.25) -> Any:
    """Poll `fn()` until truthy or *timeout_s* elapses; returns the last
    value. Used wherever a T8b assertion depends on core.js's single ordered
    write chain (D7) settling asynchronously, with no DOM signal to
    `wait_for_selector` on (e.g. a disk write landing after `contents.save`).
    """
    deadline = time.monotonic() + timeout_s
    result = fn()
    while not result and time.monotonic() < deadline:
        time.sleep(interval_s)
        result = fn()
    return result


def _poll_drive_cell_source_contains(
    page: Any, path: str, marker: str, *, timeout_s: float
) -> dict[str, Any]:
    """Poll `contents.get(path)` until its first cell's source contains
    *marker*, or timeout. Returns the last drive-get result either way, so a
    timeout still leaves callers something to inspect/report rather than a
    bare None."""
    last: dict[str, Any] = {}

    def _check() -> bool:
        nonlocal last
        last = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, path)
        content = last.get("content") or {}
        return marker in _cell_source_text(content.get("cells"))

    _poll_until(_check, timeout_s=timeout_s)
    return last


def _open_existing_notebook(page: Any, path: str, *, timeout_ms: float) -> None:
    """Open an ALREADY-SEEDED notebook at *path* via `docmanager:open` (the
    same real JupyterLab command `_open_blank_notebook` uses after creation),
    handling the Select Kernel dialog if it appears. Never creates the file:
    callers seed it first via `_persistence_seed_notebook_with_source_js` /
    `_persistence_seed_notebook_js`. Does not wait for kernel-idle -- T8b only
    ever edits cell TEXT and saves, never runs a cell, so there is nothing to
    wait for a live kernel for."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    page.wait_for_function("() => !!window.jupyterapp", timeout=timeout_ms)
    opened = page.evaluate(
        """async (path) => {
            try {
                await window.jupyterapp.commands.execute("docmanager:open", {
                    path, factory: "Notebook", kernel: {name: "python"}});
                return {ok: true};
            } catch (e) {
                return {ok: false, error: String(e)};
            }
        }""",
        path,
    )
    if not opened.get("ok"):
        raise NotebookCheckError(f"could not open {path!r}: {opened.get('error')!r}")
    page.wait_for_function("() => !!document.querySelector('.jp-Notebook')", timeout=timeout_ms)
    try:
        page.wait_for_selector(".jp-Dialog", timeout=10_000)
        LOG.info("kernel-selection dialog present for %s; accepting", path)
        page.click(".jp-Dialog .jp-mod-accept")
        page.wait_for_selector(".jp-Dialog", state="detached", timeout=timeout_ms)
    except PlaywrightTimeoutError:
        LOG.info("no kernel-selection dialog appeared for %s", path)


def _replace_first_cell_source(page: Any, new_source: str, *, timeout_ms: float) -> None:
    """Click into the notebook's first cell editor and replace its whole
    source with *new_source* -- real page.click() + page.keyboard only,
    never dispatchEvent (same discipline as D6/AC-9)."""
    loc = page.locator(".jp-Notebook .jp-CodeCell .cm-content").first
    loc.wait_for(state="visible", timeout=timeout_ms)
    loc.click()
    page.keyboard.press("Control+a")
    page.keyboard.type(new_source)


def _run_persistence_scenario_s4(
    browser: Any, served: ServedDir, prefix: str, timeout_ms: float
) -> dict[str, Any]:
    """S4 (AC-10): fresh context, drive seeded with persist-probe.ipynb (one
    editable cell), OPFS starts empty. Binds via a real panel click, checks
    the mirror BY CONTENT right after the bind and again after a real
    Control+S resave, then reloads and proves rehydration needs no new
    picker call (and rebinds to the SAME folder name)."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    out: dict[str, Any] = {}
    picker_calls = {"n": 0}
    context = browser.new_context()

    def _on_picker_called() -> None:
        picker_calls["n"] += 1

    context.expose_function("__praxisPickerCalled", _on_picker_called)
    context.add_init_script(PERSISTENCE_BASE_INIT_SCRIPT)
    context.add_init_script(PERSISTENCE_PICKER_STUB_INIT_SCRIPT)
    try:
        page = context.new_page()
        lab_url = f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
        page.goto(lab_url, wait_until="load", timeout=timeout_ms)
        page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
        page.wait_for_function("() => !!window.jupyterapp", timeout=timeout_ms)

        seeded = page.evaluate(_persistence_seed_notebook_with_source_js("persist-probe.ipynb", "s4-before"))
        out["seed_ok"] = bool(seeded.get("ok"))
        out["seed_error"] = seeded.get("error")

        page.click("[data-praxis-action=toggle-panel]", timeout=timeout_ms)
        page.click("[data-praxis-action=choose-folder]", timeout=timeout_ms)
        page.wait_for_function(
            "() => document.querySelector('#praxis-persistence')"
            "?.getAttribute('data-praxis-tier') === 'L2'",
            timeout=timeout_ms,
        )

        disk = page.evaluate(_PERSISTENCE_OPFS_READ_FILE_JS, "persist-probe.ipynb")
        drive = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, "persist-probe.ipynb")
        out["mirror_after_choose_matches"] = _cells_match(disk.get("text"), drive.get("content"))
        out["mirror_after_choose_disk_exists"] = disk.get("exists")
        out["mirror_after_choose_drive_exists"] = drive.get("exists")

        _open_existing_notebook(page, "persist-probe.ipynb", timeout_ms=timeout_ms)
        _replace_first_cell_source(page, "s4-after", timeout_ms=timeout_ms)
        page.keyboard.press("Control+s")
        drive_after_resave = _poll_drive_cell_source_contains(
            page, "persist-probe.ipynb", "s4-after", timeout_s=timeout_ms / 1000
        )

        def _resave_mirrored() -> bool:
            d = page.evaluate(_PERSISTENCE_OPFS_READ_FILE_JS, "persist-probe.ipynb")
            return _cells_match(d.get("text"), drive_after_resave.get("content"))

        out["mirror_after_resave_matches"] = bool(
            _poll_until(_resave_mirrored, timeout_s=timeout_ms / 1000)
        )

        chip_text_before_reload = (
            page.eval_on_selector("[data-praxis-action=toggle-panel]", "(el) => el.textContent") or ""
        )
        out["folder_name_before_reload"] = chip_text_before_reload

        page.reload(wait_until="load", timeout=timeout_ms)
        page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
        try:
            page.wait_for_function(
                "() => document.querySelector('#praxis-persistence')"
                "?.getAttribute('data-praxis-tier') === 'L2'",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            pass
        out["tier_after_reload"] = page.get_attribute("#praxis-persistence", "data-praxis-tier")
        out["picker_calls"] = picker_calls["n"]
        chip_text_after_reload = (
            page.eval_on_selector("[data-praxis-action=toggle-panel]", "(el) => el.textContent") or ""
        )
        out["folder_name_after_reload"] = chip_text_after_reload
        out["rehydrated_without_picker"] = picker_calls["n"] == 1 and out["tier_after_reload"] == "L2"
        out["rehydrated_folder_name_matches"] = (
            "praxis-persist-probe" in chip_text_before_reload
            and "praxis-persist-probe" in chip_text_after_reload
        )
    finally:
        context.close()
    return out


def _run_persistence_scenario_s5(
    browser: Any, served: ServedDir, prefix: str, timeout_ms: float
) -> dict[str, Any]:
    """S5 (AC-10, D7 "differs on disk"): fresh context. Before choosing a
    folder, OPFS praxis-persist-probe/ is seeded with persist-probe.ipynb
    holding DIFFERENT content from the drive's own seeded version, so bulk
    sync must exclude it (never overwrite it). A real, forced explicit save
    of the drive file afterwards must still leave the disk bytes untouched;
    only a real click on Replace disk copy may write them."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    out: dict[str, Any] = {}
    context = browser.new_context()
    context.add_init_script(PERSISTENCE_BASE_INIT_SCRIPT)
    context.add_init_script(PERSISTENCE_PICKER_STUB_INIT_SCRIPT)
    try:
        page = context.new_page()
        lab_url = f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
        page.goto(lab_url, wait_until="load", timeout=timeout_ms)
        page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
        page.wait_for_function("() => !!window.jupyterapp", timeout=timeout_ms)

        opfs_before = _notebook_json_text("s5-on-disk-before-choose")
        seed_opfs = page.evaluate(_PERSISTENCE_OPFS_WRITE_FILES_JS, {"persist-probe.ipynb": opfs_before})
        out["seed_opfs_ok"] = bool(seed_opfs.get("ok"))
        out["seed_opfs_error"] = seed_opfs.get("error")

        seeded = page.evaluate(
            _persistence_seed_notebook_with_source_js("persist-probe.ipynb", "s5-drive-version")
        )
        out["seed_drive_ok"] = bool(seeded.get("ok"))
        out["seed_drive_error"] = seeded.get("error")

        page.click("[data-praxis-action=toggle-panel]", timeout=timeout_ms)
        page.click("[data-praxis-action=choose-folder]", timeout=timeout_ms)

        def _excluded_one() -> bool:
            return page.get_attribute("#praxis-persistence", "data-praxis-excluded") == "1"

        _poll_until(_excluded_one, timeout_s=timeout_ms / 1000)
        out["excluded_after_choose"] = page.get_attribute("#praxis-persistence", "data-praxis-excluded")
        chip_text = page.eval_on_selector("[data-praxis-action=toggle-panel]", "(el) => el.textContent") or ""
        out["differs_excluded"] = out["excluded_after_choose"] == "1" and "(1 not mirrored)" in chip_text

        disk_before_save = page.evaluate(_PERSISTENCE_OPFS_READ_FILE_JS, "persist-probe.ipynb")

        _open_existing_notebook(page, "persist-probe.ipynb", timeout_ms=timeout_ms)
        # Force real dirtiness (a no-op net edit) so the explicit save below
        # is a genuine content-changing save, not a skipped no-op save --
        # the exclusion must hold even though a real fileChanged "save"
        # fires.
        cell = page.locator(".jp-Notebook .jp-CodeCell .cm-content").first
        cell.wait_for(state="visible", timeout=timeout_ms)
        cell.click()
        page.keyboard.press("End")
        page.keyboard.type(" ")
        page.keyboard.press("Backspace")
        page.keyboard.press("Control+s")
        page.wait_for_timeout(800)  # give the (must-be-skipped) mirror chain a chance to run

        disk_after_save = page.evaluate(_PERSISTENCE_OPFS_READ_FILE_JS, "persist-probe.ipynb")
        out["differs_disk_untouched_after_save"] = (
            disk_after_save.get("text") == disk_before_save.get("text") == opfs_before
        )

        panel_hidden = page.eval_on_selector("#praxis-persistence > div", "(el) => el.hidden")
        if panel_hidden:
            page.click("[data-praxis-action=toggle-panel]", timeout=timeout_ms)
        page.click(
            '[data-praxis-action=replace-disk-copy][data-praxis-path="persist-probe.ipynb"]',
            timeout=timeout_ms,
        )

        def _excluded_zero() -> bool:
            return page.get_attribute("#praxis-persistence", "data-praxis-excluded") == "0"

        _poll_until(_excluded_zero, timeout_s=timeout_ms / 1000)
        out["excluded_after_replace"] = page.get_attribute("#praxis-persistence", "data-praxis-excluded")

        disk_after_replace = page.evaluate(_PERSISTENCE_OPFS_READ_FILE_JS, "persist-probe.ipynb")
        drive_after_replace = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, "persist-probe.ipynb")
        out["replace_writes"] = out["excluded_after_replace"] == "0" and _cells_match(
            disk_after_replace.get("text"), drive_after_replace.get("content")
        )
    finally:
        context.close()
    return out


def _run_persistence_scenario_s6(
    browser: Any, served: ServedDir, prefix: str, timeout_ms: float
) -> dict[str, Any]:
    """S6 (AC-10, B-1/B-3): fresh context, drive seeded with
    persist-probe.ipynb. Binds through the PANEL's Choose working folder
    before any save (B-3: this alone sets the ack to "folder"), forces
    queryPermission to "prompt", reloads, makes a real explicit Control+S
    save while paused (the pending set must persist it), reloads again with
    the flag still set, then Reconnects with a real click. The first-save
    gate dialog is polled after EVERY step -- it must never open
    (gate_never_opened_s6), because the ack was already set by the bind."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    out: dict[str, Any] = {}
    dialog_checks: list[bool] = []
    context = browser.new_context()
    context.add_init_script(PERSISTENCE_BASE_INIT_SCRIPT)
    context.add_init_script(PERSISTENCE_PICKER_STUB_INIT_SCRIPT)
    try:
        page = context.new_page()
        lab_url = f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
        page.goto(lab_url, wait_until="load", timeout=timeout_ms)
        page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
        page.wait_for_function("() => !!window.jupyterapp", timeout=timeout_ms)
        dialog_checks.append(_dialog_open(page))

        seeded = page.evaluate(_persistence_seed_notebook_with_source_js("persist-probe.ipynb", "s6-initial"))
        out["seed_ok"] = bool(seeded.get("ok"))
        out["seed_error"] = seeded.get("error")

        # -- bind through the panel, before any save (B-3) --------------------
        page.click("[data-praxis-action=toggle-panel]", timeout=timeout_ms)
        page.click("[data-praxis-action=choose-folder]", timeout=timeout_ms)
        page.wait_for_function(
            "() => document.querySelector('#praxis-persistence')"
            "?.getAttribute('data-praxis-tier') === 'L2'",
            timeout=timeout_ms,
        )
        dialog_checks.append(_dialog_open(page))

        disk_before_edit = page.evaluate(_PERSISTENCE_OPFS_READ_FILE_JS, "persist-probe.ipynb")
        out["disk_after_bind_exists"] = disk_before_edit.get("exists")

        # -- force "prompt", reload --------------------------------------------
        page.evaluate("() => window.localStorage.setItem('__praxis_test_force_prompt', '1')")
        page.reload(wait_until="load", timeout=timeout_ms)
        page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
        try:
            page.wait_for_function(
                "() => document.querySelector('#praxis-persistence')"
                "?.getAttribute('data-praxis-tier') === 'L2-paused'",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            pass
        out["tier_on_prompt"] = page.get_attribute("#praxis-persistence", "data-praxis-tier")
        dialog_checks.append(_dialog_open(page))

        # -- explicit Control+S save while paused ------------------------------
        _open_existing_notebook(page, "persist-probe.ipynb", timeout_ms=timeout_ms)
        _replace_first_cell_source(page, "s6-edited", timeout_ms=timeout_ms)
        page.keyboard.press("Control+s")
        drive_after_edit_save = _poll_drive_cell_source_contains(
            page, "persist-probe.ipynb", "s6-edited", timeout_s=timeout_ms / 1000
        )
        dialog_checks.append(_dialog_open(page))  # right after Control+S (D4)

        out["paused_save_not_written"] = (
            page.evaluate(_PERSISTENCE_OPFS_READ_FILE_JS, "persist-probe.ipynb").get("text")
            == disk_before_edit.get("text")
        )

        # -- reload again, flag still set: pending survives ---------------------
        page.reload(wait_until="load", timeout=timeout_ms)
        page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
        try:
            page.wait_for_function(
                "() => document.querySelector('#praxis-persistence')"
                "?.getAttribute('data-praxis-tier') === 'L2-paused'",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            pass
        out["tier_after_second_reload"] = page.get_attribute("#praxis-persistence", "data-praxis-tier")
        out["pending_survives_reload"] = out["tier_after_second_reload"] == "L2-paused"
        dialog_checks.append(_dialog_open(page))

        # -- real click Reconnect -----------------------------------------------
        page.click("[data-praxis-action=toggle-panel]", timeout=timeout_ms)
        page.click("[data-praxis-action=reconnect]", timeout=timeout_ms)
        dialog_checks.append(_dialog_open(page))  # right after the click, during the flush
        try:
            page.wait_for_function(
                "() => document.querySelector('#praxis-persistence')"
                "?.getAttribute('data-praxis-tier') === 'L2'",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            pass
        out["tier_after_reconnect"] = page.get_attribute("#praxis-persistence", "data-praxis-tier")
        dialog_checks.append(_dialog_open(page))

        disk_after_reconnect = page.evaluate(_PERSISTENCE_OPFS_READ_FILE_JS, "persist-probe.ipynb")
        out["reconnect_flushed_matches"] = out["tier_after_reconnect"] == "L2" and _cells_match(
            disk_after_reconnect.get("text"), drive_after_edit_save.get("content")
        )

        out["dialog_checks"] = dialog_checks
        out["gate_never_opened_s6"] = not any(dialog_checks)
    finally:
        context.close()
    return out


def _run_persistence_scenario_s7(
    browser: Any, served: ServedDir, prefix: str, timeout_ms: float
) -> dict[str, Any]:
    """S7 (AC-10, restore): fresh context with a bound folder. OPFS is seeded
    with sub/restore-me.ipynb and a dot-prefixed .hidden file (both absent
    from the drive); the drive holds persist-probe.ipynb whose content
    differs from the disk copy (bulk sync excludes it -- restore must still
    never overwrite a drive-present path, excluded or not)."""
    out: dict[str, Any] = {}
    context = browser.new_context()
    context.add_init_script(PERSISTENCE_BASE_INIT_SCRIPT)
    context.add_init_script(PERSISTENCE_PICKER_STUB_INIT_SCRIPT)
    try:
        page = context.new_page()
        lab_url = f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
        page.goto(lab_url, wait_until="load", timeout=timeout_ms)
        page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
        page.wait_for_function("() => !!window.jupyterapp", timeout=timeout_ms)

        restore_me_text = _notebook_json_text("restore-me-content")
        opfs_probe_text = _notebook_json_text("s7-on-disk")
        seed_opfs = page.evaluate(
            _PERSISTENCE_OPFS_WRITE_FILES_JS,
            {
                "sub/restore-me.ipynb": restore_me_text,
                ".hidden": "should not restore",
                "persist-probe.ipynb": opfs_probe_text,
            },
        )
        out["seed_opfs_ok"] = bool(seed_opfs.get("ok"))
        out["seed_opfs_error"] = seed_opfs.get("error")

        seeded = page.evaluate(_persistence_seed_notebook_with_source_js("persist-probe.ipynb", "s7-drive"))
        out["seed_drive_ok"] = bool(seeded.get("ok"))
        drive_probe_before = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, "persist-probe.ipynb")

        # -- bind (starting state: "fresh context with a bound folder") --------
        page.click("[data-praxis-action=toggle-panel]", timeout=timeout_ms)
        page.click("[data-praxis-action=choose-folder]", timeout=timeout_ms)

        def _excluded_one() -> bool:
            return page.get_attribute("#praxis-persistence", "data-praxis-excluded") == "1"

        _poll_until(_excluded_one, timeout_s=timeout_ms / 1000)
        out["excluded_after_choose"] = page.get_attribute("#praxis-persistence", "data-praxis-excluded")

        # -- real click Restore ---------------------------------------------------
        page.click("[data-praxis-action=restore]", timeout=timeout_ms)

        def _restored() -> bool:
            d = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, "sub/restore-me.ipynb")
            return bool(d.get("exists"))

        _poll_until(_restored, timeout_s=timeout_ms / 1000)

        drive_restored = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, "sub/restore-me.ipynb")
        out["restore_matches"] = _cells_match(restore_me_text, drive_restored.get("content"))

        drive_hidden = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, ".hidden")
        out["restore_skipped_dotfile"] = drive_hidden.get("exists") is False

        drive_probe_after = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, "persist-probe.ipynb")
        out["restore_did_not_overwrite"] = drive_probe_after.get("content") == drive_probe_before.get("content")
    finally:
        context.close()
    return out


def _run_persistence_scenario_s8(
    browser: Any, served: ServedDir, prefix: str, timeout_ms: float
) -> dict[str, Any]:
    """S8 (AC-11): fresh context, drive seeded with persist-probe.ipynb (one
    editable cell). A real click into the notebook plus a real Control+S
    opens the first-save gate modal. Proves Escape (twice -- Chromium's
    CloseWatcher makes the SECOND consecutive Escape non-cancelable) and a
    backdrop click do NOT close it, and that a real choose-folder click
    does."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    out: dict[str, Any] = {}
    context = browser.new_context()
    context.add_init_script(PERSISTENCE_BASE_INIT_SCRIPT)
    context.add_init_script(PERSISTENCE_PICKER_STUB_INIT_SCRIPT)
    try:
        page = context.new_page()
        lab_url = f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
        page.goto(lab_url, wait_until="load", timeout=timeout_ms)
        page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
        page.wait_for_function("() => !!window.jupyterapp", timeout=timeout_ms)

        seeded = page.evaluate(_persistence_seed_notebook_with_source_js("persist-probe.ipynb", ""))
        out["seed_ok"] = bool(seeded.get("ok"))

        _open_existing_notebook(page, "persist-probe.ipynb", timeout_ms=timeout_ms)
        _replace_first_cell_source(page, "s8-marker", timeout_ms=timeout_ms)
        page.keyboard.press("Control+s")

        page.wait_for_selector("dialog#praxis-persistence-first-save[open]", timeout=timeout_ms)
        out["modal_open"] = bool(
            page.evaluate(
                "() => document.querySelector('dialog#praxis-persistence-first-save')?.open === true"
            )
        )
        out["modal_focus_inside"] = bool(
            page.evaluate(
                "() => { const d = document.querySelector('dialog#praxis-persistence-first-save');"
                " return !!(d && d.contains(document.activeElement)); }"
            )
        )

        drive_after_first_save = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, "persist-probe.ipynb")
        out["save_landed_before_modal"] = "s8-marker" in _cell_source_text(
            (drive_after_first_save.get("content") or {}).get("cells")
        )

        # -- Escape x2: the SECOND press is non-cancelable (CloseWatcher); the
        # dialog must re-arm itself on `close` when no choice is recorded.
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        out["modal_survives_double_escape"] = bool(
            page.evaluate(
                "() => { const d = document.querySelector('dialog#praxis-persistence-first-save');"
                " return !!(d && d.open && d.contains(document.activeElement)); }"
            )
        )

        # -- backdrop click: no listener closes the dialog on it -----------------
        page.mouse.click(2, 2)
        page.wait_for_timeout(200)
        out["modal_survives_backdrop_click"] = bool(
            page.evaluate(
                "() => document.querySelector('dialog#praxis-persistence-first-save')?.open === true"
            )
        )

        # -- choosing a folder (real click) closes it -----------------------------
        page.click(
            "dialog#praxis-persistence-first-save [data-praxis-action=choose-folder]",
            timeout=timeout_ms,
        )
        try:
            page.wait_for_selector(
                "dialog#praxis-persistence-first-save[open]", state="detached", timeout=timeout_ms
            )
            out["modal_closed"] = True
        except PlaywrightTimeoutError:
            out["modal_closed"] = not bool(
                page.evaluate(
                    "() => document.querySelector('dialog#praxis-persistence-first-save')?.open === true"
                )
            )

        # -- a second explicit save must NOT reopen it -----------------------------
        try:
            page.wait_for_function(
                "() => document.querySelector('#praxis-persistence')"
                "?.getAttribute('data-praxis-tier') === 'L2'",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            pass
        page.click(".jp-Notebook .jp-CodeCell .cm-content", timeout=timeout_ms)
        page.keyboard.press("Control+s")
        page.wait_for_timeout(500)
        out["modal_reopened"] = bool(
            page.evaluate(
                "() => document.querySelector('dialog#praxis-persistence-first-save')?.open === true"
            )
        )
    finally:
        context.close()
    return out


def _run_persistence_scenario_s9(
    browser: Any, served: ServedDir, prefix: str, timeout_ms: float
) -> dict[str, Any]:
    """S9 (AC-11): fresh context. Create Untitled.ipynb via File -> New ->
    Notebook (real menu clicks, not the harness's contents.newUntitled
    shortcut used elsewhere), type a marker into the first cell, and press a
    real Control+S. JupyterLab's rename-untitled-on-save dialog must appear
    BEFORE the gate modal (D4: the command's `evt.result` only resolves once
    that dialog is answered and the save completes); the gate then opens, and
    the RENAMED file holds the marker by content."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    out: dict[str, Any] = {}
    context = browser.new_context()
    context.add_init_script(PERSISTENCE_BASE_INIT_SCRIPT)
    try:
        page = context.new_page()
        lab_url = f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
        page.goto(lab_url, wait_until="load", timeout=timeout_ms)
        page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
        page.wait_for_function("() => !!window.jupyterapp", timeout=timeout_ms)

        # -- File -> New -> Notebook, real menu clicks -----------------------------
        page.click(".lm-MenuBar-item:has-text('File')", timeout=timeout_ms)
        page.click(".lm-Menu-itemLabel:has-text('New')", timeout=timeout_ms)
        page.click(".lm-Menu-itemLabel:text-is('Notebook')", timeout=timeout_ms)

        # A kernel-selection dialog may appear before the notebook is usable.
        try:
            page.wait_for_selector(".jp-Dialog", timeout=10_000)
            page.click(".jp-Dialog .jp-mod-accept")
            page.wait_for_selector(".jp-Dialog", state="detached", timeout=timeout_ms)
        except PlaywrightTimeoutError:
            pass

        page.wait_for_function("() => !!document.querySelector('.jp-Notebook')", timeout=timeout_ms)
        _replace_first_cell_source(page, "s9-marker", timeout_ms=timeout_ms)

        page.keyboard.press("Control+s")

        # -- JupyterLab's rename-untitled dialog ------------------------------------
        page.wait_for_selector(".jp-Dialog", timeout=timeout_ms)
        out["rename_dialog_before_gate"] = not _dialog_open(page)
        name_input = page.locator(".jp-Dialog input[type=text], .jp-Dialog .jp-mod-styled input").first
        name_input.wait_for(state="visible", timeout=timeout_ms)
        name_input.click()
        page.keyboard.press("Control+a")
        page.keyboard.type("renamed-probe.ipynb")
        page.click(".jp-Dialog .jp-mod-accept", timeout=timeout_ms)
        page.wait_for_selector(".jp-Dialog", state="detached", timeout=timeout_ms)

        # -- gate then opens ----------------------------------------------------------
        page.wait_for_selector("dialog#praxis-persistence-first-save[open]", timeout=timeout_ms)
        out["gate_after_rename"] = _dialog_open(page)

        drive = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, "renamed-probe.ipynb")
        out["renamed_file_saved"] = "s9-marker" in _cell_source_text((drive.get("content") or {}).get("cells"))
        out["renamed_drive_exists"] = drive.get("exists")
    finally:
        context.close()
    return out


def _run_persistence_scenario_s10(
    browser: Any, served: ServedDir, prefix: str, timeout_ms: float
) -> dict[str, Any]:
    """S10 (AC-12): fresh context, drive seeded with persist-probe.ipynb.
    Proves native JupyterLab Download and Upload round-trip BY CONTENT, using
    Playwright's download/filechooser events fired from real UI clicks -- no
    praxis export code exists (D3): this scenario is what decides whether
    T10's contingent Download button is actually needed."""
    out: dict[str, Any] = {}
    context = browser.new_context(accept_downloads=True)
    context.add_init_script(PERSISTENCE_BASE_INIT_SCRIPT)
    try:
        page = context.new_page()
        lab_url = f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
        page.goto(lab_url, wait_until="load", timeout=timeout_ms)
        page.wait_for_selector("#praxis-persistence", state="attached", timeout=timeout_ms)
        page.wait_for_function("() => !!window.jupyterapp", timeout=timeout_ms)

        seeded = page.evaluate(_persistence_seed_notebook_with_source_js("persist-probe.ipynb", "s10-drive"))
        out["seed_ok"] = bool(seeded.get("ok"))

        drive_before = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, "persist-probe.ipynb")

        # -- Download: right-click the file row in the file browser, click Download --
        try:
            row = page.locator(".jp-DirListing-item", has_text="persist-probe.ipynb").first
            row.wait_for(state="visible", timeout=timeout_ms)
            row.click(button="right")
            page.wait_for_selector(".lm-Menu-itemLabel:text-is('Download')", timeout=timeout_ms)
            with page.expect_download(timeout=timeout_ms) as download_info:
                page.click(".lm-Menu-itemLabel:text-is('Download')", timeout=timeout_ms)
            download = download_info.value
            tmp_path = Path(tempfile.mkdtemp()) / "downloaded-persist-probe.ipynb"
            download.save_as(str(tmp_path))
            downloaded_text = tmp_path.read_text()
            out["download_matches"] = _cells_match(downloaded_text, drive_before.get("content"))
        except Exception as e:  # noqa: BLE001 -- report, don't crash the whole run
            out["download_matches"] = False
            out["download_error"] = f"{type(e).__name__}: {e}"

        # -- Upload: real click on Upload, real file chooser --------------------------
        try:
            upload_marker = "s10-upload-marker"
            upload_text = _notebook_json_text(upload_marker)
            upload_content = json.loads(upload_text)
            tmp_upload_dir = Path(tempfile.mkdtemp())
            tmp_upload_path = tmp_upload_dir / "upload-probe.ipynb"
            tmp_upload_path.write_text(upload_text)

            upload_button = page.locator("[title='Upload Files'], [title='Upload']").first
            upload_button.wait_for(state="visible", timeout=timeout_ms)
            with page.expect_file_chooser(timeout=timeout_ms) as fc_info:
                upload_button.click(timeout=timeout_ms)
            file_chooser = fc_info.value
            file_chooser.set_files(str(tmp_upload_path))

            def _uploaded() -> bool:
                d = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, "upload-probe.ipynb")
                return bool(d.get("exists"))

            _poll_until(_uploaded, timeout_s=timeout_ms / 1000)
            drive_uploaded = page.evaluate(_PERSISTENCE_DRIVE_GET_JS, "upload-probe.ipynb")
            decoded = _decode_notebook_content(
                drive_uploaded.get("content"), drive_uploaded.get("format")
            )
            out["upload_matches"] = decoded is not None and decoded.get("cells") == upload_content.get(
                "cells"
            )
            out["upload_drive_format"] = drive_uploaded.get("format")
        except Exception as e:  # noqa: BLE001
            out["upload_matches"] = False
            out["upload_error"] = f"{type(e).__name__}: {e}"
    finally:
        context.close()
    return out


def _ensure_persistence_browser(
    p: Any, browser: Any, *, chrome_path: str, offline: bool, scenario_label: str
) -> Any:
    """Relaunch the shared `--persistence-check` browser if it died under a
    PRIOR scenario, instead of letting one browser-process crash cascade into
    every remaining scenario reporting a misleading "browser has been closed"
    (masking which scenario, if any, actually broke). Observed root cause
    (260922): a genuine Chromium-level crash -- not anything in this harness or
    in the product's persistence JS -- see the `playwright` pin comment in
    pyproject.toml for the full diagnosis. This function does not change what
    any scenario asserts; it only decides which browser instance a scenario
    runs against.
    """
    if browser.is_connected():
        return browser
    LOG.warning(
        "persistence-check: browser was disconnected before %s -- relaunching",
        scenario_label,
    )
    return p.chromium.launch(
        executable_path=chrome_path,
        headless=True,
        args=chromium_launch_args(offline=offline),
    )


def run_persistence_check(
    *,
    serve_dir: Path,
    base_path: str,
    chrome_path: str,
    timeout_s: float,
    offline: bool = False,
) -> dict[str, Any]:
    """--persistence-check: T8a (S1-S3 / AC-8, AC-9, AC-13, AC-14, AC-17) plus
    T8b (S4-S10 / AC-10, AC-11, AC-12).

    Follows the existing check shape (ServedDir, chromium_launch_args, a
    `result` dict with `failures`) -- see `run_typeahead_check` above.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:  # pragma: no cover - environment problem
        raise RuntimeError(f"playwright is not importable: {e}") from e

    prefix = _normalize_base_path(base_path)
    timeout_ms = timeout_s * 1000
    result: dict[str, Any] = {"failures": []}

    with ServedDir(serve_dir, base_path, coi=False) as served:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=chrome_path,
                headless=True,
                args=chromium_launch_args(offline=offline),
            )
            try:
                try:
                    s1 = _run_persistence_scenario_s1(browser, served, prefix, timeout_ms)
                except Exception as e:  # keep going -- AC-17 needs a partial result, not a crash
                    LOG.warning("persistence-check S1 raised: %s: %s", type(e).__name__, e)
                    s1 = {"error": f"{type(e).__name__}: {e}"}
                result["s1"] = s1

                browser = _ensure_persistence_browser(
                    p, browser, chrome_path=chrome_path, offline=offline, scenario_label="S2"
                )
                try:
                    s2 = _run_persistence_scenario_s2(browser, served, prefix, timeout_ms)
                except Exception as e:
                    LOG.warning("persistence-check S2 raised: %s: %s", type(e).__name__, e)
                    s2 = {"error": f"{type(e).__name__}: {e}"}
                result["s2"] = s2

                browser = _ensure_persistence_browser(
                    p, browser, chrome_path=chrome_path, offline=offline, scenario_label="S3"
                )
                try:
                    s3 = _run_persistence_scenario_s3(browser, served, prefix, timeout_ms)
                except Exception as e:
                    LOG.warning("persistence-check S3 raised: %s: %s", type(e).__name__, e)
                    s3 = {"error": f"{type(e).__name__}: {e}"}
                result["s3"] = s3

                browser = _ensure_persistence_browser(
                    p, browser, chrome_path=chrome_path, offline=offline, scenario_label="S4"
                )
                try:
                    s4 = _run_persistence_scenario_s4(browser, served, prefix, timeout_ms)
                except Exception as e:
                    LOG.warning("persistence-check S4 raised: %s: %s", type(e).__name__, e)
                    s4 = {"error": f"{type(e).__name__}: {e}"}
                result["s4"] = s4

                browser = _ensure_persistence_browser(
                    p, browser, chrome_path=chrome_path, offline=offline, scenario_label="S5"
                )
                try:
                    s5 = _run_persistence_scenario_s5(browser, served, prefix, timeout_ms)
                except Exception as e:
                    LOG.warning("persistence-check S5 raised: %s: %s", type(e).__name__, e)
                    s5 = {"error": f"{type(e).__name__}: {e}"}
                result["s5"] = s5

                browser = _ensure_persistence_browser(
                    p, browser, chrome_path=chrome_path, offline=offline, scenario_label="S6"
                )
                try:
                    s6 = _run_persistence_scenario_s6(browser, served, prefix, timeout_ms)
                except Exception as e:
                    LOG.warning("persistence-check S6 raised: %s: %s", type(e).__name__, e)
                    s6 = {"error": f"{type(e).__name__}: {e}"}
                result["s6"] = s6

                browser = _ensure_persistence_browser(
                    p, browser, chrome_path=chrome_path, offline=offline, scenario_label="S7"
                )
                try:
                    s7 = _run_persistence_scenario_s7(browser, served, prefix, timeout_ms)
                except Exception as e:
                    LOG.warning("persistence-check S7 raised: %s: %s", type(e).__name__, e)
                    s7 = {"error": f"{type(e).__name__}: {e}"}
                result["s7"] = s7

                browser = _ensure_persistence_browser(
                    p, browser, chrome_path=chrome_path, offline=offline, scenario_label="S8"
                )
                try:
                    s8 = _run_persistence_scenario_s8(browser, served, prefix, timeout_ms)
                except Exception as e:
                    LOG.warning("persistence-check S8 raised: %s: %s", type(e).__name__, e)
                    s8 = {"error": f"{type(e).__name__}: {e}"}
                result["s8"] = s8

                browser = _ensure_persistence_browser(
                    p, browser, chrome_path=chrome_path, offline=offline, scenario_label="S9"
                )
                try:
                    s9 = _run_persistence_scenario_s9(browser, served, prefix, timeout_ms)
                except Exception as e:
                    LOG.warning("persistence-check S9 raised: %s: %s", type(e).__name__, e)
                    s9 = {"error": f"{type(e).__name__}: {e}"}
                result["s9"] = s9

                browser = _ensure_persistence_browser(
                    p, browser, chrome_path=chrome_path, offline=offline, scenario_label="S10"
                )
                try:
                    s10 = _run_persistence_scenario_s10(browser, served, prefix, timeout_ms)
                except Exception as e:
                    LOG.warning("persistence-check S10 raised: %s: %s", type(e).__name__, e)
                    s10 = {"error": f"{type(e).__name__}: {e}"}
                result["s10"] = s10
            finally:
                # `browser` may already be a dead process (crashed under some
                # earlier scenario, never relaunched because nothing after S10
                # needed it) -- closing an already-disconnected browser raises,
                # which would mask whatever real failures are already in
                # `result`. Best-effort only.
                try:
                    browser.close()
                except Exception:  # noqa: BLE001 -- see comment above
                    pass

    failures: list[str] = result["failures"]

    # -- AC-8 -----------------------------------------------------------------
    indicator_present = s1.get("indicator_present_before_save")
    result["indicator_present_before_save"] = indicator_present
    if indicator_present is not True:
        failures.append(
            f"AC-8 indicator_present_before_save: expected True, got {indicator_present!r} -- "
            "the #praxis-persistence chip never appeared on the lab entry before any save"
        )
    initial_tier = s1.get("initial_tier")
    result["initial_tier"] = initial_tier
    if initial_tier not in ("L0", "L1"):
        failures.append(f"AC-8 initial_tier: expected 'L0' or 'L1', got {initial_tier!r}")
    repl_entry_has_chip = s1.get("repl_entry_has_chip")
    result["repl_entry_has_chip"] = repl_entry_has_chip
    if repl_entry_has_chip is not False:
        failures.append(f"AC-8 repl_entry_has_chip: expected False, got {repl_entry_has_chip!r}")

    # -- AC-9 -----------------------------------------------------------------
    gesture_log = s2.get("gesture_log") or []
    result["gesture_log"] = gesture_log
    required_apis = {"persist", "showDirectoryPicker", "requestPermission"}
    seen_apis = {e.get("api") for e in gesture_log}
    missing_apis = required_apis - seen_apis
    if missing_apis:
        failures.append(f"AC-9 gesture_log: missing entries for {sorted(missing_apis)}")
    for entry in gesture_log:
        if entry.get("api") in required_apis and (
            entry.get("userActivation") is not True or entry.get("inClickDispatch") is not True
        ):
            failures.append(f"AC-9 gesture_log entry not gesture-synchronous: {entry}")

    picker_calls = s2.get("picker_calls")
    result["picker_calls"] = picker_calls
    if picker_calls != 1:
        failures.append(f"AC-9 picker_calls: expected 1, got {picker_calls!r}")

    persist_returned = s2.get("persist_returned")
    tier_after_persist = s2.get("tier_after_persist")
    result["persist_returned"] = persist_returned  # no assertion on the VALUE (AC-9)
    result["tier_after_persist"] = tier_after_persist
    expected_tier_after_persist = "L1" if persist_returned is True else "L0"
    if tier_after_persist != expected_tier_after_persist:
        failures.append(
            f"AC-9 tier_after_persist: persist_returned={persist_returned!r} implies "
            f"{expected_tier_after_persist!r}, got {tier_after_persist!r}"
        )
    result["permission_methods_polyfilled"] = s2.get("permission_methods_polyfilled")

    # -- AC-13 ------------------------------------------------------------
    result["nofsa_l2_controls"] = s3.get("nofsa_l2_controls")
    if result["nofsa_l2_controls"] != 0:
        failures.append(f"AC-13 nofsa_l2_controls: expected 0, got {result['nofsa_l2_controls']!r}")
    result["nofsa_message_mentions_chromium"] = s3.get("nofsa_message_mentions_chromium")
    if result["nofsa_message_mentions_chromium"] is not True:
        failures.append(
            "AC-13 nofsa_message_mentions_chromium: expected True, got "
            f"{result['nofsa_message_mentions_chromium']!r}"
        )
    result["nofsa_modal_choose_absent"] = s3.get("nofsa_modal_choose_absent")
    if result["nofsa_modal_choose_absent"] is not True:
        failures.append(
            "AC-13 nofsa_modal_choose_absent: expected True, got "
            f"{result['nofsa_modal_choose_absent']!r}"
        )
    result["nofsa_indicator_present"] = s3.get("nofsa_indicator_present")
    if result["nofsa_indicator_present"] is not True:
        failures.append(
            f"AC-13 nofsa_indicator_present: expected True, got {result['nofsa_indicator_present']!r}"
        )

    # -- AC-14 ------------------------------------------------------------
    result["indexeddb_names"] = s2.get("indexeddb_names")
    result["hygiene_no_legacy_jupyterlite_dbs"] = s2.get("hygiene_no_legacy_jupyterlite_dbs")
    if result["hygiene_no_legacy_jupyterlite_dbs"] is not True:
        failures.append(
            "AC-14 hygiene_no_legacy_jupyterlite_dbs: expected True, got "
            f"{result['hygiene_no_legacy_jupyterlite_dbs']!r}"
        )
    result["hygiene_one_praxis_repl_contents"] = s2.get("hygiene_one_praxis_repl_contents")
    if result["hygiene_one_praxis_repl_contents"] is not True:
        failures.append(
            "AC-14 hygiene_one_praxis_repl_contents: expected True, got "
            f"{result['hygiene_one_praxis_repl_contents']!r}"
        )
    result["hygiene_praxis_repl_persistence_present"] = s2.get("hygiene_praxis_repl_persistence_present")
    if result["hygiene_praxis_repl_persistence_present"] is not True:
        failures.append(
            "AC-14 hygiene_praxis_repl_persistence_present: expected True, got "
            f"{result['hygiene_praxis_repl_persistence_present']!r}"
        )
    result["hygiene_probe_readable"] = s2.get("hygiene_probe_readable")
    if result["hygiene_probe_readable"] is not True:
        failures.append(
            f"AC-14 hygiene_probe_readable: expected True, got {result['hygiene_probe_readable']!r}"
        )

    # -- AC-10 (S4: L2 by content) ---------------------------------------------
    for key in (
        "mirror_after_choose_matches",
        "mirror_after_resave_matches",
        "rehydrated_without_picker",
        "rehydrated_folder_name_matches",
    ):
        result[key] = s4.get(key)
        if result[key] is not True:
            failures.append(f"AC-10 S4 {key}: expected True, got {result[key]!r}")
    result["picker_calls_s4"] = s4.get("picker_calls")

    # -- AC-10 (S5: differs-on-disk exclusion) ---------------------------------
    for key in ("differs_excluded", "differs_disk_untouched_after_save", "replace_writes"):
        result[key] = s5.get(key)
        if result[key] is not True:
            failures.append(f"AC-10 S5 {key}: expected True, got {result[key]!r}")

    # -- AC-10 (S6: paused save, persisted pending set, no gate) ---------------
    result["tier_on_prompt"] = s6.get("tier_on_prompt")
    if result["tier_on_prompt"] != "L2-paused":
        failures.append(f"AC-10 S6 tier_on_prompt: expected 'L2-paused', got {result['tier_on_prompt']!r}")
    for key in (
        "paused_save_not_written",
        "pending_survives_reload",
        "reconnect_flushed_matches",
        "gate_never_opened_s6",
    ):
        result[key] = s6.get(key)
        if result[key] is not True:
            failures.append(f"AC-10 S6 {key}: expected True, got {result[key]!r}")

    # -- AC-10 (S7: restore) ---------------------------------------------------
    for key in ("restore_matches", "restore_skipped_dotfile", "restore_did_not_overwrite"):
        result[key] = s7.get(key)
        if result[key] is not True:
            failures.append(f"AC-10 S7 {key}: expected True, got {result[key]!r}")

    # -- AC-11 (S8: first-save gate -- Escape, backdrop, choose) ---------------
    for key in (
        "modal_open",
        "modal_focus_inside",
        "save_landed_before_modal",
        "modal_survives_double_escape",
        "modal_survives_backdrop_click",
        "modal_closed",
    ):
        result[key] = s8.get(key)
        if result[key] is not True:
            failures.append(f"AC-11 S8 {key}: expected True, got {result[key]!r}")
    result["modal_reopened"] = s8.get("modal_reopened")
    if result["modal_reopened"] is not False:
        failures.append(f"AC-11 S8 modal_reopened: expected False, got {result['modal_reopened']!r}")

    # -- AC-11 (S9: untitled rename then the gate) -----------------------------
    for key in ("rename_dialog_before_gate", "gate_after_rename", "renamed_file_saved"):
        result[key] = s9.get(key)
        if result[key] is not True:
            failures.append(f"AC-11 S9 {key}: expected True, got {result[key]!r}")

    # -- AC-12 (S10: native Download/Upload) -----------------------------------
    for key in ("download_matches", "upload_matches"):
        result[key] = s10.get(key)
        if result[key] is not True:
            failures.append(f"AC-12 S10 {key}: expected True, got {result[key]!r}")
    if s10.get("download_error"):
        result["download_error"] = s10["download_error"]
    if s10.get("upload_error"):
        result["upload_error"] = s10["upload_error"]

    for label, scenario in (
        ("S1", s1),
        ("S2", s2),
        ("S3", s3),
        ("S4", s4),
        ("S5", s5),
        ("S6", s6),
        ("S7", s7),
        ("S8", s8),
        ("S9", s9),
        ("S10", s10),
    ):
        if scenario.get("error"):
            failures.append(f"{label} scenario raised an exception: {scenario['error']}")

    result["passed"] = not failures
    return result


#: Runs ONE cell by index via `notebook:run-cell` and reads its outputs back
#: from the notebook MODEL (never the DOM -- JupyterLab 4 windows the
#: notebook, so an off-screen cell's output is not in the DOM at all).
_RUN_ONE_CELL_JS = r"""async (index) => {
    const w = window.jupyterapp.shell.currentWidget;
    w.content.activeCellIndex = index;
    let dispatched = true, dispatch_error = null;
    try {
        await window.jupyterapp.commands.execute('notebook:run-cell');
    } catch (e) {
        dispatched = false;
        dispatch_error = String(e);
    }
    const cell = w.content.model.cells.get(index);
    const outs = cell.outputs;
    const n = outs.length ?? outs.size;
    const chunks = [];
    let has_error_output = false;
    for (let j = 0; j < n; j++) {
        const o = outs.get ? outs.get(j) : outs[j];
        const d = o?.toJSON ? o.toJSON() : o;
        if (!d) continue;
        if (d.output_type === 'error' || d.ename) has_error_output = true;
        if (typeof d.text === 'string') chunks.push(d.text);
        else if (Array.isArray(d.text)) chunks.push(d.text.join(''));
        if (d.data && typeof d.data['text/plain'] === 'string') {
            chunks.push(d.data['text/plain']);
        }
        if (d.ename) chunks.push(d.ename + ': ' + d.evalue);
        if (Array.isArray(d.traceback)) chunks.push(d.traceback.join('\n'));
    }
    return {
        dispatched: dispatched,
        dispatch_error: dispatch_error,
        output_text: chunks.join('\n'),
        has_error_output: has_error_output,
    };
}"""


def run_autosetup_fault_check(
    *,
    serve_dir: Path,
    base_path: str,
    chrome_path: str,
    timeout_s: float,
    faults: list[Fault],
    offline: bool = False,
) -> dict[str, Any]:
    """AC-3/AC-5 fault-injection gate (spec section 8.3, --autosetup-fault-check row).

    Doubles as the negative control the old --fresh-boot-check premise
    (`plr_before == ModuleNotFoundError`) used to provide: if auto-setup never
    ran at all, cell 1 would print its side-effect string instead of being
    blocked, and the assertions below would fail for that reason (spec section
    8.3, table note).

    Cell sources are written directly into the notebook model
    (`cell.sharedModel.setSource`), not typed: the harness creates this
    notebook itself, so there is no pre-existing source worth preserving by
    typing. See the module docstring above for the browser-verification caveat.
    """
    from playwright.sync_api import sync_playwright

    prefix = _normalize_base_path(base_path)
    timeout_ms = timeout_s * 1000
    pageerrors: list[str] = []

    cell_sources = [
        AUTOSETUP_FAULT_SIDE_EFFECT_CELL,
        AUTOSETUP_FAULT_SIDE_EFFECT_CELL,
        AUTOSETUP_FAULT_RETRY_CELL,
        AC1_ZERO_ACTION_LINE,
    ]

    with ServedDir(serve_dir, base_path, coi=False, faults=faults) as served:
        url = f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
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
                page.goto(url, wait_until="load", timeout=timeout_ms)

                notebook_path = _open_blank_notebook(page, timeout_ms=timeout_ms)

                prep = page.evaluate(
                    """(sources) => {
                        const w = window.jupyterapp.shell.currentWidget;
                        const model = w.content.model;
                        while (model.cells.length < sources.length) {
                            model.sharedModel.insertCell(model.cells.length,
                                {cell_type: "code", source: ""});
                        }
                        while (model.cells.length > sources.length) {
                            model.sharedModel.deleteCell(model.cells.length - 1);
                        }
                        for (let i = 0; i < sources.length; i++) {
                            model.cells.get(i).sharedModel.setSource(sources[i]);
                        }
                        return {cell_count: model.cells.length};
                    }""",
                    cell_sources,
                )
                LOG.info("prepared %d cell(s) in the blank notebook", prep.get("cell_count"))

                cell_results: list[dict[str, Any]] = []
                for i in range(len(cell_sources)):
                    r = page.evaluate(_RUN_ONE_CELL_JS, i)
                    LOG.info(
                        "cell %d: dispatched=%s has_error_output=%s output=%r",
                        i, r.get("dispatched"), r.get("has_error_output"),
                        (r.get("output_text") or "")[:200],
                    )
                    cell_results.append(r)

                return {
                    "notebook": notebook_path,
                    "url": url,
                    "cells": cell_sources,
                    "cell_results": cell_results,
                    "pageerrors": pageerrors,
                    "offline": offline,
                    "faults": [dataclasses.asdict(f) for f in faults],
                }
            finally:
                browser.close()


def run_restart_check(
    *,
    serve_dir: Path,
    base_path: str,
    chrome_path: str,
    timeout_s: float,
    offline: bool = False,
) -> dict[str, Any]:
    """AC-7 gate (spec section 8.3, --restart-check row): after AC-1 passes,
    restart the kernel via the kernel API (`session.kernel.restart()` -- no
    command dispatch, so no Select Kernel dialog, S0 finding F7), then run the
    SAME probe cell again and assert `kernel_nonce` changed. See the module
    docstring above for the browser-verification caveat.
    """
    from playwright.sync_api import sync_playwright

    prefix = _normalize_base_path(base_path)
    timeout_ms = timeout_s * 1000
    pageerrors: list[str] = []

    with ServedDir(serve_dir, base_path, coi=False) as served:
        url = f"http://127.0.0.1:{served.port}{prefix}lab/index.html"
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
                page.goto(url, wait_until="load", timeout=timeout_ms)

                notebook_path = _open_blank_notebook(page, timeout_ms=timeout_ms)

                probe_code = build_restart_probe_cell()
                page.evaluate(
                    """(source) => {
                        const w = window.jupyterapp.shell.currentWidget;
                        const model = w.content.model;
                        model.cells.get(0).sharedModel.setSource(source);
                    }""",
                    probe_code,
                )

                before = page.evaluate(_RUN_ONE_CELL_JS, 0)
                before_result = _extract_sentinel_json(before.get("output_text") or "")
                LOG.info("restart-check: before restart %s", before_result)

                restart_outcome = page.evaluate(
                    """async () => {
                        try {
                            const w = window.jupyterapp.shell.currentWidget;
                            await w.sessionContext.session.kernel.restart();
                            return {ok: true};
                        } catch (e) {
                            return {ok: false, error: String(e)};
                        }
                    }"""
                )
                if not restart_outcome.get("ok"):
                    raise NotebookCheckError(
                        f"session.kernel.restart() failed: {restart_outcome.get('error')!r}"
                    )

                page.wait_for_function(
                    """() => {
                        const w = window.jupyterapp?.shell?.currentWidget;
                        return w?.sessionContext?.session?.kernel?.status === 'idle';
                    }""",
                    timeout=timeout_ms,
                )

                after = page.evaluate(_RUN_ONE_CELL_JS, 0)
                after_result = _extract_sentinel_json(after.get("output_text") or "")
                LOG.info("restart-check: after restart %s", after_result)

                return {
                    "notebook": notebook_path,
                    "url": url,
                    "before": before_result,
                    "after": after_result,
                    "pageerrors": pageerrors,
                    "offline": offline,
                }
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
    elif expected.get("shape_count") is None or expected.get("layer_count") is None:
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


# ---------------------------------------------------------------------------
# --display-check (epic 260929_notebook-display-design, task A7; spec D16 and AC-7).
#
# The chrome scenarios D1 (Light) and D1-dark (default Dark), and the preemption-safe unit
# machinery every later browser unit of the epic reuses (D2-D4 in sprint B, K1a/K1b/K2/N-d
# in sprint C). The unit is the scenario: one process, one browser, one fresh context, its own
# result and stamp. `--scenario <id>` runs exactly one unit, bounded by a `Watchdog` armed at
# the unit's D16 budget as its FIRST act; with no `--scenario` the flag is the driver (one
# `unit_runner.run_unit` subprocess per unit, budget + 60 s, stamp-matched resume);
# `--aggregate-only` recomputes nothing and never deletes.
#
# Everything that starts, kills or atomically writes a unit's files comes from
# scripts/unit_runner.py, loaded by path (nothing edits sys.path). The pure functions
# (unit table, input hashing, skip rule, aggregate, key derivation) are tested without a
# browser or the PLR submodule by web-repl/tests/test_repl_smoke_resume.py; the browser
# scenario body (`run_display_scenario`, `DisplaySession`) is exercised only by a real run.
# ---------------------------------------------------------------------------

DISPLAY_CHECK = "display-check"
DISPLAY_NOTEBOOK_NAME = "display_check.ipynb"
DISPLAY_NOTEBOOK_PATH = (
    REPO_ROOT / "web-repl" / "tests" / "fixtures" / "notebooks" / DISPLAY_NOTEBOOK_NAME
)
UNIT_RUNNER_PATH = Path(__file__).resolve().parent / "unit_runner.py"
#: The driver kills a unit at its budget + this; the unit's own watchdog fires at the budget
#: and CI's step timeout is the budget + 2 min, so each outer bound is only a backstop (D16).
DRIVER_EXTRA_S = 60.0

DISPLAY_NAV_TIMEOUT_MS = 90_000
DISPLAY_KERNEL_TIMEOUT_MS = 180_000
DISPLAY_STEP_TIMEOUT_MS = 60_000
#: B10: one cell run in D2-D4 (the FIRST cell of a fresh kernel also waits for the kernel's auto-setup).
DISPLAY_CELL_TIMEOUT_MS = 120_000

#: D16 "Persistence gate": the first-save modal (`dialog#praxis-persistence-first-save`) would
#: block the harness's saves in a fresh context. The key is an existing one (core.js ACK_KEY);
#: this epic adds none.
PERSISTENCE_ACK_INIT_SCRIPT = (
    'window.localStorage.setItem("praxis-repl-persistence-ack", "browser-only");'
)

_UNIT_RUNNER: Any = None


def unit_runner_module() -> Any:
    """``scripts/unit_runner.py`` loaded by path, once, under a private module name."""
    global _UNIT_RUNNER
    if _UNIT_RUNNER is None:
        import importlib.util

        name = "_repl_smoke_unit_runner"
        spec = importlib.util.spec_from_file_location(name, UNIT_RUNNER_PATH)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load the shared unit runner from {UNIT_RUNNER_PATH}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        _UNIT_RUNNER = module
    return _UNIT_RUNNER


# -- The unit table (D16) -------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class HarnessUnit:
    """One D16 unit: its id, check, budget, and the listed keys with the value each must hold.

    ``expected`` is an ordered tuple of ``(key, value)`` pairs; the keys are the "listed keys"
    (the result keys the unit's ACs name). ``budget_s`` is the per-subprocess timeout that the
    unit's own watchdog enforces; estimates from the spec, not measurements (a change needs the
    orchestrator's approval, D16).
    """

    id: str
    check: str
    budget_s: float
    expected: tuple[tuple[str, Any], ...]
    acs: tuple[str, ...] = ()
    #: The viewport list, hashed into the ``args`` input. The spec states none for the chrome
    #: units; 1440x900 is the baseline the spike and dock units use.
    viewports: tuple[tuple[int, int], ...] = ((1440, 900),)
    #: False for a negative-only unit (``N-d``, AC-39(d)): it runs as a ``--scenario`` (the sensitivity driver starts
    #: it) but is never part of the aggregate, which only a check's real units can gate (D16).
    in_aggregate: bool = True

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(k for k, _ in self.expected)


#: AC-21: one output's ``text/html`` is at most this many bytes (D4).
HTML_BYTES_CAP = 65_536
#: AC-24, AC-2 recorded ``s2_b_exec_t``: the executed-saved-reopened path reopens TRUSTED and live (branch S2-T).
_LIVE_LIQUID_FILL = "rgb(115, 169, 194)"  # #73A9C2, the moonstone liquid fill (a brand constant, D3)


@dataclasses.dataclass(frozen=True)
class AtMost:
    """A listed key that holds when its value is a number not above ``limit`` (AC-21 ``html_bytes_max``). The
    unit table's other keys are equalities; a bound cannot be one. Booleans and ``NaN`` never hold."""

    limit: float

    def holds(self, actual: Any) -> bool:
        return (
            isinstance(actual, (int, float)) and not isinstance(actual, bool) and actual == actual and actual <= self.limit
        )

    def example(self) -> float:
        """A value that holds (tests build a passing result from it)."""
        return self.limit

    def __repr__(self) -> str:
        return f"AtMost({self.limit})"


@dataclasses.dataclass(frozen=True)
class AtLeast:
    """A listed key that holds when its value is a number not below ``limit`` (AC-36 ``viewer_height`` >= 300).
    Booleans and ``NaN`` never hold."""

    limit: float

    def holds(self, actual: Any) -> bool:
        return (
            isinstance(actual, (int, float)) and not isinstance(actual, bool) and actual == actual and actual >= self.limit
        )

    def example(self) -> float:
        return self.limit

    def __repr__(self) -> str:
        return f"AtLeast({self.limit})"


@dataclasses.dataclass(frozen=True)
class OneOf:
    """A listed key that holds when its value is one of ``values``, strictly by type (AC-34 ``hello_backend`` is
    ``WebGL2`` or ``WebGPU``: the page's backend, read from the kernel, not a boolean derived from it)."""

    values: tuple[Any, ...]

    def holds(self, actual: Any) -> bool:
        return any(type(actual) is type(v) and actual == v for v in self.values)

    def example(self) -> Any:
        return self.values[0]

    def __repr__(self) -> str:
        return f"OneOf{self.values!r}"


_RAIL_STATE_KEYS = (
    ("rail_state_never_run", "not-run"),
    ("rail_state_after_run", "ran"),
    ("rail_state_while_sleep", "running"),
    ("rail_state_after_raise", "error"),
    ("rail_state_after_edit", "stale"),
)

UNIT_TABLE: tuple[HarnessUnit, ...] = (
    HarnessUnit(
        "D1",
        DISPLAY_CHECK,
        6 * 60.0,
        (
            *_RAIL_STATE_KEYS,
            ("rail_colors_match", True),
            ("prompts_take_no_space", True),
            ("light_ground", "rgb(238, 241, 244)"),
            ("light_sheet", "rgb(255, 255, 255)"),
            ("exec_count_on_rail", True),
            ("pageerrors", []),
        ),
        acs=("AC-7",),
    ),
    HarnessUnit(
        "D1-dark",
        DISPLAY_CHECK,
        5 * 60.0,
        (*_RAIL_STATE_KEYS, ("prompts_take_no_space", True), ("rail_colors_match_dark", True)),
        acs=("AC-7",),
    ),
    HarnessUnit(
        "D2",
        DISPLAY_CHECK,
        12 * 60.0,
        (
            # AC-21 (reprs live)
            ("repr_cells_ok", True),
            ("svg_in_dom", True),
            ("html_bytes_max", AtMost(HTML_BYTES_CAP)),
            ("text_plain_matches", True),
            ("pageerrors", []),
            # AC-22 (error panels live)
            ("error_panels", True),
            ("error_status", True),
            ("runall_stops", True),
            ("other_errors_plain", True),
            # AC-23 (staleness live)
            ("stale_marked", True),
            ("stale_not_persisted", True),
            ("unchanged_not_marked", True),
            ("mark_survives_scroll", True),
            ("earlier_session_marked", True),
            ("rerun_not_marked", True),
            ("persistence_gate_never_open", True),
            # AC-25 (keyboard and text alternative)
            ("svg_role_img", True),
            ("aria_label_equals_summary", True),
            ("tab_focuses_figure", True),
            ("arrow_moves", True),
            ("escape_leaves", True),
        ),
        acs=("AC-21", "AC-22", "AC-23", "AC-25"),
    ),
    HarnessUnit(
        "D3",
        DISPLAY_CHECK,
        8 * 60.0,
        (
            ("no_script_in_bundles", True),
            ("reopened_branch", "S2-T"),  # EXECUTED_REOPEN_BRANCH: the branch AC-2 recorded for this path
            ("persistence_gate_never_open", True),
            # the S2-T branch-conditional keys (the recorded branch); the other branches' keys are evidence only
            ("svg_in_dom", True),
            ("liquid_fill_computed", _LIVE_LIQUID_FILL),
        ),
        acs=("AC-24",),
    ),
    HarnessUnit(
        "D4",
        DISPLAY_CHECK,
        6 * 60.0,
        (("hc_text_color", True), ("hc_sheet_fill", True), ("hc_palette_untouched", True)),
        acs=("AC-26",),
    ),
)
UNIT_BY_ID: dict[str, HarnessUnit] = {u.id: u for u in UNIT_TABLE}


def _holds(actual: Any, expected: Any) -> bool:
    """Strict: a boolean key holds only as that boolean (1 is not True), others by type and value. A bound
    (``AtMost``) holds by its own rule."""
    if isinstance(expected, (AtMost, AtLeast, OneOf)):
        return expected.holds(actual)
    if isinstance(expected, bool):
        return actual is expected
    return type(actual) is type(expected) and actual == expected


def evaluate_unit_result(unit: HarnessUnit, result: Any) -> tuple[list[str], list[str]]:
    """``(missing_keys, failing_keys)`` of a unit's result against its listed keys."""
    if not isinstance(result, dict):
        return list(unit.keys), []
    missing = [k for k, _ in unit.expected if k not in result]
    failing = [k for k, want in unit.expected if k in result and not _holds(result[k], want)]
    return missing, failing


def unit_paths(out_dir: Path, unit_id: str) -> dict[str, Path]:
    """``result.<id>.json``, its stamp (the completion marker) and the timeout marker."""
    out = Path(out_dir)
    return {
        "result": out / f"result.{unit_id}.json",
        "stamp": out / f"result.{unit_id}.stamp.json",
        "timeout": out / f"result.{unit_id}.timeout.json",
    }


def default_out_dir(check: str) -> Path:
    """``outputs/repl_smoke/<check>/`` (gitignored)."""
    return REPO_ROOT / "outputs" / "repl_smoke" / check


def out_dir_rule_error(args: argparse.Namespace) -> str | None:
    """D16 (C8-5): a non-default ``--serve-dir`` or any ``--neg`` needs an explicit ``--out-dir``,
    so a negative or a copied dist can never overwrite the default results. Returns the error
    message (the caller exits 2) or ``None``."""
    non_default_dist = Path(args.serve_dir).resolve() != DEFAULT_SERVE_DIR.resolve()
    if (non_default_dist or args.neg) and args.out_dir is None:
        why = "a non-default --serve-dir" if non_default_dist else "--neg"
        return f"{why} requires an explicit --out-dir (it must never overwrite the default results)"
    return None


# -- Input hashing ---------------------------------------------------------------


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return unit_runner_module()._sha256_file(Path(path))


@dataclasses.dataclass
class HashEnv:
    """Everything a unit's inputs are built from, already hashed (so tests can fake it)."""

    dist: str
    notebook: str
    harness: str
    runner: str
    chrome: str
    driver: str
    base_path: str = "/"
    chrome_path: str = ""
    chrome_version: str = ""


def chrome_version_of(chrome_path: str) -> str:
    """``chrome --version`` output (the only process ``--aggregate-only`` runs)."""
    try:
        proc = subprocess.run(
            [chrome_path, "--version"], capture_output=True, text=True, timeout=30, check=False
        )
        return (proc.stdout or proc.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unavailable: {type(exc).__name__}"


def build_hash_env(
    args: argparse.Namespace,
    chrome_path: str,
    *,
    notebook_path: Path | None = None,
    harness_path: Path | None = None,
    runner_path: Path | None = None,
    driver_fn: Any = None,
    chrome_version_fn: Any = None,
    dist_hash_fn: Any = None,
) -> HashEnv:
    """Resolve and hash the real inputs. Raises ``FileNotFoundError`` for a missing dist,
    notebook or ``uv.lock`` (a missing input is never hashed as empty)."""
    ur = unit_runner_module()
    dist = (dist_hash_fn or ur.dist_hash)(Path(args.serve_dir).resolve())
    version = (chrome_version_fn or chrome_version_of)(chrome_path)
    return HashEnv(
        dist=dist,
        notebook=_sha256_file(notebook_path or DISPLAY_NOTEBOOK_PATH),
        harness=_sha256_file(harness_path or Path(__file__).resolve()),
        runner=_sha256_file(runner_path or UNIT_RUNNER_PATH),
        chrome=_sha256_bytes(f"{chrome_path}\n{version}".encode()),
        driver=(driver_fn or ur.driver_input)(),
        base_path=_normalize_base_path(args.base_path),
        chrome_path=str(chrome_path),
        chrome_version=version,
    )


def unit_inputs(unit: HarnessUnit, env: HashEnv, neg: Any = ()) -> dict[str, str]:
    """The stamp's ``inputs``: dist, notebook, harness, runner, chrome, args, driver (D16)."""
    args_blob = json.dumps(
        {
            "unit": unit.id,
            "base_path": env.base_path,
            "viewports": [list(v) for v in unit.viewports],
            "neg": sorted(neg),
        },
        sort_keys=True,
    )
    return {
        "dist": env.dist,
        "notebook": env.notebook,
        "harness": env.harness,
        "runner": env.runner,
        "chrome": env.chrome,
        "args": _sha256_bytes(args_blob.encode()),
        "driver": env.driver,
    }


# -- Inspecting a unit's files against the CURRENT inputs (the skip rule) ---------


def _read_json_file(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None


def _rm(path: Path) -> None:
    try:
        Path(path).unlink()
    except FileNotFoundError:
        pass


def clear_unit_files(out_dir: Path, unit_id: str) -> None:
    """Delete a unit's stamp (first: never a stamp without its result), result and timeout marker."""
    paths = unit_paths(out_dir, unit_id)
    for key in ("stamp", "result", "timeout"):
        _rm(paths[key])


def inspect_unit(out_dir: Path, unit: HarnessUnit, current_inputs: dict[str, str]) -> dict[str, Any]:
    """Classify a unit's files against the current inputs (D16 skip rule, C8-3).

    * ``valid``: a stamp exists, its ``inputs`` equal ``current_inputs`` and its
      ``result_sha256`` equals the sha256 of the result on disk.
    * ``reusable`` (the skip rule): valid AND ``stamp.exit == 0`` AND every listed key present
      and holding.
    * ``mismatched``: the names of the inputs whose hash differs from the stamp's.
    """
    paths = unit_paths(out_dir, unit.id)
    try:
        result_bytes: bytes | None = paths["result"].read_bytes()
    except OSError:
        result_bytes = None
    result: Any = None
    if result_bytes is not None:
        try:
            result = json.loads(result_bytes)
        except ValueError:
            result = None
    stamp = _read_json_file(paths["stamp"])
    state: dict[str, Any] = {
        "unit": unit.id,
        "result": result if isinstance(result, dict) else None,
        "stamp": stamp if isinstance(stamp, dict) else None,
        "result_path": str(paths["result"]),
        "has_timeout_marker": paths["timeout"].exists(),
        "valid": False,
        "reusable": False,
        "mismatched": [],
        "missing_keys": [],
        "failing_keys": [],
        "reasons": [],
    }
    if state["stamp"] is None:
        state["reasons"].append("no stamp")
        return state
    recorded = state["stamp"].get("inputs") or {}
    state["mismatched"] = sorted(
        n for n in set(recorded) | set(current_inputs) if recorded.get(n) != current_inputs.get(n)
    )
    if state["mismatched"]:
        state["reasons"].append("stamp inputs differ from the current inputs")
        return state
    if result_bytes is None or state["result"] is None:
        state["reasons"].append("no readable result")
        return state
    if state["stamp"].get("result_sha256") != _sha256_bytes(result_bytes):
        state["reasons"].append("result_sha256 does not match the result on disk")
        return state
    state["valid"] = True
    missing, failing = evaluate_unit_result(unit, state["result"])
    state["missing_keys"], state["failing_keys"] = missing, failing
    if state["stamp"].get("exit") != 0:
        state["reasons"].append(f"stamp.exit == {state['stamp'].get('exit')!r}")
    if missing:
        state["reasons"].append(f"listed keys missing: {missing}")
    if failing:
        state["reasons"].append(f"listed keys failing: {failing}")
    state["reusable"] = not state["reasons"]
    return state


# -- The driver and the aggregate --------------------------------------------------


def run_units_driver(
    *,
    table: Any,
    out_dir: Path,
    inputs_for: Any,
    argv_for: Any,
    runner: Any,
    fresh: bool = False,
    aggregate_only: bool = False,
    cwd: Any = None,
    check: str = DISPLAY_CHECK,
    driver_extra_s: float = DRIVER_EXTRA_S,
    meta: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    """Run (or, with ``aggregate_only``, only judge) every unit of ``table`` in table order.

    A unit is skipped only if its stamp meets the skip rule (``inspect_unit``); ``fresh``
    ignores every stamp. Each recomputed unit is ONE ``runner.run_unit`` call with timeout =
    its budget + ``driver_extra_s`` (there is no whole-run timeout); the driver clears the
    unit's files first and never kills anything itself. A ``run_unit`` timeout over a VALID
    stamp defers to the stamp (logged with ``logging.warning``). ``aggregate_only`` starts no
    unit, and NEVER deletes: a missing, timed-out or stale unit counts as failed and stays on
    disk. Returns ``(aggregate, exit_code)``; the exit is 0 only if every listed key of every
    unit holds. The pass rule is the same for a reused and a recomputed unit.
    """
    ur = unit_runner_module()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scenarios: dict[str, Any] = {}
    reused: list[dict[str, Any]] = []
    recomputed: list[str] = []
    timed_out: list[str] = []
    missing: list[str] = []
    stale: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    judged: dict[str, dict[str, Any]] = {}

    for unit in table:
        inputs = inputs_for(unit)
        state = inspect_unit(out_dir, unit, inputs)
        if state["reusable"] and not fresh:
            reused.append(
                {
                    "id": unit.id,
                    "source": state["result_path"],
                    "inputs": state["stamp"]["inputs"],
                    "result_sha256": state["stamp"]["result_sha256"],
                }
            )
            judged[unit.id] = state
            continue
        if not aggregate_only:
            clear_unit_files(out_dir, unit.id)
            argv = list(argv_for(unit))
            LOG.info("starting unit %s (timeout %.0f s)", unit.id, unit.budget_s + driver_extra_s)
            outcome = runner.run_unit(argv, unit.budget_s + driver_extra_s, cwd=cwd)
            state = inspect_unit(out_dir, unit, inputs)
            if state["valid"]:
                if outcome.timed_out:
                    LOG.warning(
                        "unit %s: run_unit timed out over a VALID stamp; the stamp governs", unit.id
                    )
                recomputed.append(unit.id)
                judged[unit.id] = state
                continue
            hung = outcome.timed_out or state["has_timeout_marker"] or outcome.exit == 124
            (timed_out if hung else missing).append(unit.id)
            LOG.error("unit %s is INCOMPLETE (exit %s): %s", unit.id, outcome.exit, state["reasons"])
            continue
        # --aggregate-only: classify, never touch the files
        if state["stamp"] is not None and not state["valid"]:
            stale.append(
                {"id": unit.id, "mismatched": state["mismatched"], "reasons": state["reasons"]}
            )
        elif state["stamp"] is not None:
            judged[unit.id] = state  # a valid stamp whose unit failed: judged from its result
        elif state["has_timeout_marker"]:
            timed_out.append(unit.id)
        else:
            missing.append(unit.id)

    for unit in table:
        st = judged.get(unit.id)
        scenarios[unit.id] = st["result"] if st is not None else None
        if st is not None and not st["reusable"]:
            failed.append(
                {
                    "id": unit.id,
                    "exit": st["stamp"].get("exit"),
                    "missing_keys": st["missing_keys"],
                    "failing_keys": st["failing_keys"],
                    "reasons": st["reasons"],
                }
            )
    passed = all(u.id in judged and judged[u.id]["reusable"] for u in table)
    aggregate: dict[str, Any] = {
        "check": check,
        "mode": "aggregate-only" if aggregate_only else ("fresh" if fresh else "driver"),
        "passed": passed,
        "scenarios": scenarios,
        "reused": reused,
        "recomputed": recomputed,
        "timed_out": timed_out,
        "missing": missing,
        "stale": stale,
        "failed": failed,
        "out_dir": str(out_dir),
    }
    if "D1-dark" in scenarios:  # keys must not collide with D1's (AC-7)
        aggregate["d1_dark"] = scenarios["D1-dark"]
    aggregate.update(meta or {})
    ur.write_atomic(
        out_dir / "result.json", json.dumps(aggregate, indent=1, sort_keys=True, default=str).encode()
    )
    print(json.dumps(aggregate, sort_keys=True, default=str))
    return aggregate, (0 if passed else 1)


# -- run_scenario: ONE unit in ONE process ------------------------------------------


def _tail(text: str, limit: int = 4096) -> str:
    return text.encode("utf-8", "replace")[-limit:].decode("utf-8", "replace")


def _flush_all() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (OSError, ValueError):
            pass
    for handler in logging.getLogger().handlers:
        try:
            handler.flush()
        except Exception:  # pragma: no cover - a broken handler must not stop the unit
            pass


def _sleep_forever_until_killed() -> None:  # pragma: no cover - the watchdog exits the process
    while True:
        time.sleep(1)


def run_scenario(
    unit_id: str,
    *,
    out_dir: Path,
    env_fn: Any,
    session_factory: Any,
    scenario_fn: Any,
    table: Any = None,
    neg: Any = (),
    ensure_token_fn: Any = None,
    watchdog_factory: Any = None,
    kill_tree_fn: Any = None,
    exit_fn: Any = None,
    budget_s: float | None = None,
) -> int:
    """Run exactly one unit in this process, in the D16 order; ends in ``exit_fn(stamp.exit)``.

    1. ``ensure_token`` (may re-exec; a no-op under the driver);
    2. arm a ``Watchdog`` at the unit's table budget, the FIRST act after that: on expiry it
       deletes the result if present, writes ``result.<id>.timeout.json``, prints one JSON
       line and exits 124 with no stamp;
    3. clear this unit's own stamp, result and timeout marker (stamp first);
    4. hash the inputs (``env_fn``), open the session, run the scenario. A scenario that
       raises is an ``error`` finding: the unit still writes its result and stamp (complete,
       exit 1, never reused);
    5. write the result through ``Watchdog.write_result``;
    6. bounded teardown: ``session.close()`` (browser and Playwright; a failure is logged),
       ``kill_tree(os.getpid(), token)`` over residual descendants, flush;
    7. commit the stamp through ``Watchdog.commit``, then ONLY ``exit_fn(stamp.exit)``
       (``os._exit`` in production: no ``atexit``, no threads, no interpreter shutdown).

    ``budget_s`` overrides the table budget for tests (never a CLI flag: budgets are
    pre-registered). The seams (``ensure_token_fn``, ``watchdog_factory``, ``kill_tree_fn``,
    ``exit_fn``) default to the production ``unit_runner`` behaviour.
    """
    ur = unit_runner_module()
    unit = {u.id: u for u in (table or UNIT_TABLE)}[unit_id]
    budget = float(unit.budget_s if budget_s is None else budget_s)
    token = (ensure_token_fn or ur.ensure_token)()
    exit_fn = exit_fn or os._exit
    kill_tree_fn = kill_tree_fn or ur.kill_tree
    out_dir = Path(out_dir)
    paths = unit_paths(out_dir, unit.id)
    started = time.time()

    def on_expire() -> None:
        _rm(paths["result"])
        marker = {"unit": unit.id, "budget_s": budget, "started": started, "expired": time.time()}
        try:
            ur.write_atomic(paths["timeout"], json.dumps(marker).encode())
        except OSError:
            pass
        ur.emit_line(json.dumps({"unit": unit.id, "status": "timeout", "budget_s": budget}))

    make_watchdog = watchdog_factory or (lambda b, cb: ur.Watchdog(b, cb, token=token))
    watchdog = make_watchdog(budget, on_expire)  # the first act after ensure_token

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        clear_unit_files(out_dir, unit.id)
        env = env_fn()
        inputs = unit_inputs(unit, env, neg)
    except Exception:
        LOG.exception("unit %s cannot build its inputs; no result, no stamp", unit.id)
        watchdog.disarm()
        return exit_fn(2)

    session: Any = None
    error: dict[str, Any] | None = None
    fields: dict[str, Any] = {}
    try:
        session = session_factory(unit, env)
        fields = dict(scenario_fn(session, unit, env) or {})
    except Exception as exc:  # a raised scenario is an `error` finding; the unit still completes
        LOG.exception("scenario %s raised", unit.id)
        error = {
            "type": type(exc).__name__,
            "message": str(exc)[:2000],
            "traceback_tail": _tail(traceback.format_exc()),
        }

    result: dict[str, Any] = dict(fields)
    result.update(
        {
            "unit": unit.id,
            "check": unit.check,
            "pageerrors": list(getattr(session, "pageerrors", None) or []),
            "chrome_path": env.chrome_path,
            "chrome_version": env.chrome_version,
            "error": error,
            "budget_s": budget,
            "started": started,
            "finished": time.time(),
        }
    )
    missing, failing = evaluate_unit_result(unit, result)
    result["missing_keys"], result["failing_keys"] = missing, failing
    data = json.dumps(result, indent=1, sort_keys=True, default=str).encode()
    if not watchdog.write_result(lambda: ur.write_atomic(paths["result"], data)):
        _sleep_forever_until_killed()
    ur.emit_line(
        json.dumps(
            {"unit": unit.id, "status": "done", "missing_keys": missing, "failing_keys": failing,
             "error": error["type"] if error else None}
        )
    )

    # Bounded teardown (D16, C9-1), still inside the watchdog-bounded region.
    if session is not None:
        try:
            session.close()
        except Exception:
            LOG.exception("session close raised")
    try:
        survivors = kill_tree_fn(os.getpid(), token)
        if survivors:
            LOG.error("descendants survived kill_tree: %s", survivors)
    except Exception:
        LOG.exception("kill_tree raised during teardown")
    _flush_all()

    stamp_exit = 0 if (error is None and not missing and not failing) else 1
    stamp = {
        "unit": unit.id,
        "inputs": inputs,
        "result_sha256": _sha256_bytes(data),
        "started": started,
        "finished": time.time(),
        "exit": stamp_exit,
        "budget_s": budget,
    }
    stamp_bytes = json.dumps(stamp, indent=1, sort_keys=True).encode()
    if not watchdog.commit(lambda: ur.write_atomic(paths["stamp"], stamp_bytes)):
        _sleep_forever_until_killed()
    return exit_fn(stamp_exit)  # nothing runs after the stamp but the exit


# -- D1 / D1-dark: the browser scenario body ----------------------------------------
#
# What is read, and how (AC-7). Every value comes from the DOM's computed styles or the notebook
# MODEL through page.evaluate, never from printed console text:
#   rail_state_*          the cell node's `data-praxis-cell-state` attribute (written by
#                         shell/display/chrome.js from the model), read at each stage together
#                         with the model's ground truth (execution count/state, output types)
#   rail_colors_match     getComputedStyle(cell, '::before'): backgroundColor per state, and for
#                         stale the dashed backgroundImage (a repeating gradient of moonstone ink
#                         over a transparent backgroundColor); not-run is compared with the
#                         computed `--jp-border-color1` (resolved through a probe element)
#   prompts_take_no_space getBoundingClientRect().width of `.jp-InputPrompt` and `.jp-OutputPrompt`
#                         of the executed cell, with a live-layout guard (cell and editor widths)
#   light_ground          getComputedStyle(<notebook>.content.node).backgroundColor (`.jp-Notebook`)
#   light_sheet           getComputedStyle(cell 0).backgroundColor (`.jp-CodeCell`)
#   exec_count_on_rail    getComputedStyle(cell, '::after').content (quotes stripped) against
#                         the model's execution count, for every cell
#   pageerrors            the session's `pageerror` listener

RAIL_RGB = {"ran": "rgb(47, 104, 130)", "running": "rgb(237, 122, 155)", "error": "rgb(179, 64, 42)"}
STALE_RAIL_NEEDLES = ("repeating-linear-gradient", RAIL_RGB["ran"])
CSS_TRANSPARENT = frozenset({"rgba(0, 0, 0, 0)", "transparent"})
D1_STAGES = (
    ("never_run", "not-run"),
    ("after_run", "ran"),
    ("while_sleep", "running"),
    ("after_raise", "error"),
    ("after_edit", "stale"),
)
THEME_NAMES = {True: "JupyterLab Light", False: "JupyterLab Dark"}
#: A cell whose node is narrower than this has no live layout (content-visibility, detached).
MIN_LIVE_CELL_WIDTH_PX = 100.0


def strip_css_content(raw: Any) -> str | None:
    """A computed ``content`` value as text: ``'"3"'`` -> ``"3"``, ``'""'`` -> ``""``;
    ``none`` / ``normal`` / missing -> ``None`` (no pseudo-element is generated)."""
    if raw is None:
        return None
    text = str(raw).strip()
    if text in ("none", "normal"):
        return None
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


def rail_color_ok(state: str, snap: dict[str, Any] | None, grey: str | None) -> bool:
    """Is this snapshot's computed rail the section 3.1 colour for ``state``?"""
    snap = snap or {}
    bg = snap.get("before_bg")
    if state == "not-run":  # rail grey: the computed --jp-border-color1
        return bool(grey) and bg == grey
    if state == "stale":  # dashed: a repeating gradient of moonstone ink over transparent
        image = snap.get("before_bg_image") or ""
        return bg in CSS_TRANSPARENT and all(needle in image for needle in STALE_RAIL_NEEDLES)
    return bg == RAIL_RGB.get(state)


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def prompts_ok(prompts: dict[str, Any] | None) -> bool:
    """Both prompts found and each <= 1 px wide, with a live layout so a hidden cell proves nothing."""
    p = prompts or {}
    widths = (p.get("input_w"), p.get("output_w"))
    if not all(_num(w) for w in widths) or not all(w <= 1 for w in widths):
        return False
    return (
        _num(p.get("cell_w"))
        and p["cell_w"] >= MIN_LIVE_CELL_WIDTH_PX
        and _num(p.get("editor_w"))
        and p["editor_w"] > 0
    )


def exec_counts_on_rail(final: list[dict[str, Any]] | None) -> bool:
    """Each cell's ``::after`` text equals its model execution count (none for a never-run
    cell), and at least one cell has a count, so a page with no counts at all cannot pass."""
    if not final:
        return False
    counted = 0
    for snap in final:
        count = (snap.get("model") or {}).get("execution_count")
        text = strip_css_content(snap.get("after_content"))
        if count is None:
            if text not in (None, ""):
                return False
        else:
            counted += 1
            if text != str(count):
                return False
    return counted >= 1


def derive_chrome_keys(raw: dict[str, Any], *, light: bool) -> dict[str, Any]:
    """The D1 (``light``) or D1-dark result keys from the raw snapshots (pure; tested on synthetic
    ground truth with a positive control and negative controls)."""
    keys: dict[str, Any] = {}
    for (stage, _), (name, _) in zip(D1_STAGES, _RAIL_STATE_KEYS):
        keys[name] = (raw.get(stage) or {}).get("state")
    theme_ok = raw.get("theme_name") == THEME_NAMES[light]
    grey = raw.get("grey_token")
    colors = theme_ok and all(
        rail_color_ok(state, raw.get(stage), grey) for stage, state in D1_STAGES
    )
    keys["prompts_take_no_space"] = prompts_ok(raw.get("prompts"))
    keys["exec_count_on_rail"] = exec_counts_on_rail(raw.get("final"))
    if light:
        keys["rail_colors_match"] = colors
        keys["light_ground"] = raw.get("ground")
        keys["light_sheet"] = raw.get("sheet")
    else:
        keys["rail_colors_match_dark"] = colors
    return keys


#: Harness-only page helpers (installed with page.evaluate; nothing here ships in dist). They only
#: read: computed styles, the notebook model, and the DOM attributes the product writes.
DISPLAY_CHECK_JS = r"""
(() => {
  const app = () => window.jupyterapp;
  const panel = () => app().shell.currentWidget;
  const widgets = () => panel().content.widgets;
  const model = (i) => panel().content.model.cells.get(i);
  const outTypes = (m) => {
    const o = m.outputs, out = [];
    if (!o) return out;
    const n = o.length ?? o.size ?? 0;
    for (let j = 0; j < n; j++) {
      const x = o.get ? o.get(j) : o[j];
      const d = x && x.toJSON ? x.toJSON() : x;
      out.push(d && d.output_type ? d.output_type : (x && x.type) || null);
    }
    return out;
  };
  const snapshot = (i) => {
    const node = widgets()[i].node, m = model(i);
    const before = getComputedStyle(node, '::before'), after = getComputedStyle(node, '::after');
    return {
      index: i, in_document: document.contains(node),
      state: node.getAttribute('data-praxis-cell-state'),
      exec_attr: node.getAttribute('data-praxis-exec'),
      before_bg: before.backgroundColor, before_bg_image: before.backgroundImage,
      before_width: before.width, after_content: after.content,
      sheet_bg: getComputedStyle(node).backgroundColor,
      model: {
        execution_count: m.executionCount ?? null, execution_state: m.executionState ?? null,
        output_types: outTypes(m), source: m.sharedModel.getSource(),
      },
    };
  };
  window.__praxisDisplayCheck = {
    themeName: () => document.body.getAttribute('data-jp-theme-name'),
    cellsReady: (n) => { try { return panel().content.model.cells.length >= n && widgets().length >= n; } catch (e) { return false; } },
    kernelStatus: () => { try { return panel().sessionContext.session.kernel.status; } catch (e) { return null; } },
    markCells: () => { widgets().forEach((w, i) => w.node.setAttribute('data-dcheck-index', String(i))); return widgets().length; },
    runCell: (i) => {
      panel().content.activeCellIndex = i;
      try {
        const p = app().commands.execute('notebook:run-cell');
        if (p && p.catch) p.catch((e) => { window.__praxisDisplayCheckError = String(e); });
        return {dispatched: true};
      } catch (e) { return {dispatched: false, error: String(e)}; }
    },
    modelDone: (i) => { const m = model(i); return (m.executionCount ?? null) !== null && m.executionState !== 'running'; },
    snapshot,
    pollState: async (a) => {
      const t0 = performance.now();
      let last = snapshot(a.i);
      while (performance.now() - t0 < a.ms) {
        last = snapshot(a.i);
        if (last.state === a.want) return last;
        await new Promise((r) => setTimeout(r, 25));
      }
      return last;
    },
    greyToken: () => {
      const el = document.createElement('div');
      el.style.backgroundColor = 'var(--jp-border-color1)';
      document.body.appendChild(el);
      const c = getComputedStyle(el).backgroundColor;
      el.remove();
      return c;
    },
    ground: () => getComputedStyle(panel().content.node).backgroundColor,
    prompts: (i) => {
      const node = widgets()[i].node;
      node.scrollIntoView({block: 'nearest'});
      const w = (e) => (e ? e.getBoundingClientRect().width : null);
      return {
        input_w: w(node.querySelector('.jp-InputPrompt')),
        output_w: w(node.querySelector('.jp-OutputPrompt')),
        cell_w: node.getBoundingClientRect().width,
        editor_w: w(node.querySelector('.jp-InputArea-editor')),
      };
    },
    displayStatus: () => (window.__praxisDisplay ? window.__praxisDisplay.status : null),
    firstSaveDialogOpen: () => { const d = document.querySelector('dialog#praxis-persistence-first-save'); return !!(d && d.open); },
  };
})()
"""

_DC_SAVE_JS = """async (a) => {
    try {
        await window.jupyterapp.serviceManager.contents.save(a.path, {
            type: "notebook", format: "json", content: a.content});
        return {ok: true};
    } catch (e) { return {ok: false, error: String(e)}; }
}"""

_DC_THEME_JS = """async (theme) => {
    try {
        await window.jupyterapp.commands.execute('apputils:change-theme', {theme: theme});
        return {ok: true};
    } catch (e) { return {ok: false, error: String(e)}; }
}"""

# Ready to change theme: all three must hold. `window.jupyterapp` appears before JupyterLab's
# plugins have activated, so the command may not be registered yet; `restored` (JupyterFrontEnd's
# promise, resolved after layout restoration) is read through a flag armed on the first poll,
# because the predicate is polled synchronously; and the splash plugin removes
# `#jupyterlab-splash` 200 ms after the first theme load, so a theme change made before that
# overlaps the initial load and double-removes the splash.
THEME_READY_JS = """() => {
    const app = window.jupyterapp;
    if (!app || !app.commands || !app.restored) return false;
    if (window.__praxisRestored === undefined) {
        window.__praxisRestored = false;
        app.restored.then(() => { window.__praxisRestored = true; });
    }
    return app.commands.hasCommand('apputils:change-theme')
        && window.__praxisRestored === true
        && !document.getElementById('jupyterlab-splash');
}"""


def wait_for_theme_ready(page: Any, timeout_ms: int = DISPLAY_NAV_TIMEOUT_MS) -> None:
    """Block until ``apputils:change-theme`` can be executed safely (see ``THEME_READY_JS``)."""
    page.wait_for_function(THEME_READY_JS, timeout=timeout_ms)


class DisplayCheckError(RuntimeError):
    """A display-check scenario could not reach the state it needs to measure."""


def display_context_init_scripts(neg: Any = ()) -> list[str]:
    """The init scripts every display-check context carries: the persistence ack (D16) and the harness-only
    monitor that watches the first-save modal for the whole scenario (``persistence_gate_never_open``)."""
    return [PERSISTENCE_ACK_INIT_SCRIPT, PERSISTENCE_GATE_MONITOR_INIT_SCRIPT]


DISPLAY_PAGEERROR_STACK_CHARS = 600


def format_pageerror(exc: Any) -> str:
    """One ``pageerrors`` entry: the message, then the JavaScript stack cut to 600 characters.

    Still a single string, so the key stays a list of strings and is empty exactly when there
    were no page errors. ``stack`` is absent on a plain exception and None when the page gave none.
    """
    message = str(exc)
    stack = getattr(exc, "stack", None)
    if not stack:
        return message
    return f"{message}\n{str(stack)[:DISPLAY_PAGEERROR_STACK_CHARS]}"


class DisplaySession:
    """A served dist + Playwright + one fresh Chromium context and page.

    ``close()`` is the teardown's step 2: browser closed, Playwright stopped, the served dir
    shut down; every failure is logged with ``logging.error`` and never changes the keys.
    """

    def __init__(self, unit: HarnessUnit, args: argparse.Namespace, env: HashEnv) -> None:
        from playwright.sync_api import sync_playwright

        self.pageerrors: list[str] = []
        self.prefix = _normalize_base_path(args.base_path)
        self._neg = tuple(getattr(args, "neg", ()) or ())
        self._stack = contextlib.ExitStack()
        self._pw: Any = None
        self._browser: Any = None
        try:
            served = self._stack.enter_context(
                ServedDir(Path(args.serve_dir).resolve(), args.base_path, coi=False)
            )
            self.origin = f"http://127.0.0.1:{served.port}"
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                executable_path=env.chrome_path,
                headless=True,
                args=chromium_launch_args(offline=False),
            )
            width, height = unit.viewports[0]
            context = self._browser.new_context(viewport={"width": width, "height": height})
            for script in display_context_init_scripts(neg=self._neg):
                context.add_init_script(script)
            self.page = context.new_page()
            self.page.on("pageerror", lambda exc: self.pageerrors.append(format_pageerror(exc)))
        except BaseException:
            self.close()
            raise

    @property
    def lab_url(self) -> str:
        return f"{self.origin}{self.prefix}lab/index.html"

    def open_page(self, unit: HarnessUnit, *, block: tuple[str, ...] = ()) -> tuple[Any, list[str]]:
        """A second fresh context and page in the same browser (D4's twin with ``praxis-theme.css`` blocked).
        ``block`` are URL globs aborted at the context (a page request; the kernel worker is not involved).
        Returns ``(page, blocked)``: ``blocked`` collects the URL of every aborted request."""
        width, height = unit.viewports[0]
        context = self._browser.new_context(viewport={"width": width, "height": height})
        for script in display_context_init_scripts(neg=self._neg):
            context.add_init_script(script)
        blocked: list[str] = []
        for glob in block:
            context.route(glob, make_block_handler(blocked))
        page = context.new_page()
        page.on("pageerror", lambda exc: self.pageerrors.append(str(exc)))
        return page, blocked

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


def _dc(page: Any, expr: str, arg: Any = None) -> Any:
    """``page.evaluate`` of ``window.__praxisDisplayCheck.<expr>`` (an expression body over ``a``)."""
    return page.evaluate(f"async (a) => window.__praxisDisplayCheck.{expr}", arg)


def run_chrome_scenario(session: Any, unit: HarnessUnit, env: Any, *, notebook: dict | None = None) -> dict[str, Any]:
    """D1 (Light via ``apputils:change-theme``) or D1-dark (default Dark, no theme change).

    Cells run ONE AT A TIME through ``notebook:run-cell``; Run All is never used. Stage by
    stage: the never-run cell is snapshotted untouched; cell 1 runs (ran); cell 2 sleeps 3 s and
    is polled to ``running``; cell 3 raises (error); cell 4 runs and is then typed into with a
    real keyboard (stale). Returns the derived keys plus informational evidence.
    """
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    page = session.page
    light = unit.id == "D1"
    fixture = notebook if notebook is not None else json.loads(DISPLAY_NOTEBOOK_PATH.read_text())
    n_cells = len(fixture["cells"])

    page.goto(session.lab_url, wait_until="load", timeout=DISPLAY_NAV_TIMEOUT_MS)
    page.wait_for_function(
        "() => !!window.jupyterapp && !!window.jupyterapp.shell", timeout=DISPLAY_NAV_TIMEOUT_MS
    )
    page.evaluate(DISPLAY_CHECK_JS)
    if light:
        wait_for_theme_ready(page)
        changed = page.evaluate(_DC_THEME_JS, THEME_NAMES[True])
        if not changed.get("ok"):
            raise DisplayCheckError(f"apputils:change-theme failed: {changed.get('error')!r}")
    try:
        page.wait_for_function(
            "(want) => window.__praxisDisplayCheck.themeName() === want",
            arg=THEME_NAMES[light], timeout=30_000,
        )
    except PlaywrightTimeoutError:
        LOG.warning("theme %r never applied; the keys will say so", THEME_NAMES[light])

    saved = page.evaluate(_DC_SAVE_JS, {"path": DISPLAY_NOTEBOOK_NAME, "content": fixture})
    if not saved.get("ok"):
        raise DisplayCheckError(f"could not seed {DISPLAY_NOTEBOOK_NAME}: {saved.get('error')!r}")
    _open_existing_notebook(page, DISPLAY_NOTEBOOK_NAME, timeout_ms=DISPLAY_NAV_TIMEOUT_MS)
    page.wait_for_function(
        "(n) => window.__praxisDisplayCheck.cellsReady(n)", arg=n_cells, timeout=DISPLAY_NAV_TIMEOUT_MS
    )
    _dc(page, "markCells()")
    page.wait_for_function(
        "() => window.__praxisDisplayCheck.kernelStatus() === 'idle'", timeout=DISPLAY_KERNEL_TIMEOUT_MS
    )

    def run_and_wait(index: int) -> None:
        ran = _dc(page, "runCell(a)", index)
        if not ran.get("dispatched"):
            raise DisplayCheckError(f"could not run cell {index}: {ran.get('error')!r}")
        page.wait_for_function(
            "(i) => window.__praxisDisplayCheck.modelDone(i)", arg=index, timeout=DISPLAY_STEP_TIMEOUT_MS
        )

    def settle(index: int, want: str) -> dict[str, Any]:
        return _dc(page, "pollState(a)", {"i": index, "want": want, "ms": 10_000})

    raw: dict[str, Any] = {"never_run": _dc(page, "snapshot(a)", 0)}
    run_and_wait(1)
    raw["after_run"] = settle(1, "ran")
    raw["prompts"] = _dc(page, "prompts(a)", 1)
    ran = _dc(page, "runCell(a)", 2)  # dispatched, not awaited: polled while it sleeps
    if not ran.get("dispatched"):
        raise DisplayCheckError(f"could not run the sleep cell: {ran.get('error')!r}")
    raw["while_sleep"] = _dc(page, "pollState(a)", {"i": 2, "want": "running", "ms": 30_000})
    page.wait_for_function(
        "(i) => window.__praxisDisplayCheck.modelDone(i)", arg=2, timeout=DISPLAY_STEP_TIMEOUT_MS
    )
    run_and_wait(3)
    raw["after_raise"] = settle(3, "error")
    run_and_wait(4)
    settle(4, "ran")
    page.locator('[data-dcheck-index="4"] .cm-content').click()
    page.keyboard.press("Control+End")
    page.keyboard.type(" # edited")
    raw["after_edit"] = settle(4, "stale")

    raw["final"] = [_dc(page, "snapshot(a)", i) for i in range(n_cells)]
    raw["grey_token"] = _dc(page, "greyToken()")
    raw["ground"] = _dc(page, "ground()")
    raw["sheet"] = raw["never_run"].get("sheet_bg")
    raw["theme_name"] = _dc(page, "themeName()")

    keys = derive_chrome_keys(raw, light=light)
    keys.update(
        {
            "theme_name": raw["theme_name"],
            "grey_token": raw["grey_token"],
            "display_status": _dc(page, "displayStatus()"),
            "persistence_first_save_dialog_open": _dc(page, "firstSaveDialogOpen()"),
            "rail_width_px": {
                stage: (raw.get(stage) or {}).get("before_width") for stage, _ in D1_STAGES
            },
            "evidence": raw,
        }
    )
    return keys


# -- D2 / D3 / D4: the B10 scenario bodies (AC-21 .. AC-26) ------------------------------------
#
# Task B10 (epic 260929_notebook-display-design, backlog #5646). D2 executes the fixture's drawing,
# error, staleness and keyboard cells in one kernel (one kernel restart, one Run All in its own
# notebook); D3 executes its own drawing cells, saves, reloads and reopens them; D4 measures the
# outputs under "JupyterLab Dark High Contrast" in one context and reads the theme's own token in a
# second context with praxis-theme.css blocked.
#
# HOW IT IS BUILT SO THAT MOST OF IT IS TESTABLE WITHOUT A BROWSER. Each scenario is a sequence of
# calls on a ``driver`` (``DisplayDriver`` wraps one Playwright page; the tests substitute a
# scripted fake) and a set of PURE key derivations (``derive_*``) over what the driver read. What is
# read, and how, in the browser:
#
#   drawn outputs, stamps  the notebook MODEL: ``cell.model.outputs.get(j).toJSON()`` (never printed
#                          text); the stamp through the D2 expression ``stampOf`` verbatim
#   html_bytes             UTF-8 length of the model's ``text/html`` (TextEncoder)
#   svg_in_dom, notices    the output's DOM node: the ``.jp-OutputArea-output`` that holds an element
#                          whose ``dataset.praxisRes`` equals the resource name (compared as a
#                          string, never through a selector built from the name); the notice text
#                          occurrences in that node's ``textContent``
#   error panel heading    ``.praxis-error__title`` in the error cell's DOM; the error output from the model
#   rail state             ``data-praxis-cell-state`` on the cell node (chrome.js)
#   keyboard keys          ``page.keyboard`` (Tab, ArrowRight, Escape); ``document.activeElement``, the
#                          shell's ``[data-praxis-live]`` region and ``.praxis-focus-ring``
#   persisted marks        ``contents.get`` of the saved notebook (the FILE, not the DOM)
#   reopened branch        the output model's ``trusted``, the chosen ``data-mime-type`` and what
#                          survived in the DOM (D1's S2 branches)
#   colours                ``getComputedStyle`` (fill, color) and ``var(--jp-...)`` resolved through a
#                          throwaway probe element
#   first-save modal       a context init script polls ``dialog#praxis-persistence-first-save`` for the
#                          whole scenario (and across the D3 reload through sessionStorage)
#
# What the tests prove and what only a real browser run (B10b) can: see the B10 report.

EXECUTED_REOPEN_BRANCH = "S2-T"  # AC-2, recorded: S2 = s2_b_exec_t, run bf83a4e6 (executed-saved-reopened is trusted)
RUNALL_NOTEBOOK_NAME = "display_check_runall.ipynb"
RUNALL_CELL_IDS = ("assemble", "transfers", "pickup", "e1", "marker")
#: logical name -> the fixture's cell id (``display_check.ipynb``); the D1 cells (indices 0-4) are not listed
FIXTURE_CELLS: dict[str, str] = {
    "boot": "boot", "assemble": "assemble", "transfers": "transfers", "pickup": "pickup",
    "draw_source": "draw-source", "draw_assay": "draw-assay", "draw_tips": "draw-tips", "draw_deck": "draw-deck",
    "aspirate": "aspirate", "e1": "e1", "e2": "e2", "e4": "e4", "e6": "e6",
    "value_error": "value-error", "redraw": "redraw", "marker": "marker",
}
#: the drawing cells and what each draws: cell id -> (stamp kind, resource name; ``None``: any non-empty name)
DRAW_CELLS: dict[str, tuple[str, str | None, str]] = {
    "draw-source": ("plate", "source", "source"),
    "draw-assay": ("plate", "assay", "assay"),
    "draw-tips": ("tiprack", "tips_300", "tips_300"),
    "draw-deck": ("deck", None, "deck"),
}
#: AC-22 = AC-16's headings; the fixture state makes E2 name assay A2 alone
ERROR_HEADINGS = {
    "e1": "Not enough liquid in assay A1:H1.",
    "e2": "Not enough room in assay A2.",
    "e4": "Channel 0 already holds a tip.",
    "e6": "Channel 0 has no tip.",
}
#: AC-9's string for the assay after the fixture's three column transfers (en dash U+2013, micro sign U+00B5)
ASSAY_TEXT_PLAIN = "24 of 96 wells hold liquid, 50–150 µL. 2,400 µL in the plate."
#: The readout after ArrowRight from A1 (interact.js ``readoutText``). AC-25's text says "assay A2: 50 µL", but the
#: fixture this same unit asserts against AC-9 (24 wells, 50-150 µL, 2,400 µL) puts 100 µL in column 2, so the key is
#: derived from the fixture, not from the AC-25 literal (recorded as a spec ambiguity in the B10 report).
ARROW_RIGHT_LIVE_TEXT = "assay A2: 100 µL"
CHANGED_NOTICE = "Changed since, see deck panel."
EARLIER_NOTICE = "Drawn in an earlier session."
MOONSTONE_RGB = "rgb(115, 169, 194)"  # #73A9C2, the liquid fill (a brand constant, D3)
HC_THEME_NAME = "JupyterLab Dark High Contrast"
THEME_CSS_GLOB = "**/assets/theme/praxis-theme.css*"
#: Session-context statuses that mean a kernel (re)started (the vocabulary shell/display/stale.js listens for).
RESTART_STATUSES = ("starting", "restarting", "autorestarting")
PERSISTENCE_GATE_SEEN_KEY = "__praxis_dcheck_first_save_seen"

#: Harness-only, added to EVERY display-check context: the first-save modal must never open (D16). It only
#: polls; ``window.__praxisFirstSaveMonitor`` proves it is alive, and a sighting survives a reload in
#: sessionStorage. It writes no product key.
PERSISTENCE_GATE_MONITOR_INIT_SCRIPT = (
    """(() => {
  try {
    const KEY = "__GATE_KEY__";
    window.__praxisFirstSaveMonitor = true;
    const check = () => {
      try {
        const d = document.querySelector("dialog#praxis-persistence-first-save");
        if (d && (d.open || d.hasAttribute("open"))) {
          window.__praxisFirstSaveSeen = true;
          try { sessionStorage.setItem(KEY, "1"); } catch (e) {}
        }
      } catch (e) {}
    };
    setInterval(check, 50);
  } catch (e) {}
})();"""
).replace("__GATE_KEY__", PERSISTENCE_GATE_SEEN_KEY)


# -- pure helpers ------------------------------------------------------------------------------


def hex_to_rgb(value: Any) -> str | None:
    """``#73A9C2`` -> ``rgb(115, 169, 194)`` (the form ``getComputedStyle`` returns); ``None`` for anything else."""
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        return None
    return "rgb({}, {}, {})".format(*(int(value[i : i + 2], 16) for i in (1, 3, 5)))


def poll_until(
    read: Any, ok: Any, *, timeout_s: float, interval_s: float = 0.25, clock: Any = time.monotonic, sleep: Any = time.sleep
) -> tuple[Any, bool]:
    """Read until ``ok(value)`` holds or ``timeout_s`` passes. Always reads at least once; returns the LAST
    reading with whether it held. Never sleeps past the deadline."""
    deadline = clock() + timeout_s
    while True:
        value = read()
        if ok(value):
            return value, True
        now = clock()
        if now >= deadline:
            return value, False
        sleep(min(interval_s, max(0.0, deadline - now)))


def restart_finished(statuses: Any) -> bool:
    """A kernel restart has happened and finished: a restart-ish status was seen and the last status is ``idle``
    (an ``idle`` before the restart began proves nothing)."""
    seq = list(statuses or [])
    return bool(seq) and any(s in RESTART_STATUSES for s in seq) and seq[-1] == "idle"


def make_block_handler(blocked: list[str]) -> Any:
    """A Playwright route handler that records the request URL and aborts it."""

    def handler(route: Any) -> None:
        blocked.append(route.request.url)
        route.abort()

    return handler


def cell_indices(notebook: dict[str, Any]) -> dict[str, int]:
    """Cell id -> index. Raises ``ValueError`` on a duplicated or missing id (the harness addresses cells by id)."""
    out: dict[str, int] = {}
    for i, cell in enumerate(notebook.get("cells", [])):
        cid = cell.get("id")
        if not isinstance(cid, str) or not cid:
            raise ValueError(f"cell {i} has no id")
        if cid in out:
            raise ValueError(f"duplicated cell id {cid!r}")
        out[cid] = i
    return out


def require_cells(notebook: dict[str, Any], *ids: str) -> dict[str, int]:
    """``cell_indices`` after checking that every id in ``ids`` exists (``KeyError`` naming the missing ones)."""
    idx = cell_indices(notebook)
    missing = [i for i in ids if i not in idx]
    if missing:
        raise KeyError(f"the fixture notebook lacks cells {missing}")
    return idx


def build_runall_notebook(notebook: dict[str, Any]) -> dict[str, Any]:
    """The "E1 then marker" pair for the one Run All scenario (AC-22 ``runall_stops``): the cells of
    ``RUNALL_CELL_IDS`` cloned from the fixture (so its hash covers them), never executed, no outputs."""
    idx = require_cells(notebook, *RUNALL_CELL_IDS)
    cells = []
    for cid in RUNALL_CELL_IDS:
        cell = json.loads(json.dumps(notebook["cells"][idx[cid]]))
        cell["execution_count"], cell["outputs"] = None, []
        cells.append(cell)
    pair = {k: json.loads(json.dumps(v)) for k, v in notebook.items() if k != "cells"}
    pair["cells"] = cells
    return pair


def _strings(value: Any) -> Any:
    """Every string in a JSON value; a list of strings (a multi-line notebook string) is joined first."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        if value and all(isinstance(x, str) for x in value):
            yield "".join(value)
        else:
            for x in value:
                yield from _strings(x)
    elif isinstance(value, dict):
        for x in value.values():
            yield from _strings(x)


def count_scripts_in_outputs(notebook: Any) -> int:
    """How many ``<script`` occurrences (case-insensitive) appear in the OUTPUTS of a saved notebook (AC-24
    ``no_script_in_bundles``). A script in a cell's source is not in a bundle."""
    if not isinstance(notebook, dict):
        return 0
    total = 0
    for cell in notebook.get("cells") or []:
        if not isinstance(cell, dict):
            continue
        for output in cell.get("outputs") or []:
            for text in _strings(output):
                total += text.lower().count("<script")
    return total


def saved_notebook_has_outputs(notebook: Any) -> bool:
    """A saved notebook that carries at least one ``text/html`` output: a file read that proves something."""
    if not isinstance(notebook, dict):
        return False
    for cell in notebook.get("cells") or []:
        for output in (cell.get("outputs") or []) if isinstance(cell, dict) else []:
            if isinstance(output, dict) and "text/html" in (output.get("data") or {}):
                return True
    return False


def _drawing(report: Any) -> dict[str, Any] | None:
    """The first output of a cell report that carries a stamp (the drawn resource)."""
    for output in (report or {}).get("outputs") or []:
        if isinstance(output, dict) and isinstance(output.get("stamp"), dict):
            return output
    return None


def _res(report: Any) -> dict[str, Any]:
    r = (report or {}).get("res")
    return r if isinstance(r, dict) else {}


def _notices(res: Any, field: str) -> int | None:
    """A notice count, or ``None`` when the output was not found (an unfound output proves nothing)."""
    if not isinstance(res, dict) or res.get("found") is not True:
        return None
    n = res.get(field)
    return n if isinstance(n, int) and not isinstance(n, bool) else None


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _stamp_ok(stamp: Any, kind: str, resource: str | None) -> bool:
    if not isinstance(stamp, dict) or stamp.get("v") != 1 or stamp.get("kind") != kind:
        return False
    if not _is_int(stamp.get("rev")):
        return False
    session = stamp.get("session")
    if not isinstance(session, str) or not session:
        return False
    name = stamp.get("resource")
    return name == resource if resource is not None else (isinstance(name, str) and bool(name))


# -- key derivations (pure; tested with a positive control and negative controls) ------------------


def derive_repr_keys(reports: dict[str, Any]) -> dict[str, Any]:
    """AC-21 from the four drawing cells' reports (keys ``draw_source`` ... ``draw_deck``)."""
    cells_ok = svg_ok = True
    sizes: list[int] = []
    plain_assay = None
    for key, (kind, resource, _res_name) in ((k.replace("-", "_"), v) for k, v in DRAW_CELLS.items()):
        report = reports.get(key)
        out = _drawing(report)
        if out is None:
            cells_ok = svg_ok = False
            sizes.append(None)  # type: ignore[arg-type]
            continue
        mimes = out.get("mimes") or []
        cells_ok = cells_ok and "text/html" in mimes and "text/plain" in mimes and _stamp_ok(out["stamp"], kind, resource)
        n = _notices(_res(report), "svg_count")
        svg_ok = svg_ok and n is not None and n >= 1
        html_bytes = out.get("html_bytes")
        sizes.append(html_bytes if _is_int(html_bytes) else None)  # type: ignore[arg-type]
        if key == "draw_assay":
            plain_assay = out.get("plain")
    return {
        "repr_cells_ok": bool(cells_ok),
        "svg_in_dom": bool(svg_ok),
        "html_bytes_max": max(sizes) if sizes and all(s is not None for s in sizes) else None,
        "text_plain_matches": plain_assay == ASSAY_TEXT_PLAIN,
    }


def _last_output_type(report: Any) -> str | None:
    outputs = (report or {}).get("outputs") or []
    return outputs[-1].get("output_type") if outputs and isinstance(outputs[-1], dict) else None


def derive_error_keys(errors: dict[str, Any], value_error: Any, runall: dict[str, Any]) -> dict[str, Any]:
    """AC-22: the four PLR error cells, the plain ``ValueError`` cell and the Run All pair."""
    panels = status = True
    for cid, heading in ERROR_HEADINGS.items():
        report = errors.get(cid) or {}
        titles = (report.get("error") or {}).get("titles") or []
        panels = panels and bool(titles) and titles[0] == heading
        status = status and _last_output_type(report) == "error" and report.get("state") == "error"
    plain = (
        _last_output_type(value_error) == "error"
        and ((value_error or {}).get("error") or {}).get("praxis_error_nodes") == 0
        and any(o.get("ename") == "ValueError" for o in (value_error or {}).get("outputs") or [])
    )
    ran = all((runall.get(c) or {}).get("execution_count") is not None for c in ("assemble", "transfers", "pickup", "e1"))
    stops = (
        ran
        and _last_output_type(runall.get("e1")) == "error"
        and (runall.get("marker") or {}).get("execution_count") is None
        and not (runall.get("marker") or {}).get("outputs")
    )
    return {
        "error_panels": bool(panels), "error_status": bool(status),
        "runall_stops": bool(stops), "other_errors_plain": bool(plain),
    }


def derive_stale_keys(raw: dict[str, Any]) -> dict[str, Any]:
    """AC-23 (the four staleness keys) from the notice counts read at each stage."""
    source, tips = raw.get("source"), raw.get("tips")
    changed = _notices(source, "changed_notices")
    marked = changed is not None and changed >= 1
    tips_changed = _notices(tips, "changed_notices")
    persisted = raw.get("persisted") or {}
    stored = (
        persisted.get("file_read_ok") is True and persisted.get("has_outputs") is True
        and persisted.get("mark_present_before_save") is True and persisted.get("contains_changed") is False
    )
    survives = (
        raw.get("rerender_ok") is True
        and _notices(raw.get("after_scroll"), "changed_notices") == 1
        and _notices(raw.get("after_rerender"), "changed_notices") == 1
    )
    return {
        "stale_marked": marked,
        "stale_not_persisted": bool(stored),
        "unchanged_not_marked": bool(marked and tips_changed == 0),
        "mark_survives_scroll": bool(survives),
    }


def derive_session_keys(raw: dict[str, Any]) -> dict[str, Any]:
    """AC-23 ``earlier_session_marked`` and its negative control ``rerun_not_marked``."""
    pre, rerun = raw.get("pre") or {}, raw.get("rerun") or {}
    a, b = pre.get("session"), rerun.get("session")
    new_session = isinstance(a, str) and bool(a) and isinstance(b, str) and bool(b) and a != b
    pre_marked = _notices(pre.get("res"), "earlier_notices")
    rerun_marked = _notices(rerun.get("res"), "earlier_notices")
    return {
        "earlier_session_marked": bool(new_session and pre_marked is not None and pre_marked >= 1),
        "rerun_not_marked": bool(new_session and rerun_marked == 0),
    }


def persistence_gate_never_open(reads: Any) -> bool:
    """``persistence_gate_never_open``: at least one reading, every one from a LIVE monitor, none a sighting."""
    reads = list(reads or [])
    return bool(reads) and all(isinstance(r, dict) and r.get("monitor") is True and r.get("seen") is False for r in reads)


def derive_keyboard_keys(raw: dict[str, Any]) -> dict[str, Any]:
    """AC-25 from the assay figure, the assay's ``text/plain`` and the three key presses."""
    fig = raw.get("figure") or {}
    label = fig.get("aria_label")
    live_tab, live_arrow = raw.get("live_tab"), raw.get("live_arrow")
    escape = raw.get("escape") or {}
    return {
        "svg_role_img": fig.get("found") is True and fig.get("role") == "img" and fig.get("in_svg") is True,
        "aria_label_equals_summary": bool(
            fig.get("found") is True and isinstance(label, str) and label != "" and label == raw.get("plain")
        ),
        "tab_focuses_figure": (raw.get("focus_probe") or {}).get("ok") is True and (raw.get("tab") or {}).get("is_figure") is True,
        "arrow_moves": live_arrow == ARROW_RIGHT_LIVE_TEXT and live_arrow != live_tab,
        "escape_leaves": escape.get("is_figure") is True and escape.get("rings") == 0,
    }


def classify_reopened_branch(obs: Any) -> str:
    """The D1 S2 branch of a reopened output, from what the model and the DOM show. Never a guess:
    ``unrendered`` when nothing rendered, ``unclassified`` when the reads disagree or are missing."""
    if not isinstance(obs, dict) or obs.get("rendered") is not True:
        return "unrendered"
    trusted, cell = obs.get("output_model_trusted"), obs.get("cell_model_trusted")
    if not isinstance(trusted, bool) or (isinstance(cell, bool) and cell != trusted):
        return "unclassified"
    live = all(_is_int(obs.get(k)) and obs[k] > 0 for k in ("svg_count", "live_res_count", "tabindex_count"))
    if trusted:  # a trusted output is never sanitized: it must render live
        return EXECUTED_REOPEN_BRANCH if live else "unclassified"
    mime = obs.get("chosen_mime")
    if mime == "text/plain":
        return "S2-C" if obs.get("plain_visible") is True else "unclassified"
    if mime != "text/html":
        return "unclassified"
    if obs.get("svg_count") == 0:
        return "S2-B" if obs.get("summary_visible") is True else "unclassified"
    klass, style = obs.get("svg_class_kept"), obs.get("svg_style_kept")
    if not isinstance(klass, bool) or not isinstance(style, bool):
        return "unclassified"
    return "S2-A" if klass and style else "S2-A'"


def derive_d3_keys(raw: dict[str, Any]) -> dict[str, Any]:
    """AC-24 for the recorded branch (S2-T): the always-listed keys plus ``svg_in_dom`` and ``liquid_fill_computed``."""
    saved = raw.get("saved") or {}
    svg_ok = True
    for key in (k.replace("-", "_") for k in DRAW_CELLS):
        n = _notices(_res((raw.get("reports") or {}).get(key)), "svg_count")
        svg_ok = svg_ok and n is not None and n >= 1
    return {
        "no_script_in_bundles": bool(
            saved.get("file_read_ok") is True and saved.get("has_outputs") is True and saved.get("script_count") == 0
        ),
        "reopened_branch": classify_reopened_branch(raw.get("trust")),
        "persistence_gate_never_open": persistence_gate_never_open(raw.get("gate")),
        "svg_in_dom": bool(svg_ok),
        "liquid_fill_computed": (raw.get("paints") or {}).get("liquid_fill"),
    }


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and value != ""


def derive_hc_keys(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """AC-26. ``a``: the measured context (High Contrast, Praxis CSS loaded); ``b``: the twin context with
    ``praxis-theme.css`` blocked (High Contrast, the theme's own token)."""
    hc_a = a.get("theme") == HC_THEME_NAME
    text = hc_a and a.get("summary_found") is True and _nonempty(a.get("summary_color")) and (
        a.get("summary_color") == a.get("font_token")
    )
    inline = hex_to_rgb(a.get("inline_fill"))
    sheet = (
        hc_a and a.get("sheet_found") is True and _nonempty(a.get("sheet_fill")) and a.get("sheet_fill") == a.get("layout_token")
        and inline is not None and a.get("layout_token") != inline  # a match the inline palette alone would explain proves nothing
    )
    untouched = (
        hc_a and b.get("theme") == HC_THEME_NAME
        and _nonempty(a.get("praxis_css")) and b.get("praxis_css") == ""  # loaded in A, really blocked in B
        and _is_int(b.get("blocked")) and b["blocked"] >= 1
        and _nonempty(a.get("layout_token")) and a.get("layout_token") == b.get("layout_token")
    )
    return {"hc_text_color": bool(text), "hc_sheet_fill": bool(sheet), "hc_palette_untouched": bool(untouched)}


# -- in-page helpers (harness-only; nothing here ships in dist) ---------------------------------------

#: Installed after ``DISPLAY_CHECK_JS`` (it extends ``window.__praxisDisplayCheck``). READS the notebook model
#: and the DOM. It writes only: focus on a throwaway probe element (``focusProbe`` / ``removeProbe``), a scroll
#: (``scrollTo``), the status subscription, a probe element for token colours and ONE same-value
#: ``outputs.set`` (``rerender``: the sanctioned "async re-render"). Commands are issued from Python, in one
#: named place each (``_DC_RUN_JS``, ``_DC_CMD_JS``).
DISPLAY_CHECK_OUTPUT_JS = r"""
(() => {
  const GATE_KEY = "__GATE_KEY__";
  const CHANGED = "Changed since, see deck panel.";
  const EARLIER = "Drawn in an earlier session.";
  const dc = (window.__praxisDisplayCheck = window.__praxisDisplayCheck || {});
  const app = () => window.jupyterapp;
  const panel = () => app().shell.currentWidget;
  const cellAt = (i) => { try { return panel().content.widgets[i] || null; } catch (e) { return null; } };
  // The D2 stamp reader, verbatim: the shell's stampOf, the dock's and this harness's are one expression.
  const stampOf = (output) => output.metadata?.praxis ?? output.metadata?.["text/html"]?.praxis;
  const utf8 = (s) => new TextEncoder().encode(s).length;
  const joined = (v) => (Array.isArray(v) ? v.join("") : typeof v === "string" ? v : null);
  const count = (text, needle) => (text ? text.split(needle).length - 1 : 0);
  const outputCount = (m) => (m.outputs ? (m.outputs.length ?? m.outputs.size ?? 0) : 0);
  const outputJson = (m, j) => { const x = m.outputs.get(j); return x && x.toJSON ? x.toJSON() : x; };
  const record = (o, j) => {
    const data = o.data || {};
    const html = joined(data["text/html"]);
    return {
      index: j, output_type: o.output_type ?? null, mimes: Object.keys(data),
      html_bytes: html === null ? null : utf8(html), plain: joined(data["text/plain"]),
      stamp: stampOf(o) ?? null, ename: o.ename ?? null, evalue: o.evalue ?? null,
    };
  };
  // A resource name is user data: it is compared as a string, never put in a selector.
  const holdsRes = (root, name) => Array.from(root.querySelectorAll("[data-praxis-res]")).some((e) => e.dataset.praxisRes === name);
  const resNode = (cell, name) => {
    if (!cell || typeof name !== "string") return null;
    return Array.from(cell.node.querySelectorAll(".jp-OutputArea-output")).find((n) => holdsRes(n, name)) || null;
  };
  const figureEl = (cell, name) => {
    const node = resNode(cell, name);
    return node ? Array.from(node.querySelectorAll("[data-praxis-res]")).find((e) => e.dataset.praxisRes === name) || null : null;
  };
  const resInfo = (cell, name) => {
    const node = resNode(cell, name);
    if (!node) return { found: false, svg_count: 0, changed_notices: 0, earlier_notices: 0, text_length: 0 };
    const text = node.textContent || "";
    return { found: true, svg_count: node.querySelectorAll("svg").length, changed_notices: count(text, CHANGED),
             earlier_notices: count(text, EARLIER), text_length: text.length };
  };
  const TABBABLE = 'a[href], button, input, select, textarea, [tabindex], [contenteditable="true"]';
  const tabbable = (el) => {
    const t = el.getAttribute("tabindex");
    if (t !== null && Number(t) < 0) return false;
    if (el.hasAttribute("disabled")) return false;
    return el.getClientRects().length > 0;
  };
  const computed = (el, k) => (el ? (getComputedStyle(el)[k] ?? null) : null);

  dc.stampOf = (output) => stampOf(output);
  dc.report = (a) => {
    const cell = cellAt(a.i);
    if (!cell) return { index: a.i, found: false, in_document: false, state: null, execution_count: null, execution_state: null,
                        outputs: [], res: null, error: { titles: [], praxis_error_nodes: 0 } };
    const m = cell.model;
    const outputs = [];
    for (let j = 0; j < outputCount(m); j++) outputs.push(record(outputJson(m, j), j));
    return {
      index: a.i, found: true, in_document: document.contains(cell.node),
      state: cell.node.getAttribute("data-praxis-cell-state"),
      execution_count: m.executionCount ?? null, execution_state: m.executionState ?? null, outputs,
      res: typeof a.res === "string" ? resInfo(cell, a.res) : null,
      error: { titles: Array.from(cell.node.querySelectorAll(".praxis-error__title")).map((e) => e.textContent),
               praxis_error_nodes: cell.node.querySelectorAll(".praxis-error").length },
    };
  };
  dc.figure = (a) => {
    const g = figureEl(cellAt(a.i), a.res);
    if (!g) return { found: false };
    return { found: true, tag: g.localName, role: g.getAttribute("role"), tabindex: g.getAttribute("tabindex"),
             aria_label: g.getAttribute("aria-label"), in_svg: !!g.closest("svg") };
  };
  dc.paints = (a) => {
    const node = resNode(cellAt(a.i), a.res);
    const plate = node ? node.querySelector(".sv-plate") : null;
    const liquid = node ? Array.from(node.querySelectorAll('path[fill="#73A9C2"]')) : [];
    const summary = node ? node.querySelector(".praxis-summary") : null;
    return {
      summary_found: !!summary, summary_color: computed(summary, "color"),
      sheet_found: !!plate, sheet_fill: computed(plate, "fill"), inline_fill: plate ? plate.getAttribute("fill") : null,
      liquid_count: liquid.length, liquid_fill: computed(liquid[0], "fill"), liquid_attr: liquid[0] ? liquid[0].getAttribute("fill") : null,
      svg_count: node ? node.querySelectorAll("svg").length : 0,
    };
  };
  dc.probeColor = (a) => {
    const el = document.createElement("div");
    el.style[a.prop] = `var(${a.token})`;
    document.body.appendChild(el);
    const c = getComputedStyle(el)[a.prop];
    el.remove();
    return c;
  };
  dc.praxisCss = () => getComputedStyle(document.documentElement).getPropertyValue("--praxis-moonstone").trim();

  // -- the keyboard keys: a throwaway focusable probe sits right before the figure, so Tab's next stop is
  //    whatever the page really makes it (the figure's own tabindex), not a stop the harness chose.
  dc.focusProbe = (a) => {
    const fig = figureEl(cellAt(a.i), a.res);
    const svg = fig ? fig.closest("svg") : null;
    if (!fig || !svg || !svg.parentNode) return { ok: false, next_is_figure: false, next_tag: null };
    const probe = document.createElement("span");
    probe.setAttribute("tabindex", "0");
    probe.setAttribute("data-dcheck-probe", "");
    svg.parentNode.insertBefore(probe, svg);
    probe.focus();
    const all = Array.from(document.querySelectorAll(TABBABLE)).filter(tabbable);
    const at = all.indexOf(probe);
    const next = at >= 0 ? all[at + 1] : null;
    return { ok: document.activeElement === probe, next_is_figure: next === fig, next_tag: next ? next.localName : null };
  };
  dc.removeProbe = () => {
    const probes = Array.from(document.querySelectorAll("[data-dcheck-probe]"));
    probes.forEach((p) => p.remove());
    return probes.length;
  };
  dc.activeIs = (a) => {
    const fig = figureEl(cellAt(a.i), a.res);
    const active = document.activeElement;
    const holder = active && active.closest ? active.closest("[data-praxis-res]") : null;
    return { is_figure: !!fig && active === fig, active_tag: active ? active.localName : null,
             active_res: holder ? holder.dataset.praxisRes : null };
  };
  dc.liveText = () => { const el = document.querySelector("[data-praxis-live]"); return el ? el.textContent : null; };
  dc.ringCount = (a) => { const cell = cellAt(a.i); return cell ? cell.node.querySelectorAll(".praxis-focus-ring").length : 0; };

  // -- staleness: scroll, and one same-value output re-set (an async re-render of an existing output)
  dc.scrollTo = (a) => {
    const cell = cellAt(a.i);
    if (!cell) return { ok: false };
    cell.node.scrollIntoView({ block: a.block });
    return { ok: true };
  };
  dc.rerender = (a) => {
    const cell = cellAt(a.i);
    if (!cell || !cell.model.outputs || a.j >= outputCount(cell.model)) return { ok: false, error: "no such output" };
    const value = outputJson(cell.model, a.j);
    if (!value) return { ok: false, error: "no output json" };
    try { cell.model.outputs.set(a.j, value); return { ok: true }; } catch (e) { return { ok: false, error: String(e) }; }
  };

  // -- D3: what a reopened output is (model trust, chosen mime, what survived in the DOM)
  dc.trust = (a) => {
    const cell = cellAt(a.i);
    const empty = { rendered: false, output_model_trusted: null, cell_model_trusted: null, notebook_model_trusted: null,
                    chosen_mime: null, svg_count: 0, live_res_count: 0, tabindex_count: 0, svg_class_kept: null,
                    svg_style_kept: null, summary_visible: false, plain_visible: false };
    if (!cell) return empty;
    const m = cell.model;
    let j0 = -1;
    for (let j = 0; j < outputCount(m) && j0 < 0; j++) if (stampOf(outputJson(m, j)) != null) j0 = j;
    if (j0 < 0) return empty;
    const widget = cell.outputArea && cell.outputArea.widgets ? cell.outputArea.widgets[j0] : null;
    const wnode = widget ? widget.node : null;
    const mime = wnode ? (wnode.matches("[data-mime-type]") ? wnode : wnode.querySelector("[data-mime-type]")) : null;
    if (!mime) return empty;
    const flag = (v) => (typeof v === "boolean" ? v : null);
    const o = m.outputs.get(j0);
    const svgs = Array.from(mime.querySelectorAll("svg"));
    const summary = mime.querySelector(".praxis-summary");
    const plain = joined((outputJson(m, j0).data || {})["text/plain"]) || "";
    let nbTrusted = null;
    try { nbTrusted = flag(panel().content.model.trusted); } catch (e) { nbTrusted = null; }
    return {
      rendered: true, output_model_trusted: flag(o.trusted), cell_model_trusted: flag(m.trusted), notebook_model_trusted: nbTrusted,
      chosen_mime: mime.getAttribute("data-mime-type"), svg_count: svgs.length,
      live_res_count: mime.querySelectorAll("[data-praxis-res]").length, tabindex_count: mime.querySelectorAll("[tabindex]").length,
      svg_class_kept: svgs.some((s) => s.querySelectorAll("[class]").length > 0),
      svg_style_kept: svgs.some((s) => !!s.getAttribute("style")),
      summary_visible: !!summary && (summary.textContent || "").trim().length > 0,
      plain_visible: plain !== "" && (mime.textContent || "").includes(plain),
    };
  };

  // -- the kernel-restart vocabulary, the first-save monitor, the Restart dialog, misc reads
  dc.startStatusLog = () => {
    window.__praxisDisplayCheckStatuses = [];
    panel().sessionContext.statusChanged.connect((_, status) => window.__praxisDisplayCheckStatuses.push(status));
    return true;
  };
  dc.statusLog = () => (window.__praxisDisplayCheckStatuses || []).slice();
  dc.gate = () => {
    let stored = null;
    try { stored = sessionStorage.getItem(GATE_KEY); } catch (e) { stored = null; }
    return { monitor: window.__praxisFirstSaveMonitor === true, seen: window.__praxisFirstSaveSeen === true || stored === "1" };
  };
  dc.dialogOpen = () => !!document.querySelector(".jp-Dialog");
  dc.hasCommand = (id) => app().commands.hasCommand(id);
  dc.dirty = () => { try { return panel().context.model.dirty ?? null; } catch (e) { return null; } };
  dc.panelCount = () => document.querySelectorAll(".jp-NotebookPanel").length;
  dc.windowing = () => { try { const c = panel().content; return (c.notebookConfig && c.notebookConfig.windowingMode) ?? c.windowingMode ?? null; } catch (e) { return null; } };
})()
""".replace("__GATE_KEY__", PERSISTENCE_GATE_SEEN_KEY)

#: Run one cell and AWAIT its completion (a re-run after a kernel restart cannot be told apart from the earlier
#: run by its execution count, which the restart resets). Bounded in-page as well as by the unit's watchdog.
_DC_RUN_JS = """async (a) => {
    try {
        const w = window.jupyterapp.shell.currentWidget;
        w.content.activeCellIndex = a.i;
        const p = window.jupyterapp.commands.execute('notebook:run-cell');
        const timer = new Promise((r) => setTimeout(() => r('timeout'), a.timeout_ms));
        const done = await Promise.race([Promise.resolve(p).then(() => 'done'), timer]);
        return {ok: done === 'done', error: done === 'done' ? null : 'timeout'};
    } catch (e) { return {ok: false, error: String(e)}; }
}"""

#: Any other command (save, restart, run-all), awaited or not, bounded in-page.
_DC_CMD_JS = """async (a) => {
    try {
        const p = window.jupyterapp.commands.execute(a.id, a.args || {});
        if (!a.wait) {
            if (p && p.catch) p.catch((e) => { window.__praxisDisplayCheckError = String(e); });
            return {ok: true};
        }
        const timer = new Promise((r) => setTimeout(() => r('timeout'), a.timeout_ms));
        const done = await Promise.race([Promise.resolve(p).then(() => 'done'), timer]);
        return {ok: done === 'done', error: done === 'done' ? null : 'timeout'};
    } catch (e) { return {ok: false, error: String(e)}; }
}"""

_DC_READ_FILE_JS = """async (path) => {
    try {
        const m = await window.jupyterapp.serviceManager.contents.get(path, {content: true, type: "notebook"});
        return {ok: true, content: m.content};
    } catch (e) { return {ok: false, error: String(e)}; }
}"""

_DC_CONTEXT_SAVE_JS = """async () => {
    try { await window.jupyterapp.shell.currentWidget.context.save(); return {ok: true}; }
    catch (e) { return {ok: false, error: String(e)}; }
}"""

_DC_CLOSE_JS = """() => {
    const w = window.jupyterapp.shell.currentWidget;
    if (!w) return false;
    w.close();
    return true;
}"""


class DisplayDriver:
    """One Playwright page, seen as the calls the D2-D4 scenarios make (each is one bounded interaction).

    The scenarios take a ``driver`` so that their ORDER and key plumbing are tested against a scripted fake
    (``web-repl/tests/test_repl_smoke_resume.py``). This class is exercised only by a real browser run.
    """

    def __init__(self, session: Any, *, page: Any = None, blocked: list[str] | None = None, sleep: Any = time.sleep) -> None:
        self.session = session
        self.page = page if page is not None else session.page
        self.blocked: list[str] = blocked if blocked is not None else []
        self.sleep = sleep
        self._n_cells = 0

    # -- session ----------------------------------------------------------------------------------
    def _dc(self, expr: str, arg: Any = None) -> Any:
        return _dc(self.page, expr, arg)

    def _install(self) -> None:
        self.page.wait_for_function(
            "() => !!window.jupyterapp && !!window.jupyterapp.shell", timeout=DISPLAY_NAV_TIMEOUT_MS
        )
        self.page.evaluate(DISPLAY_CHECK_JS)
        self.page.evaluate(DISPLAY_CHECK_OUTPUT_JS)

    def open_lab(self) -> None:
        self.page.goto(self.session.lab_url, wait_until="load", timeout=DISPLAY_NAV_TIMEOUT_MS)
        self._install()

    def set_theme(self, name: str) -> None:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        wait_for_theme_ready(self.page)
        changed = self.page.evaluate(_DC_THEME_JS, name)
        if not changed.get("ok"):
            raise DisplayCheckError(f"apputils:change-theme {name!r} failed: {changed.get('error')!r}")
        try:
            self.page.wait_for_function(
                "(want) => window.__praxisDisplayCheck.themeName() === want", arg=name, timeout=30_000
            )
        except PlaywrightTimeoutError:
            LOG.warning("theme %r never applied; the keys will say so", name)

    def theme_name(self) -> Any:
        return self._dc("themeName()")

    def seed_and_open(self, name: str, notebook: dict[str, Any]) -> None:
        saved = self.page.evaluate(_DC_SAVE_JS, {"path": name, "content": notebook})
        if not saved.get("ok"):
            raise DisplayCheckError(f"could not seed {name}: {saved.get('error')!r}")
        _open_existing_notebook(self.page, name, timeout_ms=DISPLAY_NAV_TIMEOUT_MS)
        self._n_cells = len(notebook["cells"])
        self.page.wait_for_function(
            "(n) => window.__praxisDisplayCheck.cellsReady(n)", arg=self._n_cells, timeout=DISPLAY_NAV_TIMEOUT_MS
        )
        self._dc("markCells()")
        self._dc("startStatusLog()")

    def wait_kernel_idle(self) -> None:
        self.page.wait_for_function(
            "() => window.__praxisDisplayCheck.kernelStatus() === 'idle'", timeout=DISPLAY_KERNEL_TIMEOUT_MS
        )

    # -- cells --------------------------------------------------------------------------------------
    def run_cell(self, index: int) -> None:
        """Run one cell through ``notebook:run-cell`` and wait until the model says it is done. A command that
        rejects (an error cell can) is not fatal by itself: the model wait below decides; a timeout is."""
        ran = self.page.evaluate(_DC_RUN_JS, {"i": index, "timeout_ms": DISPLAY_CELL_TIMEOUT_MS})
        if not ran.get("ok"):
            if ran.get("error") == "timeout":
                raise DisplayCheckError(f"cell {index} did not finish within {DISPLAY_CELL_TIMEOUT_MS} ms")
            LOG.warning("notebook:run-cell for cell %s rejected (%s); waiting on the model", index, ran.get("error"))
        self.page.wait_for_function(
            "(i) => window.__praxisDisplayCheck.modelDone(i)", arg=index, timeout=DISPLAY_CELL_TIMEOUT_MS
        )

    def report(self, index: int, res: str | None = None) -> dict[str, Any]:
        return self._dc("report(a)", {"i": index, "res": res})

    def poll(self, read: Any, ok: Any, timeout_s: float) -> tuple[Any, bool]:
        return poll_until(read, ok, timeout_s=timeout_s, interval_s=0.25, sleep=self.sleep)

    # -- keyboard ---------------------------------------------------------------------------------------
    def figure(self, index: int, res: str) -> dict[str, Any]:
        return self._dc("figure(a)", {"i": index, "res": res})

    def focus_probe(self, index: int, res: str) -> dict[str, Any]:
        return self._dc("focusProbe(a)", {"i": index, "res": res})

    def remove_probe(self) -> int:
        return self._dc("removeProbe()")

    def press(self, key: str) -> None:
        self.page.keyboard.press(key)

    def settle(self, ms: float) -> None:
        self.page.wait_for_timeout(ms)

    def live_text(self) -> Any:
        return self._dc("liveText()")

    def active_is_figure(self, index: int, res: str) -> bool:
        return bool(self._dc("activeIs(a)", {"i": index, "res": res}).get("is_figure"))

    def ring_count(self, index: int, res: str) -> int:
        return int(self._dc("ringCount(a)", {"i": index, "res": res}))

    # -- staleness --------------------------------------------------------------------------------------
    def scroll_to(self, index: int, block: str = "center") -> None:
        self._dc("scrollTo(a)", {"i": index, "block": block})

    def rerender(self, index: int, j: int) -> bool:
        return bool(self._dc("rerender(a)", {"i": index, "j": j}).get("ok"))

    def save_and_read(self, name: str) -> dict[str, Any]:
        """``docmanager:save``, then (only if the FILE on the drive still lacks the outputs) the document
        context's own save; verified by reading the file with ``contents.get``."""
        last: dict[str, Any] = {"ok": False, "content": None, "method": None}
        for method, fire in (
            ("docmanager:save", lambda: self.page.evaluate(
                _DC_CMD_JS, {"id": "docmanager:save", "wait": True, "timeout_ms": DISPLAY_STEP_TIMEOUT_MS})),
            ("context.save", lambda: self.page.evaluate(_DC_CONTEXT_SAVE_JS)),
        ):
            fire()

            def read(method: str = method) -> dict[str, Any]:
                got = self.page.evaluate(_DC_READ_FILE_JS, name)
                content = got.get("content") if got.get("ok") else None
                return {"ok": bool(got.get("ok")) and saved_notebook_has_outputs(content), "content": content, "method": method}

            last, verified = poll_until(read, lambda r: r["ok"], timeout_s=10.0, interval_s=0.5, sleep=self.sleep)
            if verified:
                break
        return last

    def restart_kernel(self) -> dict[str, Any]:
        """Restart the kernel of the current notebook with ``kernelmenu:restart`` (the Restart dialog accepted if it
        appears) and wait for the restart status vocabulary then ``idle``. Falls back to the kernel API only if the
        command does not exist (recorded in ``via``)."""
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

        page = self.page
        before = len(self._dc("statusLog()"))
        evidence: dict[str, Any] = {"via": None, "dialog_seen": False}
        if self._dc("hasCommand(a)", "kernelmenu:restart"):
            evidence["via"] = "kernelmenu:restart"
            page.evaluate(_DC_CMD_JS, {"id": "kernelmenu:restart", "wait": False})
            try:
                page.wait_for_selector(".jp-Dialog", timeout=10_000)
                evidence["dialog_seen"] = True
                page.click(".jp-Dialog .jp-mod-accept")
                page.wait_for_selector(".jp-Dialog", state="detached", timeout=DISPLAY_NAV_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                LOG.info("no Restart Kernel dialog appeared")
        else:
            evidence["via"] = "kernel.restart"
            done = page.evaluate(
                """async () => { try { await window.jupyterapp.shell.currentWidget.sessionContext.session.kernel.restart();
                                       return {ok: true}; } catch (e) { return {ok: false, error: String(e)}; } }"""
            )
            if not done.get("ok"):
                raise DisplayCheckError(f"kernel.restart() failed: {done.get('error')!r}")
        statuses, ok = poll_until(
            lambda: self._dc("statusLog()")[before:], restart_finished,
            timeout_s=DISPLAY_KERNEL_TIMEOUT_MS / 1000.0, interval_s=0.5, sleep=self.sleep,
        )
        evidence["statuses"] = statuses
        if not ok:
            raise DisplayCheckError(f"the kernel did not restart and come back idle: statuses {statuses!r}")
        return evidence

    def run_all(self) -> None:
        done = self.page.evaluate(
            _DC_CMD_JS, {"id": "notebook:run-all-cells", "wait": True, "timeout_ms": DISPLAY_KERNEL_TIMEOUT_MS}
        )
        if not done.get("ok"):
            raise DisplayCheckError(f"notebook:run-all-cells did not finish: {done.get('error')!r}")

    # -- trust, paints, gate, reload -----------------------------------------------------------------------
    def trust(self, index: int) -> dict[str, Any]:
        return self._dc("trust(a)", {"i": index})

    def paints(self, index: int, res: str) -> dict[str, Any]:
        return self._dc("paints(a)", {"i": index, "res": res})

    def probe_color(self, prop: str, token: str) -> Any:
        return self._dc("probeColor(a)", {"prop": prop, "token": token})

    def praxis_css(self) -> Any:
        return self._dc("praxisCss()")

    def gate(self) -> dict[str, Any]:
        return self._dc("gate()")

    def windowing(self) -> Any:
        return self._dc("windowing()")

    def blocked_count(self) -> int:
        return len(self.blocked)

    def close_panel(self, name: str) -> None:
        if not self.page.evaluate(_DC_CLOSE_JS):
            raise DisplayCheckError(f"no notebook panel to close for {name}")
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            if self._dc("panelCount()") == 0:
                return
            if self._dc("dialogOpen()"):
                LOG.info("a dialog blocked closing %s; accepting it", name)
                self.page.click(".jp-Dialog .jp-mod-accept", timeout=5000)
            self.sleep(0.5)
        raise DisplayCheckError(f"the notebook panel for {name} would not close")

    def reload_and_open(self, name: str, notebook: dict[str, Any]) -> None:
        """A full page reload (fresh JS state), then the document is opened from the drive. Nothing is run."""
        self.page.reload(wait_until="load", timeout=DISPLAY_NAV_TIMEOUT_MS)
        self._install()
        self.page.wait_for_timeout(3000)  # let a workspace restore settle
        _open_existing_notebook(self.page, name, timeout_ms=DISPLAY_NAV_TIMEOUT_MS)
        self._n_cells = len(notebook["cells"])
        self.page.wait_for_function(
            "(n) => window.__praxisDisplayCheck.cellsReady(n)", arg=self._n_cells, timeout=DISPLAY_NAV_TIMEOUT_MS
        )
        self._dc("markCells()")


# -- the scenarios --------------------------------------------------------------------------------------


def _first_error(report: dict[str, Any]) -> dict[str, Any] | None:
    return next((o for o in report.get("outputs") or [] if o.get("output_type") == "error"), None)


def _run_setup(driver: Any, idx: dict[str, int], key: str) -> None:
    """Run one setup cell and refuse to go on if it did not run cleanly: every later key would be about a broken
    setup, not about the product."""
    i = idx[FIXTURE_CELLS[key]]
    driver.run_cell(i)
    report = driver.report(i)
    err = _first_error(report)
    if err is not None or report.get("execution_count") is None:
        what = f"{err.get('ename')}: {err.get('evalue')}" if err else "it never ran"
        raise DisplayCheckError(f"setup cell {key!r} failed: {what}")


def _drawing_session(report: Any) -> str | None:
    out = _drawing(report)
    return out["stamp"].get("session") if out else None


def _keyboard_raw(driver: Any, index: int, plain: Any) -> dict[str, Any]:
    """AC-25's presses on the assay figure, with the figure scrolled into view first."""
    res = "assay"
    driver.scroll_to(index, "center")
    driver.settle(500)
    raw: dict[str, Any] = {"figure": driver.figure(index, res), "plain": plain}
    try:
        raw["focus_probe"] = driver.focus_probe(index, res)
        driver.press("Tab")
        driver.settle(200)
        raw["tab"] = {"is_figure": driver.active_is_figure(index, res)}
        raw["live_tab"] = driver.live_text()
        driver.press("ArrowRight")
        driver.settle(200)
        raw["live_arrow"] = driver.live_text()
        driver.press("Escape")
        driver.settle(200)
        raw["escape"] = {"is_figure": driver.active_is_figure(index, res), "rings": driver.ring_count(index, res)}
    finally:
        driver.remove_probe()
    return raw


def run_d2(driver: Any, fixture: dict[str, Any]) -> dict[str, Any]:
    """D2 (AC-21, AC-22, AC-23, AC-25): one kernel, cells run ONE AT A TIME (Run All only in its own notebook,
    last), one kernel restart. Returns the derived keys plus informational evidence."""
    idx = require_cells(fixture, *FIXTURE_CELLS.values())
    cid = FIXTURE_CELLS
    evidence: dict[str, Any] = {}
    driver.open_lab()
    driver.seed_and_open(DISPLAY_NOTEBOOK_NAME, fixture)
    driver.wait_kernel_idle()
    for key in ("boot", "assemble", "transfers", "pickup"):
        _run_setup(driver, idx, key)

    # AC-21: the four drawing cells
    for key in ("draw_source", "draw_assay", "draw_tips", "draw_deck"):
        driver.run_cell(idx[cid[key]])
    reports = {
        cell.replace("-", "_"): driver.report(idx[cell], res_name) for cell, (_k, _r, res_name) in DRAW_CELLS.items()
    }
    keys: dict[str, Any] = derive_repr_keys(reports)
    assay_out = _drawing(reports["draw_assay"]) or {}

    # AC-25: the keyboard, on the assay, before anything changes
    keys.update(derive_keyboard_keys(_keyboard_raw(driver, idx[cid["draw_assay"]], assay_out.get("plain"))))

    # AC-23: an aspirate-only cell changes what `source` drew and nothing the tip rack or assay drew
    driver.run_cell(idx[cid["aspirate"]])
    source_i, tips_i = idx[cid["draw_source"]], idx[cid["draw_tips"]]
    source_read, marked = driver.poll(
        lambda: driver.report(source_i, "source"), lambda r: (_notices(_res(r), "changed_notices") or 0) >= 1, 5.0
    )
    tips_read = driver.report(tips_i, "tips_300")
    # persisted first, while the mark is known to be in the DOM
    pre_save = driver.report(source_i, "source")
    saved = driver.save_and_read(DISPLAY_NOTEBOOK_NAME)
    content = saved.get("content")
    persisted = {
        "file_read_ok": bool(saved.get("ok")),
        "has_outputs": saved_notebook_has_outputs(content),
        "contains_changed": CHANGED_NOTICE in json.dumps(content or {}),
        "mark_present_before_save": (_notices(_res(pre_save), "changed_notices") or 0) >= 1,
    }
    # then the disturbances: away and back (windowing), and an async re-render of the very output
    driver.scroll_to(idx[cid["marker"]], "end")
    driver.settle(800)
    driver.scroll_to(source_i, "center")
    driver.settle(800)
    after_scroll, _ = driver.poll(
        lambda: driver.report(source_i, "source"), lambda r: _notices(_res(r), "changed_notices") == 1, 5.0
    )
    drawn = _drawing(pre_save)
    rerender_ok = bool(drawn) and driver.rerender(source_i, drawn["index"])
    _, _settled = driver.poll(
        lambda: driver.report(source_i, "source"), lambda r: _notices(_res(r), "changed_notices") == 1, 5.0
    )
    driver.settle(500)  # then once more: exactly once, not a transient
    after_rerender = driver.report(source_i, "source")
    keys.update(
        derive_stale_keys(
            {
                "source": _res(source_read), "tips": _res(tips_read), "persisted": persisted,
                "after_scroll": _res(after_scroll), "after_rerender": _res(after_rerender), "rerender_ok": rerender_ok,
            }
        )
    )

    # AC-22: the error cells, one at a time
    error_reports: dict[str, Any] = {}
    for key in ("e1", "e2", "e4", "e6"):
        driver.run_cell(idx[cid[key]])
        error_reports[key] = driver.report(idx[cid[key]])
    driver.run_cell(idx[cid["value_error"]])
    value_error = driver.report(idx[cid["value_error"]])

    # AC-23: a kernel restart, the boot cell, then a re-run drawing cell (the panel's new current session)
    assay_i = idx[cid["draw_assay"]]
    pre_session = _drawing_session(driver.report(assay_i, "assay"))
    restart = driver.restart_kernel()
    driver.wait_kernel_idle()
    driver.run_cell(idx[cid["boot"]])
    driver.run_cell(idx[cid["redraw"]])
    pre_read, _ = driver.poll(
        lambda: driver.report(assay_i, "assay"), lambda r: (_notices(_res(r), "earlier_notices") or 0) >= 1, 5.0
    )
    driver.settle(500)
    rerun_read = driver.report(idx[cid["redraw"]], "redraw")
    keys.update(
        derive_session_keys(
            {
                "pre": {"session": pre_session, "res": _res(pre_read)},
                "rerun": {"session": _drawing_session(rerun_read), "res": _res(rerun_read)},
            }
        )
    )
    gate_reads = [driver.gate()]

    # AC-22 `runall_stops`: the one Run All, in its own notebook (a second kernel), last
    pair = build_runall_notebook(fixture)
    pidx = cell_indices(pair)
    driver.seed_and_open(RUNALL_NOTEBOOK_NAME, pair)
    driver.wait_kernel_idle()
    driver.run_all()
    runall = {c: driver.report(pidx[c]) for c in RUNALL_CELL_IDS}
    keys.update(derive_error_keys(error_reports, value_error, runall))
    gate_reads.append(driver.gate())
    keys["persistence_gate_never_open"] = persistence_gate_never_open(gate_reads)
    evidence.update(
        restart=restart, gate_reads=gate_reads, persisted=persisted, windowing_mode=driver.windowing(),
        live_arrow_expected=ARROW_RIGHT_LIVE_TEXT,
        # the raw reports behind `error_panels` / `error_status` / `other_errors_plain` / `runall_stops`, so a
        # failing key can be read off the result file instead of needing a re-run with extra logging
        error_reports=error_reports, value_error=value_error, runall=runall,
    )
    keys["evidence"] = evidence
    return keys


def run_d3(driver: Any, fixture: dict[str, Any]) -> dict[str, Any]:
    """D3 (AC-24): execute its own drawing cells, save, close, reload the page, reopen from the drive; nothing is
    run after the reload, so what is read is what was SAVED."""
    idx = require_cells(fixture, *FIXTURE_CELLS.values())
    cid = FIXTURE_CELLS
    driver.open_lab()
    driver.seed_and_open(DISPLAY_NOTEBOOK_NAME, fixture)
    driver.wait_kernel_idle()
    for key in ("boot", "assemble", "transfers"):
        _run_setup(driver, idx, key)
    for key in ("draw_source", "draw_assay", "draw_tips", "draw_deck"):
        driver.run_cell(idx[cid[key]])
    saved = driver.save_and_read(DISPLAY_NOTEBOOK_NAME)
    content = saved.get("content")
    gate_reads = [driver.gate()]
    driver.close_panel(DISPLAY_NOTEBOOK_NAME)
    driver.reload_and_open(DISPLAY_NOTEBOOK_NAME, fixture)
    for cell in DRAW_CELLS:  # wait (bounded) for each reopened output to render
        driver.poll(lambda cell=cell: driver.trust(idx[cell]), lambda t: t.get("rendered") is True, 20.0)
    reports = {
        cell.replace("-", "_"): driver.report(idx[cell], res_name) for cell, (_k, _r, res_name) in DRAW_CELLS.items()
    }
    trust = driver.trust(idx["draw-assay"])
    paints = driver.paints(idx["draw-assay"], "assay")
    gate_reads.append(driver.gate())
    raw = {
        "saved": {
            "file_read_ok": bool(saved.get("ok")), "has_outputs": saved_notebook_has_outputs(content),
            "script_count": count_scripts_in_outputs(content),
        },
        "reports": reports, "trust": trust, "paints": paints, "gate": gate_reads,
    }
    keys = derive_d3_keys(raw)
    keys["branch_evidence"] = {  # what the OTHER branches' keys would read; never listed (the recorded branch is S2-T)
        "summary_text_visible": trust.get("summary_visible"), "text_plain_visible": trust.get("plain_visible"),
        "liquid_fill_attr": paints.get("liquid_attr"), "chosen_mime": trust.get("chosen_mime"),
    }
    keys["evidence"] = {"trust": trust, "paints": paints, "gate_reads": gate_reads, "saved_script_count": raw["saved"]["script_count"]}
    return keys


def run_d4(driver: Any, fixture: dict[str, Any], *, blocked_driver_factory: Any) -> dict[str, Any]:
    """D4 (AC-26): "JupyterLab Dark High Contrast" in two contexts. The first runs the setup cells and draws the
    assay; the second (``praxis-theme.css`` blocked) only reads the theme's own ``--jp-layout-color0``."""
    idx = require_cells(fixture, *FIXTURE_CELLS.values())
    driver.open_lab()
    driver.set_theme(HC_THEME_NAME)
    driver.seed_and_open(DISPLAY_NOTEBOOK_NAME, fixture)
    driver.wait_kernel_idle()
    for key in ("boot", "assemble", "transfers"):
        _run_setup(driver, idx, key)
    assay_i = idx[FIXTURE_CELLS["draw_assay"]]
    driver.run_cell(assay_i)
    paints = driver.paints(assay_i, "assay")
    a = {
        "theme": driver.theme_name(), "summary_found": paints.get("summary_found"), "summary_color": paints.get("summary_color"),
        "font_token": driver.probe_color("color", "--jp-content-font-color0"),
        "sheet_found": paints.get("sheet_found"), "sheet_fill": paints.get("sheet_fill"), "inline_fill": paints.get("inline_fill"),
        "layout_token": driver.probe_color("backgroundColor", "--jp-layout-color0"), "praxis_css": driver.praxis_css(),
    }
    blocked = blocked_driver_factory()
    blocked.open_lab()
    blocked.set_theme(HC_THEME_NAME)
    b = {
        "theme": blocked.theme_name(), "layout_token": blocked.probe_color("backgroundColor", "--jp-layout-color0"),
        "praxis_css": blocked.praxis_css(), "blocked": blocked.blocked_count(),
    }
    keys = derive_hc_keys(a, b)
    keys["evidence"] = {"measured": a, "blocked": b}
    return keys


def run_display_scenario(session: Any, unit: HarnessUnit, env: Any, *, notebook: dict | None = None) -> dict[str, Any]:
    """The scenario body of one ``--display-check`` unit: D1 and D1-dark (chrome, sprint A) or D2, D3 and D4
    (sprint B). One unit, one process, one browser; the session is closed by ``run_scenario``'s bounded teardown."""
    if unit.id in ("D1", "D1-dark"):
        return run_chrome_scenario(session, unit, env, notebook=notebook)
    if unit.id not in ("D2", "D3", "D4"):
        raise DisplayCheckError(f"no scenario body for unit {unit.id!r}")
    fixture = notebook if notebook is not None else json.loads(DISPLAY_NOTEBOOK_PATH.read_text())
    driver = DisplayDriver(session)
    if unit.id == "D2":
        return run_d2(driver, fixture)
    if unit.id == "D3":
        return run_d3(driver, fixture)

    def blocked_driver() -> Any:
        page, blocked = session.open_page(unit, block=(THEME_CSS_GLOB,))
        return DisplayDriver(session, page=page, blocked=blocked)

    return run_d4(driver, fixture, blocked_driver_factory=blocked_driver)


# -- The --display-check entry point --------------------------------------------------


def run_display_check(
    args: argparse.Namespace,
    *,
    runner: Any = None,
    hash_env: HashEnv | None = None,
    unit_argv_prefix: list[str] | None = None,
    scenario_entry: Any = None,
) -> int:
    """``--display-check``: one unit (``--scenario``), the driver, or ``--aggregate-only``.

    Returns the exit code (2 for a usage error, raised before anything launches); a real
    ``--scenario`` run ends in ``os._exit(stamp.exit)`` inside ``run_scenario`` and never
    returns. ``runner``, ``hash_env``, ``unit_argv_prefix`` and ``scenario_entry`` are test seams.
    """
    problem = out_dir_rule_error(args)
    if problem is None and args.neg:
        problem = (
            f"--neg {args.neg[0]} is a --dock-check flag; --display-check has no negative "
            "flag (AC-39(a) mutates a dist copy instead)"
        )
    if problem is None and args.aggregate_only and (args.fresh or args.scenario):
        problem = "--aggregate-only recomputes nothing: it cannot be combined with --fresh or --scenario"
    table = [u for u in UNIT_TABLE if u.check == DISPLAY_CHECK]
    if problem is None and args.scenario and args.scenario not in {u.id for u in table}:
        problem = f"unknown --display-check scenario {args.scenario!r}; units are {[u.id for u in table]}"
    if problem is not None:
        LOG.error("%s", problem)
        return 2
    out_dir = Path(args.out_dir).resolve() if args.out_dir else default_out_dir(DISPLAY_CHECK)
    neg = tuple(args.neg)

    def make_env() -> HashEnv:
        if hash_env is not None:
            return hash_env
        return build_hash_env(args, str(resolve_chrome_path(args.chrome_path)))

    if args.scenario:
        entry = scenario_entry or run_scenario
        return entry(
            args.scenario,
            out_dir=out_dir,
            env_fn=make_env,
            session_factory=lambda unit, env: DisplaySession(unit, args, env),
            scenario_fn=run_display_scenario,
            neg=neg,
        )

    try:
        env = make_env()
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        LOG.error("cannot build the input set: %s: %s", type(exc).__name__, exc)
        return 2
    prefix = unit_argv_prefix if unit_argv_prefix is not None else [sys.executable, str(Path(__file__).resolve())]

    def argv_for(unit: HarnessUnit) -> list[str]:
        argv = prefix + [
            "--display-check", "--scenario", unit.id,
            "--base-path", args.base_path,
            "--out-dir", str(out_dir),
            "--serve-dir", str(Path(args.serve_dir).resolve()),
        ]
        if env.chrome_path:
            argv += ["--chrome-path", env.chrome_path]
        for flag in neg:
            argv += ["--neg", flag]
        return argv

    _, code = run_units_driver(
        table=table,
        out_dir=out_dir,
        inputs_for=lambda unit: unit_inputs(unit, env, neg),
        argv_for=argv_for,
        runner=runner or unit_runner_module(),
        fresh=args.fresh,
        aggregate_only=args.aggregate_only,
        cwd=str(REPO_ROOT),
        check=DISPLAY_CHECK,
        meta={
            "chrome_path": env.chrome_path,
            "chrome_version": env.chrome_version,
            "base_path": env.base_path,
        },
    )
    return code


# ---------------------------------------------------------------------------
# --dock-check (epic 260929_notebook-display-design, task C7; spec D16, D6, D11, D12, AC-30..AC-42).
#
# The Visualizer3D deck panel gate: units K1a (AC-34, AC-35, AC-37), K1b (AC-38) and K2 (AC-36) and the
# negative-only unit N-d (AC-39(d)), on the SAME preemption-safe machinery as --display-check (the unit
# table, input hashing, stamps, resume, the aggregate, `--aggregate-only`, `run_scenario`); a dock unit
# differs only in its browser (a FULL Chromium with SwiftShader WebGL, never headless_shell) and in its
# scenario body. Everything pure in this section (the D6 sizing table, the key derivations, the static
# greps) is tested without a browser by web-repl/tests/test_repl_smoke_resume.py; the scenario bodies take
# a `driver` so their ORDER and key plumbing are tested against a scripted fake, and only a real run
# exercises `DockSession` / `DockDriver` and the in-page helpers.
# ---------------------------------------------------------------------------

DOCK_CHECK = "dock-check"

# -- static greps the dock gate closes (AC-39(c), AC-41 R19, AC-31 extended R21) -------------------------------


def _glob_match(name: str, patterns: Any) -> bool:
    import fnmatch

    return any(fnmatch.fnmatchcase(name, p) for p in patterns)


def grep_tree(
    root: Any,
    paths: Any,
    pattern: str,
    *,
    include: Any = (),
    exclude_dirs: Any = (),
) -> list[tuple[str, int, str]]:
    """``grep -rnE <pattern> [--include=GLOB ...] [--exclude-dir=GLOB ...] <paths>`` run from ``root``, in Python.

    Returns ``(path relative to root, 1-based line, line text)`` in path order. ``include`` globs select files by
    base name (empty: every file); ``exclude_dirs`` globs skip a directory by base name while recursing. A path that
    does not exist raises ``FileNotFoundError`` (``grep`` exits 2 there; an unreadable path is never "no hit"). A file
    with a NUL byte is binary and yields no line, as grep reports it with one "Binary file matches" line instead."""
    rx = re.compile(pattern)
    base = Path(root)
    hits: list[tuple[str, int, str]] = []

    def scan(path: Path) -> None:
        if include and not _glob_match(path.name, include):
            return
        try:
            data = path.read_bytes()
        except OSError:
            return
        if b"\0" in data:
            return
        for number, line in enumerate(data.decode("utf-8", "replace").splitlines(), start=1):
            if rx.search(line):
                hits.append((path.relative_to(base).as_posix(), number, line))

    def walk(directory: Path) -> None:
        for entry in sorted(directory.iterdir(), key=lambda p: p.name):
            if entry.is_dir():
                if not _glob_match(entry.name, exclude_dirs):
                    walk(entry)
            elif entry.is_file():
                scan(entry)

    for rel in paths:
        target = base / rel
        if not target.exists():
            raise FileNotFoundError(f"grep: {rel}: No such file or directory")
        if target.is_dir():
            walk(target)
        else:
            scan(target)
    return hits


#: AC-39(c): no test-only hooks in the product JS. ``--exclude-dir=__tests__`` is the spec's one exclusion: a
#: ``*.test.js`` next to a source file IS scanned, so a test may not spell the token either (dock.test.js built
#: its expression from pieces for this reason).
AC39C_PATTERN = r"__praxis_test|data-praxis-test"
AC39C_PATHS = ("web-repl/shell/display", "web-repl/overlay/assets/visualizer3d-augmentations")
#: AC-41 R19: the serial-port prompts are the visualizer transport's; none of these paths may name them.
R19_PATTERN = r"requestDevice|requestPort"
R19_PATHS = (
    "web-repl/overlay/assets/visualizer-augmentations",
    "web-repl/overlay/assets/visualizer3d-augmentations",
    "web-repl/shell/display",
)
#: AC-31, extended R21 (D7 "R21 check" over six paths): five directories and ``dock.js``.
R21_EXTENDED_DIRS = (
    "web-repl/overlay/assets/python/praxis/viz/",
    "web-repl/overlay/assets/visualizer/",
    "web-repl/overlay/assets/visualizer-augmentations/",
    "web-repl/overlay/assets/visualizer3d/",
    "web-repl/overlay/assets/visualizer3d-augmentations/",
)
R21_EXTENDED_FILES = ("web-repl/shell/display/dock.js",)
R21_EXTENDED_PATHS = R21_EXTENDED_DIRS + R21_EXTENDED_FILES
R21_CHANNEL = "praxis_repl"
R21_DOC_FORM = "``praxis_repl``"


def ac39c_hits(root: Any) -> list[tuple[str, int, str]]:
    """AC-39(c) verbatim: ``grep -rnE '__praxis_test|data-praxis-test' shell/display visualizer3d-augmentations
    --include='*.js' --exclude-dir=__tests__``. The gate passes iff this is empty."""
    return grep_tree(root, AC39C_PATHS, AC39C_PATTERN, include=("*.js",), exclude_dirs=("__tests__",))


def r19_check(root: Any) -> tuple[bool, list[tuple[str, int, str]]]:
    """AC-41 R19: the grep must exit **1 exactly**. ``(ok, hits)``: ``ok`` is false on any hit and on a missing path
    (grep's 2), so an unreadable tree never reads as a pass."""
    try:
        hits = grep_tree(root, R19_PATHS, R19_PATTERN)
    except FileNotFoundError:
        return False, []
    return (not hits), hits


def r21_extended_check(root: Any) -> dict[str, Any]:
    """The D7 "R21 check" over the six paths of AC-31, in its Python form (same rule as the bash gate).

    ``test -d`` on each directory and ``test -f`` on ``dock.js`` (``paths_exist``); the first grep must exit 0 or 1
    (``first_grep_status``: 2, an unreadable path, fails); the RST documentation form `` ``praxis_repl`` `` is
    stripped from every hit (``sed``); and NO line may still name the channel (``residual`` empty). Returns
    ``{ok, paths_exist, first_grep_status, hits, residual}``; ``hits`` is the plain grep, ``residual`` what the strip
    leaves."""
    base = Path(root)
    exist = all((base / d).is_dir() for d in R21_EXTENDED_DIRS) and all((base / f).is_file() for f in R21_EXTENDED_FILES)
    out: dict[str, Any] = {"ok": False, "paths_exist": exist, "first_grep_status": 2, "hits": [], "residual": []}
    if not exist:
        return out
    try:
        hits = grep_tree(base, R21_EXTENDED_PATHS, R21_CHANNEL)
    except FileNotFoundError:
        return out
    out["first_grep_status"] = 0 if hits else 1
    out["hits"] = hits
    out["residual"] = [h for h in hits if R21_CHANNEL in h[2].replace(R21_DOC_FORM, "")]
    out["ok"] = out["first_grep_status"] in (0, 1) and not out["residual"]
    return out


# -- the D6 sizing table (AC-36 "keyed by the D6 sizing case"; AC-39(d)'s skip rule) ----------------------------


#: AC-1 (spike S1, bathos run 1e0cab6d-0765-4c16-802f-84c571637a3e, outcome ``s1_a``): the four facts the D6
#: table is keyed by. ``css_limits_honoured`` (inline ``min-width``/``max-width`` held after a splitter drag),
#: ``layout_sizing_reachable`` (``saveLayout`` -> edit ``sizes`` -> ``restoreLayout`` moved the split),
#: ``css_limits_refit`` (limits + ``parent.fit()`` moved the widget) and ``restore_layout_keeps_iframe``
#: (``restoreLayout()`` reloaded nothing). Re-recording AC-1 means editing THIS constant (and so the harness hash).
SIZING_RECORD: dict[str, bool] = {
    "css_limits_honoured": True,
    "layout_sizing_reachable": True,
    "css_limits_refit": True,
    "restore_layout_keeps_iframe": True,
}
SIZING_CASES = ("honoured_reachable", "ignored_reachable", "honoured_unreachable", "ignored_unreachable")  # last is S1-L
ASSERTED = "asserted"
RECORDED_ONLY = "recorded-only"
#: The width-key families of AC-36 (the names S1 recorded in ``width_key_status``; ``fit_after_tier_change`` is one
#: family per tier it re-satisfies, because a case can assert one tier and record the other).
WIDTH_CATEGORIES = (
    "open_width_1280_1599",
    "drag_clamp_1280_1599",
    "fit_after_tier_change_1280_1599",
    "open_width_ge_1600",
    "fit_after_tier_change_ge_1600",
    "resize_within_wide",
)
_WIDE_CATEGORIES = ("open_width_ge_1600", "fit_after_tier_change_ge_1600", "resize_within_wide")

#: AC-36 tolerances. The wide formula is ±8 px (D6). The 420-480 clamp has no stated tolerance: 2 px absorbs
#: sub-pixel layout (S1 measured with 3); a drag target is 300 / 700 px, far outside either.
WIDE_TOL_PX = 8.0
CLAMP_TOL_PX = 2.0
PANEL_MIN_PX = 420.0
PANEL_MAX_PX = 480.0
NOTEBOOK_CAP_PX = 960.0
VIEWER_MIN_HEIGHT_PX = 300.0
MOTION_MAX_HEIGHT_PX = 36.0


def sizing_case(css_limits_honoured: bool, layout_sizing_reachable: bool) -> str:
    """The D6 table row: ``honoured_reachable``, ``ignored_reachable``, ``honoured_unreachable`` or
    ``ignored_unreachable`` (S1-L)."""
    return f"{'honoured' if css_limits_honoured else 'ignored'}_{'reachable' if layout_sizing_reachable else 'unreachable'}"


def width_key_status(
    *,
    css_limits_honoured: bool,
    layout_sizing_reachable: bool,
    css_limits_refit: bool,
    restore_layout_keeps_iframe: bool = True,
) -> dict[str, str]:
    """``{width-key family: "asserted" | "recorded-only"}`` per the D6 table (AC-36).

    * honoured/reachable and ignored/reachable: every width key asserted;
    * honoured/unreachable: the 1280-1599 keys asserted (CSS), the >= 1600 keys asserted only if ``css_limits_refit``;
    * S1-L (ignored/unreachable): every width key recorded-only;
    * ``restore_layout_keeps_iframe`` false: the open-time keys and ``fit_after_tier_change`` keep their case status;
      the drag-clamp keys and ``resize_within_wide`` take the ``unreachable`` row's status for the same CSS column
      (CSS ignored: recorded-only; CSS honoured: the 1280-1599 drag is CSS, ``resize_within_wide`` is inline px and
      asserted only if ``css_limits_refit``).

    The drawer keys, the height keys, ``nb_content_width`` and ``iframe_reloads_during_resize`` are asserted in every
    case and are not families here."""

    def base(unreachable: bool) -> dict[str, str]:
        if not unreachable:
            return {c: ASSERTED for c in WIDTH_CATEGORIES}
        medium = ASSERTED if css_limits_honoured else RECORDED_ONLY
        wide = ASSERTED if (css_limits_honoured and css_limits_refit) else RECORDED_ONLY
        return {c: (wide if c in _WIDE_CATEGORIES else medium) for c in WIDTH_CATEGORIES}

    status = base(not layout_sizing_reachable)
    if not restore_layout_keeps_iframe:
        unreachable = base(True)
        status["drag_clamp_1280_1599"] = unreachable["drag_clamp_1280_1599"]
        status["resize_within_wide"] = unreachable["resize_within_wide"]
    return status


def ac39d_status(status: dict[str, str]) -> str:
    """AC-39(d): ``run`` where the >= 1600 width key is asserted, else ``skipped`` (and recorded as such)."""
    return "run" if status.get("open_width_ge_1600") == ASSERTED else "skipped"


SIZING_STATUS: dict[str, str] = width_key_status(**SIZING_RECORD)


def wide_panel_width_expected(main_width: float, nb_h_padding: float) -> float:
    """D6, >= 1600 px: ``panel_width = max(420, main_area_width - 960 - nb_h_padding)``."""
    return max(PANEL_MIN_PX, float(main_width) - NOTEBOOK_CAP_PX - float(nb_h_padding))


def wide_width_ok(panel_width: Any, main_width: Any, nb_h_padding: Any) -> bool:
    """The AC-36 >= 1600 predicate: ``panel_width`` equals the D6 formula within ±8 px. Missing or non-numeric
    measurements are a failure, never a pass."""
    if not (_num(panel_width) and _num(main_width) and _num(nb_h_padding)):
        return False
    return abs(float(panel_width) - wide_panel_width_expected(main_width, nb_h_padding)) <= WIDE_TOL_PX


def open_width_ok(width: Any) -> bool:
    """AC-36 at 1440x900 and 1280x800: ``panel_width`` is in [420, 480] after opening."""
    return _num(width) and PANEL_MIN_PX - CLAMP_TOL_PX <= width <= PANEL_MAX_PX + CLAMP_TOL_PX


def clamp_low_ok(width: Any) -> bool:
    """A real splitter drag to 300 px is clamped to 420."""
    return _num(width) and abs(width - PANEL_MIN_PX) <= CLAMP_TOL_PX


def clamp_high_ok(width: Any) -> bool:
    """A real splitter drag to 700 px is clamped to 480."""
    return _num(width) and abs(width - PANEL_MAX_PX) <= CLAMP_TOL_PX


# -- the dock units (D16 table) ---------------------------------------------------------------------------------

#: AC-36's nine ordered steps on ONE page, ONE kernel and ONE ``dock()`` (Revision 7, C7-5): every viewport change
#: is a ``page.setViewportSize`` on that page. Each entry is ``(step, the viewport it runs at)``; the viewport list
#: is hashed into K2's ``args`` input. ``fit`` runs 1440 -> 1600 -> 1440 and ends at 1440x900 again, and
#: ``resize_within_wide`` runs 1600 -> 1920 wide at the same height (no tier crossing). AC-36 gives no height for
#: that step: the height of the next one (1080) is applied only at ``wide_1920``.
K2_STEPS: tuple[tuple[str, tuple[int, int]], ...] = (
    ("drawer", (1152, 800)),
    ("dismiss_reopen", (1152, 800)),
    ("tier_up", (1440, 900)),
    ("medium_1440", (1440, 900)),
    ("fit", (1600, 900)),
    ("medium_1280", (1280, 800)),
    ("wide_1600", (1600, 900)),
    ("resize_within_wide", (1920, 900)),
    ("wide_1920", (1920, 1080)),
)
#: K2's width keys in step order, each with the D6 family that decides asserted vs recorded-only.
K2_WIDTH_KEYS: tuple[tuple[str, str], ...] = (
    ("open_width_1440", "open_width_1280_1599"),
    ("drag_clamp_low_1440", "drag_clamp_1280_1599"),
    ("drag_clamp_high_1440", "drag_clamp_1280_1599"),
    ("fit_after_tier_change_wide", "fit_after_tier_change_ge_1600"),
    ("fit_after_tier_change_medium", "fit_after_tier_change_1280_1599"),
    ("open_width_1280", "open_width_1280_1599"),
    ("drag_clamp_low_1280", "drag_clamp_1280_1599"),
    ("drag_clamp_high_1280", "drag_clamp_1280_1599"),
    ("panel_width_wide_1600", "open_width_ge_1600"),
    ("resize_within_wide", "resize_within_wide"),
    ("panel_width_wide_1920", "open_width_ge_1600"),
)
_K2_WIDTH_FAMILY = dict(K2_WIDTH_KEYS)
#: K2's listed keys in step order: a width key is listed only when its family is asserted; the rest are always listed.
_K2_ORDER: tuple[tuple[str, Any], ...] = (
    ("drawer_overlays", True),
    ("drawer_no_reflow", True),
    ("drawer_dismiss_reopen", True),
    ("tier_up_rehomes", True),
    ("open_width_1440", True),
    ("drag_clamp_low_1440", True),
    ("drag_clamp_high_1440", True),
    ("fit_after_tier_change_wide", True),
    ("fit_after_tier_change_medium", True),
    ("open_width_1280", True),
    ("drag_clamp_low_1280", True),
    ("drag_clamp_high_1280", True),
    ("viewer_height", AtLeast(VIEWER_MIN_HEIGHT_PX)),
    ("motion_slot_height", AtMost(MOTION_MAX_HEIGHT_PX)),
    ("nb_content_width_1600", AtMost(NOTEBOOK_CAP_PX)),
    ("panel_width_wide_1600", True),
    ("resize_within_wide", True),
    ("iframe_reloads_during_resize", 0),
    ("nb_content_width_1920", AtMost(NOTEBOOK_CAP_PX)),
    ("panel_width_wide_1920", True),
)


def k2_expected(status: dict[str, str]) -> tuple[tuple[str, Any], ...]:
    """K2's listed keys under a D6 sizing ``status`` (``width_key_status``): the drawer keys, the height keys,
    ``nb_content_width_*`` and ``iframe_reloads_during_resize`` in every case; a width key only where its family is
    ``asserted``. A recorded-only key is still measured and written to the result, but no listed key gates on it."""
    return tuple(
        (key, want) for key, want in _K2_ORDER if _K2_WIDTH_FAMILY.get(key) is None or status.get(_K2_WIDTH_FAMILY[key]) == ASSERTED
    )


#: AC-39(d)'s unit: it lists the >= 1600 width key, which the stock-split control must FAIL (the sensitivity run
#: passes iff it does), or, where that key is recorded-only (D6), ``skipped`` and says so.
ND_KEY = "panel_width_wide_1600"


def nd_expected(status: dict[str, str]) -> tuple[tuple[str, Any], ...]:
    return ((ND_KEY, True),) if ac39d_status(status) == "run" else (("skipped", True),)


_K1A_EXPECTED: tuple[tuple[str, Any], ...] = (
    # AC-34
    ("panel_is_split_right", True),
    ("viewer_resources", True),
    ("hello_backend", OneOf(("WebGL2", "WebGPU"))),
    ("canvas_nonblank", True),
    ("embed_hidden", True),
    ("pageerrors", []),
    # AC-35
    ("click_focuses", True),
    ("follow_focuses", True),
    ("follow_off_holds", True),
    ("follow_skips_null", True),
    ("preset_directions", True),
    ("follow_keeps_preset", True),
    # AC-37
    ("state_updates", True),
    ("stale_and_panel", True),
)
#: AC-38, in its fixed execution order (Revision 6, C6-2; Revision 7): this IS the order the keys run in.
K1B_ORDER = (
    "reconnect_after_reload",
    "preset_survives_reload",
    "drawer_reconnect",
    "redock_live",
    "stop_placeholder",
    "redock_reloads",
    "late_iframe",
    "many_reloads",
    "restart_placeholder",
)

DOCK_UNITS: tuple[HarnessUnit, ...] = (
    HarnessUnit("K1a", DOCK_CHECK, 10 * 60.0, _K1A_EXPECTED, acs=("AC-34", "AC-35", "AC-37"), viewports=((1440, 900),)),
    HarnessUnit("K1b", DOCK_CHECK, 14 * 60.0, tuple((k, True) for k in K1B_ORDER), acs=("AC-38",), viewports=((1440, 900),)),
    HarnessUnit(
        "K2", DOCK_CHECK, 15 * 60.0, k2_expected(SIZING_STATUS), acs=("AC-36",), viewports=tuple(v for _, v in K2_STEPS)
    ),
    HarnessUnit(
        "N-d", DOCK_CHECK, 6 * 60.0, nd_expected(SIZING_STATUS), acs=("AC-39",), viewports=((1600, 900),), in_aggregate=False
    ),
)
#: The dock units join the one D16 table (ids, check, budget, listed keys); ``run_dock_check`` judges the
#: aggregate over the ones that count.
UNIT_TABLE = (*UNIT_TABLE, *DOCK_UNITS)
UNIT_BY_ID = {u.id: u for u in UNIT_TABLE}
DOCK_AGGREGATE_UNITS: tuple[HarnessUnit, ...] = tuple(u for u in DOCK_UNITS if u.in_aggregate)


# -- K1a: pure key derivation (AC-34, AC-35, AC-37) ---------------------------------------------------------------

#: The page's camera presets, copied from ``static/renderer.js:117-121`` (AC-35: "copied into the harness"). A test
#: reads renderer.js and fails if this copy drifts.
VIEWS: dict[str, tuple[float, float, float]] = {
    "iso": (-0.7, -1.0, 0.85),
    "top": (0.0, -0.001, 1.0),
    "front": (0.0, -1.0, 0.12),
}
PRESET_DOT_MIN = 0.99
#: AC-34: more than 1% of the iframe viewport's pixels must differ from the page ground ``#EEF1F4``.
CANVAS_DIFF_MIN = 0.01
CANVAS_GROUND_RGB = (0xEE, 0xF1, 0xF4)
#: Per-channel tolerance for "differs from the ground": a screenshot round trip may shift the ground by a level
#: or two, which must not read as drawing.
CANVAS_CHANNEL_TOL = 6
#: A camera point that moved by more than this (mm) has moved; by at most this it has held.
CAMERA_EPS = 1e-3
EMBED_HIDDEN_SELECTORS = (".navbar", "#toolbar-left", "#stats-panel", "#sidepanel", "#toolbar")
DECK_RESOURCES_REQUIRED = ("assay", "source", "tips_300")
OPEN_STATES = ("open-waiting", "open-connected", "open-lost")


def _vec3(value: Any) -> tuple[float, float, float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 3 and all(_num(c) for c in value):
        return (float(value[0]), float(value[1]), float(value[2]))
    return None


def _dist(a: Any, b: Any) -> float | None:
    va, vb = _vec3(a), _vec3(b)
    if va is None or vb is None:
        return None
    return sum((x - y) ** 2 for x, y in zip(va, vb)) ** 0.5


def _moved(a: Any, b: Any) -> bool:
    d = _dist(a, b)
    return d is not None and d > CAMERA_EPS


def _held(a: Any, b: Any) -> bool:
    d = _dist(a, b)
    return d is not None and d <= CAMERA_EPS


def preset_ok(camera: Any, name: str) -> bool:
    """AC-35: ``normalize(camera.from - camera.at) . normalize(VIEWS[name]) > 0.99``. A missing, malformed or
    zero-length camera is a failure."""
    view = VIEWS.get(name)
    cam = camera if isinstance(camera, dict) else {}
    frm, at = _vec3(cam.get("from")), _vec3(cam.get("at"))
    if view is None or frm is None or at is None:
        return False
    d = tuple(f - a for f, a in zip(frm, at))
    dn = sum(c * c for c in d) ** 0.5
    vn = sum(c * c for c in view) ** 0.5
    if dn < 1e-9 or vn < 1e-9:
        return False
    return sum((x / dn) * (y / vn) for x, y in zip(d, view)) > PRESET_DOT_MIN


def canvas_fraction(canvas: Any) -> float | None:
    """``diff_pixels / total_pixels`` of a canvas measurement, or ``None`` if it has no pixels to divide by."""
    c = canvas if isinstance(canvas, dict) else {}
    diff, total = c.get("diff_pixels"), c.get("total_pixels")
    if not (_num(diff) and _num(total)) or total <= 0:
        return None
    return diff / total


def canvas_nonblank(canvas: Any) -> bool:
    """AC-34 ``canvas_nonblank``: the fraction of differing pixels is ABOVE 1%, and the instrument is valid: the same
    measurement read a blank synthetic ground image as 0 and a marked one (5% of pixels) as above 1%."""
    c = canvas if isinstance(canvas, dict) else {}
    frac = canvas_fraction(c)
    blank, marked = c.get("control_blank"), c.get("control_marked")
    return bool(
        frac is not None and frac > CANVAS_DIFF_MIN
        and _num(blank) and blank == 0
        and _num(marked) and marked > CANVAS_DIFF_MIN
    )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _is_str(value: Any) -> bool:
    return isinstance(value, str) and value != ""


def derive_k1a_keys(raw: Any) -> dict[str, Any]:
    """K1a's listed keys (``pageerrors`` is added by ``run_scenario``) from the raw page evidence (pure; tested with
    a positive control and a negative control per key, and on empty evidence, where every key fails).

    ``raw``: ``panel`` ``{state, home, panel_left, notebook_right}``; ``resources`` (``plrViewer.resources()``);
    ``hello`` (``viewer.clients_seen[-1]``, read from the kernel); ``canvas`` ``{diff_pixels, total_pixels,
    control_blank, control_marked}``; ``embed`` (computed ``display`` per selector in the iframe); ``click``,
    ``follow_on``, ``follow_off``, ``follow_null`` (footer and ``camera().at`` before and after one activation, with
    the Follow switch as read), ``presets`` (camera after Top, Front, Iso), ``follow_keeps``, ``state`` (``stateOf``
    before and after the aspirate) and ``stale`` (the notice text, its count, the panel state)."""
    r = _dict(raw)
    panel, click = _dict(r.get("panel")), _dict(r.get("click"))
    on, off, null = _dict(r.get("follow_on")), _dict(r.get("follow_off")), _dict(r.get("follow_null"))
    keeps, state, stale = _dict(r.get("follow_keeps")), _dict(r.get("state")), _dict(r.get("stale"))
    presets, embed = _dict(r.get("presets")), _dict(r.get("embed"))
    resources = r.get("resources")
    left, right = panel.get("panel_left"), panel.get("notebook_right")
    ledger = null.get("ledger_resources")
    notices = stale.get("changed_notices")

    keys: dict[str, Any] = {}
    keys["panel_is_split_right"] = bool(
        panel.get("state") == "open-connected" and panel.get("home") == "split"
        and _num(left) and _num(right) and left >= right - 1.0
    )
    keys["viewer_resources"] = bool(
        isinstance(resources, list) and all(n in resources for n in DECK_RESOURCES_REQUIRED)
    )
    keys["hello_backend"] = _dict(r.get("hello")).get("backend")
    keys["canvas_nonblank"] = canvas_nonblank(r.get("canvas"))
    keys["embed_hidden"] = all(embed.get(sel) == "none" for sel in EMBED_HIDDEN_SELECTORS)
    keys["click_focuses"] = bool(
        _is_str(click.get("footer_before")) and click.get("footer_before") != "source"
        and click.get("footer_after") == "source" and _moved(click.get("at_before"), click.get("at_after"))
    )
    keys["follow_focuses"] = bool(
        on.get("enabled") is True and on.get("focused") == "assay" and on.get("footer") == "assay"
        and _moved(on.get("at_before"), on.get("at_after"))
    )
    keys["follow_off_holds"] = bool(
        off.get("enabled") is False and _is_str(off.get("footer_before"))
        and off.get("footer_before") == off.get("footer_after")
        and _held(off.get("at_before"), off.get("at_after"))
    )
    keys["follow_skips_null"] = bool(
        null.get("enabled") is True and isinstance(ledger, list) and len(ledger) >= 1 and all(n is None for n in ledger)
        and _is_str(null.get("footer_before")) and null.get("footer_before") == null.get("footer_after")
        and _held(null.get("at_before"), null.get("at_after"))
    )
    keys["preset_directions"] = all(preset_ok(presets.get(n), n) for n in ("top", "front", "iso"))
    keys["follow_keeps_preset"] = bool(
        keeps.get("pressed") == "top" and preset_ok(keeps.get("camera"), "top")
        and _is_str(keeps.get("footer_before")) and _is_str(keeps.get("footer_after"))
        and keeps.get("footer_before") != keeps.get("footer_after")
    )
    keys["state_updates"] = bool(
        _is_str(state.get("well")) and _is_str(state.get("before")) and _is_str(state.get("after"))
        and state.get("before") != state.get("after")
    )
    keys["stale_and_panel"] = bool(
        _num(notices) and notices >= 1 and isinstance(stale.get("notice_text"), str)
        and "deck panel" in stale["notice_text"]
        and _is_str(stale.get("panel_state")) and stale.get("panel_state") != "closed"
    )
    return keys


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
            "Assert AC-1/AC-2 zero-action auto-setup (spec 260914_first-run-auto-setup.md "
            "section 8.3): a first cell that neither imports nor calls praxis_boot.setup() "
            "itself still gets a ready kernel, `praxis_boot.gate_waited is True`, and "
            "AC-1's playground names (LiquidHandler/STAR) resolve with no import. Always "
            "holds the async pylabrobot wheel fetch for 15s so the wait is deterministic. "
            "--notebook-check cannot cover this: it runs welcome.ipynb, a saved notebook, "
            "not a first-ever cell dispatched at kernel idle."
        ),
    )
    p.add_argument(
        "--autosetup-fault-check",
        action="store_true",
        help=(
            "AC-3/AC-5 fault-injection gate (spec section 8.3): inject a --fault at the "
            "harness's static server, then assert a harness-created blank notebook's "
            "first two cells are blocked with a PraxisAutoSetupError naming the fault "
            "(and their own side-effect sentinel does NOT run), a third recovery cell "
            "(`await praxis_boot.setup()`, fault count spent) succeeds, and a fourth "
            "cell reproduces AC-1. Requires at least one --fault."
        ),
    )
    p.add_argument(
        "--restart-check",
        action="store_true",
        help=(
            "AC-7 gate (spec section 8.3): after AC-1 passes, restart the kernel via "
            "session.kernel.restart() (no command dispatch, so no Select Kernel dialog) "
            "and assert praxis_boot.kernel_nonce changed, state is 'ready' again, and "
            "Serial is still the browser shim."
        ),
    )
    p.add_argument(
        "--fault",
        action="append",
        default=[],
        metavar="KIND:SUFFIX[:SECONDS]",
        help=(
            "--autosetup-fault-check only (repeatable). `404:<path-suffix>`, "
            "`tamper:<path-suffix>`, or `delay:<path-suffix>:<seconds>`. Matched against "
            "the served request's parsed, unquoted URL path with str.endswith. Example: "
            "--fault 404:bootstrap/stages.py or --fault tamper:bootstrap/stages.py."
        ),
    )
    p.add_argument(
        "--fault-count",
        type=int,
        default=1,
        help=(
            "How many of the FIRST matching requests each --fault actually faults; "
            "requests after that are served normally, which is what makes the "
            "post-fault retry cell succeed. Default: 1."
        ),
    )
    p.add_argument(
        "--persistence-check",
        action="store_true",
        help=(
            "T8a+T8b browser gate (spec 260922_repl-persistence-ladder.md): scenarios "
            "S1-S10 (AC-8 through AC-14, AC-17) -- the indicator/L1 tier on a fresh "
            "lab/ load, real-click gesture-synchrony proof for persist()/"
            "showDirectoryPicker()/requestPermission(), the non-FSA degraded panel, "
            "IndexedDB storage hygiene, L2 folder mirroring and rehydration by "
            "content, differs-on-disk exclusion, paused/reload/reconnect with a "
            "persisted pending set, restore from folder, the first-save disclosure "
            "gate (including an untitled-file rename), and native JupyterLab "
            "Download/Upload round-tripping by content. Needs a freshly built "
            "web-repl/dist (see --serve-dir) and --base-path /praxis/ to match CI. "
            "Exits nonzero if any scenario key fails; see the printed JSON's "
            "'failures' list."
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
    p.add_argument(
        "--display-check",
        action="store_true",
        help=(
            "Notebook display gates (epic 260929_notebook-display-design, D16). With "
            "--scenario <id> runs exactly ONE unit (D1, D1-dark, D2, D3, D4) in this process, "
            "bounded by its own watchdog; with no --scenario it is the driver: one "
            "unit_runner.run_unit subprocess per unit, resuming over stamp-matched units, "
            "writing <out-dir>/result.json. Needs a fresh web-repl/dist."
        ),
    )
    p.add_argument(
        "--scenario",
        default=None,
        metavar="ID",
        help="--display-check only. Run exactly this unit (one process, one browser). Default: the driver.",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help=(
            "Directory for result.<id>.json, stamps, timeout markers and result.json. Default "
            "outputs/repl_smoke/<check>/ (gitignored). REQUIRED (else exit 2) with a "
            "non-default --serve-dir or any --neg, so a negative or a copied dist can never "
            "overwrite the default results."
        ),
    )
    p.add_argument(
        "--fresh",
        action="store_true",
        help="--display-check driver only. Ignore every stamp and recompute every unit.",
    )
    p.add_argument(
        "--aggregate-only",
        action="store_true",
        help=(
            "--display-check only. Recompute nothing, start no unit subprocess and NEVER delete: "
            "judge the stamps on disk against the current inputs and write <out-dir>/result.json. "
            "Give it the same hashed arguments (--base-path, and --serve-dir/--out-dir when "
            "non-default) as the scenario runs. CI's final step."
        ),
    )
    p.add_argument(
        "--neg",
        action="append",
        default=[],
        choices=["drop-query"],
        help=(
            "Harness-only negative flag (AC-39(e), --dock-check K1b; sprint C). Hashed into the "
            "unit's args input; requires --out-dir. --display-check has none and rejects it."
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
        and not args.autosetup_fault_check
        and not args.restart_check
        and not args.persistence_check
        and not args.display_check
        and not args.expect_fail
    ):
        LOG.error(
            "nothing to do: pass --probe, --viz-check, --notebook-check, "
            "--completion-check, --typeahead-check, --fresh-boot-check, "
            "--autosetup-fault-check, --restart-check, --persistence-check, "
            "--display-check, and/or --expect-fail"
        )
        return 2

    if args.display_check:
        return run_display_check(args)

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
        except Exception as e:
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

        if result.get("forbidden_bootstrap_hits"):
            LOG.error(
                "notebook-check FAILED (AC-10, static check): %s's code cells contain "
                "forbidden bootstrap call(s) %s -- this would make the run below pass "
                "even with auto-setup entirely broken (test-design trap 1)",
                result["notebook"], result["forbidden_bootstrap_hits"],
            )
            return 1
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
            "output(s).", result["notebook"], result["cell_count"], len(result["expected"]),
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

        probe_code = build_fresh_boot_probe_code()

        # Test-design trap 1 (spec section 8.4): a probe that sets up the kernel
        # itself would pass even with auto-setup entirely broken. Refuse to run
        # rather than silently proving nothing.
        forbidden_hit = find_forbidden_bootstrap_call(probe_code)
        if forbidden_hit is not None:
            LOG.error(
                "fresh-boot-check refused to run: its own probe source contains "
                "forbidden bootstrap call %r -- this is a harness bug, not a "
                "product failure", forbidden_hit,
            )
            return 2
        if probe_imports_playground_names(probe_code):
            LOG.error(
                "fresh-boot-check refused to run: its own probe source imports "
                "LiquidHandler/pylabrobot[.legacy].liquid_handling, which would make "
                "playground_names_ok pass vacuously (T3b)"
            )
            return 2

        # R2-1: ALWAYS delay the async micropip wheel fetch so AC-2's wait is
        # deterministic, not timing luck. Read the filename from the served
        # manifest -- never hardcode it, the +g<sha> segment changes per build.
        try:
            wheel_filename = read_wheel_filename(serve_dir, "pylabrobot")
        except RuntimeError as e:
            LOG.error("fresh-boot-check could not resolve the pylabrobot wheel: %s", e)
            return 2
        wheel_delay_fault = Fault(
            kind="delay",
            suffix=f"assets/wheels/{wheel_filename}",
            delay_s=FRESH_BOOT_WHEEL_DELAY_S,
            max_hits=1,
        )
        LOG.info(
            "fresh-boot-check: always-on delay fault on assets/wheels/%s (%ss)",
            wheel_filename, FRESH_BOOT_WHEEL_DELAY_S,
        )

        # Keep well inside the cell timeout (the delay raises how long boot
        # takes; never shrink the assertion to fit a smaller timeout instead).
        gate_timeout_s = max(args.timeout, FRESH_BOOT_WHEEL_DELAY_S + 60.0)

        try:
            result = run_probe(
                serve_dir=serve_dir,
                base_path=args.base_path,
                coi=args.coi,
                chrome_path=str(chrome_path),
                timeout_s=gate_timeout_s,
                expect_praxis_sha=None,
                entry=args.entry,
                offline=args.offline,
                code_override=probe_code,
                faults=[wheel_delay_fault],
            )
        except Exception as e:
            LOG.error("fresh-boot-check run failed: %s: %s", type(e).__name__, e)
            return 2

        if args.out:
            args.out.write_text(json.dumps(result, indent=2) + "\n")
            LOG.info("wrote result to %s", args.out)

        expected_root = _normalize_base_path(args.base_path)
        delay_hits = wheel_delay_fault.hits
        measured_gate_wait_s = result.get("_meta", {}).get("probe_wall_s")
        LOG.info(
            "fresh boot: cwd=%s import_praxis_boot=%s state=%s autostart_origin=%s "
            "derived_host_root=%s (expected %s)",
            result.get("cwd"),
            result.get("import_praxis_boot"),
            result.get("state"),
            result.get("autostart_origin"),
            result.get("derived_host_root"),
            expected_root,
        )
        LOG.info(
            "fresh boot: plr_after=%s serial_is_shim=%s playground_names_ok=%s "
            "gate_waited=%s wheel-delay hits=%d/%d measured probe wall=%.2fs",
            result.get("plr_after"),
            result.get("serial_is_shim"),
            result.get("playground_names_ok"),
            result.get("gate_waited"),
            delay_hits, wheel_delay_fault.max_hits,
            measured_gate_wait_s if measured_gate_wait_s is not None else -1.0,
        )

        failures: list[str] = []
        if delay_hits < 1:
            failures.append(
                f"the always-on wheel-delay fault never fired (hits={delay_hits}); "
                "the wait this gate depends on was NOT deterministic (test-design "
                "trap 5)."
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
        if result.get("state") != "ready":
            failures.append(
                f"praxis_boot.state == {result.get('state')!r}, expected 'ready' "
                f"(failure={result.get('failure')})"
            )
        if result.get("autostart_origin") != "PYTHONSTARTUP":
            failures.append(
                f"praxis_boot.autostart_origin == {result.get('autostart_origin')!r}, "
                "expected 'PYTHONSTARTUP' -- auto-setup did not start from the "
                "startup file"
            )
        plr_after = result.get("plr_after") or ""
        plr_prefix = expected_plr_version_prefix()
        if not plr_after.startswith(plr_prefix):
            failures.append(
                f"pylabrobot version {plr_after!r} does not start with {plr_prefix!r}"
            )
        if result.get("derived_host_root") != expected_root:
            failures.append(
                f"praxis_boot.host_root {result.get('derived_host_root')!r} != "
                f"expected {expected_root!r}. A wrong root 404s the loader fetch."
            )
        if result.get("serial_is_shim") is not True:
            failures.append(
                "pylabrobot's Serial is NOT the browser shim after auto-setup, so "
                "device I/O would silently use desktop pyserial."
            )
        if result.get("playground_names_ok") is not True:
            failures.append(
                "AC-1's playground-names clause failed: LiquidHandler/STAR are not "
                f"resolvable with no import ({result.get('playground_names_error')})"
            )
        if result.get("gate_waited") is not True:
            failures.append(
                "praxis_boot.gate_waited is not True -- this run does not prove "
                "AC-2's wait: the probe cell never observed state=='running' on "
                "entry, so either setup finished before the cell was dispatched "
                "(the always-on wheel delay should prevent this) or the gate "
                "itself is not wiring gate_waited correctly."
            )

        if failures:
            for f in failures:
                LOG.error("FAIL: %s", f)
            return 1
        LOG.info(
            "fresh-boot-check PASSED: a fresh kernel auto-set-up PyLabRobot %s with "
            "browser shims bound and playground names resolvable, with NO setup "
            "code typed or run by this probe (gate_waited=%s, wheel-delay hits=%d, "
            "measured wait=%.2fs)",
            result.get("plr_after"), result.get("gate_waited"), delay_hits,
            measured_gate_wait_s if measured_gate_wait_s is not None else -1.0,
        )
        return 0

    if args.autosetup_fault_check:
        serve_dir = args.serve_dir.resolve()
        if not serve_dir.is_dir():
            LOG.error("--serve-dir does not exist or is not a directory: %s", serve_dir)
            return 2
        if not args.fault:
            LOG.error(
                "--autosetup-fault-check requires at least one --fault "
                "(e.g. --fault 404:bootstrap/stages.py)"
            )
            return 2
        try:
            faults = [parse_fault(spec, max_hits=args.fault_count) for spec in args.fault]
        except ValueError as e:
            LOG.error("bad --fault: %s", e)
            return 2

        try:
            result = run_autosetup_fault_check(
                serve_dir=serve_dir,
                base_path=args.base_path,
                chrome_path=str(chrome_path),
                timeout_s=args.timeout,
                faults=faults,
                offline=args.offline,
            )
        except Exception as e:
            LOG.error("autosetup-fault-check run failed: %s: %s", type(e).__name__, e)
            return 2

        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2, sort_keys=True))
            LOG.info("wrote result to %s", args.out)

        cells = result.get("cell_results") or []
        failures: list[str] = []
        if len(cells) < 4:
            failures.append(f"expected 4 cell results, got {len(cells)}")
        else:
            expected_reason = None
            for f in faults:
                expected_reason = FAULT_REASON_NEEDLE.get(f.kind)
                if expected_reason:
                    break

            for idx in (0, 1):
                c = cells[idx]
                out = c.get("output_text") or ""
                if "PraxisAutoSetupError" not in out:
                    failures.append(
                        f"cell {idx + 1}: expected 'PraxisAutoSetupError' in output, "
                        f"got {out[:300]!r}"
                    )
                if expected_reason and expected_reason not in out:
                    failures.append(
                        f"cell {idx + 1}: expected fault reason {expected_reason!r} in "
                        f"output, got {out[:300]!r}"
                    )
                if AUTOSETUP_FAULT_SIDE_EFFECT_NEEDLE in out:
                    failures.append(
                        f"cell {idx + 1}: its own side-effect sentinel "
                        f"{AUTOSETUP_FAULT_SIDE_EFFECT_NEEDLE!r} appeared in output -- "
                        "the cell's code RAN instead of being blocked"
                    )
                if not c.get("has_error_output"):
                    failures.append(f"cell {idx + 1}: expected an error output, found none")

            c3 = cells[2]
            out3 = c3.get("output_text") or ""
            if c3.get("has_error_output"):
                failures.append(
                    f"cell 3 (retry, fault count spent): expected no error, got {out3[:300]!r}"
                )
            if not AUTOSETUP_SUCCESS_LINE_PATTERN.search(out3):
                failures.append(
                    f"cell 3 (retry): expected praxis_boot.setup()'s success line "
                    f"'PyLabRobot <version> ready (site root <root>); Serial is the browser shim', "
                    f"got {out3[:300]!r}"
                )
            # Record gate_waited for AC-2 measurement (not a pass/fail condition):
            # scan every line for a JSON object carrying it, last one wins.
            gate_waited = None
            for line in out3.splitlines():
                try:
                    data = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                if isinstance(data, dict) and "gate_waited" in data:
                    gate_waited = data["gate_waited"]
            result["gate_waited"] = gate_waited

            c4 = cells[3]
            out4 = c4.get("output_text") or ""
            if c4.get("has_error_output") or "True" not in out4 or "False" in out4:
                failures.append(f"cell 4 (AC-1 probe): expected bare 'True', got {out4[:300]!r}")

            # Check that all faults actually fired (spec trap 5)
            for i, f in enumerate(faults):
                if f.hits < 1:
                    failures.append(
                        f"fault {i + 1} ({f.kind}:{f.suffix}): never fired (hits={f.hits}); "
                        "the gate's blocked-cell assertions would be unproven (test-design trap 5)."
                    )

        if result.get("pageerrors"):
            failures.append(f"pageerror(s): {result['pageerrors']}")

        LOG.info(
            "autosetup-fault-check: faults=%s cells=%s",
            result.get("faults"),
            [
                {"has_error_output": c.get("has_error_output"), "dispatched": c.get("dispatched")}
                for c in cells
            ],
        )

        if failures:
            for f in failures:
                LOG.error("FAIL: %s", f)
            return 1
        LOG.info(
            "autosetup-fault-check PASSED: every cell was blocked while the fault was "
            "live, the retry succeeded once it was spent, and AC-1 held afterward"
        )
        return 0

    if args.restart_check:
        serve_dir = args.serve_dir.resolve()
        if not serve_dir.is_dir():
            LOG.error("--serve-dir does not exist or is not a directory: %s", serve_dir)
            return 2
        try:
            result = run_restart_check(
                serve_dir=serve_dir,
                base_path=args.base_path,
                chrome_path=str(chrome_path),
                timeout_s=args.timeout,
                offline=args.offline,
            )
        except Exception as e:
            LOG.error("restart-check run failed: %s: %s", type(e).__name__, e)
            return 2

        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2, sort_keys=True))
            LOG.info("wrote result to %s", args.out)

        before = result.get("before") or {}
        after = result.get("after") or {}
        LOG.info("restart-check: nonce before=%s after=%s", before.get("kernel_nonce"), after.get("kernel_nonce"))

        failures: list[str] = []
        if before.get("state") != "ready" or before.get("serial_is_shim") is not True:
            failures.append(
                f"AC-1 did not hold BEFORE the restart (state={before.get('state')!r}, "
                f"serial_is_shim={before.get('serial_is_shim')!r}); this gate only "
                "proves anything once AC-1 has already passed"
            )
        if after.get("state") != "ready":
            failures.append(f"praxis_boot.state == {after.get('state')!r} after restart, expected 'ready'")
        if after.get("serial_is_shim") is not True:
            failures.append("Serial is NOT the browser shim after restart")
        if not before.get("kernel_nonce") or not after.get("kernel_nonce"):
            failures.append(
                f"could not read kernel_nonce on both sides (before={before.get('kernel_nonce')!r}, "
                f"after={after.get('kernel_nonce')!r})"
            )
        elif before.get("kernel_nonce") == after.get("kernel_nonce"):
            failures.append(
                f"kernel_nonce unchanged ({before.get('kernel_nonce')!r}) across the restart -- "
                "this did not actually get a new interpreter (test-design trap 4)"
            )
        if result.get("pageerrors"):
            failures.append(f"pageerror(s): {result['pageerrors']}")

        if failures:
            for f in failures:
                LOG.error("FAIL: %s", f)
            return 1
        LOG.info(
            "restart-check PASSED: kernel_nonce changed (%s -> %s), AC-1 held again",
            before.get("kernel_nonce"), after.get("kernel_nonce"),
        )
        return 0

    if args.persistence_check:
        serve_dir = args.serve_dir.resolve()
        if not serve_dir.is_dir():
            LOG.error("--serve-dir does not exist or is not a directory: %s", serve_dir)
            return 2
        try:
            result = run_persistence_check(
                serve_dir=serve_dir,
                base_path=args.base_path,
                chrome_path=str(chrome_path),
                timeout_s=args.timeout,
                offline=args.offline,
            )
        except Exception as e:
            LOG.error("persistence-check run failed: %s: %s", type(e).__name__, e)
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

        LOG.info(
            "persistence-check: indicator_present_before_save=%s initial_tier=%s "
            "repl_entry_has_chip=%s picker_calls=%s tier_after_persist=%s "
            "nofsa_l2_controls=%s nofsa_modal_choose_absent=%s "
            "mirror_after_choose_matches=%s tier_on_prompt=%s "
            "gate_never_opened_s6=%s modal_open=%s gate_after_rename=%s "
            "download_matches=%s upload_matches=%s",
            result.get("indicator_present_before_save"),
            result.get("initial_tier"),
            result.get("repl_entry_has_chip"),
            result.get("picker_calls"),
            result.get("tier_after_persist"),
            result.get("nofsa_l2_controls"),
            result.get("nofsa_modal_choose_absent"),
            result.get("mirror_after_choose_matches"),
            result.get("tier_on_prompt"),
            result.get("gate_never_opened_s6"),
            result.get("modal_open"),
            result.get("gate_after_rename"),
            result.get("download_matches"),
            result.get("upload_matches"),
        )
        if not result["passed"]:
            for f in result["failures"]:
                LOG.error("FAIL: %s", f)
            return 1
        LOG.info(
            "persistence-check PASSED (S1-S10: AC-8 through AC-14, AC-17)"
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
        except Exception as e:
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
        except Exception as e:
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
