"""PgStaffTimeOffRepository — PostgreSQL implementation of StaffTimeOffRepository."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.staff_time_off import StaffTimeOff
from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
from domain.value_objects.time_slot import TimeSlot
from infrastructure.database.models.staff_time_off import StaffTimeOffModel


class PgStaffTimeOffRepository(StaffTimeOffRepository):
    """Postgres-backed repository for staff time-off blocks.

    Receives an ``AsyncSession`` via constructor injection.
    ``get_by_staff_and_range()`` maps rows to ``TimeSlot`` value objects.
    ``get_by_id()``, ``save()``, and ``delete()`` work with the ``StaffTimeOff`` entity.
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

    async def get_by_id(self, id: UUID) -> StaffTimeOff | None:
        """Return the StaffTimeOff entity with the given ID, or None if not found."""
        stmt = select(StaffTimeOffModel).where(StaffTimeOffModel.id == id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def save(self, time_off: StaffTimeOff) -> StaffTimeOff:
        """Persist a new or updated StaffTimeOff entity and return it.

        Uses ``session.merge()`` so this works for both INSERT and UPDATE (upsert by PK).
        """
        model = self._to_model(time_off)
        await self._session.merge(model)
        await self._session.flush()
        return time_off

    async def delete(self, id: UUID) -> None:
        """Delete the StaffTimeOff record with the given ID. No-op if not found."""
        stmt = select(StaffTimeOffModel).where(StaffTimeOffModel.id == id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_time_slot(self, model: StaffTimeOffModel) -> TimeSlot:
        """Convert a ``StaffTimeOffModel`` row to a ``TimeSlot`` value object."""
        return TimeSlot(
            start=model.start_datetime,
            end=model.end_datetime,
        )

    def _to_entity(self, model: StaffTimeOffModel) -> StaffTimeOff:
        """Convert a ``StaffTimeOffModel`` row to a ``StaffTimeOff`` domain entity."""
        return StaffTimeOff(
            id=model.id,
            staff_id=model.staff_id,
            time_slot=TimeSlot(
                start=model.start_datetime,
                end=model.end_datetime,
            ),
            reason=model.reason,
        )

    def _to_model(self, entity: StaffTimeOff) -> StaffTimeOffModel:
        """Convert a ``StaffTimeOff`` domain entity to a ``StaffTimeOffModel`` row."""
        from datetime import timezone

        now = datetime.now(timezone.utc)
        return StaffTimeOffModel(
            id=entity.id,
            staff_id=entity.staff_id,
            start_datetime=entity.time_slot.start,
            end_datetime=entity.time_slot.end,
            reason=entity.reason,
            created_at=now,
            updated_at=now,
        )
