"""Unit tests for ToolExecutor (Task 1.2 — RED phase).

Tests:
- Query tool: session is closed, NOT committed
- Mutation tool: session is committed then closed
- Exception path: session is rolled back, error envelope returned
- ApplicationError is mapped to {"error": {"message", "code"}}
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.exceptions import ApplicationError, NotFoundError
from interfaces.chat_tools.context import AgentContext


def _make_ctx() -> AgentContext:
    return AgentContext(user_id=uuid.uuid4(), role="admin")


class TestToolExecutorSessionLifecycle:
    """ToolExecutor manages AsyncSession lifecycle per call."""

    async def test_query_tool_closes_without_commit(self):
        """Query tools (is_mutation=False): session.close() called, commit NOT called."""
        from interfaces.chat_tools.executor import ToolExecutor

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()

        async def fake_handler(session, ctx, args):
            return {"ok": True}

        executor = ToolExecutor(session_factory=AsyncMock(return_value=mock_session))
        result = await executor.run(
            handler=fake_handler,
            ctx=_make_ctx(),
            args={"x": 1},
            is_mutation=False,
        )

        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()
        assert result == {"ok": True}

    async def test_mutation_tool_commits_then_closes(self):
        """Mutation tools (is_mutation=True): commit() then close() are called."""
        from interfaces.chat_tools.executor import ToolExecutor

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()

        call_order: list[str] = []

        async def record_commit():
            call_order.append("commit")

        async def record_close():
            call_order.append("close")

        mock_session.commit.side_effect = record_commit
        mock_session.close.side_effect = record_close

        async def fake_mutation_handler(session, ctx, args):
            return {"created": True}

        executor = ToolExecutor(session_factory=AsyncMock(return_value=mock_session))
        result = await executor.run(
            handler=fake_mutation_handler,
            ctx=_make_ctx(),
            args={},
            is_mutation=True,
        )

        assert call_order == ["commit", "close"]
        assert result == {"created": True}

    async def test_exception_triggers_rollback(self):
        """When handler raises, rollback() is called and session is closed."""
        from interfaces.chat_tools.executor import ToolExecutor

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()

        async def failing_handler(session, ctx, args):
            raise RuntimeError("unexpected")

        executor = ToolExecutor(session_factory=AsyncMock(return_value=mock_session))
        result = await executor.run(
            handler=failing_handler,
            ctx=_make_ctx(),
            args={},
            is_mutation=True,
        )

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()
        assert "error" in result

    async def test_rollback_on_query_exception(self):
        """Even query tools roll back on exception."""
        from interfaces.chat_tools.executor import ToolExecutor

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()

        async def failing_query_handler(session, ctx, args):
            raise ValueError("query blew up")

        executor = ToolExecutor(session_factory=AsyncMock(return_value=mock_session))
        result = await executor.run(
            handler=failing_query_handler,
            ctx=_make_ctx(),
            args={},
            is_mutation=False,
        )

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
        assert "error" in result


class TestToolExecutorErrorEnvelope:
    """ApplicationError is mapped to the standard error envelope."""

    async def test_application_error_mapped_to_envelope(self):
        """ApplicationError → {'error': {'message': ..., 'code': ...}}."""
        from interfaces.chat_tools.executor import ToolExecutor

        mock_session = AsyncMock()

        async def app_error_handler(session, ctx, args):
            raise ApplicationError("Something went wrong", "SOME_CODE")

        executor = ToolExecutor(session_factory=AsyncMock(return_value=mock_session))
        result = await executor.run(
            handler=app_error_handler,
            ctx=_make_ctx(),
            args={},
            is_mutation=False,
        )

        assert result == {"error": {"message": "Something went wrong", "code": "SOME_CODE"}}

    async def test_not_found_error_mapped(self):
        """NotFoundError (ApplicationError subclass) maps to the error envelope."""
        from interfaces.chat_tools.executor import ToolExecutor

        mock_session = AsyncMock()
        svc_id = uuid.uuid4()

        async def not_found_handler(session, ctx, args):
            raise NotFoundError("Service", svc_id)

        executor = ToolExecutor(session_factory=AsyncMock(return_value=mock_session))
        result = await executor.run(
            handler=not_found_handler,
            ctx=_make_ctx(),
            args={},
            is_mutation=False,
        )

        assert "error" in result
        assert result["error"]["code"] == "SERVICE_NOT_FOUND"
        assert str(svc_id) in result["error"]["message"]

    async def test_generic_exception_wrapped(self):
        """Non-ApplicationError exceptions are wrapped in a generic error envelope."""
        from interfaces.chat_tools.executor import ToolExecutor

        mock_session = AsyncMock()

        async def boom_handler(session, ctx, args):
            raise RuntimeError("boom")

        executor = ToolExecutor(session_factory=AsyncMock(return_value=mock_session))
        result = await executor.run(
            handler=boom_handler,
            ctx=_make_ctx(),
            args={},
            is_mutation=False,
        )

        assert "error" in result
        assert "code" in result["error"]
        assert "message" in result["error"]
