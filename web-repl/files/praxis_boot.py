"""Bring PyLabRobot up in this kernel, from any notebook.

    import praxis_boot
    await praxis_boot.setup()

That is the whole thing. There is no URL to paste and no site root to get
right -- ``setup()`` works out where the site lives from the kernel worker's
own URL.

Why this file exists at all: PyLabRobot is not baked into the Pyodide image.
It is installed at runtime, and its device I/O classes are then swapped for
browser shims (Web Serial, WebUSB, WebHID, FTDI-over-serial). That work lives
in ``bootstrap/praxis_bootstrap.py`` on the web server, and until something
runs it a fresh kernel has no ``pylabrobot`` at all -- ``import pylabrobot``
raises ``ModuleNotFoundError``. Every kernel session needs it once.

This module ships in the JupyterLite contents drive, which the kernel mounts
at ``/drive`` and uses as its working directory, so it is importable from any
notebook you create without fetching anything by hand first.
"""

from __future__ import annotations

# The kernel worker is served from "<site root>extensions/@jupyterlite/..." --
# this is the segment that separates the two.
_WORKER_MARKER = "extensions/"
_LOADER_PATH = "bootstrap/praxis_bootstrap.py"

#: Site root resolved by the last successful setup(), or None.
host_root: str | None = None


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
            "await praxis_boot.setup(host_root='/praxis/')"
        ) from exc

    # rfind, not find: a site deployed under a path that itself contains
    # "extensions/" would otherwise be truncated at the wrong segment.
    index = pathname.rfind(_WORKER_MARKER)
    if index == -1:
        raise RuntimeError(
            f"could not derive the site root: the kernel worker URL {pathname!r} "
            f"does not contain {_WORKER_MARKER!r}, so the layout this relies on has "
            "changed. Pass it explicitly: "
            "await praxis_boot.setup(host_root='/praxis/')"
        )

    root = pathname[:index]
    if not root.startswith("/"):
        root = "/" + root
    if not root.endswith("/"):
        root += "/"
    return root


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


async def setup(host_root_override: str | None = None, *, force: bool = False) -> str:
    """Run the Praxis bootstrap in this kernel. Safe to call once per session.

    Args:
        host_root_override: Site root such as ``"/praxis/"``. Derived from the
            kernel worker URL when omitted, which is what you want.
        force: Re-run even if this kernel has already been bootstrapped.

    Returns:
        The site root that was used.
    """
    global host_root

    import js

    if host_root is not None and not force:
        print(f"already bootstrapped (site root {host_root}); pass force=True to redo")
        return host_root

    root = host_root_override if host_root_override is not None else derive_host_root()
    loader_url = root + _LOADER_PATH

    # Synchronous XHR on purpose: the loader must be present before anything
    # below it runs, and this mirrors how welcome.ipynb fetches it.
    xhr = js.XMLHttpRequest.new()
    xhr.open("GET", loader_url, False)
    xhr.send(None)
    status = int(xhr.status)
    if status != 200:
        raise RuntimeError(
            f"fetching the loader at {loader_url} returned HTTP {status}. The site "
            f"root was derived as {root!r}; if that is wrong for this deploy, pass "
            "it explicitly: await praxis_boot.setup(host_root_override='/praxis/')"
        )

    # exec into a private namespace rather than the caller's globals: the
    # loader's real outputs are side effects (shims stapled onto builtins,
    # PyLabRobot's io classes rebound), not names, so there is nothing to be
    # gained by scattering its internals through the user's notebook.
    namespace: dict = {}
    exec(compile(str(xhr.responseText), "praxis_bootstrap.py", "exec"), namespace)

    praxis_main = namespace.get("praxis_main")
    if praxis_main is None:
        raise RuntimeError(
            f"{loader_url} was fetched but defines no praxis_main(), so it is not the "
            "Praxis loader this expects."
        )

    await praxis_main(root)

    version = _verify()
    host_root = root
    print(f"PyLabRobot {version} ready (site root {root}); Serial is the browser shim")
    return root
