"""AppointmentEventModel — maps the ``appointment_events`` table.

Each row is an immutable audit event recording a lifecycle transition on an appointment.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, uuid_pk


class AppointmentEventModel(Base):
    """Immutable audit record for a single appointment lifecycle event."""

    __tablename__ = "appointment_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    appointment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    # Optional free-form JSONB payload (e.g. cancellation reason, new slot)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ---------------------------------------------------------------------------
    # Typed audit columns (nullable — backward compat with existing rows)
    # ---------------------------------------------------------------------------

    #: Actor who triggered this event (user UUID from X-User-ID header)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )

    #: Time slot details for APPOINTMENT_RESCHEDULED events
    old_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    old_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    new_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    new_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    #: Cancellation reason for APPOINTMENT_CANCELLED events
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    appointment: Mapped["AppointmentModel"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AppointmentModel", back_populates="appointment_events", lazy="select"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"AppointmentEventModel(appointment_id={self.appointment_id!r}, "
            f"type={self.event_type!r})"
        )
