# Add JupyterLite Bootstrap Retry Logic (P2)

> **Stream**: 4 - Reliability Improvements  
> **Effort**: M (2-3 hours)  
> **Priority**: P2

---

## Objective

Add retry mechanism for failed shim loads during JupyterLite bootstrap, improving reliability of Pyodide-based protocol execution.

---

## Context Files (Read First)

1. `.agent/staging/logic-audits/comprehensive_logic_audit.md` → Section "JupyterLite Loading"
2. `src/app/features/playground/services/playground-jupyterlite.service.ts:173-351`
3. `src/assets/python/web_serial_shim.py`
4. `src/assets/python/web_usb_shim.py`
5. `src/assets/python/web_ftdi_shim.py`

---

## Root Cause Analysis

**Problem**: Shim loading is single-attempt. Network hiccups or timing issues cause permanent bootstrap failure.

**Current behavior**:
```
fetch(shim) → fail → bootstrap fails → user sees error
```

**Desired behavior**:
```
fetch(shim) → fail → retry (3x with backoff) → bootstrap fails only after all retries exhausted
```

---

## Scope

### Change
- Add retry wrapper in `playground-jupyterlite.service.ts`
- Apply to all shim fetch operations
- Add logging for retry attempts

### Do NOT Change
- Shim file contents
- BroadcastChannel communication
- Python worker code

---

## Implementation Steps

1. **Create retry utility**
   ```typescript
   // src/app/core/utils/fetch-retry.ts
   export async function fetchWithRetry(
     url: string,
     options?: RequestInit,
     config?: { maxRetries?: number; backoffMs?: number }
   ): Promise<Response> {
     const maxRetries = config?.maxRetries ?? 3;
     const backoffMs = config?.backoffMs ?? 1000;
     
     let lastError: Error | null = null;
     
     for (let attempt = 0; attempt < maxRetries; attempt++) {
       try {
         const response = await fetch(url, options);
         if (!response.ok) throw new Error(`HTTP ${response.status}`);
         return response;
       } catch (error) {
         lastError = error as Error;
         console.warn(`Fetch attempt ${attempt + 1}/${maxRetries} failed for ${url}:`, error);
         
         if (attempt < maxRetries - 1) {
           await new Promise(r => setTimeout(r, backoffMs * (attempt + 1)));
         }
       }
     }
     
     throw lastError ?? new Error(`Failed to fetch ${url} after ${maxRetries} attempts`);
   }
   ```

2. **Integrate into shim loading**
   ```typescript
   // In playground-jupyterlite.service.ts
   private async loadShims(): Promise<void> {
     const shims = ['web_serial_shim.py', 'web_usb_shim.py', 'web_ftdi_shim.py'];
     
     for (const shim of shims) {
       const url = `${this.hostRoot}assets/python/${shim}`;
       const response = await fetchWithRetry(url, undefined, { maxRetries: 3, backoffMs: 500 });
       const code = await response.text();
       // ... existing exec logic ...
     }
   }
   ```

3. **Add error boundary**
   - If all retries fail, show actionable error: "Network issue loading Python environment. Please refresh and try again."

4. **Add unit tests**
   ```bash
   npm run test -- --include="**/fetch-retry.spec.ts"
   ```

---

## Verification

```bash
# Run jupyterlite specs (locally, not CI)
npx playwright test jupyterlite-bootstrap.spec.ts --grep-invert @slow --reporter=line 2>&1 | tail -10

# Or if @slow is applied, run explicitly:
npx playwright test jupyterlite-bootstrap.spec.ts --reporter=line 2>&1 | tail -10
```

---

## Success Criteria

- [ ] `fetchWithRetry()` utility created with tests
- [ ] Shim loading uses retry logic
- [ ] Console shows retry attempts on failure
- [ ] User sees actionable error after all retries exhausted
- [ ] No regression in bootstrap time for happy path
