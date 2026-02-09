import { Injectable, signal, inject, effect } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { AppStore } from '@core/store/app.store';
import { InteractionService } from '@core/services/interaction.service';
import { PyodideSnapshotService } from '@core/services/pyodide-snapshot.service';
import { PathUtils } from '@core/utils/path.utils';


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
  private processedInteractionIds = new Set<string>();
  private messageListener: ((event: MessageEvent) => void) | null = null;

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
    if (this.messageListener) {
      window.removeEventListener('message', this.messageListener);
      this.messageListener = null;
    }
    if (this.loadingTimeout) {
      clearTimeout(this.loadingTimeout);
    }
  }

  private setupReadyListener(): void {
    if (this.replChannel) {
      this.replChannel.close();
    }
    if (this.messageListener) {
      window.removeEventListener('message', this.messageListener);
    }

    const channelName = 'praxis_repl';
    console.log('[REPL] Setting up BroadcastChannel:', channelName);

    this.replChannel = new BroadcastChannel(channelName);

    const messageHandler = async (data: any) => {
      if (!data) return;

      const type = data.type;
      console.log('[REPL] Processing message type:', type);

      if (type === 'praxis:ready' || type === 'r') {
        console.log('[REPL] Received kernel ready signal');
        this.isLoading.set(false);
        (window as any).__praxis_pyodide_ready = true;
        if (this.loadingTimeout) {
          clearTimeout(this.loadingTimeout);
          this.loadingTimeout = undefined;
        }

        // If it was just the minimal ready ('r'), we need to send the bootstrap
        if (type === 'r') {
          console.log('[REPL] Minimal ready, sending full bootstrap');
          const bootstrapCode = await this.getOptimizedBootstrap();
          this.sendMessageToKernel({ type: 'praxis:bootstrap', code: bootstrapCode });
        }
      } else if (type === 'USER_INTERACTION') {
        console.log('[REPL] USER_INTERACTION received:', data.payload);
        this.handleUserInteraction(data.payload);
      } else if (type === 'praxis:snapshot_query' || type === 'q') {
        console.log('[Pyodide] Received snapshot query');
        const snapshot = await this.snapshotService.getSnapshot();
        if (snapshot) {
          console.log('[Pyodide] Sending snapshot to iframe');
          const postLoadCode = this.getPostLoadCode();
          this.sendMessageToKernel({
            type: 'praxis:snapshot_load',
            payload: snapshot,
            post_load_code: postLoadCode,
          });
        } else {
          console.log('[Pyodide] No snapshot found. Sending full bootstrap.');
          const bootstrapCode = await this.getOptimizedBootstrap();
          this.sendMessageToKernel({ type: 'praxis:bootstrap', code: bootstrapCode });
        }
      } else if (type === 'praxis:save_snapshot') {
        console.log('[Pyodide] Received snapshot to save');
        await this.snapshotService.saveSnapshot(data.payload);
        console.log('[Pyodide] Snapshot saved for future fast-start');
      } else if (type === 'praxis:snapshot_query_failed') {
        console.warn('[Pyodide] Snapshot restore failed, doing fresh init');
        await this.snapshotService.invalidateSnapshot();
        const bootstrapCode = await this.getOptimizedBootstrap();
        this.sendMessageToKernel({ type: 'praxis:bootstrap', code: bootstrapCode });
      }
    };

    this.replChannel.onmessage = (event) => {
      console.log('[REPL] Received message on BroadcastChannel:', event.data?.type);
      messageHandler(event.data);
    };

    // Also listen for window messages as a fallback
    this.messageListener = (event: MessageEvent) => {
      const type = event.data?.type;
      if (type === 'USER_INTERACTION' || (type && type.startsWith('praxis:')) || type === 'r' || type === 'q') {
        console.log('[REPL] Received message on window:', type);
        messageHandler(event.data);
      }
    };
    window.addEventListener('message', this.messageListener);
  }

  private sendMessageToKernel(message: any): void {
    if (this.replChannel) {
      this.replChannel.postMessage(message);
    }
    // Fallback: also try postMessage to all iframes
    const iframes = document.querySelectorAll('iframe');
    iframes.forEach(iframe => {
      try {
        iframe.contentWindow?.postMessage(message, '*');
      } catch (e) {
        // Ignore cross-origin errors
      }
    });
  }

  private async handleUserInteraction(payload: any): Promise<void> {
    if (!payload.id || this.processedInteractionIds.has(payload.id)) {
      console.log('[REPL] Skipping duplicate interaction request:', payload.id);
      return;
    }
    this.processedInteractionIds.add(payload.id);

    console.log('[REPL] Opening interaction dialog:', payload.interaction_type, 'ID:', payload.id);
    const result = await this.interactionService.handleInteraction({
      interaction_type: payload.interaction_type,
      payload: payload.payload
    });

    console.log('[REPL] Interaction result obtained:', result, 'ID:', payload.id);

    this.sendMessageToKernel({
      type: 'praxis:interaction_response',
      id: payload.id,
      value: result
    });

    // Keep set size manageable
    if (this.processedInteractionIds.size > 100) {
      const first = this.processedInteractionIds.values().next().value;
      if (first) this.processedInteractionIds.delete(first);
    }
  }

  private getIsDarkMode(): boolean {
    return document.body.classList.contains('dark-theme');
  }

  public getMinimalBootstrap(): string {
    const channelName = 'praxis_repl';

    // Ultra minimal bootstrap to avoid URL length limits and ensure reliability
    return `
import js, asyncio
js.console.log('PRAXIS: Minimal boot starting, URL:', js.window.location.href)
async def _h(e):
  d = e.data.to_py() if hasattr(e.data, 'to_py') else e.data
  if d.get('type') == 'praxis:bootstrap':
    js.console.log('PRAXIS: Executing bootstrap...')
    exec("async def _f():\\n" + "\\n".join("  "+l for l in d.get('code').split("\\n")), globals())
    await globals()['_f']()
c = js.BroadcastChannel.new('${channelName}') if hasattr(js.BroadcastChannel, 'new') else js.BroadcastChannel('${channelName}')
c.onmessage = lambda e: asyncio.ensure_future(_h(e))
c.postMessage(js.Object.fromEntries([('type', 'r')]))
if hasattr(js, 'window'): js.window.parent.postMessage(js.Object.fromEntries([('type', 'r')]), '*')
js.console.log('PRAXIS: Minimal boot ready')
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

    const bootstrapCode = this.getMinimalBootstrap();

    console.log('[REPL] Building JupyterLite URL. Theme:', this.currentTheme);

    const baseUrl = this.calculateHostRoot() + 'assets/jupyterlite/repl/index.html';
    const params = new URLSearchParams({
      kernel: 'python',
      toolbar: '1',
      theme: isDark ? 'JupyterLab Dark' : 'JupyterLab Light',
      execute: '1',
    });

    if (bootstrapCode) {
      params.set('code', bootstrapCode);
    }

    const fullUrl = `${baseUrl}?${params.toString()}`;
    this.jupyterliteUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(fullUrl));

    this.loadingTimeout = setTimeout(() => {
      if (this.isLoading()) {
        console.warn('[REPL] Loading timeout (300s) reached');
        this.isLoading.set(false);
      }
    }, 300000);
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

    let shimInjections = `# --- Host Root --- \n`;
    shimInjections += `PRAXIS_HOST_ROOT = "${hostRoot}"\n`;
    shimInjections += 'import sys\nimport os\n';
    shimInjections += 'if "." not in sys.path: sys.path.append(".")\n';
    shimInjections += 'import pyodide.http\n';

    for (const shim of shims) {
      shimInjections += `
try:
    _shim_code = await (await pyodide.http.pyfetch(f'{PRAXIS_HOST_ROOT}assets/shims/${shim}')).string()
    exec(_shim_code, globals())
except Exception as e:
    print(f"Failed to load ${shim}: {e}")
`;
    }

    shimInjections += `
try:
    _bridge_code = await (await pyodide.http.pyfetch(f'{PRAXIS_HOST_ROOT}assets/python/web_bridge.py')).string()
    with open('web_bridge.py', 'w') as f:
        f.write(_bridge_code)
except Exception as e:
    print(f"Failed to load web_bridge.py: {e}")

if not os.path.exists('praxis'):
    os.makedirs('praxis')
    
`;

    for (const file of ['__init__.py', 'interactive.py']) {
      shimInjections += `
try:
    _p_code = await (await pyodide.http.pyfetch(f'{PRAXIS_HOST_ROOT}assets/python/praxis/${file}')).string()
    with open(f'praxis/${file}', 'w') as f:
        f.write(_p_code)
except Exception as e:
    print(f"Failed to load praxis/${file}: {e}")
`;
    }

    const baseBootstrap = this.generateBootstrapCode();
    return shimInjections + '\n' + baseBootstrap;
  }

  private getPostLoadCode(): string {
    const channelName = 'praxis_repl';

    const lines = [
      'import js, json',
      'from pyodide.ffi import to_js',
      '',
      'def _send_to_angular(msg_dict):',
      '    try:',
      '        js_msg = to_js(msg_dict, dict_converter=js.Object.fromEntries)',
      '        if hasattr(globals(), "_praxis_channel") and globals()["_praxis_channel"]:',
      '            globals()["_praxis_channel"].postMessage(js_msg)',
      '        if hasattr(js, "window"): js.window.parent.postMessage(js_msg, "*")',
      '    except Exception as e: js.console.error(f"Failed to send to angular: {e}")',
      '',
      'def _praxis_message_handler(event):',
      '    try:',
      '        data = event.data.to_py() if hasattr(event.data, "to_py") else event.data',
      '        if isinstance(data, dict) and data.get("type") == "praxis:execute":',
      '            code = data.get("code", "")',
      '            try:',
      '                if "await " in code:',
      '                    import asyncio',
      '                    async def _run_async():',
      '                        try:',
      '                            indented = "\\n".join("    " + l for l in code.split("\\n"))',
      '                            wrapper = f"async def __praxis_async_exec__():\\n{indented}"',
      '                            exec(wrapper, globals())',
      '                            result = await globals()["__praxis_async_exec__"]()',
      '                            if result is not None: print(result)',
      '                        except Exception as e: import traceback; traceback.print_exc()',
      '                        except BaseException as e: import traceback; traceback.print_exc()',
      '                    asyncio.ensure_future(_run_async())',
      '                else:',
      '                    exec(code, globals())',
      '            except Exception as e: import traceback; traceback.print_exc()',
      '            except BaseException as e: import traceback; traceback.print_exc()',
      '        elif isinstance(data, dict) and data.get("type") == "praxis:interaction_response":',
      '            import web_bridge',
      '            web_bridge.handle_interaction_response(data.get("id"), data.get("value"))',
      '    except Exception as e: js.console.error(f"Execution error: {e}")',
      '',
      'try:',
      '    if hasattr(js, "BroadcastChannel"):',
      `        _praxis_channel = js.BroadcastChannel.new("${channelName}") if hasattr(js.BroadcastChannel, "new") else js.BroadcastChannel("${channelName}")`,
      '        _praxis_channel.onmessage = _praxis_message_handler',
      '        import web_bridge',
      '        web_bridge.register_broadcast_channel(_praxis_channel)',
      '    if hasattr(js, "window"): js.window.onmessage = _praxis_message_handler',
      'except Exception as e: js.console.error(f"Failed to setup channel: {e}")',
      '',
      'js.console.log("PRAXIS: Ready signal starting...")',
      '_send_to_angular({"type": "praxis:ready"})',
    ];
    return lines.join('\n');
  }

  private generateBootstrapCode(): string {
    const lines = [
      'import pyodide.http, micropip, sys, js',
      'if "." not in sys.path: sys.path.append(".")\n',
      'try:',
      '    _wheel_url = f"{PRAXIS_HOST_ROOT}assets/wheels/pylabrobot-0.1.6-py3-none-any.whl"',
      '    js.console.log(f"PRAXIS: Installing wheel from {_wheel_url}")',
      '    await micropip.install(_wheel_url, deps=False)',
      '    js.console.log("PRAXIS: Wheel installed successfully")',
      'except Exception as e:',
      '    js.console.error(f"PRAXIS: Failed to install wheel: {e}")',
      '    import traceback; traceback.print_exc()',
      '',
      'import builtins',
      'for s in ["WebSerial", "WebUSB", "WebFTDI"]:',
      '    if s in globals(): setattr(builtins, s, globals()[s])',
      '',
      'import sys; from unittest.mock import MagicMock',
      `await micropip.install(f'{PRAXIS_HOST_ROOT}assets/wheels/pylibftdi-0.0.0-py3-none-any.whl', deps=False)`,
      'js.console.log("PRAXIS: pylibftdi stub installed from wheel")',
      'sys.modules["ssl"] = MagicMock()',
      '',
      'import pylabrobot.io.serial as _ser',
      'import pylabrobot.io.usb as _usb',
      'import pylabrobot.io.ftdi as _ftdi',
      'if "WebSerial" in globals(): _ser.Serial = WebSerial',
      'if "WebUSB" in globals(): _usb.USB = WebUSB',
      'if "WebFTDI" in globals(): _ftdi.FTDI = WebFTDI; _ftdi.HAS_PYLIBFTDI = True',
      '',
      'import pylabrobot',
      'import pylabrobot.resources as _res',
      'for _n in dir(_res):',
      '    if not _n.startswith("_"): globals()[_n] = getattr(_res, _n)',
      '',
      'try:',
      '    import web_bridge',
      '    web_bridge.bootstrap_playground(globals())',
      'except Exception as e: import js; js.console.error(f"Failed to init playground: {e}")',
      '',
    ];

    return lines.join('\n') + this.getPostLoadCode();
  }

  private calculateHostRoot(): string {
    const baseHref = document.querySelector('base')?.getAttribute('href') || '/';
    return PathUtils.normalizeBaseHref(baseHref);
  }
}
