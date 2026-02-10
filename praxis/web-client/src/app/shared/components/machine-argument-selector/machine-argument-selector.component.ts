import { Component, Input, Output, EventEmitter, OnInit, OnChanges, SimpleChanges, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { AssetService } from '../../../features/assets/services/asset.service';
import { Machine, MachineFrontendDefinition, MachineBackendDefinition } from '../../../features/assets/models/asset.models';
import { AssetRequirement } from '../../../features/protocols/models/protocol.models';
import { PLRCategory, MACHINE_CATEGORIES, RESOURCE_CATEGORIES } from '../../../core/db/plr-category';
import { DeckCatalogService } from '../../../features/run-protocol/services/deck-catalog.service';
import { DeckDefinitionSpec } from '../../../features/run-protocol/models/deck-layout.models';
import { DeckSelectorDialogComponent, DeckSelectorDialogData } from '../deck-selector-dialog/deck-selector-dialog.component';
import { humanize } from '../../../core/utils/plr-display.utils';
import { firstValueFrom } from 'rxjs';

/**
 * Resolved machine selection for a single argument
 */
export interface MachineArgumentSelection {
  argumentId: string;  // The asset requirement accession_id
  argumentName: string;  // Display name
  parameterName: string; // The original Python parameter name
  frontendId: string;  // Frontend definition accession_id
  selectedMachine?: Machine;  // If user selected an existing machine
  selectedBackend?: MachineBackendDefinition;  // If user selected a backend to create new
  selectedDeckType?: DeckDefinitionSpec;  // Selected deck layout (for LiquidHandlers)
  isValid: boolean;
}

/**
 * Machine requirement with resolved frontend info
 */
interface MachineRequirement {
  requirement: AssetRequirement;
  frontend: MachineFrontendDefinition | null;
  availableBackends: MachineBackendDefinition[];
  existingMachines: Machine[];
  isLoading: boolean;
  isExpanded: boolean;
  selection: MachineArgumentSelection | null;
  showError: boolean;
}

@Component({
  selector: 'app-machine-argument-selector',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatExpansionModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatDialogModule
  ],
  template: `
    <div class="machine-args-container">
      @for (req of machineRequirements(); track req.requirement.accession_id) {
        <div class="machine-arg-section" 
             [class.error]="req.showError && !req.selection?.isValid"
             [class.complete]="req.selection?.isValid">
          
          <mat-expansion-panel [expanded]="req.isExpanded" (expandedChange)="toggleExpansion(req, $event)">
            <mat-expansion-panel-header>
              <mat-panel-title>
                <div class="panel-title-content">
                  <div class="status-indicator" [class.complete]="req.selection?.isValid" [class.error]="req.showError && !req.selection?.isValid">
                    @if (req.selection?.isValid) {
                      <mat-icon>check_circle</mat-icon>
                    } @else if (req.showError) {
                      <mat-icon>error</mat-icon>
                    } @else {
                      <mat-icon>radio_button_unchecked</mat-icon>
                    }
                  </div>
                  <div class="title-text">
                    <span class="arg-name">{{ getArgumentDisplayName(req.requirement) }}</span>
                    <span class="arg-type">{{ req.frontend?.name || req.requirement.type_hint_str || 'Machine' }}</span>
                  </div>
                </div>
              </mat-panel-title>
              <mat-panel-description>
                @if (req.selection?.isValid) {
                  <span class="selection-summary">
                    {{ req.selection?.selectedMachine?.name || getBackendDisplayName(req.selection?.selectedBackend) }}
                    @if (req.selection?.selectedBackend?.backend_type === 'simulator') {
                      <mat-icon class="sim-icon" matTooltip="Simulated">science</mat-icon>
                    }
                  </span>
                }
              </mat-panel-description>
            </mat-expansion-panel-header>

            <div class="panel-content">
              @if (req.isLoading) {
                <div class="loading-state">
                  <mat-spinner diameter="32"></mat-spinner>
                  <span>Loading options...</span>
                </div>
              } @else {
                <!-- Existing Machines Section -->
                @if (getFilteredMachines(req).length > 0) {
                  <div class="options-section">
                    <h4 class="section-title">
                      <mat-icon>inventory</mat-icon>
                      Existing Machines
                    </h4>
                    <div class="options-grid">
                      @for (machine of getFilteredMachines(req); track machine.accession_id) {
                        <div class="option-card" 
                             [class.selected]="req.selection?.selectedMachine?.accession_id === machine.accession_id"
                             [class.disabled]="!isMachineCompatible(machine)"
                             [matTooltip]="getMachineTooltip(machine)"
                             matTooltipPosition="above"
                             [matTooltipShowDelay]="400"
                             (click)="isMachineCompatible(machine) && selectMachine(req, machine)">
                          <div class="option-icon">
                            <mat-icon>precision_manufacturing</mat-icon>
                          </div>
                          <div class="option-info">
                            <span class="option-name">{{ machine.name }}</span>
                            <span class="option-meta">{{ getMachineBackendLabel(machine) }}</span>
                          </div>
                          @if (machine.is_simulation_override) {
                            <span class="type-badge sim">Sim</span>
                          } @else {
                            <span class="type-badge real">Real</span>
                          }
                          
                          @if (!isMachineCompatible(machine)) {
                             <span class="incompatible-badge" [matTooltip]="'Available in ' + (machine.is_simulation_override ? 'simulation' : 'hardware') + ' mode only'">
                               Mismatch
                             </span>
                          }
                        </div>
                      }
                    </div>
                  </div>
                }

                <!-- Available Backends Section -->
                @if (getFilteredBackends(req).length > 0) {
                  <div class="options-section">
                    <h4 class="section-title">
                      <mat-icon>add_circle</mat-icon>
                      {{ simulationMode ? 'Simulation Backends' : 'Hardware Drivers' }}
                    </h4>
                    <div class="options-grid">
                      @for (backend of getFilteredBackends(req); track backend.accession_id) {
                        <div class="option-card backend-card" 
                             [class.selected]="req.selection?.selectedBackend?.accession_id === backend.accession_id"
                             [class.disabled]="!isBackendCompatible(backend)"
                             [matTooltip]="backend.fqn"
                             matTooltipPosition="above"
                             [matTooltipShowDelay]="400"
                             (click)="isBackendCompatible(backend) && selectBackend(req, backend)">
                          <div class="option-icon" [class.sim]="backend.backend_type === 'simulator'">
                            <mat-icon>{{ backend.backend_type === 'simulator' ? 'science' : 'cable' }}</mat-icon>
                          </div>
                          <div class="option-info">
                            <span class="option-name">{{ getBackendDisplayName(backend) }}</span>
                            <span class="option-meta">{{ backend.manufacturer || 'PyLabRobot' }}</span>
                          </div>
                          @if (backend.backend_type === 'simulator') {
                            <span class="type-badge sim">Sim</span>
                          } @else {
                            <span class="type-badge real">Hardware</span>
                          }

                          @if (!isBackendCompatible(backend)) {
                             <span class="incompatible-badge" [matTooltip]="'Available in ' + (backend.backend_type === 'simulator' ? 'simulation' : 'hardware') + ' mode only'">
                               Mismatch
                             </span>
                          }
                        </div>
                      }
                    </div>
                  </div>
                }

                <!-- No options state -->
                @if (getFilteredMachines(req).length === 0 && getFilteredBackends(req).length === 0) {
                  <div class="empty-state">
                    <mat-icon>search_off</mat-icon>
                    <p>No {{ simulationMode ? 'simulated' : 'real' }} options available for {{ req.frontend?.name || 'this machine type' }}</p>
                    <p class="hint">Try switching the execution mode toggle</p>
                  </div>
                }
              }
            </div>
          </mat-expansion-panel>
        </div>
      }

      @if (machineRequirements().length === 0) {
        <div class="no-machines-state">
          <mat-icon>check_circle</mat-icon>
          <p>This protocol has no machine requirements</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .machine-args-container {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-md);
    }

    .machine-arg-section {
      border-radius: 16px;
      overflow: hidden;
      transition: all 0.2s ease;

      &.error {
        box-shadow: 0 0 0 2px var(--mat-sys-error);
      }

      &.complete {
        box-shadow: 0 0 0 2px var(--mat-sys-primary);
      }
    }

    ::ng-deep .mat-expansion-panel {
      background: var(--mat-sys-surface-container) !important;
      border-radius: 16px !important;
    }

    ::ng-deep .mat-expansion-panel-header {
      padding: 16px 24px !important;
    }

    .panel-title-content {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .status-indicator {
      display: flex;
      align-items: center;
      color: var(--mat-sys-outline);

      &.complete {
        color: var(--mat-sys-primary);
      }

      &.error {
        color: var(--mat-sys-error);
      }

      mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
    }

    .title-text {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .arg-name {
      font-weight: 600;
      color: var(--mat-sys-on-surface);
    }

    .arg-type {
      font-size: 12px;
      color: var(--mat-sys-on-surface-variant);
    }

    .selection-summary {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      color: var(--mat-sys-primary);
    }

    .sim-badge {
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      background: var(--mat-sys-tertiary-container);
      color: var(--mat-sys-tertiary);
    }

    .sim-icon {
      font-size: 14px !important;
      width: 14px !important;
      height: 14px !important;
      color: var(--mat-sys-tertiary);
      opacity: 0.7;
    }

    .panel-content {
      padding: 0 24px 24px;
    }

    .loading-state {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      padding: 32px;
      color: var(--mat-sys-on-surface-variant);
    }

    .options-section {
      margin-bottom: 20px;

      &:last-child {
        margin-bottom: 0;
      }
    }

    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--mat-sys-on-surface-variant);
      margin: 0 0 12px;

      mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
    }

    .options-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 12px;
    }

    .option-card {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px 20px;
      border-radius: 12px;
      background: var(--mat-sys-surface-container-high);
      border: 1px solid var(--mat-sys-outline-variant);
      cursor: pointer;
      min-height: 72px;
      align-items: center;
      transition: all 0.2s ease;

      &:hover {
        background: var(--mat-sys-surface-container-highest);
        border-color: var(--mat-sys-primary);
        transform: translateY(-2px);
      }

      &.selected {
        background: var(--mat-sys-primary-container);
        border-color: var(--mat-sys-primary);
        box-shadow: 0 0 0 2px var(--mat-sys-primary);
      }
    }

    .option-icon {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--mat-sys-primary-container);
      color: var(--mat-sys-primary);
      flex-shrink: 0;

      &.sim {
        background: var(--mat-sys-tertiary-container);
        color: var(--mat-sys-tertiary);
      }

      mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
      }
    }

    .option-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .option-name {
      font-weight: 500;
      color: var(--mat-sys-on-surface);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .option-meta {
      font-size: 11px;
      color: var(--mat-sys-on-surface-variant);
    }

    .type-badge {
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      flex-shrink: 0;

      &.sim {
        background: var(--mat-sys-tertiary-container);
        color: var(--mat-sys-tertiary);
      }

      &.real {
        background: var(--mat-sys-primary-container);
        color: var(--mat-sys-primary);
      }
    }

    .empty-state, .no-machines-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 32px;
      text-align: center;
      color: var(--mat-sys-on-surface-variant);

      mat-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        opacity: 0.5;
        margin-bottom: 12px;
      }

      p {
        margin: 0;
      }

      .hint {
        font-size: 12px;
        opacity: 0.7;
        margin-top: 8px;
      }
    }

    .no-machines-state {
      background: var(--mat-sys-surface-container);
      border-radius: 16px;

      mat-icon {
        color: var(--mat-sys-primary);
        opacity: 1;
      }
    }

    .option-card.disabled {
      opacity: 0.6;
      background: var(--mat-sys-surface-container);
      border-style: dashed;
      pointer-events: none;
      
      .option-icon {
        filter: grayscale(1);
        background: var(--mat-sys-outline-variant);
        color: var(--mat-sys-outline);
      }
      
      .type-badge {
        background: var(--mat-sys-outline-variant);
        color: var(--mat-sys-outline);
      }
    }

    .incompatible-badge {
      margin-left: auto;
      font-size: 10px;
      color: var(--mat-sys-error);
      font-weight: 500;
      padding: 2px 6px;
      background: var(--mat-sys-error-container);
      border-radius: 4px;
    }
  `]
})
export class MachineArgumentSelectorComponent implements OnInit, OnChanges {
  private assetService = inject(AssetService);
  private dialog = inject(MatDialog);
  private deckCatalog = inject(DeckCatalogService);

