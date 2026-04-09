"""Async database engine and session factory."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from infrastructure.config import settings

# ---------------------------------------------------------------------------
# Engine — created once per process; shared across all sessions.
# ---------------------------------------------------------------------------

_engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=settings.app_env == "development",
    pool_pre_ping=True,
)

# ---------------------------------------------------------------------------
# Session factory — use this to open individual database sessions.
# ---------------------------------------------------------------------------

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Dependency-injectable session generator (e.g. for FastAPI Depends).
# ---------------------------------------------------------------------------


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an ``AsyncSession`` and close it automatically on exit.

    Usage (FastAPI)::

        async def my_endpoint(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with async_session_factory() as session:
        yield session


def get_engine() -> AsyncEngine:
    """Return the shared async engine (useful for testing / Alembic)."""
    return _engine
