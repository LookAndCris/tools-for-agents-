"""ToolExecutor — owns the AsyncSession lifecycle for every tool call.

Each tool invocation gets a fresh ``AsyncSession`` created by the session
factory.  The executor:

1. Opens the session.
2. Creates the use case via ``tool_def.uc_factory(session)`` (for the primary
   wired path used by all production tools).
3. Calls ``handler(ctx, inp, uc)``.
4. On success: ``commit()`` if ``is_mutation=True``, else just ``close()``.
5. On any exception: ``rollback()`` then ``close()``, returns an error envelope.

The error envelope format mirrors the REST API:
``{"error": {"message": "...", "code": "..."}}``.

``ApplicationError`` subclasses are mapped to their ``message`` and ``code``
attributes.  All other exceptions produce ``code="INTERNAL_ERROR"``.

There are two entry points:

* ``execute_tool(tool_def, ctx, inp)`` — primary path used by
  ``ToolRegistry.execute()`` for tools with a ``uc_factory``.
  Opens session, wires use case, calls ``handler(ctx, inp, uc)``.

* ``run(handler, ctx, args, *, is_mutation)`` — lower-level path kept for
  backward compatibility and direct testing.
  Calls ``handler(session, ctx, args)`` (legacy three-arg convention).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from application.exceptions import ApplicationError
from interfaces.chat_tools.context import AgentContext

if TYPE_CHECKING:
    from interfaces.chat_tools.registry import ToolDef


class ToolExecutor:
    """Manages the per-invocation session lifecycle for a tool handler.

    Args:
        session_factory: An async callable that returns an ``AsyncSession``.
            Typically ``infrastructure.database.session.async_session_factory``.

    Usage::

        executor = ToolExecutor(session_factory=async_session_factory)

        # Primary wired path (used by ToolRegistry):
        result = await executor.execute_tool(tool_def, ctx, inp)

        # Legacy path (for direct use / backward-compat):
        result = await executor.run(
            handler=my_handler,
            ctx=agent_context,
            args={"key": "value"},
            is_mutation=False,
        )
    """

    def __init__(self, session_factory: Callable) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Primary path — used by ToolRegistry.execute() for wired tools
    # ------------------------------------------------------------------

    async def execute_tool(
        self,
        tool_def: ToolDef,
        ctx: AgentContext,
        inp: Any,
    ) -> dict[str, Any]:
        """Execute a tool with a managed session and use-case dependency.

        This is the primary entry point called by ``ToolRegistry.execute()``
        for tools that have a ``uc_factory``.

        Args:
            tool_def: The ``ToolDef`` for the tool to execute.
            ctx: Caller identity context.
            inp: The already-validated Pydantic input model instance.

        Returns:
            ``{"result": <return_value>}`` on success, or
            ``{"error": {"message": ..., "code": ...}}`` on failure.

        Session lifecycle:
            - Session opened at start.
            - ``commit()`` on success if ``tool_def.is_mutation`` is True.
            - ``rollback()`` on any exception.
            - ``close()`` always (via ``finally``).
        """
        session = await self._session_factory()
        try:
            uc = tool_def.uc_factory(session)  # type: ignore[misc]
            result = await tool_def.handler(ctx, inp, uc)
            if tool_def.is_mutation:
                await session.commit()
            return {"result": result}
        except ApplicationError as exc:
            await session.rollback()
            return {"error": {"message": exc.message, "code": exc.code}}
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            return {
                "error": {
                    "message": str(exc),
                    "code": "INTERNAL_ERROR",
                }
            }
        finally:
            await session.close()

    # ------------------------------------------------------------------
    # Legacy path — backward compat; handler signature: (session, ctx, args)
    # ------------------------------------------------------------------

    async def run(
        self,
        handler: Callable,
        ctx: AgentContext,
        args: dict[str, Any],
        *,
        is_mutation: bool,
    ) -> dict[str, Any]:
        """Execute *handler* inside a managed session.

        Legacy entry point where the handler receives the raw session and args
        dict directly: ``async def handler(session, ctx, args) -> Any``.

        Args:
            handler: ``async def handler(session, ctx, args) -> Any``
            ctx: Caller context.
            args: Raw argument dict passed directly to the handler.
            is_mutation: If True, commit on success; otherwise just close.

        Returns:
            The raw return value of the handler (not wrapped) on success, or
            ``{"error": {"message": ..., "code": ...}}`` on failure.

        Note:
            Unlike ``execute_tool()``, this method returns the handler's raw
            return value (not wrapped in ``{"result": ...}``).  The caller is
            responsible for wrapping if needed.
        """
        session = await self._session_factory()
        try:
            result = await handler(session, ctx, args)
            if is_mutation:
                await session.commit()
            return result
        except ApplicationError as exc:
            await session.rollback()
            return {"error": {"message": exc.message, "code": exc.code}}
        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            return {
                "error": {
                    "message": str(exc),
                    "code": "INTERNAL_ERROR",
                }
            }
        finally:
            await session.close()
