"""Boot-stage building blocks for praxis's browser-Python bootstrap.

Pure CPython -- no ``import js``, no fetching, no Pyodide-VFS writes (ADR
260817_repl-layout-and-delivery-mechanism.md SS2.1/SS3.1: this is one of the
two files that generalizes the one CPython-testability win the loader already
had). This module owns THREE things, per that ADR:

1. **The boot error taxonomy** (SS4.3) -- ``PraxisBootError``,
   ``PraxisDriftError``, ``PraxisUnavailableError``. This is their ONLY home.
   A prior design kept a second copy in ``errors.py`` with a
   ``sys.modules``-shadowing trick to avoid a two-class-object split; that
   design is DROPPED here, not reproduced, because with one home the risk it
   guarded against does not exist.

2. **``install_native_stubs()``** -- replaces the old ``_mock_native_deps()``
   MagicMock entirely with real ``types.ModuleType`` objects for the seven
   dotted names PyLabRobot's capability probes ``try: import X`` against.
   *That MagicMock was load-bearing*: PLR's ``HAS_SERIAL`` / ``USE_USB`` /
   ``USE_HID`` / ``HAS_PYLIBFTDI`` flags are module-scope
   ``try: import X / except ImportError: HAS_X = False`` booleans evaluated
   ONCE at import time -- a naive removal flips all four False silently.

3. **``apply()`` / ``verify_identity()``** -- the home of the single-class-
   object identity invariant (ADR SS2.2, "R-ID"). ``apply()`` patches
   ``pylabrobot.io.{serial.Serial, usb.USB, hid.HID, ftdi.FTDI}`` from their
   ``builtins.Web*`` shim classes; its own post-write assert is a cheap
   consistency check on that write, not the invariant -- it fires one line
   after its own ``setattr`` and cannot observe a LATER rebind.
   ``verify_identity()`` is the actual enforcement point: same assert, by
   ``is`` -- never by name -- called again by the caller AFTER everything
   that could still rebind a ``builtins.Web*`` name has run. Both are
   fail-closed: raise ``PraxisDriftError`` immediately, never warn.

**Contract with the caller** (``web-repl/bootstrap/praxis_bootstrap.py`` --
a SEPARATE task owns that file; this module defines the interface it calls
into, it does not call itself):

    # 1. Fetch shim/web_bridge/praxis-package source over XHR and write it
    #    into the Pyodide VFS. (praxis_bootstrap.py's job -- needs `js`.)
    ...

    # 2. Import each shim EXACTLY ONCE via `import_shim_class` (R-ID) and
    #    staple the result onto builtins. MUST happen before step 3, because
    #    `install_native_stubs()`'s postcondition requires
    #    `sys.modules['serial'].Serial is WebSerial` immediately.
    import builtins
    builtins.WebSerial = stages.import_shim_class("web_serial_shim", "WebSerial")
    builtins.WebUSB    = stages.import_shim_class("web_usb_shim",    "WebUSB")
    builtins.WebHID    = stages.import_shim_class("web_hid_shim",    "WebHID")
    builtins.WebFTDI   = stages.import_shim_class("web_ftdi_shim",   "WebFTDI")

    # 3. Install the native stubs -- BEFORE any `import pylabrobot`.
    stages.install_native_stubs(web_serial_cls=builtins.WebSerial)

    # 4. Install wheels, `import pylabrobot`, etc. (loader's job.)
    ...

    # 5. Patch pylabrobot.io from the shims (cheap post-write consistency
    #    check only -- NOT the R-ID enforcement point).
    stages.apply()

    # 6. web_bridge.bootstrap_playground() and anything else that could still
    #    rebind a builtins.Web* name runs here. (loader's job.)
    ...

    # 7. THE R-ID enforcement point (ADR SS2.2): assert-only, no setattr,
    #    called last, immediately before praxis:ready.
    stages.verify_identity()

``import_shim_class`` is the ONLY sanctioned way to turn fetched shim source
into a class object: it is a plain, memoized ``importlib.import_module`` call
-- there is no ``exec`` anywhere in this file, into a throwaway namespace or
otherwise. That is deliberate and structural, not incidental: ``exec(src, {})``
is the exact mechanism ADR SS2.2 identifies as manufacturing a SECOND, distinct
class object under the same name every time it runs (the ADR calls the two
resulting objects "class A" and "class B"). A second call to
``import_shim_class`` with the same module name returns the cached
``sys.modules`` entry, so the class object it hands back is identical, by
``is``, to the first call's -- not merely equal by name or repr.
"""

