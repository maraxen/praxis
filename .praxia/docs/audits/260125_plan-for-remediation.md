---
title: 'Handoff: Addressing Critical Audit Blockers'
---

# Handoff: Addressing Critical Audit Blockers

**Date**: 2026-01-25  
**Context**: Jan 24 Shipping Readiness Audit completed. 6 key areas audited. 8 critical blockers identified.

## 🔴 Critical Roadmap (Sorted by Priority)

### 1. Safety & Stability

- **AUDIT-01: Simulated/Physical Validation Gap**
  - **Issue**: No validation to prevent starting a physical run with a simulated machine.
  - **Target**: `run-protocol.component.ts`, `execution.service.ts`.
  - **Needed**: A hard stop in the UI/Service layer if `machine.is_simulation_override` is mismatched with the protocol's intended execution mode.

- **AUDIT-06: Database Schema Migrations**
  - **Issue**: No versioning or migration path for OPFS SQLite.
  - **Target**: `sqlite-opfs.worker.ts`, `sqlite.service.ts`.
  - **Needed**: Implement a `PRAGMA user_version` check on init. Guide user through "Factory Reset" if mismatch detected for now.

### 2. Core Operational Reliability

- **AUDIT-03: Missing Execution Controls**
  - **Issue**: No `PAUSE` or `CANCEL` in UI.
  - **Target**: `run-detail.component.ts`.
  - **Needed**: Implementation of the `executionService.stop()` or `cancel()` calls in the UI buttons.

- **AUDIT-07: JupyterLite Bootstrap Limits**
  - **Issue**: URL length limits for Python bootstrap code.
  - **Target**: `playground.component.ts`.
  - **Needed**: Move bootstrap script to a static `.py` file or use `postMessage` to send it *after* kernel load instead of via URL param.

### 3. Functional Gaps

- **AUDIT-09: Direct Control Realism**
  - **Issue**: Uses mock methods, not introspected machine methods.
  - **Target**: `direct-control.component.ts`.
  - **Needed**: Replace `getMockMethodsForCategory` with a real call to the driver's capability introspection.

## 🛠️ Next Session Instructions

1. **Pick a Blocker**: Start with AUDIT-01 or AUDIT-06 as they are the highest risk.
2. **Review Detailed Audit**: Read the corresponding file in `docs/audits/` for component maps and suggested test cases.
3. **Verify-And-Merge**: Ensure any fix includes the recommended E2E tests mentioned in the audit doc.

## Status of Campaign

- [x] Audit merged to `docs/audits/`
- [x] Consolidated `INDEX.md` created
- [ ] Retries for AUDIT-02, 04, 05 (Followed up by User)
