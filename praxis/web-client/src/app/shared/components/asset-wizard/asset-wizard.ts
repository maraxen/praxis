import { Component, OnInit, inject, signal, ViewChild, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatStepperModule } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatRadioModule } from '@angular/material/radio';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialogRef, MatDialogModule, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { AssetService } from '@features/assets/services/asset.service';
import { ModeService } from '@core/services/mode.service';
import { DeckCatalogService } from '@features/run-protocol/services/deck-catalog.service';
import { DeckDefinitionSpec } from '@features/run-protocol/models/deck-layout.models';
import {
  MachineDefinition,
  ResourceDefinition,
  MachineCreate,
  ResourceCreate,
  Machine,
  MachineFrontendDefinition,
  MachineBackendDefinition
} from '@features/assets/models/asset.models';
import { debounceTime, distinctUntilChanged, map, startWith, switchMap } from 'rxjs/operators';
import { Observable, of, firstValueFrom, combineLatest } from 'rxjs';
import { toObservable } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-asset-wizard',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatRadioModule,
    MatCardModule,
    MatIconModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    MatSnackBarModule
  ],
  templateUrl: './asset-wizard.html',
  styleUrl: './asset-wizard.scss',
})
export class AssetWizard implements OnInit {
  private fb = inject(FormBuilder);
  private assetService = inject(AssetService);
  public modeService = inject(ModeService);
  private deckCatalog = inject(DeckCatalogService);
  private dialogRef = inject(MatDialogRef<AssetWizard>);
  public data = inject(MAT_DIALOG_DATA, { optional: true });
  private snackBar = inject(MatSnackBar);

  @ViewChild('stepper') stepper!: any;

  @Input() context: 'playground' | 'asset-management' = 'asset-management';

  isLoading = signal(false);
  existingMachines$: Observable<Machine[]> = of([]);
  selectedExistingMachine: Machine | null = null;

  // Form groups for each step
  typeStepFormGroup: FormGroup = this.fb.group({
    assetType: ['', Validators.required]
  });

  categoryStepFormGroup: FormGroup = this.fb.group({
    category: ['', Validators.required]
  });

  // Step 3: Frontend selection (for machines) or Definition (for resources)
  frontendStepFormGroup: FormGroup = this.fb.group({
    frontend: ['', Validators.required]
  });

  // Step 4: Backend selection (for machines only)
  backendStepFormGroup: FormGroup = this.fb.group({
    backend: ['', Validators.required]
  });

  // Step 4B: Deck selection (for LiquidHandler machines with multiple compatible decks)
  deckStepFormGroup: FormGroup = this.fb.group({
    deckType: ['', Validators.required]
  });

  // For resources, we still use definition selection
  definitionStepFormGroup: FormGroup = this.fb.group({
    definition: ['', Validators.required]
  });

  configStepFormGroup: FormGroup = this.fb.group({
    name: ['', Validators.required],
    connection_info: [''],
    location: [''],
    description: ['']
  });

  categories$: Observable<string[]> = of([]);

  // Frontend definitions for machines
  frontends$: Observable<MachineFrontendDefinition[]> = of([]);
  selectedFrontend: MachineFrontendDefinition | null = null;

  // Backend definitions for selected frontend
  backends$: Observable<MachineBackendDefinition[]> = of([]);
  selectedBackend: MachineBackendDefinition | null = null;

  // Deck selection state (for LiquidHandler machines)
  compatibleDecks: DeckDefinitionSpec[] = [];
  selectedDeckType: DeckDefinitionSpec | null = null;
  showDeckStep = false;

  // For resources: still use the old search-based approach
  // For resources: signal-based search with observable for debounce
  private readonly searchQuery = signal<string>('');
  private readonly searchQuery$ = toObservable(this.searchQuery);
  searchResults$: Observable<any[]> = of([]);
  selectedDefinition: ResourceDefinition | null = null;

  /**
   * Get display name for a backend (strips package path and 'Backend' suffix)
   */
  getBackendDisplayName(backend: MachineBackendDefinition): string {
    const name = backend.name || backend.fqn.split('.').pop() || 'Unknown';
    // Make "Chatterbox" more user-friendly
    if (name.toLowerCase().includes('chatterbox')) {
      return 'Simulated';
    }
    return name.replace(/Backend$/, '');
  }

  /**
   * Get CSS class for backend type badge
   */
  getBackendTypeBadgeClass(backend: MachineBackendDefinition): string {
    if (backend.backend_type === 'simulator') {
      return 'bg-[var(--mat-sys-tertiary-container)] text-[var(--mat-sys-tertiary)]';
    }
    return 'bg-[var(--mat-sys-primary-container)] text-[var(--mat-sys-primary)]';
  }

