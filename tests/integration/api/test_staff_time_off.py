"""Integration tests for staff-time-off endpoints.

Scenarios:
- POST /staff-time-off → 201, creates time-off record
- DELETE /staff-time-off/{id} → 204 empty body
- DELETE /staff-time-off/{random_id} → 404 envelope
- Auth required — missing X-User-ID → 401
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.api.conftest import (
    FIXED_STAFF_UUID,
    seed_role,
    seed_staff_profile,
    seed_user,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_staff_with_fixed_id(db_session: AsyncSession):
    """Seed a staff profile using FIXED_STAFF_UUID (matched by auth override)."""
    from infrastructure.database.models.staff_profile import StaffProfileModel

    role = await seed_role(db_session, "staff_to")
    user = await seed_user(db_session, role.id)
    now = datetime.now(timezone.utc)
    staff = StaffProfileModel(
        id=FIXED_STAFF_UUID,
        user_id=user.id,
        specialty="Time Off Test",
        bio="Bio",
        is_available=True,
        created_at=now,
        updated_at=now,
    )
    db_session.add(staff)
    await db_session.flush()
    return staff


def _future_window(hours_ahead: int = 24, duration_hours: int = 2):
    """Return (start_time, end_time) as ISO strings for a future time block."""
    start = datetime.now(timezone.utc) + timedelta(hours=hours_ahead)
    end = start + timedelta(hours=duration_hours)
    return start.isoformat(), end.isoformat()


# ---------------------------------------------------------------------------
# POST /staff-time-off
# ---------------------------------------------------------------------------


async def test_block_staff_time_returns_201(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /staff-time-off returns 201 Created."""
    await _seed_staff_with_fixed_id(db_session)
    start, end = _future_window(24, 2)

    payload = {
        "staff_id": str(FIXED_STAFF_UUID),
        "start_time": start,
        "end_time": end,
        "reason": "Vacation",
    }
    response = await client.post("/staff-time-off/", json=payload)
    assert response.status_code == 201


async def test_block_staff_time_response_shape(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /staff-time-off returns time-off record with expected fields."""
    await _seed_staff_with_fixed_id(db_session)
    start, end = _future_window(48, 3)

    payload = {
        "staff_id": str(FIXED_STAFF_UUID),
        "start_time": start,
        "end_time": end,
        "reason": "Holiday",
    }
    response = await client.post("/staff-time-off/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "staff_id" in data
    assert "start_time" in data
    assert "end_time" in data
    assert data["staff_id"] == str(FIXED_STAFF_UUID)


async def test_block_staff_time_nonexistent_staff_returns_404(
    client: AsyncClient,
) -> None:
    """POST /staff-time-off with unknown staff_id returns 404 envelope."""
    start, end = _future_window(24, 2)
    payload = {
        "staff_id": str(uuid.uuid4()),  # non-existent
        "start_time": start,
        "end_time": end,
        "reason": None,
    }
    response = await client.post("/staff-time-off/", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "message" in data["error"]
    assert "code" in data["error"]


async def test_block_staff_time_invalid_range_returns_400(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /staff-time-off with start >= end returns 400 envelope."""
    await _seed_staff_with_fixed_id(db_session)

    now = datetime.now(timezone.utc)
    start = (now + timedelta(hours=2)).isoformat()
    end = (now + timedelta(hours=1)).isoformat()  # end before start

    payload = {
        "staff_id": str(FIXED_STAFF_UUID),
        "start_time": start,
        "end_time": end,
        "reason": "Invalid range",
    }
    response = await client.post("/staff-time-off/", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


async def test_block_staff_time_requires_auth(client_no_auth: AsyncClient) -> None:
    """POST /staff-time-off returns 401 when X-User-ID header is missing."""
    start, end = _future_window(24, 2)
    payload = {
        "staff_id": str(uuid.uuid4()),
        "start_time": start,
        "end_time": end,
    }
    response = await client_no_auth.post("/staff-time-off/", json=payload)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /staff-time-off/{id}
# ---------------------------------------------------------------------------


async def test_delete_staff_time_off_returns_204(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """DELETE /staff-time-off/{id} returns 204 No Content."""
    await _seed_staff_with_fixed_id(db_session)
    start, end = _future_window(72, 2)

    # Create a time-off block first
    create_payload = {
        "staff_id": str(FIXED_STAFF_UUID),
        "start_time": start,
        "end_time": end,
        "reason": "To be deleted",
    }
    create_response = await client.post("/staff-time-off/", json=create_payload)
    assert create_response.status_code == 201
    time_off_id = create_response.json()["id"]

    # Delete it
    delete_response = await client.delete(f"/staff-time-off/{time_off_id}")
    assert delete_response.status_code == 204


async def test_delete_staff_time_off_empty_body(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """DELETE /staff-time-off/{id} returns empty response body."""
    await _seed_staff_with_fixed_id(db_session)
    start, end = _future_window(96, 2)

    create_payload = {
        "staff_id": str(FIXED_STAFF_UUID),
        "start_time": start,
        "end_time": end,
        "reason": "Empty body check",
    }
    create_response = await client.post("/staff-time-off/", json=create_payload)
    assert create_response.status_code == 201
    time_off_id = create_response.json()["id"]

    delete_response = await client.delete(f"/staff-time-off/{time_off_id}")
    assert delete_response.status_code == 204
    # Body must be empty (no JSON content)
    assert delete_response.content == b""


async def test_delete_nonexistent_time_off_returns_404(
    client: AsyncClient,
) -> None:
    """DELETE /staff-time-off/{random_id} returns 404 envelope."""
    random_id = uuid.uuid4()
    response = await client.delete(f"/staff-time-off/{random_id}")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "message" in data["error"]
    assert "code" in data["error"]


async def test_delete_staff_time_off_requires_auth(
    client_no_auth: AsyncClient,
) -> None:
    """DELETE /staff-time-off/{id} returns 401 when X-User-ID header is missing."""
    random_id = uuid.uuid4()
    response = await client_no_auth.delete(f"/staff-time-off/{random_id}")
    assert response.status_code == 401
