"""Tests for the TimeSlot value object."""
from datetime import datetime, timezone, timedelta
import pytest
from domain.value_objects.time_slot import TimeSlot
from domain.exceptions import InvalidTimeSlotError


def utc(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class TestTimeSlotCreation:
    def test_valid_creation(self):
        slot = TimeSlot(start=utc(2026, 4, 10, 10), end=utc(2026, 4, 10, 11))
        assert slot.start == utc(2026, 4, 10, 10)
        assert slot.end == utc(2026, 4, 10, 11)

    def test_start_must_be_before_end(self):
        with pytest.raises(InvalidTimeSlotError):
            TimeSlot(start=utc(2026, 4, 10, 11), end=utc(2026, 4, 10, 10))

    def test_start_equal_end_raises(self):
        with pytest.raises(InvalidTimeSlotError):
            TimeSlot(start=utc(2026, 4, 10, 10), end=utc(2026, 4, 10, 10))

    def test_naive_datetime_raises(self):
        naive = datetime(2026, 4, 10, 10, 0)
        with pytest.raises(InvalidTimeSlotError):
            TimeSlot(start=naive, end=utc(2026, 4, 10, 11))

    def test_is_immutable(self):
        slot = TimeSlot(start=utc(2026, 4, 10, 10), end=utc(2026, 4, 10, 11))
        with pytest.raises((AttributeError, TypeError)):
            slot.start = utc(2026, 4, 10, 9)


class TestTimeSlotOverlaps:
    def test_non_overlapping_adjacent(self):
        a = TimeSlot(start=utc(2026, 4, 10, 10), end=utc(2026, 4, 10, 11))
        b = TimeSlot(start=utc(2026, 4, 10, 11), end=utc(2026, 4, 10, 12))
        assert a.overlaps(b) is False
        assert b.overlaps(a) is False

    def test_overlapping(self):
        a = TimeSlot(start=utc(2026, 4, 10, 10), end=utc(2026, 4, 10, 11, 30))
        b = TimeSlot(start=utc(2026, 4, 10, 11), end=utc(2026, 4, 10, 12))
        assert a.overlaps(b) is True
        assert b.overlaps(a) is True

    def test_contained_slot_overlaps(self):
        outer = TimeSlot(start=utc(2026, 4, 10, 10), end=utc(2026, 4, 10, 12))
        inner = TimeSlot(start=utc(2026, 4, 10, 10, 30), end=utc(2026, 4, 10, 11, 30))
        assert outer.overlaps(inner) is True


class TestTimeSlotDurationAndContains:
    def test_duration_minutes(self):
        slot = TimeSlot(start=utc(2026, 4, 10, 10), end=utc(2026, 4, 10, 11, 30))
        assert slot.duration_minutes() == 90

    def test_contains_inner(self):
        outer = TimeSlot(start=utc(2026, 4, 10, 9), end=utc(2026, 4, 10, 17))
        inner = TimeSlot(start=utc(2026, 4, 10, 10), end=utc(2026, 4, 10, 11))
        assert outer.contains(inner) is True

    def test_not_contains_partial(self):
        slot = TimeSlot(start=utc(2026, 4, 10, 10), end=utc(2026, 4, 10, 12))
        other = TimeSlot(start=utc(2026, 4, 10, 11), end=utc(2026, 4, 10, 13))
        assert slot.contains(other) is False