from __future__ import annotations

import asyncio
import builtins
import importlib
import inspect
import sys
import threading
import traceback
import types

__all__ = [
    "PraxisBootError",
    "PraxisDriftError",
    "PraxisUnavailableError",
    "NATIVE_STUB_MODULES",
    "IO_TARGETS",
    "DEV_SENTINEL",
    "install_native_stubs",
    "import_shim_class",
    "apply",
    "verify_identity",
    "assert_praxis_git_sha",
    "LOOP_TASK_TARGETS",
    "LoopTaskThread",
    "install_loop_threads",
]


# ---------------------------------------------------------------------------
# 1. Error taxonomy (ADR SS4.3) -- the ONLY home.
# ---------------------------------------------------------------------------


class PraxisBootError(Exception):
    """Base class for every fail-closed boot-stage error this bootstrap raises."""


class PraxisDriftError(PraxisBootError):
    """A build/runtime artifact does not match its expected fingerprint.

    Covers: a mismatched PLR_SOURCE_SHA, a mismatched BUILD_ID, a mismatched
    shell-injected praxis_git_sha (all raised by the loader, not this module)
    -- and, as raised by ``apply()`` below, a broken single-class-object
    identity invariant (ADR SS2.2 R-ID).
    """


class PraxisUnavailableError(PraxisBootError):
    """A required asset (manifest.json, a wheel, ...) could not be fetched or installed.

    Raised by the loader, not this module; the class lives here because the
    taxonomy has exactly one home (ADR SS4.3).
    """


# ---------------------------------------------------------------------------
# 2. install_native_stubs() -- REPLACES `_mock_native_deps()` entirely.
# ---------------------------------------------------------------------------

# RAN, read verbatim from (old) praxis_bootstrap.py:40-49 -- the SEVEN dotted
# names the current MagicMock covers. This set is load-bearing and must not
# grow or shrink casually: PLR's capability flags are evaluated once, at
# import time, against exactly these import statements.
NATIVE_STUB_MODULES: tuple[str, ...] = (
    "ssl",
    "usb",
    "usb.core",
    "usb.util",
    "serial",
    "serial.tools",
    "serial.tools.list_ports",
)


