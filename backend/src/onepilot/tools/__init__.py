"""Tool registry bootstrap.

Importing this module installs the default tool set onto the global
``registry`` singleton. Agents must access tools through the registry — never
import concrete tool classes directly.
"""

from __future__ import annotations

from onepilot.tools.base import Tool, ToolContext, ToolResult
from onepilot.tools.email_tool import EmailDraftTool
from onepilot.tools.general_chat_tool import GeneralChatTool
from onepilot.tools.lead_tool import LeadSupportTool
from onepilot.tools.rag_tool import RAGTool
from onepilot.tools.registry import ToolRegistry, registry


def _bootstrap() -> None:
    for tool in (RAGTool(), EmailDraftTool(), LeadSupportTool(), GeneralChatTool()):
        registry.register(tool)


_bootstrap()


__all__ = [
    "EmailDraftTool",
    "GeneralChatTool",
    "LeadSupportTool",
    "RAGTool",
    "Tool",
    "ToolContext",
    "ToolRegistry",
    "ToolResult",
    "registry",
]
