"""
Tests for Tool Registry — Milestone 10

Tests cover:
  - All 4 core tools are registered
  - get_tool() returns correct instances
  - Unregistered tool raises KeyError
  - list_tools() returns metadata for all tools
  - is_registered() returns correct boolean
  - BaseTool.meta is properly set on each tool class
"""

import pytest

from app.ai.planner.schemas import ToolName
from app.ai.tools.base import BaseTool, ToolMeta
from app.ai.tools.registry import get_tool, is_registered, list_tools
from app.ai.tools.document_reader import DocumentReaderTool
from app.ai.tools.document_search import DocumentSearchTool
from app.ai.tools.general_llm import GeneralLLMTool
from app.ai.tools.conversation_memory import ConversationMemoryTool


class TestToolRegistry:
    def test_all_core_tools_registered(self):
        for name in [
            ToolName.DOCUMENT_READER,
            ToolName.DOCUMENT_SEARCH,
            ToolName.GENERAL_LLM,
            ToolName.CONVERSATION_MEMORY,
        ]:
            assert is_registered(name), f"{name.value} not registered"

    def test_get_tool_returns_correct_instances(self):
        assert isinstance(get_tool(ToolName.DOCUMENT_READER), DocumentReaderTool)
        assert isinstance(get_tool(ToolName.DOCUMENT_SEARCH), DocumentSearchTool)
        assert isinstance(get_tool(ToolName.GENERAL_LLM), GeneralLLMTool)
        assert isinstance(get_tool(ToolName.CONVERSATION_MEMORY), ConversationMemoryTool)

    def test_unregistered_tool_raises_key_error(self):
        # Use a fake ToolName value by creating a mock
        class FakeTool:
            value = "nonexistent_tool"

        with pytest.raises(KeyError):
            from app.ai.tools.registry import TOOL_REGISTRY
            TOOL_REGISTRY[FakeTool()]

    def test_list_tools_returns_all_meta(self):
        metas = list_tools()
        assert len(metas) == 4
        names = {m.name for m in metas}
        assert "document_reader" in names
        assert "document_search" in names
        assert "general_llm" in names
        assert "conversation_memory" in names

    def test_is_registered_true_for_core_tools(self):
        assert is_registered(ToolName.DOCUMENT_READER) is True

    def test_get_tool_creates_fresh_instances(self):
        """Each call should return a new instance."""
        t1 = get_tool(ToolName.DOCUMENT_READER)
        t2 = get_tool(ToolName.DOCUMENT_READER)
        assert t1 is not t2


class TestToolMeta:
    def test_document_reader_meta(self):
        meta = DocumentReaderTool.meta
        assert isinstance(meta, ToolMeta)
        assert meta.name == "document_reader"
        assert meta.supports_streaming is False
        assert meta.timeout_seconds > 0

    def test_document_search_meta(self):
        meta = DocumentSearchTool.meta
        assert meta.name == "document_search"
        assert "semantic_search" in meta.capabilities

    def test_general_llm_meta(self):
        meta = GeneralLLMTool.meta
        assert meta.name == "general_llm"
        assert meta.supports_streaming is True

    def test_conversation_memory_meta(self):
        meta = ConversationMemoryTool.meta
        assert meta.name == "conversation_memory"
        assert meta.requires_auth is False


class TestBaseToolInterface:
    def test_all_tools_subclass_base_tool(self):
        for tool_cls in [
            DocumentReaderTool, DocumentSearchTool,
            GeneralLLMTool, ConversationMemoryTool
        ]:
            assert issubclass(tool_cls, BaseTool)

    def test_all_tools_have_execute_method(self):
        for tool_cls in [
            DocumentReaderTool, DocumentSearchTool,
            GeneralLLMTool, ConversationMemoryTool
        ]:
            assert hasattr(tool_cls, "execute")
            assert callable(tool_cls.execute)
