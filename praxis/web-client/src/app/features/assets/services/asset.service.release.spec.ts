import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { AssetService } from './asset.service';
import { SqliteService } from '@core/services/sqlite';
import { ModeService } from '@core/services/mode.service';
import { ApiWrapperService } from '@core/services/api-wrapper.service';
import { ResourceStatus, Resource } from '../models/asset.models';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { of, firstValueFrom } from 'rxjs';

/**
 * TDD Tests for AssetService.releaseResource()
 *
 * Model C Hybrid Lifecycle:
 * - After protocol completion, resources are either reused or depleted
 * - Reuse → status becomes AVAILABLE
 * - Deplete → status becomes DEPLETED
 */
describe('AssetService - releaseResource', () => {
    let service: AssetService;
    let modeService: ModeService;
    let sqliteService: SqliteService;

    const mockResourceRepo = {
        findAll: vi.fn(),
        findBy: vi.fn(),
        findOneBy: vi.fn(),
        create: vi.fn(),
        update: vi.fn(),
        delete: vi.fn()
    };

    const mockRepos = {
        machines: { findAll: vi.fn(), create: vi.fn(), delete: vi.fn(), findOneBy: vi.fn(), findBy: vi.fn(), update: vi.fn() },
        resources: mockResourceRepo,
        resourceDefinitions: { findAll: vi.fn(), findOneBy: vi.fn(), findBy: vi.fn(), findByPlrCategory: vi.fn() },
        machineDefinitions: { findAll: vi.fn() },
        machineFrontendDefinitions: { findAll: vi.fn() },
        machineBackendDefinitions: { findAll: vi.fn() },
        workcells: { findAll: vi.fn() }
    };

    const MOCK_IN_USE_RESOURCE: Resource = {
        accession_id: 'res-001',
        name: 'Corning 96 DWP',
        fqn: 'resources.default.corning_96_dwp',
        status: ResourceStatus.IN_USE,
        resource_definition_accession_id: 'def-plate-001',
        asset_type: 'RESOURCE',
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        properties_json: { auto_instantiated: true, source: 'protocol_setup' }
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
    });

    it('should set status to AVAILABLE for outcome "reuse"', async () => {
        mockResourceRepo.update.mockImplementation((id: string, updates: any) =>
            of({ ...MOCK_IN_USE_RESOURCE, ...updates })
        );

        const result = await firstValueFrom(
            service.releaseResource('res-001', 'reuse')
        );

        expect(result.status).toBe(ResourceStatus.AVAILABLE);
        expect(mockResourceRepo.update).toHaveBeenCalledWith(
            'res-001',
            expect.objectContaining({ status: ResourceStatus.AVAILABLE })
        );
    });

    it('should set status to DEPLETED for outcome "deplete"', async () => {
        mockResourceRepo.update.mockImplementation((id: string, updates: any) =>
            of({ ...MOCK_IN_USE_RESOURCE, ...updates })
        );

        const result = await firstValueFrom(
            service.releaseResource('res-001', 'deplete')
        );

        expect(result.status).toBe(ResourceStatus.DEPLETED);
        expect(mockResourceRepo.update).toHaveBeenCalledWith(
            'res-001',
            expect.objectContaining({ status: ResourceStatus.DEPLETED })
        );
    });

    it('should update the updated_at timestamp', async () => {
        const beforeCall = new Date().toISOString();

        mockResourceRepo.update.mockImplementation((id: string, updates: any) =>
            of({ ...MOCK_IN_USE_RESOURCE, ...updates })
        );

        const result = await firstValueFrom(
            service.releaseResource('res-001', 'reuse')
        );

        expect(mockResourceRepo.update).toHaveBeenCalledWith(
            'res-001',
            expect.objectContaining({
                updated_at: expect.any(String)
            })
        );

        // Verify the timestamp is recent (within 5 seconds)
        const updatedAt = new Date((mockResourceRepo.update.mock.calls[0][1] as any).updated_at);
        const now = new Date();
        expect(now.getTime() - updatedAt.getTime()).toBeLessThan(5000);
    });
});
