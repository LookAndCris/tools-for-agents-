"""WaitlistEntryModel — maps the ``waitlist`` table."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, uuid_pk


class WaitlistEntryModel(Base, TimestampMixin):
    """Persisted waitlist entry — maps to the ``WaitlistEntry`` domain entity."""

    __tablename__ = "waitlist"

    id: Mapped[uuid.UUID] = uuid_pk()
    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("client_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    service_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    preferred_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("staff_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    preferred_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    preferred_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Status stored as a string matching WaitlistStatus enum values
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    notifications: Mapped[list["WaitlistNotificationModel"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "WaitlistNotificationModel",
        back_populates="waitlist_entry",
        lazy="select",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"WaitlistEntryModel(id={self.id!r}, status={self.status!r})"
