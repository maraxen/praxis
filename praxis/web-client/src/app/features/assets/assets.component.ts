import { Component, ChangeDetectionStrategy, inject, ViewChild, signal, OnInit, OnDestroy, NgZone } from '@angular/core';

import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MachineListComponent } from './components/machine-list/machine-list.component';
import { ResourceAccordionComponent } from './components/resource-accordion/resource-accordion.component';
import { DefinitionsListComponent } from './components/definitions-list/definitions-list.component';
import { AssetWizard } from '@shared/components/asset-wizard/asset-wizard';
import { HardwareDiscoveryDialogComponent } from '@shared/components/hardware-discovery-dialog/hardware-discovery-dialog.component';
import { HardwareDiscoveryButtonComponent } from '@shared/components/hardware-discovery-button/hardware-discovery-button.component';
import { AssetDashboardComponent } from './components/asset-dashboard/asset-dashboard.component';
import { SpatialViewComponent } from './components/spatial-view/spatial-view.component';
import { AssetService } from './services/asset.service';
import { finalize } from 'rxjs/operators';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, Router } from '@angular/router';
import { ModeService } from '@core/services/mode.service';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { SqliteService } from '@core/services/sqlite';
import { ConfirmationDialogComponent } from '@shared/components/confirmation-dialog';

