# Styling Audit Report

**Date:** 2026-01-15
**Scope:** Frontend Codebase (`praxis/web-client/src/app`)
**Objective:** Identify hardcoded styling values and plan migration to Theme CSS Variables.

## 1. Executive Summary

A comprehensive scan of the frontend codebase reveals significant technical debt regarding hardcoded styling:

* **Colors:** Over 100+ instances of hardcoded hex codes.
* **Spacing:** Thousands of hardcoded pixel values (e.g., `8px`, `16px`) used for margins, padding, and sizing.
* **Offenders:** Several "hero" components (Shell, Docs, View Controls) rely heavily on only inline or hardcoded styles.

## 2. High Offensiveness Files

These files contain the highest density of hardcoded values and should be prioritized for refactoring.

### Top 5 Files by Hardcoded Pixels

| File | Count | Component Type |
| :--- | :--- | :--- |
| `view-controls.component.ts` | 77 | UI Controls |
| `unified-shell.component.ts` | 76 | Layout |
| `docs-page.component.ts` | 69 | Feature |
| `well-selector-dialog.component.ts` | 64 | Dialog |
| `hardware-discovery-dialog.component.ts` | 49 | Dialog |

**Recommendation:** Start migration with `unified-shell.component.ts` to establish global layout patterns, then move to reusable components (`view-controls`, `well-selector`).

## 3. Color Palette Analysis

Many hardcoded hex codes correspond exactly or closely to existing or needed theme variables.

| Hex Code | Count | Proposed Variable / Utility | Notes |
| :--- | :--- | :--- | :--- |
| `#ED7A9B` | 24 | `var(--primary-color)` | Rose Pompadour (Brand Primary) |
| `#ffffff` | 11 | `var(--mat-sys-on-primary)` or `text-white` | White text/background |
| `#73a9c2` | 11 | `var(--tertiary-color)` | Moonstone Blue |
| `#f44336` | 10 | `var(--mat-sys-error)` | Error Red |
| `#1a1a2e` | 8 | `var(--mat-sys-surface-container-low)` | Dark Background Base |
| `#4caf50` | 5 | `var(--mat-sys-success)` | Success Green |
| `#1976d2` | 4 | `var(--info-color)` (Needs Audit) | Info Blue |

**Action Item:** Define missing semantic variables for Info/Warning if they don't strictly align with Material System.

## 4. Spacing Analysis

Hardcoded pixel values are prevalent. Standardizing these to a scale (e.g., 4px grid) is critical.

| Pixel Value | Count | Standard |
| :--- | :--- | :--- |
| `8px` | 296 | `0.5rem` / `p-2` / `gap-2` |
| `16px` | 294 | `1rem` / `p-4` / `gap-4` |
| `12px` | 231 | `0.75rem` / `p-3` |
| `4px` | 151 | `0.25rem` / `p-1` |
| `24px` | 103 | `1.5rem` / `p-6` |

**Recommendation:** Enforce Tailwind utility classes (e.g., `p-2`, `m-4`) or CSS variables (`--spacing-2`) instead of raw pixels in SCSS.

## 5. Migration Plan Strategy

1. **Global Variable Enforcement**: Ensure `src/styles.scss` covers all identified common hex codes.
2. **Phase 1: Colors**: Replace all brand hex codes (#ED7A9B, #73a9c2) with `--primary-color` and `--tertiary-color`.
3. **Phase 2: Layout Shell**: Refactor `unified-shell.component.ts` to use semantic variables.
4. **Phase 3: Component Cleanup**: Tackle high-offender files one by one.
5. **Linting**: Consider adding a stylelint rule to warn against specific hardcoded values.
