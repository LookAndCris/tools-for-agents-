"""Staff tools — find available staff for a service."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from application.dto.queries import FindAvailableStaffQuery
from application.use_cases.find_available_staff import FindAvailableStaffUseCase
from interfaces.chat_tools.context import AgentContext


class FindAvailableStaffInput(BaseModel):
    """Input for find_available_staff."""

    service_id: UUID


async def find_available_staff(
    ctx: AgentContext,
    inp: FindAvailableStaffInput,
    uc: FindAvailableStaffUseCase,
) -> list[Any]:
    """Return all staff members who offer the requested service.

    Delegates to ``FindAvailableStaffUseCase``.
    """
    query = FindAvailableStaffQuery(service_id=inp.service_id)
    return await uc.execute(query)