  /** Humanize PLR identifiers for template use */
  humanize = humanize;

  /** Protocol asset requirements (machine arguments) */
  @Input() requirements: AssetRequirement[] = [];

  /** Whether running in simulation mode */
  @Input() simulationMode: boolean = true;

  /** Emit when selections change */
  @Output() selectionsChange = new EventEmitter<MachineArgumentSelection[]>();

  /** Emit validation state */
  @Output() validChange = new EventEmitter<boolean>();

  /** Internal state for machine requirements */
  machineRequirements = signal<MachineRequirement[]>([]);

  /** Cached frontends and backends */
  private frontendsCache: MachineFrontendDefinition[] = [];
  private backendsCache: MachineBackendDefinition[] = [];

  /** Session-scoped cache of ephemeral machines (backendAccessionId → Machine) */
  private ephemeralMachineCache = new Map<string, Machine>();
  private machinesCache: Machine[] = [];

  async ngOnInit() {
    await this.loadCaches();
  }

  async ngOnChanges(changes: SimpleChanges) {
    if (changes['requirements']) {
      await this.loadCaches();
      this.buildRequirements();
    }
    if (changes['simulationMode']) {
      this.validateSelectionsAgainstMode();
      this.emitSelections();
    }
  }

  private validateSelectionsAgainstMode() {
    const reqs = this.machineRequirements();
    let changed = false;

    const updated = reqs.map(req => {
      // Check if current selection (machine or backend) is compatible with new mode
      const sel = req.selection;
      if (!sel) return req;

      let isValid = true;
      if (sel.selectedMachine && !this.isMachineCompatible(sel.selectedMachine)) {
        isValid = false;
      } else if (sel.selectedBackend && !this.isBackendCompatible(sel.selectedBackend)) {
        isValid = false;
      }

      if (!isValid) {
        changed = true;
        return { ...req, selection: null }; // Deselect
      }
      return req;
    });

    if (changed) {
      this.machineRequirements.set(updated);
    }
  }

