"""Praxis browser-Python bootstrap -- the ordered, fail-closed loader.

Per ADR ``.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md``
Sec 2.1, this file is the "ordered fail-closed driver; SINGLE OWNER", and the
old separate ``boot.py`` design is MERGED into it (Sec 4.3): this module owns
the ordered stage ledger and sequences it. It does NOT own the error
taxonomy, ``install_native_stubs()``, ``apply()``/``assert_identity()``, or
``import_shim_class()`` -- ``stages.py`` (in this same directory) owns all of
those; this file imports and sequences them. It does not own the D2 fetch
primitives or the D1 handshake body either -- ``transport.py`` owns those,
kept ``import js``-free so they are CPython-unit-testable. Per the plan's
P3.7 design intent, ``praxis_main()`` -- the actual ordered stage sequence --
is kept short by construction: the logic lives in ``stages``/``transport``,
this function only calls into it in order and stops on the first failure.

Entry point: called exactly as the old file was --
``asyncio.ensure_future(praxis_main(HOST_ROOT))`` by the minimal external
bootstrap snippet that fetches this file's own source over a synchronous XHR
and ``exec``s it (``playground-jupyterlite.service.ts`` today; its
standalone-site successor is Phase 5, out of this task's scope). That
snippet is this file's only caller and the only place ``host_root`` comes
from -- signature and name are kept exactly so nothing there needs to change.

**Why this file itself fetches two more files before doing anything else**
(``_bootstrap_loader_modules``, below): ``stages.py`` and ``transport.py``
live in ``web-repl/bootstrap/``, which sits OUTSIDE
``overlay/assets/{shims,python}`` -- ``build_manifest.py``'s own
``SOURCE_SUBDIRS`` -- so ``manifest.json`` structurally cannot list them
(ADR Sec 2.3's D2 table: the "sources" array is built by walking exactly
those two subdirectories). They ARE the code that makes manifest-driven
fetching possible, so fetching them cannot itself be manifest-driven; this
is the one and only hardcoded-URL exception, and it is a categorically
different thing from the seven hardcoded literals this rewrite removes
(four shims, ``web_bridge.py``, ``praxis/__init__.py``,
``praxis/interactive.py`` -- all now driven by ``transport.fetch_sources()``
reading ``manifest.json``'s "sources" array).

**Why this satisfies the "``praxis_boot_errors`` must be reachable before
any wheel is" requirement without a synthetic module**: this file imports
``stages`` (and therefore the whole ``PraxisBootError`` taxonomy) as
literally its first action, before ``manifest.json`` is even fetched. A
manifest-404 or a wheel-404 therefore always has ``PraxisUnavailableError``
available to raise it with -- the taxonomy's single home in ``stages.py`` (a
loose file, not a wheel) already satisfies the requirement, so no second,
synthetic ``praxis_boot_errors`` module is built here. See this task's
report for the full reasoning.

**Fail-closed, end to end:** every stage after the two-file self-bootstrap
runs inside one ``try`` whose ``except`` posts ``{"type": "praxis:error",
"reason": ...}`` on the ``praxis_repl`` BroadcastChannel and returns WITHOUT
ever reaching the ``{"type": "praxis:ready"}`` post at the very end of the
``try`` body. That is what moves ``praxis:ready`` INSIDE the guarded region
(P3.8): the old file posted it unconditionally after a separate,
already-swallowed wheel-install failure (old ``:239-246`` logs and falls
through; old ``:286-293`` posts ready regardless) -- the demonstrated live
bomb where renaming the wheel produced a 404, PyLabRobot never installed,
and ``praxis:ready`` fired anyway with ``builtins.Plate`` absent.
"""

from __future__ import annotations

import builtins
import hashlib
import importlib


# The one hardcoded-URL exception -- see the module docstring above.
_LOADER_MODULE_FILES = ("stages.py", "transport.py")

# sha256 of each loader module, STAMPED INTO THE STAGED COPY by
# build_repl.stage_bootstrap(). The source tree deliberately ships this empty:
# an empty dict is not "no pinning configured", it is a hard failure (see
# _bootstrap_loader_modules), so a tree served straight from source rather than
# from a real build cannot silently run unverified loader code.
#
# WHY THE VALUES CANNOT COME FROM manifest.json: transport.py is what fetches
# and verifies the manifest, and it is one of the two files being bootstrapped
# here. The manifest cannot vouch for its own fetcher. Stamping is the only
# place the expectation can live that is earlier than the thing it checks.
#
# The line below is rewritten wholesale on every stage, so stamping is
# idempotent and a stale value cannot survive a rebuild.
_LOADER_MODULE_SHA256 = {}  # PRAXIS-LOADER-SHA-INJECT


