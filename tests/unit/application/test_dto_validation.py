"""Tests for application layer DTOs — commands, queries, responses, and UserContext."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest


def utc(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# UserContext tests
# ---------------------------------------------------------------------------

class TestUserContext:
    def test_basic_construction(self):
        from application.dto.user_context import UserContext
        ctx = UserContext(
            user_id=uuid.uuid4(),
            role="client",
        )
        assert ctx.role == "client"
        assert ctx.staff_id is None
        assert ctx.client_id is None

    def test_full_construction(self):
        from application.dto.user_context import UserContext
        uid = uuid.uuid4()
        sid = uuid.uuid4()
        cid = uuid.uuid4()
        ctx = UserContext(user_id=uid, role="staff", staff_id=sid, client_id=cid)
        assert ctx.user_id == uid
        assert ctx.staff_id == sid
        assert ctx.client_id == cid

    def test_frozen(self):
        from application.dto.user_context import UserContext
        ctx = UserContext(user_id=uuid.uuid4(), role="admin")
        with pytest.raises((AttributeError, TypeError)):
            ctx.role = "client"  # type: ignore


# ---------------------------------------------------------------------------
# Command DTO tests
# ---------------------------------------------------------------------------

class TestCreateAppointmentCommand:
    def test_valid(self):
        from application.dto.commands import CreateAppointmentCommand
        cmd = CreateAppointmentCommand(
            client_id=uuid.uuid4(),
            staff_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            start_time=utc(2026, 5, 1, 10),
        )
        assert cmd.notes is None

    def test_with_notes(self):
        from application.dto.commands import CreateAppointmentCommand
        cmd = CreateAppointmentCommand(
            client_id=uuid.uuid4(),
            staff_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            start_time=utc(2026, 5, 1, 10),
            notes="Please confirm",
        )
        assert cmd.notes == "Please confirm"

    def test_missing_required_field_raises(self):
        from application.dto.commands import CreateAppointmentCommand
        with pytest.raises(Exception):  # Pydantic V2 raises ValidationError
            CreateAppointmentCommand(
                client_id=uuid.uuid4(),
                staff_id=uuid.uuid4(),
                # missing service_id and start_time
            )


class TestCancelAppointmentCommand:
    def test_valid(self):
        from application.dto.commands import CancelAppointmentCommand
        cmd = CancelAppointmentCommand(appointment_id=uuid.uuid4())
        assert cmd.reason is None

    def test_with_reason(self):
        from application.dto.commands import CancelAppointmentCommand
        cmd = CancelAppointmentCommand(appointment_id=uuid.uuid4(), reason="No longer needed")
        assert cmd.reason == "No longer needed"


class TestRescheduleAppointmentCommand:
    def test_valid(self):
        from application.dto.commands import RescheduleAppointmentCommand
        cmd = RescheduleAppointmentCommand(
            appointment_id=uuid.uuid4(),
            new_start_time=utc(2026, 5, 2, 14),
        )
        assert cmd.new_start_time.year == 2026


class TestBlockStaffTimeCommand:
    def test_valid(self):
        from application.dto.commands import BlockStaffTimeCommand
        cmd = BlockStaffTimeCommand(
            staff_id=uuid.uuid4(),
            start_time=utc(2026, 5, 1, 8),
            end_time=utc(2026, 5, 1, 12),
        )
        assert cmd.reason is None


class TestUnblockStaffTimeCommand:
    def test_valid(self):
        from application.dto.commands import UnblockStaffTimeCommand
        cmd = UnblockStaffTimeCommand(time_off_id=uuid.uuid4())
        assert cmd.time_off_id is not None


# ---------------------------------------------------------------------------
# Query DTO tests
# ---------------------------------------------------------------------------

class TestFindAvailableSlotsQuery:
    def test_valid(self):
        from application.dto.queries import FindAvailableSlotsQuery
        q = FindAvailableSlotsQuery(
            staff_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            date_from=date(2026, 5, 1),
            date_to=date(2026, 5, 7),
        )
        assert q.date_from <= q.date_to


class TestFindAvailableStaffQuery:
    def test_valid(self):
        from application.dto.queries import FindAvailableStaffQuery
        q = FindAvailableStaffQuery(service_id=uuid.uuid4())
        assert q.service_id is not None


class TestGetClientAppointmentsQuery:
    def test_valid_no_status(self):
        from application.dto.queries import GetClientAppointmentsQuery
        q = GetClientAppointmentsQuery(client_id=uuid.uuid4())
        assert q.status is None

    def test_valid_with_status(self):
        from application.dto.queries import GetClientAppointmentsQuery
        q = GetClientAppointmentsQuery(client_id=uuid.uuid4(), status="scheduled")
        assert q.status == "scheduled"


# ---------------------------------------------------------------------------
# Response DTO tests
# ---------------------------------------------------------------------------

class TestServiceResponse:
    def test_construction(self):
        from application.dto.responses import ServiceResponse
        resp = ServiceResponse(
            id=uuid.uuid4(),
            name="Haircut",
            description="A standard haircut",
            duration_minutes=60,
            buffer_before=5,
            buffer_after=5,
            price=Decimal("25.00"),
            currency="USD",
            is_active=True,
        )
        assert resp.name == "Haircut"
        assert resp.price == Decimal("25.00")


class TestStaffResponse:
    def test_construction(self):
        from application.dto.responses import StaffResponse
        sid = uuid.uuid4()
        resp = StaffResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            specialty="Massage",
            bio="Expert therapist",
            is_available=True,
            service_ids=[sid],
        )
        assert resp.specialty == "Massage"
        assert sid in resp.service_ids


class TestAppointmentResponse:
    def test_construction(self):
        from application.dto.responses import AppointmentResponse
        now = utc(2026, 5, 1, 10)
        resp = AppointmentResponse(
            id=uuid.uuid4(),
            client_id=uuid.uuid4(),
            staff_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            start_time=now,
            end_time=utc(2026, 5, 1, 11),
            status="scheduled",
            notes=None,
            created_at=now,
        )
        assert resp.status == "scheduled"
        assert resp.notes is None


class TestAvailableSlotsResponse:
    def test_construction(self):
        from application.dto.responses import AvailableSlotsResponse
        slots = [utc(2026, 5, 1, 9), utc(2026, 5, 1, 10)]
        resp = AvailableSlotsResponse(
            staff_id=uuid.uuid4(),
            service_id=uuid.uuid4(),
            slots=slots,
        )
        assert len(resp.slots) == 2


class TestStaffTimeOffResponse:
    def test_construction(self):
        from application.dto.responses import StaffTimeOffResponse
        resp = StaffTimeOffResponse(
            id=uuid.uuid4(),
            staff_id=uuid.uuid4(),
            start_time=utc(2026, 5, 1, 8),
            end_time=utc(2026, 5, 1, 12),
            reason="Vacation",
        )
        assert resp.reason == "Vacation"
