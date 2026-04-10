"""Staff router — read-only endpoints for staff availability.

Both endpoints require authentication (UserContext is used for future
filtering by blocked staff, etc.).
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends

from application.dto.queries import FindAvailableSlotsQuery, FindAvailableStaffQuery
from application.dto.responses import AvailableSlotsResponse, StaffResponse
from application.dto.user_context import UserContext
from application.use_cases.find_available_slots import FindAvailableSlotsUseCase
from application.use_cases.find_available_staff import FindAvailableStaffUseCase
from interfaces.api.dependencies import (
    get_current_user,
    get_find_available_slots_uc,
    get_find_available_staff_uc,
)

router = APIRouter()


@router.get("/available", response_model=list[StaffResponse])
async def get_available_staff(
    service_id: UUID,
    caller: UserContext = Depends(get_current_user),
    uc: FindAvailableStaffUseCase = Depends(get_find_available_staff_uc),
) -> list[StaffResponse]:
    """Return staff members who offer the requested service."""
    query = FindAvailableStaffQuery(service_id=service_id)
    return await uc.execute(query)


@router.get("/available-slots", response_model=AvailableSlotsResponse)
async def get_available_slots(
    staff_id: UUID,
    service_id: UUID,
    date_from: date,
    date_to: date,
    caller: UserContext = Depends(get_current_user),
    uc: FindAvailableSlotsUseCase = Depends(get_find_available_slots_uc),
) -> AvailableSlotsResponse:
    """Return available booking slots for a staff member within a date range.

    Query params: staff_id, service_id, date_from, date_to (all required).
    Raises 422 if date_to < date_from or range exceeds 31 days.
    Raises 404 if the service does not exist.
    """
    query = FindAvailableSlotsQuery(
        staff_id=staff_id,
        service_id=service_id,
        date_from=date_from,
        date_to=date_to,
    )
    return await uc.execute(query)
