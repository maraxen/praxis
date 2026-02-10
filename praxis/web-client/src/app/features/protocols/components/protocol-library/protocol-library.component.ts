import { Component, ChangeDetectionStrategy, inject, signal, computed } from '@angular/core';

import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { ProtocolService } from '../../services/protocol.service';
import { ProtocolDefinition } from '../../models/protocol.models';
import { finalize } from 'rxjs/operators';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ViewControlsComponent } from '@shared/components/view-controls/view-controls.component';
import { ViewControlsConfig, ViewControlsState } from '@shared/components/view-controls/view-controls.types';
import { ProtocolCardComponent } from '@features/run-protocol/components/protocol-card/protocol-card.component';
import { PageTooltipComponent } from '@shared/components/page-tooltip/page-tooltip.component';

import { ProtocolDetailDialogComponent } from '../protocol-detail-dialog/protocol-detail-dialog.component';

@Component({
  selector: 'app-protocol-library',
  standalone: true,
  imports: [
    MatTableModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatInputModule,
    MatFormFieldModule,
    MatDialogModule,
    ReactiveFormsModule,
    FormsModule,
    MatProgressSpinnerModule,
    ViewControlsComponent,
    ProtocolCardComponent,
    PageTooltipComponent
  ],
  template: `
    <div class="p-6 max-w-screen-2xl mx-auto h-full flex flex-col" #protocolsRoot>
      <app-page-tooltip 
        id="protocols-intro" 
        text="Access your library of experimental protocols. You can upload new definitions, view detailed specifications, and start execution directly from here." 
        [target]="protocolsRoot">
      </app-page-tooltip>
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div>
          <h1 class="text-3xl font-bold text-sys-text-primary mb-1">Protocol Library</h1>
          <p class="text-sys-text-secondary">Manage and execute your experimental protocols</p>
        </div>
        <button mat-flat-button class="!bg-gradient-to-br !from-primary !to-primary-dark !text-white !rounded-xl !px-6 !py-6 !font-semibold shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all hover:-translate-y-0.5" (click)="uploadProtocol()" [disabled]="isLoading()" data-tour-id="import-protocol-btn">
          <mat-icon>upload</mat-icon>
          Upload Protocol
        </button>
      </div>

      <div class="bg-surface border border-[var(--theme-border)] rounded-3xl overflow-hidden backdrop-blur-xl flex flex-col flex-1 min-h-0 shadow-xl">
        <div class="bg-surface border-b border-[var(--theme-border)] px-4 py-2">
          <app-view-controls
            [config]="viewConfig()"
            [state]="viewState()"
            (stateChange)="onStateChange($event)">
          </app-view-controls>
        </div>

        <div class="flex-1 overflow-auto bg-[var(--mat-sys-surface-variant)] relative">
           @if (isLoading()) {
             <div class="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-black/50 z-10 backdrop-blur-sm">
               <mat-spinner diameter="40"></mat-spinner>
             </div>
           }
           
          @if (filteredProtocols().length > 0) {
            @if (viewState().viewType === 'table' || viewState().viewType === 'list') {
              <table mat-table [dataSource]="filteredProtocols()" class="!bg-transparent w-full" data-tour-id="protocol-table">
                <!-- Name Column -->
                <ng-container matColumnDef="name">
                  <th mat-header-cell *matHeaderCellDef class="px-6 py-4"> Name </th>
                  <td mat-cell *matCellDef="let protocol" class="!text-sys-text-primary border-b !border-[var(--theme-border)] px-6 py-4">
                    <div class="flex flex-col">
                      <div class="flex items-center gap-2">
                        <span class="font-medium text-base">{{ protocol.name }}</span>
                        @if (protocol.is_top_level) {
                          <span class="top-level-badge">Top Level</span>
                        }
                      </div>
                    </div>
                  </td>
                </ng-container>

                <!-- Version Column -->
                <ng-container matColumnDef="version">
                  <th mat-header-cell *matHeaderCellDef class="px-6 py-4"> Version </th>
                  <td mat-cell *matCellDef="let protocol" class="!text-sys-text-secondary border-b !border-[var(--theme-border)] px-6 py-4"> 
                    <span class="font-mono text-xs bg-[var(--theme-surface-elevated)] px-2 py-1 rounded text-sys-text-secondary">{{ protocol.version }}</span>
                  </td>
                </ng-container>

                <!-- Description Column -->
                <ng-container matColumnDef="description">
                  <th mat-header-cell *matHeaderCellDef class="px-6 py-4"> Description </th>
                  <td mat-cell *matCellDef="let protocol" class="!text-sys-text-secondary opacity-70 border-b !border-[var(--theme-border)] px-6 py-4 max-w-md truncate"> {{ protocol.description || 'No description' }} </td>
                </ng-container>

                <!-- Category Column -->
                <ng-container matColumnDef="category">
                  <th mat-header-cell *matHeaderCellDef class="px-6 py-4"> Category </th>
                  <td mat-cell *matCellDef="let protocol" class="!text-sys-text-secondary border-b !border-[var(--theme-border)] px-6 py-4">
                    @if (protocol.category) {
                      <span class="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-400/10 text-blue-300 border border-blue-400/20">
                        {{ protocol.category }}
                      </span>
                    } @else {
                      <span class="text-sys-text-tertiary italic">Uncategorized</span>
                    }
                  </td>
                </ng-container>

                <!-- Actions Column -->
                <ng-container matColumnDef="actions">
                  <th mat-header-cell *matHeaderCellDef class="px-6 py-4 text-center"> Actions </th>
                  <td mat-cell *matCellDef="let protocol" class="border-b !border-[var(--theme-border)] px-6 py-4">
                    <div class="actions-cell">
                      <button mat-icon-button class="!text-green-400 hover:!bg-green-400/20 transition-all" matTooltip="Run Protocol" (click)="$event.stopPropagation(); runProtocol(protocol)">
                        <mat-icon>play_arrow</mat-icon>
                      </button>
                    </div>
                  </td>
                </ng-container>

                <tr mat-header-row *matHeaderRowDef="displayedColumns" class="!h-12"></tr>
                <tr mat-row *matRowDef="let row; columns: displayedColumns;" (click)="viewDetails(row)" class="hover:bg-[var(--mat-sys-surface-variant)] transition-colors cursor-pointer !h-16"></tr>
              </table>
            } @else {
              <div class="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                @for (protocol of filteredProtocols(); track protocol.accession_id) {
                  <app-protocol-card
                    [protocol]="protocol"
                    (select)="viewDetails($event)">
                  </app-protocol-card>
                }
              </div>
            }
          } @else {
            <div class="flex flex-col items-center justify-center h-full text-sys-text-tertiary py-20">
              <mat-icon class="!w-16 !h-16 !text-[64px] opacity-40 mb-4">science</mat-icon>
              <p class="text-lg font-medium">No protocols found</p>
              <p class="text-sm opacity-60 mb-6">Try adjusting your search or upload a new protocol</p>
              <button mat-flat-button class="!bg-primary/10 !text-primary !rounded-xl !px-6 !py-6 !font-semibold hover:!bg-primary/20 transition-all" (click)="uploadProtocol()">
                <mat-icon>upload</mat-icon>
                Upload Protocol
              </button>
            </div>
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: 100%;
    }
    
    /* Mat Table Overrides for Transparency */
    ::ng-deep .mat-mdc-table {
      background: transparent !important;
    }

    /* Better table header visibility in dark mode */
    ::ng-deep th.mat-header-cell, ::ng-deep .mat-mdc-header-cell {
      background: var(--mat-sys-surface-container-high) !important;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 600;
      border-bottom: 1px solid var(--mat-sys-outline-variant);
    }

    /* Fix badge appearance */
    .top-level-badge {
      background: var(--mat-sys-primary-container);
      color: var(--mat-sys-on-primary-container);
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 500;
    }

    /* Center action icons */
    .actions-cell {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProtocolLibraryComponent {
  private protocolService = inject(ProtocolService);
  private router = inject(Router);
  private dialog = inject(MatDialog);

  protocols = signal<ProtocolDefinition[]>([]);
  isLoading = signal(false);

  viewState = signal<ViewControlsState>({
    viewType: 'table',
    groupBy: null,
    filters: {},
    sortBy: 'name',
    sortOrder: 'asc',
    search: ''
  });

  viewConfig = computed<ViewControlsConfig>(() => ({
    viewTypes: ['table', 'card'],
    filters: [
      {
        key: 'category',
        label: 'Category',
        type: 'multiselect',
        options: this.categoryOptions()
      },
      {
        key: 'type',
        label: 'Type',
        type: 'select',
        options: [
          { label: 'All Types', value: 'all' },
          { label: 'Top Level', value: 'top_level' },
          { label: 'Sub-Protocol', value: 'sub' }
        ]
      },
      {
        key: 'status',
        label: 'Status',
        type: 'multiselect',
        options: [
          { label: 'Passed', value: 'passed' },
          { label: 'Failed', value: 'failed' },
          { label: 'Not Simulated', value: 'none' }
        ]
      }
    ],
    sortOptions: [
      { label: 'Name', value: 'name' },
      { label: 'Category', value: 'category' },
      { label: 'Version', value: 'version' }
    ],
    storageKey: 'protocol-library-view',
    defaults: {
      viewType: 'table',
      sortBy: 'name',
      sortOrder: 'asc'
    }
  }));

  private categoryOptions = computed(() => {
    const cats = new Set<string>();
    this.protocols().forEach(p => {
      if (p.category) cats.add(p.category);
    });
    return Array.from(cats).sort().map(c => ({ label: c, value: c }));
  });

  filteredProtocols = computed(() => {
    const state = this.viewState();
    const query = state.search.toLowerCase();
    const categories = state.filters['category'] || [];
    const type = state.filters['type']?.[0] || 'all';
    const statuses = state.filters['status'] || [];

    let filtered = this.protocols().filter(protocol => {
      // Search filter
      const matchesSearch = !query ||
        protocol.name.toLowerCase().includes(query) ||
        protocol.description?.toLowerCase().includes(query) ||
        protocol.category?.toLowerCase().includes(query);

      // Category filter
      const matchesCategory = categories.length === 0 || (protocol.category && categories.includes(protocol.category));

      // Type filter
      const matchesType = type === 'all' ||
        (type === 'top_level' && protocol.is_top_level) ||
        (type === 'sub' && !protocol.is_top_level);

      // Status filter
      let matchesStatus = true;
      if (statuses.length > 0) {
        matchesStatus = false;
        if (statuses.includes('passed') && protocol.simulation_result?.passed === true) matchesStatus = true;
        if (statuses.includes('failed') && protocol.simulation_result && protocol.simulation_result.passed === false) matchesStatus = true;
        if (statuses.includes('none') && !protocol.simulation_result) matchesStatus = true;
      }

      return matchesSearch && matchesCategory && matchesType && matchesStatus;
    });

    // Sorting
    filtered = [...filtered].sort((a, b) => {
      const valA = (a as unknown as Record<string, unknown>)[state.sortBy] || '';
      const valB = (b as unknown as Record<string, unknown>)[state.sortBy] || '';
      const comparison = valA.toString().localeCompare(valB.toString());
      return state.sortOrder === 'asc' ? comparison : -comparison;
    });

    return filtered;
  });

  displayedColumns: string[] = ['name', 'version', 'description', 'category', 'actions'];

  constructor() {
    this.loadProtocols();
  }

  loadProtocols(): void {
    this.isLoading.set(true);
    this.protocolService.getProtocols().pipe(
      finalize(() => this.isLoading.set(false))
    ).subscribe(
      (data) => {
        this.protocols.set(data);
      },
      (error) => {
        console.error('Error fetching protocols:', error);
      }
    );
  }

  viewDetails(protocol: ProtocolDefinition) {
    this.dialog.open(ProtocolDetailDialogComponent, {
      data: { protocol },
      width: '700px',
      maxWidth: '90vw',
      maxHeight: '90vh',
      panelClass: 'praxis-dialog-panel'
    });
  }

  runProtocol(protocol: ProtocolDefinition) {
    this.router.navigate(['/run'], { queryParams: { protocolId: protocol.accession_id } });
  }

  onStateChange(newState: ViewControlsState) {
    this.viewState.set(newState);
  }

  uploadProtocol() {
    if (this.isLoading()) return;

    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.py';
    fileInput.onchange = (event: Event) => {
      const target = event.target as HTMLInputElement;
      const file = target.files?.[0];
      if (file) {
        this.isLoading.set(true); // Set loading true before API call
        this.protocolService.uploadProtocol(file).pipe(
          finalize(() => this.isLoading.set(false)) // Set loading false after API call completes
        ).subscribe({
          next: () => {
            this.loadProtocols(); // Refresh list
          },
          error: (err) => console.error('[ProtocolLibrary] Upload failed:', err)
        });
      }
    };
    fileInput.click();
  }
}