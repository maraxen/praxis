import { Component, ChangeDetectionStrategy, Input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MachineStatus } from '@features/assets/models/asset.models';

/**
 * A reusable status indicator component for machine state display.
 * Displays a color-coded dot and an optional label.
 */
@Component({
  selector: 'app-machine-status-badge',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div 
      class="status-badge" 
      [class]="badgeClasses()"
      [title]="statusLabel()">
      <span class="status-dot" [class.pulse]="status === 'running'"></span>
      @if (showLabel) {
        <span class="status-label">{{ statusLabel() }}</span>
      }
      @if (stateSource !== 'live') {
        <span class="source-tag" [class]="stateSource">{{ stateSource | uppercase }}</span>
      }
    </div>
  `,
  styles: [`
    :host {
      display: inline-block;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 500;
      white-space: nowrap;
      transition: all 0.2s ease;
      background: var(--mat-sys-surface-variant);
      color: var(--theme-text-primary);
      border: 1px solid var(--theme-border-light);

      &.compact {
        padding: 2px 4px;
        gap: 0;
        .status-label { display: none; }
      }

      /* Status Colors */
      &.idle { 
        border-color: var(--theme-status-success-border); 
        .status-dot { background: var(--mat-sys-success); }
      }
      &.running { 
        border-color: var(--theme-status-warning-border); 
        .status-dot { background: var(--mat-sys-tertiary); }
      }
      &.error { 
        border-color: var(--mat-sys-error); 
        .status-dot { background: var(--mat-sys-error); }
      }
      &.offline { 
        border-color: var(--mat-sys-outline-variant);
        .status-dot { background: var(--mat-sys-on-surface-variant); }
      }
      &.maintenance { 
        border-color: var(--theme-status-info-border); 
        .status-dot { background: var(--theme-status-info); }
      }
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;

      &.pulse {
        box-shadow: 0 0 0 0 var(--mat-sys-tertiary-container);
        animation: pulse-animation 2s infinite;
      }
    }

    .source-tag {
      font-size: 9px;
      font-weight: 700;
      padding: 1px 4px;
      border-radius: 4px;
      margin-left: 4px;
      text-transform: uppercase;
      opacity: 0.8;

      &.simulated {
        background: var(--mat-sys-tertiary-container);
        color: var(--mat-sys-on-tertiary-container);
      }
      &.cached {
        background: var(--mat-sys-surface-variant);
        color: var(--mat-sys-on-surface-variant);
      }
      &.definition {
        background: var(--mat-sys-primary-container);
        color: var(--mat-sys-on-primary-container);
      }
    }

    @keyframes pulse-animation {
      0% {
        transform: scale(1);
        box-shadow: 0 0 0 0 var(--mat-sys-tertiary);
      }
      70% {
        transform: scale(1.1);
        box-shadow: 0 0 0 6px transparent;
      }
      100% {
        transform: scale(1);
        box-shadow: 0 0 0 0 transparent;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MachineStatusBadgeComponent {
  /** The current status of the machine. */
  @Input({ required: true }) status!: MachineStatus;

  /** The source of the machine's state. */
  @Input() stateSource: 'live' | 'simulated' | 'cached' | 'definition' = 'live';

  /** Whether to show the text label for the status. */
  @Input() showLabel = true;

  /** Whether to use a compact layout. */
  @Input() compact = false;

  /** Computed classes for the badge container. */
  protected badgeClasses = computed(() => {
    const s = this.status;
    return {
      [s]: !!s,
      'compact': this.compact
    };
  });

  /** Human-readable label for the status. */
  protected statusLabel = computed(() => {
    if (!this.status) return '';
    return this.status.charAt(0).toUpperCase() + this.status.slice(1);
  });
}
