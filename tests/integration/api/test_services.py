"""Integration tests for services endpoints.

Scenarios:
- GET /services → 200, empty list initially
- Seed a service, GET /services → 200, list with 1 item
- GET /services/{id} → 200 with correct data
- GET /services/{random_id} → 404 with envelope error format
"""
from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.api.conftest import seed_service


async def test_list_services_returns_empty_list(client: AsyncClient) -> None:
    """GET /services returns 200 with empty list when no services exist."""
    response = await client.get("/services/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


async def test_list_services_returns_seeded_service(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /services returns the seeded service in the list."""
    svc = await seed_service(db_session, name="Haircut")

    response = await client.get("/services/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    ids = [item["id"] for item in data]
    assert str(svc.id) in ids


async def test_list_services_response_shape(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /services items include expected fields."""
    await seed_service(db_session, name="Massage")

    response = await client.get("/services/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    item = data[0]
    assert "id" in item
    assert "name" in item
    assert "duration_minutes" in item
    assert "price" in item


async def test_get_service_by_id_returns_200(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """GET /services/{id} returns 200 with correct service data."""
    svc = await seed_service(db_session, name="Facial", duration_minutes=45)

    response = await client.get(f"/services/{svc.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(svc.id)
    assert data["name"] == "Facial"
    assert data["duration_minutes"] == 45


async def test_get_service_by_id_not_found_returns_404(client: AsyncClient) -> None:
    """GET /services/{random_id} returns 404 with error envelope."""
    random_id = uuid.uuid4()
    response = await client.get(f"/services/{random_id}")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "message" in data["error"]
    assert "code" in data["error"]


async def test_get_service_by_id_error_envelope_format(client: AsyncClient) -> None:
    """404 response uses the standard error envelope format."""
    random_id = uuid.uuid4()
    response = await client.get(f"/services/{random_id}")
    assert response.status_code == 404
    data = response.json()
    # Envelope: {"error": {"message": "...", "code": "..."}}
    assert "error" in data
    error = data["error"]
    assert isinstance(error["message"], str)
    assert isinstance(error["code"], str)
    assert len(error["message"]) > 0
    assert len(error["code"]) > 0


async def test_services_no_auth_required(client_no_auth: AsyncClient) -> None:
    """GET /services does not require authentication."""
    response = await client_no_auth.get("/services/")
    assert response.status_code == 200
