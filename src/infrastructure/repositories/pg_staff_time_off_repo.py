"""PgStaffTimeOffRepository — PostgreSQL implementation of StaffTimeOffRepository."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
from domain.value_objects.time_slot import TimeSlot
from infrastructure.database.models.staff_time_off import StaffTimeOffModel


class PgStaffTimeOffRepository(StaffTimeOffRepository):
    """Postgres-backed repository for staff time-off blocks.

    Receives an ``AsyncSession`` via constructor injection.
    Each ``StaffTimeOffModel`` row maps directly to a ``TimeSlot`` value object
    (start_datetime → TimeSlot.start, end_datetime → TimeSlot.end).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # StaffTimeOffRepository ABC implementation
    # ------------------------------------------------------------------

    async def get_by_staff_and_range(
        self,
        staff_id: UUID,
        start: datetime,
        end: datetime,
    ) -> list[TimeSlot]:
        """Return all time-off blocks for the given staff member that overlap *[start, end)*.

        A block overlaps the range when:
            block.start_datetime < end AND block.end_datetime > start
        """
        stmt = select(StaffTimeOffModel).where(
            StaffTimeOffModel.staff_id == staff_id,
            StaffTimeOffModel.start_datetime < end,
            StaffTimeOffModel.end_datetime > start,
        )
        result = await self._session.execute(stmt)
        return [self._to_time_slot(row) for row in result.scalars().all()]

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_time_slot(self, model: StaffTimeOffModel) -> TimeSlot:
        """Convert a ``StaffTimeOffModel`` row to a ``TimeSlot`` value object."""
        return TimeSlot(
            start=model.start_datetime,
            end=model.end_datetime,
        )
