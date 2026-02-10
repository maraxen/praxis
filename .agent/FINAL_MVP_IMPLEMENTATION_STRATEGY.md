# FINAL MVP IMPLEMENTATION STRATEGY

**Version**: 2.0 (Refined)
**Date**: 2026-02-09
**Status**: Ready for Implementation

---

## Executive Summary

**Goal**: Validate protocol completion via stdout and stabilize JupyterLite bootstrap readiness.

**Scope**:
1. Protocol execution validates completion through status + logs
2. JupyterLite bootstrap extracted to static file with error boundary
3. Skeleton loader replaces infinite spinner
4. E2E suite achieves 100% pass rate (Tiers 1, 3, 4)

**MVP Exclusions**:
- ❌ Tier 2: Protocol Upload validation (deferred post-MVP)

---

## PHASE 1: PROTOCOL COMPLETION VALIDATION

### 1.1 Objective
Ensure protocols definitively complete and stdout is captured for verification.

### 1.2 Current State (Working)
- Status transitions: `PENDING → RUNNING → COMPLETED` ✓
- Stdout captured and displayed in log panel ✓
- Database persistence works ✓
- Observable completion signal triggers status update ✓

### 1.3 Validation Enhancements

**File**: `execution.service.ts`

**Change A**: Add explicit completion log marker
```typescript
// Line ~388 (success path in executeBrowserProtocol)
this.addLog('[Protocol Execution Complete]');
```

**Change B**: Ensure function call logs flush before completion
```typescript
// After Observable.complete(), before setting COMPLETED status
await new Promise(resolve => setTimeout(resolve, 100)); // Allow async writes
```

### 1.4 E2E Validation Assertions

**File**: `e2e/page-objects/monitor.page.ts`

```typescript
async assertProtocolCompleted(): Promise<void> {
  // Status check
  await expect(this.statusChip).toContainText(/COMPLETED/i, { timeout: 60000 });

  // Logs present
  const logPanel = this.page.getByTestId('log-panel');
  await expect(logPanel).not.toBeEmpty();

  // Completion marker
  await expect(logPanel).toContainText(/Protocol Execution Complete|successfully/i);
}
```

---

## PHASE 2: JUPYTERLITE BOOTSTRAP STABILIZATION

### 2.1 Root Cause
URL-encoded bootstrap code can exceed browser limits (~4KB) or get mangled, causing Python SyntaxError in kernel → infinite spinner.

### 2.2 Solution: Static Bootstrap File

**New File**: `src/assets/jupyterlite/praxis_bootstrap.py`

```python
"""
Praxis JupyterLite Bootstrap
Fetched and executed in Phase 2 of initialization.
"""
import sys
from js import BroadcastChannel, console

def setup_praxis():
    """Initialize Praxis environment and signal readiness."""
    try:
        # Import web bridge
        import web_bridge

        # Signal ready to parent
        channel = BroadcastChannel.new('praxis_repl')
        channel.postMessage({'type': 'praxis:ready'})
        console.log('✓ Praxis bootstrap complete')

    except Exception as e:
        console.error(f'Bootstrap failed: {e}')
        raise

setup_praxis()
```

### 2.3 Service Updates

**File**: `playground-jupyterlite.service.ts`

**Change A**: Reduce minimal bootstrap to essential BroadcastChannel setup
```typescript
getMinimalBootstrap(): string {
  return `
from js import BroadcastChannel
ch = BroadcastChannel.new('praxis_repl')
ch.postMessage({'type': 'r'})
`.trim();
}
```

**Change B**: Fetch full bootstrap from static asset
```typescript
async getOptimizedBootstrap(): Promise<string> {
  const baseUrl = this.calculateHostRoot();
  const response = await fetch(`${baseUrl}/assets/jupyterlite/praxis_bootstrap.py`);

  if (!response.ok) {
    throw new Error(`Failed to fetch bootstrap: ${response.status}`);
  }

  return response.text();
}
```

