# Playground Tab Improvements (P2)

> **Stream**: 2 - UX Polish
> **Effort**: S (1-2 hours)
> **Priority**: P2
> **Approach**: TDD - Write tests first, then implement

---

## Objective

Fix two critical UX issues in the Playground component:
1. **State Loss**: Switching tabs destroys the JupyterLite iframe, losing Pyodide state
2. **Tab Styling**: Tabs are visually obtrusive - need subtle, professional appearance

---

## Context Files (Read First)

1. `src/app/features/playground/playground.component.ts:130-226` → Tab template
2. `src/app/features/playground/playground.component.ts:294-305` → Tab CSS
3. `.agent/skills/ui-ux-pro-max/SKILL.md` → Tab styling best practices

---

## Root Cause Analysis

### State Loss Issue
**Problem**: Tabs use `<ng-template matTabContent>` which lazy-loads content. Angular Material destroys/recreates DOM when switching tabs, terminating the iframe and Pyodide worker.

**Current behavior**:
```
User on Notebook tab → Switch to Direct Control → Notebook iframe destroyed → Pyodide worker terminated
Switch back to Notebook → New iframe created → Pyodide bootstraps from scratch (30+ seconds)
```

**Desired behavior**:
```
User on Notebook tab → Switch to Direct Control → Notebook iframe hidden but preserved
Switch back to Notebook → Iframe still exists → Pyodide state intact (instant)
```

### Tab Styling Issue
Current tabs use Angular Material defaults - need subtle, professional appearance per ui-ux-pro-max guidelines.

---

## TDD Approach

### Step 1: Write E2E Tests First

Create `e2e/specs/playground-tab-persistence.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Playground Tab State Persistence', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/app/playground?mode=browser');
        await page.waitForSelector('mat-tab-group');
    });

    test('switching tabs preserves JupyterLite iframe', async ({ page }) => {
        // Wait for notebook tab to be active and iframe loaded
        const notebookIframe = page.locator('iframe.notebook-frame');
        await expect(notebookIframe).toBeVisible();
        
        // Get iframe's src to verify it's the same element later
        const originalSrc = await notebookIframe.getAttribute('src');
        
        // Switch to Direct Control tab
        await page.getByRole('tab', { name: 'Direct Control' }).click();
        
        // Wait for direct control content
        await expect(page.locator('.direct-control-dashboard')).toBeVisible();
        
        // Switch back to Notebook tab
        await page.getByRole('tab', { name: 'Notebook' }).click();
        
        // Verify iframe still has same src (not recreated)
        const newSrc = await notebookIframe.getAttribute('src');
        expect(newSrc).toBe(originalSrc);
    });

    test('tab label shows "Notebook" not "REPL Notebook"', async ({ page }) => {
        const tab = page.getByRole('tab', { name: 'Notebook' });
        await expect(tab).toBeVisible();
    });
});
```

### Step 2: Run Tests (Should Fail)

```bash
npx playwright test playground-tab-persistence.spec.ts --reporter=line 2>&1 | tail -10
```

---

## Implementation Steps

### 1. Fix State Preservation

Replace lazy-loading `matTabContent` with hidden pattern:

```typescript
// BEFORE (destroys content on tab switch):
<mat-tab label="REPL Notebook">
  <ng-template matTabContent>
    <div class="repl-notebook-wrapper">
      <!-- content -->
    </div>
  </ng-template>
</mat-tab>

// AFTER (preserves content):
<mat-tab label="Notebook">
  <div class="repl-notebook-wrapper" [hidden]="selectedTabIndex() !== 0">
    <!-- content -->
  </div>
</mat-tab>
```

**Note**: Remove `<ng-template matTabContent>` entirely - use `[hidden]` attribute instead.

### 2. Rename Tab

Change `label="REPL Notebook"` → `label="Notebook"` (line 131)

### 3. Style Tabs (Per ui-ux-pro-max)

Add subtle tab styling:

```scss
.repl-tabs {
  ::ng-deep .mat-mdc-tab-header {
    background: transparent;
    border-bottom: 1px solid var(--mat-sys-outline-variant);
  }

  ::ng-deep .mat-mdc-tab {
    min-width: 80px;
    opacity: 0.7;
    transition: opacity 0.2s ease;
    
    &:hover {
      opacity: 1;
    }
    
    &.mdc-tab--active {
      opacity: 1;
    }
  }

  ::ng-deep .mat-mdc-tab-labels {
    gap: 0;
  }
  
  ::ng-deep .mdc-tab-indicator__content--underline {
    border-color: var(--mat-sys-primary);
    border-width: 2px;
    border-radius: 2px 2px 0 0;
  }
}
```

---

## Verification

```bash
# Run tab persistence tests
npx playwright test playground-tab-persistence.spec.ts --reporter=line 2>&1 | tail -10

# Manual verification
# 1. Open /app/playground?mode=browser
# 2. Wait for Pyodide to initialize (~30s)
# 3. Run a Python command in notebook
# 4. Switch to Direct Control tab
# 5. Switch back to Notebook tab
# 6. Verify previous Python state is preserved (variables still defined)
```

---

## Success Criteria

- [ ] E2E tests written first and initially failing
- [ ] Tab label changed from "REPL Notebook" to "Notebook"
- [ ] Switching tabs does NOT destroy JupyterLite iframe
- [ ] Pyodide state persists across tab switches
- [ ] Tab styling is subtle and professional
- [ ] All new E2E tests pass
- [ ] No regression in existing playground specs
