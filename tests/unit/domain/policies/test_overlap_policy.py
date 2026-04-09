"""Tests for OverlapPolicy — checks for appointment scheduling conflicts."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.value_objects.time_slot import TimeSlot
from domain.value_objects.appointment_status import AppointmentStatus
from domain.entities.appointment import Appointment
from domain.policies.overlap_policy import OverlapPolicy


def utc(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 4, 10, hour, minute, tzinfo=timezone.utc)


def make_slot(start_h: int, end_h: int) -> TimeSlot:
    return TimeSlot(start=utc(start_h), end=utc(end_h))


def make_appointment(slot: TimeSlot, status: AppointmentStatus = AppointmentStatus.SCHEDULED) -> Appointment:
    return Appointment(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        staff_id=uuid.uuid4(),
        service_id=uuid.uuid4(),
        time_slot=slot,
        status=status,
    )


class TestOverlapPolicyNoConflict:
    def test_empty_existing_returns_ok(self):
        policy = OverlapPolicy()
        result = policy.check(make_slot(10, 11), [])
        assert result.is_ok is True
        assert result.violations == []

    def test_non_overlapping_returns_ok(self):
        policy = OverlapPolicy()
        existing = [make_appointment(make_slot(12, 13))]
        result = policy.check(make_slot(10, 11), existing)
        assert result.is_ok is True

    def test_adjacent_slot_returns_ok(self):
        policy = OverlapPolicy()
        existing = [make_appointment(make_slot(11, 12))]
        result = policy.check(make_slot(10, 11), existing)
        assert result.is_ok is True


class TestOverlapPolicyWithConflict:
    def test_overlapping_returns_fail(self):
        policy = OverlapPolicy()
        existing = [make_appointment(make_slot(10, 12))]
        result = policy.check(make_slot(11, 13), existing)
        assert result.is_ok is False
        assert len(result.violations) > 0

    def test_violation_message_is_descriptive(self):
        policy = OverlapPolicy()
        existing = [make_appointment(make_slot(10, 12))]
        result = policy.check(make_slot(11, 13), existing)
        assert any("conflict" in v.lower() or "overlap" in v.lower() for v in result.violations)

    def test_multiple_conflicts_returns_multiple_violations(self):
        policy = OverlapPolicy()
        existing = [
            make_appointment(make_slot(10, 12)),
            make_appointment(make_slot(11, 13)),
        ]
        result = policy.check(make_slot(10, 14), existing)
        assert result.is_ok is False
        assert len(result.violations) >= 2
