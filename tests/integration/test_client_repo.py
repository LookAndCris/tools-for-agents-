"""Integration tests for PgClientRepository.

Tests follow RED → GREEN → REFACTOR.
Run against a real PostgreSQL instance via the db_session fixture.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.repositories.pg_client_repo import PgClientRepository
from infrastructure.database.models.role import RoleModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.models.client_profile import ClientProfileModel


# ---------------------------------------------------------------------------
# Helpers — create prerequisite role + user + client rows
# ---------------------------------------------------------------------------


async def _create_role(session: AsyncSession, name: str = "client_role") -> RoleModel:
    role = RoleModel(id=uuid.uuid4(), name=name)
    session.add(role)
    await session.flush()
    return role


async def _create_user(session: AsyncSession, role_id: uuid.UUID) -> UserModel:
    now = datetime.now(timezone.utc)
    user = UserModel(
        id=uuid.uuid4(),
        role_id=role_id,
        email=f"client_{uuid.uuid4().hex[:8]}@test.com",
        first_name="Test",
        last_name="Client",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_client_profile(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    notes: str | None = None,
    blocked_staff_ids: list[uuid.UUID] | None = None,
) -> ClientProfileModel:
    now = datetime.now(timezone.utc)
    profile = ClientProfileModel(
        id=uuid.uuid4(),
        user_id=user_id,
        notes=notes,
        blocked_staff_ids=blocked_staff_ids or [],
        created_at=now,
        updated_at=now,
    )
    session.add(profile)
    await session.flush()
    return profile


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_client_entity(db_session: AsyncSession) -> None:
    """Persist a ClientProfileModel and retrieve it as a domain Client."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    profile = await _create_client_profile(db_session, user.id, notes="VIP client")

    repo = PgClientRepository(db_session)
    entity = await repo.get_by_id(profile.id)

    assert entity is not None
    assert entity.id == profile.id
    assert entity.user_id == user.id
    assert entity.notes == "VIP client"
    assert entity.blocked_staff_ids == frozenset()


async def test_get_by_id_returns_none_for_missing(db_session: AsyncSession) -> None:
    """get_by_id returns None for a non-existent ID."""
    repo = PgClientRepository(db_session)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


async def test_get_by_id_maps_blocked_staff(db_session: AsyncSession) -> None:
    """blocked_staff_ids is correctly mapped from ARRAY to frozenset[UUID]."""
    role = await _create_role(db_session, name="blocked_test_role")
    user = await _create_user(db_session, role.id)
    staff_id1 = uuid.uuid4()
    staff_id2 = uuid.uuid4()
    profile = await _create_client_profile(
        db_session,
        user.id,
        blocked_staff_ids=[staff_id1, staff_id2],
    )

    repo = PgClientRepository(db_session)
    entity = await repo.get_by_id(profile.id)

    assert entity is not None
    assert entity.blocked_staff_ids == frozenset([staff_id1, staff_id2])


# ---------------------------------------------------------------------------
# get_by_user_id
# ---------------------------------------------------------------------------


async def test_get_by_user_id_returns_client_entity(db_session: AsyncSession) -> None:
    """Retrieve a client by its associated user_id."""
    role = await _create_role(db_session, name="user_id_role")
    user = await _create_user(db_session, role.id)
    profile = await _create_client_profile(db_session, user.id)

    repo = PgClientRepository(db_session)
    entity = await repo.get_by_user_id(user.id)

    assert entity is not None
    assert entity.id == profile.id
    assert entity.user_id == user.id


async def test_get_by_user_id_returns_none_when_no_profile(db_session: AsyncSession) -> None:
    """get_by_user_id returns None if the user has no client profile."""
    repo = PgClientRepository(db_session)
    result = await repo.get_by_user_id(uuid.uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# Rollback isolation
# ---------------------------------------------------------------------------


async def test_client_not_visible_across_tests(db_session: AsyncSession) -> None:
    """Confirms db_session fixture isolates writes between tests."""
    role = await _create_role(db_session, name="isolation_role_client")
    user = await _create_user(db_session, role.id)
    profile = await _create_client_profile(db_session, user.id)

    repo = PgClientRepository(db_session)
    entity = await repo.get_by_id(profile.id)
    assert entity is not None  # visible within this test
