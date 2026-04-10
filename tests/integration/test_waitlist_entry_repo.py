"""Integration tests for PgWaitlistEntryRepository.

Tests follow RED → GREEN → REFACTOR.
Run against a real PostgreSQL instance via the db_session fixture.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.waitlist_entry import WaitlistEntry
from domain.value_objects.waitlist_status import WaitlistStatus
from infrastructure.repositories.pg_waitlist_entry_repo import PgWaitlistEntryRepository
from infrastructure.database.models.role import RoleModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.models.client_profile import ClientProfileModel
from infrastructure.database.models.service import ServiceModel
from infrastructure.database.models.staff_profile import StaffProfileModel
from infrastructure.database.models.waitlist_entry import WaitlistEntryModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _create_role(session: AsyncSession) -> RoleModel:
    role = RoleModel(id=uuid.uuid4(), name=f"wl_role_{uuid.uuid4().hex[:6]}")
    session.add(role)
    await session.flush()
    return role


async def _create_user(session: AsyncSession, role_id: uuid.UUID) -> UserModel:
    now = _utcnow()
    user = UserModel(
        id=uuid.uuid4(),
        role_id=role_id,
        email=f"wl_user_{uuid.uuid4().hex[:8]}@test.com",
        first_name="Waitlist",
        last_name="User",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_client(session: AsyncSession, user_id: uuid.UUID) -> ClientProfileModel:
    now = _utcnow()
    profile = ClientProfileModel(
        id=uuid.uuid4(),
        user_id=user_id,
        blocked_staff_ids=[],
        created_at=now,
        updated_at=now,
    )
    session.add(profile)
    await session.flush()
    return profile


async def _create_service(session: AsyncSession) -> ServiceModel:
    from decimal import Decimal
    now = _utcnow()
    svc = ServiceModel(
        id=uuid.uuid4(),
        name=f"Service_{uuid.uuid4().hex[:6]}",
        description="Test service",
        duration_minutes=60,
        buffer_before=0,
        buffer_after=0,
        price=Decimal("100.00"),
        currency="USD",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(svc)
    await session.flush()
    return svc


async def _create_staff(session: AsyncSession, user_id: uuid.UUID) -> StaffProfileModel:
    now = _utcnow()
    profile = StaffProfileModel(
        id=uuid.uuid4(),
        user_id=user_id,
        is_available=True,
        created_at=now,
        updated_at=now,
    )
    session.add(profile)
    await session.flush()
    return profile


def _make_entry(
    client_id: uuid.UUID,
    service_id: uuid.UUID,
    preferred_staff_id: uuid.UUID | None = None,
    status: WaitlistStatus = WaitlistStatus.PENDING,
) -> WaitlistEntry:
    return WaitlistEntry(
        id=uuid.uuid4(),
        client_id=client_id,
        service_id=service_id,
        preferred_staff_id=preferred_staff_id,
        status=status,
    )


# ---------------------------------------------------------------------------
# save / get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_get_by_id(db_session: AsyncSession) -> None:
    """save() persists a new WaitlistEntry; get_by_id() returns it."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    client = await _create_client(db_session, user.id)
    service = await _create_service(db_session)

    entry = _make_entry(client.id, service.id)
    repo = PgWaitlistEntryRepository(db_session)
    saved = await repo.save(entry)

    assert saved.id == entry.id
    assert saved.client_id == client.id
    assert saved.service_id == service.id
    assert saved.status == WaitlistStatus.PENDING

    fetched = await repo.get_by_id(entry.id)
    assert fetched is not None
    assert fetched.id == entry.id
    assert fetched.client_id == client.id


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_unknown(db_session: AsyncSession) -> None:
    """get_by_id() returns None when no row matches."""
    repo = PgWaitlistEntryRepository(db_session)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_save_updates_status(db_session: AsyncSession) -> None:
    """save() with the same ID updates the record (status change persists)."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    client = await _create_client(db_session, user.id)
    service = await _create_service(db_session)

    entry = _make_entry(client.id, service.id)
    repo = PgWaitlistEntryRepository(db_session)
    await repo.save(entry)

    # Mutate and save again
    entry.notify()
    await repo.save(entry)

    fetched = await repo.get_by_id(entry.id)
    assert fetched is not None
    assert fetched.status == WaitlistStatus.NOTIFIED


# ---------------------------------------------------------------------------
# find_pending_by_service — FIFO ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_pending_by_service_returns_fifo_order(db_session: AsyncSession) -> None:
    """find_pending_by_service() returns PENDING entries in FIFO (created_at ASC) order."""
    role = await _create_role(db_session)
    user1 = await _create_user(db_session, role.id)
    user2 = await _create_user(db_session, role.id)
    client1 = await _create_client(db_session, user1.id)
    client2 = await _create_client(db_session, user2.id)
    service = await _create_service(db_session)

    # Entry for client1 created first (slightly earlier created_at)
    from datetime import timedelta
    now = _utcnow()
    entry1 = WaitlistEntry(
        id=uuid.uuid4(),
        client_id=client1.id,
        service_id=service.id,
        created_at=now - timedelta(seconds=5),
    )
    entry2 = WaitlistEntry(
        id=uuid.uuid4(),
        client_id=client2.id,
        service_id=service.id,
        created_at=now,
    )

    repo = PgWaitlistEntryRepository(db_session)
    await repo.save(entry1)
    await repo.save(entry2)

    results = await repo.find_pending_by_service(service.id)
    assert len(results) == 2
    assert results[0].id == entry1.id
    assert results[1].id == entry2.id


@pytest.mark.asyncio
async def test_find_pending_by_service_excludes_non_pending(db_session: AsyncSession) -> None:
    """find_pending_by_service() excludes entries that are not PENDING."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    client = await _create_client(db_session, user.id)
    service = await _create_service(db_session)

    pending_entry = _make_entry(client.id, service.id, status=WaitlistStatus.PENDING)
    notified_entry = _make_entry(client.id, service.id, status=WaitlistStatus.NOTIFIED)

    repo = PgWaitlistEntryRepository(db_session)
    await repo.save(pending_entry)
    await repo.save(notified_entry)

    results = await repo.find_pending_by_service(service.id)
    ids = [r.id for r in results]
    assert pending_entry.id in ids
    assert notified_entry.id not in ids


