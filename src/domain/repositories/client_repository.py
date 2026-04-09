"""ClientRepository ABC — defines the persistence contract for clients."""
from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.client import Client


class ClientRepository(ABC):
    """Abstract repository for Client persistence operations."""

    @abstractmethod
    def get_by_id(self, id: UUID) -> Client | None:
        """Return the client with the given ID, or None if not found."""
        ...

    @abstractmethod
    def get_by_user_id(self, user_id: UUID) -> Client | None:
        """Return the client associated with the given user ID, or None."""
        ...
