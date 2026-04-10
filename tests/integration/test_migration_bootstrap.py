"""Integration smoke tests — verifies migration bootstrap and session isolation.

These tests prove that:
1. ``alembic upgrade head`` created all 10 expected tables.
2. The savepoint-rollback isolation pattern works correctly:
   a. Data written in one test is not visible in the next.
   b. The session fixture yields a usable ``AsyncSession``.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from infrastructure.database.models.role import RoleModel


# ---------------------------------------------------------------------------
# 4.2 / 5.2 — migration tables exist
# ---------------------------------------------------------------------------

EXPECTED_TABLES = {
    "roles",
    "users",
    "staff_profiles",
    "client_profiles",
    "services",
    "staff_services",
    "staff_availability",
    "staff_time_off",
    "appointments",
    "appointment_events",
}


@pytest.mark.asyncio
async def test_all_expected_tables_exist(async_engine) -> None:
    """Verify that alembic upgrade head created all 10 tables."""
    async with async_engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
    table_set = set(tables)
    missing = EXPECTED_TABLES - table_set
    assert not missing, f"Missing tables after migration: {missing}"


# ---------------------------------------------------------------------------
# Waitlist migration tests (Task 2.1)
# ---------------------------------------------------------------------------

WAITLIST_TABLES = {"waitlist", "waitlist_notifications"}


@pytest.mark.asyncio
async def test_waitlist_tables_exist(async_engine) -> None:
    """Verify that the waitlist migration created both waitlist tables."""
    async with async_engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
    table_set = set(tables)
    missing = WAITLIST_TABLES - table_set
    assert not missing, f"Missing waitlist tables after migration: {missing}"


@pytest.mark.asyncio
async def test_waitlist_table_has_expected_columns(async_engine) -> None:
    """Verify the waitlist table has required columns."""
    async with async_engine.connect() as conn:
        columns = await conn.run_sync(
            lambda sync_conn: {
                col["name"] for col in inspect(sync_conn).get_columns("waitlist")
            }
        )
    expected = {"id", "client_id", "service_id", "status", "created_at"}
    assert expected.issubset(columns), f"Missing columns in waitlist: {expected - columns}"


@pytest.mark.asyncio
async def test_waitlist_notifications_table_has_expected_columns(async_engine) -> None:
    """Verify the waitlist_notifications table has required columns."""
    async with async_engine.connect() as conn:
        columns = await conn.run_sync(
            lambda sync_conn: {
                col["name"] for col in inspect(sync_conn).get_columns("waitlist_notifications")
            }
        )
    expected = {"id", "waitlist_id", "notified_at"}
    assert expected.issubset(columns), (
        f"Missing columns in waitlist_notifications: {expected - columns}"
    )


@pytest.mark.asyncio
async def test_waitlist_fk_to_client_profiles(async_engine) -> None:
    """Verify waitlist has a FK to client_profiles."""
    async with async_engine.connect() as conn:
        fks = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_foreign_keys("waitlist")
        )
    referred_tables = {fk["referred_table"] for fk in fks}
    assert "client_profiles" in referred_tables


@pytest.mark.asyncio
async def test_waitlist_fk_to_services(async_engine) -> None:
    """Verify waitlist has a FK to services."""
    async with async_engine.connect() as conn:
        fks = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_foreign_keys("waitlist")
        )
    referred_tables = {fk["referred_table"] for fk in fks}
    assert "services" in referred_tables


@pytest.mark.asyncio
async def test_waitlist_notifications_fk_to_waitlist(async_engine) -> None:
    """Verify waitlist_notifications has a FK to waitlist."""
    async with async_engine.connect() as conn:
        fks = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_foreign_keys("waitlist_notifications")
        )
    referred_tables = {fk["referred_table"] for fk in fks}
    assert "waitlist" in referred_tables


@pytest.mark.asyncio
async def test_waitlist_service_id_index_exists(async_engine) -> None:
    """Verify the waitlist(service_id) index exists."""
    async with async_engine.connect() as conn:
        indexes = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_indexes("waitlist")
        )
    # Check that at least one index covers service_id
    service_id_indexed = any(
        "service_id" in idx["column_names"] for idx in indexes
    )
    assert service_id_indexed, "No index found on waitlist.service_id"


# ---------------------------------------------------------------------------
# 5.1 — savepoint rollback isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_is_rolled_back_after_test(db_session: AsyncSession) -> None:
    """Write a role in this test; the next test should NOT see it."""
    role = RoleModel(
        id=uuid.uuid4(),
        name="__isolation_test_role__",
        description="Should be rolled back",
    )
    db_session.add(role)
    await db_session.flush()

    # Confirm the row is visible within this session
    result = await db_session.execute(
        text("SELECT name FROM roles WHERE name = '__isolation_test_role__'")
    )
    row = result.scalar_one_or_none()
    assert row == "__isolation_test_role__"

    # Test ends here — fixture rolls back the savepoint.


@pytest.mark.asyncio
async def test_previous_insert_not_visible(db_session: AsyncSession) -> None:
    """Verify the row from the previous test was rolled back."""
    result = await db_session.execute(
        text("SELECT name FROM roles WHERE name = '__isolation_test_role__'")
    )
    row = result.scalar_one_or_none()
    assert row is None, "Previous test's row leaked — savepoint rollback failed!"


@pytest.mark.asyncio
async def test_session_is_functional(db_session: AsyncSession) -> None:
    """Basic smoke: the session can execute a trivial query."""
    result = await db_session.execute(text("SELECT 1"))
    value = result.scalar_one()
    assert value == 1
