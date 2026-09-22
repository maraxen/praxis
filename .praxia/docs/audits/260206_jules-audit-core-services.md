---
title: 'Jules Audit: Core Services'
description: 'Jules deep audit of the web-client core services (Feb 3, 2026; quality score 6/10)'
status: archived
task_id: 260922_debt-1293-docs-migration
---
# Jules Audit: Core Services
**Session ID**: 1009855817323566566
**Date**: Feb 3, 2026
**Quality Score**: 6/10

## Key Findings

### Service Integration Map
| Source | Target | Mechanism | Purpose |
|--------|--------|-----------|---------| 
| ExecutionService | PythonRuntime | executeBlob | Running protocol binaries |
| PythonRuntime | HardwareDiscovery | RAW_IO events | Direct hardware control |
| PythonRuntime | InteractionService | USER_INTERACTION | Dialog display from Python |
| ExecutionService | AsyncRepositories | CRUD Observables | Persisting run status |
| HardwareDiscovery | Backend API | HardwareService | Machine registration |

### Async Patterns
- Worker IPC via Promise-based `sendMessage` helper
- Deferred initialization for Pyodide (started on first request)
- Status signaling: `'idle' | 'loading' | 'ready' | 'error'`

### Snapshot System
- Integrates with `PyodideSnapshotService` for memory snapshots
- Significantly accelerates subsequent restarts
