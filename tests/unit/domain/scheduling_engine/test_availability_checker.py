"""Tests for AvailabilityChecker — computes available time windows."""
from __future__ import annotations

from datetime import datetime, timezone, date

import pytest

from domain.value_objects.time_slot import TimeSlot
from domain.scheduling_engine.availability_checker import AvailabilityChecker


def utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 10, hour, minute, tzinfo=timezone.utc)


def make_slot(start_hour: int, end_hour: int, start_min: int = 0, end_min: int = 0) -> TimeSlot:
    return TimeSlot(start=utc(start_hour, start_min), end=utc(end_hour, end_min))


TARGET_DATE = date(2026, 4, 10)


class TestGetAvailableWindowsFullDay:
    def test_full_day_no_time_off(self):
        """With one availability window and no time off, returns the full window."""
        windows = [make_slot(9, 17)]
        result = AvailabilityChecker.get_available_windows(windows, [], TARGET_DATE)
        assert len(result) == 1
        assert result[0] == make_slot(9, 17)

    def test_multiple_windows_no_time_off(self):
        """Multiple availability windows, no time off, returns both sorted."""
        windows = [make_slot(13, 17), make_slot(9, 12)]
        result = AvailabilityChecker.get_available_windows(windows, [], TARGET_DATE)
        assert len(result) == 2
        assert result[0].start < result[1].start


class TestGetAvailableWindowsTimeOffRemovesWindow:
    def test_time_off_covers_entire_window(self):
        """Time-off block that covers the entire window removes it."""
        windows = [make_slot(9, 12)]
        time_off = [make_slot(9, 12)]
        result = AvailabilityChecker.get_available_windows(windows, time_off, TARGET_DATE)
        assert result == []

    def test_time_off_overlapping_entire_window_removes_it(self):
        """Time-off block larger than window removes it."""
        windows = [make_slot(10, 11)]
        time_off = [make_slot(9, 12)]
        result = AvailabilityChecker.get_available_windows(windows, time_off, TARGET_DATE)
        assert result == []


class TestGetAvailableWindowsTimeOffSplitsWindow:
    def test_time_off_in_middle_splits_window(self):
        """Time-off in the middle of a window splits it into two parts."""
        windows = [make_slot(9, 17)]
        time_off = [make_slot(12, 13)]  # lunch break
        result = AvailabilityChecker.get_available_windows(windows, time_off, TARGET_DATE)
        assert len(result) == 2
        # First part: 9:00–12:00
        assert result[0].start == utc(9)
        assert result[0].end == utc(12)
        # Second part: 13:00–17:00
        assert result[1].start == utc(13)
        assert result[1].end == utc(17)

    def test_time_off_at_start_trims_window(self):
        """Time-off at the beginning of a window trims the start."""
        windows = [make_slot(9, 17)]
        time_off = [make_slot(9, 10)]
        result = AvailabilityChecker.get_available_windows(windows, time_off, TARGET_DATE)
        assert len(result) == 1
        assert result[0].start == utc(10)
        assert result[0].end == utc(17)

    def test_time_off_at_end_trims_window(self):
        """Time-off at the end of a window trims the end."""
        windows = [make_slot(9, 17)]
        time_off = [make_slot(16, 17)]
        result = AvailabilityChecker.get_available_windows(windows, time_off, TARGET_DATE)
        assert len(result) == 1
        assert result[0].start == utc(9)
        assert result[0].end == utc(16)


class TestGetAvailableWindowsNoAvailability:
    def test_no_windows_returns_empty(self):
        result = AvailabilityChecker.get_available_windows([], [], TARGET_DATE)
        assert result == []

    def test_all_windows_blocked_returns_empty(self):
        windows = [make_slot(9, 12), make_slot(13, 17)]
        time_off = [make_slot(8, 18)]  # covers everything
        result = AvailabilityChecker.get_available_windows(windows, time_off, TARGET_DATE)
        assert result == []

    def test_filters_windows_for_target_date(self):
        """Windows on a different date are excluded."""
        # Window on the target date
        target_window = make_slot(9, 17)
        # Window on a different date (April 11)
        other_date_window = TimeSlot(
            start=datetime(2026, 4, 11, 9, tzinfo=timezone.utc),
            end=datetime(2026, 4, 11, 17, tzinfo=timezone.utc),
        )
        result = AvailabilityChecker.get_available_windows(
            [target_window, other_date_window], [], TARGET_DATE
        )
        assert len(result) == 1
        assert result[0] == target_window
