import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

import { ActiveRunsPanelComponent } from './components/active-runs-panel.component';
import { RunHistoryTableComponent } from './components/run-history-table.component';
import { RunStatsPanelComponent } from './components/run-stats-panel.component';
import { ViewControlsComponent } from '@shared/components/view-controls/view-controls.component';
import { ViewControlsConfig, ViewControlsState } from '@shared/components/view-controls/view-controls.types';
import { ProtocolService } from '@features/protocols/services/protocol.service';
import { MachinesService } from '@core/api-generated/services/MachinesService';
import { ApiWrapperService } from '@core/services/api-wrapper.service';
import { RunStatus, FilterState } from './models/monitor.models';
import { MachineRead } from '@core/api-generated/models/MachineRead';
import { ProtocolDefinition } from '@features/protocols/models/protocol.models';

/**
 * Main dashboard for the Execution Monitor feature.
 * Displays active runs and run history.
 */
@Component({
  selector: 'app-execution-monitor',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    ActiveRunsPanelComponent,
    RunHistoryTableComponent,
    RunStatsPanelComponent,
    ViewControlsComponent
  ],
  template: `
    <div class="p-6 max-w-screen-2xl mx-auto">
      <!-- Header -->
      <div class="flex items-center gap-4 mb-8">
        <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-[var(--mat-sys-success-container)] to-[var(--mat-sys-tertiary-container)] flex items-center justify-center border border-[var(--theme-border)]">
          <mat-icon class="text-[var(--mat-sys-success)] !w-6 !h-6 !text-[24px]">monitor_heart</mat-icon>
        </div>
        <div>
          <h1 class="text-3xl font-bold text-sys-text-primary mb-1">Execution Monitor</h1>
          <p class="text-sys-text-secondary">Track and analyze protocol executions</p>
        </div>
      </div>

      <!-- Summary Statistics -->
      <app-run-stats-panel></app-run-stats-panel>

      <!-- Active Runs Panel -->
      <app-active-runs-panel></app-active-runs-panel>

      <!-- View Controls -->
      <app-view-controls
        [config]="viewControlsConfig()"
        (stateChange)="onViewControlsChange($event)">
      </app-view-controls>

      <!-- Run History Table -->
      <app-run-history-table 
        [filters]="currentFilters()" 
        [search]="searchQuery()" 
        data-tour-id="run-history-table">
      </app-run-history-table>
    </div>
  `,
})
export class ExecutionMonitorComponent implements OnInit {
  private readonly protocolService = inject(ProtocolService);
  private readonly apiWrapper = inject(ApiWrapperService);

  readonly currentFilters = signal<FilterState | null>(null);
  readonly searchQuery = signal('');

  readonly protocols = signal<ProtocolDefinition[]>([]);
  readonly machines = signal<MachineRead[]>([]);

  readonly viewControlsConfig = computed<ViewControlsConfig>(() => ({
    storageKey: 'execution-monitor',
    filters: [
      {
        key: 'status',
        label: 'Status',
        type: 'multiselect',
        pinned: true,
        options: [
          { label: 'Running', value: 'running' },
          { label: 'Completed', value: 'completed' },
          { label: 'Failed', value: 'failed' },
          { label: 'Paused', value: 'paused' },
          { label: 'Pending', value: 'pending' },
          { label: 'Queued', value: 'queued' },
          { label: 'Cancelled', value: 'cancelled' }
        ]
      },
      {
        key: 'machine_id',
        label: 'Machine',
        type: 'multiselect',
        options: this.machines().map(m => ({ label: m.name || 'Unknown', value: m.accession_id }))
      },
      {
        key: 'protocol_id',
        label: 'Protocol',
        type: 'multiselect',
        options: this.protocols().map(p => ({ label: p.name || 'Unknown', value: p.accession_id }))
      }
    ],
    sortOptions: [
      { label: 'Date Created', value: 'created_at' },
      { label: 'Start Time', value: 'start_time' },
      { label: 'Status', value: 'status' }
    ],
    defaults: {
      sortBy: 'created_at',
      sortOrder: 'desc'
    }
  }));

  ngOnInit(): void {
    this.loadFilterOptions();
  }

  private loadFilterOptions(): void {
    this.protocolService.getProtocols().subscribe(protocols => {
      this.protocols.set(protocols);
    });

    this.apiWrapper.wrap(MachinesService.getMultiApiV1MachinesGet()).subscribe((machines: MachineRead[]) => {
      this.machines.set(machines);
    });
  }

  onViewControlsChange(state: ViewControlsState): void {
    this.searchQuery.set(state.search);

    // Map ViewControlsState to FilterState
    this.currentFilters.set({
      status: (state.filters['status'] as RunStatus[]) || [],
      protocol_id: (state.filters['protocol_id'] as string[]) || null,
      machine_id: (state.filters['machine_id'] as string[]) || null,
      sort_by: (state.sortBy as FilterState['sort_by']) || 'created_at',
      sort_order: state.sortOrder
    });
  }

  readonly activeFiltersCount = computed(() => {
    const f = this.currentFilters();
    if (!f) return 0;
    let count = 0;
    if (f.status?.length) count++;
    if (f.protocol_id?.length) count++;
    if (f.machine_id?.length) count++;
    return count;
  });

  onFiltersChange(filters: FilterState): void {
    this.currentFilters.set(filters);
  }

  onSearch(term: string): void {
    this.searchQuery.set(term);
  }

  clearFilters(): void {
    this.searchQuery.set('');
  }
}
