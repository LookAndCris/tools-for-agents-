"""Tests for the Staff entity."""
from datetime import datetime, timezone
from uuid import uuid4, UUID
import pytest
from domain.entities.staff import Staff


def now():
    return datetime.now(timezone.utc)


def make_staff(**kwargs):
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        specialty="Barbering",
        bio="Expert barber",
        is_available=True,
        service_ids=frozenset(),
        created_at=now(),
    )
    defaults.update(kwargs)
    return Staff(**defaults)


class TestStaffOffersService:
    def test_offers_service_when_in_set(self):
        sid = uuid4()
        staff = make_staff(service_ids=frozenset([sid]))
        assert staff.offers_service(sid) is True

    def test_not_offers_service_when_not_in_set(self):
        staff = make_staff(service_ids=frozenset())
        assert staff.offers_service(uuid4()) is False


class TestStaffAddRemoveService:
    def test_add_service(self):
        staff = make_staff(service_ids=frozenset())
        sid = uuid4()
        staff.add_service(sid)
        assert staff.offers_service(sid) is True

    def test_remove_service(self):
        sid = uuid4()
        staff = make_staff(service_ids=frozenset([sid]))
        staff.remove_service(sid)
        assert staff.offers_service(sid) is False

    def test_remove_nonexistent_is_noop(self):
        staff = make_staff(service_ids=frozenset())
        staff.remove_service(uuid4())  # should not raise
        assert len(staff.service_ids) == 0
