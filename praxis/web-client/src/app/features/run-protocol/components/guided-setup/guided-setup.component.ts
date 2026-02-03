import { booleanAttribute, Component, computed, EventEmitter, Inject, inject, Input, OnInit, Optional, Output, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { PLRCategory } from '@core/db/plr-category';
import { Resource, ResourceDefinition } from '@features/assets/models/asset.models';
import { AssetService } from '@features/assets/services/asset.service';
import { AssetRequirement, ProtocolDefinition } from '@features/protocols/models/protocol.models';
import { PraxisAutocompleteComponent } from '@shared/components/praxis-autocomplete/praxis-autocomplete.component';
import { SelectOption } from '@shared/components/praxis-select/praxis-select.component';

export interface GuidedSetupData {
  protocol: ProtocolDefinition;
  deckResource?: any; // strict type would be better but avoiding import cycles
  assetMap?: Record<string, Resource>;
}

export interface GuidedSetupResult {
  assetMap: Record<string, Resource>; // Map requirement accession_id -> Inventory Resource
}

@Component({
  selector: 'app-guided-setup',
  standalone: true,
  imports: [
    MatDialogModule,
    MatButtonModule,
    MatSelectModule,
    MatIconModule,
    MatTooltipModule,
    MatChipsModule,
    FormsModule,
    PraxisAutocompleteComponent
  ],
  template: `
    @if (!isInline) {
      <h2 mat-dialog-title>Deck Setup: {{ data?.protocol?.name }}</h2>
    }
    <mat-dialog-content [class.inline-content]="isInline">
      @if (!isInline) {
        <p class="description">
          Please assign inventory items to the required assets for this protocol.
          We've auto-selected matches where possible.
        </p>
      }

      <!-- Loading state -->
      @if (isLoading()) {
        <div class="loading-state">
          <mat-icon class="animate-spin">sync</mat-icon>
          <span>Loading inventory...</span>
        </div>
      } @else if (inventory().length === 0 && requiredAssets.length > 0) {
        <div class="empty-state">
          <mat-icon>inventory_2</mat-icon>
          <span>No resources in inventory.</span>
          <button mat-stroked-button color="primary" (click)="generateEphemeralResources()" [disabled]="isGenerating()">
            <mat-icon>auto_awesome</mat-icon>
            {{ isGenerating() ? 'Generating...' : 'Generate Ephemeral Resources' }}
          </button>
        </div>
      } @else {
        <div class="list-actions">
          <button mat-stroked-button (click)="autoFillAll()">
            <mat-icon>auto_fix_high</mat-icon>
            Auto-fill All
          </button>
          <button mat-button (click)="clearAll()" [disabled]="!hasSelections()">
            <mat-icon>clear_all</mat-icon>
            Clear All
          </button>
        </div>
        <div class="requirements-list">
          @for (req of requiredAssets; track req.accession_id; let i = $index) {
            <div class="requirement-item" 
                 [matTooltip]="getAssetTooltip(req)"
                 [matTooltipShowDelay]="600"
                 [class.current]="i === currentIndex()"
                 [class.completed]="selectedAssets()[req.accession_id]"
                 [class.autofilled]="isAutofilled(req.accession_id)" 
                 [class.pending]="!selectedAssets()[req.accession_id] && i > currentIndex()">
              
              <!-- Order Badge -->
              <div class="order-badge" 
                   [class.active]="i === currentIndex()"
                   [class.completed]="selectedAssets()[req.accession_id]">
                @if (selectedAssets()[req.accession_id]) {
                  <mat-icon style="font-size: 18px; width: 18px; height: 18px">check</mat-icon>
                } @else {
                  {{ i + 1 }}
                }
              </div>

              <div class="req-info">
                <div class="req-header">
                  <span class="req-name">{{ req.name }}</span>
                  @if (isAutofilled(req.accession_id)) {
                    <span class="autofill-badge">
                      <mat-icon class="autofill-icon">auto_awesome</mat-icon>
                      Auto
                    </span>
                  } @else if (selectedAssets()[req.accession_id]) {
                    <!-- 'Set' badge removed as redundant with checkmark/completed style -->
                  }
                  @if (req.optional) {
                    <span class="optional-badge">Optional</span>
                  }
                </div>
                <span class="req-type">{{ req.type_hint_str || 'Generic Resource' }}</span>
                @if (req.fqn) {
                  <span class="req-fqn">{{ getShortFqn(req.fqn) }}</span>
                }
              </div>

              <div class="resource-select">
                <label class="text-xs font-medium text-gray-500 mb-1 block">
                  @if (i === currentIndex() && !selectedAssets()[req.accession_id]) {
                     Select Item
                  } @else {
                     &nbsp;
                  }
                </label>
                <div class="resource-select-field">
                  <app-praxis-autocomplete
                    [options]="requirementsOptions()[req.accession_id] || []"
                    [ngModel]="selectedAssets()[req.accession_id]"
                    (ngModelChange)="updateSelection(req.accession_id, $event)"
                    [placeholder]="'Search inventory...'"
                  ></app-praxis-autocomplete>
                  <button mat-icon-button class="autofill-btn" (click)="autoFillAsset(req)" matTooltip="Auto-select matching item" [matTooltipShowDelay]="600">
                    <mat-icon>auto_fix_high</mat-icon>
                  </button>
                  @if (selectedAssets()[req.accession_id]) {
                    <button mat-icon-button class="clear-asset-btn" (click)="clearAsset(req)" matTooltip="Clear selection" [matTooltipShowDelay]="600">
                      <mat-icon>cancel</mat-icon>
                    </button>
                  }
                </div>
                @if (!req.optional && !selectedAssets()[req.accession_id]) {
                  <!-- <div class="text-xs text-red-500 mt-1">Required</div> -->
                }
              </div>
            </div>
          }
        </div>

        <!-- Summary -->
        <div class="summary">
          <div class="summary-item">
            <mat-icon [class.text-green]="autofilledCount() > 0">auto_awesome</mat-icon>
            <span>{{ autofilledCount() }} auto-filled</span>
          </div>
          <div class="summary-item">
            <mat-icon [class.text-amber]="unassignedCount() > 0" [class.text-green]="unassignedCount() === 0">
              {{ unassignedCount() === 0 ? 'check_circle' : 'warning' }}
            </mat-icon>
            <span>{{ unassignedCount() }} unassigned</span>
          </div>
        </div>
      }
    </mat-dialog-content>

    @if (!isInline) {
      <mat-dialog-actions align="end">
        <button mat-button mat-dialog-close>Cancel</button>
        <button
          mat-raised-button
          color="primary"
          [disabled]="!isValid()"
          (click)="confirm()">
          Confirm Setup
        </button>
      </mat-dialog-actions>
    }
  `,
  styles: [`
    .description {
      color: var(--sys-on-surface-variant);
      margin-bottom: 24px;
    }
    .loading-state, .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 48px 24px;
      gap: 16px;
      color: var(--sys-on-surface-variant);
    }
    .inline-content {
      padding: 0 !important;
      max-height: none !important;
      overflow: visible !important;
    }
    .loading-state mat-icon, .empty-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      opacity: 0.5;
    }
    .animate-spin {
      animation: spin 1s linear infinite;
    }
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    .requirements-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .list-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-bottom: 12px;
      padding-right: 4px;
    }
    .requirement-item {
      display: grid;
      grid-template-columns: auto 1fr 240px;
      gap: 16px;
      align-items: center;
      padding: 12px 16px;
      background: var(--sys-surface-container);
      border-radius: 12px;
      border: 2px solid transparent;
      transition: all 0.2s ease;
    }
    .requirement-item.autofilled {
      border-color: var(--theme-status-success-border);
      background: var(--theme-status-success-muted);
    }
    .requirement-item.assigned {
      border-color: var(--theme-status-info-border);
      background: var(--theme-status-info-muted);
    }
    .requirement-item.unassigned {
      border-color: var(--theme-status-warning-border);
      background: var(--theme-status-warning-muted);
    }
    .req-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .req-header {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .req-name {
      font-weight: 600;
      font-size: 1rem;
    }
    .autofill-badge, .set-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: 12px;
    }
    .autofill-badge {
      background: var(--theme-status-success-muted);
      color: var(--theme-status-success);
    }
    .set-badge {
      background: var(--theme-status-info-muted);
      color: var(--theme-status-info);
    }
    .autofill-icon, .set-icon {
      font-size: 14px !important;
      width: 14px !important;
      height: 14px !important;
    }
    
    /* Highlight Styles mirroring ResourcePlacementStep */
    .requirement-item.current {
      background: var(--sys-tertiary-container);
      border-color: var(--sys-tertiary);
      transform: scale(1.01);
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    .requirement-item.completed {
      background: var(--sys-surface-container-low);
      border-color: var(--sys-outline-variant);
      opacity: 0.9;
    }
    
    .requirement-item.completed.autofilled {
       background: var(--theme-status-success-muted);
       border-color: var(--theme-status-success-border);
    }

    .requirement-item.pending {
      opacity: 0.7;
    }

    .order-badge {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--sys-surface-container-high);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      font-size: 0.875rem;
      flex-shrink: 0;
      transition: all 0.2s ease;
    }

    .order-badge.active {
      background: var(--sys-tertiary);
      color: var(--sys-on-tertiary);
    }
    
    .order-badge.completed {
       background: var(--sys-primary);
       color: var(--sys-on-primary);
    }
    
    .requirement-item.autofilled .order-badge.completed {
        background: var(--sys-green); /* If available, or hardcode green */
        background: var(--theme-status-success);
    }
    .optional-badge {
      font-size: 0.7rem;
      font-weight: 500;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: 12px;
      background: var(--sys-surface-variant);
      color: var(--sys-on-surface-variant);
    }
    .req-type {
      font-size: 0.85em;
      color: var(--sys-on-surface-variant);
    }
    .req-fqn {
      font-size: 0.75em;
      color: var(--sys-outline);
      font-family: monospace;
    }
    .resource-select {
      min-width: 240px;
    }
    .resource-select-field {
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .resource-select-field app-praxis-autocomplete {
      flex: 1;
    }
    .autofill-btn {
      color: var(--theme-status-success);
      opacity: 0.7;
      transition: all 0.2s ease;
    }
    .autofill-btn:hover {
      opacity: 1;
      background: var(--theme-status-success-muted);
    }
    .clear-asset-btn {
      color: var(--sys-outline);
      opacity: 0.7;
      transition: all 0.2s ease;
    }
    .clear-asset-btn:hover {
      opacity: 1;
      color: var(--sys-error);
      background: var(--sys-error-container);
    }
    mat-form-field {
      margin-bottom: -1.25em;
    }
    .option-content {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .option-name {
      flex: 1;
    }
    .option-id {
      font-size: 0.8em;
      opacity: 0.6;
    }
    .match-icon {
      font-size: 16px !important;
      width: 16px !important;
      height: 16px !important;
      color: var(--theme-status-success);
    }
    .suggested-icon {
      font-size: 16px !important;
      width: 16px !important;
      height: 16px !important;
      color: var(--theme-status-warning);
      margin-right: 4px;
    }
    ::ng-deep .suggested-group .mat-mdc-optgroup-label {
      color: var(--theme-status-success) !important;
      font-weight: 600;
    }
    ::ng-deep .suggested-option {
      background: var(--theme-status-success-muted) !important;
    }
    .summary {
      display: flex;
      gap: 24px;
      justify-content: center;
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid var(--sys-outline-variant);
    }
    .summary-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.9rem;
      color: var(--sys-on-surface-variant);
    }
    .summary-item mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }
    .text-green {
      color: var(--theme-status-success) !important;
    }
    .text-amber {
      color: var(--theme-status-warning) !important;
    }
    ::ng-deep .mat-mdc-tooltip .mdc-tooltip__body {
      white-space: pre-line !important;
      padding: 8px 12px !important;
      line-height: 1.4 !important;
    }
  `]
})
export class GuidedSetupComponent implements OnInit {
  private assetService = inject(AssetService);
  private dialogRef = inject(MatDialogRef<GuidedSetupComponent>, { optional: true });

  // Inline Inputs
  @Input() protocol: ProtocolDefinition | null = null;
  @Input({ transform: booleanAttribute }) simulationMode = false;
  @Input({ transform: booleanAttribute }) isInline = false;
  @Input() initialSelections: Record<string, Resource> = {};
  @Input() excludeAssetIds: string[] = [];
  @Output() selectionChange = new EventEmitter<Record<string, Resource>>();

  inventory = signal<Resource[]>([]);
  selectedAssets = signal<Record<string, Resource | null>>({});
  autofilledIds = signal<Set<string>>(new Set());
  isLoading = signal(true);
  currentIndex = signal(0);
  isGenerating = signal(false);

  constructor(@Inject(MAT_DIALOG_DATA) @Optional() public data: GuidedSetupData | null) { }

  get requiredAssets(): AssetRequirement[] {
    const protocol = this.protocol || this.data?.protocol;
    const assets = protocol?.assets || [];

    if (this.excludeAssetIds.length > 0) {
      return assets.filter(a => !this.excludeAssetIds.includes(a.accession_id));
    }
    return assets;
  }

  // Pre-compute options to ensure stable references
  requirementsOptions = computed(() => {
    const map: Record<string, SelectOption[]> = {};
    const inventory = this.inventory();

    this.requiredAssets.forEach(req => {
      map[req.accession_id] = this.generateOptionsForReq(req, inventory);
    });
    return map;
  });

  // Computed signals for summary
  autofilledCount = computed(() => {
    let count = 0;
    const autofilled = this.autofilledIds();
    const selected = this.selectedAssets();
    for (const id of autofilled) {
      if (selected[id]) count++;
    }
    return count;
  });

  unassignedCount = computed(() => {
    return this.requiredAssets.filter(req =>
      !req.optional && !this.selectedAssets()[req.accession_id]
    ).length;
  });

  hasSelections = computed(() => {
    return Object.values(this.selectedAssets()).some(val => !!val);
  });

  ngOnInit() {
    // Initialize with initial selections if provided
    if (this.initialSelections && Object.keys(this.initialSelections).length > 0) {
      this.selectedAssets.set({ ...this.initialSelections });
    }

    this.assetService.getResources().subscribe({
      next: async (resources) => {
        this.inventory.set(resources);

        // Automation: If in simulation mode and inventory is empty, generate resources automatically
        if (this.simulationMode && resources.length === 0 && this.requiredAssets.length > 0) {
          console.log('[GuidedSetup] Simulation mode detected with empty inventory. Generating ephemeral resources...');
          await this.generateEphemeralResources();
        } else {
          this.autoSelect();
        }

        this.isLoading.set(false);
      },
      error: (err) => {
        console.error('Failed to load inventory:', err);
        this.isLoading.set(false);
      }
    });
  }

  autoSelect() {
    const currentMap = this.selectedAssets();
    const map: Record<string, Resource | null> = { ...currentMap };
    const autofilled = new Set<string>(this.autofilledIds());

    // Tracks resources already assigned (either manually or by auto-select)
    const usedResourceIds = new Set<string>();
    Object.values(currentMap).forEach(res => {
      if (res) usedResourceIds.add(res.accession_id);
    });

    this.requiredAssets.forEach(req => {
      // Skip if already has a selection
      if (map[req.accession_id]) {
        return;
      }

      const match = this.getBestMatch(req, usedResourceIds);

      if (match) {
        map[req.accession_id] = match;
        usedResourceIds.add(match.accession_id);
        autofilled.add(req.accession_id);
      } else {
        map[req.accession_id] = null;
      }
    });

    this.selectedAssets.set(map);
    this.autofilledIds.set(autofilled);

    // Update current index to first unassigned
    const firstUnassigned = this.requiredAssets.findIndex(req => !map[req.accession_id]);
    if (firstUnassigned !== -1) {
      this.currentIndex.set(firstUnassigned);
    } else {
      this.currentIndex.set(this.requiredAssets.length);
    }

    // Always emit in inline mode so parent can track selection state
    // The parent's canProceedFromAssetSelection() handles validation
    if (this.isInline) {
      this.selectionChange.emit(map as Record<string, Resource>);
    }
  }

  private getBestMatch(req: AssetRequirement, usedResourceIds: Set<string>): Resource | null {
    // Find compatible resources sorted by match quality
    const candidates = this.getCompatibleResources(req);

    // Prioritize exact FQN matches
    const exactMatches = candidates.filter(res => this.isExactMatch(req, res));
    const sortedCandidates = [...exactMatches, ...candidates.filter(res => !this.isExactMatch(req, res))];

    // Find first unused candidate
    return sortedCandidates.find(res => !usedResourceIds.has(res.accession_id)) || null;
  }

  /**
   * Get compatible resources for a requirement.
   * Uses multiple matching strategies with priority:
   * 1. Exact FQN match (resource.fqn === req.fqn)
   * 2. FQN class name match (last part of FQN matches)
   * 3. Type hint string match
   * 4. Category/keyword matching
   */
  getCompatibleResources(req: AssetRequirement): Resource[] {
    const reqFqn = (req.fqn || '').toLowerCase();
    const reqType = (req.type_hint_str || '').toLowerCase();
    const reqClassName = this.getClassName(reqFqn);

    return this.inventory().filter(res => {
      const resFqn = (res.fqn || '').toLowerCase();
      const resClassName = this.getClassName(resFqn);

      // EXCLUDE carriers when requirement is for a non-carrier resource
      const resCategory = this.getResourceCategory(res);
      if (resCategory === PLRCategory.CARRIER && req.required_plr_category && req.required_plr_category !== PLRCategory.CARRIER) {
        return false;
      }

      // 1. Exact FQN match
      if (resFqn && reqFqn && resFqn === reqFqn) {
        return true;
      }

      // 2. FQN class name match (e.g., both end with "Plate")
      if (resClassName && reqClassName && resClassName === reqClassName) {
        return true;
      }

      // 3. Type hint match against FQN class name
      if (reqType && resClassName && resClassName.includes(reqType)) {
        return true;
      }

      // 4. Category matching (uses backend-provided required_plr_category)
      if (this.matchesByCategory(req, res)) {
        return true;
      }

      return false;
    });
  }

  /**
   * Extract class name from FQN (last part after dot)
   */
  private getClassName(fqn: string): string {
    if (!fqn) return '';
    const parts = fqn.split('.');
    return parts[parts.length - 1] || '';
  }

  /**
   * Get PLR category from a resource.
   * Checks plr_definition first, then falls back to FQN inference.
   */
  private getResourceCategory(res: Resource): string | null {
    // Primary: Check if category is in plr_definition
    if (res.plr_definition && typeof res.plr_definition === 'object') {
      const category = (res.plr_definition as any).category;
      if (category && typeof category === 'string') {
        return category;
      }
    }

    // Fallback: Infer from FQN (less reliable but needed until all resources have definitions)
    if (!res.fqn) return null;
    const fqnLower = res.fqn.toLowerCase();

    if (fqnLower.includes('plate') && !fqnLower.includes('carrier') && !fqnLower.includes('reader')) {
      return PLRCategory.PLATE;
    }
    if (fqnLower.includes('tiprack') || (fqnLower.includes('tip') && fqnLower.includes('rack'))) {
      return PLRCategory.TIP_RACK;
    }
    if (fqnLower.includes('trough') || fqnLower.includes('reservoir')) {
      return PLRCategory.TROUGH;
    }
    if (fqnLower.includes('carrier')) {
      return PLRCategory.CARRIER;
    }
    if (fqnLower.includes('tube') && !fqnLower.includes('rack')) {
      return PLRCategory.TUBE;
    }
    if (fqnLower.includes('tuberack') || (fqnLower.includes('tube') && fqnLower.includes('rack'))) {
      return PLRCategory.TUBE_RACK;
    }

    return null;
  }

  /**
   * Category-based matching using backend-provided required_plr_category.
   * This is the CORRECT way - no string matching on names/FQNs.
   */
  private matchesByCategory(req: AssetRequirement, res: Resource): boolean {
    // If requirement specifies a category, use it (backend provides this)
    if (req.required_plr_category) {
      const resCategory = this.getResourceCategory(res);
      if (!resCategory) return false;

      // Exact category match
      return resCategory.toLowerCase() === req.required_plr_category.toLowerCase();
    }

    // No category specified - don't filter by category
    return false;
  }

  /**
   * Check if a resource is an exact match for a requirement (by FQN or class name)
   */
  isExactMatch(req: AssetRequirement, res: Resource): boolean {
    const reqFqn = (req.fqn || '').toLowerCase();
    const resFqn = (res.fqn || '').toLowerCase();

    if (resFqn && reqFqn && resFqn === reqFqn) {
      return true;
    }

    const reqClassName = this.getClassName(reqFqn);
    const resClassName = this.getClassName(resFqn);

    return !!(resClassName && reqClassName && resClassName === reqClassName);
  }

  /**
   * Get exact matches (suggested resources) for a requirement
   */
  getExactMatches(req: AssetRequirement): Resource[] {
    return this.getCompatibleResources(req).filter(res => this.isExactMatch(req, res));
  }

  /**
   * Get other compatible resources (non-exact matches)
   */
  getOtherCompatible(req: AssetRequirement): Resource[] {
    return this.getCompatibleResources(req).filter(res => !this.isExactMatch(req, res));
  }

  /**
   * Check if a requirement was auto-filled
   */
  isAutofilled(reqId: string): boolean {
    return this.autofilledIds().has(reqId) && !!this.selectedAssets()[reqId];
  }

  /**
   * Get short FQN for display (last 2-3 parts)
   */
  getShortFqn(fqn: string): string {
    if (!fqn) return '';
    const parts = fqn.split('.');
    return parts.slice(-2).join('.');
  }

  getAssetTooltip(req: AssetRequirement): string {
    const selected = this.selectedAssets()[req.accession_id];
    let tooltip = `Requirement: ${req.name}`;
    tooltip += `\nType: ${req.type_hint_str || 'Generic Resource'}`;

    if (req.fqn) {
      tooltip += `\nFQN: ${req.fqn}`;
    }

    if (selected) {
      tooltip += `\n\n--- Selection ---`;
      tooltip += `\nName: ${selected.name}`;
      if (selected.fqn) {
        tooltip += `\nFQN: ${selected.fqn}`;
      }
      tooltip += `\nStatus: ${this.isAutofilled(req.accession_id) ? 'Auto-matched' : 'Confirmed'}`;
    } else {
      tooltip += `\n\nStatus: Unassigned`;
    }

    return tooltip;
  }



  private generateOptionsForReq(req: AssetRequirement, inventory: Resource[]): SelectOption[] {
    // Helper to get compatible resources since we can't call methods easily inside computed
    const compatible = this.getCompatibleResourcesForInventory(req, inventory);

    const exact: Resource[] = [];
    const other: Resource[] = [];

    compatible.forEach(res => {
      if (this.isExactMatch(req, res)) {
        exact.push(res);
      } else {
        other.push(res);
      }
    });

    const options: SelectOption[] = [];

    exact.forEach(res => options.push({
      label: `${res.name} (${res.accession_id.substring(0, 6)})`,
      value: res, // Resource object reference is stable
      icon: 'recommend'
    }));

    other.forEach(res => options.push({
      label: `${res.name} (${res.accession_id.substring(0, 6)})`,
      value: res
    }));

    return options;
  }

  // Refactored to take inventory as arg for computed purity
  private getCompatibleResourcesForInventory(req: AssetRequirement, inventory: Resource[]): Resource[] {
    const reqFqn = (req.fqn || '').toLowerCase();
    const reqType = (req.type_hint_str || '').toLowerCase();
    const reqClassName = this.getClassName(reqFqn);

    return inventory.filter(res => {
      const resFqn = (res.fqn || '').toLowerCase();
      const resClassName = this.getClassName(resFqn);

      // EXCLUDE carriers - they are container resources, not consumables
      if (resFqn.includes('carrier') || resClassName.toLowerCase().includes('carrier')) {
        return false;
      }

      if (resFqn && reqFqn && resFqn === reqFqn) return true;
      if (resClassName && reqClassName && resClassName === reqClassName) return true;
      if (reqType && resClassName && resClassName.includes(reqType)) return true;
      if (this.matchesByCategory(req, res)) return true;

      return false;
    });
  }

  updateSelection(reqId: string, resource: Resource | null) {
    this.selectedAssets.update(current => ({
      ...current,
      [reqId]: resource
    }));

    // Emit change if inline
    if (this.isInline) {
      this.selectionChange.emit(this.selectedAssets() as Record<string, Resource>);
    }

    // If manually changed, remove from autofilled set
    if (this.autofilledIds().has(reqId)) {
      this.autofilledIds.update(set => {
        const newSet = new Set(set);
        newSet.delete(reqId);
        return newSet;
      });
    }

    // Auto-advance logic
    if (resource) { // If setting a value
      const index = this.requiredAssets.findIndex(r => r.accession_id === reqId);
      // Only advance if we worked on the current item
      if (index === this.currentIndex()) {
        // Find next unassigned
        const nextUnassigned = this.requiredAssets.findIndex((r, i) => i > index && !this.selectedAssets()[r.accession_id]);
        if (nextUnassigned !== -1) {
          this.currentIndex.set(nextUnassigned);
        }
      }
    }
  }

  isValid(): boolean {
    // Check if all required assets have a selection
    return this.requiredAssets.every(req =>
      req.optional ? true : !!this.selectedAssets()[req.accession_id]
    );
  }

  confirm() {
    const result: GuidedSetupResult = {
      assetMap: this.selectedAssets() as Record<string, Resource>
    };
    this.selectionChange.emit(result.assetMap);
    if (this.dialogRef) {
      this.dialogRef.close(result);
    }
  }

  clearAsset(req: AssetRequirement) {
    this.updateSelection(req.accession_id, null);
  }

  autoFillAll() {
    this.autoSelect();
  }

  clearAll() {
    const map: Record<string, Resource | null> = {};
    this.requiredAssets.forEach(req => {
      map[req.accession_id] = null;
    });
    this.selectedAssets.set(map);
    this.autofilledIds.set(new Set());
    if (this.isInline) {
      this.selectionChange.emit(map as Record<string, Resource>);
    }
  }

  autoFillAsset(req: AssetRequirement) {
    const currentMap = this.selectedAssets();
    const usedResourceIds = new Set<string>();
    Object.values(currentMap).forEach(res => {
      if (res) usedResourceIds.add(res.accession_id);
    });

    const match = this.getBestMatch(req, usedResourceIds);
    if (match) {
      this.updateSelection(req.accession_id, match);
      this.autofilledIds.update(set => {
        const newSet = new Set(set);
        newSet.add(req.accession_id);
        return newSet;
      });
    }
  }

  /**
   * Generate ephemeral resources from resource definitions for simulation mode.
   * When inventory is empty, this creates temporary resources matching each requirement.
   */
  async generateEphemeralResources() {
    if (this.isGenerating()) return;

    this.isGenerating.set(true);
    const createdResources: Resource[] = [];
    const excludedIds = new Set(this.excludeAssetIds);

    try {
      console.log(`[GuidedSetup] Starting ephemeral resource generation for ${this.requiredAssets.length} assets. Excluded:`, Array.from(excludedIds));

      for (const req of this.requiredAssets) {
        if (excludedIds.has(req.accession_id)) {
          console.log(`[GuidedSetup] Skipping excluded asset: ${req.accession_id}`);
          continue;
        }

        console.log(`[GuidedSetup] Generating resource for: ${req.accession_id}`, req);

        // Try to find a matching resource definition
        // First try by req.fqn, then by type_hint_str
        // getResourceDefinition is async and returns Promise<ResourceDefinition | null>
        let def = await this.assetService.getResourceDefinition(req.fqn);

        if (!def && req.type_hint_str) {
          console.log(`[GuidedSetup] No definition found for FQN "${req.fqn}". Trying type_hint_str "${req.type_hint_str}"...`);
          // Note: type_hint_str might be something like 'Plate' or 'TipRack'
          const allDefs = await firstValueFrom(this.assetService.getResourceDefinitions()) as ResourceDefinition[];
          def = allDefs.find(d =>
            (d.fqn && d.fqn.toLowerCase().includes(req.type_hint_str!.toLowerCase())) ||
            (d.name && d.name.toLowerCase().includes(req.type_hint_str!.toLowerCase()))
          ) || null;
        }

        if (def) {
          // Create an ephemeral resource from the definition
          const resourceCreate = {
            name: `${req.accession_id.slice(-6)} - ${def.name || 'Ephemeral'}`,
            fqn: def.fqn,
            resource_definition_accession_id: def.accession_id,
            asset_type: 'resource',
            is_ephemeral: true,
            properties_json: {}
          };

          const created = await firstValueFrom(this.assetService.createResource(resourceCreate as any)) as Resource;
          createdResources.push(created);
          console.log(`[GuidedSetup] Created ephemeral resource: ${created.name} (Accession ID: ${created.accession_id}) using definition: ${def.fqn}`);
        } else {
          console.warn(`[GuidedSetup] No definition found for ${req.fqn} (type_hint_str: ${req.type_hint_str}), skipping`);
        }
      }

      console.log(`[GuidedSetup] Generated ${createdResources.length} ephemeral resources.`);

      if (createdResources.length > 0) {
        // Refresh full inventory to ensure we have all resources
        const allResources = await firstValueFrom(this.assetService.getResources()) as Resource[];
        this.inventory.set(allResources);
        console.log(`[GuidedSetup] Updated inventory with ${allResources.length} total resources.`);

        // Trigger auto-select with the new inventory
        this.autoSelect();
      }
    } catch (err) {
      console.error('[GuidedSetup] Failed to generate ephemeral resources:', err);
    } finally {
      this.isGenerating.set(false);
    }
  }



  compareResources(o1: Resource, o2: Resource): boolean {
    return o1 && o2 ? o1.accession_id === o2.accession_id : o1 === o2;
  }
}
