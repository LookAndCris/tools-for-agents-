"""Client entity — links a User to their booking preferences and constraints."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class Client:
    """Client profile for a person who books appointments."""

    id: UUID
    user_id: UUID
    created_at: datetime
    preferred_staff_id: UUID | None = None
    blocked_staff_ids: frozenset[UUID] = field(default_factory=frozenset)
    notes: str | None = None

    def prefers_staff(self, staff_id: UUID) -> bool:
        """Return True if this client has explicitly preferred the given staff member."""
        return self.preferred_staff_id == staff_id

    def has_blocked(self, staff_id: UUID) -> bool:
        """Return True if this client has blocked the given staff member."""
        return staff_id in self.blocked_staff_ids
