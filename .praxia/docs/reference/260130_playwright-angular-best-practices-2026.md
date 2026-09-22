# Playwright + Angular Best Practices (2026)

> A consolidated guide for E2E testing Angular applications with Playwright.

---

## 1. Locator Strategy

### Priority Order (Most to Least Resilient)

1. **`data-testid`** – Explicit testing contract, immune to styling/text changes
2. **Accessible roles** – `getByRole('button', { name: 'Submit' })`
3. **Text content** – `getByText('Welcome')` for user-visible labels
4. **CSS selectors** – Last resort; avoid deep nesting

```typescript
// ✅ Preferred
page.getByTestId('submit-btn');
page.getByRole('button', { name: 'Save' });

// ❌ Avoid
page.locator('div.wrapper > button.primary-btn');
```

### Angular-Specific Tips

- Use `data-testid` on Angular components: `<app-hero-card [attr.data-testid]="'hero-' + hero.id">`
- For Material components, prefer `mat-*` attribute selectors or accessible roles

---

## 2. Web-First Assertions

Playwright's assertions **auto-retry** until the condition is met. Prefer them over manual waits.

```typescript
// ✅ Auto-retrying assertions
await expect(page.getByTestId('status')).toHaveText('Submitted');
await expect(page.getByRole('dialog')).toBeVisible();
await expect(page.getByTestId('save-btn')).toBeEnabled();

// ❌ Avoid manual waits
await page.waitForTimeout(1000);
```

### Key Assertions

| Assertion | Use Case |
|:----------|:---------|
| `toBeVisible()` | Element in viewport and not hidden |
| `toBeEnabled()` | Button/input is clickable |
| `toHaveText()` | Exact text match |
| `toContainText()` | Partial text match |
| `toHaveAttribute(name, value)` | Check data attributes |
| `toHaveClass()` | CSS class verification |

---

## 3. Waiting Strategies for Angular

Angular's Zone.js and change detection require deliberate waiting patterns.

### Route Navigation

```typescript
await page.goto('/dashboard');
await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
```

### Async Data Loading

```typescript
// Wait for loading indicator to disappear
await expect(page.getByTestId('loading-spinner')).toBeHidden();
// Then assert on loaded content
await expect(page.getByTestId('hero-list')).toContainText('Hero 1');
```

### Material Animations

Angular Material components often animate. Use `{ force: true }` sparingly or prefer waiting for stable state:

```typescript
// Wait for stepper animation to complete
await expect(page.locator('.mat-step-header[aria-selected="true"]')).toBeVisible();

// Only force click if animations cause flakiness after proper waiting
await page.getByTestId('next-step').click({ force: true });
```

---

## 4. Page Object Pattern

Encapsulate selectors and interactions in Page Object classes for maintainability.

```typescript
// pages/hero-detail.page.ts
export class HeroDetailPage {
  constructor(private page: Page) {}

  get nameInput() {
    return this.page.getByTestId('hero-name-input');
  }

  get saveButton() {
    return this.page.getByRole('button', { name: 'Save' });
  }

  get cancelButton() {
    return this.page.getByRole('button', { name: 'Cancel' });
  }

  async setName(name: string) {
    await this.nameInput.fill(name);
  }

  async save() {
    await this.saveButton.click();
  }
}
```

### Test File

```typescript
test('should save hero name', async ({ page }) => {
  const heroPage = new HeroDetailPage(page);
  
  await page.goto('/heroes/1');
  await heroPage.setName('Updated Hero');
  await heroPage.save();
  
  await expect(page.getByTestId('success-toast')).toBeVisible();
});
```

---

## 5. Test Isolation & Fixtures

### Use Playwright's Test Fixtures

```typescript
// fixtures/auth.fixture.ts
import { test as base } from '@playwright/test';

export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    await page.goto('/login');
    await page.getByTestId('username').fill('testuser');
    await page.getByTestId('password').fill('password');
    await page.getByRole('button', { name: 'Login' }).click();
    await expect(page.getByTestId('dashboard')).toBeVisible();
    await use(page);
  },
});
```

### Database/State Isolation

- Reset database state before each test via API calls or fixtures
- Use `beforeEach` to ensure clean state
- For OPFS/IndexedDB, clear storage in `beforeEach`:

```typescript
test.beforeEach(async ({ page }) => {
  await page.evaluate(() => indexedDB.deleteDatabase('appDb'));
});
```

---

## 6. Handling Async Initialization (OPFS, SQLite Wasm)

Angular apps using OPFS or SQLite Wasm require waiting for initialization.

```typescript
// Wait for database ready indicator
await expect(page.getByTestId('db-ready-indicator')).toBeVisible({ timeout: 30000 });

// Or wait for specific component that requires DB
await expect(page.getByTestId('hero-list')).not.toBeEmpty();
```

### Recommended Pattern

Add a visible `data-testid="app-ready"` element that only renders after all async initialization completes.

---

## 7. Debugging & Tracing

### Enable Trace on First Retry

```typescript
// playwright.config.ts
export default defineConfig({
  retries: 2,
  use: {
    trace: 'on-first-retry',
    video: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
});
```

### Interactive Debugging

```bash
npx playwright test --debug
npx playwright test --ui
```

### View Trace

```bash
npx playwright show-trace trace.zip
```

---

## 8. CI/CD Best Practices

### Parallelization

```typescript
// playwright.config.ts
export default defineConfig({
  workers: process.env.CI ? 4 : undefined,
  fullyParallel: true,
});
```

### Sharding for Large Suites

```bash
npx playwright test --shard=1/4
npx playwright test --shard=2/4
# ... run on separate CI machines
```

### Timeout Configuration

```typescript
export default defineConfig({
  timeout: 60000,        // Per-test timeout
  expect: {
    timeout: 10000,      // Assertion timeout
  },
});
```

---

## 9. Angular-Specific Patterns

### Testing Standalone Components

Angular 19+ standalone components work naturally with Playwright—no special setup needed for E2E testing.

### Handling Signals & Reactive State

When testing components using Angular Signals:

```typescript
// Trigger state change and wait for DOM update
await page.getByTestId('increment-btn').click();
await expect(page.getByTestId('counter-value')).toHaveText('1');
```

### Zone.js Stability

Playwright's auto-waiting handles most Zone.js timing, but for complex async:

```typescript
// Wait for Angular stability explicitly if needed
await page.waitForFunction(() => {
  return (window as any).getAllAngularTestabilities?.()
    ?.every((t: any) => t.isStable());
});
```

---

## 10. Common Pitfalls

| Pitfall | Solution |
|:--------|:---------|
| Flaky clicks on animated elements | Use `force: true` or wait for animation completion |
| Stale element references | Use Playwright locators (auto-retry, no stale refs) |
| Tests pass locally, fail in CI | Enable traces, increase timeouts, check viewport size |
| Material overlay z-index issues | Click on overlays directly, not through parent |
| OPFS not ready | Add explicit readiness indicator and wait for it |

---

## Quick Reference

```typescript
// Navigation
await page.goto('/heroes');

// Interaction
await page.getByTestId('search').fill('Batman');
await page.getByRole('button', { name: 'Search' }).click();

// Assertions
await expect(page.getByTestId('results')).toContainText('Batman');
await expect(page.getByRole('row')).toHaveCount(5);

// Waiting
await expect(page.getByTestId('loading')).toBeHidden();
await expect(page.getByTestId('content')).toBeVisible();
```

---

*Generated: 2026-01-30*
