"""CancellationPolicy — role-based rules for appointment cancellation."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from domain.entities.appointment import Appointment
from domain.policies.policy_result import PolicyResult


class CancellationPolicy:
    """Policy that determines whether an actor may cancel an appointment.

    Rules:
    - Terminal appointments (CANCELLED, COMPLETED, NO_SHOW) cannot be cancelled.
    - Admins can always cancel active appointments.
    - Staff can cancel active appointments they are assigned to.
    - Clients can cancel active appointments.
    """

    def can_cancel(
        self,
        appointment: Appointment,
        cancelled_by_role: str,
        current_time: datetime,
        actor_id: Optional[UUID] = None,
    ) -> PolicyResult:
        """Check if the given actor may cancel *appointment*.

        Args:
            appointment: The appointment to potentially cancel.
            cancelled_by_role: Role string — 'admin', 'staff', or 'client'.
            current_time: The current UTC datetime (for future time-window checks).
            actor_id: Optional UUID of the actor (required for role='staff' checks).

        Returns:
            PolicyResult.ok() if cancellation is allowed, PolicyResult.fail() otherwise.
        """
        # Terminal appointments cannot be cancelled regardless of role
        if appointment.status.is_terminal():
            return PolicyResult.fail(
                f"Appointment cannot be cancelled: it is already in a terminal "
                f"state '{appointment.status.value}'."
            )

        # Admins can always cancel active appointments
        if cancelled_by_role == "admin":
            return PolicyResult.ok()

        # Clients can cancel any active appointment
        if cancelled_by_role == "client":
            return PolicyResult.ok()

        # Staff can only cancel their own appointments
        if cancelled_by_role == "staff":
            if actor_id is not None and actor_id == appointment.staff_id:
                return PolicyResult.ok()
            return PolicyResult.fail(
                "Staff may only cancel appointments they are assigned to."
            )

        # Unknown role — deny
        return PolicyResult.fail(f"Unknown role '{cancelled_by_role}'. Cancellation denied.")
