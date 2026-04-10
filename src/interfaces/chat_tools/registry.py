"""ToolRegistry — central registry for LLM chat tools.

Provides:
- ``ToolDef``: NamedTuple describing a registered tool.
- ``@tool()`` decorator: registers an async handler into a ``ToolRegistry``.
- ``ToolRegistry``: stores tools, generates OpenAI-compatible schemas,
  and dispatches ``execute()`` calls.

Design decisions:
- Framework-agnostic: no FastAPI/HTTP dependencies.
- Schema export via Pydantic V2 ``model_json_schema()``.
- Auth is explicit: ``execute()`` requires an ``AgentContext``.
- The ``@tool`` decorator infers the input model from the second positional
  type-hint of the handler (``async def fn(ctx: AgentContext, inp: InputModel)``).
- When ``uc_factory`` is provided in ``register()``, the registry uses an
  injected ``ToolExecutor`` to open a session, create the use case, and call
  ``handler(ctx, inp, uc)``.  This is the primary path for all production tools.
  Tools registered without a ``uc_factory`` fall back to the two-arg path
  ``handler(ctx, inp)`` for backward compatibility (test helpers, etc.).
"""
from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Callable, NamedTuple

from pydantic import BaseModel, ValidationError

from interfaces.chat_tools.context import AgentContext

if TYPE_CHECKING:
    from interfaces.chat_tools.executor import ToolExecutor


class ToolDef(NamedTuple):
    """Immutable descriptor for a registered tool."""

    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable  # async (AgentContext, InputModel[, UseCase]) -> Any
    is_mutation: bool
    uc_factory: Callable | None = None  # (AsyncSession) -> UseCase; None = no DI


