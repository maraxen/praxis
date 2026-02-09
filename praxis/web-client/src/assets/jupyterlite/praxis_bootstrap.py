"""
Praxis JupyterLite Bootstrap (Phase 2 — Complete)
Self-contained: fetches shims, bridge, packages, installs wheels,
patches IO modules, imports resources, sets up BroadcastChannel listener.
Fully synchronous where possible; uses run_until_complete for async micropip.
Called by the minimal URL bootstrap which passes host_root.
"""
import os
import sys
import builtins
import importlib


def _sync_fetch(url):
    """Fetch a URL synchronously using XMLHttpRequest (works in web workers)."""
    import js
    xhr = js.XMLHttpRequest.new()
    xhr.open('GET', url, False)  # False = synchronous
    xhr.send(None)
    if xhr.status == 200:
        return str(xhr.responseText)
    return None


def _install_wheels(host_root):
    """Install PyLabRobot and pylibftdi wheels via micropip.
    
    micropip.install() is async, but we're in a sync context.
    In Pyodide/JupyterLite, we use the running webloop's event loop.
    """
    import micropip
    import asyncio

    plr_url = f'{host_root}assets/wheels/pylabrobot-0.1.6-py3-none-any.whl'
    ftdi_url = f'{host_root}assets/wheels/pylibftdi-0.0.0-py3-none-any.whl'

    async def _do_install():
        await micropip.install(plr_url, deps=False)
        await micropip.install(ftdi_url, deps=False)

    # In Pyodide, there's a running event loop we can use
    try:
        loop = asyncio.get_running_loop()
        # We're inside a running loop — use run_until_complete won't work.
        # Instead, use Pyodide's synchronous eval for async code.
        import pyodide.code
        pyodide.code.run_sync(
            f"import micropip; await micropip.install('{plr_url}', deps=False)"
        )
        pyodide.code.run_sync(
            f"import micropip; await micropip.install('{ftdi_url}', deps=False)"
        )
    except RuntimeError:
        # No running loop — create one (testing/non-Pyodide context)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_do_install())
        loop.close()


def _mock_native_deps():
    """Mock native dependencies that aren't available in the browser."""
    from unittest.mock import MagicMock

    for mod_name in [
        'ssl', 'usb', 'usb.core', 'usb.util',
        'serial', 'serial.tools', 'serial.tools.list_ports',
    ]:
        if mod_name not in sys.modules:
            sys.modules[mod_name] = MagicMock()


def _patch_io_modules():
    """Patch pylabrobot.io modules to use browser shims from builtins."""
    import pylabrobot.io.serial as _ser
    import pylabrobot.io.usb as _usb
    import pylabrobot.io.ftdi as _ftdi

    if hasattr(builtins, 'WebSerial'):
        _ser.Serial = builtins.WebSerial
    if hasattr(builtins, 'WebUSB'):
        _usb.USB = builtins.WebUSB
    if hasattr(builtins, 'WebFTDI'):
        _ftdi.FTDI = builtins.WebFTDI
        _ftdi.HAS_PYLIBFTDI = True

    try:
        import pylabrobot.io.hid as _hid
        if hasattr(builtins, 'WebHID'):
            _hid.HID = builtins.WebHID
    except Exception:
        pass


def _import_resources():
    """Import all pylabrobot resources into builtins for REPL access."""
    import pylabrobot
    import pylabrobot.resources as _res

    # Make all non-private names available
    for name in dir(_res):
        if not name.startswith('_'):
            setattr(builtins, name, getattr(_res, name))


def _setup_broadcast_listener():
    """Set up BroadcastChannel listener for praxis:execute and interaction_response."""
    import js
    import asyncio

    channel_name = 'praxis_repl'

    try:
        ch = js.BroadcastChannel.new(channel_name)
    except Exception:
        ch = js.BroadcastChannel(channel_name)

    def _handle_message(event):
        try:
            data = event.data
            # Convert JsProxy to Python dict if needed
            if hasattr(data, 'to_py'):
                data = data.to_py()

            if not isinstance(data, dict):
                return

            msg_type = data.get('type', '')

            if msg_type == 'praxis:execute':
                code = data.get('code', '')
                try:
                    if 'await ' in code:
                        # Wrap async code
                        async def _run_async():
                            try:
                                indented = '\n'.join('    ' + l for l in code.split('\n'))
                                wrapper = f"async def __praxis_async_exec__():\n{indented}"
                                exec(wrapper, globals())
                                result = await globals()['__praxis_async_exec__']()
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

            elif msg_type == 'praxis:interaction_response':
                try:
                    import web_bridge
                    web_bridge.handle_interaction_response(
                        data.get('id'), data.get('value')
                    )
                except Exception as e:
                    js.console.error(f'[Bootstrap] interaction_response error: {e}')

        except Exception as e:
            js.console.error(f'[Bootstrap] Message handler error: {e}')

    ch.onmessage = _handle_message

    # Also register channel with web_bridge for outgoing messages
    try:
        import web_bridge
        web_bridge.register_broadcast_channel(ch)
    except Exception:
        pass

    # Store channel reference globally
    globals()['_praxis_channel'] = ch


