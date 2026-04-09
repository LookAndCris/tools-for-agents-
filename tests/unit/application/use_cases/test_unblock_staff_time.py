"""Unit tests for UnblockStaffTimeUseCase (Task 5.3 - RED phase)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
from domain.value_objects.time_slot import TimeSlot


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def _make_staff_time_off(staff_id: uuid.UUID | None = None) -> object:
    """Create a StaffTimeOff entity for testing."""
    from domain.entities.staff_time_off import StaffTimeOff

    return StaffTimeOff(
        id=uuid.uuid4(),
        staff_id=staff_id or uuid.uuid4(),
        time_slot=TimeSlot(
            start=_utc(2026, 6, 10, 9),
            end=_utc(2026, 6, 10, 17),
        ),
        reason="Annual leave",
    )


class TestUnblockStaffTimeUseCase:
    """Unit tests for UnblockStaffTimeUseCase."""

    @pytest.fixture
    def time_off_repo(self):
        return AsyncMock(spec=StaffTimeOffRepository)

    @pytest.fixture
    def time_off_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def time_off_entity(self):
        return _make_staff_time_off()

    @pytest.fixture
    def caller(self):
        from application.dto.user_context import UserContext

        return UserContext(user_id=uuid.uuid4(), role="admin")

    @pytest.fixture
    def cmd(self, time_off_id):
        from application.dto.commands import UnblockStaffTimeCommand

        return UnblockStaffTimeCommand(time_off_id=time_off_id)

    @pytest.fixture
    def uc(self, time_off_repo):
        from application.use_cases.unblock_staff_time import UnblockStaffTimeUseCase

        return UnblockStaffTimeUseCase(time_off_repo=time_off_repo)

    # ------------------------------------------------------------------ #
    # Happy path
    # ------------------------------------------------------------------ #

    async def test_unblocks_staff_time_successfully(
        self, uc, cmd, caller, time_off_entity, time_off_repo
    ):
        """Successful unblock returns None (or no error)."""
        time_off_repo.get_by_id.return_value = time_off_entity
        time_off_repo.delete.return_value = None

        # Should not raise
        result = await uc.execute(cmd, caller)

        # Use case returns None on success
        assert result is None

    async def test_unblocks_calls_delete_with_correct_id(
        self, uc, cmd, caller, time_off_id, time_off_entity, time_off_repo
    ):
        """delete() is called exactly once with the correct ID."""
        time_off_repo.get_by_id.return_value = time_off_entity
        time_off_repo.delete.return_value = None

        await uc.execute(cmd, caller)

        time_off_repo.delete.assert_called_once_with(time_off_id)

    async def test_unblocks_checks_existence_before_deleting(
        self, uc, cmd, caller, time_off_entity, time_off_repo
    ):
        """get_by_id() is called before delete() to validate the block exists."""
        time_off_repo.get_by_id.return_value = time_off_entity
        time_off_repo.delete.return_value = None

        await uc.execute(cmd, caller)

        time_off_repo.get_by_id.assert_called_once_with(cmd.time_off_id)

    # ------------------------------------------------------------------ #
    # Time-off not found
    # ------------------------------------------------------------------ #

    async def test_raises_not_found_when_time_off_missing(
        self, uc, cmd, caller, time_off_repo
    ):
        """NotFoundError raised when the time-off block does not exist."""
        from application.exceptions import NotFoundError

        time_off_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await uc.execute(cmd, caller)

        assert "NOT_FOUND" in exc_info.value.code
        time_off_repo.delete.assert_not_called()
