---
title: 'RECON - CHANGELOG.md Setup Research'
---

# RECON - CHANGELOG.md Setup Research

This report details the research and recommendations for establishing a `CHANGELOG.md` for the Praxis project.

## Recommended Format

It is recommended to adopt the **Keep a Changelog** format. This format is human-readable, well-structured, and has become a widely accepted standard. It organizes changes by version and categorizes them into sections:

- `Added` for new features.
- `Changed` for changes in existing functionality.
- `Deprecated` for soon-to-be-removed features.
- `Removed` for now-removed features.
- `Fixed` for any bug fixes.
- `Security` in case of vulnerabilities.

To support this, it is also recommended to adopt the **Conventional Commits** specification for all git commit messages. This will create a structured commit history that can be programmatically parsed to generate changelog entries.

## Integration Approach

1.  **Create `CHANGELOG.md`**: The `CHANGELOG.md` file should be created at the root of the repository.
2.  **Link from Documentation**: A link to the `CHANGELOG.md` file should be added to the main documentation navigation in `docs/index.md`. A new section, such as "Release History," would be appropriate.

## Automation Options

While direct Google searches for automation tools were unsuccessful during this reconnaissance, the use of Conventional Commits opens up the possibility of using popular and well-maintained tools to automate the changelog generation process. The following tools are known to work well for this purpose and should be investigated further:

-   **git-cliff**: A highly customizable changelog generator written in Rust.
-   **standard-version**: A tool for versioning using semver and CHANGELOG generation powered by Conventional Commits.

## Initial CHANGELOG.md Draft Outline

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
-

### Changed
-

### Fixed
-

## [v0.1-alpha] - YYYY-MM-DD

### Added
- Initial project setup.
- Core backend services for protocol management.
- Web client with basic UI for protocol listing and execution.
```

## v0.1-alpha Entry Draft

### [v0.1-alpha]

-   **Added**: Initial setup of the Praxis project, including the FastAPI backend, Angular web client, and core services for protocol discovery and execution.
-   **Added**: Support for PyLabRobot for hardware-agnostic protocol execution.
-   **Added**: Basic asset management for machines and resources.
-   **Added**: Real-time monitoring of protocol execution via WebSockets.
-   **Fixed**: Initial bug fixes related to database setup and migrations.
