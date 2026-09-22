---
title: 'Hardcoded CSS Audit Report'
---

## Hardcoded CSS Audit Report

This report identifies instances within `praxis/web-client/src` where hardcoded color values (hex, rgb, rgba) are used instead of theme-aware CSS variables.

### Critical (Settings Page)

| File | Line | Current Value | Suggested Variable |
| :--- | :--- | :--- | :--- |
| `settings.component.ts` | 275 | `rgba(30, 30, 45, 0.7)` | `var(--glass-bg)` |
| `settings.component.ts` | 278 | `rgba(255, 255, 255, 0.1)` | `var(--glass-border)` |
| `settings.component.ts` | 279 | `rgba(0, 0, 0, 0.37)` | `var(--glass-shadow)` |

### High Priority (Asset Management / Status indicators)

| File | Line | Current Value | Suggested Variable |
| :--- | :--- | :--- | :--- |
| `asset-filters.component.ts` | 172 | `rgba(34, 197, 94, 0.2)` / `rgb(34, 197, 94)` | `var(--mat-sys-success-container)` / `var(--mat-sys-success)` |
| `asset-filters.component.ts` | 173 | `rgba(59, 130, 246, 0.2)` / `rgb(59, 130, 246)` | `var(--mat-sys-primary-container)` / `var(--mat-sys-primary)` |
| `asset-filters.component.ts` | 174 | `rgba(239, 68, 68, 0.2)` / `rgb(239, 68, 68)` | `var(--mat-sys-error-container)` / `var(--mat-sys-error)` |
| `asset-filters.component.ts` | 175 | `rgba(245, 158, 11, 0.2)` / `rgb(245, 158, 11)` | `var(--mat-sys-warning-container)` / `var(--mat-sys-warning)` |
| `maintenance-badge.component.ts` | 54-56 | Green shades (hardcoded) | `var(--mat-sys-success)` variables |
| `maintenance-badge.component.ts` | 60-62 | Amber shades (hardcoded) | `var(--mat-sys-warning)` variables |
| `maintenance-badge.component.ts` | 66-68 | Red shades (hardcoded) | `var(--mat-sys-error)` variables |

### Other Files

| File | Line | Current Value | Suggested Variable |
| :--- | :--- | :--- | :--- |
| `filter-header.component.ts` | 70 | `rgba(0,0,0,0.05)` | `var(--glass-shadow)` or `var(--theme-border)` |
| `resource-accordion.component.ts` | 278 | `rgba(0,0,0,0.1)` | `var(--theme-border)` or `var(--glass-shadow)` |
| `asset-dashboard.component.ts` | 201 | `rgba(248, 113, 113, 0.2)` | `var(--mat-sys-error-container)` |
| `home.component.ts` | 249 | `rgba(0, 0, 0, 0.4)` | `var(--glass-shadow)` |
| `machine-focus-view.component.ts` | 115 | `rgba(0,0,0,0.05)` | `var(--glass-shadow)` |
| `run-filters.component.scss` | 39-50 | Multiple status colors | `var(--mat-sys-* status)` variables |

### Summary

The `Settings` page and `Asset Management` modules contain several hardcoded `rgba` values for panels and status indicators. These should be migrated to the centralized CSS variables defined in `styles.scss` to ensure consistent theming (especially across Light/Dark modes).
