"""Service tools — search, details, price, and duration.

Four tools:
- ``search_services``: list all active services (delegates to ListServicesUseCase).
- ``get_service_details``: full details for a single service.
- ``get_service_price``: derived — extracts price/currency from GetServiceDetailsUseCase.
- ``get_service_duration``: derived — extracts duration fields from GetServiceDetailsUseCase.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from application.use_cases.get_service_details import GetServiceDetailsUseCase
from application.use_cases.list_services import ListServicesUseCase
from interfaces.chat_tools.context import AgentContext


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class SearchServicesInput(BaseModel):
    """Input for search_services.  Currently no parameters — returns all active services."""


class GetServiceDetailsInput(BaseModel):
    """Input for get_service_details."""

    service_id: UUID


class GetServicePriceInput(BaseModel):
    """Input for get_service_price (derived tool)."""

    service_id: UUID


class GetServiceDurationInput(BaseModel):
    """Input for get_service_duration (derived tool)."""

    service_id: UUID


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


async def search_services(
    ctx: AgentContext,
    inp: SearchServicesInput,
    uc: ListServicesUseCase,
) -> list[Any]:
    """List all active services.

    Returns a list of service representation objects (ServiceResponse instances
    or dicts — callers should serialise as appropriate).
    """
    return await uc.execute()


async def get_service_details(
    ctx: AgentContext,
    inp: GetServiceDetailsInput,
    uc: GetServiceDetailsUseCase,
) -> Any:
    """Return full details for a single service.

    Raises:
        NotFoundError: if the service does not exist (handled by ToolExecutor).
    """
    return await uc.execute(inp.service_id)


async def get_service_price(
    ctx: AgentContext,
    inp: GetServicePriceInput,
    uc: GetServiceDetailsUseCase,
) -> dict[str, Any]:
    """Return only the price and currency for a service.

    Derived tool: internally calls GetServiceDetailsUseCase and extracts
    price-related fields so the LLM receives a minimal, focused response.
    """
    details = await uc.execute(inp.service_id)
    return {
        "service_id": str(inp.service_id),
        "price": str(details.price),
        "currency": details.currency,
    }


async def get_service_duration(
    ctx: AgentContext,
    inp: GetServiceDurationInput,
    uc: GetServiceDetailsUseCase,
) -> dict[str, Any]:
    """Return only the duration details for a service.

    Derived tool: internally calls GetServiceDetailsUseCase and extracts
    duration-related fields.
    """
    details = await uc.execute(inp.service_id)
    return {
        "service_id": str(inp.service_id),
        "duration_minutes": details.duration_minutes,
        "buffer_before": details.buffer_before,
        "buffer_after": details.buffer_after,
    }
