import { Component, ChangeDetectionStrategy, inject, signal, computed } from '@angular/core';

import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatTabsModule } from '@angular/material/tabs';
import { MatPaginatorModule } from '@angular/material/paginator';
import { AssetService } from '../../services/asset.service';
import { ResourceDefinition } from '../../models/asset.models';
import { getPropertyTooltip } from '@shared/constants/resource-tooltips';
import { MachineDefinitionAccordionComponent } from '../machine-definition-accordion/machine-definition-accordion.component';
import { ViewControlsComponent } from '@shared/components/view-controls/view-controls.component';
import { ViewControlsConfig, ViewControlsState } from '@shared/components/view-controls/view-controls.types';
import { ModeService } from '@core/services/mode.service';

@Component({
  selector: 'app-definitions-list',
  standalone: true,
  imports: [
    MatTableModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatTabsModule,
    MachineDefinitionAccordionComponent,
    ViewControlsComponent,
    MatPaginatorModule
  ],
  template: `
    <div class="definitions-list-container">
      @if (modeService.isBrowserMode()) {
        <div class="browser-mode-banner">
          <mat-icon>info</mat-icon>
          <span>
            Registry is read-only in browser mode.
            Definitions are loaded from bundled PyLabRobot data.
          </span>
        </div>
      }
      <mat-tab-group animationDuration="0ms">
        <mat-tab>
          <ng-template mat-tab-label>
            <div class="flex items-center gap-2">
              <mat-icon class="!w-5 !h-5 !text-[18px]">precision_manufacturing</mat-icon>
              <span>Machine Types</span>
            </div>
          </ng-template>
          <div class="tab-content">
            <div class="bg-[var(--mat-sys-surface)] border-b border-[var(--theme-border)] px-4 py-2 mb-4 rounded-xl shadow-sm mx-4 mt-4">
              <app-view-controls
                [config]="machineViewConfig()"
                [state]="machineViewState()"
                (stateChange)="onMachineViewStateChange($event)">
              </app-view-controls>
            </div>
            <app-machine-definition-accordion [viewState]="machineViewState()"></app-machine-definition-accordion>
          </div>
        </mat-tab>

        <mat-tab>
          <ng-template mat-tab-label>
            <div class="flex items-center gap-2">
              <mat-icon class="!w-5 !h-5 !text-[18px]">science</mat-icon>
              <span>Resource Types</span>
            </div>
          </ng-template>
          <div class="resource-tab-content">
            <div class="bg-[var(--mat-sys-surface)] border-b border-[var(--theme-border)] px-4 py-2 mb-4 rounded-xl shadow-sm mt-4">
              <app-view-controls
                [config]="resourceViewConfig()"
                [state]="resourceViewState()"
                (stateChange)="onResourceViewStateChange($event)">
              </app-view-controls>
            </div>

            <table mat-table [dataSource]="filteredResourceDefinitions()" class="mat-elevation-z2 mt-4">
              <ng-container matColumnDef="name">
                <th mat-header-cell *matHeaderCellDef> Name </th>
                <td mat-cell *matCellDef="let def"> {{ def.name }} </td>
              </ng-container>

              <ng-container matColumnDef="type">
                <th mat-header-cell *matHeaderCellDef> Type </th>
                <td mat-cell *matCellDef="let def"> {{ def.resource_type || 'N/A' }} </td>
              </ng-container>

              <ng-container matColumnDef="manufacturer">
                <th mat-header-cell *matHeaderCellDef> Manufacturer </th>
                <td mat-cell *matCellDef="let def"> {{ def.manufacturer || 'N/A' }} </td>
              </ng-container>

              <ng-container matColumnDef="model">
                <th mat-header-cell *matHeaderCellDef> Model </th>
                <td mat-cell *matCellDef="let def"> {{ def.model || 'N/A' }} </td>
              </ng-container>

              <ng-container matColumnDef="consumable">
                <th mat-header-cell *matHeaderCellDef class="!text-center"> Consumable </th>
                <td mat-cell *matCellDef="let def" class="!text-center">
                  <mat-icon
                    [color]="def.is_consumable ? 'primary' : 'warn'"
                    [matTooltip]="def.is_consumable ? getPropertyTooltip('consumable') : 'Non-consumable: can be reused across protocols'"
                  >
                    {{ def.is_consumable ? 'check_circle' : 'cancel' }}
                  </mat-icon>
                </td>
              </ng-container>

              <ng-container matColumnDef="actions">
                <th mat-header-cell *matHeaderCellDef class="!text-center"> Actions </th>
                <td mat-cell *matCellDef="let def" class="!text-center">
                  <button mat-icon-button color="primary" matTooltip="View Details">
                    <mat-icon>info</mat-icon>
                  </button>
                </td>
              </ng-container>

              <tr mat-header-row *matHeaderRowDef="displayedResourceColumns"></tr>
              <tr mat-row *matRowDef="let row; columns: displayedResourceColumns;"></tr>

              <tr class="mat-row" *matNoDataRow>
                <td class="mat-cell" colspan="6">
                  <div class="empty-state">
                    <mat-icon>search_off</mat-icon>
                    <span>No resource definitions matching the filter "{{ resourceViewState().search }}"</span>
                  </div>
                </td>
              </tr>
            </table>

            <mat-paginator
              [length]="totalResourceCount()"
              [pageSize]="pageSize()"
              [pageIndex]="pageIndex()"
              [pageSizeOptions]="[5, 10, 25, 100]"
              (page)="onPageChange($event)"
              aria-label="Select page of resource definitions">
            </mat-paginator>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .definitions-list-container {
      /* Remove padding to allow tabs to be full width */
      height: 100%;
      display: flex;
      flex-direction: column;
    }

    .browser-mode-banner {
      display: flex;
      align-items: center;
      gap: 12px;
      background: var(--mat-sys-secondary-container);
      color: var(--mat-sys-on-secondary-container);
      padding: 12px 16px;
      margin: 16px 16px 0 16px;
      border-radius: 8px;
    }

    .filter-field {
      width: 100%;
      margin-bottom: 16px;
    }

    .mat-elevation-z2 {
      width: 100%;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 48px 0;
      color: var(--mat-sys-on-surface-variant);
      gap: 12px;
    }

    .empty-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      opacity: 0.5;
    }

    mat-tab-group {
      /* Remove auto margin */
      margin-top: 0;
    }

    .resource-tab-content {
      padding: 0 16px 16px 16px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DefinitionsListComponent {
  private assetService = inject(AssetService);
  public modeService = inject(ModeService);

  resourceDefinitions = signal<ResourceDefinition[]>([]);
  machineViewState = signal<ViewControlsState>({
    viewType: 'accordion',
    groupBy: 'category',
    filters: {},
    sortBy: 'name',
    sortOrder: 'asc',
    search: ''
  });

  resourceViewState = signal<ViewControlsState>({
    viewType: 'table',
    groupBy: null,
    filters: {},
    sortBy: 'name',
    sortOrder: 'asc',
    search: ''
  });

  machineViewConfig = computed<ViewControlsConfig>(() => ({
    viewTypes: ['accordion'],
    groupByOptions: [
      { label: 'Category', value: 'category' },
      { label: 'Manufacturer', value: 'manufacturer' }
    ],
    sortOptions: [
      { label: 'Name', value: 'name' },
      { label: 'Manufacturer', value: 'manufacturer' }
    ],
    storageKey: 'machine-definitions',
    defaults: {
      viewType: 'accordion',
      sortBy: 'name',
      sortOrder: 'asc'
    }
  }));

  resourceViewConfig = computed<ViewControlsConfig>(() => ({
    viewTypes: ['table'],
    filters: [
      {
        key: 'manufacturer',
        label: 'Manufacturer',
        type: 'multiselect',
        options: this.manufacturers().map(m => ({ label: m, value: m }))
      },
      {
        key: 'plr_category',
        label: 'Category',
        type: 'multiselect',
        options: this.categories().map(c => ({ label: c, value: c }))
      },
      {
        key: 'consumable',
        label: 'Consumable Only',
        type: 'toggle',
        defaultValue: false
      }
    ],
    sortOptions: [
      { label: 'Name', value: 'name' },
      { label: 'Type', value: 'resource_type' },
      { label: 'Manufacturer', value: 'manufacturer' }
    ],
    storageKey: 'resource-definitions',
    defaults: {
      viewType: 'table',
      sortBy: 'name',
      sortOrder: 'asc'
    }
  }));

  manufacturers = computed(() => {
    const mfgs = new Set<string>();
    this.resourceDefinitions().forEach(d => {
      if (d.manufacturer) mfgs.add(d.manufacturer);
    });
    return Array.from(mfgs).sort();
  });

  categories = computed(() => {
    const cats = new Set<string>();
    this.resourceDefinitions().forEach(d => {
      if (d.plr_category) cats.add(d.plr_category);
    });
    return Array.from(cats).sort();
  });

  pageSize = signal(10);
  pageIndex = signal(0);

  totalResourceCount = computed(() => this.allFilteredResourceDefinitions().length);

  allFilteredResourceDefinitions = computed(() => {
    const state = this.resourceViewState();
    let filtered = this.resourceDefinitions();

    // 1. Search
    if (state.search) {
      const search = state.search.toLowerCase();
      filtered = filtered.filter(def =>
        def.name.toLowerCase().includes(search) ||
        def.resource_type?.toLowerCase().includes(search) ||
        def.manufacturer?.toLowerCase().includes(search) ||
        def.model?.toLowerCase().includes(search)
      );
    }

    // 2. Manufacturer Filter
    const mfgFilters = state.filters['manufacturer'] || [];
    if (mfgFilters.length > 0) {
      filtered = filtered.filter(def => def.manufacturer && mfgFilters.includes(def.manufacturer));
    }

    // 2b. Category Filter
    const catFilters = state.filters['plr_category'] || [];
    if (catFilters.length > 0) {
      filtered = filtered.filter(def => def.plr_category && catFilters.includes(def.plr_category));
    }

    // 3. Consumable Toggle
    if (state.filters['consumable']?.includes(true)) {
      filtered = filtered.filter(def => def.is_consumable);
    }

    // 4. Sorting
    filtered = [...filtered].sort((a, b) => {
      const valA = (a as unknown as Record<string, unknown>)[state.sortBy] || '';
      const valB = (b as unknown as Record<string, unknown>)[state.sortBy] || '';
      const comparison = valA.toString().localeCompare(valB.toString());
      return state.sortOrder === 'asc' ? comparison : -comparison;
    });

    return filtered;
  });

  onMachineViewStateChange(state: ViewControlsState) {
    this.machineViewState.set(state);
  }

  onResourceViewStateChange(state: ViewControlsState) {
    this.resourceViewState.set(state);
    this.pageIndex.set(0); // Reset to first page on filter change
  }

  onPageChange(event: any) {
    this.pageSize.set(event.pageSize);
    this.pageIndex.set(event.pageIndex);
  }

  filteredResourceDefinitions = computed(() => {
    const all = this.allFilteredResourceDefinitions();
    const start = this.pageIndex() * this.pageSize();
    return all.slice(start, start + this.pageSize());
  });

  displayedResourceColumns: string[] = ['name', 'type', 'manufacturer', 'model', 'consumable', 'actions'];

  constructor() {
    this.loadResourceDefinitions();
  }

  private loadResourceDefinitions(): void {
    this.assetService.getResourceDefinitions().subscribe(
      (data) => {
        this.resourceDefinitions.set(data);
      },
      (error) => {
        console.error('Error fetching resource definitions:', error);
      }
    );
  }

  getPropertyTooltip(property: string): string {
    return getPropertyTooltip(property);
  }
}
