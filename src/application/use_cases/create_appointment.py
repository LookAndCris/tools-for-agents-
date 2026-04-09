"""CreateAppointmentUseCase — books a new appointment after validating policies."""
from __future__ import annotations

import uuid
from datetime import timedelta, timezone

from application.dto.commands import CreateAppointmentCommand
from application.dto.responses import AppointmentResponse
from application.dto.user_context import UserContext
from application.exceptions import BookingConflictError, NotFoundError, StaffUnavailableError
from domain.entities.appointment import Appointment
from domain.policies.availability_policy import AvailabilityPolicy
from domain.policies.overlap_policy import OverlapPolicy
from domain.repositories.appointment_repository import AppointmentRepository
from domain.repositories.service_repository import ServiceRepository
from domain.repositories.staff_availability_repository import StaffAvailabilityRepository
from domain.repositories.staff_repository import StaffRepository
from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
from domain.value_objects.appointment_status import AppointmentStatus
from domain.value_objects.time_slot import TimeSlot


class CreateAppointmentUseCase:
    """Command use case: create a new appointment.

    Validates service exists, staff exists, checks availability policy,
    checks overlap policy, then creates and saves the Appointment entity.
    Calls session.flush() via repository — does NOT commit.
    """

    def __init__(
        self,
        service_repo: ServiceRepository,
        staff_repo: StaffRepository,
        availability_repo: StaffAvailabilityRepository,
        time_off_repo: StaffTimeOffRepository,
        appointment_repo: AppointmentRepository,
    ) -> None:
        self._service_repo = service_repo
        self._staff_repo = staff_repo
        self._availability_repo = availability_repo
        self._time_off_repo = time_off_repo
        self._appointment_repo = appointment_repo

    async def execute(
        self, cmd: CreateAppointmentCommand, caller: UserContext
    ) -> AppointmentResponse:
        """Create and persist a new appointment.

        Args:
            cmd: CreateAppointmentCommand with client, staff, service and start time.
            caller: The user context of the actor making the request.

        Returns:
            AppointmentResponse representing the created appointment.

        Raises:
            NotFoundError: If the service or staff member does not exist.
            StaffUnavailableError: If the availability policy rejects the slot.
            BookingConflictError: If the overlap policy detects a time conflict.
        """
        # --- 1. Validate service exists ---
        service = await self._service_repo.get_by_id(cmd.service_id)
        if service is None:
            raise NotFoundError("Service", cmd.service_id)

        # --- 2. Validate staff exists ---
        staff = await self._staff_repo.get_by_id(cmd.staff_id)
        if staff is None:
            raise NotFoundError("Staff", cmd.staff_id)

        # --- 3. Build the proposed TimeSlot from start_time + service duration ---
        duration_minutes = service.duration.duration_minutes
        end_time = cmd.start_time + timedelta(minutes=duration_minutes)
        proposed_slot = TimeSlot(start=cmd.start_time, end=end_time)

        # --- 4. Fetch availability data for the slot's date ---
        day_of_week = cmd.start_time.isoweekday()  # ISO: 1=Mon, 7=Sun
        day_start = cmd.start_time.replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
        )
        day_end = day_start + timedelta(days=1)

        availability_windows = await self._availability_repo.get_by_staff_and_day(
            cmd.staff_id, day_of_week
        )
        time_off_blocks = await self._time_off_repo.get_by_staff_and_range(
            cmd.staff_id, day_start, day_end
        )

        # --- 5. Run AvailabilityPolicy ---
        avail_result = AvailabilityPolicy().check(
            proposed_slot, availability_windows, time_off_blocks
        )
        if not avail_result.is_ok:
            raise StaffUnavailableError("; ".join(avail_result.violations))

        # --- 6. Fetch existing appointments and run OverlapPolicy ---
        existing_appointments = await self._appointment_repo.find_by_staff_and_date_range(
            cmd.staff_id, day_start, day_end
        )
        overlap_result = OverlapPolicy().check(proposed_slot, existing_appointments)
        if not overlap_result.is_ok:
            raise BookingConflictError("; ".join(overlap_result.violations))

        # --- 7. Create Appointment entity ---
        appointment = Appointment(
            id=uuid.uuid4(),
            client_id=cmd.client_id,
            staff_id=cmd.staff_id,
            service_id=cmd.service_id,
            time_slot=proposed_slot,
            status=AppointmentStatus.SCHEDULED,
            notes=cmd.notes,
            created_by=caller.user_id,
        )

        # --- 8. Persist (flush, no commit) ---
        saved = await self._appointment_repo.save(appointment)

        return AppointmentResponse.from_entity(saved)
