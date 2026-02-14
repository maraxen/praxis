
import pytest
import pytest_asyncio
import os
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

# Ensure we set this before importing modules that might read it (though imports might already cache it)
os.environ["TEST_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from praxis.backend.main import app
import praxis.backend.main as main_module
from praxis.backend.utils.db import Base
import praxis.backend.utils.db as db_utils
import praxis.backend.api.dependencies as dependencies_module

# Use in-memory SQLite for these tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Function-scoped database engine for SQLite in-memory."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Initialize DB schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # PATCHING: Ensure app uses this engine (crucial for lifespan)
    # 1. Set app state
    app.state.async_engine = engine
    
    # 2. Patch module level references used for cleanup/dispose in main.py
    original_main_engine = main_module.praxis_async_engine
    main_module.praxis_async_engine = engine
    
    # 3. Patch utils engine
    db_utils.async_engine = engine
    
    yield engine
    
    # Cleanup
    main_module.praxis_async_engine = original_main_engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Function-scoped database session with rollback and comprehensive app patching."""
    # Connect and begin transaction
    async with db_engine.connect() as connection:
        async with connection.begin() as transaction:
            # Create the session to return to the test
            session = AsyncSession(bind=connection, expire_on_commit=False)
            
            # Create a patched factory bound to this specific connection
            # This is critical for SQLite in-memory to share the state
            patched_factory = async_sessionmaker(
                bind=connection,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False
            )
            
            # Save original factories
            original_utils_factory = db_utils.AsyncSessionLocal
            original_main_factory = main_module.AsyncSessionLocal
            original_deps_factory = dependencies_module.AsyncSessionLocal
            
            # Apply patches to ALL known locations where AsyncSessionLocal is imported
            db_utils.AsyncSessionLocal = patched_factory
            main_module.AsyncSessionLocal = patched_factory
            dependencies_module.AsyncSessionLocal = patched_factory

            try:
                yield session
            finally:
                # Restore original factories
                db_utils.AsyncSessionLocal = original_utils_factory
                main_module.AsyncSessionLocal = original_main_factory
                dependencies_module.AsyncSessionLocal = original_deps_factory
                
                await session.close()
                await transaction.rollback()

@pytest_asyncio.fixture(scope="function")
async def client(db) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient fixture that relies on the patched db."""
    # The 'db' fixture is requested to ensure patching is active during client usage
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c
