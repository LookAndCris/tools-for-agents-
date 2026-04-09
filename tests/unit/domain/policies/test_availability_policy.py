"""Tests for AvailabilityPolicy — checks if a proposed slot fits available windows."""
from __future__ import annotations

from datetime import datetime, timezone

from domain.value_objects.time_slot import TimeSlot
from domain.policies.availability_policy import AvailabilityPolicy


def utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 10, hour, minute, tzinfo=timezone.utc)


def make_slot(start_h: int, end_h: int, start_m: int = 0, end_m: int = 0) -> TimeSlot:
    return TimeSlot(start=utc(start_h, start_m), end=utc(end_h, end_m))


class TestAvailabilityPolicyWithinWindow:
    def test_slot_within_window_returns_ok(self):
        policy = AvailabilityPolicy()
        proposed = make_slot(10, 11)
        windows = [make_slot(9, 17)]
        result = policy.check(proposed, windows, [])
        assert result.is_ok is True
        assert result.violations == []

    def test_slot_exactly_matches_window_returns_ok(self):
        policy = AvailabilityPolicy()
        proposed = make_slot(9, 17)
        windows = [make_slot(9, 17)]
        result = policy.check(proposed, windows, [])
        assert result.is_ok is True


class TestAvailabilityPolicyOutsideWindow:
    def test_slot_outside_all_windows_returns_fail(self):
        policy = AvailabilityPolicy()
        proposed = make_slot(8, 9)
        windows = [make_slot(9, 17)]
        result = policy.check(proposed, windows, [])
        assert result.is_ok is False
        assert len(result.violations) > 0

    def test_partially_outside_window_returns_fail(self):
        """Slot extends beyond window end — should fail."""
        policy = AvailabilityPolicy()
        proposed = make_slot(16, 18)  # extends past 17:00
        windows = [make_slot(9, 17)]
        result = policy.check(proposed, windows, [])
        assert result.is_ok is False

    def test_no_available_windows_returns_fail(self):
        policy = AvailabilityPolicy()
        proposed = make_slot(10, 11)
        result = policy.check(proposed, [], [])
        assert result.is_ok is False


class TestAvailabilityPolicyTimeOffConflict:
    def test_slot_conflicts_with_time_off_returns_fail(self):
        policy = AvailabilityPolicy()
        proposed = make_slot(12, 13)
        windows = [make_slot(9, 17)]
        time_off = [make_slot(12, 13)]
        result = policy.check(proposed, windows, time_off)
        assert result.is_ok is False
        assert len(result.violations) > 0

    def test_slot_not_in_time_off_returns_ok(self):
        policy = AvailabilityPolicy()
        proposed = make_slot(10, 11)
        windows = [make_slot(9, 17)]
        time_off = [make_slot(12, 13)]  # lunch — no conflict
        result = policy.check(proposed, windows, time_off)
        assert result.is_ok is True
