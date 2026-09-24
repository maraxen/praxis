---
title: 'Documentation Reconnaissance Report'
---

# Documentation Reconnaissance Report

## 1. Broken Link Inventory

| File | Line | Link Text | Broken Link | Reason |
| --- | --- | --- | --- | --- |
| `docs/architecture/overview.md` | 3 | `Source` | `praxis/backend/core/protocols/orchestrator.py` | File does not exist. |
| `docs/user-guide/protocol-inference-sharp-bits.md` | 338 | `pylabrobot.protocol_analyzer` | `pylabrobot.protocol_analyzer` | Link is not a valid path. |

## 2. Outdated Content List

| File | Line(s) | Outdated Content | Reason | Priority |
| --- | --- | --- | --- | --- |
| `README.md` | 39 | `Asset Management Refactor (2025-12)` | The date is in the future. | Medium |
| `mkdocs.yml` | 99 | `Copyright &copy; 2025 Ovchinnikov Lab, MIT Biology` | The copyright year is in the future. | Medium |
| `praxis/web-client/src/assets/docs/` | - | Entire directory | This directory appears to be a duplicate of the `docs/` directory. This could lead to confusion and maintenance overhead. | High |

## 3. Accuracy Issues

| File | Line(s) | Inaccuracy | Suggested Fix | Priority |
| --- | --- | --- | --- | --- |
| `docs/getting-started/installation-production.md` | 27 | `docker compose up -d db redis` | The service names in `docker-compose.yml` are `praxis-db` and `redis`. | `docker compose up -d praxis-db redis` | High |
| `docs/getting-started/installation-production.md` | 38-43 | `.env` file | The application uses `praxis.ini` for configuration, not a `.env` file. | Replace `.env` instructions with `praxis.ini` instructions. | High |
| `docs/getting-started/quickstart.md` | 15 | `cd praxis/praxis/web-client` | Incorrect file path. | `cd praxis/web-client` | High |
| `docs/getting-started/quickstart.md` | 23 | `make db-test` | This command is not mentioned in the installation guide and is inconsistent with `docker compose`. | Replace with `docker compose up -d praxis-db redis`. | High |
| `docs/getting-started/quickstart.md` | 24 | `uvicorn praxis.backend.main:app --reload` | The `uvicorn` command is different from the one in `installation-production.md`. | Use `uvicorn main:app --reload --port 8000`. | High |
| `docs/architecture/backend.md` | 5 | Directory Structure Diagram | The diagram is missing. | Generate and add the diagram. | Medium |
| `docs/architecture/frontend.md` | 5 | Architecture Overview Diagram | The diagram is missing. | Generate and add the diagram. | Medium |
| `docs/development/contributing.md` | 23 | `make db-test` | Inconsistent with `docker compose`. | Replace with `docker compose up -d praxis-db redis`. | High |
| `docs/development/contributing.md` | 27 | `uvicorn praxis.backend.main:app --reload --port 8000` | The `uvicorn` command is different from the one in `quickstart.md`. | Use `uvicorn main:app --reload --port 8000`. | High |
| `docs/development/contributing.md` | 91 | `praxis/praxis/` | Incorrect file path in project structure. | Remove the extra `praxis/`. | High |
| `docs/development/testing.md` | 13 | `make db-test` | Inconsistent with `docker compose`. | Replace with `docker compose up -d praxis-db redis`. | High |
| `docs/development/testing.md` | 129 | `npm test -- --include=**/machine-list.component.spec.ts` | Incorrect command for running specific frontend tests. | Use `ng test --include=**/machine-list.component.spec.ts`. | Medium |
| `docs/reference/configuration.md` | 126 | `.env.example` | This file does not exist. | Create the file or remove the reference. | High |
| `docs/reference/configuration.md` | 91-124 | `docker-compose.yml` | The service names are incorrect. | Update the service names to match the actual `docker-compose.yml` file. | High |
| `docs/reference/cli-commands.md` | 7 | `make db-test` | Inconsistent with `docker compose`. | Replace with `docker compose up -d praxis-db redis`. | High |
| `docs/reference/cli-commands.md` | 12 | `uvicorn praxis.backend.main:app --reload --port 8000` | The `uvicorn` command is different from the one in `quickstart.md`. | Use `uvicorn main:app --reload --port 8000`. | High |
| `docs/reference/cli-commands.md` | 179 | `praxis/praxis/web-client` | Incorrect file path. | `praxis/web-client` | High |
| `docs/reference/troubleshooting.md` | 19 | `docker compose up -d db` | Incorrect service name. | `docker compose up -d praxis-db` | High |
| `docs/reference/troubleshooting.md` | 60 | `praxis/web-client/src/environments/environment.ts` | Incorrect file path. | `praxis/web-client/src/environments/environment.ts` | High |

## 4. Screenshot Audit

There are no screenshots in the documentation.

## 5. Update Priorities

1.  **High:** Address all accuracy issues, particularly those related to setup and installation, as they will prevent users from getting started. Remove the duplicate `praxis/web-client/src/assets/docs/` directory.
2.  **Medium:** Fix the broken links and outdated content. Generate the missing diagrams.
3.  **Low:** Add screenshots to the documentation to improve clarity.
