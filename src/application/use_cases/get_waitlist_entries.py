"""GetWaitlistEntriesUseCase — retrieve waitlist entries for a client."""
from __future__ import annotations

from uuid import UUID

from application.dto.responses import WaitlistEntryResponse
from domain.repositories.waitlist_entry_repository import WaitlistEntryRepository


class GetWaitlistEntriesUseCase:
    """Query use case: get all waitlist entries for a client.

    Read-only — no flush or commit needed.
    """

    def __init__(self, waitlist_repo: WaitlistEntryRepository) -> None:
        self._waitlist_repo = waitlist_repo

    async def execute(self, client_id: UUID) -> list[WaitlistEntryResponse]:
        """Return all waitlist entries for the given client.

        Args:
            client_id: The UUID of the client whose entries to retrieve.

        Returns:
            List of WaitlistEntryResponse (may be empty).
        """
        entries = await self._waitlist_repo.find_by_client(client_id)
        return [WaitlistEntryResponse.from_entity(entry) for entry in entries]
