# Deep Audit Synthesis: Praxis Web-Client
**Date**: Feb 3, 2026
**Sessions Analyzed**: 15+ Jules deep audit sessions
**Project**: praxis/web-client (Angular)

---

## Executive Summary

This synthesis consolidates findings from ~15 completed Jules deep audit sessions covering the Praxis Angular web-client. The audit examined protocol execution, asset management, browser persistence, E2E testing, and core services.

### Overall Quality Score: **5.5/10**

| Module | Score | Critical Issues |
|--------|-------|-----------------|
| Run Protocol | 4/10 | Stepper brittleness, machine config gaps |
| Asset Management | 4/10 | 40+ type casts, missing CRUD tests |
| Core Services | 6/10 | Well-architected, minor Pyodide gaps |
| Resource/Index Components | 4/10 | Zero keyboard accessibility |
| E2E Testing | 5/10 | Auth/workcell/docs uncovered |
| Docs/State Inspector | 6.5/10 | Mermaid fragility, zero DocsPage tests |

---

## Critical Issues (P1) - Blocking/Security

| ID | Issue | Location | Impact |
|----|-------|----------|--------|
| P1-001 | **Zero keyboard accessibility** for grid selection | `IndexSelectorComponent`, `ResourceAccordionComponent` | ADA/WCAG non-compliance |
| P1-002 | **40+ `as any` casts** hide runtime errors | `AssetService`, `browser-mode.interceptor.ts` | Type safety bypass, silent failures |
| P1-003 | **DocsPageComponent has zero tests** | `docs-page.component.ts` | Core UI completely untested |
| P1-004 | **TS compilation errors block E2E** | `run-detail.component.ts:formatDateTime` | All E2E tests fail to start |
| P1-005 | **Machine config not populated in browser mode** | `ExecutionService.executeBrowserProtocol` | `resolved_assets_json` always null |

---

## High Priority (P2) - Current Sprint

| ID | Issue | Location | Recommendation |
|----|-------|----------|----------------|
| P2-001 | Linear stepper uses hardcoded indices | `RunProtocolComponent` | Use named step mapping |
| P2-002 | Missing MachineListComponent tests | `machine-list.component.ts` | Add signal-based filtering tests |
| P2-003 | Mermaid tied to ngx-markdown internals | `docs-page.component.ts:586` | Custom renderer or dedicated component |
| P2-004 | Ephemeral resources never cleaned | `ConsumableAssignmentService` | Add purge job or UI action |
| P2-005 | Missing pause/resume protocol endpoints | `execution.service.ts` | Implement server-side endpoints |
| P2-006 | Window event listener for 'machine-registered' | `machine-list.component.ts:413` | Replace with Angular Subject |

---

## Medium Priority (P3) - Backlog

| ID | Issue | Location |
|----|-------|----------|
| P3-001 | `Math.random()` for serial number generation | `asset.service.ts:98` |
| P3-002 | Hardcoded `µL` unit heuristic | `state-inspector.component.ts:609` |
| P3-003 | `brands` computed re-scans all resources | `resource-accordion.component.ts:461` |
| P3-004 | Duplicated icon mapping logic | `resource-accordion.component.ts:729` |
| P3-005 | FQN divergence between browser/production | `category-inference.ts` |

---

## Tech Debt Summary

### By Category

| Category | Count | Severity |
|----------|-------|----------|
| Type Safety | 60+ occurrences | High |
| Testing Gaps | 4 critical modules | High |
| Accessibility | 2 components | High |
| Performance | 2 bottlenecks | Medium |
| Code Smells | 21 TODOs | Low-Medium |

### Key Tech Debt Items

1. **[high/robustness]** Pervasive `as any` casting in AssetService, browser interceptors
2. **[high/testing]** ResourceAccordionComponent tests broken (missing ActivatedRoute)
3. **[high/accessibility]** Zero keyboard support for grid interactions
4. **[medium/types]** StateInspectorComponent uses `any` for diffing logic
5. **[medium/testing]** Low coverage for complex wizard logic
6. **[low/cleanup]** 3 orphaned index.ts barrel files

---

## E2E Coverage Gaps

### Modules Without Coverage
- `auth` - Login, logout, session, RBAC
- `workcell` - Dashboard functionality
- `docs` - Documentation viewer
- `stress-test` - Performance testing

### Missing Critical Flows
- Protocol failure and recovery
- Asset edit/delete lifecycle
- Advanced search/filtering
- Playground direct control

---

## Service Layer Analysis

The service layer is **well-architected** with:
- All services use `providedIn: 'root'` correctly
- Clear core/feature separation
- No circular dependencies detected
- Unidirectional dependency flow

**Risk**: Runtime circular dependencies through method calls as app grows.

---

## Complexity Hotspots

| File | Metric | Value |
|------|--------|-------|
| `plr-definitions.ts` | Cyclomatic Complexity | 26 |
| `run-protocol.component.ts` | Dependencies | 41 |
| `asset-wizard.component.ts` | Cyclomatic Complexity | 9 |
| `extractUniqueNameParts` | LOC | 69 |

---

## Dead Code Identified

| Type | Item | Location |
|------|------|----------|
| Component | `ProtocolListSkeletonComponent` | `protocol-list-skeleton.component.ts` |
| Service | `AuthService` | `auth/services/auth.service.ts` |
| Orphan | `view-controls/index.ts` | shared/components |
| Orphan | `protocol-warning-badge/index.ts` | shared/components |
| Orphan | `confirmation-dialog/index.ts` | shared/components |

---

## Recommendations Summary

### Immediate Actions (This Sprint)
1. Fix TS error in `run-detail.component.ts` (`iso-date` → `isoDate`)
2. Add `role="grid"`, `tabindex`, keyboard listeners to IndexSelectorComponent
3. Update Asset models to match API generated types (remove casts)
4. Add DocsPageComponent unit tests

### Near-Term (Next 2 Sprints)
5. Implement ephemeral resource cleanup mechanism
6. Replace window event listeners with Angular services
7. Formalize simulator backend mapping in schema
8. Expand E2E coverage to auth, workcell, docs

### Long-Term (Roadmap)
9. Refactor run-protocol stepper to use named steps
10. Create dedicated mermaid rendering component
11. Centralize facet/FQN logic for browser mode

---

## Jules Session IDs Analyzed

| Session ID | Focus Area | Status |
|------------|------------|--------|
| 1530702602442313801 | Resource/Index components | Completed |
| 9343870938443040265 | Protocol execution | Completed |
| 6053508350166975463 | Machine selection | Completed |
| 6546155916196685132 | Asset wizards | Completed |
| 6602665788886583153 | Shared components | Completed |
| 17585661742425938948 | Core services | Completed |
| 5948510037840387857 | State management | Completed |
| 722255056572614367 | API layer | Completed |
| 18252387941259554826 | Persistence | Completed |
| 16104588224268161412 | Python/Pyodide | Completed |
| 16334618667450956192 | E2E testing | Completed |
| 4929236208583428701 | Main modules | Completed |
| 6491192860331751931 | Feature modules | Completed |
| 6792077716272402628 | Routing | Completed |
| 12060423353350524806 | Dialog components | Completed |
| 5981630414686659482 | Run Protocol feature | Completed |
| 1009855817323566566 | Core Services | Completed |

---

*Generated by orchestrator synthesis session, Feb 3, 2026*
