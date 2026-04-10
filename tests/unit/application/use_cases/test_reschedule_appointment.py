"""Unit tests for RescheduleAppointmentUseCase (Task 4.3 - RED phase)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from domain.repositories.appointment_repository import AppointmentRepository
from domain.repositories.staff_availability_repository import StaffAvailabilityRepository
from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
from domain.value_objects.appointment_status import AppointmentStatus
from domain.value_objects.time_slot import TimeSlot
from tests.factories import AppointmentFactory, ServiceFactory


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc)


class TestRescheduleAppointmentUseCase:
    """Unit tests for RescheduleAppointmentUseCase."""

    @pytest.fixture
    def appointment_repo(self):
        return AsyncMock(spec=AppointmentRepository)

    @pytest.fixture
    def availability_repo(self):
        return AsyncMock(spec=StaffAvailabilityRepository)

    @pytest.fixture
    def time_off_repo(self):
        return AsyncMock(spec=StaffTimeOffRepository)

    @pytest.fixture
    def appointment_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def staff_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def service_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def service(self, service_id):
        return ServiceFactory(
            id=service_id,
            duration__duration_minutes=60,
            duration__buffer_before=0,
            duration__buffer_after=0,
        )

    @pytest.fixture
    def appointment(self, appointment_id, staff_id, service_id):
        return AppointmentFactory(
            id=appointment_id,
            staff_id=staff_id,
            service_id=service_id,
            status=AppointmentStatus.SCHEDULED,
            time_slot=TimeSlot(
                start=_utc(2026, 4, 10, 10, 0),
                end=_utc(2026, 4, 10, 11, 0),
            ),
        )

    @pytest.fixture
    def availability_window(self):
        return TimeSlot(
            start=_utc(2026, 4, 11, 9, 0),
            end=_utc(2026, 4, 11, 18, 0),
        )

    @pytest.fixture
    def new_start_time(self):
        return _utc(2026, 4, 11, 14, 0)

    @pytest.fixture
    def caller(self):
        from application.dto.user_context import UserContext

        return UserContext(user_id=uuid.uuid4(), role="client", client_id=uuid.uuid4())

    @pytest.fixture
    def cmd(self, appointment_id, new_start_time):
        from application.dto.commands import RescheduleAppointmentCommand

        return RescheduleAppointmentCommand(
            appointment_id=appointment_id,
            new_start_time=new_start_time,
        )

    @pytest.fixture
    def service_repo(self):
        from unittest.mock import AsyncMock

        from domain.repositories.service_repository import ServiceRepository

        return AsyncMock(spec=ServiceRepository)

    @pytest.fixture
    def uc(self, appointment_repo, service_repo, availability_repo, time_off_repo):
        from application.use_cases.reschedule_appointment import RescheduleAppointmentUseCase

        return RescheduleAppointmentUseCase(
            appointment_repo=appointment_repo,
            service_repo=service_repo,
            availability_repo=availability_repo,
            time_off_repo=time_off_repo,
        )

    # ------------------------------------------------------------------ #
    # Happy path
    # ------------------------------------------------------------------ #

    async def test_reschedules_appointment_successfully(
        self,
        uc,
        cmd,
        caller,
        appointment,
        service,
        availability_window,
        appointment_repo,
        service_repo,
        availability_repo,
        time_off_repo,
    ):
        """Successful reschedule returns AppointmentResponse with new time."""
        from application.dto.responses import AppointmentResponse

        appointment_repo.get_by_id.return_value = appointment
        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = [availability_window]
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []
        appointment_repo.save.side_effect = lambda a: a

        result = await uc.execute(cmd, caller)

        assert isinstance(result, AppointmentResponse)
        assert result.start_time == cmd.new_start_time
        assert result.status == "scheduled"

    async def test_reschedule_saves_updated_appointment(
        self,
        uc,
        cmd,
        caller,
        appointment,
        service,
        availability_window,
        appointment_repo,
        service_repo,
        availability_repo,
        time_off_repo,
    ):
        """Appointment is saved exactly once after rescheduling."""
        appointment_repo.get_by_id.return_value = appointment
        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = [availability_window]
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []
        appointment_repo.save.side_effect = lambda a: a

        await uc.execute(cmd, caller)

        appointment_repo.save.assert_called_once()

    async def test_rescheduled_appointment_has_new_slot(
        self,
        uc,
        cmd,
        caller,
        appointment,
        service,
        availability_window,
        appointment_repo,
        service_repo,
        availability_repo,
        time_off_repo,
        new_start_time,
    ):
        """Appointment entity has the new time slot after rescheduling."""
        appointment_repo.get_by_id.return_value = appointment
        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = [availability_window]
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []

        saved_appointment = None

        async def capture(appt):
            nonlocal saved_appointment
            saved_appointment = appt
            return appt

        appointment_repo.save.side_effect = capture

        await uc.execute(cmd, caller)

        assert saved_appointment is not None
        assert saved_appointment.time_slot.start == new_start_time

    # ------------------------------------------------------------------ #
    # Appointment not found
    # ------------------------------------------------------------------ #

    async def test_raises_not_found_when_appointment_missing(
        self, uc, cmd, caller, appointment_repo
    ):
        """NotFoundError raised when appointment does not exist."""
        from application.exceptions import NotFoundError

        appointment_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await uc.execute(cmd, caller)

        assert "APPOINTMENT" in exc_info.value.code
        appointment_repo.save.assert_not_called()

    # ------------------------------------------------------------------ #
    # Availability policy fail → StaffUnavailableError
    # ------------------------------------------------------------------ #

    async def test_raises_staff_unavailable_when_new_slot_outside_availability(
        self,
        uc,
        cmd,
        caller,
        appointment,
        service,
        appointment_repo,
        service_repo,
        availability_repo,
        time_off_repo,
    ):
        """StaffUnavailableError raised when new slot is outside availability."""
        from application.exceptions import StaffUnavailableError

        appointment_repo.get_by_id.return_value = appointment
        service_repo.get_by_id.return_value = service
        # No availability windows for new date
        availability_repo.get_by_staff_and_day.return_value = []
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []

        with pytest.raises(StaffUnavailableError):
            await uc.execute(cmd, caller)

        appointment_repo.save.assert_not_called()

    # ------------------------------------------------------------------ #
    # Overlap policy fail → BookingConflictError
    # ------------------------------------------------------------------ #

    async def test_raises_booking_conflict_when_new_slot_overlaps(
        self,
        uc,
        cmd,
        caller,
        appointment,
        service,
        availability_window,
        appointment_repo,
        service_repo,
        availability_repo,
        time_off_repo,
        staff_id,
        service_id,
        new_start_time,
    ):
        """BookingConflictError raised when new slot overlaps an existing appointment."""
        from datetime import timedelta

        from application.exceptions import BookingConflictError

        # Existing appointment at the same new time
        conflict_appt = AppointmentFactory(
            staff_id=staff_id,
            service_id=service_id,
            time_slot=TimeSlot(
                start=new_start_time,
                end=new_start_time + timedelta(hours=1),
            ),
        )

        appointment_repo.get_by_id.return_value = appointment
        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = [availability_window]
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = [conflict_appt]

        with pytest.raises(BookingConflictError):
            await uc.execute(cmd, caller)

        appointment_repo.save.assert_not_called()

    async def test_reschedule_threads_caller_user_id_into_event(
        self,
        uc,
        cmd,
        caller,
        appointment,
        service,
        availability_window,
        appointment_repo,
        service_repo,
        availability_repo,
        time_off_repo,
    ):
        """reschedule() event details contain caller.user_id as performed_by."""
        appointment_repo.get_by_id.return_value = appointment
        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = [availability_window]
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []

        saved_appointment = None

        async def capture(appt):
            nonlocal saved_appointment
            saved_appointment = appt
            return appt

        appointment_repo.save.side_effect = capture

        await uc.execute(cmd, caller)

        assert saved_appointment is not None
        reschedule_events = [e for e in saved_appointment.events if e["type"] == "rescheduled"]
        assert len(reschedule_events) == 1
        assert reschedule_events[0]["details"]["performed_by"] == caller.user_id
