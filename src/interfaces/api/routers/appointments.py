"""Appointments router — CRUD endpoints for appointment management.

All endpoints require authentication. Write endpoints commit on success.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.commands import (
    CancelAppointmentCommand,
    CreateAppointmentCommand,
    RescheduleAppointmentCommand,
)
from application.dto.queries import GetClientAppointmentsQuery
from application.dto.responses import AppointmentResponse
from application.dto.user_context import UserContext
from application.use_cases.cancel_appointment import CancelAppointmentUseCase
from application.use_cases.create_appointment import CreateAppointmentUseCase
from application.use_cases.get_client_appointments import GetClientAppointmentsUseCase
from application.use_cases.reschedule_appointment import RescheduleAppointmentUseCase
from infrastructure.database.session import get_session
from interfaces.api.dependencies import (
    get_cancel_appointment_uc,
    get_client_appointments_uc,
    get_create_appointment_uc,
    get_current_user,
    get_reschedule_appointment_uc,
)

router = APIRouter()


@router.get("/", response_model=list[AppointmentResponse])
async def list_appointments(
    status: str | None = None,
    caller: UserContext = Depends(get_current_user),
    uc: GetClientAppointmentsUseCase = Depends(get_client_appointments_uc),
) -> list[AppointmentResponse]:
    """Return appointments for the authenticated client, optionally filtered by status."""
    query = GetClientAppointmentsQuery(
        client_id=caller.client_id,  # type: ignore[arg-type]
        status=status,
    )
    return await uc.execute(query)


@router.post("/", status_code=201, response_model=AppointmentResponse)
async def create_appointment(
    cmd: CreateAppointmentCommand,
    caller: UserContext = Depends(get_current_user),
    uc: CreateAppointmentUseCase = Depends(get_create_appointment_uc),
    session: AsyncSession = Depends(get_session),
) -> AppointmentResponse:
    """Book a new appointment.

    Returns 201 on success.
    Returns 409 on scheduling conflict.
    Returns 422 on validation errors or policy violations.
    """
    result = await uc.execute(cmd, caller)
    await session.commit()
    return result


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def cancel_appointment(
    appointment_id: UUID,
    cmd: CancelAppointmentCommand,
    caller: UserContext = Depends(get_current_user),
    uc: CancelAppointmentUseCase = Depends(get_cancel_appointment_uc),
    session: AsyncSession = Depends(get_session),
) -> AppointmentResponse:
    """Cancel an existing appointment.

    Returns 404 if the appointment does not exist.
    Returns 422 if cancellation policy is violated.
    """
    # Ensure the command uses the path parameter ID
    cmd_with_id = CancelAppointmentCommand(
        appointment_id=appointment_id,
        reason=cmd.reason,
    )
    result = await uc.execute(cmd_with_id, caller)
    await session.commit()
    return result


@router.post("/{appointment_id}/reschedule", response_model=AppointmentResponse)
async def reschedule_appointment(
    appointment_id: UUID,
    cmd: RescheduleAppointmentCommand,
    caller: UserContext = Depends(get_current_user),
    uc: RescheduleAppointmentUseCase = Depends(get_reschedule_appointment_uc),
    session: AsyncSession = Depends(get_session),
) -> AppointmentResponse:
    """Reschedule an existing appointment to a new time slot.

    Returns 404 if the appointment does not exist.
    Returns 409 if the new slot has a scheduling conflict.
    Returns 422 if availability policy rejects the new slot.
    """
    # Ensure the command uses the path parameter ID
    cmd_with_id = RescheduleAppointmentCommand(
        appointment_id=appointment_id,
        new_start_time=cmd.new_start_time,
    )
    result = await uc.execute(cmd_with_id, caller)
    await session.commit()
    return result
