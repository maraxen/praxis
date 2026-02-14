/**
 * Types for SQLite OPFS Web Worker communication
 */

export type RowMode = 'array' | 'object';

export interface SqliteBatchExecRequest {
    operations: {
        sql: string;
        bind?: any[];
    }[];
}

export interface SqliteWorkerRequest {
    id: string;
    type: 'init' | 'exec' | 'execBatch' | 'export' | 'import' | 'status' | 'close' | 'clear';
    payload: any;
}

export interface SqliteInitRequest {
    dbName?: string;
    /** Optional directory in OPFS to use for the SAH pool. Defaults to 'praxis-data' */
    poolDirectory?: string;
    /** The base href of the application, used for resolving WASM and other assets. */
    baseHref?: string;
}

export interface SqliteExecRequest {
    sql: string;
    bind?: any[];
    rowMode?: RowMode;
    returnValue?: 'this' | 'resultRows' | 'saveSql';
}

export interface SqliteImportRequest {
    data: Uint8Array;
}

export interface SqliteWorkerResponse {
    id: string;
    type: 'initialized' | 'execResult' | 'exportResult' | 'importResult' | 'error' | 'closed' | 'schema_mismatch';
    payload: any;
}

export interface SqliteExecResult {
    resultRows: any[];
    columnNames: string[];
    rowCount: number;
    changes: number;
    lastInsertRowid?: number | bigint;
}

export interface SqliteErrorResponse {
    message: string;
    code?: string;
    stack?: string;
}

export interface SqliteSchemaMismatchPayload {
    currentVersion: number;
    expectedVersion: number;
}

/** Storage mode indicating where DB is persisted */
export type StorageMode = 'opfs' | 'memory';

/** Payload returned when worker successfully initializes */
export interface SqliteInitializedPayload {
    success: boolean;
    storageMode: StorageMode;
    initTimeMs: Record<string, number>;
    message?: string;
}

// Schema version constant - bump this when schema changes
export const CURRENT_SCHEMA_VERSION = 1;

