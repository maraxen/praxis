---
title: 'Technology Stack: PyLabPraxis'
---

# Technology Stack: PyLabPraxis

## Backend
*   **Language:** Python 3.12+
*   **Framework:** FastAPI (High-performance REST API)
*   **Task Orchestration:** Celery (Asynchronous task execution and scheduling)
*   **Message Broker & State Store:** Redis (Broker for Celery and fast state management via `PraxisState`)
*   **Database:** PostgreSQL (Persistent relational data storage for protocols, assets, and metadata)
*   **ORM/Database Toolkit:** SQLAlchemy 2.0+ & Alembic (Migrations)
*   **Hardware Interface:** PyLabRobot (PLR) - Core library for lab automation hardware interaction

## Frontend
*   **Language:** TypeScript
*   **Framework:** Angular (Standalone components, Signals-based state management)
*   **Styling:** Modern CSS/SCSS with a focus on Material Design principles

## Identity & Security
*   **Identity Provider:** Keycloak (Integrated for Role-Based Access Control (RBAC) and identity management)

## Infrastructure & DevOps
*   **Containerization:** Docker & Docker Compose
*   **Process Management:** Celery Workers for background protocol execution

## Quality Assurance
*   **Backend Testing:** Pytest (Unit and integration tests)
*   **Static Type Checking:** ty (Advanced static analysis for Python)
*   **Frontend Testing:** Playwright (End-to-end and component testing)
*   **Linting & Formatting:** Ruff (Python), Prettier/ESLint (Angular)
