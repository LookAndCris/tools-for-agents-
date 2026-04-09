"""Unit tests for ListServicesUseCase."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from domain.repositories.service_repository import ServiceRepository
from tests.factories import ServiceFactory


class TestListServicesUseCase:
    @pytest.fixture
    def service_repo(self):
        return AsyncMock(spec=ServiceRepository)

    async def test_returns_all_active_services(self, service_repo):
        from application.use_cases.list_services import ListServicesUseCase
        from application.dto.responses import ServiceResponse

        svc1 = ServiceFactory(name="Haircut", is_active=True)
        svc2 = ServiceFactory(name="Massage", is_active=True)
        service_repo.get_all_active.return_value = [svc1, svc2]

        uc = ListServicesUseCase(service_repo=service_repo)
        result = await uc.execute()

        service_repo.get_all_active.assert_called_once()
        assert len(result) == 2
        assert all(isinstance(r, ServiceResponse) for r in result)
        names = {r.name for r in result}
        assert names == {"Haircut", "Massage"}

    async def test_returns_empty_list_when_no_services(self, service_repo):
        from application.use_cases.list_services import ListServicesUseCase

        service_repo.get_all_active.return_value = []

        uc = ListServicesUseCase(service_repo=service_repo)
        result = await uc.execute()

        assert result == []

    async def test_response_fields_correct(self, service_repo):
        from application.use_cases.list_services import ListServicesUseCase
        from application.dto.responses import ServiceResponse
        from domain.value_objects.money import Money
        from domain.value_objects.service_duration import ServiceDuration

        from decimal import Decimal
        svc = ServiceFactory(
            name="Deep Tissue",
            description="Deep tissue massage",
            is_active=True,
        )
        service_repo.get_all_active.return_value = [svc]

        uc = ListServicesUseCase(service_repo=service_repo)
        result = await uc.execute()

        resp = result[0]
        assert resp.id == svc.id
        assert resp.name == svc.name
        assert resp.description == svc.description
        assert resp.is_active is True
        assert isinstance(resp, ServiceResponse)
