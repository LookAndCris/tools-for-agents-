"""Tests for the Appointment entity."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from domain.value_objects.time_slot import TimeSlot
from domain.value_objects.appointment_status import AppointmentStatus
from domain.exceptions import InvalidStatusTransitionError
from domain.entities.appointment import Appointment


def utc(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def make_slot(start_hour: int = 10, end_hour: int = 11) -> TimeSlot:
    return TimeSlot(
        start=utc(2026, 4, 10, start_hour),
        end=utc(2026, 4, 10, end_hour),
    )


def make_appointment(**kwargs) -> Appointment:
    defaults = dict(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        staff_id=uuid.uuid4(),
        service_id=uuid.uuid4(),
        time_slot=make_slot(),
        status=AppointmentStatus.SCHEDULED,
    )
    defaults.update(kwargs)
    return Appointment(**defaults)


class TestAppointmentCreation:
    def test_valid_creation(self):
        appt = make_appointment()
        assert appt.status == AppointmentStatus.SCHEDULED

    def test_stores_time_slot(self):
        slot = make_slot(10, 11)
        appt = make_appointment(time_slot=slot)
        assert appt.time_slot == slot

    def test_is_active_scheduled(self):
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        assert appt.is_active is True

    def test_is_active_confirmed(self):
        appt = make_appointment(status=AppointmentStatus.CONFIRMED)
        assert appt.is_active is True

    def test_is_not_active_cancelled(self):
        appt = make_appointment(status=AppointmentStatus.CANCELLED)
        assert appt.is_active is False

    def test_is_not_active_completed(self):
        appt = make_appointment(status=AppointmentStatus.COMPLETED)
        assert appt.is_active is False

    def test_is_not_active_no_show(self):
        appt = make_appointment(status=AppointmentStatus.NO_SHOW)
        assert appt.is_active is False


class TestAppointmentConfirm:
    def test_confirm_scheduled_appointment(self):
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        appt.confirm()
        assert appt.status == AppointmentStatus.CONFIRMED

    def test_confirm_already_confirmed_raises(self):
        appt = make_appointment(status=AppointmentStatus.CONFIRMED)
        with pytest.raises(InvalidStatusTransitionError):
            appt.confirm()

    def test_confirm_cancelled_raises(self):
        appt = make_appointment(status=AppointmentStatus.CANCELLED)
        with pytest.raises(InvalidStatusTransitionError):
            appt.confirm()


class TestAppointmentCancel:
    def test_cancel_scheduled_appointment(self):
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        appt.cancel()
        assert appt.status == AppointmentStatus.CANCELLED

    def test_cancel_confirmed_appointment(self):
        appt = make_appointment(status=AppointmentStatus.CONFIRMED)
        appt.cancel()
        assert appt.status == AppointmentStatus.CANCELLED

    def test_cancel_already_cancelled_raises(self):
        appt = make_appointment(status=AppointmentStatus.CANCELLED)
        with pytest.raises(InvalidStatusTransitionError):
            appt.cancel()

    def test_cancel_completed_raises(self):
        appt = make_appointment(status=AppointmentStatus.COMPLETED)
        with pytest.raises(InvalidStatusTransitionError):
            appt.cancel()


class TestAppointmentReschedule:
    def test_reschedule_scheduled_appointment(self):
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        new_slot = make_slot(14, 15)
        appt.reschedule(new_slot)
        assert appt.time_slot == new_slot
        assert appt.status == AppointmentStatus.SCHEDULED

    def test_reschedule_confirmed_resets_to_scheduled(self):
        appt = make_appointment(status=AppointmentStatus.CONFIRMED)
        new_slot = make_slot(14, 15)
        appt.reschedule(new_slot)
        assert appt.time_slot == new_slot
        assert appt.status == AppointmentStatus.SCHEDULED

    def test_reschedule_cancelled_raises(self):
        appt = make_appointment(status=AppointmentStatus.CANCELLED)
        with pytest.raises(InvalidStatusTransitionError):
            appt.reschedule(make_slot(14, 15))