def praxis_main(host_root):
    """Full bootstrap: fetch files, install wheels, patch IO, import resources, listen."""
    import js

    js.console.log(f'[Bootstrap] Starting with host_root: {host_root}')

    # --- 1. Define files to fetch ---
    shims = {
        'web_serial_shim.py': ('WebSerial', f'{host_root}assets/shims/web_serial_shim.py'),
        'web_usb_shim.py': ('WebUSB', f'{host_root}assets/shims/web_usb_shim.py'),
        'web_ftdi_shim.py': ('WebFTDI', f'{host_root}assets/shims/web_ftdi_shim.py'),
        'web_hid_shim.py': ('WebHID', f'{host_root}assets/shims/web_hid_shim.py'),
    }
    other_files = {
        'web_bridge.py': f'{host_root}assets/python/web_bridge.py',
        'praxis/__init__.py': f'{host_root}assets/python/praxis/__init__.py',
        'praxis/interactive.py': f'{host_root}assets/python/praxis/interactive.py',
    }

    # --- 2. Fetch all files ---
    all_urls = {}
    all_urls.update({k: v[1] for k, v in shims.items()})
    all_urls.update(other_files)

    fetched = {}
    for filename, url in all_urls.items():
        try:
            code = _sync_fetch(url)
            if code:
                fetched[filename] = code
                js.console.log(f'[Bootstrap] \u2713 Fetched {filename}')
            else:
                js.console.warn(f'[Bootstrap] \u2717 {filename}: fetch failed')
        except Exception as e:
            js.console.warn(f'[Bootstrap] \u2717 {filename}: {e}')

    # --- 3. Write files to Pyodide VFS ---
    for path, code in fetched.items():
        try:
            d = os.path.dirname(path)
            if d and not os.path.exists(d):
                os.makedirs(d)
            with open(path, 'w') as f:
                f.write(code)
        except Exception as e:
            js.console.warn(f'[Bootstrap] Failed to write {path}: {e}')

    importlib.invalidate_caches()

    # --- 4. Inject shims into builtins ---
    for filename, (shim_name, _url) in shims.items():
        if filename in fetched:
            try:
                ns = {}
                exec(fetched[filename], ns)
                if shim_name in ns:
                    setattr(builtins, shim_name, ns[shim_name])
                    js.console.log(f'[Bootstrap] \u2713 {shim_name} injected into builtins')
            except Exception as e:
                js.console.warn(f'[Bootstrap] Failed to inject {shim_name}: {e}')

    # --- 5. Install wheels ---
    try:
        js.console.log('[Bootstrap] Installing PyLabRobot wheel...')
        _install_wheels(host_root)
        js.console.log('[Bootstrap] \u2713 Wheels installed')
    except Exception as e:
        js.console.error(f'[Bootstrap] Wheel install failed: {e}')
        import traceback
        traceback.print_exc()

    # --- 6. Mock native deps ---
    _mock_native_deps()
    js.console.log('[Bootstrap] \u2713 Native deps mocked')

    # --- 7. Patch IO modules ---
    try:
        _patch_io_modules()
        js.console.log('[Bootstrap] \u2713 IO modules patched')
    except Exception as e:
        js.console.warn(f'[Bootstrap] IO patch failed: {e}')

    # --- 8. Import resources ---
    try:
        _import_resources()
        js.console.log('[Bootstrap] \u2713 PyLabRobot resources imported')
    except Exception as e:
        js.console.warn(f'[Bootstrap] Resource import failed: {e}')

    # --- 9. Import web_bridge and bootstrap playground ---
    if 'web_bridge.py' in fetched:
        try:
            import web_bridge
            web_bridge.bootstrap_playground(globals())
            js.console.log('[Bootstrap] \u2713 web_bridge.bootstrap_playground() done')
        except Exception as e:
            js.console.error(f'[Bootstrap] Failed web_bridge bootstrap: {e}')

    # --- 10. Set up BroadcastChannel listener ---
    try:
        _setup_broadcast_listener()
        js.console.log('[Bootstrap] \u2713 BroadcastChannel listener active')
    except Exception as e:
        js.console.error(f'[Bootstrap] Channel listener failed: {e}')

    # --- 11. Signal ready via BroadcastChannel ---
    try:
        ch = js.BroadcastChannel.new('praxis_repl')
        msg = js.Object.fromEntries([['type', 'praxis:ready']])
        ch.postMessage(msg)
        js.console.log('[Bootstrap] \u2713 Praxis bootstrap complete, ready signal sent')
    except Exception as e:
        js.console.error(f'[Bootstrap] Failed to signal ready: {e}')
