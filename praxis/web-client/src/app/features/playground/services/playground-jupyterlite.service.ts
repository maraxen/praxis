import { Injectable, signal, inject, effect } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { AppStore } from '@core/store/app.store';
import { InteractionService } from '@core/services/interaction.service';
import { PathUtils } from '@core/utils/path.utils';


@Injectable({
  providedIn: 'root'
})
export class PlaygroundJupyterliteService {
  private sanitizer = inject(DomSanitizer);
  private store = inject(AppStore);
  private interactionService = inject(InteractionService);


  // JupyterLite Iframe Configuration
  jupyterliteUrl = signal<SafeResourceUrl | undefined>(undefined);
  isLoading = signal(true);
  loadingError = signal<string | null>(null);
  private currentTheme = '';
  private loadingTimeout: ReturnType<typeof setTimeout> | undefined;
  private replChannel: BroadcastChannel | null = null;
  private processedInteractionIds = new Set<string>();
  private messageListener: ((event: MessageEvent) => void) | null = null;

  // Kernel restart detection
  private lastKernelId: string | null = null;
  private kernelPollInterval: ReturnType<typeof setInterval> | undefined;

  // Auto-retry: JupyterLite's service-worker-manager unregisters all SWs on first load.
  // The SW needs ~5-10s to re-activate, so we auto-retry with short intervals.
  private bootstrapAttempt = 0;
  private readonly MAX_AUTO_RETRIES = 2;
  private readonly RETRY_TIMEOUT_MS = 15_000;

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
    this.loadingError.set(null);
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
    if (this.kernelPollInterval) {
      clearInterval(this.kernelPollInterval);
      this.kernelPollInterval = undefined;
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

    // Auto-retry timeout: first attempts use short timeout, then auto-retry.
    // On first load, JupyterLite's SW manager unregisters all SWs and re-registers.
    // The SW needs a few seconds to activate. Auto-retrying avoids a 60s manual wait.
    if (this.loadingTimeout) {
      clearTimeout(this.loadingTimeout);
    }
    this.loadingTimeout = setTimeout(() => {
      if (this.isLoading()) {
        if (this.bootstrapAttempt < this.MAX_AUTO_RETRIES) {
          this.bootstrapAttempt++;
          console.warn(`[REPL] Bootstrap timeout (${this.RETRY_TIMEOUT_MS / 1000}s), auto-retrying (attempt ${this.bootstrapAttempt}/${this.MAX_AUTO_RETRIES})...`);
          this.reloadNotebook();
        } else {
          console.warn('[REPL] All auto-retries exhausted');
          this.loadingError.set('Bootstrap timeout. Check console for errors.');
          this.isLoading.set(false);
        }
      }
    }, this.RETRY_TIMEOUT_MS);

    const messageHandler = async (data: any) => {
      if (!data) return;

      const type = data.type;
      console.log('[REPL] Processing message type:', type);

      if (type === 'praxis:ready') {
        console.log(`[REPL] Kernel fully bootstrapped and ready (attempt ${this.bootstrapAttempt + 1})`);
        this.isLoading.set(false);
        this.loadingError.set(null);
        (window as any).__praxis_pyodide_ready = true;
        this.bootstrapAttempt = 0; // Reset for future reloads
        if (this.loadingTimeout) {
          clearTimeout(this.loadingTimeout);
          this.loadingTimeout = undefined;
        }
        // Start kernel restart detection after first successful bootstrap
        this.startKernelRestartDetection();
      } else if (type === 'USER_INTERACTION') {
        console.log('[REPL] USER_INTERACTION received:', data.payload);
        this.handleUserInteraction(data.payload);
      }
    };

    this.replChannel.onmessage = (event) => {
      console.log('[REPL] Received message on BroadcastChannel:', event.data?.type);
      messageHandler(event.data);
    };

    // Also listen for window messages as a fallback
    this.messageListener = (event: MessageEvent) => {
      const type = event.data?.type;
      if (type === 'USER_INTERACTION' || type === 'praxis:ready') {
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

  /**
   * Poll iframe's JupyterLite kernel status. When the kernel ID changes
   * (indicating a restart), re-inject the bootstrap code.
   */
  private startKernelRestartDetection(): void {
    // Clear any existing poll
    if (this.kernelPollInterval) {
      clearInterval(this.kernelPollInterval);
    }

    // Snapshot current kernel ID
    this.lastKernelId = this.getCurrentKernelId();

    this.kernelPollInterval = setInterval(() => {
      try {
        const currentId = this.getCurrentKernelId();
        if (currentId && this.lastKernelId && currentId !== this.lastKernelId) {
          console.log('[REPL] Kernel restart detected (ID changed:', this.lastKernelId, '->', currentId, ')');
          this.lastKernelId = currentId;
          this.isLoading.set(true);
          this.loadingError.set(null);
          (window as any).__praxis_pyodide_ready = false;
          // Wait a moment for the new kernel to be ready, then re-inject
          setTimeout(() => this.reinjectBootstrap(), 2000);
        } else if (currentId && !this.lastKernelId) {
          // First time we see a kernel ID — just record it
          this.lastKernelId = currentId;
        }
      } catch (e) {
        // Cross-origin or not ready — ignore silently
      }
    }, 2000);
  }

  private getCurrentKernelId(): string | null {
    try {
      const iframe = document.querySelector('iframe.notebook-frame') as HTMLIFrameElement | null;
      const jupyterapp = (iframe?.contentWindow as any)?.jupyterapp;
      if (!jupyterapp?.serviceManager?.kernels) return null;

      const runningKernels = jupyterapp.serviceManager.kernels.running();
      const first = runningKernels.next();
      return first.done ? null : first.value?.id ?? null;
    } catch (e) {
      return null;
    }
  }

  private reinjectBootstrap(): void {
    const iframe = document.querySelector('iframe.notebook-frame') as HTMLIFrameElement | null;
    const jupyterapp = (iframe?.contentWindow as any)?.jupyterapp;
    if (!jupyterapp?.commands) {
      console.warn('[REPL] Cannot re-inject bootstrap: jupyterapp.commands not available');
      this.isLoading.set(false);
      return;
    }

    const bootstrapCode = this.getMinimalBootstrap();
    console.log('[REPL] Re-injecting bootstrap after kernel restart...');

    try {
      jupyterapp.commands.execute('console:inject', {
        activate: false,
        code: bootstrapCode
      }).then(() => {
        return jupyterapp.commands.execute('console:run-forced');
      }).then(() => {
        console.log('[REPL] Bootstrap re-injection completed');
        // praxis:ready will be emitted by the bootstrap when it finishes
      }).catch((err: any) => {
        console.error('[REPL] Bootstrap re-injection failed:', err);
        this.isLoading.set(false);
        this.loadingError.set('Bootstrap re-injection failed after kernel restart');
      });
    } catch (e) {
      console.error('[REPL] Bootstrap re-injection error:', e);
      this.isLoading.set(false);
    }
  }

  private getIsDarkMode(): boolean {
    return document.body.classList.contains('dark-theme');
  }

  public getMinimalBootstrap(): string {
    // Compute host root in TypeScript and embed it — no js.window needed in worker.
    // Uses synchronous XMLHttpRequest to fetch praxis_bootstrap.py, then runs
    // praxis_main() as an async coroutine via asyncio.ensure_future.
    const hostRoot = this.calculateHostRoot();
    return `
import js, asyncio
HOST_ROOT = '${hostRoot}'
try:
    js.console.log(f'[Bootstrap] Fetching praxis_bootstrap.py from {HOST_ROOT}')
    xhr = js.XMLHttpRequest.new()
    xhr.open('GET', HOST_ROOT + 'assets/jupyterlite/praxis_bootstrap.py', False)
    xhr.send(None)
    code = str(xhr.responseText)
    js.console.log(f'[Bootstrap] Fetched {len(code)} bytes, executing...')
    exec(compile(code, 'praxis_bootstrap.py', 'exec'))
    asyncio.ensure_future(praxis_main(HOST_ROOT))
except Exception as e:
    js.console.error(f'[Bootstrap] FATAL: {e}')
    import traceback; traceback.print_exc()
`.trim();
  }

  private validateUrlSize(url: string): void {
    if (url.length > 2000) {
      console.warn(`URL length ${url.length} exceeds safe limit (2000)`);
    }
  }

  private async buildJupyterliteUrl(): Promise<void> {
    // NOTE: Do NOT clear loadingTimeout here — setupReadyListener() owns it.
    // Clearing it would prevent the 60s timeout from ever firing.

    this.isLoading.set(true);
    this.loadingError.set(null);
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
    this.validateUrlSize(fullUrl);
    this.jupyterliteUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(fullUrl));

    // setupReadyListener already sets a timeout
  }

  private async updateJupyterliteTheme(_: string): Promise<void> {
    const isDark = this.getIsDarkMode();
    const newTheme = isDark ? 'dark' : 'light';

    if (this.currentTheme !== newTheme) {
      console.log('[REPL] Theme changed from', this.currentTheme, 'to', newTheme);
      this.currentTheme = newTheme;

      const iframe = document.querySelector('iframe.notebook-frame') as HTMLIFrameElement | null;
      if (!iframe?.contentWindow) return;

      const themeName = isDark ? 'JupyterLab Dark' : 'JupyterLab Light';

      try {
        // Try JupyterLab command API (same-origin iframe)
        const win = iframe.contentWindow as any;
        if (win.jupyterapp?.commands) {
          await win.jupyterapp.commands.execute('apputils:change-theme', { theme: themeName });
          return;
        }

        // Fallback: set body data attributes directly
        const body = iframe.contentDocument?.body;
        if (body) {
          body.dataset['jpThemeName'] = themeName;
          body.dataset['jpThemeLight'] = isDark ? 'false' : 'true';
        }
      } catch (e) {
        console.warn('[REPL] Could not update iframe theme:', e);
      }
    }
  }

  private calculateHostRoot(): string {
    const baseHref = document.querySelector('base')?.getAttribute('href') || '/';
    return PathUtils.normalizeBaseHref(baseHref);
  }
}
