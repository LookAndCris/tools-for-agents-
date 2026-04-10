"""Appointment entity — the aggregate root for the scheduling domain."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from domain.exceptions import InvalidStatusTransitionError
from domain.value_objects.appointment_status import AppointmentStatus
from domain.value_objects.time_slot import TimeSlot

_TERMINAL_STATUSES = frozenset(
    {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW}
)


class Appointment:
    """
    Aggregate root that owns scheduling lifecycle transitions.

    Invariant: status transitions must follow _VALID_TRANSITIONS.
    Use confirm(), start(), complete(), cancel(), mark_no_show(), reschedule()
    for state mutations. Each mutation appends a domain event to self.events.
    """

    def __init__(
        self,
        id: UUID,
        client_id: UUID,
        staff_id: UUID,
        service_id: UUID,
        time_slot: TimeSlot,
        status: AppointmentStatus = AppointmentStatus.SCHEDULED,
        notes: str | None = None,
        created_by: UUID | None = None,
        cancelled_by: UUID | None = None,
        cancelled_at: datetime | None = None,
        cancellation_reason: str | None = None,
        events: list[dict[str, Any]] | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.client_id = client_id
        self.staff_id = staff_id
        self.service_id = service_id
        self.time_slot = time_slot
        self.status = status
        self.notes = notes
        self.created_by = created_by
        self.cancelled_by = cancelled_by
        self.cancelled_at = cancelled_at
        self.cancellation_reason = cancellation_reason
        self.events: list[dict[str, Any]] = events if events is not None else []
        now = datetime.now(timezone.utc)
        self.created_at = created_at if created_at is not None else now
        self.updated_at = updated_at if updated_at is not None else now

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """Return True if the appointment has not reached a terminal state."""
        return self.status not in _TERMINAL_STATUSES

    # ------------------------------------------------------------------
    # Mutation methods
    # ------------------------------------------------------------------

    def confirm(self) -> None:
        """Transition SCHEDULED → CONFIRMED."""
        self._transition_to(AppointmentStatus.CONFIRMED)
        self._append_event("confirmed")

    def start(self) -> None:
        """Transition CONFIRMED → IN_PROGRESS."""
        self._transition_to(AppointmentStatus.IN_PROGRESS)
        self._append_event("started")

    def complete(self) -> None:
        """Transition IN_PROGRESS → COMPLETED."""
        self._transition_to(AppointmentStatus.COMPLETED)
        self._append_event("completed")

    def mark_created(self, performed_by: UUID | None = None) -> None:
        """Append a 'created' event with optional actor attribution."""
        self._append_event("created", details={"performed_by": performed_by})

    def cancel(
        self,
        cancelled_by: UUID | None = None,
        reason: str | None = None,
    ) -> None:
        """Transition to CANCELLED from any active state, optionally recording who/why."""
        self._transition_to(AppointmentStatus.CANCELLED)
        self.cancelled_by = cancelled_by
        self.cancellation_reason = reason
        self.cancelled_at = datetime.now(timezone.utc)
        self._append_event(
            "cancelled",
            details={"reason": reason, "performed_by": cancelled_by},
        )

    def mark_no_show(self) -> None:
        """Transition IN_PROGRESS → NO_SHOW."""
        self._transition_to(AppointmentStatus.NO_SHOW)
        self._append_event("no_show")

    def reschedule(self, new_slot: TimeSlot, performed_by: UUID | None = None) -> None:
        """
        Update the time slot and reset status to SCHEDULED.

        Only allowed if the appointment is currently SCHEDULED or CONFIRMED.
        Captures old_start/old_end BEFORE overwriting self.time_slot.
        """
        if self.status not in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
            raise InvalidStatusTransitionError(
                f"Cannot reschedule an appointment with status '{self.status.value}'."
            )
        # Capture old slot BEFORE overwriting
        old_start = self.time_slot.start
        old_end = self.time_slot.end
        self.time_slot = new_slot
        self.status = AppointmentStatus.SCHEDULED
        self._append_event(
            "rescheduled",
            details={
                "old_start": old_start,
                "old_end": old_end,
                "new_start": new_slot.start,
                "new_end": new_slot.end,
                "performed_by": performed_by,
            },
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _transition_to(self, target: AppointmentStatus) -> None:
        if not self.status.can_transition_to(target):
            raise InvalidStatusTransitionError(
                f"Cannot transition from '{self.status.value}' to '{target.value}'."
            )
        self.status = target
        self.updated_at = datetime.now(timezone.utc)

    def _append_event(
        self, event_type: str, details: dict[str, Any] | None = None
    ) -> None:
        event: dict[str, Any] = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if details:
            event["details"] = details
        self.events.append(event)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Appointment(id={self.id}, status={self.status.value}, "
            f"slot={self.time_slot})"
        )
