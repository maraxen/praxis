# Error Boundary Handling Audit

## Status: ✅ Good Coverage with Minor Gaps

---

## Worker Error Handling

### PythonRuntimeService

[python-runtime.service.ts:71-96](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/services/python-runtime.service.ts#L71-96)

```typescript
// Status signals for UI recovery
status = signal<'idle' | 'loading' | 'ready' | 'error'>('idle');
lastError = signal<string | null>(null);

// Worker error handler
this.worker.onerror = (evt) => {
    console.error('[PythonRuntime] Worker error:', evt);
    this.status.set('error');
    this.lastError.set(evt.message);
};

// Init promise rejection
this.sendMessage('INIT').then(() => {
    this.isReady.set(true);
    this.status.set('ready');
}).catch(err => {
    this.status.set('error');
    this.lastError.set(String(err));
});
```

**Assessment**: ✅ Signals propagate error state to UI

### SqliteOpfsService

[sqlite-opfs.service.ts:62-67](file:///Users/mar/Projects/praxis/praxis/web-client/src/app/core/services/sqlite/sqlite-opfs.service.ts#L62-67)

```typescript
this.worker.onerror = (err) => {
    console.warn('[SqliteOpfsService] Worker error (non-fatal):', err);
};
```

**Assessment**: ⚠️ Logged but not surfaced to UI

### DirectControlKernelService

```typescript
script.onerror = () => reject(new Error('Failed to load Pyodide script'));
```

**Assessment**: ✅ Promise rejection on script load failure

---

## Missing Patterns

| Pattern | Status |
|---------|--------|
| Angular `ErrorHandler` provider | ❌ Not implemented |
| `unhandledrejection` listener | ❌ Not implemented |
| Global error boundary component | ❌ Not implemented |

---

## Recommendations

1. **Add Global Error Handler**: Implement Angular `ErrorHandler` to catch uncaught exceptions
2. **Surface SqliteOpfs Errors**: Propagate worker errors to a service-level signal
3. **Add Error Recovery UI**: Show toast/dialog when critical services fail
