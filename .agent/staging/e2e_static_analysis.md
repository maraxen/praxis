# E2E Static Analysis - Redundant/Outdated Tests

> Generated: 2026-01-31T09:00

## Categories for Review

### 🗑️ Candidates for Removal/Consolidation

| Spec | Lines | Issue | Recommendation |
|------|-------|-------|----------------|
| `verify-logo-fix.spec.ts` | 25 | One-off fix verification | **DELETE** - smoke test covers this |
| `screenshot_recon.spec.ts` | 55 | Recon tool, not test | **MOVE** to tools/ |
| `low-priority-capture.spec.ts` | 49 | Screenshot capture only | **DELETE** or move to tools/ |
| `medium-priority-capture.spec.ts` | ? | Screenshot capture only | **DELETE** or move to tools/ |
| `capture-remaining.spec.ts` | 56 | Screenshot capture only | **DELETE** or move to tools/ |
| `asset-wizard-visual.spec.ts` | ? | Visual regression | Keep if VRT configured, else DELETE |

### 🔄 Redundant Test Coverage

**6 specs test createMachine flow:**
1. `02-asset-management.spec.ts` (CRUD tests)
2. `04-browser-persistence.spec.ts`
3. `asset-inventory.spec.ts`
4. `functional-asset-selection.spec.ts`
5. `machine-frontend-backend.spec.ts`
6. `user-journeys.spec.ts`

**Recommendation**: Keep `machine-frontend-backend.spec.ts` as canonical wizard test, simplify others to use mocked machine data.

### ⚠️ Potentially Outdated

| Spec | Issue |
|------|-------|
| `ghpages-deployment.spec.ts` | May reference old deployment config |
| `mock-removal-verification.spec.ts` | One-time verification, can remove |
| `interactive-protocol.spec.ts` | 37 lines, very minimal |

### 📊 Spec Size Distribution

**Tiny (<50 lines) - Review for value:**
- verify-logo-fix (25)
- interactive-protocol (37)
- 01-onboarding (48)
- low-priority-capture (49)

**Large (>200 lines) - Core tests:**
- machine-frontend-backend (483)
- protocol-library (300+)
- catalog-workflow (200+)

---

## Summary

| Category | Count | Action |
|----------|-------|--------|
| Remove (capture/one-off) | 6 | Delete or move to tools/ |
| Consolidate (createMachine) | 5 | Simplify to use mocked data |
| Keep as-is | 27 | |

**Estimated cleanup: ~15% of specs (6/38) are low-value**
