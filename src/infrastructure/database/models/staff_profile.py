"""StaffProfileModel — maps the ``staff_profiles`` table."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, uuid_pk


class StaffProfileModel(Base, TimestampMixin):
    """Professional profile for a staff member linked to a system user."""

    __tablename__ = "staff_profiles"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    specialty: Mapped[str | None] = mapped_column(String(150), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped["UserModel"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "UserModel", back_populates="staff_profile", lazy="select"
    )
    staff_services: Mapped[list["StaffServiceModel"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "StaffServiceModel", back_populates="staff", lazy="select", cascade="all, delete-orphan"
    )
    availability_windows: Mapped[list["StaffAvailabilityModel"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "StaffAvailabilityModel", back_populates="staff", lazy="select", cascade="all, delete-orphan"
    )
    time_off_periods: Mapped[list["StaffTimeOffModel"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "StaffTimeOffModel", back_populates="staff", lazy="select", cascade="all, delete-orphan"
    )
    appointments: Mapped[list["AppointmentModel"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AppointmentModel", back_populates="staff", lazy="select"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"StaffProfileModel(id={self.id!r}, user_id={self.user_id!r})"
