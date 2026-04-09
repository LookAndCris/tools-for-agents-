"""Tests for AppointmentStatus value object."""
import pytest
from domain.value_objects.appointment_status import AppointmentStatus
from domain.exceptions import InvalidStateTransitionError


class TestAppointmentStatusTransitions:
    def test_scheduled_can_transition_to_confirmed(self):
        assert AppointmentStatus.SCHEDULED.can_transition_to(AppointmentStatus.CONFIRMED) is True

    def test_scheduled_can_transition_to_cancelled(self):
        assert AppointmentStatus.SCHEDULED.can_transition_to(AppointmentStatus.CANCELLED) is True

    def test_scheduled_cannot_transition_to_completed(self):
        assert AppointmentStatus.SCHEDULED.can_transition_to(AppointmentStatus.COMPLETED) is False

    def test_confirmed_can_transition_to_in_progress(self):
        assert AppointmentStatus.CONFIRMED.can_transition_to(AppointmentStatus.IN_PROGRESS) is True

    def test_in_progress_can_transition_to_completed(self):
        assert AppointmentStatus.IN_PROGRESS.can_transition_to(AppointmentStatus.COMPLETED) is True

    def test_in_progress_can_transition_to_no_show(self):
        assert AppointmentStatus.IN_PROGRESS.can_transition_to(AppointmentStatus.NO_SHOW) is True

    def test_completed_cannot_transition_to_anything(self):
        for target in AppointmentStatus:
            assert AppointmentStatus.COMPLETED.can_transition_to(target) is False

    def test_cancelled_cannot_transition_to_anything(self):
        for target in AppointmentStatus:
            assert AppointmentStatus.CANCELLED.can_transition_to(target) is False

    def test_is_terminal_for_completed(self):
        assert AppointmentStatus.COMPLETED.is_terminal() is True

    def test_is_terminal_for_cancelled(self):
        assert AppointmentStatus.CANCELLED.is_terminal() is True

    def test_is_terminal_for_no_show(self):
        assert AppointmentStatus.NO_SHOW.is_terminal() is True

    def test_is_not_terminal_for_scheduled(self):
        assert AppointmentStatus.SCHEDULED.is_terminal() is False
