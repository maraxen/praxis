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
});
