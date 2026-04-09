"""UnblockStaffTimeUseCase — removes a time-off block for a staff member."""
from __future__ import annotations

from application.dto.commands import UnblockStaffTimeCommand
from application.dto.user_context import UserContext
from application.exceptions import NotFoundError
from domain.repositories.staff_time_off_repository import StaffTimeOffRepository


class UnblockStaffTimeUseCase:
    """Command use case: remove a time-off block by ID.

    Validates that the time-off block exists, then deletes it.
    Calls ``flush()`` (via delete()) — does NOT commit.
    """

    def __init__(self, time_off_repo: StaffTimeOffRepository) -> None:
        self._time_off_repo = time_off_repo

    async def execute(
        self, cmd: UnblockStaffTimeCommand, caller: UserContext
    ) -> None:
        """Remove the specified time-off block.

        Args:
            cmd: UnblockStaffTimeCommand with time_off_id.
            caller: The user context of the actor making the request.

        Returns:
            None on success.

        Raises:
            NotFoundError: If the time-off block does not exist.
        """
        # --- 1. Validate time-off exists ---
        time_off = await self._time_off_repo.get_by_id(cmd.time_off_id)
        if time_off is None:
            raise NotFoundError("StaffTimeOff", cmd.time_off_id)

        # --- 2. Delete (flush is called inside delete()) ---
        await self._time_off_repo.delete(cmd.time_off_id)
