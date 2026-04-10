"""Slot tools — find available booking slots."""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from application.dto.queries import FindAvailableSlotsQuery
from application.use_cases.find_available_slots import FindAvailableSlotsUseCase
from interfaces.chat_tools.context import AgentContext


class FindAvailableSlotsInput(BaseModel):
    """Input for find_available_slots."""

    staff_id: UUID
    service_id: UUID
    date_from: date
    date_to: date


async def find_available_slots(
    ctx: AgentContext,
    inp: FindAvailableSlotsInput,
    uc: FindAvailableSlotsUseCase,
) -> Any:
    """Return available booking slots for a staff member within a date range.

    Delegates to ``FindAvailableSlotsUseCase``.
    """
    query = FindAvailableSlotsQuery(
        staff_id=inp.staff_id,
        service_id=inp.service_id,
        date_from=inp.date_from,
        date_to=inp.date_to,
    )
    return await uc.execute(query)
