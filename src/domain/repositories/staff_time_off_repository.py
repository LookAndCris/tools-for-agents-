"""StaffTimeOffRepository ABC — defines persistence contract for staff time-off."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from domain.value_objects.time_slot import TimeSlot


class StaffTimeOffRepository(ABC):
    """Abstract repository for StaffTimeOff persistence operations."""

    @abstractmethod
    async def get_by_staff_and_range(
        self,
        staff_id: UUID,
        start: datetime,
        end: datetime,
    ) -> list[TimeSlot]:
        """Return all time-off blocks for the given staff member within the date range."""
        ...
