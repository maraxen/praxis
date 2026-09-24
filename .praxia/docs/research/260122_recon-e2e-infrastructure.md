---
title: 'RECON Report: E2E Test Infrastructure'
---

# RECON Report: E2E Test Infrastructure

This report details the findings of the reconnaissance mission to audit the Playwright E2E test infrastructure.

---

## 1. Configuration Verification Checklist

| Requirement | File | Current Setting | Status | Notes |
|---|---|---|---|---|
| Headless Execution | `playwright.config.ts` | `headless: true` | ✅ **Verified** | Configuration is correctly set for headless execution in CI/agent environments. |
| List Reporter | `playwright.config.ts` | `reporter: 'list'` | ✅ **Verified** | The reporter is correctly configured for clean, agent-friendly output. |
| Screenshot Capture | `playwright.config.ts` | `screenshot: 'only-on-failure'` | ❌ **Needs Remediation** | Screenshots are only captured on test failure. The requirement is to capture them on *all* runs for a complete visual record. |
| Output Directory | `playwright.config.ts` | `outputDir` is not set | ⚠️ **Recommendation** | Playwright defaults to `test-results`. It is recommended to explicitly set `outputDir: 'test-results/'` for clarity. |

---

## 2. Test Coverage Summary

The current E2E test suite consists of two main spec files:

- **`e2e/advanced-workflow.spec.ts`**: This test covers a critical and complex user path involving the execution of a protocol with advanced form fields. It effectively tests asset selection (autocomplete), single-select chips, and dynamic array inputs. API calls are mocked, indicating a focus on UI logic.
- **`e2e/playground.spec.ts`**: This test focuses on the interactive playground feature. It verifies terminal I/O (stdout/stderr), code completion popups, and signature help functionality.

The existing coverage is of good quality for the features it targets but is narrow in scope.

---

## 3. Gitignore Status

- **`test-results/`**: ❌ **Not Ignored**. The default Playwright output directory is not listed in `praxis/web-client/.gitignore`, which could lead to test artifacts being committed to the repository.
- **`__screenshots__/`**: ✅ **Ignored**. This directory is present in the gitignore file, suggesting it may have been used by a previous testing tool (e.g., Jest-Playwright or a manual setup).

---

## 4. Missing Tests for Critical Paths

The current test suite has significant gaps in coverage for core application functionality. The following critical paths are not currently tested:

1.  **Authentication Flow**: There are no tests for user login and logout. The existing tests bypass authentication by injecting a fake token into local storage.
2.  **Protocol Discovery and Selection**: The main dashboard for listing, searching, and selecting a protocol to run is untested.
3.  **Basic Protocol Run**: A simple "happy path" test for a protocol with basic input fields (text, numbers, booleans) is missing. This would complement the existing advanced workflow test.
4.  **Run Monitoring & Results**: There are no tests to verify the real-time updates on the run monitoring page (e.g., from WebSockets) or the display of final results and logs upon completion.
5.  **User Settings / Profile Management**: User-facing settings pages are untested.
6.  **Error Handling**: No tests cover UI behavior when APIs return errors (e.g., 4xx or 5xx status codes) or when users provide invalid input in forms.

---

## 5. Recommendations

1.  **Modify `playwright.config.ts`**:
    -   Change the `screenshot` option from `'only-on-failure'` to `'on'` to ensure visual artifacts are generated for every test run, which is valuable for CI/CD pipelines.
    -   Explicitly define `outputDir: 'test-results/'` to make the configuration clearer.

2.  **Update `.gitignore`**:
    -   Add `test-results/` to `praxis/web-client/.gitignore` to prevent test reports, traces, and screenshots from being committed.

3.  **Expand Test Coverage**:
    -   Prioritize creating new E2E tests for the identified critical paths, starting with the **authentication flow** and a **basic protocol run**.
    -   Develop a strategy for testing WebSocket-driven updates on the run monitoring page.

4.  **Create a `global.teardown.ts`**:
    -   Consider adding a global teardown file to perform cleanup actions after the test suite runs, if necessary.
