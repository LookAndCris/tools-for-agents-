"""Response DTOs — Pydantic V2 models for use case outputs."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ServiceResponse(BaseModel):
    """DTO representing a service."""

    id: UUID
    name: str
    description: str
    duration_minutes: int
    buffer_before: int
    buffer_after: int
    price: Decimal
    currency: str
    is_active: bool

    @classmethod
    def from_entity(cls, service) -> "ServiceResponse":
        """Create a ServiceResponse from a Service domain entity."""
        return cls(
            id=service.id,
            name=service.name,
            description=service.description,
            duration_minutes=service.duration.duration_minutes,
            buffer_before=service.duration.buffer_before,
            buffer_after=service.duration.buffer_after,
            price=service.price.amount,
            currency=service.price.currency,
            is_active=service.is_active,
        )


class StaffResponse(BaseModel):
    """DTO representing a staff member."""

    id: UUID
    user_id: UUID
    specialty: str | None
    bio: str | None
    is_available: bool
    service_ids: list[UUID]

    @classmethod
    def from_entity(cls, staff) -> "StaffResponse":
        """Create a StaffResponse from a Staff domain entity."""
        return cls(
            id=staff.id,
            user_id=staff.user_id,
            specialty=staff.specialty,
            bio=staff.bio,
            is_available=staff.is_available,
            service_ids=list(staff.service_ids),
        )


class AppointmentResponse(BaseModel):
    """DTO representing an appointment."""

    id: UUID
    client_id: UUID
    staff_id: UUID
    service_id: UUID
    start_time: datetime
    end_time: datetime
    status: str
    notes: str | None
    created_at: datetime

    @classmethod
    def from_entity(cls, appointment) -> "AppointmentResponse":
        """Create an AppointmentResponse from an Appointment domain entity."""
        return cls(
            id=appointment.id,
            client_id=appointment.client_id,
            staff_id=appointment.staff_id,
            service_id=appointment.service_id,
            start_time=appointment.time_slot.start,
            end_time=appointment.time_slot.end,
            status=appointment.status.value,
            notes=appointment.notes,
            created_at=appointment.created_at,
        )


class AvailableSlotsResponse(BaseModel):
    """DTO representing available booking slots."""

    staff_id: UUID
    service_id: UUID
    slots: list[datetime]  # UTC start times


class StaffTimeOffResponse(BaseModel):
    """DTO representing a staff time-off record."""

    id: UUID
    staff_id: UUID
    start_time: datetime
    end_time: datetime
    reason: str | None

    @classmethod
    def from_entity(cls, time_off) -> "StaffTimeOffResponse":
        """Create a StaffTimeOffResponse from a StaffTimeOff domain entity."""
        return cls(
            id=time_off.id,
            staff_id=time_off.staff_id,
            start_time=time_off.time_slot.start,
            end_time=time_off.time_slot.end,
            reason=time_off.reason,
        )


class AppointmentEventResponse(BaseModel):
    """DTO representing a single audit event on an appointment."""

    id: UUID
    appointment_id: UUID
    event_type: str
    occurred_at: datetime
    performed_by: UUID | None = None
    details: dict[str, Any] | None = None


class WaitlistEntryResponse(BaseModel):
    """DTO representing a waitlist entry."""

    id: UUID
    client_id: UUID
    service_id: UUID
    preferred_staff_id: UUID | None
    preferred_start: datetime | None
    preferred_end: datetime | None
    status: str
    notes: str | None = None
    created_at: datetime

    @classmethod
    def from_entity(cls, entry) -> "WaitlistEntryResponse":
        """Create a WaitlistEntryResponse from a WaitlistEntry domain entity."""
        return cls(
            id=entry.id,
            client_id=entry.client_id,
            service_id=entry.service_id,
            preferred_staff_id=entry.preferred_staff_id,
            preferred_start=entry.preferred_start,
            preferred_end=entry.preferred_end,
            status=entry.status.value,
            notes=entry.notes,
            created_at=entry.created_at,
        )
