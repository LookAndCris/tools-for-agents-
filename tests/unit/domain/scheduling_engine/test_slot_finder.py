"""Tests for SlotFinder — generates valid appointment start times."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

import pytest

from domain.value_objects.time_slot import TimeSlot
from domain.value_objects.appointment_status import AppointmentStatus
from domain.entities.appointment import Appointment
from domain.scheduling_engine.slot_finder import SlotFinder


def utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 10, hour, minute, tzinfo=timezone.utc)


def make_slot(start_h: int, end_h: int, start_m: int = 0, end_m: int = 0) -> TimeSlot:
    return TimeSlot(start=utc(start_h, start_m), end=utc(end_h, end_m))


def make_appointment(slot: TimeSlot, status: AppointmentStatus = AppointmentStatus.SCHEDULED) -> Appointment:
    return Appointment(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        staff_id=uuid.uuid4(),
        service_id=uuid.uuid4(),
        time_slot=slot,
        status=status,
    )


class TestSlotFinderFindsValidSlots:
    def test_finds_slots_in_empty_day(self):
        """With one window and no appointments, returns slots at every interval."""
        windows = [make_slot(9, 11)]  # 2-hour window
        result = SlotFinder.find_slots(
            available_windows=windows,
            existing_appointments=[],
            service_duration_minutes=60,
            interval_minutes=30,
        )
        # 9:00 and 9:30 are valid starts for a 60-min service in a 9:00–11:00 window
        assert utc(9, 0) in result
        assert utc(9, 30) in result
        # 10:00 + 60min = 11:00 which equals window end but doesn't exceed — valid
        assert utc(10, 0) in result

    def test_returns_sorted_datetimes(self):
        """Results are sorted chronologically."""
        windows = [make_slot(9, 12)]
        result = SlotFinder.find_slots(windows, [], 60, 30)
        assert result == sorted(result)

    def test_window_too_short_for_service_returns_empty(self):
        """Window shorter than service duration yields no slots."""
        windows = [make_slot(9, 9, 0, 30)]  # 30-minute window
        result = SlotFinder.find_slots(windows, [], 60, 30)
        assert result == []

    def test_exact_fit_window_yields_one_slot(self):
        """Window exactly equal to service duration yields exactly one slot."""
        windows = [make_slot(10, 11)]  # 60-minute window
        result = SlotFinder.find_slots(windows, [], 60, 30)
        assert len(result) == 1
        assert result[0] == utc(10)


class TestSlotFinderWithExistingAppointments:
    def test_no_slots_when_fully_booked(self):
        """Existing appointment fills the window — no slots available."""
        windows = [make_slot(9, 11)]  # 2-hour window
        existing = [make_appointment(make_slot(9, 11))]
        result = SlotFinder.find_slots(windows, existing, 60, 30)
        assert result == []

    def test_slots_before_appointment_are_available(self):
        """Slots that don't overlap an existing appointment are still valid."""
        windows = [make_slot(9, 13)]  # 4-hour window
        existing = [make_appointment(make_slot(12, 13))]  # last hour booked
        result = SlotFinder.find_slots(windows, existing, 60, 30)
        # 9:00, 9:30, 10:00, 10:30 → but 11:00–12:00 is fine, 11:30 would conflict with 12:00–13:00
        assert utc(9) in result
        assert utc(11) in result  # 11:00–12:00 does not overlap 12:00–13:00

    def test_ignores_cancelled_appointment_conflicts(self):
        """Cancelled appointments don't block slots."""
        windows = [make_slot(9, 11)]
        cancelled = [make_appointment(make_slot(9, 11), status=AppointmentStatus.CANCELLED)]
        result = SlotFinder.find_slots(windows, cancelled, 60, 30)
        assert len(result) > 0

    def test_respects_interval_spacing(self):
        """Slots are only generated at interval_minutes boundaries."""
        windows = [make_slot(9, 12)]
        result = SlotFinder.find_slots(windows, [], 60, 60)
        # With 60-min interval: 9:00 and 10:00 and 11:00 are candidates
        assert utc(9) in result
        assert utc(10) in result
        assert utc(11) in result
        # 9:30 should NOT be in results (not on 60-min boundary)
        assert utc(9, 30) not in result


class TestSlotFinderMultipleWindows:
    def test_finds_slots_in_multiple_windows(self):
        """SlotFinder works across multiple disjoint windows."""
        windows = [make_slot(9, 10), make_slot(14, 16)]
        result = SlotFinder.find_slots(windows, [], 60, 30)
        # 9:00 in first window
        assert utc(9) in result
        # 14:00 and 14:30 in second window (wait: 14:30+60=15:30 < 16:00 — valid)
        assert utc(14) in result
        assert utc(14, 30) in result
        # 15:00+60=16:00 equals window end — valid
        assert utc(15) in result
