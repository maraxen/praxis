# Frontend Polish Pipeline

This document describes the visual polish pipeline used for the Praxis web-client and tracks remaining items for future sessions.

## Pipeline Overview

The frontend polish pipeline is a systematic approach to identifying and fixing visual/UI issues using a combination of automated screenshot capture and AI-powered analysis.

### Pipeline Stages

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  1. CAPTURE     │ ──▶ │  2. ANALYZE     │ ──▶ │  3. FIX         │ ──▶ │  4. VALIDATE    │
│  (flash agent)  │     │  (multimodal)   │     │  (flash agent)  │     │  (multimodal)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Stage 1: Capture Screenshots (flash agent)

Use Playwright to capture screenshots of target components/pages.

**Command Pattern:**
```bash
cd praxis/web-client
npx playwright test e2e/specs/viz-review.spec.ts --project=chromium
```

**Key Considerations:**
- Capture both light and dark mode variants
- Capture different states (empty, loading, populated)
- Capture responsive views (narrow viewport)
- Save to organized directories: `e2e/screenshots/<category>/`

**Existing Spec Files:**
- `e2e/specs/viz-review.spec.ts` - General visual review captures
- `e2e/specs/capture-all-dialogs.spec.ts` - Dialog component captures

### Stage 2: Analyze with Multimodal Agent

Dispatch the `multimodal-looker` agent to analyze screenshots for visual issues.

**Analysis Criteria:**
1. Layout and spacing issues
2. Typography problems (font sizes, weights, readability)
3. Color contrast and accessibility
4. Alignment issues
5. Visual hierarchy
6. Empty states
7. Button/control styling
8. Truncation or overflow
9. Dark mode specific issues

**Agent Dispatch Pattern:**
```
background_task(
  agent: "multimodal-looker",
  prompt: "Analyze screenshots at <paths>. For each, evaluate <criteria>. Return structured report with issues, priority, and CSS recommendations.",
  sync: true
)
```

### Stage 3: Apply Fixes (flash agent)

Dispatch `flash` agents with specific fix instructions based on multimodal analysis.

**Fix Dispatch Pattern:**
```
task(
  subagent_type: "flash",
  prompt: "Fix <issue> in <file>. Apply these CSS changes: <specific CSS>. Return summary of changes."
)
```

**Best Practices:**
- Provide specific file paths
- Include exact CSS/styling recommendations from analysis
- Request summary of changes for tracking

### Stage 4: Validate Improvements (multimodal agent)

Capture new "after" screenshots and compare with "before" versions.

**Validation Criteria:**
- Is the issue fixed?
- Are there visible improvements?
- Any regressions introduced?
- Overall quality assessment

---

## Completed Items (This Session)

### Critical Priority
| Component | File | Fixes Applied |
|-----------|------|---------------|
| Deck View | `shared/components/deck-view/deck-view.component.ts` | Contrast, labels 9px→11px, shadows, label backplates |
| Dark Mode Dashboard | `features/home/home.component.ts` | Card borders, better shadows, empty states contrast |

### High Priority
| Component | File | Fixes Applied |
|-----------|------|---------------|
| Nav Rail | `layout/unified-shell.component.ts` | Theme-aware background, 2px active borders, unified hover |
| Protocol Library Table | `features/protocols/components/protocol-library/protocol-library.component.ts` | Table headers, badge styling, action alignment |
| Sidebar Collapse | `layout/unified-shell.component.ts` | Hidden labels in rail mode (display:none), transparent bottom controls, icon centering - VALIDATED 10/10 |
| Asset Library | `features/assets/assets.component.ts` | Tab min-width 80px, pill buttons, removed double border |
| Asset Dashboard | `features/assets/components/asset-dashboard/asset-dashboard.component.ts` | Reduced button padding, unified section headers |
| Protocol Detail Panel | `features/protocols/components/protocol-detail/protocol-detail.component.ts` | Increased padding 32px, header border, pre-wrap descriptions |
| Protocol Detail Dialog | `features/protocols/components/protocol-detail-dialog/protocol-detail-dialog.component.ts` | Solid background, backdrop blur, ellipsis truncation, button spacing |

### Medium Priority
| Component | File | Fixes Applied |
|-----------|------|---------------|
| Run Protocol Wizard | `features/run-protocol/run-protocol.component.ts` | Stepper padding, sticky footer, focus states |
| Protocol Library Empty | `protocol-library.component.ts` | Icon opacity 40%, dimensions !w-16 !h-16, added Upload Protocol CTA button |
| Asset Dashboard Empty | `asset-dashboard.component.ts` | Icon !w-12 !h-12 !text-[48px], text-lg font-semibold |
| Workcell Dashboard | `workcell-dashboard.component.ts` | Icon text-slate-400, !w-16 !h-16 !text-[64px], mat-flat-button, flex flex-col on container |
| Login Component | `login.component.ts` | Glass card uses var(--glass-bg), error uses var(--mat-sys-error), blur 20px |