def install_native_stubs(
    web_serial_cls: type | None = None,
) -> dict[str, bool]:
    """Register real ``types.ModuleType`` stand-ins for the seven dotted names.

    PyLabRobot's ``try: import X`` capability probes need these to succeed so
    ``HAS_SERIAL`` evaluates True in a browser where ``serial`` does not
    actually exist. Measured against the real built wheels
    (``pylabrobot-0.2.2+gdd79c4c8`` + the fixed ``pylibftdi`` stub wheel;
    re-measured 260818 after the Phase 4 pin bump -- values unchanged; the
    1.0.0b1 pin ``pylabrobot-1.0.0b1+g786ac2c4`` reports the same four flags in
    the browser -- ``--probe`` ``capability_flags``, 260929),
    before ``apply()``, with these seven names stubbed:
    ``{'HAS_SERIAL': True, 'USE_USB': False, 'USE_HID': False,
    'HAS_PYLIBFTDI': True}``. Do NOT assume this function makes all four
    PLR capability flags True -- it does not, and never claimed to for two
    of them once you check PLR's own source rather than PLR's docstrings:

    - ``HAS_SERIAL`` -- True, via the ``serial`` stub this function installs.
    - ``HAS_PYLIBFTDI`` -- True, but NOT because of this function: PLR's own
      ``pylabrobot.io.ftdi`` does ``try: import pylibftdi.driver; from
      pylibftdi import Device, FtdiError`` against the real, separately
      installed ``pylibftdi`` stub *wheel* (``web-repl/scripts/
      pylibftdi_stub/``), not against anything in ``NATIVE_STUB_MODULES``.
    - ``USE_USB`` / ``USE_HID`` -- False, and structurally so: PLR gates them
      on ``import libusb_package`` (``pylabrobot/io/usb.py``) and
      ``import hid`` (``pylabrobot/io/hid.py``) respectively, and neither
      ``libusb_package`` nor ``hid`` is one of the seven names stubbed here
      or anywhere else in this bootstrap. This is deliberate, not an
      oversight: both flags are read ONLY inside the ORIGINAL
      ``pylabrobot.io.usb.USB`` / ``pylabrobot.io.hid.HID`` classes' own
      ``setup()`` methods (verified by
      ``git -C external/pylabrobot grep -n USE_USB USE_HID`` -- no other
      file reads either name), and ``apply()`` replaces those classes
      wholesale with ``WebUSB`` / ``WebHID`` -- independent implementations
      (``web-repl/overlay/assets/shims/web_{usb,hid}_shim.py``) that never
      consult ``USE_USB``/``USE_HID`` at all. The flags gate no code path
      the browser REPL reaches; stubbing ``libusb_package``/``hid`` just to
      flip two dead flags True would add stub surface for no behavioral
      gain, so this function leaves them unstubbed and False on purpose.

    The seven stub names are load-bearing beyond the four flags above,
    though: at the 0.2.2 pin ``pylabrobot/storage/cytomat/cytomat.py`` did a
    bare module-scope ``import serial`` with NO ``try/except`` -- it only
    succeeded in a browser because this function ran first and put a
    ``serial`` module in ``sys.modules``. (At 1.0.0b1 that site,
    ``pylabrobot/legacy/storage/cytomat/cytomat.py``, is try-guarded, but
    ``pylabrobot.io.serial`` / ``ftdi`` / ``usb`` still evaluate their
    capability flags against these names at import time.)

    Not classes. Not ``unittest.mock.MagicMock``. Not bare ``object()``s --
    real ``types.ModuleType`` instances, because a downstream check asserts
    ``'unittest.mock' not in type(sys.modules['serial']).__module__``.

    MUST be called before any ``import pylabrobot`` (or submodule of it) --
    PLR's flags are checked once and never re-evaluated.

    Idempotent / non-destructive: a name already present in ``sys.modules``
    (e.g. CPython's own real stdlib ``ssl``) is left untouched -- this is the
    same guard the old ``_mock_native_deps()`` used
    (``if mod_name not in sys.modules: ...``), preserved here on purpose so a
    module that is genuinely real and working is never shadowed by a stub.

    ``web_serial_cls``, if given, is stapled onto the stub ``serial`` module
    as ``serial.Serial`` -- this is what lets the immediately-following boot
    postcondition ``sys.modules['serial'].Serial is WebSerial`` hold. Passing
    ``None`` (the default) is supported for isolated testing of the stub
    machinery itself, independent of any shim class.

    Returns ``{dotted_name: True}`` for every name this call itself
    installed (a name that was already present is reported ``False`` --
    "not freshly installed", not "failed").
    """
    freshly_installed: dict[str, bool] = dict.fromkeys(NATIVE_STUB_MODULES, False)

    def _new(name: str) -> types.ModuleType:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
        freshly_installed[name] = True
        return mod

    # -- ssl: bare stand-in. Nothing in this bootstrap reads attributes off
    # it; PLR-adjacent code only needs `import ssl` to not raise. --
    if "ssl" not in sys.modules:
        _new("ssl")

    # -- usb / usb.core / usb.util --
    usb_mod = sys.modules["usb"] if "usb" in sys.modules else _new("usb")
    usb_core = sys.modules["usb.core"] if "usb.core" in sys.modules else _new("usb.core")
    usb_util = sys.modules["usb.util"] if "usb.util" in sys.modules else _new("usb.util")
    usb_mod.core = usb_core
    usb_mod.util = usb_util

    # -- serial / serial.tools / serial.tools.list_ports --
    if "serial" in sys.modules:
        serial_mod = sys.modules["serial"]
    else:
        serial_mod = _new("serial")
        serial_mod.SerialException = type("SerialException", (Exception,), {})
    if web_serial_cls is not None:
        serial_mod.Serial = web_serial_cls
    elif not hasattr(serial_mod, "Serial"):
        serial_mod.Serial = None

    serial_tools = (
        sys.modules["serial.tools"] if "serial.tools" in sys.modules else _new("serial.tools")
    )
    serial_mod.tools = serial_tools

    if "serial.tools.list_ports" in sys.modules:
        list_ports = sys.modules["serial.tools.list_ports"]
    else:
        list_ports = _new("serial.tools.list_ports")
        list_ports.comports = lambda include_links=False: []
    serial_tools.list_ports = list_ports

    return freshly_installed


