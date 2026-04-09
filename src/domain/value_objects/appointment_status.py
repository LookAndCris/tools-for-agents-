"""AppointmentStatus enum with guarded state-machine transitions."""
from __future__ import annotations

from enum import Enum


class AppointmentStatus(str, Enum):
    """Lifecycle states for an Appointment aggregate."""

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

    def can_transition_to(self, target: "AppointmentStatus") -> bool:
        """Return True if this status may transition to *target*."""
        return target in _VALID_TRANSITIONS.get(self, set())

    def is_terminal(self) -> bool:
        """Return True if this status is a terminal state (no further transitions)."""
        return self in _TERMINAL_STATES


_VALID_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.SCHEDULED: {
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.IN_PROGRESS,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.IN_PROGRESS: {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.NO_SHOW,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.CANCELLED: set(),
    AppointmentStatus.NO_SHOW: set(),
}

_TERMINAL_STATES: frozenset[AppointmentStatus] = frozenset(
    {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    }
)
