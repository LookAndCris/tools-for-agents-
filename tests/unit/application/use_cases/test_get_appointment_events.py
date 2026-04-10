"""Unit tests for GetAppointmentEventsUseCase (Task 3.1 - RED phase)."""
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


class TestGetAppointmentEventsUseCase:
    """Unit tests for GetAppointmentEventsUseCase."""

    @pytest.fixture
    def appointment_repo(self):
        return AsyncMock(spec=AppointmentRepository)

    @pytest.fixture
    def appointment_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def actor_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def appointment_with_events(self, appointment_id, actor_id):
        """An appointment with a 'created' event and a 'cancelled' event."""
        appt = AppointmentFactory(
            id=appointment_id,
            status=AppointmentStatus.SCHEDULED,
            time_slot=TimeSlot(
                start=_utc(2026, 4, 10, 10, 0),
                end=_utc(2026, 4, 10, 11, 0),
            ),
            events=[
                {
                    "type": "created",
                    "timestamp": _utc(2026, 4, 10, 9, 0).isoformat(),
                    "details": {"performed_by": actor_id},
                },
                {
                    "type": "cancelled",
                    "timestamp": _utc(2026, 4, 10, 9, 30).isoformat(),
                    "details": {
                        "performed_by": actor_id,
                        "reason": "Test reason",
                    },
                },
            ],
        )
        return appt

    @pytest.fixture
    def uc(self, appointment_repo):
        from application.use_cases.get_appointment_events import GetAppointmentEventsUseCase

        return GetAppointmentEventsUseCase(appointment_repo=appointment_repo)

    # ------------------------------------------------------------------ #
    # Happy path
    # ------------------------------------------------------------------ #

    async def test_returns_list_of_event_responses(
        self, uc, appointment_id, appointment_with_events, appointment_repo
    ):
        """Returns a list of AppointmentEventResponse DTOs."""
        from application.dto.responses import AppointmentEventResponse

        appointment_repo.get_by_id.return_value = appointment_with_events

        result = await uc.execute(appointment_id)

        assert isinstance(result, list)
        assert len(result) == 2
        for item in result:
            assert isinstance(item, AppointmentEventResponse)

    async def test_events_ordered_chronologically(
        self, uc, appointment_id, appointment_with_events, appointment_repo
    ):
        """Events are returned in chronological order (oldest first)."""
        appointment_repo.get_by_id.return_value = appointment_with_events

        result = await uc.execute(appointment_id)

        assert result[0].event_type == "created"
        assert result[1].event_type == "cancelled"
        assert result[0].occurred_at <= result[1].occurred_at

    async def test_event_response_fields(
        self, uc, appointment_id, appointment_with_events, appointment_repo, actor_id
    ):
        """AppointmentEventResponse has all expected fields populated."""
        appointment_repo.get_by_id.return_value = appointment_with_events

        result = await uc.execute(appointment_id)

        created = result[0]
        assert created.event_type == "created"
        assert created.appointment_id == appointment_id
        assert created.id is not None

    async def test_empty_events_returns_empty_list(
        self, uc, appointment_id, appointment_repo
    ):
        """Returns empty list when appointment has no events."""
        appt = AppointmentFactory(
            id=appointment_id,
            status=AppointmentStatus.SCHEDULED,
            events=[],
        )
        appointment_repo.get_by_id.return_value = appt

        result = await uc.execute(appointment_id)

        assert result == []

    # ------------------------------------------------------------------ #
    # Not found
    # ------------------------------------------------------------------ #

    async def test_raises_not_found_for_missing_appointment(
        self, uc, appointment_id, appointment_repo
    ):
        """Raises NotFoundError when appointment does not exist."""
        from application.exceptions import NotFoundError

        appointment_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await uc.execute(appointment_id)

        assert "APPOINTMENT" in exc_info.value.code
