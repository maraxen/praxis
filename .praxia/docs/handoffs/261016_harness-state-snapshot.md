---
title: 'Harness-file state snapshot (praxis, as of 2026-01-31 text)'
description: E2E pass/fail status removed from AGENTS.md "Current State (2026-01-31)"; dated snapshot, not evidence about the tree today.
status: active
task_id: 261016_harness-fleet-audit
date: '261016'
---

## Current State (2026-01-31)

**✅ Passing:**
- `smoke.spec.ts` (4 tests, ~6s)
- `01-onboarding.spec.ts` (1 test, ~4s)  
- `health-check.spec.ts` (1 test, ~10s) - Fixed Observable pattern
- `protocol-library.spec.ts` (8 tests, ~21s)

**❌ Needs Attention:**
- `jupyterlite-bootstrap.spec.ts` - Missing PageObject method
- `ghpages-deployment.spec.ts` - Path resolution, SPA routing
- `asset-wizard.spec.ts` - Stale selectors (layout drift)
- `playground-direct-control.spec.ts` - Infrastructure issue

**Handoff (2026-01-31, historical):** `.praxia/docs/handoffs/260131_e2e-autonomous-handoff.md`

**Recent Fixes:**
- health-check.spec.ts: Replaced dynamic RxJS import with inline toPromise()
- health-check.spec.ts: Use localStorage for mode check
- AGENTS.md: Updated with Bun development guidelines
- AGENTS.md: Removed Autonomous Mode Development Cycle
