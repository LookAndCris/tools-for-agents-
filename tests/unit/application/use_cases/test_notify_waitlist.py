"""Unit tests for NotifyWaitlistUseCase (Task 3.1 — RED phase).

Tests:
- Returns empty list when no PENDING entries exist
- FIFO order: notifies entries in created_at ASC order
- Soft staff filter: passes staff_id to repo query
- Each notified entry transitions to NOTIFIED status
- Creates a WaitlistNotification record per notified entry
- Notifications include expires_at
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, call

import pytest

from application.dto.commands import NotifyWaitlistCommand
from application.dto.responses import WaitlistEntryResponse
from domain.entities.waitlist_entry import WaitlistEntry
from domain.entities.waitlist_notification import WaitlistNotification
from domain.repositories.waitlist_entry_repository import WaitlistEntryRepository
from domain.repositories.waitlist_notification_repository import WaitlistNotificationRepository
from domain.value_objects.waitlist_status import WaitlistStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _make_pending_entry(
    service_id: uuid.UUID,
    offset_seconds: int = 0,
) -> WaitlistEntry:
    return WaitlistEntry(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        service_id=service_id,
        created_at=_utcnow() - timedelta(seconds=offset_seconds),
    )


class TestNotifyWaitlistUseCase:
    """Unit tests for NotifyWaitlistUseCase."""

    @pytest.fixture
    def waitlist_repo(self):
        return AsyncMock(spec=WaitlistEntryRepository)

    @pytest.fixture
    def notification_repo(self):
        return AsyncMock(spec=WaitlistNotificationRepository)

    @pytest.fixture
    def service_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def use_case(self, waitlist_repo, notification_repo):
        from application.use_cases.notify_waitlist import NotifyWaitlistUseCase
        return NotifyWaitlistUseCase(
            waitlist_repo=waitlist_repo,
            notification_repo=notification_repo,
        )

    async def test_returns_empty_list_when_no_pending_entries(
        self, use_case, waitlist_repo, notification_repo, service_id
    ):
        """execute() returns empty list when no PENDING entries exist."""
        waitlist_repo.find_pending_by_service.return_value = []

        cmd = NotifyWaitlistCommand(service_id=service_id)
        result = await use_case.execute(cmd)

        assert result == []
        notification_repo.save.assert_not_called()

    async def test_notifies_single_pending_entry(
        self, use_case, waitlist_repo, notification_repo, service_id
    ):
        """execute() notifies a single PENDING entry and returns its response."""
        entry = _make_pending_entry(service_id)
        waitlist_repo.find_pending_by_service.return_value = [entry]

        def _save_entry_passthrough(e: WaitlistEntry) -> WaitlistEntry:
            return e

        def _save_notif_passthrough(n: WaitlistNotification) -> WaitlistNotification:
            return n

        waitlist_repo.save = AsyncMock(side_effect=_save_entry_passthrough)
        notification_repo.save = AsyncMock(side_effect=_save_notif_passthrough)

        cmd = NotifyWaitlistCommand(service_id=service_id)
        result = await use_case.execute(cmd)

        assert len(result) == 1
        assert isinstance(result[0], WaitlistEntryResponse)
        assert result[0].status == WaitlistStatus.NOTIFIED.value
        assert entry.status == WaitlistStatus.NOTIFIED

    async def test_notifies_multiple_entries_fifo_order(
        self, use_case, waitlist_repo, notification_repo, service_id
    ):
        """execute() returns notified entries in the order provided (FIFO from repo)."""
        entry1 = _make_pending_entry(service_id, offset_seconds=10)
        entry2 = _make_pending_entry(service_id, offset_seconds=5)
        entry3 = _make_pending_entry(service_id, offset_seconds=0)
        # Repo returns in FIFO order (oldest first)
        waitlist_repo.find_pending_by_service.return_value = [entry1, entry2, entry3]

        def _save_entry_passthrough(e: WaitlistEntry) -> WaitlistEntry:
            return e

        def _save_notif_passthrough(n: WaitlistNotification) -> WaitlistNotification:
            return n

        waitlist_repo.save = AsyncMock(side_effect=_save_entry_passthrough)
        notification_repo.save = AsyncMock(side_effect=_save_notif_passthrough)

        cmd = NotifyWaitlistCommand(service_id=service_id)
        result = await use_case.execute(cmd)

        assert len(result) == 3
        assert result[0].id == entry1.id
        assert result[1].id == entry2.id
        assert result[2].id == entry3.id

    async def test_passes_staff_id_filter_to_repo(
        self, use_case, waitlist_repo, notification_repo, service_id
    ):
        """execute() passes staff_id to find_pending_by_service when provided."""
        waitlist_repo.find_pending_by_service.return_value = []
        staff_id = uuid.uuid4()

        cmd = NotifyWaitlistCommand(service_id=service_id, staff_id=staff_id)
        await use_case.execute(cmd)

        waitlist_repo.find_pending_by_service.assert_called_once_with(
            service_id, staff_id=staff_id
        )

    async def test_creates_notification_record_per_entry(
        self, use_case, waitlist_repo, notification_repo, service_id
    ):
        """execute() creates one WaitlistNotification per notified entry."""
        entry1 = _make_pending_entry(service_id)
        entry2 = _make_pending_entry(service_id)
        waitlist_repo.find_pending_by_service.return_value = [entry1, entry2]

        def _save_entry_passthrough(e: WaitlistEntry) -> WaitlistEntry:
            return e

        def _save_notif_passthrough(n: WaitlistNotification) -> WaitlistNotification:
            return n

        waitlist_repo.save = AsyncMock(side_effect=_save_entry_passthrough)
        notification_repo.save = AsyncMock(side_effect=_save_notif_passthrough)

        cmd = NotifyWaitlistCommand(service_id=service_id)
        await use_case.execute(cmd)

        assert notification_repo.save.call_count == 2

    async def test_notification_includes_expires_at(
        self, use_case, waitlist_repo, notification_repo, service_id
    ):
        """execute() sets expires_at on the WaitlistNotification."""
        entry = _make_pending_entry(service_id)
        waitlist_repo.find_pending_by_service.return_value = [entry]

        saved_notifications: list[WaitlistNotification] = []

        def _save_entry_passthrough(e: WaitlistEntry) -> WaitlistEntry:
            return e

        async def _capture_notification(n: WaitlistNotification) -> WaitlistNotification:
            saved_notifications.append(n)
            return n

        waitlist_repo.save = AsyncMock(side_effect=_save_entry_passthrough)
        notification_repo.save = AsyncMock(side_effect=_capture_notification)

        cmd = NotifyWaitlistCommand(service_id=service_id)
        await use_case.execute(cmd)

        assert len(saved_notifications) == 1
        assert saved_notifications[0].expires_at is not None

    async def test_no_staff_id_filter_when_none(
        self, use_case, waitlist_repo, notification_repo, service_id
    ):
        """execute() calls find_pending_by_service with staff_id=None when not provided."""
        waitlist_repo.find_pending_by_service.return_value = []

        cmd = NotifyWaitlistCommand(service_id=service_id)
        await use_case.execute(cmd)

        waitlist_repo.find_pending_by_service.assert_called_once_with(
            service_id, staff_id=None
        )
