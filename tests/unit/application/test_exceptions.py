"""Tests for application exception hierarchy."""
from __future__ import annotations

import uuid

import pytest


class TestApplicationError:
    def test_base_error(self):
        from application.exceptions import ApplicationError
        err = ApplicationError("Something went wrong")
        assert str(err) == "Something went wrong"
        assert err.code == "APPLICATION_ERROR"
        assert isinstance(err, Exception)

    def test_custom_code(self):
        from application.exceptions import ApplicationError
        err = ApplicationError("bad input", code="BAD_INPUT")
        assert err.code == "BAD_INPUT"


class TestNotFoundError:
    def test_entity_not_found(self):
        from application.exceptions import NotFoundError, ApplicationError
        eid = uuid.uuid4()
        err = NotFoundError("Service", eid)
        assert isinstance(err, ApplicationError)
        assert "Service" in str(err)
        assert str(eid) in str(err)
        assert err.code == "SERVICE_NOT_FOUND"

    def test_staff_not_found(self):
        from application.exceptions import NotFoundError
        eid = uuid.uuid4()
        err = NotFoundError("Staff", eid)
        assert err.code == "STAFF_NOT_FOUND"

    def test_appointment_not_found(self):
        from application.exceptions import NotFoundError
        eid = uuid.uuid4()
        err = NotFoundError("Appointment", eid)
        assert err.code == "APPOINTMENT_NOT_FOUND"


class TestBookingConflictError:
    def test_is_application_error(self):
        from application.exceptions import BookingConflictError, ApplicationError
        err = BookingConflictError("Slot already taken")
        assert isinstance(err, ApplicationError)
        assert "Slot already taken" in str(err)
        assert err.code == "BOOKING_CONFLICT"


class TestPolicyViolationAppError:
    def test_single_violation(self):
        from application.exceptions import PolicyViolationAppError, ApplicationError
        err = PolicyViolationAppError(["Staff not available at this time"])
        assert isinstance(err, ApplicationError)
        assert err.code == "POLICY_VIOLATION"
        assert len(err.violations) == 1

    def test_multiple_violations(self):
        from application.exceptions import PolicyViolationAppError
        violations = ["Slot outside working hours", "Staff on time off"]
        err = PolicyViolationAppError(violations)
        assert len(err.violations) == 2
        assert "Slot outside working hours" in str(err)

    def test_empty_violations(self):
        from application.exceptions import PolicyViolationAppError
        err = PolicyViolationAppError([])
        assert err.violations == []


class TestStaffUnavailableError:
    def test_is_application_error(self):
        from application.exceptions import StaffUnavailableError, ApplicationError
        err = StaffUnavailableError("Staff is on leave")
        assert isinstance(err, ApplicationError)


class TestCancellationDeniedError:
    def test_is_application_error(self):
        from application.exceptions import CancellationDeniedError, ApplicationError
        err = CancellationDeniedError("Too close to appointment time")
        assert isinstance(err, ApplicationError)


class TestExceptionHierarchy:
    def test_all_inherit_from_application_error(self):
        from application.exceptions import (
            ApplicationError,
            NotFoundError,
            BookingConflictError,
            PolicyViolationAppError,
            StaffUnavailableError,
            CancellationDeniedError,
        )
        for cls in [
            NotFoundError,
            BookingConflictError,
            PolicyViolationAppError,
            StaffUnavailableError,
            CancellationDeniedError,
        ]:
            assert issubclass(cls, ApplicationError), f"{cls.__name__} must inherit from ApplicationError"
