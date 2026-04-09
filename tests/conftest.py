"""
Shared pytest fixtures for the tools-for-agents test suite.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.factories import (
    AppointmentFactory,
    ClientFactory,
    ServiceDurationFactory,
    ServiceFactory,
    StaffFactory,
    TimeSlotFactory,
    UserFactory,
)


def utc_now() -> datetime:
    """Return the current UTC datetime without microseconds."""
    return datetime.now(timezone.utc).replace(microsecond=0)


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def now() -> datetime:
    """Current UTC timestamp (microsecond-free)."""
    return utc_now()


@pytest.fixture
def future_slot():
    """A one-hour TimeSlot starting at 10:00 UTC today."""
    return TimeSlotFactory()


@pytest.fixture
def two_hour_slot():
    """A two-hour TimeSlot starting at 10:00 UTC today."""
    base = utc_now().replace(hour=10, minute=0, second=0, microsecond=0)
    return TimeSlotFactory(start=base, end=base + timedelta(hours=2))


# ---------------------------------------------------------------------------
# Entity fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user():
    """A default User instance."""
    return UserFactory()


@pytest.fixture
def staff():
    """A default Staff instance."""
    return StaffFactory()


@pytest.fixture
def client():
    """A default Client instance."""
    return ClientFactory()


@pytest.fixture
def service():
    """A default Service instance (60-min, $100 USD)."""
    return ServiceFactory()


@pytest.fixture
def service_30min():
    """A 30-minute Service with no buffers."""
    duration = ServiceDurationFactory(duration_minutes=30)
    return ServiceFactory(duration=duration)


@pytest.fixture
def appointment():
    """A default Appointment in SCHEDULED status."""
    return AppointmentFactory()

