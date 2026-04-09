"""Integration tests for PgStaffTimeOffRepository.

Tests follow RED → GREEN → REFACTOR.
Run against a real PostgreSQL instance via the db_session fixture.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.repositories.pg_staff_time_off_repo import PgStaffTimeOffRepository
from infrastructure.database.models.role import RoleModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.models.staff_profile import StaffProfileModel
from infrastructure.database.models.staff_time_off import StaffTimeOffModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


async def _create_role(session: AsyncSession) -> RoleModel:
    role = RoleModel(id=uuid.uuid4(), name=f"toff_role_{uuid.uuid4().hex[:6]}")
    session.add(role)
    await session.flush()
    return role


async def _create_user(session: AsyncSession, role_id: uuid.UUID) -> UserModel:
    now = datetime.now(timezone.utc)
    user = UserModel(
        id=uuid.uuid4(),
        role_id=role_id,
        email=f"toff_staff_{uuid.uuid4().hex[:8]}@test.com",
        first_name="TimeOff",
        last_name="Staff",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_staff(session: AsyncSession, user_id: uuid.UUID) -> StaffProfileModel:
    now = datetime.now(timezone.utc)
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


async def _create_time_off(
    session: AsyncSession,
    staff_id: uuid.UUID,
    start: datetime,
    end: datetime,
    reason: str | None = None,
) -> StaffTimeOffModel:
    now = datetime.now(timezone.utc)
    toff = StaffTimeOffModel(
        id=uuid.uuid4(),
        staff_id=staff_id,
        start_datetime=start,
        end_datetime=end,
        reason=reason,
        created_at=now,
        updated_at=now,
    )
    session.add(toff)
    await session.flush()
    return toff


# ---------------------------------------------------------------------------
# get_by_staff_and_range
# ---------------------------------------------------------------------------


async def test_get_by_staff_and_range_returns_overlapping_blocks(db_session: AsyncSession) -> None:
    """Returns time-off blocks that overlap the requested date range."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    staff = await _create_staff(db_session, user.id)

    # Block A: within range
    await _create_time_off(db_session, staff.id, _utc(2026, 5, 10), _utc(2026, 5, 12))
    # Block B: entirely outside range
    await _create_time_off(db_session, staff.id, _utc(2026, 6, 1), _utc(2026, 6, 3))
    # Block C: overlaps range end
    await _create_time_off(db_session, staff.id, _utc(2026, 5, 14), _utc(2026, 5, 16))

    repo = PgStaffTimeOffRepository(db_session)
    results = await repo.get_by_staff_and_range(
        staff.id,
        start=_utc(2026, 5, 9),
        end=_utc(2026, 5, 15),
    )

    assert len(results) == 2  # Block A and Block C


async def test_get_by_staff_and_range_returns_empty_outside_range(db_session: AsyncSession) -> None:
    """Returns empty list when no time-off blocks overlap the range."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    staff = await _create_staff(db_session, user.id)
    await _create_time_off(db_session, staff.id, _utc(2026, 1, 1), _utc(2026, 1, 5))

    repo = PgStaffTimeOffRepository(db_session)
    results = await repo.get_by_staff_and_range(
        staff.id,
        start=_utc(2026, 6, 1),
        end=_utc(2026, 6, 30),
    )
    assert results == []


async def test_get_by_staff_and_range_maps_to_time_slot(db_session: AsyncSession) -> None:
    """The returned TimeSlot has correct start/end datetimes."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    staff = await _create_staff(db_session, user.id)
    start = _utc(2026, 5, 10, 8)
    end = _utc(2026, 5, 10, 18)
    await _create_time_off(db_session, staff.id, start, end)

    repo = PgStaffTimeOffRepository(db_session)
    results = await repo.get_by_staff_and_range(
        staff.id,
        start=_utc(2026, 5, 1),
        end=_utc(2026, 5, 31),
    )

    assert len(results) == 1
    slot = results[0]
    assert slot.start == start
    assert slot.end == end
    assert slot.start.tzinfo is not None


async def test_get_by_staff_and_range_returns_empty_for_unknown_staff(db_session: AsyncSession) -> None:
    """Returns empty list for unknown staff_id."""
    repo = PgStaffTimeOffRepository(db_session)
    results = await repo.get_by_staff_and_range(
        uuid.uuid4(),
        start=_utc(2026, 1, 1),
        end=_utc(2026, 12, 31),
    )
    assert results == []


