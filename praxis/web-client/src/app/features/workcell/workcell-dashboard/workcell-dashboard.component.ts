import { Component, OnInit, inject, signal, ChangeDetectionStrategy, computed, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule, MatMenuTrigger } from '@angular/material/menu';
import { MatDialog } from '@angular/material/dialog';
import { WorkcellViewService } from '../services/workcell-view.service';
import { WorkcellExplorerComponent } from '@shared/components/workcell/workcell-explorer/workcell-explorer.component';
import { MachineCardComponent } from '@shared/components/workcell/machine-card/machine-card.component';
import { MachineCardMiniComponent } from '@shared/components/workcell/machine-card/machine-card-mini.component';
import { MachineFocusViewComponent } from '../machine-focus-view/machine-focus-view.component';
import { MachineWithRuntime } from '../models/workcell-view.models';
import { DeckSimulationDialogComponent } from '@features/run-protocol/components/simulation-config-dialog/deck-simulation-dialog.component';

@Component({
  selector: 'app-workcell-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatMenuModule,
    WorkcellExplorerComponent,
    MachineCardComponent,
    MachineCardMiniComponent,
    MachineFocusViewComponent
  ],
  template: `
    <div class="dashboard-container">
      <!-- Sidebar -->
      <aside class="sidebar">
        <div class="flex h-full flex-col">
          <div class="flex-grow p-0 overflow-hidden">
             <app-workcell-explorer 
                [groups]="workcellGroups()"
                (machineSelect)="onMachineSelected($event)"
             />
          </div>
        </div>
      </aside>

      <!-- Main Canvas -->
      <main class="main-canvas" (contextmenu)="onContextMenu($event)">
        
        <!-- Context Menu Trigger -->
        <div style="visibility: hidden; position: fixed"
             [style.left]="contextMenuPosition.x"
             [style.top]="contextMenuPosition.y"
             [matMenuTriggerFor]="contextMenu">
        </div>

        <!-- Header/Controls - Hidden in Focus Mode -->
        @if (viewMode() !== 'focus') {
          <header class="dashboard-header">
            <div class="flex items-center gap-4">
              <h1 class="header-title">Workcell Dashboard</h1>
              @if (isLoading()) {
                <span class="loading-text animate-pulse">Loading...</span>
              }
            </div>

            <div class="flex items-center gap-3">
              <!-- Simulate Button -->
              <button mat-stroked-button color="primary" (click)="openSimulationDialog()">
                <mat-icon>science</mat-icon>
                Simulate
              </button>

              <div class="header-divider"></div>

              <div class="view-toggle-container">
                <button
                  (click)="setViewMode('grid')"
                  [class.active]="viewMode() === 'grid'"
                  class="toggle-btn"
                >
                  Grid
                </button>
                <button
                  (click)="setViewMode('list')"
                  [class.active]="viewMode() === 'list'"
                  class="toggle-btn"
                >
                  List
                </button>
              </div>
            </div>
          </header>
        }

        <!-- Canvas Content -->
        <div class="canvas-content" [class.p-6]="viewMode() !== 'focus'">
          @if (isLoading()) {
            <div class="flex items-center justify-center h-full">
               <div class="spinner"></div>
            </div>
          } @else {
            @switch (viewMode()) {
              @case ('grid') {
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 fade-in grid-view">
                  @for (machine of allMachines(); track machine.accession_id) {
                    <app-machine-card 
                      [machine]="machine"
                      (machineSelected)="onMachineSelected($event)">
                    </app-machine-card>
                  } @empty {
                    <div class="col-span-full flex flex-col items-center justify-center py-20 empty-state">
                      <mat-icon class="mb-4 !w-16 !h-16 !text-[64px]">precision_manufacturing</mat-icon>
                      <p>No machines found</p>
                      <button mat-flat-button color="primary" class="mt-4" (click)="openSimulationDialog()">
                        Create Simulation
                      </button>
                    </div>
                  }
                </div>
              }
              @case ('list') {
                <div class="flex flex-col gap-4 fade-in list-view">
                  @for (machine of allMachines(); track machine.accession_id) {
                    <app-machine-card-mini 
                      [machine]="machine"
                      (machineSelected)="onMachineSelected($event)">
                    </app-machine-card-mini>
                  } @empty {
                    <div class="flex flex-col items-center justify-center py-10 empty-state">
                       <p>No machines found</p>
                    </div>
                  }
                </div>
              }
              @case ('focus') {
                @if (selectedMachine(); as machine) {
                  <app-machine-focus-view 
                    [machine]="machine"
                    (back)="clearSelection()"
                  ></app-machine-focus-view>
                } @else {
                  <div class="flex flex-col items-center justify-center h-full empty-state fade-in">
                    <mat-icon class="text-6xl mb-4">select_all</mat-icon>
                    <p>Select a machine from the explorer to focus</p>
                  </div>
                }
              }
            }
          }
        </div>
      </main>

      <!-- Context Menu -->
      <mat-menu #contextMenu="matMenu">
        <button mat-menu-item (click)="openSimulationDialog()">
          <mat-icon>add_box</mat-icon>
          <span>Add Simulated Deck</span>
        </button>
        <button mat-menu-item disabled>
          <mat-icon>refresh</mat-icon>
          <span>Refresh View</span>
        </button>
      </mat-menu>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: 100%;
    }
    .dashboard-container {
      display: flex;
      height: 100%;
      width: 100%;
      overflow: hidden;
      background-color: var(--mat-sys-surface-container-low);
    }
    .sidebar {
      width: 280px;
      flex-shrink: 0;
      border-right: 1px solid var(--mat-sys-outline-variant);
      background-color: var(--mat-sys-surface);
    }
    .main-canvas {
      display: flex;
      flex-direction: column;
      flex-grow: 1;
      position: relative;
      overflow: hidden;
    }
    .dashboard-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1rem 1.5rem;
      background-color: var(--mat-sys-surface);
      border-bottom: 1px solid var(--mat-sys-outline-variant);
    }
    .header-title {
      font-size: 1.25rem;
      font-weight: 700;
      color: var(--mat-sys-on-surface);
      margin: 0;
    }
    .loading-text {
      font-size: 0.75rem;
      color: var(--mat-sys-on-surface-variant);
    }
    .header-divider {
      height: 1.5rem;
      width: 1px;
      background-color: var(--mat-sys-outline-variant);
      margin: 0 0.25rem;
    }
    .view-toggle-container {
      display: flex;
      align-items: center;
      background-color: var(--mat-sys-surface-container-high);
      padding: 0.25rem;
      border-radius: 0.5rem;
    }
    .toggle-btn {
      padding: 0.25rem 0.75rem;
      font-size: 0.875rem;
      border-radius: 0.375rem;
      transition: all 0.2s;
      color: var(--mat-sys-on-surface-variant);
      
      &:hover {
        color: var(--mat-sys-on-surface);
      }
      
      &.active {
        background-color: var(--mat-sys-surface);
        color: var(--mat-sys-primary);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
      }
    }
    .canvas-content {
      display: flex;
      flex-direction: column;
      flex-grow: 1;
      overflow: auto;
    }
    .spinner {
      width: 2rem;
      height: 2rem;
      border: 4px solid var(--mat-sys-primary);
      border-top-color: transparent;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .empty-state {
      color: var(--mat-sys-on-surface-variant);
    }
    .fade-in {
      animation: fadeIn 0.3s ease-in;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkcellDashboardComponent implements OnInit {
  public viewService = inject(WorkcellViewService);
  private dialog = inject(MatDialog);

  // Local State
  viewMode = signal<'grid' | 'list' | 'focus'>('grid');
  isLoading = signal<boolean>(true);

  // Service State Alias
  workcellGroups = this.viewService.workcellGroups;
  selectedMachine = this.viewService.selectedMachine;

  // Derived Data
  allMachines = computed(() => {
    return this.workcellGroups().flatMap(g => g.machines);
  });

  // Context Menu
  @ViewChild(MatMenuTrigger) contextMenuTrigger!: MatMenuTrigger;
  contextMenuPosition = { x: '0px', y: '0px' };

  ngOnInit() {
    if (typeof window !== 'undefined') {
      (window as any).dashboard = this;
    }
    this.viewService.loadWorkcellGroups().subscribe({
      next: () => this.isLoading.set(false),
      error: (err) => {
        console.error('Failed to load workcells', err);
        this.isLoading.set(false);
      }
    });
  }

  setViewMode(mode: 'grid' | 'list' | 'focus') {
    this.viewMode.set(mode);
  }

  onMachineSelected(machine: MachineWithRuntime) {
    this.selectedMachine.set(machine);
    this.viewMode.set('focus');
  }

  clearSelection() {
    this.selectedMachine.set(null);
    this.viewMode.set('grid');
  }

  onContextMenu(event: MouseEvent) {
    event.preventDefault();
    this.contextMenuPosition.x = event.clientX + 'px';
    this.contextMenuPosition.y = event.clientY + 'px';
    this.contextMenuTrigger.openMenu();
  }

  openSimulationDialog() {
    this.dialog.open(DeckSimulationDialogComponent, {
      width: '90vw',
      maxWidth: '1400px',
      height: '85vh',
      panelClass: 'simulation-dialog-panel'
    }).afterClosed().subscribe(result => {
      if (result) {
        // Reload workcells to ensure any new state is reflected
        this.viewService.loadWorkcellGroups().subscribe();
      }
    });
  }
}