def _bootstrap_loader_modules(host_root: str) -> None:
    """Fetch ``stages.py`` and ``transport.py`` themselves and make them
    importable, before anything else in this file runs.

    Cannot use ``transport.sync_fetch`` -- that function lives in one of the
    two files this bootstraps -- so this does the minimal synchronous XHR
    fetch inline. If THIS fails, there is no taxonomy loaded yet to raise a
    typed error with; it raises a bare ``RuntimeError`` and lets ``js`` do
    the console logging, which is the only fail-closed option available at
    this exact point (``praxis:ready`` still never gets posted, because
    ``praxis_main``'s caller never reaches that far).
    """
    import js

    for filename in _LOADER_MODULE_FILES:
        url = f"{host_root}bootstrap/{filename}"
        xhr = js.XMLHttpRequest.new()
        xhr.open("GET", url, False)
        xhr.send(None)
        if xhr.status != 200:
            js.console.error(f"[Bootstrap] failed to fetch {filename} from {url}: HTTP {xhr.status}")
            raise RuntimeError(f"failed to fetch loader module {filename!r}: HTTP {xhr.status}")

        body = str(xhr.responseText)

        # Integrity gate. These two files are executed as code, and they run
        # BEFORE D1 (the shell praxis_git_sha handshake) and D2 (manifest source
        # verification) exist to check anything -- transport.py IS D2's fetch
        # loop. Until this pin landed, `status != 200` was the only thing
        # standing between the kernel and arbitrary substituted loader code.
        #
        # Hashing convention matches D2's exactly (transport.fetch_sources):
        # sha256 over text.encode("utf-8"), compared against a hash the build
        # computed over the file's bytes.
        expected = _LOADER_MODULE_SHA256.get(filename)
        if not expected:
            js.console.error(f"[Bootstrap] no pinned sha256 for {filename}")
            raise RuntimeError(
                f"no pinned sha256 for loader module {filename!r}. The staged copy "
                "of praxis_bootstrap.py is stamped by build_repl.stage_bootstrap(); "
                "an unstamped copy means this site is being served from the source "
                "tree rather than a real build. Refusing to execute unverified "
                "loader code."
            )
        actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
        if actual != expected:
            js.console.error(f"[Bootstrap] sha256 mismatch for {filename}")
            raise RuntimeError(
                f"loader module sha256 mismatch for {filename!r}: pinned {expected}, "
                f"fetched {actual}. Refusing to execute. Usual cause: dist/ was "
                "rebuilt from a different source tree than the one that stamped "
                "this bootstrap; a rebuild restamps both."
            )

        with open(filename, "w") as f:
            f.write(body)

    importlib.invalidate_caches()


def _check_wheel_drift(wheel_entry: dict, stages_mod) -> None:
    """D2 for the wheels array: compare the manifest's recorded
    ``source_sha`` for a package against that same package's own installed
    ``_praxis_build_info.PLR_SOURCE_SHA`` (written by ``build_wheels.py``'s
    ``write_build_info()`` and read the same way ``build_manifest.py``'s
    ``_extract_source_sha()`` reads it from the built wheel). Reading it back
    off the just-installed package, rather than re-fetching and re-hashing
    the ``.whl`` bytes over a synchronous XHR, avoids the browser's
    synchronous-XHR binary-response restriction entirely and reuses the
    exact mechanism the manifest generator already trusts.

    ``source_sha: null`` (e.g. pylibftdi, whose provenance is genuinely
    unknown -- wheel spec OQ-6) means "nothing to compare"; skipped, not an
    error.
    """
    expected = wheel_entry.get("source_sha")
    if expected is None:
        return
    package = wheel_entry["package"]
    try:
        build_info = importlib.import_module(f"{package}._praxis_build_info")
        actual = build_info.PLR_SOURCE_SHA
    except (ImportError, AttributeError) as exc:
        raise stages_mod.PraxisDriftError(
            f"D2 wheel source drift: manifest declares source_sha={expected!r} "
            f"for {package!r} but the installed wheel has no readable "
            f"_praxis_build_info.PLR_SOURCE_SHA ({exc})"
        ) from exc
    if actual != expected:
        raise stages_mod.PraxisDriftError(
            f"D2 wheel source drift: {package} manifest source_sha={expected!r} "
            f"!= installed PLR_SOURCE_SHA={actual!r}"
        )


