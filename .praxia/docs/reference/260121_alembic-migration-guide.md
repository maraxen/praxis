---
title: 'Alembic Migration Workflow Guide'
---

# Alembic Migration Workflow Guide

## Quick Reference

A summary of the most common commands for managing migrations.

### Alembic Commands

All Alembic commands should be run from the root of the repository.

- **Create a New Blank Migration**:
  ```bash
  uv run alembic revision -m "short_description_of_changes"
  ```

- **Run Migrations (Upgrade)**:
  ```bash
  # Upgrade to the latest version
  uv run alembic upgrade head
  ```

- **Revert Migrations (Downgrade)**:
  ```bash
  # Downgrade by one revision
  uv run alembic downgrade -1

  # Downgrade to the base (no migrations applied)
  uv run alembic downgrade base
  ```

- **View Migration Status**:
  ```bash
  # Show the current revision
  uv run alembic current

  # Show the full history
  uv run alembic history
  ```

### Test Database

To run migrations locally or use the `autogenerate` feature, you need a running PostgreSQL database.

- **Start the Test Database**:
  ```bash
  sudo docker-compose -f docker-compose.test.yml up -d
  ```

- **Stop the Test Database**:
  ```bash
  sudo docker-compose -f docker-compose.test.yml down
  ```
