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
} from '@angular/core';
import { InteractionService } from '@core/services/interaction.service';

import { FormsModule } from '@angular/forms';

import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
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
import { Subscription } from 'rxjs';
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
  ],
  template: `
    <div class="repl-container">
      <!-- Main Notebook Area -->
      <div class="notebook-area">
        <mat-card class="repl-card">
          <!-- Menu Bar -->
          <div class="repl-header">
            <div class="header-title">
              <mat-icon>auto_stories</mat-icon>
              <h2>Playground ({{ modeLabel() }})</h2>
            </div>
            
            <div class="header-actions flex items-center gap-2">
              <app-hardware-discovery-button></app-hardware-discovery-button>
              <button 
                mat-icon-button 
                (click)="reloadNotebook()"
                matTooltip="Restart Kernel (reload notebook)"
                aria-label="Restart Kernel (reload notebook)">
                <mat-icon>restart_alt</mat-icon>
              </button>
              <button 
                mat-icon-button 
                (click)="openAddMachine()"
                matTooltip="Add Machine"
                aria-label="Add Machine"
                color="primary">
                <mat-icon>precision_manufacturing</mat-icon>
              </button>
              <button 
                mat-icon-button 
                (click)="openAddResource()"
                matTooltip="Add Resource"
                aria-label="Add Resource"
                color="primary">
                <mat-icon>science</mat-icon>
              </button>
              <button 
                mat-icon-button 
                (click)="openInventory()"
                matTooltip="Browse Inventory"
                aria-label="Browse Inventory"
                color="primary">
                <mat-icon>inventory_2</mat-icon>
              </button>
            </div>
          </div>

          <mat-tab-group class="repl-tabs" [selectedIndex]="selectedTabIndex()" (selectedIndexChange)="selectedTabIndex.set($event)" [preserveContent]="true">
            <mat-tab label="Notebook">
              <!-- JupyterLite iframe -->
              <div class="repl-notebook-wrapper" data-tour-id="repl-notebook" [hidden]="selectedTabIndex() !== 0">

                @if (jupyterliteService.jupyterliteUrl()) {
                  <iframe
                    #notebookFrame
                    [src]="jupyterliteService.jupyterliteUrl()"
                    class="notebook-frame"
                    data-testid="jupyterlite-iframe"
                    (load)="onIframeLoad()"
                    allow="cross-origin-isolated; usb; serial"
                    sandbox="allow-scripts allow-same-origin allow-popups allow-forms allow-modals"
                  ></iframe>
                }

                @if (jupyterliteService.isLoading()) {
                  <div class="loading-overlay">
                    <div class="skeleton-container">
                      <!-- Header bar -->
                      <div class="skeleton-bar header"></div>
                      <!-- Toolbar -->
                      <div class="skeleton-bar toolbar"></div>
                      <!-- Content cells -->
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
            </mat-tab>
            
            <mat-tab label="Direct Control">
              <div class="direct-control-dashboard" [hidden]="selectedTabIndex() !== 1">
                <!-- Machine Selector Sidebar -->
                <div class="machine-selector-panel">
                    <div class="panel-header">
                      <h3>Available Machines</h3>
                      <button mat-icon-button (click)="loadMachinesForDirectControl()" matTooltip="Refresh machines">
                        <mat-icon>refresh</mat-icon>
                      </button>
                    </div>
                    
                    @if (availableMachines().length === 0) {
                      <div class="empty-machines">
                        <mat-icon>precision_manufacturing</mat-icon>
                        <p>No machines registered</p>
                        <button mat-stroked-button (click)="openAssetWizard('MACHINE')">
                          <mat-icon>add</mat-icon>
                          Add Machine
                        </button>
                      </div>
                    } @else {
                      <div class="machine-list">
                        @for (machine of availableMachines(); track machine.accession_id) {
                          <div 
                            class="machine-card" 
                            [class.selected]="selectedMachine()?.accession_id === machine.accession_id"
                            (click)="selectMachineForControl(machine)">
                            <div class="machine-icon">
                              <mat-icon>{{ getMachineIcon($any(machine).machine_category) }}</mat-icon>
                            </div>
                            <div class="machine-info">
                              <span class="machine-name">{{ machine.name }}</span>
                              <span class="machine-category">{{ $any(machine).machine_category || 'Machine' }}</span>
                            </div>
                            <div class="machine-status" [class]="$any(machine).status?.toLowerCase() || 'offline'">
                              <span class="status-dot"></span>
                            </div>
                          </div>
                        }
                      </div>
                    }
                  </div>
                  
                  <!-- Control Panel -->
                  <div class="control-panel">
                    @if (selectedMachine()) {
                      <app-direct-control 
                        [machine]="$any(selectedMachine())"
                        (executeCommand)="onExecuteCommand($event)">
                      </app-direct-control>
                    } @else {
                      <div class="empty-state">
                        <mat-icon>settings_remote</mat-icon>
                        <p>Select a machine from the list to control it</p>
                      </div>
                    }
                  </div>
                </div>
            </mat-tab>
          </mat-tab-group>
        </mat-card>
      </div>
    </div>
  `,
  styles: [
    `
      .repl-container {
        height: 100%;
        width: 100%;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        padding: 16px;
        gap: 0; 
      }

      .notebook-area {
        height: 100%;
        min-width: 0; /* Allow shrinking */
        display: flex;
        flex-direction: column;
      }

      .repl-card {
        height: 100%;
        display: flex;
        flex-direction: column;
        padding: 0;
        background: var(--mat-sys-surface-container);
        border: 1px solid var(--mat-sys-outline-variant);
        color: var(--mat-sys-on-surface);
        border-radius: 8px;
        overflow: hidden;
      }

      .repl-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 16px;
        background: var(--mat-sys-surface-container-high);
        border-bottom: 1px solid var(--mat-sys-outline-variant);
        flex-shrink: 0;
        height: 56px;
        box-sizing: border-box;
      }

      .header-title {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .repl-header mat-icon {
        color: var(--mat-sys-primary);
      }

      .repl-header h2 {
        margin: 0;
        font-size: 1.1rem;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .repl-tabs {
        flex: 1;
        display: flex;
        flex-direction: column;
        min-height: 0;
      }

      :host ::ng-deep .repl-tabs {
        .mat-mdc-tab-body-wrapper {
          flex: 1;
        }
      }
  .repl-tabs {
  ::ng-deep .mat-mdc-tab-header {
    background: transparent;
    border-bottom: 1px solid var(--mat-sys-outline-variant);
  }

  ::ng-deep .mat-mdc-tab {
    min-width: 80px;
    opacity: 0.7;
    transition: opacity 0.2s ease;
    
    &:hover {
      opacity: 1;
    }
    
    &.mdc-tab--active {
      opacity: 1;
    }
  }

  ::ng-deep .mat-mdc-tab-labels {
    gap: 0;
  }
  
  ::ng-deep .mdc-tab-indicator__content--underline {
    border-color: var(--mat-sys-primary);
    border-width: 2px;
    border-radius: 2px 2px 0 0;
  }
}

      .repl-notebook-wrapper {
        height: 100%;
        position: relative;
        background: var(--mat-sys-surface-container-low);
      }

      .direct-control-wrapper {
        height: 100%;
        padding: 24px;
        overflow-y: auto;
        background: var(--mat-sys-surface-container-low);
      }

      .notebook-frame {
        width: 100%;
        height: 100%;
        border: none;
      }

      .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        gap: 16px;
        color: var(--mat-sys-on-surface-variant);
        text-align: center;
      }

      .empty-state mat-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
      }

      .loading-overlay {
        position: absolute;
        inset: 0;
        background: var(--mat-sys-surface-container-low);
        z-index: 100;
        display: flex;
        align-items: center;
        justify-content: center;

        .skeleton-container {
          width: 90%;
          max-width: 800px;
        }

        .skeleton-bar {
          height: 40px;
          background: linear-gradient(90deg, var(--mat-sys-surface-container-high) 25%, var(--mat-sys-surface-container-highest) 50%, var(--mat-sys-surface-container-high) 75%);
          background-size: 200% 100%;
          animation: shimmer 1.5s infinite;
          margin-bottom: 8px;
          border-radius: 4px;

          &.header { height: 48px; }
          &.toolbar { height: 36px; width: 60%; }
        }

        .skeleton-cell {
          height: 60px;
          background: var(--mat-sys-surface-container);
          border-left: 3px solid var(--mat-sys-outline-variant);
          margin-bottom: 12px;
          border-radius: 4px;

          &.short { width: 70%; }
        }

        .loading-text {
          text-align: center;
          color: var(--mat-sys-on-surface-variant);
          margin-top: 24px;
          font-weight: 500;
        }
      }

      .error-overlay {
        position: absolute;
        inset: 0;
        background: color-mix(in srgb, var(--mat-sys-surface-container-low) 95%, transparent);
        z-index: 101;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .error-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
        text-align: center;
        max-width: 400px;
        padding: 24px;
      }

      .error-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        margin-bottom: 8px;
      }

      .error-message {
        color: var(--mat-sys-error);
        font-weight: 500;
        margin-bottom: 16px;
      }

      @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }

      /* Direct Control Dashboard */
      .direct-control-dashboard {
        display: flex;
        height: 100%;
        background: var(--mat-sys-surface-container-low);
      }

      .machine-selector-panel {
        width: 280px;
        min-width: 280px;
        border-right: 1px solid var(--mat-sys-outline-variant);
        background: var(--mat-sys-surface-container);
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }

      .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        border-bottom: 1px solid var(--mat-sys-outline-variant);
        background: var(--mat-sys-surface-container-high);
      }

      .panel-header h3 {
        margin: 0;
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--mat-sys-on-surface);
      }

      .machine-list {
        flex: 1;
        overflow-y: auto;
        padding: 8px;
      }

      .machine-card {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        border-radius: 8px;
        cursor: pointer;
        transition: background-color 0.15s ease, box-shadow 0.15s ease;
        margin-bottom: 4px;
        background: var(--mat-sys-surface);
        border: 1px solid transparent;
      }

      .machine-card:hover {
        background: var(--mat-sys-surface-container-highest);
      }

      .machine-card.selected {
        background: color-mix(in srgb, var(--mat-sys-primary) 12%, var(--mat-sys-surface));
        border-color: var(--mat-sys-primary);
      }

      .machine-icon {
        width: 40px;
        height: 40px;
        border-radius: 8px;
        background: var(--mat-sys-primary-container);
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }

      .machine-icon mat-icon {
        color: var(--mat-sys-on-primary-container);
      }

      .machine-info {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 2px;
      }

      .machine-name {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--mat-sys-on-surface);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .machine-category {
        font-size: 0.75rem;
        color: var(--mat-sys-on-surface-variant);
      }

      .machine-status {
        flex-shrink: 0;
      }

      .status-dot {
        display: block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--mat-sys-outline);
      }

      .machine-status.idle .status-dot {
        background: var(--mat-sys-tertiary);
      }

      .machine-status.running .status-dot,
      .machine-status.connected .status-dot {
        background: var(--mat-sys-primary);
        animation: pulse 2s infinite;
      }

      .machine-status.error .status-dot {
        background: var(--mat-sys-error);
      }

      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
      }

      .empty-machines {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        padding: 24px;
        gap: 12px;
        color: var(--mat-sys-on-surface-variant);
        text-align: center;
      }

      .empty-machines mat-icon {
        font-size: 40px;
        width: 40px;
        height: 40px;
        opacity: 0.5;
      }

      .empty-machines p {
        margin: 0;
        font-size: 0.875rem;
      }

      .control-panel {
        flex: 1;
        overflow-y: auto;
        padding: 24px;
        min-width: 0;
      }
    `,
  ],
})
export class PlaygroundComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('notebookFrame') notebookFrame!: ElementRef<HTMLIFrameElement>;
  @ViewChild(DirectControlComponent) directControlComponent?: DirectControlComponent;

  private modeService = inject(ModeService);
  private snackBar = inject(MatSnackBar);
  private cdr = inject(ChangeDetectorRef);
  private assetService = inject(AssetService);
  private sqliteService = inject(SqliteService);
  private dialog = inject(MatDialog);
  private interactionService = inject(InteractionService);
  private jupyterChannel = inject(JupyterChannelService);
  public jupyterliteService = inject(PlaygroundJupyterliteService);

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
      height: 'auto',
      minHeight: '400px',
      maxHeight: '90vh',
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

  /* Helper methods for Code Generation */

  /**
   * Generate a Python-safe variable name from an asset
   */
  private assetToVarName(asset: { name: string; accession_id: string }): string {
    // Convert name to snake_case and add UUID prefix
    const desc = asset.name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_|_$/g, '');
    const prefix = asset.accession_id.slice(0, 6);
    return `${desc}_${prefix}`;
  }



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
            (function() {
              const originalFetch = window.fetch;
              window.fetch = function(input, init) {
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
   * Generate Python code to instantiate a resource
   */
  private generateResourceCode(resource: Resource, variableName?: string): string {
    const varName = variableName || this.assetToVarName(resource);
    const fqn = resource.fqn || resource.plr_definition?.fqn;
    const safeName = resource.name.replace(/['"\\]/g, '_');

    if (!fqn) {
      return `# Resource: ${safeName} (no FQN available)`;
    }

    const lines = [
      `# Resource: ${safeName}`,
      `from web_bridge import instantiate_resource`,
      `${varName} = instantiate_resource("${fqn}", "${varName}")`,
      `print(f"Created: {${varName}}")`
    ];

    return lines.join('\n');
  }

  /**
   * Generate Python code to instantiate a machine.
   */
  private async generateMachineCode(machine: Machine, variableName?: string, deckConfigId?: string): Promise<string> {
    const varName = variableName || this.assetToVarName(machine);
    const safeName = machine.name.replace(/['"\\]/g, '_');

    // Extract backend FQN
    const backendFqn = machine.plr_definition?.fqn || machine.backend_definition?.fqn || machine.simulation_backend_name;
    const isSimulated = !!(machine.is_simulation_override || machine.simulation_backend_name);
    const category = (machine as any).machine_category || 'LiquidHandler';

    const config = {
      backend_fqn: backendFqn || 'pylabrobot.liquid_handling.backends.simulation.SimulatorBackend',
      port_id: machine.connection_info?.['address'] || machine.connection_info?.['port_id'] || '',
      is_simulated: isSimulated,
      baudrate: machine.connection_info?.['baudrate'] || 9600
    };

    const lines = [
      `# Machine: ${safeName}`,
      `from web_bridge import create_configured_backend, create_machine_frontend`,
      ``,
      `config = ${JSON.stringify(config, null, 2)}`,
      `backend = create_configured_backend(config)`,
      `${varName} = create_machine_frontend("${category}", backend, name="${safeName}")`,
      `await ${varName}.setup()`,
      `print(f"Created: {${varName}}")`
    ];

    return lines.join('\n');
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
    const varName = variableName || this.assetToVarName(asset);

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

    // Generate appropriate Python code
    let code: string;
    if (type === 'machine') {
      code = await this.generateMachineCode(asset as Machine, varName, deckConfigId);
    } else {
      code = this.generateResourceCode(asset as Resource, varName);
    }

    // Send code via JupyterChannelService
    try {
      this.jupyterChannel.sendMessage({
        type: 'praxis:execute',
        code: code
      });
      this.snackBar.open(`Inserted ${varName}`, 'OK', { duration: 2000 });
    } catch (e) {
      console.error('Failed to send asset to REPL:', e);
      // Fallback: copy code to clipboard
      navigator.clipboard.writeText(code).then(() => {
        this.snackBar.open(`Code copied to clipboard (channel send failed)`, 'OK', {
          duration: 2000,
        });
      });
    }
  }

  /**
   * Handle executeCommand from DirectControlComponent
   * Uses a dedicated Pyodide kernel that persists across tab switches
   */


  async onExecuteCommand(event: { machineName: string, methodName: string, args: Record<string, unknown> }) {
    const { machineName, methodName, args } = event;
    console.log(`[DirectControl] Executing ${methodName} on ${machineName}`, args);

    // Find machine asset
    const machines = this.availableMachines();
    const asset = machines.find(m => m.name === machineName);
    if (!asset) {
      const err = `Machine ${machineName} not found`;
      this.snackBar.open(err, 'OK');
      this.directControlComponent?.handleCommandError(err);
      return;
    }

    const varName = this.assetToVarName(asset);
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
      this.snackBar.open(`Error: ${errorMsg.substring(0, 80)}`, 'Dismiss', { duration: 5000 });
      // AUDIT-09: Pass error to DirectControl
      this.directControlComponent?.handleCommandError(errorMsg);
    }
  }
}
