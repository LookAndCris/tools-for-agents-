"""RoleModel — maps the ``roles`` table."""
from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.base import Base, TimestampMixin, uuid_pk


class RoleModel(Base, TimestampMixin):
    """Represents a system role (e.g. admin, staff, client)."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    users: Mapped[list["UserModel"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "UserModel", back_populates="role", lazy="select"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"RoleModel(id={self.id!r}, name={self.name!r})"
