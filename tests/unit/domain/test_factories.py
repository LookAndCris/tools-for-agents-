"""Tests for domain Factory-Boy factories."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

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
from domain.value_objects.appointment_status import AppointmentStatus
from domain.value_objects.time_slot import TimeSlot
from domain.value_objects.money import Money
from domain.value_objects.service_duration import ServiceDuration
from domain.entities.appointment import Appointment
from domain.entities.user import User
from domain.entities.service import Service
from domain.entities.staff import Staff
from domain.entities.client import Client


class TestTimeSlotFactory:
    def test_creates_valid_time_slot(self):
        slot = TimeSlotFactory()
        assert isinstance(slot, TimeSlot)

    def test_slot_is_utc_aware(self):
        slot = TimeSlotFactory()
        assert slot.start.tzinfo is not None
        assert slot.end.tzinfo is not None

    def test_start_before_end(self):
        slot = TimeSlotFactory()
        assert slot.start < slot.end

    def test_unique_instances_by_default(self):
        s1 = TimeSlotFactory()
        s2 = TimeSlotFactory()
        assert isinstance(s1, TimeSlot)
        assert isinstance(s2, TimeSlot)


class TestMoneyFactory:
    def test_creates_valid_money(self):
        m = MoneyFactory()
        assert isinstance(m, Money)
        assert m.amount == Decimal("100.00")
        assert m.currency == "USD"

    def test_override_amount(self):
        m = MoneyFactory(amount=Decimal("50.00"))
        assert m.amount == Decimal("50.00")


class TestServiceDurationFactory:
    def test_creates_valid_service_duration(self):
        sd = ServiceDurationFactory()
        assert isinstance(sd, ServiceDuration)
        assert sd.duration_minutes == 60
        assert sd.buffer_before == 0
        assert sd.buffer_after == 0

    def test_total_equals_duration(self):
        sd = ServiceDurationFactory()
        assert sd.total == 60


class TestUserFactory:
    def test_creates_valid_user(self):
        user = UserFactory()
        assert isinstance(user, User)
        assert isinstance(user.id, uuid.UUID)
        assert "@" in user.email

    def test_unique_emails(self):
        u1 = UserFactory()
        u2 = UserFactory()
        assert u1.email != u2.email


class TestServiceFactory:
    def test_creates_valid_service(self):
        service = ServiceFactory()
        assert isinstance(service, Service)
        assert service.name
        assert service.is_active is True

    def test_has_duration_subfactory(self):
        service = ServiceFactory()
        assert isinstance(service.duration, ServiceDuration)

    def test_has_money_subfactory(self):
        service = ServiceFactory()
        assert isinstance(service.price, Money)


class TestStaffFactory:
    def test_creates_valid_staff(self):
        staff = StaffFactory()
        assert isinstance(staff, Staff)
        assert isinstance(staff.id, uuid.UUID)

    def test_service_ids_is_frozenset(self):
        staff = StaffFactory()
        assert isinstance(staff.service_ids, frozenset)


class TestClientFactory:
    def test_creates_valid_client(self):
        client = ClientFactory()
        assert isinstance(client, Client)
        assert isinstance(client.id, uuid.UUID)

    def test_default_no_preferences(self):
        client = ClientFactory()
        assert client.preferred_staff_id is None
        assert len(client.blocked_staff_ids) == 0


class TestAppointmentFactory:
    def test_creates_valid_appointment(self):
        appt = AppointmentFactory()
        assert isinstance(appt, Appointment)
        assert appt.status == AppointmentStatus.SCHEDULED

    def test_has_time_slot(self):
        appt = AppointmentFactory()
        assert isinstance(appt.time_slot, TimeSlot)

    def test_all_ids_are_uuids(self):
        appt = AppointmentFactory()
        assert isinstance(appt.id, uuid.UUID)
        assert isinstance(appt.client_id, uuid.UUID)
        assert isinstance(appt.staff_id, uuid.UUID)
        assert isinstance(appt.service_id, uuid.UUID)

    def test_override_status(self):
        appt = AppointmentFactory(status=AppointmentStatus.CONFIRMED)
        assert appt.status == AppointmentStatus.CONFIRMED
