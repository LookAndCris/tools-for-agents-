"""CancelAppointmentUseCase — cancels an appointment after policy check."""
from __future__ import annotations

from datetime import datetime, timezone

from application.dto.commands import CancelAppointmentCommand
from application.dto.responses import AppointmentResponse
from application.dto.user_context import UserContext
from application.exceptions import CancellationDeniedError, NotFoundError
from domain.policies.cancellation_policy import CancellationPolicy
from domain.repositories.appointment_repository import AppointmentRepository


class CancelAppointmentUseCase:
    """Command use case: cancel an existing appointment.

    Loads the appointment, runs CancellationPolicy, calls appointment.cancel(),
    saves via repository, and flushes. Does NOT commit.
    """

    def __init__(self, appointment_repo: AppointmentRepository) -> None:
        self._appointment_repo = appointment_repo

    async def execute(
        self, cmd: CancelAppointmentCommand, caller: UserContext
    ) -> AppointmentResponse:
        """Cancel the specified appointment.

        Args:
            cmd: CancelAppointmentCommand with appointment_id and optional reason.
            caller: The user context of the actor requesting cancellation.

        Returns:
            AppointmentResponse representing the cancelled appointment.

        Raises:
            NotFoundError: If the appointment does not exist.
            CancellationDeniedError: If the cancellation policy rejects the request.
        """
        # --- 1. Load appointment ---
        appointment = await self._appointment_repo.get_by_id(cmd.appointment_id)
        if appointment is None:
            raise NotFoundError("Appointment", cmd.appointment_id)

        # --- 2. Run CancellationPolicy ---
        current_time = datetime.now(timezone.utc)
        result = CancellationPolicy().can_cancel(
            appointment=appointment,
            cancelled_by_role=caller.role,
            current_time=current_time,
            actor_id=caller.staff_id,
        )
        if not result.is_ok:
            raise CancellationDeniedError("; ".join(result.violations))

        # --- 3. Cancel the entity ---
        appointment.cancel(
            cancelled_by=caller.user_id,
            reason=cmd.reason,
        )

        # --- 4. Persist (flush, no commit) ---
        saved = await self._appointment_repo.save(appointment)

        return AppointmentResponse.from_entity(saved)
