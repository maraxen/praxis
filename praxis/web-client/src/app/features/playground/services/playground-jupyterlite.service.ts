import { Injectable, signal, inject, effect } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { AppStore } from '@core/store/app.store';
import { InteractionService } from '@core/services/interaction.service';
import { PyodideSnapshotService } from '@core/services/pyodide-snapshot.service';
import { PathUtils } from '@core/utils/path.utils';
import { PyodideSnapshotService } from './pyodide-snapshot.service';

const JUPYTERLITE_SNAPSHOT_KEY = 'pyodide-jupyterlite';

@Injectable({
  providedIn: 'root'
})
export class PlaygroundJupyterliteService {
  private sanitizer = inject(DomSanitizer);
  private store = inject(AppStore);
  private interactionService = inject(InteractionService);
  private snapshotService = inject(PyodideSnapshotService);

  // JupyterLite Iframe Configuration
  jupyterliteUrl = signal<SafeResourceUrl | undefined>(undefined);
  isLoading = signal(true);
  loadingError = signal(false);
  private currentTheme = '';
  private loadingTimeout: ReturnType<typeof setTimeout> | undefined;
  private replChannel: BroadcastChannel | null = null;

  constructor() {
    effect(() => {
      const theme = this.store.theme();
      this.updateJupyterliteTheme(theme);
    });
  }

  public initialize(): void {
    this.setupReadyListener();
    this.buildJupyterliteUrl();
  }

  public reloadNotebook(): void {
    this.jupyterliteUrl.set(undefined);
    setTimeout(() => {
      this.buildJupyterliteUrl();
    }, 100);
  }

  public destroy(): void {
    if (this.replChannel) {
      this.replChannel.close();
      this.replChannel = null;
    }
    if (this.loadingTimeout) {
      clearTimeout(this.loadingTimeout);
    }
  }

  private setupReadyListener(): void {
    if (this.replChannel) {
      this.replChannel.close();
    }

    this.replChannel = new BroadcastChannel('praxis_repl');
    this.replChannel.onmessage = async (event) => {
      const data = event.data;
      if (data?.type === 'praxis:ready') {
        console.log('[REPL] Received kernel ready signal');
        this.isLoading.set(false);
        if (this.loadingTimeout) {
          clearTimeout(this.loadingTimeout);
          this.loadingTimeout = undefined;
        }
      } else if (data?.type === 'USER_INTERACTION') {
        console.log('[REPL] USER_INTERACTION received via BroadcastChannel:', data.payload);
        this.handleUserInteraction(data.payload);
      } else if (data?.type === 'praxis:snapshot_query') {
        console.log('[Pyodide] Received snapshot query');
        const snapshot = await this.snapshotService.getSnapshot();
        if (snapshot) {
            console.log('[Pyodide] Sending snapshot to iframe');
            const postLoadCode = this.getPostLoadCode();
            this.replChannel?.postMessage({
                type: 'praxis:snapshot_load',
                payload: snapshot,
                post_load_code: postLoadCode,
            });
        } else {
            console.log('[Pyodide] No snapshot found. Sending full bootstrap.');
            const bootstrapCode = await this.getOptimizedBootstrap();
            this.replChannel?.postMessage({ type: 'praxis:bootstrap', code: bootstrapCode });
        }
      } else if (data?.type === 'praxis:save_snapshot') {
          console.log('[Pyodide] Received snapshot to save');
          await this.snapshotService.saveSnapshot(data.payload);
          console.log('[Pyodide] Snapshot saved for future fast-start');
      } else if (data?.type === 'praxis:snapshot_query_failed') {
        // This can happen if snapshot is corrupted
        console.warn('[Pyodide] Snapshot restore failed, doing fresh init from iframe request');
        await this.snapshotService.invalidateSnapshot();
        const bootstrapCode = await this.getOptimizedBootstrap();
        this.replChannel?.postMessage({ type: 'praxis:bootstrap', code: bootstrapCode });
    }
    };
  }

  private async handleUserInteraction(payload: any): Promise<void> {
    console.log('[REPL] Opening interaction dialog:', payload.interaction_type);
    const result = await this.interactionService.handleInteraction({
      interaction_type: payload.interaction_type,
      payload: payload.payload
    });

    console.log('[REPL] Interaction result obtained:', result);

    if (this.replChannel) {
      this.replChannel.postMessage({
        type: 'praxis:interaction_response',
        id: payload.id,
        value: result
      });
    }
  }

