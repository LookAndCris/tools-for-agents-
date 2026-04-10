"""Staff time-off router — manage staff unavailability blocks.

Both endpoints require authentication. Write endpoints commit on success.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.commands import BlockStaffTimeCommand, UnblockStaffTimeCommand
from application.dto.responses import StaffTimeOffResponse
from application.dto.user_context import UserContext
from application.use_cases.block_staff_time import BlockStaffTimeUseCase
from application.use_cases.unblock_staff_time import UnblockStaffTimeUseCase
from infrastructure.database.session import get_session
from interfaces.api.dependencies import (
    get_block_staff_time_uc,
    get_current_user,
    get_unblock_staff_time_uc,
)

router = APIRouter()


@router.post("/", status_code=201, response_model=StaffTimeOffResponse)
async def block_staff_time(
    cmd: BlockStaffTimeCommand,
    caller: UserContext = Depends(get_current_user),
    uc: BlockStaffTimeUseCase = Depends(get_block_staff_time_uc),
    session: AsyncSession = Depends(get_session),
) -> StaffTimeOffResponse:
    """Block a time period for a staff member (create time-off record).

    Returns 201 on success.
    Returns 404 if the staff member does not exist.
    Returns 400 if the time range is invalid (start >= end).
    """
    result = await uc.execute(cmd, caller)
    await session.commit()
    return result


@router.delete("/{time_off_id}", status_code=204)
async def unblock_staff_time(
    time_off_id: UUID,
    caller: UserContext = Depends(get_current_user),
    uc: UnblockStaffTimeUseCase = Depends(get_unblock_staff_time_uc),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Remove a staff time-off block.

    Returns 204 No Content on success.
    Returns 404 if the time-off record does not exist.
    """
    cmd = UnblockStaffTimeCommand(time_off_id=time_off_id)
    await uc.execute(cmd, caller)
    await session.commit()
    return Response(status_code=204)
