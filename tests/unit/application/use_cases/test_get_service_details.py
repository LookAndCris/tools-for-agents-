"""Unit tests for GetServiceDetailsUseCase."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from domain.repositories.service_repository import ServiceRepository
from tests.factories import ServiceFactory


class TestGetServiceDetailsUseCase:
    @pytest.fixture
    def service_repo(self):
        return AsyncMock(spec=ServiceRepository)

    async def test_returns_service_when_found(self, service_repo):
        from application.use_cases.get_service_details import GetServiceDetailsUseCase
        from application.dto.responses import ServiceResponse

        svc = ServiceFactory(name="Haircut", is_active=True)
        service_repo.get_by_id.return_value = svc

        uc = GetServiceDetailsUseCase(service_repo=service_repo)
        result = await uc.execute(svc.id)

        service_repo.get_by_id.assert_called_once_with(svc.id)
        assert isinstance(result, ServiceResponse)
        assert result.id == svc.id
        assert result.name == "Haircut"

    async def test_raises_not_found_when_service_missing(self, service_repo):
        from application.use_cases.get_service_details import GetServiceDetailsUseCase
        from application.exceptions import NotFoundError

        service_repo.get_by_id.return_value = None

        uc = GetServiceDetailsUseCase(service_repo=service_repo)
        missing_id = uuid.uuid4()

        with pytest.raises(NotFoundError) as exc_info:
            await uc.execute(missing_id)

        assert exc_info.value.code == "SERVICE_NOT_FOUND"
        assert str(missing_id) in str(exc_info.value)

    async def test_response_includes_all_fields(self, service_repo):
        from application.use_cases.get_service_details import GetServiceDetailsUseCase

        svc = ServiceFactory(is_active=False)
        service_repo.get_by_id.return_value = svc

        uc = GetServiceDetailsUseCase(service_repo=service_repo)
        result = await uc.execute(svc.id)

        assert result.is_active is False
        assert result.duration_minutes == svc.duration.duration_minutes
        assert result.buffer_before == svc.duration.buffer_before
        assert result.buffer_after == svc.duration.buffer_after
