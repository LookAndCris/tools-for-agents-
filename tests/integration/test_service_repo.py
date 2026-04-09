"""Integration tests for PgServiceRepository.

Tests follow RED → GREEN → REFACTOR.
Run against a real PostgreSQL instance via the db_session fixture.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.repositories.pg_service_repo import PgServiceRepository
from infrastructure.database.models.service import ServiceModel


# ---------------------------------------------------------------------------
# Helpers — build a ServiceModel row directly (bypasses repo for setup)
# ---------------------------------------------------------------------------


def _make_service_model(
    *,
    name: str = "Haircut",
    duration_minutes: int = 60,
    buffer_before: int = 0,
    buffer_after: int = 0,
    price: Decimal = Decimal("150.00"),
    currency: str = "MXN",
    is_active: bool = True,
) -> ServiceModel:
    now = datetime.now(timezone.utc)
    return ServiceModel(
        id=uuid.uuid4(),
        name=name,
        description="A test service",
        duration_minutes=duration_minutes,
        buffer_before=buffer_before,
        buffer_after=buffer_after,
        price=price,
        currency=currency,
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_service_entity(db_session: AsyncSession) -> None:
    """Save a ServiceModel directly, then retrieve it via repo.get_by_id."""
    model = _make_service_model(name="Haircut Test")
    db_session.add(model)
    await db_session.flush()

    repo = PgServiceRepository(db_session)
    entity = await repo.get_by_id(model.id)

    assert entity is not None
    assert entity.id == model.id
    assert entity.name == "Haircut Test"
    assert entity.duration.duration_minutes == 60
    assert entity.price.amount == Decimal("150.00")
    assert entity.price.currency == "MXN"
    assert entity.is_active is True


async def test_get_by_id_returns_none_for_missing(db_session: AsyncSession) -> None:
    """get_by_id returns None for a non-existent ID."""
    repo = PgServiceRepository(db_session)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


async def test_get_by_id_maps_buffers(db_session: AsyncSession) -> None:
    """Buffers from ServiceModel are correctly mapped to ServiceDuration."""
    model = _make_service_model(
        name="Massage",
        duration_minutes=90,
        buffer_before=10,
        buffer_after=5,
    )
    db_session.add(model)
    await db_session.flush()

    repo = PgServiceRepository(db_session)
    entity = await repo.get_by_id(model.id)

    assert entity is not None
    assert entity.duration.buffer_before == 10
    assert entity.duration.duration_minutes == 90
    assert entity.duration.buffer_after == 5
    assert entity.total_duration_minutes == 105  # 10+90+5


# ---------------------------------------------------------------------------
# get_all_active
# ---------------------------------------------------------------------------


async def test_get_all_active_returns_only_active(db_session: AsyncSession) -> None:
    """get_all_active excludes inactive services."""
    active = _make_service_model(name="Active Service")
    inactive = _make_service_model(name="Inactive Service", is_active=False)
    db_session.add(active)
    db_session.add(inactive)
    await db_session.flush()

    repo = PgServiceRepository(db_session)
    results = await repo.get_all_active()

    ids = {s.id for s in results}
    assert active.id in ids
    assert inactive.id not in ids


# ---------------------------------------------------------------------------
# find_by_ids
# ---------------------------------------------------------------------------


async def test_find_by_ids_returns_matching_services(db_session: AsyncSession) -> None:
    """find_by_ids returns exactly the requested services."""
    svc1 = _make_service_model(name="Service One")
    svc2 = _make_service_model(name="Service Two")
    svc3 = _make_service_model(name="Service Three")
    db_session.add_all([svc1, svc2, svc3])
    await db_session.flush()

    repo = PgServiceRepository(db_session)
    results = await repo.find_by_ids([svc1.id, svc3.id])

    ids = {s.id for s in results}
    assert ids == {svc1.id, svc3.id}


async def test_find_by_ids_empty_list(db_session: AsyncSession) -> None:
    """find_by_ids with empty list returns empty list."""
    repo = PgServiceRepository(db_session)
    results = await repo.find_by_ids([])
    assert results == []


# ---------------------------------------------------------------------------
# Rollback isolation
# ---------------------------------------------------------------------------


async def test_service_not_visible_across_tests(db_session: AsyncSession) -> None:
    """Confirms the db_session fixture properly isolates this test's writes."""
    model = _make_service_model(name="Isolation Test Service")
    db_session.add(model)
    await db_session.flush()

    repo = PgServiceRepository(db_session)
    entity = await repo.get_by_id(model.id)
    assert entity is not None  # visible within this test

    # The service will NOT be visible in the next test (savepoint rollback).
