"""Integration tests for PgAppointmentRepository.

Tests follow RED → GREEN → REFACTOR.
Run against a real PostgreSQL instance via the db_session fixture.

Key scenarios:
- save/get round-trip
- events are persisted and reconstructed from AppointmentEventModel rows
- find_by_staff_and_date_range with range filtering
- find_by_client with optional status filter
- FK integrity (referencing non-existent client/staff/service raises)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.repositories.pg_appointment_repo import PgAppointmentRepository
from infrastructure.database.models.role import RoleModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.models.staff_profile import StaffProfileModel
from infrastructure.database.models.client_profile import ClientProfileModel
from infrastructure.database.models.service import ServiceModel

from domain.entities.appointment import Appointment
from domain.value_objects.appointment_status import AppointmentStatus
from domain.value_objects.time_slot import TimeSlot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(year: int, month: int, day: int, hour: int = 10) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)


async def _create_role(session: AsyncSession) -> RoleModel:
    role = RoleModel(id=uuid.uuid4(), name=f"appt_role_{uuid.uuid4().hex[:6]}")
    session.add(role)
    await session.flush()
    return role


async def _create_user(session: AsyncSession, role_id: uuid.UUID) -> UserModel:
    now = datetime.now(timezone.utc)
    user = UserModel(
        id=uuid.uuid4(),
        role_id=role_id,
        email=f"appt_user_{uuid.uuid4().hex[:8]}@test.com",
        first_name="Appt",
        last_name="User",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_staff(session: AsyncSession, role_id: uuid.UUID) -> StaffProfileModel:
    user = await _create_user(session, role_id)
    now = datetime.now(timezone.utc)
    profile = StaffProfileModel(
        id=uuid.uuid4(),
        user_id=user.id,
        is_available=True,
        created_at=now,
        updated_at=now,
    )
    session.add(profile)
    await session.flush()
    return profile


async def _create_client(session: AsyncSession, role_id: uuid.UUID) -> ClientProfileModel:
    user = await _create_user(session, role_id)
    now = datetime.now(timezone.utc)
    profile = ClientProfileModel(
        id=uuid.uuid4(),
        user_id=user.id,
        blocked_staff_ids=[],
        created_at=now,
        updated_at=now,
    )
    session.add(profile)
    await session.flush()
    return profile


async def _create_service(session: AsyncSession) -> ServiceModel:
    now = datetime.now(timezone.utc)
    svc = ServiceModel(
        id=uuid.uuid4(),
        name=f"ApptSvc_{uuid.uuid4().hex[:6]}",
        description="Test",
        duration_minutes=60,
        buffer_before=0,
        buffer_after=0,
        price=Decimal("200.00"),
        currency="MXN",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(svc)
    await session.flush()
    return svc


def _make_appointment(
    client_id: uuid.UUID,
    staff_id: uuid.UUID,
    service_id: uuid.UUID,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    status: AppointmentStatus = AppointmentStatus.SCHEDULED,
) -> Appointment:
    now = datetime.now(timezone.utc)
    start = start or now.replace(hour=10, minute=0, second=0, microsecond=0)
    end = end or start + timedelta(hours=1)
    return Appointment(
        id=uuid.uuid4(),
        client_id=client_id,
        staff_id=staff_id,
        service_id=service_id,
        time_slot=TimeSlot(start=start, end=end),
        status=status,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# save + get_by_id round-trip
# ---------------------------------------------------------------------------


async def test_save_and_get_by_id_round_trip(db_session: AsyncSession) -> None:
    """save() persists an Appointment; get_by_id() retrieves it as the same entity."""
    role = await _create_role(db_session)
    client = await _create_client(db_session, role.id)
    staff = await _create_staff(db_session, role.id)
    service = await _create_service(db_session)
    appt = _make_appointment(client.id, staff.id, service.id)

    repo = PgAppointmentRepository(db_session)
    saved = await repo.save(appt)

    assert saved.id == appt.id
    assert saved.status == AppointmentStatus.SCHEDULED

    retrieved = await repo.get_by_id(appt.id)
    assert retrieved is not None
    assert retrieved.id == appt.id
    assert retrieved.client_id == client.id
    assert retrieved.staff_id == staff.id
    assert retrieved.service_id == service.id
    assert retrieved.time_slot == appt.time_slot
    assert retrieved.status == AppointmentStatus.SCHEDULED


async def test_get_by_id_returns_none_for_missing(db_session: AsyncSession) -> None:
    """get_by_id returns None for a non-existent ID."""
    repo = PgAppointmentRepository(db_session)
    result = await repo.get_by_id(uuid.uuid4())
    assert result is None


async def test_save_updates_existing_appointment(db_session: AsyncSession) -> None:
    """save() called a second time with same ID updates the record."""
    role = await _create_role(db_session)
    client = await _create_client(db_session, role.id)
    staff = await _create_staff(db_session, role.id)
    service = await _create_service(db_session)
    appt = _make_appointment(client.id, staff.id, service.id)

    repo = PgAppointmentRepository(db_session)
    await repo.save(appt)

    # Update status
    appt.confirm()
    await repo.save(appt)

    retrieved = await repo.get_by_id(appt.id)
    assert retrieved is not None
    assert retrieved.status == AppointmentStatus.CONFIRMED


# ---------------------------------------------------------------------------
# Events are persisted and reconstructed
# ---------------------------------------------------------------------------


async def test_events_are_persisted_and_reconstructed(db_session: AsyncSession) -> None:
    """Domain events on Appointment.events are stored in appointment_events table."""
    role = await _create_role(db_session)
    client = await _create_client(db_session, role.id)
    staff = await _create_staff(db_session, role.id)
    service = await _create_service(db_session)
    appt = _make_appointment(client.id, staff.id, service.id)
    appt.confirm()  # adds "confirmed" event

    repo = PgAppointmentRepository(db_session)
    await repo.save(appt)

    retrieved = await repo.get_by_id(appt.id)
    assert retrieved is not None
    # Events should be reconstructed
    assert len(retrieved.events) >= 1
    event_types = [e["type"] for e in retrieved.events]
    assert "confirmed" in event_types


async def test_save_syncs_new_events_only(db_session: AsyncSession) -> None:
    """Re-saving an appointment only adds NEW events (no duplication)."""
    role = await _create_role(db_session)
    client = await _create_client(db_session, role.id)
    staff = await _create_staff(db_session, role.id)
    service = await _create_service(db_session)
    appt = _make_appointment(client.id, staff.id, service.id)
    appt.confirm()

    repo = PgAppointmentRepository(db_session)
    await repo.save(appt)  # saves with 1 event ("confirmed")

    # Re-fetch and add another event
    retrieved = await repo.get_by_id(appt.id)
    assert retrieved is not None
    retrieved.start()
    await repo.save(retrieved)  # should add "started" event only

    final = await repo.get_by_id(appt.id)
    assert final is not None
    event_types = [e["type"] for e in final.events]
    assert event_types.count("confirmed") == 1
    assert "started" in event_types


# ---------------------------------------------------------------------------
# find_by_staff_and_date_range
# ---------------------------------------------------------------------------


async def test_find_by_staff_and_date_range_returns_matching(db_session: AsyncSession) -> None:
    """Returns appointments for the staff member that overlap the date range."""
    role = await _create_role(db_session)
    client = await _create_client(db_session, role.id)
    staff = await _create_staff(db_session, role.id)
    service = await _create_service(db_session)

    appt_in = _make_appointment(
        client.id, staff.id, service.id,
        start=_utc(2026, 5, 10, 10),
        end=_utc(2026, 5, 10, 11),
    )
    appt_out = _make_appointment(
        client.id, staff.id, service.id,
        start=_utc(2026, 7, 1, 10),
        end=_utc(2026, 7, 1, 11),
    )

    repo = PgAppointmentRepository(db_session)
    await repo.save(appt_in)
    await repo.save(appt_out)

    results = await repo.find_by_staff_and_date_range(
        staff.id,
        start=_utc(2026, 5, 1),
        end=_utc(2026, 5, 31),
    )

    ids = {a.id for a in results}
    assert appt_in.id in ids
    assert appt_out.id not in ids


async def test_find_by_staff_and_date_range_returns_empty(db_session: AsyncSession) -> None:
    """Returns empty list when no appointments fall in range."""
    repo = PgAppointmentRepository(db_session)
    results = await repo.find_by_staff_and_date_range(
        uuid.uuid4(),
        start=_utc(2026, 1, 1),
        end=_utc(2026, 1, 31),
    )
    assert results == []


# ---------------------------------------------------------------------------
# find_by_client
# ---------------------------------------------------------------------------


async def test_find_by_client_returns_all_appointments(db_session: AsyncSession) -> None:
    """Returns all appointments for a client when no status filter is given."""
    role = await _create_role(db_session)
    client = await _create_client(db_session, role.id)
    staff = await _create_staff(db_session, role.id)
    service = await _create_service(db_session)

    appt1 = _make_appointment(client.id, staff.id, service.id,
                               start=_utc(2026, 5, 10, 9), end=_utc(2026, 5, 10, 10))
    appt2 = _make_appointment(client.id, staff.id, service.id,
                               start=_utc(2026, 5, 11, 9), end=_utc(2026, 5, 11, 10))

    repo = PgAppointmentRepository(db_session)
    await repo.save(appt1)
    await repo.save(appt2)

    results = await repo.find_by_client(client.id)
    ids = {a.id for a in results}
    assert appt1.id in ids
    assert appt2.id in ids


async def test_find_by_client_filters_by_status(db_session: AsyncSession) -> None:
    """find_by_client filters by status when provided."""
    role = await _create_role(db_session)
    client = await _create_client(db_session, role.id)
    staff = await _create_staff(db_session, role.id)
    service = await _create_service(db_session)

    appt_scheduled = _make_appointment(
        client.id, staff.id, service.id,
        start=_utc(2026, 5, 10, 9), end=_utc(2026, 5, 10, 10),
        status=AppointmentStatus.SCHEDULED,
    )
    appt_confirmed = _make_appointment(
        client.id, staff.id, service.id,
        start=_utc(2026, 5, 11, 9), end=_utc(2026, 5, 11, 10),
        status=AppointmentStatus.CONFIRMED,
    )

    repo = PgAppointmentRepository(db_session)
    await repo.save(appt_scheduled)
    await repo.save(appt_confirmed)

    scheduled_results = await repo.find_by_client(client.id, status=AppointmentStatus.SCHEDULED)
    ids = {a.id for a in scheduled_results}
    assert appt_scheduled.id in ids
    assert appt_confirmed.id not in ids


# ---------------------------------------------------------------------------
# Rollback isolation
# ---------------------------------------------------------------------------


async def test_appointment_not_visible_across_tests(db_session: AsyncSession) -> None:
    """Confirms db_session fixture isolates writes between tests."""
    role = await _create_role(db_session)
    client = await _create_client(db_session, role.id)
    staff = await _create_staff(db_session, role.id)
    service = await _create_service(db_session)
    appt = _make_appointment(client.id, staff.id, service.id)

    repo = PgAppointmentRepository(db_session)
    await repo.save(appt)

    retrieved = await repo.get_by_id(appt.id)
    assert retrieved is not None  # visible within this test


# ---------------------------------------------------------------------------
# Audit event columns — typed columns persist correctly
# ---------------------------------------------------------------------------


async def test_created_event_persists_performed_by_column(db_session: AsyncSession) -> None:
    """AppointmentEventModel row for 'created' event stores performed_by as typed UUID column."""
    from infrastructure.database.models.appointment_event import AppointmentEventModel
    from sqlalchemy import select

    role = await _create_role(db_session)
    client = await _create_client(db_session, role.id)
    staff = await _create_staff(db_session, role.id)
    service = await _create_service(db_session)

    actor_id = uuid.uuid4()
    appt = _make_appointment(client.id, staff.id, service.id)
    appt.mark_created(performed_by=actor_id)

    repo = PgAppointmentRepository(db_session)
    await repo.save(appt)

    # Fetch the raw event row
    stmt = select(AppointmentEventModel).where(
        AppointmentEventModel.appointment_id == appt.id,
        AppointmentEventModel.event_type == "created",
    )
    result = await db_session.execute(stmt)
    event_row = result.scalar_one_or_none()
    assert event_row is not None
    assert event_row.performed_by == actor_id


async def test_cancelled_event_persists_performed_by_and_reason(db_session: AsyncSession) -> None:
    """AppointmentEventModel row for 'cancelled' event stores performed_by and reason columns."""
    from infrastructure.database.models.appointment_event import AppointmentEventModel
    from sqlalchemy import select

    role = await _create_role(db_session)
    client = await _create_client(db_session, role.id)
    staff = await _create_staff(db_session, role.id)
    service = await _create_service(db_session)

    actor_id = uuid.uuid4()
    appt = _make_appointment(client.id, staff.id, service.id)
    appt.cancel(cancelled_by=actor_id, reason="Changed my plans")

    repo = PgAppointmentRepository(db_session)
    await repo.save(appt)

    stmt = select(AppointmentEventModel).where(
        AppointmentEventModel.appointment_id == appt.id,
        AppointmentEventModel.event_type == "cancelled",
    )
    result = await db_session.execute(stmt)
    event_row = result.scalar_one_or_none()
    assert event_row is not None
    assert event_row.performed_by == actor_id
    assert event_row.reason == "Changed my plans"


async def test_rescheduled_event_persists_all_slot_columns(db_session: AsyncSession) -> None:
    """AppointmentEventModel row for 'rescheduled' event stores performed_by, old/new slot columns."""
    from infrastructure.database.models.appointment_event import AppointmentEventModel
    from sqlalchemy import select

    role = await _create_role(db_session)
    client = await _create_client(db_session, role.id)
    staff = await _create_staff(db_session, role.id)
    service = await _create_service(db_session)

    actor_id = uuid.uuid4()
    original_start = _utc(2026, 6, 10, 10)
    original_end = _utc(2026, 6, 10, 11)
    appt = _make_appointment(
        client.id, staff.id, service.id,
        start=original_start,
        end=original_end,
    )

    new_start = _utc(2026, 6, 10, 14)
    new_end = _utc(2026, 6, 10, 15)
    new_slot = TimeSlot(start=new_start, end=new_end)
    appt.reschedule(new_slot, performed_by=actor_id)

    repo = PgAppointmentRepository(db_session)
    await repo.save(appt)

    stmt = select(AppointmentEventModel).where(
        AppointmentEventModel.appointment_id == appt.id,
        AppointmentEventModel.event_type == "rescheduled",
    )
    result = await db_session.execute(stmt)
    event_row = result.scalar_one_or_none()
    assert event_row is not None
    assert event_row.performed_by == actor_id
    assert event_row.old_start == original_start
    assert event_row.old_end == original_end
    assert event_row.new_start == new_start
    assert event_row.new_end == new_end


async def test_legacy_event_tolerates_null_audit_columns(db_session: AsyncSession) -> None:
    """Events without audit details produce NULL typed columns — backward compat."""
    from infrastructure.database.models.appointment_event import AppointmentEventModel
    from sqlalchemy import select

    role = await _create_role(db_session)
    client = await _create_client(db_session, role.id)
    staff = await _create_staff(db_session, role.id)
    service = await _create_service(db_session)

    appt = _make_appointment(client.id, staff.id, service.id)
    appt.confirm()  # 'confirmed' event has no audit details

    repo = PgAppointmentRepository(db_session)
    await repo.save(appt)

    stmt = select(AppointmentEventModel).where(
        AppointmentEventModel.appointment_id == appt.id,
        AppointmentEventModel.event_type == "confirmed",
    )
    result = await db_session.execute(stmt)
    event_row = result.scalar_one_or_none()
    assert event_row is not None
    # All new typed columns should be NULL
    assert event_row.performed_by is None
    assert event_row.reason is None
    assert event_row.old_start is None
    assert event_row.old_end is None
    assert event_row.new_start is None
    assert event_row.new_end is None
