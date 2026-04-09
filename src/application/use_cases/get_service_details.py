"""GetServiceDetailsUseCase — returns a single service by ID."""
from __future__ import annotations

from uuid import UUID

from domain.repositories.service_repository import ServiceRepository
from application.dto.responses import ServiceResponse
from application.exceptions import NotFoundError


class GetServiceDetailsUseCase:
    """Query use case: return details for a single service."""

    def __init__(self, service_repo: ServiceRepository) -> None:
        self._service_repo = service_repo

    async def execute(self, service_id: UUID) -> ServiceResponse:
        """Return the service with the given ID.

        Raises:
            NotFoundError: If the service does not exist.
        """
        service = await self._service_repo.get_by_id(service_id)
        if service is None:
            raise NotFoundError("Service", service_id)
        return ServiceResponse.from_entity(service)
