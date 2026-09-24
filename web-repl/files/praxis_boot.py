"""You normally never import this: every kernel runs it automatically at
start (via ``praxis_startup.py``). It fetches and applies the Praxis
bootstrap, and gates every cell until that finishes, so ``import pylabrobot``
just works in your first cell.

Why this module exists at all: PyLabRobot is not baked into the Pyodide
image. It is installed at runtime, and its device I/O classes are then
swapped for browser shims (Web Serial, WebUSB, WebHID, FTDI-over-serial).
That work lives in ``bootstrap/praxis_bootstrap.py`` on the web server, and
until something runs it a fresh kernel has no ``pylabrobot`` at all --
``import pylabrobot`` raises ``ModuleNotFoundError``.

Things you might actually want to call by hand:

    import praxis_boot
    praxis_boot.status()          # prints "praxis auto-setup state: <state>"
    await praxis_boot.setup()     # safe to call any time; returns immediately
                                   # if this kernel is already set up. Also the
                                   # retry path after a failed auto-setup.
    praxis_boot.dismiss()         # after a failure, use this kernel without
                                   # PyLabRobot instead of retrying setup

If a cell raises ``PraxisAutoSetupError``, auto-setup failed in this kernel;
the message names the cause and your recovery options. Do not edit or rename
this file or ``praxis_startup.py`` in your drive -- a shadowed copy silently
stops auto-setup from running.

This module ships in the JupyterLite contents drive, which the kernel mounts
at ``/drive`` and uses as its working directory, so it is importable from any
notebook you create without fetching anything by hand first.
"""

from __future__ import annotations

import asyncio
import secrets

# The kernel worker is served from "<site root>extensions/@jupyterlite/..." --
# this is the segment that separates the two.
_WORKER_MARKER = "extensions/"
_LOADER_PATH = "bootstrap/praxis_bootstrap.py"

#: Bumped whenever the startup file's expectations of this module change.
#: praxis_startup.py refuses to auto-start against a mismatched version.
AUTOSETUP_PROTOCOL = 1

#: Site root resolved by the last successful setup(), or None.
host_root: str | None = None

#: "idle" | "running" | "ready" | "failed" | "dismissed"
state: str = "idle"

#: The exception that put this kernel into "failed", or None.
failure: BaseException | None = None

#: Set True only when _gate_cell entered with state == "running" for a given
#: cell -- i.e. proof that a cell's execute request genuinely had to wait.
gate_waited: bool = False

#: Where _autostart() was invoked from (e.g. "PYTHONSTARTUP"), or None.
autostart_origin: str | None = None

#: Per-kernel identifier, freshly minted at import time. A restart runs this
#: module again from scratch, so a new nonce proves a new interpreter (AC-7).
kernel_nonce: str = secrets.token_hex(8)

#: The in-flight auto-setup task, or None before _autostart() runs.
_task: "asyncio.Future | None" = None

#: Created lazily inside a coroutine (never at import time, when there may be
#: no running event loop yet).
_lock: "asyncio.Lock | None" = None


class PraxisAutoSetupError(RuntimeError):
    """Raised inside a gated cell when this kernel's auto-setup did not (yet,
    or ever) reach "ready". See the module docstring for recovery options."""


def _safe_repr(obj: object, fallback: str = "<unprintable exception>") -> str:
    """``repr(obj)``, or *fallback* if that itself raises anything.

    Guards every error message this module builds (gate step 4, _gate_error,
    status()) against an exception whose own __repr__/__str__ raises (R2-5) --
    otherwise formatting the very thing meant to explain a failure could
    itself crash and defeat the fail-closed/fail-visible design.
    """
    try:
        return repr(obj)
    except BaseException:
        return fallback


