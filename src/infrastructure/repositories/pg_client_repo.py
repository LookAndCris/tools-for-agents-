"""PgClientRepository — PostgreSQL implementation of ClientRepository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.client import Client
from domain.repositories.client_repository import ClientRepository
from infrastructure.database.models.client_profile import ClientProfileModel


class PgClientRepository(ClientRepository):
    """Postgres-backed repository for Client entities.

    Receives an ``AsyncSession`` via constructor injection; session lifecycle
    is managed by the caller (use-case / FastAPI dependency).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # ClientRepository ABC implementation
    # ------------------------------------------------------------------

    async def get_by_id(self, id: UUID) -> Client | None:
        """Return the Client with the given ID, or None if not found."""
        stmt = select(ClientProfileModel).where(ClientProfileModel.id == id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def get_by_user_id(self, user_id: UUID) -> Client | None:
        """Return the Client associated with the given user ID, or None."""
        stmt = select(ClientProfileModel).where(ClientProfileModel.user_id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_entity(self, model: ClientProfileModel) -> Client:
        """Convert a ``ClientProfileModel`` row to a pure ``Client`` domain entity."""
        return Client(
            id=model.id,
            user_id=model.user_id,
            created_at=model.created_at,
            preferred_staff_id=model.preferred_staff_id,
            blocked_staff_ids=frozenset(model.blocked_staff_ids or []),
            notes=model.notes,
        )

    def _to_model(self, entity: Client) -> ClientProfileModel:
        """Convert a pure ``Client`` domain entity to a ``ClientProfileModel`` row."""
        return ClientProfileModel(
            id=entity.id,
            user_id=entity.user_id,
            created_at=entity.created_at,
            preferred_staff_id=entity.preferred_staff_id,
            blocked_staff_ids=list(entity.blocked_staff_ids),
            notes=entity.notes,
        )
