"""StaffTimeOffModel — maps the ``staff_time_off`` table."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, uuid_pk


class StaffTimeOffModel(Base, TimestampMixin):
    """A discrete time-off block for a staff member (holiday, sick leave, etc.)."""

    __tablename__ = "staff_time_off"
    __table_args__ = (
        CheckConstraint(
            "start_datetime < end_datetime",
            name="ck_staff_time_off_datetime_order",
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    staff_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("staff_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    staff: Mapped["StaffProfileModel"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "StaffProfileModel", back_populates="time_off_periods", lazy="select"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"StaffTimeOffModel(staff_id={self.staff_id!r}, "
            f"{self.start_datetime} → {self.end_datetime})"
        )
