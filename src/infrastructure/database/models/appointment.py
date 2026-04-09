"""AppointmentModel — maps the ``appointments`` table."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, uuid_pk


class AppointmentModel(Base, TimestampMixin):
    """Persisted appointment record — maps to the ``Appointment`` aggregate root."""

    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint(
            "scheduled_start < scheduled_end",
            name="ck_appointments_slot_order",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("client_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("staff_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    scheduled_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    scheduled_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Status stored as a string matching AppointmentStatus enum values
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scheduled", index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    client: Mapped["ClientProfileModel"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ClientProfileModel", back_populates="appointments", lazy="select"
    )
    staff: Mapped["StaffProfileModel"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "StaffProfileModel", back_populates="appointments", lazy="select"
    )
    service: Mapped["ServiceModel"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ServiceModel", back_populates="appointments", lazy="select"
    )
    appointment_events: Mapped[list["AppointmentEventModel"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AppointmentEventModel",
        back_populates="appointment",
        lazy="select",
        cascade="all, delete-orphan",
        order_by="AppointmentEventModel.occurred_at",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"AppointmentModel(id={self.id!r}, status={self.status!r})"