class ToolRegistry:
    """Central registry that stores tool definitions and dispatches calls.

    Usage::

        executor = ToolExecutor(session_factory=async_session_factory)
        registry = ToolRegistry(executor=executor)

        registry.register(
            name="search_services",
            description="List active services",
            input_model=SearchServicesInput,
            handler=search_services,          # async (ctx, inp, uc) -> Any
            uc_factory=make_list_services_uc, # (AsyncSession) -> ListServicesUseCase
        )

        schemas = registry.get_openai_schemas()
        result  = await registry.execute("search_services", {}, ctx)
    """

    def __init__(self, executor: ToolExecutor | None = None) -> None:
        self._tools: dict[str, ToolDef] = {}
        self._executor = executor

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        description: str,
        input_model: type[BaseModel],
        handler: Callable,
        *,
        is_mutation: bool = False,
        uc_factory: Callable | None = None,
    ) -> None:
        """Register a tool definition.

        Args:
            name: Unique tool identifier used for dispatch.
            description: Human-readable description shown in the schema.
            input_model: Pydantic model class for input validation.
            handler: ``async def handler(ctx, inp[, uc]) -> Any``.
                     When ``uc_factory`` is provided the handler MUST accept a
                     third positional argument ``uc`` (the use case).
            is_mutation: True if the tool modifies state (triggers commit).
            uc_factory: Optional factory ``(AsyncSession) -> UseCase`` used
                        to create the use case for this tool.  When set, the
                        registry delegates execution to the ``ToolExecutor``
                        so that each call gets a fresh session and properly
                        wired use case.  Required for all production tools.
        """
        self._tools[name] = ToolDef(
            name=name,
            description=description,
            input_model=input_model,
            handler=handler,
            is_mutation=is_mutation,
            uc_factory=uc_factory,
        )

    def list_tools(self) -> list[ToolDef]:
        """Return all registered ``ToolDef`` entries."""
        return list(self._tools.values())

    # ------------------------------------------------------------------
    # Schema export
    # ------------------------------------------------------------------

    def get_openai_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible tool schemas for all registered tools.

        Format (per OpenAI ``tools`` array spec)::

            [
                {
                    "type": "function",
                    "function": {
                        "name": "tool_name",
                        "description": "...",
                        "parameters": { <JSON Schema> }
                    }
                },
                ...
            ]
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": td.name,
                    "description": td.description,
                    "parameters": td.input_model.model_json_schema(),
                },
            }
            for td in self._tools.values()
        ]

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def execute(
        self,
        name: str,
        args: dict[str, Any],
        ctx: AgentContext | None,
    ) -> dict[str, Any]:
        """Dispatch a tool call by name.

        When the tool has a ``uc_factory``, execution is delegated to the
        injected ``ToolExecutor`` which opens a fresh ``AsyncSession``, wires
        the use case, calls ``handler(ctx, inp, uc)``, and manages
        commit/rollback.

        When the tool has no ``uc_factory`` (backward-compat / test helpers),
        the registry calls ``handler(ctx, inp)`` directly.

        Args:
            name: The tool name to invoke.
            args: Raw dict of arguments (will be parsed via the input model).
            ctx: Caller context — MUST be a valid ``AgentContext``.

        Returns:
            ``{"result": <return value>}`` on success, or
            ``{"error": {"message": ..., "code": ...}}`` on failure.
        """
        # -- Auth guard (always first — must not open a session for unauthenticated calls) --
        if ctx is None:
            return {"error": {"message": "AgentContext is required", "code": "MISSING_CONTEXT"}}

        # -- Tool lookup --
        td = self._tools.get(name)
        if td is None:
            return {
                "error": {
                    "message": f"Tool '{name}' is not registered",
                    "code": "TOOL_NOT_FOUND",
                }
            }

        # -- Input validation --
        try:
            inp = td.input_model.model_validate(args)
        except ValidationError as exc:
            return {
                "error": {
                    "message": str(exc),
                    "code": "VALIDATION_ERROR",
                }
            }

        # -- Wired path: delegate to ToolExecutor for session + DI lifecycle --
        if td.uc_factory is not None:
            if self._executor is None:
                return {
                    "error": {
                        "message": (
                            f"Tool '{name}' requires a ToolExecutor but none was "
                            "provided to ToolRegistry."
                        ),
                        "code": "INTERNAL_ERROR",
                    }
                }
            return await self._executor.execute_tool(td, ctx, inp)

        # -- Backward-compat path: handler(ctx, inp) with no DI wiring --
        try:
            result = await td.handler(ctx, inp)
            return {"result": result}
        except Exception as exc:  # noqa: BLE001
            return {
                "error": {
                    "message": str(exc),
                    "code": getattr(exc, "code", "INTERNAL_ERROR"),
                }
            }


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def tool(
    name: str,
    description: str,
    *,
    is_mutation: bool = False,
    registry: ToolRegistry,
) -> Callable:
    """Decorator that registers an async handler with the given registry.

    The decorator infers the input Pydantic model from the handler's second
    positional parameter type hint (``inp: SomePydanticModel``).

    Usage::

        @tool("search_services", "Search for services by name", registry=registry)
        async def search_services(ctx: AgentContext, inp: SearchInput) -> list[dict]:
            ...

    Args:
        name: Unique tool name (used for dispatch and in schemas).
        description: Human-readable description for the schema.
        is_mutation: Set to True for tools that write data (triggers commit).
        registry: The ``ToolRegistry`` instance to register with.
    """

    def decorator(fn: Callable) -> Callable:
        sig = inspect.signature(fn)
        params = list(sig.parameters.values())
        # Handler signature: (ctx, inp, ...) — inp is the second param
        if len(params) < 2:
            raise TypeError(
                f"@tool handler '{fn.__name__}' must have at least 2 parameters: "
                "(ctx: AgentContext, inp: BaseModel)"
            )
        inp_param = params[1]
        annotation = inp_param.annotation

        # When `from __future__ import annotations` is active all annotations
        # are stored as strings.  Resolve the string in the function's own
        # globals/locals so that locally-defined models in tests also work.
        if isinstance(annotation, str):
            try:
                annotation = eval(annotation, fn.__globals__)  # noqa: S307
            except Exception:
                annotation = None

        if annotation is None or annotation is inspect.Parameter.empty or not (
            isinstance(annotation, type) and issubclass(annotation, BaseModel)
        ):
            raise TypeError(
                f"@tool handler '{fn.__name__}': second parameter '{inp_param.name}' "
                "must be type-hinted with a Pydantic BaseModel subclass."
            )
        input_model: type[BaseModel] = annotation

        registry.register(
            name=name,
            description=description,
            input_model=input_model,
            handler=fn,
            is_mutation=is_mutation,
        )
        return fn

    return decorator
