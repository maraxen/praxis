---
title: 'RECON Report: Playwright Usage for Jules'
---

# RECON Report: Playwright Usage for Jules

This report documents the current Playwright setup in the `praxis/web-client` application and provides a recommended approach for Jules to run end-to-end tests.

## 1. Current Playwright Configuration Summary

The Playwright setup is configured in `praxis/web-client/playwright.config.ts`.

- **Configuration File**: `praxis/web-client/playwright.config.ts`
- **Test Directory**: `praxis/web-client/e2e/specs`
- **Web Server**: The configuration includes a `webServer` block that automatically starts the Angular development server using `npm run start:browser -- --port 4200` before running tests. The server runs on `http://localhost:4200`.
- **Browser**: The tests are configured to run against Chromium.
- **Reporter**: A simple `list` reporter is used for console output.
- **Parallelism**: Tests run in parallel by default, but this is disabled on CI (`workers: process.env.CI ? 1 : undefined`).

## 2. Jules Execution Requirements

As an AI agent, my execution environment has specific requirements:

- **Headless Mode**: All browser tests must run in headless mode, as there is no graphical user interface.
- **Self-Contained Commands**: The test command must be executable from the command line without manual intervention.
- **Server Management**: The command should handle starting and stopping the web application server automatically.
- **Dependency Management**: The process should rely on the project's existing dependencies.

## 3. Headless Mode Verification

The existing configuration is well-suited for my execution environment. The `playwright.config.ts` file explicitly enables headless mode in two places:

1.  In the global `use` block: `headless: true`
2.  In the `chromium` project configuration: `use: { ...devices['Desktop Chrome'], headless: true }`

This ensures that all tests will run without requiring a graphical interface, which is ideal.

## 4. Recommended Test Command for Jules

To execute the Playwright test suite, I should use the following command:

```bash
cd praxis/web-client && npx playwright test
```

**Rationale**:

- **Working Directory**: The command must be run from the `praxis/web-client` directory, as `playwright.config.ts` and `package.json` are located there.
- **`npx`**: Using `npx` ensures that the locally installed version of Playwright from `node_modules` is used, avoiding potential version conflicts.
- **`playwright test`**: This is the standard command to invoke the Playwright test runner, which will automatically use the `playwright.config.ts` file.

This single command handles starting the web server, running all tests in headless mode, and shutting down the server.

## 5. Known Issues & Gotchas

- **No npm Script**: There is no dedicated npm script (e.g., `npm run test:e2e`) in `package.json`. I must always use the full `npx playwright test` command.
- **Initial Browser Download**: The first time `npx playwright test` is run, it may take some time to download the necessary browser binaries. This is expected behavior.
- **Agent Skills (`.agent/skills`)**: The repository contains agent skills related to Playwright (`playwright-skill` and `webapp-testing`). While these provide general testing patterns, they are not tailored to this project's specific setup. **I should ignore these skills and use the project's native test command**, which is simpler and more reliable as it leverages the existing configuration.
