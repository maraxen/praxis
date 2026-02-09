/**
 * Seed Coverage Tests — tests for the coverage-based seedDefaultAssets() logic.
 * 
 * Since seedDefaultAssets() is private, we test it via resetToDefaults()
 * and initializeFreshDatabase(), which call it in sequence.
 * We mock the worker communication layer (sendRequest) and the exec/execBatch
 * methods to verify the seeding SQL operations.
 */
import { TestBed } from '@angular/core/testing';
import { SqliteOpfsService } from './sqlite-opfs.service';
import { of } from 'rxjs';
import { describe, it, expect, beforeEach, vi, type Mock } from 'vitest';

describe('SqliteOpfsService - seedDefaultAssets coverage', () => {
    let service: SqliteOpfsService;
    let execSpy: Mock;
    let execBatchSpy: Mock;

    const MOCK_DEFINITIONS = [
        { accession_id: 'def-001', name: '96-well Plate', fqn: 'resources.plate.96well' },
        { accession_id: 'def-002', name: 'Tip Rack 200uL', fqn: 'resources.tips.200ul' },
        { accession_id: 'def-003', name: 'Reservoir 300mL', fqn: 'resources.trough.300ml' },
    ];

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [SqliteOpfsService]
        });
        service = TestBed.inject(SqliteOpfsService);

        // Access private methods via bracket notation for testing
        execSpy = vi.fn();
        execBatchSpy = vi.fn().mockReturnValue(of(void 0));
        (service as any).exec = execSpy;
        (service as any).execBatch = execBatchSpy;
    });

    it('should seed all definitions when no instances exist', () => {
        // Definitions query returns 3 defs
        execSpy.mockReturnValueOnce(of({
            resultRows: MOCK_DEFINITIONS
        }));
        // Existing resources query returns nothing (no coverage)
        execSpy.mockReturnValueOnce(of({
            resultRows: []
        }));

        (service as any).seedDefaultAssets().subscribe();

        // Should have called execBatch with 3 INSERT operations
        expect(execBatchSpy).toHaveBeenCalledTimes(1);
        const operations = execBatchSpy.mock.calls[0][0];
        expect(operations).toHaveLength(3);

        // Verify each operation inserts the correct definition
        for (let i = 0; i < operations.length; i++) {
            const op = operations[i];
            expect(op.sql).toContain('INSERT OR IGNORE INTO resources');
            // bind[1] = name, bind[2] = fqn derived, bind[5] = properties_json, bind[6] = def accession_id
            expect(op.bind[1]).toBe(MOCK_DEFINITIONS[i].name);
            expect(op.bind[6]).toBe(MOCK_DEFINITIONS[i].accession_id);
            expect(op.bind[7]).toBe('available'); // status

            // Verify auto_instantiated tagging
            const props = JSON.parse(op.bind[5]);
            expect(props.auto_instantiated).toBe(true);
            expect(props.source).toBe('seed');
        }
    });

    it('should skip definitions that already have instances', () => {
        execSpy.mockReturnValueOnce(of({
            resultRows: MOCK_DEFINITIONS
        }));
        // def-001 and def-003 already have instances
        execSpy.mockReturnValueOnce(of({
            resultRows: [
                { resource_definition_accession_id: 'def-001', cnt: 2 },
                { resource_definition_accession_id: 'def-003', cnt: 1 },
            ]
        }));

        (service as any).seedDefaultAssets().subscribe();

        // Should only seed def-002 (the one without instances)
        expect(execBatchSpy).toHaveBeenCalledTimes(1);
        const operations = execBatchSpy.mock.calls[0][0];
        expect(operations).toHaveLength(1);
        expect(operations[0].bind[1]).toBe('Tip Rack 200uL');
        expect(operations[0].bind[6]).toBe('def-002');
    });

    it('should skip entirely when all definitions have instances', () => {
        execSpy.mockReturnValueOnce(of({
            resultRows: MOCK_DEFINITIONS
        }));
        // All definitions already covered
        execSpy.mockReturnValueOnce(of({
            resultRows: [
                { resource_definition_accession_id: 'def-001', cnt: 1 },
                { resource_definition_accession_id: 'def-002', cnt: 1 },
                { resource_definition_accession_id: 'def-003', cnt: 1 },
            ]
        }));

        (service as any).seedDefaultAssets().subscribe();

        // Should NOT call execBatch at all
        expect(execBatchSpy).not.toHaveBeenCalled();
    });

    it('should handle empty definitions gracefully', () => {
        execSpy.mockReturnValueOnce(of({
            resultRows: []
        }));

        (service as any).seedDefaultAssets().subscribe();

        // No definitions → no seeding → no execBatch call
        expect(execBatchSpy).not.toHaveBeenCalled();
    });

    it('should generate correct FQN format for seeded instances', () => {
        execSpy.mockReturnValueOnce(of({
            resultRows: [{ accession_id: 'def-x', name: 'My Custom Plate', fqn: 'resources.plate.custom' }]
        }));
        execSpy.mockReturnValueOnce(of({ resultRows: [] }));

        (service as any).seedDefaultAssets().subscribe();

        const operations = execBatchSpy.mock.calls[0][0];
        expect(operations).toHaveLength(1);
        // FQN should be: resources.default.<cleaned_name>
        expect(operations[0].bind[2]).toBe('resources.default.my_custom_plate');
    });
});
