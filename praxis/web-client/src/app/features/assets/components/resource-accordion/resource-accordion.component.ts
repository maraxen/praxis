import { Component, ChangeDetectionStrategy, inject, signal, computed, OnInit } from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';

import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatBadgeModule } from '@angular/material/badge';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatChipsModule } from '@angular/material/chips';
import { ReactiveFormsModule } from '@angular/forms';
import { AssetService } from '../../services/asset.service';
import { Resource, ResourceStatus, ResourceDefinition, Machine } from '../../models/asset.models';
import { ResourceInstancesDialogComponent } from './resource-instances-dialog.component';
import { AssetStatusChipComponent, AssetStatusType } from '../asset-status-chip/asset-status-chip.component';
import { getCategoryTooltip, getPropertyTooltip } from '@shared/constants/resource-tooltips';
import { getResourceCategoryIcon } from '@shared/constants/asset-icons';
import { getUiGroup, UI_GROUP_ORDER, shouldHideCategory, ResourceUiGroup } from '../../utils/resource-category-groups';
import { ResourceChipsComponent } from '../resource-chips/resource-chips.component';
import { getDisplayLabel } from '../../utils/resource-name-parser';
import { AppStore } from '@core/store/app.store';
import { ViewControlsComponent } from '@shared/components/view-controls/view-controls.component';
import { ViewControlsConfig, ViewControlsState } from '@shared/components/view-controls/view-controls.types';

export interface ResourceGroup {
  category: string;
  definitions: ResourceDefinitionGroup[];
  totalCount: number;
  consumableStatus: 'all' | 'none' | 'mixed'; // 'mixed' = dashed outline
}

export interface ResourceDefinitionGroup {
  definition: ResourceDefinition;
  instances: Resource[];
  count: number | null; // null = infinite (only for consumables)
  isInfinite: boolean;
  isConsumable: boolean;
  isReusable: boolean;
  activeCount: number;
  discardedCount: number;
  primaryStatus: AssetStatusType | null; // Most relevant status for chip display
}

