"""Unit tests for CreateAppointmentUseCase (Task 4.1 - RED phase)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from domain.repositories.appointment_repository import AppointmentRepository
from domain.repositories.service_repository import ServiceRepository
from domain.repositories.staff_availability_repository import StaffAvailabilityRepository
from domain.repositories.staff_repository import StaffRepository
from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
from domain.value_objects.time_slot import TimeSlot
from tests.factories import AppointmentFactory, ServiceFactory, StaffFactory


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc)


class TestCreateAppointmentUseCase:
    """Unit tests for CreateAppointmentUseCase."""

    @pytest.fixture
    def service_repo(self):
        return AsyncMock(spec=ServiceRepository)

    @pytest.fixture
    def staff_repo(self):
        return AsyncMock(spec=StaffRepository)

    @pytest.fixture
    def availability_repo(self):
        return AsyncMock(spec=StaffAvailabilityRepository)

    @pytest.fixture
    def time_off_repo(self):
        return AsyncMock(spec=StaffTimeOffRepository)

    @pytest.fixture
    def appointment_repo(self):
        return AsyncMock(spec=AppointmentRepository)

    @pytest.fixture
    def service_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def staff_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def client_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def start_time(self):
        return _utc(2026, 4, 10, 10, 0)

    @pytest.fixture
    def service(self, service_id):
        return ServiceFactory(
            id=service_id,
            duration__duration_minutes=60,
            duration__buffer_before=0,
            duration__buffer_after=0,
        )

    @pytest.fixture
    def staff(self, staff_id, service_id):
        return StaffFactory(id=staff_id, service_ids=frozenset({service_id}))

    @pytest.fixture
    def availability_window(self, start_time):
        """Full-day window covering the test appointment start time."""
        return TimeSlot(
            start=_utc(2026, 4, 10, 9, 0),
            end=_utc(2026, 4, 10, 18, 0),
        )

    @pytest.fixture
    def uc(
        self, service_repo, staff_repo, availability_repo, time_off_repo, appointment_repo
    ):
        from application.use_cases.create_appointment import CreateAppointmentUseCase

        return CreateAppointmentUseCase(
            service_repo=service_repo,
            staff_repo=staff_repo,
            availability_repo=availability_repo,
            time_off_repo=time_off_repo,
            appointment_repo=appointment_repo,
        )

    @pytest.fixture
    def cmd(self, client_id, staff_id, service_id, start_time):
        from application.dto.commands import CreateAppointmentCommand

        return CreateAppointmentCommand(
            client_id=client_id,
            staff_id=staff_id,
            service_id=service_id,
            start_time=start_time,
        )

    @pytest.fixture
    def caller(self, client_id):
        from application.dto.user_context import UserContext

        return UserContext(user_id=uuid.uuid4(), role="client", client_id=client_id)

    # ------------------------------------------------------------------ #
    # Happy path
    # ------------------------------------------------------------------ #

    async def test_creates_appointment_successfully(
        self,
        uc,
        cmd,
        caller,
        service,
        staff,
        availability_window,
        service_repo,
        staff_repo,
        availability_repo,
        time_off_repo,
        appointment_repo,
    ):
        """Successful appointment creation returns AppointmentResponse."""
        from application.dto.responses import AppointmentResponse

        service_repo.get_by_id.return_value = service
        staff_repo.get_by_id.return_value = staff
        availability_repo.get_by_staff_and_day.return_value = [availability_window]
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []
        appointment_repo.save.side_effect = lambda a: a

        result = await uc.execute(cmd, caller)

        assert isinstance(result, AppointmentResponse)
        assert result.client_id == cmd.client_id
        assert result.staff_id == cmd.staff_id
        assert result.service_id == cmd.service_id
        assert result.start_time == cmd.start_time
        assert result.status == "scheduled"

    async def test_appointment_saved_via_repo(
        self,
        uc,
        cmd,
        caller,
        service,
        staff,
        availability_window,
        service_repo,
        staff_repo,
        availability_repo,
        time_off_repo,
        appointment_repo,
    ):
        """Appointment is saved exactly once via appointment_repo.save()."""
        service_repo.get_by_id.return_value = service
        staff_repo.get_by_id.return_value = staff
        availability_repo.get_by_staff_and_day.return_value = [availability_window]
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []
        appointment_repo.save.side_effect = lambda a: a

        await uc.execute(cmd, caller)

        appointment_repo.save.assert_called_once()

    async def test_new_appointment_has_scheduled_status(
        self,
        uc,
        cmd,
        caller,
        service,
        staff,
        availability_window,
        service_repo,
        staff_repo,
        availability_repo,
        time_off_repo,
        appointment_repo,
    ):
        """New appointment is created with SCHEDULED status."""
        from domain.value_objects.appointment_status import AppointmentStatus

        service_repo.get_by_id.return_value = service
        staff_repo.get_by_id.return_value = staff
        availability_repo.get_by_staff_and_day.return_value = [availability_window]
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []

        saved_appointment = None

        async def capture_save(appt):
            nonlocal saved_appointment
            saved_appointment = appt
            return appt

        appointment_repo.save.side_effect = capture_save

        await uc.execute(cmd, caller)

        assert saved_appointment is not None
        assert saved_appointment.status == AppointmentStatus.SCHEDULED

    async def test_appointment_domain_events_appended(
        self,
        uc,
        cmd,
        caller,
        service,
        staff,
        availability_window,
        service_repo,
        staff_repo,
        availability_repo,
        time_off_repo,
        appointment_repo,
    ):
        """Appointment entity has domain events after creation."""
        service_repo.get_by_id.return_value = service
        staff_repo.get_by_id.return_value = staff
        availability_repo.get_by_staff_and_day.return_value = [availability_window]
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []

        saved_appointment = None

        async def capture_save(appt):
            nonlocal saved_appointment
            saved_appointment = appt
            return appt

        appointment_repo.save.side_effect = capture_save

        await uc.execute(cmd, caller)

        # The appointment entity should exist and have at least an empty events list
        assert saved_appointment is not None
        assert isinstance(saved_appointment.events, list)

    # ------------------------------------------------------------------ #
    # Service not found
    # ------------------------------------------------------------------ #

    async def test_raises_not_found_when_service_missing(
        self, uc, cmd, caller, service_repo, staff_repo, appointment_repo
    ):
        """NotFoundError raised when service does not exist."""
        from application.exceptions import NotFoundError

        service_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await uc.execute(cmd, caller)

        assert "SERVICE" in exc_info.value.code
        staff_repo.get_by_id.assert_not_called()
        appointment_repo.save.assert_not_called()

    # ------------------------------------------------------------------ #
    # Staff not found
    # ------------------------------------------------------------------ #

    async def test_raises_not_found_when_staff_missing(
        self, uc, cmd, caller, service, service_repo, staff_repo, appointment_repo
    ):
        """NotFoundError raised when staff does not exist."""
        from application.exceptions import NotFoundError

        service_repo.get_by_id.return_value = service
        staff_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await uc.execute(cmd, caller)

        assert "STAFF" in exc_info.value.code
        appointment_repo.save.assert_not_called()

    # ------------------------------------------------------------------ #
    # Availability policy violation → StaffUnavailableError
    # ------------------------------------------------------------------ #

    async def test_raises_staff_unavailable_when_outside_availability(
        self,
        uc,
        cmd,
        caller,
        service,
        staff,
        service_repo,
        staff_repo,
        availability_repo,
        time_off_repo,
        appointment_repo,
    ):
        """StaffUnavailableError raised when availability policy fails."""
        from application.exceptions import StaffUnavailableError

        service_repo.get_by_id.return_value = service
        staff_repo.get_by_id.return_value = staff
        # No availability windows → staff is unavailable
        availability_repo.get_by_staff_and_day.return_value = []
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []

        with pytest.raises(StaffUnavailableError):
            await uc.execute(cmd, caller)

        appointment_repo.save.assert_not_called()

    async def test_raises_staff_unavailable_when_time_off_covers_slot(
        self,
        uc,
        cmd,
        caller,
        service,
        staff,
        availability_window,
        service_repo,
        staff_repo,
        availability_repo,
        time_off_repo,
        appointment_repo,
    ):
        """StaffUnavailableError when time-off fully blocks the slot."""
        from application.exceptions import StaffUnavailableError

        full_block = TimeSlot(
            start=_utc(2026, 4, 10, 8, 0),
            end=_utc(2026, 4, 10, 18, 0),
        )
        service_repo.get_by_id.return_value = service
        staff_repo.get_by_id.return_value = staff
        availability_repo.get_by_staff_and_day.return_value = [availability_window]
        time_off_repo.get_by_staff_and_range.return_value = [full_block]
        appointment_repo.find_by_staff_and_date_range.return_value = []

        with pytest.raises(StaffUnavailableError):
            await uc.execute(cmd, caller)

        appointment_repo.save.assert_not_called()

    # ------------------------------------------------------------------ #
    # Overlap policy violation → BookingConflictError
    # ------------------------------------------------------------------ #

    async def test_raises_booking_conflict_when_slot_overlaps_existing(
        self,
        uc,
        cmd,
        caller,
        service,
        staff,
        availability_window,
        service_repo,
        staff_repo,
        availability_repo,
        time_off_repo,
        appointment_repo,
        staff_id,
        service_id,
        client_id,
    ):
        """BookingConflictError raised when an existing appointment overlaps."""
        from application.exceptions import BookingConflictError

        # Existing appointment occupies 10:00-11:00 — same as the requested slot
        existing = AppointmentFactory(
            staff_id=staff_id,
            service_id=service_id,
            time_slot=TimeSlot(
                start=_utc(2026, 4, 10, 10, 0),
                end=_utc(2026, 4, 10, 11, 0),
            ),
        )

        service_repo.get_by_id.return_value = service
        staff_repo.get_by_id.return_value = staff
        availability_repo.get_by_staff_and_day.return_value = [availability_window]
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = [existing]

        with pytest.raises(BookingConflictError):
            await uc.execute(cmd, caller)

        appointment_repo.save.assert_not_called()
