/// <reference lib="webworker" />

import sqlite3InitModule, { Database, Sqlite3Static } from '@sqlite.org/sqlite-wasm';
import {
    SqliteWorkerRequest,
    SqliteWorkerResponse,
    SqliteExecResult,
    SqliteExecRequest,
    SqliteInitRequest,
    SqliteImportRequest,
    SqliteErrorResponse,
    SqliteBatchExecRequest,
    SqliteInitializedPayload,
    StorageMode,
    CURRENT_SCHEMA_VERSION
} from './sqlite-opfs.types';

let sqlite3: Sqlite3Static | null = null;
let db: Database | null = null;
let poolUtil: any = null;
let currentDbName: string = '/praxis.db';  // Tracks the currently opened database file
let storageMode: StorageMode = 'opfs';     // Tracks whether using OPFS or in-memory fallback

/**
 * VFS requires absolute paths (leading /)
 * This is an internal virtual path within the OPFS origin-private sandbox.
 */
const VFS_DB_NAME = '/praxis.db';

/**
 * Handle incoming messages from the main thread
 */
addEventListener('message', async ({ data }: { data: SqliteWorkerRequest }) => {
    const { id, type, payload } = data;

    try {
        switch (type) {
            case 'init':
                await handleInit(id, payload);
                break;
            case 'exec':
                await handleExec(id, payload);
                break;
            case 'execBatch':
                await handleExecBatch(id, payload);
                break;
            case 'export':
                await handleExport(id);
                break;
            case 'import':
                await handleImport(id, payload);
                break;
            case 'status':
                await handleStatus(id);
                break;
            case 'close':
                await handleClose(id);
                break;
            case 'clear':
                await handleClear(id);
                break;
            default:
                sendError(id, `Unknown request type: ${type}`);
        }
    } catch (error: any) {
        console.error(`[SqliteOpfsWorker] Error handling ${type}:`, error);
        sendError(id, error.message || 'Unknown error', error.stack);
    }
});

/**
 * Initialize SQLite and the OPFS SAHPool VFS
 */
async function handleInit(id: string, payload: SqliteInitRequest) {
    const startTime = performance.now();
    const timings: Record<string, number> = {};

    if (db) {
        sendResponse(id, 'initialized', { success: true, message: 'Already initialized' });
        return;
    }

    const wasmPath = getWasmPath();
    console.log(`[SqliteOpfsWorker] Initializing SQLite WASM from ${wasmPath}`);

    try {
        sqlite3 = await (sqlite3InitModule as any)({
            print: console.log,
            printErr: console.error,
            locateFile: (file: string) => `${wasmPath}${file}`
        });
    } catch (err) {
        console.error('[SqliteOpfsWorker] Failed to load WASM module:', err);
        throw err;
    }
    timings['wasmLoad'] = performance.now() - startTime;

    if (!sqlite3) {
        throw new Error('Failed to initialize SQLite WASM module');
    }

    // Attempt OPFS SAHPool VFS - fallback to in-memory on failure
    let useMemoryFallback = false;

    if (typeof (sqlite3 as any).installOpfsSAHPoolVfs !== 'function') {
        console.warn('[SqliteOpfsWorker] OPFS SAHPool not available, falling back to in-memory DB');
        useMemoryFallback = true;
    } else {
        // Install opfs-sahpool VFS (SyncAccessHandle Pool)
        // This VFS is preferred for performance and doesn't require SharedArrayBuffer
        // proxyUri must point to our copied asset to avoid Vite's dynamic import issues
        try {
            poolUtil = await (sqlite3 as any).installOpfsSAHPoolVfs({
                name: 'opfs-sahpool', // Standard name used by the library
                directory: 'praxis-data',
                clearOnInit: false,
                proxyUri: `${wasmPath}sqlite3-opfs-async-proxy.js`
            });
            console.log('[SqliteOpfsWorker] opfs-sahpool VFS installed successfully');
        } catch (err) {
            console.warn('[SqliteOpfsWorker] Failed to install opfs-sahpool VFS, falling back to in-memory:', err);
            useMemoryFallback = true;
        }
    }

    timings['vfsInstall'] = performance.now() - startTime;

    // Open the database
    const dbName = payload.dbName || VFS_DB_NAME;
    currentDbName = dbName;

    if (useMemoryFallback) {
        // In-memory database fallback (no persistence)
        storageMode = 'memory';
        db = new sqlite3.oo1.DB(':memory:', 'c');
        console.warn('[SqliteOpfsWorker] Using in-memory database - data will NOT persist across sessions');
    } else {
        // Use OPFS SAHPool VFS
        storageMode = 'opfs';
        if (poolUtil?.OpfsSAHPoolDb) {
            db = new poolUtil.OpfsSAHPoolDb(dbName);
        } else {
            db = new sqlite3.oo1.DB({
                filename: dbName,
                vfs: 'opfs-sahpool'
            });
        }
        console.log(`[SqliteOpfsWorker] Database "${dbName}" opened with opfs-sahpool VFS`);
    }

    // Check schema version for migration handling
    if (!db) {
        throw new Error('Database failed to open');
    }
    const versionResult = db.exec({
        sql: 'PRAGMA user_version',
        rowMode: 'array',
        returnValue: 'resultRows'
    });
    const storedVersion = (versionResult as any)?.[0]?.[0] ?? 0;

    if (storedVersion !== 0 && storedVersion !== CURRENT_SCHEMA_VERSION) {
        console.warn(`[SqliteOpfsWorker] Schema mismatch: stored=${storedVersion}, expected=${CURRENT_SCHEMA_VERSION}`);
        sendResponse(id, 'schema_mismatch', {
            currentVersion: storedVersion,
            expectedVersion: CURRENT_SCHEMA_VERSION
        });
        return;
    }

    timings['total'] = performance.now() - startTime;
    console.log(`[SqliteOpfsWorker] Initialization complete in ${timings['total'].toFixed(1)}ms (WASM: ${timings['wasmLoad']?.toFixed(1)}ms, VFS: ${(timings['vfsInstall'] - timings['wasmLoad']).toFixed(1)}ms, mode: ${storageMode})`);

    const response: SqliteInitializedPayload = {
        success: true,
        storageMode,
        initTimeMs: timings,
        message: storageMode === 'memory' ? 'Using in-memory database (no persistence)' : undefined
    };
    sendResponse(id, 'initialized', response);
}

