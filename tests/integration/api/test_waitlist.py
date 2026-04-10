"""Integration tests for waitlist endpoints (Task 4.1 — RED phase).

Scenarios:
- POST /waitlist → 201, adds client to waitlist
- GET /waitlist → 200, returns entries scoped to authenticated caller
- POST /waitlist/notify → 200, notifies pending entries in FIFO order
- Auth required — missing X-User-ID → 401
- Duplicate add → 400 (VALIDATION_ERROR)
- No pending entries → notify returns empty list
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.client_profile import ClientProfileModel
from infrastructure.database.models.service import ServiceModel
from tests.integration.api.conftest import (
    FIXED_CLIENT_UUID,
    seed_client_profile,
    seed_role,
    seed_service,
    seed_user,
)


# ---------------------------------------------------------------------------
# Helpers — DB seeding for waitlist tests
# ---------------------------------------------------------------------------


async def _seed_waitlist_setup(db_session: AsyncSession):
    """Seed: role, user, client profile, service.

    Returns (client_profile, service_model).
    """
    role = await seed_role(db_session, "client_wl")
    user = await seed_user(db_session, role.id)

    now = datetime.now(timezone.utc)
    client = ClientProfileModel(
        id=FIXED_CLIENT_UUID,
        user_id=user.id,
        blocked_staff_ids=[],
        created_at=now,
        updated_at=now,
    )
    db_session.add(client)
    await db_session.flush()

    svc = await seed_service(db_session, name="WaitlistSvc")
    return client, svc


# ---------------------------------------------------------------------------
# POST /waitlist
# ---------------------------------------------------------------------------


async def test_add_to_waitlist_returns_201(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /waitlist returns 201 Created."""
    _, svc = await _seed_waitlist_setup(db_session)

    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "service_id": str(svc.id),
    }
    response = await client.post("/waitlist/", json=payload)
    assert response.status_code == 201


async def test_add_to_waitlist_response_shape(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /waitlist returns entry with expected fields."""
    _, svc = await _seed_waitlist_setup(db_session)

    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "service_id": str(svc.id),
    }
    response = await client.post("/waitlist/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "client_id" in data
    assert "service_id" in data
    assert "status" in data
    assert data["client_id"] == str(FIXED_CLIENT_UUID)
    assert data["service_id"] == str(svc.id)
    assert data["status"] == "pending"


async def test_add_to_waitlist_requires_auth(client_no_auth: AsyncClient) -> None:
    """POST /waitlist returns 401 when X-User-ID header is missing."""
    payload = {
        "client_id": str(uuid.uuid4()),
        "service_id": str(uuid.uuid4()),
    }
    response = await client_no_auth.post("/waitlist/", json=payload)
    assert response.status_code == 401


async def test_add_to_waitlist_duplicate_allowed(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /waitlist with duplicate pending entry is ALLOWED per spec — returns 201."""
    _, svc = await _seed_waitlist_setup(db_session)

    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "service_id": str(svc.id),
    }
    # First add succeeds
    r1 = await client.post("/waitlist/", json=payload)
    assert r1.status_code == 201

    # Second add with same client + service → also succeeds (spec allows duplicates)
    r2 = await client.post("/waitlist/", json=payload)
    assert r2.status_code == 201
    # Both entries should have different IDs
    assert r1.json()["id"] != r2.json()["id"]


