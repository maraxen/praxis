---
title: 'Reconnaissance Report: .gitignore Audit'
---

# Reconnaissance Report: .gitignore Audit

## 1. Executive Summary

This report provides a detailed audit of the repository's `.gitignore` files and version control practices. The analysis indicates that while the existing `.gitignore` files provide a decent baseline for a Python and Node.js project, there are several critical issues that need to be addressed. Key problems include a large vendored dependency, tracked binary files, local database files, and screenshots from E2E tests.

This report recommends updating the `.gitignore` files to exclude these problematic files and removing them from the Git history to reduce the repository's size and improve its health.

## 2. Current `.gitignore` Pattern Analysis

The repository contains two `.gitignore` files: one at the root and another in `praxis/web-client`.

*   **Root `.gitignore`:** The root `.gitignore` file contains a comprehensive set of rules for a typical Python project, covering common artifacts such as `__pycache__`, `*.pyc`, virtual environment directories, and build outputs. It also includes patterns for common tools like `pytest`, `mypy`, and `ruff`.
*   **`praxis/web-client/.gitignore`:** The `.gitignore` file in the web client's subdirectory is well-configured for a standard Angular project. It correctly ignores `node_modules`, build artifacts, and editor-specific files.

Overall, the existing patterns are well-structured and provide a solid foundation. However, there are some gaps and improperly tracked files that need to be addressed.

## 3. Problematic Tracked Files

The following files are currently tracked in the repository but should be ignored:

*   **`external/pylabrobot` (105M):** This directory appears to be a vendored copy of the `pylabrobot` library. It is the largest single item in the repository and should not be tracked in version control. Instead, it should be managed as a dependency, for example, by referencing it as a Git submodule or installing it via a package manager.
*   **`.agent/scripts/jules-diff-tool/jules-diff-tool` (3.2M):** This is a large, compiled binary file. Binary executables should not be tracked in Git. This tool should be built from source as part of a development setup process or downloaded from a release artifact.
*   **`praxis.db` and `praxis/web-client/src/assets/db/praxis.db` (832K and 884K):** These appear to be SQLite database files. Local database files should not be version-controlled, as they are specific to a local development environment and can change frequently.
*   **E2E Screenshots:** The `praxis/web-client/e2e/screenshots` directory contains numerous PNG files that appear to be screenshots from Playwright E2E tests. These are test artifacts and should not be committed to the repository.

## 4. Missing `.gitignore` Patterns

The following patterns are missing from the `.gitignore` files:

*   **`*.db`:** There is no global pattern to ignore database files. This would prevent files like `praxis.db` from being accidentally committed.
*   **`praxis/web-client/e2e/screenshots/`:** The root `.gitignore` file attempts to ignore `praxis/web-client/e2e/screenshot/` (singular), but the actual directory is `screenshots` (plural). This typo means the rule is not effective.

## 5. Recommended `.gitignore` Updates

To address the issues identified in this report, I recommend the following changes:

1.  **Add to root `.gitignore`:**
    *   Add `*.db` to ignore all database files.
    *   Add `external/` to ignore the vendored `pylabrobot` dependency.
    *   Add `.agent/scripts/jules-diff-tool/jules-diff-tool` to ignore the binary tool.
    *   Correct the typo in the screenshot directory pattern to `praxis/web-client/e2e/screenshots/`.

2.  **Remove problematic files from Git history:**
    *   Simply adding these files to `.gitignore` will not remove them from the repository's history. To completely remove them, you will need to use a tool like `git-filter-repo` or the BFG Repo-Cleaner. This is a destructive operation that will rewrite the repository's history, so it should be done with caution.

By implementing these recommendations, you will significantly reduce the size of the repository, improve its overall health, and prevent environment-specific files from being shared among developers.
