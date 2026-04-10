"""Integration tests for service chat tools (T01, T02).

Tests call handler functions directly with the test-scoped db_session,
bypassing ToolExecutor to preserve savepoint isolation.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from interfaces.chat_tools.context import AgentContext
from interfaces.chat_tools.dependencies import (
    make_get_service_details_uc,
    make_list_services_uc,
)
from interfaces.chat_tools.tools.service_tools import (
    GetServiceDetailsInput,
    SearchServicesInput,
    get_service_details,
    search_services,
)


# ---------------------------------------------------------------------------
# T01 — search_services returns all active services
# ---------------------------------------------------------------------------


async def test_search_services_returns_all_active_services(
    db_session: AsyncSession,
    seeded_db: SimpleNamespace,
    admin_ctx: AgentContext,
) -> None:
    """T01: search_services returns the 3 seeded active services."""
    uc = make_list_services_uc(db_session)
    result = await search_services(admin_ctx, SearchServicesInput(), uc)

    # Should return exactly the 3 seeded services
    assert len(result) == 3

    # Verify each item has the expected fields
    for svc in result:
        assert hasattr(svc, "name")
        assert hasattr(svc, "price")
        assert hasattr(svc, "duration_minutes")
        assert svc.name  # non-empty string
        assert svc.price >= Decimal("0")
        assert svc.duration_minutes > 0


# ---------------------------------------------------------------------------
# T02 — get_service_details returns the correct service
# ---------------------------------------------------------------------------


async def test_get_service_details_returns_correct_service(
    db_session: AsyncSession,
    seeded_db: SimpleNamespace,
    admin_ctx: AgentContext,
) -> None:
    """T02: get_service_details returns correct data for 'Corte de cabello'."""
    uc = make_get_service_details_uc(db_session)
    inp = GetServiceDetailsInput(service_id=seeded_db.service_corte.id)

    result = await get_service_details(admin_ctx, inp, uc)

    assert result.name == "Corte de cabello"
    assert result.duration_minutes == 45
    assert result.price == Decimal("250.00")
