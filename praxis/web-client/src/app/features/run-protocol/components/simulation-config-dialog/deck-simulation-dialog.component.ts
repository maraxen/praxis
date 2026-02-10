import { Component, ChangeDetectionStrategy, inject, signal, computed } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTabsModule } from '@angular/material/tabs';
import { MatListModule } from '@angular/material/list';
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';

import { DeckCatalogService } from '../../services/deck-catalog.service';
import { DeckVisualizerComponent } from '../deck-visualizer/deck-visualizer.component';
import { DeckConfiguration, CarrierDefinition } from '../../models/deck-layout.models';
import { PlrDeckData } from '@core/models/plr.models';

@Component({
  selector: 'app-deck-simulation-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatFormFieldModule,
    MatInputModule,
    MatTabsModule,
    MatListModule,
    ReactiveFormsModule,
    DeckVisualizerComponent
  ],
  template: `
    <div class="h-full flex flex-col overflow-hidden bg-[var(--mat-sys-surface-container-low)]">
      <!-- Header -->
      <div class="px-6 py-4 bg-[var(--theme-surface)] border-b border-[var(--theme-border)] flex items-center justify-between shrink-0">
        <div>
          <h2 class="text-xl font-bold text-[var(--theme-text-primary)] m-0">New Deck Simulation</h2>
          <p class="text-sm text-[var(--theme-text-secondary)] m-0">Configure detailed deck layout for simulation</p>
        </div>
        <button mat-icon-button (click)="close()">
          <mat-icon>close</mat-icon>
        </button>
      </div>

      <div class="flex-grow flex overflow-hidden">
        <!-- Sidebar Controls -->
        <div class="w-80 flex flex-col border-r border-[var(--theme-border)] bg-[var(--theme-surface)] shrink-0">
          <div class="p-4 space-y-6 overflow-y-auto">
            
            <!-- Configuration Form -->
            <form [formGroup]="configForm" class="flex flex-col gap-4">
              <mat-form-field appearance="outline" class="w-full">
                <mat-label>Configuration Name</mat-label>
                <input matInput formControlName="name" placeholder="e.g. Standard PCR Setup">
                <mat-error *ngIf="configForm.get('name')?.hasError('required')">Name is required</mat-error>
              </mat-form-field>

              <mat-form-field appearance="outline" class="w-full">
                <mat-label>Deck Type</mat-label>
                <mat-select formControlName="deckType" (selectionChange)="onDeckTypeChange()">
                  @for (deck of availableDecks(); track deck.fqn) {
                    <mat-option [value]="deck.fqn">{{ deck.name }}</mat-option>
                  }
                </mat-select>
              </mat-form-field>
            </form>

            <mat-divider></mat-divider>

            <!-- Palette -->
            <div *ngIf="currentDeckConfig()" class="flex flex-col gap-4">
              <div class="flex items-center justify-between">
                <h3 class="text-sm font-bold text-[var(--theme-text-secondary)] uppercase tracking-wider m-0">
                  {{ isSlotBased() ? 'Labware' : 'Carriers' }}
                </h3>
              </div>

              <!-- Rail Based Tools (Hamilton) -->
              <div *ngIf="!isSlotBased()" class="flex flex-col gap-2">
                <div class="text-xs text-[var(--theme-text-tertiary)] mb-2">Select a rail below, then click to add items.</div>
                
                <mat-form-field appearance="outline" class="w-full text-sm">
                  <mat-label>Target Rail (1-30)</mat-label>
                  <input matInput type="number" [formControl]="targetRailControl" min="1" max="30">
                </mat-form-field>

                <div class="grid grid-cols-1 gap-2">
                  <button *ngFor="let carrier of availableCarriers()"
                    mat-stroked-button
                    class="justify-start !text-left h-auto py-2"
                    (click)="addCarrier(carrier)">
                    <div class="flex flex-col items-start gap-1">
                      <span class="font-medium text-[var(--theme-text-primary)]">{{carrier.name}}</span>
                      <span class="text-xs text-[var(--theme-text-tertiary)]">{{carrier.type}} • {{carrier.numSlots}} slots</span>
                    </div>
                  </button>
                </div>
              </div>

              <!-- Slot Based Tools (OT-2) -->
              <div *ngIf="isSlotBased()" class="flex flex-col gap-2">
                 <div class="p-3 bg-[var(--theme-status-info-muted)] text-[var(--theme-status-info)] text-sm rounded-md border border-[var(--theme-status-info-border)]">
                    Slot-based layout editing is coming soon. For now, a standard layout is provided.
                 </div>
              </div>

            </div>

          </div>
          
          <!-- Actions Footer -->
          <div class="p-4 border-t border-[var(--theme-border)] flex gap-2 mt-auto bg-[var(--theme-surface)]">
            <button mat-stroked-button class="flex-1" (click)="close()">Cancel</button>
            <button mat-flat-button color="primary" class="flex-1" 
              [disabled]="configForm.invalid || !currentDeckConfig()"
              (click)="save()">
              Save Configuration
            </button>
          </div>
        </div>

        <!-- Main Visualizer Area -->
        <div class="flex-grow bg-[var(--mat-sys-surface-container-low)] p-4 overflow-hidden relative">
          <div class="absolute inset-4 bg-[var(--theme-surface)] rounded-xl shadow-[var(--glass-shadow)] border border-[var(--theme-border)] overflow-hidden flex flex-col">
            
            <div class="flex-grow overflow-hidden relative">
               <app-deck-visualizer 
                 [layoutData]="visualizationData()" 
               />
               
               <!-- Empty State Overlay if no deck selected -->
               <div *ngIf="!currentDeckConfig()" class="absolute inset-0 z-10 bg-[var(--theme-surface)]/50 backdrop-blur-sm flex items-center justify-center">
                 <div class="bg-[var(--theme-surface)] p-6 rounded-xl shadow-[var(--glass-shadow)] border border-[var(--theme-border)] text-center max-w-sm">
                   <mat-icon class="text-4xl text-[var(--theme-text-tertiary)] mb-2">grid_on</mat-icon>
                   <h3 class="text-lg font-medium text-[var(--theme-text-primary)]">Select a Deck Type</h3>
                   <p class="text-[var(--theme-text-secondary)]">Choose a deck platform from the sidebar to start configuring.</p>
                 </div>
               </div>
            </div>

            <!-- Status Bar -->
            <div class="px-4 py-2 bg-[var(--mat-sys-surface-variant)] border-t border-[var(--theme-border)] text-xs text-[var(--theme-text-tertiary)] flex justify-between">
              <span>{{ currentDeckConfig()?.deckName || 'No Deck' }}</span>
              <span *ngIf="currentDeckConfig()">
                 {{ currentDeckConfig()?.carriers?.length || 0 }} items placed
              </span>
            </div>

          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: 85vh;
      width: 90vw;
      max-width: 1400px;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DeckSimulationDialogComponent {
  private fb = inject(FormBuilder);
  private dialogRef = inject(MatDialogRef<DeckSimulationDialogComponent>);
  private deckService = inject(DeckCatalogService);

  configForm = this.fb.group({
    name: ['', Validators.required],
    deckType: ['', Validators.required]
  });

  targetRailControl = this.fb.control(10, [Validators.min(1), Validators.max(30)]);

  // State
  currentDeckConfig = signal<DeckConfiguration | null>(null);
  availableCarriers = signal<CarrierDefinition[]>([]);
  availableDecks = toSignal(this.deckService.loadDeckDefinitions(), { initialValue: [] });

  // Computed visualization data for the DeckVisualizer
  visualizationData = computed<PlrDeckData | null>(() => {
    const config = this.currentDeckConfig();
    if (!config) return null;

    // We need to synthesize a PlrResource tree from the configuration
    const deckDef = this.deckService.getDeckDefinition(config.deckType);
    if (!deckDef) return null;

    // Start with base deck
    const rootRes = this.deckService.createPlrResourceFromSpec(deckDef);

    // Add configured carriers
    // NOTE: This logic mimics runtime state generation, simplified for preview
    config.carriers.forEach(carrier => {
      // Find x position based on rail
      const rail = config.rails.find(r => r.index === carrier.railPosition - 1); // 1-based to 0-based
      const xPos = rail ? rail.xPosition : 100;

      const carrierRes = {
        name: carrier.name,
        type: carrier.fqn.split('.').pop() || 'Carrier',
        location: { x: xPos, y: 0, z: 0, type: "Coordinate" },
        size_x: carrier.dimensions.width,
        size_y: carrier.dimensions.height,
        size_z: carrier.dimensions.depth,
        children: [] as any[],
        rotation: { x: 0, y: 0, z: 0 }
      };

      // Add dummy children for slots to make them visible
      carrier.slots.forEach(slot => {
        carrierRes.children.push({
          name: slot.name,
          type: "Container", // Generic
          location: slot.position,
          size_x: slot.dimensions.width,
          size_y: slot.dimensions.height,
          size_z: 10,
          children: []
        });
      });

      rootRes.children.push(carrierRes);
    });

    return {
      resource: rootRes,
      state: {} // No live state
    };
  });

  isSlotBased = computed(() => {
    const type = this.configForm.get('deckType')?.value;
    return type?.includes('OT') || type?.includes('Opentrons');
  });

  onDeckTypeChange() {
    const fqn = this.configForm.get('deckType')?.value;
    if (!fqn) {
      this.currentDeckConfig.set(null);
      return;
    }

    const spec = this.deckService.getDeckDefinition(fqn);
    if (spec) {
      const config = this.deckService.createDeckConfiguration(spec);
      this.currentDeckConfig.set(config);

      // Load carriers
      if (spec.layoutType === 'rail-based') {
        this.availableCarriers.set(this.deckService.getCompatibleCarriers(fqn));
        this.targetRailControl.setValue(10); // Default good placement
      } else {
        this.availableCarriers.set([]);
      }
    }
  }

  addCarrier(def: CarrierDefinition) {
    const current = this.currentDeckConfig();
    const railIdx = (this.targetRailControl.value || 1);

    if (!current || !def) return;

    // Create new carrier instance
    const id = `carrier_${Date.now()}`; // Simple ID
    const newCarrier = this.deckService.createCarrierFromDefinition(def, id, railIdx);

    // Update immutable state
    this.currentDeckConfig.set({
      ...current,
      carriers: [...current.carriers, newCarrier]
    });
  }

  save() {
    if (this.configForm.invalid || !this.currentDeckConfig()) return;

    const name = this.configForm.get('name')?.value || 'Untitled Configuration';
    const config = this.currentDeckConfig()!;

    this.deckService.saveUserDeckConfiguration(config, name).subscribe({
      next: (res) => {
        console.log('Deck configuration saved', res);
        this.dialogRef.close(res);
      },
      error: (err) => console.error('Failed to save config', err)
    });
  }

  close() {
    this.dialogRef.close();
  }
}
