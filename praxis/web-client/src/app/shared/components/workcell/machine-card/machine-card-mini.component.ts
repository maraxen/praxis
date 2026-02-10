import { Component, ChangeDetectionStrategy, output, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MachineWithRuntime } from '@features/workcell/models/workcell-view.models';
import { MachineStatusBadgeComponent } from '../machine-status-badge/machine-status-badge.component';

@Component({
  selector: 'app-machine-card-mini',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatProgressBarModule,
    MachineStatusBadgeComponent
  ],
  template: `
    <div class="machine-mini-card" 
         [class.running]="machine.status === 'running'"
         [class.error]="machine.status === 'error'"
         (click)="machineSelected.emit(machine)">
      
      <div class="main-info">
        <mat-icon class="machine-icon">precision_manufacturing</mat-icon>
        <div class="name-container">
          <h4 class="machine-name">{{ machine.name }}</h4>
          <span class="machine-type">{{ machine.machine_type }}</span>
        </div>
      </div>

      <div class="status-container">
        <app-machine-status-badge 
          [status]="machine.status" 
          [stateSource]="machine.stateSource"
          [showLabel]="false">
        </app-machine-status-badge>
      </div>

      <div class="protocol-container">
        @if (machine.currentRun; as run) {
          <div class="progress-info">
            <span class="protocol-name truncate">{{ run.protocolName }}</span>
            <div class="progress-bar-wrapper">
               <mat-progress-bar mode="determinate" [value]="run.progress"></mat-progress-bar>
               <span class="progress-text">{{ run.progress }}%</span>
            </div>
          </div>
        } @else {
          <span class="idle-text">Idle</span>
        }
      </div>

      <div class="alerts-container">
        @if (machine.alerts.length > 0) {
          <div class="alert-indicator" [class]="machine.alerts[0].severity">
            <mat-icon>{{ machine.alerts[0].severity === 'error' ? 'error' : 'warning' }}</mat-icon>
            <span class="alert-count">{{ machine.alerts.length }}</span>
          </div>
        }
      </div>

      <div class="actions-container" (click)="$event.stopPropagation()">
        <button mat-icon-button [matMenuTriggerFor]="menu">
          <mat-icon>more_vert</mat-icon>
        </button>
        <mat-menu #menu="matMenu">
          <button mat-menu-item (click)="machineSelected.emit(machine)">
            <mat-icon>visibility</mat-icon>
            <span>View Details</span>
          </button>
          @if (machine.status === 'running') {
            <button mat-menu-item color="warn">
              <mat-icon>pause_circle</mat-icon>
              <span>Pause</span>
            </button>
          }
        </mat-menu>
      </div>
    </div>
  `,
  styles: [`
    .machine-mini-card {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 12px 16px;
      background: var(--mat-sys-surface-container-low);
      border: 1px solid var(--mat-sys-outline-variant);
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s ease;

      &:hover {
        background: var(--mat-sys-surface-container);
        border-color: var(--mat-sys-primary);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
      }

      &.running {
        border-left: 4px solid var(--theme-status-warning-border, var(--mat-sys-tertiary));
      }

      &.error {
        border-color: var(--mat-sys-error);
      }
    }

    .main-info {
      display: flex;
      align-items: center;
      gap: 12px;
      width: 250px;
      flex-shrink: 0;

      .machine-icon {
        color: var(--mat-sys-primary);
        font-size: 20px;
        width: 20px;
        height: 20px;
      }

      .name-container {
        display: flex;
        flex-direction: column;
        overflow: hidden;

        .machine-name {
          margin: 0;
          font-size: 14px;
          font-weight: 500;
          color: var(--mat-sys-on-surface);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .machine-type {
          font-size: 11px;
          color: var(--mat-sys-on-surface-variant);
        }
      }
    }

    .status-container {
      width: 40px;
      display: flex;
      justify-content: center;
    }

    .protocol-container {
      flex-grow: 1;
      min-width: 200px;
      
      .idle-text {
        font-size: 13px;
        color: var(--mat-sys-on-surface-variant);
        font-style: italic;
      }

      .progress-info {
        display: flex;
        flex-direction: column;
        gap: 4px;

        .protocol-name {
          font-size: 12px;
          font-weight: 500;
          color: var(--mat-sys-on-surface);
        }

        .progress-bar-wrapper {
          display: flex;
          align-items: center;
          gap: 8px;

          mat-progress-bar {
            height: 4px;
            border-radius: 2px;
          }

          .progress-text {
            font-size: 10px;
            color: var(--mat-sys-on-surface-variant);
            width: 30px;
          }
        }
      }
    }

    .alerts-container {
      width: 60px;
      display: flex;
      justify-content: center;

      .alert-indicator {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 2px 6px;
        border-radius: 4px;

        mat-icon { font-size: 16px; width: 16px; height: 16px; }
        .alert-count { font-size: 11px; font-weight: 600; }

        &.warning {
          color: #854d0e;
          background: rgba(250, 204, 21, 0.1);
        }
        &.error {
          color: #991b1b;
          background: rgba(239, 68, 68, 0.1);
        }
      }
    }

    .actions-container {
      flex-shrink: 0;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MachineCardMiniComponent {
  @Input({ required: true }) machine!: MachineWithRuntime;
  machineSelected = output<MachineWithRuntime>();
}
