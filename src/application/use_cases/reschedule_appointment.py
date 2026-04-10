"""RescheduleAppointmentUseCase — moves an appointment to a new time slot."""
from __future__ import annotations

from datetime import timedelta, timezone

from application.dto.commands import RescheduleAppointmentCommand
from application.dto.responses import AppointmentResponse
from application.dto.user_context import UserContext
from application.exceptions import BookingConflictError, NotFoundError, StaffUnavailableError
from domain.policies.availability_policy import AvailabilityPolicy
from domain.policies.overlap_policy import OverlapPolicy
from domain.repositories.appointment_repository import AppointmentRepository
from domain.repositories.service_repository import ServiceRepository
from domain.repositories.staff_availability_repository import StaffAvailabilityRepository
from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
from domain.value_objects.time_slot import TimeSlot


class RescheduleAppointmentUseCase:
    """Command use case: move an appointment to a new time slot.

    Loads the appointment, validates the new slot against availability and
    overlap policies, calls appointment.reschedule(), saves, and flushes.
    Does NOT commit.
    """

    def __init__(
        self,
        appointment_repo: AppointmentRepository,
        service_repo: ServiceRepository,
        availability_repo: StaffAvailabilityRepository,
        time_off_repo: StaffTimeOffRepository,
    ) -> None:
        self._appointment_repo = appointment_repo
        self._service_repo = service_repo
        self._availability_repo = availability_repo
        self._time_off_repo = time_off_repo

    async def execute(
        self, cmd: RescheduleAppointmentCommand, caller: UserContext
    ) -> AppointmentResponse:
        """Reschedule the specified appointment to a new time.

        Args:
            cmd: RescheduleAppointmentCommand with appointment_id and new_start_time.
            caller: The user context of the actor requesting the reschedule.

        Returns:
            AppointmentResponse with the updated time slot.

        Raises:
            NotFoundError: If the appointment or service does not exist.
            StaffUnavailableError: If availability policy rejects the new slot.
            BookingConflictError: If the new slot overlaps an existing appointment.
        """
        # --- 1. Load appointment ---
        appointment = await self._appointment_repo.get_by_id(cmd.appointment_id)
        if appointment is None:
            raise NotFoundError("Appointment", cmd.appointment_id)

        # --- 2. Load service to get duration ---
        service = await self._service_repo.get_by_id(appointment.service_id)
        if service is None:
            raise NotFoundError("Service", appointment.service_id)

        # --- 3. Build new TimeSlot ---
        duration_minutes = service.duration.duration_minutes
        new_end_time = cmd.new_start_time + timedelta(minutes=duration_minutes)
        new_slot = TimeSlot(start=cmd.new_start_time, end=new_end_time)

        # --- 4. Fetch availability data for the new slot's date ---
        day_of_week = cmd.new_start_time.isoweekday()
        day_start = cmd.new_start_time.replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc
        )
        day_end = day_start + timedelta(days=1)

        availability_windows = await self._availability_repo.get_by_staff_and_day(
            appointment.staff_id, day_of_week
        )
        time_off_blocks = await self._time_off_repo.get_by_staff_and_range(
            appointment.staff_id, day_start, day_end
        )

        # --- 5. Run AvailabilityPolicy ---
        avail_result = AvailabilityPolicy().check(
            new_slot, availability_windows, time_off_blocks
        )
        if not avail_result.is_ok:
            raise StaffUnavailableError("; ".join(avail_result.violations))

        # --- 6. Fetch existing appointments and run OverlapPolicy ---
        existing_appointments = await self._appointment_repo.find_by_staff_and_date_range(
            appointment.staff_id, day_start, day_end
        )
        # Exclude the appointment being rescheduled from the overlap check
        others = [a for a in existing_appointments if a.id != appointment.id]
        overlap_result = OverlapPolicy().check(new_slot, others)
        if not overlap_result.is_ok:
            raise BookingConflictError("; ".join(overlap_result.violations))

        # --- 7. Mutate entity ---
        appointment.reschedule(new_slot, performed_by=caller.user_id)

        # --- 8. Persist (flush, no commit) ---
        saved = await self._appointment_repo.save(appointment)

        return AppointmentResponse.from_entity(saved)
