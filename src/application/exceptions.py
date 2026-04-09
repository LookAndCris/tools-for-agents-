"""
Application exception hierarchy.

All application errors inherit from ApplicationError so the API layer
can catch any application-level problem with a single except clause.

Domain errors (DomainError subclasses) are NOT caught here — they are
either allowed to propagate or wrapped in ApplicationError subclasses
when different HTTP semantics are required.
"""
from __future__ import annotations

from uuid import UUID


class ApplicationError(Exception):
    """Base class for all application-layer errors."""

    def __init__(self, message: str, code: str = "APPLICATION_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(ApplicationError):
    """Raised when a requested entity does not exist.

    Maps to HTTP 404.
    """

    def __init__(self, entity: str, id: UUID) -> None:
        super().__init__(
            f"{entity} {id} not found",
            f"{entity.upper()}_NOT_FOUND",
        )
        self.entity = entity
        self.entity_id = id


class BookingConflictError(ApplicationError):
    """Raised when an appointment cannot be booked due to a time conflict.

    Maps to HTTP 409.
    """

    def __init__(self, message: str = "Booking conflict") -> None:
        super().__init__(message, "BOOKING_CONFLICT")


class PolicyViolationAppError(ApplicationError):
    """Raised when one or more business policy checks fail.

    Maps to HTTP 422.
    """

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__("; ".join(violations), "POLICY_VIOLATION")


class StaffUnavailableError(ApplicationError):
    """Raised when a staff member is not available for the requested slot.

    Maps to HTTP 422.
    """

    def __init__(self, message: str = "Staff is not available") -> None:
        super().__init__(message, "STAFF_UNAVAILABLE")


class CancellationDeniedError(ApplicationError):
    """Raised when a cancellation request is rejected by policy.

    Maps to HTTP 422.
    """

    def __init__(self, message: str = "Cancellation not allowed") -> None:
        super().__init__(message, "CANCELLATION_DENIED")


class ValidationError(ApplicationError):
    """Raised when input data fails application-level validation.

    Maps to HTTP 400.
    """

    def __init__(self, message: str, code: str = "VALIDATION_ERROR") -> None:
        super().__init__(message, code)
