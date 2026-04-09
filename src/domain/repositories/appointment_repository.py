"""AppointmentRepository ABC — defines the persistence contract for appointments."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from domain.entities.appointment import Appointment
from domain.value_objects.appointment_status import AppointmentStatus


class AppointmentRepository(ABC):
    """Abstract repository for Appointment persistence operations."""

    @abstractmethod
    def get_by_id(self, id: UUID) -> Appointment | None:
        """Return the appointment with the given ID, or None if not found."""
        ...

    @abstractmethod
    def save(self, appointment: Appointment) -> Appointment:
        """Persist a new or updated appointment and return it."""
        ...

    @abstractmethod
    def find_by_staff_and_date_range(
        self,
        staff_id: UUID,
        start: datetime,
        end: datetime,
    ) -> list[Appointment]:
        """Return all appointments for the given staff member in the date range."""
        ...

    @abstractmethod
    def find_by_client(
        self,
        client_id: UUID,
        status: AppointmentStatus | None = None,
    ) -> list[Appointment]:
        """Return all appointments for the given client, optionally filtered by status."""
        ...
