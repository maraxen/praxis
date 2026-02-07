import { Component, ChangeDetectionStrategy, inject, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ExecutionService } from '../../../features/run-protocol/services/execution.service';
import { AppStore } from '../../store/app.store';
import { ExecutionStatus } from '../../../features/run-protocol/models/execution.models';
import { PythonRuntimeService } from '@core/services/python-runtime.service';

@Component({
  selector: 'app-status-bar',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatProgressBarModule, MatButtonModule],
  template: `
    <div class="status-bar" [ngClass]="{'connected': isConnected(), 'disconnected': !isConnected()}">
      <div class="status-left">
        <mat-icon [fontIcon]="isConnected() ? 'cloud_done' : 'cloud_off'"></mat-icon>
        @if (isConnected()) {
          <span>Connected</span>
        }
        @if (!isConnected()) {
          <span>Disconnected</span>
        }
        
        <!-- Python Engine Status -->
        <div class="python-status flex items-center gap-2 ml-4 pl-4 border-l border-white/20">
           @if (pythonRuntime.status() === 'loading') {
             <mat-icon class="animate-spin text-xs">sync</mat-icon>
             <span class="text-xs">Init Engine...</span>
           } @else if (pythonRuntime.status() === 'ready') {
             <mat-icon class="text-green-300 text-xs" fontIcon="check_circle"></mat-icon>
             <span class="text-xs opacity-80">Engine Ready</span>
           } @else if (pythonRuntime.status() === 'error') {
             <div class="flex items-center gap-2 bg-red-600/20 px-2 py-0.5 rounded border border-red-500/50">
               <mat-icon class="text-red-300" fontIcon="dangerous"></mat-icon>
               <span class="text-red-200 font-bold">Engine Failed</span>
               <button mat-stroked-button color="warn" class="!h-6 !px-2 !text-xs !line-height-normal" (click)="restartEngine()">
                 RESTART
               </button>
             </div>
           }
        </div>
      </div>
    
      @if (currentRun()) {
        <div class="status-center">
          @switch (currentRun()?.status) {
            @case (ExecutionStatus.RUNNING) {
              <span>
                <mat-icon fontIcon="play_arrow"></mat-icon> Protocol Running: {{ currentRun()?.protocolName }}
              </span>
            }
            @case (ExecutionStatus.PENDING) {
              <span>
                <mat-icon fontIcon="hourglass_empty"></mat-icon> Protocol Pending: {{ currentRun()?.protocolName }}
              </span>
            }
            @case (ExecutionStatus.COMPLETED) {
              <span>
                <mat-icon fontIcon="check_circle_outline"></mat-icon> Protocol Completed: {{ currentRun()?.protocolName }}
              </span>
            }
            @case (ExecutionStatus.FAILED) {
              <span>
                <mat-icon fontIcon="error_outline"></mat-icon> Protocol Failed: {{ currentRun()?.protocolName }}
              </span>
            }
            @case (ExecutionStatus.CANCELLED) {
              <span>
                <mat-icon fontIcon="cancel"></mat-icon> Protocol Cancelled: {{ currentRun()?.protocolName }}
              </span>
            }
            @default {
              <span>
                <mat-icon fontIcon="info_outline"></mat-icon> Status: {{ currentRun()?.status }}
              </span>
            }
          }
          @if (isRunning()) {
            <mat-progress-bar mode="determinate" [value]="currentRun()?.progress"></mat-progress-bar>
          }
        </div>
      }
    
      <div class="status-right">
        <!-- Add other global status indicators here -->
      </div>
    </div>
    `,
  styles: [`
    .status-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 4px 16px;
      font-size: 0.8rem;
      color: var(--mat-sys-on-primary);
      transition: background-color 0.3s ease;
      height: 32px;
      flex-shrink: 0;
    }
    .status-bar.connected {
      background-color: var(--mat-sys-primary);
    }
    .status-bar.disconnected {
      background-color: var(--mat-sys-error);
      color: var(--mat-sys-on-error);
    }
    .status-left, .status-right, .status-center {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .status-center {
      flex-grow: 1;
      justify-content: center;
    }
    mat-icon {
      font-size: 1.2em;
      height: 1.2em;
      width: 1.2em;
    }
    mat-progress-bar {
      width: 100px; /* Adjust as needed */
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatusBarComponent {
  readonly ExecutionStatus = ExecutionStatus;
  readonly executionService = inject(ExecutionService);
  readonly appStore = inject(AppStore);
  readonly pythonRuntime = inject(PythonRuntimeService);
  private snackBar = inject(MatSnackBar);

  readonly isConnected = this.executionService.isConnected;
  readonly currentRun = this.executionService.currentRun;
  readonly isLoading = this.appStore.isLoading;

  readonly isRunning = () => this.currentRun()?.status === ExecutionStatus.RUNNING;

  constructor() {
    effect(() => {
      if (this.pythonRuntime.status() === 'error') {
        const errorMsg = this.pythonRuntime.lastError() || 'Unknown error';
        this.snackBar.open(`Python Engine Critical Failure: ${errorMsg}`, 'RESTART', {
          duration: 8000,
          panelClass: ['snackbar-critical'],
          verticalPosition: 'top'
        }).onAction().subscribe(() => {
          this.restartEngine();
        });
      }
    });
  }

  restartEngine() {
    this.pythonRuntime.restartWorker();
    this.snackBar.open('Restarting Python Engine...', '', { duration: 2000 });
  }
}

