---
title: 'Root Markdown Files Audit Report'
---

# Root Markdown Files Audit Report

This report provides an audit of the root-level markdown files in the repository.

## 1. File-by-File Status

*   **`README.md`**:
    *   **Status**: Mostly up-to-date.
    *   **Content**: Provides a good overview of the project, its architecture, and key features.
    *   **Issues**: Contains links to the documentation website. These links should be verified to ensure they are not broken.

*   **`CONTRIBUTING.md`**:
    *   **Status**: Appears current.
    *   **Content**: Details the development workflow, testing, and documentation standards.
    *   **Issues**: It references `make` commands (`make test`, `make lint`, `make typecheck`, `make docs`). The `README.md` suggests `uv run` commands for similar tasks. This is a consistency issue that needs to be resolved.

*   **`LICENSE.md`**:
    *   **Status**: OK.
    *   **Content**: Standard MIT License.
    *   **Issues**: None.

*   **`ROADMAP.md`**:
    *   **Status**: OK.
    *   **Content**: High-level, long-term strategic goals.
    *   **Issues**: Cross-references `POST_SHIP.md`. This link is correct.

*   **`RUNWAY.md`**:
    *   **Status**: Outdated.
    *   **Content**: A checklist for renaming the repository from `pylabpraxis` to `praxis`. This action appears to have been completed.
    *   **Issues**: This file is no longer relevant and can be archived or deleted.

*   **`POST_SHIP.md`**:
    *   **Status**: Appears current.
    *   **Content**: Outlines tasks and architectural improvements after the initial alpha release.
    *   **Issues**: Seems well-structured. No immediate issues.

*   **`TECHNICAL_DEBT.md`**:
    *   **Status**: Appears current and actively used.
    *   **Content**: A living document tracking known issues and missing features.
    *   **Issues**: This is a valuable document for developers. No immediate issues.

## 2. Cross-Reference Issues

*   **`README.md` -> `CONTRIBUTING.md` / `AGENTS.md`**: Links are correct.
*   **`README.md` -> `docs/*`**: The `README` links to several documents in the `docs/` directory. These links should be programmatically checked for validity.
*   **`CONTRIBUTING.md` -> `docs/installation.md`**: This link should also be verified.
*   **`ROADMAP.md` -> `POST_SHIP.md`**: Link is correct.

The main cross-reference issue is the consistency between the commands recommended in `README.md` (`uv run ...`) and `CONTRIBUTING.md` (`make ...`).

## 3. Outdated Content

*   The most significant piece of outdated content is the entire `RUNWAY.md` file, which documents a completed repository rename.
*   The `CONTRIBUTING.md` file might be partially outdated if the `Makefile` is deprecated in favor of direct `uv` commands.

## 4. Consolidation Recommendations

*   **`ROADMAP.md`**, **`POST_SHIP.md`**, and **`TECHNICAL_DEBT.md`**: These three files cover similar themes (future work, improvements, issues).
    *   `ROADMAP.md` is for high-level, long-term vision.
    *   `POST_SHIP.md` is for near-term, post-release tasks.
    *   `TECHNICAL_DEBT.md` is for specific, known issues.
    *   **Recommendation**: The distinction is logical, but could be confusing. Consider merging `POST_SHIP.md` into `TECHNICAL_DEBT.md` or into a more granular project board/issue tracker. For now, adding a sentence at the top of each file explaining its specific scope and linking to the others would improve clarity. For example, in `ROADMAP.md`: "For more immediate post-release plans, see [POST_SHIP.md](./POST_SHIP.md). For a list of known issues and smaller-scale improvements, see [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md)."

## 5. Update Priorities

1.  **High Priority**:
    *   **Archive or Delete `RUNWAY.md`**: This file is no longer relevant. Archiving it (e.g., moving to `.agent/archive/`) is a safe option.
    *   **Resolve Command Inconsistency**: Update `CONTRIBUTING.md` to use the same `uv run` commands as `README.md` for linting, testing, and type-checking, assuming `uv` is the canonical tool. Verify this against the project's tooling setup.

2.  **Medium Priority**:
    *   **Verify Documentation Links**: Run a link checker to validate all external and internal links in `README.md` and `CONTRIBUTING.md`.
    *   **Clarify Scope of Roadmap Files**: Add cross-linking sentences to `ROADMAP.md`, `POST_SHIP.md`, and `TECHNICAL_DEBT.md` to clarify their distinct purposes as recommended above.

3.  **Low Priority**:
    *   **Consolidation**: Consider the larger recommendation of merging `POST_SHIP.md` into a more comprehensive project management tool or document in the future. This is a bigger change and can be deferred.