  private getIsDarkMode(): boolean {
    return document.body.classList.contains('dark-theme');
  }

  public getMinimalBootstrap(): string {
    return `
import js
from pyodide.ffi import to_js
import pyodide_js
import asyncio

_praxis_initialized = False

async def _praxis_boot_handler(event):
    global _praxis_initialized
    if _praxis_initialized:
        print("PRAXIS: Already initialized, ignoring message.")
        return

    data = event.data
    if hasattr(data, "to_py"):
        data = data.to_py()

    if isinstance(data, dict) and data.get("type") == "praxis:snapshot_load":
        print("PRAXIS: Receiving snapshot...")
        try:
            await pyodide_js.loadSnapshot(data.get("payload"))
            exec(data.get("post_load_code"), globals())
            _praxis_initialized = True
            print("PRAXIS: Snapshot restored.")
            if '_praxis_channel' in globals():
                globals()['_praxis_channel'].postMessage(to_js({"type": "praxis:ready"}, dict_converter=js.Object.fromEntries))
                print("PRAXIS: Re-sent ready signal from snapshot.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"PRAXIS: Snapshot load failed: {e}. Requesting full bootstrap.")
            _praxis_boot_channel.postMessage(to_js({"type": "praxis:snapshot_query_failed"}, dict_converter=js.Object.fromEntries))

    elif isinstance(data, dict) and data.get("type") == "praxis:bootstrap":
        print("PRAXIS: Receiving full bootstrap...")
        try:
            exec(data.get("code"), globals())
            _praxis_initialized = True
            print("PRAXIS: Full bootstrap complete. Creating snapshot...")
            snapshot = await pyodide_js.dumpSnapshot()
            if '_praxis_channel' in globals():
                globals()['_praxis_channel'].postMessage(to_js({"type": "praxis:save_snapshot", "payload": snapshot}, dict_converter=js.Object.fromEntries))
                print("PRAXIS: Snapshot sent to host for saving.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"PRAXIS: Bootstrap failed: {e}")

def _main_boot():
    if hasattr(js, "BroadcastChannel"):
        global _praxis_boot_channel
        _praxis_boot_channel = js.BroadcastChannel.new("praxis_repl")
        def message_wrapper(event):
            asyncio.ensure_future(_praxis_boot_handler(event))
        _praxis_boot_channel.onmessage = message_wrapper
        _praxis_boot_channel.postMessage(to_js({"type": "praxis:snapshot_query"}, dict_converter=js.Object.fromEntries))
        print("PRAXIS: Minimal bootstrap ready, querying for snapshot...")
    else:
        print("PRAXIS: Critical - BroadcastChannel missing")

_main_boot()
`.trim();
  }

  private async buildJupyterliteUrl(): Promise<void> {
    if (this.loadingTimeout) {
      clearTimeout(this.loadingTimeout);
    }

    this.isLoading.set(true);
    this.loadingError.set(false);
    this.jupyterliteUrl.set(undefined);

    const isDark = this.getIsDarkMode();
    this.currentTheme = isDark ? 'dark' : 'light';

    // AUDIT-07: Use minimal bootstrap to avoid URL length limits
    // The full bootstrap will be injected via BroadcastChannel
    const bootstrapCode = this.getMinimalBootstrap();

    console.log('[REPL] Building JupyterLite URL. Calculated isDark:', isDark, 'Effective Theme Class:', this.currentTheme);

    const baseUrl = './assets/jupyterlite/repl/index.html';
    const params = new URLSearchParams({
      kernel: 'python',
      toolbar: '1',
      theme: isDark ? 'JupyterLab Dark' : 'JupyterLab Light',
    });

    if (bootstrapCode) {
      params.set('code', bootstrapCode);
    }

    const fullUrl = `${baseUrl}?${params.toString()}`;
    this.jupyterliteUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(fullUrl));

