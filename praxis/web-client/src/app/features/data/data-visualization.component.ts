import { Component, ChangeDetectionStrategy, signal, computed, OnInit, OnDestroy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { FormsModule } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { ViewControlsComponent } from '@shared/components/view-controls/view-controls.component';
import { ViewControlsConfig, ViewControlsState } from '@shared/components/view-controls/view-controls.types';
import { WellSelectorDialogComponent } from '@shared/components/well-selector-dialog/well-selector-dialog.component';
import { PlotlyModule } from 'angular-plotly.js';
import { interval, Subscription } from 'rxjs';
import { ProtocolService } from '@features/protocols/services/protocol.service';
import { ProtocolDefinition } from '@features/protocols/models/protocol.models';

interface TransferDataPoint {
  timestamp: Date;
  well: string;
  volumeTransferred: number;
  cumulativeVolume: number;
  temperature?: number;
  pressure?: number;
  protocolName?: string;
  status?: string;
}

interface MockRun {
  id: string;
  protocolName: string;
  protocolId: string;
  measurementType: string;
  plateId: string;
  status: 'completed' | 'running' | 'failed';
  startTime: Date;
  endTime?: Date;
  wellCount: number;
  totalVolume: number;
}

@Component({
  selector: 'app-data-visualization',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatSelectModule,
    MatFormFieldModule,
    MatChipsModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    PlotlyModule,
    FormsModule,
    ViewControlsComponent
  ],
  template: `
    <div class="data-page">
      <header class="page-header">
        <div class="title-row">
          <h1>Data Visualization</h1>
          <button mat-flat-button color="primary" (click)="exportChart()">
            <mat-icon>download</mat-icon>
            Export
          </button>
        </div>
        <p class="subtitle">Analyze experiment data and transfer volumes</p>
      </header>

      <!-- Standardized View Controls -->
      <div class="bg-sys-surface border-b border-sys-outline-variant px-4 py-2 mb-4 rounded-xl shadow-sm">
        <app-view-controls
          [config]="viewConfig()"
          [state]="viewState()"
          (stateChange)="onViewStateChange($event)">
        </app-view-controls>
      </div>

      <!-- Chart Configuration -->
      <mat-card class="config-card">
        <mat-card-content>
          <div class="config-row">
            <div>
              <mat-form-field appearance="outline" subscriptSizing="dynamic" class="min-w-[150px]">
                <mat-label>X-Axis</mat-label>
                <mat-select [ngModel]="xAxis()" (ngModelChange)="xAxis.set($event)">
                  <mat-option *ngFor="let opt of xAxisOptions" [value]="opt.value">{{ opt.label }}</mat-option>
                </mat-select>
              </mat-form-field>
            </div>

            <div>
              <mat-form-field appearance="outline" subscriptSizing="dynamic" class="min-w-[150px]">
                <mat-label>Y-Axis</mat-label>
                <mat-select [ngModel]="yAxis()" (ngModelChange)="yAxis.set($event)">
                  <mat-option *ngFor="let opt of yAxisOptions" [value]="opt.value">{{ opt.label }}</mat-option>
                </mat-select>
              </mat-form-field>
            </div>

            <div class="well-filter">
              <button mat-stroked-button (click)="openWellSelector()">
                <mat-icon>grid_view</mat-icon>
                {{ selectedWells().length > 0
                   ? selectedWells().length + ' wells selected'
                   : 'Select Wells' }}
              </button>

              <!-- Show selected wells as preview chips (collapsed if >5) -->
              @if (selectedWells().length > 0 && selectedWells().length <= 5) {
                <mat-chip-set>
                  @for (well of selectedWells(); track well) {
                    <mat-chip (removed)="removeWell(well)">
                      {{ well }}
                      <button matChipRemove>
                        <mat-icon>cancel</mat-icon>
                      </button>
                    </mat-chip>
                  }
                </mat-chip-set>
              }

              @if (selectedWells().length > 5) {
                <span class="text-sm text-sys-on-surface-variant">
                  {{ selectedWells().slice(0, 3).join(', ') }}... and {{ selectedWells().length - 3 }} more
                </span>
              }

              <div class="well-actions">
                <button mat-button (click)="selectAllWells()">All</button>
                <button mat-button (click)="clearWells()">Clear</button>
              </div>
            </div>
          </div>
        </mat-card-content>
      </mat-card>

      <!-- Main Chart -->
      <mat-card class="chart-card">
        <mat-card-header>
          <div class="flex justify-between items-start w-full">
            <div>
              <mat-card-title>{{ chartTitle() }}</mat-card-title>
              @if (selectedRun()) {
                <mat-card-subtitle>
                  Run: {{ selectedRun()?.id }} | Started: {{ selectedRun()?.startTime | date:'medium' }}
                </mat-card-subtitle>
              }
            </div>
            @if (selectedPoint(); as point) {
              <div class="selected-point-info bg-sys-surface-container-high p-3 rounded-lg border border-sys-outline-variant">
                <div class="text-xs font-bold uppercase tracking-wider text-sys-primary mb-1">Selected Point</div>
                <div class="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                  <span class="text-sys-on-surface-variant">X: {{ point.x }}</span>
                  <span class="text-sys-on-surface-variant">Y: {{ point.y }}</span>
                  @if (point.temp) {
                    <span class="text-sys-on-surface-variant">Temp: {{ point.temp }}</span>
                  }
                </div>
              </div>
            }
          </div>
        </mat-card-header>
        <mat-card-content>
          <div class="chart-container">
            @if (filteredData().length === 0) {
              <div class="flex flex-col items-center justify-center h-full text-sys-on-surface-variant">
                <mat-icon class="text-6xl h-auto w-auto mb-4 opacity-20">analytics</mat-icon>
                <p class="text-lg">No data available to display.</p>
              </div>
            } @else {
              <plotly-plot
                [data]="chartData()"
                [layout]="chartLayout()"
                [config]="chartConfig"
                (plotly_click)="onPointClick($event)"
                [useResizeHandler]="true"
                [style]="{position: 'relative', width: '100%', height: '100%'}">
              </plotly-plot>
            }
          </div>
        </mat-card-content>
      </mat-card>

      <!-- Stats Grid -->
      <div class="stats-grid">
        <mat-card class="stat-card">
          <mat-card-content>
            <mat-icon>science</mat-icon>
            <div class="stat-value">{{ totalVolume() | number:'1.0-0' }} µL</div>
            <div class="stat-label">Total Volume Transferred</div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <mat-icon>grid_view</mat-icon>
            <div class="stat-value">{{ selectedWells().length }}</div>
            <div class="stat-label">Wells Selected</div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <mat-icon>timeline</mat-icon>
            <div class="stat-value">{{ filteredData().length }}</div>
            <div class="stat-label">Data Points</div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <mat-icon>history</mat-icon>
            <div class="stat-value">{{ runs().length }}</div>
            <div class="stat-label">Total Runs</div>
          </mat-card-content>
        </mat-card>
      </div>

      <!-- Run History Table -->
      <mat-card class="history-card">
        <mat-card-header>
          <mat-card-title>Run History</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <table mat-table [dataSource]="filteredRunsTable()" class="run-table">
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>Status</th>
              <td mat-cell *matCellDef="let run">
                <mat-icon [class]="'status-' + run.status" [matTooltip]="run.status">
                  {{ run.status === 'completed' ? 'check_circle' : run.status === 'running' ? 'pending' : 'error' }}
                </mat-icon>
              </td>
            </ng-container>

            <ng-container matColumnDef="protocol">
              <th mat-header-cell *matHeaderCellDef>Protocol</th>
              <td mat-cell *matCellDef="let run">{{ run.protocolName }}</td>
            </ng-container>

            <ng-container matColumnDef="startTime">
              <th mat-header-cell *matHeaderCellDef>Started</th>
              <td mat-cell *matCellDef="let run">{{ run.startTime | date:'short' }}</td>
            </ng-container>

            <ng-container matColumnDef="duration">
              <th mat-header-cell *matHeaderCellDef>Duration</th>
              <td mat-cell *matCellDef="let run">
                {{ run.endTime ? formatDuration(run.startTime, run.endTime) : 'Running...' }}
              </td>
            </ng-container>

            <ng-container matColumnDef="wells">
              <th mat-header-cell *matHeaderCellDef>Wells</th>
              <td mat-cell *matCellDef="let run">{{ run.wellCount }}</td>
            </ng-container>

            <ng-container matColumnDef="volume">
              <th mat-header-cell *matHeaderCellDef>Volume</th>
              <td mat-cell *matCellDef="let run">{{ run.totalVolume | number:'1.0-0' }} µL</td>
            </ng-container>

            <ng-container matColumnDef="actions">
              <th mat-header-cell *matHeaderCellDef></th>
              <td mat-cell *matCellDef="let run">
                <button mat-icon-button matTooltip="View Details" (click)="selectRun(run)">
                  <mat-icon>visibility</mat-icon>
                </button>
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr mat-row *matRowDef="let row; columns: displayedColumns;"
                [class.selected-row]="row.id === selectedRunId"
                (click)="selectRun(row)"></tr>
          </table>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .data-page {
      padding: 0 24px 24px 24px;
      max-width: 1400px;
      margin: 0 auto;
    }

    .page-header {
      margin-bottom: 16px;
      padding-top: 24px;
    }

    .title-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }

    .page-header h1 {
      margin: 0;
      font-size: 2rem;
      font-weight: 500;
    }

    .subtitle {
      margin: 4px 0 0;
      color: var(--sys-on-surface-variant);
    }

    .selector-card {
      margin-bottom: 16px;
    }

    .selector-row {
      display: flex;
      gap: 16px;
      align-items: center;
      flex-wrap: wrap;
    }

    .protocol-select {
      min-width: 250px;
    }

    .run-select {
      min-width: 300px;
      flex: 1;
    }

    .group-select {
        min-width: 150px;
    }

    .run-option {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .run-option mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    .config-card {
      margin-bottom: 24px;
    }

    .config-row {
      display: flex;
      gap: 16px;
      align-items: center;
      flex-wrap: wrap;
    }

    .config-row mat-form-field {
      min-width: 180px;
    }

    .well-filter {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      background: var(--sys-surface-container-low);
      padding: 12px 16px;
      border-radius: 12px;
      border: 1px solid var(--sys-outline-variant);
    }

    .well-actions {
      display: flex;
      gap: 4px;
      margin-left: auto;
    }

    .filter-label {
      font-size: 0.9rem;
      color: var(--sys-on-surface-variant);
      white-space: nowrap;
    }

    mat-chip {
      --mdc-chip-label-text-size: 12px;
      height: 32px !important;
    }

    .chart-card {
      margin-bottom: 24px;
    }

    .chart-container {
      width: 100%;
      height: 450px;
      min-height: 450px;
    }

    .selected-point-info {
      min-width: 150px;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }

    .stat-card mat-card-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding: 24px;
    }

    .stat-card mat-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
      color: var(--sys-primary);
      margin-bottom: 8px;
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 600;
      color: var(--sys-on-surface);
    }

    .stat-label {
      font-size: 0.85rem;
      color: var(--sys-on-surface-variant);
    }

    .history-card {
      margin-top: 24px;
    }

    .run-table {
      width: 100%;
    }

    .run-table tr.selected-row {
      background: var(--sys-surface-variant);
    }

    .run-table tr:hover {
      background: var(--sys-surface-container-high);
      cursor: pointer;
    }

    .status-completed {
      color: var(--status-success);
    }

    .status-running {
      color: var(--status-warning);
    }

    .status-failed {
      color: var(--status-error);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DataVisualizationComponent implements OnInit, OnDestroy {
  private protocolService = inject(ProtocolService);
  private dialog = inject(MatDialog);

  // Table columns
  displayedColumns = ['status', 'protocol', 'startTime', 'duration', 'wells', 'volume', 'actions'];

  // Standardized View Controls
  viewConfig = computed<ViewControlsConfig>(() => ({
    viewTypes: ['table'], // Only table view for history
    groupByOptions: [
      { label: 'Well', value: 'well' },
      { label: 'Experiment', value: 'protocol' },
      { label: 'Status', value: 'status' }
    ],
    filters: [
      {
        key: 'protocolId',
        label: 'Protocol',
        type: 'multiselect',
        options: this.protocols().map(p => ({ label: p.name, value: p.accession_id }))
      },
      {
        key: 'measurementType',
        label: 'Measurement Type',
        type: 'multiselect',
        options: this.availableMeasurementTypes().map(m => ({ label: m, value: m }))
      },
      {
        key: 'plateId',
        label: 'Plate ID',
        type: 'multiselect',
        options: this.availablePlateIds().map(p => ({ label: p, value: p }))
      },
      {
        key: 'status',
        label: 'Status',
        type: 'multiselect',
        options: [
          { label: 'Completed', value: 'completed', icon: 'check_circle' },
          { label: 'Running', value: 'running', icon: 'pending' },
          { label: 'Failed', value: 'failed', icon: 'error' }
        ]
      }
    ],
    sortOptions: [
      { label: 'Start Time', value: 'startTime' },
      { label: 'Protocol', value: 'protocolName' },
      { label: 'Volume', value: 'totalVolume' }
    ],
    storageKey: 'data-viz-history',
    defaults: {
      viewType: 'table',
      sortBy: 'startTime',
      sortOrder: 'desc'
    }
  }));

  viewState = signal<ViewControlsState>({
    viewType: 'table',
    groupBy: 'well',
    filters: {},
    sortBy: 'startTime',
    sortOrder: 'desc',
    search: ''
  });

  // Well configuration
  allWells = Array.from({ length: 96 }, (_, i) => {
    const row = String.fromCharCode(65 + Math.floor(i / 12));
    const col = (i % 12) + 1;
    return `${row}${col}`;
  });
  selectedWells = signal<string[]>(['A1', 'A2', 'A3', 'A4', 'B1', 'B2', 'B3', 'B4']); // Initial selection

  // Chart configuration
  xAxis = signal<string>('timestamp');
  yAxis = signal<string>('volumeTransferred');

  // Selection state
  isLoading = signal(true);
  selectedRunId = '';
  showFilters = signal(true);
  groupBy = computed(() => this.viewState().groupBy || 'well');

  // Data signals
  protocols = signal<ProtocolDefinition[]>([]);
  runs = signal<MockRun[]>([]);
  data = signal<TransferDataPoint[]>([]);
  selectedPoint = signal<{x: any, y: any, well: string, temp?: number} | null>(null);
  private updateSubscription?: Subscription;

  availableMeasurementTypes = computed(() => {
    const types = new Set<string>();
    this.runs().forEach(r => {
      if (r.measurementType) types.add(r.measurementType);
    });
    return Array.from(types).sort();
  });

  availablePlateIds = computed(() => {
    const ids = new Set<string>();
    this.runs().forEach(r => {
      if (r.plateId) ids.add(r.plateId);
    });
    return Array.from(ids).sort();
  });

  readonly xAxisOptions = [
    { label: 'Time', value: 'timestamp' },
    { label: 'Well', value: 'well' }
  ];

  readonly yAxisOptions = [
    { label: 'Volume Transferred (µL)', value: 'volumeTransferred' },
    { label: 'Cumulative Volume (µL)', value: 'cumulativeVolume' },
    { label: 'Temperature (°C)', value: 'temperature' },
    { label: 'Pressure (kPa)', value: 'pressure' }
  ];

  chartConfig = {
    displayModeBar: true,
    responsive: true,
    modeBarButtonsToRemove: ['lasso2d', 'select2d']
  };

  // Computed: filter runs by standardize ViewControls state
  filteredRunsTable = computed(() => {
    let filtered = this.runs();
    const state = this.viewState();

    // 1. Search Filter
    if (state.search) {
      const q = state.search.toLowerCase();
      filtered = filtered.filter(r =>
        r.protocolName.toLowerCase().includes(q) ||
        r.id.toLowerCase().includes(q)
      );
    }

    // 2. Protocol Filter
    const protocolFilters = (state.filters['protocolId'] || []) as string[];
    if (protocolFilters.length > 0) {
      filtered = filtered.filter(r => protocolFilters.includes(r.protocolId));
    }

    // 3. Status Filter
    const statusFilters = (state.filters['status'] || []) as string[];
    if (statusFilters.length > 0) {
      filtered = filtered.filter(r => statusFilters.includes(r.status));
    }

    // 4. Measurement Type Filter
    const typeFilters = (state.filters['measurementType'] || []) as string[];
    if (typeFilters.length > 0) {
      filtered = filtered.filter(r => typeFilters.includes(r.measurementType));
    }

    // 5. Plate ID Filter
    const plateFilters = (state.filters['plateId'] || []) as string[];
    if (plateFilters.length > 0) {
      filtered = filtered.filter(r => plateFilters.includes(r.plateId));
    }

    // 6. Sort
    filtered = [...filtered].sort((a, b) => {
      const sortBy = state.sortBy as keyof MockRun;
      let valA: any = a[sortBy];
      let valB: any = b[sortBy];

      if (valA instanceof Date) valA = valA.getTime();
      if (valB instanceof Date) valB = valB.getTime();

      if (typeof valA === 'string') valA = valA.toLowerCase();
      if (typeof valB === 'string') valB = valB.toLowerCase();

      const comparison = valA > valB ? 1 : (valA < valB ? -1 : 0);
      return state.sortOrder === 'asc' ? comparison : -comparison;
    });

    return filtered;
  });

  // Keep filteredRuns for run selection logic
  filteredRuns = computed(() => this.filteredRunsTable());

  // Computed: get selected run object
  selectedRun = computed(() => {
    return this.runs().find(r => r.id === this.selectedRunId) || null;
  });

  ngOnInit() {
    this.isLoading.set(true);
    this.initializeViewControls();
    // Load protocols first to populate filter options
    this.protocolService.getProtocols().subscribe({
      next: (protocols) => {
        this.protocols.set(protocols);
      },
      error: (e) => console.warn('Failed to load protocols', e)
    });

    // Load runs (from seeded DB or backend)
    this.protocolService.getRuns().subscribe({
      next: (runs) => {
        this.isLoading.set(false);
        if (runs && runs.length > 0) {
          // Map backend/SQLite run objects to MockRun interface for visualization
          const mappedRuns: MockRun[] = runs.map(r => {
            // Use run name; fallback to 'Unknown Protocol' (protocol_name was never a direct field)
            const name = r.name || 'Unknown Protocol';
            // Infer well count based on protocol name/type
            let wellCount = 96;
            if (name.includes('Simple') || name.includes('Transfer')) wellCount = 12;

            return {
              id: r.accession_id,
              protocolName: name,
              protocolId: (r as any).top_level_protocol_definition_accession_id || 'unknown',
              measurementType: name.includes('Plate Reader') ? 'Absorbance' : 'Transfer',
              plateId: `PLT-${Math.floor(Math.random() * 1000).toString().padStart(3, '0')}`,
              status: (r.status || 'failed').toLowerCase() as 'completed' | 'running' | 'failed',
              startTime: r.start_time ? new Date(r.start_time) : (r.created_at ? new Date(r.created_at) : new Date()),
              endTime: r.end_time ? new Date(r.end_time) : undefined,
              wellCount: wellCount,
              totalVolume: 1000 // Default for seeded runs
            };
          });

          this.runs.set(mappedRuns);

          // Auto-select first run from filtered list
          const firstFiltered = this.filteredRuns()[0];
          if (firstFiltered) {
            this.selectedRunId = firstFiltered.id;
            this.loadRunData(firstFiltered);
          }
        } else {
          // Fallback to client-side mock generation if no runs found (e.g. empty DB)
          this.generateFallbackData();
        }
      },
      error: (e) => {
        console.warn('Failed to load runs, using fallback', e);
        this.isLoading.set(false);
        this.generateFallbackData();
      }
    });

    // Simulate live data updates for running experiments
    this.updateSubscription = interval(5000).subscribe(() => {
      const run = this.selectedRun();
      if (run?.status === 'running') {
        this.addLiveDataPoint();
      }
    });
  }

  private generateFallbackData() {
    console.warn('No runs found in database. Using fallback mock data.');
    const mockRuns: MockRun[] = [
      {
        id: 'mock-run-1',
        protocolName: 'Mock Transfer Protocol',
        protocolId: 'proto-1',
        measurementType: 'Transfer',
        plateId: 'PLT-001',
        status: 'completed',
        startTime: new Date(Date.now() - 3600000),
        endTime: new Date(Date.now() - 3000000),
        wellCount: 96,
        totalVolume: 500
      }
    ];
    this.runs.set(mockRuns);
    this.selectedRunId = mockRuns[0].id;

    // Generate mock transfer logs
    const mockLogs: TransferDataPoint[] = [];
    this.selectedWells().forEach(well => {
      for (let i = 0; i < 10; i++) {
        mockLogs.push({
          timestamp: new Date(mockRuns[0].startTime.getTime() + i * 60000),
          well,
          volumeTransferred: 10 + Math.random() * 5,
          cumulativeVolume: 10 * (i + 1),
          temperature: 25,
          protocolName: mockRuns[0].protocolName,
          status: mockRuns[0].status
        });
      }
    });
    this.data.set(mockLogs);
  }

  ngOnDestroy() {
    this.updateSubscription?.unsubscribe();
  }

  initializeViewControls() {
    // Optional initialization from URL or local storage if needed
  }

  onViewStateChange(state: ViewControlsState) {
    this.viewState.set(state);

    // Auto-select first run of filtered list when filters change
    const filtered = this.filteredRuns();
    if (filtered.length > 0 && !filtered.find(r => r.id === this.selectedRunId)) {
      this.selectedRunId = filtered[0].id;
      this.loadRunData(filtered[0]);
    }
  }

  onProtocolChange() {
    // Deprecated by ViewControls, but keeping for compatibility if needed
  }

  onRunChange() {
    // Deprecated by ViewControls
  }

  selectRun(run: MockRun) {
    this.selectedRunId = run.id;
    this.loadRunData(run);
  }

  clearFilters() {
    // Handled by ViewControls component internal state
  }

  private loadRunData(run: MockRun) {
    this.protocolService.getTransferLogs(run.id).subscribe({
      next: (logs) => {
        const mappedData: TransferDataPoint[] = logs.map(l => ({
          timestamp: new Date(l.timestamp),
          well: l.well,
          volumeTransferred: l.volume_transferred,
          cumulativeVolume: l.cumulative_volume,
          temperature: l.temperature,
          pressure: l.pressure,
          protocolName: run.protocolName,
          status: run.status
        }));
        this.data.set(mappedData);
      },
      error: (err) => console.error('Failed to load transfer logs', err)
    });
  }

  private addLiveDataPoint() {
    const run = this.selectedRun();
    if (!run) return;

    // Simple pseudo-random for live data
    const newData = [...this.data()];
    const latestTime = new Date();

    this.selectedWells().slice(0, 3).forEach(well => {
      const volume = 10 + Math.random() * 20;
      const lastPoint = newData.filter(d => d.well === well).pop();
      newData.push({
        timestamp: latestTime,
        well,
        volumeTransferred: Math.round(volume * 10) / 10,
        cumulativeVolume: Math.round(((lastPoint?.cumulativeVolume || 0) + volume) * 10) / 10,
        temperature: 22 + Math.random() * 2,
        pressure: 101 + Math.random(),
        protocolName: run.protocolName,
        status: run.status
      });
    });
    this.data.set(newData);
  }

  formatDuration(start: Date, end: Date): string {
    const diffMs = end.getTime() - start.getTime();
    const minutes = Math.floor(diffMs / 60000);
    const seconds = Math.floor((diffMs % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  }

  filteredData = computed(() => {
    return this.data().filter(d => this.selectedWells().includes(d.well));
  });

  totalVolume = computed(() => {
    return this.filteredData().reduce((sum, d) => sum + d.volumeTransferred, 0);
  });

  chartTitle = computed(() => {
    const yLabels: Record<string, string> = {
      'volumeTransferred': 'Volume Transferred',
      'cumulativeVolume': 'Cumulative Volume',
      'temperature': 'Temperature',
      'pressure': 'Pressure'
    };
    const xLabels: Record<string, string> = {
      'timestamp': 'Time',
      'well': 'Well'
    };
    return `${yLabels[this.yAxis()]} over ${xLabels[this.xAxis()]}`;
  });

  chartData = computed(() => {
    const data = this.filteredData();
    const groupBy = this.groupBy();

    // Determine unique groups based on selection
    const groups = [...new Set(data.map(d => {
      if (groupBy === 'protocol') return d.protocolName || 'Unknown';
      if (groupBy === 'status') return d.status || 'Unknown';
      return d.well;
    }))];

    if (this.xAxis() === 'well') {
      // Bar chart grouped by selection
      const grouped = groups.map(group => {
        const groupData = data.filter(d => {
          if (groupBy === 'protocol') return d.protocolName === group;
          if (groupBy === 'status') return d.status === group;
          return d.well === group;
        });
        const total = groupData.reduce((sum, d) => sum + (d as Record<string, any>)[this.yAxis()], 0);
        return { group, value: total / groupData.length };
      });

      return [{
        x: grouped.map(g => g.group),
        y: grouped.map(g => g.value),
        type: 'bar',
        marker: { color: '#00e5ff' }
      }];
    }

    // Line chart over time, one trace per group
    return groups.map((group, i) => {
      const groupData = data.filter(d => {
        if (groupBy === 'protocol') return d.protocolName === group;
        if (groupBy === 'status') return d.status === group;
        return d.well === group;
      }).sort((a, b) =>
        a.timestamp.getTime() - b.timestamp.getTime()
      );
      const colors = ['#00e5ff', '#ff6b6b', '#4ecdc4', '#ffd93d', '#c3aed6', '#667eea', '#f093fb', '#a8e6cf', '#fdcb6e'];

      return {
        x: groupData.map(d => d.timestamp.toLocaleTimeString()),
        y: groupData.map(d => (d as Record<string, any>)[this.yAxis()]),
        type: 'scatter',
        mode: 'lines+markers',
        name: group,
        customdata: groupData.map(d => ({ temp: d.temperature })),
        line: { color: colors[i % colors.length] },
        marker: { color: colors[i % colors.length] }
      };
    });
  });

  chartLayout = computed(() => {
    const yLabels: Record<string, string> = {
      'volumeTransferred': 'Volume (µL)',
      'cumulativeVolume': 'Cumulative Volume (µL)',
      'temperature': 'Temperature (°C)',
      'pressure': 'Pressure (kPa)'
    };

    return {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      xaxis: {
        gridcolor: 'rgba(128,128,128,0.2)',
        tickfont: { color: 'var(--sys-on-surface)' },
        title: { text: this.xAxis() === 'timestamp' ? 'Time' : 'Well', font: { color: 'var(--sys-on-surface)' } }
      },
      yaxis: {
        gridcolor: 'rgba(128,128,128,0.2)',
        tickfont: { color: 'var(--sys-on-surface)' },
        title: { text: yLabels[this.yAxis()], font: { color: 'var(--sys-on-surface)' } }
      },
      margin: { t: 20, r: 30, l: 60, b: 50 },
      autosize: true,
      showlegend: this.selectedWells().length > 1,
      legend: {
        font: { color: 'var(--sys-on-surface)' }
      }
    };
  });

  toggleWell(well: string) {
    const current = this.selectedWells();
    if (current.includes(well)) {
      this.selectedWells.set(current.filter(w => w !== well));
    } else {
      this.selectedWells.set([...current, well]);
    }
  }

  removeWell(well: string) {
    this.selectedWells.update(wells => wells.filter(w => w !== well));
  }

  openWellSelector() {
    const dialogRef = this.dialog.open(WellSelectorDialogComponent, {
      data: {
        plateType: '96',
        initialSelection: this.selectedWells(),
        mode: 'multi',
        title: 'Select Wells for Visualization'
      },
      width: '800px',
      maxHeight: '90vh'
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.confirmed) {
        this.selectedWells.set(result.wells);
      }
    });
  }

  selectAllWells() {
    this.selectedWells.set([...this.allWells]);
  }

  clearWells() {
    this.selectedWells.set([]);
  }

  onPointClick(event: any) {
    if (event.points && event.points.length > 0) {
      const point = event.points[0];
      this.selectedPoint.set({
        x: point.x,
        y: point.y,
        well: point.fullData.name,
        temp: point.customdata?.temp
      });
    }
  }

  exportChart() {
    const blob = new Blob(['mock chart content'], { type: 'image/png' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'chart.png';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }
}
