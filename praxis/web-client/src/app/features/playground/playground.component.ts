import {
  Component,
  ElementRef,
  OnInit,
  OnDestroy,
  ViewChild,
  inject,
  ChangeDetectorRef,
  signal,
  computed,
  AfterViewInit,
  HostListener
} from '@angular/core';
import { InteractionService } from '@core/services/interaction.service';
import { CommandRegistryService } from '@core/services/command-registry.service';

import { FormsModule } from '@angular/forms';

import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatListModule } from '@angular/material/list';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { ModeService } from '@core/services/mode.service';
import { SqliteService } from '@core/services/sqlite';
import { AssetService } from '@features/assets/services/asset.service';
import { Machine, Resource, MachineStatus } from '@features/assets/models/asset.models';
import { Subscription, firstValueFrom } from 'rxjs';
import { filter, first, take } from 'rxjs/operators';
import { HardwareDiscoveryButtonComponent } from '@shared/components/hardware-discovery-button/hardware-discovery-button.component';

import { serial as polyfillSerial } from 'web-serial-polyfill';
import { SerialManagerService } from '@core/services/serial-manager.service';
import { MatDialog } from '@angular/material/dialog';
import { AssetWizard } from '@shared/components/asset-wizard/asset-wizard';

import { MatTabsModule } from '@angular/material/tabs';
import { DirectControlComponent } from './components/direct-control/direct-control.component';
import { DirectControlKernelService } from './services/direct-control-kernel.service';
import { JupyterChannelService } from './services/jupyter-channel.service';
import { PlaygroundJupyterliteService } from './services/playground-jupyterlite.service';
import { PlaygroundAssetService } from './services/playground-asset.service';
import { PageTooltipComponent } from '@shared/components/page-tooltip/page-tooltip.component';
import { PraxisSelectComponent, SelectOption } from '@shared/components/praxis-select/praxis-select.component';


/**
 * Playground Component
 *
 * Replaces the xterm.js-based REPL with an embedded JupyterLite notebook.
 * Uses iframe embedding with URL parameters for configuration.
 */
