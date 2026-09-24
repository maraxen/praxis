---
title: 'RECON Report: Theme CSS Variable Audit'
---

# RECON Report: Theme CSS Variable Audit

## 1. Hardcoded Color Inventory & Theme Variable Mapping

| File | Line | Hardcoded Value | Suggested Theme Variable | Exists? | Priority | Notes |
|---|---|---|---|---|---|---|
| `praxis/web-client/src/app/features/protocols/components/protocol-detail-dialog/protocol-detail-dialog.component.ts` | 200 | `text-yellow-500` | `--theme-status-warning` | Yes | High | Tailwind class should be replaced with a proper themed class. |
| `praxis/web-client/src/app/features/settings/components/settings.component.ts` | 136 | `text-green-600` | `--theme-status-success` | Yes | Medium | Tailwind class used for "completed" text. |
| `praxis/web-client/src/app/features/settings/components/settings.component.ts` | 136 | `dark:text-green-400` | `--theme-status-success` | Yes | Medium | Tailwind dark mode variant. |

## 2. Theme Variables to be Created

No new theme variables are immediately necessary based on this audit. The existing `--theme-status-warning` and `--theme-status-success` variables are sufficient for the identified hardcoded colors.

## 3. Priority Ranking

1.  **High:** `protocol-detail-dialog.component.ts`: The warning color for simulation violations is a key status indicator and should be themed.
2.  **Medium:** `settings.component.ts`: The "completed" status text is less critical than a warning, but should still be themed for consistency.

## 4. Summary

The audit revealed a small number of hardcoded colors, primarily using Tailwind CSS utility classes. The existing theme variable system is adequate to address these findings without requiring the creation of new variables. The priority should be to replace the Tailwind classes with theme-aware styles.