@Component({
  selector: 'app-assets',
  standalone: true,
  imports: [
    MatTabsModule,
    MatIconModule,
    MatButtonModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatSnackBarModule,
    MachineListComponent,
    ResourceAccordionComponent,
    DefinitionsListComponent,
    AssetDashboardComponent,
    SpatialViewComponent,
    HardwareDiscoveryButtonComponent
  ],
  template: `
    <div class="p-6 max-w-screen-2xl mx-auto h-full flex flex-col">
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
        <div class="min-w-0 flex-1">
          <h1 class="text-3xl font-bold text-sys-text-primary mb-1 truncate">Asset Management</h1>
          <p class="text-sys-text-secondary truncate">Manage your laboratory hardware and inventory</p>
        </div>
        <div class="flex flex-wrap items-center gap-2 sm:gap-3 w-full sm:w-auto">
          <app-hardware-discovery-button class="sm:mr-2"></app-hardware-discovery-button>
          <span class="flex-1 sm:flex-initial" [matTooltip]="selectedIndex === 4 ? (modeService.isBrowserMode() ? 'Resource definitions are loaded from bundled data in Browser Mode.' : 'Sync all hardware and protocol definitions from the backend.') : ''">
            <button 
              mat-flat-button 
              class="!bg-gradient-to-br !from-primary !to-primary-dark !text-white !rounded-full !px-6 !py-3 !font-semibold shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed w-full sm:w-auto" 
              (click)="openAddAsset()" 
              [disabled]="isLoading() || isSyncing()"
              data-tour-id="add-asset-btn"
            >
              <mat-icon>{{ selectedIndex === 4 ? 'sync' : 'add' }}</mat-icon>
              {{ selectedIndex === 4 ? 'Sync Definitions' : 'Add ' + assetTypeLabel() }}
            </button>
          </span>
        </div>
      </div>

      <div class="bg-surface border border-[var(--theme-border)] rounded-3xl overflow-hidden backdrop-blur-xl flex flex-col flex-1 min-h-0 shadow-xl relative">
        <mat-tab-group 
          animationDuration="300ms" 
          class="assets-tabs flex-1 flex flex-col min-h-0 custom-tabs" 
          [(selectedIndex)]="selectedIndex" 
          (selectedIndexChange)="onTabChange($event)"
          mat-stretch-tabs="false" 
          mat-align-tabs="start"
        >
          <mat-tab>
            <ng-template mat-tab-label>
              <div class="flex items-center gap-2 px-2 py-1">
                <mat-icon class="!w-5 !h-5 !text-[20px]">dashboard</mat-icon>
                <span class="font-medium">Overview</span>
              </div>
            </ng-template>
            <div class="h-full overflow-hidden bg-[var(--mat-sys-surface-variant)] relative p-4">
              <app-asset-dashboard></app-asset-dashboard>
            </div>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <div class="flex items-center gap-2 px-2 py-1">
                <mat-icon class="!w-5 !h-5 !text-[20px]">map</mat-icon>
                <span class="font-medium">Spatial View</span>
              </div>
            </ng-template>
            <div class="h-full overflow-hidden bg-[var(--mat-sys-surface-variant)] relative">
              <app-spatial-view></app-spatial-view>
            </div>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <div class="flex items-center gap-2 px-2 py-1">
                <mat-icon class="!w-5 !h-5 !text-[20px]">precision_manufacturing</mat-icon>
                <span class="font-medium">Machines</span>
              </div>
            </ng-template>
            <div class="h-full overflow-y-auto bg-[var(--mat-sys-surface-variant)] relative">
              @if (isLoading()) {
                <div class="absolute inset-0 bg-[var(--mat-sys-surface-variant)] backdrop-blur-sm z-10 flex items-center justify-center">
                  <mat-spinner diameter="40"></mat-spinner>
                </div>
              }
              <app-machine-list #machineList data-tour-id="machine-list"></app-machine-list>
            </div>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <div class="flex items-center gap-2 px-2 py-1">
                <mat-icon class="!w-5 !h-5 !text-[20px]">science</mat-icon>
                <span class="font-medium">Resources</span>
              </div>
            </ng-template>
            <div class="h-full overflow-y-auto bg-[var(--mat-sys-surface-variant)] relative">
              @if (isLoading()) {
                <div class="absolute inset-0 bg-[var(--mat-sys-surface-variant)] backdrop-blur-sm z-10 flex items-center justify-center">
                  <mat-spinner diameter="40"></mat-spinner>
                </div>
              }
              <app-resource-accordion #resourceAccordion data-tour-id="resource-list"></app-resource-accordion>
            </div>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <div class="flex items-center gap-2 px-2 py-1">
                <mat-icon class="!w-5 !h-5 !text-[20px]">inventory_2</mat-icon>
                <span class="font-medium">Registry</span>
              </div>
            </ng-template>
            <div class="h-full overflow-y-auto bg-[var(--mat-sys-surface-variant)] relative">
              @if (isSyncing()) {
                <div class="absolute inset-0 bg-[var(--mat-sys-surface-variant)] backdrop-blur-sm z-10 flex items-center justify-center">
                  <mat-spinner diameter="40"></mat-spinner>
                </div>
              }
              <app-definitions-list></app-definitions-list>
            </div>
          </mat-tab>
        </mat-tab-group>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: 100%;
    }

    /* Custom Mat Tab Styling */
    ::ng-deep .custom-tabs .mat-mdc-tab-header {
      border-bottom: none !important;
      background: var(--mat-sys-surface-variant); /* Slightly lighter header */
    }

    ::ng-deep .custom-tabs .mat-mdc-tab-label-container {
      padding: 0 16px;
    }

    ::ng-deep .custom-tabs .mdc-tab {
      color: var(--theme-text-secondary) !important;
      font-family: inherit !important;
      letter-spacing: normal !important;
      min-width: 80px !important;
      padding: 0 20px !important;
      height: 56px !important;
      opacity: 1 !important;
    }

    ::ng-deep .custom-tabs .mdc-tab__content {
      flex: 0 1 auto !important;
    }

    ::ng-deep .custom-tabs .mdc-tab--active {
      color: var(--theme-text-primary) !important;
    }

    ::ng-deep .custom-tabs .mdc-tab--active .mdc-tab__text-label {
      color: var(--primary-color) !important;
    }

    ::ng-deep .custom-tabs .mdc-tab--active .mat-icon {
      color: var(--primary-color) !important;
    }

    ::ng-deep .custom-tabs .mat-mdc-tab-group-indicator {
      border-bottom-color: var(--primary-color) !important;
      height: 3px !important;
      border-radius: 3px 3px 0 0;
    }

    ::ng-deep .custom-tabs .mat-mdc-tab-body-wrapper {
      flex: 1;
      height: 100%;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AssetsComponent implements OnInit, OnDestroy {
  private dialog = inject(MatDialog);
  private assetService = inject(AssetService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private ngZone = inject(NgZone);
  public modeService = inject(ModeService);
  private snackBar = inject(MatSnackBar);
  private sqlite = inject(SqliteService);

  @ViewChild('machineList') machineList!: MachineListComponent;
  @ViewChild('resourceAccordion') resourceAccordion!: ResourceAccordionComponent;

  selectedIndex = 0;
  assetTypeLabel = signal('Machine');
  isLoading = signal(false);
  isSyncing = signal(false);

  private hardwareDiscoveryListener = () => {
    this.ngZone.run(() => this.openHardwareDiscovery());
  };

  ngOnInit() {
    // Listen for command palette hardware discovery event
    window.addEventListener('open-hardware-discovery', this.hardwareDiscoveryListener);
    window.addEventListener('asset-dashboard-action', this.dashboardActionListener);

    // Listen to query params to switch tabs
    this.route.queryParams.subscribe(params => {
      const type = params['type'];
      if (type === 'machine') {
        this.selectedIndex = 2;
        this.assetTypeLabel.set('Machine');
      } else if (type === 'resource') {
        this.selectedIndex = 3;
        this.assetTypeLabel.set('Resource');
      } else if (type === 'registry' || type === 'definition') {
        this.selectedIndex = 4;
        this.assetTypeLabel.set('Registry Item');
      } else if (type === 'spatial') {
        this.selectedIndex = 1;
        this.assetTypeLabel.set('Asset');
      } else {
        this.selectedIndex = 0;
        this.assetTypeLabel.set('Asset');
      }
    });
  }

  ngOnDestroy() {
    window.removeEventListener('open-hardware-discovery', this.hardwareDiscoveryListener);
    window.removeEventListener('asset-dashboard-action', this.dashboardActionListener);
  }

  onTabChange(index: number) {
    this.selectedIndex = index;
    let type = 'overview';

    switch (index) {
      case 0:
        this.assetTypeLabel.set('Asset');
        type = 'overview';
        break;
      case 1:
        this.assetTypeLabel.set('Asset');
        type = 'spatial';
        break;
      case 2:
        this.assetTypeLabel.set('Machine');
        type = 'machine';
        break;
      case 3:
        this.assetTypeLabel.set('Resource');
        type = 'resource';
        break;
      case 4:
        this.assetTypeLabel.set('Registry Item');
        type = 'registry';
        break;
    }

    // Update URL without reloading
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { type },
      queryParamsHandling: 'merge', // merge with other existing query params
      replaceUrl: true // prevent pushing a new history state for every tab click
    });
  }

  private dashboardActionListener = (event: Event) => {
    const action = (event as CustomEvent).detail;
    this.ngZone.run(() => {
      if (action === 'add-machine') this.openAddMachine();
      if (action === 'add-resource') this.openAddResource();
      if (action === 'discover') this.openHardwareDiscovery();
      if (action === 'reset-lab') this.resetLab();
    });
  };

  private resetLab() {
    const dialogRef = this.dialog.open(ConfirmationDialogComponent, {
      data: {
        title: 'Reset Lab to Defaults?',
        message: 'This will delete all custom resources, machines, and protocol run history, then restore the default simulated lab. This action cannot be undone.',
        confirmText: 'Reset Everything',
        color: 'warn',
        icon: 'restart_alt'
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.snackBar.open('Resetting lab...', '', { duration: 0 });
        this.sqlite.resetToDefaults().subscribe({
          next: () => {
            this.snackBar.open('Lab reset complete. Reloading...', 'OK', { duration: 2000 });
            setTimeout(() => window.location.reload(), 1500);
          },
          error: (err: Error) => {
            console.error('[Assets] Reset failed:', err);
            this.snackBar.open('Reset failed: ' + err.message, 'Close', { duration: 5000 });
          }
        });
      }
    });
  }

  openAddAsset() {
    if (this.isLoading()) return; // Prevent multiple clicks

    if (this.selectedIndex === 2) { // Machines tab
      this.openAddMachine();
    } else if (this.selectedIndex === 3) { // Resources tab
      this.openAddResource();
    } else if (this.selectedIndex === 0 || this.selectedIndex === 1) {
      // Overview or Spatial View - prompt for choice
      this.openAddAssetChoice();
    } else if (this.selectedIndex === 4) {
      // Registry tab
      if (this.modeService.isBrowserMode()) {
        this.snackBar.open('Resource definitions are loaded from bundled data in Browser Mode. Connect to a backend to add custom definitions.', 'Close', { duration: 5000 });
        return;
      }
      this.triggerSyncDefinitions();
    }
  }

  private openAddAssetChoice() {
    this.openUnifiedDialog();
  }

  private triggerSyncDefinitions() {
    this.isSyncing.set(true);
    this.assetService.syncDefinitions().pipe(
      finalize(() => this.isSyncing.set(false))
    ).subscribe({
      next: (resp) => {
        this.snackBar.open(resp.message || 'Synchronization started successfully.', 'Close', { duration: 3000 });
      },
      error: (err) => {
        console.error('Error during synchronization', err);
        this.snackBar.open('Failed to initiate synchronization. See console for details.', 'Close', { duration: 5000 });
      }
    });
  }

  private openAddMachine() {
    this.openUnifiedDialog('machine');
  }

  private openAddResource() {
    this.openUnifiedDialog('resource');
  }

  private openUnifiedDialog(type: 'machine' | 'resource' | null = null) {
    const dialogRef = this.dialog.open(AssetWizard, {
      minWidth: '600px',
      maxWidth: '1000px',
      width: '80vw',
      height: 'auto',
      minHeight: '400px',
      maxHeight: '90vh',
      data: type ? { preselectedType: type.toUpperCase() } : {}
    });

    // AssetWizard handles the creation itself, so we just need to refresh the lists
    dialogRef.afterClosed().subscribe(result => {
      if (result) {
        this.machineList?.loadMachines();
        this.resourceAccordion?.loadData();
      }
    });
  }

  openHardwareDiscovery() {
    const dialogRef = this.dialog.open(HardwareDiscoveryDialogComponent, {
      width: '1000px',
      maxHeight: '90vh'
    });

    // Refresh machine list after hardware discovery dialog closes
    // (machines may have been registered during discovery)
    dialogRef.afterClosed().subscribe(() => {
      this.machineList?.loadMachines();
    });
  }
}
