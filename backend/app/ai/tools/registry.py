"""
Tool Registry — Milestone 10

The Tool Registry is the single source of truth for all registered tools.

Design contract:
  - Tools are registered at module import time (in TOOL_REGISTRY below).
  - The Executor ONLY interacts with tools through this registry.
  - Adding a new tool requires ONLY:
      1. Creating a new tool file under app/ai/tools/.
      2. Importing and adding it to TOOL_REGISTRY below.
      Zero Executor changes required.
  - The registry exposes rich metadata (ToolMeta) for the Developer Panel.

Public API:
  - get_tool(tool_name: ToolName) -> BaseTool
  - list_tools() -> List[ToolMeta]
  - is_registered(tool_name: ToolName) -> bool
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

from app.ai.planner.schemas import ToolName
from app.ai.tools.base import BaseTool, ToolMeta
from app.ai.tools.conversation_memory import ConversationMemoryTool
from app.ai.tools.document_reader import DocumentReaderTool
from app.ai.tools.document_search import DocumentSearchTool
from app.ai.tools.general_llm import GeneralLLMTool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core Registry — Add new tools here. Zero Executor changes needed.
# ---------------------------------------------------------------------------

TOOL_REGISTRY: Dict[ToolName, Type[BaseTool]] = {
    ToolName.DOCUMENT_READER: DocumentReaderTool,
    ToolName.DOCUMENT_SEARCH: DocumentSearchTool,
    ToolName.GENERAL_LLM: GeneralLLMTool,
    ToolName.CONVERSATION_MEMORY: ConversationMemoryTool,
    # Future tools (uncomment when implemented):
    # ToolName.GMAIL: GmailTool,
    # ToolName.GOOGLE_DRIVE: GoogleDriveTool,
    # ToolName.GITHUB: GitHubTool,
    # ToolName.CALENDAR: CalendarTool,
    # ToolName.WEB_SEARCH: WebSearchTool,
    # ToolName.PYTHON_EXECUTOR: PythonExecutorTool,
    # ToolName.PDF_GENERATOR: PDFGeneratorTool,
}


def get_tool(tool_name: ToolName) -> BaseTool:
    """
    Instantiate and return a registered tool.

    Args:
        tool_name: The ToolName enum value.

    Returns:
        A fresh instance of the requested tool.

    Raises:
        KeyError: If the tool is not registered. The Executor catches this
                  and handles it as a fatal step failure.
    """
    tool_cls = TOOL_REGISTRY.get(tool_name)
    if tool_cls is None:
        registered = [t.value for t in TOOL_REGISTRY]
        raise KeyError(
            f"Tool '{tool_name.value}' is not registered. "
            f"Registered tools: {registered}"
        )
    return tool_cls()


def list_tools() -> List[ToolMeta]:
    """Return metadata for all registered tools (for Developer Panel / diagnostics)."""
    metas = []
    for tool_name, tool_cls in TOOL_REGISTRY.items():
        # Each tool class has a class-level `meta` attribute
        meta = getattr(tool_cls, "meta", None)
        if meta:
            metas.append(meta)
        else:
            logger.warning(f"Tool '{tool_name.value}' has no meta attribute.")
    return metas


def is_registered(tool_name: ToolName) -> bool:
    """Return True if the tool is registered."""
    return tool_name in TOOL_REGISTRY