  private async loadCaches() {
    try {
      this.frontendsCache = await firstValueFrom(this.assetService.getMachineFrontendDefinitions());
      this.backendsCache = await firstValueFrom(this.assetService.getMachineBackendDefinitions());
      this.machinesCache = await firstValueFrom(this.assetService.getMachines());
    } catch (e) {
      console.error('[MachineArgSelector] Failed to load caches:', e);
    }
  }

  private buildRequirements() {
    // Filter to only machine requirements (not plates, tips, etc.)
    const machineReqs = this.requirements.filter(r =>
      this.isMachineRequirement(r)
    );

    const built: MachineRequirement[] = machineReqs.map(req => {
      // Find matching frontend by category or type hint
      const frontend = this.findFrontendForRequirement(req);

      // Get backends for this frontend
      let availableBackends = frontend
        ? this.backendsCache.filter(b => b.frontend_definition_accession_id === frontend.accession_id)
        : [];

      // FALLBACK: If no simulators found via strict ID match, look for simulators in the same category
      const hasSim = availableBackends.some(b => b.backend_type === 'simulator');
      if (frontend && !hasSim) {
        const catSims = this.backendsCache.filter(b =>
          b.backend_type === 'simulator' &&
          (b.name?.toLowerCase().includes(frontend.machine_category?.toLowerCase() || '') ||
            b.fqn.toLowerCase().includes(frontend.machine_category?.split(/[_\s]/)[0].toLowerCase() || ''))
        );
        availableBackends = [...availableBackends, ...catSims];
      }

      // Get existing machines matching this category (exclude ephemeral machines created by backend selection)
      const existingMachines = this.machinesCache.filter(m =>
        this.machineMatchesRequirement(m, req, frontend) &&
        !m.connection_info?.['ephemeral']
      );

      return {
        requirement: req,
        frontend,
        availableBackends,
        existingMachines,
        isLoading: false,
        isExpanded: true,
        selection: null,
        showError: false
      };
    });

    this.machineRequirements.set(built);
    this.emitSelections();
  }

