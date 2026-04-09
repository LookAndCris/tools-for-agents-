"""Staff entity — links a User to their professional profile and offered services."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class Staff:
    """Professional profile for a staff member who delivers services."""

    id: UUID
    user_id: UUID
    created_at: datetime
    specialty: str | None = None
    bio: str | None = None
    is_available: bool = True
    service_ids: frozenset[UUID] = field(default_factory=frozenset)

    def offers_service(self, service_id: UUID) -> bool:
        """Return True if this staff member offers the given service."""
        return service_id in self.service_ids

    def add_service(self, service_id: UUID) -> None:
        """Add a service to this staff member's offerings."""
        self.service_ids = frozenset(self.service_ids | {service_id})

    def remove_service(self, service_id: UUID) -> None:
        """Remove a service from this staff member's offerings (noop if absent)."""
        self.service_ids = frozenset(self.service_ids - {service_id})
