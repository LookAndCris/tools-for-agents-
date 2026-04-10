"""Integration tests for GET /health.

Verifies:
- 200 status code
- Response body contains {"status": "ok"}
"""
from __future__ import annotations

from httpx import AsyncClient


async def test_health_returns_200(client: AsyncClient) -> None:
    """GET /health returns HTTP 200."""
    response = await client.get("/health")
    assert response.status_code == 200


async def test_health_body_contains_status_ok(client: AsyncClient) -> None:
    """GET /health body contains {"status": "ok"}."""
    response = await client.get("/health")
    data = response.json()
    assert data.get("status") == "ok"


async def test_health_no_auth_required(client_no_auth: AsyncClient) -> None:
    """GET /health does not require authentication — works without X-User-ID."""
    response = await client_no_auth.get("/health")
    assert response.status_code == 200