  private isMachineRequirement(req: AssetRequirement): boolean {
    const catStr = (req.required_plr_category || '');
    const typeHint = (req.type_hint_str || '').toLowerCase();
    const fqn = (req.fqn || '').toLowerCase();

    // 1. Primary check: Strict category match using standard MACHINE_CATEGORIES set
    if (MACHINE_CATEGORIES.has(catStr as PLRCategory)) {
      return true;
    }

    // 2. Exclude resource categories (Plate, TipRack, Trough, etc.) using canonical set
    if (RESOURCE_CATEGORIES.has(catStr as PLRCategory)) {
      return false;
    }

    // 3. Fallback: Robust checking of type_hint and FQN against standard machine category names
    // This catches cases where seeding might be incomplete or metadata is missing
    const isMachineMatch = Array.from(MACHINE_CATEGORIES).some(machineCat => {
      const catLower = machineCat.toLowerCase();
      // Look for standard category name (e.g., 'liquidhandler', 'platereader') in strings
      return typeHint.includes(catLower) || fqn.includes(catLower);
    });

    if (isMachineMatch) return true;

    // 4. Specific type-based machine indicators (e.g., common PLR types)
    if (typeHint.includes('shaker') || typeHint.includes('centrifuge') ||
      typeHint.includes('incubator') || typeHint.includes('heater') || typeHint.includes('scara')) {
      return true;
    }

    return false;
  }

