# Logic Audit Suite

> **Last Updated**: 2026-01-31  
> **Scope**: Browser-mode execution, asset management, hardware discovery

## Audit Files

| File | Topics |
|------|--------|
| [01-data-models.md](./01-data-models.md) | MachineDefinition vs MachineFrontendDefinition, 3-tier architecture |
| [02-asset-wizard.md](./02-asset-wizard.md) | Resource definition chain, filtering, search |
| [03-protocol-execution.md](./03-protocol-execution.md) | Parameter resolution, deck setup, run state machine |
| [04-constraints.md](./04-constraints.md) | Deck drop validation, asset constraint matching |
| [05-github-pages.md](./05-github-pages.md) | baseHref calculation, path normalization |
| [06-jupyterlite.md](./06-jupyterlite.md) | Bootstrap flow, shim loading, BroadcastChannel |
| [07-hardware-discovery.md](./07-hardware-discovery.md) | VID/PID lookup, device lifecycle, WebSerial/WebUSB |
| [08-serialization.md](./08-serialization.md) | Deck state, WellSelector, IndexSelector, backend args |
| [09-recommendations.md](./09-recommendations.md) | Prioritized action items |
| [10-import-export.md](./10-import-export.md) | Database export/import, OPFS VFS, legacy removal |
| [11-error-handling.md](./11-error-handling.md) | Worker errors, status signals, global handlers |
| [12-session-recovery.md](./12-session-recovery.md) | Pause/resume, crash recovery, interrupt buffer |
| [13-memory-management.md](./13-memory-management.md) | Pyodide heap cleanup, worker restart mechanism |
| [14-port-persistence.md](./14-port-persistence.md) | WebSerial authorization, connection lifecycle |
| [15-storage-quotas.md](./15-storage-quotas.md) | LocalStorage, OPFS quotas, StorageManager API |



## Quick Reference

### Status Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Sound / No issues |
| ⚠️ | Concerns identified |
| ❌ | Critical gap |

### Key Findings Summary

| Area | Status | Issue |
|------|--------|-------|
| VID/PID Coverage | ⚠️ | 9 entries vs 33 backends (~73% gap) |
| baseHref Patterns | ⚠️ | 3 inconsistent implementations |
| Deck Serialization | ⚠️ | Heuristic class inference |
| JupyterLite Bootstrap | ✅ | 2-phase BroadcastChannel |
| Run State Machine | ✅ | 13 comprehensive states |
| WellSelector/IndexSelector | ✅ | Well-generalized |
| Import/Export | ✅ | Modern OPFS VFS, legacy removed |
| Error Handling | ✅ | Status signals, worker.onerror |
| Session Recovery | ⚠️ | Browser resume not supported |
| Memory Management | ⚠️ | No Pyodide cleanup between runs |
| Port Persistence | ✅ | getPorts() authorization works |
| Storage Quotas | ⚠️ | OPFS quota not monitored |


## Not Yet Audited

See [09-recommendations.md](./09-recommendations.md) for suggested additional areas.
