import { DeckGeneratorService } from './deck-generator.service';
import { DeckCatalogService } from './deck-catalog.service';
import { ProtocolDefinition } from '@features/protocols/models/protocol.models';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Machine, MachineStatus } from '@features/assets/models/asset.models';
import { TestBed } from '@angular/core/testing';
import { SqliteService } from '@core/services/sqlite';
import { AssetService } from '@features/assets/services/asset.service';
import { of } from 'rxjs';

describe('DeckGeneratorService', () => {
    let service: DeckGeneratorService;

    beforeEach(() => {
        const sqliteMock = {
            deckDefinitions: of({ findAll: () => of([]) }),
            resourceDefinitions: of({ findAll: () => of([]) }),
            machineDefinitions: of({ findAll: () => of([]) })
        };

        const assetServiceMock = {
            getResourceDefinition: vi.fn().mockResolvedValue(null)
        };

        TestBed.configureTestingModule({
            providers: [
                {
                    provide: DeckGeneratorService,
                    useFactory: (deckCatalog: DeckCatalogService, assetService: AssetService) => 
                        new DeckGeneratorService(deckCatalog, assetService),
                    deps: [DeckCatalogService, AssetService]
                },
                DeckCatalogService,
                { provide: SqliteService, useValue: sqliteMock },
                { provide: AssetService, useValue: assetServiceMock }
            ]
        });

        service = TestBed.inject(DeckGeneratorService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should use machine definition when available', () => {
        const protocol: ProtocolDefinition = {
            name: 'Test',
            is_top_level: true,
            accession_id: 'test_1',
            assets: [],
            version: '1.0',
            parameters: []
        };

        const machineWithDef: Machine = {
            accession_id: 'mach_def_1',
            name: 'Machine with Def',
            status: MachineStatus.IDLE,
            plr_definition: {
                name: 'Custom Deck',
                type: 'CustomDeck',
                location: { x: 0, y: 0, z: 0 },
                children: []
            },
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        };

        const data = service.generateDeckForProtocol(protocol, undefined, machineWithDef);

        expect(data.resource.name).toBe('Custom Deck');
        expect(data.resource.type).toBe('CustomDeck');
    });

    it('should generate a Hamilton STAR deck by default (no machine)', () => {
        const protocol: ProtocolDefinition = {
            name: 'Test Protocol',
            is_top_level: true,
            accession_id: 'test_1',
            assets: [],
            version: '1.0',
            parameters: []
        };
        const data = service.generateDeckForProtocol(protocol);

        expect(data.resource.type).toBe('pylabrobot.resources.hamilton.HamiltonSTARDeck');
        expect(data.resource.num_rails).toBe(30);
        expect(data.resource.size_x).toBe(1200);
    });

    it('should generate an OT-2 deck when OT-2 machine is provided', () => {
        const protocol: ProtocolDefinition = {
            name: 'Test Protocol',
            is_top_level: true,
            accession_id: 'test_1',
            assets: [],
            version: '1.0',
            parameters: []
        };

        const ot2Machine: Machine = {
            accession_id: 'mach_1',
            name: 'My OT-2',
            machine_type: 'Opentrons OT-2',
            model: 'OT-2', // Triggers detection
            status: MachineStatus.IDLE,
            user_configured_capabilities: {},
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        };

        const data = service.generateDeckForProtocol(protocol, undefined, ot2Machine);

        expect(data.resource.type).toBe('pylabrobot.resources.opentrons.deck.OTDeck');
        expect(data.resource.num_rails).toBeUndefined(); // Should NOT have rails
        // OT-2 Width
        expect(data.resource.size_x).toBeCloseTo(624.3);
    });

    it('should generate an empty OT-2 deck (no auto-placed resources)', () => {
        const protocol: ProtocolDefinition = {
            name: 'Test',
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
                    constraints: {},
                    location_constraints: {}
                }
            ] as any,
            parameters: []
        };

        const ot2Machine: Machine = {
            accession_id: 'mach_1',
            name: 'My OT-2',
            machine_type: 'Opentrons OT-2',
            model: 'OT-2',
            status: MachineStatus.IDLE,
            user_configured_capabilities: {},
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
        };

        const data = service.generateDeckForProtocol(protocol, undefined, ot2Machine);

        // Should NOT have user assets auto-placed
        const plate = data.resource.children.find(c => c.name === 'ghost_SourcePlate');
        expect(plate).toBeUndefined();

        // Should have Trash if spec defined it (mock spec handled by DeckCatalogService)
        // Note: DeckCatalogService is real in this test, so it should have OT2 slots including trash
        const trash = data.resource.children.find(c => c.name === 'Trash');
        if (trash) {
            expect(trash.type).toBe('Trash');
        }
    });

    it('should generate an empty Hamilton deck (no default carriers or ghosts)', () => {
        const protocol: ProtocolDefinition = {
            name: 'Test',
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
                    constraints: {},
                    location_constraints: {}
                }
            ] as any,
            parameters: []
        };

        const data = service.generateDeckForProtocol(protocol); // No asset map

        // Should have NO carriers
        const carriers = data.resource.children.filter(c => c.type.includes('Carrier'));
        expect(carriers.length).toBe(0);

        // Should have NO ghost resources
        const ghost = data.resource.children.find(c => c.name.startsWith('ghost_'));
        expect(ghost).toBeUndefined();
    });
});
