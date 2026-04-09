"""Tests for the Service entity."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
import pytest
from domain.entities.service import Service
from domain.value_objects.service_duration import ServiceDuration
from domain.value_objects.money import Money


def now():
    return datetime.now(timezone.utc)


def make_service(**kwargs):
    defaults = dict(
        id=uuid4(),
        name="Haircut",
        description="Classic haircut",
        duration=ServiceDuration(buffer_before=5, duration_minutes=30, buffer_after=5),
        price=Money(amount=Decimal("25.00"), currency="USD"),
        is_active=True,
        created_at=now(),
    )
    defaults.update(kwargs)
    return Service(**defaults)


class TestServiceCreation:
    def test_valid_creation(self):
        svc = make_service()
        assert svc.name == "Haircut"
        assert svc.is_active is True

    def test_empty_name_raises(self):
        with pytest.raises(ValueError):
            make_service(name="")

    def test_whitespace_name_raises(self):
        with pytest.raises(ValueError):
            make_service(name="   ")


class TestServiceTotalDuration:
    def test_total_duration_delegates_to_duration(self):
        svc = make_service(
            duration=ServiceDuration(buffer_before=5, duration_minutes=60, buffer_after=10)
        )
        assert svc.total_duration_minutes == 75
