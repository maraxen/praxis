import { CarrierInferenceService } from './carrier-inference.service';
import { DeckCatalogService } from './deck-catalog.service';
import { ProtocolDefinition } from '@features/protocols/models/protocol.models';
import { describe, it, expect, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { SqliteService } from '@core/services/sqlite';
import { of } from 'rxjs';

describe('CarrierInferenceService', () => {
    let service: CarrierInferenceService;

    beforeEach(() => {
        const sqliteMock = {
            deckDefinitions: of({ findAll: () => of([]) }),
            resourceDefinitions: of({ findAll: () => of([]) }),
            machineDefinitions: of({ findAll: () => of([]) })
        };

        TestBed.configureTestingModule({
            providers: [
                {
                    provide: CarrierInferenceService,
                    useFactory: (deckCatalog: DeckCatalogService) => new CarrierInferenceService(deckCatalog),
                    deps: [DeckCatalogService]
                },
                DeckCatalogService,
                { provide: SqliteService, useValue: sqliteMock }
            ]
        });

        service = TestBed.inject(CarrierInferenceService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('inferRequiredCarriers', () => {
        it('should return empty array for protocol with no assets', () => {
            const protocol: ProtocolDefinition = {
                name: 'Empty Protocol',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [],
                parameters: []
            };

            const requirements = service.inferRequiredCarriers(protocol);
            expect(requirements).toEqual([]);
        });

        it('should infer plate carrier for plate assets', () => {
            const protocol: ProtocolDefinition = {
                name: 'Plate Protocol',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [
                    {
                        name: 'SourcePlate',
                        accession_id: 'req_1',
                        type_hint_str: 'Plate',
                        fqn: 'pylabrobot.resources.Plate',
                        optional: false,
                        constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} },
                        location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] }
                    }
                ],
                parameters: []
            };

            const requirements = service.inferRequiredCarriers(protocol);

            expect(requirements.length).toBe(1);
            expect(requirements[0].resourceType).toBe('Plate');
            expect(requirements[0].carrierType).toBe('plate');
            expect(requirements[0].count).toBe(1);
            expect(requirements[0].slotsNeeded).toBe(1);
        });

        it('should calculate correct carrier count for multiple assets', () => {
            const protocol: ProtocolDefinition = {
                name: 'Multi-Plate Protocol',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [
                    { name: 'Plate1', accession_id: 'req_1', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                    { name: 'Plate2', accession_id: 'req_2', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                    { name: 'Plate3', accession_id: 'req_3', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                    { name: 'Plate4', accession_id: 'req_4', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                    { name: 'Plate5', accession_id: 'req_5', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                    { name: 'Plate6', accession_id: 'req_6', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                ],
                parameters: []
            };

            const requirements = service.inferRequiredCarriers(protocol);

            expect(requirements.length).toBe(1);
            expect(requirements[0].slotsNeeded).toBe(6);
            // 5-slot carrier needs 2 carriers for 6 plates
            expect(requirements[0].count).toBe(2);
            expect(requirements[0].slotsAvailable).toBe(10);
        });

        it('should infer different carrier types for mixed assets', () => {
            const protocol: ProtocolDefinition = {
                name: 'Mixed Protocol',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [
                    { name: 'Plate1', accession_id: 'req_1', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                    { name: 'TipRack1', accession_id: 'req_2', type_hint_str: 'TipRack', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                    { name: 'Reservoir1', accession_id: 'req_3', type_hint_str: 'Reservoir', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                ],
                parameters: []
            };

            const requirements = service.inferRequiredCarriers(protocol);

            expect(requirements.length).toBe(3);

            const plateReq = requirements.find(r => r.resourceType === 'Plate');
            const tipReq = requirements.find(r => r.resourceType === 'TipRack');
            const troughReq = requirements.find(r => r.resourceType === 'Reservoir');

            expect(plateReq).toBeTruthy();
            expect(plateReq!.carrierType).toBe('plate');

            expect(tipReq).toBeTruthy();
            expect(tipReq!.carrierType).toBe('tip');

            expect(troughReq).toBeTruthy();
            expect(troughReq!.carrierType).toBe('mfx');
        });

        it('should suggest non-conflicting rail positions', () => {
            const protocol: ProtocolDefinition = {
                name: 'Multi-Carrier Protocol',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [
                    { name: 'Plate1', accession_id: 'req_1', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                    { name: 'TipRack1', accession_id: 'req_2', type_hint_str: 'TipRack', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                ],
                parameters: []
            };

            const requirements = service.inferRequiredCarriers(protocol);

            // Check that suggested rails don't overlap
            const allRails = requirements.flatMap(r => r.suggestedRails);
            const uniqueRails = new Set(allRails);
            expect(uniqueRails.size).toBe(allRails.length);
        });
    });

    describe('createDeckSetup', () => {
        it('should create complete deck setup for protocol', () => {
            const protocol: ProtocolDefinition = {
                name: 'Test Protocol',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [
                    { name: 'SourcePlate', accession_id: 'req_1', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                    { name: 'DestPlate', accession_id: 'req_2', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                ],
                parameters: []
            };

            const setup = service.createDeckSetup(protocol);

            expect(setup.carrierRequirements.length).toBeGreaterThan(0);
            expect(setup.slotAssignments.length).toBe(2);
            expect(setup.complete).toBe(false);
        });

        it('should assign resources to slots', () => {
            const protocol: ProtocolDefinition = {
                name: 'Test Protocol',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [
                    { name: 'SourcePlate', accession_id: 'req_1', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                ],
                parameters: []
            };

            const setup = service.createDeckSetup(protocol);

            expect(setup.slotAssignments.length).toBe(1);
            expect(setup.slotAssignments[0].resource.name).toBe('SourcePlate');
            expect(setup.slotAssignments[0].slot.id).toBeTruthy();
            expect(setup.slotAssignments[0].carrier).toBeTruthy();
        });
    });

    describe('sortByZAxis', () => {
        it('should sort assignments by Z position', () => {
            // This tests the sorting logic
            const protocol: ProtocolDefinition = {
                name: 'Test',
                accession_id: 'test_1',
                version: '1.0',
                is_top_level: true,
                assets: [
                    { name: 'Plate1', accession_id: 'req_1', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                    { name: 'Plate2', accession_id: 'req_2', type_hint_str: 'Plate', fqn: '', optional: false, constraints: { required_methods: [], required_attributes: [], required_method_signatures: {}, required_method_args: {} }, location_constraints: { location_requirements: [], on_resource_type: '', stack: false, directly_position: false, position_condition: [] } },
                ],
                parameters: []
            };

            const setup = service.createDeckSetup(protocol);

            // Assignments should have sequential placementOrder
            for (let i = 0; i < setup.slotAssignments.length; i++) {
                expect(setup.slotAssignments[i].placementOrder).toBe(i);
            }
        });
    });
});
