"""OverlapPolicy — checks that a proposed time slot doesn't conflict with existing appointments."""
from __future__ import annotations

from typing import TYPE_CHECKING

from domain.scheduling_engine.conflict_resolver import ConflictResolver
from domain.value_objects.time_slot import TimeSlot
from domain.policies.policy_result import PolicyResult

if TYPE_CHECKING:
    from domain.entities.appointment import Appointment


class OverlapPolicy:
    """Policy that forbids scheduling appointments with time conflicts.

    Uses ConflictResolver to detect overlapping active appointments.
    Returns a PolicyResult with violation details for each conflict.
    """

    def check(
        self,
        proposed: TimeSlot,
        existing: list["Appointment"],
    ) -> PolicyResult:
        """Check if the proposed slot conflicts with any existing active appointment.

        Args:
            proposed: The time window being requested.
            existing: Current appointments to check against.

        Returns:
            PolicyResult.ok() if no conflicts, PolicyResult.fail(...) with one
            violation message per conflicting appointment.
        """
        conflicts = ConflictResolver.find_conflicts(proposed, existing)
        if not conflicts:
            return PolicyResult.ok()

        violations = [
            f"Scheduling conflict with appointment {appt.id} "
            f"({appt.time_slot.start.isoformat()}–{appt.time_slot.end.isoformat()})"
            for appt in conflicts
        ]
        return PolicyResult.fail(*violations)
