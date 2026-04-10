"""GetAppointmentEventsUseCase — returns audit events for an appointment."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from application.dto.responses import AppointmentEventResponse
from application.exceptions import NotFoundError
from domain.repositories.appointment_repository import AppointmentRepository


class GetAppointmentEventsUseCase:
    """Query use case: return all audit events for a given appointment.

    Events are returned in chronological order (oldest first).
    """

    def __init__(self, appointment_repo: AppointmentRepository) -> None:
        self._appointment_repo = appointment_repo

    async def execute(self, appointment_id: UUID) -> list[AppointmentEventResponse]:
        """Return the list of events for *appointment_id*.

        Args:
            appointment_id: The UUID of the appointment to query.

        Returns:
            A list of :class:`AppointmentEventResponse` DTOs ordered by
            *occurred_at* ascending (chronological).

        Raises:
            NotFoundError: If no appointment with the given ID exists.
        """
        appointment = await self._appointment_repo.get_by_id(appointment_id)
        if appointment is None:
            raise NotFoundError("Appointment", appointment_id)

        # Build response DTOs from the entity's in-memory events list.
        # The events are dicts with at least "type" and "timestamp" keys.
        responses: list[AppointmentEventResponse] = []
        for raw_event in appointment.events:
            occurred_at_raw = raw_event.get("timestamp")
            if isinstance(occurred_at_raw, str):
                occurred_at = datetime.fromisoformat(occurred_at_raw)
            elif isinstance(occurred_at_raw, datetime):
                occurred_at = occurred_at_raw
            else:
                occurred_at = datetime.now(timezone.utc)

            # Ensure timezone awareness
            if occurred_at.tzinfo is None:
                occurred_at = occurred_at.replace(tzinfo=timezone.utc)

            details = raw_event.get("details") or {}
            performed_by_raw = details.get("performed_by")
            if performed_by_raw is not None and not isinstance(performed_by_raw, uuid.UUID):
                try:
                    performed_by_raw = uuid.UUID(str(performed_by_raw))
                except (ValueError, AttributeError):
                    performed_by_raw = None

            responses.append(
                AppointmentEventResponse(
                    id=uuid.uuid4(),
                    appointment_id=appointment_id,
                    event_type=raw_event.get("type", "unknown"),
                    occurred_at=occurred_at,
                    performed_by=performed_by_raw,
                    details=details,
                )
            )

        # Sort chronologically (oldest first)
        responses.sort(key=lambda e: e.occurred_at)
        return responses
