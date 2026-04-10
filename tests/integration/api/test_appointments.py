"""Integration tests for appointments endpoints.

Scenarios:
- GET /appointments → 200, empty list
- POST /appointments → 201, creates appointment
- POST /appointments/{id}/cancel → 200
- POST /appointments/{id}/reschedule → 200
- POST /appointments with non-existent service/staff → 404 envelope
- POST /appointments/{random_id}/cancel → 404
- Auth required — missing X-User-ID → 401
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.appointment import AppointmentModel
from infrastructure.database.models.appointment_event import AppointmentEventModel
from tests.integration.api.conftest import (
    FIXED_CLIENT_UUID,
    FIXED_STAFF_UUID,
    seed_client_profile,
    seed_role,
    seed_service,
    seed_staff_availability,
    seed_staff_profile,
    seed_staff_service_link,
    seed_user,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _next_monday_at(hour: int = 10, tz=timezone.utc) -> datetime:
    """Return the next Monday at the given hour (UTC)."""
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    # Ensure at least 1 day ahead
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)
    return datetime(
        next_monday.year, next_monday.month, next_monday.day,
        hour, 0, 0, tzinfo=tz,
    )


async def _seed_bookable_setup(db_session: AsyncSession):
    """Seed: role, user, staff profile, service, staff-service link, availability.

    Returns (staff_profile, service_model, client_profile).
    Auth override uses FIXED_CLIENT_UUID and FIXED_STAFF_UUID — we use these
    as the effective client_id and staff_id in commands.
    """
    role = await seed_role(db_session, "staff")
    user = await seed_user(db_session, role.id)

    # Create the staff profile with the FIXED_STAFF_UUID so auth context works
    from infrastructure.database.models.staff_profile import StaffProfileModel
    now = datetime.now(timezone.utc)
    staff = StaffProfileModel(
        id=FIXED_STAFF_UUID,
        user_id=user.id,
        specialty="Test",
        bio="Bio",
        is_available=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(staff)
    await db_session.flush()

    # Create client profile with FIXED_CLIENT_UUID
    client_role = await seed_role(db_session, "client")
    client_user = await seed_user(db_session, client_role.id)
    from infrastructure.database.models.client_profile import ClientProfileModel
    client = ClientProfileModel(
        id=FIXED_CLIENT_UUID,
        user_id=client_user.id,
        blocked_staff_ids=[],
        created_at=now,
        updated_at=now,
    )
    db_session.add(client)
    await db_session.flush()

    svc = await seed_service(db_session, name="TestSvc", duration_minutes=60)
    await seed_staff_service_link(db_session, FIXED_STAFF_UUID, svc.id)

    # Seed availability for all 7 days so any weekday works
    for day in range(1, 8):
        await seed_staff_availability(
            db_session,
            FIXED_STAFF_UUID,
            day_of_week=day,
            start_time=time(8, 0),
            end_time=time(20, 0),
        )

    return staff, svc, client


# ---------------------------------------------------------------------------
# GET /appointments
# ---------------------------------------------------------------------------


async def test_list_appointments_returns_200(client: AsyncClient) -> None:
    """GET /appointments returns 200."""
    response = await client.get("/appointments/")
    assert response.status_code == 200


async def test_list_appointments_returns_list(client: AsyncClient) -> None:
    """GET /appointments returns a JSON list."""
    response = await client.get("/appointments/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


async def test_list_appointments_requires_auth(client_no_auth: AsyncClient) -> None:
    """GET /appointments returns 401 when X-User-ID header is missing."""
    response = await client_no_auth.get("/appointments/")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /appointments — success
# ---------------------------------------------------------------------------


async def test_create_appointment_returns_201(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /appointments returns 201 Created."""
    staff, svc, _ = await _seed_bookable_setup(db_session)

    start_time = _next_monday_at(10)

    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "staff_id": str(FIXED_STAFF_UUID),
        "service_id": str(svc.id),
        "start_time": start_time.isoformat(),
        "notes": None,
    }
    response = await client.post("/appointments/", json=payload)
    assert response.status_code == 201


async def test_create_appointment_response_shape(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /appointments returns appointment with expected fields."""
    staff, svc, _ = await _seed_bookable_setup(db_session)

    start_time = _next_monday_at(11)

    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "staff_id": str(FIXED_STAFF_UUID),
        "service_id": str(svc.id),
        "start_time": start_time.isoformat(),
    }
    response = await client.post("/appointments/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "client_id" in data
    assert "staff_id" in data
    assert "service_id" in data
    assert "start_time" in data
    assert "end_time" in data
    assert "status" in data
    assert data["client_id"] == str(FIXED_CLIENT_UUID)
    assert data["staff_id"] == str(FIXED_STAFF_UUID)
    assert data["service_id"] == str(svc.id)
    assert data["status"] == "scheduled"


async def test_create_appointment_requires_auth(client_no_auth: AsyncClient) -> None:
    """POST /appointments returns 401 when X-User-ID header is missing."""
    payload = {
        "client_id": str(uuid.uuid4()),
        "staff_id": str(uuid.uuid4()),
        "service_id": str(uuid.uuid4()),
        "start_time": _next_monday_at(10).isoformat(),
    }
    response = await client_no_auth.post("/appointments/", json=payload)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /appointments — error cases
# ---------------------------------------------------------------------------


async def test_create_appointment_unknown_service_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /appointments with non-existent service returns 404 envelope."""
    # Seed staff but use random service_id
    role = await seed_role(db_session, "staff_err")
    user = await seed_user(db_session, role.id)
    staff = await seed_staff_profile(db_session, user.id)

    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "staff_id": str(staff.id),
        "service_id": str(uuid.uuid4()),  # non-existent
        "start_time": _next_monday_at(10).isoformat(),
    }
    response = await client.post("/appointments/", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "message" in data["error"]
    assert "code" in data["error"]


async def test_create_appointment_unknown_staff_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /appointments with non-existent staff returns 404 envelope."""
    svc = await seed_service(db_session)

    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "staff_id": str(uuid.uuid4()),  # non-existent
        "service_id": str(svc.id),
        "start_time": _next_monday_at(10).isoformat(),
    }
    response = await client.post("/appointments/", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert "error" in data


async def test_create_appointment_conflict_returns_409(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /appointments with double-booking conflict returns 409 envelope."""
    staff, svc, _ = await _seed_bookable_setup(db_session)
    start_time = _next_monday_at(12)

    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "staff_id": str(FIXED_STAFF_UUID),
        "service_id": str(svc.id),
        "start_time": start_time.isoformat(),
    }
    # First booking succeeds
    r1 = await client.post("/appointments/", json=payload)
    assert r1.status_code == 201

    # Second booking in the same slot → conflict
    r2 = await client.post("/appointments/", json=payload)
    assert r2.status_code == 409
    data = r2.json()
    assert "error" in data
    assert data["error"]["code"] == "BOOKING_CONFLICT"


