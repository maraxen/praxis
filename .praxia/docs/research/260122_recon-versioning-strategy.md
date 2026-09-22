---
title: 'Reconnaissance Report: Versioning Strategy and Roadmap'
---

# Reconnaissance Report: Versioning Strategy and Roadmap

## 1. Current State Summary

- **Current Version**: `0.0.1` (as per `pyproject.toml`)
- **Roadmap Documents**: 
    - `ROADMAP.md`: Outlines long-term strategic goals such as a plugin marketplace, local NLP, and DAG optimization.
    - `POST_SHIP.md`: Details immediate priorities for the v0.1-Alpha+ release, focusing on a robust database and schema generation pipeline.
- **Inconsistencies**: The project has two separate roadmap documents, which could lead to confusion.

## 2. Recommended Versioning Scheme

We recommend adopting the **Semantic Versioning (SemVer)** specification (`MAJOR.MINOR.PATCH`).

- **`MAJOR`**: Incremented for incompatible API changes.
- **`MINOR`**: Incremented for adding functionality in a backward-compatible manner.
- **`PATCH`**: Incremented for backward-compatible bug fixes.

For the initial development phase (i.e., `0.x.x`):

- The API should be considered unstable.
- **`0.MINOR.PATCH`**: Minor versions will be used for new features and breaking changes, and patch versions for bug fixes.
- **Pre-release tags**: Use tags like `-alpha`, `-beta`, and `-rc` to denote the stability of a release (e.g., `0.1.0-alpha.1`).

## 3. Milestone Proposal

- **v0.1 (Alpha Release)**:
    - **Focus**: Initial stabilization and core functionality.
    - **Features**:
        - Robust database and schema generation pipeline (`POST_SHIP.md`).
        - Basic protocol execution.
        - Core UI/UX for defining and running protocols.

- **v0.2 (Beta Release)**:
    - **Focus**: Feature expansion and API refinement.
    - **Features**:
        - Initial implementation of the DAG optimization for protocol execution (`ROADMAP.md`).
        - Begin work on the plugin and definition marketplace infrastructure (`ROADMAP.md`).
        - UI/UX polish based on feedback from the alpha release.

- **v1.0 (Stable Release)**:
    - **Focus**: Public API stability and feature completeness.
    - **Features**:
        - Stable and well-documented API for protocol execution and third-party integrations.
        - A functional plugin and definition marketplace with a vetted database of definitions (`ROADMAP.md`).
        - Integration of local NLP for protocol generation (`ROADMAP.md`).

## 4. Release Cadence Recommendation

- **Minor Releases (e.g., 0.1, 0.2)**: Monthly release cycle.
- **Patch Releases (e.g., 0.1.1, 0.1.2)**: As needed for bug fixes and security patches.
- **Pre-releases (e.g., 0.1.0-alpha.1)**: Weekly or bi-weekly for continuous testing.

## 5. Roadmap Consolidation Suggestions

To improve clarity and reduce confusion, we recommend consolidating `ROADMAP.md` and `POST_SHIP.md` into a single, unified `ROADMAP.md` file. This file should be structured to show the long-term vision, as well as the immediate and near-term priorities.