@Component({
  selector: 'app-playground',
  standalone: true,
  imports: [
    FormsModule,

    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatTooltipModule,
    MatListModule,
    MatSnackBarModule,
    MatFormFieldModule,
    MatInputModule,
    MatMenuModule,
    MatDividerModule,
    MatSelectModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    HardwareDiscoveryButtonComponent,
    DirectControlComponent,
    PageTooltipComponent,
    PraxisSelectComponent
  ],
  template: `
    <div class="playground-layout" #playgroundRoot>
      <app-page-tooltip
        id="playground-intro"
        text="The Playground provides a full Jupyter environment for interactive hardware control and protocol development."
        [target]="playgroundRoot">
      </app-page-tooltip>

      <!-- Central View Area -->
      <div class="playground-canvas">
        <!-- JupyterLite View (stays alive in DOM) -->
        <div class="view-pane" [hidden]="playgroundMode() !== 'jupyter'">
          <div class="iframe-wrapper" data-tour-id="repl-notebook">
            @if (jupyterliteService.jupyterliteUrl()) {
              <iframe
                #notebookFrame
                [src]="jupyterliteService.jupyterliteUrl()"
                class="notebook-frame"
                data-testid="jupyterlite-iframe"
                (load)="onIframeLoad()"
                allow="cross-origin-isolated; usb; serial"
              ></iframe>
            }

            @if (jupyterliteService.isLoading()) {
              <div class="loading-overlay">
                <div class="skeleton-container">
                  <div class="skeleton-bar header"></div>
                  <div class="skeleton-bar toolbar"></div>
                  <div class="skeleton-content">
                    <div class="skeleton-cell"></div>
                    <div class="skeleton-cell short"></div>
                  </div>
                  <div class="loading-text">Initializing Python environment...</div>
                </div>
              </div>
            }

            @if (jupyterliteService.loadingError()) {
              <div class="error-overlay">
                <div class="error-content">
                  <mat-icon color="warn" class="error-icon">error_outline</mat-icon>
                  <div class="error-message">{{ jupyterliteService.loadingError() }}</div>
                  <button mat-flat-button color="primary" (click)="retryBootstrap()">
                    <mat-icon>refresh</mat-icon>
                    Retry Loading
                  </button>
                </div>
              </div>
            }
          </div>
        </div>

        <!-- Direct Control View -->
        <div class="view-pane" [hidden]="playgroundMode() !== 'direct-control'">
          <app-direct-control
            [machine]="$any(selectedMachine())"
            (executeCommand)="onExecuteCommand($event)">
          </app-direct-control>
        </div>
      </div>

      <!-- Floating Toolbar (horizontal, top right) -->
      <div class="toolbar-rail" role="toolbar" aria-label="Playground tools">
        <!-- View Mode Split Toggle -->
        <mat-button-toggle-group
          [value]="playgroundMode()"
          (change)="playgroundMode.set($event.value)"
          class="mode-toggle"
          hideSingleSelectionIndicator>
          <mat-button-toggle value="jupyter"
            matTooltip="Jupyter Notebook"
            matTooltipPosition="left"
            aria-label="Switch to Jupyter Notebook">
            <mat-icon>auto_stories</mat-icon>
          </mat-button-toggle>
          <mat-button-toggle value="direct-control"
            matTooltip="Direct Control"
            matTooltipPosition="left"
            aria-label="Switch to Direct Control">
            <mat-icon>tune</mat-icon>
          </mat-button-toggle>
        </mat-button-toggle-group>

        <!-- Action Buttons -->
        <button mat-icon-button
          (click)="openInventory()"
          matTooltip="Add Asset"
          matTooltipPosition="left"
          aria-label="Add Asset">
          <mat-icon>add_circle_outline</mat-icon>
        </button>
        <app-hardware-discovery-button></app-hardware-discovery-button>
      </div>

      <!-- Machine Selector (renders to left of toolbar in DC mode) -->
      @if (playgroundMode() === 'direct-control' && availableMachines().length > 0) {
        <div class="machine-selector-float">
          <app-praxis-select
            placeholder="Select Machine"
            [options]="machineSelectOptions()"
            (selectionChange)="onMachineSelected($event)">
          </app-praxis-select>
        </div>
      }
    </div>
  `,
  styles: [
    `
      .playground-layout {
        height: 100%;
        width: 100%;
        display: flex;
        position: relative;
        overflow: hidden;
        background: var(--mat-sys-surface-container-low);
      }

      .playground-canvas {
        flex: 1;
        height: 100%;
        min-width: 0;
        position: relative;
      }

      .view-pane {
        height: 100%;
        width: 100%;
        position: absolute;
        inset: 0;
      }

      .iframe-wrapper {
        height: 100%;
        width: 100%;
        position: relative;
      }

      .notebook-frame {
        width: 100%;
        height: 100%;
        border: none;
      }

      /* ─── Floating Toolbar (horizontal, top right) ─── */
      .toolbar-rail {
        position: absolute;
        top: 36px;
        right: 16px;
        z-index: 10;

        display: flex;
        flex-direction: row;
        align-items: center;
        padding: 4px 8px;
        gap: 4px;

        background: linear-gradient(
          135deg,
          var(--mat-sys-surface) 0%,
          var(--mat-sys-surface-container-low) 100%
        );
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--theme-border, var(--mat-sys-outline-variant));
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        transition: box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);

        &:hover {
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
        }
      }

      .mode-toggle {
        border-radius: 12px !important;
        overflow: hidden;
      }

      ::ng-deep .mode-toggle .mat-button-toggle-appearance-standard {
        background: transparent;
      }

      ::ng-deep .mode-toggle .mat-button-toggle-checked .mat-button-toggle-appearance-standard {
        background: var(--mat-sys-primary);
        color: var(--mat-sys-on-primary);
      }

      .machine-selector-float {
        position: absolute;
        top: 36px;
        right: calc(16px + 240px);
        z-index: 10;
      }

      .toolbar-rail button,
      .toolbar-rail app-hardware-discovery-button {
        cursor: pointer;
      }

      /* ─── Loading & Error Overlays ─── */
      .loading-overlay {
        position: absolute;
        inset: 0;
        background: var(--mat-sys-surface-container-low);
        z-index: 100;
        display: flex;
        align-items: center;
        justify-content: center;

        .skeleton-container {
          width: 80%;
          max-width: 600px;
        }

        .skeleton-bar {
          height: 32px;
          background: linear-gradient(90deg, var(--mat-sys-surface-container-high) 25%, var(--mat-sys-surface-container-highest) 50%, var(--mat-sys-surface-container-high) 75%);
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
          margin-bottom: 8px;
          border-radius: 4px;
          &.header { height: 40px; }
          &.toolbar { height: 28px; width: 60%; }
        }

        .skeleton-cell {
          height: 50px;
          background: var(--mat-sys-surface-container);
          margin-bottom: 8px;
          border-radius: 4px;
          &.short { width: 70%; }
        }

        .loading-text {
          text-align: center;
          color: var(--mat-sys-on-surface-variant);
          margin-top: 16px;
        }
      }

      .error-overlay {
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--mat-sys-surface-container-low);
        z-index: 100;
      }

      .error-content {
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
      }

      @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }
    `,
  ],
})
export class PlaygroundComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('notebookFrame') notebookFrame!: ElementRef<HTMLIFrameElement>;
  @ViewChild(DirectControlComponent) directControlComponent?: DirectControlComponent;

  playgroundMode = signal<'jupyter' | 'direct-control'>('jupyter');

  private modeService = inject(ModeService);
  private snackBar = inject(MatSnackBar);
  private cdr = inject(ChangeDetectorRef);
  private assetService = inject(AssetService);
  private sqliteService = inject(SqliteService);
  private dialog = inject(MatDialog);
  private interactionService = inject(InteractionService);
  private jupyterChannel = inject(JupyterChannelService);
  public jupyterliteService = inject(PlaygroundJupyterliteService);
  private playgroundAssetService = inject(PlaygroundAssetService);
  private commandRegistry = inject(CommandRegistryService);

  // Serial Manager for main-thread I/O (Phase B)
  private serialManager = inject(SerialManagerService);

  // Direct Control dedicated kernel (separate from JupyterLite)
  private directControlKernel = inject(DirectControlKernelService);

  modeLabel = computed(() => this.modeService.modeLabel());

  private viewInitialized = false;

  private subscription = new Subscription();

  // Selected machine for Direct Control
  selectedMachine = signal<Machine | null>(null);
  availableMachines = signal<Machine[]>([]);
  selectedTabIndex = signal(0);

  /** Derived SelectOption[] for praxis-select — pure signal, no RxJS */
  machineSelectOptions = computed<SelectOption[]>(() =>
    this.availableMachines().map(m => ({
      label: m.name,
      value: m.name,
      icon: this.getMachineIcon(m.asset_type || '')
    }))
  );

  // Event listener for machine-registered events
  private machineRegisteredHandler = () => {
    console.log('[Playground] machine-registered event received, refreshing list...');
    this.loadMachinesForDirectControl();
  };

  constructor() {
    // Expose helpers for E2E tests
    (window as any).setPlaygroundCode = (code: string) => {
      (window as any).__praxis_pending_code = code;
    };
    (window as any).runPlaygroundCode = () => {
      const code = (window as any).__praxis_pending_code;
      if (code) {
        this.jupyterChannel.sendMessage({
          type: 'praxis:execute',
          code: code
        });
      }
    };

    // Theme syncing is handled by PlaygroundJupyterliteService's own effect
    // Initialize WebSerial Polyfill if WebUSB is available
    if (typeof navigator !== 'undefined' && 'usb' in navigator) {
      try {
        (window as any).polyfillSerial = polyfillSerial; // Expose the serial API interface
        console.log('[REPL] WebSerial Polyfill loaded and exposed as window.polyfillSerial');
      } catch (e) {
        console.warn('[REPL] Failed to load WebSerial polyfill', e);
      }
    }

    // SerialManager is auto-initialized and listening for BroadcastChannel messages
    console.log('[REPL] SerialManager ready for main-thread serial I/O');
  }

  ngOnInit() {
    this.jupyterliteService.initialize();

    // Wait for the database to be ready before loading assets.
    // This prevents race conditions on initial load or after a db reset.
    this.subscription.add(
      this.sqliteService.isReady$.pipe(
        filter(ready => ready),
        take(1)
      ).subscribe(() => {
        console.log('[Playground] Database is ready, loading machines for Direct Control.');
        this.loadMachinesForDirectControl();
      })
    );

    // Listen for new machine registrations
    window.addEventListener('machine-registered', this.machineRegisteredHandler);

    // Register keyboard shortcut
    this.commandRegistry.registerCommand({
      id: 'toggle-playground-mode',
      label: 'Toggle Playground Mode',
      shortcut: 'Alt+T',
      action: () => this.playgroundMode.set(
        this.playgroundMode() === 'jupyter' ? 'direct-control' : 'jupyter'
      ),
      category: 'Playground',
      keywords: ['jupyter', 'direct control', 'mode', 'toggle']
    });
  }

  ngAfterViewInit() {
    this.viewInitialized = true;
    this.cdr.detectChanges();
  }



  /**
   * Handle USER_INTERACTION requests from the REPL channel and show UI dialogs
   */
  private async handleUserInteraction(payload: any) {
    console.log('[REPL] Opening interaction dialog:', payload.interaction_type);
    const result = await this.interactionService.handleInteraction({
      interaction_type: payload.interaction_type,
      payload: payload.payload
    });

    console.log('[REPL] Interaction result obtained:', result);

    this.jupyterChannel.sendMessage({
      type: 'praxis:interaction_response',
      id: payload.id,
      value: result
    });
  }

  ngOnDestroy() {
    this.subscription.unsubscribe();
    window.removeEventListener('machine-registered', this.machineRegisteredHandler);
    this.jupyterliteService.destroy();
  }

  /**
   * Load registered machines for Direct Control tab.
   * Auto-selects the most recently created machine if none is selected.
   */
  loadMachinesForDirectControl(): void {
    this.subscription.add(
      this.assetService.getMachines().subscribe({
        next: (machines) => {
          console.log('[Playground] Loaded machines for Direct Control:', machines.length, machines);
          // Sort by created_at descending (most recent first)
          const sorted = [...machines].sort((a, b) => {
            const aDate = (a as any).created_at ? new Date((a as any).created_at).getTime() : 0;
            const bDate = (b as any).created_at ? new Date((b as any).created_at).getTime() : 0;
            return bDate - aDate;
          });
          this.availableMachines.set(sorted);

          // Auto-select the first (most recent) machine if none selected
          if (!this.selectedMachine() && sorted.length > 0) {
            this.selectedMachine.set(sorted[0]);
            console.log('[Playground] Auto-selected machine for Direct Control:', sorted[0].name);
          }
        },
        error: (err) => {
          console.error('[Playground] Failed to load machines:', err);
        }
      })
    );
  }

  /**
   * Select a machine for Direct Control
   */
  selectMachineForControl(machine: Machine): void {
    this.selectedMachine.set(machine);
  }

  /** Handle praxis-select machine selection */
  onMachineSelected(value: unknown): void {
    const name = value as string;
    const machine = this.availableMachines().find(m => m.name === name);
    if (machine) {
      this.selectMachineForControl(machine);
    }
  }

  /**
   * Get icon for machine category
   */
  getMachineIcon(category: string): string {
    const iconMap: Record<string, string> = {
      'LiquidHandler': 'science',
      'PlateReader': 'visibility',
      'Shaker': 'vibration',
      'Centrifuge': 'loop',
      'Incubator': 'thermostat',
      'Other': 'precision_manufacturing'
    };
    return iconMap[category] || 'precision_manufacturing';
  }

  openAddMachine() {
    this.openAssetWizard('MACHINE');
  }



  openAddResource() {
    this.openAssetWizard('RESOURCE');
  }

  openInventory() {
    this.openAssetWizard();
  }

  openAssetWizard(preselectedType?: 'MACHINE' | 'RESOURCE') {
    const dialogRef = this.dialog.open(AssetWizard, {
      minWidth: '600px',
      maxWidth: '1000px',
      width: '80vw',
      height: '85vh',
      data: {
        ...(preselectedType ? { preselectedType } : {}),
        context: 'playground'
      }
    });

    dialogRef.afterClosed().subscribe((result: any) => {
      if (result && typeof result === 'object') {
        const type = result.asset_type === 'MACHINE' ? 'machine' : 'resource';
        this.insertAsset(type, result);
      }
    });
  }

  /* Asset injection methods — delegated to PlaygroundAssetService */




  /**
   * Handle iframe load event
   */
  onIframeLoad() {
    console.log('[REPL] Iframe loaded event fired');

    // Check if iframe has actual content
    const iframe = this.notebookFrame?.nativeElement;
    // We try to access contentDocument. If it fails (cross-origin) or is empty/about:blank, likely failed or just initialized.
    let hasContent = false;
    try {
      hasContent = (iframe?.contentDocument?.body?.childNodes?.length ?? 0) > 0;
    } catch (e) {
      console.warn('[REPL] Cannot access iframe content (possibly 431 error or cross-origin):', e);
      hasContent = false;
    }

    if (hasContent) {
      console.log('[REPL] Iframe content detected');
      // Success case - but we wait for 'ready' signal to clear isLoading for the user.
      // However, if we don't get 'ready' signal, we rely on timeout.
      // We do NOT clear isLoading here immediately because the kernel is still booting.

      // Inject fetch interceptor to suppress 404s for virtual filesystem lookups
      try {
        const script = iframe!.contentWindow?.document.createElement('script');
        if (script) {
          script.textContent = `
  (function () {
    const originalFetch = window.fetch;
    window.fetch = function (input, init) {
      const url = typeof input === 'string' ? input : (input instanceof URL ? input.href : input.url);
      // Suppress network requests for pylabrobot modules that are already in VFS
      if (url.includes('pylabrobot') && (url.endsWith('.py') || url.endsWith('.so') || url.includes('/__init__.py'))) {
        // We could return a fake response here, but Pyodide might need a real network 404 
        // to move to the next finder. However, we can log it gracefully.
      }
      return originalFetch(input, init);
    };
  })();
`;
          iframe!.contentWindow?.document.head.appendChild(script);
          console.log('[REPL] Fetch interceptor injected into iframe');
        }
      } catch (e) {
        console.warn('[REPL] Could not inject interceptor (likely cross-origin):', e);
      }
    } else {
      console.warn('[REPL] Iframe load event fired but no content detected (or access denied)');
      // If we loaded blank/error page (like 431), we should probably fail.
      // But 'about:blank' also fires load.
      // Let's assume if it's a 431 error page, it has SOME content but maybe not what we expect?
      // Actually, if it's 431, the browser shows an error page.

      // If we clear isLoading here, we hide the spinner and show the error page (white screen or browser error).
      // If we don't clear it, the timeout will eventually catch it.
      // Let's rely on the timeout to show "Retry" if the kernel doesn't say "Ready".
    }
  }

  /**
   * Reload the notebook (restart kernel)
   */
  reloadNotebook() {
    this.jupyterliteService.reloadNotebook();
  }

  /**
   * Retry the bootstrap process after an error or timeout
   */
  retryBootstrap(): void {
    console.log('[Playground] Retrying bootstrap...');
    this.jupyterliteService.loadingError.set(null);
    this.jupyterliteService.isLoading.set(true);
    this.jupyterliteService.initialize();
  }

  /**
   * Split a fully qualified Python name into (module_path, class_name).
   * e.g. "pylabrobot.resources.greiner.plates.Greiner_384" → ["pylabrobot.resources.greiner.plates", "Greiner_384"]
   */
  private splitFqn(fqn: string): [string, string] {
    const lastDot = fqn.lastIndexOf('.');
    if (lastDot === -1) return [fqn, fqn];
    return [fqn.substring(0, lastDot), fqn.substring(lastDot + 1)];
  }

  /**
   * Check if a machine is currently in use by a protocol run
   */
  isMachineInUse(machine: Machine): boolean {
    // Check if machine has an active protocol run
    return machine.status === MachineStatus.RUNNING;
  }

  /**
   * Helper for E2E tests to trigger code execution
   */
  public executeCodeForTest(code: string) {
    this.jupyterChannel.sendMessage({
      type: 'praxis:execute',
      code: code
    });
  }

  /**
   * Insert asset into the notebook by generating and executing Python code
   */
  async insertAsset(
    type: 'machine' | 'resource',
    asset: Machine | Resource,
    variableName?: string,
    deckConfigId?: string
  ) {
    // If implementing physical machine, check prior authorization
    if (type === 'machine') {
      const machine = asset as Machine;
      this.selectedMachine.set(machine);
      // If it's a physical machine (not simulated)
      if (!machine.is_simulation_override) {
        try {
          // We might want to check ports here, but for now assuming user knows what they are doing
          // or logic is handled elsewhere.
        } catch (err) {
          console.error('Failed to check hardware permissions:', err);
        }
      }
    }

    // Generate appropriate Python code (delegated to service for consistency)
    let code: string;
    if (type === 'machine') {
      code = await this.playgroundAssetService.generateMachineCode(asset as Machine, variableName, deckConfigId);
    } else {
      code = this.playgroundAssetService.generateResourceCode(asset as Resource, variableName);
    }

    // Extract var name from generated code for snackbar (first assignment line)
    const assignMatch = code.match(/^(\w+)\s*=/m);
    const displayName = assignMatch?.[1] || asset.name;

    // Primary: inject via jupyterapp commands (visible in REPL cells + executed)
    const injected = await this.injectViaJupyterApp(code);

    if (injected) {
      this.snackBar.open(`Inserted ${displayName}`, 'OK', { duration: 2000 });
    } else {
      // Fallback: BroadcastChannel (executes in kernel but not visible as REPL cells)
      console.warn('[Playground] console:inject failed, falling back to BroadcastChannel');
      try {
        this.jupyterChannel.sendMessage({
          type: 'praxis:execute',
          code: code,
          label: displayName
        });
        this.snackBar.open(`Inserted ${displayName}`, 'OK', { duration: 2000 });
      } catch (e) {
        console.error('[Playground] Failed to send asset to REPL:', e);
        navigator.clipboard.writeText(code).then(() => {
          this.snackBar.open(`Code copied to clipboard (injection failed)`, 'OK', {
            duration: 2000,
          });
        });
      }
    }
  }

  /**
   * Inject code into JupyterLite console via iframe's jupyterapp commands API.
   * Uses console:inject (with path) to populate the prompt, then console:run-forced to execute.
   */
  private async injectViaJupyterApp(code: string): Promise<boolean> {
    try {
      const iframe = this.notebookFrame?.nativeElement;
      const jupyterapp = (iframe?.contentWindow as any)?.jupyterapp;
      if (!jupyterapp?.commands) {
        console.warn('[Playground] jupyterapp.commands not available');
        return false;
      }

      // Find the console widget's session path from the shell
      let consolePath = '';
      try {
        // REPLite has a single console widget — find it
        const shell = jupyterapp.shell;
        if (shell?.currentWidget?.sessionContext?.path) {
          consolePath = shell.currentWidget.sessionContext.path;
        } else if (shell?.currentWidget?.console?.sessionContext?.path) {
          consolePath = shell.currentWidget.console.sessionContext.path;
        } else {
          // Try iterating shell widgets
          const widgets = shell?.widgets?.('main');
          if (widgets) {
            for (const w of widgets) {
              const path = w?.sessionContext?.path || w?.console?.sessionContext?.path;
              if (path) { consolePath = path; break; }
            }
          }
        }
      } catch { /* proceed with empty path */ }

      console.log('[Playground] Console path:', consolePath || '(default)');
      console.log('[Playground] Injecting code, length:', code.length);

      // Step 1: Inject code into console prompt
      await jupyterapp.commands.execute('console:inject', {
        path: consolePath,
        code: code,
        activate: true
      });

      // Step 2: Execute the injected code
      await jupyterapp.commands.execute('console:run-forced', {
        activate: false
      });

      console.log('[Playground] console:inject + run-forced complete');
      return true;
    } catch (e) {
      console.warn('[Playground] Failed to inject via jupyterapp:', e);
      return false;
    }
  }

  /**
   * Handle executeCommand from DirectControlComponent
   * Uses a dedicated Pyodide kernel that persists across tab switches
   */


  async onExecuteCommand(event: { machineName: string, methodName: string, args: Record<string, unknown> }) {
    const { machineName, methodName, args } = event;
    console.log(`[DirectControl] Executing ${methodName} on ${machineName} `, args);

    // Find machine asset
    const machines = this.availableMachines();
    const asset = machines.find(m => m.name === machineName);
    if (!asset) {
      const err = `Machine ${machineName} not found`;
      this.snackBar.open(err, 'OK');
      this.directControlComponent?.handleCommandError(err);
      return;
    }

    const varName = this.playgroundAssetService.assetToVarName(asset);
    const machineId = asset.accession_id;
    const connectionInfo = asset.connection_info as Record<string, unknown> || {};
    const plrBackend = connectionInfo['plr_backend'] as string || '';
    const category = (asset as unknown as { machine_category?: string }).machine_category || 'LiquidHandler';

    try {
      // Boot kernel if needed (this is idempotent)
      if (!this.directControlKernel.isReady()) {
        this.snackBar.open('Booting Python kernel...', 'OK', { duration: 3000 });
        await this.directControlKernel.boot();
      }

      // Ensure machine is instantiated
      await this.directControlKernel.ensureMachineInstantiated(
        machineId,
        asset.name,
        varName,
        plrBackend,
        category
      );

      // Execute the method
      this.snackBar.open(`Executing ${methodName}...`, 'OK', { duration: 2000 });
      const output = await this.directControlKernel.executeMethod(varName, methodName, args);

      if (output.trim()) {
        console.log('[DirectControl] Output:', output);
        this.snackBar.open(output.split('\n')[0].substring(0, 80), 'OK', { duration: 5000 });
        // AUDIT-09: Pass valid result to DirectControl
        this.directControlComponent?.handleCommandResult(output);
      } else {
        this.directControlComponent?.handleCommandResult("Command completed (no output)");
      }
    } catch (e) {
      console.error('[DirectControl] Command failed:', e);
      const errorMsg = e instanceof Error ? e.message : String(e);
      this.snackBar.open(`Error: ${errorMsg.substring(0, 80)} `, 'Dismiss', { duration: 5000 });
      // AUDIT-09: Pass error to DirectControl
      this.directControlComponent?.handleCommandError(errorMsg);
    }
  }
}
