"""FindAvailableSlotsUseCase — returns available booking slots within a date range."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from application.dto.queries import FindAvailableSlotsQuery
from application.dto.responses import AvailableSlotsResponse
from application.exceptions import NotFoundError, ValidationError
from domain.repositories.appointment_repository import AppointmentRepository
from domain.repositories.service_repository import ServiceRepository
from domain.repositories.staff_availability_repository import StaffAvailabilityRepository
from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
from domain.scheduling_engine.availability_checker import AvailabilityChecker
from domain.scheduling_engine.slot_finder import SlotFinder

MAX_DATE_RANGE_DAYS = 31


class FindAvailableSlotsUseCase:
    """Query use case: find available appointment slots for a staff member.

    Iterates day-by-day across the requested range (max 31 days), delegating
    availability window computation to AvailabilityChecker and slot generation
    to SlotFinder. Never reimplements scheduling logic.
    """

    def __init__(
        self,
        service_repo: ServiceRepository,
        availability_repo: StaffAvailabilityRepository,
        time_off_repo: StaffTimeOffRepository,
        appointment_repo: AppointmentRepository,
    ) -> None:
        self._service_repo = service_repo
        self._availability_repo = availability_repo
        self._time_off_repo = time_off_repo
        self._appointment_repo = appointment_repo

    async def execute(self, query: FindAvailableSlotsQuery) -> AvailableSlotsResponse:
        """Return available slots for the given staff member and service.

        Args:
            query: Contains staff_id, service_id, date_from and date_to (inclusive).

        Returns:
            AvailableSlotsResponse with a sorted list of UTC datetime slot starts.

        Raises:
            ValidationError: if date_to < date_from or range exceeds 31 days.
            NotFoundError: if the service does not exist.
        """
        self._validate_range(query.date_from, query.date_to)

        service = await self._service_repo.get_by_id(query.service_id)
        if service is None:
            raise NotFoundError("Service", query.service_id)

        duration_minutes = service.duration.duration_minutes

        all_slots: list[datetime] = []
        current_date = query.date_from

        while current_date <= query.date_to:
            day_slots = await self._slots_for_date(
                current_date, query.staff_id, duration_minutes
            )
            all_slots.extend(day_slots)
            current_date += timedelta(days=1)

        return AvailableSlotsResponse(
            staff_id=query.staff_id,
            service_id=query.service_id,
            slots=sorted(all_slots),
        )

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    async def _slots_for_date(
        self,
        target_date: date,
        staff_id,
        duration_minutes: int,
    ) -> list[datetime]:
        """Compute available slots for a single date using the domain engine."""
        day_of_week = target_date.isoweekday()  # ISO: 1=Mon, 7=Sun

        # Day boundaries in UTC for repo queries
        day_start = datetime(
            target_date.year, target_date.month, target_date.day,
            0, 0, 0, tzinfo=timezone.utc,
        )
        day_end = day_start + timedelta(days=1)

        # Fetch raw availability windows, time-off blocks, and existing appointments
        availability_windows = await self._availability_repo.get_by_staff_and_day(
            staff_id, day_of_week
        )
        time_off_blocks = await self._time_off_repo.get_by_staff_and_range(
            staff_id, day_start, day_end
        )
        existing_appointments = await self._appointment_repo.find_by_staff_and_date_range(
            staff_id, day_start, day_end
        )

        # Delegate to domain scheduling engine — do NOT reimplement logic
        free_windows = AvailabilityChecker.get_available_windows(
            availability_windows, time_off_blocks, target_date
        )
        return SlotFinder.find_slots(free_windows, existing_appointments, duration_minutes)

    @staticmethod
    def _validate_range(date_from: date, date_to: date) -> None:
        """Raise ValidationError if the date range is invalid or too large."""
        if date_to < date_from:
            raise ValidationError(
                f"date_to ({date_to}) must be >= date_from ({date_from})",
                "INVALID_DATE_RANGE",
            )
        delta = (date_to - date_from).days + 1  # inclusive count
        if delta > MAX_DATE_RANGE_DAYS:
            raise ValidationError(
                f"Date range of {delta} days exceeds the maximum of {MAX_DATE_RANGE_DAYS} days.",
                "DATE_RANGE_TOO_LARGE",
            )
