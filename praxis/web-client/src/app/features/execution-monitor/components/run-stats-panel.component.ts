import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RunHistoryService } from '../services/run-history.service';
import { RunSummary } from '../models/monitor.models';

interface RunStats {
  totalRuns: number;
  runsToday: number;
  successRate: number;
  avgDurationMs: number;
  completedRuns: number;
  failedRuns: number;
}

/**
 * Displays summary statistics for protocol runs.
 * Shows runs/day, success rate, and average duration.
 */
@Component({
  selector: 'app-run-stats-panel',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatProgressSpinnerModule],
  template: `
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      @if (isLoading()) {
        <div class="col-span-full py-12 flex items-center justify-center praxis-card">
          <mat-spinner diameter="32"></mat-spinner>
        </div>
      } @else {
        <!-- Runs Today -->
        <div class="praxis-card group cursor-default">
          <div class="card-header pb-2">
            <div class="stat-icon runs-today">
              <mat-icon>today</mat-icon>
            </div>
          </div>
          <div class="card-content">
            <span class="text-3xl font-bold text-sys-text-primary block">{{ stats().runsToday }}</span>
            <span class="card-subtitle">Runs Today</span>
          </div>
        </div>

        <!-- Total Runs -->
        <div class="praxis-card group cursor-default">
          <div class="card-header pb-2">
            <div class="stat-icon total-runs">
              <mat-icon>history</mat-icon>
            </div>
          </div>
          <div class="card-content">
            <span class="text-3xl font-bold text-sys-text-primary block">{{ stats().totalRuns }}</span>
            <span class="card-subtitle">Total Runs</span>
          </div>
        </div>

        <!-- Success Rate -->
        <div class="praxis-card group cursor-default">
          <div class="card-header pb-2">
            <div class="stat-icon success-rate" [class.warning]="stats().successRate < 80">
              <mat-icon>{{ stats().successRate >= 80 ? 'check_circle' : 'warning' }}</mat-icon>
            </div>
            <div class="ml-auto text-xs font-medium text-sys-text-tertiary">
              {{ stats().completedRuns }} / {{ stats().completedRuns + stats().failedRuns }}
            </div>
          </div>
          <div class="card-content">
            <span class="text-3xl font-bold text-sys-text-primary block">{{ stats().successRate | number:'1.0-0' }}%</span>
            <span class="card-subtitle">Success Rate</span>
          </div>
        </div>

        <!-- Average Duration -->
        <div class="praxis-card group cursor-default">
          <div class="card-header pb-2">
            <div class="stat-icon avg-duration">
              <mat-icon>timer</mat-icon>
            </div>
          </div>
          <div class="card-content">
            <span class="text-3xl font-bold text-sys-text-primary block truncate">{{ formatDuration(stats().avgDurationMs) }}</span>
            <span class="card-subtitle">Avg Duration</span>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .stat-icon {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;

      mat-icon {
        width: 24px;
        height: 24px;
        font-size: 24px;
      }

      &.runs-today {
        background: var(--mat-sys-tertiary-container);
        mat-icon { color: var(--tertiary-color); }
      }

      &.total-runs {
        background: var(--mat-sys-primary-container);
        mat-icon { color: var(--primary-color); }
      }

      &.success-rate {
        background: var(--mat-sys-success-container);
        mat-icon { color: var(--mat-sys-success); }

        &.warning {
          background: var(--mat-sys-warning-container);
          mat-icon { color: var(--mat-sys-warning); }
        }
      }

      &.avg-duration {
        background: var(--mat-sys-tertiary-container);
        mat-icon { color: var(--tertiary-color); }
      }
    }
  `]
})
export class RunStatsPanelComponent implements OnInit {
  private readonly runHistoryService = inject(RunHistoryService);

  readonly isLoading = signal(true);
  readonly stats = signal<RunStats>({
    totalRuns: 0,
    runsToday: 0,
    successRate: 0,
    avgDurationMs: 0,
    completedRuns: 0,
    failedRuns: 0
  });

  ngOnInit(): void {
    this.loadStats();
  }

  private loadStats(): void {
    // Fetch a larger set of runs to calculate statistics
    this.runHistoryService.getRunHistory({ limit: 100 }).subscribe({
      next: (runs) => {
        this.calculateStats(runs);
        this.isLoading.set(false);
      },
      error: () => {
        this.isLoading.set(false);
      }
    });
  }

  private calculateStats(runs: RunSummary[]): void {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const runsToday = runs.filter(r => {
      const runDate = new Date(r.created_at);
      return runDate >= today;
    }).length;

    const completedRuns = runs.filter(r => r.status === 'completed').length;
    const failedRuns = runs.filter(r => r.status === 'failed').length;
    const finishedRuns = completedRuns + failedRuns;

    const successRate = finishedRuns > 0
      ? (completedRuns / finishedRuns) * 100
      : 100;

    const runsWithDuration = runs.filter(r => r.duration_ms && r.duration_ms > 0);
    const avgDurationMs = runsWithDuration.length > 0
      ? runsWithDuration.reduce((sum, r) => sum + (r.duration_ms || 0), 0) / runsWithDuration.length
      : 0;

    this.stats.set({
      totalRuns: runs.length,
      runsToday,
      successRate,
      avgDurationMs,
      completedRuns,
      failedRuns
    });
  }

  formatDuration(ms: number): string {
    if (!ms || ms === 0) return '-';
    return this.runHistoryService.formatDuration(ms);
  }
}