@pytest.mark.asyncio
async def test_find_pending_by_service_filters_by_staff(db_session: AsyncSession) -> None:
    """find_pending_by_service() with staff_id returns only entries preferring that staff."""
    role = await _create_role(db_session)
    user_client = await _create_user(db_session, role.id)
    user_staff = await _create_user(db_session, role.id)
    client = await _create_client(db_session, user_client.id)
    staff = await _create_staff(db_session, user_staff.id)
    service = await _create_service(db_session)

    entry_with_staff = _make_entry(client.id, service.id, preferred_staff_id=staff.id)
    entry_no_staff = _make_entry(client.id, service.id)

    repo = PgWaitlistEntryRepository(db_session)
    await repo.save(entry_with_staff)
    await repo.save(entry_no_staff)

    results = await repo.find_pending_by_service(service.id, staff_id=staff.id)
    ids = [r.id for r in results]
    assert entry_with_staff.id in ids
    assert entry_no_staff.id not in ids


@pytest.mark.asyncio
async def test_find_pending_by_service_returns_empty_for_unknown_service(
    db_session: AsyncSession,
) -> None:
    """find_pending_by_service() returns empty list for unknown service_id."""
    repo = PgWaitlistEntryRepository(db_session)
    results = await repo.find_pending_by_service(uuid.uuid4())
    assert results == []


# ---------------------------------------------------------------------------
# find_by_client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_by_client_returns_all_entries(db_session: AsyncSession) -> None:
    """find_by_client() returns all waitlist entries for a given client."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    client = await _create_client(db_session, user.id)
    svc1 = await _create_service(db_session)
    svc2 = await _create_service(db_session)

    entry1 = _make_entry(client.id, svc1.id)
    entry2 = _make_entry(client.id, svc2.id)

    repo = PgWaitlistEntryRepository(db_session)
    await repo.save(entry1)
    await repo.save(entry2)

    results = await repo.find_by_client(client.id)
    ids = {r.id for r in results}
    assert entry1.id in ids
    assert entry2.id in ids


@pytest.mark.asyncio
async def test_find_by_client_returns_empty_for_unknown_client(
    db_session: AsyncSession,
) -> None:
    """find_by_client() returns empty list for unknown client_id."""
    repo = PgWaitlistEntryRepository(db_session)
    results = await repo.find_by_client(uuid.uuid4())
    assert results == []
