import { Component, inject, signal, computed, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { forkJoin } from 'rxjs';

import { AssetService } from '../../services/asset.service';
import { AssetStatusChipComponent } from '../asset-status-chip/asset-status-chip.component';
import { Machine, Resource, Workcell } from '../../models/asset.models';
import { ViewControlsComponent } from '@shared/components/view-controls/view-controls.component';
import { ViewControlsConfig, ViewControlsState } from '@shared/components/view-controls/view-controls.types';
import { getMachineDisplay, getResourceDisplay } from '@core/utils/machine-display.utils';

@Component({
  selector: 'app-spatial-view',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    AssetStatusChipComponent,
    ViewControlsComponent
  ],
  template: `
    <div class="h-full flex flex-col bg-[var(--mat-sys-surface-variant)]">
      <!-- Standardized View Controls -->
      <div class="bg-[var(--mat-sys-surface)] border-b border-[var(--theme-border)] px-6 py-2">
        <app-view-controls
          [config]="viewConfig()"
          [state]="viewState()"
          (stateChange)="onViewStateChange($event)">
        </app-view-controls>
      </div>

      <!-- Main Content -->
      <div class="flex-1 overflow-y-auto p-6 relative">
        @if (isLoading()) {
          <div class="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-black/50 z-20 backdrop-blur-sm">
            <mat-spinner diameter="40"></mat-spinner>
          </div>
        }

        @if (viewState().viewType === 'list') {
          <!-- List View -->
          <div class="flex flex-col gap-1">
            @for (asset of filteredAssets(); track asset.accession_id) {
              <div class="flex items-center gap-4 px-5 py-3 bg-[var(--mat-sys-surface)] border border-[var(--theme-border)] rounded-xl hover:bg-[var(--mat-sys-surface-container-low)] transition-all cursor-pointer group">
                <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" [ngClass]="getIconBgClass(asset)">
                  <mat-icon [class]="getIconTextClass(asset)" class="!text-[18px] !w-[18px] !h-[18px]">{{ getIcon(asset) }}</mat-icon>
                </div>
                <div class="min-w-0 flex-1">
                  <span class="font-semibold text-sm text-sys-text-primary truncate block">{{ asset.name }}</span>
                </div>
                <span class="text-xs text-sys-text-tertiary shrink-0 hidden sm:block">{{ getAssetSubtitle(asset) }}</span>
                <app-asset-status-chip [status]="asset.status" class="shrink-0" />
                <div class="flex items-center gap-1 text-xs text-sys-text-tertiary shrink-0 hidden md:flex">
                  <mat-icon class="!w-3 !h-3 !text-[12px] opacity-70">location_on</mat-icon>
                  <span class="truncate max-w-[120px]">{{ getLocationLabel(asset) }}</span>
                </div>
                <span class="text-[10px] text-sys-text-tertiary font-mono shrink-0 opacity-60">{{ getShortId(asset.accession_id) }}</span>
              </div>
            }
          </div>
        } @else {
        <!-- Card Grid View -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          @for (asset of filteredAssets(); track asset.accession_id) {
            <div class="asset-card group relative bg-[var(--mat-sys-surface)] border border-[var(--theme-border)] rounded-2xl p-5 hover:shadow-lg hover:-translate-y-1 transition-all duration-200 cursor-pointer">
              <!-- Type Indicator -->
              <div class="absolute top-4 right-4 text-[10px] uppercase font-bold tracking-wider px-2 py-1 rounded bg-[var(--mat-sys-surface-variant)] text-sys-text-tertiary">
                {{ isMachine(asset) ? 'Machine' : 'Resource' }}
              </div>

              <!-- Icon & Name -->
              <div class="flex items-start gap-4 mb-4">
                <div class="w-12 h-12 rounded-xl flex items-center justify-center shrink-0" 
                     [ngClass]="getIconBgClass(asset)">
                  <mat-icon [class]="getIconTextClass(asset)">{{ getIcon(asset) }}</mat-icon>
                </div>
                <div class="min-w-0 flex-1">
                  <h3 class="font-bold text-lg text-sys-text-primary truncate mb-1" [matTooltip]="asset.name">{{ asset.name }}</h3>
                  <p class="text-xs text-sys-text-secondary truncate">{{ getAssetSubtitle(asset) }}</p>
                </div>
              </div>

              <!-- Metadata Grid -->
              <div class="grid grid-cols-2 gap-y-3 gap-x-2 text-sm mb-4">
                <div class="flex flex-col">
                  <span class="text-[10px] uppercase text-sys-text-tertiary font-bold tracking-wider mb-0.5">Status</span>
                  <app-asset-status-chip [status]="asset.status" class="w-fit" />
                </div>
                
                <div class="flex flex-col">
                  <span class="text-[10px] uppercase text-sys-text-tertiary font-bold tracking-wider mb-0.5">Location</span>
                  <div class="flex items-center gap-1.5 text-sys-text-secondary truncate">
                    <mat-icon class="!w-3 !h-3 !text-[12px] opacity-70">location_on</mat-icon>
                    <span class="truncate" [matTooltip]="getLocationLabel(asset)">{{ getLocationLabel(asset) }}</span>
                  </div>
                </div>
              </div>

              <!-- Footer / Quick Actions -->
              <div class="pt-3 border-t border-[var(--theme-border)] flex items-center justify-between opacity-60 group-hover:opacity-100 transition-opacity">
                <span class="text-xs text-sys-text-tertiary font-mono">{{ getShortId(asset.accession_id) }}</span>
                <!-- Could add action buttons here later -->
              </div>
            </div>
          }
        </div>
        }

        @if (!isLoading() && filteredAssets().length === 0) {
          <div class="flex flex-col items-center justify-center h-[60vh] text-sys-text-tertiary">
            <div class="w-20 h-20 rounded-full bg-[var(--mat-sys-surface-variant)] flex items-center justify-center mb-4">
              <mat-icon class="!w-10 !h-10 !text-[40px] opacity-50">filter_list_off</mat-icon>
            </div>
            <h3 class="text-lg font-medium text-sys-text-secondary mb-1">No assets found</h3>
            <p>Try adjusting your filters or search terms</p>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: 100%;
    }

    .asset-card {
      min-height: 200px;
      display: flex;
      flex-direction: column;
      background: linear-gradient(135deg, var(--mat-sys-surface) 0%, var(--mat-sys-surface-container-low) 100%);
      position: relative;
      overflow: hidden;
    }

    .asset-card::before {
      content: '';
      position: absolute;
      top: -20%;
      right: -10%;
      width: 100px;
      height: 100px;
      background: radial-gradient(circle at center, var(--mat-sys-primary) 0%, transparent 70%);
      opacity: 0.03;
      pointer-events: none;
    }

    .asset-card:hover {
      border-color: var(--mat-sys-primary);
      box-shadow: 0 8px 24px -12px var(--mat-sys-primary);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SpatialViewComponent implements OnInit {
  private assetService = inject(AssetService);

  // Data Signals
  machines = signal<Machine[]>([]);
  resources = signal<Resource[]>([]);
  workcells = signal<Workcell[]>([]);
  isLoading = signal(true);

  // Standardized View Controls Config
  viewConfig = computed<ViewControlsConfig>(() => ({
    viewTypes: ['card', 'list'],
    groupByOptions: [
      { label: 'None', value: null },
      { label: 'Status', value: 'status' },
      { label: 'Category', value: 'category' },
      { label: 'Location', value: 'location' },
    ],
    filters: [
      {
        key: 'status',
        label: 'Status',
        type: 'multiselect',
        options: [
          { label: 'Available', value: 'available', icon: 'check_circle' },
          { label: 'In Use', value: 'in_use', icon: 'play_circle' },
          { label: 'Error', value: 'error', icon: 'error' },
          { label: 'Maintenance', value: 'maintenance', icon: 'build' }
        ]
      },
      {
        key: 'category',
        label: 'Category',
        type: 'chips',
        options: this.categories().map(cat => ({ label: cat, value: cat }))
      },
      {
        key: 'machine_id',
        label: 'Location',
        type: 'select',
        options: [
          { label: 'Any location', value: null },
          ...this.machines().map(m => ({ label: m.name, value: m.accession_id }))
        ]
      },
      {
        key: 'workcell_id',
        label: 'Workcell',
        type: 'select',
        options: [
          { label: 'Any workcell', value: null },
          ...this.workcells().map(w => ({ label: w.name, value: w.accession_id }))
        ]
      },
      {
        key: 'maintenance_due',
        label: 'Maintenance',
        type: 'select',
        options: [
          { label: 'All', value: false },
          { label: 'Due Only', value: true }
        ]
      }
    ],
    sortOptions: [
      { label: 'Name', value: 'name' },
      { label: 'Date Added', value: 'created_at' },
      { label: 'Status', value: 'status' },
      { label: 'Category', value: 'category' }
    ],
    storageKey: 'spatial-view',
    defaults: {
      sortBy: 'created_at',
      sortOrder: 'desc'
    }
  }));

  viewState = signal<ViewControlsState>({
    viewType: 'card',
    groupBy: null,
    filters: {
      status: [],
      category: [],
      machine_id: [],
      workcell_id: [],
      maintenance_due: []
    },
    sortBy: 'created_at',
    sortOrder: 'desc',
    search: ''
  });

  // Categories derived for filters
  categories = computed(() => {
    // Collect all unique categories from machines and resources
    const cats = new Set<string>();
    this.machines().forEach(m => {
      if (m.machine_category) cats.add(m.machine_category);
    });
    // Resources might use 'plr_category' from definition, or we can just ignore for now
    // as Resource logic is a bit more complex. 
    // Let's rely on machine categories primarily for now or strictly map resources.
    return Array.from(cats).sort();
  });

  allAssets = computed(() => {
    return [...this.machines(), ...this.resources()];
  });

  filteredAssets = computed(() => {
    let assets = this.allAssets();
    const state = this.viewState();

    // 1. Search
    if (state.search) {
      const q = state.search.toLowerCase();
      assets = assets.filter(a =>
        a.name.toLowerCase().includes(q) ||
        (a.fqn || '').toLowerCase().includes(q) ||
        (a.location_label || '').toLowerCase().includes(q)
      );
    }

    // 2. Status
    const statusFilters = state.filters['status'] || [];
    if (statusFilters.length > 0) {
      assets = assets.filter(a => statusFilters.includes(a.status));
    }

    // 3. Category
    const categoryFilters = state.filters['category'] || [];
    if (categoryFilters.length > 0) {
      assets = assets.filter(a => {
        if (this.isMachine(a)) {
          return a.machine_category && categoryFilters.includes(a.machine_category);
        }
        return false;
      });
    }

    // 4. Machine ID (Location)
    const machineIdFilter = state.filters['machine_id']?.[0]; // Select type returns array
    if (machineIdFilter) {
      assets = assets.filter(a => {
        if (a.accession_id === machineIdFilter) return true;
        if (!this.isMachine(a)) {
          return (a as Resource).machine_location_accession_id === machineIdFilter;
        }
        return false;
      });
    }

    // 5. Workcell ID
    const workcellIdFilter = state.filters['workcell_id']?.[0];
    if (workcellIdFilter) {
      assets = assets.filter(a => {
        return (a as Machine | Resource).workcell_accession_id === workcellIdFilter;
      });
    }

    // 6. Maintenance Due
    const maintenanceDueFilter = state.filters['maintenance_due']?.[0];
    if (maintenanceDueFilter === true) {
      // In a real app, this would check a 'maintenance_due' property or date
      // For now, mirroring existing logic (which didn't actually have property check implemented here)
      // assets = assets.filter(a => a.maintenance_due); 
    }

    // 7. Sorting
    assets.sort((a, b) => {
      let valA: string | number = '';
      let valB: string | number = '';

      const getVal = (item: Machine | Resource, field: string): string | number => {
        if (field === 'name') return item.name?.toLowerCase() || '';
        if (field === 'created_at') return new Date(item.created_at || 0).getTime();
        if (field === 'status') return item.status;
        if (field === 'category') return (this.isMachine(item) ? (item.machine_category || '') : '').toLowerCase();
        return '';
      };

      valA = getVal(a, state.sortBy);
      valB = getVal(b, state.sortBy);

      if (valA < valB) return state.sortOrder === 'asc' ? -1 : 1;
      if (valA > valB) return state.sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    return assets;
  });

  ngOnInit() {
    this.refreshData();
  }

  refreshData() {
    this.isLoading.set(true);
    forkJoin({
      machines: this.assetService.getMachines(),
      resources: this.assetService.getResources()
    }).subscribe({
      next: (res) => {
        this.machines.set(res.machines);
        this.resources.set(res.resources);
        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load assets', err);
        this.isLoading.set(false);
      }
    });
  }

  onViewStateChange(state: ViewControlsState) {
    this.viewState.set(state);
  }

  clearFilters() {
    this.viewState.update(s => ({
      ...s,
      search: '',
      groupBy: null,
      filters: {
        status: [],
        category: [],
        machine_id: [],
        workcell_id: [],
        maintenance_due: []
      }
    }));
  }

  // Helpers
  isMachine(asset: Machine | Resource): asset is Machine {
    return 'machine_category' in asset;
  }

  getIcon(asset: Machine | Resource): string {
    if (this.isMachine(asset)) return getMachineDisplay(asset.machine_category).icon;
    return getResourceDisplay(undefined).icon; // Resource has no category field; uses default
  }

  getIconBgClass(asset: Machine | Resource): string {
    if (this.isMachine(asset)) return getMachineDisplay(asset.machine_category).bgClass;
    return getResourceDisplay(undefined).bgClass;
  }

  getIconTextClass(asset: Machine | Resource): string {
    if (this.isMachine(asset)) return getMachineDisplay(asset.machine_category).textClass;
    return getResourceDisplay(undefined).textClass;
  }

  getAssetSubtitle(asset: Machine | Resource): string {
    if (this.isMachine(asset)) return asset.model || asset.manufacturer || 'Unknown Model';
    return (asset as Resource).resource_definition_accession_id ? 'Resource' : 'Custom Resource';
  }

  getLocationLabel(asset: any): string {
    return asset.location_label || 'Unassigned';
  }

  getShortId(id: string): string {
    return id.substring(0, 8);
  }
}