import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { RunProtocolComponent } from './run-protocol.component';
import { ProtocolService } from '@features/protocols/services/protocol.service';
import { ExecutionService } from './services/execution.service';
import { ModeService } from '@core/services/mode.service';
import { AppStore } from '@core/store/app.store';
import { ActivatedRoute, Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';
import { signal } from '@angular/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { patchState } from '@ngrx/signals';
import { DeckGeneratorService } from './services/deck-generator.service';
import { AssetService } from '@features/assets/services/asset.service';
import { DeckCatalogService } from './services/deck-catalog.service';
import { WizardStateService } from './services/wizard-state.service';

describe('RunProtocolComponent', () => {
    let component: RunProtocolComponent;
    let fixture: ComponentFixture<RunProtocolComponent>;
    let protocolService: any;
    let executionService: any;
    let modeService: any;
    let store: any;
    let router: any;
    let deckGenerator: any;
    let assetService: any;
    let deckCatalog: any;
    let wizardState: any;

    beforeEach(async () => {
        // Mock matchMedia for AppStore
        Object.defineProperty(window, 'matchMedia', {
            writable: true,
            value: vi.fn().mockImplementation(query => ({
                matches: false,
                media: query,
                onchange: null,
                addListener: vi.fn(),
                removeListener: vi.fn(),
                addEventListener: vi.fn(),
                removeEventListener: vi.fn(),
                dispatchEvent: vi.fn(),
            })),
        });

        protocolService = {
            getProtocols: vi.fn().mockReturnValue(of([])),
            getProtocol: vi.fn()
        };
        executionService = {
            isRunning: signal(false),
            startRun: vi.fn().mockReturnValue(of({ id: 'run-123' })),
            getCompatibility: vi.fn().mockReturnValue(of([]))
        };
        modeService = {
            mode: signal('browser'),
            isBrowserMode: signal(true)
        };
        router = {
            navigate: vi.fn()
        };
        deckGenerator = {
            generateDeckForProtocol: vi.fn().mockReturnValue({ resource: {}, state: {} })
        };
        assetService = {
            getMachineDefinitions: vi.fn().mockReturnValue(of([])),
            getResourceDefinition: vi.fn().mockReturnValue(Promise.resolve(null)),
            getMachineFrontendDefinitions: vi.fn().mockReturnValue(of([])),
            getBackendsForFrontend: vi.fn().mockReturnValue(of([])),
            getMachineBackendDefinitions: vi.fn().mockReturnValue(of([]))
        };
        deckCatalog = {
            getDeckTypeForMachine: vi.fn().mockReturnValue('HamiltonSTARDeck'),
            getDeckDefinition: vi.fn()
        };
        wizardState = {
            getAssetMap: vi.fn().mockReturnValue({}),
            setAssetMap: vi.fn()
        };

        await TestBed.configureTestingModule({
            imports: [RunProtocolComponent, NoopAnimationsModule],
            providers: [
                { provide: ProtocolService, useValue: protocolService },
                { provide: ExecutionService, useValue: executionService },
                { provide: ModeService, useValue: modeService },
                { provide: ActivatedRoute, useValue: { snapshot: { queryParams: {} }, queryParams: of({}) } },
                { provide: Router, useValue: router },
                { provide: MatSnackBar, useValue: { open: vi.fn() } },
                { provide: MatDialog, useValue: { open: vi.fn() } },
                { provide: DeckGeneratorService, useValue: deckGenerator },
                { provide: AssetService, useValue: assetService },
                { provide: DeckCatalogService, useValue: deckCatalog },
                { provide: WizardStateService, useValue: wizardState },
                AppStore
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(RunProtocolComponent);
        component = fixture.componentInstance;
        store = TestBed.inject(AppStore);
        fixture.detectChanges();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    describe('Machine Validation', () => {
        it('should identify simulated machine correctly', () => {
            const simulatedBackend = { backend_type: 'simulator' };
            const selections = [{ argumentName: 'test', selectedBackend: simulatedBackend }] as any;
            
            component.machineSelections.set(selections);
            patchState(store, { simulationMode: false });
            
            expect(component.showMachineError()).toBe(true);
        });

        it('should show error when in Physical mode and machine is simulated', async () => {
            patchState(store, { simulationMode: false });
            
            component.machineSelections.set([
                { 
                  argumentName: 'lh',
                  selectedMachine: { 
                    accession_id: 'm1', 
                    backend_definition: { backend_type: 'simulator' } 
                  }
                } as any
            ]);

            expect(component.showMachineError()).toBe(true);
        });

        it('should NOT show error when in Simulation mode', async () => {
            patchState(store, { simulationMode: true });
            
            component.machineSelections.set([
                { 
                  argumentName: 'lh',
                  selectedMachine: { 
                    accession_id: 'm1', 
                    backend_definition: { backend_type: 'simulator' } 
                  }
                } as any
            ]);

            expect(component.showMachineError()).toBe(false);
        });
    });

    describe('Navigation Guard', () => {
        it('should have unsaved changes if a protocol is selected', () => {
            component.selectedProtocol.set({ id: 'test', accession_id: 'test' } as any);
            expect(component.hasUnsavedChanges()).toBe(true);
        });

        it('should NOT have unsaved changes if no protocol is selected', () => {
            component.selectedProtocol.set(null);
            expect(component.hasUnsavedChanges()).toBe(false);
        });
    });

    describe('State Hydration', () => {
        it('should load state from localStorage', () => {
            const state = {
                protocolId: 'test-proto',
                stepperIndex: 2,
                machineSelections: [{ argumentName: 'lh', selectedMachine: { accession_id: 'm1' } }]
            };
            localStorage.setItem('praxis_run_wizard_state', JSON.stringify(state));
            
            // Mock protocols so find() works
            component.protocols.set([{ accession_id: 'test-proto', name: 'Test' } as any]);
            
            const result = (component as any).loadStateFromStorage();
            expect(result).toBe(true);
            expect(component.selectedProtocol()?.accession_id).toBe('test-proto');
            expect(component.machineSelections()).toEqual(state.machineSelections);
        });

        it('should return false if no state in localStorage', () => {
            localStorage.removeItem('praxis_run_wizard_state');
            const result = (component as any).loadStateFromStorage();
            expect(result).toBe(false);
        });
    });
});
