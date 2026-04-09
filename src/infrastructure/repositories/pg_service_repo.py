"""PgServiceRepository — PostgreSQL implementation of ServiceRepository."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.service import Service
from domain.repositories.service_repository import ServiceRepository
from domain.value_objects.money import Money
from domain.value_objects.service_duration import ServiceDuration
from infrastructure.database.models.service import ServiceModel


class PgServiceRepository(ServiceRepository):
    """Postgres-backed repository for Service entities.

    Receives an ``AsyncSession`` via constructor injection; session lifecycle
    is managed by the caller (use-case / FastAPI dependency).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # ServiceRepository ABC implementation
    # ------------------------------------------------------------------

    async def get_by_id(self, id: UUID) -> Service | None:
        """Return the Service with the given ID, or None if not found."""
        stmt = select(ServiceModel).where(ServiceModel.id == id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def get_all_active(self) -> list[Service]:
        """Return all active services."""
        stmt = select(ServiceModel).where(ServiceModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def find_by_ids(self, ids: list[UUID]) -> list[Service]:
        """Return all services whose IDs are in *ids*."""
        if not ids:
            return []
        stmt = select(ServiceModel).where(ServiceModel.id.in_(ids))
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_entity(self, model: ServiceModel) -> Service:
        """Convert a ``ServiceModel`` row to a pure ``Service`` domain entity."""
        duration = ServiceDuration(
            buffer_before=model.buffer_before,
            duration_minutes=model.duration_minutes,
            buffer_after=model.buffer_after,
        )
        price = Money(
            amount=Decimal(str(model.price)),
            currency=model.currency,
        )
        return Service(
            id=model.id,
            name=model.name,
            description=model.description,
            duration=duration,
            price=price,
            is_active=model.is_active,
            created_at=model.created_at,
        )

    def _to_model(self, entity: Service) -> ServiceModel:
        """Convert a pure ``Service`` domain entity to a ``ServiceModel`` row."""
        return ServiceModel(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            duration_minutes=entity.duration.duration_minutes,
            buffer_before=entity.duration.buffer_before,
            buffer_after=entity.duration.buffer_after,
            price=entity.price.amount,
            currency=entity.price.currency,
            is_active=entity.is_active,
            created_at=entity.created_at,
        )
