"""ConflictResolver — detects scheduling conflicts among appointments."""
from __future__ import annotations

from domain.value_objects.time_slot import TimeSlot
from domain.entities.appointment import Appointment


class ConflictResolver:
    """Stateless service for finding appointment scheduling conflicts."""

    @staticmethod
    def find_conflicts(
        proposed: TimeSlot,
        existing: list[Appointment],
    ) -> list[Appointment]:
        """
        Return all active appointments whose time_slot overlaps with proposed.

        Only checks appointments where is_active is True (SCHEDULED or CONFIRMED).
        Uses TimeSlot.overlaps() as the single source of truth for overlap detection.
        """
        return [
            appt
            for appt in existing
            if appt.is_active and proposed.overlaps(appt.time_slot)
        ]
