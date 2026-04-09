"""Service entity — read-mostly entity representing an offered service."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from domain.value_objects.service_duration import ServiceDuration
from domain.value_objects.money import Money


class Service:
    """Represents a service offered by the business (e.g., 'Haircut', 'Deep Tissue Massage').

    Immutable after construction — state changes are not expected.
    The only lifecycle flag is ``is_active`` (soft-delete).
    """

    def __init__(
        self,
        id: UUID,
        name: str,
        description: str,
        duration: ServiceDuration,
        price: Money,
        is_active: bool,
        created_at: datetime,
    ) -> None:
        name = name.strip()
        if not name:
            raise ValueError("Service name cannot be empty or whitespace.")
        self.id = id
        self.name = name
        self.description = description
        self.duration = duration
        self.price = price
        self.is_active = is_active
        self.created_at = created_at

    @property
    def total_duration_minutes(self) -> int:
        """Total slot time needed (including buffers)."""
        return self.duration.total

    def __repr__(self) -> str:  # pragma: no cover
        return f"Service(id={self.id!r}, name={self.name!r}, active={self.is_active})"
