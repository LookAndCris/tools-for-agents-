"""AddWaitlistUseCase — add a client to the waitlist for a service."""
from __future__ import annotations

import uuid

from application.dto.commands import AddWaitlistCommand
from application.dto.responses import WaitlistEntryResponse
from application.exceptions import NotFoundError
from domain.entities.waitlist_entry import WaitlistEntry
from domain.repositories.client_repository import ClientRepository
from domain.repositories.service_repository import ServiceRepository
from domain.repositories.staff_repository import StaffRepository
from domain.repositories.waitlist_entry_repository import WaitlistEntryRepository
from domain.value_objects.waitlist_status import WaitlistStatus


class AddWaitlistUseCase:
    """Command use case: add a client to the waitlist for a service.

    Validates that the client and service exist, optionally validates preferred
    staff, then creates and saves the entry.  Duplicate PENDING entries for the
    same client+service are ALLOWED per spec.
    Calls session.flush() via repository — does NOT commit.
    """

    def __init__(
        self,
        service_repo: ServiceRepository,
        staff_repo: StaffRepository,
        waitlist_repo: WaitlistEntryRepository,
        client_repo: ClientRepository,
    ) -> None:
        self._service_repo = service_repo
        self._staff_repo = staff_repo
        self._waitlist_repo = waitlist_repo
        self._client_repo = client_repo

    async def execute(self, cmd: AddWaitlistCommand) -> WaitlistEntryResponse:
        """Add a client to the waitlist.

        Args:
            cmd: AddWaitlistCommand with client, service, and optional preferences.

        Returns:
            WaitlistEntryResponse representing the created waitlist entry.

        Raises:
            NotFoundError: If the client, service, or preferred staff does not exist.
        """
        # --- 1. Validate client exists ---
        client = await self._client_repo.get_by_id(cmd.client_id)
        if client is None:
            raise NotFoundError("Client", cmd.client_id)

        # --- 2. Validate service exists ---
        service = await self._service_repo.get_by_id(cmd.service_id)
        if service is None:
            raise NotFoundError("Service", cmd.service_id)

        # --- 3. Validate preferred staff exists (if provided) ---
        if cmd.preferred_staff_id is not None:
            staff = await self._staff_repo.get_by_id(cmd.preferred_staff_id)
            if staff is None:
                raise NotFoundError("Staff", cmd.preferred_staff_id)

        # --- 4. Create WaitlistEntry entity ---
        # Duplicate PENDING entries for same client+service are intentionally allowed.
        entry = WaitlistEntry(
            id=uuid.uuid4(),
            client_id=cmd.client_id,
            service_id=cmd.service_id,
            preferred_staff_id=cmd.preferred_staff_id,
            preferred_start=cmd.preferred_start,
            preferred_end=cmd.preferred_end,
            status=WaitlistStatus.PENDING,
            notes=cmd.notes,
        )

        # --- 5. Persist (flush, no commit) ---
        saved = await self._waitlist_repo.save(entry)

        return WaitlistEntryResponse.from_entity(saved)
