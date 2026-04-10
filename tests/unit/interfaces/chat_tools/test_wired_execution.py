"""Integration-style tests for the wired execution path.

Tests the FULL path: executor → registry → handler(ctx, inp, uc) with mocked
session and mocked use cases.  Verifies CRITICAL 1: that ToolRegistry.execute()
properly uses ToolExecutor to open a session, wire the use case factory, and
call the handler with all three required arguments.

NOTE: No `from __future__ import annotations` — see test_registry.py.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from pydantic import BaseModel

from interfaces.chat_tools.context import AgentContext
from interfaces.chat_tools.registry import ToolRegistry
from interfaces.chat_tools.executor import ToolExecutor


def _ctx(**kwargs) -> AgentContext:
    defaults = {"user_id": uuid.uuid4(), "role": "admin"}
    defaults.update(kwargs)
    return AgentContext(**defaults)


# ---------------------------------------------------------------------------
# Tests: AgentContext.from_user_context() (WARNING coverage gap)
# ---------------------------------------------------------------------------


class TestAgentContextBridge:
    """AgentContext.from_user_context() maps UserContext fields correctly."""

    def test_from_user_context_maps_all_fields(self):
        """from_user_context copies user_id, role, staff_id, client_id."""
        from application.dto.user_context import UserContext

        staff_id = uuid.uuid4()
        uc = UserContext(
            user_id=uuid.uuid4(),
            role="staff",
            staff_id=staff_id,
            client_id=None,
        )
        agent_ctx = AgentContext.from_user_context(uc)

        assert agent_ctx.user_id == uc.user_id
        assert agent_ctx.role == uc.role
        assert agent_ctx.staff_id == uc.staff_id
        assert agent_ctx.client_id is None

    def test_from_user_context_client(self):
        """from_user_context works for a client user."""
        from application.dto.user_context import UserContext

        client_id = uuid.uuid4()
        uc = UserContext(
            user_id=uuid.uuid4(),
            role="client",
            staff_id=None,
            client_id=client_id,
        )
        agent_ctx = AgentContext.from_user_context(uc)

        assert agent_ctx.role == "client"
        assert agent_ctx.client_id == client_id
        assert agent_ctx.staff_id is None

    def test_agent_context_is_immutable(self):
        """AgentContext is a frozen dataclass — mutation raises FrozenInstanceError."""
        from dataclasses import FrozenInstanceError

        ctx = AgentContext(user_id=uuid.uuid4(), role="admin")
        with pytest.raises(FrozenInstanceError):
            ctx.role = "client"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: Wired path — registry.execute() goes through ToolExecutor
# ---------------------------------------------------------------------------


class TestWiredRegistryExecution:
    """ToolRegistry.execute() wires session + use case and calls handler(ctx, inp, uc)."""

    async def test_execute_calls_handler_with_use_case(self):
        """The wired path calls handler(ctx, inp, uc) — not handler(ctx, inp)."""
        received_args: list = []

        class EchoInput(BaseModel):
            message: str

        class FakeUC:
            pass

        async def echo_handler(ctx: AgentContext, inp: EchoInput, uc: FakeUC) -> dict:
            received_args.append((ctx, inp, uc))
            return {"echo": inp.message}

        mock_session = AsyncMock()
        mock_session_factory = AsyncMock(return_value=mock_session)
        fake_uc = FakeUC()
        uc_factory = MagicMock(return_value=fake_uc)

        executor = ToolExecutor(session_factory=mock_session_factory)
        registry = ToolRegistry(executor=executor)
        registry.register(
            name="echo",
            description="Echo a message",
            input_model=EchoInput,
            handler=echo_handler,
            uc_factory=uc_factory,
            is_mutation=False,
        )

        ctx = _ctx()
        result = await registry.execute("echo", {"message": "hello"}, ctx)

        assert result == {"result": {"echo": "hello"}}
        assert len(received_args) == 1
        assert received_args[0][0] is ctx
        assert received_args[0][1].message == "hello"
        assert received_args[0][2] is fake_uc

    async def test_execute_passes_session_to_uc_factory(self):
        """The session opened by the executor is passed to the uc_factory."""
        factory_sessions: list = []

        class NoInput(BaseModel):
            pass

        class FakeUC:
            pass

        async def noop_handler(ctx: AgentContext, inp: NoInput, uc: FakeUC) -> dict:
            return {}

        mock_session = AsyncMock()
        mock_session_factory = AsyncMock(return_value=mock_session)

        def capturing_factory(session):
            factory_sessions.append(session)
            return FakeUC()

        executor = ToolExecutor(session_factory=mock_session_factory)
        registry = ToolRegistry(executor=executor)
        registry.register(
            name="noop",
            description="No-op",
            input_model=NoInput,
            handler=noop_handler,
            uc_factory=capturing_factory,
            is_mutation=False,
        )

        await registry.execute("noop", {}, _ctx())

        assert len(factory_sessions) == 1
        assert factory_sessions[0] is mock_session

    async def test_mutation_tool_commits_session(self):
        """Mutation tools cause session.commit() to be called after handler."""

        class MutInput(BaseModel):
            value: str

        class FakeUC:
            pass

        async def mut_handler(ctx: AgentContext, inp: MutInput, uc: FakeUC) -> dict:
            return {"created": True}

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session_factory = AsyncMock(return_value=mock_session)

        executor = ToolExecutor(session_factory=mock_session_factory)
        registry = ToolRegistry(executor=executor)
        registry.register(
            name="create_thing",
            description="Create something",
            input_model=MutInput,
            handler=mut_handler,
            uc_factory=MagicMock(return_value=FakeUC()),
            is_mutation=True,
        )

        result = await registry.execute("create_thing", {"value": "x"}, _ctx())

        assert result == {"result": {"created": True}}
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    async def test_query_tool_does_not_commit_session(self):
        """Query tools (is_mutation=False) must NOT call session.commit()."""

        class QInput(BaseModel):
            q: str

        class FakeUC:
            pass

        async def query_handler(ctx: AgentContext, inp: QInput, uc: FakeUC) -> list:
            return []

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session_factory = AsyncMock(return_value=mock_session)

        executor = ToolExecutor(session_factory=mock_session_factory)
        registry = ToolRegistry(executor=executor)
        registry.register(
            name="search",
            description="Search",
            input_model=QInput,
            handler=query_handler,
            uc_factory=MagicMock(return_value=FakeUC()),
            is_mutation=False,
        )

        result = await registry.execute("search", {"q": "test"}, _ctx())

        assert result == {"result": []}
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()

    async def test_handler_exception_triggers_rollback(self):
        """When handler raises, rollback is called and an error envelope is returned."""
        from application.exceptions import ApplicationError

        class FInput(BaseModel):
            pass

        class FakeUC:
            pass

        async def failing_handler(ctx: AgentContext, inp: FInput, uc: FakeUC) -> dict:
            raise ApplicationError("Not allowed", "FORBIDDEN")

        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session_factory = AsyncMock(return_value=mock_session)

        executor = ToolExecutor(session_factory=mock_session_factory)
        registry = ToolRegistry(executor=executor)
        registry.register(
            name="failing",
            description="Fails",
            input_model=FInput,
            handler=failing_handler,
            uc_factory=MagicMock(return_value=FakeUC()),
            is_mutation=True,
        )

        result = await registry.execute("failing", {}, _ctx())

        assert "error" in result
        assert result["error"]["message"] == "Not allowed"
        assert result["error"]["code"] == "FORBIDDEN"
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    async def test_missing_context_still_rejected(self):
        """None context must still return MISSING_CONTEXT error (no session opened)."""

        class AInput(BaseModel):
            v: str

        class FakeUC:
            pass

        async def handler(ctx: AgentContext, inp: AInput, uc: FakeUC) -> dict:
            return {}

        mock_session_factory = AsyncMock()
        executor = ToolExecutor(session_factory=mock_session_factory)
        registry = ToolRegistry(executor=executor)
        registry.register(
            name="auth_tool",
            description="Auth required",
            input_model=AInput,
            handler=handler,
            uc_factory=MagicMock(return_value=FakeUC()),
        )

        result = await registry.execute("auth_tool", {"v": "x"}, None)  # type: ignore[arg-type]
        assert "error" in result
        assert result["error"]["code"] == "MISSING_CONTEXT"
        # Session factory must NOT be called before context check
        mock_session_factory.assert_not_called()

    async def test_backward_compat_no_uc_factory(self):
        """Tools registered without uc_factory still work (handler(ctx, inp) path).

        This preserves the existing behaviour used in unit test helpers and
        synthetic handlers that do not need DI wiring.
        """

        class BInput(BaseModel):
            x: int

        executor = ToolExecutor(session_factory=AsyncMock())
        registry = ToolRegistry(executor=executor)

        # register() without uc_factory → backward-compat two-arg handler
        async def simple_handler(ctx: AgentContext, inp: BInput) -> dict:
            return {"x": inp.x}

        registry.register(
            name="simple_tool",
            description="Simple",
            input_model=BInput,
            handler=simple_handler,
        )

        result = await registry.execute("simple_tool", {"x": 42}, _ctx())
        assert result == {"result": {"x": 42}}