  ngOnInit() {
    // Initialize context from dialog data if provided
    if (this.data?.context) {
      this.context = this.data.context;
    }

    // Listen to assetType changes to update categories
    this.typeStepFormGroup.get('assetType')?.valueChanges.subscribe(type => {
      this.categoryStepFormGroup.get('category')?.reset();
      this.selectedExistingMachine = null;
      this.selectedFrontend = null;
      this.selectedBackend = null;
      this.selectedDefinition = null;

      if (type === 'MACHINE') {
        this.categories$ = this.assetService.getMachineFacets().pipe(
          map(facets => facets.machine_category
            .filter(f => f.value !== 'Backend' && f.value !== 'Other')
            .map(f => String(f.value)))
        );

        // Load existing machines if in playground mode
        if (this.context === 'playground') {
          this.existingMachines$ = this.assetService.getMachines();
        }
      } else if (type === 'RESOURCE') {
        this.categories$ = this.assetService.getFacets().pipe(
          map(facets => facets.plr_category.map(f => String(f.value)))
        );
      }

      // Clear search when type changes
      this.searchQuery.set('');
    });

    // Listen to category changes to load frontends (for machines)
    this.categoryStepFormGroup.get('category')?.valueChanges.subscribe(category => {
      if (this.typeStepFormGroup.get('assetType')?.value === 'MACHINE' && category) {
        // Load frontends filtered by category
        this.frontends$ = this.assetService.getMachineFrontendDefinitions().pipe(
          map(frontends => frontends.filter(f => f.machine_category === category))
        );
      }
    });

    // Listen to frontend selection to load backends
    this.frontendStepFormGroup.get('frontend')?.valueChanges.subscribe(frontendId => {
      if (frontendId) {
        this.backends$ = this.assetService.getBackendsForFrontend(frontendId);
      }
    });

    // Handle initial asset type if provided
    const preselected = this.data?.preselectedType || this.data?.initialAssetType;
    if (preselected) {
      const type = String(preselected).toUpperCase();
      this.typeStepFormGroup.patchValue({ assetType: type });
      setTimeout(() => {
        if (this.stepper) {
          this.stepper.selectedIndex = 1;
        }
      }, 0);
    }

    // Resource search logic (kept for resources)
    const assetType$ = this.typeStepFormGroup.get('assetType')!.valueChanges.pipe(startWith(this.typeStepFormGroup.get('assetType')?.value || ''));
    const category$ = this.categoryStepFormGroup.get('category')!.valueChanges.pipe(startWith(this.categoryStepFormGroup.get('category')?.value || ''));
    const query$ = this.searchQuery$.pipe(startWith(''), debounceTime(300), distinctUntilChanged());

    this.searchResults$ = combineLatest([assetType$, category$, query$]).pipe(
      switchMap(([assetType, category, query]) => {
        if (!assetType || assetType !== 'RESOURCE') return of([]);
        return this.assetService.searchResourceDefinitions(query, category);
      })
    );
  }

  searchDefinitions(query: string) {
    this.searchQuery.set(query);
  }

  getCategoryIcon(cat: string): string {
    const mapping: { [key: string]: string } = {
      'LiquidHandler': 'precision_manufacturing',
      'PlateReader': 'visibility',
      'HeaterShaker': 'thermostat',
      'Shaker': 'vibration',
      'Centrifuge': 'rotate_right',
      'Incubator': 'thermostat_auto',
      'Plate': 'grid_view',
      'TipRack': 'view_in_ar',
      'Trough': 'water_drop',
      'Reservoir': 'water_drop',
      'Carrier': 'apps',
      'Deck': 'dashboard',
      'Tube': 'science',
      'Other': 'extension'
    };
    return mapping[cat] || 'science';
  }

  /**
   * Select a frontend definition (for machines)
   */
  selectFrontend(frontend: MachineFrontendDefinition) {
    this.selectedFrontend = frontend;
    this.frontendStepFormGroup.patchValue({ frontend: frontend.accession_id });
    this.selectedBackend = null;
    this.backendStepFormGroup.reset();

    // Pre-fill instance name
    const uniqueSuffix = Math.random().toString(36).substring(2, 6).toUpperCase();
    this.configStepFormGroup.patchValue({
      name: `${frontend.name} ${uniqueSuffix}`,
      description: frontend.description || ''
    });
  }

