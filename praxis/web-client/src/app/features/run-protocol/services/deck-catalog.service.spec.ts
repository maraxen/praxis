import { DeckCatalogService } from './deck-catalog.service';
import { describe, it, expect, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { SqliteService } from '@core/services/sqlite';
import { of } from 'rxjs';

describe('DeckCatalogService', () => {
    let service: DeckCatalogService;
    let mockSqlite: any;

    beforeEach(() => {
        mockSqlite = {
            deckDefinitions: of({
                findAll: () => [],
                create: (val: any) => val
            })
        };

        TestBed.configureTestingModule({
            providers: [
                DeckCatalogService,
                { provide: SqliteService, useValue: mockSqlite }
            ]
        });
        service = TestBed.inject(DeckCatalogService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    describe('getHamiltonSTARSpec', () => {
        it('should return correct deck specification', () => {
            const spec = service.getHamiltonSTARSpec();

            expect(spec.fqn).toBe('pylabrobot.resources.hamilton.HamiltonSTARDeck');
            expect(spec.name).toBe('Hamilton STAR Deck');
            expect(spec.manufacturer).toBe('Hamilton');
            expect(spec.numRails).toBe(30);
            expect(spec.railSpacing).toBe(22.5);
        });

        it('should have correct dimensions', () => {
            const spec = service.getHamiltonSTARSpec();

            expect(spec.dimensions.width).toBe(1200);
            expect(spec.dimensions.height).toBe(653.5);
            expect(spec.dimensions.depth).toBe(500);
        });

        it('should have hardware-accurate rail positions', () => {
            const spec = service.getHamiltonSTARSpec();

            expect(spec.railPositions).toBeDefined();
            expect(spec.railPositions!.length).toBe(30);

            // First rail at offset 100mm
            expect(spec.railPositions![0]).toBe(100);

            // Second rail at 100 + 22.5 = 122.5mm
            expect(spec.railPositions![1]).toBe(122.5);

            // Last rail at 100 + (29 * 22.5) = 752.5mm
            expect(spec.railPositions![29]).toBe(752.5);
        });
    });

    describe('getDeckDefinition', () => {
        it('should return Hamilton STAR spec for matching FQN', () => {
            const spec = service.getDeckDefinition('pylabrobot.resources.hamilton.HamiltonSTARDeck');
            expect(spec).toBeTruthy();
            expect(spec!.numRails).toBe(30);
        });

        it('should return Hamilton STAR spec for short name', () => {
            const spec = service.getDeckDefinition('HamiltonSTARDeck');
            expect(spec).toBeTruthy();
        });

        it('should return null for unknown deck', () => {
            const spec = service.getDeckDefinition('UnknownDeck');
            expect(spec).toBeNull();
        });
    });

    describe('getCompatibleCarriers', () => {
        it('should return carriers for Hamilton deck', () => {
            const carriers = service.getCompatibleCarriers('HamiltonSTARDeck');

            expect(carriers.length).toBeGreaterThan(0);
            expect(carriers.find(c => c.type === 'plate')).toBeTruthy();
            expect(carriers.find(c => c.type === 'tip')).toBeTruthy();
        });

        it('should return plate carrier with correct specs', () => {
            const carriers = service.getCompatibleCarriers('Hamilton');
            const plateCarrier = carriers.find(c => c.type === 'plate');

            expect(plateCarrier).toBeTruthy();
            expect(plateCarrier!.numSlots).toBe(5);
            expect(plateCarrier!.railSpan).toBe(6);
        });

        it('should return empty array for unknown deck', () => {
            const carriers = service.getCompatibleCarriers('UnknownDeck');
            expect(carriers).toEqual([]);
        });

        it('should use correct PLR module paths for Hamilton carriers', () => {
            const carriers = service.getCompatibleCarriers('HamiltonSTARDeck');

            for (const carrier of carriers) {
                // FQN must NOT reference non-existent ml_star module
                expect(carrier.fqn).not.toContain('ml_star');

                // FQN must point to real PLR hamilton submodules
                expect(carrier.fqn).toMatch(
                    /^pylabrobot\.resources\.hamilton\.(plate_carriers|tip_carriers|mfx_carriers)\./
                );

                // Carrier factory name must be UPPERCASE (PLR convention)
                const factoryName = carrier.fqn.split('.').pop()!;
                expect(factoryName).toMatch(/^[A-Z]/); // starts with uppercase
            }
        });

        it('should return Tecan carriers for EVO decks', () => {
            const carriers = service.getCompatibleCarriers('TecanEVO150');

            expect(carriers.length).toBeGreaterThan(0);
            expect(carriers.find(c => c.type === 'plate')).toBeTruthy();
            expect(carriers.find(c => c.type === 'tip')).toBeTruthy();

            // Tecan FQNs must point to real PLR tecan submodules
            for (const carrier of carriers) {
                expect(carrier.fqn).toMatch(
                    /^pylabrobot\.resources\.tecan\.(plate_carriers|tip_carriers)\./
                );
            }
        });
    });

    describe('createDeckConfiguration', () => {
        it('should create configuration with rails', () => {
            const spec = service.getHamiltonSTARSpec();
            const config = service.createDeckConfiguration(spec);

            expect(config.deckType).toBe(spec.fqn);
            expect(config.deckName).toBe(spec.name);
            expect(config.numRails).toBe(30);
            expect(config.rails.length).toBe(30);
        });

        it('should create rails with correct positions', () => {
            const spec = service.getHamiltonSTARSpec();
            const config = service.createDeckConfiguration(spec);

            // Verify first rail
            expect(config.rails[0].index).toBe(0);
            expect(config.rails[0].xPosition).toBe(100);
            expect(config.rails[0].width).toBe(22.5);

            // Verify rail 10
            expect(config.rails[10].index).toBe(10);
            expect(config.rails[10].xPosition).toBe(100 + 10 * 22.5);
        });

        it('should start with empty carriers', () => {
            const spec = service.getHamiltonSTARSpec();
            const config = service.createDeckConfiguration(spec);

            expect(config.carriers).toEqual([]);
        });
    });

    describe('createCarrierFromDefinition', () => {
        it('should create carrier with correct properties', () => {
            const carriers = service.getCompatibleCarriers('Hamilton');
            const plateCarrierDef = carriers.find(c => c.type === 'plate')!;

            const carrier = service.createCarrierFromDefinition(
                plateCarrierDef,
                'carrier_1',
                5
            );

            expect(carrier.id).toBe('carrier_1');
            expect(carrier.fqn).toBe(plateCarrierDef.fqn);
            expect(carrier.railPosition).toBe(5);
            expect(carrier.type).toBe('plate');
        });

        it('should create slots for carrier', () => {
            const carriers = service.getCompatibleCarriers('Hamilton');
            const plateCarrierDef = carriers.find(c => c.type === 'plate')!;

            const carrier = service.createCarrierFromDefinition(
                plateCarrierDef,
                'plate_carrier_1',
                5
            );

            expect(carrier.slots.length).toBe(5);
            expect(carrier.slots[0].id).toBe('plate_carrier_1_slot_0');
            expect(carrier.slots[0].name).toBe('Position 1');
            expect(carrier.slots[0].occupied).toBe(false);
        });

        it('should create slots with compatible resource types', () => {
            const carriers = service.getCompatibleCarriers('Hamilton');
            const tipCarrierDef = carriers.find(c => c.type === 'tip')!;

            const carrier = service.createCarrierFromDefinition(
                tipCarrierDef,
                'tip_carrier_1',
                15
            );

            expect(carrier.slots[0].compatibleResourceTypes).toContain('TipRack');
        });

        describe('getDeckTypeForMachine', () => {
            it('should return Hamilton deck for Hamilton machine', () => {
                const machine: any = {
                    machine_category: 'HamiltonSTAR',
                    model: 'STAR',
                    manufacturer: 'Hamilton'
                };
                expect(service.getDeckTypeForMachine(machine)).toBe('pylabrobot.resources.hamilton.HamiltonSTARDeck');
            });

            it('should return OT-2 deck for Opentrons machine', () => {
                const machine: any = {
                    machine_category: 'OpentronsOT2',
                    model: 'OT-2',
                    manufacturer: 'Opentrons'
                };
                expect(service.getDeckTypeForMachine(machine)).toBe('pylabrobot.resources.opentrons.deck.OTDeck');
            });

            it('should return Hamilton deck from connection info', () => {
                const machine: any = {
                    connection_info: { backend: 'pylabrobot.liquid_handling.backends.hamilton.STAR' }
                };
                expect(service.getDeckTypeForMachine(machine)).toBe('pylabrobot.resources.hamilton.HamiltonSTARDeck');
            });

            it('should return null for unknown machine', () => {
                const machine: any = {
                    machine_category: 'Unknown',
                    manufacturer: 'Unknown'
                };
                expect(service.getDeckTypeForMachine(machine)).toBeNull();
            });
        });
    });

    describe('PlrResource Synthesis', () => {
        it('should create PlrResource from spec', () => {
            const spec = service.getHamiltonSTARSpec();
            const res = service.createPlrResourceFromSpec(spec);

            expect(res.name).toBe('deck');
            expect(res.type).toBe(spec.fqn);
            expect(res.size_x).toBe(spec.dimensions.width);
            expect(res.num_rails).toBe(30);
        });

        it('should create PlrResource from config with carriers', () => {
            const spec = service.getHamiltonSTARSpec();
            const config = service.createDeckConfiguration(spec);

            // Add a carrier
            const carriers = service.getCompatibleCarriers('Hamilton');
            const plateCarrierDef = carriers.find(c => c.type === 'plate')!;
            const carrier = service.createCarrierFromDefinition(plateCarrierDef, 'c1', 5);

            // Add labware to slot 0
            carrier.slots[0].resource = {
                name: 'p1',
                type: 'Plate',
                location: { x: 0, y: 0, z: 0, type: 'Coordinate' },
                size_x: 127.76,
                size_y: 85.48,
                size_z: 15,
                children: []
            };

            config.carriers.push(carrier);

            const res = service.createPlrResourceFromConfig(config);

            expect(res.children.length).toBe(1);
            const carrierRes = res.children[0];
            expect(carrierRes.name).toBe('c1');
            expect(carrierRes.type).toBe(plateCarrierDef.fqn);

            // Check slot and resource
            const slotRes = carrierRes.children[0];
            expect(slotRes.type).toBe('Site');
            expect(slotRes.children[0].name).toBe('p1');
            expect(slotRes.children[0].size_z).toBe(15);
        });
    });
});
