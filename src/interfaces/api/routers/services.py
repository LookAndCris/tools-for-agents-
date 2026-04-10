"""Services router — read-only endpoints for the service catalog.

Both endpoints are public (no auth required).
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from application.dto.responses import ServiceResponse
from application.use_cases.get_service_details import GetServiceDetailsUseCase
from application.use_cases.list_services import ListServicesUseCase
from interfaces.api.dependencies import get_list_services_uc, get_service_details_uc

router = APIRouter()


@router.get("/", response_model=list[ServiceResponse])
async def list_services(
    uc: ListServicesUseCase = Depends(get_list_services_uc),
) -> list[ServiceResponse]:
    """Return all active services."""
    return await uc.execute()


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: UUID,
    uc: GetServiceDetailsUseCase = Depends(get_service_details_uc),
) -> ServiceResponse:
    """Return details for a single service.

    Raises 404 if the service does not exist.
    """
    return await uc.execute(service_id)