def derive_host_root() -> str:
    """Work out the site root from the kernel worker's own URL.

    The site root cannot be read from ``window.location``: the kernel is a Web
    Worker, so its global is ``self`` and there is no ``window``. That is why
    the bootstrap has historically been handed a hardcoded ``HOST_ROOT``, and
    why a cell copied between a root deploy and a subpath deploy 404s.

    ``self.location`` DOES exist in the worker, and it points at the kernel
    worker script -- measured 2026-08-24:

        /praxis/extensions/@jupyterlite/pyodide-kernel-extension/static/comlink.worker.<hash>.js

    Everything before ``extensions/`` is the site root, giving ``/praxis/``
    here and ``/`` on a root deploy.

    Raises rather than guessing. A wrong root produces a 404 on the loader
    fetch, and silently falling back to ``"/"`` would turn a clear failure
    into a confusing one on exactly the deploy shape that needs this most.
    """
    import js

    try:
        pathname = str(js.location.pathname)
    except Exception as exc:  # pragma: no cover - browser-only path
        raise RuntimeError(
            "could not read the kernel worker's own location, so the site root "
            "cannot be derived. Pass it explicitly: "
            "await praxis_boot.setup(host_root_override='/praxis/')"
        ) from exc

    # rfind, not find: a site deployed under a path that itself contains
    # "extensions/" would otherwise be truncated at the wrong segment.
    index = pathname.rfind(_WORKER_MARKER)
    if index == -1:
        raise RuntimeError(
            f"could not derive the site root: the kernel worker URL {pathname!r} "
            f"does not contain {_WORKER_MARKER!r}, so the layout this relies on has "
            "changed. Pass it explicitly: "
            "await praxis_boot.setup(host_root_override='/praxis/')"
        )

    root = pathname[:index]
    if not root.startswith("/"):
        root = "/" + root
    if not root.endswith("/"):
        root += "/"
    return root


def _inject_playground_names() -> None:
    """Inject playground names into the IPython user namespace.

    The legacy welcome bootstrap cell exec'd the loader into the NOTEBOOK globals,
    so ``praxis_main``'s ``bootstrap_playground(globals())`` reached the user.
    ``_run_setup`` execs it into a private dict, so those names never reached the
    user's namespace. This injects them after a successful bootstrap so a notebook
    can write ``LiquidHandler(backend=STAR(), deck=...)`` without imports.

    If there is no IPython shell (e.g., in CPython tests), this is a no-op.
    Any exception here is swallowed and does NOT fail setup.
    """
    try:
        import IPython

        shell = IPython.get_ipython()
        if shell is None:
            return

        import web_bridge

        web_bridge.bootstrap_playground(shell.user_ns)
    except Exception:
        # Failures here must never fail setup (the post-condition is _verify,
        # not ergonomics). Swallow silently.
        pass


def _verify() -> str:
    """Confirm the bootstrap actually did what it claims. Returns the version.

    This is not belt-and-braces. ``praxis_main()`` wraps its entire body in a
    single ``except Exception`` that broadcasts ``praxis:error`` and does NOT
    re-raise -- a deliberate fail-closed catch-all. The practical consequence
    is that ``await praxis_main(...)`` returns normally on a FAILED boot, so
    awaiting it proves only that the call finished. Without the checks below,
    ``setup()`` would cheerfully report success on a kernel that has no
    PyLabRobot, which is the precise failure this module exists to end.
    """
    import builtins
    import importlib

    try:
        pylabrobot = importlib.import_module("pylabrobot")
    except Exception as exc:
        raise RuntimeError(
            "the bootstrap ran but pylabrobot is still not importable. The loader "
            "reports failures on the 'praxis_repl' BroadcastChannel rather than by "
            "raising, so check the browser console for a praxis:error message."
        ) from exc

    serial_module = importlib.import_module("pylabrobot.io.serial")
    web_serial = getattr(builtins, "WebSerial", None)
    if web_serial is None or serial_module.Serial is not web_serial:
        raise RuntimeError(
            "pylabrobot imported, but its Serial class is NOT the browser shim, so "
            "device I/O would silently go to desktop pyserial instead of Web Serial. "
            "This is an identity check on the class object, so it cannot pass on a "
            "same-named impostor."
        )

    return getattr(pylabrobot, "__version__", "unknown")


