"""StaffAvailabilityModel — maps the ``staff_availability`` table.

Each row represents a recurring weekly availability window for a staff member.
"""
from __future__ import annotations

import uuid
from datetime import time

from sqlalchemy import CheckConstraint, ForeignKey, Integer, SmallInteger, Time
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, uuid_pk


class StaffAvailabilityModel(Base, TimestampMixin):
    """A recurring weekly availability window for a staff member.

    ``day_of_week`` follows ISO weekday notation: 1=Monday … 7=Sunday.
    """

    __tablename__ = "staff_availability"
    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 1 AND 7", name="ck_staff_availability_day_of_week"),
        CheckConstraint("start_time < end_time", name="ck_staff_availability_time_order"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    staff_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("staff_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    # Relationships
    staff: Mapped["StaffProfileModel"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "StaffProfileModel", back_populates="availability_windows", lazy="select"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"StaffAvailabilityModel(staff_id={self.staff_id!r}, "
            f"day={self.day_of_week}, {self.start_time}-{self.end_time})"
        )
