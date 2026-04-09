"""Alembic environment configuration — async engine mode.

This env.py uses the async engine pattern (``run_async_migrations``) so
that it is fully compatible with the project's ``asyncpg`` / SQLAlchemy
async stack.  The target metadata is loaded from
``infrastructure.database.models`` which imports *all* models so that
``Base.metadata`` is fully populated before autogenerate inspects it.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# ---------------------------------------------------------------------------
# Load Alembic's logging config (from alembic.ini)
# ---------------------------------------------------------------------------
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import all models so Base.metadata is fully populated.
# ``import infrastructure.database.models`` triggers all model imports via
# the package's __init__.py which re-exports every model class.
# ---------------------------------------------------------------------------
import infrastructure.database.models  # noqa: F401  — side-effect import
from infrastructure.database.base import Base
from infrastructure.config import settings

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Inject the async DATABASE_URL from application settings.
# This overrides the blank ``sqlalchemy.url`` in alembic.ini.
# ---------------------------------------------------------------------------
config.set_main_option("sqlalchemy.url", settings.database_url)


# ---------------------------------------------------------------------------
# Helper: run migrations in "offline" mode (no live DB connection).
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations without a real DB connection.

    Emits the SQL to stdout so it can be inspected or piped to a file.
    Useful for generating a migration script without a running Postgres.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Helper: run migrations synchronously via a real async connection.
# ---------------------------------------------------------------------------


def do_run_migrations(connection: Connection) -> None:
    """Configure the migration context and execute pending revisions."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run all pending migrations inside it."""
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),  # type: ignore[arg-type]
        poolclass=pool.NullPool,  # avoid keeping connections open
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online mode — delegates to the async runner."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Dispatch: Alembic calls this module at the module level.
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
