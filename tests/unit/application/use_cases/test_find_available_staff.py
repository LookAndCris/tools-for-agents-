"""Unit tests for FindAvailableStaffUseCase."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from domain.repositories.staff_repository import StaffRepository
from tests.factories import StaffFactory


class TestFindAvailableStaffUseCase:
    @pytest.fixture
    def staff_repo(self):
        return AsyncMock(spec=StaffRepository)

    async def test_returns_staff_for_service(self, staff_repo):
        from application.use_cases.find_available_staff import FindAvailableStaffUseCase
        from application.dto.responses import StaffResponse
        from application.dto.queries import FindAvailableStaffQuery

        service_id = uuid.uuid4()
        staff1 = StaffFactory(is_available=True)
        staff2 = StaffFactory(is_available=True)
        staff_repo.find_by_service.return_value = [staff1, staff2]

        uc = FindAvailableStaffUseCase(staff_repo=staff_repo)
        query = FindAvailableStaffQuery(service_id=service_id)
        result = await uc.execute(query)

        staff_repo.find_by_service.assert_called_once_with(service_id)
        assert len(result) == 2
        assert all(isinstance(r, StaffResponse) for r in result)

    async def test_returns_empty_when_no_staff(self, staff_repo):
        from application.use_cases.find_available_staff import FindAvailableStaffUseCase
        from application.dto.queries import FindAvailableStaffQuery

        service_id = uuid.uuid4()
        staff_repo.find_by_service.return_value = []

        uc = FindAvailableStaffUseCase(staff_repo=staff_repo)
        query = FindAvailableStaffQuery(service_id=service_id)
        result = await uc.execute(query)

        assert result == []

    async def test_response_fields_correct(self, staff_repo):
        from application.use_cases.find_available_staff import FindAvailableStaffUseCase
        from application.dto.queries import FindAvailableStaffQuery

        service_id = uuid.uuid4()
        staff = StaffFactory(
            specialty="Massage",
            bio="Experienced",
            is_available=True,
            service_ids=frozenset({service_id}),
        )
        staff_repo.find_by_service.return_value = [staff]

        uc = FindAvailableStaffUseCase(staff_repo=staff_repo)
        query = FindAvailableStaffQuery(service_id=service_id)
        result = await uc.execute(query)

        resp = result[0]
        assert resp.id == staff.id
        assert resp.user_id == staff.user_id
        assert resp.specialty == "Massage"
        assert resp.bio == "Experienced"
        assert resp.is_available is True
        assert service_id in resp.service_ids
