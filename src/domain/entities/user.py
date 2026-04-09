"""User entity — identity and role for system access."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    """Represents an authenticated user with a role in the system."""

    id: UUID
    email: str
    first_name: str
    last_name: str
    role: str
    created_at: datetime
    updated_at: datetime
    phone: str | None = None
    is_active: bool = True

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def deactivate(self) -> None:
        from datetime import timezone
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)

    def activate(self) -> None:
        from datetime import timezone
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
