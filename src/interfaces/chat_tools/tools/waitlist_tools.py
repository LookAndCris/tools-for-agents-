"""Waitlist tools — add clients to waitlist and notify pending entries."""
from __future__ import annotations

from typing import Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from application.dto.commands import AddWaitlistCommand, NotifyWaitlistCommand
from application.use_cases.add_waitlist import AddWaitlistUseCase
from application.use_cases.notify_waitlist import NotifyWaitlistUseCase
from interfaces.chat_tools.context import AgentContext


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class AddWaitlistInput(BaseModel):
    """Input for add_waitlist."""

    client_id: UUID
    service_id: UUID
    preferred_staff_id: UUID | None = None
    preferred_start: datetime | None = None
    preferred_end: datetime | None = None
    notes: str | None = None


class NotifyWaitlistInput(BaseModel):
    """Input for notify_waitlist."""

    service_id: UUID
    staff_id: UUID | None = None  # optional filter by preferred staff


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def add_waitlist(
    ctx: AgentContext,
    inp: AddWaitlistInput,
    uc: AddWaitlistUseCase,
) -> Any:
    """Add a client to the waitlist for a service.

    Mutation tool — session will be committed by ToolExecutor on success.
    """
    cmd = AddWaitlistCommand(
        client_id=inp.client_id,
        service_id=inp.service_id,
        preferred_staff_id=inp.preferred_staff_id,
        preferred_start=inp.preferred_start,
        preferred_end=inp.preferred_end,
        notes=inp.notes,
    )
    return await uc.execute(cmd)


async def notify_waitlist(
    ctx: AgentContext,
    inp: NotifyWaitlistInput,
    uc: NotifyWaitlistUseCase,
) -> list[Any]:
    """Notify pending waitlist entries for a service (FIFO order).

    Mutation tool — session will be committed by ToolExecutor on success.
    """
    cmd = NotifyWaitlistCommand(
        service_id=inp.service_id,
        staff_id=inp.staff_id,
    )
    return await uc.execute(cmd)