  private findFrontendForRequirement(req: AssetRequirement): MachineFrontendDefinition | null {
    const typeHint = (req.type_hint_str || '').toLowerCase();
    const cat = (req.required_plr_category || '').toLowerCase();

    // Try to match by type hint FQN
    let match = this.frontendsCache.find(f =>
      typeHint.includes(f.fqn.toLowerCase())
    );
    if (match) return match;

    // Try to match by category
    match = this.frontendsCache.find(f =>
      (f.machine_category || '').toLowerCase() === cat ||
      (f.machine_category || '').toLowerCase().includes(cat.replace('handler', '').replace('reader', ''))
    );
    if (match) return match;

    // Try keyword matching
    if (typeHint.includes('liquidhandler') || cat.includes('liquid')) {
      match = this.frontendsCache.find(f => f.fqn.toLowerCase().includes('liquidhandler'));
    } else if (typeHint.includes('platereader') || cat.includes('reader')) {
      match = this.frontendsCache.find(f => f.fqn.toLowerCase().includes('platereader'));
    } else if (typeHint.includes('shaker') || cat.includes('shaker')) {
      match = this.frontendsCache.find(f => f.fqn.toLowerCase().includes('shaker'));
    }

    return match || null;
  }

  private machineMatchesRequirement(machine: Machine, req: AssetRequirement, frontend: MachineFrontendDefinition | null): boolean {
    if (!frontend) return false;

    const machineCategory = (machine.machine_category || '').toLowerCase();
    const frontendCategory = (frontend.machine_category || '').toLowerCase();

    return machineCategory === frontendCategory ||
      machineCategory.includes(frontendCategory.split(/[_\s]/)[0]);
  }

  getArgumentDisplayName(req: AssetRequirement): string {
    // Try to create a nice display name
    // Use the parameter name if available (human readable from code)
    if (req.name) {
      return req.name.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());
    }

