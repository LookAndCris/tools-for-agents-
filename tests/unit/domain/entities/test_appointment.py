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


class TestMarkCreated:
    """Tests for the new mark_created() domain method."""

    def test_mark_created_appends_created_event(self):
        """mark_created() appends an event with type 'created'."""
        appt = make_appointment()
        appt.mark_created()
        event_types = [e["type"] for e in appt.events]
        assert "created" in event_types

    def test_mark_created_with_performed_by_stores_actor(self):
        """mark_created(performed_by=...) stores the actor UUID in event details."""
        actor_id = uuid.uuid4()
        appt = make_appointment()
        appt.mark_created(performed_by=actor_id)
        created_events = [e for e in appt.events if e["type"] == "created"]
        assert len(created_events) == 1
        assert created_events[0]["details"]["performed_by"] == actor_id

    def test_mark_created_without_performed_by_details_are_none_or_absent(self):
        """mark_created() without actor stores None or omits performed_by."""
        appt = make_appointment()
        appt.mark_created()
        created_events = [e for e in appt.events if e["type"] == "created"]
        assert len(created_events) == 1
        # performed_by should be None (or absent) when not provided
        details = created_events[0].get("details", {})
        assert details.get("performed_by") is None

    def test_mark_created_default_performed_by_is_none(self):
        """mark_created() has no required parameters — backward compat."""
        appt = make_appointment()
        appt.mark_created()  # should not raise
        assert len(appt.events) == 1


class TestCancelAudit:
    """Tests for audit enrichment of cancel() method."""

    def test_cancel_stores_performed_by_in_event_details(self):
        """cancel() stores performed_by in event details dict."""
        actor_id = uuid.uuid4()
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        appt.cancel(cancelled_by=actor_id, reason="test reason")
        cancel_events = [e for e in appt.events if e["type"] == "cancelled"]
        assert len(cancel_events) == 1
        details = cancel_events[0].get("details", {})
        assert details.get("performed_by") == actor_id

    def test_cancel_stores_reason_in_event_details(self):
        """cancel() stores reason in event details dict."""
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        appt.cancel(reason="No longer needed")
        cancel_events = [e for e in appt.events if e["type"] == "cancelled"]
        assert len(cancel_events) == 1
        details = cancel_events[0].get("details", {})
        assert details.get("reason") == "No longer needed"

    def test_cancel_without_actor_stores_none_performed_by(self):
        """cancel() without actor stores None for performed_by."""
        appt = make_appointment(status=AppointmentStatus.SCHEDULED)
        appt.cancel()
        cancel_events = [e for e in appt.events if e["type"] == "cancelled"]
        assert len(cancel_events) == 1
        details = cancel_events[0].get("details", {})
        assert details.get("performed_by") is None


class TestRescheduleAudit:
    """Tests for audit enrichment of reschedule() method."""

    def test_reschedule_captures_old_slot_before_overwrite(self):
        """reschedule() captures old_start/old_end in event details BEFORE overwriting."""
        original_start = utc(2026, 4, 10, 10)
        original_end = utc(2026, 4, 10, 11)
        original_slot = TimeSlot(start=original_start, end=original_end)
        appt = make_appointment(time_slot=original_slot)

        new_slot = make_slot(14, 15)
        appt.reschedule(new_slot)

        reschedule_events = [e for e in appt.events if e["type"] == "rescheduled"]
        assert len(reschedule_events) == 1
        details = reschedule_events[0].get("details", {})
        assert details.get("old_start") == original_start
        assert details.get("old_end") == original_end

    def test_reschedule_stores_new_slot_in_event_details(self):
        """reschedule() stores new_start/new_end in event details."""
        appt = make_appointment()
        new_slot = make_slot(14, 15)
        appt.reschedule(new_slot)

        reschedule_events = [e for e in appt.events if e["type"] == "rescheduled"]
        assert len(reschedule_events) == 1
        details = reschedule_events[0].get("details", {})
        assert details.get("new_start") == new_slot.start
        assert details.get("new_end") == new_slot.end

    def test_reschedule_stores_performed_by_in_event_details(self):
        """reschedule(performed_by=...) stores the actor in event details."""
        actor_id = uuid.uuid4()
        appt = make_appointment()
        new_slot = make_slot(14, 15)
        appt.reschedule(new_slot, performed_by=actor_id)

        reschedule_events = [e for e in appt.events if e["type"] == "rescheduled"]
        assert len(reschedule_events) == 1
        details = reschedule_events[0].get("details", {})
        assert details.get("performed_by") == actor_id

    def test_reschedule_without_actor_stores_none_performed_by(self):
        """reschedule() without performed_by stores None."""
        appt = make_appointment()
        new_slot = make_slot(14, 15)
        appt.reschedule(new_slot)

        reschedule_events = [e for e in appt.events if e["type"] == "rescheduled"]
        assert len(reschedule_events) == 1
        details = reschedule_events[0].get("details", {})
        assert details.get("performed_by") is None

    def test_reschedule_old_slot_differs_from_new_slot(self):
        """Verify old_start != new_start after reschedule (smoke test for capture order)."""
        original_start = utc(2026, 4, 10, 10)
        original_slot = TimeSlot(start=original_start, end=utc(2026, 4, 10, 11))
        appt = make_appointment(time_slot=original_slot)

        new_start = utc(2026, 4, 10, 14)
        new_slot = TimeSlot(start=new_start, end=utc(2026, 4, 10, 15))
        appt.reschedule(new_slot)

        reschedule_events = [e for e in appt.events if e["type"] == "rescheduled"]
        details = reschedule_events[0]["details"]
        assert details["old_start"] != details["new_start"]
        assert details["old_start"] == original_start
        assert details["new_start"] == new_start