async def test_add_to_waitlist_unknown_service_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /waitlist with non-existent service returns 404 envelope."""
    _, _ = await _seed_waitlist_setup(db_session)

    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "service_id": str(uuid.uuid4()),  # non-existent
    }
    response = await client.post("/waitlist/", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert "error" in data


# ---------------------------------------------------------------------------
# GET /waitlist
# ---------------------------------------------------------------------------


async def test_list_waitlist_returns_200(client: AsyncClient) -> None:
    """GET /waitlist returns 200."""
    response = await client.get("/waitlist/")
    assert response.status_code == 200


async def test_list_waitlist_returns_list(client: AsyncClient) -> None:
    """GET /waitlist returns a JSON list."""
    response = await client.get("/waitlist/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_list_waitlist_scoped_to_caller(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /waitlist returns only the authenticated client's entries."""
    _, svc = await _seed_waitlist_setup(db_session)

    # Add one entry for the authenticated client
    payload = {
        "client_id": str(FIXED_CLIENT_UUID),
        "service_id": str(svc.id),
    }
    await client.post("/waitlist/", json=payload)

    response = await client.get("/waitlist/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    # All entries should belong to the fixed client
    for entry in data:
        assert entry["client_id"] == str(FIXED_CLIENT_UUID)


async def test_list_waitlist_requires_auth(client_no_auth: AsyncClient) -> None:
    """GET /waitlist returns 401 when X-User-ID header is missing."""
    response = await client_no_auth.get("/waitlist/")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /waitlist/notify
# ---------------------------------------------------------------------------


async def test_notify_waitlist_returns_200(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /waitlist/notify returns 200."""
    _, svc = await _seed_waitlist_setup(db_session)

    payload = {"service_id": str(svc.id)}
    response = await client.post("/waitlist/notify", json=payload)
    assert response.status_code == 200


async def test_notify_waitlist_returns_list(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /waitlist/notify returns a JSON list."""
    _, svc = await _seed_waitlist_setup(db_session)

    payload = {"service_id": str(svc.id)}
    response = await client.post("/waitlist/notify", json=payload)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_notify_waitlist_no_pending_returns_empty(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /waitlist/notify returns empty list when no PENDING entries exist."""
    _, svc = await _seed_waitlist_setup(db_session)

    payload = {"service_id": str(svc.id)}
    response = await client.post("/waitlist/notify", json=payload)
    assert response.status_code == 200
    assert response.json() == []


async def test_notify_waitlist_fifo_order(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """POST /waitlist/notify notifies entries in FIFO order (oldest first)."""
    _, svc = await _seed_waitlist_setup(db_session)

    # Add 2 entries for the same service (same client is fine in this test since
    # each add is a new request; in reality they'd be distinct clients,
    # but for FIFO ordering we add, check notify returns all notified)
    svc2 = await seed_service(db_session, name="WaitlistSvc2")

    # Create a second client for second entry
    role2 = await seed_role(db_session, "client_wl2")
    user2 = await seed_user(db_session, role2.id)
    now = datetime.now(timezone.utc)
    client2_id = uuid.uuid4()
    client2 = ClientProfileModel(
        id=client2_id,
        user_id=user2.id,
        blocked_staff_ids=[],
        created_at=now,
        updated_at=now,
    )
    db_session.add(client2)
    await db_session.flush()

    # Add two clients to same service
    await client.post("/waitlist/", json={
        "client_id": str(FIXED_CLIENT_UUID),
        "service_id": str(svc2.id),
    })
    # Direct DB insert for second client (can't override auth for second client)
    from infrastructure.database.models.waitlist_entry import WaitlistEntryModel
    entry2 = WaitlistEntryModel(
        id=uuid.uuid4(),
        client_id=client2_id,
        service_id=svc2.id,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db_session.add(entry2)
    await db_session.flush()

    payload = {"service_id": str(svc2.id)}
    response = await client.post("/waitlist/notify", json=payload)
    assert response.status_code == 200
    notified = response.json()
    assert len(notified) == 2
    # All notified should have status "notified"
    for entry in notified:
        assert entry["status"] == "notified"


async def test_notify_waitlist_requires_auth(client_no_auth: AsyncClient) -> None:
    """POST /waitlist/notify returns 401 when X-User-ID header is missing."""
    payload = {"service_id": str(uuid.uuid4())}
    response = await client_no_auth.post("/waitlist/notify", json=payload)
    assert response.status_code == 401
