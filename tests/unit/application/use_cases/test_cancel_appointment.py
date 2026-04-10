"""Unit tests for CancelAppointmentUseCase (Task 4.3 - RED phase)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from domain.repositories.appointment_repository import AppointmentRepository
from domain.value_objects.appointment_status import AppointmentStatus
from domain.value_objects.time_slot import TimeSlot
from tests.factories import AppointmentFactory


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc)


class TestCancelAppointmentUseCase:
    """Unit tests for CancelAppointmentUseCase."""

    @pytest.fixture
    def appointment_repo(self):
        return AsyncMock(spec=AppointmentRepository)

    @pytest.fixture
    def appointment_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def appointment(self, appointment_id):
        return AppointmentFactory(
            id=appointment_id,
            status=AppointmentStatus.SCHEDULED,
            time_slot=TimeSlot(
                start=_utc(2026, 4, 10, 10, 0),
                end=_utc(2026, 4, 10, 11, 0),
            ),
        )

    @pytest.fixture
    def caller(self):
        from application.dto.user_context import UserContext

        return UserContext(user_id=uuid.uuid4(), role="client", client_id=uuid.uuid4())

    @pytest.fixture
    def admin_caller(self):
        from application.dto.user_context import UserContext

        return UserContext(user_id=uuid.uuid4(), role="admin")

    @pytest.fixture
    def uc(self, appointment_repo):
        from application.use_cases.cancel_appointment import CancelAppointmentUseCase

        return CancelAppointmentUseCase(appointment_repo=appointment_repo)

    @pytest.fixture
    def cmd(self, appointment_id):
        from application.dto.commands import CancelAppointmentCommand

        return CancelAppointmentCommand(
            appointment_id=appointment_id,
            reason="Changed my mind",
        )

    # ------------------------------------------------------------------ #
    # Happy path
    # ------------------------------------------------------------------ #

    async def test_cancels_appointment_successfully(
        self, uc, cmd, caller, appointment, appointment_repo
    ):
        """Successful cancellation returns AppointmentResponse with cancelled status."""
        from application.dto.responses import AppointmentResponse

        appointment_repo.get_by_id.return_value = appointment
        appointment_repo.save.side_effect = lambda a: a

        result = await uc.execute(cmd, caller)

        assert isinstance(result, AppointmentResponse)
        assert result.status == "cancelled"

    async def test_cancel_saves_updated_appointment(
        self, uc, cmd, caller, appointment, appointment_repo
    ):
        """Appointment is saved exactly once after cancellation."""
        appointment_repo.get_by_id.return_value = appointment
        appointment_repo.save.side_effect = lambda a: a

        await uc.execute(cmd, caller)

        appointment_repo.save.assert_called_once()

    async def test_cancel_stores_reason_on_entity(
        self, uc, cmd, caller, appointment, appointment_repo
    ):
        """Cancellation reason is stored on the appointment entity."""
        appointment_repo.get_by_id.return_value = appointment

        saved_appointment = None

        async def capture(appt):
            nonlocal saved_appointment
            saved_appointment = appt
            return appt

        appointment_repo.save.side_effect = capture

        await uc.execute(cmd, caller)

        assert saved_appointment is not None
        assert saved_appointment.cancellation_reason == cmd.reason

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
    # CancellationPolicy denied → CancellationDeniedError
    # ------------------------------------------------------------------ #

    async def test_raises_cancellation_denied_for_terminal_appointment(
        self, uc, cmd, caller, appointment_id, appointment_repo
    ):
        """CancellationDeniedError raised when appointment is already in terminal state."""
        from application.exceptions import CancellationDeniedError

        completed_appt = AppointmentFactory(
            id=appointment_id,
            status=AppointmentStatus.COMPLETED,
            time_slot=TimeSlot(
                start=_utc(2026, 4, 9, 10, 0),
                end=_utc(2026, 4, 9, 11, 0),
            ),
        )
        appointment_repo.get_by_id.return_value = completed_appt

        with pytest.raises(CancellationDeniedError):
            await uc.execute(cmd, caller)

        appointment_repo.save.assert_not_called()

    async def test_raises_cancellation_denied_for_wrong_staff(
        self, uc, cmd, appointment_id, appointment_repo
    ):
        """CancellationDeniedError raised when staff tries to cancel another's appointment."""
        from application.dto.user_context import UserContext
        from application.exceptions import CancellationDeniedError

        # Staff member trying to cancel someone else's appointment
        different_staff_id = uuid.uuid4()
        staff_caller = UserContext(
            user_id=uuid.uuid4(), role="staff", staff_id=different_staff_id
        )

        appt = AppointmentFactory(
            id=appointment_id,
            staff_id=uuid.uuid4(),  # Different staff member owns this appointment
            status=AppointmentStatus.SCHEDULED,
            time_slot=TimeSlot(
                start=_utc(2026, 4, 10, 10, 0),
                end=_utc(2026, 4, 10, 11, 0),
            ),
        )
        appointment_repo.get_by_id.return_value = appt

        with pytest.raises(CancellationDeniedError):
            await uc.execute(cmd, staff_caller)

        appointment_repo.save.assert_not_called()

    async def test_cancel_threads_caller_user_id_into_event(
        self, uc, cmd, caller, appointment, appointment_repo
    ):
        """cancel() event details contain caller.user_id as performed_by."""
        appointment_repo.get_by_id.return_value = appointment

        saved_appointment = None

        async def capture(appt):
            nonlocal saved_appointment
            saved_appointment = appt
            return appt

        appointment_repo.save.side_effect = capture

        await uc.execute(cmd, caller)

        assert saved_appointment is not None
        cancel_events = [e for e in saved_appointment.events if e["type"] == "cancelled"]
        assert len(cancel_events) == 1
        assert cancel_events[0]["details"]["performed_by"] == caller.user_id
