"""Staff time tools — block and unblock staff time."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from application.dto.commands import BlockStaffTimeCommand, UnblockStaffTimeCommand
from application.dto.user_context import UserContext
from application.use_cases.block_staff_time import BlockStaffTimeUseCase
from application.use_cases.unblock_staff_time import UnblockStaffTimeUseCase
from interfaces.chat_tools.context import AgentContext


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class BlockStaffTimeInput(BaseModel):
    """Input for block_staff_time."""

    staff_id: UUID
    start_time: datetime
    end_time: datetime
    reason: str | None = None


class UnblockStaffTimeInput(BaseModel):
    """Input for unblock_staff_time."""

    time_off_id: UUID


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _to_user_context(ctx: AgentContext) -> UserContext:
    """Bridge AgentContext → UserContext for use case calls."""
    return UserContext(
        user_id=ctx.user_id,
        role=ctx.role,
        staff_id=ctx.staff_id,
        client_id=ctx.client_id,
    )


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def block_staff_time(
    ctx: AgentContext,
    inp: BlockStaffTimeInput,
    uc: BlockStaffTimeUseCase,
) -> Any:
    """Block a time period for a staff member.

    Mutation tool — session will be committed by ToolExecutor on success.
    """
    cmd = BlockStaffTimeCommand(
        staff_id=inp.staff_id,
        start_time=inp.start_time,
        end_time=inp.end_time,
        reason=inp.reason,
    )
    return await uc.execute(cmd, _to_user_context(ctx))


async def unblock_staff_time(
    ctx: AgentContext,
    inp: UnblockStaffTimeInput,
    uc: UnblockStaffTimeUseCase,
) -> Any:
    """Remove a time-off block for a staff member.

    Mutation tool — session will be committed by ToolExecutor on success.
    Returns None on success (the use case does not return the deleted entity).
    """
    cmd = UnblockStaffTimeCommand(time_off_id=inp.time_off_id)
    return await uc.execute(cmd, _to_user_context(ctx))
