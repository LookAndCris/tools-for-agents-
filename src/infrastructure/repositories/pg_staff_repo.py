"""PgStaffRepository — PostgreSQL implementation of StaffRepository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.staff import Staff
from domain.repositories.staff_repository import StaffRepository
from infrastructure.database.models.staff_profile import StaffProfileModel
from infrastructure.database.models.staff_service import StaffServiceModel


class PgStaffRepository(StaffRepository):
    """Postgres-backed repository for Staff entities.

    Receives an ``AsyncSession`` via constructor injection; session lifecycle
    is managed by the caller (use-case / FastAPI dependency).

    Eager-loads the ``staff_services`` junction rows so ``service_ids`` can
    be populated without an extra lazy-load round trip.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # StaffRepository ABC implementation
    # ------------------------------------------------------------------

    async def get_by_id(self, id: UUID) -> Staff | None:
        """Return the Staff member with the given ID, or None if not found."""
        stmt = (
            select(StaffProfileModel)
            .options(selectinload(StaffProfileModel.staff_services))
            .where(StaffProfileModel.id == id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def find_by_service(self, service_id: UUID) -> list[Staff]:
        """Return all staff members who offer the given service."""
        stmt = (
            select(StaffProfileModel)
            .options(selectinload(StaffProfileModel.staff_services))
            .join(
                StaffServiceModel,
                StaffProfileModel.id == StaffServiceModel.staff_id,
            )
            .where(StaffServiceModel.service_id == service_id)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_entity(self, model: StaffProfileModel) -> Staff:
        """Convert a ``StaffProfileModel`` row to a pure ``Staff`` domain entity."""
        service_ids = frozenset(ss.service_id for ss in (model.staff_services or []))
        return Staff(
            id=model.id,
            user_id=model.user_id,
            created_at=model.created_at,
            specialty=model.specialty,
            bio=model.bio,
            is_available=model.is_available,
            service_ids=service_ids,
        )

    def _to_model(self, entity: Staff) -> StaffProfileModel:
        """Convert a pure ``Staff`` domain entity to a ``StaffProfileModel`` row."""
        return StaffProfileModel(
            id=entity.id,
            user_id=entity.user_id,
            created_at=entity.created_at,
            specialty=entity.specialty,
            bio=entity.bio,
            is_available=entity.is_available,
        )
