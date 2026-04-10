"""Unit tests for AddWaitlistUseCase.

Tests:
- client_id and service_id are validated (NotFoundError if not found)
- Client existence validated (NotFoundError if client missing)
- Duplicate waitlist entries ARE ALLOWED (spec requires this)
- Successful add returns WaitlistEntryResponse
- preferred_staff_id is optional
- notes field is included in command and response
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from application.dto.commands import AddWaitlistCommand
from application.dto.responses import WaitlistEntryResponse
from application.exceptions import NotFoundError
from domain.entities.waitlist_entry import WaitlistEntry
from domain.repositories.waitlist_entry_repository import WaitlistEntryRepository
from domain.repositories.client_repository import ClientRepository
from domain.repositories.service_repository import ServiceRepository
from domain.repositories.staff_repository import StaffRepository
from domain.value_objects.waitlist_status import WaitlistStatus
from tests.factories import ServiceFactory, StaffFactory, ClientFactory


class TestAddWaitlistUseCase:
    """Unit tests for AddWaitlistUseCase."""

    @pytest.fixture
    def service_repo(self):
        return AsyncMock(spec=ServiceRepository)

    @pytest.fixture
    def staff_repo(self):
        return AsyncMock(spec=StaffRepository)

    @pytest.fixture
    def waitlist_repo(self):
        return AsyncMock(spec=WaitlistEntryRepository)

    @pytest.fixture
    def client_repo(self):
        return AsyncMock(spec=ClientRepository)

    @pytest.fixture
    def client_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def service_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def service(self, service_id):
        return ServiceFactory(id=service_id)

    @pytest.fixture
    def client(self, client_id):
        return ClientFactory(id=client_id)

    @pytest.fixture
    def use_case(self, service_repo, staff_repo, waitlist_repo, client_repo):
        from application.use_cases.add_waitlist import AddWaitlistUseCase
        return AddWaitlistUseCase(
            service_repo=service_repo,
            staff_repo=staff_repo,
            waitlist_repo=waitlist_repo,
            client_repo=client_repo,
        )

    async def test_raises_not_found_if_service_missing(
        self, use_case, service_repo, client_repo, waitlist_repo, client_id, service_id, client
    ):
        """execute() raises NotFoundError when service does not exist."""
        client_repo.get_by_id.return_value = client
        service_repo.get_by_id.return_value = None

        cmd = AddWaitlistCommand(client_id=client_id, service_id=service_id)
        with pytest.raises(NotFoundError) as exc_info:
            await use_case.execute(cmd)

        assert "Service" in str(exc_info.value.message)

    async def test_raises_not_found_if_client_missing(
        self, use_case, client_repo, client_id, service_id
    ):
        """execute() raises NotFoundError when client does not exist."""
        client_repo.get_by_id.return_value = None

        cmd = AddWaitlistCommand(client_id=client_id, service_id=service_id)
        with pytest.raises(NotFoundError) as exc_info:
            await use_case.execute(cmd)

        assert "Client" in str(exc_info.value.message)

    async def test_raises_not_found_if_preferred_staff_missing(
        self, use_case, service_repo, staff_repo, waitlist_repo, client_repo, client_id, service_id, service, client
    ):
        """execute() raises NotFoundError when preferred_staff_id is given but not found."""
        client_repo.get_by_id.return_value = client
        service_repo.get_by_id.return_value = service
        staff_repo.get_by_id.return_value = None

        staff_id = uuid.uuid4()
        cmd = AddWaitlistCommand(
            client_id=client_id,
            service_id=service_id,
            preferred_staff_id=staff_id,
        )
        with pytest.raises(NotFoundError) as exc_info:
            await use_case.execute(cmd)

        assert "Staff" in str(exc_info.value.message)

    async def test_allows_duplicate_pending_entry(
        self, use_case, service_repo, waitlist_repo, client_repo, client_id, service_id, service, client
    ):
        """execute() allows duplicate PENDING entries for same client+service (spec requirement)."""
        client_repo.get_by_id.return_value = client
        service_repo.get_by_id.return_value = service
        # Existing PENDING entry for same service — must be ALLOWED
        existing = WaitlistEntry(
            id=uuid.uuid4(),
            client_id=client_id,
            service_id=service_id,
            status=WaitlistStatus.PENDING,
        )
        waitlist_repo.find_by_client.return_value = [existing]

        def _save_passthrough(entry: WaitlistEntry) -> WaitlistEntry:
            return entry

        waitlist_repo.save = AsyncMock(side_effect=_save_passthrough)

        cmd = AddWaitlistCommand(client_id=client_id, service_id=service_id)
        result = await use_case.execute(cmd)

        # Must succeed and return a new entry
        assert isinstance(result, WaitlistEntryResponse)
        assert result.status == WaitlistStatus.PENDING.value

    async def test_successful_add_returns_response(
        self, use_case, service_repo, waitlist_repo, client_repo, client_id, service_id, service, client
    ):
        """execute() creates a new WaitlistEntry and returns WaitlistEntryResponse."""
        client_repo.get_by_id.return_value = client
        service_repo.get_by_id.return_value = service

        def _save_passthrough(entry: WaitlistEntry) -> WaitlistEntry:
            return entry

        waitlist_repo.save = AsyncMock(side_effect=_save_passthrough)

        cmd = AddWaitlistCommand(client_id=client_id, service_id=service_id)
        result = await use_case.execute(cmd)

        assert isinstance(result, WaitlistEntryResponse)
        assert result.client_id == client_id
        assert result.service_id == service_id
        assert result.status == WaitlistStatus.PENDING.value

        waitlist_repo.save.assert_called_once()

    async def test_successful_add_with_notes(
        self, use_case, service_repo, waitlist_repo, client_repo, client_id, service_id, service, client
    ):
        """execute() stores and returns the notes field when provided."""
        client_repo.get_by_id.return_value = client
        service_repo.get_by_id.return_value = service

        def _save_passthrough(entry: WaitlistEntry) -> WaitlistEntry:
            return entry

        waitlist_repo.save = AsyncMock(side_effect=_save_passthrough)

        cmd = AddWaitlistCommand(client_id=client_id, service_id=service_id, notes="Prefer mornings")
        result = await use_case.execute(cmd)

        assert isinstance(result, WaitlistEntryResponse)
        assert result.notes == "Prefer mornings"

    async def test_successful_add_notes_none_by_default(
        self, use_case, service_repo, waitlist_repo, client_repo, client_id, service_id, service, client
    ):
        """execute() returns notes=None when not provided."""
        client_repo.get_by_id.return_value = client
        service_repo.get_by_id.return_value = service

        def _save_passthrough(entry: WaitlistEntry) -> WaitlistEntry:
            return entry

        waitlist_repo.save = AsyncMock(side_effect=_save_passthrough)

        cmd = AddWaitlistCommand(client_id=client_id, service_id=service_id)
        result = await use_case.execute(cmd)

        assert result.notes is None

    async def test_does_not_raise_on_existing_non_pending_entry(
        self, use_case, service_repo, waitlist_repo, client_repo, client_id, service_id, service, client
    ):
        """execute() allows adding to waitlist even if a NOTIFIED entry exists for same service."""
        client_repo.get_by_id.return_value = client
        service_repo.get_by_id.return_value = service
        # Only a NOTIFIED (non-PENDING) entry exists — should be fine
        existing = WaitlistEntry(
            id=uuid.uuid4(),
            client_id=client_id,
            service_id=service_id,
            status=WaitlistStatus.NOTIFIED,
        )
        waitlist_repo.find_by_client.return_value = [existing]

        def _save_passthrough(entry: WaitlistEntry) -> WaitlistEntry:
            return entry

        waitlist_repo.save = AsyncMock(side_effect=_save_passthrough)

        cmd = AddWaitlistCommand(client_id=client_id, service_id=service_id)
        result = await use_case.execute(cmd)

        assert isinstance(result, WaitlistEntryResponse)

    async def test_preferred_staff_not_validated_when_none(
        self, use_case, service_repo, staff_repo, waitlist_repo, client_repo, client_id, service_id, service, client
    ):
        """execute() does not call staff_repo when preferred_staff_id is not provided."""
        client_repo.get_by_id.return_value = client
        service_repo.get_by_id.return_value = service

        def _save_passthrough(entry: WaitlistEntry) -> WaitlistEntry:
            return entry

        waitlist_repo.save = AsyncMock(side_effect=_save_passthrough)

        cmd = AddWaitlistCommand(client_id=client_id, service_id=service_id)
        await use_case.execute(cmd)

        staff_repo.get_by_id.assert_not_called()
