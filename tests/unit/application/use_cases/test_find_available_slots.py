"""Unit tests for FindAvailableSlotsUseCase."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from domain.repositories.appointment_repository import AppointmentRepository
from domain.repositories.service_repository import ServiceRepository
from domain.repositories.staff_availability_repository import StaffAvailabilityRepository
from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
from domain.value_objects.time_slot import TimeSlot
from tests.factories import AppointmentFactory, ServiceFactory


def _utc(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    """Build a UTC-aware datetime for tests."""
    return datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc)


class TestFindAvailableSlotsUseCase:
    """Tests for FindAvailableSlotsUseCase — day/week/month queries."""

    @pytest.fixture
    def service_repo(self):
        return AsyncMock(spec=ServiceRepository)

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
    def staff_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def service(self):
        """A 60-minute service."""
        return ServiceFactory(
            duration__duration_minutes=60,
            duration__buffer_before=0,
            duration__buffer_after=0,
        )

    @pytest.fixture
    def uc(self, service_repo, availability_repo, time_off_repo, appointment_repo):
        from application.use_cases.find_available_slots import FindAvailableSlotsUseCase

        return FindAvailableSlotsUseCase(
            service_repo=service_repo,
            availability_repo=availability_repo,
            time_off_repo=time_off_repo,
            appointment_repo=appointment_repo,
        )

    # ------------------------------------------------------------------ #
    # Day query: single day, full 8-hour window, no time-off, no conflicts
    # ------------------------------------------------------------------ #

    async def test_day_query_returns_slots(
        self, uc, service_repo, availability_repo, time_off_repo, appointment_repo, staff_id, service
    ):
        from application.dto.queries import FindAvailableSlotsQuery
        from application.dto.responses import AvailableSlotsResponse

        target_date = date(2026, 4, 10)

        # Availability: 09:00 – 17:00 on that day
        window = TimeSlot(
            start=_utc(2026, 4, 10, 9, 0),
            end=_utc(2026, 4, 10, 17, 0),
        )
        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = [window]
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []

        query = FindAvailableSlotsQuery(
            staff_id=staff_id,
            service_id=service.id,
            date_from=target_date,
            date_to=target_date,
        )
        result = await uc.execute(query)

        assert isinstance(result, AvailableSlotsResponse)
        assert result.staff_id == staff_id
        assert result.service_id == service.id
        # 8-hour window / 60-min slots at 30-min intervals → 09:00, 09:30, ..., 16:00
        assert len(result.slots) > 0
        assert all(isinstance(s, datetime) for s in result.slots)
        # First slot should be 09:00
        assert result.slots[0] == _utc(2026, 4, 10, 9, 0)

    async def test_day_query_calls_repos_with_correct_args(
        self, uc, service_repo, availability_repo, time_off_repo, appointment_repo, staff_id, service
    ):
        from application.dto.queries import FindAvailableSlotsQuery

        target_date = date(2026, 4, 10)
        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = []
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []

        query = FindAvailableSlotsQuery(
            staff_id=staff_id,
            service_id=service.id,
            date_from=target_date,
            date_to=target_date,
        )
        await uc.execute(query)

        # Service lookup
        service_repo.get_by_id.assert_called_once_with(service.id)
        # Availability by weekday (April 10 2026 is Friday = ISO 5)
        availability_repo.get_by_staff_and_day.assert_called_once_with(staff_id, 5)
        # Time-off and appointments for the day range
        time_off_repo.get_by_staff_and_range.assert_called_once()
        appointment_repo.find_by_staff_and_date_range.assert_called_once()

    # ------------------------------------------------------------------ #
    # Week query: 7 days
    # ------------------------------------------------------------------ #

    async def test_week_query_iterates_each_day(
        self, uc, service_repo, availability_repo, time_off_repo, appointment_repo, staff_id, service
    ):
        from application.dto.queries import FindAvailableSlotsQuery

        date_from = date(2026, 4, 7)   # Tuesday
        date_to = date(2026, 4, 13)    # Monday (7 days total)

        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = []
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []

        query = FindAvailableSlotsQuery(
            staff_id=staff_id,
            service_id=service.id,
            date_from=date_from,
            date_to=date_to,
        )
        await uc.execute(query)

        # Should call availability_repo once per day in the range (7 days)
        assert availability_repo.get_by_staff_and_day.call_count == 7

    async def test_week_query_aggregates_slots_across_days(
        self, uc, service_repo, availability_repo, time_off_repo, appointment_repo, staff_id, service
    ):
        from application.dto.queries import FindAvailableSlotsQuery

        date_from = date(2026, 4, 7)
        date_to = date(2026, 4, 8)  # 2 days

        # Day 1: 09:00-10:00 window → 1 slot for 60-min service
        day1_window = TimeSlot(
            start=_utc(2026, 4, 7, 9, 0),
            end=_utc(2026, 4, 7, 10, 0),
        )
        # Day 2: 14:00-16:00 window → 3 slots (30-min intervals)
        day2_window = TimeSlot(
            start=_utc(2026, 4, 8, 14, 0),
            end=_utc(2026, 4, 8, 16, 0),
        )

        service_repo.get_by_id.return_value = service
        # Return different windows based on ISO weekday
        # April 7 = Tuesday (2), April 8 = Wednesday (3)
        availability_repo.get_by_staff_and_day.side_effect = lambda sid, dow: (
            [day1_window] if dow == 2 else [day2_window]
        )
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []

        query = FindAvailableSlotsQuery(
            staff_id=staff_id,
            service_id=service.id,
            date_from=date_from,
            date_to=date_to,
        )
        result = await uc.execute(query)

        # Day 1: 09:00 (1 slot for 60-min service in 09:00-10:00 window)
        # Day 2: 14:00, 14:30, 15:00 (3 slots at 30-min step in 14:00-16:00 window) → 4 total
        assert len(result.slots) == 4
        # Slots should be in ascending order
        assert result.slots == sorted(result.slots)

    # ------------------------------------------------------------------ #
    # Month query: 31 days (maximum allowed)
    # ------------------------------------------------------------------ #

    async def test_month_query_31_days_is_allowed(
        self, uc, service_repo, availability_repo, time_off_repo, appointment_repo, staff_id, service
    ):
        from application.dto.queries import FindAvailableSlotsQuery

        date_from = date(2026, 4, 1)
        date_to = date(2026, 5, 1)  # 31 days inclusive

        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = []
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []

        query = FindAvailableSlotsQuery(
            staff_id=staff_id,
            service_id=service.id,
            date_from=date_from,
            date_to=date_to,
        )
        result = await uc.execute(query)

        # Should not raise — 31 days is max allowed
        assert result.slots == []  # No windows so no slots
        # Should call availability_repo once per day (31 days)
        assert availability_repo.get_by_staff_and_day.call_count == 31

    # ------------------------------------------------------------------ #
    # Validation: range > 31 days must be rejected
    # ------------------------------------------------------------------ #

    async def test_range_exceeding_31_days_raises_validation_error(
        self, uc, service_repo, availability_repo, time_off_repo, appointment_repo, staff_id, service
    ):
        from application.dto.queries import FindAvailableSlotsQuery
        from application.exceptions import ValidationError

        date_from = date(2026, 4, 1)
        date_to = date(2026, 5, 2)  # 32 days — over the limit

        query = FindAvailableSlotsQuery(
            staff_id=staff_id,
            service_id=service.id,
            date_from=date_from,
            date_to=date_to,
        )
        with pytest.raises(ValidationError):
            await uc.execute(query)

        # Repos should NOT be called when validation fails
        service_repo.get_by_id.assert_not_called()

    async def test_date_from_after_date_to_raises_validation_error(
        self, uc, service_repo, service, staff_id
    ):
        from application.dto.queries import FindAvailableSlotsQuery
        from application.exceptions import ValidationError

        query = FindAvailableSlotsQuery(
            staff_id=staff_id,
            service_id=service.id,
            date_from=date(2026, 4, 10),
            date_to=date(2026, 4, 5),  # before date_from
        )
        with pytest.raises(ValidationError):
            await uc.execute(query)

    # ------------------------------------------------------------------ #
    # No-availability scenario
    # ------------------------------------------------------------------ #

    async def test_returns_empty_when_no_availability_windows(
        self, uc, service_repo, availability_repo, time_off_repo, appointment_repo, staff_id, service
    ):
        from application.dto.queries import FindAvailableSlotsQuery

        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = []
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = []

        query = FindAvailableSlotsQuery(
            staff_id=staff_id,
            service_id=service.id,
            date_from=date(2026, 4, 10),
            date_to=date(2026, 4, 10),
        )
        result = await uc.execute(query)

        assert result.slots == []

    async def test_returns_empty_when_time_off_covers_all_windows(
        self, uc, service_repo, availability_repo, time_off_repo, appointment_repo, staff_id, service
    ):
        from application.dto.queries import FindAvailableSlotsQuery

        # Availability: 09:00-17:00
        window = TimeSlot(
            start=_utc(2026, 4, 10, 9, 0),
            end=_utc(2026, 4, 10, 17, 0),
        )
        # Time-off covers the entire availability window
        full_block = TimeSlot(
            start=_utc(2026, 4, 10, 8, 0),
            end=_utc(2026, 4, 10, 18, 0),
        )

        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = [window]
        time_off_repo.get_by_staff_and_range.return_value = [full_block]
        appointment_repo.find_by_staff_and_date_range.return_value = []

        query = FindAvailableSlotsQuery(
            staff_id=staff_id,
            service_id=service.id,
            date_from=date(2026, 4, 10),
            date_to=date(2026, 4, 10),
        )
        result = await uc.execute(query)

        assert result.slots == []

    # ------------------------------------------------------------------ #
    # Service not found
    # ------------------------------------------------------------------ #

    async def test_raises_not_found_when_service_missing(
        self, uc, service_repo, availability_repo, time_off_repo, appointment_repo, staff_id, service
    ):
        from application.dto.queries import FindAvailableSlotsQuery
        from application.exceptions import NotFoundError

        service_repo.get_by_id.return_value = None

        query = FindAvailableSlotsQuery(
            staff_id=staff_id,
            service_id=service.id,
            date_from=date(2026, 4, 10),
            date_to=date(2026, 4, 10),
        )
        with pytest.raises(NotFoundError):
            await uc.execute(query)

    # ------------------------------------------------------------------ #
    # Time-off partially blocks window
    # ------------------------------------------------------------------ #

    async def test_time_off_reduces_available_slots(
        self, uc, service_repo, availability_repo, time_off_repo, appointment_repo, staff_id, service
    ):
        from application.dto.queries import FindAvailableSlotsQuery

        # Availability: 09:00-12:00
        window = TimeSlot(
            start=_utc(2026, 4, 10, 9, 0),
            end=_utc(2026, 4, 10, 12, 0),
        )
        # Time-off: 10:00-12:00 — blocks second half
        block = TimeSlot(
            start=_utc(2026, 4, 10, 10, 0),
            end=_utc(2026, 4, 10, 12, 0),
        )

        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = [window]
        time_off_repo.get_by_staff_and_range.return_value = [block]
        appointment_repo.find_by_staff_and_date_range.return_value = []

        query = FindAvailableSlotsQuery(
            staff_id=staff_id,
            service_id=service.id,
            date_from=date(2026, 4, 10),
            date_to=date(2026, 4, 10),
        )
        result = await uc.execute(query)

        # Only 09:00 slot fits in 09:00-10:00 sub-window for a 60-min service
        assert len(result.slots) == 1
        assert result.slots[0] == _utc(2026, 4, 10, 9, 0)

    # ------------------------------------------------------------------ #
    # Existing appointments block slots
    # ------------------------------------------------------------------ #

    async def test_existing_appointment_blocks_slot(
        self, uc, service_repo, availability_repo, time_off_repo, appointment_repo, staff_id, service
    ):
        from application.dto.queries import FindAvailableSlotsQuery

        # Availability: 09:00-11:00 → two possible 60-min slots: 09:00, 10:00
        window = TimeSlot(
            start=_utc(2026, 4, 10, 9, 0),
            end=_utc(2026, 4, 10, 11, 0),
        )
        # Existing appointment occupies 09:00-10:00
        existing_appt = AppointmentFactory(
            staff_id=staff_id,
            time_slot=TimeSlot(
                start=_utc(2026, 4, 10, 9, 0),
                end=_utc(2026, 4, 10, 10, 0),
            ),
        )

        service_repo.get_by_id.return_value = service
        availability_repo.get_by_staff_and_day.return_value = [window]
        time_off_repo.get_by_staff_and_range.return_value = []
        appointment_repo.find_by_staff_and_date_range.return_value = [existing_appt]

        query = FindAvailableSlotsQuery(
            staff_id=staff_id,
            service_id=service.id,
            date_from=date(2026, 4, 10),
            date_to=date(2026, 4, 10),
        )
        result = await uc.execute(query)

        # 09:00 is blocked by existing appointment; only 10:00 is free
        assert len(result.slots) == 1
        assert result.slots[0] == _utc(2026, 4, 10, 10, 0)
