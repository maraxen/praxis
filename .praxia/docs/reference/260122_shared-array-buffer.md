# Known Issue: SharedArrayBuffer is not defined

## Issue Description

When running Praxis in **Browser Mode** (using Pyodide), you may encounter the following error in the browser console:
`python.worker.ts:17 Uncaught ReferenceError: SharedArrayBuffer is not defined`

## Cause

`SharedArrayBuffer` is required by Pyodide for certain features, including multi-threading and efficient memory sharing between the main thread and the worker. For security reasons (to mitigate Spectre-like attacks), modern browsers only enable `SharedArrayBuffer` if the page is in a "cross-origin isolated" state.

This state requires two specific HTTP response headers to be set:

1. `Cross-Origin-Opener-Policy: same-origin`
2. `Cross-Origin-Embedder-Policy: require-corp`

## Impact

- **Python Worker Internal Communication**: The initialization of the Pyodide worker may fail or be restricted.
- **Performance**: Without `SharedArrayBuffer`, certain operations in the browser-native environment may be significantly slower or fail to execute if they depend on shared memory.

## Resolution

### 1. Development Environment (Angular Dev Server)

The `angular.json` should be updated to include these headers automatically for the dev server.

**Example configuration in `angular.json`:**

```json
"serve": {
  "options": {
    "headers": {
      "Cross-Origin-Opener-Policy": "same-origin",
      "Cross-Origin-Embedder-Policy": "require-corp"
    }
  }
}
```

### 2. Production Environment

If you are deploying Praxis (e.g., to GitHub Pages or a custom server), you must ensure your web server sends these headers.

#### GitHub Pages / Netlify / Static Hosting

GitHub Pages does not support custom headers natively. You can use a service worker workaround such as [coi-serviceworker](https://github.com/gzuidhof/coi-serviceworker) to enable cross-origin isolation.

#### Nginx

Add the following to your server block:

```nginx
add_header Cross-Origin-Opener-Policy same-origin;
add_header Cross-Origin-Embedder-Policy require-corp;
```

#### Apache

Add the following to your `.htaccess` or server config:

```apache
<IfModule mod_headers.c>
    Header set Cross-Origin-Opener-Policy "same-origin"
    Header set Cross-Origin-Embedder-Policy "require-corp"
</IfModule>
```

### 3. Fallback (Non-SAB Environments)

If headers cannot be set, Pyodide may attempt to run in a single-threaded mode, but this can lead to responsiveness issues in the main thread (UI blocking) and is not the recommended configuration for Praxis.