def _import_resources() -> None:
    """Spray every public name in ``pylabrobot.resources`` onto builtins, so
    a REPL cell can write bare ``Plate(...)`` / ``Deck(...)`` / etc. Ported
    unchanged from the old bootstrap -- the REPL's user-facing contract
    (U15) depends on this and nothing in this task's scope changes it.
    """
    import pylabrobot.resources as _res

    for name in dir(_res):
        if not name.startswith("_"):
            setattr(builtins, name, getattr(_res, name))


def _setup_broadcast_listener(channel) -> None:
    """Install the long-lived ``praxis:execute`` / ``praxis:interaction_response``
    handler on *channel*, replacing whatever handler the D1 handshake left
    on it. Ported unchanged in behavior from the old bootstrap's
    ``_setup_broadcast_listener`` / ``_handle_message`` -- not one of this
    task's five required changes, so its echo-and-exec semantics for
    injected REPL code are preserved exactly.
    """
    import js

    def _handle_message(event):
        try:
            data = event.data
            if hasattr(data, "to_py"):
                data = data.to_py()
            if not isinstance(data, dict):
                return

            msg_type = data.get("type", "")

            if msg_type == "praxis:execute":
                code = data.get("code", "")
                label = data.get("label", "")

                if code.strip():
                    var_name = ""
                    for line in code.split("\n"):
                        stripped = line.strip()
                        if (
                            "=" in stripped
                            and not stripped.startswith("#")
                            and not stripped.startswith("from ")
                            and not stripped.startswith("import ")
                            and not stripped.startswith("await ")
                            and not stripped.startswith("print")
                        ):
                            var_name = stripped.split("=")[0].strip()
                            if var_name and var_name.isidentifier():
                                break
                            var_name = ""
                    header = f"[Praxis] Injected: {label or var_name or 'code'}"
                    print(f"\n{'-' * 50}")
                    print(f"  {header}")
                    print(f"{'-' * 50}")
                    print(code)
                    print(f"{'-' * 50}\n")

                try:
                    if "await " in code:
                        import asyncio

                        async def _run_async():
                            try:
                                indented = "\n".join("    " + l for l in code.split("\n"))
                                wrapper = f"async def __praxis_async_exec__():\n{indented}"
                                exec(wrapper, globals())
                                result = await globals()["__praxis_async_exec__"]()
                                if result is not None:
                                    print(result)
                            except Exception:
                                import traceback

                                traceback.print_exc()

                        asyncio.ensure_future(_run_async())
                    else:
                        exec(code, globals())
                except Exception:
                    import traceback

                    traceback.print_exc()

            elif msg_type == "praxis:interaction_response":
                try:
                    import web_bridge

                    web_bridge.handle_interaction_response(data.get("id"), data.get("value"))
                except Exception as e:
                    js.console.error(f"[Bootstrap] interaction_response error: {e}")

        except Exception as e:
            js.console.error(f"[Bootstrap] Message handler error: {e}")

    channel.onmessage = _handle_message

    try:
        import web_bridge

        web_bridge.register_broadcast_channel(channel)
    except Exception:
        pass

    globals()["_praxis_channel"] = channel