# ---------------------------------------------------------------------------
# import_shim_class() -- the R-ID mechanism (ADR SS2.2).
# ---------------------------------------------------------------------------


def import_shim_class(module_name: str, class_name: str) -> type:
    """Import ``module_name`` exactly once and return ``getattr(module, class_name)``.

    Precondition (the caller's job, not this function's): ``module_name``'s
    source has already been fetched and written into the Pyodide VFS.

    This is the entire R-ID mechanism (ADR SS2.2). There is no ``exec`` in
    this function, or anywhere in this module -- a second call with the same
    ``module_name`` hits Python's own ``sys.modules`` cache and returns the
    SAME module object, so the class handed back is identical, by ``is``, to
    whatever a previous call (or a previous ``import module_name`` anywhere
    else in the process) already produced. That is the whole fix: exactly one
    importable module exists per shim, therefore exactly one class object
    exists per shim name.
    """
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


# ---------------------------------------------------------------------------
# 3. apply() -- the home of the single-class-object identity invariant.
# ---------------------------------------------------------------------------

# (pylabrobot.io submodule, attribute name on it, builtins name of the shim)
IO_TARGETS: tuple[tuple[str, str, str], ...] = (
    ("pylabrobot.io.serial", "Serial", "WebSerial"),
    ("pylabrobot.io.usb", "USB", "WebUSB"),
    ("pylabrobot.io.hid", "HID", "WebHID"),
    ("pylabrobot.io.ftdi", "FTDI", "WebFTDI"),
)


def assert_identity(
    module: types.ModuleType, attr: str, expected_cls: type, builtin_name: str
) -> None:
    """Fail-closed identity check, factored out of ``apply()`` for testability.

    Factored out so it is independently testable against a DELIBERATELY
    broken pair -- not just the always-passes-trivially case of "assert
    right after I set it myself".

    Raises ``PraxisDriftError`` unless ``getattr(module, attr) is
    expected_cls`` -- checked by ``is``, never by name or ``==``/repr
    equality, per ADR SS2.2. This is precisely the comparison that a
    re-introduced double-``exec`` (ADR SS2.2's "class A" vs "class B") fails:
    two classes can be textually identical, share a name, and even compare
    equal by repr, while still being two distinct objects that fail ``is``.
    """
    actual_cls = getattr(module, attr)
    if actual_cls is not expected_cls:
        msg = (
            f"single-class-object invariant (ADR SS2.2 R-ID) violated: "
            f"{module.__name__}.{attr} is {actual_cls!r}, which is NOT "
            f"builtins.{builtin_name} ({expected_cls!r}) BY IDENTITY. "
            f"Exactly one class object must exist per shim name -- this is "
            f"the exact shape of the historical bug where "
            f"`web_bridge.bootstrap_playground()`'s now-deleted shim "
            f"re-injection rebound builtins.{builtin_name} to a second, "
            f"distinct class produced by a real module import, after "
            f"pylabrobot.io had already been patched with the first, "
            f"exec-into-a-throwaway-namespace class."
        )
        raise PraxisDriftError(msg)


