"""ServiceModel — maps the ``services`` table."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, uuid_pk


class ServiceModel(Base, TimestampMixin):
    """Represents a bookable service offered by the business."""

    __tablename__ = "services"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    buffer_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    buffer_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="MXN")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    staff_services: Mapped[list["StaffServiceModel"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "StaffServiceModel", back_populates="service", lazy="select", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["AppointmentModel"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AppointmentModel", back_populates="service", lazy="select"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"ServiceModel(id={self.id!r}, name={self.name!r})"
