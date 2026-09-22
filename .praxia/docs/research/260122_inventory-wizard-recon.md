---
title: 'Recon Report: Inventory Wizard Analysis'
---

# Recon Report: Inventory Wizard Analysis

**Date**: 2026-01-21
**Target**: Asset Wizard (Inventory Creation)
**Component**: `AssetWizard`
**Location**: `src/app/shared/components/asset-wizard/`

## 1. Component Identification

The "Add Inventory Wizard" corresponds to the `AssetWizard` component.

- **Controller**: `asset-wizard.ts`
- **Template**: `asset-wizard.html`
- **Styles**: `asset-wizard.scss`
- **Trigger**: `PlaygroundComponent` -> `openInventory()` -> `MatDialog.open(AssetWizard)`

## 2. Current Implementation Logic

The wizard is implemented as a **Linear Stepper** (`MatStepper`) with 4 steps:

1. **Type & Category**: Selects 'MACHINE' vs 'RESOURCE' and sub-category. Driven by `typeStepFormGroup`.
2. **Definition**: Searchable list of `MachineDefinition` or `ResourceDefinition`. Uses `AssetService.search*` methods.
3. **Configuration**: Instance configuration (Name, Backend/Driver, Connection Info). Context-aware (hides backend for Resources, handles simulated backends).
4. **Review**: Summary screen and final `createAsset()` call.

## 3. Critical Findings: Why it is "UGLY"

The visual inspection helps confirm significant missing styles. The HTML structure implies a sophisticated layout that is **completely unimplemented** in the CSS.

### A. Missing CSS Patterns (The "Ghost" Classes)

The HTML relies on numerous classes that **do not exist** in the `asset-wizard.scss` or global search. These elements are effectively unstyled `<div>`s:

- `.asset-wizard-container` (No layout container)
- `.step-content` (No padding/spacing)
- `.type-selection`, `.type-card` (Intended as cards/grid, rendering as plain stacked blocks)
- `.category-selection`
- `.step-actions` (Buttons likely jammed together or default aligned)
- `.search-container`
- `.results-grid`, `.result-card` (Search results likely render as a plain vertical list with no card styling)
- `.form-grid`

### B. Design System Violations

- **Hardcoded Colors**: The few styles that *do* exist (for `.review-card`) use hardcoded hex values:
  - `#fafafa` (Background)
  - `#eee` (Borders)
  - `#666`, `#333`, `#3f51b5` (Text/Primary)
- **No Design Tokens**: The component completely ignores the `var(--mat-sys-...)` token system used elsewhere in the application, making it incompatible with Dark Mode and theming.
- **Typography**: No use of typography mixins or classes.

### C. UI/UX Gaps

- **Responsive Layout**: Without the grid CSS, the "cards" for type selection and search results do not reflow.
- **Interactive States**: No hover effects or selection states defined for `.type-card` or `.result-card`.
- **Feedback**: The "Loading" state is implemented but uses a simple spinner with hardcoded `#3f51b5` text.

## 4. Recommendations for Designer Task

A complete redesign is required. The logic is functional (Angular Reactive Forms + Stepper), but the View Layer is incomplete.

**Action Plan:**

1. **Implement Layout CSS**: Create proper Flex/Grid layouts for `.type-selection` and `.results-grid`.
2. **Tokenize Colors**: Replace all hex codes with `var(--mat-sys-surface-container)`, `var(--mat-sys-on-surface)`, etc.
3. **Card Components**: Style `.type-card` and `.result-card` to look like interactive, selectable elements (elevation, border, hover states).
4. **Standardize Spacing**: Use standard spacing variables instead of `20px`/`12px`.
