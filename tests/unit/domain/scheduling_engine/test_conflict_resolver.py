"""Tests for ConflictResolver — detects overlapping appointments."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from domain.value_objects.time_slot import TimeSlot
from domain.value_objects.appointment_status import AppointmentStatus
from domain.entities.appointment import Appointment
from domain.scheduling_engine.conflict_resolver import ConflictResolver


def utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 10, hour, minute, tzinfo=timezone.utc)


def make_slot(start_hour: int, end_hour: int, start_min: int = 0, end_min: int = 0) -> TimeSlot:
    return TimeSlot(start=utc(start_hour, start_min), end=utc(end_hour, end_min))


def make_appointment(slot: TimeSlot, status: AppointmentStatus = AppointmentStatus.SCHEDULED) -> Appointment:
    return Appointment(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        staff_id=uuid.uuid4(),
        service_id=uuid.uuid4(),
        time_slot=slot,
        status=status,
    )


class TestConflictResolverNoConflicts:
    def test_no_existing_appointments_returns_empty(self):
        proposed = make_slot(10, 11)
        result = ConflictResolver.find_conflicts(proposed, [])
        assert result == []

    def test_adjacent_slot_no_conflict(self):
        proposed = make_slot(10, 11)
        existing = make_appointment(make_slot(11, 12))
        result = ConflictResolver.find_conflicts(proposed, [existing])
        assert result == []

    def test_non_overlapping_slot_no_conflict(self):
        proposed = make_slot(10, 11)
        existing = make_appointment(make_slot(12, 13))
        result = ConflictResolver.find_conflicts(proposed, [existing])
        assert result == []


class TestConflictResolverWithConflicts:
    def test_single_overlap_returns_appointment(self):
        proposed = make_slot(10, 12)  # 10:00–12:00
        overlapping = make_appointment(make_slot(11, 13))  # 11:00–13:00 — overlaps
        result = ConflictResolver.find_conflicts(proposed, [overlapping])
        assert len(result) == 1
        assert result[0] is overlapping

    def test_multiple_overlaps_returns_all(self):
        proposed = make_slot(9, 13)  # 9:00–13:00
        appt1 = make_appointment(make_slot(9, 10))
        appt2 = make_appointment(make_slot(11, 12))
        appt3 = make_appointment(make_slot(12, 13))
        result = ConflictResolver.find_conflicts(proposed, [appt1, appt2, appt3])
        assert len(result) == 3

    def test_ignores_cancelled_appointments(self):
        proposed = make_slot(10, 12)  # 10:00–12:00 overlaps 11:00–12:00
        cancelled = make_appointment(make_slot(11, 12), status=AppointmentStatus.CANCELLED)
        result = ConflictResolver.find_conflicts(proposed, [cancelled])
        assert result == []

    def test_ignores_no_show_appointments(self):
        proposed = make_slot(10, 12)  # 10:00–12:00 overlaps 11:00–12:00
        no_show = make_appointment(make_slot(11, 12), status=AppointmentStatus.NO_SHOW)
        result = ConflictResolver.find_conflicts(proposed, [no_show])
        assert result == []

    def test_ignores_completed_appointments(self):
        proposed = make_slot(10, 12)  # 10:00–12:00 overlaps 11:00–12:00
        completed = make_appointment(make_slot(11, 12), status=AppointmentStatus.COMPLETED)
        result = ConflictResolver.find_conflicts(proposed, [completed])
        assert result == []

    def test_active_and_cancelled_mixed(self):
        proposed = make_slot(10, 12)
        active = make_appointment(make_slot(11, 12), status=AppointmentStatus.CONFIRMED)
        cancelled = make_appointment(make_slot(10, 11), status=AppointmentStatus.CANCELLED)
        result = ConflictResolver.find_conflicts(proposed, [active, cancelled])
        assert len(result) == 1
        assert result[0] is active