# ---------------------------------------------------------------------------
# save
# ---------------------------------------------------------------------------


async def test_save_creates_new_time_off(db_session: AsyncSession) -> None:
    """save() persists a new StaffTimeOff entity and returns it."""
    from domain.entities.staff_time_off import StaffTimeOff
    from domain.value_objects.time_slot import TimeSlot
    from sqlalchemy import select

    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    staff = await _create_staff(db_session, user.id)

    start = _utc(2026, 7, 1, 9)
    end = _utc(2026, 7, 1, 17)
    entity = StaffTimeOff(
        id=uuid.uuid4(),
        staff_id=staff.id,
        time_slot=TimeSlot(start=start, end=end),
        reason="Holiday",
    )

    repo = PgStaffTimeOffRepository(db_session)
    saved = await repo.save(entity)

    assert saved is not None
    assert saved.id == entity.id
    assert saved.staff_id == staff.id
    assert saved.time_slot.start == start
    assert saved.time_slot.end == end
    assert saved.reason == "Holiday"

    # Verify it was actually written to the database
    stmt = select(StaffTimeOffModel).where(StaffTimeOffModel.id == entity.id)
    result = await db_session.execute(stmt)
    row = result.scalar_one_or_none()
    assert row is not None


async def test_save_updates_existing_time_off(db_session: AsyncSession) -> None:
    """save() with an existing ID updates the record (upsert semantics)."""
    from domain.entities.staff_time_off import StaffTimeOff
    from domain.value_objects.time_slot import TimeSlot

    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    staff = await _create_staff(db_session, user.id)

    # Create initial record
    existing = await _create_time_off(
        db_session, staff.id, _utc(2026, 7, 1, 9), _utc(2026, 7, 1, 17), reason="Original"
    )

    # Update with new reason via save()
    entity = StaffTimeOff(
        id=existing.id,
        staff_id=staff.id,
        time_slot=TimeSlot(start=_utc(2026, 7, 1, 9), end=_utc(2026, 7, 1, 17)),
        reason="Updated reason",
    )

    repo = PgStaffTimeOffRepository(db_session)
    saved = await repo.save(entity)

    assert saved.id == existing.id
    assert saved.reason == "Updated reason"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


async def test_delete_removes_time_off(db_session: AsyncSession) -> None:
    """delete() removes a StaffTimeOff block by ID."""
    from sqlalchemy import select

    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    staff = await _create_staff(db_session, user.id)

    toff = await _create_time_off(
        db_session, staff.id, _utc(2026, 8, 1, 9), _utc(2026, 8, 1, 17)
    )

    repo = PgStaffTimeOffRepository(db_session)
    await repo.delete(toff.id)

    # Verify it was removed
    stmt = select(StaffTimeOffModel).where(StaffTimeOffModel.id == toff.id)
    result = await db_session.execute(stmt)
    row = result.scalar_one_or_none()
    assert row is None


async def test_delete_nonexistent_id_does_not_raise(db_session: AsyncSession) -> None:
    """delete() with a non-existent ID does not raise an exception."""
    repo = PgStaffTimeOffRepository(db_session)
    # Should complete without error
    await repo.delete(uuid.uuid4())


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


async def test_get_by_id_returns_entity(db_session: AsyncSession) -> None:
    """get_by_id() returns the matching StaffTimeOff entity."""
    from domain.entities.staff_time_off import StaffTimeOff

    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    staff = await _create_staff(db_session, user.id)

    start = _utc(2026, 9, 1, 8)
    end = _utc(2026, 9, 1, 18)
    toff = await _create_time_off(db_session, staff.id, start, end, reason="Conference")

    repo = PgStaffTimeOffRepository(db_session)
    result = await repo.get_by_id(toff.id)

    assert result is not None
    assert isinstance(result, StaffTimeOff)
    assert result.id == toff.id
    assert result.staff_id == staff.id
    assert result.time_slot.start == start
    assert result.time_slot.end == end
    assert result.reason == "Conference"


async def test_get_by_id_returns_none_for_unknown_id(db_session: AsyncSession) -> None:
    """get_by_id() returns None when no record matches."""
    repo = PgStaffTimeOffRepository(db_session)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None
