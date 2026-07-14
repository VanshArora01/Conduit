"""
Tests for PlannerService — Production Readiness / Intent Routing

Tests cover:
  - Heuristic fast-path (greetings, intent classification, no-document queries)
  - LLM-based planning with valid JSON output
  - Retry on malformed JSON
  - Fallback plan on repeated failure
  - Response mode override logic
  - Scenario matrix intents
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

from app.ai.planner.planner import PlannerService, _is_greeting, _detect_intent, _detect_answer_length
from app.ai.planner.schemas import (
    ExecutionPlan, PlannerRequest, TaskType, ToolName,
)


def _make_request(query: str, has_documents: bool = False, titles=None, history=None) -> PlannerRequest:
    return PlannerRequest(
        query=query,
        conversation_id="test-conv-123",
        has_documents=has_documents,
        attached_document_titles=titles or [],
        conversation_history=history or [],
    )


def _valid_plan_json(**overrides) -> str:
    plan = {
        "task": "GENERAL",
        "reasoning": "test reasoning",
        "confidence": 0.9,
        "steps": [{"tool": "general_llm", "description": "test", "config": {}, "parallel": False}],
        "rewritten_query": None,
        "requires_documents": False,
        "requires_retrieval": False,
        "requires_history": False,
        "requires_general_knowledge": True,
        "response_mode": "stream",
        "max_chunks": 5,
        "retrieval_strategy": None,
    }
    plan.update(overrides)
    return json.dumps(plan)


class TestIsGreeting:
    def test_hi(self):
        assert _is_greeting("Hi") is True

    def test_hello(self):
        assert _is_greeting("Hello!") is True

    def test_thanks(self):
        assert _is_greeting("thanks") is True

    def test_short_phrase(self):
        assert _is_greeting("ok cool") is True

    def test_question(self):
        assert _is_greeting("What is the main theme?") is False

    def test_how_question(self):
        assert _is_greeting("How does DRM work?") is False

    def test_long_greeting(self):
        assert _is_greeting("this is a long sentence without meaning") is False


class TestDetectIntent:
    def test_summarize(self):
        plan = _detect_intent("summarize this document", True, 1)
        assert plan is not None
        assert plan.task == TaskType.DOCUMENT_SUMMARY
        assert plan.steps[0].tool == ToolName.DOCUMENT_READER

    def test_rewrite(self):
        plan = _detect_intent("rewrite the introduction to be more professional", True, 1)
        assert plan is not None
        assert plan.task == TaskType.DOCUMENT_REWRITE
        assert plan.steps[0].tool == ToolName.DOCUMENT_READER

    def test_improve(self):
        plan = _detect_intent("improve this document based on standard practices", True, 1)
        assert plan is not None
        assert plan.task == TaskType.DOCUMENT_REWRITE

    def test_compare(self):
        plan = _detect_intent("compare document A and document B", True, 2)
        assert plan is not None
        assert plan.task == TaskType.DOCUMENT_COMPARISON
        assert plan.steps[0].tool == ToolName.DOCUMENT_READER

    def test_fact_lookup(self):
        plan = _detect_intent("what is DRM", True, 1)
        assert plan is not None
        assert plan.task == TaskType.DOCUMENT_QA
        assert plan.steps[0].tool == ToolName.DOCUMENT_SEARCH

    def test_general_knowledge_with_docs(self):
        plan = _detect_intent("what is the capital of France?", True, 1)
        assert plan is not None
        assert plan.task == TaskType.GENERAL
        assert plan.steps[0].tool == ToolName.GENERAL_LLM

    def test_conversation_memory(self):
        plan = _detect_intent("what did you say before about DRM", True, 1, has_history=True)
        assert plan is not None
        assert plan.task == TaskType.CONVERSATION_MEMORY

    def test_followup(self):
        plan = _detect_intent("explain that further", True, 1, has_history=True)
        assert plan is not None
        assert plan.task == TaskType.CONVERSATION_MEMORY

    def test_no_docs_returns_none(self):
        assert _detect_intent("summarize this", False, 0) is None


class TestAnswerLength:
    def test_default_medium(self):
        assert _detect_answer_length("summarize the doc") == "medium"

    def test_short(self):
        assert _detect_answer_length("briefly summarize this") == "short"

    def test_detailed(self):
        assert _detect_answer_length("give a detailed explanation") == "detailed"


class TestPlannerServiceFastPath:
    @pytest.mark.asyncio
    async def test_greeting_returns_general_plan_without_llm(self):
        service = PlannerService()
        with patch.object(service._llm, "generate", new_callable=AsyncMock) as mock_llm:
            plan = await service.plan(_make_request("Hi"), pipeline_id="p1", conversation_id="c1")
        mock_llm.assert_not_called()
        assert plan.task == TaskType.GENERAL
        assert any(s.tool == ToolName.GENERAL_LLM for s in plan.steps)

    @pytest.mark.asyncio
    async def test_no_documents_returns_general_plan_without_llm(self):
        service = PlannerService()
        with patch.object(service._llm, "generate", new_callable=AsyncMock) as mock_llm:
            plan = await service.plan(
                _make_request("Summarise my synopsis", has_documents=False),
                pipeline_id="p1", conversation_id="c1"
            )
        mock_llm.assert_not_called()
        assert plan.task == TaskType.GENERAL

    @pytest.mark.asyncio
    async def test_summarize_intent_fast_path(self):
        service = PlannerService()
        with patch.object(service._llm, "generate", new_callable=AsyncMock) as mock_llm:
            plan = await service.plan(
                _make_request("summarize this document", has_documents=True, titles=["Doc.pdf"]),
                pipeline_id="p1", conversation_id="c1",
            )
        mock_llm.assert_not_called()
        assert plan.task == TaskType.DOCUMENT_SUMMARY
        assert plan.steps[0].tool == ToolName.DOCUMENT_READER

    @pytest.mark.asyncio
    async def test_determinism_identical_query(self):
        service = PlannerService()
        req = _make_request("what is DRM", has_documents=True, titles=["Doc.pdf"])
        with patch.object(service._llm, "generate", new_callable=AsyncMock):
            a = await service.plan(req, pipeline_id="p1", conversation_id="c1")
            b = await service.plan(req, pipeline_id="p2", conversation_id="c1")
        assert a.task == b.task
        assert [s.tool for s in a.steps] == [s.tool for s in b.steps]


class TestPlannerServiceLLMPath:
    @pytest.mark.asyncio
    async def test_valid_llm_output_parsed(self):
        """Ambiguous query that does not hit intent heuristics → LLM plan."""
        service = PlannerService()
        valid_json = _valid_plan_json(
            task="DOCUMENT_SUMMARY",
            steps=[{"tool": "document_reader", "description": "read", "config": {}, "parallel": False}],
            requires_documents=True,
            rewritten_query="summary key points",
        )
        with patch.object(service._llm, "generate", new_callable=AsyncMock, return_value=valid_json) as mock_llm:
            plan = await service.plan(
                _make_request(
                    "Considering regulatory constraints, outline a rollout strategy referencing my materials",
                    has_documents=True, titles=["Synopsis.pdf"]
                ),
                pipeline_id="p1", conversation_id="c1"
            )
        mock_llm.assert_called()
        assert plan.task == TaskType.DOCUMENT_SUMMARY
        assert plan.is_fallback is False

    @pytest.mark.asyncio
    async def test_malformed_json_triggers_retry_then_succeeds(self):
        service = PlannerService()
        valid_json = _valid_plan_json()
        side_effects = ["this is not json", valid_json]
        with patch.object(service._llm, "generate", new_callable=AsyncMock, side_effect=side_effects):
            plan = await service.plan(
                _make_request(
                    "Considering regulatory constraints, outline a rollout strategy referencing my materials",
                    has_documents=True, titles=["Doc.pdf"]
                ),
                pipeline_id="p1", conversation_id="c1"
            )
        assert plan.task == TaskType.GENERAL
        assert plan.is_fallback is False

    @pytest.mark.asyncio
    async def test_both_attempts_fail_returns_fallback(self):
        service = PlannerService()
        with patch.object(service._llm, "generate", new_callable=AsyncMock, side_effect=Exception("LLM down")):
            plan = await service.plan(
                _make_request(
                    "Considering regulatory constraints, outline a rollout strategy referencing my materials",
                    has_documents=True, titles=["Doc.pdf"]
                ),
                pipeline_id="p1", conversation_id="c1"
            )
        assert plan.is_fallback is True
        assert plan.task == TaskType.GENERAL

    @pytest.mark.asyncio
    async def test_plan_with_doc_tools_but_no_docs_downgraded(self):
        service = PlannerService()
        plan_with_docs = _valid_plan_json(
            task="DOCUMENT_QA",
            steps=[{"tool": "document_search", "description": "search", "config": {}, "parallel": False}],
            requires_documents=True,
            requires_retrieval=True,
        )
        with patch.object(service._llm, "generate", new_callable=AsyncMock, return_value=plan_with_docs):
            plan = await service.plan(
                _make_request("Explain DRM", has_documents=False),
                pipeline_id="p1", conversation_id="c1"
            )
        assert plan.task == TaskType.GENERAL


class TestPlannerScenarios:
    @pytest.mark.asyncio
    async def test_scenario_1_summarise_uses_document_reader(self):
        service = PlannerService()
        with patch.object(service._llm, "generate", new_callable=AsyncMock) as mock_llm:
            plan = await service.plan(
                _make_request("summarize this document", has_documents=True, titles=["Synopsis.pdf"]),
                pipeline_id="p1", conversation_id="c1"
            )
        mock_llm.assert_not_called()
        assert plan.task == TaskType.DOCUMENT_SUMMARY
        assert any(s.tool == ToolName.DOCUMENT_READER for s in plan.steps)

    @pytest.mark.asyncio
    async def test_scenario_2_explain_drm_uses_document_search(self):
        service = PlannerService()
        with patch.object(service._llm, "generate", new_callable=AsyncMock) as mock_llm:
            plan = await service.plan(
                _make_request("what is DRM", has_documents=True, titles=["Synopsis.pdf"]),
                pipeline_id="p1", conversation_id="c1"
            )
        mock_llm.assert_not_called()
        assert plan.task == TaskType.DOCUMENT_QA
        assert any(s.tool == ToolName.DOCUMENT_SEARCH for s in plan.steps)

    @pytest.mark.asyncio
    async def test_scenario_4_fifa_2022_no_docs(self):
        service = PlannerService()
        with patch.object(service._llm, "generate", new_callable=AsyncMock) as mock_llm:
            plan = await service.plan(
                _make_request("Who won FIFA 2022?", has_documents=False),
                pipeline_id="p1", conversation_id="c1"
            )
        mock_llm.assert_not_called()
        assert plan.task == TaskType.GENERAL

    @pytest.mark.asyncio
    async def test_scenario_capital_of_france(self):
        service = PlannerService()
        with patch.object(service._llm, "generate", new_callable=AsyncMock) as mock_llm:
            plan = await service.plan(
                _make_request("what is the capital of France?", has_documents=True, titles=["Doc.pdf"]),
                pipeline_id="p1", conversation_id="c1"
            )
        mock_llm.assert_not_called()
        assert plan.task == TaskType.GENERAL

    @pytest.mark.asyncio
    async def test_scenario_6_hi_greeting(self):
        service = PlannerService()
        with patch.object(service._llm, "generate", new_callable=AsyncMock) as mock_llm:
            plan = await service.plan(
                _make_request("Hi"),
                pipeline_id="p1", conversation_id="c1"
            )
        mock_llm.assert_not_called()
        assert plan.task == TaskType.GENERAL

    @pytest.mark.asyncio
    async def test_scenario_7_no_docs_auto_general(self):
        service = PlannerService()
        with patch.object(service._llm, "generate", new_callable=AsyncMock) as mock_llm:
            plan = await service.plan(
                _make_request("Tell me about quantum computing", has_documents=False),
                pipeline_id="p1", conversation_id="c1"
            )
        mock_llm.assert_not_called()
        assert plan.task == TaskType.GENERAL
        assert not plan.is_fallback
