"""PgAppointmentRepository — PostgreSQL implementation of AppointmentRepository.

Strategy:
- ``save()`` uses ``merge()`` (upsert by PK) for the AppointmentModel row.
- Domain events in ``Appointment.events`` are synced to ``AppointmentEventModel``
  rows: existing rows are preserved; new events (list positions beyond what's
  already stored) are inserted.
- ``get_by_id()`` eager-loads ``appointment_events`` to reconstruct the full
  events list.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.appointment import Appointment
from domain.repositories.appointment_repository import AppointmentRepository
from domain.value_objects.appointment_status import AppointmentStatus
from domain.value_objects.time_slot import TimeSlot
from infrastructure.database.models.appointment import AppointmentModel
from infrastructure.database.models.appointment_event import AppointmentEventModel


class PgAppointmentRepository(AppointmentRepository):
    """Postgres-backed repository for Appointment aggregate roots.

    Receives an ``AsyncSession`` via constructor injection; session lifecycle
    is managed by the caller (use-case / FastAPI dependency).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # AppointmentRepository ABC implementation
    # ------------------------------------------------------------------

    async def get_by_id(self, id: UUID) -> Appointment | None:
        """Return the Appointment with the given ID, or None if not found.

        Eager-loads ``appointment_events`` to reconstruct the full event list.
        """
        stmt = (
            select(AppointmentModel)
            .options(selectinload(AppointmentModel.appointment_events))
            .where(AppointmentModel.id == id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def save(self, appointment: Appointment) -> Appointment:
        """Persist a new or updated Appointment and return it.

        Uses ``session.merge()`` so this works for both INSERT and UPDATE.
        Event rows are synced: existing rows (matched by appointment_id + event_type
        + occurred_at position) are NOT duplicated; only net-new events are inserted.
        """
        model = self._to_model(appointment)
        merged = await self._session.merge(model)

        # Sync events
        await self._sync_events(appointment, merged)

        await self._session.flush()
        return appointment

    async def find_by_staff_and_date_range(
        self,
        staff_id: UUID,
        start: datetime,
        end: datetime,
    ) -> list[Appointment]:
        """Return appointments for the given staff member whose slot overlaps [start, end)."""
        stmt = (
            select(AppointmentModel)
            .options(selectinload(AppointmentModel.appointment_events))
            .where(
                AppointmentModel.staff_id == staff_id,
                AppointmentModel.scheduled_start < end,
                AppointmentModel.scheduled_end > start,
            )
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def find_by_client(
        self,
        client_id: UUID,
        status: AppointmentStatus | None = None,
    ) -> list[Appointment]:
        """Return all appointments for the given client, optionally filtered by status."""
        conditions = [AppointmentModel.client_id == client_id]
        if status is not None:
            conditions.append(AppointmentModel.status == status.value)

        stmt = (
            select(AppointmentModel)
            .options(selectinload(AppointmentModel.appointment_events))
            .where(*conditions)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    # ------------------------------------------------------------------
    # Event sync helper
    # ------------------------------------------------------------------

    async def _sync_events(
        self, appointment: Appointment, model: AppointmentModel
    ) -> None:
        """Insert AppointmentEventModel rows for domain events not yet persisted.

        Counts existing event rows for this appointment and only inserts the
        net-new domain events (those beyond the already-persisted count).
        """
        # Count existing persisted event rows
        existing_stmt = select(AppointmentEventModel).where(
            AppointmentEventModel.appointment_id == model.id
        )
        existing_result = await self._session.execute(existing_stmt)
        existing_count = len(existing_result.scalars().all())

        # Insert only events that have no corresponding DB row yet
        new_events = appointment.events[existing_count:]
        for event_dict in new_events:
            event_model = AppointmentEventModel(
                id=uuid.uuid4(),
                appointment_id=model.id,
                event_type=event_dict["type"],
                occurred_at=_parse_event_timestamp(event_dict.get("timestamp")),
                details=event_dict.get("details"),
            )
            self._session.add(event_model)

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_entity(self, model: AppointmentModel) -> Appointment:
        """Convert an ``AppointmentModel`` (with eager-loaded events) to ``Appointment``."""
        time_slot = TimeSlot(
            start=model.scheduled_start,
            end=model.scheduled_end,
        )
        status = AppointmentStatus(model.status)

        # Reconstruct events list from AppointmentEventModel rows (ordered by occurred_at)
        events: list[dict[str, Any]] = []
        for evt in sorted(model.appointment_events, key=lambda e: e.occurred_at):
            event_dict: dict[str, Any] = {
                "type": evt.event_type,
                "timestamp": evt.occurred_at.isoformat(),
            }
            if evt.details:
                event_dict["details"] = evt.details
            events.append(event_dict)

        return Appointment(
            id=model.id,
            client_id=model.client_id,
            staff_id=model.staff_id,
            service_id=model.service_id,
            time_slot=time_slot,
            status=status,
            notes=model.notes,
            created_by=model.created_by,
            cancelled_by=model.cancelled_by,
            cancelled_at=model.cancelled_at,
            cancellation_reason=model.cancellation_reason,
            events=events,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Appointment) -> AppointmentModel:
        """Convert an ``Appointment`` domain entity to an ``AppointmentModel`` row.

        Note: does NOT include relationship collections (events are synced separately).
        """
        return AppointmentModel(
            id=entity.id,
            client_id=entity.client_id,
            staff_id=entity.staff_id,
            service_id=entity.service_id,
            scheduled_start=entity.time_slot.start,
            scheduled_end=entity.time_slot.end,
            status=entity.status.value,
            notes=entity.notes,
            created_by=entity.created_by,
            cancelled_by=entity.cancelled_by,
            cancelled_at=entity.cancelled_at,
            cancellation_reason=entity.cancellation_reason,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _parse_event_timestamp(ts: str | None) -> datetime:
    """Parse an ISO timestamp string (from domain event dicts) to a datetime.

    Falls back to UTC now if *ts* is None or malformed.
    """
    from datetime import timezone
    if ts is None:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.now(timezone.utc)