    this.loadingTimeout = setTimeout(() => {
      if (this.isLoading()) {
        console.warn('[REPL] Loading timeout (30s) reached');
        this.isLoading.set(false);
      }
    }, 30000);
  }

  private async updateJupyterliteTheme(_: string): Promise<void> {
    const isDark = this.getIsDarkMode();
    const newTheme = isDark ? 'dark' : 'light';

    if (this.currentTheme !== newTheme) {
      console.log('[REPL] Theme changed from', this.currentTheme, 'to', newTheme, '- rebuilding URL');
      this.currentTheme = newTheme;
      await this.buildJupyterliteUrl();
    }
  }
  public async getOptimizedBootstrap(): Promise<string> {
    const shims = ['web_serial_shim.py', 'web_usb_shim.py', 'web_ftdi_shim.py'];
    const hostRoot = this.calculateHostRoot();

    let shimInjections = `# --- Host Root (injected from Angular) --- \n`;
    shimInjections += `PRAXIS_HOST_ROOT = "${hostRoot}"\n`;
    shimInjections += 'print(f"PylibPraxis: Using Host Root: {PRAXIS_HOST_ROOT}")\n\n';
    shimInjections += '# --- Browser Hardware Shims --- \n';
    shimInjections += 'import pyodide.http\n';

    for (const shim of shims) {
      shimInjections += `
print("PylibPraxis: Loading ${shim}...")
try:
    _shim_code = await (await pyodide.http.pyfetch(f'{PRAXIS_HOST_ROOT}assets/shims/${shim}')).string()
    exec(_shim_code, globals())
    print("PylibPraxis: Loaded ${shim}")
except Exception as e:
    print(f"PylibPraxis: Failed to load ${shim}: {e}")
`;
    }

    shimInjections += `
print("PylibPraxis: Loading web_bridge.py...")
try:
    _bridge_code = await (await pyodide.http.pyfetch(f'{PRAXIS_HOST_ROOT}assets/python/web_bridge.py')).string()
    with open('web_bridge.py', 'w') as f:
        f.write(_bridge_code)
    print("PylibPraxis: Loaded web_bridge.py")
except Exception as e:
    print(f"PylibPraxis: Failed to load web_bridge.py: {e}")

import os
if not os.path.exists('praxis'):
    os.makedirs('praxis')
    
for _p_file in ['__init__.py', 'interactive.py']:
    try:
        print(f"PylibPraxis: Loading praxis/{_p_file}...")
        _p_code = await (await pyodide.http.pyfetch(f'{PRAXIS_HOST_ROOT}assets/python/praxis/{_p_file}')).string()
        with open(f'praxis/{_p_file}', 'w') as f:
            f.write(_p_code)
        print(f"PylibPraxis: Loaded praxis/{_p_file}")
    except Exception as e:
        print(f"PylibPraxis: Failed to load praxis/{_p_file}: {e}")
`;

    const baseBootstrap = this.generateBootstrapCode();
    return shimInjections + '\n' + baseBootstrap;
  }

  private getPostLoadCode(): string {
    const lines = [
      '# Message listener for asset injection via BroadcastChannel',
      '# We use BroadcastChannel because it works across Window/Worker contexts',
      'import js',
      'import json',
      '',
      'def _praxis_message_handler(event):',
      '    try:',
      '        data = event.data',
      '        # Convert JsProxy to dict if needed',
      '        if hasattr(data, "to_py"):',
      '            data = data.to_py()',
      '        ',
      '        if isinstance(data, dict) and data.get("type") == "praxis:execute":',
      '            code = data.get("code", "")',
      '            print(f"Executing: {code}")',
      '            # Handle async code (contains await)',
      '            if "await " in code:',
      '                import asyncio',
      '                # Wrap in async function and schedule',
      '                async def _run_async():',
      '                    exec(f"async def __praxis_async__(): return {code}", globals())',
      '                    result = await __praxis_async__()',
      '                    if result is not None:',
      '                        print(result)',
      '                asyncio.ensure_future(_run_async())',
      '            else:',
      '                exec(code, globals())',
      '        elif isinstance(data, dict) and data.get("type") == "praxis:interaction_response":',
      '            try:',
      '                import web_bridge',
      '                web_bridge.handle_interaction_response(data.get("id"), data.get("value"))',
      '            except ImportError:',
      '                print("! web_bridge not found for interaction response")',
      '    except Exception as e:',
      '        import traceback',
      '        print(f"Error executing injected code: {e}")',
      '        print(traceback.format_exc())',
      '',
      '# Setup BroadcastChannel',
      'try:',
      '    if hasattr(js, "BroadcastChannel"):',
      '        # Try .new() first (Pyodide convention)',
      '        if hasattr(js.BroadcastChannel, "new"):',
      '            _praxis_channel = js.BroadcastChannel.new("praxis_repl")',
      '        else:',
      '            # Fallback to direct constructor',
      '            _praxis_channel = js.BroadcastChannel("praxis_repl")',
      '        ',
      '        _praxis_channel.onmessage = _praxis_message_handler',
      '        ',
      '        # Register channel with web_bridge for interactive protocols',
      '        try:',
      '            import web_bridge',
      '            web_bridge.register_broadcast_channel(_praxis_channel)',
      '            print("✓ Interactive protocols enabled (channel registered)")',
      '        except ImportError:',
      '            print("! web_bridge not available for channel registration")',
      '        ',
      '        print("✓ Asset injection ready (channel created)")',
      '    else:',
      '        print("! BroadcastChannel not available")',
      'except Exception as e:',
      '    print(f"! Failed to setup injection channel: {e}")',
      '',
      '# Send ready signal to Angular host',
      'try:',
      '    # Must convert dict to JS Object for structured clone in BroadcastChannel',
      '    from pyodide.ffi import to_js',
      '    ready_msg = to_js({"type": "praxis:ready"}, dict_converter=js.Object.fromEntries)',
      '    _praxis_channel.postMessage(ready_msg)',
      '    print("✓ Ready signal sent")',
      'except Exception as e:',
      '    print(f"! Ready signal failed: {e}")',
    ];
    return lines.join('\n');
  }

  private generateBootstrapCode(): string {
    const lines = [
      '# PyLabRobot Interactive Notebook',
      '# Installing pylabrobot from local wheel...',
      'import micropip',
      'await micropip.install(f"{PRAXIS_HOST_ROOT}assets/wheels/pylabrobot-0.1.6-py3-none-any.whl")',
      '',
      '# Ensure WebSerial, WebUSB, and WebFTDI are in builtins for all cells',
      'import builtins',
      'if "WebSerial" in globals():',
      '    builtins.WebSerial = WebSerial',
      'if "WebUSB" in globals():',
      '    builtins.WebUSB = WebUSB',
      'if "WebFTDI" in globals():',
      '    builtins.WebFTDI = WebFTDI',
      '',
      '# Mock pylibftdi (not supported in browser/Pyodide)',
      'import sys',
      'from unittest.mock import MagicMock',
      'sys.modules["pylibftdi"] = MagicMock()',
      '',
      '# Load WebSerial/WebUSB/WebFTDI shims for browser I/O',
      '# Note: These are pre-loaded to avoid extra network requests',
      'try:',
      '    import pyodide_js',
      '    from pyodide.ffi import to_js',
      'except ImportError:',
      '    pass',
      '',
      '# Shims will be injected directly via code to avoid 404s',
      '# Patching is done in the bootstrap below',
      '',
      '# Patch pylabrobot.io to use browser shims',
      'import pylabrobot.io.serial as _ser',
      'import pylabrobot.io.usb as _usb',
      'import pylabrobot.io.ftdi as _ftdi',
      '_ser.Serial = WebSerial',
      '_usb.USB = WebUSB',
      '',
      '# CRITICAL: Patch FTDI for backends like CLARIOstarBackend',
      '_ftdi.FTDI = WebFTDI',
      '_ftdi.HAS_PYLIBFTDI = True',
      'print("✓ Patched pylabrobot.io with WebSerial/WebUSB/WebFTDI")',
      '',
      '# Import pylabrobot',
      'import pylabrobot',
      'from pylabrobot.resources import *',
      '',
      'print("✓ pylabrobot loaded with browser I/O shims (including FTDI)!")',
      'print(f"  Version: {pylabrobot.__version__}")',
      'print("Use the Inventory button to insert asset variables.")',
      '',
    ];

    return lines.join('\n') + this.getPostLoadCode();
  }

  private calculateHostRoot(): string {
    const href = window.location.href;
    const anchor = '/assets/jupyterlite/';

    if (href.includes(anchor)) {
      return href.split(anchor)[0] + '/';
    }

    const baseHref = document.querySelector('base')?.getAttribute('href') || '/';
    const cleanBase = PathUtils.normalizeBaseHref(baseHref);

    return window.location.origin + cleanBase;
  }
}
