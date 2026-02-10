import { ChangeDetectionStrategy, Component, Input, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

export type DeckStateSource = 'live' | 'simulated' | 'cached' | 'definition';

@Component({
  selector: 'app-deck-state-indicator',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="state-indicator" [class]="source">
      <span class="status-dot" [class.pulse]="source === 'live'"></span>
      <span class="status-label">{{ label() }}</span>
    </div>
  `,
  styles: [`
    :host {
      display: inline-block;
      vertical-align: middle;
    }

    .state-indicator {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      white-space: nowrap;
      background: var(--mat-sys-surface-variant);
      border: 1px solid var(--theme-border-light);
      color: var(--theme-text-primary);
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    .state-indicator.live {
      border-color: var(--theme-status-success-border);
      background: var(--theme-status-success-muted);
      color: var(--theme-status-success);
      .status-dot { 
        background: var(--mat-sys-success);
      }
      .status-dot.pulse {
        box-shadow: 0 0 0 0 var(--theme-status-success);
        animation: pulse-green 2s infinite;
      }
    }

    .state-indicator.simulated {
      border-color: var(--theme-status-info-border);
      background: var(--theme-status-info-muted);
      color: var(--theme-status-info);
      .status-dot { background: var(--mat-sys-tertiary); }
    }

    .state-indicator.cached {
      border-color: var(--theme-border);
      background: var(--mat-sys-surface-variant);
      color: var(--theme-text-secondary);
      .status-dot { background: var(--mat-sys-on-surface-variant); }
    }

    .state-indicator.definition {
      border-color: var(--theme-border-light);
      border-style: dashed;
      background: transparent;
      color: var(--theme-text-tertiary);
      .status-dot { background: var(--mat-sys-primary-container); }
    }

    @keyframes pulse-green {
      0% {
        transform: scale(1);
        box-shadow: 0 0 0 0 var(--theme-status-success);
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
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DeckStateIndicatorComponent {
  @Input({ required: true }) source!: DeckStateSource;

  protected label = computed(() => {
    switch (this.source) {
      case 'live': return 'Live';
      case 'simulated': return 'Simulated';
      case 'cached': return 'Offline';
      case 'definition': return 'Static';
      default: return this.source;
    }
  });
}
