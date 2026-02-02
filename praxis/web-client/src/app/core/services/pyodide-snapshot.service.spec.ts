import { TestBed } from '@angular/core/testing';
import { PyodideSnapshotService } from './pyodide-snapshot.service';

// TODO: Un-skip these tests once the vitest environment has proper IndexedDB support.
// The current jsdom environment does not have a working implementation of IndexedDB,
// which causes these tests to fail.
describe.skip('PyodideSnapshotService', () => {
    let service: PyodideSnapshotService;

    beforeEach(() => {
        TestBed.configureTestingModule({
            providers: [PyodideSnapshotService]
        });
        service = TestBed.inject(PyodideSnapshotService);
    });

    describe('hasSnapshot', () => {
        it('returns false when no snapshot exists', async () => {
            const result = await service.hasSnapshot();
            expect(result).toBe(false);
        });

        it('returns true after snapshot is saved', async () => {
            await service.saveSnapshot(new Uint8Array([1, 2, 3]));
            const result = await service.hasSnapshot();
            expect(result).toBe(true);
        });

        it('supports custom keys', async () => {
            await service.saveSnapshot(new Uint8Array([1, 2, 3]), 'custom-key');
            expect(await service.hasSnapshot('custom-key')).toBe(true);
            expect(await service.hasSnapshot('other-key')).toBe(false);
        });
    });

    describe('getSnapshot', () => {
        it('returns null when no snapshot exists', async () => {
            const result = await service.getSnapshot();
            expect(result).toBeNull();
        });

        it('returns saved snapshot data', async () => {
            const data = new Uint8Array([1, 2, 3]);
            await service.saveSnapshot(data);
            const result = await service.getSnapshot();
            expect(result).toEqual(data);
        });

        it('returns correct snapshot for specific key', async () => {
            const data1 = new Uint8Array([1, 2, 3]);
            const data2 = new Uint8Array([4, 5, 6]);
            await service.saveSnapshot(data1, 'key1');
            await service.saveSnapshot(data2, 'key2');

            expect(await service.getSnapshot('key1')).toEqual(data1);
            expect(await service.getSnapshot('key2')).toEqual(data2);
        });
    });

    describe('invalidateSnapshot', () => {
        it('removes existing snapshot', async () => {
            await service.saveSnapshot(new Uint8Array([1, 2, 3]));
            await service.invalidateSnapshot();
            const result = await service.hasSnapshot();
            expect(result).toBe(false);
        });

        it('only invalidates specified key', async () => {
            await service.saveSnapshot(new Uint8Array([1, 2, 3]), 'key1');
            await service.saveSnapshot(new Uint8Array([4, 5, 6]), 'key2');
            await service.invalidateSnapshot('key1');

            expect(await service.hasSnapshot('key1')).toBe(false);
            expect(await service.hasSnapshot('key2')).toBe(true);
        });
    });

    describe('getSnapshotVersion', () => {
        it('returns version string for cache busting', async () => {
            const version = service.getSnapshotVersion();
            expect(typeof version).toBe('string');
            expect(version.length).toBeGreaterThan(0);
        });
    });
});
