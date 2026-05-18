"""Tool primitives.

Tools are thin orchestrators that call services. They never talk to providers
or repositories directly. Every tool returns a typed :class:`ToolResult` so
the agent can record a deterministic trace.

Conventions:
- Tool names are stable identifiers (e.g. ``"rag.answer"``).
- ``input_summary`` and ``output_summary`` are short, human-readable strings
  used for tracing / observability; they must not contain PII or secrets.
- Tools that may produce external actions (e.g. send_email) set
  ``approval_required=True`` and provide a ``proposed_payload``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from onepilot.core.config import Settings
from onepilot.security.auth import Principal


@dataclass(slots=True)
class ToolContext:
    session: Session
    principal: Principal
    settings: Settings


@dataclass(slots=True)
class ToolResult:
    tool_name: str
    input_summary: str
    output_summary: str
    output: Any
    duration_ms: int = 0
    approval_required: bool = False
    approval_action_type: str | None = None
    approval_title: str | None = None
    approval_payload: dict | None = None
    approval_risk: str = "medium"
    safety_flags: list[str] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)


class Tool(ABC):
    name: str = "tool"
    description: str = ""

    @abstractmethod
    def run(self, ctx: ToolContext, **kwargs: Any) -> ToolResult: ...