@Component({
  selector: 'app-resource-accordion',
  standalone: true,
  imports: [
    MatExpansionModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatBadgeModule,
    MatSlideToggleModule,
    MatDialogModule,
    MatChipsModule,
    ReactiveFormsModule,
    AssetStatusChipComponent,
    ResourceChipsComponent,
    ViewControlsComponent,
    NgTemplateOutlet
  ],
  template: `
    <div class="resource-accordion-container">
      <!-- Standardized View Controls -->
      <div class="bg-[var(--mat-sys-surface)] border-b border-[var(--theme-border)] px-4 py-2 mb-4 rounded-xl shadow-sm">
        <app-view-controls
          [config]="viewConfig()"
          [state]="viewState()"
          (stateChange)="onViewStateChange($event)">
        </app-view-controls>
      </div>

      @if (viewState().viewType === 'accordion') {
        <ng-template #definitionItem let-defGroup="defGroup">
          <div class="definition-item" (click)="openInstancesDialog(defGroup)" [attr.data-testid]="'resource-item-' + defGroup.definition.accession_id">
            <div class="def-info">
              <span class="def-name">{{ getDisplayLabel(defGroup.definition) }}</span>
              @if (viewState().search && getMatchingInstanceName(defGroup)) {
                <span class="text-xs text-[var(--mat-sys-on-surface-variant)] italic">
                  Matches: {{ getMatchingInstanceName(defGroup) }}
                </span>
              }
              <!-- Prioritized chip ordering: Status (if itemized) → Count → Type flags → Vendor -->
              <div class="def-chips">
                @if (defGroup.isConsumable && defGroup.primaryStatus) {
                  <app-asset-status-chip [status]="defGroup.primaryStatus" [showLabel]="true" />
                }
                
                <app-resource-chips 
                  [definition]="defGroup.definition" 
                  [showVendor]="true"
                  [showDisplayName]="false">
                </app-resource-chips>

                @if (defGroup.isConsumable) {
                  <mat-chip class="info-chip consumable" [matTooltip]="getPropertyTooltip('consumable')">Consumable</mat-chip>
                }
              </div>
            </div>
            <div class="def-counts">
              @if (defGroup.isConsumable && defGroup.isInfinite) {
                <span class="count infinite" [matTooltip]="getPropertyTooltip('infinite')">∞</span>
              } @else {
                <span
                  class="count"
                  [class.low]="defGroup.activeCount < 3"
                  [matTooltip]="defGroup.activeCount < 3 ? getPropertyTooltip('low-stock') : 'Available quantity'"
                >
                  {{ defGroup.isConsumable ? defGroup.activeCount : 1 }}
                </span>
              }
              @if (viewState().filters['show_discarded']?.includes(true) && defGroup.discardedCount > 0) {
                <span class="count discarded" [matTooltip]="getPropertyTooltip('depleted')">
                  ({{ defGroup.discardedCount }} discarded)
                </span>
              }
              @if (defGroup.isReusable) {
                <mat-icon class="reusable-icon" [matTooltip]="getPropertyTooltip('reusable')">refresh</mat-icon>
              }
            </div>
            <mat-icon class="chevron">chevron_right</mat-icon>
          </div>
        </ng-template>

        @if (viewState().groupBy) {
          <mat-accordion multi="true">
          @for (group of filteredGroups(); track group.category) {
            <mat-expansion-panel class="category-panel" [expanded]="!!viewState().search">
              <mat-expansion-panel-header>
                <mat-panel-title>
                  <mat-icon class="category-icon" [matTooltip]="getCategoryTooltip(group.category)">{{ getCategoryIcon(group.category) }}</mat-icon>
                  <span [matTooltip]="getCategoryTooltip(group.category)">{{ group.category }}</span>
                </mat-panel-title>
                <mat-panel-description>
                  <span class="count-badge">{{ group.totalCount }} types</span>
                  @if (group.consumableStatus !== 'none') {
                    <mat-chip
                      class="consumable-chip"
                      [class.mixed]="group.consumableStatus === 'mixed'"
                      [matTooltip]="group.consumableStatus === 'mixed'
                        ? 'Some items in this category are consumable (used up during protocols)'
                        : getPropertyTooltip('consumable')"
                    >
                      Consumable
                    </mat-chip>
                  }
                </mat-panel-description>
              </mat-expansion-panel-header>

              <div class="definition-list">
                @for (defGroup of group.definitions; track defGroup.definition.accession_id) {
                  <ng-container *ngTemplateOutlet="definitionItem; context: {defGroup: defGroup}"></ng-container>
                }
              </div>
            </mat-expansion-panel>
          }
          </mat-accordion>
        } @else {
          <!-- Flat List View (groupBy: null) -->
          <div class="definition-list flat-list">
            @for (defGroup of filteredFlatDefinitions(); track defGroup.definition.accession_id) {
              <ng-container *ngTemplateOutlet="definitionItem; context: {defGroup: defGroup}"></ng-container>
            }
          </div>
        }
      }

      @if (viewState().viewType === 'list') {
        <div class="flex flex-col gap-2">
          @for (group of filteredGroups(); track group.category) {
            @for (defGroup of group.definitions; track defGroup.definition.accession_id) {
              <div class="flex items-center gap-4 p-3 bg-[var(--mat-sys-surface)] border border-[var(--theme-border)] rounded-lg hover:border-[var(--mat-sys-primary)] transition-colors cursor-pointer"
                   (click)="openInstancesDialog(defGroup)">
                <div class="w-10 h-10 rounded-full bg-[var(--mat-sys-primary-container)] text-[var(--mat-sys-on-primary-container)] flex items-center justify-center">
                  <mat-icon>{{ getCategoryIcon(group.category) }}</mat-icon>
                </div>
                <div class="flex-1 flex flex-col">
                  <span class="font-medium">{{ getDisplayLabel(defGroup.definition) }}</span>
                  <span class="text-xs text-[var(--mat-sys-on-surface-variant)]">{{ group.category }}</span>
                </div>
                <div class="flex items-center gap-2">
                  @if (defGroup.isConsumable && defGroup.primaryStatus) {
                    <app-asset-status-chip [status]="defGroup.primaryStatus" size="small" />
                  }
                  <div class="text-sm font-semibold px-2 py-1 bg-[var(--mat-sys-surface-container-highest)] rounded text-[var(--mat-sys-on-surface)]">
                    {{ defGroup.isConsumable && defGroup.isInfinite ? '∞' : (defGroup.isConsumable ? defGroup.activeCount : 1) }}
                  </div>
                </div>
              </div>
            }
          }
        </div>
      }

      @if (filteredGroups().length === 0) {
        <div class="empty-state">
          <mat-icon>inventory_2</mat-icon>
          <p>No resources matching current filters</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .resource-accordion-container {
      padding: 0 16px 16px 16px;
    }

    .accordion-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .accordion-header h3 {
      margin: 0;
      font-size: 1.1rem;
      font-weight: 500;
    }

    .discard-toggle {
      font-size: 0.85rem;
    }

    .filter-field {
      width: 100%;
      margin-bottom: 16px;
    }

    .category-panel {
      margin-bottom: 8px;
    }

    .category-icon {
      margin-right: 8px;
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    .count-badge {
      background: var(--sys-primary-container);
      color: var(--sys-on-primary-container);
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      margin-right: 8px;
    }

    .consumable-chip {
      font-size: 0.65rem;
      min-height: 20px;
      padding: 0 6px;
    }

    /* Dashed outline for mixed consumable categories */
    .consumable-chip.mixed {
      border: 2px dashed var(--sys-outline);
      background: transparent;
    }

    .definition-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .definition-item {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      // Premium surface gradient
      background: linear-gradient(135deg, var(--mat-sys-surface) 0%, var(--mat-sys-surface-container-low) 100%);
      border: 1px solid var(--theme-border);
      border-radius: 12px; // Match standard
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .definition-item:hover {
      background: linear-gradient(135deg, var(--mat-sys-surface-container-low) 0%, var(--mat-sys-surface-container) 100%);
      border-color: var(--sys-primary);
      transform: translateX(4px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    .def-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0; // CRITICAL for truncation in flex
    }

    .def-name {
      font-weight: 500;
      font-size: 0.9rem;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--theme-text-primary);
    }

    .def-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      margin-top: 4px;
    }

    .info-chip {
      --mdc-chip-container-height: 20px;
      font-size: 0.65rem;
      font-weight: 500;
    }

    .info-chip.consumable {
      --mdc-chip-elevated-container-color: var(--sys-tertiary-container);
      --mdc-chip-label-text-color: var(--sys-on-tertiary-container);
    }

    .info-chip.vendor {
      --mdc-chip-elevated-container-color: var(--sys-surface-container-high);
      --mdc-chip-label-text-color: var(--sys-on-surface-variant);
    }

    .def-meta {
      font-size: 0.75rem;
      color: var(--sys-on-surface-variant);
    }

    .def-counts {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-right: 8px;
    }

    .count {
      font-weight: 600;
      font-size: 1rem;
    }

    .count.infinite {
      font-size: 1.5rem;
      color: var(--sys-primary);
    }

    .count.low {
      color: var(--sys-error);
    }

    .count.discarded {
      font-size: 0.75rem;
      color: var(--sys-on-surface-variant);
    }

    .reusable-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
      color: var(--sys-tertiary);
    }

    .chevron {
      color: var(--sys-on-surface-variant);
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 48px;
      color: var(--sys-on-surface-variant);
    }

    .empty-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      margin-bottom: 16px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResourceAccordionComponent implements OnInit {
  private assetService = inject(AssetService);
  private dialog = inject(MatDialog);
  private store = inject(AppStore);

  resources = signal<Resource[]>([]);
  definitions = signal<ResourceDefinition[]>([]);
  machines = signal<Machine[]>([]);

  viewConfig = computed<ViewControlsConfig>(() => ({
    viewTypes: ['accordion', 'list'],
    groupByOptions: [
      { label: 'Category', value: 'category' },
    ],
    filters: [
      {
        key: 'status',
        label: 'Status',
        type: 'multiselect',
        options: [
          { label: 'Available', value: ResourceStatus.AVAILABLE, icon: 'check_circle' },
          { label: 'In Use', value: ResourceStatus.IN_USE, icon: 'play_arrow' },
          { label: 'Reserved', value: ResourceStatus.RESERVED, icon: 'lock' },
          { label: 'Depleted', value: ResourceStatus.DEPLETED, icon: 'remove_circle' },
          { label: 'Expired', value: ResourceStatus.EXPIRED, icon: 'event_busy' }
        ]
      },
      {
        key: 'category',
        label: 'Category',
        type: 'multiselect',
        options: this.categories().map(c => ({ label: c, value: c }))
      },
      {
        key: 'brands',
        label: 'Brand',
        type: 'multiselect',
        options: this.brands().map(b => ({ label: b, value: b }))
      },
      {
        key: 'machine_id',
        label: 'Location',
        type: 'multiselect',
        options: this.machines().map(m => ({ label: m.name, value: m.accession_id }))
      },
      {
        key: 'show_discarded',
        label: 'Show Discarded',
        type: 'toggle',
        defaultValue: false
      }
    ],
    sortOptions: [
      { label: 'Name', value: 'name' },
      { label: 'Count', value: 'count' },
      { label: 'Category', value: 'category' },
      { label: 'Created', value: 'created_at' }
    ],
    storageKey: 'resource-accordion',
    defaults: {
      viewType: 'accordion',
      sortBy: 'name',
      sortOrder: 'asc'
    }
  }));

  viewState = signal<ViewControlsState>({
    viewType: 'accordion',
    groupBy: 'category',
    filters: {},
    sortBy: 'name',
    sortOrder: 'asc',
    search: ''
  });

  onViewStateChange(state: ViewControlsState) {
    this.viewState.set(state);
  }

  brands = computed(() => {
    const brands = new Set<string>();
    this.resources().forEach(r => {
      const vendor = (r as any).definition?.vendor || (r as any).vendor || (r as any).manufacturer;
      if (vendor) brands.add(vendor);
    });
    return Array.from(brands).sort();
  });

  constructor() {
    // Removed old filterControl logic
  }



  // Computed Categories for Filter
  categories = computed(() => {
    return this.resourceGroups().map(g => g.category).sort();
  });

  resourceGroups = computed(() => {
    const defs = this.definitions();
    const res = this.resources();

    // Group definitions by category
    const categoryMap = new Map<ResourceUiGroup, ResourceDefinitionGroup[]>();

    defs.forEach(def => {
      if (shouldHideCategory(def.plr_category)) return;
      const category = getUiGroup(def.plr_category);
      const isConsumable = (def as any).is_consumable ?? false;
      const instances = res.filter(r => r.resource_definition_accession_id === def.accession_id);
      const activeInstances = instances.filter(r =>
        r.status !== ResourceStatus.DEPLETED && r.status !== ResourceStatus.EXPIRED
      );
      const discardedInstances = instances.filter(r =>
        r.status === ResourceStatus.DEPLETED || r.status === ResourceStatus.EXPIRED
      );

      // Compute primary status for chip display (priority: reserved > in_use > error statuses > available)
      const statusPriority: Record<string, number> = {
        'reserved': 1,
        'in_use': 2,
        'depleted': 3,
        'expired': 4,
        'available': 5,
        'unknown': 6
      };
      let primaryStatus: AssetStatusType | null = null;
      if (isConsumable && activeInstances.length > 0) {
        // Find the highest priority status among active instances
        const sortedByPriority = activeInstances.sort((a, b) =>
          (statusPriority[a.status] || 99) - (statusPriority[b.status] || 99)
        );
        primaryStatus = sortedByPriority[0]?.status as AssetStatusType || null;
      }

      const defGroup: ResourceDefinitionGroup = {
        definition: def,
        instances: instances,
        count: (def as any).default_count ?? null,
        // Only consumables can be infinite; non-consumables always show "1"
        // Infinite if enabled in settings AND item is consumable
        isInfinite: isConsumable && this.store.infiniteConsumables(),
        isConsumable: isConsumable,
        isReusable: (def as any).is_reusable ?? false,
        activeCount: activeInstances.length,
        discardedCount: discardedInstances.length,
        primaryStatus: primaryStatus
      };

      if (!categoryMap.has(category)) {
        categoryMap.set(category, []);
      }
      categoryMap.get(category)!.push(defGroup);
    });

    // Convert to array
    const groups: ResourceGroup[] = [];
    categoryMap.forEach((defGroups, category) => {
      const consumableCount = defGroups.filter(d => d.isConsumable).length;
      let consumableStatus: 'all' | 'none' | 'mixed';
      if (consumableCount === 0) {
        consumableStatus = 'none';
      } else if (consumableCount === defGroups.length) {
        consumableStatus = 'all';
      } else {
        consumableStatus = 'mixed';
      }

      groups.push({
        category,
        definitions: defGroups,
        totalCount: defGroups.length,
        consumableStatus
      });
    });

    // Sort by UI_GROUP_ORDER
    return groups.sort((a, b) => {
      const idxA = UI_GROUP_ORDER.indexOf(a.category as ResourceUiGroup);
      const idxB = UI_GROUP_ORDER.indexOf(b.category as ResourceUiGroup);
      return idxA - idxB;
    });
  });

  // Flat list of definitions when groupBy is null
  filteredFlatDefinitions = computed(() => {
    // Get the already-filtered groups
    const groups = this.filteredGroups();

    // Flatten: extract definitions from each group and combine
    return groups
      .map(group => group.definitions)  // Extract definitions arrays
      .flat();                          // Flatten into single array
  });

  // Filtered groups based on all filters
  filteredGroups = computed(() => {
    const state = this.viewState();
    let groups = this.resourceGroups();

    // 1. Filter by Category
    const categoryFilters = state.filters['category'] || [];
    if (categoryFilters.length > 0) {
      groups = groups.filter(g => categoryFilters.includes(g.category));
    }

    const showDiscarded = state.filters['show_discarded']?.includes(true);
    const statusFilters = state.filters['status'] || [];
    const brandsFilters = state.filters['brands'] || [];
    const machineIdFilters = state.filters['machine_id'] || [];

    return groups.map(group => {
      // Filter definitions within the group and update counts based on filters
      const filteredDefs = group.definitions.map(defGroup => {
        // Apply Filters to Instances first
        let matchingInstances = defGroup.instances;

        // Default: Hide discarded unless requested
        if (!showDiscarded) {
          matchingInstances = matchingInstances.filter(inst =>
            inst.status !== ResourceStatus.DEPLETED && inst.status !== ResourceStatus.EXPIRED
          );
        }

        // Status Filter
        if (statusFilters.length > 0) {
          matchingInstances = matchingInstances.filter(inst =>
            statusFilters.includes(inst.status)
          );
        }

        // Location Filter (Machine)
        if (machineIdFilters.length > 0) {
          matchingInstances = matchingInstances.filter(inst =>
            inst.location && machineIdFilters.some((id: string) => inst.location?.startsWith(id))
          );
        }

        // Brand Filter
        if (brandsFilters.length > 0) {
          const vendor = (defGroup.definition as any).vendor;
          if (!vendor || !brandsFilters.includes(vendor)) {
            return null;
          }
        }

        // Search Filter (Name, Category or Instance Name)
        if (state.search) {
          const searchLower = state.search.toLowerCase();
          const matchesDefName = defGroup.definition.name.toLowerCase().includes(searchLower);
          const matchesCategory = group.category.toLowerCase().includes(searchLower);
          const matchesInstanceName = matchingInstances.some(inst =>
            inst.name.toLowerCase().includes(searchLower)
          );

          if (!matchesDefName && !matchesCategory && !matchesInstanceName) {
            return null;
          }

          // If instance name matches but def name doesn't, we filter instances
          if (matchesInstanceName && !matchesDefName && !matchesCategory) {
            matchingInstances = matchingInstances.filter(inst =>
              inst.name.toLowerCase().includes(searchLower)
            );
          }
        }

        // If status/location filter is active, and no instances match, hide the definition
        const hasActivePhysicalFilters = statusFilters.length > 0 || machineIdFilters.length > 0;
        if (hasActivePhysicalFilters && matchingInstances.length === 0) {
          return null;
        }

        // Recalculate derived properties for the filtered view
        const activeCount = matchingInstances.length;

        // Compute primary Status for chip
        const statusPriority: Record<string, number> = {
          'reserved': 1, 'in_use': 2, 'depleted': 3, 'expired': 4, 'available': 5, 'unknown': 6
        };

        let primaryStatus: AssetStatusType | null = null;
        if (defGroup.isConsumable && matchingInstances.length > 0) {
          const sorted = [...matchingInstances].sort((a, b) =>
            (statusPriority[a.status] || 99) - (statusPriority[b.status] || 99)
          );
          primaryStatus = sorted[0]?.status as AssetStatusType || null;
        }

        return {
          ...defGroup,
          instances: matchingInstances,
          activeCount: activeCount,
          primaryStatus: primaryStatus
        } as ResourceDefinitionGroup;

      }).filter((d): d is ResourceDefinitionGroup => d !== null);

      // Sort Definitions
      const sortedDefs = [...filteredDefs].sort((a, b) => {
        let valA: any = '';
        let valB: any = '';

        switch (state.sortBy) {
          case 'name':
            valA = a.definition.name.toLowerCase();
            valB = b.definition.name.toLowerCase();
            break;
          case 'count':
            valA = a.activeCount;
            valB = b.activeCount;
            break;
          case 'created_at':
            valA = (a.definition as any).created_at || '';
            valB = (b.definition as any).created_at || '';
            break;
        }

        const comparison = valA > valB ? 1 : (valA < valB ? -1 : 0);
        return state.sortOrder === 'asc' ? comparison : -comparison;
      });

      return {
        ...group,
        definitions: sortedDefs,
        totalCount: sortedDefs.length
      };

    }).filter(group => group.definitions.length > 0).sort((a, b) => {
      // Sort groups if 'category' sort is selected
      if (state.sortBy === 'category') {
        const comparison = a.category.localeCompare(b.category);
        return state.sortOrder === 'asc' ? comparison : -comparison;
      }
      return a.category.localeCompare(b.category); // Default category sort
    });
  });

  ngOnInit() {
    this.loadData();
  }

  loadData() {
    this.assetService.getResources().subscribe(resources => {
      console.debug(`[ASSET-DEBUG] ResourceAccordion: Loaded ${resources.length} resources`, resources.map(r => r.name));
      this.resources.set(resources);
    });

    this.assetService.getResourceDefinitions().subscribe(defs => {
      this.definitions.set(defs);
    });
    this.assetService.getMachines().subscribe(machines => {
      this.machines.set(machines);
    });
  }

  onFiltersChange(_filters: any) {
    // Legacy method - can be removed or redirected if needed
    // But viewState is now primary
  }

  getCategoryIcon(category: string): string {
    switch (category) {
      case 'Carriers': return 'grid_view';
      case 'Holders': return 'biotech';
      case 'Plates': return 'dataset';
      case 'TipRacks': return 'apps';
      case 'Containers': return 'science';
      case 'Other': return 'category';
      default: return getResourceCategoryIcon(category);
    }
  }

  getDisplayLabel(def: ResourceDefinition): string {
    return getDisplayLabel(def);
  }

  getCategoryTooltip(category: string): string {
    return getCategoryTooltip(category);
  }

  getPropertyTooltip(property: string): string {
    return getPropertyTooltip(property);
  }

  getMatchingInstanceName(defGroup: ResourceDefinitionGroup): string | null {
    const search = this.viewState().search.toLowerCase();
    if (!search) return null;
    const match = defGroup.instances.find(inst => inst.name.toLowerCase().includes(search));
    return match ? match.name : null;
  }

  openInstancesDialog(defGroup: ResourceDefinitionGroup) {
    this.dialog.open(ResourceInstancesDialogComponent, {
      width: '900px',
      data: {
        definition: defGroup.definition,
        instances: defGroup.instances,
        showDiscarded: this.viewState().filters['show_discarded']?.includes(true)
      }
    });
  }
}
