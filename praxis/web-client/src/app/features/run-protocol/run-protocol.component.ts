import { ChangeDetectionStrategy, Component, computed, effect, inject, OnInit, signal, ViewChild } from '@angular/core';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { FormBuilder, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MatBadgeModule } from '@angular/material/badge';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatStepper, MatStepperModule } from '@angular/material/stepper';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize, map, take, switchMap } from 'rxjs';

import { MatDialog } from '@angular/material/dialog';
import { ModeService } from '@core/services/mode.service';
import { AppStore } from '@core/store/app.store';
import { ProtocolDefinition } from '@features/protocols/models/protocol.models';
import { ProtocolService } from '@features/protocols/services/protocol.service';
import { HardwareDiscoveryButtonComponent } from '@shared/components/hardware-discovery-button/hardware-discovery-button.component';
import { WellSelectorDialogComponent, WellSelectorDialogData, WellSelectorDialogResult } from '@shared/components/well-selector-dialog/well-selector-dialog.component';
import { DeckSetupWizardComponent } from './components/deck-setup-wizard/deck-setup-wizard.component';
import { GuidedSetupComponent } from './components/guided-setup/guided-setup.component'; // Import added
import { MachineCompatibility } from './models/machine-compatibility.models';
import { MachineSelectionComponent } from './components/machine-selection/machine-selection.component';
import { MachineArgumentSelectorComponent, MachineArgumentSelection } from '@shared/components/machine-argument-selector/machine-argument-selector.component';
import { ParameterConfigComponent } from './components/parameter-config/parameter-config.component';
import { ProtocolCardSkeletonComponent } from './components/protocol-card/protocol-card-skeleton.component';
import { ProtocolCardComponent } from './components/protocol-card/protocol-card.component';
import { DeckCatalogService } from './services/deck-catalog.service';
import { DeckGeneratorService } from './services/deck-generator.service';
import { ExecutionService } from './services/execution.service';
import { WizardStateService } from './services/wizard-state.service';
import { ProtocolSummaryComponent } from './components/protocol-summary/protocol-summary.component';
import { AssetService } from '@features/assets/services/asset.service';
import { SimulationConfigDialogComponent } from './components/simulation-config-dialog/simulation-config-dialog.component';
import { Machine as _Machine, MachineDefinition, MachineStatus as _MachineStatus } from '@features/assets/models/asset.models';
import { MACHINE_CATEGORIES, PLRCategory } from '@core/db/plr-category';
import { HasUnsavedChanges } from '@core/guards/navigation.guard';


const RECENTS_KEY = 'praxis_recent_protocols';
const WIZARD_STORAGE_KEY = 'praxis_run_wizard_state';
const MAX_RECENTS = 5;

interface FilterOption {
  value: string;
  count: number;
  selected: boolean;
}

interface FilterCategory {
  key: string;
  label: string;
  options: FilterOption[];
  expanded: boolean;
}

