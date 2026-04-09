"""Command DTOs — Pydantic V2 models for write use case inputs."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CreateAppointmentCommand(BaseModel):
    """Command to book a new appointment."""

    client_id: UUID
    staff_id: UUID
    service_id: UUID
    start_time: datetime  # UTC-aware
    notes: str | None = None


class CancelAppointmentCommand(BaseModel):
    """Command to cancel an existing appointment."""

    appointment_id: UUID
    reason: str | None = None


class RescheduleAppointmentCommand(BaseModel):
    """Command to move an appointment to a new time slot."""

    appointment_id: UUID
    new_start_time: datetime  # UTC-aware


class BlockStaffTimeCommand(BaseModel):
    """Command to block a time period for a staff member (unavailability)."""

    staff_id: UUID
    start_time: datetime
    end_time: datetime
    reason: str | None = None


class UnblockStaffTimeCommand(BaseModel):
    """Command to remove a time-off block for a staff member."""

    time_off_id: UUID
