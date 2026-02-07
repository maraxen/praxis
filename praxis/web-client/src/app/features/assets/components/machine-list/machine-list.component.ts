import { Component, ChangeDetectionStrategy, inject, signal, ViewChild, computed, OnInit, OnDestroy } from '@angular/core';

import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatMenuModule, MatMenuTrigger } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AssetService } from '../../services/asset.service';
import { Machine, MachineDefinition } from '../../models/asset.models';
import { AssetStatusChipComponent } from '../asset-status-chip/asset-status-chip.component';
import { LocationBreadcrumbComponent } from '../location-breadcrumb/location-breadcrumb.component';
import { MaintenanceBadgeComponent } from '../maintenance-badge/maintenance-badge.component';
import { MachineDetailsDialogComponent } from './machine-details-dialog.component';
import { ViewControlsComponent } from '@shared/components/view-controls/view-controls.component';
import { ViewControlsConfig, ViewControlsState } from '@shared/components/view-controls/view-controls.types';
import { AppStore } from '@core/store/app.store';

@Component({
  selector: 'app-machine-list',
  standalone: true,
  imports: [
    MatTableModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatInputModule,
    MatMenuModule,
    MatDividerModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    AssetStatusChipComponent,
    LocationBreadcrumbComponent,
    MaintenanceBadgeComponent,
    ViewControlsComponent
  ],
  template: `
    <div class="machine-list-container">
      <!-- Standardized View Controls -->
      <div class="bg-[var(--mat-sys-surface)] border-b border-[var(--theme-border)] px-4 py-2 mb-4 rounded-xl shadow-sm">
        <app-view-controls
          [config]="viewConfig()"
          [state]="viewState()"
          (stateChange)="onViewStateChange($event)">
        </app-view-controls>
      </div>

      <!-- Content Area -->
      <div class="flex-1 overflow-hidden relative">
        @if (isLoading()) {
          <div class="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-black/50 z-20 backdrop-blur-sm rounded-xl">
            <mat-spinner diameter="40"></mat-spinner>
          </div>
        }

        <!-- Table View -->
        @if (viewState().viewType === 'table') {
          <div class="bg-[var(--mat-sys-surface)] border border-[var(--theme-border)] rounded-xl overflow-hidden shadow-sm">
            <table mat-table [dataSource]="filteredMachines()" class="w-full">
              <!-- Name Column -->
              <ng-container matColumnDef="name">
                <th mat-header-cell *matHeaderCellDef> Name </th>
                <td mat-cell *matCellDef="let machine"> {{ machine.name }} </td>
              </ng-container>

              <!-- Simulated Indicator -->
              <ng-container matColumnDef="simulated">
                <th mat-header-cell *matHeaderCellDef> Mode </th>
                <td mat-cell *matCellDef="let machine">
                  @if (machine.is_simulation_override) {
                    <mat-chip class="simulated-chip" [highlighted]="false">
                      <mat-icon class="chip-icon">computer</mat-icon>
                      Simulated
                    </mat-chip>
                  } @else {
                    <mat-chip class="physical-chip" [highlighted]="false">
                      <mat-icon class="chip-icon">precision_manufacturing</mat-icon>
                      Physical
                    </mat-chip>
                  }
                </td>
              </ng-container>

              <!-- Status Column -->
              <ng-container matColumnDef="status">
                <th mat-header-cell *matHeaderCellDef> Status </th>
                <td mat-cell *matCellDef="let machine">
                  <app-asset-status-chip [status]="machine.status" [showLabel]="true" />
                </td>
              </ng-container>

              <!-- Category Column -->
              <ng-container matColumnDef="category">
                <th mat-header-cell *matHeaderCellDef> Category </th>
                <td mat-cell *matCellDef="let machine"> {{ machine.machine_category || 'Unknown' }} </td>
              </ng-container>

              <!-- Model Column -->
              <ng-container matColumnDef="model">
                <th mat-header-cell *matHeaderCellDef> Model </th>
                <td mat-cell *matCellDef="let machine"> {{ machine.model || 'N/A' }} </td>
              </ng-container>

              <!-- Location Column -->
              <ng-container matColumnDef="location">
                <th mat-header-cell *matHeaderCellDef> Location </th>
                <td mat-cell *matCellDef="let machine">
                    <app-location-breadcrumb [location]="machine.location"></app-location-breadcrumb>
                </td>
              </ng-container>

              <!-- Maintenance Column -->
              <ng-container matColumnDef="maintenance">
                <th mat-header-cell *matHeaderCellDef> Maintenance </th>
                <td mat-cell *matCellDef="let machine">
                    <app-maintenance-badge [machine]="machine" />
                </td>
              </ng-container>

              <!-- Actions Column -->
              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef> Actions </th>
                <td mat-cell *matCellDef="let machine">
                  <button mat-icon-button color="primary" matTooltip="View Details" (click)="viewDetails(machine)">
                    <mat-icon>info</mat-icon>
                  </button>
                  <button mat-icon-button color="accent" matTooltip="Edit Machine" (click)="editMachine(machine)">
                    <mat-icon>edit</mat-icon>
                  </button>
                  <button mat-icon-button color="warn" matTooltip="Delete Machine" (click)="deleteMachine(machine)">
                    <mat-icon>delete</mat-icon>
                  </button>
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="displayedColumns()"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedColumns();" 
                  (contextmenu)="onContextMenu($event, row)"
                  class="machine-row"></tr>

              <tr class="mat-row" *matNoDataRow>
                <td class="mat-cell" colspan="7">No machines matching the selected filters</td>
              </tr>
            </table>
          </div>
        }

        <!-- Card View -->
        @if (viewState().viewType === 'card') {
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            @for (machine of filteredMachines(); track machine.accession_id) {
              <div class="praxis-card premium group cursor-pointer"
                   (click)="viewDetails(machine)"
                   (contextmenu)="onContextMenu($event, machine)">
                
                <div class="card-header">
                  <div class="flex items-center gap-3 min-w-0">
                    <div class="w-10 h-10 rounded-lg flex-shrink-0 flex items-center justify-center bg-[var(--mat-sys-primary-container)] text-[var(--mat-sys-primary)]">
                      <mat-icon>{{ machine.is_simulation_override ? 'computer' : 'precision_manufacturing' }}</mat-icon>
                    </div>
                    <div class="min-w-0">
                      <h3 class="card-title group-hover:text-[var(--mat-sys-primary)] transition-colors">{{ machine.name }}</h3>
                      <p class="card-subtitle">{{ machine.model || machine.machine_category }}</p>
                    </div>
                  </div>
                </div>

                <div class="card-content">
                  <div class="card-meta mb-2">
                    <mat-icon class="!w-3 !h-3 !text-[12px]">location_on</mat-icon>
                    <span class="truncate">{{ machine.location_label || 'Unassigned' }}</span>
                  </div>
                </div>

                <div class="card-actions">
                  <app-asset-status-chip [status]="machine.status" />
                  @if (store.maintenanceEnabled()) {
                    <app-maintenance-badge [machine]="machine" />
                  }
                </div>
              </div>
            }
          </div>
        }

        <!-- List View -->
        @if (viewState().viewType === 'list') {
          <div class="flex flex-col gap-2">
            @for (machine of filteredMachines(); track machine.accession_id) {
              <div class="flex items-center gap-4 p-3 bg-[var(--mat-sys-surface)] border border-[var(--theme-border)] rounded-xl hover:bg-[var(--mat-sys-surface-container-highest)] cursor-pointer"
                   (click)="viewDetails(machine)">
                <mat-icon class="text-[var(--mat-sys-primary)]">{{ machine.is_simulation_override ? 'computer' : 'precision_manufacturing' }}</mat-icon>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="font-bold truncate">{{ machine.name }}</span>
                    <span class="text-xs text-[var(--mat-sys-on-surface-variant)]">{{ machine.machine_category }}</span>
                  </div>
                </div>
                <app-asset-status-chip [status]="machine.status" />
                <div class="flex items-center gap-1">
                  <button mat-icon-button (click)="$event.stopPropagation(); editMachine(machine)"><mat-icon>edit</mat-icon></button>
                  <button mat-icon-button color="warn" (click)="$event.stopPropagation(); deleteMachine(machine)"><mat-icon>delete</mat-icon></button>
                </div>
              </div>
            }
          </div>
        }

        @if (!isLoading() && filteredMachines().length === 0) {
          <div class="flex flex-col items-center justify-center p-12 text-[var(--mat-sys-on-surface-variant)]">
            <mat-icon class="!w-12 !h-12 !text-[48px] mb-4 opacity-20">inventory_2</mat-icon>
            <p>No machines matching the current filters.</p>
          </div>
        }
      </div>

      <!-- Context Menu -->
      <div style="visibility: hidden; position: fixed"
           [style.left]="contextMenuPosition.x"
           [style.top]="contextMenuPosition.y"
           [matMenuTriggerFor]="contextMenu">
      </div>
      <mat-menu #contextMenu="matMenu">
        <ng-template matMenuContent let-item="item">
          <button mat-menu-item (click)="editMachine(item)">
            <mat-icon>edit</mat-icon>
            <span>Edit</span>
          </button>
          <button mat-menu-item (click)="duplicateMachine(item)">
            <mat-icon>content_copy</mat-icon>
            <span>Duplicate</span>
          </button>
          <mat-divider></mat-divider>
          <button mat-menu-item (click)="deleteMachine(item)">
            <mat-icon color="warn">delete</mat-icon>
            <span style="color: var(--mat-sys-error)">Delete</span>
          </button>
        </ng-template>
      </mat-menu>
    </div>
  `,
  styles: [`
    .machine-list-container {
      padding: 0 16px 16px 16px;
    }

    .mat-elevation-z2 {
      width: 100%;
    }

    .machine-row:hover {
      background-color: var(--mat-sys-surface-container-highest);
      cursor: pointer;
    }

    .mat-no-data-row {
      text-align: center;
      font-style: italic;
      color: var(--mat-sys-color-on-surface-variant);
    }

    .simulated-chip {
      --mdc-chip-container-height: 24px;
      font-size: 0.75rem;
      background: var(--mat-sys-tertiary-container);
      color: var(--mat-sys-tertiary);
    }

    .physical-chip {
      --mdc-chip-container-height: 24px;
      font-size: 0.75rem;
      background: var(--mat-sys-success-container);
      color: var(--mat-sys-success);
    }

    :host ::ng-deep .chip-icon {
      font-size: 14px;
      width: 14px;
      height: 14px;
      margin-right: 4px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MachineListComponent implements OnInit, OnDestroy {
  private assetService = inject(AssetService);
  private dialog = inject(MatDialog);
  public store = inject(AppStore);

  machines = signal<Machine[]>([]);
  machineDefinitions = signal<MachineDefinition[]>([]);
  isLoading = signal(true);

  // Standardized View Controls
  viewConfig = computed<ViewControlsConfig>(() => ({
    viewTypes: ['table', 'card', 'list'],
    groupByOptions: [
      { label: 'Status', value: 'status' },
      { label: 'Category', value: 'machine_category' },
    ],
    filters: [
      {
        key: 'status',
        label: 'Status',
        type: 'multiselect',
        options: [
          { label: 'Idle', value: 'idle', icon: 'hourglass_empty' },
          { label: 'Running', value: 'running', icon: 'play_arrow' },
          { label: 'Error', value: 'error', icon: 'error_outline' },
          { label: 'Offline', value: 'offline', icon: 'wifi_off' },
          { label: 'Maintenance', value: 'maintenance', icon: 'build' }
        ]
      },
      {
        key: 'category',
        label: 'Category',
        type: 'chips',
        options: this.availableCategories().map(cat => ({ label: cat, value: cat }))
      },
      {
        key: 'simulated',
        label: 'Mode',
        type: 'select',
        options: [
          { label: 'All', value: null },
          { label: 'Physical', value: false, icon: 'precision_manufacturing' },
          { label: 'Simulated', value: true, icon: 'computer' }
        ]
      },
      {
        key: 'backends',
        label: 'Backend',
        type: 'multiselect',
        options: this.availableBackends().map(b => ({ label: b, value: b }))
      }
    ],
    sortOptions: [
      { label: 'Name', value: 'name' },
      { label: 'Category', value: 'category' },
      { label: 'Status', value: 'status' },
      { label: 'Date Added', value: 'created_at' }
    ],
    storageKey: 'machine-list',
    defaults: {
      viewType: 'table',
      sortBy: 'name',
      sortOrder: 'asc'
    }
  }));

  viewState = signal<ViewControlsState>({
    viewType: 'table',
    groupBy: null,
    filters: {},
    sortBy: 'name',
    sortOrder: 'asc',
    search: ''
  });

  availableCategories = computed(() => {
    const cats = new Set<string>();
    this.machines().forEach(m => {
      if (m.machine_category) cats.add(m.machine_category);
    });
    return Array.from(cats).sort();
  });

  availableBackends = computed(() => {
    const backends = new Set<string>();
    this.machineDefinitions().forEach(def => {
      if (def.compatible_backends) {
        def.compatible_backends.forEach(b => backends.add(b));
      }
    });
    return Array.from(backends).sort();
  });

  displayedColumns = computed(() => {
    const cols = ['name', 'simulated', 'status', 'category', 'model', 'location'];
    if (this.store.maintenanceEnabled()) {
      cols.push('maintenance');
    }
    cols.push('actions');
    return cols;
  });

  @ViewChild(MatMenuTrigger) contextMenuTrigger!: MatMenuTrigger;
  contextMenuPosition = { x: '0px', y: '0px' };

  // Listener for global machine-registered event (from hardware discovery)
  private machineRegisteredListener = () => {
    this.loadMachines();
  };

  ngOnInit() {
    this.loadMachines();
    this.loadMachineDefinitions();

    // Listen for machines registered via hardware discovery
    window.addEventListener('machine-registered', this.machineRegisteredListener);
  }

  ngOnDestroy() {
    window.removeEventListener('machine-registered', this.machineRegisteredListener);
  }

  loadMachines(): void {
    this.isLoading.set(true);
    this.assetService.getMachines().subscribe({
      next: (data: Machine[]) => {
        this.machines.set(data);
        this.isLoading.set(false);
      },
      error: (error: Error) => {
        console.error('[ASSET-DEBUG] loadMachines: Error fetching machines:', error);
        this.isLoading.set(false);
      }
    });
  }

  loadMachineDefinitions(): void {
    this.assetService.getMachineDefinitions().subscribe({
      next: (defs: MachineDefinition[]) => this.machineDefinitions.set(defs),
      error: (err: Error) => console.error('[ASSET-DEBUG] Error loading machine definitions:', err)
    });
  }

  onViewStateChange(state: ViewControlsState) {
    this.viewState.set(state);
  }

  filteredMachines = computed(() => {
    let filtered = this.machines();
    const state = this.viewState();

    // 1. Search Filter
    if (state.search) {
      const search = state.search.toLowerCase();
      filtered = filtered.filter(m =>
        m.name.toLowerCase().includes(search) ||
        m.machine_category?.toLowerCase().includes(search) ||
        m.model?.toLowerCase().includes(search) ||
        m.manufacturer?.toLowerCase().includes(search)
      );
    }

    // 2. Status Filter
    const statusFilters = state.filters['status'] || [];
    if (statusFilters.length > 0) {
      filtered = filtered.filter(m => statusFilters.includes(m.status));
    }

    // 3. Category Filter
    const categoryFilters = state.filters['category'] || [];
    if (categoryFilters.length > 0) {
      filtered = filtered.filter(m =>
        m.machine_category && categoryFilters.includes(m.machine_category)
      );
    }

    // 4. Simulated Filter
    const simulatedFilter = state.filters['simulated']?.[0];
    if (simulatedFilter !== undefined && simulatedFilter !== null) {
      filtered = filtered.filter(m =>
        (m.is_simulation_override ?? false) === simulatedFilter
      );
    }

    // 5. Backend Filter
    const backendFilters = state.filters['backends'] || [];
    if (backendFilters.length > 0) {
      // requires joining with definitions or property on machine if available
      // For now skip as per original implementation note
    }

    // 6. Sort
    return [...filtered].sort((a, b) => {
      let valA: string | number = '';
      let valB: string | number = '';

      switch (state.sortBy) {
        case 'name':
          valA = a.name.toLowerCase();
          valB = b.name.toLowerCase();
          break;
        case 'category':
          valA = (a.machine_category || '').toLowerCase();
          valB = (b.machine_category || '').toLowerCase();
          break;
        case 'created_at':
          valA = new Date(a.created_at || 0).getTime();
          valB = new Date(b.created_at || 0).getTime();
          break;
        case 'status':
          valA = a.status;
          valB = b.status;
          break;
      }

      const comparison = valA > valB ? 1 : (valA < valB ? -1 : 0);
      return state.sortOrder === 'asc' ? comparison : -comparison;
    });
  });

  onContextMenu(event: MouseEvent, machine: Machine) {
    event.preventDefault();
    this.contextMenuPosition.x = event.clientX + 'px';
    this.contextMenuPosition.y = event.clientY + 'px';
    this.contextMenuTrigger.menuData = { item: machine };
    this.contextMenuTrigger.openMenu();
  }

  viewDetails(machine: Machine) {
    this.dialog.open(MachineDetailsDialogComponent, {
      width: '800px', // Wider to accommodate tabs and deck view
      data: { machine }
    });
  }

  editMachine(_machine: Machine) {
    // TODO: Implement machine editing
  }

  duplicateMachine(_machine: Machine) {
    // TODO: Implement machine duplication
  }

  deleteMachine(machine: Machine) {
    if (confirm(`Are you sure you want to delete machine "${machine.name}"?`)) {
      this.assetService.deleteMachine(machine.accession_id).subscribe({
        next: () => {
          this.loadMachines();
        },
        error: (err) => console.error('Error deleting machine', err)
      });
    }
  }
}
