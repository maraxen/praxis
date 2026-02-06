import { TestBed } from '@angular/core/testing';
import { SqliteService } from './sqlite.service';
import { SqliteOpfsService } from './sqlite-opfs.service';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('SqliteService', () => {
    let service: SqliteService;
    let mockOpfs: any;

    beforeEach(() => {
        mockOpfs = {
            init: vi.fn(),
            exportDatabase: vi.fn(),
            importDatabase: vi.fn(),
            close: vi.fn(),
            resetToDefaults: vi.fn()
        };

        // Default behavior: init returns immediate success
        mockOpfs.init.mockReturnValue(of(void 0));
        mockOpfs.exportDatabase.mockReturnValue(of(new Uint8Array([])));
        mockOpfs.importDatabase.mockReturnValue(of(void 0));
        mockOpfs.close.mockReturnValue(of(void 0));
        mockOpfs.resetToDefaults.mockReturnValue(of(void 0));

        TestBed.configureTestingModule({
            providers: [
                SqliteService,
                { provide: SqliteOpfsService, useValue: mockOpfs }
            ]
        });
        service = TestBed.inject(SqliteService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should initialize opfs on construction and update status', () => {
        // Constructor already called init
        expect(mockOpfs.init).toHaveBeenCalled();

        // Check status via signal
        const status = service.status();
        expect(status.initialized).toBe(true);
        expect(status.source).toBe('opfs');
    });

    it('should delegate exportDatabase to opfs', () => {
        service.exportDatabase().subscribe();
        expect(mockOpfs.exportDatabase).toHaveBeenCalled();
    });

    it('should delegate resetToDefaults to opfs', () => {
        service.resetToDefaults().subscribe();
        expect(mockOpfs.resetToDefaults).toHaveBeenCalled();
    });
});