@Component({
  selector: 'app-run-protocol',
  standalone: true,
  imports: [
    MatStepperModule,
    MatButtonModule,
    MatIconModule,
    FormsModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatExpansionModule,
    MatCheckboxModule,
    MatBadgeModule,
    MatProgressSpinnerModule,
    MatSlideToggleModule,
    MatButtonToggleModule,
    MatTooltipModule,
    ParameterConfigComponent,
    ProtocolCardComponent,
    ProtocolCardSkeletonComponent,
    MachineSelectionComponent,
    MachineArgumentSelectorComponent,
    HardwareDiscoveryButtonComponent,
    DeckSetupWizardComponent,
    ProtocolSummaryComponent,
    GuidedSetupComponent,
    MatSnackBarModule
  ],
  template: `
    <div class="h-full flex flex-col p-6 max-w-screen-2xl mx-auto">
      <!-- Top Bar -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h1 class="text-3xl font-bold text-sys-text-primary mb-1">Execute Protocol</h1>
          <p class="text-sys-text-secondary">Configure and run experimental procedures</p>
        </div>
        
        <!-- Simulation Mode Toggle -->
        <div class="flex items-center gap-3">
           <mat-button-toggle-group
             hideSingleSelectionIndicator
             [value]="store.simulationMode()"
             (change)="store.setSimulationMode($event.value)"
             class="!rounded-full !border-[var(--theme-border)] !bg-[var(--mat-sys-surface-variant)] !overflow-hidden">
             <mat-button-toggle [value]="false" class="!px-4 !text-sm !font-medium" [class.!text-sys-text-primary]="!store.simulationMode()">Physical</mat-button-toggle>
             <mat-button-toggle [value]="true" class="!px-4 !text-sm !font-medium" [class.!text-primary]="store.simulationMode()">Simulation</mat-button-toggle>
           </mat-button-toggle-group>
        </div>
      </div>

      <!-- Main Content Surface -->
      <div class="bg-surface border border-[var(--theme-border)] rounded-3xl overflow-y-auto overflow-x-hidden backdrop-blur-xl flex-1 min-h-0 shadow-xl flex flex-col">
        <mat-stepper [linear]="true" #stepper class="!bg-transparent h-full flex flex-col">
          
          <!-- Step 1: Select Protocol -->
          <mat-step [stepControl]="protocolFormGroup">
            <ng-template matStepLabel><span data-tour-id="run-step-label-protocol">Select Protocol</span></ng-template>
            <form [formGroup]="protocolFormGroup" class="h-full flex flex-col p-6" data-tour-id="run-step-protocol">
              @if (selectedProtocol()) {
                <div class="flex flex-col h-full overflow-y-auto px-6 pb-6">
                  <!-- Navigation buttons at top -->
                  <div class="flex justify-between mb-6 sticky top-0 bg-surface z-10 py-4">
                    <button mat-button (click)="clearProtocol()" class="!text-sys-text-secondary">
                      <mat-icon>arrow_back</mat-icon> Back to Selection
                    </button>
                    <button mat-flat-button color="primary" matStepperNext class="!rounded-xl !px-8 !py-6">
                      Continue <mat-icon>arrow_forward</mat-icon>
                    </button>
                  </div>

                  <!-- Protocol details card -->
                  <div class="max-w-2xl w-full mx-auto bg-surface-elevated border border-primary/30 rounded-3xl p-8 relative overflow-hidden group shadow-2xl">
                    <div class="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-50"></div>
                    
                    <div class="relative z-10 flex flex-col items-center text-center gap-4">
                      <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-primary-dark flex items-center justify-center shadow-lg shadow-primary/30 mb-2">
                        <mat-icon class="!w-8 !h-8 !text-[32px] text-white">science</mat-icon>
                      </div>
                      
                      <h2 class="text-3xl font-bold text-sys-text-primary mb-0">{{ selectedProtocol()?.name }}</h2>
                      
                      <!-- Scrollable description container -->
                      <div class="description-container w-full max-w-lg">
                        <p class="text-lg text-sys-text-secondary">{{ selectedProtocol()?.description }}</p>
                      </div>
                      
                      <div class="flex gap-2 mt-2">
                          <span class="px-3 py-1 rounded-full bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] text-sys-text-secondary text-sm flex items-center gap-2">
                            <mat-icon class="!w-4 !h-4 !text-[16px]">category</mat-icon> {{ selectedProtocol()?.category || 'General' }}
                          </span>
                          <span class="px-3 py-1 rounded-full bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] text-sys-text-secondary text-sm flex items-center gap-2">
                            <mat-icon class="!w-4 !h-4 !text-[16px]">tag</mat-icon> {{ selectedProtocol()?.version }}
                          </span>
                      </div>
                    </div>
                  </div>
                </div>
              } @else {
                <div class="flex h-full gap-6">
                  <!-- Sidebar Filters -->
                  <aside class="w-72 flex-shrink-0 flex flex-col gap-6">
                    <div class="bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] rounded-2xl p-4">
                      <div class="relative mb-4">
                        <mat-icon class="absolute left-3 top-1/2 -translate-y-1/2 text-sys-text-tertiary">search</mat-icon>
                        <input 
                          class="w-full bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] rounded-xl py-3 pl-10 pr-10 text-sys-text-primary placeholder-sys-text-tertiary focus:outline-none focus:border-primary/50 transition-colors"
                          [value]="searchQuery()" 
                          (input)="onSearchChange($event)" 
                          placeholder="Search protocols..."
                        >
                        @if (searchQuery()) {
                          <button class="absolute right-3 top-1/2 -translate-y-1/2 text-sys-text-tertiary hover:text-sys-text-primary" (click)="clearSearch()">
                            <mat-icon class="!w-5 !h-5 !text-[20px]">close</mat-icon>
                          </button>
                        }
                      </div>

                      <div class="flex flex-col gap-4">
                        @for (category of filterCategories(); track category.key) {
                          <div class="flex flex-col gap-2">
                            <h4 class="text-xs font-bold text-sys-text-tertiary uppercase tracking-wider px-2">{{ category.label }}</h4>
                            @for (option of category.options; track option.value) {
                              <button 
                                class="flex items-center justify-between w-full px-3 py-2 rounded-lg text-sm transition-all hover:bg-[var(--mat-sys-surface-variant)] text-left"
                                [class.bg-primary-10]="option.selected"
                                [class.text-primary]="option.selected"
                                [class.text-sys-text-secondary]="!option.selected"
                                (click)="toggleFilter(category.key, option.value)"
                              >
                                <span>{{ option.value }}</span>
                                <span class="bg-[var(--mat-sys-surface-variant)] px-1.5 py-0.5 rounded text-xs opacity-60">{{ option.count }}</span>
                              </button>
                            }
                          </div>
                        }
                      </div>
                    </div>
                  </aside>

                  <!-- Main Grid -->
                  <div class="flex-1 overflow-auto pr-2">
                    <!-- Recents -->
                    @if (recentProtocols().length > 0 && !searchQuery()) {
                      <div class="mb-8">
                        <h3 class="text-sys-text-primary text-lg font-medium mb-4 flex items-center gap-2">
                          <mat-icon class="text-primary/70">history</mat-icon> Recently Used
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          @for (protocol of recentProtocols(); track protocol.accession_id) {
                            <app-protocol-card
                              [protocol]="protocol"
                              [compact]="true"
                              (select)="selectProtocol($event)"
                              class="transform hover:-translate-y-1 transition-transform duration-300"
                            />
                          }
                        </div>
                      </div>
                    }

                    <!-- All Protocols -->
                    <div>
                      <h3 class="text-sys-text-primary text-lg font-medium mb-4 flex items-center gap-2">
                        <mat-icon class="text-primary/70">grid_view</mat-icon> All Protocols
                      </h3>
                      
                      @if (isLoading()) {
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          @for (i of [1, 2, 3, 4, 5, 6]; track i) {
                            <app-protocol-card-skeleton />
                          }
                        </div>
                      } @else if (filteredProtocols().length === 0) {
                        <div class="flex flex-col items-center justify-center py-20 text-sys-text-tertiary">
                          <mat-icon class="!w-16 !h-16 !text-[64px] opacity-20 mb-4">search_off</mat-icon>
                          <p class="text-lg">No protocols found matching your criteria</p>
                          <button mat-button class="mt-4 !text-primary" (click)="clearSearch()">Clear Filters</button>
                        </div>
                      } @else {
                        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-8">
                          @for (protocol of filteredProtocols(); track protocol.accession_id) {
                            <app-protocol-card
                              [protocol]="protocol"
                              (select)="selectProtocol($event)"
                              class="transform hover:-translate-y-1 transition-transform duration-300"
                            />
                          }
                        </div>
                      }
                    </div>
                  </div>
                </div>
              }
            </form>
          </mat-step>

          <!-- Step 2: Configure Parameters -->
          <mat-step [stepControl]="parametersFormGroup">
            <ng-template matStepLabel><span data-tour-id="run-step-label-params">Configure Parameters</span></ng-template>
            <form [formGroup]="parametersFormGroup" class="h-full flex flex-col p-6" data-tour-id="run-step-params">
              <div class="flex-1 overflow-y-auto max-w-3xl mx-auto w-full">
                <div class="bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] rounded-2xl p-8">
                  <h3 class="text-xl font-bold text-sys-text-primary mb-6 flex items-center gap-3">
                    <div class="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
                      <mat-icon>tune</mat-icon>
                    </div>
                    Protocol Parameters
                  </h3>
                  
                  <app-parameter-config
                    [protocol]="selectedProtocol()"
                    [formGroup]="parametersFormGroup">
                  </app-parameter-config>
                </div>
              </div>

              <div class="wizard-footer mt-6 flex justify-between">
                <button mat-button matStepperPrevious class="!text-sys-text-secondary">Back</button>
                <button mat-flat-button color="primary" matStepperNext [disabled]="parametersFormGroup.invalid" class="!rounded-xl !px-8 !py-6">Continue</button>
              </div>
            </form>
          </mat-step>

          <!-- Step 3: Machine Selection -->
          <mat-step [stepControl]="machineFormGroup">
            <ng-template matStepLabel><span data-tour-id="run-step-label-machine">Select Machines</span></ng-template>
            <div class="h-full flex flex-col p-6" data-tour-id="run-step-machine">
              <div class="flex-1 overflow-y-auto">
                <h3 class="text-xl font-bold text-sys-text-primary mb-6 flex items-center gap-3">
                   <div class="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
                     <mat-icon>precision_manufacturing</mat-icon>
                   </div>
                   Select Execution Machines
                   <span class="flex-1"></span>
                   <app-hardware-discovery-button></app-hardware-discovery-button>
                </h3>

                @if (showMachineError()) {
                  <div class="mb-6 p-4 status-error-bg rounded-2xl flex items-start gap-3 animate-in fade-in slide-in-from-top-2 duration-300">
                    <mat-icon class="status-error-text mt-0.5">error_outline</mat-icon>
                    <div>
                      <p class="status-error-text font-bold">Physical execution requires real machines.</p>
                      <p class="status-error-text opacity-80 text-sm">Some selected machines are simulated. Switch to Simulation mode or select physical machines.</p>
                    </div>
                  </div>
                }

                @if (isLoadingCompatibility()) {
                  <div class="flex flex-col items-center justify-center py-12">
                    <mat-spinner diameter="40"></mat-spinner>
                    <p class="mt-4 text-sys-text-tertiary">Loading machine options...</p>
                  </div>
                } @else {
                  <!-- NEW: Per-argument machine selector -->
                  <app-machine-argument-selector
                    [requirements]="selectedProtocol()?.assets || []"
                    [simulationMode]="store.simulationMode()"
                    (selectionsChange)="machineSelections.set($event)"
                    (validChange)="machineSelectionsValid.set($event); machineFormGroup.get('machineId')?.setValue($event ? 'valid' : '')"
                  ></app-machine-argument-selector>

                  <!-- Keep old selector as fallback for backwards compat, hidden -->
                  @if (false) {
                    <app-machine-selection
                      [machines]="compatibilityData()"
                      [selected]="selectedMachine()"
                      [isPhysicalMode]="!store.simulationMode()"
                      (select)="onMachineSelect($event)"
                    ></app-machine-selection>
                  }
                }
              </div>

              <div class="wizard-footer mt-6 flex justify-between">
                 <button mat-button matStepperPrevious class="!text-sys-text-secondary">Back</button>
                 <button mat-flat-button color="primary" matStepperNext [disabled]="!machineSelectionsValid() || showMachineError()" class="!rounded-xl !px-8 !py-6">Continue</button>
              </div>
            </div>
          </mat-step>

          <!-- Step 4: Asset Selection -->
          <mat-step [stepControl]="assetsFormGroup">
             <ng-template matStepLabel><span data-tour-id="run-step-label-assets">Select Assets</span></ng-template>
             <div class="h-full flex flex-col p-6" data-tour-id="run-step-assets">
               <div class="flex-1 overflow-y-auto">
                 <h3 class="text-xl font-bold text-sys-text-primary mb-6 flex items-center gap-3">
                    <div class="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
                      <mat-icon>inventory_2</mat-icon>
                    </div>
                    Asset Selection
                 </h3>

                 @if (selectedProtocol()) {
                    <app-guided-setup 
                      [protocol]="selectedProtocol()" 
                      [isInline]="true"
                      [simulationMode]="store.simulationMode()"
                      [excludeAssetIds]="excludedMachineAssetIds()"
                      [initialSelections]="configuredAssets() || {}"
                      (selectionChange)="onAssetSelectionChange($event)">
                    </app-guided-setup>
                 }
               </div>

               <div class="wizard-footer mt-6 flex justify-between">
                  <button mat-button matStepperPrevious class="!text-sys-text-secondary">Back</button>
                  <button mat-flat-button color="primary" matStepperNext [disabled]="assetsFormGroup.invalid" class="!rounded-xl !px-8 !py-6">Continue</button>
               </div>
             </div>
          </mat-step>

          <!-- Step 5: Well Selection (Conditional) -->
          @if (wellSelectionRequired()) {
            <mat-step [stepControl]="wellsFormGroup">
              <ng-template matStepLabel>
                <span data-tour-id="run-step-label-wells">Select Wells</span>
              </ng-template>
              <div class="h-full flex flex-col p-6" data-tour-id="run-step-wells">
                <div class="flex-1 overflow-y-auto">
                  <h3 class="text-xl font-bold text-sys-text-primary mb-6 flex items-center gap-3">
                    <div class="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
                      <mat-icon>grid_on</mat-icon>
                    </div>
                    Well Selection
                  </h3>
                  
                  <p class="text-sys-text-secondary mb-6">
                    This protocol requires you to specify which wells to use. Click each parameter below to select wells.
                  </p>
                  
                  @for (param of getWellParameters(); track param.name) {
                    <div class="mb-6 p-4 bg-surface-variant rounded-xl">
                      <div class="flex items-center justify-between mb-2">
                        <span class="font-medium">{{ param.name }}</span>
                        <span class="text-sm text-sys-text-tertiary">{{ param.description }}</span>
                      </div>
                      <button mat-stroked-button (click)="openWellSelector(param)" class="w-full !justify-start" data-testid="well-selection-button">
                        <mat-icon class="mr-2">grid_on</mat-icon>
                        {{ getWellSelectionLabel(param.name) }}
                      </button>
                    </div>
                  }
                </div>
                
                <div class="wizard-footer mt-6 flex justify-between">
                  <button mat-button matStepperPrevious class="!text-sys-text-secondary">Back</button>
                  <button mat-flat-button color="primary" matStepperNext 
                          [disabled]="!areWellSelectionsValid()" 
                          class="!rounded-xl !px-8 !py-6">
                    Continue
                  </button>
                </div>
              </div>
            </mat-step>
          }

          <!-- Step 6: Deck Setup (Inline Wizard) - Skipped for no-deck protocols -->
          <mat-step [stepControl]="deckFormGroup" [optional]="selectedProtocol()?.requires_deck === false">
            <ng-template matStepLabel><span data-tour-id="run-step-label-deck">Deck Setup</span></ng-template>
            <div class="h-full flex flex-col" data-tour-id="run-step-deck">
              @if (selectedProtocol()?.requires_deck === false) {
                <!-- No deck required - show skip message -->
                <div class="flex flex-col items-center justify-center h-full text-sys-text-tertiary">
                  <div class="w-16 h-16 rounded-full status-success-bg flex items-center justify-center mb-4">
                    <mat-icon class="!w-8 !h-8 !text-[32px] status-success">check_circle</mat-icon>
                  </div>
                  <h3 class="text-lg font-medium text-sys-text-primary mb-2">No Deck Setup Required</h3>
                  <p class="text-sys-text-secondary mb-6 max-w-md text-center">
                    This protocol operates on standalone machines and does not require deck configuration.
                  </p>
                  <div class="flex gap-4">
                    <button mat-button matStepperPrevious class="!border-[var(--theme-border)] !rounded-xl !px-6 !py-6">Back</button>
                    <button mat-flat-button color="primary" matStepperNext class="!rounded-xl !px-8 !py-6">Continue to Review</button>
                  </div>
                </div>
              } @else if (selectedProtocol()) {
                <app-deck-setup-wizard
                  [data]="{ protocol: selectedProtocol()!, deckResource: deckData()?.resource || null, assetMap: configuredAssets() || {}, deckType: selectedDeckType() || 'HamiltonSTARDeck' }" 
                  (setupComplete)="onDeckSetupComplete()"
                  (setupSkipped)="onDeckSetupSkipped()">
                </app-deck-setup-wizard>
              } @else {
                <div class="flex flex-col items-center justify-center h-full text-sys-text-tertiary">
                  <mat-icon class="!w-16 !h-16 !text-[64px] opacity-20 mb-4">build</mat-icon>
                  <p>Select a protocol first to configure the deck.</p>
                </div>
              }
            </div>
          </mat-step>

          <!-- Step 6: Review & Run -->
          <mat-step [stepControl]="readyFormGroup" label="Review & Run">
             <div class="h-full flex flex-col items-center p-6 text-center max-w-2xl mx-auto overflow-y-auto">
               <div class="my-auto w-full">
               <div class="w-24 h-24 rounded-full bg-primary/20 flex items-center justify-center text-primary mb-6 shadow-[0_0_30px_rgba(237,122,155,0.3)]">
                 <mat-icon class="!w-12 !h-12 !text-[48px]">rocket_launch</mat-icon>
               </div>
               
               <h2 class="text-4xl font-bold text-sys-text-primary mb-2">Ready to Launch</h2>
               <p class="text-xl text-sys-text-secondary mb-12">Confirm execution parameters before starting</p>
               
                <div class="grid grid-cols-2 gap-4 w-full mb-8">
                   <div class="bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] rounded-2xl p-6 flex flex-col items-center">
                      <span class="text-sys-text-tertiary text-sm uppercase tracking-wider font-bold mb-2">Protocol</span>
                      <span class="text-sys-text-primary text-lg font-medium" data-testid="review-protocol-name">{{ selectedProtocol()?.name }}</span>
                   </div>
                                   <div class="bg-[var(--mat-sys-surface-variant)] border border-[var(--theme-border)] rounded-2xl p-6 flex flex-col items-center">
                      <span class="text-sys-text-tertiary text-sm uppercase tracking-wider font-bold mb-2">Mode</span>
                     <span class="text-lg font-medium" [class.text-primary]="store.simulationMode()" [class.text-tertiary]="!store.simulationMode()">
                       {{ store.simulationMode() ? 'Simulation' : 'Physical Run' }}
                     </span>
                  </div>
                </div>

                <!-- Protocol Summary -->
                <div class="w-full mb-8 text-left">
                  <app-protocol-summary
                    [protocol]="selectedProtocol()"
                    [parameters]="parametersFormGroup.value"
                    [assets]="configuredAssets() || {}"
                    [wellSelections]="wellSelections()"
                    [wellSelectionRequired]="wellSelectionRequired()">
                  </app-protocol-summary>
                </div>


                <!-- Name & Notes Section -->
                <div class="w-full max-w-2xl mb-8 space-y-4">
                  <mat-form-field appearance="outline" class="w-full">
                    <mat-label>Run Name</mat-label>
                    <input matInput 
                           [formControl]="runNameControl" 
                           placeholder="e.g., Pilot Study - Batch 3"
                           required>
                    <mat-hint>Give this run a descriptive name</mat-hint>
                    @if (runNameControl.hasError('required')) {
                      <mat-error>Run name is required</mat-error>
                    }
                  </mat-form-field>
                  
                  <mat-form-field appearance="outline" class="w-full">
                    <mat-label>Notes (Optional)</mat-label>
                    <textarea matInput 
                              [formControl]="runNotesControl"
                              rows="3"
                              placeholder="Document experimental conditions, operator notes, etc."></textarea>
                  </mat-form-field>
                </div>
               <div class="wizard-footer flex gap-4 w-full justify-center mt-auto">
                  <button mat-button matStepperPrevious class="!border-[var(--theme-border)] !text-sys-text-secondary !rounded-xl !px-8 !py-6 w-40 border">Back</button>
                  
                  <!-- Schedule Button -->
                  <button mat-stroked-button color="primary" 
                    class="!rounded-xl !px-6 !py-6 !font-bold !text-lg w-48 !border-primary/50"
                    [disabled]="modeService.isBrowserMode() || isStartingRun() || executionService.isRunning()"
                    [matTooltip]="modeService.isBrowserMode() ? 'Scheduling is not supported in browser mode' : 'Schedule this protocol for later'"
                    [matTooltipShowDelay]="600"
                    matTooltipPosition="above">
                    <div class="flex items-center gap-2">
                      <mat-icon>calendar_today</mat-icon>
                      Schedule
                    </div>
                  </button>
                  
                  <button mat-raised-button class="bg-gradient-success !text-white !rounded-xl !px-8 !py-6 !font-bold !text-lg w-64 shadow-success hover:shadow-success-hover hover:-translate-y-0.5 transition-all" (click)="startRun()"
                    [disabled]="isStartingRun() || executionService.isRunning() || !configuredAssets() || !machineSelectionsValid() || showMachineError()">

                    @if (isStartingRun()) {
                      <mat-spinner diameter="24" class="mr-2"></mat-spinner>
                      Initializing...
                    } @else {
                      <div class="flex items-center gap-2">
                        <mat-icon>play_circle</mat-icon>
                        Start Execution
                      </div>
                    }
                  </button>
               </div>
             </div>
             </div>
          </mat-step>
        </mat-stepper>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
      height: 100%;
    }
    
    /* Utilities */
    .bg-primary-10 { background-color: rgba(var(--primary-color-rgb), 0.1); }
    .text-white-70 { color: var(--theme-text-secondary); }
    .text-tertiary { color: var(--tertiary-color); }

    .border-theme-status-success { border-color: var(--theme-status-success-border) !important; }
    .bg-theme-status-success-muted { background-color: var(--theme-status-success-muted) !important; }
    .text-theme-status-success { color: var(--theme-status-success) !important; }

    .bg-gradient-success {
      background: var(--gradient-success);
    }
    .shadow-success {
      box-shadow: 0 4px 6px -1px var(--theme-status-success-muted), 0 2px 4px -1px var(--theme-status-success-muted);
    }
    .shadow-success-hover {
       box-shadow: 0 10px 15px -3px var(--theme-status-success-border), 0 4px 6px -2px var(--theme-status-success-border);
    }


    /* Protocol description scrollable container */
    .description-container {
      max-height: 200px;
      overflow-y: auto;
      margin: 16px 0;
      padding-right: 8px;
    }

    /* Fix Stepper Content Scrolling - MDC Classes */
    ::ng-deep .mat-horizontal-stepper-wrapper {
      flex: 1 1 auto;
      display: flex;
      flex-direction: column;
      height: 100%;
      min-height: 0;
    }

    ::ng-deep .mat-horizontal-content-container {
      flex: 1 1 auto;
      height: 100%;
      min-height: 0;
      padding: 0 !important;
      overflow: hidden !important;
    }

    /* Active Step Content */
    ::ng-deep .mat-horizontal-stepper-content.mat-horizontal-stepper-content-current {
      height: 100% !important;
      display: flex !important;
      flex-direction: column !important;
      min-height: 0 !important;
      flex: 1 1 auto !important;
      /* Ensure overflow is visible for the active step so Playwright can see it */
      overflow: visible !important;
      visibility: visible !important;
      opacity: 1 !important;
    }

    /* Inactive Step Content: Hide everything else */
    ::ng-deep .mat-horizontal-stepper-content:not(.mat-horizontal-stepper-content-current) {
      height: 0 !important;
      overflow: hidden !important;
      visibility: hidden !important;
      display: none !important;
    }

    /* Stepper Overrides */
    ::ng-deep .mat-step-header {
      border-radius: 12px;
      transition: background 0.2s;
      padding: 12px 24px !important;
    }
    ::ng-deep .mat-step-header:hover {
      background: var(--mat-sys-surface-variant);
    }
    ::ng-deep .mat-step-label {
      color: var(--theme-text-secondary) !important;
      font-size: 0.85rem !important;
      white-space: nowrap !important;
      overflow: hidden !important;
      text-overflow: ellipsis !important;
      line-height: 1.3 !important;
    }

    /* Sticky action bar for wizard footer */
    .wizard-footer {
      position: sticky;
      bottom: 0;
      background: var(--mat-sys-surface);
      border-top: 1px solid var(--mat-sys-outline-variant);
      padding: 16px;
      z-index: 20;
    }

    /* Better focus state for form controls in dark mode */
    ::ng-deep .mat-mdc-form-field.mat-focused {
      .mdc-notched-outline__leading,
      .mdc-notched-outline__notch,
      .mdc-notched-outline__trailing {
        border-color: var(--mat-sys-primary) !important;
        border-width: 2px !important;
      }
    }
    ::ng-deep .mat-step-label-selected {
      color: var(--theme-text-primary) !important;
      font-weight: 600 !important;
    }
    ::ng-deep .mat-step-icon {
      background-color: var(--mat-sys-surface-variant) !important;
      color: var(--theme-text-secondary) !important; /* Ensure number is readable */
    }
    ::ng-deep .mat-step-icon-selected {
      background-color: var(--primary-color) !important;
      color: white !important; /* White text on primary color */
    }
    ::ng-deep .mat-step-icon-content {
      /* Ensure the inner text (number) inherits the color correctly */
      color: inherit !important; 
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RunProtocolComponent implements OnInit, HasUnsavedChanges {
  @ViewChild('stepper') set stepperRef(v: MatStepper) {
    if (v) {
      this.stepper = v;
      // Auto-save on step change
      v.selectionChange.subscribe(() => this.saveStateToStorage());
    }
  }
  stepper!: MatStepper;
  private _formBuilder = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private protocolService = inject(ProtocolService);
  public executionService = inject(ExecutionService);
  private deckGenerator = inject(DeckGeneratorService);
  private dialog = inject(MatDialog);
  public modeService = inject(ModeService);
  private assetService = inject(AssetService);
  private snackBar = inject(MatSnackBar);

  // Signals
  protocols = signal<ProtocolDefinition[]>([]);
  selectedProtocol = signal<ProtocolDefinition | null>(null);
  selectedMachine = signal<MachineCompatibility | null>(null);
  machineSelections = signal<MachineArgumentSelection[]>([]);  // NEW: Per-argument selections
  compatibilityData = signal<MachineCompatibility[]>([]);
  isLoadingCompatibility = signal(false);
  machineSelectionsValid = signal(false);  // NEW: Validation state from selector

  isLoading = signal(true);
  isStartingRun = signal(false);
  searchQuery = signal('');
  activeFilters = signal<Record<string, Set<string>>>({});
  configuredAssets = signal<Record<string, any> | null>(null);

  protocolFormGroup = this._formBuilder.group({ protocolId: ['', { validators: (c: any) => c.value ? null : { required: true } }] });
  machineFormGroup = this._formBuilder.group({ machineId: ['', { validators: (c: any) => c.value && !this.showMachineError() ? null : { required: true } }] });
  parametersFormGroup = this._formBuilder.group({});
  assetsFormGroup = this._formBuilder.group({ valid: [false, { validators: (c: any) => c.value ? null : { required: true } }] });
  wellsFormGroup = this._formBuilder.group({ valid: [true] });  // Optional by default, validated when wells required
  deckFormGroup = this._formBuilder.group({ valid: [false, { validators: (c: any) => c.value || this.selectedProtocol()?.requires_deck === false ? null : { required: true } }] });
  readyFormGroup = this._formBuilder.group({ ready: [true] });

  // Run name and notes form controls
  runNameControl = this._formBuilder.control('', { validators: (c: any) => c.value ? null : { required: true } });
  runNotesControl = this._formBuilder.control('');

  // Well selection state
  wellSelectionRequired = computed(() => {
    const protocol = this.selectedProtocol();
    // Trigger if parameters indicate wells
    return protocol?.parameters?.some(p => this.isWellSelectionParameter(p)) ?? false;
  });
  wellSelections = signal<Record<string, string[]>>({});

  hasUnsavedChanges(): boolean {
    // Only block if a protocol is selected and we haven't successfully started a run
    return !!this.selectedProtocol() && !this.isStartingRun();
  }

  // Compute asset IDs that should be excluded from GuidedSetup (because they are machines)
  excludedMachineAssetIds = computed(() => {
    const protocol = this.selectedProtocol();
    if (!protocol || !protocol.assets) return [];

    // Identify machine requirements using the same logic as the machine selector
    return protocol.assets
      .filter(req => {
        const catStr = (req.required_plr_category || '');
        const typeHint = (req.type_hint_str || '').toLowerCase();

        // Match logic from MachineArgumentSelectorComponent.isMachineRequirement
        if (MACHINE_CATEGORIES.has(catStr as PLRCategory)) {
          return true;
        }

        const lowerCat = catStr.toLowerCase();
        if (lowerCat.includes('plate') || lowerCat.includes('tip') || lowerCat.includes('trough') ||
          lowerCat.includes('reservoir') || lowerCat.includes('carrier') || lowerCat.includes('tube')) {
          return false;
        }

        return typeHint.includes('liquidhandler') || typeHint.includes('platereader') ||
          typeHint.includes('shaker') || typeHint.includes('centrifuge') ||
          typeHint.includes('incubator') || typeHint.includes('heater') || typeHint.includes('scara');
      })
      .map(req => req.accession_id || '');
  });

  constructor() {
    // Snap-back to Machine Selection step (index 2) if mode change invalidates selections
    effect(() => {
      const error = this.showMachineError();
      const valid = this.machineSelectionsValid();
      const currentStep = this.stepper?.selectedIndex;

      // If error exists or selections are invalid, and we are past the machine selection step (step 3, index 2)
      if ((error || !valid) && currentStep > 2) {
        // Use a small timeout to ensure stepper is ready and avoid expression changed error
        setTimeout(() => {
          if (this.stepper) {
            this.stepper.selectedIndex = 2; // Return to Select Machines
            this.snackBar.open('Environment mode changed. Please re-verify machines.', 'OK', { duration: 5000 });
          }
        }, 100);
      }
    });

    // Auto-save state when relevant data changes (Hydration Support)
    effect(() => {
      // Access signals to trigger effect
      this.selectedProtocol();
      this.machineSelections();
      this.configuredAssets();
      this.wellSelections();
      this.runNameControl.value;
      this.runNotesControl.value;
      this.store.simulationMode();

      this.saveStateToStorage();
    });
  }

  private saveStateToStorage() {
    if (!this.selectedProtocol() || this.isStartingRun()) {
      // If no protocol or starting run, we don't need to keep setup state
      // (starting run clears it anyway in subscribe)
      return;
    }

    try {
      const state = {
        protocolId: this.selectedProtocol()?.accession_id,
        parameters: this.parametersFormGroup.value,
        machineSelections: this.machineSelections(),
        configuredAssets: this.configuredAssets(),
        wellSelections: this.wellSelections(),
        stepperIndex: this.stepper?.selectedIndex || 0,
        runName: this.runNameControl.value,
        runNotes: this.runNotesControl.value,
        simulationMode: this.store.simulationMode()
      };
      localStorage.setItem(WIZARD_STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      console.warn('[RunProtocol] Failed to save state', e);
    }
  }

  private loadStateFromStorage(): boolean {
    try {
      const stored = localStorage.getItem(WIZARD_STORAGE_KEY);
      if (!stored) return false;

      const state = JSON.parse(stored);
      if (!state.protocolId) return false;

      const protocol = this.protocols().find(p => p.accession_id === state.protocolId);
      if (!protocol) return false;

      console.log('[RunProtocol] Hydrating state from Storage for protocol:', protocol.name);

      // 1. Restore protocol (this resets forms, so we do it first)
      this.selectProtocol(protocol);

      // 2. Restore other states
      if (state.parameters) {
        this.parametersFormGroup.patchValue(state.parameters);
      }
      if (state.machineSelections) {
        this.machineSelections.set(state.machineSelections);
        // If selections exist, mark form as valid
        const isValid = !!state.machineSelections.length;
        this.machineSelectionsValid.set(isValid);
        this.machineFormGroup.get('machineId')?.setValue(isValid ? 'valid' : '');
      }
      if (state.configuredAssets) {
        this.configuredAssets.set(state.configuredAssets);
        this.assetsFormGroup.patchValue({ valid: this.canProceedFromAssetSelection() });
      }
      if (state.wellSelections) {
        this.wellSelections.set(state.wellSelections);
        this.validateWellSelections();
      }
      if (state.runName) this.runNameControl.setValue(state.runName);
      if (state.runNotes) this.runNotesControl.setValue(state.runNotes);
      if (state.simulationMode !== undefined) this.store.setSimulationMode(state.simulationMode);

      // 3. Restore Stepper index after a short delay
      if (state.stepperIndex > 0) {
        setTimeout(() => {
          if (this.stepper) {
            this.stepper.selectedIndex = state.stepperIndex;
          }
        }, 100);
      }

      return true;
    } catch (e) {
      console.warn('[RunProtocol] Failed to load state', e);
      return false;
    }
  }

  /** Helper to check if a machine is simulated */
  isMachineSimulated = computed(() => {
    const selection = this.selectedMachine();
    if (!selection) return false;

    const machine = selection.machine;

    // NEW: Check backend_definition.backend_type
    if (machine.backend_definition?.backend_type === 'simulator') {
      return true;
    }

    const connectionInfo = machine.connection_info || {};
    const backend = (connectionInfo['backend'] || '').toString();

    // Legacy fallback
    return machine.is_simulation_override === true ||
      (machine as any).is_simulated === true ||
      backend.includes('Simulator') ||
      backend.includes('simulation') ||
      backend.includes('Chatterbox');
  });

  /** Whether to show the machine validation error */
  showMachineError = computed(() => {
    // In simulation mode, never show error
    if (this.store.simulationMode()) return false;

    // Check if any selected machine/backend in machineSelections is simulated
    const selections = this.machineSelections();
    if (!selections || selections.length === 0) return false;

    return selections.some(sel => {
      // If a backend template was selected, check its type
      if (sel.selectedBackend) {
        return sel.selectedBackend.backend_type === 'simulator';
      }
      // If an existing machine was selected, check its backend
      if (sel.selectedMachine) {
        const machine = sel.selectedMachine;
        if (machine.backend_definition?.backend_type === 'simulator') return true;
        // Fallback: check connection_info for backend hints
        const connectionInfo = machine.connection_info || {};
        const backend = (connectionInfo['backend'] || '').toString().toLowerCase();
        return backend.includes('chatterbox') || backend.includes('simulation');
      }
      return false;
    });
  });

  onAssetSelectionChange(assetMap: Record<string, any>) {
    this.configuredAssets.set(assetMap);
    const valid = this.canProceedFromAssetSelection();
    this.assetsFormGroup.patchValue({ valid });
  }

  canProceedFromAssetSelection(): boolean {
    const protocol = this.selectedProtocol();
    if (!protocol || !protocol.assets) return true;

    // Get list of machine asset IDs that are handled in the machine selection step
    const excludedIds = new Set(this.excludedMachineAssetIds());

    // Check if configuredAssets contains all required non-machine assets
    // Machine assets are handled separately by MachineArgumentSelector
    const currentAssets = this.configuredAssets() || {};
    return protocol.assets
      .filter(req => !excludedIds.has(req.accession_id || ''))
      .every(req => req.optional || !!currentAssets[req.accession_id]);
  }

  // Computed Deck Data
  deckData = computed(() => {
    const protocol = this.selectedProtocol();
    const machineCompat = this.selectedMachine();
    if (!protocol) return null;
    return this.deckGenerator.generateDeckForProtocol(
      protocol,
      this.configuredAssets() || undefined,
      machineCompat?.machine
    );
  });

  private isBrowserModeActive(): boolean {
    if (this.modeService.isBrowserMode()) return true;

    if (typeof window !== 'undefined') {
      const modeParam = new URLSearchParams(window.location.search).get('mode');
      if (modeParam === 'browser') return true;
    }

    try {
      const stored = localStorage.getItem('praxis_mode_override');
      if (stored === 'browser') return true;
    } catch {
      // Ignore storage failures in restricted environments
    }

    return false;
  }

  // Inject global store for simulation mode
  store = inject(AppStore);

  // WizardStateService for inline deck setup
  wizardState = inject(WizardStateService);
  private deckCatalog = inject(DeckCatalogService);

  /** Computed deck type for the selected machine */
  selectedDeckType = computed(() => {
    const machine = this.selectedMachine()?.machine;
    return this.deckCatalog.getDeckTypeForMachine(machine);
  });

  /** Called when inline deck setup wizard completes */
  onDeckSetupComplete() {
    // Get asset map from wizard state
    const assetMap = this.wizardState.getAssetMap();
    this.configuredAssets.set(assetMap);
    this.deckFormGroup.patchValue({ valid: true });

    // Auto-advance to verification step
    setTimeout(() => {
      this.stepper.next();
    }, 0);
  }

  /** Called when inline deck setup wizard is skipped */
  onDeckSetupSkipped() {
    // Allow proceeding even if skipped. 
    // We keep the configuredAssets from the Asset Selection step (Step 4).
    this.deckFormGroup.patchValue({ valid: true });

    // Auto-advance to verification step
    setTimeout(() => {
      this.stepper.next();
    }, 0);
  }

  // Computed
  recentProtocols = computed(() => {
    const recentIds = this.getRecentIds();
    const allProtocols = this.protocols();
    return recentIds
      .map(id => allProtocols.find(p => p.accession_id === id))
      .filter((p): p is ProtocolDefinition => p !== undefined);
  });

  filterCategories = computed<FilterCategory[]>(() => {
    const allProtocols = this.protocols();
    const active = this.activeFilters();

    // Build category filter
    const categoryMap = new Map<string, number>();
    allProtocols.forEach(p => {
      const cat = p.category || 'Uncategorized';
      categoryMap.set(cat, (categoryMap.get(cat) || 0) + 1);
    });

    const categoryOptions: FilterOption[] = Array.from(categoryMap.entries())
      .map(([value, count]) => ({
        value,
        count,
        selected: active['category']?.has(value) || false,
      }))
      .sort((a, b) => b.count - a.count);

    // Build is_top_level filter
    const topLevelCount = allProtocols.filter(p => p.is_top_level).length;
    const subCount = allProtocols.length - topLevelCount;
    const typeOptions: FilterOption[] = [
      { value: 'Top Level', count: topLevelCount, selected: active['type']?.has('Top Level') || false },
      { value: 'Sub-Protocol', count: subCount, selected: active['type']?.has('Sub-Protocol') || false },
    ].filter(o => o.count > 0);

    return [
      { key: 'category', label: 'Category', options: categoryOptions, expanded: true },
      { key: 'type', label: 'Type', options: typeOptions, expanded: false },
    ].filter(c => c.options.length > 0);
  });

  filteredProtocols = computed(() => {
    let result = this.protocols();
    const query = this.searchQuery().toLowerCase().trim();
    const active = this.activeFilters();

    // Apply search filter
    if (query) {
      result = result.filter(p =>
        p.name.toLowerCase().includes(query) ||
        (p.description?.toLowerCase().includes(query)) ||
        (p.category?.toLowerCase().includes(query))
      );
    }

    // Apply category filter
    if (active['category']?.size) {
      result = result.filter(p => active['category'].has(p.category || 'Uncategorized'));
    }

    // Apply type filter
    if (active['type']?.size) {
      result = result.filter(p => {
        const isTop = active['type'].has('Top Level') && p.is_top_level;
        const isSub = active['type'].has('Sub-Protocol') && !p.is_top_level;
        return isTop || isSub;
      });
    }

    return result;
  });

  ngOnInit() {
    this.loadProtocols();

    // Check for pre-selected protocol from query params
    this.route.queryParams.subscribe((params: any) => {
      const protocolId = params['protocolId'];
      if (protocolId) {
        this.loadProtocolById(protocolId);
      }
    });
  }

  loadProtocols() {
    this.isLoading.set(true);
    console.log('[RunProtocol] Loading protocols...');
    this.protocolService.getProtocols().pipe(
      finalize(() => {
        this.isLoading.set(false);
        console.log('[RunProtocol] Protocol load finished. isLoading=false');
      })
    ).subscribe({
      next: (protocols) => {
        console.log(`[RunProtocol] Received ${protocols?.length || 0} protocols`);
        this.protocols.set(protocols);

        // Priority 1: Hydrate from Storage
        if (this.loadStateFromStorage()) {
          console.log('[RunProtocol] Loaded state from storage.');
          return;
        }

        // Priority 2: Check for pre-selected from query
        const protocolId = this.route.snapshot.queryParams['protocolId'];
        if (protocolId) {
          this.loadProtocolById(protocolId);
        }
      },
      error: (err) => console.error('Failed to load protocols', err)
    });
  }

  loadProtocolById(id: string) {
    const found = this.protocols().find(p => p.accession_id === id);
    if (found) {
      this.selectProtocol(found);
    }
  }

  selectProtocol(protocol: ProtocolDefinition) {
    this.selectedProtocol.set(protocol);
    this.configuredAssets.set(null); // Reset deck config

    // Create form controls for parameters to support hydration and validation
    const group: any = {};
    if (protocol.parameters) {
      protocol.parameters.forEach(p => {
        group[p.name] = [p.default_value_repr ?? ''];
      });
    }
    this.parametersFormGroup = this._formBuilder.group(group);

    // Auto-generate default run name
    const date = new Date().toISOString().split('T')[0];
    const defaultName = `${protocol.name} - ${date}`;
    this.runNameControl.setValue(defaultName);

    // Create form controls for parameters
    if (protocol.parameters) {
      // This block's content was not provided in the instruction,
      // so it remains empty as per the instruction's snippet.
    }
    this.protocolFormGroup.patchValue({ protocolId: protocol.accession_id });

    this.assetsFormGroup.patchValue({ valid: false });
    this.deckFormGroup.patchValue({ valid: protocol.requires_deck === false });

    // Always load compatibility to show templates or machines
    this.loadCompatibility(protocol.accession_id);

    // Sync to URL
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { protocolId: protocol.accession_id },
      queryParamsHandling: 'merge'
    });
  }

  loadCompatibility(protocolId: string) {
    this.isLoadingCompatibility.set(true);

    // Fetch both compatibility and machine definitions to show "Templates"
    this.executionService.getCompatibility(protocolId).pipe(
      switchMap(compatData => {
        return this.assetService.getMachineDefinitions().pipe(
          map((definitions: MachineDefinition[]) => {
            const existingIds = new Set(compatData.map(d => (d.machine as any).machine_definition_accession_id));

            const templates: MachineCompatibility[] = definitions
              .filter(def => !existingIds.has(def.accession_id))
              .map(def => ({
                machine: {
                  accession_id: `template-${def.accession_id}`,
                  name: def.name,
                  machine_category: def.machine_category,
                  is_simulation_override: true,
                  simulation_backend_name: (def.available_simulation_backends?.[0]) || 'Chatterbox',
                  description: def.description,
                  machine_definition_accession_id: def.accession_id,
                  is_template: true
                } as any,
                compatibility: {
                  is_compatible: true,
                  missing_capabilities: [],
                  matched_capabilities: [],
                  warnings: []
                }
              }));

            return [...compatData, ...templates];
          })
        );
      }),
      finalize(() => this.isLoadingCompatibility.set(false))
    ).subscribe({
      next: (data) => {
        let allCompat = data as MachineCompatibility[];
        const protocol = this.selectedProtocol();

        // Filter based on protocol requirements (Frontend filtering)
        if (protocol) {
          console.log('[RunProtocol] Debug Machine Filtering:', {
            protocolName: protocol.name,
            requiresDeck: protocol.requires_deck,
            assets: protocol.assets?.map(a => ({ name: a.name, cat: a.required_plr_category, hint: a.type_hint_str })),
            allCompatLength: allCompat.length,
            allCompatNames: allCompat.map(c => c.machine.name)
          });

          // Identify required machine categories from assets
          const requiredCategories = new Set<string>();
          const machineAssets = protocol.assets?.filter(a => a.required_plr_category && !a.required_plr_category.includes('plate') && !a.required_plr_category.includes('tip_rack')) || [];

          machineAssets.forEach(a => {
            // Extract simple category from type_hint or category
            if (a.required_plr_category) requiredCategories.add(a.required_plr_category.toLowerCase());
            // Also add common aliases
            if (a.type_hint_str?.includes('LiquidHandler')) requiredCategories.add('liquidhandler');
            if (a.type_hint_str?.includes('PlateReader')) requiredCategories.add('platereader');
          });

          console.log('[RunProtocol] Required Categories:', Array.from(requiredCategories));

          // Default to LiquidHandler if nothing specific found but deck is required
          if (requiredCategories.size === 0 && protocol.requires_deck !== false) {
            console.log('[RunProtocol] Defaulting to LiquidHandler (deck required, no specific machine categories)');
            requiredCategories.add('liquidhandler');
          }

          if (requiredCategories.size > 0) {
            allCompat = allCompat.filter(d => {
              const cat = (d.machine.machine_category || '').toLowerCase();
              // Normalized category matching - check base category names
              const normalizedCat = cat.replace(/[_\-\s]/g, '');
              const matchesCategory = requiredCategories.has(normalizedCat) ||
                // Common liquid handler variants
                (requiredCategories.has('liquidhandler') && (
                  normalizedCat === 'liquidhandler' ||
                  normalizedCat.includes('hamilton') ||
                  normalizedCat.includes('opentrons') ||
                  normalizedCat.includes('tecan')
                )) ||
                // Common plate reader variants
                (requiredCategories.has('platereader') && (
                  normalizedCat === 'platereader' ||
                  normalizedCat.includes('bmg') ||
                  normalizedCat.includes('clario')
                ));
              return matchesCategory;
            });
            console.log('[RunProtocol] After category filter:', allCompat.length);
          }
        }

        // Filter based on deck requirement
        if (protocol?.requires_deck === false) {
          console.log('[RunProtocol] Deck not required, explicitly filtering out LiquidHandlers');
          // If deck not required, hide LiquidHandlers (unless they are specifically capable - logic can be improved)
          allCompat = allCompat.filter(d =>
            d.machine.machine_category !== 'LiquidHandler' &&
            d.machine.machine_category !== 'HamiltonSTAR'
          );
          console.log('[RunProtocol] After deck=false filter:', allCompat.length);
        }

        this.compatibilityData.set(allCompat);

        // Only auto-select if exactly one option and it's a real machine (not template)
        // We want users to click templates to configure them
        const active = allCompat.filter(d =>
          d.compatibility.is_compatible && !(d.machine as any).is_template
        );
        if (active.length === 1) {
          this.onMachineSelect(active[0]);
        }
      },
      error: (err) => console.error('Failed to load compatibility/definitions', err)
    });
  }

  onMachineSelect(machineCompat: MachineCompatibility) {
    const machine = machineCompat.machine;

    if ((machine as any).is_template) {
      this.configureSimulationTemplate(machineCompat);
      return;
    }

    this.selectedMachine.set(machineCompat);
    const machineId = machine.accession_id;
    this.machineFormGroup.patchValue({ machineId });
    this.machineFormGroup.get('machineId')?.updateValueAndValidity();
  }

  private configureSimulationTemplate(templateCompat: MachineCompatibility) {
    // 1. Get the actual definition
    this.assetService.getMachineDefinitions().pipe(take(1)).subscribe(defs => {
      const def = (defs as any[]).find(d => d.accession_id === (templateCompat.machine as any).machine_definition_accession_id);
      if (!def) return;

      // 2. Open config dialog
      const dialogRef = this.dialog.open(SimulationConfigDialogComponent, {
        data: { definition: def },
        disableClose: true
      });

      dialogRef.afterClosed().subscribe(result => {
        if (result) {
          // 3. Create the ephemeral machine
          this.isStartingRun.set(true); // Show spinner during creation

          // Find appropriate frontend/backend IDs
          // In a real implementation, these would come from the definition's associations
          // For now, we'll try to find them by FQN or use the definition's own accession_id if it's acting as a combined template

          this.assetService.getMachineFrontendDefinitions().pipe(
            switchMap(frontends => {
              const frontend = frontends.find(f => f.fqn === def.frontend_fqn || f.fqn === def.fqn);
              const frontendId = frontend?.accession_id || def.accession_id;

              return this.assetService.getBackendsForFrontend(frontendId).pipe(
                map(backends => {
                  // First try exact match
                  let backend = backends.find(b =>
                    b.backend_type === 'simulator' &&
                    (b.name === result.simulation_backend_name || b.fqn === result.simulation_backend_name)
                  );

                  // Fallback: any simulator backend for this machine type
                  if (!backend) {
                    backend = backends.find(b => b.backend_type === 'simulator');
                    if (backend) {
                      console.warn(`[RunProtocol] Specific simulator backend '${result.simulation_backend_name}' not found, falling back to: ${backend.name}`);
                    }
                  }

                  if (!backend) {
                    const msg = `No compatible simulator backend found for ${def.name}`;
                    console.error(`[RunProtocol] ${msg}`);
                    this.snackBar.open(msg, 'OK', { duration: 5000 });
                  }

                  if (!backend) {
                    console.error(`[RunProtocol] No compatible backend found for frontend '${frontendId}'`);
                  }

                  return {
                    frontendId,
                    backendId: backend?.accession_id
                  };
                })
              );
            }),
            switchMap(ids => {
              return this.assetService.createMachine({
                name: result.name,
                frontend_definition_accession_id: ids.frontendId,
                backend_definition_accession_id: ids.backendId,
                backend_config: {},
                is_simulation_override: true,
                simulation_backend_name: result.simulation_backend_name,
                connection_info: {
                  backend: result.simulation_backend_name,
                  plr_backend: def.fqn || ''
                }
              } as any);
            }),
            finalize(() => this.isStartingRun.set(false))
          ).subscribe({
            next: (newMachine) => {
              // 4. Set as selected machine
              const newCompat: MachineCompatibility = {
                machine: {
                  ...newMachine,
                  machine_category: def.machine_category,
                  is_simulation_override: true
                },
                compatibility: {
                  is_compatible: true,
                  missing_capabilities: [],
                  matched_capabilities: [],
                  warnings: []
                }
              };

              // Add to the list so it stays visible
              this.compatibilityData.update(current => [newCompat, ...current]);
              this.onMachineSelect(newCompat);
            },
            error: (err) => {
              console.error('Failed to create simulation machine', err);
              this.snackBar.open('Failed to create simulation machine. Check console for details.', 'Close', {
                duration: 5000,
                panelClass: ['error-snackbar']
              });
            }
          });
        }
      });
    });
  }

  clearProtocol() {
    // Audit-fix: prevent accidental clearing if wizard successfully advanced
    // Use optional chaining. If stepper is not yet ready but we have a selection, 
    // treat it as "deep in wizard" to prevent clearing during initialization races.
    const stepperIndex = this.stepper ? this.stepper.selectedIndex : (this.selectedProtocol() ? 1 : 0);

    if (stepperIndex > 0) {
      console.warn('[RunProtocol] clearProtocol called while deep in wizard (step > 0). Ignoring to prevent state loss.');
      return;
    }

    this.selectedProtocol.set(null);
    this.selectedMachine.set(null);
    this.compatibilityData.set([]);
    this.protocolFormGroup.reset();
    this.machineFormGroup.reset();
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { protocolId: null },
      queryParamsHandling: 'merge'
    });
  }

  // Recents Management
  private getRecentIds(): string[] {
    try {
      const stored = localStorage.getItem(RECENTS_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }

  private addToRecents(id: string) {
    const recents = this.getRecentIds().filter(r => r !== id);
    recents.unshift(id);
    localStorage.setItem(RECENTS_KEY, JSON.stringify(recents.slice(0, MAX_RECENTS)));
  }

  // Search & Filters
  onSearchChange(event: Event) {
    const input = event.target as HTMLInputElement;
    this.searchQuery.set(input.value);
  }

  clearSearch() {
    this.searchQuery.set('');
  }

  toggleFilter(categoryKey: string, value: string) {
    const current = this.activeFilters();
    const categorySet = new Set(current[categoryKey] || []);

    if (categorySet.has(value)) {
      categorySet.delete(value);
    } else {
      categorySet.add(value);
    }

    this.activeFilters.set({
      ...current,
      [categoryKey]: categorySet
    });
  }

  getSelectedCount(category: FilterCategory): number {
    return category.options.filter(o => o.selected).length;
  }

  // Execution
  startRun() {
    // AUDIT-01: Validation Guard
    if (!this.store.simulationMode() && this.showMachineError()) {
      this.snackBar.open('Cannot start physical run with simulated machines. Please select physical machines or switch to simulation mode.', 'Close', {
        duration: 5000,
        panelClass: 'error-snackbar'
      });
      return;
    }

    const protocol = this.selectedProtocol();
    // Validate parameters form AND ensure deck is configured
    if (protocol && this.parametersFormGroup.valid && !this.isStartingRun() && this.configuredAssets()) {
      this.isStartingRun.set(true);
      const runName = this.runNameControl.value?.trim() || `${protocol.name} - ${new Date().toLocaleString()}`;
      const runNotes = this.runNotesControl.value?.trim() || '';

      // Merge parameters form values with well selections
      const wellSelections = this.wellSelections();
      const params: Record<string, any> = {
        ...this.parametersFormGroup.value,
      };

      // Add well selections, serializing arrays to comma-separated strings
      Object.entries(wellSelections).forEach(([name, wells]) => {
        const wellsStr = Array.isArray(wells) ? wells.join(',') : wells;
        params[name] = wellsStr;
      });

      // Map configured assets (consumables/resources) to their parameter names
      const assetMappings = this.configuredAssets() || {};
      protocol.assets?.forEach(assetReq => {
        const selectedResource = assetMappings[assetReq.accession_id];
        if (selectedResource) {
          // Use original parameter name (assetReq.name) as the key
          params[assetReq.name] = selectedResource.accession_id;
        }
      });

      // Add machine argument mappings from per-argument selector
      const machineAssignments = this.machineSelections();
      for (const sel of machineAssignments) {
        const key = sel.parameterName || sel.argumentName;
        if (sel.selectedMachine) {
          // Existing machine: reference by accession_id
          params[key] = sel.selectedMachine.accession_id;
        } else if (sel.selectedBackend) {
          // New simulated instance: pass backend info for runtime creation
          params[key] = {
            _create_from_backend: true,
            backend_accession_id: sel.selectedBackend.accession_id,
            frontend_accession_id: sel.frontendId,
            is_simulated: sel.selectedBackend.backend_type === 'simulator',
            simulation_backend_name: sel.selectedBackend.fqn
          };
        }
      }

      this.executionService.startRun(
        protocol.accession_id,
        runName,
        params,
        this.store.simulationMode(),  // Use global store
        runNotes,  // Add notes parameter
        protocol
      ).pipe(
        finalize(() => this.isStartingRun.set(false))
      ).subscribe({
        next: (response) => {
          // Clear wizard state on success
          localStorage.removeItem(WIZARD_STORAGE_KEY);
          this.router.navigate(['/app/monitor', response.run_id]);
        },
        error: (err) => console.error('[RunProtocol] Failed to start run:', err)
      });
    }
  }
  // Well Selection Methods
  private isWellSelectionParameter(param: any): boolean {
    const name = (param.name || '').toLowerCase();
    // Check name patterns
    const wellNamePatterns = ['well', 'wells', 'source_wells', 'target_wells', 'well_ids', 'indices'];
    if (wellNamePatterns.some(p => name.includes(p))) {
      return true;
    }

    // Check ui_hint if available (supports string or object with type)
    const uiHint = (param as any).ui_hint;
    if (uiHint === 'well_selector' || uiHint?.type === 'well_selector') {
      return true;
    }

    return false;
  }

  getWellParameters(): any[] {
    return this.selectedProtocol()?.parameters?.filter(p => this.isWellSelectionParameter(p)) || [];
  }

  openWellSelector(param: any) {
    const currentSelection = this.wellSelections()[param.name] || [];

    // Auto-detect plate type from selected assets
    const plateType = this.detectPlateType();

    const dialogData: WellSelectorDialogData = {
      plateType,
      initialSelection: currentSelection,
      mode: 'multi',
      title: `Select Wells: ${param.name}`,
      plateLabel: param.description || param.name
    };

    this.dialog.open(WellSelectorDialogComponent, {
      data: dialogData,
      width: plateType === '384' ? '900px' : '700px'
    }).afterClosed().subscribe((result: WellSelectorDialogResult) => {
      if (result?.confirmed) {
        this.wellSelections.update(s => ({ ...s, [param.name]: result.wells }));
        this.validateWellSelections();
      }
    });
  }

  private detectPlateType(): '96' | '384' {
    // Check configured assets for plate with well count
    const assets = this.configuredAssets();
    if (assets) {
      for (const [, asset] of Object.entries(assets)) {
        const res = asset as any;
        // Check resource definition for well count
        if (res?.fqn?.toLowerCase().includes('384') || res?.name?.includes('384')) {
          return '384';
        }
      }
    }
    return '96';  // Default
  }

  getWellSelectionLabel(paramName: string): string {
    const wells = this.wellSelections()[paramName] || [];
    if (wells.length === 0) return 'Click to select wells...';
    if (wells.length <= 5) return wells.join(', ');
    return `${wells.length} wells selected`;
  }

  areWellSelectionsValid(): boolean {
    const wellParams = this.getWellParameters();
    const selections = this.wellSelections();

    // All required well parameters must have at least one selection
    return wellParams.every(p => {
      if (p.optional) return true;
      return (selections[p.name]?.length || 0) > 0;
    });
  }

  private validateWellSelections() {
    this.wellsFormGroup.get('valid')?.setValue(this.areWellSelectionsValid());
  }
}