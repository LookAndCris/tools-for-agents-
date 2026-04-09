"""Additional tests for Appointment aggregate behaviors (start, complete, mark_no_show, events)."""
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
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        staff_id=uuid.uuid4(),
        service_id=uuid.uuid4(),
        time_slot=make_slot(),
        status=AppointmentStatus.SCHEDULED,
        notes=None,
        created_by=None,
        cancelled_by=None,
        cancelled_at=None,
        cancellation_reason=None,
        events=[],
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    return Appointment(**defaults)


class TestAppointmentStart:
    def test_start_from_confirmed(self):
        appt = make_appointment(status=AppointmentStatus.CONFIRMED)
        appt.start()
        assert appt.status == AppointmentStatus.IN_PROGRESS

    def test_start_from_scheduled_raises(self):
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        with pytest.raises(InvalidStatusTransitionError):
            appt.start()

    def test_start_appends_event(self):
        appt = make_appointment(status=AppointmentStatus.CONFIRMED)
        appt.start()
        assert len(appt.events) == 1
        assert appt.events[0]["type"] == "started"
        assert "timestamp" in appt.events[0]


class TestAppointmentComplete:
    def test_complete_from_in_progress(self):
        appt = make_appointment(status=AppointmentStatus.IN_PROGRESS)
        appt.complete()
        assert appt.status == AppointmentStatus.COMPLETED

    def test_complete_from_scheduled_raises(self):
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        with pytest.raises(InvalidStatusTransitionError):
            appt.complete()

    def test_complete_appends_event(self):
        appt = make_appointment(status=AppointmentStatus.IN_PROGRESS)
        appt.complete()
        assert appt.events[-1]["type"] == "completed"


class TestAppointmentMarkNoShow:
    def test_no_show_from_in_progress(self):
        appt = make_appointment(status=AppointmentStatus.IN_PROGRESS)
        appt.mark_no_show()
        assert appt.status == AppointmentStatus.NO_SHOW

    def test_no_show_from_scheduled_raises(self):
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        with pytest.raises(InvalidStatusTransitionError):
            appt.mark_no_show()

    def test_no_show_appends_event(self):
        appt = make_appointment(status=AppointmentStatus.IN_PROGRESS)
        appt.mark_no_show()
        assert appt.events[-1]["type"] == "no_show"


class TestAppointmentCancelWithDetails:
    def test_cancel_records_cancelled_by(self):
        actor = uuid.uuid4()
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        appt.cancel(cancelled_by=actor, reason="Changed mind")
        assert appt.cancelled_by == actor

    def test_cancel_records_reason(self):
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        appt.cancel(reason="No longer needed")
        assert appt.cancellation_reason == "No longer needed"

    def test_cancel_sets_cancelled_at(self):
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        appt.cancel()
        assert appt.cancelled_at is not None

    def test_cancel_appends_event(self):
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        appt.cancel()
        assert appt.events[-1]["type"] == "cancelled"


class TestAppointmentIsActiveExtended:
    def test_in_progress_is_active(self):
        appt = make_appointment(status=AppointmentStatus.IN_PROGRESS)
        assert appt.is_active is True


class TestAppointmentEventsTracked:
    def test_events_tracked_across_transitions(self):
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        appt.confirm()
        appt.start()
        appt.complete()
        assert len(appt.events) == 3
        types = [e["type"] for e in appt.events]
        assert types == ["confirmed", "started", "completed"]

    def test_reschedule_appends_event(self):
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        appt.reschedule(make_slot(14, 15))
        assert appt.events[-1]["type"] == "rescheduled"
