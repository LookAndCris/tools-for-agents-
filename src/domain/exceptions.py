"""
Domain exceptions hierarchy.

All domain errors inherit from DomainError so callers can catch
any domain-level problem with a single except clause when needed.
"""


class DomainError(Exception):
    """Base class for all domain errors."""


class InvalidTimeSlotError(DomainError):
    """Raised when a TimeSlot is invalid (e.g. end <= start or non-UTC datetime)."""


class AppointmentConflictError(DomainError):
    """Raised when a proposed appointment overlaps an existing one."""


class StaffNotAvailableError(DomainError):
    """Raised when a staff member is not available for the requested slot."""


class ServiceNotOfferedError(DomainError):
    """Raised when a staff member does not offer the requested service."""


class InvalidStatusTransitionError(DomainError):
    """Raised when an illegal Appointment state transition is attempted."""


class CancellationNotAllowedError(DomainError):
    """Raised when cancellation is denied (e.g. outside allowed window)."""


class InsufficientFundsError(DomainError):
    """Raised when a Money subtraction would result in a negative balance."""


class InvalidMoneyError(DomainError):
    """Raised when a Money value object is constructed with invalid parameters."""


class InvalidServiceDurationError(DomainError):
    """Raised when a ServiceDuration is constructed with invalid parameters."""


class PolicyViolationError(DomainError):
    """Raised when a business policy is violated."""


# Aliases for cross-naming compatibility
InvalidStateTransitionError = InvalidStatusTransitionError
OverlapError = AppointmentConflictError
