"""Integration tests for staff endpoints.

Scenarios:
- GET /staff/available?service_id=... → 200 (auth required)
- GET /staff/available-slots?... → 200 (auth required)
- Auth required — missing X-User-ID → 401
"""
from __future__ import annotations

import uuid
from datetime import date, time

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.api.conftest import (
    seed_role,
    seed_service,
    seed_staff_availability,
    seed_staff_profile,
    seed_staff_service_link,
    seed_user,
)


async def test_get_available_staff_returns_200(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /staff/available?service_id=... returns 200."""
    svc = await seed_service(db_session)
    response = await client.get("/staff/available", params={"service_id": str(svc.id)})
    assert response.status_code == 200


async def test_get_available_staff_returns_list(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /staff/available returns a JSON list."""
    svc = await seed_service(db_session)
    response = await client.get("/staff/available", params={"service_id": str(svc.id)})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


async def test_get_available_staff_with_linked_staff(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /staff/available returns the staff member linked to the service."""
    role = await seed_role(db_session, "staff")
    user = await seed_user(db_session, role.id)
    staff = await seed_staff_profile(db_session, user.id)
    svc = await seed_service(db_session)
    await seed_staff_service_link(db_session, staff.id, svc.id)

    response = await client.get("/staff/available", params={"service_id": str(svc.id)})
    assert response.status_code == 200
    data = response.json()
    staff_ids = [item["id"] for item in data]
    assert str(staff.id) in staff_ids


async def test_get_available_staff_requires_auth(client_no_auth: AsyncClient) -> None:
    """GET /staff/available returns 401 when X-User-ID header is missing."""
    random_service_id = uuid.uuid4()
    response = await client_no_auth.get(
        "/staff/available", params={"service_id": str(random_service_id)}
    )
    assert response.status_code == 401


async def test_get_available_slots_returns_200(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /staff/available-slots returns 200 with required params."""
    role = await seed_role(db_session, "staff")
    user = await seed_user(db_session, role.id)
    staff = await seed_staff_profile(db_session, user.id)
    svc = await seed_service(db_session, duration_minutes=60)
    # Seed availability for Monday (1) from 8am-6pm
    await seed_staff_availability(
        db_session,
        staff.id,
        day_of_week=1,
        start_time=time(8, 0),
        end_time=time(18, 0),
    )

    # Find the next Monday
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7 or 7  # at least 1 day out
    next_monday = today.replace(
        day=today.day + days_until_monday
    )
    # Fallback: use a fixed future date range that includes a Monday
    from datetime import timedelta
    date_from = today + timedelta(days=1)
    date_to = date_from + timedelta(days=6)

    response = await client.get(
        "/staff/available-slots",
        params={
            "staff_id": str(staff.id),
            "service_id": str(svc.id),
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
    )
    assert response.status_code == 200


async def test_get_available_slots_response_shape(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /staff/available-slots returns staff_id, service_id, and slots."""
    role = await seed_role(db_session, "staff")
    user = await seed_user(db_session, role.id)
    staff = await seed_staff_profile(db_session, user.id)
    svc = await seed_service(db_session, duration_minutes=60)

    from datetime import timedelta
    date_from = date.today() + timedelta(days=1)
    date_to = date_from + timedelta(days=6)

    response = await client.get(
        "/staff/available-slots",
        params={
            "staff_id": str(staff.id),
            "service_id": str(svc.id),
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "staff_id" in data
    assert "service_id" in data
    assert "slots" in data
    assert isinstance(data["slots"], list)
    assert data["staff_id"] == str(staff.id)
    assert data["service_id"] == str(svc.id)


async def test_get_available_slots_invalid_service_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /staff/available-slots returns 404 if service does not exist."""
    role = await seed_role(db_session, "staff")
    user = await seed_user(db_session, role.id)
    staff = await seed_staff_profile(db_session, user.id)

    from datetime import timedelta
    date_from = date.today() + timedelta(days=1)
    date_to = date_from + timedelta(days=6)

    response = await client.get(
        "/staff/available-slots",
        params={
            "staff_id": str(staff.id),
            "service_id": str(uuid.uuid4()),  # non-existent service
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
    )
    assert response.status_code == 404
    data = response.json()
    assert "error" in data


async def test_get_available_slots_requires_auth(client_no_auth: AsyncClient) -> None:
    """GET /staff/available-slots returns 401 when X-User-ID header is missing."""
    from datetime import timedelta
    date_from = date.today() + timedelta(days=1)
    date_to = date_from + timedelta(days=6)

    response = await client_no_auth.get(
        "/staff/available-slots",
        params={
            "staff_id": str(uuid.uuid4()),
            "service_id": str(uuid.uuid4()),
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
        },
    )
    assert response.status_code == 401
