"""Global exception handlers — map ApplicationError subclasses to HTTP responses.

Error envelope format: {"error": {"message": "...", "code": "..."}}
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from application.exceptions import (
    ApplicationError,
    BookingConflictError,
    CancellationDeniedError,
    NotFoundError,
    PolicyViolationAppError,
    StaffUnavailableError,
    ValidationError,
)

# Map ApplicationError subclasses to HTTP status codes
_STATUS_MAP: dict[type[ApplicationError], int] = {
    NotFoundError: 404,
    BookingConflictError: 409,
    PolicyViolationAppError: 422,
    StaffUnavailableError: 422,
    CancellationDeniedError: 422,
    ValidationError: 400,
}


def _error_response(exc: ApplicationError, status_code: int) -> JSONResponse:
    """Build the standard error envelope response."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"message": exc.message, "code": exc.code}},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all application error handlers on the given FastAPI app.

    Each ``ApplicationError`` subclass is mapped to its appropriate HTTP status.
    A fallback handler catches any unmapped ``ApplicationError`` as 500.
    """

    async def _handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:  # type: ignore[misc]
        return _error_response(exc, 404)

    async def _handle_booking_conflict(request: Request, exc: BookingConflictError) -> JSONResponse:  # type: ignore[misc]
        return _error_response(exc, 409)

    async def _handle_policy_violation(request: Request, exc: PolicyViolationAppError) -> JSONResponse:  # type: ignore[misc]
        return _error_response(exc, 422)

    async def _handle_staff_unavailable(request: Request, exc: StaffUnavailableError) -> JSONResponse:  # type: ignore[misc]
        return _error_response(exc, 422)

    async def _handle_cancellation_denied(request: Request, exc: CancellationDeniedError) -> JSONResponse:  # type: ignore[misc]
        return _error_response(exc, 422)

    async def _handle_validation_error(request: Request, exc: ValidationError) -> JSONResponse:  # type: ignore[misc]
        return _error_response(exc, 400)

    async def _handle_application_error(request: Request, exc: ApplicationError) -> JSONResponse:  # type: ignore[misc]
        """Fallback handler for unmapped ApplicationError subclasses."""
        return _error_response(exc, 500)

    # Register specific subclasses first (most specific match wins)
    app.add_exception_handler(NotFoundError, _handle_not_found)  # type: ignore[arg-type]
    app.add_exception_handler(BookingConflictError, _handle_booking_conflict)  # type: ignore[arg-type]
    app.add_exception_handler(PolicyViolationAppError, _handle_policy_violation)  # type: ignore[arg-type]
    app.add_exception_handler(StaffUnavailableError, _handle_staff_unavailable)  # type: ignore[arg-type]
    app.add_exception_handler(CancellationDeniedError, _handle_cancellation_denied)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, _handle_validation_error)  # type: ignore[arg-type]
    # Fallback for any other ApplicationError
    app.add_exception_handler(ApplicationError, _handle_application_error)  # type: ignore[arg-type]
