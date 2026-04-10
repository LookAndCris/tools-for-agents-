"""PgWaitlistNotificationRepository — PostgreSQL implementation of WaitlistNotificationRepository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.waitlist_notification import WaitlistNotification
from domain.repositories.waitlist_notification_repository import WaitlistNotificationRepository
from infrastructure.database.models.waitlist_notification import WaitlistNotificationModel


class PgWaitlistNotificationRepository(WaitlistNotificationRepository):
    """Postgres-backed repository for WaitlistNotification entities.

    Receives an ``AsyncSession`` via constructor injection; session lifecycle
    is managed by the caller (use-case / FastAPI dependency).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # WaitlistNotificationRepository ABC implementation
    # ------------------------------------------------------------------

    async def save(self, notification: WaitlistNotification) -> WaitlistNotification:
        """Persist a new WaitlistNotification and return it.

        Uses ``session.merge()`` for upsert semantics.
        """
        model = self._to_model(notification)
        await self._session.merge(model)
        await self._session.flush()
        return notification

    async def find_by_waitlist_entry(
        self, waitlist_entry_id: UUID
    ) -> list[WaitlistNotification]:
        """Return all notifications for the given waitlist entry."""
        stmt = select(WaitlistNotificationModel).where(
            WaitlistNotificationModel.waitlist_id == waitlist_entry_id
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _to_entity(self, model: WaitlistNotificationModel) -> WaitlistNotification:
        """Convert a WaitlistNotificationModel to a WaitlistNotification domain entity."""
        return WaitlistNotification(
            id=model.id,
            waitlist_entry_id=model.waitlist_id,
            appointment_id=model.appointment_id,
            notified_at=model.notified_at,
            expires_at=model.expires_at,
        )

    def _to_model(self, entity: WaitlistNotification) -> WaitlistNotificationModel:
        """Convert a WaitlistNotification domain entity to a WaitlistNotificationModel row."""
        return WaitlistNotificationModel(
            id=entity.id,
            waitlist_id=entity.waitlist_entry_id,
            appointment_id=entity.appointment_id,
            notified_at=entity.notified_at,
            expires_at=entity.expires_at,
        )
