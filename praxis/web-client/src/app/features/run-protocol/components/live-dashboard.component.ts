
import { Component, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { RouterLink } from '@angular/router';
import { ExecutionService } from '../services/execution.service';
import { ExecutionStatus } from '../models/execution.models';
import { TelemetryService } from '@core/services/telemetry.service';
import { TelemetryChartComponent } from '@shared/components/telemetry-chart/telemetry-chart.component';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-live-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatProgressBarModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    RouterLink,
    TelemetryChartComponent
  ],
  template: `
    <div class="p-6" data-testid="run-detail-view">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-3xl font-bold">Execution Monitor</h1>
        <div class="flex items-center gap-2">
          <span class="text-sm" [style.color]="executionService.isConnected() ? 'var(--theme-status-success)' : 'var(--theme-text-tertiary)'">
            <mat-icon class="text-sm">{{ executionService.isConnected() ? 'wifi' : 'wifi_off' }}</mat-icon>
            {{ executionService.isConnected() ? 'Connected' : 'Disconnected' }}
          </span>
        </div>
      </div>
    
      @if (executionService.currentRun(); as run) {
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Status Card -->
          <mat-card class="glass-panel" data-testid="run-info-card">
            <mat-card-header>
              <mat-card-title>{{ run.protocolName }}</mat-card-title>
              <mat-card-subtitle>Run ID: {{ run.runId }}</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content class="pt-4">
              <div class="flex items-center gap-2 mb-4">
                <mat-chip-set>
                  <mat-chip [highlighted]="run.status === ExecutionStatus.RUNNING"
                    data-testid="run-status"
                    [style.background-color]="run.status === ExecutionStatus.COMPLETED ? 'var(--theme-status-success-muted)' : (run.status === ExecutionStatus.FAILED ? 'var(--theme-status-error-muted)' : 'transparent')">
                    {{ run.status | uppercase }}
                  </mat-chip>
                </mat-chip-set>
              </div>
    
              <div class="mb-4">
                <p class="text-sm text-gray-600 mb-1">Progress: {{ run.progress }}%</p>
                <mat-progress-bar mode="determinate" [value]="run.progress"></mat-progress-bar>
              </div>
    
              @if (run.currentStep) {
                <p class="text-sm">
                  <span class="text-gray-500">Current Step:</span> {{ run.currentStep }}
                </p>
              }
            </mat-card-content>
            <mat-card-actions>
              <button mat-button color="warn" (click)="stopRun()"
                [disabled]="run.status !== ExecutionStatus.RUNNING && run.status !== ExecutionStatus.PAUSED">
                <mat-icon>stop</mat-icon> Stop
              </button>
              <button mat-button color="primary" (click)="pauseRun()"
                [disabled]="run.status !== ExecutionStatus.RUNNING">
                <mat-icon>pause</mat-icon> Pause
              </button>
              <button mat-button color="primary" (click)="resumeRun()"
                [disabled]="run.status !== ExecutionStatus.PAUSED">
                <mat-icon>play_arrow</mat-icon> Resume
              </button>
            </mat-card-actions>
          </mat-card>
    
          <!-- Log Output -->
          <mat-card class="glass-panel lg:col-span-2" role="region" aria-label="Execution Log">
            <mat-card-header>
              <mat-card-title>Execution Log</mat-card-title>
            </mat-card-header>
            <mat-card-content class="pt-4">
              <div style="background-color: var(--mat-sys-surface-container);" 
                   [style.color]="'var(--theme-status-success)'" 
                   class="font-mono text-sm p-4 rounded-lg h-64 overflow-y-auto"
                   data-testid="log-panel">
                @for (log of run.logs; track $index) {
                  <div class="mb-1">{{ log }}</div>
                }
                @empty {
                <div class="text-gray-500">Waiting for log output...</div>
              }
            </div>
          </mat-card-content>
        </mat-card>
      </div>
    
      <div class="mt-6">
        <mat-card class="glass-panel">
          <mat-card-header>
            <mat-card-title>Live Telemetry</mat-card-title>
          </mat-card-header>
          <mat-card-content class="pt-4">
            <app-telemetry-chart
              [xData]="telemetryX"
              [yData]="telemetryY"
              title="Temperature Over Time"
              yAxisTitle="Temperature (°C)">
            </app-telemetry-chart>
          </mat-card-content>
        </mat-card>
      </div>
    
      <!-- Actions -->
      @if (run.status === ExecutionStatus.COMPLETED || run.status === ExecutionStatus.FAILED) {
        <div class="mt-6 flex gap-2">
          <button mat-flat-button color="primary" routerLink="/run">
            <mat-icon>replay</mat-icon> Run Another
          </button>
          <button mat-stroked-button routerLink="/home">
            <mat-icon>home</mat-icon> Dashboard
          </button>
        </div>
      }
    } @else {
      <mat-card class="glass-panel text-center py-12">
        <mat-icon class="text-6xl text-gray-300 mb-4">play_disabled</mat-icon>
        <p class="text-gray-500">No active execution</p>
        <button mat-flat-button color="primary" routerLink="/run" class="mt-4">
          Start New Run
        </button>
      </mat-card>
    }
    </div>
    `
})
export class LiveDashboardComponent implements OnDestroy {
  executionService = inject(ExecutionService);
  telemetryService = inject(TelemetryService);
  ExecutionStatus = ExecutionStatus;

  telemetryX: string[] = [];
  telemetryY: number[] = [];
  private telemetrySubscription?: Subscription;

  constructor() {
    this.startTelemetry();
  }

  startTelemetry() {
    this.telemetrySubscription = this.telemetryService.getTemperatureStream().subscribe(point => {
      const timeStr = new Date(point.timestamp).toLocaleTimeString();
      this.telemetryX = [...this.telemetryX, timeStr];
      this.telemetryY = [...this.telemetryY, point.value];

      // Keep only last 30 points for performance
      if (this.telemetryX.length > 30) {
        this.telemetryX.shift();
        this.telemetryY.shift();
      }
    });
  }

  stopRun() {
    this.executionService.stopRun().subscribe();
  }

  pauseRun() {
    this.executionService.pauseRun().subscribe();
  }

  resumeRun() {
    this.executionService.resumeRun().subscribe();
  }

  ngOnDestroy() {
    this.telemetrySubscription?.unsubscribe();
    // Don't clear run on destroy - allow continued monitoring
  }
}
