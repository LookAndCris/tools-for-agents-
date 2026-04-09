"""PolicyResult — immutable result of a domain policy evaluation."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PolicyResult:
    """
    Result of a domain policy check.

    Use the class methods ok() and fail() to construct instances.
    """

    is_ok: bool
    violations: list[str] = field(default_factory=list)

    @classmethod
    def ok(cls) -> "PolicyResult":
        """Return a passing policy result with no violations."""
        return cls(is_ok=True, violations=[])

    @classmethod
    def fail(cls, *reasons: str) -> "PolicyResult":
        """Return a failing policy result with the given violation messages."""
        return cls(is_ok=False, violations=list(reasons))
