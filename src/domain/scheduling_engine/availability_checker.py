"""AvailabilityChecker — computes available time windows for a given date."""
from __future__ import annotations

from datetime import date, datetime, timezone

from domain.value_objects.time_slot import TimeSlot


class AvailabilityChecker:
    """
    Stateless service that computes available time windows.

    Subtracts time-off blocks from availability windows, splitting windows
    when time-off falls in the middle.
    """

    @staticmethod
    def get_available_windows(
        availability_windows: list[TimeSlot],
        time_off_blocks: list[TimeSlot],
        target_date: date,
    ) -> list[TimeSlot]:
        """
        Return available time windows for target_date after removing time-off blocks.

        Algorithm:
        1. Filter availability windows to those on target_date.
        2. For each time-off block, subtract it from all current windows.
           - If time-off covers an entire window, remove the window.
           - If time-off is at the start of a window, trim the start.
           - If time-off is at the end of a window, trim the end.
           - If time-off is in the middle, split into two windows.
        3. Return the remaining windows sorted by start time.
        """
        # Step 1: Filter to target date
        day_windows: list[TimeSlot] = [
            w for w in availability_windows if w.start.date() == target_date
        ]

        # Step 2: Subtract each time-off block
        for block in time_off_blocks:
            day_windows = AvailabilityChecker._subtract_block(day_windows, block)

        # Step 3: Sort by start time
        return sorted(day_windows, key=lambda w: w.start)

    @staticmethod
    def _subtract_block(
        windows: list[TimeSlot], block: TimeSlot
    ) -> list[TimeSlot]:
        """
        Remove a time-off block from a list of windows.

        Returns a new list of windows with the block removed.
        """
        result: list[TimeSlot] = []
        for window in windows:
            # No overlap — keep window unchanged
            if not window.overlaps(block):
                result.append(window)
                continue

            # Block covers the entire window — remove it
            if block.start <= window.start and block.end >= window.end:
                continue  # drop this window entirely

            # Block trims the start
            if block.start <= window.start and block.end < window.end:
                trimmed = TimeSlot(start=block.end, end=window.end)
                result.append(trimmed)
                continue

            # Block trims the end
            if block.start > window.start and block.end >= window.end:
                trimmed = TimeSlot(start=window.start, end=block.start)
                result.append(trimmed)
                continue

            # Block is in the middle — split into two
            left = TimeSlot(start=window.start, end=block.start)
            right = TimeSlot(start=block.end, end=window.end)
            result.append(left)
            result.append(right)

        return result
