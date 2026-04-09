"""ServiceRepository ABC — defines the persistence contract for services."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.service import Service


class ServiceRepository(ABC):
    """Abstract repository for Service persistence operations."""

    @abstractmethod
    def get_by_id(self, id: UUID) -> Service | None:
        """Return the service with the given ID, or None if not found."""
        ...

    @abstractmethod
    def get_all_active(self) -> list[Service]:
        """Return all active services."""
        ...

    @abstractmethod
    def find_by_ids(self, ids: list[UUID]) -> list[Service]:
        """Return all services whose IDs are in the given list."""
        ...
