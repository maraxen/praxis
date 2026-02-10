import { TestBed } from '@angular/core/testing';
import { WizardStateService } from './wizard-state.service';
import { CarrierInferenceService } from './carrier-inference.service';
import { DeckCatalogService } from './deck-catalog.service';
import { ConsumableAssignmentService } from './consumable-assignment.service';
import { ProtocolDefinition } from '@features/protocols/models/protocol.models';
import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('WizardStateService', () => {
    let service: WizardStateService;
    let mockCarrierInference: any;

    beforeEach(() => {
        mockCarrierInference = {
            createDeckSetup: vi.fn().mockReturnValue({
                carrierRequirements: [],
                slotAssignments: [],
                stackingHints: [],
                complete: false
            })
        };

        TestBed.configureTestingModule({
            providers: [
                {
                    provide: WizardStateService,
                    useFactory: (a: any, b: any, c: any) => new WizardStateService(a, b, c),
                    deps: [CarrierInferenceService, DeckCatalogService, ConsumableAssignmentService]
                },
                { provide: CarrierInferenceService, useValue: mockCarrierInference },
                { provide: DeckCatalogService, useValue: {} },
                { provide: ConsumableAssignmentService, useValue: {} }
            ]
        });

        service = TestBed.inject(WizardStateService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('initialize', () => {
        it('should initialize with protocol', () => {
            const protocol: ProtocolDefinition = {
                name: 'Test Protocol',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };

            service.initialize(protocol);

            expect(service.currentStep()).toBe('carrier-placement');
            expect(service.protocol()).toBe(protocol);
            expect(mockCarrierInference.createDeckSetup).toHaveBeenCalled();
        });

        it('should start with empty assignments for empty protocol', () => {
            const protocol: ProtocolDefinition = {
                name: 'Empty',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };

            service.initialize(protocol);

            expect(service.carrierRequirements().length).toBe(0);
            expect(service.slotAssignments().length).toBe(0);
        });
    });

    describe('step navigation', () => {
        beforeEach(() => {
            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };
            service.initialize(protocol);
        });

        it('should start at carrier-placement', () => {
            expect(service.currentStep()).toBe('carrier-placement');
        });

        it('should navigate to next step', () => {
            service.nextStep();
            expect(service.currentStep()).toBe('resource-placement');

            service.nextStep();
            expect(service.currentStep()).toBe('verification');
        });

        it('should navigate to previous step', () => {
            service.nextStep();
            service.nextStep();
            expect(service.currentStep()).toBe('verification');

            service.previousStep();
            expect(service.currentStep()).toBe('resource-placement');

            service.previousStep();
            expect(service.currentStep()).toBe('carrier-placement');
        });

        it('should not go before first step', () => {
            service.previousStep();
            expect(service.currentStep()).toBe('carrier-placement');
        });
    });

    describe('carrier placement tracking', () => {
        beforeEach(() => {
            mockCarrierInference.createDeckSetup.mockReturnValue({
                carrierRequirements: [
                    { carrierFqn: 'fqn1', placed: false },
                    { carrierFqn: 'fqn2', placed: false }
                ],
                slotAssignments: [],
                stackingHints: [],
                complete: false
            });

            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };
            service.initialize(protocol);
        });

        it('should mark carrier as placed', () => {
            const reqs = service.carrierRequirements();
            expect(reqs[0].placed).toBe(false);

            service.markCarrierPlaced(reqs[0].carrierFqn, true);

            expect(service.carrierRequirements()[0].placed).toBe(true);
        });

        it('should compute allCarriersPlaced correctly', () => {
            expect(service.allCarriersPlaced()).toBe(false);

            const reqs = service.carrierRequirements();
            for (const req of reqs) {
                service.markCarrierPlaced(req.carrierFqn, true);
            }

            expect(service.allCarriersPlaced()).toBe(true);
        });
    });

    describe('skip and complete', () => {
        beforeEach(() => {
            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };
            service.initialize(protocol);
        });

        it('should handle skip', () => {
            service.skip();
            expect(service.skipped()).toBe(true);
            expect(service.isComplete()).toBe(true);
        });

        it('should handle complete', () => {
            service.complete();
            expect(service.isComplete()).toBe(true);
            expect(service.skipped()).toBe(false);
        });
    });

    describe('state persistence', () => {
        it('should get and restore state', () => {
            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };
            service.initialize(protocol);
            service.nextStep();

            const state = service.getState();

            service.reset();
            expect(service.currentStep()).toBe('carrier-placement');

            service.restoreState(state);
            expect(service.currentStep()).toBe('resource-placement');
        });
    });

    describe('progress computation', () => {
        it('should compute progress correctly', () => {
            mockCarrierInference.createDeckSetup.mockReturnValue({
                carrierRequirements: [{ carrierFqn: 'c1', placed: false }],
                slotAssignments: [{ resource: { name: 'r1' }, placed: false }],
                stackingHints: [],
                complete: false
            });

            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };
            service.initialize(protocol);

            expect(service.progress()).toBe(0);

            // Mark carrier placed
            service.markCarrierPlaced('c1', true);

            // 1 / 2 = 50%
            expect(service.progress()).toBe(50);
        });
    });

    describe('deckResource computed signal', () => {
        const mockCarrier = {
            id: 'carrier_1',
            fqn: 'pylabrobot.resources.hamilton.plate_carriers.PLT_CAR_L5AC_A00',
            name: 'PLT_CAR_L5AC',
            type: 'plate' as const,
            railPosition: 7,
            railSpan: 6,
            slots: [
                {
                    id: 'carrier_1_slot_0',
                    index: 0,
                    name: 'Position 1',
                    compatibleResourceTypes: ['Plate'],
                    occupied: false,
                    resource: null,
                    position: { x: 10, y: 10, z: 0 },
                    dimensions: { width: 127, height: 85 }
                }
            ],
            dimensions: { width: 135, height: 497, depth: 10 }
        };

        const mockResource = {
            name: 'my_plate',
            type: 'Plate',
            location: { x: 10, y: 0, z: 0, type: 'Coordinate' },
            size_x: 127.76,
            size_y: 85.48,
            size_z: 14.5,
            children: []
        };

        let mockDeckCatalog: any;

        beforeEach(() => {
            mockDeckCatalog = {
                getDeckDefinition: vi.fn().mockReturnValue({
                    fqn: 'HamiltonSTARDeck',
                    name: 'Hamilton STAR Deck',
                    manufacturer: 'Hamilton',
                    layoutType: 'rail-based',
                    numRails: 30,
                    railSpacing: 22.5,
                    dimensions: { width: 1200, height: 653.5, depth: 500 }
                })
            };

            mockCarrierInference.createDeckSetup.mockReturnValue({
                carrierRequirements: [{
                    resourceType: 'Plate',
                    count: 1,
                    carrierFqn: mockCarrier.fqn,
                    carrierType: 'plate',
                    carrierName: mockCarrier.name,
                    slotsNeeded: 1,
                    slotsAvailable: 5,
                    suggestedRails: [7],
                    placed: false
                }],
                slotAssignments: [{
                    resource: mockResource,
                    slot: mockCarrier.slots[0],
                    carrier: mockCarrier,
                    placementOrder: 0,
                    placed: false
                }],
                stackingHints: [],
                complete: false
            });

            TestBed.resetTestingModule();
            TestBed.configureTestingModule({
                providers: [
                    {
                        provide: WizardStateService,
                        useFactory: (a: any, b: any, c: any) => new WizardStateService(a, b, c),
                        deps: [CarrierInferenceService, DeckCatalogService, ConsumableAssignmentService]
                    },
                    { provide: CarrierInferenceService, useValue: mockCarrierInference },
                    { provide: DeckCatalogService, useValue: mockDeckCatalog },
                    { provide: ConsumableAssignmentService, useValue: {} }
                ]
            });

            service = TestBed.inject(WizardStateService);
        });

        it('should return a valid deck shell with correct dimensions after initialization', () => {
            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };
            service.initialize(protocol);

            const deck = service.deckResource();
            expect(deck).toBeTruthy();
            expect(deck.name).toBe('deck');
            expect(deck.type).toBe('HamiltonSTARDeck');
            expect(deck.size_x).toBe(1200);
            expect(deck.size_y).toBe(653.5);
            expect(deck.size_z).toBe(500);
        });

        it('should have empty children when no carriers are placed', () => {
            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };
            service.initialize(protocol);

            const deck = service.deckResource();
            expect(deck.children).toEqual([]);
        });

        it('should add carrier as deck child when markCarrierPlaced is called', () => {
            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };
            service.initialize(protocol);

            service.markCarrierPlaced(mockCarrier.fqn, true);

            const deck = service.deckResource();
            expect(deck.children.length).toBe(1);
            expect(deck.children[0].name).toBe(mockCarrier.name);
            expect(deck.children[0].type).toContain('PLT_CAR_L5AC_A00');
            expect(deck.children[0].size_x).toBe(135);
            expect(deck.children[0].size_y).toBe(497);
        });

        it('should add resource as carrier child when markResourcePlaced is called', () => {
            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };
            service.initialize(protocol);

            // Place carrier first, then resource
            service.markCarrierPlaced(mockCarrier.fqn, true);
            service.markResourcePlaced(mockResource.name, true);

            const deck = service.deckResource();
            const carrier = deck.children[0];
            expect(carrier.children.length).toBe(1);
            expect(carrier.children[0].name).toBe('my_plate');
            expect(carrier.children[0].type).toBe('Plate');
            expect(carrier.children[0].size_x).toBe(127.76);
        });

        it('should remove carrier child when placement is reverted', () => {
            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };
            service.initialize(protocol);

            service.markCarrierPlaced(mockCarrier.fqn, true);
            expect(service.deckResource().children.length).toBe(1);

            service.markCarrierPlaced(mockCarrier.fqn, false);
            expect(service.deckResource().children.length).toBe(0);
        });

        it('should show resource under carrier only when BOTH are placed', () => {
            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };
            service.initialize(protocol);

            // Place resource without placing carrier first
            service.markResourcePlaced(mockResource.name, true);

            const deck = service.deckResource();
            // Carrier not placed, so no children on deck
            expect(deck.children.length).toBe(0);
        });

        it('should use correct carrier position from railPosition and rail spacing', () => {
            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };
            service.initialize(protocol);

            service.markCarrierPlaced(mockCarrier.fqn, true);

            const carrier = service.deckResource().children[0];
            // railPosition=7, railSpacing=22.5, offset=100 → x = 100 + 7*22.5 = 257.5
            expect(carrier.location.x).toBe(257.5);
        });
        describe('buildExecutionManifest', () => {
            beforeEach(() => {
                const protocol: ProtocolDefinition = {
                    name: 'Test',
                    accession_id: 'test_1',
                    version: '1.0',
                    is_top_level: true,
                    assets: [],
                    parameters: [
                        { name: 'source_plate', type_hint: 'Plate', default_value_repr: 'None', fqn: 'pylabrobot.resources.Plate' }
                    ]
                };
                service.initialize(protocol);
            });

            it('should build a valid manifest', () => {
                const machineConfigs = [
                    {
                        param_name: 'liquid_handler',
                        machine_type: 'LiquidHandler',
                        backend_fqn: 'pylabrobot.liquid_handling.backends.hamilton.STAR.STAR',
                        is_simulated: true
                    }
                ];

                const manifest = service.buildExecutionManifest(machineConfigs);

                expect(manifest.protocol.requires_deck).toBe(true);
                expect(manifest.machines.length).toBe(1);
                expect(manifest.machines[0].machine_type).toBe('LiquidHandler');
                expect(manifest.machines[0].deck).toBeTruthy();
                expect(manifest.parameters.length).toBe(1);
                expect(manifest.parameters[0].name).toBe('source_plate');
                expect(manifest.parameters[0].value).toBe('source_plate'); // Fix 1: Value should match name for deck resources
                expect(manifest.parameters[0].is_deck_resource).toBe(true);
            });

            it('should include correct deck manifest', () => {
                const machineConfigs = [{ param_name: 'lh', machine_type: 'LiquidHandler', backend_fqn: 'STAR', is_simulated: true }];
                const manifest = service.buildExecutionManifest(machineConfigs);
                const deck = manifest.machines[0].deck;

                expect(deck).toBeTruthy();
                expect(deck?.fqn).toBe('pylabrobot.resources.hamilton.STARDeck');
                expect(deck?.layout_type).toBe('rail-based');
            });
        });
    });
});
