"""Tests for the Client entity."""
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from domain.entities.client import Client


def now():
    return datetime.now(timezone.utc)


def make_client(**kwargs):
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        preferred_staff_id=None,
        blocked_staff_ids=frozenset(),
        notes=None,
        created_at=now(),
    )
    defaults.update(kwargs)
    return Client(**defaults)


class TestClientPreferences:
    def test_prefers_staff_when_set(self):
        sid = uuid4()
        client = make_client(preferred_staff_id=sid)
        assert client.prefers_staff(sid) is True

    def test_not_prefers_staff_when_different(self):
        client = make_client(preferred_staff_id=uuid4())
        assert client.prefers_staff(uuid4()) is False

    def test_no_preference_returns_false(self):
        client = make_client(preferred_staff_id=None)
        assert client.prefers_staff(uuid4()) is False


class TestClientBlockedStaff:
    def test_has_blocked_when_in_set(self):
        sid = uuid4()
        client = make_client(blocked_staff_ids=frozenset([sid]))
        assert client.has_blocked(sid) is True

    def test_not_blocked_when_not_in_set(self):
        client = make_client(blocked_staff_ids=frozenset())
        assert client.has_blocked(uuid4()) is False
