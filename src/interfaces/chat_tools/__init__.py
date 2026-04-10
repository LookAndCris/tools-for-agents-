"""Chat tools interface package.

Framework-agnostic LLM tool registry for the tools-for-agents booking system.

Quick start::

    from interfaces.chat_tools import registry, AgentContext

    # Get OpenAI-compatible schemas for all 12 tools
    schemas = registry.get_openai_schemas()

    # Execute a tool (session opened and closed per call automatically)
    ctx = AgentContext(user_id=..., role="admin")
    result = await registry.execute("search_services", {}, ctx)
"""
from __future__ import annotations

from interfaces.chat_tools.context import AgentContext
from interfaces.chat_tools.registry import ToolRegistry

# Import setup module to trigger tool registration
import interfaces.chat_tools.setup as _setup  # noqa: F401

# Expose the pre-populated global registry
registry: ToolRegistry = _setup.registry


def tools_list() -> list[dict]:
    """Return OpenAI-compatible JSON schemas for all registered tools.

    Convenience alias for ``registry.get_openai_schemas()``.
    """
    return registry.get_openai_schemas()


__all__ = ["AgentContext", "ToolRegistry", "registry", "tools_list"]
