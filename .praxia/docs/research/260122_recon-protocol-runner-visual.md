---
title: 'RECON Report: Protocol Runner Visual Audit'
---

# RECON Report: Protocol Runner Visual Audit

## 1. Component Hierarchy Map

The Protocol Runner feature is composed of a main `RunProtocolComponent` that orchestrates a series of child components, primarily within a stepper-based wizard.

```
run-protocol.component.ts
├── app-protocol-card
│   └── app-protocol-warning-badge
├── app-protocol-card-skeleton
├── app-parameter-config
├── app-machine-selection
│   └── app-machine-card
├── app-machine-argument-selector
├── app-hardware-discovery-button
├── app-guided-setup
│   └── app-praxis-autocomplete
├── app-deck-setup-wizard
│   ├── app-setup-instructions
│   ├── app-requirements-panel
│   │   └── app-requirement-indicator
│   ├── app-carrier-placement-step
│   ├── app-resource-placement-step
│   └── app-verification-step
│   └── app-deck-view
├── app-protocol-summary
└── app-simulation-config-dialog
```

## 2. Hardcoded Color Audit

Numerous hardcoded colors and Tailwind CSS color classes were found. These should be replaced with the application's theme variables to ensure consistency and maintainability.

### `run-protocol.component.ts`

- **Line 312:** `[class.text-blue-400]` - Use `var(--sys-tertiary)` for a neutral/info color.
- **Line 328:** `!from-green-500 !to-emerald-600` - Use a theme variable for the gradient, e.g., `var(--gradient-primary)`.
- **Line 330:** `shadow-green-500/20 hover:shadow-green-500/40` - Use theme variables for shadows.
- **Line 377:** `.text-white-70 { color: var(--theme-text-secondary); }` - The class name is misleading, but it's using a theme variable. Recommend renaming the class.
- **Line 378:** `.border-green-500-30 { border-color: rgba(74, 222, 128, 0.3) !important; }` - Use `var(--theme-status-success-border)`.
- **Line 379:** `.bg-green-500-05 { background-color: rgba(74, 222, 128, 0.05) !important; }` - Use `var(--theme-status-success-muted)`.

### `guided-setup.component.ts`

- **Line 268:** `background: rgb(34, 197, 94);` - Use `var(--theme-status-success)`.
- **Line 272:** `color: rgb(34, 197, 94);` - Use `var(--theme-status-success)`.
- **Line 300:** `color: rgb(34, 197, 94);` - Use `var(--theme-status-success)`.
- **Line 306:** `color: rgb(251, 191, 36);` - Use `var(--theme-status-warning)`.
- **Line 310:** `color: rgb(34, 197, 94) !important;` - Use `var(--theme-status-success)`.
- **Line 322:** `.text-green { color: var(--theme-status-success) !important; }` - This is a good use of a theme variable, but the `!important` should be avoided if possible.

### `protocol-summary.component.ts`

- **Line 72:** `bg-green-500/10 text-green-500 border border-green-500/20` - Use `var(--theme-status-success-muted)`, `var(--theme-status-success)`, and `var(--theme-status-success-border)`.
- **Line 82:** `text-sm text-red-500 italic` - Use `var(--status-error)`.

### `live-dashboard.component.ts`

- **Line 1:** `[class.text-green-600]` - Use `var(--theme-status-success)`.
- **Line 1:** `[class.text-gray-400]` - Use `var(--theme-text-tertiary)`.
- **Line 2:** `[class.bg-green-100]` - Use `var(--theme-status-success-muted)`.
- **Line 3:** `[class.bg-red-100]` - Use `var(--theme-status-error-muted)` (needs to be created).
- **Line 4:** `bg-gray-900 text-green-400` - Use `var(--mat-sys-surface-container)` and `var(--theme-status-success)`.

### `setup-instructions.component.ts`

- **Line 104:** `background: var(--surface-container-low, #f5f5f5);` - Fallback color should be a theme variable.
- **Line 126:** `border-left-color: var(--error, #d32f2f);` - Fallback should be `var(--mat-sys-error)`.
- **Line 130:** `border-left-color: var(--primary, var(--status-info));` - Good use of variables.
- **Line 134:** `border-left-color: var(--secondary, #9e9e9e);` - Fallback should be `var(--theme-text-tertiary)`.
- **Line 173:** `color: var(--error, #d32f2f);` - Fallback should be `var(--mat-sys-error)`.
- **Line 177:** `color: var(--primary, var(--status-info));` - Good use of variables.
- **Line 181:** `color: var(--secondary, #9e9e9e);` - Fallback should be `var(--theme-text-tertiary)`.

## 3. Theme Variable Usage Gaps

- **Status Colors:** The application has theme variables for success, warning, and error states, but they are not consistently used. Many components use hardcoded colors or Tailwind classes for these states.
- **Gradients:** The "Start Execution" button has a hardcoded gradient that should be defined as a theme variable.
- **Shadows:** The same button uses hardcoded shadows that could be defined as theme variables.
- **Fallback Colors:** Several components use hardcoded fallback colors in their CSS. These should be replaced with theme variables to ensure that the application degrades gracefully if a variable is not defined.

## 4. Visual Issues List

- **Inconsistent Status Colors:** The use of different shades of green, red, and blue for status indicators creates a disjointed user experience.
- **Lack of Theming in Tailwind:** The use of Tailwind CSS color classes like `text-red-500` and `bg-green-100` is not integrated with the application's theming system. This means that these colors will not change when the user switches between light and dark themes.
- **Misleading Class Names:** The `.text-white-70` class in `run-protocol.component.ts` is misleading because it applies the `--theme-text-secondary` color, which is not necessarily white.

## 5. Recommendations

1.  **Replace all hardcoded colors with theme variables.** This is the most critical step to ensure visual consistency and maintainability.
2.  **Integrate Tailwind CSS with the application's theming system.** This can be done by defining the theme colors in the `tailwind.config.js` file and using the theme variables in the CSS.
3.  **Create new theme variables as needed.** For example, a variable for the "Start Execution" button gradient should be created.
4.  **Rename misleading CSS class names.** The `.text-white-70` class should be renamed to something more descriptive, like `.text-secondary`.
5.  **Remove `!important` flags where possible.** These can often be avoided by using more specific CSS selectors.