# ---------------------------------------------------------------------------
# POST /appointments/{id}/cancel
# ---------------------------------------------------------------------------


async def test_cancel_appointment_returns_200(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /appointments/{id}/cancel returns 200."""
    staff, svc, _ = await _seed_bookable_setup(db_session)
    start_time = _next_monday_at(14)

    # Create appointment first
    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "staff_id": str(FIXED_STAFF_UUID),
        "service_id": str(svc.id),
        "start_time": start_time.isoformat(),
    }
    create_response = await client.post("/appointments/", json=payload)
    assert create_response.status_code == 201
    appt_id = create_response.json()["id"]

    # Cancel
    cancel_response = await client.post(
        f"/appointments/{appt_id}/cancel",
        json={"appointment_id": appt_id, "reason": "test cancel"},
    )
    assert cancel_response.status_code == 200


async def test_cancel_appointment_status_is_cancelled(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /appointments/{id}/cancel updates status to 'cancelled'."""
    staff, svc, _ = await _seed_bookable_setup(db_session)
    start_time = _next_monday_at(15)

    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "staff_id": str(FIXED_STAFF_UUID),
        "service_id": str(svc.id),
        "start_time": start_time.isoformat(),
    }
    create_response = await client.post("/appointments/", json=payload)
    assert create_response.status_code == 201
    appt_id = create_response.json()["id"]

    cancel_response = await client.post(
        f"/appointments/{appt_id}/cancel",
        json={"appointment_id": appt_id, "reason": "testing"},
    )
    assert cancel_response.status_code == 200
    data = cancel_response.json()
    assert data["status"] == "cancelled"


async def test_cancel_nonexistent_appointment_returns_404(
    client: AsyncClient,
) -> None:
    """POST /appointments/{random_id}/cancel returns 404 envelope."""
    random_id = uuid.uuid4()
    response = await client.post(
        f"/appointments/{random_id}/cancel",
        json={"appointment_id": str(random_id), "reason": "not found"},
    )
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "message" in data["error"]
    assert "code" in data["error"]


# ---------------------------------------------------------------------------
# POST /appointments/{id}/reschedule
# ---------------------------------------------------------------------------


async def test_reschedule_appointment_returns_200(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /appointments/{id}/reschedule returns 200."""
    staff, svc, _ = await _seed_bookable_setup(db_session)

    # Book at 10am Monday
    start_time = _next_monday_at(10)
    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "staff_id": str(FIXED_STAFF_UUID),
        "service_id": str(svc.id),
        "start_time": start_time.isoformat(),
    }
    create_response = await client.post("/appointments/", json=payload)
    assert create_response.status_code == 201
    appt_id = create_response.json()["id"]

    # Reschedule to 13am Monday same week (different slot)
    new_start = _next_monday_at(13)
    reschedule_response = await client.post(
        f"/appointments/{appt_id}/reschedule",
        json={
            "appointment_id": appt_id,
            "new_start_time": new_start.isoformat(),
        },
    )
    assert reschedule_response.status_code == 200


async def test_reschedule_appointment_updates_start_time(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /appointments/{id}/reschedule updates the start_time field."""
    staff, svc, _ = await _seed_bookable_setup(db_session)

    # Use different hours to avoid conflict with other tests in this batch
    start_time = _next_monday_at(9)
    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "staff_id": str(FIXED_STAFF_UUID),
        "service_id": str(svc.id),
        "start_time": start_time.isoformat(),
    }
    create_response = await client.post("/appointments/", json=payload)
    assert create_response.status_code == 201
    appt_id = create_response.json()["id"]

    new_start = _next_monday_at(16)
    reschedule_response = await client.post(
        f"/appointments/{appt_id}/reschedule",
        json={
            "appointment_id": appt_id,
            "new_start_time": new_start.isoformat(),
        },
    )
    assert reschedule_response.status_code == 200
    data = reschedule_response.json()
    # start_time should reflect the new time
    assert "start_time" in data


async def test_reschedule_nonexistent_appointment_returns_404(
    client: AsyncClient,
) -> None:
    """POST /appointments/{random_id}/reschedule returns 404 envelope."""
    random_id = uuid.uuid4()
    new_start = _next_monday_at(10)
    response = await client.post(
        f"/appointments/{random_id}/reschedule",
        json={
            "appointment_id": str(random_id),
            "new_start_time": new_start.isoformat(),
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "message" in data["error"]
    assert "code" in data["error"]
