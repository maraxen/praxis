# Import/Export & OPFS VFS Audit

## Status: ✅ Fully Modernized

The import/export logic has been fully modernized to use OPFS (Origin Private File System) with the `opfs-sahpool` VFS (SyncAccessHandle Pool).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Import/Export Flow                          │
├─────────────────────────────────────────────────────────────────┤
│  UI (settings.component.ts)                                      │
│  ├─ Export: sqlite.exportDatabase() → download .db file          │
│  └─ Import: File input → sqlite.importDatabase(Uint8Array)       │
│                            ↓                                     │
│  SqliteService (sqlite.service.ts)                               │
│  └─ Delegates to → SqliteOpfsService                             │
│                            ↓                                     │
│  SqliteOpfsService (sqlite-opfs.service.ts)                      │
│  └─ sendRequest('export') / sendRequest('import')                │
│                            ↓                                     │
│  Web Worker (sqlite-opfs.worker.ts)                              │
│  ├─ Export: poolUtil.exportFile(dbName) → Uint8Array             │
│  └─ Import: poolUtil.unlink() → poolUtil.importDb() → reopen     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Implementation Details

### VFS Selection

[sqlite-opfs.worker.ts:102-148](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/workers/sqlite-opfs.worker.ts#L102-148)

```typescript
// Attempt OPFS SAHPool VFS - fallback to in-memory on failure
if (typeof sqlite3.installOpfsSAHPoolVfs !== 'function') {
    useMemoryFallback = true;
} else {
    poolUtil = await sqlite3.installOpfsSAHPoolVfs({
        name: 'opfs-sahpool',
        directory: 'praxis-data',
        clearOnInit: false,
        proxyUri: `${wasmPath}sqlite3-opfs-async-proxy.js`
    });
}
```

### Export Implementation

[sqlite-opfs.worker.ts:247-261](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/workers/sqlite-opfs.worker.ts#L247-261)

```typescript
async function handleExport(id: string) {
    if (!db || !poolUtil) throw new Error('Database not initialized');
    
    const dbName = db.filename;
    const data = await poolUtil.exportFile(dbName);
    
    // Transfer buffer for zero-copy efficiency
    sendResponse(id, 'exportResult', data, [data.buffer]);
}
```

### Import Implementation

[sqlite-opfs.worker.ts:266-313](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/workers/sqlite-opfs.worker.ts#L266-313)

```typescript
async function handleImport(id: string, payload: SqliteImportRequest) {
    // 1. Close current database
    if (db) { db.close(); db = null; }
    
    // 2. CRITICAL: Delete existing file before import
    if (typeof poolUtil.unlink === 'function') {
        await poolUtil.unlink(dbName);
    }
    
    // 3. Import the new database
    await poolUtil.importDb(dbName, data);
    
    // 4. Re-open the database
    db = new poolUtil.OpfsSAHPoolDb(dbName);
}
```

---

## Legacy Removal

The codebase confirms legacy paths have been removed:

```typescript
// sqlite-opfs.service.ts:39-41
/**
 * OPFS is now the ONLY storage mechanism for browser mode.
 * The legacy sql.js + IndexedDB path has been removed.
 */
```

### Remaining IndexedDB References

| Location | Context | Status |
|----------|---------|--------|
| `sqlite-opfs.service.ts` | Comment documenting removal | ✅ Reference only |
| `system-topology.component.ts` | Mermaid diagram label | ✅ Diagram rendering |
| `execution.service.ts` | Comment "Persist run to IndexedDB" | ⚠️ **Stale comment** |

---

## UI Integration

[settings.component.ts:365-427](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/settings/components/settings.component.ts#L365-427)

### Export Flow

1. User clicks "Export Database" button
2. `sqlite.exportDatabase()` returns `Observable<Uint8Array>`
3. Creates Blob with MIME type `application/x-sqlite3`
4. Downloads as `praxis-backup-YYYY-MM-DD.db`

### Import Flow

1. User selects `.db` file via file input
2. Confirmation dialog warns about data replacement
3. `file.arrayBuffer()` → `Uint8Array`
4. `sqlite.importDatabase(data)` replaces OPFS file
5. Page reloads to reinitialize services

---

## Fallback Handling

| Scenario | Behavior |
|----------|----------|
| OPFS SAHPool unavailable | Falls back to `:memory:` database |
| Memory mode export | ⚠️ Will fail - `poolUtil` is null |
| Schema version mismatch | Auto-resets to fresh prebuilt database |

---

## Assessment: ✅ Sound

**Strengths:**
- Clean separation: Worker handles VFS, service exposes Observables
- Zero-copy buffer transfer for export
- Proper unlink-before-import pattern
- Confirmation dialogs before destructive operations
- Reload after import ensures clean state

**Minor Issues:**
- Stale "IndexedDB" comment in `execution.service.ts:168`
- Export will error if running in memory fallback mode (edge case)

---

## Environment Flags

All environments currently have OPFS disabled in config, but the code ignores this flag:

```typescript
// environment.ts, environment.prod.ts, etc.
sqliteOpfsEnabled: false  // NOT CHECKED - OPFS always used
```

> The `sqliteOpfsEnabled` flag appears vestigial - the code always attempts OPFS.
