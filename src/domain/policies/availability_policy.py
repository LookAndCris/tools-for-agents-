"""AvailabilityPolicy — checks that a proposed slot fits within available windows."""
from __future__ import annotations

from datetime import date

from domain.policies.policy_result import PolicyResult
from domain.scheduling_engine.availability_checker import AvailabilityChecker
from domain.value_objects.time_slot import TimeSlot


class AvailabilityPolicy:
    """Policy that checks if a proposed slot falls within available (post-time-off) windows.

    Uses AvailabilityChecker to compute net availability after time-off,
    then verifies the proposed slot is fully contained within a free window.
    """

    def check(
        self,
        proposed: TimeSlot,
        available_windows: list[TimeSlot],
        time_off_blocks: list[TimeSlot],
    ) -> PolicyResult:
        """Check if *proposed* fits within the available windows.

        Args:
            proposed: The time window being requested.
            available_windows: Staff's availability windows for the day.
            time_off_blocks: Staff's time-off blocks for the day.

        Returns:
            PolicyResult.ok() if the slot is available,
            PolicyResult.fail(...) with a violation message explaining why.
        """
        target_date: date = proposed.start.date()
        free_windows = AvailabilityChecker.get_available_windows(
            available_windows, time_off_blocks, target_date
        )

        violations: list[str] = []

        # The proposed slot must be fully contained in at least one free window
        if not any(window.contains(proposed) for window in free_windows):
            if not available_windows:
                violations.append("No availability windows defined for this date.")
            else:
                violations.append(
                    f"Proposed slot {proposed.start.isoformat()}–"
                    f"{proposed.end.isoformat()} does not fall within any "
                    "available window after time-off deduction."
                )

        if violations:
            return PolicyResult.fail(*violations)
        return PolicyResult.ok()
