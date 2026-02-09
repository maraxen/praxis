"""
Praxis JupyterLite Bootstrap (Phase 2)
Self-contained: fetches its own shims, bridge, and packages from the server.
Fully synchronous — uses XMLHttpRequest, no async/await needed.
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


def praxis_main(host_root: str):
    """Full bootstrap: fetch files, write to VFS, inject shims, signal ready."""
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

    # --- 5. Import web_bridge ---
    if 'web_bridge.py' in fetched:
        try:
            import web_bridge
            js.console.log('[Bootstrap] \u2713 web_bridge imported')
        except Exception as e:
            js.console.error(f'[Bootstrap] Failed to import web_bridge: {e}')

    # --- 6. Signal ready via BroadcastChannel ---
    try:
        ch = js.BroadcastChannel.new('praxis_repl')
        msg = js.Object.fromEntries([['type', 'praxis:ready']])
        ch.postMessage(msg)
        js.console.log('[Bootstrap] \u2713 Praxis bootstrap complete, ready signal sent')
    except Exception as e:
        js.console.error(f'[Bootstrap] Failed to signal ready: {e}')
