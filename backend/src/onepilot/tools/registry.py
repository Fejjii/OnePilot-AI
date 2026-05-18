"""Lightweight tool registry.

Agents look up tools by name and call ``run``. The registry is a module-level
singleton populated at import time by :mod:`onepilot.tools`. This keeps the
agent layer decoupled from concrete tool implementations.
"""

from __future__ import annotations

from collections.abc import Iterator

from onepilot.core.errors import NotFoundError
from onepilot.tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        tool = self._tools.get(name)
        if tool is None:
            raise NotFoundError(f"Tool '{name}' is not registered")
        return tool

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return sorted(self._tools.keys())

    def __iter__(self) -> Iterator[Tool]:
        return iter(self._tools.values())


registry = ToolRegistry()
