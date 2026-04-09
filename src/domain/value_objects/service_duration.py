"""ServiceDuration value object — buffer + core duration in minutes."""
from __future__ import annotations

from dataclasses import dataclass

from domain.exceptions import InvalidServiceDurationError


@dataclass(frozen=True)
class ServiceDuration:
    """Immutable service duration including optional setup/cleanup buffers (in minutes)."""

    buffer_before: int
    duration_minutes: int
    buffer_after: int

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise InvalidServiceDurationError(
                f"duration_minutes must be positive (got {self.duration_minutes})."
            )
        if self.buffer_before < 0:
            raise InvalidServiceDurationError(
                f"buffer_before cannot be negative (got {self.buffer_before})."
            )
        if self.buffer_after < 0:
            raise InvalidServiceDurationError(
                f"buffer_after cannot be negative (got {self.buffer_after})."
            )

    @property
    def total(self) -> int:
        """Total slot time needed: buffer_before + duration + buffer_after."""
        return self.buffer_before + self.duration_minutes + self.buffer_after
