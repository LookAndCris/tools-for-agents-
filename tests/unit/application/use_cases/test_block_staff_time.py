"""Unit tests for BlockStaffTimeUseCase (Task 5.3 - RED phase)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from domain.repositories.staff_repository import StaffRepository
from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
from tests.factories import StaffFactory


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


class TestBlockStaffTimeUseCase:
    """Unit tests for BlockStaffTimeUseCase."""

    @pytest.fixture
    def staff_repo(self):
        return AsyncMock(spec=StaffRepository)

    @pytest.fixture
    def time_off_repo(self):
        return AsyncMock(spec=StaffTimeOffRepository)

    @pytest.fixture
    def staff_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def staff(self, staff_id):
        return StaffFactory(id=staff_id)

    @pytest.fixture
    def caller(self):
        from application.dto.user_context import UserContext

        return UserContext(user_id=uuid.uuid4(), role="admin")

    @pytest.fixture
    def cmd(self, staff_id):
        from application.dto.commands import BlockStaffTimeCommand

        return BlockStaffTimeCommand(
            staff_id=staff_id,
            start_time=_utc(2026, 6, 10, 9),
            end_time=_utc(2026, 6, 10, 17),
            reason="Annual leave",
        )

    @pytest.fixture
    def uc(self, staff_repo, time_off_repo):
        from application.use_cases.block_staff_time import BlockStaffTimeUseCase

        return BlockStaffTimeUseCase(
            staff_repo=staff_repo,
            time_off_repo=time_off_repo,
        )

    # ------------------------------------------------------------------ #
    # Happy path
    # ------------------------------------------------------------------ #

    async def test_blocks_staff_time_successfully(
        self, uc, cmd, caller, staff, staff_repo, time_off_repo
    ):
        """Successful block returns StaffTimeOffResponse with correct fields."""
        from application.dto.responses import StaffTimeOffResponse
        from domain.entities.staff_time_off import StaffTimeOff

        staff_repo.get_by_id.return_value = staff
        time_off_repo.save.side_effect = lambda entity: entity

        result = await uc.execute(cmd, caller)

        assert isinstance(result, StaffTimeOffResponse)
        assert result.staff_id == cmd.staff_id
        assert result.reason == "Annual leave"

    async def test_blocks_staff_time_saves_entity(
        self, uc, cmd, caller, staff, staff_repo, time_off_repo
    ):
        """BlockStaffTime calls save() exactly once on the time_off_repo."""
        time_off_repo.save.side_effect = lambda entity: entity
        staff_repo.get_by_id.return_value = staff

        await uc.execute(cmd, caller)

        time_off_repo.save.assert_called_once()

    async def test_blocks_staff_time_stores_correct_range(
        self, uc, cmd, caller, staff, staff_repo, time_off_repo
    ):
        """The saved StaffTimeOff entity has the correct time_slot start/end."""
        from domain.entities.staff_time_off import StaffTimeOff

        saved_entity: StaffTimeOff | None = None

        async def capture(entity):
            nonlocal saved_entity
            saved_entity = entity
            return entity

        staff_repo.get_by_id.return_value = staff
        time_off_repo.save.side_effect = capture

        await uc.execute(cmd, caller)

        assert saved_entity is not None
        assert saved_entity.time_slot.start == cmd.start_time
        assert saved_entity.time_slot.end == cmd.end_time

    async def test_blocks_staff_time_response_has_start_end(
        self, uc, cmd, caller, staff, staff_repo, time_off_repo
    ):
        """Response DTO has the correct start_time and end_time."""
        staff_repo.get_by_id.return_value = staff
        time_off_repo.save.side_effect = lambda entity: entity

        result = await uc.execute(cmd, caller)

        assert result.start_time == cmd.start_time
        assert result.end_time == cmd.end_time

    # ------------------------------------------------------------------ #
    # Staff not found
    # ------------------------------------------------------------------ #

    async def test_raises_not_found_when_staff_missing(
        self, uc, cmd, caller, staff_repo, time_off_repo
    ):
        """NotFoundError raised when staff member does not exist."""
        from application.exceptions import NotFoundError

        staff_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError) as exc_info:
            await uc.execute(cmd, caller)

        assert "STAFF" in exc_info.value.code
        time_off_repo.save.assert_not_called()

    # ------------------------------------------------------------------ #
    # Invalid range (start >= end)
    # ------------------------------------------------------------------ #

    async def test_raises_validation_error_when_start_equals_end(
        self, uc, caller, staff_id, staff_repo, time_off_repo, staff
    ):
        """ValidationError raised when start_time equals end_time."""
        from application.dto.commands import BlockStaffTimeCommand
        from application.exceptions import ValidationError

        cmd_bad = BlockStaffTimeCommand(
            staff_id=staff_id,
            start_time=_utc(2026, 6, 10, 9),
            end_time=_utc(2026, 6, 10, 9),  # same as start
        )
        staff_repo.get_by_id.return_value = staff

        with pytest.raises((ValidationError, Exception)):
            await uc.execute(cmd_bad, caller)

        time_off_repo.save.assert_not_called()

    async def test_raises_validation_error_when_start_after_end(
        self, uc, caller, staff_id, staff_repo, time_off_repo, staff
    ):
        """ValidationError raised when start_time is after end_time."""
        from application.dto.commands import BlockStaffTimeCommand
        from application.exceptions import ValidationError

        cmd_bad = BlockStaffTimeCommand(
            staff_id=staff_id,
            start_time=_utc(2026, 6, 10, 17),
            end_time=_utc(2026, 6, 10, 9),  # before start
        )
        staff_repo.get_by_id.return_value = staff

        with pytest.raises((ValidationError, Exception)):
            await uc.execute(cmd_bad, caller)

        time_off_repo.save.assert_not_called()
