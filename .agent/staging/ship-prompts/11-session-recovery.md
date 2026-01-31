# Session Recovery Implementation (P2)

> **Stream**: 6 - Reliability & UX  
> **Effort**: L (4-6 hours)  
> **Priority**: P2

---

## Objective

Implement session recovery so interrupted protocol runs can be resumed after browser crash or accidental tab close.

---

## Context Files (Read First)

1. `.agent/staging/logic-audits/09-recommendations.md` → Session Recovery
2. `src/app/core/db/repositories/protocolRuns.repository.ts`
3. `src/app/features/run-protocol/services/execution.service.ts`
4. `src/app/core/db/enums.ts` → ProtocolRunStatus

---

## Root Cause Analysis

**Problem**: If browser crashes mid-run:
- Run status stuck in `running` or `pausing`
- No mechanism to detect orphaned runs
- User must manually clean up and restart

**Desired behavior**:
- On app load, detect orphaned runs
- Prompt user: "A protocol run was interrupted. Resume or discard?"
- Resume from last checkpoint OR mark as failed

---

## Scope

### Change
- Add `lastHeartbeat` field to ProtocolRun model
- Create `SessionRecoveryService` to detect orphaned runs
- Add UI prompt for recovery action
- Update `execution.service.ts` to write heartbeats

### Do NOT Change
- Protocol execution logic
- Database schema (use existing JSON fields)
- Run state machine transitions

---

## Implementation Steps

1. **Add heartbeat tracking**
   ```typescript
   // In ProtocolRun model (use metadata JSON field)
   interface RunMetadata {
     lastHeartbeat?: number; // timestamp
     checkpointStep?: number;
     checkpointState?: any;
   }
   ```

2. **Write heartbeats during execution**
   ```typescript
   // execution.service.ts
   private heartbeatInterval?: ReturnType<typeof setInterval>;
   
   private startHeartbeat(runId: string): void {
     this.heartbeatInterval = setInterval(async () => {
       await this.protocolRuns.updateMetadata(runId, {
         lastHeartbeat: Date.now()
       });
     }, 5000); // Every 5 seconds
   }
   ```

3. **Create SessionRecoveryService**
   ```typescript
   // session-recovery.service.ts
   @Injectable({ providedIn: 'root' })
   export class SessionRecoveryService {
     async checkForOrphanedRuns(): Promise<OrphanedRun[]> {
       const activeRuns = await this.protocolRuns.findByStatus(['running', 'pausing', 'resuming']);
       const orphaned: OrphanedRun[] = [];
       
       for (const run of activeRuns) {
         const lastHeartbeat = run.metadata?.lastHeartbeat ?? 0;
         const staleThreshold = Date.now() - 30000; // 30 seconds
         
         if (lastHeartbeat < staleThreshold) {
           orphaned.push(run);
         }
       }
       
       return orphaned;
     }
   }
   ```

4. **Add recovery prompt UI**
   - Show dialog on app init if orphaned runs detected
   - Options: "Resume", "Mark as Failed", "Dismiss"

5. **Implement resume logic**
   ```typescript
   async resumeRun(runId: string): Promise<void> {
     // Re-initialize execution context
     // Skip to checkpoint step
     // Continue execution
   }
   ```

---

## Verification

```bash
# Unit tests for session recovery service
npm run test -- --include="**/session-recovery.service.spec.ts"

# E2E test (manual):
# 1. Start protocol run
# 2. Force kill browser (kill -9)
# 3. Reopen app
# 4. Verify recovery prompt appears
```

---

## Success Criteria

- [ ] Heartbeat written every 5 seconds during run
- [ ] Orphaned runs detected on app load
- [ ] Recovery dialog shown with options
- [ ] "Mark as Failed" updates run status correctly
- [ ] "Resume" restarts execution (best-effort)

---

## Notes

Full resume (from exact step) requires checkpoint state that may not be available. MVP can be:
1. Detect orphaned run
2. Offer to mark as failed
3. Log last known state for debugging

True resume is a stretch goal.
