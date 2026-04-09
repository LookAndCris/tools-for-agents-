"""StaffAvailabilityRepository ABC — defines persistence contract for staff availability."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from domain.value_objects.time_slot import TimeSlot


class StaffAvailabilityRepository(ABC):
    """Abstract repository for StaffAvailability persistence operations."""

    @abstractmethod
    def get_by_staff(self, staff_id: UUID) -> list[TimeSlot]:
        """Return all availability windows for the given staff member."""
        ...

    @abstractmethod
    def get_by_staff_and_day(self, staff_id: UUID, day_of_week: int) -> list[TimeSlot]:
        """Return availability windows for the given staff member on a specific weekday.

        Args:
            staff_id: The staff member's UUID.
            day_of_week: ISO weekday integer (1=Monday, 7=Sunday).
        """
        ...