def apply() -> dict[str, bool]:
    """Patch pylabrobot.io from the builtins shim classes.

    Assigns ``pylabrobot.io.{serial.Serial, usb.USB, hid.HID, ftdi.FTDI}``
    from their ``builtins.Web*`` shim classes, then runs
    ``assert_identity()`` once per target as a cheap internal consistency
    check on the ``setattr`` this function just did.

    **That post-write assert is NOT the ADR SS2.2 R-ID enforcement point.**
    It fires one line after this function's own ``setattr`` on a plain
    ``types.ModuleType``, so it can only fail if something overrides
    ``__setattr__`` -- it cannot observe the historical bug shape (a LATER
    rebind of ``builtins.Web*``, after this function already ran). The real
    enforcement point is ``verify_identity()``, below, called by
    ``praxis_bootstrap.py`` immediately before ``praxis:ready`` -- after
    everything that could still rebind a ``builtins.Web*`` name (notably
    ``web_bridge.bootstrap_playground()``) has run. Kept here anyway because
    it is a free, cheap check that this function did what it meant to do;
    just don't mistake it for the invariant.

    Preconditions: all four of ``builtins.WebSerial``, ``builtins.WebUSB``,
    ``builtins.WebHID``, ``builtins.WebFTDI`` must already be set (by
    ``import_shim_class`` calls the caller made earlier) -- ``apply()``
    raises ``PraxisDriftError`` naming the missing one rather than silently
    skipping a target, which is exactly the kind of silent partial-patch
    ``praxis:ready`` firing over that this whole redesign exists to close.

    Does NOT touch ``pylabrobot.io.ftdi.HAS_PYLIBFTDI`` -- that flag is set by
    PLR's own ``try: import pylibftdi.driver / from pylibftdi import Device,
    FtdiError`` at ``pylabrobot.io.ftdi`` import time, and is real (backed by
    the ``pylibftdi`` stub wheel actually installing that package) once the
    stub package supplies both ``pylibftdi.driver`` and the two names PLR
    imports. A prior version of this function forced
    ``ftdi_mod.HAS_PYLIBFTDI = True`` unconditionally, which papered over a
    then-broken stub (the real import genuinely failed) -- forcing a flag
    True over a failed capability probe is precisely the pathology ADR
    260817 exists to abolish, so it was deleted rather than kept as a
    belt-and-suspenders default.

    Returns ``{"<module>.<attr>": True}`` for all four targets on success.
    Never returns a ``False`` entry: a failed identity check raises instead
    of being reported, because ADR SS2.2 mandates fail-closed, not "warn and
    report False for someone else to check."
    """
    results: dict[str, bool] = {}
    for module_path, attr, builtin_name in IO_TARGETS:
        if not hasattr(builtins, builtin_name):
            msg = (
                f"apply() called before builtins.{builtin_name} was staged -- "
                f"the loader must call import_shim_class() for all four shims "
                f"and staple them onto builtins before calling stages.apply()"
            )
            raise PraxisDriftError(msg)
        shim_cls = getattr(builtins, builtin_name)
        module = importlib.import_module(module_path)
        setattr(module, attr, shim_cls)
        assert_identity(module, attr, shim_cls, builtin_name)
        results[f"{module_path}.{attr}"] = True

    return results


