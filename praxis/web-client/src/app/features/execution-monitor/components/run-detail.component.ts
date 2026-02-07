import { Component, inject, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { Location } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatTabsModule } from '@angular/material/tabs';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { NgxSkeletonLoaderModule } from 'ngx-skeleton-loader';
import { Subject, takeUntil } from 'rxjs';

import { RunHistoryService } from '../services/run-history.service';
import { RunDetail } from '../models/monitor.models';
import { SimulationResultsService } from '@core/services/simulation-results.service';
import { StateHistory } from '@core/models/simulation.models';
import { StateInspectorComponent } from './state-inspector';
import { StateHistoryTimelineComponent } from './state-history-timeline';
import { StateDeltaComponent } from './state-delta/state-delta.component';
import { ParameterViewerComponent } from './parameter-viewer';
import { DeckViewComponent } from '@shared/components/deck-view/deck-view.component';
import { ExecutionService } from '@features/run-protocol/services/execution.service';

/**
 * Displays detailed information about a single protocol run.
 */
@Component({
  selector: 'app-run-detail',
  standalone: true,
  imports: [
    RouterLink,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatDividerModule,
    MatTabsModule,
    MatSnackBarModule,
    NgxSkeletonLoaderModule,
    StateInspectorComponent,
    StateHistoryTimelineComponent,
    StateDeltaComponent,
    ParameterViewerComponent,
    DeckViewComponent
  ],
  template: `
    <div class="p-6 max-w-screen-xl mx-auto" data-testid="run-detail-view">
      <!-- Header -->
      <div class="flex items-center gap-4 mb-6">
        <button mat-icon-button (click)="goBack()" aria-label="Go back">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <div class="flex-1">
          <h1 class="text-2xl font-bold text-sys-text-primary">
            @if (run()) {
              {{ run()?.protocol_name || run()?.name || 'Run Details' }}
            } @else {
              Run Details
            }
          </h1>
          <p class="text-sys-text-secondary">{{ runId() }}</p>
        </div>
      </div>

      @if (isLoading()) {
        <div class="flex justify-center py-12">
           <div class="w-full max-w-3xl space-y-4">
              <ngx-skeleton-loader count="1" appearance="line" [theme]="{ height: '100px', 'border-radius': '12px' }"></ngx-skeleton-loader>
              <div class="grid grid-cols-3 gap-4">
                 <ngx-skeleton-loader count="1" appearance="line" [theme]="{ height: '300px', 'border-radius': '12px' }" class="col-span-2"></ngx-skeleton-loader>
                 <ngx-skeleton-loader count="1" appearance="line" [theme]="{ height: '300px', 'border-radius': '12px' }" class="col-span-1"></ngx-skeleton-loader>
              </div>
           </div>
        </div>
      } @else if (!run()) {
        <div class="empty-state text-center py-12 text-sys-text-tertiary">
          <mat-icon class="!w-16 !h-16 !text-[64px] opacity-30 mb-4">error_outline</mat-icon>
          <p class="text-lg">Run not found</p>
          <a mat-button routerLink="/app/monitor" class="mt-4">
            <mat-icon>arrow_back</mat-icon>
            Back to Monitor
          </a>
        </div>
      } @else {
        <!-- Timeline -->
        <div class="timeline-container relative flex items-center justify-between mb-8 px-8 max-w-3xl mx-auto">
          <!-- Progress Bar Background -->
          <div class="absolute left-8 right-8 top-1/2 h-1 bg-[var(--mat-sys-surface-variant)] -z-10 translate-y-[-50%]"></div>
          <!-- Steps -->
          @for (step of timelineSteps(); track step.label) {
             <div class="flex flex-col items-center gap-2 bg-surface px-4 z-10">
                <div class="w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors duration-300"
                     [class.border-primary]="step.state === 'completed' || step.state === 'active'"
                     [class.bg-primary]="step.state === 'completed'"
                     [class.text-[var(--mat-sys-on-primary)]]="step.state === 'completed'"
                     [class.border-error]="step.state === 'error'"
                     [class.text-error]="step.state === 'error'"
                     [class.border-outline-variant]="step.state === 'pending'">
                   @if (step.state === 'completed') { <mat-icon class="!w-5 !h-5 !text-[20px]">check</mat-icon> }
                   @else if (step.state === 'error') { <mat-icon class="!w-5 !h-5 !text-[20px]">error</mat-icon> }
                   @else { <span class="text-xs font-bold">{{ step.index }}</span> }
                </div>
                <span class="text-xs font-medium" [class.text-primary]="step.state === 'active'" [class.opacity-60]="step.state === 'pending'">{{ step.label }}</span>
             </div>
          }
        </div>

        <!-- Tabs for Overview and State Inspector -->
        <mat-tab-group class="run-tabs" animationDuration="200ms">
          <mat-tab label="Overview">

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Main Info Card -->
          <mat-card class="lg:col-span-2 detail-card">
            <mat-card-header>
              <mat-card-title>Run Information</mat-card-title>
            </mat-card-header>
            <mat-card-content class="pt-4">
              <!-- Status -->
              <div class="info-row">
                <span class="info-label">Status</span>
                <div class="flex items-center gap-2">
                  <mat-icon [class]="runHistoryService.getStatusColor(run()!.status)" class="!w-5 !h-5 !text-[20px]">
                    {{ runHistoryService.getStatusIcon(run()!.status) }}
                  </mat-icon>
                  <span class="font-semibold" data-testid="run-status">{{ run()!.status }}</span>
                </div>
              </div>
              <mat-divider></mat-divider>

              <!-- Times -->
              <div class="info-row">
                <span class="info-label">Created</span>
                <span>{{ formatDateTime(run()!.created_at) }}</span>
              </div>
              @if (run()!.start_time) {
                <div class="info-row">
                  <span class="info-label">Started</span>
                  <span>{{ formatDateTime(run()!.start_time) }}</span>
                </div>
              }
              @if (run()!.end_time) {
                <div class="info-row">
                  <span class="info-label">Completed</span>
                  <span>{{ formatDateTime(run()!.end_time) }}</span>
                </div>
              }
              @if (run()!.duration_ms) {
                <div class="info-row">
                  <span class="info-label">Duration</span>
                  <span>{{ runHistoryService.formatDuration(run()!.duration_ms) }}</span>
                </div>
              }
              <mat-divider></mat-divider>

              <!-- Parameters -->
              @if (run()!.input_parameters_json && hasKeys(run()!.input_parameters_json)) {
                <div class="mt-4">
                  <h3 class="font-semibold text-sys-text-primary mb-2">Input Parameters</h3>
                  <app-parameter-viewer [parameters]="run()!.input_parameters_json" data-testid="parameter-viewer" />
                </div>
              }
            </mat-card-content>
          </mat-card>

          <!-- Sidebar -->
          <div class="space-y-4">
            <!-- Actions Card -->
            <mat-card class="detail-card">
              <mat-card-header>
                <mat-card-title>Actions</mat-card-title>
              </mat-card-header>
              <mat-card-content class="pt-4 space-y-2">
                @if (run()?.status === 'running' || run()?.status === 'paused') {
                  <div class="run-controls">
                    <button mat-raised-button color="warn" (click)="cancelRun()" [disabled]="isCancelling()" data-testid="cancel-button">
                      <mat-icon>stop</mat-icon> Cancel
                    </button>
                    <button mat-raised-button (click)="togglePause()" [disabled]="isToggling()" data-testid="pause-button">
                      <mat-icon>{{ run()?.status === 'paused' ? 'play_arrow' : 'pause' }}</mat-icon>
                      {{ run()?.status === 'paused' ? 'Resume' : 'Pause' }}
                    </button>
                  </div>
                }
                <button mat-stroked-button class="w-full" disabled>
                  <mat-icon>replay</mat-icon>
                  Re-run Protocol
                </button>
                <button mat-stroked-button class="w-full" disabled>
                  <mat-icon>download</mat-icon>
                  Export Logs
                </button>
              </mat-card-content>
            </mat-card>

            <!-- Output Data Card-->
            @if (run()!.output_data_json && hasKeys(run()!.output_data_json)) {
              <mat-card class="detail-card">
                <mat-card-header>
                  <mat-card-title>Output Data</mat-card-title>
                </mat-card-header>
                <mat-card-content class="pt-4">
                  <app-parameter-viewer [parameters]="run()!.output_data_json" />
                </mat-card-content>
              </mat-card>
            }
          </div>
        </div>

        <!-- Operation Timeline -->
        <div class="mt-8">
          <h3 class="text-lg font-bold mb-4 text-sys-text-primary">Operation Timeline</h3>
          @if (stateHistory()?.operations; as operations) {
            <mat-card class="detail-card">
              <mat-card-content class="p-0">
                <div class="operation-list">
                  @for (operation of operations; track operation.operation_index) {
                    <div class="operation-item p-4 border-b border-sys-outline-variant last:border-0 hover:bg-sys-surface-container-high transition-colors">
                      <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-3">
                          <span class="font-mono text-sm font-semibold text-sys-primary">{{ operation.operation_index + 1 }}.</span>
                          <span class="font-mono text-sm font-bold text-sys-on-surface">{{ operation.method_name }}</span>
                          @if (operation.resource) {
                            <span class="text-xs px-2 py-0.5 rounded-full bg-sys-surface-variant text-sys-on-surface-variant">{{ operation.resource }}</span>
                          }
                        </div>
                        <div class="flex items-center gap-2">
                           @if (operation.duration_ms) {
                             <span class="text-xs font-mono text-sys-on-surface-variant">{{ (operation.duration_ms / 1000).toFixed(1) }}s</span>
                           }
                           <mat-icon [class]="operation.status === 'failed' ? 'text-sys-error' : 'text-sys-success'" class="!w-5 !h-5 !text-[20px]">
                             {{ operation.status === 'failed' ? 'error' : 'check_circle' }}
                           </mat-icon>
                        </div>
                      </div>
                      
                      @if (operation.error_message) {
                        <div class="mb-2 text-xs text-sys-error bg-sys-error-container p-2 rounded">
                          {{ operation.error_message }}
                        </div>
                      }

                      <!-- State Deltas -->
                      @if (operation.state_delta && hasKeys(operation.state_delta)) {
                        <app-state-delta [deltas]="formatDeltas(operation.state_delta)" />
                      }
                    </div>
                  }
                  @if (operations.length === 0) {
                    <div class="p-8 text-center text-sys-text-tertiary">
                      No operations recorded.
                    </div>
                  }
                </div>
              </mat-card-content>
            </mat-card>
          } @else {
             <!-- Loading or empty state for history -->
             @if (isLoadingStateHistory()) {
                <div class="flex justify-center p-8">
                  <mat-spinner diameter="32"></mat-spinner>
                </div>
             }
          }
        </div>

        <!-- Logs Section -->
        @if (run()!.logs && run()!.logs!.length > 0) {
          <mat-card class="detail-card mt-6">
            <mat-card-header>
              <mat-card-title>Execution Logs</mat-card-title>
            </mat-card-header>
            <mat-card-content class="pt-4">
              <div class="bg-[#1e1e1e] text-green-400 p-4 rounded-lg font-mono text-sm max-h-96 overflow-y-auto" data-testid="log-panel">
                @for (log of run()!.logs; track $index) {
                  <div class="log-line">{{ log }}</div>
                }
              </div>
            </mat-card-content>
          </mat-card>
        }
          </mat-tab>
          
          <!-- State Inspector Tab -->
          <mat-tab label="State Inspector">
            <div class="tab-content p-4">
              @if (isLoadingStateHistory()) {
                <div class="flex justify-center py-12">
                  <mat-spinner diameter="32"></mat-spinner>
                </div>
              } @else if (!stateHistory()) {
                <div class="empty-state text-center py-12 text-sys-text-tertiary">
                  <mat-icon class="!w-12 !h-12 !text-[48px] opacity-30 mb-4">hourglass_empty</mat-icon>
                  <p>No state history available for this run.</p>
                  <p class="text-sm">State history is recorded during protocol execution.</p>
                </div>
              } @else {
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div class="lg:col-span-2">
                    <app-state-inspector 
                      [stateHistory]="stateHistory()"
                      [initialOperationIndex]="currentOperationIndex()"
                      (operationSelected)="onOperationSelected($event)">
                    </app-state-inspector>
                  </div>
                  <div>
                    <app-state-history-timeline
                      [stateHistory]="stateHistory()"
                      [currentIndex]="currentOperationIndex()"
                      (operationSelected)="onOperationSelected($event)">
                    </app-state-history-timeline>
                  </div>
                </div>
              }
            </div>
          </mat-tab>

          <!-- Live View Tab -->
          <mat-tab label="Live View">
            <div class="tab-content flex flex-col items-center justify-center min-h-[500px] p-6 bg-[var(--plr-bg)] rounded-b-xl border-x border-b border-[var(--theme-border)]">
              @if (isLive()) {
                @if (executionService.currentRun(); as runState) {
                  @if (runState.plr_definition) {
                    <app-deck-view
                      data-testid="deck-view"
                      [resource]="runState.plr_definition"
                      [state]="runState.wellState || {}">
                    </app-deck-view>
                  } @else {
                    <div class="empty-state text-center py-12 text-sys-text-tertiary">
                      <mat-icon class="!w-12 !h-12 !text-[48px] opacity-30 mb-4">view_quilt</mat-icon>
                      <p>Deck layout not available for this run</p>
                    </div>
                  }
                }
              } @else {
                <div class="empty-state text-center py-12 text-sys-text-tertiary">
                  <mat-icon class="!w-12 !h-12 !text-[48px] opacity-30 mb-4">history</mat-icon>
                  <p>Live view only available for active runs.</p>
                  <p class="text-sm">This run is currently in terminal state: {{ run()?.status }}</p>
                </div>
              }
            </div>
          </mat-tab>
        </mat-tab-group>
      }
    </div>
  `,
  styles: [`
    .detail-card {
      background: var(--mat-sys-surface-container-low);
      border: 1px solid var(--mat-sys-outline-variant);
    }
    .info-row {
      display: flex;
      justify-content: space-between;
      padding: 12px 0;
    }
    .info-label {
      color: var(--mat-sys-on-surface-variant);
      font-weight: 500;
    }
    .log-line {
      padding: 2px 0;
      white-space: pre-wrap;
      word-break: break-all;
    }
    pre {
      margin: 0;
      font-family: 'Fira Code', 'Monaco', monospace;
    }
    .run-tabs {
      margin-top: 24px;
    }
    .tab-content {
      min-height: 400px;
    }
  `],
})
export class RunDetailComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly location = inject(Location);
  private readonly simulationService = inject(SimulationResultsService);
  readonly runHistoryService = inject(RunHistoryService);

  readonly run = signal<RunDetail | null>(null);
  readonly isLoading = signal(true);
  readonly stateHistory = signal<StateHistory | null>(null);
  readonly isLoadingStateHistory = signal(false);
  readonly currentOperationIndex = signal(0);

  readonly executionService = inject(ExecutionService);
  private readonly snackBar = inject(MatSnackBar);

  isCancelling = signal(false);
  isToggling = signal(false);
  private destroy$ = new Subject<void>();

  readonly isLive = computed(() => {
    const r = this.run();
    return r && ['running', 'paused', 'preparing'].includes(r.status);
  });
  readonly timelineSteps = computed(() => {
    const run = this.run();
    if (!run) return [];

    const status = run.status;

    let setupState: 'pending' | 'active' | 'completed' | 'error' = 'pending';
    let runningState: 'pending' | 'active' | 'completed' | 'error' = 'pending';
    let completeState: 'pending' | 'active' | 'completed' | 'error' = 'pending';

    // Setup Phase
    if (['queued', 'preparing', 'pending'].includes(status)) {
      setupState = 'active';
    } else {
      // If we are past setup, it's completed.
      setupState = 'completed';
    }

    // Running Phase
    if (status === 'running' || status === 'paused') {
      runningState = 'active';
    } else if (['completed', 'failed', 'cancelled'].includes(status)) {
      runningState = 'completed';
    }

    // Complete Phase
    if (status === 'completed') {
      completeState = 'completed';
    } else if (status === 'failed' || status === 'cancelled') {
      completeState = 'error';
    }

    return [
      { label: 'Setup', index: 1, state: setupState },
      { label: 'Running', index: 2, state: runningState },
      { label: 'Complete', index: 3, state: completeState }
    ];
  });

  runId = signal(''); // Changed runId to a signal

  ngOnInit(): void {
    const runId = this.route.snapshot.paramMap.get('id');
    if (runId) {
      this.runId.set(runId);
      this.loadRunDetail();
      this.loadStateHistory(); // Kept loadStateHistory
      this.executionService.connectWebSocket(runId);

      // Subscribe to real-time errors
      this.executionService.errors$
        .pipe(takeUntil(this.destroy$))
        .subscribe(err => {
          this.snackBar.open(`Connection Error: ${err.message}`, 'Retry', {
            duration: 5000,
            panelClass: ['snackbar-error']
          }).onAction().subscribe(() => {
            window.location.reload();
          });
        });
    } else {
      this.isLoading.set(false);
    }
  }

  ngOnDestroy(): void {
    this.executionService.disconnect();
    this.destroy$.next(); // Added destroy$.next()
    this.destroy$.complete(); // Added destroy$.complete()
  }

  loadRunDetail(): void {
    this.isLoading.set(true);
    this.runHistoryService.getRunDetail(this.runId()).subscribe({ // Updated to use runId()
      next: (detail) => {
        this.run.set(detail);
        this.isLoading.set(false);
        if (this.isLive()) {
          this.executionService.connectWebSocket(this.runId());
        }
      },
      error: (err) => {
        console.error('[RunDetail] Error loading run:', err);
        this.isLoading.set(false);
      },
    });
  }

  goBack(): void {
    this.location.back();
  }

  formatDateTime(isoDate?: string): string {
    if (!isoDate) return '-';
    try {
      return new Date(isoDate).toLocaleString();
    } catch {
      return isoDate;
    }
  }

  formatJson(obj?: Record<string, unknown>): string {
    if (!obj) return '';
    return JSON.stringify(obj, null, 2);
  }

  hasKeys(obj?: Record<string, unknown>): boolean {
    return !!obj && Object.keys(obj).length > 0;
  }

  formatDeltas(stateDelta: Record<string, number | string>): Array<{ key: string, before: number | string, after: number | string, change: number | string }> {
    return Object.entries(stateDelta).map(([key, change]) => ({
      key,
      before: '-', // State before not readily available in simple delta view without lookup
      after: '-',  // State after not readily available
      change
    }));
  }

  loadStateHistory(): void {
    this.isLoadingStateHistory.set(true);
    this.simulationService.getStateHistory(this.runId()).subscribe({
      next: (history) => {
        this.stateHistory.set(history);
        this.isLoadingStateHistory.set(false);
      },
      error: (err) => {
        console.error('[RunDetail] Error loading state history:', err);
        this.isLoadingStateHistory.set(false);
      },
    });
  }

  onOperationSelected(index: number): void {
    this.currentOperationIndex.set(index);
  }

  cancelRun() {
    this.isCancelling.set(true);
    this.executionService.cancel(this.runId()).subscribe({
      next: () => {
        this.snackBar.open('Run cancelled', 'Close', { duration: 3000 });
        this.loadRunDetail();
      },
      error: (err: Error) => this.snackBar.open('Failed to cancel: ' + err.message, 'Close'),
      complete: () => this.isCancelling.set(false)
    });
  }

  togglePause() {
    this.isToggling.set(true);
    const action = this.run()?.status === 'paused' ? 'resume' : 'pause';
    this.executionService[action](this.runId()).subscribe({
      next: () => {
        this.loadRunDetail();
      },
      error: (err: Error) => this.snackBar.open('Failed to ' + action + ': ' + err.message, 'Close'),
      complete: () => this.isToggling.set(false)
    });
  }
}
