import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AssetService } from './asset.service';
import { SqliteService } from '@core/services/sqlite';
import { ModeService } from '@core/services/mode.service';
import { ApiWrapperService } from '@core/services/api-wrapper.service';
import { ResourceStatus, ResourceDefinition, Resource } from '../models/asset.models';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of, firstValueFrom } from 'rxjs';

/**
 * TDD Tests for AssetService.resolveOrCreateResource()
 *
 * Model C Hybrid Lifecycle:
 * - If an available instance exists for a definition → return it, set IN_USE
 * - If no instance exists → auto-create from definition, tag as auto_instantiated
 * - In production mode → delegate to API
 */
describe('AssetService - resolveOrCreateResource', () => {
  let service: AssetService;
  let modeService: ModeService;
  let sqliteService: SqliteService;
  let apiWrapper: ApiWrapperService;

  const mockResourceRepo = {
    findAll: vi.fn(),
    findBy: vi.fn(),
    findOneBy: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn()
  };

  const mockResourceDefRepo = {
    findAll: vi.fn(),
    findOneBy: vi.fn(),
    findBy: vi.fn(),
    findByPlrCategory: vi.fn()
  };

  const mockRepos = {
    machines: { findAll: vi.fn(), create: vi.fn(), delete: vi.fn(), findOneBy: vi.fn(), findBy: vi.fn(), update: vi.fn() },
    resources: mockResourceRepo,
    resourceDefinitions: mockResourceDefRepo,
    machineDefinitions: { findAll: vi.fn() },
    machineFrontendDefinitions: { findAll: vi.fn() },
    machineBackendDefinitions: { findAll: vi.fn() },
    workcells: { findAll: vi.fn() }
  };

  const MOCK_DEFINITION: ResourceDefinition = {
    accession_id: 'def-plate-001',
    name: 'Corning 96 DWP',
    fqn: 'pylabrobot.resources.corning.Corning_96_DWP',
    is_consumable: true,
    plr_category: 'Plate',
    vendor: 'Corning',
    num_items: 96
  };

  const MOCK_EXISTING_INSTANCE: Resource = {
    accession_id: 'res-001',
    name: 'Corning 96 DWP',
    fqn: 'resources.default.corning_96_dwp',
    status: ResourceStatus.AVAILABLE,
    resource_definition_accession_id: 'def-plate-001',
    asset_type: 'RESOURCE',
    properties_json: { auto_instantiated: true, source: 'seed' }
  } as any;

  beforeEach(() => {
    vi.clearAllMocks();
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
            getAsyncRepositories: vi.fn().mockReturnValue(of(mockRepos))
          }
        },
        {
          provide: ModeService,
          useValue: {
            isBrowserMode: vi.fn().mockReturnValue(true),
            isProductionMode: vi.fn().mockReturnValue(false)
          }
        },
        {
          provide: ApiWrapperService,
          useValue: { wrap: vi.fn() }
        }
      ]
    });

    service = TestBed.inject(AssetService);
    modeService = TestBed.inject(ModeService);
    sqliteService = TestBed.inject(SqliteService);
    apiWrapper = TestBed.inject(ApiWrapperService);
  });

  it('should return existing available instance when one exists', async () => {
    // Arrange: definition exists, one available instance exists
    mockResourceDefRepo.findOneBy.mockReturnValue(of(MOCK_DEFINITION));
    mockResourceRepo.findBy.mockReturnValue(of([MOCK_EXISTING_INSTANCE]));
    mockResourceRepo.update.mockImplementation((id: string, updates: any) =>
      of({ ...MOCK_EXISTING_INSTANCE, ...updates })
    );

    // Act
    const result = await firstValueFrom(
      service.resolveOrCreateResource('def-plate-001')
    );

    // Assert: returned instance is the existing one, now IN_USE
    expect(result.accession_id).toBe('res-001');
    expect(result.status).toBe(ResourceStatus.IN_USE);
    expect(mockResourceRepo.create).not.toHaveBeenCalled();
  });

  it('should create new instance when no available instance exists', async () => {
    // Arrange: definition exists, but no instances
    mockResourceDefRepo.findOneBy.mockReturnValue(of(MOCK_DEFINITION));
    mockResourceRepo.findBy.mockReturnValue(of([])); // No instances
    mockResourceRepo.create.mockImplementation((resource: any) => of(resource));

    // Act
    const result = await firstValueFrom(
      service.resolveOrCreateResource('def-plate-001')
    );

    // Assert: a new instance was created
    expect(result.name).toBe('Corning 96 DWP');
    expect(result.status).toBe(ResourceStatus.IN_USE);
    expect(result.resource_definition_accession_id).toBe('def-plate-001');
    expect(mockResourceRepo.create).toHaveBeenCalledTimes(1);
  });

  it('should tag auto-created instance with auto_instantiated metadata', async () => {
    // Arrange: no instances exist
    mockResourceDefRepo.findOneBy.mockReturnValue(of(MOCK_DEFINITION));
    mockResourceRepo.findBy.mockReturnValue(of([]));
    mockResourceRepo.create.mockImplementation((resource: any) => of(resource));

    // Act
    const result = await firstValueFrom(
      service.resolveOrCreateResource('def-plate-001')
    );

    // Assert: properties_json has auto_instantiated tag
    expect(result.properties_json).toBeDefined();
    expect(result.properties_json.auto_instantiated).toBe(true);
    expect(result.properties_json.source).toBe('protocol_setup');
  });

  it('should set status to IN_USE on resolved instance', async () => {
    // Arrange: existing available instance
    mockResourceDefRepo.findOneBy.mockReturnValue(of(MOCK_DEFINITION));
    mockResourceRepo.findBy.mockReturnValue(of([MOCK_EXISTING_INSTANCE]));
    mockResourceRepo.update.mockImplementation((id: string, updates: any) =>
      of({ ...MOCK_EXISTING_INSTANCE, ...updates })
    );

    // Act
    const result = await firstValueFrom(
      service.resolveOrCreateResource('def-plate-001')
    );

    // Assert
    expect(result.status).toBe(ResourceStatus.IN_USE);
  });

  it('should prefer available instances over creating new ones', async () => {
    // Arrange: one available, one in-use
    const inUseInstance: Resource = {
      ...MOCK_EXISTING_INSTANCE,
      accession_id: 'res-002',
      status: ResourceStatus.IN_USE
    } as any;

    mockResourceDefRepo.findOneBy.mockReturnValue(of(MOCK_DEFINITION));
    mockResourceRepo.findBy.mockReturnValue(of([inUseInstance, MOCK_EXISTING_INSTANCE]));
    mockResourceRepo.update.mockImplementation((id: string, updates: any) =>
      of({ ...MOCK_EXISTING_INSTANCE, ...updates })
    );

    // Act
    const result = await firstValueFrom(
      service.resolveOrCreateResource('def-plate-001')
    );

    // Assert: picked the available one, not the in-use one
    expect(result.accession_id).toBe('res-001');
    expect(mockResourceRepo.create).not.toHaveBeenCalled();
  });

  it('should create instance when all existing are in use', async () => {
    // Arrange: all instances are in-use
    const inUse1: Resource = { ...MOCK_EXISTING_INSTANCE, accession_id: 'res-002', status: ResourceStatus.IN_USE } as any;
    const inUse2: Resource = { ...MOCK_EXISTING_INSTANCE, accession_id: 'res-003', status: ResourceStatus.IN_USE } as any;

    mockResourceDefRepo.findOneBy.mockReturnValue(of(MOCK_DEFINITION));
    mockResourceRepo.findBy.mockReturnValue(of([inUse1, inUse2]));
    mockResourceRepo.create.mockImplementation((resource: any) => of(resource));

    // Act
    const result = await firstValueFrom(
      service.resolveOrCreateResource('def-plate-001')
    );

    // Assert: new instance created since none were available
    expect(mockResourceRepo.create).toHaveBeenCalledTimes(1);
    expect(result.status).toBe(ResourceStatus.IN_USE);
    expect(result.properties_json.auto_instantiated).toBe(true);
  });
});
