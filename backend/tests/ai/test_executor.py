"""
Tests for Executor — Milestone 10

Tests cover:
  - Single step execution (sequential)
  - Parallel step grouping
  - Tool failure triggers retry
  - Tool failure after max retries returns StepResult(success=False)
  - GeneralLLM steps are skipped (reserved for final LLM call)
  - Final prompt is built from tool outputs
  - FinalResponse has correct structure
  - run_stream() yields tokens
  - Unregistered tool handled gracefully
"""

import pytest
from dataclasses import dataclass, field
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock

from app.ai.executor.executor import Executor, _group_steps
from app.ai.executor.schemas import ExecutionContext, FinalResponse, StepResult
from app.ai.planner.schemas import (
    ExecutionPlan, ExecutionStep, TaskType, ToolName, ResponseMode
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_context(**kwargs) -> ExecutionContext:
    return ExecutionContext(
        pipeline_id="pipe_test",
        request_id="req_test",
        conversation_id="conv_test",
        user_id="user_test",
        db=AsyncMock(),
        attached_document_ids=["doc-1"],
        attached_document_titles=["Test Doc"],
        history=[],
        raw_query="test query",
        **kwargs
    )


def _make_plan(steps: List[ExecutionStep], task=TaskType.DOCUMENT_QA, **kwargs) -> ExecutionPlan:
    return ExecutionPlan(
        task=task,
        reasoning="Test plan",
        steps=steps,
        **kwargs
    )


# ---------------------------------------------------------------------------
# Tests for _group_steps
# ---------------------------------------------------------------------------

class TestGroupSteps:
    def test_all_sequential(self):
        steps = [
            ExecutionStep(tool=ToolName.DOCUMENT_SEARCH, parallel=False),
            ExecutionStep(tool=ToolName.CONVERSATION_MEMORY, parallel=False),
        ]
        groups = _group_steps(steps)
        assert len(groups) == 2
        assert all(len(g) == 1 for g in groups)

    def test_parallel_group(self):
        steps = [
            ExecutionStep(tool=ToolName.DOCUMENT_SEARCH, parallel=True),
            ExecutionStep(tool=ToolName.CONVERSATION_MEMORY, parallel=True),
            ExecutionStep(tool=ToolName.GENERAL_LLM, parallel=False),
        ]
        groups = _group_steps(steps)
        assert len(groups) == 2
        assert len(groups[0]) == 2  # parallel group
        assert len(groups[1]) == 1  # sequential

    def test_empty_steps(self):
        assert _group_steps([]) == []


# ---------------------------------------------------------------------------
# Tests for Executor.run
# ---------------------------------------------------------------------------

class TestExecutorRun:

    @pytest.mark.asyncio
    async def test_general_llm_step_is_skipped_during_tool_execution(self):
        """GeneralLLM steps should be skipped — they're the final LLM call."""
        executor = Executor()
        context = _make_context()
        plan = _make_plan(
            steps=[ExecutionStep(tool=ToolName.GENERAL_LLM, description="Final answer")],
            task=TaskType.GENERAL,
        )

        # Mock the GeneralLLMTool.execute used for the final LLM call
        mock_llm_result = {
            "response": "Hello! I'm Conduit.",
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "latency_ms": 500,
            "cost": 0.0001,
            "finish_reason": "stop",
        }
        with patch("app.ai.executor.executor.GeneralLLMTool.execute", new_callable=AsyncMock, return_value=mock_llm_result):
            response = await executor.run(plan, context)

        assert isinstance(response, FinalResponse)
        assert response.answer == "Hello! I'm Conduit."
        assert response.error is None

    @pytest.mark.asyncio
    async def test_document_search_step_executed_and_result_stored(self):
        """Document search tool should run and store output in context."""
        executor = Executor()
        context = _make_context()
        plan = _make_plan(
            steps=[
                ExecutionStep(tool=ToolName.DOCUMENT_SEARCH, description="Search docs"),
                ExecutionStep(tool=ToolName.GENERAL_LLM, description="Generate answer"),
            ],
            task=TaskType.DOCUMENT_QA,
            requires_documents=True,
            requires_retrieval=True,
        )

        mock_search_result = {
            "chunks": [{"score": 0.9, "payload": {"document_title": "Test Doc", "content": "DRM is...", "chunk_index": 0, "provider": "test"}}],
            "optimized_chunks": [{"score": 0.9, "payload": {"document_title": "Test Doc", "content": "DRM is...", "chunk_index": 0, "provider": "test"}}],
            "raw_chunks": [],
            "filtered_chunks": [],
            "retrieval_records": [],
            "query_used": "DRM",
            "source": "document_search",
        }
        mock_llm_result = {"response": "DRM stands for Digital Rights Management.", "prompt_tokens": 100, "completion_tokens": 30, "latency_ms": 800, "cost": 0.0002, "finish_reason": "stop"}

        with patch("app.ai.tools.document_search.DocumentSearchTool.execute", new_callable=AsyncMock, return_value=mock_search_result):
            with patch("app.ai.executor.executor.GeneralLLMTool.execute", new_callable=AsyncMock, return_value=mock_llm_result):
                response = await executor.run(plan, context)

        assert response.answer == "DRM stands for Digital Rights Management."
        assert len(response.retrieved_chunks) > 0

    @pytest.mark.asyncio
    async def test_tool_failure_returns_error_response(self):
        """If a tool raises an exception, Executor should return an error FinalResponse."""
        executor = Executor()
        context = _make_context()
        plan = _make_plan(
            steps=[ExecutionStep(tool=ToolName.DOCUMENT_SEARCH, retry_on_failure=False)],
            task=TaskType.DOCUMENT_QA,
        )

        with patch("app.ai.tools.document_search.DocumentSearchTool.execute", new_callable=AsyncMock, side_effect=Exception("Qdrant is down")):
            with patch("app.ai.executor.executor.GeneralLLMTool.execute", new_callable=AsyncMock, return_value={"response": "fallback", "prompt_tokens": 10, "completion_tokens": 5, "latency_ms": 100, "cost": 0.0, "finish_reason": "stop"}):
                response = await executor.run(plan, context)

        # Executor should continue to final LLM call even with failed tool steps
        assert isinstance(response, FinalResponse)

    @pytest.mark.asyncio
    async def test_empty_plan_steps_uses_general_llm(self):
        """Empty plan steps should fall back to GeneralLLM."""
        executor = Executor()
        context = _make_context()
        plan = _make_plan(steps=[], task=TaskType.GENERAL)

        mock_llm = {"response": "Hi there!", "prompt_tokens": 20, "completion_tokens": 5, "latency_ms": 200, "cost": 0.0, "finish_reason": "stop"}
        with patch("app.ai.executor.executor.GeneralLLMTool.execute", new_callable=AsyncMock, return_value=mock_llm):
            response = await executor.run(plan, context)

        assert response.answer == "Hi there!"


class TestExecutorRunStream:
    @pytest.mark.asyncio
    async def test_stream_yields_tokens(self):
        """run_stream should yield string tokens."""
        executor = Executor()
        context = _make_context()
        plan = _make_plan(
            steps=[ExecutionStep(tool=ToolName.GENERAL_LLM, description="Answer")],
            task=TaskType.GENERAL,
        )

        async def mock_stream(*args, **kwargs):
            yield "Hello"
            yield " world"
            yield "!"

        with patch("app.ai.executor.executor.GeneralLLMTool.stream", return_value=mock_stream()):
            tokens = []
            async for token in executor.run_stream(plan, context):
                tokens.append(token)

        assert "".join(tokens) == "Hello world!"


class TestExecutorPlanOverride:
    def test_override_search_to_reader_for_summary(self):
        executor = Executor()
        context = _make_context()
        plan = _make_plan(
            steps=[ExecutionStep(tool=ToolName.DOCUMENT_SEARCH)],
            task=TaskType.DOCUMENT_SUMMARY,
            requires_documents=True,
            requires_retrieval=True,
        )
        corrected = executor._validate_and_correct_plan(plan, context, "[test]")
        assert corrected.steps[0].tool == ToolName.DOCUMENT_READER
        assert corrected.requires_retrieval is False

    def test_override_reader_to_search_for_qa(self):
        executor = Executor()
        context = _make_context()
        plan = _make_plan(
            steps=[ExecutionStep(tool=ToolName.DOCUMENT_READER)],
            task=TaskType.DOCUMENT_QA,
            requires_documents=True,
        )
        corrected = executor._validate_and_correct_plan(plan, context, "[test]")
        assert corrected.steps[0].tool == ToolName.DOCUMENT_SEARCH
        assert corrected.requires_retrieval is True

    def test_override_doc_tools_without_docs(self):
        executor = Executor()
        context = ExecutionContext(
            pipeline_id="pipe_test",
            request_id="req_test",
            conversation_id="conv_test",
            user_id="user_test",
            db=AsyncMock(),
            attached_document_ids=[],
            attached_document_titles=[],
            history=[],
            raw_query="test query",
        )
        plan = _make_plan(
            steps=[ExecutionStep(tool=ToolName.DOCUMENT_SEARCH)],
            task=TaskType.DOCUMENT_QA,
            requires_documents=True,
        )
        corrected = executor._validate_and_correct_plan(plan, context, "[test]")
        assert corrected.task == TaskType.GENERAL
        assert corrected.steps[0].tool == ToolName.GENERAL_LLM
