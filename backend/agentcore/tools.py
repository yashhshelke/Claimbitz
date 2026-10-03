"""Tool interface for agents.

A "tool" is anything an agent can invoke to get information it doesn't
already have — e.g. a policy database lookup, an ICD-10 validity check, a
duplicate-claim search. Task #4 gives each specialized agent its own small
set of tools; this module defines the shared interface + a simple registry
so that wiring is consistent across agents.

Kept intentionally small: a tool is just an async callable with a name and
description. Nothing here talks to a real database — concrete tools
(backed by Postgres/Pinecone/rule-engines) are added alongside the agents
that need them in task #4, and alongside the DB layer in task #6.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any


class Tool(ABC):
    """Base class for anything an agent can invoke by name."""

    name: str
    description: str

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """Execute the tool and return a JSON-serializable result."""

    def as_schema(self) -> dict[str, str]:
        """Minimal descriptor an agent can include in its LLM prompt."""
        return {"name": self.name, "description": self.description}


class FunctionTool(Tool):
    """Wrap a plain async function as a ``Tool`` without writing a subclass."""

    def __init__(self, name: str, description: str, fn: Callable[..., Awaitable[Any]]) -> None:
        self.name = name
        self.description = description
        self._fn = fn

    async def run(self, **kwargs: Any) -> Any:
        return await self._fn(**kwargs)


class ToolRegistry:
    """A simple name -> Tool lookup, scoped to one agent instance."""

    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools or []:
            self.register(tool)

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            available = ", ".join(sorted(self._tools)) or "<none>"
            raise KeyError(f"No tool named '{name}' registered. Available: {available}") from exc

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def schemas(self) -> list[dict[str, str]]:
        return [tool.as_schema() for tool in self._tools.values()]

    async def run(self, name: str, **kwargs: Any) -> Any:
        return await self.get(name).run(**kwargs)


__all__ = ["Tool", "FunctionTool", "ToolRegistry"]
