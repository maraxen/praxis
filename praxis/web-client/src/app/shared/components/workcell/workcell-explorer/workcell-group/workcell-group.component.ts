import { Component, output, signal, effect, ChangeDetectionStrategy, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import type { WorkcellGroup, MachineWithRuntime } from '@features/workcell/models/workcell-view.models';
import { MachineTreeNodeComponent } from '../machine-tree-node/machine-tree-node.component';

@Component({
  selector: 'app-workcell-group',
  standalone: true,
  imports: [CommonModule, MachineTreeNodeComponent],
  template: `
    <div class="mb-2">
      <!-- Group Header -->
      <button
        type="button"
        (click)="toggle()"
        class="flex w-full items-center justify-between rounded-md px-2 py-2 text-left text-sm font-semibold text-[var(--mat-sys-on-surface-variant)] hover:bg-[var(--mat-sys-surface-variant)] hover:text-[var(--mat-sys-on-surface)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--mat-sys-primary)]"
        [attr.aria-expanded]="isExpanded()"
      >
        <div class="flex items-center gap-2">
          <!-- Chevron Icon -->
          <svg
            class="h-4 w-4 transform transition-transform duration-200"
            [class.rotate-90]="isExpanded()"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
          
          <span>{{ group.workcell?.name || 'Unassigned' }}</span>
        </div>
        
        <span class="text-xs font-normal text-[var(--mat-sys-on-surface-variant)]">
          {{ group.machines.length }}
        </span>
      </button>

      @if (isExpanded()) {
        <div class="mt-1 ml-2 space-y-1 border-l border-[var(--mat-sys-outline-variant)] pl-2" role="group">
          @for (machine of group.machines; track machine.accession_id) {
            <app-machine-tree-node
              [machine]="machine"
              (machineSelect)="onMachineSelect($event)"
            />
          }
        </div>
      }
    </div>
  `,
  styles: [`:host { display: block; }`],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class WorkcellGroupComponent {
  @Input({ required: true }) set group(value: WorkcellGroup) {
    this.groupSignal.set(value);
  }
  get group(): WorkcellGroup {
    return this.groupSignal()!;
  }

  groupSignal = signal<WorkcellGroup | null>(null);
  machineSelect = output<MachineWithRuntime>();

  isExpanded = signal(false);

  constructor() {
    effect(() => {
      const g = this.groupSignal();
      if (!g) return;

      // If the group has explicit expansion (e.g. from search filtering), use it.
      // Otherwise, check local storage.
      if (g.isExpanded) {
        this.isExpanded.set(true);
      } else {
        const id = g.workcell?.accession_id || 'unassigned';
        const stored = localStorage.getItem(`workcell-expanded-${id}`);
        this.isExpanded.set(stored === 'true');
      }
    });
  }

  toggle() {
    this.isExpanded.update(v => !v);
    const id = this.group.workcell?.accession_id || 'unassigned';
    localStorage.setItem(`workcell-expanded-${id}`, String(this.isExpanded()));
  }

  onMachineSelect(machine: MachineWithRuntime) {
    this.machineSelect.emit(machine);
  }
}
