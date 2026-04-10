"""WaitlistNotificationModel — maps the ``waitlist_notifications`` table."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, uuid_pk


class WaitlistNotificationModel(Base, TimestampMixin):
    """Persisted waitlist notification audit record."""

    __tablename__ = "waitlist_notifications"

    id: Mapped[uuid.UUID] = uuid_pk()
    waitlist_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("waitlist.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    notified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    waitlist_entry: Mapped["WaitlistEntryModel"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "WaitlistEntryModel",
        back_populates="notifications",
        lazy="select",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"WaitlistNotificationModel(id={self.id!r}, "
            f"waitlist_id={self.waitlist_id!r})"
        )
