# Recommendations & Future Audits

## Prioritized Action Items

### High Priority

1. **VID/PID Table Expansion**
   - Add missing device mappings for Tecan, Inheco, Agilent
   - Implement auto-discovery fallback via backend API

2. **baseHref Unification**
   - Create `PathUtils.normalizeBaseHref()` to consolidate 3 patterns

### Medium Priority

3. **Deck Serialization Validation**
   - Add runtime check that generated FQNs match actual PLR classes

4. **Bootstrap Retry Logic**
   - Add retry mechanism for failed shim loads in JupyterLite

### Low Priority

5. **KNOWN_DEVICES Auto-Sync**
   - Generate VID/PID table from PLR package metadata

---

## Suggested Additional Audits

### Not Yet Covered

| Area | Why Audit? |
|------|-----------|
| **Error Boundary Handling** | How do unhandled exceptions in web workers propagate back to UI? |
| **SQLite Transaction Safety** | Are concurrent writes from multiple tabs handled correctly? |
| **Protocol Blob Validation** | Is there schema/signature validation before execution? |
| **Asset Deduplication** | How are duplicate resources in inventory handled? |
| **Offline Support** | What happens when network is lost mid-operation? |
| **Pyodide Memory Management** | How is heap memory cleaned up between protocol runs? |
| **Theme/Dark Mode Propagation** | Does JupyterLite iframe receive theme updates correctly? |
| **Session Recovery** | Can interrupted protocol runs be resumed after browser crash? |

### Browser-Specific Concerns

| Area | Why Audit? |
|------|-----------|
| **WebSerial Port Persistence** | Do port handles survive page refresh? |
| **IndexedDB Size Limits** | What happens when storage quota is exceeded? |
| **SharedArrayBuffer Requirements** | Cross-origin isolation headers for multi-threaded Pyodide |
| **Service Worker Caching** | How are Python wheels and WASM cached/invalidated? |

### Data Integrity

| Area | Why Audit? |
|------|-----------|
| **Run Log Persistence** | Are logs persisted before status updates? |
| **Asset Version Conflicts** | How are definition updates handled for existing instances? |
| **Protocol Migration** | How do old protocols behave with new parameter schemas? |

---

## Quick Wins (< 1 day)

1. Extract `normalizeBaseHref()` utility
2. Add error logging to BroadcastChannel failure paths
3. Document VID/PID table update process in CONTRIBUTING.md