def _autostart(origin: str) -> None:
    """Start auto-setup for this kernel. Called once by ``praxis_startup.py``
    during kernel init (PYTHONSTARTUP). Synchronous, and must never raise --
    it runs before any cell exists to show an error in, so an exception here
    would be swallowed invisibly (the same reasoning that makes the startup
    file's own catch-and-rewrite gate unconditional).

    Idempotent: a second call (e.g. ``%run praxis_startup.py`` again) is a
    no-op once ``_task`` exists.
    """
    global state, autostart_origin, _task, failure

    try:
        if _task is not None:
            return

        autostart_origin = origin

        try:
            import IPython

            shell = IPython.get_ipython()
            manager = shell.kernel.lite_transform_manager
        except BaseException as exc:
            state = "failed"
            failure = RuntimeError(
                "pyodide-kernel internals changed: could not reach "
                f"get_ipython().kernel.lite_transform_manager ({_safe_repr(exc)})"
            )
            return

        # cleanup_transforms runs before line_transforms (which hold
        # pip_magic), so inserting at index 0 makes a first cell of
        # "%pip install x" wait too.
        if _gate_cell not in manager.cleanup_transforms:
            manager.cleanup_transforms.insert(0, _gate_cell)

        state = "running"
        _task = asyncio.ensure_future(_run_setup(auto=True))
    except BaseException as exc:  # belt-and-suspenders: _autostart must never raise
        try:
            state = "failed"
            failure = exc
        except BaseException:
            pass


async def _run_setup(
    host_root_override: str | None = None, *, force: bool = False, auto: bool = False
) -> str | None:
    """Do the actual bootstrap work. Shared body for ``setup()`` and the
    auto-started task; ``auto`` controls whether a failure is surfaced by
    raising (manual call) or left for the gate to surface (auto-setup)."""
    global host_root, state, failure, _lock

    if _lock is None:
        _lock = asyncio.Lock()

    async with _lock:
        if state == "ready" and not force:
            if not auto:
                print(f"already bootstrapped (site root {host_root}); pass force=True to redo")
            return host_root

        try:
            root = host_root_override if host_root_override is not None else derive_host_root()
            loader_url = root + _LOADER_PATH

            import js

            # Synchronous XHR on purpose: the loader must be present before
            # anything below it runs, and this mirrors how welcome.ipynb
            # fetches it.
            xhr = js.XMLHttpRequest.new()
            xhr.open("GET", loader_url, False)
            xhr.send(None)
            xhr_status = int(xhr.status)
            if xhr_status != 200:
                raise RuntimeError(
                    f"fetching the loader at {loader_url} returned HTTP {xhr_status}. The "
                    f"site root was derived as {root!r}; if that is wrong for this deploy, "
                    "pass it explicitly: await praxis_boot.setup(host_root_override='/praxis/')"
                )

            # exec into a private namespace rather than the caller's globals:
            # the loader's real outputs are side effects (shims stapled onto
            # builtins, PyLabRobot's io classes rebound), not names, so there
            # is nothing to be gained by scattering its internals through the
            # user's notebook.
            namespace: dict = {}
            exec(compile(str(xhr.responseText), "praxis_bootstrap.py", "exec"), namespace)

            praxis_main = namespace.get("praxis_main")
            if praxis_main is None:
                raise RuntimeError(
                    f"{loader_url} was fetched but defines no praxis_main(), so it is not "
                    "the Praxis loader this expects."
                )

            await praxis_main(root, raise_on_error=True)
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            state = "failed"
            failure = exc
            if not auto:
                raise
            return None

        try:
            version = _verify()
        except asyncio.CancelledError:
            raise
        except BaseException as exc:
            # Tag so _gate_error() can give restart-only recovery text
            # (failure mode 6): a retry re-hits the once-guard, which skips
            # the stages and fails _verify() again.
            try:
                exc._praxis_verify_failed = True  # noqa: SLF001 -- our own tag
            except BaseException:
                pass
            state = "failed"
            failure = exc
            if not auto:
                raise
            return None

        host_root = root
        _inject_playground_names()
        state = "ready"
        failure = None
        if not auto:
            print(f"PyLabRobot {version} ready (site root {root}); Serial is the browser shim")
        return root


