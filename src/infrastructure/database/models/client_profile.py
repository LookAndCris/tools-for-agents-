"""ClientProfileModel — maps the ``client_profiles`` table."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, uuid_pk


class ClientProfileModel(Base, TimestampMixin):
    """Client profile for a person who books appointments."""

    __tablename__ = "client_profiles"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    preferred_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("staff_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # blocked_staff_ids stored as a PostgreSQL UUID array.
    # Defaults to empty array at the database level; Python default is [].
    blocked_staff_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=False,
        server_default="{}",
        default=list,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["UserModel"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "UserModel", back_populates="client_profile", lazy="select"
    )
    appointments: Mapped[list["AppointmentModel"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AppointmentModel", back_populates="client", lazy="select"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"ClientProfileModel(id={self.id!r}, user_id={self.user_id!r})"
