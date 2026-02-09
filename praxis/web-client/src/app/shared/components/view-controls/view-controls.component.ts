import {
  Component,
  Input,
  Output,
  EventEmitter,
  OnInit,
  OnDestroy,
  ChangeDetectionStrategy,
  signal,
  effect,
  inject,
  computed,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { MatBottomSheet, MatBottomSheetModule } from '@angular/material/bottom-sheet';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { Router, ActivatedRoute } from '@angular/router';
import { Subject, debounceTime, distinctUntilChanged, takeUntil } from 'rxjs';

import { PraxisMultiselectComponent } from '../praxis-multiselect/praxis-multiselect.component';
import { ViewTypeToggleComponent } from './view-type-toggle.component';
import { GroupBySelectComponent } from './group-by-select.component';
import { FilterChipBarComponent } from '../filter-chip-bar/filter-chip-bar.component';
import { ViewControlsMobileSheetComponent } from './view-controls-mobile-sheet.component';
import {
  ViewControlsState,
  ViewControlsConfig,
  ViewType,
  ActiveFilter,
} from './view-controls.types';

@Component({
  selector: 'app-view-controls',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatSelectModule,
    MatFormFieldModule,
    MatMenuModule,
    MatDividerModule,
    MatBottomSheetModule,
    PraxisMultiselectComponent,
    ViewTypeToggleComponent,
    GroupBySelectComponent,
    FilterChipBarComponent,
  ],
  template: `
<div class="view-controls-container" [class.mobile]="isMobile()">
  <!-- Desktop / Table Layout -->
  @if (!isMobile()) {
    <div class="controls-row-primary">
      <div class="left-group">
        <!-- Search -->
        <div class="search-wrapper">
          <mat-icon class="search-icon">search</mat-icon>
          <input
            type="text"
            class="search-input"
            [placeholder]="config.defaults?.search || 'Search...'"
            [value]="state.search"
            (input)="onSearchInput($event)"
            aria-label="Search"
          />
          @if (state.search) {
            <button mat-icon-button class="clear-search" (click)="clearSearch()">
              <mat-icon>close</mat-icon>
            </button>
          }
        </div>

        <!-- View Type Toggle -->
        @if (config.viewTypes && config.viewTypes.length > 1) {
          <app-view-type-toggle
            [viewType]="state.viewType"
            [availableTypes]="config.viewTypes"
            (viewTypeChange)="onViewTypeChange($event)"
          ></app-view-type-toggle>
        }

        <mat-divider vertical="true" class="h-6 mx-2"></mat-divider>

        <!-- Group By -->
        @if (config.groupByOptions && config.groupByOptions.length > 0) {
          <app-group-by-select
            [value]="state.groupBy"
            [options]="config.groupByOptions"
            (valueChange)="onGroupByChange($event)"
          ></app-group-by-select>
        }

        <!-- Pinned Filters -->
        <div class="pinned-filters">
          @for (filter of pinnedFilters(); track filter.key) {
            <app-praxis-multiselect
              [label]="filter.label"
              [options]="filter.options || []"
              [value]="state.filters[filter.key] || []"
              (valueChange)="onFilterChange(filter.key, $event)"
              class="compact-filter"
            ></app-praxis-multiselect>
          }
        </div>

        <!-- Add Filter Button -->
        @if (unpinnedFilters().length > 0) {
          <button mat-stroked-button [matMenuTriggerFor]="filterMenu" class="add-filter-btn">
            <mat-icon>add</mat-icon>
            Add Filter
          </button>
          <mat-menu #filterMenu="matMenu" class="filter-popover-menu">
            @for (filter of unpinnedFilters(); track filter.key) {
              <div class="filter-menu-item" (click)="$event.stopPropagation()">
                <span class="filter-label">{{ filter.label }}</span>
                <app-praxis-multiselect
                  [options]="filter.options || []"
                  [value]="state.filters[filter.key] || []"
                  (valueChange)="onFilterChange(filter.key, $event)"
                ></app-praxis-multiselect>
              </div>
            }
          </mat-menu>
        }
      </div>

      <div class="right-group">
        <!-- Sort -->
        @if (config.sortOptions && config.sortOptions.length > 0) {
          <div class="sort-controls">
            <mat-form-field appearance="outline" class="sort-field" subscriptSizing="dynamic">
              <mat-label>Sort By</mat-label>
              <mat-select [value]="state.sortBy" (selectionChange)="onSortByChange($event.value)">
                @for (option of config.sortOptions; track option.value) {
                  <mat-option [value]="option.value">{{ option.label }}</mat-option>
                }
              </mat-select>
            </mat-form-field>
            <button
              mat-icon-button
              class="sort-order-btn"
              [matTooltip]="state.sortOrder === 'asc' ? 'Sort Ascending' : 'Sort Descending'"
              (click)="toggleSortOrder()"
            >
              <mat-icon>{{ state.sortOrder === 'asc' ? 'arrow_upward' : 'arrow_downward' }}</mat-icon>
            </button>
          </div>
        }

        <!-- Result Count -->
        @if (config.showResultCount && state.resultCount !== undefined) {
          <span class="result-count">{{ state.resultCount }} items</span>
        }
      </div>
    </div>
  } @else {
    <!-- Mobile Layout -->
    <div class="controls-row-mobile">
      <div class="search-wrapper mobile">
        <mat-icon class="search-icon">search</mat-icon>
        <input
          type="text"
          class="search-input"
          [placeholder]="config.defaults?.search || 'Search...'"
          [value]="state.search"
          (input)="onSearchInput($event)"
          aria-label="Search"
        />
      </div>
      <button mat-stroked-button (click)="openMobileFilters()" class="mobile-filters-btn">
        <mat-icon>filter_list</mat-icon>
        Filters
        @if (activeFilters().length > 0) {
          <span class="mobile-filter-badge">{{ activeFilters().length }}</span>
        }
      </button>
    </div>
  }

  <!-- Active Filter Chips (Row 2) -->
  <app-filter-chip-bar
    [filters]="activeFilters()"
    (removeValue)="removeFilterValue($event)"
    (clearAll)="clearAll()"
  ></app-filter-chip-bar>
</div>
  `,
  styles: [`
:host {
  display: block;
}

.view-controls-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.5rem 0;
}

.controls-row-primary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.left-group, .right-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-wrapper {
  position: relative;
  min-width: 200px;
  max-width: 300px;
  display: flex;
  align-items: center;

  .search-icon {
    position: absolute;
    left: 12px;
    font-size: 18px;
    width: 18px;
    height: 18px;
    color: var(--theme-text-secondary);
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    height: 2.25rem;
    padding: 0 2.5rem;
    border-radius: 1.125rem;
    border: 1px solid var(--theme-border);
    background-color: var(--theme-surface-elevated);
    color: var(--theme-text-primary);
    font-size: 0.875rem;
    transition: all 0.2s ease;

    &:focus {
      outline: none;
      border-color: var(--primary-color);
      box-shadow: 0 0 0 2px var(--mat-sys-primary-container);
    }

    &::placeholder {
      color: var(--theme-text-secondary);
      opacity: 0.6;
    }
  }

  .clear-search {
    position: absolute;
    right: 8px;
    width: 24px;
    height: 24px;
    line-height: 24px;
    
    .mat-icon {
      font-size: 16px;
      width: 16px;
      height: 16px;
    }
  }
}

.pinned-filters {
  display: flex;
  align-items: center;
  gap: 8px;
}

.compact-filter {
  ::ng-deep .praxis-multiselect-trigger {
    height: 32px !important;
    padding: 0 10px !important;
    border-radius: 16px !important;
  }
}

.add-filter-btn {
  height: 2rem;
  border-radius: 1rem;
  font-size: 0.8125rem;
  padding: 0 0.75rem;
  border-style: dashed;
}

.filter-menu-item {
  padding: 8px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 200px;

  .filter-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--theme-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
}

.sort-controls {
  display: flex;
  align-items: center;
  gap: 4px;

  .sort-field {
    width: 140px;
    ::ng-deep {
      .mat-mdc-text-field-wrapper {
        height: 32px !important;
        padding: 0 8px !important;
      }
      .mat-mdc-form-field-infix {
        padding: 0 !important;
        min-height: auto !important;
      }
      .mat-mdc-form-field-label-wrapper {
        top: -8px;
      }
    }
  }

  .sort-order-btn {
    width: 32px;
    height: 32px;
    line-height: 32px;
    .mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }
  }
}

.result-count {
  font-size: 13px;
  color: var(--theme-text-secondary);
  font-weight: 500;
}


.controls-row-mobile {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .search-wrapper.mobile {
    flex: 1;
    max-width: none;
  }
  
  .mobile-filters-btn {
    height: 36px;
    border-radius: 18px;
    position: relative;
  }

  .mobile-filter-badge {
    position: absolute;
    top: -6px;
    right: -6px;
    background: var(--primary-color);
    color: white;
    font-size: 10px;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
  }
}
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ViewControlsComponent implements OnInit, OnDestroy {
  @Input() set config(value: ViewControlsConfig) {
    this._config.set(value);
  }
  get config(): ViewControlsConfig {
    return this._config();
  }

  @Input() set state(value: ViewControlsState) {
    this._state.set({
      ...this._state(),
      ...value,
    });
  }
  get state(): ViewControlsState {
    return this._state();
  }

  @Output() stateChange = new EventEmitter<ViewControlsState>();
  @Output() viewTypeChange = new EventEmitter<ViewType>();
  @Output() groupByChange = new EventEmitter<string | null>();
  @Output() filtersChange = new EventEmitter<Record<string, unknown[]>>();
  @Output() sortChange = new EventEmitter<{
    sortBy: string;
    sortOrder: 'asc' | 'desc';
  }>();
  @Output() searchChange = new EventEmitter<string>();

  private _config = signal<ViewControlsConfig>({});

  private _state = signal<ViewControlsState>({
    viewType: 'card',
    groupBy: null,
    filters: {},
    sortBy: '',
    sortOrder: 'asc',
    search: '',
  });

  private searchSubject = new Subject<string>();
  private destroy$ = new Subject<void>();

  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private bottomSheet = inject(MatBottomSheet);
  private breakpointObserver = inject(BreakpointObserver);

  isMobile = signal(false);

  // Filters pinned to the bar (always visible)
  pinnedFilters = computed(() => {
    // Default pinning: Status and Category or first 2
    const filters = this._config().filters || [];
    if (filters.some(f => f.pinned)) {
      return filters.filter(f => f.pinned);
    }

    // MVP: Pin Status and Category if they exist
    const highlighted = filters.filter(f =>
      ['status', 'category'].includes(f.key.toLowerCase())
    );

    if (highlighted.length > 0) return highlighted;

    return filters.slice(0, 2);
  });

  // Filters in the "+ Add Filter" menu
  unpinnedFilters = computed(() => {
    const pinnedKeys = new Set(this.pinnedFilters().map(f => f.key));
    return (this._config().filters || []).filter(f => !pinnedKeys.has(f.key));
  });

  // Active filters for chip display
  activeFilters = computed<ActiveFilter[]>(() => {
    const result: ActiveFilter[] = [];
    const currentState = this._state();

    for (const [key, values] of Object.entries(currentState.filters)) {
      if (!values || (Array.isArray(values) && values.length === 0)) continue;

      const config = this._config().filters?.find(f => f.key === key);
      if (!config) continue;

      const valArray = Array.isArray(values) ? values : [values];
      const displayValues = valArray
        .map(v => config.options?.find(o => o.value === v)?.label || String(v))
        .join(', ');

      result.push({
        filterId: key,
        label: config.label,
        values: valArray,
        displayText: `${config.label}: ${displayValues}`
      });
    }

    return result;
  });

  constructor() {
    effect(() => {
      const currentState = this._state();
      this.persistState(currentState);
      if (this.config.enableUrlSync) {
        this.syncToUrl(currentState);
      }
    });

    this.breakpointObserver
      .observe([Breakpoints.Handset, Breakpoints.HandsetPortrait, '(max-width: 768px)'])
      .pipe(takeUntil(this.destroy$))
      .subscribe(result => {
        this.isMobile.set(result.matches);
      });
  }

  ngOnInit() {
    this.initializeState();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private initializeState() {
    const persisted = this.loadPersistedState();
    const urlState = this.config.enableUrlSync ? this.readFromUrl() : {};
    const defaults = this.config.defaults || {};

    const initialState: ViewControlsState = {
      ...this._state(),
      ...defaults,
      ...persisted,
      ...urlState,
    };

    // Ensure state fields are not undefined (fallback to base defaults)
    initialState.search = initialState.search ?? '';
    initialState.sortBy = initialState.sortBy ?? '';
    initialState.sortOrder = initialState.sortOrder ?? 'asc';
    initialState.filters = initialState.filters ?? {};

    // Ensure all filter keys from config are present in state as arrays
    if (this.config.filters) {
      this.config.filters.forEach(f => {
        if (initialState.filters[f.key] === undefined) {
          initialState.filters[f.key] = [];
        } else if (!Array.isArray(initialState.filters[f.key])) {
          initialState.filters[f.key] = [initialState.filters[f.key]];
        }
      });
    }

    this._state.set(initialState);

    // Setup search debounce
    this.searchSubject
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntil(this.destroy$))
      .subscribe((value) => {
        this.updateState({ search: value });
        this.searchChange.emit(value);
      });
  }

  get hasActiveFilters(): boolean {
    return this.activeFilters().length > 0 || !!this._state().search || !!this._state().groupBy;
  }

  onSearchInput(event: Event) {
    const input = event.target as HTMLInputElement;
    this.searchSubject.next(input.value);
  }

  clearSearch() {
    this.searchSubject.next('');
    this.updateState({ search: '' });
    this.searchChange.emit('');
  }

  onViewTypeChange(viewType: ViewType) {
    this.updateState({ viewType });
    this.viewTypeChange.emit(viewType);
  }

  onGroupByChange(groupBy: string | null) {
    this.updateState({ groupBy });
    this.groupByChange.emit(groupBy);
  }

  onFilterChange(key: string, value: unknown[]) {
    const valArray = Array.isArray(value) ? value : [value];
    const newFilters = { ...this.state.filters, [key]: valArray };
    this.updateState({ filters: newFilters });
    this.filtersChange.emit(newFilters);
  }

  removeFilter(filterId: string) {
    const newFilters = { ...this.state.filters };
    delete newFilters[filterId];
    this.updateState({ filters: newFilters });
    this.filtersChange.emit(newFilters);
  }

  /** Remove a specific value from a filter (keeps other values in that filter) */
  removeFilterValue(event: { filterId: string; value: unknown }) {
    const currentValues = this.state.filters[event.filterId] || [];
    const newValues = currentValues.filter(v => v !== event.value);

    const newFilters = { ...this.state.filters };
    if (newValues.length === 0) {
      // If no values left, remove the filter entirely
      delete newFilters[event.filterId];
    } else {
      newFilters[event.filterId] = newValues;
    }

    this.updateState({ filters: newFilters });
    this.filtersChange.emit(newFilters);
  }

  onSortByChange(sortBy: string) {
    this.updateState({ sortBy });
    this.sortChange.emit({ sortBy, sortOrder: this.state.sortOrder });
  }

  toggleSortOrder() {
    const sortOrder = this.state.sortOrder === 'asc' ? 'desc' : 'asc';
    this.updateState({ sortOrder });
    this.sortChange.emit({ sortBy: this.state.sortBy, sortOrder });
  }

  clearAll() {
    const clearedFilters: Record<string, unknown[]> = {};
    if (this.config.filters) {
      this.config.filters.forEach(f => clearedFilters[f.key] = []);
    }

    const newState: Partial<ViewControlsState> = {
      search: '',
      groupBy: null,
      filters: clearedFilters,
    };

    this.updateState(newState);
    this.searchChange.emit('');
    this.groupByChange.emit(null);
    this.filtersChange.emit(clearedFilters);
  }

  openMobileFilters() {
    const sheetRef = this.bottomSheet.open(ViewControlsMobileSheetComponent, {
      data: {
        config: this.config,
        state: this.state
      }
    });

    sheetRef.afterDismissed().subscribe((result: ViewControlsState | undefined) => {
      if (result) {
        this.updateState(result);
      }
    });
  }

  private updateState(patch: Partial<ViewControlsState>) {
    const newState = { ...this.state, ...patch };
    this._state.set(newState);
    this.stateChange.emit(newState);
  }

  private loadPersistedState(): Partial<ViewControlsState> {
    if (!this.config.storageKey) return {};
    try {
      const stored = localStorage.getItem(`viewControls.${this.config.storageKey}`);
      return stored ? JSON.parse(stored) : {};
    } catch (e) {
      console.warn('Failed to load persisted view controls state', e);
      return {};
    }
  }

  private persistState(state: ViewControlsState): void {
    if (!this.config.storageKey) return;
    try {
      localStorage.setItem(`viewControls.${this.config.storageKey}`, JSON.stringify(state));
    } catch (e) {
      console.warn('Failed to persist view controls state', e);
    }
  }

  private readFromUrl(): Partial<ViewControlsState> {
    const params = this.route.snapshot.queryParams;
    const filters: Record<string, unknown[]> = {};
    const prefix = this.config.urlParamPrefix || '';

    this.config.filters?.forEach(f => {
      const paramName = prefix + (f.urlParam || f.key);
      const value = params[paramName];
      if (value) {
        filters[f.key] = Array.isArray(value) ? value : value.split(',');
      }
    });

    const state: Partial<ViewControlsState> = { filters };

    if (params['q']) state.search = params['q'];
    if (params['groupBy']) state.groupBy = params['groupBy'];
    if (params['sortBy']) state.sortBy = params['sortBy'];
    if (params['sortOrder']) state.sortOrder = params['sortOrder'] as 'asc' | 'desc';

    return state;
  }

  private syncToUrl(state: ViewControlsState): void {
    const queryParams: Record<string, string | null> = {};
    const prefix = this.config.urlParamPrefix || '';

    this.config.filters?.forEach(f => {
      const paramName = prefix + (f.urlParam || f.key);
      const values = state.filters[f.key];
      queryParams[paramName] = values?.length ? values.join(',') : null;
    });

    queryParams['q'] = state.search || null;
    queryParams['groupBy'] = state.groupBy || null;
    queryParams['sortBy'] = state.sortBy || null;
    queryParams['sortOrder'] = state.sortOrder !== 'asc' ? state.sortOrder : null;

    this.router.navigate([], {
      relativeTo: this.route,
      queryParams,
      queryParamsHandling: 'merge',
      replaceUrl: true
    });
  }
}
