"""UserModel — maps the ``users`` table."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, uuid_pk


class UserModel(Base, TimestampMixin):
    """Represents an authenticated system user linked to a role."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    role_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    role: Mapped["RoleModel"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "RoleModel", back_populates="users", lazy="select"
    )
    staff_profile: Mapped["StaffProfileModel | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "StaffProfileModel", back_populates="user", uselist=False, lazy="select"
    )
    client_profile: Mapped["ClientProfileModel | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ClientProfileModel", back_populates="user", uselist=False, lazy="select"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"UserModel(id={self.id!r}, email={self.email!r})"
