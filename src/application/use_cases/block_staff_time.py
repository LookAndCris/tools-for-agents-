"""BlockStaffTimeUseCase — creates a time-off block for a staff member."""
from __future__ import annotations

import uuid

from application.dto.commands import BlockStaffTimeCommand
from application.dto.responses import StaffTimeOffResponse
from application.dto.user_context import UserContext
from application.exceptions import NotFoundError, ValidationError
from domain.entities.staff_time_off import StaffTimeOff
from domain.repositories.staff_repository import StaffRepository
from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
from domain.value_objects.time_slot import TimeSlot
from domain.exceptions import InvalidTimeSlotError


class BlockStaffTimeUseCase:
    """Command use case: block a time period for a staff member.

    Validates that the staff member exists and the time range is valid,
    then creates a ``StaffTimeOff`` entity and persists it.
    Calls ``flush()`` — does NOT commit.
    """

    def __init__(
        self,
        staff_repo: StaffRepository,
        time_off_repo: StaffTimeOffRepository,
    ) -> None:
        self._staff_repo = staff_repo
        self._time_off_repo = time_off_repo

    async def execute(
        self, cmd: BlockStaffTimeCommand, caller: UserContext
    ) -> StaffTimeOffResponse:
        """Block a time period for the given staff member.

        Args:
            cmd: BlockStaffTimeCommand with staff_id, start_time, end_time, reason.
            caller: The user context of the actor making the request.

        Returns:
            StaffTimeOffResponse representing the created time-off block.

        Raises:
            NotFoundError: If the staff member does not exist.
            ValidationError: If start_time >= end_time.
        """
        # --- 1. Validate staff exists ---
        staff = await self._staff_repo.get_by_id(cmd.staff_id)
        if staff is None:
            raise NotFoundError("Staff", cmd.staff_id)

        # --- 2. Build TimeSlot (validates start < end) ---
        try:
            time_slot = TimeSlot(start=cmd.start_time, end=cmd.end_time)
        except InvalidTimeSlotError as exc:
            raise ValidationError(str(exc)) from exc

        # --- 3. Create domain entity ---
        entity = StaffTimeOff(
            id=uuid.uuid4(),
            staff_id=cmd.staff_id,
            time_slot=time_slot,
            reason=cmd.reason,
        )

        # --- 4. Persist (flush is called inside save()) ---
        saved = await self._time_off_repo.save(entity)

        return StaffTimeOffResponse.from_entity(saved)
