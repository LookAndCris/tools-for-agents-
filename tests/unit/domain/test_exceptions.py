"""Tests for domain exceptions hierarchy."""
import pytest
from domain.exceptions import (
    DomainError,
    InvalidTimeSlotError,
    AppointmentConflictError,
    StaffNotAvailableError,
    ServiceNotOfferedError,
    InvalidStatusTransitionError,
    CancellationNotAllowedError,
    InsufficientFundsError,
)


class TestDomainErrorHierarchy:
    def test_domain_error_is_exception(self):
        """DomainError must inherit from Exception."""
        assert issubclass(DomainError, Exception)

    def test_invalid_time_slot_error_is_domain_error(self):
        assert issubclass(InvalidTimeSlotError, DomainError)

    def test_appointment_conflict_error_is_domain_error(self):
        assert issubclass(AppointmentConflictError, DomainError)

    def test_staff_not_available_error_is_domain_error(self):
        assert issubclass(StaffNotAvailableError, DomainError)

    def test_service_not_offered_error_is_domain_error(self):
        assert issubclass(ServiceNotOfferedError, DomainError)

    def test_invalid_status_transition_error_is_domain_error(self):
        assert issubclass(InvalidStatusTransitionError, DomainError)

    def test_cancellation_not_allowed_error_is_domain_error(self):
        assert issubclass(CancellationNotAllowedError, DomainError)

    def test_insufficient_funds_error_is_domain_error(self):
        assert issubclass(InsufficientFundsError, DomainError)


class TestDomainErrorMessages:
    def test_domain_error_accepts_message(self):
        err = DomainError("something went wrong")
        assert str(err) == "something went wrong"

    def test_invalid_time_slot_error_accepts_message(self):
        err = InvalidTimeSlotError("end must be after start")
        assert str(err) == "end must be after start"

    def test_appointment_conflict_error_accepts_message(self):
        err = AppointmentConflictError("slot already taken")
        assert str(err) == "slot already taken"

    def test_staff_not_available_error_accepts_message(self):
        err = StaffNotAvailableError("staff is on holiday")
        assert str(err) == "staff is on holiday"

    def test_service_not_offered_error_accepts_message(self):
        err = ServiceNotOfferedError("staff does not offer this service")
        assert str(err) == "staff does not offer this service"

    def test_invalid_status_transition_error_accepts_message(self):
        err = InvalidStatusTransitionError("cannot transition from CANCELLED to COMPLETED")
        assert str(err) == "cannot transition from CANCELLED to COMPLETED"

    def test_cancellation_not_allowed_error_accepts_message(self):
        err = CancellationNotAllowedError("cancellation window has passed")
        assert str(err) == "cancellation window has passed"

    def test_insufficient_funds_error_accepts_message(self):
        err = InsufficientFundsError("balance would go negative")
        assert str(err) == "balance would go negative"


class TestDomainExceptionsAreRaisable:
    def test_can_raise_and_catch_domain_error(self):
        with pytest.raises(DomainError, match="base error"):
            raise DomainError("base error")

    def test_can_catch_specific_as_domain_error(self):
        """Specific exceptions must be catchable via the base class."""
        with pytest.raises(DomainError):
            raise InvalidTimeSlotError("non-UTC datetime")

    def test_can_raise_appointment_conflict_error(self):
        with pytest.raises(AppointmentConflictError):
            raise AppointmentConflictError("conflict detected")

    def test_can_raise_staff_not_available_error(self):
        with pytest.raises(StaffNotAvailableError):
            raise StaffNotAvailableError("not available")

    def test_can_raise_service_not_offered_error(self):
        with pytest.raises(ServiceNotOfferedError):
            raise ServiceNotOfferedError("not offered")

    def test_can_raise_invalid_status_transition_error(self):
        with pytest.raises(InvalidStatusTransitionError):
            raise InvalidStatusTransitionError("bad transition")

    def test_can_raise_cancellation_not_allowed_error(self):
        with pytest.raises(CancellationNotAllowedError):
            raise CancellationNotAllowedError("not allowed")

    def test_can_raise_insufficient_funds_error(self):
        with pytest.raises(InsufficientFundsError):
            raise InsufficientFundsError("insufficient")
