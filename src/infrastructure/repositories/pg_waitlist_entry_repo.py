"""PgWaitlistEntryRepository — PostgreSQL implementation of WaitlistEntryRepository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.waitlist_entry import WaitlistEntry
from domain.repositories.waitlist_entry_repository import WaitlistEntryRepository
from domain.value_objects.waitlist_status import WaitlistStatus
from infrastructure.database.models.waitlist_entry import WaitlistEntryModel


class PgWaitlistEntryRepository(WaitlistEntryRepository):
    """Postgres-backed repository for WaitlistEntry entities.

    Receives an ``AsyncSession`` via constructor injection; session lifecycle
    is managed by the caller (use-case / FastAPI dependency).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # WaitlistEntryRepository ABC implementation
    # ------------------------------------------------------------------

    async def save(self, entry: WaitlistEntry) -> WaitlistEntry:
        """Persist a new or updated WaitlistEntry and return it.

        Uses ``session.merge()`` so this works for both INSERT and UPDATE.
        """
        model = self._to_model(entry)
        await self._session.merge(model)
        await self._session.flush()
        return entry

    async def get_by_id(self, id: UUID) -> WaitlistEntry | None:
        """Return the WaitlistEntry with the given ID, or None if not found."""
        stmt = select(WaitlistEntryModel).where(WaitlistEntryModel.id == id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def find_pending_by_service(
        self,
        service_id: UUID,
        staff_id: UUID | None = None,
    ) -> list[WaitlistEntry]:
        """Return PENDING entries for a service ordered by created_at ASC (FIFO).

        Optionally filter by preferred_staff_id when staff_id is provided.
        """
        conditions = [
            WaitlistEntryModel.service_id == service_id,
            WaitlistEntryModel.status == WaitlistStatus.PENDING.value,
        ]
        if staff_id is not None:
            conditions.append(WaitlistEntryModel.preferred_staff_id == staff_id)

        stmt = (
            select(WaitlistEntryModel)
            .where(*conditions)
            .order_by(WaitlistEntryModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def find_by_client(self, client_id: UUID) -> list[WaitlistEntry]:
        """Return all waitlist entries for the given client."""
        stmt = select(WaitlistEntryModel).where(WaitlistEntryModel.client_id == client_id)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_entity(self, model: WaitlistEntryModel) -> WaitlistEntry:
        """Convert a WaitlistEntryModel to a WaitlistEntry domain entity."""
        return WaitlistEntry(
            id=model.id,
            client_id=model.client_id,
            service_id=model.service_id,
            preferred_staff_id=model.preferred_staff_id,
            preferred_start=model.preferred_start,
            preferred_end=model.preferred_end,
            status=WaitlistStatus(model.status),
            created_at=model.created_at,
            notes=model.notes,
        )

    def _to_model(self, entity: WaitlistEntry) -> WaitlistEntryModel:
        """Convert a WaitlistEntry domain entity to a WaitlistEntryModel row."""
        return WaitlistEntryModel(
            id=entity.id,
            client_id=entity.client_id,
            service_id=entity.service_id,
            preferred_staff_id=entity.preferred_staff_id,
            preferred_start=entity.preferred_start,
            preferred_end=entity.preferred_end,
            status=entity.status.value,
            created_at=entity.created_at,
            notes=entity.notes,
        )
