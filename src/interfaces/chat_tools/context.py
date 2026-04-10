"""AgentContext — immutable caller identity for chat tool execution.

Mirrors ``UserContext`` from the application layer but lives in the
interfaces layer so the chat-tools module has no upward dependency on
application internals beyond what it already uses.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from application.dto.user_context import UserContext


@dataclass(frozen=True)
class AgentContext:
    """Immutable caller identity passed to every tool invocation.

    Analogous to ``UserContext`` used by HTTP endpoints but decoupled from
    the FastAPI request lifecycle.  The ``AgentContext`` must be created by the
    caller (e.g. an LLM orchestration loop) and passed explicitly to every
    tool call so that authentication is always explicit and auditable.

    Attributes:
        user_id: UUID of the authenticated user.
        role: Caller's role — one of "admin", "staff", or "client".
        staff_id: UUID of the linked staff record, if the caller is staff/admin.
        client_id: UUID of the linked client record, if the caller is a client.
    """

    user_id: UUID
    role: str  # "admin" | "staff" | "client"
    staff_id: UUID | None = None
    client_id: UUID | None = None

    @classmethod
    def from_user_context(cls, uc: UserContext) -> "AgentContext":
        """Build an ``AgentContext`` from a ``UserContext``.

        Convenience factory so that existing HTTP-layer context objects can be
        bridged into the chat-tools layer without manual field mapping.

        Args:
            uc: A ``UserContext`` produced by the API authentication layer.

        Returns:
            A new frozen ``AgentContext`` with the same identity fields.
        """
        return cls(
            user_id=uc.user_id,
            role=uc.role,
            staff_id=uc.staff_id,
            client_id=uc.client_id,
        )
