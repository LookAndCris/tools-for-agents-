"""NotifyWaitlistUseCase — notify pending waitlist entries for a service."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from application.dto.commands import NotifyWaitlistCommand
from application.dto.responses import WaitlistEntryResponse
from domain.entities.waitlist_notification import WaitlistNotification
from domain.repositories.waitlist_entry_repository import WaitlistEntryRepository
from domain.repositories.waitlist_notification_repository import WaitlistNotificationRepository


# Default notification window — 48 hours
_NOTIFICATION_EXPIRY_HOURS = 48


class NotifyWaitlistUseCase:
    """Command use case: notify pending waitlist entries for a service.

    Retrieves PENDING entries in FIFO order (created_at ASC), transitions
    each to NOTIFIED, creates a WaitlistNotification record, and saves both.
    Calls session.flush() via repository — does NOT commit.
    """

    def __init__(
        self,
        waitlist_repo: WaitlistEntryRepository,
        notification_repo: WaitlistNotificationRepository,
    ) -> None:
        self._waitlist_repo = waitlist_repo
        self._notification_repo = notification_repo

    async def execute(self, cmd: NotifyWaitlistCommand) -> list[WaitlistEntryResponse]:
        """Notify pending waitlist entries for a service.

        Args:
            cmd: NotifyWaitlistCommand with service_id and optional staff_id filter.

        Returns:
            List of WaitlistEntryResponse for each notified entry (may be empty).
        """
        # --- 1. Fetch PENDING entries in FIFO order ---
        pending_entries = await self._waitlist_repo.find_pending_by_service(
            cmd.service_id, staff_id=cmd.staff_id
        )

        if not pending_entries:
            return []

        notified: list[WaitlistEntryResponse] = []
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=_NOTIFICATION_EXPIRY_HOURS)

        for entry in pending_entries:
            # --- 2. Transition entry to NOTIFIED ---
            entry.notify()
            saved_entry = await self._waitlist_repo.save(entry)

            # --- 3. Create notification record ---
            notification = WaitlistNotification(
                id=uuid.uuid4(),
                waitlist_entry_id=entry.id,
                notified_at=now,
                expires_at=expires_at,
            )
            await self._notification_repo.save(notification)

            notified.append(WaitlistEntryResponse.from_entity(saved_entry))

        return notified
