import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { AssetService } from './asset.service';
import { SqliteService } from '@core/services/sqlite';
import { Machine, MachineCreate, Resource, ResourceCreate, MachineStatus, ResourceStatus, MachineDefinition, ResourceDefinition } from '../models/asset.models';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ModeService } from '@core/services/mode.service';
import { ApiWrapperService } from '@core/services/api-wrapper.service';
import { of, firstValueFrom } from 'rxjs';

describe('AssetService', () => {
  let service: AssetService;
  let modeService: ModeService;
  let apiWrapper: ApiWrapperService;
  let sqliteService: SqliteService;

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        AssetService,
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: SqliteService,
          useValue: {
            initDb: vi.fn(),
            getResourceDefinitions: vi.fn(),
            getAsyncRepositories: vi.fn().mockReturnValue(of({}))
          }
        },
        {
          provide: ModeService,
          useValue: {
            isBrowserMode: vi.fn().mockReturnValue(false),
            isProductionMode: vi.fn().mockReturnValue(true)
          }
        },
        {
          provide: ApiWrapperService,
          useValue: {
            wrap: vi.fn()
          }
        }
      ]
    });

    service = TestBed.inject(AssetService);
    modeService = TestBed.inject(ModeService);
    apiWrapper = TestBed.inject(ApiWrapperService);
    sqliteService = TestBed.inject(SqliteService);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Machines', () => {
    it('should get machines', () => {
      const mockMachines: Machine[] = [
        { accession_id: 'm1', name: 'Machine 1', status: MachineStatus.IDLE },
        { accession_id: 'm2', name: 'Machine 2', status: MachineStatus.RUNNING }
      ];

      vi.spyOn(apiWrapper, 'wrap').mockReturnValue(of(mockMachines));

      service.getMachines().subscribe(machines => {
        expect(machines.length).toBe(2);
        expect(machines).toEqual(mockMachines);
      });

      expect(apiWrapper.wrap).toHaveBeenCalled();
    });

    it('should create machine', () => {
      const newMachine: MachineCreate = { name: 'New Machine', status: MachineStatus.IDLE };
      const createdMachine: Machine = { accession_id: 'm3', name: newMachine.name, status: newMachine.status! };

      vi.spyOn(apiWrapper, 'wrap').mockReturnValue(of(createdMachine));

      service.createMachine(newMachine).subscribe(machine => {
        expect(machine).toEqual(createdMachine);
      });

      expect(apiWrapper.wrap).toHaveBeenCalled();
    });

    it('should delete machine', () => {
      vi.spyOn(apiWrapper, 'wrap').mockReturnValue(of(null));

      service.deleteMachine('m1').subscribe(response => {
        expect(response).toBeNull();
      });

      expect(apiWrapper.wrap).toHaveBeenCalled();
    });
  });

  describe('Resources', () => {
    it('should get resources', () => {
      const mockResources: Resource[] = [
        { accession_id: 'r1', name: 'Resource 1', status: ResourceStatus.AVAILABLE },
        { accession_id: 'r2', name: 'Resource 2', status: ResourceStatus.IN_USE }
      ];

      vi.spyOn(apiWrapper, 'wrap').mockReturnValue(of(mockResources));

      service.getResources().subscribe(resources => {
        expect(resources.length).toBe(2);
        expect(resources).toEqual(mockResources);
      });

      expect(apiWrapper.wrap).toHaveBeenCalled();
    });

    it('should create resource', () => {
      const newResource: ResourceCreate = { name: 'New Resource', status: ResourceStatus.AVAILABLE };
      const createdResource: Resource = { accession_id: 'r3', name: newResource.name, status: newResource.status! };

      vi.spyOn(apiWrapper, 'wrap').mockReturnValue(of(createdResource));

      service.createResource(newResource).subscribe(resource => {
        expect(resource).toEqual(createdResource);
      });

      expect(apiWrapper.wrap).toHaveBeenCalled();
    });

    it('should delete resource', () => {
      vi.spyOn(apiWrapper, 'wrap').mockReturnValue(of(null));

      service.deleteResource('r1').subscribe(response => {
        expect(response).toBeNull();
      });

      expect(apiWrapper.wrap).toHaveBeenCalled();
    });
  });

  describe('Definitions', () => {
    it('should get machine definitions', () => {
      const mockDefs: MachineDefinition[] = [
        { accession_id: 'md1', name: 'Machine Def 1' },
        { accession_id: 'md2', name: 'Machine Def 2' }
      ];

      vi.spyOn(apiWrapper, 'wrap').mockReturnValue(of(mockDefs));

      service.getMachineDefinitions().subscribe(defs => {
        expect(defs.length).toBe(2);
        expect(defs).toEqual(mockDefs);
      });

      expect(apiWrapper.wrap).toHaveBeenCalled();
    });

    it('should get resource definitions', () => {
      const mockDefs: ResourceDefinition[] = [
        { accession_id: 'rd1', name: 'Resource Def 1', is_consumable: false },
        { accession_id: 'rd2', name: 'Resource Def 2', is_consumable: true }
      ];

      vi.spyOn(apiWrapper, 'wrap').mockReturnValue(of(mockDefs));

      service.getResourceDefinitions().subscribe(defs => {
        expect(defs.length).toBe(2);
        expect(defs).toEqual(mockDefs);
      });

      expect(apiWrapper.wrap).toHaveBeenCalled();
    });
  });

  describe('Browser Mode Facets', () => {
    it('should infer categories correctly in browser mode', () => {
      vi.spyOn(modeService, 'isBrowserMode').mockReturnValue(true);

      const mockDefs: ResourceDefinition[] = [
        { accession_id: 'r1', name: 'R1', plr_category: 'ExplicitCat', is_consumable: false, vendor: 'V1', num_items: 1, plate_type: 'p1', well_volume_ul: 100, tip_volume_ul: 100 } as any,
        { accession_id: 'r2', name: 'R2', plr_category: '', resource_type: 'TypeCat', is_consumable: false, fqn: 'some.fqn' } as any,
        { accession_id: 'r3', name: 'R3', fqn: 'pylabrobot.resources.plates.Cos_96_Well' } as any,
        { accession_id: 'r4', name: 'R4', fqn: 'unknown.thing' } as any
      ];

      vi.spyOn(service, 'getResourceDefinitions').mockReturnValue(of(mockDefs));

      service.getFacets().subscribe(facets => {
        expect(facets.plr_category).toBeDefined();
        const cats = facets.plr_category;
        expect(cats.find(c => c.value === 'ExplicitCat')?.count).toBe(1);
        expect(cats.find(c => c.value === 'TypeCat')?.count).toBe(1);
        expect(cats.find(c => c.value === 'Plate')?.count).toBe(1);
        expect(cats.find(c => c.value === 'Other')?.count).toBe(1);
      });
    });
  });

  describe('Browser Mode CRUD', () => {
    const mockMachineRepo = {
      findAll: vi.fn(),
      create: vi.fn(),
      delete: vi.fn(),
      findOneBy: vi.fn(),
      findBy: vi.fn(),
      update: vi.fn()
    };

    const mockResourceRepo = {
      findAll: vi.fn(),
      create: vi.fn(),
      delete: vi.fn(),
      findOneBy: vi.fn(),
      findBy: vi.fn()
    };

    const mockResourceDefRepo = {
      findAll: vi.fn(),
      findOneBy: vi.fn(),
      findBy: vi.fn(),
      findByPlrCategory: vi.fn()
    };

    const mockRepos = {
      machines: mockMachineRepo,
      resources: mockResourceRepo,
      resourceDefinitions: mockResourceDefRepo,
      machineDefinitions: { findAll: vi.fn() },
      machineFrontendDefinitions: { findAll: vi.fn() },
      machineBackendDefinitions: { findAll: vi.fn() },
      workcells: { findAll: vi.fn() }
    };

    beforeEach(() => {
      vi.spyOn(modeService, 'isBrowserMode').mockReturnValue(true);
      vi.spyOn(sqliteService, 'getAsyncRepositories').mockReturnValue(of(mockRepos as any));
      vi.clearAllMocks();
    });

    describe('Machine CRUD in Browser Mode', () => {
      it('should create machine in browser mode via SqliteService', async () => {
        const newMachine: MachineCreate = {
          name: 'Browser Machine',
          status: MachineStatus.IDLE,
          machine_definition_accession_id: 'def-123'
        };

        mockMachineRepo.create.mockImplementation((m) => of(m));

        const result = await firstValueFrom(service.createMachine(newMachine));

        expect(result.name).toBe(newMachine.name);
        expect(result.status).toBe('idle');
        expect(result.asset_type).toBe('MACHINE');
        expect(mockMachineRepo.create).toHaveBeenCalled();
      });

      it('should get machines from SqliteService in browser mode', async () => {
        const mockMachines = [
          { accession_id: 'bm-001', name: 'Browser Machine 1', status: 'IDLE', machine_category: 'opentrons', fqn: 'mac.1' },
          { accession_id: 'bm-002', name: 'Browser Machine 2', status: 'RUNNING', machine_category: 'hamilton', fqn: 'mac.2' }
        ];

        mockMachineRepo.findAll.mockReturnValue(of(mockMachines));

        const result = await firstValueFrom(service.getMachines());
        expect(result.length).toBe(2);
        expect(result[0].name).toBe('Browser Machine 1');
      });

      it('should delete machine in browser mode', async () => {
        mockMachineRepo.delete.mockReturnValue(of(undefined));
        await expect(firstValueFrom(service.deleteMachine('bm-001'))).resolves.toBeUndefined();
      });
    });

    describe('Resource CRUD in Browser Mode', () => {
      it('should create resource in browser mode via SqliteService', async () => {
        const newResource: ResourceCreate = {
          name: 'Browser Plate',
          status: ResourceStatus.AVAILABLE,
          resource_definition_accession_id: 'plate-def-123'
        };

        mockResourceRepo.create.mockImplementation((r) => of(r));

        const result = await firstValueFrom(service.createResource(newResource));

        expect(result.name).toBe(newResource.name);
        expect(result.status).toBe('available');
        expect(result.asset_type).toBe('RESOURCE');
      });

      it('should get resources from SqliteService in browser mode', async () => {
        const mockResources = [
          { accession_id: 'br-001', name: 'Browser Plate 1', status: 'available' },
          { accession_id: 'br-002', name: 'Browser Tip Rack', status: 'in_use' }
        ];

        mockResourceRepo.findAll.mockReturnValue(of(mockResources));

        const result = await firstValueFrom(service.getResources());
        expect(result.length).toBe(2);
        expect(result[0].name).toBe('Browser Plate 1');
      });

      it('should delete resource in browser mode', async () => {
        mockResourceRepo.delete.mockReturnValue(of(undefined));
        await expect(firstValueFrom(service.deleteResource('br-001'))).resolves.toBeUndefined();
      });
    });
  });
});
