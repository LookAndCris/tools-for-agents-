"""Appointment tools — create, cancel, reschedule, and list client appointments."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from application.dto.commands import (
    CancelAppointmentCommand,
    CreateAppointmentCommand,
    RescheduleAppointmentCommand,
)
from application.dto.queries import GetClientAppointmentsQuery
from application.dto.user_context import UserContext
from application.use_cases.cancel_appointment import CancelAppointmentUseCase
from application.use_cases.create_appointment import CreateAppointmentUseCase
from application.use_cases.get_client_appointments import GetClientAppointmentsUseCase
from application.use_cases.reschedule_appointment import RescheduleAppointmentUseCase
from interfaces.chat_tools.context import AgentContext


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class CreateAppointmentInput(BaseModel):
    """Input for create_appointment."""

    client_id: UUID
    staff_id: UUID
    service_id: UUID
    start_time: datetime
    notes: str | None = None


class CancelAppointmentInput(BaseModel):
    """Input for cancel_appointment."""

    appointment_id: UUID
    reason: str | None = None


class RescheduleAppointmentInput(BaseModel):
    """Input for reschedule_appointment."""

    appointment_id: UUID
    new_start_time: datetime


class GetClientAppointmentsInput(BaseModel):
    """Input for get_client_appointments."""

    client_id: UUID
    status: str | None = None


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


async def create_appointment(
    ctx: AgentContext,
    inp: CreateAppointmentInput,
    uc: CreateAppointmentUseCase,
) -> Any:
    """Book a new appointment.

    Mutation tool — session will be committed by ToolExecutor on success.
    """
    cmd = CreateAppointmentCommand(
        client_id=inp.client_id,
        staff_id=inp.staff_id,
        service_id=inp.service_id,
        start_time=inp.start_time,
        notes=inp.notes,
    )
    return await uc.execute(cmd, _to_user_context(ctx))


async def cancel_appointment(
    ctx: AgentContext,
    inp: CancelAppointmentInput,
    uc: CancelAppointmentUseCase,
) -> Any:
    """Cancel an existing appointment.

    Mutation tool — session will be committed by ToolExecutor on success.
    """
    cmd = CancelAppointmentCommand(
        appointment_id=inp.appointment_id,
        reason=inp.reason,
    )
    return await uc.execute(cmd, _to_user_context(ctx))


async def reschedule_appointment(
    ctx: AgentContext,
    inp: RescheduleAppointmentInput,
    uc: RescheduleAppointmentUseCase,
) -> Any:
    """Move an appointment to a new time slot.

    Mutation tool — session will be committed by ToolExecutor on success.
    """
    cmd = RescheduleAppointmentCommand(
        appointment_id=inp.appointment_id,
        new_start_time=inp.new_start_time,
    )
    return await uc.execute(cmd, _to_user_context(ctx))


async def get_client_appointments(
    ctx: AgentContext,
    inp: GetClientAppointmentsInput,
    uc: GetClientAppointmentsUseCase,
) -> list[Any]:
    """Return a client's appointment history.

    Query tool — no commit required.
    """
    query = GetClientAppointmentsQuery(
        client_id=inp.client_id,
        status=inp.status,
    )
    return await uc.execute(query)
