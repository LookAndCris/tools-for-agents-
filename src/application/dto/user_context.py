"""UserContext — immutable caller identity and role dataclass."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class UserContext:
    """Represents the authenticated caller's identity and role.

    Constructed by API middleware after authentication/authorization.
    Passed into use cases as a read-only context object.
    """

    user_id: UUID
    role: str  # "admin" | "staff" | "client"
    staff_id: UUID | None = None
    client_id: UUID | None = None
