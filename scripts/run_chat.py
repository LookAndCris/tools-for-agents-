"""Standalone terminal chat loop for the tools-for-agents booking assistant.

Connects the chat_tools registry to the OpenAI API so you can interact with
the booking system from the command line.

Usage::

    # With default anonymous admin context (no real user in DB needed)
    python scripts/run_chat.py

    # With a specific user UUID (must exist in the DB)
    python scripts/run_chat.py --user-id <uuid> --role client --client-id <uuid>

    # Specify a different OpenAI model
    python scripts/run_chat.py --model gpt-4o

Exit with Ctrl-C or by typing "exit" / "salir".

Environment variables (loaded from .env automatically)::

    OPENAI_API_KEY   — required
    DATABASE_URL     — required (default: postgresql+asyncpg://postgres:postgres@localhost:5432/tools_for_agents)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

# ---------------------------------------------------------------------------
# Path bootstrapping — allow running as `python scripts/run_chat.py` from
# the project root without installing the package.
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC = _PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Load .env before importing settings-dependent modules
try:
    from dotenv import load_dotenv  # type: ignore[import]

    load_dotenv(_PROJECT_ROOT / ".env")
except ImportError:
    # python-dotenv not installed — rely on environment variables being set
    pass

# ---------------------------------------------------------------------------
# Application imports (after path/env bootstrap)
# ---------------------------------------------------------------------------

from openai import AsyncOpenAI  # noqa: E402 (import after path setup)

from infrastructure.config import settings  # noqa: E402
from infrastructure.database.session import async_session_factory  # noqa: E402
from interfaces.chat_tools import AgentContext, registry  # noqa: E402  (triggers setup.py)
from interfaces.chat_tools.executor import ToolExecutor  # noqa: E402

# ---------------------------------------------------------------------------
# Session factory fix — async_sessionmaker.__call__ is synchronous (returns
# an AsyncSession directly, not a coroutine).  ToolExecutor calls
# ``await self._session_factory()``, so the factory must be an *async*
# callable.  Wrap async_session_factory in a coroutine function and replace
# the executor injected by setup.py so each tool call gets a fresh session.
# ---------------------------------------------------------------------------


async def _make_session():  # type: ignore[return]
    """Async session factory: creates a new AsyncSession per tool invocation."""
    return async_session_factory()


registry._executor = ToolExecutor(session_factory=_make_session)  # type: ignore[union-attr]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "Eres un asistente de agendamiento de citas. "
    "Ayudas a los clientes a buscar servicios disponibles, encontrar horarios libres, "
    "y agendar, reagendar o cancelar citas. "
    "Usa las herramientas disponibles para consultar y modificar la agenda. "
    "Sé amable, conciso y proactivo. "
    "Si necesitas datos que el usuario no proporcionó (como el ID de un servicio o staff), "
    "primero usa la herramienta adecuada para buscarlos y luego procede con la acción."
)

DEFAULT_MODEL = "gpt-4o-mini"
EXIT_COMMANDS = {"exit", "salir", "quit", "q"}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Terminal chat loop for the tools-for-agents booking assistant.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--user-id",
        default="00000000-0000-0000-0000-000000000001",
        help=(
            "UUID of the authenticated user context. "
            "Use any UUID if running without a real DB user (default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--role",
        default="admin",
        choices=["admin", "staff", "client"],
        help="Role to use for the agent context (default: %(default)s).",
    )
    parser.add_argument(
        "--staff-id",
        default=None,
        help="UUID of the linked staff profile (required when role=staff).",
    )
    parser.add_argument(
        "--client-id",
        default=None,
        help="UUID of the linked client profile (required when role=client).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use (default: %(default)s).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Tool call execution
# ---------------------------------------------------------------------------


async def _execute_tool_calls(
    tool_calls: list[Any],
    ctx: AgentContext,
) -> list[dict[str, Any]]:
    """Execute all tool calls returned by OpenAI and collect results.

    Args:
        tool_calls: The ``tool_calls`` list from the OpenAI response message.
        ctx: The agent context for authentication.

    Returns:
        A list of OpenAI tool-result message dicts ready to append to
        the conversation ``messages`` list.
    """
    results: list[dict[str, Any]] = []

    for tc in tool_calls:
        tool_name = tc.function.name
        try:
            args: dict[str, Any] = json.loads(tc.function.arguments)
        except json.JSONDecodeError as exc:
            args = {}
            print(f"  [!] Failed to parse arguments for {tool_name}: {exc}", file=sys.stderr)

        print(f"  → {tool_name}({_truncate_repr(args)})", flush=True)

        result = await registry.execute(tool_name, args, ctx)

        # Serialize result to a JSON string for the tool message
        content = json.dumps(result, default=_json_fallback, ensure_ascii=False)

        results.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": content,
            }
        )

    return results


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _json_fallback(obj: Any) -> Any:
    """Fallback serializer for objects that are not JSON-serializable by default."""
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return str(obj)


def _truncate_repr(obj: Any, max_len: int = 120) -> str:
    """Return a short string representation for display purposes."""
    s = repr(obj)
    return s if len(s) <= max_len else s[:max_len] + "…"


# ---------------------------------------------------------------------------
# Main conversation loop
# ---------------------------------------------------------------------------


async def chat_loop(args: argparse.Namespace) -> None:
    """Run the interactive conversation loop."""
    # ------------------------------------------------------------------
    # Validate API key
    # ------------------------------------------------------------------
    api_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print(
            "Error: OPENAI_API_KEY is not set.\n"
            "Add it to your .env file or export it as an environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # Build agent context
    # ------------------------------------------------------------------
    try:
        user_id = UUID(args.user_id)
    except ValueError:
        print(f"Error: --user-id '{args.user_id}' is not a valid UUID.", file=sys.stderr)
        sys.exit(1)

    staff_id: UUID | None = None
    if args.staff_id:
        try:
            staff_id = UUID(args.staff_id)
        except ValueError:
            print(f"Error: --staff-id '{args.staff_id}' is not a valid UUID.", file=sys.stderr)
            sys.exit(1)

    client_id: UUID | None = None
    if args.client_id:
        try:
            client_id = UUID(args.client_id)
        except ValueError:
            print(f"Error: --client-id '{args.client_id}' is not a valid UUID.", file=sys.stderr)
            sys.exit(1)

    ctx = AgentContext(
        user_id=user_id,
        role=args.role,
        staff_id=staff_id,
        client_id=client_id,
    )

    # ------------------------------------------------------------------
    # OpenAI client and tool schemas
    # ------------------------------------------------------------------
    client = AsyncOpenAI(api_key=api_key)
    tools = registry.get_openai_schemas()

    # ------------------------------------------------------------------
    # Print banner
    # ------------------------------------------------------------------
    tool_count = len(tools)
    print("─" * 60)
    print("  Booking Assistant — tools-for-agents")
    print(f"  Model : {args.model}")
    print(f"  Tools : {tool_count} registered")
    print(f"  Role  : {ctx.role}  |  user_id: {ctx.user_id}")
    print("─" * 60)
    print("Type your message and press Enter. Type 'exit' to quit.\n")

    # ------------------------------------------------------------------
    # Conversation state
    # ------------------------------------------------------------------
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    while True:
        # -- User input --
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue

        if user_input.lower() in EXIT_COMMANDS:
            print("Bye!")
            break

        messages.append({"role": "user", "content": user_input})

        # -- Agentic tool-call loop --
        while True:
            try:
                response = await client.chat.completions.create(
                    model=args.model,
                    messages=messages,  # type: ignore[arg-type]
                    tools=tools,  # type: ignore[arg-type]
                    tool_choice="auto",
                )
            except Exception as exc:  # noqa: BLE001
                print(f"\n[OpenAI error] {exc}\n", file=sys.stderr)
                # Remove the last user message so the conversation stays clean
                messages.pop()
                break

            choice = response.choices[0]
            msg = choice.message

            # Append the assistant message to history (including any tool_calls)
            assistant_message: dict[str, Any] = {"role": "assistant"}
            if msg.content:
                assistant_message["content"] = msg.content
            if msg.tool_calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            messages.append(assistant_message)

            # If there are no tool calls, the assistant has finished responding
            if not msg.tool_calls:
                # Print the final assistant response
                reply = msg.content or ""
                print(f"\nAssistant: {reply}\n")
                break

            # Execute tool calls and feed results back
            print("\n[Calling tools…]")
            tool_results = await _execute_tool_calls(msg.tool_calls, ctx)
            messages.extend(tool_results)
            # Loop back to get the next assistant response after tool results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments and run the async chat loop."""
    args = _parse_args()
    try:
        asyncio.run(chat_loop(args))
    except KeyboardInterrupt:
        print("\nInterrupted. Bye!")


if __name__ == "__main__":
    main()