  /**
   * Select a backend definition (for machines)
   */
  selectBackend(backend: MachineBackendDefinition) {
    this.selectedBackend = backend;
    this.backendStepFormGroup.patchValue({ backend: backend.accession_id });

    // Resolve compatible decks for this backend (only for LiquidHandlers with has_deck)
    this.selectedDeckType = null;
    this.deckStepFormGroup.reset();

    if (this.selectedFrontend?.has_deck && backend.fqn) {
      const decks = this.deckCatalog.getCompatibleDeckTypes(backend.fqn);
      this.compatibleDecks = decks;

      if (decks.length === 0) {
        // No compatible decks — skip deck step
        this.showDeckStep = false;
      } else if (decks.length === 1) {
        // Single compatible deck — auto-select and skip step
        this.showDeckStep = false;
        this.selectedDeckType = decks[0];
        this.deckStepFormGroup.patchValue({ deckType: decks[0].fqn });
      } else {
        // Multiple compatible decks — show selection step
        this.showDeckStep = true;
      }
    } else {
      this.compatibleDecks = [];
      this.showDeckStep = false;
    }
  }

  /**
   * Select a deck type (for LiquidHandler machines)
   */
  selectDeck(deck: DeckDefinitionSpec) {
    this.selectedDeckType = deck;
    this.deckStepFormGroup.patchValue({ deckType: deck.fqn });
  }

  /**
   * Select a resource definition (for resources)
   */
  selectDefinition(def: ResourceDefinition) {
    this.selectedDefinition = def;
    this.definitionStepFormGroup.patchValue({ definition: def.accession_id });

    const uniqueSuffix = Math.random().toString(36).substring(2, 6).toUpperCase();
    this.configStepFormGroup.patchValue({
      name: `${def.name} ${uniqueSuffix}`,
      description: def.description || ''
    });
  }

  selectExistingMachine(machine: Machine) {
    this.selectedExistingMachine = machine;
    this.dialogRef.close(machine);
  }

  chooseSimulateNew() {
    this.selectedExistingMachine = null;
    if (this.stepper) {
      this.stepper.selectedIndex = 1;
    }
  }

  async createAsset() {
    if (this.isLoading()) return;

    const assetType = this.typeStepFormGroup.get('assetType')?.value;
    const category = this.categoryStepFormGroup.get('category')?.value;
    const config = this.configStepFormGroup.value;

    this.isLoading.set(true);

    try {
      let createdAsset: any;
      if (assetType === 'MACHINE') {
        // Use the new 3-tier architecture
        const machinePayload: MachineCreate = {
          name: config.name,
          machine_category: category,
          machine_type: category,
          description: config.description,
          // Link to frontend and backend definitions
          frontend_definition_accession_id: this.selectedFrontend?.accession_id,
          backend_definition_accession_id: this.selectedBackend?.accession_id,
          // Determine if simulated based on backend type
          is_simulation_override: this.selectedBackend?.backend_type === 'simulator',
          simulation_backend_name: this.selectedBackend?.backend_type === 'simulator'
            ? this.getBackendDisplayName(this.selectedBackend!)
            : undefined,
          connection_info: config.connection_info ? { address: config.connection_info } : undefined,
          // Include backend config for hardware connections
          backend_config: this.selectedBackend?.connection_config,
          // Include selected deck type for LiquidHandler machines
          deck_type: this.selectedDeckType?.fqn
        };
        createdAsset = await firstValueFrom(this.assetService.createMachine(machinePayload));
      } else {
        const resourcePayload: ResourceCreate = {
          name: config.name,
          resource_definition_accession_id: this.selectedDefinition?.accession_id,
        };
        createdAsset = await firstValueFrom(this.assetService.createResource(resourcePayload));
      }

      this.dialogRef.close(createdAsset);
    } catch (error: any) {
      console.error('Error creating asset:', error);
      const msg = error?.message || '';
      if (msg.includes('UNIQUE constraint') || msg.includes('already exists')) {
        this.snackBar.open('An asset with this name already exists. Please use a different name.', 'OK', { duration: 5000 });
      } else {
        this.snackBar.open('Failed to create asset. Please try again.', 'OK', { duration: 5000 });
      }
    } finally {
      this.isLoading.set(false);
    }
  }

  close() {
    this.dialogRef.close();
  }

  /**
   * Check if the current asset type is MACHINE
   */
  get isMachine(): boolean {
    return this.typeStepFormGroup.get('assetType')?.value === 'MACHINE';
  }

  /**
   * Check if selected backend requires connection info
   */
  get requiresConnectionInfo(): boolean {
    return this.selectedBackend?.backend_type === 'hardware';
  }
}
