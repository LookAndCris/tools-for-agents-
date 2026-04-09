"""Factory-Boy factories for domain objects.

Usage:
    from tests.factories.domain_factories import AppointmentFactory, TimeSlotFactory

    appt = AppointmentFactory()
    slot = TimeSlotFactory()
    slot_2h = TimeSlotFactory(start=utc_now(), end=utc_now() + timedelta(hours=2))
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import factory

from domain.entities.appointment import Appointment
from domain.entities.client import Client
from domain.entities.service import Service
from domain.entities.staff import Staff
from domain.entities.user import User
from domain.value_objects.appointment_status import AppointmentStatus
from domain.value_objects.money import Money
from domain.value_objects.service_duration import ServiceDuration
from domain.value_objects.time_slot import TimeSlot


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class TimeSlotFactory(factory.Factory):
    """Generates valid UTC-aware TimeSlot instances (default: 1 hour from now)."""

    class Meta:
        model = TimeSlot

    start = factory.LazyFunction(lambda: _utc_now().replace(hour=10, minute=0, second=0))
    end = factory.LazyFunction(lambda: _utc_now().replace(hour=11, minute=0, second=0))


class MoneyFactory(factory.Factory):
    """Generates valid Money instances (default: 100.00 USD)."""

    class Meta:
        model = Money

    amount = Decimal("100.00")
    currency = "USD"


class ServiceDurationFactory(factory.Factory):
    """Generates valid ServiceDuration instances (default: 60 min, 0 buffers)."""

    class Meta:
        model = ServiceDuration

    buffer_before = 0
    duration_minutes = 60
    buffer_after = 0


class UserFactory(factory.Factory):
    """Generates User instances with realistic defaults."""

    class Meta:
        model = User

    id = factory.LazyFunction(uuid.uuid4)
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Sequence(lambda n: f"First{n}")
    last_name = factory.Sequence(lambda n: f"Last{n}")
    role = "client"
    created_at = factory.LazyFunction(_utc_now)
    updated_at = factory.LazyFunction(_utc_now)


class ServiceFactory(factory.Factory):
    """Generates Service instances with valid duration and price."""

    class Meta:
        model = Service

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Service {n}")
    description = "A test service"
    duration = factory.SubFactory(ServiceDurationFactory)
    price = factory.SubFactory(MoneyFactory)
    is_active = True
    created_at = factory.LazyFunction(_utc_now)


class StaffFactory(factory.Factory):
    """Generates Staff instances."""

    class Meta:
        model = Staff

    id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    created_at = factory.LazyFunction(_utc_now)
    specialty = None
    bio = None
    is_available = True
    service_ids = factory.LazyFunction(frozenset)


class ClientFactory(factory.Factory):
    """Generates Client instances."""

    class Meta:
        model = Client

    id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    created_at = factory.LazyFunction(_utc_now)
    preferred_staff_id = None
    blocked_staff_ids = factory.LazyFunction(frozenset)
    notes = None


class AppointmentFactory(factory.Factory):
    """Generates Appointment instances with a 1-hour slot at 10:00 UTC."""

    class Meta:
        model = Appointment

    id = factory.LazyFunction(uuid.uuid4)
    client_id = factory.LazyFunction(uuid.uuid4)
    staff_id = factory.LazyFunction(uuid.uuid4)
    service_id = factory.LazyFunction(uuid.uuid4)
    time_slot = factory.SubFactory(TimeSlotFactory)
    status = AppointmentStatus.SCHEDULED