def verify_identity() -> dict[str, bool]:
    """Assert-only re-check of the R-ID invariant (ADR SS2.2) -- NO ``setattr``.

    This is the actual enforcement point for ADR SS2.2, not ``apply()``'s
    post-write assert (see the note in ``apply()``'s docstring for why that
    one is structurally incapable of catching real drift). The historical bug
    -- ``web_bridge.bootstrap_playground()``'s now-deleted shim re-injection
    re-importing a shim module and rebinding ``builtins.Web*`` to a second,
    distinct class AFTER ``pylabrobot.io`` had already been patched -- can
    only be caught by asserting again, later, after everything that could
    still perform such a rebind has run. Callers must call this AFTER
    ``apply()`` and AFTER ``web_bridge.bootstrap_playground()`` -- see
    ``praxis_bootstrap.py``'s call site, immediately before ``praxis:ready``.

    Reads (never writes) ``pylabrobot.io.{serial.Serial, usb.USB, hid.HID,
    ftdi.FTDI}`` against ``builtins.Web{Serial,USB,HID,FTDI}`` and raises
    ``PraxisDriftError`` via ``assert_identity()`` -- fail-closed, same as
    ``apply()`` -- on the first mismatch found, checked by ``is``, never by
    name or ``==``.

    Preconditions: same as ``apply()`` -- all four ``builtins.Web*`` names
    must already be set, and ``apply()`` must already have run (so
    ``pylabrobot.io.*`` has the attribute to read at all).

    Returns ``{"<module>.<attr>": True}`` for all four targets on success.
    """
    results: dict[str, bool] = {}
    for module_path, attr, builtin_name in IO_TARGETS:
        if not hasattr(builtins, builtin_name):
            msg = (
                f"verify_identity() called before builtins.{builtin_name} was "
                f"staged -- the loader must call import_shim_class() for all "
                f"four shims and staple them onto builtins before calling "
                f"stages.verify_identity()"
            )
            raise PraxisDriftError(msg)
        shim_cls = getattr(builtins, builtin_name)
        module = importlib.import_module(module_path)
        assert_identity(module, attr, shim_cls, builtin_name)
        results[f"{module_path}.{attr}"] = True

    return results


# ---------------------------------------------------------------------------
# 4. assert_praxis_git_sha() -- D1, ADR Sec 2.3.
# ---------------------------------------------------------------------------

# The literal sentinel both `build_manifest.py --dev` and `inject_shell.py
# --dev` write. A real superproject sha is 40 hex characters and can never
# collide with this string, so plain equality below is unambiguous.
DEV_SENTINEL = "dev"


def assert_praxis_git_sha(manifest_sha: str, shell_sha: str) -> None:
    """D1: compare the manifest's ``praxis_git_sha`` (fetched, written by
    ``build_manifest.py``) against the shell's (received over the
    ``praxis:shell-ping``/``praxis:shell-pong`` handshake defined in
    ``web-repl/shell/praxis-shell.js``, injected by ``inject_shell.py``).

    This is the ONLY detector that catches WHOLE-DEPLOYMENT staleness --
    every fetched asset, including manifest.json itself, consistently old --
    because ``shell/praxis-shell.js``'s injected value lives OUTSIDE the
    JupyterLite fetched-asset set (ADR Sec 2.3). D2 (manifest sha256 over
    wheels and sources) cannot catch this: a wholly-stale deployment is
    internally self-consistent by construction.

    Deliberately just ``!=``. The dev-loop escape hatch ("the assert is
    skipped only when BOTH sides read 'dev'") is not a branch here -- it is
    an EMERGENT property of plain string equality: ``"dev" == "dev"``
    already passes, and every other pairing (two different real shas, or one
    real sha against the literal "dev") already fails. Adding an explicit
    ``if manifest_sha == DEV_SENTINEL and shell_sha == DEV_SENTINEL: return``
    branch would be redundant with what equality already does, and would
    invite exactly the kind of asymmetric-dev bug this function's negative
    test (``web-repl/tests/test_d1_praxis_git_sha.py``) exists to catch if
    someone "simplifies" this into an OR.

    Raises ``PraxisDriftError`` naming BOTH values on any mismatch, fail
    closed -- never a warning.
    """
    if manifest_sha != shell_sha:
        raise PraxisDriftError(
            "D1 whole-deployment staleness check (ADR Sec 2.3) failed: "
            f"manifest.json praxis_git_sha={manifest_sha!r} != shell-injected "
            f"praxis_git_sha={shell_sha!r}. This compares the superproject "
            "git sha baked into the fetched manifest against the one "
            "injected into lab/index.html (outside the fetched-asset set) "
            "at build time -- a mismatch means the deployment is at least "
            "partially stale relative to what was built."
        )