/**
 * Execute SQL statements
 */
async function handleExec(id: string, payload: SqliteExecRequest) {
    if (!db) throw new Error('Database not initialized');

    const { sql, bind, rowMode = 'object', returnValue = 'resultRows' } = payload;

    const columnNames: string[] = [];
    const resultRows = db.exec({
        sql,
        bind,
        rowMode,
        columnNames,
        returnValue
    } as any);

    const result: SqliteExecResult = {
        resultRows: Array.isArray(resultRows) ? resultRows : [],
        columnNames,
        rowCount: Array.isArray(resultRows) ? resultRows.length : 0,
        changes: db.changes(),
        lastInsertRowid: db.selectValue('SELECT last_insert_rowid()') as number
    };

    sendResponse(id, 'execResult', result);
}

/**
 * Execute multiple SQL statements in a single transaction
 */
async function handleExecBatch(id: string, payload: SqliteBatchExecRequest) {
    if (!db) throw new Error('Database not initialized');

    const { operations } = payload;

    try {
        db.exec('BEGIN TRANSACTION');
        for (const op of operations) {
            db.exec({
                sql: op.sql,
                bind: op.bind
            });
        }
        db.exec('COMMIT');
    } catch (err) {
        try {
            db.exec('ROLLBACK');
        } catch (_) {
            // Rollback failed, likely already rolled back or connection lost
        }
        throw err;
    }

    sendResponse(id, 'execResult', {
        rowCount: operations.length,
        resultRows: [],
        changes: db.changes()
    });
}

/**
 * Export the database to a Uint8Array
 */
async function handleExport(id: string) {
    if (!db || !poolUtil) throw new Error('Database not initialized');

    const dbName = db.filename;
    console.log(`[SqliteOpfsWorker] Exporting database: ${dbName}`);

    // Use the pool utility to export the file directly from OPFS
    const data = await poolUtil.exportFile(dbName);

    if (!data) {
        throw new Error('Failed to export database (no data received)');
    }

    sendResponse(id, 'exportResult', data, [data.buffer]);
}

/**
 * Import database from Uint8Array
 */