async def setup(host_root_override: str | None = None, *, force: bool = False) -> str:
    """Run the Praxis bootstrap in this kernel. Safe to call any time;
    returns immediately if this kernel is already set up. Also the retry
    path after a failed auto-setup.

    Args:
        host_root_override: Site root such as ``"/praxis/"``. Derived from the
            kernel worker URL when omitted, which is what you want.
        force: Re-run even if this kernel has already been bootstrapped.

    Returns:
        The site root that was used.
    """
    if _task is not None and not _task.done():
        # Auto-setup is still running (e.g. this cell got here without going
        # through the gate, or is itself the recovery cell): wait for the
        # SAME run rather than starting a second one.
        await asyncio.shield(_task)

    if force:
        # setup(force=True) is the one deliberate exception to the once-guard
        # (AC-6): clear it before _run_setup re-execs praxis_main.
        import builtins as _builtins

        _builtins._PRAXIS_BOOT_DONE = False

    return await _run_setup(host_root_override, force=force)


async def _gate_cell(lines: list[str]) -> list[str]:
    """Cell transform installed as ``cleanup_transforms[0]`` by ``_autostart``.

    Normative (S0 E4): this must catch every exception and return a rewrite;
    it must NEVER raise out of ``transform_cell``, or the kernel is left
    ``busy`` with JS pageerrors instead of a normal traceback in the cell.
    """
    try:
        return await _gate_cell_dispatch(lines)
    except BaseException as exc:
        return _gate_internal_error_lines(exc)


async def _gate_cell_dispatch(lines: list[str]) -> list[str]:
    global state, gate_waited, failure

    if state in ("ready", "dismissed"):
        return lines

    if state == "running":
        gate_waited = True
        interrupted = False
        try:
            await asyncio.shield(_task)
        except asyncio.CancelledError:
            # Distinguish "the task itself ended" (liveness, handled below)
            # from "this wait was itself interrupted" (R2-4 second bullet):
            # only the latter leaves the task still not done.
            if _task is None or not _task.done():
                interrupted = True
        except KeyboardInterrupt:
            interrupted = True
        except BaseException:
            pass  # the task's own exception; state below reflects the outcome

        if interrupted:
            # Static string (R2-5): do not build this dynamically. The
            # shielded task keeps running, so the next cell waits again.
            return [
                "raise __import__('praxis_boot').PraxisAutoSetupError("
                "'praxis auto-setup was interrupted while this cell waited for it. "
                "Your cell was NOT run; re-run it, or run await praxis_boot.setup().')\n"
            ]

        # Re-dispatch exactly once through steps 1/3/4, re-reading state;
        # never back into this branch.
        if state == "running":
            if _task is not None and _task.done():
                # Liveness R2-4 first bullet: task done but state never got
                # recorded (e.g. the task itself was cancelled).
                cause: BaseException | None
                if _task.cancelled():
                    cause = asyncio.CancelledError()
                else:
                    cause = _task.exception()
                new_failure = RuntimeError("praxis auto-setup task ended without a result")
                if cause is not None:
                    new_failure.__cause__ = cause
                failure = new_failure
                state = "failed"
            else:
                # Should be impossible: the wait returned but the task is
                # neither done nor did we get interrupted. Fail closed.
                return _gate_internal_error_lines(
                    RuntimeError("gate: task not done after a single await")
                )

        if state in ("ready", "dismissed"):
            return lines
        if state == "failed":
            return _gate_dispatch_failed(lines)
        return _gate_internal_error_lines(RuntimeError(f"gate: unexpected state {state!r}"))

    if state == "failed":
        return _gate_dispatch_failed(lines)

    return _gate_internal_error_lines(RuntimeError(f"gate: unexpected state {state!r}"))


