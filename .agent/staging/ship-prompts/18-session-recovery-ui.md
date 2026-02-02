# Session Recovery UI Dialog (P1)

> **Stream**: 6 - Reliability & UX  
> **Effort**: S (1-2 hours)  
> **Priority**: P1  
> **Approach**: TDD - Write E2E tests first, then implement  
> **Isolation**: Use git worktree before starting

---

## Objective

Implement the missing UI dialog for session recovery. The `SessionRecoveryService` already detects orphaned runs, but there is no user-facing prompt to take action.

---

## Context Files (Read First)

1. `src/app/core/services/session-recovery.service.ts` → Existing service with `checkForOrphanedRuns()`
2. `src/app/core/components/session-recovery/` → Placeholder directory for component
3. `src/app/layout/unified-shell/unified-shell.component.ts` → App shell for dialog trigger
4. `.agent/skills/test-driven-development/SKILL.md` → TDD workflow
5. `.agent/skills/using-git-worktrees/SKILL.md` → Worktree setup

---

## Worktree Setup (REQUIRED FIRST STEP)

```bash
# Create isolated worktree for this feature
just jules-worktree session-recovery-ui

# Or manually:
git worktree add .worktrees/session-recovery-ui -b feat/session-recovery-ui
cd .worktrees/session-recovery-ui/praxis/web-client
npm install
```

---

## TDD Approach

### Step 1: Write E2E Test First

Create `e2e/specs/session-recovery-dialog.spec.ts`:

```typescript
import { test, expect } from '../fixtures/worker-db.fixture';

test.describe('Session Recovery Dialog', () => {
  test('shows recovery dialog when orphaned run exists', async ({ page, workerDb }) => {
    // Seed an orphaned run (status: 'running', stale heartbeat)
    await workerDb.exec(`
      INSERT INTO protocol_runs (id, status, metadata)
      VALUES ('orphaned-run-1', 'running', '{"lastHeartbeat": ${Date.now() - 60000}}')
    `);
    
    // Navigate to app - dialog should appear
    await page.goto('/app');
    
    // Verify dialog appears
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Protocol run was interrupted')).toBeVisible();
    
    // Verify action buttons
    await expect(page.getByRole('button', { name: 'Mark as Failed' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Dismiss' })).toBeVisible();
  });

  test('marks run as failed when button clicked', async ({ page, workerDb }) => {
    await workerDb.exec(`
      INSERT INTO protocol_runs (id, status, metadata)
      VALUES ('orphaned-run-2', 'running', '{"lastHeartbeat": ${Date.now() - 60000}}')
    `);
    
    await page.goto('/app');
    await page.getByRole('button', { name: 'Mark as Failed' }).click();
    
    // Dialog should close
    await expect(page.getByRole('dialog')).not.toBeVisible();
    
    // Verify run status updated
    const result = await workerDb.get(`SELECT status FROM protocol_runs WHERE id = 'orphaned-run-2'`);
    expect(result.status).toBe('failed');
  });

  test('does not show dialog when no orphaned runs', async ({ page }) => {
    await page.goto('/app');
    await expect(page.getByRole('dialog')).not.toBeVisible({ timeout: 3000 });
  });
});
```

### Step 2: Run Tests (Should Fail)

```bash
npx playwright test session-recovery-dialog.spec.ts --reporter=line 2>&1 | tail -20
```

---

## Implementation Steps

### 1. Create Recovery Dialog Component

```typescript
// src/app/core/components/session-recovery/session-recovery-dialog.component.ts
@Component({
  selector: 'app-session-recovery-dialog',
  standalone: true,
  imports: [MatDialogModule, MatButtonModule],
  template: `
    <h2 mat-dialog-title>Protocol Run Interrupted</h2>
    <mat-dialog-content>
      <p>A protocol run was interrupted. What would you like to do?</p>
      <mat-list>
        @for (run of data.orphanedRuns; track run.id) {
          <mat-list-item>{{ run.protocolName }} - Last active: {{ run.lastHeartbeat | date:'short' }}</mat-list-item>
        }
      </mat-list>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Dismiss</button>
      <button mat-flat-button color="warn" (click)="markAllFailed()">Mark as Failed</button>
    </mat-dialog-actions>
  `
})
export class SessionRecoveryDialogComponent {
  constructor(
    @Inject(MAT_DIALOG_DATA) public data: { orphanedRuns: OrphanedRun[] },
    private dialogRef: MatDialogRef<SessionRecoveryDialogComponent>,
    private recoveryService: SessionRecoveryService
  ) {}

  async markAllFailed(): Promise<void> {
    await this.recoveryService.markAllAsFailed(this.data.orphanedRuns);
    this.dialogRef.close('marked');
  }
}
```

### 2. Add markAllAsFailed to Service

```typescript
// In session-recovery.service.ts
async markAllAsFailed(runs: OrphanedRun[]): Promise<void> {
  for (const run of runs) {
    await this.protocolRuns.update(run.id, { status: 'failed' });
  }
}
```

### 3. Trigger Dialog on App Init

```typescript
// In unified-shell.component.ts
async ngOnInit(): Promise<void> {
  // ... existing init ...
  
  // Check for orphaned runs after DB ready
  const orphaned = await this.recoveryService.checkForOrphanedRuns();
  if (orphaned.length > 0) {
    this.dialog.open(SessionRecoveryDialogComponent, {
      data: { orphanedRuns: orphaned },
      disableClose: true
    });
  }
}
```

---

## Verification

```bash
# Run the E2E tests
npx playwright test session-recovery-dialog.spec.ts --reporter=line 2>&1 | tail -20

# Verify no regression
npx playwright test smoke.spec.ts --reporter=line 2>&1 | tail -10
```

---

## Merge Back

```bash
# After all tests pass
cd /Users/mar/Projects/praxis
git checkout main
git merge feat/session-recovery-ui
git worktree remove .worktrees/session-recovery-ui
```

---

## Success Criteria

- [ ] E2E tests written first and initially failing
- [ ] Dialog component created with proper Material styling
- [ ] Dialog appears on app load when orphaned runs exist
- [ ] "Mark as Failed" updates run status correctly
- [ ] "Dismiss" closes dialog without action
- [ ] All E2E tests pass
- [ ] No regression in smoke tests
