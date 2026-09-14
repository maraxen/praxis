"""Test configuration and fixtures.

This module patches `asyncio.run` to be safe when tests run under an
already-running event loop (pytest-asyncio / anyio). It falls back to the
project's `run_sync` helper when `asyncio.run` would raise a RuntimeError.
"""

from __future__ import annotations

import asyncio
import typing

from praxis.backend.utils.async_run import run_sync

_orig_asyncio_run = asyncio.run


def _safe_asyncio_run(coro: typing.Coroutine) -> typing.Any:
  try:
    return _orig_asyncio_run(coro)
  except RuntimeError as e:  # pragma: no cover - fallback path in test harness
    if "cannot be called from a running event loop" not in str(e):
      raise
    return run_sync(coro)


# Patch at import time so all tests benefit.
asyncio.run = _safe_asyncio_run
import contextlib
import os
import subprocess
import time
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio

try:
  import nest_asyncio

  nest_asyncio.apply()
except Exception:
  # If nest_asyncio isn't available, continue without applying.
  pass
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
  AsyncSession,
  create_async_engine,
)
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.pool import NullPool, StaticPool
from sqlmodel import SQLModel

from praxis.backend.utils.db import Base
from tests.factories import (
  FunctionCallLogFactory,
  FunctionDataOutputFactory,
  FunctionProtocolDefinitionFactory,
  MachineFactory,
  ProtocolRunFactory,
  ResourceDefinitionFactory,
  ResourceFactory,
  WellDataOutputFactory,
  WorkcellFactory,
)


@pytest.fixture(scope="session")
def event_loop():
  """Create an instance of the default event loop for each test case."""
  loop = asyncio.get_event_loop_policy().new_event_loop()
  yield loop
  loop.close()


# Dual Database Testing Support
# =============================
# Tests can run against either SQLite or PostgreSQL based on environment configuration.
# - SQLite: Fast, in-memory, no Docker required. Good for local development and quick CI.
# - PostgreSQL: Production-like, tests JSONB indexing and PostgreSQL-specific features.
#
# The application uses JsonVariant which automatically uses JSONB on PostgreSQL
# and falls back to standard JSON on SQLite.
#
# Configuration:
# - TEST_DATABASE_URL: Set to a PostgreSQL connection string for PostgreSQL testing
# - TEST_DB_TYPE=sqlite: Force SQLite mode (or omit TEST_DATABASE_URL)
#
# Examples:
#   SQLite (default):     TEST_DB_TYPE=sqlite pytest
#   PostgreSQL:           TEST_DATABASE_URL=postgresql+asyncpg://... pytest

TEST_DB_TYPE = os.getenv("TEST_DB_TYPE", "").lower()

if TEST_DB_TYPE == "sqlite" or (
  not os.getenv("TEST_DATABASE_URL") and TEST_DB_TYPE != "postgresql"
):
  # SQLite mode - fast, in-memory testing
  TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
  USE_SQLITE = True
else:
  # PostgreSQL mode - production-like testing
  TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test_user:test_password@127.0.0.1:5433/test_db",
  )
  USE_SQLITE = False


def pytest_configure(config):
  """Register custom pytest markers for database-specific tests."""
  config.addinivalue_line("markers", "postgresql_only: mark test to run only on PostgreSQL")
  config.addinivalue_line("markers", "sqlite_only: mark test to run only on SQLite")
  config.addinivalue_line(
    "markers", "slow: mark test as slow so it can be excluded from default runs"
  )


def pytest_collection_modifyitems(config, items):
  """Skip tests based on database type markers."""
  skip_postgresql = pytest.mark.skip(reason="Test requires PostgreSQL, running on SQLite")
  skip_sqlite = pytest.mark.skip(reason="Test requires SQLite, running on PostgreSQL")

  for item in items:
    if "postgresql_only" in item.keywords and USE_SQLITE:
      item.add_marker(skip_postgresql)
    elif "sqlite_only" in item.keywords and not USE_SQLITE:
      item.add_marker(skip_sqlite)


def pytest_report_header(config):
  """Add database type to pytest header output."""
  db_type = (
    "SQLite (in-memory)"
    if USE_SQLITE
    else f"PostgreSQL ({TEST_DATABASE_URL.split('@')[-1].split('/')[0]})"
  )
  return [f"Database: {db_type}"]


@pytest.fixture(scope="session")
def db_type():
  """Fixture to access the current database type in tests.

  Returns:
      str: 'sqlite' or 'postgresql'

  """
  return "sqlite" if USE_SQLITE else "postgresql"