# ---------------------------------------------------------------------------
# 5. install_loop_threads() -- PLR reader threads as tasks (Pyodide has no threads).
# ---------------------------------------------------------------------------

# Thread target method name -> the coroutine method that target runs on a fresh
# event loop. Only this exact shape is converted; tests/test_loop_threads.py scans
# the pinned PLR source and fails on any thread site that is neither this shape
# nor listed there as known-unsupported.
LOOP_TASK_TARGETS: dict[str, str] = {"_reading_thread_main": "_continuously_read"}

_REAL_THREAD = threading.Thread


def _loop_task_coroutine(target):
    """The bound coroutine function to run instead of ``target``, or None."""
    owner = getattr(target, "__self__", None)
    coroutine_name = LOOP_TASK_TARGETS.get(getattr(target, "__name__", ""))
    if owner is None or coroutine_name is None:
        return None
    coroutine_fn = getattr(owner, coroutine_name, None)
    return coroutine_fn if inspect.iscoroutinefunction(coroutine_fn) else None


def _report_task_failure(task: asyncio.Task) -> None:
    if task.cancelled() or task.exception() is None:
        return
    exc = task.exception()
    print(f"Exception in background task {task.get_name()}:", file=sys.stderr)
    traceback.print_exception(type(exc), exc, exc.__traceback__, file=sys.stderr)


class LoopTaskThread(_REAL_THREAD):
    """``threading.Thread`` that runs PLR's reader loop as a task on the running loop.

    A Pyodide kernel cannot start threads (``RuntimeError: can't start new
    thread``), so ``HamiltonLiquidHandler.setup()`` failed the moment it started
    its firmware reader. That reader thread only runs ``_continuously_read()`` on a
    private event loop, and in the browser it has to run on the kernel's own loop
    anyway: the WebUSB shim's ``read()`` awaits JavaScript promises that loop
    drives. So for a target in ``LOOP_TASK_TARGETS`` whose owner has the matching
    coroutine method, ``start()`` schedules that coroutine on the running loop and
    never calls the target. ``call_soon_threadsafe`` (how the reader hands replies
    back) works unchanged on one loop.

    ``join()`` cannot block (it would freeze the loop the task runs on), so it
    cancels the task; PLR sets its stop event first, then joins. Every other target
    goes to the real ``Thread.start()``, which in Pyodide raises as before.
    """

    _praxis_task: asyncio.Task | None = None

    def start(self) -> None:
        coroutine_fn = _loop_task_coroutine(getattr(self, "_target", None))
        if coroutine_fn is None:
            return super().start()
        if self._praxis_task is not None:
            raise RuntimeError("threads can only be started once")
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError(
                f"{coroutine_fn.__qualname__} runs as a task in the browser kernel, so "
                "it must be started from inside a running event loop (await the call "
                "that starts it, e.g. `await lh.setup()`)."
            ) from None
        self._praxis_task = loop.create_task(coroutine_fn(), name=coroutine_fn.__qualname__)
        self._praxis_task.add_done_callback(_report_task_failure)
        return None

    def is_alive(self) -> bool:
        if self._praxis_task is None:
            return super().is_alive()
        return not self._praxis_task.done()

    def join(self, timeout: float | None = None) -> None:
        if self._praxis_task is None:
            return super().join(timeout)
        if not self._praxis_task.done():
            self._praxis_task.cancel()
        return None


def install_loop_threads(platform: str | None = None) -> bool:
    """In Pyodide, make ``threading.Thread`` the ``LoopTaskThread`` (idempotent).

    PLR looks ``threading.Thread`` up at call time, so this can run any time before
    a machine's ``setup()``; the bootstrap runs it before installing any wheel.
    Returns whether the shim is installed. Outside Pyodide (``platform`` defaults
    to ``sys.platform``) it does nothing and returns False: real threads work there.
    """
    if (platform or sys.platform) != "emscripten":
        return False
    threading.Thread = LoopTaskThread
    return True