async def praxis_main(host_root: str, *, raise_on_error: bool = False) -> None:
    """The ordered fail-closed stage ledger. Every stage after the two-file
    self-bootstrap runs inside the single ``try`` below; ANY exception
    there -- typed (``PraxisBootError`` and subclasses) or not -- is caught
    once, broadcast as ``praxis:error``, and stops the function before the
    ``praxis:ready`` post at the bottom of the ``try`` body is ever reached.
    """
    import js

    # Once-guard: if already run successfully in this kernel, skip stages and
    # re-post ready. The flag is set only after ALL stages pass; a failed
    # sequence leaves it unset, so a retry re-runs the stages.
    if getattr(builtins, "_PRAXIS_BOOT_DONE", False):
        js.console.log("[Bootstrap] already bootstrapped in this kernel; skipping")
        try:
            channel = js.BroadcastChannel.new("praxis_repl")
        except Exception:
            channel = js.BroadcastChannel("praxis_repl")

        def _post(msg: dict) -> None:
            channel.postMessage(js.Object.fromEntries(list(msg.items())))

        _post({"type": "praxis:ready"})
        return

    try:
        channel = js.BroadcastChannel.new("praxis_repl")
    except Exception:
        channel = js.BroadcastChannel("praxis_repl")

    def _post(msg: dict) -> None:
        channel.postMessage(js.Object.fromEntries(list(msg.items())))

    def _register_shell_pong_handler(cb) -> None:
        def _on_message(event):
            data = event.data
            if hasattr(data, "to_py"):
                data = data.to_py()
            cb(data)

        channel.onmessage = _on_message

    try:
        js.console.log(f"[Bootstrap] Starting with host_root: {host_root}")

        # 1. Make the taxonomy + fetch/D1 machinery importable. Everything
        #    below can now raise a properly-typed PraxisBootError.
        _bootstrap_loader_modules(host_root)
        import stages
        import transport

        def _xhr_new():
            return js.XMLHttpRequest.new()

        # 2. D2: fetch + parse manifest.json (fail closed on 404 / bad JSON).
        manifest = transport.fetch_manifest(host_root, _xhr_new)

        # 3. D1: shell-ping/pong, then compare praxis_git_sha (fail closed).
        shell_sha = await transport.shell_ping(
            _register_shell_pong_handler, _post, expected_sha=manifest["praxis_git_sha"]
        )
        stages.assert_praxis_git_sha(manifest["praxis_git_sha"], shell_sha)

        # 4. D2: fetch every manifest-listed source, verify sha256, write to
        #    VFS -- replaces the seven hardcoded fetch literals.
        transport.fetch_sources(manifest, host_root, _xhr_new)
        importlib.invalidate_caches()

        # 5. R-ID: import each shim exactly once, staple onto builtins.
        builtins.WebSerial = stages.import_shim_class("web_serial_shim", "WebSerial")
        builtins.WebUSB = stages.import_shim_class("web_usb_shim", "WebUSB")
        builtins.WebHID = stages.import_shim_class("web_hid_shim", "WebHID")
        builtins.WebFTDI = stages.import_shim_class("web_ftdi_shim", "WebFTDI")

        # 6. Install native stubs BEFORE any `import pylabrobot`.
        stages.install_native_stubs(web_serial_cls=builtins.WebSerial)

        # 7. Install wheels from manifest-listed filenames, verify D2 drift.
        import micropip

        # Install ALL wheels before checking ANY of them. _check_wheel_drift
        # imports the installed distribution to read its build info, and an
        # interleaved check imports pylabrobot.io.ftdi while the pylibftdi
        # wheel is still uninstalled (manifest order is alphabetical, so
        # pylabrobot comes first). PLR's `try: import pylibftdi.driver` then
        # fails and HAS_PYLIBFTDI=False is latched permanently in the cached
        # module -- making every FTDI-backed machine unusable in the REPL.
        for wheel_entry in manifest["wheels"]:
            wheel_url = f"{host_root}assets/wheels/{wheel_entry['filename']}"
            await micropip.install(wheel_url, deps=False)
        for wheel_entry in manifest["wheels"]:
            _check_wheel_drift(wheel_entry, stages)

        # 8. Patch pylabrobot.io from the shims (cheap post-write consistency
        #    check only -- see step 12 for the actual R-ID enforcement point).
        stages.apply()

        # 9. REPL ergonomics: spray pylabrobot.resources onto builtins.
        _import_resources()

        # 10. web_bridge: stdout redirect stays guarded; shim re-injection
        #     is deleted (ADR Sec 2.2 -- see web_bridge.py's own comment).
        builtins._PRAXIS_JUPYTERLITE = True
        import web_bridge

        web_bridge.bootstrap_playground(globals())

        # 11. Take over the channel for praxis:execute / interaction_response.
        _setup_broadcast_listener(channel)

        # 12. R-ID enforcement point (ADR SS2.2): assert-only, no setattr.
        #     Must run here -- AFTER web_bridge.bootstrap_playground() (step
        #     10), the one place a builtins.Web* name could still get rebound
        #     -- not right after stages.apply() (step 8), where a post-write
        #     assert on stages.apply()'s own setattr is vacuous by
        #     construction. This is the only position where the check is
        #     non-vacuous; see stages.verify_identity()'s docstring.
        stages.verify_identity()

        js.console.log("[Bootstrap] All stages passed")
        # Set the once-guard flag ONLY after all stages pass, so a failed
        # sequence leaves it unset and a retry re-runs the stages.
        builtins._PRAXIS_BOOT_DONE = True
        _post({"type": "praxis:ready"})

    except Exception as exc:  # noqa: BLE001 -- fail-closed catch-all, by design
        import traceback

        js.console.error(f"[Bootstrap] FAILED: {exc}")
        traceback.print_exc()
        _post({"type": "praxis:error", "reason": str(exc)})
        if raise_on_error:
            raise
