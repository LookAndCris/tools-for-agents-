"""StaffRepository ABC — defines the persistence contract for staff members."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.staff import Staff


class StaffRepository(ABC):
    """Abstract repository for Staff persistence operations."""

    @abstractmethod
    def get_by_id(self, id: UUID) -> Staff | None:
        """Return the staff member with the given ID, or None if not found."""
        ...

    @abstractmethod
    def find_by_service(self, service_id: UUID) -> list[Staff]:
        """Return all staff members who offer the given service."""
        ...
