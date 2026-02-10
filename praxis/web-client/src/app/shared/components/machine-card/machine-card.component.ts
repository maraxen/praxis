import { Component, ChangeDetectionStrategy, input, output } from '@angular/core';
import { humanize } from '@core/utils/plr-display.utils';

import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Machine } from '@features/assets/models/asset.models';
import { MachineCompatibility } from '@features/run-protocol/models/machine-compatibility.models';
import { HardwareBadgeComponent } from '../hardware-badge/hardware-badge.component';
import { CommonModule } from '@angular/common';

// Local type to handle properties not strictly defined in the Machine model
type MachineWithFlags = Machine & {
  is_simulated?: boolean;
  is_template?: boolean;
  type?: string;
};

@Component({
  selector: 'app-machine-card',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    HardwareBadgeComponent
  ],
  template: `
    <div
      class="machine-card relative border-[1.5px] rounded-2xl p-6 cursor-pointer transition-all duration-300 group hover:-translate-y-1.5 hover:shadow-2xl hover:shadow-primary/10 h-full backdrop-blur-xl flex flex-col"
      [class.border-outline]="!selected()"
      [class.border-primary]="selected()"
      [class.selected-bg]="selected()"
      [class.opacity-60]="machineCompatibility() && !machineCompatibility()?.compatibility?.is_compatible"
      [class.opacity-40]="isPhysicalMode() && isSimulated()"
      [class.grayscale]="isPhysicalMode() && isSimulated()"
      (click)="onClick()"
    >
      <!-- Badge as chip overlay -->
      <div class="absolute top-3 right-3 z-10">
        <app-hardware-badge [isSimulated]="isSimulated()" [isTemplate]="isTemplate()" />
      </div>

      <div class="card-content flex-grow pt-2">
        <h3 class="text-lg font-bold text-sys-text-primary group-hover:text-primary transition-colors line-clamp-2 pr-16">{{ getMachine().name }}</h3>
        <span class="text-[10px] font-bold uppercase tracking-widest text-sys-text-tertiary block mt-1">{{ humanize(getMachine().machine_category) || 'Laboratory Machine' }}</span>
        <span class="text-xs text-sys-text-secondary block mt-0.5 opacity-60">{{ getMachine().manufacturer }} {{ getMachine().model }}</span>
      </div>

      <!-- Compatibility Info -->
      <div class="card-actions mt-auto">
        @if (machineCompatibility()) {
          @if (!machineCompatibility()?.compatibility?.is_compatible) {
            <div class="mt-4 p-3 bg-red-400/10 rounded-lg border border-red-400/20">
              <p class="text-sm text-red-400 font-medium mb-1">Incompatible</p>
              <ul class="text-xs text-red-400/70 list-disc pl-4 space-y-1">
                @for (missing of machineCompatibility()!.compatibility.missing_capabilities; track missing.capability_name) {
                   <li>Missing: {{ missing.capability_name }}</li>
                }
              </ul>
            </div>
          } @else if (machineCompatibility()!.compatibility.warnings.length > 0) {
             <div class="mt-4 p-3 bg-amber-400/10 rounded-lg border border-amber-400/20">
              <p class="text-sm text-amber-500 font-medium mb-1">Warnings</p>
              <ul class="text-xs text-amber-600/70 list-disc pl-4 space-y-1">
                @for (warn of machineCompatibility()!.compatibility.warnings; track warn) {
                   <li>{{ warn }}</li>
                }
              </ul>
            </div>
          }
        }

        <!-- Physical Mode Warning -->
        @if (isPhysicalMode() && isSimulated()) {
          <div class="mt-4 p-3 bg-red-400/10 rounded-lg border border-red-400/20">
            <p class="text-sm text-red-400 font-medium">Not available for Physical mode</p>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .machine-card {
      min-height: 160px;
      border-color: var(--mat-sys-outline-variant);
      background: linear-gradient(135deg, var(--mat-sys-surface) 0%, var(--mat-sys-surface-container-low) 100%);
      position: relative;
      overflow: hidden;
    }

    .machine-card::before {
      content: '';
      position: absolute;
      top: -50%;
      left: -50%;
      width: 200%;
      height: 200%;
      background: radial-gradient(circle at center, var(--mat-sys-primary-container) 0%, transparent 70%);
      opacity: 0.05;
      pointer-events: none;
      transition: opacity 0.3s ease;
    }

    .machine-card:hover::before {
      opacity: 0.1;
    }

    .machine-card.border-outline {
      border-color: var(--mat-sys-outline-variant);
    }

    .machine-card.border-primary {
      border-color: var(--mat-sys-primary);
      box-shadow: 0 0 15px -5px var(--mat-sys-primary);
    }

    .machine-card.selected-bg {
      background: linear-gradient(135deg, var(--mat-sys-primary-container) 0%, var(--mat-sys-surface-container-low) 100%);
    }

    .machine-card-header {
      display: flex;
      align-items: center;
      min-height: 32px;
    }

    .status-indicator {
      flex-shrink: 0;
      margin-right: 8px;
      display: flex;
      align-items: center;
    }

    .border-primary { border-color: var(--sys-primary, #6366f1); }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MachineCardComponent {
  /** Humanize PLR identifiers for template use */
  humanize = humanize;

  // Inputs can be either a straight Machine or the Compatibility wrapper
  machine = input<Machine | null>(null);
  machineCompatibility = input<MachineCompatibility | null>(null);

  selected = input<boolean>(false);
  isPhysicalMode = input<boolean>(false);

  cardClick = output<void>();

  getMachine(): Machine {
    if (this.machine()) return this.machine()!;
    if (this.machineCompatibility()) return this.machineCompatibility()!.machine;
    throw new Error('MachineCard must provide either machine or machineCompatibility input');
  }

  isSimulated(): boolean {
    const m = this.getMachine() as MachineWithFlags;
    if (!m) return false;

    const connectionInfo = m.connection_info || {};
    const backend = (connectionInfo['backend'] || '').toString();
    const type = m.type || '';

    return m.is_simulation_override === true ||
      m.is_simulated === true ||
      backend.includes('Simulator') ||
      backend.includes('Simulation') ||
      type.toLowerCase().includes('simulator');
  }

  isTemplate(): boolean {
    return (this.getMachine() as MachineWithFlags).is_template === true;
  }

  onClick() {
    this.cardClick.emit();
  }
}
