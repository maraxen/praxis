---
title: 'AUDIT-08: GitHub Pages Deployment Configuration'
---

# AUDIT-08: GitHub Pages Deployment Configuration

This audit reviews the configuration and deployment process for the GitHub Pages version of the Praxis web client.

## 1. Build Configuration Summary

The `gh-pages` build is defined in `praxis/web-client/angular.json` under the `projects.web-client.architect.build.configurations.gh-pages` key.

| Setting | Value | File |
| :--- | :--- | :--- |
| **File Replacements**| `src/environments/environment.gh-pages.ts` | `angular.json` |
| **Base Href** | `/praxis/` | `angular.json` |
| **Optimization** | `true` | `angular.json` |
| **Output Hashing** | `all` | `angular.json` |
| **Output Path** | `./praxis/web-client/dist/web-client/browser` | `deploy.yml` |

## 2. Asset Resolution Checklist

| Asset Type | Status | Notes |
| :--- | :--- | :--- |
| **Images** | ✅ Pass | Handled by Angular's build process and `baseHref`. |
| **Fonts** | ✅ Pass | Handled by Angular's build process and `baseHref`. |
| **Static JSON** | ✅ Pass | Handled by Angular's build process and `baseHref`. |
| **JupyterLite Assets**| ✅ Pass | Extensively tested in `ghpages-deployment.spec.ts`. |
| **Worker Files** | ✅ Pass | Implicitly tested by SQLite initialization test. |

## 3. Environment Comparison

| Setting | Dev (`environment.ts`) | GH-Pages (`environment.gh-pages.ts`) |
| :--- | :--- | :--- |
| **`production`** | `false` | `false` |
| **`browserMode`** | `false` (default) | `true` |
| **`apiUrl`** | `/api/v1` | `/api/v1` (intercepted) |
| **`wsUrl`** | `'ws://localhost:8000/api/v1/ws'` | `''` (disabled) |
| **`keycloak.enabled`**| `true` (default) | `false` |
| **`sqliteOpfsEnabled`**| `false` | `false` |
| **Base HREF** | `/` | `/praxis/` |
| **Assets Path** | `/assets` | `/praxis/assets` |

## 4. Gap/Limitation List

| Severity | Issue | Description |
| :--- | :--- | :--- |
| 🟡 **Yellow** | **`production: false` in `environment.gh-pages.ts`** | The `gh-pages` environment is not a true production environment. Angular's `enableProdMode()` is not called, which can impact performance. This seems intentional to keep it as a demo environment. |
| 🟡 **Yellow** | **Limited E2E asset coverage** | While JupyterLite assets are well-tested, there is no specific E2E test to verify the loading of other static assets like images or fonts within specific components. |
| 🟠 **Orange** | **No CSP Header** | The application is not served with a Content-Security-Policy (CSP) header, which could expose it to cross-site scripting (XSS) attacks. |

## 5. Recommended Test Cases

*   **Test Case 1: Verify a static image asset in a component.**
    *   **Description:** Create a test that navigates to a page with a static image (e.g., a logo in the about dialog) and verifies that the image loads correctly.
*   **Test Case 2: Verify a custom font is applied.**
    *   **Description:** Create a test that checks if a specific element has the correct `font-family` applied, ensuring that custom fonts are loaded and applied correctly.
*   **Test Case 3: Verify Python worker loading.**
    *   **Description:** Add a test that specifically checks for the successful loading of the `python.worker.ts` file to ensure the Pyodide environment is initialized correctly.

## 6. Shipping Blockers

There are **no critical shipping blockers** for the GitHub Pages deployment. The existing configuration is sound and the E2E tests provide good coverage for the most critical parts of the application. The identified gaps are limitations or areas for improvement rather than critical defects.
