"""FindAvailableStaffUseCase — returns staff members who offer a given service."""
from __future__ import annotations

from domain.repositories.staff_repository import StaffRepository
from application.dto.queries import FindAvailableStaffQuery
from application.dto.responses import StaffResponse


class FindAvailableStaffUseCase:
    """Query use case: find staff members offering a specific service."""

    def __init__(self, staff_repo: StaffRepository) -> None:
        self._staff_repo = staff_repo

    async def execute(self, query: FindAvailableStaffQuery) -> list[StaffResponse]:
        """Return all staff members who offer the requested service."""
        staff_list = await self._staff_repo.find_by_service(query.service_id)
        return [StaffResponse.from_entity(s) for s in staff_list]
