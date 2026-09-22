"""Manifest-driven fetch + D2 integrity verification for the browser bootstrap.

Pure CPython -- no ``import js`` anywhere in this module (ADR
``.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md``
Sec 2.1: "``transport.py``: ``_sync_fetch -> (ok, status, text)``; no
``import js``. That constraint exists so the transport is unit-testable in
CPython."). Every function that needs a browser object (an XHR-like fetcher,
a BroadcastChannel-like message pump) takes it as an injected callable or
object instead of importing ``js`` to construct one itself -- that is what
makes every function in this module exercisable from a plain CPython pytest
run with fake stand-ins, never a real browser.

This module owns:

1. ``_sync_fetch`` -- the low-level synchronous fetch primitive, browser
   object injected.
2. ``fetch_manifest`` -- fetch + parse ``manifest.json``, fail closed
   (``PraxisUnavailableError``) on a missing file or malformed JSON.
3. ``fetch_sources`` -- THE fetch loop this task exists to fix. Reads the
   manifest's ``"sources"`` array (built dynamically by
   ``build_manifest.py``'s ``collect_sources()`` from everything under
   ``overlay/assets/{shims,python}``) instead of iterating a hardcoded list
   of URL literals, verifies each fetched file's sha256 against its manifest
   entry (D2), and writes it into the Pyodide VFS. This is what brings the
   old file's seven hardcoded fetch literals (four shims, ``web_bridge.py``,
   ``praxis/__init__.py``, ``praxis/interactive.py`` -- ADR Sec 2.3) under
   the manifest seam, and it does so for whatever the manifest lists, not
   just those seven -- ``praxis/viz/*``, ``experimental/*``, and the shims'
   own ``__init__.py`` all ride the same loop with no further code.
4. ``shell_ping`` -- the bootstrap-side half of the D1 ``praxis:shell-ping``
   / ``praxis:shell-pong`` handshake (ADR Sec 2.3; wire protocol defined in
   ``web-repl/shell/praxis-shell.js``). Takes an already-bound
   ``register_handler`` callable and a ``post_fn`` callable rather than
   constructing or touching a ``BroadcastChannel`` itself, so it is testable
   against a bare Python stand-in object.

``stages.py`` owns the error taxonomy (``PraxisBootError`` /
``PraxisDriftError`` / ``PraxisUnavailableError``) -- this module imports it
rather than redefining anything, per ADR Sec 4.3 ("the taxonomy has exactly
one home").
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os

from stages import PraxisDriftError, PraxisUnavailableError

__all__ = [
    "MANIFEST_REL_PATH",
    "SHIMS_PREFIX",
    "PYTHON_PREFIX",
    "FetchResult",
    "sync_fetch",
    "fetch_manifest",
    "dest_for_source",
    "fetch_sources",
    "shell_ping",
]

# manifest.json's own location, relative to host_root -- build_manifest.py
# writes it to <web-repl-root>/overlay/assets/wheels/manifest.json, and that
# tree is copied verbatim into dist/ (ADR Sec 2.1).
MANIFEST_REL_PATH = "assets/wheels/manifest.json"

# The two ``overlay/assets/`` subdirectories build_manifest.py's
# ``collect_sources()`` walks (its own ``SOURCE_SUBDIRS``). A manifest
# "sources" entry's ``path`` always starts with one of these.
SHIMS_PREFIX = "assets/shims/"
PYTHON_PREFIX = "assets/python/"

FetchResult = tuple  # (ok: bool, status: int, text: str) -- documented, not enforced


# ---------------------------------------------------------------------------
# 1. sync_fetch -- the injected-object primitive.
# ---------------------------------------------------------------------------


def sync_fetch(url: str, xhr_new) -> tuple:
    """Fetch *url* synchronously via an XHR-like object built by ``xhr_new()``.

    ``xhr_new`` is a zero-arg callable returning an object with ``.open``,
    ``.send``, ``.status`` and ``.responseText`` -- in the browser this is
    ``lambda: js.XMLHttpRequest.new()``; in tests it is a fake with the same
    shape. This function never imports ``js`` itself, which is what makes it
    (and everything built on it below) importable and callable from plain
    CPython.

    Returns ``(ok, status, text)`` -- deliberately NOT ``text or None`` on a
    200: the old bootstrap's ``if xhr.status == 200: return text; return
    None`` made a 200-with-empty-body indistinguishable from a real failure
    (standalone spec Sec "(4) _sync_fetch" -- this was a live, demonstrated
    false-negative). ``ok`` is the only failure signal; ``text`` is ``""``
    on failure, never ``None``, so callers never need a ``None``-check.
    """
    xhr = xhr_new()
    xhr.open("GET", url, False)  # False = synchronous (required in a Worker)
    xhr.send(None)
    status = int(xhr.status)
    ok = status == 200
    text = str(xhr.responseText) if ok else ""
    return ok, status, text


# ---------------------------------------------------------------------------
# 2. fetch_manifest -- D2's own delivery, fail closed.
# ---------------------------------------------------------------------------


def fetch_manifest(host_root: str, xhr_new) -> dict:
    """Fetch and parse ``manifest.json``. Raises ``PraxisUnavailableError``
    (never returns a sentinel) on an HTTP failure or invalid JSON, and on a
    manifest missing any of its three mandated top-level keys -- this is the
    "manifest-404 ... occurs before any wheel is importable" case the task
    brief names: by the time this function can be called, ``stages`` (and
    therefore ``PraxisUnavailableError``) is already imported, because the
    loader imports ``stages``/``transport`` themselves before attempting
    this fetch (see ``praxis_bootstrap.py``'s own module docstring).
    """
    url = f"{host_root}{MANIFEST_REL_PATH}"
    ok, status, text = sync_fetch(url, xhr_new)
    if not ok:
        raise PraxisUnavailableError(
            f"manifest fetch failed: GET {url} -> HTTP {status} "
            "(no manifest means no wheel and no first-party source can be "
            "verified or installed -- this is the earliest possible "
            "fail-closed point)."
        )
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PraxisUnavailableError(
            f"manifest at {url} is not valid JSON: {exc}"
        ) from exc
    missing = [k for k in ("praxis_git_sha", "wheels", "sources") if k not in manifest]
    if missing:
        raise PraxisUnavailableError(
            f"manifest at {url} is missing required key(s) {missing!r} -- "
            f"got keys {sorted(manifest.keys())!r}"
        )
    return manifest


# ---------------------------------------------------------------------------
# 3. fetch_sources -- THE manifest-driven fetch loop (replaces the seven
#    hardcoded literals; ADR Sec 2.3 D2).
# ---------------------------------------------------------------------------


def dest_for_source(rel_path: str) -> str:
    """Map a manifest ``"sources"`` entry's ``path`` to its VFS write
    destination / import path.

    Shims flatten to the VFS root (``assets/shims/web_serial_shim.py`` ->
    ``web_serial_shim.py``) because ``stages.import_shim_class()`` imports
    each one by bare module name (its own docstring's worked example:
    ``import_module("web_serial_shim")``) -- this is the R-ID contract
    (ADR Sec 2.2), not a naming preference.

    Everything under ``assets/python/`` keeps its structure minus that one
    prefix, so ``assets/python/praxis/interactive.py`` ->
    ``praxis/interactive.py`` and ``import praxis.interactive`` resolves as
    a regular package (ADR Sec 2.4 pins ``praxis/__init__.py`` as a regular,
    non-namespace package).

    Raises ``PraxisUnavailableError`` on a path outside both prefixes --
    build_manifest.py's ``collect_sources()`` can only ever produce paths
    under ``SOURCE_SUBDIRS = ("shims", "python")``, so this is a "the
    manifest shape changed under us" guard, not a reachable case today.

    Also raises ``PraxisUnavailableError``, fail-closed, if the computed
    destination is a bare ``__init__.py`` landing at the VFS root (``dest_root``
    itself, e.g. ``assets/shims/__init__.py`` -> ``__init__.py``). That would
    silently turn the bootstrap's own working directory into a Python
    package -- the same directory ``stages.py``, ``transport.py`` and every
    fetched shim/source file are written into -- which can change import
    resolution in ways that are very hard to debug later (F-VFS). This is a
    belt-and-suspenders check: ``build_manifest.py``'s ``collect_sources()``
    is the primary fix (it never emits ``assets/shims/__init__.py`` as a
    source at all, because shims are imported as bare top-level modules --
    ``stages.import_shim_class()`` -- never through a ``shims`` package), but
    this function fails loud rather than silently writing a root-level
    package marker if that invariant is ever violated upstream.
    """
    if rel_path.startswith(SHIMS_PREFIX):
        dest = rel_path[len(SHIMS_PREFIX):]
    elif rel_path.startswith(PYTHON_PREFIX):
        dest = rel_path[len(PYTHON_PREFIX):]
    else:
        raise PraxisUnavailableError(
            f"manifest source path {rel_path!r} is outside {SHIMS_PREFIX!r} and "
            f"{PYTHON_PREFIX!r} -- cannot determine its VFS destination."
        )
    if dest == "__init__.py":
        raise PraxisUnavailableError(
            f"manifest source path {rel_path!r} would flatten to a bare "
            "__init__.py at the VFS root -- refusing to write it. This would "
            "silently turn the bootstrap's own working directory into a "
            "Python package. If this fires, the fix belongs in "
            "build_manifest.py's collect_sources() (exclude the offending "
            "path from the manifest), not here."
        )
    return dest


def fetch_sources(manifest: dict, host_root: str, xhr_new, dest_root: str = ".") -> list:
    """Fetch every entry in ``manifest["sources"]``, verify its sha256
    against the manifest (D2), and write it into the VFS under *dest_root*.

    This is THE fetch loop the task brief targets: it replaces the old
    file's seven hardcoded URL literals with an iteration driven entirely by
    what ``manifest.json`` lists -- currently the four shims
    (web_ftdi_shim.py, web_hid_shim.py, web_serial_shim.py, web_usb_shim.py),
    ``praxis/__init__.py``, ``praxis/interactive.py``, and ``web_bridge.py``.
    Note: ``assets/shims/__init__.py`` is deliberately excluded from the
    manifest (see ``build_manifest.py:207--220``); if fetched, ``dest_for_source()``
    would flatten it to a bare ``__init__.py`` at the VFS root, silently
    converting the bootstrap's own directory into a Python package (F-VFS hazard).
    The ``experimental/`` directory is reserved for Phase 4 and will be covered
    once Phase 4 populates it. Zero further code is needed when that set grows.

    Fail-closed on both axes: an HTTP failure raises
    ``PraxisUnavailableError``; a sha256 mismatch raises
    ``PraxisDriftError`` naming the path and both hashes. Returns the list
    of destination paths written, in manifest order.
    """
    written = []
    for entry in manifest["sources"]:
        rel_path = entry["path"]
        expected_sha = entry["sha256"]
        url = f"{host_root}{rel_path}"
        ok, status, text = sync_fetch(url, xhr_new)
        if not ok:
            raise PraxisUnavailableError(
                f"source fetch failed: GET {url} -> HTTP {status}"
            )
        actual_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if actual_sha != expected_sha:
            raise PraxisDriftError(
                f"D2 source sha256 mismatch: {rel_path} "
                f"manifest={expected_sha} fetched={actual_sha}"
            )
        dest = os.path.join(dest_root, dest_for_source(rel_path))
        dirname = os.path.dirname(dest)
        if dirname and not os.path.isdir(dirname):
            os.makedirs(dirname, exist_ok=True)
        with open(dest, "w") as f:
            f.write(text)
        written.append(dest)
    return written


# ---------------------------------------------------------------------------
# 4. shell_ping -- D1's bootstrap-side handshake half.
# ---------------------------------------------------------------------------


async def shell_ping(
    register_handler, post_fn, timeout_s: float = 5.0, expected_sha: str | None = None
) -> str:
    """Ask the shell (``web-repl/shell/praxis-shell.js``) for its injected
    ``praxis_git_sha`` over the ``praxis:shell-ping`` / ``praxis:shell-pong``
    handshake on the ``praxis_repl`` BroadcastChannel (ADR Sec 2.3 D1).

    ``register_handler(callback)`` installs ``callback(data: dict)`` as the
    channel's incoming-message handler; ``post_fn(dict)`` sends a message on
    that same channel. The caller supplies both, already bound to the real
    channel and doing any JsProxy/``to_py`` conversion needed -- this
    function touches no ``BroadcastChannel`` or ``js`` object directly,
    which is what makes it callable from CPython with a bare fake channel
    (see ``web-repl/tests/test_praxis_bootstrap_loader.py``).

    Returns the pong's ``praxis_git_sha`` value. Raises
    ``PraxisUnavailableError`` if no pong arrives within *timeout_s* -- "a
    missing pong ... is the bootstrap's problem to time out on" per
    ``praxis-shell.js``'s own protocol comment.

    One ping can draw SEVERAL pongs: every same-origin tab's shell listens on
    the shared ``praxis_repl`` channel, so a still-open tab from an older
    deploy answers too, and may answer first (debt #1858). Pass
    *expected_sha* (the manifest's ``praxis_git_sha``) and a matching pong
    wins as soon as it arrives, whatever came before it. If the timeout
    elapses with pongs seen but none matching, the FIRST one seen is
    returned rather than raising, so the caller's
    ``stages.assert_praxis_git_sha`` still fails closed with its real
    drift diagnosis naming both shas. Without *expected_sha* the first pong
    wins, as before.
    """
    loop = asyncio.get_event_loop()
    fut = loop.create_future()
    seen: list = []

    def _on_message(data):
        if (
            isinstance(data, dict)
            and data.get("type") == "praxis:shell-pong"
            and not fut.done()
        ):
            sha = data.get("praxis_git_sha")
            seen.append(sha)
            if expected_sha is None or sha == expected_sha:
                fut.set_result(sha)

    register_handler(_on_message)
    post_fn({"type": "praxis:shell-ping"})
    try:
        return await asyncio.wait_for(fut, timeout=timeout_s)
    except asyncio.TimeoutError as exc:
        if seen:
            return seen[0]
        raise PraxisUnavailableError(
            f"D1 praxis:shell-ping timed out after {timeout_s}s waiting for "
            "praxis:shell-pong -- no shell present, or a shell that never "
            "answers (web-repl/shell/praxis-shell.js Sec 2.3)."
        ) from exc
