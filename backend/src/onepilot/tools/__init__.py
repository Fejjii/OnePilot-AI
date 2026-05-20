"""Tool registry bootstrap.

Importing this module installs the default tool set onto the global
``registry`` singleton. Agents must access tools through the registry — never
import concrete tool classes directly.
"""

from __future__ import annotations

from onepilot.tools.base import Tool, ToolContext, ToolResult
from onepilot.tools.calendar_tool import (
    CalendarCheckAvailabilityTool,
    CalendarCreateEventRequestTool,
    CalendarSuggestSlotsTool,
)
from onepilot.tools.email_tool import EmailDraftTool
from onepilot.tools.general_chat_tool import GeneralChatTool
from onepilot.tools.lead_tool import LeadSupportTool
from onepilot.tools.rag_tool import RAGTool
from onepilot.tools.registry import ToolRegistry, registry
from onepilot.tools.web_search_tool import WebSearchTool


def _bootstrap() -> None:
    for tool in (
        RAGTool(),
        WebSearchTool(),
        EmailDraftTool(),
        CalendarCheckAvailabilityTool(),
        CalendarSuggestSlotsTool(),
        CalendarCreateEventRequestTool(),
        LeadSupportTool(),
        GeneralChatTool(),
    ):
        registry.register(tool)


_bootstrap()


__all__ = [
    "CalendarCheckAvailabilityTool",
    "CalendarCreateEventRequestTool",
    "CalendarSuggestSlotsTool",
    "EmailDraftTool",
    "GeneralChatTool",
    "LeadSupportTool",
    "RAGTool",
    "WebSearchTool",
    "Tool",
    "ToolContext",
    "ToolRegistry",
    "ToolResult",
    "registry",
]