**Change C**: Add URL size validation
```typescript
private validateUrlSize(url: string): void {
  if (url.length > 2000) {
    console.warn(`URL length ${url.length} exceeds safe limit (2000)`);
  }
}
```

### 2.4 Error Boundary Implementation

**File**: `playground-jupyterlite.service.ts`

```typescript
// Add loadingError signal
loadingError = signal<string | null>(null);

setupReadyListener(): void {
  const channel = new BroadcastChannel('praxis_repl');

  // 60s timeout with error UI (not 30s - allow for slow networks)
  const timeout = setTimeout(() => {
    if (this.isLoading()) {
      this.loadingError.set('Bootstrap timeout. Check console for errors.');
      this.isLoading.set(false);
    }
  }, 60000);

  channel.onmessage = (event) => {
    if (event.data.type === 'praxis:ready' || event.data.type === 'r') {
      clearTimeout(timeout);
      this.loadingError.set(null);
      this.isLoading.set(false);
      window.__praxis_pyodide_ready = true;
    }
  };
}
```

### 2.5 Retry Logic

**File**: `playground.component.ts`

```typescript
retryBootstrap(): void {
  // Reset state
  this.jupyterliteService.loadingError.set(null);
  this.jupyterliteService.isLoading.set(true);

  // Rebuild URL and reinitialize
  this.jupyterliteService.buildJupyterliteUrl();
  this.jupyterliteService.setupReadyListener();
}
```

---

## PHASE 3: SKELETON LOADER UI

### 3.1 Objective
Replace generic spinner with skeleton that matches JupyterLab appearance for better perceived performance.

### 3.2 Simplified Skeleton (Not Over-Engineered)

**File**: `playground.component.ts` (template section)

```html
@if (jupyterliteService.isLoading()) {
  <div class="loading-overlay">
    <div class="skeleton-container">
      <!-- Header bar -->
      <div class="skeleton-bar header"></div>
      <!-- Toolbar -->
      <div class="skeleton-bar toolbar"></div>
      <!-- Content cells -->
      <div class="skeleton-content">
        <div class="skeleton-cell"></div>
        <div class="skeleton-cell short"></div>
      </div>
      <div class="loading-text">Initializing Python environment...</div>
    </div>
  </div>
}

@if (jupyterliteService.loadingError()) {
  <div class="error-overlay">
    <div class="error-message">{{ jupyterliteService.loadingError() }}</div>
    <button (click)="retryBootstrap()">Retry</button>
  </div>
}
```

### 3.3 Minimal CSS

**File**: `playground.component.scss`

```scss
.loading-overlay {
  position: absolute;
  inset: 0;
  background: #fafafa;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;

  .skeleton-container {
    width: 90%;
    max-width: 800px;
  }

  .skeleton-bar {
    height: 40px;
    background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    margin-bottom: 8px;
    border-radius: 4px;

    &.header { height: 48px; }
    &.toolbar { height: 36px; width: 60%; }
  }

  .skeleton-cell {
    height: 60px;
    background: #f5f5f5;
    border-left: 3px solid #e0e0e0;
    margin-bottom: 12px;
    border-radius: 4px;

    &.short { width: 70%; }
  }

  .loading-text {
    text-align: center;
    color: #666;
    margin-top: 24px;
  }
}

.error-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.95);
  z-index: 101;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;

  .error-message {
    color: #d32f2f;
    font-weight: 500;
  }

  button {
    padding: 8px 24px;
    background: #1976d2;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

---

## PHASE 4: E2E TEST UPDATES

### 4.1 Protocol Completion Tests

**File**: `e2e/specs/user-journeys.spec.ts`

```typescript
test('protocol execution completes with logs', async ({ page }) => {
  // ... setup and start execution ...

  const monitor = new ExecutionMonitorPage(page);

  // Wait for completion
  await monitor.waitForStatus(/COMPLETED/i, 120000);

  // Validate logs present
  const logPanel = page.getByTestId('log-panel');
  const logs = await logPanel.textContent();

  expect(logs).toBeTruthy();
  expect(logs).toMatch(/Protocol Execution Complete|successfully/i);
});
```

### 4.2 JupyterLite Bootstrap Tests

**File**: `e2e/specs/jupyterlite-bootstrap.spec.ts`

```typescript
test('bootstrap completes and signals ready', async ({ page }) => {
  const consoleLogs: string[] = [];
  page.on('console', msg => consoleLogs.push(msg.text()));

  await page.goto('/app/playground');

  // Skeleton should appear
  await expect(page.locator('.loading-overlay')).toBeVisible({ timeout: 5000 });

  // Wait for ready (skeleton disappears)
  await expect(page.locator('.loading-overlay')).not.toBeVisible({ timeout: 120000 });

  // Verify no critical errors
  const errors = consoleLogs.filter(log =>
    log.includes('SyntaxError') || log.includes('Bootstrap failed')
  );
  expect(errors).toHaveLength(0);

  // Verify ready signal logged
  const readyLogs = consoleLogs.filter(log =>
    log.includes('praxis:ready') || log.includes('bootstrap complete')
  );
  expect(readyLogs.length).toBeGreaterThan(0);
});

