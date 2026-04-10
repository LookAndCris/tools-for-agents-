"""WaitlistEntryRepository ABC — persistence contract for WaitlistEntry entities."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.waitlist_entry import WaitlistEntry


class WaitlistEntryRepository(ABC):
    """Abstract repository for WaitlistEntry persistence operations."""

    @abstractmethod
    async def save(self, entry: WaitlistEntry) -> WaitlistEntry:
        """Persist a new or updated WaitlistEntry and return it."""
        ...

    @abstractmethod
    async def get_by_id(self, id: UUID) -> WaitlistEntry | None:
        """Return the WaitlistEntry with the given ID, or None if not found."""
        ...

    @abstractmethod
    async def find_pending_by_service(
        self,
        service_id: UUID,
        staff_id: UUID | None = None,
    ) -> list[WaitlistEntry]:
        """Return pending waitlist entries for a service, ordered by created_at ASC (FIFO).

        Optionally filter by preferred_staff_id.
        """
        ...

    @abstractmethod
    async def find_by_client(self, client_id: UUID) -> list[WaitlistEntry]:
        """Return all waitlist entries for the given client."""
        ...
