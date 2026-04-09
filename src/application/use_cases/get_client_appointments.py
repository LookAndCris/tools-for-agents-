"""GetClientAppointmentsUseCase — returns a client's appointments."""
from __future__ import annotations

from domain.repositories.appointment_repository import AppointmentRepository
from domain.value_objects.appointment_status import AppointmentStatus
from application.dto.queries import GetClientAppointmentsQuery
from application.dto.responses import AppointmentResponse


class GetClientAppointmentsUseCase:
    """Query use case: list appointments for a given client."""

    def __init__(self, appointment_repo: AppointmentRepository) -> None:
        self._appointment_repo = appointment_repo

    async def execute(self, query: GetClientAppointmentsQuery) -> list[AppointmentResponse]:
        """Return all appointments for the given client.

        Optionally filters by status string (e.g. "scheduled").
        """
        status_filter: AppointmentStatus | None = None
        if query.status is not None:
            status_filter = AppointmentStatus(query.status)

        appointments = await self._appointment_repo.find_by_client(
            query.client_id,
            status_filter,
        )
        return [AppointmentResponse.from_entity(a) for a in appointments]
