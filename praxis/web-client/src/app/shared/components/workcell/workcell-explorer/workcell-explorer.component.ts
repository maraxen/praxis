import { Component, output, signal, computed, ChangeDetectionStrategy, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WorkcellGroup, MachineWithRuntime } from '@features/workcell/models/workcell-view.models';
import { WorkcellGroupComponent } from './workcell-group/workcell-group.component';

@Component({
  selector: 'app-workcell-explorer',
  standalone: true,
  imports: [CommonModule, WorkcellGroupComponent],
  template: `
    <div class="flex flex-col h-full explorer-container border-r border-[var(--mat-sys-outline-variant)]">
      <!-- Search Header -->
      <div class="p-4 border-b border-[var(--mat-sys-outline-variant)]">
        <div class="relative">
          <input
            type="text"
            placeholder="Search machines..."
            class="w-full rounded-md border border-[var(--mat-sys-outline-variant)] bg-[var(--mat-sys-surface-container)] py-2 pl-9 pr-4 text-sm text-[var(--mat-sys-on-surface)] placeholder-[var(--mat-sys-on-surface-variant)] focus:border-[var(--mat-sys-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--mat-sys-primary)]"
            [value]="searchQuery()"
            (input)="updateSearch($event)"
          />
          <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
            <svg class="h-4 w-4 text-[var(--mat-sys-on-surface-variant)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>
      </div>

      <!-- Content -->
      <div class="flex-grow overflow-y-auto p-2">
        @if (filteredGroups().length === 0) {
          <div class="p-4 text-center text-sm text-[var(--mat-sys-on-surface-variant)]">
            No machines found matching "{{ searchQuery() }}"
          </div>
        } @else {
          @for (group of filteredGroups(); track group.workcell?.accession_id || 'unassigned') {
            <app-workcell-group
              [group]="group"
              (machineSelect)="onMachineSelect($event)"
            />
          }
        }
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; height: 100%; }
    .explorer-container {
      background-color: var(--mat-sys-surface);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class WorkcellExplorerComponent {
  @Input({ required: true }) set groups(value: WorkcellGroup[]) {
    this.groupsSignal.set(value);
  }
  get groups() {
    return this.groupsSignal();
  }
  private groupsSignal = signal<WorkcellGroup[]>([]);

  machineSelect = output<MachineWithRuntime>();

  searchQuery = signal('');

  filteredGroups = computed(() => {
    const query = this.searchQuery().toLowerCase().trim();
    const allGroups = this.groupsSignal();

    if (!query) {
      return allGroups;
    }

    // Filter logic
    return allGroups.map(group => {
      // Check if group name matches
      const groupName = group.workcell?.name?.toLowerCase() || 'unassigned';
      const hasGroupMatch = groupName.includes(query);

      // Check if any machines match
      const matchingMachines = group.machines.filter(m =>
        m.name.toLowerCase().includes(query) ||
        m.machine_type?.toLowerCase().includes(query)
      );

      if (hasGroupMatch) {
        // If group matches, return group with ALL machines, fully expanded
        return { ...group, isExpanded: true };
      } else if (matchingMachines.length > 0) {
        // If machines match, return group with ONLY matching machines, expanded
        return { ...group, machines: matchingMachines, isExpanded: true };
      }

      return null;
    }).filter((g): g is WorkcellGroup => g !== null);
  });

  updateSearch(event: Event) {
    const input = event.target as HTMLInputElement;
    this.searchQuery.set(input.value);
  }

  onMachineSelect(machine: MachineWithRuntime) {
    this.machineSelect.emit(machine);
  }
}
