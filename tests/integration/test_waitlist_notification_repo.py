"""Integration tests for PgWaitlistNotificationRepository.

Tests follow RED → GREEN → REFACTOR.
Run against a real PostgreSQL instance via the db_session fixture.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.waitlist_entry import WaitlistEntry
from domain.entities.waitlist_notification import WaitlistNotification
from domain.value_objects.waitlist_status import WaitlistStatus
from infrastructure.repositories.pg_waitlist_notification_repo import PgWaitlistNotificationRepository
from infrastructure.repositories.pg_waitlist_entry_repo import PgWaitlistEntryRepository
from infrastructure.database.models.role import RoleModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.models.client_profile import ClientProfileModel
from infrastructure.database.models.service import ServiceModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _create_role(session: AsyncSession) -> RoleModel:
    role = RoleModel(id=uuid.uuid4(), name=f"wln_role_{uuid.uuid4().hex[:6]}")
    session.add(role)
    await session.flush()
    return role


async def _create_user(session: AsyncSession, role_id: uuid.UUID) -> UserModel:
    now = _utcnow()
    user = UserModel(
        id=uuid.uuid4(),
        role_id=role_id,
        email=f"wln_user_{uuid.uuid4().hex[:8]}@test.com",
        first_name="WLNotif",
        last_name="User",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_client(session: AsyncSession, user_id: uuid.UUID) -> ClientProfileModel:
    from decimal import Decimal
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


async def _create_waitlist_entry(
    session: AsyncSession,
    client_id: uuid.UUID,
    service_id: uuid.UUID,
) -> WaitlistEntry:
    """Create and persist a PENDING waitlist entry."""
    entry = WaitlistEntry(
        id=uuid.uuid4(),
        client_id=client_id,
        service_id=service_id,
        status=WaitlistStatus.PENDING,
    )
    repo = PgWaitlistEntryRepository(session)
    await repo.save(entry)
    return entry


# ---------------------------------------------------------------------------
# save / find_by_waitlist_entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_find_by_waitlist_entry(db_session: AsyncSession) -> None:
    """save() persists a WaitlistNotification; find_by_waitlist_entry() returns it."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    client = await _create_client(db_session, user.id)
    service = await _create_service(db_session)
    entry = await _create_waitlist_entry(db_session, client.id, service.id)

    notification = WaitlistNotification(
        id=uuid.uuid4(),
        waitlist_entry_id=entry.id,
        notified_at=_utcnow(),
        expires_at=_utcnow() + timedelta(days=3),
    )

    repo = PgWaitlistNotificationRepository(db_session)
    saved = await repo.save(notification)

    assert saved.id == notification.id
    assert saved.waitlist_entry_id == entry.id
    assert saved.expires_at is not None

    results = await repo.find_by_waitlist_entry(entry.id)
    assert len(results) == 1
    assert results[0].id == notification.id


@pytest.mark.asyncio
async def test_find_by_waitlist_entry_returns_empty_for_unknown(
    db_session: AsyncSession,
) -> None:
    """find_by_waitlist_entry() returns empty list when no notifications exist."""
    repo = PgWaitlistNotificationRepository(db_session)
    results = await repo.find_by_waitlist_entry(uuid.uuid4())
    assert results == []


@pytest.mark.asyncio
async def test_save_multiple_notifications_for_same_entry(db_session: AsyncSession) -> None:
    """Multiple notifications can be saved for the same waitlist entry."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    client = await _create_client(db_session, user.id)
    service = await _create_service(db_session)
    entry = await _create_waitlist_entry(db_session, client.id, service.id)

    now = _utcnow()
    notif1 = WaitlistNotification(
        id=uuid.uuid4(),
        waitlist_entry_id=entry.id,
        notified_at=now - timedelta(days=1),
    )
    notif2 = WaitlistNotification(
        id=uuid.uuid4(),
        waitlist_entry_id=entry.id,
        notified_at=now,
    )

    repo = PgWaitlistNotificationRepository(db_session)
    await repo.save(notif1)
    await repo.save(notif2)

    results = await repo.find_by_waitlist_entry(entry.id)
    ids = {r.id for r in results}
    assert notif1.id in ids
    assert notif2.id in ids


@pytest.mark.asyncio
async def test_save_notification_without_expires_at(db_session: AsyncSession) -> None:
    """save() works when expires_at is None."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    client = await _create_client(db_session, user.id)
    service = await _create_service(db_session)
    entry = await _create_waitlist_entry(db_session, client.id, service.id)

    notification = WaitlistNotification(
        id=uuid.uuid4(),
        waitlist_entry_id=entry.id,
        notified_at=_utcnow(),
        expires_at=None,
    )

    repo = PgWaitlistNotificationRepository(db_session)
    saved = await repo.save(notification)
    assert saved.expires_at is None
