"""PgStaffAvailabilityRepository — PostgreSQL implementation of StaffAvailabilityRepository.

StaffAvailabilityModel stores recurring weekly windows as (day_of_week, start_time, end_time).
When converting to TimeSlot (which requires datetime), we anchor to the nearest future
date that falls on the correct ISO weekday, rooted at today UTC.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.repositories.staff_availability_repository import StaffAvailabilityRepository
from domain.value_objects.time_slot import TimeSlot
from infrastructure.database.models.staff_availability import StaffAvailabilityModel


def _anchor_date_for_weekday(day_of_week: int) -> date:
    """Return today's date adjusted to the nearest occurrence of *day_of_week*.

    Uses ISO weekday (1=Monday … 7=Sunday). We simply use today's date as the
    anchor date — the TimeSlot represents a *template* availability window, not
    a concrete calendar date.  Callers that need real slots on a specific date
    should use the start_time / end_time directly against their target date.

    For tests we need a consistent, timezone-aware datetime, so we use
    today UTC, adjusted forward to the correct ISO weekday.
    """
    today = date.today()
    delta = (day_of_week - today.isoweekday()) % 7
    return today + timedelta(days=delta)


def _to_time_slot(model: StaffAvailabilityModel) -> TimeSlot:
    """Build a UTC-aware TimeSlot from a StaffAvailabilityModel row.

    The date is anchored to the next occurrence of ``model.day_of_week``
    relative to today (UTC).  Time components come directly from the model.
    """
    anchor = _anchor_date_for_weekday(model.day_of_week)
    start = datetime(
        anchor.year, anchor.month, anchor.day,
        model.start_time.hour, model.start_time.minute, model.start_time.second,
        tzinfo=timezone.utc,
    )
    end = datetime(
        anchor.year, anchor.month, anchor.day,
        model.end_time.hour, model.end_time.minute, model.end_time.second,
        tzinfo=timezone.utc,
    )
    return TimeSlot(start=start, end=end)


class PgStaffAvailabilityRepository(StaffAvailabilityRepository):
    """Postgres-backed repository for recurring staff availability windows.

    Receives an ``AsyncSession`` via constructor injection.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # StaffAvailabilityRepository ABC implementation
    # ------------------------------------------------------------------

    async def get_by_staff(self, staff_id: UUID) -> list[TimeSlot]:
        """Return all recurring availability windows for the given staff member."""
        stmt = select(StaffAvailabilityModel).where(
            StaffAvailabilityModel.staff_id == staff_id
        )
        result = await self._session.execute(stmt)
        return [_to_time_slot(row) for row in result.scalars().all()]

    async def get_by_staff_and_day(self, staff_id: UUID, day_of_week: int) -> list[TimeSlot]:
        """Return availability windows for the given staff member on a specific weekday.

        Args:
            staff_id: The staff member's UUID.
            day_of_week: ISO weekday integer (1=Monday, 7=Sunday).
        """
        stmt = select(StaffAvailabilityModel).where(
            StaffAvailabilityModel.staff_id == staff_id,
            StaffAvailabilityModel.day_of_week == day_of_week,
        )
        result = await self._session.execute(stmt)
        return [_to_time_slot(row) for row in result.scalars().all()]