### Dialog Sizing (Previous Session)
| Dialog | Fixes Applied |
|--------|---------------|
| AddAssetDialog | `min-width: 600px; max-width: 850px; width: 70vw` |
| InventoryDialog | `min-height: 400px; max-height: 70vh; height: auto` |
| ResourceDialog | `min-width: 600px; max-width: 800px; width: 70vw` |

---

## Current Session Progress

### Validated This Session
| Component | Status | Score | Notes |
|-----------|--------|-------|-------|
| Sidebar/Nav Rail | ✅ PASS | 10/10 | Labels hidden, icons centered, bottom controls clean |
| Protocol Library Empty State | ✅ PASS | 10/10 | Icon visibility improved, CTA button added |
| Asset Dashboard Empty State | ✅ PASS | 10/10 | check_circle renders correctly, text prominent |
| Workcell Dashboard Empty State | ✅ PASS | 10/10 | Icon visibility improved, CTA is filled button |
| Workcell Loading State | ✅ PASS | 8/10 | Spinner centered (code verified), container sizing correct |
| Login Page | ✅ PASS | 10/10 | Glass background darker, text shadow added, retry button styled |
| Settings Page | ✅ PASS | 9/10 | Glassmorphism applied, layout centered (max-w-5xl), dividers spaced |
| Snackbars | ✅ PASS | 9/10 | High contrast pink action, solid dark bg, z-index fixed above footer |

### Medium Priority Completed
| Component | File | Fixes Applied |
|-----------|------|---------------|
| Protocol Library Empty | `protocol-library.component.ts` | Icon opacity 40%, dimensions !w-16 !h-16, added Upload Protocol CTA button |
| Asset Dashboard Empty | `asset-dashboard.component.ts` | Icon !w-12 !h-12 !text-[48px], text-lg font-semibold |
| Workcell Dashboard | `workcell-dashboard.component.ts` | Icon text-slate-400, !w-16 !h-16 !text-[64px], mat-flat-button, flex flex-col on container |
| Login Component | `login.component.ts` | Glass card uses var(--glass-bg), error uses var(--mat-sys-error), blur 20px |

### Low Priority Completed
| Component | File | Fixes Applied |
|-----------|------|---------------|
| Settings Page | `settings.component.ts` | Added .glass-panel styles, centered layout with max-w-5xl, improved divider spacing |
| Snackbars | `styles.scss` | Global overrides: solid dark bg, pink action text, margin-bottom 48px, z-index 2000 |

### Remaining Items
- **Charts (Telemetry, Heatmap)**: 🛑 BLOCKED | Test environment data issue (no protocols found in browser mode reset). See `TECHNICAL_DEBT.md`.

---

## Remaining Items

*None (except blocked items)*

---

## Screenshot Locations

```
praxis/web-client/e2e/screenshots/
├── dialogs/                    # Dialog component screenshots
├── viz-review/                 # Visual review screenshots
├── medium-priority/            # Login, Empty States
└── low-priority/               # Settings, Snackbars
```

---

## Quick Start for New Session

### 1. Verify Environment
```bash
cd praxis/web-client
npm run build                    # Ensure build passes
npm run start:browser &          # Start dev server
```

### 2. Capture Screenshots for Target Components
```bash
npx playwright test e2e/specs/viz-review.spec.ts --project=chromium
```

### 3. Dispatch Analysis
Use multimodal-looker agent to analyze captured screenshots.

### 4. Apply Fixes
Dispatch flash agents with specific CSS fixes from analysis.

### 5. Validate
Capture "after" screenshots and compare with multimodal agent.

---

## Agent Usage Notes

| Agent | Use Case |
|-------|----------|
| `flash` | Screenshot capture, applying specific fixes, running tests |
| `multimodal-looker` | Analyzing screenshots, comparing before/after |
| `investigator` | Deep-dive into component issues, finding root causes |
| `explore` | Finding files, understanding codebase structure |

---

## Related Documentation

- `.agents/ACTIVE_DEVELOPMENT.md` - Current development status
- `.agents/TECHNICAL_DEBT.md` - Known issues (e.g. data seeding)
- `praxis/web-client/e2e/` - Playwright test infrastructure
- `praxis/web-client/src/styles.scss` - Global styles and theme variables
