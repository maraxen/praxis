import { Component, ChangeDetectionStrategy, output, computed, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MachineWithRuntime } from '@features/workcell/models/workcell-view.models';
import { MachineStatusBadgeComponent } from '../machine-status-badge/machine-status-badge.component';
import { DeckViewComponent } from '../../deck-view/deck-view.component';
import { PlrResource, PlrState } from '@core/models/plr.models';

@Component({
  selector: 'app-machine-card',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatProgressBarModule,
    MachineStatusBadgeComponent,
    DeckViewComponent
  ],
  template: `
    <div class="machine-card" 
         [class.running]="machine.status === 'running'"
         [class.error]="machine.status === 'error'"
         (click)="onCardClick()">
      
      <!-- Header -->
      <header class="card-header">
        <div class="machine-info">
          <mat-icon class="machine-icon">precision_manufacturing</mat-icon>
          <div class="name-container">
            <h3 class="machine-name">{{ machine.name }}</h3>
            <span class="machine-type">{{ machine.machine_type }}</span>
          </div>
        </div>
        <app-machine-status-badge 
          [status]="machine.status" 
          [stateSource]="machine.stateSource"
          [compact]="true">
        </app-machine-status-badge>
      </header>

      <!-- Content -->
      <div class="card-content">
        <!-- Mini Deck View -->
        <div class="deck-preview">
          @if (deckResource()) {
            <div class="deck-scale-wrapper">
              <app-deck-view 
                [resource]="deckResource()" 
                [state]="deckState()">
              </app-deck-view>
            </div>
          } @else {
            <div class="deck-placeholder">
              <mat-icon>grid_view</mat-icon>
              <span>No Deck Preview</span>
            </div>
          }
        </div>

        <!-- Protocol Progress -->
        @if (machine.currentRun; as run) {
          <div class="progress-section">
            <div class="progress-info">
              <span class="protocol-name">{{ run.protocolName }}</span>
              <span class="step-info">Step {{ run.currentStep }}/{{ run.totalSteps }}</span>
            </div>
            <mat-progress-bar mode="determinate" [value]="run.progress"></mat-progress-bar>
            @if (run.estimatedRemaining) {
              <span class="time-remaining">
                <mat-icon>timer</mat-icon>
                ~{{ run.estimatedRemaining }}m remaining
              </span>
            }
          </div>
        }

        <!-- Alerts -->
        @if (machine.alerts.length > 0) {
          <div class="alerts-section">
            @for (alert of machine.alerts; track alert.message) {
              <div class="alert-item" [class]="alert.severity">
                <mat-icon>{{ alert.severity === 'error' ? 'error' : 'warning' }}</mat-icon>
                <span>{{ alert.message }}</span>
              </div>
            }
          </div>
        }
      </div>

      <!-- Footer -->
      <footer class="card-footer" (click)="$event.stopPropagation()">
        <button mat-button color="primary" (click)="onFocus()">
          <mat-icon>fullscreen</mat-icon>
          Focus View
        </button>
        <button mat-icon-button [matMenuTriggerFor]="menu">
          <mat-icon>more_vert</mat-icon>
        </button>
        <mat-menu #menu="matMenu">
          <button mat-menu-item (click)="onFocus()">
            <mat-icon>visibility</mat-icon>
            <span>View Details</span>
          </button>
          @if (machine.status === 'running') {
            <button mat-menu-item color="warn">
              <mat-icon>pause_circle</mat-icon>
              <span>Pause Protocol</span>
            </button>
          }
          <button mat-menu-item>
            <mat-icon>settings</mat-icon>
            <span>Configure</span>
          </button>
        </mat-menu>
      </footer>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .machine-card {
      background: var(--mat-sys-surface-container-low);
      border: 1px solid var(--mat-sys-outline-variant);
      border-radius: 12px;
      overflow: hidden;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: pointer;
      display: flex;
      flex-direction: column;
      height: 100%;

      &:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
        border-color: var(--mat-sys-primary);
      }

      &.running {
        border-bottom: 3px solid var(--theme-status-warning-border, var(--mat-sys-tertiary));
      }

      &.error {
        border-color: var(--mat-sys-error);
      }
    }

    .card-header {
      padding: 16px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 1px solid var(--mat-sys-outline-variant);

      .machine-info {
        display: flex;
        gap: 12px;
        align-items: center;

        .machine-icon {
          color: var(--mat-sys-primary);
          background: var(--mat-sys-primary-container);
          padding: 8px;
          border-radius: 8px;
          width: 24px;
          height: 24px;
          font-size: 24px;
        }

        .name-container {
          display: flex;
          flex-direction: column;

          .machine-name {
            margin: 0;
            font-size: 16px;
            font-weight: 600;
            color: var(--mat-sys-on-surface);
            line-height: 1.2;
          }

          .machine-type {
            font-size: 12px;
            color: var(--mat-sys-on-surface-variant);
          }
        }
      }
    }

    .card-content {
      padding: 16px;
      flex-grow: 1;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .deck-preview {
      height: 140px;
      background: var(--mat-sys-surface-container-low);
      border-radius: 8px;
      overflow: hidden;
      position: relative;
      border: 1px solid rgba(255, 255, 255, 0.05);

      .deck-scale-wrapper {
        transform: scale(0.35);
        transform-origin: top left;
        padding: 10px;
      }

      .deck-placeholder {
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: rgba(255, 255, 255, 0.3);
        gap: 8px;

        mat-icon { font-size: 32px; width: 32px; height: 32px; }
        span { font-size: 12px; }
      }
    }

    .progress-section {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .progress-info {
        display: flex;
        justify-content: space-between;
        font-size: 12px;

        .protocol-name {
          font-weight: 500;
          color: var(--mat-sys-on-surface);
        }
        .step-info {
          color: var(--mat-sys-on-surface-variant);
        }
      }

      .time-remaining {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
        color: var(--mat-sys-tertiary);
        margin-top: 4px;

        mat-icon { font-size: 14px; width: 14px; height: 14px; }
      }
    }

    .alerts-section {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .alert-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;

        &.warning {
          background: rgba(250, 204, 21, 0.1);
          color: #854d0e;
          mat-icon { color: #eab308; }
        }

        &.error {
          background: rgba(239, 68, 68, 0.1);
          color: #991b1b;
          mat-icon { color: #ef4444; }
        }

        mat-icon { font-size: 16px; width: 16px; height: 16px; }
      }
    }

    .card-footer {
      padding: 8px 16px;
      background: var(--mat-sys-surface-container);
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-top: 1px solid var(--mat-sys-outline-variant);

      button[mat-button] {
        font-weight: 500;
        font-size: 13px;
        mat-icon { margin-right: 4px; }
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MachineCardComponent {
  @Input({ required: true }) machine!: MachineWithRuntime;
  machineSelected = output<MachineWithRuntime>();

  deckResource = computed(() => this.machine.plr_definition as unknown as PlrResource);
  deckState = computed(() => this.machine.plr_state as unknown as PlrState);

  onCardClick() {
    this.machineSelected.emit(this.machine);
  }

  onFocus() {
    this.machineSelected.emit(this.machine);
    // In a real implementation, this might navigate or trigger a view mode change
  }
}
