# Fix API Proxy ECONNREFUSED Errors (P0)

> **Stream**: 8 - Dev Infrastructure  
> **Effort**: S (1 hour)  
> **Priority**: P0 (Blocks dev experience)

---

## Objective

Investigate and resolve the repeating `ECONNREFUSED` errors when the dev server tries to proxy `/api/v1/protocols/definitions` requests.

---

## Symptoms

```
[vite] http proxy error: /api/v1/protocols/definitions?limit=100
AggregateError [ECONNREFUSED]: 
    at internalConnectMultiple (node:net:1139:18)
    at afterConnectMultiple (node:net:1714:7)
```

Errors repeat every ~15 seconds, suggesting a polling/retry mechanism.

---

## Context Files (Read First)

1. `vite.config.ts` OR `proxy.conf.json` → Proxy configuration
2. `src/app/core/services/` → Service making the API call
3. `angular.json` → Dev server config

---

## Root Cause Hypotheses

| # | Hypothesis | How to Verify |
|---|------------|---------------|
| 1 | Backend server not running | Check if Python/Node backend is running on proxy target port |
| 2 | Wrong proxy target URL | Check `vite.config.ts` proxy target matches backend port |
| 3 | Browser mode doesn't need proxy | Code should check mode before making API calls |
| 4 | Missing mode guard | Protocol service calls API even in browser-only mode |

---

## Scope

### Investigate
- Proxy configuration
- What triggers the `/api/v1/protocols/definitions` call
- Whether this call is needed in browser-only mode

### Fix (depending on cause)
- Add mode check to skip API calls in browser mode
- OR fix proxy configuration
- OR add graceful error handling for offline backend

---

## Implementation Steps

1. **Check proxy config**
   ```bash
   cat vite.config.ts | grep -A 20 "proxy"
   # OR
   cat proxy.conf.json
   ```

2. **Find the caller**
   ```bash
   grep -r "protocols/definitions" src/app --include="*.ts" | head -10
   ```

3. **Check if mode guard exists**
   ```typescript
   // Expected pattern:
   if (this.modeService.isBackendMode()) {
     return this.http.get('/api/v1/protocols/definitions');
   } else {
     return this.localProtocolService.getDefinitions();
   }
   ```

4. **If mode guard missing, add it**
   - Inject mode service
   - Return empty/local data in browser mode
   - Log info message instead of making HTTP call

5. **If proxy config wrong, fix it**
   - Update target URL to correct backend port
   - Add error handling for unavailable backend

---

## Verification

```bash
# Start dev server without backend
npm run start

# Check console - should NOT see ECONNREFUSED errors
# OR should see graceful "Backend not available, using local data" message
```

---

## Success Criteria

- [ ] Root cause identified
- [ ] No more ECONNREFUSED spam in console
- [ ] App still works in browser-only mode
- [ ] If backend running, API calls work correctly

---

## Quick Fix (If Needed)

If investigation takes too long, add error suppression:

```typescript
// In the calling service
this.http.get('/api/v1/protocols/definitions').pipe(
  catchError(err => {
    if (err.status === 0) {
      console.info('Backend unavailable, using local protocol definitions');
      return of({ definitions: [] });
    }
    throw err;
  })
);
```
