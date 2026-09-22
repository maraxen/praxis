# Docs 404 Investigation

## Problem Summary

The application displays a "404 Not Found" Snackbar error when navigating to documentation pages like "Quickstart".

**Error**: `Http failure response for /assets/docs/getting-started/quickstart-production.md: 404`

## Root Cause

1. **Speculative Loading**: `DocsPageComponent` defaults to `production` mode and attempts to load a mode-specific markdown file first (e.g., `quickstart-production.md`) before falling back to the generic file (`quickstart.md`).
2. **Global Error Handling**: The `ErrorInterceptor` intercepts *all* HTTP errors, including these expected 404s from the speculative load. It displays a user-facing Snackbar notification immediately, regardless of whether the component handles the error later.
3. **Missing Files**: Most documentation files do NOT have a `*-production.md` variant, making this 404 a common occurrence.

## Affected Paths

The following files are requested but rarely exist (only those marked `[EXISTS]` were found). All others trigger 404s.

### Getting Started

- `quickstart-production.md` (Missing)
- `browser-mode-production.md` (Missing)
- `browser-script-production.md` (Missing)
- `installation-production.md` **[EXISTS]**

### Architecture

- `overview-production.md` **[EXISTS]**
- `backend-production.md` **[EXISTS]**
- `frontend-production.md` (Missing)
- `execution-flow-production.md` (Missing)
- `state-management-production.md` (Missing)
- `simulation-production.md` (Missing)

### User Guide, Development, Reference, API

- All files in these sections generally lack a `-production.md` variant and trigger 404s.

## Recommendations

### Recommended Fix: HttpContext Suppression

Instead of creating dozens of duplicate `*-production.md` files, we should modify the error handling logic to support "silent" 404s.

1. **Update `ErrorInterceptor`**:
    Add code to check for an `HttpContextToken` (e.g., `SKIP_ERROR_HANDLING`). If present, return the error to the caller without showing the Snackbar.

    ```typescript
    // core/http/http-context.tokens.ts
    export const SKIP_ERROR_HANDLING = new HttpContextToken<boolean>(() => false);

    // core/http/error.interceptor.ts
    if (req.context.get(SKIP_ERROR_HANDLING)) {
        return next(req);
    }
    ```

2. **Update `DocsPageComponent`**:
    Pass this context when making the speculative requests.

    ```typescript
    // features/docs/components/docs-page.component.ts
    this.http.get(modePath, { 
        responseType: 'text',
        context: new HttpContext().set(SKIP_ERROR_HANDLING, true)
    })
    ```

This approach maintains the useful mode-switching capability while eliminating the false-positive error notifications.
