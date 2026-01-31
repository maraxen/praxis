# Session & Run Recovery Audit

## Status: ⚠️ Browser Mode Has Limitations

---

## Pause/Resume Support

### Production Mode

[execution.service.ts:619-631](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/features/run-protocol/services/execution.service.ts#L619-631)

```typescript
pause(runId: string): Observable<void> {
    if (this.modeService.isBrowserMode()) {
        return of(undefined).pipe(tap(() => 
            console.warn('Pause is not supported in browser mode.')
        ));
    }
    return this.http.post<void>(`${this.API_URL}/api/v1/execution/runs/${runId}/pause`, {});
}

resume(runId: string): Observable<void> {
    if (this.modeService.isBrowserMode()) {
        return of(undefined).pipe(tap(() => 
            console.warn('Resume is not supported in browser mode.')
        ));
    }
    return this.http.post<void>(`${this.API_URL}/api/v1/execution/runs/${runId}/resume`, {});
}
```

**Assessment**: ⚠️ Browser mode pause/resume explicitly unsupported

---

## Crash Recovery

| Scenario | Current Behavior |
|----------|------------------|
| Browser tab closed mid-run | Run state lost, no recovery |
| Page refresh mid-run | Run state lost, worker terminated |
| Browser crash | No session persistence |

---

## Interrupt Buffer

[python.worker.ts:61](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/workers/python.worker.ts#L61)

```typescript
const interruptBuffer = new Uint8Array(new SharedArrayBuffer(1));
```

- Used for graceful Pyodide interrupt via `pyodide.setInterruptBuffer()`
- Allows cooperative cancellation of long-running Python code

---

## Run State Persistence

- `_currentRun` signal stores active run metadata
- Run logs saved to SQLite after each step
- **No checkpoint/resume mechanism** for browser execution

---

## Recommendations

1. **Add Checkpoint Support**: Persist execution state at function call boundaries
2. **Implement "Resume" for Browser**: Store protocol position + deck state for recovery
3. **Add Session Persistence**: Save `_currentRun` to localStorage on visibility change
