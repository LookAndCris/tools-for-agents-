"""Query DTOs — Pydantic V2 models for read use case inputs."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class FindAvailableSlotsQuery(BaseModel):
    """Query for available booking slots within a date range."""

    staff_id: UUID
    service_id: UUID
    date_from: date
    date_to: date  # inclusive; max 31 days from date_from


class FindAvailableStaffQuery(BaseModel):
    """Query for staff members who offer a specific service."""

    service_id: UUID


class GetClientAppointmentsQuery(BaseModel):
    """Query for a client's appointment history, optionally filtered by status."""

    client_id: UUID
    status: str | None = None  # e.g. "scheduled", "confirmed", "cancelled"
