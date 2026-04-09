"""ListServicesUseCase — returns all active services."""
from __future__ import annotations

from domain.repositories.service_repository import ServiceRepository
from application.dto.responses import ServiceResponse


class ListServicesUseCase:
    """Query use case: return all active services."""

    def __init__(self, service_repo: ServiceRepository) -> None:
        self._service_repo = service_repo

    async def execute(self) -> list[ServiceResponse]:
        """Return all active services as ServiceResponse DTOs."""
        services = await self._service_repo.get_all_active()
        return [ServiceResponse.from_entity(svc) for svc in services]
