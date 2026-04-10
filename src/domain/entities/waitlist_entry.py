"""WaitlistEntry domain entity."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from domain.exceptions import InvalidStatusTransitionError
from domain.value_objects.waitlist_status import WaitlistStatus


class WaitlistEntry:
    """Domain entity representing a client's position on a service waitlist.

    Invariant: only PENDING entries can be notified.
    """

    def __init__(
        self,
        id: UUID,
        client_id: UUID,
        service_id: UUID,
        preferred_staff_id: UUID | None = None,
        preferred_start: datetime | None = None,
        preferred_end: datetime | None = None,
        status: WaitlistStatus = WaitlistStatus.PENDING,
        created_at: datetime | None = None,
        notes: str | None = None,
    ) -> None:
        self.id = id
        self.client_id = client_id
        self.service_id = service_id
        self.preferred_staff_id = preferred_staff_id
        self.preferred_start = preferred_start
        self.preferred_end = preferred_end
        self.status = status
        self.created_at = created_at if created_at is not None else datetime.now(timezone.utc)
        self.notes = notes

    def notify(self) -> None:
        """Transition status from PENDING to NOTIFIED.

        Raises:
            InvalidStatusTransitionError: if status is not PENDING.
        """
        if self.status != WaitlistStatus.PENDING:
            raise InvalidStatusTransitionError(
                f"Cannot notify a waitlist entry with status '{self.status.value}'. "
                "Only PENDING entries can be notified."
            )
        self.status = WaitlistStatus.NOTIFIED

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"WaitlistEntry(id={self.id}, client_id={self.client_id}, "
            f"service_id={self.service_id}, status={self.status.value})"
        )
