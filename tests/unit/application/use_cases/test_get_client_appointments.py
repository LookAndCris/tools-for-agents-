"""Unit tests for GetClientAppointmentsUseCase."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from domain.repositories.appointment_repository import AppointmentRepository
from domain.value_objects.appointment_status import AppointmentStatus
from tests.factories import AppointmentFactory


class TestGetClientAppointmentsUseCase:
    @pytest.fixture
    def appointment_repo(self):
        return AsyncMock(spec=AppointmentRepository)

    async def test_returns_appointments_for_client(self, appointment_repo):
        from application.use_cases.get_client_appointments import GetClientAppointmentsUseCase
        from application.dto.responses import AppointmentResponse
        from application.dto.queries import GetClientAppointmentsQuery

        client_id = uuid.uuid4()
        appt1 = AppointmentFactory(client_id=client_id)
        appt2 = AppointmentFactory(client_id=client_id)
        appointment_repo.find_by_client.return_value = [appt1, appt2]

        uc = GetClientAppointmentsUseCase(appointment_repo=appointment_repo)
        query = GetClientAppointmentsQuery(client_id=client_id)
        result = await uc.execute(query)

        appointment_repo.find_by_client.assert_called_once_with(client_id, None)
        assert len(result) == 2
        assert all(isinstance(r, AppointmentResponse) for r in result)

    async def test_returns_empty_when_no_appointments(self, appointment_repo):
        from application.use_cases.get_client_appointments import GetClientAppointmentsUseCase
        from application.dto.queries import GetClientAppointmentsQuery

        client_id = uuid.uuid4()
        appointment_repo.find_by_client.return_value = []

        uc = GetClientAppointmentsUseCase(appointment_repo=appointment_repo)
        query = GetClientAppointmentsQuery(client_id=client_id)
        result = await uc.execute(query)

        assert result == []

    async def test_passes_status_filter_to_repo(self, appointment_repo):
        from application.use_cases.get_client_appointments import GetClientAppointmentsUseCase
        from application.dto.queries import GetClientAppointmentsQuery

        client_id = uuid.uuid4()
        appt = AppointmentFactory(client_id=client_id, status=AppointmentStatus.SCHEDULED)
        appointment_repo.find_by_client.return_value = [appt]

        uc = GetClientAppointmentsUseCase(appointment_repo=appointment_repo)
        query = GetClientAppointmentsQuery(client_id=client_id, status="scheduled")
        result = await uc.execute(query)

        # Verify the repo was called with the resolved status enum
        call_args = appointment_repo.find_by_client.call_args
        assert call_args[0][0] == client_id
        assert call_args[0][1] == AppointmentStatus.SCHEDULED

    async def test_response_fields_correct(self, appointment_repo):
        from application.use_cases.get_client_appointments import GetClientAppointmentsUseCase
        from application.dto.responses import AppointmentResponse
        from application.dto.queries import GetClientAppointmentsQuery

        client_id = uuid.uuid4()
        appt = AppointmentFactory(client_id=client_id)
        appointment_repo.find_by_client.return_value = [appt]

        uc = GetClientAppointmentsUseCase(appointment_repo=appointment_repo)
        query = GetClientAppointmentsQuery(client_id=client_id)
        result = await uc.execute(query)

        resp = result[0]
        assert resp.id == appt.id
        assert resp.client_id == client_id
        assert resp.staff_id == appt.staff_id
        assert resp.service_id == appt.service_id
        assert resp.status == appt.status.value
        assert isinstance(resp, AppointmentResponse)
