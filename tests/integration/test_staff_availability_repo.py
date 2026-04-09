"""Integration tests for PgStaffAvailabilityRepository.

Tests follow RED → GREEN → REFACTOR.
Run against a real PostgreSQL instance via the db_session fixture.
"""
from __future__ import annotations

import uuid
from datetime import datetime, time, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.repositories.pg_staff_availability_repo import PgStaffAvailabilityRepository
from infrastructure.database.models.role import RoleModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.models.staff_profile import StaffProfileModel
from infrastructure.database.models.staff_availability import StaffAvailabilityModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_role(session: AsyncSession) -> RoleModel:
    role = RoleModel(id=uuid.uuid4(), name=f"avail_role_{uuid.uuid4().hex[:6]}")
    session.add(role)
    await session.flush()
    return role


async def _create_user(session: AsyncSession, role_id: uuid.UUID) -> UserModel:
    now = datetime.now(timezone.utc)
    user = UserModel(
        id=uuid.uuid4(),
        role_id=role_id,
        email=f"avail_staff_{uuid.uuid4().hex[:8]}@test.com",
        first_name="Avail",
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


async def _create_availability(
    session: AsyncSession,
    staff_id: uuid.UUID,
    *,
    day_of_week: int = 1,
    start_time: time = time(9, 0),
    end_time: time = time(17, 0),
) -> StaffAvailabilityModel:
    now = datetime.now(timezone.utc)
    avail = StaffAvailabilityModel(
        id=uuid.uuid4(),
        staff_id=staff_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        created_at=now,
        updated_at=now,
    )
    session.add(avail)
    await session.flush()
    return avail


# ---------------------------------------------------------------------------
# get_by_staff
# ---------------------------------------------------------------------------


async def test_get_by_staff_returns_all_availability_windows(db_session: AsyncSession) -> None:
    """get_by_staff returns TimeSlots for every availability row of a staff member."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    staff = await _create_staff(db_session, user.id)
    # Two windows: Monday and Wednesday
    await _create_availability(db_session, staff.id, day_of_week=1, start_time=time(9, 0), end_time=time(17, 0))
    await _create_availability(db_session, staff.id, day_of_week=3, start_time=time(10, 0), end_time=time(15, 0))

    repo = PgStaffAvailabilityRepository(db_session)
    results = await repo.get_by_staff(staff.id)

    assert len(results) == 2


async def test_get_by_staff_returns_empty_for_no_availability(db_session: AsyncSession) -> None:
    """get_by_staff returns an empty list for a staff member with no availability rows."""
    repo = PgStaffAvailabilityRepository(db_session)
    results = await repo.get_by_staff(uuid.uuid4())
    assert results == []


# ---------------------------------------------------------------------------
# get_by_staff_and_day
# ---------------------------------------------------------------------------


async def test_get_by_staff_and_day_filters_by_weekday(db_session: AsyncSession) -> None:
    """get_by_staff_and_day returns only windows for the requested day."""
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    staff = await _create_staff(db_session, user.id)
    await _create_availability(db_session, staff.id, day_of_week=1)  # Monday
    await _create_availability(db_session, staff.id, day_of_week=2)  # Tuesday
    await _create_availability(db_session, staff.id, day_of_week=1, start_time=time(14, 0), end_time=time(18, 0))  # Monday again

    repo = PgStaffAvailabilityRepository(db_session)
    monday_slots = await repo.get_by_staff_and_day(staff.id, 1)
    tuesday_slots = await repo.get_by_staff_and_day(staff.id, 2)

    assert len(monday_slots) == 2
    assert len(tuesday_slots) == 1


async def test_get_by_staff_and_day_returns_empty_when_no_match(db_session: AsyncSession) -> None:
    """get_by_staff_and_day returns empty list when no windows match."""
    repo = PgStaffAvailabilityRepository(db_session)
    results = await repo.get_by_staff_and_day(uuid.uuid4(), 5)
    assert results == []


async def test_availability_time_slot_has_correct_boundaries(db_session: AsyncSession) -> None:
    """The TimeSlot returned reflects the start/end times from the model row.
    
    Since StaffAvailabilityModel stores time-of-day without a date, the repo
    returns TimeSlot objects anchored to a reference UTC date (today).
    We verify start < end and the correct time components.
    """
    role = await _create_role(db_session)
    user = await _create_user(db_session, role.id)
    staff = await _create_staff(db_session, user.id)
    await _create_availability(
        db_session, staff.id, day_of_week=1,
        start_time=time(9, 0), end_time=time(12, 0)
    )

    repo = PgStaffAvailabilityRepository(db_session)
    slots = await repo.get_by_staff_and_day(staff.id, 1)

    assert len(slots) == 1
    slot = slots[0]
    assert slot.start < slot.end
    assert slot.start.hour == 9
    assert slot.end.hour == 12
    assert slot.start.tzinfo is not None
