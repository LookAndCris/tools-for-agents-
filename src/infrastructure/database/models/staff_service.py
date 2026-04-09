"""StaffServiceModel — junction table mapping staff to services they offer."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, uuid_pk


class StaffServiceModel(Base, TimestampMixin):
    """Junction record linking a staff member to a service they offer."""

    __tablename__ = "staff_services"
    __table_args__ = (
        UniqueConstraint("staff_id", "service_id", name="uq_staff_services_staff_service"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    staff_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("staff_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships
    staff: Mapped["StaffProfileModel"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "StaffProfileModel", back_populates="staff_services", lazy="select"
    )
    service: Mapped["ServiceModel"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ServiceModel", back_populates="staff_services", lazy="select"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"StaffServiceModel(staff_id={self.staff_id!r}, service_id={self.service_id!r})"
