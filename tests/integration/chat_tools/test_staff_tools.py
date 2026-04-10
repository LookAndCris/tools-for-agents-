"""Integration tests for staff chat tools (T06).

Tests call handler functions directly with the test-scoped db_session,
bypassing ToolExecutor to preserve savepoint isolation.
"""
from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession

from interfaces.chat_tools.context import AgentContext
from interfaces.chat_tools.dependencies import make_find_available_staff_uc
from interfaces.chat_tools.tools.staff_tools import (
    FindAvailableStaffInput,
    find_available_staff,
)


# ---------------------------------------------------------------------------
# T06 — find_available_staff returns seeded staff for the given service
# ---------------------------------------------------------------------------


async def test_find_available_staff_returns_seeded_staff(
    db_session: AsyncSession,
    seeded_db: SimpleNamespace,
    admin_ctx: AgentContext,
) -> None:
    """T06: find_available_staff returns 1 staff member linked to service_corte."""
    uc = make_find_available_staff_uc(db_session)
    inp = FindAvailableStaffInput(service_id=seeded_db.service_corte.id)

    result = await find_available_staff(admin_ctx, inp, uc)

    assert len(result) == 1
    assert result[0].id == seeded_db.staff_profile.id
    assert result[0].is_available is True
