import { ComponentFixture, TestBed } from '@angular/core/testing';
import { SettingsComponent } from './settings.component';
import { AppStore } from '@core/store/app.store';
import { OnboardingService } from '@core/services/onboarding.service';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { SqliteService } from '@core/services/sqlite';
import { BrowserService } from '@core/services/browser.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog } from '@angular/material/dialog';
import { of } from 'rxjs';

describe('SettingsComponent', () => {
    let component: SettingsComponent;
    let fixture: ComponentFixture<SettingsComponent>;

    // Mocks
    const storeMock = {
        theme: vi.fn(() => 'system'),
        setTheme: vi.fn(),
        maintenanceEnabled: vi.fn(() => true),
        setMaintenanceEnabled: vi.fn(),
        infiniteConsumables: vi.fn(() => false),
        setInfiniteConsumables: vi.fn()
    };

    const onboardingMock = {
        showHints: vi.fn(() => false),
        enableHints: vi.fn(),
        disableHints: vi.fn(),
        resetTooltips: vi.fn()
    };

    const sqliteMock = {
        exportDatabase: vi.fn(),
        importDatabase: vi.fn(),
        resetToDefaults: vi.fn()
    };

    const snackBarMock = {
        open: vi.fn()
    };

    const dialogMock = {
        open: vi.fn()
    };

    const browserMock = {
        reload: vi.fn()
    };

    beforeEach(async () => {
        vi.clearAllMocks();

        await TestBed.configureTestingModule({
            imports: [SettingsComponent],
            providers: [
                { provide: AppStore, useValue: storeMock },
                { provide: OnboardingService, useValue: onboardingMock },
                { provide: SqliteService, useValue: sqliteMock },
                { provide: MatSnackBar, useValue: snackBarMock },
                { provide: MatDialog, useValue: dialogMock },
                { provide: BrowserService, useValue: browserMock }
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(SettingsComponent);
        component = fixture.componentInstance;
        fixture.detectChanges();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('should create', () => {
        expect(component).toBeTruthy();
    });

    it('should set theme', () => {
        component.setTheme('dark');
        expect(storeMock.setTheme).toHaveBeenCalledWith('dark');
    });

    it('should call exportDatabase when exportData is called', async () => {
        sqliteMock.exportDatabase.mockResolvedValue(undefined);
        await component.exportData();
        expect(sqliteMock.exportDatabase).toHaveBeenCalled();
        expect(snackBarMock.open).toHaveBeenCalledWith('Database exported', 'OK', { duration: 3000 });
    });

    it('should handle export failure', async () => {
        sqliteMock.exportDatabase.mockRejectedValue(new Error('Export failed'));
        await component.exportData();
        expect(snackBarMock.open).toHaveBeenCalledWith('Export failed', 'OK', { duration: 3000 });
    });

    it('should open confirmation dialog when importData is called', async () => {
        const file = new File([''], 'test.db', { type: 'application/x-sqlite3' });
        const event = { target: { files: [file] } } as unknown as Event;

        const dialogRefMock = {
            afterClosed: vi.fn(() => of(true))
        };
        dialogMock.open.mockReturnValue(dialogRefMock);
        sqliteMock.importDatabase.mockResolvedValue(undefined);

        await component.importData(event);

        expect(dialogMock.open).toHaveBeenCalled();
        expect(sqliteMock.importDatabase).toHaveBeenCalledWith(file);

        // Use fake timers to test setTimeout
        vi.useFakeTimers();
        // Wait for the subscribe block to execute
        await Promise.resolve();
        vi.advanceTimersByTime(2000);

        expect(browserMock.reload).toHaveBeenCalled();

        vi.useRealTimers();
    });
});
