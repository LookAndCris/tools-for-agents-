"""Factory-Boy factories for the tools-for-agents test suite.

Re-exports all domain factories for convenient use in tests:

    from tests.factories import AppointmentFactory, TimeSlotFactory, ServiceFactory
"""
from tests.factories.domain_factories import (
    AppointmentFactory,
    ClientFactory,
    MoneyFactory,
    ServiceDurationFactory,
    ServiceFactory,
    StaffFactory,
    TimeSlotFactory,
    UserFactory,
)

__all__ = [
    "AppointmentFactory",
    "ClientFactory",
    "MoneyFactory",
    "ServiceDurationFactory",
    "ServiceFactory",
    "StaffFactory",
    "TimeSlotFactory",
    "UserFactory",
]
