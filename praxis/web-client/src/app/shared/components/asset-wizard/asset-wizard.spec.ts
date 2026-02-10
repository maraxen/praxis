import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { AssetWizard } from './asset-wizard';
import { AssetService } from '@features/assets/services/asset.service';
import { ModeService } from '@core/services/mode.service';
import { DeckCatalogService } from '@features/run-protocol/services/deck-catalog.service';
import { MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MachineFrontendDefinition, MachineBackendDefinition } from '@features/assets/models/asset.models';

// ────────────────────────────────────────────────────────────
// Test Fixtures
// ────────────────────────────────────────────────────────────
const MOCK_FRONTENDS: MachineFrontendDefinition[] = [
  { accession_id: 'fdef-lh', name: 'Liquid Handler', fqn: 'pylabrobot.liquid_handling.LiquidHandler', machine_category: 'LiquidHandler', has_deck: true } as any,
  { accession_id: 'fdef-pr', name: 'Plate Reader', fqn: 'pylabrobot.plate_reading.PlateReader', machine_category: 'PlateReader', has_deck: false } as any,
  { accession_id: 'fdef-img', name: 'Imager', fqn: 'pylabrobot.plate_reading.Imager', machine_category: 'PlateReader', has_deck: false } as any,
  { accession_id: 'fdef-hs', name: 'Heater Shaker', fqn: 'pylabrobot.heating_shaking.HeaterShaker', machine_category: 'Shaker', has_deck: false } as any,
];

const MOCK_LH_BACKENDS: MachineBackendDefinition[] = [
  { accession_id: 'bdef-star', name: 'STAR', fqn: 'pylabrobot.liquid_handling.backends.hamilton.STAR', frontend_definition_accession_id: 'fdef-lh', backend_type: 'hardware', manufacturer: 'Hamilton' } as any,
  { accession_id: 'bdef-sim-lh', name: 'Simulated', fqn: 'pylabrobot.liquid_handling.backends.ChatterboxBackend', frontend_definition_accession_id: 'fdef-lh', backend_type: 'simulator' } as any,
];

const MOCK_PR_BACKENDS: MachineBackendDefinition[] = [
  { accession_id: 'bdef-clario', name: 'CLARIOstar', fqn: 'pylabrobot.plate_reading.clario_star_backend.CLARIOstarBackend', frontend_definition_accession_id: 'fdef-pr', backend_type: 'hardware', manufacturer: 'BMG Labtech' } as any,
  { accession_id: 'bdef-sim-pr', name: 'Simulated', fqn: 'pylabrobot.plate_reading.backends.ChatterboxBackend', frontend_definition_accession_id: 'fdef-pr', backend_type: 'simulator' } as any,
];

// Imager has ZERO backends (by design — this is the bug we're fixing)
const MOCK_IMG_BACKENDS: MachineBackendDefinition[] = [];

const MOCK_HS_BACKENDS: MachineBackendDefinition[] = [
  { accession_id: 'bdef-ham-hs', name: 'HamiltonHeaterShaker', fqn: 'pylabrobot.heating_shaking.backends.hamilton.HamiltonHeaterShaker', frontend_definition_accession_id: 'fdef-hs', backend_type: 'hardware', manufacturer: 'Hamilton' } as any,
  { accession_id: 'bdef-sim-hs', name: 'Simulated', fqn: 'pylabrobot.heating_shaking.backends.ChatterboxBackend', frontend_definition_accession_id: 'fdef-hs', backend_type: 'simulator' } as any,
];

function backendsForFrontend(frontendId: string) {
  const map: Record<string, MachineBackendDefinition[]> = {
    'fdef-lh': MOCK_LH_BACKENDS,
    'fdef-pr': MOCK_PR_BACKENDS,
    'fdef-img': MOCK_IMG_BACKENDS,
    'fdef-hs': MOCK_HS_BACKENDS,
  };
  return of(map[frontendId] || []);
}