    // Fallback to ID-based name if name is missing (rare)
    const id = req.accession_id || 'unknown';
    return id.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());
  }

  getBackendDisplayName(backend?: MachineBackendDefinition): string {
    if (!backend) return 'Unknown';
    const name = backend.name || backend.fqn.split('.').pop() || 'Unknown';
    // Normalize common patterns
    if (name.toLowerCase().includes('chatterbox')) return 'Simulated';
    return name.replace(/Backend$/, '');
  }

  getFilteredMachines(req: MachineRequirement): Machine[] {
    // Return all machines, but we will visually disable incompatible ones
    return req.existingMachines;
  }

  getFilteredBackends(req: MachineRequirement): MachineBackendDefinition[] {
    // Return all backends, but we will visually disable incompatible ones
    return req.availableBackends;
  }

  toggleExpansion(req: MachineRequirement, expanded: boolean) {
    const reqs = this.machineRequirements();
    const idx = reqs.findIndex(r => r.requirement.accession_id === req.requirement.accession_id);
    if (idx >= 0) {
      reqs[idx] = { ...reqs[idx], isExpanded: expanded };
      this.machineRequirements.set([...reqs]);
    }
  }

  selectMachine(req: MachineRequirement, machine: Machine) {
    const reqs = this.machineRequirements();
    const idx = reqs.findIndex(r => r.requirement.accession_id === req.requirement.accession_id);
    if (idx >= 0) {
      reqs[idx] = {
        ...reqs[idx],
        selection: {
          argumentId: req.requirement.accession_id || '',
          argumentName: this.getArgumentDisplayName(req.requirement),
          parameterName: req.requirement.name,
          frontendId: req.frontend?.accession_id || '',
          selectedMachine: machine,
          selectedBackend: undefined,
          isValid: true
        }
      };
      this.machineRequirements.set([...reqs]);
      this.emitSelections();
    }
  }

  async selectBackend(req: MachineRequirement, backend: MachineBackendDefinition) {
    const reqs = this.machineRequirements();
    const idx = reqs.findIndex(r => r.requirement.accession_id === req.requirement.accession_id);
    if (idx < 0) return;

    // Check session cache — reuse previously created ephemeral machine for this backend
    const cacheKey = `${req.requirement.accession_id}::${backend.accession_id}`;
    const cached = this.ephemeralMachineCache.get(cacheKey);
    if (cached) {
      // If this frontend has a deck with multiple options, allow re-selecting the deck
      let deckType: DeckDefinitionSpec | undefined;
      if (req.frontend?.has_deck && backend.fqn) {
        const compatibleDecks = this.deckCatalog.getCompatibleDeckTypes(backend.fqn);
        if (compatibleDecks.length > 1) {
          const backendName = this.getBackendDisplayName(backend);
          const dialogRef = this.dialog.open(DeckSelectorDialogComponent, {
            data: {
              decks: compatibleDecks,
              frontendName: req.frontend.name || 'Machine',
              backendName
            } as DeckSelectorDialogData,
            width: '500px',
            autoFocus: false
          });
          const newDeck = await firstValueFrom(dialogRef.afterClosed());
          if (newDeck) {
            deckType = newDeck;
          } else {
            // Cancelled — keep existing selection
            return;
          }
        } else if (compatibleDecks.length === 1) {
          deckType = compatibleDecks[0];
        }
      } else {
        deckType = cached.connection_info?.['deck_type_fqn']
          ? this.deckCatalog.getDeckDefinition(cached.connection_info['deck_type_fqn']) ?? undefined
          : undefined;
      }

      console.debug('[MachineArgSelector] Reusing cached ephemeral machine:', cached.name, cached.accession_id);
      reqs[idx] = {
        ...reqs[idx],
        selection: {
          argumentId: req.requirement.accession_id || '',
          argumentName: this.getArgumentDisplayName(req.requirement),
          parameterName: req.requirement.name,
          frontendId: req.frontend?.accession_id || '',
          selectedMachine: cached,
          selectedBackend: backend,
          selectedDeckType: deckType,
          isValid: true
        }
      };
      this.machineRequirements.set([...reqs]);
      this.emitSelections();
      return;
    }

    // Resolve compatible decks if this is a liquid handler with a deck
    let selectedDeck: DeckDefinitionSpec | null = null;
    if (req.frontend?.has_deck && backend.fqn) {
      const compatibleDecks = this.deckCatalog.getCompatibleDeckTypes(backend.fqn);

      if (compatibleDecks.length === 1) {
        // Single compatible deck — auto-select
        selectedDeck = compatibleDecks[0];
        console.debug('[MachineArgSelector] Auto-selected deck:', selectedDeck.name);
      } else if (compatibleDecks.length > 1) {
        // Multiple decks — show dialog
        const backendName = this.getBackendDisplayName(backend);
        const dialogRef = this.dialog.open(DeckSelectorDialogComponent, {
          data: {
            decks: compatibleDecks,
            frontendName: req.frontend.name || 'Machine',
            backendName
          } as DeckSelectorDialogData,
          width: '500px',
          autoFocus: false
        });

        selectedDeck = await firstValueFrom(dialogRef.afterClosed());
        if (!selectedDeck) {
          // User cancelled — abort backend selection
          console.debug('[MachineArgSelector] Deck selection cancelled');
          return;
        }
      }
    }

    // Mark as loading while we create the machine
    reqs[idx] = { ...reqs[idx], isLoading: true };
    this.machineRequirements.set([...reqs]);

    try {
      // Create an ephemeral machine on-the-fly for this backend
      const backendName = this.getBackendDisplayName(backend);
      const category = req.frontend?.machine_category || 'Machine';
      const uniqueSuffix = Math.random().toString(36).substring(2, 6).toUpperCase();
      const machineName = `${category} (${backendName}) ${uniqueSuffix}`;

      const connectionInfo: Record<string, any> = {
        backend: backend.fqn,
        plr_backend: backend.fqn,
        ephemeral: true
      };
      if (selectedDeck) {
        connectionInfo['deck_type_fqn'] = selectedDeck.fqn;
      }

      const newMachine = await firstValueFrom(
        this.assetService.createMachine({
          name: machineName,
          machine_category: category,
          is_simulation_override: backend.backend_type === 'simulator',
          simulation_backend_name: backend.fqn,
          frontend_definition_accession_id: req.frontend?.accession_id,
          backend_definition_accession_id: backend.accession_id,
          deck_type: selectedDeck?.fqn,
          connection_info: connectionInfo
        })
      );

      console.debug('[MachineArgSelector] Created ephemeral machine:', newMachine.name, newMachine.accession_id,
        selectedDeck ? `with deck: ${selectedDeck.name}` : '(no deck)');

      // Cache for session reuse
      this.ephemeralMachineCache.set(cacheKey, newMachine);

      // Update the requirement with the newly created machine
      const updatedReqs = this.machineRequirements();
      updatedReqs[idx] = {
        ...updatedReqs[idx],
        isLoading: false,
        selection: {
          argumentId: req.requirement.accession_id || '',
          argumentName: this.getArgumentDisplayName(req.requirement),
          parameterName: req.requirement.name,
          frontendId: req.frontend?.accession_id || '',
          selectedMachine: newMachine,
          selectedBackend: backend,
          selectedDeckType: selectedDeck ?? undefined,
          isValid: true
        }
      };
      this.machineRequirements.set([...updatedReqs]);
      this.emitSelections();
    } catch (error) {
      console.error('[MachineArgSelector] Failed to create ephemeral machine:', error);
      // Revert loading state
      const updatedReqs = this.machineRequirements();
      updatedReqs[idx] = { ...updatedReqs[idx], isLoading: false, showError: true };
      this.machineRequirements.set([...updatedReqs]);
    }
  }

  /** Mark all incomplete sections as error (call when user tries to proceed) */
  showValidationErrors() {
    const reqs = this.machineRequirements();
    const updated = reqs.map(r => ({
      ...r,
      showError: !r.selection?.isValid
    }));
    this.machineRequirements.set(updated);
  }

  private emitSelections() {
    const reqs = this.machineRequirements();
    const selections = reqs
      .filter(r => r.selection)
      .map(r => r.selection!);

    this.selectionsChange.emit(selections);

    const allValid = reqs.length === 0 || reqs.every(r => r.selection?.isValid);
    this.validChange.emit(allValid);
  }

  isMachineCompatible(machine: Machine): boolean {
    const isSimulated = machine.is_simulation_override || false;
    return this.simulationMode ? isSimulated : !isSimulated;
  }

  isBackendCompatible(backend: MachineBackendDefinition): boolean {
    const isSimulator = backend.backend_type === 'simulator';
    return this.simulationMode ? isSimulator : !isSimulator;
  }

  /** Get a descriptive label for the machine card showing backend info */
  getMachineBackendLabel(machine: Machine): string {
    const category = humanize(machine.machine_category);
    const backendFqn = machine.backend_definition?.fqn || machine.simulation_backend_name || '';
    const backendShort = backendFqn ? backendFqn.split('.').pop()?.replace(/Backend$/, '') : '';
    if (backendShort) {
      return `${category} · ${backendShort}`;
    }
    return category;
  }

  /** Build a detailed tooltip for machine cards on hover */
  getMachineTooltip(machine: Machine): string {
    const lines: string[] = [machine.name];
    if (machine.machine_category) lines.push(`Category: ${humanize(machine.machine_category)}`);
    if (machine.backend_definition?.fqn) lines.push(`Backend: ${machine.backend_definition.fqn}`);
    else if (machine.simulation_backend_name) lines.push(`Backend: ${machine.simulation_backend_name}`);
    if (machine.manufacturer) lines.push(`Manufacturer: ${machine.manufacturer}`);
    lines.push(`ID: ${machine.accession_id}`);
    return lines.join('\n');
  }
}
