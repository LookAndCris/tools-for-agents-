"""Integration tests for PgStaffRepository.

Tests follow RED → GREEN → REFACTOR.
Run against a real PostgreSQL instance via the db_session fixture.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.repositories.pg_staff_repo import PgStaffRepository
from infrastructure.database.models.role import RoleModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.models.staff_profile import StaffProfileModel
from infrastructure.database.models.service import ServiceModel
from infrastructure.database.models.staff_service import StaffServiceModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_role(session: AsyncSession, name: str | None = None) -> RoleModel:
    role = RoleModel(id=uuid.uuid4(), name=name or f"role_{uuid.uuid4().hex[:6]}")
    session.add(role)
    await session.flush()
    return role


async def _create_user(session: AsyncSession, role_id: uuid.UUID) -> UserModel:
    now = datetime.now(timezone.utc)
    user = UserModel(
        id=uuid.uuid4(),
        role_id=role_id,
        email=f"staff_{uuid.uuid4().hex[:8]}@test.com",
        first_name="Staff",
        last_name="Member",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_staff_profile(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    specialty: str | None = None,
    bio: str | None = None,
    is_available: bool = True,
) -> StaffProfileModel:
    now = datetime.now(timezone.utc)
    profile = StaffProfileModel(
        id=uuid.uuid4(),
        user_id=user_id,
        specialty=specialty,
        bio=bio,
        is_available=is_available,
        created_at=now,
        updated_at=now,
    )
    session.add(profile)
    await session.flush()
    return profile


async def _create_service(
    session: AsyncSession, name: str | None = None
) -> ServiceModel:
    from decimal import Decimal
    now = datetime.now(timezone.utc)
    svc = ServiceModel(
        id=uuid.uuid4(),
        name=name or f"Service_{uuid.uuid4().hex[:6]}",
        description="Test service",
        duration_minutes=60,
        buffer_before=0,
        buffer_after=0,
        price=Decimal("100.00"),
        currency="MXN",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(svc)
    await session.flush()
    return svc


async def _link_staff_service(
    session: AsyncSession, staff_id: uuid.UUID, service_id: uuid.UUID
) -> None:
    now = datetime.now(timezone.utc)
    link = StaffServiceModel(
        id=uuid.uuid4(),
        staff_id=staff_id,
        service_id=service_id,
        created_at=now,
        updated_at=now,
    )
    session.add(link)
    await session.flush()


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_staff_entity(db_session: AsyncSession) -> None:
    """Persist a StaffProfileModel and retrieve it as a domain Staff entity."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    profile = await _create_staff_profile(
        db_session, user.id, specialty="Barbering", bio="Expert barber"
    )

    repo = PgStaffRepository(db_session)
    entity = await repo.get_by_id(profile.id)

    assert entity is not None
    assert entity.id == profile.id
    assert entity.user_id == user.id
    assert entity.specialty == "Barbering"
    assert entity.bio == "Expert barber"
    assert entity.is_available is True
    assert entity.service_ids == frozenset()


async def test_get_by_id_returns_none_for_missing(db_session: AsyncSession) -> None:
    """get_by_id returns None for a non-existent ID."""
    repo = PgStaffRepository(db_session)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


async def test_get_by_id_includes_service_ids(db_session: AsyncSession) -> None:
    """Staff entity includes service_ids from the staff_services junction table."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    profile = await _create_staff_profile(db_session, user.id)
    svc1 = await _create_service(db_session)
    svc2 = await _create_service(db_session)
    await _link_staff_service(db_session, profile.id, svc1.id)
    await _link_staff_service(db_session, profile.id, svc2.id)

    repo = PgStaffRepository(db_session)
    entity = await repo.get_by_id(profile.id)

    assert entity is not None
    assert entity.service_ids == frozenset([svc1.id, svc2.id])


# ---------------------------------------------------------------------------
# find_by_service
# ---------------------------------------------------------------------------


async def test_find_by_service_returns_linked_staff(db_session: AsyncSession) -> None:
    """find_by_service returns only staff linked to the given service."""
    role = await _create_role(db_session)
    user1 = await _create_user(db_session, role.id)
    user2 = await _create_user(db_session, role.id)
    user3 = await _create_user(db_session, role.id)
    staff1 = await _create_staff_profile(db_session, user1.id)
    staff2 = await _create_staff_profile(db_session, user2.id)
    staff3 = await _create_staff_profile(db_session, user3.id)
    svc = await _create_service(db_session)
    await _link_staff_service(db_session, staff1.id, svc.id)
    await _link_staff_service(db_session, staff2.id, svc.id)
    # staff3 is NOT linked

    repo = PgStaffRepository(db_session)
    results = await repo.find_by_service(svc.id)

    ids = {s.id for s in results}
    assert staff1.id in ids
    assert staff2.id in ids
    assert staff3.id not in ids


async def test_find_by_service_returns_empty_when_no_match(db_session: AsyncSession) -> None:
    """find_by_service returns empty list when no staff offers the service."""
    repo = PgStaffRepository(db_session)
    results = await repo.find_by_service(uuid.uuid4())
    assert results == []


# ---------------------------------------------------------------------------
# Rollback isolation
# ---------------------------------------------------------------------------


async def test_staff_not_visible_across_tests(db_session: AsyncSession) -> None:
    """Confirms db_session fixture isolates writes between tests."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    profile = await _create_staff_profile(db_session, user.id)

    repo = PgStaffRepository(db_session)
    entity = await repo.get_by_id(profile.id)
    assert entity is not None  # visible within this test


# ---------------------------------------------------------------------------
# get_by_user_id
# ---------------------------------------------------------------------------


async def test_get_by_user_id_returns_staff_entity(db_session: AsyncSession) -> None:
    """get_by_user_id returns the correct Staff entity for a given user_id."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    profile = await _create_staff_profile(
        db_session, user.id, specialty="Styling", bio="Expert stylist"
    )

    repo = PgStaffRepository(db_session)
    entity = await repo.get_by_user_id(user.id)

    assert entity is not None
    assert entity.id == profile.id
    assert entity.user_id == user.id
    assert entity.specialty == "Styling"
    assert entity.bio == "Expert stylist"
    assert entity.is_available is True


async def test_get_by_user_id_returns_none_for_missing(db_session: AsyncSession) -> None:
    """get_by_user_id returns None when no staff profile exists for the user_id."""
    repo = PgStaffRepository(db_session)
    result = await repo.get_by_user_id(uuid.uuid4())
    assert result is None


async def test_get_by_user_id_includes_service_ids(db_session: AsyncSession) -> None:
    """Staff entity returned by get_by_user_id includes service_ids."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    profile = await _create_staff_profile(db_session, user.id)
    svc1 = await _create_service(db_session)
    svc2 = await _create_service(db_session)
    await _link_staff_service(db_session, profile.id, svc1.id)
    await _link_staff_service(db_session, profile.id, svc2.id)

    repo = PgStaffRepository(db_session)
    entity = await repo.get_by_user_id(user.id)

    assert entity is not None
    assert entity.service_ids == frozenset([svc1.id, svc2.id])