def _gate_dispatch_failed(lines: list[str]) -> list[str]:
    """Step 3: let a recovery cell (one that mentions ``praxis_boot``, e.g.
    ``await praxis_boot.setup()`` or ``praxis_boot.dismiss()``) through;
    block everything else with a single raise line."""
    joined = "".join(lines)
    if "praxis_boot" in joined:
        return lines
    return ["raise __import__('praxis_boot')._gate_error()\n"]


def _gate_internal_error_lines(exc: BaseException) -> list[str]:
    """Step 4: the gate itself hit an internal error. Never raise -- return a
    rewrite, with a static fallback if even building the message fails."""
    try:
        return [
            "raise RuntimeError("
            + repr("PraxisAutoSetupError: praxis auto-setup gate error: " + _safe_repr(exc))
            + ")\n"
        ]
    except BaseException:
        return ["raise RuntimeError('PraxisAutoSetupError: praxis auto-setup gate error')\n"]


def _gate_error() -> PraxisAutoSetupError:
    """Build the error a blocked cell raises when ``state == "failed"``.
    Guarded formatting (R2-5): the whole construction sits in one
    ``try/except BaseException`` and falls back to a fully static message
    naming no details, rather than let a bad ``__repr__``/``__str__`` on the
    recorded failure crash the very code meant to explain it."""
    try:
        exc = failure
        detail = f"{type(exc).__name__}: {exc}" if exc is not None else "no recorded failure"
        msg = f"PyLabRobot setup failed in this kernel: {detail}."
        if host_root is not None:
            msg += f" (site root {host_root})"

        if exc is not None and getattr(exc, "_praxis_verify_failed", False):
            msg += (
                " Your cell was NOT run. setup completed but the result is broken; "
                "`praxis_boot.setup()` cannot fix this - restart the kernel."
            )
        elif exc is not None and "D1 whole-deployment staleness check" in str(exc):
            msg += (
                " Your cell was NOT run. Another Praxis tab from an older deploy on this "
                "site answered first. Close other Praxis tabs from an older deploy, then "
                "restart the kernel."
            )
        else:
            msg += (
                " Your cell was NOT run. Retry with `await praxis_boot.setup()` in a "
                "cell, restart the kernel, or run `praxis_boot.dismiss()` to use this "
                "kernel without PyLabRobot."
            )

        err = PraxisAutoSetupError(msg)
        err.__cause__ = exc
        return err
    except BaseException:
        err = PraxisAutoSetupError(
            "PyLabRobot setup failed in this kernel (details unavailable). Your cell "
            "was NOT run. Retry with `await praxis_boot.setup()`, or restart the kernel."
        )
        try:
            err.__cause__ = failure
        except BaseException:
            pass
        return err


def dismiss() -> None:
    """Use this kernel without PyLabRobot instead of retrying setup. Only
    takes effect from a failed kernel (OQ-2)."""
    global state

    if state == "failed":
        state = "dismissed"


def status() -> dict:
    """Print exactly one line, ``praxis auto-setup state: <state>``, then
    return a dict describing this kernel's auto-setup state. Never raises,
    even if the recorded failure's own formatting is broken (R2-5)."""
    print(f"praxis auto-setup state: {state}")

    try:
        pylabrobot_version = None
        if state == "ready":
            try:
                import importlib

                pylabrobot_version = importlib.import_module("pylabrobot").__version__
            except Exception:
                pylabrobot_version = None

        return {
            "state": state,
            "host_root": host_root,
            "pylabrobot_version": pylabrobot_version,
            "autostart_origin": autostart_origin,
            "kernel_nonce": kernel_nonce,
            "failure": _safe_repr(failure) if failure is not None else None,
        }
    except BaseException:
        return {
            "state": state,
            "host_root": host_root,
            "pylabrobot_version": None,
            "autostart_origin": autostart_origin,
            "kernel_nonce": kernel_nonce,
            "failure": "<unprintable exception>" if failure is not None else None,
        }
