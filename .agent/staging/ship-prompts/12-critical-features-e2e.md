# Add Critical Feature E2E Tests (P1)

> **Stream**: 7 - Test Coverage  
> **Effort**: M (2-3 hours)  
> **Priority**: P1

---

## Objective

Add explicit E2E tests for 4 critical features currently lacking coverage: command palette, real-time monitor updates, theme cycling, and tutorial flow.

---

## Context Files (Read First)

1. `.agent/staging/critical_features.md` → Features marked ⚠️
2. `e2e/specs/smoke.spec.ts` → May have partial coverage
3. `e2e/specs/settings-functionality.spec.ts` → Theme tests
4. `e2e/specs/01-onboarding.spec.ts` → Onboarding tests

---

## Features Needing Tests

| Feature | Current Coverage | Priority |
|---------|-----------------|----------|
| Command palette | None | High |
| Real-time monitor updates | Unverified | Medium |
| Theme cycling | Partial in settings | Medium |
| Tutorial flow | Partial in onboarding | Medium |

---

## Scope

### Change
- Add tests to existing spec files OR create new spec

### Do NOT Change
- Source application code
- Existing test logic

---

## Implementation Steps

### 1. Command Palette Test

```typescript
// Add to smoke.spec.ts or create command-palette.spec.ts
test.describe('Command Palette', () => {
  test('opens with keyboard shortcut', async ({ page }) => {
    await page.goto('/app');
    await page.keyboard.press('Meta+k'); // or 'Control+k' on Windows
    await expect(page.locator('[data-testid="command-palette"]')).toBeVisible();
  });

  test('searches and executes command', async ({ page }) => {
    await page.goto('/app');
    await page.keyboard.press('Meta+k');
    await page.locator('[data-testid="command-palette-input"]').fill('settings');
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/.*settings.*/);
  });
});
```

### 2. Real-Time Monitor Updates Test

```typescript
// Add to monitor-detail.spec.ts
test('shows real-time log updates', async ({ page }) => {
  // Navigate to active run (or mock one)
  await page.goto('/app/monitor');
  
  // Wait for initial content
  const logContainer = page.locator('[data-testid="run-logs"]');
  await expect(logContainer).toBeVisible();
  
  // Verify logs are appearing (if run is active)
  // This may need a running protocol fixture
});
```

### 3. Theme Cycling Test

```typescript
// Add to settings-functionality.spec.ts
test('cycles through all themes', async ({ page }) => {
  await page.goto('/app/settings');
  
  const themes = ['light', 'dark', 'system'];
  for (const theme of themes) {
    await page.locator(`[data-testid="theme-${theme}"]`).click();
    // Verify theme applied (check class on html or body)
    if (theme !== 'system') {
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
    }
  }
});
```

### 4. Tutorial Flow Test

```typescript
// Add to 01-onboarding.spec.ts
test('completes tutorial flow', async ({ page }) => {
  await page.goto('/app?showTutorial=true');
  
  // Step through tutorial
  await expect(page.locator('[data-testid="tutorial-step-1"]')).toBeVisible();
  await page.locator('[data-testid="tutorial-next"]').click();
  
  await expect(page.locator('[data-testid="tutorial-step-2"]')).toBeVisible();
  await page.locator('[data-testid="tutorial-next"]').click();
  
  // Complete
  await page.locator('[data-testid="tutorial-finish"]').click();
  await expect(page.locator('[data-testid="tutorial-step-1"]')).not.toBeVisible();
});
```

---

## Verification

```bash
# Run specific test file
npx playwright test smoke.spec.ts --grep "Command Palette" --reporter=line 2>&1 | tail -10
npx playwright test settings-functionality.spec.ts --grep "theme" --reporter=line 2>&1 | tail -10
npx playwright test 01-onboarding.spec.ts --grep "tutorial" --reporter=line 2>&1 | tail -10
```

---

## Success Criteria

- [ ] Command palette test passes
- [ ] Theme cycling test passes
- [ ] Tutorial flow test passes (or skip if feature not implemented)
- [ ] Real-time updates test passes (or documented as needing fixture)

---

## Notes

Before implementing, verify:
1. What are the actual data-testid attributes on these elements?
2. Is the command palette keyboard shortcut Cmd+K or Ctrl+K?
3. Does the tutorial feature exist and have a trigger mechanism?

Use `npx playwright test --debug` to inspect the actual DOM before writing selectors.
