# Pyodide Memory Management Audit

## Status: ⚠️ No Explicit Cleanup Between Runs

---

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Python Worker Lifecycle                      │
├─────────────────────────────────────────────────────────────────┤
│  1. Worker created (lazy init on first use)                     │
│  2. Pyodide loaded → shared instance for all runs               │
│  3. Protocol executes in namespace: setup_ns = {}; exec(...)    │
│  4. Run completes → namespace NOT cleared                       │
│  5. Next run → same Pyodide instance, accumulated state         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Execution Pattern

[python.worker.ts:214-250](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/workers/python.worker.ts#L214-250)

```python
# Protocol execution creates local namespace
setup_ns = {}
exec(js.deck_setup_script, setup_ns)

# Protocol function executed with kwargs
protocol_func(**kwargs)
```

**Issue**: `setup_ns` goes out of scope but Python objects may persist in Pyodide's heap.

---

## Memory Accumulation Risks

| Risk | Impact |
|------|--------|
| Large numpy arrays from previous runs | Heap fragmentation |
| Imported modules cached | Expected behavior, low risk |
| Global variables from protocols | May interfere with subsequent runs |
| Resource objects not garbage collected | Memory leak over time |

---

## Worker Restart Mechanism

[python-runtime.service.ts:47-56](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/services/python-runtime.service.ts#L47-56)

```typescript
restartWorker() {
    if (this.worker) {
        this.worker.terminate();
        this.worker = null;
    }
    this.isReady.set(false);
    this.status.set('idle');
    this.lastError.set(null);
    this.initWorker();
}
```

**Assessment**: ✅ Full cleanup available via worker restart

---

## Recommendations

1. **Add `gc.collect()` Call**: Run Python GC after each protocol execution
2. **Clear Globals Between Runs**: Reset `pyodide.globals` to clean state
3. **Monitor Heap Size**: Log `pyodide.heap_size()` after runs for leak detection
4. **Auto-Restart Threshold**: Restart worker if heap exceeds threshold (e.g., 512MB)