@pytest.fixture(scope="session", autouse=True)
def docker_db(worker_id):
  """Starts the test database container before running tests and stops it afterwards.

  This fixture is session-scoped and autouse, so it runs automatically.

  When using pytest-xdist, only the master process manages the Docker container.
  Worker processes skip this fixture and connect to the existing database.

  When using SQLite mode, this fixture is a no-op since no Docker is needed.
  """
  # Skip Docker management when using SQLite
  if USE_SQLITE:
    yield
    return

  # Only run docker operations on the main worker or if not using xdist
  # worker_id is "master" when not using xdist or on the coordinator process
  if worker_id != "master":
    # We're a worker process - the master already started the DB
    yield
    return

  docker_compose_file = "docker-compose.test.yml"

  # Check if docker-compose file exists
  if not os.path.exists(docker_compose_file):
    yield
    return

  # Start the DB
  try:
    subprocess.run(
      ["docker", "compose", "-f", docker_compose_file, "up", "-d", "test_db"],
      check=True,
      capture_output=True,
    )
  except subprocess.CalledProcessError:
    yield
    return

  # Wait for DB to be healthy
  max_retries = 30
  ready = False
  for _ in range(max_retries):
    try:
      # Check container health
      # Using 'wait' command if available is better, but 'up -d --wait' is cleaner if supported.
      # Re-running up with wait
      subprocess.run(
        ["docker", "compose", "-f", docker_compose_file, "up", "-d", "--wait", "test_db"],
        check=True,
        capture_output=True,
        timeout=2,
      )
      ready = True
      break
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
      time.sleep(1)

  if not ready:
    pass

  yield

  subprocess.run(
    ["docker", "compose", "-f", docker_compose_file, "down"], check=False, capture_output=True
  )


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
  """Creates a session-scoped test database engine.

  Session scope creates the database once for all tests, significantly
  speeding up test execution. Individual tests use transaction rollback
  to maintain isolation.

  Database-specific behavior:
  - SQLite: Uses StaticPool to maintain a single connection for in-memory DB.
            No enum type cleanup needed as SQLite stores enums as strings.
  - PostgreSQL: Uses NullPool for proper connection management.
                Drops enum types to prevent persistence errors between runs.
  """
  if USE_SQLITE:
    # SQLite in-memory requires StaticPool to maintain the same connection
    # across the entire test session, otherwise tables are lost
    engine = create_async_engine(
      TEST_DATABASE_URL,
      echo=False,
      poolclass=StaticPool,
      connect_args={"check_same_thread": False},
    )
  else:
    # PostgreSQL uses NullPool for proper connection cleanup
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)

  async with engine.begin() as conn:
    if not USE_SQLITE:
      # PostgreSQL-specific: Clean up enum types that persist across test runs
      # This prevents "type already exists" errors
      await conn.execute(text("DROP TYPE IF EXISTS assettype CASCADE"))

    # Drop and recreate all tables for a clean slate
    with contextlib.suppress(Exception):
      await conn.run_sync(Base.metadata.drop_all)
    await conn.run_sync(Base.metadata.create_all)
    await conn.run_sync(SQLModel.metadata.create_all)

  yield engine

  # Cleanup: drop all tables after session
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.drop_all)

  await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(
  db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
  """Yields a single, transacted session for one test function.
  The transaction is rolled back after the test completes.

  Uses connection-level transactions to ensure proper rollback.
  This is a performance optimization: the database schema is created
  once per session (in db_engine), and each test gets a clean slate
  via transaction rollback instead of recreating tables.
  """
  async with db_engine.connect() as connection, connection.begin() as transaction:
    # Create session bound to this connection
    session = AsyncSession(bind=connection, expire_on_commit=False)

    # Set up factories to use this session
    WorkcellFactory._meta.sqlalchemy_session = session
    MachineFactory._meta.sqlalchemy_session = session
    ResourceDefinitionFactory._meta.sqlalchemy_session = session
    ResourceFactory._meta.sqlalchemy_session = session
    FunctionProtocolDefinitionFactory._meta.sqlalchemy_session = session
    ProtocolRunFactory._meta.sqlalchemy_session = session
    FunctionCallLogFactory._meta.sqlalchemy_session = session
    FunctionDataOutputFactory._meta.sqlalchemy_session = session
    WellDataOutputFactory._meta.sqlalchemy_session = session

    try:
      yield session
    finally:
      # Clean up session and transaction
      # Catch all errors to prevent test failures from cleanup operations
      with contextlib.suppress(Exception):
        session.expunge_all()

      with contextlib.suppress(Exception):
        await session.close()

      # Rollback transaction, catching circular dependency errors
      # These can occur when tests delete objects with complex cascade relationships
      try:
        await transaction.rollback()
      except Exception:
        # Ignore rollback errors - transaction will be cleaned up when connection closes
        pass


# ============================================================================
# Auth Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
  """Create active test user with known password for auth testing.

  Username: testuser
  Password: testpass123
  Email: testuser@example.com
  Active: True
  """
  from praxis.backend.models.domain.user import UserCreate
  from praxis.backend.services.user import UserService

  user_service = UserService(db_session)
  user_data = UserCreate(
    username="testuser",
    email="testuser@example.com",
    password="testpass123",
    is_active=True,
  )
  user = await user_service.create(db=db_session, obj_in=user_data)
  await db_session.commit()
  await db_session.refresh(user)
  return user


@pytest_asyncio.fixture
async def test_inactive_user(db_session: AsyncSession):
  """Create inactive test user for rejection testing.

  Username: inactiveuser
  Password: testpass123
  Email: inactive@example.com
  Active: False
  """
  from praxis.backend.models.domain.user import UserCreate
  from praxis.backend.services.user import UserService

  user_service = UserService(db_session)
  user_data = UserCreate(
    username="inactiveuser",
    email="inactive@example.com",
    password="testpass123",
    is_active=False,
  )
  user = await user_service.create(db=db_session, obj_in=user_data)
  await db_session.commit()
  await db_session.refresh(user)
  return user


@pytest.fixture
def valid_auth_headers(test_user):
  """Generate valid Authorization headers for test_user.

  Returns:
      dict: {"Authorization": "Bearer <token>"}

  """
  from praxis.backend.utils.auth import create_access_token

  token = create_access_token(
    data={"sub": test_user.username, "user_id": str(test_user.accession_id)}
  )
  return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def expired_token(test_user):
  """Generate expired token for testing expiration handling.

  Creates a token that expired 1 second ago.

  Returns:
      str: Expired JWT token

  """
  from datetime import timedelta

  from praxis.backend.utils.auth import create_access_token

  return create_access_token(
    data={"sub": test_user.username, "user_id": str(test_user.accession_id)},
    expires_delta=timedelta(seconds=-1),
  )
