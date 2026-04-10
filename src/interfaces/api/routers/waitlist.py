"""Waitlist router — endpoints for waitlist management.

All endpoints require authentication. Write endpoints commit on success.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.commands import AddWaitlistCommand, NotifyWaitlistCommand
from application.dto.responses import WaitlistEntryResponse
from application.dto.user_context import UserContext
from application.use_cases.add_waitlist import AddWaitlistUseCase
from application.use_cases.get_waitlist_entries import GetWaitlistEntriesUseCase
from application.use_cases.notify_waitlist import NotifyWaitlistUseCase
from infrastructure.database.session import get_session
from interfaces.api.dependencies import (
    get_add_waitlist_uc,
    get_current_user,
    get_notify_waitlist_uc,
    get_waitlist_entries_uc,
)

router = APIRouter()


@router.post("/", status_code=201, response_model=WaitlistEntryResponse)
async def add_to_waitlist(
    cmd: AddWaitlistCommand,
    caller: UserContext = Depends(get_current_user),
    uc: AddWaitlistUseCase = Depends(get_add_waitlist_uc),
    session: AsyncSession = Depends(get_session),
) -> WaitlistEntryResponse:
    """Add a client to the waitlist for a service.

    Returns 201 on success.
    Returns 400 on duplicate PENDING entry (ValidationError).
    Returns 404 if service or preferred staff is not found.
    """
    result = await uc.execute(cmd)
    await session.commit()
    return result


@router.get("/", response_model=list[WaitlistEntryResponse])
async def list_waitlist(
    caller: UserContext = Depends(get_current_user),
    uc: GetWaitlistEntriesUseCase = Depends(get_waitlist_entries_uc),
) -> list[WaitlistEntryResponse]:
    """Return waitlist entries for the authenticated client."""
    return await uc.execute(caller.client_id)  # type: ignore[arg-type]


@router.post("/notify", response_model=list[WaitlistEntryResponse])
async def notify_waitlist(
    cmd: NotifyWaitlistCommand,
    caller: UserContext = Depends(get_current_user),
    uc: NotifyWaitlistUseCase = Depends(get_notify_waitlist_uc),
    session: AsyncSession = Depends(get_session),
) -> list[WaitlistEntryResponse]:
    """Notify pending waitlist entries for a service in FIFO order.

    Returns 200 with list of notified entries (may be empty).
    """
    result = await uc.execute(cmd)
    await session.commit()
    return result
