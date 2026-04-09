"""Tests for CancellationPolicy — role-based cancellation rules."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from domain.value_objects.time_slot import TimeSlot
from domain.value_objects.appointment_status import AppointmentStatus
from domain.entities.appointment import Appointment
from domain.policies.cancellation_policy import CancellationPolicy


def utc(hour: int) -> datetime:
    return datetime(2026, 4, 10, hour, tzinfo=timezone.utc)


def make_slot() -> TimeSlot:
    return TimeSlot(start=utc(10), end=utc(11))


def make_appointment(status: AppointmentStatus = AppointmentStatus.SCHEDULED, staff_id: uuid.UUID | None = None) -> Appointment:
    return Appointment(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        staff_id=staff_id or uuid.uuid4(),
        service_id=uuid.uuid4(),
        time_slot=make_slot(),
        status=status,
    )


CURRENT_TIME = datetime(2026, 4, 10, 8, tzinfo=timezone.utc)


class TestCancellationPolicyAdminAlwaysCan:
    def test_admin_can_cancel_scheduled(self):
        policy = CancellationPolicy()
        appt = make_appointment(AppointmentStatus.SCHEDULED)
        result = policy.can_cancel(appt, "admin", CURRENT_TIME)
        assert result.is_ok is True

    def test_admin_can_cancel_confirmed(self):
        policy = CancellationPolicy()
        appt = make_appointment(AppointmentStatus.CONFIRMED)
        result = policy.can_cancel(appt, "admin", CURRENT_TIME)
        assert result.is_ok is True


class TestCancellationPolicyStaff:
    def test_staff_can_cancel_own_active_appointment(self):
        policy = CancellationPolicy()
        staff_id = uuid.uuid4()
        appt = make_appointment(AppointmentStatus.SCHEDULED, staff_id=staff_id)
        result = policy.can_cancel(appt, "staff", CURRENT_TIME, actor_id=staff_id)
        assert result.is_ok is True

    def test_staff_cannot_cancel_others_appointment(self):
        policy = CancellationPolicy()
        appt = make_appointment(AppointmentStatus.SCHEDULED)
        other_staff_id = uuid.uuid4()
        result = policy.can_cancel(appt, "staff", CURRENT_TIME, actor_id=other_staff_id)
        assert result.is_ok is False


class TestCancellationPolicyClient:
    def test_client_can_cancel_active_appointment(self):
        policy = CancellationPolicy()
        appt = make_appointment(AppointmentStatus.SCHEDULED)
        result = policy.can_cancel(appt, "client", CURRENT_TIME)
        assert result.is_ok is True

    def test_client_can_cancel_confirmed_appointment(self):
        policy = CancellationPolicy()
        appt = make_appointment(AppointmentStatus.CONFIRMED)
        result = policy.can_cancel(appt, "client", CURRENT_TIME)
        assert result.is_ok is True


class TestCancellationPolicyAlreadyCancelled:
    def test_already_cancelled_denied(self):
        policy = CancellationPolicy()
        appt = make_appointment(AppointmentStatus.CANCELLED)
        result = policy.can_cancel(appt, "admin", CURRENT_TIME)
        assert result.is_ok is False
        assert len(result.violations) > 0

    def test_completed_appointment_denied(self):
        policy = CancellationPolicy()
        appt = make_appointment(AppointmentStatus.COMPLETED)
        result = policy.can_cancel(appt, "admin", CURRENT_TIME)
        assert result.is_ok is False

    def test_no_show_appointment_denied(self):
        policy = CancellationPolicy()
        appt = make_appointment(AppointmentStatus.NO_SHOW)
        result = policy.can_cancel(appt, "client", CURRENT_TIME)
        assert result.is_ok is False
