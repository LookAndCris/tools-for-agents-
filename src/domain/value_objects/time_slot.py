"""TimeSlot value object — immutable UTC-aware time window."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.exceptions import InvalidTimeSlotError


@dataclass(frozen=True)
class TimeSlot:
    """An immutable, UTC-aware time window with start (inclusive) and end (exclusive)."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise InvalidTimeSlotError("TimeSlot datetimes must be timezone-aware (UTC).")
        if self.start >= self.end:
            raise InvalidTimeSlotError(
                f"TimeSlot start ({self.start}) must be strictly before end ({self.end})."
            )

    def overlaps(self, other: "TimeSlot") -> bool:
        """Return True if this slot overlaps with other (touching boundaries do NOT overlap)."""
        return self.start < other.end and self.end > other.start

    def contains(self, other: "TimeSlot") -> bool:
        """Return True if this slot fully contains the other slot."""
        return self.start <= other.start and self.end >= other.end

    def duration_minutes(self) -> int:
        """Return the duration in whole minutes."""
        return int((self.end - self.start).total_seconds() // 60)