async function handleImport(id: string, payload: SqliteImportRequest) {
    if (!sqlite3 || !poolUtil) throw new Error('SQLite not initialized');

    const { data } = payload;
    const dbName = currentDbName;  // Use currently opened database, not hardcoded path

    console.log(`[SqliteOpfsWorker] Importing database to ${dbName}, size: ${data.byteLength} bytes`);
    if (typeof poolUtil.getFileNames === 'function') {
        console.log('[SqliteOpfsWorker] VFS files before import:', poolUtil.getFileNames());
    }

    // Close current database if open
    if (db) {
        console.log('[SqliteOpfsWorker] Closing current DB before import');
        db.close();
        db = null;
    }

    // CRITICAL: Delete existing OPFS file before import.
    // The SAH Pool VFS importDb may not properly overwrite existing files.
    if (typeof poolUtil.unlink === 'function') {
        try {
            await poolUtil.unlink(dbName);
            console.log(`[SqliteOpfsWorker] Deleted existing ${dbName}`);
        } catch (err: any) {
            // File may not exist yet, that's fine
            console.log(`[SqliteOpfsWorker] No existing ${dbName} to delete (or error):`, err.message);
        }
    }

    // Import the new database file into OPFS
    await poolUtil.importDb(dbName, data);
    console.log(`[SqliteOpfsWorker] Database file imported`);

    // Re-open the database
    if (poolUtil.OpfsSAHPoolDb) {
        db = new poolUtil.OpfsSAHPoolDb(dbName);
    } else {
        db = new sqlite3.oo1.DB({
            filename: dbName,
            vfs: 'opfs-sahpool'
        });
    }

    console.log(`[SqliteOpfsWorker] Database ${dbName} imported and re-opened`);

    sendResponse(id, 'importResult', { success: true });
}

/**
 * Get the status of the SAHPool VFS
 */
async function handleStatus(id: string) {
    if (!poolUtil) {
        sendResponse(id, 'error', { message: 'Pool utility not initialized' });
        return;
    }

    const capacity = poolUtil.getCapacity ? poolUtil.getCapacity() : -1;
    const fileCount = poolUtil.getFileCount ? poolUtil.getFileCount() : -1;
    const files = poolUtil.getFileNames ? poolUtil.getFileNames() : [];

    sendResponse(id, 'execResult', {
        capacity,
        fileCount,
        files
    });
}

/**
 * Close the database
 */
async function handleClose(id: string) {
    if (db) {
        db.close();
        db = null;
    }
    sendResponse(id, 'closed', {});
}

/**
 * Clear all database files from OPFS (factory reset)
 * 
 * CRITICAL: For E2E test isolation, we should only delete the current database file,
 * NOT wipe all files via poolUtil.wipeFiles(), because parallel workers share the same OPFS.
 */
async function handleClear(id: string) {
    console.log(`[SqliteOpfsWorker] Clearing database: ${currentDbName}`);

    // Close current database if open
    if (db) {
        db.close();
        db = null;
    }

    if (poolUtil && typeof poolUtil.unlink === 'function') {
        // Only delete the specific database file for this worker/instance
        try {
            await poolUtil.unlink(currentDbName);
            console.log(`[SqliteOpfsWorker] Deleted ${currentDbName}`);
        } catch (err: any) {
            console.warn(`[SqliteOpfsWorker] Could not delete ${currentDbName}:`, err.message);
        }
    } else {
        console.warn('[SqliteOpfsWorker] Pool utility unlink not available for clear operation');
    }

    console.log('[SqliteOpfsWorker] Database cleared.');
    sendResponse(id, 'closed', {}); // Reuse 'closed' response type
}

/**
 * Helper to send success responses
 */
function sendResponse(id: string, type: SqliteWorkerResponse['type'], payload: any, transfer?: Transferable[]) {
    postMessage({ id, type, payload } as SqliteWorkerResponse, { transfer });
}

/**
 * Helper to send error responses
 */
function sendError(id: string, message: string, stack?: string) {
    postMessage({
        id,
        type: 'error',
        payload: { message, stack } as SqliteErrorResponse
    } as SqliteWorkerResponse);
}

/**
 * Helper to get the WASM path based on the worker's location
 */
function getWasmPath(): string {
    const origin = self.location.origin;
    const path = self.location.pathname;

    // Detect if we are on GitHub Pages (subdirectory /praxis/)
    const isGhPages = path.includes('/praxis/');
    const root = isGhPages ? '/praxis/' : '/';

    return `${origin}${root}assets/wasm/`;
}
