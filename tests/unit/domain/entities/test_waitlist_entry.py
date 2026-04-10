"""Tests for WaitlistEntry and WaitlistNotification entities (Task 1.1 — RED phase)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest


def _utc(year, month, day, hour=0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


class TestWaitlistEntryCreation:
    def test_minimal_construction(self):
        from domain.entities.waitlist_entry import WaitlistEntry
        from domain.value_objects.waitlist_status import WaitlistStatus

        entry = WaitlistEntry(
            id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
        )
        assert entry.status == WaitlistStatus.PENDING
        assert entry.preferred_staff_id is None
        assert entry.preferred_start is None
        assert entry.preferred_end is None

    def test_full_construction(self):
        from domain.entities.waitlist_entry import WaitlistEntry
        from domain.value_objects.waitlist_status import WaitlistStatus

        cid = uuid.uuid4()
        sid = uuid.uuid4()
        stid = uuid.uuid4()
        start = _utc(2026, 6, 1, 10)
        end = _utc(2026, 6, 1, 12)
        eid = uuid.uuid4()

        entry = WaitlistEntry(
            id=eid,
            client_id=cid,
            service_id=sid,
            preferred_staff_id=stid,
            preferred_start=start,
            preferred_end=end,
            status=WaitlistStatus.PENDING,
        )
        assert entry.id == eid
        assert entry.client_id == cid
        assert entry.service_id == sid
        assert entry.preferred_staff_id == stid
        assert entry.preferred_start == start
        assert entry.preferred_end == end

    def test_created_at_defaults_to_now(self):
        from domain.entities.waitlist_entry import WaitlistEntry

        entry = WaitlistEntry(
            id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
        )
        assert entry.created_at is not None
        assert entry.created_at.tzinfo is not None

    def test_created_at_can_be_set_explicitly(self):
        from domain.entities.waitlist_entry import WaitlistEntry

        ts = _utc(2026, 5, 1, 9)
        entry = WaitlistEntry(
            id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            created_at=ts,
        )
        assert entry.created_at == ts


class TestWaitlistEntryNotify:
    def test_notify_transitions_pending_to_notified(self):
        from domain.entities.waitlist_entry import WaitlistEntry
        from domain.value_objects.waitlist_status import WaitlistStatus

        entry = WaitlistEntry(
            id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            status=WaitlistStatus.PENDING,
        )
        entry.notify()
        assert entry.status == WaitlistStatus.NOTIFIED

    def test_notify_raises_on_non_pending(self):
        from domain.entities.waitlist_entry import WaitlistEntry
        from domain.value_objects.waitlist_status import WaitlistStatus
        from domain.exceptions import InvalidStatusTransitionError

        entry = WaitlistEntry(
            id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            status=WaitlistStatus.NOTIFIED,
        )
        with pytest.raises(InvalidStatusTransitionError):
            entry.notify()

    def test_notify_raises_on_expired(self):
        from domain.entities.waitlist_entry import WaitlistEntry
        from domain.value_objects.waitlist_status import WaitlistStatus
        from domain.exceptions import InvalidStatusTransitionError

        entry = WaitlistEntry(
            id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            status=WaitlistStatus.EXPIRED,
        )
        with pytest.raises(InvalidStatusTransitionError):
            entry.notify()

    def test_duplicate_entries_allowed_same_client_service(self):
        """Duplicates are allowed — no unique constraint enforced in entity."""
        from domain.entities.waitlist_entry import WaitlistEntry

        client_id = uuid.uuid4()
        service_id = uuid.uuid4()

        entry1 = WaitlistEntry(id=uuid.uuid4(), client_id=client_id, service_id=service_id)
        entry2 = WaitlistEntry(id=uuid.uuid4(), client_id=client_id, service_id=service_id)

        # Both can be instantiated — duplicates are allowed
        assert entry1.client_id == entry2.client_id
        assert entry1.service_id == entry2.service_id
        assert entry1.id != entry2.id


class TestWaitlistNotificationCreation:
    def test_minimal_construction(self):
        from domain.entities.waitlist_notification import WaitlistNotification

        wn = WaitlistNotification(
            id=uuid.uuid4(),
            waitlist_entry_id=uuid.uuid4(),
        )
        assert wn.appointment_id is None
        assert wn.notified_at is not None
        assert wn.expires_at is None

    def test_full_construction(self):
        from domain.entities.waitlist_notification import WaitlistNotification

        wid = uuid.uuid4()
        eid = uuid.uuid4()
        apid = uuid.uuid4()
        notified = _utc(2026, 6, 1, 10)
        expires = _utc(2026, 6, 2, 10)

        wn = WaitlistNotification(
            id=wid,
            waitlist_entry_id=eid,
            appointment_id=apid,
            notified_at=notified,
            expires_at=expires,
        )
        assert wn.id == wid
        assert wn.waitlist_entry_id == eid
        assert wn.appointment_id == apid
        assert wn.notified_at == notified
        assert wn.expires_at == expires
