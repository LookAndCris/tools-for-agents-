"""Integration test fixtures — async engine, session, and per-test rollback.

## How isolation works

Each test gets a clean database state without dropping or recreating tables:

1. ``async_engine`` fixture: creates one engine for the whole integration
   session (module-scoped).  Tables are created via ``alembic upgrade head``
   before the session starts (see ``apply_migrations``).

2. ``db_connection`` fixture: opens a *single* connection and starts an outer
   transaction.  This connection is reused by every ``db_session`` within the
   same test so that nested savepoints work correctly.

3. ``db_session`` fixture: creates a savepoint *inside* the outer transaction.
   After the test body finishes the savepoint is rolled back, undoing all
   changes made during the test.  The outer transaction is rolled back when
   the test module finishes, giving a second clean-up layer.

This pattern is safe, fast, and compatible with SQLAlchemy 2.0 async.

## Requirements

A running PostgreSQL instance is needed.  Start one with::

    docker compose up -d db

The ``DATABASE_URL`` is read from ``infrastructure.config.settings`` which
honours a ``.env`` file at the project root.
"""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from infrastructure.config import settings

# ---------------------------------------------------------------------------
# Project root — used to locate alembic.ini
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# Migration bootstrap (session-scoped, runs once per pytest session)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def apply_migrations() -> None:  # type: ignore[return]
    """Run ``alembic upgrade head`` before integration tests start.

    This ensures the schema matches the current revision without requiring
    manual setup.  If alembic is not configured or the DB is not reachable the
    fixture will raise an error with a clear message.
    """
    result = subprocess.run(
        ["poetry", "run", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic upgrade head failed:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# Async engine (session-scoped — created once per pytest process)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def async_engine(apply_migrations: None) -> AsyncEngine:  # type: ignore[misc]
    """Return a session-scoped async engine connected to the test database.

    ``NullPool`` is used so connections are never held open between tests.
    ``apply_migrations`` is listed as a dependency to ensure the schema
    is up-to-date before any test opens a connection.
    """
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    yield engine
    await engine.dispose()


# ---------------------------------------------------------------------------
# Per-test connection with outer transaction (function-scoped)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_connection(async_engine: AsyncEngine) -> AsyncConnection:  # type: ignore[misc]
    """Open a connection and start an outer transaction.

    The outer transaction is rolled back after the test, regardless of what
    the test does.  This provides a second safety net on top of savepoints.
    """
    async with async_engine.connect() as conn:
        await conn.begin()
        yield conn
        await conn.rollback()


# ---------------------------------------------------------------------------
# Per-test session with savepoint isolation (function-scoped)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session(db_connection: AsyncConnection) -> AsyncSession:  # type: ignore[misc]
    """Yield an ``AsyncSession`` bound to the per-test savepoint.

    Pattern:
    - A savepoint is created inside the outer transaction.
    - The test runs against this savepoint.
    - After the test, the savepoint is rolled back — all mutations are undone.
    - The outer transaction (from ``db_connection``) is also rolled back.

    This guarantees each test sees a clean slate without DDL operations.
    """
    # Begin a nested (savepoint) transaction
    await db_connection.begin_nested()

    session = AsyncSession(
        bind=db_connection,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
        # Roll back to the savepoint — undoes everything done during the test
        await db_connection.rollback()