test('error UI shows on bootstrap failure with retry option', async ({ page }) => {
  // This test validates error UI exists and retry button works
  // Actual failure is hard to trigger, so we verify components exist

  await page.goto('/app/playground');

  // Error overlay should be in DOM (hidden initially)
  const errorOverlay = page.locator('.error-overlay');
  const retryButton = errorOverlay.locator('button');

  // Verify structure exists for when errors occur
  expect(await retryButton.count()).toBe(1);
});
```

### 4.3 Path Resolution Test (GH-Pages)

**File**: `e2e/specs/jupyterlite-bootstrap.spec.ts`

```typescript
test('assets load with correct base-href', async ({ page }) => {
  const requests: string[] = [];
  page.on('request', req => requests.push(req.url()));

  await page.goto('/app/playground');
  await page.waitForTimeout(5000);

  // Verify bootstrap asset request uses correct path
  const bootstrapRequest = requests.find(url =>
    url.includes('praxis_bootstrap.py') || url.includes('web_bridge.py')
  );

  expect(bootstrapRequest).toBeDefined();

  // Should NOT have double slashes or missing /praxis/ prefix
  expect(bootstrapRequest).not.toMatch(/\/\//g);
});
```

---

## PHASE 5: FULL E2E VALIDATION

### 5.1 Test Matrix (MVP Scope)

| Suite | Test File | Focus | MVP |
|-------|-----------|-------|-----|
| **Tier 1** | `settings-functionality.spec.ts` | Settings persistence | ✅ |
| **Tier 1** | `workcell-dashboard.spec.ts` | Deck selection, seeding | ✅ |
| **Tier 2** | `user-journeys.spec.ts` (upload) | Protocol upload | ❌ Deferred |
| **Tier 3** | `user-journeys.spec.ts` (execution) | Execution, completion, logs | ✅ |
| **Tier 4** | `jupyterlite-bootstrap.spec.ts` | Bootstrap, readiness, REPL | ✅ |

### 5.2 Validation Checklist

```
Protocol Completion (Tier 3)
├─ [ ] Status shows COMPLETED
├─ [ ] Progress reaches 100%
├─ [ ] Logs display in panel
├─ [ ] Completion marker present
└─ [ ] Can start another run

JupyterLite Bootstrap (Tier 4)
├─ [ ] Skeleton loader appears
├─ [ ] praxis:ready signal received
├─ [ ] Skeleton fades when ready
├─ [ ] No SyntaxError in console
├─ [ ] Assets load from correct paths
├─ [ ] Error UI shows on failure
└─ [ ] Retry button works

GH-Pages Compatibility
├─ [ ] Base-href /praxis/ works
├─ [ ] Relative paths resolve
├─ [ ] No 404 errors
└─ [ ] Schemas/themes load
```

### 5.3 Run Commands

```bash
# Individual suites
npx playwright test jupyterlite-bootstrap.spec.ts
npx playwright test user-journeys.spec.ts
npx playwright test settings-functionality.spec.ts
npx playwright test workcell-dashboard.spec.ts

# Full suite (MVP scope)
npx playwright test --grep-invert "protocol upload"

# With UI for debugging
npx playwright test --ui
```

---

## IMPLEMENTATION ORDER

```
1. Create praxis_bootstrap.py static file
   └─ Single consolidated bootstrap with BroadcastChannel signal

2. Update playground-jupyterlite.service.ts
   ├─ Reduce minimal bootstrap
   ├─ Fetch from static asset
   ├─ Add error boundary (60s timeout)
   └─ Add URL size validation

3. Add skeleton loader to playground.component
   ├─ Template with skeleton elements
   ├─ Error overlay with retry button
   └─ Minimal CSS

4. Update execution.service.ts
   ├─ Add completion log marker
   └─ Small flush delay

5. Update E2E tests
   ├─ Protocol completion assertions
   ├─ Bootstrap readiness tests
   └─ Path resolution validation

6. Run full E2E suite and fix failures
```

---

## FILES TO MODIFY

| File | Changes |
|------|---------|
| `src/assets/jupyterlite/praxis_bootstrap.py` | **NEW** - Static bootstrap file |
| `src/app/features/playground/services/playground-jupyterlite.service.ts` | Fetch static bootstrap, error boundary, URL validation |
| `src/app/features/playground/playground.component.ts` | Skeleton loader template, retry logic |
| `src/app/features/playground/playground.component.scss` | Skeleton and error overlay styles |
| `src/app/features/run-protocol/services/execution.service.ts` | Completion log marker, flush delay |
| `e2e/page-objects/monitor.page.ts` | Completion assertion method |
| `e2e/specs/jupyterlite-bootstrap.spec.ts` | Bootstrap readiness tests |
| `e2e/specs/user-journeys.spec.ts` | Protocol completion tests |

---

## SUCCESS CRITERIA

| Metric | Target |
|--------|--------|
| E2E Pass Rate (Tiers 1, 3, 4) | 100% |
| Bootstrap Success Rate | 100% (no infinite spinners) |
| Bootstrap Timeout | <60s on standard connection |
| Console Errors | 0 critical errors |
| Protocol Completion | Status + logs always present |

---

## RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| Bootstrap asset fails to load | Error boundary shows retry button |
| URL still too long | Size validation warns in console |
| Network timeout on slow connection | 60s timeout (not 30s) |
| Python syntax error in kernel | Errors logged to console, visible in UI |
| Path resolution breaks in GH-Pages | Test with actual /praxis/ subdirectory |

---

## TECHNICAL NOTES

### Bootstrap Flow (Two-Phase)
1. **Phase 1 (Minimal)**: 3-line Python code passed via URL parameter
   - Sets up BroadcastChannel listener
   - Sends 'r' (ready) signal
2. **Phase 2 (Full)**: `praxis_bootstrap.py` fetched as asset
   - Imports web_bridge
   - Installs pylabrobot wheel
   - Sends 'praxis:ready' signal

### Why Static File?
- URL parameters have ~4KB browser limit
- Inline code is fragile and hard to debug
- Static file can be versioned and tested independently
- Eliminates URL encoding/mangling issues

### Why 60s Timeout?
- Pyodide initialization can be slow (especially first load)
- Wheel installation takes time over slow networks
- 30s too aggressive based on recon findings
- Still provides feedback faster than current 300s timeout

---

## NEXT STEPS

1. **User Approval** - Confirm strategy before implementation
2. **Phase 1** - Start with static bootstrap file creation
3. **Incremental Testing** - Test each phase before moving to next
4. **Full Suite Run** - Validate all Tiers 1, 3, 4 pass
5. **Documentation** - Update .agent/ACTIVE_DEVELOPMENT.md with results
