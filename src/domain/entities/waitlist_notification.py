"""WaitlistNotification domain entity — audit record for waitlist notifications."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID


class WaitlistNotification:
    """Lightweight audit record created when a waitlist entry is notified.

    Records when the notification happened and optionally links to the
    appointment that was opened.
    """

    def __init__(
        self,
        id: UUID,
        waitlist_entry_id: UUID,
        appointment_id: UUID | None = None,
        notified_at: datetime | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.waitlist_entry_id = waitlist_entry_id
        self.appointment_id = appointment_id
        self.notified_at = notified_at if notified_at is not None else datetime.now(timezone.utc)
        self.expires_at = expires_at

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"WaitlistNotification(id={self.id}, "
            f"waitlist_entry_id={self.waitlist_entry_id}, "
            f"notified_at={self.notified_at})"
        )
