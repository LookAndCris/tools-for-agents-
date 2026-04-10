"""WaitlistStatus — lifecycle states for a WaitlistEntry."""
from __future__ import annotations

from enum import Enum


class WaitlistStatus(str, Enum):
    """Lifecycle states for a WaitlistEntry."""

    PENDING = "pending"
    NOTIFIED = "notified"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
