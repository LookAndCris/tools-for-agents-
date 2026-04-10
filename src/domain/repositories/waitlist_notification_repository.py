"""WaitlistNotificationRepository ABC — persistence contract for WaitlistNotification entities."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.waitlist_notification import WaitlistNotification


class WaitlistNotificationRepository(ABC):
    """Abstract repository for WaitlistNotification persistence operations."""

    @abstractmethod
    async def save(self, notification: WaitlistNotification) -> WaitlistNotification:
        """Persist a new WaitlistNotification and return it."""
        ...

    @abstractmethod
    async def find_by_waitlist_entry(self, waitlist_entry_id: UUID) -> list[WaitlistNotification]:
        """Return all notifications for the given waitlist entry."""
        ...
