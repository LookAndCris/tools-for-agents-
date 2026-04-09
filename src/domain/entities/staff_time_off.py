"""StaffTimeOff domain entity — represents a staff member's time-off block."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from domain.value_objects.time_slot import TimeSlot


@dataclass
class StaffTimeOff:
    """A discrete time-off block for a staff member.

    Attributes:
        id: Unique identifier for this time-off record.
        staff_id: The ID of the staff member this block belongs to.
        time_slot: The UTC-aware time window for the block.
        reason: Optional human-readable reason (e.g. "Annual leave", "Sick").
    """

    id: UUID
    staff_id: UUID
    time_slot: TimeSlot
    reason: str | None = None
