"""Unit tests for chat tools (Tasks 2.1 and 3.1 — RED phase).

Service tools:
- search_services: delegates to ListServicesUseCase
- get_service_details: delegates to GetServiceDetailsUseCase
- get_service_price: thin wrapper, returns only price fields
- get_service_duration: thin wrapper, returns only duration fields

Staff tools:
- find_available_staff: delegates to FindAvailableStaffUseCase

Slot tools:
- find_available_slots: delegates to FindAvailableSlotsUseCase

Appointment tools:
- create_appointment: mutation, delegates to CreateAppointmentUseCase
- cancel_appointment: mutation, delegates to CancelAppointmentUseCase
- reschedule_appointment: mutation, delegates to RescheduleAppointmentUseCase
- get_client_appointments: query, delegates to GetClientAppointmentsUseCase

Staff time tools:
- block_staff_time: mutation, delegates to BlockStaffTimeUseCase
- unblock_staff_time: mutation, delegates to UnblockStaffTimeUseCase

NOTE: No `from __future__ import annotations` — see test_registry.py for explanation.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from interfaces.chat_tools.context import AgentContext
from tests.factories import AppointmentFactory, ServiceFactory, StaffFactory


def _ctx(**kwargs) -> AgentContext:
    defaults = {"user_id": uuid.uuid4(), "role": "admin"}
    defaults.update(kwargs)
    return AgentContext(**defaults)


def _utc(year, month, day, hour=10, minute=0) -> datetime:
    return datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Service tool tests
# ---------------------------------------------------------------------------


class TestSearchServices:
    async def test_delegates_to_list_services_uc(self):
        """search_services calls ListServicesUseCase.execute() and returns results."""
        from interfaces.chat_tools.tools.service_tools import search_services, SearchServicesInput

        uc = AsyncMock()
        svc = ServiceFactory(name="Haircut")
        uc.execute.return_value = [svc]

        inp = SearchServicesInput()
        result = await search_services(_ctx(), inp, uc)

        uc.execute.assert_called_once()
        assert len(result) == 1

    async def test_returns_list_of_service_dicts(self):
        """search_services returns serialized service data."""
        from interfaces.chat_tools.tools.service_tools import search_services, SearchServicesInput
        from application.dto.responses import ServiceResponse

        uc = AsyncMock()
        svc = ServiceFactory(name="Massage")
        from application.dto.responses import ServiceResponse
        svc_resp = ServiceResponse.from_entity(svc)
        uc.execute.return_value = [svc_resp]

        inp = SearchServicesInput()
        result = await search_services(_ctx(), inp, uc)

        assert isinstance(result, list)
        assert len(result) == 1

    async def test_empty_returns_empty_list(self):
        """search_services returns [] when no services are found."""
        from interfaces.chat_tools.tools.service_tools import search_services, SearchServicesInput

        uc = AsyncMock()
        uc.execute.return_value = []

        result = await search_services(_ctx(), SearchServicesInput(), uc)
        assert result == []


class TestGetServiceDetails:
    async def test_delegates_to_get_service_details_uc(self):
        """get_service_details calls GetServiceDetailsUseCase.execute(service_id)."""
        from interfaces.chat_tools.tools.service_tools import get_service_details, GetServiceDetailsInput
        from application.dto.responses import ServiceResponse

        uc = AsyncMock()
        svc = ServiceFactory(name="Haircut")
        svc_resp = ServiceResponse.from_entity(svc)
        uc.execute.return_value = svc_resp
        service_id = uuid.uuid4()

        inp = GetServiceDetailsInput(service_id=service_id)
        result = await get_service_details(_ctx(), inp, uc)

        uc.execute.assert_called_once_with(service_id)
        assert result is not None


class TestGetServicePrice:
    async def test_returns_only_price_fields(self):
        """get_service_price extracts price/currency from GetServiceDetailsUseCase."""
        from interfaces.chat_tools.tools.service_tools import get_service_price, GetServicePriceInput
        from application.dto.responses import ServiceResponse

        uc = AsyncMock()
        svc = ServiceFactory(name="Haircut")
        svc_resp = ServiceResponse.from_entity(svc)
        uc.execute.return_value = svc_resp
        service_id = uuid.uuid4()

        inp = GetServicePriceInput(service_id=service_id)
        result = await get_service_price(_ctx(), inp, uc)

        uc.execute.assert_called_once_with(service_id)
        assert "price" in result
        assert "currency" in result
        assert "service_id" in result
        # Should NOT include duration or other fields directly
        assert "duration_minutes" not in result


class TestGetServiceDuration:
    async def test_returns_only_duration_fields(self):
        """get_service_duration extracts duration fields from GetServiceDetailsUseCase."""
        from interfaces.chat_tools.tools.service_tools import get_service_duration, GetServiceDurationInput
        from application.dto.responses import ServiceResponse

        uc = AsyncMock()
        svc = ServiceFactory(name="Haircut")
        svc_resp = ServiceResponse.from_entity(svc)
        uc.execute.return_value = svc_resp
        service_id = uuid.uuid4()

        inp = GetServiceDurationInput(service_id=service_id)
        result = await get_service_duration(_ctx(), inp, uc)

        uc.execute.assert_called_once_with(service_id)
        assert "duration_minutes" in result
        assert "service_id" in result
        assert "price" not in result


# ---------------------------------------------------------------------------
# Staff tool tests
# ---------------------------------------------------------------------------


class TestFindAvailableStaff:
    async def test_delegates_to_find_available_staff_uc(self):
        """find_available_staff calls FindAvailableStaffUseCase.execute() with query."""
        from interfaces.chat_tools.tools.staff_tools import find_available_staff, FindAvailableStaffInput
        from application.dto.queries import FindAvailableStaffQuery

        uc = AsyncMock()
        staff = StaffFactory()
        from application.dto.responses import StaffResponse
        staff_resp = StaffResponse.from_entity(staff)
        uc.execute.return_value = [staff_resp]
        service_id = uuid.uuid4()

        inp = FindAvailableStaffInput(service_id=service_id)
        result = await find_available_staff(_ctx(), inp, uc)

        uc.execute.assert_called_once()
        call_arg = uc.execute.call_args[0][0]
        assert isinstance(call_arg, FindAvailableStaffQuery)
        assert call_arg.service_id == service_id
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Slot tool tests
# ---------------------------------------------------------------------------


class TestFindAvailableSlots:
    async def test_delegates_to_find_available_slots_uc(self):
        """find_available_slots calls FindAvailableSlotsUseCase.execute() with query."""
        from interfaces.chat_tools.tools.slot_tools import find_available_slots, FindAvailableSlotsInput
        from application.dto.queries import FindAvailableSlotsQuery
        from application.dto.responses import AvailableSlotsResponse

        uc = AsyncMock()
        staff_id = uuid.uuid4()
        service_id = uuid.uuid4()
        uc.execute.return_value = AvailableSlotsResponse(
            staff_id=staff_id, service_id=service_id, slots=[]
        )

        inp = FindAvailableSlotsInput(
            staff_id=staff_id,
            service_id=service_id,
            date_from=date(2026, 4, 10),
            date_to=date(2026, 4, 15),
        )
        result = await find_available_slots(_ctx(), inp, uc)

        uc.execute.assert_called_once()
        call_arg = uc.execute.call_args[0][0]
        assert isinstance(call_arg, FindAvailableSlotsQuery)
        assert call_arg.staff_id == staff_id
        assert call_arg.service_id == service_id
        assert result is not None


# ---------------------------------------------------------------------------
# Appointment tool tests
# ---------------------------------------------------------------------------


class TestCreateAppointment:
    async def test_delegates_to_create_appointment_uc(self):
        """create_appointment calls CreateAppointmentUseCase.execute() with cmd + ctx."""
        from interfaces.chat_tools.tools.appointment_tools import create_appointment, CreateAppointmentInput
        from application.dto.commands import CreateAppointmentCommand
        from application.dto.user_context import UserContext

        uc = AsyncMock()
        appt = AppointmentFactory()
        from application.dto.responses import AppointmentResponse
        appt_resp = AppointmentResponse.from_entity(appt)
        uc.execute.return_value = appt_resp

        agent_ctx = _ctx()
        inp = CreateAppointmentInput(
            client_id=uuid.uuid4(),
            staff_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            start_time=_utc(2026, 4, 15),
        )
        result = await create_appointment(agent_ctx, inp, uc)

        uc.execute.assert_called_once()
        call_cmd, call_caller = uc.execute.call_args[0]
        assert isinstance(call_cmd, CreateAppointmentCommand)
        assert isinstance(call_caller, UserContext)
        assert call_caller.user_id == agent_ctx.user_id
        assert result is not None

    async def test_caller_context_maps_from_agent_context(self):
        """UserContext passed to UC has same user_id and role as AgentContext."""
        from interfaces.chat_tools.tools.appointment_tools import create_appointment, CreateAppointmentInput
        from application.dto.user_context import UserContext

        uc = AsyncMock()
        appt = AppointmentFactory()
        from application.dto.responses import AppointmentResponse
        uc.execute.return_value = AppointmentResponse.from_entity(appt)

        user_id = uuid.uuid4()
        agent_ctx = AgentContext(user_id=user_id, role="staff", staff_id=uuid.uuid4())
        inp = CreateAppointmentInput(
            client_id=uuid.uuid4(),
            staff_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            start_time=_utc(2026, 4, 15),
        )
        await create_appointment(agent_ctx, inp, uc)

        _, call_caller = uc.execute.call_args[0]
        assert call_caller.user_id == user_id
        assert call_caller.role == "staff"


class TestCancelAppointment:
    async def test_delegates_to_cancel_appointment_uc(self):
        """cancel_appointment calls CancelAppointmentUseCase.execute() with cmd + ctx."""
        from interfaces.chat_tools.tools.appointment_tools import cancel_appointment, CancelAppointmentInput
        from application.dto.commands import CancelAppointmentCommand
        from application.dto.user_context import UserContext

        uc = AsyncMock()
        appt = AppointmentFactory()
        from application.dto.responses import AppointmentResponse
        uc.execute.return_value = AppointmentResponse.from_entity(appt)

        agent_ctx = _ctx()
        inp = CancelAppointmentInput(appointment_id=uuid.uuid4(), reason="Changed mind")
        result = await cancel_appointment(agent_ctx, inp, uc)

        uc.execute.assert_called_once()
        call_cmd, call_caller = uc.execute.call_args[0]
        assert isinstance(call_cmd, CancelAppointmentCommand)
        assert isinstance(call_caller, UserContext)
        assert result is not None


class TestRescheduleAppointment:
    async def test_delegates_to_reschedule_uc(self):
        """reschedule_appointment calls RescheduleAppointmentUseCase.execute()."""
        from interfaces.chat_tools.tools.appointment_tools import reschedule_appointment, RescheduleAppointmentInput
        from application.dto.commands import RescheduleAppointmentCommand
        from application.dto.user_context import UserContext

        uc = AsyncMock()
        appt = AppointmentFactory()
        from application.dto.responses import AppointmentResponse
        uc.execute.return_value = AppointmentResponse.from_entity(appt)

        agent_ctx = _ctx()
        inp = RescheduleAppointmentInput(
            appointment_id=uuid.uuid4(),
            new_start_time=_utc(2026, 4, 20),
        )
        result = await reschedule_appointment(agent_ctx, inp, uc)

        uc.execute.assert_called_once()
        call_cmd, call_caller = uc.execute.call_args[0]
        assert isinstance(call_cmd, RescheduleAppointmentCommand)
        assert isinstance(call_caller, UserContext)
        assert result is not None


class TestGetClientAppointments:
    async def test_delegates_to_get_client_appointments_uc(self):
        """get_client_appointments calls GetClientAppointmentsUseCase.execute()."""
        from interfaces.chat_tools.tools.appointment_tools import get_client_appointments, GetClientAppointmentsInput
        from application.dto.queries import GetClientAppointmentsQuery

        uc = AsyncMock()
        uc.execute.return_value = []

        client_id = uuid.uuid4()
        inp = GetClientAppointmentsInput(client_id=client_id)
        result = await get_client_appointments(_ctx(), inp, uc)

        uc.execute.assert_called_once()
        call_arg = uc.execute.call_args[0][0]
        assert isinstance(call_arg, GetClientAppointmentsQuery)
        assert call_arg.client_id == client_id
        assert result == []


# ---------------------------------------------------------------------------
# Staff time-off tool tests
# ---------------------------------------------------------------------------


class TestBlockStaffTime:
    async def test_delegates_to_block_staff_time_uc(self):
        """block_staff_time calls BlockStaffTimeUseCase.execute() with cmd + ctx."""
        from interfaces.chat_tools.tools.staff_time_tools import block_staff_time, BlockStaffTimeInput
        from application.dto.commands import BlockStaffTimeCommand
        from application.dto.user_context import UserContext

        uc = AsyncMock()
        from domain.entities.staff_time_off import StaffTimeOff
        from domain.value_objects.time_slot import TimeSlot
        import uuid as _uuid
        time_off = StaffTimeOff(
            id=_uuid.uuid4(),
            staff_id=_uuid.uuid4(),
            time_slot=TimeSlot(start=_utc(2026, 4, 15, 9), end=_utc(2026, 4, 15, 11)),
            reason=None,
        )
        from application.dto.responses import StaffTimeOffResponse
        uc.execute.return_value = StaffTimeOffResponse.from_entity(time_off)

        agent_ctx = _ctx()
        inp = BlockStaffTimeInput(
            staff_id=uuid.uuid4(),
            start_time=_utc(2026, 4, 15, 9),
            end_time=_utc(2026, 4, 15, 11),
        )
        result = await block_staff_time(agent_ctx, inp, uc)

        uc.execute.assert_called_once()
        call_cmd, call_caller = uc.execute.call_args[0]
        assert isinstance(call_cmd, BlockStaffTimeCommand)
        assert isinstance(call_caller, UserContext)
        assert result is not None


class TestUnblockStaffTime:
    async def test_delegates_to_unblock_staff_time_uc(self):
        """unblock_staff_time calls UnblockStaffTimeUseCase.execute() with cmd + ctx."""
        from interfaces.chat_tools.tools.staff_time_tools import unblock_staff_time, UnblockStaffTimeInput
        from application.dto.commands import UnblockStaffTimeCommand
        from application.dto.user_context import UserContext

        uc = AsyncMock()
        uc.execute.return_value = None  # unblock returns None on success

        agent_ctx = _ctx()
        time_off_id = uuid.uuid4()
        inp = UnblockStaffTimeInput(time_off_id=time_off_id)
        result = await unblock_staff_time(agent_ctx, inp, uc)

        uc.execute.assert_called_once()
        call_cmd, call_caller = uc.execute.call_args[0]
        assert isinstance(call_cmd, UnblockStaffTimeCommand)
        assert isinstance(call_caller, UserContext)
        assert call_cmd.time_off_id == time_off_id


# ---------------------------------------------------------------------------
# Waitlist tool tests (Task 3.3 — RED phase)
# ---------------------------------------------------------------------------


class TestAddWaitlist:
    async def test_delegates_to_add_waitlist_uc(self):
        """add_waitlist calls AddWaitlistUseCase.execute() with cmd."""
        from interfaces.chat_tools.tools.waitlist_tools import add_waitlist, AddWaitlistInput
        from application.dto.commands import AddWaitlistCommand
        from application.dto.responses import WaitlistEntryResponse
        from domain.value_objects.waitlist_status import WaitlistStatus

        uc = AsyncMock()
        client_id = uuid.uuid4()
        service_id = uuid.uuid4()
        entry_resp = WaitlistEntryResponse(
            id=uuid.uuid4(),
            client_id=client_id,
            service_id=service_id,
            preferred_staff_id=None,
            preferred_start=None,
            preferred_end=None,
            status=WaitlistStatus.PENDING.value,
            created_at=_utc(2026, 4, 1),
        )
        uc.execute.return_value = entry_resp

        agent_ctx = _ctx()
        inp = AddWaitlistInput(client_id=client_id, service_id=service_id)
        result = await add_waitlist(agent_ctx, inp, uc)

        uc.execute.assert_called_once()
        call_cmd = uc.execute.call_args[0][0]
        assert isinstance(call_cmd, AddWaitlistCommand)
        assert call_cmd.client_id == client_id
        assert call_cmd.service_id == service_id
        assert result is not None

    async def test_input_maps_preferred_staff_id(self):
        """add_waitlist passes preferred_staff_id to AddWaitlistCommand."""
        from interfaces.chat_tools.tools.waitlist_tools import add_waitlist, AddWaitlistInput
        from application.dto.commands import AddWaitlistCommand
        from application.dto.responses import WaitlistEntryResponse
        from domain.value_objects.waitlist_status import WaitlistStatus

        uc = AsyncMock()
        client_id = uuid.uuid4()
        service_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        uc.execute.return_value = WaitlistEntryResponse(
            id=uuid.uuid4(),
            client_id=client_id,
            service_id=service_id,
            preferred_staff_id=staff_id,
            preferred_start=None,
            preferred_end=None,
            status="pending",
            created_at=_utc(2026, 4, 1),
        )

        agent_ctx = _ctx()
        inp = AddWaitlistInput(
            client_id=client_id,
            service_id=service_id,
            preferred_staff_id=staff_id,
        )
        await add_waitlist(agent_ctx, inp, uc)

        call_cmd = uc.execute.call_args[0][0]
        assert isinstance(call_cmd, AddWaitlistCommand)
        assert call_cmd.preferred_staff_id == staff_id


class TestNotifyWaitlist:
    async def test_delegates_to_notify_waitlist_uc(self):
        """notify_waitlist calls NotifyWaitlistUseCase.execute() with cmd."""
        from interfaces.chat_tools.tools.waitlist_tools import notify_waitlist, NotifyWaitlistInput
        from application.dto.commands import NotifyWaitlistCommand
        from application.dto.responses import WaitlistEntryResponse
        from domain.value_objects.waitlist_status import WaitlistStatus

        uc = AsyncMock()
        service_id = uuid.uuid4()
        uc.execute.return_value = []  # empty notify result

        agent_ctx = _ctx()
        inp = NotifyWaitlistInput(service_id=service_id)
        result = await notify_waitlist(agent_ctx, inp, uc)

        uc.execute.assert_called_once()
        call_cmd = uc.execute.call_args[0][0]
        assert isinstance(call_cmd, NotifyWaitlistCommand)
        assert call_cmd.service_id == service_id
        assert call_cmd.staff_id is None
        assert result == []

    async def test_input_maps_staff_id_filter(self):
        """notify_waitlist passes staff_id to NotifyWaitlistCommand."""
        from interfaces.chat_tools.tools.waitlist_tools import notify_waitlist, NotifyWaitlistInput
        from application.dto.commands import NotifyWaitlistCommand

        uc = AsyncMock()
        service_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        uc.execute.return_value = []

        agent_ctx = _ctx()
        inp = NotifyWaitlistInput(service_id=service_id, staff_id=staff_id)
        await notify_waitlist(agent_ctx, inp, uc)

        call_cmd = uc.execute.call_args[0][0]
        assert isinstance(call_cmd, NotifyWaitlistCommand)
        assert call_cmd.staff_id == staff_id