describe('AssetWizard', () => {
  let component: AssetWizard;
  let fixture: ComponentFixture<AssetWizard>;

  const mockAssetService = {
    getMachineFacets: () => of({ machine_category: [] }),
    getFacets: () => of({ plr_category: [] }),
    getMachineFrontendDefinitions: () => of(MOCK_FRONTENDS),
    getBackendsForFrontend: (id: string) => backendsForFrontend(id),
    getMachines: () => of([]),
    searchResourceDefinitions: () => of([]),
    createMachine: (payload: any) => of({ ...payload, accession_id: 'test-machine-001' }),
  };

  const mockModeService = {
    isBrowserMode: () => true
  };

  const mockDeckCatalog = {
    getCompatibleDeckTypes: () => []
  };

  const mockDialogRef = {
    close: vi.fn()
  };

  const mockSnackBar = {
    open: () => { }
  };

  beforeEach(async () => {
    mockDialogRef.close.mockClear();

    await TestBed.configureTestingModule({
      imports: [AssetWizard, NoopAnimationsModule],
      providers: [
        { provide: AssetService, useValue: mockAssetService },
        { provide: ModeService, useValue: mockModeService },
        { provide: DeckCatalogService, useValue: mockDeckCatalog },
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: {} },
        { provide: MatSnackBar, useValue: mockSnackBar }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(AssetWizard);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // ────────────────────────────────────────────────────────────
  // Frontend Loading
  // ────────────────────────────────────────────────────────────

  describe('frontend loading on MACHINE type selection', () => {
    it('should load frontend definitions when MACHINE type is selected', async () => {
      component.typeStepFormGroup.patchValue({ assetType: 'MACHINE' });
      fixture.detectChanges();
      await fixture.whenStable();

      const frontends = await component.frontends$.toPromise?.() ||
        await new Promise<any>(resolve => component.frontends$.subscribe(resolve));

      expect(frontends.length).toBeGreaterThan(0);
    });

    it('should NOT load frontend definitions when RESOURCE type is selected', async () => {
      component.typeStepFormGroup.patchValue({ assetType: 'RESOURCE' });
      fixture.detectChanges();
      await fixture.whenStable();

      // frontends$ should remain empty
      const frontends = await new Promise<any>(resolve => component.frontends$.subscribe(resolve));
      expect(frontends.length).toBe(0);
    });
  });

  // ────────────────────────────────────────────────────────────
  // Frontend Selection → Backend Loading
  // ────────────────────────────────────────────────────────────

  describe('frontend selection triggers backend loading', () => {
    it('should load backends when a frontend is selected', async () => {
      // Select MACHINE type first
      component.typeStepFormGroup.patchValue({ assetType: 'MACHINE' });
      fixture.detectChanges();
      await fixture.whenStable();

      // Select the Liquid Handler frontend
      const lhFrontend = MOCK_FRONTENDS[0]; // fdef-lh
      component.selectFrontend(lhFrontend);
      fixture.detectChanges();
      await fixture.whenStable();

      expect(component.selectedFrontend).toBeTruthy();
      expect(component.selectedFrontend!.accession_id).toBe('fdef-lh');

      // Backends should be loaded
      const backends = await new Promise<any>(resolve => component.backends$.subscribe(resolve));
      expect(backends.length).toBe(2); // STAR + Simulated
    });

    it('should load correct backends for PlateReader frontend', async () => {
      component.typeStepFormGroup.patchValue({ assetType: 'MACHINE' });
      fixture.detectChanges();
      await fixture.whenStable();

      const prFrontend = MOCK_FRONTENDS.find(f => f.accession_id === 'fdef-pr')!;
      component.selectFrontend(prFrontend);
      fixture.detectChanges();
      await fixture.whenStable();

      const backends = await new Promise<any>(resolve => component.backends$.subscribe(resolve));
      expect(backends.length).toBe(2); // CLARIOstar + Simulated
      expect(backends[0].accession_id).toBe('bdef-clario');
    });

    it('should reset backend selection when frontend changes', async () => {
      component.typeStepFormGroup.patchValue({ assetType: 'MACHINE' });
      fixture.detectChanges();
      await fixture.whenStable();

      // Select LH and then a backend
      component.selectFrontend(MOCK_FRONTENDS[0]);
      fixture.detectChanges();
      const backends = await new Promise<any>(resolve => component.backends$.subscribe(resolve));
      component.selectBackend(backends[0]);
      expect(component.selectedBackend).toBeTruthy();

      // Now select a different frontend
      component.selectFrontend(MOCK_FRONTENDS[1]);
      fixture.detectChanges();

      // Backend should be reset
      expect(component.selectedBackend).toBeNull();
    });
  });

  // ────────────────────────────────────────────────────────────
  // Category Derivation from Frontend
  // ────────────────────────────────────────────────────────────

  describe('category derivation from selectedFrontend', () => {
    it('should derive machine_category from selectedFrontend in createAsset payload', async () => {
      const createSpy = vi.spyOn(mockAssetService, 'createMachine');

      component.typeStepFormGroup.patchValue({ assetType: 'MACHINE' });
      fixture.detectChanges();
      await fixture.whenStable();

      // Select frontend and backend
      component.selectFrontend(MOCK_FRONTENDS[0]); // LiquidHandler
      fixture.detectChanges();
      await fixture.whenStable();

      const backends = await new Promise<any>(resolve => component.backends$.subscribe(resolve));
      component.selectBackend(backends[0]); // STAR

      // Fill config
      component.configStepFormGroup.patchValue({ name: 'Test LH' });

      await component.createAsset();

      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          machine_category: 'LiquidHandler',
          machine_type: 'LiquidHandler',
          frontend_definition_accession_id: 'fdef-lh',
          backend_definition_accession_id: 'bdef-star',
        })
      );

      createSpy.mockRestore();
    });
  });

  // ────────────────────────────────────────────────────────────
  // Form Validation
  // ────────────────────────────────────────────────────────────

  describe('form validation', () => {
    it('should require frontend selection to proceed', () => {
      component.typeStepFormGroup.patchValue({ assetType: 'MACHINE' });
      fixture.detectChanges();

      // Frontend step should be invalid without selection
      expect(component.frontendStepFormGroup.valid).toBe(false);

      // Select a frontend
      component.selectFrontend(MOCK_FRONTENDS[0]);
      fixture.detectChanges();

      // Should now be valid
      expect(component.frontendStepFormGroup.valid).toBe(true);
    });
  });
});
